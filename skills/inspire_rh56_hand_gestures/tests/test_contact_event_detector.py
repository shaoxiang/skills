"""Unit tests for RH56 ContactEventDetector v2.1."""
from __future__ import annotations

import sys
from pathlib import Path

RUNTIME_SRC = Path(__file__).resolve().parent.parent.parent.parent.parent / "rosclaw-rh56-runtime" / "src"
if RUNTIME_SRC.exists():
    sys.path.insert(0, str(RUNTIME_SRC))

from rosclaw_rh56.body.body_state import RH56BodyState
from rosclaw_rh56.body.contact_event_detector import (
    ContactEventDetector,
    ContactEventDetectorConfig,
    ContactEventRecord,
    event_distribution,
    tag_distribution,
)
from rosclaw_rh56.protocol.inspire_protocol import DOF_NAMES
from rosclaw_rh56.sensors.force_model import ForceBaseline, ForceModel


def _make_state(**kwargs) -> RH56BodyState:
    defaults = {
        "target_angle": {},
        "actual_angle": {},
        "force_raw_g": {},
        "force_baseline_g": {},
        "force_net_g": {},
        "current_ma": {},
        "status": {},
        "error": {},
        "temperature_c": {},
    }
    defaults.update(kwargs)
    return RH56BodyState(ts=0.0, **defaults)


def _detector():
    baseline = {name: ForceBaseline(mean=0.0) for name in DOF_NAMES}
    return ContactEventDetector(ForceModel(baseline=baseline))


def test_no_contact():
    det = _detector()
    state = _make_state(
        target_angle={"thumb": 400},
        actual_angle={"thumb": 400},
        force_net_g={"thumb": 10.0},
    )
    record = det.update(state)
    assert isinstance(record, ContactEventRecord)
    assert record.primary_event == "no_contact"


def test_desired_contact():
    det = _detector()
    state = _make_state(
        target_angle={"thumb": 400, "index": 400},
        actual_angle={"thumb": 400, "index": 400},
        force_net_g={"thumb": 100.0, "index": 120.0},
    )
    record = det.update(state)
    assert record.primary_event == "desired_contact"
    assert "no_contact" not in record.secondary_tags


def test_thumb_only_contact():
    det = _detector()
    state = _make_state(
        target_angle={"thumb": 400, "index": 400},
        actual_angle={"thumb": 400, "index": 400},
        force_net_g={"thumb": 100.0, "index": 10.0},
    )
    record = det.update(state)
    assert record.primary_event == "thumb_only_contact"


def test_over_contact():
    det = _detector()
    state = _make_state(
        target_angle={"thumb": 400},
        actual_angle={"thumb": 400},
        force_net_g={"thumb": 300.0},
    )
    record = det.update(state)
    assert record.primary_event == "over_contact"


def test_hardware_protection_from_status():
    det = _detector()
    state = _make_state(status={"thumb": 0x04})
    record = det.update(state)
    assert record.primary_event == "hardware_protection"


def test_hardware_protection_from_error():
    det = _detector()
    state = _make_state(error={"thumb": 0x01})
    record = det.update(state)
    assert record.primary_event == "hardware_protection"


def test_temperature_limited():
    det = _detector()
    state = _make_state(temperature_c={"thumb": 46})
    record = det.update(state)
    assert record.primary_event == "temperature_limited"


def test_early_contact():
    det = _detector()
    state = _make_state(
        target_angle={"thumb": 400},
        actual_angle={"thumb": 600},
        force_net_g={"thumb": 100.0},
    )
    record = det.update(state)
    assert record.primary_event == "early_contact"


def test_motion_blocked():
    det = _detector()
    state = _make_state(
        target_angle={"thumb": 400},
        actual_angle={"thumb": 600},
        force_net_g={"thumb": 260.0},
    )
    record = det.update(state)
    assert record.primary_event == "motion_blocked"


def test_safety_priority_overrides_desired_contact():
    det = _detector()
    state = _make_state(
        target_angle={"thumb": 400},
        actual_angle={"thumb": 400},
        force_net_g={"thumb": 100.0},
        status={"thumb": 0x04},
    )
    record = det.update(state)
    assert record.primary_event == "hardware_protection"


def test_event_distribution_accounting():
    det = _detector()
    records = [
        det.update(_make_state(force_net_g={"thumb": 10.0})),
        det.update(_make_state(force_net_g={"thumb": 100.0, "index": 120.0})),
        det.update(_make_state(force_net_g={"thumb": 300.0})),
    ]
    dist = event_distribution(records)
    assert sum(dist.values()) == len(records)
    assert dist.get("no_contact") == 1
    assert dist.get("desired_contact") == 1
    assert dist.get("over_contact") == 1


def test_tag_distribution_independent():
    det = _detector()
    records = [
        det.update(_make_state(force_net_g={"thumb": 100.0, "index": 10.0})),
    ]
    primary_dist = event_distribution(records)
    tag_dist = tag_distribution(records)
    assert sum(primary_dist.values()) == len(records)
    assert "thumb_only_contact" not in tag_dist  # it is the primary
    assert "desired_contact" not in tag_dist


def test_body_state_fields_populated():
    det = _detector()
    state = _make_state(
        target_angle={"thumb": 400, "index": 400},
        actual_angle={"thumb": 400, "index": 400},
        force_net_g={"thumb": 100.0, "index": 120.0},
    )
    det.update(state)
    assert state.primary_event == "desired_contact"
    assert isinstance(state.secondary_tags, list)
    assert "desired_contact" not in state.secondary_tags


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
