# Lane C: ITF listings (qualifying, results after June 2026, per-match detail)

Research lane of the gap-sources study, 29 September 2026. Gaps covered: `women_itf_qualifying`, `itf_after_june_2026`, and background for `itf_detail` ([data map](../../../data_map.yaml), section `gaps:`). Research only; nothing here is an approved source.

Labels: **observed** (read in a response saved under `data/raw/gap_sources/itf/`), **provider claim** (what a source says about itself), **inference**, **not determined**.

## Bottom line

* **The ITF website's draw API is closed to a scripted client.** itftennis.com sits behind Imperva (Incapsula). `GetEventFilters` answered with JSON, but the first `GetDrawsheet` request got HTTP 403 with an Incapsula incident page. The lane stopped there, after 4 requests to that host. The site does offer a "Qualifying Draw" for singles (observed on one 2023 men's event). Its draws for 2025-26 and July-Sep 2026 were **not read**.
* **The ITF's live-data API holds complete draws, qualifying included, but only for a rolling 14-day window.** This is the API behind the ITF's own "World Tennis Tour Live" and "Live Match Centre" pages (`api.itf-production.sports-data.stadion.io`), and it needs no credentials. Its day list refuses dates more than 14 days old (HTTP 422). From 15-29 Sep 2026 it listed 64 events and 3,637 matches, with winners and set scores.
  * For ISO week 39 (21-27 Sep) it had every event: 13 men's and 10 women's. That is 403 of 403 and 309 of 310 main-draw singles matches, plus 485 men's and 283 women's qualifying matches.
  * Its event lists for weeks 38 and 39 equal Wikipedia's exactly. The archived 2025 day lists hold every women's ITF event Sackmann has that week.
  * Per-match statistics (34-40 types, including aces, double faults and serve points) and point-by-point are served by match id for 2025 and 2026 matches. They were present on 32 of 32 sampled main-draw matches, 20 of 30 sampled qualifying matches (final qualifying round always, earlier rounds mainly at W50/M25), and 5 of 6 sampled 2025 main-draw matches.
* **Polymarket's settled ITF markets give winners for about 93% of the missing main-draw matches, and for qualifying from late July.** Between 22 Jun and 20 Sep 2026 there are 13,216 ITF singles moneylines: 12,884 settled 1/0, 316 voided 0.5/0.5, 16 open in the snapshot.
  * In ISO weeks 27-38, 12,063 carry a winner. Of these, **9,149 are main draw** (men 4,925, women 4,224) and 2,914 are labelled qualifying (men 1,835, women 1,079, from 27 Jul).
  * That is 88.6% of the brief's 10,332 estimate. It is 93% of the 9,827 main-draw matches implied by the 317 events Wikipedia lists for those weeks (men 174 events, about 5,394 matches, 91% covered; women 143 events, about 4,433 matches, 95% covered).
  * Inference: the brief's women's figure (5,123) matches 2025's volume (167 events, 5,144 matches in Sackmann). 2026 had 24 fewer women's events in those weeks, so about 4,430 women's matches are missing, not 5,123.
  * In 15-22 Sep, Polymarket had markets for 373/379 men's main, 504/521 men's qualifying, 283/288 women's main and 309/309 women's qualifying matches of the ITF's own lists.
* **The Live Tennis API sample adds no winners, and qualifying only from 21 Jul 2026.** It lists 541 men's and 554 women's ITF qualifying matches (none in 2025) and 3,566 men's and 3,217 women's ITF main-draw matches from 22 Jun to 13 Aug 2026. Zenodo now has **v1.0.2 (28 Sep 2026)**. It has the same rows and still ends 13 Aug, but corrects `scheduled_time_utc`: the v1.0.0 file the project holds is in Israel local time (2-3 h ahead of UTC).
* **Tennis Explorer lists women's ITF, qualifying included; it lists no men's ITF in 2026.** Examples: W15 Monastir (20-27 Sep) has 31 main-draw and 40 qualifying matches with set scores and bookmaker odds, the same counts as the ITF's own list; W35 Aldershot (27 Jul-2 Aug) has 31 and 24. Wikipedia gives only quarter-finals onward, and no qualifying.

