# Filling the data map's gaps: downloads

**Status: data collection, not a selection.** Started 29 September 2026 with the ATP tour-level gap. The [gap-sources research](../../research/gap-sources/README.md) proposed a source list for each of the [data map](../../../data/data_map.html)'s eight gaps; this study downloads them, one gap at a time, in the order proposed. Nothing here approves a dataset, model or venue.

## ATP tour-level point by point, 2025 to June 2026

The gap (`atp_points_2025` in [data_map.yaml](../../../data/data_map.yaml)) is 3,778 ATP tour-level singles matches of 2025 to June 2026 (Finals, 1000s, 500s, 250s and their qualifying) held only as box scores on 25 September 2026. The research proposed two sources:

| Order | Source | What the research measured | Status on 30 Sep 2026 |
|---|---|---|---|
| 1 | **SofaScore**, listed tournament by tournament | Complete points for 34 of 36 sampled matches, box scores for 34; about 3,570 of the gap | Downloaded: every point for 3,777 of the 3,778 matches (3,753 complete), box scores for 3,777 |
| 2 | **SirGenkii/infotennis**, a GitHub fork's MySQL dumps of decrypted ATP Stats Centre files | Point outcomes (winner, forced or unforced error) for 715 gap matches of December 2024 to April 2025 | Downloaded, hash-checked and staged; fills the 715 |

**The gap on the map fell from 3,778 to 3** (build of 30 September, 18:04 UTC). One is a match SofaScore has no record of, Kitzbühel 2025, Rinderknech v Hanfmann. The other two are a match the map holds twice under two spellings of a name, whose other row has the points.

### SirGenkii/infotennis (done)

`src/ingest/public_dump/sirgenkii_infotennis.py` downloads the repository at its head commit `ec1b188` (11 April 2025; the dumps date from `1bb7527`, 7 April 2025) and stages each dump as a table.

* **Downloaded [observed]:** 13 files, 34.5 MB, in 13 seconds: the six dumps plus the README, licence, config, player table and the three API notes. Every file matches the pinned git tree's blob SHA-1, and each dump is byte-identical to the research copy in `data/raw/gap_sources/sirgenkii/`.
* **Staged [observed]:** 239,526 rows, every value kept as dumped text.

  | Table | Rows | Columns | What a row is |
  |---|---:|---:|---|
  | `atp_results` | 1,343 | 18 | A match: event, round, players with ATP ids, score |
  | `atp_rally_analysis` | 136,928 | 29 | A point: server, serve 1 or 2, how it ended, serve speed and direction, rally-length bucket, score |
  | `atp_stroke_analysis` | 87,976 | 15 | A player's winners and errors by stroke, per set |
  | `atp_court_vision` | 6,992 | 47 | A tracked stroke: hit, net, bounce and peak positions (8 matches) |
  | `atp_key_stats` | 6,264 | 44 | A player's box score per set, with winners and unforced errors |
  | `atp_calendars` | 23 | 13 | An event: dates, category, surface |

* **Checked [observed]:** the research session's own parser (`src/eda/gap_sources/sirgenkii_matches.py`) reads the same row counts from its copy, and the same values in every cell. The only differences are 2,071 Court Vision coordinates dumped as `-0`, which it reads as 0.
* **In the map [observed, measured 29 Sep 2026]:** the results table's 1,343 rows are 1,286 played singles matches once the United Cup doubles rubbers and the unplayed matches (no score) are left out. 922 carry points.
  * *Placement:* 1,284 of the 1,285 in the map's window land on known matches, 1,280 of them by ATP tournament and player ids, as the Infosys copy is joined. The one left over, Tseng v Holmgren in the 2025 Australian Open qualifying, joins as a new match.
  * *The gap:* 715 of its 3,778 matches get every point with its outcome, as the research counted. That leaves 3,063 for SofaScore.
  * *On the page:* the map built at 22:08 UTC shows the gap at 3,063. The build at 21:46 UTC had shown 3,070, because it predated the fix that leaves 7 unplayed matches out.

### SofaScore (done)

`src/ingest/point_sources/sofascore_editions.py` is the by-tournament mode that the research found missing from the SofaScore adapter ("needs a by-tournament listing mode"). The player adapter lists one career at a time; this one works from the gap itself:

1. **Targets.** The gap's 3,778 matches, frozen at the first run in [sofascore_atp_points_2025_matches.csv](../../../data/studies/gap_downloads/sofascore_atp_points_2025_matches.csv). Once the map is rebuilt with what the run collects, the gap shrinks, so the list is not derived again unless asked (`--refresh-targets`).
2. **Editions.** The targets fall in 112 tournament editions (tour, tournament, year, ISO week).
3. **Locate.** SofaScore's day listing of the ATP category on a few days of the edition's week. The tournament season whose events name the most of the edition's known matches is taken. This is the method of the research probe, which located 9 of 9 sampled editions.
4. **List and link.** Every event of that season, qualifying included. Each target links to the singles event whose players both share a name word with it, 10 days before to 21 after the tournament start. Two refinements came from the session linking the Australian Open and Roland Garros gap:
   * A name with no word of three letters or more (Li Tu) uses its two-letter words.
   * When a pair met twice at one event, in the qualifying and again in the main draw, the event in the target's own draw is taken.
5. **Fetch.** The point-by-point record of every linked event, newest first, then every box score. If SofaScore blocks part-way, the points are what the run has.

**The first run was refused [observed].** At 21:40 UTC on 29 September, SofaScore answered HTTP 403 "challenge" to the first request and to its retry a minute later. That was nearly four hours after it had blocked the research probe (17:54 UTC). The run stopped as the collection rules require, after 2 requests, and froze the targets. The plain client was still refused on 30 September at 14:56 UTC (HTTP 403, now "Forbidden").

**The download [observed].** 30 September, 15:10 to 18:01 UTC, in browser mode, through the Chrome window the owner had opened for the Australian Open and Roland Garros session. The two sessions took turns, never running at once.
* *Requests:* 7,867: 313 to locate and list the 112 editions, then 3,777 point records and 3,777 box scores. There were 2 retries, no challenge and no token renewal.
* *Listing:* all 112 editions located; all 3,778 targets linked, to 3,776 events. The two events linked twice are the map's duplicates (next list).
* *Records:*

  | Point record | Targets |
  |---|---:|
  | Complete: every set has the score's games | 3,679 |
  | Complete to a retirement (the game in progress also listed) | 74 |
  | Short: games missing | 12 |
  | Other: the games fall differently from the score | 9 |
  | No score to compare with (SofaScore lists none) | 3 |
  | No record (HTTP 404) | 1 |

  "Other" is judged against SofaScore's own score, which can be wrong. At Båstad 2025 (Ugo Carabelli v van de Zandschulp) the listing says 7-6 5-4, but the record's 34 games are those of the official 7-6 5-7 6-3.
* *Box scores:* 3,777 of 3,778; 3,760 with the full serve and return set.
* *Staged:* 4,995 events (every event of the 112 tournaments), 464,721 point states and 226,347 statistics rows.
* *No record at all:* Kitzbühel 2025, Rinderknech v Hanfmann (neither points nor box score).

**The links, checked against the official result [observed].** `src/eda/gap_downloads/verify_links.py` rebuilds the links offline and compares each event with Tennis My Life's row for the same match, qualifying and main draw kept apart:

| Verdict | Targets |
|---|---:|
| Same winner and the same games in every set | 3,768 |
| Same winner; SofaScore lists no score (retirements early in the match) | 3 |
| Same winner; the score differs (Båstad, above) | 1 |
| No official row: the map's six matches taken from Sackmann | 6 |
| A different winner | 0 |

Two of the six Sackmann rows repeat a Tennis My Life match under another spelling:
* Humbert v Oconnell (Rotterdam 2026);
* Bu Yunchaokete v Albert Ramos (Monte-Carlo qualifying 2025).

Each links to its twin's event, and the map credits the Tennis My Life row. Two pairs met twice at Basel 2025, in the qualifying and again in the main draw: Opelka v van de Zandschulp, and Cilic v Goffin. Each of their four matches links to its own event.

## SofaScore by edition: seven more gaps (work package P6)

