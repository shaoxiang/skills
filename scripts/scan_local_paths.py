#!/usr/bin/env python3
"""Scan repository files for local/absolute machine paths."""

from __future__ import annotations

import sys
from pathlib import Path

BAD_PATHS = [
    "/data/rosclaw",
    "/home/",
    "/mnt/data",
    "C:\\Users\\",
]

SKIP_FILES = {
    "scan_local_paths.py",
    "scan_secrets.py",
}


def scan(path: Path) -> list[str]:
    findings: list[str] = []
    for p in sorted(path.rglob("*")):
        if not p.is_file():
            continue
        if ".git" in p.parts:
            continue
        if p.suffix == ".md":
            continue
        if p.name in SKIP_FILES:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for bad in BAD_PATHS:
            idx = text.find(bad)
            if idx == -1:
                continue
            # crude context extraction
            ctx = text[max(0, idx - 20): idx + len(bad) + 40].replace("\n", " ")
            findings.append(f"{p}: local path {bad!r} near: {ctx!r}")
    return findings


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    findings = scan(root)
    if findings:
        print("LOCAL PATH SCAN FAIL", file=sys.stderr)
        for f in findings:
            print(f"  {f}", file=sys.stderr)
        return 1
    print(f"LOCAL PATH SCAN PASS: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