## C1. The official ITF listings

### itftennis.com (observed, 29 Sep 2026, 17:28-17:31 UTC)

| Request | Answer |
|---|---|
| `https://www.itftennis.com/robots.txt` | 200. `User-agent: *`, `Disallow: /umbraco/`, `Allow: /`. Header `x-cdn: Imperva`; cookies `visid_incap_178373`, `incap_ses_*`, `nlbi_178373`, `ARRAffinity` |
| `/en/tournament/m15-antalya/tur/2023/m-itf-tur-29a-2023/` | 200, 61 KB, redirected to `.../draws-and-results/`. The page embeds Imperva's bot-protection script (`/fic-number-thrall-faire-touch-dull-fight-erefull`) and `/_Incapsula_Resource`. The draw is a React component (`DrawSheet`) filled by JavaScript; `window.ITF_PAGE.tournament_id = "M-ITF-TUR-29A-2023"` |
| `/tennis/api/TournamentApi/GetEventFilters?tournamentKey=M-ITF-TUR-29A-2023` | 200 JSON (`Microsoft-IIS/10.0` behind Imperva): `tournamentId 1100192931`, `tourType "N"`, `circuitCode "MT"`, filters Singles → Main Draw (`M`) and **Qualifying Draw (`Q`)**, Doubles → Main Draw |
| `/tennis/api/TournamentApi/GetDrawsheet?circuitCode=MT&eventClassificationCode=Q&matchTypeCode=S&tournamentId=1100192931&tourType=N&weekNumber=0` | **403**, 853 bytes: "Request unsuccessful. Incapsula incident ID ..." (`edet=15`; `x-iinfo ... B15(12,...)`). The lane stopped requesting this host |

* The page bundle (`https://itftennis-ep.azureedge.net/media/assets/bundle.js`, an Azure CDN host) names 31 `/tennis/api/*` endpoints (observed). They include `TournamentApi/GetCalendar`, `GetCalendarFilters`, `GetEventFilters`, `GetDrawsheet`, `GetOrderOfPlay`, `GetOrderOfPlayDays`, `GetAcceptanceList`, `PlayerApi/GetPlayerActivity` and `GetPlayerWinLoss`.
* `GetDrawsheet` takes `circuitCode` (`MT` men / `WT` women), `eventClassificationCode` (`M` main / `Q` qualifying), `matchTypeCode` (`S`/`D`), the numeric `tournamentId` from `GetEventFilters`, `tourType` and `weekNumber=0`. Calendar parameters: `circuitCode, searchString, skip, take, nationCodes, zoneCodes, dateFrom, dateTo, indoorOutdoor, categories, isOrderAscending, orderField, surfaceCodes, singlesDrawFormat`.
* Tournament keys changed format. 2023 keys look like `M-ITF-TUR-29A-2023`; the 2025-26 keys look like `W-ITF-TUN-2026-034`, with URL `.../w15-monastir/tun/2026/w-itf-tun-2026-034/`.
* On 23 Sep 2026 the career-coverage study saw the site refuse all automated requests after a few reads (empty responses). Today's refusal took a different form (403 at the first draw request) (observed, [career coverage README](../../../../docs/studies/career_coverage/README.md)).
* **Not determined:** whether itftennis.com serves 2025-26 qualifying draws and July-Sep 2026 results, since they were not read. A search engine shows 2026 fact sheets such as W15 Monastir 29 Jun-5 Jul: "singles qualifying draw 48, main draw 32" (provider claim via search snippet; not fetched). A browser-based read, as the career-coverage study did for atptour.com, was not attempted. Whether to do so is the owner's call.
* **Statistics on the site's draws (observed in archived responses):** the draw format carries players, set scores (with tie-break losing score), winner, seed, entry status and play status. It has no statistics fields. This was seen in Internet Archive captures of `GetDrawsheet` from 2022 (XML), 2023, 2024 and June 2026, and the bundle has no per-match statistics component for draws. None of those four captures is a World Tennis Tour professional event: 2022 is an Olympic women's singles draw, 2023-24 are legends doubles, and June 2026 is a draw of senior players requested with circuit `WT`. So the 2019-2024 WTT check asked for is **not determined** on the live site. Inference: none there.

