# R2: Official and enterprise tennis data feeds. Historical point-level and shot-level data for men's ITF and Challenger matches

- **Research and access date for every URL:** 23 Sep 2026. This was web research only. I did not sign up, log in, request a trial, fill in a form, contact a vendor or buy anything.
- **Builds on:** the 10 Sep 2026 audit (ITF rights moved to Infront in 2025 with LSports distributing; Sportradar's January 2025 ITF removal; Sportradar's rolling catalog; Stats Perform tennis from 2021 and its ML-training restriction; TDI's archive and sandbox). Each item was re-checked and taken further at point and shot level. Section 6 lists what was confirmed and what is new.

**Evidence labels**

- **[provider claim]:** a statement by the data owner, vendor or governing body. Rulebooks and regulations count.
- **[observed]:** a real payload or sample that I read. Every "observed" item here is an example payload printed in official documentation. None of them is an ITF or Challenger match.
- **[third-party report]:** press, partner or competitor material.
- **[inference]:** my own reasoning. Nothing states it.
- **not stated:** I looked for it and did not find it.

---

## 0. Method and access limits

- **How pages were read.** I read pages with the WebFetch tool. For public documentation pages I also downloaded the raw HTML or PDF and converted it to text, so that quotes are verbatim.
  - The conversion used the base Miniforge interpreter, not the project's `tennis` env. It was used only to turn HTML or PDF into text in the scratchpad.
  - Scratch files are in the session scratchpad and have not been deleted.
- **Blocked or unreadable pages.** These are recorded here. I did not try to get around any of them.
  - **tennisdata.com and results.tennisdata.com:** HTTP 403 on every page tried. That covers the home page, `/tennis-data-platform`, a results match page, `/about` and `/terms-and-conditions`. TDI and Tennis Results evidence therefore comes from the ATP Tour site, Sportradar pages, a TDI staff interview and search-engine summaries. Each is labelled.
  - **coverage-matrix.sportradar.com:** a JavaScript app. The static fetch shows only "Showing 0 to 0 of 0 rows".
  - **marketplace.sportradar.com:** the Tennis API product page returned only a title.
  - **store.sportradar.com:** DNS lookup failed.
  - **HTTP 403:** sportbusiness.com, sbcnews.co.uk, legalsportsreport.com, insidersport.com.
  - **Other failures:** investors.sportradar.com timed out twice. The news.geniussports.com German Tennis Federation (DTB) article returned HTTP 500.
- **Disclosure: retry with a second tool.** Two documents refused a command-line (curl) request: `sportradar.com/official-atp-addendum` (Cloudflare page) and the ATP 2026 Rulebook PDF (403). Both then opened normally through the standard WebFetch tool. I used no header spoofing, proxies, caches or archive copies. The owner can decide whether that second attempt was acceptable.
- **Search quota.** The session's web-search quota ran out near the end. Sportlevel, Swish Analytics and Abelson Info each got only one search or one homepage read.
- **Quote format.** In quotes taken from tables, "·" marks a boundary between table cells. "…" marks text I left out.

---

## 1. Bottom line

1. **ITF M15/M25 (about 50% of the reference population):** I found no official or enterprise source that documents a purchasable 2019–2026 archive of point-level data.
   - Chair umpires recorded points in both eras. Up to 2024 they used "Sportradar devices". From 2025 they use new ITF handheld devices supplied under the Infront deal.
   - Sportradar removed the ITF World Tennis Tour from its Tennis API from 2025. Nothing I found says where the 2017–2024 ITF point data can be obtained now.
   - Infront and LSports sell a live betting feed. Neither states any historical archive.
2. **Challenger and ATP data is official, but historical access is short and heavily restricted.**
   - Challenger and ATP point data is official umpire "level 1" data from TDI. Sportradar is described as "TDI's exclusive distribution partner" [third-party report], under a rights cycle that began in 2024.
   - Sportradar's Tennis API v3 documents Challenger "Point-by-point from round 1". Each point carries server, score, result (ace / double_fault / server_won / receiver_won), a first-serve-fault flag and a UTC timestamp.
   - That data is only available for seasons inside a rolling window of "at least the current season and the two adjacent editions". Today that is roughly 2024/25–2026 [inference].
   - Sportradar's master terms make the licence display-only on named properties. They bar betting and prediction-market use without written consent, and they require destruction of "all historical data … together with any derivatives" when the contract ends.
3. **Challenger and ATP qualifying.** Several sources say official scoring covers qualifying:
   - the ATP Rulebook live-scoring rule ("each match");
   - Sportradar/TDI in 2022 ("including all qualifying and doubles matches");
   - a 2026 report on Polymarket's ATP deal ("main draw and qualifying").
   Sportradar's API documentation only hedges: "Qualification rounds often have lower coverage than the main draw". Whether qualifying point data is exposed per match in the Tennis API is not stated.
4. **ITF qualifying.** The ITF's own 2025 table says chair-umpire live scoring happens only in the M15 main draw, and in the M25 last qualifying round plus main draw. It calls this "NO CHANGE" from before. So most ITF qualifying matches probably never had official point data [inference].
5. **Shot and tracking data is essentially unavailable for the target tiers.**
   - ITF Level 2 data (rally length, shot type) and Level 3 data (player and ball tracking) are collected only at streamed matches from 2025. That means M25 and above, never M15.
   - ATP Challengers use line umpires, with optional "Review ELC". Full "Live ELC" (the electronic line-calling system that also produces tracking) is mandatory only at ATP Tour events.
   - The legacy IMG ARENA player-and-ball tracking feed, now Sportradar's, is live only. It covers Grand Slam-type events and is available by arrangement.
6. **Best leads, all unverified:**
   - TDI's free "Tennis Results" site. It claims official point-by-point results for all ATP and Challenger matches, and a qualifying match page appears in search results. It is blocked to automated fetching, and its depth and terms are unknown.
   - Sportradar's Tennis API, for Challenger 2024–2026 only.
   - Enetpulse's "exclusive" point-by-point history since 2020, which is focused on tour level.
   - Goalserve's $150/month feed, which claims point-by-point "match history" for Challenger and ITF. Its provenance is unofficial and its depth is unknown.

---

## 2. Who collected men's point data, by tier (rights map, 2019–2026)

| Tier | 2019–2024 | 2025–2026 | Key evidence |
|---|---|---|---|
| ITF M15/M25 main draw | ITF chair umpires using "Sportradar devices". Sportradar was the ITF official data partner from 2012; a 3-year extension was announced Oct 2021. | ITF chair umpires using new ITF handheld devices (the Infront solution, "developed in close collaboration with the ITF and Tennis Data Innovations"). Infront Bettor holds the rights 2025–2029, extended by 3 years in Oct 2025. LSports is a distributor. | Sportradar coverage tiers; ITF 2025 organisational requirements; Infront 2023/2024/2025 releases |
| ITF qualifying | Probably only the M25 last qualifying round was scored [inference from "NO CHANGE"]. | M25: "Last Round of Qualifying & Main Draw". M15: "Main Draw" only. | ITF 2025 requirements table |
| Challenger main and qualifying | ATP chair-umpire scoring, managed by TDI from 2020. From 2022 Sportradar ran a secondary official feed "including all qualifying and doubles matches" alongside the "existing official fast data feed". | Sportradar holds ATP and Challenger betting and media data rights "starting 2024" (a six-year cycle according to press summaries). It is "TDI's exclusive distribution partner" [third-party report]. | Sportradar/TDI release; ATP Rulebook §6.09; SportsPro (13 Mar 2023); Polymarket report |
| ATP main and qualifying | Same as Challenger | Same as Challenger. Live ELC is mandatory at all ATP Tour events. | ATP Rulebook §5.08 |
| Grand Slam qualifying | Roland Garros, Wimbledon and US Open: IMG ARENA live data feed ("DDE"), which lists "Men's Singles Qualifying (QMS)". Its scoring notes refer to the 2022 editions; earlier years were not checked. Australian Open: not researched. | Roland Garros, Wimbledon, US Open: Sportradar (IMG ARENA acquisition closed 3 Nov 2025). Australian Open: Infront Bettor (Tennis Australia deal "includes top grand slam event, Qualifying…", Sep 2025). | Sportradar DDE docs; Infront release |
| Davis Cup | Sportradar as ITF partner | Infront's ITF deal "encompasses … Davis Cup". Sportradar's Tennis API: "coverage for the Davis Cup … will continue". | Infront 2023; Sportradar changelog |

---

## 3. Sources

### 3.1 Sportradar Tennis API v3 (media API) and Tennis Probabilities

**URLs**

- https://developer.sportradar.com/tennis/docs/tennis-ig-data-coverage-tiers (same page as `/ig-data-coverage-tiers`; updated 2026-07-28)
- https://developer.sportradar.com/tennis/docs/tennis-ig-historical-data (updated 2026-07-28)
- https://developer.sportradar.com/tennis/reference/sport-event-timeline
- https://developer.sportradar.com/tennis/docs/tennis-ig-live-match-retrieval
- https://developer.sportradar.com/tennis/reference/faq
- https://developer.sportradar.com/sportradar-updates/changelog/tennis-api-coverage-updates
- https://developer.sportradar.com/tennis/docs/ig-account-maintenance
- https://developer.sportradar.com/sportradar-updates/page/terms-and-conditions ("Last Updated: August 5, 2026")
- https://sportradar.com/official-atp-addendum/?lang=en-us ("Version 02 December 2024")
- https://developer.sportradar.com/tennis/reference/timeline-probabilities

**Data unit**

- The Sport Event Timeline is a point sequence. Each `point` event carries:
  - `server`
  - `home_score` / `away_score` (the game score after the point; the documentation example uses 50 for advantage)
  - `competitor` (the point winner)
  - `result` (`ace`, `double_fault`, `server_won`, `receiver_won`, `unknown`)
  - `first_serve_fault`
  - `time`
  - `id`
- Plus `period_score` and match-state events.
- `point_type` (game/break/set/match point) exists only in the live `sport_event_status.game_state`, not in timeline events.
- There is no rally length, serve speed or shot data in the timeline.
- "Standard match stats" apply to most tiers. Stroke-level aggregates (forehand/backhand winners and errors) are "Extended match stats" and are Tier 1 (Grand Slams) only.
- The coverage flag `detailed_serve_outcomes` shows that some matches can have point-by-point data without ace/double-fault detail.

**Point-level data by men's tier**

| Tier | Point-level? | Earliest claimed year | Note |
|---|---|---|---|
| ITF M15/M25 main draw | Yes up to 2024; No from 2025 | not stated | Tier 5: "ITF (up to 2024 only) … Point-by-point from round 1". Whether those seasons can still be queried is not stated. |
| ITF qualifying | Unknown | not stated | "From round 1" is ambiguous about qualifying. |
| Challenger main draw | Yes | not stated | Tier 2: official data, "Point-by-point from round 1". |
| Challenger qualifying | Unknown (hedged) | not stated | "Qualification rounds often have lower coverage than the main draw". |
| ATP main draw | Yes | not stated | Tier 2 |
| ATP qualifying | Probably | not stated | "usually consistent throughout major tournaments such as ATP events and Grand Slams". |
| Grand Slam qualifying | Probably | not stated | Tier 1: "100% point-by-point from round 1". Qualifying is a stage inside the Grand Slam season (e.g. "2026 Wimbledon, London, GB, Qualifying, 1st - 2nd Round"). |
| Davis Cup | World Group: Yes. Non-World Group: No. | not stated | Tier 3 vs Tier 7 |

**Historical access and depth**

- Seasons are served from a per-competition rolling window: "at least the current season and the two adjacent editions".
- Timelines are kept only while a season stays inside that window.
- Player profiles and per-year statistics go back to 2007, but those are aggregates, not points.
- The master terms define order-form history tiers: "Core History" (the current season plus the prior 2 years), "Expanded History" (25 years) and "Complete History" (all available seasons). Whether Tennis v3 is sold with anything beyond the rolling window is not stated.
- What happened to 2017–2024 ITF seasons after the 2025 removal is not stated. The FAQ still lists "sr:category:785 - ITF Men", and the tier table still carries "ITF (up to 2024 only)".

**Timestamps**

- Yes. Each timeline event has `time`, "Timestamp of a timeline event ex. 2024-04-16T20:49:49+00:00". The API FAQ says timestamps are UTC.
- The OpenAPI example also shows `updated` and `updated_time`.

**Published price and trial**

- Price: not published. The marketplace page is JS-only and the store domain does not resolve.
- A competitor's marketing page claims "even 'starter' contracts are typically $5,000 to $10,000/month with annual commitments" [third-party report; low reliability].
- Trial: exists, and the Tennis API is not on the list of products that cannot be self-issued. The limits are "30-day trial period 1,000 requests (quota) per rolling 30 days 1 QPS". "Probabilities API" is on the list of trials that cannot be self-issued.

**Licence terms (Sportradar US master terms, Aug 2026)**

- **Trial:** internal evaluation only (§3.1).
- **Paid use is display-only:** "for the sole purposes of displaying Data and Content … on the Properties specified" (§2.1, §2.3).
- **Prediction markets:** no use for a "prediction market, trading platform, financial product" without prior written consent (§2.1).
- **Betting:** no use for "gambling or betting-related purposes without express written approval" (§2.10).
- **Termination:** all data "including without limitation all historical data … together with any derivatives, copies, extracts, or compilations thereof" must be destroyed after termination (§7.4).
- **AI and ML:** §5 bars using Sportradar's "AI models, algorithms, Outputs or other intellectual property" to train AI/ML. Whether "other intellectual property" includes Data is ambiguous.
- **Storage:** storage on customer servers is contemplated during the term (§1.21).
- **ATP Addendum** (official ATP/TDI data):
  - destroy Licensed Materials at termination (§1.8.2);
  - no "unofficial TDI feeds", no "collate data", no trading on information from "television pictures, the internet, attendance at Matches" (§3.1.1);
  - ITIA data-sharing obligations (§1.2).

**Evidence**

1. [provider claim] Coverage tiers page: "5 · ITF (up to 2024 only) · Data directly from ITF umpires via Sportradar devices. Standard match stats. Point-by-point from round 1. No post-match corrections. No court information."
2. [provider claim] Same page: "2 · ATP 1000, ATP Finals, ATP 500, ATP Cup, ATP 250, Challenger · Official data. Standard match stats (no extended stats). Point-by-point from round 1. Post-match corrections. Tier 2 and Tier 3 are differentiated by the presence of official data."
3. [provider claim] Same page: "1 · Grand Slams · Extended match stats. 100% point-by-point from round 1. Post-match corrections."
4. [provider claim] Same page: "Note: Qualification rounds often have lower coverage than the main draw, although coverage is usually consistent throughout major tournaments such as ATP events and Grand Slams."
5. [provider claim] Same page: "7 · Billie Jean King Cup (non-World Group), Davis Cup (non-World Group) · No point-by-point. Game-by-game score, or results only post-match."
6. [provider claim] Same page: "play_by_play : true when a point-by-point timeline is available for the match." and "detailed_serve_outcomes : true when serve-level outcomes (aces, double faults, first and second serve success) are included."
7. [provider claim] Coverage-updates changelog, "January 2nd, 2025": "Starting in 2025, the ITF World Tennis Tour will no longer be a part of the Tennis API. However, coverage for the Davis Cup and Billie Jean King Cup will continue as usual." and "We now offer 100% official ATP Tour coverage within the Tennis API".
8. [provider claim] Historical Data page:
   - "The season catalog carries a rolling window per competition: at least the current season and the two adjacent editions."
   - "Completed matches retain their full detail: summaries, statistics, and point-by-point timelines remain available for as long as the season stays in the catalog."
   - "with player data as far back as 2007"
   - "Archive what you need before a season ages out of the rolling window"
9. [provider claim] Sport Event Timeline reference: "Returns information for a given sport event ID including a timeline of events, (point-by-point or Game-by-Game depending on the coverage) and some basic stats". Field rows: "result … ace , double_fault , server_won , receiver_won , unknown"; "server … home , away"; "first_serve_fault … Signifies the first serve of a point was a fault when true".
10. [observed, doc example, Grand Slam-level match] Historical Data page: `{ "id": 2409264448, "type": "point", "time": "2026-07-12T18:55:56+00:00", "competitor": "home", "home_score": 40, "away_score": 30, "server": "home", "result": "server_won" }`
11. [observed, doc example, ATP 500 main draw] Tracking Live Matches page: `{ "id": 4730503, "type": "point", "time": "2026-07-27T21:50:35+00:00", "competitor": "home", "home_score": 50, "away_score": 40, "server": "away", "result": "receiver_won", "first_serve_fault": true }`
12. [provider claim] FAQ: "sr:category:72 - Challenger … sr:category:785 - ITF Men" and "Standard match stats are available whenever live point-by-point coverage is true."
13. [provider claim] Account Maintenance: "Sportradar API trials are defaulted at: 30-day trial period 1,000 requests (quota) per rolling 30 days 1 QPS" and "Trial access provides the same real-world data as production, with some rare exceptions."
14. [provider claim] Master terms §2.1: "…for the sole purposes of displaying Data and Content provided through each such Product on the Properties specified for such Product on the Order Form … Customer shall not use, or permit any third party to use, the Services/Rights or any related data, content or outputs for any prediction market, trading platform, financial product or similar offering without Company's prior written consent".
15. [provider claim] Master terms §7.4: "…destruction and sanitization of all data and databases … including without limitation all historical data, non-realtime data, and game-related statistical information, together with any derivatives, copies, extracts, or compilations thereof".
16. [provider claim] Master terms §1.5 and §1.6: "Complete History means … the current season and all available prior seasons of historical data" and "Core History means … the current season and the prior two (2) years of historical data".
17. [provider claim] ATP Addendum: "'TDI Official Data' shall mean the data … (including Match related data points collected by the umpire of each respective Match through a dedicated scoring system, such as: player(s), start and finish time, sets, games, breaks, points, tiebreaks and right of services/ball changes)". Also §3.1.1: "(i) acquire or use any unofficial TDI feeds; (ii) collate data; and/or (iii) trade based on information which it receives or ingests from television pictures, the internet, attendance at Matches or otherwise".
18. [provider claim] Timeline Probabilities: "Provides a timeline of pre-match and live probability changes for a given match". It adds win-probability history, not additional point fields.

**Unknowns and red flags**

- Whether Challenger qualifying, ATP qualifying and Grand Slam qualifying timelines are populated. This is decided match by match through `coverage.play_by_play`, and I could not read the coverage matrix.
- The fate of the 2017–2024 ITF timelines, and whether "Complete History" exists for tennis.
- The trial quota (1,000 calls) is below the reference population's roughly 4,000 matches.
- Prediction-market use is explicitly prohibited without consent.
- **Deadline:** anything licensed must be destroyed at the end of the contract.

**Judgement: LOW.** Sportradar does document Challenger point-by-point data. But only the last two or three editions are retrievable, it holds no ITF data from 2025 and says nothing about access to pre-2025 ITF, pricing is enterprise-level, and the licence is display-only with bans on prediction-market use and on keeping data after the contract ends.

---

### 3.2 Sportradar "Tennis on DDE" (legacy IMG ARENA tennis feed, including Player & Ball tracking)

**URLs**

- https://docs.sportradar.com/tennis/documentation-1/tennis-scoring-types.md
- https://docs.sportradar.com/tennis/live-data-scenarios-1/the-basics.md
- https://docs.sportradar.com/tennis/p-and-b-tracking-websockets.md
- https://docs.sportradar.com/tennis/p-and-b-tracking-websockets/rally-summary-feed.md
- https://docs.sportradar.com/tennis/stream-endpoints-websockets/connecting-to-the-stream-endpoints.md
- https://docs.sportradar.com/tennis/schedule-endpoints-restful-1/competitions-id-events.md
- Acquisition close: https://sportradar.com/content-hub/news/sportradar-announces-close-of-acquisition-of-img-arena-and-its-strategic-portfolio-of-global-sports-betting-rights/?lang=en-us

**Data unit**

- A live websocket packet stream:
  - `PointStarted`
  - `PointFault`
  - `PointScored`, with `pointType` Standard/Ace/DoubleFault, `scoredBy`, the full score, `server`, a millisecond `timestamp` and `matchTime`
- Player & Ball ("P&B") tracking feeds:
  - rally summary (shots per rally, serve speed and side, winning stroke, result and speed, distance travelled)
  - per-rally ball/shot tracking
  - per-rally player tracking
  - live ball and player tracking

**Point-level data by men's tier**

- ITF: No. Challenger: No. ATP main draw and qualifying: No; only United Cup is listed for ATP. Davis Cup: not stated.
- Grand Slam qualifying: Yes, live. Men's Singles Qualifying (QMS) is listed for the French Open, Wimbledon and US Open. The earliest year referenced is 2022 editions.
- Tracking at named tournaments: "contact support@openbet.com" (not stated per tournament).

**Historical access and depth**

- Not stated. The streams are live. `startPosition` replays a sequence within one event.
- The REST events list "is incomplete and will generally only show previous events and events for today and tom[orrow]".
- The legacy REST host is "Decommissioning on 30th Sept 2026".

**Timestamps:** yes, millisecond UTC `timestamp` per packet, plus `matchTime`.

**Price and trial:** not stated. Test streams "play a real historical match (with the names of the players modified)".

**Licence:** not stated in the documentation. This is a betting-operator product.

**Evidence**

1. [provider claim] "Throughout the United Cup and Grand Slams covered by IMG, there are a number of tennis scoring types." Table rows include "Men's Singles Qualifying (QMS)" under French Open, Wimbledon and US Open.
2. [provider claim] "A point packed is received whenever a player wins a point. They are generally standard, aces or double faults."
3. [observed, doc example] `"eventElementType": "PointScored" … "details": {"pointType": "Standard", "scoredBy": "TeamB"} … "server": {"member": 1, "team": "TeamB"}, "timestamp": "2024-05-20T09:48:11.872Z"`.
4. [provider claim] Rally summary: "breakdown of points won per player by rally length grouping and the Average number of shots per rally, distance travelled, winning shot (speed/stroke/result)".
5. [observed, doc example, 2022 women's match] `"conclusion": {"stroke": "Backhand", "result": "Error", "action": "Forced", … "speed": 71.193}, "serve": {… "side": "Advantage", "speed": 98.213}`.
6. [provider claim] "For availability of P&B Tracking feeds across specific Tournaments and Tours, please contact support@openbet.com".
7. [provider claim] "Legacy - https://dde-api.data.imgarena.com/competitions/{id}/events (Decommissioning on 30th Sept 2026)".
8. [provider claim] Sportradar release: acquisition completed "November 3, 2025". The release names no tennis properties.

**Unknowns and red flags:** no archive product is stated, P&B availability is per tournament, and the feed has nothing below Grand Slam level for men.

**Judgement: NONE** for ITF and Challenger. This is a live feed for Grand Slams (including qualifying) and team events only. It could matter only for the roughly 5% of Grand Slam and ATP qualifying matches, and even then no historical route is stated.

---

### 3.3 TDI: Tennis Data Innovations (ATP / ATP Media joint venture), "Tennis Results" site and Tennis Sport Data Platform (TSDP)

**URLs**

- https://www.tennisdata.com/ and https://www.tennisdata.com/tennis-data-platform (HTTP 403)
- https://results.tennisdata.com/en (HTTP 403)
- https://www.atptour.com/en/news/tennis-data-innovations-champion-data-may-2023-release (16 May 2023)
- https://www.ubitennis.net/2024/02/exclusive-the-atp-tennis-data-and-its-growing-demand/ (5 Feb 2024)
- https://sportradar.com/content-hub/news/tennis-data-innovations-and-sportradar-team-up-to-expand-official-tennis-data-distribution/?lang=en-us (Oct 2022)
- ATP 2026 Rulebook: https://www.atptour.com/-/media/files/rulebook/2026/2026-rulebook_14jan26.pdf
- https://bettorsinsider.com/news/2026/08/07/polymarket-becomes-atp-tours-official-prediction-market-provider-lands-live-streaming-rights/

**Data unit**

- Umpire "level 1" point-by-point data (points, serve, score).
- Optical tracking (Hawk-Eye / ELC) where installed.
- The Tennis Results site is claimed to show, for every point, who won it and how.

**Point-level data by men's tier**

| Tier | Point-level? | Earliest claimed year | Note |
|---|---|---|---|
| ITF | No | – | Not TDI's rights |
| Challenger main draw | Yes | not stated; TDI since 2020 | Umpire L1 data |
| Challenger qualifying | Yes (claimed for the official feed) | not stated | "including all qualifying and doubles matches". A "QS009" (qualifying singles) page appears on Tennis Results in search results. |
| ATP main draw and qualifying | Yes | not stated | |
| Grand Slam qualifying | No | – | Grand Slams are not ATP events |
| Davis Cup | No | – | |

**Tracking**

- Live ELC is "mandatory at all ATP Tour events".
- Challenger events use line umpires, plus "Electronic Review (Review ELC) - applicable to ATP Challenger Tour only".
- So Challenger tracking data is likely sparse [inference].

**Historical access and depth**

- The TSDP "will also serve as a rich and accessible archive of historical data sets … open 'sandbox' environment to enable third parties". This was a 2023 forward-looking claim.
- No current access route, eligibility criteria or depth is stated anywhere I could read.
- The Tennis Results site is free. Its depth is not stated (it launched in 2025 per a search-engine summary; not verified). Automated fetches get 403.

**Timestamps**

- The TDI Official Data definition includes "start and finish time", at match level.
- Point timestamps: not stated.

**Price and trial:** not stated. There is no stated route for researchers or bettors. Commercial distribution goes through Sportradar, "TDI's exclusive distribution partner" [third-party report].

**Licence:** see the ATP Addendum under 3.1. The Tennis Results terms are unknown (403).

**Evidence**

1. [provider claim, via ATP Tour, 2023] "The TSDP will enable TDI to ingest, merge and distribute multiple live data sources from professional tennis, including umpire scoring and player & ball tracking data, at ultra-low latency." and "The TSDP will also serve as a rich and accessible archive of historical data sets, in addition to providing an open 'sandbox' environment to enable third parties to innovate with tennis data."
2. [third-party report, interview with TDI Head of Product] Quotes from the interview:
   - "TDI … is responsible for collecting, managing & commercialising data & streaming across all ATP events from Challengers to Masters 1000s."
   - "We collect data point by point from the chair umpire, what we call 'level 1' data."
   - "Historically, ATP data was presented by Infosys, and where Hawkeye was present, the statistics are complete."
   - "In 2024, we aim to achieve uniformity in data collection and analysis for all ATP events."
   - "Now, players can download raw Hawkeye data for their data analysis teams or directly use the metrics and insights we provide on Tennis IQ." (Tennis IQ is for players.)
3. [provider claim] Sportradar/TDI (2022): "With scores delivered directly from the umpire's chair, the new feed provides full and uninterrupted coverage of ATP Tour and ATP Challenger Tour events across the season, including all qualifying and doubles matches".
4. [provider claim, governing-body rule] ATP 2026 Rulebook §6.09 D:
   - "Each Tournament shall be responsible for the set up and maintenance of a network … to support live scoring services for each match* of the event"
   - "*… Tournaments are not required to provide live scoring support for qualifying matches played at an alternate venue."
   - §6.09 F: "must exclusively use official ATP data".
5. [provider claim, governing-body rule] ATP Rulebook §5.08: "The use of the Live ELC system replacing line umpires is mandatory at all ATP Tour events." Under "ATP Challenger Tour Tournaments": "Tournaments must hire officials as specified below…". Also: "Electronic Review (Review ELC) - applicable to ATP Challenger Tour only".
6. [provider claim, seen only via search-engine summaries; pages returned 403]
   - "The freely available 'Tennis Results' site is the official source for results from all ATP Tour & Challenger Tour matches, offering an unparalleled level of transparency for verifying bet settlements."
   - "'Tennis Results' provides access to detailed results on every point played, revealing not just who won the point, but how they won it".
   - Search index title: "Poullain vs Orlov | 2026#3105#QS009 | Tennis Results" (results.tennisdata.com/en/results/17dd5f94-4420-4ded-a2ed-6e8f545c0c09).
7. [third-party report, 7 Aug 2026] "The rights cover approximately 20,000 matches per ATP season, spanning main draw and qualifying singles and doubles across both the ATP Tour and ATP Challenger Tour" and "official real-time data and odds for every match will come from Sportradar, TDI's exclusive distribution partner".

**Unknowns and red flags**

- The site blocks automated access.
- Depth, granularity (does it show the server and a point type per point?), bulk access and terms of use are all unknown.
- The TSDP sandbox has had no visible public follow-through since 2023.
- Challenger tracking data is not standard.

**Judgement: LOW for TDI direct.** TDI names no public, research or small-customer route, and commercial access goes through Sportradar. The Tennis Results site is **LOW–MEDIUM, pending the owner's manual check**: it is the only official, free source claiming point-by-point data for every Challenger match including qualifying, but its history depth and permitted use are unknown.

---

### 3.4 Infront (Infront Bettor): ITF official data partner 2025–, and the ITF's umpire scoring

**URLs**

- https://www.itftennis.com/media/13885/wtt-data-streaming.pdf ("Version 3: January 2025")
- https://www.itftennis.com/media/15118/2025-wtt-regulations.pdf (Appendix F)
- https://www.infront.sport/news/sports-media-rights/infront-secures-landmark-five-year-global-partnership-with-international-tennis-federation (15/09/2023)
- https://www.infront.sport/news/sports-media-rights/infront-makes-significant-strides-with-data-platform-ahead-of-itf-partnership-launch (05/02/2024)
- https://www.infront.sport/news/sports-betting/infront-and-itf-extend-global-partnership-to-expand-data-and-streaming-capabilities (01/10/2025)
- https://www.infront.sport/news/sports-betting/infront-bettor-expands-tennis-portfolio-through-exclusive-australian-open-video-and-data-rights-partnership (15/09/2025)
- https://europeangaming.eu/portal/press-releases/2026/05/07/203656/data-bet-integrates-infront-bettor-official-tennis-data-to-broaden-sportsbook-coverage/
- https://www.globenewswire.com/en/news-release/2021/10/26/2320392/0/en/Sportradar-Announces-Extension-of-Official-Data-Partnership-With-the-International-Tennis-Federation.html

**Data unit (ITF definitions)**

- **L0:** pre-match.
- **L1:** "scoring data, generally recorded by the Umpire" (point sequence plus aces, double faults and similar).
- **L2:** subjective shot and rally stats, captured by human logging or computer vision.
- **L3:** "player and ball tracking data".

**Point-level data by men's tier (Infront era)**

| Tier | Point-level? | Earliest claimed year | Note |
|---|---|---|---|
| ITF M15 main draw | Yes (L1) | 2025 | L2/L3: No |
| ITF M25 main draw | Yes (L1 + L2/L3 at streamed matches) | 2025 | |
| ITF qualifying | M25 last round only; M15: No | 2025 | Live scoring only where there is a chair umpire |
| Challenger / ATP | No | – | Not Infront's rights |
| Grand Slam qualifying | Australian Open qualifying: data rights stated; point granularity not stated | from the Sep 2025 deal (not stated which AO edition) | |
| Davis Cup | Rights stated from 2025; point granularity not stated | 2025 | |

**Historical access and depth**

- Not stated. Every Infront statement found is about live B2B supply to sportsbooks.
- No archive product or pre-2025 data is mentioned.
- The ITF regulations say ITF Licensing "owns, controls and shall have the exclusive right to exploit" the data rights. The 2017–2024 umpire data (Sportradar era) is therefore presumably ITF-controlled [inference], but I found no statement of an archive or access route.

**Timestamps:** not stated.

**Price and trial:** not stated.

**Licence**

- Not stated for customers.
- The ITF regulations define "Unofficial Data" as data "obtained from sources, or via means, which ITFL has not authorised, including … physical attendance …, television pictures, the internet". This binds National Associations, but it signals the rights-holder's position on scraped data.

**Evidence**

1. [provider claim, ITF] ITF 2025 organisational requirements (quotes from the document):
   - "NO CHANGE: Live scoring will take place at all WTT tournaments as it does currently."
   - "New handheld live scoring devices will be provided by the ITF with new match scoring software installed and 4G/5G-enabled SIM cards."
2. [provider claim, ITF] Same document: "At all WTT matches, where there is a Chair Umpire, 'Level 1' data will be collected from the Chair Umpire's live scoring device, as it is now (for example: points, aces, sets). However, at all streamed WTT matches, 'Level 2' data (rally length, winners, unforced error, type of shot etc) and 'Level 3' data (player and ball movements tracked) will also be collected."
3. [provider claim, ITF] Same document, summary table:
   - "Round for Live Scoring: W15/M15 Main Draw * · … M25 Last Round of Qualifying & Main Draw *" ("* Minimum Officiating Requirements")
   - "Data (L2/L3): W15/M15 No … M25 Yes"
   - Streaming: "M25 – Final Round of Qualifying Matches and all Main Draw Matches".
4. [provider claim, ITF] 2025 WTT Regulations, Appendix F:
   - "ITFL owns, controls and shall have the exclusive right to exploit and/or to authorise third parties to exploit the Data Rights with respect to all Tournaments on a worldwide basis."
   - "Level 1 (L1) Data means … scoring data, generally recorded by the Umpire, including by way of example: game score, set score, aces, double faults, service points won and challenges remaining".
   - "'Match' means a match forming part of a Tournament (including any match in the main draw or qualifying rounds)".
5. [provider claim] Infront 2023: "The deal, beginning in 2025, encompasses the ITF Men's and Women's World Tennis Tour, Billie Jean King Cup by Gainbridge and Davis Cup" and "The agreement provides data coverage for more than 58,000 tennis matches annually and includes the development of a Level 3 computer vision data solution."
6. [provider claim] Infront 2024: "The scoring solution is being developed in close collaboration with the ITF and Tennis Data Innovations" and "integration documents already in the hands of clients".
7. [provider claim] Infront Oct 2025: "expanding the collaboration by three years" and "Infront will continue to deliver data coverage for over 66,000 matches annually, including enhanced data capture computer vision solutions." The end year is not stated. 2032 is my arithmetic [inference].
8. [provider claim] Infront Sep 2025: "New agreement with Tennis Australia (TA) includes top grand slam event, Qualifying and TA tournaments … will provide licensed sportsbooks access to high-quality live content and reliable data".
9. [third-party report / partner PR, May 2026] "spans more than 66,000 International Tennis Federation matches annually as well as the Australian Open". The feed is a "live fast-path" feed "sourced directly from the umpire's chair".
10. [provider claim, Sportradar era] Sportradar tier 5: "Data directly from ITF umpires via Sportradar devices" (see 3.1).

**Unknowns and red flags**

- There is no archive statement at all.
- M15 qualifying and most M25 qualifying have no umpire scoring.
- L2/L3 data only exists from 2025, and only at streamed matches.
- Customers are licensed sportsbooks.

**Judgement: LOW.** The data exists (L1 for ITF M15/M25 main draws from 2025), but it is sold live to licensed sportsbooks, no archive is stated, and nothing covers 2019–2024.

---

### 3.5 LSports (ITF official distributor from 2025)

**URLs**

- https://www.lsports.eu/lsports-to-become-itfs-official-data-distributor/ (August 6, 2024)
- https://www.lsports.eu/tennis-data-api/
- https://docs.lsports.eu/u/llms.txt
- https://docs.lsports.eu/u/engage/hyper-livescore/enumerations/incidents-by-sport-type.md

**Data unit**

- A live score plus incident/statistic stream. The tennis incidents are Aces, DoubleFaults, ServicePoints, BreakPoints, Score, … and "Points Won".
- Planned "level 3 data, including positional and performance data" from computer vision applied to live streams.

**Point-level data by tier**

- ITF: as for Infront (official feed), from 2025.
- ATP, WTA and others: LSports' own scouting ("web scouting, TV/in-venue scouts, and computer vision").
- Point-level granularity per tier: not stated.

**Historical access and depth:** not stated. The documentation lists Snapshot APIs "for live and pre-match events" only.

**Timestamps:** not stated for tennis.

**Price and trial:** price not stated. The tennis page links a "Free Trial".

**Licence:** not stated. The product is described as "trusted by 220+ sportsbooks".

**Evidence**

1. [provider claim] "LSports is proud to announce that it will become an official distributor of the International Tennis Federation (ITF) trading services and data starting in 2025, after signing a multi-year contract with Infront Sports."
2. [provider claim] "Data is collected and verified using various techniques such as web scouting, TV/in-venue scouts, and computer vision."
3. [provider claim] "As the ITF's official tech partner, LSports will leverage advanced computer vision techniques to extract information from live streams. This will enable the delivery of level 3 data, including positional and performance data".
4. [provider claim] Documentation: "Snapshot … Request full data snapshots for live and pre-match events".

**Unknowns and red flags:** no historical product, and the data is B2B for sportsbooks. LSports documentation describes a STATSCORE-powered "Points InPlay" tennis widget; STATSCORE's own page for it describes a gamification product.

**Judgement: LOW.** It is the official ITF channel, but only as a live sportsbook feed from 2025, and no archive is stated.

---

### 3.6 Stats Perform / Opta

**URLs**

- https://developers.statsperform.com/historical-sports-data-for-pricing-models (Published July 28, 2026)
- https://developers.statsperform.com/sports-data-for-prediction-markets (July 30, 2026)
- https://developers.statsperform.com/coverage-and-data-rights (June 15, 2026)
- https://developers.statsperform.com/feed-ma21-tennis-detailed-predictions (June 25, 2026)
- https://www.statsperform.com/products/official-wta-data-streaming/
- https://www.statsperform.com/legal/mla-december-2025/

**Data unit**

- The MA21 Detailed predictions feed is a per-point sequence, requested by point number or range. Per point it carries the score state, `isTeam1Serving`, `isFirstServe`, `stroke`, `zone`, `pointtype` (earlyPoint / setupPoint / gamePoint), a millisecond timestamp and probabilities.
- For WTA, "official data directly from the umpire, along with a parallel, low-latency shot-by-shot feed".

**Point-level data by men's tier**

- Not stated for any specific men's tier.
- `coverageLevel` 2 is "Point by Point scores available along with match events (ATP)".
- Challenger and ITF: not stated.

**Historical access and depth**

- The tennis archive runs "from 2021". Which tours it covers is not stated.
- MA21 can be queried by fixture "by point number or point ranges". Depth for MA21 specifically is not stated.

**Timestamps:** yes in MA21 ("hour-minute-seconds-milliseconds").

**Price and trial:** not stated.

**Licence (MLA Dec 2025)**

- §4(c) bars using Licensed Materials to "create, develop, test, train … machine learning … models".
- §4(c) also says "Licensee shall not bulk download or otherwise build archival files using the Licensed Materials".
- §4(r) bars "Betting Activities".
- §10(b)(iii) requires return or destruction at the end.
- These are standard MLA terms; the betting-product contracts may differ (not stated).

**Evidence**

1. [provider claim] "Archive depth by sport … Golf: from 2000 Tennis: from 2021".
2. [provider claim] Coverage matrix row: "Ultrafast Data … WTA" (tennis column).
3. [provider claim] MA21 field description: "coverageLevel … 0 = Only final set or game-by-game scores available • 1 = Only Point by Point scores available • 2 = Point by Point scores available along with match events (ATP) • 3 = Point by Point scores available along with match events (WTA)".
4. [provider claim] MA21: "n,m Delivers all points including predictions in the inclusive range from n to m" and "Historical model evaluation Query predictions by point number or point ranges".
5. [provider claim] Coverage page: "RunningBall ultrafast data covers more than 110,000 events per year across major betting sports, including … tennis. Data is collected in-venue by a 1,500+ strong global scouting network".
6. [provider claim] MLA §4(c) and §4(r), quoted above.

**Unknowns and red flags:** men's tour scope is unknown, the archive starts in 2021, and ML training and archiving are prohibited under the standard licence.

**Judgement: LOW.** It has point-level structure and data from 2021, but the men's Challenger/ITF coverage is unstated and the standard licence forbids ML training and building archives.

---

### 3.7 Enetpulse

**URLs**

- https://eclient.enetpulse.com/docs/xml-data/what-enetpulse-provides-for-tennis-events
- https://enetpulse.com/tennis-data/

**Data unit**

- Per-game score progression after each point: for each game, each player's score is recorded after every point ("Point 1 … Point 4") with an update time.
- Current server ("current_server"), "firsttoserve".
- Match statistics.

**Point-level data by tier**

- Live point-by-point "on most ATP and WTA tour-level matches".
- Grand Slams and Davis Cup appear as tour types; point-level for them is not stated.
- Challenger: named only in the headline, point-level not stated. ITF: not stated. Qualifying: not stated.

**Historical access and depth:** "we keep the pbp history since 2020 year". Point-by-point history is an "exclusive product" (contact sales). Match statistics go back to 2014.

**Timestamps:** each score record carries `ut` (update time, seconds) [observed].

**Price and trial:** price not stated. "A test period is available".

**Licence:** not stated.

**Evidence**

1. [provider claim] "Point by point result updates (we keep the pbp history since 2020 year)" and "(7). Point by Point History (It's an exclusive product, so please contact Sales for more information)".
2. [provider claim] "Live, point-by-point scoring as play happens, on most ATP and WTA tour-level matches" and "All the best from ATP, WTA, Grand Slams, and Challengers."
3. [observed, doc example: 2020 Zverev–Thiem match] `<scope_result … scope_data_typeFK="646" value="15" … ut="2020-09-13 22:21:10" …/>`, where "scope_data_typeFK= "644" refers to "Point 1"".
4. [provider claim] "A test period is available so your team can run real queries against real tennis data before making a decision".

**Unknowns and red flags:** Challenger and ITF point-level coverage is unstated, the history product is sales-only, and the licence is unknown.

**Judgement: LOW.** A 2020+ point history exists but is sold separately, and it is claimed only for tour-level ATP/WTA matches.

---

### 3.8 Data Sports Group (DSG)

**URL:** https://datasportsgroup.com/coverage/tennis/

**Data unit:** a live point-by-point feed plus serve and return stats.

**Tiers**

- The page lists ATP, WTA, ITF (subtitle), "ATP Challenger", Davis Cup and BJK Cup.
- Point-level per tier: not stated. Qualifying: not stated.

**Historical access:** "Historical Data Archives: Historical data per season" is an add-on. Whether it includes point data is not stated.

**Timestamps:** not stated.

**Price and trial:** price not stated. "Get Free API Trial".

**Licence:** not stated.

**Evidence**

1. [provider claim] "Coverage of ATP, WTA, ITF & Grand Slams Real-time Point-by-Point feeds, Ace/Fault stats, and rapid settlement in JSON/XML."
2. [provider claim] "ATP Challenger - Developmental tour competitions".
3. [provider claim] "ADD-ONS Historical Data Archives Historical data per season".

**Judgement: LOW.** The point-by-point feed is live, and the historical add-on is not stated to hold point sequences.

---

### 3.9 Podium (Podium Ltd)

**URL:** https://podiumsports.com/sport/tennis/

**Data unit:** "Point-by-Point Scoring Match scores (points, games and sets) to be updated at the end of each point. Server will be denoted." The update frequency is 2–15 seconds.

**Tiers** (from the coverage table [observed parse of the HTML table]):

- Point-by-point is Y for ATP World Tour (Singles), WTA Tour, Grand Slams (Singles) and Davis Cup (World Group).
- For Grand Slam Qualifying (Singles), the point-by-point cell is blank; game-by-game is Y.
- Challenger appears only in prose. ITF: not stated.

**Historical, timestamps, price, trial, licence:** all not stated.

**Evidence:** [provider claim] "From Grand Slam finals to early round matches on the Challenger circuits, we provide accurate, real-time data from every point."

**Judgement: NONE–LOW.** This is a live feed and states no history.

---

### 3.10 Genius Sports

**URL:** https://www.geniussports.com/newsroom/genius-sports-launches-betvision-for-tennis-in-partnership-with-infront-to-enhance-live-betting-experiences/ (22 Jan 2026)

**What it is:** BetVision for Tennis is a betting video player with "official game stats and micro markets", built on Infront content (Australian Open and ITF). No point-level data product is claimed. The DTB (German Tennis Federation) rights article could not be read (HTTP 500).

**Evidence:** [provider claim] "Through its video content partnership with Infront Bettor, Genius Sports' BetVision for Tennis will cover the Australian Open as well as International Tennis Federation ("ITF") competitions".

**Judgement: NONE.** It resells Infront content inside a betting video product, with no historical data offering.

---

### 3.11 STATSCORE

- **URLs:** https://www.statscore.com/coverage/ and https://statscore.atlassian.net/wiki/spaces/PIP/overview
- **Finding:** tennis is not listed on STATSCORE's coverage page (per fetch). LSports documentation calls the STATSCORE-powered "Points InPlay" a "Point-by-point live tracking for tennis" widget. STATSCORE's own documentation for it describes a gamification product.
- **Judgement: NONE.** It makes no point-level tennis data claim of its own.

---

### 3.12 Sportlevel, Swish Analytics, Abelson Info

- **Sportlevel** (https://sportlevel.com/): the homepage claims "Real-Time Sports Data, Live Odds, and Streaming Services". No tennis claim was found.
- **Swish Analytics, Abelson Info:** one web search each found no tennis point-level product. No provider page was read because the search quota ran out.
- **Judgement: NONE** (thinly checked).

---

### 3.13 Goalserve (additional enterprise-style feed found; not official)

**URLs:** https://www.goalserve.com/en/sport-data-feeds/tennis-api/prices and https://www.goalserve.com/en/sport-data-feeds/tennis-api/coverage

**Data unit:** "Tennis Point by Point", live game stats, odds.

**Tiers**

- "Live tennis data api is available for all ATP, WTA, Challenger and ITF tournaments".
- Qualifying: not stated. Point-level per tier: not stated.

**Historical depth:** not stated. It claims "detailed point by point tennis match history".

**Timestamps:** not stated.

**Price and trial**

- Published: "SALE Tennis Package $150" per month, "$900" for 6 months and "$1200" for 12 months on sale.
- Elsewhere on the same page it says "6-month subscription: $1000", which is inconsistent.
- "We provide free 30 days trial."

**Licence:** not stated. Data provenance is not stated (not official).

**Judgement: LOW–MEDIUM (unverified).** It is the only feed found with a self-serve price that explicitly claims point-by-point history for Challenger and ITF, but the history depth, provenance and licence are unknown.

---

## 4. Ranked summary (likelihood of getting 2019–2026 ITF/Challenger men's point-level data to a small independent project)

| Rank | Source | Point-level evidence for target tiers | 2019–2026 depth | Access for a small project | Judgement |
|---|---|---|---|---|---|
| 1 | TDI "Tennis Results" site (results.tennisdata.com) | Claimed point-by-point for all ATP and Challenger matches; a Challenger qualifying page appears in search results [search summaries only] | Unknown (site claimed launched 2025) | Free, but blocked to automated fetch; terms unknown | LOW–MEDIUM (unverified) |
| 2 | Goalserve | Claims point-by-point "match history" for Challenger and ITF (unofficial) | Not stated | $150/month, 30-day trial; licence unknown | LOW–MEDIUM (unverified) |
| 3 | Sportradar Tennis API v3 | Challenger main draw official point-by-point "from round 1"; ITF only "up to 2024" | Rolling window ≈ last 2–3 editions (≈2024/25–2026) [inference]; ITF history access not stated | Enterprise pricing; trial is evaluation-only (1,000 calls); display-only licence; prediction-market/betting use banned without consent; destroy at termination | LOW |
| 4 | Enetpulse | Point-by-point history "since 2020" (tour-level ATP/WTA); Challenger/ITF not stated | 2020+ (tour level) | "Exclusive product", sales only | LOW |
| 5 | Stats Perform / Opta | MA21 point sequence; men's tier scope not stated | Tennis archive "from 2021" | Enterprise; standard MLA bars ML training and archive-building | LOW |
| 6 | Infront Bettor (ITF) | ITF L1 point data (M15 main draw; M25 last qualifying round + main draw) from 2025; L2/L3 at M25+ streamed matches | 2025+ only; archive not stated | Licensed sportsbooks | LOW |
| 7 | LSports (ITF distributor) | As Infront, plus own scouting | Not stated | Sportsbook B2B; free trial link | LOW |
| 8 | Data Sports Group | Live point-by-point; ITF/Challenger listed | "Historical data per season" add-on; point data not stated | Free trial link; price not stated | LOW |
| 9 | TDI direct (TSDP archive/sandbox) | Umpire L1 for Challenger + qualifying; Hawk-Eye mainly at ATP Tour | "Archive" claimed in 2023; depth not stated | No stated route; exclusive distribution via Sportradar | LOW |
| 10 | Podium | Live point-by-point; Challenger only in prose | None stated | Enquiry only | NONE–LOW |
| 11 | Sportradar DDE (legacy IMG ARENA) + P&B tracking | Grand Slams incl. qualifying (live); no ITF/Challenger | None stated; legacy host decommissions 30 Sep 2026 | Betting-operator product | NONE (for ITF/Challenger) |
| 12 | Genius Sports | No point-level claim (BetVision on Infront content) | – | – | NONE |
| 13 | STATSCORE | Tennis not on its coverage page | – | – | NONE |
| 14 | Sportlevel / Swish Analytics / Abelson Info | No tennis point-level claim found (thin check) | – | – | NONE |

**Implication for the reference population** [inference]. Through official or enterprise channels:

- The about 50% of matches that are ITF main draws have no known historical route. Point data exists for 2019–2024 (Sportradar era) and 2025–2026 (Infront era), but no archive is offered.
- Most ITF qualifying matches probably never had point data.
- Challenger main draw and qualifying (about 42%) and ATP qualifying and main draw (about 8%) have official point data. The only documented purchasable route (Sportradar) reaches back only about 2–3 editions, and its licence terms conflict with prediction-market modelling.

---

## 5. Open questions the owner could resolve (no vendor contact was made by me)

1. **Open results.tennisdata.com in a normal browser.** Check:
   - whether a Challenger qualifying and a 2019–2023 Challenger match show a point sequence, with server and how each point ended;
   - how far back matches go;
   - what the site's terms of use say about reuse and automated access.
2. **Open coverage-matrix.sportradar.com in a browser**, possibly without login. Check whether Challenger and ITF seasons from before 2024 are listed, and whether play-by-play shows as full or partial for qualifying.
3. **Decide whether a Sportradar trial is worth it.** Under §3.1 of the terms, a trial may be used only to evaluate the product. It could confirm `coverage.play_by_play` for Challenger qualifying and whether any 2024 ITF seasons remain. It cannot legally be used to build a dataset or for betting-related purposes. Signing up is the owner's decision.
4. **Questions only a vendor can answer, if the owner chooses to ask:**
   - Is "Complete History" (defined in Sportradar's terms) sold for Tennis v3, including 2019–2023 Challenger timelines and 2017–2024 ITF?
   - Does the ITF or ITFL license its 2017–2024 umpire L1 archive to anyone?
   - What is the scope and price of Enetpulse's "Point by Point History" product?

---

## 6. Prior-audit items: confirmed, updated or new

**Confirmed from the 10 Sep 2026 audit**

- ITF rights moved from Sportradar to Infront for 2025 onward, with LSports distributing. Infront's deal was since extended by three years (1 Oct 2025).
- Sportradar's ITF removal: verbatim changelog dated "January 2nd, 2025".
- Sportradar's rolling catalog: "at least the current season and the two adjacent editions".
- Stats Perform: tennis archive "from 2021"; its MLA bars ML training (and also bans building archives).
- TDI's archive and sandbox: a 2023 forward-looking claim only.

**New in this pass**

- The ITF's per-tier live-scoring scope: M15 main draw only; M25 last qualifying round plus main draw; L2/L3 data at M25+ streamed matches from 2025.
- ATP Rulebook: live scoring for "each match", with qualifying at alternate venues exempt; Live ELC is mandatory only at ATP Tour events.
- Sportradar's Aug 2026 terms: display-only use, the prediction-market ban, destruction including derivatives, and the History tiers.
- The Sportradar timeline field list, with documentation example payloads.
- TDI's free "Tennis Results" site.
- Enetpulse's point-by-point history since 2020.
- Stats Perform MA21's point-level structure.
- The legacy IMG ARENA DDE feed covering Grand Slam qualifying and player & ball tracking, with the legacy host decommissioning on 30 Sep 2026.
- Polymarket's 2026 ATP deal, using Sportradar's official data [third-party report].
- Goalserve's published pricing.
