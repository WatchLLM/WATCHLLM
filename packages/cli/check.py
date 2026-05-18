import json
from pathlib import Path
from urllib import error, request
from urllib.parse import urlsplit, urlunsplit

from config import load_mode
from rules.engine import evaluate_rules_for_content


def read_file(file_path: str) -> dict[str, object]:
    path = Path(file_path)

    return {
        'file_path': str(path),
        'content': path.read_text(encoding='utf-8'),
    }


def _shadow_violation_payload(
    violations: list[dict[str, object]],
    file_path: str,
) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []

    for violation in violations:
        severity = violation.get('severity')

        if severity not in {'info', 'warn', 'critical'}:
            severity = 'warn'

        line = violation.get('line')
        column = violation.get('column')

        payload.append(
            {
                'rule_key': str(violation.get('rule') or 'unknown'),
                'severity': severity,
                'file_path': str(violation.get('file_path') or file_path),
                'line': line if isinstance(line, int) else None,
                'column': column if isinstance(column, int) else None,
                'reason': str(violation.get('reason') or ''),
            },
        )

    return payload


def _format_shadow_violations(
    file_path: str,
    violations: list[dict[str, object]],
    response_body: str = '',
) -> str:
    lines = []

    if response_body.strip():
        lines.extend([response_body.rstrip(), ''])

    lines.extend(['WatchLLM shadow violations', ''])

    for index, violation in enumerate(violations, start=1):
        rule = violation.get('rule', '')
        reason = violation.get('reason', '')
        line = violation.get('line')
        column = violation.get('column')
        location = file_path

        if isinstance(line, int):
            location = f'{location}:{line}'

            if isinstance(column, int):
                location = f'{location}:{column}'

        lines.extend(
            [
                f'{index}. Rule: {rule}',
                f'   Location: {location}',
                f'   Reason: {reason}',
                '',
            ],
        )

    return '\n'.join(lines).rstrip()


def send_file_content(
    worker_url: str,
    token: str,
    file_path: str,
    content: str,
    shadow_violations: list[dict[str, object]] | None = None,
) -> tuple[int, str]:
    url = worker_url.strip()

    if not url:
        raise ValueError('Worker URL is required')

    data: dict[str, object] = {
        'file_path': str(Path(file_path)),
        'content': content,
    }

    if shadow_violations:
        data['shadow_violations'] = _shadow_violation_payload(shadow_violations, file_path)

    payload = json.dumps(data).encode('utf-8')

    req = request.Request(
        url,
        data=payload,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )

    try:
        with request.urlopen(req) as response:
            return response.status, response.read().decode('utf-8')
    except error.HTTPError as exc:
        return exc.code, exc.read().decode('utf-8')


def send_file(
    worker_url: str,
    token: str,
    file_path: str,
    shadow_violations: list[dict[str, object]] | None = None,
) -> tuple[int, str]:
    data = read_file(file_path)

    return send_file_content(
        worker_url,
        token,
        file_path,
        str(data['content']),
        shadow_violations,
    )


def _try_attach_llm_review(
    worker_url: str | None,
    token: str | None,
    file_path: str,
    content: str,
    blocking_violations: list[dict[str, object]],
) -> None:
    if not worker_url or not token or not blocking_violations:
        return

    try:
        first_violation = blocking_violations[0]
        reason = str(first_violation.get('reason', ''))
        parts = urlsplit(worker_url.strip())
        review_url = urlunsplit((parts.scheme, parts.netloc, '/llm/review', '', ''))

        payload = json.dumps(
            {
                'violation': {
                    'rule_name': str(first_violation.get('rule', '')),
                    'reason': reason,
                    'location': file_path,
                },
                'code': content,
            },
        ).encode('utf-8')

        req = request.Request(
            review_url,
            data=payload,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )

        with request.urlopen(req) as response:
            if response.status >= 200 and response.status < 300:
                review = json.loads(response.read().decode('utf-8'))
                explanation = review.get('explanation')
                suggestion = review.get('suggestion')
                reason_lines = [reason]

                if isinstance(explanation, str) and explanation:
                    first_violation['explanation'] = explanation
                    reason_lines.append(f'Explanation: {explanation}')

                if isinstance(suggestion, str) and suggestion:
                    first_violation['suggestion'] = suggestion
                    reason_lines.append(f'Suggestion: {suggestion}')

                first_violation['reason'] = '\n'.join(reason_lines)
    except Exception:
        return


def check_content(
    worker_url: str | None,
    token: str | None,
    file_path: str,
    content: str,
    submit_remote: bool = True,
    explain: bool = True,
) -> str:
    mode = load_mode()
    violations = evaluate_rules_for_content(file_path, content)
    blocking_violations = [
        violation
        for violation in violations
        if violation.get('blocking') is True
    ]

    if blocking_violations:
        if explain:
            _try_attach_llm_review(worker_url, token, file_path, content, blocking_violations)

        raise RuntimeError(json.dumps({'status': 'blocked', 'violations': violations}))

    if not submit_remote:
        if violations:
            return _format_shadow_violations(file_path, violations)

        return 'WatchLLM local check passed'

    if not worker_url:
        raise ValueError('Worker URL is required')

    if not token:
        raise ValueError('Token is required')

    status, body = send_file_content(
        worker_url,
        token,
        file_path,
        content,
        violations if mode == 'shadow' else None,
    )

    if status < 200 or status >= 300:
        raise RuntimeError(f'Worker rejected file: {status} {body}')

    if violations:
        return _format_shadow_violations(file_path, violations, body)

    return body


def check_file(
    worker_url: str | None,
    token: str | None,
    file_path: str,
    submit_remote: bool = True,
    explain: bool = True,
) -> str:
    data = read_file(file_path)

    return check_content(
        worker_url,
        token,
        file_path,
        str(data['content']),
        submit_remote=submit_remote,
        explain=explain,
    )
