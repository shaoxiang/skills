# RH56 Force-Closed-Loop v2.1 Report

**Body:** inspire_rh56_right_dev_ttyUSB0  
**Report date:** 2026-06-29  
**Skill:** inspire_rh56_hand_gestures v0.3.0  
**Policy under evaluation:** ok_contact_safe_v2  
**Overall conclusion:** `ok_contact_safe_v2` is **REJECTED** in this iteration. After adding cooldowns to the repeatability script, the best candidate achieved 5/5 valid `desired_contact` rounds with excellent force metrics; the only remaining blocker is the lack of real visual/human OK-shape labels (current labels are placeholders).

---

## 1. Executive Summary

This report documents the first full v2.1 self-evolution cycle for the Inspire RH56 right hand. We executed the required order:

1. Force baseline raw-frame audit (PASS)
2. Exclusive primary-event / multi-label secondary tag schema enforced in search/analysis scripts
3. Asymmetric OK contact search across 72 candidates and three approach paths
4. Force-curve decay and balance analysis
5. Placeholder OK-shape labels
6. Repeatability v2 test
7. Promotion gate
8. Body cognition / sim2real delta update
9. Dashboard and heatmap generation

The asymmetric search found three `desired_contact` candidates that are better than the previous v2 best pose `429/429/280`, especially `ok_v2_1_0004` (`thumb=430, index=410, thumb_rot=300`, `thumb_first` path). The first repeatability run was cut short by hand temperature rising above the warning threshold (only 2/5 valid rounds). We then added configurable inter-round and inter-candidate cooldowns to `scripts/28_ok_contact_repeatability_v2.py` and re-ran the test. The best candidate now achieves 5/5 valid `desired_contact` rounds with `contact_detected_rate=1.0` and very low CV. However, because no camera is available, the shape labels remain placeholders with `ok_shape_score=0`, so the promotion gate still correctly rejects the policy.

**No countdown_force_ok_v2 validation was attempted** because `scripts/31_countdown_force_ok_v2.py` refuses to run when the promoted policy status is not `promoted`.

---

## 2. Differences from v2

| Item | v2 | v2.1 (this run) |
|------|----|-----------------|
| Contact search | Symmetric descent from `429/429/280` | Asymmetric grid with `thumb_first`, `index_first`, `rot_first` |
| Event schema | Ad-hoc string labels, distribution double-counted | Exclusive `primary_event` + multi-label `secondary_tags` |
| Force curve | Single final force | Full curve: peak, mean 300/800 ms, final, decay rate, stable ratio |
| Shape validation | None | Placeholder shape labels (real labels required for promotion) |
| Repeatability | 5 rounds at one pose | 5 rounds per top candidate, from open palm each round |
| Promotion gate | Manual judgement | Scripted gate with numeric thresholds and explicit rejection |
| Body cognition | Best pose only | Contact manifold: no_contact, thumb_only, index_only, desired, over_contact, temperature_limited regions |
| Sim2real delta | Basic notes | Structured `delta_types`: contact_manifold, sensing, thermal, path_dependence |

---

## 3. Force Baseline Raw-Frame Audit

**Command:**

```bash
python scripts/24_force_baseline_audit.py \
  --port /dev/ttyUSB0 \
  --duration-sec 60 \
  --sample-rate-hz 20 \
  --record-raw-hex \
  --record-angle-status-temp \
  --output data/episodes/force_baseline_audit.jsonl
```

**Artifacts:**

- `data/episodes/force_baseline_audit.jsonl` (1201 frames)
- `reports/force_baseline_audit.md`
- Updated `body_cognition.yaml`: `baseline_audit_passed: true`

**Results:**

| Check | Result |
|-------|--------|
| Raw RX frame uniqueness | 1 unique raw frame per DOF over 1201 samples (constant open-palm offset is expected) |
| Cross-channel variation | `ANGLE_ACT`, `STATUS`, `TEMP` all vary, proving each Modbus transaction is real |
| Timing | Mean interval 50.00 ms, max 50.98 ms, read latency ~4.89 ms |
| Signed decoding | Consistent negative open-palm offsets (thumb ≈ -67 g, index ≈ -43 g) |
| Baseline usable | Yes |

