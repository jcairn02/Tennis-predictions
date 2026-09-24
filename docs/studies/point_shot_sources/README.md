# Point- and shot-level sources for the ten Challenger careers

**The ten Challenger careers have point or shot data for 85 of their 4,055 official matches (2%).**

**SofaScore**, a free score site, holds complete point-by-point records for an estimated 2,930 of the other 3,959 (74%):

* 1,746 matched and checked match by match, and the rest estimated for stretches the reading tool could not see;
* nearly every ITF match from 2013 to 2024, and nearly every Challenger and tour-level match from 2024;
* the full serve and return box score alongside.

**Its gaps are Challenger matches of 2022–23 and ITF matches of 2025.**

* TennisLive.net showed point-by-point on all 15 of the pages sampled in those gaps, which would lift the total to about nine in ten.
* The Live Tennis API's paid archive lists most of the same matches from 2023.

**Neither free site licenses bulk use.** The official owners of the umpire data (Sportradar, Infront, TDI) sell it only live or for the last two or three seasons, and bar betting use without consent.

**Shot-level data barely reaches these players:**

* 18 volunteer charts;
* per-point serve speed, placement and distance run for about 34 Grand Slam matches, from the Slams' public feeds;
* ATP tracking, which exists from 2025 but only under licence.

**Status: study, not a decision.** It audits sources the project does not use yet, measures the free ones match by match against the ten careers of the [career-coverage study](../career_coverage/README.md), and maps the paid and private ones onto the same matches from what their providers claim. Nothing was bought, no account was opened and no provider was contacted.

| Item | Where |
|---|---|
| SofaScore match lists, one file per player (read through WebFetch, 23 Sep 2026) | [sofascore_raw/](../../../data/studies/point_shot_sources/sofascore_raw/) |
| SofaScore linked to the official record | `src/eda/point_shot_sources/link_sofascore.py` → [sofascore_links.csv](../../../data/studies/point_shot_sources/sofascore_links.csv), [sofascore_events.csv](../../../data/studies/point_shot_sources/sofascore_events.csv), [sofascore_summary.json](../../../data/studies/point_shot_sources/sofascore_summary.json) |
| Direct reads of point-by-point records: SofaScore's marker checked (59), ITF 2025–26 (20), TennisLive in SofaScore's gaps (20) | `pbp_checks.py` → [pbp_checks.csv](../../../data/studies/point_shot_sources/pbp_checks.csv), [pbp_checks_itf_recent.csv](../../../data/studies/point_shot_sources/pbp_checks_itf_recent.csv), [tennislive_checks.csv](../../../data/studies/point_shot_sources/tennislive_checks.csv) (samples in the matching `*_sample.csv`), [pbp_check_summary.json](../../../data/studies/point_shot_sources/pbp_check_summary.json) |
| Sackmann's old point strings (two surviving copies) and the Tennis Abstract chart index | `link_public_sources.py` → [public_source_rows.csv](../../../data/studies/point_shot_sources/public_source_rows.csv), [public_source_receipts.json](../../../data/studies/point_shot_sources/public_source_receipts.json) |
| Provider claims, one row per source and level | [source_claims.csv](../../../data/studies/point_shot_sources/source_claims.csv) |
| The four research passes (23 Sep 2026): each source's URLs, quotations, evidence labels and blocked pages | [research_notes/](../../../data/studies/point_shot_sources/research_notes/): [self-serve APIs](../../../data/studies/point_shot_sources/research_notes/1_self_serve_apis.md), [official feeds](../../../data/studies/point_shot_sources/research_notes/2_official_feeds.md), [tracking and Grand Slam feeds](../../../data/studies/point_shot_sources/research_notes/3_tracking_and_grand_slam_feeds.md), [public websites and datasets](../../../data/studies/point_shot_sources/research_notes/4_public_websites_and_datasets.md) |
| What each source adds, match by match | `fill_matrix.py` → [fill_matrix.csv](../../../data/studies/point_shot_sources/fill_matrix.csv), [fill_summary.json](../../../data/studies/point_shot_sources/fill_summary.json) |
| Tests | `test/point_shot_sources/` (offline) |

## Question

Which sources the project does not use yet hold **point-by-point** records (every point in order, with server and score) or **shot-by-shot** records (strokes, or ball and player tracking) of matches already played? How recent and complete are they? For the ten Challenger players whose 4,055 official matches were checked in the career-coverage study, which of their matches would each source fill?

## Where the dump stands

85 of the 4,055 official matches (2%) have point or shot data in the staged dump:

