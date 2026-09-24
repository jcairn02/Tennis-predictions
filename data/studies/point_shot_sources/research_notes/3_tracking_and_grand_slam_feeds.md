# R3: Shot-level and tracking sources, and official-site match centres (men's tennis, 2019–2026)

Prepared 23 September 2026. I accessed every URL on that date. This is web research only: I did not sign up, log in, fill in forms, contact anyone or buy anything.

Evidence labels:
- **[observed]**: I fetched the page or data file and saw the content myself.
- **[provider claim]**: the organisation that runs or sells the source says it.
- **[third-party report]**: someone else reports it (press, blog, GitHub README, podcast).
- **"not stated"**: the source I read does not say.

Where I had to interpret something, it is marked **"Inference:"**. I kept these to a minimum.

Tier names used in the tables:
- **ITF main**: ITF M15/M25 main draw
- **ITF Q**: ITF qualifying
- **CH main**: ATP Challenger main draw
- **CH Q**: Challenger qualifying
- **ATP main**: ATP tour-level main draw, including Grand Slam main draws
- **ATP Q**: ATP tour-level qualifying at non-Slam events
- **GS Q**: Grand Slam qualifying
- **DC**: Davis Cup

"S" means shot or tracking data. "P" means point-level data.

---

## 0. Method and limitations (read first)

- **Web-search budget ran out part-way through.** The session hit its limit of 200 WebSearch calls, which is shared with other agents. After that I could only fetch URLs I already knew or could find in pages I had read. These items could not be followed up:
  - Tennis Australia's Game Insight Group
  - Details of ELC at Davis Cup
  - A full list of Challengers using ELC
  - Tennis Canada's PlayReplay scope
- **Bot protection was respected, never bypassed.** Where a site blocked access, I recorded it and moved on:
  - itftennis.com HTML pages sit behind Imperva/Incapsula. An automated request gets a 1,045-byte challenge page with `X-Iinfo` and `visid_incap_…` headers [observed]. ITF **PDFs** did download.
  - The Infosys match-centre APIs used by ATP, the Australian Open and Roland-Garros return CloudFront `403 … Request blocked` [observed].
  - atptour.com sends plain `curl` requests a Cloudflare "Just a moment..." challenge page [observed]. Some atptour.com JSON did come back through the WebFetch tool.
  - These sites also failed:
    - foxtenn.com: TLS certificate does not match the domain
    - baseline.vision: connection refused (the right domain is baselinevision.com, which worked)
    - tennisdata.com: 403
    - tennis.com.au: 403
    - pif.gov.sa and businesswire.com: 403
    - gamesetmap.com: expired certificate
- **Small, single-match checks only; nothing bulk-downloaded.**
  - US Open: qualifying draw feeds for 2022–2026 and 7 single-match files.
  - Wimbledon: 5 single-match files.
  - Australian Open: 3 match-centre files and 2 results files.
  - Roland-Garros: 1 match page.
  - atptour.com: 6 match-statistics files.
  - The files are saved in the scratchpad next to this report (`uso_*.json`, `wim_*.json`, `ao_*.json`, `rg_QM025.html`).
- **I did not decode anything that was encrypted or encoded.**
- **PDF text was extracted with a copy of `pypdf` installed only into `scratchpad/pylibs`.** It was run through the project's `./python.sh` interpreter. The project's conda environment was not changed.

---

## 1. Bottom line

1. **No public shot or tracking data was found for ITF M15/M25 or ATP Challenger matches in 2019–2026.**
   - Electronic line calling (ELC) at these tiers is patchy, and nobody publishes its tracking data.
   - For ITF events, the regulations give the ITF's licensing arm (ITFL) exclusive data rights, including tracking ("Level 3" data).
   - The same regulations restrict how ELC and player-analysis data may be used, and they bar betting use.
2. **ATP Challenger: ELC is still optional in 2026.**
   - The 2026 ATP Rulebook requires 3–7 human line judges per Challenger match. Live ELC is mandatory only at ATP Tour events.
   - Some Challengers do use ELC:
     - Heilbronn 2024 (Foxtenn, all courts)
     - All five Canadian Challengers in 2026 (Bolt6)
     - Lincoln, USA, 2026 (Bolt6)
3. **atptour.com Challenger match pages give box scores only.** For main-draw and qualifying matches (2019 and 2025 checked), the JSON holds serve, return and point totals, plus umpire name and match duration. It has no point-by-point, rally or tracking fields [observed].
   - The richer "Stats Centre" views (Court Vision, Rally Analysis, Stroke Analysis, MatchBeats) come from Infosys. Their endpoints are blocked, and a GitHub scraper reports that the Court Vision data is encrypted.
   - The atptour.com terms prohibit "Systematic retrieval of data" and any "gambling or wagering" use.
4. **ITF M15/M25 ELC only starts in 2026.**
   - The USTA uses PlayReplay on every match court of every USTA Pro Circuit hard-court ITF event for five years from 2026.
   - Germany's federation (DTB) ran pilots at ITF events in Bavaria in 2026.
   - An ITF "Silver" tier of ELC systems, intended for the World Tennis Tour, has existed since July 2025.
   - Nothing covers 2019–2025.
5. **The one real point-by-point route at Challenger level is a commercial licence.** Tennis Data Innovations (TDI, owned by ATP and ATP Media) and Sportradar supply an umpire-scored feed covering "ATP Tour and ATP Challenger Tour events … including all qualifying and doubles matches".
   - This is point-level scoring, not shot data. It is aimed at betting and media customers, and no price is published.
   - Whether tracking data exists at Challengers is not stated.
6. **The strongest positive finding is outside Challenger/ITF: Grand Slam qualifying (about 5% of the reference matches).** The official Grand Slam scoring feeds are public, unauthenticated JSON, and I observed point-level data for qualifying:
   - **US Open, 2022–2026.** Every point carries Unix start and end times, serve speed, serve width and depth, return depth and distance run. Rally count is filled in for the 2025–2026 samples but is 0 in the 2022–2024 samples.
     - Coverage is partial before 2025. The draw feed marks each match with a `statsLevel` code, and the share of qualifying matches marked "H" was 38% (2022), 37% (2023), 37% (2024), 60% (2025) and 99% (2026).
     - In the matches I sampled, the "S"-level matches had empty point histories.
   - **Wimbledon, 2025–2026.** Qualifying at Roehampton got ELC for the first time in 2025. All 2026 qualifying matches are "H"-level, and sampled matches have full point data. The 2024 feeds did not respond.
   - **Australian Open, 2026 only.** The public match-centre JSON for qualifying has key stats (including fastest and average serve speed), winners and errors by stroke type, and a text commentary for every point with a timestamp. The API returns "No Results" for 2025.
   - **Roland-Garros.** Qualifying pages carry box-score statistics. The point-level (Infosys MatchBeats) API is blocked.
