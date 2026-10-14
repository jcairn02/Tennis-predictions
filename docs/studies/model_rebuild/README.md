# The current best model rebuilt on the corrected data: a tie

8 October 2026 · Run at the owner's request after the [corrections of corrupt rows](../../decisions/2026-10-08-corrupt-data-fixes.md). The study is a comparison. **The owner then decided** that the rebuilt model is the current best model, as a template built on the day's tables, not as stored files ([decision](../../decisions/2026-10-08-current-best-model.md)). The earlier model's files are unchanged.

**The request** (owner, 8 Oct 2026), on the two open items of the corrections:
* "Serve-speed records … Should I apply them to the live speed feed?" — "Yes apply them".
* "The model's own inputs … Rebuilding it and refitting on the GPU would bring them in, together with the 7 Oct changes. Should I run that and compare against the current model?" — "Then run this".

**Note for reviewers (9 Oct 2026): a flaw in this study's intervals, found after it ran. The study was not re-run.**
* **The flaw.** Every model-against-model interval here adds both models' seed-to-seed variance as if their seed noise were independent (§3: "4-week blocks plus the seeds' variance"). Both models used the same TabPFN seeds (random states 0–3), so most of that noise is shared and cancels in the difference. Adding both counts it twice.
  * Found by the adoption framework's statistics review ([finding 1](../adoption_framework/review_statistics.md)). With the same interval code, a model compared with itself got ±0.087 mLL instead of 0.
  * It shows here too: the women's "speed history alone" row compares identical forecasts (women's speed column is 0) and got ±0.11 instead of 0 (`comparison.csv`).