### The ITF live-data API (observed)

The ITF pages load `https://widgets.itf-production.sports-data.stadion.io/itf-widget-sdk.umd.js` (Stadion; served from AmazonS3). The SDK calls `https://api.itf-production.sports-data.stadion.io/` with no credentials for the endpoints used here. An `Authorization` header appears only for a video-rights check. There is no `robots.txt` (404), no OpenAPI document (404), and no bot challenge was met in 138 requests.

| Endpoint (from the SDK) | Behaviour |
|---|---|
| `custom/wttCompleteMatchList/<YYYY-MM-DD>` | Every World Tennis Tour singles and doubles match of that day, by event and court. Each event has name, `tennisId` (the ITF key), grade (`eventCategory.type`), start/end dates, surface and country. Each match has draw (`Main Draw` / `Qualifying Draw`), round, status, `winnerSideId`, set scores, duration, `isLiveStreamed` and an ITF match id. **HTTP 422 "date must be within 14 days of today" otherwise**: 14 Sep was refused and 15 Sep served on 29 Sep; future dates were not tested |
| `custom/matchRibbon/<date>/wtt` | Same 14-day rule (422 for 15 Jul 2026) |
| `custom/widgetMatchStats/<match uuid>` | Per side, per set and match total, 34 statistic types. These include Aces, Double Faults, Serve Points Played, First Serve Percentage, First/Second Serve Points Won, Break Points Played/Saved/Converted, Return Points and Serve Games. Higher grades add 6 (winners by stroke, net and baseline points). An empty body (212 bytes) means no data |
| `custom/pointByPoint/<match uuid>` | Every point: server, outcome (`ACE`, `DOUBLE_FAULT`, `POINT`...) and game score after it. An empty body (96 bytes) means no data |

The per-match endpoints answered for 2025 match ids taken from archived day lists (observed), so they are not date-limited. Only the day lists that enumerate matches are.

**Completeness.**
* Weeks 38 and 39 of 2026: the day lists' events equal Wikipedia's lists exactly. Women: 8 of 8 and 10 of 10; men: 10 of 10 and 13 of 13; no event on one side only.
* 2025: the six archived day lists (Internet Archive) hold every women's ITF event that Sackmann lists for that week (13/13, 14/14, 9/9, 15/15). For men they hold 14 of 16 (one missing is a Monastir event listed without a key), 18/18, 6/6 and 13/14.
* Inference: the list covers all WTT events, not a covered subset.

**Window totals (singles, 15-29 Sep 2026; `itf_site_summary.json`).**

| Main-draw week | Tour | Events | Main listed / with result | Qualifying listed / with result |
|---|---|---|---|---|
| 2026-W38 (14-20 Sep) | M | 10 | 306 / 306 | 44 / 44 (partial: qualifying was 12-14 Sep) |
| 2026-W38 | W | 8 | 244 / 244 | 32 / 32 (partial) |
| 2026-W39 (21-27 Sep) | M | 13 | 403 / 403 | 485 / 479 |
| 2026-W39 | W | 10 | 309 / 309 | 283 / 280 |

The Wayback captures of 2025 day lists show women's ITF qualifying in 2025. On 17 Mar 2025 (a Monday) the list held 188 women's qualifying matches across 15 events, 185 with results. On 9 Jun 2025 it held 157 across 14 events, 155 with results (observed, single-day views).

### Sampled events

* 12 events from Sep 2026 come from the live lists. The week-39 events are complete; for week-38 events the main draw is complete and qualifying before 15 Sep is missing.
* 9 events from 2025 come from archived Monday lists, so only one day each is shown.
* Picks are grade-spread and deterministic (`itf_site.py`). Full fields are in [itf_site_events.csv](../itf_site_events.csv).
* Counts are "with result / listed". Statistics are "with values / checked"; PBP is "with points / checked".