7. **Rights are unresolved for all official feeds.** I could not retrieve the website terms for any of the four Slams. Data being publicly reachable does not mean it is licensed for storage, model training or betting.

---

## 2. Electronic line calling and tracking by men's tier (answer to scope item 1)

| Tier | ELC status, 2019–2026 | Is tracking produced? | Is it available to outsiders? |
|---|---|---|---|
| ATP Tour main | Voluntary before 2025. Live ELC mandatory on all courts from 2025 (ATP 2023; 2026 Rulebook). | Yes: ATP says it gives "comprehensive player and ball tracking across the whole Tour". | Only box scores are public. Stats Centre / Court Vision is blocked, reportedly encrypted, and restricted by the terms. Licensing is through TDI. |
| ATP Tour qualifying | Live ELC "from the first day of qualifying … on all match courts" (2026 Rulebook). | Yes (provider claim). | Nothing public observed. |
| Grand Slam qualifying | AO and US Open: Hawk-Eye Live on all competition courts since 2021. AO has used Bolt6 since 2025. Wimbledon qualifying: ELC from 2025. Roland-Garros: human line judges through 2026. | Yes: serve speed, depth and distance appear in the public feeds. | Public JSON: US Open 2022–2026, Wimbledon 2025–2026, AO 2026 (current year only). Rights not retrieved. |
| Challenger main and qualifying | Not mandatory in 2026: line judges required, review ELC allowed. Known cases: Heilbronn 2024 (Foxtenn), 5 Canadian events in 2026 (Bolt6), Lincoln 2026 (Bolt6). | Per system, at those events (e.g. Foxtenn "match analytics and statistics"). | No public tracking. atptour.com box scores only. |
| ITF M15/M25 main and qualifying | Allowed with ITF approval. USTA hard-court ITF events use PlayReplay from 2026. DTB pilots in 2026. | PlayReplay tracks "every ball and player". | No. ITFL owns data rights, analysis data is for internal coaching only, and betting use is barred. |
| Davis Cup | ITF says top-tier ("Gold") systems are intended for Davis Cup. Specifics not retrieved. | not stated | not stated |

**Evidence:**
- ATP Tour **[provider claim]**, https://www.atptour.com/en/news/electronic-line-calling-release-april-2023 (28 April 2023):
  - "The ATP has announced Tour-wide adoption of Electronic Line Calling Live (ELC Live) from 2025."
  - "…for players competing in both main draw and qualifying events."
  - "All-court ELC Live coverage will also deliver comprehensive player and ball tracking across the whole Tour, leading to an unprecedented level of data for player-performance analysis and the development of new statistics."
