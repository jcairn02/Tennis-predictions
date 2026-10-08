# The data map's eight gaps: which suggested sources actually hold the data

**Status: research, not a decision.** Checked on 29 September 2026. Each card on the [data map](../../../data/data_map.html) names where its missing data "could come from" (`gaps:` in [data_map.yaml](../../../data/data_map.yaml)). This page checks every suggestion against the data itself, adds the sources found on the way, and proposes a final list.

**How it was checked.** For the five gaps made of known matches, a seeded random sample: 75 tournament editions, and in them 226 matches read on SofaScore and on TennisLive, with the listing measured on 3,573 gap matches. The other gaps were checked against the sources' own listings, calibrated on years the project's files cover. Four research lanes ran in parallel; their reports are in [research_notes/](../../../data/studies/gap_sources/research_notes/). Evidence, scripts and reruns: [data/studies/gap_sources/](../../../data/studies/gap_sources/README.md).

**Nothing was bought, no account was opened and nothing was decrypted.** SofaScore, TennisLive and the WTA API were read as bounded measurements under the owner's decisions of 23-25 September. SofaScore blocked the plain client after about 830 requests (HTTP 403 "challenge"). Its last two Slam editions and its count of 2025-26 ITF listings were not read.

## The proposed list

"Filled" is the measured share of the gap's sampled matches, applied to the gap; the checks behind each figure are in the gap's section below. Sources are in the order proposed.

