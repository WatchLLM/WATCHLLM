# WatchLLM VS Code Extension Tasks

## Task 01 — Build the repo skeleton

Status: Complete

Gate:
- `npm run compile` succeeds.
- Extension can be launched in the Extension Development Host without crashing.

Scope:
- `package.json` with correct activation events (`onLanguage:javascript`, `onLanguage:typescript`)
- `tsconfig.json`
- `src/extension.ts` stub
- Minimal `.vscode/launch.json` for debugging

Non-goals:
- Save hook logic
- Subprocesses
- UI

---

## Task 02 — Kernel configuration layer

Status: Complete

Gate:
- Settings show up in the VS Code Settings UI under a "WatchLLM" category.
- Changing a setting in `settings.json` is accurately reflected in the extension's runtime config object.

Scope:
- `watchllm.pythonPath`
- `watchllm.kernelPath`
- `watchllm.mode`

Non-goals:
- Subprocesses
- Save interception

---

## Task 03 — Kernel subprocess executor

Status: Complete

Gate:
- Unit/integration tests can successfully invoke a dummy script returning 0/1/2 and parse the stdout as JSON.
- Process timeouts are enforced.

Scope:
- Subprocess execution via `child_process`
- stdin passing
- json stdout parsing
- Edge case handling (timeout, crash)

Non-goals:
- Save interception
- Diagnostics UI

---

## Task 04 — Save interception hook

Status: Complete

Gate:
- A dummy kernel script returning exit code 1 successfully blocks the file save in the editor.
- Returning 0 successfully allows it.

Scope:
- `workspace.onWillSaveTextDocument`
- `event.waitUntil`
- Promise chaining

Non-goals:
- Diagnostics UI
- End-to-end kernel testing

---

## Task 05 — Violation mapping & diagnostics

Status: Complete

Gate:
- Kernel JSON cleanly maps to editor warnings in the Problems panel.
- Clear error notification is presented to the user.

Scope:
- VS Code `Diagnostic` API mapping
- `DiagnosticCollection`
- Error notifications

Non-goals:
- Modifying the kernel contract

---

## Task 06 — End-to-end integration testing

Status: Complete

Gate:
- Saving a TS file with a known hardcoded secret actually blocks the save and shows a squiggle via the real python kernel.
- Graceful degradation works when kernel is uninstalled.

Scope:
- Local kernel resolution
- Graceful degradation (fail-open)
- Real file testing

Non-goals:
- Rewriting core logic

---

## Task 07 — Packaging & Release prep

Status: Complete

Gate:
- `vsce package` creates a `.vsix` file.
- The `.vsix` can be successfully installed into VS Code locally.

Scope:
- Bundler setup (`esbuild` or `webpack`)
- `.vscodeignore`
- `vsce`

Non-goals:
- New features
