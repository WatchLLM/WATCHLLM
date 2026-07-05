# WatchLLM Docs

## 0) Purpose

This repository holds the central architectural specifications, RFCs, design docs, and master roadmap for the WatchLLM ecosystem. It defines interfaces and guidelines to prevent architectural entropy.

---

## 1) Scope

### In scope
* Markdown design documents (`architecture/`).
* Interface and JSON payload specifications (`specs/`).
* Request for Comments logic for major design decisions (`RFCs/`).
* Sequential product phases (`roadmap/`).
* Glossary and core context (`context/`).

### Out of scope
* Executable code.
* Runtime packages.

---

## 2) Architecture Rules

### 2.1 The Documentation Truth Rule
Any schema, CLI argument, or architecture design written here is the strict source of truth for the rest of the WatchLLM codebase. 

### 2.2 Format
All documents must be written in GitHub Flavored Markdown (GFM). Use mermaid diagrams where appropriate for architecture.

---

## 3) Implementation Order

1. **Context & Glossary**: Seed the central terminology so all agents speak the same language.
2. **Architecture**: Map out the high-level diagrams and runtime boundaries.
3. **Specs**: Document the machine-level CLI arguments and JSON schemas.
4. **Roadmap**: Outline the sequential phases (Kernel, Runtime, VSCode, Klyd, etc.).

---

## 4) Definition of Done
* Developers (and agents) can read the markdown files to perfectly understand the system boundaries without reading the source code.
