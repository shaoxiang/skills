#!/usr/bin/env python3
"""Verify that a Skill can be installed (dry-run)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    if len(sys.argv) != 2:
        fail("Usage: verify_install.py skills/<skill_name>")

    src = Path(sys.argv[1]).resolve()
    if not src.is_dir():
        fail(f"Skill directory not found: {src}")

    repo_root = src.parents[1]
    validate_script = repo_root / "scripts" / "validate_skill.py"
    result = subprocess.run([sys.executable, str(validate_script), str(src)], capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        fail(f"Validation failed for {src.name}")

    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / src.name
        shutil.copytree(src, dest)
        print(f"INSTALL DRY-RUN PASS: {src.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
