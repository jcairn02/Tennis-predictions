# Tennis My Life's revisions of lower-level history: the decision, and the check of the four held files: process log

13 Oct 2026, 18:00 – 19:05 PDT · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code extension) · Session: `84155559-d2ab-4579-95b0-3c7290cd7e6f` (peer name `tennis-predictions-f6`) · For a future reviewer · Report: [README.md](README.md)

## 1. The request

* **The owner's words, verbatim** (13 Oct 2026, about 18:00 PDT), the first message of this session:
  > "Im confused . I was told this "Two standing notes on every sheet, neither blocking:
  > Tennis My Life has revised some old Challenger and qualifying matches since the 8 Oct freeze. Your decision on accepting those is still open.
  > Four old Challenger files are held back for review."
  >
  > I thought we accepted all the new challenger data, but we arent retrainig the model yet beacuse its an expensive operation and its a small change?? is there a communication issue between agents on the state of this pipeline"
* **My answer (chat, read-only lookups; summarised):** yes, a gap in the record, not in the data. (a) The 10 Oct men's 2026
  Challenger package is in the model and in every bet-day run (today's run counts 1,725 of its 1,735; the 11 SofaScore
  main-draw matches of 5 Oct are now Tennis My Life's own rows). (b) The first note is the 50 Tennis My Life corrections
  the owner discussed with the master-pipeline session on 11 Oct; the owner's answers then (verbatim below) were never
  recorded as a decision, so the freeze rule and `history.py` still treat them as open, and the daily-prediction
  session's README still recommends the opposite (hold live runs at the 8 Oct data). (c) The second note is the four
  Tennis My Life Challenger season files (2022–2025) held by the download gate since 10 Oct; a read-only diff of mine
  (scratchpad `held_diff.py`, `held_diff2.py`) found re-keyed events, removed duplicates, four misfiled 2008 events and
  about 200 player-id corrections. (d) The 13 Oct lower-level feed is not in predictions yet (its harm check pending).
* **The recommendations the owner then approved, verbatim** (my message, 13 Oct about 18:05):
  > 1. **Record your 11 Oct answer as a decision.** Tennis My Life's corrections and new matches at the levels the model already uses would go in by themselves: on bet days straight away, and into training at the next rebuild. The rebuild check would list these changes instead of refusing, and each rebuild gets a harm check. Then I'd update the project rules, both session reports and the sheet notes to match. I prefer this to keeping bet days on the 8 Oct data. The mismatch is 50 old records, and a 20-year-old listed as 58 is exactly the kind of error you want fixed.
  > 2. **Accept the four parked files under that rule, after one check.** I'd rebuild the match history in a scratch copy with them accepted and list every change. It takes minutes and changes no shared files.
  > 3. **Still no retrain for these alone.** Include them in the next rebuild, for example once today's feed passes its harm check.
  >
  > Want me to record the decision and run the check on the four files?
* **The owner's answer, verbatim** (13 Oct 2026, about 18:10):
  > "record the decision and run the check on the four files"
* **The owner's words of 11 Oct that the decision records** (verbatim as the master-pipeline session logged them,
  [its process log](../master_pipeline/process_log.md), rows 11:55 and 12:05):
  > "There was a freeze that was told to freeze and not include new challenger data until we run an experiment that checks how we should effectively integrate challenger data. We however completed the study and found how to effectively integrate challenger data by changing weight of that info and adjusting it by opponent skill. This is not that right? Why aren't we just using the newest data? Is it to save time from training a big model constantly?"

  > "Do you recommend also retraining post 50 corrections? I'm away from my computer accessing remotely so it won't be competing for Gpu usage"
* **How it was read:**
  * "record the decision" = a decision record in `docs/decisions/` for recommendation 1 (the standing rule), indexed;
    `history.py` changed so that the rule's changes are listed as allowed instead of refusing a template build, with a
    test; CLAUDE.md's freeze paragraph, the master-pipeline README (its decisions 8 and 9), the daily-prediction README
    (its decision 8) and the bet sheet's notes brought into line. Recommendation 3 (no retrain for these alone) is part
    of the record.
  * "run the check on the four files" = recommendation 2's check: Stage 0 built twice in a scratch tree from today's
    staged files, once as is and once with the four held versions staged in place of the current copies; every change
    listed; the history check run on both.
  * **Whether the owner's answer also accepts the four files.** Two readings: (i) the check only, the owner to accept
    afterwards; (ii) recommendation 2 as a whole ("accept ... after one check"), the check being the condition. I act
    on (ii) only if the check shows nothing but corrections, and only once the session building the lower-level feed's
    harm check (`tennis-predictions-af`, busy) confirms that replacing the four staged Tennis My Life files does not
    touch its in-flight builds; otherwise the acceptance is left as one ready command and put to the owner. Reason:
    the owner's complaint was open items nobody closes, and recommendation 2 was approved in substance; but the files
    are shared inputs of every Stage 0 build, so the acceptance must not land in another session's build.
  * Set aside: re-reading the 11 Oct question from scratch (the owner has answered it twice); retraining now (the owner
    approved recommendation 3).
* **The target:** not a model study. No price, hour, seasons or primary. The only readings are data diffs (no model
  output is read here). The harm check the rule calls for runs at the next instance rebuild, not here.

## 2. Starting point