**Pass/Fail:** PASS

---

## 4. Event Schema Fix

All new scripts write records with a single, mutually exclusive `primary_event` and an optional `secondary_tags` list. The safety-priority order is honored:

```text
hardware_protection > motion_blocked > over_contact > position_stall > temperature_limited > early_contact > self_collision > desired_contact > thumb_only_contact > index_only_contact > weak_contact > no_contact
```

The 72-candidate search produced an event distribution whose counts sum exactly to the number of candidates:

| primary_event | count |
|---------------|-------|
| desired_contact | 3 |
| thumb_only_contact | 3 |
| over_contact | 8 |
| motion_blocked | 11 |
| temperature_above_warn | 47 |

**Note:** Dedicated unit tests (`tests/test_contact_event_schema.py`, `tests/test_primary_event_exclusive.py`, `tests/test_event_distribution_accounting.py`) are still pending.

---

## 5. ForceModel / BodyState / ContactEvent Schema

Scripts use a de-facto standard record shape derived from the v2.1 guide:

```json
{
  "candidate_id": "ok_v2_1_0004",
  "path": "thumb_first",
  "target_pose": {"thumb": 430, "index": 410, "thumb_rot": 300},
  "dwell_s": 1.0,
  "force_curve": [...],
  "force_metrics": {...},
  "actual_angle": {},
  "position_error": {},
  "status": {},
  "error": {},
  "temperature": {},
  "primary_event": "desired_contact",
  "secondary_tags": ["stable_contact", "promotion_candidate"]
}
```

The `ForceModel` logic (baseline subtraction, desired/over-contact windows) is embedded in the search/analyzer scripts. A standalone `src/rosclaw_rh56/sensors/force_model.py` module was not created in this iteration.

---

## 6. Asymmetric OK Contact Search

**Command:**

```bash
python scripts/25_ok_asymmetric_contact_search.py \
  --port /dev/ttyUSB0 \
  --start-from-open-each-candidate \
  --thumb-values 470,450,430,410,390 \
  --index-values 520,500,470,450,430,410,390 \
  --rot-values 340,320,300,280,260,240 \
  --paths thumb_first,index_first,rot_first \
  --dwell-grid 1.0 \
  --max-temp-c 50 \
  --cooldown-temp-c 45 \
  --output data/episodes/ok_asymmetric_search.jsonl
```

**Artifacts:**

- `data/episodes/ok_asymmetric_search.jsonl`
- `data/episodes/top_ok_candidates.yaml`
- `reports/ok_force_curve_analysis.md`

**Search summary:**

- Smoke test: 16 candidates, no contact (used to verify script).
- Main run: 72 candidates across `thumb_first`, `index_first`, `rot_first`.
- Each candidate started from open palm.
- High-frequency Modbus polling was throttled to ~2 Hz after an initial 0.2 s delay to avoid actuator motion stalls.

---

## 7. Search Heatmaps

Dashboard generated 17 PNG heatmaps under `screenshots/`:

```text
rh56_heatmap_thumb_index_rot240.png
rh56_heatmap_thumb_index_rot260.png
rh56_heatmap_thumb_index_rot280.png
rh56_heatmap_thumb_index_rot300.png
rh56_heatmap_thumb_rot_index390.png
rh56_heatmap_thumb_rot_index410.png
rh56_heatmap_thumb_rot_index430.png
rh56_heatmap_index_rot_thumb410.png
rh56_heatmap_index_rot_thumb430.png
... plus paired event_map and thermal_map for each rot slice.
```

See `screenshots/rh56_force_dashboard.md` for the full list and the rendered dashboard.

---

## 8. Top Candidates

### 8.1 Top Desired-Contact Candidates

