# WatchLLM VS Code Extension Audit Specification (Phase 3 — Editor Integration)

This document defines the expected perfect state of the **WatchLLM VS Code Extension** (Phase 3). It outlines the architecture, rules, interface contracts, and edge cases necessary to pass a complete verification run.

---

## 1. Purpose & Scope
The VS Code Extension is the editor-side host integration. It intercepts save commands in real-time, queries the WatchLLM engine (Python CLI, Rust CLI, or Wasm runner), and enforces security boundaries by blocking writes or rendering editor squiggles (Diagnostics). It does not write AST parsing rules itself; it acts purely as an enforcement interface.

---

## 2. Expected Directory & File Layout
A perfect implementation must contain:
```
d:\watchllm\vscode\
├── src/
│   ├── extension.ts              # Extension activation & command registry
│   ├── config.ts                 # Reading & normalizing user workspace settings
│   ├── saveHook.ts               # onWillSaveTextDocument interception logic
│   ├── kernelExecutor.ts         # Subprocess launcher & Wasm adapter
│   └── diagnostics.ts            # Rendering problem list entries & red squiggles
├── test/
│   ├── suite/
│   │   ├── index.ts              # Mocha test runner setup
│   │   ├── extension.test.ts     # Save hooks & configuration integration tests
│   │   └── diagnostics.test.ts   # Diagnostic parser tests (flat & nested JSON)
│   └── runTest.ts                # VS Code instance spawner for testing
├── package.json                  # Extension metadata, activationEvents & contributions
├── tsconfig.json                 # TypeScript compiler configuration
├── esbuild.js                    # Production asset bundler
└── tasks.md                      # Active gate checklist
```

---

## 3. Core Component Responsibilities & Contracts

### A. Save Hook Interceptor (`saveHook.ts`)
- Must hook into `workspace.onWillSaveTextDocument`.
- Must block the save flow synchronously using `event.waitUntil()` until the kernel returns a decision.
- Only intercepts Javascript (`javascript`, `javascriptreact`) and TypeScript (`typescript`, `typescriptreact`) files.

### B. Kernel Executor (`kernelExecutor.ts`)
- Spawns the kernel process or invokes the loaded Wasm module.
- Must pipe the **active, unsaved document buffer** from memory to the engine's `stdin` (instead of reading from disk).
- Implements a strict execution timeout (default: 800ms) to ensure the developer's save is never locked indefinitely.

### C. Diagnostics Engine (`diagnostics.ts`)
- Processes the JSON result from the executor.
- Parses violations and highlights code segments using `vscode.Diagnostic` objects linked to a `DiagnosticCollection`.
- Must support contract resolution: handling both flat and nested JSON violation reports (Python `rule_results` format vs Rust flat format).
- Must clear diagnostics on the target file when it passes evaluation.

---

## 4. UI & Configuration Contracts

### Settings Contributions (`package.json`)
- `watchllm.pythonPath` (type: `string`, default: `"python"`): Path to the Python interpreter.
- `watchllm.kernelPath` (type: `string`, default: `"-m watchllm_kernel check"`): Kernel CLI execution flags.
- `watchllm.mode` (type: `string`, default: `"enforce"`, options: `"enforce"`, `"shadow"`).

### Graceful Degradation (Fail-Open)
- If the kernel process crashes, fails to spawn, runs out of memory, or takes longer than the timeout, the extension must **fail-open** (allow the save to proceed).
- The user must be notified of the failure via a standard VS Code alert warning (`window.showWarningMessage`), indicating the local security guard is temporarily disabled.

---

## 5. Critical Edge Cases & Error Recovery

| Edge Case | Expected Perfect Behavior |
|---|---|
| **Process Hangs** | If the child process gets stuck (e.g. infinite loop in parser), the 800ms timeout must kill the process and allow the save (fail-open) with a warning prompt. |
| **Path Traversal / Drive Letters** | Under Windows, file paths passed to the CLI must maintain correct formatting (slashes normalized) so the kernel can match boundaries. |
| **Unsaved Buffer Changes** | The code checked must be the active memory buffer, not the file on disk. If checking the disk file, changes made by autocomplete/copilot just before save will escape analysis. |
| **Workspace Disruption** | If the user disables the extension or changes mode to `shadow`, existing Diagnostics (red squiggles) must be removed immediately from active files. |

---

## 6. Verification Checklist
To confirm VS Code Extension compliance, run:
1. **Compilation**: Bundle the extension assets:
   ```bash
   npm run compile
   ```
2. **Automated Testing**: Run extension host tests:
   ```bash
   npm test
   ```
3. **Save Blocking Check**: Save a file containing a hardcoded stripe secret key (`sk_live_...`) in enforce mode. Confirm the save fails and a squiggle displays.
4. **Shadow Mode Check**: Set `watchllm.mode` to `"shadow"`, save the secret file, and confirm the save is successful but the squiggle still displays in the Problems tab.
