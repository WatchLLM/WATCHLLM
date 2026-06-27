# Internal documentation (watchllm/runtime)

Agent-facing and planning context for the WatchLLM Runtime repository. These files are **not** public product docs.

## Layout

| File | Purpose |
|------|---------|
| `IMPORTANT.md` | Runtime spec: architecture rules, Rust core boundaries, JSON parity requirement |
| `PROMPT_TEMPLATE.md` | Copy-paste daily task prompts for agent sessions |
| `README.md` | This index |

## Public vs internal

- **`internal_docs/`** — planning and agent workflow (this directory)
- **`../docs` repo** — ecosystem-wide architecture, RFCs, and shared specs
- **Repo root** — `README.md` (public), `tasks.md` (active gate tracker)
