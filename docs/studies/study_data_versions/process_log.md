# Studies on current data, with a data-version pointer: process log

22 Oct 2026 (local, UTC−7), from 16:18 · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code) ·
Session: `c0f7c8d9-cc78-498f-9409-72258b59a7dd` · For a future reviewer · No report yet (a proposal under audit)

## 1. The request

* **How it arose.** Two tests failed (`test/predictability_diagnostic/test_stage1.py::test_built_baselines_table`,
  `test_stage3.py::test_built_ratings_table`), found while adding the weekly event-country check
  ([men's lower-level fill log](../men_lower_level_fill/process_log.md), § 12).
* **The owner's words, verbatim, in order (22 Oct 2026):**
  1. "Why did this occur? how can we make it so it doesnt occur again? certain built tables and model and bet days will
     get out of sync constantly right given how it currently worsk?"
  2. "shouldn't we fix the studies to point to new history? Or basically to re-create the study we have to retest it on
     the new data? meaning , we want re-create the study, but the study says so in itself. (IE it needs to be re-run)
     And a standing rule when we build a study, understand we cant keep every huge model it was tested with , as thats
     not practical, so it should have an addendum and a pointer?"
  3. Quoting the plan below: "have another agent audit this plan to see if it likes each step of it".
* **The plan under audit, as given to the owner (verbatim):**
  1. Record the rule as your decision, and add it to the project rules and the study template, with a small helper
     that writes the data-version block. For existing studies, one index page listing which data each one ran on,
     instead of editing every report.
  2. Add a helper that gives studies the current model's tables. Switch the studies still in use first: the
     candidate-feature pool and the open lead studies. Closed studies switch only if they're re-run.
  3. Make the shared loading code warn whenever something reads a table built from an older history, so this can't
     happen silently again.
  4. Fix the two tests so each checks a table against the history it was built from.
  5. Then list the old copies (about 3 GB across the six main study folders) for you to approve before anything is
     deleted.
  * A correction sent after: the current model's folder is about 17 GB, not 20; the 14 and 16 Oct model folders
    (about 34 GB) would be listed for approval with the old copies.

## 2. What was established before the audit (observed, 22 Oct)

* The repository's chain tables above the history were built once and never refreshed: Stage 1 baselines 30 Sep,
  Stage 3 ratings and Stage 4 features 1 Oct, surface IOS and Elo pieces 6 Oct, Thinking frame and UFC stages 2 Oct.
  The history (Stage 0), Stage 1's odds link and the timeline were rebuilt on 21 Oct by the shared rebuild
  (`src/eda/data_continuity/rebuild_stage0.py`: Stage 0, checks, odds, remap, timeline, timing features, TrueSkill).
* Model builds run the whole chain in their own folder (`run_chain.py`), "so no study's folder is overwritten"
  (CLAUDE.md). The current model's folder (`C:/Users/zerom/tnr_tpl1021`): history 928,337 matches = Stage 1 = Stage 3
  (packages and feed merged). The repository: history 873,964, Stage 1 and Stage 3 872,704.
* The daily engine rebuilds Stage 3 from the model's checkpoint and writes it in its work tree before Stage 4 reads it;
  it raises if the saved outputs' matches differ from today's (`src/eda/daily_prediction/dp_state.py`, about lines
  360–385). Replays at switches proved live inputs equal the training frame.
* About 60 files under `src/` read the Stage 1–4 tables.
* Sizes: the six main study folders about 3 GB; model build folders about 17 GB each, three on disk
  (`tnr_tpl1014`, `tnr_tpl1016`, `tnr_tpl1021`).
  * *Note, 22 Oct 2026, 16:25: `C:/Users/zerom/tnr_tpl1014`, the build tree of `template_2026-10-14` (an older
    instance, replaced on 16 Oct), was deleted at 16:17 PDT at the owner's word by the cleanup session (4437577b; its
    record: `docs/studies/cleanup_inventory/process_log.md`, § 9d), one minute before the audit brief below was
    written. The brief still names it as on disk; the brief is kept verbatim. On disk now: `tnr_tpl1016` (the
    documented rollback) and `tnr_tpl1021` (the instance in use).*

## 3. Plan of 22 Oct, 18:31: step 1 and the rule draft

* **The owner's words, verbatim** (after the revised plan, about 17:00):
  > "I like this. My purpose of saying "re-point" was as more and more studies accumulate they will be pointing to "old versions", but if we keep all the old versions then disk size will grow. We dont want the studies to point to "new versions" but we may want the process of HOW to recreate the old version IF we need to, but may not want to keep all the old versions (the ones the studies reference". We also probably need a process to ensure future agents automatically update this when necessary, so it doesnt constantly cause failures or its out of date without my manual execution. So agents implicitly know when they do something that would add to this, they also know to add to this. "A read-only inventory and index page: which history each table is on, and which code mixes versions" Is this reasonable? or am I missing a key point?"

  Then, after the answer ("a recipe, not a copy"; the code is the missing piece; delete only after a recipe is proven;
  automation over memory; three more inventory columns): **"start step 1 and draft the rule."**
* **Step 1, as acted on (read-only: no table, code path or study file changed; new files only, in this study's
  folders):**
  1. **Histories:** every Stage 0 version on disk: the repository's (21 Oct); the copies the shared rebuilds saved
     (each the history in use before that rebuild); the frozen reference's; the model folders' (`tnr_tpl1016`,
     `tnr_tpl1021`, `tnr_lyr_new`). Each with its fingerprint (sha256), match count and newest date.
  2. **Tables:** every parquet under `data/studies` with a `match_id` column, the saved histories excepted. Its match
     ids against each history: equal to one; inside several (the newest named); or holding matches no kept history
     has. With its size, rows and newest match date.
  3. **Readers:** each `src/` file's references to each table's file name (static, by name), and whether the file also
     names a saved history; grouped by study folder.
  4. **Code that mixes versions:** files that read an older table together with a live base table (Stage 0, the
     timeline, the odds link) without naming a saved history are flagged, and each flag is read by hand.
  5. **Recreatable:** for each history and table, whether it is kept as a file and whether the code that built it is
     captured anywhere; if not, what is missing.
  6. **Folders:** every `C:/Users/zerom/tnr_*` folder with its size and the documents that name it.
  7. **Outputs:** `data/studies/study_data_versions/*.csv` and the index page `docs/studies/study_data_versions/index.md`,
     both written by one script, so the index can later regenerate itself.
* **The rule draft** goes to `docs/studies/study_data_versions/rule_draft.md`, not to `docs/decisions/`, until the
  owner approves it. Each line names the check that enforces it and is marked as the owner's words or an agent's
  choice (the production-integrity decision of 22 Oct, principles 2 and 5).

## 4. Chronology

| When | Step | Output |
|---|---|---|
| 16:18 | This log opened; the audit brief written (appendix, verbatim) and given to a read-only subagent | this log |
| 16:25 | Peer session tennis-predictions-92 (cleanup) reported that `tnr_tpl1014` was deleted at 16:17 at the owner's word, and asked for a dated note here (the owner wants every study naming a deleted tree to say so). Confirmed by listing (only `tnr_tpl1016`, `tnr_tpl1021` remain); note added in § 2; the auditor told of it. The men's lower-level fill log already carries the cleanup session's note | § 2 |
| by 16:33 | **The audit returned** (condensed in appendix A2; 106 tool uses, about 14 minutes). Its main points: the framing is partly wrong. The repository's chain tables are one consistent older version, the history saved by the 7 Oct rebuild, which about 39 files read together with that saved history on purpose (`feature_interactions/panel.py`). The faults are narrower: two joins mix versions (`unpriced_leads/build_extras.py`, `serve_return_leads/elasticity.py`); no table records the history it was built from; a model folder's code exists only inside it. Step verdicts: 1 change (fill the template's existing data-version section; a generated index plus a generated line per study), 2 change substantially (pin, never "current"; switch only on a re-run; not the feature pool first), 3 change (no shared loader exists; builders record their history; join points refuse a mismatch), 4 keep (both: the recorded history in the tests, and an end-of-build check), 5 drop the deletion (3 GB of 518 GB free; the only copies; `tnr_tpl1016` is the rollback and a replay target). The claim that any past history can be rebuilt exactly is **false as stated**: the code is the gap (101 uncommitted changes after today's commit). It also notes that today's decided corrections are not yet in the repository's history | – | appendix A2 |
| 16:33–16:35 | **The lead's checks of the audit** [observed]: Stage 1 and Stage 3's match ids equal the 7 Oct saved history exactly (872,704); today's history differs from it by 97 matches gone and 1,357 added; `panel.py` pairs the 6 Oct tables with that saved history (its `OLD` paths); `build_extras.elo_at_matches` inner-joins Stage 1 with today's history; `elasticity.long_table` reads the 6 Oct surface IOS with today's Stage 0 and timeline. In elasticity's window (before 29 Jul): 75 matches in today's history are not in the 7 Oct one, none with a ratings row (40 WTA tour-level main draws); 95 went the other way, 81 with ratings rows. (A first count of 617,531 matches without ratings was mostly the rating pool's design, not the mix.) A heads-up to the serve/return study's session failed: it has ended, and no session is on that study. Its files were not touched | – | – |
| after 16:36 (no clock reading until 18:31) | Report to the owner: the audit's verdicts, the lead's agreement with all five, the revised order, the rule's proposed wording. Then the owner's clarification (§ 3, verbatim) and the answer: "a recipe, not a copy"; the code is the missing piece; delete only after a recipe is proven; automation over memory; three more inventory columns | – | – |
| 18:31 | "start step 1 and draft the rule." Read the production-integrity decision of 22 Oct (principles 2 and 5: every rule names its check; every rule is marked as the owner's words or an agent's choice). Found: the frozen reference keeps `code/` and `env/` beside its tables, the recipe pattern the rule would make standard. Histories on disk: six saved by the shared rebuilds (7, 8, 14 ×3 and 21 Oct), the repository's, the frozen reference's, and the build folders' | § 3 | – |
| 18:32–18:34 | `src/eda/study_data_versions/inventory.py` written (read-only: it writes only `data/studies/study_data_versions/` and `docs/studies/study_data_versions/index.md`); membership by sorted hashes (`searchsorted`) for speed. Started 18:34 in the background (`inventory.log`) | Step 1 | the script |
| 18:34–18:35 | **The rule draft** written: `rule_draft.md`. Seven lines, each with who chose it and its check; what it changes for existing studies (nothing re-pointed; the two mixing places pinned; generated notes; re-runs after the next shared rebuild); three questions for the owner (adopt; the code copy; retired model folders) | Rule | `rule_draft.md` |
| 18:51 | **The inventory's first run** (16.8 minutes) [observed]: 13 histories; 1,533 tables scanned, 1,275 with match ids, 296 on an older history (6.5 GB); 204 code files flagged; 12 folders, "294 GB". Two faults found by reading the output: (a) the folder sizes counted the junctions each build folder makes to the repository's `data/dump` and `data/raw` (Python 3.11's `os.walk` descends into junctions; `du` gave 17 GB for `tnr_tpl1021`, the walk 55.7): fixed by skipping reparse points; (b) the mixing flag was too broad (any file naming an older table and a live base table) | Step 1 | `inventory.log` |
| 18:52–18:55 | Fixes: junctions skipped (folders 103 GB in all; `tnr_tpl1021` 17.4, `tnr_tpl1016` 16.5, `tnr_lle` 20.3, `tnr_lyr_new` 23.7, `tnr_sys4` 23.2); "likely" flags limited to code outside the model chain and the daily engine that names one of the snapshot's chain tables (75), the rest "weak" (129), with a second static signal (the table's file named; a model folder named; the module only). `--reuse-tables` added (the table scan reused: 19 s). Read by hand: `unpriced_leads/build_rhythm.py` left-joins the 6 Oct surface IOS onto a frame of today's history (confirmed); with `build_extras.py` (the audit's) and `elasticity.py` (measured at 16:33–16:35), three confirmed, recorded in `mixing_reviewed.csv`. **`elasticity.py` was missed by the static pass entirely** (it names "frozen", read as a pinned history), so the static pass cannot be the safety net: the runtime stamp and refusal of the plan's step 3 is | Step 1 | `mixing.csv`, `mixing_reviewed.csv` |
| 18:55–18:57 | The index regenerated with the verdicts and with "recreatable only while the folder exists" for build folders; the owner's README for step 1 written | Step 1 | `index.md`, `README.md` |

