# SKILL.md — Inspire RH56 Hand Gesture Countdown

## Skill ID

`ros-claw/inspire_rh56_hand_gestures`

## Intent

Execute the Inspire RH56 right-hand gesture countdown (five, four, three, two, one, OK) and verify the final OK pose.

## Preconditions

- Robot: `inspire_rh56_right` connected over RS485 / Modbus RTU.
- Port `/dev/ttyUSB0` (or configured port) accessible.
- `robot_state` provider returning joint positions, force feedback, temperature, and STATUS registers.
- Hand calibrated so raw angle 0 = closed/bent, 1000 = open/extended.
- Hand at a known safe start pose (open palm recommended).

## Effects

- Hand visits each countdown gesture.
- Final pose is the validated OK contact pose.
- `task_completed == true` if all gestures are reached within timeout and no safety fault is reported.

## Runtime Contract

- **Input:** `robot_state`
- **Output:** `trace` + `runtime_events`
- **Entrypoint:** `behavior_tree.xml`
- **Runtime mode:** `sandbox_first` by default

## Gesture targets (raw angles)

| Gesture | little | ring | middle | index | thumb | thumb_rot |
|---------|--------|------|--------|-------|-------|-----------|
| five    | 1000   | 1000 | 1000   | 1000  | 1000  | 1000      |
| four    | 1000   | 1000 | 1000   | 1000  | 0     | 1000      |
| three   | 0      | 1000 | 1000   | 1000  | 0     | 1000      |
| two     | 0      | 0    | 1000   | 1000  | 0     | 1000      |
| one     | 0      | 0    | 0      | 1000  | 0     | 1000      |
| ok_safe | 1000   | 1000 | 1000   | 400   | 400   | 250       |

## Safety Envelope

- Target angles clamped to [0, 1000].
- Speed ≤ 500, force ≤ 300 g.
- Dwell 1.5 s between gestures.
- Abort if `STATUS` ∈ {5, 6, 7} (current protection, locked rotor, fault).
- Abort if any actuator temperature exceeds its configured limit.
- Verify final OK pose with force feedback; expect elevated `FORCE_ACT` on thumb and index.

## Evidence

- See `evidence/reports/`.
- See `examples/countdown_ok.py` for the validated reference implementation.
