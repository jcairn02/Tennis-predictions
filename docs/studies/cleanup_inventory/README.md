# Cleanup inventory, 4–11 October 2026

11 Oct 2026 · For the owner · **Deleted the same day, 17:54–17:59: 236.3 GB of the "delete now" groups, less what
was held back ([What was deleted](#what-was-deleted-11-oct-2026)). 14 Oct: `tnr_lyr_off` and `tnr_lyr_on`, 47.1 GB,
after their step ([below](#14-oct-2026-tnr_lyr_off-and-tnr_lyr_on)). 14 Oct: three Roland Garros leftovers, 8 files, 7.9 MB;
`.gitignore` and `data\LARGE_FILES.md` brought up to date ([below](#14-oct-2026-three-roland-garros-leftovers-gitignore-and-the-large-files-guide)).** · Process log: [process_log.md](process_log.md) ·
Subagent briefs: [subagent_briefs.md](subagent_briefs.md)

You asked: "For the past week, find all studies/data or models that are artifacts, no longer useful, scratch pads or
tests that we've done. Everything that past models proposed we clean up but I didn't. List it all and segment it into
highly recommend cleans/deletion and optional."

## In short

* **About 355 GB is highly recommended for deletion:** about 264 GB now, and about 91 GB more once one small step is
  done for each item. **About 3.2 GB is optional.** Sizes are decimal (1 GB = 10⁹ bytes).
* **Twelve build sandboxes in `C:\Users\zerom\` are 309 GB of it.** Each is a full copy of the repository, made for
  one build on 8–10 Oct. Their results were copied into `data\studies`, and nothing reads them now.
* **Most of it was proposed before.** Past sessions proposed 37 items that still exist, and you answered three of
  those proposals: you approved each one, and each was done. The rest were never answered; some were asked 4–5 times.
* **The disk is about to block work.** C: has **120 GB free**, and it falls during the day. The master notebook's
  builder (`src/pipeline/train.py`) refuses a new template build below 130 GB.
* **Deleting the study leftovers also speeds up every daily run.** Every build sandbox and every daily work tree
  copies `data\studies`, so about 10 GB of it is copied on every run.
* **One danger: the sandboxes contain junctions (folder links) into the real `data\raw` and `data\dump`.** A careless
  delete can follow a junction and erase the real data. Use the steps in [How to delete safely](#how-to-delete-safely).

## 14 Oct 2026: `tnr_lyr_off` and `tnr_lyr_on`

You said: "Do this and be mindful of anything that reads these files to properly change it".

* **47.1 GB deleted; C: went from 219 GB to 263 GB free.** No file was lost from the kept folders. Each build's two
  links into `data\raw` and `data\dump` were removed as links first.
* **Three programs read these two builds.** Each was changed or checked:
  * The level-layer check (`verify.py --gates`) read 7 small summary files. It now reads copies of them.
  * The level-layer solver check (`solver_tolerance.py`) re-solves player ratings from the "on" build's working file
    and its settings. It now reads copies, and the copied settings file points at the copied strength table.
    Its record folder is switched off: left on, a re-run would have quietly re-created the deleted folder.
  * A study from 13 Oct (`unpriced_leads`) needs one table of the "off" build. It already keeps its own saved
    copy, which still matches its fingerprint, so nothing changed there.
* **The copies:** 18 files, 42 MB, byte for byte, in `data\studies\level_layer_adoption\sandbox_extracts\` (with a
  README and a list of fingerprints).
* **Proved three times** (before the code change, after it, and with the builds gone):
  * Both programs give exactly the same results from the copies as from the builds. The only exception is the
    re-solve's stopwatch reading.
  * The gate check still reproduces its 10 Oct record byte for byte.
  * Neither deleted folder came back.
* **What can no longer be repeated as written:** a leak test that was run inside the whole "on" build. Its 10 Oct
  result stays on record. Repeating it would mean a rebuild on today's tables.
* `tnr_lyr_new` is still read by the solver check and by the 13 Oct study. If it is deleted later, it needs the same
  treatment.
* **Records:** `data\studies\cleanup_inventory\lyr_2026-10-14.json`; the script:
  `src\eda\cleanup_inventory\lyr_sandboxes.py`.

## 14 Oct 2026: three Roland Garros leftovers, `.gitignore` and the large-files guide

You pasted the "Delete now" line of the commit check of 13 Oct, then asked: "add to .gitignore anything large in size
or folders/files that are easily reproducable that aren't very small."

* **Deleted: 8 files, 7.9 MB,** in `rg_first_serve_recount`: `confirmed\candidate_corrections\` and
  `followup\service_games_round1\` and `round3\`. The correction applied on 13 Oct replaced them, and nothing reads
  them. They were not in git or a backup, so the deletion is final. Their fingerprints are in the process log (§ 8b).
* **`.gitignore`:**
  * Ignored everywhere: arrays and model state (`.npz`, `.joblib`, `.safetensors`). These are fits and caches.
  * Ignored: the daily engine's 2.5 GB temporary caches; a candidate's `left_out.csv.gz`; the feed check table that
    every refresh rewrites.
  * Every file over 50 MB is now listed: 187 files, all ignored.
  * The feed's 13 Oct hand check of identities is no longer ignored, because nothing else holds it.
* **`data\LARGE_FILES.md`:** a row for every file over 50 MB, the 8 Oct backup described, and a check that takes
  about a second.
* **Not done (your call):**
  * Git still tracks 1,279 `.npz` files (1.35 GB) that the new rule covers. `git rm -r --cached -- '*.npz'
    data/studies/official_point_feeds/wta_checks.csv` stops tracking them and keeps the files on disk.
  * No backup holds the frozen reference, or anything made since 8 Oct. `src\eda\data_continuity\backup.py` uploads
    one.

## What was deleted (11 Oct 2026)

You said: "Delete all the highly recommended delete now files. The ones you are very confident about it".

* **236.3 GB deleted in 2.5 minutes; C: went from 120 GB to 341 GB free.**
* **No file was lost from the kept trees** (`data\raw`, `data\dump`, `tnr_dump_freeze`, `tnr_lyr_new`,
  `current_best_model`). Each was listed file by file before the run, after every sandbox and at the end.

| Group | Deleted | Size |
|---|---|---:|
| A. Build sandboxes | `tnr_live`, `tnr_live2`, `tnr_live3`, `tnr_sys1`–`tnr_sys3`, `tnr_sys5`, `tnr_sys_ios`, `tnr_lyr_rp` (their 26 junctions removed first, link only) | 196.1 GB |
| B. Backup zips | The three 8 Oct zips (the manifests and README stay) | 22.1 GB |
| C. Scratchpads | 297 old sessions' folders. One empty file is left in 531ce504: a Claude process in use today holds it, and it goes when that process ends | 4.5 GB |
| D. Study leftovers | 1,455 files and folders, as listed below, less the items held back | 12.9 GB |
| E. Temp, caches, strays | `ssp_verifier_*`, pytest's temp folder, `skrub_data`, 159 `__pycache__` folders and `.pytest_cache`, the 8 root strays, the 2 dead scripts | 0.7 GB |

* **Processes stopped:** the four in G below, and eight more orphan `tail -f` processes (started 1–8 Oct, parents
  gone). Those eight held files open in scratchpads being deleted.
* **Held back, not "very confident":**
  * `tnr_sys4` (23.2 GB): `lower_level_evidence/system_arms.reuse()` copies from it for an arm the pending P7 test could
    build.
  * `level_layer_adoption\candidate_men26\` (0.13 GB): `level_layer_adoption/verify.py` reads it, and that study's
    reviewer check is pending.
  * `lower_level_evidence\system\stage0\C0_pre\` (0.19 GB): five of that study's scripts name it, and P7 is pending.
  * `current_best_model\2026-10-09_rg_box_scores\first_collect_indoor_filled\` (0.03 GB): the Roland Garros
    correction's record; the correction is not yet applied.
  * `event_levels\frame.parquet` (0.07 GB): kept while `event_levels\local\C\` (optional) is kept.
  * `surface_ios\arms\` (0.2 GB): the previous model's frame builder reads `arms\sprof.parquet`
    (`surface_rating_race/arms.py:64`, `model_frame.py:53`). It cannot be rebuilt on the tables it was built on.
  * `lower_level_evidence\candidates\R_S2\` and `system\results\arms\SYS_S2\` (small): they hold the two share
    inputs that the [feature universe](../feature_universe/README.md) lists as a lead to admit.
  * 20 scratchpads:
    * those written in the last 24 hours, or whose session's transcript was;
    * this session's own;
    * the three that docs cite;
    * four that repository records point into (6a2c00c2, 46524484, 48421609, 5ba10243).
  * The loose scratch files in `Temp`.
  * The 11 locked folders (they need an administrator).
* **Git:** 1,091 of the deleted files were tracked in git. No git command was run.
  * `git status` shows them as deleted, and every one of them comes from this run.
  * Commit them with your next commit, or bring any back with `git restore <path>`.
* **A copy kept:** [kept/tennis_model_anatomy.html](kept/tennis_model_anatomy.html), from scratchpad 7d6b3770.
* **Not done (your call):**
  * `data\LARGE_FILES.md` lines 16, 22, 25, 28 and 31, and `.gitignore` line 53, describe deleted files. **Done 14
    Oct** (process log § 8d).
  * The READMEs of `surface_ios`, `surface_rating_race`, `point_sequence`, `polymarket_sharp_money` and
    `predictive_frontier_tabpfn` cite deleted files.
  * 34 other leftover `tail.exe` processes (1–11 Oct) still run. Some may belong to open sessions, so I left them.
  * The "once one small step is done" group (about 91 GB) and the optional group are untouched.
* **Records:**
  * every item, its size, the links removed and the result:
    `data\studies\cleanup_inventory\deletions_2026-10-11.json`;
  * the reader check: `deletions_2026-10-11_readers.txt`;
  * the script: `src\eda\cleanup_inventory\delete_now.py`.

## Highly recommended: delete now (about 264 GB)

### A. Build sandboxes: 219.3 GB

| Folder | Size | What it was | Why it can go | Proposed before |
|---|---:|---|---|---|
| `C:\Users\zerom\tnr_sys1` … `tnr_sys5`, `tnr_sys_ios` | 140.9 GB (22.0, 24.4, 23.4, 23.2, 23.4, 24.5) | The lower-level-evidence study's arm builds (9–10 Oct) | Every arm's frame, fits and records are in `data\studies\lower_level_evidence\system\`; the layer was adopted and rebuilt in `tnr_lyr_new` | f63f0543, 9 and 10 Oct (5 times); that study's README §7 |
| `C:\Users\zerom\tnr_live`, `tnr_live2`, `tnr_live3` | 56.0 GB (18.7 each) | prediction_run's first replay, its live-dated replay and the 9 Oct live run (Beijing) | Copied to `data\studies\prediction_run\{replay_2026-10-09, replay_2026-10-09_live, live_2026-10-09}`. `tnr_live` also blocks the next default prediction-run setup | 5073fd89, 9 Oct |
| `C:\Users\zerom\tnr_lyr_rp` | 22.4 GB | The 10 Oct level-layer replay | Copied to `data\studies\prediction_run\replay_2026-10-10_layer\` (23 of 23 equal). **Delete by hand: one junction points into `tnr_dump_freeze`, which must stay** | d061329f, 11 Oct |

### B. The 8 Oct backup's local zips: 22.1 GB

| File | Size | Why it can go | Proposed before |
|---|---:|---|---|
| `data\backups\2026-10-08\tennis_data_{studies,raw,dump}_2026-10-08.zip` | 22.1 GB (15.4, 4.0, 2.7) | **Checked today:** the copies in `gs://tennis-predictions-archive/data/2026-10-08/` have the same sizes and identical MD5. Keep the small manifest files beside them | 53e9c9d9, 8 Oct ("delete them now that the bucket copies are checked?"), no reply |

### C. Session scratchpads: 8.1 GB

| Folder | Size | Why it can go |
|---|---:|---|
| `C:\Users\zerom\AppData\Local\Temp\claude\c--Users-zerom-Documents-Tennis-predictions\<session>\` (318 folders, 254 of them empty) | 8.1 GB (largest: f63f0543 2.0, 5a3adee6 1.5, 3210cf29 1.3, 7d6b3770 0.9, 6a2c00c2 0.6) | Throwaway scratch. Sessions named these files as leftovers 3–8 Oct; nothing in the repository reads them. **First:** confirm f63f0543, e1afd0c6, b2538231 and 310009bc have finished (they wrote files today), and copy out `7d6b3770…\scratchpad\tennis_model_anatomy.html` if you want it |

### D. Study leftovers in `data\studies`: 13.6 GB

Each item below is either rebuildable or superseded, and its verdict or result is recorded elsewhere. No current model,
decision, test or pipeline reads it.

| Item (under `data\studies\`) | Size | What, and why it can go | Proposed before |
|---|---:|---|---|
| `surface_ios\uploads\*\X_train.parquet`, `X_query.parquet`, `y_train.npy` (768 files) | 5.48 GB | Fit inputs of a finished study (6 Oct); 4.3 GB of them are byte-identical seed copies. **Keep `manifest.json` and the 256 `query_ids.parquet`** (two other studies read them) | — |
| `polymarket_sharp_money\{wallet_markets, scored_positions, prematch_positions, prematch_positions_buffer30, maker_cells}.parquet` | 2.66 GB | Derived tables (25 Sep, before the week); rebuild in about 10 minutes from the kept fills; results in the JSONs | — |
| `lower_level_evidence\`: the first run's `candidates\{F,FP,FP_half,FP_L,FP_placebo,P,R_L,R_S2}\` fits and frames, `candidates\offsets\forms_z_untranslated.parquet`, the rejected `system\arms\{SYS_w0,SYS_w50,SYS_w100,SYS_NOCLASS,SEP_ALL,RES_ONLY,SYS_ITFASIS,SYS_BOTH_ITFASIS,IDENTITY,NEW_SYS_BOTH_optA_unread}\`, the dry runs `*_C1DRY`, the probes' `work\` folders, `system\results\arms\{SYS_PLACEBO,SYS_S2}\`, `system\stage0\C0_pre\` | 1.42 GB | Superseded first run and rejected or never-scored arms; readings in `system\results`; `C0_pre` rebuilds in minutes | That study's README (the fits are "the owner's call") |
| `event_levels\local\A\`, `local\B\`, `frame.parquet`, partial `results_*.{csv,json}` | 0.50 GB | Fits of finished research (8 Oct); verdict in `results.csv` | 8f9a727d, 8 Oct (the partial results) |
| `point_sequence\` intermediate tables (`points_*`, `matches_*`, `trait_*`, `lev_player_matches`, …) and `cache\` | 0.39 GB | Closed study's intermediates and cache | — |
| `bet_timing\local\`, `local_lines\`, `local_consensus\`, `local_cons_trained\{pb__,bo__}*.npz`, `results_2024_2026.json` | 0.38 GB | Fits of finished research (8 Oct), scored in its result JSONs; a superseded first scoring | 58de132a, 8 Oct |
| `surface_ios\full_runs\*_current.*`, `surface_ios\arms\` | 0.55 GB | Pooled runs and arm frames; the current model rebuilds its IOS in its own build; the decision itself says to delete `full_runs\` before a rebuild | — |
| `line_sharpening\` intermediate tables and `local\` | 0.33 GB | Finished research (6 Oct); deterministic 15-minute rebuild; results kept | — |
| `lean_review\arms\{A1,A3,P0,P2}\` | 0.16 GB | Vetoed or unused arms; readings in `t2_scores.csv` | — |
| `tour_pooling\fits\` (all but `split__*`), `segments\standin\` | 0.16 GB | Rejected arms; forecasts kept in `scores\forecasts.parquet` | — |
| `shot_level\stage2_frame.parquet` | 0.13 GB | Finished study's scored frame (4-minute rebuild) | — |
| `level_layer_adoption\candidate_men26\` | 0.13 GB | **Byte-identical duplicate** of `current_best_model\template_2026-10-10\` (90 of 90 files) | d061329f, 11 Oct |
| `training_window\local\`, `meta_stack\local\`, `pair_strength\local\` | 0.30 GB | Fits of rejected studies; verdicts recorded | — |
| `feature_interactions\local\{binj__,levels__}*.npz`, `features\levels.parquet`, `redteam\*_binj_2024.parquet`, `verify\cols.parquet` and smoke files | 0.11 GB | Rejected arms and caches; verdicts recorded | — |
| `match_timing\undated_matches.csv` | 0.11 GB | Stale, uncompressed old list; nothing reads it (also delete its lines in `data\LARGE_FILES.md` and `.gitignore`) | 7d6b3770, 6 Oct (4 times); 78f9b081, 8 Oct |
| `tabpfn_thinking\tabicl\` | 0.07 GB | A finished TabICL check; result in `tabicl_check.json` | — |
| `daily_prediction\stage0_speed\{old,old2,new}_{default,live}\` (data files; keep each `record.json`) | 0.54 GB | Six copies of Stage 0's output from today's byte-identity proof; the comparisons and hashes are recorded | This session |
| `feature_alpha_audit\repair_*` at the top level | 0.04 GB | Superseded by `repairs\` (two are hash-identical copies) | — |
| `current_best_model\2026-10-09_rg_box_scores\first_collect_indoor_filled\` | 0.03 GB | The Roland Garros candidate's aborted first collection, never fitted; its hash is recorded | rg_first_serve_recount process log |
| Smaller items (each under 25 MB) | 0.09 GB | `predictive_frontier_tabpfn\report_qa\*_desktop_profile\` (browser profiles), `surface_elo_pieces\local\` and `audit_scratch\{fake_tabpfn,pytest}\`, `predictability_diagnostic\summary_number_check.csv`, `ufc_ideas\_check_*`, `data_continuity\_scratch_{left,right}.parquet`, `infosys_atp_backfill\speed_panel_augmented.parquet` (a hash-identical duplicate), `ios_product_centring\local\repro\`, `predictive_frontier\matplotlib_cache\` and QA screenshots, `surface_rating_race\results_partial.*` and `moves_partial.csv`, the verifier's smoke chunks `*_s999.json`, `data_map\_logs\`, `lower_level_evidence\snapshots\dryrun_p7_*.md`, a few smoke logs | 8edce54f, 46524484, 210f1d50, 893b6c86, 8a6ba876 (6–9 Oct), and READMEs |

### E. Temporary and test folders, caches, strays: 0.66 GB

| Item | Size | Why it can go | Proposed before |
|---|---:|---|---|
| `C:\Users\zerom\AppData\Local\Temp\ssp_verifier_*` (5 folders) | 0.52 GB | The serve-speed verifier's temporary folders; results in its records | 48421609, 7 Oct |
| Repository root: `explore1.csv` … `explore5.csv`, `panel_noresult.parquet`, `controls_full.json`, `nearest_final.json` | 0.11 GB | Scratch written to the root by sessions on 2–7 Oct; nothing references them (`nearest_final.json`'s content is now in code). Four are in git (`git rm`) | eedac0ed, 6 Oct (the explore files) |
| `__pycache__` (159 folders), `.pytest_cache`, `C:\Users\zerom\AppData\Local\Temp\pytest-of-zerom`, `data\studies\{data_continuity,surface_elo_pieces}\pytest_tmp\`, about 30 loose scratch scripts in `Temp` | 0.03 GB | Caches and test temp, recreated automatically | 46524484, 53e9c9d9 (6–8 Oct) |
| `C:\Users\zerom\skrub_data` | empty | Made by a package install on 6 Oct | — |
| `src\eda\feature_interactions\round1\math_audit\apply_checkpoint1.py`, `round0\body\check_tables.py` | 7 KB | One-off edits already applied; nothing cites them | — |

### F. Locked test folders: size unknown (an administrator must take ownership)

Eleven folders made on 2 Oct deny every read, even of their permissions; they look like a sandboxed tool's pytest
runs. **They cause 11 of pytest's 18 collection errors.**
* `data\backups\evaluation-tests-56120ecf35dd437290bb3736c40bfb3c\`
* `data\studies\feature_alpha_audit\pytest_original_retry_20261002\`
* `data\studies\feature_alpha_audit\repairs\pytest_integrated_final\`
* `data\studies\predictive_frontier_tabpfn\pytest_{2026_roundoff_audit, final_men2026, guard_review_retry, men2026_tabpfn, protocol_guard_2026, protocol_sdk_2026, score_history_20261002, score_receipts_20261002}\`

Proposed by eedac0ed (6 Oct) and 53e9c9d9 and 78f9b081 (8 Oct); never answered.

### G. Leftover processes still running

* `tail.exe` 53808 and 41588 have followed `tnr_lle\logs\lane*.out` since 9 Oct. They also hold files that block
  deleting `tnr_lle`.
* `bash.exe` 37948 and 24472 are loops left by a session on 10 Oct at 18:46, polling a task file every 10 s.

## Highly recommended once one small step is done (about 91 GB)

| Item | Size | The step first | Proposed before |
|---|---:|---|---|
| ~~`C:\Users\zerom\tnr_lyr_off`, `tnr_lyr_on`~~ **Deleted 14 Oct** ([above](#14-oct-2026-tnr_lyr_off-and-tnr_lyr_on)) | 47.1 GB | `level_layer_adoption\verify.py --gates` reads them for that study's reviewer check, which is still unticked. Run it, or drop it, then delete. The results are already in `level_layer_adoption\template_off\` and `current_best_model\level_layer_2026-10-10\` | d061329f, 11 Oct |
| ~~`C:\Users\zerom\tnr_sb_rg_candidate`~~ **Deleted 16 Oct** (at the owner's word, by the P6 data-issues session: [its log](../p6_data_issues/process_log.md)) | 22.4 GB | It held the only copy of the Roland Garros candidate's Stage 0 and timeline, which `input_dose.py` and `verify_applied.py` take. Those files (96 MB) were first copied into `data/studies/current_best_model/2026-10-09_rg_box_scores/candidate_tables/`, then the sandbox was removed by `run_chain.py --cleanup` (its links unlinked first; the real data folders checked unchanged) | 640ec189, 10 Oct (twice) |
| `C:\Users\zerom\tnr_lle` | 20.3 GB | Stop the two `tail` processes. If the women's and ITF test (P7) may run, copy out the 32 files `lower_level_evidence\system_arms.reuse()` would take from here (0.40 GB); otherwise just delete | f63f0543, 9–10 Oct |
| Scratchpads 1407378e, 1de31848, 9fe8e537 | 1.1 GB | Docs cite scripts or memos inside them (`checkpoint_1.md`, `review_statistics.md`, `round2_lead.md`): copy those files into the repository first | — |

## Optional (about 3.2 GB)

These have some value: evidence a decision or an open checklist item still cites, or tables that cannot be rebuilt
as they were.

| Item (under `data\studies\` unless stated) | Size | Why keep it, perhaps |
|---|---:|---|
| `ufc_ideas\stage{A,B,C}_features`, `stageB_ios` | 0.40 GB | Read only by finished studies; a rebuild on today's tables would differ |
| `surface_ios\full_runs\*_surface.*`, `tuning\`, `cache\` | 0.71 GB | `ios_product_centring`'s centring proposal (awaiting you) reads them; `tuning\` is behind `tuning_choice.json` (2 h to rebuild) |
| `surface_rating_race\local\` (race and sprof arms) | 0.23 GB | Evidence for the offset-Elo decision (about 3 GPU hours to redo) |
| `serve_speed_tabpfn\local\`, `design\verifier_worlds\`, `verifier_multiplicity\` | 0.22 GB | Evidence for the speed-nudge decision and its design audit |
| `feature_interactions\round1\_panel_aug.parquet`, `_history_feats_2010_2024.parquet` | 0.19 GB | Cannot be rebuilt; on 8 Oct you asked for them to be gitignored rather than deleted |
| `lower_level_evidence\system\arms\{NEW_ASIS,NEW_ASIS_PRE,NEW_SYS_BOTH,REF_noITF,IDENTITY_ALL}\`, `system\results\arms\R_S2\`, `system\ios_layer\inputs\` | 0.43 GB | Evidence for the open P7 decision (women and ITF) |
| `level_layer_adoption\stage0\C0_men26\`, `template_off\` | 0.27 GB | Named in the Challenger-data decision and the layer's harm check |
| `point_sequence\sequences.parquet`, `seq_matches.parquet`; `bet_timing\local_cons_trained\pf__*.npz`; `prediction_run\live_2026-10-09\stage0\`; `ios_product_centring\centred_products.parquet`; `tabpfn_thinking58\upload\` | 0.42 GB | Evidence behind the Pinnacle-first decision, open checklist items, or records a README lists |
| Smaller items (each under 50 MB): `predictive_frontier_tabpfn\superseded_pooled_preparation.zip` (kept on purpose), `feature_alpha_audit`'s original-audit outputs and `pre_repair_studies.zip`, `lean_review\arms\A0\`, `event_levels\local\C\`, `tour_pooling\borrow_sim*\` and `fits\split__*`, `rating_systems\stageA_ttt_hold.parquet`, `predictability_diagnostic\audit4\lag_features.parquet`, `rg_first_serve_recount`'s `candidate_corrections\`, superseded rounds and `*_v1` files (until the correction is applied), `surface_elo_pieces\audit_scratch\*.py` (the audit's numbers come from them), `infosys_atp_backfill\replaced\`, `career_coverage\…\superseded\`, `gap_downloads\…superseded_perspective_ids.csv` (that study is active today), `data\dump\points\wta\*.parquet` of 24 Sep (review scripts still read them) | 0.38 GB | |
| `daily_prediction\runs\` replays and test runs | 0.01 GB | Tiny; this study's README cites some of them |
| `docs\research\legacy-one-shot\CLAUDE.md` | 5 KB | Rename it (e.g. `LEGACY_CLAUDE.md`): a file named CLAUDE.md can be loaded as instructions (eedac0ed, 6 Oct) |

## Keep: looks like a candidate, but is needed

| Item | Size | Why |
|---|---:|---|
| `C:\Users\zerom\tnr_lyr_new` | 23.7 GB | The current template's build tree: the daily pipeline and its tests read it |
| `C:\Users\zerom\tnr_dump_freeze` | 15 MB | The 8 Oct freeze of Tennis My Life: replays read it |
| `data\studies\daily_prediction\state\` | 58.3 GB | TabPFN's training caches (the 13-minute fit is 1.4 minutes because of them; they rebuild by themselves in about 12 minutes if you ever need the space) and the two checkpoints |
| `data\studies\current_best_model\{reference_2026-10-08, pinnacle_first_2026-10-09, template_2026-10-10, level_layer_2026-10-10}\` | about 2 GB | The frozen reference, the holdback control, the current template, the layer's harm-check arm |
| `data\studies\data_continuity\rebuilds\*\replaced\` | 0.77 GB | The only copy of the 30 Sep tables; the corrupt-data decision's restore point |
| `model_rebuild\`, `surface_rating_race\model\` and `local\model__*`, `feature_interactions\local\model__*`, `lean_review\arms\A2\`, `lower_level_evidence\system\{SYS,SYS_BOTH,strength,validated_src,stage0\C0_now}\` | about 0.9 GB | Read by current code, tests or decisions (the previous model, the template's input list, the adopted layer) |
| `data\raw`, `data\dump`, `predictions\`, `AGENTS.md` | — | Raw data; real predictions; AGENTS.md points other tools to CLAUDE.md |

## How to delete safely

When you decide, tell me which groups and I'll do them in this order. These steps are what I would run. (Steps 1-3
and the "delete now" groups ran on 11 Oct, through `src\eda\cleanup_inventory\delete_now.py`: see
[What was deleted](#what-was-deleted-11-oct-2026).)

1. **Stop the leftover processes:** `Stop-Process -Id 53808, 41588, 37948, 24472`.
2. **Sandboxes: remove their junctions first, then delete.** The project's own cleanup commands do both and check
   that no link is left:
   * `tnr_live`, `tnr_live2`, `tnr_live3`: `PREDICTION_RUN_SANDBOX=C:/Users/zerom/<name> ./python.sh src/eda/prediction_run/run.py --cleanup`.
   * `tnr_sys1`–`tnr_sys5`, `tnr_sys_ios` (and later `tnr_lle`, `tnr_lyr_off`, `tnr_lyr_on`, `tnr_sb_rg_candidate`):
     `MODEL_REBUILD_SANDBOX=C:/Users/zerom/<name> ./python.sh src/eda/model_rebuild/run_chain.py --cleanup`.
   * **`tnr_lyr_rp` by hand.** Run `cmd /c rmdir "<junction>"` (no `/s`) on each of its 10 junctions:
     * `data\raw`;
     * `data\dump\{odds,players,points,rankings}`;
     * `data\dump\matches\{live_tennis_api_zenodo,mantennisdata,open_tennis_data,sackmann_archive,tennis_my_life}`.

     The last one points into `tnr_dump_freeze`, which must stay. Then check that
     `Get-ChildItem C:\Users\zerom\tnr_lyr_rp -Recurse -Force -Attributes ReparsePoint` returns nothing, and only then
     delete the folder.
   * **Never use** `rm -rf`, `du`, or Windows PowerShell 5.1's `Remove-Item -Recurse` on a sandbox before its
     junctions are gone.
3. **The backup zips:** delete the three `.zip` files only; keep `manifest.csv.gz`, `summary.json` and the README.
4. **The locked folders:** as administrator, `takeown /f <folder> /r /d y` and `icacls <folder> /grant zerom:F /t`,
   then delete.
5. **Files tracked in git** (the root `explore*.csv`, `controls_full.json` and `nearest_final.json`, a few study
   files): remove them with `git rm`. They show as deletions in your next commit.
6. **Docs to touch afterwards:**
   * `data\LARGE_FILES.md` and `.gitignore`: remove the lines for the deleted files;
   * study READMEs that cite deleted files: `surface_ios`, `surface_rating_race`, `point_sequence`,
     `polymarket_sharp_money`, `predictive_frontier_tabpfn`.

**What cannot be undone:** most `data\studies` items made after 8 Oct are in no backup and not in git. Deleting them
is final. Their results stay in the records named above.

## Also noticed

* **Session transcripts expire.** Claude Code deletes session transcripts after 30 days by default, so those from
  22 Sep go about 22 Oct. They hold the record of what past sessions proposed. To keep them, set `cleanupPeriodDays`
  (cdb42571 recommended this; no reply).
* **Not this project:** home-folder items that look like they belong to other work. `C:\Users\zerom\checkpoints`
  (335 MB of pose-estimation weights, 2025), `feature_generation_hpo` and `orig_recover.py` (UFC), and a file named
  `=2.0` (output of a mistyped conda install).
* **Measurement:** sizes were measured without following junctions (robocopy `/XJ`, or file listings that skip
  links). References were found by searching for names and paths, so a path built at run time could be missed. The
  subagents' claims that decide the largest items were checked (process log): the bucket copies, the code that reads
  the four "one step first" sandboxes, the readers of `surface_ios\uploads`, and the leftover processes.