**Status: done, 8 October 2026 19:36 UTC to 12 October 14:18 UTC.** [Work package P6](collection-plan.md#p6-sofascore-in-chrome-challengers-tour-level-wta-2018) ran the same adapter over seven more gaps of the map, in the plan's order, inside the Chrome tab the owner opened (browser mode).

**In all [observed]:**
* *Targets:* 51,241 distinct matches (446 are in two gaps); 47,871 linked.
* *Points:* every point for 30,680, 30,134 of them complete to the score. Box scores for 15,814, in the first three gaps.
* *Links:* about 99% of the links that can be checked agree with the official winner and every set.
* *Requests:* about 70,500 reached SofaScore.
* *Incidents:* one challenge, which cleared by itself in 26 minutes; a Chrome window that closed and was reopened a day later.
* *Coverage:* SofaScore's records are near complete for Challengers of 2024-26 and for most tour-level main draws. They are thin for qualifying at every level, and almost absent for Challengers from spring 2022 to the end of 2023. P5's TennisLive pages hold most of what SofaScore lacks.
* *The timeline:* `refresh.py --sources sofascore` ran at the end (12 Oct, 14:23-14:30 UTC; every step exited 0).
  * The timing linker (`src/eda/match_timing/srcc_sofascore.py`) now reads every gap's per-match file as prior links, keyed by gap and map uid; before, it read the ATP gap's alone.
  * It linked 108,433 of 111,213 SofaScore singles events in scope to Stage 0. The adapter's links agree with its own for 48,732 events and differ for 46, and they added 8 links it could not make.
  * The check tested 483,136 matches: 0.046% of their known days fall outside their windows, 0.011% after them.

| Order | Gap | Targets | Editions | What it is | Status |
|---|---|---:|---:|---|---|
| 1 | `challenger_points_2025` | 14,675 | 673 | Challengers and their qualifying, 2025-26 | Done, 9 Oct 18:41 UTC: every point for 14,601 |
| 2 | `wta125_points_2019_2026` (new) | 377 | 91 | WTA 125s and their qualifying, 2019-26 | Done, 9 Oct 19:29 UTC: every point for 213 |
| 3 | `tour_points_rest` (new) | 1,216 | 360 | Tour-level and Slam main draws of 2019-26 still without points | Done, 10 Oct 01:58 UTC: every point for 1,025 |
| 4 | `challenger_points_2022_2024` (new) | 5,781 | 1,208 | The Challenger matches of 2022-24 the Infosys copy has no points for | Done, 11 Oct 17:59 UTC: every point for 1,931 (SofaScore has none for most of 2022-23) |
| 5 | `atp_points_2018_2020` | 2,685 | 184 | ATP tour level and qualifying, 2018-20 | Done, 11 Oct 19:49 UTC: every point for 881 (773 of 911 main-draw) |
| 6 | `wta_2018_points` | 2,079 | 82 | WTA tour level, WTA 125s and their qualifying, 2018 | Done, 11 Oct 21:29 UTC: every point for 553 (359 of 541 tour main-draw) |
| 7 | `challenger_points_2018_2021` | 24,874 | 951 | Challengers and their qualifying, 2018-21 | Done, 12 Oct 14:18 UTC: every point for 11,885 |

"Editions" are the adapter's: tour, tournament name, year and week of the map's date.

**How it is run, and where it departs from the plan [observed]:**
* **The new gaps** were added under `gaps:` in data_map.yaml before the first request, with the plan's selects. On the map of 8 Oct (16:34 UTC) their sizes equal the plan's: 5,781, 377 and 1,216.
  * `tour_points_rest` is not quite what the plan describes. 446 of its matches are ATP matches of 2019-20 that are also in `atp_points_2018_2020`; the receipts mean they are fetched once. 288 are WTA matches of 2019, 102 of them before the WTA's point log starts on 1 April. About 160 are from the Tokyo, Beijing and Seoul events of late September 2026.
  * `wta125_points_2019_2026`: 147 of its 377 are from January-March 2019 (Indian Wells 125K, Newport Beach, Guadalajara), and 143 from 2025-26.
* **All seven target lists were frozen at the start** (19:43 UTC), from that one map build, instead of at each gap's first run. Otherwise the later gaps would be frozen days later, perhaps after P5 has given many of the same Challenger and WTA 2018 matches TennisLive's partial records. The map counts those as "point", so they would hide the matches from SofaScore's complete records. The map's reader of these lists (`sofascore_edition_uids` in `src/eda/data_map/measure.py`) now accepts a list frozen before its first run.
* **The trial budget is 150 requests, not 60.** The first gap's three newest editions have 20 targets each, so 60 requests would have run out before any box score was asked for.
* **Pace:** the plan's 2 s plus up to 1 s of jitter. The faster pace is the owner's call and was not used.
* **The link check now reads both result files the map is built from.** `verify_links.py` compared links only with Tennis My Life's ATP rows of 2025-26. It now reads every Tennis My Life and Sackmann file from 2018 on, Tennis My Life's row first where both hold the match, and names the file used (`official`).
  * Re-run on the ATP gap (in memory, files unchanged), it gives the same verdict for all 3,772 Tennis My Life matches, and the 6 Sackmann matches that had no official row now agree too.
  * Targets taken from other files (API-Tennis, the WTA's lists and website, a Slam's draws) stay "no official row", with their source in `creator`.
  * A new verdict, "SofaScore lists no winner", separates SofaScore's records without a winner (winner code 3, or none) from a real "winner differs".
* **Three linking fixes, found by the first gap's link check** (in `sofascore_editions.py`, with tests; they apply to every later gap):
  * *Played before cancelled.* SofaScore also lists matches that never took place, at times beside the same pair's played match a day or a round later. On a tie of names, the played event is now taken.
  * *A shared first name is not enough.* A target is left unlinked when its event shares more name words with another of the edition's known matches: the event is that match's, and the target's own is not listed. Re-run on the ATP gap (in memory), this would unlink one target, the Sackmann twin of Bu Yunchaokete v Albert Ramos; its Tennis My Life twin keeps the event, so the map is unchanged.
  * *The week before.* Tennis My Life dates some Challengers a week late. An edition not found in its own week is now looked for 3 and 5 days before its date; editions found in their own week never get that far.
  * *The winner, when a pair met twice* (found by the third gap's check). At the Finals a pair can meet in the round robin and again in the final. On a tie, the event the target's winner won is now taken; Tennis My Life's and Sackmann's rows name the winner first. It changed two links of the third gap, and none of the first two.
* **The link check treats a default (DEF) like a retirement**, so SofaScore's unstarted 0-0 set no longer counts as a different score.
* **Tried and not adopted: requiring each player's surname** (11 Oct 2026). It was meant to stop borrowed events, where a target whose match SofaScore lacks takes an event of one of its players against an opponent who shares only a first name (9 in gap 4). Re-linked offline over the first five gaps, it would have removed about 30 such links but lost about 150 correct ones:
  * SofaScore shows a player's current name on old matches, so married and changed names share only a first name (Jaksic now Jovic, Rueffer now Papadakis, Andrei now Paar, Cias now Juszczak);
  * other names are ordered or spelt differently (Sanhui Shin; "B. Yunchaokete").

  Linking stays as it was. The link check reports borrowed events as a different winner or score, gap by gap.
* **Since 14 Oct 2026, links that fail both tests are refused** ([the follow-up study](../p6_data_issues/README.md#1-borrowed-links-fixed)). A link is refused when no surname matches *and* the official result disagrees: 47 links, 26 in gap 4 and 21 in gap 7, each read by hand. They are listed in `data/studies/gap_downloads/sofascore_link_vetoes.csv`, which the adapter reads. Gaps 4 and 7 were re-linked offline. The link check now also drops an unplayed 0-0 set on either side, and all eight link checks were re-run. The gap sections below give the counts of 9-12 Oct; the follow-up study gives the re-checked ones.
* **A closed Chrome window now stops the run** (`browser.py`; `common.Client` lets the stop through). Gap 4's first run lost its browser between 04:17 and 04:26 UTC on 10 Oct. It then recorded every request as failed ("Target page, context or browser has been closed"), about one every 50 seconds, for 34 hours, until it was stopped by hand on 11 Oct at 14:16 UTC. None of those requests reached SofaScore, and the next run asks for each again. Now a tab closed on its own is replaced by a new one on the site, and a closed window stops the run with "Blocked".
* **Chrome was reopened on 11 Oct (14:17 UTC) with three more flags**, which keep it from slowing or freezing the tab when its window is hidden: `--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows`. They change nothing SofaScore sees. Gap 3's run had lost 2.8 hours to a frozen tab. The command is under [browser mode](#running-it).

### challenger_points_2025

**Trial [observed]**, 19:36-19:42 UTC, 127 requests, no challenge:
* *Editions:* the three newest, Challengers being played this week (Braga, Antofagasta and the Ferrero Challenger at Villena, 5 Oct 2026). All three were located from one day listing (category 72, 7 Oct).
* *Links:* 60 of 60 targets.
* *Points:* 58 complete, 1 complete to a retirement, 1 short by a game (Heide v Zeitune, Antofagasta).
* *Box scores:* 60 of 60, all full.
* *Against Expected:* the plan's sample of 2025-26 had every point for 31 of 32 and a box score for 32 of 32.

**The download [observed].** 8 Oct 19:42 UTC to 9 Oct 18:30 UTC (22.8 hours), then two short re-runs (18:35-18:41 UTC) that applied the linking fixes above.
* *Requests:* 30,140: the trial's 127, the bulk run's 29,940 (7 retries) and the re-runs' 73. The listing took 901 of them (195 day listings, 706 season pages).
* *The block:* at 13:49 UTC on 9 Oct, after 24,505 requests in 18 hours (about 1,360 an hour), SofaScore answered a challenge. The tab showed SofaScore's check page, "Access denied. Verification failed, please refresh the page to try again", with no box to click. The adapter reloaded the tab, clearing the site's cookies and storage every 5 minutes. A fresh token appeared at 14:15 UTC (1,530 s), and the run carried on by itself. There was no other challenge.
* *Links:* 671 of 673 editions located; 14,608 of 14,675 targets linked.
* *Records:*

  | Point record | Targets |
  |---|---:|
  | Complete: every set has the score's games | 14,203 |
  | Complete to a retirement (the game in progress also listed) | 282 |
  | Short: games missing | 83 |
  | Other: the games fall differently from SofaScore's score | 26 |
  | No score to compare with (SofaScore lists none) | 7 |
  | No record (HTTP 404) | 7 |
  | Not linked | 67 |

* *Box scores:* 14,592 of 14,675; 14,541 with the full serve and return set.
* *By year:* 2025, every point for 9,675 of 9,745 targets; 2026, for 4,926 of 4,930.
* *Staged:* every event of the located seasons with the ATP gap's (22,532 events), 2,214,259 point states and 1,092,164 statistics rows.

**Not linked [observed]:** 67 targets.
* *Nottingham 2025 (31):* Tennis My Life (event 2025-2907) dates the January Challenger 7 July, the week of "Nottingham 3". SofaScore lists its matches in January (two checked).
* *Manama 2025 (31):* Tennis My Life's "Manama" (2025-9635) is dated 24 November, the week of Manama 2, which is a separate edition that linked. No Manama tournament is in SofaScore's Challenger listings of 3-21 November, so this edition was not found.
* *5 others:* Brisbane 2 (3), Newport (1), and Gima v Hernandez Serrano at Costa do Sauipe (1; see the linking fixes).

**The links, checked against the official result [observed]:**

| Verdict | Targets |
|---|---:|
| Same winner and the same games in every set | 14,572 |
| Same winner; the score differs (SofaScore's listed score; e.g. Bunschoten, Kicker v Moeller 7-5 6-4, listed 4-1) | 14 |
| Same winner; SofaScore lists no score (early retirements) | 12 |
| SofaScore lists no winner (winner code 3 at retirements and abandoned matches; one suspended at Bordeaux) | 7 |
| A different winner: Hersonissos 3, Fellin v Rosenkranz, a retirement SofaScore credits to Rosenkranz | 1 |
| No official row: two matches the map took from the SofaScore careers | 2 |
| Not linked | 67 |

One SofaScore event is linked by two targets: Bertrand v Azoidis at Hersonissos 4, which the map holds twice, under two spellings and two tournament names.

**On the map [observed]**, rebuilt at 18:43 UTC on 9 Oct: the Challenger cells of 2025-26 hold 20,074 matches, 19,531 of them (97%) with point data. All 18,295 SofaScore records inside the map's window were placed through the adapter's links. 543 matches are still below point:
* *145 of the targets:* the 67 not linked, the 7 without a record, and about 71 of this week's matches. Those are held, but dated after the map's window, which ends on Sunday 4 October.
* *398 that joined the map after the lists were frozen:* 381 from P4's TennisLive listings (results only) and 17 from Tennis My Life's latest files. They are not targets. A later pass could collect them: their editions' listings are already cached, so about 800 requests.

### wta125_points_2019_2026

**The download [observed].** 9 Oct, 18:43-19:29 UTC: 971 requests (two trials of 14 and 88, the run's 869), no challenge. SofaScore files the WTA 125s under their own category, "WTA 125" (id 871); the map's loader now reads it (`SOFASCORE_TOUR` in `src/eda/data_map/measure.py`), or it would have dropped every record.
* *The first trial located none of its three editions*, and it was not a fair sample. The gap's newest editions are the map's rows from the WTA website records (the Kaggle copy, version 29), and those of September 2026 name the wrong players for their tournaments. In SofaScore's listing, Valencia's WTA 125 of 14 September was played by Kawa, Lazaro Garcia, Bennemann and others. The map's ten Valencia matches are Adkar v Zhang, Nishimura v Sato, Johnson v Gao and the like, and no WTA 125 listing that week names them. They look like ITF matches the file's pseudo-tournament ids put under WTA 125 titles; P2, which refreshes these records, should check them.
* *A second trial over the 16 newest editions* reached seven of Sackmann's: all located, and all 13 of their targets linked. With the July editions from the WTA website, 18 of 18 targets in located editions linked, 17 complete, all 18 with full box scores. The bulk run followed.
* *Links:* 84 of 91 editions located; 312 of 377 targets linked.
* *Records:* every point for 213 (205 complete, 3 complete to a retirement, 2 short, 3 other); no record (HTTP 404) for 99; not linked 65. Box scores: 170 (169 full).

  | Year | Targets | Linked | Every point | No record |
  |---|---:|---:|---:|---:|
  | 2019 | 157 | 149 | 66 | 83 |
  | 2020 | 13 | 12 | 5 | 7 |
  | 2021-2024 | 64 | 64 | 56 | 8 |
  | 2025 | 54 | 54 | 54 | 0 |
  | 2026 | 89 | 33 | 32 | 1 |

  The 2019 events are the WTA 125K series of January-March (Newport Beach, Indian Wells 125K, Guadalajara): SofaScore lists them but has no point record for 78 of their matches. Qualifying rarely has one in 2019-2023 (1 of 30).
* *Not linked:* 65. 55 are the September 2026 matches from the WTA website records above (six editions). The other 10:
  * six of Sackmann's matches that the located seasons do not list: four at the 2019 125Ks, one at Prague 2020, one in Mumbai's 2026 qualifying;
  * four from the WTA's lists, which name no tournament.

**The links, checked against the official result [observed]:** all 300 linked targets that have an official row (Sackmann's) agree on the winner and every set. The other 12 linked targets come from the WTA's lists (4) or website records (8), which the check does not read. Three events are each linked by two targets: Badosa's three matches at Guadalajara 2019, which the map holds twice (Sackmann's row and the WTA lists' row with no tournament name).

**On the map [observed]**, rebuilt at 19:31 UTC on 9 Oct: the WTA 125 cells of 2019-2026 hold 8,853 matches, 203 of them below point (92 in 2019, 80 in 2026, at most 8 in any other year).

### tour_points_rest

**The download [observed].** 9 Oct 19:31 UTC to 10 Oct 01:49 UTC, then a re-link (01:56-01:58 UTC) that applied the winner rule. 3,477 requests: the trial's 74, the run's 3,399 (2 retries) and the re-link's 4. Box scores were fetched, as planned for the first three gaps. There was no challenge.
* *Stalls:* from 20:33 UTC the tab stalled 24 times for more than a minute, 2.8 hours in all (the longest 29 minutes); gap 1 had none in 22.8 hours. During one, the SofaScore page did not answer a fresh DevTools connection either, while Chrome sat almost idle. Each stall ended by itself, or when the window was brought forward; which one is not known. Other sessions' model fits kept about 60% of the machine's 16 threads busy.
* *Trial:* Beijing and Tokyo 2026: 32 of 32 targets linked, 30 complete, all with full box scores.
* *Links:* 347 of 360 editions located; 1,112 of 1,216 targets linked.
* *Records:*

  | Point record | Targets |
  |---|---:|
  | Complete: every set has the score's games | 852 |
  | Complete to a retirement | 91 |
  | Short: games missing | 70 |
  | Other | 10 |
  | No score to compare with | 2 |
  | No record (HTTP 404) | 87 |
  | Not linked | 104 |

* *Box scores:* 1,052 (1,019 full).
* *By tour and year:*

  | Tour, years | Targets | Every point | Complete |
  |---|---:|---:|---:|
  | ATP 2019-20 | 447 | 409 | 385 |
  | ATP 2021-26 | 366 | 310 | 266 |
  | WTA 2019 | 288 | 207 | 196 |
  | WTA 2020-26 | 115 | 99 | 96 |

**Not linked [observed]:** 104.
* *92 in 13 editions not located:*
  * the 2023 Asian Games (34, from API-Tennis), which are not in SofaScore's ATP listings of their weeks;
  * WTA list rows of 2019 with no tournament name (25);
  * Bucharest 2019 (25): SofaScore's WTA listings of that week name only Wimbledon, Gstaad's qualifying and Lausanne;
  * two WTA 2026 editions from the WTA website records (7: Guadalajara, Sao Paulo);
  * one row of the Slam point archive with no tournament name.
* *7 left unlinked by the rule against borrowed events:* each is a second row the map holds for a match it also holds under better names.
  * Five are API-Tennis rows that call a qualifying match main draw; Rinderknech v Gutierrez at Båstad 2021, for one, is a qualifying first round.
  * The other two are Sackmann's O'Connell v Ramos (Geneva 2022) and API-Tennis's Hsu v de Minaur (Australian Open 2023).
* *5 more:* their editions were located, but their seasons do not list them.

**The links, checked against the official result [observed]:**

| Verdict | Targets |
|---|---:|
| Same winner and the same games in every set | 1,088 |
| Same winner; the score differs (SofaScore adds a set at Hobart and Nanchang 2019; the Next Gen Finals' short sets) | 3 |
| Same winner; SofaScore lists no score | 2 |
| No official row (the WTA's lists 7, Slam draws 4, the Slam point archive 3, API-Tennis 2, the WTA website records 2, the Australian Open's Wayback copy 1) | 19 |
| Not linked | 104 |

Before the winner rule, the finals of the ATP Finals of 2021 (Zverev v Medvedev) and 2023 (Djokovic v Sinner) had taken the same pair's round-robin event: two "a different winner" verdicts, now gone. One event is linked by two targets: Gauff v Kozlova at Linz 2019, which the map holds twice (Tennis My Life's row and the WTA website's).

**On the map [observed]**, rebuilt at 02:02 UTC on 10 Oct: the tour-level and Slam main draws of 2019-2026 hold 37,635 matches; 236 are below point (WTA 2019: 82; ATP 2023: 36, 34 of them the Asian Games; WTA 2026: 33; no other year above 22).

### challenger_points_2022_2024 (points only)

**The download [observed].**
* *First run:* 10 Oct 01:51-01:55 UTC (trial, 24 requests), then the run from 01:59 UTC. It made 1,928 good requests (listings) before the Chrome window closed at about 04:20 UTC; see the closed-window fix above.
* *Second run:* 11 Oct 14:18-17:59 UTC, 5,198 requests, 1 retry, no challenge. It asked again for everything that had failed.
* *Links:* 1,204 of 1,208 editions located; 5,264 of 5,781 targets linked.
* *Box scores:* not asked for (`--skip statistics`).
* *Trial:* Noumea and Nonthaburi, January and December 2024: 17 of 18 targets linked, all 17 complete.

**SofaScore has no Challenger point records from spring 2022 to the end of 2023 [observed].**

| Year | Targets | Linked | Every point |
|---|---:|---:|---:|
| 2022 | 2,140 | 1,889 | 56 (all in January-March) |
| 2023 | 1,588 | 1,498 | 1 |
| 2024 | 2,053 | 1,877 | 1,874 |

* *Records:* every point for 1,931 (1,820 complete, 71 complete to a retirement, 9 short, 17 other, 14 with no score to compare); no record (HTTP 404) for 3,333; 517 not linked.
* *Not a fault of the run:* it fetched the newest first, and its answers run 200 through 2024, then 404 for 2,384 requests in a row through 2023 and 2022, with 200s again in early 2022. The ten careers' own SofaScore records, collected in September, show the same hole: points for 3 of their 408 Challenger matches from April 2022 to December 2023, against 306 of 308 in 2024 and 52 of 80 in 2021.
* *Against Expected:* the research's "99%" came from the careers' 2024 matches only.
* *What fills it:* P5's TennisLive pages (running at the same time) hold 2,029 of the 2,088 targets of 2022 that SofaScore lacks and 1,499 of the 1,587 of 2023. The map counts those as point data, though TennisLive usually lacks the set-closing games.

**The links, checked against the official result [observed]:**

| Verdict | Targets |
|---|---:|
| Same winner and the same games in every set | 4,755 |
| Same winner; the score differs | 62 |
| Same winner; SofaScore lists no score | 12 |
| SofaScore lists no winner | 8 |
| A different winner | 16 |
| No official row (API-Tennis 400, Infosys 6, the SofaScore careers 5) | 411 |
| Not linked | 517 |

* *9 of the 16 different winners are borrowed events:* the target's match is not in SofaScore's listing, and an event of one of its players whose opponent shares only a first name took its place. For example, Musetti v Gigante (Forli 2022) took Angelini v Arnaldi through "Lorenzo" and "Matteo", and Ficovich v Heide (Brasilia 2023) took Heide v Juan Pablo Paz. The rest are records that disagree (retirements) or a pair that met twice in nearby weeks (Nottingham had two Challengers in June 2022).
* *190 SofaScore events are each linked by two targets:* the map holds those matches twice, mostly an API-Tennis row beside Sackmann's (55 pairs) or Tennis My Life's (16), and some rows of Tennis My Life beside Sackmann's under two tournament names (13).

**On the map [observed]**, rebuilt at 18:09 UTC on 11 Oct: the Challenger cells of 2022-2024 hold 29,580 matches; 232 are below point (91 in 2022, 108 in 2023, 33 in 2024).

### atp_points_2018_2020 (points only)

**The download [observed].** 11 Oct, 18:00-19:49 UTC: 2,444 requests (the trial's 9, the run's 2,435), no retry, no challenge. It had no stall, the first run since Chrome was reopened with the flags against background throttling. All 184 editions were located; 2,669 of 2,685 targets linked. The 446 targets shared with `tour_points_rest` came from the cache.

| | Targets | Linked | Every point | Complete |
|---|---:|---:|---:|---:|
| Main draws 2018-2020 | 911 | 911 | 773 | 738 |
| Qualifying 2018-2020 | 1,774 | 1,758 | 108 | 99 |

* *Main draws* have every point for 85% (2018: 364 of 465; 2019: 300 of 322; 2020: 109 of 124), as the research expected ("mostly").
* *Qualifying* was unmeasured. SofaScore lists the matches but has a point record for 6% of them, and P5's TennisLive pages hold most of the rest.
* *Not linked:* 16, all qualifying: 3 at Doha and 12 at Pune in 2019, and 1 at Hamburg 2020.

**The links, checked against the official result [observed]:** 2,665 of 2,669 agree on the winner and every set. In three more, SofaScore adds an unplayed 0-0 set to a finished match (Miami 2018, Eastbourne and Basel 2019). In one (Gstaad 2018), the official result is a walkover that SofaScore lists without a score. No link has a different winner, and no event is linked twice.

**On the map [observed]**, rebuilt at 19:54 UTC on 11 Oct: ATP tour level of 2018-2020 has point data for 4,966 of 5,106 main-draw matches and 2,052 of 2,103 qualifying matches.

### wta_2018_points (points only)

**The download [observed].** 11 Oct, 19:49-21:29 UTC: 2,288 requests (the trial's 57, the run's 2,231), no retry, no challenge, no stall. 76 of 82 editions were located; 2,004 of 2,079 targets linked.

| | Targets | Linked | Every point | Complete |
|---|---:|---:|---:|---:|
| Tour-level main draws (Finals, 1000, 500, 250) | 541 | 508 | 359 | 344 |
| WTA 125K main draws | 286 | 279 | 155 | 152 |
| Qualifying (tour and 125K) | 1,252 | 1,217 | 39 | 38 |

* *Main draws* fall short of the research sample, 344 of 541 complete against 19 of 22. These are the matches the SofaScore copy on disk (marcosjn2) lacks, which may be a harder set [inference].
* *Qualifying* is listed by SofaScore, as the research found, but rarely has a point record (39 of 1,217).
* *Not located (6 editions):*
  * Bucharest, where SofaScore's WTA listings name no Bucharest event in 2018 or 2019;
  * the Pan Pacific Open (Tokyo), Kunming (Anning) and Zhengzhou, from the WTA website records;
  * two WTA list editions with no tournament name.

**The links, checked against the official result [observed]:** 1,987 of 2,004 linked targets agree on the winner and every set, 6 differ in score, none in winner. The other 11 come from the WTA website records (10) or lists (1), which the check does not read. Two events are each linked by two targets, matches the map holds twice (Mallorca 2018, for one).

**On the map [observed]**, rebuilt at 21:35 UTC on 11 Oct: WTA 2018 has point data for 1,960 of 1,963 tour-level main-draw matches, 1,147 of 1,178 qualifying matches and 423 of 440 WTA 125K matches. Most of what SofaScore lacks, P5's TennisLive pages hold.

### challenger_points_2018_2021 (points only)

**The download [observed].**
* *Trial:* 11 Oct 21:29-21:34 UTC, 78 requests, on Maia 2 and Rio de Janeiro (December 2021). 70 of 70 targets linked, 54 with every point.
* *Run:* 11 Oct 21:34 UTC to 12 Oct 14:18 UTC, 23,957 requests, 2 retries, no challenge, no stall.
* *Links:* 942 of 951 editions located; 22,348 of 24,874 targets linked.

| Year | Main draw: targets | Linked | Every point | Qualifying: targets | Linked | Every point |
|---|---:|---:|---:|---:|---:|---:|
| 2018 | 4,951 | 4,446 | 2,068 | 3,622 | 3,579 | 125 |
| 2019 | 7,202 | 6,656 | 4,029 | 265 | 253 | 113 |
| 2020 | 2,255 | 2,011 | 1,699 | 385 | 341 | 31 |
| 2021 | 4,690 | 3,562 | 3,289 | 1,504 | 1,500 | 531 |

* *Records:* every point for 11,885 (11,415 complete, 206 complete to a retirement, 254 short, 10 other); no record (HTTP 404) for 10,463; 2,526 not linked.
* *Against Expected:* main draws of 2019-2021 have every point for 9,017 of 12,229 linked targets (74%), the careers' figure for 2019-21. 2018's main draws reach 47% of linked targets (the careers: 13 of 49 in 2018). Qualifying rarely has a point record (800 of 5,673 linked), as at every level in P6.

**Not linked [observed]:** 2,526.
* *2,425 in located seasons that do not list them.* In 2021 most come from venues that held several Challengers in a row, which Tennis My Life lumps under one name and date. For example, six Biella events of 2021 (ids 2021-9434, -9466, -9470, -9496, -9498 and -9503) are all "Biella 1" dated 14 February; Oeiras, Antalya, Forli, Prague and Nur-Sultan are similar. Only the first event of each run is located, and the later events' matches fall outside the link window: about 1,100 targets of 2021.
* *63 in 9 editions not located:* Bangkok 2018 and 2019, Aix-en-Provence, Iasi and Prostejov 2020, and four in Australia and New Caledonia (2019).
* *38 left unlinked by the rule against borrowed events.*
* *Already covered:* on the rebuilt map, 2,384 of the 2,528 unlinked targets have point data, nearly all from P5's TennisLive pages. Searching later weeks for the lumped events would mostly add the set-closing games TennisLive lacks, so it was not built.

**The links, checked against the official result [observed]:**

| Verdict | Targets |
|---|---:|
| Same winner and the same games in every set | 22,096 |
| Same winner; the score differs | 106 |
| Same winner; SofaScore lists no score | 3 |
| SofaScore lists no winner | 11 |
| A different winner (borrowed events, or records that disagree) | 43 |
| No official row (API-Tennis 84, Infosys 4, the SofaScore careers 1) | 89 |
| Not linked | 2,526 |

168 SofaScore events are each linked by two targets: matches the map holds twice.

**On the map [observed]**, rebuilt at 14:22 UTC on 12 Oct: the Challenger cells of 2018-2021 have point data for 19,596 of 19,953 main-draw matches and 5,864 of 6,244 qualifying matches. SofaScore gave 11,885 of the gap's matches every point; P5's TennisLive pages hold most of the rest.

### Running P6 again

All seven gaps are done; nothing is running. A rerun asks only for what is missing or failed, across gaps too: every answer is on disk with its receipt.

Any gap run again gets a trial, the run (rerun it if it ends on its budget), the link check and the map rebuild. Gaps 4-7 are **points only** ([the plan's change of 9 Oct 2026](collection-plan.md#p6-sofascore-in-chrome-challengers-tour-level-wta-2018), step 3: Stage 0 already holds a box score for about 99% of their matches). A rerun of them must keep `--skip statistics`; without it, it would ask for every box score it skipped.

```
./python.sh -m src.ingest.point_sources.sofascore_editions --gap <gap> --browser --skip statistics --limit 3 --max-requests 150 --min-interval 2.0 --jitter 1.0
./python.sh -m src.ingest.point_sources.sofascore_editions --gap <gap> --browser --skip statistics --max-requests 40000 --min-interval 2.0 --jitter 1.0
./python.sh src/eda/gap_downloads/verify_links.py --gap <gap>
./python.sh src/eda/data_map/build.py
```

At the end: `./python.sh src/eda/match_timing/refresh.py --sources sofascore`. Logs go to `data/raw/point_sources/sofascore_editions/_logs/` (`> <log> 2>&1`).

## SofaScore by edition: ITF (work package P7)

**Status: running since 12 October 2026 (trials 14:58 UTC; bulk from 13 October, 01:26 UTC).** [Work package P7](collection-plan.md#p7-sofascore-in-chrome-itf-2025-2026-then-itf-2018-2024) runs the same adapter over the map's ITF main draws, inside the Chrome tab the owner opened (browser mode). It goes newest first, gap by gap, and fetches points and box scores (no `--skip statistics`).

| Order | Gap | Targets | Editions | What it is | Status |
|---|---|---:|---:|---|---|
| 1 | `itf_points_2025_2026` (new) | 63,334 | 2,338 | ITF main draws of 2025-26 without point data | Done but the deferred, 15 Oct 00:10 UTC: every point for 19,411 (18,944 complete); 35,309 deferred |
| 2 | `itf_detail` | 207,045 | 7,550 | ITF main draws of 2018-24 with only a result | Running again from 27 Oct at the plan's pace (sixteenth run from 23:00 UTC on 28 Oct, after a PC restart), after a block (24 Oct ~22:55 UTC, SofaScore's captcha page, caused by a VPN switched on mid-run) and 2.5 days' rest. Ran from 15 Oct 00:47 UTC; every point record asked by 22 Oct ~09:20 UTC (194,772 of 201,141 events with one); box scores since |

**How it is run, and where it departs from the plan [observed]:**
* **It started after P6 had finished** (12 Oct, 14:18 UTC), and after P6's map rebuild (14:22 UTC) and timing refresh (14:23-14:30 UTC). P4's listings were already on the map, so the ITF matches TennisLive listed since June 2026 are targets.
* **The new gap** `itf_points_2025_2026` was added under `gaps:` in data_map.yaml with the plan's select. It holds 63,334 matches on the map of 14:22 UTC on 12 Oct, against 55,416 on 8 Oct; the difference is mostly TennisLive's listings since June 2026.
  * *By the file the map took them from:* Sackmann 49,255 (2025 to early June 2026); TennisLive's listings 7,600 (men, June to September 2026); the WTA website records 6,448 (women, June to September 2026); the ITF live-data API 30; SofaScore's careers 1.
  * *By year:* 2025, 38,831; 2026, 24,503. Only 770 are from September 2026 and 30 from October: from the week of 14 September the map already has point data for nearly every ITF match (2,732 of 2,786 to 11 October).
* **Both target lists were frozen at the start** (14:57 UTC), from that one map build, as in P6. `itf_detail` holds 207,045, against 205,872 on 8 Oct.
* **Gzipped evidence.** The per-match and link-check tables of both gaps are `.csv.gz` (`GZIPPED` in the adapter); at about 300 bytes a row, they would be about 60 MB each otherwise. Four readers now accept them:
  * the adapter's `load_targets`;
  * `verify_links.py`;
  * the map's `sofascore_edition_uids` (`src/eda/data_map/measure.py`);
  * the timing linker's `gap_links` (`src/eda/match_timing/srcc_sofascore.py`), which the plan did not name.
* **Staging is streamed.** The adapter's `stage()` writes each table to Parquet as it reads the raw files, instead of gathering every row in memory first; the ITF gaps will hold tens of millions of point rows. Re-run over P6's raw files, it gave the same three tables, every column but the staging time, in 83 s.
* **The bulk runs pass `--no-stage`.** Staging runs once after each gap (`--stage-only`), beside the link check and the map rebuild.
* **Trials at chosen editions.** A new `--editions` option names the editions to try (keys as in the editions table). That way two of each trial's three editions are at the weekly venues, Monastir and Antalya, as the plan asks.
* **Pace:** the plan's 2 s plus up to 1 s of jitter. The faster pace is the owner's call and was not used.
* **Detached runs.** The bulk runs are started through WMI (`Win32_Process.Create`), outside the job object of the Claude Code session that starts them, so that they outlive the session. An hourly check by that session reruns a run that has ended.
* **Stalls under load, and the fix (13 Oct).**
  * *The stalls:* from about 15:40 UTC the run slowed from about 24 requests a minute to under half, with gaps of up to five minutes, without an error or a refusal. Other sessions' analysis scripts (about a dozen Python processes) held the machine's CPU at 100%.
  * *The cause:* Chrome ran every renderer of the scraping profile at **Idle** priority, the SofaScore tab's among them, despite the three flags against backgrounding. Under full load, an Idle process gets almost no CPU.
  * *The fix:* at 16:49 UTC the profile's Chrome processes and the adapter's Python process were raised to AboveNormal. The run went back to about 25 requests a minute at once. The collector needs little CPU, so the other sessions lose almost nothing.
  * *It does not last:* Chrome lowers its renderers again by itself, and new renderers start low. By the next hourly check five processes were below AboveNormal again, and the run had stalled once for 15 minutes (16:58-17:12 UTC). The rest of that hour it ran at about 24 requests a minute.
  * *The watchdog:* since 17:48 UTC, `src/ingest/point_sources/keep_tab_priority.ps1` raises them again every 15 seconds. It acts on the scraping profile's Chrome processes and the adapter's Python processes only, logs each change to `_logs/keep_tab_priority.log`, and stops by itself after seven days. It is started detached, like the runs:

    ```
    pwsh -NoProfile -File src/ingest/point_sources/keep_tab_priority.ps1
    ```

### Trials [observed]

**`itf_points_2025_2026`**, 12 Oct, 14:58-15:07 UTC, 194 requests, no challenge:

| Edition (map's date) | The map's file | Targets | Linked | Every point | Box score |
|---|---|---:|---:|---:|---:|
| M15 Monastir (7 Sep 2026) | TennisLive's listings | 31 | 31 | 31 | 31 |
| W35 Antalya (23 Feb 2026) | Sackmann | 31 | 31 | 0 | 0 |
| WTT W35 Reus (7 Sep 2026) | The WTA website records | 30 | 30 | 30 | 30 |

* *Located:* each edition from one day listing of its own week (category 785 men, 213 women). Their SofaScore seasons have 2-3 pages and 31-73 events.
* *Links:* 92 of 92 targets, against the plan's stop line of 80%.
* *Points:* 59 complete, 1 complete to a retirement, 1 other.
* *W35 Antalya 4 (February 2026):* SofaScore lists all 31 of its matches, but holds no point record and no statistics for any (HTTP 404).
* *Box scores are a reduced set in 2026.* All 61 hold the same 11 items:
  * aces and double faults;
  * points won: in all, on serve, on return, most in a row;
  * service games won, and most games in a row;
  * return points won against first and second serves, as "24/61";
  * break points converted.

  First serves in and won follow from the opponent's return items. Break points faced and saved do not, except from the point record. The adapter's "full box score" needs the first-serve items, so it counts 0 of 61.

**`itf_detail`**, 12 Oct, 15:08-15:19 UTC, 194 requests, no challenge:

| Edition (map's date) | SofaScore's season | Targets | Linked | Every point | Full box score |
|---|---|---:|---:|---:|---:|
| M15 Monastir (25 Nov 2024) | Tunisia F60, Singles | 30 | 30 | 30 | 30 |
| W15 Antalya (16 Dec 2024) | Antalya, Singles Main, W-ITF-TUR-33A | 31 | 31 | 31 | 31 |
| M15 Doha (16 Dec 2024) | Doha, Singles Main, M-ITF-QAT-04A | 31 | 31 | 31 | 31 |

* *Points:* 90 complete, 2 complete to a retirement.
* *Box scores:* all 92 hold the full 19 items, as the research found for 2018-24.
* *Located:* Monastir held an M15 and an M25 that week; the M15's season was taken (19 of its known matches named). The seasons have 2-3 pages and 55-88 events, within the adapter's cap of 25 pages.

**Against Expected:**
* *2018-24* (the research: box scores for about 98%, complete points for about 93%): the trial reached 92 of 92 in both.
* *2025-26* was unmeasured. The trial linked 92 of 92 (stop line 80%), with records for two editions of three.

**The links, checked against the official result [observed]** (`verify_links.py`, 15:19-15:20 UTC):
* *2024:* 92 of 92 agree on the winner and every set.
* *2026:* the 31 Sackmann targets (Antalya) agree. The other 61 are "no official row": they come from TennisLive's listings and the WTA website records, which the check does not read.

### ITF qualifying [observed]

The plan asks for a separate qualifying gap only if most of the trial editions' qualifying events carry points. `src/eda/gap_downloads/itf_qualifying_probe.py` (15:19-15:24 UTC, 125 requests, no challenge) took the played qualifying singles of the six trial editions from their season listings on disk, at most 30 per edition, and asked for their point records.

| Edition | Qualifying matches SofaScore lists | Asked | Every point | Complete |
|---|---:|---:|---:|---:|
| M15 Monastir 2026 | 23 | 23 | 8 | 8 |
| WTT W35 Reus 2026 | 24 | 24 | 8 | 4 |
| W35 Antalya 2026 | 0 | 0 | 0 | 0 |
| M15 Monastir 2024 | 24 | 24 | 8 | 5 |
| M15 Doha 2024 | 24 | 24 | 24 | 22 |
| W15 Antalya 2024 | 56 | 30 | 11 | 11 |
| **All** | | **125** | **59 (47%)** | **50** |

* **No qualifying gap was added**: fewer than half carry points, against 153 of 184 for the same editions' main draws.
* SofaScore also lists only part of each qualifying draw: about 24 matches for most editions, while the map holds 46-129 qualifying matches in the same tournaments' weeks.
* The map holds about 70,000 ITF qualifying matches of 2025-26 and 204,000 of 2018-24, nearly all below point.
* Evidence: `data/studies/gap_downloads/itf_qualifying_probe.json` and `.csv`.

### itf_points_2025_2026: the download (done but the deferred)

**The first run [observed]**, 13 Oct, 01:26-22:27 UTC (budget 30,000):
* *Listing:* 2,338 editions listed by about 04:50 UTC (4,908 requests). 62,727 of 63,334 targets (99.0%) linked to 62,677 events.
* *Point records,* newest first: 24,000 of 62,677 asked for. 19,395 have a record, and 4,605 are absent (HTTP 404), all of those from February 2026 back.
* *Stopped by hand* at 22:27 UTC, after about 28,830 requests, once the owner chose to defer the flagged events (below). Its evidence tables were not rewritten; the next run rewrites them from the cache.

**SofaScore has no ITF point records before March 2026 [observed for February; inference for the rest].**
* *The break:* every match from early March 2026 on has a record (April to August 2026: about 99%). From 19:46 UTC the run met February 2026, and since then every answer has been HTTP 404, 1,471 in a row. These are SofaScore's own JSON answers from its API, not a block page.
* *The flag:* SofaScore's listings carry `coverage: -1` on almost every ITF singles event from January 2025 to February 2026 (3,455 of 3,455 in March 2025; 2,193 of 2,239 in February 2026), and on almost none from March 2026. Exceptions: May 2025 (2,874 of 3,780 flagged) and June 2025 (1,917 of 3,953).
* *How reliable it is:* across every event fetched in P6 and P7, an event flagged `coverage: -1` had a point record 8 times in 1,403. The flag does not mark every hole, though: P6's Challenger hole of 2022-23 carries no flag.
* *The cost:* about 40,000 of the gap's targets are from January 2025 to February 2026. Asking for their points and box scores, as the plan does, takes about 80,000 requests (about 2.3 days at the plan's pace), almost all answered 404.
* *The 2024 trial* (`itf_detail`) had every point and the full box score for 92 of 92, so the hole looks like 2025 to February 2026 only.

**Nothing more at SofaScore [observed]** (`src/eda/gap_downloads/sofascore_uncovered_probe.py`, 13 Oct 22:30 UTC, 28 requests, no challenge). It asked six flagged events (January, March, July and October 2025; January and February 2026) and two unflagged events with points (March and April 2026) for four of SofaScore's per-event endpoints:
* *Point records:* 0 of 6 flagged events (HTTP 404).
* *The event's own record* says no more than the listing: `coverage: -1`.
* *The momentum series* (`/tennis-power`) answers, but empty, for all eight, the controls included.
* *Statistics:* 2 of the 6 flagged events have some, but only six items: aces, double faults, service points won, service games won, and the longest runs of points and games. Sackmann's box scores already hold more for 2025.
* Evidence: `data/studies/gap_downloads/sofascore_uncovered_probe.json`.

**Deferred, on the owner's word (13 Oct 2026).**
* *The option:* the owner chose to leave the flagged events until the end of P7. The adapter's `--defer-uncovered` does not ask for events SofaScore lists with `coverage: -1`. Their per-match rows say "deferred (coverage -1)", and the summary counts them under `points_deferred`.
* *The order now:* the rest of `itf_points_2025_2026`, then `itf_detail`, then one last run of this gap without the option, which asks for the deferred events. Whether to make that last run is the owner's call; it costs about 80,000 requests and would add few records.
* *The second run* started at 22:33 UTC with the option.
* *A restart:* Windows Update restarted the PC on 14 Oct at 07:29 and 07:33 UTC, which killed the second run, the Flashscore run (P13) and the priority watchdog. The owner reopened the SofaScore Chrome window at 13:54 UTC. A third run with the same command started at 14:06 UTC and resumed from the receipts.

**The result [observed]**, 15 Oct 00:10 UTC (the third run's end, exit 0), with no block over the three runs:

| | Targets |
|---|---:|
| Linked to a SofaScore event | 62,727 of 63,334 |
| Every point listed | 19,411 (18,944 complete to the score) |
| No point record (HTTP 404) | 8,007 |
| Deferred (flagged `coverage: -1`; asked at the end of P7, if kept) | 35,309 |
| A box score (the reduced 11-item set of 2026; 6 items on some 2025 events) | 23,378 |

* *The link check* (`verify_links.py`, 15 Oct 00:48 UTC) covers every linked target, deferred ones included: it reads the event's listed result.
  * 48,253 agree on the winner and every set, 191 differ in score, 49 name another winner, 324 have no winner on SofaScore, and 6 no score.
  * 13,904 have no official row: TennisLive's listings 7,561, the WTA website records 6,318, the ITF live API 25. 607 are not linked.
  * 100 SofaScore events are each linked by two targets: matches the map holds twice.
* *Staged* (`--stage-only --defer-uncovered`, 00:52-01:02 UTC): every event of the located seasons with P6's (203,219 events), 6,346,036 point rows and 1,407,110 statistics rows.
* *On the map* (rebuilt 01:02-01:04 UTC): the ITF matches from 1 March 2026 have point (or shot) data for 24,698 of 26,224 (94%). 2025 has almost none, 398 of 39,114, in SofaScore's hole. Flashscore (P13) fills most of it.
* *The timeline* (`refresh.py --sources sofascore`, 01:04-01:15 UTC; every step exited 0): the linker read 210,518 SofaScore singles events and linked 160,314 to Stage 0, against 108,433 before. Of the 45,045 it left unlinked, 42,731 are ITF events (men 24,681, women 18,050), and 43,193 in all have no Stage 0 match with both players in the window (`data/studies/match_timing/links/sources_c_summary.json`).
* *Twins:* 136 matches of January 2025 to February 2026 appear twice in one SofaScore season, one copy flagged and one not. The run asks only the linked copy. The 15 unflagged copies asked so far had no record either, so the rule was not changed.

**Elsewhere, so far [observed, 13 Oct 2026]:**
* *The ITF live-data API* (P1's host) serves statistics and points for a 2025 match by its id: 5 of 6 sampled in the research had both. But nothing found lists 2025 match ids.
  * Its day list keeps only 14 days.
  * Its generic resources stop at the match: `match/<id>` answers for a 2025 match, while `round/`, `draw/`, `event/` and filtered lists answer 404. The `include` options cannot reach a draw's other matches, and no API description is served (`openapi.json`, `openapi.yaml` and `docs` answer 404).
  * Probe: 12 requests. Five were made by `src/eda/gap_downloads/itf_stadion_probe.py`, with receipts (evidence in `itf_stadion_probe.json`). Seven follow-ups read the refusal's text and looked for a description; they were made without receipts, and their answers were seen only in the session.
* *itftennis.com* (P12's route) was read from inside a Chrome tab with its own profile and port (9223). Its calendar and event filters answered: a week of May 2025 lists its 2025 event keys, and W75 Zagreb's numeric id came back. Its draw sheet, the one call that might carry the match ids, got HTTP 403 from Imperva three times. The probe stopped there, as the plan says: 5 requests to the site, the draw sheet's three attempts included (`itf_site_probe.py`; evidence in `itf_site_probe.json`). The window was closed afterwards.
* *The ITF API's court listing* (`custom/matchesByCourt/<id>`, named in its widget library) answered 404 for a 2025 event, without a date and with one (2 requests, with receipts).
* *Flashscore is the lead* ([research note](../../research/gap-sources/itf_2025_points.md)).
  * *The live site:* its point feed held complete records for the 4 checked matches of 2025-26 that have a match duration in the handoff copy, and nothing for the 4 without one. A record has the server, the score after each point and break-point flags, but no ace or double-fault codes.
  * *The copy on disk:* it holds no points, but it gives Flashscore match ids for 40,847 of the window's 42,876 targets.
  * *The estimate:* about 28,400 targets with complete points (93% to June 2025, 45% from July), at one request each, about 30 hours [inference from 8 checks; a trial should measure it].
  * *The rest:* TennisLive (P8) would add partial points for most of what Flashscore lacks, except in January 2025.
  * *Paid feeds* seem to cover about the same matches as Flashscore.

### itf_detail: the download (running)

**The first run [observed]**, 15 Oct, 00:47-21:47 UTC (budget 30,000; it stopped at the budget, exit 1, with no block):
* *Listing:* 7,550 editions listed by about 12:55 UTC (about 17,300 requests). 202,253 of 207,045 targets (97.7%) linked to 201,141 events. None is flagged `coverage: -1`, so `--defer-uncovered` defers nothing in this gap.
* *Point records,* newest first: 12,500 of the 201,141 events asked, back to 19 August 2024. 12,525 targets have a record (98.6% of those asked), and 176 are absent (HTTP 404).
  * *Against the score:* 12,166 complete, 154 complete to a retirement, 159 short, 33 other, 13 with no score to compare.
* *Box scores* come after every point record, as in P6: 92 so far, the trial's.
* *Pace:* about 1,410 requests an hour once the listing was done.

**The second run** started at 21:53 UTC with the same command (log `run_20261015T215358Z_itf_detail.log`). It replays the listing from the receipts without a request. It was started by hand: the watcher meant to restart the run at its budget looked for the Flashscore client's wording of a budget stop, not this adapter's ("request budget of 30000 used up"), and stood down. The run sat idle for 6 minutes. The next watcher accepts both wordings.

**After the second run [observed]** (it used its budget and ended at 19:01 UTC on 16 Oct, with no block; a watcher started the third run at once, log `run_20261016T190139Z_itf_detail.log`):
* *Point records:* 42,500 of the 201,141 events asked, back to 23 October 2023. 42,445 targets have a record (98.6% of those asked), and 594 are absent.
  * *Against the score:* 41,186 complete, 609 complete to a retirement, 478 short, 149 other, 23 with no score to compare.
* *Where the absent ones are:* mostly the first days of particular tournaments, not whole tournaments. Only 8 of the 1,623 tournaments asked lack every record (23 targets). At W25 Santo Domingo (November 2023), for example, all 31 matches of the first two rounds are absent and 11 of the last 15 have a record. The absent answers are SofaScore's own JSON 404s, in runs of neighbouring event ids.

**The Chrome window closed (16 Oct, about 23:00 UTC) [observed].** The third run stopped then, with "the Chrome window with the debugging port was closed", after 48,100 events had been asked. It was not a block. The scraping profile wrote its settings at 23:00:16 and left no crash report, so Chrome closed cleanly: by hand, or by Chrome itself (an update had been installed the night before and was waiting for a restart). The session reopened the window at 23:11 UTC with the command below (same profile, the three flags), started minimised, and launched the fourth run at 23:12 UTC (log `run_20261016T231210Z_itf_detail.log`).

**After the fourth run [observed]** (it used its budget and ended at 20:23 UTC on 17 Oct, with no block; a watcher started the fifth run at once, log `run_20261017T202340Z_itf_detail.log`): point records asked for 77,800 events, back to 10 October 2022. 77,804 targets have a record (98.7% of those asked; 76,379 complete), and 1,043 are absent. 11 of the 2,933 tournaments asked lack every record (56 targets).

**A challenge, and the window closed again (17 Oct) [observed].** At 23:07 UTC, after 3,702 requests of the fifth run, SofaScore answered with its challenge: HTTP 403, reason "challenge", the refusal that asks the page for a fresh token. It was the first since P6's of 8 October. The adapter reloaded the tab and waited for the token, as designed; no check was detected in the page. At 23:09:11 UTC Chrome closed, cleanly again, and the run stopped after 81,800 events.
* *Around it:* Windows logged configuration-change events, COM permission errors and a DNS time-out at 23:07:55-23:08:17. A network change would explain both the challenge and the timing [inference]. The closure of 16 October had no such events, and no scheduled task runs at either time.
* *Resumed:* the session reopened the window at 23:24 UTC, shown without focus rather than minimised, so the site's check can run in a visible page, and started the sixth run (log `run_20261017T232427Z_itf_detail.log`). SofaScore accepted it without a check.

**After the sixth run [observed]** (it used its budget and ended at 20:36 UTC on 18 Oct, with no block; a watcher started the seventh run at once, log `run_20261018T203706Z_itf_detail.log`): point records asked for 111,200 events, back to 13 September 2021. 111,091 targets have a record (98.4% of those asked; 107,465 complete), and 1,808 are absent.

**The window closed a third time (19 Oct, 14:20 UTC) [observed].** The seventh run stopped then, after 137,100 events, with no challenge before it: the last answer, at 14:20:23, was a record, and Chrome wrote its settings at 14:20:27 and left no crash report. Five seconds earlier, the priority watchdog had found the tab's renderer raised from Idle to Normal, which Chrome does when its window comes to the front [observed]; so the window was most likely brought forward and closed by hand [inference]. The run then sat idle for about 22 hours: the session's check-ins did not run, and the PC restarted at 04:18 UTC on 20 Oct, which also ended the watchdog.
* *After the seventh run:* 138,243 targets asked, back to 25 November 2019. 135,859 have a record (98.3%; 130,717 complete), and 2,384 are absent.
* *Resumed (20 Oct, 12:51 UTC), at the owner's word ("continue downloading the sofascore itf data"):* the window reopened minimised (Chrome 155.0.8059.85, updated by the restart), the watchdog restarted for 14 days (`-Hours 336`), and the eighth run started (log `run_20261020T125101Z_itf_detail.log`).

**After the eighth run [observed]** (it used its budget and ended at 10:13 UTC on 21 Oct, with no block; a watcher started the ninth run at once, log `run_20261021T101330Z_itf_detail.log`): 168,242 targets asked, back to 21 January 2019. 164,302 have a record (97.7%; 158,555 complete), and 3,940 are absent. The share absent grows in the older seasons, about 6-7% of the matches asked in 2019.

**After the ninth run [observed]** (it used its budget and ended at 07:30 UTC on 22 Oct, with no block; a watcher started the tenth run at once, log `run_20261022T073108Z_itf_detail.log`): 192,131 targets have a record (185,663 complete), 6,125 are absent (about 8% of the 2018 matches asked), and 3,997 are not yet asked. The tenth run finishes the point records, then starts the box scores: about 201,000 requests, about 6 days.

**After the tenth run [observed]** (it used its budget and ended at 04:48 UTC on 23 Oct, with no block; a watcher started the eleventh run at once, log `run_20261023T044917Z_itf_detail.log`):
* *Point records, all asked:* 195,871 targets have one (189,340 complete), and 6,382 are absent.
* *Box scores,* asked for 25,300 events so far: 26,215 targets have one, 26,177 of them the full set. About 99% of those asked have one.

**After the eleventh run [observed]** (it used its budget and ended at 02:07 UTC on 24 Oct, with no block; a watcher started the twelfth run at once, log `run_20261024T020752Z_itf_detail.log`): box scores asked for about 55,300 events; 56,242 targets have one, 56,161 of them the full set.

**A block (24 Oct) [observed].** At 20:40 UTC, after 25,414 requests of the twelfth run, SofaScore began answering with its challenge (HTTP 403, reason "challenge"). The adapter reloaded the tab and waited for a fresh token, clearing the site's cookies and storage every 5 minutes, for an hour; then once more. No token came, and no check was detected in the page. At about 22:55 UTC the run stopped, "HTTP 403 (challenge) ... after 3 attempts", the plan's stop on a block (exit 1 at 23:03). The tab was then on SofaScore's own captcha page (`www.sofascore.com/captcha.html`).
* *By then:* box scores for 82,296 targets (82,150 the full set), every point record, nothing lost. Left: box scores for about 119,000 events, about 3.5 days at the plan's pace.
* *The one earlier challenge* (P6, 8 Oct) cleared by itself 25 minutes after the reload. This one did not clear in 2 hours.
* *Not rerun:* the plan's rule is to stop and report on a challenge, and a captcha is not the session's to pass.

**Resumed after a rest (27 Oct) [observed].** The session reported three options and recommended resting, then testing; the owner answered "continue" on 27 Oct. By then no request had gone to SofaScore for 2.5 days, and the Chrome window had been closed.
* *Reopened:* the window was reopened with the same profile, and it showed the normal page, not the captcha.
* *Tested:* a test run of 20 requests at a slower pace, 3 s + up to 2 s, had every request answered (14:01-14:02 UTC, log `run_20261027T133109Z_itf_detail_test.log`).
* *Restarted:* the thirteenth run started at 14:30 UTC at that pace (log `run_20261027T143015Z_itf_detail.log`).
* *Left [inference from the pace]:* about 118,500 box scores at about 900 requests an hour, about 5.5 days, so about 2 November.

**The block's cause, and back to the plan's pace (27 Oct) [owner's statement].** The owner: "It stopped and challenged because I started VPN while the process was running, not because of our pace". So the slower pace was not needed. The thirteenth run was stopped at 14:55 UTC, after 195 requests (all answered), and the fourteenth started at 14:55 UTC at the plan's 2 s + up to 1 s (log `run_20261027T145507Z_itf_detail.log`).
* *Left [inference from the pace]:* about 118,300 box scores at about 1,400 an hour, about 3.5 days, so about 31 October.
* *The challenge of 17 Oct* fits the same cause [inference]: it came in the same minute as a burst of Windows network-configuration events (above).

**After the fourteenth run [observed]** (it used its budget and ended at 12:49 UTC on 28 Oct, with no block; a watcher started the fifteenth run at once, log `run_20261028T124937Z_itf_detail.log`): box scores asked for about 112,800 events; 112,571 targets have one, 112,130 of them the full set. About 0.8% of the run's requests were absent (SofaScore's 404), none refused.
* *Left [inference from the pace]:* about 88,300 box scores at about 1,400 an hour, about 2.7 days, so about 31 October.

**The PC restarted (28 Oct, 21:17 UTC) [observed].** The fifteenth run stopped then, after about 12,000 requests (box scores asked for about 124,800 events), with no block before it: its last answer, at 21:17:33 UTC, was a box score. Windows records the restart as started from the Start menu by the PC's user ("Other (Unplanned)"). It also closed the Chrome window and the priority watchdog.
* *The network after it:* NordVPN's app starts with Windows (from 21:19 UTC), but its three network adapters stayed disconnected and the traffic went through the home Wi-Fi as before. So the download's network was unchanged.
* *Resumed (22:59-23:00 UTC):* the session reopened the window minimised (the normal page, no check showing), restarted the watchdog for 14 days (`-Hours 336`), and started the sixteenth run (log `run_20261028T230036Z_itf_detail.log`). The restart cost about 1.7 hours.
* *Left [inference from the pace]:* about 76,300 box scores, about 2.3 days, so still about 31 October.

**Left [inference from the pace]:** about 188,600 point records after the first run, then about 201,000 box scores: about 390,000 requests, or about 11.5 days, so about 27 October if nothing stops it. The second run kept to that pace.

### Running and resuming P7

A run stops at its budget of 30,000 requests (about a day), on a block, or when the Chrome window closes. Rerunning the same command resumes: every answer is on disk with its receipt, and nothing is asked twice. Run from the repository root in Git Bash. Now, gap 2, at the plan's pace (2 s + up to 1 s; a slower 3 s + up to 2 s was used for 25 minutes on 27 Oct, until the owner gave the block's cause, below):

```
./python.sh -m src.ingest.point_sources.sofascore_editions --gap itf_detail --browser --max-requests 30000 --min-interval 2.0 --jitter 1.0 --no-stage --defer-uncovered > data/raw/point_sources/sofascore_editions/_logs/run_<UTC stamp>_itf_detail.log 2>&1
```

**Do not change the PC's network during a run** (a VPN on or off, another connection). SofaScore's access check is tied to the address it was passed from; a change mid-run brings its challenge, as on 24 Oct (below). Stop the run first, change, then reopen the window and resume.

Gap 1 ran the same command with `--gap itf_points_2025_2026`. `--defer-uncovered` leaves the flagged events for the end (above). The last run of P7, if the owner keeps it, is gap 1's command without it.

When a run ends with every target fetched (the log's last `point-by-point` and `statistics` lines reach their totals with no `STOPPED`), finish the gap:

```
./python.sh -m src.ingest.point_sources.sofascore_editions --gap itf_detail --stage-only
./python.sh src/eda/gap_downloads/verify_links.py --gap itf_detail
./python.sh src/eda/data_map/build.py
./python.sh src/eda/match_timing/refresh.py --sources sofascore
```

Gap 1's after-steps ran on 15 Oct (above). Never run two map builds or two timing refreshes at once.

The trials, for the record:

```
./python.sh -m src.ingest.point_sources.sofascore_editions --gap itf_points_2025_2026 --browser --editions "M|M15 Monastir|2026|w37" "W|W35 Antalya|2026|w09" "W|WTT W35 - REUS, SPAIN|2026|w37" --max-requests 300 --min-interval 2.0 --jitter 1.0
./python.sh -m src.ingest.point_sources.sofascore_editions --gap itf_detail --browser --editions "M|M15 Monastir|2024|w48" "W|W15 Antalya|2024|w51" "M|M15 Doha|2024|w51" --max-requests 300 --min-interval 2.0 --jitter 1.0
./python.sh src/eda/gap_downloads/itf_qualifying_probe.py --browser --per-edition 30 --max-requests 250
```

### Limits of P7 so far

* **SofaScore's 2026 ITF box scores are a reduced set** (11 items). They count against Stage 0's official ITF box scores only on the items they share: aces, double faults, first serves in and won, second serves won, and break points converted.
* **Whole editions can lack records.** One of the three 2025-26 trial editions had neither points nor statistics. The bulk run will measure how common that is.
* **The link check cannot vouch for about 14,000 targets of 2026** that come from TennisLive's listings and the WTA website records. It reads only Tennis My Life's and Sackmann's files.
* **The new readers of gzipped tables** are tested offline (`test/gap_downloads`, `test/data_map`, `test/match_timing/test_link_sources_c.py`). They will first read real ITF links at the first map rebuild and timing refresh after gap 1.

## Flashscore point feeds: ITF January 2025 to February 2026 (work package P13)

**Status: done, 14 October 2026 01:09 UTC to 15 October 15:57 UTC.** [Work package P13](collection-plan.md#p13-flashscore-point-feeds-itf-january-2025-to-february-2026) was added at the owner's word after P7 found SofaScore empty for these months. It asks Flashscore's point feed of each ITF main-draw target of the window, by the match ids of the Flashscore copy on disk ([research](../../research/gap-sources/itf_2025_points.md)). Flashscore is another site than P7's, so the two run side by side.

**How it is run [observed]** (`src/ingest/point_sources/flashscore_points.py`):
* **The extract** (14 Oct, 01:07 UTC, offline, 82 s): the handoff copy's ITF singles records of 20 Dec 2024 to 15 Mar 2026, from 148 files of `flashscore_full` and `flashscore_gql_stats`, one per match id. 44,308 records, of which 42,791 are dated 1 Jan 2025 to 28 Feb 2026, 29,614 of those with a match duration. These are the research's counts exactly.
* **The targets:** the 42,876 targets of P7's frozen list (`itf_points_2025_2026`, the map of 12 Oct) with a map date from 29 Dec 2024 to 28 Feb 2026.
* **The link:** 40,873 targets (95%) linked to a record. The rule is the same tour; the record dated 3 days before to 8 after the target's date; both players' first surname words among a target player's name words; on a tie, the record whose grade (M15, W35) is in the target's tournament name.
* **The feed:** `global.flashscore.ninja/2/x/feed/df_mh_1_<id>`, with the feed signature the site's own pages send (`x-fsign`). An empty answer is recorded once as absent. Pace: the plan's 2 s plus up to 1 s.
* **The order:** records with a duration in the handoff copy first, newest first, then the rest. Nothing is skipped; the likely empty ones just come last.
* **Parsing:** each game's server, winner and the score after every point (the last point is the game winner's), with Flashscore's break-, set- and match-point marks, and tiebreaks point by point. A record is "complete" when every set has as many games as the record's own set score.

**Trial [observed]**, 14 Oct, 01:09-01:19 UTC, 189 requests, no refusal. About 7 targets per month and tour, seeded:
* *Records:* 131 of 189, 130 of them complete. The one short record (W15 Oslo, January 2025) misses a game.
* *By month:* nearly every target of December 2024 to June 2025 has a record; from July 2025 about half.
* *The duration rule:*

  | Handoff record | Feed with points | Empty feed |
  |---|---:|---:|
  | With a duration | 131 | 6 |
  | Without one | 0 | 52 |

* *Against the official result* (`src/eda/gap_downloads/verify_flashscore.py`): 115 of 115 records with an official row (Sackmann's) agree on the winner and every set. 16 come from the WTA website records (12) and TennisLive's listings (4), which the check does not read.
* *Irregular games:* 6 of the 131 records have one game whose listed scores skip a step ("15:0" then "40:0"). The point between has no known winner, and that game lists a point fewer than was played.
* *Staged:* 17,805 points.

**Expected for the bulk [inference, written before it ran]:** about 28,000-28,500 records, at the trial's rate on the 29,614 targets with a duration, and almost none without one.

**The download [observed]**, 14 Oct 04:38 UTC to 15 Oct 15:57 UTC, in three runs:
* *The runs:* a Windows Update restart (14 Oct 07:29 UTC) cut the first; the second used its budget at 10:58 UTC on 15 Oct; the third asked the rest.
* *Requests:* 40,867 in all, the trial's included, one per feed. There was no retry, error or refusal.
* *Records:* 27,534 feeds hold a point record; 13,333 are empty. By target: a record for 27,535 of the 42,876, 27,174 of them complete, 305 short, 56 other; 2,003 targets not linked.
* *By month* (targets with a record, of those linked): December 2024 to June 2025, 92-98% each month; July to November 2025, 42-53%; December 2025, 23%; January-February 2026, 41-55%.
* *The duration rule held:* 27,501 of the 28,434 targets with a duration in the handoff copy have a record, and 35 of the 12,439 without one.
* *Irregular games:* 900 of the 27,534 records (3.3%) have at least one game whose listed scores skip a step.
* *Staged:* 3,682,438 point rows.

**Against the official result [observed]** (`verify_flashscore.py`, 15 Oct 16:00 UTC, after a fix: a never-started 0-0 set in the official score is now left aside, as in `verify_links.py`):
* 24,887 of the 24,973 records that have an official row agree on the winner and every set; 83 differ in score and 3 name another winner.
* 2,562 have no official row (TennisLive's listings 1,328, the WTA website records 1,234).
* Before the fix, 226 differed in score, mostly retirements written "6-0 0-0" in the official score.

**On the map [observed]**, rebuilt at 16:00 UTC on 15 Oct. The loader `load_flashscore_points` in `src/eda/data_map/measure.py` places each record on the map match the adapter linked it to (`flashscore_point_uids`, from the per-target table, as for TennisLive's gap pages), and adds no new matches. With it, the ITF matches have point (or shot) data as follows:

| Months | ITF matches | With point data |
|---|---:|---:|
| January-June 2025 | 18,909 | 16,988 (90%) |
| July-December 2025 | 20,083 | 8,845 (44%) |
| January-February 2026 | 4,076 | 1,916 (47%) |

The year 2025 as a whole has 25,933 of 39,114, against 398 before P13. What remains without points in the window (about 15,300 matches: 13,181 of 2025, most from July on, and 2,160 of January-February 2026) is for TennisLive's pages (P8), whose records usually lack the set-closing games.

**Not in the timing clock:** like the other new sources, Flashscore's records are not wired into the leak-proof clock.

### Running and resuming P13

A run stops at its budget of 30,000 requests (about 23 hours) or on a block. Rerunning the same command resumes: every answer is on disk with its receipt, and nothing is asked twice. From the repository root, in Git Bash:

```
./python.sh -m src.ingest.point_sources.flashscore_points --max-requests 30000 --min-interval 2.0 --jitter 1.0 > data/raw/point_sources/flashscore_points/_logs/run_<UTC stamp>.log 2>&1
```

When every feed is asked (the log's last `feeds:` line reaches its total with no `STOPPED`):

```
./python.sh src/eda/gap_downloads/verify_flashscore.py
./python.sh src/eda/data_map/build.py
```

The extract (`--extract`) runs only once; each run restages `points.parquet` and `matches.parquet` from every feed on disk.

**Files:**
* *Raw* (gitignored): `data/raw/point_sources/flashscore_points/feed/<id>.txt.gz`, `_receipts.jsonl` and `_logs/`.
* *Staged* (gitignored): `data/dump/points/flashscore_points/`, holding `handoff_itf.parquet`, `matches.parquet` and `points.parquet`.
* *Evidence:* `data/studies/gap_downloads/flashscore_itf_points_2025_2026_matches.csv.gz` (one row per target), `_summary.json`, `_link_check.csv.gz` and `.json`.
* *Tests:* `test/gap_downloads/test_flashscore_points.py` (the parser, the link, the trial's spread and a whole run against a fake Flashscore) and `test/data_map/test_sofascore_edition_links.py` (the map's placement).
* *Shared since 16 Oct 2026:* the raw folder, receipts and staged tables also hold work package P6's Flashscore feeds, men's ATP and Challenger matches of 2018-24 ([the P6 data issues report](../p6_data_issues/README.md#2-sofascores-holes-what-fills-them), `flashscore_p6.py`). Staging takes each feed's match from every extract on disk (`handoff_itf.parquet`, and P6's `handoff_p6.parquet`); linking still reads the ITF extract alone. `verify_flashscore.py --p6` checks P6's records, and the map places them through P6's own per-target table.

## Running it

From the repository root, in Git Bash:

```
./python.sh -m src.ingest.public_dump.sirgenkii_infotennis              # done; reruns skip what is on disk
./python.sh -m src.ingest.point_sources.sofascore_editions               # plain client, once SofaScore's block has lifted
./python.sh -m src.ingest.point_sources.sofascore_editions --limit 3 --max-requests 60   # a trial on the 3 newest editions
./python.sh -m src.ingest.point_sources.sofascore_editions --stage-only  # no HTTP: rebuild the tables and evidence
./python.sh src/eda/data_map/build.py                                    # then redraw the data map
```

**Browser mode**, when SofaScore challenges the plain client. First open a Chrome window with a blank profile and a debugging port, in PowerShell:

```
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:LOCALAPPDATA\sofascore-cdp" --no-first-run --no-default-browser-check --disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows https://www.sofascore.com/tennis
```

The three `--disable-…` flags (added 11 Oct 2026) keep the tab running at full speed when the window is hidden or minimised; without them, a long run can stall for many minutes at a time (gap 3 of P6 lost 2.8 hours). Let the page load (click the check if one shows). Then run:

```
./python.sh -m src.ingest.point_sources.sofascore_editions --browser
```

The adapter makes each request as a `fetch()` inside that tab, at its own pace. It reloads the tab when the site's hourly token expires. Keep the window open; if a check appears in it, click it.

**Every run:**
* **Resumes.** Every answer is kept with a receipt, and nothing is asked twice. An HTTP 404 means the record does not exist and is not asked again.
* **Stops on a block.** HTTP 403, 429 or a challenge, after one retry a minute later.
* **Is budgeted.** `--max-requests`, 10,000 by default.
* **Rebuilds its evidence**, from everything on disk, even when it stops early.

`--skip statistics` fetches points only (about half the requests). `--gap <id>` points the adapter at another gap of the map: `atp_points_2025` first, then the seven of [P6](#sofascore-by-edition-seven-more-gaps-work-package-p6).

## Files

| File | What it is | Made by |
|---|---|---|
| [sirgenkii_summary.json](../../../data/studies/gap_downloads/sirgenkii_summary.json) | The SirGenkii download: every file's bytes, SHA-256 and git blob SHA-1, and each staged table's rows | `sirgenkii_infotennis.py` |
| [sofascore_atp_points_2025_matches.csv](../../../data/studies/gap_downloads/sofascore_atp_points_2025_matches.csv) | One row per target: the match as the map had it, the SofaScore event it links to, and what was fetched (status, points, completeness against the score, box score) | `sofascore_editions.py` |
| [sofascore_atp_points_2025_editions.csv](../../../data/studies/gap_downloads/sofascore_atp_points_2025_editions.csv) | One row per edition: the SofaScore season found, the listings tried, events listed and targets linked | `sofascore_editions.py` |
| [sofascore_atp_points_2025_summary.json](../../../data/studies/gap_downloads/sofascore_atp_points_2025_summary.json), [runs.jsonl](../../../data/studies/gap_downloads/runs.jsonl) | The last run's counts by year and level, and one line per run | `sofascore_editions.py` |
| [sofascore_atp_points_2025_link_check.csv](../../../data/studies/gap_downloads/sofascore_atp_points_2025_link_check.csv), [.json](../../../data/studies/gap_downloads/sofascore_atp_points_2025_link_check.json) | Each target's event against Tennis My Life's winner and score, and the counts | `src/eda/gap_downloads/verify_links.py` |
| `sofascore_<gap>_matches.csv`, `_editions.csv`, `_summary.json`, `_link_check.csv` and `.json` for each P6 gap: `challenger_points_2025`, `wta125_points_2019_2026`, `tour_points_rest`, `challenger_points_2022_2024`, `atp_points_2018_2020`, `wta_2018_points`, `challenger_points_2018_2021` | The same five files as for the ATP gap. Since P6, the matches file has a `link_note` column (why a target was left unlinked), and the link check has the `official` file read (Tennis My Life or Sackmann) and the target's `creator` | `sofascore_editions.py`, `verify_links.py` |
| `sofascore_<gap>_matches.csv.gz`, `_editions.csv`, `_summary.json`, `_link_check.csv.gz` and `.json` for the P7 gaps `itf_points_2025_2026` and `itf_detail` | The same five files, the two per-target tables gzipped | `sofascore_editions.py`, `verify_links.py` |
| [itf_qualifying_probe.json](../../../data/studies/gap_downloads/itf_qualifying_probe.json), [.csv](../../../data/studies/gap_downloads/itf_qualifying_probe.csv) | P7's measure of ITF qualifying: each sampled qualifying event's point record, and the counts by edition | `src/eda/gap_downloads/itf_qualifying_probe.py` |

Raw files, gitignored:
* `data/raw/public_dump/sirgenkii_infotennis/`: the repository's files at their own paths, with `_receipts.jsonl`.
* `data/raw/point_sources/sofascore_editions/`: SofaScore's answers, gzipped verbatim, with `_receipts.jsonl`, and the runs' logs in `_logs/`.

Staged tables, gitignored:
* `data/dump/points/sirgenkii_infotennis/`: one Parquet file per dump.
* `data/dump/points/sofascore_editions/`: `events`, `points` and `statistics`, in the columns of the SofaScore player adapter.

Tests: `./python.sh -m pytest test/gap_downloads test/data_map -q`. They cover the dump reader, name linking and completeness, a whole run against a fake SofaScore (a block included), the link check's verdicts, and the map's placement of the records. P6 added tests for the linking fixes (played before cancelled, borrowed events, the week before, the winner), the link check's two result files and new verdicts, a list frozen before its first run, the WTA 125 category, a closed Chrome window (`test/point_shot_sources/test_point_sources_scrape.py`) and the timing linker's reading of every gap's links (`test/match_timing/test_link_sources_c.py`). P7 added tests for the gzipped tables (written and read back by the adapter, the link check, the map and the timing linker), the `--editions` selection, the streamed staging, and the qualifying probe's selection (`test/gap_downloads/test_itf_qualifying_probe.py`).

## Limits

* **Linking by names.** Name forms differ between the map and SofaScore, so a match could go unlinked or be paired wrongly. For this gap all 3,778 linked, and the check found no link with a different winner. It cannot vouch for the 6 matches that have no official row.
* **SofaScore's own records.** 21 records are short or uneven against the score, and SofaScore's listed score is itself wrong at least once (Båstad). Where another source holds the same match, the records can be compared once the sources are merged.
* **Placement on the map.** The map dates 2026 matches by the day played, so its generic link can put a record on the same pair's meeting a few days earlier at another event. The map therefore places SofaScore's records on the matches the adapter linked them to, by tournament, and uses the generic link only for the rest (`sofascore_edition_uids` in `src/eda/data_map/measure.py`). The other session found this trap in the Slam data.
* **The frozen list.** It keeps the map's match ids (`uid`) of the build of 25 September 2026. A later build renumbers matches, so the list is joined by its names and dates, not by `uid`.
* **P6: SofaScore's holes.** Its point records are near complete for Challengers of 2024-26 and for most tour-level main draws. They are thin for qualifying at every level, about half for Challengers of 2018, and almost absent for Challengers from spring 2022 to the end of 2023. Where SofaScore has nothing, the map's point data for those matches comes mostly from TennisLive (P5), which usually lacks the set-closing games. *Since 14 Oct 2026* the ATP Stats Centre's own point files fill 2,360 of these matches completely: the map's source `infosys_challengers` ([the follow-up](../p6_data_issues/README.md), section 2).
* **P6: the map's own rows.** Some targets are wrong in the map, and nothing on SofaScore can fix them:
  * Tennis My Life misdates editions: Nottingham 2025 is dated July for a January event; several 2021 venues' consecutive Challengers share one name and date.
  * The WTA website records file September 2026 matches under the wrong WTA 125s.
  * The map holds some matches twice (an API-Tennis row beside Tennis My Life's or Sackmann's), and each twin links to the same event.
  * These targets stay unlinked, or the twins share an event; the map credits one row.
  * *Followed up 14 Oct 2026* ([the data issues P6 found](../p6_data_issues/README.md)):
    * The website copy's last ten editions (7-14 Sep 2026) misfile all 187 of their matches. They are now left out of the map and of the lower-level feed, and the WTA API's records place those matches.
    * Tennis My Life misdates 67 Challenger editions of 2018-25. They leave 1,586 matches twice on the map, and 31 Tenerife 2024 matches in Stage 0 a month early (a leak). Both are prepared for the owner's decision, not changed.
* **P6: borrowed events.** When SofaScore lacks a target's match, an event of one of its players whose opponent shares only a first name can take its place. The link check shows these as a different winner or score: 9 in gap 4 and some of the 43 in gap 7. A surname rule that would stop them cost more correct links than it saved, because SofaScore shows players' current names, married names included. *Since 14 Oct 2026, a link that fails both the surname test and the official result is refused (47 links; [the follow-up](../p6_data_issues/README.md)).*
* **P6: the frozen lists.** They were taken from the map of 8 October. Matches that joined the map later (P4's TennisLive listings added 381 Challenger matches of 2025-26) are not targets.
* **P6: box scores.** Only gaps 1-3 asked for them (15,814). For gaps 4-7 Stage 0 holds a box score for about 99% of the matches.
* **Rights.** SofaScore's terms forbid automated extraction; it is collected on the owner's decision of 23 September 2026 ([point- and shot-level sources](../point_shot_sources/README.md#direct-download-24-september-2026)). The SirGenkii data has no licence and is a third party's decryption of ATP files, the kind the owner accepted for the Hugging Face copy on 25 September ([decision](../../decisions/2026-09-25-atp-pipeline-handoff.md)). The project decrypts nothing.

## TennisLive by event (work package P4)

**Status: done on 9 October 2026.** [Work package P4](collection-plan.md#p4-tennislive-womens-players-whole-events-and-every-event-of-2018-2026-listed) listed every ITF, Challenger, WTA 125, tour-level, Finals and Grand Slam event that TennisLive.net holds for 2018 to 2026-W40 (to 4 October), each from its results section, so that men's ITF qualifying and the ITF matches since June 2026 reach the map as results. Two seeded samples of match pages measure point coverage for P8.

**In short [observed]:**
* 11,644 events listed: 11,385 from their results sections, and 259 without a tournament page from the date pages of their days. They hold 696,217 played singles matches (373,968 main draw, 322,249 qualifying), and doubles.
* Where Tennis My Life's or Sackmann's files hold the same match, 445,411 of 446,056 have the same winner and set scores (99.86%).
* On the rebuilt map, the listings join 516,866 known matches and add 178,506 new ones: men's ITF qualifying of every year (5,276-23,326 a year), the ITF matches since June 2026, and events and matches the files miss.
* TennisLive stopped answering this address for about 35 minutes at 02:45 UTC on 9 Oct, after about 12,200 requests in seven hours. The 400 sample pages were completed after it lifted: points on 177 of 200 ITF main-draw pages since June 2026, and on 70 of 200 ITF qualifying pages, 43 of 62 in the final qualifying round.

### What changed from the plan [observed]

* **The events come from the site's calendar, not from players.** The plan expected none ("The site has no calendar endpoint ... so events are found through players"). But every date page (`/<YYYY-MM-DD>/`) embeds the week's `tournamentCatalog`, every event of that week with a tournament page, and the day's menu and matches.
  * One Wednesday page per ISO week found the events: 457 requests and no slug guessing or name matching, instead of the 2,000-3,000 player listings the plan expected.
  * The calendar names 12,395 events, 11,644 of them of the listed kinds (the rest are Davis Cup and BJK Cup ties, juniors, exhibitions).
  * Its ITF events per year equal Sackmann's files: 386 men's and 373 women's in 2021 in both, 526 and 533 in 2022. For 2025-26 TennisLive has more (634 and 629 in 2025 against 595 and 588), and Sackmann's mirror ends on 1 June 2026.
  * The plan's ~15,400 editions counted one event more than once when its sources spell it differently: of the map's 16,364 editions in these levels, 15,674 link to a TennisLive event by their players (`tennislive_editions.csv.gz`). The 690 others are mostly one- or two-match editions of secondary sources (API-Tennis 369, the WTA website 95, the ITF API's week-41 qualifying 57); only 10 editions of Tennis My Life's or Sackmann's files found no event.
* **259 events have no tournament page,** so no results section and no match pages: 202 women's ITF of 2018, 53 ITF of early 2019 and 4 Challengers. They appear in the day menus without a URL, and their matches only on the date pages, so the run also read every date page of their weeks, from the Saturday before to the Sunday (370 more pages).
* **Tour-level events of 2022-2026 are listed too.** The plan's section says 2018-2021; its prompt says 2018-2026, and P5's qualifying gap (2018-2026) links to these listings. That added 578 events, one request each.
* **The women's tour** is in the player adapter (`--slugs wta:<slug>`; raw `players/wta/<slug>/`), and the map reads each page's tour from its URL. Tested offline, and live on 9 Oct with one player (2 requests: Anna Sisková's 2026 season, 56 matches). The event mode needs no player listing.
* **Weekly venues** (Monastir, Antalya, Sharm El Sheikh) need no final-date check: an event is TennisLive's own, by id, in the week whose catalog names it. As a check, 11,548 of 11,635 events have every match between the Saturday before their week and the Monday after; the other 87 start a few days earlier (a Thursday or Friday qualifying start, or late December for an early-January event).

### The download [observed]

8 Oct 2026 19:47 UTC to 9 Oct 03:51 UTC, at the adapter's 1.5 s + up to 1 s between request starts (about 1,800 requests an hour); the last 283 sample pages at 3 s + up to 2 s.

| Requests | Number | Answers |
|---|---:|---|
| Date pages: one Wednesday a week, 2018-W01 to 2026-W40 | 457 | all HTTP 200, each with its date as asked |
| Results sections | 11,385 | all HTTP 200, and every match in them over |
| Date pages of the 259 events without a page | 370 | all HTTP 200 |
| Session page (a token) | 1 | the date pages' own token served the whole run |
| Sample match pages | 400 | 399 fetched (116 before the block, 283 after it; 5 timed out during it and were asked again), 1 already held for a career; all HTTP 200 |

* **Raw**, gzipped as served: 95 MB of date pages, 104 MB of results sections (2.1 GB as served).
* **The block [observed]:** from 02:45:20 UTC on 9 Oct every request, the home page included, timed out with no byte answered, while the site answered another network at once (HTTP 403 to a fetch robot, Cloudflare's usual). It answered this address again by 03:20 UTC. No HTTP 403, 429 or challenge came at any time. The run was stopped at 03:02 UTC, the samples resumed at 03:21 UTC at a slower pace, and the adapter now stops after two requests in a row that get no answer.

| Listed events and played singles | Men: events | main | qualifying | Women: events | main | qualifying |
|---|---:|---:|---:|---:|---:|---:|
| ITF | 4,468 | 137,512 | 159,604 | 4,412 | 136,971 | 114,435 |
| Challenger / WTA 125 | 1,527 | 49,926 | 23,711 | 229 | 7,233 | 1,718 |
| Tour level, Finals, Slams | 543 | 21,867 | 10,934 | 465 | 20,459 | 11,847 |

By year, in `tennislive_summary.json` (`targets_by_year_tour_kind`). Men's ITF qualifying runs from 23,506 played matches in 2018 (whose Futures had 128-player qualifying draws) to 22,753 in 2025 and 17,405 in 2026 to 4 October.

### Trial and Expected [observed]

The trial (8 Oct, 19:47-19:55 UTC, 22 requests) listed the 11 events of the gap research's follow-up ([lane D](../../../data/studies/gap_sources/research_notes/D_tennislive.md#follow-up-mens-itf-after-june-2026)):

| Expected (the plan) | Research (29 Sep) | P4 |
|---|---|---|
| Every sampled event listed in full | 11 of 11 | 11 of 11, 31 main-draw matches in each |
| Men's ITF qualifying listed with results for every event | 318 in 8 events | the same 318 (24, 56, 54, 56, 24, 40, 40, 24); every men's ITF event of 2018-2026 listed |
| Points on most sampled main-draw pages | 18 of 24 men's, 9 of 9 women's | 177 of 200 since June 2026: 85 of 100 men's, 92 of 100 women's |
| Statistics on all | 33 of 33 | 196 of 200 main-draw pages (77 of 200 qualifying pages) |

### Samples of match pages [observed]

Drawn when every event was listed (seed 20261008), one match per event, from the played singles matches
with a page, and frozen in `tennislive_samples.csv`. Each page's record is judged against the listed score with
the rules of `src/eda/point_shot_sources/verify_scrape.py`.

| Sample | Pages | With points | Complete | Only set-closing games missing | Other shortfall | No points | Statistics | Median share of games with points |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ITF main draw since 1 June 2026, men | 100 | 85 | 8 | 54 | 23 | 15 | 98 | 0.86 |
| Same, women | 100 | 92 | 10 | 66 | 16 | 8 | 98 | 0.89 |
| ITF qualifying 2019-2026, men (12-13 a year) | 100 | 32 | 0 | 22 | 10 | 68 | 33 | 0 |
| Same, women | 100 | 38 | 0 | 28 | 10 | 62 | 44 | 0 |

* **Main draws:** most pages carry points, as the research found (18 of 24 men's, 9 of 9 women's). 16 of the 23 pages without points show the site's "Complete game and point progress is not available" notice. Complete records are rare, because the game that closed each set is usually missing.
* **Qualifying:** points on 70 of 200 pages, under half, so by the plan's rule P8 keeps the listings' results instead of fetching every ITF qualifying page. The final qualifying round is the exception, as the plan expected (the umpires' devices): points on 43 of its 62 pages (men 19 of 27, women 24 of 35), against 27 of 138 in the earlier rounds. Fetching only final-round pages is an option for P8 [inference: about a third of ITF qualifying matches are final-round].
* By year, the qualifying pages with points run from 0-4 of 13 (2019-21) to 5-8 of 12-13 (2022-24) and 3-4 of 12 (2025-26) per tour (`samples` in `tennislive_summary.json`).

### Checks [observed]

* **The listed results against the result files** (`src/eda/gap_downloads/verify_tennislive.py`). Each played singles match is looked up in Tennis My Life's and Sackmann's files: the same tour, surname pair, first names, draw and round, dated inside the event's week (a Slam's three weeks). 446,056 have an official row:

  | Verdict | Matches |
  |---|---:|
  | Same winner, same games in every set | 445,411 |
  | Same winner, a set's games differ | 413 |
  | Same winner, the official score written loser first (Tennis My Life's WTA Rome 2026) | 73 |
  | Same winner, no listed score | 12 |
  | Different winner | 147 |

  * Of the 147, 12 are Tennis My Life's Rouen 2026 WTA rows, whose winners and losers are swapped (its own rows have Shymanovich losing her round of 16 and then playing the quarter-final); TennisLive's are consistent. Most others are a pair that met twice in a week or two, where one file lacks the match.
  * 250,161 have no official row: men's ITF qualifying (159,604; no file lists it), the ITF matches after the files end, women's ITF qualifying the files miss, and name forms the check cannot pair.
* **The weekly venues** and **the map's editions**: above.

### On the map [observed]

Rebuilt at 03:56 UTC on 9 Oct (`./python.sh src/eda/data_map/build.py`):

* The loader (`load_tennislive_listed` in `src/eda/data_map/measure.py`, run after the result files) read 696,217 played singles: 516,866 link to known matches and 178,506 join as new ones.
* Each match is dated by its event's Monday, as the result files date theirs (a Slam's by the Monday of the week it was played). Dated by the day played, the linker's changed-name pass (three days) missed Thursday-to-Sunday matches such as 'Stefano D'Agostino' / 'Stefano Dagostino', and Slam matches of the second week fell outside its window.
* The ITF levels are TennisLive's; any other event takes its level from the matches it shares with the result files, as TennisLive ranks a few WTA 250s with the WTA 125s.

| Cell | Before (8 Oct, 16:37 UTC) | After |
|---|---|---|
| Men's ITF 2026 | 7,841 matches, 6,105 estimated missing | 14,857, none estimated missing |
| Women's ITF 2026 | 12,922, 1,805 estimated missing | 14,159, none |
| Men's ITF qualifying | 0-68 a year | 2018: 23,326; 2019: 12,755; 2020: 5,276; 2021: 15,488; 2022: 19,109; 2023: 20,845; 2024: 21,795; 2025: 22,585; 2026: 17,646 |
| Women's ITF qualifying | 2026: 9,696, 1,159 estimated missing | 2026: 12,499, none; 2025: +1,584; 2018: +1,261 (matches the WTA website's records lack) |
| Men's ITF main draws 2018 and 2025 | 16,900 and 17,850 | 17,634 and 19,522 (events Sackmann's files lack: 27 in 2018, about 40 in 2025) |
| Men's Challenger qualifying 2018, 2025, 2026 | 3,632; 3,591; 3,087 | +217, +129, +359 (first-round qualifying matches Sackmann lacks; 2026 after June) |

* **Duplicates.** Where the linker cannot pair two spellings, a known match is added again: 'Cori Gauff' / 'Coco Gauff', 'Paula Badosa Gibert' / 'Paula Badosa', 'Laura Boehner' / the WTA lists' 'Bohner'. A loose test (the same player, round and week with an opponent of the same first name) flags at most 100 of the 178,506 added matches, and many of those are real second meetings at weekly venues.
* The map's gaps `itf_after_june_2026` and `men_itf_qualifying` now read as filled, and men's ITF qualifying is no longer marked "no source".
* **Not on the leak-proof clock:** TennisLive's listings are not wired into `src/eda/match_timing/` or Stage 0, so the models do not see them yet; that is separate work. No `refresh.py` run was needed.

### Running and resuming P4

From the repository root:

```
./python.sh -m src.ingest.point_sources.tennislive_events --pageless-days --max-requests 25000 > data/raw/point_sources/tennislive/_logs/events_<UTC stamp>.log 2>&1
./python.sh src/eda/gap_downloads/verify_tennislive.py
./python.sh src/eda/data_map/build.py
```

* Every run resumes and asks nothing twice; an answer fetched while an event was still being played is asked again later. It stops on a block, and after two requests in a row with no answer.
* `--stage-only` rebuilds the tables and evidence with no HTTP (about 6 minutes; `--no-pages` skips the match-page tables).
* The samples were drawn once, when every event of the full range was listed, and are frozen in `tennislive_samples.csv`.
* A trial: `--weeks 2026-W27:2026-W36 --limit 12 --max-requests 60`, or `--only <event URL>,...` (in Git Bash an argument starting with `/` is rewritten into a Windows path; the adapter reads it anyway).
* Logs: `data/raw/point_sources/tennislive/_logs/`.

### Files

| File | What it is |
|---|---|
| [tennislive_events.csv.gz](../../../data/studies/gap_downloads/tennislive_events.csv.gz) | One row per event the calendar names: TennisLive id, URL, name, rank, kind, weeks, the results answer, and counts of singles (main, qualifying, played) and doubles |
| [tennislive_editions.csv.gz](../../../data/studies/gap_downloads/tennislive_editions.csv.gz) | One row per edition of the map's match table (tour, name, year, week): the event holding most of its matches, by player pairs |
| [tennislive_samples.csv](../../../data/studies/gap_downloads/tennislive_samples.csv) | The 400 sampled pages: the listed match, the page's points and completeness against the listed score, the statistics block |
| [tennislive_link_check.json](../../../data/studies/gap_downloads/tennislive_link_check.json), [.csv.gz](../../../data/studies/gap_downloads/tennislive_link_check.csv.gz) | The listed results against Tennis My Life's and Sackmann's: counts by tour, kind, draw and year, and the matches that differ |
| [tennislive_summary.json](../../../data/studies/gap_downloads/tennislive_summary.json), [runs.jsonl](../../../data/studies/gap_downloads/runs.jsonl) | The last run's counts (calendar, events by kind, year and tour, the weekly-venue check, editions, samples) and one line per run |

* **Code:** `src/ingest/point_sources/tennislive_events.py` (the event mode); `src/ingest/point_sources/tennislive.py` (players of both tours, and the pages); `src/eda/gap_downloads/verify_tennislive.py`; the map's readers `load_tennislive_listed` and `load_tennislive` in `src/eda/data_map/measure.py`.
* **Tests:** `./python.sh -m pytest test/gap_downloads -q`.
* **Raw** (gitignored), in `data/raw/point_sources/tennislive/`: `calendar/` (date pages), `tournaments/` (results sections), `session/`, `matches/` (pages), `_receipts.jsonl`, `_logs/`.
* **Staged:** `data/dump/points/tennislive/events.parquet` (12,395 events) and `listed.parquet` (872,190 matches, singles and doubles, every time field the site sends). The sampled pages join `matches`, `games`, `points` and `statistics`, where `sampled_in` names the sample.

### Limits

* **Results only.** The listings carry scores and winners, not points; TennisLive's points are on the match pages (P5, P8), usually without the game that closed each set.
* **TennisLive's own records.** 560 of 446,056 checked matches differ from the result files in score or winner. Either side can be wrong (Tennis My Life's Rouen 2026 and Rome 2026 rows are), and the matches no file holds cannot be checked.
* **The 2018-19 events without a page** come from date pages, whose matches carry no page URL; an event whose day page was missing would be short.
* **Event kinds** come from TennisLive's rank and name. The map's levels for anything but ITF and Slams come from the matches an event shares with the result files.
* **The block** means the site limits volume. P5 (~38,000 pages) and P8 (~19,000) should expect pauses: TennisLive answered nothing for about 35 minutes after some 12,200 requests in seven hours.
* **Rights.** TennisLive's terms forbid automated extraction and its robots.txt disallows `/api/`; collected under the owner's decision of 8 October 2026 ([decision](../../decisions/2026-10-08-scraping-approved.md)).

## TennisLive pages for the gaps (work package P5)

**Status: done on 10 October 2026.** [Work package P5](collection-plan.md#p5-tennislive-challengers-2018-2024-tour-and-slam-qualifying-wta-2018) fetched TennisLive's match pages for four gaps of the map, each match found through P4's event listings. A page holds the score after each point, game by game (the game that closed each set usually missing), the server, break-point markers and 8 match statistics.

**In short [observed]:**
* 38,421 gap matches frozen, 39,064 of their 39,542 rows linked and confirmed against the result files' scores, and 36,737 pages fetched in 25.5 hours with no refusal or pause.
* Points on 37,950 of the 38,772 rows with a page (97.9%), complete for 2,286; statistics on 38,522. Where an official box score exists, it equals the statistics in every field for 37,277 of 37,394 rows (0.3% of matches differ, one with the players swapped).
* On the rebuilt map: `challenger_points_2018_2021` 25,100 → 964, `challenger_points_2022_2024` 5,760 → 364, `wta_2018_points` 2,031 → 59, `qualifying_points_2018_2026` 6,473 → 221.

### The targets [observed]

| Gap | Matches | Editions | The plan (map of 8 Oct) |
|---|---:|---:|---:|
| `challenger_points_2018_2021` | 25,186 | 1,124 | 24,874 |
| `challenger_points_2022_2024` | 5,794 | 1,218 | 5,781 |
| `wta_2018_points` | 2,080 | 83 | 2,079 |
| `qualifying_points_2018_2026` (new under `gaps:`) | 6,482 | 624 | 6,579 |

* **Frozen at the first run** (9 Oct, 14:38 UTC), all four from the same map build (9 Oct, 03:56 UTC), in `tennislive_<gap>_matches.csv.gz`. They are 38,421 matches in 39,542 rows, because WTA 2018 qualifying (1,121) is in two gaps. `challenger_points_2022_2024` was already under `gaps:` (P6 added it).
* **Against the plan's counts.** P6's lists of the same gaps were frozen from the map of 8 Oct (16:34 UTC). Against them:
  * P4's listings, added to the map at 03:56 UTC, created 317 Challenger matches of 2018-21 (286 of them qualifying), 13 of 2022-24 and one WTA 2018 qualifying match that the result files lack;
  * 5 Challenger qualifying matches of 2018-21 left the gap;
  * the qualifying gap is 97 smaller than the plan's [inference: the ATP Stats Centre files of 2018-21, decrypted and put on the map on the evening of 8 Oct, give 117 tour and Slam qualifying matches their points].
* **The references.** Each target is checked against the row of the file the map took it from: Tennis My Life's (20,371 matches) or Sackmann's (17,051), with round, score and box score; API-Tennis's fixture (568), with score and winner. 431 have none: the map took them from TennisLive's own listings (338), the WTA's lists or website (64), and a few others.

### Linking [observed]

Offline, from P4's `listed.parquet` (`src/ingest/point_sources/tennislive_gaps.py`, no request):

1. **The event.** Each edition (tour, tournament, year and week of the map's date) goes to the TennisLive event that holds most of the map's matches of that edition, by player pairs (P4's rule). 2,834 of the 2,986 editions have one.
2. **The candidates** are the listed singles matches whose players both share a name word with the target's (the rule of `sofascore_editions.best_event`). They are ordered by the words shared, then the target's draw, its round, its games per set, played, and the nearest to the map's date.
3. **A candidate is confirmed** as the target's own match:
   * in the edition's event, by the reference's games per set; or by the map's surname pair, the round and one set's score (or a match that ended early);
   * in another event from 10 days before to 21 after the map's date, by the games per set and either the surname pair or three name words;
   * elsewhere in the target's year, by the surname pair, games, draw and round;
   * with no reference row, by the surname pair, in the edition's event or else in the target's week.

   Games per set found in a neighbouring event come before a pair and round found in the edition's event. A target with no confirmed candidate keeps its edition's best one, unconfirmed.
4. **A page is asked for** when its link is confirmed and has a page URL, and is in the target's draw or has the reference's games per set.

The rules come from a first, looser pass (any shared name word, in the edition's event, then three weeks around it). It linked 38,569 rows, but disagreed with the reference's winner for 66 and its score for 76, mostly a pair's other meeting elsewhere:
* **Misdated editions.** Tennis My Life files the March 2018 Irving Challenger under Dallas's name and date (29 January) and Biella 2-7 of 2021 under Biella 1's (14 February). The same holds for several same-city Challengers of 2020-21 (Antalya, Forli, Istanbul, Oeiras, Nur-Sultan, Prague, Santiago). Their matches are found in another week: 881 rows. *(Checked on 14 Oct: 14 February is Biella 2's own week, so only Biella 3-7's matches are dated wrong, by 3 weeks to 3½ months.)*
* **Two events in one edition.** Tennis My Life's "Prague" of 2020 is Prague I and II, and Griekspoor and Coppejans met in the first round of both.
* **API-Tennis files some Challenger qualifying matches as main-draw rounds** ("Final", "Semi-finals"). 101 of its rows link to a TennisLive qualifying match, and the 94 with the same score are fetched; 315 stay unconfirmed or unlinked.

| | Challengers 2018-21 | Challengers 2022-24 | WTA 2018 | Qualifying 2018-26 |
|---|---:|---:|---:|---:|
| Confirmed in the edition's event | 23,704 | 5,233 | 2,064 | 6,388 |
| Confirmed in another event within three weeks | 641 | 151 | 0 | 2 |
| Confirmed in another week of the year | 735 | 116 | 0 | 30 |
| Unconfirmed (the edition's best candidate kept) | 25 | 93 | 5 | 10 |
| Not linked | 81 | 201 | 11 | 52 |
| Pages asked for (rows) | 24,790 | 5,498 | 2,064 | 6,420 |
| Distinct pages | 24,028 | 5,348 | 2,062 | 6,409 |

* **Confirmed but not asked for:** 285 links have no page, those of the four Challengers without a tournament page (Almaty 2018, 90; Shenzhen 2018, 89; Canberra, 56; Bangkok, 49) and one at Porto; 7 are in another draw without the reference's games.
* **The link check.** Of the 38,662 confirmed rows with a reference row, 38,649 have its winner and the games of every set. The other 13 are records the two sources keep differently:
  * 6 with a set's games differing (retirements written otherwise; Orlando 2018, where Tennis My Life's last set has the loser winning it);
  * 4 with no listed score;
  * 2 with another winner (Lisbon 2020's retirement at 5-2; Rome 1 2021, a quarter-final in the file and a round of 16 on TennisLive);
  * 1 with the score written loser first.

  402 confirmed rows have no reference row to check.
* **The map held about 900 of these matches twice** (until 14 Oct; [fixed then](#update-14-october-2026-each-misdated-match-held-once)). 921 pages are linked by two of the map's matches: mostly a Tennis My Life row of a misdated edition and Sackmann's row of the same match (817), else two spellings of a name. Each page is fetched once, and on the map both copies were credited (`tennislive_gap_uids` in `src/eda/data_map/measure.py`).
* **In all:** 36,737 distinct pages; 30 were held already (the ten careers' and P4's samples).

### Trial [observed]

9 Oct, 14:57-15:09 UTC: the 3 newest editions of each gap, 141 pages, all HTTP 200, about 1,460 requests an hour at 2 s + up to 1 s.

| Expected (the plan) | Trial (with the pages held already) |
|---|---|
| Points on 95-99% of Challenger matches | 2021: 86 of 87 |
| Points on all 32 sampled WTA 2018 matches | the 2018 Houston and Taipei 125Ks, main draw and qualifying: 49 of 51 |
| Points on ~80% of tour qualifying | 2026 WTA qualifying (Guadalajara, São Paulo): 8 of 8 |
| Complete records rare | 11 of 173 rows complete; 134 lack only the set-closing games |

Statistics are on 165 of the 173 rows. The 151 with an official box score equal it in every field, none with the players swapped.

### The download [observed]

9 Oct 15:10 UTC to 10 Oct 16:41 UTC (25.5 hours), then the stage and the evidence until 18:29 UTC.

* **Requests:** 36,567, one of them a retry: 36,566 new pages, every one HTTP 200, plus 171 held already (the trial's 141 and 30 earlier pages). About 1,434 an hour at 2 s + up to 1 s.
* **No block:** no HTTP 403, 429 or challenge, and no silent drop, so the pause rule never fired. P4's drop of 9 Oct (after some 12,200 requests at about 1,800 an hour) did not recur at this pace; why it happened is unknown.
* **Raw:** 12.8 GB as served, kept gzipped: `matches/` now holds 41,356 pages in 2.1 GB (the careers' and P4's samples included).
* **Staged:** 41,412 pages, 821,647 games, 4,169,807 points and 325,633 statistics rows (`data/dump/points/tennislive/`).

| Rows with a page | Challengers 2018-21 | Challengers 2022-24 | WTA 2018 | Qualifying 2018-26 |
|---|---:|---:|---:|---:|
| Pages | 24,790 | 5,498 | 2,064 | 6,420 |
| With points | 24,238 (97.8%) | 5,430 (98.8%) | 2,021 (97.9%) | 6,261 (97.5%) |
| Complete | 328 | 1,751 | 10 | 197 |
| Only set-closing games missing | 22,718 | 3,412 | 1,949 | 5,527 |
| Other shortfall | 1,192 | 267 | 62 | 537 |
| No points | 552 | 68 | 43 | 159 |
| Median share of games with points | 0.90 | 0.92 | 0.89 | 0.90 |
| Statistics | 24,623 | 5,486 | 2,036 | 6,377 |
| Box score compared / every field equal | 23,984 / 23,961 | 5,219 / 5,218 | 2,015 / 2,010 | 6,176 / 6,088 |

WTA 2018 qualifying (1,112 rows with a page) is counted in both of its gaps. By year and level: `tennislive_gaps_summary.json` (`by_year_level`).

| Expected (the plan) | Observed |
|---|---|
| Points on 95-99% of Challenger matches | 97.8% (2018-21) and 98.8% (2022-24); by year from 96.6% (2020) to 99.4% (2024); main draws 98.7%, qualifying 95.7% |
| Points on all 32 sampled WTA 2018 matches | 2,021 of 2,064 (97.9%): main draws 98.0-100%, tour qualifying 97.9%, WTA 125 qualifying 90.1% |
| Points on ~80% of tour qualifying (a thin sample) | 97.5%: tour qualifying 97.2%, Slam qualifying 98.2%; men and women alike |
| Complete records rare | 2,286 of 38,772 (5.9%), except the Challengers of 2023-24, where 1,725 of 3,416 are complete |

* **The statistics against the official box score.** Of the 36,300 distinct matches compared, 116 differ (0.3%), mostly by a few points (the median largest difference is 3), and 63 of them are Slam qualifying. One has the players swapped (Roanne 2021, Debru v Pellegrino): the research's 2 swaps in 36 sampled tour matches came from a small sample.
* **Pages without points:** 822 rows, 793 pages.
  * 562 show the site's "Complete game and point progress is not available";
  * 609 still have the statistics;
  * 50 are retirements and 8 walkovers.

  46 of the pages list a set's games without any point in them; the map counts those as statistics.

### On the map [observed]

Rebuilt at 21:13 UTC on 10 Oct (`./python.sh src/eda/data_map/build.py`):

| Gap | Before (map of 10 Oct, 02:02 UTC) | After |
|---|---:|---:|
| `challenger_points_2018_2021` | 25,100 | 964 |
| `challenger_points_2022_2024` | 5,760 | 364 |
| `wta_2018_points` | 2,031 | 59 |
| `qualifying_points_2018_2026` | 6,473 | 221 |

* **The loader** (`load_tennislive(gaps=True)` and `tennislive_gap_uids` in `src/eda/data_map/measure.py`) read 37,639 page rows: the 36,737 pages, plus a row for each second copy of a match the map holds twice. All are inside the map's window and on known matches: 37,623 on the matches the adapter linked them to, 16 through the map's own linker, none added as new.
* **Two fixes came from the first rebuild** (18:56 UTC). A placed page now takes its match's date, year and names, and the placement key includes the draw:
  * 164 pages fell outside the map's window. They were the qualifying of early-January 2018 events, played on 29-31 December 2017, and dated by the day played.
  * TennisLive writes some brothers under one surname ("Arklon" and "Conner Huertas Del Pino"), which leaves the pair without a key.
  * A pair can meet in the qualifying and again in the main draw of one event, under one key without the draw.
* **What is left** in the gaps:
  * pages without points: 552 Challenger matches of 2018-21 (408 of them with statistics), 68 of 2022-24, 43 WTA 2018 and 159 qualifying;
  * the four Challengers without a page (284 matches);
  * links not found or not confirmed: 106 Challenger matches of 2018-21, 292 of 2022-24 (mostly the API-Tennis rows above), 16 WTA 2018 and 62 qualifying;
  * 7 confirmed links in another draw without the reference's games;
  * 18 matches the map holds twice under one key, whose page is credited to one copy.
* **Not on the leak-proof clock.** The pages reach the map only; `src/eda/match_timing/` and Stage 0 do not read them, so no `refresh.py` run was needed. Wiring them in is separate work.

### Running and resuming P5

From the repository root (Git Bash):

```
./python.sh -m src.ingest.point_sources.tennislive_gaps --max-requests 40000 > data/raw/point_sources/tennislive/_logs/gaps_<UTC stamp>.log 2>&1
./python.sh src/eda/data_map/build.py
```

* **Resumes:** every page is kept with a receipt, and nothing is asked twice; an HTTP 404 is recorded once as absent. The targets stay frozen (`--refresh-targets` derives them again).
* **Stops** on HTTP 429, a challenge or an unexpected 403. If two requests in a row get no answer at all (TennisLive's silent drop of 9 Oct), it pauses 30 minutes and goes on at 3 s + up to 2 s; four pauses in a row with no answer stop it.
* **At the end of each run** it restages every page on disk (about 40 minutes for 41,000 pages) and rewrites the evidence (about 2 minutes). The summary's `last_fetch` keeps the last run that made requests, so an offline rebuild does not lose the download's counts.
* `--link-only` freezes and links with no HTTP, and rebuilds the evidence from the staged tables; `--stage-only` also restages; `--limit N` asks only for the pages of each gap's N newest editions (the trial).
* The download is complete: a rerun asks for nothing (every page is held), unless `--refresh-targets` derives new targets from a newer map.

### Files

| File | What it is |
|---|---|
| `tennislive_<gap>_matches.csv.gz` (one per gap) | One row per target: the map's match, the reference row, the link and its evidence, the page's record and the box-score check |
| `tennislive_<gap>_editions.csv` | One row per edition: its TennisLive event and the targets linked |
| [tennislive_gaps_summary.json](../../../data/studies/gap_downloads/tennislive_gaps_summary.json), [runs.jsonl](../../../data/studies/gap_downloads/runs.jsonl) | The last run's counts (overall, by gap, year and level; links, records, statistics, pauses) and one line per run |

* **Code:** `src/ingest/point_sources/tennislive_gaps.py` (the gap mode); `tennislive.py` (the pages and their stage, `gaps_in`); the map's reader `load_tennislive(gaps=True)` and `tennislive_gap_uids` in `src/eda/data_map/measure.py`.
* **Tests:** `./python.sh -m pytest test/gap_downloads -q` (`test_tennislive_gaps.py`: the reference rows, the link rules, the record and box checks, the pauses, the page order, a whole run against a fake TennisLive and the map's placement).
* **Raw** (gitignored): the pages join `data/raw/point_sources/tennislive/matches/`, each receipt naming the gaps that asked; logs in `_logs/gaps_*.log`.
* **Staged:** the pages join `data/dump/points/tennislive/` (`matches`, `games`, `points`, `statistics`), where `gaps_in` names the gaps.

### Limits

* **Partial records.** TennisLive's pages usually lack the game that closed each set: 2,286 of 38,772 records are complete, 1,725 of them Challengers of 2023-24. The map counts a partial record as "point", and that is why P6 froze its SofaScore lists before these pages reached the map; SofaScore's complete records of the same matches are still to come (P6 gaps 4-7).
* **Links by names and scores.** 478 target rows are unconfirmed or not linked, most of them API-Tennis rows (315) whose rounds and scores look wrong. A reference row can itself be wrong, and the 402 matches without one are linked by the surname pair alone.
* **TennisLive's statistics** were checked only where an official box score exists (37,394 rows); the 116 matches that differ are listed in the per-target tables (`box_differences`), with no judgement of which source is right.
* **The map's duplicates:** the misdated copies are held once since 14 Oct (below). 11 doubles of 2026's two-week events remain. The 18 "held twice under one key" above are, on the map of 14 Oct, real repeat meetings that share one key (below).
* **Not on the leak-proof clock.** TennisLive's pages are not wired into `src/eda/match_timing/` or Stage 0, so the models do not see them; no `refresh.py` run is needed for them, and wiring them is separate work.
* **Rights.** TennisLive's terms forbid automated extraction; collected under the owner's decision of 8 October 2026 ([decision](../../decisions/2026-10-08-scraping-approved.md)).

### Update, 14 October 2026: each misdated match held once

**Asked by the owner** on 14 Oct, quoting this section's report of the misdated editions and of the looser linking: "Fix this if it isnt already fixed" ([process log](process_log.md#p5-follow-up-tennis-my-lifes-misdated-challenger-editions)).

* **The linking** was fixed in P5 itself: only links confirmed by the score were fetched and placed (above).
* **Stage 0, the model's match table, never held these doubles** [observed].
  * Its own linker joins a misdated Tennis My Life row to Sackmann's copy within a season when the set scores agree, and keeps Sackmann's row with its date.
  * Its one misdated event is the 31 matches of the third Tenerife Challenger of 2024, dated 21 January, which Sackmann lacks. It is covered by the owner's decision of 14 Oct on the [P6 data-issues study](../p6_data_issues/README.md) ([decision](../../decisions/2026-10-14-p6-data-issues.md)), and that study is correcting it.
* **The map: fixed** [observed; build of 14 Oct, 19:26 UTC].
  * **The rule** (`repair_tml_dates` in `src/eda/data_map/measure.py`; tests in `test/data_map/test_tml_redate.py`). Before Tennis My Life's rows join the map, a row whose own match Sackmann's files (else TennisLive's listings) hold more than 10 days and at most a year away takes that date and tournament name. Its own match means the same pair, round and games per set, in an event of the same id or sharing a name word. A row with two such twins, or one at its own date, is left as it is.
  * **Moved:** 1,841 rows (1,659 by Sackmann's twin, 166 by TennisLive's listing, 16 with the rest of their event), listed in `data/studies/data_map/tml_redated.csv`.
  * **Against the P6 data-issues study's reviewed list of misdated editions:** 57 of its 68 are moved, 56 to its date. The 57th, the 2021 Australian Open qualifying played in Doha, lands one day apart. The other 11 are dated 7-9 days off, and the map's linker joins those to Sackmann's copy anyway.
  * **Against its list of 1,586 doubles:** all 1,575 of this kind are gone. 1,548 are held once at their true date; the other 27 are pairs that really met twice that season (Sackmann lists both meetings).
  * **The map:** 709,194 → 708,199 matches. Men's Challengers and their qualifying of 2018-25 lose 1,646 (2021: 6,914 → 6,313). The 2021 Biella events go from 454 to 298 matches (seven editions of 43 make 301).
  * **The gap downloads stay attached.** Their frozen lists name the old copies, so the placement also reads the keys of the copies merged into each match (`placement_index`). Placed by their own links: all 34,453 SofaScore records, all 131 Flashscore records, and 36,851 of 36,903 TennisLive page rows.
  * **The gaps** (map of 15:55 UTC → 19:26 UTC): `challenger_points_2018_2021` 737 → 666, `challenger_points_2022_2024` 232 → 217, `wta_2018_points` 51 and `qualifying_points_2018_2026` 216 unchanged.
* **Not fixed here:**
  * 11 doubles of another kind: the last rounds of 2026's two-week events (Australian Open, Indian Wells, Miami, Rome, Roland Garros). Tennis My Life dates them by the day played, 11 or more days after Sackmann's start date.
  * **Shared keys, not doubles** [observed]. 17 pairs of Challenger matches share one key on the map (tour, event name, date, players and draw). In each, the same two players met at two editions a week apart that Tennis My Life files under one name and date: Burnie 2019 and 2020 (with Launceston's matches); Antalya 1, Potchefstroom 1, Split 1, Almaty, Salinas and Napoli 2021 (Napoli with Ercolano's); Oeiras 1, Shymkent 1 and Nonthaburi 1 2022; Nonthaburi 1 2023; Indian Wells 1 2024. So one row of each pair is 6-9 days from Sackmann's date for it, within the 10 days the rule leaves alone. Their Tennis My Life rows differ in round and score, and the map holds two matches for each pair, as it should. But one of each pair carries the other edition's date, and a download frozen under the shared key is placed by the map's own linker instead. The other keys that name two matches are 3 pairs that met in the round robin and again in the final of the ATP Finals, and 2 at ITF events (not checked).

## WTA website records after early September (work package P2(b))

**Status: done on 14 October 2026, and kept current every week since by the scheduled job `wta_site` ([below](#running-and-resuming-p2b)).** [Work package P2(b)](collection-plan.md#p2-wta-api-the-2026-editions-since-the-batches-and-womens-itf-results-after-early-september) collected the women's ITF and ITF-qualifying results the WTA website lists after early September 2026. Kaggle still serves version 29 (24 Sep 2026), so they came from the WTA API's player-matches endpoint, the website's own source, player by player. Part (a), the WTA API's catch-up, is reported in [official_point_feeds](../official_point_feeds/README.md#the-catch-up-of-11-and-13-october-2026-work-package-p2a). Process log: [process_log.md](process_log.md).

**In short [observed]:**
* Every 2026 list of 4,467 players: 32,465 played singles at every level, 14,378 ITF main-draw and 12,436 ITF-qualifying matches among them.
* 4,445 ITF results the Kaggle copy lacks. 1,326 main-draw and 1,071 qualifying matches of those are at editions starting in September or October, and 994 and 770 at editions after 7 Sep.
* **The website lists a week's ITF results a week or two late.** On 11 Oct it held the editions of 21 Sep in part and nothing later. A second crawl on 13-14 Oct reached those of 28 Sep and some of 5 Oct. Against the ITF's own data it holds 97%, 96%, 76% and 17% of the women's ITF singles of the weeks of 14, 21 and 28 Sep and 5 Oct.
* Where another source holds the same match, the winner always agrees: 22,342 of the Kaggle copy's 22,396 played 2026 ITF singles are found, every one with its winner (22,339 with its score); TennisLive and the ITF's data confirm 1,710 and 1,539 of the 1,753 results after 7 Sep, no winner differing.
* 6,854 requests over 11-14 Oct, with no block, challenge or pause.

### What changed from the plan [observed]

* **No newer Kaggle version.** On 11 Oct, Kaggle's current version of `bwandowando/womens-tennis-association-matches-1975-present` was still 29 (2 requests; nothing downloaded; the answers kept in `data/raw/gap_sources/bwandowando/_checks/`). `src/eda/gap_sources/wta_site_kaggle.py --fetch-only` now puts any later version in its own folder `v<N>/`, beside version 29, and the map reads the newest.
* **The endpoint is paged.** Without `pageSize`, a page holds the year's first 10 matches. All five trial players got exactly 10, against 15-55 rows each in the Kaggle copy. `page` counts from 0 and no total is sent, so the mode reads `pageSize=100` and pages until one comes back short (64 of 4,467 players needed two pages).
* **`perspective_player_id` is not a player id.** On 34,971 of the Kaggle copy's 44,604 rows of 2026 ITF events it is a small label (23, 150 ...) covering many players. `player_1`, the player the website was asked about, holds the WTA id. A first trial seeded from the plan's field asked for "players" 1 to 6 and stalled. The starting set is the 2,113 `player_1` ids at 2026 ITF events, frozen in [wta_player_seeds_2026.csv](../../../data/studies/gap_downloads/wta_player_seeds_2026.csv); the wrong list is kept as `wta_player_seeds_2026_superseded_perspective_ids.csv`.
* **The API's quirks:**
  * an unknown id answers HTTP 200 with an empty body, recorded once as absent;
  * id 1 is a bye's placeholder ("BYE BYE");
  * `tourn_nbr` is fixed-width (`' 901'` for group 901), so editions are keyed by the tournament object's group id; keyed by `tourn_nbr`, 100 of 541 editions missed their Kaggle twin;
  * `TournamentLevel` is a code (C, IS, P, PM, GS, ITF); the tournament object's `level` gives the name.
* **The website's lag** made a second crawl worth its cost. It re-asked only players whose 11 Oct list showed a match since 1 Aug, since a list grows only at its end.
* **Raw pages** are `players/<id>/matches_<year>_<page>.json.gz`, not the plan's `matches_<year>.json.gz`. The five trial answers at that path hold the default 10 matches and are not staged.

### The crawl [observed]

Players: the starting set (wave 0), then every singles opponent the answers name that is not yet known, wave by wave, until none is new. Doubles partners and opponents are not followed, nor the bye placeholder. Pace: 2 s plus up to 1 s.

| Run | When (UTC) | Requests | Players | Answers |
|---|---|---:|---:|---|
| First crawl | 11 Oct 16:02-19:09 | 4,436 | 4,410 (waves 2,113 / 2,006 / 283 / 8) | 4,432 pages; 2 players unknown; 1 page failed (HTTP 502 four times), asked again on 13 Oct and answered |
| Second crawl | 13 Oct 23:06 – 14 Oct 00:46 | 2,366 | 4,467 (2,113 / 2,058 / 286 / 10), 2,165 pages replayed from disk | all answered; 57 players new since 11 Oct |
| Trials, probes, Kaggle, the retry | 11 and 13 Oct | 52 | – | the five-player trial (default pages, 5), 3 paging probes, the failed trial (10, 9 of them errors), 1 unknown-id probe (not kept: empty), the 25-player trial, 5 lag probes, 2 Kaggle requests, and the retry of 13 Oct |

* **Staged:** `data/dump/points/wta/player_matches/2026.parquet` holds 99,787 served rows, one per player asked and match, doubles included. `player_results/2026.parquet` holds 32,465 played singles. Byes, walkovers (D) and unplayed matches (UNP, V) are left out, as the map reads the Kaggle copy. Each match is kept once: the two players' rows are joined through keys of the edition, draw and round with both ids, or one id and the other's surname. 32,211 results are listed by both players, 252 by one, 2 by three.
* **The 11 Oct pages** that the second crawl replaced are kept in `data/raw/point_sources/wta/players_snapshot_20261011/` (4,462 files, 26 MB).

### Results by week and Expected [observed]

ITF results at editions starting after 7 Sep 2026, main draw / qualifying, by the edition's week; and, by the week a match was played (Monday to Sunday), the ITF's and TennisLive's women's ITF singles found among the 13-14 Oct results:

| ITF week | First crawl (11 Oct) | Second crawl (13-14 Oct) | Played that week: found of the ITF's (of TennisLive's) |
|---|---|---|---|
| 14 Sep | 248 / 188 | 248 / 188 | 361 of 373 (439 of 465) |
| 21 Sep | 124 / 95 | 309 / 268 | 518 of 542 (544 of 570) |
| 28 Sep | – | 328 / 256 | 521 of 683 (531 of 695) |
| 5 Oct | – | 109 / 58 | 141 of 847 (142 of 746) |
| 12 Oct | – | – | 0 of 271 |

* **Against Expected:** the plan expected about 3,000 main-draw results after early September, plus qualifying. On 14 Oct the website lists 994 main-draw and 770 qualifying results after 7 Sep. The shortfall is the website's lag, not the crawl: no player's list holds a later week, and the five players probed on 13 Oct had gained the week of 28 Sep in two days [inference from the probe].
* **The weeks of 14 and 21 Sep look complete** on the website. About 4% of the ITF's matches are not found, scattered over events (Maanshan 10 of 82, Monastir 7 of 118, Wagga Wagga 5 of 7). Examples suggest the check's name matching more than missing records [inference]: 'Laura Boehner' is written 'Bohner' by the WTA, and same-surname pairs (Qu v Qu, Xu v Xu) have no pair key.

### Checks [observed]

`src/eda/gap_downloads/verify_wta_player_matches.py` writes [wta_player_matches_check.json](../../../data/studies/gap_downloads/wta_player_matches_check.json) and `wta_player_matches_check.csv.gz`, one row per TennisLive or ITF match from the cut on.

* **Against the Kaggle copy** (the same website, read in September), by edition, draw, round and both players' ids: 22,342 of its 22,396 played ITF singles of 2026 are found (99.76%). Every one has the same winner and 22,339 the same score; every month from January to August is complete but for 2 July matches. The results hold 4,445 ITF matches the copy lacks: 1,880 at editions of January-August, mostly qualifying matches between players it never asked about; 2,397 at editions of September and October (above); 168 at editions starting in December 2025.
* **Against TennisLive's event listings** (P4, to 4 Oct) and **the ITF's live-data API** (P1, from 15 Sep), through `verify_tennislive.check` with the results standing in for official rows:
  * TennisLive: 1,715 agree, 3 have the same winner and another score, 823 are not in the results;
  * the ITF: 1,534 agree, 7 have the same winner and another score, 1,175 are not in the results;
  * no winner differs.

  Read the other way, they confirm 1,710 and 1,539 of the 1,753 results after 7 Sep.
* **Inside the results:** one match is listed with two winners, Evansville W100's first round (Stephens v Jeong, three rows). 28 results lack the loser's id: qualifying opponents the website names without one.

### On the map [observed]

Rebuilt at 00:50 UTC on 14 Oct 2026 (`./python.sh src/eda/data_map/build.py`; window to 11 Oct; no catalog problem).

* **The reader:** `load_wta_site` in `src/eda/data_map/measure.py` reads the newest Kaggle copy, then the API's results. Each API row joins its Kaggle edition by tournament group and start date, and is left out when that edition holds the same draw, round and surname pair. Against the Kaggle copy alone (281,706 rows from 2018), the API adds 4,959 rows: 1,454 ITF, 2,706 ITF qualifying, 397 WTA 125, 133 WTA 125 qualifying and 337 others. Most of these are matches other sources already hold, so they link to known matches rather than add new ones. 68 of the copy's own qualifying rows change round (Q1 to Q2, Q2 to Q3): the API supplies those editions' first qualifying round, which the copy lacked, and rounds are counted from it.

| Women's 2026 cell | 10 Oct (to 4 Oct) | 12 Oct (to 11 Oct; first crawl, keyed with the flaw) | 14 Oct (to 11 Oct) |
|---|---:|---:|---:|
| ITF | 14,159 | 14,661 | 14,675 |
| ITF qualifying | 12,499 | 12,678 | 12,917 |

* **The WTA website as a source:** 26,415 of the 27,592 women's ITF and ITF-qualifying matches of 2026 on the map now carry it. By the edition's week after 7 Sep: 430 of 432 (14 Sep), 572 of 576 (21 Sep), 582 of 619 (28 Sep), 167 of 870 (5 Oct), none of the 175 of 12 Oct. The map adds the website's records before TennisLive's listings, so it is these rows that create the matches and the others that link to them.
* **The 12 Oct build**, made by another session, read the first crawl's results while three-digit group ids still carried their leading space. For 100 editions its API rows were not matched to the Kaggle copy's, and only the map's linker kept them from being counted twice. This build replaces it.
* No estimate of missing matches is left in these cells. The gaps `itf_after_june_2026` and `men_itf_qualifying` were already filled by P4's listings.

### Running and resuming P2(b)

From the repository root, in Git Bash:

```
./python.sh -m src.ingest.point_sources.wta --player-matches --player-year 2026 --max-requests 8000          # the crawl; rerun to resume
./python.sh -m src.ingest.point_sources.wta --player-matches --player-year 2026 --max-requests 6000 \
    --refresh-before <UTC time of the rerun> --refresh-active-since <a date some weeks back>                  # pick up the weeks listed since
./python.sh -m src.ingest.point_sources.wta --player-matches --player-year 2026 --stage-only                   # no HTTP: replay and restage
./python.sh src/eda/gap_downloads/verify_wta_player_matches.py                                                # the checks
./python.sh src/eda/data_map/build.py
```

* **Resumes:** every page is kept with a receipt and not asked again. A rerun replays the crawl from the frozen seeds, reading cached pages from disk, and asks only for pages it lacks or whose answer failed. `--stage-only` replays with a client that may make no request.
* **Stops** on a block (HTTP 403 or 429, a challenge, a redirect, a reset). Five errors in a row pause it for 10 minutes; 150 absences in a row stop it.
* **Later weeks come by themselves** (since 14 Oct 2026, the owner having asked for "this data to come in automatically with the other repeating data acquisition"; [cadence decision, amendment of 14 Oct](../../decisions/2026-10-06-download-cadence.md)). The weekly job `wta_site` of `src/ingest/scheduled.py`, every Tuesday in the lower-level feed's task, runs
  ```
  ./python.sh -m src.ingest.point_sources.wta --player-matches --player-year <year> --max-requests 3000 \
      --refresh-before <the run's start> --refresh-active-since <six weeks back> --refresh-rotation 6
  ```
  * *Who is asked again:* each player whose list shows a match in the last six weeks, and one in six of the rest in turn, so every player at least every six weeks. New opponents are followed. About 2,400 requests.
  * *Staging:* for Wednesday's lower-level feed, which reads these results as its source `wta_site` (`candidate_stage0.py`).
  * *Year ends:* until mid-February the previous year's lists are refreshed too, and a new year starts from the previous year's ITF players (`frozen_seeds`; the Kaggle copy has no 2027).
  * *An alert* when the newest ITF edition listed is more than six weeks old.
  * *By hand:* `./python.sh -m src.ingest.scheduled --only wta_site`.
* Logs: `data/raw/point_sources/wta/_logs/P2b_*.log` and `P2_topup_*.log`.

### Files

| File | What it is |
|---|---|
| [wta_player_seeds_2026.csv](../../../data/studies/gap_downloads/wta_player_seeds_2026.csv) | The 2,113 starting players, frozen at the first run, with the Kaggle folder read |
| `wta_player_players_2026.csv.gz` | One row per player asked: wave, outcome, pages, rows, singles, new opponents, last edition |
| [wta_player_matches_2026_summary.json](../../../data/studies/gap_downloads/wta_player_matches_2026_summary.json), [runs.jsonl](../../../data/studies/gap_downloads/runs.jsonl) | The last run's counts (seeds, waves, outcomes, results by level and week) and one line per run |
| [wta_player_matches_check.json](../../../data/studies/gap_downloads/wta_player_matches_check.json), `wta_player_matches_check.csv.gz` | The checks above |
| `wta_player_matches_check_crawl_20261011.json` | The same checks on the first crawl; its Kaggle section predates the group-id fix and is superseded |

* **Code:** `src/ingest/point_sources/wta.py` (`--player-matches`: `fetch_player_pages`, `crawl_players`, `player_results`, `stage_player_matches`); `src/eda/gap_sources/wta_site_kaggle.py` (`--fetch-only`); `src/eda/gap_downloads/verify_wta_player_matches.py`; the map's reader `load_wta_site` and `wta_site_api_rows` in `src/eda/data_map/measure.py`.
* **Tests:** `./python.sh -m pytest test/official_point_feeds/test_wta_player_matches.py test/gap_downloads/test_verify_wta_player_matches.py test/data_map -q`.
* **Raw** (gitignored): `data/raw/point_sources/wta/players/` and `players_snapshot_20261011/`; the paging, lag and Kaggle probes in `data/raw/point_sources/wta/probe/players/` and `data/raw/gap_sources/bwandowando/_checks/`; receipts in `data/raw/point_sources/wta/_receipts.jsonl`.

### Limits

* **The website's lag.** On 14 Oct results ended with the ITF editions of 5 Oct, partly listed. Later weeks arrive with the weekly job `wta_site`, a week or two behind the play, as the website lists them.
* **The second crawl re-asked only players active since 1 Aug.** It can miss a match after 21 Sep between two players neither of whom had played from 1 Aug to 21 Sep. The weekly job's rotation re-asks every idle player within six weeks, which closes that gap by late November (six weekly runs from 20 Oct).
* **The crawl's reach.** A player is reached only through a chain of singles opponents from the starting set. A group that met only each other in 2026 would be missed; none can be counted from here.
* **The website's own records.** One match has two winners; 28 losers have no id; ITF events the website does not carry would be missing from it (one such event is suspected, Wagga Wagga).
* **Not on the leak-proof clock, nor in Stage 0.** The results reach the map only. The map reads them with the Kaggle copy (`measured_as: wta_site`). `src/eda/match_timing/` and Stage 0 do not read them, and the lower-level evidence study's candidate Stage 0 reads the Kaggle copy (version 29) alone. Wiring them in is separate work, and new lower-level history enters the model only as a candidate (CLAUDE.md).
* **Rights.** wtatennis.com forbids automated access and harvesting; collected under the owner's decision of 8 October 2026 ([decision](../../decisions/2026-10-08-scraping-approved.md)).

## Bookmaker odds below the 250s (work package P11)

**Status: collecting (the backfill from 22 October 2026, 12:51 UTC; a daily job from 22 Oct). The forward-capture test is done (24 Oct); whether to record Pinnacle's own site through the day is the owner's decision ([below](#forward-capture-of-closing-lines-the-test-done-24-oct-2026)).** [Work package P11](collection-plan.md#p11-bookmaker-odds-below-the-250s-probe-then-collect) asks which public site holds bookmakers' opening and closing odds for Challenger, WTA 125 and ITF matches of 2018-2026, to collect from the best one, and to test a forward capture of closing lines. Prices stay out of git: every table under `data/studies/` here holds counts and flags only. [Process log](process_log.md#work-package-p11-bookmaker-odds-below-the-250s-probe-collect-forward-capture).

**In short:**
* **TennisExplorer is the best source at every level** [observed]. Where BetExplorer lists a level, TennisExplorer lists as much. It alone has Pinnacle, opening prices and every price change with its time, ITF matches of 2019, and ITF qualifying. OddsPortal could not be read past its anti-bot layer.
* **Pinnacle below the tour level** (the probe's match pages): on 40 of 40 Challenger and WTA 125 main-draw matches, 25 of 40 ITF main-draw matches (2 of 10 in 2019, 7-8 of 10 in 2022-26), 6 of 13 Challenger and WTA 125 qualifying matches, and 0 of 16 ITF qualifying matches.
* **The collection is running** in the background, newest day first, back to January 2018: about 250 priced matches a day of October 2026, about 105 of January 2026; roughly 600,000 requests, about three weeks if nothing stops it (2025-26 in about four to five days).
* **The forward-capture test** (24 Oct): below the tour level TennisExplorer's last Pinnacle price is Pinnacle's close on 75% of the matches where it shows one, and it shows one on 76% of the matches Pinnacle lists. The site stops recording hours before the start and misses late moves. Only reading Pinnacle's own site through the day gives every true close ([below](#forward-capture-of-closing-lines-the-test-done-24-oct-2026)).

### The sample

One week per year, drawn with a fixed seed among the weeks that hold a WTA 125 and several men's Challengers and ITF events of both tours: 25 Feb 2019, 9 May 2022, 14 Jul 2025 and 5 Jan 2026. Every map match of those weeks' Challenger, WTA 125 and ITF editions (main draw and qualifying) is in it: 6,043 matches. Each site was read by day over each week's span of play (the Saturday before to the Sunday after). For a few matches per level and year (5 main-draw, 2 qualifying), the first ones in a fixed random order that the site lists, the match's odds were read book by book.

### What each site holds [observed]

Requests: BetExplorer 141, TennisExplorer 181 (after the other session's TennisExplorer download ended at 12:07 UTC; one collector per site), OddsPortal 24. No site refused: every answer was HTTP 200 except one OddsPortal address that the probe guessed (404).

| Sample matches listed: TennisExplorer / BetExplorer | 2019 | 2022 | 2025 | 2026 |
|---|---:|---:|---:|---:|
| Men's Challengers | 140 / 138 of 141 | 153 / 153 of 190 | 114 / 112 of 123 | 150 / 150 of 154 |
| WTA 125 | 47 / 43 of 48 | 60 / 60 of 60 | 61 / 61 of 62 | 31 / 31 of 31 |
| Men's ITF main draw | 175 / 30 of 184 | 400 / 405 of 415 | 512 / 504 of 524 | 210 / 211 of 218 |
| Women's ITF main draw | 204 / 0 of 215 | 382 / 376 of 407 | 444 / 441 of 463 | 195 / 196 of 200 |
| Men's Challenger qualifying | 5 / 0 of 5 | 77 / 75 of 80 | 72 / 70 of 72 | 90 / 86 of 90 |
| ITF qualifying, both tours | 212 / 0 of 219 | 756 / 0 of 792 | 910 / 0 of 945 | 351 / 0 of 359 |

Each site misses 37 of the 2022 Challengers, 33 of them the same matches. Main-draw matches that TennisExplorer lists nearly all show prices. ITF qualifying shows prices less often: 93 of 219 in 2019, 366 of 792 in 2022, 229 of 945 in 2025, 128 of 359 in 2026.

**TennisExplorer's match pages** (5 main-draw and 2 qualifying matches per level and year, the first in a fixed random order that the site lists with prices; 109 pages):

| | Books (median) | Pinnacle |
|---|---:|---:|
| Challengers and WTA 125s, main draw | 15-16 | 40 of 40 |
| ITF main draw | 5 (2019), 12-15 (2022-26) | 25 of 40 (2019 2, 2022 8, 2025 8, 2026 7, of 10 each) |
| Challenger and WTA 125 qualifying | 3-16 | 6 of 13 (none before 2025) |
| ITF qualifying | 2-7 | 0 of 16 |

* **Each book's price comes with every change and its time, and the opening with its time.** Pinnacle's prices carry times on 67 of the 71 pages that show it. The site's day listing shows the books' average last price for every listed match.
* **Pinnacle's last change** came a median 98 minutes before the listed start (a quarter within 29 minutes, a quarter more than 3.8 hours before; one a minute after the start). Whether that last price is Pinnacle's close is what the forward-capture test checks (below).

**BetExplorer** has odds on every match it lists, from 4 to 16 books (a median of 7-11 for ITF, 14-16 for Challengers and WTA 125s), each with its closing price and the time it was set. But:
* it shows **no Pinnacle** from this connection, as the Pinnacle-gap research found at tour level;
* its odds table has **no opening price**: that takes one more request per book and side;
* it lists **no ITF qualifying, and almost no ITF of 2019**.

**OddsPortal:**
* Its pages are script shells. The match lists come from feeds that the page decrypts (AES with a key in its public script). The project decrypted one with the page's own steps, which the 8 October decision covers.
* **The date feed serves only the last 30 days**; older matches sit in per-tournament archives.
* **A match's odds load behind an anti-bot layer:** a proof token the page mints every few minutes, and honeypot links. Getting past that is outside the 8 October decision, so the probe stopped there.
* Its books carry BetExplorer's numbering (the two sites share their odds), so it would likely repeat BetExplorer's prices. Whether it shows Pinnacle to this region is unknown.

### The choice

The plan's rule was the best closing coverage at each level, then Pinnacle (the model's odds input is Pinnacle first). **TennisExplorer wins at every level:** it ties BetExplorer on Challengers, WTA 125s and ITF main draws of 2022-26, is alone on ITF of 2019 and on ITF qualifying, and alone has Pinnacle and opening prices. Collected: `src/ingest/tennisexplorer_lower.py`.

### The collection

**How it works:**
* Day by day, newest first: the day's two results pages (men and women), then the page of every in-scope match the day lists with prices.
* **In scope:** Challengers (any type on the site's calendar), the men's ITF the site lumps as "Futures", and every event the calendar does not type as tour level: women's ITF and WTA 125s. Main draws and qualifying alike.
* **Out of scope:** the tour level (the tour adapter's), exhibitions, leagues, team and UTR events. Matches listed without prices have no book on their page and are not asked.
* **Its own folders** (`data/raw/tennisexplorer_lower/`, `data/dump/odds/tennisexplorer_lower/`), so a lower-level page never reaches the tour-level staging that the model's odds input reads.
* **It waits** whenever the tour-level adapter (the daily `pinnacle_closes` job) or the model's odds step uses the site.
* **Pace:** 2.5 seconds plus up to 1 between requests, the tour adapter's pace, which held for 10,000 pages without a refusal. It stops at the first refusal.

**Trials [observed]:**

| | Requests | Match pages | Pinnacle on | Books (median) |
|---|---:|---:|---|---|
| A: 20-21 Oct 2026 (budget 500, used up) | 500 | 494, all parsed | Challengers 66 of 76; men's ITF main 157 of 235; women's ITF and WTA 125 83 of 145; men's ITF qualifying 0 of 38 | 15, 9, 11, 2 |
| B: 26 Feb 2019 | 132 | 128, all parsed | Challengers 35 of 35; women's ITF and WTA 125 main 14 of 37; men's ITF main 0 of 26; qualifying 0 of 30 | 15, 5, 5, 3 |

* *Expected* (shared rule 5), from the probe's own day listings: about 105 priced matches a day (the January 2026 week). Trial A reached about 250 a day, as October is busier.
* 250 of trial A's 306 Pinnacle rows carry times. The rest show one price with no change table.

**The bulk** started at 12:51 UTC on 22 Oct, detached: runs of 10,000 requests, each staged after it, newest day first from 21 Oct back to 1 Jan 2018.
* *Expected [inference]:* roughly 400,000 requests at about 1,200 an hour, so about two weeks, if nothing stops it. 2025-26 should be done in about four to five days.
  * *Revised 24 Oct:* the first 51,170 requests covered 266 days (about 190 a day), so the span to 2018 is roughly 600,000 requests: about three weeks in all, to mid-November if nothing stops it.
* *Progress:* the data map's `in_progress` line, and `data/raw/tennisexplorer_lower/_logs/bulk.log`.

### Forward capture of closing lines: the test, done 24 Oct 2026

**What was compared.** For the lower-level matches of 22-23 Oct, two records of Pinnacle's closing price:
* **(A) Pinnacle's own site**, read every 10 minutes for 36 hours (04:50 UTC on 22 Oct to 16:50 UTC on 23 Oct: 216 reads, 463 requests, no refusal), into its own folders, apart from the bet-day recorder's. A match's last price before its start is its captured close.
* **(B) TennisExplorer's page of the same match**, fetched after play: the last Pinnacle price the site recorded, and when.

**Result** [observed; `pinnacle_capture_compare.json`, complete]:

| Lower-level matches Pinnacle listed that started, 22-23 Oct | Challengers | ITF main draws | All |
|---|---:|---:|---:|
| Captured from Pinnacle's own site (A) | 35 | 224 | 259 |
| Found on TennisExplorer | 34 | 215 | 249 |
| With a Pinnacle price there (B) | 32 | 165 | 197 |
| (B)'s last price equal to (A)'s close, both sides to 0.005 | 20 | 128 | 148 |

* **Pinnacle listed no qualifying match** at these levels in the 36 hours, so neither route gives a Pinnacle price for qualifying.
* **(A) reached every match Pinnacle listed** with a price a median 10 minutes before the listed start (quartiles 7 and 20 minutes): Pinnacle keeps these markets open until close to the start.
* **(B) gave Pinnacle's true close for 148 of the 259 (57%).** The site had a Pinnacle price for 197 (76%), equal to the close on 75% of those (80% on 22 Oct, 68% on 23 Oct).
* **Why (B) misses:** the site stops recording Pinnacle's lower-level prices hours before the start. Its last recorded change came a median 3.6 hours before the listed start (quartiles 2.0 and 4.2 hours), never after it.
  * Of the 49 matches where its price differed from the close, in 36 Pinnacle moved its line after the site's last recorded change; 8 had no times on the site; about 5 cannot be checked (the capture began later).
  * In none of the 148 equal ones did Pinnacle move after the site's last change. So the site's record is right up to the point where it stops.
* **Late moves are common:** of the 185 captured matches whose price moved at all, 82 had their last move in the final 3 hours and 44 in the final hour.
* At tour level the site matched Pinnacle's own price on 93% of readings, with its last change about an hour before the start ([Pinnacle-gap research](../../research/pinnacle-gap/README.md)). Below the tour level it is staler.

**What it means** [inference]:
* **The backfill's lower-level Pinnacle prices are late pre-match prices, not closes:** equal to the close on about 3 matches in 4 where the site shows Pinnacle. The other books' prices on those pages carry the same caution, untested here.
* **A true lower-level close can be had only by reading Pinnacle's own site through the day.** A close not captured on the day is lost for good: no free archive has it.

**Recommendation (the owner's decision).** Keep the daily TennisExplorer job: it is the only history (2018 on) and the only record of the other books and of openings. **And start recording Pinnacle's own site every 10 minutes as a standing job, if lower-level markets may be bet in the coming months** (Polymarket's lower tier is about a fifth of its tennis money).
* **For it:** the true close for every lower-level match Pinnacle prices; a model's odds input is Pinnacle's close ("Pinnacle first"), and the backfill's would carry an earlier price on a quarter of rows; closes not recorded now cannot be recovered later.
* **Against:** the PC must stay on and online all day. About 300 requests a day to the site the bet-day recorder already reads (a read is skipped while a bet-day pull runs), and about 10 MB a day of raw copies and tables: the 36-hour test used 463 requests and 15 MB.
  * **When the PC is off,** those hours' closes are lost from this record, and their matches keep only TennisExplorer's late price.
  * **Most lower-level matches start overnight in California:** 62% of October 2026's 5,195 priced ones between midnight and 08:00 Pacific, 68% between 22:00 and 08:00. A PC switched off at night would miss about two-thirds of them.
* **If yes:** the daily task can start the existing capture loop each morning for 24 hours (`pinnacle_capture.sh`, its own folders), with the same alerts as the other jobs. Not started: it is a new standing job on the owner's PC.

### Daily from 22 Oct 2026

**The daily job** (the owner, 22 Oct: "Implement gathering lower level odds daily"; [cadence amendment](../../decisions/2026-10-06-download-cadence.md)):
* `lower_odds` in the daily task (07:30), right after the tour-level `pinnacle_closes`. It runs the collector over the last 21 days: each day not yet done, its listings, then every priced lower-level match page, at most 1,500 requests.
* While the backfill runs, the job is skipped: the backfill starts each run from the newest day. The real 07:30 task of 23 Oct ran it so (skipped, and the comparison's check said "not ready").
* **The comparison's reminder is spent:** the job checked each day whether the comparison could run (`pinnacle_capture.py --ready`), and the complete comparison of 24 Oct stops it. To run the comparison again: `./python.sh src/eda/gap_downloads/pinnacle_capture.py --compare` (writes `pinnacle_capture_compare.json` and `.csv.gz` here, counts only).

### Running and resuming P11

From the repository root, in Git Bash:

```
./python.sh src/eda/gap_downloads/odds_probe.py --report                       # offline: every probe measure
./python.sh -m src.ingest.tennisexplorer_lower --stage-only                    # offline: restage the changed months
./python.sh src/eda/gap_downloads/pinnacle_capture.py --closes                 # offline: the captured closes
./python.sh src/eda/gap_downloads/pinnacle_capture.py --compare                # offline, once the site's pages of those days are in
```

* **The bulk** runs detached. If it stopped (the PC slept or restarted, or a run ended on a refusal), start it again from PowerShell; it resumes where the receipts end, and days already done are skipped without a request:
  ```
  $env:BUDGET="10000"; $env:MAX_RUNS="60"; $env:SINCE="2018-01-01"; Start-Process -WindowStyle Hidden -FilePath "C:\Program Files\Git\bin\bash.exe" -ArgumentList '-l','-c','"/c/Users/zerom/Documents/Tennis-predictions/src/ingest/tennisexplorer_lower_bulk.sh"'
  ```
  A refusal (exit 2 in `bulk.log`) is a block: wait at least a day before restarting, and check that the daily `pinnacle_closes` job gets through first.
* **The capture** runs detached (`src/eda/gap_downloads/pinnacle_capture.sh`, log in `data/raw/pinnacle_capture/_logs/`). If it stopped early, rerun it the same way; each pull is its own file.

### Files

* *Probe evidence* (counts and flags, no price): `data/studies/gap_downloads/odds_probe_sample.csv` and `.json` (the sample); `odds_probe_<site>.csv.gz` (one row per sample match: listed, priced, and on the detail matches the number of books, Pinnacle, times) and `.json` (by level and year), for `betexplorer` and `tennisexplorer`. Made by `src/eda/gap_downloads/odds_probe.py`.
* *Collection evidence:* `tennisexplorer_lower_summary.json` (the last run and counts by month) and `runs.jsonl`.
* *Raw* (gitignored): `data/raw/odds_probe/<site>/`, `data/raw/tennisexplorer_lower/`, `data/raw/pinnacle_capture/`, each with `_receipts.jsonl`.
* *Staged* (gitignored): `data/dump/odds/tennisexplorer_lower/{listed,matches,odds,moves}/<month>.parquet`, every column a string; `data/dump/odds/pinnacle_capture/pulls/`.
* *Comparison evidence* (when run): `pinnacle_capture_compare.json` and `.csv.gz` (counts and flags only).
* *Tests:* `test/gap_downloads/test_odds_probe.py`, `test_tennisexplorer_lower.py`, `test_pinnacle_capture.py` (synthetic pages, made-up prices), `test_lower_odds_job.py` (the daily job and the reminder, child processes faked).

### Limits

* **The samples are small:** 5 main-draw and 2 qualifying match pages per level and year in the probe. The trials' 622 pages are the better guide to Pinnacle's share.
* **"Closing" is the site's last recorded price.** Below the tour level the forward-capture test found it equal to Pinnacle's own close on 75% of matches (22-23 Oct). The site's record stops a median 3.6 hours before the start. At tour level it matched Pinnacle's own price to the cent on 93% of readings ([Pinnacle-gap research](../../research/pinnacle-gap/README.md)).
* **Not linked to the map or Stage 0.** The staged tables keep the site's match ids and names. Linking them to the project's matches is separate work, as is anything the model would read: new lower-level data enters the model only as a tested candidate (CLAUDE.md). Odds are not counted on the data map's match table.
* **The same site as the daily `pinnacle_closes` job.** A block of the bulk would also block that job, which the model's odds input reads from November 2025. Hence the tour adapter's pace, the wait whenever it runs, and the stop at the first refusal.
* **Rights.** TennisExplorer's, BetExplorer's and OddsPortal's terms restrict automated extraction; collected under the owner's decision of 8 October 2026 ([decision](../../decisions/2026-10-08-scraping-approved.md)). Never republish: this repository is public.
