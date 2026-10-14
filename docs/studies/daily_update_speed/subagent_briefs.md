# Subagent briefs, verbatim

The briefs given to the scoping subagents (10 Oct 2026, about 18:05 PDT), for the process log (rule 6). Each agent got
the COMMON part followed by its own ASSIGNMENT.

## COMMON

```
You are helping scope an engineering change in the repository C:\Users\zerom\Documents\Tennis-predictions (a tennis
prediction research project; Windows; Python via ./python.sh only).

STRICTLY READ-ONLY. Do not edit, create or delete any file. Do not run any builder, test or script that writes files.
You may read files, grep, and run read-only shell commands (ls, head, reading JSON/logs). Do not run ./python.sh at all.

THE PROBLEM. The model's inputs (57 columns, listed below) for a day's upcoming matches are produced today by
src/eda/prediction_run/run.py --build, which rebuilds the whole input chain from scratch in a sandbox copy of the
repository: Stage 0 (about 875,000 matches of all levels), then about 35 builder steps over the full history. It takes
about 2 hours. The owner needs a daily update in minutes. The model itself is not retrained daily (season Y's model is
trained on seasons 2013..Y-1). Every input of a match depends only on results that finished before the match could start
(a "leak-proof" design), so the inputs of past matches do not change when new results arrive: only the upcoming
matches' inputs must be computed. The bar for any faster path: its inputs must equal the full rebuild's exactly (or
within solver tolerance for joint solves), as src/eda/prediction_run/replay.py checks.

THE 57 INPUTS: odds_logit ratings_iid elo_games adjperf_tpw_2w points_52w sets_14d age age_sq form_ace form_df
form_first_in form_first_won form_second_won form_hold form_bp_saved form_bp_faced_pg form_brk form_bp_conv
form_rpw_first form_rpw_second formdef_ace formdef_df formdef_first_in formdef_bp_faced_pg iosO_ace iosD_ace iosO_df
iosD_df iosO_first_in iosD_first_in iosO_first_won iosD_first_won iosO_second_won iosD_second_won iosO_hold iosD_hold
iosO_bp_saved iosD_bp_saved prod_ace prod_df prod_first_in prod_first_won prod_second_won prod_hold prod_bp_saved tour
surface level indoor best_of round elo_overall elo_surf_offset surf_season_a surf_season_b surf_layoff_a surf_layoff_b
(odds_logit is replaced by the live price at bet time; the context inputs come from Stage 0.)

USEFUL MAPS: src/eda/prediction_run/run.py (stage0_steps: the preparation steps), src/eda/model_rebuild/run_chain.py
(LANES: the chain's steps), src/eda/tabpfn_thinking/common.py (SOURCES and FEATURES: which table and column each input
comes from in the first frame), src/eda/tabpfn_leakproof/ (REPLACED: columns replaced by the leak-proof versions),
src/eda/surface_elo_pieces/build_frames.py, src/eda/surface_ios/arms.py, src/eda/surface_rating_race/model_frame.py.
The level layer's hooks (LLE_LAYER, src/eda/lower_level_evidence/level_layer.py and level_layer_ios.py) sit inside
several builders and must keep working. Step runtimes (minutes, one build alone, approximate): see the ASSIGNMENT.

FOR EACH BUILDER IN YOUR ASSIGNMENT, report (with file:line references):
1. What it reads and writes (tables, columns).
2. Which of the 57 inputs its outputs reach, directly or through later steps; or "none" (report-only, diagnostics,
   superseded columns). Be precise: a step whose output is read but whose columns are all replaced later reaches none.
3. How its computation depends on history: (a) a sequential pass with per-player state (Elo-like, decayed sums,
   counters); (b) joint solves per day or week across players (IOS-like); (c) tuning grids or fitted constants (and
   whether the constants are pinned or reproduced anyway); (d) window aggregates; (e) whole-table batch fits.
4. Where its runtime goes (tuning grid, Python loops over all matches, data loading, repeated passes).
5. What a fast "live mode" would need for it: e.g. skip (if it reaches no input); constants from the last full build
   instead of re-tuning; a saved state at a cut date and a resume over the new matches only; computing only the rows of
   the upcoming matches; a one-day joint solve instead of every day's. Say what state would have to be saved.
6. Risks for exact equality with the full rebuild (randomness, ordering, floating point, global normalisations over all
   history such as season means or standardisation, anything that changes past values when new data arrives).

Be concrete and brief: a table or a short block per builder, then a 5-line summary of the biggest wins. Do not
speculate beyond what the code shows; label inferences as such.
```

## ASSIGNMENT A (preparation path)

```
Your builders (the preparation path of a prediction run, in order): src/eda/predictability_diagnostic/stage0_build.py
(with --live-rows), src/eda/current_best_model/additions.py (--apply, --pin-timing), src/eda/prediction_run/inject.py,
src/eda/predictability_diagnostic/stage0_checks.py, src/eda/current_best_model/layer_config.py (--resolve: an Elo pass
for the opponent strength), src/eda/predictability_diagnostic/stage1_odds.py, src/eda/match_timing/link_sources_c.py,
src/eda/match_timing/timing.py, src/eda/match_timing/timing_check.py, src/eda/match_timing/rebuild.py (per-player
features, the timed IOS solves via ios_time.py, the merge; about 8 minutes). The whole preparation took about 20
minutes before rebuild.py.
```

## ASSIGNMENT B (Elo, ratings, Stage 4, Elo pieces)

```
Your builders: src/eda/predictability_diagnostic/stage1_baselines.py (about 19-25 min; an Elo tuning grid),
src/eda/predictability_diagnostic/stage3_ratings.py (about 2-9 min), src/eda/predictability_diagnostic/stage4_features.py
(about 9-20 min), src/eda/surface_elo_pieces/pieces.py (about 7-13 min), src/eda/surface_elo_pieces/build_frames.py.
```

## ASSIGNMENT C (the UFC-ideas stages)

```
Your builders: src/eda/ufc_ideas/stageA_ratings.py (run with --reuse-grid; about 14-29 min), stageA_features.py,
stageC_fatigue.py, stageC_sos.py (about 2-9 min), stageC_rundown.py, stageB_adjperf.py (about 27 min), stageB_ios.py
(about 13 min), src/eda/ios_constants/registry.py --check, stageB_split.py (about 5 min), stageB_rundown.py (about
15 min), stageD_profile.py (about 6 min), stageD_rundown.py. Find also which step writes
data/studies/ufc_ideas/stageD_features.parquet and stageD_profile_features.parquet (the first frame reads them).
```

## ASSIGNMENT D (frames, surface IOS, and the input map)

```
Your builders: src/eda/tabpfn_thinking/build_frame.py (with common.py), src/eda/tabpfn_leakproof/build_frame.py (with its
common.py: REPLACED), src/eda/surface_ios/build_cache.py (about 1 min), src/eda/surface_ios/build_features.py (about
15 min alone), src/eda/surface_ios/frames.py, src/eda/surface_ios/arms.py, src/eda/surface_rating_race/model_frame.py.
ALSO, the central deliverable: for each of the 57 inputs, the chain of custody in the final model frame: the final
column, the table it was taken from, and the builder step that computed its value (following replacements through the
leak-proof frame, the Elo-pieces frame and the surface-IOS arms). Give it as a 57-row table.
```
