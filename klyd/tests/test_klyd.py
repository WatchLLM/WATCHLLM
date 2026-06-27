import json
import os
import sqlite3
import stat
import tempfile
from pathlib import Path
from unittest.mock import patch

import unittest
from click.testing import CliRunner

from klyd.cli import main


class TestKlydCLI(unittest.TestCase):
    def test_cli_help_does_not_crash(self):
        # Passing help should exit with status 0 or print help
        with self.assertRaises(SystemExit) as cm:
            main(["--help"])
        self.assertEqual(cm.exception.code, 0)

    def test_cli_version_does_not_crash(self):
        with self.assertRaises(SystemExit) as cm:
            main(["--version"])
        self.assertEqual(cm.exception.code, 0)

    def test_init_creates_klyd_directory_and_files(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            tmp_path = Path(tmpdir)
            with patch.object(Path, "cwd", return_value=tmp_path):
                # Create a fake .git directory so that hook initialisation succeeds
                (tmp_path / ".git").mkdir()

                runner = CliRunner()
                result = runner.invoke(main, ["init"])
                self.assertEqual(result.exit_code, 0, result.output)

                klyd_root = tmp_path / ".klyd"
                self.assertTrue(klyd_root.is_dir(), f"Missing .klyd directory in {tmp_path}")

                db_file = klyd_root / "memory.db"
                self.assertTrue(db_file.is_file(), f"Missing memory.db in {klyd_root}")

                config_file = klyd_root / "config.json"
                self.assertTrue(config_file.is_file(), f"Missing config.json in {klyd_root}")

                # Verify decisions table columns
                with sqlite3.connect(str(db_file)) as conn:
                    columns = {
                        row[1]
                        for row in conn.execute("PRAGMA table_info(decisions)").fetchall()
                    }
                expected_columns = {
                    "decision",
                    "module",
                    "file_patterns",
                    "confidence",
                    "event_type",
                    "reinforcement_count",
                    "last_seen_commit",
                    "created_at",
                    "flagged",
                    "archived",
                }
                self.assertTrue(
                    expected_columns.issubset(columns),
                    f"Missing columns. Found: {columns}",
                )

                # Verify config content
                config_data = json.loads(config_file.read_text(encoding="utf-8"))
                self.assertEqual(config_data["provider"], "anthropic")
                self.assertIn("model", config_data)
                self.assertIn("api_key_env", config_data)

                # Verify git hooks
                hooks_dir = tmp_path / ".git" / "hooks"

                expected_hooks = {
                    "post-commit": "kl extract-commit >> .klyd/errors.log 2>&1 || true",
                    "pre-commit": "kl prepare-injection >> .klyd/errors.log 2>&1 || true",
                }

                for hook_name, expected_command in expected_hooks.items():
                    hook_file = hooks_dir / hook_name

                    self.assertTrue(
                        hook_file.is_file(),
                        f"Missing git hook: {hook_file}",
                    )

                    hook_content = hook_file.read_text(encoding="utf-8")
                    if os.name == "nt":
                        self.assertEqual(
                            hook_content,
                            f"@{expected_command}\n",
                        )
                    else:
                        self.assertEqual(
                            hook_content,
                            f"#!/bin/sh\n{expected_command}\n",
                        )
                        execute_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                        self.assertEqual(
                            hook_file.stat().st_mode & execute_bits,
                            execute_bits,
                            f"Hook is not executable: {hook_file}",
                        )

    def test_init_requires_git_directory_for_hooks(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            tmp_path = Path(tmpdir)

            with patch.object(Path, "cwd", return_value=tmp_path):
                runner = CliRunner()
                result = runner.invoke(main, ["init"])

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("No .git directory found", result.output)

    def test_status_prints_active_and_flagged_decisions(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            tmp_path = Path(tmpdir)

            with patch.object(Path, "cwd", return_value=tmp_path):
                (tmp_path / ".git").mkdir()

                runner = CliRunner()
                init_result = runner.invoke(main, ["init"])
                self.assertEqual(init_result.exit_code, 0, init_result.output)

                db_file = tmp_path / ".klyd" / "memory.db"

                with sqlite3.connect(db_file) as conn:
                    conn.execute(
                        """
                        INSERT INTO decisions (
                            decision,
                            module,
                            file_patterns,
                            confidence,
                            event_type,
                            flagged
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "Use SQLite for local memory.",
                            "storage",
                            json.dumps([".klyd/*"]),
                            0.9,
                            "NEW",
                            0,
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO decisions (
                            decision,
                            module,
                            file_patterns,
                            confidence,
                            event_type,
                            flagged
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "Store memory outside .klyd.",
                            "storage",
                            json.dumps([".klyd/*"]),
                            0.7,
                            "CONTRADICT",
                            1,
                        ),
                    )
                    conn.commit()

                result = runner.invoke(main, ["status"])

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("ACTIVE DECISIONS", result.output)
            self.assertIn("NEEDS REVIEW", result.output)
            self.assertIn("Use SQLite for local memory.", result.output)
            self.assertIn("Store memory outside .klyd.", result.output)

    def test_review_reject_archives_flagged_decision(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            tmp_path = Path(tmpdir)

            with patch.object(Path, "cwd", return_value=tmp_path):
                (tmp_path / ".git").mkdir()

                runner = CliRunner()
                init_result = runner.invoke(main, ["init"])
                self.assertEqual(init_result.exit_code, 0, init_result.output)

                db_file = tmp_path / ".klyd" / "memory.db"

                with sqlite3.connect(db_file) as conn:
                    cursor = conn.execute(
                        """
                        INSERT INTO decisions (
                            decision,
                            module,
                            file_patterns,
                            confidence,
                            event_type,
                            flagged
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "Contradict local-only memory.",
                            "storage",
                            json.dumps([".klyd/*"]),
                            0.8,
                            "CONTRADICT",
                            1,
                        ),
                    )
                    flagged_id = cursor.lastrowid
                    conn.commit()

                result = runner.invoke(main, ["review"], input="r\n")

                with sqlite3.connect(db_file) as conn:
                    archived = conn.execute(
                        "SELECT archived FROM decisions WHERE id = ?",
                        (flagged_id,),
                    ).fetchone()[0]

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(archived, 1)
            self.assertIn("Rejected and archived flagged decision", result.output)

    def test_review_accept_archives_old_and_unflags_new_decision(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            tmp_path = Path(tmpdir)

            with patch.object(Path, "cwd", return_value=tmp_path):
                (tmp_path / ".git").mkdir()

                runner = CliRunner()
                init_result = runner.invoke(main, ["init"])
                self.assertEqual(init_result.exit_code, 0, init_result.output)

                db_file = tmp_path / ".klyd" / "memory.db"

                with sqlite3.connect(db_file) as conn:
                    old_cursor = conn.execute(
                        """
                        INSERT INTO decisions (
                            decision,
                            module,
                            file_patterns,
                            confidence,
                            event_type,
                            flagged
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "Use old storage approach.",
                            "storage",
                            json.dumps([".klyd/*"]),
                            0.8,
                            "NEW",
                            0,
                        ),
                    )
                    old_id = old_cursor.lastrowid

                    new_cursor = conn.execute(
                        """
                        INSERT INTO decisions (
                            decision,
                            module,
                            file_patterns,
                            confidence,
                            event_type,
                            flagged
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "Use new storage approach.",
                            "storage",
                            json.dumps([".klyd/*"]),
                            0.9,
                            "CONTRADICT",
                            1,
                        ),
                    )
                    new_id = new_cursor.lastrowid
                    conn.commit()

                result = runner.invoke(main, ["review"], input=f"a\n{old_id}\n")

                with sqlite3.connect(db_file) as conn:
                    old_archived = conn.execute(
                        "SELECT archived FROM decisions WHERE id = ?",
                        (old_id,),
                    ).fetchone()[0]

                    new_state = conn.execute(
                        "SELECT flagged, archived FROM decisions WHERE id = ?",
                        (new_id,),
                    ).fetchone()

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(old_archived, 1)
            self.assertEqual(new_state[0], 0)
            self.assertEqual(new_state[1], 0)
            self.assertIn("Accepted flagged decision", result.output)

    def test_prepare_injection_writes_relevant_unflagged_unarchived_decisions(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            tmp_path = Path(tmpdir)

            with patch.object(Path, "cwd", return_value=tmp_path):
                (tmp_path / ".git").mkdir()

                runner = CliRunner()
                init_result = runner.invoke(main, ["init"])
                self.assertEqual(init_result.exit_code, 0, init_result.output)

                db_file = tmp_path / ".klyd" / "memory.db"

                with sqlite3.connect(db_file) as conn:
                    conn.execute(
                        """
                        INSERT INTO decisions (
                            decision,
                            module,
                            file_patterns,
                            confidence,
                            event_type,
                            reinforcement_count,
                            flagged,
                            archived
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "Use Click for CLI commands.",
                            "cli",
                            json.dumps(["src/klyd/*.py"]),
                            0.9,
                            "NEW",
                            3,
                            0,
                            0,
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO decisions (
                            decision,
                            module,
                            file_patterns,
                            confidence,
                            event_type,
                            reinforcement_count,
                            flagged,
                            archived
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "Keep all state local in .klyd.",
                            "storage",
                            json.dumps([]),
                            0.95,
                            "NEW",
                            5,
                            0,
                            0,
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO decisions (
                            decision,
                            module,
                            file_patterns,
                            confidence,
                            event_type,
                            reinforcement_count,
                            flagged,
                            archived
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "Docs-only decision should not match.",
                            "docs",
                            json.dumps(["docs/*.md"]),
                            0.8,
                            "NEW",
                            1,
                            0,
                            0,
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO decisions (
                            decision,
                            module,
                            file_patterns,
                            confidence,
                            event_type,
                            reinforcement_count,
                            flagged,
                            archived
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "Flagged decision should not be injected.",
                            "cli",
                            json.dumps(["src/klyd/*.py"]),
                            0.7,
                            "CONTRADICT",
                            1,
                            1,
                            0,
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO decisions (
                            decision,
                            module,
                            file_patterns,
                            confidence,
                            event_type,
                            reinforcement_count,
                            flagged,
                            archived
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "Archived decision should not be injected.",
                            "cli",
                            json.dumps(["src/klyd/*.py"]),
                            0.7,
                            "NEW",
                            1,
                            0,
                            1,
                        ),
                    )
                    conn.commit()

                def fake_run_git_command(args):
                    if args == ["diff", "--cached", "--name-only"]:
                        return "src/klyd/cli.py\n"

                    raise AssertionError(f"Unexpected git command: {args}")

                with patch(
                    "klyd.cli.run_git_command",
                    side_effect=fake_run_git_command,
                ):
                    result = runner.invoke(main, ["prepare-injection"])

                injection_file = tmp_path / ".klyd" / "injection.txt"
                content = injection_file.read_text(encoding="utf-8")

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue(injection_file.is_file())
            self.assertIn("KLYD ARCHITECTURAL MEMORY", content)
            self.assertIn("src/klyd/cli.py", content)
            self.assertIn("Use Click for CLI commands.", content)
            self.assertIn("Keep all state local in .klyd.", content)
            self.assertNotIn("Docs-only decision should not match.", content)
            self.assertNotIn("Flagged decision should not be injected.", content)
            self.assertNotIn("Archived decision should not be injected.", content)

    def test_prepare_injection_writes_file_when_no_relevant_decisions(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            tmp_path = Path(tmpdir)

            with patch.object(Path, "cwd", return_value=tmp_path):
                (tmp_path / ".git").mkdir()

                runner = CliRunner()
                init_result = runner.invoke(main, ["init"])
                self.assertEqual(init_result.exit_code, 0, init_result.output)

                with patch(
                    "klyd.cli.run_git_command",
                    return_value="src/unknown.py\n",
                ):
                    result = runner.invoke(main, ["prepare-injection"])

                injection_file = tmp_path / ".klyd" / "injection.txt"
                content = injection_file.read_text(encoding="utf-8")

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue(injection_file.is_file())
            self.assertIn("RELEVANT DECISIONS:", content)
            self.assertIn("- (none)", content)

    def test_run_aider_launches_subprocess_with_injection_message(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            with patch.object(Path, "cwd", return_value=tmp_path):
                klyd_root = tmp_path / ".klyd"
                klyd_root.mkdir()

                injection_file = klyd_root / "injection.txt"
                injection_file.write_text(
                    "KLYD ARCHITECTURAL MEMORY\n\n"
                    "RELEVANT DECISIONS:\n"
                    "- Use Click for CLI commands.\n",
                    encoding="utf-8",
                )

                class CompletedProcess:
                    returncode = 0

                with patch(
                    "klyd.cli.subprocess.run",
                    return_value=CompletedProcess(),
                ) as run_mock:
                    runner = CliRunner()
                    result = runner.invoke(main, ["run", "aider", "--yes"])

            self.assertEqual(result.exit_code, 0, result.output)

            run_mock.assert_called_once()
            called_command = run_mock.call_args.args[0]
            called_kwargs = run_mock.call_args.kwargs

            self.assertEqual(called_command[0], "aider")
            self.assertIn("--yes", called_command)
            self.assertIn("--message", called_command)

            message_index = called_command.index("--message") + 1
            injected_message = called_command[message_index]

            self.assertIn("[KLYD MEMORY]", injected_message)
            self.assertIn("Use Click for CLI commands.", injected_message)

            self.assertEqual(called_kwargs["cwd"], tmp_path)
            self.assertIn("KLYD_MEMORY", called_kwargs["env"])
            self.assertIn(
                "Use Click for CLI commands.",
                called_kwargs["env"]["KLYD_MEMORY"],
            )

    def test_run_requires_injection_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            with patch.object(Path, "cwd", return_value=tmp_path):
                runner = CliRunner()
                result = runner.invoke(main, ["run", "aider"])

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("No .klyd/injection.txt found", result.output)

    def test_run_generic_command_uses_klyd_memory_environment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            with patch.object(Path, "cwd", return_value=tmp_path):
                klyd_root = tmp_path / ".klyd"
                klyd_root.mkdir()

                (klyd_root / "injection.txt").write_text(
                    "Generic memory context.",
                    encoding="utf-8",
                )

                class CompletedProcess:
                    returncode = 0

                with patch(
                    "klyd.cli.subprocess.run",
                    return_value=CompletedProcess(),
                ) as run_mock:
                    runner = CliRunner()
                    result = runner.invoke(main, ["run", "python", "--version"])

            self.assertEqual(result.exit_code, 0, result.output)

            called_command = run_mock.call_args.args[0]
            called_env = run_mock.call_args.kwargs["env"]

            self.assertEqual(called_command, ["python", "--version"])
            self.assertIn("KLYD_MEMORY", called_env)
            self.assertIn("Generic memory context.", called_env["KLYD_MEMORY"])
