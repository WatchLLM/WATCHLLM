# WATCHLLM — RULE SYSTEM

All enforcement rules are deterministic and evaluated through AST or explicit graph checks.

The LLM is never part of the rule decision.

---

## Enforcement Modes

### enforce

Violation = BLOCK

Used for write-path governance.

### shadow

Violation = WARN + LOG

Used for rollout, measurement, and false-positive discovery.

Shadow mode must be explicit. There must be no mixed implicit behaviour.

---

## endpoint_requires_auth

Any API handler that accesses the database must call `auth.verify()` before database access within the same function scope.

Required properties:

- function-scoped traversal
- sequential call ordering inside the function
- no global flattened call-array decisions
- no LLM inference

---

## input_validation_required

Request input must be validated before use.

Required properties:

- validation must occur before sensitive use
- rule must be deterministic
- no natural-language inference

---

## forbidden_imports

Modules cannot import restricted modules.

Required properties:

- import source must be parsed from AST
- restricted modules must be explicit
- no fuzzy package matching

---

## no_secrets_in_code

No hardcoded secrets allowed.

Required properties:

- explicit secret patterns only
- no probabilistic classification
- violations must include rule name and reason

---

## rate_limit_required

Public endpoints must implement rate limiting.

Required properties:

- endpoint detection must be deterministic
- rate-limit call or middleware must be explicit
- no LLM approval

---

## service_boundary

Modules cannot import forbidden modules or services.

Required properties:

- source module resolution must support custom roots and monorepos
- if source module cannot be determined safely, return no violation
- target module must be derived from import path deterministically
- allowed dependencies must be explicit

---

## Rule Properties

- deterministic
- explicit
- auditable
- scoped
- no heuristics for enforcement
- no LLM decisions
