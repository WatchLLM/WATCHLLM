# WatchLLM Runtime

```
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░  ░░░░  ░░░      ░░░        ░░░      ░░░  ░░░░  ░░  ░░░░░░░░  ░░░░░░░░  ░░░░  ░
▒  ▒  ▒  ▒▒  ▒▒▒▒  ▒▒▒▒▒  ▒▒▒▒▒  ▒▒▒▒  ▒▒  ▒▒▒▒  ▒▒  ▒▒▒▒▒▒▒▒  ▒▒▒▒▒▒▒▒   ▒▒   ▒
▓        ▓▓  ▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓▓▓▓        ▓▓  ▓▓▓▓▓▓▓▓  ▓▓▓▓▓▓▓▓        ▓
█   ██   ██        █████  █████  ████  ██  ████  ██  ████████  ████████  █  █  █
█  ████  ██  ████  █████  ██████      ███  ████  ██        ██        ██  ████  █
████████████████████████████████████████████████████████████████████████████████
```

*Governance-aware orchestration substrate for autonomous coding systems.*

## Current status

Early design & specification phase. Subsystem boundary defined; codebase scaffolded.

## Overview

The `runtime` repository contains the runtime orchestration layer for WatchLLM. It provides the secure execution boundary for autonomous software agents, managing tool permissions, dynamically issuing and rotating access credentials (Non-Human Identity), sandboxing file/system calls, and injecting context variables like `WATCHLLM_AGENT_ID` to support audit and attribution.

## Core Features

- **Agent Identity & Attribution:** Automatically injects agent attribution metadata into execution shells.
- **Sandboxed Execution:** Wraps tool and shell commands inside secure namespaces/subprocesses to prevent escape.
- **Dynamic Credential Rotation:** Integrates with access management systems to supply short-lived, task-specific credentials.
- **Tool Access Control:** Declares and enforces tool call permissions dynamically at runtime.

## Relationship to Kernel

- **WatchLLM Runtime (Orchestration/Access):** Governs the running agent process and its network/OS permissions.
- **WatchLLM Kernel (Write-Path law):** Intercepts all code modifications during shell writes before they persist to disk.

## Non-goals

- **AST Rule Analysis:** `runtime` does not parse AST structures or evaluate code syntax; it calls the Kernel for code block decisions.
- **Interactive UI:** Does not host visual dashboards; it operates purely as an execution daemon or SDK.

## Installation

```bash
pip install -e .
```

## Usage

```bash
watchllm-runtime --help
python -m watchllm_runtime --help
```

## Links

- [WatchLLM Organization](https://github.com/WatchLLM)
- [Central Documentation](https://github.com/WatchLLM/docs)
- [watchllm.dev](https://watchllm.dev)
