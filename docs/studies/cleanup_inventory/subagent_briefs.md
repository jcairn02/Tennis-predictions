# Subagent briefs, verbatim (11 Oct 2026, launched about 16:52 PDT)

Four read-only Explore subagents, launched in parallel by session `d2d2331e-b87f-42fd-baa1-b5c3ddebe82c`. Process log:
[process_log.md](process_log.md).

## 1. Past cleanup proposals

You are surveying the Tennis-predictions repository (C:\Users\zerom\Documents\Tennis-predictions) for a cleanup inventory the owner asked for on 11 Oct 2026: "For the past week, find all studies/data or models that are artifacts, no longer useful, scratch pads or tests that we've done. Everything that past models proposed we clean up but I didn't. List it all and segment it into highly recommend cleans/deletion and optional (most should be highly if done properly)."

STRICTLY READ-ONLY. Do not delete, move, rename, write or modify any file or folder. Do not run git commands that change state, builds, tests or downloads. Only list, read, search and measure.

DANGER, JUNCTIONS: the sandbox folders C:\Users\zerom\tnr_* and work trees contain Windows junctions (folder links) into the repository's real data (data\raw, data\dump and the folders under data\dump\matches). Never run `du` or any recursive walk that follows them. To measure a folder's size use `robocopy "<folder>" NULL /L /S /XJ /NFL /NDL /NJH /BYTES /R:0 /W:0` (cmd or PowerShell) and read the Bytes total (/XJ skips junctions), or PowerShell `Get-ChildItem -LiteralPath <p> -Recurse -Force -Attributes !ReparsePoint -File | Measure-Object Length -Sum`.

YOUR AREA: what past Claude sessions proposed to clean up, and whether the owner did it.
Sources:
(a) The session transcripts in C:\Users\zerom\.claude\projects\c--Users-zerom-Documents-Tennis-predictions\*.jsonl (94 files, 1.2 GB, one JSON object per line). Assistant turns have "type": "assistant" with message.content items of type "text"; user turns have "type": "user". Use a read-only Python script run with C:/Users/zerom/miniforge3/envs/tennis/python.exe; stream the files line by line (some are 20-46 MB). Restrict to sessions with activity from 2026-10-02 on (the "timestamp" field). Extract assistant text that proposes deleting, cleaning or removing files or folders. Keywords: delete, deletion, clean up, cleanup, remove, prune, safe to delete, can be deleted, no longer needed, leftover, left on disk, not deleted, obsolete, superseded, scratch, temporary, stale, discard, free up, disk space, sandbox. Also extract the owner's replies to such proposals, to see whether the owner approved, declined or ignored them. Note the project rule "Do not delete temporary files mid-session; discuss cleanup before deletion": many sessions left files and named them in their final report. Those are prime targets.
(b) The repository's docs: docs/**/process_log.md, docs/**/README.md, docs/studies/README.md, docs/roadmap.md, data/README.md, data/TODO.md, data/LARGE_FILES.md: sentences that propose cleanup or name leftovers (e.g. "left on disk", "not deleted", "can be deleted", "superseded", "scratch").
For each proposal: the paths; who proposed it (session id and date, or document and line); why; the owner's response if any; whether it still exists now (check the path); and its current size (safe method above). Deduplicate proposals that name the same paths.

CLASSIFY each still-existing item:
- HIGH (highly recommend deleting or cleaning): regenerable or redundant, and nothing current depends on it. Examples: test-run outputs whose results are recorded elsewhere, dry runs, retries superseded by a final run, scratch files, aborted or failed runs, duplicate copies, sandbox copies whose outputs were copied out, caches, root-level strays nobody references.
- OPTIONAL: low but non-zero value. Examples: superseded outputs a README still cites as evidence, intermediate tables that take hours to rebuild, backups of replaced tables (rollback insurance), old instances kept as evidence.
- KEEP (list briefly with the reason): anything that one of these depends on: the current best model, a decision (docs/decisions/), CLAUDE.md, the daily prediction pipeline (src/eda/daily_prediction, data/studies/daily_prediction), the frozen reference (data/studies/current_best_model/reference_2026-10-08), the Pinnacle-first instance (the holdback control), the current template (data/studies/current_best_model/template_2026-10-10 and its build tree C:\Users\zerom\tnr_lyr_new), the freeze view C:\Users\zerom\tnr_dump_freeze, raw data (data/raw, data/dump), or a current test.
Before calling something unreferenced, Grep for its path or name in src/, test/, docs/, config/, CLAUDE.md, AGENTS.md, data/*.md, data/*.yaml and data/studies/**/*.json.

REPORT. Your final message is the only thing returned to me. Give a table per class with these columns:
- full path;
- size;
- what it is;
- proposed by (session id and date, or document);
- the owner's response;
- evidence of references or none found;
- a one-line reason.
Sum the sizes per class. Be precise: measure, do not guess, and say what you could not check.

## 2. Studies A to L