* 76 have a point sequence as their richest layer: 7 from the Grand Slam point files (2011–2024 main draws) and 69 from the Live Tennis API's June 2026 sample;
* 9 have a Match Charting Project chart (two of them are also in the Grand Slam point files).

3,959 played matches have neither (11 of the 4,055 are walkovers).

## Method

1. **Candidates.** Every [source register](../../research/tennis-data-audit/source-register.md) entry whose records reach point or shot level, plus four web research passes on 23 September 2026 that looked for more:
   * self-serve APIs;
   * official and enterprise feeds;
   * tracking and shot-level sources;
   * public websites and datasets.

   Provider statements are recorded with their URL and a quotation. Nothing was bought, no account or trial was opened and no provider was contacted.
2. **SofaScore, match by match.**
   * *Reading the lists.* Each player's match list (`https://api.sofascore.com/api/v1/team/<id>/events/last/<page>`) was read page by page through the WebFetch tool and transcribed one line per match. Plain HTTP clients get HTTP 403, and that block was not worked around.
   * *Unread stretches.* The reading tool cuts each 30-match page after 15–25 matches. Pages run oldest to newest, so the unread part of every page is a known stretch of dates. A match whose playing days touch such a stretch counts as *unread*, not as absent.
   * *Linking.* Each listed singles match was linked to the official record by opponent name, tournament dates, round and place name.
   * *Point marker.* A match counts as having a SofaScore point record when its listing carries SofaScore's `firstToServe` field. That marker was checked against the point-by-point endpoint for a stratified sample (see Results).
3. **Live Tennis API.** Two parts of the dump measure it:
   * the vendor's public match index shows which matches its paid archive lists;
   * its June 2026 observed sample shows how many of the listed matches carry points.
4. **Sackmann's old point strings and the Tennis Abstract chart index.** Both were downloaded byte-exact with receipts, and the ten players' rows were linked by the same rule.
5. **TennisLive.net and the Grand Slam feeds.**
   * *TennisLive:* 20 of the players' matches in SofaScore's gaps were opened one page at a time.
   * *Grand Slam feeds:* coverage is taken from the feeds' own draw files (the share of matches at the full data level) and from sampled matches, read by the shot-level research.
6. **Paid and private sources.** Their claims were mapped onto the ten careers by level and year ([source_claims.csv](../../../data/studies/point_shot_sources/source_claims.csv)). "Claimed" means a provider's statement applied to the calendar, never a checked record.
7. **Counting.** A point-level source counts the matches it would lift from no point record to one. A shot-level source counts the matches it would lift to a shot record, including matches that already have a point sequence.

## Results: the sources measured match by match

### SofaScore

**Reading.** The ten players' SofaScore lists came to 211 pages. They held 3,650 matches (2,876 singles, 774 doubles) from October 2013 to August 2026, and each list was read back to its end. About 340 SofaScore pages were read in all, counting searches and checks.

**Linking.** Of the 4,055 official matches:

