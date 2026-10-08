# Lane A2: Slam editions and courts without serve speed, and ESPN (7 Oct 2026)

**Status: research notes, not a decision.** All probes ran on 7 Oct 2026, 14:01–15:03 UTC.

**Scope.** Where per-match first-serve speed can be had for:
* the Slam editions the project lacks (AO 2025, RG 2025, RG 2026);
* Slam courts and qualifying events with no speed;
* ESPN's tennis data at every level.

**Rules kept.**
* No login, account, form, purchase or email.
* No decryption or key testing. Encrypted Infosys envelopes were inspected for their top-level keys only.
* No CAPTCHA or bot-challenge workaround. None was met.
* At most 22 requests per host, at least 3 s apart on the same host (2 s on web.archive.org). Every request is in the probe log (§7).
* Nothing was written to the repository except this file. Payloads and scripts are in the session scratchpad (`…/scratchpad/laneA2/`), not kept.

**Evidence labels:**
* **[observed]:** I saw the field and its values today.
* **[observed, local]:** read in files the project already holds.
* **[observed via summariser]:** a WebFetch summary of the page.
* **[documented]:** the provider describes it.
* **[claimed]:** the provider asserts it.
* **[third-party report]**, **[search excerpt]**, **[inference]**, **[not determined]**.

## 0. Bottom line

1. **AO 2025: no public, plain, edition-wide source of per-match average first-serve speed exists that I could find.** What there is:
   * **Already held:** the 8 Wayback match-centre captures (6 of them singles with speeds). The SirGenkii fork adds **14 men's first-round matches with per-point serve speed and serve number** [observed, local]. None of the 14 has speed in the Wayback set: the only overlap, MS101, was captured before play.
   * **Gone:** the ATP Stats Centre no longer serves those files ("Match Not Found" / S3 403 today) [observed].
   * **Weak:** a tournament top-20 "Fastest serve speed" leaderboard [observed].
   * **Not determined:** Eurosport/TNT statistics, which load client-side from a persisted-query GraphQL API.
   * **Encrypted:** the live Infosys MatchBeats file for the AO 2025 final is still served, encrypted (200, `data: null`) [observed]. It is probably the only edition-wide carrier [inference: the earlier pass found live files for 2022, 2025 and 2026], and usable only through the owner's decryption decision.
2. **RG 2025 and RG 2026: no plain route.**
   * **rolandgarros.com's own match API is plain JSON** with a `serviceStatistics` block (`fastest`, `averageFirstServe`, `averageSecondServe`, "Service speed (mph)").
     * **2023–2026: every value is `null`.** Seen in 6 matches, show courts included, and in a Wayback capture of the 2025 final taken 2.5 hours after it ended [observed].
     * **2019 and 2022: `fastest` is plausible (119–131 mph); the "averages" are 0–6.** They are unusable [observed].
   * **The only carriers seen are Infosys files, all encrypted:**
     * **Live:** the RG 2025 `match-centre/2025/520/{MID}/data.json` file, whose `stats` block is encrypted (SM100: 200), and the RG 2026 key-stats API (SM001: 200) [observed].
     * **Wayback:** files for only 13 RG 2025 and 10 RG 2026 main-draw singles matches, plus 58 RG 2025 qualifying matches [observed, CDX].
     * **ATP Stats Centre:** no RG key stats ("Match Not Found") [observed].
3. **ESPN carries no tennis match statistics at any level** [observed].
   * **Listings:** 0 of 6,508 competition listings in 13 scoreboards carry a statistic.
   * **Statistics endpoint:** `…/competitors/{id}/statistics` answers 404 "No competitor stats found" for all 12 matches tried: Slams 2019–2026, WTA 1000 2025–26, ATP 500 2025–26, ATP 250 2016 and 2019. Scoreboards go back to Wimbledon 2016.
   * **Stats source:** `statsSource` is "none".
   * **Coverage:** ATP and WTA leagues only, so no Challengers or ITF.
   * **Consequence:** it cannot fill ATP May 2025 onward, WTA, or ATP 2015–2020.
