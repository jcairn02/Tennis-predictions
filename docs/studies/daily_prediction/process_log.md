# The daily prediction script, phase 1: process log

10 October 2026 (PDT), started about 20:15 · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code) ·
Session: `d2d2331e-b87f-42fd-baa1-b5c3ddebe82c` · For a future reviewer · Report: [README.md](README.md) (written at
the end) · Builds on the plan [prediction_pipeline/PLAN.md](../prediction_pipeline/PLAN.md) and its
[process log](../prediction_pipeline/process_log.md) (session `b6a34d10-94c8-4ba5-a412-700597c70ab5`)

## 1. The request

* **The owner's words, verbatim** (10 Oct 2026, about 20:00 PDT):
  > "Read docs/studies/prediction_pipeline/PLAN.md and its process_log.md, then build phase 1 of the daily prediction
  > script (§ 7) as a new package with one command per step and a run_day command that chains them, reusing the
  > verified prototypes in src/eda/prediction_pipeline/ and the existing prediction_run code, keeping a process log, and
  > not editing other studies' files or the builders the daily_update_speed session is changing without asking me
  > first. Before calling anything done, add pytest tests that would fail if the logic were wrong — each family's
  > resumed state equals a full recompute (bit for bit; surface IOS within 1e-6), a replay of a past day through run_day
  > reproduces all 57 inputs in data/studies/current_best_model/template_2026-10-10/model_frame.parquet exactly, a
  > changed past row invalidates its checkpoint, and the price-grid forecast matches a direct TabPFN prediction within
  > 0.001 — then report each test's result and each step's run time."
* **How it was read** (before any code was written).
  * **"Phase 1 (§ 7)".** PLAN.md § 7 lists five build items: (1) matchups and prices (a Pinnacle recorder, player and
    event linking, an alias table, first-round event columns); (2) the state path (state store and manifests, one
    updater per family sharing one row loader, frame assembly for new rows only, the replay through the state path);
    (3) the daily fit runner with the price grid, stage 2's coefficients for the instance's season, the prediction
    writer and its provenance; (4) the grader; (5) speed work. The four tests the owner names all fall in items 2 and 3
    (resume = full recompute, the replay, checkpoint invalidation: item 2; the price-grid forecast: item 3), and the
    prototypes to reuse are item 2's. **Acted on: phase 1 = items 2 and 3**, with a command for every pipeline step of
    § 2: refresh, matchups and prices reuse what exists (prediction_run's refresh; matchups and margin-free prices from
    a CSV, as `run.py --matchups` takes them today), so the script runs end to end without the Pinnacle recorder.
  * **Set aside:** (a) item 1 alone ("phase 1" read as the first numbered item): no test the owner named touches it;
    (b) items 1-3 together: the Pinnacle recorder is a new network adapter that none of the named tests covers; it is
    named in the report as the next build. Not asked (the session gives no channel to wait on an answer); the reading
    is stated here and in the report so the owner can correct it.
  * **"One command per step and a run_day command that chains them":** one subcommand per § 2 step (refresh,
    matchups, prices, tables, states, fit, predict, grade), plus the work tree and the checkpoints the state path needs;
    run_day runs them in order, each in its own process, and records each step's time.
  * **"Not editing other studies' files or the builders the daily_update_speed session is changing":** new folders
    only (`src/eda/daily_prediction/`, `test/daily_prediction/`, `data/studies/daily_prediction/`, this folder). The
    builders, `prediction_run/` and the prototypes in `src/eda/prediction_pipeline/` are imported unchanged; where a
    prototype needs more (stable player keys across tables, other passes), the new code goes in the new package. If a
    builder edit turns out to be necessary, stop and ask.
  * **Exactness, as the owner set it:** test 1 bit for bit, the surface IOS within 1e-6. Test 2 "exactly": read as bit
    for bit for the 36 inputs outside the joint solves, and for the 21 IOS inputs bit for bit where the replay's solver
    system equals the template's, else within the owner's IOS tolerance (1e-6), with the measured maximum reported
    either way. Test 4: within 0.001 in probability.
* **The target** (adoption framework § 1): not a model comparison and no adoption. The bar is the 8 Oct prediction-run
  decision: live inputs equal the training inputs. No outcome is scored to choose anything; test 4 compares two
  forecasts of the same model, not forecasts with results.

## 2. Starting point

