# Execution Model

## Core Principle

Enforcement decisions run locally and do not depend on network availability.

## Enforcement Path (Exact Order)

1. Editor or CLI host receives source content at save/evaluate time.
2. Host invokes kernel evaluation (stdin or file path flow).
3. Kernel parses source into AST for the selected language.
4. Kernel runs deterministic rules in defined order.
5. Kernel reduces rule decisions into a single allow or block decision.
6. Host applies decision before write completion.
7. If blocked, host surfaces structured violation output.
8. Optional local log entry is written for blocked events.

## Runtime Guarantees

- Local execution only for the critical enforcement path.
- No remote call required to determine allow or block.
- Enforce and shadow modes share the same rule evaluation path.

## Network Unavailability Behavior

If network is unavailable, enforcement behavior is unchanged because the
decision path is local-first and offline-capable by design.

## Host Integration Paths

- Editor integration path: pre-save hook invokes kernel contract.
- CLI fallback path: direct user or automation invocation for local checks.