## Appendix: briefs

### A1. The plan's auditor (subagent type Plan: read-only tools; 16:18)

See the brief below, given verbatim.

````text
You are auditing a 5-step plan for a tennis-prediction project (repository: C:\Users\zerom\Documents\Tennis-predictions, Windows; use `./python.sh` in Git Bash for Python, the project's conda env). You are an independent reviewer: the owner asked "have another agent audit this plan to see if it likes each step of it". Do not rubber-stamp it. For each step, decide whether you would keep it as is, change it, or drop it, and say why, with evidence from the code and data where you can (file:line, or a read-only command's result). You may disagree with the problem framing too.

STRICTLY READ-ONLY: do not edit, create, move or delete any file; do not run builds, fits, model runs, downloads, the scheduled jobs, or anything that writes to data/ or to the model folders. Reading files and running read-only Python (e.g. `./python.sh -c "import pandas as pd; ..."` to count rows or read dates) is fine. Other sessions are working in this repository right now.

Background (verify what matters; don't take it on trust):
- Project rules: CLAUDE.md at the repository root (read the sections "The current best model", "Daily predictions", "Prediction runs", "Process logs", "Git and working files"). The process-log template: docs/studies/process_log_template.md. The decision records live in docs/decisions/.
- The problem found today: two tests fail, test/predictability_diagnostic/test_stage1.py::test_built_baselines_table and test_stage3.py::test_built_ratings_table: the repository's built tables data/studies/predictability_diagnostic/stage1_baselines.parquet and stage3_ratings.parquet hold 872,704 matches, the repository's history (stage0_matches.parquet, rebuilt 21 Oct) 873,964.
- Cause, as I (the lead) read it: the repository holds the whole feature chain's outputs, but the coordinated "shared-table rebuild" (src/eda/data_continuity/rebuild_stage0.py, called from the notebook layer src/pipeline/data.py rebuild_shared_tables) refreshes only the base: Stage 0, Stage 1's odds link, the link remap, the timeline (data/studies/match_timing/), the leak-proof timing features and TrueSkill. Everything above was built once by the studies that created it and never refreshed: Stage 1 baselines (30 Sep), Stage 3 ratings and Stage 4 features (1 Oct), data/studies/surface_ios and surface_elo_pieces (6 Oct), tabpfn_thinking and ufc_ideas (2 Oct). Since 8 Oct, model builds run the whole chain in a sandbox copy (src/eda/model_rebuild/run_chain.py; data/studies/level_layer_adoption/build_template.sh), "so no study's folder is overwritten"; each build merges the accepted lower-level packages and the weekly feed into its own history (src/eda/current_best_model/additions.py). The current model's build folder is C:/Users/zerom/tnr_tpl1021 (data/studies/master_pipeline/selected_instance.json): its history, Stage 1 and Stage 3 all hold 928,337 matches.
- The daily prediction engine (src/eda/daily_prediction/) works in its own copy of the repository; I read it as recomputing Stage 3 from the model's saved checkpoint and writing it before Stage 4 reads it (dp_state.py, about lines 360-385; dp_elo.py), so it never uses the repository's stale copies. Switch-time replays proved live inputs equal the model's training frame.
- About 60 files under src/ read the Stage 1-4 tables (grep for stage1_baselines, stage3_ratings, stage4_features, RATINGS).
- Sizes: the six main study folders (predictability_diagnostic, surface_ios, surface_elo_pieces, tabpfn_thinking, ufc_ideas, tabpfn_leakproof) total about 3 GB; model build folders are about 17 GB each; three exist (C:/Users/zerom/tnr_tpl1014, tnr_tpl1016, tnr_tpl1021).
- The owner's proposal, in their words: "shouldn't we fix the studies to point to new history? Or basically to re-create the study we have to retest it on the new data? meaning, we want re-create the study, but the study says so in itself. (IE it needs to be re-run) And a standing rule when we build a study, understand we cant keep every huge model it was tested with, as thats not practical, so it should have an addendum and a pointer?"

The plan to audit (as given to the owner):
1. Record the rule as your decision, and add it to the project rules and the study template, with a small helper that writes the data-version block. For existing studies, one index page listing which data each one ran on, instead of editing every report.
2. Add a helper that gives studies the current model's tables. Switch the studies still in use first: the candidate-feature pool and the open lead studies. Closed studies switch only if they're re-run.
3. Make the shared loading code warn whenever something reads a table built from an older history, so this can't happen silently again.
4. Fix the two tests so each checks a table against the history it was built from.
5. Then list the old copies (about 3 GB across the six main study folders) for you to approve before anything is deleted.
(Plus: the 14 and 16 Oct model folders, about 34 GB, listed for approval with the old copies.)

Questions I most want answered (beyond your own):
a. Is "the current model's folder" the right default source for studies? It merges packages and the feed (928k matches) while the repository's history does not (874k); it changes at every retrain; and model folders are deleted over time. What breaks for a study that mixes files from both, or whose pointer outlives its folder?
b. Is the claim "any past history can be rebuilt exactly from the kept raw downloads (superseded versions kept) and the shared rebuilds' backups" true in this repository? Look at data/raw/public_dump/*/superseded, data/studies/data_continuity/rebuilds/*/replaced, src/eda/level_layer_adoption/freeze_dump.py, how code versions are kept (the owner commits manually and rarely; check `git log -5` and how much is uncommitted with `git status --short | wc -l`), and the frozen reference (data/studies/current_best_model/reference_2026-10-08/). If a pointer is not enough to reproduce, what minimum should a study keep?
c. Step 3: where would a staleness warning live so it catches real readers without flooding every run (which loaders do the 60 readers go through)? How would a table know which history it was built from (do the builders record a Stage 0 fingerprint anywhere today)? Is a warning the right strength, or should some readers refuse?
d. Step 4: should the two tests compare against a recorded source history, or move into the model build's own checks (e.g. post_build), or both? Is anything else in the test suite tied to the moving history in the same way?
e. Step 5 and the model folders: what must stay (the frozen reference, the holdback control named in CLAUDE.md, the instance in use and its tree, anything the replay registry data/studies/daily_prediction/replay_views.json or exact replays need)? Is deleting tnr_tpl1014 or tnr_tpl1016 safe today?
f. Ordering and missing steps: is anything missing (e.g. pre-registered or sealed studies that must stay pinned; studies other sessions are running right now; the cleanup-inventory study docs/studies/cleanup_inventory/)? Would you order the steps differently?

Report (plain words, under about 900 words): for each step, a verdict (keep / change / drop) with reasons and evidence; then what is missing; then your recommended plan in order. Mark which statements you verified (observed) and which are inference.
````

A message sent to the auditor at 16:25 (verbatim): "A fact update for your audit, from the lead:
C:/Users/zerom/tnr_tpl1014 no longer exists. The cleanup session deleted it at 16:17 PDT today at the owner's word, one
minute before your brief was written. C:/Users/zerom/tnr_gaps went too, and earlier today five daily work trees and
template_2026-10-21's TabPFN caches; the record is docs/studies/cleanup_inventory/process_log.md § 9d and § 9b. Still
on disk: tnr_tpl1016 (the documented rollback), tnr_tpl1021 (live), and the tnr_dump_freeze* folders. For question e,
treat the 14 Oct folder as gone. The owner also wants every study that names a deleted build folder to carry a dated
note saying it was built on an older instance; please weigh that practice in your answers to a, b and e."

### A2. The auditor's report (returned by 16:33), condensed by the lead

Every claim, verdict and file reference of the report, condensed (a verbatim copy failed to paste through the shell at
16:36; the full text is in this session's transcript). The lead's checks of its key claims are in § 4, 16:33–16:35:

* **The framing is partly wrong.** The repository's study folders are meant to hold older results; that is why model
  builds run in a sandbox (`run_chain.py:7-11`: each study's folder "holds earlier models' evidence"). They are one
  consistent older version: Stage 1 and Stage 3 equal the history saved by the 7 Oct rebuild (872,704 matches) [obs];
  the surface IOS, Elo pieces, Stage 4, UFC-ideas Stage B and Thinking frame tables fall within it [obs]. 39 code files
  point at that saved history on purpose (`feature_interactions/panel.py:36-48`) [obs].
* **The real faults:** (1) different versions mixed in one computation: `unpriced_leads/build_extras.py:85-86` (the
  6 Oct Stage 1 with today's history, via `screen.py:53`) and `serve_return_leads/elasticity.py:121-139` (the 6 Oct
  surface IOS with today's timeline): 97 matches drop silently, 1,357 newer get no values [obs]; (2) no table records
  which history it was built from; (3) a model folder's code exists only inside that folder.
* **Step 1: change.** The template already asks for the commit, uncommitted changes and each table's path, SHA-256 or
  row count and instance (`process_log_template.md:76-77`) [obs]; the helper should fill that section. The owner asked
  twice for the note in the study itself ("the study says so in itself"; "update studies that reference them", cleanup
  log § 9d): one generated index as the source of truth plus one generated line per affected study linking to it. Mark
  the rule's mechanics as an agent's choice, as the production-integrity decision requires.
* **Step 2: change substantially.** Pin the model folder, never "current": resolve it once and record the instance and
  the history fingerprints `chain_additions.json` keeps (before `2f79cfdd…`, the 21 Oct rebuild's and still the
  repository's; after `eeb73c0a…`, the folder's) [obs]. Mixing breaks: the folder's history has 54,373 more matches
  with its own timeline [obs]; its men's inputs use the level layer; its code differs from the repository's in 82 files
  [obs]; reading its tables with the repository's code or timeline silently loses matches or drops the layer [inf].
  Read a folder's tables with that folder's code (`qualifying_targets/frame.py:13,40-41`) [obs]. "Current" in comments
  ages (`unpriced_leads/rebuild_pool.py:36,117` calls the 10 Oct folder `tnr_lyr_new` "the current instance") [obs]. A
  study switches only when re-run. Not the candidate-feature pool first: it is pinned on purpose to the frozen
  63,737-match frame, reads past sealed dates (`SEALED = 2026-07-29`), and is the source of the live five-pattern
  adjustment's frozen parameters. Start with the two mixing sites: they need a pin, not a switch.
* **Step 3: change.** No shared loading code exists: 61 files name the table files and call `read_parquet`
  themselves; `load_matches` covers Stage 0 only [obs]. No builder records the history it read [obs]. An "older than
  today" warning would fire on every pinned study. Instead: builders record the history's SHA-256 and row count; a
  same-history check at join points refuses a mismatch unless the caller names a version (as the daily engine already
  refuses, `dp_state.py:367-368, 378-379`) [obs]; a report-only inventory on the STATUS page. Existing tables can be
  stamped by matching their ids to the saved rebuild copies; exact for Stage 1, Stage 3 and the Elo pieces [obs].
* **Step 4: keep, do both.** Compare each table with the history it was built from (the 7 Oct copy, whose hash
  `event_levels/common.py:66-68` records; skip if the copy is missing), and add an end-of-build check that every chain
  table matches the build's history (the post-build step checks only the odds and the input list today) [obs]. Never
  make the tests pass by rebuilding in place: that breaks the panel's pairing. `test_stage4.py:416` (country table
  against today's history) is a legitimate freshness alarm; keep it.
* **Step 5: drop the deletion of the six folders.** 3 GB against 518 GB free [obs]; the only copies of the pre-7 Oct
  chain tables; pinned studies read them. Must stay: the frozen reference and the Pinnacle-first instance (the holdback
  control); the live instance and `tnr_tpl1021`; the rebuild copies (about 370 MB each), which code and
  `replay_views.json` point at; the `tnr_dump_freeze*` folders; `tnr_lyr_new` (a fallback folder in the daily engine).
  `tnr_tpl1014` already deleted [obs]. `tnr_tpl1016` is not safe to delete: the documented rollback
  (`current_best_model/README.md:13`), kept by the cleanup script, read by replays of the 16 Oct instance
  (`dp_steps.py:126-130`) [obs]. One off-machine backup exists (8 Oct); model folders are never backed up [obs].
* **Question b.** "Any past history can be rebuilt exactly" is false as stated: `rebuild_stage0.py:4-5` says the
  replaced tables "cannot be rebuilt from today's code: they are kept first" [obs]. True: every shared history since
  6 Oct is kept as a file; Tennis My Life's staged files per rebuild can be re-made (`freeze_dump.py`); Sackmann's files
  have one version each (278 receipts) [obs]. The gap is the code: 101 changes uncommitted after today's commit; the
  live folder's `stage0_build.py` matches neither the latest commit nor the 14 Oct one [obs]. The minimum to keep: the
  pointers and their fingerprints; a copy of the code (`src/` is 20 MB) or the commit plus its uncommitted changes;
  the correction tables used; the small set of columns read, with a SHA-256 (as `rebuild_pool.py` did).
* **Missing.** The repository's own history is already behind: today's 201 row corrections and 20 event corrections
  are not in it (3,152 rows in the corrections file, 2,951 applied; no event corrections applied) [obs]; anything
  switched now goes stale at the next rebuild. Another session edits the predictability-diagnostic folder today
  (`stage4_country*`) [obs]: claim files first. Back up before any deletion.
* **Recommended order:** (1) a read-only inventory and generated index: each table's version, and which joins mix
  versions; (2) the owner decides the rule: pin, never "current"; re-run, never re-point; the dated note; the minimum
  to keep; (3) builders record their history; the model build gets the end-of-chain check; (4) fix the two tests;
  (5) the two mixing sites refuse a mismatch; (6) generate the dated notes in the affected studies; (7) re-run studies
  only after the next shared rebuild, the owner choosing which; (8) deletions last, after a backup; `tnr_tpl1016` only
  when its rollback is retired.

Note (the lead, 16:35): the "another session" editing `stage4_country*` is this session (the event-country fix and its
weekly check, the men's lower-level fill log §§ 11–12).
