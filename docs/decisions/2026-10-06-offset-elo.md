# Swap the old Elo blend for the offset Elo in the model

**Stated by the owner on 6 October 2026,** after the [surface-rating race](../studies/surface_rating_race/README.md): "Swap the old Elo blend for the offset Elo in the model." Recorded on 6 October 2026.

The owner's reason was given earlier the same day: "our plan is not to bet at the close but before the close, so if its not fully priced in the mid market, but it is by close, that means its useful."

## Decision

**The best model's `elo_logit` and `surface_first` are replaced by six inputs:**

| Input | What it is |
|---|---|
| `elo_overall` | overall Elo's log-odds that A wins (Stage 1's overall rating, retirements counted) |
| `elo_surf_offset` | the two players' surface offsets, in log-odds. Each offset starts at 0, moves only on its surface by the surprise of overall rating + offset, and has its own K (tuned on 2013–2018: men 80/(n + 10)^0.6, women 80/(n + 20)^0.6) |
| `surf_season_a`, `surf_season_b` | log(1 + each player's matches on the match's surface earlier this calendar season) |
| `surf_layoff_a`, `surf_layoff_b` | log(1 + days since each player's last match on the surface), capped at 3 years |

* **The removed inputs.** `elo_logit` is the 70/30 (men) or 75/25 (women) blend of overall and surface-only Elo. `surface_first` is A's first matches on the surface this season minus B's.
* **What "the offset Elo" means here.** It is the representation the race tested and the analyst recommended: the race's arm `elo_off`, the Elo-pieces study's primary. It includes the two surface-switch pairs that replace `surface_first`. The swap without them (`elo_only`) was tested only at the close, a tie.
* **The model after both of 6 October's decisions** has 58 inputs:
  * the closing odds;
  * 31 inputs unchanged from the leak-proof best model;
  * the 21 IOS profile inputs built per surface ([decision](2026-10-06-surface-ios-profile.md));
  * these six.

  Its inputs for every match are in `data/studies/surface_rating_race/model/model_frame.parquet`, listed in `model_inputs.json` and built by `src/eda/surface_rating_race/model_frame.py`. The build is checked value for value against each source.

## The evidence

All gains are milli-log-loss per match. **Positive = the offset Elo is better.** The forecasts are the local TabPFN-3.5, three seeds, recalibrated per tour on 2019–2021. Intervals are over four-week blocks; a range spanning 0 is a tie. The source is `data/studies/surface_rating_race/results.csv`.

| Against the old blend (`base` → `elo_off`) | Men | Women | Both tours |
|---|---|---|---|
| Fed the Polymarket price 24 hours before the start (2025–2026, 2,648 matches) | +0.69 [−0.61, +1.99] tie | +0.90 [−0.15, +1.95] tie | **+0.78 [+0.03, +1.54] better** |
| Without any price (2022–2026) | **+2.24 [+0.99, +3.50] better** | −0.33 [−1.33, +0.67] tie | **+1.01 [+0.18, +1.84] better**, 5 of 5 seasons |
| With the closing odds (2022–2026) | +0.13 [−0.14, +0.41] tie | −0.25 [−0.55, +0.05] tie | −0.05 [−0.24, +0.14] tie |

* **Priced by the close, not at 24 hours.** Between 24 hours and 30 minutes before the start, the Polymarket price moves toward the offset Elo's view beyond the old Elo's. The slope is +0.22 [+0.02, +0.43] on every match with a price and +0.16 [+0.03, +0.29] on event openers. That is the owner's pattern.
* **Against the TTT offset.** The race's surface-offset TrueSkill Through Time tied the offset Elo inside the model everywhere: −0.25, −0.02 and −0.01 at the 24-hour price, without a price and at the close. The pre-registered rule then picks the cheaper rating. The offset Elo takes about a second per pass, against 22 minutes for the men's TTT offset.
* **In the model as it stands.** The swap was checked on top of the surface IOS profile kept earlier the same day, run after this decision and not pre-registered (`src/eda/surface_rating_race/composed.py`; `composed_results.csv`). The gains hold:

  | The model before → after the swap | Men | Women | Both tours |
  |---|---|---|---|
  | 24-hour price | +0.44 [−0.71, +1.58] tie | **+1.11 [+0.04, +2.18] better** | **+0.74 [+0.04, +1.45] better** |
  | Without any price | **+1.59 [+0.42, +2.75] better** | +0.01 [−0.91, +0.93] tie | **+0.83 [+0.07, +1.59] better**, 5 of 5 seasons |
  | With the closing odds | +0.05 [−0.20, +0.31] tie | −0.21 [−0.48, +0.07] tie | −0.07 [−0.24, +0.10] tie |

  The price also moves toward the new model's view between 24 hours and 30 minutes: +0.23 [+0.04, +0.43] beyond the old model's. The whole day's change, from the original best model to the model after both decisions, is +0.72 [+0.06, +1.39] at the 24-hour price, +1.08 [+0.25, +1.90] without a price, and −0.06 [−0.26, +0.13], a tie, at the close.
* **Leak checks.** Elo and the switch inputs follow each player's own matches in order, safe by construction under the [match clock](2026-10-05-match-timing.md). The day gaps use the timeline's best-estimate days. The Elo-pieces study's date-and-round, flip and truncation probes all passed.

## What it does not show

* **No edge on the closing price.** With the close in the model the swap ties.
* **No money yet.** The [line-sharpening study](../studies/line_sharpening/README.md) bet the current best model at Polymarket's early market instead of the close and found the same result: $0.00 per 100 matches realized (−0.86 to +0.91).
* **The 24-hour test is small.** It covers two seasons of one venue. Its gain is only just clear of zero.
* **The women's case is thin.**
  * On the original inputs every women's result ties: +0.90 at 24 hours, −0.33 without a price, −0.25 at the close.
  * On top of the surface profile, the 24-hour gain is clear: +1.11 [+0.04, +2.18]. The rest still tie.

## Before it is used

* **Recalibrate.** Fit one slope per tour on the model's log-odds, from the model's own earlier out-of-sample seasons. The race's slopes for `elo_off` were 0.889 (men) and 0.968 (women), fitted on 2019–2021.
* **Keep it fresh.** The offset Elo is not part of `src/eda/match_timing/refresh.py`.
  * **The model is now behind Stage 0.** Another session rebuilt Stage 0 and the match timeline at 00:35 UTC on 7 October. That rebuild brought the 2 October audit's repairs, the Slam box scores and new results, and changed 42 June-2026 WTA match ids. The model's inputs, `model_frame.parquet` included, are still built on the 30 September snapshot. `data/studies/surface_rating_race/inputs_manifest.json` records the hashes.
  * **Rebuild steps.** After a rebuild of Stage 0 or the match timeline:
    1. rebuild Stage 1 (`src/eda/predictability_diagnostic/stage1_baselines.py`), since `pieces.py` stops unless it reproduces Stage 1 exactly;
    2. run `./python.sh src/eda/surface_elo_pieces/pieces.py`, which re-tunes the offset's K on 2013–2018 only;
    3. run `src/eda/surface_elo_pieces/build_frames.py`;
    4. bring the surface IOS up to date (its decision lists the steps);
    5. run `./python.sh src/eda/surface_rating_race/model_frame.py`.

    `build_frames.py` and `model_frame.py` check the unchanged inputs against the leak-proof refit's upload. Those checks will fail once the shared tables change, until the base inputs are rebuilt to match.

## Not decided

* **Men only, or both tours?** The owner's statement covers the model as a whole. The evidence is clear for men without a price. For women it is clear only at the 24-hour price on top of the surface profile; everything else ties. The model pools both tours, so the swap could be made per tour.
* **The surface IOS profile, now that the offset Elo is in.** With the offset Elo present, the profile adds nothing detectable:
  * without a price, +0.07 [−0.07, +0.21] (men +0.19 [−0.05, +0.42]);
  * at the 24-hour price, −0.06 [−0.43, +0.31];
  * at the close, −0.01 [−0.10, +0.08].

  Its no-odds gain over the original inputs (+0.25; men +0.84 [+0.40, +1.28]) is largely what the offset Elo now carries. At the 24-hour price it ties even on its own: −0.02 [−0.42, +0.38]. That was the untested reason for keeping it. Whether it stays is a matter for its own decision.
* **TrueSkill Through Time.** The 3 October decision (TTT as the leading base-rating candidate) is unchanged. The race found that TTT with surface offsets is the best rating on its own. The decided TTT, a blend, was worse than the old Elo at the 24-hour price (−0.65 [−0.95, −0.36]).
* **A Thinking refit** of the model with its new inputs. None was made; the evidence is the local non-thinking model, calibrated.
* **The project's status.** No model, dataset, market or roadmap is selected. This is a decision about which inputs a candidate model carries.