| Gap | Missing | Sources, in order | What they fill (measured) | Grain added | Status of the route |
|---|---:|---|---|---|---|
| **ITF 2018-2024 with only a result** | 201,946 | 1. **SofaScore** | Box score 82 of 84 sampled; complete points 78 of 84. About 196,600 box scores and 186,600 point records | Stats + point | Adapter exists; needs a by-tournament listing mode |
| | | 2. **TennisLive** | Box score 81 of 84; points 80 of 84, but set-closing games missing | Stats (+ partial point) | Adapter exists; one page per match |
| **Women's ITF qualifying 2025-26** | ≈28,555 (est.) | 1. **WTA website's match records**: Kaggle copy `bwandowando/…-matches-1975-present` (v29, 24 Sep 2026), or the WTA API's player-matches endpoint directly | 25,014 matches with scores (15,196 in 2025; 9,818 in 2026 to early September). 92-106% of Sackmann's volume in every year 2019-24 | Result | Kaggle file downloaded; the endpoint is on the API the 24 Sep decision covers |
| | | 2. TennisLive (tournament listings) | Qualifying listed, with results, for every 2026 event sampled (2025 not sampled) | Result | Adapter exists; needs an event-listing mode |
| **Women's shot-by-shot** | 17,854 | 1. **Tennis Abstract website-only charts** | 2,061 gap matches: 1,467 in the Hugging Face copy, 594 only on the website | Shot | HF download plus pages to parse |
| | | 2. **Hawk-Eye Court Vision copies** (`hawkilol`) | 621 women's AO and RG matches, 2019-24 | Shot (tracking) | Downloaded |
| | | — | About 15,000 matches (mostly WTA 250-1000) have no public shot source | | |
| **Challenger points, 2025-Jun 2026** | 14,438 | 1. **SofaScore** | Complete points 31 of 32, box 32 of 32. About 14,000 | Point + stats | Adapter exists |
| | | 2. TennisLive | Points 32 of 32, 1 complete | Partial point | Adapter exists; one page per match |
| **ITF results after early June 2026** | ≈10,332 (est.; women's part ≈4,430) | 1. **TennisLive** | 8 of 8 sampled men's events and 3 of 3 women's: every main-draw match with a result, qualifying too | Result + stats (+ partial point) | Tournament-results listing found |
| | | 2. **WTA website records** (women) | 3,946 main-draw matches with scores, weeks 27-37 | Result | Downloaded |
| | | 3. Polymarket settled markets (on disk) | 9,149 main-draw winners (≈91% men, 95% women) | Winner only | On disk |
| | | then: ITF live-data API | The last 14 days only, complete with qualifying, statistics and points | Result + stats + point | Forward capture |
| **ATP tour-level points, 2025-Jun 2026** | 3,778 | 1. **SofaScore** | Complete points 34 of 36, box 34 of 36. About 3,570 | Point + stats | Adapter exists |
| | | 2. SirGenkii fork (width) | Point outcomes for 715 gap matches of Jan-Apr 2025 | Point with outcome | Downloaded |
| | | then: ATP Stats Centre files | They exist for 2025-26 (16 of 20 sampled), encrypted | Point with outcome, tracking | Needs the owner's decision on decryption |
| **WTA points in 2018** | 3,491 | 1. **SofaScore** (main draws) | Complete points 19 of 22 main-draw matches, 0 of 10 qualifying. About 1,900 | Point + stats | Adapter exists |
| | | 2. **TennisLive** (qualifying too) | Points 32 of 32 (qualifying included), none complete | Partial point + stats | Adapter exists; one page per match |
| **AO and RG points, 2022-2026** | 1,636 | 1. **SofaScore** | Listed 1,529 of 1,530; complete points 36 of 37, box 37 of 37. All years | Point + stats | Adapter exists |
| | | 2. **Hawk-Eye copies** (`hawkilol`) | Complete points for 745 gap matches (AO 2022-24, RG 2022-24), 552 with ball tracking; none for 2025-26 | Shot (tracking) + point | Downloaded |

**Held already, or downloaded by this check, and not needed as a first choice:** the Kaggle SofaScore scrape `marcosjn2`, to 28 June 2025, with point winners only. It holds a subset of what SofaScore serves: 1,377 WTA 2018, 1,335 ATP 2025 and 1,242 AO/RG 2022-25 gap matches.

## What the checks changed

**Held up, now measured on the gaps themselves rather than on ten Challenger careers:**
* SofaScore for ITF 2018-24, both tours.
* SofaScore and TennisLive for Challengers, 2025-26.
* SofaScore for ATP tour level.
* The Hawk-Eye GitHub copies for AO/RG 2022-24.
* The Tennis Abstract website-only charts and their Hugging Face copy.
* Polymarket's settled ITF markets.
* SirGenkii for January-April 2025, which turns out to add width, not matches (below).

**Did not hold:**
* **"WTA point by point in 2018: No public source found."**
  * SofaScore has complete point records for most 2018 main draws.
  * TennisLive has partial records, qualifying included.
  * The WTA API's emptiness is confirmed: 18 of 18 event logs across nine 2018 editions are empty.
* **"A newer Sackmann snapshot":** none exists. The repositories still answer 404, and no mirror or fork has anything after 2 June 2026. tennisabstract.com is still updated, but only player by player.
* **The Flashscore files already on disk** do not help either ITF gap: box scores for 175 of 201,946 ITF matches, and 8 of 16,277 women's qualifying matches of 2024.
* **TennisLive's point records** are rarely complete (set-closing games missing), so it is a second choice for points.
* **The Live Tennis API** does not reach ITF before 2023. Its paid archive remains an unmeasured vendor claim.

**New, not on the cards:**
* **The WTA website's match records** hold women's ITF qualifying and post-June results with scores, for every year.
* **The ITF's own live-data API** holds complete draws with statistics and points, but only for the last 14 days.
* **TennisLive lists men's ITF results after June 2026**, and one request lists a whole event.
* **The women's post-June estimate is too high** by about 690 matches (143 events in those weeks of 2026, against 167 in 2025).
* **The Live Tennis API sample's "UTC" times are Israel local time** (vendor's correction of 28 Sep 2026).

## Gap by gap

### ITF matches of 2018-2024 with only a result (201,946)

*The card suggested:* SofaScore (box scores and points for most ITF matches 2013-2024), and TennisLive (points from 2019). The claim came from ten men's Challenger careers.