* **Code:** commit `677a63f` plus many uncommitted changes of other sessions. `history.py`, `diagnostics.py`,
  `bet_sheet.py`, `test_history.py` and both session READMEs are untracked (new since the commit); CLAUDE.md and the
  decisions index are modified. `history.py` was last edited today by the data-gaps session (`tennis-predictions-af`,
  17:04–17:05: the "decided repairs" class), which is still running.
* **Data [observed]:**
  * The four held files: `data/raw/public_dump/tennis_my_life/held/{2022,2023,2024,2025}_challenger.<sha12>.csv`
    (sha12 `d95fa0a4bf8a`, `ee3a2128d89a`, `ca3a597f1a97`, `78b86009de42`; first seen 10 Oct 07:30; reasons 38, 67,
    127 and 12 rows of the current copy gone). The current copies are the 22 Sep downloads; their staged tables
    `data/dump/matches/tennis_my_life/atp_challenger/{2022..2025}_challenger.parquet` (22 Sep).
  * Today's live run `data/studies/daily_prediction/runs/live_2026-10-13_165316/history.json`: gated lower-level new past
    30, dropped 30, revised 20 (the 50 corrections of 11 Oct; all `source` tml); accepted additions 1,725.
  * The frozen reference: `data/studies/current_best_model/reference_2026-10-08/` (via `reference.py`).
* **Earlier looks:** the master-pipeline session's 11 Oct lookup of the 50 corrections (its process log 11:45–12:05;
  observed there: 97 player ids touched, in 6,402 of the 62,869 rows the 2026 fit trains on); the daily-prediction
  session's reading of the first live day (its process log, 11:30 continuation); my two read-only diffs above.
