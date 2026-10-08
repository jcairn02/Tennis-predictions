# Adaptive speed memory: the applier and the exploratory scorer (integration strategist)

8 October 2026 · agent 3. Built to [plan.md](plan.md).
* **Exploratory.** 2024–26 results were already opened.
* **`--run` was not run.**

## The applier: `src/eda/serve_speed_tabpfn/adaptive/adjust.py`

This is the code that defines "the current best model's" speed adjustment from now on:

**logit q = s_tour,mode,Y · η + b̃_mode,Y · column_mode**

* **η:** the base's log-odds, the 16-seed mean of the symmetrised TabPFN forecast for season Y, trained on 2013..Y−1.
* **mode:** T or L, per match.
* **column_mode:** `spd_T_<S>` (14-day form ÷ 2.223995 km/h) or `spd_L_<S>` (28-day form ÷ 1.949605 km/h).
* **Women:** their column is forced to 0, so they get the mode's tour slope.
* **Coefficients:** `score.nudge_parameters`, unchanged, walk-forward on 2019..Y−1 from the base's seeds 0–3, b shrunk at τ = 0.05.
  * **T** is fitted on the instant history, `spd_f`.
  * **L** is fitted on today's-sources history, `spd_B_M1`.

**`--coefficients`** wrote `adaptive/coefficients.json`. Observed:
* the 2024–26 rows equal the published fits (S9 for T, B-M1 for L) to **0.0**; the writer refuses otherwise;
* 2026: T s_atp 0.9007, b̃ 0.0389; L s_atp 0.8996, b̃ 0.0376; s_wta 0.9168 in both;
* the exact standardisers are recorded; rounded ones would break the equalities;
* **2027** is fitted once the frame's 2026 reaches November. Today it is "not yet fittable", since the frame ends at 28 July.

**`--date D --scenario S`** scores every frame match whose best-estimate day is D.
* It reads only data in hand: the base forecast, the columns and mode, and `coefficients.json`. No result.
* It writes `adaptive/scored/<D>_<S>.csv` (base forecast, η, mode, both columns, q).
* Live, a fixture list and the watermark-based mode (plan rule 1) replace the frame keys; neither is built here.

## The exploratory scorer: `adaptive/score_adaptive.py`

**Validation of `columns.parquet`**, against the whole frame:
* one row per match;
* columns finite, 0 for women;
* mode T/L, and L exactly when `late_a` or `late_b`.

**Per scenario A, B, D, E, men 2024–26 (7,068):** each arm against the calibrated base, mLL (positive = better), block-only interval, pooled and by season. The arms run through `adjust.apply`:

| Arm | Definition |
|---|---|
| `pure_T` | every match in mode T (`spd_T_S`, T's coefficients) |
| `pure_L` | every match in mode L (`spd_L_S`, L's coefficients) |
| `switch` | `mode_S` per match: the rule |
| `joint` | **descriptive:** s, b_T and b_L fitted together, walk-forward on the scenario's own history and mode flags |

Also reported: the switch against the better pure arm, paired (positive = the switch better), and the mode shares.

**`--run` (the lead's, once).** It refuses to start unless:
* the code, frame and feature file equal the study's;
* **the columns build has passed** (probes, no results read, recorded hash). I added this gate;
* the base fits are present and the reuse checks have passed.

It then reads `labels()`, and writes nothing unless, to 1e-9:
* **under A,** the switch equals pure T equals S9 (+0.410 [+0.045, +0.775]);
* **under B,** pure L equals B-M1 (+0.3754 [+0.1097, +0.6410]).

## Tests: `test_ssp_adaptive.py` (9 pass; 96 in the study folder)

On a stand-in world:
* **the applier:** formula, sign, mode, women, season row;
* **the fit** equals `nudge_parameters` per mode;
* **the coefficients and the joint fit** are bit-identical when seasons ≥ Y are scrambled;
* **the writer** refuses a published value off by 1e-6;
* **validation** refuses five defects;
* **`--check` and `--date`** read no result;
* **`--run`:** refuses an irreproducible "study" and an unpassed build, and runs once;
* **synthetic:** the switch beats both pure arms when the truth follows the modes, and a null is rarely rejected.

## On the real columns (observed, result-free)

**`--check`** (`check_adaptive.json`):
* the build passed;
* `spd_T_A` − `spd_f` = 0.0, `spd_L_B` − `spd_B_M1` = 0.0, and mode A is all T, so both reproductions are set up;
* the inputs equal the study's, the coefficients agree, and the fits and checks are complete.

**The mode L share, men 2024–26:**

| Scenario | 2024–26 | By season (2024 / 2025 / 2026) | 2019–23 |
|---|---|---|---|
| A | 0% | | |
| **B** | **46.6%** | 50.3% / 42.6% / 46.8% | 24.1% |
| **D** | **13.0%** | | |
| **E** | **34.3%** | | |

(An earlier draft quoted the modeller's interim log.)

**`--date 2026-07-06 --scenario B`** (Wimbledon R16): 7 matches.
* The 3 men are in mode L: mid-Slam speeds are not yet in hand.
* The 4 women are in mode T, with q equal to the tour slope alone (1e-16).

**Next (the lead):** optionally `--synthetic --scenario B`; then `--run` once, logged. The better pure arm is chosen on the same data, so that comparison is descriptive.

## Looks

* **`adjust.py --coefficients`** read outcomes 2019–2025, all opened earlier, through `score.labels`. They were used only to refit the published coefficients, which it reproduced exactly.
* **The mode shares** come from `--check`, values only.
* **Stand-in worlds:** synthetic only.

## Addendum, 8 October 2026: always L (the owner's amendment)

**Policy.** `adjust.py` now defaults to **always mode L**: the 28-day `spd_L` (÷ 1.9496052 km/h). The live feed picks the coefficient set (`--feed`, default `weekly`).
* `apply()` and `--date` use always-L by default.
* The T/L switch is kept behind `--policy switch`, documented as superseded.
* `score_adaptive.py` is unchanged and still runs: `apply`'s positional order is kept, and `L` stays an alias of `L_weekly`.

**`coefficients.json` now holds three sets** (2024–26), each with the history it was fitted on:

| Set | History |
|---|---|
| `L_weekly` | `spd_B_M1` = `spd_L_B`. It equals the latency run's B-M1 to **0.0** |
| `L_daily` | `spd_L_D`, scenario D |
| `T` | `spd_f`, equal to S9 |

**`L_daily`, 2026:** s_atp 0.8999, s_wta 0.9168, b̂ 0.0405 (SE 0.0185), **b̃ 0.0356** per unit (`L_weekly`: b̃ 0.0376).

**Tests** (13 adaptive; 100 in the study folder):
* always-L by default;
* the feed picks the set;
* women unchanged;
* `L_weekly` equals B-M1 exactly, in the stand-in and in the real table;
* `L_daily` reads seasons < Y only.

**Look:** the fit read 2019–2025 outcomes, all opened earlier, through `score.labels`, only for the walk-forward coefficients. No scoring run on 2024–26.
