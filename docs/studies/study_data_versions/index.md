# Which data each table was built on: the index

Generated 2026-10-22T18:55 by `src/eda/study_data_versions/inventory.py` (read-only). Do not edit by hand: run the script.
Owner's request and the plan: [process log](process_log.md); the rule it supports: [draft](rule_draft.md).

## The histories on disk

| History | What it is | Matches | Newest match | Written | Same matches as | Recreatable from a recipe |
|---|---|---:|---|---|---|---|
| repository | the repository's history (the shared tables) | 873,964 | 2026-10-20 | 2026-10-21T06:48 | – | no: the code that built it is not kept |
| before 2026-10-07T0005Z | saved by the shared rebuild of 2026-10-07T0005Z: the history in use before it | 872,704 | 2026-09-21 | 2026-09-30T10:30 | – | no: the code that built it is not kept |
| before 2026-10-08T1853Z | saved by the shared rebuild of 2026-10-08T1853Z: the history in use before it | 873,364 | 2026-10-05 | 2026-10-06T17:07 | – | no: the code that built it is not kept |
| before 2026-10-14T0412Z | saved by the shared rebuild of 2026-10-14T0412Z: the history in use before it | 873,437 | 2026-10-07 | 2026-10-08T11:54 | frozen reference, folder tnr_lle | no: the code that built it is not kept |
| before 2026-10-14T2115Z | saved by the shared rebuild of 2026-10-14T2115Z: the history in use before it | 873,636 | 2026-10-12 | 2026-10-13T21:13 | before 2026-10-14T2119Z | no: the code that built it is not kept |
| before 2026-10-14T2119Z | saved by the shared rebuild of 2026-10-14T2119Z: the history in use before it | 873,636 | 2026-10-12 | 2026-10-13T21:13 | before 2026-10-14T2115Z | no: the code that built it is not kept |
| before 2026-10-21T1347Z | saved by the shared rebuild of 2026-10-21T1347Z: the history in use before it | 873,681 | 2026-10-12 | 2026-10-14T14:21 | – | no: the code that built it is not kept |
| frozen reference | the frozen reference of 8 Oct (kept by decision, with its code) | 873,437 | 2026-10-07 | 2026-10-08T11:54 | before 2026-10-14T0412Z, folder tnr_lle | yes: kept with its code and environment |
| folder tnr_lle | the build folder tnr_lle | 873,437 | 2026-10-07 | 2026-10-08T11:54 | before 2026-10-14T0412Z, frozen reference | only while the folder exists: its code is inside it |
| folder tnr_lyr_new | the build folder tnr_lyr_new | 875,172 | 2026-10-07 | 2026-10-10T10:41 | – | only while the folder exists: its code is inside it |
| folder tnr_sys4 | the build folder tnr_sys4 | 1,171,445 | 2026-10-07 | 2026-10-09T17:49 | – | only while the folder exists: its code is inside it |
| folder tnr_tpl1016 | the build folder tnr_tpl1016 | 926,984 | 2026-10-12 | 2026-10-16T14:36 | – | only while the folder exists: its code is inside it |
| folder tnr_tpl1021 | the build folder tnr_tpl1021 | 928,337 | 2026-10-20 | 2026-10-21T07:35 | – | only while the folder exists: its code is inside it |

## The tables under data/studies

1,533 parquet tables scanned; 1,275 hold match ids. **296 are on an older history** than the repository's (they equal an older one, or hold matches it has since dropped).

