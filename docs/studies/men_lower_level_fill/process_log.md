# The men's lower-level fill: process log

16 Oct 2026 (local, UTC−7), from 13:43 · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code) · Session:
`c0f7c8d9-cc78-498f-9409-72258b59a7dd` · For a future reviewer · Report: [README.md](README.md)

## 1. The request

* **The owner's words, verbatim** (16 Oct 2026, about 13:40):
  > "Add the men's 4,246 matches now
  >
  > And start a "to_do" list for womens model , as its currently needs a fix to be bettable. Maybe fill in data holes, new stats. Including relating lower level to high level matches etc. Adding the data thats not in for it"
* **What "the men's 4,246 matches" are** (this session's count, earlier the same day, from files only): the men's part of
  the lower-level matches the level-evidence study collected on 9–10 Oct (its candidate C0_now) that are still outside
  the model's builds (the live Stage 0, the accepted packages and the feed's snapshot 20261014), leaving out ITF
  qualifying:
  * ITF main draws 3,274; Challenger qualifying 952; Challenger main draws 20;
  * 723 of them involve a player with a main-tour main-draw match within 365 days.
* **The owner had been told** (the preceding messages, verbatim in the session): ITF results count at a quarter in the
  ratings and in full in the workload counts; the men's 3,274 and 972 were recommended because they fill holes in data
  the model already uses that way; "Expect no measurable change in betting results; this is housekeeping, not an edge";
  "add it and retrain on the same day you aren't betting".
* **How it was read:**
  * Build the package from today's downloads with today's builder (as the owner was told: "the package should be rebuilt
    from the downloads with today's builder, then checked"), men only, the scope the feed does not cover, results only.
  * Register it under the 14 Oct rule (gap fills that pass both conditions enter by themselves).
  * Rebuild the template on the day's tables with every accepted package and the feed, fit it, run the harm check against
    the current instance, and switch the daily runs to the new instance if there is no harm.
  * Set aside: deriving from the 10 Oct candidate (faster, but the owner was told it would be rebuilt); carrying the
    matches' box scores (see § 6, call 2).
* **The women's to-do list** is a separate deliverable ([docs/studies/womens_model/to_do.md](../womens_model/to_do.md)).
* **The target:** none. This is a data repair under the 14 Oct rule; the only model reading is the rebuild's harm check.

## 2. Starting point

* **Code:** commit `1d8f53e`, with many uncommitted changes by other sessions.
* **The current instance:** `template_2026-10-14` (`data/studies/master_pipeline/selected_instance.json`, tree
  `C:/Users/zerom/tnr_tpl1014`, selected 14 Oct 07:42). Built before the two TennisLive packages (registered 14 Oct 09:59
  and 12:32), the feed's snapshot 20261014 (advanced 14 Oct 19:56) and the Tenerife date correction (applied 14 Oct
  21:19).
* **`accepted.json`:** packages `tennislive_box_fill`, `tennislive_box_fill_men_gsq`; feed `lower_level_feed/20261014`;
  retired `men_2026_ch_chq`.
* **The machine at 13:40:** a SofaScore download (ITF detail, `--no-stage`: it writes raw files only); the UFC project's
  TabICL runs on the graphics card (77% busy, 11.4 of 32.6 GB). 232.7 GB free on C:.
* **The idea and how it arose:** a repair (holes in levels and seasons the history covers), entering by the route the
  level-evidence study's evidence supports (the men's level layer); framework § 0 kind: expansion/repair.

## 3. Plan (as first written, before any build)

1. Build the candidate `MLF20261016` with the level-evidence builder against the frozen reference: the sources of men's
   matches (`tennislive,itf_live,sofascore,tennislive_pages,tdi`; the two WTA sources left out), the feed's box sources
   and exclusions. Then its checks, the feed's identity rule screen, READY.
2. Derive the package scope `MLF20261016_pkg`: men only; Challenger and Challenger qualifying dated 2010-01-01 to
   2025-12-31, ITF dated 2010-01-01 to 2026-05-31 (the feed covers men's Challenger levels from 1 Jan 2026 and men's ITF
   from 1 Jun 2026); results only for all three levels. Checks, READY.
3. Check the 14 Oct rule's two conditions on it, and compare its matches with this morning's count (4,246).
4. Package `men_lower_level_fill` (`additions.py --package`), `--check-against`, `--register`.
5. Rebuild: `build_template.sh <new sandbox> data/studies/current_best_model/template_2026-10-16 1 accepted`,
   `post_build.sh`, fits seeds 0–3 for 2019–2026, then seeds 4–15 for 2026 (the switch needs them), then the other
   seasons' seeds 4–15. Launched detached.
6. The harm check, fixed here before any build or reading:
   * **Arms:** NEW = `template_2026-10-16` against ON = `template_2026-10-14` (the current instance).
   * **What it covers:** everything that entered since ON was built: this package, the two TennisLive packages, the feed's
     snapshot 20261014, the Tenerife date correction, and the matches Tennis My Life has published since. That is the 14
     Oct rule's "each rebuild's harm check covers what entered since".
   * **Scorer:** the 10 Oct harm check's own (`level_layer_adoption/harm.py`'s `reading_rows` on
     `system_pairs.load_models`; compare.py's recipe; seeds 0–3 paired; speed rule "zero"), as the feed's check used it.
   * **Primary:** both tours, both stages, test seasons 2020–2026, fits 2019–2026. Secondaries (not deciding): men,
     women, 2020–2024, 2025–2026, each season.
   * **Rule:** harm = worse by more than 0.10 mLL per match with the whole 95% interval below 0. No harm → switch the
     daily runs to NEW. Harm → no switch, and the owner decides.
7. Switch `selected_instance.json` to NEW; the README; CLAUDE.md's list of packages; a section in the 14 Oct decision.

## 3a. Plan addendum (13:58–14:05, before any reading of the package or the model)

* **The duplicate risk is read, not assumed away.** The merge skips a match already held under the same id, as the same
  meeting, or as the same pair and round within 3 days. `conditions_new.py` also lists every added match whose two
  players already meet in today's merged tables within 14 days at any round, level or tournament (`near_pairs.csv`).
  Rows there are looked at by hand before registering; true duplicates would be cut by a narrower derive.
* **The switch follows the 14 Oct procedure** (`data_gaps_2026/switch_final.sh`): `use_instance` (its template check),
  the replay's checkpoint (2026-06-22), the replay check with Tennis My Life's dump frozen as the build read it,
  `replay-compare`, the live checkpoint (2026-09-21). Two lessons of 14 Oct are built in:
  * the build and the switch run in one detached script, in order, so no two GPU jobs overlap (the 14 Oct deadlock
    between the build's last fits and the replay's fit);
  * the dump view is frozen at the start of the Stage 0 rebuild that wrote today's tables (2026-10-14T21:19:58Z,
    `data_continuity/rebuilds/2026-10-14T2119Z`): the template build copies those tables, and the replay rebuilds
    Stage 0 from the dump.
* **The switch is made by the script when the pre-declared rule finds no harm** (§ 3, step 6), so it does not depend on
  this session lasting the 4–5 hours. Guards:
  * no switch if `accepted.json` changed since the build (a replay would merge other packages);
  * no switch if `use_instance`'s template check refuses;
  * the previous selection is put back if the checkpoint, the replay or `replay-compare` fails.
* **`compare.py` against the frozen reference** runs after the harm check, as on 14 Oct, for its input check (the
  uneven-input flags CLAUDE.md says to read first). It is not a gate.

## 4. Chronology

Local time (UTC−7). "Results" means any outcome-based score of any model.

