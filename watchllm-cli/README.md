# watchllm

```
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░  ░░░░  ░░░      ░░░        ░░░      ░░░  ░░░░  ░░  ░░░░░░░░  ░░░░░░░░  ░░░░  ░
▒  ▒  ▒  ▒▒  ▒▒▒▒  ▒▒▒▒▒  ▒▒▒▒▒  ▒▒▒▒  ▒▒  ▒▒▒▒  ▒▒  ▒▒▒▒▒▒▒▒  ▒▒▒▒▒▒▒▒   ▒▒   ▒
▓        ▓▓  ▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓▓▓▓        ▓▓  ▓▓▓▓▓▓▓▓  ▓▓▓▓▓▓▓▓        ▓
█   ██   ██        █████  █████  ████  ██  ████  ██  ████████  ████████  █  █  █
█  ████  ██  ████  █████  ██████      ███  ████  ██        ██        ██  ████  █
████████████████████████████████████████████████████████████████████████████████
```

*Unified CLI for the WatchLLM agent governance ecosystem.*

## Installation

```bash
pip install watchllm
```

That's it. This single package installs the entire WatchLLM stack:

| Included package | Role |
|---|---|
| `watchllm-kernel` | Deterministic write-path enforcement kernel |
| `watchllm-klyd` | Persistent architectural memory layer |
| `watchllm-orchestrator` | Agent identity and policy orchestration |
| `watchllm` | This CLI — unified entry point for all commands |

## Usage

```bash
watchllm --help
```

### Commands

```bash
# Evaluate a source file against governance rules
watchllm evaluate <file>
watchllm evaluate --stdin < file.ts

# Spawn an agent session bound to an identity role
watchllm spawn --role read-only-agent

# Export the current kernel config
watchllm kernel export-config

# Inspect klyd memory
watchllm kl --help
```

## PyPI

- [`watchllm`](https://pypi.org/project/watchllm/) — install this one
- [`watchllm-kernel`](https://pypi.org/project/watchllm-kernel/) — pulled in automatically
- [`watchllm-klyd`](https://pypi.org/project/watchllm-klyd/) — pulled in automatically
- [`watchllm-orchestrator`](https://pypi.org/project/watchllm-orchestrator/) — pulled in automatically

## Links

- [WatchLLM Organization](https://github.com/WatchLLM)
- [Central Documentation](https://github.com/WatchLLM/docs)
- [watchllm.dev](https://watchllm.dev)