| Verdict | History | Tables | Size |
|---|---|---:|---:|
| inside | before 2026-10-07T0005Z | 125 | 2.9 GB |
| inside | before 2026-10-08T1853Z .. folder tnr_tpl1021 | 85 | 1.5 GB |
| outside | closest repository | 61 | 0.8 GB |
| equals | before 2026-10-07T0005Z | 10 | 0.6 GB |
| outside | closest folder tnr_sys4 | 47 | 0.6 GB |
| inside | folder tnr_tpl1021 | 28 | 0.5 GB |
| inside | folder tnr_tpl1016 .. folder tnr_tpl1021 | 8 | 0.5 GB |
| inside | repository .. folder tnr_tpl1021 | 102 | 0.4 GB |
| inside | before 2026-10-07T0005Z .. folder tnr_tpl1021 | 552 | 0.4 GB |
| equals | before 2026-10-21T1347Z | 6 | 0.4 GB |
| outside | closest before 2026-10-21T1347Z | 9 | 0.4 GB |
| outside | closest before 2026-10-14T2115Z | 11 | 0.3 GB |
| equals | before 2026-10-14T0412Z | 10 | 0.3 GB |
| outside | closest folder tnr_tpl1016 | 23 | 0.3 GB |
| inside | before 2026-10-21T1347Z .. folder tnr_tpl1016 | 11 | 0.3 GB |
| inside | folder tnr_tpl1016 | 13 | 0.2 GB |
| equals | folder tnr_sys4 | 5 | 0.2 GB |
| inside | folder tnr_sys4 | 13 | 0.2 GB |
| equals | folder tnr_lyr_new | 5 | 0.1 GB |
| equals | repository | 4 | 0.1 GB |
| outside | closest before 2026-10-08T1853Z | 2 | 0.1 GB |
| inside | before 2026-10-14T2115Z .. folder tnr_tpl1016 | 6 | 0.1 GB |
| inside | before 2026-10-07T0005Z .. folder tnr_lyr_new | 3 | 98 MB |
| inside | before 2026-10-14T2115Z .. folder tnr_tpl1021 | 47 | 78 MB |
| inside | folder tnr_sys4 .. folder tnr_lyr_new | 11 | 45 MB |

"equals": the table holds exactly that history's matches. "inside": every history from the first to the last named holds all its matches (a main-tour table sits inside many). "outside": it holds matches no kept history has (candidate builds, live rows); the closest history is named.

### By study folder (tables on an older history)

| Study folder | Tables | On an older history | Size |
|---|---:|---:|---:|
| daily_prediction | 429 | 45 | 2.7 GB |
| current_best_model | 69 | 20 | 1.1 GB |
| ufc_ideas | 14 | 14 | 1.0 GB |
| lower_level_evidence | 48 | 21 | 0.8 GB |
| data_gaps_2026 | 49 | 4 | 0.7 GB |
| source_reconciliation | 87 | 36 | 0.7 GB |
| surface_ios | 269 | 45 | 0.6 GB |
| predictability_diagnostic | 10 | 5 | 0.5 GB |
| feature_universe | 6 | 4 | 0.4 GB |
| level_layer_adoption | 21 | 10 | 0.3 GB |
| shot_level | 4 | 4 | 0.3 GB |
| match_timing | 23 | 2 | 0.3 GB |
| rating_systems | 3 | 3 | 0.2 GB |
| unpriced_leads | 18 | 6 | 0.2 GB |
| feature_interactions | 5 | 2 | 0.1 GB |
| feature_alpha_audit | 11 | 6 | 0.1 GB |
| surface_elo_pieces | 6 | 5 | 0.1 GB |
| box_score_gate_review | 50 | 1 | 0.1 GB |
| point_sequence | 3 | 0 | 0.1 GB |
| surface_rating_race | 3 | 3 | 0.1 GB |
| ios_product_centring | 2 | 2 | 0.1 GB |
| prediction_run | 11 | 1 | 100 MB |
| serve_speed_tabpfn | 22 | 16 | 99 MB |
| master_pipeline | 3 | 1 | 90 MB |
| event_levels | 3 | 3 | 84 MB |
| tabpfn_thinking | 4 | 4 | 73 MB |
| serve_return_leads | 8 | 4 | 61 MB |
| tour_pooling | 36 | 0 | 54 MB |
| market_anchoring | 3 | 1 | 46 MB |
| qualifying_targets | 8 | 6 | 37 MB |

## Code that may mix versions

A static first pass by file names. **76 file(s) are likely:** outside the model chain and the daily engine, they name one of the snapshot's chain tables together with a live base table (Stage 0, the timeline or the odds link) and no saved history. Each is read by hand.

