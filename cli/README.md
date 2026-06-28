# watchllm CLI

**Unified developer entry point for the WatchLLM toolchain.**

```
╔══════════════════════════════════════════════════════════════════╗
║   ░██╗ ░░     ██╗    ██╗  ██████╗████████╗ ██████╗██╗  ██╗      ║
║   ░██║ ░░     ██║    ██║  ██╔═══╝╚══██╔══╝██╔════╝██║  ██║      ║
║   ░██║ ░░     ██║ █╗ ██║  ██║       ██║   ██║     ███████║      ║
║   ░██║ ░░     ██║███╗██║  ██║       ██║   ██║     ██╔══██║      ║
║   ░██████╗    ╚███╔███╔╝  ╚██████╗  ██║   ╚██████╗██║  ██║      ║
║   ░╚═════╝     ╚══╝╚══╝    ╚═════╝  ╚═╝    ╚═════╝╚═╝  ╚═╝      ║
║        ███████╗███████╗███████╗██╗     ███╗   ███╗               ║
║        ╚══════╝╚══════╝╚══════╝╚═╝     ╚══╝   ╚══╝               ║
╚══════════════════════════════════════════════════════════════════╝
```

*Deterministic runtime governance for autonomous coding agents.*

---

## Install

```bash
pip install -e d:/watchllm/cli
```

## Commands

### Core Workflow

| Command | Description |
|---|---|
| `watchllm init [dir]` | Generate a default `.watchllm.yaml` in `dir` |
| `watchllm evaluate <file>` | Run the kernel governance checks on a source file |
| `watchllm preview <file>` | Dry-run evaluate — preview without enforcing |
| `watchllm status` | Check health of all installed WatchLLM subsystems |

### Safety & Recovery

| Command | Description |
|---|---|
| `watchllm diff` | Show git-style unified diff since last snapshot |
| `watchllm rollback` | Undo last file edit — restore from snapshot |

### Session Management

| Command | Description |
|---|---|
| `watchllm session list` | List all saved sessions |
| `watchllm session resume [name]` | Resume (or create) a named session |
| `watchllm session clear` | Delete all sessions |

### Setup

| Command | Description |
|---|---|
| `watchllm completion` | Show tab-completion setup instructions |

---

## Features

### 🎨 Premium Terminal UX
- **Animated spinners** for long-running kernel evaluations
- **Progress bars** with elapsed time tracking
- **Color-coded status logs**: green ✓ success, red ✗ errors, yellow ⚠ warnings
- **Full brand banner** with ASCII art logo

### 🛡 Interactive Safety
- **Confirmation prompts** before rollback, session clear, and other destructive operations
- **Dry-run mode** via `--dry-run` flag or `preview` command
- **Snapshot system**: every `evaluate` saves a snapshot for one-click rollback

### 📋 Intuitive Output
- **Syntax-highlighted code blocks** with line numbers
- **Git-style unified diffs** via `watchllm diff`
- **Compact tables** for status and session listings
- **Collapsible panels** for violation reports and guidance

### 💾 Context Preservation
- **Persistent sessions** remember working directory, model, and last active time
- **Multi-line paste** support
- **Graceful Ctrl+C handling** — stops cleanly without killing the terminal

---

## Examples

```bash
# Initialize config in current dir
watchllm init

# Dry-run first — see what happens without risk
watchllm preview src/auth/handler.ts

# Evaluate with full enforcement
watchllm evaluate src/auth/handler.ts

# Show what changed since last evaluation
watchllm diff

# Something went wrong? Roll back.
watchllm rollback

# Check everything is installed
watchllm status

# Save your state
watchllm session resume my-project

# Resume later
watchllm session resume my-project
```
