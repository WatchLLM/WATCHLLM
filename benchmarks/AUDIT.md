# WatchLLM Benchmarks Audit Specification (Benchmarks Suite)

This document defines the expected perfect state of the **WatchLLM Benchmarks** repository. It outlines the architecture, rules, interface contracts, and edge cases necessary to pass a complete verification run.

---

## 1. Purpose & Scope
The Benchmarks Suite is a Python-based utility designed to verify the performance constraints of the WatchLLM Kernel. Its main task is to measure execution latency for file reading, AST parsing, rule matching, and end-to-end evaluation, ensuring the total overhead remains under the target 10ms threshold. It does not implement active security checks or write-path blocking.

---

## 2. Expected Directory & File Layout
A perfect implementation must contain:
```
d:\watchllm\benchmarks/
├── src/
│   └── benchmarks/
│       ├── __init__.py           # Package exports
│       ├── cli.py                # Click CLI command definitions
│       └── suites/                # Timing logic modules
│           ├── __init__.py
│           ├── loader.py             # File and size-indexed corpus loader
│           ├── parser_benchmarks.py  # Measures raw tree-sitter parser speed
│           ├── rule_benchmarks.py    # Measures isolated rule traversal speed
│           └── e2e_benchmarks.py     # Measures aggregate save-path latency
├── pyproject.toml                # Build configuration
└── tasks.md                      # Active gate checklist
```

---

## 3. Core Component Responsibilities & Constraints

### A. The 10ms Rule Constraint
- The sum of file loading, AST parsing, and rule evaluation must not exceed 10ms on a single CPU core for a standard 1000-line JS/TS file.
- The benchmark runner must calculate P50, P90, and P99 latencies to identify cold-start spikes and parser performance drops.

### B. Clean Imports (No Mocks)
- Timing tests must import and test the actual `watchllm_kernel` modules directly. Mocks are not permitted to ensure latency measurements represent real-world execution.

### C. File Corpus Loader (`loader.py`)
- Automatically generates or pulls sample JS/TS files of various sizes (100 lines, 500 lines, 1000 lines, 5000 lines) to map file size to processing time.

---

## 4. CLI & JSON Reporting Contracts

### Command Structure
```bash
watchllm-benchmarks run [OPTIONS]
```
Options:
- `-o, --output <path>`: Destination path to write the JSON benchmark report.
- `-c, --count <n>`: Number of iterations per benchmark run (default: 100).

### JSON Output Schema
```json
{
  "timestamp": "2026-06-21T14:52:34Z",
  "system_info": {
    "cpu": "Intel...",
    "os": "Windows..."
  },
  "results": {
    "parser_latency_1k_lines": {
      "p50_ms": 1.4,
      "p99_ms": 3.8,
      "mean_ms": 1.6,
      "min_ms": 1.2,
      "max_ms": 5.2
    },
    "rule_evaluation_latency": {
      "p50_ms": 2.1,
      "p99_ms": 4.5
    },
    "e2e_latency": {
      "p50_ms": 3.8,
      "p99_ms": 8.9
    }
  }
}
```

---

## 5. Critical Edge Cases & Error Recovery

| Edge Case | Expected Perfect Behavior |
|---|---|
| **Cold Starts** | The first execution run of Python and Tree-sitter imports is slow. The benchmark suite must warm up the parser with 5-10 discard iterations before starting official time measurements. |
| **Gigantic Files** | Files > 50,000 lines can cause memory spikes. The loader must cap the max benchmark size or report memory constraints, logging warning messages instead of crashing the run. |
| **Invalid Language Extension** | If a file containing binary or non-JS/TS data is loaded, the parser benchmark must record it as a failure or skip it, instead of throwing an unhandled interpreter exception. |
| **Process Interruption** | If the host system experiences CPU throttling during a run, P99 values will spike. The timing engine should identify statistical outliers and report them separately. |

---

## 6. Verification Checklist
To confirm Benchmarks compliance, run:
1. **CLI Execution**: Check basic CLI responsiveness:
   ```bash
   watchllm-benchmarks --help
   ```
2. **Standard Benchmark Run**: Execute the timing suite on standard targets:
   ```bash
   watchllm-benchmarks run --count 100 -o report.json
   ```
   Verify that P50 and P99 metrics are successfully logged to the console and written to `report.json`.
3. **Parity Check**: Confirm that `watchllm_kernel` imports are verified and no mock frameworks are loaded.
