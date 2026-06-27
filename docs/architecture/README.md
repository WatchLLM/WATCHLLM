# WatchLLM System Architecture

Index of architectural documents for the WatchLLM ecosystem.

## Documents

- **System Diagram:** Overview of system layers (Kernel, klyd, Replay, Runtime).
- **Data Flow:** Analysis of save events, AST parsing, evaluation, and logging.
- **Runtime Boundaries:** Explicit definitions of what each subsystem is allowed to know to maintain separation of concerns.

## Context Prerequisites

Architecture docs should stay consistent with canonical context docs in
[`../context/`](../context/README.md):

- [Mission](../context/mission.md)
- [Threat Model](../context/threat-model.md)
- [Glossary](../context/glossary.md)
- [Language Support](../context/language-support.md)
- [Execution Model](../context/execution-model.md)