| Group | Event | ITF key | City | Dates | Qualifying | Main | Statistics | PBP |
|---|---|---|---|---|---|---|---|---|
| W 2026-W39 | W50 Berkeley, CA | W-ITF-USA-2026-043 | Berkeley, CA, USA | 21-27 Sep 2026 | 24/24 | 31/31 | Q 4/4, MD 4/4 | 2/2 |
| W 2026-W39 | W50 Yecla | W-ITF-ESP-2026-023 | Yecla, Spain | 20-27 Sep 2026 | 24/24 | 31/31 | Q 4/4, MD 4/4 | 2/2 |
| W 2026-W39 | W15 Belem | W-ITF-BRA-2026-009 | Belem, Brazil | 21-27 Sep 2026 | 4/6 | 31/31 | Q 2/2, MD 4/4 | 2/2 |
| W 2026-W39 | W15 Monastir | W-ITF-TUN-2026-034 | Monastir, Tunisia | 20-27 Sep 2026 | 40/40 | 31/31 | Q 1/4, MD 4/4 | 1/2 |
| M 2026-W39 | M25 Falun | M-ITF-SWE-2026-004 | Falun, Sweden | 20-27 Sep 2026 | 24/24 | 31/31 | Q 4/4, MD 4/4 | 2/2 |
| M 2026-W39 | M25 Setubal | M-ITF-POR-2026-014 | Setubal, Portugal | 20-27 Sep 2026 | 52/52 | 31/31 | Q 1/4, MD 4/4 | 1/2 |
| M 2026-W39 | M15 Columbia, SC | M-ITF-USA-2026-039 | Columbia, SC, USA | 21-27 Sep 2026 | 24/24 | 31/31 | Q 2/4, MD 4/4 | 1/2 |
| M 2026-W39 | M15 Telavi | M-ITF-GEO-2026-004 | Telavi, Georgia | 21-27 Sep 2026 | 24/24 | 31/31 | Q 2/4, MD 4/4 | 2/2 |
| W 2026-W38 | W75 Le Neubourg | W-ITF-FRA-2026-020 | Le Neubourg, France | 13-20 Sep 2026 | before window | 31/31 | MD 1/1 | 1/1 |
| W 2026-W38 | W15 Sao Luis | W-ITF-BRA-2026-007 | Sao Luis, Brazil | 14-20 Sep 2026 | before window | 31/31 | MD 1/1 | 1/1 |
| M 2026-W38 | M25 Guiyang | M-ITF-CHN-2026-027 | Guiyang, China | 13-20 Sep 2026 | 8/8 (partial) | 31/31 | Q 1/1, MD 1/1 | 2/2 |
| M 2026-W38 | M15 Tsaghkadzor | M-ITF-ARM-2026-005 | Tsaghkadzor, Armenia | 13-19 Sep 2026 | before window | 31/31 | MD 1/1 | 1/1 |
| W 2025 | W75 Luan | W-ITF-CHN-2025-004 | Luan, China | 16-23 Mar 2025 | 8/8 (17 Mar only) | - | Q 1/1 | 1/1 |
| W 2025 | W35 Swan Hill | W-ITF-AUS-2025-003 | Swan Hill, Australia | 16-23 Mar 2025 | 16/16 (17 Mar) | - | Q 0/1 | 0/1 |
| W 2025 | W15 Sharm ElSheikh | W-ITF-EGY-2025-009 | Sharm El Sheikh, Egypt | 16-23 Mar 2025 | 16/16 (17 Mar) | - | Q 0/1 | 0/1 |
| W 2025 | W100 Biarritz | W-ITF-FRA-2025-013 | Biarritz, France | 9-15 Jun 2025 | 10/10 (9 Jun) | - | Q 1/1 | 1/1 |
| W 2025 | W15 Gdansk | W-ITF-POL-2025-002 | Gdansk, Poland | 9-15 Jun 2025 | 15/16 (9 Jun) | - | Q 0/1 | 0/1 |
| W 2025 | W15 Tashkent | W-ITF-UZB-2025-002 | Tashkent, Uzbekistan | 9-15 Jun 2025 | 15/15 (9 Jun) | - | Q 1/1 | 1/1 |
| M 2025 | M25 Badalona | M-ITF-ESP-2025-010 | Badalona, Spain | 16-23 Mar 2025 | 25/25 (17 Mar) | - | Q 0/1 | 0/1 |
| M 2025 | M15 Villa Maria | M-ITF-ARG-2025-002 | Villa Maria, Argentina | 16-23 Mar 2025 | 16/16 (17 Mar) | - | Q 0/1 | 0/1 |
| M 2025 | M25 Ceska Lipa | M-ITF-CZE-2025-002 | Ceska Lipa, Czechia | 8-15 Jun 2025 | 8/8 (9 Jun) | - | Q 1/1 | 1/1 |