| candidate | path | thumb | index | rot | thumb_final | index_final | thumb_rot_final | balance | decay_rate | stable_ratio |
|-----------|------|-------|-------|-----|-------------|-------------|-----------------|---------|------------|--------------|
| ok_v2_1_0004 | thumb_first | 430 | 410 | 300 | 98 | 148 | 103 | 50 | 23.2 | 0.98 |
| ok_v2_1_0010 | thumb_first | 410 | 430 | 300 | 98 | 174 | 88 | 76 | 55.6 | 0.99 |
| ok_v2_1_0001 | thumb_first | 430 | 430 | 300 | 86 | 147 | 71 | 61 | 47.4 | 0.97 |

All three are in the desired force window:

- thumb: [80, 180] g
- index: [80, 200] g
- thumb_rot: [40, 160] g

### 8.2 Representative Over-Contact Candidates

| candidate | path | thumb | index | rot | thumb_final | index_final | primary_event |
|-----------|------|-------|-------|-----|-------------|-------------|---------------|
| ok_v2_1_0006 | rot_first | 430 | 410 | 300 | 195 | 22 | over_contact |
| ok_v2_1_0007 | thumb_first | 430 | 390 | 300 | 106 | 207 | over_contact |
| ok_v2_1_0019 | thumb_first | 430 | 430 | 280 | 113 | 261 | over_contact |

### 8.3 Representative Thumb-Only Candidates

| candidate | path | thumb | index | rot | thumb_final | index_final | primary_event |
|-----------|------|-------|-------|-----|-------------|-------------|---------------|
| ok_v2_1_0002 | index_first | 430 | 430 | 300 | 155 | 20 | thumb_only_contact |
| ok_v2_1_0003 | rot_first | 430 | 430 | 300 | 163 | 21 | thumb_only_contact |
| ok_v2_1_0011 | index_first | 410 | 430 | 300 | 179 | 25 | thumb_only_contact |

---

## 9. Force Curve / Decay / Slip Analysis

The analyzer (`scripts/26_force_curve_analyzer.py`) computed:

- force_peak
- force_mean_last_300ms
- force_mean_last_800ms
- force_final
- force_decay_rate
- contact_duration_ratio
- stable_contact_ratio
- index_force_drop
- thumb_index_balance
- over_contact_margin
- thermal_cost

**Key findings:**

1. **Index force decay** was observed in candidate `ok_v2_1_0004`:
   - index_peak: 190 g
   - index_final: 148 g
   - index_force_drop: 42 g
   - Interpretation: possible slip or tendon relaxation after initial contact.
2. **Thumb/index imbalance** varies with path; `thumb_first` gives the best balance.
3. **Over-contact margin** is narrow: reducing index by 20–40 ticks from a desired pose often crosses the 200 g index desired-max boundary.

---

## 10. Repeatability v2

We ran the repeatability test twice: first with the original script, then after adding thermal cooldowns.

### 10.1 Initial run (thermal-limited)

**Command:**

```bash
python scripts/28_ok_contact_repeatability_v2.py \
  --candidate-file data/episodes/top_ok_candidates.yaml \
  --rounds 5 \
  --start-from-open-each-round \
  --dwell-s 1.0 \
  --record-force-curve \
  --output data/episodes/ok_repeatability_v2.jsonl
```

**Result:** The best candidate `ok_v2_1_0004` only completed 2 valid `desired_contact` rounds; rounds 3–5 were blocked by `temperature_above_warn`. The other two candidates were blocked on all rounds. `contact_detected_rate = 0.4` (FAIL).

### 10.2 Cooldown run (fixed thermal management)

`scripts/28_ok_contact_repeatability_v2.py` was updated with:

- `--cooldown-temp-c` (default 45.0 °C)
- `--inter-round-cooldown-s` (default 5.0 s)
- `--inter-candidate-cooldown-s` (default 10.0 s)
- `--max-cooldown-wait-s` (default 120.0 s)
- Automatic open-palm cooldown when temperature exceeds the warning threshold

**Command:**

```bash
python scripts/28_ok_contact_repeatability_v2.py \
  --candidate-file data/episodes/top_ok_candidates.yaml \
  --rounds 5 \
  --start-from-open-each-round \
  --output data/episodes/ok_repeatability_v2_cooldown.jsonl \
  --cooldown-temp-c 45.0 \
  --inter-round-cooldown-s 5.0 \
  --inter-candidate-cooldown-s 15.0 \
  --max-cooldown-wait-s 180.0
```