*Checked:* 28 editions, two per tour and year (seeded, probability proportional to size); 855 gap matches listed; 84 read on both sites.

| Source | Listed | Box score | Point record, complete | Point record, any | Evidence |
|---|---|---|---|---|---|
| **SofaScore** | 843 of 855 (98.6%) | 82 of 84 (97.6%; 95% CI 92-99) | 78 of 84 (92.9%; 85-97) | 81 of 84 | observed |
| SofaScore, men / women | 404/414 · 439/441 | 40/42 · 42/42 | 39/42 · 39/42 | | observed |
| **TennisLive** | 81 of 84 pages | 81 of 84 (8 match totals, counts) | 3 of 84 | 80 of 84 (median 93% of games) | observed |
| Flashscore files on disk | 98,239 of the gap's matches | 175 | – | – | observed |

* **SofaScore:** weighted by tour and year, about 196,600 box scores and 186,600 complete point records.
  * *Its weakest year is 2018.* Hungary F1's season holds only 23 of its 31 singles matches, and the men's complete-point share is 4 of 6.
  * *Contents:* the full 18-field serve and return box score. Points come as the score after each point, the server, and ace/double-fault codes.
* **TennisLive:**
  * *Coverage:* women's ITF is covered like men's from 2019. In 2018, one of the two women's editions (Hammamet $15K) has results but no match pages.
  * *Record quality:* records usually lack the game that closes each set, the pattern already known from the ten careers.
* **Not a route:**
  * The Live Tennis API index lists only 2023-24 (10.8% of the gap), and the vendor dates its ITF points from 2025.
  * The ITF live-data API serves statistics by match id, but 2018-24 ids cannot be listed.

### Women's ITF qualifying, 2025-2026 (≈28,555, estimated)

*The card suggested:* SofaScore or TennisLive listings.

*Found instead, and verified:* the WTA website's own match records. Kaggle `bwandowando/womens-tennis-association-matches-1975-present` (version 29, 24 Sep 2026, "Apache 2.0") is built from wtatennis.com player by player. The same records are served by `api.wtatennis.com/tennis/players/<id>/matches/?year=<y>` (checked with one request).

| Year | Sackmann's women's ITF qualifying | In the WTA-site file | Sackmann's matches found in it |
|---|---:|---:|---:|
| 2018 | 354 | 13,146 | 94% |
| 2019 | 10,144 | 9,904 | 92% |
| 2020 | 3,806 | 3,650 | 93% |
| 2021 | 10,710 | 10,178 | 92% |
| 2022 | 13,789 | 12,680 | 88% |
| 2023 | 13,850 | 14,623 | 91% |
| 2024 | 16,277 | 15,339 | 90% |
| **2025** | – | **15,196** | – |
| **2026** (to about 9 Sep) | – | **9,818** | – |

* **Calibration.** In 2019-24, where both exist, the file's qualifying volume is 92-106% of Sackmann's, and 88-93% of Sackmann's matches are found by name and week (the rest is mostly name formats).
* **The gap.** For the gap years it holds 25,014 matches, all but a handful with scores, against the map's 28,555. The estimate runs to 20 September, the file to early September.
* **Use with care: duplicates.** 12% of the file's ITF rows are duplicates: the same match under two pseudo ids. They were removed on tournament, draw, round and player pair.
* **A bonus.** It also holds 2018's women's ITF qualifying (13,146), which Sackmann barely lists.