Dates are the event's own start and end (the start includes qualifying). Every 2026 main draw has 31 singles matches.

2025 main-draw statistics were checked on six matches from the archived lists of 30 Jan and 16 May 2025. Five had statistics (34 types) and point-by-point: W35 Bethany Beach QF, W15 Tsaghkadzor R16, M25 Antalya R16, M15 Luan QF and M25 Reggio Emilia QF. W15 Antalya R16 (Jan 2025) had neither.

Inference: umpire scoring devices record every main-draw match and the final qualifying round, and earlier qualifying rounds only at some events. This agrees with the ITF's 2025 table in the point-source study ("chair-umpire scoring only at M25 final qualifying round").

### Archived copies (Internet Archive CDX, observed)

* `itftennis.com/tennis/api/TournamentApi/GetDrawsheet*`: 30 captures, 2 with parameters (a June 2026 draw of senior players, and one 776-byte HTML page from July 2026). This is not a route to bulk ITF draws.
* `api.itf-production.sports-data.stadion.io/*`: 384 captures. They include six day lists (2025-01-30, 2025-03-17, 2025-05-16, 2025-06-09, 2026-01-29, 2026-05-11) and four match-statistics captures. None falls in July-Sep 2026.
* The 2025-01-30 list was captured on 2025-07-23, so the 14-day limit is newer than that (inference).

## C2. Other public listings

| Source | Qualifying listed? | After June 2026? | Evidence |
|---|---|---|---|
| Tennis Explorer | **Women: yes**, as a separate "singles - qual." tab with round codes `Q-1R`, `Q-2R`, `Q-R16`, set scores and bookmaker odds. **Men: no ITF events at all in 2026** | Women: yes | Observed. `/monastir-51-itf/2026/wta-women/` ("Monastir 51 ITF 2026 (Tunisia)", $15,000, hard) = sampled W15 Monastir W-ITF-TUN-2026-034: 31 main (1R 16, R16 8, QF 4, SF 2, F 1) and 40 qualifying (16/16/8), the same as the ITF list. `/aldershot-itf/2026/wta-women/` (W35 Aldershot, 27 Jul-2 Aug): 31 main and 24 qualifying; the final Saigo d. Karunaratne 7-5 2-6 6-3 agrees with the Live Tennis API index. Men: the 2026 calendar (`/calendar/atp-men/`) lists 279 tournaments (204 Challengers) and none ITF, and `/aldershot-itf/2026/atp-men/` (a known M25 event) returns an empty "[tournament]" template. robots.txt disallows only `/redirect/`, `/terms-of-use/`, `/contact/`; its terms restrict automated extraction (fact from the [public-dump study](../../../../docs/studies/public_data_dump/README.md)) |
| Wikipedia, "2026 ITF Men's/Women's World Tennis Tour (April-June / July-September)" | No | Yes, **quarter-finals on**: per event the singles champion with final score, runner-up, semifinalists and quarterfinalists, plus doubles, each linking to the ITF draw by key | Observed (MediaWiki API, 4 requests). Weeks 27-38: 174 men's and 143 women's events; weeks 38-39 equal the ITF live lists exactly. All three sampled Sep events and both Aldershot events are there |
| Flashscore / Tennis24 | Not determined | ITF women's event pages exist (e.g. `tennis24.com/itf-women-singles/w15-monastir-50/results/`) | Observed via web search. The pages are JavaScript shells: no match rows without the feeds, which were not read. The Flashscore files already on disk are handled by `flashscore_itf.py` in this study |
| ATP / WTA sites | ATP player activity: ITF main draws only | - | Not rechecked here. The career-coverage study found atptour.com's per-season activity lists men's ITF main draws, not qualifying |
| ITF fact sheets | Draw sizes only | - | Provider claim via search snippets (e.g. qualifying draw 48 at W15 Monastir) |