4. **Outside courts and qualifying: speed was mostly never measured,** so no source can fill them (detail in §3).
   * **Wimbledon 2019–2024:** speed only on the six show courts (Centre, No.1, No.2, No.3, 12, 18), which have it on 100% of matches. Courts 4–11 and 14–17 have it on 0% (one exception). Qualifying 2019–24 has 0 of 224 matches each year [observed, local].
   * **RG 2022:** speed on Chatrier, Lenglen, Simonne-Mathieu and Courts 6, 7, 13 and 14. None on Courts 4, 5 or 8–12 [observed, local; RG's own API agrees on a Court 9 / Court 13 pair, observed].
   * **AO 2020–2024:** every court has speed [observed, local].
   * **AO 2015–19:** about 70% of main-draw singles have speed. Which courts lacked it is not determined.
5. **Held-data findings that change the brief's "no speeds" list** [observed, local]:
   * **RG 2018** has speeds, but only in `Speed_MPH`, with `ServeNumber` filled. They are recoverable now.
   * **2012–2013 (all Slams) and AO 2014** have speeds on 82–96% of points, but no serve-number marker. So first-serve speed cannot be identified directly.
   * **Wimbledon 2016 women's** points are absent from the archive altogether.

## 1. Method

* **Read first:** the five earlier-pass files the brief lists.
* **ESPN.** Scoreboards, the core API's competition, competitor, statistics, athlete, season-statistics and event-log resources, the summary endpoint, and one web match page and one web scoreboard page. The matches cover the tiers and years the brief asked for (§2.1).
* **Roland-Garros.** robots.txt; three match pages, whose Nuxt state was decoded locally with Node (an `eval` of the saved state, no network); the eight Nuxt bundles; the single-match API for 11 matches.
* **Wayback Machine.**
  * CDX surveys of the RG and AO Infosys hosts, RG match pages and the AO scores API.
  * Capture reads: the RG 2025 final page, two encrypted Infosys files (for keys only), and three AO API files.
* **archive.today:** one timemap and three prefix or host listings.
* **ATP Stats Centre host** (`itp-atp-sls.infosys-platforms.com`): 14 existence checks on Slam key-stats and rally files, calibrated against a file lane A1 received today.
* **Live RG and AO Infosys hosts:** 7 existence checks (`itp-rg-sls` 5, `itp-ao-sls` 2). Top-level keys and the plain `data` fields were read; no ciphertext was decoded.
* **Third parties and datasets.**
  * TNT Sports/Eurosport (robots.txt, a match page, its stats tab, 7 JS chunks), Tennis Majors (WebFetch), Matchstat (third-party code on GitHub).
  * Hugging Face API searches (8) and tree reads (4); GitHub code searches (`gh api`, the owner's logged-in CLI, read-only, about 15 calls); data.gouv.fr API (3); about 20 WebSearch calls; 9 WebFetch calls.
* **Local measurement of held data,** in scratchpad scripts:
  * speed fill by Slam, year, event and court from the Sackmann archive, the Wimbledon and US Open feed tables, the hawkilol Court Vision copy and the AO match-centre tables;
  * speed keys in the held SofaScore and WTA API files;
  * the SirGenkii fork's AO 2025 rows.

## 2. Per-source findings

### 2.1 ESPN (all levels)

**Endpoints tried** (no key; a Chrome-like client; all 200 unless noted):
* `site.api.espn.com/apis/site/v2/sports/tennis/{atp|wta}/scoreboard[?dates=YYYYMMDD]`;
* `sports.core.api.espn.com/v2/sports/tennis/leagues/{atp|wta}/events/{tid-year}/competitions/{id}[/competitors/{id}[/statistics]]`;
* `…/tennis/athletes/{id}`;
* `…/seasons/{Y}/types/2/athletes/{id}/statistics`;
* `…/seasons/{Y}/athletes/{id}/eventlog`;
* `…/tennis/leagues`;
* `…/leagues/atp/events?dates=2025`;
* `site(.web).api.espn.com/…/summary`;
* `www.espn.com/tennis/match/_/gameId/{id}` and `/tennis/scoreboard/tournament/_/eventId/{id}/competitionType/1`.

**What the payloads hold** [observed]:
* **Scoreboard.** One request returns whole tournaments: every match with round, court, status, set scores and tiebreaks, and athlete ids.
  * AO 2025 alone has 635 competitions: men's and women's singles 239 each (main draw plus qualifying), doubles, mixed.
  * Every competitor's `statistics` array is empty.
* **Core competition resource.** `"statsSource":{"id":"0","description":"none","state":"none"}`, with the same for `gameSource` and `linescoreSource`. Checked on AO 2025 final 153116, USO 2025 final 161412 and China Open 2026 qualifying 186254.
* **Competitor statistics.** HTTP 404 `{"error":{"message":"No competitor stats found for competitionId = …"}}` for all 12 matches in the table below.
* **Summary endpoint.** HTTP 400. It looks up `events/{event}/competitions/{event}`, so tennis's two-level ids (event = tournament, competition = match) cannot be addressed.
* **Web.** The match page `www.espn.com/tennis/match/_/gameId/153116` is 404. The tournament scoreboard page shows results only; its "Stats" strings are other sports' navigation.
* **Athlete season statistics.** Only `singlesWon`, `singlesLost`, `singlesTitles`, `doublesTitles` and `prize`.
* **Event log.** Links to event, competition and competitor only, with no statistics refs.
* **Leagues.** The league list has only `atp` and `wta`. `leagues/atp/events?dates=2025` lists 61 events.
  * A scoreboard for 11 Sep 2025, a week of Challengers and Davis Cup only, returned just the Shanghai Masters.
  * So ESPN has no Challengers [inference from two observations]. WTA 125 events do appear (Saint-Malo, Solgironès, Suzhou, Samsun) [observed names; tier inferred].
* **Third-party corroboration.** The `LHBUSA/tennis` source matrix (`docs/TENNIS_SOURCE_MATRIX.md`) records ESPN's core API as "No surface, no ATP level, no match statistics, no Challengers" and notes "Public developer API closed 2014-12-08; no licence path" [third-party report].

**Tiers × years probed for statistics** (all 404, "No competitor stats found"):

| Tier | Match (ESPN event / competition) |
|---|---|
| Slam 2025 | AO final Sinner–Zverev (154-2025 / 153116); USO final Alcaraz–Sinner (189-2025 / 161412); RG final Alcaraz–Sinner (172-2025 / 156766) |
| Slam 2026 | RG final Zverev–Cobolli (172-2026 / 175668) |
| Slam, earlier | Wimbledon 2019 final (188-2019 / 99232); Wimbledon 2023 R1, Court 7, Karatsev–Van Assche (188-2023 / 135282) |
| WTA 1000 | Madrid 2025 final (413-2025 / 155872); China Open 2026 R4 Zheng–Charaeva (959-2026 / 184355) |
| ATP 500 | Dallas 2025 final (836-2025 / 153667); China Open 2026 SF Medvedev–Djokovic (959-2026 / 183467) |
| ATP 250 | Hungarian Open 2019 final (442-2019 / 97666); Shenzhen 2016 final (384-2016 / 74133) |
| Challenger | None listed: not in ESPN |

**Scoreboards read** (competitions listed / with statistics):

| League, date | Events | Competitions | With stats |
|---|---|---:|---:|
| ATP, 2016-07-10 | Wimbledon 2016 (661), Shenzhen, Hamburg | 690 | 0 |
| ATP, 2019-02-24 | Hungarian Open, Marseille, Delray Beach, Dubai, Rio, São Paulo | 190 | 0 |
| ATP, 2019-07-14 | Wimbledon 2019 | 454 | 0 |
| ATP, 2023-07-03 | Wimbledon 2023 | 635 | 0 |
| ATP, 2025-01-20 | AO 2025 | 635 | 0 |
| ATP, 2025-02-09 | Dallas, Rotterdam, Delray Beach, Buenos Aires, Marseille | 238 | 0 |
| ATP, 2025-06-08 | RG 2025 (635), Stuttgart, 's-Hertogenbosch | 807 | 0 |
| ATP, 2025-09-07 | USO 2025 (619), Shanghai | 781 | 0 |
| ATP, 2025-09-11 | Shanghai 2025 only | 162 | 0 |
| ATP, 2026-06-07 | RG 2026 (633), Stuttgart, 's-Hertogenbosch | 797 | 0 |
| ATP, current | China Open, Shanghai 2026 | 385 | 0 |
| WTA, 2025-05-03 | Madrid, Saint-Malo, Solgironès | 391 | 0 |
| WTA, current | China Open, Suzhou, Samsun 2026 | 343 | 0 |

(Some events appear in two scoreboards.)

**Other facts.**
* **Speed field:** none at any level. Measuring system: not applicable.
* **Cost:** free.
* **Terms:** the ESPN page footer links "Terms of Use" to https://disneytermsofuse.com/english/ [observed]. Disney Terms of Use, "Last Updated May 24, 2024" [observed via summariser]:
  * §2.B.x bars accessing, copying or extracting "using a robot, spider, script, or other automated means", including "data mining or web scraping" and "compiling, building, creating or contributing to any collection of data, data set or database";
  * §2.A bars use in "training, testing, benchmarking or validation of any artificial intelligence or machine learning" system;
  * §3.H bars commercial use.
* **Verdict:** dead end for serve speed. ESPN could only ever be a results and score source.

### 2.2 rolandgarros.com: plain match API and page state

* **Routes** [observed]:
  * the page `https://www.rolandgarros.com/en-us/matches/{year}/{id}` server-renders a Nuxt 2 state (`window.__NUXT__`);
  * the API behind it is `https://www.rolandgarros.com/api/en-us/matches/{id}?event={year}`. It is found in bundle `5ce9bcc.js` as `"/api/".concat(lang,"/matches/").concat(id)` + `"?event="`.
  * A third-party matrix also lists `/api/en-us/results/{year}/{SM|DM|QM}` for match lists, qualifying included [third-party report; not tested].
  * robots.txt disallows only `/admin` and `/maintenance` [observed].
* **Fields** [observed]:
  * `matchStatisticsSection.matchStatistics` and `setStatistics1…5`: aces, double faults, first serve, win on 1st and 2nd serve, net points, break points, receiving points, winners, unforced errors and total points, each as `teamAValue`/`teamBValue` strings;
  * `serviceStatistics` = `{title:"Service speed (mph)", fastest, averageFirstServe, averageSecondServe}`, with labels "Max speed", "Average 1st serve speed", "Average 2nd serve speed".
  * The page component `ServiceStatistics` (bundle `d549552.js`) renders those three values from the server data. The speeds are not fetched client-side from RG.
* **Values by edition** [observed]:

| Edition, match | Court | `fastest` (mph) | `averageFirstServe` | `averageSecondServe` |
|---|---|---|---|---|
| 2019 SM001 (final) | Chatrier | 131 / 121 | 2 / 3 | 6 / 3 |
| 2022 SM001 (final) | Chatrier | 119 / 126 | 1 / 1 | 0 / 3 |
| 2022 SM041 (R2) | Court 13 | 122 / 125 | 2 / 1 | 6 / 6 |
| 2022 SM033 (R2) | Court 9 | null | null | null |
| 2023 SM001 (final) | Chatrier | null | null | null |
| 2024 SM001 (final), page | Chatrier | null | null | null |
| 2025 SM001 (final), API and page | Chatrier | null | null | null |
| 2025 SM001, Wayback capture `20250608212650` (2.5 h after the final ended) | Chatrier | null | null | null |
| 2025 SM100 (R1) | Simonne-Mathieu | null | null | null |
| 2026 SM001 (final), page | Chatrier | null | null | null |
| 2026 SD100 (R1) | Court 12 | null | null | null |

* **Reading the values.**
  * The 2019 and 2022 "averages" of 0–6 cannot be mph averages; the field is mis-mapped [inference]. `fastest` is plausible.
  * **RG's plain JSON therefore offers at most a fastest serve for 2019–2022, and nothing from 2023 on.**
* **Coverage of Wayback copies of the page:** 903 distinct RG 2025 `en-us/matches` URLs were captured, 169 singles pages during the event [observed, CDX]. They would hold the same nulls [inference from the one capture read].
* **Measuring system:** not stated. RG uses Hawk-Eye tracking on the courts with Court Vision [inference].
* **Terms** (quoted in the earlier pass, `B_grand_slams.md`): "The User is prohibited from using any software, device, robot, script, program, automated means … to extract any information, data or content from the Website."
* **Verdict:** not a route for RG 2025–26 speed.

### 2.3 Infosys match-centre files for RG and AO (live and archived)

* **RG host in the Wayback Machine** (`itp-rg-sls.infosys-platforms.com`). A CDX survey (collapse by URL) found 8,688 URLs [observed]. By family, 200 answers only:

| Family | 2025 | 2026 |
|---|---|---|
| `static/prod/match-centre/{Y}/520/{MID}/data.json` | 39 (QD 14, QM 15, SD 7, SM 3) | 0 |
| `static/prod/match-centre/{Y}/520/{MID}/he-data.json` | 21 (QM 13, SD 7, SM 1) | 9 (SD 3, SM 6) |
| `prod/api/match-beats/data/…` | 70 (QD 29, QM 28, SD 7, SM 5, DM 1) | 11 (SM 6, SD 4, MX 1) |
| `prod/api/stats-plus/v1/keystats/…` | 0 | 11 (SM 6, SD 4, MX 1) |
| `prod/api/rally-analysis/…` | 1 | 11 |
| commentary (`v2`, LLM) | 7 | 10 |
| **Distinct matches with any of the data files above** | **SM 6, SD 7, QM 29, QD 29, DM 1** | **SM 6, SD 4, MX 1** |

  * **Contents.** Two were read for their keys [observed]:
    * 2025 SM023 `data.json` = `{mbStatus, insights, mbData, rally, stats, quiz}`, each `{lastModified, response:<base64>}`;
    * 2026 SM004 key stats = `{lastModified, response, data:null}`.
  * All encrypted, and not decoded.
  * The `stats` and key-stats blobs probably hold max, average first- and average second-serve speed [inference: the decrypted ATP key-stats schema in the SirGenkii fork has `max_speed`, `serve1_avg_speed`, `serve2_avg_speed`, §2.9].
* **AO host in the Wayback Machine** (`itp-ao-sls`): 193 URLs, with data only for 2022 and 2023 [observed]. Nothing for 2025.
* **Live files, 7 Oct 2026** (Referer and Origin set to the Slam site; keys read, nothing decoded) [observed]:
  * **RG 2025** `static/prod/match-centre/2025/520/SM100/data.json`: 200, 149,833 B. Six blocks (`mbStatus, insights, mbData, rally, stats, quiz`), each `{data: null, lastModified, response}`; the `stats` response is 40,192 base64 characters.
  * **RG 2026:** the static `match-centre` path is 403 for SD100 and SM001 (no object). The **API** `prod/api/stats-plus/v1/keystats/year/2026/eventId/520/matchId/SM001` gives 200, 90,468 B, `{lastModified, response, data: null}`.
  * **AO 2025:** `static/prod/match-beats/2025/580/MS701/data.json` gives 200, 109,796 B, `{lastModified, response, data: null}`, as the earlier pass found. A `static/prod/match-centre/…` path like RG's is 403 (none).
* **Verdict.** These encrypted files are the only edition-wide carriers found for AO 2025 and RG 2025–26 speeds:
  * per set and per match key stats at RG [inference from the ATP key-stats schema];
  * per point at AO (MatchBeats [third-party description, earlier pass]).
  * Using them needs the owner's decision on decryption, plus match-id lists: RG's `/api/en-us/results/{year}/{SM|QM…}`, and AO's archived draws (held) [inference].
  * Coverage of qualifying and outer courts is unknown.

### 2.4 ATP Stats Centre host (`itp-atp-sls.infosys-platforms.com`) for Slam matches

* **The host is not blocking.** A calibration on the Paris 2025 final static key-stats file (`2025/352/MS001`, the path lane A1 used) returned 200, `{lastModified, response}` (31,616 base64 chars) [observed].
* **Slam matches** [observed]:
  * static key stats for AO 2025 / RG 2025 / RG 2026 `MS001` (lower and upper case): S3 403 `AccessDenied`, meaning no object at that path [inference from the calibration];
  * API key stats `prod/api/stats-plus/v1/keystats/year/{Y}/eventId/{580|520}/matchId/MS001`: 404 "Match Not Found" for AO 2025, RG 2025 and RG 2026;
  * rally analysis for AO 2025 `MS101` (API) and static `ms101`: 404 / 403.
  * Yet the SirGenkii fork holds AO 2025 (tournament 580) rally rows for 14 men's R1 matches [observed, local]. So those files were served in early 2025, when the fork last pushed (11 Apr 2025), and are no longer [inference].
* **Verdict:** not a route for Slam speed today. The fork's 14 AO 2025 matches are the only surviving copy found.

### 2.5 AO scores API: other endpoints in the Wayback Machine

CDX over `prod-scores-api.ausopen.com/`: 526 URLs [observed].

| Endpoint | 2025 captures | Speed content |
|---|---|---|
| `/match-centre/{MID}` | 9 (held: 8 matches) | Per-set "Fastest serve", "1st Serve Average", "2nd serve average" (km/h; mph secondary) |
| `/year/2025/stats` | 1 (6 Oct 2025) | Ten statistics, each a top-20 per event. "Fastest serve speed" in km/h (`suffix: kmh`). No average speeds, no per-match values [observed] |
| `/players/{id}/matches` | 9 | Match list and scores; no serve or speed keys [observed] |
| `/year/2025/period/MD/day/{d}/results` | 15 (7 under 1 KB) | `tournament, year, matches, courts, events, players, rounds, teams`; no statistics keys [observed] |
| `/year/2025/period/{MD|Q}/day/{d}/schedule` | 18 | Not read (the schedule mirrors the results) |

**Held AO 2025 captures with speed** [observed, local]: MS 2 of 4, WS 4 of 4, MD 1, CS 1. The MS101 capture predates play (all zeros).

### 2.6 archive.today

No mementos [observed]:
* the timemap for `https://ausopen.com/match/2025-jannik-sinner-vs-alexander-zverev-ms701` returns 404 "TimeMap does not exists";
* the prefix listings `https://ausopen.com/match/2025*` and `https://www.rolandgarros.com/en-us/matches/2025*` say "No results";
* the host listing `prod-scores-api.ausopen.com` says "No results".

No CAPTCHA was served. Dead end.

### 2.7 Third-party republishers

* **TNT Sports UK / Eurosport.**
  * AO 2025 match pages exist, for example `https://www.tntsports.co.uk/tennis/australian-open-men/2025/live-jannik-sinner-alexander-zverev_mtc1576391/live-stats.shtml` (tabs: live, commentary, stats, matches, news, table, videos), with eurosport.de, .es and .it twins [observed].
  * The server-rendered state's `matchStatistics` entity store is empty.
  * Statistics load client-side from `https://netsport.eurosport.io` (GraphQL, persisted queries: `sha256Hash`). The statistics query is in a lazily loaded chunk I did not find [observed].
  * Whether its tennis statistics include serve speed: **[not determined]**. Lane A1 saw a US Open 2026 R1 "General Statistics" without speed and an empty Shanghai object.
  * robots.txt allows the match pages for `*` [observed]. Terms not read. One fair next step: open the stats tab in a browser for one AO 2025 match.
* **Tennis Majors.** The RG 2026 R1 match page (`https://www.tennismajors.com/fr?p=798211`) shows breaks, total points, aces, double faults, and serve and return points won. No speed [observed via summariser].
* **BBC, tennis.com, L'Équipe:** no evidence of per-match speed in search [search excerpt]. Not probed.
* **Tennis Australia / ausopen.com news.** Articles quote single speeds, for example "217 km/h, his fastest of the tournament" [search excerpt, tennis.com.au, 16 Jan 2025]. Not systematic.
* **Matchstat Tennis API** (RapidAPI host `tennis-api-atp-wta-itf.p.rapidapi.com`, paid). Public code shows career-level fields `averageFirstServeSpeed`, `averageSecondServeSpeed`, `fastestServe` and `averageFastestServe` from `/tennis/v2/{atp|wta}/h2h/vs-all-stats/{player_id}/` [third-party report: `sharp-signals/Tennis` cache file `data/cache/players/atp/91521.json`, and `linbeau0822/tennis-scout-agent` `backend/data_ingestion/stats_ingester.py`].
  * Career averages imply match-level speed records upstream [inference].
  * The match-level endpoint, Slam coverage and terms are not verified. **Passed to the vendor lane.**
* **Flashscore:** skipped per brief. Lane A1 reports that Slam finals carry "Average 1st serve speed".

### 2.8 Datasets

* **Hugging Face** (API searches: "australian open", "roland garros", "grand slam tennis", "tennis serve", "tennis 2025", "tennis", "ausopen", "slam").
  * No AO or RG 2025–26 statistics dataset [observed].
  * `Aneeshers/tennis-sackmann-archive` mirrors Sackmann's Slam point-by-point with the held years only (AO and RG 2011–21; USO 2011–24; Wimbledon 2011–19 and 2021–24) [observed, tree].
  * `mvpeav/tennis-predictions`, `Neuromediator/tennis-dashboard-data` and `fulgence10/tennis-data` are model outputs or features [observed, trees].
* **GitHub code search:**
  * `"prod-scores-api.ausopen.com/match-centre"` (3 hits, all `LHBUSA/tennis` code and docs, no data dump);
  * `"rolandgarros.com/api"` (26: ticket bots, `lfavole/rolandgarros-scores`, `glad94`);
  * `"serviceStatistics" rolandgarros` (0);
  * `"averageFirstServe"` (Matchstat caches, above).
  * No published AO 2025 or RG 2025–26 statistics found [observed].
* **Kaggle** (search only): only the known AO 2020–24 / RG 2019–24 Hawk-Eye serve set (the hawkilol-derived paper) [search excerpt].
* **FFT open data:** data.gouv.fr has 4 "tennis" datasets (court and club lists) and none for "roland-garros" or "tennis match" [observed].
* **Tennis Australia Game Insight Group releases:** only the known 2018 "From AO to AI" and 2019 Monash sets (AO 2017–18). The 2023 "AO Data Slam" has no public copy (earlier pass).
* **Press-centre stat sheets:** no public archive of Slam or tour match-statistics PDFs with average speeds found [search excerpts]. AO 2025 "by the numbers" is tournament-level.

### 2.9 Held data re-read (local)

* **SofaScore:** 3,362 held `statistics.json` files; 42 distinct statistic keys, none about speed [observed, local].
* **WTA API:** 1,758 held `stats` / `advanced-stats` files (AO 2025, RG 2025–26, Wimbledon 2025, USO 2025, a WTA 1000 2025); 100 distinct keys, none about speed [observed, local].
* **SirGenkii fork** (`data/dump/points/sirgenkii_infotennis/`):
  * **AO 2025 (tournament 580):** `atp_rally_analysis` holds 14 men's R1 matches: MS101, 102, 104, 105, 107, 108, 109, 112, 116, 117, 120, 121, 124, 125.
    * Serve speed (km/h) is on 98–100% of points, with `serve` 1/2.
    * Example: MS101 Sinner, first serves in 194.1 km/h (n = 79).
      * *Correction, 7 Oct 2026 (serve-speed acquisition):* that figure grouped first-serve points by `player_id`, the player who ended the point, not the server. It is the first-serve points Jarry ended. The fork's points are right: all 199 equal the AO's own MatchBeats file point for point. By server, Sinner's first serves in average 189.8 km/h (n = 58) and Jarry's 196.1 (n = 71) ([study](../../../../docs/studies/serve_speed_acquisition/README.md)).
    * MS101 is the only overlap with the Wayback set, and its capture predates play, so **all 14 matches add speed**.
  * **`atp_key_stats`** has `max_speed`, `serve1_avg_speed` and `serve2_avg_speed`, but no rows for 580 [observed, local].
  * The Hugging Face 2021–24 copy (`infosys_deep/2024_data.jsonl.gz`, 12,502 records) has no Slam tournament ids (580, 520, 540, 560) [observed, local].
* **Sackmann Slam archive** (`data/dump/points/sackmann_archive/slam_pointbypoint/`) [observed, local]:
  * **RG 2018 and RG 2019:** `Speed_KMH` blank, **`Speed_MPH` filled** (RG 2018 MS 70.8% of points, WS 62.9%; median 100 mph), and `ServeNumber` filled (1/2). Matches with speed: 100 of 127 MS and 91 of 126 WS in 2018. **RG 2018 first-serve speed is recoverable from held data.**
  * **2012 and 2013 (all four Slams), AO 2014:** `Speed_KMH` on 82–96% of points (median about 157–165 km/h, both serves mixed).
    * No `ServeNumber` column in 2012–13, and it is blank in AO 2014.
    * `P1/P2FirstSrvIn` and `SecondSrvIn` are blank.
    * `History` does not encode the serve number (cross-tabulated against the 2011 flags: its second digit is 5 on double faults and 1–4 otherwise, for both serves).
    * So first serves cannot be identified directly [inference: only a mixture model on speed could split them].
  * **Wimbledon 2016:** the women's points file is absent; men's speed is on 47.5% of points.
  * **US Open 2019 and 2020 main-draw singles:** speed on 157 of 251 and 129 of 248 matches (54–59% and 47% of points). 2021–24: all.

## 3. Courts and qualifying: was speed measured? (gaps 3–4)

"Has speed" = at least 10% of the match's points carry a speed > 0.

### 3.1 Wimbledon (IBM feed tables, held) [observed, local]

Main-draw singles, matches with speed / matches:

| Court | 2019 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| Centre Court | 32/32 | 32/32 | 33/33 | 36/36 | 32/32 | 33/33 | 34/34 |
| No.1 Court | 27/27 | 27/27 | 30/30 | 31/31 | 32/32 | 30/30 | 28/28 |
| No.2 Court | 22/22 | 21/21 | 25/25 | 20/20 | 21/21 | 24/24 | 25/25 |
| No.3 Court | 23/23 | 20/21 | 17/17 | 17/17 | 16/16 | 18/18 | 23/23 |
| Court 12 | 22/22 | 17/17 | 18/18 | 14/14 | 15/15 | 18/18 | 17/17 |
| Court 18 | 20/20 | 16/16 | 18/18 | 16/16 | 16/16 | 18/18 | 19/19 |
| Courts 4–11, 14–17 (12 courts) | 0/108 | 0/119 | 0/111 | 1/120 | 0/120 | 113/113 | 108/108 |
| Qualifying (QS + RS) | 0/224 | 0/224 | 0/223 | 0/224 | 0/224 | 223/224 | 224/224 |

* **Official statements.**
  * Hawk-Eye "for the first time operating across all six Show Courts" [search excerpt of wimbledon.com, "A day in the life: Hawk-Eye", 7 Jul 2015].
  * From 2025, "All 18 match courts will be installed with automated electronic line calling" [observed via summariser, Sky Sports, 9 Oct 2024: https://www.skysports.com/tennis/news/12110/13230764/…].
  * Qualifying at Roehampton had no ELC before 2025 (earlier pass).
* **Verdict.** Before 2025, speed was measured only on the six show courts. The other 12 courts and qualifying were never measured, so no source can fill them [inference, strong].

### 3.2 Roland-Garros (hawkilol Court Vision copy, held) [observed, local]

Singles, matches with speed / matches in the copy:

| Court | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|
| Chatrier | 44/44 | 57/57 | 50/50 | 50/50 | 49/49 | 50/50 |
| Lenglen | 39/39 | 28/28 | 35/35 | 36/36 | 37/37 | 43/43 |
| Simonne-Mathieu | – | 4/4 | 28/28 | 28/28 | 28/28 | 18/18 |
| Courts 6, 7, 13, 14 | – | 4/4 | 10/10 | 64/64 | – | 15/15 (Court 7) |
| Courts 4, 5, 8, 9, 10, 11, 12 | – | – | – | 0/47 | – | – |
| Total in the copy | 83 | 93 | 123 | 225 | 114 | 126 |

* **Agreement with RG's own API.** For 2022, Court 9 SM033 is `null` and Court 13 SM041 has a max speed (§2.2) [observed].
* **2023–24:** the copy holds only show courts (plus Court 7 in 2024), so the outer courts are not determinable from it.
* **Verdict.**
  * RG 2022's outer Courts 4, 5 and 8–12 had no measurement [inference, strong].
  * For 2023–24, Courts 6, 13 and 14 probably had speed, as in 2022 [inference]. The only copies would be encrypted Infosys files; the Wayback holds 426 RG 2024 MatchBeats captures (earlier pass).
  * RG 2014–2021 in the Sackmann files: 171–195 of about 254 singles matches have speed (RG 2018 and 2019 in mph).
* **Qualifying:** not determined. The API `matches/QM001?event=2022` returns `match: null`. For RG 2025 qualifying, 58 matches (QM 29, QD 29) have archived Infosys data files in the Wayback Machine, all encrypted.

### 3.3 Australian Open [observed, local]

* **2020–2024 (hawkilol):** every court has speed: 250/250, 253/253, 252/252, 254/254 and 254/254 singles matches, outer Courts 3–22 included.
* **2015–2019 (Sackmann):** 175–178 of the 254-match singles draws each year (about 70%). The archive names courts only for 2011, so the courts that lacked speed are **not determined**.
  * Wikipedia's 2019 article says "Hawkeye line-calling technology was extended to be included on all courts" (uncited) [third-party report].
  * If that is true, AO 2019's missing 30% were measured but not published in the feed Sackmann copied. No other copy was found; the 2019 "manhattan" API is dead.
* **Qualifying:** AO 2026 has "1st Serve Average" (km/h) for 112 of 112 MQ and 112 of 112 WQ matches. AO 2022–25 qualifying was measured [inference: Hawk-Eye Live on all courts since 2021], but no copy survives outside the encrypted Infosys files.

### 3.4 US Open qualifying [observed, local]

* **2022–24:** every qualifying match with point data has speed: MQ 43/43, 36/36, 41/41 and WQ 39/39, 39/39, 44/44.
  * Those are the matches flagged "H" (full data: 82, 80 and 85 a year), on Courts 4, 6, 7, 11 and 12 (and 17 in 2022).
  * About 140 "S" (score-only) matches a year have no point data at all.
* **2025:** 131 "H", with no speed on Courts 9 and 14–15. **2026:** all.
* **Measurement on the other courts:** in 2021 the USTA announced Hawk-Eye Live "on all competition courts" [observed via summariser, ESPN, 24 May 2021: https://africa.espn.com/tennis/story/_/id/31503876/…]. So 2022–24 qualifying "S" matches may have been measured but not published [not determined].
* **Before 2022:** the 2019 and 2021 feeds are not served, and the 2020 qualifying was cancelled. No source.

## 4. Gap verdicts

| Gap | Verdict |
|---|---|
| AO 2025 main draw | 6 singles matches with speed already held (Wayback). 14 more men's R1 matches with per-point speed held in SirGenkii. The rest exist only in encrypted Infosys files (live MatchBeats, final checked). Eurosport/TNT not determined |
| AO 2025 qualifying | Measured [inference]; no public copy found |
| RG 2025 / RG 2026 | No plain source: RG API null; ESPN none; Tennis Majors none; archive.today none. Encrypted Infosys only: live 2025 `data.json` (with a `stats` block) and the live 2026 key-stats API; Wayback copies for 13 and 10 main-draw singles matches |
| ESPN | No speed at any tier or year; no Challengers |
| Wimbledon outside courts before 2025 | Not measured |
| RG 2022–24 outside courts | Courts 4, 5, 8–12 not measured (2022); 6, 13, 14 measured in 2022, 2023–24 unknown |
| AO before 2020 | About 70% have speed; the rest is not determined (possibly measured but unpublished in 2019) |
| Wimbledon qualifying before 2025 | Not measured |
| USO qualifying before 2022 | No source. 2022–24 "S" matches unpublished |
| AO qualifying | Measured (2026 observed). No public copy for 2022–25; whether Infosys files cover qualifying is unverified |
| RG qualifying | Not determined |

## 5. Terms (as read)

* **ESPN / Disney:** see §2.1. Automated extraction, dataset compilation, AI/ML use and commercial use are barred.
* **Roland-Garros:** automated extraction prohibited (quoted in §2.2). robots.txt open.
* **Tennis Australia, USTA, AELTC:** as quoted in [access routes](../../../../docs/research/granular-data-leads/access-routes.md).
* **Infosys files:** encrypted. Decryption is the owner's decision.
* **TNT Sports:** robots.txt allows `*` on match pages. Terms not read.
* **Matchstat:** paid (RapidAPI). Terms not read.

## 6. Dead ends

* **ESPN:** summary endpoint 400 (single-id lookup); web match pages 404; core statistics 404 everywhere; `seasons/{Y}/events` 404.
* **rolandgarros.com:** speeds null 2023–26; garbled averages 2019–22; `QM001?event=2022` → `match: null`.
* **ATP Stats Centre:** no Slam key stats or rally files today. The Monte-Carlo 2025 lower-case static path is 403, because S3 keys are case-sensitive and the upper-case Paris path answers 200 [inference].
* **AO API in the Wayback:** results, players and stats files hold no per-match speed. The Infosys AO host has nothing for 2025.
* **Wimbledon 2025 ELC article:** `www` redirects to `/en_GB/news`, and the Wayback captures are a 1–2 KB app shell (not read further).
* **ausopen.com/node/246218,** whose search excerpt claimed "1st serve average" values: 404 now. Its only capture (2024) is a 301.
* **TNT lazy chunks** (5): theme files only.
* **archive.today:** no captures.
* **Hugging Face, Kaggle, GitHub, data.gouv.fr:** no copies.

## 7. Probe log

All on 7 Oct 2026, UTC. Client: curl_cffi with a Chrome profile, from the `tennis` environment; no redirects followed. Requests per host:
* sports.core.api.espn.com 22; rolandgarros.com 21; site.api.espn.com 14; web.archive.org 14; itp-atp-sls 14; huggingface.co 12; tntsports.co.uk 10; itp-rg-sls 5; archive.ph 4; data.gouv.fr 3; www.espn.com 2; wimbledon.com 2; itp-ao-sls 2; site.web.api.espn.com 1. Total 126.
* Not in the table: about 20 WebSearch calls; 9 WebFetch calls (ausopen.com/node/246218 404; tennismajors.com; rapidapi.com; wimbledon.com ×2, unreadable; skysports.com; en.wikipedia.org; africa.espn.com; disneytermsofuse.com); and about 15 read-only `gh api` calls, 14:15–14:52 UTC.

| # | UTC | URL | Status | Bytes | Note |
|---|---|---|---|---|---|
| 1 | 14:01:55 | https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard?dates=20250120 | 200 | 1835599 | ESPN ATP scoreboard AO2025 day |
| 2 | 14:02:20 | https://site.api.espn.com/apis/site/v2/sports/tennis/atp/summary?event=153116 | 400 | 205 | ESPN summary AO2025 MS final |
| 3 | 14:02:28 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events/154-2025/competitions/153116?lang=en&region=us | 200 | 3663 | ESPN core competition AO2025 MS final |
| 4 | 14:02:37 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events/154-2025/competitions/153116/competitors/3623?lang=en&region=us | 200 | 533 | ESPN core competitor Sinner AO2025 final |
| 5 | 14:02:40 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events/154-2025/competitions/153116/competitors/3623/statistics?lang=en&region=us | 404 | 108 | ESPN core competitor statistics guess |
| 6 | 14:02:53 | https://www.espn.com/tennis/match/_/gameId/153116 | 404 | 87082 | ESPN web match page AO2025 MS final |
| 7 | 14:03:16 | https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard | 200 | 821813 | ESPN ATP scoreboard current (Oct 2026) |
| 8 | 14:03:32 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events/959-2026/competitions/186254?lang=en&region=us | 200 | 3457 | ESPN core competition China Open 2026 Q1 |
| 9 | 14:03:40 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events/959-2026/competitions/183467/competitors/296/statistics?lang=en&region=us | 404 | 107 | ESPN core competitor statistics China Open 2026 SF Djokovic (ATP 500) |
| 10 | 14:03:51 | https://site.web.api.espn.com/apis/site/v2/sports/tennis/atp/summary?event=154-2025&competition=153116&region=us&lang=en | 400 | 228 | ESPN site.web summary with event+competition |
| 11 | 14:04:05 | https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard?dates=20250907 | 200 | 2137314 | ESPN ATP scoreboard USO2025 final day |
| 12 | 14:04:12 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events/189-2025/competitions/161412/competitors/3782/statistics?lang=en&region=us | 404 | 108 | ESPN core competitor statistics USO2025 MS final Alcaraz |
| 13 | 14:04:15 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events/189-2025/competitions/161412?lang=en&region=us | 200 | 3658 | ESPN core competition USO2025 MS final |
| 14 | 14:04:25 | https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard?dates=20190714 | 200 | 1337752 | ESPN ATP scoreboard Wimbledon 2019 final day |
| 15 | 14:04:43 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events/188-2019/competitions/99232/competitors/296/statistics?lang=en&region=us | 404 | 106 | ESPN core competitor statistics Wimbledon 2019 MS final Djokovic |
| 16 | 14:04:46 | https://sports.core.api.espn.com/v2/sports/tennis/athletes/3623?lang=en&region=us | 200 | 4011 | ESPN core athlete Sinner (look for statistics link) |
| 17 | 14:04:51 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/seasons/2026/types/2/athletes/3623/statistics?lang=en&region=us | 200 | 1508 | ESPN core athlete season statistics Sinner 2026 |
| 18 | 14:05:09 | https://sports.core.api.espn.com/v2/sports/tennis/leagues?lang=en&region=us&limit=50 | 200 | 243 | ESPN core tennis leagues list |
| 19 | 14:05:18 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/seasons/2025/events?lang=en&region=us&limit=300 | 404 | 52 | ESPN core ATP 2025 events list |
| 20 | 14:05:25 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events?lang=en&region=us&dates=2025&limit=300 | 200 | 6516 | ESPN core ATP events dates=2025 |
| 21 | 14:05:50 | https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard?dates=20250608 | 200 | 2274047 | ESPN atp scoreboard 20250608 |
| 22 | 14:05:50 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events/172-2025/competitions/156766/competitors/3782/statistics?lang=en&region=us | 404 | 108 | ESPN core competitor statistics RG 2025 MS final |
| 23 | 14:05:53 | https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard?dates=20260607 | 200 | 2098085 | ESPN atp scoreboard 20260607 |
| 24 | 14:05:53 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events/172-2026/competitions/175668/competitors/2375/statistics?lang=en&region=us | 404 | 108 | ESPN core competitor statistics RG 2026 MS final |
| 25 | 14:05:56 | https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard?dates=20250503 | 200 | 914715 | ESPN wta scoreboard 20250503 |
| 26 | 14:05:56 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/wta/events/413-2025/competitions/155872/competitors/3626/statistics?lang=en&region=us | 404 | 108 | ESPN core competitor statistics WTA 1000 Madrid 2025 final |
| 27 | 14:05:59 | https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard?dates=20190224 | 200 | 420751 | ESPN atp scoreboard 20190224 |
| 28 | 14:05:59 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events/442-2019/competitions/97666/competitors/1354/statistics?lang=en&region=us | 404 | 107 | ESPN core competitor statistics ATP 250 Hungarian Open 2019 final |
| 29 | 14:06:43 | https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard?dates=20230703 | 200 | 1694075 | ESPN atp scoreboard 20230703 |
| 30 | 14:06:43 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events/188-2023/competitions/135282/competitors/1989/statistics?lang=en&region=us | 404 | 108 | ESPN core competitor statistics Wimbledon 2023 R1, Court 7 |
| 31 | 14:06:46 | https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard | 200 | 788147 | ESPN wta scoreboard current |
| 32 | 14:06:49 | https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard?dates=20160710 | 200 | 1934929 | ESPN atp scoreboard 20160710 |
| 33 | 14:06:49 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events/384-2016/competitions/74133/competitors/310/statistics?lang=en&region=us | 404 | 106 | ESPN core competitor statistics, ATP Shenzhen Open 2016 final (ATP 250) |
| 34 | 14:07:03 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/wta/events/959-2026/competitions/184355/competitors/6048/statistics?lang=en&region=us | 404 | 108 | ESPN core competitor statistics WTA 1000 China Open 2026 R4 |
| 35 | 14:07:25 | https://www.espn.com/tennis/scoreboard/tournament/_/eventId/154-2025/competitionType/1 | 200 | 434873 | ESPN web scoreboard AO2025 men's singles |
| 36 | 14:07:46 | https://www.rolandgarros.com/robots.txt | 200 | 77 | RG robots.txt |
| 37 | 14:07:52 | https://www.rolandgarros.com/en-us/matches/2025/SM001 | 200 | 578086 | RG 2025 match page SM001 (final) |
| 38 | 14:08:57 | https://www.rolandgarros.com/en-us/matches/2026/SM001 | 200 | 577826 | RG 2026 match page SM001 |
| 39 | 14:09:00 | https://www.rolandgarros.com/en-us/matches/2024/SM001 | 200 | 577760 | RG 2024 match page SM001 |
| 40 | 14:09:23 | https://www.rolandgarros.com/_nuxt/54f2597.js | 200 | 2922 | RG nuxt bundle |
| 41 | 14:09:26 | https://www.rolandgarros.com/_nuxt/d549552.js | 200 | 286312 | RG nuxt bundle |
| 42 | 14:09:29 | https://www.rolandgarros.com/_nuxt/607f7f0.js | 200 | 51749 | RG nuxt bundle |
| 43 | 14:09:32 | https://www.rolandgarros.com/_nuxt/cb7d3ce.js | 200 | 19491 | RG nuxt bundle |
| 44 | 14:09:36 | https://www.rolandgarros.com/_nuxt/63e1e5e.js | 200 | 33647 | RG nuxt bundle |
| 45 | 14:09:39 | https://www.rolandgarros.com/_nuxt/d7ffc9b.js | 200 | 238759 | RG nuxt bundle |
| 46 | 14:09:42 | https://www.rolandgarros.com/_nuxt/3551236.js | 200 | 247111 | RG nuxt bundle |
| 47 | 14:09:45 | https://www.rolandgarros.com/_nuxt/5ce9bcc.js | 200 | 721050 | RG nuxt bundle |
| 48 | 14:10:26 | https://www.rolandgarros.com/api/en-us/matches/SM001?event=2025 | 200 | 12320 | RG API single match 2025 SM001 |
| 49 | 14:10:39 | https://web.archive.org/cdx/search/cdx?url=rolandgarros.com/en-us/matches/2025/&matchType=prefix&output=json&fl=timestamp,original,statuscode,length&collapse=urlkey&limit=5000 | 200 | 82412 | Wayback CDX RG en-us match pages 2025 |
| 50 | 14:10:53 | https://web.archive.org/cdx/search/cdx?url=rolandgarros.com/en-us/matches/2025/S&matchType=prefix&output=json&fl=timestamp,original,statuscode,length&from=20250518&to=20250630&filter=statuscode:200&limit=5000 | 200 | 17150 | Wayback CDX RG 2025 singles match pages during tournament |
| 51 | 14:11:11 | https://web.archive.org/web/20250608212650id_/https://www.rolandgarros.com/en-us/matches/2025/SM001 | 200 | 562945 | Wayback RG 2025 SM001 capture 20250608212650 |
| 52 | 14:11:31 | https://web.archive.org/cdx/search/cdx?url=itp-rg-sls.infosys-platforms.com/&matchType=prefix&output=json&fl=timestamp,original,statuscode,mimetype,length&collapse=urlkey&limit=10000 | 200 | 1373903 | Wayback CDX all itp-rg-sls URLs |
| 53 | 14:12:10 | https://web.archive.org/web/20260603194548id_/https://itp-rg-sls.infosys-platforms.com/prod/api/stats-plus/v1/keystats/year/2026/eventId/520/matchId/SM004 | 200 | 30544 | Wayback RG 2026 keystats SM004 (keys only; not decoded) |
| 54 | 14:12:13 | https://web.archive.org/web/20250601082234id_/https://itp-rg-sls.infosys-platforms.com/static/prod/match-centre/2025/520/SM023/data.json | 200 | 231601 | Wayback RG 2025 match-centre data.json SM023 (keys only; not decoded) |
| 55 | 14:12:42 | https://www.rolandgarros.com/api/en-us/matches/SM001?event=2022 | 200 | 10014 | RG API single match 2022 SM001 |
| 56 | 14:12:45 | https://www.rolandgarros.com/api/en-us/matches/SM001?event=2019 | 200 | 11257 | RG API single match 2019 SM001 |
| 57 | 14:13:09 | https://www.rolandgarros.com/api/en-us/matches/SM100?event=2025 | 200 | 8588 | RG API single match 2025 SM100 |
| 58 | 14:13:12 | https://www.rolandgarros.com/api/en-us/matches/SD100?event=2026 | 200 | 9659 | RG API single match 2026 SD100 |
| 59 | 14:13:26 | https://web.archive.org/cdx/search/cdx?url=prod-scores-api.ausopen.com/&matchType=prefix&output=json&fl=timestamp,original,statuscode,mimetype,length&collapse=urlkey&limit=20000 | 200 | 61496 | Wayback CDX all prod-scores-api.ausopen.com URLs |
| 60 | 14:13:45 | https://web.archive.org/web/20251006161733id_/https://prod-scores-api.ausopen.com/year/2025/stats | 200 | 397992 | Wayback AO scores API /year/2025/stats |
| 61 | 14:14:02 | https://web.archive.org/web/20250116222219id_/https://prod-scores-api.ausopen.com/players/214826/matches | 200 | 19895 | Wayback AO scores API /players/{id}/matches (Jan 2025) |
| 62 | 14:14:21 | https://web.archive.org/cdx/search/cdx?url=itp-ao-sls.infosys-platforms.com/&matchType=prefix&output=json&fl=timestamp,original,statuscode,mimetype,length&collapse=urlkey&limit=20000 | 200 | 29986 | Wayback CDX all itp-ao-sls URLs |
| 63 | 14:19:39 | https://www.tntsports.co.uk/robots.txt | 200 | 4076 | TNT Sports UK robots.txt |
| 64 | 14:19:57 | https://www.tntsports.co.uk/tennis/australian-open-men/2025/live-jannik-sinner-alexander-zverev_mtc1576391/live-commentary.shtml | 200 | 888904 | TNT Sports UK AO2025 MS final page |
| 65 | 14:20:19 | https://www.tntsports.co.uk/tennis/australian-open-men/2025/live-jannik-sinner-alexander-zverev_mtc1576391/live-stats.shtml | 200 | 814835 | TNT Sports UK AO2025 MS final STATS tab |
| 66 | 14:22:40 | https://www.tntsports.co.uk/layout_app_match/_next/static/chunks/0v80rdl0r8jxc.js | 200 | 483476 | TNT Next chunk (match page) |
| 67 | 14:22:43 | https://www.tntsports.co.uk/layout_app_match/_next/static/chunks/3xh8nz1l9p5xz.js | 200 | 12189 | TNT Next chunk (match page) |
| 68 | 14:26:46 | https://huggingface.co/api/datasets?search=australian%20open&limit=50&full=false | 200 | 64461 | HF dataset search australian open |
| 69 | 14:26:49 | https://huggingface.co/api/datasets?search=roland%20garros&limit=50&full=false | 200 | 2 | HF dataset search roland garros |
| 70 | 14:26:52 | https://huggingface.co/api/datasets?search=grand%20slam%20tennis&limit=50&full=false | 200 | 2 | HF dataset search grand slam tennis |
| 71 | 14:26:55 | https://huggingface.co/api/datasets?search=tennis%20serve&limit=50&full=false | 200 | 2 | HF dataset search tennis serve |
| 72 | 14:26:58 | https://huggingface.co/api/datasets?search=tennis%202025&limit=50&full=false | 200 | 2 | HF dataset search tennis 2025 |
| 73 | 14:27:08 | https://huggingface.co/api/datasets?search=tennis&limit=100&full=false&sort=lastModified | 200 | 101209 | HF dataset search tennis sorted by lastModified |
| 74 | 14:27:11 | https://huggingface.co/api/datasets?search=ausopen&limit=100&full=false&sort=lastModified | 200 | 2 | HF dataset search ausopen |
| 75 | 14:27:14 | https://huggingface.co/api/datasets?search=slam&limit=100&full=false&sort=lastModified | 200 | 104754 | HF dataset search slam |
| 76 | 14:27:31 | https://huggingface.co/api/datasets/mvpeav/tennis-predictions/tree/main?recursive=true&expand=false | 200 | 23951 | HF tree mvpeav/tennis-predictions |
| 77 | 14:27:34 | https://huggingface.co/api/datasets/Aneeshers/tennis-sackmann-archive/tree/main?recursive=true&expand=false | 200 | 60176 | HF tree Aneeshers/tennis-sackmann-archive |
| 78 | 14:27:37 | https://huggingface.co/api/datasets/Neuromediator/tennis-dashboard-data/tree/main?recursive=true&expand=false | 200 | 24477 | HF tree Neuromediator/tennis-dashboard-data |
| 79 | 14:27:41 | https://huggingface.co/api/datasets/fulgence10/tennis-data/tree/main?recursive=true&expand=false | 200 | 1693 | HF tree fulgence10/tennis-data |
| 80 | 14:28:51 | https://www.wimbledon.com/amp/en_GB/news/articles/2025-07-03/the_precision_operation_introducing_electronic_line_calling.html | 301 | 0 | Wimbledon AMP article on ELC 2025; redirect to /en_GB/news (not followed) |
| 81 | 14:29:02 | https://www.wimbledon.com/en_GB/news/articles/2025-07-03/the_precision_operation_introducing_electronic_line_calling.html | 302 | 0 | Wimbledon article on ELC 2025; redirect to /en_GB/news (not followed) |
| 82 | 14:29:13 | https://web.archive.org/web/2025id_/https://www.wimbledon.com/en_GB/news/articles/2025-07-03/the_precision_operation_introducing_electronic_line_calling.html | 302 | 0 | Wayback nearest-capture redirect (not followed) |
| 83 | 14:29:22 | https://web.archive.org/cdx/search/cdx?url=wimbledon.com/en_GB/news/articles/2025-07-03/the_precision_operation_introducing_electronic_line_calling.html&output=json&fl=timestamp,original,statuscode,length | 200 | 3163 | Wayback CDX Wimbledon ELC article |
| 84 | 14:37:38 | https://www.rolandgarros.com/api/en-us/matches/SM033?event=2022 | 200 | 11115 | RG API 2022 SM033 (Court 9 speed test) |
| 85 | 14:37:41 | https://www.rolandgarros.com/api/en-us/matches/SM041?event=2022 | 200 | 10043 | RG API 2022 SM041 (Court 13 speed test) |
| 86 | 14:38:01 | https://www.rolandgarros.com/api/en-us/matches/SM001?event=2023 | 200 | 9810 | RG API 2023 SM001 |
| 87 | 14:39:47 | https://www.rolandgarros.com/api/en-us/matches/QM001?event=2022 | 200 | 2333 | RG API 2022 QM001 (qualifying test; match null) |
| 88 | 14:41:00 | https://www.data.gouv.fr/api/1/datasets/?q=roland-garros&page_size=30 | 200 | 94 | data.gouv.fr search roland-garros (0) |
| 89 | 14:41:03 | https://www.data.gouv.fr/api/1/datasets/?q=tennis%20match&page_size=30 | 200 | 94 | data.gouv.fr search tennis match (0) |
| 90 | 14:41:11 | https://www.data.gouv.fr/api/1/datasets/?q=tennis&page_size=40 | 200 | 16794 | data.gouv.fr search tennis (4) |
| 91 | 14:41:23 | https://archive.ph/timemap/https://ausopen.com/match/2025-jannik-sinner-vs-alexander-zverev-ms701 | 404 | 75 | archive.today timemap AO2025 MS701 page |
| 92 | 14:41:35 | https://archive.ph/https://ausopen.com/match/2025* | 200 | 3329 | archive.today prefix listing ausopen.com/match/2025* (No results) |
| 93 | 14:41:55 | https://archive.ph/prod-scores-api.ausopen.com | 200 | 3387 | archive.today host listing (No results) |
| 94 | 14:41:59 | https://archive.ph/https://www.rolandgarros.com/en-us/matches/2025* | 200 | 3468 | archive.today prefix listing RG 2025 (No results) |
| 95 | 14:44:14 | https://itp-atp-sls.infosys-platforms.com/static/prod/stats-plus/2025/580/ms001/keystats.json | 403 | 111 | ATP Infosys key stats AO 2025 (lower-case id) |
| 96 | 14:44:18 | https://itp-atp-sls.infosys-platforms.com/static/prod/stats-plus/2025/520/ms001/keystats.json | 403 | 263 | ATP Infosys key stats RG 2025 (lower-case id) |
| 97 | 14:44:21 | https://itp-atp-sls.infosys-platforms.com/static/prod/stats-plus/2026/520/ms001/keystats.json | 403 | 111 | ATP Infosys key stats RG 2026 (lower-case id) |
| 98 | 14:44:25 | https://itp-atp-sls.infosys-platforms.com/static/prod/rally-analysis/2025/520/ms001/data.json | 403 | 243 | ATP Infosys rally analysis RG 2025 (lower-case id) |
| 99 | 14:44:39 | https://itp-atp-sls.infosys-platforms.com/static/prod/stats-plus/2025/410/ms001/keystats.json | 403 | 243 | ATP Infosys key stats Monte-Carlo 2025 (lower-case id; failed calibration) |
| 100 | 14:45:13 | https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard?dates=20250209 | 200 | 583084 | ESPN atp scoreboard 20250209 |
| 101 | 14:45:13 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/events/836-2025/competitions/153667/competitors/2989/statistics?lang=en&region=us | 404 | 108 | ESPN core competitor statistics ATP 500 Dallas 2025 final |
| 102 | 14:45:16 | https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard?dates=20250911 | 200 | 395178 | ESPN atp scoreboard 20250911 (Challenger week: Shanghai only) |
| 103 | 14:46:22 | https://web.archive.org/cdx/search/cdx?url=ausopen.com/node/246218&output=json&fl=timestamp,original,statuscode,length | 200 | 117 | Wayback CDX ausopen.com/node/246218 |
| 104 | 14:47:21 | https://www.tntsports.co.uk/layout_app_match/_next/static/chunks/0-74k-u_6qlg2.js | 200 | 638 | TNT lazy chunk |
| 105 | 14:47:25 | https://www.tntsports.co.uk/layout_app_match/_next/static/chunks/1b0wx0lrs8-z1.js | 200 | 646 | TNT lazy chunk |
| 106 | 14:47:28 | https://www.tntsports.co.uk/layout_app_match/_next/static/chunks/39v2-eovkqoi6.js | 200 | 666 | TNT lazy chunk |
| 107 | 14:47:31 | https://www.tntsports.co.uk/layout_app_match/_next/static/chunks/40e71ham3y3ro.js | 200 | 666 | TNT lazy chunk |
| 108 | 14:47:35 | https://www.tntsports.co.uk/layout_app_match/_next/static/chunks/41pk9003estnj.js | 200 | 648 | TNT lazy chunk |
| 109 | 14:48:12 | https://web.archive.org/web/20250602042710id_/https://prod-scores-api.ausopen.com/year/2025/period/MD/day/10/results | 200 | 363160 | Wayback AO 2025 MD day 10 results |
| 110 | 14:50:09 | https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/seasons/2026/athletes/3623/eventlog?lang=en&region=us | 200 | 10843 | ESPN core athlete event log Sinner 2026 |
| 111 | 14:53:54 | https://itp-atp-sls.infosys-platforms.com/static/prod/stats-plus/2025/580/MS001/keystats.json | 403 | 263 | ATP Infosys key stats AO 2025 (upper-case id) |
| 112 | 14:53:58 | https://itp-atp-sls.infosys-platforms.com/static/prod/stats-plus/2025/520/MS001/keystats.json | 403 | 263 | ATP Infosys key stats RG 2025 (upper-case id) |
| 113 | 14:54:02 | https://itp-atp-sls.infosys-platforms.com/static/prod/stats-plus/2026/520/MS001/keystats.json | 403 | 263 | ATP Infosys key stats RG 2026 (upper-case id) |
| 114 | 14:54:17 | https://itp-atp-sls.infosys-platforms.com/static/prod/stats-plus/2025/352/MS001/keystats.json | 200 | 31660 | Calibration: Paris 2025 final; encrypted envelope (keys only; not decoded) |
| 115 | 14:54:21 | https://itp-atp-sls.infosys-platforms.com/prod/api/stats-plus/v1/keystats/year/2025/eventId/580/matchId/MS001 | 404 | 15 | API key stats AO 2025 final: "Match Not Found" |
| 116 | 14:54:40 | https://itp-atp-sls.infosys-platforms.com/prod/api/stats-plus/v1/keystats/year/2025/eventId/520/matchId/MS001 | 404 | 15 | API key stats RG 2025 final: "Match Not Found" |
| 117 | 14:54:44 | https://itp-atp-sls.infosys-platforms.com/prod/api/stats-plus/v1/keystats/year/2026/eventId/520/matchId/MS001 | 404 | 15 | API key stats RG 2026 final: "Match Not Found" |
| 118 | 14:54:47 | https://itp-atp-sls.infosys-platforms.com/prod/api/rally-analysis/year/2025/eventId/580/matchId/MS101 | 404 | 15 | API rally analysis AO 2025 MS101 (held by SirGenkii): "Match Not Found" |
| 119 | 14:55:00 | https://itp-atp-sls.infosys-platforms.com/static/prod/rally-analysis/2025/580/ms101/data.json | 403 | 111 | Static rally analysis AO 2025 ms101, as SirGenkii used |
| 120 | 15:01:55 | https://itp-rg-sls.infosys-platforms.com/static/prod/match-centre/2025/520/SM100/data.json | 200 | 149833 | RG Infosys live data.json 2025 SM100 (existence and keys only; not decoded) |
| 121 | 15:01:59 | https://itp-rg-sls.infosys-platforms.com/static/prod/match-centre/2026/520/SD100/data.json | 403 | 243 | RG Infosys live data.json 2026 SD100 (no object) |
| 122 | 15:02:18 | https://itp-rg-sls.infosys-platforms.com/static/prod/match-centre/2025/520/SM100/data.json | 200 | 149833 | Repeat, saved, to read the plain `data` keys (all null; not decoded) |
| 123 | 15:02:21 | https://itp-rg-sls.infosys-platforms.com/static/prod/match-centre/2026/520/SM001/data.json | 403 | 263 | RG Infosys live data.json 2026 SM001 (no object) |
| 124 | 15:02:35 | https://itp-rg-sls.infosys-platforms.com/prod/api/stats-plus/v1/keystats/year/2026/eventId/520/matchId/SM001 | 200 | 90468 | RG Infosys live key-stats API 2026 SM001 (keys only; not decoded) |
| 125 | 15:02:53 | https://itp-ao-sls.infosys-platforms.com/static/prod/match-centre/2025/580/MS701/data.json | 403 | 263 | AO Infosys live match-centre path 2025 MS701 (no object) |
| 126 | 15:02:57 | https://itp-ao-sls.infosys-platforms.com/static/prod/match-beats/2025/580/MS701/data.json | 200 | 109796 | AO Infosys live MatchBeats 2025 MS701 (keys only; not decoded) |
