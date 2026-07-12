# klyd

```
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░  ░░░░  ░░░      ░░░        ░░░      ░░░  ░░░░  ░░  ░░░░░░░░  ░░░░░░░░  ░░░░  ░
▒  ▒  ▒  ▒▒  ▒▒▒▒  ▒▒▒▒▒  ▒▒▒▒▒  ▒▒▒▒  ▒▒  ▒▒▒▒  ▒▒  ▒▒▒▒▒▒▒▒  ▒▒▒▒▒▒▒▒   ▒▒   ▒
▓        ▓▓  ▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓▓▓▓        ▓▓  ▓▓▓▓▓▓▓▓  ▓▓▓▓▓▓▓▓        ▓
█   ██   ██        █████  █████  ████  ██  ████  ██  ████████  ████████  █  █  █
█  ████  ██  ████  █████  ██████      ███  ████  ██        ██        ██  ████  █
████████████████████████████████████████████████████████████████████████████████
```

*Persistent architectural memory for autonomous coding agents.*

## Current status

Early design & specification phase. Subsystem boundary defined; codebase scaffolded.

## Overview

Large Language Models (LLMs) tend to lose architectural context and make regression decisions over long coding sessions. `klyd` solves this by acting as a persistent architectural memory layer. It extracts architectural decisions from git history/diffs, stores them locally, and retrieves relevant constraints at write time to keep autonomous agents aligned with project guidelines.

`klyd` remembers. The kernel enforces.

## Core Features

- **Architectural Decision Extraction:** Auto-extracts design constraints and guidelines from repository changes and commit history.
- **Local Memory Store:** Uses a lightweight local SQLite database to persist constraints offline.
- **Context Retrieval:** Queries relevant architectural constraints based on the files currently being edited.
- **Agent Prompt Injection:** Injects retrieved guidelines into agent execution loops to guide code generation.

## Relationship to Kernel

- **klyd (Memory):** Tracks and provides the historical context and architectural rules.
- **Kernel (Enforcement):** Deteministically evaluates code changes at the write-path to ensure those rules are not violated.

## Non-goals

- **Write-path interception:** `klyd` does not block files or handle save hooks; that is the sole responsibility of the Kernel.
- **Code Generation:** `klyd` does not generate or rewrite source code.

## Installation

klyd is installed automatically as part of the unified WatchLLM CLI:

```bash
pip install watchllm
```

That single command installs klyd, the kernel, orchestrator, and the `watchllm` CLI entry point.

> **For contributors only:** To install klyd in editable mode for local development:
> ```bash
> pip install -e .
> ```

## Usage

```bash
watchllm --help
```

klyd's memory and context features are exposed via the unified `watchllm` command. You do not need to invoke `klyd` directly.

## Links

- [WatchLLM Organization](https://github.com/WatchLLM)
- [Central Documentation](https://github.com/WatchLLM/docs)
- [watchllm.dev](https://watchllm.dev)