The lane also checked Polymarket and Wikipedia on the sampled events. Polymarket has moneylines for all 40 qualifying matches of W15 Monastir (Sep 2026), 47 of the 52 at M25 Setubal and 24 of 24 at W50 Berkeley. It has all 31 main-draw matches of W35 and M25 Aldershot (July), resolved. The catalog snapshot ends 22 Sep, so the September main draws are only started.

## C3. Live Tennis API public sample (Zenodo)

Counts are in [itf_listing_counts.csv](../itf_listing_counts.csv) and [itf_listing_summary.json](../itf_listing_summary.json) (`itf_listing_counts.py`).

**How ITF rows are identified (observed).**
* ITF singles are `tier_key` 270 (men; M15/M25 names) and 271 (women; W15-W100).
* Tiers 264 and 287 and the untiered M/W rows are ITF **doubles**: 2,283 rows, every one listing "/" pairs. They are left out.
* Qualifying appears only as the round label "Qualifications"; `is_qualifying` is never true on ITF rows.
* Two naming styles ("ITF W35 Aldershot Women" and "W35 Aldershot") list some matches twice under different player ids. Dropping repeats on the surname pair within 36 hours removes 169 rows (54 after 22 Jun). 65 "Cancelled" rows are dropped.
* Times are converted from Israel local time (see the note on v1.0.2 below).

**Counts.**

| | Men | Women |
|---|---|---|
| ITF qualifying rows, 2025 | 0 | 0 |
| ITF qualifying rows, 2026 | 541 (Jul 303, Aug 238) | 554 (Jul 262, Aug 292) |
| First qualifying row | 21 Jul 2026 (week 30) | same |
| Qualifying per week, weeks 30-32 | 146-157 | 107-219 |
| ITF main-draw rows, 22 Jun-13 Aug 2026 | 3,566 | 3,217 |
| of which weeks 27-33 (week 33 ends Thu 13 Aug) | 3,102 | 2,757 |

* For scale, the ITF's own list shows 485 men's and 283 women's qualifying matches in week 39. Inference: the Zenodo qualifying rows are a partial listing.
* The index has **no winners or scores**. It also has no ITF singles rows at all in April 2026, although other tiers have 2,175 rows that month, and only 16 men's rows in December 2025.

**Newer Zenodo versions (observed via the Zenodo API, concept DOI 10.5281/zenodo.22048730).**
* **v1.0.1** (22 Aug 2026): description fix only. The data files are identical to v1.0.0, and it says live point observation began 12 Oct 2025.
* **v1.0.2** (28 Sep 2026, record 23018680): same rows (173,571 matches, still 1 Jan 2023-13 Aug 2026). It corrects timestamps: "The timestamps in versions 1.0.0 and 1.0.1 were labelled UTC but were written in Israel local time." In `matches.csv.gz`, 120,758 rows move back 3 h and 52,813 back 2 h. The project stages v1.0.0 (`data/dump/matches/live_tennis_api_zenodo/`), so every join on `scheduled_time_utc` is 2-3 h off until it is re-staged.

**Vendor claims (livetennisapi.com, read 29 Sep 2026; provider claims).**
* The home page and `/historical-tennis-data-api` say: "ATP, WTA, Challenger and ITF, singles and doubles", "ITF point depth from 2025 via the governing body's own umpire feed", and 60.5% of completed matches since 2023 point-complete as of 21 Sep 2026.
* Its "Qualifying draws, at scale" claim (30,306 of 97,901 matches) is about the 2013-2022 reconstruction. The page says that reconstruction does not cover ITF ("ITF and futures, all draws 141 / 145,117, under 0.1%").
* `/data/academic` tabulates ITF women's singles 37,379 (37,132 with a point sequence, 4,843 live-observed) and ITF men's singles 35,642 (35,377; 4,896). These equal tiers 271 and 270 of the sample.
* No page states ITF qualifying coverage. Inference: the vendor's own ITF source is the ITF live-data feed described in C1.

