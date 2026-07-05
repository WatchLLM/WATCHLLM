# WatchLLM Context Docs

Canonical conceptual context for the WatchLLM ecosystem.

## Purpose

These documents define the shared conceptual baseline that implementation repos
must follow before adding subsystem-specific specifications.

## Documents

- `mission.md` - Why WatchLLM exists and what failure mode it prevents.
- `threat-model.md` - Core threat categories, examples, and deterministic rule mappings.
- `glossary.md` - Stable definitions for key terms used across repos.
- `language-support.md` - MVP language targets and rationale.
- `execution-model.md` - Exact local enforcement path and runtime behavior.

## Relationship to Repo-Level Docs

- `docs/context/*` is canonical for ecosystem-wide context.
- Subsystem repos may reference or summarize context but should not fork meaning.
