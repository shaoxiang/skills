"""Unit tests for RH56 ForceModel v2.1.

Prefers the generic `rosclaw.body.force_model` types introduced in rosclaw PR#53
and falls back to the local `rosclaw_rh56` runtime if rosclaw is not yet installed.
"""
from __future__ import annotations

import sys
from pathlib import Path

RUNTIME_SRC = Path(__file__).resolve().parent.parent.parent.parent.parent / "rosclaw-rh56-runtime" / "src"
if RUNTIME_SRC.exists():
    sys.path.insert(0, str(RUNTIME_SRC))

# Prefer generic rosclaw types; fallback to legacy rosclaw_rh56 runtime.
try:
    from rosclaw.body.force_model import DofForceWindow, ForceBaseline, ForceModel
except Exception:  # pragma: no cover - fallback for older runtimes
    from rosclaw_rh56.sensors.force_model import DofForceWindow, ForceBaseline, ForceModel

try:
    from rosclaw_rh56.protocol.inspire_protocol import DOF_NAMES
except Exception:  # pragma: no cover
    DOF_NAMES = ["little", "ring", "middle", "index", "thumb", "thumb_rot"]


def _approx(a, b, tol=1e-6):
    return abs(a - b) < tol


def test_net_force_subtracts_baseline():
    baseline = {
        "thumb": ForceBaseline(mean=-50.0),
        "index": ForceBaseline(mean=-35.0),
    }
    model = ForceModel(baseline=baseline)
    raw = {"thumb": 100.0, "index": 50.0, "middle": 0.0}
    net = model.net_force(raw)
    assert _approx(net["thumb"], 150.0)
    assert _approx(net["index"], 85.0)
    assert _approx(net["middle"], 0.0)


def test_contact_level_thresholds_default():
    model = ForceModel()
    assert model.contact_level(10.0, dof="thumb") == "none"
    assert model.contact_level(60.0, dof="thumb") == "soft"
    assert model.contact_level(100.0, dof="thumb") == "desired"
    assert model.contact_level(200.0, dof="thumb") == "strong"
    assert model.contact_level(260.0, dof="thumb") == "hard"
    assert model.contact_level(400.0, dof="thumb") == "emergency"


def test_per_dof_contact_windows():
    model = ForceModel(
        contact_windows_g={
            "thumb": DofForceWindow(desired_min=80, desired_max=180, hard=250, emergency=350),
            "index": DofForceWindow(desired_min=80, desired_max=200, hard=250, emergency=350),
        }
    )
    assert model.is_desired_contact(190.0, dof="index")
    assert not model.is_desired_contact(190.0, dof="thumb")
    assert model.is_over_contact(260.0, dof="thumb")


def test_desired_and_over_contact():
    model = ForceModel()
    assert model.is_desired_contact(120.0, dof="thumb")
    assert not model.is_desired_contact(10.0, dof="thumb")
    assert model.is_over_contact(260.0, dof="thumb")
    assert not model.is_over_contact(100.0, dof="thumb")


def test_missing_baseline_blocks_contact_search():
    model = ForceModel()
    missing = model.list_missing_baselines()
    assert set(missing) == set(DOF_NAMES)


def test_current_not_used_for_static_contact():
    model = ForceModel()
    assert model.policy.get("use_current_for_static_contact") is False
    assert model.policy.get("use_force_for_static_contact") is True


def test_negative_baseline_subtraction():
    baseline = {"thumb": ForceBaseline(mean=-78.0)}
    model = ForceModel(baseline=baseline)
    net = model.net_force({"thumb": -10.0})
    assert _approx(net["thumb"], 68.0)


if __name__ == "__main__":
    failures = 0
    for name in list(globals().keys()):
        fn = globals()[name]
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:
                print(f"FAIL {name}: {e}")
                failures += 1
    sys.exit(1 if failures else 0)