## C4. Polymarket settled ITF markets

Source: the project's catalog. The census snapshot is from 10 Sep 2026 and the extension from 22 Sep 2026 (`data/dump/odds/polymarket/`; rules text in `data/studies/tennis_data_audit/polymarket/markets.jsonl.gz` and `data/raw/public_dump/polymarket_catalog/markets_extension.jsonl.gz`). Scope: ITF-bucket moneylines, dated by `gameStartTime`.

* **Gender and draw come from each market's rules text (observed).** The first sentence names the event: "in the ITF Men Hurghada", "ITF Women Bastad", "M25 Setubal", "W50 Yecla". This gives the gender for all 17,930 ITF moneylines.
* **Draw labels.** "Qualifying" appears from a 27 Jul 2026 match and "Main Draw" from 1 Sep; before that the text names no draw. Against the Live Tennis API rows of 22 Jun-13 Aug, 5,741 of the 5,742 unlabelled markets that match any row match a main-draw row. Labelled "Qualifying" markets match only qualifying rows (178; 111 unmatched). So unlabelled is counted as main draw.
* **Settlement rules (provider claim, same rules text).** The market resolves to the player who "advances", including by retirement or default. A walkover, cancellation, or no winner within 14 days resolves 50-50. Primary resolution source: "official information from the International Tennis Federation".

| Match time 22 Jun-20 Sep 2026 | Men | Women |
|---|---|---|
| ITF moneylines | 7,377 | 5,839 |
| settled 1/0 (winner) | 7,169 | 5,715 |
| voided 0.5/0.5 | 199 | 117 |
| open in the snapshot | 9 | 7 |
| **ISO weeks 27-38, settled 1/0** | **6,760** | **5,303** |
| of which main draw (label or unlabelled) | 4,925 | 4,224 |
| of which qualifying (label; from 27 Jul) | 1,835 | 1,079 |
| brief's estimate of missing main-draw matches, weeks 27-38 | 5,209 | 5,123 |
| Wikipedia events, weeks 27-38 (× 31 matches) | 174 (5,394) | 143 (4,433) |
| main-draw winners / Wikipedia-implied matches | 91% | 95% |

**Coverage cross-checks (observed; `crosschecks` in the summary JSON).**
* 15-22 Sep: 1,496 ITF moneylines. 826 match qualifying and 656 main-draw matches of the ITF's own lists; 14 are unmatched.
* 22 Jun-13 Aug: 77-93% of the Live Tennis API's main-draw rows per week have a market. Weeks 26-28 are lowest (77-85%); from week 29 it is 83-93%.
* By week, labelled qualifying markets grow from 35-43 per tour in week 31 to 286-395 (men) and 131-238 (women) a week from week 34 (CSV, `period_type = iso_week`).

## Caveats

* The ITF website's draws, the best listing, were not read (blocked). The ITF live-data route reaches only the last 14 days. For weeks 27-37 of 2026 the observed public routes are Polymarket (winners only, main draw about 93%, qualifying from late July), Tennis Explorer (women only, scores and odds), the Live Tennis API sample (no winners) and Wikipedia (QF on). SofaScore is another lane's.
* Inference, not tested: polling the day list daily from now on would capture every World Tennis Tour result, qualifying included, with statistics and point-by-point where recorded. The per-match endpoints serve 2025-26 matches by id, but ids for July-Aug 2026 come only from day lists no longer served. Enumerating older matches another way would mean using undocumented endpoints to get round the operator's date rule, and was not tried.
* Statistics coverage rests on 30 qualifying and 32 main-draw matches (week 39) plus 15 matches of 2025; it is a sample, not a rate.
* Gender inference is from rules text. The main/qualifying split before 1 Sep rests on the Live Tennis API match described above.
* Polymarket figures are catalog snapshots: markets deleted before 10 Sep, or created after 22 Sep, are not counted.
* "31 matches per event" assumes 32-player main draws. Walkovers are counted as matches in the ITF lists but settle 0.5/0.5 on Polymarket.
* Terms: ITF regulations give its licensing arm the data rights and bar betting use (fact, from the [point-shot study](../../../../docs/studies/point_shot_sources/README.md)). The ITF site's terms page was not read. The Stadion API has no robots.txt. The owner decided on 23 Sep 2026 to collect public data regardless of such terms for non-commercial research.

