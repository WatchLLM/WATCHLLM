# WatchLLM Replay Context Documents

This `internal_docs/` folder contains the canonical specifications, architectures, and prompt templates for building the **WatchLLM Replay** observability suite.

### Documents

* `IMPORTANT.md`: Read this first. It defines the core rules, architecture constraints, and definition of done for the Replay layer.
* `PROMPT_TEMPLATE.md`: Contains the exact, scoped prompts to feed to an agent (in an 8-day progression) to systematically build the Replay layer without regressions or feature-creep.
* `../tasks.md`: A checklist tracking completion of the 8 tasks defined in the prompt template.

These documents ensure consistent context is maintained across multiple LLM agent sessions.
