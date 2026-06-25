#!/usr/bin/env python3
"""Sync registry/skills.json to the ROSClaw Hub using ADMIN_API_KEY."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def build_payload(item: dict, readme_text: str) -> dict:
    return {
        "name": item["name"],
        "display_name": item.get("display_name"),
        "description": item.get("description", ""),
        "long_description": readme_text,
        "github_repo_url": item["source"]["repo"],
        "author_name": "ROSClaw Team",
        "author_url": "https://github.com/ros-claw",
        "category": item.get("category", "general"),
        "robot_types": item.get("robot_types", ["universal"]),
        "compatible_robots": item.get("compatible_robots", ["universal"]),
        "tags": item.get("tags", []),
        "version": item.get("version"),
        "dependencies": [],
    }


def main() -> int:
    if len(sys.argv) != 2:
        fail("Usage: sync_hub.py registry/skills.json")

    api_key = os.environ.get("ROSCLAW_ADMIN_API_KEY")
    if not api_key:
        fail("Missing ROSCLAW_ADMIN_API_KEY")

    base_url = os.environ.get("ROSCLAW_HUB_BASE_URL", "https://www.rosclaw.io").rstrip("/")

    registry_path = Path(sys.argv[1])
    root = registry_path.resolve().parents[1]
    registry = json.loads(registry_path.read_text(encoding="utf-8"))

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; rosclaw-catalog-sync/1.0)",
    }

    for item in registry["skills"]:
        name = item["name"]
        readme_rel = item.get("files", {}).get("readme")
        readme_text = ""
        if readme_rel:
            readme_path = root / readme_rel
            if readme_path.exists():
                readme_text = readme_path.read_text(encoding="utf-8")

        payload = build_payload(item, readme_text)

        get_url = f"{base_url}/api/skills/{name}"
        post_url = f"{base_url}/api/skills"
        put_url = f"{base_url}/api/skills/{name}"

        print(f"Syncing {name}")

        get_res = requests.get(get_url, timeout=30)

        if get_res.status_code == 200:
            res = requests.put(put_url, headers=headers, json=payload, timeout=30)
        elif get_res.status_code == 404:
            res = requests.post(post_url, headers=headers, json=payload, timeout=30)
        else:
            print(f"Warning: GET {name} returned {get_res.status_code}; trying POST")
            res = requests.post(post_url, headers=headers, json=payload, timeout=30)

        if res.status_code not in (200, 201):
            fail(f"Failed to sync {name}: status={res.status_code}, body={res.text}")

        print(f"OK: {name}")

    return 0


if __name__ == "__main__":
    # Allow running without import guard in non-package context.
    import json

    raise SystemExit(main())