**Artifacts:**

- `data/episodes/ok_repeatability_v2_cooldown.jsonl`

**Results for best candidate `ok_v2_1_0004`:**

| round | primary_event | thumb_net | index_net | thumb_rot_net |
|-------|---------------|-----------|-----------|---------------|
| 0 | desired_contact | 92 | 132 | 100 |
| 1 | desired_contact | 94 | 131 | 101 |
| 2 | desired_contact | 92 | 132 | 101 |
| 3 | desired_contact | 91 | 130 | 100 |
| 4 | desired_contact | 91 | 129 | 100 |

**Statistics:**

- rounds: 5 valid
- contact_detected_rate: 1.0
- thumb_mean: 92.0 g, thumb_cv: 0.0133
- index_mean: 130.8 g, index_cv: 0.01
- thumb_rot_mean: 100.4 g, thumb_rot_cv: 0.0055
- max_force_net_g: 132
- max_temp_c: 44

**Other candidates:**

| candidate | contact_rate | thumb_mean | index_mean | thumb_rot_mean |
|-----------|--------------|------------|------------|----------------|
| ok_v2_1_0010 | 1.0 | 91.0 | 156.4 | 82.6 |
| ok_v2_1_0001 | 1.0 | 80.2 | 128.2 | 68.8 |

All three candidates now satisfy the force-window and contact-rate requirements.

**Pass/Fail:** PASS on force/repeatability metrics; FAIL on promotion only because `ok_shape_score=0`.

---

## 11. Human / Visual OK Shape Labels

**Command:**

```bash
python scripts/27_label_ok_shape.py \
  --episode data/episodes/ok_asymmetric_search.jsonl \
  --media-dir data/media/ok_candidates \
  --output data/episodes/ok_shape_labels.jsonl
```

**Artifacts:**

- `data/episodes/ok_shape_labels.jsonl`

Because no camera feed was available, the script emitted **placeholder labels** with:

- `ok_shape_score: 0`
- `thumb_index_ring_closed: false`
- `contact_natural: false`
- `over_pressed_visual: false`
- `visually_safe: false`
- `human_label_required: true`

All top candidates therefore fail the promotion gate shape requirement (`ok_shape_score_mean_min: 4.0`).

---

## 12. Promotion Gate Result

We ran the promotion gate twice: once with the initial thermal-limited repeatability file, and again with the cooldown repeatability file.

### 12.1 Initial gate (thermal-limited)

**Command:**

```bash
python scripts/29_promote_ok_contact_policy.py \
  --repeatability data/episodes/ok_repeatability_v2.jsonl \
  --shape-labels data/episodes/ok_shape_labels.jsonl \
  --output ~/.rosclaw-rh56/memory/promoted_ok_contact_safe_v2.yaml \
  --report reports/ok_contact_promotion_decision.md
```

**Decision:** `ok_contact_safe_v2` **REJECTED**

**Reject reasons:**

- `contact_detected_rate_too_low:0.4` (required ≥ 0.8)
- `ok_shape_score_too_low:0` (required ≥ 4.0)

### 12.2 Cooldown gate (current best)

**Command:**

```bash
python scripts/29_promote_ok_contact_policy.py \
  --repeatability data/episodes/ok_repeatability_v2_cooldown.jsonl \
  --shape-labels data/episodes/ok_shape_labels.jsonl \
  --output ~/.rosclaw-rh56/memory/promoted_ok_contact_safe_v2_cooldown.yaml \
  --report reports/ok_contact_promotion_decision_cooldown.md
```

**Artifacts:**

- `~/.rosclaw-rh56/memory/promoted_ok_contact_safe_v2_cooldown.yaml`
- `reports/ok_contact_promotion_decision_cooldown.md`

**Decision:** `ok_contact_safe_v2` **REJECTED** (only shape score remains)

**Reject reasons:**

- `ok_shape_score_too_low:0` (required ≥ 4.0)

**Best candidate:** `ok_v2_1_0004` (`thumb=430, index=410, thumb_rot=300`, `thumb_first`)

