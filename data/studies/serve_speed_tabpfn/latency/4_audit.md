# Latency follow-up: red-team check of B-M1 (agent 4, auditor)

8 October 2026, about 03:30–03:40 UTC (20:30–20:40 local on 7 Oct), after the outcome run. Inputs:
* `plan.md`;
* the three notes;
* `availability.parquet`;
* `variants.parquet` (SHA-256 `b88b74eb…`);
* `variants_meta.json`;
* the frozen results.

**Labels.** All numbers are **observed** unless marked *inferred*.

**Scripts:** `src/eda/serve_speed_tabpfn/design/auditor_lat_rebuild.py` and `auditor_lat_probe.py`. Their outputs `auditor_lat_*` are in this folder.

**Rules followed.**
* `features_latency.py` and `panel.py` were not imported.
* No outcome, result, target or price was read. The only reads were feature values, the frozen output files and file times.
* No GPU was used and no builder's file was edited.

## Verdict: **B-M1 is built as specified, and it is leak-proof under scenario B. Sign off on the values.**

| Check | Result |
|---|---|
| 1. Independent rebuild | **Exact**, as for B-M0 |
| 2. Probe B on B-M1 | **Passes**, with a leaky control that works |
| 3. B's release rule | **Exactly as documented** |
| 4. The 28-day half-life | **Result-free, and documented before the outcome run** |

**Two cautions for the lead's message to the owner** (§5):
* **B-M1 was not a pre-specified headline.** The plan fixed B-M0 and B-M2, so B-M1's +0.38 is descriptive.
* **The upstream data changed after the freeze.** It does not affect these numbers.

## 1. Independent rebuild of `spd_B_M1` and `spd_B_M0`

**How it was built** (my code; `features_latency.py` not imported):
* **Panel:** the study's frozen panel, `speed_panel.parquet` (SHA-256 `f774eb50…`, the hash recorded in `variants_meta.json`), read as data.
* **Release days:** `release_B` from `availability.parquet`.
* **History:** own earlier rows (earlier date, or the same event at an earlier round), with obs ≥ es − 364 **and** `release_B` ≤ es.
* **Edition offsets:** refitted at each target's es on rows with `release_B` ≤ es. My snapshot code uses the panel.py reference and fallback conventions.
* **Filter:** the frozen men's constants, half-life 14 d (M0) or 28 d (M1), projected to es.
* **Column:** clip(Δf̂ / SD, ±4); women 0.