* 2,491 link to a listed match;
* 1,552 fall in stretches the reading tool cut off;
* 12 are genuinely absent (eight of Choinski's 2012–13 ITF matches, where his SofaScore history has barely begun; his two Furth 2015 qualifying matches; a 2019 ITF semi-final; one Davis Cup rubber).

Within the stretches that were read, SofaScore lists essentially the whole official record.

**The point marker.** 1,870 of the linked matches carry SofaScore's point marker. By level and period, the share of read matches with a point record is:

| Level | 2012–18 | 2019–21 | 2022–23 | 2024 | 2025–26 |
|---|---|---|---|---|---|
| ITF main draw | 91% of 238 | 96% of 297 | 98% of 310 | 97% of 145 | **2025: 0 of 15; 2026: 7 of 8** (read directly) |
| Challenger main draw | 35% of 26 | 79% of 70 | **1% of 213** | 99% of 168 | 98% of 295 |
| Challenger qualifying | 4% of 27 | 29% of 17 | **0% of 88** | 100% of 33 | 100% of 57 |
| Tour-level qualifying | 1 of 9 | 1 of 2 | 37% of 35 | 100% of 30 | 98% of 59 |
| Tour-level main draw | – | – | 4 of 5 | 100% of 11 | 100% of 43 |

ITF qualifying, 2023: 9 of 17. SofaScore also lists 222 ITF qualifying matches of these players that the official ATP record leaves out; 54 of them carry the marker.

**Checking the marker.** A stratified sample of 59 point-by-point records was read directly: by level, era and marker, two marked and one unmarked match per cell.

* One listed event id did not exist, a copying slip, so 58 checks count.
* 40 of the 58 had a point record, and **all 40 were complete**: every set has as many games as the official score, two retirements included.
* **Outside ITF draws of 2025–26, every disagreement between the listed marker and the record was a copying slip.** The transcribed lists had copied the marker wrongly 9 times (5 marks missed, 4 invented). Read from each disputed event itself, the marker agreed with the record, so it matched in all 55 cases. Match-level flags carry this copying noise, but it nearly cancels in the totals.
* **In ITF draws of 2025–26 the marker fails.** A separate random sample of 20 matches, marker ignored, found no record for any of the 13 from 2025 and records for 6 of the 7 from 2026. With the stratified sample's three matches, that is 0 of 15 for 2025 and 7 of 8 for 2026, all from April 2026 on.

**What a record holds:**

* the score after every point and the server of every game;
* per-point codes that SofaScore does not document (`pointDescription` takes 0, 1 or 2; a scraper's documentation reads them as ace, double fault and the like);
* no clock time per point;
* the same matches' 18-field serve and return box score, checked on ITF matches of 2017, 2019, 2022 and 2024. A 2025 ITF match without a record had only aces and double faults. The dump has statistics for 0.1% of these players' pre-2025 ITF matches.

**Rights.** SofaScore sells no data. Its FAQ says that "due to agreements with our data providers, we are unable to share the data sources in the form of API endpoints". Its terms page does not render outside a browser; the excerpt a search engine shows forbids "any automated means ... scraping, crawling" and "data mining". Three RapidAPI listings resell its data; one says so outright ("Data sourced from sofascore public endpoints"), for $0–99 a month. None states a licence from SofaScore. The reads for this study were a bounded measurement, not an acquisition. Bulk use of SofaScore data has no lawful route today other than asking SofaScore.

### TennisLive.net

The public-web research found one more site with historical point sequences for lower tiers: [TennisLive.net](https://www.tennislive.net/), run by eHM, s.r.o. (Slovakia). Its match pages are plain HTML. Each game shows the server, the score after every point and break-point markers, and the match statistics sit alongside. That research's spot checks found point-by-point for:

* ITF main draws from 2018, but none on the January 2025 pages it opened;
* Challenger main draws from 2016;
* Challenger qualifying in 2022;
* ATP qualifying in 2023.

It found none on ITF qualifying pages (December 2025).

**Sample of SofaScore's holes.** TennisLive was checked on 20 of the ten players' matches: Challenger main draws and qualifying of 2022–23, and ITF main draws of 2025. The sample was drawn from tournaments held once per city and year, so that each page's address could be built from the names ([tennislive_checks.csv](../../../data/studies/point_shot_sources/tennislive_checks.csv)).

* 15 addresses resolved. **All 15 pages have point-by-point.** That breaks down as 6 of 6 Challenger main draws, 4 of 4 Challenger qualifying and 5 of 5 ITF matches from March to August 2025.
* The other five addresses did not resolve because of name spellings (for example "J.J. Wolf").

Across SofaScore's three holes, that suggests about 700 of the players' matches (at least 557 at the lower end of the sample's 95% interval). The ITF part counts only matches from March 2025. Completeness of each record was not checked, and the research noticed opening games that look short on a few pages.

**Terms.** Updated 13 September 2026: "Systematic scraping, bulk extraction, automated redistribution and commercial reuse require permission or another valid legal basis." The upstream source is not stated. No clock time is shown per point.

### Live Tennis API's paid archive

The vendor's public index is already in the dump. It lists **1,897 of the players' 2,420 official matches of 2023–2026 (78%)**:

| Level | Share of 2023–26 official matches listed |
|---|---|
| Challenger main draw | 94% |
| Challenger qualifying | 96% |
| Tour-level qualifying | 96% |
| Tour-level main draw | 92% |
| ITF main draw | 53% |
| ITF qualifying | none of 30 |

**What the vendor claims** ([historical product](https://livetennisapi.com/historical-tennis-data-api), [academic page](https://livetennisapi.com/data/academic), read 23 September 2026):

* 99.3% of indexed ITF men's singles and 99.6% of Challenger men's singles "carry a point sequence";
* but only 60.5% of all completed 2023+ matches are "measured point-complete";
* the 2023–2025 sequences were "expanded after the match from a third-party feed", which is not named;
* "ITF point depth" starts in 2025;
* real per-point timestamps exist only from its own live capture (October 2025 on, in the product from March 2026).

**Measured.** Its June 2026 live-captured sample has score states for 69 of these players' 80 indexed matches that month (86%):

* Challenger main draw: 35 of 38;
* ITF: 15 of 17;
* tour level: 19 of 21;
* Challenger qualifying: 0 of 4.

**It fills SofaScore's two holes.** It indexes 228 of the 356 Challenger main-draw matches of 2022–23 (the 2023 ones) and 236 of the 346 ITF matches of 2025–26.

**Its 2013–2022 archive**, rebuilt "from the public record", claims 55% of Challenger main draws and 34% of Challenger qualifying (pooled over those years). It does not cover ITF.

**Price and terms.** $49 buys a one-month access window with bulk downloads, including the 2013–2022 files; a year costs $399. The terms forbid storing data "beyond what is reasonably necessary to operate your application" (§3(c)), which needs written clarification before any bulk acquisition.

### Sackmann's old point strings

The original `tennis_pointbypoint` repository returns 404. Two third-party copies survive on GitHub: [ppaulojr/tennis_pointbypoint](https://github.com/ppaulojr/tennis_pointbypoint) (April 2015) and the `data/` folder of [sportsdatascience/setuppoints](https://github.com/sportsdatascience/setuppoints) (January 2018; matches of 2011–2015 and January 2017).

They hold **68 of these players' matches**, all 2013–2017:

* 62 are Choinski's, 51 of them ITF main draws;
* 4 are Hardt's and 2 are Holt's;
* one is a 2013 ITF qualifying match that is not on the ATP record;
* two are Choinski's Furth 2015 qualifying matches, which no source had in the career study.

Each string gives the server and the winner of every point, with aces and double faults where the original recorded them. The original parser left out retirements.

### Tennis Abstract's chart index

The [chart index](https://www.tennisabstract.com/charting/meta.html) lists 18 charts of these players; the dump's GitHub export of the Match Charting Project has 10. The other 8, from 2022 to 2026, would be new shot-by-shot records:

* Holt's 2022 US Open first round;
* Hardt's 2022 Alicante Challenger final;
* Onclin's and Choinski's 2023 Roland Garros qualifying;
* Walton's 2023 Cary Challenger quarter-final and his 2026 Australian Open and Roland Garros first rounds;
* Glinka's 2025 Drummondville Challenger final.

## Results: paid and private sources, from their claims

Nothing here was bought or requested. Each provider's statement is mapped onto the ten careers by level and year in [source_claims.csv](../../../data/studies/point_shot_sources/source_claims.csv). Where a provider gives no share, every match in the claimed range is counted, so the figure is an upper bound.

### Who held the umpire's point data

Chair umpires' scoring devices record every point at ATP, Challenger and ITF events. The research traced who distributes that data:

| Population | 2019–2024 | 2025–2026 |
|---|---|---|
| ITF main draws | ITF umpires on "Sportradar devices" | Infront (with LSports distributing), ITF devices |
| ITF qualifying | chair-umpire scoring only at M25 final qualifying round (ITF 2025 table, "no change") | same |
| Challenger and ATP, main and qualifying | ATP scoring managed by TDI (ATP's data venture) from 2020; Sportradar ran a secondary official feed from 2022 | Sportradar as "TDI's exclusive distribution partner" from 2024 |
| Grand Slams, including qualifying | IMG ARENA (Roland Garros, Wimbledon, US Open) | Sportradar after buying IMG ARENA (2025); Infront for the Australian Open |

SofaScore's point records follow these seams:

* ITF was present to 2024, absent in 2025 and back from April 2026.
* Challenger was nearly absent in 2022–23 and present from 2024.

The research found forum reports that live-score apps lost ITF point-by-point in early 2025.

### Official and enterprise feeds

* **Sportradar Tennis API** ([coverage tiers](https://developer.sportradar.com/tennis/docs/tennis-ig-data-coverage-tiers), [historical data](https://developer.sportradar.com/tennis/docs/tennis-ig-historical-data)).
  * **Data:** official Challenger and ATP "Point-by-point from round 1". Each point carries the server, the winner, a result (ace, double fault, server won, receiver won), a first-serve-fault flag and a UTC time.
  * **History:** only seasons inside a rolling window of "the current season and the two adjacent editions" (2024–2026 today). ITF was dropped in January 2025, and nothing says its 2017–2024 timelines can still be reached.
  * **Terms:** display-only; no prediction-market or betting use without written consent; all historical data and derivatives destroyed when the contract ends. The trial is for evaluation only.
  * **Ten careers:** up to 1,105 matches, all of them in years where SofaScore already has records.
* **TDI's "Tennis Results" site** (results.tennisdata.com).
  * **Claim:** free and official, with "detailed results on every point played" for all ATP and Challenger matches. A qualifying page appears in search results.
  * **Access:** it refuses automated reading, so depth and terms are unknown. Search summaries say it launched in 2025.
  * **Ten careers:** up to 687 matches of 2025–26.
  * **Next step:** it needs a look in an ordinary browser.
* **Infront / LSports (ITF from 2025).**
  * **Data:** umpire point data for M15 and M25 main draws, plus rally and tracking data at streamed M25 matches from 2025.
  * **Access:** sold live to licensed sportsbooks; no archive is stated.
  * **Ten careers:** up to 346 matches.
* **Enetpulse** (a Livesport company according to Wikipedia; Livesport runs Flashscore). It keeps "the pbp history since 2020" as an "exclusive product" (sales only), claimed for "most ATP and WTA tour-level matches". ITF and qualifying are not stated.
* **Stats Perform / Opta.** It has a point-level prediction feed and a tennis archive "from 2021", for tiers not stated. Its standard licence forbids machine-learning training and building archives.
* **Data Sports Group, Podium, Goalserve** claim live point-by-point but document no point history for these tiers. Goalserve ($150 a month) says "detailed point by point tennis match history" without depth.

### Self-serve APIs

* **api-tennis.com** (and allsportsapi.com, which shares its examples).
  * **Data:** every fixture carries a `pointbypoint` array: server per game, point scores, and break, set and match point flags.
  * **Evidence:** the documentation shows a finished 2022 ITF M25 match with points. Historical depth and per-tier coverage are not stated.
  * **Price:** $40–120 a month with a 14-day trial, which is the cheapest way to measure it.
* **Matchstat / Tennis-API.com** documents point-by-point only for its live feed.
* **BetsAPI** documents no point history for tennis.

### Other public websites and datasets

* **Flashscore, Tennis24 and Livesport** (one company).
  * They show a "Point by point" tab, claimed for "all ATP and WTA matches". Scraper notes say Challenger and ITF matches have it now.
  * Old pages cannot be checked without reading their data feeds, and their terms forbid any extraction.
* **OnCourt** (€48.95 a year) advertises a "point-by-point replay of most matches". It does not say which tiers or years, or whether the points sit in the database it licenses. Only a purchase would tell.
* **No point-by-point** is shown by Tennis Insight, TennisStats, Tennis Explorer, CoreTennis or LiveScore. 365Scores shows only a live tracker.
* **Public datasets** (Kaggle, Hugging Face, Zenodo, Dataverse, Mendeley, GitHub, papers) hold no 2019–2026 ITF or Challenger point data. The only exceptions are the Live Tennis API sample the dump already has and mirrors of it.
  * Grand Slam sets (such as the 2024 "momentum" Wimbledon 2023 file) derive from the same Slam feeds as Sackmann's archive.
  * Shot datasets from broadcasts (F3Set, OSL) are tour-level only.

### Grand Slam scoring feeds, and ball tracking

The shot-level research found **no public shot or tracking data for ITF or Challenger matches in 2019–2026**.

* **ATP Tour.**
  * *Tracking exists.* Live electronic line calling has been mandatory on all ATP Tour courts since 2025, qualifying included. The ATP says it gives "comprehensive player and ball tracking across the whole Tour" ([announcement](https://www.atptour.com/en/news/electronic-line-calling-release-april-2023)).
  * *Only under licence.* The tracking is sold only through TDI's licence. atptour.com's Challenger match data holds box scores only. Its tour-level "Court Vision" and "MatchBeats" views sit behind a blocked API, and a scraper reports them encrypted.
  * *Terms.* atptour.com prohibits "systematic retrieval of data" and "gambling or wagering" use.
  * *Ten careers:* 127 tour-level matches of 2025–26.
* **Challenger.** Electronic line calling is optional: the 2026 Rulebook requires line judges and allows review systems. Known cases are Heilbronn 2024 (Foxtenn) and six Challengers in 2026 (Bolt6). None offers its data.
* **ITF.** Line-calling systems arrive in 2026: PlayReplay at USTA hard-court ITF events, and pilots in Germany. The ITF's regulations give its licensing arm the data rights, keep player-analysis data for coaching, and bar betting use.
* **Grand Slams: the one public route.** The Slams' own scoring feeds are unauthenticated JSON.
  * *US Open (2022–2026) and Wimbledon (2025–2026):* every point, with serve speed, serve placement, return depth, distance run, winner or error and a clock time. Rally length is filled from 2025. US Open qualifying had full data for only 37–38% of matches before 2025, 60% in 2025 and 99% in 2026.
  * *Australian Open:* the match centre gives a timed line for every point and serve speeds, for the current edition only.
  * *Roland Garros:* point data sits behind a blocked API.
  * *Ten careers:* 43 Slam matches fall in covered editions, and about 34 are expected to carry the full data. Of the 43, 24 already have a SofaScore record and 6 are point-level in the dump, so the gain is the per-point measurements, not coverage.
  * *Terms:* none of the four Slams' website terms could be retrieved. The Australian Open's ticket conditions forbid taking match data out of the grounds for betting, but those are ticket terms, not website terms.

## Ranked: the sources not yet used

The ranking weighs four things, in this order:

* point- or shot-level matches added to the ten careers, weighted towards 2019–2026;
* depth of the data;
* whether it can be obtained lawfully;
* what it costs.

"Adds" counts matches that have no point record in the dump now (3,959 in all). Figures marked *claim* are provider statements mapped onto the calendar; the others were measured here.

| # | Source | Kind | Data | Adds to the ten careers | Years | Access, price | Main caveat |
|---|---|---|---|---|---|---|---|
| 1 | **SofaScore** | public site | every point's score, server per game, point codes; full serve/return box score | **1,746 measured; ≈2,930 with unread stretches (74%)** | ITF 2013–24 and from Apr 2026; Challenger main draws 2019–21 (most) and 2024–26; tour level 2024–26 | web only; no licence or API offered; resellers $0–99/month | terms forbid automated extraction; holes in Challenger 2022–23 and ITF 2025 |
| 2 | **TennisLive.net** | public site | point scores per game with server and break points; match stats | **≈700 (≥557) in SofaScore's holes**, from 15 of 15 sampled pages | ITF 2018–26 (not Jan 2025), Challenger 2016–26 | web only | bulk use needs the operator's permission; no clock times |
| 3 | **Live Tennis API archive** | paid API | point sequences; clock time per point from its own capture (late 2025 on) | index lists 1,814 (2023–26); vendor says 99% carry a sequence, 60.5% point-complete; **86% measured in June 2026**; ≈219 Challenger matches 2013–22 (*claim*) | 2013–2026 | $49 for a month's access, $399 a year | storage limited by its terms; 2023–25 rebuilt from an unnamed feed |
| 4 | **Grand Slam scoring feeds** | official public JSON | every point with serve speed, placement, return depth, distance run and clock time; rally length from 2025 | **≈34 of 43 Slam matches** in covered editions (deepens 24 that SofaScore already has) | US Open 2022–26 (qualifying partial before 2025), Wimbledon 2025–26, Australian Open current edition | free | website terms not retrieved; Australian Open keeps only the current edition |
| 5 | **TDI "Tennis Results"** | official free site | every point, "how they won it" (*claim*) | up to 687 of 2025–26 (*claim*) | 2025– | free web; refuses automated reading | unverified; terms unknown |
| 6 | **Sportradar Tennis API** | enterprise | per point: server, winner, ace/double fault, first-serve fault, UTC time | up to 1,105 of 2024–26 (*claim*) | rolling 2–3 seasons | quote; evaluation-only trial | no betting or prediction-market use without consent; delete at end of contract |
| 7 | **Tennis Abstract charts** (website) | public | shot by shot | **8 matches**, 2022–26 | 2022–26 | free | CC BY-NC-SA; volunteer selection |
| 8 | **Sackmann point strings** (two copies) | public | point winner and server, aces/double faults where noted | **67 matches** (+1 ITF qualifying) | 2013–17 | free | old; retirements excluded |
| 9 | **ATP Tour tracking** (Live ELC, via TDI) | licence | ball and player tracking | 127 tour-level matches of 2025–26 (*claim*, upper bound) | 2025– | TDI/Sportradar licence only | atptour.com views blocked and reportedly encrypted; no stated route for outsiders |
| 10 | **api-tennis.com** | self-serve API | point scores per game, break/set/match points | unknown (one 2022 ITF example) | ? | $40–120/month, 14-day trial | depth unstated |
| 11 | **Enetpulse** | B2B | point history | tour-level main draws from 2020 (*claim*, ≤97) | 2020– | sales only | Challenger/ITF not stated |
| 12 | **OnCourt** | desktop database | "point-by-point replay of most matches" | unknown | ? | €48.95/year | unknown whether the points are in the licensed database |
| 13 | **Infront / LSports** | sportsbook feed | umpire point data (ITF) | up to 346 ITF of 2025–26 (*claim*) | 2025– | licensed sportsbooks only | no archive offered |

**Checked and set aside:**

* **Stats Perform:** its standard licence bans machine-learning training and building archives.
* **Goalserve:** its point history claim gives no depth.
* **Flashscore:** its terms forbid extraction, and its depth can't be checked.
* **Matchstat:** point data is live-only.
* **Also set aside:** BetsAPI, Data Sports Group, Podium, STATSCORE, Genius Sports, Tennis Insight, TennisStats, Tennis Explorer, CoreTennis, LiveScore, 365Scores, and the public datasets.

## What the ten careers would look like

Matches with a point record, of the 3,959 that have none now. The figures are expected counts: measured, plus unread stretches at observed rates.

| Period | Needing | Free sources measured here (SofaScore, old point strings, charts) | + TennisLive in SofaScore's holes (needs permission) | + Live Tennis API index instead (paid, upper bound) |
|---|---:|---:|---:|---:|
| 2012–18 | 469 | 368 (78%) | 368 | 368 |
| 2019–21 | 650 | 573 (88%) | 573 | 573 |
| 2022–23 | 1,121 | 571 (51%) | ≈1,060 | 893 (80%) |
| 2024 | 638 | 628 (98%) | 628 | 632 |
| 2025–26 | 1,081 | 802 (74%) | ≈1,010 | 1,004 (93%) |
| **All** | **3,959** | **2,941 (74%)** | **≈3,640 (92%)** | **3,471 (88%)** |

**By player,** the free sources would lift point coverage from 1–4% of each career to 66–82%. The Live Tennis API index would take it to 77–97%. Counts below include the matches that have points now:

| Player | Matches | With points now | After free sources (expected) | + Live Tennis API index |
|---|---:|---:|---:|---:|
| Jan Choinski | 748 | 18 (2%) | 549 (73%) | 610 (82%) |
| Nikolas Sanchez Izquierdo | 588 | 9 (2%) | 425 (72%) | 496 (84%) |
| Gauthier Onclin | 457 | 6 (1%) | 376 (82%) | 439 (96%) |
| Nick Hardt | 450 | 16 (4%) | 312 (69%) | 387 (86%) |
| Daniil Glinka | 386 | 4 (1%) | 310 (80%) | 361 (94%) |
| Adam Walton | 372 | 15 (4%) | 303 (81%) | 359 (97%) |
| Brandon Holt | 352 | 2 (1%) | 269 (76%) | 308 (88%) |
| Gabriele Piraino | 295 | 8 (3%) | 212 (72%) | 272 (92%) |
| Samuele Pieri | 261 | 5 (2%) | 171 (66%) | 202 (77%) |
| Nicolas Villalon | 146 | 2 (1%) | 99 (68%) | 121 (83%) |

The by-player figures leave TennisLive out; its estimate is by level and period only.

**What is still missing afterwards:**

* ITF matches of January–February 2025;
* Challenger matches before 2019, and Challenger qualifying before 2022;
* ITF qualifying;
* Davis Cup ties;
* a handful of 2012–13 ITF matches.

**Shot-level data is the real gap.** Beyond the 18 volunteer charts (10 in the dump's export, 8 more on the website), little reaches these players' matches:

* **ATP Tour tracking:** exists for every tour-level match since 2025 (127 of theirs), but only under TDI's licence.
* **Challengers and ITF events:** almost no electronic line calling before 2026, and ITF rules keep such data for coaching.
* **Grand Slam feeds:** serve speed, placement and distance run per point for about 34 of their Slam matches. That is the closest thing to shot-level data that is publicly reachable.

## Findings for the next phase

These are options for the owner, not decisions.

1. **The coverage exists; the permission does not.**
   * Two public sites together show point-by-point for an estimated nine in ten of these careers' matches that lack it.
   * Neither licenses bulk use, and the official owners of the same umpire data (Sportradar, Infront, TDI) sell it live or within a rolling window, with no betting use without consent.
   * Asking SofaScore and TennisLive's operator for permission is the only route to most of this data. The official feeds are not a substitute for the history.
2. **Paid route with the fewest strings.** The Live Tennis API's one-month $49 window would let the project check its 2023–26 index against these players' matches directly (its `/history/coverage` roll-up and per-match tapes). Its storage clause (§3(c)) needs written clarification first.
3. **Free, lawful, small.** Sackmann's old point strings (68 matches, CC BY-NC-SA) and the 8 unexported Tennis Abstract charts can be added to the dump now, with the same licence as data already there.
4. **Box scores come with the points.** SofaScore's pre-2025 ITF matches carry full serve and return statistics, which the dump has for 0.1% of those matches.
5. **Rights seams shape any point dataset.** Coverage breaks around the dates official data changed hands (ITF in 2025, Challenger around 2022–24), and different sites break differently: SofaScore lacks Challenger 2022–23, TennisLive has it. A merged point layer needs a per-source, per-period provenance field, not one flag.
6. **Vendor claims could not settle coverage.** The paid sources' claims could not be checked without buying, and their unstated shares are upper bounds.
   * Sportradar adds nothing SofaScore does not already show for the same years.
   * Infront would cover ITF 2025, SofaScore's gap, but sells no archive.

## Corrections for the source register

The [source register](../../research/tennis-data-audit/source-register.md) was organized on 11 September 2026, before this study. These entries are now out of date. They are listed here and **not applied**, because the register is generated from its JSON files.

* **Wrong or stale:**
  * **PUB038 TennisLive:** listed as "Lead only … Defer". It shows point-by-point on public pages for ITF 2018+ and Challenger 2016+, and on 15 of 15 pages sampled here. Its terms need permission for bulk use.
  * **PUB009 Sackmann point strings:** listed as "original payload unavailable". Two GitHub copies hold 2011 to January 2017.
  * **PUB007 Tennis Abstract charting index:** it is fetchable in one request (robots.txt allows it). It holds 18,262 chart links, with men's charts to 13 September 2026.
* **Superseded by measurements here:**
  * **The Live Tennis API entries:** the vendor's archive excludes ITF before 2023, and 60.5% of 2023+ matches are point-complete. The June 2026 sample measures 86% for these players.
  * **sportradar_tennis_v3:** its terms (display-only; no prediction-market use without consent; destroy at end) and its per-point fields.
* **Missing:**
  * SofaScore;
  * Flashscore/Livesport;
  * the Grand Slam scoring feeds;
  * TDI's "Tennis Results" site;
  * ATP Tour tracking under Live ELC;
  * the point claims of Enetpulse, OnCourt and api-tennis.com.

## Limitations

* **Transcription.** Every SofaScore and TennisLive reading went through a web-reading tool whose small model transcribes what it sees, and it slips:
  * 9 of 58 listing markers were miscopied;
  * one event id was wrong;
  * one timestamp was a year early;
  * some opponent names were garbled.

  The study catches these where they matter (timestamps out of order, direct reads of disputed markers). Match-level SofaScore flags still carry some noise, and totals are more reliable than any single row.
* **Unread stretches.** 1,552 official matches fall where the tool cut SofaScore's pages. They are estimated from each level and period's observed rate, not measured.
* **Sample sizes.**
  * The ITF 2025–26 figures rest on 23 direct reads.
  * The TennisLive figures rest on 15 pages. Its ITF estimate starts in March 2025 because the January 2025 pages opened had no points.
  * Completeness of TennisLive records was not checked.
* **Claims are not coverage.** Paid and private sources are mapped from what their providers say, with unstated shares counted in full. Nothing was bought, so none of those figures is measured.
* **Scope.** Ten Challenger-level men show the pattern for such careers, not rates for the whole tour. WTA, doubles and junior matches are out of scope.
* **Rights.** Reading a public page for this measurement is not permission to collect it. SofaScore, TennisLive, Flashscore and the official feeds each need their own permission or licence before any bulk use.

## Rerunning

```
./python.sh src/eda/point_shot_sources/link_sofascore.py        # sofascore_raw/ -> links, events, summary
./python.sh src/eda/point_shot_sources/link_public_sources.py   # downloads (cached in data/raw/point_shot_sources/) -> public_source_rows.csv
./python.sh src/eda/point_shot_sources/pbp_checks.py            # evaluates the direct reads -> pbp_check_summary.json
./python.sh src/eda/point_shot_sources/fill_matrix.py           # fill_matrix.csv, fill_summary.json
./python.sh -m pytest test/point_shot_sources -q
```

`pbp_checks.py --sample`, `--sample-itf-recent` and `--sample-tennislive` redraw the three check samples (seeded). The SofaScore listings and the direct reads are evidence files, not reproducible downloads. They were read on 23 September 2026 through a web-reading tool, because SofaScore refuses plain HTTP clients. Reading them again later will show more matches, and possibly different coverage.
