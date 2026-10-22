# The data issues P6 found: the Tenerife dates corrected, the ATP's Challenger point files staged, two new checks

**Decided by the owner on 14 October 2026,** on four recommendations of the [P6 data-issues study](../studies/p6_data_issues/README.md) ([process log](../studies/p6_data_issues/process_log.md)). The owner pasted them back (verbatim):

> "Apply the Tenerife correction: yes. It's a repair that closes a leak. It needs a date action added to the correction tables, then a harm-check comparison.
> Put the ATP Challenger files on the map in their own tables: yes, keeping them out of the serve-speed history unless you decide otherwise.
> Add a weekly check of Tennis My Life's new Challenger dates against TennisLive's: yes. Tennis My Life is now the only Challenger source, so a misdated edition would enter unchecked.
> Have the feed alert on new "player in two main draws in one week" flags: yes. Blocking on every flag would stop on known older cases."

and wrote: **"Double check all above is currently a good idea, then if you decide it is, execute it."** Recorded and carried out by Claude. Where the double-check changed how a point is carried out, it says so below.

## Decision

1. **The 31 matches of the third Tenerife Challenger of 2024 take their true date, 26 February 2024.**
   * **The fault.** Stage 0 holds them from Tennis My Life alone, dated 21 January as "Tenerife 1". Sackmann lacks the edition. The leak-proof clock therefore lets their results count from about 1 February, a month before they were played, and 136 later matches read them early (93 of them evaluation matches, in the frozen reference too).
   * **The evidence.** Three independent reviewers confirmed the same 31 rows, operation and value under the rule of 8 October ([corrupt data](2026-10-08-corrupt-data-fixes.md)): `data/studies/p6_data_issues/stage0_review/consensus.json`.
   * **The mechanism: a date correction in the correction tables, keyed by the match, not by the row number.** `date_corrections.csv` sits beside `row_corrections.csv` in `data/studies/input_data_audit/fixes/`, and `src/eda/input_data_audit/corrections.py` applies it when Stage 0 is built.
     * *Changed by the double-check.* The 8 October tables find each row by its file and row number, and stop the build when a guarded row no longer matches. Tennis My Life rewrote this file's row order on 13 October: none of its 5,936 rows kept its position. A row-numbered correction would have stopped every Stage 0 build at its next revision, including bet-day runs.
     * So each correction names the match by its file, tournament id, round and both players, and by the wrong date it replaces. If Tennis My Life fixes the date itself, the correction no longer matches and does nothing, and the build says so.
   * **The route.** A candidate built on the frozen reference with these 31 dates changed, and `compare.py` read as a harm check; the change is far below what it can resolve. The rule, declared before any reading: adopt unless the candidate reads worse by more than 0.10 mLL with the whole 95% interval below 0, or an input moves in a way the change's dose does not explain ([adoption by kind](2026-10-09-adoption-by-change-class.md)).
   * **Then it enters** the live tables at a coordinated Stage 0 rebuild, as the Roland Garros repair did. `history.py` counts the 31 as decided repairs.
   * **Not included:** the two Australian Open 2021 qualifying walkovers the study first proposed. The reviewers found them duplicates of Sackmann's rows, not misdates; re-dating them would have created a leak.
2. **The ATP Stats Centre's Challenger point files go on the data map, in tables of their own.**
   * The files: MatchBeats (every point) and rally analysis, for 2,360 Challenger matches of 2021-24 that SofaScore lacks and the Hugging Face copy holds without point files.
   * They are decrypted as the site's own page does and staged in `data/dump/points/infosys_challengers/` (`src/ingest/point_sources/infosys_challengers_stage.py`), and the map reads them as a source of its own.
   * **Kept out of the serve-speed history:** they never enter `data/dump/points/infosys_atp/`, which the serve-speed backfill reads, and the ATP files' own decrypt and stage steps now leave these purposes out.
   * Whether Challenger serve speeds should ever enter the speed history is a separate question, for the feature pool.
3. **A weekly check of Tennis My Life's edition dates** (`src/eda/tml_revisions/edition_dates.py`), in the weekly task.
   * **How it judges.** It re-runs the study's linking and verdicts on the day's files: Tennis My Life's rows against Sackmann's rows, TennisLive's listing days, SofaScore's starts and TDI's days.
   * **When it alerts.** On an edition dated in another week than it was played that is not on the known list. The known list holds the study's 67 editions; Tennis My Life re-dating one of them changes its key, so that alerts too.
   * **It corrects nothing.** A flagged edition goes to the three-reviewer route.
   * *Against TennisLive's alone, as the recommendation said?* The check uses every play-day source the study validated. TennisLive's days decide most editions; Sackmann's (to June 2026), SofaScore's and TDI's guard against TennisLive's own errors.
4. **The lower-level feed alerts on a new "player in two main draws of one week" flag** (`src/eda/data_gaps_2026/two_draws.py`).
   * After each weekly snapshot, the flags are compared with the last advanced snapshot's. A new one alerts (the weekly task's notification), and none blocks.
   * The 13 October snapshot's 28 flags are the first baseline: 25 from the WTA website copy's misfiled week, 3 from the W15 Luque 2026 edition the copy lists twice.

## Status

**All four carried out on 14 October 2026** (the study's README, section 5, and process log record each step).
1. **The Tenerife dates are in force.**
   * **The harm check:** both tours, both stages, 2020-2024: -0.001 [-0.004, +0.002] mLL per match, unresolved, P(better) 0.23. No input flagged, so **adopted** under the rule above.
   * **The table:** `data/studies/input_data_audit/fixes/date_corrections.csv`, added 14:15 PDT.
   * **The live tables** were rebuilt at stamp 2026-10-14T2119Z, equal to the dry run byte for byte. All 31 matches now have their exact play day in the timeline. `history.py`: the template may be built.
   * **A latent bug** in `rebuild_stage0.id_map` (it fails when no match id changes) stopped the first attempt halfway. It was restored from its kept copies at once, then fixed and tested.
2. **The ATP Challenger files are on the map:** 2,375 matches, 394,010 points. All are linked to matches the map already held; none was added.
3. **The weekly date check:** the job `tml_dates`, Wednesdays from 21 October. Its first run found the 67 known editions and nothing new.
4. **The feed's two-draws alert:** in the feed and the weekly task from 21 October. The snapshot advanced on 14 October holds the September WTA matches correctly.