You are surveying the Tennis-predictions repository (C:\Users\zerom\Documents\Tennis-predictions) for a cleanup inventory the owner asked for on 11 Oct 2026: "For the past week, find all studies/data or models that are artifacts, no longer useful, scratch pads or tests that we've done. Everything that past models proposed we clean up but I didn't. List it all and segment it into highly recommend cleans/deletion and optional (most should be highly if done properly)."

STRICTLY READ-ONLY. Do not delete, move, rename, write or modify any file or folder. Do not run git commands that change state, builds or tests. Only list, read, search and measure. Never follow Windows junctions. To measure sizes use `robocopy "<folder>" NULL /L /S /XJ /NFL /NDL /NJH /BYTES /R:0 /W:0` (read the Bytes total), or PowerShell `Get-ChildItem -LiteralPath <p> -Recurse -Force -Attributes !ReparsePoint -File | Measure-Object Length -Sum`. Some folders under data/studies deny access (e.g. feature_alpha_audit/pytest_original_retry_20261002): report them as access denied, with what you can see.

YOUR AREA: the study output folders data/studies/<study> whose names start with A to L. Sizes measured today:
adoption_framework 477K, ao_rg_points 1.4M, atp_pipeline_handoff 1.2M, bet_timing 465M, betonline_lines 436K, career_coverage 7.1M, close_drift 20K, current_best_model 1.9G, daily_update_speed 22K, data_continuity 754M, data_map 14M, event_levels 511M, feature_alpha_audit 218M, feature_interactions 425M, feature_provenance 6.6M, feature_universe 326M, gap_downloads 26M, gap_sources 5.1M, granular_data_leads 3.8M, indoor_fill 63M, infosys_atp_backfill 6.6M, input_data_audit 54M, ios_constants 24K, ios_product_centring 130M, lean_review 223M, level_layer_adoption 381M, line_sharpening 314M, lower_level_evidence 2.3G.
(Skip data/studies/daily_prediction: another reviewer covers it.)

