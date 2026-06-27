# WatchLLM Documentation Audit Specification (Docs Site)

This document defines the expected perfect state of the **WatchLLM Documentation** repository. It outlines the architecture, rules, interface contracts, and edge cases necessary to pass a complete verification run.

---

## 1. Purpose & Scope
The Docs repository is the central point of truth for WatchLLM's system design, specification, glossary, and roadmaps. It details the rules, schemas, CLI arguments, and boundaries that all other repositories (Kernel, Runtime, VS Code, Klyd, Replay) must follow. It contains only static markdown documentation and contains no executable code.

---

## 2. Expected Directory & File Layout
A perfect implementation must contain:
```
d:\watchllm\docs/
├── architecture/
│   ├── README.md                 # Architecture map list
│   └── system_boundaries.md      # Mermaid sequence diagrams of runtime boundaries
├── context/
│   ├── README.md
│   ├── mission.md                # Core purpose and agent threat context
│   ├── threat-model.md           # Secret leaks, bypasses, false-positive metrics
│   ├── glossary.md               # Standardized terms (shadow mode, AST node)
│   ├── language-support.md       # TS/JS focus rationale
│   └── execution-model.md        # Local-first, pre-write save path details
├── specs/
│   ├── README.md
│   └── cli_contracts.md          # CLI parameters and JSON contract schemas
├── RFCs/
│   ├── README.md
│   └── rfc-001-wasm-compilation.md # Durable reasoning for moving to Rust/Wasm
├── roadmap/
│   ├── README.md
│   └── master_roadmap.md         # 8 product phases and timelines
├── README.md                     # Main entrypoint
└── tasks.md                      # Active gate checklist
```

---

## 3. Core Content & Quality Rules

### 3.1 GFM Compliance & Mermaid Diagrams
- All documents must be written in valid GitHub Flavored Markdown (GFM).
- Architecture maps must contain valid, rendering `mermaid` diagrams showing sequential events (e.g. editor Save -> VS Code Hook -> subprocess spawn -> Kernel AST Parse -> allow/block decision).

### 3.2 Canonical Documentation Invariant
- Any interface specification (such as CLI flags or JSON response schemas) documented in this repository is the strict source of truth. Implementing code must match these specs.

---

## 4. Critical Edge Cases & Verification Scenarios

| Edge Case | Expected Perfect Behavior |
|---|---|
| **Broken Markdown Links** | Document links (e.g., `[Glossary](../context/glossary.md)`) must be verified relative to the file root. Broken or circular links must not exist. |
| **Mermaid Syntax Failure** | Diagrams must not use invalid HTML labels or syntax that prevents rendering in VS Code or GitHub previews. |
| **Out-of-date Specs** | When CLI arguments are updated in `kernel/`, the specs in `docs/specs/cli_contracts.md` must be updated concurrently to prevent configuration divergence. |

---

## 5. Verification Checklist
To verify Docs site compliance, run:
1. **Link Verification**: Audit all internal relative links in the docs files to ensure there are no broken references:
   - Verify links in [architecture/system_boundaries.md](file:///d:/watchllm/docs/architecture/system_boundaries.md)
   - Verify links in [specs/cli_contracts.md](file:///d:/watchllm/docs/specs/cli_contracts.md)
2. **Mermaid Rendering**: Open [architecture/system_boundaries.md](file:///d:/watchllm/docs/architecture/system_boundaries.md) and confirm that the Mermaid diagrams compile and display execution flows cleanly.
3. **Glossary Alignment**: Check [context/glossary.md](file:///d:/watchllm/docs/context/glossary.md) to confirm all terms are stable.
