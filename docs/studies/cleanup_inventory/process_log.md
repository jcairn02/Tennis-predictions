# Cleanup inventory, 4-11 Oct 2026: process log

11 Oct 2026 (PDT), started 16:44 · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code) · Session
`d2d2331e-b87f-42fd-baa1-b5c3ddebe82c` (the daily prediction script's session, after its part 3) · Report:
[README.md](README.md) · For a future reviewer

## 1. The request

* **The owner's words, verbatim** (11 Oct 2026, about 16:40 PDT): "For the past week, find all studies/data or models
  that are artifacts, no longer useful, scratch pads or tests that we've done. / Everything that past models proposed
  we clean up but I didn't. / List it all and segment it into highly recommend cleans/deletion and optional (most should
  be highly if done properly)"
* **How it was read.**
  * **A list, not a cleanup:** nothing is deleted, moved or changed (the project's rule: discuss cleanup before deletion;
    this list is that discussion).
  * **"The past week":** made or changed from Sun 4 Oct 2026 on; older items only where a session proposed cleaning them.
  * **"Past models proposed":** what earlier Claude sessions proposed (their transcripts and the docs they wrote) and the
    owner did not act on.
  * **Two classes as asked** (highly recommended; optional), plus a short **keep** list where something looks like a
    candidate but is needed, so the owner sees why it is not in the first two.
  * **Scope:** the repository (`data/studies`, `data/backups`, root strays, caches, scratch code), the build sandboxes
    outside it (`C:/Users/zerom/tnr_*`), and the temporary folders this project's sessions wrote.
* **Plan.** Measure sizes; four read-only subagents in parallel (past proposals; studies A-L; studies M-Z; sandboxes,
  strays, backups, temporary folders and scratch code), briefs verbatim in [subagent_briefs.md](subagent_briefs.md);
  `data/studies/daily_prediction` done here; then check the subagents' claims that decide a class (references,
  sizes), and write the report.
* **The hazard named in every brief:** the sandboxes hold Windows junctions into the repository's real `data/raw` and
  `data/dump`; a recursive delete or measurement that follows them would touch the real data.

## 2. Chronology

