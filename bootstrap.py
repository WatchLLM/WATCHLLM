#!/usr/bin/env python3
"""
bootstrap.py — WatchLLM monorepo installer.

Installs all WatchLLM subsystems in one shot:
  - Python packages: kernel, klyd, orchestrator, cli (pip install -e)
  - Rust binary:     runtime (cargo build --release)
  - Node packages:   vscode, replay (npm install)

Usage:
  python bootstrap.py           # install everything
  python bootstrap.py --skip-rust  # skip Rust build (faster for Python-only work)
  python bootstrap.py --skip-node  # skip npm installs
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# Force UTF-8 for Windows consoles
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------

IS_WIN = platform.system() == "Windows"

def _c(text: str, code: str) -> str:
    if IS_WIN and not os.environ.get("FORCE_COLOR"):
        return text
    return f"\033[{code}m{text}\033[0m"

def ok(msg: str) -> None:    print(_c(f"  ✅  {msg}", "32"))
def fail(msg: str) -> None:  print(_c(f"  ❌  {msg}", "31"))
def info(msg: str) -> None:  print(_c(f"  →  {msg}", "36"))
def warn(msg: str) -> None:  print(_c(f"  ⚠️  {msg}", "33"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def require(executable: str) -> bool:
    """Return True if executable is on PATH, else print a warning."""
    if shutil.which(executable) is None:
        warn(f"{executable!r} not found on PATH — skipping steps that need it.")
        return False
    return True


def run(cmd: list[str], cwd: Path, label: str) -> bool:
    """Run a subprocess command. Return True on success."""
    info(f"{label}: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode == 0:
        ok(label)
        return True
    else:
        fail(f"{label} — exit code {result.returncode}")
        return False


# ---------------------------------------------------------------------------
# Installation steps
# ---------------------------------------------------------------------------

PYTHON_PKGS = [
    ("kernel",       ROOT / "kernel"),
    ("klyd",         ROOT / "klyd"),
    ("orchestrator", ROOT / "orchestrator"),
    ("watchllm-cli", ROOT / "cli"),
]

NODE_PKGS = [
    ("vscode",  ROOT / "vscode"),
    ("replay",  ROOT / "replay"),
]


def install_python(errors: list[str]) -> None:
    print("\n[Python packages]")
    pip = [sys.executable, "-m", "pip", "install", "-e"]

    for name, path in PYTHON_PKGS:
        if not path.exists():
            warn(f"{name}: directory not found at {path} — skipping")
            continue
        success = run(pip + [str(path)], cwd=ROOT, label=f"pip install -e {name}")
        if not success:
            errors.append(f"pip install {name}")


def install_rust(errors: list[str]) -> None:
    print("\n[Rust runtime]")
    rust_dir = ROOT / "runtime"

    if not require("cargo"):
        errors.append("cargo not found (Rust runtime skipped)")
        return

    if not rust_dir.exists():
        warn(f"runtime/ directory not found at {rust_dir} — skipping")
        return

    success = run(
        ["cargo", "build", "--release"],
        cwd=rust_dir,
        label="cargo build --release (runtime)",
    )
    if not success:
        errors.append("cargo build runtime")


def install_node(errors: list[str]) -> None:
    print("\n[Node packages]")

    npm_cmd = "npm.cmd" if IS_WIN else "npm"
    if not require(npm_cmd):
        errors.append("npm not found (Node packages skipped)")
        return

    for name, path in NODE_PKGS:
        if not path.exists():
            warn(f"{name}: directory not found at {path} — skipping")
            continue
        success = run([npm_cmd, "install"], cwd=path, label=f"npm install ({name})")
        if not success:
            errors.append(f"npm install {name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="bootstrap",
        description="Install all WatchLLM subsystems.",
    )
    parser.add_argument("--skip-rust", action="store_true", help="Skip cargo build")
    parser.add_argument("--skip-node", action="store_true", help="Skip npm installs")
    parser.add_argument("--python-only", action="store_true", help="Only install Python packages")
    args = parser.parse_args()

    print(_c("\nWatchLLM Bootstrap", "1"))
    print("=" * 42)

    errors: list[str] = []

    install_python(errors)

    if not args.python_only:
        if not args.skip_rust:
            install_rust(errors)
        if not args.skip_node:
            install_node(errors)

    print()
    if errors:
        print(_c("Bootstrap completed with errors:", "31"))
        for e in errors:
            print(f"  - {e}")
        print("\nFix the above and re-run bootstrap.py")
        return 1
    else:
        print(_c("Bootstrap complete. All subsystems installed.", "32"))
        print("\nNext steps:")
        print("  watchllm init        # generate .watchllm.yaml in your project")
        print("  watchllm status      # verify everything is running")
        return 0


if __name__ == "__main__":
    sys.exit(main())
