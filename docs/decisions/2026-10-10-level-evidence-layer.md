# The level layer is part of the current best model, for men

**Decided by the owner on 10 October 2026.** The owner asked for the final method of the [level-evidence
study](../studies/lower_level_evidence/system/README.md) to be made part of the official current best model, with the
study lead's implementation brief (`docs/studies/lower_level_evidence/system/IMPLEMENTATION_PROMPT.md`, sha256
`7f0ce83d…`). The owner's words, the brief's first lines:

> "# Task: make the level layer (the "final method") part of the official current best model, for men
> [...] The owner wants the final method of the level-evidence study made part of the official current best model.
> Implement it, verify it as specified below, record it, and report back."

Two questions put to the owner while carrying it out, and the answers (10 Oct 2026):
* The uncommitted women's `indoor` fill in `tabpfn_thinking/build_frame.py`: **"Include it"** (it is the owner's
  [decision of 9 Oct](2026-10-09-indoor-input.md)).
* The 2026 data the owner asked for in the same session: recorded apart, in
  [the men's 2026 Challenger data](2026-10-10-men-2026-challenger-data.md).

Implemented, verified and recorded by Claude the same day. Process log and report:
[docs/studies/level_layer_adoption/](../studies/level_layer_adoption/README.md).

## Decision

1. **For men, every lower-level observation enters the model's inputs in main-tour terms** (tour and Slam qualifying,
   Challenger main draw and qualifying). The rules are the study's SYS, every setting as tested:
   * **Translation.** Each observation is shifted by γ_s × (the opponent's pre-match Elo − the main-tour reference
     strength), plus δ_{s,L} where A's classes allow it. First serves in and double faults (the ENV class) take δ only.
   * **Weight.** Each observation counts at w_{s,L}, role B's fitted value, capped at 1 (Challenger about 0.6,
     qualifying about 1).
   * **Per input family:** `points_52w` translated and weighted; the 17 one-step forms with the opponents' norms
     re-referenced, the match's own value shifted by δ only, the weights in the decay-and-shrink, and Stage B's tuned
     constants pinned to the reference's; the joint solves (surface IOS and the products) with a level effect estimated
     in each solve at the allowed levels, rows weighted by `w_joint`; `ratings_iid` weighted by `w_joint`, no level
     term; the Elo family K × w_results, the rated-match count advancing by w_results (men's ITF results about
     0.25–0.5, ITF-qualifying results 0).
   * **Excluded:** ITF and ITF-qualifying box scores (w = 0) until the P7 test gives them training-season parameters.
   * **Untouched:** women; age, workload counts, context, odds, and stage 2's serve-speed adjustment.
   * **Parameters by the row's own season;** rows before 2013 read 2013's; **seasons after the last fitted one read the
     last fitted season's** until the next refit (new, `params_season_ceiling: "last_fitted"`).
2. **The config:** `data/studies/current_best_model/level_layer/official.json` (sha256 `be66df29…`). It is SYS.json
   with these changes only (its `changed_from_sys`): the name; no study record folder; `ios_points_short` off (the
   input was dropped on 9 Oct; the IOS part still runs for the joint solves); the ceiling; and the opponent strength
   resolved per build. It names the frozen tables, hash-checked at every read: B's `params.parquet` (`4c559abd…`), A's
   `classes.csv` (`58e78622…`), the frozen strength (`4fa9a573…`) and Stage B's pin (`43429744…`).
3. **The opponent strength, per build:** the plain pre-match Elo on the build's own Stage 0 (Stage 1's pass, the frozen
   reference's K, no w_results weighting), written with its check into the build's tree
   (`src/eda/current_best_model/layer_config.py --resolve`). It must equal the frozen strength on the reference's
   matches; a difference is reported; a scale shift of more than 1 Elo point in a tour-season's main-tour mean is
   re-centred as the study's addition 7 did (option c).