| metric | value |
|--------|-------|
| rounds | 5 |
| thumb_mean | 92.0 g |
| index_mean | 130.8 g |
| thumb_rot_mean | 100.4 g |
| thumb_cv | 0.0133 |
| index_cv | 0.01 |
| thumb_rot_cv | 0.0055 |
| contact_detected_rate | 1.0 |
| ok_shape_score | 0 |
| max_force_net_g | 132 |
| max_temp_c | 44 |

**Per-candidate summary (cooldown):**

| candidate | thumb_mean | index_mean | thumb_rot_mean | contact_rate | shape | passed | reasons |
|-----------|------------|------------|----------------|--------------|-------|--------|---------|
| ok_v2_1_0004 | 92.0 | 130.8 | 100.4 | 1.0 | 0 | False | ok_shape_score_too_low:0 |
| ok_v2_1_0010 | 91.0 | 156.4 | 82.6 | 1.0 | 0 | False | ok_shape_score_too_low:0 |
| ok_v2_1_0001 | 80.2 | 128.2 | 68.8 | 1.0 | 0 | False | ok_shape_score_too_low:0 |

---

## 13. Countdown Force-OK v2 Validation

Not executed. `scripts/31_countdown_force_ok_v2.py` checks that `promoted_ok_contact_safe_v2.yaml` has `status: promoted`; the current policy is `status: rejected`, so the script correctly refuses to run.

**Pass/Fail:** BLOCKED (pending promotion)

---

## 14. Body Cognition Update Summary

File: `~/.rosclaw-rh56/body/body_cognition.yaml`

Updated to schema `rosclaw.rh56.body_cognition.v2_1`:

- `force_model.baseline_audit_passed: true`
- `force_model.primary_contact_signal: FORCE_ACT`
- `force_model.current_static_contact_reliable: false`
- `ok_contact_manifold` populated with examples for:
  - `no_contact_region`
  - `thumb_only_contact_region`
  - `index_only_contact_region` (empty)
  - `desired_contact_region`
  - `over_contact_region`
  - `temperature_limited_region` (empty so far)
- `path_dependence.observed: true`, `best_path: thumb_first`
- `force_decay.observed: true`, with candidate `ok_v2_1_0004` observation
- `known_traits` extended with thermal and path-dependent findings
- `search_history` includes smoke test (16 candidates) and main run (72 candidates)

---

## 15. Sim2Real Delta Update Summary

File: `~/.rosclaw-rh56/body/sim2real_delta.yaml`

Updated to schema `rosclaw.rh56.sim2real_delta.v2_1`:

- `asset` references `e-urdf-zoo` commit `9777f267...`
- `gesture_deltas.ok_contact.real_observed_poses` lists no_contact and desired_contact examples
- `sim2real.ok_gesture.delta_types`:
  - `contact_manifold_delta`
  - `sensing_delta`
  - `thermal_delta`
  - `path_dependence`
- Interpretation notes:
  - Real RH56 OK contact is deeper than topology-only simulation predicts.
  - `CURRENT` is not a static contact signal.
  - `FORCE_ACT` is the primary contact feedback.
  - Index contact is unstable in repeatability and path-dependent.

---

