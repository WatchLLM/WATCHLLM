# WatchLLM Benchmarks

```
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░  ░░░░  ░░░      ░░░        ░░░      ░░░  ░░░░  ░░  ░░░░░░░░  ░░░░░░░░  ░░░░  ░
▒  ▒  ▒  ▒▒  ▒▒▒▒  ▒▒▒▒▒  ▒▒▒▒▒  ▒▒▒▒  ▒▒  ▒▒▒▒  ▒▒  ▒▒▒▒▒▒▒▒  ▒▒▒▒▒▒▒▒   ▒▒   ▒
▓        ▓▓  ▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓  ▓▓▓▓▓▓▓▓        ▓▓  ▓▓▓▓▓▓▓▓  ▓▓▓▓▓▓▓▓        ▓
█   ██   ██        █████  █████  ████  ██  ████  ██  ████████  ████████  █  █  █
█  ████  ██  ████  █████  ██████      ███  ████  ██        ██        ██  ████  █
████████████████████████████████████████████████████████████████████████████████
```

*Ecosystem-wide performance and regression benchmarking.*

## Current status

Early design & specification phase. Subsystem boundary defined; codebase scaffolded.

## Overview

The `benchmarks` repository hosts the performance validation suites for the WatchLLM ecosystem. It is responsible for measuring parsing latencies, rule execution costs, and end-to-end write-path delays against large, real-world source files to ensure WatchLLM keeps its key performance target: **evaluating and block/allowing file saves in under 10 milliseconds**.

## Core Features

- **Ecosystem Stress Testing:** Benchmarks rule checking speed on heavy TSX/TS/JS repositories.
- **Latency Budget Enforcement:** Monitors regression curves to catch changes that exceed target ceilings.
- **Telemetry Analysis:** Compiles benchmarks to JSON schemas for local reporting.

## Relationship to Kernel

- **WatchLLM Benchmarks (Validation):** Measures execution times and provides baseline budget specifications.
- **WatchLLM Kernel (Target):** The target system being benchmarked and optimized.

## Non-goals

- **Static analysis engine:** `benchmarks` does not host rule definitions or compile ASTs; it imports the Kernel package to measure it.

## Installation

```bash
pip install -e .
```

## Usage

```bash
watchllm-benchmarks --help
watchllm-benchmarks run
python -m benchmarks --help
```

## Links

- [WatchLLM Organization](https://github.com/WatchLLM)
- [Central Documentation](https://github.com/WatchLLM/docs)
- [watchllm.dev](https://watchllm.dev)
