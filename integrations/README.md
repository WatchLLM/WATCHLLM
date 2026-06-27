# WatchLLM Integrations

Drop-in integration templates for common CI/CD workflows.

## GitHub Actions

Copy `github/action.yml` to your repo as `.github/workflows/watchllm.yml`.
The action checks all changed JS/TS files on pull requests.

## Pre-commit Hook

Add `pre-commit-hooks.yaml` reference to your `.pre-commit-config.yaml`.

```yaml
repos:
  - repo: https://github.com/watchllm/watchllm
    rev: v0.1.0
    hooks:
      - id: watchllm-kernel
```

Then run `pre-commit install`.
