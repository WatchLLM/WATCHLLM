# OSS export automation setup

`.github/workflows/oss-sync.yml` exports the allowlisted tree to a deterministic
branch in `WatchLLM/watchllm-oss` and opens or updates a pull request. It never
pushes directly to public `main`.

## Required repository setup

1. Add a private-repository Actions secret named `OSS_SYNC_TOKEN`.
2. Use a fine-grained GitHub token scoped only to
   `WatchLLM/watchllm-oss`, with:
   - **Contents: Read and write** (push the automation branch)
   - **Pull requests: Read and write** (create/update the export PR)
   - **Workflows: Read and write** (the export includes
     `.github/workflows/ci.yml` and `.github/workflows/publish-kernel.yml`;
     GitHub rejects a push that creates or updates workflow files without this)
   - **Metadata: Read** (implicit)
3. Protect `main` in the public repository:
   - require pull requests;
   - require the public CI checks;
   - disallow force pushes and deletion;
   - require at least one human approval when another maintainer is available.

The token does not need administration, packages, issues, or access to any
other repository. Repository rules remain the enforcement boundary; the
workflow's private-repository `GITHUB_TOKEN` has read-only contents permission.

If the push fails with `refusing to allow a Personal Access Token to create or
update workflow ... without 'workflow' scope`, the Workflows permission is
missing. For a classic PAT, the equivalent is the `workflow` scope.

## Branch behavior

The generated branch is always `automation/oss-export`. Each run rebuilds it
from public `origin/main` and updates it with `--force-with-lease`. This keeps a
single reviewable PR without granting automation a path to push public `main`.
If branch rules apply to all branches, permit this token to update only the
`automation/oss-export` branch while retaining `main` protection.
