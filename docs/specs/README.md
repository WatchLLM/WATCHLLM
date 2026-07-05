# WatchLLM Specifications

Machine-level interfaces and protocol contracts for WatchLLM integration.

## Specifications

- **CLI Contract:** Command flag conventions, exit codes, and standard stdin piping constraints.
- **Reporting Contract:** The JSONL schema for local violation logging and event structures.
- **Parser Abstraction:** The normalized AST query interfaces and language bindings.

## Context Prerequisites

Before writing or revising specs, align with canonical context docs in
[`../context/`](../context/README.md):

- [Mission](../context/mission.md)
- [Threat Model](../context/threat-model.md)
- [Glossary](../context/glossary.md)
- [Language Support](../context/language-support.md)
- [Execution Model](../context/execution-model.md)
