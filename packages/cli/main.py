import argparse
import json
import os
import sys
from getpass import getpass

from auth import load_token, save_token
from check import check_content, check_file
from config import load_mode, set_mode
from output import (
    format_banner,
    format_error,
    format_success,
    format_violations,
    format_warning_text,
)

VERSION = '0.1.0'


def _is_worker_success_response(result: str) -> bool:
    try:
        payload = json.loads(result)
    except json.JSONDecodeError:
        return False

    return isinstance(payload, dict) and payload.get('ok') is True


def _print_check_result(result: str) -> None:
    stripped = result.strip()

    if stripped == 'WatchLLM local check passed':
        print(format_success('Local check passed'))
        return

    if stripped.startswith('WatchLLM shadow violations') or '\nWatchLLM shadow violations' in stripped:
        print(format_warning_text(stripped))
        return

    if _is_worker_success_response(stripped):
        print(format_success('Remote check passed and audit log stored'))
        return

    print(result)


def _run_check(args: argparse.Namespace) -> None:
    if args.mode:
        set_mode(args.mode)
    else:
        load_mode()

    submit_remote = not args.local_only
    explain = not args.no_explain and not args.local_only

    if submit_remote and not args.worker_url:
        raise ValueError('Worker URL required. Pass --worker-url or set WATCHLLM_WORKER_URL.')

    token = load_token() if submit_remote else ''

    if args.stdin:
        result = check_content(
            args.worker_url,
            token,
            args.file,
            sys.stdin.read(),
            submit_remote=submit_remote,
            explain=explain,
        )
    else:
        result = check_file(
            args.worker_url,
            token,
            args.file,
            submit_remote=submit_remote,
            explain=explain,
        )

    _print_check_result(result)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='watchllm',
        description=format_banner(enable_colour=False),
        epilog='Examples:\n'
        '  watchllm login\n'
        '  watchllm check workers/index.ts --local-only\n'
        '  watchllm check workers/index.ts --mode shadow\n',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--version', action='version', version=f'watchllm {VERSION}')

    subparsers = parser.add_subparsers(dest='command', required=True)

    login_parser = subparsers.add_parser('login', help='save a Clerk token locally')
    login_parser.add_argument('token', nargs='?')

    check_parser = subparsers.add_parser('check', help='run deterministic WatchLLM checks')
    check_parser.add_argument('file')
    check_parser.add_argument('--worker-url', default=os.environ.get('WATCHLLM_WORKER_URL'))
    check_parser.add_argument('--mode', choices=('enforce', 'shadow'))
    check_parser.add_argument('--local-only', action='store_true')
    check_parser.add_argument('--stdin', action='store_true')
    check_parser.add_argument('--no-explain', action='store_true')

    args = parser.parse_args()

    try:
        if args.command == 'login':
            token = args.token or getpass('Clerk token: ')
            save_token(token)
            print(format_success('Token saved'))
            return

        if args.command == 'check':
            _run_check(args)
            return
    except RuntimeError as exc:
        try:
            payload = json.loads(str(exc))
        except json.JSONDecodeError:
            print(format_error(str(exc)))
            raise SystemExit(1)

        violations = payload.get('violations')

        if isinstance(violations, list):
            print(format_violations(args.file, violations))
            raise SystemExit(1)

        print(format_error(str(exc)))
        raise SystemExit(1)
    except (FileNotFoundError, ValueError) as exc:
        print(format_error(str(exc)))
        raise SystemExit(1)
    except KeyboardInterrupt:
        print(format_error('Interrupted'))
        raise SystemExit(130)


if __name__ == '__main__':
    main()
