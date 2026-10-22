# Tennis My Life's own corrections of the lower levels it publishes enter by themselves; a held file is accepted after a check

**Asked by the owner on 11 October 2026, decided on 13 October 2026.** On 11 October the master-pipeline session
reported that Tennis My Life had corrected 50 old lower-level matches since the 8 October freeze. The owner asked
(verbatim, [master-pipeline process log](../studies/master_pipeline/process_log.md), rows 11:55 and 12:05):

> "There was a freeze that was told to freeze and not include new challenger data until we run an experiment that checks how we should effectively integrate challenger data. We however completed the study and found how to effectively integrate challenger data by changing weight of that info and adjusting it by opponent skill. This is not that right? Why aren't we just using the newest data? Is it to save time from training a big model constantly?"

> "Do you recommend also retraining post 50 corrections? I'm away from my computer accessing remotely so it won't be competing for Gpu usage"

The session recommended accepting the corrections under a standing policy, and not retraining for them alone. **No
decision was recorded,** so every later session read the question as open: on 13 October the bet sheets carried
"Your decision on accepting those is still open". The owner asked whether there was "a communication issue between
agents on the state of this pipeline", was given these recommendations (verbatim):

> 1. **Record your 11 Oct answer as a decision.** Tennis My Life's corrections and new matches at the levels the model already uses would go in by themselves: on bet days straight away, and into training at the next rebuild. The rebuild check would list these changes instead of refusing, and each rebuild gets a harm check. Then I'd update the project rules, both session reports and the sheet notes to match. I prefer this to keeping bet days on the 8 Oct data. The mismatch is 50 old records, and a 20-year-old listed as 58 is exactly the kind of error you want fixed.
> 2. **Accept the four parked files under that rule, after one check.** I'd rebuild the match history in a scratch copy with them accepted and list every change. It takes minutes and changes no shared files.
> 3. **Still no retrain for these alone.** Include them in the next rebuild, for example once today's feed passes its harm check.

and answered: **"record the decision and run the check on the four files"**. Recorded and carried out by Claude
([report](../studies/tml_revisions/README.md), [process log](../studies/tml_revisions/process_log.md)).

## Decision

1. **What enters by itself.** The lower-level matches Stage 0 takes from Tennis My Life's own files, at the levels it
   fed the frozen reference: men's Challenger main draws, ATP tour qualifying and Slam qualifying. This covers its
   corrections (players re-identified, ages, scores, box scores), the matches it removes (duplicates, misfiled rows)
   and the past matches it adds. They are treated as main-tour corrections have been since 9 October: listed, not
   tested as a candidate.
2. **On bet days at once; in training at the next rebuild.** Prediction runs build from the day's files, so they
   already use them. Training takes them at the next template build on the day's tables. **No retrain for these
   alone** (the owner, 11 and 13 October).
3. **The history check lists them; it no longer refuses a build for them.** `history.py` counts them as `tml_lower`,
   apart from `gated`. These stay gated:
   * other sources' lower-level changes: new sources and kinds enter as accepted packages or through the lower-level
     feed ([10 Oct](2026-10-10-men-2026-challenger-data.md), [13 Oct](2026-10-13-lower-level-feed.md)). *Since
     14 Oct 2026, a package that fills holes from a source that counts as the history does is registered without a
     decision of its own ([decision](2026-10-14-lower-level-gap-fills.md)).*
   * Tennis My Life at a level it never fed;
   * a candidate build's box layers on a Tennis My Life row;
   * any change to a row Stage 0 takes from Sackmann.
4. **A harm check at each rebuild.** The next template build on the day's tables is compared with the current instance
   (both stages; harm = worse by more than 0.10 mLL with the whole 95% interval below 0, the adoption framework's
   default). The reading is pooled as a repair.
5. **Held files.** The download gate ([6 Oct](2026-10-06-tml-file-versions.md)) still holds a season file in which rows
   of the current copy are gone. A held file at these levels is accepted after the check
   `src/eda/tml_revisions/held_check.py`: Stage 0 is built in a scratch tree with and without it, and every changed
   match is listed.
   * **It is accepted when every change is:** a duplicate removed, a match restored to its own event or date, a key
     rebuilt for the same match, a player's id corrected, a score or box score revised, or rows Stage 0 already
     dropped. No main-tour match may change, and nothing unexplained may be lost.
   * **Otherwise** it stays held and goes to the owner.