4. **How the template is built** (the current-best-model decision's "Building it", step 2):
   ```
   ./python.sh src/eda/model_rebuild/run_chain.py --setup
   ./python.sh src/eda/model_rebuild/run_chain.py --prepare-layer --out data/studies/current_best_model/<date>
   ./python.sh src/eda/model_rebuild/run_chain.py --lane 1 --layer --out ...    # lane 2 beside it
   ./python.sh src/eda/model_rebuild/run_chain.py --lane 2 --layer --out ...
   ./python.sh src/eda/model_rebuild/run_chain.py --lane 3 --layer --out ...
   ./python.sh src/eda/model_rebuild/run_chain.py --collect --out ...
   ```
   then the odds input and the input list as before, the fits and stage 2. `--layer` runs the layer's IOS part before
   `leakproof_frame` and refuses a config resolved on another Stage 0. Prediction runs resolve the layer on their own
   Stage 0 (live rows included) and run every later step with it (`prediction_run/run.py`; `--no-layer` builds the
   template of before).
5. **The hooks are in the decided builders,** off unless `LLE_LAYER` names a config: `stage1_baselines.py`,
   `surface_elo_pieces/pieces.py`, `stage4_features.py`, `stage3_ratings.py`, `ufc_ideas/stageB_adjperf.py`,
   `match_timing/rebuild.py`, `surface_ios/build_cache.py`, `build_features.py`, `arms.py`, `probe.py` and
   `tabpfn_leakproof/build_frame.py`. They call `level_layer.py` and `level_layer_ios.py`; nothing is copied.

## Evidence

* **The study** ([README](../studies/lower_level_evidence/system/README.md)): at the statistic level the translated,
  weighted relationship predicts players' next main-tour statistics far better than pooling as equivalent (men +0.41
  [+0.34, +0.47] milli per opportunity); at the model level on 2020–2024, SYS against the reference read −0.008
  [−0.162, +0.145] mLL, unresolved; on the 2025–26 holdout +0.011 [−0.425, +0.447], unresolved. Adopted as a repair:
  data already in the model, entering in main-tour terms; the model comparison is a harm check.