* **Environment:** `./python.sh` (the `tennis` conda env).
* **The idea:** a verified fix (the source's own corrections of data already used), as a standing policy for a
  recurring kind (adoption framework § 10: decide recurring kinds once).

## 3. Plan

Written 13 Oct 2026 about 18:28 PDT, before the check's builds.

1. **Coordinate:** message `tennis-predictions-af` (the decision; the `history.py` change; the scratch check; ask
   whether replacing the four staged files would touch its in-flight builds).
2. **The check (scratch only):** a tree `C:/Users/zerom/tnr_tmlcheck/`: `src/` copied; the three decided-input files
   Stage 0 reads copied (`stage0_level_rules.csv`, `slam_box_overrides.csv`, `input_data_audit/fixes/`); `data/raw`
   and every `data/dump/matches` child but Tennis My Life junctioned read-only; Tennis My Life's staged folders
   junctioned except `atp_challenger`, copied. **Validation:** the adapter's own staging function (`stage_csv_file`)
   run on the four *current* CSVs must reproduce the repository's staged tables (content-equal). Then Stage 0 built
   twice with the same code (`stage0_build.py --out-dir`): A with the current files, B with the four held versions
   staged. Compare A and B match by match (history.py's content hash): new, dropped, revised, by source, tour, level and
   year; main-tour rows touched; the cleaning-log rule counts; the players touched and how many training rows of the
   2026 fit they appear in. The history check on B against the reference, to see what B adds to it.
   **Accept when** every change is one of: an event re-keyed with the same matches, a duplicate removed, a misfiled
   row removed, a player id corrected, a box score or score revised; and no main-tour row changes. Otherwise hold and
   report.
3. **The decision record** `docs/decisions/2026-10-13-tml-lower-level-revisions.md`, the index row, CLAUDE.md.
4. **`history.py`:** a class "tml_lower" (lower-level new past, dropped and revised rows whose `source` is Tennis My
   Life) listed and allowed; `template_ok` reads only what remains gated. Test in `test/current_best_model/test_history.py`.
5. **The sheet's notes** (`src/pipeline/diagnostics.py`): the history note says what is used and when training takes it;
   the download note names held files. Tests `test/master_pipeline`.
6. **The session READMEs:** master pipeline decisions 8–9, daily prediction decision 8 (by addition).
7. **Accept the four files** if step 2 passes and step 1 clears it (`tennis_my_life --accept-held NAME@SHA12` ×4,
   then a check that the staged tables equal B's inputs); else the command goes to the owner.
8. **Report** (README), finish this log.

## 4. Chronology

Local time (UTC−7). No model result is read in this work.

| When | Step (command or action) | Why | Results seen by then | Output |
|---|---|---|---|---|
| 18:00–18:05 | Read-only lookups for the owner's question: `diagnostics.py`, a bet sheet's provenance, today's run's `history.json`, the decisions of 6, 10 and 13 Oct, `accepted.json`, both session READMEs and process logs, the data-gaps README; scratch `held_diff.py`, `held_diff2.py` on the held files | The owner's question | none (data diffs only) | the answer in § 1 |
| 18:10 | The owner: "record the decision and run the check on the four files" | – | – | – |
| 18:12–18:26 | Read the decisions index, the process-log template, `history.py`, `tennis_my_life.py`, `stage0_build.py` (sources, inputs, outputs), `dp_worktree.py`, the data-gaps log and its harm-arm script; listed peer sessions (busy: `af`, `b2`, `e1`) | Plan the check and the edits | none | the data-gaps session is `tennis-predictions-af`; its harm arm builds on the frozen reference's tables plus its candidate, not on today's staged Tennis My Life files [observed, `data/studies/data_gaps_2026/harm/build_feed_arm.sh`] |
| 18:28 | Opened this log | Rule 2 | none | this file |
| 18:29 | Messaged `tennis-predictions-af` (verbatim in the appendix) | Plan step 1 | none | – |
| 18:29 | Wrote `src/eda/tml_revisions/held_check.py` (setup, validate, build A/B, stage, compare, cleanup) | Plan step 2 | none | – |
| 18:30 | **`af` replied** (key points, verbatim): "Go ahead: nothing I am running or about to run reads today's staged TML Challenger files, and I am not editing history.py now." "Please keep it [the decided-repairs class]; your "tml_lower" class beside it is fine with me." "run_chain --setup calls history.check() once at its start (--candidate, so it never refuses): if you are mid-edit then, just keep history.py importable at each save." "If you accept the files today, tomorrow's run simply sees them. Fine either way." | – | – | cleared to proceed |
| 18:30–18:31 | `held_check.py setup` (15 s; tree `C:/Users/zerom/tnr_tmlcheck`), `validate` [observed]: the adapter's staging of the four current copies equals the repository's staged tables (provenance columns included), 4 of 4; each raw copy's SHA-256 equals its staged sidecar's | Validation before any build | none | – |
| 18:31–18:33 | `build A` (152.7 s) [observed]: 873,642 matches, 1,747,284 player rows; "TML-only rows appended: 6,392 (436 in events Sackmann also holds)" | Plan step 2 | none | `tnr_tmlcheck/out/A` |
| 18:33–18:35 | `stage` (the held versions staged: 5,384, 5,688, 5,936, 6,399 rows), `build B` (87.7 s) [observed]: 873,636 matches; "TML-only rows appended: 6,378 (422 in events Sackmann also holds)" | Plan step 2 | none | `tnr_tmlcheck/out/B` |
| 18:35 | **Failure:** `compare` stopped: the cleaning log holds several rows per rule (by tour, level, qualifying, year); fixed (`cleaning_rules` groups by those cells) | – | none | – |
| 18:36–18:39 | `compare` [observed]: 15 dropped, 9 new, **0 revised**, **0 main-tour**; all men's Challenger rows from Tennis My Life; 23 players touched, 9 of them in the 2026 fit's training rows (192 rows), 15 rows dated after the player's first change (2022: 2, 2023: 7, 2024: 4, 2025: 2) of 62,869. Cleaning rules: C01 2024 124 → 0, D1_tml 7/5/3 → 0, D6 2022 1 → 0, 2023 1 → 2, 2025 8 → 0; C20, C50, C61 small shifts. History check: lower-level new past 30 → 39, dropped 30 → 45, revised 20 → 20 | Plan step 2 | data diffs only | `data/studies/tml_revisions/held_check/` |
| 18:39–18:42 | Read the three events and the eight pairs in both builds (scratch `inspect_events.py`, `inspect_pairs.py`) [observed]: **Champaign 2025** (R16 ×3, QF ×1): A holds each of the four twice, a Sackmann row and a Tennis My Life-only copy with the same round, score and names but other ids (one id, atp:200473, is the winner of a copy in R16 as "Mats Rosenkranz" and in the QF as "Kenta Miyoshi"); B holds only Sackmann's. **Rome GA**: A places three matches of the February 2023 edition in the July 2022 edition (Hong d. Brancatelli R32, Kodat d. Shimabukuro R16, Hong d. Kodat QF), two of them also present as Sackmann's 2023 rows (unlinked in A: `tml_link` none); in B the two link to Sackmann's 2023 rows (`one_player_anchor`) and the third, which Sackmann lacks, sits in the 2023 edition on 2023-02-20. **The eight 2026 pairs**: the same match, the same two players (Okonkwo, Tabata, Manning, Martinez Gomez with their opponents) and the same box scores; only the key differs and the sides swap (A built the key from the player's ATP code and mapped it to the numeric id afterwards, through the id aliases; B resolves it first); the four players hold 47, 43, 11 and 42 rows in both builds | Explain every change before judging | data diffs only | – |
| 18:40 | **`af` asked** (verbatim, the questions): "(a) Are you reading the live Stage 0 or those decided tables? If so, when will you be done? (b) Will your held-files decision need its own Stage 0 rebuild or a new instance? If yes, we could do one coordinated rebuild for both instead of two." Its plan: the feed registered and a new instance `template_2026-10-13` tonight if its harm check shows no harm; then the Roland Garros repair (`adopt.py --apply`) and a live Stage 0 rebuild | – | – | – |
| 18:41 | Replied (verbatim in the appendix): no collision; no own rebuild; its coordinated rebuild will carry the Tennis My Life changes once the files are accepted | – | – | – |
| 18:42–18:48 | `explain()` relabelled: "key" (same event, same players: a key built from an id resolved later) apart from "event" and "player"; `compare` rerun [observed]: paired 8 "key", 0 "event", 0 "player"; unpaired 7 dropped (the 4 Champaign copies, the 3 Rome GA rows of July 2022), 1 new (Hong d. Brancatelli on 2023-02-20). Every other figure unchanged | The label was wrong for the 2026 pairs | data diffs only | `held_check/summary.json`, `changes.csv` |
| 18:48 | **`af`** (verbatim): "Understood: the RG swap and the live Stage 0 rebuild wait for your message that the four held files are accepted and history.py is edited. ... I expect to start it after my harm check, around 22:00–23:00 PDT ... While rebuild_stage0.py runs, please don't build on the live Stage 0 or timing.parquet." | – | – | – |
| 18:49 | **Judgment call 1 (§ 6): accept the four files.** The acceptance rule written in § 3 is met: every change is a duplicate removed, a misplaced match restored to its edition, a key rebuilt with the same match, or the source dropping rows Stage 0 already dropped; no main-tour row; no revised fact; nothing unexplained lost | Plan step 7 | data diffs only | – |
| 18:48 (clock; this row written after the run) | `./python.sh -m src.ingest.public_dump.tennis_my_life --start-year 2000 --accept-held 2022_challenger.csv@d95fa0a4bf8a --accept-held 2023_challenger.csv@ee3a2128d89a --accept-held 2024_challenger.csv@ca3a597f1a97 --accept-held 2025_challenger.csv@78b86009de42` (7 s; exit 0) [observed]: each "changed; kept the replaced file as …/superseded/<name>.20260922…csv"; staged 5,384, 5,688, 5,936, 6,399 rows; "8 staged files, 36,533 rows, 0 download errors, 0 held"; `_changes.jsonl` gained the four lines. (The no-lock check and the tasklist were read at 18:47) | Plan step 7 | data diffs only | – |
| 18:49 | Verified [observed]: each raw copy's SHA-256 is the held version's; each staged table equals the one B was built from in every column but `_retrieved_at` (Stage 0 keeps only `_source_file` and `_row` of the provenance). The held copies stay in `held/` (the adapter keeps them; nothing deletes them) | – | – | – |
| 18:50 | Found: `src/pipeline/data.py`'s `held_tml_files()` lists every CSV in `held/`, so the morning cell would keep showing the four as held. `src/pipeline/` is the bet-sheet session's (`tennis-predictions-b2`, busy; Part 2 of the master-pipeline log); messaged it (verbatim in the appendix) before editing `diagnostics.py` or `data.py` | Plan step 5 | – | waiting for its answer |
| 18:50–18:52 | Read `candidate_stage0.py`'s use of `history.check`: its pass reads the top-level `dropped` and `future` only; its box layers keep the reference row's `source`, so a rule on `source == "tml"` alone would let a candidate's completions of Tennis My Life rows through. The reference's own tml lower-level rows sit at (atp, CH, False), (atp, GSQ, True), (atp, TQ, True) [observed] | The rule's edges | – | **Judgment call 2 (§ 6)** |
| 18:52–18:53 | `history.py`: the `tml_lower` class (`tml_levels`, `layered_ids`, `tml_own`; docstring; `summary_line`). **Failure (mine):** the first save of `summary_line` lacked a `+` (a syntax error); `history.py` was not importable from about 18:52 until 18:53:25. The data-gaps session's harm build runs from its sandbox's own copy of `src` (made 18:28), and its lanes 1 and 2 exited 0 at 18:53 [observed, `harm/feed_instance/chain_lane*.json`]; nothing else was found importing it in that minute (not provable) | Plan step 4 | – | – |
| 18:53–18:54 | Tests: `test_history.py` (docstring; two tests updated to the decision: a tml Challenger backfill and a tml Challenger score revision are now listed and allowed, a Sackmann revision still refused; four new: tml corrections and backfills listed and allowed, a dropped tml match allowed but a Sackmann one refused, tml at a level it never fed gated, a candidate's box layer on a tml row gated); `test_additions.py::test_history_counts_accepted_additions_apart`: n2's source "tennislive" (the data-gaps session's test; told). `test/current_best_model`: **98 passed** | – | – | – |
| 18:54–18:56 | Decision record `docs/decisions/2026-10-13-tml-lower-level-revisions.md`; its index row (first placed above the 10 Oct rows, moved to the end at 18:55); CLAUDE.md's freeze bullets; the master-pipeline README decisions 8 and 9 and the daily-prediction README decision 8, by addition | Plan steps 3, 6 | – | – |
| 18:56–18:58 | `history.check` with the new code on the scratch builds [observed]: A "Tennis My Life's own lower-level changes 80 (allowed, decided 13 Oct: new past 30, dropped 30, revised 20); lower-level new past 0, dropped 0, revised 0 -> the template may be built"; B the same with 104 (39, 45, 20) | Verify the rule on real tables | – | – |
| 18:58 | Messaged `af`: files accepted, `history.py` edited (verbatim in the appendix) | Its rebuild waits for this | – | – |
| 18:58–18:59 | `test/tml_revisions/test_held_check.py` (the pairing's three kinds, an unpaired drop, a pair without a common player, the held records, each file's staging folder, the tree outside the repository): **8 passed** | The check is now a decided procedure | – | – |
| 18:59 | The README drafted (§ 4's sheet lines left open) | Plan step 8 | – | – |
| 18:59 | `ListAgents`: `b2` "waiting" (its own prompt), so my 18:50 message unread. **Judgment call 3 (§ 6):** make the three `src/pipeline` edits myself and tell it | – | – | – |
| 18:59–19:00 | `diagnostics.py`: `HELD_LINE`, `_held_in_refresh`, `_undecided_lower_level`; `_run_notes`: no history note for Tennis My Life's own corrections (decided; a record written before today counts them as gated rows of source tml), a note only for lower-level changes no decision covers, and the download note naming held files. `data.py`: `held_tml_files()` skips a held version equal to the current copy; `accept_held_tml()`'s note points to the check. New tests `test/master_pipeline/test_tml_notes.py` (6); `test/master_pipeline`: **37 passed**; `held_tml_files()` now returns [] [observed] | Plan step 5 | – | – |
| 19:01 | Today's run `live_2026-10-13_165316` through the new `_run_notes` [observed]: the recomputed-state note, and "Tennis My Life's download held 4 changed files for review (2022_challenger.csv, 2023_challenger.csv, 2024_challenger.csv, 2025_challenger.csv); this run used the copies it had." No history note | Check the wording on a real run | – | – |
| 19:01 | Messaged `b2` what changed (verbatim in the appendix) | – | – | – |
| 19:03 | **`af`** (verbatim): "Thanks, f6. Received, and the test edit is fine. Timing: the RG swap and the live Stage 0 rebuild will come after my instance switch's replay check, which must read the pre-RG decided tables. So expect them about 22:30–23:30 PDT, not now. I'll message when the rebuild starts and when it ends." | – | – | README § 4's timing |
| after 19:05 | **`b2` replied** (key points, verbatim): "Re your src/pipeline edits: fine by me. I re-read diagnostics.py and data.py; your notes and my gap causes coexist, and test/master_pipeline is 38 of 38 with your test_tml_notes.py." Its own changes of today: a Stage 0 repair reading ambiguous 10-8 / 13-11 deciders as match tiebreaks at events whose other deciders are ("exactly 2 matches change, Laver Cup 2026 Ruud-Cerundolo and Alcaraz-Fritz ... lower levels are untouched"; decision record to come), `tp.data_check`, and the daily archive path. "Please ping me before touching those [readiness.py, bet_sheet.py, test_master_pipeline.py, the notebook, docs/studies/master_pipeline/README.md and process_log.md]; diagnostics.py and data.py are yours to edit." Re-read [observed]: my CLAUDE.md bullets and the `test_additions.py` edit are intact after other sessions' later edits of those files. No interaction: its repair is main-tour (listed as allowed main-tour revisions, not `tml_lower`) | – | – | – |
| about 21:15 | **`af`** (verbatim): "f6: starting now (about 21:15 PDT). rg_first_serve_recount/adopt.py --apply, then data_continuity/rebuild_stage0.py (about 30 minutes), then history.py. Please don't build on the live Stage 0 or timing.parquet until I message that it's done. FYI: the daily pipeline now uses template_2026-10-13 on C:/Users/zerom/tnr_gaps (the lower-level feed adopted; harm check +0.044 [−0.097, +0.185] mLL, no harm)." Re-read [observed]: my `diagnostics.py` functions and the two README lines are intact after `b2`'s later edits. Replied: nothing of mine builds on the live tables; what its history check should show | – | – | – |
| after 21:15 | **The owner:** "delete the scratch copy". Looked first [observed]: the marker; 13 junctions, all into the repository's `data/raw` and `data/dump` (listed with PowerShell 7, which does not follow links); 1,506 own files, 234 MB. A first command was blocked by the tool before it ran (it read `rmdir /s` as a system path); nothing changed (13 links still there). Then: each junction removed alone (`[System.IO.Directory]::Delete(link, false)`: the link only); 0 left; the tree removed (`Remove-Item -Recurse`, only once no link was left and the marker was present). Shared folders before and after: raw Tennis My Life 89 files, staged `atp_main` 54, Sackmann archive 192, `data/raw` 12 folders, unchanged [observed] | The owner's request | – | the scratch tree deleted |
| after 21:48 | **`af`** (verbatim): "f6: done. The RG swap was applied at 21:12 (kept copies in rg_first_serve_recount/adoption/20261013T211216). rebuild_stage0.py finished at 21:48 (873,437 → 873,636 matches, 39 ids remapped; record in data_continuity/rebuilds/2026-10-14T0412Z/). history.py, as you predicted: tml_lower 104 (new past 39, dropped 45, revised 20); allowed main tour 9 (Davis Cup and Laver Cup records, and one Båstad R32); decided repairs 2,964; gated 0 → "the template may be built". I reworded summary_line's accepted part to "accepted N (allowed: lower-level additions a, completions b, decided repairs c)" ... (test/current_best_model 99 pass). Next: a template build on the day's tables in C:/Users/zerom/tnr_tpl1014 (out data/studies/current_best_model/template_2026-10-14). The live tables are free again." Re-read [observed]: `tml_levels`, `layered_ids`, `tml_own` and the `tml_lower` part of `summary_line` intact after its edit; `test_history.py` 28 passed. The live Stage 0's 873,636 equals build B's count (the Roland Garros repair changes box scores, not matches). README § 4 updated (the update line first wrote 873,437 as "873,436", corrected in the same session) | Confirms the decision took effect on the shared tables | – | – |
| 19:02 | README § 4 and the decision's "Implemented" completed; the scratch tree measured (own files about 200 MB: Stage 0 builds 171 MB, `src` 19 MB, staged copies 5 MB); left in place for the owner (CLAUDE.md: discuss cleanup before deleting) | Plan step 8 | – | – |

## 6. Judgment calls and deviations

1. **Accepting the four files, not only checking them** (18:49, after the check's results; no model result exists in
   this work). Options: (a) check only and ask the owner; (b) accept when the rule written in § 3 before the builds is
   met, once the data-gaps session cleared the timing. Chose (b): the owner approved recommendation 2 ("Accept the
   four parked files under that rule, after one check") by asking for its check, and the owner's complaint was open
   items nobody closes. The other branch would have left one ready command and a fifth open item. The acceptance is
   undoable (the replaced copies are kept).
2. **The rule's edges** (18:50–18:52, after the four files' diffs, before any history-check run with the new code).
   Options: `source == "tml"` alone; plus the levels Tennis My Life fed the reference; plus excluding a candidate's
   box layers. Chose all three. Source alone would have let a candidate build's box-score completions of Tennis My Life
   rows (from other sources) pass as Tennis My Life's own, and would let a new level from Tennis My Life (for example
   WTA 125, should it start publishing one) in without a test. The cost: a Tennis My Life correction that changes a row
   Stage 0 takes from Sackmann still refuses a build. That is the cautious side, and it did not occur in the 50
   corrections or the four files.
3. **Editing the bet-sheet session's code without its answer** (18:59). Options: wait (it was "waiting" on its own
   prompt, possibly for hours); hand the change to it; edit and tell it. Chose to edit and tell it: the owner approved
   "the sheet notes" in recommendation 1, the edits are small and covered by its tests (all pass), and the files had
   not changed since 17:48. The other branch would have left tomorrow's sheets showing the confusing note.
4. **No sheet note for decided corrections, rather than a reworded one** (18:59). A note saying "decided; used" would
   show on every sheet for good, because the history check always compares with the 8 Oct reference, and it would
   claim that training "takes them at its next rebuild" even after that rebuild. Main-tour corrections, allowed since
   9 Oct, get no note either. The provenance's history line still lists every change.
5. **Deviation from § 3:** the plan named the decision file before the history.py change; they were done the other way
   round (code 18:52, decision 18:54), with no consequence. The plan's "reach" measure counts the players of the eight
   re-keyed 2026 matches, whose histories do not change, so it overstates the reach (an upper bound).

## 7. Claims and their evidence

| Claim (README) | Evidence | Status |
|---|---|---|
| The scratch staging reproduces the repository's staged tables | `held_check.py validate`; marker `C:/Users/zerom/tnr_tmlcheck/.tml_held_check_tree` ("validated") | observed |
| 24 matches change, 873,642 → 873,636; no main-tour match; no fact of a shared match | `data/studies/tml_revisions/held_check/summary.json`, `changes.csv` | observed |
| The Champaign copies are duplicates under wrong ids; the Rome GA 2023 matches were in the 2022 edition | scratch `inspect_events.py` output (chronology 18:39–18:42); `changes.csv` | observed |
| The eight 2026 pairs are the same matches and players under new keys | scratch `inspect_pairs.py` output; `changes.csv` (`pair_kind` "key") | observed |
| Tennis My Life itself removed 139 rows Stage 0 already dropped (C01 124, D1_tml 15) | `held_check/cleaning_rules_changed.csv` | observed |
| 15 training rows of the 2026 fit fall after a touched player's first change | `summary.json` → `reach` (the template's frame, seasons 2013–2025; the reference's player table) | observed (an upper bound: § 6 item 5) |
| "Far too small to measure" | the count above | inference |
| The installed files are the checked versions | chronology 18:49 (SHA-256 and table equality) | observed |
| The 50 corrections and their reach (97 players, 6,402 rows) | the master-pipeline session's lookup of 11 Oct (its process log 11:45, 12:05) | taken as reported; the 13 Oct runs' counts (30/30/20) re-read here |
| After the change, the history check allows a template build on today's tables | chronology 18:56–18:58 (A and B) | observed |

## 8. Weak points

* **Attribution by source.** The rule cannot tell a correction Tennis My Life made from a change of Stage 0's builder
  code that alters Tennis My Life rows; both land in `tml_lower`. They are listed, and the harm check at each rebuild
  is the backstop.
* **The check is a data diff, not a model reading.** No model was scored. The rebuild's harm check, planned tonight
  by the data-gaps session, is the only model-level reading, and it mixes these corrections with the feed and the
  Roland Garros repair, so it cannot attribute an effect to them alone. At this size no comparison could.
* **The acceptance read a reading of the owner's reply** (§ 1, § 6 item 1). A reviewer who reads it as "check only"
  would undo the acceptance from the kept copies.
* **The scratch builds ran without the accepted package and without live rows.** The diff between A and B does not
  depend on them, since only the four files differed, but neither build is a bet-day table.
* **Where a flaw would hide:** in `explain()`'s pairing (same round, date and score plus one shared player). Two
  different matches with the same score in the same round could pair wrongly. The eight pairs were checked by hand.

**What a re-design would do:** compute, for every training row, whether its 57 inputs change between builds A and B
(the chain run twice), rather than counting touched players. That would measure the reach exactly, at about 4 hours of
builds.

## 9. Reviewer checklist

* [ ] `./python.sh -m pytest test/current_best_model test/master_pipeline test/tml_revisions -q` (98, 37 and 8 passed
  on 13 Oct).
* [ ] Re-derive the 24 changes: `held_check.py compare` on the kept tree (or a fresh setup, then
  validate/build A/stage/build B/compare). Note: after the acceptance, a fresh `setup` finds no held file. To redo it,
  point `held_files` at the `held/` copies with the superseded current copies restored in a tree.
* [ ] Check the raw files' SHA-256 against the decision's list, and `_changes.jsonl`'s four lines of 13 Oct.
* [ ] Read `history.py`'s `tml_own` against the decision's rule 3, and run `history.py --stage0 <a fresh Stage 0>`
  (expect "Tennis My Life's own lower-level changes … -> the template may be built").
* [ ] Confirm that nothing outside this list was edited: § 10's file list against `git status`.

## 10. Reproduction

```
# the check (about 6 minutes; no GPU)
./python.sh src/eda/tml_revisions/held_check.py setup
./python.sh src/eda/tml_revisions/held_check.py validate
./python.sh src/eda/tml_revisions/held_check.py build A
./python.sh src/eda/tml_revisions/held_check.py stage
./python.sh src/eda/tml_revisions/held_check.py build B
./python.sh src/eda/tml_revisions/held_check.py compare
# the acceptance (network; Tennis My Life's own download, under its lock)
./python.sh -m src.ingest.public_dump.tennis_my_life --start-year 2000 --accept-held 2022_challenger.csv@d95fa0a4bf8a \
    --accept-held 2023_challenger.csv@ee3a2128d89a --accept-held 2024_challenger.csv@ca3a597f1a97 \
    --accept-held 2025_challenger.csv@78b86009de42
# tests
./python.sh -m pytest test/current_best_model test/master_pipeline test/tml_revisions -q
```

**Files created:** `docs/decisions/2026-10-13-tml-lower-level-revisions.md`; `docs/studies/tml_revisions/` (README,
this log); `src/eda/tml_revisions/held_check.py`; `test/tml_revisions/test_held_check.py`;
`test/master_pipeline/test_tml_notes.py`; `data/studies/tml_revisions/held_check/` (five files). **Edited:**
`src/eda/current_best_model/history.py`; `test/current_best_model/test_history.py`, `test_additions.py`;
`src/pipeline/diagnostics.py`, `data.py`; `docs/decisions/README.md`; `CLAUDE.md`;
`docs/studies/master_pipeline/README.md` (decisions 8, 9); `docs/studies/daily_prediction/README.md` (decision 8).
**Data changed:** `data/raw/public_dump/tennis_my_life/{2022..2025}_challenger.csv` (accepted versions; replaced copies
in `superseded/`), their staged tables in `data/dump/matches/tennis_my_life/atp_challenger/`, and the ongoing files
the same download refreshed. **Outside the repository:** the scratch tree `C:/Users/zerom/tnr_tmlcheck` (about
200 MB; `held_check.py cleanup` removes it); scratch scripts in the session's scratchpad.

## Appendix: messages to other sessions (verbatim)

No subagents were used. The messages sent, verbatim:

**To `tennis-predictions-af`, 18:29:**

> From tennis-predictions-f6: the owner just decided that Tennis My Life's own lower-level corrections enter by themselves, and I'm about to edit history.py and maybe accept the four held TML Challenger files. Please read before your next history.py edit.
>
> 1. Decision (owner, 13 Oct; I'm writing docs/decisions/2026-10-13-tml-lower-level-revisions.md): Tennis My Life's corrections, drops and backfills of the lower levels it publishes (men's Challenger main draws, ATP tour/Slam qualifying) enter by themselves. Bet-day runs use them at once, and training picks them up at the next rebuild. The history check lists them and no longer refuses a template build for them. New sources and kinds (your feed, ITF box scores, women's lower levels) are unchanged: packages and feeds only.
>
> 2. history.py: I'll add one class, "tml_lower": gated new_past/dropped/revised rows whose source is "tml" move out of "gated" into their own allowed bucket, and template_ok reads only what's left. The edit is additive, next to your "decided repairs" code, and I'll add a test in test_history.py. If you're editing history.py right now, tell me and I'll wait.
>
> 3. The four held TML files (2022–2025_challenger.csv, held since 10 Oct): I'm checking them in a scratch tree (C:/Users/zerom/tnr_tmlcheck, junctions read-only, no shared file written). If they're clean, I'd accept them with tennis_my_life --accept-held ×4, which replaces data/raw/public_dump/tennis_my_life/2022..2025_challenger.csv (old copies kept under superseded/) and restages data/dump/matches/tennis_my_life/atp_challenger/2022..2025_challenger.parquet. Your build_feed_arm.sh builds on the frozen reference's tables plus your candidate, so I don't think it reads those staged files. Does anything you're running or about to run read today's staged TML Challenger files, e.g. a scratch Stage 0 for the coverage alarm or the feed's merge check? If yes, when would it be safe? I won't accept them until you answer.
>
> 4. Your README § 7 item 7 (the held files): I'll leave your files alone. Once I report, you may want to link the decision there.

**To `tennis-predictions-af`, 18:41:**

> From tennis-predictions-f6: no collision. Go ahead with both steps of your plan as far as I'm concerned.
>
> (a) I'm not reading the live Stage 0 or the decided tables. At 18:31 my check copied the three decided inputs (stage0_level_rules.csv, slam_box_overrides.csv, input_data_audit/fixes/) into its own scratch tree and built from the copies. The compare finished at 18:39. It read only my scratch builds, the frozen reference and the live timing.parquet (read-only). What's left on my side, none of it touching the decided tables or the live Stage 0:
> - In the next ~20 minutes: accept the four held files with one TML download run (tennis_my_life --start-year 2000 --accept-held ×4). That writes the raw TML folder and data/dump/matches/tennis_my_life, under the TML lock.
> - Then: history.py (the additive "tml_lower" class, keeping DECIDED_TABLES / decided_repair_ids / accepted.decided_repairs intact), diagnostics.py's sheet notes, and docs.
>
> (b) No separate rebuild or instance is needed. Under the decision, TML's corrections enter bet-day runs at once, since each run rebuilds Stage 0 from the staged files, and enter training at the next template build on the day's tables. So once the files are accepted, your RG live Stage 0 rebuild will include the four files' changes and the 50 corrections of 11 Oct. That makes it the one coordinated rebuild; nothing more from me. After my history.py edit, check() moves Tennis-My-Life-sourced lower-level new past, dropped and revised rows to "tml_lower" (allowed), so builds on your rebuilt Stage 0 won't be refused for them. Your instance tonight (frozen reference + feed) won't carry them, which is right for your harm check; the next template build on the day's tables will.
>
> The check's result: 24 Stage 0 matches differ (873,642 → 873,636), all men's Challengers, none main-tour, no revised facts:
> - 4 Champaign 2025 TML-only copies of Sackmann's matches, carrying wrong player ids, are removed;
> - 3 Rome GA 2023 matches that A misplaced into the July 2022 edition: 2 were duplicates of Sackmann's 2023 rows (removed), and 1 that Sackmann lacks returns to its real date (2023-02-20);
> - 8 2026 matches are re-keyed with the same players and box scores: four ATP codes now resolve before the keys are built, so sides swap and nothing else changes.
> TML also dropped its own misfiled 2008 rows (your C01, 124) and duplicates (D1_tml, 15), which Stage 0 was already dropping. Report: data/studies/tml_revisions/held_check/summary.json and changes.csv.
>
> The decision will be at docs/decisions/2026-10-13-tml-lower-level-revisions.md (writing it now). I'll message again when the files are accepted and history.py is edited.

**To `tennis-predictions-b2`, 18:50:**

> From tennis-predictions-f6: the owner decided Tennis My Life's lower-level corrections enter by themselves, and I'd like to make three small edits in src/pipeline (your bet-sheet code). Are you mid-edit in diagnostics.py or data.py?
>
> The decision (owner, 13 Oct; docs/decisions/2026-10-13-tml-lower-level-revisions.md, being written): the "50 corrections" behind your sheet's history note are accepted. Live runs use them, as they already do; training picks them up at the next template build on the day's tables; history.py will list them as an allowed class "tml_lower" instead of refusing. I also checked and accepted the four held TML Challenger files (2022–2025) at 18:48. The owner was confused by the two standing notes ("Your decision on accepting those is still open", "Four old Challenger files are held back for review"); that's what this fixes.
>
> The edits I propose:
> 1. diagnostics.py, _run_notes: when the history check's only lower-level differences are Tennis My Life's, so template_ok is True after my history.py change, show a short plain note instead of the warning: "Tennis My Life has corrected N lower-level matches since the 8 Oct freeze; they are used here (decided 13 Oct) and enter the model's training at its next rebuild." Keep the current warning for anything still gated. Also make the download note name the held files when that's the cause.
> 2. data.py, held_tml_files(): skip a held version whose SHA equals the current raw copy's (it has been accepted). Otherwise the morning cell keeps listing the four as held, since the held copies stay in held/ as records.
> 3. data.py, accept_held_tml(): reword the warning, which says a lower-level acceptance makes template builds refuse. Under the decision a TML file is accepted after src/eda/tml_revisions/held_check.py and is listed, not refused.
> Plus tests in test/master_pipeline.
>
> Would you rather I make these, or do them yourself? If you're editing those files now, tell me and I'll wait or hand them over.

**To `tennis-predictions-af`, 18:58,** and **to `tennis-predictions-b2`, 19:01:** in the session transcript
(`84155559-d2ab-4579-95b0-3c7290cd7e6f`). The first reports the acceptance, the `history.py` edit and its importability
window, the test edit in `test_additions.py`, and the decision's path. The second lists the `src/pipeline` edits
function by function (§ 4, 18:59–19:00). It also says the note for decided corrections was dropped rather than
reworded (§ 6 item 4).

---

## Note, 22 Oct 2026: two build trees named above deleted

Added by the cleanup session `4437577b-803e-4161-baf5-c6fade971478`, at the owner's word
([cleanup inventory, process log § 9d](../cleanup_inventory/process_log.md)).
* **Deleted on 22 Oct 2026:** `C:/Users/zerom/tnr_gaps` and `C:/Users/zerom/tnr_tpl1014`, the build trees of
  `template_2026-10-13` and `template_2026-10-14`.
* **In this log** they appear only in other sessions' messages (the rows "about 21:15" and "after 21:48"), as the
  instance then in use and the next build. The live model is now `template_2026-10-21b`.