| Code | Snapshot tables it names | Verdict |
|---|---|---|
| `src/eda/bet_timing/frame.py` | data/studies/surface_elo_pieces/early_price_frame.parquet; data/studies/surface_elo_pieces/frame.parquet; data/studies/surface_elo_pieces/pieces.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/box_score_gate_review/coverage.py` | data/studies/surface_ios/cache/pool.parquet | not read: names the module only: probably not reading the table |
| `src/eda/box_score_gate_review/simulate_gate.py` | data/studies/surface_ios/cache/pool.parquet | not read: names the module only: probably not reading the table |
| `src/eda/close_drift/drift.py` | data/studies/predictability_diagnostic/stage1_baselines.parquet; data/studies/surface_ios/arms/base.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/data_gaps_2026/coverage.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/data_gaps_2026/exposure.py` | data/studies/surface_rating_race/model/model_frame.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/event_levels/blend.py` | data/studies/surface_elo_pieces/frame.parquet; data/studies/surface_elo_pieces/pieces.parquet; data/studies/surface_ios/cache/pool.parquet | not read: names the module only: probably not reading the table |
| `src/eda/event_levels/frame.py` | data/studies/surface_elo_pieces/frame.parquet; data/studies/surface_elo_pieces/pieces.parquet; data/studies/surface_ios/arms/base.parquet; data/studies/surface_ | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/feature_interactions/features/f25_switch.py` | data/studies/surface_elo_pieces/pieces.parquet; data/studies/surface_ios/cache/pool.parquet | not read: names the module only: probably not reading the table |
| `src/eda/feature_interactions/redteam/binj_attack.py` | data/studies/surface_elo_pieces/pieces.parquet; data/studies/surface_ios/arms/base.parquet; data/studies/surface_rating_race/model/model_frame.parquet | not read: names the module only: probably not reading the table |
| `src/eda/feature_interactions/round0/body/schemas.py` | data/studies/surface_rating_race/model/model_frame.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/feature_interactions/round0/mathematics/markov_composition.py` | data/studies/predictability_diagnostic/stage3_ratings.parquet; data/studies/surface_ios/arms/base.parquet; data/studies/surface_ios/surface_features.parquet; da | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/feature_interactions/round0/mechanics/feature_spread.py` | data/studies/surface_ios/arms/base.parquet; data/studies/surface_ios/surface_features.parquet; data/studies/surface_rating_race/model/model_frame.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/feature_interactions/round1/feasibility/assemble.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/feature_interactions/round1/feasibility/rulings_c.py` | data/studies/predictability_diagnostic/stage3_ratings.parquet; data/studies/surface_elo_pieces/pieces.parquet; data/studies/surface_ios/arms/base.parquet; data/ | not read: names the module only: probably not reading the table |
| `src/eda/feature_interactions/verify_final/gate_round2.py` | data/studies/surface_elo_pieces/frame.parquet; data/studies/surface_elo_pieces/pieces.parquet; data/studies/tabpfn_thinking/frame.parquet | not read: names the module only: probably not reading the table |
| `src/eda/feature_provenance/counts/postframe.py` | data/studies/surface_rating_race/model/model_frame.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/feature_provenance/counts/stage0_tiers.py` | data/studies/surface_rating_race/model/model_frame.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/feature_universe/catalogue/build_universe.py` | data/studies/surface_ios/arms/base.parquet; data/studies/surface_ios/cache/pool.parquet | not read: names the module only: probably not reading the table |
| `src/eda/feature_universe/catalogue/spec_market.py` | data/studies/tabpfn_thinking/frame.parquet | not read: names the module only: probably not reading the table |
| `src/eda/in_season_retrain/check.py` | data/studies/surface_rating_race/model/model_frame.parquet | not read: names the module only: probably not reading the table |
| `src/eda/indoor_fill/status.py` | data/studies/surface_ios/arms/base.parquet; data/studies/tabpfn_thinking/frame.parquet | not read: names the module only: probably not reading the table |
| `src/eda/infosys_atp_backfill/compare.py` | data/studies/surface_ios/arms/base.parquet; data/studies/surface_ios/cache/pool.parquet; data/studies/surface_rating_race/model/model_frame.parquet | not read: names the module only: probably not reading the table |
| `src/eda/input_data_audit/model_frame_checks.py` | data/studies/surface_ios/cache/pool.parquet; data/studies/surface_ios/surface_features.parquet; data/studies/surface_rating_race/model/model_frame.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/input_data_audit/review/A3-referee/rc.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/input_data_audit/review/B1-rederive/r02_f7_people.py` | data/studies/surface_ios/arms/base.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/input_data_audit/review/B1-rederive/r09_scopes.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/input_data_audit/review/B1-rederive/r10_verdict.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/input_data_audit/review/B2-skeptic/write_round2.py` | data/studies/predictability_diagnostic/stage1_baselines.parquet; data/studies/surface_ios/arms/base.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/input_data_audit/review/B3-referee/f11_f13_odds.py` | data/studies/surface_rating_race/model/model_frame.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/input_data_audit/review/B3-referee/f7_identity.py` | data/studies/surface_ios/arms/base.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/input_data_audit/speed/a14_propagation.py` | data/studies/surface_ios/arms/base.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/ios_product_centring/probe.py` | data/studies/predictability_diagnostic/stage1_baselines.parquet; data/studies/surface_ios/arms/base.parquet; data/studies/surface_ios/cache/pool.parquet | not read: names the module only: probably not reading the table |
| `src/eda/merge_feasibility/scan.py` | data/studies/surface_ios/arms/base.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/point_sequence/carry_data.py` | data/studies/predictability_diagnostic/stage3_ratings.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/point_sequence/diag_edge_location.py` | data/studies/surface_ios/arms/base.parquet; data/studies/surface_rating_race/predictions.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/point_sequence/med_residual_screen.py` | data/studies/surface_ios/arms/base.parquet; data/studies/tabpfn_thinking/frame.parquet | not read: names the module only: probably not reading the table |
| `src/eda/point_sequence/pace_screen.py` | data/studies/surface_ios/arms/base.parquet; data/studies/tabpfn_thinking/frame.parquet | not read: names the module only: probably not reading the table |
| `src/eda/point_sequence/trait_s4_explore.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/predictive_frontier/score.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/qualifying_targets/frame.py` | data/studies/surface_elo_pieces/frame.parquet; data/studies/surface_elo_pieces/pieces.parquet; data/studies/surface_ios/cache/pool.parquet; data/studies/surface | not read: names a model folder: probably consistent (a static guess) |
| `src/eda/qualifying_targets/pull_check.py` | data/studies/surface_rating_race/model/model_frame.parquet | not read: names the module only: probably not reading the table |
| `src/eda/rg_first_serve_recount/recount.py` | data/studies/surface_ios/cache/pool.parquet | not read: names the module only: probably not reading the table |
| `src/eda/rg_first_serve_recount/review_followup/R2-skeptic/rgx.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/rg_first_serve_recount/review_followup/R2-skeptic/svx3.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/rg_first_serve_recount/review_followup/R3-referee/rates.py` | data/studies/surface_ios/cache/pool.parquet | not read: names the module only: probably not reading the table |
| `src/eda/rg_first_serve_recount/review_followup/R3-referee/simulate.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/rg_first_serve_recount/review_followup/R3-referee/svx_addendum.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/rg_first_serve_recount/review_followup/R3-referee/svx_simulate.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/rg_first_serve_recount/sources.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/serve_return_leads/readings.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/serve_return_leads/robustness.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/serve_speed_tabpfn/design/auditor_gate2.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/serve_speed_tabpfn/design/auditor_r4_rebuild.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/serve_speed_tabpfn/design/engineer_clock.py` | data/studies/surface_ios/arms/base.parquet; data/studies/surface_rating_race/model/model_frame.parquet | not read: names the module only: probably not reading the table |
| `src/eda/serve_speed_tabpfn/design/engineer_coverage.py` | data/studies/surface_rating_race/model/model_frame.parquet | not read: names the module only: probably not reading the table |
| `src/eda/serve_speed_tabpfn/design/modeller_common.py` | data/studies/surface_rating_race/model/model_frame.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/serve_speed_tabpfn/latency/availability.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/serve_speed_tabpfn/latency/features_latency.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/shot_level/common.py` | data/studies/surface_ios/arms/base.parquet; data/studies/surface_ios/cache/pool.parquet | not read: names the module only: probably not reading the table |
| `src/eda/shot_level/stage0_coverage.py` | data/studies/surface_ios/cache/pool.parquet | not read: names the module only: probably not reading the table |
| `src/eda/shot_level/stage0_summary.py` | data/studies/predictability_diagnostic/stage4_features.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/shot_level/stage1_stats.py` | data/studies/surface_ios/cache/pool.parquet | not read: names the module only: probably not reading the table |
| `src/eda/shot_level/stage2_summary.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/shot_level/stage3_profiles.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/source_reconciliation/atp_analysis.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/source_reconciliation/ctx_context.py` | data/studies/surface_ios/arms/base.parquet; data/studies/surface_rating_race/model/model_frame.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/source_reconciliation/ctx_dob.py` | data/studies/surface_ios/arms/base.parquet; data/studies/surface_rating_race/model/model_frame.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/source_reconciliation/ctx_handcheck.py` | data/studies/surface_ios/arms/base.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/source_reconciliation/ctx_results.py` | data/studies/surface_rating_race/model/model_frame.parquet | not read: names the module only: probably not reading the table |
| `src/eda/source_reconciliation/ctx_summary.py` | data/studies/surface_ios/arms/base.parquet; data/studies/surface_rating_race/model/model_frame.parquet | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/source_reconciliation/odds_common.py` | data/studies/surface_elo_pieces/pieces.parquet; data/studies/surface_ios/arms/base.parquet; data/studies/surface_ios/cache/pool.parquet; data/studies/surface_ra | not read: names a snapshot table's file and a live base table: a candidate |
| `src/eda/unpriced_leads/build_extras.py` | data/studies/predictability_diagnostic/stage1_baselines.parquet; data/studies/surface_ios/arms/base.parquet; data/studies/surface_ios/cache/pool.parquet | mixes: confirmed: elo_at_matches() inner-joins the 30 Sep Stage 1 (the 7 Oct snapshot) with today's history (screen.STAGE0_M): matches that differ drop or get no Elo (the 22 Oct audit; read by the lead) |
| `src/eda/unpriced_leads/build_rhythm.py` | data/studies/surface_ios/arms/base.parquet; data/studies/surface_ios/cache/pool.parquet; data/studies/surface_ios/surface_features.parquet | mixes: confirmed: left-joins the 6 Oct surface IOS (built on the 7 Oct snapshot) onto a frame of today's history: matches not in the snapshot get blanks (read by the lead, 22 Oct) |
| `src/ratings/elo.py` | data/studies/surface_ios/arms/base.parquet | not read: names the module only: probably not reading the table |
| `src/eda/serve_return_leads/elasticity.py` |  | mixes: confirmed (missed by the static pass): long_table() reads the 6 Oct surface IOS with today's Stage 0 and timeline; before 29 Jul, 75 matches get no ratings and 95 since-dropped matches feed them (measured 22 Oct). The static triage guessed 'model folder' here: it can miss a mix |

