"""Tests for the AgentRunner."""

import sys
import textwrap
import time
from pathlib import Path

from reliability.runner import AgentRunner


def test_successful_subprocess_captures_stdout_and_stderr():
    runner = AgentRunner(timeout=10)
    script = textwrap.dedent("""\
        import sys
        sys.stdout.write("hello stdout")
        sys.stderr.write("hello stderr")
    """)
    result = runner.run([sys.executable, "-c", script])
    assert result.timed_out is False
    assert result.returncode == 0
    assert "hello stdout" in result.stdout
    assert "hello stderr" in result.stderr


def test_successful_subprocess_detects_created_file():
    runner = AgentRunner(timeout=10)
    script = textwrap.dedent("""\
        from pathlib import Path
        Path("new_file.txt").write_text("content")
    """)
    result = runner.run([sys.executable, "-c", script])
    assert result.timed_out is False
    assert result.returncode == 0
    added = [fc for fc in result.file_changes if fc.change_type == "added"]
    assert len(added) == 1
    assert added[0].path == "new_file.txt"


def test_timeout_case():
    runner = AgentRunner(timeout=1)
    # A script that sleeps longer than the timeout
    script = textwrap.dedent("""\
        import time
        time.sleep(5)
    """)
    result = runner.run([sys.executable, "-c", script])
    assert result.timed_out is True
    assert result.returncode is None
    assert result.stdout == ""
    assert result.stderr == ""
