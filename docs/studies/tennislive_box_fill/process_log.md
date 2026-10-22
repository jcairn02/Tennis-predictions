# TennisLive box-score fill and the lower-level data policy: process log

14 Oct 2026 – 14 Oct 2026 · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code extension) · Sessions: `41028241-54bf-46db-9857-d2b89fee4f7e` (peer name `tennis-predictions-56`) · For a future reviewer · Report: [README.md](README.md)

## 1. The request

* **The owner's words, verbatim** (14 Oct 2026, first message). The owner pasted an earlier session's answer about TennisLive (its section "2. TennisLive, the clock, Stage 0 and the unmapped folders"), quoted its box-score paragraph, and asked:
  > "In particular. I was pretty sure I lifted the data freeze? yet it keeps coming up?
  > Filling in those ~420 box scores seems strictly better than not?"
* **This session's answer (chat, 14 Oct, before any work here).** Read-only lookups: the decision records (8 Oct freeze and its 9 Oct narrowing, 10 Oct layer and package, 13 Oct Tennis My Life and feed decisions), the master-pipeline log rows of 11 Oct (11:55, 12:05), the P5 report ([gap_downloads README](../gap_downloads/README.md) § "TennisLive pages for the gaps"), the feed's consistency note ([data_gaps_2026 log](../data_gaps_2026/process_log.md), 16:35–16:40), the builder's TennisLive loader, and two counts on P5's per-target tables (`data/studies/gap_downloads/tennislive_*_points_*_matches.csv.gz`, observed):
  * 486 matches whose official row (Tennis My Life 307, Sackmann 179) has no box score while TennisLive has statistics: men CH 306, CHQ 22, TQ 6, GSQ 1; women GSQ 147 (Roland Garros 2018 72, Wimbledon 2018 75), TQ 4; by year 2018 173, 2019 48, 2020 14, 2021 199, 2022 35, 2023 6, 2024 11, none later; 31 retirements.
  * TennisLive's statistics against the official box score, all fields equal, by tour and level: men CH 99.90% (22,088), CHQ 99.96% (7,115), TQ 99.14% (2,431), GSQ 94.87% (1,014); women TQ 99.79% (1,902), GSQ 98.67% (829; 2018: 171 of 171). Men's GSQ differences sit in AO 2018 qualifying (22, off by one in many fields), AO 2019 (20, TennisLive shows no break points faced) and US Open 2025 (8).

  The answer said: the freeze was loosened three times, never lifted; the record of 13 Oct is narrower than the owner's 11 Oct question; filling is better in expectation, tiny, a repair. It recommended (verbatim):
  > 1. **Fill them.** Add them as a package that goes in at the next rebuild, with no retrain for these alone. The code that reads TennisLive's statistics as box scores already exists; the weekly feed uses it for 2026.
  > 2. **Write down what you meant on 11 Oct, so this stops coming back.** Lower-level data goes in by itself, and is listed and covered by the check at each rebuild, when both of these hold:
  >    - its source counts the same way as our match table on the matches both hold;
  >    - it fills holes at levels and seasons we already cover.
  >
  >    Test first only when it would add coverage we don't have in some seasons. For example, ITF box scores before 2025 would take a level from none to nearly all in a few seasons. That changes what the rating inputs mean from season to season, and it's the risk the freeze was invented for on 8 Oct. Keep the 8 Oct model as the yardstick; it costs nothing.
  >
  > Want me to record that decision, update the project rules, and build the TennisLive fill package?
* **The owner's reply, verbatim** (14 Oct 2026):
  > "record the decision, update the projecct rules to match and build the tenis live package.
  > Very impressive work by the way , good job!"
* **How it was read:**
  * *Record the decision:* the policy of recommendation 2, as a decision record in `docs/decisions/`, with its two conditions made operational (thresholds stated there and in § 3 below), the test-first exception, and the yardstick kept.
  * *Update the project rules to match:* CLAUDE.md's freeze paragraph and its "tested as candidates" bullet; the decisions index; amendment notes in the 8 Oct current-best-model decision and the 13 Oct Tennis My Life decision, whose texts say other sources' lower-level data stays gated.
  * *Build the TennisLive package:* box scores from TennisLive's match-page statistics for lower-level matches the history holds without one, as an accepted package (`src/eda/current_best_model/additions.py`), which every template build and prediction run merges into its own tables; registered under the new policy, so that it is used on bet days at once and in training at the next rebuild, whose harm check covers it.
  * *Set aside:* (a) wiring TennisLive's point records or match times into the clock (not asked); (b) a retrain now (the policy and the Tennis My Life precedent: next rebuild); (c) writing the fills into the repository's shared tables (packages never change them, by design); (d) changing `history.py`'s gate (the policy is implemented by registered packages, which `history.py` already counts as accepted; a wider change, e.g. Sackmann's own corrections, was not proposed to the owner).
* **The target:** none; a data repair, no model result read. The harm check is the next rebuild's ([adoption framework](../adoption_framework/README.md) § 10: repairs pooled).

## 2. Starting point