- ATP Rulebook 2026 **[observed text]**, https://www.atptour.com/-/media/files/rulebook/2026/2026-rulebook_19dec25.pdf:
  - "The use of the Live ELC system replacing line umpires is mandatory at all ATP Tour events."
  - "2) ATP Challenger Tour Tournaments — Tournaments must hire officials as specified below: For Challenger 50 and 75 events on clay court, a minimum of three (3) Line Umpires shall be provided…"
  - "For Challenger 175 events, a minimum of five (5) Line Umpires shall be provided for every qualifying match. A minimum of seven (7) line umpires shall be provided for every main draw match."
  - "A. Electronic Review (Review ELC) - applicable to ATP Challenger Tour only. The use of an approved electronic system for reviewing line calls and/or overrules is authorized for use at ATP events."
  - For ATP Tour events: "The system must be available from the first day of qualifying through the end of the event on all match courts." (the same text is in the Chapter 6 PDF, https://www.atptour.com/-/media/files/rulebook/2026/2026-rulebook-chapter-6_facilities_19dec25.pdf)
- ATP **[provider claim]**:
  - Q1 2025 "ATP Business Insider" (https://new.express.adobe.com/webpage/81qRcSpow6tYJ): "We broke new boundaries this quarter with the introduction of Live Electronic Line Calling across all Tour events."
  - https://www.atptour.com/en/news/atp-builds-on-record-year-2026 (8 January 2026): "Live Electronic Line Calling will continue to be deployed across all ATP Tour events."
- Challenger examples:
  - Heilbronn **[third-party report]**, https://www.tennis.com/news/articles/how-did-an-atp-challenger-in-germany-make-history-with-electronic-line-calling (30 May 2025):
    - "The world premiere of Electronic Live Calling on clay took place exactly one year ago at the Neckarcup ATP Challenger in Heilbronn."
    - "The Barcelona-based company FOXTENN provided the technology, which was implemented across all courts for the entire week"
  - Canada **[provider claim]**, https://www.tenniscanada.com/news/canadian-events/2026/tennis-canada-confirms-full-2026-national-event-calendar (19 May 2026): "Through a partnership with Bolt6, electronic line-calling (ELC) technology will be implemented at all five events" (the five ATP Challengers).
  - Lincoln **[provider claim]**, https://www.usta.com/en/home/stay-current/missourivalley/nebraska/lincoln-challenger-pro-circuit-2026.html (29 May 2026): "The electronic line-calling system is a unique addition, as not all Pro Circuit tourneys utilize this growing technology."
- Grand Slams:
  - AO and US Open **[third-party report]**, https://www.svgeurope.org/blog/headlines/wimbledon-to-adopt-sony-hawk-eyes-live-electronic-line-calling-for-2025/ (10 October 2024): "the Australian Open and US Open have each used Hawk-Eye's Live ELC system on all competition courts since 2021"
  - Wimbledon, same article: "These changes will see the introduction of Electronic Line Calling technology at the Wimbledon Qualifying Competition venue for the first time."
  - AO **[provider claim]**, https://ausopen.com/articles/news/ao-ventures-announces-first-investments-backing-innovation-ao-and-beyond (27 January 2026): "Since 2025, Bolt6 has delivered the electronic line calling technology for the Australian Open."
  - Roland-Garros **[third-party report]**, https://www.flashscore.com/news/tennis-french-open-atp-singles-french-open-set-to-continue-with-line-judges-for-2026-tournament/t8RZX3Zj: "For the next Roland Garros, the FFT will continue to highlight the excellence of French refereeing, recognised throughout the world"
- ITF World Tennis Tour:
  - 2026 Regulations **[observed text]**, https://www.itftennis.com/media/15546/2026-wtt-regulations.pdf:
    - "The use of Electronic Line-Calling (ELC) systems is permitted at a Men's WTT Tournament, subject to the following conditions and requirements"
    - "The ELC system must have been classified by the ITF and approved by the ITF for use at the tournament in question."
  - ITF tiers **[third-party report]**, https://www.espn.com/tennis/story/_/id/45802019/itf-introduces-tiered-system-expand-electronic-line-calling (23 July 2025): Gold is "used at elite competitions like the Grand Slam tournaments, WTA and ATP tours, Billie Jean King Cup and Davis Cup". Silver is for "second-tier competitions such as the ITF World Tennis Tour".
  - USTA **[provider claim]**, https://www.theglobeandmail.com/investing/markets/markets-news/Newswire.ca/1614628/usta-to-feature-playreplay-electronic-line-calling-at-all-usta-pro-circuit-men-s-and-women-s-itf-world-tennis-tour-hard-court-events-over-the-next-five-years/ (30 April 2026): "The USTA will utilize the ELC system developed by tennis technology company PlayReplay … on every match court of a USTA Pro Circuit hard-court ITF World Tennis Tour event for the next five years."
- Cost context **[third-party report]**, https://www.ubitennis.net/2021/01/tennis-and-data-methods-used-to-collect-information-and-how-much-each-one-cost/ (23 January 2021), estimated cost per court per week:
  - Hawk-Eye: "Estimated cost: 60-70 thousand euros per court on a weekly basis"
  - FOXTENN: "less than 50 thousand euros per court on a weekly basis"
  - FlightScope: "35-40 thousand euros per court on a weekly basis"

---

## 3. Source-by-source

### A. Official match centres and scoring feeds

#### A1. US Open: IBM SlamTracker scoring feeds (usopen.org)

- **URLs**
  - Draws: `https://www.usopen.org/en_US/scores/feeds/{year}/draws/MQ.json` (men's qualifying) and `…/MS.json` (men's main draw)
  - Point history: `…/{year}/slamtracker/history/{matchId}C.json`
  - Match statistics: `…/{year}/matches/complete/{matchId}.json`
  - Site configuration: `https://www.usopen.org/en_US/json/gen/config_web.json`
- **Data unit:**
  - Per point: score state, server, serve number, serve speed, serve width and depth, return depth, rally count, distance run, kick height, winner/error flags, winner shot type, a one-sentence description, and Unix start and end times.
  - Per match: base, serve, return and rally statistics; serve direction by deuce/ad court; distance run by set.

| Tier | S | P | Earliest year |
|---|---|---|---|
| ITF main / ITF Q / CH main / CH Q / ATP Q / DC | no (not covered) | no | n/a |
| ATP main (US Open main draw) | derived tracking only (speeds, depths, distance); no ball coordinates | yes | 2022 at this path; 2025 and 2026 checked (126/127 and 127/127 matches "H") |
| GS Q (US Open) | same as above | yes, for "H"-level matches | 2022 (the 2019 and 2021 feed paths return 404) |

- **Historical access:** public, unauthenticated JSON [observed].
- **Timestamps:** `EpochTimeStart` and `EpochTimeEnd` for every point (Unix seconds); an `epoch` per match in the draw feed.
- **Price:** none (public feed).
- **Licence/terms:** usopen.org terms not retrieved (every probed URL returned the same 4 KB JavaScript shell). The config contains `"useEncoded": true`. The files I fetched were plain JSON.
- **Evidence [observed]:**
  - Share of `statsLevel` codes in men's qualifying:
    - 2022: `{'S': 69, 'H': 43}`
    - 2023: `{'H': 41, 'S': 71}`
    - 2024: `{'H': 41, 'S': 71}`
    - 2025: `{'H': 67, 'S': 45}`
    - 2026: `{'H': 111, 'N': 1}` (the one "N" is a walkover)
  - 2025 qualifying Round 3, match 11306 (Court 11, M. Huesler vs Z. Svajda):
    - 112 points
    - Serve speed filled on 105 points, `RallyCount` on 106, `ServeWidth` on 112
    - Sample values: `P1DistanceRun` "16.626,54.547"; `EpochTimeStart` "1755882187"
    - Sample sentence: "M. Huesler fails to convert the break point with a forehand forced error"
  - 2026 qualifying match 11102 (Court 14): 105 points, 96 with serve speed, 73 with rally count.
  - Earlier samples:
    - 2022 match 11107: 171 points, 157 with speed, rally 0 on every point
    - 2023 match 11101: 149 points, rally 0
    - 2024 match 11101: 157 points, rally 0
  - "S"-level matches had no point history: 2024 match 11102, and 2025 match 11101 (whose match-statistics file says `"statsLevel": "S"` although the draw feed says "H"). Their files contain only "Players arrive on court." and "Players warming up."
  - Even "S"-level match statistics include serve speeds and distance run, e.g. 2025 match 11101: `"f_srv_a_spd": ["189 KMH", "118 MPH"]` and `"distance_run": {"match": {"team_1": ["477.0 m", …]}}`.
  - The config shows `"matchHistory": {"path": "/en_US/scores/feeds/2026/slamtracker/history/<matchId>C.json"`, `"matchDistance"`, and the tooltip `"shot_quality": "The quality of the player's four main shots on a 0-10 scale"`.
- **Evidence [provider claim]:** https://www.ibm.com/new/product-blog/inside-the-ibm-architecture-that-powers-fan-engagement-at-the-us-open (3 June 2026): "More than 7 million data points, with each point producing more than 150 variables", including "serve speed, match statistics, aces, double faults, unforced errors, rally length, distance run…"
- **Unknowns:**
  - The meaning of the `statsLevel` codes H, S and N is not stated.
  - Whether 2019–2021 data exists at other paths.
  - Terms of use.
  - Whether ball or player coordinates exist anywhere; not seen in the feeds.
- **Judgement: Challenger/ITF = none.** The feed does not cover those tiers.
- **Secondary judgement: US Open qualifying = high** for 2025–2026. It is partial for 2022–2024 (about 37–38% of matches, rally count missing), and legal rights still have to be cleared.

#### A2. Wimbledon: IBM SlamTracker feeds (wimbledon.com and 2025.wimbledon.com)

- **URLs**
  - 2026 draw: `https://www.wimbledon.com/en_GB/scores/feeds/2026/draws/QS.json` ("Gentlemen's Qualifying Singles")
  - 2025 feeds live on the `2025.wimbledon.com` subdomain, e.g. `https://2025.wimbledon.com/en_GB/scores/feeds/2025/slamtracker/history/{matchId}C.json` and `…/matches/complete/{matchId}.json`
  - 2026 point history: `https://www.wimbledon.com/en_GB/scores/feeds/2026/slamtracker/history/{matchId}C.json`
- **Data unit:** the same per-point and per-match schema as the US Open.

| Tier | S | P | Earliest year |
|---|---|---|---|
| ITF / CH / ATP Q / DC | no | no | n/a |
| ATP main (Wimbledon main draw) | derived tracking (speed, depth, distance) | yes | 2025 checked (match 1101: 155 points, 146 with speed, 146 with rally count) |
| GS Q (Wimbledon) | derived tracking | yes | **2025.** 2024 not reachable: the www path returns 403 and `2024.wimbledon.com` does not resolve. |

- **Historical access:** public JSON for 2025 and 2026 [observed]. Earlier years were not accessible.
- **Timestamps:** per-point `EpochTimeStart` and `EpochTimeEnd`; per-match `epoch`.
- **Price:** none.
- **Licence/terms:** not retrieved (the candidate terms URLs redirect to `/en_GB/about`).
- **Evidence [observed]:**
  - 2025 qualifying draw: every match I read had `"statsLevel": "H"`. Match 11101 was "R: Show Court 1" with `"epoch": "1750682849000"`.
  - Match 11101 (Fucsovics vs Rodionov): 116 points, with serve speed on 113, rally count on 113, `ServeWidth` on 115, `ReturnDepth` on 101, `P1DistanceRun` on 116. `KickHeight` is "0.0,0.0" throughout.
  - Match 11137 (R: Court 14): 257 points, 252 with serve speed, 250 with rally count.
  - 2026 qualifying draw: 112 matches, all `H`. Match 11101 (R: Court 2): 197 points, 185 with serve speed.
- **Evidence [third-party report], ELC at the qualifying venue:** see section 2 (SVG Europe).
- **Unknowns:** the meaning of `H`; terms; whether older years are archived elsewhere.
- **Judgement: Challenger/ITF = none.**
- **Secondary judgement: Wimbledon qualifying 2025–2026 = high**, subject to clearing rights.

#### A3. Australian Open: match centre (prod-scores-api.ausopen.com, with Infosys)

- **URLs**
  - Results: `https://prod-scores-api.ausopen.com/year/{year}/period/Q/day/{d}/results`
  - Match centre: `https://prod-scores-api.ausopen.com/match-centre/{matchId}`. The match page gives this as `dataUrl`; there is no year in the path.
  - Match pages look like `https://ausopen.com/match/2026-yoshihito-nishioka-vs-nerman-fatic-mq129`.
  - Infosys Court Vision (blocked): `itp-ao-sls.infosys-platforms.com/prod/api/court-vision/...`
- **Data unit:**
  - Key statistics per set (aces, double faults, winners, unforced errors, "Fastest serve", "1st Serve Average", "2nd serve average")
  - Serve statistics
  - Rally statistics: forehand/backhand winners and unforced errors by shot type (groundstroke, volley, approach, passing, lob, overhead, drop)
  - A commentary entry for every point, with a Unix timestamp, e.g. "N. Fatic loses the point with a Backhand Unforced Error"

| Tier | S | P | Earliest year |
|---|---|---|---|
| ITF / CH / ATP Q / DC | no | no | n/a |
| ATP main (AO main draw) | derived only (serve speeds) | yes (commentary) | 2026 observed (MS701 file exists) |
| GS Q (AO) | derived only | yes (text per point, with timestamp) | **2026 only** through this API. It returns "No Results" for 2025. |

- **Historical access:** public JSON for the current year only [observed]. The deeper Infosys data (Court Vision / MatchBeats) is blocked with a 403.
- **Timestamps:** per-point `timestamp` (Unix); `date` and `actual_start_time` (local time) per match.
- **Price:** none.
- **Licence/terms:** website terms not retrieved. The footer points to the Tennis Australia "Conditions of Use", which returned 403. The `/ao-terms-conditions` link is the ticket and entry conditions PDF, not the website terms. It forbids taking out of the grounds "any match scores or related statistics or data for any commercial, betting or gambling purpose" [observed text, PDF].
- **Evidence [observed]:**
  - 2026 qualifying match MQ129 (Kia Arena): 88 point-result entries, all with timestamps, e.g. `"timestamp": 1768176701, "commentary": "Y. Nishioka wins the point with a Forehand Winner"`. Key stats include `Fastest serve` (193 and 203 km/h) and `1st Serve Average` (167 and 186 km/h).
  - Match MQ109 (Court 5, an outside court): 119 point-result entries; fastest serves 206 and 186.
  - 2025 qualifying results: `{"error":{"heading":"No Results","description":"No scores are available. Please check back at a later time."}}`
- **Evidence [provider claim]:**
  - https://ausopen.com/visit/tournament-info/electronic-review: "Bolt6 delivers fast, trusted Electronic Line Calling across every Australian Open match court".
  - Infosys ingests "Scoring, statistics, player position, and ball tracking data" (AWS/Infosys blog, 1 June 2022, https://aws.amazon.com/blogs/media/how-infosys-reimagines-the-game-of-tennis-using-aws/).
- **Unknowns:** whether AO 2019–2025 data is archived anywhere public; the content of the Infosys Court Vision data for qualifying; terms.
- **Judgement: Challenger/ITF = none.**
- **Secondary judgement: AO qualifying = medium.** Only the current year is served, so it would have to be captured each January. There is no ball-tracking detail beyond serve speed.

#### A4. Roland-Garros: Infosys match centre (rolandgarros.com)

- **URLs**
  - Match pages: `https://www.rolandgarros.com/en-us/matches/2025/QM025` (men's qualifying Round 3, Møller vs Gigante)
  - Infosys API (blocked): `itp-rg-sls.infosys-platforms.com/prod/api/court-vision/...`
- **Data unit:** a box score embedded in the page. Point-level data (MatchBeats) and Court Vision come through Infosys.

| Tier | S | P | Earliest year |
|---|---|---|---|
| ITF / CH / ATP Q / DC | no | no | n/a |
| ATP main (RG main draw) | unknown (API blocked) | unknown (API blocked) | not stated |
| GS Q (RG) | unknown | claimed yes (2019), not verifiable | 2019 claim |

- **Historical access:** the 2025 qualifying page is public with box-score labels [observed]; the point data API is blocked.
- **Timestamps:** not observed.
- **Price:** none.
- **Licence/terms:** not retrieved (the candidate URLs timed out with HTTP 408).
- **Evidence [observed]:** the QM025 page embeds `"Statistics","aces","3","double faults","5","first serve","win on 1st serve","win on 2nd serve","net points won","break points won","receiving points won","winners","14","unforced errors","total points won"`. The Infosys endpoint returns 403.
- **Evidence [provider claim]:** https://www.rolandgarros.com/en-us/article/stats-infosys-roland-garros-2019 (21 May 2019): "The point-by-point moving-data feature will be available on rolandgarros.com throughout qualifying and the main draw."
- **Evidence [third-party report]:** https://github.com/glad94/tennis-web-scraping says the Infosys Court Vision "raw data is encrypted" and that the author could "extract and decrypt the actual raw court vision data".
- **Unknowns:** whether qualifying courts have tracking at all, given RG has no ELC.
- **Judgement: Challenger/ITF = none. Secondary judgement: RG qualifying = low.**

#### A5. atptour.com scores and statistics (including the Infosys "Stats Centre")

- **URLs**
  - Results: `https://www.atptour.com/en/scores/archive/heilbronn/460/2025/results` (links like `/en/scores/stats-centre/archive/2025/460/ms001` and qualifying `/qs008`)
  - Statistics JSON: `https://www.atptour.com/-/Hawkeye/MatchStats/Complete/{year}/{eventId}/{matchId}`
  - Infosys endpoints listed by a scraper (https://github.com/glad94/infotennis/blob/main/config.yaml):
    - `https://itp-atp-sls.infosys-platforms.com/static/prod/court-vision/%(year)s/%(tourn_id)s/%(match_id)s/data.json`
    - `…/rally-analysis/…`
    - `…/stroke-analysis/v2/…`
    - `…/stats-plus/…/keystats.json`
  - A second scraper (https://github.com/glad94/tennis-web-scraping/tree/main/api-info) also lists `/prod/api/match-beats/data/year/#year/eventId/#eventId/matchId/#matchId`.
- **Data unit:** a per-match box score (serve, return and point totals, by set), plus court, umpire name, `MatchTime` and `IsQualifier`. The Infosys Stats Centre adds Court Vision (ball trajectories), Rally Analysis, Stroke Analysis and MatchBeats for tour events.

| Tier | S | P | Earliest year |
|---|---|---|---|
| ITF main / ITF Q | not observed on atptour.com | not observed | n/a |
| CH main | no (public) | no: box score only | 2019 observed (Heilbronn 2019 final) |
| CH Q | no | no: box score only | 2025 observed (Heilbronn QS008) |
| ATP main | yes via Infosys Court Vision at "more than 60 ATP Tour events each season" (claim); endpoints blocked | MatchBeats point-by-point (claim); blocked | 2021 per third party ("from Antwerp 2021 onwards") |
| ATP Q | not observed (2025 Indian Wells QS001 returned empty) | not observed | unknown |
| GS Q | no | no | n/a |
| DC | unknown | unknown | not stated |

- **Historical access:** public JSON for box scores [observed]. The Infosys point and tracking data is blocked (CloudFront 403 [observed]) and reportedly encrypted.
- **Timestamps:** none observed beyond `MatchTime` (duration) and `DateSeq` (meaning not stated).
- **Price:** none.
- **Licence/terms [observed]**, https://www.atptour.com/en/terms-and-conditions:
  - "You may use the Website and/or Content solely for your own individual non-commercial, entertainment and informational purposes."
  - "Systematic retrieval of data or other Content from the Website, including but not limited to scores, statistics, and/or rankings, whether to create or compile, directly or indirectly, a collection, compilation, database, or directory, is prohibited"
  - "Any other use, including for any commercial, gambling or wagering purposes, is strictly prohibited"
  - Machine learning or AI training: not stated. No effective date is given.
- **Evidence [observed]:**
  - 2025/460/MS001 returns `"EventType": "CH"`, `"TournamentName": "Neckarcup 2.0"`, with fields like `"FirstServePointsWon"`, `"BreakPointsConverted"` and `UmpireFirstName`. It has no speed, rally, shot or distance fields.
  - 2025/460/QS008 (second qualifying round, Wiskandt vs Maestrelli) is populated.
  - 2019/460/MS001 is populated (e.g. `"Aces":{"Number":3,…}`).
  - The Indian Wells 2025 final has the same box-score schema.
- **Evidence [provider claim]:** https://www.prnewswire.com/news-releases/atp-and-infosys-launch-revamped-stats-center-to-bring-fans-closer-to-the-game-through-digital-innovation-301394949.html (7 October 2021): MatchBeats is "Point-by-point analysis studying shot speeds, rally lengths and auto generated insights", across "more than 60 ATP Tour events each season".
- **Evidence [third-party report]:** https://github.com/glad94/infotennis README: "Match Data can only be scraped for matches from Antwerp 2021 onwards." Rally Analysis, Stroke Analysis and Court Vision are available "if available".
- **Unknowns:**
  - Whether the Stats Centre shows Court Vision for Challenger events that have ELC, or for ATP qualifying from 2025. I could not render the page, and the API is blocked.
  - Whether atptour.com has any point-by-point view for Challengers. None was seen in the JSON.
- **Judgement: low.** Challenger pages give box scores only, the terms forbid systematic retrieval and betting use, and the tour-level tracking views are blocked and encrypted.

#### A6. ATP Tennis IQ (TDI, TennisViz, PIF)

- **URLs:**
  - https://www.atptour.com/en/news/atp-tdi-unveil-tennis-iq-analytics-platform (25 September 2023)
  - https://www.atptour.com/en/news/atp-pif-tennis-iq-2025-announcement (22 August 2025)
- **Data unit:** a platform for players and coaches: scouting, video analysis, wearables data, and metrics such as Shot Quality, In Attack and Steal Score.
- **Tiers:** users include ATP Tour and Challenger players. Which events' data it contains, by tier or year, is not stated.
- **Historical access:** no outside access. **Timestamps:** not stated. **Price:** not stated.
- **Evidence [provider claim]:**
  - 2023: "A brand-new performance analytics platform that democratises access to cutting-edge data and insights for players on the ATP Tour."
  - 2025: "The platform will empower around 2,000 players across the ATP Tour and ATP Challenger Tour…"; "Enhanced scouting and video tools to analyse opponents and match performance"; "Wearables integration to bring physical performance data into focus". Access also extends to "all ATP coach members".
- **Unknowns:** whether it holds Challenger tracking data or shot-level data; whether players can export data; the terms.
- **Judgement: none.** Only players and coaches can use it, and no third-party route is stated.

#### A7. Tennis Data Innovations (TDI) and Sportradar: licensing channel for ATP Tour and Challenger data

- **URLs:**
  - https://uk.linkedin.com/company/tennisdata
  - https://www.ubitennis.net/2024/02/exclusive-the-atp-tennis-data-and-its-growing-demand/
  - https://sportradar.com/content-hub/news/tennis-data-innovations-and-sportradar-team-up-to-expand-official-tennis-data-distribution/?lang=en-us
  - https://igamingbusiness.com/sports-betting/sportradar-tennis-data-streaming-deal-atp/
- **Data unit:** umpire-scored point-by-point data ("Level 1"), plus deeper data "including optical detections like Hawkeye and other providers". The tier split for the deeper data is not stated.

| Tier | S | P | Earliest year |
|---|---|---|---|
| CH main / CH Q | not stated | yes (umpire feed, "all qualifying") | not stated (TDI founded 2020) |
| ATP main / ATP Q | yes (Hawk-Eye / ELC; ATP claim) | yes | not stated |
| ITF / GS Q / DC | no (not TDI's rights) | no | n/a |

- **Historical access:** by licence only. **Timestamps:** not stated. **Price:** not published.
- **Licence:** a B2B commercial licence aimed at betting and media customers; the terms are not public.
- **Evidence [provider claim]:**
  - LinkedIn: TDI "was established in 2020 as a specialist commercial vehicle to manage data and streaming assets across the ATP Tour and ATP Challenger Tour."
  - Sportradar: "With scores delivered directly from the umpire's chair, the new feed provides full and uninterrupted coverage of ATP Tour and ATP Challenger Tour events across the season, including all qualifying and doubles matches" (no date shown on the page).
  - TDI's head of product in Ubitennis (5 February 2024): "We collect data point by point from the chair umpire, what we call 'level 1' data" and "various data sources beyond chair umpire data, including optical detections like Hawkeye and other providers". Also: "We work closely with our partner in this space, Sportradar, to surface additional statistics for betting clients."
- **Evidence [third-party report]:** iGB (12 December 2023) reports a multi-year deal covering betting and media data and streaming for the ATP Tour and Challenger Tour.
- **Unknowns:** whether tracking is available at Challengers; how far back the archive goes; whether academic or small-customer terms exist.
- **Judgement: low.** Challenger point-level data exists but only through a commercial, betting-oriented licence with no published price. Shot or tracking data at Challengers is not stated.

#### A8. itftennis.com and the ITF data framework (World Tennis Tour)

- **URLs:**
  - Tournament pages, e.g. https://www.itftennis.com/en/tournament/m25-winston-salem-nc/usa/2026/m-itf-usa-2026-003/: blocked by Imperva [observed]
  - Regulations: https://www.itftennis.com/media/15546/2026-wtt-regulations.pdf [observed text]
  - https://igamingbusiness.com/legal-compliance/itf-confirms-ban-on-live-scoring-data-for-15k-events/
  - https://www.tennis.com/news/articles/itf-stops-live-scoring-at-15k-events-part-of-anti-corruption-measures
- **Data unit:** the ITF defines four data levels:
  - Level 0: pre-match information
  - Level 1: umpire scoring
  - Level 2: "subjective statistical data … human logging process or computer vision"
  - Level 3: "player and ball tracking data"

| Tier | S | P | Earliest year |
|---|---|---|---|
| ITF M15 main and qualifying | no (except 2026 ELC pilots, see B5) | live scoring collection banned at $15k events (phased out by 2021) | not stated |
| ITF M25 main and qualifying | no (except 2026 USTA hard-court events, B5) | live data kept at $25k level (third party); not seen publicly | not stated |
| Other tiers | n/a | n/a | n/a |

- **Historical access:** unknown. The site is bot-protected, so I could not check whether match pages show statistics or point-by-point. The regulations mention that ITFL may provide "a live score centre of any Match … on the ITF website."
- **Timestamps:** not stated. **Price:** not stated.
- **Licence [observed, 2026 Regulations]:**
  - "ITFL owns, controls and shall have the exclusive right to exploit and/or to authorise third parties to exploit the Data Rights with respect to all Tournaments on a worldwide basis."
  - "Level 3 (L3) Data means … player and ball tracking data, generally captured via cameras in-Venue or computer-vision technology…"
  - "Unofficial Data means any Tournament Data which is obtained from sources, or via means, which ITFL has not authorised, including … television pictures, the internet, or otherwise."
  - On ELC and player-analysis data (Appendix G):
    - "PAT Data shall only be used for internal analysis and coaching purposes of the respective Player"
    - "no PAT Data or product derived therefrom shall be used or supplied to any third party for any purpose related to Betting"
    - "the ITF shall be free to use such PAT Data and authorise third parties to use such PAT Data for any purposes."
- **Evidence [third-party report]:**
  - iGB (17 December 2019): "…including a ban on the collection of live scoring data for minor events offering prize money up to $15,000." and "Further reductions will continue during 2020 and 2021, until it has been phased out completely." It also quotes the betting-integrity body IBIA: "Retaining live data for $25k matches…"
  - Tennis.com (17 December 2019): the ITF has a "more than $14 million annual agreement with Sportradar".
  - Whether that is still the ITF's data partner in 2025–2026 is not stated in what I read.
- **Unknowns:**
  - What itftennis.com match pages show, and from which year (blocked).
  - Whether M15 matches have any point-level record after 2021.
  - Who ITFL's current data licensees are.
- **Judgement: low.** Point-level data at M25 sits with ITFL and is licensed commercially. M15 live data was removed. Tracking only appears from 2026 at a few events, and the regulations restrict its use.

#### A9. daviscup.com

- **Status:** pages are client-rendered (Next.js). I found no match-statistics links or APIs in the HTML I downloaded [observed]. A search listing showed atptour.com carrying "Davis Cup Qualifiers 2nd Rd | Live Scores" (event 8097), but that page was not verified.
- **All fields:** not stated.
- **Judgement: none/unknown.** Davis Cup is under 1% of the reference matches.

### B. Electronic line calling and tracking systems

#### B1. Hawk-Eye (Sony), including Hawk-Eye Live and SkeleTRACK

- **URLs:**
  - https://www.hawkeyeinnovations.com/data
  - https://www.hawkeyeinnovations.com/news/4243365/skeletrack-a-new-era-of-data-in-tennis
  - Sony and ATP Media partnership press page (returned 403): https://pro.sony/ue_US/press/hawk-eye-atp-media-partnership
- **Data unit:** ball trajectories and player tracking. SkeleTRACK adds "29 skeletal points" and racket points.
- **Tiers:**
  - ATP main and ATP qualifying: S yes; mandatory all-court ELC from 2025. The supplier differs by event and is not stated per event.
  - GS qualifying: AO and US Open since 2021 (AO under Bolt6 from 2025); Wimbledon since 2025.
  - Challenger: no deployment found.
  - ITF: none found.
  - Davis Cup: not stated.
  - P: it produces point-level data wherever it runs.
- **Historical access:** licence through rights holders only.
- **Storage and sale:**
  - Hawk-Eye [provider claim]: it "delivers a range of data feeds to partners to enable and support their products, including live, delayed, play-by-play and summary feeds." Who owns the data is not stated on that page.
  - ATP data is sold by TDI (A7).
- **SkeleTRACK [provider claim]:** "debuted at the Laver Cup 2024 in September". Data "could be shared with players and coaches".
- **Price and terms for researchers:** not stated.
- **Judgement: none** for Challenger/ITF, because it is not deployed there.

#### B2. Foxtenn

- **URL:** https://www.foxtenn.com/ (TLS error, not reachable).
- **Data unit:** the ball bounce, from high-speed cameras and lasers.
- **Tiers:**
  - CH main and CH Q: S yes at some events (Heilbronn 2024: all courts, the first ELC on clay).
  - ATP: an ITF "Gold" system (third party); which events use it is not stated.
  - ITF and Davis Cup: not stated.
  - P: not stated.
- **Evidence [third-party report]:** tennis.com (30 May 2025): "FOXTENN's capabilities extend beyond just line calls. The system provides detailed match analytics and statistics, invaluable for television broadcasts, ATP officials, and the players themselves."
- **Archive, sale, price, terms:** not stated.
- **Judgement: low.** It is used at a few Challengers, but no data is offered to outsiders.

#### B3. Bolt6

- **URLs:**
  - https://www.bolt6.ai/
  - https://ausopen.com/visit/tournament-info/electronic-review
  - https://ausopen.com/articles/news/ao-ventures-announces-first-investments-backing-innovation-ao-and-beyond
- **Data unit:** ball and player tracking.
  - [third-party report] FutureSport Joe, 5 February 2026: "Cloud-based ball and player tracking powering electronic line calling, alt-casts, and real-time sports data…"
  - [provider claim] Bolt6 site: "Live ball tracking".
- **Tiers:**
  - GS qualifying (AO): S yes from 2025, "every Australian Open match court".
  - CH main and CH Q: S yes at 5 Canadian Challengers and Lincoln in 2026.
  - ATP: "grown its tennis footprint across the ATP and WTA Tours" (provider claim); events not stated.
  - ITF and Davis Cup: not stated.
  - P: not stated.
- **Evidence [provider claim]:** "A global leader in AI-powered officiating, broadcast, and data services." The AO says Bolt6 also helps "across video review, live stats…"
- **Archive, sale, price, terms:** not stated. Its ITF approval (live ELC on hard courts) was seen only as a search-engine snippet of an Imperva-protected ITF page.
- **Judgement: low.** It covers a few Challengers, only from 2026, with no data offering.

#### B4. FlightScope

- **Evidence:**
  - [third-party report] Ubitennis 2021: FlightScope uses "cameras, radars" and tablet systems for chair umpires, and provides "live scoring system and the line call system"; estimated €35–40k per court per week.
  - ITF approval as the third ELC system after Hawk-Eye and FOXTENN was seen only in a search-engine snippet of an Imperva-protected ITF page.
- **Tiers, archive, sale:** not stated.
- **Judgement: none/unknown.**

#### B5. PlayReplay

- **URLs:**
  - https://www.playreplay.io/
  - https://www.playreplay.io/news-list
  - https://www.usta.com/en/home/pro/pro-media---news/usta-to-feature-playreplay-electronic-line-calling-at-usta-pro-c.html
  - https://www.tennis.de/dtb/news/verband/verband--allgemein-/2026/dtb-testet-erstmals-electronic-line-calling--elc--bei-deutschen-.html
- **Data unit:** four cameras on the net posts giving 3-D tracking of ball and players: line calls, ball speed, spin, net clearance, player position. Players get match statistics in an app.

| Tier | S | P | Earliest year |
|---|---|---|---|
| ITF M15/M25 main and qualifying (USTA hard courts) | yes | system-level yes; outside access not stated | 2026 |
| ITF (Germany) | yes (pilots at "ITF-Turnieren in Bayern", junior and professional) | not stated | 2026 |
| CH / ATP / GS Q / DC | no | no | n/a |

- **Evidence [provider claim]:**
  - PlayReplay site: "unmatched real-time tracking of every ball and player, with performance data"; "Player App: receive detailed match statistics after your game!"; "Four cameras in total with two cameras mounted on each net post, allowing 3D tracking of the players, court & the ball at all times."
  - USTA: "The USTA Pro Circuit currently stages 67 men's and women's ITF World Tennis Tour hard-court events amid its 133 total tournaments in 2026."
  - PlayReplay news list: "World-First: PlayReplay Achieves ITF Silver Status for Real-Time Electronic Line Calling" (16 February 2026).
  - DTB: PlayReplay provides "wertvolle Spieldaten für Spieler und Trainer" ("valuable match data for players and coaches").
- **Licence:** at ITF events, the ELC data falls under ITF Appendix G: internal coaching use only, no betting, and the ITF may authorise third parties (see A8).
- **Price:** "pricing models for both lease and outright purchases"; figures not published.
- **Judgement: low.** The data only starts in 2026, is controlled by the ITF, and no outside access is stated. It could become a licensing conversation with ITFL.

#### B6. Zenniz

- **URLs:**
  - https://zenniz.com/smart-corner/zenniz-achieves-the-itf-silver-level-certification-as-the-only-all-in-one-smart-tennis-court-solution-in-the-world
  - https://zenniz.com/smart-corner/2025-highlights
- **Evidence [provider claim]:** "The certification is an official certification of the International Tennis Federation (ITF) for Electronic Line Calling." The named deployment is the Finnish National League.
- **Tiers:** no professional-tier deployments found for any men's tier in the population.
- **Archive, sale, price:** not stated.
- **Judgement: none.**

#### B7. Baseline Vision

- **URLs:**
  - https://www.baselinevision.com/
  - https://www.utrsports.net/blogs/press/utr-sports-baseline-vision-expand-electronic-line-calling-ptt
- **Data unit:** "player placement, shot placement, speed, accuracy, net clearance" (provider claim).
- **Tiers:** none of the population's tiers. It is used on the UTR Pro Tennis Tour, an adjacent circuit.
- **Evidence [provider claim]** (UTR, 24 March 2026):
  - "…partnership expansion with Baseline Vision to integrate real-time data streaming and electronic line calling (ELC) into the UTR Pro Tennis Tour (UTR PTT) worldwide."
  - "The partnership builds on a successful 2025 pilot held at more than 80 UTR PTT events across the U.S. and Europe."
  - "UTR Sports will further integrate Baseline Vision's player and ball-tracking data into its analytics offerings…"
- **ITF classification, archive, price:** not stated.
- **Judgement: none** for Challenger/ITF.

#### B8. SwingVision

- **Evidence:**
  - [third-party report] https://www.tennis.com/baseline/articles/fair-play-swingvision-puts-its-electronic-line-calling-to-the-test-in-tournament-play (8 December 2024): it plans to test in "the USTA Florida section, with an eye toward potential use at professional Challenger level events". The CEO said: "Next year we're looking for certification with the ITF".
  - [third-party report] https://www.tennisnerd.net/news/live-line-calling-from-swingvision/43158 (20 December 2024): "In 2025 Swingvision will also try to test the line calling system at ITF events."
  - [third-party report] https://www.siliconsnark.com/tennis-tech-in-2026-can-call-every-line-it-still-cant-fix-your-forehand/ (1 September 2026): "SwingVision became an ITF-approved Player Analysis Technology product in October 2025." The same source says this is not an ITF-classified ELC system.
- **Tiers:** no confirmed deployment at any population tier. College use (ITA) is outside the population.
- **Archive, sale:** not stated.
- **Judgement: none.**

#### B9. PlaySight

- **URL:** https://playsight.com/
- **Evidence [provider claim]:** "PLAYFAIR - pro level video replay for tennis". The customer logos are the ITA and US universities.
- **Tiers:** no professional-tier deployments stated.
- **Archive, sale, price:** not stated.
- **Judgement: none.**

#### B10. Wingfield

- **URL:** https://www.wingfield.io/en/blog/partnership-dtb (15 June 2023).
- **Evidence [provider claim]:** "With the Wingfield system, we want to give players a modern, uncomplicated opportunity to play LK matches." These are amateur rating matches in the DTB system.
- **Tiers:** none of the professional tiers.
- **Price:** the page summary gave €12.99 per player per match; I did not re-check this.
- **Judgement: none.**

### C. Analytics vendors

#### C1. TennisViz (Ellipse Data)

- **URLs:**
  - https://tennisviz.com/
  - https://tennisviz.com/performance-portal/
  - https://www.atptour.com/en/news/insights-introduction (8 August 2022)
- **Data unit:** AI-derived shot and point metrics (Shot Quality, In Attack, Conversion, and others) built on TDI's tracking data.
- **Tiers:** ATP broadcast "into the broadcast of ATP Masters 1000 tournaments and the season-ending Nitto ATP Finals" (2022). Challenger and ITF: not stated.
- **Evidence [provider claim]:**
  - ATP: "TDI's industry-leading match and tracking data and TennisViz's next generation Artificial Intelligence".
  - Performance Portal: "details at the shot and point level as well as summary information". Which tours it covers is not stated. Access is by "Request a demo".
- **Evidence [observed]:** the US Open SlamTracker config uses the metric names "Shot Quality" and "In Attack". The config does not say who supplies them.
- **Price:** not stated.
- **Judgement: low/none.** It is a B2B service built on licensed tour data.

#### C2. Tennis Australia Game Insight Group

- **Status:** not retrieved. The web-search budget ran out, a guessed domain did not resolve, and tennis.com.au returned 403.
- **All fields:** unknown.
- **Judgement: none** (unverified).

#### C3. Golden Set Analytics

- **URL:** https://www.goldensetanalytics.com/
- **Evidence [provider claim]:**
  - "High performance analytics based on the most comprehensive dataset of historical and all current matches on tour"
  - "GSA works only with selected clients, providing 24/7 service"
  - "Exact measurements of serve toss and contacts points during matches"
- **Tiers:** "GSA ATP-WTA SERVICES". Challenger and ITF coverage is not stated.
- **Price, terms:** not stated.
- **Judgement: low/unknown.** It is closed to selected clients, and whether it covers Challengers is not stated.

#### C4. TennisProfiler

- **URL:** https://www.tennisprofiler.com/
- **Evidence [provider claim]:** "charted more than one million points"; "Statistics are done manually"; offers ATP and WTA player profiles by subscription ("Profiler Starter" and "Profiler Premium"; prices not listed).
- **Tiers:** top ATP and WTA players. Challenger and ITF: not stated.
- **Judgement: none.**

---

## 4. Ranked summary table

Ranked first by the main judgement (Challenger/ITF men's matches, 2019–2026), then by usefulness for the other tiers in the reference population.

| Rank | Source | Tiers with any shot/tracking (S) or point-level (P) data | Years | Access route | Challenger/ITF judgement | Value for other tiers in the population |
|---|---|---|---|---|---|---|
| 1 | TDI / Sportradar (ATP data licence) | CH main and Q: P (umpire feed); ATP main and Q: S and P | not stated | commercial licence, no price | **low** | ATP tour level (licence) |
| 2 | ITFL (ITF data rights) | ITF M25: P (live data kept); M15: live data removed; tracking only from 2026 | not stated | commercial licence | **low** | none |
| 3 | PlayReplay (USTA ITF events; DTB pilots) | ITF M15/M25 on hard courts: S (and P internally) | 2026 onward | none public; ITF Appendix G restricts use | **low** (future only) | none |
| 4 | Bolt6 | some Challengers (Canada, Lincoln): S | 2026 | none public | **low** | AO qualifying and main (tracking behind the AO feed) |
| 5 | Foxtenn | some Challengers (Heilbronn): S | 2024 onward | none public | **low** | ATP (some events, not stated which) |
| 6 | atptour.com JSON / Stats Centre | CH main and Q: box score only; ATP: Court Vision and MatchBeats blocked | 2019 onward (box scores) | public page; terms prohibit systematic retrieval and gambling use | **low** | ATP main (blocked) |
| 7 | Golden Set Analytics | "all current matches on tour" (tiers not stated) | not stated | selected clients | **low/unknown** | tour level |
| 8 | TennisViz | ATP (via TDI) | 2022 onward | B2B | **low/none** | ATP |
| 9 | ATP Tennis IQ | ATP and CH players are users; data by tier not stated | 2023 onward | players and coaches only | **none** | via a player's own cooperation only (terms not stated) |
| 10 | **US Open SlamTracker feeds** | GS qualifying and main: P plus derived S (speed, depth, distance) | 2022–2026 | **public JSON** (terms not retrieved) | none | **high for US Open qualifying 2025–26** (partial 2022–24) |
| 11 | **Wimbledon SlamTracker feeds** | GS qualifying and main: P plus derived S | 2025–2026 | **public JSON** (terms not retrieved) | none | **high for Wimbledon qualifying 2025–26** |
| 12 | **AO match-centre API** | GS qualifying and main: P (text per point) plus serve speeds | 2026 only | public JSON, current year only | none | **medium** (capture each January) |
| 13 | Roland-Garros Infosys match centre | GS qualifying and main: box score public; P blocked | 2019 claim | public page / blocked API | none | low |
| 14 | Hawk-Eye | ATP, GS: S and P | 2021 onward (GS all courts) | through rights holders | none | via TDI / Slams |
| 15 | itftennis.com | unknown (bot-protected) | unknown | blocked | none/unknown | none |
| 16 | daviscup.com | unknown | unknown | client-rendered | none/unknown | Davis Cup (<1%) |
| 17 | FlightScope, Zenniz, Baseline Vision, SwingVision, PlaySight, Wingfield, TennisProfiler, Tennis Australia Game Insight Group | no population-tier deployments found (Baseline Vision: UTR PTT only) | n/a | n/a | none | none |

---

## 5. Open questions worth an explicit decision later (suggestions, not recommendations)

- **Rights check before any storage or modelling of Slam feeds.** Read and record the website terms for usopen.org, wimbledon.com, ausopen.com and rolandgarros.com before storing, training on, or using for betting any of the SlamTracker or AO data. The atptour.com terms, where retrieved, prohibit systematic retrieval and gambling use.
- **Is GS qualifying worth building on?** It could provide point-level data for the reference players: US Open 2022–2026, Wimbledon 2025–2026 and AO from 2026. Roughly 5% of the reference matches are tour-level qualifying, and only part of that is Slam qualifying.
- **Challenger and ITF point-level data** exists only through licensed umpire feeds (TDI/Sportradar; ITFL/its licensee). Tracking data at these tiers either does not exist before 2024–2026 or is contractually locked.
- **Not researched here (outside this scope):** computer-vision extraction from streamed video (Challenger TV via Sportradar; ITF live streaming). Note that the ITF regulations define data taken from "television pictures, the internet" as "Unofficial Data".
