#!/usr/bin/env python3
"""Validate a single ROSClaw Skill directory."""

from __future__ import annotations

import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "skill.yaml",
    "behavior_tree.xml",
    "providers.yaml",
    "e-urdf-compat.yaml",
    "safety.yaml",
    "dojo.yaml",
    "darwin_eval.yaml",
    "lineage.yaml",
]


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def load_yaml(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        fail(f"Failed to parse YAML {path}: {e}")


def main() -> int:
    if len(sys.argv) != 2:
        fail("Usage: validate_skill.py skills/<skill_name>")

    root = Path(sys.argv[1]).resolve()
    if not root.exists() or not root.is_dir():
        fail(f"Skill directory not found: {root}")

    for rel in REQUIRED_FILES:
        path = root / rel
        if not path.exists():
            fail(f"Missing required file: {rel}")

    skill = load_yaml(root / "skill.yaml")
    metadata = skill.get("metadata", {})
    identity = skill.get("identity", {})
    status = skill.get("status", {})

    name = metadata.get("name")
    version = metadata.get("version")
    stage = metadata.get("stage")

    if not name:
        fail("skill.yaml missing metadata.name")
    if not version:
        fail("skill.yaml missing metadata.version")
    if not re.match(r"^\d+\.\d+\.\d+([\-+][A-Za-z0-9\.\-]+)?$", version):
        fail(f"Invalid version: {version}")

    allowed_stages = {
        "draft",
        "candidate",
        "source_verified",
        "ci_passed",
        "official_verified",
        "installable",
        "deprecated",
        "revoked",
    }
    if stage not in allowed_stages:
        fail(f"Invalid metadata.stage: {stage}")

    source_subdir = identity.get("source_subdir")
    if source_subdir:
        expected = f"skills/{name}"
        if source_subdir != expected:
            fail(f"identity.source_subdir must be {expected!r}, got {source_subdir!r}")

    git_repo = identity.get("git_repo")
    if git_repo and "ros-claw/skills" not in git_repo:
        fail(f"Official catalog skills must use git_repo 'https://github.com/ros-claw/skills', got {git_repo!r}")

    try:
        ET.parse(root / "behavior_tree.xml")
    except Exception as e:
        fail(f"Invalid behavior_tree.xml: {e}")

    safety = load_yaml(root / "safety.yaml")
    if "hard_constraints" not in safety:
        fail("safety.yaml missing hard_constraints")

    if safety.get("runtime_mode", {}).get("default") == "real_robot_unguarded":
        fail("real_robot_unguarded is not allowed as default runtime mode")

    # Scan for secrets and local paths.
    repo_root = root.parents[1]
    for script_name in ("scan_secrets.py", "scan_local_paths.py"):
        script = repo_root / "scripts" / script_name
        if not script.exists():
            continue
        result = subprocess.run([sys.executable, str(script), str(root)], capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            sys.exit(1)
        print(result.stdout.strip())

    print(f"PASS: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
