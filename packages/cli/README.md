# WatchLLM CLI

The WatchLLM CLI is the local deterministic enforcement engine.

It is responsible for:

- parsing source files
- running AST-based rules
- applying enforce or shadow mode
- blocking invalid writes locally
- submitting remote audit payloads when requested

## Commands

```bash
python cli/main.py --version
python cli/main.py login
python cli/main.py check <file>
```

## Login

```bash
python cli/main.py login
```

Or:

```bash
python cli/main.py login "$CLERK_TOKEN"
```

## Local-only check

Use this for save-time enforcement and offline checks.

```bash
python cli/main.py check path/to/file.ts --local-only
```

## Remote check

Remote checks require a Worker URL and a saved token.

```bash
python cli/main.py check path/to/file.ts --worker-url https://your-worker.example.workers.dev/check
```

Alternatively:

```bash
WATCHLLM_WORKER_URL=https://your-worker.example.workers.dev/check \
python cli/main.py check path/to/file.ts
```

## Stdin mode

Use stdin mode when the current editor buffer has not been written to disk yet.

```bash
cat path/to/file.ts | python cli/main.py check path/to/file.ts --local-only --stdin
```

The VS Code extension uses this path.

## Modes

### Enforce

```bash
python cli/main.py check path/to/file.ts --local-only --mode enforce
```

In enforce mode, blocking violations return a non-zero exit code.

### Shadow

```bash
python cli/main.py check path/to/file.ts --mode shadow
```

In shadow mode, violations are shown and can be logged remotely, but they do not block.

## Environment variables

```text
WATCHLLM_MODE          enforce or shadow
WATCHLLM_WORKER_URL    Worker /check endpoint
WATCHLLM_TOKEN_PATH    optional custom token path
NO_COLOR               disables ANSI colour output
```

## Exit behaviour

```text
0    check passed, or shadow warnings only
1    check blocked or configuration failed
130  interrupted
```

## Output

Successful local check:

```text
✓ Local check passed
```

Blocked check:

```text
✗ WatchLLM blocked this file

1. Rule: endpoint_requires_auth
   Severity: critical
   Location: workers/index.ts
   Reason: API handler accesses database before auth.verify()
```

Shadow mode:

```text
WatchLLM shadow violations

1. Rule: no_secrets_in_code
   Location: workers/index.ts
   Reason: Hardcoded secret detected
```