* **Code:** commit `1d8f53e`, with many uncommitted changes by other sessions. The builder `src/eda/lower_level_evidence/candidate_stage0.py` (its sha256 goes into the build record); `additions.py`; `src/eda/data_gaps_2026/feed.py` (the rule screen reused).
* **Data:** the frozen reference's Stage 0 (8 Oct; the builder's `load_reference`), the reference's timeline; TennisLive's staged pages `data/dump/points/tennislive/matches.parquet` and `statistics.parquet` (41,412 pages, staged 10 Oct, P5 and P8 and earlier samples).
* **Earlier looks:** P5's comparison and this session's counts (§ 1). The feed already takes TennisLive's box scores, but only inside its 2026 scope (7 matches).
* **Environment:** `./python.sh` (the `tennis` Conda environment).
* **The idea:** a verified fix of missing data, more of a kind already used (repair). No model was read for any choice.

## 3. Plan

Fixed at 09:50 PDT, 14 Oct, before the candidate was built (the P5 numbers of § 1 had been seen; nothing of the candidate's).

1. **Decision record and rules** (`docs/decisions/2026-10-14-lower-level-gap-fills.md`; CLAUDE.md; decisions index; notes in the 8 Oct and 13 Oct records).
2. **Build** candidate `TLB20261014`: `--sources tennislive_pages --box-sources tennislive_pages --box-exclude tennislive_pages:ITF,tennislive_pages:ITFQ`, out `C:/Users/zerom/tnr_tl_box/candidates/TLB20261014` (outside `data/studies`, which every template build copies whole, as the feed's candidates are). TennisLive's pages are a box-only source: no new match, completions only, revisions counted and not applied.
3. **`--checks`** (structure, Stage 0's rules, duplicates, history, repair, inventory, dose, identity samples).
4. **The two conditions, per cell, fixed now:**
   * **C1, counts the same way.** Per tour and level, on the candidate's own links where the frozen history already holds a box score: TennisLive's eight counts (all but service games, which it does not give) equal Stage 0's on at least 98% of matches, with at least 30 such matches. A tour and level that fails, or has fewer than 30, keeps results only (its completions undone by `--derive-from ... --results-only`).
   * **C2, fills holes at covered levels and seasons.** Per tour, level and season with a completion: the frozen history already holds a box score for at least half of that cell's completed or retired matches. A cell that fails has its completions undone (`--keep-since` rules), and is left for a tested candidate.
   * Expected from P5 (seen): men's GSQ may fail C1 (94.9% there); every other cell should pass both.
5. **Identity:** the feed's rule screen (`feed.auto_verdicts`, `screen`) on the builder's samples, written as `identity_verdicts.csv` (by = rule); and a hand check of 30 applied completions drawn at random (seed 20261014): TennisLive's players, date, event, round and score beside Stage 0's, in `data/studies/tennislive_box_fill/hand_check.csv`.
6. **`--ready`;** the derive for C1/C2 if any cell fails, its checks and READY.
7. **Package:** `additions.py --package <candidate> --name tennislive_box_fill --decision docs/decisions/2026-10-14-lower-level-gap-fills.md`.
8. **Merge check:** `additions.py --check-against <candidate> --only tennislive_box_fill` must pass.
9. **Today's tables, read-only:** `additions.merge` on the repository's current Stage 0 in memory, every listed package plus this one: how many completions apply, and why any is skipped.
10. **Register** (`additions.py --register tennislive_box_fill`), after telling the busy peer session; the README; this log's §§ 7–10.

## 4. Chronology

Local time (PDT, UTC−7). "Results" means any outcome-based score of any model: none is read in this study.

| When | Step (command or action) | Why | Results seen by then | Output |
|---|---|---|---|---|
| 08:40–09:10 | The first answer's lookups (§ 1), read-only | The owner's question | none | chat |
| 09:15 | The owner's reply (§ 1, verbatim) | – | none | – |
| 09:15–09:45 | Read `additions.py`, the builder's TennisLive loader, `build`, checks, `derive` and `main`, `feed.py`'s run and rule screen, `prediction_run/run.py`'s table steps, the daily engine's checkpoint hashing (`dp_hash.py`, `dp_steps.run_day`); `selected_instance.json` (template_2026-10-14, switched 07:42); running processes (three downloaders, no build); peer sessions (17, one busy) [observed] | How a package is built, merged and used live, and what it could disturb | none | – |
| 09:30 | Men's GSQ disagreements by edition (P5's tables) [observed]: AO 2018 22, AO 2019 20, US Open 2025 8 | Whether TennisLive counts as Stage 0 does there | none | § 1 |
| 09:50 | Log opened; plan § 3 fixed | Rule 2 | none | this file |
| 09:29–09:32 | **Build** `candidate_stage0.py --label TLB20261014 --out C:/Users/zerom/tnr_tl_box/candidates/TLB20261014 --sources tennislive_pages --box-sources tennislive_pages --box-exclude tennislive_pages:ITF,tennislive_pages:ITFQ --status-log data/studies/tennislive_box_fill/status.log`, exit 0 in 2.5 min [observed, `data/studies/tennislive_box_fill/build_TLB20261014.log`]: 40,638 page rows; 32,338 linked to Stage 0 matches; 0 new matches; 8,300 left out (7,284 "the same pair already in Stage 0 at this event (unconfirmed duplicate)", 565 level unknown, 315 not in the candidate, 133 round unknown, 3 other) | Plan step 2 | none | candidate folder |
| 09:35 | Decision record drafted (policy part; package section pending) | Plan step 1 | none | `docs/decisions/2026-10-14-lower-level-gap-fills.md` |
| 09:36 | `src/eda/tennislive_box_fill/conditions.py` written (C1, C2, the hand-check sample) and run on the candidate [observed, `data/studies/tennislive_box_fill/conditions.json`, `c1_agreement.csv`, `c2_coverage.csv`]: box layers on 30,229 matches: 420 completions (the earlier session's "about 420" is this count), 29,337 revisions (mostly service games, which TennisLive lacks), 472 identical; **417 completions pass Stage 0's checks** (3 fail: Gatineau 2019, Lima 2020 failed_check; Toulouse 2022 Q1 all_zero). **C1** (frozen history, eight counts): men CH 99.871% (17,013), CHQ 99.985% (6,746), **GSQ 95.261% (844): fails**, TQ 99.913% (2,294); women CH 100% (229), CHQ 100% (109), GSQ 98.869% (796), TQ 99.944% (1,778). **C2**: every cell passes but **men's GSQ 2018 (49.33% before; 183 completions)**; the narrowest passes are women's GSQ 2018 (53.85%; 139) and men's TQ 2015 (52.94%; 2) | Plan step 4 | none (counts only) | as listed |
| 09:40 | Reconciled with § 1's recount of 486 (P5's tables) [observed]: 219 of the 486 are builder completions; 181 are revisions (Stage 0 already holds a box score, from the other result file); 73 unconfirmed links; 11 level or round unknown; 2 linked without a layer. The builder's other 201 completions are men's 2018 Roland Garros (88) and Wimbledon (95) qualifying, women's of the same (68, 71) and 3 at RG 2022–2024, which P5 counted as having an official box score: Stage 0 holds them `blank` | Explain the two counts | none | – |
| 09:42 | Men's GSQ agreement by event [observed]: on the frozen history, 100% at every Australian Open, US Open and Wimbledon edition but US Open 2025 (96.8%); **Roland Garros 2022–2026 0–29%**, the editions whose frozen rows carry the known error (second serves booked as first serves; finding #2 of the input-data audit), replaced since by RG's own record (repair adopted 10 Oct, applied 13 Oct). **Against today's tables (the repository's Stage 0 after that repair), supplementary, not the pre-registered measure: men's GSQ 99.64% (845), women's 99.75% (798); RG 2022–2026 now 86–100%** | Why men's GSQ fails C1 | none | – |
| 09:44 | Slam-qualifying box share by season in today's tables [observed]: men 2013 0.75, 2014 0.75, 2015 0.50, **2016–2017 0.00**, **2018 0.49**, 2019–2026 ≈1.00; women 2013 0.59, 2014 0.99, **2015–2017 0.00**, **2018 0.54**, 2019–2026 ≈1.00. Three applied completions (RG 2022 men 1, women 1; RG 2024 women 1) already hold a box score in today's tables (the RG repair); the merge will skip them | C2's reading | none | – |
| 09:46 | **Judgment call 1** (§ 6): the package keeps the pre-registered measures; men's GSQ keeps results only (`--results-only atp:GSQ`), 184 completions undone; the men's 2018 RG and Wimbledon qualifying (183) go to the owner as a recommendation, not into this package | – | none | – |
| 09:47 | **Failure:** `--checks` stopped in `check_rules`: `additions.parquet` of a candidate without new matches was written as a frame without columns (`KeyError: None of ['match_id', 'source']`). The builder had never built a box-only candidate | Plan step 3 | none | `checks_TLB20261014.log` (first run) |
| 09:48–09:52 | **Fix 1:** `candidate_stage0.empty_additions()` (`ADDITION_COLUMNS`, `ADDITION_DERIVED`); the non-empty path unchanged. Test added (`test_a_candidate_without_new_matches_writes_additions_the_checks_can_read`); 32 pass. Rebuilt the candidate with the fixed builder; `conditions.py` re-run: the same numbers (420 / 417 / C1 / C2) [observed] | – | none | `build_TLB20261014_rerun.log`, `conditions_rerun.log` |
| 09:53 | **Failure 2:** `--checks` stopped in `inventory` → `relevance`'s `merge_asof`: the empty frame's text columns were object, the player table's `str` (pandas 3.0.6) | – | none | – |
| 09:54–09:57 | **Fix 2:** `empty_additions` types its text columns `str` (as a written additions table reads back); test asserts `StringDtype`; 32 pass; rebuilt; **`--checks` exit 0** [observed]: structure pass (reference facts identical; `has_box` changed only where a layer applied; timing identical); duplicates 0; history "accepted 3 (decided repairs 3) … lower-level revised 414 … refused" (as a candidate must read before registration); repair remaps 0 | – | none | `checks_TLB20261014.log` |
| 09:58 | **Failure 3:** `feed.auto_verdicts` stopped on the empty `identity_sample_players.csv` (`EmptyDataError`). **Fix 3:** `feed._sample()` returns None for an empty sample; new `test/data_gaps_2026/test_feed.py`; 7 pass. Peer 9e had edited the same builder today (`WTA_SITE_MISFILED`, its uncommitted lines); left untouched | Plan step 5 | none | – |
| 09:59 | Rule screen [observed]: links 19 right, 1 unsure (Lena Rüffer listed as Papadakis, name grade 3), unsure share 0.05 ≤ 0.25: pass; written as `identity_verdicts.csv` (by = rule). `--ready` exit 0 | Plan step 5 | none | candidate folder |
| 10:00–10:03 | **Derive** `TLB20261014_pkg --derive-from TLB20261014 --results-only atp:GSQ`; its `--checks` exit 0 (history "accepted 2 (decided repairs 2) … revised 231"); `--ready` exit 0 [observed] | Plan step 6 | none | `derive_*.log`, `checks_TLB20261014_pkg.log` |
| 10:04 | `conditions.py` on the derived candidate (`--out data/studies/tennislive_box_fill/package`) [observed]: **233 applied**; every cell passes C1 and C2; the hand-check sample (30, seed 20261014) written | Plan step 4 on the package | none | `package/conditions.json` |
| 10:06 | **Hand check** of the 30 (by Claude) [observed]: 30 right (same players, event, round, score; spellings and retirements noted) | Plan step 5 | none | `package/hand_check.csv` |
| 10:08–10:12 | **Side check added** to `conditions.py` (`sides`: side A's counts re-derived from names alone) [observed]: 233 of 233 counts on the named player; winners agree 232; the other is Chengdu 2018 F (Zhang d. Laaksonen 2-6 5-2 ret.), TennisLive's winner field naming Laaksonen. Test file `test/tennislive_box_fill/test_conditions.py` (C1, C2), 2 pass | Beyond the plan: the builder places counts by its link's side; an independent check was cheap | none | `package/sides_check.csv` |
| 10:14 | **Package** `additions.py --package … --name tennislive_box_fill --decision docs/decisions/2026-10-14-lower-level-gap-fills.md`: 0 added, 233 completions; **`--check-against … --only tennislive_box_fill`: pass** (matches, players, timeline equal) [observed] | Plan steps 7–8 | none | `package_write.log`, `check_against.log`, the package's `manifest.json` |
| 10:16 | **Merge on today's tables, read-only** (`additions.merge`, this package then the feed's `20261013c`) [observed]: 231 of 233 applied; the 2 others (RG 2022 men 1… listed above: RG 2022 women 1, RG 2024 women 1 were the three noted at 09:44; on today's tables 2 of the package's 233 already hold RG's box score) skipped; the feed: 48,529 added, 43 skipped as same id, 1 completion, as before | Plan step 9 | none | `package/merge_on_today.json` |
| 10:18 | Running processes (three downloaders only, no build or bet-day run); heads-up sent to the busy peer `tennis-predictions-9e` (§ Appendix) | Plan step 10 | none | – |
| 10:20 | **The peer's reply, verbatim (excerpt):** "No conflict from tennis-predictions-9e: go ahead and register tennislive_box_fill. Nothing of mine reads accepted.json or the merged tables right now. … Today's noon feed run (the Windows task) will advance accepted.json's "feeds" entry with --advance, at roughly 12:15-12:30. Please finish your registration before then, so the two writes to accepted.json don't race." | – | none | – |
| 10:21 | CLAUDE.md's training-data bullets rewritten (re-read first; other sessions' uncommitted edits elsewhere in the file kept) | Plan step 1 | none | CLAUDE.md |
| 09:59 (clock) | **Registered:** `additions.py --register tennislive_box_fill` at 09:59:00 PDT by the shell's clock [observed]; `accepted.json` packages ["tennislive_box_fill"], feeds unchanged; `listed()` = [tennislive_box_fill, 20261013c]; `accepted_ids`: 48,572 added, 234 completed. *Correction to the times in this table: they were written from memory and run about 20 minutes late; the shell's `date` read 09:26 at the instance check and 09:59:00 at registration, so the rows from 09:47 on happened between about 09:35 and 09:59.* | Plan step 10 | none | `accepted.json` |
| 10:00 (clock) | `history.check` on the derived candidate after registration [observed]: "accepted 233 (completions 233) … lower-level revised 0 → the template may be built". Reply sent to 9e | – | none | `package/history_after_register.json` |
| after | Decision record completed (package section, C1's "history" defined as today's tables with the frozen copy read beside it, C2's wording corrected to the § 3 definition, "Implemented"); decisions index row and the 8 Oct row's note; notes in the 8 Oct and 13 Oct records; this README; the studies index row. Reach read from the derived candidate's `dose.csv` [observed]: 1,229 of 67,226 frame matches with a new box score in a player's previous 365 days, 169 within 28 days | – | none | as listed |
| after | Tests: `test/lower_level_evidence test/data_gaps_2026 test/current_best_model test/tennislive_box_fill`: **381 passed, 6 xfailed** (the 6 expected failures noted in the feed study's log) [observed] | – | none | – |
| 10:05 (clock) | **Correction: the times of this table and of § 3.** They were estimated, not read. The files' modification times and the builder's status log give the real order [observed]: the log and § 3 were written before the first build started (09:29:32 by `status.log`), not at 09:50; first build 09:29–09:32; conditions re-run after fix 1, 09:39:54; the rebuild after fix 2, 09:44:51; checks pass 09:47:04; identity verdicts 09:48:19; READY 09:48:28; derive and its checks to 09:51:24; the package's conditions 09:52:50; hand check 09:53:07; package written 09:53:35; merge check 09:55:54; merge on today's tables 09:58:05; CLAUDE.md 09:58:51; **registered 09:59:04**; history after registration 10:00:08. The order of the rows is right; only their clock labels were off. **Clarification of the 10:16 row:** on today's tables, the 2 of the package's 233 that already hold Roland Garros's own box score are women's RG 2022 (1) and RG 2024 (1); the third match noted at 09:44 (men's RG 2022) is not in the package | Rule 4 | none | – |
| 10:06 (clock) | The parent's C1/C2 files (written 09:39:54, after fix 1's rebuild) were not re-run after fix 2's rebuild. Checked instead [observed]: the final parent's and the package's box layers are the same 30,229 rows apart from `applied` (417 against 233), and `package/c1_agreement.csv` (09:52, on the final candidates) is byte-identical to the parent's | Completeness | none | – |

### Resumed 14 Oct 2026, 11:49 PDT: the men's Slam-qualifying fills and the two conditions

* **The owner's words, verbatim** (14 Oct 2026, quoting the report's paragraph):
  > "183 more matches I'd add. Men's 2018 Roland Garros and Wimbledon qualifying have no box scores in our history, and TennisLive has them. They narrowly missed both thresholds:
  >
  > Yes add and fix those"
* **How it was read:**
  * *add:* the 184 men's Slam-qualifying completions of the parent candidate (183 of 2018 Roland Garros and Wimbledon qualifying, 1 of RG 2022, which today's tables already score from RG's own record), as a second package;
  * *fix those:* the two conditions that kept them out, so that the same misfire does not recur:
    * **C1** is read on today's tables (with every decided repair) as the deciding reading, the frozen copy's reading kept beside it (the decision record's text since 10:01 already says so; the code did not);
    * **C2** gains a second way to pass: the fill brings the cell's box-score share closer to its level's median share over the other seasons from 2013 (seasons with at least 30 played matches), measured on today's tables. A cell that already holds half its box scores still passes as before. A level that is empty in most seasons (ITF before 2025, women's ITF qualifying) has a median near 0, so its fills still fail and stay a tested candidate.
  * *Other reading, set aside:* "fix those" meaning only "fill those matches". Fixing the tests is the reading the report invited ("both misses come from where I drew the lines"); the final message says which reading was acted on.
* **Plan (fixed before re-running any condition):**
  1. `conditions.py`: C1 on today's tables beside the frozen copy; C2's relative branch; tests.
  2. Re-run on the parent `TLB20261014`: every cell under the fixed conditions.
  3. Derive `TLB20261014_mgsq` (`--keep-tours atp --keep-levels GSQ`); its checks and READY (the parent's identity verdicts carry over).
  4. Its conditions, a hand check of 30 (seed 20261015), the side check.
  5. Package `tennislive_box_fill_men_gsq`; `--check-against`; the merge on today's tables, read-only.
  6. Register only after the noon feed run has written `accepted.json` (the peer's request, 10:20).
  7. The decision record, CLAUDE.md, the indexes and the report.

| When | Step (command or action) | Why | Results seen by then | Output |
|---|---|---|---|---|
| 11:49 (clock) | Time and `accepted.json` read: packages ["tennislive_box_fill"], feeds 20261013c; the feed's weekly run starts at 12:00 | Rule 2; the peer's request | none | – |
| 11:50 | `conditions.py` changed: `history_counts()` and `c1(..., hist)` (C1 on today's tables; the frozen reading beside it in `c1_agreement.csv`); `c2()` on today's tables, completions already scored there not counted (`completions_landing`), the level's median over the other seasons from 2013 with at least 30 played (`level_median_other_seasons`), `pass_half` or `pass_toward_level`. Tests: 2 updated, 2 new (`test_c1_reads_todays_tables_where_a_repair_replaced_the_frozen_counts`, `test_c2_lets_a_season_with_a_hole_catch_up_with_its_level`, the latter with an ITF-like level that still fails); 4 pass | Plan 1 | none | – |
| 11:51 | **The whole candidate under the fixed conditions** (`--out data/studies/tennislive_box_fill/parent_fixed`) [observed]: C1 on today's tables passes for every tour and level (men's GSQ 99.645% on 845; frozen 95.261% on 844, listed as `c1_pass_today_fail_frozen_with_completions`); C2 passes every cell (men's GSQ 2018: 0.4933 → 0.9018, level median 0.9978, by `pass_toward_level`); 417 applied, 414 land on today's tables, 0 missing from them; sides 417 / winners 416 | Plan 2 | none | `parent_fixed/` |
| 11:52–11:54 | **Derive** `TLB20261014_mgsq --derive-from TLB20261014 --keep-tours atp --keep-levels GSQ` (233 completions undone, 184 kept); `--checks` exit 0 (history "accepted 1 (decided repairs 1) … revised 183"); `--ready` exit 0 [observed] | Plan 3 | none | `derive_TLB20261014_mgsq.log`, `checks_TLB20261014_mgsq.log` |
| 11:55 | Conditions on it (`--out …/men_gsq --seed 20261015`) [observed]: 184 applied, 183 landing; no cell fails; sides 184 of 184, winners 184 of 184. Hand check of the 30 drawn: 30 right (Roland Garros and Wimbledon 2018 qualifying; spellings noted) | Plan 4 | none | `men_gsq/conditions.json`, `men_gsq/hand_check.csv` |
| 11:56 | **Package** `tennislive_box_fill_men_gsq`: 0 added, 184 completions; `--check-against … --only tennislive_box_fill_men_gsq`: pass [observed] | Plan 5 | none | `men_gsq/package_write.log`, `men_gsq/check_against.log` |
| 11:58 | A background watcher waits for the feed's run record (`feed/runs.jsonl` gaining a line); today's scheduled job was on its WTA step at 12:06, the feed after it | Plan 6 | none | – |
| 12:00–12:20 | The decision record, CLAUDE.md, the 8 Oct record's note, the decisions and studies indexes and the README updated for the fixed conditions and the second package. Reach [observed, the candidates' `dose.csv`]: second package 913 frame matches (365 days) and 123 (28 days); both packages together 2,100 and 292 | Plan 7 | none | as listed |
| 12:21–12:27 | Tests again: 385 passed, 6 xfailed [observed]. The scheduled job still on its WTA step (log 12:26); the feed not started | – | none | – |
| 12:32:21 | Merge on today's tables, read-only, in the order a run would merge (first package, second, the feed's 20261013c) [observed]: 231 of 233; **183 of 184** (the RG 2022 match already scored); the feed 48,529 added, 43 same id, 1 completion, as before | Plan 5 | none | `men_gsq/merge_on_today.json` |
| 12:32:27 | **Registered** `tennislive_box_fill_men_gsq` [observed]: packages ["tennislive_box_fill", "tennislive_box_fill_men_gsq"]; `listed()` both packages then 20261013c; `accepted_ids` 418 completions. The feed's run had started its candidate build at 12:31:21 (`feed.log`; its status line 12:32:01): **judgment call 7** (§ 6) | Plan 6 | none | `accepted.json` |
| 12:33 | Message to 9e (registered during the feed's build; no write overlap; why). `history.check` on `TLB20261014_mgsq` [observed]: "accepted 184 (completions 184) … the template may be built" | – | none | `men_gsq/history_after_register.json` |
| 12:56:50 | **The feed's run ended** (`runs.jsonl`, label F20261014, exit 0, "advanced", 25.3 min) [observed]: `accepted.json` packages ["tennislive_box_fill", "tennislive_box_fill_men_gsq"], feeds {"lower_level_feed": "20261014"}; `listed()` hash-checks all three; `accepted_ids` 49,001 added, 418 completed. Judgment call 7's reasoning held: the advance kept both packages | Checklist item | none | `accepted.json` |
| 12:58 | Merge on today's tables with every listed package and the new snapshot, read-only [observed]: 231 of 233, 183 of 184; the feed's 20261014 48,958 added, 43 same id, 1 completion | – | none | `men_gsq/merge_after_feed_20261014.json` |
| 14:20–14:53 | Peer 9e's coordinated live Stage 0 rebuild (stamp 2026-10-14T2119Z; the owner's P6 decision of 14 Oct: Tenerife Challenger 3 of 2024 re-dated). Its report, as received: live Stage 0 873,681 matches; history.py "the template may be built", decided repairs 2,992, completions 3, the one moved from decided repairs being this study's men's RG 2022 match, which `history.py` counts as a package completion first (a label only: those 3 matches take RG's own box score in the tables, and the merge skips the packages' completions for them) | Peer report, not re-checked except as below | none | – |
| 15:00 | Merge on the rebuilt live tables, read-only [observed]: 873,681 matches; 231 of 233, 183 of 184; the feed's 20261014 as before | After a shared-table change | none | `men_gsq/merge_after_rebuild_2119Z.json` |

## 5. Sources (research only)

None: no external source was consulted. TennisLive's pages were downloaded on 9–10 Oct by work package P5 ([gap_downloads README](../gap_downloads/README.md)), under the owner's decision of 8 Oct.

## 6. Judgment calls and deviations

1. **Men's Slam qualifying kept out, by the pre-registered measure** (09:46, after C1/C2 were read on the candidate; no model read).
   * Options: (a) apply § 3 as fixed (C1 on the frozen history), leaving men's GSQ out; (b) re-measure C1 on today's tables, where the Roland Garros repair replaced the frozen rows' known error, which passes (99.64%).
   * Chosen: (a). § 3 fixed the measure before the numbers; changing it after seeing that it excluded a cell is the move the process rules guard against. Under (b) the result would barely differ: men's GSQ 2018 still fails C2 (49.33% < 50%); only one RG 2022 match would enter, and it already holds RG's box score on today's tables.
   * The decision record now defines "the history" as today's tables with decided repairs and asks both readings, so a later package faces the right comparison.
   * What the other branch changes: nothing in this package. The 183 men's 2018 matches go to the owner with a recommendation to add them.
2. **The C2 threshold (half the cell's box scores) and the C1 threshold (98%, 30 shared)** are Claude's operationalisation of the owner's wording, fixed in § 3 before the candidate's numbers. P5's per-level agreement rates were known then (§ 1), so the 98% bar was not blind to which levels would pass: at 98% only men's GSQ (94.9% on P5) was expected to fail. The weekly feed's precedent sat between 95% (excluded: TennisLive at ITF) and 99% (included).
3. **The two code fixes** (empty additions, empty identity samples) were needed by the first box-only candidate. Neither changes a candidate that adds matches. Both were tested before the feed's weekly run at noon used the files.
4. **The rule screen in place of the full hand check of the builder's link sample**, as the weekly feed does; added on top: a hand check of 30 of the package's own completions, and the side check on all 233.
5. **Registered before the README and the decision text were final,** at the peer's request, so as not to race the noon feed run's write to `accepted.json`. The evidence and the checks were complete at registration.
6. **The chronology's clock times** from 09:47 were written from memory and run late; see the correction row. No choice depended on them.
7. **The second package was registered during the feed's run, not after it** (12:32, a deviation from the resumed plan's step 6).
   * The plan, at the peer's request (10:20), was to register after the noon feed run had written `accepted.json`.
   * At 12:32 the scheduled job had been on its WTA step until 12:31. The check run just before registering read the feed's status as still on last night's lines (the status line of 12:32:01 is from the new run's build, seen only after). So the feed had in fact just started.
   * Why it is safe, held at the time and re-checked after: the feed writes `accepted.json` only at its last step, `--advance`, after its build, checks, derive, snapshot and merge check. No step before reads the packages list for a pass or fail (`history_ok` needs only "dropped 0" and "future 0"; `--check-against` merges only its snapshot), and `--set-feed` rewrites only "feeds".
   * The peer was told, with the reasons. The watcher on `runs.jsonl` checks after the advance that `accepted.json` holds both packages.
8. **The fixed conditions were written after seeing that the first ones excluded men's GSQ,** at the owner's explicit instruction ("fix those"). The fix is general, not tuned to the cell:
   * C1 reads the tables the model uses;
   * C2's branch reads the cell against its own level's other seasons.

   Its tests include a level the branch must still refuse (ITF-like, median 0). Under the fixed conditions every one of the 417 completions passes; under the old ones 233 did.

## 7. Claims and their evidence

| Claim (README) | Evidence | Status |
|---|---|---|
| 420 completions found, 417 pass Stage 0's checks | `conditions.json` (parent), `checks_TLB20261014.log` | observed |
| Agreement per tour and level (99.87% … 95.26%) | `c1_agreement.csv` (parent); `package/conditions.json` | observed |
| Men's GSQ 99.64% on today's tables | chronology 09:42, the command in that row (not saved as a file) | observed; supplementary |
| Coverage by cell; men's GSQ 2018 49.33% | `c2_coverage.csv` | observed |
| Slam-qualifying box share by season | chronology 09:44 (command output, not saved) | observed |
| 233 in the package, by tour, level and season | `package/conditions.json`; the package's `manifest.json` | observed |
| 30 of 30 by hand | `package/hand_check.csv` | observed (Claude's reading) |
| 233 of 233 on the named side; winners 232 | `package/sides_check.csv` | observed |
| The merge reproduces the candidate; 231 apply today | `check_against.log`; `package/merge_on_today.json` | observed |
| "the template may be built" after registration | `package/history_after_register.json` | observed |
| Reach 1,229 / 169 | the derived candidate's `dose.csv` | observed |
| About four extra minutes a bet-day run | the 11 Oct live run (states 390 s with 11 parts recomputed, master-pipeline log 11:25) against about 2 min resumed | inference |
| Under the fixed conditions all 417 pass; men's GSQ 99.645% today, 95.261% frozen; 2018 0.49 → 0.90 against a level median of 0.998 | `parent_fixed/c1_agreement.csv`, `parent_fixed/c2_coverage.csv` | observed |
| Second package: 184, 183 landing; 30 of 30 by hand; sides 184, winners 184 | `men_gsq/conditions.json`, `men_gsq/hand_check.csv`, `men_gsq/sides_check.csv`, `men_gsq/merge_on_today.json` | observed |
| Reach together 2,100 (3.1%) and 292 | `TLB20261014/dose.csv` (the parent holds all 417) | observed |
| The effect on forecasts is tiny | reach above; no model read | inference |

## 8. Weak points

* **The thresholds are judgment.** 98% and one half are Claude's; the women's GSQ 2018 cell passes C2 at 53.85%, men's GSQ 2018 fails at 49.33%. A slightly different bar flips both.
* **Agreement is measured where both sources score a match;** the fills are matches where our files have none. If TennisLive is worse exactly where the official files are blank (for example events whose official statistics were never published), the agreement rate would not show it. The hand check (30) and Stage 0's own box checks (passed by all 233) are the guard.
* **The builder's linker leaves out about 7,300 unconfirmed TennisLive rows,** most of them already scored or main tour; up to 73 of P5's gap candidates are among them. Missing fills, not wrong ones.
* **No model was read.** The harm check is the next rebuild's, pooled with whatever else enters; it cannot see an effect this small, by design (adoption by kind of change).
* **Where a flaw would hide:** in side placement (checked independently on all 233) or in a link to the wrong meeting of the same pair (the builder's set-score confirmation; the hand check).
* **A re-design** would measure C1 on today's tables from the start, set C2 relative to the level's other seasons (a fill that moves a season toward its neighbours passes), and extend the builder's link confirmation for TennisLive's partial records.

## 9. Reviewer checklist

* [ ] `additions.py --check-against C:/Users/zerom/tnr_tl_box/candidates/TLB20261014_pkg --only tennislive_box_fill` passes.
* [ ] `conditions.py --candidate <pkg> --out <tmp>` reproduces `package/conditions.json` (233; sides 233/232).
* [ ] The package's `manifest.json` hashes match its files (`additions.listed()` checks them).
* [ ] Spot-check five rows of `package/hand_check.csv` against the TennisLive pages in `data/raw/point_sources/tennislive/matches/`.
* [ ] `./python.sh -m pytest test/lower_level_evidence test/data_gaps_2026 test/current_best_model test/tennislive_box_fill -q`.
* [ ] The next template build's `chain_additions.json` lists `tennislive_box_fill` with 231 or more completions applied, and `tennislive_box_fill_men_gsq` with 183.
* [ ] `additions.py --check-against C:/Users/zerom/tnr_tl_box/candidates/TLB20261014_mgsq --only tennislive_box_fill_men_gsq` passes.
* [ ] `conditions.py --candidate <parent> --out <tmp>` reproduces `parent_fixed/` (417 pass; men's GSQ by `pass_toward_level`).
* [ ] After the feed's advance of 14 Oct, `accepted.json` holds both packages and the new snapshot.

## 10. Reproduction

```
B=src/eda/lower_level_evidence/candidate_stage0.py; P=C:/Users/zerom/tnr_tl_box/candidates; S="--status-log data/studies/tennislive_box_fill/status.log"
./python.sh $B --label TLB20261014 --out $P/TLB20261014 --sources tennislive_pages --box-sources tennislive_pages --box-exclude tennislive_pages:ITF,tennislive_pages:ITFQ $S   # ~2.5 min
./python.sh src/eda/tennislive_box_fill/conditions.py --candidate $P/TLB20261014                     # C1, C2 on the whole candidate
./python.sh $B --label TLB20261014 --out $P/TLB20261014 --checks $S                                     # ~2 min
# identity_verdicts.csv: src/eda/data_gaps_2026/feed.py's auto_verdicts + screen on $P/TLB20261014 (the rule screen)
./python.sh $B --label TLB20261014 --out $P/TLB20261014 --ready $S
./python.sh $B --label TLB20261014_pkg --out $P/TLB20261014_pkg --derive-from $P/TLB20261014 --results-only atp:GSQ $S
./python.sh $B --label TLB20261014_pkg --out $P/TLB20261014_pkg --checks $S
./python.sh $B --label TLB20261014_pkg --out $P/TLB20261014_pkg --ready $S
./python.sh src/eda/tennislive_box_fill/conditions.py --candidate $P/TLB20261014_pkg --out data/studies/tennislive_box_fill/package
./python.sh src/eda/current_best_model/additions.py --package $P/TLB20261014_pkg --name tennislive_box_fill --decision docs/decisions/2026-10-14-lower-level-gap-fills.md
./python.sh src/eda/current_best_model/additions.py --check-against $P/TLB20261014_pkg --only tennislive_box_fill
./python.sh src/eda/current_best_model/additions.py --register tennislive_box_fill
# the second package (14 Oct, "Yes add and fix those"), with the fixed conditions
./python.sh src/eda/tennislive_box_fill/conditions.py --candidate $P/TLB20261014 --out data/studies/tennislive_box_fill/parent_fixed
./python.sh $B --label TLB20261014_mgsq --out $P/TLB20261014_mgsq --derive-from $P/TLB20261014 --keep-tours atp --keep-levels GSQ $S
./python.sh $B --label TLB20261014_mgsq --out $P/TLB20261014_mgsq --checks $S
./python.sh $B --label TLB20261014_mgsq --out $P/TLB20261014_mgsq --ready $S
./python.sh src/eda/tennislive_box_fill/conditions.py --candidate $P/TLB20261014_mgsq --out data/studies/tennislive_box_fill/men_gsq --seed 20261015
./python.sh src/eda/current_best_model/additions.py --package $P/TLB20261014_mgsq --name tennislive_box_fill_men_gsq --decision docs/decisions/2026-10-14-lower-level-gap-fills.md
./python.sh src/eda/current_best_model/additions.py --check-against $P/TLB20261014_mgsq --only tennislive_box_fill_men_gsq
./python.sh src/eda/current_best_model/additions.py --register tennislive_box_fill_men_gsq
```

No GPU. The candidates are rebuildable from the staged TennisLive pages and the frozen reference; the builder's sha256 is in each `build_record.json`.

## Appendix: messages to and from peer sessions

* **To `tennis-predictions-9e`** (the busy peer), before registering: the package, its effect on builds and bet-day runs (packages merged before the feed; checkpoint families recomputed, about four minutes, until a new Monday checkpoint; tiny differences in a replay on `template_2026-10-14`), and an offer to hold the registration.
* **From `tennis-predictions-9e`:** no conflict; finish before the noon feed run's `--advance` (12:15–12:30); it changed the builder's WTA-website loader today (`WTA_SITE_MISFILED`), women's 2026 results only.
* **To `tennis-predictions-9e`,** after registering: done at 09:59; `--set-feed` keeps "packages"; the two small code changes its feed run will use.
* No subagent was launched.
