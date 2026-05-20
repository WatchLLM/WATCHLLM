# WatchLLM

```text
 __        __    _       _     _     _     __  __
 \ \      / /_ _| |_ ___| |__ | |   | |   |  \/  |
  \ \ /\ / / _` | __/ __| '_ \| |   | |   | |\/| |
   \ V  V / (_| | || (__| | | | |___| |___| |  | |
    \_/\_/ \__,_|\__\___|_| |_|_____|_____|_|  |_|
```

WatchLLM is a write-path governance layer for AI-generated code.

It runs deterministic architectural and security checks before code is saved, submitted, or persisted. The LLM layer is explanation-only and never decides enforcement.

## What it does

- Blocks invalid code in enforce mode
- Warns and logs in shadow mode
- Runs local AST checks through the Python CLI
- Supports VS Code save-time enforcement
- Stores remote audit records through the Cloudflare Worker
- Provides LLM explanations without changing rule decisions

## Core principle

```text
Deterministic rules decide.
LLM explains only.
```

## Repository layout

```text
packages/cli/         Python CLI and deterministic rule engine
packages/vscode/      VS Code save-time enforcement extension
context/              Product, architecture, and execution constraints
```

## Quick start

Install Python dependencies, then run the CLI directly from the packages/cli directory or via the `watchllm` command.

```bash
python packages/cli/main.py --version
python packages/cli/main.py check path/to/file.ts --local-only
```

## Login

Remote checks require a Clerk token.

```bash
python packages/cli/main.py login
```

Or pass the token directly:

```bash
python packages/cli/main.py login "$CLERK_TOKEN"
```

The token is stored locally at:

```text
~/.watchllm/token
```

## Local checks

Local checks run deterministic rules only and do not require network access.

```bash
python packages/cli/main.py check packages/cli/rules/auth.py --local-only
```

This is the path used by the VS Code extension for save-time blocking.

## Remote checks

Remote checks submit the file to the Worker for audit logging and storage.

```bash
WATCHLLM_WORKER_URL=https://your-worker.example.workers.dev/check \
python packages/cli/main.py check packages/cli/rules/auth.py
```

## Modes

WatchLLM supports two explicit modes:

### Enforce
Violations block the save or submission path (returns non-zero exit code).

### Shadow
Violations warn and are logged remotely, but do not block the pipeline.

---

## License

MIT License.