| When | Step | Result |
|---|---|---|
| 16:44 | Repository layout; transcripts (94; by last change: 62 from 4 Oct on); `du` of `data/studies/*` and `data/backups` (the sandboxes' sizes left to robocopy without junctions) | `data/studies` about 80 GB (`daily_prediction` 55 GB, `surface_ios` 6.7, `polymarket_sharp_money` 2.5, `lower_level_evidence` 2.3, `current_best_model` 1.9); `data/backups` 21 GB; 16 sandboxes `tnr_*` made 8-10 Oct; root strays `explore1-5.csv`, `panel_noresult.parquet`, `controls_full.json`, `nearest_final.json` |
| 16:52 | Four subagents launched (briefs verbatim in `subagent_briefs.md`) | running |
| 16:55 | `data/studies/daily_prediction` measured (this session's own) | state 55 GB (TabPFN caches 54 GB, checkpoints 2026-06-22 and 2026-09-21, 178-180 MB each), stage0_speed 512 MB (six output copies of 86 MB from part 3's proof), runs 94 MB (the first live day 86 MB; replays and test runs under 1 MB each), checks/logs under 0.3 MB, tmp empty |
| 16:58 | (Time note: the rows above headed 16:52 and 16:55 were written at 16:58 by the clock; the launch was a few minutes earlier) | — |
| 17:18 | Subagent 1 (past proposals) returned: 52 proposals, 37 items still on disk; HIGH 22 items about 335.9 GB (12 build sandboxes about 309 GB: `tnr_lle`, `tnr_sys1-5`, `tnr_sys_ios`, `tnr_lyr_off/on/rp`, `tnr_live/2/3`, `tnr_sb_rg_candidate`; the 8 Oct backup's local zips 22.1 GB, recorded as uploaded to the archive bucket; session scratchpads 4.0 GB; verifier temp 0.5 GB; small study leftovers), plus 11 access-denied test folders of 2 Oct; OPTIONAL 12 items 0.30 GB; KEEP 6. The owner had answered 3 proposals (each "delete", done). **Free disk 128.7 GB, below the 130 GB the master notebook's `train.py` requires for a new instance build.** Also: two `bash` processes of session d061329f polling since 10 Oct; transcript retention unset (22 Sep transcripts due for automatic deletion about 22 Oct) | To check before the report: the largest items' claims (sandbox outputs collected, bucket copies) |
| 17:24 | **Checked (observed): the 8 Oct backup's three zips are in `gs://tennis-predictions-archive/data/2026-10-08/` with the local files' exact sizes (2,737,251,036; 3,951,430,658; 15,407,302,293 bytes) and identical MD5** (`gsutil ls -L` hashes against `Get-FileHash -Algorithm MD5`; read-only). The local copies are redundant. Free disk now 119.9 GB (falling during the afternoon) | — |
| 17:21 | (Time note: the row above, headed 17:24, was written at 17:21 by the clock; the row headed 17:18 was written at 17:20. From here each row is written after reading the clock) | — |
| 17:44 | Subagent 3 (studies M-Z) returned: HIGH about 9.94 GB (`surface_ios/uploads` fit payloads 5.48 GB, of which 4.29 GB byte-identical seed copies; Polymarket derived tables 2.66 GB of 25 Sep; `surface_ios/full_runs/*_current` 0.33 GB; `point_sequence` intermediates 0.32 GB; `surface_ios/arms` 0.21 GB; rejected studies' fit folders: `tour_pooling` 0.16, `training_window` 0.13, `meta_stack` 0.10, `pair_strength` 0.07; `shot_level/stage2_frame` 0.13; `match_timing/undated_matches.csv` 0.11; smaller items), OPTIONAL about 1.97 GB, KEEP about 3.8 GB; 8 access-denied `pytest_*` folders of 2 Oct. **Finding: every build sandbox and every daily work tree copies `data/studies` (bar `full_runs`, `pytest_*`, caches and run folders), so about 9.6 GB of the HIGH set is copied by each build and each daily run.** Its caveats: rebuilds of tables made before the 6 and 8 Oct Stage 0 changes would differ; duplicate checks partly sampled; references found by name | To check: the surface_ios claims (the decision's named files; what the current model reads) |
| 17:22 | (Time note: the row above, headed 17:44 by a typing error, was written at 17:22 by the clock) | — |
| 17:23 | Subagent 4 (sandboxes, strays, backups, temporary folders, scratch code) returned. **Sandboxes:** 10 HIGH, 219.29 GB (`tnr_live/2/3`, `tnr_lyr_rp`, `tnr_sys1-5`, `tnr_sys_ios`: results copied out, nothing reads them); 4 OPTIONAL, 89.79 GB, each for a named reason found in code: `tnr_lle` (`lower_level_evidence/system_arms.reuse()` copies 32 files from it if P7's planned re-check runs), `tnr_lyr_off`/`tnr_lyr_on` (`level_layer_adoption/verify.py --gates` reads them; that study's reviewer checklist is unticked), `tnr_sb_rg_candidate` (the only copy of the Roland Garros candidate Stage 0 and timeline, about 100 MB, whose adoption is decided but not yet applied); KEEP `tnr_lyr_new`, `tnr_dump_freeze`. Junctions: two per sandbox (`data/raw`, `data/dump`); `tnr_lyr_rp` ten, one into `tnr_dump_freeze` (manual removal required). Files are copies, not hard links. Root strays HIGH (`explore1-5.csv`, `panel_noresult.parquet`, `controls_full.json`, `nearest_final.json`; AGENTS.md KEEP). `data/backups/2026-10-08` OPTIONAL in its view (a verified cloud copy remains); an access-denied `evaluation-tests-*` folder of 2 Oct. Temporary: scratchpads 9.37 GB (HIGH 8.07 GB once their sessions are closed; 1.11 GB cited by docs), `ssp_verifier_*` 0.52 GB, pytest temp 1 MB, `__pycache__` 30 MB. **Orphan processes:** `tail.exe` 53808 and 41588 (following `tnr_lle` logs since 9 Oct); subagent 1 also named `bash` 37948 and 24472 (session d061329f, since 10 Oct). Home items `checkpoints`, `feature_generation_hpo`, `orig_recover.py`, `=2.0`: not this project | Differences between subagents 1 and 4 resolved in the report by the code dependencies subagent 4 found (to verify) |
| 17:27 | Subagent 2 (studies A-L) returned: HIGH about 3.13 GB (lower_level_evidence 1.42, event_levels 0.50, bet_timing 0.38, line_sharpening 0.33, lean_review 0.16, `level_layer_adoption/candidate_men26` 0.13 as a hash-identical duplicate of the template, feature_interactions 0.11, smaller), OPTIONAL about 1.22 GB, KEEP judged 1.62 GB; 2 access-denied folders. Its note: most items made after 8 Oct are in no backup and not in git | — |
| 17:27 | Checked (observed): `system_arms.py:68` (`FIRST_RUN = tnr_lle`), `level_layer_adoption/verify.py:48` (`tnr_lyr_off/on/new`), `solver_tolerance.py:36`, the Roland Garros README lines 848-853 (the candidate Stage 0 stays in `tnr_sb_rg_candidate` until applied); the four processes running (`tail.exe` 53808 and 41588 on `tnr_lle\logs`, `bash.exe` 37948 and 24472 from a session's shell snapshot); `surface_ios/uploads` read outside the study only for `manifest.json` and `query_ids.parquet`; `candidate_corrections` only written by `consensus.py` | Deciding the classes below |
| 17:27 | **Reconciliation (made after reading all four reports, before writing the report):** (a) one class per item, each item counted once (study folders from subagents 2-3, sandboxes and temporary folders from subagent 4, "proposed before" from subagent 1); (b) the four sandboxes that code or a pending step still reads, which subagent 1 had as HIGH and subagent 4 as OPTIONAL, are put as "highly recommended once one small step is done", naming the step (the owner's "most should be highly if done properly"); (c) the backup zips, which subagent 4 had as OPTIONAL, are HIGH on the observed MD5 equality with the bucket; (d) `rg_first_serve_recount/confirmed/candidate_corrections`, HIGH for subagent 3, OPTIONAL until the Roland Garros correction is applied; (e) `surface_elo_pieces/audit_scratch`: the fake outputs and pytest folder HIGH, its scripts OPTIONAL (the audit's numbers come from them); (f) sizes decimal throughout | — |
| 17:27 | Report written (`README.md`); one row added to the studies index | — |

## 3. Claims and their evidence

| Claim | Evidence | Status |
|---|---|---|
| About 264 GB can go now, 91 GB more after one step each, about 3.2 GB optional | The four subagent reports (sizes by robocopy `/XJ` or listings that skip links), recombined without double counting | measured by the subagents; the largest items' reasons checked here |
| The 8 Oct backup's local zips are redundant | `gsutil ls -L` MD5 against `Get-FileHash` of the three zips (17:21) | observed |
| The four "one step first" sandboxes are read by named code or steps | the grep results above | observed |
| Past sessions proposed most of it; the owner answered three proposals | subagent 1's reading of 71 transcripts (assistant lines with cleanup words, the owner's following messages) | reported by the subagent, not re-read here |
| C: had 119.9 GB free at 17:21; `train.py` needs 130 GB | `Get-PSDrive C`; subagent 1 and 4 (`src/pipeline/train.py:170`) | observed / reported |

## 4. Weak points

* **References were found by searching for names and paths;** a path a script builds at run time could be missed.
  Each subagent searched src, test, docs, config and the study JSONs; the largest items were checked here.
* **"Rebuildable" was not tested:** tables made before the 6 and 8 Oct Stage 0 changes would rebuild with different
  values; only the recorded verdicts would stand.
* **Duplicates were partly sampled** (all seed copies of `X_train`, one slot for the other upload files).
* **The 11 locked folders** could not be read at all.
* **Where a flaw would most likely hide:** a sandbox or study file that a not-yet-run step of an open study needs
  (P7, the Roland Garros application, the level layer's reviewer check). Those are the items held back to "after one
  step".

## 5. Reviewer checklist and reproduction

* [ ] For each HIGH item, grep its folder name in `src/`, `test/`, `docs/decisions/` and `CLAUDE.md` once more on the
      day of deletion (the code changes daily).
* [ ] Re-run the MD5 comparison of the backup zips before deleting them (command in the chronology).
* [ ] Measure a sandbox with `robocopy <folder> NULL /L /S /XJ /NFL /NDL /NJH /BYTES /R:0 /W:0`, never `du`.
* [ ] List a sandbox's junctions with `Get-ChildItem <folder> -Recurse -Force -Attributes ReparsePoint` before any delete.

## 6. The deletions (owner's go-ahead)

* **The owner's words, verbatim** (11 Oct 2026, about 17:30 PDT): "Delete all the highly recommended delete now files.
  The ones you are very confident about it"
* **How it was read:** the README's "Highly recommended: delete now" groups A-G only; within them, only items whose
  safety I could confirm from the code at this hour. The "after one small step" group and the optional group are not
  touched.
* **Held back from the delete-now group after rechecking (17:28-17:35), so not "very confident":**
  * `C:\Users\zerom\tnr_sys4` (23.2 GB): `lower_level_evidence/system_arms.identity_source()` returns the sandbox in
    IDENTITY_ALL's `build.json` (this one), and `reuse()` copies Stage 3 and Stage B outputs from it for an Elo-only
    arm; the pending P7 test could build one.
  * `level_layer_adoption/candidate_men26/` (0.13 GB): `level_layer_adoption/verify.py:47` reads it, and that study's
    reviewer check is pending (as for `tnr_lyr_off`/`on`).
  * `lower_level_evidence/system/stage0/C0_pre/` (0.19 GB): five of that study's scripts name it; P7 is pending.
  * `current_best_model/2026-10-09_rg_box_scores/first_collect_indoor_filled/` (0.03 GB): its process log keeps it as
    the record, and the Roland Garros correction is not yet applied.
  * `event_levels/frame.parquet` (0.07 GB): kept while `event_levels/local/C/` (optional) is kept.
  * The loose scratch files in `Temp` (0.3 MB): not every one attributed to this project.
  * The 11 locked folders: deletion needs an administrator (not attempted).
  * Session scratchpads written today, this session's own, and the three that docs cite.
* **Checked before deleting:** no reader outside its study for `feature_interactions/features/levels.parquet` (only
  its own verifier, whose output goes too), the Polymarket derived tables, or `point_sequence`'s intermediates
  (`speed_features`, `sequences`, `seq_matches` are not in the list); the two `bash` loops belong to session d061329f
  (its transcript last written 10 Oct 19:02), waiting for a test output line that never came.
* **Method:** one script (`src/eda/cleanup_inventory/delete_now.py`): a dry run listing every path and size first;
  then, per tree, every reparse point (junction or link) found by a walk that never follows one, each removed with
  `cmd /c rmdir` (the link only), a second walk required to find none, and only then `cmd /c rmdir /s /q`. The
  junction targets and the kept trees (`data/raw`, `data/dump`, `tnr_dump_freeze`, `tnr_lyr_new`,
  `current_best_model`) are listed file by file before and after: no file may disappear from them. A record of every
  deletion: `data/studies/cleanup_inventory/deletions_2026-10-11.json`.

### 6a. Dry runs and the last checks (17:39-17:52)

* **17:39, processes:** all four still ran. `tail` 53808 and 41588: parents gone (orphans since 9 Oct). `bash` 37948
  and 24472: the parent is `claude.exe` 32204 (an idle VS Code tab started 10 Oct 09:05), the loop still polling
  d061329f's `b7rrpey33.output`. The script stops a pid only while its command line still holds the path the
  inventory found (a reused pid is left alone), with `taskkill /T /F`.
* **17:40, live sessions:** 21 `claude.exe` processes from VS Code tabs (8-11 Oct). Transcripts written in the last
  24 hours: e12a476e, f63f0543, 310009bc, b2538231, e1afd0c6, 8b00b734, d061329f, b6a34d10 and this session. Rule
  tightened from "a file written today" to: **a scratchpad goes only when neither it nor its session's transcript was
  written in the last 24 hours.** With the cited ones, that holds 16 folders (listed by the dry run).
* **Dry run 1** was cut short by my own `head` in the pipe (no deletion; the script had only listed). **Dry run 2**
  failed writing the reader listing (its folder did not exist); fixed. **Dry run 3** (17:47) completed: 1,950 items,
  238.2 GB; every sandbox link points into `data\raw`, `data\dump` or `tnr_dump_freeze` (`tnr_lyr_rp`: 10 links, the
  others 2); the 93 other links are pytest's `*current` links, all inside the folders deleted; one listing of the kept
  trees takes 10 s (`data\raw` 334,580 files), so the script re-lists them after each sandbox and stops on any loss.
* **Git:** 1,113 of the files are tracked (the surface_ios labels `y_train.npy`, the browser profiles, the
  feature_interactions fits, the root strays, the two dead scripts, …). They are deleted from the working tree only;
  no git command is run, so they show as deletions for the owner's next commit and can be restored from git.
* **Reader check (17:47-17:52), what code names an item:** a text search of `src`, `test`, `scripts`, `docs` and the
  repository's top-level files for every item's name gave 881 items "named", almost all by common file names
  (`stage0_matches.parquet`, `model_frame.parquet`, `X_train.parquet`). Narrowed to code outside the item's own
  study that also names the study and the deleted folder in a path, then read line by line. Findings:
  * **`surface_ios\arms\` is read:** `surface_rating_race/arms.py:64` (`SPROF_ARM`) and `model_frame.py:53` read
    `arms/sprof.parquet` for the previous model's frame, kept as evidence; `meta_stack/run_local.py:97` reads the arm
    frames. It cannot be rebuilt on the tables it was built on. **Held back** (0.215 GB).
  * **`lower_level_evidence\candidates\R_S2\` and `system\results\arms\SYS_S2\`:** the feature universe README
    (line 603) lists "the two box-score share differences ... the lower-level study's R_S2" as a lead to admit, not
    yet in the store. These frames carry those inputs. **Held back** (small).
  * Everything else named is a false match: tests that build their own `tmp_path` arms or use arm names as config
    labels (`test_system_decide`, `test_system_supplementary`, `test_level_layer*`, `test_translate_hooks`,
    `test_system_pairs`); readers of the kept copies (`feature_alpha_audit\repairs\`, `undated_matches.csv.gz`,
    `system\arms\SYS`, `lean_review\arms\A2`, `surface_ios\uploads\*\query_ids.parquet`, `full_runs\*_surface.*`);
    the template chain's `robocopy` that excludes `full_runs`; the backup test's exclusion pattern for the browser
    profiles; module paths (`surface_ios/arms.py`). `verifier_tables.py:3` already leaves the s999 smoke chunks out.
  * `data\LARGE_FILES.md` lines 16, 22, 25, 28, 31 describe deleted files (docs to touch afterwards; not edited).
* **Scratchpads named by repository records:** besides the three docs cite, records name folders inside 6a2c00c2
  (the 8 Oct rebuild's expected output, `rebuilds/2026-10-08T1853Z/rebuild.json`), 46524484 (the 7 Oct rebuild's),
  48421609 (`verifier_noread.json`'s inputs) and 5ba10243 (`serve_speed_sources/coverage_summary.json`'s ManTennisData
  download). Each record holds its result, so these are probably throwaway, but not "very confident": **held back.**
* **Dry run 4 (17:53), with the holds:** 1,942 items, 236.3 GB, nothing missing; 298 scratchpads to go, 20 held.

### 6b. The run (17:54-17:57) and its follow-up (17:57-18:00)

* **The run** (`./python.sh src/eda/cleanup_inventory/delete_now.py`, 153.5 s, exit 0):
  * Processes: `tail` 53808 and 41588 and `bash` 24472 stopped (`taskkill /T /F`); `bash` 37948 had exited by its
    turn (its child loop gone).
  * Sandboxes: all nine deleted, 26 junctions removed as links first. The kept trees were listed after each one:
    0 files lost each time (`data\raw` grew 334,734 → 334,781 meanwhile: the SofaScore scraper of another session,
    pid 56724, still writing).
  * Groups B, D, E: every item deleted (3; 1,455; 177). Group C: 292 of 298 at first.
* **Six scratchpads failed with "directory is not empty"** (8 files of 0 KB left). Cause found: eight `tail -f`
  processes (started 1-8 Oct, parents gone, not in the inventory's list) held them open. They are the same kind as G's
  two, and they blocked an approved deletion, so I stopped them (each checked to be `tail.exe` with that folder in its
  command line). Five folders were then deleted (recorded under `follow_up` in the JSON).
  * The sixth, 531ce504's empty `tasks\b3kd0htc0.output`, is "Access is denied". No `tail` holds it; `claude.exe`
    54500 (a VS Code tab started 8 Oct 12:29, in use today: its `bash` children started 14:34 and 14:36) is the likely
    holder. Not stopped. The file goes when its holder closes it.
  * **Not stopped:** 34 other leftover `tail.exe` processes (1-11 Oct). Some may belong to open sessions; listed in
    the README for the owner.
* **Totals (sizes measured at the dry run):** A 196.1, B 22.1, C 4.5, D 12.9, E 0.7 = **236.3 GB**; free disk
  120 → 341 GB (`df`, GiB).
* **Git (read-only check):** `git status` shows 1,091 tracked files deleted, every one inside an item of this run
  (checked against the record; 0 others). No git command was run.
* **Docs:** the README's "What was deleted" section and status line; the studies index row. Not edited, listed for
  the owner: `data/LARGE_FILES.md` lines 16, 22, 25, 28, 31; `.gitignore` line 53; five study READMEs that cite
  deleted files.

### 6c. Claims and evidence; weak points; checks

| Claim | Evidence |
|---|---|
| 236.3 GB deleted; nothing lost from the kept trees | `deletions_2026-10-11.json`: per item `deleted`, `bytes`, `links_removed`; `protected_files_before/after/lost`, and per sandbox `protected_lost_after` (all empty) |
| Every junction removed as a link, never followed | each sandbox's `links_removed` (link and target); the walk never enters a reparse point; a second walk found none before `rmdir /s /q` |
| The held items are read or needed | the code lines in § 6a; `deletions_2026-10-11_readers.txt` |
| Git deletions all come from this run | the 18:00 check (1,091 of 1,091) |

* **Weak points.**
  * Reader checks search names. A path built at run time from parts the search missed could still read a deleted
    file. The cross-study search needed the study's name in the same file.
  * Group D sizes are the dry run's measure, not freed bytes. The free-space rise (≈ 221 GiB ≈ 237 GB) agrees.
  * Idle VS Code tabs (21 `claude.exe` from 8-11 Oct) belong to sessions whose scratchpads went when neither folder
    nor transcript had changed for 24 hours. If such a session is resumed, its scratch files are gone (scratch by
    definition; nothing in the repository read them).
* **Reviewer checks.**
  * [ ] `Get-ChildItem C:\Users\zerom -Directory -Filter tnr_*` lists only the kept and held sandboxes.
  * [ ] The JSON's `protected_files_lost` is `{}` and every `protected_lost_after` is `{}`.
  * [ ] `git status --porcelain | grep "^ D"` paths are all under the record's items.

## 7. `tnr_lyr_off` and `tnr_lyr_on` (14 Oct 2026)

Session `d2d2331e-b87f-42fd-baa1-b5c3ddebe82c`, continued (context summaries before this; this log and the README
re-read). Clock read before each row.

* **The owner's words, verbatim** (14 Oct 2026, about 07:00 PDT), after my explanation that only 10 small files of the
  two sandboxes were read by the level-layer check, quoting my three steps ("Copy those 10 small files into the
  project. / Change one line in the check's program so it reads them there. / Delete the 47 GB."): "Do this and be
  mindful of anything that reads these files to properly change it"
* **How it was read:** keep every reader of the two sandboxes working after the deletion, not only `verify.py`;
  change each properly; then delete. Records that only name the sandboxes as where something was built stay as they
  are (history), with dated notes added where a reader would think the sandbox still exists.
* **07:04-07:08, the readers found** (a search of the whole repository but `data/raw` for the two names; then the
  code that loads what they point to):
  * `src/eda/level_layer_adoption/verify.py --gates`: 5 summary JSONs from ON (G5's leak probes:
    `stage1_baselines_summary`, `stage3_ratings_summary`, `stage4_features_summary`, `stageB_adj_summary`,
    `pieces_meta`) and 2 from OFF (the constants check: `stage3_ratings_summary`, `stageB_adj_summary`). Its
    `--identity`, `--fidelity`, `--candidate` and G2/G3 read only the stored frames in `data/studies` (kept). The
    stored build config it loads names ON's strength table, but G2/G3 never read it (they read params and classes, in
    the repository).
  * **`src/eda/level_layer_adoption/solver_tolerance.py` (not in my earlier answer):** re-solves men's holds on ON's
    lane-2 cache (`surface_ios/cache/atp.npz`, 24.7 MB) with ON's build config set as the layer's config; that config
    names ON's strength table (16.3 MB) and `record_dir` inside ON. It is the evidence behind `--candidate`'s solver
    tolerance (1e-7), set after the strict check failed. One solve takes about 54 s (`checks/solver_tolerance.json`).
  * **`src/eda/unpriced_leads/rebuild_pool.py` (a study of 13 Oct, after the inventory):** reads OFF's
    `ufc_ideas/stageB_adj.parquet` once, pinned by SHA-256, into a frozen extract it reuses when its record matches
    ("the sandbox may go"). The extract and record exist (13 Oct 10:57).
  * A reproduction step only: `docs/studies/level_layer_adoption/process_log.md:271` runs the match-timing leak probe
    inside ON. It needs the whole build; it cannot be kept small. Its output stays recorded
    (`checks/probe_match_timing_ON.json`).
  * Records naming the sandboxes as where things were built (`level_layer_2026-10-10/` and `template_off/` logs,
    chain JSONs, `build_config.json`, `layer_calls.jsonl`): history, unchanged. No test, notebook or daily-pipeline
    state names either sandbox; no running process does.
* **Plan:**
  1. Copy what the readers read into `data/studies/level_layer_adoption/sandbox_extracts/<sandbox>/…`, keeping the
     sandbox's own folder layout (so the code changes only its root), with SHA-256 of source and copy.
  2. For `solver_tolerance.py`: the extract's `build_config.json` is a relocated copy (only `strength.path` and
     `record_dir` pointed into the extract, so a re-run can never write into the deleted folder); the original kept
     byte for byte beside it.
  3. Prove each reader gives the same output from the extracts as from the sandboxes, before any code edit (in
     memory) and after it; `verify.py`'s outputs written to a temporary folder, not over the 10 Oct records.
  4. Delete the two sandboxes with `delete_now.py`'s method (links first, kept trees listed before and after).
  5. Re-run the proofs with the sandboxes gone; check nothing re-created them.
* **07:09, a fifth reader found while planning:** the layer's hooks append `layer_calls.jsonl` to the config's
  `record_dir` and create the folder (`level_layer.record`; the `weights` hook runs in the IOS solve). ON's sandbox
  log was last written 10 Oct 14:24, `solver_tolerance.py`'s run. With the original config, a re-run after the
  deletion would re-create part of `tnr_lyr_on`. **So the relocated config sets `record_dir` to null** (not "into the
  extract" as plan step 2 first said): no computed value depends on it, and a re-run then writes nothing.
* **07:11, extract** (`src/eda/cleanup_inventory/lyr_sandboxes.py --extract`): 18 files, 41,974,158 bytes, each
  SHA-256 equal to its source (the script stops otherwise); the relocated config validates
  (`level_layer.load_config`). Folder: `data/studies/level_layer_adoption/sandbox_extracts/` (`manifest.json`,
  `README.md`).
* **07:13, before-proof 1: failed on one field.** Gates: equal (sandbox vs extract), and equal to the 10 Oct record
  byte for byte. Solver: every array and field equal but `res/solver/lle_layer/seconds` (62.5 vs 53.9, wall clock).
  The comparison now leaves fields named `seconds` out (`TIMING` in the script). This was decided after seeing that
  difference; it is the only field left out.
* **07:16, before-proof 2: pass.** Gates equal, and equal to the 10 Oct record; solver equal (53.3 s and 57.2 s);
  `unpriced_leads`' extract valid (its record's two hashes match the code's pin and the file).
* **07:16, the code changes:**
  * `verify.py`: `SANDBOX["OFF"]`, `["ON"]` → `STUDY / "sandbox_extracts" / <sandbox>`, plus a docstring line.
  * `solver_tolerance.py`: `BOXES["ON"]` → the extract, plus a docstring paragraph.
  * `unpriced_leads` unchanged (another session's study; its code already reads its extract when the sandbox is gone).
* **07:17, edited-proof: pass.** The modules' own roots point at the extracts; gates and solver equal to the
  before-proof's sandbox outputs. No test imports either module.
* **07:18, deletion** (`--delete`, after a dry run listing 2 links each, `data\raw` and `data\dump`, both into kept
  trees): `tnr_lyr_off` 16,101 files, `tnr_lyr_on` 16,110 files, 47.09 GB; the kept trees (`data\raw`,
  `data\dump`, both `tnr_dump_freeze*`, `tnr_lyr_new`, `current_best_model`, `level_layer_adoption`,
  `unpriced_leads`) lost 0 files after each. Free disk 219 → 263 GB (`df`, GiB).
* **07:19, after-proof: pass.** Gates and solver equal with the sandboxes gone; neither re-created.
* **07:20, last checks:** the 18 copies and the relocated config still match the manifest (no record written beside
  them: the only `layer_calls.jsonl` there is the copied one, unchanged); `verify.py --gates` run as a command
  rewrote `checks/gates.json`, `gates_G2.csv` and `gates_G3.csv` with identical bytes (SHA-256 checked; copies of
  the three kept in this session's scratchpad beforehand); a search of `src`, `test` and `scripts` finds the two
  names only in this script, the two edited modules (as extract folder names) and `unpriced_leads`' provenance.
* **Docs:** the extract's README; dated notes added to the level-layer study's process log (§ 11) and to the
  `level_layer_2026-10-10` README; this study's README and the studies index.

### 7a. Claims, weak points, checks

| Claim | Evidence |
|---|---|
| Every reader of the two sandboxes still works, with the same outputs | `lyr_2026-10-14.json`: `proof_before`, `proof_edited`, `proof_after` (all `pass`) |
| Nothing kept was lost | `lyr_2026-10-14.json` `delete.items[*].kept_trees_lost_after` (empty) |
| The copies are the sandbox files | `sandbox_extracts/manifest.json` (SHA-256 of each source, equal to the copy at copy time and at 07:20) |

* **Weak points.**
  * Readers were found by searching for the two names, then following what they load. A path built from other
    parts (e.g. a sandbox root passed on a command line) would be missed. A run-time argument naming them would now
    fail loudly (a missing folder), not silently.
  * The solver proof ran one of `solver_tolerance.py`'s eight solves (men's holds, pooled, the decided tolerance).
    The other seven read the same two files from the same folder.
  * The proofs re-ran the checks on today's repository tables (Stage 0, the timeline). They prove the copies
    equal the sandboxes as inputs, not that the 10 Oct results would reproduce on every check: `--gates` happened
    to reproduce byte for byte.
* **Reviewer checks.**
  * [ ] `./python.sh src/eda/cleanup_inventory/lyr_sandboxes.py --prove --stage after` passes.
  * [ ] `sandbox_extracts/manifest.json`'s hashes match the files.
  * [ ] `tnr_lyr_off` and `tnr_lyr_on` do not exist under `C:\Users\zerom`.

## 8. The commit check, three deleted folders, `.gitignore` and the large-files guide (13-14 Oct 2026)

Session `428558ac-970b-47cf-a90b-f769d4c9a79f` (Claude Opus 5.5, `claude-opus-5-5`, VS Code), in parallel with § 7's
session. Times PDT. The check of 13 Oct was answered in chat; it is recorded here because the deletions and doc
changes of 14 Oct rest on it. Subagent briefs verbatim: [subagent_briefs.md](subagent_briefs.md) §§ 5-8.

* **The owner's words, verbatim.**
  * 13 Oct, about 21:40: "im gonna do a github push and commit. / Check if any files >50mb exist and how many files
    are no longer used and useful and can be cleaned up"
  * 14 Oct, about 07:00, quoting two lines of my answer: "Delete now	8	8 MB	Three Roland Garros leftovers that
    tonight's applied correction replaced. They are confirmed/candidate_corrections/ and followup/service_games_round1/
    and round3/ in rg_first_serve_recount / " / The guide to large files (data/LARGE_FILES.md) is out of date. Five
    rows describe files deleted on 11 Oct, and 49 large files aren't listed, 36 of them the training caches. That's
    harmless for the push." Update this / And then add to .gitignore anything large in size or folders/files that are
    easily reproducable that aren't very small."
* **How it was read.**
  * 13 Oct: read-only. Which files over 50 MB git would pick up, and this inventory's delta since 11 Oct 18:00:
    the held, one-step and optional items re-checked, and what was new.
  * 14 Oct: the pasted "Delete now" row is the go-ahead for those 8 files. "Update this" means the guide matches the
    disk: every file over 50 MB has a row, and no row names a missing file. For `.gitignore`, two tests:
    * large = over 50 MB (the guide's threshold and GitHub's warning);
    * easily reproducible = a script writes it from inputs kept on this machine, and it is not very small.
  * Set aside: a 10 MB "large" threshold. It would have taken decision evidence that cannot be rebuilt as it was out
    of git (e.g. `lower_level_evidence/system/relationship/formulations.csv`, 11.2 MB).

### 8a. 13 Oct, 21:50-22:40: the check

* **Files over 50 MB.** 188 in the repository folder; 187 ignored. The one that was not ignored is the daily
  engine's temporary solver cache, `_ios_cache_<stamp>.npz` (2.49 GB). `dp_state.py:211` writes it into the run
  folder, and `:250` deletes it when the step ends. It was seen in `box_score_gate_review/replay/base/` at 21:58,
  gone by 22:13, and in `replay/same_event/` at 22:23.
  * None of the 188 is tracked, and no blob over 50 MB is reachable from `main`.
  * A 109 MB blob (`undated_matches.csv`) is held only by seven local `refs/codex/` checkpoint refs (2-8 Oct), which
    a push does not send.
* **What a commit would add.** 7,240 untracked, not-ignored files, 1.72 GB, of which 1.31 GB is `.npz`. The `.npz`
  files are stored uncompressed and shrink about tenfold under zlib: two whole fits folders went from 121 to 12 MB and
  from 30 to 3 MB. GitHub already held 1.19 GB, packed, reachable from `main`.
* **Classification.** Subagents A and B classified; their decisive claims were re-checked here.
  * Delete now: 8 files, 7.9 MB.
  * After one step: 619 files, 0.87 GB.
  * Optional: 3,473 files, 1.68 GB.
  * Keep: 5,631 files, 122 GB, of which 116.5 GB is the two TabPFN caches in `daily_prediction/state/`.
* **Re-checked here:**
  * Untracked code that production imports: `stage0_build.py:69` imports `input_data_audit/corrections.py`.
    `src/pipeline/`, `scripts/master_pipeline.ipynb` and `src/eda/daily_prediction/` are untracked too.
  * The selected instance: `master_pipeline/selected_instance.json` names `template_2026-10-13`, selected 20:41:37.
  * The RG application: `adoption/20261013T211216/` exists, and `data_gaps_2026/rg_apply.log` ends "21:49:32 done".
  * One correction to subagent B: `tnr_sb_rg_candidate` still has a reader. The unticked reviewer item at
    `rg_first_serve_recount/process_log.md:222` needs the candidate's Stage 0, which lives in that sandbox.
* **Sandboxes** (robocopy `/XJ`, GB):
  * `tnr_gaps` 13.6, the selected instance's tree.
  * `tnr_gate_review` 11.3, the gate review's tree, running that night.
  * `tnr_daily_patterns` and `_live` 10.6 and 10.5, unpriced leads, "kept for review".
  * `tnr_lyr_new` 23.7, the code's default tree.
  * `tnr_lyr_off` and `tnr_lyr_on` 23.5 each (deleted in § 7).
  * `tnr_sb_rg_candidate` 22.4.
  * `tnr_lle` 20.3 and `tnr_sys4` 23.2, which wait for P7.

### 8b. 14 Oct, 07:05-07:15: the three Roland Garros folders

* **Re-checked first.**
  * No code reads them. `consensus.py:110` writes `candidate_corrections/`. The reviewers' `extract.py` and
    `svx_simulate.py` write a different file of that name in their own folders.
  * The RG README (line 322) calls the folder superseded.
  * `adoption_framework/checklist.md:224` names it in item 6, which is ticked done; its step 3 then used
    `followup/confirmed/candidate/`. That line is left as history.
  * `service_games_round1/` and `round3/` are named nowhere.
  * No restore since the 21:12 application, and no process writing there (only the 14 Oct template build ran, in
    `tnr_tpl1014`).
* **The first `rm` deleted nothing:** the shell's `rm` alias asked for confirmation and read end-of-input. The second
  (`command rm -f`, the same 8 paths) deleted them at 07:14, then the three empty folders. 7,927,160 bytes:

  | File (under `data/studies/rg_first_serve_recount/`) | Bytes | SHA-256 |
  |---|---:|---|
  | `confirmed/candidate_corrections/id_aliases.csv` | 509 | `846cde8d49aaf0842fc9124864f672ca0ea576643321dd65e4593b6207cfc382` |
  | `confirmed/candidate_corrections/row_corrections.csv` | 529,328 | `26876a5512080671977d99408619256a63da25406c421f5819fedcdf16a881bc` |
  | `followup/service_games_round1/matches.csv` | 2,127,878 | `3cb9143768d5534caece6be144d25250aaaa9bfcc6af28e31ffc7bf381ed1028` |
  | `followup/service_games_round1/proposed_swaps.csv` | 63,207 | `0e6a30b8115b0e52dfaa90aa4714352c9437838a3d71b7cdc20cc5850133c978` |
  | `followup/service_games_round1/summary.json` | 3,377 | `d571f8b82b28e61ac00e4f1914a5a795019aeb3a8c6791e670d039968421db13` |
  | `followup/service_games_round3/matches.csv` | 5,037,236 | `8c64982b224e54e50f8e077874fc006b27ddab4a8855bc98c5fca1fe5569f1bb` |
  | `followup/service_games_round3/proposed_swaps.csv` | 157,179 | `c26cc5a903f50bd73551d20d58be152e59337c9334d3a75da9bcbd26d433b879` |
  | `followup/service_games_round3/summary.json` | 8,446 | `de2836939a581df2782b4184d3bb15e01ed3aa937dc81e40d5ddc77525ea6c6e` |

  They were untracked and in no backup, so the deletion is final.

### 8c. 14 Oct, 07:15-07:30: `.gitignore`

* **Added:**
  * `*.npz`, `*.joblib`, `*.safetensors`;
  * the two temporary cache names, `_ios_cache_*.npz` and `_cache_tmp.npz`;
  * `data/studies/**/left_out.csv.gz`, which candidate Stage 0s write and which rebuilds in minutes;
  * `official_point_feeds/wta_checks.csv`, which `verify_wta.py` rewrites offline on every refresh (its summary
    `wta_verification.json` stays tracked).
* **The list of files over 50 MB** was rebuilt from a fresh scan at 07:15 (187 files, 140.7 GB). The lines for
  deleted files were removed, including `undated_matches.csv`, and the feed's two folders moved into the list as
  their comment asked.
* **Left in git on purpose:** decision evidence that cannot be rebuilt as it was, such as the RG reviewers' working
  tables, `formulations.csv` and the input audit's reviewer tables.
* **Considered and not done: keeping the model instances' fits and § 7's sandbox extracts in git** (the extracts'
  `atp.npz`, 24.7 MB, is now the only copy). `compare.py:87-98` reads an instance's `model_frame.parquet` as well as
  its fits, and the extracts' strength table is a parquet too. Both halves were already outside git, so what
  protects them is a copy in the bucket, not git.
* **Check at 07:22.**
  * All 187 files over 50 MB are ignored, and none is tracked.
  * The new rules hide 1,649 `.npz` and 3 `left_out.csv.gz` files, and nothing else.
  * Untracked and not ignored: 5,946 files, 323 MB.
  * Tracked files the rules now match: 1,279 `.npz` present (1.35 GB) and `wta_checks.csv`. They stay tracked until
    `git rm -r --cached -- '*.npz' data/studies/official_point_feeds/wta_checks.csv` runs. A dry run (`-n`) listed
    1,647 entries, 367 of them `.npz` already deleted on 11 Oct. It was not run: git commands are the owner's.

### 8d. 14 Oct, 07:15-07:41: `data/LARGE_FILES.md`

* **Who did what.** Subagents C and D (briefs §§ 7-8) researched rows for the 72 files over 50 MB that had no row,
  and the rows that had changed. Checked here before writing:
  * the 8 Oct backup: its local README and manifest, where `market_index.parquet` and both Polymarket price files
    have today's sizes and SHA-256;
  * the price files were extended, not replaced: their first 72,161,992 and 50,464,333 bytes still hash to the
    guide's 23 Sep values;
  * `market_index`'s 524,656 rows, from its sidecar;
  * the frozen reference is in no backup: the backup manifest lists 0 of its files, and its README says it "reaches
    cold storage with the next `backup.py` run";
  * every flag of every command the new rows name, from each script's argparse, and the notebook's
    `import src.pipeline as tp` with its `data_check` and `make_checkpoint`.
* **Changed in the guide:**
  * a paragraph on the 8 Oct backup;
  * the 5 rows of files deleted on 11 Oct removed, with a note that keeps their rebuild commands, and the shot-level
    row trimmed to the surviving file;
  * sizes re-measured;
  * the Polymarket rows, sections 2, 3 and 6 and the checksums brought up to the refresh of 5 Oct;
  * 22 rows added: 6 for raw downloads and staged tables, 16 for study tables, caches and copies;
  * the `replaced/` row rewritten for three rebuilds (its "366 MB" was MiB);
  * "Keeping this list current" rewritten: the new type rules, the temporary caches, a git-based check that takes
    about a second (the `find` it replaces ran over 25 minutes), and the tracked `.npz` files.
* **`.gitignore`, after subagent D's finding.** The feed candidates' folder rule was narrowed to their tables. The
  hand check of 13 Oct (`identity_verdicts.csv`, 448 rows, which exists nowhere else) and the other small records
  (84 files, 14.4 MB) can now be committed. Weekly candidates are built outside the repository (`feed.py:68`).
* **Check at 07:40.**
  * All 187 files over 50 MB match a row. No row names a missing path: the parser's 6 hits were names in prose,
    each checked.
  * All 187 are ignored, and the candidates' tables still are.
  * Table rows are well formed, and the relative links resolve.
  * Untracked and not ignored: 6,041 files, 338 MB.
* **Found and left for the owner: no backup holds the frozen reference (1.41 GB), nor anything made after 8 Oct
  16:05 UTC.** That covers the model instances and their fits, § 7's sandbox extracts, and the unpriced-leads
  `luck/values.parquet`, which its registry pins by hash. The upload is the owner's call:
  `./python.sh src/eda/data_continuity/backup.py plan`, then `pack`, `verify` and `upload`.

### 8e. Claims, weak points, checks

| Claim | Evidence |
|---|---|
| Nothing over 50 MB would be committed | The guide's Check command printed nothing (07:3x), and all 187 files over 50 MB are ignored |
| The 8 deleted files had no reader, and the correction stands | § 8b's searches; `adoption/20261013T211216/`; `rg_apply.log` |
| The new rules hide only generated arrays and rebuildable bulk | `git check-ignore -v` on the newly ignored files: 1,649 `.npz` and 3 `left_out.csv.gz` (§ 8c) |
| The guide covers every file over 50 MB | The coverage script in § 8d's check (187 of 187) |

* **Weak points.**
  * The ways back in the rows added on 14 Oct come from code and docs. None of those rebuilds was run.
  * The thresholds are judgments: "large" is over 50 MB, and "easily reproducible" is a script and inputs on this
    machine. A 10 MB threshold would also have ignored two tables of decision evidence.
  * `*.npz` makes every new array local-only. For fits that cannot be rebuilt as they were, the protection is a
    backup that has not yet been made.
  * Readers were found by name. A path built at run time could be missed.
* **Reviewer checks.**
  * [ ] The guide's Check command prints nothing, and its Count gives at least 187 files (builds add more).
  * [ ] `git check-ignore -v` ignores a new `.npz`, and does not ignore
        `data/studies/data_gaps_2026/feed/candidates/F20261013c/identity_verdicts.csv`.
  * [ ] The three RG folders of § 8b do not exist.

## 9. The commit check of 22 Oct 2026, and its three "delete now" groups

Session `4437577b-803e-4161-baf5-c6fade971478` (Claude Opus 5.5, `claude-opus-5-5`, VS Code). Times PDT, from the tool
outputs; the messages' own times were not recorded. The check was answered in chat; it is recorded here because the
deletions rest on it. No subagents.

* **The owner's words, verbatim.**
  * 22 Oct, about 11:28: "Get the tennis predictions pipeline in a state where I can easily git add and push it. No
    files > 50MB, no unused temporary files that take up too much disk space recently done. With some combination of
    .git ignoring and deleting files / Propose how to get it in this state (if it isnt)"
  * 22 Oct, before 13:00 (the first clock reading after it), pasting the proposal's three "Delete now" rows (the
    solver caches of 14 Oct, the caches of the 21 Oct morning model, the five one-off repository copies of 13-16 Oct):
    "Delete these 3 suggested delete now repository/files"
* **How the first was read.** Read-only: a proposal. Two parts: what a commit would add (files over 50 MB; tracked
  files an ignore rule now matches), and the disk that temporary or superseded files hold, in the repository and in the
  `tnr_*` trees the pipeline makes outside it. "Recently done": made since the last cleanup and push (14 Oct).

### 9a. 22 Oct, 11:28-11:50: the check

* **What a commit would add** (git, read-only). `main` equals `origin/main` (`1d8f53e`, 14 Oct 07:45); nothing staged.
  * Untracked, not ignored: 2,182 files, 49.2 MB, none over 5 MB.
  * Tracked and changed: 243 files, 64.2 MB (the largest 9.1 MB, `match_timing/links/sofascore.csv`). One tracked
    file deleted: `master_pipeline/running/32032.json`, a runner's marker (`src/pipeline/runner.py:29`) committed on
    14 Oct.
  * The guide's checks (`data/LARGE_FILES.md`, "Keeping this list current"): untracked over 50 MB, none; tracked over
    50 MB, none; tracked files an ignore rule matches, none (the 1,646 `.npz` of § 8 are no longer tracked).
  * Files over 50 MB in the folder, outside `.git`: 241, all ignored. 231 match the named list (`.gitignore` lines
    55-123); 10 only a type or folder rule: the three solver caches below (line 40), five Parquet files (line 27:
    `current_best_model/2026-10-09_rg_box_scores/candidate_tables/` and `2026-10-14_tenerife_dates/candidate_tables/`
    `predictability_diagnostic/stage0_match_players.parquet`, `serve_return_leads/elasticity/values.parquet`,
    `source_reconciliation/_snapshot/stage0_match_players.parquet`, `source_reconciliation/box/engine_long.parquet`)
    and two in `data/dump` (line 6: `points/infosys_atp_recent/court_vision.parquet`, `court_vision_shots.parquet`).
  * A pattern scan of the 2,394 text files a commit would add or change (API-key prefixes, JWTs, `key/token/password =
    "..."`): no match.
  * The object store: 1.36 GB in 3 packs; 12,802 objects reachable (1.30 GB); 1,216 blobs and 351 trees unreachable
    (about 60 MB).
* **Disk** (a scratchpad walk with `os.scandir` that never enters a reparse point, 11:36; decimal units).
  * The repository folder: 247.55 GB in 737,754 files, 201.6 GB of it written since 14 Oct.
  * `daily_prediction/state/` 183.45 GB:
    * `template_2026-10-21b` 62.59, the selected instance (`master_pipeline/selected_instance.json`, 21 Oct 15:55);
    * `template_2026-10-21` 62.40, of which `tabpfn/` 62.01;
    * `template_2026-10-16` 58.46, of which `tabpfn/` 57.88.
  * `daily_prediction/runs/` 7.80 GB, of which 6.24 GB is three `_ios_cache_<stamp>.npz` in `live_2026-10-14_123349`,
    `_125827` and `_135305` (2,494,003,914; 1,873,705,026; 1,873,710,330 bytes).
  * 19 `tnr_*` trees, 189.8 GB. `tnr_daily_qual` was absent at the scan; another session re-created it at 11:42 for
    a replay (`replay_2026-10-19_Q1_qualifying_maindate`, instance `template_2026-10-21b`) and removed it at 11:53.
  * Session scratchpads 1.02 GB.
  * C: free 278 GB at 11:33, 259 GB at 11:46 (during that replay), 276 GB at 13:00.
* **Readers** (searches of `src`, `docs`, `test` and `scripts` for each name).
  * The five daily work trees (`tnr_daily_patterns`, `_patterns_live`, `_fastcourt`, `_fastcourt_live`,
    `_replayfix`): named only in process logs, as "kept" or "kept for review (cleanup to be discussed)":
    `unpriced_leads/process_log.md` lines 312, 364 and 389; `daily_prediction/process_log.md` line 794. Each carries
    a `dp_worktree.py` marker, created 14 Oct 01:03Z to 16 Oct 22:06Z.
  * `template_2026-10-21`: the first retrain's morning instance, replaced at 16:39 the same day by
    `template_2026-10-21b` after the odds flaw (`in_season_retrain/README.md` lines 32-48, which also give its
    rollback). `dp_tabcache.py:200` treats a seed whose three files are missing as having no cache, and builds it.
  * The solver caches: `dp_state.py:243` gives each a new stamp; nothing reads one after its step.
* **Classes proposed.**
  * Delete now, 127.4 GB: the three groups above.
  * The owner's call, 86.0 GB: `template_2026-10-16`'s caches (the rollback); `tnr_tpl1014` and `tnr_gaps`, the 14
    and 13 Oct build trees (re-run commands in process logs and `form_evidence.py:82`'s default name them).
  * Kept:
    * the selected instance and its tree `tnr_tpl1021`;
    * `tnr_tpl1016`, the rollback's tree;
    * `tnr_lyr_new`, the fallback tree of `dp_common.py:31`, `pp_common.py:28`, `rebuild_pool.py:117` and
      `level_layer_adoption`;
    * `tnr_lle` and `tnr_sys4`, which wait for P7 (collecting);
    * `tnr_feed`, `tnr_mlf`, `tnr_tl_box` and the four `tnr_dump_freeze*`;
    * `tnr_daily_qual`, in use.
  * Proposed and not yet answered:
    * four ignore rules: the runner's markers, `*.npz.bak`, and the 10 locked `pytest_*` folders under
      `data/studies`, which make every `git status` warn;
    * the guide's update;
    * moving the root folder `patterns_replay_2026-07-13_R16/` beside the other replays.

### 9b. 22 Oct, from 13:00: the deletions

* **How the go-ahead was read.** The three "Delete now" rows as pasted, and nothing else.
  * The solver caches: the three files only; their runs' records stay.
  * The 21 Oct morning model's caches: `state/template_2026-10-21/tabpfn/`, as the row says. Its checkpoints
    (`2026-06-22/`, `2026-09-23/`) stay, so the documented rollback still works.
  * The five work trees.
  * Not covered: the ignore rules, the guide, the "your call" rows, the locked folders, the root folder.
* **Set aside:** deleting all of `state/template_2026-10-21/`, as was done for the 10, 13 and 14 Oct instances on 21
  Oct (`in_season_retrain/process_log.md` line 200). The row promised the checkpoints stay.
* **The method:** `src/eda/cleanup_inventory/delete_2026_10_22.py`, on `delete_now.py`'s walk, link removal and
  fingerprints (11 and 14 Oct).
  * **Each item is re-checked just before it goes:**
    * a solver cache: its size as found;
    * the caches: their instance is not the selected one, and no run folder made since the switch names it;
    * a work tree: its `dp_worktree.py` marker, and no process command line names it.
  * **Folder links** are found by a walk that never enters one, and removed as links (`cmd /c rmdir`, never the
    target). A second walk must find none before `rmdir /s /q`.
  * **The kept trees** are listed file by file before the run, after each item, and at the end. Files that other
    jobs may remove while the run goes on (the engine's own temporary caches; partial downloads) are reported
    without stopping the run. Any other lost file stops it. The kept trees are:
    * every link's target: `data/raw`, `data/dump`, `tnr_dump_freeze`, `tnr_dump_freeze_1014`;
    * the instances' daily state;
    * `current_best_model`;
    * the three runs;
    * `tnr_tpl1021` and `tnr_tpl1016`.
  * **The record:** `data/studies/cleanup_inventory/deletions_2026-10-22.json`.
* **Chronology.**

  | When | Step | Result |
  |---|---|---|
  | 13:00 | Readers re-checked before writing the script: the replay running since 11:42 is on `template_2026-10-21b` (its `run.json`), not the morning instance; `dp_tabcache.py:200` rebuilds a seed whose files are missing; `dp_state.py:243` stamps each solver cache; the five trees carry `dp_worktree.py` markers; the browser download's profile is outside the repository (`browser.py`, a user-started Chrome); partial files of the running downloads end `.tmp`, `.part` or `.partial` (searches of `src/ingest`) | The method above |
  | 13:04 | `--dry-run` | Every check passes on all 9 items: 127.44 GB (3 solver caches 6.24; `tabpfn/` 64 files, 62.01, newest 21 Oct 10:43, no run names the instance since the switch; the trees 10.61, 10.52, 12.33, 12.54 and 13.19, newest 13-16 Oct, 10, 10, 10, 2 and 10 links, every target inside a kept tree). C: free 284.0 GB |
  | 13:05 | The run started (background) | running |
  | 13:05-13:12 | The run, 412 s | **9 of 9 deleted, 127.44 GB.** 42 links removed as links before their trees went (10, 10, 10, 2, 10). The kept trees were listed 11 times: 758,594 files before, 758,977 at the end (`data/raw` +419 and `data/dump` +1 from the running downloads; `tnr_tpl1021` +30; `state/` −64 and each run −1, all of them the items' own files). Lost: none; temporary files gone meanwhile: none. C: free 284.0 → 443.8 GB, about 32 GB more than the run deleted: freed elsewhere at the same time (no other `tnr_*` tree disappeared). Git: no tracked file missing; no untracked file over 50 MB |
  | 13:13 | Observed afterwards: the owner had committed and pushed at 12:09 (`9228b26`, "latest rebuild and extra data", 2,496 files; `origin/main` equals it), between the check and the go-ahead. The largest blob it added or changed is 9.1 MB; the tree's largest file is 36.9 MB (`shot_level/stage2_results.json`, older). The runner marker's deletion went with it | § 9a describes the tree before that commit |

### 9c. Claims, weak points, checks

| Claim | Evidence |
|---|---|
| The three groups are gone: 9 items, 127.44 GB | The record's `runs[0]`: `deleted` true for all 9, and `expected_gone_still_present` 0 after each; the paths are absent (13:13) |
| No kept file was lost | The 11 listings of the kept trees: no path present before is missing after any item, other than each item's own files; no temporary file vanished either |
| Every link was removed as a link, never followed | `delete_now.remove_tree`: 42 links (`links_removed`), each by `rmdir` without `/s`, a second walk empty before `rmdir /s /q`; the targets' counts unchanged or growing (`tnr_dump_freeze` and `tnr_dump_freeze_1014` 209 and 209) |
| The morning model's rollback still works | Its checkpoints `2026-06-22/` and `2026-09-23/` remain; `dp_tabcache.py:200` builds a seed whose files are missing (not run) |
| Nothing a commit would add changed | `git_after`: no tracked file missing, no untracked file over 50 MB |

* **Weak points.**
  * A rollback to `template_2026-10-21` without its caches was not run. It rests on the code and on the guide's account of the rebuild (the same forecasts, bit for bit, tested by the daily-prediction study).
  * Readers were found by name in `src`, `docs`, `test` and `scripts`; a path built at run time could be missed. No process named the trees, and none had been written since 16 Oct.
  * The trees had been kept "for review", and a reviewer can no longer open them. Re-creating one needs a `dp_worktree` setup on the base tree of its day (`tnr_gaps` for 13 Oct, `tnr_tpl1014` for 14-16 Oct; both still on disk, both in the "your call" group) and the frozen dumps (kept).
  * The extra 32 GB of free space was not traced. The kept trees lost nothing, and no other `tnr_*` tree went.
  * **Correction (22 Oct, after the run; the owner had asked what the 13 and 14 Oct build trees are):** the third
    point above names the wrong base tree for 13 Oct. The runs' own `run.json` files give it:
    * the two 13 Oct trees (`tnr_daily_patterns`, `_patterns_live`) were set up on `tnr_lyr_new` (`template_2026-10-10`), not `tnr_gaps`;
    * the three 16 Oct trees (`tnr_daily_fastcourt`, `_fastcourt_live`, `_replayfix`) on `tnr_tpl1014`.
    Re-creating the 13 Oct ones needs `tnr_lyr_new`, still on disk and not in the "your call" group.

### 9d. 22 Oct, from 13:40: the 13 and 14 Oct build trees

* **The owner's words, verbatim** (quoting my recommendation, then the instruction): "My recommendation: delete both.
  The cost is that those few past checks can't be re-run exactly as written; their results and records stay in the
  repo. I'd also point that one script's default at the live model's copy, so it doesn't name a missing folder. / Do
  this, update studies that refernce them that we've deleted it , so models who review the study know it was built with
  an older version and may have to be updated"
  * The question before it: "The 13 and 14 Oct build copies (28 GB): What are these ?why were they built and why did
    they become obsolete?" It was answered in chat from the two instances' READMEs, `data_gaps_2026/process_log.md`
    (lines 146-184) and the live-history table of `current_best_model/README.md`.
* **How it was read.**
  * **Delete** `C:/Users/zerom/tnr_gaps` (`template_2026-10-13`'s build tree, 13.65 GB) and `C:/Users/zerom/tnr_tpl1014`
    (`template_2026-10-14`'s, 14.44 GB), as in § 9b: links first, the kept trees listed, each tree re-checked just
    before.
  * **"That one script":** `feature_universe/form_evidence.py`, whose default is `tnr_gaps` / `template_2026-10-13`.
    It gets the master notebook's selection as its default (the tree and the instance together, since the tree's
    tables are that instance's build). `--tree` and `--instance` still name any other.
  * **"Update studies that reference them":** each study document that names either tree gets a dated note. The note
    says the tree is deleted, which of the study's results ran on it (and on which instance), that those results stand
    as recorded but come from an older model, and that a re-check needs the current instance.
    * Run folders, chain logs, JSON records and the build scripts in `data/studies` are evidence, and are not edited.
    * Extended, and told to the owner: the same note where a study log says the five work trees of § 9b were "kept".
  * **Not covered:** `tnr_lyr_new` (on 14 Oct the owner withdrew a request to delete it and `tnr_gaps`:
    `data_gaps_2026/process_log.md` line 196, "dont delete them"; today's request names only the 13 and 14 Oct
    trees). Nor the other open items of § 9a.
* **What the 14 Oct stop said, re-checked.** `tnr_gaps`'s only reader in code was `form_evidence.py`'s default; no
  test names either tree (repository search, 13:40). `tnr_tpl1014` is named in code only in `form_evidence.py`'s
  docstring.
* **Time note.** The "13:40" in this section's heading and in the search above was written without reading the clock.
  The question was answered at about 13:35-13:40. The go-ahead came later; the first clock reading after it is the run's
  start, 16:15:43. The rows below carry clock times.
* **Chronology.**

  | When | Step | Result |
  |---|---|---|
  | before 16:15 | Every mention found (repository search, `data/raw` excluded): 159 files. Records (run folders, chain logs, JSON, the build scripts in `data/studies`) are left as evidence. To annotate: 7 study documents, the two instances' READMEs, the guide; `form_evidence.py` | The list |
  | before 16:15 | `run_chain.py` read: a chain sandbox has no marker (its `setup` copies `src`, `docs` and `data/studies`, and links `data/raw` and `data/dump`). So part 2 checks its shape instead (the script's docstring). `delete_2026_10_22.py --part 2` added; part 1's dry run re-checked: 9 "already gone", the record byte for byte unchanged | — |
  | before 16:15 | `--part 2 --dry-run` | Both pass every check: `tnr_gaps` 13,773 files, 13.65 GB, newest 13 Oct 20:12; `tnr_tpl1014` 14,106 files, 14.44 GB, newest 14 Oct 07:09; two links each (`data/dump`, `data/raw` into the repository); no run on either since its instance was replaced, none in 3 days; the rollback trees `tnr_tpl1016`, `tnr_tpl1021`. C: free 490.0 GB |
  | 16:15:43-16:17:37 | The run, 114 s | **Both deleted, 28.08 GB;** 4 links removed as links. The kept trees: 771,279 files before, 771,377 after (`data/raw` +98, the running downloads); lost: none; temporary files gone meanwhile: none. C: free 490.0 → 518.2 GB. Git: no tracked file missing, no untracked file over 50 MB |
  | after 16:17 | A peer (`tennis-predictions-f8`) had announced edits to many `src/pipeline` and `src/eda/daily_prediction` files: none is touched here. `form_evidence.py`: `DEFAULT_TREE` and `DEFAULT_INSTANCE` replaced by `selected_instance()` (the notebook's selection, as `dp_common` reads since 22 Oct); `--tree` and `--instance` only together; the docstring says what the outputs of 14 Oct were built on | Checked: the default resolves to `template_2026-10-21b` on `C:/Users/zerom/tnr_tpl1021` (both exist, with the instance's `model_frame_chain.parquet`); either flag alone is refused; `--help` runs. The full script was not run: it would write new outputs |
  | after 16:17 | The notes: `data_gaps_2026`, `box_score_gate_review`, `men_lower_level_fill`, `daily_prediction`, `unpriced_leads`, `tml_revisions` (process logs: a dated section at the end); `feature_universe/README.md` (the Rebuild block's comment and a U-126 note); the two instances' READMEs (a note under the banner: no longer a ready rollback); the guide's checkpoint row. Extended, beyond the two trees: the morning instance's rollback lines (`in_season_retrain/README.md`, `current_best_model/README.md`: its caches are gone, the first run rebuilds them) | A search afterwards: every document naming either tree has a deletion note, except this study's own files (this section) and `study_data_versions/process_log.md` |
  | after 16:19 | `docs/studies/study_data_versions/process_log.md` appeared: a new study by session `c0f7c8d9…`, started 16:18, still being written (16:19). It lists `tnr_tpl1014` as existing and asks whether deleting it is safe | Not edited (another session is writing it). Messaged: `tennis-predictions-f6` and `tennis-predictions-14`, the two busy tennis sessions other than f8 (the listing gives no session ids), each told to ignore it if the log is not theirs; and f8, of the one line edited in its `current_best_model/README.md` |
  | after 16:26 | `tennis-predictions-f6` replied: the log is its own. It added the dated note to that log's facts section and chronology, kept its audit brief of 16:18 verbatim (the note says the brief still names the tree), and told its reviewer agent the folder is gone | Every study naming either tree now carries a note; `tennis-predictions-14`'s message was not about its work |

### 9e. Claims, weak points, checks (§ 9d)

| Claim | Evidence |
|---|---|
| Both trees are gone, 28.08 GB | The record's `part2.runs[0]`: `deleted` true for both; the paths absent afterwards |
| No kept file was lost | 3 listings of the kept trees: no path present before is missing after either item |
| Neither was in use, nor a rollback | The dry run's checks: not selected; not in a rollback command (`current_best_model/README.md`, `in_season_retrain/README.md`); no run naming either as its base tree since its instance was replaced; no process naming either |
| The one code reader is repointed | `form_evidence.py`: the default resolves to the selection; either flag alone refused |
| Every study naming them says so | The search after the notes (above), with one exception, `study_data_versions`, whose session was messaged |

* **Weak points.**
  * Readers were found by name; a path built at run time could be missed. The build scripts in `data/studies`
    (`harm/build_feed_arm.sh` sets `SB=C:/Users/zerom/tnr_gaps`; `build_final.sh` defaults to `tnr_tpl1014`) would
    re-create a tree if run. They are records, so they were not edited.
  * The notes say "older versions of the model" without measuring how far each study's readings would move on the
    current instance. That is for whoever re-checks a study.
  * `study_data_versions` may still state that `tnr_tpl1014` exists, until its session reads the message.
  * The messages went to two sessions, because the listing gives no session ids. One of them received a message that
    is not about its work.
* **Reviewer checks.**
  * [ ] `C:/Users/zerom/tnr_gaps` and `C:/Users/zerom/tnr_tpl1014` do not exist.
  * [ ] `./python.sh src/eda/feature_universe/form_evidence.py --tree X` exits with "give --tree and --instance together".
  * [ ] Every study document naming either tree (search outside `data/raw`, records aside) has a note of 22 Oct 2026.
* **Reproduction.** `./python.sh src/eda/cleanup_inventory/delete_2026_10_22.py --part 2 --dry-run` now finds both
  gone; the record keeps the plan (`part2.dry_run`) and the run (`part2.runs`).
* **Reviewer checks.**
  * [ ] None of the 9 paths in the record's `runs[0].items` exists.
  * [ ] `state/template_2026-10-21/` holds only `2026-06-22/` and `2026-09-23/`.
  * [ ] `tnr_dump_freeze` and `tnr_dump_freeze_1014` hold 209 files each.
  * [ ] The guide's Check command prints nothing.
* **Reproduction.** `./python.sh src/eda/cleanup_inventory/delete_2026_10_22.py --dry-run` now finds every item gone. The
  record keeps the plan (`dry_run`) and the run (`runs`).

## 10. The commit check of 29 Oct 2026, and its three items deleted

Session `f3ef49b6-3465-4894-9ba4-f454eb3a9b2a` (Claude Opus 5.5, `claude-opus-5-5`, VS Code; `tennis-predictions-66` to
its peers). Times PDT. The check's commands were not clock-stamped; the first clock reading, 07:14:29, came after it.
The check was answered in chat; it is recorded here because the deletions rest on it. No subagents.

* **The owner's words, verbatim.**
  * 29 Oct, before 07:14 (the whole message was pasted text): "We've made some changes recently, various studies that
    I havent pushed yet. / Find the set of files that can be deleted that can be easily reproduced (only related to
    studies, nothing production related) / As well as if there are any files >50MB that should be gitignored or removed
    for the next push"
  * 29 Oct, after 07:14: "Delete this", followed by the check's section "Study files you can delete (rebuildable,
    nothing in production reads them)", pasted whole: the seven replay working copies (96.3 GB), the bytecode cache
    inside the frozen reference's code copy (15 MB), the P9 study's working tables (26 MB).
* **How the first was read.** Read-only: a proposal. "Recently": since the last push, `9228b26` of 22 Oct 12:09, which
  `origin/main` equals. Two parts: what a commit would add, and the disk that recent study leftovers hold, in the
  repository and in the `tnr_*` trees outside it. "Nothing production related": the live and rollback models' caches and
  build trees, the live runs, the shared tables and the feeds were left out, whatever their size.

### 10a. 29 Oct, before 07:14: the check

* **What a commit would add** (git, read-only). `main` equals `origin/main`; nothing staged.
  * Untracked, not ignored: 1,024 files, 26.6 MB (1,076 files, 26.9 MB once the morning's bet-day run had finished).
    Tracked and changed: 156 files, 18.6 MB. The largest: `gap_downloads/sofascore_itf_detail_matches.csv.gz`, 8.5 MB.
  * The guide's checks: untracked over 50 MB, none; tracked over 50 MB, none; tracked files an ignore rule matches,
    none.
  * Files over 50 MB outside `data/raw` and `data/dump`: 130, all ignored. Five match only `*.parquet`, the same five
    as in § 9a (`current_best_model`'s Roland Garros and Tenerife candidates' Stage 0,
    `serve_return_leads/elasticity/values.parquet`, `source_reconciliation/_snapshot/stage0_match_players.parquet` and
    `box/engine_long.parquet`).
  * While the run went on, `master_pipeline/predict.lock` and `master_pipeline/running/42084.json` were present and
    untracked. A runner marker was committed once (14 Oct; removed 22 Oct, § 9a).
* **Disk** (PowerShell and `find`, never following a link; decimal units).
  * `data/studies`: 143.75 GB; 3.48 GB written since 22 Oct 12:09, of which `daily_prediction` 3.21 GB (2.28 GB of it
    the morning run's temporary solver cache, which the run deleted at its end).
  * 20 `tnr_*` trees (robocopy `/L /XJ`). Seven were made on 24-25 Oct for replays and a check: `tnr_daily_earlier`
    13.78, `tnr_daily_earlier2` 13.78, `tnr_daily_main` 13.73, `tnr_daily_main_w` 13.72, `tnr_daily_main2` 13.78,
    `tnr_daily_datefix_off` 13.77, `tnr_daily_datefix_on` 13.77 GB: 96.33 GB.
    * Each holds `src` (20 MB), `docs` (14 MB), `run` (89-111 MB) and `data/studies` (13.6 GB). Each `dp_worktree.py`
      marker names its run.
    * The five replays have 10 links each: `data/raw`, `data/dump/{odds,players,points,rankings}` and
      `data/dump/matches/{live_tennis_api_zenodo,mantennisdata,open_tennis_data,sackmann_archive}` into the
      repository; `data/dump/matches/tennis_my_life` into `tnr_dump_freeze_10211347`. The two checks have 2
      (`data/raw`, `data/dump`).
  * The frozen reference's code copy: 97 `__pycache__` folders, 379 `.pyc` files, 15,420,827 bytes, all written 28 Oct
    09:03. Pytest's assertion-rewrite files of the copy's own tests are among them. `frozen/files.csv.gz` lists 1,581
    files, none a `.pyc`, and `reference.verify` checks only those (missing or differing).
  * The P9 study (`p9_point_details`, 28 Oct): nine git-ignored `.parquet` tables in `build/` and `harness/`,
    26,080,455 bytes, written 28 Oct 09:11-09:22.
  * C: free 347.9 GB, then 361.6 GB once the morning run had removed its work tree.
* **Readers** (searches of `src`, `test`, `scripts` and `docs`).
  * The seven trees: `master_pipeline/process_log.md` Parts 14 and 17 (lines 2091-2184 and 2651-2837: "Kept for
    review, not deleted (cleanup is the owner's call)"); their run folders' JSON records; the notebook's saved output
    (run folder names only). No code, no test. `dp.py cleanup` would delete one, but its default `--work-tree` is the
    engine's own tree (`DP_WORK_TREE`, else `tnr_daily`).
  * The bytecode: nothing; Python and pytest rewrite it.
  * The P9 tables: P9's own scripts only. `test_harness.py:219` names a `build/` path in a path-guard test that reads no
    file.
* **A bet-day run was in flight during the check** (`dp.py run_day`, pid 42084, from 06:40:27; its states step from
  06:50). It had ended by 07:14, removing its work tree `tnr_daily_nb` and the 2.28 GB cache. Nothing was touched while it ran.
* **Proposed.**
  * Delete the three items.
  * Add ignore rules for the runner's markers and `predict.lock`, and for
    `daily_prediction/checks/weights_sha256_cache.json`. It is keyed to this machine's paths and rebuilt by
    `dp_predict.weights_sha256`.
  * Name the five files in `.gitignore` and the guide.
  * Left out:
    * the production caches and trees;
    * `tnr_lle`, `tnr_sys4` and `tnr_lyr_new` (67.16 GB, made before the last push). `study_data_versions` asks for
      their code to be captured before any deletion, a rule awaiting the owner.

### 10b. 29 Oct, from 07:14: the deletions

* **How the go-ahead was read.** The three items as pasted, whole.
  * The seven trees entirely, their code copies included. The pasted text offered to keep those ("costs 140 MB"), and
    the go-ahead did not take it up.
  * The bytecode: the 97 `__pycache__` folders under `frozen/code/` only.
  * The P9 tables: the nine `.parquet` files only. The study's JSON and CSV outputs stay.
  * **Not covered:** the ignore rules, the five names, the run folders, everything left out above.
* **The method:** `src/eda/cleanup_inventory/delete_2026_10_29.py`, on `delete_now.py`'s walk, link removal and
  listings, as `delete_2026_10_22.py`.
  * **Before the run:** no bet-day run in flight (no `predict.lock`, no runner marker, no process running the daily
    engine).
  * **Each item is re-checked just before it goes:**
    * a tree: its `dp_worktree.py` marker names its own run, and that run's folder stays; each link points where
      `dp_worktree.setup` points it; it is neither the selected build tree nor a live work tree; no process command line
      names it;
    * the bytecode: only `.pyc` files, directly inside the code copy's `__pycache__` folders, none of them listed in
      `files.csv.gz`, and no link anywhere in the copy;
    * the P9 tables: each one's size as found, each ignored by git;
    * every item: readable, and nothing in it written in the last 2 hours.
  * **Links** are removed as links (`cmd /c rmdir`), never followed. A second walk must find none before `rmdir /s /q`.
  * **The kept trees** are listed file by file before the run and after each item. Files other jobs remove meanwhile
    (temporary and partial files, by name) are reported; any other lost file stops the run. The kept trees:
    * `data/raw`, `data/dump`, `tnr_dump_freeze_10211347` and the other Tennis My Life freezes;
    * the engine's state and runs;
    * `current_best_model` and `p9_point_details`;
    * `tnr_tpl1021` (selected) and `tnr_tpl1016` (rollback).
  * **The frozen reference** is verified before the run and again right after the bytecode goes, with
    `reference.verify(write=False)` so its tracked `verify.json` is left as it is. The same files must be present and
    equal, or the run stops.
  * **Git** before and after: tracked files missing from disk; untracked files over 50 MB.
  * **The record:** `data/studies/cleanup_inventory/deletions_2026-10-29.json`.
* **Chronology.**

  | When | Step | Result |
  |---|---|---|
  | 07:14-07:30 | Re-checked before writing the script: the trees' markers (each names its run) and links; `files.csv.gz` (1,581 rows, no `.pyc`); the bytecode (97 folders, all inside `frozen/code`, `.pyc` only); the P9 sizes, all nine ignored by git; the kernel guard (`src/pipeline/__init__.py`) checks only modules the notebook imported, so a new script under `src/` does not stop it; claims on shared files are not built yet (production-integrity plan, step 6); peers: two tennis sessions busy, none naming a tree | The method above |
  | 07:20:16-07:20:31 | `--dry-run` | Every check passed except `ignored_by_git` on the P9 tables. **A bug in the check, not a finding:** git, asked by hand before, ignores all nine. The script sent the paths on stdin in text mode, which on Windows ends each line with `\r`, so git read names with a trailing `\r`. Fixed by passing them as arguments. This dry run's record was replaced by the next one's, so its failure is recorded only here |
  | 07:20:50-07:21:03 | `--dry-run` again | **Every check passes on all 9 items.** The trees: 13.72-13.78 GB each, 96.33 GB, newest 24 Oct 20:48 to 25 Oct 10:11; each marker names its run; 10, 10, 10, 10, 10, 2 and 2 links, each where `dp_worktree.setup` puts it. The bytecode: 97 folders, 379 files. The P9 tables: 9, sizes as found. No bet-day step in flight; the selection `template_2026-10-21b` on `tnr_tpl1021`; the reference verifies (1,581 files). C: free 362.3 GB |
  | 07:21:11 | The run started (background) | running |
  | 07:21:26-07:32:29 | The run, 660.7 s | **9 of 9 deleted, 96.38 GB** (96,378,182,615 bytes). 54 links removed as links before their trees went; each tree then went in about 2.5 s. The kept trees were listed 11 times: 1,144,229 files before, 1,144,087 at the end (`data/raw` +246 from the running downloads; `current_best_model` −379 and `p9_point_details` −9, the items' own files). Lost: none; temporary files gone meanwhile: none. The reference right after the bytecode went: 1,581 files, none missing or differing, the inventory intact. C: free 362.3 → 459.0 GB. Git: no tracked file missing, before or after; no untracked file over 50 MB |
  | during the run | Messages with `tennis-predictions-34` (summarised). Its claim (CLAUDE.md, `docs/decisions/README.md`, `edge_anatomy/README.md`, new `holdouts` folders) did not overlap with this work. It then edited the two P9 documents (a line in README § 4, a note in § 6, an addendum at the end of the log) and handed them back before the notes below | — |
  | 07:32-07:34 | The notes, each a dated addition: `master_pipeline/process_log.md` (a section at the end); `p9_point_details/process_log.md` (after the peer's addendum) and `README.md` (the end of § 8) | — |
  | 07:34:11-07:34:17 | The reviewer checks below, run once | All pass: no `tnr_daily*` tree left; `tnr_dump_freeze_10211347` 209 files; `p9_point_details` no `.parquet`, 24 other files; no `__pycache__` under `frozen/`; `reference.verify(write=False)` ok (1,581, none missing or differing), `verify.json` unchanged; the guide's Check prints nothing |

### 10c. Claims, weak points, checks

| Claim | Evidence |
|---|---|
| The three items are gone: 9 items, 96.38 GB | The record's `runs[0]`: `deleted` true for all 9, and `expected_gone_still_present` 0 after each; every path absent afterwards (07:33, 07:34) |
| No kept file was lost | The 11 listings of the kept trees: no path present before is missing after any item, other than the items' own files; no temporary file vanished either |
| Every link was removed as a link, never followed | `delete_now.remove_tree`: 54 links (`links_removed`), each removed by `rmdir` without `/s`, and a second walk found none before `rmdir /s /q`. The targets lost nothing: `tnr_dump_freeze_10211347` still holds 209 files |
| The frozen reference is as it was frozen | `reference.verify(write=False)` before the run, right after the bytecode went, and at 07:34: ok, 1,581 files, none missing or differing, the inventory intact; `verify.json` untouched |
| Nothing a commit would add changed | `git_before` and `git_after`: no tracked file missing; no untracked file over 50 MB |

* **Weak points.**
  * Readers were found by name in `src`, `test`, `scripts` and `docs`, so a path built at run time could be missed.
    Against it:
    * no process named a tree;
    * none had been written since 25 Oct 10:11;
    * the engine builds each run's tree afresh and refuses an existing one.
  * The trees held the only copies of the code as it stood on 24-25 Oct; the run folders keep only fingerprints.
    Re-running a proof exactly would need that code. The go-ahead did not take up the offer to keep it (140 MB).
  * The step logs that the run folders' `tables.json` name are gone. Their outcomes are in the run folders' records.
  * The bytecode's cause is still there: a test run from the repository root can walk into the frozen code copy again.
    A pytest setting that limits collection to `test/` would stop it (suggested in the check; not asked for).
* **Reviewer checks.**
  * [ ] No `C:/Users/zerom/tnr_daily*` tree exists. (Live runs create `tnr_daily_nb` while they run and remove it at
    the end.)
  * [ ] `./python.sh -c "from src.eda.current_best_model import reference as R; print(R.verify(write=False)['ok'])"`
    prints `True`.
  * [ ] `tnr_dump_freeze_10211347` holds 209 files.
  * [ ] `data/studies/p9_point_details` holds no `.parquet`, and its other 24 files remain.
  * [ ] The guide's Check command prints nothing.
* **Reproduction.** `./python.sh src/eda/cleanup_inventory/delete_2026_10_29.py --dry-run` now finds every item gone. The
  record (`data/studies/cleanup_inventory/deletions_2026-10-29.json`) keeps the plan (`dry_run`) and the run (`runs`).