For each study:
1. Its status, from docs/studies/<study>/README.md and its process log: active; evidence for a decision in docs/decisions/; superseded; rejected; abandoned; or finished and only historical.
2. Inside it, the sub-folders and files that are artifacts. Look for test runs, scratch, dry runs, retries, rejected candidates, sandbox copies, logs, temporary or superseded outputs: names like pytest_*, *dry_run*, *retry*, *candidate*, tmp, temp, scratch, full_runs, sandbox, backup, old, superseded versions, large logs. Give each its size and modification date; focus on items from 2026-10-04 on, but include older test or scratch outputs too, with their dates.
3. Whether each is referenced: Grep for the path or name in src/, test/, docs/ (especially the study's own README claims and decisions), config/, CLAUDE.md, data/*.yaml and data/studies/**/*.json.
current_best_model holds the frozen reference (reference_2026-10-08), the Pinnacle-first instance (pinnacle_first_2026-10-09, the holdback control) and the current template (template_2026-10-10); these are KEEP. List any other instances, candidates or comparison folders inside it and judge them.

CLASSIFY each candidate:
- HIGH (highly recommend deleting or cleaning): regenerable or redundant, and nothing current depends on it. Examples: test-run outputs whose results are recorded elsewhere, dry runs, retries superseded by a final run, scratch, aborted or failed runs, duplicate copies, superseded candidates whose verdict is recorded, caches.
- OPTIONAL: low but non-zero value. Examples: superseded outputs a README still cites as evidence, intermediate tables that take hours to rebuild, backups of replaced tables, old instances kept as evidence.
- KEEP: anything that one of these depends on: the current best model, a decision, CLAUDE.md, the daily prediction pipeline, raw data, an active study, or a current test. Give a one-line reason.

REPORT. Your final message is the only thing returned to me:
1. Per study, one line: size, status, artifacts found (or none).
2. A table of candidates with these columns: full path; size; what it is and who made it (study, date); references found or none; class (HIGH / OPTIONAL / KEEP); a one-line reason.
3. Totals per class.
Be precise: measure, do not guess, and say what you could not check.

## 3. Studies M to Z

You are surveying the Tennis-predictions repository (C:\Users\zerom\Documents\Tennis-predictions) for a cleanup inventory the owner asked for on 11 Oct 2026: "For the past week, find all studies/data or models that are artifacts, no longer useful, scratch pads or tests that we've done. Everything that past models proposed we clean up but I didn't. List it all and segment it into highly recommend cleans/deletion and optional (most should be highly if done properly)."

STRICTLY READ-ONLY. Do not delete, move, rename, write or modify any file or folder. Do not run git commands that change state, builds or tests. Only list, read, search and measure. Never follow Windows junctions. To measure sizes use `robocopy "<folder>" NULL /L /S /XJ /NFL /NDL /NJH /BYTES /R:0 /W:0` (read the Bytes total), or PowerShell `Get-ChildItem -LiteralPath <p> -Recurse -Force -Attributes !ReparsePoint -File | Measure-Object Length -Sum`. Some folders under data/studies deny access (e.g. data/studies/predictive_frontier_tabpfn/pytest_*): report them as access denied, with what you can see (name, date).

YOUR AREA: the study output folders data/studies/<study> whose names start with M to Z. Sizes measured today:
market_anchoring 44M, master_pipeline 168K (another session's active work: KEEP, just note it), match_timing 391M, merge_feasibility 56K, meta_stack 114M, model_rebuild 61M, odds_sources 29M, official_point_feeds 20M, pair_strength 70M, pinnacle_first 180K, point_sequence 479M, point_shot_sources 5.4M, polymarket_sharp_money 2.5G, predictability_diagnostic 506M, prediction_pipeline 160K, prediction_run 100M, predictive_frontier 31M, predictive_frontier_tabpfn 84M, public_data_dump 2.3M, rating_systems 250M, rg_first_serve_recount 150M, serve_speed_acquisition 4.4M, serve_speed_sources 1.2M, serve_speed_tabpfn 305M, sharp_benchmark 6.9M, shot_level 495M, surface_elo_pieces 172M, surface_ios 6.7G, surface_rating_race 358M, tabpfn_leakproof 36M, tabpfn_local 2.7M, tabpfn_thinking 168M, tabpfn_thinking58 45M, tennis_data_audit 410M, tour_pooling 234M, training_window 124M, ufc_ideas 975M.

For each study:
1. Its status, from docs/studies/<study>/README.md and its process log: active; evidence for a decision in docs/decisions/; superseded; rejected; abandoned; or finished and only historical.
2. Inside it, the sub-folders and files that are artifacts. Look for test runs, scratch, dry runs, retries, rejected candidates, sandbox copies, logs, temporary or superseded outputs: names like pytest_*, *dry_run*, *retry*, *candidate*, tmp, temp, scratch, full_runs, sandbox, backup, old, superseded versions, large logs. Give each its size and modification date; focus on items from 2026-10-04 on, but include older test or scratch outputs too, with their dates.
3. Whether each is referenced: Grep for the path or name in src/, test/, docs/, config/, CLAUDE.md, data/*.yaml and data/studies/**/*.json.
Notes:
- surface_ios (6.7 GB) is large: find what dominates it and whether those files are needed. The current best model uses surface IOS profile runs, so check which runs the decisions name.
- Per CLAUDE.md, surface_rating_race/model/ is "the previous model, kept as evidence": OPTIONAL at most.
- predictability_diagnostic holds the repository's Stage 0 and Stage 1 tables: KEEP those.
- match_timing/timing.parquet is the decided match clock: KEEP.
- serve_speed_tabpfn/live holds the live speed panel: KEEP.

CLASSIFY each candidate:
- HIGH (highly recommend deleting or cleaning): regenerable or redundant, and nothing current depends on it. Examples: test-run outputs whose results are recorded elsewhere, dry runs, retries superseded by a final run, scratch, aborted or failed runs, duplicate copies, superseded candidates whose verdict is recorded, caches.
- OPTIONAL: low but non-zero value. Examples: superseded outputs a README still cites as evidence, intermediate tables that take hours to rebuild, backups, old instances kept as evidence.
- KEEP: anything that one of these depends on: the current best model, a decision, CLAUDE.md, the daily prediction pipeline, raw data, an active study, or a current test. Give a one-line reason.

REPORT. Your final message is the only thing returned to me:
1. Per study, one line: size, status, artifacts found (or none).
2. A table of candidates with these columns: full path; size; what it is and who made it (study, date); references found or none; class (HIGH / OPTIONAL / KEEP); a one-line reason.
3. Totals per class.
Be precise: measure, do not guess, and say what you could not check.

## 4. Sandboxes, strays, backups, temporary folders, scratch code

You are surveying the Tennis-predictions project (repository C:\Users\zerom\Documents\Tennis-predictions) for a cleanup inventory the owner asked for on 11 Oct 2026: "For the past week, find all studies/data or models that are artifacts, no longer useful, scratch pads or tests that we've done. Everything that past models proposed we clean up but I didn't. List it all and segment it into highly recommend cleans/deletion and optional (most should be highly if done properly)."

STRICTLY READ-ONLY. Do not delete, move, rename, write or modify any file or folder. Do not run git commands that change state, builds or tests. Only list, read, search and measure.

DANGER, JUNCTIONS: the sandboxes C:\Users\zerom\tnr_* contain Windows junctions (folder links) into the repository's real data (data\raw, data\dump and the folders under data\dump\matches). A recursive delete or `du` that follows them would touch or count the real data. Never run `du` on them. To measure sizes use `robocopy "<folder>" NULL /L /S /XJ /NFL /NDL /NJH /BYTES /R:0 /W:0` (cmd or PowerShell; read the Bytes total; /XJ skips junctions). To list junctions use PowerShell `Get-ChildItem -LiteralPath <p> -Recurse -Depth 4 -Force -Attributes ReparsePoint | Select FullName, Target`.

YOUR AREA: six parts.
1. The 16 sandboxes in C:\Users\zerom: tnr_dump_freeze, tnr_live, tnr_live2, tnr_live3, tnr_lle, tnr_lyr_new, tnr_lyr_off, tnr_lyr_on, tnr_lyr_rp, tnr_sb_rg_candidate, tnr_sys1 to tnr_sys5, tnr_sys_ios. They were made 8-10 Oct 2026. For each:
   - its size without junctions, and its junctions with their targets;
   - which study or session made it and why: marker files (.prediction_run_sandbox, LLE_SYSTEM.json, freeze_dump.json), its logs/ folder, and the docs/studies/*/process_log.md and README.md that mention it (Grep for "tnr_<name>");
   - whether its results were copied into data/studies (cite the record);
   - whether any code, config, decision or test still points at it: Grep for "tnr_" in src/, test/, docs/decisions/, config/, CLAUDE.md, AGENTS.md and data/studies/**/*.json.
   Known: tnr_lyr_new is the current template's build tree (the daily pipeline's default DP_BASE_TREE, read by its tests) and tnr_dump_freeze is the frozen Tennis My Life view used by replays. Both are KEEP unless you find otherwise.
2. Root-level strays in the repository: explore1.csv to explore5.csv, panel_noresult.parquet, controls_full.json, nearest_final.json; and AGENTS.md (is it a duplicate of CLAUDE.md?). For each: size, date, who made it (Grep src/ and docs/ for the name), and whether anything references it.
3. data/backups (21 GB): every item; what it backs up (e.g. src/eda/data_continuity/rebuild_stage0.py keeps every file it replaces); its date; whether a newer version replaced it; its size.
4. Temporary and test areas:
   - C:\Users\zerom\AppData\Local\Temp\pytest-of-zerom (pytest's temporary folders): size and dates;
   - C:\Users\zerom\AppData\Local\Temp\claude\ (session scratchpads): size per project folder;
   - __pycache__ and .pytest_cache folders inside the repository: count and total size;
   - any *.part, *.tmp or .tmp.* files inside the repository.
5. Home-folder strays from this project in the past week (e.g. C:\Users\zerom\skrub_data, made 2026-10-06). Also check what C:\Users\zerom\checkpoints, feature_generation_hpo, orig_recover.py and the file named "=2.0" are, with their dates. Include them only if this project's sessions made them in the window, or they clearly belong to this project; otherwise say they look unrelated.
6. Scratch code made from 2026-10-04 on, in scripts/ (notebooks) and src/: one-off checks, recon, debug, dry runs, temporary probes (names like scratch, check_, tmp_, dry_run, recon, debug, probe). Say whether a README's reproduction section cites each. Code is small, so give it OPTIONAL unless clearly dead.

CLASSIFY each candidate:
- HIGH (highly recommend deleting or cleaning): regenerable or redundant, and nothing current depends on it. Examples: sandboxes whose outputs were copied out and that no code or config points at, test-run temp folders, caches, root strays nobody references, failed or aborted runs.
- OPTIONAL: low but non-zero value. Examples: backups of replaced tables (rollback insurance), sandboxes a README still cites as the place a result was built (evidence), scratch code a reproduction section cites.
- KEEP: give a one-line reason.

REPORT. Your final message is the only thing returned to me: one table per part with these columns: full path; size; date; what it is and who made it; references found or none; class (HIGH / OPTIONAL / KEEP); a one-line reason. Then totals per class. For every sandbox you mark HIGH, add a SAFE DELETION NOTE listing its junctions: they must be removed with `cmd /c rmdir <junction>` (no /s) before the tree is deleted, because a recursive delete that follows a junction would delete the real data. Be precise: measure, do not guess, and say what you could not check.

# Subagent briefs, verbatim (13-14 Oct 2026)

Four read-only general-purpose subagents, launched by session `428558ac-970b-47cf-a90b-f769d4c9a79f`: §§ 5-6 in
parallel on 13 Oct at about 22:05 PDT (the commit check), §§ 7-8 in parallel on 14 Oct at about 07:17 PDT (rows for
`data/LARGE_FILES.md`). Process log: [process_log.md](process_log.md) § 8.

## 5. Study leftovers A (13 Oct)

You are helping audit the Tennis-predictions repository (C:\Users\zerom\Documents\Tennis-predictions, Windows 11; Git Bash and PowerShell available; always use absolute paths) before the owner commits and pushes to GitHub. Your job: classify study outputs in your assigned folders as cleanup candidates or not.

**Strictly read-only.** Do not delete, move, rename or edit any file. No git command that changes state (git status / ls-files / log / diff / ls-tree are fine). Do not run project builds, tests or scripts. If you need scratch files, write them only under C:\Users\zerom\AppData\Local\Temp\claude\c--Users-zerom-Documents-Tennis-predictions\428558ac-970b-47cf-a90b-f769d4c9a79f\scratchpad\agentA\ .

**Baseline.** A full cleanup inventory was made on 11 Oct 2026, and its "delete now" group was deleted at 17:54–17:59 that day. Read docs/studies/cleanup_inventory/README.md and process_log.md § 6 first. It put items in: deleted; "held back"; "highly recommended once one small step is done"; "optional"; "keep". Do not re-argue its verdicts without new evidence. Your job is the delta:
1. For every item of that inventory inside your folders that still exists (held back, one-step, optional, keep), check whether its situation changed since 11 Oct 18:00 PDT: is the blocking step now done (decisions in docs/decisions/ dated 2026-10-10 to 2026-10-13; ticked checklists in the study's README or process_log; new code)? Did a new reader appear, or did its reader go away? Then re-class it.
2. Classify every file or folder in your folders created or changed after 2026-10-11 18:00 PDT.
3. Report byte-identical duplicates within your folders (hash files over 1 MB with sha256sum; say which copy code reads).

**Your folders** (under data/studies/), with their code in src/eda/<same name>/ and docs in docs/studies/<same name>/:
lower_level_evidence (2,505 untracked files, the biggest), level_layer_adoption, current_best_model, data_gaps_2026, edge_anatomy, event_levels, indoor_fill, input_data_audit (also the untracked src/eda/input_data_audit/review/ folder, 101 files: scratch review scripts or real code?), ios_product_centring, lean_review.

**Classes** (as on 11 Oct):
- HIGH: no current code, test, notebook, decision or open checklist item reads it; its result or verdict is recorded elsewhere (name where); rebuildable or superseded.
- ONE-STEP: would be HIGH after one named step (name the step and what it waits on).
- OPTIONAL: some evidential value (a decision or README cites it; not rebuildable as it was) but nothing runs on it.
- KEEP: read by current code, tests, the pipeline or the master notebook (scripts/master_pipeline.ipynb, src/pipeline/), named by a decision or CLAUDE.md, or IN USE TONIGHT.

**Tonight the repository is being written by other sessions** (13 Oct 2026, now about 22:00 PDT):
- a Stage 0 rebuild applying the Roland Garros correction (rg_first_serve_recount/adopt.py --apply, then data_continuity/rebuild_stage0.py, started about 21:15, about 30 minutes);
- a new template build (src/eda/model_rebuild/run_chain.py --setup, started 21:53; data/studies/current_best_model/template_2026-10-14/ just appeared);
- the box-score gate review's replay (box_score_gate_review/replay_gaps.py, work tree C:/Users/zerom/tnr_gate_review);
- the lower-level feed and its harm check (data_gaps_2026): at 20:41 the daily pipeline was pointed at template_2026-10-13, whose build tree is C:/Users/zerom/tnr_gaps (see docs/studies/data_gaps_2026/process_log.md around lines 146–261);
- unpriced_leads step 3, and two scrapers.
Anything written in the last 6 hours, or by a running process, is KEEP ("in use tonight"), whatever it looks like. Note which template instance is now current, and whether template_2026-10-10 / pinnacle_first_2026-10-09 / level_layer_2026-10-10 / reference_2026-10-08 are still named as the frozen reference, the holdback control, or the previous template by CLAUDE.md, the decisions or code.

**How to check readers:** grep src/, test/, scripts/ (including the notebook), src/pipeline/, docs/decisions/ and CLAUDE.md for the folder or file name, and for path pieces a script might join at run time (the parent folder plus a glob or f-string). Read each hit's line to tell a reader from a writer, from a test that builds its own tmp copy, and from a doc mention. Give evidence as file:line. A name found only in the item's own finished study is not a reader. The reader check of 11 Oct is in data/studies/cleanup_inventory/deletions_2026-10-11_readers.txt.

**Commit context:** git tracks nothing written since 8 Oct (last commit 677a63f, 8 Oct 10:18). .gitignore ignores *.parquet, *.duckdb, archives in data/, data/raw/, data/dump/ and a few named paths; .npz, .csv, .json and .log files are committed unless ignored. Untracked .npz fits (TabPFN outputs per season and seed, stored uncompressed) are 1.3 GB of the 1.7 GB the commit would add. For every untracked item, say: commit, gitignore (keep local), or delete.

Measure sizes with stat or du -b on files. No folder in data/studies should be a junction; if you meet a reparse point, do not follow it, report it.

**Return** (at most 1,200 words plus the table):
- A table, one row per item (group rows where many files share a verdict): path relative to data/studies, files, MB, git state (untracked / tracked / ignored / mixed), class, reason with evidence (file:line or doc), and for untracked items commit / gitignore / delete.
- Totals per class (files, MB).
- Duplicates found.
- Anything you could not check.
- The single claim in your report you are least sure of, and why.

## 6. Study leftovers B (13 Oct)

You are helping audit the Tennis-predictions repository (C:\Users\zerom\Documents\Tennis-predictions, Windows 11; Git Bash and PowerShell available; always use absolute paths) before the owner commits and pushes to GitHub. Your job: classify study outputs in your assigned folders as cleanup candidates or not.

**Strictly read-only.** Do not delete, move, rename or edit any file. No git command that changes state (git status / ls-files / log / diff / ls-tree are fine). Do not run project builds, tests or scripts. If you need scratch files, write them only under C:\Users\zerom\AppData\Local\Temp\claude\c--Users-zerom-Documents-Tennis-predictions\428558ac-970b-47cf-a90b-f769d4c9a79f\scratchpad\agentB\ .

**Baseline.** A full cleanup inventory was made on 11 Oct 2026, and its "delete now" group was deleted at 17:54–17:59 that day. Read docs/studies/cleanup_inventory/README.md and process_log.md § 6 first. It put items in: deleted; "held back"; "highly recommended once one small step is done"; "optional"; "keep". Do not re-argue its verdicts without new evidence. Your job is the delta:
1. For every item of that inventory inside your folders that still exists (held back, one-step, optional, keep), check whether its situation changed since 11 Oct 18:00 PDT: is the blocking step now done (decisions in docs/decisions/ dated 2026-10-10 to 2026-10-13; ticked checklists in the study's README or process_log; new code)? Did a new reader appear, or did its reader go away? Then re-class it.
2. Classify every file or folder in your folders created or changed after 2026-10-11 18:00 PDT.
3. Report byte-identical duplicates within your folders (hash files over 1 MB with sha256sum; say which copy code reads).

**Your folders** (under data/studies/), with their code in src/eda/<same name>/ and docs in docs/studies/<same name>/:
daily_prediction (855 untracked files: runs/, logs/, stage0_speed/, layer_copies/ …; note its state/ folder of about 58 GB of TabPFN caches is ignored and was KEEP on 11 Oct: just confirm it is still read), rg_first_serve_recount (352 untracked, including followup/ 95 MB, review/, confirmed/, adoption/, and the untracked code folder src/eda/rg_first_serve_recount/review_followup/ with 82 files: scratch or real code?), prediction_run, unpriced_leads, tour_pooling, gap_downloads, model_rebuild, master_pipeline, bet_timing, infosys_atp_backfill, prediction_pipeline, data_continuity, adoption_framework, feature_provenance, odds_sources, box_score_gate_review, training_window, daily_update_speed, official_point_feeds, tml_revisions, ios_constants, serve_speed_acquisition, close_drift, cleanup_inventory, pinnacle_first, serve_speed_tabpfn, public_data_dump.
Also, quickly: the 11 Oct "optional" items in folders with no untracked files (ufc_ideas, surface_ios, surface_rating_race, serve_speed_tabpfn local/design, feature_interactions round1, point_sequence, tabpfn_thinking58, rating_systems, predictability_diagnostic audit4, feature_alpha_audit, career_coverage): do they still exist, and did anything change for them? One line each is enough.
Also two strays:
- The folder patterns_replay_2026-07-13_R16/ at the REPOSITORY ROOT (32 files, written 18:21–21:10 tonight; its newest file is reprice_2026-10-14T041012Z.csv). Compare it with data/studies/daily_prediction/runs/patterns_replay_livedating_2026-07-13_R16/, and read docs/studies/unpriced_leads/process_log.md around "13 Oct 18:00–18:35" and src/eda/unpriced_leads/. What wrote it, why at the root, is it a duplicate, and is a session still writing it?
- data/TODO.md (untracked): a note to keep, or scratch?

**Classes** (as on 11 Oct):
- HIGH: no current code, test, notebook, decision or open checklist item reads it; its result or verdict is recorded elsewhere (name where); rebuildable or superseded.
- ONE-STEP: would be HIGH after one named step (name the step and what it waits on).
- OPTIONAL: some evidential value (a decision or README cites it; not rebuildable as it was) but nothing runs on it.
- KEEP: read by current code, tests, the pipeline or the master notebook (scripts/master_pipeline.ipynb, src/pipeline/), named by a decision or CLAUDE.md, or IN USE TONIGHT.

**Tonight the repository is being written by other sessions** (13 Oct 2026, now about 22:00 PDT):
- a Stage 0 rebuild applying the Roland Garros correction (rg_first_serve_recount/adopt.py --apply, then data_continuity/rebuild_stage0.py, started about 21:15, about 30 minutes; see docs/studies/tml_revisions/process_log.md around line 146);
- a new template build (src/eda/model_rebuild/run_chain.py --setup, started 21:53; data/studies/current_best_model/template_2026-10-14/ just appeared);
- the box-score gate review's replay (src/eda/box_score_gate_review/replay_gaps.py running now, calling daily_prediction/dp.py tables on data/studies/box_score_gate_review/replay/base; work tree C:/Users/zerom/tnr_gate_review);
- the lower-level feed and its harm check (data_gaps_2026): at 20:41 the daily pipeline was pointed at template_2026-10-13, build tree C:/Users/zerom/tnr_gaps;
- unpriced_leads step 3, and two scrapers (src.ingest.point_sources.sofascore_editions and flashscore_points).
Anything written in the last 6 hours, or by a running process, is KEEP ("in use tonight"), whatever it looks like.

**How to check readers:** grep src/, test/, scripts/ (including the notebook), src/pipeline/, docs/decisions/ and CLAUDE.md for the folder or file name, and for path pieces a script might join at run time (the parent folder plus a glob or f-string). Read each hit's line to tell a reader from a writer, from a test that builds its own tmp copy, and from a doc mention. Give evidence as file:line. A name found only in the item's own finished study is not a reader. The reader check of 11 Oct is in data/studies/cleanup_inventory/deletions_2026-10-11_readers.txt.

**Commit context:** git tracks nothing written since 8 Oct (last commit 677a63f, 8 Oct 10:18). .gitignore ignores *.parquet, *.duckdb, archives in data/, data/raw/, data/dump/ and a few named paths; .npz, .csv, .json and .log files are committed unless ignored. For every untracked item, say: commit, gitignore (keep local), or delete. Run folders full of logs are fine to commit if they are records a README cites; say so when they are not.

Measure sizes with stat or du -b on files. No folder in data/studies should be a junction; if you meet a reparse point, do not follow it, report it.

**Return** (at most 1,200 words plus the table):
- A table, one row per item (group rows where many files share a verdict): path relative to data/studies (or the repository root for the strays), files, MB, git state (untracked / tracked / ignored / mixed), class, reason with evidence (file:line or doc), and for untracked items commit / gitignore / delete.
- Totals per class (files, MB).
- Duplicates found.
- Anything you could not check.
- The single claim in your report you are least sure of, and why.

## 7. Rows for the large-files guide: raw downloads and staged tables (14 Oct)

You are researching rows for the repository's guide to files over 50 MB, `data/LARGE_FILES.md`, in C:\Users\zerom\Documents\Tennis-predictions (Windows 11; Git Bash and PowerShell; use absolute paths). Read that guide first: its table has the columns File | Size | What it is | Way back | Exact copy?, and its sections show the house style (plain words, exact commands run from the repository root with `./python.sh`, rough run times, and whether the result is an exact copy).

**Strictly read-only.** Do not edit, move or delete anything; no state-changing git command; do not run scripts, downloads or builds. Scratch files only under C:\Users\zerom\AppData\Local\Temp\claude\c--Users-zerom-Documents-Tennis-predictions\428558ac-970b-47cf-a90b-f769d4c9a79f\scratchpad\agentC\ .

**Your items** (sizes in decimal MB, measured 14 Oct 2026 07:10):
1. `data/dump/points/tennislive/listed.parquet` (71.6 MB, written 13 Oct 16:58).
2. `data/dump/points/wta/events/2024.parquet`, `2025.parquet`, `2026.parquet` (50.4, 58.5, 56.5 MB).
3. `data/raw/gap_sources/bwandowando/matches.csv` (278.5 MB) and `data/raw/gap_sources/marcosjn2/atp-matches.jsonl`, `wta-matches.jsonl` (145.0, 118.5 MB), all written 29 Sep.
4. `data/raw/point_sources/sofascore_editions/_receipts.jsonl` (57.9 MB, still growing) and `data/raw/point_sources/wta/_receipts.jsonl` (108.5 MB).
5. Existing rows that changed since the guide was written; for each, say when and why it changed, and which statements in the guide are now stale (row counts, checksums, request counts):
   - `data/dump/odds/polymarket/market_index.parquet`: the guide says 106.5 MB and 464,266 rows; it is now 119.7 MB.
   - `data/raw/public_dump/polymarket_prices/bodies/itf.jsonl.gz` (guide 72.2 MB, now 91.5 MB) and `challenger_125_inferred.jsonl.gz` (guide 50.5 MB, now 54.4 MB). The guide's Checksums section gives the 23 Sep bytes and SHA-256; are those files gone, replaced or extended? Check the receipts and run logs (`data/studies/public_data_dump/polymarket_runs.jsonl`, download_log.json) for later runs.
   - `data/raw/public_dump/polymarket_trades/` (guide 1.91 GB) and `data/dump/odds/polymarket/trades/` (guide 877 MB): measure their total sizes now (files only, `du -sb` is fine here: these folders hold no junctions).

**For each item, find:** what it is (one plain sentence: source, contents, rows if cheap to learn from a summary or receipt, not by loading big files); which script writes it (file:line) and which code reads it; the way back (the exact command from the repository root, from the adapter's docstring, README or the study's docs, and the rough time; whether it re-downloads or rebuilds offline); and whether the result is an exact copy (byte-identical, same rows, or not). For receipt logs, say whether they can be rebuilt at all, and what they record. Sources' licences or availability notes in the docs are worth one clause if relevant. Adapters live in src/ingest/ (point_sources/, gap_sources or similar); their docs in docs/research/ or docs/studies/ (e.g. data_gaps_2026, gap_downloads, official_point_feeds, gap_sources).

**Return:** one proposed table row per item (or per group, where several files share everything), in the guide's column format, ready to paste, with sizes as given above; under each row, the evidence (file:line) for each claim. Then the list of stale statements in the existing rows and sections, each with the corrected text you propose. Keep it under 1,000 words plus the rows. Mark anything you inferred rather than read.

## 8. Rows for the large-files guide: study tables, caches and copies (14 Oct)

You are researching rows for the repository's guide to files over 50 MB, `data/LARGE_FILES.md`, in C:\Users\zerom\Documents\Tennis-predictions (Windows 11; Git Bash and PowerShell; use absolute paths). Read that guide first: its table has the columns File | Size | What it is | Way back | Exact copy?, and its rows show the house style (plain words, exact commands run from the repository root with `./python.sh`, rough run times, and whether the result is an exact copy).

**Strictly read-only.** Do not edit, move or delete anything; no state-changing git command; do not run scripts or builds (a template build and other sessions are running). Scratch files only under C:\Users\zerom\AppData\Local\Temp\claude\c--Users-zerom-Documents-Tennis-predictions\428558ac-970b-47cf-a90b-f769d4c9a79f\scratchpad\agentD\ .

**Your items** (all under data/studies/; sizes in decimal MB, measured 14 Oct 2026 07:10):
1. `daily_prediction/state/`: per instance (`template_2026-10-10/`, `template_2026-10-13/`), 16 files `tabpfn/season2026/seed<N>/executor_state.joblib` of 3,617.5 MB each, and `<checkpoint>/forms/z.parquet` (about 85 MB) for checkpoints 2026-06-22 and 2026-09-21. The folder has its own `.gitignore`. What are the TabPFN caches and the checkpoints, who writes and reads them (src/eda/daily_prediction/, src/pipeline/), how each is rebuilt and how long it takes, and what happens if deleted (does the engine rebuild by itself?). Docs: docs/studies/daily_prediction/README.md, docs/studies/master_pipeline/README.md.
2. Copies of Stage 0 (`stage0_match_players.parquet`, about 62–65 MB) kept by runs: `daily_prediction/runs/live_2026-10-11_110150/stage0/`, `live_2026-10-13_163937/stage0/`, `live_2026-10-13_165316/stage0/`; `prediction_run/live_2026-10-09/stage0/`; `master_pipeline/data_check/stage0/`; `box_score_gate_review/replay/_stage0_after_tables/`. Why each run keeps one, who reads it, and whether it can be rebuilt (it reflects the live data at run time).
3. `current_best_model/reference_2026-10-08/frozen/`: `env/tabpfn-v3.5-20260909.safetensors` (876.0 MB), `tables/data/studies/predictability_diagnostic/stage0_match_players.parquet` (62.3), `tables_later/data/studies/match_timing/ios_features.parquet` (50.1) and `leakproof_features.parquet` (97.4). What the frozen copy is, its total size, whether and where it is backed up (the reference's README, data/backups/, gs://tennis-predictions-archive), how to restore it, and how `reference.py --verify` checks it.
4. `data_gaps_2026/feed/candidates/F20261013b/`, `F20261013c/`, `F20261013c_gaps/` (`stage0_match_players.parquet` 75.3, 75.3, 64.7 MB; the whole folder is about 630 MB). What they are, which is current (see `current_best_model/accepted_additions/accepted.json` "feeds"), and how `src/eda/data_gaps_2026/feed.py` rebuilds them. The .gitignore already describes them; give the guide row.
5. `lower_level_evidence/system/relationship/targets_dev_key.parquet` (79.0) and `lower_level_evidence/system/stage0/C0_now/`, `C0_pre/` `stage0_match_players.parquet` (75.4, 71.3).
6. `event_levels/frame.parquet` (71.9); `match_timing/ios_features.parquet` (50.2, rebuilt 13 Oct 21:30); `surface_elo_pieces/pieces.parquet` (86.9); `surface_ios/surface_features.parquet` (293.5); `surface_rating_race/ttt_offset.parquet` (63.3); `tabpfn_thinking/frame.parquet` (62.8); `unpriced_leads/candidates/luck/values.parquet` (86.1).
7. The existing row for `data_continuity/rebuilds/<stamp>/replaced/` says "366 MB (the rebuild of 6 Oct 2026, 2026-10-07T0005Z)". There are now more rebuilds (at least 2026-10-07T0005Z, one on 8 Oct, and 2026-10-14T0412Z from last night's Roland Garros application). For each: total size of its `replaced/` (`du -sb`; no junctions there), what it holds (its `rebuild.json`), and whether "None by rebuilding: copy them back from here" still holds.

**For each item, find:** what it is (one plain sentence); which script writes it (file:line) and which code reads it; the way back (the exact command from the repository root, the rough time, from the study README, process log or the script's docstring); and whether the result is an exact copy (same rows, deterministic, or not, e.g. because the tables changed since). Study docs are in docs/studies/<study>/.

**Return:** one proposed table row per item (or per group where files share everything), in the guide's column format, ready to paste, with sizes as given; under each row, the evidence (file:line) for each claim. Keep it under 1,200 words plus the rows. Mark anything you inferred rather than read.
