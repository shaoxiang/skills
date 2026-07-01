#!/usr/bin/env bash
# Launch the RH56 Rock-Paper-Scissors demo.
# This example is part of the inspire_rh56_hand_gestures skill.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate ROS 2 if available (required for the ROS2 RealSense camera bridge).
if [ -f /opt/ros/jazzy/setup.bash ]; then
    source /opt/ros/jazzy/setup.bash
fi

# Make sure the local rosclaw_rps package is importable.
export PYTHONPATH="${PYTHONPATH}:${SCRIPT_DIR}/src"

# If rosclaw_rh56 is not installed in the active Python environment, try the
# standard sibling runtime layout next to the skills directory.
if ! python3 -c "import rosclaw_rh56" 2>/dev/null; then
    CANDIDATE="${SCRIPT_DIR}/../../../rosclaw-rh56-runtime/src"
    if [ -d "${CANDIDATE}/rosclaw_rh56" ]; then
        export PYTHONPATH="${PYTHONPATH}:${CANDIDATE}"
    fi
fi

cd "${SCRIPT_DIR}"
exec python3 -m rosclaw_rps.cli --mode full "$@"