## Files and reproduction

* Raw answers (gitignored, 158 MB) are in `data/raw/gap_sources/itf/`: the ITF site at the top level (`robots.txt`, `pages/`, `api/`, `assets/`), other hosts under `other/<host>/`, one receipt per request in `_receipts.jsonl`, and the block marker in `_blocked.json`.
* Requests on 29 Sep 2026, 17:28-18:14 UTC: 184 in total. Stadion API 138 (133 × 200, 3 × 422, 2 × 404), web.archive.org 19, tennisexplorer.com 10, itftennis.com 4 (1 × 403), zenodo.org 4, en.wikipedia.org 4, livetennisapi.com 3, and one each to the two ITF asset hosts. Requests went one at a time, at least 2.5 s apart plus jitter.
* Scripts in `src/eda/gap_sources/`:
  * `itf_http.py`: the paced, receipted client. It stops on a block and refuses a blocked host afterwards.
  * `itf_site.py`: `fetch-live`, `fetch-wayback`, `fetch-detail`, `fetch-stats`, `build`. Produces [itf_site_events.csv](../itf_site_events.csv) and [itf_site_summary.json](../itf_site_summary.json).
  * `itf_listing_counts.py`: C3 and C4 from the dump. Produces [itf_listing_counts.csv](../itf_listing_counts.csv) and [itf_listing_summary.json](../itf_listing_summary.json).
* Rerun: `./python.sh src/eda/gap_sources/itf_site.py build` and `./python.sh src/eda/gap_sources/itf_listing_counts.py`. Both run offline from the cache. The fetch steps re-ask only for what is missing, but `fetch-live` now reaches only the 14 days before its run date.

## Sources (accessed 29 September 2026)

* https://www.itftennis.com/robots.txt ; https://www.itftennis.com/en/tournament/m15-antalya/tur/2023/m-itf-tur-29a-2023/ ; https://www.itftennis.com/tennis/api/TournamentApi/GetEventFilters?tournamentKey=M-ITF-TUR-29A-2023 ; `.../GetDrawsheet?...` (403)
* https://itftennis-ep.azureedge.net/media/assets/bundle.js ; https://widgets.itf-production.sports-data.stadion.io/itf-widget-sdk.umd.js
* https://api.itf-production.sports-data.stadion.io/custom/wttCompleteMatchList/2026-09-15 … 2026-09-29 ; `custom/widgetMatchStats/<id>` ; `custom/pointByPoint/<id>`
* https://web.archive.org/cdx/search/cdx?url=api.itf-production.sports-data.stadion.io/&matchType=prefix ; https://web.archive.org/cdx/search/cdx?url=www.itftennis.com/tennis/api/TournamentApi/GetDrawsheet&matchType=prefix
* https://zenodo.org/api/records/22048731/versions?allversions=true&size=25 ; https://zenodo.org/records/23018680
* https://livetennisapi.com/ ; https://livetennisapi.com/historical-tennis-data-api ; https://livetennisapi.com/data/academic
* https://www.tennisexplorer.com/monastir-51-itf/2026/wta-women/ (and `?phase=qualification`) ; https://www.tennisexplorer.com/aldershot-itf/2026/wta-women/ (and `?phase=qualification`) ; https://www.tennisexplorer.com/calendar/atp-men/ ; https://www.tennisexplorer.com/aldershot-itf/2026/atp-men/
* https://en.wikipedia.org/wiki/2026_ITF_Women%27s_World_Tennis_Tour_(July%E2%80%93September) ; https://en.wikipedia.org/wiki/2026_ITF_Men%27s_World_Tennis_Tour_(July%E2%80%93September) ; the April-June pages
* https://www.tennis24.com/itf-women-singles/w15-monastir-50/results/ (JavaScript shell)