* **What it does.** The intervals are too wide; the estimates are right. The rows against the calibrated close are not affected: a price has no seeds.
* **How much.** The review re-read these same two models with the seed term paired, both stages, on 2020–2024 (the previous model is this study's "current"; [output](../../../data/studies/adoption_framework/seed_term_independent.out)).
  * Their per-seed losses correlate +0.97 to +0.99, and the SE fell 9–18%.
  * Both tours, + = rebuilt better: +0.07 [−0.08, +0.21] unpaired, [−0.05, +0.19] paired.
  * Rows where only the speed column differs share nearly all their seed noise, and would narrow far more.
* **What it can change.** *Inferred:* the row nearest to 0 is stage 1 at the 24-hour price, −0.26 [−0.56, +0.03] (2025–2026).
  * With an SE 9–18% narrower, it would be about [−0.53, +0.00] to [−0.51, −0.02], so it could come to read worse.
  * The 8 Oct decision's "it tied the earlier one" rests on these intervals.
* **Not re-run, on purpose.** `compare.py` now pairs the seed term, and keeps the old interval as `lo_unpaired` / `hi_unpaired` ([checklist](../adoption_framework/checklist.md), item 1). A re-run would overwrite `comparison.csv`, and would read 2025–2026 results again: the proposed clean holdout.

## In short

**Rebuilding the model on the corrected tables changes nothing measurable** (observed, `comparison.csv`). Figures are in milli-log-loss per match (mLL); positive means the rebuilt model has the lower log loss.

| Both stages (TabPFN, then the speed adjustment), debut seasons out | Matches | Rebuilt − current | 95% interval |
|---|---:|---:|---|
| Both tours 2022–2026, with the corrected speed history | 23,687 | +0.03 | [−0.13, +0.20] |
| Both tours 2022–2026, with today's speed column | 23,687 | +0.02 | [−0.14, +0.18] |
| Stage 1 alone (calibrated TabPFN) | 23,687 | +0.03 | [−0.14, +0.19] |
| Men 2024–2026 (the speed study's test), corrected speed history | 7,068 | −0.09 | [−0.33, +0.14] |
| Women 2022–2026 | 11,346 | +0.06 | [−0.15, +0.26] |
| Stage 1 at Polymarket's price 24 hours before the start, 2025–2026 | 2,629 | −0.26 | [−0.56, +0.03] |

* **Every row is a tie.** None of the 29 model-against-model rows (populations, seasons, both speed histories, the 24-hour price) has an interval that excludes 0. Season by season, 2022 to 2026, the estimates run from −0.21 to +0.26.
* **The edge over the market is the same:** against the calibrated close, +1.31 [+0.68, +1.95] for the current model and +1.34 [+0.71, +1.98] for the rebuilt one, both tours 2022–2026.
* **Why so little moves** (*inferred*). The corrected rows are a small share of each player's history, and most sit in the training years. The inputs they feed moved by a median of 0.0001–0.005 standard deviations (`input_changes.csv`). The closing odds, which carry most of the forecast, are unchanged except on 6 rows of the frame.
* **The speed fix is applied to the live feed.** The 130 impossible serve-speed records are gone from the live speed feed's history (§1).

**Suggested, then decided by the owner** ([decision](../../decisions/2026-10-08-current-best-model.md)): the rebuilt model is the current best model, as a template.
* **For it.** Its accuracy ties, and its training data is what the live tables now hold: the corrections of 8 Oct, the 7 Oct changes and the men's 2018 season. So live forecasts would come from a model trained on the data its inputs are computed from.
* **Against it.** At the 24-hour price it leans the other way (−0.26 [−0.56, +0.03]). That is the least favourable of the 29 model-against-model rows, and none of the 29 excludes 0.
* **Not finished on disk, by choice.** The owner wants the template, not stored files. A task that needs the model builds it on that day's tables, with all 16 seeds and its coefficients (the decision lists the commands).

## 1. The speed fix, applied to the live feed

*Observed* (`src/eda/input_data_audit/speed_live_panel.py`; `data/studies/serve_speed_tabpfn/live/speed_panel_frozen_corrected.json`).

* **The study's frozen panel is untouched.** It is a frozen input of the pre-registered serve-speed study, and its scorers refuse changed inputs.
* **The live feed reads a corrected copy instead** (`live/live_panel.py`). The copy is checked against the frozen file's SHA-256, so a changed frozen panel stops the live run until the copy is rebuilt.
* **How the copy is made.**
  * The study's own record table marks the 130 records not valid.
  * Its own choice (`panel.build_panel`) runs again on the Stage 0 and timing tables the frozen panel was built on (kept by the 8 Oct rebuild).
  * Without the exclusions, that choice reproduces the frozen panel exactly.
* **What changed.**
  * 107 player-matches had chosen one of the records.
  * 77 now take the Slam or Infosys point-by-point average.
  * 30 have no valid record left and are marked unusable.
  * Nothing else changed apart from 3 outlier flags on the same players.
* **The live run of 8 Oct was rerun.** Today's speed form moved for one player, by 0.18 km/h: the excluded records are old, and the 28-day memory weighs the recent ones.
* **Tests.** 7 pass (`test/serve_speed_tabpfn/test_ssp_live_form_panel.py`), one of them new: the live history never uses an excluded record.

## 2. How the model was rebuilt

**In a sandbox copy of the repository** (`src/eda/model_rebuild/run_chain.py`):
* **Why a sandbox.** Every builder of the chain writes into its own study's folder, and those folders hold the current model's evidence. None of them takes an output folder.
* **What the sandbox held:** a copy of `src/`, `docs/` and `data/studies/` taken after the corrections' rebuild of 8 Oct, plus links to the read-only raw data. Every path a builder used resolved inside the sandbox.
* **What came back.** The rebuilt frame, its input list and the builders' manifests are in `data/studies/model_rebuild/`.

**The builders, unchanged, in their documented order:**

| Step | Builders | Run time |
|---|---|---|
| Stage 1, 3 and 4 | `stage1_baselines` (Elo; constants re-tuned on 2013–2018, unchanged), `stage3_ratings` (`ratings_iid`), `stage4_features` | 19, 3, 8 min |
| The input tables | the ufc_ideas Stages A–D. A and C feed no input, but Stage D requires every stage on the same matches; A reused its tuning grids (`--reuse-grid`) | about 65 min |
| The base frame and the leak-proof IOS swap | `tabpfn_thinking/build_frame.py`, `tabpfn_leakproof/build_frame.py` | seconds |
| The offset Elo | `surface_elo_pieces/pieces.py` (Stage 1 reproduced exactly; K re-tuned on 2013–2018, unchanged), `build_frames.py` | 8 min |
| The surface IOS profile | `surface_ios/build_cache.py`, `build_features.py` (32 full-history runs), `frames.py`, `arms.py` | 19 min |
| The model frame | `surface_rating_race/model_frame.py`. Its checks passed: rows, the surface profile, the Elo swap, the 31 unchanged inputs against the rebuilt upload, labels, test ids, the flip | seconds |

**The rebuilt frame:**
* 67,226 matches × the same 58 inputs. The current frame has 63,737.
* Training (2013–2021): 42,538, against 39,918. The 2,620 more are **the men's 2018 season**, restored by the 7 Oct odds.
* Test: 24,688, of which 869 are newer 2026 matches. Those are left out of the comparison.
* 63,697 matches are in both frames. 40 changed id between the table versions and are left out.

**The inputs on the shared matches** (`input_changes.csv`):
* Every box-score input moved a little on almost every row, because the IOS solver and the opponent-adjusted measures solve all players together. The median move was 0.0001–0.005 standard deviations; correlations were 0.98 or more.
* The rows the faults touched moved much more: the 99th-percentile move is up to 0.96 standard deviations (`prod_first_in`, training). The WTA 2015 window drives the training rows.
* **Split ids:** test rows without the form inputs fall from 67 to 26.
* **Ages and odds:** ages changed on 9 test rows; odds on 3 training and 3 test rows.

## 3. The fits and the comparison

* **Fits** (`src/eda/model_rebuild/fits.py`):
  * the serve-speed study's runner, unchanged: 8 estimators, softmax temperature 0.9, pretraining limits ignored, its job data and queries;
  * the arm "model" on the rebuilt frame, seasons 2019–2026 (each trained on 2013 .. Y − 1), seeds 0–3: 32 fits, 17 minutes on the RTX 5090;
  * it took its turn on the card with another session's runner, as the studies' runners do.
* **Speed columns** (`src/eda/model_rebuild/speed_columns.py`). The adjustment's column `spd_L_B` was recomputed on the corrected speed history by the study's own column builder. On the frozen history the builder reproduces the stored columns exactly. With the correction, 77 frame matches move by 1 unit or more and 306 by 0.25 or more.
* **Scoring** (`src/eda/model_rebuild/compare.py`):
  * both models through the same code. The calibration slopes and the speed adjustment's s and b were refitted walk-forward on 2019 .. Y − 1 from each model's own seeds 0–3, debut seasons out, b shrunk with τ = 0.05;
  * on the current model this reproduces the decided coefficients of 2024–2026 exactly (s_atp, s_wta, b, its SE);
  * paired log loss with the serve-speed study's intervals: 4-week blocks plus the seeds' variance.
* **The refitted coefficients** for 2026 (s_atp, s_wta, b̃):

  | Model | Speed history | s_atp | s_wta | b̃ |
  |---|---|---:|---:|---:|
  | Current | today's | 0.900 | 0.917 | 0.0376 |
  | Rebuilt | today's | 0.896 | 0.919 | 0.0372 |
  | Rebuilt | corrected | 0.896 | 0.919 | 0.0342 |

* **What the comparison is not:**
  * the decided application averages 16 seeds; both models are compared here on seeds 0–3;
  * the comparison covers the matches both frames hold, not the 869 newer ones (a proposed clean holdout of matches from 29 Jul 2026 is under discussion in another study);
  * nothing here was pre-registered: it is a robustness check of a data correction, not a new model.

## 4. Files and reruns

| What | Where |
|---|---|
| Code | `src/eda/model_rebuild/`: `run_chain.py` (the sandbox chain, lanes 1, 1a, 2, 3), `fits.py`, `speed_columns.py`, `input_changes.py`, `compare.py`; the live speed fix in `src/eda/input_data_audit/speed_live_panel.py` and `src/eda/serve_speed_tabpfn/live/live_panel.py` |
| Evidence | `data/studies/model_rebuild/`: `model_frame.parquet`, `model_inputs.json`, `chain_lane*.json`, `chain_outputs/` (the builders' manifests), `fits/` (32), `speed_columns_corrected.*`, `input_changes*.csv`, `comparison.csv`, `comparison.json` |
| The sandbox | `C:/Users/zerom/tnr_sb` (16 GB, outside the repository: Windows' 260-character path limit ruled out the session folder). Deleted on the owner's word after the run: its links were removed first, and the repository's data was intact. Its logs are kept in `chain_logs/` |

```
./python.sh src/eda/model_rebuild/run_chain.py --setup           # then --lane 1 and --lane 2 side by side, --lane 3, --collect, --cleanup
# (the run of 8 Oct used an earlier lane order: lane 1, a lane 1a for the ufc_ideas Stages A and C, lane 1 resumed;
#  chain_lane*.json records each step's exact command)
./python_tabpfn_local.sh src/eda/model_rebuild/fits.py --seeds 0-3
./python.sh src/eda/model_rebuild/speed_columns.py
./python.sh src/eda/model_rebuild/compare.py
```
