# WatchLLM Orchestrator

```
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░  ░░░░  ░░░      ░░░        ░░░      ░░░  ░░░░  ░░  ░░░░░░░░  ░░░░░░░░  ░░░░  ░
▒  ▒  ▒  ▒▒  ▒▒▒▒  ▒▒▒▒▒  ▒▒▒▒▒  ▒▒▒▒  ▒▒  ▒▒▒▒  ▒▒  ▒▒▒▒▒▒▒▒  ▒▒▒▒▒▒▒▒   ▒▒   ▒
▓        ▓▓  ▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓▓▓▓        ▓▓  ▓▓▓▓▓▓▓▓  ▓▓▓▓▓▓▓▓        ▓
█   ██   ██        █████  █████  ████  ██  ████  ██  ████████  ████████  █  █  █
█  ████  ██  ████  █████  ██████      ███  ████  ██        ██        ██  ████  █
████████████████████████████████████████████████████████████████████████████████
```

*Centralized runtime orchestration, identity-aware execution, and dynamic policy graphs for autonomous agents.*

## Current status

Planning and scaffolding phase. Context docs are seeded.

## Overview

The `orchestrator` repository is the **Phase 7** orchestration layer of the WatchLLM ecosystem. While the `kernel` enforces rules deterministically at the filesystem level, `orchestrator` sits a layer above the agent itself. It controls *which* agents are allowed to run, *what* capabilities (identity) they have, and *how* they are routed to models.

## Core Features

- **Model Routing:** Dynamically routes agent tasks to the most appropriate LLM based on task complexity and organizational cost caps.
- **Identity-Aware Execution:** Binds an agent session to an identity token (e.g., "Junior Agent", "Lead Architect"). The Kernel reads this token to enforce identity-specific filesystem permissions.
- **Dynamic Policy Graphs:** Maps organizational rule schemas (from the `schemas/` repo) to specific projects at runtime without hardcoding.

## Relationship to Kernel

- **WatchLLM Orchestrator:** Configures the identity and policy bounds before the agent starts.
- **WatchLLM Kernel (Enforcer):** Reads the identity context provided by Orchestrator and enforces it during file-write operations.

## Links

- [WatchLLM Organization](https://github.com/WatchLLM)
- [Central Documentation](https://github.com/WatchLLM/docs)
- [watchllm.dev](https://watchllm.dev)
