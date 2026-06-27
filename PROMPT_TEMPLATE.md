⇒ WatchLLM Productization — Prompt Pack

Copy **one full day block** below into your agent session. Each block uses the same template to tackle the critical architectural gaps identified in the gap analysis.

**Repo:** `watchllm` (local: `d:\watchllm`)

---

⇒ Day 01 — Task 01: Create JSON Schema for `.watchllm.yaml`

⇒ Task Instructions

Today's task:
**PRODUCTIZATION Task 01 — Define the unified configuration schema**

Create the JSON Schema definition for the new project-level configuration file `.watchllm.yaml` in `schemas/schemas/v1/config.json`.
It should define the schema for rule configurations:
- `boundary`: enabled, severity, map (forbidden/allowed edges)
- `forbidden_imports`: enabled, severity, modules, forbidden_prefixes, allowed_relative_prefixes
- `secrets` and `auth_flow`: enabled, severity

Today's gate:
- The JSON schema file is syntactically valid JSON.
- It covers all configuration overrides needed by the 4 core rules.

> Scope Constraints

Only work on:
- `schemas/schemas/v1/config.json`
- Updating schema documentation or READMEs if necessary.

Do NOT:
- write Python code to load the schema yet
- refactor existing rules

> Required Outputs

You must:
- implement the task narrowly
- explain architectural decisions
- update internal docs if needed

> Validation Requirements

Before finishing:
- ensure valid JSON output

> Reporting Format

At the end, report:
1. Files changed
2. What changed
3. Gate status

---

⇒ Day 02 — Task 02: Implement `config_loader.py` in Kernel

⇒ Task Instructions

Today's task:
**PRODUCTIZATION Task 02 — Build the configuration loader**

Implement a robust configuration loader in `kernel/src/watchllm_kernel/config_loader.py` that can:
- Find `.watchllm.yaml` by walking up the directory tree from a given start path.
- Parse the YAML file safely.
- Return a configuration dictionary.

Ensure `pyyaml` is added to `pyproject.toml` dependencies.

Today's gate:
- `pyyaml` is in `pyproject.toml`.
- `config_loader.py` can discover and load a `.watchllm.yaml` file.
- It returns an empty dict if the file is not found (fail-open).

> Scope Constraints

Only work on:
- `kernel/src/watchllm_kernel/config_loader.py`
- `kernel/pyproject.toml`
- Unit tests for the config loader

Do NOT:
- integrate the config loader into the rules yet

> Required Outputs

You must:
- write unit tests for the loader
- explain potential failure points

> Validation Requirements

Before finishing:
- run `pytest` to ensure loader works
- verify fail-open behavior

> Reporting Format

At the end, report:
1. Files changed
2. What changed
3. Gate status

---

⇒ Day 03 — Task 03: Refactor Kernel Rules for Config Overrides

⇒ Task Instructions

Today's task:
**PRODUCTIZATION Task 03 — Refactor rules to accept dynamic config**

Update the existing rules to accept configuration parameters instead of relying exclusively on hardcoded default lists.
- `BoundaryRule.__init__`: Accept `boundary_map` and convert JSON/YAML lists to tuples for compatibility.
- `ForbiddenImportRule.__init__`: Accept lists/sets and convert them to frozensets.
- Update `cli.py` to instantiate rules with these overrides.

Today's gate:
- Rules still default to hardcoded constants if no config is provided.
- If config is provided, the rules override their behavior correctly.
- All existing tests pass.

> Scope Constraints

Only work on:
- `kernel/src/watchllm_kernel/rules/boundary.py`
- `kernel/src/watchllm_kernel/rules/forbidden_imports.py`
- `kernel/tests/` rule tests

Do NOT:
- change the CLI entrypoint argument parser

> Required Outputs

You must:
- update tests to prove overrides work
- ensure deterministic output

> Validation Requirements

Before finishing:
- run all kernel tests

> Reporting Format

At the end, report:
1. Files changed
2. What changed
3. Gate status

---

⇒ Day 04 — Task 04: Refactor Kernel CLI to Load Config

⇒ Task Instructions

Today's task:
**PRODUCTIZATION Task 04 — Wire config loader to the CLI**

Update `kernel/src/watchllm_kernel/cli.py` so that the `main()` function:
- Resolves the directory of the file being evaluated.
- Uses `config_loader.load_config(start_path)` to get the config.
- Passes the config into `build_default_rules()`.

Today's gate:
- The `watchllm-kernel check` command loads the `.watchllm.yaml` if present in the target directory tree.
- The CLI doesn't crash if the config is invalid or missing.