| When | Step (command or action) | Why | Results seen by then | Output |
|---|---|---|---|---|
| 13:20–13:40 | The counts behind the owner's request (earlier messages): the 9–10 Oct candidate's additions looked up in the live Stage 0, the packages and the feed by id and by players, tour, level and date (±10 days); reach by main-tour activity; the 14 Oct coverage condition per tour, level and season | The owner asked what is held out | none | Scratch scripts (`held_out.py`, `coverage_rule.py`, `the_8600.py`, session scratchpad) |
| 13:40–13:45 | Read the TennisLive package's route (process log § 10), the feed's scope and source rules, the builder's options, the rebuild and harm-check scripts of 13–14 Oct; checked running processes, the GPU and disk | Plan | none | This log, § 3 |
| 13:44:24 | **Candidate build launched, detached** (`build_candidate.sh` through Git Bash in its own console): `candidate_stage0.py --label MLF20261016 --sources tennislive,itf_live,sofascore,tennislive_pages,tdi --box-sources wta_api,itf_live,tdi,tennislive_pages --box-exclude tennislive_pages:ITF,tennislive_pages:ITFQ`, then `--checks` | Plan step 1 | none | `C:/Users/zerom/tnr_mlf/candidates/MLF20261016/`; logs in `data/studies/men_lower_level_fill/` |
| 13:45–13:55 | While it runs: `src/eda/men_lower_level_fill/harm.py` (the check fixed in § 3, step 6; a copy of the feed's 13 Oct check with ON = `template_2026-10-14`, test seasons 2020–2026, the two periods as secondaries); `conditions_new.py`; `build_template.sh` (the 13–14 Oct rebuild's steps, with the harm check right after the seeds 0–3 fits) | Steps 3, 5, 6 | none | The three files |
| 13:55 | **Found:** the official conditions script reads both conditions for box-score completions only. For new matches the coverage condition (C2) needs its own reading, so `conditions_new.py` reads it per tour, level and season on today's tables with every package and the feed merged. C1 (counts the same way) concerns box scores, and this package carries none | Step 3 | none | – |
| 13:56 | Checked the card wait (`training_window/fits.wait_for_card`): it waits for this project's local-env processes and 12 GB free. The UFC project's TabICL jobs run in another environment, so the fits will share the card with them rather than wait | Step 5 | none | – |
| 13:50–13:53 | **`conditions_new.py` rewritten before any reading,** after reading `additions.py`'s merge and the official conditions script: (a) the adds are what the merge would add, because the merge skips a match already held under the same id, as the same meeting, or as the same pair and round within 3 days (TML's backfills since 8 Oct, the feed); the first draft counted by id only. The candidate is written as a trial package in the reading's own folder and merged at the position `--register` gives it (after the other packages, before the feed); rows it would displace are counted. (b) Levels as the official script's buckets (`LC.bucket`), counts as played matches (completed or retired), as in its C2 | Step 3 | none | `src/eda/men_lower_level_fill/conditions_new.py` |
| 13:51 | Build log: all five sources linked (TennisLive 232,005 new before the scope cut; ITF live 190; SofaScore 78; TennisLive pages and TDI 0, box sources) | Step 1 | none | `build_MLF20261016.log`, `status.log` |
| 13:50 | Correction to the three rows above timed 13:45–13:55, 13:55 and 13:56: they were written from memory, and the shell's clock read 13:50:32 at the next check, so all three happened between about 13:45 and 13:50 | – | none | – |
| 13:53–13:57 | **Who reads `accepted.json`, and when** (before registering). A peer's daily-engine replay started 13:52 (`fastcourt_replay_2026-07-13_R16`, exact "training" dating, instance `template_2026-10-14`); its tables step ran `additions.py --apply` at 13:55, so it merges the packages as they stand now. **Found:** an exact replay holds the instance's timeline and stops if the work tree's Stage 0 holds a match that timeline lacks (`dp_tables.hold_timeline`). The work tree's Stage 0 is the frozen TML dump plus the packages *currently* accepted. Read-only check: of the feed snapshot 20261014's 49,001 added matches, **2,110 are missing from `tnr_tpl1014`'s timeline** (dated 2025-06-23 to 2026-10-12; that instance was built on snapshot 20261013c). So exact replays against `template_2026-10-14` have been exposed to this since the feed advanced (14 Oct 19:56), before this study; this package adds about 4,200 more such matches until the rebuilt instance is selected. Live bet-day runs build their own timeline and are not affected | Step 4 (registration timing) | none | – |
| 13:56–14:03 | Build written: 1,105,683 matches, 232,246 new against the frozen reference (every tour and level the sources give; the men's scope is cut by the derive). Count-only preview of the men's scope before the merge's skips: **4,376** (ITF 3,372, Challenger qualifying 953, Challenger 51; 359 carry a source box score, which the derive blanks; 4,205 completed, 170 retired, 1 other). This morning's 4,246 already left out matches held under other ids or within ±10 days by players, so the merge's skips should take the 4,376 close to it. The candidate's checks: **pass** (structure, history: "lower-level new past 201,450 … a template build is refused", as expected for the whole candidate before the cut) | Steps 1–2 | none | `checks_MLF20261016.log`, the candidate's `checks.json` |
| 13:58–14:05 | Plan addendum § 3a written (the near-pair listing; the switch inside the detached script, with its guards; `compare.py` for the input check). `conditions_new.py` refactored (`c2_cells`, `near_pairs`); tests `test/men_lower_level_fill/test_conditions_new.py`: 5 pass. `build_template.sh` extended to the switch; `package_steps.sh` written | § 3a | none | as named |
| 14:04:09 | `package_steps.sh` launched, detached: rule screen → READY → derive `MLF20261016_pkg` (`--keep-tours atp --keep-since atp:CH:2010-01-01:2025-12-31,atp:CHQ:2010-01-01:2025-12-31,atp:ITF:2010-01-01:2026-05-31 --results-only atp:CH,atp:CHQ,atp:ITF`) → its checks → READY → `conditions_new.py --out data/studies/men_lower_level_fill/package` | Steps 1–3 | none | `package_steps.out` |
| 14:04:13 | **Rule screen: pass** [observed, `screen_MLF20261016.log`]. Unsure shares (limits: links 0.25, players 0.35): links TennisLive 0.05, ITF live 0.05, SofaScore 0, TDI 0, TennisLive pages 0; players TennisLive 0, ITF live 0.025, SofaScore 0.20. Written as `identity_verdicts.csv` (by = rule). READY 14:04:16 | Step 1 | none | candidate folder |
| 14:05 (first written as 14:06; the shell read 14:05:49 just after) | **The identity repair's moves by hand** (the screen does not score them; the rule called 18 of the 20 sampled moves "unsure", since the names differ): all 20 are the same person by name, country and years (second surnames: Fermosell Delgado, Batalla Diez, Fumeaux Buenaventura, Camargo Lima, Plaza Araujo; middle names: Tai Leonard Sach, Attila Dominik Boros, Aditya Vishal Balsekar; spellings: Wei Qiang/Weiqiang Zheng, Rui-Xuan/Ruixuan Wang, Niccolo/Nicolo Inserra, Bekkhan/Bekhan Atlangeriev, Ammar/Anmar Alhogbani, Marianne/Marianna Argyrokastriti; two new TennisLive ids joined to South Africans of the same name). Two plausible, not certain: Junhyun/Junhyeon Lee (KOR; 3 matches 2019–2022 and 23 from 2023) and Mohammed/Mhamed Affes (TUN; one match each). The 20 include 2 women's moves, outside this package | Step 1 | none | `identity_sample_repair_moves.csv` |
| 14:05–14:09 | **Derive `MLF20261016_pkg`** [observed]: 4,376 new matches (ITF 3,372, Challenger qualifying 953, Challenger 51), 331 new player ids, every new id in a new namespace and of the match's tour; its checks pass (reference matches and facts identical; history "lower-level new past 4,376 … refused" before registration, as expected); READY 14:08:52 | Step 2 | none | `derive_MLF20261016_pkg.log`, `checks_MLF20261016_pkg.log` |
| 14:08:54–14:23:05 | **`conditions_new.py`** (two full merges and the near-pair scan, 14 minutes) [observed]: the merge onto today's tables, in `--register`'s position, adds **4,345** (Challenger 20, Challenger qualifying 953, ITF 3,372); 31 skipped as the same pair and round within 3 days (all Challenger: already in today's tables since 8 Oct); 0 displaced; 4,344 played. **C2: all 19 cells pass**, every one by the first branch (the cell already holds at least as many played matches as it gains; the closest: Challenger qualifying 2019, 271 held, 24 added; 2020, 394 and 17). C1 does not apply (no box score in the package). **Near pairs:** 167 added matches (169 rows) whose two players also meet in today's tables within 14 days | Step 3 | none | `package/c2_new_matches.{csv,json}`, `package/near_pairs.csv` |
| 14:23–14:25 | **The near pairs read** [observed]: every row is exactly 7 days (126) or 14 days (43) away, never the same week. 166 have different scores; 3 share one (6-3 6-3 Tabarka 2019; 6-4 6-4 Maanshan 2026; 6-4 6-3 at an ITF and a Challenger qualifying two weeks apart). In the two same-venue cases, the held tables have no match of either player in the added week, and every other round of both players differs between the two weeks (Tabarka: held week of 27 May R32 v 108705, R16, QF, SF; added week of 20 May R32, R16 v 144742. Maanshan: held week of 30 Mar R32–SF; added week of 6 Apr R32, R16, QF, SF, all other opponents different). So they are separate weekly events at venues that host back-to-back weeks, and the added week fills a hole. Three equal scores among 169 rematches is what chance gives for the commonest scores. **Explains the count:** this morning's 4,246 treated a same-pair meeting within ±10 days as already held, which removed these 7-day rematches; the merge keeps them, hence 4,345 | Step 3 | none | – |
| 14:19–14:22 (times of this row and the next reconstructed from the shell's readings 14:19:17 and 14:25:37) | **The peer replay's failure diagnosed** (read-only scratch `replay_dup.py`): `fastcourt_replay_2026-07-13_R16` stopped at its additions step, "the merge made duplicate match ids, sides or timeline rows". The frozen 8 Oct Stage 0 (what an exact replay's dump view rebuilds) against the repository's current timeline (what its work tree copies): 290 timeline ids are not in that Stage 0, and **43 of the feed snapshot's added ids are among them** (TML has since published those matches under the same ids). The merge adds them, and their timeline rows duplicate. Every exact replay with the default 8 Oct view fails there today, independent of this package. This study's replay uses a view frozen at 14 Oct 21:19:58Z, whose Stage 0 holds them | – | none | scratchpad `replay_dup.py` |
| 14:22–14:23 | Heads-up sent to the three busy tennis sessions (56, b0, 61): the replay diagnosis, the coming registration, the rebuild and its switch, the dump view the new instance's replays need | Step 4 | none | – |
| 14:24 | **Package written:** `additions.py --package C:/Users/zerom/tnr_mlf/candidates/MLF20261016_pkg --name men_lower_level_fill --decision docs/decisions/2026-10-14-lower-level-gap-fills.md`: 4,376 added matches, 0 completions. **`--check-against … --only men_lower_level_fill`: pass** (matches, players, timeline equal) [observed] | Step 4 | none | `package_write.log`, `check_against.log` |
| 14:20–14:25 | **The peers' replies** (cross-session messages, verbatim excerpts). 61: "No conflict: go ahead with the package and tonight's switch. This session (serve/return-leads study, diagnostic only) reads neither accepted.json nor selected_instance.json." 56: "No need to hold off: my run is past its additions and history steps … Heads-up: your replay check tonight runs through engine code I changed today. … For template_2026-10-16: run.json's base_tree must be tnr_tpl1016 (DP_BASE_TREE), and that tree must keep surface_ios/surface_features.parquet while it is the instance. … If your replay check fails in the patterns step, send me its patterns_inside.log." b0 (14:26): "No need to hold off: this session (the source-reconciliation study) reads neither accepted.json nor selected_instance.json, and ran no replay." Running processes at 14:25:37: downloaders and other sessions' read-only checks; no prediction run, build or feed job | Step 4 | none | – |
| 14:25:43 | **Registered:** `additions.py --register men_lower_level_fill` [observed]. `accepted.json` packages: tennislive_box_fill, tennislive_box_fill_men_gsq, men_lower_level_fill; feed lower_level_feed/20261014; retired men_2026_ch_chq. Bet-day runs merge it from their next additions step | Step 4 | none | `accepted.json` |
| 14:26–14:27 | `history.py` after registration [observed]: on the package's Stage 0, "accepted 4,376 (allowed: lower-level additions 4,376) … lower-level new past 0, dropped 0, revised 0 → the template may be built"; on the live tables, "the template may be built" | Step 4 | none | `package/history_after_register.out`, `package/history_live_after_register.out` |
| 14:28:30 | **Rebuild launched, detached** (`build_template.sh` through Git Bash in its own hidden console, PID 47060). The sandbox, the instance folder, the dump view and the work tree did not exist before; GPU 4% busy, 3.2 of 32.6 GB; 206 GB free. Dump view frozen 14:28:33 (104 staged files, 4 re-staged to their 14 Oct version); build started 14:28:35 | Step 5 | none | `build_template.out`, `freeze_dump.log` |
| 14:30 | Reply to 56: the replay sets `DP_BASE_TREE`/`DP_INSTANCE` explicitly; the tree keeps `surface_features.parquet`; on a failed replay the script restores the selection, and the patterns log goes to 56 if that step is where it stopped | – | none | – |
| 14:31–14:35 | The decision record's section for the third package written (`docs/decisions/2026-10-14-lower-level-gap-fills.md`: point 5's note, the section, "To undo") | Step 7 | none | the record |
| 14:36 | **The count gap checked** [observed, from `near_pairs.csv`]: the morning's rule (`the_8600.py`: same tour, same level, same pair within ±10 days counts as held) would drop 124 of today's 4,345 (ITF 122, Challenger qualifying 2), all 7-day rematches. Under it today's build gives 4,221: ITF 3,250 (morning 3,274), Challenger qualifying 951 (952), Challengers 20 (20). So the morning's figure overcounted by 25 relative to today's build, and undercounted the real fill by 124. The row at 14:23–14:25 said the rematches explain the whole gap; that holds only after this 25 | Step 3 | none | – |
| 14:32 | Correction to the two rows above timed 14:31–14:35 and 14:36: they were written ahead of the clock (the shell read 14:32:10 after both); both happened between 14:28:30 and 14:32. From here, times are taken from `date` | – | none | – |
| 14:32 | CLAUDE.md's list of packages and the decisions index's 14 Oct row updated (other sessions' uncommitted edits in both files kept). Rebuild: sandbox ready 14:30:31, lane 0 running | Step 7 | none | CLAUDE.md, `docs/decisions/README.md` |
| 14:32–14:34 (first written as 14:33–14:40; the shell read 14:34:37) | The owner's README written; the studies index rows for it and for the women's list. Reach [observed, the package's `dose.csv`]: 749 of the 35,319 men's frame matches of 2013–2026 have a player whose previous 365 days gain a match, 41 within 28 days; none of the women's. Correction to the row above: at 14:32 the sandbox's merge (`run_chain.py --additions`) was running, lane 0 after it (`build.out`) | Step 7 | none | `README.md`, `docs/studies/README.md` |
| 14:34–14:36 | **Smoke run of `harm.py`** with both arms `template_2026-10-14` (into the scratchpad; equal arms, so a difference of 0 by construction, nothing about the package): ran in 8 s; primary 31,722 matches, estimate 0.0 [0.0, 0.0], harm False. The scorer's period label for 2020–2026 is "2020-2026", as `harm.py`'s primary filter expects | Step 6 | none (equal arms) | scratchpad `harm_smoke/` |
| 14:36 | **A numeric guard added to the switch:** `replay-compare` always exits 0 (`dp.py`'s `_print`), so the script now reads its `replay_compare.json`: every replayed match in the frame, the IOS inputs' NaN pattern equal and within 1e-6 (the owner's tolerance), every input within 1e-4 (14 Oct's switch read 4.5e-6); otherwise the selection is put back. The edit falls after the line the running script was executing (the build, line 48), so bash reads the new text when it gets there; `bash -n` passes | § 3a | none | `build_template.sh` |
| 14:36:15 | The sandbox's merge [observed, `build.out`]: `men_lower_level_fill` added 4,345, 31 skipped as the same pair and round within 3 days (as the reading); the feed 48,958 added, 43 skipped as the same id; the TennisLive packages' completions 231 and 183. Stage 0 before the merge: sha256 ca8f5b63…, the repository's of 14 Oct 14:21 PDT | Step 5 | none | the sandbox's `data/studies/current_best_model/accepted_additions_applied.json` (`build.out` prints it cut at 3,000 characters) |
| 14:38 | The process-log template gets one rule (rule 3): take each row's time from the clock, not memory; this log's four time corrections, and the same in the data-gaps and TennisLive logs, are the reason. Rebuild at 14:38:32: lane 0's `timing_features` | – | none | `docs/studies/process_log_template.md` |
| 14:40 | Interim report to the owner (the package in, the checks, the retrain running with its automatic switch, the replay finding, the women's list; item 1 of the list needs the owner's word) | – | none | – |
| 14:49:07 | Rebuild: lanes 1 and 2 started [observed, `build.out`] | Step 5 | none | – |
| before 15:02 | **Peer 56, verbatim excerpt:** "within the next hour I'm changing the exact-replay path (the owner asked me to fix replays), and your switch() replay check will run it. … 1. Dump view: DP_FREEZE_DUMP still wins (you set it). Without it, a new registry, data/studies/daily_prediction/replay_views.json, names each instance's view … 16 Oct: tnr_dump_freeze_1016) … 2. Additions in hold mode: the replay merges the instance's own list instead of today's accepted.json. It reads <instance>/accepted_at_build.json first (your script writes it) … 3. Timeline in hold mode: hold_timeline also runs right after the stage0 step, before additions … 4. Replays write <run>/replay_tables.json … Separately, the owner asked me to fix the venue key for renamed events in feature_interactions/features/f09_venue.py (Shanghai 2026). It feeds only the patterns step's fast-courts member, not the 57 inputs. … When does your switch() start, roughly?" | – | none | – |
| 15:02 | Checked: `accepted.json` unchanged since the build's start (sha256 b65c7b41914b…, equal to `accepted_at_build.json`). **Reply to 56:** none of the changes is a problem; switch() expected around 18:00 PDT ± 1 h; their changes to be in by about 17:00; `accepted_at_build.json` is a verbatim copy of `accepted.json` (same list as `chain_additions.json`); the dump view's freeze time; the guard after `replay-compare`, so a broken replay path leaves the daily runs on `template_2026-10-14`. **Consequence for this study:** the switch's replay will run through 56's new replay path (the instance's own package list, an early timeline hold), not the path of 14 Oct | Step 6 | none | – |
| 15:07 | Rebuild: lane 2 exit 0 (`surface_ios_features` 1,037 s) [observed, `lane2.out`] | Step 5 | none | – |
| 15:21:42 | **Failure 1: the build stopped.** Lane 1 exit 1 in `stage4_features`, inside its leak probe (`run_probe` → `probe` → `build_all` → `elo_variants` → `weighted_elo_pass`): `OverflowError: (34, 'Result too large')` at `10.0 ** ((rb - ra) / 400.0)` [observed, `lane1.out`]. The watcher reported "build failed" | Step 5 | none | `template_2026-10-16/lane1.out` |
| 15:22–15:27 | **Diagnosis** [observed, by reading the code]: the probe redraws every later match's outcome columns as random integers in [0, the column's maximum], each column independently (`OUTCOMES` holds `tpw_n`, `tpw_d`, `games_won_n`, `games_won_d` among the rates). The weighted Elo's weight is the winner's games or points share over its scale (about 0.6), so a redrawn share of, say, 400 of 3 gives a weight of several hundred. With K up to about 400, one update moves a rating by about 10^5, and the next pre-match exponent passes 308. The previous three builds passed this step by luck of the draws (the probe's generator is seeded; today's tables put the draws on other rows), so a rerun would fail the same way. Not bad data: on real rows the shares stay in 0–1 (the probe's own base build on the real slice ran without error). The frame's Elo inputs reach at most 7.3 on the exponent's scale (`template_2026-10-14`'s `in_elo_overall`, `in_elo_games`) | – | none | – |
| 15:24–15:27 | **Fix:** in `src/eda/predictability_diagnostic/stage4_features.py`, the exponent of both win-probability lines of `weighted_elo_pass` is capped at ±`EXP_CAP` = 300 before `10.0 **`. For any real gap the operations and operands are the same, so the outputs are bit for bit the same; NaN still passes through. Options weighed: (a) redraw the probe's numerators at most their denominators (the principled test fix, but more code in the probe's loop, and it changes the probe's draws); (b) the cap (two lines, no change to the probe or to real inputs). Chose (b). The daily engine's copy (`dp_elo.weighted_pass`) is left as it is: live data never comes near the cap. **Test** `test_weighted_elo_survives_an_impossible_weight_and_keeps_the_values_before_it` (`test/predictability_diagnostic/test_stage4.py`): a weight of 1e6 on one match; the pass completes, every value up to that match is the uncapped pass's bit for bit, and the gap does pass the cap. The unpatched sandbox copy raises the build's error on the same history [observed]. The Stage 4 Elo tests: 3 pass. The patched file copied into the sandbox (it differed from the repository's only by this edit; sha256 9d55b5db… both) | – | none | as named |
| 15:27 | `build_template.sh` made resumable (not running then): `accepted_at_build.json` written only at the first start, the guard's hash read from it; `SKIP_BUILD=1` skips the build step. `resume_build.sh` written: lane 1 from `stage4_features` with the layer, lane 3, collect, then `build_template.sh` with `SKIP_BUILD=1` | Step 5 | none | the two scripts |
| ~15:27 | **Peer 56, verbatim excerpt:** "The replay-path code is final (in since 15:06); I won't touch it again before your switch. … Exact replay of 13 Jul R16 against template_2026-10-14 … The IOS inputs were exact, but the Elo trio differed by up to 1.9e-3 on 15 of 23 matches, failing your 1e-4 guard. The cause was the only Stage 0 difference: the 31 rows of the 2024 Tenerife 1 Challenger, dated 2024-02-26 by today's code (P6's correction, decided 14 Oct) against 2024-01-21 in the 14 Oct build. With those dates set back …: Elo bitwise, 42/57 inputs bitwise, max 4.47e-6 …, IOS exact. Your guard passes. The repository's Stage 0, which your 16 Oct build copies, already has 2024-02-26, so your replay tonight should not see that gap. Also in since ~15:10: f09_venue.RENAMED … It feeds only the patterns step's G3, not the 57 inputs." | – | none | – |
| 15:28:55 | **Resumed, detached** (`resume_build.sh`, PID 14296); `accepted.json` still b65c7b41914b… Watcher on `resume_build.out` for the harm verdict or a failure. Reply to 56 (the failure, the fix, the new timing: switch about 18:30–19:30 PDT) | Step 5 | none | `resume_build.out` |
| 15:30 | Tests [observed]: `test/predictability_diagnostic/test_stage4.py` and `test/men_lower_level_fill`: 24 pass, 1 fails. The failure is `test_every_evaluation_event_name_is_in_the_country_table`, a data test: the repository's Stage 0 holds an evaluation event name the country table (`stage4_event_country`) lacks. It reads the live tables, not the Elo pass, so it is unrelated to the fix; left for the owner (the country table needs the new name) | – | none | – |
| 15:35–15:50 | Owner asked whether the rebuild can be paused (verbatim: "Is this the full model rebuild? can we pause it? or would that lose all the work we have?"). Answered: yes, the full rebuild; stopping loses only the step in progress (finished steps are kept and resume with `--from`; a fit on disk is never redone); nothing in use changes; predictions can run now, but not during the fits and switch (about 17:30–19:30). Recommended letting it run; asked whether to stop. No answer by 17:19 | – | none | – |
| 15:50 | Lane 1's `stage4_features` (resumed) exit 0 in 969 s; **its leak probe passed**: cut 4 "protected changed 0, later changed 38140, control caught at 32, largest protected difference 7.99e-15" [observed, sandbox `logs/stage4_features.log`] | Step 5 | none | – |
| 16:59–17:15 | Lane 1 done (23:58:59Z), lane 3 and collect (23:59:11Z), post-build, fits seeds 0–3 2019–2026 (16 min) [observed, `resume_build.out`] | Step 5 | none | – |
| 17:15:29–17:15:42 | **The harm check** [observed, `harm/new_vs_on.json`]. **Primary** (both tours, both stages, 2020–2026, 31,722 matches; + = NEW better): **+0.0068 mLL [−0.0255, +0.0390], unresolved, P(better) 0.66. No harm by the rule** (§ 3, step 6) → the script continued to the 2026 fits and the switch. Secondaries (not deciding; slices of one comparison are one reading): men +0.034 [−0.016, +0.084] P 0.91; women −0.023 [−0.065, +0.020] P 0.14; 2020–2024 −0.005 [−0.043, +0.032]; 2025–2026 +0.035 [−0.033, +0.103] P 0.86; by season all unresolved except **women 2024 −0.125 [−0.227, −0.022], "worse"** (one of 21 season slices; about one in twenty lands outside its 95% range by chance) | Step 6 | **the harm check's results (first model reading of this study)** | `harm/new_vs_on.{csv,json}` |
| 17:15:32–17:15:42 | `compare.py` against the frozen reference (not a gate) [observed]: both tours +0.009 [−0.343, +0.362], unresolved; men −0.138 [−0.600, +0.323]; women +0.171 [−0.428, +0.771] (across the odds change it resolves only about ±0.35). **The input check:** 20 inputs flagged uneven against 19 for `template_2026-10-14`; the 19 are the same (attributed on 14 Oct to decided changes). **New: `elo_surf_offset`, men's 2023** (scale ratio 0.894 against the 0.9 line; 2022 0.908, 2024 0.902) | Step 6 | the harm check above | `template_2026-10-16/vs_reference_2026-10-08/` |
| 17:16–17:19 | **The new flag attributed** [observed]: NEW against ON directly, men's `elo_overall` and `elo_games` barely move (correlation 0.998–0.999, scale within ±1% every season); `elo_surf_offset` moves in every men's season, 2013 included (correlation about 0.98; scale 1.01 in 2013–14 falling to about 0.93 from 2020). Cause: the offset's K is tuned by a grid search on 2013–2018 on each build's own history (`surface_elo_pieces/pieces.py`'s `tune_offset`), and **the men's choice flipped**: 14 Oct kd0 80, kd_off 10, shape 0.6 → today kd0 160, kd_off 10, shape 0.8 (`pieces_meta.json`'s `offset_constants`; women unchanged). The new K moves a little more for newcomers and a little less for long histories, so the offsets' spread narrows as players' histories grow, in every season. The package adds about 950 men's 2018 matches to the tuning history, the likely trigger (TML's revisions since 14 Oct may also contribute; not separated). The decided recipe re-tunes this on every build; not a data fault, not the finding-#6 pattern (a level appearing in some seasons) | Step 6 | the harm check above | – |
| 17:19–17:21 | Report to the owner: the harm check, the secondary readings, the new flag and its cause; the switch about to start, and stopping still cheap if they wanted to predict first. No answer before the switch began | – | the harm check above | – |
| 17:25:54–17:57:42 | **The switch, by the script** [observed, `resume_build.out`, `switch.log`]: fits seeds 4–15 for 2026 done (READY FOR THE SWITCH, 17:25:54); `use_instance` (template check OK) and checkpoint 2026-06-22 (609 s); the replay `replay_2026-07-13_R16_20261016T173604` through peer 56's new replay path (the instance's own package list, the dump view `tnr_dump_freeze_1016`, the early hold). At 17:57:42: **"the replay's inputs differ from the instance's frame" → SWITCH REVERTED** (the previous `selected_instance.json` restored); the script went on to the fits seeds 4–15 for 2019–2025 | Step 7 | the harm check above | `switch.log` |
| 17:58 | **Failure 2, mine: the guard misread its own path.** `switch.log` ends in `FileNotFoundError: … '/c/Users/zerom/Documents/Tennis-predictions/data/studies/daily_prediction/runs/replay_2026-07-13_R16_20261016T173604/replay_compare.json'`. The script's `REPO` is a Git Bash path (`/c/Users/…`); Git Bash converts such paths in a native program's arguments (so `dp.py` got `C:/Users/…` and wrote the run in the right place), but not inside the `python -c` code string, where Windows Python cannot open it. The replay's own comparison, read with a Windows path [observed]: 23 matches, none missing from the frame, 42 of 57 inputs bit for bit, the IOS inputs exact (0.0, NaN pattern equal), largest difference 4.38e-6 (14 Oct's switch: 4.47e-6) → **the guard passes**. So the revert was the script's bug, not the check. A folder `C:\c\Users\…` exists but dates from 13 Jun 2026 and holds another project's files: not written by this run | Step 7 | as above | `replay_compare.json` |
| 17:58:56 | **The switch completed by hand, as the pre-declared plan says** (no harm by the rule, and the replay passes the numeric guard written at 14:36, before any model reading). No prediction run active (only the build's fits, PID 31852); `accepted.json` still b65c7b41914b…; previous selection saved as `selected_instance_before_manual_switch.json`. `use_instance('template_2026-10-16', tree='C:/Users/zerom/tnr_tpl1016')`: **the template check OK on all five** (57 inputs; Pinnacle-first odds on this frame; the layer built, config 61bc8a824fc1; seeds 0–15 for 2026; the tree holds the layer config). **The daily runs use `template_2026-10-16` from 17:58:56** | Step 7 | as above | `selected_instance.json` |
| 17:59:10 | The live checkpoint 2026-09-21 launched detached (`live_checkpoint.sh`, PID 30972). The script's path bug is fixed after the script ends: editing a running bash script before its current line would shift what it reads next | Step 7 | as above | `live_checkpoint.out` |
| 17:59–18:00 | Message to peer 56: the switch done, the replay through their path passed, the build's last fits on the card until about 19:15. The README's "Tonight's rebuild" and status line; the decision record's rebuild bullet (no harm; the flag; in training from 17:58) | Step 7 | as above | README, the record |
| 18:00 | **The pooled record** (`class_record.csv`, kind repair): `rebuild_2026_10_16` (the primary, 2020–2026, holdout seasons, not pooled) and `rebuild_2026_10_16_2020_2024` (−0.005 [−0.043, +0.032], pooled; the pool reads seasons ≤ 2024 only). Repairs pooled over 6: fixed +0.001 [−0.016, +0.018], tau 0.000 [observed, `class_record.out`] | – | as above | `data/studies/adoption_framework/class_record.{csv,out}` |
| 18:02 | Report to the owner: the switch at 17:58 (the script's revert, the check that had passed, the switch by hand); the live checkpoint under way; no prediction run before the build's last fits end (about 19:15), or the fits stopped on request | – | as above | – |
| 18:10:19 | **Live checkpoint 2026-09-21 done** (668 s, exit 0) [observed, `live_checkpoint.out`]. `state/template_2026-10-16/` holds 2026-06-22 and 2026-09-21: the switch is complete | Step 7 | as above | – |
| 18:11 | Women's list item 6 gains the women's 2024 reading; §§ 6, 8, 9 updated for the switch | – | as above | `docs/studies/womens_model/to_do.md` |
| 18:36:54 | **The rebuild script ended: DONE** [observed, `resume_build.out`]: fits seeds 4–15 for 2019–2025 done (about 26–41 s a fit); 128 fits on disk (seeds 0–3 for 2019–2026, seeds 4–15 for every season); no rebuild process left (18:37:18); the card free | Step 5 | as above | `template_2026-10-16/fits/` |
| 18:37–18:39 | **The path bug fixed** (the script no longer running): the replay's run path is built with `cygpath -m` (C:/…), so the guard's `python -c` can open it. Checked [observed]: `bash -n` passes, and the fixed guard on tonight's replay opens its `replay_compare.json` and passes (exit 0). The lesson added to the session memory on detached jobs (paths inside `python -c`; never edit a running bash script above its current line) | – | as above | `build_template.sh` |

## 6. Judgment calls and deviations

1. **A fresh build, not a derive from the 10 Oct candidate.** The owner was told the package would be rebuilt from the
   downloads with today's builder. For men the builder's identity rules have not changed since 10 Oct (the known
   partial-name fault is still open), so the two routes should agree; § 4 records the comparison.
2. **Results only.** The package carries no box score:
   * men's ITF box scores before 2025 are a coverage change (tested first under the 14 Oct rule), and the men's layer
     gives every ITF box score weight 0 anyway;
   * the few Challenger box scores that came with these matches (11 in this morning's count) would add a source-quality
     question to a results package. TennisLive's Challenger box scores enter by the 14 Oct route as completion packages.
3. **C2 read for added matches by a new script, on what the merge would add** (13:50–13:53, before any reading). The
   official script reads completions only. The first draft counted adds by id; the merge's skips (same meeting, same
   pair and round within 3 days) would have been miscounted. Other branch: counting by id would have read 4,376 adds,
   with the same verdict (every cell's margin is wide).
4. **The near pairs were looked at, and all were kept** (14:23–14:25, after seeing the list, which holds no outcome of
   the model). Options: keep all; drop the 3 same-score pairs; narrow the derive. Kept, because every pair is a week or
   two apart, and the two same-venue, same-score cases are separate events by their draws. Other branch: dropping 3
   matches out of 4,345 would change nothing measurable.
5. **The identity repair's moves read by hand** beyond the feed's rule screen, which does not score them (14:05). All
   20 kept; the two uncertain ones (one match each, plus the Lee pair's 3 and 23) are left as the builder made them.
6. **The switch made by the script on the pre-declared rule** (§ 3a, before any build). The 14 Oct rule lets a package
   enter by itself and its rebuild's harm check decide. Waiting for this session would risk a rebuild finished but
   never switched. Other branch: a manual switch tomorrow, the daily runs keeping `template_2026-10-14` meanwhile.
7. **The dump view frozen at the Stage 0 rebuild's start** (2026-10-14T21:19:58Z), not at the build's start
   (§ 3a). The template build copies the repository's Stage 0, which that rebuild wrote; the view must give the same
   Stage 0. Other branch, a view frozen now: 4 Tennis My Life files have changed since, so the replay's Stage 0 would
   differ from the instance's and the replay check would fail.
8. **The lower date bound of the derive, 2010-01-01**, is not binding: no added men's match is dated before 2017.
9. **The leak probe's overflow fixed by a cap in the Elo pass, not by changing the probe** (15:24–15:27, before any
   model result). Options in § 4 (15:24–15:27). The cap leaves real inputs bit for bit as they were and the probe's
   draws as they were. The other branch (redrawing numerators at most their denominators) is the more correct test;
   it is left as a suggestion. The resumed build mixes steps run before the edit (lane 1's `stage1_baselines` and
   `stage3_ratings`, lane 0, lane 2) with steps after it; none of the earlier steps calls `weighted_elo_pass`, so the
   instance is what a fresh build with the patched file would give.
   * *Correction (15:30 by the clock): lane 0's `timing_features` (`match_timing/rebuild.py`) does call it, through
     `feature_alpha_audit/repair_features.games_elo`, on real rows only. The conclusion stands for another reason: on
     real rows the cap cannot bind. Weights stay below about 1.7, and Elo's expected score makes each update shrink as
     a gap grows, so real gaps stay in the low thousands of points, against the cap's 120,000. The old and new code
     give the same bits there.*
10. **The switch completed by hand after the script reverted it** (17:58, after the harm check and the replay had
    been read). The pre-declared plan (§ 3, step 6; § 3a) switches on no harm when the replay passes the guard. The
    revert came from the guard failing to open its file (a Git Bash path inside `python -c`), not from the replay;
    applied with a Windows path, the same guard passes. Options: complete the switch (the plan's outcome); leave the
    old instance and ask the owner. Completed, because the reading that decides was fixed before any result and is
    unchanged; the owner was told at once. Other branch: the daily runs stay on `template_2026-10-14`, trained
    without the batch since 14 Oct, until the owner answers.

## 7. Claims and their evidence

| Claim (README) | Evidence | Status |
|---|---|---|
| 4,376 in the package; 4,345 land (ITF 3,372, CHQ 953, CH 20); 31 already held | `package/c2_new_matches.json` (`merge_onto_today`, `added_by_tour_level`); `package_write.log` | observed |
| All 19 cells pass C2 by the first branch; the narrowest CHQ 2019 271/24 | `package/c2_new_matches.csv` | observed |
| 167 near pairs, all 7 or 14 days apart, 166 with another score; the 3 same-score cases separate events | `package/near_pairs.csv`; the draws read at 14:23–14:25 (§ 4) | observed (the draws by eye) |
| The morning's 4,246 vs 4,345: 124 rematches dropped by the morning's rule, and 25 the other way | `near_pairs.csv` with the morning's rule (§ 4, 14:36) | observed |
| The identity screen passed; 20 repair moves are the same person, 2 uncertain | `screen_MLF20261016.log`; the candidate's `identity_sample_repair_moves.csv` | observed (the moves by eye) |
| The package reproduces the checked build | `check_against.log` | observed |
| Reach: 749 of 35,319 men's frame matches (365 days), 41 (28 days) | the package candidate's `dose.csv` | observed |
| "Expect no measurable change in betting results" | the reach above and the layer's weights | inference |
| Exact replays with the 8 Oct dump view fail: 43 feed ids published by TML since | scratch `replay_dup.py`; the peer run's `tables.json` and its `additions.log` | observed |
| 2,110 of the feed's current matches are missing from `tnr_tpl1014`'s timeline | the read-only check at 13:53–13:57 (§ 4) | observed |
| The rebuild stopped in the builder's leak probe; the fix leaves real inputs bit for bit as they were; a test reproduces the old failure | `template_2026-10-16/lane1.out`; the diff of `stage4_features.py`; `test_stage4.py`'s new test; the old copy raising on it (§ 4, 15:24–15:27) | observed; "bit for bit on real inputs" is inference from the operations being unchanged within the cap and real gaps far below it |
| No harm: +0.007 [−0.025, +0.039], P(better) 0.66; the secondaries | `harm/new_vs_on.{csv,json}` | observed |
| The new input flag comes from the re-tuned surface-offset K | `pieces_meta.json`'s `offset_constants` in `tnr_tpl1014` and `tnr_tpl1016`; the direct comparison of the two frames (§ 4, 17:16–17:19) | observed (the K change); inference (that the 2018 additions triggered it) |
| The replay check passed; the script's revert was its own path bug; the switch completed at 17:58:56 | `replay_compare.json` of `replay_2026-07-13_R16_20261016T173604`; `switch.log`'s `FileNotFoundError`; `use_instance`'s template check; `selected_instance.json` | observed |

No number above rests on a choice made after seeing a model result: no model result had been read when the package
entered.

## 8. Weak points

* **Threats to validity, most important first:**
  * **Identity.** The package brings 331 new player ids. The whole candidate's identity repair moved 3,055 new-match
    player rows onto known players, and the package carries part of them. The rule screen and 20 moves by hand see a
    sample only. A wrong merge puts one player's lower-level results on another's record.
    At ITF weight a quarter, one wrong merge moves a rating little; many would show as a level shift in the rating
    inputs, which `compare.py`'s input check reads.
  * **Duplicates beyond 14 days, or under different players' ids.** The near-pair listing pairs by ids or by both
    players' name keys. A match held under a misspelled name *and* another id at a date more than 14 days away would
    slip through. The builder's own checks (same pair within 3 days in two tournaments: 0; player twice in one round: 0)
    cover the commonest forms.
  * **The harm check's power.** The package moves 749 of 35,319 men's frame matches' histories, far below what the
    check resolves. The check is a harm screen for everything since 14 Oct together, not a reading of this package.
  * **The engine changed today** (peer 56: the states and patterns steps). The switch's replay runs through that
    code. A failure there would revert the switch for a reason unrelated to this package. *(Afterwards: the replay
    passed through it; the revert came from this study's own script.)*
  * **Women's 2024 reads worse** (−0.125 [−0.227, −0.022]), the only one of 21 season slices clear of zero. The batch
    touched women's data mainly through the TennisLive completions (2015–2024) and the feed (2025–2026); nothing was
    traced to 2024 specifically. By the rule it does not decide; it is noted for the women's list.
  * **The switch was completed by hand** after the script's guard failed to open its own file (§ 6, item 10). The
    replay's reading was applied with the same thresholds; a reviewer should re-read `replay_compare.json`.
* **Where a flaw would most likely hide:** in the identity repair's moves and in matches
  dated by TennisLive's event week rather than the match day (the 2019 Tabarka week of 20 May against the history's
  27 May shows the venues' weekly rhythm; a misdated week would look like a rematch).
* **What a re-design would do:** hand-check 50 of the package's matches against a second source (the ITF's own draws);
  pair near matches by draw position as well as by players; run the package alone as a `--candidate` build against
  the template without it, to read its own effect (below resolution, as expected).

## 9. Reviewer checklist

* [ ] Re-derive the landing count: `./python.sh src/eda/men_lower_level_fill/conditions_new.py --candidate C:/Users/zerom/tnr_mlf/candidates/MLF20261016_pkg --out <scratch>` (14 minutes) gives 4,345 and 19 passing cells.
* [ ] `./python.sh src/eda/current_best_model/additions.py --check-against C:/Users/zerom/tnr_mlf/candidates/MLF20261016_pkg --only men_lower_level_fill` passes.
* [ ] `./python.sh src/eda/current_best_model/history.py` on the live tables reads "the template may be built".
* [ ] Open `package/near_pairs.csv`: every `added_tournament_date` 7 or 14 days from `held_tournament_date`.
* [ ] Tests: `./python.sh -m pytest test/men_lower_level_fill -q` (5 pass).
* [ ] The harm check's verdict words against its interval (`harm/new_vs_on.json`).
* [ ] The switch: `data/studies/master_pipeline/selected_instance.json` names `template_2026-10-16` with tree
      `C:/Users/zerom/tnr_tpl1016` (selected 17:58:56); `data/studies/daily_prediction/state/template_2026-10-16/`
      holds 2026-06-22 and 2026-09-21; the replay's `replay_compare.json` passes the guard (§ 4, 17:58).
* [ ] The input flag's cause: `offset_constants` in the two build trees' `data/studies/surface_elo_pieces/pieces_meta.json`.
* [ ] The builder fix: `./python.sh -m pytest test/predictability_diagnostic/test_stage4.py -q -k elo` (3 pass).

## 10. Reproduction

```
# from the repository root, Git Bash; the tennis environment through ./python.sh
bash data/studies/men_lower_level_fill/build_candidate.sh     # candidate MLF20261016 and its checks (~20 min)
bash data/studies/men_lower_level_fill/package_steps.sh       # rule screen, READY, derive MLF20261016_pkg, checks,
                                                              # READY, conditions_new.py (~20 min)
./python.sh src/eda/current_best_model/additions.py --package C:/Users/zerom/tnr_mlf/candidates/MLF20261016_pkg \
  --name men_lower_level_fill --decision docs/decisions/2026-10-14-lower-level-gap-fills.md
./python.sh src/eda/current_best_model/additions.py --check-against C:/Users/zerom/tnr_mlf/candidates/MLF20261016_pkg \
  --only men_lower_level_fill
./python.sh src/eda/current_best_model/additions.py --register men_lower_level_fill
bash data/studies/men_lower_level_fill/build_template.sh      # GPU: the dump view, the build, fits seeds 0-3
                                                              # 2019-2026, harm check, compare.py, fits seeds 4-15
                                                              # 2026, the switch, fits seeds 4-15 2019-2025 (~4-6 h)
# as run on 16 Oct: the build stopped in lane 1 (stage4_features' leak probe, 15:21 PDT); after the EXP_CAP fix,
# copied into the sandbox:
bash data/studies/men_lower_level_fill/resume_build.sh        # lane 1 from stage4_features, lane 3, collect, then
                                                              # build_template.sh with SKIP_BUILD=1
```

The downloads move: a rebuild of the candidate on a later day reads newer files and gives slightly different counts.
The record of this one is the candidates' `manifest.json` (every input's sha256) and the package's `manifest.json`.

## 11. Follow-up of 22 Oct 2026: the country list

Same session (`c0f7c8d9-cc78-498f-9409-72258b59a7dd`), resumed on 22 Oct 2026. The session's clock was read at 11:24:32
and 13:05:31 only; the rows between carry no finer times.

* **The owner's words, verbatim.** Quoting this study's report of 16 Oct: "Should we fix or deal with these?" Then,
  after the recommendation (fix the country list; leave the surface offset; update the 6 Oct record): **"Fix the
  country list"**.
* **How it was read:** add the missing event names to the Stage 4 country table, and nothing else. The weekly check
  for new names and the 6 Oct record's update were proposed in the same message and not asked for, so they were not
  done.

| When | Step | Results seen by then | Output |
|---|---|---|---|
| 11:24 | The failing test's missing keys listed [observed]: 22 ATP event names of 28 Sep – 19 Oct 2026 (21 Challengers under their 2026 names; "Shanghai", which Tennis My Life renamed from "Shanghai Masters"). None of the 57 inputs reads the table (`template_2026-10-21b`'s `model_inputs.json`). The timing code reads it for time zones: Shanghai 2026's 95 timeline rows have 3-day windows, against 2 days for Shanghai 2025; the Challengers' windows are exact (1 day) from sources with their own time zones | – | – |
| 11:24–13:05 | Each missing event's tournament id looked up in the ATP's tournament list (`data/raw/public_dump/mantennisdata/atp/tournaments.csv`: location, country code) [observed]. All 21 Challengers placed. One correction to the name-based guess: "Ferrero Challenger" is in **Villena, Spain** (2026-7909, "Ferrero & Forty Challenger"), not Italy. "Copa Internacional de Tenis" is the name of the 2025–26 Curitiba (2895), Campinas (6307) and Piracicaba (2835) Challengers, all Brazil. Shanghai's id is a constructed one (`2026-5014-20261007`); code 5014 is the Shanghai Masters in 2024 and 2025 | – | – |
| 11:24–13:05 | Heads-up sent to peer 0a (it had asked about file overlaps; the table is not on its list). **22 rows added** to `data/studies/predictability_diagnostic/stage4_event_country.csv` in its sorted order; the countries are the ATP list's IOC codes; each row's basis names it. **Failure 3, mine:** Python's `write_text` wrote Windows line endings, so every line differed; restored to the file's own (LF). The diff is then exactly 22 lines added and none removed [observed]. The file before is kept in the session scratchpad (`stage4_event_country.before_2026-10-22.csv`) | – | the table |
| 11:24–13:05 | The same slip found in two files rewritten by Python on 16 Oct: this log (all lines CRLF) and `class_record.csv` (its two rows of 16 Oct CRLF among LF lines). Both normalised to LF; content checked unchanged. Git on this machine converts line endings at commit, so nothing would have reached a commit wrongly | – | the two files |
| 11:24–13:05 | **The check** (`stage4_country.check()`, written to the scratchpad, not over the 1 Oct check and summary that the Stage 4 report quotes) [observed]: the 22 keys are in the table with their countries. **Shanghai 2026: tennis-data's Location gives Shanghai, China for all 94 linked matches: agrees.** The Challengers have no second source (tennis-data does not cover them); their countries rest on the ATP list. The only events without a country are Kingston 2026, blank by design (the name cannot place it; a test expects it). No new disagreement with the WTA's calendar | – | scratchpad `country_check_2026-10-22.csv`, `country_summary_2026-10-22.json` |
| 11:24–13:05 | `test/predictability_diagnostic/test_stage4.py`: **20 pass**, the country-table test included [observed] | – | – |
| 13:05 | **When it takes effect:** live runs build their own timeline from the repository's table, so at once (for Shanghai it no longer matters: its results are over a week old). The shared timeline that template builds copy was last written 21 Oct 06:51; the fix enters it at the next shared-table rebuild (the notebook's `rebuild_shared_tables`), and training at the retrain after that. New event names will keep appearing weekly, so the test will fail again until each is added | – | – |

## 12. Follow-up of 22 Oct 2026: the weekly check

* **The owner's words, verbatim**, quoting the report of section 11 ("The weekly check wasn't part of what you asked,
  so I didn't add it. New event names appear every week, so this test will fail again until each new one is added. I
  can add that weekly check whenever you want."): **"add the weekly check"**.
* **How it was read.** The offer of the morning was "a small step to the weekly data update that lists any new event
  without a country, so it gets added the same week". Acted on as: each week, a name the official lists place in one
  country is added by the check itself, with its basis. A name they cannot place, or place in two countries, is
  listed and raises the weekly task's notification. Set aside: listing only, which would need a person every week for
  names an official list already places. The report to the owner states this choice.
* **Where it runs:** the weekly task (`src/ingest/scheduled.py --weekly`, the "lower-level feed" Windows task), on
  Wednesdays after the coverage job. That job builds a Stage 0 from today's files, so new names reach the table before
  the next shared-table rebuild. The check also reads the repository's Stage 0, the failing test's view.

| When | Step | Output |
|---|---|---|
| 13:05–13:17 | Read the notebook's weekly update and the weekly task's jobs (`job_tml_dates`, `job_coverage` as templates; `weekly_due`; the dispatch, whose final `else` runs the Slam reminder for any unknown job name). `scheduled.py` last edited 21 Oct 20:49 (not in use by another session); not on peer 0a's list. Checked: the ATP's tournament list uses the table's IOC-style codes, except New Caledonia "CAL" and Guadeloupe "GLP", which the table reads as France (Le Gosier, Nouméa, Réunion rows) | – |
| 13:17–13:20 | **`src/eda/predictability_diagnostic/stage4_country_weekly.py`** written: the evaluation names missing from the table; readings from the ATP's tournament list (by the id's first two parts; territories as France), the WTA's calendar (as `stage4_country.check()` links it) and tennis-data's Location (Stage 1's link); one country → added with its basis and date (`--apply`), else left for a person; the table rewritten through a temporary file with LF endings, existing rows untouched, the table re-read just before writing; `summary.json`, `proposals.csv`, `added.csv` (history) in `data/studies/predictability_diagnostic/country_weekly/`. Exit 0, 3 (names left for a person), 1 | the script |
| 13:20 | **Byte check on a copy of the real table** [observed]: one added row (with a comma and quotes) gives a one-line diff in its sorted place; a duplicate key is skipped; no row asked gives no write | scratchpad |
| 13:20 | Tests `test/predictability_diagnostic/test_country_weekly.py`: the id parsing and the territories; one country added, two or none left for a person; the rewrite keeps every existing row and the order. 3 pass | the tests |
| 13:20 | **Failure 4, mine:** with no missing name, a filter on the empty table selected no columns (`d[[]]`): the run stopped. Fixed with explicit row masks; rerun: 856 evaluation names, 0 missing, exit 0 | the script |
| 13:21 | **The replay of this morning** [observed]: the check run in report mode on the table as it was before the hand fix (the scratchpad copy). It proposes all 22 names for adding, each with the country set by hand, Villena (Spain) included; Shanghai placed by the ATP list and tennis-data together. None left for a person | scratchpad `country_weekly_replay/` |
| 13:21–13:22 | **`src/ingest/scheduled.py`:** the job `event_country` (Wednesdays, after coverage; `--stage0` the coverage Stage 0 when it was built today; alerts only for names left for a person, at once and every 4 weeks; a failure alerts the second time in a row), its constants, its explicit dispatch branch, the docstring and the help texts. `test/data_continuity/test_rebuild_and_schedule.py`: two expectations of Wednesday's job list updated (one would have failed only on Wednesdays), and a test of the job (applies; today's coverage Stage 0 only; added names recorded, not alerted; alert, quiet week, reminder, forgotten once added; failures). **27 pass** | the runner, the tests |
| 13:22 | **End to end** [observed]: `./python.sh -m src.ingest.scheduled --weekly --only event_country --no-notify`: exit 0 in 1.3 s, no alert, 0 names missing, recorded in `data/raw/_scheduled/runs.jsonl`. `stage4_country.py`'s description points to the weekly job | – |
| 13:22 | **Two unrelated test failures seen** in `test/predictability_diagnostic` (not run in section 11): `test_built_baselines_table` (Stage 1) and `test_built_ratings_table` (Stage 3). Each built table has 872,704 rows against the repository's Stage 0 of 873,964: they were built before Stage 0's last rebuild. Not touched here; reported to the owner | – |

---

## Note, 22 Oct 2026: the 14 Oct instance's build tree deleted

Added by the cleanup session `4437577b-803e-4161-baf5-c6fade971478`, at the owner's word
([cleanup inventory, process log § 9d](../cleanup_inventory/process_log.md)).
* **Deleted on 22 Oct 2026:** `C:/Users/zerom/tnr_tpl1014`, the build tree of `template_2026-10-14`. That is the
  instance this study started from (selected 14 Oct 07:42), which its rebuild `template_2026-10-16` replaced at 17:58
  on 16 Oct. This study's own trees, `tnr_tpl1016` and `tnr_mlf`, stay.
* **What no longer repeats as written:**
  * The count of the feed's matches missing from `tnr_tpl1014`'s timeline (2,110; § 4 and the claims table) read that
    tree's own timeline, and no other copy holds it.
  * The `offset_constants` comparison can still be redone, from the instances' own copies:
    `current_best_model/template_2026-10-14/chain_outputs/surface_elo_pieces_pieces_meta.json` and the 16 Oct
    instance's.
* **For a reviewer:** the results stand as recorded. This study's "before" side is the 14 Oct instance, an older
  version of the model; the live one is `template_2026-10-21b`.
