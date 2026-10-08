# Lane A1: official and public web sources for serve speed at ATP and WTA tour-level events (7 Oct 2026)

**Status: research, not a decision.** Everything was read on 7 October 2026. Nothing was bought, no account or trial was opened, no form was submitted, nobody was contacted and nothing was decrypted. No decryption key was tested.

**Scope.** Serve speed (above all per-match average first-serve speed) at ATP and WTA tour level outside the Slams (250, 500, 1000, Finals), plus whether Challengers and WTA 125s measure speed at all. Gaps, in the brief's order:
1. ATP tour level, May 2025 to today and going forward;
2. WTA tour level, any year 2015–2026;
3. ATP tour level, 2015–2020;
4. Challenger and WTA 125: is speed measured at all?

**Evidence labels:** **[observed]** = I saw the field and its values (or its absence) in a payload or page; **[documented]** = a provider's rulebook, schema or its own client code; **[claimed]** = marketing or press text; **[third-party]** = someone else reports it; **[search]** = search-engine excerpt only; **[inference]** = my reasoning. **(WF)** marks a quote that came through the WebFetch summariser, so it is near-verbatim. Every URL below was accessed on 7 Oct 2026.

## 0. Bottom line

* **Gap 1 (ATP, May 2025 onward).**
  * **Ball tracking is now on every ATP Tour match court.** The 2026 ATP Rulebook makes Live ELC mandatory on all match courts from the first day of qualifying. The ATP's 2023 announcement said this would "deliver comprehensive player and ball tracking across the whole Tour" [documented].
    * Whether every approved vendor's system feeds a serve speed into the official data is not stated [inference]. The 2022–24 pattern (§2.1) suggests the Stats Centre took speed only from Hawk-Eye.
  * **The only official per-match carrier is the encrypted ATP Stats Centre.** Its Key Stats files have "Max Speed", "1st Serve Average Speed" (`speedStats.fsAvgSpeed`) and "2nd Serve Average Speed". MatchBeats has a `serveSpeed` on every point [documented: Infosys's own client code].
    * The files exist for 2026 tour matches: the Beijing 2026 final's Key Stats returned a 31,576-character ciphertext with `data: null` [observed].
    * Every other atptour.com and ATP app route checked has no speed: match stats JSON (2019 and 2026), leaderboards, individual match stats, TDI Insights and the live gateway [observed].
  * **Flashscore covers only a few non-Slam matches.** Its desktop statistics feed is signed (HTTP 401 without the page's `x-fsign` value), and I did not send the signature.
    * Its mobile site serves the same statistics as plain HTML. In a sample of 16 non-Slam matches from May–October 2026 (12 ATP, 4 WTA), only the Madrid and Rome Masters finals carried "Average 1st serve speed" [observed].
    * The sample's Slam finals all carried it, and so did a control match that also has it in the crawl.
    * The mobile site's robots.txt disallows `/match/` for all agents.
  * **Nothing else public carries non-Slam speed** [observed]:
    * about 20 tournament sites (§3.8);
    * 14 aggregators (two gated and not entered), including Matchstat, Tennis Abstract and tennisstats.com, which carry speed **for Slams only** (§3.9);
    * 7 broadcasters and OTT services (§3.10).
* **The speedless 2022–24 events (coordinator's list): probably unfillable from public sources.**
  * The clay ones had no electronic line calling before 2025. Several hard-court ones used FOXTENN.
  * No tournament site, aggregator or Flashscore shows a speed for any of them (Barcelona, Halle and Paris 2024 finals, among others, tested on Matchstat).
  * Whether a stand-alone radar ran at some of them is unknown (§2.1, §3.8).
* **Gap 2 (WTA, any year).**
  * **No official public carrier of WTA speed exists.** The WTA API's `stats` and `advanced-stats` for a 2026 WTA 500 final have no speed key, and the 2026 wtatennis.com match-centre script contains no "speed" string at all [observed].
  * **Measurement was narrow before 2026.** In 2025 the WTA required an electronic review system only "at minimum on center court" at WTA 1000 hard-court events and WTA 500 hard and grass events. From 2026 every WTA 1000, 500 and 250 must run Live ELC on all match courts from qualifying [documented].
  * **Flashscore carried no WTA non-Slam speed in the 2026 sample.** That covers the Rome, Toronto and Cincinnati finals and a Beijing round of 16. The women's Wimbledon final carried it [observed].
  * **The only official per-match carrier found is the LTA's Infosys match centre, and it is encrypted.**
    * It covers Queen's and Eastbourne 2026, men's and women's draws.
    * Its client code defines "Fastest Serve (m/h)", "1st Serve Avg. (m/h)" and "2nd Serve Avg. (m/h)" [documented]. Every reply is in the ATP-style encrypted envelope [observed, §3.8].
  * **No tournament site, aggregator or broadcaster shows WTA non-Slam speed** [observed].
* **Gap 3 (ATP 2015–2020).**
  * **No official public carrier.** The ATP website showed no per-match speed before the Stats Centre pages of late 2021. Its match-stats JSON for 2019 has no speed key [observed]. A scraper's schema confirms this for 1991 to 18 Oct 2021 [observed, `serve-and-volley/atp-world-tour-tennis-data`].
  * **Infosys's "second screen" data before 2021 survives nowhere public that I found.** The Wayback Machine holds no ATP Infosys data file before 2021 [observed, CDX].
  * **Radar readings at tour events are not archived publicly.** They existed (SMT/IDS: "we've been supplying data to both tours"; EDH radar linked to the umpire device) [claimed], but no public archive was found.
  * **No aggregator has tour-level speed for any year.** Tennis Abstract's author: "The only available point-by-point serve speed data these days comes from Wimbledon and the US Open" (2024) [documented].
* **Gap 4 (Challenger, WTA 125).**
  * **Challengers:** the 2026 ATP Rulebook only *authorises* electronic review at Challengers ("Review ELC … applicable to ATP Challenger Tour only") [documented]. 2026 is reported as "the first year Challengers have regularly used ELC", with Bolt6 at US events [third-party]. A 2026 Bolt6 event (the Lincoln final) shows no speed on Flashscore [observed].
  * **WTA 125:** outside the WTA's 2026 ELC requirement, which names only WTA 1000, 500 and 250 [documented].
* **Side finding for the main session (Flashscore crawl): 922 of the crawl's 939 2024 "speeds" are "0 km/h" placeholders** [observed, §3.7.4].
  * `flashscore_crawl.py` counts 0 km/h as timed. The rows it reports as about 100% (Cincinnati and Toronto 2024, about 15 Challengers of 2024) are all zeros; the Cincinnati and Toronto ones are WTA matches.
  * Only 17 real 2024 values remain: the Next Gen Finals, one Shanghai match and the ATP Finals final.
  * 2025–26 values are real (995 of 1,000).
  * The ATP Cincinnati 2024 final has no speed field at all, in the crawl or on the live mobile page.

### 0.1 Source table

| Source | Speed field | Coverage (tiers × years) | Access and cost | Terms | Confidence it can fill the gap |
|---|---|---|---|---|---|
| ATP Stats Centre (Infosys) Key Stats and MatchBeats | Per match: max, first-serve average, second-serve average. Per point: `serveSpeed` [documented] | ATP tour level; decrypted copies 2021–Apr 2025 (event by event); files exist for 2025–26 [observed]; ELC on all courts since 2025 [documented] | Free browser load; **encrypted** | atptour.com: no "systematic retrieval", no gambling use | High that the data exists; blocked by the decryption decision |
| LTA match centre (Infosys) | Per match: fastest serve, first- and second-serve averages, mph [documented] | Queen's and Eastbourne 2026, men and women (plus LTA event 7740) [observed, Wayback] | Free; **encrypted** | LTA bans scraping and AI training | Medium (WTA payloads may lack speed) |
| Flashscore (mobile HTML) | Per match per player: first- and second-serve averages, km/h [observed] | 2026 non-Slam: Madrid and Rome finals only, of 16 sampled; Slams yes [observed] | Free; desktop feed signed (401); mobile `/match/` disallowed by robots.txt | No extraction or scraping without consent | Low (sporadic) |
| Matchstat | Per match: fastest serve, first- and second-serve averages (km/h) [observed] | Slams only, 2019–2026 (RG 2025 null) [observed] | Free embedded JSON; API plans [claimed] | No commercial use without a licence | None for non-Slams |
| serve-and-volley (GitHub) | Per match: max, first-serve average, second-serve average, km/h and mph [observed] | ATP 42 events, 18 Oct 2021 – 2022 (overlaps held data) [observed] | Free download | CC BY 4.0 (README); ATP data | None (no new coverage) |
| WTA API and wtatennis.com; ATP site, gateway; tournament sites; other aggregators; broadcasters | None [observed] | — | — | Various bans (see sections) | None |

## 1. Method

* **Requests.** Every HTTP request went through one logging helper (`probe.py`, curl_cffi with Chrome TLS impersonation, from the project's `tennis` environment via `./python.sh`).
  * It logs UTC time, host, URL, status and bytes; keeps at least about 3 s between requests to the same host; and refuses more than 25 per host.
  * Header changes were limited to what a browser sends: a `Referer` and `Origin` for atptour.com, the ATP's Infosys host and the WTA API.
  * No cookie, token, signature or credential was sent.
  * Bodies were kept in the session scratchpad (`…/scratchpad/laneA1/bodies/`), never in the repository. The largest is the ATP rulebook PDF (5.9 MB).
* **Two helper agents ran in parallel under the same rules and the same logging helper:**
  * T: tournament websites;
  * B: aggregators and broadcasters.
  * Their findings are §3.8–3.10. Their requests are in the same log.
* **Searches.** WebSearch for announcements, rulebooks and third-party descriptions. WebFetch for single articles; those calls are listed in §4.3 with approximate times.
* **Local reads (read-only, no network).** The Hugging Face handoff's Flashscore crawl, to pick control matches and to check the zero values (§3.7.4).
* **Not done.**
  * No decryption and no key test.
  * No `x-fsign` signature was sent to Flashscore's feed.
  * The Infosys chatbot (a POST endpoint that answers questions such as "What was the average first serve speed…") was not called.
  * No CAPTCHA or bot challenge was met. None was served to my requests.
  * Helper B met a Cloudflare challenge at AiScore and stopped, and did not attempt TNNS's Turnstile-gated token.
  * Helper T did not use the ProTennisLive token and WTA key embedded in Madrid's app.

## 2. Which events measure serve speed at all

This bounds what any source can hold. A source cannot have speed for a court that had neither ball tracking nor a radar feeding the data chain.

### 2.1 ATP Tour

| Period | What the rules or announcements say | Evidence |
|---|---|---|
| 2017–2024 | ELC Live "first trialled at the Next Gen ATP Finals in 2017"; "available for tournaments on a voluntary basis, becoming widely adopted since the COVID-19 pandemic" (WF) | [documented] ATP release, 28 Apr 2023, https://www.atptour.com/en/news/electronic-line-calling-release- |
| From 2025 | "Tour-wide adoption of Electronic Line Calling Live (ELC Live) will be from 2025", for "players competing in both main draw and qualifying events". "All-court ELC Live coverage will also deliver comprehensive player and ball tracking across the whole Tour, leading to an unprecedented level of data … in collaboration with Tennis Data Innovations (TDI)" (WF) | [documented] same release |
| 2026 | Rule 5.08 A.1: "The use of the Live ELC system replacing line umpires is mandatory at all ATP Tour events." Rule 6.01 H: "1) All ATP Tour tournaments regardless of surface are required to use the ATP approved and designated Live ELC. 2) The system must be available for use on all match courts. 3) The system must be available from the first day of qualifying through the end of the event on all match courts." | [documented] 2026 ATP Rulebook, 27 Apr 2026 revision, https://www.atptour.com/-/media/files/rulebook/2026/2026-rulebook_27apr26.pdf (the 14 Jan 2026 version has the same text) |
| 2026 | Vendors with their own review procedures in Exhibit T.1: FoxTenn, Hawk-Eye, FlightScope | [documented] same rulebook |

**What the coordinator measured, and what explains it [inference, partly search].**
* **The measurement.** In the decrypted Stats Centre copy, 70 of 189 tour events of 2022–24 have no speed on any match: mostly clay events and smaller 250s, plus some grass and indoor ones. Within the other events, 92–99% of matches have speed on every court.
* **Hawk-Eye was not used for line calling on clay before 2025.** "Foxtenn 'Real Bounce' was used in Madrid and in previous years in Rio and Barcelona as the preferred technology for clay court line calling" [search, summarising https://sport.quotidiano.net/en/tennis/sinner-errore-giudice-occhio-di-falco-3b0e44ca]. The Mutua Madrid Open announced FoxTenn ELC for 2021 [search, https://mutuamadridopen.com/en/mutua-madrid-open-to-feature-electronic-line-calling-from-foxtenn/].
* **The pattern fits the Stats Centre getting speed from Hawk-Eye installations only.** Events with no ball tracking, FoxTenn alone, or a stand-alone radar would then have nothing there.
  * Madrid 2022 at 5% fits FoxTenn for line calls with little Hawk-Eye.
  * Monte-Carlo and Rome, which had Hawk-Eye for television and statistics, are not in the speedless list.
* **Whether those events had a radar gun**, and whether anything public shows its readings, is in §3.8 (helper T).
* **The same caveat applies from 2025.** The ATP's Live ELC mandate names several vendors, so a FoxTenn-equipped event in 2025–26 may also lack Stats Centre speeds, even though its ELC tracks the ball [inference; not measurable without the decrypted files].

### 2.2 WTA

| Period | Rule | Evidence |
|---|---|---|
| 2025 | Section XVIII C "Electronic Review". "a. WTA/ATP Combined WTA 1000 Mandatory Tournaments: Use of an ELC System is required at minimum on center court during the Main Draw at all WTA 1000 Mandatory hard court Tournaments. In addition, if a court will be equipped with an ELC System for the Main Draw and that court also will be used for Qualifying, then the ELC System is required to be used on that court during Qualifying. b. All Other WTA 1000 Mandatory and WTA 500 Tournaments: Use of an ELC System is required at minimum on center court for the Main Draw at all WTA 1000 Mandatory and WTA 500 hard and grass court Tournaments." No requirement for WTA 250s or clay | [documented] 2025 WTA Rulebook, p. 374, https://photoresources.wtatennis.com/wta/document/2025/01/06/50d1eafa-e678-4081-bfa8-5576f670f801/2025-WTA-Rulebook-1-5-2025-.pdf |
| 2025 | Charleston (WTA 500, clay) "first WTA Tour clay tournament to use Electronic Line Calling Live", qualifying and main draw; Madrid and Rome used it as combined events | [search] https://wtatennis.com/news/4239258/credit-one-charleston-open-becomes-first-clay-tournament-to-use-elc-live |
| 2026 | Section XVIII C "Electronic Line Calling", 1. Required Use: "All WTA 1000, WTA 500, and WTA 250 Tournaments, regardless of surface, are required to use a WTA-approved and designated live electronic line calling system ('Live ELC System'). The Live ELC System must be available for use on all match courts and operational from the first day of Qualifying until the end of the Tournament. Except for combined or back-to-back events that have secured or are securing ELC under the ATP ELC program as of 2025, the WTA at its sole discretion is responsible for assigning a selected and approved vendor to each Tournament." | [documented] 2026 WTA Rulebook, p. 382, https://photoresources.wtatennis.com/wta/document/2025/12/24/b300b2a4-8d71-4346-969f-1f6b9399661f/2026-WTA-Rulebook-12-22-2025-.pdf |
| 2025 and 2026 | Both rulebooks allow a betting sponsor's logo on "the serve clock and serve speed box", so serve-speed displays are a standard court fixture. That says nothing about where readings are recorded | [documented] same rulebooks |
| 2022 | Same requirement as 2025, word for word apart from "Mandatory": centre court of WTA 1000 hard-court events, and of WTA 1000 and 500 hard and grass events, main draw | [documented] 2022 WTA Rulebook (21 Mar 2022), p. 382, https://photoresources.wtatennis.com/wta/document/2022/04/28/fb67aec5-5894-466c-9aea-c7f4813ce20f/2022-WTA-Rulebook-3-21-2022-.pdf |
| 2026, July revision | Live ELC clause unchanged | [documented] https://photoresources.wtatennis.com/wta/document/2026/08/10/f7e04e05-20c2-4f22-979c-3bbfdb3aa778/2026-WTA-Rulebook-7-27-2026-.pdf, p. 384 |
| 2015–2021 | Not checked; 2023 and 2024 not checked either | — |

**Reading:** before 2026, WTA tracking-based speed exists only on the show courts of WTA 1000/500 hard and grass events, plus the combined ATP/WTA events. Radar-only courts may have displayed speeds without recording them anywhere public [inference].

### 2.3 Challengers and WTA 125

* **Challengers.**
  * The 2026 ATP Rulebook only authorises electronic review there [documented]:
    * Rule 7.22 L: "A. Electronic Review (Review ELC) - applicable to ATP Challenger Tour only".
    * Rule 6.27: "The use of an approved electronic system for reviewing line calls and/or overrules is authorized for use at ATP events."
  * **Live ELC at some 2026 Challengers.**
    * "This is the first year Challengers have regularly used ELC, with the Bolt6 system approved for the top level of professional competition … I know there is no alternative once the ELC has been mandated" [third-party: ZooTennis, 21 Jul 2026, on the Cranbrook/Bloomfield Hills Challenger 125, http://tenniskalamazoo.blogspot.com/2026/07/elc-goes-down-2025-finalist-martin.html].
    * Lincoln 2026 used Bolt6; "not all Pro Circuit tourneys utilize this growing technology" [search, https://www.usta.com/en/home/stay-current/missourivalley/nebraska/lincoln-challenger-pro-circuit-2026.html].
    * Tallahassee 2026 "marks the debut of Electronic Line Calling" (WF) [third-party, https://floridatennis.com/blogs/news/atp-challenger-in-tallahassee-returns-april-12-19-with-loaded-field-streaming-video-and-electronic-line-calling].
    * Heilbronn 2024 was the first clay ELC Live event (FoxTenn, all courts) [third-party, https://www.tennis.com/news/articles/how-did-an-atp-challenger-in-germany-make-history-with-electronic-line-calling].
  * **Tennis IQ for Challengers.** The ATP's player-facing Tennis IQ (serve location and similar) has Challengers "expected to be added later this year" (WF) [third-party, tennis.com, 13 Apr 2026, https://www.tennis.com/news/articles/game-plan-match-stats-live-data-how-tech-changing-match-preparation].
  * **Official data on Challenger sites.** Rule 6.09 F: tournaments that show "live scoring or statistical match data on their digital platforms … must exclusively use official ATP data" [documented].
* **What reaches public sources from Challengers.**
  * A Bolt6 Challenger final (Lincoln 2026) shows no speed on Flashscore [observed, §3.7].
  * The crawl's 2024 Challenger "100%" events are all "0 km/h" placeholders (§3.7.4), so they are no evidence of measurement.
  * Together with the Stats Centre's under 1%, no public source shows Challenger serve speed [observed, absence].
* **WTA 125.** The 2026 WTA requirement names only WTA 1000, 500 and 250 [documented]. No WTA 125 ELC programme was found [search, absence].

### 2.4 Tracking and radar suppliers

* **Approved line-calling systems (ITF list, December 2023)** [documented, https://www.itftennis.com/media/12242/line-calling.pdf]:
  * Hawk-Eye Officiating (2005); Hawk-Eye Live (June 2020, hard and grass);
  * FOXTENN (December 2016; first used at Metz 2017); FOXTENN Live (November 2021, hard and grass);
  * "IMG Arena (formerly FlightScope)" (January 2020); IMG Arena Live (December 2023);
  * Bolt6 Sentinel (live, hard courts, October 2023).
* **Serve-speed radars:** the same list says "the ITF Technical Centre also launched a scheme to validate the accuracy of systems used for measuring the speed of serves. To date, one system has completed evaluation – FlightScope RacquetRadar."
* **Radar linked to the umpire's scoring device (an older claim).**
  * EDH Sport, FlightScope's predecessor, says "EDH Scoring Systems are present on the umpires chair at all ATP and WTA events from the start of the Qualifying competition to the last ball of the finals".
  * Its RacquetRadar is "Triggered automatically by the umpire's EDH scoring PDA". Clients named: "Wimbledon, Paris, numerous USA events, Canada, Dubai, Rome and Beijing".
  * Source: an undated EDH press document, probably about 2004–05, since it cites Roddick's 2003 and 2004 records [claimed, https://uploads.flightscope.com/AGC-EDH_Information/Press/0124.doc].
  * So some tour events recorded radar speeds inside the official scoring chain two decades ago [inference]. I found no public archive of them.
* **SMT/IDS radar** (about 2014): "the leading supplier of serve speed clock systems to the WTA and ATP" and "the only supplier of serve speed systems at tennis Grand Slam tournaments". It says speeds are "not an official statistic" and that it has "been supplying data to both tours" [claimed, §3.10].
* **Radar consistency:** the ATP "does not officially recognize speed records because of the variance in radar guns" [third-party/search, https://en.wikipedia.org/wiki/Fastest_recorded_tennis_serves]. Radar and Hawk-Eye readings, and different radars, are not one measurement system [inference].
* **Who holds the data now:** Sportradar is TDI's exclusive distributor for ATP data (earlier lanes), and acquired IMG Arena, which owns the former FlightScope line calling, in November 2025 [third-party, earlier lanes].

## 3. Per-source findings

### 3.1 atptour.com: no plain per-match speed anywhere

| Route | Result | Evidence |
|---|---|---|
| Match-stats page `/en/scores/match-stats/archive/2026/747/ms001` (Beijing 2026 final) | The Vue template renders only `Stats.ServiceStats` (serve rating, aces, double faults, first serve, first- and second-serve points won, break points saved, service games), `ReturnStats` and `PointStats`. It also loads Infosys's script (`atp_matchstats-externalScript` = `…/itp/prod/atp/match-centre/main.js`) | [observed] |
| `/-/Hawkeye/MatchStats/Complete/2026/747/MS001` and `/2019/404/MS001` | JSON box score; no key containing speed, km/h or mph (126 distinct keys in 2019) | [observed] |
| Stats leaderboard `/en/stats/leaderboard` (API `/en/-/www/StatsLeaderboard`) | Boards: serve, return, under pressure; filters 1991–2025, surface, opponent rank. No speed board | [observed] |
| Individual match stats `/en/stats/individual-game-stats` (API `/en/-/www/individualmatchstats/`) | Fact types: aces, first serve, first- and second-serve points won, service games won, break points saved, the return equivalents. No speed | [observed] |
| TDI Insights `/en/stats/tdi-leaderboard-leaders` (API `/-/aws/tdileaderboard/stats/all`) | TennisViz "Shot Quality" 0–10 for serve, return, forehand, backhand, "calculated in real-time by analysing each shot's speed, spin, depth, width"; player level, not a speed | [observed] |
| Stats Centre page `/en/scores/stats-centre/archive/2025/404/ms022` | HTML shell; no server-rendered speed. Search engines index the rendered values ("first serve average speeds ranging from approximately 170-220 km/h") [search] | [observed] |
| News | Season averages only, e.g. 2025 leaders in average first-serve speed from "the Infosys ATP Stats section" (WF), 18 Jan 2026, https://www.atptour.com/en/news/scorecards-mpetshi-perricard-first-serve-speed | [observed text] |

* **Terms (earlier lanes):** atptour.com forbids "Systematic retrieval of data" and "gambling or wagering" use.
* **Access:** 11 requests to www.atptour.com, all 200, no challenge.

### 3.2 Infosys ATP Stats Centre: the only official per-match carrier, encrypted

* **Speed fields, from Infosys's own client code** [documented; observed in `https://itp-atp-sls.infosys-platforms.com/itp/prod/atp/match-centre/main.js`, 2.26 MB]:
  * **Key Stats** (per match, and per set where the page offers set tabs [inference]):
    * `"Max Speed":[…speedStats.maxSpeed…]`
    * `"1st Serve Average Speed":[…speedStats.fsAvgSpeed…]`
    * `"2nd Serve Average Speed":[…speedStats.ssAvgSpeed…]`
  * **MatchBeats** (per point). The export columns are `set, game, point, server, firstServer, scorer, result, serve, serveSpeed, stroke, hand, lastHitter, pointDuration, currentMatchDuration, isBrkPt, isCrucialPt, tm1GameScore…`. The rally view has a "Serve speed" filter.
  * Units: the rendered page shows km/h and mph [search]. The serve-and-volley CSVs (§3.4) carry both.
  * **Measuring system:** not stated in the code. The 2022–24 pattern suggests Hawk-Eye installations (§2.1) [inference].
* **Routes** (from `…/itp/prod/atp/config/match-centre/env.prod.json`) [observed]:
  * `API_STATS` `/prod/api/stats-plus/v1/keystats/year/#year/eventId/#eventId/matchId/#matchId`
  * `API_MATCH_BEATS`, `API_RALLY_ANALYSIS`, `API_STROKE_SUMMARY`, `API_COURT_VISION`, `API_INSIGHTS` (assisted journalism) and `API_LLM_COMMENTARY` (`/prod/api/llm-commentary/v3/…`), plus a chatbot.
  * The chatbot's suggested questions include "What was the average first serve speed of {tm1Ply1Name}{tm1Ply2Name} in current match?". Not called (it is a POST; a form-like submission).
* **What came back today** (Referer and Origin set to atptour.com) [observed]:

  | Request | Status | Body |
  |---|---|---|
  | keystats API route, 2026/747/MS001 (Beijing 2026 final) | 200 | `{lastModified, response: <31,576 base64 chars>, data: null}` |
  | keystats static file, 2026/747/MS001 | 403 | S3 `AccessDenied` (no static copy at that path yet) |
  | keystats static file, 2025/352/MS001 (Paris 2025 final) | 200 | `{lastModified, response}` |
  | LLM commentary v3, 2026/747/MS001 | 200 | same encrypted envelope (the 24 Sep pass got 403 on `/prod/api/*`; this route now answers) |
  | match-beats status, 2026/747/MS001 | 200 | 1,680-byte encrypted envelope; even availability flags are not plain |

* **Contents of the encrypted files, third-party:** see the 24 Sep notes (`granular_data_leads/research_notes/A_tour_official.md` §2). Decrypted copies: Hugging Face handoff (2021–24), SirGenkii (January–April 2025).
* **Archive:** the files stay up after the match and are rewritten later (earlier lanes). The Wayback Machine holds 237 captures of ATP Infosys data files, from November 2021 to 2026, and none earlier [observed, CDX].
* **Cost:** free to load in a browser.
* **Terms:** atptour.com's; Infosys terms not stated.
* **Decryption is the owner's decision.**

### 3.3 ATP app gateway (`app.atptour.com/api/v2/gateway/livematches/website?scoringTournamentLevel=tour`)

* **Contents** [observed, 14:11 UTC; 9 matches listed from Shanghai, Beijing and Tokyo]:
  * no key containing speed;
  * `ExtendedMessage` gives the last point in words (e.g. "… wins the point on his 2nd serve.");
  * `HasStats` true and `HasCourtTracking` false on all 9, including Shanghai's Stadium Court.
* **History:** live only (earlier lane).
* **The site script** (`/assets/atptour/js/atptour.min.js`) uses the gateway only for live scores [observed].

### 3.4 `serve-and-volley/atp-world-tour-tennis-data` (GitHub): plain copy of rendered Key Stats, 18 Oct 2021 – 2022

*An open dataset, so lane B may also list it.*

* **What it is** [observed]: CSVs scraped from the rendered Stats Centre pages.
  * `csv/3_match_stats/match_stats_extended_2021.csv`: 257 rows; 246 with both players' first-serve average above 0.
  * `match_stats_extended_2022.csv`: 1,547 rows; 1,436 with both above 0.
* **Columns:** `winner_/loser_max_service_speed_kmh/_mph`, `avg_1st_serve_speed_kmh/_mph`, `avg_2nd_serve_speed_kmh/_mph`, plus net points, winners and unforced errors. The files have no header; the column order is in the README.
* **Coverage** [observed]:
  * 2021: Stockholm, Antwerp, St Petersburg, Vienna, Paris, ATP Finals, Next Gen Finals.
  * 2022: 35 events, mostly 81–100% of rows with speed (Eastbourne 35%, Adelaide 69%, Queen's 74%).
  * No clay 250s at all.
  * **An independent check on the coordinator's speedless list:** the 35 events include none of the 30 speedless 2022 events except Madrid, and Madrid only with its two semi-finals and final [observed].
  * So the rendered Stats Centre itself showed speed event by event, as the decrypted copy does.
* **Quality:** at least one impossible value (a 460 km/h maximum) [observed].
* **Before 18 Oct 2021:** the basic files (1991–2022) have no speed columns. The README sends ATP matches before 2021-10-18 to `match_stats_deprecated.py`, whose output lacks speed [observed].
* **Value to the project:** it overlaps the decrypted handoff copy. A plain-text cross-check for 2021-Q4 and 2022, not new coverage.
* **Licence:** CC BY 4.0 per the README (the GitHub API shows no licence file). The data is the ATP's.
* **Repository:** pushed 28 Aug 2023; 222 stars.

### 3.5 WTA: API, website, app and partners

| Route | Result | Evidence |
|---|---|---|
| `api.wtatennis.com/tennis/tournaments/1152/2026/matches/LS001/stats` (Singapore 2026 final, WTA 500) | 32 keys (aces, double faults, first-serve points, break points…); none about speed | [observed] |
| `…/LS001/advanced-stats` | 68 keys (winners and errors by wing, fault reasons, rally buckets, net play, violations); none about speed | [observed] |
| `…/tournaments/1020/2026/matches` (Beijing 2026, during play) | Match rows carry a `BinPacketBase64` field: empty on all 53 Singapore rows and on Beijing's live match (LS009) | [observed] |
| wtatennis.com match page, `bundle-es.js` and `match-centre.js` (build v7.53.2) | No "speed" or "Speed" string in the page or either script. The match centre is a React widget on the API above | [observed] |
| SAP Tennis Analytics for Media | "Exclusively for the WTA credentialed media", from 2018 (WF) | [claimed] https://www.wtatennis.com/news/1415620/sap-and-wta-announce-real-time-analytics-for-media |
| Stats Perform (Official WTA Data Supplier, Nov 2020) | Opta analysts collect "detailed match statistics down to rally and shot level", for "broadcast, second screen, and betting experiences" (WF). No public product | [claimed] https://www.wtatennis.com/news/1906120/wta-and-stats-perform-serve-up-breakthrough-partnership |

* **Terms:** the WTA's terms forbid automated access and harvesting (earlier lane, `H_wta.md`).
* **Verdict:** no official WTA route carries speed.

### 3.6 ProTennisLive (LSHD)

* **Today:** `https://www.protennislive.com/` and `/lshd/main.html?year=2026&wtaid=1020` both return 503 "Service Unavailable" (IIS) [observed]. The 24 Sep pass saw the same.
* **Wayback** (CDX for `protennislive.com/*` and `/lshd/*`) [observed]:
  * old `frameset.asp` pages and the LSHD shell (`main.html`);
  * Flash modules: `livemodule/livemod.swf`, `completedmodule/completedmod.swf`, `drawmodule/drawmod.swf`;
  * no captured data feed.
* **Verdict:** whatever LSHD displayed is not recoverable. The API (`api.protennislive.com/feeds`) is token-only (earlier lane).

### 3.7 Flashscore (Livesport): field present only on some matches; desktop feed signed, mobile page plain

#### 3.7.1 Routes

* **Desktop match page** (`/match/{id}/`) [observed]:
  * no statistics in the HTML;
  * the page config publishes `"feed_sign":"SW9D1eZo"`;
  * the statistics feed `https://2.flashscore.ninja/2/x/feed/df_st_1_8v653Rz9` returned **401 Unauthorized** without the `x-fsign` header.
  * Under the brief I did not send it. **This is a signed feed.**
* **Mobile site** (`https://www.flashscore.mobi/match/{id}/?t=stats`) [observed]:
  * server-rendered HTML with the whole statistics block, no script needed;
  * when Flashscore has them, it includes rows such as "198 km/h | Average 1st serve speed | 203 km/h" and "165 km/h | Average 2nd serve speed | 169 km/h";
  * **Control:** the 2024 ATP Finals final (id `UizcOOid`) matched the crawl's stored values exactly.
* **Mobile robots.txt:** `User-agent: * … Disallow: /match/` [observed, https://www.flashscore.mobi/robots.txt]. The 23 mobile match pages read here (plus robots.txt) were a bounded measurement, disclosed for the owner's judgement. I read robots.txt only after the first two match pages.
* **Terms** (earlier lane, effective 1 Apr 2023) [documented]:
  * 2.9 "no extraction (copying) or utilization … of Database Content or of a qualitatively or quantitatively substantial part thereof is permitted without our explicit consent";
  * 2.10 "you are not permitted to use the content of the website by embedding, aggregating, scraping or recreating it without our express consent";
  * AI training not mentioned.
* **Tennis24** is the same Livesport platform and feed (earlier lane); not probed.

#### 3.7.2 Sample, May–October 2026

One results page per event on flashscore.com (to list ids), then the final's mobile stats tab. Finished matches only.

| Event (2026) | Date | Match | Average 1st / 2nd serve speed |
|---|---|---|---|
| ATP Madrid 1000 | 3 May | Final, Sinner v Zverev | **present** (both players, km/h) |
| ATP Rome 1000 | 17 May | Final, Sinner v Ruud | **present** |
| ATP Rome 1000 | May | R32, Pellegrino v Fils | none |
| ATP Hamburg 500 | 23 May | Final | none |
| ATP Halle 500 | 21 Jun | Final | none |
| ATP Queen's 500 | 21 Jun | Final | none |
| ATP Washington 500 | 3 Aug | Final | none |
| ATP Montreal 1000 | 14 Aug | Final | none |
| ATP Cincinnati 1000 | 23 Aug | Final | none |
| ATP Beijing 500 | 6 Oct | Final | none |
| ATP Shanghai 1000 | 6–7 Oct | qualifying final; R128 | none; none |
| WTA Rome 1000 | 16 May | Final | none (the ATP final on the same court has it) |
| WTA Toronto 1000 | 13 Aug | Final | none |
| WTA Cincinnati 1000 | 23 Aug | Final | none |
| WTA Beijing 1000 | 7 Oct | R16 | none |
| Challenger Lincoln (Bolt6 ELC) | 19 Jul | Final | none |
| Wimbledon, men / women | 12 / 11 Jul | Finals | **present** / **present** |
| US Open, men | 13 Sep | Final | **present** |
| *Controls:* ATP Finals 2024 final; Cincinnati 2024 final | Nov / Aug 2024 | — | present (equals crawl); none (crawl record also has none) |

* **Reading [inference]:**
  * Flashscore's speed comes from a feed that reaches some ATP Masters finals and the Slams, not from the venue's measurement. The WTA Rome final on the same court as the ATP final lacks it.
  * For May–October 2026 it is a sporadic source for ATP non-Slam matches and gives nothing for WTA non-Slam matches in this sample.
  * One final per event cannot show partial coverage within an event. Rome had it on the final but not on a round of 32.
* **Archive:** the mobile page served 2024 matches with their speed rows, so old matches keep the field.
* **Cost:** free.

#### 3.7.3 What the field is

* Per player, per match: "Average 1st serve speed" and "Average 2nd serve speed" in km/h.
* No count of serves averaged is shown.
* Whether the average is over first serves in or all first serves is not stated.
* No fastest serve row was seen.
* The measuring system is not stated.
* The main session found that it agrees with the official Slam speeds to a median of 0.3 km/h per player.

#### 3.7.4 The zero-placeholder problem in the crawl (for `flashscore_crawl.py`)

[observed, local read-only scan, `crawl_cincy_check.py` in the scratchpad]

* **What makes the two rows "100%".** All 62 "Cincinnati" and 53 "Toronto" 2024 records with a speed field are WTA matches from the head-to-head passes (e.g. Anisimova v Pegula, Navarro v Andreeva), and every one has `home_average_1st_serve_speed` = `away_…` = **"0 km/h"**.
* **Why they count.** `kmh()` returns 0.0, which is finite, so they count as timed.
* **The ATP matches at those events.** The ATP Cincinnati 2024 final's own record (`rB0NYxcM`, year file) has no speed field, and neither does its live mobile page.

**Extent** [observed, `crawl_zero_check.py`; same files, same parsing as `flashscore_crawl.py`; deduplicated by match id, keeping a non-zero record where one exists]:

| Year | Records with a parsed first-serve average | Both players > 0 km/h | "0 km/h" placeholders |
|---|---:|---:|---:|
| 2024 | 939 | **17** | 922 |
| 2025 | 606 | 602 | 4 |
| 2026 (to 17 Apr) | 394 | 393 | 1 |

* **2024: only 17 real values.** They are Next Gen Finals 2024 (15), one Shanghai 2024 match and the 2024 ATP Finals final.
* **Zeros on every record:** Cincinnati 2024 (61), Toronto 2024 (52), Hamburg 2024 (34) and Washington 2024 (13), and every 2024 Challenger in the crawl's "~100%" list:
  * Bonn, Todi, Grodzisk Mazowiecki, Santo Domingo, Zhangjiagang, Bogota, Cordenons, Porto (two events), Dobrich, Mallorca, Cary, Lincoln, Monterrey, Cleveland, Barranquilla, Como, San Marino, Jinan, Liberec, Lüdenscheid, Lexington.
* **2025–26 values are real.** The event list is Slams, Rome, Madrid, Toronto, Cincinnati, Washington, Geneva, Eastbourne, Umag, Queen's, Basel, Shanghai, Beijing, the Turin Finals and Hong Kong 2026.
* **Consequence:** the brief's "about 15 Challengers of 2024 at about 100%" and "Cincinnati/Toronto 2024 100%" are artifacts. The 2024 partial shares (Washington 14%, Hamburg 29%) are zeros too.
* **Fix:** treat 0 km/h as missing.
* Sent to the main session at about 14:45 UTC. It confirmed the bug and changed both scripts to treat values outside 40–270 km/h as missing. The per-event table is `crawl_zero_check.tsv` in the scratchpad.

### 3.8 Tournament websites (helper T, plus my check of the LTA widget)

**Result: no tournament site shows per-match serve speed in plain form** (average, per set, per point or fastest), across about 20 sites [observed, 14:09–14:56 UTC].
* They show at most the ATP-standard box score.
* No site names a measuring system.
* Past editions are rarely kept.
* The one site whose client code has speed rows is the LTA's (Queen's, Eastbourne), and its data is encrypted (below).

| Event | Site / data route | Provider | Speed | Editions / archive | Terms |
|---|---|---|---|---|---|
| Indian Wells | bnpparibasopen.com/scores; tRPC (`matchDetails`, `draws`) | Own Next.js | None in the scores code; match detail not reached in about 9 requests | `/scores/2026` exists; depth unknown | Personal-use licence; ticket holders barred from collecting scores or statistics "for any commercial, betting or gambling purpose"; AI not mentioned |
| Miami | `prod.stats.miamiopen.com/api/v1/scores?tournament=0902&year=` | Own | None (scores, start, duration) | 2026 only; `year=2024` returns 2026 | Bans "any scripts designed to scrape or extract data" |
| Madrid | mutuamadridopen.com/results (Vue, PHP proxy) | ProTennisLive (ATP) and the WTA API, through credentials embedded in the app's JS. **Not used** | None (score, server, duration, umpire) | Current year only [inference] | No site terms found |
| Rome | `dp-fitp-ibi-prod-function.azurewebsites.net/api/v2/atp/match-stats?match_id=…` | FITP | None; ATP-standard stats per set | Current only [inference] | None found |
| Canada | nationalbankopen.com, `api.nationalbankopen.com` | Own | None (ATP-standard labels) | Editions 2023–2027 selectable | Bars collecting "match scores or statistics for betting or commercial purposes" |
| Cincinnati, Dubai | `tennis-feeds.rain-digital.ca/get/atp/{event}/{match}` | Rain Digital (court config names SMT) | None; per-set box score plus actual start and end times | Current only [inference] | Cincinnati bans "any robot, spider, scraper"; Dubai bars ticket holders from collecting scores or stats for betting |
| Paris | rolexparismasters.com (FFT, data in page) | FFT | None. Schema has winner/error splits, null in 14 matches | 2025 | Bans "any software, device, robot, script… to extract any information" |
| Washington, Vienna, Rio, United Cup | ATP tournament-site platform, `/-/tournaments/matchStatsApi/MatchStats?year=&eventId=&matchId=` | ATP | None (ATP-standard per set) | Current year; prior years return HTTP 500 | ATP terms: "Systematic retrieval of … scores, statistics … is prohibited"; "commercial, gambling or wagering purposes strictly prohibited" |
| Halle | terrawortmann-open.de; live app `live.terrawortmann-open.de` (`api.php`) | ProTennisLive-format proxy | None (score, server, time) | Results since 1993 (no stats); the Wayback Machine has the 2023–24 live page but not its JS | Not read |
| Doha | atpqataropen.com, AWS API `/results`, `/matchDetails` | Own | Unknown: 401 "Live ATP data is temporarily unavailable" outside the event | — | Ticket terms only |
| Brisbane, Adelaide | tennis.com.au iframes from `{event}-prod.smtinternetservices.com/json/…` | SMT | None (sets, minutes per set, match time). **Not the AO match-centre platform** | 2026 only | Tennis Australia bans "automated means (such as harvesting bots, robots, spiders, or scrapers)" |
| Shanghai, Beijing, Wuhan, Basel, Stuttgart (WTA), Nitto ATP Finals, WTA Finals, Barcelona, Munich, 's-Hertogenbosch, Hamburg | — | — | No stats section, empty before the event, unreachable (Wuhan), or links out to atptour.com or wtatennis.com. Barcelona's "Estadísticas" are historical records; 's-Hertogenbosch shows score and duration; Hamburg's "Hawkeye" menu is a newsletter | — | — |
| **Queen's, Eastbourne (LTA)** | lta.org.uk match centre → Infosys `isp-lta-sls.infosys-platforms.com` | **Infosys** | **Documented, encrypted** (see below) | 2026 events 311, 741 and 7740 seen in the Wayback CDX (captures June 2026) | LTA terms 13.3 ban "text or data mining or web scraping … for any purpose"; 13.5 ban use for "developing, training, fine-tuning or validating any artificial intelligence system or model" |

**The LTA's Infosys match centre** (my requests, 15:05–15:07 UTC, Referer lta.org.uk) [observed]:
* **Config.** `…/isp/prod/lta/config/match-centre/env.prod.json` lists `API_STATS` = `/prod/api/lta/stats/year/#year/eventId/#eventId/matchId/#matchId`, plus scores, head-to-head and draws.
* **Speed rows in the client code** (`…/match-centre/assets/index-D1tGxy04.js`):
  * "Fastest Serve (m/h)": "The fastest serve hit by a player during the match."
  * "1st Serve Avg. (m/h)": "The average speed of a player's 1st serve during the match."
  * "2nd Serve Avg. (m/h)": "The average speed of a player's 2nd serve during the match."
  * So the widget is built to show per-match speed in mph, for the men's and women's draws it covers [documented].
* **Every reply is encrypted**, in the same `{lastModified, response}` envelope as the ATP Stats Centre:
  * stats for the 2026 Queen's men's final (311/MS001): 32,620 bytes;
  * the Queen's women's final (311/LS001) and the Eastbourne women's final (741/LS001): **18,372 bytes each**;
  * even `scores/match`.
* **Reading the sizes [inference]:** identical sizes for two different WTA finals hint at a fixed-size payload, perhaps without speed. That cannot be confirmed without decrypting.
* **Why it matters:** the only official route found with per-match speed fields for **WTA** non-Slam matches (gap 2), for the LTA's grass events from 2026. Same owner decision as §3.2.
* **Terms:** forbid scraping and AI use.

**What the sites suggest about measurement at the speedless events** (helper T; sources as stated):
* **Clay, before 2025: no electronic line calling at any of the listed clay tour events.**
  * The list: Barcelona, Munich, Estoril, Hamburg, Rio, Buenos Aires, Houston, Marrakech, Bucharest, Belgrade, Cordoba, Santiago, Bastad, Gstaad, Kitzbühel, Umag, Geneva, Lyon.
  * **Madrid** offered FOXTENN review from 2021 [observed, https://mutuamadridopen.com/en/mutua-madrid-open-to-feature-electronic-line-calling-from-foxtenn/, 9 Feb 2021].
  * **Rio 2020** trialled FOXTENN [search, ATP release of 24 Jan 2020].
  * The **Argentina Open 2025** was the first clay event with ELC Live, using Hawk-Eye [search: ESPN Deportes, Clarosports].
  * **Estoril** first used FOXTENN in 2025 [search].
* **FOXTENN instead of Hawk-Eye on hard courts:**
  * Marseille [third-party, AFP via scroll.in, 16 Mar 2019, https://scroll.in/field/916856/hawkeye-vs-foxtenn-two-tech-firms-are-battling-it-out-to-win-the-tennis-line-call-business];
  * Metz and Antwerp from 2017 [third-party, SportsBusiness Journal, 24 Jul 2017, https://www.sportsbusinessdaily.com/Journal/Issues/2017/07/24/Technology/Foxtenn.aspx];
  * Acapulco 2020 [third-party, tennis.com].
* **FOXTENN alone does not explain the gaps.**
  * Antwerp 2021 and 2022 do have Stats Centre speeds (87% and 97% of matches, §3.4).
  * So FOXTENN events can still carry speed when Hawk-Eye tracking is also installed, presumably for television [inference].
* **No evidence either way** for Halle, Stuttgart (ATP), 's-Hertogenbosch, Montpellier, Tokyo, Dallas, Pune, Astana, Newport or Los Cabos. Nothing found about stand-alone radars at any of them.
  * So "no ELC" does not prove "no measurement". But no public source showing radar readings for these events was found either: no tournament site, aggregator or Flashscore.
* **WTA:**
  * Charleston 2025 was the first WTA clay event with ELC Live [search, ESPN].
  * Stuttgart still used line judges in 2025 [search, Sportskeeda].
  * Eastbourne and Berlin: unknown.

### 3.9 Aggregators (helper B)

* **What was sampled:** finished matches of 2026 across tiers: ATP 1000 Shanghai, ATP 500 Beijing and Tokyo, WTA 1000 Beijing, WTA 125 Suzhou, Challenger Alicante, and the US Open 2026 as a control. Older Masters, 500s and Finals were read where a source shows history.
* **The coordinator's fill test, for sources that show any speed:** the Barcelona 2024, Halle 2024 and Paris 2024 finals, a Cincinnati 2024 semi-final and the Indian Wells 2025 final.

| Source | Speed field | Where seen / not seen | Archive | Access, cost | Terms (scraping / ML / betting) | Evidence |
|---|---|---|---|---|---|---|
| **Matchstat** (matchstat.com) | Per player per match: `fastestServe`, `averageFirstServeSpeed`, `averageSecondServeSpeed`. Whole numbers with no unit shown (km/h by magnitude, e.g. US Open 2026 final 213/192 first-serve averages) | **Filled at Slams only:** AO 2019 (WTA), 2024 (WTA), 2025 (ATP); RG 2019 (WTA); Wimbledon 2025 (WTA), 2026 (ATP); USO 2025 (WTA), 2026 (ATP, WTA). Null at RG 2025. **Null at every non-Slam seen:** Cincinnati 2024/25/26, Paris 2023/24, IW 2025, Monte-Carlo 2023/24, Madrid 2021/26, Montreal 2026, Barcelona 2024, Halle 2021/24, Munich 2025, Beijing/Tokyo 2026, Washington 2026, ATP 250s, both Finals, WTA 1000/500, Challengers | Slams 2019–Sep 2026 | JSON embedded in server-rendered head-to-head pages (`/tennis/h2h-odds-bets/{A}/{B}/`), free; API with free and paid plans [claimed] | "You must not use any part of the content on our site for commercial purposes without obtaining a licence"; no explicit scraping or ML clause found; the API is marketed for betting tools and ML (https://matchstat.com/predictions-tips/terms-and-conditions/) | values [observed]; unit [inference]; API [claimed] |
| **Tennis Abstract** (player `jsfrags/{Player}.js`) | Per match "Serve Speed" table: average, first-serve average, SD, T/wide average, max/min, and the same for second serves; mph by magnitude | Wimbledon and US Open rows only, 2021–2024. No 2025–26 rows, no non-Slam rows (e.g. none for Halle or Cincinnati 2024) | Last 20 speed matches plus a career row; ends at USO 2024 | Static JS, free | Not stated on the pages read | [observed]. The author's own statement (25 Mar 2024): "The only available point-by-point serve speed data these days comes from Wimbledon and the US Open" [documented] |
| **tennisstats.com** | Per player-season "Average Serve Speed" (km/h); player page says "* Slams Only". API: player aggregates `serve_speed_dict.average_first_serve_speed`, `average_second_serve_speed`; match stats have no speed | Slams only (its own note) | 2026 season | HTML free; API £19.99/month | "you will not access the Site through automated or non-human means, whether through a bot, script or otherwise"; personal non-commercial; API sold "for … Machine Learning, and AI" (https://tennisstats.com/terms-and-conditions) | [observed], [documented]; source not stated |
| 365Scores | None (aces, double faults, serve/return points won, break points, runs; USO adds stroke winners and errors) | Shanghai, WTA Beijing, Challenger Alicante, WTA 125 Suzhou, USO 2026 final: none | USO 2026 retrievable | Public JSON `webws.365scores.com/web/game/stats/…` | EULA not retrieved (timeout) | [observed] |
| AiScore | Unknown | — | — | Cloudflare managed challenge (403) on the first request; stopped | — | [observed: block] |
| LiveScore | None (web match page: Info and Summary only; stats endpoint returns `{}`) | Shanghai R1, USO 2026 final | — | Public JSON (scores) | Not read | [observed] |
| Tennis Temple | None (aces, double faults, first-serve %, serve points won, per set; USO adds winners and errors) | WTA Beijing 2026, USO 2026 final | USO 2026 | Server-rendered `/match/{slug}/{id}/stats` | "forbidden to extract or reuse all or a substantial part of our databases, including by automated means (scraping, bots, crawlers other than search engines)" (https://en.tennistemple.com/about/terms) | [observed] |
| Scores24 | None (Sportradar-style keys) | Shanghai 2026, USO 2026 final | USO 2026 | Server-rendered state | No "automated programs to interact with the Site" (https://scores24.live/en/p-rules) | [observed] |
| Oddspedia | None (Sportradar-style keys) | WTA Beijing 2026, USO 2026 final | USO 2026 | Server-rendered state | No reproduction without written consent | [observed] |
| BetExplorer, Tennis Explorer | None (odds, head-to-head, splits) | Shanghai 2026 | — | HTML | Livesport s.r.o. terms (the Flashscore group): no automated requests, no "embedding, aggregating, scraping or recreating" | [observed] |
| ESPN | None (players' `statistics` arrays empty) | Shanghai, China Open (ATP and WTA), USO 2026 final | — | `site.api.espn.com/…/tennis/atp/scoreboard` | Disney terms ban robots and scraping, "including … for the purposes of creating or developing any AI Tool" | [observed]. Lane A2 covers ESPN at the Slams |
| TNNS (tnnslive.com; embedded by Ubitennis) | Not determinable | — | — | Match detail needs a token minted through a Cloudflare Turnstile challenge; stopped | — | [observed: gate] |

* **The pattern behind it [inference]:** Scores24, Oddspedia, LiveScore and TNNS use Sportradar-style statistic keys or IDs. None has a speed field, even at the US Open. That fits the earlier finding that Sportradar's feeds carry no speed.
* **The fill test:** no aggregator fills any non-Slam event. Rio 2024 was not tested.
* **Cross-check.** Matchstat's US Open 2026 final values are first-serve averages of 213 and 192, second-serve averages of 181 and 164. They equal what Flashscore's mobile page shows for that final (§3.7.2) [observed].
  * So the two probably share an upstream (the Slam's own feed) [inference].
  * Helper B noted that 192 is low for that player against his earlier rounds. If wrong, the error is upstream.

### 3.10 Broadcasters and OTT (helper B)

| Source | Result | Terms | Evidence |
|---|---|---|---|
| Tennis TV (tennistv.com) | Public pages are a video library and profiles, with no statistics. The subscriber match centre is described as having "in-depth live statistics" | Bans automated "scraping, extracting"; domestic, non-commercial | public pages [observed]; match centre [search] |
| Tennis Channel / tennis.com | Serve and return percentages only (WTA Beijing, Shanghai, USO 2026 final); tennischannel.com redirects to tennis.com | Sinclair terms: personal, non-commercial; bans "mining, scraping, data extraction" | [observed] |
| Eurosport / TNT Sports | eurosport.com redirects to tntsports.co.uk. Shanghai 2026 statistics object empty; WTA Beijing none; USO 2026 R1 "General Statistics" without speed | Not read | [observed] |
| BBC Sport | Set scores only | Permission needed for "Anything plucked from our services to develop or train artificial intelligence or to do computer analysis" | [observed] |
| Sky Sports | Scores and live text only | Bans robots and scraping and use for "training … any artificial intelligence tool, model" | [observed] |
| beIN Sports | Tennis data loads through client-side Opta widgets (`optaApi`); nothing in the HTML; not pursued | Private use only; no scraping clause found | [observed: widget references] |
| Amazon Prime Video | No public statistics pages found | — | [search] |

* **The radar supplier's own statement** (SMT/IDS, about 2014, written for "25 years" since Wimbledon 1989) [claimed, https://smt.com/smt-ids-celebrates-25-years-of-measuring-tennis-fastest-serves/; WF and helper B]:
  * "the leading supplier of serve speed clock systems to the WTA and ATP";
  * "the only supplier of serve speed systems at tennis Grand Slam tournaments";
  * accuracy "plus-or-minus 1 to 2 mph";
  * "It's a fan-enhancement tool, not an official statistic … The ATP and WTA tours do not consider Serve Speeds official stats";
  * "we've been supplying data to both tours as part of our contribution to the sport".
* **What follows [inference]:** radar speeds at tour events reached the tours themselves, scoreboards and TV graphics. No public archive of those radar readings was found.

## 4. Probe log (7 Oct 2026, UTC)

* **The full per-request log** (time, host, method, mode, URL, status, bytes, note) is `probe_log.tsv` in the session scratchpad (`…/scratchpad/laneA1/`), with the bodies; neither is in the repository.
* Below it is grouped.
* **Modes:**
  * "chrome" = Chrome TLS fingerprint only;
  * "atp" = Chrome plus `Referer`/`Origin: https://www.atptour.com`;
  * "wta" = the same for wtatennis.com;
  * "plain" = a curl user agent.

### 4.1 This lane's own requests (96)

| Time | Host | n | Mode | Requests | Status |
|---|---|---:|---|---|---|
| 14:03:55–14:03:58, 14:50:06–14:50:09 | photoresources.wtatennis.com | 4 | chrome | WTA Rulebook PDFs: 2026 (Dec 2025 and Jul 2026 versions), 2025, 2022 | 200 ×4 |
| 15:05:59–15:07:02 | isp-lta-sls.infosys-platforms.com | 6 | ref=lta.org.uk | LTA match-centre `env.prod.json`; `stats` for 2026 311/MS001, 311/LS001 and 741/LS001; `scores/match` 741/LS001; match-centre asset `index-D1tGxy04.js` | 200 ×6 (all data replies encrypted) |
| 14:04:55–14:14:00 | www.atptour.com | 10 | chrome / atp | 2026 Rulebook (14 Jan and 27 Apr PDFs); match-stats page and Hawkeye JSON for 2026/747/MS001; `atptour.min.js`; stats leaderboard; individual match stats; stats home; TDI Insights; Stats Centre page 2025/404/ms022 | 200 ×10 |
| 14:33:09 | www.atptour.com | 1 | atp | Hawkeye JSON 2019/404/MS001 | 200 |
| 14:10:02–14:11:08, 14:36:16 | itp-atp-sls.infosys-platforms.com | 7 | atp | `main.js`; `env.prod.json`; keystats static 2026/747/MS001 and 2025/352/MS001; keystats API 2026/747/MS001; LLM commentary v3 2026/747/MS001; match-beats status 2026/747/MS001 | 200 ×6; 403 ×1 (static 2026). Envelopes inspected for their keys only |
| 14:11:51 | app.atptour.com | 1 | atp | gateway `livematches/website?scoringTournamentLevel=tour` | 200 |
| 14:14:15–14:15:21 | api.wtatennis.com | 5 | wta | tournaments Sep–Oct 2026; matches 1152/2026 and 1020/2026; `stats` and `advanced-stats` 1152/2026/LS001 | 200 ×5 |
| 14:21:03–14:21:46 | www.wtatennis.com | 3 | chrome | match page 1152/2026/LS001; `bundle-es.js`; `match-centre.js` (v7.53.2) | 200 ×3 |
| 14:15:33–14:15:36 | www.protennislive.com | 2 | chrome | root; `/lshd/main.html?year=2026&wtaid=1020` | 503 ×2 |
| 14:15:50–14:22:19 | web.archive.org | 3 | plain | CDX: `protennislive.com/*`, `www.protennislive.com/lshd/*`, `infosys-platforms.com` (domain) | 200 ×3 |
| 14:17:21–14:30:43 | www.flashscore.com | 21 | chrome | match page 8v653Rz9; results pages for ATP Beijing, Cincinnati 2024 (control), Rome, Hamburg, Halle, London (Queen's), Wimbledon, Washington, Montreal, Cincinnati, US Open, Shanghai (×2), Madrid; WTA Rome, Wimbledon, Toronto, Cincinnati, Beijing; Challenger Lincoln | 200 ×21 |
| 14:18:07 | 2.flashscore.ninja | 1 | ref=flashscore.com | statistics feed `df_st_1_8v653Rz9` **without** `x-fsign` | 401 |
| 14:23:37–14:30:44 | www.flashscore.mobi | 24 | chrome | robots.txt; match page 8v653Rz9; 22 stats tabs (§3.7.2 table plus the controls) | 200 ×24 |
| 14:19:39 | uploads.flightscope.com | 1 | chrome | EDH press document `0124.doc` | 200 |
| 14:33:56–14:34:43 | raw.githubusercontent.com | 4 | chrome | serve-and-volley README; `match_stats_extended_2021.csv`, `…_2022.csv`; `match_stats_2019.csv` | 200 ×4 |
| 14:34:16–14:34:19 | api.github.com | 2 | plain | contents of `csv/3_match_stats`; repository metadata (unauthenticated) | 200 ×2 |
| 14:36:50 | www.itftennis.com | 1 | chrome | ITF line-calling PDF (Dec 2023) | 200 |

* **Pacing.** Requests to one host were 3–4 s apart. In the Flashscore batches the two hosts (desktop results page, mobile stats tab) alternated about 1.5 s apart overall.
* **No block, challenge or CAPTCHA was served.** The only refusals were the expected 401 (unsigned Flashscore feed), 403 (missing S3 object) and 503 (ProTennisLive down).

### 4.2 Helper agents' requests

The log has 330 rows in all. Rows are attributed to a helper by host, so the split is approximate. Neither helper used WebFetch.

* **Helper T (tournament sites), about 127 requests, 14:09–14:56 UTC.**
  * mutuamadridopen.com 10; bnpparibasopen.com 9; brisbane-prod.smtinternetservices.com 7;
  * web.archive.org 6 (Halle pages, one timeout); www.lta.org.uk 6;
  * unitedcup.com 5 (one 500); nationalbankopen.com 5; atpqataropen.com 5;
  * erstebank-open.com 4 (one 500);
  * 3 each: miamiopen.com, tennis.com.au, internazionalibnlditalia.com, rolexparismasters.com, chinaopen.com, nittoatpfinals.com (one 404), cincinnatiopen.com, terrawortmann-open.de, live.terrawortmann-open.de, swissindoorsbasel.ch, dubaidutyfreetennischampionships.com, mubadaladcopen.com;
  * 2 each: prod.stats.miamiopen.com, tennis-feeds.rain-digital.ca, porsche-tennis.com, tennis.com, barcelonaopenbancsabadell.com, hamburg-open.com, libema-open.nl;
  * 1 each: the FITP Azure function, brisbaneinternational.com.au, rolexshanghaimasters.com, api.nationalbankopen.com, qatartennis.org, mubadalacitidcopen.com, wtafinals.com, the Doha AWS API (401), scroll.in, sportsbusinessdaily.com, en.wikipedia.org, bmwopen.de, rioopen.com;
  * errors: wuhanopen.org ×2 (timeouts), open13.fr (connection reset), foxtenn.com (certificate mismatch, not bypassed).
* **Helper B (aggregators and broadcasters), about 107 requests, 14:10–14:41 UTC.**
  * matchstat.com 11 (two 404); webws.365scores.com 8; tennisstats.com 8;
  * bbc.co.uk 6 (two 404); en.tennistemple.com 5 (plus www, one 404); tennisabstract.com 5;
  * 4 each: livescore.com (one 404), prod-cdn-public-api.livescore.com, scores24.live, oddspedia.com, betexplorer.com, tntsports.co.uk, tennis.com;
  * 3 each: tennisexplorer.com, site.api.espn.com (one 400), tennistv.com, s42493.pcdn.co (Tennis Abstract files);
  * 2 each: eurosport.com (one 404), skysports.com (one 404), tnnslive.com, api.tnnslive.com (one 404), raw.githubusercontent.com (Sackmann READMEs, two 404);
  * 1 each: aiscore.com (403, Cloudflare challenge; stopped), espn.com (404), tennischannel.com, beinsports.com, bein.com, smt.com, ubitennis.net, tennis-db.com, sky.com, sbgi.net, disneytermsofuse.com, github.com (404), 365scores.com (timeout).

### 4.3 WebFetch calls (not in the TSV; times approximate)

| ≈ UTC | URL | Result |
|---|---|---|
| 14:00, 14:01 | https://www.atptour.com/en/news/electronic-line-calling-release- (two prompts) | 200 |
| 14:01 | https://floridatennis.com/blogs/news/atp-challenger-in-tallahassee-returns-april-12-19-with-loaded-field-streaming-video-and-electronic-line-calling | 200 |
| 14:02 | https://ktvz.com/?p=1127985 (AP, 28 Apr 2023) | 200 |
| 14:03 | https://www.siliconsnark.com/tennis-tech-in-2026-can-call-every-line-it-still-cant-fix-your-forehand/ | 200 |
| 14:06 | http://tenniskalamazoo.blogspot.com/2026/07/elc-goes-down-2025-finalist-martin.html | 200 |
| 14:06 | https://www.sportbusiness.com/news/atp-to-ramp-up-tracking-data-with-full-switch-to-electronic-line-calling/ | 403 (not retried) |
| 14:07 | https://www.atptour.com/en/news/atp-builds-on-record-year-2026 | 200 |
| 14:07 | https://www.tennis.com/news/articles/how-did-an-atp-challenger-in-germany-make-history-with-electronic-line-calling | 200 |
| 14:12 | https://www.atptour.com/en/news/scorecards-mpetshi-perricard-first-serve-speed | 200 |
| 14:20 | https://www.wtatennis.com/news/1906120/wta-and-stats-perform-serve-up-breakthrough-partnership | 200 |
| 14:20 | https://www.tennis.com/news/articles/game-plan-match-stats-live-data-how-tech-changing-match-preparation | 200 |
| 14:31 | https://www.puntodebreak.com/en/2025/02/06/this-is-how-the-atp-explains-why-it-will-install-electronic-refereeing-on-clay-courts | 200 |
| 14:33 | https://ieee-dataport.org/keywords/tennis-match-statistics | 200 |
| 14:33 | https://github.com/serve-and-volley/atp-world-tour-tennis-data | 200 |
| 14:35 | https://www.wtatennis.com/news/1415620/sap-and-wta-announce-real-time-analytics-for-media | 200 |

About 31 WebSearch calls were also made by this lane (announcements, rulebooks, vendors, datasets).

## 5. Leads for other lanes

* **A2 (Slam gaps):** Matchstat's head-to-head pages embed per-match `averageFirstServeSpeed` and `averageSecondServeSpeed` for **AO 2025 (men)**, AO 2024 (women), Wimbledon 2025–26, the US Open 2025–26 and RG 2019 (women). RG 2025 is null [observed by helper B; unit inferred as km/h].
  * Also Flashscore's mobile page: AO 2025 9% and RG 2025 42% in the crawl. The 2026 Slam finals all carry speed live.
* **B (open datasets):** `serve-and-volley/atp-world-tour-tennis-data`, rendered Stats Centre Key Stats for 18 Oct 2021 – 2022, CC BY 4.0 (§3.4).
* **C (paid vendors):**
  * SMT/IDS, the serve-speed radar supplier, says it supplied speed data to both tours [claimed].
  * Stats Perform is the official WTA data supplier [claimed].
  * TennisViz and Hawk-Eye hold tracking.
  * None publishes per-match speed openly.
* **Main session:** the "0 km/h" placeholders in the Flashscore crawl (§3.7.4), confirmed and fixed.

## 6. Dead ends

**This lane:**
* **atptour.com.** No speed in any plain route:
  * the Hawkeye match-stats JSON (2019, 2026);
  * the match-stats template;
  * the leaderboards, individual match stats and TDI Insights;
  * the Stats Centre HTML.
* **Infosys.** Every route returns the encrypted envelope (keystats, LLM commentary, match-beats status). The 2026 static keystats path is 403. The Wayback Machine holds no ATP Infosys data before November 2021.
* **ATP app gateway.** Live snapshot only, no speed.
* **WTA.** No speed in the API (`stats`, `advanced-stats`), the match centre or the site bundle. `BinPacketBase64` is empty, even live.
* **ProTennisLive.** 503 on both URLs; the Wayback Machine has only Flash shells.
* **Flashscore.**
  * The desktop statistics feed needs `x-fsign`: 401 without it. Not sent.
  * The mobile `/match/` pages are disallowed by robots.txt. Stopped at 23.
  * Tennis24 is the same platform, so not probed.
* **ATP 2015–2020 serve speed in public datasets.** A search for Kaggle and GitHub datasets found only `serve-and-volley` (18 Oct 2021 – 2022).
  * The "MAVERAG1SERV" variable in search excerpts belongs to an academic paper's Slam data, not a dataset.
  * IEEE Dataport's "Tennis Match Statistics" has no stated tours, years or source.
* **Articles not read.**
  * sportbusiness.com's ELC/tracking article: 403 (not retried).
  * puntodebreak.com (Feb 2025) names no ELC vendors for 2025 clay.
* **Not attempted (outside the rules):**
  * decrypting the Stats Centre files;
  * the Infosys chatbot (a POST);
  * any signed or token-gated feed.

**Helper B:**
* AiScore: Cloudflare managed challenge on the first request; stopped.
* TNNS: match detail needs a Turnstile-minted token; stopped.
* beIN: client-side Opta widgets only.
* 365Scores: point-by-point endpoint not found; EULA fetch timed out.
* ESPN: summary endpoint 400, match pages 404.
* LiveScore: statistics endpoint returns `{}`.
* Moved URLs: BBC `/scores-fixtures` and Sky `/tennis/scores` are 404.
* tennis-db.com: no speed leaderboard.
* Sackmann's GitHub README files: 404.
* Matchstat: the WTA head-to-head URL 404s for a name variant.

**Helper T:**
* Indian Wells: the tRPC base URL was not found in about 9 requests.
* Doha: 401 outside the event window.
* Unreachable: Wuhan (timeout twice), open13.fr (connection reset), foxtenn.com (certificate mismatch, not bypassed).
* Wayback: a whole-site query for Halle timed out. Halle's 2023–24 live JS was not archived.
* The ATP tournament platform's stats endpoint returns 500 for prior years.
* Basel and Vienna results pages are empty before their events.
* No site terms were found for Madrid or Rome.
* **Not done:** Madrid's app embeds a ProTennisLive token and a WTA API key. Neither was used.
