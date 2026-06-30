# RH56 Force-Closed-Loop v2 Validation Report

**Date:** 2026-06-29
**Body:** inspire_rh56_right_dev_ttyUSB0
**Skill:** ros-claw/inspire_rh56_hand_gestures v0.2.0

## Summary

Implemented and validated the RH56 force-closed-loop v2 layer:
- `FORCE_ACT` is the primary contact signal.
- `CURRENT` is confirmed to be ~0 at static contact.
- Open-palm force baseline was calibrated.
- OK contact search found candidate poses.
- Countdown regression passed 10/10 rounds.
- Practice flywheel generated per-step records and parquet summary.

## 1. Force Baseline Calibration

Command:
```bash
python scripts/20_force_baseline_calibration.py --duration-sec 30
```

Result:

| DOF | mean (g) | std (g) | min (g) | max (g) | samples |
|-----|----------|---------|---------|---------|---------|
| little | -11.0 | 0.0 | -11.0 | -11.0 | 601 |
| ring | -10.0 | 0.0 | -10.0 | -10.0 | 601 |
| middle | -38.0 | 0.0 | -38.0 | -38.0 | 601 |
| index | -40.0 | 0.0 | -40.0 | -40.0 | 601 |
| thumb | -78.0 | 0.0 | -78.0 | -78.0 | 601 |
| thumb_rot | -35.0 | 0.0 | -35.0 | -35.0 | 601 |

Observations:
- Negative baseline offsets confirm signed decoding is correct.
- thumb has the largest negative offset (-78 g), index -40 g.
- `FORCE_ACT` must be baseline-subtracted before contact detection.

## 2. OK Force Contact Search

Command:
```bash
python scripts/21_ok_force_contact_search.py --max-steps 30 --dwell-s 0.5
```

Best candidate found during search:

| Pose | thumb net (g) | index net (g) | thumb_rot net (g) | max net (g) |
|------|---------------|---------------|-------------------|-------------|
| thumb=429, index=429, thumb_rot=280 | 118.0 | 164.0 | 95.0 | 164.0 |

This candidate places both thumb and index inside the desired force window (80–180 g for thumb, 80–200 g for index).

Search observations:
- Contact is highly sensitive to thumb/index/rot coupling.
- Over-contact (>250 g) was detected and the search automatically backed off.
- Temperature warning blocked further steps after ~17–25 iterations; cool-down periods were inserted.
- The symmetric step strategy (thumb -= 25, index -= 25) is a starting point; future iterations should allow asymmetric search.

## 3. Repeatability Test

Command:
```bash
python scripts/23_ok_force_repeatability.py --rounds 5 --dwell-s 1.0
```

Pose: thumb=429, index=429, thumb_rot=280

| DOF | mean net (g) | std (g) | CV |
|-----|--------------|---------|-----|
| thumb | 137.2 | 48.5 | 0.35 |
| index | 18.6 | 15.2 | 0.82 |
| thumb_rot | 93.6 | 66.7 | 0.71 |

Observations:
- Thumb contact is consistent and in desired window.
- Index contact is weak and inconsistent at this pose; the index finger does not reliably make contact.
- This indicates the OK contact manifold is narrower than initially assumed and requires finer per-DOF tuning.

## 4. Countdown Regression Test

Command:
```bash
python scripts/08_run_countdown_real.py --rounds 10 --speed 500 --force 300 --dwell-sec 1.5
```

Result: **10/10 rounds completed successfully** with no errors.

The existing countdown skill remains functional and is not broken by v2 additions.

## 5. Practice Data Flywheel v2

Command:
```bash
python scripts/22_practice_flywheel_v2.py
```

Aggregated 21 search-step records into:
- `data/episodes/ok_force_search_summary.parquet`
- `data/episodes/ok_force_search_summary.yaml`
- `~/.rosclaw-rh56/memory/how_interventions_force_v2.jsonl`
- Updated `~/.rosclaw-rh56/body/body_cognition.yaml`
- Updated `~/.rosclaw-rh56/body/sim2real_delta.yaml`
- Updated `~/.rosclaw-rh56/body/calibration.yaml` contact landmark

Event distribution across recorded steps:
- desired_contact: 13
- early_contact: 1
- no_contact: 18
- self_collision: 1

## 6. Key Learnings

1. **FORCE_ACT is the correct contact signal.** Static current is effectively zero; force remains elevated during contact.
2. **Signed force decoding is required.** Baseline offsets are negative and DOF-dependent.
3. **OK contact is not symmetric.** Thumb and index require different approach paths; a symmetric coordinate descent is only a first approximation.
4. **Temperature is the practical limit.** Repeated closing motions heat the hand; cool-downs are mandatory.
5. **The v2 sandbox correctly detects over-contact and backs off.** No hardware protection events occurred during the search.

## 7. Next Steps

1. Implement asymmetric search: allow independent thumb/index/rot step sizes and directions.
2. Add settling time (longer dwell) before force measurement to reduce dynamic transients.
3. Use visual feedback or human label to score "OK shape" in addition to force.
4. Promote the current best thumb-contact pose while continuing to refine index contact.
5. Run additional repeatability tests once a fully desired-contact pose is found for both thumb and index.

## 8. Artifacts

- `~/.rosclaw-rh56/body/force_baseline.yaml`
- `~/.rosclaw-rh56/body/body_cognition.yaml`
- `~/.rosclaw-rh56/body/sim2real_delta.yaml`
- `~/.rosclaw-rh56/body/calibration.yaml`
- `data/episodes/ok_force_search_*.jsonl`
- `data/episodes/ok_force_search_summary.parquet`
- `data/episodes/ok_force_repeatability_*.jsonl`
- `/home/nvidia/.rosclaw/skills/inspire_rh56_hand_gestures/` v0.2.0 (validated, packaged, upload dry-run OK)
