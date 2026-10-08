# Adaptive memory: red-team check before the outcome run (agent 4, auditor)

8 October 2026, before `score_adaptive.py --run`. Inputs:
* `plan.md` (07:41);
* `columns.py` → `columns.parquet` / `columns_meta.json`;
* `adjust.py` → `coefficients.json`;
* `score_adaptive.py`;
* `latency/availability.parquet`.

**Labels.** All numbers are **observed** unless marked *inferred*.

**Script:** `src/eda/serve_speed_tabpfn/design/auditor_ad_check.py`, output `auditor_ad_check.json` / `.log` here.

**Rules followed.**
* No outcome, result or price was read.
* The date command ran under a spy that refuses any `a_won` read, and its CSV went to my scratchpad.
* No builder's file was edited, and no GPU was used.

## Verdict: **built as the plan says; the run may proceed.**

The checks show no outcome-dependent mode and no coefficient set fitted on seasons ≥ Y. Three reading caveats should be stated before the run (§4).

## 1. The late flags and the modes

**Method.** My own code re-derives the flags on **every** men's 2024–26 frame match (7,070, well above the 2,000 asked):
* the frozen panel's usable rows;
* `availability.parquet`'s release days;
* my R4 frame join (the frame's own player ids).

A side is late when an own earlier usable row (an earlier tournament date, or the same tournament at an earlier round) has lf + 1 < es, obs ≥ es − 14 and release > es. The mode is T when neither side is late.

| Scenario | late_a equal | late_b equal | mode equal | Mode L share, mine / build |
|---|---:|---:|---:|---|
| A | 100% | 100% | 100% | 0 / 0 (never late by construction: release = lf + 1) |
| **B** | 100% | 100% | **100%** | 46.6% / 46.6% |
| **D** | 100% | 100% | **100%** | 13.0% / 13.0% |
| E | 100% | 100% | 100% | 34.2% / 34.2% |

**The release definitions** (all 42,900 usable rows):

| Column | Tour level | Slams |
|---|---|---|
| A | lf + 1 | lf + 1 |
| B | Monday release (rule unchanged) | after the event |
| D | lf + 2 | = B |
| E | = B | lf + 2 |

D and E are never earlier than A.

**The mode depends on no outcome.** It is a function of the clock days, the release days and the side's own rows finished before es. *Inferred:* under B and D almost every Slam match from round 2 on is L, because the same Slam's earlier rounds are pending. Under D, tour rows are never late, since yesterday's match falls in the grace and any older row is in hand.

## 2. The applier (`adjust.py`)

* **Standardisers.** The columns use the exact floats 2.223995373606193 and 1.9496051535048338, equal to `speed_meta.json` s_f and `variants_meta.json` B_M1.
* **Coefficients from seasons < Y only.**
  * `coefficients.json` T and L for 2024–26 equal the study's S9 parameters and the latency run's B-M1 parameters with a **maximum difference of 0.0**, and the row counts match.
  * Both come from `score.nudge_parameters`, which fits on 2019..Y−1 (seeds 0–3) and raises if it reads a season ≥ Y.
  * T is fitted on `spd_f` (instant) and L on `spd_B_M1` (today's sources), as the plan says.
  * 2027 is "not yet fittable".
* **Black-box test** (4,000 synthetic rows, all tours, modes and seasons):
  * q equals expit(s·η + b̃·z) with each (mode, season) row's own s and b̃: maximum difference 0.0.
  * T rows ignore `col_L` and L rows ignore `col_T`, so the mode only selects; nothing is blended.
  * **Women ignore both columns** and get s_wta·η. s_wta is identical in T and L for every season.
* **The date command reads no result.** Under the spy, `score_date("2026-07-06", "B")` read:
  * `frame_keys.parquet` (match_id, tour, season, obs);
  * `columns.parquet` (spd_T_B, spd_L_B, mode_B);
  * `model_frame.parquet` (match_id, season);
  * the base fit files (forecasts).

  It never read `a_won`. It returned 7 matches: 3 men in L, 4 women in T, as the strategist's note says.

## 3. The scorer's arms and the required reproductions

* **The arms,** by code reading: `pure_T` sets mode T everywhere, `pure_L` sets mode L everywhere, and `switch` uses `mode_S`. All three go through `adjust.apply` with the same 16-seed η and the calibrated base as the comparator.
* **The joint variant** is descriptive. It refits s, b_T and b_L on each scenario's own history and raises on a season ≥ Y.
* **Both reproductions are wired as refusals before anything is written,** each to 1e-9:
  * under A, the switch equals pure T equals S9, +0.410 [+0.045, +0.775];
  * under B, pure L equals B-M1, +0.3754 [+0.1097, +0.6410].
* **Their preconditions hold** (`check_adaptive.json`, re-verified):
  * `spd_T_A` − `spd_f` = 0.0;
  * `spd_L_B` − `spd_B_M1` = 0.0;
  * mode A is all T;
  * the coefficients equal the published ones.
* **`--run` also refuses** on any of:
  * changed code, frame or features;
  * an unpassed columns build;
  * missing base fits;
  * failed reuse checks;
  * a second run.

## 4. What could make the readings misleading (state these before the run)

1. **Pure T under B is not B-M0.** It is B's 14-day column with the **instant** coefficients. B-M0 (+0.29) refitted its own, which are smaller in 2025 (b̃ 0.0275 against 0.0334). The two numbers should not be equated. The same holds for pure L under D and E, which uses B-M1's coefficients.
2. **The T arm uses instant coefficients on a column that is not instant.**
   * Under B, mode-T matches (3,778 men) have `spd_T_B` correlating 0.815 with `spd_f`; 16.8% differ by more than 0.5 unit.
   * 23.7% of them miss a grace-day row: yesterday's match, not in hand under weekly publication.
   * The grace was justified by L1 = 100% of instant, but L1 earned that with its **own** refitted b̃ (0.0239 / 0.0232 / 0.0354, below the instant 0.0305 / 0.0334 / 0.0389).
   * *Inferred:* the switch's T arm may be slightly over-weighted under B and E.
3. **Under D and E the L arm is B-calibrated.**
   * `spd_L_D` and `spd_L_E` are more informative than B-M1: SD 1.20 / 1.15 against 1.09; `spd_L_D` correlates 0.90 with B-M1.
   * They are applied with B-M1's b̃. *Inferred:* the L arm is under-weighted there.
   * The descriptive joint fit is the right check on caveats 2 and 3.
4. **"The switch against the better pure arm"** picks the better arm on the same outcomes. It is descriptive and biased against the switch, so a tie there is not evidence against it.
   * The plan's expectation, "at least as good as the better pure arm in every scenario", rests on the coefficient choices of caveats 2 and 3.
   * If it fails, the suspects are those choices, not the 14/28 rule.

## Looks

| # | Seasons | What was related to what | Script → output |
|---|---|---|---|
| AD-1 | 2024–2026 | Values and counts only: late flags and modes re-derived and compared; release-day definitions; column correlations and SDs; grace-row shares | `auditor_ad_check.py` → `auditor_ad_check.json` |
| AD-2 | – | `adjust.apply` on synthetic inputs; `score_date` under a read spy (no result read; CSV to the scratchpad); frozen coefficient and parameter files re-read | same |

No speed value, column or mode was related to a match result, a statistic target or a price.
