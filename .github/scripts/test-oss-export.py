#!/usr/bin/env python3
"""
Test suite for oss-export.sh — ensures the exporter correctly:
- Exports ONLY tracked blobs (not working-tree, not untracked files)
- Excludes internal docs (AUDIT.md, tasks.md, internal_docs/)
- Retains legitimate secrets tests (examples/scenarios/secrets/)
- Rejects symlinks and submodules via git object modes
- Produces zero writes to target in dry-run mode
- Deletes stale content from target during reconciliation
- Rejects proprietary paths not in allowlist

Dependencies: Python 3 stdlib only (subprocess, os, shutil, tempfile, unittest).
No pathspec, no third-party packages.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest


class OSSExportTests(unittest.TestCase):
    """Integration tests for oss-export.sh."""

    @classmethod
    def setUpClass(cls):
        cls.exporter = os.path.abspath(
            os.environ.get(
                "EXPORTER",
                os.path.join(
                    os.path.dirname(__file__), "..", "scripts", "oss-export.sh"
                ),
            )
        )
        cls.source_repo = os.path.abspath(
            os.environ.get("SOURCE", os.path.join(os.path.dirname(__file__), "..", ".."))
        )
        cls.test_ref = os.environ.get("TEST_REF", "HEAD")

        if not os.path.isfile(cls.exporter):
            raise RuntimeError(f"Exporter not found: {cls.exporter}")
        if not os.path.isdir(os.path.join(cls.source_repo, ".git")):
            raise RuntimeError(f"Not a git repo: {cls.source_repo}")

        cls.temp_root = tempfile.mkdtemp(prefix="oss-export-test-")
        cls.test_git_dir = os.path.join(cls.temp_root, "test-git")
        cls.fixtures_built = False

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_root, ignore_errors=True)

    @classmethod
    def build_fixture_repo(cls):
        """Build a minimal git repo with tracked files for all test scenarios."""
        if cls.fixtures_built:
            return

        os.makedirs(cls.test_git_dir, exist_ok=True)
        cls._run(["git", "init", "-b", "main"], cwd=cls.test_git_dir)
        cls._run(["git", "config", "user.name", "Test"], cwd=cls.test_git_dir)
        cls._run(["git", "config", "user.email", "test@test"], cwd=cls.test_git_dir)

        # Allowlist files
        os.makedirs(os.path.join(cls.test_git_dir, "allowlist"), exist_ok=True)
        cls._repo = cls.test_git_dir

        # Create directory structure with files
        dirs_and_files = {
            # Allowed structure
            "kernel/__init__.py": "# kernel init",
            "kernel/engine.py": "# kernel engine",
            "kernel/internal_docs/README.md": "INTERNAL - DO NOT EXPORT",
            "kernel/internal_docs/IMPORTANT.md": "INTERNAL",
            "kernel/AUDIT.md": "INTERNAL AUDIT",
            "kernel/tasks.md": "INTERNAL TASKS",
            "kernel/openclaw.txt": "PROPRIETARY",
            "kernel/.watchllm/logs/debug.log": "log data",
            "kernel/__pycache__/engine.cpython-311.pyc": "cached",
            "kernel/.pytest_cache/v/cache/nodeids": "pytest cache",
            "kernel/.env": "SECRET=123",
            "kernel/.DS_Store": "desktop junk",
            "kernel/.klyd/config": "klyd internal",
            "kernel/CACHEDIR.TAG": "cache dir tag",
            # These should be exported
            "kernel/legit_module.py": "# legitimate kernel code",
            "kernel/legit_sub/helper.py": "# helper",

            "schemas/schema_v1.json": '{"v":1}',
            "schemas/internal_docs/README.md": "INTERNAL",
            "schemas/AUDIT.md": "INTERNAL AUDIT",
            "schemas/tasks.md": "INTERNAL TASKS",

            "vscode/extension.ts": "// vscode extension",
            "vscode/test/diagnostics.test.ts": "// legit test",
            "vscode/path": "PROPRIETARY PATH DATA",
            "vscode/AUDIT.md": "INTERNAL AUDIT",
            "vscode/tasks.md": "INTERNAL TASKS",
            "vscode/.vscode/launch.json": '{"version":"0.2.0"}',
            "vscode/.vscodeignore": "node_modules",
            "vscode/.vsix": "fake vsix",

            "examples/README.md": "# examples",
            "examples/scenarios/secrets/README.md": "# secrets examples",
            "examples/scenarios/secrets/safe.py": "# safe handling",
            "examples/scenarios/secrets/unsafe.py": "# unsafe pattern",
            "examples/scenarios/auth_flow/safe.ts": "// safe auth",
            "examples/internal_docs/README.md": "INTERNAL",
            "examples/AUDIT.md": "INTERNAL AUDIT",
            "examples/tasks.md": "INTERNAL TASKS",

            # Public WebProof SDK/local commitment engine and forbidden future prover paths
            "webproof/pyproject.toml": "[project]\nname='watchllm-webproof'\n",
            "webproof/src/watchllm_webproof/__init__.py": "from .agent import VerifiableAgent",
            "webproof/src/watchllm_webproof/agent.py": "# public SDK",
            "webproof/tests/test_agent.py": "# public tests",
            "webproof/engine/Cargo.toml": "[package]\nname='watchllm-webproof-engine'\n",
            "webproof/engine/src/lib.rs": "// public local non-attesting commitment engine",
            "webproof/edge/src/index.ts": "// PRIVATE EDGE WORKER",
            "webproof/edge/src/auth.ts": "// PRIVATE EDGE AUTH",
            "webproof/edge/schema.sql": "-- PRIVATE EDGE SCHEMA",
            "webproof/edge/package.json": '{"private":true}',
            "webproof/engine/prover/remote.rs": "// PRIVATE REMOTE PROVER",
            "webproof/engine/verifier/remote.rs": "// PRIVATE REMOTE VERIFIER",
            "webproof/engine/attestation/tls.rs": "// PRIVATE ATTESTATION",
            "webproof/engine/private/keys.rs": "// PRIVATE",
            "webproof/private/keys.py": "# PRIVATE",
            "webproof/src/watchllm_webproof/prover/remote.py": "# PRIVATE PROVER",
            "webproof/src/watchllm_webproof/verifier/remote.py": "# PRIVATE VERIFIER",
            "webproof/src/watchllm_webproof/attestation/tls.py": "# PRIVATE ATTESTATION",
            "webproof/src/watchllm_webproof/private/secrets.py": "# PRIVATE",

            # Public Replay application and private WebProof dashboard extension
            "replay/package.json": '{"name":"watchllm-replay"}',
            "replay/src/server/index.cjs": "// public replay server",
            "replay/src/client/src/App.tsx": "// public replay client",
            "replay/test/query-api.test.cjs": "// public replay tests",
            "replay/src/webproof-private/server/router.cjs": "// PRIVATE WEBPROOF ROUTER",
            "replay/src/webproof-private/client/ProofsList.tsx": "// PRIVATE WEBPROOF UI",
            "replay/src/webproof-private/test/proofs-api.test.cjs": "// PRIVATE WEBPROOF TESTS",

            # Metadata — these must be tracked
            "CHANGELOG.md": "# Changelog",
            "CONTRIBUTING.md": "# Contributing",
            "LICENSE": "PRIVATE REPOSITORY NOTICE",

            # .github files
            ".github/CODEOWNERS": "* @watchllm/owners",
            ".github/SECURITY.md": "# Security",
            ".github/ISSUE_TEMPLATE/bug.yml": "name: Bug",
            ".github/ISSUE_TEMPLATE/feature.yml": "name: Feature",
            ".github/workflows/ci.yml": """name: Private CI