**Agreement with `variants.parquet`** (difference in units of the variant's SD):

| Column | Frame matches | corr | Within 0.05 | Largest difference | SD: meta / mine |
|---|---|---:|---:|---:|---|
| `spd_B_M1` | all 63,737 | 1.000000 | 100% | 2.5e-14 | 1.949605 / 1.949605 |
| `spd_B_M1` | men 31,683 | 1.000000 | 100% | 2.5e-14 | |
| `spd_B_M0` | all / men | 1.000000 | 100% | 1.8e-14 | 1.507476 / 1.507476 |
| `spd_A_M0` (control: should equal `spd_f`) | all / men | 1.000000 | 100% | 2.2e-14 | 2.223995 / 2.223995 |

**A side finding that does not affect these numbers.** The acquisition's `speeds.parquet` was rewritten at **16:21 on 7 Oct**, after the freeze (15:54).
* It fixes the QF-labelled-as-qualifying bug: 0 of 1,426 QF rows are labelled qualifying now.
* It relinks those records.
* My first rebuild re-derived the panel and mixed the R1 records with the new round labels. That admitted 4 stale rows from two mislinked QF records, and moved A by up to 0.37 SD and B by up to 0.10 SD on a few matches.
* On the frozen panel the agreement is exact, as above.
* *Inferred:* a fresh `panel.py` run today would differ slightly from the frozen panel. Any live or prospective build must rebuild and re-hash the panel.

## 2. Probe B on B-M1 (`auditor_lat_probe.py`)

**Setup:**
* 15 cut days, 13 of them in 2024–26, all inside events. They include:
  * week-two Wednesdays of two-week Masters, where week-one rows are released on the Monday;
  * a release Monday (17 Mar 2025);
  * the Sunday before one (15 Mar 2026).
* Every row with `release_B` > D is perturbed **in the filter and the snapshot inputs alike**, and the snapshots are refitted:
  * noise U(100, 250) km/h on 8 days;
  * +30 km/h on 7 days.

| Check | Result |
|---|---|
| Frame sides with **es ≤ D** that moved (92,296–126,716 checked per day; tolerance 1e-12) | **0 on every day** |
| Edition offsets at D, D − 1 and D − 7, every edition, both tours | **Identical** (difference 0.0) |
| Power: sides with D < es ≤ D + 42 that moved | 501–1,185 of samples of 758–1,408, every day |
| Leaky control: rows admitted at lf + 1 instead of `release_B` (history and snapshots), same perturbation | **Fired on 14 of 15 days** (38–637 sides) |

The day the leaky control did not fire was 17 Mar 2025, a release Monday. No frame side within 28 days had any row that lf + 1 would admit before `release_B`. There was nothing to leak; it is not a detection failure. The control fired on 12 of the 13 days in 2024–26.

**Why this covers the build.** The probe runs on my rebuild, which equals the build's `spd_B_M1` to 2.5e-14 on every frame match. A leak in the build would have shown as a disagreement in §1.

**Gap closed.** The modeller's own Probe B covered B-M0 and B-M2, not B-M1. This covers it.

## 3. B's release rule, and the same-event share

Checked on all 42,900 used panel rows, against `1_engineer.md`.

| Rule | Check | Result |
|---|---|---|
| Non-Slam rows (20,113): first Sunday on or after lf + 2, usable from the Monday | Released on a Monday | 100% |
| | Release − lf by lf's weekday: Mon 7, Tue 6, Wed 5, Thu 4, Fri 3, Sat 9, Sun 8 (Mon–Fri finishes the next Monday; Sat–Sun a week later) | **100%** |
| Slam rows (22,787, 3,058 of them qualifying): the last main-draw day + 3 | `release_B` = last main-draw day + 3 | 100% |
| | The last main-draw day recomputed independently (the latest lf of the Slam-year's main-draw singles, both tours) | 100% |
| | One release day per Slam-year | yes |
| Every row | `release_B` ≥ `release_A` | yes |

**Same-event use** (men's frame sides 2024–26, 14,140): a side's history holds a row from its own current event.
* **Under A: 41.5%.**
* **Under B: 2.2%** (307 sides).
* All 405 such rows come from events that span two calendar weeks:
  * the 12-day Masters (Shanghai, Rome, Madrid, Miami, Indian Wells, and Cincinnati and Canada from 2025);
  * Beijing, Tokyo, Hangzhou, Chengdu and Washington.
* Each is a week-one round, released (`release_B` ≤ es in every case) and used at least 3 days later (median 5).
* *Inferred:* this is the weekly rule working as documented, not a leak. "About 0" holds for rows of the same calendar week, and at the Slams it is exactly 0.

## 4. M1's half-life (28 days)

**The tuning** (`variants_meta.json` → `m1.B`). T1 information gain: positive = Δf̂ adds information about the within-match speed difference, in km/h².

| Half-life (d) | 3 | 7 | 14 | 21 | **28** | 42 | 60 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gain, tune 2019–22 | 1.56 | 2.60 | 3.23 | 3.40 | **3.42** | 3.33 | 3.17 |
| Gain, check 2023 | 0.46 | 0.87 | 0.84 | 0.91 | **1.04** | 1.28 | 1.50 |
| Full-forecast MSE, tune | 69.41 | 68.24 | 67.32 | 66.98 | 66.86 | **66.85** | 66.97 |

* **Result-free.** T1 is a statistic target on ≤ 2022, with 2023 as the check, and no outcome is involved.
* **Interior.** The grid runs 3–60 d.
* **28 d is the argmax on 2019–22,** on a flat top: 21–42 d lie within 0.09.
* **It beats 14 d on the 2023 check** (1.04 against 0.84). The check itself rises to the grid's edge (60 d), so 28 d is not the check's best.

**The criterion changed from the plan.**
* `plan.md` (20:04) said "next-match speed … as in R1".
* The modeller used the column's own T1 information gain instead. Full-forecast MSE would have picked 42 d, which loses on the 2023 check: 164.20 → 165.40 km/h².
* The reason is principled: the full forecast also rewards the level, which is not in the column. The fork was settled on result-free numbers only.

**File times** (local, 7 Oct) show the change documented before the outcome run:

| Time | File | What it records |
|---|---|---|
| 20:04 | `plan.md` | The original criterion |
| 20:20:36 | `features_latency.py` | The criterion in code |
| 20:25:22 | `variants_meta.json` | h = 28, and 42 under full-forecast MSE |
| 20:27:16 | `2_modeller.md` | The criterion and its reason |
| 20:27:56 | `check_latency.json` | The result-free check |
| 20:28:04 | `look_ledger.md` | Row 40, the run |
| 20:28:10 | `results_latency.*` | The outcome run's output |

* The order is right, but the margin is short: the note is 40 s before the `--check`.
* `plan.md` itself was not amended. **The lead should record the criterion as a pre-run deviation from the plan.**

## 5. Cautions for the owner's decision (*inferred*; from the frozen results only)

**B-M1 is descriptive, not a headline.** The plan fixed B-M0 and B-M2 as the headline before any computation. The three B variants (positive = the nudge better than the calibrated base, mLL) are:

| Variant | Gain | Share of A |
|---|---|---:|
| B-M0 | +0.29 [+0.01, +0.56] | 70% |
| **B-M1** | +0.38 [+0.11, +0.64] | 92% |
| B-M2 | +0.27 [+0.00, +0.54] | 66% |

**Picking the best of three correlated variants after seeing outcomes biases its gain upward.**
* The result-free evidence does not single out B-M1:
  * its 2023 T1 information share is 0.21, against 0.17 for B-M0 and 0.24 for B-M2;
  * its gate per-SD ratio is 0.77, against 0.69 and 0.74.
* Squaring 0.77 gives about 0.6 of A's gain. The observed 92% is above that.

**All variants' gains sit mostly in 2026**, as A's do. B-M1 by season (positive = the nudge better): 2024 +0.11 [−0.32, +0.54], 2025 +0.36 [−0.09, +0.82], 2026 +0.79 [+0.16, +1.43].

**Suggestion.** Report scenario B as "about 0.27–0.38 mLL, 66–92% of instant": B-M0 and B-M2 as specified, B-M1 as a descriptive sensitivity. If the owner adopts the 28-day half-life, fix it in the prospective test's pre-registration. It is defensible on result-free grounds: it beats 14 d on the 2023 check.

## Looks

| # | Seasons | What was related to what | Script → output |
|---|---|---|---|
| LA-1 | 2013–2026 | Feature values only: my rebuilt `spd_B_M1`, `spd_B_M0` and `spd_A_M0` against `variants.parquet`; the release rule against `availability.parquet` and Stage 0 / timing clock days; same-event shares (counts) | `auditor_lat_rebuild.py` → `auditor_lat_rebuild.json`, `auditor_lat_variants.parquet` |
| LA-2 | 2023–2026 | Probe B on B-M1: perturbed speeds against unperturbed feature values | `auditor_lat_probe.py` → `auditor_lat_probe.json` |
| LA-3 | – | Frozen outputs re-read (`variants_meta.json`, `results_latency.json`) and file times; no re-run | – |

No speed value or feature was related to a match result, a statistic target or a price in this check.