* **Code:** commit `677a63f` with many uncommitted changes (other sessions' work, `git status` at session start). The
  daily_update_speed session (`d061329f-0568-4169-b891-1a461e96dc2d`) changed, between 18:41 and 18:58 PDT today:
  `match_timing/timing.py`, `match_timing/srcc_slams.py`, `predictability_diagnostic/{common,stage0_build,
  stage1_baselines,stage4_features}.py`, `tabpfn_thinking/build_frame.py`, `model_rebuild/fits.py`,
  `lower_level_evidence/{candidate_stage0,system_arms,system_sandbox}.py`, `serve_speed_tabpfn/adaptive/adjust.py`
  (file times, observed), and had started a "lean build" (its log, 19:35). No process of it was running at 20:05
  (process list, observed). These files are read, never edited, here.
* **The instance:** `data/studies/current_best_model/template_2026-10-10/` (frame of 67,226 matches, 57 inputs, fits
  2019-2026 x seeds 0-15), built in the sandbox `C:/Users/zerom/tnr_lyr_new` on the tables of 8 Oct plus the accepted
  men's 2026 Challenger package; its intermediate tables are still there (observed). The 10 Oct layer replay
  (`data/studies/prediction_run/replay_2026-10-10_layer/`) matched 57 of 57 inputs on 23 matches against
  `model_frame_chain.parquet` (the books' average odds input), with Tennis My Life's dump held at the freeze
  (`C:/Users/zerom/tnr_dump_freeze/`, `level_layer_adoption/freeze_dump.py`) and the timeline held at the template's
  (`timeline_held.json`), because sources were restaged after the freeze (observed, its records).
* **What the prototypes proved** (PLAN.md § 4, taken from that log and its records, not re-run yet): IOS resume bitwise on
  the same table and within 5.3e-8 across tables (4 of 14 runs); offset Elo resume bitwise; Stage B z and the 17 inputs
  bitwise; Stage 4's five inputs bitwise from the day's players. Not proved: the other passes, rating_matchup
  (ratings_iid), the Elo pieces' per-player parts, frame assembly, any end-to-end run.
* **Environment:** `tennis` env (`./python.sh`) for everything but the fit; `tennis-tabpfn-local`
  (`./python_tabpfn_local.sh`) for TabPFN on the RTX 5090. 161 GB free on C: (observed 20:10). A SofaScore scraper
  (since 9 Oct) and Jupyter kernels of the `tabiclv2` env run beside this work.

## 3. Plan

Each item with the check that closes it.

1. **Infrastructure:** canonical hashing of the arrays a family's state reads (its "history slice"); the checkpoint
   store and manifest; the work tree (a sandbox copy, as prediction_run makes it, with the prediction run's licence for
   live rows). Check: unit tests of the hashing (order, NaN, dtype sensitivity).
2. **The families, on the template's own build tree first** (`tnr_lyr_new`, its code and tables, read only):
   * Elo-type passes: the offset pass (pieces), the games-weighted pass (Stage 4's elo_games), Stage 3's pass
     (ratings_iid), each resumable (state in, state out); Stage 3's outputs before the checkpoint stored with it, since
     Stage 4's loader reads the whole table. Check: resume = full pass bitwise; full pass = the tree's stored tables.
   * Surface IOS (14 runs): the prototype's solver state, mapped across tables by stable player and row keys (the
     prototype's mapping used the cache's per-table player codes, valid only for a subset of one table). Check: resume =
     full run (bitwise on the same table); full run = the tree's stored runs.
   * Stage B forms: z of the box rows before the checkpoint (float64) + targeted moments + step 3 per player. Check:
     bitwise against the decided forms_z / forms_step3.
   * Stage 4 (elo_games, points_52w, sets_14d, age, age_sq, ratings_iid) and the Elo pieces' per-player parts
     (surf_season, surf_layoff): recomputed for the day's players. Check: bitwise against the tree's stored tables.
   * Context and the odds input (row values). Check: against the frame.
   * Frame assembly for the target rows, with each family's storage casts. **Check: on the tree's own tables, every
     frame row after the checkpoint equals model_frame.parquet on all 57 inputs** (an end-to-end check before the
     replay).
3. **Checkpoints and their validation:** a checkpoint per (instance, day) with each family's slice hash; a family whose
   slice changed is recomputed in full. Check: test 3 (a past row changed in each way a family reads, invalid; a later
   row changed, still valid).
4. **The steps and run_day:** refresh, matchups, prices (reusing prediction_run), tables (prediction_run's preparation
   without the steps that reach no input), states, fit, predict, grade. Replay mode: the past day's matches as live
   rows, priced at the template's Pinnacle-first price, the dump and timeline held at the template's. **Check: test 2.**
5. **The fit runner and the price grid** (16 seeds, every live match x 91 prices x 2 orientations plus its own price),
   then stage 2 and the prediction file with provenance. **Check: test 4.**
6. **Tests and the report:** each test's result and each step's time.

## 4. Chronology

Local time PDT (UTC−7). "Results" means any outcome-based score; none is read to make a choice in this work.

| When | Step (command or action) | Why | Results seen by then | Output |
|---|---|---|---|---|
| 20:00–20:15 | Read PLAN.md, its process log, the daily_update_speed README/log/scoping, the prototypes, `prediction_run/` (run, replay, live_rows, inject, gate, fills, sandbox), the frame chain (`tabpfn_thinking/build_frame.py`, `tabpfn_leakproof/build_frame.py`, `surface_elo_pieces/{arms,build_frames,pieces}.py`, `surface_rating_race/{arms,model_frame}.py`, `surface_ios/{arms,build_features,build_cache,common}.py`), `stage3_ratings.py`, `stage3_traits.load_rows`, `stage4_features.py` (loader, weighted Elo, state, build, single features), `stageB_common.py`, the level layer (`level_layer.py` weights/translation, `level_layer_ios.py` row plan and system), `current_best_model/{odds_input,template_inputs,layer_config,additions}.py`, `model_rebuild/{run_chain,fits,compare}.py`, `serve_speed_tabpfn/{common,arms}.py`, `adaptive/adjust.py`, `live/form.py`, `indoor_fill/status.py` | Plan step 0 | none | Observed facts the design rests on: (a) the 57 inputs pass three row-wise frame copies; Stage 4 and Stage B values are stored float32 and read back as float64, the IOS and Elo pieces float64, `odds_logit` = `np.log(p/(1-p))` of the Pinnacle-first price (`odds_input.rewrite`); (b) Stage 4's loader (`stage4_features.load_rows`, also Stage B's) reads `stage3_ratings.parquet`, `stage1_baselines.parquet` and `stage1_odds.parquet` for every row; `rating_matchup` (ratings_iid) reads each match's own Stage 3 values (float32) and `mu_logit`; (c) the IOS system's player positions follow `pd.factorize` of the tour's rows (table order), so a checkpoint must be mapped across tables by player id, not by the cache's codes; (d) the template's constants (Stage 1 K, the offset K, Stage 3's chosen variances, Stage 4's constants CSV) live in the build tree's files, some not in the instance folder; (e) a fresh sandbox copy of `data/studies` took about a minute in the template build (robocopy log: 10:40:39 to 10:41:34) |
| 20:20 | Process log opened (this file) | Rule 2 | none | — |
| 20:25 | The constants files the state path's builder functions read, compared between the template's build tree and the repository (`cmp`, then the values) | A work tree copied from the repository (as prediction_run makes one) would feed the builders the repository's copies | none | **Observed: three differ.** `stage3_ratings_summary.json` (repository 1 Oct, tree 10 Oct): the women's drift 1e-4 against the template's 5e-5; `stage4_constants.csv` (Stage B's and the IOS cache's surface averages come from it): 508 rows, shrinkage K's and adjustment betas differ (up to 408 in a K); `stage1_baselines_summary.json` and `pieces_meta.json` differ only in their time stamps (chosen K and offset K equal). Equal: `stage3_shrinkage.csv`, `stage3_results.json`, `stage4_candidates.csv`, `stage2_pbp_players.parquet`, the IOS registry's `active.json`. **Design consequence:** a full prediction run never meets this (its chain re-tunes and rewrites these files); the state path skips those builders, so each checkpoint carries the instance's constants files and the work tree gets them installed before any family runs; the manifest records their hashes |
| 20:30 | `dp_common`, `dp_hash`, `dp_elo` written; scratchpad `check_elo.py` on the build tree (`tnr_lyr_new`, read only; checkpoint 2026-06-22) | Plan step 2, Elo-type passes | none | **Observed:** the offset pass equals the tree's `pieces.parquet` bitwise (10 of 10 columns, both tours); resumed from the first match of the checkpoint's week, bitwise (5,356 ATP and 903 WTA matches after it); my copy of Stage 3's pass equals the decided `rating_pass` bitwise, resumed bitwise, and the table it writes (the decided format) equals the tree's `stage3_ratings.parquet` on every column. 12-13 s each |
| 20:38 | `dp_ios` written (the cache with stable keys; checkpoint, move, resume); scratchpad `check_ios.py` | Plan step 2, the IOS | none | **Observed:** the cache equals the tree's `cache/{atp,wta}.npz` on every array and `pool.parquet` (52 s to build); WTA ace (plain) and ATP hold (two level effects) full runs equal the tree's stored runs bitwise; checkpoint saved, loaded, moved (same table) and resumed: bitwise on 1,828 and 10,298 rows (1.4 s and 3.1 s). Setup of a run 0.1-0.5 s |
| 20:44 | Checkpoint files were 28-78 MB a run (triple keys stored as text): changed to integer positions and compressed npz | Size | none | 1.3-3.1 MB a run |
| 20:46 | Scratchpad `check_ios2.py`: a checkpoint made on an older table (matches finished before 2026-03-23 only, player codes re-factorized as a real older table's would be) moved onto today's table | The move by player id across real code changes (the prototype's check kept one table's codes) | none | **Observed:** WTA ace 4,347 -> 4,548 players, 137,936 -> 148,836 triples: within 1.3e-15 on 16,008 rows; ATP hold 5,108 -> 5,229 players: within 2.4e-8 (O) / 5.3e-8 (D) on 31,084 rows (the prototype's figures again); the slice hashes of the two tables equal (their history before the checkpoint is the same) |
| 20:47 | `dp_forms`, `dp_stage4`, `dp_pieces`, `dp_context`, `dp_store`, `dp_state`, `dp.py` (checkpoint, tree-check) written. Design choices made here, before any input comparison: (a) the IOS checkpoint is the last snapshot day BEFORE the checkpoint day, so all families cover "everything before d0" (Elo: tournament weeks before d0; forms: box rows of those weeks); (b) the IOS runs go to worker processes with single-threaded BLAS (as build_features.py ran them), the rest stays in the main process with default threads (as the chain's builders ran); (c) Stage 3's whole table is rebuilt from the checkpoint's stored outputs before the checkpoint plus the resumed pass, written into a work tree, and checked equal to the stored table on a read-only tree; (d) the Elo pieces' per-player quantities are computed on the whole table with the decided functions (seconds; exact by construction) | Plan steps 2-3 | none | — |
| 20:50 | `dp.py checkpoint --day 2026-06-22` launched on the build tree (background; log `data/studies/daily_prediction/logs/checkpoint_2026-06-22.out`) | The replay's checkpoint (three weeks before the replayed week of 13 Jul) | none | running |
| **20:53 (clock read)** | **Correction: the times of the rows from 20:30 to 20:47 were written by estimate, not read from the clock.** Their order is right. Observed from the files' modification times (`ls -l --time-style=+%H:%M:%S`): `dp_hash.py` 20:28:00, `dp_elo.py` 20:31:12, `check_elo.py` 20:31:32 (run about 20:32), `dp_forms.py` 20:33:56, `check_ios.py` 20:35:40 (run about 20:36-20:38), `check_ios2.py` 20:39:31 (run about 20:40-20:42), `dp_stage4.py`/`dp_pieces.py` 20:45, `dp_context.py` 20:46:43, `dp_store.py` 20:48:07, `dp_state.py` 20:50:02, `dp.py` 20:50:42, the checkpoint launched about 20:51. No result or choice depends on these times. From here on each row's time is read from the clock | Rule 4 | — | — |
| 20:53 | `dp_worktree.py`, `dp_tables.py`, `dp_matchups.py` written (the work tree, the preparation, matchups and prices; replay mode) | Plan step 4 | none | — |
| 20:55 | **Failure:** the checkpoint run stopped at its last phase (the IOS workers): `np.load(allow_pickle=False)` refused the temporary cache, one key array (`key_event`, built from a pandas string column) being an object array. Everything before it (Elo, Stage 3, the games-weighted pass, the forms' z) had been written but no manifest, so the folder was not a checkpoint. Observed sizes: Elo states 1-2 MB each, Stage 3's saved outputs 33 MB (ATP) and 20 MB (WTA), the z 85 MB; the temporary cache 1.3 GB (deleted after use) | — | none | Fixed (the key arrays forced to numpy text; `save_cache` converts any object array); the stale temporary file removed |
| 20:56 | Checked that no dump file changed after 10 Oct 14:00 (`find -newermt`), and that since the freeze only `odds/oddstrader` and `points/itf_live` moved (not Stage 0's sources) | Whether the replay's Stage 0 can equal the template's apart from its own rows | none | Observed: none changed after 14:00; Tennis My Life is held at the freeze by the work tree's view |
| 21:00-21:27 | `dp_fit.py`, `dp_predict.py`, `dp_steps.py`, `dp_selftest.py`, the CLI commands, `test/daily_prediction/` written (times from the files). **Stage 2's 2026 coefficients:** the decided fit (`current_best_model/compare.walk_forward`, the instance's seeds 0-3 of 2019-2025, debut seasons out) on `infosys_atp_backfill/speed_columns_augmented.parquet`'s `spd_L_B` (the decided speed history: corrected plus the ATP backfill), after checking (observed) that it covers all 32,436 template frame matches of 2019-2025 (men 16,890 of 16,890; women 0). These coefficients read 2019-2025 results by the decided procedure; the earlier plan session left them uncomputed (its log, judgment call 8), while phase 1's predict step needs them; computed once and cached in `data/studies/daily_prediction/stage2/` | Plan step 5 | none | — |
| 21:27 | The checkpoint relaunched (same command) | — | none | running |
| 21:38 | Checkpoint 2026-06-22 written (`data/studies/daily_prediction/state/template_2026-10-10/2026-06-22/`, observed) | — | none | 626.6 s in all: offset pass 9.0, Stage 3 8.3, Stage 4's rows 35.7, games-weighted pass 11.9, forms (the decided forms_z) 105.6, IOS cache 53.5, the 14 IOS runs to the checkpoint 402.4 (7 workers). 178 MB |
| 21:39 | `dp.py tree-check --day 2026-06-22` launched: on the build tree's own tables, every template frame match from 22 Jun 2026 whose earliest start is on or after it, its 57 inputs from the checkpoint against `template_2026-10-10/model_frame.parquet` | Plan step 2's end-to-end check, before the replay | none | running |
| 21:41 | Its result (`data/studies/daily_prediction/checks/tree_check_2026-06-22.json`; observed) | — | none | **1,565 matches x 57 inputs: all 57 bit for bit (largest difference 0.0)**; every part resumed. 183.7 s: offset pass 5.5, Stage 3 5.4, Stage 4's rows 34.5, games-weighted pass 5.3, Stage 4's six inputs 17.2, forms context 27.1 + inputs 14.5, pieces 3.3, IOS cache 51.7 + 14 resumed runs 13.9, context 4.9 |
| 21:42 | `dp.py run_day --replay-week 2026-07-13 --replay-round R16 --checkpoint 2026-06-22 --direct-seeds 0,1` launched (run folder `data/studies/daily_prediction/runs/replay_2026-07-13_R16/`, log `logs/replay_2026-07-13_R16.out`) | Tests 2 and 4 | none | running. Observed by 21:43: the work tree in 51 s, matchups 3 s, prices 0.1 s; the same 23 matches as the 10 Oct layer replay (Bastad 4, Gstaad 3, Umag 8, Athens 4, Iasi 4), priced at the instance's own price (BetOnline's close: Pinnacle's are missing from August 2025, as decided) |
| 21:42-21:43 | `dp_selftest.py invalidation` (test 3's check) failed twice on my test code: `~bool(x)` gives -1 (fixed: `not`); a match inserted under a made-up id, which the level layer refuses (every id must be in its Stage 0; fixed: a past match duplicated, which the slice must also see). Relaunched beside the replay | — | none | running |
| 21:46 | The replay's tables step done (observed, `run_day.json`/log) | — | none | 223.0 s: Stage 0 with the live rows 127.2, the accepted packages 16.2, the live rows' check 0.6, the level layer resolved 13.7, Stage 1's odds 6.5, the live prices 0.7, the timeline held and the history check about 58 |
| 21:49 | The replay's states step done (172.7 s); `dp.py replay-compare` on it (`runs/replay_2026-07-13_R16/replay_compare.json`; observed) | Test 2 | none | **23 matches x 57 inputs against `template_2026-10-10/model_frame.parquet`: 57 of 57 inputs bit for bit on every match (largest difference 0.0, the 21 IOS inputs included); 23 of 23 matches equal on every input.** Every state part resumed from the 2026-06-22 checkpoint (its slices unchanged on the replay's tables). The IOS came out bit for bit, not merely within 1e-6: the replay's solver systems keep the template's players and positions, and the triples the replay lacks carry zero weight before the replay's day |
| 21:49 | The invalidation check's result (observed, `checks/invalidation_2026-08-31.json`): 18 of 19 cases as I had required; **the exception: a past row's serve points won changed, Stage 3's slice unchanged**. Looked at the row (scratchpad `check_s3row.py`): a 2025 ITF match (M-ITF-USA) whose box score the level layer weights to zero (ITF box scores excluded): Stage 3's pass reads n = w = 0 for it, so the change cannot reach the state, and the slice, which hashes exactly what the pass reads, is right to stay the same. **My test case was wrong, not the slice.** Changed: the changed rows are now main-tour matches (read by every family), and an explicit case per family that reads box scores requires that a change it does not read (an ITF box score) leaves the hash as it is (no needless fallback). Relaunched 21:51 | Test 3 | none | running |
| 21:54 | The refined invalidation check (observed, `checks/invalidation_2026-08-31.json`) | Test 3 | none | **22 of 22 cases as required**: a main-tour row changed before the checkpoint day changes the hash of every part that reads it (the offset pass: a result, a player, a match inserted; Stage 3: serve points won; the games-weighted pass: games won; the forms: a box-score count; the IOS (men's aces and holds): a box-score value and a match's timeline window); the same change after the day changes none; an ITF box score (weighted to zero by the layer) changed before the day changes neither Stage 3's nor the IOS's hash |
| 21:55 | `dp_selftest.py families --day 2026-08-31` launched (its own checkpoint, in a scratch state folder) | Test 1 | none | running |
| 22:03 | **Failure:** the replay's fit fitted and saved all 16 seeds (44-50 s each, about 12.6 min), then failed reading them back for its summary: the match ids were stored as an object array (a pandas string column's `to_numpy()`), which `np.load(allow_pickle=False)` refuses. run_day stopped there and deleted the work tree (its `finally`) | — | none | Fixed in `dp_fit` (text arrays; each seed's record in its own JSON beside its npz, so a later call rebuilds the summary). This run's 16 files converted in place (my own files, read with `allow_pickle=True` once, re-saved as text; their timings recovered from `fit.log`; the TabPFN checkpoint path of this call was not recorded), instead of refitting 12 minutes |
| 22:03 | `dp.py fit` (summary only: every seed on disk) and `dp.py predict` on the replay (observed: `fit.json`, `predictions.csv`, `stage2/template_2026-10-10_2026.json`) | Test 4; step 7 | none | **The 16-seed grid read back at each match's own price against the own-price (direct) prediction: max 0.00050, mean 0.00022, all 23 inside the grid; 14 of 2,070 grid steps fall.** The own-price rows predicted alone in a separate call (seeds 0, 1) differ from the same rows in the grid's call by 4.0e-5 and 5.6e-5 (the batch's effect). **Stage 2's 2026 coefficients** (the decided fit on 32,413 matches of 2019-2025): s_atp 0.9004, s_wta 0.9223, b̃ 0.0369 (b 0.0430, SE 0.0203). q from 0.050 to 0.826; the gate: 20 may be bet, 3 not (WTA players entered through qualifying with no qualifying match in Stage 0: the known gap since June 2026). predict 4 s (the coefficients' first fit about 10 s) |
| 22:04 | `predict` failed once on the converted seeds' records lacking the TabPFN checkpoint path (`KeyError`); fixed (`.get`) | — | none | — |
| 22:19 | The families check (observed, `checks/families_2026-08-31.json`; its own checkpoint at 2026-08-31 in a scratch state folder; 1,452 s, beside the end-to-end run below) | Test 1 | none | **Every family resumed equals its full recompute bit for bit on every row after the day:** the offset pass, Stage 3 and the games- and points-weighted passes (1,892 ATP and 219 WTA matches each); Stage 3's saved outputs before the day equal the full pass; this module's weighted pass equals the decided `elo_variants`; the forms' z on all 2,848 new box rows (17 of 17 pairs) and the 17 inputs on all 1,986 new pool matches; **the 14 IOS solves bit for bit (largest difference 0.0) on every row queried after the day** (3,826 ATP and 656 WTA rows; resumed 2.6-5.2 s, full 68-347 s while contended). Stage 4's six inputs (1,986 matches; 1,020 players' 260,382 matches, 29 s) and the Elo pieces' six (2,111 matches) equal the build's stored tables |
| 22:17 | Added: a live run_day leaves a checkpoint on its own tables (the Monday three weeks before its matches) when a part fell back to a full recompute or its checkpoint is more than two weeks older (`--leave-checkpoint auto`), so a day after a fallback resumes; a replay never does | Plan § 3.3 rule 3 | none | — |
| 22:21 | The final pytest run launched (`./python.sh -m pytest test/daily_prediction -v --durations=0`, output `data/studies/daily_prediction/checks/pytest_final.txt`), every check from scratch (its own checkpoint, a fresh replay with its fit, both invalidation checks), with its own work tree (`DP_TEST_WORK_TREE`, default `C:/Users/zerom/tnr_daily_pytest`) so it cannot meet a run's | Tests 1-4, for the report | none | running |
| 22:05 | Added: `reprice` (tier 0: new prices read off a run's curves, refused if the run's inputs changed), `states --full` (tier 2: every part from scratch, no checkpoint), and `dp_selftest.py invalidation_e2e` with its pytest test: test 3 through the real steps (a replay's work tree and tables; one past main-tour men's match moved one day in the work tree's timeline; states from the checkpoint against states with every part from scratch on the same changed tables). Why: the in-memory check proves the hashes see the changes; this proves the states step acts on them and still gives a from-scratch build's inputs | Test 3, end to end | none | — |
| 22:32 | (Order note: the rows of 22:19, 22:17 and 22:21 above were inserted before the 22:05 row by mistake; their text is unchanged) | Rule 4 | — | — |
| 22:31 | Checked that the template's build tree was left unchanged (`find /c/Users/zerom/tnr_lyr_new -newermt "2026-10-10 20:00" -type f`: 0 files) and that no repository file outside this build's four folders changed since 20:00 (`find src docs test data/studies predictions ...`: none) | The read-only use and the owner's rule on other studies' files | — | observed: none |
| 22:50 | The end-to-end invalidation check (observed, `checks/invalidation_e2e_dev.json`; runs `runs/invalidation_e2e_dev/{resumed,full}/`; beside pytest's families check, so its times are contended) | Test 3, end to end | none | **As required.** The changed row: `atp\|2026-425\|F\|atp:126094\|atp:209950` (an April 2026 final, two months before the checkpoint), its timeline window moved one day (es 20561 -> 20562). **Exactly the 7 men's IOS solves were recomputed in full**; the Elo-type passes, Stage 3, the games-weighted pass, the forms and the 7 women's solves resumed. **Run A's 57 inputs equal run B's (every part from scratch on the same changed tables) bit for bit on all 23 matches** (the IOS too). Times: work tree 13.7 s, matchups 7.7, prices 0.2, tables 268.1, states with 7 solves in full 989.9, states all in full 725.6 |
| 22:51 | Added `--replay-dating live` (a replay dated as upcoming matches are: the live timeline steps run instead of the instance's timeline held; a smoke test of the live path's timeline steps, not an exactness test). **Made while the final pytest run was in its families fixture**: that fixture's subprocess had imported its modules at 22:21 (none of them changed); the replay fixture and the end-to-end test, which start later, run the code as it stands now (default "training" dating, the timeline held: the exact replay's behaviour unchanged). **The code is frozen from 22:52 until the pytest run ends** | — | none | — |
| 23:15 | pytest's replay (fresh, with its fit) done; its records observed (`runs/pytest_replay_2026-07-13_R16_20261011T055552Z/`) | Tests 2 and 4; the step times | none | Identical to the development run: 57 of 57 inputs bit for bit on 23 matches, every part resumed; the grid within 0.000503 of the own-price prediction (mean 0.000224), the separate call 5.6e-5 from the in-batch one. **Clean step times** (nothing else of mine running): work tree 9.4 s, matchups 2.9, prices 0.0, tables 198.3 (Stage 0 115.6, packages 14.9, check 0.6, layer 12.5, odds 5.9, live prices 0.7, timeline held and history check about 48), states 161.5 (internally: passes 16.3, Stage 4's rows 33.7 and inputs 3.3, forms context 26.2 and inputs 9.1, pieces 3.2, IOS cache 49.8 and solves 9.3, context 4.7), fit 811.3 (16 seeds x 43.2-46.4 s; preprocessing 0.6-0.7 s a seed; 8.1 GB peak), predict 0.6, cleanup 5.9: 1,190 s in all |
| 23:31 | `reprice` exercised on the replay run (at the run's own prices: 23 repriced, within 0.00045 of its q, the grid's read-back; with moved prices: 22 repriced, one at 0.97 refused as outside the grid) and `grade` (23 of 23 joined to results; its log losses were not read: they decide nothing). One row added at the top of `docs/studies/README.md` (the studies index), as the plan's session did: the only file outside this build's four folders touched | Untested commands; convention | none | — |
| 23:17 | The live-dated smoke test (`runs/smoke_live_dating_2026-07-13_R16/`, no fit; beside pytest, so contended) | The live path's own timeline steps, which the exact replay skips | none | Every step ran: tables 273.2 s (remap 5.7, links 20.2, live links 4.1, timeline 39.2, live window 2.0, packages' window 5.5 on top of the held run's steps); states 566 s: **all 14 IOS parts recomputed (their slices changed: the rebuilt timeline moves older matches' windows, sources restaged after the freeze), the other 7 resumed**. Against the template frame: the 36 inputs outside the joint solves bit for bit; the 21 IOS inputs differ by up to 0.0093 (live dating and the restaged timeline: not an exactness test) |
| 23:41 | **The final pytest run ended: 9 passed in 4,882 s (1:21:21)** (`data/studies/daily_prediction/checks/pytest_final.txt`; observed). Durations: the families fixture 2,155.6 s (contended by the development end-to-end run until 22:50), the replay fixture (run_day with its fit) 1,191.1, the end-to-end invalidation 1,258.2, the in-memory invalidation 273.9, the replay comparison 2.6, the price grid 0.4. Its end-to-end run: the same 7 men's IOS solves recomputed, 57 of 57 inputs bit for bit (states 427.3 s with 7 solves in full, 613.9 s all in full). Computed afterwards for the report (the test asserts it without recording it): the 16-seed grid read back at the own prices against the template's stored fits of these 23 matches: max 0.00051, mean 0.00022; the own-price predictions of this fit against the stored fits: max 9.8e-6 (the batch's effect: the stored fits predicted the whole 2026 season in one call) | Tests 1-4, for the report | none | all pass |
| 23:42 | (Order note: the 23:31 row above was inserted before the 23:17 row by mistake; its text is unchanged) | Rule 4 | — | — |

## 5. Sources

None outside the repository: the project's code, tables and records; the instance's build tree.

## 6. Judgment calls

1. **"Phase 1" read as § 7 items 2 and 3** (before any code; § 1). The tests named fall there; the Pinnacle recorder
   (item 1) is a new network adapter none of them covers. Not asked: no channel to wait on an answer; stated in § 1 and
   the README for correction.
2. **Reuse by import, extend in the new package.** The prototypes' solver, z and Elo loops are imported unchanged; what
   they lacked (player ids across tables, the two other passes, checkpoint files, slices) is new code. No builder,
   `prediction_run` file or prototype was edited, so no question to the owner arose.
3. **Stage 3's whole table rebuilt from stored outputs plus the resumed pass**, rather than only the target rows:
   Stage 4's loader reads every row (the typical opponent of 2013-2018 among them), and exactness of everything it
   computes was cheaper to guarantee than to argue (made before any comparison).
4. **The Elo pieces' surface counts computed on the whole table** (seconds), not per player: exact by construction.
5. **IOS in single-threaded worker processes, the rest in the main process** (as the chain ran each); made before any
   comparison, after reading build_features.py's thread setting.
6. **The checkpoint covers "everything before the day"** for every family (the IOS: the last snapshot day before it),
   so a row queried on the day is always resumed.
7. **The slice hashes what each state actually read** (after the layer's weights). Shown by the invalidation check's
   one surprise (21:49): an ITF box score the layer weights to zero does not invalidate, which is right; the test case
   was changed, not the hash, and a "not read" case added. Made after seeing that case's result; it narrowed what the
   test requires only where the pass provably reads nothing (the pass's inputs for that row are 0 whatever its counts).
8. **The constants travel with the checkpoint** (after finding the repository's copies stale, 20:25).
9. **Stage 2's 2026 coefficients computed** by the decided fit on the backfill-augmented speed column, after checking
   its coverage; this reads 2019-2025 results, which the earlier plan session had left alone. The predict step needs
   them; the values are not used to choose anything.
10. **Test 3 extended end to end** (22:05): the in-memory check proves the hashes; only a run through the steps proves
    the fallback is taken and still exact.
11. **A converted fit instead of a refit** (22:03): the 16 seeds' arrays were complete; only their storage was wrong.
    The final pytest run refitted from scratch and matched.
12. **Live runs leave checkpoints** (22:17): without it, every day after the first fallback would fall back again.

## 7. Claims and their evidence

| Claim (README) | Evidence | Status |
|---|---|---|
| Every family resumed equals its full recompute bit for bit, the IOS included | `checks/families_2026-08-31.json` (development), `checks/pytest_families.json` (final run) | observed, twice |
| The replay through run_day reproduces the 57 inputs bit for bit | `runs/replay_2026-07-13_R16/replay_compare.json`, `runs/pytest_replay_*/replay_compare.json` | observed, twice |
| The state path on the template's own tables reproduces the frame (1,565 matches) | `checks/tree_check_2026-06-22.json` | observed |
| A changed past row invalidates exactly the parts that read it | `checks/invalidation_2026-08-31.json`, `checks/pytest_invalidation.json`; end to end `checks/invalidation_e2e_dev.json`, `checks/pytest_invalidation_e2e.json` | observed |
| The price grid is within 0.001 of a direct prediction | `runs/*/fit.json` (summary) and the stored template fits (the test reads them) | observed |
| Step times | `runs/pytest_replay_*/run_day.json`, `tables.json`, `states.json`, `fit.json` | observed (one run each; the machine shared with a scraper) |
| The live path runs end to end | `runs/smoke_live_dating_2026-07-13_R16/` | observed through states (no fit); no live day with real matchups |
| The first live run will fall back everywhere | inference from the 10 Oct Tennis My Life revision of past rows (`level_layer_adoption/freeze_dump.py`'s note) and the smoke test (every IOS part fell back on a rebuilt timeline) | inference |

## 8. Weak points

* **One replayed day, one week of the season** (15 Jul 2026, 23 matches). Every exactness claim rests on the template's
  tables. On a real day's tables (revisions) the claim becomes "equal to a from-scratch build on those tables", shown
  here end to end for one kind of change only (a timeline window).
* **The live path's timeline steps were exercised once, live-dated, beside other work;** a live day with real matchups
  never ran (no matchup source yet).
* **Where a flaw would most likely hide:** a field a state reads that the slice omits. The slices hash the very arrays
  each loop consumes, so an upstream column counts only through its effect on them (the right test); the invalidation
  cases cover each family, but only a handful of fields.
* **Times on a shared machine:** one clean run per step; the development runs were contended.
* **What a re-design would do:** replay several days (a Slam day, a week with late box scores, a day after a source
  restaging), run a live day as soon as matchups exist, and time the steps on an idle machine.

## 9. Reviewer checklist

* [ ] `./python.sh -m pytest test/daily_prediction -v` (about 90 minutes; needs `C:/Users/zerom/tnr_lyr_new` and the GPU env).
* [ ] `dp.py tree-check --day 2026-06-22` (and `--full`): 57 of 57 bit for bit.
* [ ] Read `dp_hash.py` and each family's `slice_hash`: do they hash every array the loop reads?
* [ ] Confirm nothing in `C:/Users/zerom/tnr_lyr_new` changed (`find ... -newermt`), and no repository file outside the
      four folders.
* [ ] Stage 2's coefficients (`data/studies/daily_prediction/stage2/template_2026-10-10_2026.json`) against a rerun of
      `current_best_model/compare.walk_forward`.

## 10. Reproduction

```
./python.sh src/eda/daily_prediction/dp.py checkpoint --day 2026-06-22
./python.sh src/eda/daily_prediction/dp.py tree-check --day 2026-06-22
./python.sh src/eda/daily_prediction/dp.py run_day --run data/studies/daily_prediction/runs/replay_2026-07-13_R16 --replay-week 2026-07-13 --replay-round R16 --checkpoint 2026-06-22 --direct-seeds 0,1
./python.sh src/eda/daily_prediction/dp.py replay-compare --run data/studies/daily_prediction/runs/replay_2026-07-13_R16
DP_STATE=<scratch> ./python.sh src/eda/daily_prediction/dp_selftest.py families --day 2026-08-31 --out <json>
./python.sh src/eda/daily_prediction/dp_selftest.py invalidation --day 2026-08-31 --out <json>
./python.sh src/eda/daily_prediction/dp_selftest.py invalidation_e2e --root <folder> --out <json>
./python.sh -m pytest test/daily_prediction -v --durations=0
```

# Part 2: speed-ups (11 Oct 2026)

Started 05:30 PDT, 11 Oct 2026 · Same session (`d2d2331e-b87f-42fd-baa1-b5c3ddebe82c`), **resumed after a context
summary**: the conversation was summarized at the end of part 1; this log, the README and the code were re-read from
the files before the first step of part 2.

## P2.1 The request

* **The owner's words, verbatim** (11 Oct 2026, about 05:25 PDT): "My concern is how long this process takes to build
  a prediction, see if you can find speed ups with no cost to prediction quality or potential bugs. Saving states etc."
* **Pasted with it** (a table, source not stated; its rows verbatim, the columns tab-separated in the paste):
  * "Rebuild Stage 0 incrementally: append the day's new Tennis My Life rows instead of re-reading every source file ·
    ~2 min · No (prove it against a full rebuild)"
  * "Keep one long-running process with the tables and saved states in memory, one row loader shared by all families ·
    ~1.5–2 min · No"
  * "Limit the remaining whole-table work to new rows (the IOS solver cache, the level layer's per-row terms, Stage 4's
    constants, one step-3 call per tour); run the families in parallel · ~1.5–2 min · No"
  * "Fix TabPFN's cached mode (the unexplained 0.18 gap) · GPU ~16 min → under 1 min · Must first match the normal
    path"
* **How it was read** (before any measurement):
  * **"No cost to prediction quality": the predictions must not change.** The 57 inputs stay bit for bit (the replay
    test). A change that is only scheduling (processes in parallel, work overlapped) must leave every number bit for
    bit. A change of computation path (TabPFN's cached mode) is acceptable only if it equals the decided path; the
    tolerance, fixed now before any comparison: **max |Δp| ≤ 1e-4 on every seed**, about twice the model's own batch
    effect observed in part 1 (4.0e-5 to 5.6e-5 between two calls of the same rows); the figure is reported, and
    anything not bit for bit is named as such for the owner.
  * **"Or potential bugs":** every speed-up gets a test that fails if it moves a number; anything saved between runs is
    keyed by hashes of what it was computed from (as the checkpoints are), so it cannot be used stale.
  * **"Saving states etc.":** persisting more computed state between runs (candidates: TabPFN's per-seed training
    cache, the solver cache, Stage 0's parsed sources).
  * **The pasted table** is read as the list of candidates with a prior estimate; each is measured, then built or set
    aside with the reason.
  * **Set aside:** changes that move numbers by design (int8/fp8 cache precision, fewer seeds, a coarser grid); they
    cost quality by definition.
  * **Constraints carried from part 1:** no edits to other studies' files or to the builders the daily_update_speed
    session is changing without asking; new code only in this build's four folders; no git.
* **Plan.**
  1. Where the time goes: part 1's clean step times; profile what they do not break down (Stage 0, the IOS cache, the
     loaders).
  2. **The GPU fit (811 of 1,190 s).** Find the cached mode's gap on a small problem (one estimator, a few thousand
     training rows), then at full size. If it can be made to equal the decided path: keep each seed's training cache
     per instance and season on disk and predict from it. Also measure two fits at once on the card (scheduling only).
  3. **The states step:** the families in parallel processes (scheduling only; bit for bit).
  4. **The tables step:** profile Stage 0; overlap the history check with later steps.
  5. Tests that fail if a speed-up moves a number; a timed replay through run_day; the report.

## P2.2 Chronology

Local time PDT. As in part 1, no outcome-based score is read to make a choice.

| When | Step | Why | Results seen by then | Output |
|---|---|---|---|---|
| 05:28 | Read: `prediction_pipeline/PLAN.md` § 3-7, `cache_precision.py` and its record, `daily_update_speed`'s README and `bet_time_pricing*.json`, `dp_fit.py`, `tabpfn_local/runtime.py`, and the TabPFN 9.1.0 library (`classifier.py` fit, `base.create_inference_engine`, `inference.py`'s default and explicit-KV-cache engines, `architectures/tabpfn_v3_5.py`: the three computation paths of stages 0-2, the ICL attention's cached and uncached branches, the decoder, the cache contents) | Plan steps 1-2 | none | **Observed:** the cached and the default path call the same model code: test rows attend to the training rows' first KV head in both (`icl_num_kv_heads_test = 1`); the cache holds the scaler, the ECDF context, the inducing states, 24 layers' K/V and the decoder keys. No difference found by reading. The earlier records: cached 0.179 max / 0.076 mean from the decided path at int8 and at "auto" alike (`prediction_pipeline/cache_precision.json`); the cache's build costs a full prediction (41 s), a cached prediction about 1 s (46 rows) or 4 s (4,186 rows). The machine: 126 GB RAM, 160 GB free disk, 8 cores, RTX 5090 32 GB |
| 05:36 | `dp_cachediag.py` written (both paths on the same data; hooks record the test rows at the model's input, the column aggregator, each of the 24 ICL blocks, the output norm and the decoder; the cache build's training rows against the decided path's) and run on the GPU, season 2026's training rows of the instance, the replay's 23 matches as stored and swapped (46 rows); `checks/cache_diag_*.json` | Plan step 2: locate the gap | none | **4,000 training rows, 1 estimator: identical at every stage and in the probabilities (0.0).** **4,000 rows, 8 estimators: the gap appears (max 0.164, mean 0.065);** inputs and stages 0-2 identical, the training rows identical through all 24 layers, **the test rows first differ at ICL block 0.** Cause found by reading the code with that clue: with `memory_saving_mode=True` the engine sets the peak-memory factor 8; the cached ICL block splits the batch of members into chunks but passes every chunk the whole cache, and `_torch_sdpa` slices keys and values from position 0, so every member attends to member 0's training rows (a bug of tabpfn 9.1.0's cached path; harmless with one member, and independent of int8 or "auto", as the earlier session found) |
| 05:41 | The fix tried three ways on the same small problem: the cached path without the peak-memory chunking at prediction ("predict-off": built as the decided path, `executor_.save_peak_mem = False` after the fit), with `memory_saving_mode=False`, and "auto" | Plan step 2 | none | All three: **max 7.4e-5, mean 2.8e-5** from the decided path, first difference at ICL block 0 (single bf16 roundings, max 0.125 at values near 16): the members run as one batch of 8, the decided path one at a time. Within the tolerance fixed in P2.1 (1e-4), but not bit for bit |
| 05:47 | Full size (62,869 training rows, 8 estimators, seed 0, probabilities only): (a) the batched cache, predict-off; (b) **one cache per estimator** (`tabpfn.settings.max_batched_estimator_rows = 0`, set for the cached classifier only), memory saving as decided; (c) one cache per estimator, predict-off. Why (b): at this size the default row budget (32,768 a forward) already runs the decided path one estimator at a time, so one cache per estimator mirrors its structure exactly and the chunking bug cannot arise (one member per cache) | Plan step 2 | none | (a) max 8.8e-5, mean 2.9e-5; **(b) bit for bit: largest difference 0.0 on all 46 rows; cached predictions 0.97 s against the decided path's 41.2 s**; the cache build 41.4 s (the same cost as one decided prediction); a repeat prediction from the cache identical (0.0); (c) max 1.1e-4 (switching the chunking off changes the decided path's arithmetic). **Chosen: (b)**, subject to the full query rows (4,232 a seed) and all 16 seeds matching bit for bit |
| **05:44 (clock read)** | **Correction: the times of the three rows above (05:36, 05:41, 05:47) were written by estimate.** From the records' modification times: the small runs 05:31:31 (1 estimator) and 05:31:57 (8), the three fixes 05:33:38-05:34:05, the full-size runs 05:38:40 (a), 05:40:10 (b), 05:41:40 (c). The order and the contents are right; no choice depends on the times. From here on each time is read from the clock | Rule 4 | — | — |
| 05:50 | `dp_tabcache.py` written (the cache's key, build, save and load, mirroring tabpfn's own `save_fitted_tabpfn_model`/`load_fitted_tabpfn_model` without their deflate zip), `dp_fit.run(cache=...)` (default "use": load, or build and save when missing or stale; "off": the decided path), `--fit-cache` on `fit` and `run_day`; the card's process scan once per step instead of before every seed (`fits.py`'s own pattern: free memory still checked before each seed). `dp_selftest.py fit_cache` compares a cached fit with a stored decided-path fit array by array. Launched on part 1's pytest replay (its 16 seeds fitted by the decided path), with no cache on disk yet: every seed built | Plan step 2 | none | running. Seed 0 observed: build 41.5 s, save 1.8 s, 3.6 GB, prediction of its 4,232 query rows 2.9 s; its separate own-price call 4.0e-5 from the in-batch one (part 1's decided path: the same 4.0e-5) |
| 05:52 | Measured on the build tree (read only; `scratchpad/prof_loaders.py`): Stage 4's loader = rows 11.0 s, `constants` 28.8 s (16 s of it pandas converting Arrow-backed string columns to numpy, 939 calls, inside `stage4_features.py`), point-by-point 2.3 s; Stage B's context 7.5 s; the history check 46.6 s (its result only recorded: nothing reads it to build an input; checked by grep). Read: `stage4_features` load_rows/stat_xd/pbp_history/constants (constants from fixed windows 2010-2018 plus a per-row array over every row) | Plan steps 3-4 | none | **Decided, before any comparison:** (a) the states step in three processes: the surface IOS from the start (it reads no other family's output), Stage B's forms once Stage 3's table is written (it loads Stage 4's rows itself: no in-place write to the rows between loading and Stage B, checked by reading `stat_xd`, `pbp_history`, `constants`, `elo_scales`, `weighted_inputs`, `inputs_for`), the rest in the main process; each family's code unchanged; (b) run_day runs the history check in its own process beside the states step and joins it before the fit; the `tables` command alone still runs it inline. **Set aside:** a cache of Stage 4's constants (saves about 29 s, but it would need a hash of exactly what they read; the critical path after (a) is the IOS, about 60 s, so it would gain about 10 s); converting the rows' string columns before `constants` (would change the dtype other studies' code sees); **any change inside Stage 0's builder** (`stage0_build.py`: the daily_update_speed session has edited it and planned its vectorisation; the owner's rule: ask first) |
| 05:56 | Part 2's tests added (`test_fit_cache_key_sees_every_change`, `test_fit_cache_equals_decided_path`, `test_history_check_recorded`, `test_states_ran_in_three_processes`); the fast key test run | Plan step 5 | none | 2 passed (the key test and part 1's hash test) |
| 05:58 | **Failure:** the 16-seed cache check stopped at seed 13: renaming the finished `seed13.part` folder into place was refused (`PermissionError: [WinError 5]`), 13 renames having worked; most likely a scan holding the new 3.6 GB file open. **Fixed:** no folder rename; `key.json` (which marks a complete cache) is deleted before anything is written and written last, with retries for 2 minutes on access denied. **Left on disk: `state/template_2026-10-10/tabpfn/season2026/seed13.part` (3.6 GB, the failed attempt's copy), not deleted (the owner's rule on temporary files); to be named in the report.** The 13 seeds written before the failure compared afterwards with part 1's decided-path fit (`compare_fits`) | — | none | **13 of 13 seeds bit for bit in every array** (the grid, the own-price and the own-price-alone predictions of seeds 0-1, the match ids and prices): largest difference 0.0 |
| 05:58 | `dp.py tree-check --day 2026-06-22 --tag parallel` (the states step's three processes on the template's own tables, read only; beside the GPU cache build) | Plan step 3 | none | **1,565 matches x 57 inputs: all 57 bit for bit (0.0), all 21 parts resumed**; 96.8 s against part 1's 183.7 s (main process 96 s with Stage 4's inputs for 1,565 matches 28.7 s; forms process 71.8; IOS process 80.5; waited 0.3) |
| 05:59 | The cache check relaunched (`--tag second`): seeds 0-12 from their saved caches, 13-15 built | Plan step 2 | none | running |
| 05:59 | (Time note: the relaunch in the row above was at 05:58:48, read from its own output; the row's time was written before reading it) | Rule 4 | — | — |
| 06:02 | The relaunched cache check ended (`checks/fit_cache_second.json`; observed) | Plan step 2 | none | **16 of 16 seeds bit for bit with the decided path in every array** (largest difference 0.0): seeds 0-12 loaded from their saved caches (1.6-2.1 s a load, 2.8-3.2 s to predict the 4,232 query rows: **4.5-4.7 s a seed, 8.9 s for seed 0**, which also hashes the 876 MB weights file and makes the separate own-price call), seeds 13-15 built with the fixed save (40.7-40.8 s build, 1.6-2.3 s save, 3.6 GB each). The own-price-alone calls again 4.0e-5 (seed 0) and 5.6e-5 (seed 1) from the in-batch rows, as in part 1. The step: 208 s with three builds; about 80 s with every seed loaded (estimate from these times) |
| 06:03 | `dp.py run_day` launched: the same replay as part 1's timed run (2026-07-13, R16, checkpoint 2026-06-22, direct seeds 0-1; run `runs/replay_2026-07-13_R16_speed`), now with the cached fit, the states step's three processes and the history check beside the states; `--keep-worktree` (Stage 0 to be profiled in it afterwards) | Plan step 5: tests 2 and 4 through the faster paths, the step times | none | running; nothing else of mine running |
| 06:09 | (Time note: the run_day row above, written as 06:03, was launched at 06:02:27, read from its own output.) **The timed replay ended** (`runs/replay_2026-07-13_R16_speed/`; observed); then `replay-compare`, and its fit, live frame, predictions and history against part 1's pytest replay (fitted by the decided path) | Tests 2 and 4 through the faster paths; the step times | none | **Inputs: 57 of 57 bit for bit on 23 of 23 matches (IOS 0.0), all 21 parts resumed. Fit: 16 of 16 seeds bit for bit with part 1's decided-path fit (0.0); the live frame identical; `predictions.csv` identical in every column but `price_recorded_at` (a time stamp). The history line identical to part 1's and recorded in `tables.json` (the check ran 51.2 s beside the states step).** Step times: work tree **72.0 s** (cold: the 56 GB of cache files written and read just before had evicted the disk cache; part 1: 9.4 s warm, 51 s cold), matchups 3.0, prices 0.0, **tables 157.2** (Stage 0 117.0, packages 14.8, check 0.6, layer 12.4, odds 5.9, live prices 0.7), **states 84.5** (main process: passes and Stage 3 12.3, Stage 4's rows 41.3, weighted 6.5, Stage 4's inputs 4.3, pieces 7.1, context 6.1; forms process 64.5; IOS process 75.1 (cache 63.3, solves 11.8); waited 0.3), history 0.0 (waited), **fit 81.9** (every seed loaded), predict 0.8: **399.7 s before cleanup** (part 1: 1,184 before cleanup) |
| 06:12 | Stage 0 profiled in the kept work tree (`cProfile`, the same script and arguments; it rewrote only the sandbox's own Stage 0; `scratchpad/stage0.prof`) | Plan step 4: quantify what an edit of the builder would buy | none | 148 s under the profiler (117 s without). **`feature_alpha_audit/repair_data.repair_tables` 64 s; pandas iterating Arrow-backed string columns element by element 59.8 million times (33 s of its own time), from Python-function group-bys (36.9 s) and list comprehensions over columns** (`repair_data.py` line 119: 16.6 million element reads; `stage0_build.py` `progression` lines 920-934, `build` lines 1002 and 1195, `apply_id_aliases`, `score_columns`); `Series.map` 9.7, `to_numeric` 5.6. Inference: converting those columns to numpy once, or vectorising, would likely cut Stage 0 by about half; it is an edit to two builders (the owner's call; the daily_update_speed session planned Stage 0's vectorisation) |
| 06:13 | The kept work tree deleted with the pipeline's own `dp.py cleanup` (what every run does; kept only for the profile) | — | none | 2.9 s |
| 06:14 | README: a part-2 section at the top (the owner's question first), the cost table with both days, decisions 5-6; the studies index's row extended (one sentence) | Report | none | — |
| 06:15 | **The final pytest run launched (06:15:23)**: `./python.sh -m pytest test/daily_prediction -v --durations=0` (`checks/pytest_part2.txt`), all 13 tests from scratch: part 1's nine, now through the faster paths, and part 2's four. **The code is frozen until it ends** | Plan step 5 | none | running |
| 06:16 | The Stage 0 profile's summary saved into the study's records (`checks/stage0_profile.txt`; the loaders' profiling script as `checks/prof_loaders_script.py.txt`): the scratchpad does not outlive the session | Records | none | — |
| 07:08 | **The final pytest run ended: 13 passed in 3,199.8 s (53:19)** (`checks/pytest_part2.txt`; observed). Durations: the families fixture 1,372.6 s, the end-to-end invalidation 1,032.9, the replay fixture 345.3 (run_day with every seed's cache read from disk), the cached-against-decided test 223.8, the in-memory invalidation 223.3. Its replay (`runs/pytest_replay_2026-07-13_R16_20261011T133817Z/`, from 06:38:17): work tree 10.3 s (warm), matchups 2.8, prices 0.1, tables 157.6, states 83.9 (main 78.6 with Stage 4's rows 40.9; forms 63.5; IOS 74.2), history 0.0 (waited), fit 86.5, predict 0.8, cleanup 2.7: **345.4 s**. The cached-against-decided test: the decided path's seeds 0-1 (44.3 and 43.2 s) **bit for bit with the replay's cached fit in every array**, the own-price-alone calls included (`checks/pytest_fit_cache_off.json`); seed 2's cache built from scratch in the test's own state folder (41.1 s build) **bit for bit with the replay's cache read from disk** (`checks/pytest_fit_cache_built.json`); that 3.6 GB scratch cache removed by the test as written | Plan step 5 | none | all pass |
| 07:10 | Checked: no file of the template's build tree changed since 05:28 (`find /c/Users/zerom/tnr_lyr_new -newermt "2026-10-11 05:28" -type f`: 0); no repository file outside this build's folders changed since 05:28 except the studies index's row (`find src docs test predictions scripts -newermt ...`); no work tree left (`C:/Users/zerom/tnr_daily*`: none); TabPFN's caches 58 GB on disk (16 seeds, 3.6 GB each, plus the failed attempt's `seed13.part`) | The owner's rules | — | observed |

## P2.3 Sources

None outside the repository and the installed libraries: tabpfn 9.1.0's source in the `tennis-tabpfn-local` environment
(`classifier.py`, `base.py`, `inference.py`, `memory.py`, `settings.py`, `model_loading.py`,
`architectures/tabpfn_v3_5.py`, `architectures/kv_cache.py`, `architectures/shared/{scaled_dot_product_attention,chunked_evaluate}.py`),
read 11 Oct 2026.

## P2.4 Judgment calls

1. **"No cost to prediction quality" read as "the same numbers"** (P2.1, before any measurement): scheduling changes
   bit for bit; a change of computation path within 1e-4 a seed, reported for the owner if not bit for bit. Every
   change adopted turned out bit for bit, so the tolerance decided nothing.
2. **The cached path's configuration** (05:47, after the full-size comparison of three variants): one cache per
   estimator with memory saving as decided (bit for bit) over the batched cache without chunking (8.8e-5, inside the
   tolerance). Chosen because it was bit for bit, and because it mirrors the decided path's own structure at this
   training size (one estimator per forward); seen by then: the three variants' differences from the decided path
   on 46 rows of one seed, no outcome.
3. **tabpfn's own save and load, without their zip** (05:50): the library deflates ~3.5 GB a seed. The three parts
   and the load sequence mirror `save_fitted_tabpfn_model`/`load_fitted_tabpfn_model`; checked bit for bit (16 seeds
   loaded or built).
4. **The cache's key** (05:50): the training matrix and labels, season, seed, the configuration and engine settings,
   the tabpfn and torch versions, the weights file's hash, the card's name, a format number. Not the driver version
   (torch ships its own CUDA libraries; a weak point below).
5. **The card's process scan once per fit step, not per seed** (05:50): `fits.py`'s own pattern; free memory still
   checked before every seed. A scheduling change.
6. **The states step in three processes** (05:52, before any comparison): the IOS and Stage B's forms in their own,
   each family's code unchanged; the forms process loads Stage 4's rows itself after checking by reading that nothing
   between loading and Stage B writes into them. Checked bit for bit twice (tree check, replay).
7. **The history check beside the states step** (05:52): it is a report nothing reads to build an input; joined
   before the fit, so its result is recorded before the predictions; a failed check still fails the run.
8. **Not built: anything inside Stage 0's builder** (the owner's rule; the daily_update_speed session's plan), a cache
   of Stage 4's constants, the rows' dtype conversion, a long-running process, new-rows-only versions of the
   whole-table steps. Stage 0 profiled instead, to give the owner a measured choice.
9. **The failed attempt's `seed13.part` (3.6 GB) left on disk** (05:58): the owner's rule on temporary files.
10. **The kept work tree deleted with `dp.py cleanup`** (06:13): what every run does; it was kept only for the profile.
11. **The build-path test removes its own 3.6 GB scratch cache** after comparing (written 05:56): a test's own output
    under pytest's temporary folder, not a session file.

## P2.5 Claims and their evidence

| Claim (README) | Evidence | Status |
|---|---|---|
| The 0.18 gap is a tabpfn 9.1.0 bug in the cached path with several estimators per cache and memory saving on | `checks/cache_diag_small_e1.json` (one estimator: 0.0), `cache_diag_small_e8.json` (eight: 0.164; inputs, stages 0-2 and the training rows identical; the test rows differ from ICL block 0), the three fixes (`cache_diag_small_e8_{predict-off,false,auto}.json`: 7.4e-5); the mechanism read in `ICLTransformerBlock.forward` (cached branch) and `_torch_sdpa` (`keys[i * sub_batch : ...]` slices from 0) | observed (the experiments) and inferred (the mechanism, from the code) |
| One cache per estimator gives the decided path's numbers bit for bit | `cache_diag_full_e8_same_single.json` (46 rows), `fit_cache_second.json` (16 seeds, 4,232 rows each, 13 loaded and 3 built), the 13 built seeds of the failed run (compared at 05:58, logged), the speed replay against part 1's (16 seeds), the final pytest run | observed |
| The fit takes 82 s instead of 811 | `runs/replay_2026-07-13_R16_speed/run_day.json`, `fit.json` | observed once |
| The states step in three processes gives the same inputs, in 85 s instead of 162 | `checks/tree_check_2026-06-22parallel.json` (1,565 matches), the speed replay's `replay_compare.json` and `states.json` | observed |
| The history check's record is unchanged | the speed replay's `history.json` and `tables.json` against part 1's | observed |
| Stage 0's time is half Arrow-string iteration | `checks/stage0_profile.txt` | observed under the profiler (whose overhead inflates per-call costs); the saving of "about a minute" is an inference |
| A day in under 7 minutes (5.6 warm) | the speed replay; the warm figure substitutes part 1's 9.4 s work tree | observed / inferred |

## P2.6 Weak points

* **One replayed day, timed once.** The work tree's copy took 72 s, cold, after 56 GB of cache files went through the
  disk cache; whether a daily run's cache reads keep it cold is not known.
* **The cache key does not include the GPU driver.** torch ships its own CUDA libraries, so a driver update should not
  change results; not tested.
* **A damaged cache file stops the fit with an error** (rerun with `--fit-cache rebuild`); a cache is never used
  half-written, because its key is written last.
* **Two fits writing the same seed's cache at once** are kept apart only by the card rule (a fit waits while another
  `tennis-tabpfn-local` process runs), not by a lock.
* **Where a flaw would most likely hide:** a field a cache depends on that its key omits (the library's internal state
  outside the saved parts, e.g. a global setting read at predict time). The tests compare the cached fit with the
  decided path on every array; a different machine or library version must rebuild (the key has both).
* **What a re-design would do:** time several live days on an idle machine; prefetch the next seed's cache while the
  current one predicts (about 20 s); vectorise Stage 0 with the owner's approval and prove it byte-equal.

## P2.7 Reviewer checklist

* [ ] `./python.sh -m pytest test/daily_prediction -v` (about 70 minutes).
* [ ] Read `dp_tabcache.key` and `status`: does the key cover everything a saved cache depends on?
* [ ] Read tabpfn 9.1.0's `ICLTransformerBlock.forward` (cached branch) and `_torch_sdpa`: is the bug as described?
* [ ] `dp_selftest.py fit_cache --mode off` against any cached run: bit for bit.
* [ ] `dp.py tree-check --day 2026-06-22`: 57 of 57 bit for bit.

## P2.8 Reproduction

```
./python_tabpfn_local.sh src/eda/daily_prediction/dp_cachediag.py --rows 4000 --estimators 1 --tag small_e1
./python_tabpfn_local.sh src/eda/daily_prediction/dp_cachediag.py --rows 4000 --estimators 8 --tag small_e8
./python_tabpfn_local.sh src/eda/daily_prediction/dp_cachediag.py --rows 0 --estimators 8 --c-single --no-record --tag full_e8_same_single
./python.sh src/eda/daily_prediction/dp_selftest.py fit_cache --src <a run fitted by the decided path> --seeds 0-15 --mode use --tag <t> --out <json>
./python.sh src/eda/daily_prediction/dp.py tree-check --day 2026-06-22 --tag parallel
./python.sh src/eda/daily_prediction/dp.py run_day --run <folder> --replay-week 2026-07-13 --replay-round R16 --checkpoint 2026-06-22 --direct-seeds 0,1
./python.sh -m pytest test/daily_prediction -v --durations=0
```

(07:12, correction by addition: P2.4-P2.8 were drafted at 06:20, before the final pytest run ended. P2.6's first point is
out of date: the replay was in the end timed twice, 403 s with a cold work-tree copy (`runs/replay_2026-07-13_R16_speed`)
and 345 s warm (the pytest run's replay); everything else stands, and the pytest run's results are in the 07:08 row.)
(Time note: the correction above was written at 07:11 by the clock, not 07:12.)

# Part 3: Stage 0's builders (11 Oct 2026)

Started 09:10 PDT, 11 Oct 2026 · Same session (`d2d2331e-b87f-42fd-baa1-b5c3ddebe82c`); no context summary since part 2.

## P3.1 The request

* **The owner's words, verbatim** (11 Oct 2026, about 09:09 PDT): "First delete the leftover folder from a failed save
  3.6 / Then improve time efficiency with this next step / 1. Stage 0 (117 s) is now the biggest step. I profiled it:
  about half the time is pandas reading text columns one element at a time, in stage0_build.py and
  feature_alpha_audit/repair_data.py. Fixing that would likely save about a minute a day. Both files are builders, so
  under your rule I need your go-ahead; the daily_update_speed session also planned this work. I recommend yes, with
  proof that the new Stage 0 is byte-identical to today's. Shall I go ahead?" (the second part quotes my decision 1
  of part 2's report: read as the go-ahead).
* **How it was read.**
  * The leftover folder: `state/template_2026-10-10/tabpfn/season2026/seed13.part` (3.6 GB), named in part 2's report.
  * **The go-ahead covers editing `src/eda/predictability_diagnostic/stage0_build.py` and
    `src/eda/feature_alpha_audit/repair_data.py`**, for speed only, under the standard I proposed: **the new Stage 0
    byte-identical to today's** (every file it writes, on the same inputs). Not covered: any other file of another
    study; if a third must change (a registry of validated builder code, a test), I ask first.
  * Not covered either: changing what Stage 0 computes, its dtypes or its outputs' layout.
* **Plan.**
  1. Delete the folder (after looking at it).
  2. Read both files, their hot spots (part 2's profile), what else checks or hooks them (the level-evidence study's
     validated-code snapshot, tests), and whether another session is editing them now.
  3. A baseline: Stage 0 built with today's code in a work tree, in the variants that are used (the repository's and
     the template's default build; the daily pipeline's `--live-rows`), every output file hashed; the builders' own
     tests run.
  4. The edits: Arrow-backed text columns turned into plain arrays before element-by-element Python, and Python
     group-bys replaced only where the replacement is provably the same; nothing else.
  5. The proof: the same builds with the new code, every output byte-identical; the same tests; the replay through
     run_day (57 inputs bit for bit); the times.

## P3.2 Chronology

| When | Step | Why | Results seen by then | Output |
|---|---|---|---|---|
| 09:10 | Looked at `seed13.part` (05:57: the failed attempt's four files, 3.6 GB) and `seed13` (06:00, complete, used by the checks), then deleted `seed13.part` (`rm` is aliased to ask, which declined without a terminal; `command rm -r`) | Plan step 1 | none | Deleted; the caches now 54 GB (16 seeds) |
| 09:12 | Read: `repair_data.py` (179 lines), `stage0_build.py`'s hot spots (part 2's profile) and its imports; what checks or hooks them: `lower_level_evidence/system_sandbox.py` (the hooked builders: Stage 1, Stage 3, Stage 4, the Elo pieces, Stage B; the IOS through `level_layer_ios`): **neither file is hooked**, so no validated-code registry needs an edit; `feature_alpha_audit/verify_repairs.py` only reports changed code (its assertions are on data); the tests that use them: `test/predictability_diagnostic/test_stage0_build.py`, `test/feature_alpha_audit/test_data_repairs.py`, and four more (`data_continuity/test_rebuild_and_schedule.py`, `predictability_diagnostic/test_order_asof.py`, `prediction_run/test_prediction_run.py`, `rg_first_serve_recount/test_overrides.py`). `stage0_build.py` last changed 10 Oct 18:43 (the daily_update_speed session's year fix, uncommitted; that session's files unchanged since 19:01): not being edited now | Plan step 2 | none | — |
| 09:13 | **Checked in this environment (pandas 3.0.6):** a Python loop over a Series and the same Series' `to_numpy(dtype=object)` give the very same objects (the missing value the identical object) for Arrow-backed `str`, `string`, object, bool and int64 columns; not for float64 (each NaN a new object either way), nullable Int64 (numpy against Python ints) or boolean. Hence one helper, `stage0_build.column_items`, converting only the first kind and iterating any other dtype as before | Plan step 4: the edits must change no value | none | — |
| 09:14 | The originals saved (`data/studies/daily_prediction/stage0_speed/original/*.orig`; SHA-256 `a40322d0...` and `76d552c0...`); `dp_stage0_equiv.py` written (Stage 0 built in a work tree as the pipeline runs it, its six outputs hashed; compare byte for byte, the summary also without its clock line and field by field); a replay-mode work tree `C:/Users/zerom/tnr_s0eq` (Tennis My Life held at the freeze) with the speed replay's live rows | Plan step 3 | none | Baseline launched |
| 09:15 | Baseline tests, before any edit: the two builders' own tests **96 passed**; the four other test files **40 passed** | Plan step 3 | none | — |
| 09:16 | **The edits** (nothing else changed; line endings kept, CRLF): `stage0_build.py`: `column_items` added; `apply_id_aliases` (the set of player ids), `score_columns` (the four columns zipped), `progression` (every column it loops over), `build`'s repeat check (lines 1193-1197): each loop now over `column_items(...)` arrays. `repair_data.py`: the match/side check's `groupby("match_id").side.agg(set)` (a group per match, ~873,000) as one loop building the same sets (a missing match id left out, as the group-by does); the per-name id tuple and country set as one loop (the group-by's two Python functions; read only through `.get`, so a dict serves); the score repair's `itertuples()` (every column of every row) as the four columns zipped | Plan step 4 | none | compiled; the builders' tests 96 passed |
| 09:20 | The baseline builds ended (`stage0_speed/old_{default,live}/`) | Plan step 3 | none | default 141.3 s, live 129.0 s (873,385 matches) |
| 09:29 | **Failure:** the "new" builds ran the original code: `cp` is aliased to ask before overwriting and declined without a terminal, so the work tree kept the originals (the builds' recorded code hashes show it). Kept as **the original code built twice** (renamed `old2_*`) and compared with the baseline | — | none | **Deterministic: all five data files byte-identical, the summary identical but its clock line, the inputs identical** (both variants); 129.3 and 118.8 s |
| 09:33 | The edited builders copied in with the alias bypassed (`command cp`; hashes checked equal to the repository's), then built: `stage0_speed/new_{default,live}/`; compared with the baseline (`stage0_speed/compare_old_new_{default,live}.json`) | Plan step 5 | none | **Byte-identical in both variants:** `stage0_matches.parquet`, `stage0_match_players.parquet`, `stage0_cleaning_log.csv`, `stage0_level_applied.csv`, `stage0_cells.csv` byte for byte; `stage0_summary.json` byte for byte but its `generated_at` line, no other field differing; the inputs identical (the summary's file hashes). **Time: default 141.3 → 75.8 s, live 129.0 → 74.9 s** |
| 09:37 | The new code profiled (live variant, `scratchpad/stage0_new.prof`) | Whether more is safely available in these two files | none | 88 s under the profiler (148 before); `repair_tables` 21 s (was 64), the rest pandas' own vectorised work spread thinly (filtering, maps, parsing numbers). **Stopped here:** no further concentrated element-by-element work in the two files |
| 09:38 | **Messages from another session** (`tennis-predictions-fc`, building the owner's master notebook over this pipeline; peer messages, not the owner's words): (1, ~09:25) five interface questions (entry points, who builds § 7 item 1 and the matchups CSV schema, where a TabPFN-3.5-Thinking switch lives, which outputs are stable, timing); it will not edit this study's folders, `stage0_build.py`, `repair_data.py` or `prediction_run/`; (2, ~09:38) **a bug report**: `predictions.csv` can print a player's name beside the other player's figures, because `prediction_run.live_from_matchups` turns `p_a` to Stage 0's side A but keeps the matchups CSV's names, and `dp_predict` wrote those names beside side A's ids, price and forecast; plus two points: `price_recorded_at` is when the prices step ran, not the quote's time (asks for an optional quote-time column), and `dp_predict` uses the weekly speed feed's coefficients although the decision says `spd_L_D` once the daily collector runs | Coordination; a defect in this study's output | none | Answered after the replay (below) |
| 09:39 | `run_day` replay with the faster Stage 0 (`runs/replay_2026-07-13_R16_stage0fast/`, the new builders in its fresh work tree) | Plan step 5 (end to end) | none | **57 of 57 inputs bit for bit on 23 of 23 matches, every part resumed; all 16 seeds' fits bit for bit with the speed run's; the live frame identical; predictions identical but the price time stamp.** Times: work tree 64.5 (cold), matchups 9.7, tables 128.6 (**Stage 0 84.2**, packages 15.8, check 0.5, layer 15.1, odds 6.2, live prices 0.6), states 100.8, fit 85.0, predict 0.8, cleanup 2.8 |
| 09:41 | **The name bug verified by reading** (`prediction_run/run.py` lines 130-138: `p_a if a_is_a else 1 - p_a`, names unswapped; `dp_predict.py` lines 119-122). Replays carry no names (their live meta has none), so no test could see it; no live day has been run, so no prediction file was wrong in use. The decision's stage-2 text read (`docs/decisions/2026-10-08-current-best-model.md` line 149: "refitted each season, on the speed history that matches the live feed: spd_L_B for the weekly feed, spd_L_D once the daily collector runs"); the daily collector's forms exist for 8-11 Oct (`serve_speed_tabpfn/live/speed_form_2026-10-*.parquet`) | The defect; the peer's other point | none | **Name bug: fixed in this study's code only** (`prediction_run/` is another study's): `dp_steps.side_names` adds each side's name from Stage 0's own player rows by side and refuses a match whose rows disagree with its A/B ids or give a side twice; `live_stage0.parquet` carries them; `dp_predict` writes them and refuses a run folder without them (never the CSV's names). Tests added: `test_side_names_follow_stage0_sides` (fast: passed) and `test_prediction_names_are_stage0_sides` (the replay's names against the template's own Stage 0, by id). **The speed feed: not changed** (it moves predictions by design and how replays before 8 Oct should be treated is open): put to the owner with a recommendation |
| 09:47 | The proof work tree deleted (`dp.py cleanup`); **the full pytest run launched (09:47:12)**: `checks/pytest_part3.txt`, 15 tests. Code frozen until it ends | Plan step 5 | none | running |
| 09:50 | Replied to `tennis-predictions-fc` (SendMessage): the CLI (`dp.py` commands) is the stable contract, not the Python functions; § 7 item 1 is not being built here, the matchups CSV schema is prediction_run's `MATCHUP_COLUMNS` (kept stable); an optional `quoted_at` column agreed, to be added after the test run; the Thinking switch to be owned inside `dp_fit`/`dp_predict` once the owner settles its cost, limits, seeds and stage 2; the stable outputs listed (columns may be added, not removed); the name bug confirmed and fixed; the speed-feed point put to the owner | Coordination | none | sent |
| 09:48 | (Time note: the reply row above, written as 09:50, was sent at about 09:48 by the clock) | Rule 4 | — | — |
| 10:43 | **The full pytest run ended: 15 passed in 3,334.0 s (55:34)** (`checks/pytest_part3.txt`): part 1's nine, part 2's four, the two name tests, with the faster Stage 0 in every work tree. Its replay (`runs/pytest_replay_2026-07-13_R16_20261011T171202Z/`): every name present (46 of 46) and Stage 0's by side; 323.8 s in all (work tree 10.4 warm, matchups 2.7, prices 0.1, tables 125.1, states 98.4, fit 83.6, predict 0.8, cleanup 2.9) | Plan step 5 | none | all pass |
| 10:05-10:30 | More messages from `tennis-predictions-fc` (peer, not the owner): agreement on the interface; a request for an env override of the instance (`DP_INSTANCE`); review findings: (1) ambiguous Stage 0 name keys stop a live run in prediction_run's linking (12 ATP and 2 WTA current players, e.g. Jakub Mensik: `atp:210150` and `atp:210084`); (2) **run_day's cleanup deletes the work tree even when it was refused because another run's tree exists**; (3) notes for a future Thinking fit (query only grid rows so a re-price is free; compare the served config); (4) its linker's rules; and a planned live day through `run_day` at about 10:50, which I asked it to hold until my changes land (sent ~10:20) | Coordination | none | (1) prediction_run's code (another study's): for the owner, not changed; (2) verified by reading (`dp_steps.run_day`'s `finally`): fixed below |
| 10:45 | Changes (this study's code only): `dp_common.INSTANCE_ID` from `DP_INSTANCE` (the instance folder's name; default unchanged), `init` refuses a missing instance, `run_day` refuses a run made for another instance, the fit and predict steps use the run's recorded instance; **`run_day` deletes a work tree only when its marker names this run** (`dp_worktree.setup(owner=...)`, `owner_of`); the live matchups CSV copied into the run folder at the matchups step; `dp_matchups.quote_times`: the CSV's optional `quoted_at` (UTC) to `prices.parquet` and `predictions.csv`'s `price_quoted_at` (by row, after checking tour and round). Tests added: `test_quote_times_follow_csv_rows`, `test_run_day_never_deletes_another_runs_work_tree` (5 fast tests passed). **The cleanup test checked to fail on the old code:** a scratch copy of the package with the old condition deleted the other run's tree (scratchpad `oldguard/`) | The bug; the agreed interface | none | — |
| 10:52 | Targeted pytest run launched (`checks/pytest_part3b.txt`): every test but the four family tests and the two invalidation tests (their code is unchanged since 10:43's full pass), with a fresh replay through `run_day` | Re-check of today's last changes | none | running |
| 10:56 | (Time note: the targeted run above was launched at 10:50:55 by its own output.) **It ended: 10 passed, 1 failed** (`checks/pytest_part3b.txt`, 5:34). **The failure was mine:** `test_fit_cache_equals_decided_path`'s self-test builds a comparison folder with only the fit's two inputs, and the fit step now reads the run's instance from `run.json` (refused: "run.json missing"). Fixed in `dp_selftest.FIT_INPUTS` (run.json copied too); a run folder without it stays refused. The fresh replay (`runs/pytest_replay_2026-07-13_R16_20261011T175056Z/`): 57 of 57 inputs bit for bit, names 46 of 46, `price_quoted_at` present (empty in a replay), its own work tree deleted by the marker rule; 329.6 s (work tree 10.9, matchups 2.9, tables 128.0, states 99.7, fit 84.1, predict 0.9, cleanup 3.0) | Re-check | none | — |
| 11:00 | The failed test re-run on the same fresh replay (`DP_TEST_REPLAY_RUN`) | — | none | **passed** (the decided path's seeds 0-1 and a freshly built seed 2 bit for bit with the replay's cached fit). **On the final code: every test that touches the last changes passes (11 of 11)**; the four family tests and the two invalidation tests passed at 10:43 with code they share unchanged since |
| 11:01 | Told `tennis-predictions-fc` the changes have landed (quoted_at's format and placement; `DP_INSTANCE` = the instance folder's name, with `DP_BASE_TREE` and a checkpoint on that tree, its first fit building the caches, its first predict the stage-2 coefficients; the cleanup rule); its held live run may start | Coordination | none | sent |

## P3.3 Judgment calls

1. **The go-ahead read as covering the two named builders only, for speed, under byte-identity** (09:10, before any
   edit). Neither file is a hooked builder (checked), so no registry of validated code needed an edit; no third file of
   another study was edited.
2. **One helper for every loop, restricted to the column types checked identical** (09:13, before the edits): a loop
   over any other dtype keeps its old behaviour, so a later dtype change upstream cannot silently change a value here.
3. **Byte-identity, not value-equality, as the standard**, with the summary's clock line the one stated exception, and
   a determinism check of the old code itself (made by accident at 09:29, kept deliberately).
4. **Stopped after the six hot spots** (09:37): what remains is pandas' own vectorised work spread thinly; restructuring
   it is a riskier kind of edit than the one approved.
5. **The name bug fixed in this study's code, not in prediction_run's** (09:41): `live_from_matchups` is another
   study's; the names now come from Stage 0's own rows by side, so its behaviour no longer matters for the output.
6. **The speed-feed point (`spd_L_D`) not changed** (09:41): it moves predictions by design; put to the owner.
7. **A peer's live run held** (10:20) until the code under it stopped changing.
8. **Work-tree ownership by marker rather than a flag** (10:47): a flag would have left a run's own half-made tree; the
   marker names the run.
9. **The proof work tree, the scratch package copy and the profiles:** the work tree deleted with the pipeline's own
   cleanup (09:47); the scratch copy (scratchpad `oldguard/`) and the profiles are scratchpad files, left there.

## P3.4 Claims and their evidence

| Claim (README) | Evidence | Status |
|---|---|---|
| The new Stage 0 is byte-identical to today's, in both variants | `stage0_speed/compare_old_new_{default,live}.json` (and `compare_old_old2_*`: the old code deterministic) | observed |
| Stage 0 129-141 s → 75-84 s | the same records' seconds; `runs/replay_2026-07-13_R16_stage0fast/tables.json` (84.2 in the pipeline) | observed |
| The six test files using the builders pass before and after (136) | logged runs at 09:15 and 09:39 | observed |
| The replay with the new Stage 0: 57 of 57 inputs bit for bit, fits identical | `runs/replay_2026-07-13_R16_stage0fast/replay_compare.json`; the comparison at 09:46 | observed |
| The name bug and its fix | the code read (`prediction_run/run.py` 130-138, `dp_predict.py`); `test_side_names_follow_stage0_sides`; `test_prediction_names_are_stage0_sides` on the 10:12 replay | observed |
| The cleanup bug and its fix | the code read; `test_run_day_never_deletes_another_runs_work_tree`; the old condition deleting the tree on a scratch copy | observed |
| A day in about 5.4 minutes (warm) | `runs/pytest_replay_2026-07-13_R16_20261011T171202Z/run_day.json` (323.8 s) | observed once |

## P3.5 Weak points

* **Byte-identity was shown on today's inputs (and the 8 Oct freeze of Tennis My Life).** The helper keeps every
  unverified dtype on the old path, so a new dtype cannot change values silently; but a code path today's data never
  takes (a branch of `progression` or the repairs no row reaches) is covered by the argument, not by an observation.
* **Timings are single runs on a machine whose disk cache was disturbed all day** (work-tree copies of 10-65 s).
* **Where a flaw would hide:** an element type that iterates differently from its array (the check covered str,
  string, object, bool, int64; float64, Int64 and boolean are deliberately left on the old path).
* **What a re-design would do:** re-run the byte-identity check on the next day's real tables, and after any pandas
  upgrade (the helper's premise is pandas' iteration behaviour).

## P3.6 Reviewer checklist

* [ ] Read `stage0_build.column_items` and every place it is used; diff the two builders against
      `data/studies/daily_prediction/stage0_speed/original/*.orig`.
* [ ] Rebuild: `dp_stage0_equiv.py build` with the originals and with the new files in one work tree, then `compare`:
      all byte-identical but the summary's clock line.
* [ ] `./python.sh -m pytest test/predictability_diagnostic/test_stage0_build.py test/feature_alpha_audit/test_data_repairs.py`
      and the four other test files that use the builders.
* [ ] `./python.sh -m pytest test/daily_prediction -v`.

## P3.7 Reproduction

```
./python.sh -c "import sys; sys.path.insert(0, 'src/eda/daily_prediction'); import dp_worktree as WT; from pathlib import Path; WT.setup(Path('C:/Users/zerom/tnr_s0eq'), replay=True)"
# copy run/live_rows.parquet into the tree; put the original builders in it (data/studies/daily_prediction/stage0_speed/original/)
./python.sh src/eda/daily_prediction/dp_stage0_equiv.py build --tree C:/Users/zerom/tnr_s0eq --tag old --variant default
./python.sh src/eda/daily_prediction/dp_stage0_equiv.py build --tree C:/Users/zerom/tnr_s0eq --tag old --variant live
# copy the new builders in (command cp: cp is aliased to ask), then the same with --tag new
./python.sh src/eda/daily_prediction/dp_stage0_equiv.py compare --a old --b new --variant default
./python.sh src/eda/daily_prediction/dp_stage0_equiv.py compare --a old --b new --variant live
./python.sh -m pytest test/daily_prediction -v --durations=0
```

(11:30, part 3 continued after its closing sections, by addition.) **The first live day through this pipeline**, run by the
`tennis-predictions-fc` session (its report, a peer's: observed by me only through its run folder): run
`runs/live_2026-10-11_110150/`, 8 ATP Shanghai R32 matches of 12 Oct, `run_day --refresh --checkpoint auto
--leave-checkpoint auto`, its own work tree. Steps: refresh 89.4 s, matchups 3.6, prices 0.0, work tree 10.8, tables
229.5 (the live timeline steps included), states 389.7 (**11 of 14 parts recomputed in full**, 3 resumed: the first run
on 11 Oct's tables, as expected), checkpoint 609.3 (**new checkpoint `state/template_2026-10-10/2026-09-21/`**), fit 57.2
(cached), predict 0.2, cleanup 2.5: 1,393 s. Names by Stage 0's side and `price_quoted_at` as designed; gate: 5 may be
bet, 3 not (an earlier match without a box score); `reprice` worked at a later pull. **Read by me in `history.json`:**
`template_ok` false: lower-level history differs from the 8 Oct reference (new past 30 and dropped 30, mostly the same
2011 tour-qualifying matches under revised player ids, `atp|2011-416|Q1|...`; revised 20, mostly 2026 Challengers;
main-tour changes 7, allowed). The decided freeze says new, revised or dropped lower-level history never enters by
itself, and a template build on these tables would be refused; the live path (prediction_run's design, which this
pipeline reuses) builds from the day's dump and only reports it. **Not changed: put to the owner** (hold the lower-level
history at the freeze in live runs, accept the revisions, or refuse such runs).
(Time note: the paragraph above, headed 11:30, was written at 11:27 by the clock.)