* **Verification on 10 Oct 2026.** Today's tables equal the frozen reference's (72 of 72 files), so every check below
  is on the reference's tables. Builds: B_off (the template, `LLE_LAYER` unset), B_on (the official config, the new
  instance). Files: `data/studies/level_layer_adoption/checks/` and `results/`.

  | Check | Result |
  |---|---|
  | **Identity** | Pass. B_off's chain frame equals the frozen reference's on 57 of 58 inputs on all 67,226 matches; `indoor` differs only by the decided fill (32,634 matches: 32,507 women's, 127 men's US Open 2026), equal wherever the reference had a value. With the odds input and the 57-input list applied, B_off equals the current template's inputs on these tables (`data/studies/indoor_fill/arm/`) on all 58 columns, the prices and the list |
  | **Fidelity** | Pass, bit for bit. B_on's chain frame equals the study's SYS frame on all 56 inputs compared, IOS columns included (no tolerance needed); `indoor` the decided fill; `ios_points_short` (off) equals the reference's exactly. The builders also equal the code SYS was validated on, comments aside (`validated_src/`, a test) |
  | **Invariance** (G2, B_on against B_off) | Pass: 149 of 149 checks bit for bit. Women's 32,507 matches unchanged in every input; the untouched inputs (odds, context, age, workload) on every match; `ios_points_short` on every match; `points_52w` on the 4,139 men's matches out of reach |
  | **Direction** (G3) | Pass: 16 of 17 required cells as expected; `form_first_in` under the study's ENV rule, with SYS's own verdict |
  | **Leaks** | Pass. G5: the builders' own probes moved 0 protected matches and caught their controls. `match_timing/probe.py` with the layer on: 0 earlier matches moved at four cut days (13,758–31,163 checked; largest difference 6e-15) |
  | **Stage B pin** | In effect: under the layer the men's Stage B constants re-tune differently, and the pin replaced them with the reference's (as in SYS); Stage 1, the offset Elo and Stage 3 chose the reference's constants in both builds |
  | **Strength** | The plain pre-match Elo on today's Stage 0 equals `strength_elo.parquet` bit for bit on all 873,437 matches |
  | **Tests** | 366 pass, 6 expected failures (the final code: `checks/tests_final.txt`), in `test/lower_level_evidence`, `test/current_best_model` (new: the hooks off, the ceiling, the strength, option (c) reproduced bit for bit, the build config's guard, the lane plans, the refit's freeze, the accepted additions) and `test/prediction_run` |
  | **Harm check** (the owner's 9 Oct rule) | **No harm.** B_on vs B_off, men, both stages, 2020–2024, seeds 0–3 paired (`system_pairs.py`): **−0.014 [−0.162, +0.134] mLL per match, unresolved, P(better) 0.42** (+ = with the layer better; 11,672 matches). The study measured −0.008 [−0.162, +0.145]. Every other reading unresolved (both tours +0.022, women +0.062). No edge credit |
  | **Against the frozen reference** (`compare.py`) | Both tours, both stages +0.029 [−0.313, +0.372], unresolved (with the Pinnacle-first odds and the indoor fill). Input flags identical to SYS's own (the layer's dose), plus women's `indoor` (the fill) |
  | **Holdback** (errata E1's control) | The new instance (`template_2026-10-10`) against the Pinnacle-first instance of 9 Oct, both tours, both stages, 2020–2024: +0.018 [−0.125, +0.161], unresolved, P(better) 0.60 (+ = the new instance better). No harm; the batch it sees (the layer, the indoor fill, the 57-input list) is below what this control can see (half-width 0.14 against a plausible 0.10) |
  | **Replay** | Pass, bit for bit. A prediction run with the layer and the accepted package (`run.py --build`, the layer resolved on the run's own Stage 0) replayed the 23 round-of-16 matches of 15 Jul 2026 as live rows, 10 of them with the placeholder reversing the real result: all 57 inputs equal the instance's frame on all 23 (largest difference 0). The run's data was held at the freeze (Tennis My Life's dump of 8 Oct, the template's timeline), so it proves the code path; `data/studies/prediction_run/replay_2026-10-10_layer/` |

## Maintenance

* **Each season,** at the first build after it ends: refit B's parameters walk-forward into a new folder,
  `./python.sh src/eda/lower_level_evidence/relationship.py --method F4 --out <new folder> ...` (the default method is
  F5; the frozen method is F4). `--freeze` writes its record into `--out` and refuses an existing one, so the study's
  `method_freeze.json` is never overwritten. Then write a new official config with the new path and hash (a new dated
  amendment here), re-run the identity and strength checks, and record the refit. **Not built yet:** the study's
  mechanical step produces only the 2025 and 2026 rows; the 2027 refit needs it generalised to a later season
  (`relationship.py` `step_mechanical`, `elo_select_mechanical`). Until then 2027 rows read 2026's parameters.
* **Classes:** A's frozen thresholds; re-checked yearly with `classify.py`.
* **New lower-level data,** for example P7's ITF box scores (about 22 Oct – 2 Nov 2026): follow
  `docs/studies/lower_level_evidence/system/P7_plan.md`. ITF box scores stay excluded and women untouched until then.
  The P7 plan's code changes (its §10) now start from builders that carry the hooks: a sandbox needs no patch, and the
  study's patch tools recognise the integrated builders.

## Open (reported, not resolved)

* **An optional variant** the study's lead suggested: the same layer with Elo results unweighted (`weight_results: 1`).
  The Elo discount was the weakest part (worse on 2020–24 for men's matches involving players with little main-tour
  history: −0.18 [−0.31, −0.05]). Built and harm-checked only if the owner asks. **Claude's recommendation: not now.** That reading
  is one stratum of a report-only table on seasons read many times; this work's harm check leans the same way in the
  same stratum, unresolved (exposure < 10: −0.13 [−0.46, +0.20]), and a variant's model comparison resolves about
  ±0.15, so a build now would decide nothing. Test it at the P7 refit, or on a season no choice has read.
* **The women's indoor order** (the WTA's calendar first) stays the owner's to confirm (the indoor decision, where it
  is Claude's recommendation).