> Scope Constraints

Only work on:
- `kernel/src/watchllm_kernel/cli.py`

Do NOT:
- modify rule evaluation logic

> Required Outputs

You must:
- verify the CLI still works for `stdin` and `filepath` modes

> Validation Requirements

Before finishing:
- execute a manual test using `watchllm-kernel check` on a file with and without a custom config

> Reporting Format

At the end, report:
1. Files changed
2. What changed
3. Gate status

---

⇒ Day 05 — Task 05: Build `watchllm` Top-Level CLI Wrapper

⇒ Task Instructions

Today's task:
**PRODUCTIZATION Task 05 — Unified Entry Point**

Create a new top-level Python package (e.g., `cli/` at the root, or within the kernel package) that exposes a unified `watchllm` command.
It should support:
- `watchllm init`: Generates a default `.watchllm.yaml` in the current directory.
- `watchllm evaluate`: Wraps the kernel evaluation.
- `watchllm status`: Reports installation status of klyd, kernel, and runtime.

Today's gate:
- Running `watchllm --help` shows the unified commands.
- `watchllm init` drops a valid YAML config.

> Scope Constraints

Only work on:
- The new `cli/` wrapper or top-level CLI script.
- Entrypoint definitions in `pyproject.toml`.

Do NOT:
- rewrite the kernel engine

> Required Outputs

You must:
- implement subcommands clearly
- write unit tests for `init`

> Validation Requirements

Before finishing:
- run the CLI commands manually to verify behavior

> Reporting Format

At the end, report:
1. Files changed
2. What changed
3. Gate status

---

⇒ Day 06 — Task 06: Build Monorepo Installer Script

⇒ Task Instructions

Today's task:
**PRODUCTIZATION Task 06 — Installer Bootstrapper**

Create a `bootstrap.py` script in the root directory that acts as a monorepo installer.
It should:
- `pip install -e .` for python components (kernel, klyd, orchestrator).
- `cargo build --release` for the rust runtime.
- `npm install` for node components (vscode, replay).

Today's gate:
- A new developer can clone the repo and run `python bootstrap.py` to get a fully working environment.
- The script handles missing prerequisites (e.g. complains clearly if `cargo` is not installed).

> Scope Constraints

Only work on:
- `d:\watchllm\bootstrap.py`

> Required Outputs

You must:
- ensure cross-platform compatibility (Windows and Unix paths/shell execution)

> Validation Requirements

Before finishing:
- run the script on the current machine and ensure no errors

> Reporting Format

At the end, report:
1. Files changed
2. What changed
3. Gate status

---

⇒ Day 07 — Task 07: Create CI/CD Integration Templates

⇒ Task Instructions

Today's task:
**PRODUCTIZATION Task 07 — CI/CD Templates**

WatchLLM needs to be easily adopted by teams. Create standard integration templates.
- Create `integrations/github/action.yml` for a reusable GitHub Action that runs `watchllm evaluate`.
- Create `integrations/pre-commit-hooks.yaml` to define a pre-commit hook that uses the WatchLLM kernel.

Today's gate:
- The GitHub action syntax is valid.
- The pre-commit hook definition maps to the kernel entrypoint.

> Scope Constraints

Only work on:
- `integrations/` directory
- Documentation on how to use these templates

> Required Outputs

You must:
- write clear comments in the YAML files

> Validation Requirements

Before finishing:
- validate YAML syntax

> Reporting Format

At the end, report:
1. Files changed
2. What changed
3. Gate status

---

⇒ Day 08 — Task 08: Refactor VS Code Extension for Rust Runtime

⇒ Task Instructions

Today's task:
**PRODUCTIZATION Task 08 — Rust Runtime Integration**

The VS Code extension currently spawns the Python kernel (`watchllm-kernel`). Refactor `vscode/src/kernelExecutor.ts` to spawn the Rust `watchllm-cli` (or WASM) to improve latency.
If the Rust CLI is not found, fallback to Python.

Today's gate:
- Extension compiles successfully.
- `kernelExecutor.ts` correctly identifies and spawns the Rust executable from the `runtime/` folder.

> Scope Constraints

Only work on:
- `vscode/src/kernelExecutor.ts`
- VS Code configuration settings if an override flag is needed

> Required Outputs

You must:
- ensure the JSON output parsing works seamlessly since Rust and Python share the same schema

> Validation Requirements

Before finishing:
- run `npm run build` in the `vscode/` folder

> Reporting Format

At the end, report:
1. Files changed
2. What changed
3. Gate status
