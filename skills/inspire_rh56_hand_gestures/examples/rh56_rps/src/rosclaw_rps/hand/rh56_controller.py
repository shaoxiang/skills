"""Abstract and concrete RH56 hand controllers."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from rosclaw_rh56.protocol.inspire_protocol import DOF_NAMES, InspireProtocol
from rosclaw_rh56.transport.serial_rs485 import SerialRS485Transport, TransportConfig

from ..gesture_schema import HandTelemetry


class HandController(ABC):
    """Interface for a dexterous hand controller."""

    @abstractmethod
    def move_to_gesture(self, gesture_name: str, angles: List[int], speed: int, force: int) -> bool:
        ...

    @abstractmethod
    def read_telemetry(self) -> HandTelemetry:
        ...

    @abstractmethod
    def safe_open(self) -> None:
        ...

    @abstractmethod
    def close(self) -> None:
        ...


class MockHandController(HandController):
    """Software-only hand controller for mock/camera-only modes."""

    def __init__(self, initial_angles: Optional[List[int]] = None):
        self._angles = list(initial_angles) if initial_angles else [1000] * 6
        self._last_gesture = "ready"
        self._connected = True

    def move_to_gesture(self, gesture_name: str, angles: List[int], speed: int, force: int) -> bool:
        self._angles = list(angles)
        self._last_gesture = gesture_name
        return True

    def read_telemetry(self) -> HandTelemetry:
        return HandTelemetry(
            timestamp=time.time(),
            angle_actual={name: self._angles[i] for i, name in enumerate(DOF_NAMES)},
            angle_set={name: self._angles[i] for i, name in enumerate(DOF_NAMES)},
        )

    def safe_open(self) -> None:
        self._angles = [1000] * 6
        self._last_gesture = "error"

    def close(self) -> None:
        self._connected = False


class RH56Controller(HandController):
    """RH56 RS485/Modbus RTU hand controller."""

    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        device_id: int = 2,
        baudrate: int = 115200,
        timeout_s: float = 0.3,
        default_speed: int = 600,
        default_force: int = 300,
    ):
        self._device_id = device_id
        self._default_speed = default_speed
        self._default_force = default_force
        self._proto = InspireProtocol(device_id=device_id)
        self._transport = SerialRS485Transport(
            TransportConfig(
                kind="serial_rs485",
                port=port,
                baudrate=baudrate,
                timeout_s=timeout_s,
            )
        )
        self._last_angles: List[int] = [1000] * 6

    def connect(self) -> None:
        self._transport.open()
        # Configure default speed/force once at connect.
        self._transport.write(self._proto.write_speed_set([self._default_speed] * 6))
        time.sleep(0.05)
        self._transport.write(self._proto.write_force_set([self._default_force] * 6))
        time.sleep(0.05)

    def move_to_gesture(self, gesture_name: str, angles: List[int], speed: int, force: int) -> bool:
        if not self._transport.is_open():
            self.connect()
        try:
            self._transport.write(self._proto.write_speed_set([speed] * 6))
            time.sleep(0.02)
            self._transport.write(self._proto.write_force_set([force] * 6))
            time.sleep(0.02)
            self._transport.write(self._proto.write_angle_set(angles))
            self._last_angles = list(angles)
            return True
        except Exception as exc:  # pragma: no cover
            print(f"RH56 move failed: {exc}")
            return False

    def read_telemetry(self) -> HandTelemetry:
        if not self._transport.is_open():
            self.connect()
        now = time.time()
        timeout = 0.2

        def _read_and_decode(read_fn, decode_fn):
            for _ in range(3):
                self._transport.write(read_fn())
                resp = self._transport.read(64, timeout_s=timeout)
                if resp and self._proto.__class__.__name__:  # keep protocol object alive
                    decoded = decode_fn(resp)
                    if decoded is not None:
                        return decoded
                time.sleep(0.02)
            return None

        angles = _read_and_decode(self._proto.read_angle_actual, self._proto.decode_angle_actual)
        positions = _read_and_decode(self._proto.read_position_actual, self._proto.decode_position_actual)
        forces = _read_and_decode(self._proto.read_force_actual, self._proto.decode_force_actual)
        currents = _read_and_decode(self._proto.read_current, self._proto.decode_current)
        temps = _read_and_decode(self._proto.read_temperature, self._proto.decode_temperature)
        errors = _read_and_decode(self._proto.read_error, self._proto.decode_error)
        statuses = _read_and_decode(self._proto.read_status, self._proto.decode_status)

        def _to_dict(values):
            if values is None:
                return {name: None for name in DOF_NAMES}
            return {name: values[i] for i, name in enumerate(DOF_NAMES)}

        return HandTelemetry(
            timestamp=now,
            angle_actual=_to_dict(angles),
            angle_set=_to_dict(positions),
            force_act=_to_dict(forces),
            current_ma=_to_dict(currents),
            temperature_c=_to_dict(temps),
            error=_to_dict(errors),
            status=_to_dict(statuses),
        )

    def safe_open(self) -> None:
        self.move_to_gesture("error", [1000] * 6, speed=400, force=250)

    def close(self) -> None:
        self._transport.close()


def build_hand_controller(config: dict) -> HandController:
    controller_type = config.get("controller", "mock")
    if controller_type == "rh56":
        return RH56Controller(
            port=config.get("port", "/dev/ttyUSB0"),
            device_id=int(config.get("device_id", 2)),
            baudrate=int(config.get("baudrate", 115200)),
            timeout_s=float(config.get("timeout_s", 0.3)),
            default_speed=int(config.get("default_speed", 600)),
            default_force=int(config.get("default_force", 300)),
        )
    return MockHandController()
