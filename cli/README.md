# watchllm CLI

Unified developer entry point for the WatchLLM toolchain.

## Install

```bash
pip install -e d:/watchllm/cli
```

## Commands

| Command | Description |
|---|---|
| `watchllm init [dir]` | Generate a default `.watchllm.yaml` in `dir` |
| `watchllm evaluate <file>` | Run the kernel on a source file |
| `watchllm status` | Check health of all installed WatchLLM subsystems |

## Examples

```bash
# Initialize config in current dir
watchllm init

# Evaluate a TypeScript file
watchllm evaluate src/auth/handler.ts

# Check everything is installed
watchllm status
```
