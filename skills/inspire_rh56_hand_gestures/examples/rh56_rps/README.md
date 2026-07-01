# RH56 Rock-Paper-Scissors Demo

A fun, embodied-agent demo that plays **rock-paper-scissors** with a human using:

- **Inspire RH56** right dexterous hand (RS485 / Modbus RTU)
- **ROS 2 image topic** (e.g. from an already-running RealSense node) or USB camera for human gesture recognition
- **ROSClaw BodySense** self-verification of the robot's own gesture
- **commit-reveal fairness**: the robot commits its choice *before* seeing the human gesture

> This example is bundled with the `inspire_rh56_hand_gestures` skill. It is not a pre-baked animation: the robot promises its move, counts down with its own hand, reads your hand, executes its own gesture, and uses body feedback to confirm it really did what it intended.

---

## Quick start

```bash
cd examples/rh56_rps

# 1. Mock mode (no hardware)
python3 -m rosclaw_rps.cli --mode mock --rounds 5

# 2. Hand-test mode (RH56 only, cycles all gestures)
python3 -m rosclaw_rps.cli --mode hand-test --hand-port /dev/ttyUSB0

# 3. Camera-only mode (vision pipeline without hand)
python3 -m rosclaw_rps.cli --mode camera-only --camera ros2

# 4. Full demo (ROS2 RealSense + RH56) — simplest launcher
./run_ui.sh --rounds 20

# Headless / SSH (no OpenCV window)
./run_ui.sh --auto --headless --rounds 20
```

---

## Project layout

```text
examples/rh56_rps/
  configs/
    rh56_gestures.yaml      # Gesture angle targets, speed/force, verify tolerances
    rps_demo.yaml           # Demo runtime configuration
  src/rosclaw_rps/
    cli.py                  # Main entry point and mode dispatch
    game_engine.py          # Commit-reveal fairness, state machine, RPS rules
    gesture_schema.py       # Dataclasses for gestures, telemetry, rounds
    hand/
      rh56_controller.py    # RH56 / mock HandController
      gesture_executor.py   # Execute + verify a gesture with safe recovery
    vision/
      camera_source.py      # Mock / USB / RealSense / ROS 2 camera sources
      hand_gesture_recognizer.py  # Keyboard / mock / MediaPipe recognizers
      majority_vote.py      # Temporal majority vote over a capture window
    body/
      failure_detector.py   # BodySense failure checks from telemetry
    logging/
      round_logger.py       # JSONL round logs, telemetry, frames
    ui/
      simple_opencv_ui.py   # OpenCV overlay
  tests/
    test_game_engine.py
    test_gesture_mapping.py
    test_human_gesture_majority_vote.py
    test_mock_round.py
```

---

## RH56 gesture mapping

| Game meaning | Gesture  | DOF angles `[little, ring, middle, index, thumb, thumb_rot]` |
| ------------ | -------- | ------------------------------------------------------------- |
| Ready        | OK       | `[1000, 1000, 1000, 410, 420, 300]` |
| Rock         | fist     | `[0, 0, 0, 0, 0, 1000]` |
| Paper        | open palm | `[1000, 1000, 1000, 1000, 1000, 1000]` |
| Scissors     | two fingers | `[0, 0, 1000, 1000, 0, 1000]` |
| Countdown 3  | three fingers | `[0, 1000, 1000, 1000, 0, 1000]` |
| Countdown 2  | two fingers | `[0, 0, 1000, 1000, 0, 1000]` |
| Countdown 1  | one finger | `[0, 0, 0, 1000, 0, 1000]` |
| Win          | OK       | `[1000, 1000, 1000, 410, 420, 300]` |
| Lose         | one finger | `[0, 0, 0, 1000, 0, 1000]` |
| Draw         | three fingers | `[0, 1000, 1000, 1000, 0, 1000]` |
| Error        | safe open | `[1000, 1000, 1000, 1000, 1000, 1000]` |

Angles are raw firmware units where `0 = closed/bent` and `1000 = open/extended`.

---

## Run modes

### Mock mode

No camera, no hand. Use keyboard (`r`/`p`/`s`) for the human and a mock hand.

```bash
python -m rosclaw_rps.cli --mode mock --rounds 100 --auto
```

### Hand-test mode

Cycles through all RH56 gestures without vision. Use this to tune the rock/fist gesture and verify telemetry.

```bash
python -m rosclaw_rps.cli --mode hand-test --hand-port /dev/ttyUSB0
```

### Camera-only mode

Tests the vision pipeline. Supports `mock`, `usb`, and `realsense` sources.

```bash
python -m rosclaw_rps.cli --mode camera-only --camera usb
```

### Full demo

RealSense + RH56. The robot commits, counts down, captures your gesture, executes its own, verifies, and reacts.

```bash
python -m rosclaw_rps.cli --mode full --camera realsense --hand-port /dev/ttyUSB0 --rounds 20
```

---

## Tests

```bash
pytest tests -q
```

---

## Safety notes

- Every round starts from `ready` / safe open.
- Gesture verification failure triggers immediate `safe_open`.
- `current`, `force`, `temperature`, and `status` are checked after each move.
- The robot choice is committed and hashed **before** the human capture window opens.

---

## Next steps

1. Tune the `rock` fist on real hardware (thumb position / force).
2. Calibrate MediaPipe recognition for your lighting and hand distance.
3. Add sound / better overlay for video demos.
4. Aggregate rounds into ROSClaw practice memory for failure analysis.
