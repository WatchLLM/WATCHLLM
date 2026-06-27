# WatchLLM Reliability Harness

## 0) Purpose

This document defines the **reliability layer (Phase 6)** for WatchLLM. The goal of this layer is to provide an adversarial testing framework that stress-tests autonomous agents and the WatchLLM Kernel. 

The `reliability` harness simulates malicious prompts, tool abuse scenarios, and architectural violations to ensure the safety boundaries hold firm.

---

## 1) Scope

### In scope
* A Python CLI (`reliability-stress`) using `click`.
* A test suite definition system (likely YAML/JSON) to declare adversarial prompts and expected boundaries.
* Subprocess wrappers to execute target agents (like `aider`) under observation.
* Standardized test suites for:
  - **Prompt Injection:** Tricking the agent to leak secrets or ignore system prompts.
  - **Kernel Enforcement:** Deliberately requesting architectural violations to verify the Kernel blocks them.
  - **Tool Abuse:** Triggering infinite loops or dangerous shell commands.
* Quantitative safety scoring and reporting (e.g., JUnit XML exports for CI).

### Out of scope
* Modifying the WatchLLM Kernel (reliability only *tests* the kernel).
* Creating a new Agent (reliability orchestrates existing agents).
* Inline runtime monitoring (reliability is a dev/CI tool, not an always-on proxy).

---

## 2) Architecture Rules

### 2.1 The Black-Box Principle
The harness must treat the target agent as a black box. It provides inputs (prompts, mocked git repos) and evaluates outputs (shell commands executed, files modified, final stdout).

### 2.2 Suite Segregation
Tests must be logically grouped into independent suites (e.g., `PromptInjectionSuite`, `KernelEnforcementSuite`). The failure of one suite should not crash the runner.

### 2.3 Deterministic Scoring
Safety indices must be quantitative and deterministic. The framework should yield a bounded score (e.g., 0 to 100) based on binary pass/fail criteria for each adversarial scenario.

---

## 3) Implementation Order

1. **Skeleton & Runner**: Set up `click` CLI entrypoints.
2. **Suite Loader**: Parse adversarial test definitions from YAML files.
3. **Agent Orchestrator Interface**: Build the wrapper to execute subprocesses (e.g., `aider`) in an isolated temp directory.
4. **Prompt Injection Suite**: Implement the leak/jailbreak detection tests.
5. **Kernel Enforcement Suite**: Implement tests that verify `watchllm/kernel` intercepts bad writes.
6. **Tool Abuse Suite**: Implement infinite loop detection and shell command gating.
7. **Scoring Engine**: Aggregate suite results into a single safety index.
8. **CI/CD Reporter**: Export test results to JUnit XML and human-readable summaries.

---

## 4) Definition of Done
* A developer can run `reliability-stress run --suite all`.
* The harness spawns an agent, feeds it an adversarial prompt, and verifies whether the agent successfully violated the constraints.
* A summary report and a safety score are printed to the console.
