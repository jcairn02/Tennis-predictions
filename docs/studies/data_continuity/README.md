# Securing the box-score feed: preservation and consistency after Sackmann

6 October 2026 · Study and proposal. Three parts became decisions the same day, under the owner's delegation:
* [Tennis My Life file versions](../../decisions/2026-10-06-tml-file-versions.md), after review with an independent Opus agent;
* [Slam box scores](../../decisions/2026-10-06-slam-box-scores.md), likewise. It was applied at a Stage 0 rebuild that night;
* the [download cadence](../../decisions/2026-10-06-download-cadence.md).

Nothing else here selects a source, model, schedule or spend.

The owner asked for a solution for data preservation and consistency going forward. The prompt was suggestion 10 of the [market-anchoring study](../market_anchoring/README.md#7-suggestions): stay on Sackmann-format box scores but secure the feed, because Sackmann's results repositories have gone, Tennis My Life (TML) continues the format, and TML's field definitions and licence need checking.

There are two questions:

* **Preservation.** What could the project lose, as it nearly lost Sackmann's files, and what keeps it?
* **Consistency.** Do the sources that continue Sackmann's format count the same things the same way, so the box scores the model sees live match the ones it was trained on? TML matters most. Since the [match-clock decision](../../decisions/2026-10-05-match-timing.md), Stage 0 takes every new result from TML alone.

"Sackmann's definitions" here means his values on the same matches. His data dictionary names the nine counts ("number of serve points", "number of serve games") without saying, for instance, whether a tiebreak is a serve game. A source uses his definitions to the extent its counts equal his.

## In short

**Preservation**

* *Observed, 6 Oct 2026.* Sackmann's `tennis_atp`, `tennis_wta`, `tennis_slam_pointbypoint` and `tennis_pointbypoint` answer 404. The project's copy comes from a third-party mirror, a single commit of 25 June 2026.
* *Observed.* Software Heritage holds `tennis_atp`'s full history to its visit of 8 May 2026, `tennis_wta` to 3 January 2025 and the Slam point files to 14 November 2024. It had never archived the mirror, or three other GitHub sources the project uses. On the owner's permission, all four were archived on 6 Oct 2026 ([swh_save_requests.json](../../../data/studies/data_continuity/swh_save_requests.json)).
* *Observed.* 23.8 GB of raw downloads are on this PC.
  * The Hugging Face dump (16.8 GB) has a copy in cold storage.
  * So does the public data dump of 22 September: its zip in the same bucket still covers the 1.5 GB of its files that have not changed since.
  * **About 5.5 GB has no copy anywhere else.** An earlier version of this report said 6.9 GB; it had missed the second zip.
  * That includes folders that are now the only copy: the WTA API batches, TDI's pages for matches that have left its 92-day listing, and the Australian Open's 2026 match centre.
  * 0.97 GB under `data/raw/gap_sources/` is in no catalog entry.
* *Observed.* The TML adapter wrote each changed file over the old one. Since the project's copy of 22 September, TML has changed 8 of the files held. Seven only gained matches. In `2024.csv` a score was corrected: Shelton d. Shapovalov, Washington 2024, went from "RET" to "DEF". That brought TML into line with Sackmann, and Stage 0, which takes 2024 from Sackmann, was not affected. The exposure is the 4,863 Stage 0 matches from the week of 25 May on that only TML supplies: a correction there would reach Stage 0 with no record of the earlier value.

**Consistency**

* *Observed.* On the 167,600 matches that TML and Sackmann both hold with full box scores, all 18 counts are identical in 96.5%: 97.9% of men's matches and 89.4% of women's. Women's matches of 2010–2024 are identical in all but one of 24,016.
* *Observed.* Three defects, each settled by an official record:
  1. **Women's aces and double faults, December 2024 to February 2026.** TML's differ from Sackmann's in most rows. In 2025, 18% of double-fault counts and 57% of ace counts agree. The official records side with Sackmann: at Wimbledon 2025 the feed agrees with Sackmann's aces and double faults in every row, and with TML's in 44% and 27%. From March 2026 TML agrees again.
  2. **Wimbledon 2026 men, after the splice.** TML has first serves in on 68.9% of serve points. The official feed has 62.9%, in line with every earlier year (62.5–63.8%, where Sackmann matched the feed exactly). Stage 0 took these TML rows until the rebuild of 6 Oct, which replaced their counts with the feed's.
  3. **Men's service games at the Slams.** TML agrees with the Wimbledon feed in 75–92% of player rows in 2019–2024, and with the US Open's in 94% in 2022–23. Sackmann agrees in 99–100%.
* *Observed.* **TML's men's Slam first serves have been wrong since about August 2025.** Stage 0 hid most of it by preferring Sackmann's rows. TML's first serves in, against Sackmann's or the official feed's:

  | Slam | TML | Sackmann or feed |
  |---|---:|---:|
  | US Open 2025 main draw | 62.2% | 58.8% |
  | Australian Open 2026 main draw | 66.7% | 63.3% |
  | Australian Open 2026 qualifying | 68.8% | 63.1% |
  | Wimbledon 2026 main draw | 67.7% | 63.8% |
  | Wimbledon 2026 qualifying | 70.9% | 61.6% |

  At the US Open 2026, ten final-round qualifying rows have the same fault.
  * The extra "first serves" were won at second-serve rates (51.7% in Wimbledon's qualifying, against 50.8% on second serves and 73.1% on first), so they are second serves recorded as first.
  * Two Wimbledon 2026 matches also have a wrong deciding-set score in TML.
  * *Inferred:* every future Slam that only TML supplies will likely carry this fault.
* *Observed.* **Sackmann's own Roland Garros men's qualifying of 2022–2025 has the same fault:** 65.2–68.6% first serves in where TML has 61.2–63.3%. It is in the training data, and it is flagged, not changed.
* *Observed.* Elsewhere after the splice, TML agrees with the official record:
  * **ATP tour and Challenger:** 99.8% of player rows against TDI, on every count TDI publishes (2,609 matches).
  * **WTA tour, against the WTA API** (844 matches): 99.9% on aces, double faults and break points; 95.5% on first serves in; 83.7% on service games.
  * **US Open 2026:** 97–100%.
* *Observed.* **SofaScore does not use Sackmann's definitions for two counts.**
  * Its first serves in run 0.4–0.7 per player higher, and agree exactly in only 46–61% of ATP rows in 2025–2026.
  * In 2026 it records fewer break points faced in half the rows; TDI sides with Sackmann.
  * Aces, double faults and service games agree in 99–100% of 2026 rows.
* *Observed.* **The splice loses draws.** After the splice, Stage 0 has:
  * no women's qualifying (0 matches, against 534 in June–September 2025);
  * 13% of the WTA 125 matches, and 6% of women's ITF;
  * 8% of men's Challenger qualifying, and 5% of men's ITF.

  TML publishes none of these draws. The WTA API held here has box scores for 1,118 WTA 125 matches and 336 tour-qualifying matches played since June. The Slam feeds have women's Slam qualifying.
* *Observed.* **The splice splits identities.** 86 players carry TML's ATP codes after the splice instead of the ids they had before. 72 of them have earlier matches under a Sackmann id with the same name, so 127 post-splice matches start without history. An exact name and birth date resolves 41.
* *Inferred.* Sackmann's format does not guarantee Sackmann's definitions, and a source that matched once can drift: TML's women's counts went wrong for 15 months and then came right. A one-off check is not enough. Every refresh should be checked count by count against an independent record.

**Proposal** ([section 4](#4-proposed-solution)): eight measures, cheapest first. Built so far:
* every TML version kept, with a gate that stops a damaged file from replacing a good one (decided). TML has been downloaded every day since 6 Oct by a Windows scheduled task, which notifies only when something needs a person;
* a weekly check of the upstream sources, run every Monday by the same task;
* the Slam box-score overrides for Wimbledon and the US Open 2026 (decided). They were applied at the coordinated Stage 0 rebuild of 6 Oct, and every later build applies them.

The rest are designed, each with the check that would show it working. [Section 5](#5-decisions-for-the-owner) lists what still needs the owner.

## 1. What securing the feed has to cover

| Failure | Seen in this repository | Guard |
|---|---|---|
| Loss: the source disappears | Sackmann's results repositories, gone by 22 June 2026 | Copies off this PC; external archives; a watch on every upstream |
| Rewrite: the source changes what it published | TML's 2024 score correction; Polymarket's records; TDI's 92-day listing | Never overwrite: keep every version received |
| Drift: the same source changes how it counts | TML's women's aces and double faults, Dec 2024 – Feb 2026; TML's Wimbledon 2026 first serves | Count-by-count checks against an independent record at every refresh |
| Splice: a change of source changes definitions, coverage or identities | Stage 0 after 25 May 2026: lost draws, 72 split players, Wimbledon 2026 | The same checks across the switch; source precedence per count; an identity crosswalk |
| Terms: the right to use the data is unclear or changes | TML: MIT on its site, non-commercial in its README | Record the terms at every check; ask the publisher |

The live model needs a box score for every match, published before each player's next match, counted the way the training data counted it, under terms that allow the use (market-anchoring suggestion 10).

## 2. Preservation

### 2.1 Upstream sources, 6 October 2026

`canary.py` (section 4.3) recorded this baseline:

| Source | Answer | Last change | Software Heritage, last full visit |
|---|---|---|---|
| Sackmann `tennis_atp` | 404 | — | 8 May 2026 (visits since then: not found) |
| Sackmann `tennis_wta` | 404 | — | 3 Jan 2025 |
| Sackmann `tennis_slam_pointbypoint` | 404 | — | 14 Nov 2024 |
| Sackmann `tennis_MatchChartingProject` | 200 | pushed 18 Sep 2026 | 26 Sep 2026 |
| Aneeshers `tennis-sackmann-archive`, the project's source for Sackmann | 200 | pushed 25 Jun 2026; GitHub does not recognise its licence file | never; saved on request 6 Oct 2026 |
| Tennismylife `TML-Database` on GitHub | 200 | pushed 27 Jan 2026 | 21 Feb 2026 |
| Tennis My Life manifest (`stats.tennismylife.org/api/data-files`) | 200, 207 files | newest file 6 Oct 2026, 14:00 UTC | not applicable (an API) |
| SirGenkii `infotennis` | 200 | pushed 11 Apr 2025 | never; saved on request 6 Oct 2026 |
| hawkilol `tennisSlamBallTracking` | 200 | pushed 8 Apr 2025 | never; saved on request 6 Oct 2026 |
| ryantjx `tennis-match-data` (Open Tennis Data) | 200 | pushed 4 Oct 2026 | never; saved on request 6 Oct 2026 (the repository only: its data releases are release assets, which Software Heritage does not keep) |
| Hugging Face `atlas-polybot/atp-pipeline-handoff` | 200 | 19 Jun 2026, commit `ea3d94d`, the one pinned | (zip in the project's cold storage) |

* *Inferred.* Software Heritage is a recovery route for Sackmann's history, not for his last files. It has `tennis_atp` with every commit to 8 May, but not the weeks to the end of May that the mirror holds. It is also the only place the revision history of his files survives; the mirror is one flat commit.
* *Observed.* TML's GitHub repository has not changed since January. The live data comes only from the site's API, which no archive captures. The project's own copies are TML's archive.

### 2.2 What is on this PC

`inventory.py` writes [preservation_register.csv](../../../data/studies/data_continuity/preservation_register.csv).

* **Size.** 23.77 GB in 47 raw folders and loose files (6 Oct, after that day's downloads).
  * The Hugging Face dump, `atp_pipeline_handoff` (16.80 GB), has the cold-storage zip of 25 Sep 2026.
  * The bucket also holds `tennis_public_dump_raw_2026-09-22.zip`: 451 MB, a copy of `data/raw/public_dump/` without the Hugging Face folder, made on 23 Sep. It covers a file only if the file has not changed since, which is 1.47 GB of today's files, counted file by file.
  * **5.49 GB has no copy outside the working tree.** The first version of this register missed the second zip and said 6.94 GB.
* **The largest folders without a copy:**
  * Polymarket trades (2.0 GB) and catalog (0.8 GB);
  * the Sackmann mirror copy (0.56 GB);
  * the WTA API (0.56 GB, 140,896 files);
  * the Match Charting files (0.45 GB);
  * TDI (0.27 GB);
  * TennisLive (0.20 GB), the three Slam feeds (0.21 GB) and SofaScore (0.14 GB).
* **Catalogue gaps.**
  * 12 items have no receipts file: six under `gap_sources/`, the inherited June 2026 snapshots, and Sackmann's old point-string copies.
  * 12 folders and 2 loose files under `gap_sources/` (0.97 GB) are claimed by no data-map entry, so they carry no rights or backup record.
  * This study's own folder is added to the catalog.

### 2.3 Files that change after publication

TML's manifest gives every file's modification time. `tml_revisions.py` downloaded the 8 files changed since the project's copy of 22 September into `data/raw/data_continuity/tennis_my_life/2026-10-06/`, beside that copy. It then compared the two copies row by row ([tml_revisions_files.csv](../../../data/studies/data_continuity/tml_revisions_files.csv)):

| File | Rows, 22 Sep → 6 Oct | Added | Removed | Corrected |
|---|---|---:|---:|---:|
| `2024.csv` | 3,076 → 3,076 | 0 | 0 | 1 (a score) |
| `2026.csv` | 2,259 → 2,419 | 160 | 0 | 0 |
| `2026_challenger.csv` | 5,790 → 6,131 | 341 | 0 | 0 |
| `2026_wta.csv` | 2,153 → 2,224 | 71 | 0 | 0 |
| `atp_quali/2026_atp_quali.csv` | 1,105 → 1,177 | 72 | 0 | 0 |
| The three ongoing-tournament files | 188 → 174 | 174 | 188 | 0 (rows move to the season files) |

* **New line endings.** `2024.csv` was also re-exported with Unix line endings, so its bytes and SHA-256 changed on every line though only one cell did. A change detector must compare rows, not hashes.
* **The corrected cell.** Washington 2024 QF went from "7-6(5) 6-6 RET" to "7-6(5) 6-6 DEF", changing the match from retired to defaulted. Sackmann's row already read "DEF", and Stage 0 takes 2024 from Sackmann, so Stage 0 was not affected. Had the row been TML-only, the change would have mattered: Stage 0 maps a default to "other", which moves no rating, is not counted as played, and leaves the model's population.
* **Publication delay.** *Observed.* The ongoing files carry full box scores, dated by the day played, up to the day of the download. TML's delay is therefore about a day, not a week. Those files are rewritten continuously, so only a kept copy shows when a box score first appeared.

## 3. Consistency

### 3.1 TML against Sackmann on the same matches

`tml_vs_sackmann.py` runs Stage 0's own loading and linking in memory; no Stage 0 output is written. It compares the nine counts of every player in the 190,866 TML rows linked to a Sackmann row:

* 22 pairs name the winners the other way round and are compared player to player.
* 9 pairs whose players could not be matched are dropped.

| | Men | Women |
|---|---:|---:|
| Pairs with full box scores in both | 140,085 | 27,515 |
| All 18 counts identical | 97.9% | 89.4% |

Exact agreement per count, all seasons ([tml_vs_sackmann_fields.csv](../../../data/studies/data_continuity/tml_vs_sackmann_fields.csv)):

| Count | Men | Women |
|---|---:|---:|
| Aces | 99.8% | 96.6% |
| Double faults | 99.8% | 93.6% |
| Serve points | 99.7% | 99.5% |
| First serves in | 99.4% | 99.5% |
| First-serve points won | 99.4% | 99.5% |
| Second-serve points won | 99.4% | 99.5% |
| Service games | 98.6% | 99.6% |
| Break points saved | 99.7% | 99.5% |
| Break points faced | 99.7% | 99.5% |

By season ([tml_vs_sackmann_matches.csv](../../../data/studies/data_continuity/tml_vs_sackmann_matches.csv)):

* **Women.** Identical every season 2010–2024 (one match in 24,016 differs), then 6.0% in 2025 and 44% in 2026 to May. The break is in aces and double faults (section 3.2).
  * *By month:* 3–29% of player rows agree on both counts from December 2024 to February 2026, and 93–100% from March 2026.
  * *Not a swap:* only 5% of rows have the two columns exchanged. The numbers are simply different.
* **Men.**
  * 99.5–99.97% identical in 2010–2016;
  * 94.5–95.9% in 2017–2019, from service games;
  * 97.4–98.2% in 2020–2024;
  * 96.8% in 2025;
  * 94.2% in 2026 to May, where first serves in agree in 96.2% and service games in 95.1%.

### 3.2 Official records as referees

A referee is a source compiled apart from both TML and Sackmann:

* **The WTA API:** box scores of every WTA match, 2019–2026.
* **TDI**, the ATP's data company: ATP tour and Challenger matches, mostly June–September 2026, plus 634 older matches.
* **The Wimbledon and US Open feeds.**
* **SofaScore.**

`referees.py` joins each to Stage 0 through the match-timing link files, keeps links whose score agrees with Stage 0's, and matches players by who won.

The WTA API records break points on the returner's side. Read that way, it agrees with Sackmann's break points faced in 94.6% of rows; read the other way, in 6.3%.

**Where TML and Sackmann differ, the referees side with Sackmann.** Exact agreement with the referee, before the splice, on the same players:

| Referee, women | Aces: Sackmann / TML | Double faults: Sackmann / TML |
|---|---|---|
| WTA API, 2025 | 83.8% / 48.2% | 81.3% / 17.4% |
| WTA API, 2026 to May | 99.7% / 81.6% | 99.6% / 63.3% |
| Wimbledon, 2025 | 100% / 43.9% | 100% / 26.8% |
| US Open, 2025 | 100% / 57.3% | 100% / 12.2% |

| Referee, men | Service games: Sackmann / TML |
|---|---|
| Wimbledon 2019, 2021–2024 | 100% / 75–92% |
| US Open 2022–2023 | 98.8–99.7% / 94.0–94.1% |

**After the splice**, Stage 0's counts are TML's. Exact agreement with each referee, 2026 ([referee_vs_stage0.csv](../../../data/studies/data_continuity/referee_vs_stage0.csv)):

| Referee | Player rows | Aces | Double faults | Serve points | First serves in | Service games | Break points faced |
|---|---:|---:|---:|---:|---:|---:|---:|
| TDI, ATP tour and Challenger | 5,218 | 99.8% | 99.8% | 99.8% | not published | 99.8% | 99.8% |
| WTA API, WTA tour | 1,688 | 99.9% | 99.9% | 99.3% | 95.5% | 83.7% | 99.9% |
| US Open, men | 476 | 100% | 99.6% | 100% | 97.3% | 97.3% | 100% |
| US Open, women | 254 | 100% | 100% | 100% | 100% | 100% | 100% |
| Wimbledon, men | 472 | 88.3% | 92.6% | 62.7% | 21.0% | 85.7% | 98.3% |
| Wimbledon, women | 254 | 99.6% | 100% | 99.6% | 79.9% | — | 100% |

**Pooled first serves in, as a share of serve points** ([referee_rates.csv](../../../data/studies/data_continuity/referee_rates.csv)):

* At Wimbledon, Stage 0 and the feed agree to 0.01 points for men in every year 2019–2025 (62.5–63.8%).
* In 2026, TML has 68.9% and the feed 62.9%.
* TML's serve points and serve points won are within 0.4 of the feed's on average, so TML has moved about six points per player from the second serve to the first.

*Inferred.* Every man who played Wimbledon 2026 now carries, for that event, a first-serve-in rate six points too high in Stage 0.

**Referees are not ground truth.**

* *Short records.* The WTA API's 2024–2025 records are short for a subset of matches: where they differ, the API has 7–12 fewer serve points per player on average. So Sackmann agrees with it in 99.4–99.9% of rows in 2019–2020 and 2023, but in only 83–92% in 2024–2025.
* *A different count at the Slams.* The API's Slam box scores (batch B9) put first serves in 2–3 points higher than both Sackmann and the Slams' own feeds.
* *Its own service games.* In 2026 its service games differ from Sackmann's in 9% of rows.

A referee is trusted for a count where it has matched Sackmann's history.

### 3.3 SofaScore

Exact agreement with Stage 0, ATP, which holds Sackmann's counts before the splice:

| Year | Player rows | Aces | Double faults | First serves in | Service games | Break points faced |
|---|---:|---:|---:|---:|---:|---:|
| 2024 | 1,074 | 98.4% | 97.5% | 82.9% | 96.4% | 98.5% |
| 2025 | 6,036 | 79.9% | 81.2% | 45.9% | 98.8% | 69.9% |
| 2026, to May | 2,938 | 99.7% | 99.9% | 60.5% | 99.4% | 49.6% |

* **First serves in.** SofaScore is higher by 0.4–0.7 per player on average, mostly by 1–3, while serve points mostly agree. Pooled, that is 0.5–1.3 points of first-serve-in rate.
* **Break points faced.** Equal in 2024. Then SofaScore counts fewer: in 2026, 1–3 fewer in half the rows. TDI agrees with Sackmann and TML in 99.6–100% of rows, so the change is SofaScore's.
* **2025.** Worse on every count. Most of the year's records here come from the by-tournament download of 30 September 2026, and 6% of them contradict themselves: their first-serve denominator is not their own count of first serves in.
* *Inferred.* SofaScore can stand in for aces, double faults and service games, and for serve points with care. It cannot stand in for first serves in or break points without a calibration, and features built on those would shift.

### 3.4 Coverage across the splice

[coverage_splice.csv](../../../data/studies/data_continuity/coverage_splice.csv) compares Stage 0's matches from tournament weeks of 1 June – 28 September 2026 with the same weeks of 2025.

| Draw | 2025 | 2026 | Kept | Held source with box scores after June 2026 |
|---|---:|---:|---:|---|
| Men, Challenger main | 2,421 | 2,621 | 108% | TML; TDI for 2,049 of them |
| Men, Challenger qualifying | 1,342 | 102 | 8% | TDI lists Challenger qualifying from late June (not checked here) |
| Men, ITF | 7,809 | 393 | 5% | None |
| Women, tour and Slam qualifying | 534 | 0 | 0% | WTA API (336 tour-qualifying matches since 1 June); Wimbledon and US Open feeds (224 Slam qualifying matches) |
| Women, WTA 125 main and qualifying | 845 | 111 | 13% | WTA API (875 main and 243 qualifying matches since 1 June) |
| Women, ITF | 7,468 | 427 | 6% | None |
| Tour-level and Slam main draws, both tours | | | 54–136% by level | TML; TDI; WTA API; Slam feeds |

The main-draw range reflects calendar shifts, and the TML copy ending with the week of 21 September; it does not mean matches are missing.

The lost draws are those where the [Polymarket study](../polymarket_sharp_money/README.md) found the largest share of accounts beating the close, and where market-anchoring suggestion 6 needs dated history.

### 3.5 Identity across the splice

[identity_splits.csv](../../../data/studies/data_continuity/identity_splits.csv): of 9,726 player rows after the splice, 145 carry a TML ATP code.

* **Why.** Stage 0's crosswalk learns a code only from matches that TML and Sackmann both hold. These 86 players' earlier matches are in files TML does not publish: Futures and ITF.
* **Split histories.** 72 of the 86 share an exact name with an earlier Sackmann id. Their 127 matches start from no history.
* **Repair.** An exact name and birth date, matched between TML's player table and Sackmann's, resolves 41 of them. TML's table as held lists 51 of the 86 and gives a real birth date for 44.

### 3.6 What can stand in for what

| Count | TML after the splice | TDI | WTA API | Slam feeds | SofaScore |
|---|---|---|---|---|---|
| Aces, double faults | Agrees; wrong for women Dec 2024 – Feb 2026 | Agrees (men) | Agrees (women) | Agrees | Agrees in 2026; poor in 2025 |
| Serve points | Agrees, except Wimbledon 2026 men | Agrees (derived) | Agrees, except short 2024–25 records | Agrees | Mostly |
| First serves in; first- and second-serve points won | Agrees, except Wimbledon 2026 men | Not published at match level | Agrees at tour level; its Slam box scores differ | Agrees | Differs (+0.4–0.7 first serves in) |
| Service games | Men: 97–100% against TDI and the US Open, 86% at Wimbledon. Women: 84% against the WTA API | Agrees | Its own count (9% of 2026 rows differ from Sackmann) | Agrees | Agrees |
| Break points | Agrees | Agrees | Agrees (returner side) | Agrees | Differs from 2025 |

"Agrees" means 97% exact agreement or better against Sackmann or the referees in sections 3.1–3.3.

## 4. Proposed solution

Eight measures. Each says what it is, why it is needed, whether it is built, and the check that would show it working.

The UFC project's lessons point the same way. ESPN deleted the statistics of fighters who left the UFC, and a live re-scrape could not get them back; only a snapshot taken before the scrape could. Its "time-travel" parity tests rebuild features as of a cut-off and require them to equal the training rows; check 4.7 borrows the idea.

### 4.1 Keep every version received, and never let a damaged one become current (built for TML; decided)

Decided on 6 Oct 2026 under the owner's delegation, after review with an independent Opus agent: [the decision](../../decisions/2026-10-06-tml-file-versions.md).

* **Keep.** A download that brings different bytes first keeps the replaced file under `<source>/superseded/`, with a `.meta.json` holding its first and last receipts (`common.keep_replaced`, used by `download(keep_superseded=True)`).
  * The kept copy is named by the first time those bytes were seen, so a version that comes back after another one (A, B, A) is kept once.
  * It generalises what `tennis_data_couk.py` already did for workbooks. The TML adapter does it for every file it fetches, and `--no-keep-superseded` turns it off.
* **Gate.** `download(gate=...)` can refuse to make a valid download current.
  * The new bytes go to `<source>/held/`. Their receipt is recorded under `held/<name>`, so the latest receipt under the file's own name still describes the current copy.
  * **TML's season files are held** when the last record is cut short, when the file is not the size the manifest lists, when a column is lost, or when more than 5 rows, or more than half the rows, of the current copy are gone. Rows are compared whole, not as bytes, and corrections are paired with the rows they correct: first by match identity, then by tournament, round and names.
  * **Ongoing files are held** only when cut short or missing a column.
  * A held file stops the run with an error. `--accept-held NAME@SHA12` lets that exact version through after review.
  * Accepted revisions of season files are logged, with their changed cells, in `_changes.jsonl`.
* **Also.**
  * Downloads, kept copies and metadata are written whole, then renamed.
  * A lock allows one TML run at a time.
  * The adapter's default end year is next year, so a season file published in late December is not skipped. `run_all.py` still passes 2026.
  * Each Stage 0 build records the SHA-256 of every file it reads.
* **Why.**
  * TML revises files in place, and since the splice Stage 0 takes every new result from TML. Without the replaced bytes no earlier training set can be rebuilt.
  * TML's manifest caught one of its own files half-written: it listed 12,873 bytes for an ongoing file whose download held 13,077, ending inside a row. Until now the only check was that the header named `tourney_id`.
* **Replays.**
  * *22 Sep → 6 Oct versions:* the gate accepts `2024.csv` with its one corrected cell logged, the 2026 season files with only appended rows, and the ongoing files' turnover. It holds a header-only file and a half-written one.
  * *TML's pre-audit backup of 6 September* (31 files, now kept in `data/raw/data_continuity/tennis_my_life/`): against the 22 September copies, the audit corrected 2–28 rows per season and removed none. The rows were mostly entry codes (lucky losers), plus a few box scores in 2016 and 2025. The gate accepts all of them ([tml_audit_backup.csv](../../../data/studies/data_continuity/tml_audit_backup.csv)).
* **Next.** For the other re-fetched listings (the WTA API's and SofaScore's match lists for unfinished editions, TDI's listing pages), a gzipped store keyed by content hash suits better, since those folders hold 6,000–141,000 files. The Polymarket catalog already keeps one page folder per run.
* **Cost.** A few megabytes per run, under a gigabyte a year at one run a day.
* **Check.**
  * 14 new offline tests in `test/public_data_dump/` (`test_keep_superseded.py`, `test_tml_gate.py`).
  * The next live TML run logs each kept file, and the 22 September copies appear under `superseded/`.

### 4.2 Copies off this PC (designed; needs the owner)

* **What.**
  * A monthly copy of `data/raw/`, except the zipped Hugging Face folder, to the existing bucket `gs://tennis-predictions-archive/`. Use dated archives like the September zip, with a SHA-256 manifest built from the receipts.
  * A restore drill each time: fetch one archive back and check it against the manifest.
  * **Done on 6 Oct 2026, on the owner's permission:** Software Heritage "Save Code Now" requests for the four GitHub sources it had never archived: the Sackmann mirror, SirGenkii/infotennis, hawkilol/tennisSlamBallTracking and ryantjx/tennis-match-data. All four succeeded within minutes, with full snapshots; their ids are in [swh_save_requests.json](../../../data/studies/data_continuity/swh_save_requests.json). `TML-Database` needed no new visit: Software Heritage's visit of 21 February postdates its last push.
  * Catalog entries, with rights and backup notes, for the 12 unmapped `gap_sources` folders and their 2 loose files.
* **Size.** About 5.5 GB once: everything downloaded so far that has no copy off this PC. After that, each monthly copy adds only what is new. Measured from the receipts of the last refresh runs (the size each wrote to disk):
  * the Polymarket catalog re-downloads every listed event: about 430 MB a run (5 Oct);
  * Polymarket trades about 110 MB and prices about 30 MB per two weeks (5 Oct);
  * TDI's weekly top-up about 12 MB (29 Sep);
  * the WTA API, TML and tennis-data.co.uk a few MB each.

  That is roughly 0.5–1 GB a month at the current pace, two-thirds of it Polymarket. Stored as monthly zip files like the September one, a few dozen gigabytes cost well under a dollar a month even at standard storage rates; check against the bucket's billing.
* **Check.** The register shows every folder with an off-machine copy or a reason it needs none, and the drill's hashes match.

### 4.3 Watch the sources (built: `canary.py`)

* **What.** A weekly run of about 25 requests, to open endpoints only: GitHub, Hugging Face, TML and Software Heritage. No data is downloaded. Each run appends to `canary.jsonl` and raises these flags:
  * GONE: the address no longer answers;
  * STALE: nothing new for longer than the item's allowed gap;
  * SHRANK: a manifest or file got smaller;
  * REVISED: a file of an earlier season changed;
  * TERMS: the licence statement changed;
  * UNARCHIVED: no recent Software Heritage snapshot.
* **Baseline, 6 Oct 2026.**
  * GONE: Sackmann's three results repositories.
  * Last archived in 2025 and 2024: `tennis_wta` and the Slam point files.
  * Never archived: the mirror, SirGenkii and hawkilol (all three saved on request later that day; see 4.2).
  * Last archived in February 2026: TML's GitHub.
  * Every other item answered with no flag.
* **Check.** Run it before every TML refresh. A REVISED or TERMS flag means reading the diff (`tml_revisions.py`) before rebuilding.

### 4.4 A box-score contract, checked at every refresh (designed; the checks exist as this study's scripts)

* **The contract.** The nine counts and their row checks (Stage 0's B0–B9), with the measured definitions of section 3 as the baseline: for each source and count, how well it agreed with Sackmann.
* **After each TML refresh, event by event:**
  1. Row checks, as now.
  2. Agreement with a referee, wherever one covers the event: TDI for the ATP tour and Challengers, the WTA API for the WTA tour, the Slam feeds for the Slams. Flag an event when exact agreement on any count falls below 97%; the baselines are 99.8% for TDI and 99.9% for the WTA API.
  3. Rate drift: each event's pooled rates against the referee's and against the same event's earlier years. Flag first serves in beyond ±1.5 points, and aces or double faults beyond ±0.5. Wimbledon 2026 men was +6.0.
  4. Events no referee covers (most Challengers before late June, and all ITF): rate drift against the event's own history only.
  5. **Tests that need no referee.** These come from the Wimbledon review:
     * *the moved-point test:* where two sources differ, the extra first serves of one of them must be won at a first-serve rate, not a second-serve rate;
     * each event's shift against the same players' own history;
     * rows with first serves in above 85%;
     * thresholds by draw and round, not only by tournament. The US Open 2026's fault sat in one qualifying round.
* **Where.** A `conform.py`, run by `match_timing/refresh.py` after `stage0_build.py`, writing a report per event. `referees.py` already holds the joins and the measures.
* **Check.** Replayed on this study's data, it must flag:
  * Wimbledon 2026 men (main draw and qualifying) and the US Open 2026's Q3;
  * TML's Australian Open 2026 and US Open 2025;
  * Sackmann's Roland Garros qualifying of 2022–2025;
  * TML's women's events of December 2024 – February 2026.

  It must flag nothing in women's 2010–2024.

### 4.5 A source order per count, and a quarantine (designed)

* **What.** Each count of each match takes the first source that passed 4.4 for that event, in an order set per count from section 3.6. Proposed:
  * Aces, double faults, break points, service games: the official feed (TDI, the WTA API at tour events, the Slam feeds), then TML, then SofaScore.
  * Serve points and the first- and second-serve split: the official feed, then TML. Never SofaScore without a calibration.
  * A count that fails for an event, with no source that passes, is left blank rather than filled with a suspect value, as Stage 0 already does for counts that fail its row checks.
  * Each count records its source (the merge-feasibility proposal's `stats_source`, kept per count).
* **Decided for Wimbledon and the US Open 2026, and applied** ([the decision](../../decisions/2026-10-06-slam-box-scores.md), under the owner's delegation). The owner confirmed the US Open part on a condition: "Yes if you think its most likely to be predictive". In 2022–2025 the US Open feed equalled Sackmann's counts, the training data, in 98.3–100% of player rows, so the condition holds. The review changed the plan in three ways:
  * **Whole box scores per match, from one source.** Mixing sources inside a match creates ratios no source recorded.
  * **The rule stops at the Slam feeds for now.** Elsewhere the referees' own disagreements with TML are not settled: the WTA API's first serves at some tour events, its own service-game count, and TDI's missing first/second split.
  * **Ties by identity, not by score.** The two matches whose scores disagree are TML's worst rows; filtering on score agreement would have left them uncorrected.
* **The override table.** `slam_overrides.py` writes [slam_box_overrides.csv](../../../data/studies/data_continuity/slam_box_overrides.csv): 731 matches (Wimbledon 366, US Open 365), each with the feed document's SHA-256. Every row resolves to exactly one TML row, no surname disagrees, and every feed box score passes Stage 0's checks under the feed's score. The feed's statistics equal its own point stream in 96.4–100% of rows per event.
* **Applying it.** Every `stage0_build.py` run applies the table, right after the rows are read and before any score is parsed.
  * `--no-box-overrides` builds without it.
  * Another table needs `--confirm-live-overrides` to reach the live folder.
  * `--out-dir` builds elsewhere.
* **The dry run** (`stage0_dry_run.py`, [stage0_dry_run.json](../../../data/studies/data_continuity/stage0_dry_run.json)) built Stage 0 twice into a scratch folder:
  * the live tables did not change;
  * no match changed outside the 731;
  * after the overrides, all nine counts equal the feed's in every one of them;
  * Wimbledon men's first serves in fell from 67.7% to 63.8% (main draw) and from 70.9% to 61.6% (qualifying);
  * 246 matches got back the service games Stage 0 had blanked, and all 731 now have a full box score.
* **Code drift.** On the same inputs, a plain rebuild differed from the tables of 30 Sep in 8,040 matches. `stage0_build.py` and `repair_data.py` had changed on 2 October. Every change is a correction:
  * 7,650 ITF and team matches, 98% of them from 2020–2024, no longer count a match tiebreak as games;
  * 305 player rows move to the player's own Sackmann id, each checked against the name that id carries in Sackmann's rows; 42 match ids change with them;
  * 137 durations are blanked.
* **The rebuild, 6 Oct 2026** (7 Oct, 00:05 UTC), approved by the owner on a condition: "Yes if you think its most likely to be what the end state of our model will want".
  * **First, Tennis My Life's results to 5 October.** A second dry run on those files passed like the first ([stage0_dry_run_tml1006.json](../../../data/studies/data_continuity/stage0_dry_run_tml1006.json)).
  * **One command** ran it, `rebuild_stage0.py --expect <that dry run's build>`. In order:
    1. it kept the 366 MB it would replace, with a SHA-256 manifest;
    2. it built Stage 0: 873,364 matches, equal row for row to the dry run's;
    3. it re-linked the closing odds;
    4. it rewrote the 42 changed ids in the frozen match-timing links;
    5. it refreshed and checked the timeline;
    6. it rebuilt the per-player, IOS and leak-proof inputs and the TrueSkill table.

    Record: [rebuild.json](../../../data/studies/data_continuity/rebuilds/2026-10-07T0005Z/rebuild.json).
  * **Coordination.** The three studies running at the time confirmed they did not read the tables it rewrote.
  * **Not yet rebuilt: the model's own inputs.** They are still on the tables of 30 Sep. The [offset-Elo decision](../../decisions/2026-10-06-offset-elo.md) lists the five steps, starting with Stage 1's baselines.
* **Still proposed.**
  * Women's qualifying and WTA 125 from the WTA API, and women's Slam qualifying from the Slam feeds.
  * The other events' order.
* **Check.** After the rebuild, `referees.py` shows no event below the thresholds, and `coverage.py` shows women's qualifying and WTA 125 back.

### 4.6 Keep identities across the splice (designed; small)

* **What.** At each refresh, map new TML ATP codes to Sackmann ids by exact name and birth date; TML's player table is refreshed every run. Then list the codes that still share a name with a Sackmann id, for review. No code with a Sackmann name twin enters silently.
* **Check.** In `identity.py`, the 72 split players fall to those reviewed and deliberately kept apart.

### 4.7 Record what was known when (designed)

* **What.** From the kept versions (4.1), give each staged row the time it first appeared and the time it last changed. Backtests can then use the data as first published, and publication delay can be measured per source.
* **Why.** A later correction to a TML-only row changes the inputs of matches played in between. The 2024 default shows TML makes such corrections (that one agreed with Sackmann, so Stage 0 was unaffected). A backtest on corrected data is not what the live model would have seen.
  * Live use is safe today: under the match-clock decision a result enters when it is final.
  * Backtests are not: scoring the frozen anchored model on matches as they arrive (market-anchoring suggestion 11) needs the data as it was.
* **Check.**
  * For two kept versions, the rows that changed are exactly the ones `tml_revisions.py` lists.
  * A UFC-style parity test: rebuilt as of a cut-off from the versions then held, the features equal those used at the time.

### 4.8 Terms (needs the owner)

* **What TML states.** *Observed, 6 Oct 2026; the canary records both statements every run.*
  * On its site: "License: MIT License", with an opensource.org link.
  * In its GitHub README: "All data usage is **non-commercial** unless explicitly permitted", and redistribution or commercial use "without permission from TennisMyLife and/or the ATP may violate copyright or terms of use".
  * It describes its database as inspired by Sackmann's, which is CC BY-NC-SA 4.0.
* **What to do.** Before any commercial use, ask TML for written permission, and keep the answer under `docs/decisions/`. Meanwhile keep per-row source attribution, so that TML-derived counts can be replaced by the official feeds' if needed.

### Order

1. **Done:**
   * 4.1 for TML, with the gate, and a daily download since 6 Oct ([download cadence](../../decisions/2026-10-06-download-cadence.md));
   * 4.3, run every Monday by the same scheduled task;
   * the Software Heritage part of 4.2;
   * 4.5 for Wimbledon and the US Open 2026, applied at the rebuild of 6 Oct.
2. **No spend and no outside action:** 4.6, then 4.4 and the rest of 4.5. These change how Stage 0 is built.
3. **Needs the owner:**
   * 4.2: the monthly copy off this PC;
   * 4.8.
4. **Once 4.1 has run for a few weeks:** 4.7.

## 5. Decisions for the owner

**Settled on 6 Oct 2026:**
* ~~Keep the TML adapter's new default?~~ Decided under the owner's delegation: keep every version, and add the gate ([decision](../../decisions/2026-10-06-tml-file-versions.md)).
* ~~Software Heritage requests?~~ Done on the owner's permission: four sources archived (4.2).
* ~~How to fix Wimbledon 2026?~~ Decided under the owner's delegation: the official feed's whole box scores, and its score for two matches ([decision](../../decisions/2026-10-06-slam-box-scores.md)).
* ~~The US Open 2026 extension?~~ Confirmed on the owner's condition, "most likely to be predictive", which holds (4.5).
* ~~When to rebuild Stage 0?~~ Approved on the owner's condition, "what the end state of our model will want", and run that night (4.5).
* ~~How often to download TML, and the canary?~~ Decided under the owner's conditions ([download cadence](../../decisions/2026-10-06-download-cadence.md)):
  * TML every day, from a Windows scheduled task, with a notification only when something needs a person;
  * the canary every Monday.
* ~~Collect each Slam's official feed as it is played?~~ The owner's condition was "if that will get us real up to date info as we are betting". So:
  * each feed is collected after its event, with a weekly reminder until it is;
  * collecting during the event is built with the betting pipeline, because no bet or prediction yet reads an in-progress result.

**Still the owner's:**
1. **A monthly copy of `data/raw/` to the existing bucket** `gs://tennis-predictions-archive/` (Coldline, us-west1). It would add:
   * about 5.5 GB once;
   * then 0.5–1 GB a month, with the kept TML versions and the receipts;
   * the copies a Stage 0 rebuild keeps (366 MB on 6 Oct).

   The owner's Google account on this PC already reaches the bucket.
2. **Approve the source order for other events** (4.5), including the official feeds filling women's qualifying and WTA 125 after the splice. This changes Stage 0.
3. **Write to TML** about the licence, the women's 2025 counts and the Slam first serves?

## 6. Limits

* **What is counted.** Agreement is counted where both sources have the count and the link's score agrees. Walkovers and rows without a score are excluded.
* **Independence.** Before the splice, TML may not be independent of Sackmann: it says it continues his format. Agreement there shows the same values, not two independent measurements.
* **Unchecked split.** For ATP events other than the Slams after the splice, no referee checks the first- and second-serve split: TDI's match statistics do not publish it. Its point data marks serve faults and could.
* **Two copies.** TML's revisions are seen between two copies only, 22 Sep and 6 Oct.
* **Stage 0 as built.** This study's measurements read Stage 0 as built on 30 Sep, from TML's copy of 22 Sep, with results to the week of 21 Sep 2026. That build is kept in `rebuilds/2026-10-07T0005Z/replaced/`. The live tables were rebuilt on 6 Oct, after the measurements; the rebuild record says what changed.
* **The reviewing agent's figures.** The figures this report takes from the two reviews were re-measured here before use: the moved-point win rates, the US Open 2026 Q3 rows, Roland Garros 2026, Sackmann's Roland Garros qualifying, and TML's US Open 2025 and Australian Open 2026 rates. The one exception is the reviewer's observation that TML's women's Wimbledon 2026 counts equal the WTA API's, which is not used here.
* **Roland Garros 2022's men's main draw** reads about 66% first serves in in both Sackmann and TML, against 62–64% in other years. No feed is held to check it.
* **When Sackmann went.** The catalog says Sackmann's repositories answer 404 "since September 2026". The project first recorded a 404 on 10 September. The market-anchoring research found `tennis_atp` live in the Wayback Machine on 14 March and gone on 22 June. Software Heritage has a full visit on 8 May and finds nothing after.

## Files and rebuild

| What | Where (code in `src/eda/data_continuity/`, outputs in `data/studies/data_continuity/`) |
|---|---|
| The contract, number parsing, the agreement measure | `common.py` |
| Each source's box scores on the contract | `sources.py` |
| TML against Sackmann | `tml_vs_sackmann.py` → `tml_vs_sackmann_fields.csv`, `_levels.csv`, `_matches.csv`, `_svgms.csv`, `_examples.csv`, `_pairs.parquet`, `tml_vs_sackmann.json` |
| Referees | `referees.py` → `referee_vs_stage0.csv`, `referee_three_way.csv`, `referee_rates.csv`, `referee_wta_bp_orientation.csv`, `referee_summary.json` |
| Coverage across the splice | `coverage.py` → `coverage_splice.csv` |
| Identity across the splice | `identity.py` → `identity_splits.csv`, `identity_splits.json` |
| TML's revisions | `tml_revisions.py` → `tml_revisions_files.csv`, `tml_revisions_cells.csv`, `tml_revisions.json`; the downloaded copies are in `data/raw/data_continuity/tennis_my_life/2026-10-06/` with receipts |
| The preservation register | `inventory.py` → `preservation_register.csv`, `preservation_register.json` |
| The canary | `canary.py` → `canary.jsonl` (a line per item per run), `canary_latest.json` |
| Software Heritage requests | `swh_save_requests.json` (ids, snapshots, dates) |
| TML's pre-audit backup, replayed through the gate | `tml_audit_backup.py` → `tml_audit_backup.csv`, `tml_audit_backup.json`; the 31 files in `data/raw/data_continuity/tennis_my_life/backup_ll_audit_20260906_044746/` |
| The Slam box-score overrides | `slam_overrides.py` → `slam_box_overrides.csv`, `slam_box_overrides.json` |
| The Stage 0 dry run | `stage0_dry_run.py` → `stage0_dry_run.json`, `stage0_dry_run_changes.csv` (the two builds go to the `--scratch` folder); `--name stage0_dry_run_tml1006` wrote the second run, on TML's files of 6 Oct |
| The coordinated rebuild | `rebuild_stage0.py` → `rebuilds/<stamp>/rebuild.json`, `id_map.csv`, and `replaced/` (the files it replaced, with `manifest.json`; gitignored). `--restore <stamp>` puts them back, each checked against the manifest first |
| Scheduled downloads | `src/ingest/scheduled.py`, run daily by the Windows task "Tennis predictions - daily data downloads" → `data/raw/_scheduled/runs.jsonl`, `state.json`, `logs/` |
| Keeping versions and the gate | `src/ingest/public_dump/common.py`: `keep_replaced`, `keep_held`, `write_atomic`, `Receipts.sightings`, and `download(keep_superseded=..., gate=...)`, both off by default. `src/ingest/public_dump/tennis_my_life.py`: on for TML, with the gate, `--accept-held`, the lock, the end year and `_changes.jsonl` |
| Stage 0 hooks | `src/eda/predictability_diagnostic/stage0_build.py`: the decided override table applied by default (`--no-box-overrides`, `--box-overrides` with `--confirm-live-overrides`), `--out-dir`, and `inputs.files` in the summary |
| Decisions | [TML file versions](../../decisions/2026-10-06-tml-file-versions.md), [Slam box scores](../../decisions/2026-10-06-slam-box-scores.md), [download cadence](../../decisions/2026-10-06-download-cadence.md) |
| Tests | `test/data_continuity/test_data_continuity.py` (11) and `test_rebuild_and_schedule.py` (10); `test/public_data_dump/test_keep_superseded.py` (5) and `test_tml_gate.py` (9) → `tests.xml`. With the rest of `test/public_data_dump/`: 77 pass |

Run from the repository root through Git Bash:

```bash
./python.sh src/eda/data_continuity/tml_vs_sackmann.py           # about 25 s; before referees.py
./python.sh src/eda/data_continuity/referees.py                  # about 15 s
./python.sh src/eda/data_continuity/coverage.py
./python.sh src/eda/data_continuity/identity.py
./python.sh src/eda/data_continuity/inventory.py                 # walks data/raw/, a minute or two
./python.sh src/eda/data_continuity/tml_revisions.py --no-fetch  # re-diff the saved copies; without the flag it downloads today's changed files
./python.sh src/eda/data_continuity/canary.py                    # network: about 25 requests; appends to canary.jsonl
./python.sh src/eda/data_continuity/tml_audit_backup.py --no-fetch  # replay the kept pre-audit backup through the gate
./python.sh src/eda/data_continuity/slam_overrides.py            # about a minute; writes the table only if every check holds
./python.sh src/eda/data_continuity/stage0_dry_run.py --scratch <folder outside data/studies/predictability_diagnostic>   # two Stage 0 builds, about 5 minutes
./python.sh src/eda/data_continuity/rebuild_stage0.py --expect <the dry run's overrides folder>   # REWRITES the live tables; coordinate first; about 50 minutes
./python.sh -m src.ingest.scheduled --dry-run                    # which scheduled jobs are due today (the task runs it daily)
./python.sh -m pytest test/data_continuity test/public_data_dump -p no:cacheprovider --basetemp=data/studies/data_continuity/pytest_tmp --junitxml=data/studies/data_continuity/tests.xml
```

* **Keep `--basetemp` short.** A folder deep in the user's temp directory pushed one `tennis_data_couk` test's file name past Windows' 260-character limit, and the test failed with FileNotFoundError.
* **Inputs.** The measurements only read Stage 0's tables, the match-timing link files and the staged dump. Only `rebuild_stage0.py` writes those, after keeping copies.
* **Network.** It is touched by the canary, `tml_revisions.py`, `tml_audit_backup.py`, the Software Heritage requests and the scheduled TML download.
* No paid call or new package was used.
* **The shared-code changes.**
  * `common.py` gains version keeping and the gate, both off by default. Its downloads and metadata are now written whole and then renamed, for every caller.
  * `stage0_build.py` gains the hooks above. Run with no new arguments, it writes the same six outputs as before, plus the input record in its summary.
  * The public-dump tests passed before the changes (42 of 42) and after them (56 of 56, with the 14 new ones).
  * The predictability diagnostic's tests, after the rebuild: 238 of 241 pass. Three fail because they hold that study's own tables of 30 Sep against the live Stage 0:
    * its Stage 1 baselines and Stage 3 ratings have 872,704 rows, against 873,364;
    * its Stage 4 country table lacks the events new since 22 Sep (Braga, Porto, Jingshan, Bari and others).

    Rerunning that study's stages 1–4 (about 40 minutes) would clear them, but it would also rewrite its published numbers, so it is left to whoever reruns it. The match-timing rebuild reads only those stages' code and frozen constants, not these tables.
