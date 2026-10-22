# The data issues P6 found: what is wrong, what was fixed

14 October 2026, updated 17 October · For the owner · Process log: [process_log.md](process_log.md) · Subagent briefs: [briefs.md](briefs.md)

**Status: a data-quality study.** It follows four issues raised by [work package P6](../gap_downloads/README.md#sofascore-by-edition-seven-more-gaps-work-package-p6), and reads no model result.
* **Fixed:** what is indisputable in data this project owns or describes (P6's links, the data map), and one source's misfiled week in the lower-level feed's reader (section 4 says why).
* **Collected:** the ATP's own point files for 2,360 of the matches SofaScore lacks (staged on 14 Oct), and Flashscore's point records for 3,479 targets (16 Oct; 502 of them also have the ATP's files). Both are on the data map (section 2).
* **Prepared and recommended:** changes to Stage 0's history. Under the frozen-reference rules they enter only as candidates or by the owner's decision.

**The request** (14 Oct 2026): "Find and fix these data gaps by either finding the data gap locally or on the web. Write up your discovery about this data. Clean up the data if its obvious and indisputable."

## In short

* **Borrowed links: fixed.** 47 links that took another player's match were refused. Each fails both tests: no surname matches, and the official result disagrees. Name changes (married names) are kept.
* **SofaScore's holes: two complete sources found on the web.** In all, 20,619 matches lack a SofaScore point record.
  * **The ATP's own Stats Centre** serves full point-by-point files for Challenger matches the project's copy of it lacks. 2,360 of the 20,619 are such matches, mostly the 2022-23 Challengers where SofaScore is thinnest.
    * All 2,360 are downloaded, with rally analysis for every one and MatchBeats (every point) for 2,256.
    * Their staged tables are on the data map since 14 Oct, kept out of the serve-speed history (your decision 2).
  * **Flashscore: fetched on 16 Oct.** Its copy listed a point-by-point record for 3,480 targets, mostly 2018-20 qualifying and 2020-23 Challengers.
    * A record came back for 3,479 of them, nearly all complete: 3,389 requests, no refusal.
    * 3,171 agree with the official result. 155 links had taken another match (players sharing the targets' first names, or the same pair's other meeting) and are kept off the map. 153 cannot be checked.
    * On the map, 3,268 targets now hold a complete Flashscore record of their own match, and 318 that had no point data now have some.
  * For most of the rest (the 13,000 Challengers of 2018-21), TennisLive's records, already on the map, hold about 90% of each match's games.
* **WTA website records: fixed where they reached the model.**
  * The copy's last week (editions of 7-14 Sep 2026) files all 187 of its matches under the wrong events. Nothing earlier is affected.
  * The lower-level feed, which the model's builds merge, held 41 of these matches only under a wrong event. 27 of them are ITF W50 matches filed as WTA 125s.
  * Both readers now leave those listings out, and the WTA's own records place the matches.
  * The feed's weekly run of 14 Oct advanced the corrected snapshot, which holds all 186 played matches once each, under their true events.
  * The feed now also alerts on new "player in two main draws of one week" flags (your decision 4).
* **Tennis My Life's dates: found, re-checked, prepared for your decision.**
  * 67 Challenger editions of 2018-25 are dated in another week.
  * Stage 0 mostly holds Sackmann's correct copy. The exception is 31 matches of the third Tenerife Challenger of 2024, dated a month early. That leaks their results into 136 later matches, 93 of them evaluation matches, in the frozen reference too.
  * Three independent reviewers agreed on the correction: the 31 rows move to 26 Feb 2024. You decided to apply it after a harm check.
    * **Done.** The harm check found no harm (both tours -0.001 [-0.004, +0.002] mLL, unresolved).
    * The live Stage 0 and timeline carry the true dates since 14 Oct, and the leak is closed (section 5).
  * Two Australian Open walkovers first thought misdated are duplicates instead, a smaller and harmless issue.
  * A weekly check of Tennis My Life's edition dates now runs on Wednesdays (your decision 3).
  * The data map held 1,586 matches twice for the same reason. **Fixed on 14 Oct by another session** (the P5 follow-up, at your word "Fix this if it isnt already fixed"); my report of that day still called it open (section 3's update).

## 1. Borrowed links: fixed

**The issue.** When SofaScore lacks a target's match, an event of one of its players whose opponent shares only a first name can take its place. For example, Musetti v Gigante (Forli 2022) is not on SofaScore, and Angelini v Arnaldi shares "Lorenzo" and "Matteo" with it. Such a link credits the wrong match with points.

**Why a surname rule alone would not do** [observed, 11 Oct; P6 report]. SofaScore shows a player's current name on old matches, so married and changed names share only a first name: Jaksic is now Jovic, Rueffer Papadakis, Bondarenko Volodko, Cias Juszczak. A surname rule refused about 150 correct links to stop about 30 wrong ones.

**The rule applied: refuse a link only when both tests fail** (`src/eda/p6_data_issues/borrowed_links.py`):
* *Surnames:* no target player shares a surname word with the SofaScore player on its side, in either orientation. SofaScore's surname is read from its slug against its name. The slug runs surname first ("barranco-cosano-javier", "moeller-elmer") and the name given names first ("Javier Barranco Cosano", "Elmer Møller"), so both spellings count. A word spelt within a letter or two also counts (Moeller and Møller, Azoides and Azoidis, Sin and Shin).
* *The official result:* Tennis My Life's or Sackmann's row of the target gives another winner, or the same winner with other games in a set.

A name change passes the second test, since its result agrees, so it is kept.

**What it found [observed]** over the ATP gap of 30 Sep and P6's seven gaps (52,094 links):
* 233 links have surnames that do not match. 151 of them agree with the official result: name changes and spellings, kept. 35 cannot be checked (no official row), kept.
* **47 fail both tests and were refused:** 26 in Challengers 2022-24, 21 in Challengers 2018-21. Each was read by hand: another player sharing only a first name, with another score. 20 of them had carried a point record, which no longer counts for the wrong match.
* *The first pass found 49;* reading them by hand showed 2 to be correct (Leong v San Hui Sin, whom SofaScore calls Sanhui Shin; Cepede Royg v Bondarenko, now Volodko). Both errors were in the tests, and both were fixed before the rule was applied:
  * the spelling tolerance now takes three-letter surnames;
  * the link check drops an unplayed 0-0 set on either side. SofaScore lists one after some finished matches (Miami 2018, Basel 2019, Sydney 2018), and official scores write one at a retirement between sets ("6-4 0-0 RET").

**Applied** (P6's own evidence, a descriptive layer):
* The refused links are in `data/studies/gap_downloads/sofascore_link_vetoes.csv`. The adapter (`sofascore_editions.list_and_link`) reads that file and leaves those targets unlinked, with the reason in `link_note`, in every later run and in the link check.
* Gaps 4 and 7 were re-linked offline (no request): Challengers 2022-24 now link 5,238 targets (points 1,922); Challengers 2018-21 22,327 (points 11,874).
* The link checks of all eight gaps were re-run with the 0-0 correction:

| Gap | Agrees | Score differs | Winner differs | No official row | Not linked |
|---|---:|---:|---:|---:|---:|
| `atp_points_2025` | 3,773 | 1 | 0 | 0 | 1 |
| `challenger_points_2025` | 14,573 | 13 | 1 | 2 | 67 |
| `wta125_points_2019_2026` | 300 | 0 | 0 | 12 | 65 |
| `tour_points_rest` | 1,089 | 2 | 0 | 19 | 104 |
| `challenger_points_2022_2024` | 4,764 | 12 | 7 | 435 | 543 |
| `atp_points_2018_2020` | 2,668 | 0 | 0 | 0 | 16 |
| `wta_2018_points` | 1,991 | 2 | 0 | 11 | 75 |
| `challenger_points_2018_2021` | 22,135 | 53 | 33 | 89 | 2,547 |

  (The rest of each gap: SofaScore lists no score or no winner.) The 41 links with another winner that remain pass the surname test. The 7 of gap 4, read by hand, are the right players with a result the two sources record differently [observed]:
  * a retirement credited to the other player (Wuxi and Dobrich 2024);
  * a different result outright (Santiago and Villa Maria 2022, Mexico City and Concepcion 2024);
  * at Nottingham 2022, a retirement after one set on SofaScore against a three-set win; Nottingham held two Challengers that June, so it may be the pair's other meeting [inference].

  Gap 7's 33 were not read [unknown]. Gap 4's "no official row" rose from 411 to 435: Tennis My Life's corrected 2022-25 Challenger files, accepted on 13 Oct, changed some rows the check keys on [inference].

## 2. SofaScore's holes: what fills them

**The holes are SofaScore's own [observed, P6].** SofaScore has almost no Challenger point records from spring 2022 to the end of 2023, few for qualifying at any level, and about half for 2018 Challengers. The ten careers' own SofaScore records show the same, so it is not the run. In all, 20,619 of P6's targets have no SofaScore point record.

**What each other source holds for them:**

| Source | What it holds for these matches | Status |
|---|---|---|
| **TennisLive** (P5's pages, on disk) | Nearly all of them, but usually without the set-closing games. Of the 13,000 Challengers of 2018-21: 11,543 lack only those games, 165 are complete, 614 fall short otherwise, 388 have no points, 279 no page. Of the 3,859 of 2022-24: 2,666 / 844 / 146 / 54 / 149. A median 90-92% of games have their points | Held; counts as "point" on the map |
| **Flashscore** (live site; ids in the copy on disk) | Complete point records. The copy lists the point-by-point tab for **3,480 of the targets**: ATP 2018-20 (mostly qualifying) 1,583; Challengers 2021 956, 2023 581, 2020 173; tour level 50; others few. The copy is men's only, with few Challenger records before 2020 | **Fetched 16 Oct** (below): a record for 3,479; on the map, wrong links left off |
| **The ATP Stats Centre** (Infosys, the ATP's own files) | **Complete point records for most of the 2022-24 Challengers SofaScore lacks.** The copy on disk holds about 30% of 2021-24 Challenger matches without their point files. The ATP's host now serves them: a probe asked for 26 and got all 26 (MatchBeats, every point with the serve's speed, and rally analysis), full-size files the host wrote in May-October 2026, after the copy was made. 2,253 of P6's 2022-24 Challenger targets and 107 of 2021 are such matches. The Hugging Face crawl found no Challenger file for 2015-19 | **Downloaded, staged and on the map** (14 Oct; section 5) |
| **SofaScore** | Its holes; nothing to add | — |

**The Flashscore fetch: done, 16 October 2026** (`src/ingest/point_sources/flashscore_p6.py`). It asked for the 3,389 Flashscore feeds of those 3,480 targets (some targets are the same match twice on the map), with work package P13's client and parser, into P13's raw folder and receipts. It waited until P13 had freed the host (one collector per host).
* **Requests [observed]:** 3,389, one per feed, at P13's pace (2 s plus up to 1 s): a seeded trial of 82 (21:05-21:09 UTC), then the run of 3,307 (21:20-23:39 UTC, 2 hours 19 minutes). No retry, error, refusal or challenge.
* **What came back, against the expectation [observed]:** I expected a record in about 95% of the feeds, from P13's rate.
  * A record came in 3,388 of the 3,389 feeds; the one empty feed belonged to a wrong link.
  * By target: 3,479 of 3,480 have a record; against the copy's own set score, 3,424 are complete, 36 short and 19 other. 486,895 points, staged beside P13's.
  * Flashscore still serves the 2018-20 records, which P13 had not measured.
* **The check against the official results [observed]** (`src/eda/gap_downloads/verify_flashscore.py --p6`; each target's Tennis My Life or Sackmann row):

  | Verdict | Targets |
  |---|---:|
  | Agrees: the same winner and the same games in every set | 3,171 |
  | The same winner, other games in a set | 84 |
  | Another winner | 71 |
  | No official row to check (the target came from API-Tennis's file, 149, or the Infosys copy, 4, which the check does not read) | 153 |
  | No record | 1 |

* **Wrong links, kept off the map [observed].** These targets were linked to Flashscore's records by shared name words, first names included, within 3 days before to 14 days after the target's date. Where the copy lacks a target's own match, another match can take its place.
  * **122 contradicted links share no surname with their target.** They took another match of players who share the targets' first names: Sarkissian v Mousley took Klahn v Zverev (Alexander, Bradley). Most are Challengers of 2018-21, where the copy holds few Challenger records.
  * **33 more share the surnames and are contradicted too. I read them all:**
    * about 20 are wrong links: the same pair's other meeting a week or two later, or another player of the same surname (Joao Sousa for Pedro Sousa twice, Evan King for Darian King). Flashscore writes a player as surname and initial ("King E."), so a surname test cannot tell them apart;
    * 6 are the right match with a short or odd record (a last set ending 5-4; one set only);
    * 7 are unclear.
  * **The rule applied: a link the official result contradicts is not placed on the map, 155 in all.** I had first declared P6's rule for SofaScore's links (refuse only when the surnames differ too: 122). I changed it after the trial, which found the King case. Its cost is about 6 right but incomplete records left off the map. Both rules' counts are kept in `link_check.csv.gz`.
  * The 25 links whose surnames differ but which agree, or cannot be checked, are all right: Flashscore writes some names in another form ("Sasikumar M." for Sasi Kumar Mukund, "Bu Y." for B. Yunchaokete).
  * **A bug in the check, found while reading them and fixed:** it read 9 records the wrong way round, 8 of them "O'Connell C.", whose apostrophe hid the surname. P13's check of 15 Oct uses the same step (recommendation 7).
* **On the data map [observed]**, rebuilt at 00:01 UTC on 17 Oct. Another session changed the map's linker at 22:12 UTC, so its build of that hour is the "before":

  | P6's 3,480 targets | Before | After |
  |---|---:|---:|
  | Found on the map by their key | 3,458 | 3,458 |
  | With point data | 3,138 | 3,456 |
  | With a complete Flashscore record of their own match | 0 | 3,268 |
  | … of which TennisLive's pages were there already | — | 2,991 |

  * Point data rose most in the ATP gap of 2018-20, mostly qualifying (1,429 to 1,582 of 1,583), and reached the tour-level matches of 2019-23 (0 to 49 of the 49 found).
  * **The gain is mostly completeness.** The map counts TennisLive's pages as "point" although they usually lack the set-closing games, so it cannot show that 2,991 matches now have every point where they had about 90%.
* **P13's records are unchanged by the restaging [observed]:** its per-target table, its 40,867 feeds' rows and its 3,682,438 points are identical before and after.
* **Not in the timing clock or Stage 0:** like P13's records, these reach only the map; the leak-proof clock and the model read none of them.

**Limits.**
* The 153 links without an official row are placed on their surnames alone. 144 pass the surname test, and the 9 that fail were read (the name formats above). One of them could still be the pair's other meeting.
* "Complete" compares the record with Flashscore's own set score; the official check compares the result, not every game.
* 20 records have a game whose listed scores skip a step, so that game lacks a point.
* No ace or double-fault codes: Flashscore's feed has none.

**Running it again** (a rerun asks for nothing already on disk):

```
./python.sh -m src.ingest.point_sources.flashscore_p6 --trial 100 --max-requests 150   # the seeded trial
./python.sh -m src.ingest.point_sources.flashscore_p6 --max-requests 4000              # the run
./python.sh -m src.ingest.point_sources.flashscore_points --stage-only                 # stages every feed on disk
./python.sh src/eda/gap_downloads/verify_flashscore.py --p6                            # the check; the refused links
./python.sh -m src.ingest.point_sources.flashscore_p6 --stage-only                     # marks them (no request)
./python.sh src/eda/data_map/build.py                                                  # the map
./python.sh src/eda/p6_data_issues/checks/flashscore_on_map.py                         # the before/after counts
```

**Files.** Raw (gitignored): P13's `data/raw/point_sources/flashscore_points/` (the feeds, receipts, and logs `_logs/p6_*`). Staged: `data/dump/points/flashscore_points/`, where `matches.parquet` and `points.parquet` now hold both packages, and `handoff_p6.parquet` describes P6's feeds. Evidence: `data/studies/p6_data_issues/flashscore/` (per target `fetch_matches.csv.gz` and `link_check.csv.gz`; the refused links `link_vetoes.csv`; `fetch_summary.json`, `runs.jsonl`, `map_before.json`, `map_after.json`).

**Beyond the copy [suggestion].** Flashscore lists Challengers well beyond the copy's ids; a fresh crawl of its Challenger pages (to get match ids) could reach most of the other 13,000 Challengers of 2018-21. Its coverage is unmeasured, and it is a package of its own, after P13.

**The ATP's own point files (found 14 Oct, being collected).** I had inferred from the copy that the ATP's host held no point file for these Challengers. That inference was wrong.
* **The probes** (`src/eda/p6_data_issues/infosys_probe.py`, 40 requests):
  * every match asked for that the copy holds without its point file was served: 20 of 20 on rally analysis across 2021-24, 6 of 6 on MatchBeats;
  * the files are full size, and the host's own timestamps show it wrote them in May-October 2026;
  * two were decrypted in memory, as the site's own page does: every game and point is there. Buenos Aires 2022, Heide v Lingua Lavallen: 183 points over two sets of 13 games, matching the official 7-6(7) 7-6(3). Each point carries the serve's speed and the stroke;
  * for whole Challenger events the copy lacks, 11 of 12 finals were absent under Stage 0's event id. The ATP's id may differ for those events [unresolved].
* **Matched to P6's targets** (two surnames, within 7 days): of the 3,859 Challenger matches of 2022-24 that SofaScore lacks, 2,225 are such matches, 379 already have a point file in the copy, and 1,255 are not in the copy.
  * Across all gaps, 382 targets already have a copy point file; 315 of them are the Sackmann copy of one of the map's doubles (section 3). Their Tennis My Life twin took the ATP's record, so they are phantom targets, not missing data.
* **The download** (`src/ingest/point_sources/infosys_challengers.py`) asks for both point files of the 2,360 targets (2,253 of 2022-24, 107 of 2021). It uses the existing ATP adapter's client, pacing, receipts and block stop. It runs while the ATP host is otherwise free (the daily speeds job uses it at 07:30).
* **Not done yet: decryption and staging.** The project's chain for these files (decrypt, stage, then the map's reader) also feeds the serve-speed backfill's tables. Challenger files must not enter those by accident, so staging them is a decided step (recommendation 5). The map's reader also needs a Challenger date, since it dates by the tour's calendar.

## 3. Tennis My Life's misdated editions

**What is wrong [observed: subagent B linked every Tennis My Life row of 2018-2026 to Sackmann's row, TennisLive's day and SofaScore's start, by the two players and identical set scores; its headline claims re-checked independently].**
* **67 men's Challenger editions of 2018-2025 (2,093 matches) are dated in another week.** By season: 2018 4, 2020 2, 2021 21, 2022 13, 2023 10, 2024 14, 2025 3.
  * 64 are dated early, by 7 to 309 days: Tennis My Life gives a later edition an earlier edition's date, and often its name.
  * **The six "Biella 1"s of 2021,** all dated 14 Feb: one is the real Biella 1. The other five are Biella 3 to 7, played from 8 Mar to 31 May. Tennis My Life seems to lack one edition and pass its date on [inference from the names].
  * Three are dated late: **Nottingham 2025** (dated 7 Jul, played 6-11 Jan), Manama 2025 (dated 24 Nov, played 10-15 Feb) and Targu Mures 2025 (8 days). Nottingham 2024 is dated in February but was played in June.
  * Where they belong: Sackmann's date for 66 of them, which the play days confirm; the play days alone for the 67th (Tenerife, below).
* **The 2021 Australian Open's men's qualifying** (110 matches) carries the main draw's date (8 Feb). It was played in Doha on 10-13 Jan.
* **A milder, separate pattern:** 649 Challenger editions of 2018-24 are dated by their final's day, 5-7 days late. It stops in 2025.
* **Found nowhere else:** not in Tennis My Life's women's files, not at the ATP tour level, and not in the 104 Challenger editions since June 2026 that could be checked.

**What reaches the model.**
* **Almost nothing, because Stage 0 takes Sackmann's copy.** Of the 3,991 matches in the misdated, lumped and dated-apart editions, 3,954 are Sackmann's rows with his date [observed]. The other 37 come from Tennis My Life alone; 4 of them take Sackmann's date for their event.
* **33 Tennis-My-Life-only matches carry the wrong date** [observed]:
  * **31 matches of the third Tenerife Challenger of 2024**, which Stage 0 holds as "Tenerife 1" on 21 Jan. Sackmann lacks that edition, and Stage 0 holds his first and second Tenerife Challengers separately (15 Jan and 19 Feb). All 31 are evaluation matches.
    * The real dates are 26 Feb - 3 Mar 2024, re-checked three ways:
      * TennisLive lists "ATP Tenerife 3 Challenger" from 25 Feb to 3 Mar, with Kukushkin d. Gigante 6-2 2-0 in the final on 3 Mar. That is Stage 0's final row, and the semi-final and quarter-final scores agree too.
      * SofaScore names the event the same.
      * The web gives the same: [Wikipedia, "2024 Tenerife Challenger III"](https://en.wikipedia.org/wiki/2024_Tenerife_Challenger_III) and [the ATP's report of the final](https://www.atptour.com/en/news/kukushkin-gigante-tenerife-challenger-2024-final).
  * 2 walkovers of the 2021 Australian Open qualifying, dated 8 Feb, the main draw's date.
    * Reviewer R1 found these are **duplicates, not misdates**, and I confirmed it: Stage 0 also holds both from Sackmann, as "Doha Aus Open Qualies" on 10 Jan.
    * 8 Feb is Stage 0's usual date for that qualifying, and the clock has a rule that already places these two rows in the right week.
    * Re-dating them would move that rule's window into December 2020 and create a leak. So the date fix is withdrawn. Dropping the Tennis My Life copies would be the fix: a small proposal of its own, with no effect on the model (walkovers carry no result).
* **This creates a leak** [observed; re-checked].
  * The leak-proof clock gives the 31 Tenerife matches windows that close on 28-31 Jan 2024, so their results count from about 1 Feb, a month before they were played.
  * 136 later matches of the same players read them early: they start between 29 Jan and 24 Feb 2024, and 93 of them are evaluation matches.
  * The players' own ratings take results in Stage 0's date order, so they too take these results a month early [inference from how Stage 0 orders matches].
  * The effect on any reading is far too small to see (93 matches of one season), but it is a leak, and the frozen reference carries it.

**What it does to the data map.** The map holds **1,586 matches twice** [observed]:
* 1,575 come from the misdating: a Tennis My Life copy at the wrong date, plus Sackmann's copy (1,548) or API-Tennis's (27). By season: 2018 118, 2020 30, 2021 589, 2022 265, 2023 203, 2024 309, 2025 61.
* 11 come from 2026's two-week events, which Tennis My Life dates match by match.
* **A cost of its own:** 1,843 of the gap downloads' targets are such misdated copies. Their own match was usually Sackmann's copy, so requests were spent on phantom targets.

**What was done.**
* **Stage 0: nothing applied.** Its Challenger history may take a correction from a source other than Tennis My Life's own files only as a candidate or by your decision, and a Stage 0 row correction also needs three independent reviewers in agreement (the rule of 8 Oct). Prepared:
  * **The three reviewers' verdict** (`data/studies/p6_data_issues/stage0_review/consensus.json`; their reports in [subagent_reports.md](subagent_reports.md)):
    * **Tenerife: confirmed unanimously.** All three named the same 31 rows, the same operation and the same value: the tournament date 21 Jan 2024 becomes 26 Feb 2024, the Monday of the week played.
    * Each checked it a different way: recomputed from the raw files; attacked (no duplicate, no clash in the new week, no other date fits Stage 0's convention); and against the ATP's own results page for the event ("Tenerife 3, 26 Feb - 3 Mar 2024", all 31 results equal).
    * Two of them ran the clock's own rules on a copy: after the fix every window holds its match's play day (31 of 31), against none today.
    * The current date is also impossible: on 21 Jan Gigante was playing a final in Thailand.
  * **The Australian Open walkovers: the date fix rejected unanimously.** They are duplicates (above).
  * **The correction table, ready to apply** (`stage0_review/proposed_row_corrections.csv`, the 8 Oct format): the 31 raw Tennis My Life rows, each guarded by its tournament, round and players. Its action, a date change, is one the correction mechanism does not have yet.
  * The edition-level date table for the other 66 editions (`tml_misdates/tml_edition_date_corrections.csv`). Stage 0 holds their Sackmann copies, so these matter only to the map and to future Tennis My Life-only editions.
* **Update, 16 Oct 2026: the map's doubles were fixed on 14 Oct, by another session** ([P5's follow-up](../gap_downloads/README.md#update-14-october-2026-each-misdated-match-held-once)).
  * **The rule:** before Tennis My Life's rows join the map, a row whose own match Sackmann's files (else TennisLive's listings) hold 10 days to a year away takes that date and event name (`repair_tml_dates`). 1,841 rows were moved.
  * **The downloads stay attached:** the placement also reads the keys of the copies merged into each match (`placement_index`).
  * **Its count:** all 1,575 doubles of this kind are gone.
  * **Re-checked on the map of 15 Oct** (`src/eda/p6_data_issues/checks/map_doubles_now.py`): no match of the 67 misdated editions is held twice. 375 rows of 11 editions keep Tennis My Life's date, 7-9 days off, each held once, linked to Sackmann's copy.
  * **Left:** 11 doubles of another kind, the last rounds of 2026's two-week events, which Tennis My Life dates by the day played.
  * My report of 14 Oct still called this open; the fix had landed hours earlier. The paragraph below is as first written.
* **The map: not re-dated in this study.** The map attaches each gap download to its match by tournament name, date and players. Re-dating the misdated copies would merge each with Sackmann's copy, but it would also detach the downloads keyed to the old name and date: 1,843 SofaScore targets (675 of them linked) and about 1,700 TennisLive pages. Done properly, every map match would also keep the keys of the copies merged into it. That is a change to the map's design, not a clean-up, so it is a recommendation below. The doubles inflate the map's Challenger counts by up to 3% in 2021; they never reach the model.

## 4. The WTA website records: the last week misfiled

**What is wrong [observed: subagent A; the key counts re-checked].**
* **The cause is the copy's last ten editions.** The copy is the Kaggle dataset of the WTA website's records, version 29 of 24 Sep 2026. Its last ten editions, starting 7-14 Sep 2026, file all of their 187 singles under the wrong editions:
  * only 49 of their 339 listings sit in the right edition, about what chance would give;
  * all 187 matches were played the week of 7 Sep, at five events: ITF W50 Guiyang (47) and W50 Evora (45), and the WTA 125s of Antalya (35), Montreux (35) and Barranquilla (25);
  * the copy holds no real result of the 13-14 Sep events (Guadalajara, Valencia, Caldas da Rainha, Ljubljana, Sao Paulo), though it files matches under them.
* **The 55 matches P6 flagged** were all W50 matches (Evora 28, Guiyang 27), filed under WTA 125 titles. Two examples: Wang d. Astakhova was Guiyang's first round, 7-6(5) 7-5, and Dodin d. Johnson was Evora's first round, 4-6 6-2 6-2.
* **Where the truth comes from:**
  * the WTA API's own records of each player's matches (work package P2(b)), which carry the WTA's tournament number, place all 187;
  * TennisLive agrees on the event, players and score for 185, and the WTA's live-scoring draws for 92 of the 95 WTA 125 matches;
  * every misfiled match has at least two sources agreeing.
* **Nowhere else.**
  * Before 7 Sep, all 53,951 of the copy's 2026 listings sit in the WTA API's edition.
  * From 2018 to August 2026, 270,246 of 270,262 matches sit in a single TennisLive event, edition by edition; the worst edition is 97%.
* **Probable cause** [inference]: the dataset's creator joined the newest, unfinished week wrongly.

**What reached the model** [observed; re-checked].
* **The lower-level feed's accepted snapshot of 13 Oct** holds all 186 played matches:
  * 143 once, correctly;
  * **41 only under a wrong event**: 27 of them W50 matches filed at WTA 125 level, and one held twice under two wrong events;
  * 2 twice, once right and once wrong;
  * 24 of the 44 wrong copies also carry clay instead of hard court.
* **Stage 0 holds none of them.** The feed's snapshot has been merged into every build and prediction run since it was accepted on the evening of 13 Oct.
* **Why the feed kept the wrong copies.** Its builder reads the copy's listings first. It adds a match from the WTA API's records only where the copy lacks that match *in the same edition*, so a misfiled listing hides the correct record.
  * A simulation of today's files shows the risk: the copy's and the WTA's versions of 176 of the matches would both reach the builder's later stages.
  * The feed runs by itself today, Wednesday, at noon. A match whose two copies lie a week apart (the 14 Sep editions) is not recognised as one match, so it can enter twice.

**What was done: fixed, in both loaders** (`WTA_SITE_MISFILED` in `src/eda/lower_level_evidence/candidate_stage0.py`, the feed's builder, and in `src/eda/data_map/measure.py`).
* **The fix:** the copy's listings of those ten editions are left out, and the WTA API's records supply the matches under their true events.
* **Nothing is lost.** The API holds all 187, and the copy held nothing true of the 13-14 Sep events.
* **The fix in practice.** On today's files, the feed's website source now holds each of the 186 played matches once, from the WTA's records, under its true event, and no misfiled listing is left. Tests cover both loaders and keep their two lists equal.
* **Why this was applied rather than only recommended.**
  * The feed changes the model's merged tables by itself today at noon, with or without this study.
  * Without the fix, it would carry the 41 wrong copies forward, and possibly add the correct ones beside them.
  * The fix only changes which of the feed's own two inputs supplies these matches. It adds no source and no level.
  * The feed's own checks and identity screen still gate the snapshot, and a failed check keeps the previous one.
  * It is undone by deleting the two lists. **This is a departure from this study's starting rule** (feed changes prepared, not applied); the process log records the reasoning.

**Checked end to end before the automatic run.** A full trial build of the feed's candidate, from today's files with the fix, was made in a scratch folder (its own name, so the noon run does not reuse it).
* **All 186 played matches are held once each, under their true event and level** (93 WTA 125, 92 ITF W50, and one retirement written "6-2 0-0 RET"). There are no wrong copies and no doubles. The accepted snapshot, read the same way, has 41 matches only under a wrong event and 3 twice.
* **The builder's de-duplication fires far less.** It discarded 108 matches as "the same pair at two events in one week" in the 13 Oct build, and 17 in the trial; "same pair, round and score within ten days" fell from 83 to 29. Most of those discards were the misfiled copies.
* **The feed's checks pass on the trial**:
  * the structure is sound;
  * no reference match is dropped or dated in the future;
  * the "player in two main draws of one week" flags fall from 60 to 35. Every flag of the misfiled week is gone, none is new, and the 35 that remain are older ITF and Futures events held under two names.

**The map, rebuilt on 14 Oct.** It holds no row under a misfiled title any more, and each of the 186 matches once. The three pairs found twice are real rematches the following week at another event: one in the WTA's own lists, two in the ITF's and TennisLive's records. Before the fix, the map held 86 wrong rows from this week: the 55 P6 flagged, and 31 more.

## 5. Your four decisions of 14 October: double-checked, then carried out

You approved four of the recommendations below and asked me to double-check that each is still a good idea before carrying it out. Recorded as a [decision](../../decisions/2026-10-14-p6-data-issues.md).

**The double-check.** All four hold. Two needed a change in how they are done:
* **The Tenerife correction must not use row numbers.**
  * The 8 October correction tables find each row by its file and row number, and stop the whole Stage 0 build when a guarded row no longer matches.
  * Tennis My Life rewrote this file on 13 October: none of its 5,936 rows kept its position. A row-numbered correction would have stopped every Stage 0 build at its next revision, bet-day runs included.
  * So the date correction names each match (file, tournament, round, both players) and the wrong date it replaces. If Tennis My Life fixes the date itself, the correction stops applying and the build says so.
* **"Their own tables" needs two more guards.** The existing ATP decrypt step decrypts every file in the shared download folder, and the serve-speed history reads its tables. Both it and its staging step now leave the Challenger files out.

**Carried out:**

| Decision | What was done | State |
|---|---|---|
| 1. Tenerife dates | **The mechanism:** `corrections.apply_date_corrections`, Stage 0's rule E9, and `history.py` counting the table's matches as decided repairs. **The dry run** on today's sources: exactly the 31 matches move to 26 Feb 2024; every other fact of every match is unchanged. **The harm check** (a candidate built through the chain from the frozen reference's tables, with only these dates changed): **no harm, adopted** (below). **In the live tables** since the coordinated rebuild of 14 Oct (stamp 2026-10-14T2119Z, equal byte for byte to the dry run). The timeline now finds an exact play day for all 31 matches, and `history.py` says the template may be built | **Done** |
| 2. ATP Challenger files on the map | 2,375 matches decrypted and staged into `data/dump/points/infosys_challengers/`: 394,010 MatchBeats points and 415,381 rally entries. The map's new source `infosys_challengers` links all 2,375 to matches it already holds (1,479 by ATP ids), adds none and leaves none unplaced. The ATP decrypt and stage steps leave these files out | **Done** |
| 3. Weekly Tennis My Life date check | `src/eda/tml_revisions/edition_dates.py`, the weekly task's new job `tml_dates` (Wednesdays, after coverage). Its first run finds the study's 67 editions and nothing new | **Done**; first scheduled run 21 Oct |
| 4. Feed alert on new two-draw flags | `src/eda/data_gaps_2026/two_draws.py` (it reproduces the 13 Oct snapshot's 28 flags exactly), called by the feed after its check step. The weekly task alerts on new flags and never blocks | **Done**; first scheduled run 21 Oct |

**The feed's run of today (14 Oct, 12:31)** built and advanced snapshot `20261014` with the website fix: all 186 September matches are held once, each under its true event.

**The Tenerife harm check** (`data/studies/current_best_model/2026-10-14_tenerife_dates/`; the rule declared in the decision before any reading: adopt unless worse by more than 0.10 mLL with the whole interval below 0, or an input moved in a way the change's dose does not explain):
* **A control before the long build:** the candidate's leak-proof features equal the reference's on all 203,041 matches before 21 Jan 2024, where the change cannot reach. After it, the 32 players' own matches move, by up to 4.9 SD in form profiles that no longer hold the Tenerife results early. Other matches move by less than a millionth of an SD.
* **The input check, read first:** 4 of the model's 58 inputs change.
  * The three Elo inputs, on about 10.7% of matches, by under 0.001 SD.
  * Sets in the last 14 days, on 2 matches.
  * None is flagged.
* **The scores** (both stages, 2020-2024, + = the candidate better):

  | Population | Candidate vs reference | P(better) | Reading |
  |---|---|---|---|
  | **Both tours (the declared primary)** | **-0.001 [-0.004, +0.002]** | **0.23** | **unresolved** |
  | Men | -0.002 [-0.007, +0.003] | 0.23 | unresolved |
  | Women | exactly 0 (untouched) | — | — |

  The comparison resolves ±0.003 here, since the two models' forecasts barely differ; for scale, both beat their calibrated close by 1.37. No harm, so **adopted**. A slightly lower score is the direction expected when a leak is removed: 93 evaluation matches had read results from the weeks after them.
* **Applying it took two attempts.**
  * The first rebuild stopped halfway on a latent bug in its id-mapping step, which fails when no match id changes. Its kept copies restored the live tables at once.
  * The bug was fixed, with a test, and the rerun completed.

## What was changed, and what was not

| Issue | Changed | Prepared, not applied | Why not applied |
|---|---|---|---|
| Borrowed links | 47 links refused in P6's evidence, the two gaps re-linked offline, the link checks re-run | — | — |
| SofaScore's holes | The ATP's point files of 2,360 matches downloaded, decrypted and staged in their own tables, and on the map (your decision 2). Flashscore's point records of 3,479 targets fetched, staged and on the map, the 155 links the official result contradicts left off (16 Oct, your request) | — | — |
| Tennis My Life's dates | The 31 Tenerife dates in Stage 0 and the timeline, after the harm check (your decision 1); a weekly date check (decision 3) | The 67-edition table, for the map | — |
| Tennis My Life's doubles on the map | Fixed on 14 Oct by another session (P5's follow-up: `repair_tml_dates`, `placement_index`) | — | — |
| WTA website's last week | The copy's ten misfiled editions left out of the feed's builder and of the map; the WTA API's records supply the matches | — | — |

Nothing was deleted. No raw file was edited: the corrections live in the readers. The accepted feed snapshot of 13 Oct is untouched; the next weekly run (today, 12:00) builds its successor with the fix.

## Recommendations (your decisions)

*Recommendations 1, 2, 3 and the first half of 5 were decided on 14 Oct and carried out the same day (section 5). Recommendation 4 was carried out the same day by another session (section 3's update of 16 Oct). The Flashscore fetch of 5 was run on 16 Oct at your request (section 2). The fresh Flashscore crawl of 5, 6 and the new 7 remain open.*

1. **Correct the 31 Tenerife dates in Stage 0.** This is a repair: it closes a leak in the frozen reference's 2024 evaluation season.
   * Route: add a date-correction action to Stage 0's correction tables (the 8 Oct mechanism has none yet). Then make a candidate build and run the comparison as a harm check.
   * The effect is far below what the comparison can resolve, so the harm check decides.
   * Not the 2 Australian Open walkovers: they are duplicates, not misdates (section 3). Dropping the Tennis My Life copies would be their fix, and it changes nothing the model reads.
2. **Check Tennis My Life's new Challenger editions every week.** Since June 2026 Tennis My Life is Stage 0's only Challenger source, so a misdated edition (as in 2025: Nottingham, Manama) would now enter with its wrong date and leak, with no Sackmann copy to rescue it. TennisLive's listing days, downloaded daily already, date every edition; an edition dated more than 7 days from its play days would be flagged before it reaches Stage 0. Optionally, report the misdated editions to Tennis My Life itself, whose own corrections enter by themselves (13 Oct decision); that is a public post, so it is your call.
3. **Make the feed's "player in two main draws in one week" check alert on new flags.**
   * It flagged the misfiled week (25 player-weeks), but it does not stop a snapshot.
   * Blocking on any flag would also block on the known older cases, three of them in the feed's own scope (W15 Luque 2026, which the copy lists twice). So the rule should be: a player-week flagged that the previous snapshot did not hold alerts, and blocks if you prefer.
4. **The map: re-date Tennis My Life's misdated copies with their old keys kept,** removing about 1,575 doubles and as many phantom gap targets.
5. **Bring the ATP's Challenger point files onto the map; run the Flashscore fetch after P13** (section 2). *Both done: the ATP files on 14 Oct, the Flashscore fetch on 16 Oct.*
   * The ATP files: decrypt and stage the downloaded files in their own tables, with a purpose of their own. Staging them into the existing ATP tables would put Challenger serve speeds in the tables behind the serve-speed backfill. Then give the map's reader a Challenger date.
   * Whether Challenger serve speeds should enter the speed history is a separate question, for the feature pool.
   * Then consider a fresh Flashscore Challenger crawl for the 13,000 Challengers of 2018-21 that only TennisLive's incomplete records cover. The Hugging Face crawl found no Challenger file on the ATP's host for 2015-19; 2020 is untested.
6. **Smaller:** read gap 7's 33 remaining links whose official winner differs; check the feed's player Darya Khamutsianskaya, held under two ids (subagent A's side finding).
7. **Rerun P13's Flashscore link check with the corrected player order** (`./python.sh src/eda/gap_downloads/verify_flashscore.py`; no request, minutes).
   * The check read 9 of P6's records the wrong way round before the fix (section 2), and P13's ITF check of 15 Oct used the same step. Some of its 3 "another winner" and 83 "other games" may be such misreadings.
   * P13 still places all 86 of its contradicted links on the map; P6's are now left off.
   * **My recommendation:** rerun it, read what stays contradicted, and leave those off the map too if most are wrong links, so one rule covers both packages. About 80 ITF matches out of 27,535 records are at stake, so nothing urgent.
