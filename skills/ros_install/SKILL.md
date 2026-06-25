# SKILL.md

## Skill ID

`ros-claw/ros_install`

## Intent

Install, verify, or repair a ROS / ROS 2 environment on the host workstation.

## Preconditions

- `host_state` available (OS release, existing ROS installation, apt sources).
- For destructive actions, `--execute` must be set and `sudo` confirmed.

## Effects

- `ros_setup_sourced == true`
- `roscli_available == true`
- `rosdep_initialized == true`

## Runtime Contract

- Input: `host_state`, optional `target_distro`, `install_mode`, `allow_sudo`, `execute`
- Output: `install_plan`, `executed_commands`, `verification_report`

## Safety Envelope

- `dry_run` by default.
- Host modification only when `execute == true`.
- EOL / unsupported distros blocked by sandbox checks.

## Evidence

- See `evidence/reports/`
