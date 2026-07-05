# WatchLLM Reliability

```
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░  ░░░░  ░░░      ░░░        ░░░      ░░░  ░░░░  ░░  ░░░░░░░░  ░░░░░░░░  ░░░░  ░
▒  ▒  ▒  ▒▒  ▒▒▒▒  ▒▒▒▒▒  ▒▒▒▒▒  ▒▒▒▒  ▒▒  ▒▒▒▒  ▒▒  ▒▒▒▒▒▒▒▒  ▒▒▒▒▒▒▒▒   ▒▒   ▒
▓        ▓▓  ▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓▓▓▓        ▓▓  ▓▓▓▓▓▓▓▓  ▓▓▓▓▓▓▓▓        ▓
█   ██   ██        █████  █████  ████  ██  ████  ██  ████████  ████████  █  █  █
█  ████  ██  ████  █████  ██████      ███  ████  ██        ██        ██  ████  █
████████████████████████████████████████████████████████████████████████████████
```

*Stress-testing and adversarial evaluation framework for autonomous coding agents.*

## Current status

Early design & specification phase. Subsystem boundary defined; codebase scaffolded.

## Overview

The `reliability` repository hosts the test harness and stress framework for WatchLLM. It evaluates AI agents under adversarial conditions, running prompt-injection attacks, testing for compliance with tool-abuse limits, detecting hallucinations, and validating that policies and write-path rule systems cannot be bypassed by malicious or misconfigured instructions.

## Core Features

- **Adversarial Evaluation:** Standardized suites that attempt to trick agents into leaking secrets or violating boundary rules.
- **Hallucination Detection:** Monitors generated output to detect nonexistent dependencies or configuration keys.
- **Tool Abuse Gating:** Stress tests agent orchestration models against rate limits, infinite tool execution loops, and dangerous syscalls.
- **Reliability Scoring:** Emits quantitative safety indices for agents based on compliance with structural and execution guidelines.

## Relationship to Kernel

- **WatchLLM Reliability (Stress Testing):** Tests agent limits externally by generating bypass payloads and attempting to save them.
- **WatchLLM Kernel (Enforcement):** Serves as the target defender. If an adversarial test bypasses the Kernel's rules, it marks a test failure.

## Non-goals

- **Inline Governance:** `reliability` does not intercept write paths at runtime; it is a testing and stress suite run in dev/CI.
- **Code Generation:** `reliability` does not write code for production applications.

## Installation

```bash
pip install -e .
```

## Usage

```bash
reliability-stress --help
python -m reliability.stress --help
```

## Links

- [WatchLLM Organization](https://github.com/WatchLLM)
- [Central Documentation](https://github.com/WatchLLM/docs)
- [watchllm.dev](https://watchllm.dev)
