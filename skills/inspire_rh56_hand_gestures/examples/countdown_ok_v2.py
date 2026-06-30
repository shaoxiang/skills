#!/usr/bin/env python3
"""Countdown gesture v2 for Inspire RH56 right hand.

Uses the promoted force-regulated OK pose from body_cognition.yaml instead of a
hard-coded pose. Falls back to the validated manual pose if no promoted pose
exists yet.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Add runtime src to path.
RUNTIME_SRC = Path(__file__).resolve().parent.parent.parent.parent / "rosclaw-rh56-runtime" / "src"
if RUNTIME_SRC.exists():
    sys.path.insert(0, str(RUNTIME_SRC))

import yaml

from rosclaw_rh56.protocol.inspire_protocol import DOF_NAMES, InspireProtocol
from rosclaw_rh56.transport.serial_rs485 import SerialRS485Transport, TransportConfig


def load_promoted_ok_pose():
    cognition_path = Path.home() / ".rosclaw-rh56" / "body" / "body_cognition.yaml"
    if cognition_path.exists():
        data = yaml.safe_load(cognition_path.read_text(encoding="utf-8"))
        pose = data.get("known_body_traits", {}).get("thumb_index_ok", {}).get("best_safe_contact_pose")
        if pose:
            return pose
    return {"thumb": 400, "index": 400, "thumb_rot": 250}


def main():
    port = "/dev/ttyUSB0"
    device_id = 2
    speed = 500
    force = 300
    dwell = 1.5

    config = TransportConfig(
        kind="serial_rs485",
        port=port,
        baudrate=115200,
        timeout_s=0.3,
        device_id=device_id,
    )
    transport = SerialRS485Transport(config)
    proto = InspireProtocol(device_id=device_id)
    transport.open()

    ok_pose = load_promoted_ok_pose()
    full_ok = {name: 1000 for name in DOF_NAMES}
    for k, v in ok_pose.items():
        if k in DOF_NAMES:
            full_ok[k] = int(v)

    gestures = [
        ("five", [1000, 1000, 1000, 1000, 1000, 1000]),
        ("four", [1000, 1000, 1000, 1000, 0, 1000]),
        ("three", [0, 1000, 1000, 1000, 0, 1000]),
        ("two", [0, 0, 1000, 1000, 0, 1000]),
        ("one", [0, 0, 0, 1000, 0, 1000]),
        ("ok_safe", [full_ok[name] for name in DOF_NAMES]),
    ]

    transport.write(proto.write_speed_set([speed] * 6))
    time.sleep(0.05)
    transport.write(proto.write_force_set([force] * 6))
    time.sleep(0.05)

    print(f"Countdown v2 on {port}; promoted OK pose = {ok_pose}")
    for name, angles in gestures:
        print(f"\n--> {name}: {dict(zip(DOF_NAMES, angles))}")
        transport.write(proto.write_angle_set(angles))
        time.sleep(dwell)

    print("\n--> open_palm")
    transport.write(proto.write_angle_set([1000] * 6))
    time.sleep(1.0)

    transport.close()
    print("Countdown v2 complete")


if __name__ == "__main__":
    main()