**129 weak flags, not read:** files that name some table built on an older history and a live base table, inside the chain or the engine, or naming only a study's own older outputs. By code folder: input_data_audit 29, predictability_diagnostic 17, match_timing 9, rg_first_serve_recount 9, daily_prediction 6, p6_data_issues 6, source_reconciliation 6, feature_provenance 5, surface_elo_pieces 5, feature_interactions 4, serve_speed_tabpfn 4, prediction_pipeline 3, current_best_model 2, data_continuity 2, surface_ios 2, tabpfn_thinking 2, betonline_lines 1, indoor_fill 1, infosys_atp_backfill 1, master_pipeline 1, men_lower_level_fill 1, point_sequence 1, prediction_run 1, qualifying_targets 1, serve_speed_sources 1, sharp_benchmark 1, shot_level 1, smoke_elo_walkforward.py 1, surface_rating_race 1, ufc_ideas 1, unpriced_leads 1, point_sources 1, config.py 1, overview.py 1.

## Build folders on this machine

| Folder | Size | History | Own code | In use | Replay registry | Named by |
|---|---:|---:|---|---|---|---:|
| `tnr_dump_freeze` | 15 MB |  | no |  | yes | 17 |
| `tnr_dump_freeze_1014` | 15 MB |  | no |  | yes | 7 |
| `tnr_dump_freeze_1016` | 15 MB |  | no |  | yes | 3 |
| `tnr_dump_freeze_10211347` | 15 MB |  | no |  | yes | 2 |
| `tnr_feed` | 0.8 GB |  | no |  |  | 6 |
| `tnr_lle` | 20.3 GB | 873,437 | yes |  |  | 16 |
| `tnr_lyr_new` | 23.7 GB | 875,172 | yes |  |  | 23 |
| `tnr_mlf` | 0.3 GB |  | no |  |  | 5 |
| `tnr_sys4` | 23.2 GB | 1,171,445 | yes |  |  | 7 |
| `tnr_tl_box` | 0.3 GB |  | no |  |  | 4 |
| `tnr_tpl1016` | 16.5 GB | 926,984 | yes |  |  | 9 |
| `tnr_tpl1021` | 17.4 GB | 928,337 | yes | **yes** |  | 13 |

## Files

`data/studies/study_data_versions/`: `histories.csv`, `tables.csv`, `readers.csv`, `mixing.csv`, `folders.csv`, `summary.json`.
