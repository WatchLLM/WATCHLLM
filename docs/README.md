# WatchLLM Documentation

*Central architectural specifications, RFCs, design docs, and master roadmap for the WatchLLM ecosystem.*

## Current status

Documentation complete. All four task gates are met: context glossary, architecture maps with Mermaid diagrams, CLI specification contracts, and the 8-phase master roadmap.

## Overview

The `docs` repository is the central point of truth for WatchLLM's system design and specification. It preserves the core philosophy:
> Agents are probabilistic. Infrastructure cannot be.

It defines interfaces and guidelines to prevent architectural entropy, uncontrolled abstraction, and agent-induced system incoherence.

## Directory Structure

This repository is structured into distinct documentation namespaces:

- **[architecture/](architecture/README.md):** High-level system design diagrams, runtime boundaries, and ecosystem data flows.
- **[specs/](specs/README.md):** Machine-level interface contracts (CLI arguments, reporting JSON structures, telemetry formats).
- **[RFCs/](RFCs/README.md):** Durable written reasoning for major design decisions (e.g. storage models, Wasm integration, event structures).
- **[roadmap/](roadmap/README.md):** The sequential product phases, timelines, and deliverables checklist.
- **[context/](context/README.md):** Canonical mission, threat model, glossary, language support, and execution model.

## Relationship to Kernel

- **WatchLLM Documentation (Guidelines):** Explains how components must behave, providing the rules and conventions.
- **WatchLLM Kernel (Implementation):** Follows the boundaries and CLI schemas specified in these documents.

## Non-goals

- **Executable Code:** Contains only design documentation and specification markdown files. No executable runtime packages are stored here.

## Links

- [WatchLLM Organization](https://github.com/WatchLLM)
- [watchllm.dev](https://watchllm.dev)