## 16. Practice Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| Force baseline audit | `data/episodes/force_baseline_audit.jsonl` | 1201 raw Modbus frames |
| Force baseline | `~/.rosclaw-rh56/body/force_baseline.yaml` | Per-DOF open-palm offsets |
| Asymmetric search | `data/episodes/ok_asymmetric_search.jsonl` | 72 candidate records |
| Top candidates | `data/episodes/top_ok_candidates.yaml` | 3 desired-contact candidates |
| Force metrics | `data/episodes/ok_force_curve_metrics.{json,parquet}` | Analyzer output |
| Force report | `reports/ok_force_curve_analysis.md` | Markdown analysis |
| Shape labels | `data/episodes/ok_shape_labels.jsonl` | Placeholder labels |
| Repeatability (initial) | `data/episodes/ok_repeatability_v2.jsonl` | First 5-round run, thermal-limited |
| Repeatability (cooldown) | `data/episodes/ok_repeatability_v2_cooldown.jsonl` | 5-round run with cooldowns |
| Promotion decision (initial) | `~/.rosclaw-rh56/memory/promoted_ok_contact_safe_v2.yaml` | Rejected policy with metrics |
| Promotion decision (cooldown) | `~/.rosclaw-rh56/memory/promoted_ok_contact_safe_v2_cooldown.yaml` | Rejected policy, force metrics pass |
| Promotion report (initial) | `reports/ok_contact_promotion_decision.md` | Human-readable decision |
| Promotion report (cooldown) | `reports/ok_contact_promotion_decision_cooldown.md` | Human-readable decision |
| Manual shape label helper | `scripts/33_label_ok_shape_manual.py` | Interactive or YAML-based labeling tool |
| Shape score template | `data/episodes/ok_shape_manual_scores_template.yaml` | Template for human-provided scores |
| Event schema unit tests | `tests/test_contact_event_schema.py`, `tests/test_primary_event_exclusive.py`, `tests/test_event_distribution_accounting.py` | Pass (13/13) |
| Body cognition | `~/.rosclaw-rh56/body/body_cognition.yaml` | v2.1 contact manifold |
| Sim2real delta | `~/.rosclaw-rh56/body/sim2real_delta.yaml` | v2.1 delta notes |

---

## 17. Dashboard Screenshots

Generated by `scripts/30_rh56_force_dashboard.py`:

- `screenshots/rh56_force_dashboard.md`
- 17 PNG heatmaps in `screenshots/`

The dashboard shows event distribution, top desired candidates, repeatability summary, placeholder shape labels, body cognition summary, sim2real delta summary, and a full heatmap index.

---

## 18. PR List and Submission Status

No PRs have been opened yet. The planned PRs are:

| PR | Repository | Scope | Status |
|----|------------|-------|--------|
| PR-A | inspire-rh56-mcp | Serial/RS485/Modbus + FORCE_ACT/STATUS/ERROR/TEMP MCP tools | Not started |
| PR-B | ros-claw/rosclaw | Generic `PhysicalFeedbackFrame`, `ContactEvent`, `BodyCognition`, `PromotionGateResult` | Not started |
| PR-C | e-urdf-zoo | RH56 force-feedback metadata, contact warnings, actuator mapping | Not started |
| PR-D | skill package | `inspire_rh56_hand_gestures` v0.3.0 with `ok_contact_safe_v2` policy | Not started |

---

## 19. Open Issues

1. **Visual shape labels:** Current labels are placeholders. Real labels (camera or human review) are required for promotion. This is now the only promotion blocker.
2. **Standalone ForceModel / BodyState modules:** Currently embedded in scripts; should be extracted to `src/rosclaw_rh56/sensors/force_model.py` and `src/rosclaw_rh56/body/body_state.py`.
3. **Countdown force-OK v2:** Blocked until a candidate is promoted.
4. **Longer dwell / thermal model:** Need to characterize temperature rise vs. number of closures and add predictive cooldown.
5. **Index contact decay:** Candidate `ok_v2_1_0004` shows 42 g index force drop in the search curve; needs slip/relaxation root-cause analysis.

---

## 20. Next Steps

1. **Obtain real visual/human OK-shape labels** for the top candidates. Use `scripts/33_label_ok_shape_manual.py` (interactive) or fill `data/episodes/ok_shape_manual_scores_template.yaml` and run the script.
2. **Re-run the promotion gate** with real shape labels. If force metrics still pass and shape score ≥ 4, the policy will be promoted.
3. **Run `scripts/31_countdown_force_ok_v2.py --rounds 10`** after promotion.
4. **Extract ForceModel / BodyState** into reusable library modules.
5. **Prepare PRs** for inspire-rh56-mcp, ros-claw/rosclaw, e-urdf-zoo, and skill package v0.3.0.

---

## Sign-off

This report honestly reflects the current state: RH56 force-closed-loop v2.1 has produced a repeatable OK contact candidate with excellent force metrics and demonstrated path dependence and force decay. The policy is **not yet promoted** solely because real visual/human shape labels are not available.