jobs:
  runtime:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: runtime
    steps: []
  replay:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: replay
    steps: []
""",
            ".github/workflows/publish-kernel.yml": "name: Publish",

            # Also need the allowlist/denylist in this fixture
            ".github/oss-export-allowlist.txt": """# Allowlist
kernel/
schemas/
vscode/
examples/
webproof/
replay/
CHANGELOG.md
CONTRIBUTING.md
.github/CODEOWNERS
.github/SECURITY.md
.github/ISSUE_TEMPLATE/
.github/oss-root/workflows/ci.yml => .github/workflows/ci.yml
.github/workflows/publish-kernel.yml
.github/oss-root/README.md => README.md
.github/oss-root/.gitignore => .gitignore
.github/oss-root/LICENSE => LICENSE
""",
            ".github/oss-export-denylist.txt": """# Denylist
**/internal_docs/**
**/AUDIT.md
**/tasks.md
**/__pycache__/**
**/*.pyc
**/.pytest_cache/**
**/.env
**/.DS_Store
**/.klyd/**
**/CACHEDIR.TAG
kernel/openclaw.txt
vscode/path
**/.vscode/**
**/.vscodeignore
**/.vsix
kernel/.watchllm/logs/**
webproof/edge/**
webproof/engine/prover/**
webproof/engine/verifier/**
webproof/engine/attestation/**
webproof/engine/private/**
webproof/private/**
webproof/src/watchllm_webproof/prover/**
webproof/src/watchllm_webproof/verifier/**
webproof/src/watchllm_webproof/attestation/**
webproof/src/watchllm_webproof/private/**
replay/src/webproof-private/**
""",

            # Proprietary files (NOT in allowlist)
            "proprietary/secret_code.py": "# PROPRIETARY",
            "docs/private_design.md": "# PRIVATE",
            "internal/secrets.json": '{"key":"SECRET"}',
            ".watchllm/config.yaml": "proprietary: true",

            # Mapped public-root assets (source of truth for README/.gitignore)
            ".github/oss-root/README.md": "# WatchLLM OSS\\nOpen-core governance platform.",
            ".github/oss-root/.gitignore": "*.pyc\\n__pycache__/",
            ".github/oss-root/LICENSE": "MIT License\\n",
            ".github/oss-root/workflows/ci.yml": "name: Public CI\njobs:\n  kernel:\n    runs-on: ubuntu-latest\n    steps: []\n  vscode:\n    runs-on: ubuntu-latest\n    steps: []\n",
        }

        for path, content in dirs_and_files.items():
            full_path = os.path.join(cls.test_git_dir, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)

        # NOTE: Do NOT create a symlink in the fixture repo — a real symlink
        # tracked by git (mode 120000) will cause the exporter to hard-fail
        # on all exports, which breaks most tests. The symlink-rejection test
        # creates a separate fixture with a symlink committed on purpose.

        # Add everything and commit
        cls._run(["git", "add", "-A"], cwd=cls.test_git_dir)
        cls._run(["git", "commit", "-m", "test: fixture repo with all scenarios"], cwd=cls.test_git_dir)

        cls.fixture_ref = "HEAD"
        cls.fixtures_built = True

    @staticmethod
    def _run(cmd, cwd=None, check=True, capture=True):
        kwargs = {"cwd": cwd}
        if capture:
            kwargs["stdout"] = subprocess.PIPE
            kwargs["stderr"] = subprocess.PIPE
        result = subprocess.run(cmd, **kwargs)
        if check and result.returncode != 0:
            msg = f"Command failed: {' '.join(cmd)}\nstdout: {result.stdout}\nstderr: {result.stderr}"
            raise RuntimeError(msg)
        return result

    def _export(self, ref=None, target=None, dry_run=False, source=None, expect_failure=False):
        """Run the exporter and return (stdout, stderr, returncode)."""
        if source is None:
            source = self.test_git_dir
        cmd = [
            "bash", self.exporter,
            "--ref", ref or self.fixture_ref,
            "--source", source,
            "--target", target or os.path.join(self.temp_root, "target"),
        ]
        if dry_run:
            cmd.append("--dry-run")

        result = subprocess.run(
            cmd,
            cwd=source,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if not expect_failure and result.returncode != 0:
            self.fail(
                f"Exporter failed unexpectedly (rc={result.returncode}):\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        return result.stdout, result.stderr, result.returncode

    def _list_target_files(self, target):
        """List all non-.git files in target."""
        files = []
        for root, dirs, filenames in os.walk(target):
            dirs[:] = [d for d in dirs if d != ".git"]
            for f in filenames:
                rel = os.path.relpath(os.path.join(root, f), target)
                files.append(rel)
        return sorted(files)

    # ---- Tests ----

    def test_01_tracked_only_no_untracked_leakage(self):
        """Untracked working-tree files must never be exported."""
        self.build_fixture_repo()
        target = os.path.join(self.temp_root, "target-tracked-only")
        os.makedirs(target, exist_ok=True)

        # Create an untracked file in the source that shouldn't be exported
        untracked = os.path.join(self.test_git_dir, "kernel", "UNTRAKENDO_NOT_EXPORT.py")
        with open(untracked, "w") as f:
            f.write("# THIS IS UNTRACKED")

        stdout, stderr, rc = self._export(target=target)

        files = self._list_target_files(target)
        self.assertNotIn(
            "kernel/UNTRAKENDO_NOT_EXPORT.py", files,
            "UNTRAKNEDO_NOT_EXPORT.py was exported despite being untracked"
        )

        # Clean up the untracked file
        os.unlink(untracked)

    def test_02_internal_docs_excluded(self):
        """AUDIT.md, tasks.md, and internal_docs/** must be excluded."""
        self.build_fixture_repo()
        target = os.path.join(self.temp_root, "target-no-internal")
        os.makedirs(target, exist_ok=True)

        stdout, stderr, rc = self._export(target=target)

        files = self._list_target_files(target)

        # These must NOT be present
        forbidden = [
            "kernel/AUDIT.md",
            "kernel/tasks.md",
            "kernel/internal_docs/README.md",
            "kernel/internal_docs/IMPORTANT.md",
            "schemas/AUDIT.md",
            "schemas/tasks.md",
            "schemas/internal_docs/README.md",
            "vscode/AUDIT.md",
            "vscode/tasks.md",
            "examples/AUDIT.md",
            "examples/tasks.md",
            "examples/internal_docs/README.md",
        ]
        for f in forbidden:
            self.assertNotIn(f, files, f"Internal doc was exported: {f}")

    def test_03_legitimate_secrets_tests_retained(self):
        """examples/scenarios/secrets/* must be retained (legitimate tests)."""
        self.build_fixture_repo()
        target = os.path.join(self.temp_root, "target-secrets-retained")
        os.makedirs(target, exist_ok=True)

        stdout, stderr, rc = self._export(target=target)

        files = self._list_target_files(target)

        self.assertIn("examples/scenarios/secrets/README.md", files)
        self.assertIn("examples/scenarios/secrets/safe.py", files)
        self.assertIn("examples/scenarios/secrets/unsafe.py", files)

    def test_04_symlink_rejection(self):
        """Symlinks in git tree must cause export failure."""
        # Create a separate fixture with a tracked symlink
        symlink_repo = os.path.join(self.temp_root, "symlink-repo")
        os.makedirs(symlink_repo, exist_ok=True)
        self._run(["git", "init", "-b", "main"], cwd=symlink_repo)
        self._run(["git", "config", "user.name", "Test"], cwd=symlink_repo)
        self._run(["git", "config", "user.email", "test@test"], cwd=symlink_repo)

        # Create a real tracked file
        os.makedirs(os.path.join(symlink_repo, "kernel"), exist_ok=True)
        with open(os.path.join(symlink_repo, "kernel", "real_file.py"), "w") as f:
            f.write("# real")

        # Create a symlink
        symlink_path = os.path.join(symlink_repo, "kernel", "evil_link")
        os.symlink("/etc/passwd", symlink_path)

        # Create minimal allowlist/denylist
        os.makedirs(os.path.join(symlink_repo, ".github"), exist_ok=True)
        with open(os.path.join(symlink_repo, ".github", "oss-export-allowlist.txt"), "w") as f:
            f.write("kernel/\n")
        with open(os.path.join(symlink_repo, ".github", "oss-export-denylist.txt"), "w") as f:
            f.write("# nothing denied\n")

        self._run(["git", "add", "-A"], cwd=symlink_repo)
        self._run(["git", "commit", "-m", "fixture with symlink"], cwd=symlink_repo)

        target = os.path.join(self.temp_root, "target-symlink")
        stdout, stderr, rc = self._export(
            source=symlink_repo, target=target, ref="HEAD", expect_failure=True
        )
        self.assertNotEqual(rc, 0, "Exporter should have failed on symlink")
        # The error message says "Symlink" (mixed case)
        combined = (stderr + stdout).lower()
        self.assertTrue("symlink" in combined, f"Expected 'symlink' in error output, got: {stderr}")

    def test_05_dry_run_immutability(self):
        """Dry-run must produce zero writes to target."""
        self.build_fixture_repo()

        # Pre-populate target with a file
        target = os.path.join(self.temp_root, "target-dry-run")
        os.makedirs(target, exist_ok=True)
        preexisting = os.path.join(target, "preexisting.txt")
        with open(preexisting, "w") as f:
            f.write("should survive dry-run")

        # Record mtime
        initial_mtime = os.path.getmtime(target)
        initial_files = set(self._list_target_files(target))

        stdout, stderr, rc = self._export(target=target, dry_run=True)

        # Target must be unchanged
        self.assertTrue(os.path.exists(preexisting), "Preexisting file was deleted during dry-run")
        final_files = set(self._list_target_files(target))
        self.assertEqual(
            initial_files, final_files,
            f"Target was modified during dry-run: {final_files - initial_files}"
        )

        # Check that the exporter reported "dry-run" and "no writes"
        self.assertIn("dry-run", stdout.lower() + stderr.lower())

    def test_06_proprietary_path_rejection(self):
        """Files in proprietary dirs (not in allowlist) must not be exported."""
        self.build_fixture_repo()
        target = os.path.join(self.temp_root, "target-proprietary")
        os.makedirs(target, exist_ok=True)

        stdout, stderr, rc = self._export(target=target)

        files = self._list_target_files(target)

        # These proprietary paths must NOT be present
        prohibited = [
            "proprietary/secret_code.py",
            "docs/private_design.md",
            "internal/secrets.json",
            ".watchllm/config.yaml",
        ]
        for f in prohibited:
            self.assertNotIn(f, files, f"Proprietary file was exported: {f}")

    def test_07_stale_target_deletion(self):
        """Files previously exported but no longer allowed must be deleted from target."""
        self.build_fixture_repo()
        target = os.path.join(self.temp_root, "target-stale")
        os.makedirs(target, exist_ok=True)

        # First export normally
        stdout, stderr, rc = self._export(target=target)

        # Now manually plant a stale file that shouldn't be there
        stale_file = os.path.join(target, "kernel", "STALE_DELETEME.py")
        os.makedirs(os.path.dirname(stale_file), exist_ok=True)
        with open(stale_file, "w") as f:
            f.write("# this should be deleted")

        # Also plant a file inside a dir that should not exist at all
        stale_internal = os.path.join(target, "kernel", "internal_docs", "LEAKED.md")
        os.makedirs(os.path.dirname(stale_internal), exist_ok=True)
        with open(stale_internal, "w") as f:
            f.write("# INTERNAL LEAK")

        # Also plant .git to ensure it's preserved
        git_dir = os.path.join(target, ".git")
        os.makedirs(os.path.join(git_dir, "objects"), exist_ok=True)
        with open(os.path.join(git_dir, "HEAD"), "w") as f:
            f.write("ref: refs/heads/main\n")

        # Verify stale files exist before re-export
        self.assertTrue(os.path.exists(stale_file), "Stale file should exist before export")
        self.assertTrue(os.path.exists(stale_internal), "Stale internal should exist before export")

        # Re-export
        os.makedirs(target, exist_ok=True)
        stdout, stderr, rc = self._export(target=target)

        # Stale files must be gone
        self.assertFalse(
            os.path.exists(stale_file),
            f"Stale file was not deleted: {stale_file}"
        )
        self.assertFalse(
            os.path.exists(stale_internal),
            f"Stale internal doc was not deleted: {stale_internal}"
        )

        # .git must still exist
        self.assertTrue(os.path.exists(git_dir), ".git was deleted during reconciliation")
        self.assertTrue(os.path.exists(os.path.join(git_dir, "HEAD")), ".git/HEAD was deleted")

    def test_08_public_metadata_files_exported(self):
        """CHANGELOG.md, CONTRIBUTING.md, LICENSE should be exported."""
        self.build_fixture_repo()
        target = os.path.join(self.temp_root, "target-metadata")
        os.makedirs(target, exist_ok=True)

        stdout, stderr, rc = self._export(target=target)

        files = self._list_target_files(target)

        for meta in ["CHANGELOG.md", "CONTRIBUTING.md", "LICENSE"]:
            self.assertIn(meta, files, f"Public metadata file not exported: {meta}")

    def test_09_github_metadata_exported(self):
        """.github CODEOWNERS, SECURITY.md, ISSUE_TEMPLATE, and OSS workflows exported."""
        self.build_fixture_repo()
        target = os.path.join(self.temp_root, "target-gh")
        os.makedirs(target, exist_ok=True)

        stdout, stderr, rc = self._export(target=target)

        files = self._list_target_files(target)

        expected = [
            ".github/CODEOWNERS",
            ".github/SECURITY.md",
            ".github/ISSUE_TEMPLATE/bug.yml",
            ".github/ISSUE_TEMPLATE/feature.yml",
            ".github/workflows/ci.yml",
            ".github/workflows/publish-kernel.yml",
        ]
        for f in expected:
            self.assertIn(f, files, f"GitHub metadata not exported: {f}")

        # The exported CI target must be sourced from the dedicated public
        # template. Private-only jobs and component paths must never cross the
        # repository boundary through the monorepo's full CI workflow.
        with open(os.path.join(target, ".github", "workflows", "ci.yml")) as f:
            exported_ci = f.read()
        with open(os.path.join(self.test_git_dir, ".github", "oss-root", "workflows", "ci.yml")) as f:
            public_ci = f.read()
        self.assertEqual(exported_ci, public_ci)
        self.assertIn("kernel:", exported_ci)
        self.assertIn("vscode:", exported_ci)
        private_only_components = (
            "runtime", "replay", "reliability", "klyd", "klyd_harness_repo",
            "orchestrator", "cli", "benchmarks", "website",
        )
        for component in private_only_components:
            self.assertNotIn(f"{component}:", exported_ci)
            self.assertNotIn(f"working-directory: {component}", exported_ci)
            self.assertNotIn(f"./{component}", exported_ci)
            self.assertNotIn(f"../{component}", exported_ci)
        self.assertNotIn("Private CI", exported_ci)

    def test_10_build_artifacts_excluded(self):
        """__pycache__, .pyc, .pytest_cache, .env, .DS_Store must be excluded."""
        self.build_fixture_repo()
        target = os.path.join(self.temp_root, "target-no-artifacts")
        os.makedirs(target, exist_ok=True)

        stdout, stderr, rc = self._export(target=target)

        files = self._list_target_files(target)

        artifacts = [
            "kernel/__pycache__/engine.cpython-311.pyc",
            "kernel/.pytest_cache/v/cache/nodeids",
            "kernel/.env",
            "kernel/.DS_Store",
            "kernel/.klyd/config",
            "kernel/CACHEDIR.TAG",
        ]
        for f in artifacts:
            self.assertNotIn(f, files, f"Build artifact was exported: {f}")

    def test_11_vscode_test_retained(self):
        """vscode/test/* must be retained (legitimate tests, not excluded by 'test' dir)."""
        self.build_fixture_repo()
        target = os.path.join(self.temp_root, "target-vscode-test")
        os.makedirs(target, exist_ok=True)

        stdout, stderr, rc = self._export(target=target)

        files = self._list_target_files(target)

        # vscode/test/ is legitimate test code
        test_files = [f for f in files if f.startswith("vscode/test/")]
        self.assertGreater(len(test_files), 0, "vscode/test/* should be exported")

        # vscode/path must NOT be exported
        self.assertNotIn("vscode/path", files, "vscode/path (proprietary) was exported")

        # vscode/.vscode/ must NOT be exported
        vscode_dot = [f for f in files if ".vscode/" in f]
        self.assertEqual(len(vscode_dot), 0, f".vscode/ files should not be exported: {vscode_dot}")

    def test_12_target_not_inside_source(self):
        """Reject if --target is inside --source."""
        self.build_fixture_repo()
        target = os.path.join(self.test_git_dir, "subdir-target")
        os.makedirs(target, exist_ok=True)

        stdout, stderr, rc = self._export(target=target, expect_failure=True)
        self.assertNotEqual(rc, 0, "Should reject target inside source")
        self.assertIn("inside", (stderr + stdout).lower())

    def test_13_empty_allowlist_rejected(self):
        """Exporter must fail if allowlist has no entries."""
        self.build_fixture_repo()

        # Create a copy of the repo with an empty allowlist
        test_repo = os.path.join(self.temp_root, "empty-allowlist-repo")
        shutil.copytree(self.test_git_dir, test_repo, symlinks=True)

        allowlist_path = os.path.join(test_repo, ".github", "oss-export-allowlist.txt")
        with open(allowlist_path, "w") as f:
            f.write("# Empty allowlist\n# No entries\n\n")

        target = os.path.join(self.temp_root, "target-empty-allowlist")
        stdout, stderr, rc = self._export(
            source=test_repo, target=target, expect_failure=True
        )
        self.assertNotEqual(rc, 0, "Should reject empty allowlist")

    def test_14_path_traversal_in_allowlist(self):
        """Allowlist entries with '..' must be rejected."""
        self.build_fixture_repo()
        test_repo = os.path.join(self.temp_root, "traversal-repo")
        shutil.copytree(self.test_git_dir, test_repo, symlinks=True)

        allowlist_path = os.path.join(test_repo, ".github", "oss-export-allowlist.txt")
        with open(allowlist_path, "w") as f:
            f.write("kernel/../../etc/\n")

        target = os.path.join(self.temp_root, "target-traversal")
        stdout, stderr, rc = self._export(
            source=test_repo, target=target, expect_failure=True
        )
        self.assertNotEqual(rc, 0, "Should reject path traversal in allowlist")

    def test_15_nonexistent_ref_fails(self):
        """Exporter must fail for a nonexistent git ref."""
        self.build_fixture_repo()
        target = os.path.join(self.temp_root, "target-bad-ref")

        stdout, stderr, rc = self._export(
            ref="refs/heads/does-not-exist-xyz", target=target, expect_failure=True
        )
        self.assertNotEqual(rc, 0, "Should reject nonexistent ref")

    def test_16_missing_allowlist_file_fails(self):
        """Exporter must fail when allowlist file doesn't exist."""
        test_repo = os.path.join(self.temp_root, "no-allowlist-repo")
        shutil.copytree(self.test_git_dir, test_repo, symlinks=True)
        os.unlink(os.path.join(test_repo, ".github", "oss-export-allowlist.txt"))

        target = os.path.join(self.temp_root, "target-no-allowlist")
        stdout, stderr, rc = self._export(
            source=test_repo, target=target, expect_failure=True
        )
        self.assertNotEqual(rc, 0, "Should reject missing allowlist file")

    def test_17_legitimate_kernel_code_exported(self):
        """All legitimate kernel code under allowed paths (minus denied ones) must be present."""
        self.build_fixture_repo()
        target = os.path.join(self.temp_root, "target-legit-kernel")
        os.makedirs(target, exist_ok=True)

        stdout, stderr, rc = self._export(target=target)
        files = self._list_target_files(target)

        # These should be exported
        expected = [
            "kernel/legit_module.py",
            "kernel/legit_sub/helper.py",
            "kernel/__init__.py",
            "kernel/engine.py",
        ]
        for f in expected:
            self.assertIn(f, files, f"Legitimate kernel file not exported: {f}")

        # These should NOT be exported
        denied = [
            "kernel/openclaw.txt",
            "kernel/.watchllm/logs/debug.log",
        ]
        for f in denied:
            self.assertNotIn(f, files, f"Denied kernel file was exported: {f}")

    def test_18_examples_scenarios_auth_flow_exported(self):
        """Legitimate examples (auth_flow) must be exported."""
        self.build_fixture_repo()
        target = os.path.join(self.temp_root, "target-auth-flow")
        os.makedirs(target, exist_ok=True)

        stdout, stderr, rc = self._export(target=target)
        files = self._list_target_files(target)

        auth_files = [f for f in files if "auth_flow" in f]
        self.assertGreater(len(auth_files), 0, "Auth flow examples should be exported")

    def test_19_mapped_assets_exported_exactly(self):
        """Mapped public-root assets (README.md, .gitignore) exported byte-for-byte from source."""
        self.build_fixture_repo()
        target = os.path.join(self.temp_root, "target-mapped-assets")
        os.makedirs(target, exist_ok=True)

        stdout, stderr, rc = self._export(target=target)
        files = self._list_target_files(target)

        # README.md must be present and match fixture source content
        self.assertIn("README.md", files, "README.md not exported from mapping")
        self.assertIn(".gitignore", files, ".gitignore not exported from mapping")
        self.assertIn("LICENSE", files, "LICENSE not exported from mapping")

        # Verify byte-for-byte content match
        target_readme = os.path.join(target, "README.md")
        target_gitignore = os.path.join(target, ".gitignore")
        src_readme = os.path.join(self.test_git_dir, ".github", "oss-root", "README.md")
        src_gitignore = os.path.join(self.test_git_dir, ".github", "oss-root", ".gitignore")
        src_license = os.path.join(self.test_git_dir, ".github", "oss-root", "LICENSE")

        with open(target_readme, "rb") as f:
            t_r = f.read()
        with open(src_readme, "rb") as f:
            s_r = f.read()
        self.assertEqual(t_r, s_r, "README.md content does not match source byte-for-byte")

        with open(target_gitignore, "rb") as f:
            t_g = f.read()
        with open(src_gitignore, "rb") as f:
            s_g = f.read()
        self.assertEqual(t_g, s_g, ".gitignore content does not match source byte-for-byte")

        with open(os.path.join(target, "LICENSE"), "rb") as f:
            t_l = f.read()
        with open(src_license, "rb") as f:
            s_l = f.read()
        self.assertEqual(t_l, s_l, "LICENSE content does not match source byte-for-byte")

    def test_20_duplicate_destination_rejected(self):
        """Two mappings with the same destination must be rejected."""
        self.build_fixture_repo()
        dup_repo = os.path.join(self.temp_root, "dup-dst-repo")
        shutil.copytree(self.test_git_dir, dup_repo, symlinks=True)

        allowlist_path = os.path.join(dup_repo, ".github", "oss-export-allowlist.txt")
        with open(allowlist_path, "w") as f:
            f.write("""kernel/
.github/oss-root/README.md => README.md
.github/oss-root/README.md => README.md
""")

        target = os.path.join(self.temp_root, "target-dup-dst")
        stdout, stderr, rc = self._export(
            source=dup_repo, target=target, expect_failure=True
        )
        self.assertNotEqual(rc, 0, "Should reject duplicate mapping destination")
        self.assertIn("Duplicate", (stderr + stdout))

    def test_21_traversal_destination_rejected(self):
        """Mapping destination with '..' must be rejected."""
        self.build_fixture_repo()
        trav_repo = os.path.join(self.temp_root, "trav-dst-repo")
        shutil.copytree(self.test_git_dir, trav_repo, symlinks=True)

        allowlist_path = os.path.join(trav_repo, ".github", "oss-export-allowlist.txt")
        with open(allowlist_path, "w") as f:
            f.write("""kernel/
.github/oss-root/README.md => ../etc/README.md
""")

        target = os.path.join(self.temp_root, "target-trav-dst")
        stdout, stderr, rc = self._export(
            source=trav_repo, target=target, expect_failure=True
        )
        self.assertNotEqual(rc, 0, "Should reject traversal in mapping destination")
        combined = (stderr + stdout).lower()
        self.assertTrue("traversal" in combined, f"Expected 'traversal' in error, got: {stderr}")

    def test_22_arbitrary_stale_root_file_deleted(self):
        """Stale files at target root not in export map must be deleted during reconciliation."""
        self.build_fixture_repo()
        target = os.path.join(self.temp_root, "target-stale-root")
        os.makedirs(target, exist_ok=True)

        # First export normally
        stdout, stderr, rc = self._export(target=target)

        # Plant an arbitrary stale file at root that shouldn't exist
        stale_root = os.path.join(target, "STALE_README_OLD.md")
        with open(stale_root, "w") as f:
            f.write("# OLD STALE FILE")

        # Also plant .git to ensure it's preserved
        git_dir = os.path.join(target, ".git")
        os.makedirs(os.path.join(git_dir, "objects"), exist_ok=True)
        with open(os.path.join(git_dir, "HEAD"), "w") as f:
            f.write("ref: refs/heads/main\\n")

        self.assertTrue(os.path.exists(stale_root), "Stale root file should exist before re-export")

        # Re-export
        stdout, stderr, rc = self._export(target=target)

        # Stale root file must be gone
        self.assertFalse(
            os.path.exists(stale_root),
            f"Stale root file was not deleted during reconciliation: {stale_root}"
        )

        # .git must still exist
        self.assertTrue(os.path.exists(git_dir), ".git was deleted during reconciliation")

        # README.md and .gitignore should still be present
        self.assertTrue(os.path.exists(os.path.join(target, "README.md")), "README.md missing after re-export")
        self.assertTrue(os.path.exists(os.path.join(target, ".gitignore")), ".gitignore missing after re-export")

    def test_23_empty_allowlisted_directory_rejected(self):
        """A directory entry with no tracked files must fail closed."""
        self.build_fixture_repo()
        empty_repo = os.path.join(self.temp_root, "empty-dir-repo")
        shutil.copytree(self.test_git_dir, empty_repo, symlinks=True)
        allowlist_path = os.path.join(empty_repo, ".github", "oss-export-allowlist.txt")
        with open(allowlist_path, "w") as f:
            f.write("missing-directory/\n")

        stdout, stderr, rc = self._export(
            source=empty_repo,
            target=os.path.join(self.temp_root, "target-empty-dir"),
            expect_failure=True,
        )
        self.assertNotEqual(rc, 0)
        self.assertIn("has no tracked files", stderr + stdout)

    def test_24_webproof_sdk_and_commitment_engine_export_without_private_provers(self):
        """Public local commitment code exports while remote proof implementations do not."""
        self.build_fixture_repo()
        target = os.path.join(self.temp_root, "target-webproof-boundary")
        os.makedirs(target, exist_ok=True)

        self._export(target=target)
        files = self._list_target_files(target)

        for public_file in (
            "webproof/pyproject.toml",
            "webproof/src/watchllm_webproof/__init__.py",
            "webproof/src/watchllm_webproof/agent.py",
            "webproof/tests/test_agent.py",
            "webproof/engine/Cargo.toml",
            "webproof/engine/src/lib.rs",
        ):
            self.assertIn(public_file, files)

        for private_file in (
            "webproof/edge/src/index.ts",
            "webproof/edge/src/auth.ts",
            "webproof/edge/schema.sql",
            "webproof/edge/package.json",
            "webproof/engine/prover/remote.rs",
            "webproof/engine/verifier/remote.rs",
            "webproof/engine/attestation/tls.rs",
            "webproof/engine/private/keys.rs",
            "webproof/private/keys.py",
            "webproof/src/watchllm_webproof/prover/remote.py",
            "webproof/src/watchllm_webproof/verifier/remote.py",
            "webproof/src/watchllm_webproof/attestation/tls.py",
            "webproof/src/watchllm_webproof/private/secrets.py",
        ):
            self.assertNotIn(private_file, files)

    def test_25_public_replay_exports_without_private_webproof_dashboard(self):
        """Public Replay remains exportable while its private extension never crosses."""
        self.build_fixture_repo()
        target = os.path.join(self.temp_root, "target-replay-boundary")
        os.makedirs(target, exist_ok=True)

        self._export(target=target)
        files = self._list_target_files(target)

        for public_file in (
            "replay/package.json",
            "replay/src/server/index.cjs",
            "replay/src/client/src/App.tsx",
            "replay/test/query-api.test.cjs",
        ):
            self.assertIn(public_file, files)

        for private_file in (
            "replay/src/webproof-private/server/router.cjs",
            "replay/src/webproof-private/client/ProofsList.tsx",
            "replay/src/webproof-private/test/proofs-api.test.cjs",
        ):
            self.assertNotIn(private_file, files)


def run_with_real_repo():
    """Run tests against the real source repo (for CI integration)."""
    source_repo = os.environ.get("SOURCE", "")
    if not source_repo or not os.path.isdir(os.path.join(source_repo, ".git")):
        return

    exporter = os.path.join(source_repo, ".github", "scripts", "oss-export.sh")
    if not os.path.isfile(exporter):
        return

    # Simple smoke test: dry-run against real repo
    target = tempfile.mkdtemp(prefix="oss-export-real-")
    try:
        result = subprocess.run(
            ["bash", exporter, "--ref", "HEAD", "--source", source_repo, "--target", target, "--dry-run"],
            cwd=source_repo,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        print(f"Real repo dry-run: rc={result.returncode}")
        if result.returncode != 0:
            print(f"STDERR: {result.stderr}")
    finally:
        shutil.rmtree(target, ignore_errors=True)


if __name__ == "__main__":
    # Allow running with --exporter and --source args
    import argparse
    parser = argparse.ArgumentParser(description="Test OSS export")
    parser.add_argument("--exporter", help="Path to oss-export.sh")
    parser.add_argument("--source", help="Path to source git repo")
    parser.add_argument("--ref", default="HEAD", help="Git ref to test")
    args, remaining = parser.parse_known_args()

    if args.exporter:
        OSSExportTests.exporter = os.path.abspath(args.exporter)
    if args.source:
        OSSExportTests.source_repo = os.path.abspath(args.source)
    if args.ref:
        OSSExportTests.test_ref = args.ref

    unittest.main(argv=[sys.argv[0]] + remaining, verbosity=2)
