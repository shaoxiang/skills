#!/usr/bin/env python3
"""Countdown gesture example for Inspire RH56 right hand.

Sequence: five -> four -> three -> two -> one -> ok_safe

This example demonstrates the validated OK pose for the Inspire RH56 dexterous
hand on /dev/ttyUSB0 (RS485 / Modbus RTU, slave id 2).

Validated parameters:
- speed=500  : ~1.6s for full-range motion
- force=300  : enough for reliable motion, low collision risk
- dwell=1.5s : visible pause between gestures

OK safe pose (from force-feedback contact search):
- thumb=400, index=400, thumb_rot=250
- little/ring/middle=1000 (extended)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# If running inside the skill package, add runtime src to path.
SKILL_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_SRC = SKILL_ROOT.parent.parent / "rosclaw-rh56-runtime" / "src"
if RUNTIME_SRC.exists():
    sys.path.insert(0, str(RUNTIME_SRC))

from rosclaw_rh56.transport.serial_rs485 import SerialRS485Transport, TransportConfig
from rosclaw_rh56.protocol.inspire_protocol import InspireProtocol, DOF_NAMES


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

    # Initialize speed and force thresholds.
    transport.write(proto.write_speed_set([speed] * 6))
    time.sleep(0.05)
    transport.write(proto.write_force_set([force] * 6))
    time.sleep(0.05)

    # Gesture targets in raw angle units (0=closed/bent, 1000=open/extended).
    gestures = [
        ("five", [1000, 1000, 1000, 1000, 1000, 1000]),
        ("four", [1000, 1000, 1000, 1000, 0, 1000]),
        ("three", [0, 1000, 1000, 1000, 0, 1000]),
        ("two", [0, 0, 1000, 1000, 0, 1000]),
        ("one", [0, 0, 0, 1000, 0, 1000]),
        ("ok_safe", [1000, 1000, 1000, 400, 400, 250]),
    ]

    print(f"Running countdown + OK on {port} (speed={speed}, force={force})")
    for name, angles in gestures:
        print(f"\n--> {name}: {dict(zip(DOF_NAMES, angles))}")
        transport.write(proto.write_angle_set(angles))
        time.sleep(dwell)

    # Return to safe open palm.
    print("\n--> open_palm")
    transport.write(proto.write_angle_set([1000] * 6))
    time.sleep(1.0)

    transport.close()
    print("Countdown + OK complete")


if __name__ == "__main__":
    main()
