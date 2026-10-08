# Lane B: tour point-by-point datasets, decrypted ATP copies and Sackmann (29 Sep 2026)

**Scope.** Do the sources suggested for three data-map gaps hold the data? `wta_2018_points` (3,491 matches), `atp_points_2025` (3,778), `itf_after_june_2026` (~10,332 estimated), plus what these datasets add to `slam_points_ao_rg` (AO/RG rows). Gap rows are the data map's own selection from `data/studies/data_map/matches.parquet` (tour, level, year, best grain below `point`), which reproduces the map's counts exactly.

**How.** All requests on 29 Sep 2026 (UTC 17:28–18:10). Python from `./python.sh`. GitHub read-only through the owner's `gh` CLI. Kaggle and Zenodo through their public APIs with no account; Kaggle files through Kaggle's public download endpoint. Websites paced at one request per 2+ seconds. No login, no block met, nothing decrypted, nothing installed, no existing file changed.

**Evidence labels:** [observed] = seen in the data or response today; [provider claim] = the publisher says so; [inference] = my reasoning; [not determined].

## Bottom line

| Gap | Gap matches | Kaggle marcosjn2 fills | SirGenkii fills | Together |
|---|---:|---:|---:|---:|
| `wta_2018_points` | 3,491 | **1,377** (all replay to a complete score; 1,375 equal Sackmann's score) | 0 | 1,377 |
| `atp_points_2025` | 3,778 | **1,335**, all Jan–Jun 2025 (1,307 score-checked equal) | **715**, Jan–Apr 2025, with point outcomes | **1,360** |
| &nbsp;&nbsp;of which season weeks Dec 2024–Jun 2025 | 1,419 | 1,335 (94%) | 715 | 1,360 |
| &nbsp;&nbsp;of which Jul 2025–Aug 2026 | 2,359 | 0 | 0 | 0 |
| `slam_points_ao_rg`, AO and RG 2022–2025 | 1,409 | **1,242** (1,236 complete replays) | 13 (AO 2025 men, all also in marcosjn2) | 1,242 |
| `slam_points_ao_rg`, AO/RG 2026 | 217 | 0 | 0 | 0 |
| `itf_after_june_2026` | ~10,332 (est.) | — | — | no newer Sackmann snapshot exists; **women's side: a Kaggle WTA-site dataset lists 4,695 ITF main-draw matches in the missing weeks** (lead, §B5) |

* **B1 marcosjn2 [observed]:** version 2 (29 Aug 2025), 48,479 SofaScore matches, **2015-06-20 to 2025-06-28**, despite the "2015–2026" title. Downloaded in full without login (Kaggle's public endpoint redirects to a signed storage URL). Point order checks out apart from one systematic artefact: **99.5% of tie-breaks carry one extra trailing point for the tie-break winner.** With that allowed, 99.6% of records replay to a finished match, 99.45% of 39,275 records linked to Sackmann match his score exactly, and 99.5% of games equal Sackmann's Slam point logs point for point. It holds no 2025 H2 or 2026 matches, almost no WTA 125 (Limoges only), and almost no retirements.
* **B2 SirGenkii [observed]:** head `ec1b188` (11 Apr 2025), dumps from `1bb7527` (7 Apr 2025). 1,294 matches of season 2025 (27 Dec 2024 to the commit of 7 Apr 2025); 922 with point rows, all 922 with winner / forced / unforced-error outcomes. It adds outcomes, serve number and (at some events) serve speed to 715 gap matches, but only 25 matches that marcosjn2 lacks.
* **B3 [observed]:** no newer decrypted ATP copy exists on GitHub, Hugging Face or Kaggle. The Hugging Face dump is unchanged since `ea3d94d` (19 Jun 2026); its owner publishes nothing else. The only fork of glad94/infotennis created since 24 Sep (menceladam, today) holds an Elo model, no Infosys data.
* **B4 [observed]:** the ATP Stats Centre files exist for **2025 and 2026 tour-level matches through at least 29 Aug 2026** and for 2025–26 Challengers: 16 of 20 requests returned a file. The two bodies read are encrypted envelopes: `{"lastModified", "response", "data": null}`, a third key not seen on 24 Sep.
* **B5 [observed]:** `tennis_atp`, `tennis_wta`, `tennis_slam_pointbypoint` and `tennis_pointbypoint` are still 404. The Match Charting Project is live, with no commit after `1813a13` (18 Sep 2026). The mirror the project used (`Aneeshers/tennis-sackmann-archive` @ `83733587353d`, one commit of 25 Jun 2026) and its 10 forks and Hugging Face twin have nothing newer. **tennisabstract.com is still updated with ITF results after June 2026** (one player file, last modified today).
* **B6 [observed]:** no other public point-by-point source for WTA 2018 or ATP tour level 2025–26 was found on Kaggle, GitHub, Hugging Face or Zenodo.

## B1. Kaggle `marcosjn2` "Tennis Point-by-Point Match Dataset (2015–2026)"

### The dataset [observed, Kaggle API `datasets/view` and `datasets/list`, 17:28–17:29 UTC]

* **Where:** https://www.kaggle.com/datasets/marcosjn2/tennis-point-by-point-match-dataset-20152025, owner "Marcos Johnson Noya", dataset id 8163030.
* **Version:** current version 2 ("Update 2025-08-29", 2025-08-29T16:30:11Z); version 1 "Initial release" 2025-08-29T03:24:31Z. Storage version id 12907792.
* **Files:** `atp-matches.jsonl` 145,024,923 bytes; `wta-matches.jsonl` 118,527,233 bytes. SHA-256 `57ddc344…d8ca` and `4243a226…31f0` (full values in the receipts).
* **Other:** licence label "MIT"; no description or subtitle; 143 downloads, 457 views, 3 votes; usability 0.25.
* **Record creation stamps:** `meta.created_at_utc` 2025-08-29 02:58–03:04Z (ATP) and 15:04–15:10Z (WTA). [inference] Version 1 held the ATP file and version 2 added the WTA file.

### Download [observed]

* `GET https://www.kaggle.com/api/v1/datasets/download/<owner>/<slug>/<file>` with no cookie or token answers **302** to `https://storage.googleapis.com/kagglesdsdata/datasets/8163030/12907792/<file>?X-Goog-…` (signed for 259,200 s). Both files were streamed in full (13 s) and match the listed sizes.
* Saved to `data/raw/gap_sources/marcosjn2/` (gitignored) with `_view.json`, `_files.json` and `_receipts.jsonl`. Script: `src/eda/gap_sources/fetch_marcosjn2.py`.

### Content [observed]

* **Records:** 48,479 (ATP 25,185; WTA 23,294); one per SofaScore event id, no duplicates. Every record has `meta.source = "sofascore"` and `meta.version = "1.0.0"`.
* **Dates:** `meta.date` runs 2015-06-20 to 2025-06-28. It is the match day, not the week: Halle 2015's semi-final is dated 20 Jun 2015.
* **Per game:** `server_side`, a 1/0 `point_sequence` (1 = home player won the point), its server-relative twin, and the game winner. There is no ace, fault, serve number or outcome.
* **Qualifying** is marked in the round name, or only in the tournament name (for example "Australian Open, Melbourne, Australia, Qualifying" with a blank round, or with a round such as "Round of 16"): about 1,270 records.
* **Tier (`tournament.points`)** is not the tier of the year [observed]. Linz, Strasbourg and Monterrey (Internationals in 2018) carry 500 in 2018; Dubai (Premier) carries 1000 and Birmingham (Premier) 250. [inference] It is the tournament's present SofaScore category. "none" holds WTA Internationals such as Moscow, Istanbul and Luxembourg, the Finals, the Olympics, the ATP Cup and 2020–21 one-off events.

**Men (ATP file), records by year, tier and draw:**

| Year | main 2000 | main 1000 | main 500 | main 250 | main none | qual 2000 | qual 1000 | qual 500 | qual 250 | qual none | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2015 | 89 | 134 | 133 | 204 | 96 | 0 | 3 | 0 | 18 | 10 | 687 |
| 2016 | 266 | 445 | 324 | 622 | 99 | 21 | 25 | 0 | 21 | 1 | 1,824 |
| 2017 | 316 | 448 | 351 | 751 | 25 | 74 | 32 | 3 | 61 | 0 | 2,061 |
| 2018 | 328 | 448 | 377 | 781 | 24 | 109 | 27 | 9 | 75 | 0 | 2,178 |
| 2019 | 329 | 450 | 378 | 801 | 29 | 117 | 58 | 5 | 88 | 1 | 2,256 |
| 2020 | 303 | 146 | 167 | 341 | 158 | 43 | 18 | 0 | 46 | 0 | 1,222 |
| 2021 | 471 | 491 | 348 | 860 | 255 | 400 | 144 | 18 | 173 | 20 | 3,180 |
| 2022 | 463 | 484 | 439 | 816 | 258 | 310 | 0 | 47 | 64 | 23 | 2,904 |
| 2023 | 411 | 643 | 488 | 891 | 41 | 413 | 0 | 0 | 24 | 0 | 2,911 |
| 2024 | 428 | 648 | 472 | 915 | 73 | 432 | 250 | 193 | 407 | 0 | 3,818 |
| 2025 | 227 | 406 | 322 | 409 | 0 | 324 | 160 | 135 | 161 | 0 | 2,144 |

**Women (WTA file):**

| Year | main 2000 | main 1000 | main 500 | main 250 | main 125 | main none | qual 2000 | qual 1000 | qual 500 | qual 250 | qual none | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2015 | 98 | 98 | 100 | 65 | 16 | 173 | 0 | 0 | 7 | 2 | 6 | 565 |
| 2016 | 307 | 371 | 245 | 212 | 28 | 339 | 18 | 40 | 31 | 9 | 15 | 1,615 |
| 2017 | 368 | 447 | 300 | 309 | 25 | 317 | 61 | 17 | 24 | 12 | 25 | 1,905 |
| 2018 | 410 | 475 | 310 | 355 | 22 | 318 | 41 | 10 | 24 | 21 | 18 | 2,004 |
| 2019 | 406 | 482 | 330 | 348 | 27 | 287 | 101 | 32 | 17 | 39 | 65 | 2,134 |
| 2020 | 333 | 165 | 193 | 154 | 0 | 68 | 33 | 10 | 14 | 10 | 6 | 986 |
| 2021 | 484 | 461 | 430 | 303 | 29 | 670 | 387 | 63 | 66 | 0 | 19 | 2,912 |
| 2022 | 486 | 439 | 472 | 477 | 29 | 285 | 325 | 0 | 0 | 0 | 0 | 2,513 |
| 2023 | 444 | 591 | 544 | 626 | 29 | 79 | 432 | 0 | 18 | 17 | 0 | 2,780 |
| 2024 | 458 | 700 | 515 | 653 | 30 | 64 | 429 | 286 | 264 | 347 | 0 | 3,750 |
| 2025 | 235 | 468 | 290 | 307 | 0 | 0 | 331 | 178 | 152 | 169 | 0 | 2,130 |

* **WTA 2018 by tier [observed]:** main 2000 410, 1000 475, 500 310, 250 355, 125 22 (Limoges, the only WTA 125 event in the whole file: 239 records over 2015–24), none 318 (Moscow 47, Nuremberg 29, Istanbul 27 …, WTA Finals 9, Elite Trophy 13). Qualifying 114. Total 2,004. No other WTA 125 and no ITF.
* **ATP 2025 by month of match [observed]:** Jan 352, Feb 383, Mar 296, Apr 341, May 419, Jun 353 (last record 28 Jun). **ATP 2026: 0 records.**

| Month 2025 | main 2000 | main 1000 | main 500 | main 250 | qual 2000 | qual 1000 | qual 500 | qual 250 | Total |
|---|---|---|---|---|---|---|---|---|---|
| Jan | 119 | 0 | 0 | 99 | 104 | 0 | 0 | 30 | 352 |
| Feb | 0 | 0 | 168 | 102 | 0 | 0 | 71 | 42 | 383 |
| Mar | 0 | 176 | 4 | 14 | 0 | 71 | 0 | 31 | 296 |
| Apr | 0 | 132 | 60 | 66 | 0 | 55 | 28 | 0 | 341 |
| May | 98 | 98 | 30 | 25 | 110 | 34 | 12 | 12 | 419 |
| Jun | 10 | 0 | 60 | 103 | 110 | 0 | 24 | 46 | 353 |

* **AO and RG 2022–2025 [observed]** (a Slam main draw has 127 singles matches per gender):

| Slam | Year | Men main | Men qual | Women main | Women qual |
|---|---|---|---|---|---|
| AO | 2022 | 122 | 0 | 123 | 0 |
| AO | 2023 | 95 | 104 | 109 | 109 |
| AO | 2024 | 105 | 109 | 115 | 104 |
| AO | 2025 | 119 | 104 | 117 | 109 |
| RG | 2022 | 120 | 104 | 119 | 109 |
| RG | 2023 | 100 | 93 | 108 | 106 |
| RG | 2024 | 102 | 107 | 113 | 107 |
| RG | 2025 | 108 | 110 | 118 | 111 |

### Completeness

* **Replay of every record [observed]:**
  * **Standard games:** all 1,121,953 end exactly on their last point, apart from 156 short games.
  * **Tie-breaks:** **17,059 of 17,141 (99.5%) have exactly one extra point after the tie-break was won, credited to its winner.** Dropping that trailing point leaves a valid tie-break. 239 are final-set 10-point tie-breaks.
  * **Matches, with the artefact allowed:**
    * complete: 48,284 (99.60%);
    * unfinished: 18, stopping at a set break (the ones checked are retirements);
    * inconsistent: 177 (0.37%), mainly a game with missing points in mid-match. This rises to 1.5% in 2024 and 0.8% in 2025, against 0–0.1% before 2023.
* **Against an independent point log [observed].** 5,392 Slam matches were compared with Sackmann's Slam point-by-point (IBM feeds) in the archive mirror: 31 editions, 2015–2024.
  * **Standard games:** 150,710 have the same point order; 697 differ (0.46%), in 511 matches. Some differences are errors on Sackmann's side: a five-point love game, or a one-point game.
  * **Tie-breaks:** **2,153 of 2,181 equal Sackmann's sequence plus one trailing point**; 21 are identical; 7 differ otherwise. This settles where the artefact sits: it is appended at the end.
* **Against official scores [observed].** 39,275 of the 39,822 records from 2018 on link to a Sackmann result row (same tour, both surnames, -10..+21 days).
  * **Replayed score:** set scores and tie-break points equal Sackmann's for 39,058 (99.45%). Set scores differ for 175, tie-break points only for 24, and the winner for 18.
  * **Link errors:** some of those differences are my own link errors: the Pliskova twins, two Wangs, one player facing another twice in a week.
* **Retirements are almost absent.**
  * [observed] Only 14 of the 39,275 linked records are retirements or defaults in Sackmann, against 2.8% of Sackmann's 2018–25 tour-level rows.
  * [inference] The scrape kept finished matches, plus a few retirements at a set break.
  * [observed] 60 of the 84 unfilled Jan–Jun 2025 ATP gap matches are retirements in Tennis My Life. Only 73 of the 593 unfilled WTA 2018 main-draw gap matches are.
* **Coverage within events is partial** [observed]. WTA 2018 events hold 40–90% of their matches (Auckland 15 of 31; Bucharest 0). Why a finished match is missing is [not determined]: SofaScore lacks its points, or the scraper dropped it.

### Link to the data map gaps [observed]

* **Method.**
  * Every record from 2018 on (39,822) was linked to the whole map universe with the map's own rules and name functions (`surname_key`, `pair_key` and `same_player` from `src/eda/data_map/measure.py`):
    * same tour and both surname keys, record date -10..+21 days from `d` (-40 for Slam qualifying);
    * then one surname plus the loose test of the other name;
    * a draw mismatch and clashing first names are penalised.
  * The result: 39,472 records linked, 192 of them by the one-surname pass.
  * When two records reached one match (98 records), the closer date was kept.
  * Gap matches were then read off the linked uids.
* **`wta_2018_points`: 1,377 of 3,491 filled.** All 1,377 replay complete; 1,375 have Sackmann's exact score.

  | Level | T1000 | T500 | T250 | FIN | CH (WTA 125) | TQ | CHQ |
  |---|---|---|---|---|---|---|---|
  | Gap | 559 | 361 | 949 | 27 | 304 | 1,162 | 129 |
  | Filled | 417 | 248 | 622 | 16 | 19 | 55 | 0 |

* **`atp_points_2025`: 1,335 of 3,778 filled.** By level: T1000 280/820, T500 254/635, T250 352/1,096, TQ 449/1,209, FIN 0/18.
  * **By week of `d`:** Dec 2024 45/49, Jan 88/97, Feb 313/334, Mar 276/296, Apr 239/255, May 169/176, Jun 205/212. Nothing from Jul 2025 on (2,359 gap matches).
  * **Score check:** 1,307 have Sackmann's exact score. 27 have no Sackmann row to check (Sackmann spells O'Connell differently), and 1 differs.
* **`slam_points_ao_rg`: 1,243 of 1,636 filled.**
  * **AO/RG 2022–2025:** 1,242 of 1,409 (1,236 complete replays).
  * **The rest:** 1 US Open 2024 row. None in 2026.
  * **Rows without a tournament name:** 5 gap rows carry none (4 AO 2022 and 1 AO 2026, created from Slam draws). They are left out of the AO/RG split, and none links to a record.

  | Slam | Year | Men gap | Men filled | Women gap | Women filled |
  |---|---|---|---|---|---|
  | AO | 2022 | 89 | 87 | 108 | 106 |
  | AO | 2023 | 60 | 43 | 63 | 51 |
  | AO | 2024 | 75 | 61 | 94 | 85 |
  | AO | 2025 | 76 | 70 | 89 | 82 |
  | RG | 2022 | 96 | 91 | 104 | 98 |
  | RG | 2023 | 90 | 69 | 109 | 94 |
  | RG | 2024 | 82 | 63 | 93 | 82 |
  | RG | 2025 | 74 | 63 | 107 | 97 |
  | AO/RG | 2026 | 217 | 0 | – | – |

  * **Lane A's count differs slightly** (its `marcosjn2_ao_rg_summary.json` as of this writing). Its `marcosjn2_slams.py` links main-draw records by its own rules and counts 1,216 of these 1,409 in the gap. It reports 559 of them as not already covered by the hawkilol Court Vision copy. The 26-match difference comes from the link rules and was not reconciled.
* **Per-match results:** `data/studies/gap_sources/marcosjn2_gap_links.csv` has 3,955 rows, one per gap match filled. Each row carries the gap id, map uid and fields, the record key and SofaScore event id, the link pass and date offset, the replay status, point and tie-break counts, the replayed score, and Sackmann's score with the comparison.
* **Summary:** `marcosjn2_summary.json`.

### Caveats

* The **point sequences need the trailing tie-break point removed** before any use. The replay code (`_game` in `marcosjn2_links.py`) shows the rule.
* **Point winners only.** The grain is the map's `point` level: who won each point and who served. There are no aces, double faults, serve numbers or outcomes.
* **Licence and provenance:** Kaggle label "MIT"; the records are a SofaScore scrape (`meta.source`) [observed].
* SofaScore event ids and player ids are present, so the project's SofaScore adapter could fetch the same matches directly [inference].

## B2. `SirGenkii/infotennis`

* **Repository [observed, GitHub API]:**
  * https://github.com/SirGenkii/infotennis, a fork of glad94/infotennis; public; MIT (code).
  * Head `ec1b188f30e9bccc6923ed084b0db99e0e472917` (2025-04-11, "add steps to export database as csv…"). `backup_sql/` was last changed in `1bb7527dda3845fc2cbe4c3d4391042f5cf97aa1` (2025-04-07). Nothing has been pushed since 11 Apr 2025.
* **Download [observed]:** six MySQL 8.0.41 dumps (database `infotennis4`), 34.4 MB, from raw.githubusercontent.com at the head commit; every git blob SHA-1 matches the tree.

  | Dump | Bytes | Rows |
  |---|---:|---:|
  | `atp_rally_analysis` | 21,302,011 | 136,928 |
  | `atp_stroke_analysis` | 9,236,069 | 87,976 |
  | `atp_court_vision` | 1,900,997 | 6,992 |
  | `atp_key_stats` | 1,650,472 | 6,264 |
  | `atp_results` | 316,629 | 1,343 |
  | `atp_calendars` | 8,979 | 23 |

  Also taken: the README, the `references/api-info` JSON and the scraper code. All in `data/raw/gap_sources/sirgenkii/`, with `_receipt_ec1b188.json`. Script: `src/eda/gap_sources/fetch_sirgenkii.py`.
* **Content [observed]:**
  * **Scope:** 23 tournaments, from the United Cup and Brisbane/Hong Kong (from 27–30 Dec 2024) to Monte-Carlo 2025. Monte-Carlo is marked "Ongoing" and has 32 matches: qualifying and 11 first-round matches, up to the commit of 7 Apr.
  * **Points per event:** point rows exist for most matches at every tour event; Montpellier has 19 of 39, Rotterdam and Dallas 30 of 43. Only 14 of the 239 Australian Open matches (all main draw) have them.
  * **Matches:** 1,294 distinct, all season 2025.
  * **Point end types:** unforced error 51,263; forced error 38,672; winner 31,911; ace 10,202; double fault 4,771; unclassified 109.
* **Matches by week and level [observed]** (week from Tennis My Life's `tourney_date`; "outcomes" means at least one point labelled winner, forced or unforced error):

  | Week start | Level | Matches | With point rows | With outcomes | With serve speed | With key stats | With Court Vision |
  |---|---|---:|---:|---:|---:|---:|---:|
  | Dec 2024 | T250 | 58 | 56 | 56 | 26 | 56 | 0 |
  | Dec 2024 | TQ | 30 | 29 | 29 | 12 | 24 | 0 |
  | Dec 2024 | United Cup | 26 | 0 | 0 | 0 | 0 | 0 |
  | Jan 2025 | GS (AO) | 127 | 14 | 14 | 14 | 0 | 0 |
  | Jan 2025 | GSQ (AO) | 112 | 0 | 0 | 0 | 0 | 0 |
  | Jan 2025 | T250 | 81 | 62 | 62 | 0 | 80 | 0 |
  | Jan 2025 | TQ | 36 | 33 | 33 | 0 | 33 | 0 |
  | Feb 2025 | T250 | 108 | 103 | 103 | 0 | 103 | 0 |
  | Feb 2025 | T500 | 185 | 176 | 176 | 0 | 177 | 0 |
  | Feb 2025 | TQ | 120 | 91 | 91 | 0 | 115 | 0 |
  | Mar 2025 | T1000 | 190 | 149 | 149 | 149 | 138 | 0 |
  | Mar 2025 | T250 | 81 | 80 | 80 | 54 | 80 | 0 |
  | Mar 2025 | TQ | 108 | 97 | 97 | 87 | 91 | 0 |
  | Apr 2025 | T1000 | 11 | 11 | 11 | 11 | 11 | 8 |
  | Apr 2025 | TQ | 21 | 21 | 21 | 21 | 21 | 0 |

  * **Totals:** 922 matches with point rows, all 922 with outcomes; a median of 141 point rows a match.
  * **Serve speeds:** missing at every 500 event and at the January–February 250s.
* **Link [observed]:**
  * **Tennis My Life:** 1,288 of 1,294 matches link exactly, by ATP tournament id plus both ATP player codes. The dumps carry codes such as `m0g4`; Tennis My Life has `M0G4`.
  * **The data map:** 1,283 link by names and week, the map's rule. In all 1,279 matches linked both ways, the map's `d` equals Tennis My Life's week.
  * Of the map rows reached, 998 were at `stats` grain, 228 at `shot` and 57 at `point`.
* **`atp_points_2025` fill:**
  * **Size:** 805 SirGenkii matches are gap matches; **715 have point rows, all with outcomes.** By level: T1000 106, T500 124, T250 239, TQ 246. By week: Dec 2024 47/49, Jan 83/97, Feb 297/334, Mar 258/296, Apr 30/255.
  * **Width:** outcomes cover 89% of points on average (the rest are aces, double faults or unclassified). 284 have serve speed, 695 key stats, 6 Court Vision.
  * **Overlap:** 690 of the 715 are also filled by marcosjn2, so SirGenkii adds only 25 new gap matches. It adds width (outcome, serve 1/2, rally length bucket, speed) to 690 more.
  * **AO 2025 (`slam_points_ao_rg`):** 13 men's matches with points, all also in marcosjn2.
* **Output:** `data/studies/gap_sources/sirgenkii_matches.csv` (1,294 rows: counts per table, the Tennis My Life and map links, gap flags, overlap with marcosjn2) and `sirgenkii_summary.json`.
* **Caveat:** the calendar's `date_start` has placeholder first dates (for example Delray Beach "2025.02.01 - 2025.02.16"), so weeks come from Tennis My Life, or else from the end date minus 6 days.

## B3. Newer decrypted ATP copies

* **Forks of glad94/infotennis [observed, 7 forks]:**

  | Fork | Created | Relation to upstream | Data |
  |---|---|---|---|
  | `menceladam/infotennis` | 2026-09-29 (today) | `main` identical to upstream. A branch `challenger-elo-model` has 14 commits made today | Elo, handicap and odds code using Tennis My Life; `data/ratings_latest.csv`, `predictions_log.csv`. No Infosys data |
  | `Dvago432` | 2026-04-26 | identical | none |
  | `devarajand8`, `hbweb`, `pratikv` | 2025 | one commit behind | none |
  | `alxlk` | 2025-04-10 | two commits ahead (`config.yaml` only) | none |
  | `SirGenkii` | 2025-04-07 | — | the only one with data |

  * **Upstream:** the last commit is 2026-01-06, "Async scraping at long last" (code). `glad94/infotennis_v2` (pushed 2026-04-12) holds dbt and flow code only, and `glad94.github.io` holds blog images.
* **GitHub code search for the Infosys host** `itp-atp-sls.infosys-platforms.com` and its routes (5 searches) found 11 repositories [observed]. None holds decrypted 2025–26 files:
  * code only: glad94 ×3, nipunagarwalla/courtside, iliyasone/atptour-parser, vitolytics/tennis-data-pipeline (a copy of infotennis code), dydi22/DP1, ryurko/hawkeye (2021), SimoneBiondo/webcrawler (pushed Apr 2024);
  * LHBUSA/tennis: a betting web app, created 26 Sep 2026;
  * robertyang87/tennislive (16.5 GB): a Chinese social-media content pipeline. The code-search hits are docs and a point-by-point fetch tool; its `data/` folder holds state files, not Infosys dumps (the whole tree was not listed);
  * duckduckgo/tracker-radar-wiki: tracker lists.
  * Repository searches (pushed after May 2025) for "infosys tennis", "atp stats centre", "court vision tennis", "matchbeats", "atp rally analysis", "hawkeye tennis data" and "infotennis" returned nothing relevant: computer-vision and prediction projects, plus glad94's two repositories.
* **Hugging Face [observed, Hub API]:**
  * `atlas-polybot/atp-pipeline-handoff` is **unchanged**: sha `ea3d94d79f5d9e9b4bead031e2c6262f91a86c35`, lastModified 2026-06-19T04:53:49Z, a single commit "Raw ATP scraper data only (proprietary pipeline removed; history squashed)". 451 downloads (424 on 24 Sep).
  * The organisation `atlas-polybot` has 1 dataset, 0 models and 0 spaces. There is no GitHub account of that name.
  * A search of 20 terms (infosys, court vision, hawkeye, tennis point, sofascore, atp, wta …) found no other ATP Stats Centre copy.
* **Kaggle [observed]:** "infosys tennis" gives 0 results; "atp stats", "hawkeye tennis" and "court vision" give nothing relevant.
* **Conclusion [observed across these searches; inference that none exists elsewhere]:** decrypted Stats Centre data public anywhere ends in April 2025 (SirGenkii). May 2025 onward exists only as the ATP's encrypted files (B4).

## B4. ATP Stats Centre files for 2025–2026

* **Method.** 20 requests, 2.5 s apart (18:06:13–18:07:00 UTC), plus one repeat GET at 18:07:34 UTC to read a body. Script: `src/eda/gap_sources/probe_atp_statscentre.py`; results in `data/studies/gap_sources/atp_statscentre_probe.csv`.
  * **Headers:** Chrome user agent plus `Referer` and `Origin: https://www.atptour.com`.
  * **URL templates:** from `references/api-info/atp-infosys-api-info.json` (glad94/SirGenkii), for example `https://itp-atp-sls.infosys-platforms.com/static/prod/match-beats/{year}/{event}/{match}/data.json`.
  * **Ids:** event ids are Tennis My Life `tourney_id` numbers. Match codes are ATP's: `MS001` = final, `QS001` = qualifying. The SirGenkii results table confirms MS001–MS003 are the final and semi-finals.
* **Results [observed]:**

  | Year | Event | Match | Match described | File | Status | Bytes | Type | Last-Modified |
  |---|---|---|---|---|---|---:|---|---|
  | 2025 | 416 | MS001 | Rome final | match-beats | 200 | 75,472 | json | 05 Jun 2026 |
  | 2025 | 500 | MS001 | Halle final | match-beats | 200 | n/a | json | 04 Jun 2026 |
  | 2025 | 418 | MS001 | Washington final | rally-analysis | 200 | 85,996 | json | 24 Sep 2026 |
  | 2025 | 422 | MS001 | Cincinnati final (retired at 5-0) | match-beats | **403** | – | xml | – |
  | 2025 | 5014 | MS001 | Shanghai final | match-beats (GET) | 200 | 93,284 | json | 28 May 2026 |
  | 2025 | 605 | MS001 | ATP Finals final | match-beats | 200 | n/a | json | 05 Jun 2026 |
  | 2025 | 421 | QS001 | Canada qualifying | match-beats | **403** | – | xml | – |
  | 2026 | 339 | MS001 | Brisbane final | match-beats | 200 | 72,568 | json | 04 Jun 2026 |
  | 2026 | 1536 | MS001 | Madrid final | match-beats | 200 | n/a | json | 05 Jun 2026 |
  | 2026 | 311 | MS001 | Queen's final | rally-analysis | 200 | 93,060 | json | 17 Sep 2026 |
  | 2026 | 421 | MS001 | Canada final | match-beats (GET) | 200 | 91,512 | text/plain | 14 Aug 2026 |
  | 2026 | 421 | MS001 | Canada final | keystats | 200 | 31,684 | json | 28 Sep 2026 |
  | 2026 | 421 | MS001 | Canada final | court-vision | 200 | 424,108 | json | 25 Sep 2026 |
  | 2026 | 422 | QS001 | Cincinnati qualifying | match-beats | **403** | – | xml | – |
  | 2026 | 6242 | MS001 | Winston-Salem final (29 Aug) | match-beats | 200 | 72,228 | text/plain | 29 Aug 2026 |
  | 2025 | 2907 | MS001 | Nottingham Challenger final | match-beats | 200 | 105,872 | json | 26 May 2026 |
  | 2025 | 7341 | MS001 | Brest Challenger final | match-beats | **403** | – | xml | – |
  | 2026 | 1214 | MS001 | Troyes Challenger final | match-beats | 200 | n/a | text/plain | 05 Jul 2026 |
  | 2026 | 1763 | MS001 | Genoa Challenger final (13 Sep) | match-beats | 200 | n/a | text/plain | 13 Sep 2026 |
  | 2026 | 1763 | MS001 | Genoa Challenger final | rally-analysis | 200 | n/a | json | 17 Sep 2026 |

* **What the results say:**
  * **16 of 20 exist [observed]:**
    * tour level: May–Nov 2025 and Jan–Aug 2026;
    * the Canada 2026 final: MatchBeats, rally, key stats and Court Vision;
    * Challengers: 2025 and 2026.
  * **The 4 absent files** returned 403 with an XML body type and `x-cache: Error from cloudfront`, the storage layer's answer for a missing object. No challenge page and no 429 were seen.
    * Cincinnati 2025 final: [inference] a match that ended by retirement at 5-0 may get no MatchBeats file.
    * Brest Challenger: [not determined] whether Tennis My Life's id 7341 is the ATP's.
    * The two `QS001` codes: [not determined] whether those codes exist at Masters qualifying.
  * **"n/a" sizes:** the HEAD response carried no Content-Length.
* **Body shape [observed]:**
  * **Keys:** both GET bodies are JSON objects with keys `data`, `lastModified`, `response`. **`data` is `null`**, a key not seen on 24 Sep.
  * **Ciphertext:** `response` is base64. In a saved copy of the Canada 2026 final, 91,456 characters decode to 68,592 bytes, a multiple of 16, which fits AES block ciphertext. Its `lastModified` (2026-08-14T01:40:20.787Z) equals the HTTP Last-Modified.
  * **Not decrypted.** The probe table's `body_shape` column reads "keys ['data', 'lastModified', 'response']" because the script's check predates the new key; the check was fixed afterwards and the table was not re-requested.
* **Rewrites [observed; inference on cause].** Files for 2025 matches carry Last-Modified dates of 26 May–5 Jun 2026. Rally, key stats and Court Vision files for 2026 matches are rewritten weeks after the match (Queen's rally on 17 Sep; Canada key stats on 28 Sep). This agrees with the 24 Sep note that files are regenerated, and presumably re-keyed, over time [inference].
* **Terms (plain fact, from the 24 Sep lane):** atptour.com's terms prohibit "Systematic retrieval of data"; Infosys terms not stated.

## B5. Sackmann

* **Repository status on 29 Sep 2026 [observed]** (GitHub API and `HEAD https://github.com/JeffSackmann/<repo>`):

  | Repository | Status |
  |---|---|
  | `tennis_atp` | 404 |
  | `tennis_wta` | 404 |
  | `tennis_slam_pointbypoint` | 404 |
  | `tennis_pointbypoint` | 404 |
  | `tennis_MatchChartingProject` | **200** |

  * The JeffSackmann account lists 1 public repository.
* **Match Charting Project [observed]:** `master` is `1813a1309b7ed7ebf1c7e884b32bf675d00e4edf` ("thru 18 sep 2026", committed 2026-09-18T08:35:54Z), the commit the project holds; **no later commit.** Of its 138 listed forks, only NicolaiSchmid/tennis_MatchChartingProject was pushed on or after 18 Sep, at the same instant as upstream (a mirror sync).
* **The mirror the project used [observed, receipts and sidecars]:**
  * GitHub `Aneeshers/tennis-sackmann-archive` at commit `83733587353df8a41f2fd4f516147d5aa83f5a8d`, fetched 22 Sep 2026 (`data/raw/public_dump/sackmann_archive/_receipts.jsonl`; `data/dump/matches/sackmann_archive/*.meta.json`). Its one commit is dated 2026-06-25T23:35:33Z.
  * Its README [provider claim]: Slam point-by-point from upstream `6febb77` (Oct 2024); atp and wta "from upstream commits made in June 2026"; CC BY-NC-SA 4.0.
  * Its 10 forks all carry the same push time (2026-06-25T23:38:51Z).
  * The Hugging Face twin `Aneeshers/tennis-sackmann-archive` was last modified 2026-06-25.
  * **Nothing newer exists in the mirror family.**
* **Other copies [observed]:**
  * **GitHub code search:** `atp_matches_2026.csv` is in 24 repositories (10 distinct blobs), `wta_matches_2026.csv` in 7 (3 blobs). The two blobs with rows after the mirror's last date (25 May 2026) are not Sackmann's:
    * `davidpiontransactions-eng/pariscore`: Tennis My Life format with ATP codes, to 14 Jun 2026, tour level only;
    * `MitroulisDimitris/SportsPredictor`: a 22-column derivative, to 23 Aug 2026.
  * **No search hit for** `atp_matches_futures_2026.csv`, `atp_matches_qual_chall_2026.csv` or `wta_matches_qual_itf_2026.csv`. [caveat] GitHub code search skips large files, so this is not proof of absence.
  * **Hugging Face:** 11 searches found no Sackmann-derived dataset modified after 2 Jun 2026 apart from the Aneeshers twin. `clarkkitchen22/Tennis-ATP-Dataset` (8 May 2026) is a chat-format conversion of `tennis_atp` with 1,169 rows of 2026, older than the mirror.
  * **Kaggle:** no Sackmann mirror updated after June.
* **tennisabstract.com (2 requests) [observed]:**
  * Requests: `wplayer.cgi?p=SamiraDeStefano` (200), then its data file `https://www.tennisabstract.com/jsfrags/SamiraDeStefano.js` (200, 104,879 bytes, Last-Modified 29 Sep 2026 17:43 GMT).
  * The file lists ITF results after June: W50 Horb (20 Jul 2026), W75 Hechingen (27 Jul), W50 Hamburg (10 Aug), W75 Kursumlijska Banja (17 Aug). Also WTA 125s to Tolentino (21 Sep).
  * [inference] Sackmann still compiles ITF results; they are no longer published on GitHub. One player only.
* **Lead for `itf_after_june_2026` (women only) and `women_itf_qualifying`: Kaggle `bwandowando/womens-tennis-association-matches-1975-present`.** This comes from a scratch check; nothing was staged in the project.
  * **The dataset [observed]:** version 29, updated 2026-09-24T01:36:50Z; label "Apache 2.0". Its description [provider claim] says it is built from the WTA website (wtatennis.com), per player, with pseudo match and tournament ids. `matches.csv` has 278,480,366 bytes (SHA-256 `310177ac…528b`), 1,409,422 rows and 862,445 distinct matches. `tournaments.csv` has 15,957 rows, with dates and a `level` field (ITF 14,578).
  * **Women's ITF singles, ISO weeks 27–38 of 2026** (the map's missing window): **4,695 main-draw and 3,153 qualifying matches.** Weekly main-draw counts are 489–565 in July, 334–395 in August and 539 in week 36. Week 37 is partial (55) and week 38 absent. Rows with `reason_code` B, D, UNP or V are left out, read as byes, walkovers and unplayed [inference]. Main draw and qualifying come from `qpm_flag` M/Q [inference: its round counts fit 32-draw main events plus qualifying draws].
  * **Against the map's estimate:** the map estimates 5,123 missing women's ITF main-draw matches for those weeks.
  * **Coverage check, weeks 2–22 of 2026, where Sackmann's women's ITF main draws are held:** 6,479 of the map's 6,708 matches (96.6%) are found in the file (both surnames, ±7 days of the tournament start). The file lists 8,583 main-draw matches for those weeks. Why it holds 28% more than the map is [not determined].
  * **Men's ITF after June 2026:** no source found in this lane.
  * **Where the files are:** downloaded to the session scratchpad (`laneB/bwando/`); check script `laneB/bwando_check.py`.

## B6. Other public point-by-point for WTA 2018 or ATP tour level 2025–26

* **Kaggle [observed]** (17 searches: point by point, sofascore, flashscore, pbp, wta point by point, tennis 2026, momentum, wta 2018 …):
  * marcosjn2 (B1) is the only tour-level point source for these periods.
  * Otherwise:
    * the Live Tennis API sample (known);
    * colinparker (2011–17, a Sackmann copy);
    * Wimbledon 2023 and 2024 derivatives;
    * result and odds datasets (dissfya daily ATP/WTA, alimoh89, oliviersportsdata);
    * bwandowando's WTA results (B5).
* **GitHub [observed]:**
  * **SofaScore scrapes:** Soheilkehavarz/TennisProject, kimia2328 ("February 1 to March 31, 2024"), ChiefOmid ("60 days") and shahabnajmosadatypy are course projects over a short 2024-type window. [inference] Their window is the one kimia2328 states; the others were not opened.
  * **Copies:** crowe32996/tennis-point-by-point and izzy-brown hold Sackmann copies. livetennisapi/livetennisapi-data is a stub.
* **Hugging Face [observed]:** outragest/tennis-momentum-pbp is Sackmann's `tennis_pointbypoint` files. The momentum datasets are Wimbledon 2023 derivatives. `livetennisapi/tennis-match-outcome-studies` and ramizheman/TennisNLData are known.
* **Zenodo [observed]** (10 searches):
  * record 23018680, the Live Tennis API public sample v1.0.2 (2026-09-28; index to 2026-08-13; points sample June 2026; CC BY-NC 4.0), the product the project already holds;
  * 16888520, a 915 KB xlsx with Slam-feed fields;
  * 21233132, a 14 KB xlsx.
  * Nothing for WTA 2018 or ATP 2025–26.
* **Conclusion:** for `wta_2018_points` the only public source found is marcosjn2 (1,377 matches). The rest of WTA 2018 (mostly qualifying and WTA 125, plus about a third of main draws) has no public point source. [observed within these searches; not exhaustive]

## Files written

* **Notes:** this file.
* **Tables:**
  * `data/studies/gap_sources/marcosjn2_gap_links.csv` (3,955 rows) and `marcosjn2_summary.json`;
  * `sirgenkii_matches.csv` (1,294 rows) and `sirgenkii_summary.json`;
  * `atp_statscentre_probe.csv` (20 rows).
* **Scripts** (`src/eda/gap_sources/`): `fetch_marcosjn2.py`, `marcosjn2_links.py`, `fetch_sirgenkii.py`, `sirgenkii_matches.py`, `probe_atp_statscentre.py`.
* **Raw, gitignored:** `data/raw/gap_sources/marcosjn2/` (263.6 MB, 2 files plus metadata and receipts) and `data/raw/gap_sources/sirgenkii/` (34.4 MB dumps plus references and code, with a receipt).
* **Scratchpad only:** the request log (`laneB/probe_log.tsv`), the bwandowando files and check, the Slam cross-check prototype, and one saved MatchBeats body (ciphertext, not decrypted).

## Requests made (29 Sep 2026, UTC)

| Host | Requests | Detail |
|---|---|---|
| www.kaggle.com | 34 | view, list and download redirects (302), paced ≥2.2 s; all 200/302 |
| storage.googleapis.com (Kaggle files) | 7 | two full marcosjn2 files, three bwandowando files, two 5–6 KB range reads |
| huggingface.co API | about 55 | |
| GitHub API (`gh`) | about 100 | including about 20 search calls |
| github.com | 5 | HEAD requests |
| itp-atp-sls.infosys-platforms.com | 21 | |
| www.tennisabstract.com | 2 | |
| zenodo.org | 16 | three were 400 for an over-limit page size |

No 429s, challenges or CAPTCHAs were met. The four Infosys 403s were missing-object responses (XML).
