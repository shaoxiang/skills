#!/usr/bin/env python3
"""Wrapper: calibrate RH56 open-palm force baseline.

See rosclaw-rh56-runtime/scripts/20_force_baseline_calibration.py for details.
"""
from __future__ import annotations

import sys
from pathlib import Path

RUNTIME_SCRIPTS = Path(__file__).resolve().parent.parent.parent.parent / "rosclaw-rh56-runtime" / "scripts"
RUNTIME_SRC = RUNTIME_SCRIPTS.parent / "src"
if RUNTIME_SRC.exists():
    sys.path.insert(0, str(RUNTIME_SRC))

import runpy

runpy.run_path(str(RUNTIME_SCRIPTS / "20_force_baseline_calibration.py"), run_name="__main__")
