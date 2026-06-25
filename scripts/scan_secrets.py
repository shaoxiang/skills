#!/usr/bin/env python3
"""Scan repository files for likely secrets and API keys."""

from __future__ import annotations

import re
import sys
from pathlib import Path

FORBIDDEN_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"OPENAI_API_KEY\s*[:=]\s*['\"]?[^'\"\n\s]+"),
    re.compile(r"ANTHROPIC_API_KEY\s*[:=]\s*['\"]?[^'\"\n\s]+"),
    re.compile(r"QWEN_API_KEY\s*[:=]\s*['\"]?[^'\"\n\s]+"),
    re.compile(r"ROSCLAW_ADMIN_API_KEY\s*[:=]\s*['\"]?[^'\"\n\s]+"),
    re.compile(r"x-api-key\s*[:=]\s*['\"]?[^'\"\n\s]+"),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{36,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
]

ALLOWLIST = {
    "x-api-key": [".md"],
    "ROSCLAW_ADMIN_API_KEY": [".md"],
}


def _line_for_position(text: str, pos: int) -> str:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    if end == -1:
        end = len(text)
    return text[start:end]


def _is_innocuous_line(line: str) -> bool:
    lowered = line.lower()
    if "secrets." in lowered:
        return True
    if "env:" in lowered and "${{" in line:
        return True
    if "example" in lowered or "placeholder" in lowered or "your_" in lowered:
        return True
    return False


def scan(path: Path) -> list[str]:
    findings: list[str] = []
    for p in sorted(path.rglob("*")):
        if not p.is_file():
            continue
        if ".git" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pattern in FORBIDDEN_PATTERNS:
            for match in pattern.finditer(text):
                keyword = pattern.pattern.split(r"\s*")[0]
                if keyword in ALLOWLIST and p.suffix in ALLOWLIST[keyword]:
                    continue
                line = _line_for_position(text, match.start())
                if _is_innocuous_line(line):
                    continue
                findings.append(f"{p}: possible secret ({match.group(0)[:40]})")
    return findings


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    findings = scan(root)
    if findings:
        print("SECRET SCAN FAIL", file=sys.stderr)
        for f in findings:
            print(f"  {f}", file=sys.stderr)
        return 1
    print(f"SECRET SCAN PASS: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