6. **The four files held since 10 October** (Tennis My Life's 2022–2025 Challenger files) were checked and accepted on
   13 October (below).

## Evidence

* **Classified before any result:** a repair (the source's own corrections of data already used), and a recurring
  kind, so it is decided once as a policy ([adoption framework](../studies/adoption_framework/README.md) § 10). Its
  direction: adopt unless the harm check fails. No model was read for this decision.
* **The 50 corrections** (the master-pipeline session's lookup of 11 October, observed there):
  * 30 matches re-identified. 24 are 2011 qualifying matches at Rome and Umag, where the frozen copy has unnamed
    placeholder ids. The others: 1 Winston-Salem 2015 qualifying match, Andre Ilagan's 2017 Challenger moved to his
    main id, and 4 qualifying matches of 2026.
  * 20 revised in place. 18 are ages: Ilagan 56.5 → 25.6 in 15 Challengers, Miguel Tobon 58.2 → 20.2 in 3. The other
    2 are Ilagan's Washington qualifying matches, moved to his main id.
  * Their reach: 97 players, in 6,402 of the 62,869 rows the 2026 fit trains on, through one to three old results each.
  * The live runs of 13 October list the same 30 new, 30 dropped and 20 revised.
* **The four held files**, checked on 13 October ([report](../studies/tml_revisions/README.md);
  `data/studies/tml_revisions/held_check/`):
  * **The staging reproduces the repository's own:** the scratch tree's staging of the four current copies equals the
    repository's staged tables.
  * **What changes in Stage 0:** 24 matches (873,642 → 873,636). All are men's Challengers. No main-tour match changes,
    and no fact of a match held by both builds changes.
    * Champaign 2025: 4 duplicate copies of Sackmann's matches, carrying wrong player ids, are gone.
    * Rome GA: 3 matches of the February 2023 edition had been placed in the July 2022 edition. 2 of them duplicated
      Sackmann's own 2023 rows and are gone. The third, which Sackmann lacks, returns to 20 February 2023.
    * 8 matches of 2026 keep their players and box scores under a new key, because four players' ATP codes now
      resolve earlier.
  * **What Tennis My Life itself removed,** which Stage 0 was already dropping: four misfiled 2008 events in the 2024
    file (124 rows), and 15 duplicates.
  * **Reach:** 23 players. 15 training rows of the 2026 fit fall after a touched player's first change.
* **Not chosen:** holding live runs at the 8 October data (the daily-prediction session's recommendation of 11 October,
  made before the owner's answer). It keeps live inputs on the recipe the model was trained on. The cost: known errors
  stay in live inputs (a 20-year-old aged 58, the duplicates above). The mismatch it avoids is a few dozen old records.

## Implemented

* `src/eda/current_best_model/history.py`: the `tml_lower` class (`tml_levels`, `layered_ids`, `tml_own`). Tests:
  `test/current_best_model/test_history.py` (four new tests, two updated) and one test in `test_additions.py` updated.
* `src/eda/tml_revisions/held_check.py`: the check of rule 5.
* Accepted on 13 October, about 18:48 PDT: `tennis_my_life --start-year 2000 --accept-held` for
  `2022_challenger.csv@d95fa0a4bf8a`, `2023_challenger.csv@ee3a2128d89a`, `2024_challenger.csv@ca3a597f1a97` and
  `2025_challenger.csv@78b86009de42`. The staged tables equal the versions the check built B from (all but the
  retrieval time).
* The bet sheet (`src/pipeline/diagnostics.py`): no history note for Tennis My Life's own corrections, a note only
  for lower-level changes no decision covers, and the held files named in the download note. The notebook
  (`src/pipeline/data.py`): `held_tml_files()` no longer lists an accepted version, and `accept_held_tml()` points to
  the check. Tests: `test/master_pipeline/test_tml_notes.py`, `test/tml_revisions/test_held_check.py`.
* CLAUDE.md's freeze paragraph, and the master-pipeline and daily-prediction reports' open questions, now point here.

## To undo

* Remove the `tml_lower` split in `history.py`. The class's rows go back to `gated`, and template builds on the day's
  tables are refused again while Tennis My Life's lower-level history differs from the reference.
* The four files: the replaced copies are kept in `data/raw/public_dump/tennis_my_life/superseded/`
  (`2022_challenger.20260922210901.323699b8c67c.csv` and the three beside it). Put them back and restage them, and
  Stage 0 returns to build A.
