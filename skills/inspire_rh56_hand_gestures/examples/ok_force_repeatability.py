#!/usr/bin/env python3
"""Wrapper: OK force repeatability test.

See rosclaw-rh56-runtime/scripts/23_ok_force_repeatability.py for details.
"""
from __future__ import annotations

import sys
from pathlib import Path

RUNTIME_SCRIPTS = Path(__file__).resolve().parent.parent.parent.parent / "rosclaw-rh56-runtime" / "scripts"
RUNTIME_SRC = RUNTIME_SCRIPTS.parent / "src"
if RUNTIME_SRC.exists():
    sys.path.insert(0, str(RUNTIME_SRC))

import runpy

runpy.run_path(str(RUNTIME_SCRIPTS / "23_ok_force_repeatability.py"), run_name="__main__")