*The suggested sources:*
* **TennisLive:** lists qualifying for every 2026 event sampled (88 qualifying matches in 3 women's events). 2025 was not sampled.
* **SofaScore:** lists 2025 ITF qualifying inside the event (W100 Biarritz 2025: 18 qualifying matches; a spot check, not saved). The planned count was stopped by the block.
* **The ITF live-data API:** complete qualifying, but only for the last 14 days (283 women's qualifying matches in week 39).
* **Tennis Explorer:** lists women's qualifying (2 events; counts equal the ITF's).
* **Not a route:** Flashscore on disk (8 of 16,277 in 2024), and the Live Tennis API index (none in 2025; 554 from 21 Jul 2026, no winners).

*Men's ITF qualifying*, which the map says no source lists:
* TennisLive lists it: 318 matches in 8 events of July-September 2026, all with results.
* The ITF live-data API: forward only.
* Polymarket: qualifying winners from 27 July 2026.

### Shot-by-shot data for women's matches (17,854)

*The card suggested:* 3,890 women's charts that exist only on tennisabstract.com, 3,053 of all website-only charts being in the Hugging Face copy `ramizheman/TennisNLData`.

* **The charts** [observed; lane A]:
  * *In scope:* 2,282 women's website-only charts are dated 2018-2026, and 2,061 of them link to gap matches at the gap's levels.
  * *In the Hugging Face copy:* 1,467 of the 2,061 (commit `9a1fc64`, 9,256 files); 594 are on the website only.
  * *By year:* 2018 298, 2019 377, 2020 137, 2021 219, 2022 216, 2023 307, 2024 193, 2025 183, 2026 131.
  * *Both forms carry every shot:* three website-only pages (Auckland 2019 final, Hobart 2023 and Brisbane 2026 semi-finals) hold 142-170 point rows each, every shot spelled out, and a sampled Hugging Face file holds the same log as text with the page's stat tables [observed].
  * *The charting continues:* the index lists 18,284 charts, 22 more than on 23 September, 5 of them women's of 2018-26.
* **Hawk-Eye tracking for women** [observed]: the `hawkilol` Court Vision copy holds 621 women's AO and RG gap matches with ball tracking. By year: 2019 18, 2020 122, 2021 154, 2022 146, 2023 84, 2024 97. It holds nothing after 2024.
* **Together:** about 2,600 of 17,854 (15%).
* **The rest has no public shot-level source:** about 15,000 women's matches, mostly WTA 250-1000 and the 2025-26 Slams. The WTA API's advanced statistics are match totals. The Wimbledon and US Open feeds (held) add per-point serve placement and speed for women's Slam main draws, which is point grain, not shots.

### Challenger point by point, 2025 to June 2026 (14,438)

*The card suggested:* SofaScore and TennisLive for all players, or the Live Tennis API's paid archive.

| Source | Listed | Point record, complete | Box score | Evidence |
|---|---|---|---|---|
| **SofaScore** | 202 of 207 (97.6%) | 31 of 32 (96.9%) | 32 of 32 | observed; 8 editions |
| **TennisLive** | 32 of 32 | 1 of 32 (points on 32) | 32 of 32, identical to the official box score in 31 of 31 | observed |
| Live Tennis API, paid | Index lists 12,059 (83.5%) | Vendor claims a point sequence for 99.6% of indexed Challenger singles | – | index observed; points claimed |

* **SofaScore:** about 14,000 matches.
* **TDI:** covers only its window from 23 June 2026 (held) and 634 older ids.

### ITF results after early June 2026 (≈10,332, estimated)

*The card suggested:* a newer Sackmann snapshot, SofaScore, or Polymarket's settled ITF markets (winners only).

* **No newer Sackmann snapshot exists** [observed; lane B]. `tennis_atp` and `tennis_wta` still answer 404. The mirror the project used (`Aneeshers/tennis-sackmann-archive` @ `8373358`), its 10 forks and its Hugging Face twin have nothing newer. tennisabstract.com is still updated with ITF results, but player by player.
* **TennisLive lists both tours in full** [observed; lane D follow-up].
  * *Men's events:* all 8 sampled (weeks 27-36), 248 of 248 main-draw matches with results and pages, plus 318 qualifying matches.
  * *Women's events:* all 3 sampled, 93 of 93 main-draw and 88 qualifying.
  * *Match detail:* statistics on every match read; points on 18 of 24 men's (partial).
  * *Listing:* one call to the tournament page's results section lists a whole event.
* **The WTA website's records** hold 3,946 women's main-draw matches with scores in weeks 27-37, plus 2,938 qualifying. Week 37 is partial and week 38 absent in version 29; the WTA API itself would give them.
* **Polymarket's settled markets** (on disk) [observed; lane C]:
  * *Main draw:* 9,149 winners in weeks 27-38 (men 4,925, women 4,224), about 91% of the men's and 95% of the women's matches implied by Wikipedia's event lists.
  * *Qualifying:* winners from 27 July (2,914).
  * *Limit:* winners only, with walkovers voided.
* **The ITF live-data API** (`api.itf-production.sports-data.stadion.io`, behind the ITF's World Tennis Tour Live pages; no credentials, no challenge in 138 requests) [observed; lane C].
  * *What it holds:* every event, draw and result, qualifying included, for the last 14 days. Older dates answer HTTP 422.
  * *Match detail:* per-match statistics and points by match id, for 2025 matches too.
  * *Use:* forward capture only. itftennis.com itself blocked the first draw request (Imperva, HTTP 403).
* **SofaScore** was not measured (the block). Its tournament list for 2 Aug 2026 named 28 men's and 24 women's ITF singles events on its first page (a spot check, not saved).
* **The estimate:** 2026 had 143 women's events in those weeks against 167 in 2025, so about 4,430 women's matches are missing, not 5,123 [inference; lane C].

### ATP tour-level point by point, 2025 to June 2026 (3,778)

*The card suggested:* the SirGenkii/infotennis fork (January-April 2025), the ATP's encrypted Stats Centre files, SofaScore, or paid feeds.

| Source | What it fills | Evidence |
|---|---|---|
| **SofaScore** | Listed 450 of 452; complete points 34 of 36 (94.4%), box 34 of 36. About 3,570 | observed; 9 editions |
| **TennisLive** | Points 36 of 36 (2 complete); statistics identical to the official box score in 34 of 36 (2 have the players swapped) | observed |
| SirGenkii fork | 715 gap matches of Dec 2024-Apr 2025, every one with point outcomes (winner, forced or unforced error), serve number, some serve speeds. Only 25 not also in marcosjn2 | observed; lane B |
| marcosjn2 (Kaggle) | 1,335 matches of Jan-Jun 2025, point winners only | observed; lane B |
| ATP Stats Centre files | Exist for 2025 and 2026 tour-level matches to at least 29 Aug 2026, and Challengers: 16 of 20 sampled. Still ciphertext (`{lastModified, response, data: null}`), rewritten weeks after each match | observed; not decrypted |
| Paid feeds (Sportradar, Live Tennis API) | Not rechecked; the Live Tennis API index lists 3,570 (94.5%) | index observed |

* **Nothing public is newer:** no copy of decrypted ATP data later than April 2025 was found on GitHub, Hugging Face or Kaggle. The Hugging Face dump is unchanged since 19 June 2026.
* **The only route to point outcomes after April 2025** (winner, forced or unforced error, rally length) outside TDI's window is the encrypted files. Decrypting them is outside the 24 September limits and is the owner's call.

### WTA point by point in 2018 (3,491: 2,200 main draw, 1,291 qualifying)

*The card said:* no public source found.

| Source | Main draw | Qualifying | Evidence |
|---|---|---|---|
| WTA API | Event log empty in 18 of 18 matches (nine editions, January to November, every tier); point-by-point 404 | – | observed |
| **SofaScore** | Complete points 19 of 22 (86%); the 3 misses are one small event ('s-Hertogenbosch) | 0 of 10 | observed; 8 editions, 428 of 428 listed |
| **TennisLive** | Points on 22 of 22 | Points on 10 of 10 | observed; none complete (the set-closing game is missing; 89% of games have points) |
| marcosjn2 (Kaggle) | 1,303 | 55 of 1,162 tour qualifying | observed; lane B; point winners only |

* **Main draws:** SofaScore would fill about 1,900.
* **Qualifying:** only TennisLive's partial records reach it.
* **WTA 125** (433 gap matches) was not in the sample. marcosjn2 has 19 of them.

### Roland Garros and Australian Open point by point, 2022-2026 (1,636)

*The card suggested:* the GitHub copies of Hawk-Eye Court Vision (AO 2020-24, RG 2019-24), and the 47 Wayback captures already held.

| Source | What it fills | Evidence |
|---|---|---|
| **SofaScore** | Listed 1,529 of 1,530 in the 20 editions reached; complete points 36 of 37, box 37 of 37. Every year, 2025-26 included | observed |
| **`hawkilol/tennisSlamBallTracking`** (`f97a9b3`) | Complete point records for 745 gap matches, 552 of them with ball tracking. Separate code replays 40 of 40 sampled ones to the official score | observed; lane A and the lead |
| marcosjn2 (Kaggle) | 1,242 of the 1,409 AO/RG gap matches of 2022-25, point winners only | observed; lane B |
| TennisLive | Points 42 of 42 (2 complete); statistics 42 of 42 | observed |
| `ryurko/hawkeye` | Nothing: RG 2019-21 and AO 2020-21 only | observed (README and tree) |

**The Hawk-Eye copy, by year** (complete point records, with tracking in brackets):

| Year | AO men | AO women | RG men | RG women |
|---|---|---|---|---|
| 2022 | 83 of 89 (81) | 106 of 108 (104) | 79 of 96 (29) | 75 of 104 (24) |
| 2023 | 58 of 60 (58) | 62 of 63 (62) | 30 of 90 (9) | 48 of 109 (20) |
| 2024 | 71 of 75 (71) | 94 of 94 (94) | 15 of 82 (0) | 24 of 93 (0) |

* **After 2024:** for AO and RG 2025, marcosjn2 has point winners (AO 2025: 70 of 76 men's and 82 of 89 women's gap matches; RG 2025: 63 of 74 and 97 of 107). RG 2026 has only SofaScore, apart from TennisLive's partial records.

## What collecting would take

| Source | Requests | Observed pace and blocks | Notes |
|---|---|---|---|
| SofaScore | About 2 per match (points and statistics) plus 1-10 listing pages per tournament. ITF 2018-24 alone is about 420,000; the other gaps about 50,000 | The plain client was blocked after about 830 requests on 29 Sep (about 3,800 on 24 Sep). The adapter's Chrome-tab mode ran about 3,000 an hour | ITF 2018-24 would take about six days in the browser mode |
| TennisLive | 1 per match page (points and statistics) plus 1 per event listing | No block in about 4,900 requests over two days | ITF 2018-24 about 210,000 |
| WTA website records | Already downloaded (Kaggle v29). Directly: one request per player and year | – | Refresh from the WTA API under the 24 Sep decision |
| Hawk-Eye copies, SirGenkii, marcosjn2, Polymarket | Downloaded or on disk | – | – |
| Tennis Abstract charts | 594 website pages to fetch and parse, plus the Hugging Face files | robots.txt allows `/charting/` | – |
| ITF live-data API | One day list a day, plus statistics and points per match | No challenge in 138 requests | Forward only |

## Side findings

* **The Live Tennis API sample's times are Israel local time.** Version 1.0.2 on Zenodo (28 Sep 2026) says the "UTC" times of v1.0.0 and v1.0.1 were Israel local time. The project stages v1.0.0, so every join on its times is 2-3 hours off until it is re-staged. This also applies to the June 2026 point sample.
* **The women's post-June estimate** on the map is about 690 matches too high (above).
* **The WTA-site Kaggle file repeats 12% of its ITF rows** under a second pseudo id, and needs de-duplicating before use.
* **marcosjn2 appends one extra point to 99.5% of tie-breaks**, credited to the tie-break winner. Drop it.
* **TennisLive's statistics block swaps the two players** in 2 of 36 sampled ATP matches.
* **The ATP Stats Centre envelopes gained a `data` key** (null). The files are rewritten weeks after the match.

## Method

* **The sample** (`src/eda/gap_sources/sample.py`, seed 20260929).
  * *Design:* each gap's editions were drawn with probability proportional to their gap matches, then a fixed number of matches in each: 3 for ITF, 4 for Challenger, ATP and WTA 2018, 2 for Slams. Every Slam edition was taken.
  * *Reading the result:* the design makes every match of a stratum about equally likely, so a stratum's checked share estimates the gap's share. Matches within an edition share outcomes, so the real sample is nearer the number of editions (28 ITF, 8 Challenger, 9 ATP, 8 WTA 2018, 22 Slam), and the Wilson intervals quoted are too narrow.
* **SofaScore** (`sofascore_probe.py`):
  * *Locating an edition:* its category's day listing (`/category/<id>/scheduled-events/<date>`) on a few days of its week; the tournament season naming the most of its known matches is taken.
  * *Listing it:* the season's events (`/unique-tournament/<id>/season/<id>/events/last/<n>`).
  * *Linking:* both players share a name word; the event starts 10 days before to 21 after the tournament start.
  * *Checking:* `/point-by-point` and `/statistics` for the sampled matches.
  * *Complete* means every set has as many games as the score; a retirement's game in progress counts. A full box score has aces, double faults, first-serve in and won, second-serve won and break points saved.
* **TennisLive** (lane D, `tennislive_probe.py`): each sampled match was found through a player's season listing, and its set scores equal the reference in all 226. Completeness follows the ten-career study's rules.
* **The WTA-site file** (`wta_site_kaggle.py`): women's ITF rows, byes and walkovers left out, duplicates removed. Sackmann's matches were found on both surnames with a tournament start within 7 days.
* **The lanes** (A: Slam Hawk-Eye copies and women's charts; B: tour-level point datasets, the ATP files, Sackmann; C: ITF listings and Polymarket; D: TennisLive) each kept a notes file with URLs, versions and evidence labels. Lane A stalled after writing its tables and was stopped; the lead compiled its notes from those tables and added its own checks: an independent replay of 40 Hawk-Eye matches, three Tennis Abstract pages and the chart index.

## Limits

* **Samples, not censuses.** The gap-level fills are expected counts. The ITF strata have six matches from two editions each; the Slam editions one or two.
* **SofaScore's last checks are missing.** Two women's Slam editions (RG 2026, one US Open 2024 match) and the 2025-26 ITF listing count were not read because of the block. `sofascore_itf_listings.py` is ready to run, with `--browser` if the block persists.
* **Linking by names.** Name forms differ between sources, so a few percent of matches can be missed or, rarely, paired wrongly. Listing shares are therefore conservative.
* **Vendor claims stay claims:** the Live Tennis API's archive and paid feeds were not bought.
* **Rights are unchanged by this check.** SofaScore, TennisLive, the WTA site, TDI and the Slam sites restrict automated collection. The owner's decisions of 23-25 September cover collecting SofaScore, TennisLive, the WTA API and TDI for non-commercial research. The ITF live-data API, Tennis Explorer and Tennis Abstract's pages are not named in them. Decrypting the ATP files is outside the 24 September limits.

## Evidence and reruns

Everything is in [data/studies/gap_sources/](../../../data/studies/gap_sources/README.md), with the scripts in `src/eda/gap_sources/` and raw answers under `data/raw/gap_sources/` (gitignored). The lane reports:
* [A: Slam tracking and women's charts](../../../data/studies/gap_sources/research_notes/A_slam_tracking_and_women_charts.md)
* [B: tour point datasets, ATP files, Sackmann](../../../data/studies/gap_sources/research_notes/B_tour_pbp_datasets_and_sackmann.md)
* [C: ITF listings](../../../data/studies/gap_sources/research_notes/C_itf_listings.md)
* [D: TennisLive](../../../data/studies/gap_sources/research_notes/D_tennislive.md)
