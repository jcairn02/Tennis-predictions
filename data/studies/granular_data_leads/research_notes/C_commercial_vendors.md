# Lane C: commercial and B2B vendors, and unofficial widget feeds. How wide is their per-point tennis data?

- **Accessed:** 24 Sep 2026 for everything new here. Items taken from the 23 Sep notes are marked *(R1)* for `1_self_serve_apis.md`, *(R2)* for `2_official_feeds.md` and *(R3)* for `3_tracking_and_grand_slam_feeds.md`, all in `data/studies/point_shot_sources/research_notes/`.
- **What was done:** public documentation read only. No sign-up, trial, form, vendor contact, purchase or de-obfuscation.
- **Probes:** 16 single GET requests to Sportradar's public widget backend ("gismo"), listed in §4. Every saved payload was under 5 MB and kept in the session scratchpad, not in the repository.
- **Interpreter:** scratch files were parsed with the base Miniforge interpreter (`C:\Users\zerom\miniforge3\python`), not `./python.sh`. The `tennis` environment was not touched.
- **Web searches:** 12.

**Evidence labels:** [observed] = the payload was seen (own probe, or an example the vendor publishes); [provider claim] = the vendor says so; [third-party report] = someone else reports it; [search excerpt] = a search-engine summary only; [inference] = reasoning; [not stated] = looked, found nothing. (WF) = the quote came through the web-fetch summariser, so the wording is near-verbatim. Other quotes are copied from the raw pages.

## 0. Bottom line

1. **New finding: Sportradar's public widget backend serves per-point tennis events with no key.** [observed]
   - **Where it works:** `https://lsc.fn.sportradar.com/common/en/Etc:UTC/gismo/match_timeline/{id}`. The `stats.fn.sportradar.com` host returned an identical payload.
   - **Where it doesn't:** the Live Match Tracker host (`lmt.fn.sportradar.com`) answers the same path with `"Unauthorized feed "`.
   - **What each ATP or Challenger match carries** (a Challenger qualifier was among the probes):
     - one `score_change_tennis` event per point: winner, score, a server field, `pointtype` (0 standard, 1 ace, 2 double fault) and a break/set/match-point flag;
     - one `first_serve_fault` event per fault;
     - one `service_taken` event per serve;
     - a UNIX timestamp in seconds on every event.
   - **Cross-check:** in one match, aces, double faults and first-serve faults matched Sportradar's own box score exactly.
   - **Retention is short.** Point events were present 11 days after a match and gone at 18, 25 and 59 days. Serve and game events survive at least 59 days.
   - **So this is a forward-capture route only, and reuse is unlicensed.** Sportradar says a widget `clientId` is issued "upon obtaining a license".
2. **New finding: Live Tennis API tags points with `serve` (1st or 2nd) and `outcome` (ace, double fault, winner, forced error, unforced error) from 12 Sep 2026.** [provider claim]
   - **Tiers:** all five outcomes for ATP 250/500/1000 and ATP Challenger, including qualifying. Aces and double faults only for ITF and WTA.
   - **Scale so far:** Challenger qualifying since 12 Sep has "6,881 unforced errors, 4,275 winners, 4,267 forced errors, 1,026 aces, 774 double faults".
   - **Limits:** only rows the vendor watched live; only from 12 Sep 2026; the source is unnamed ("the tour's own per-point console"); the published share is lower than what they store (134 of 197 Challenger qualifiers).
   - **Why it matters:** the only non-Slam source found that sells per-point winners, forced errors and unforced errors for Challenger.
3. **Sportradar's paid Tennis API v3 has the same per-point width as the public widget backend.** Its OpenAPI spec is public. [provider claim]
   - **Per point:** `first_serve_fault`, `result` (`ace` / `double_fault` / `server_won` / `receiver_won` / `unknown`) and an ISO timestamp. The event-type list also includes `service_fault` and `ball_position`.
   - **Missing per point:** rally length, serve speed and shot type. Winners and errors by stroke exist only as match totals, and only for Grand Slams.
   - **History:** a rolling window of the current season plus two adjacent editions.
   - **Tiers:** Challenger "Point-by-point from round 1"; WTA 250 and 125 only "from the semifinals".
4. **STATSCORE documents serve-by-serve incidents for tennis.** [provider claim] First service, first service in, service fault, net on first service, second service, double fault, ace and foot fault. It claims Challenger and ITF coverage. History depth is not stated, and the incident timeline is a paid add-on.
5. **Stats Perform, and two Sportradar betting feeds, add shot fields or tracking, but only in limited settings.**
   - **Stats Perform MA21:** per point `isFirstServe`, `shotType`, `stroke`, `isVolley` and `zone`; fullest for the WTA. Its standard licence bars ML training and archive building *(R2)*.
   - **Sportradar Live Data** (the bookmaker feed): adds bounce zones, 0–100 court coordinates and fault subtypes (foot fault, net), only for matches Sportradar scouts in depth.
   - **Sportradar DDE** (the legacy IMG ARENA feed): full shot and tracking data, Grand Slams only, live only.
6. **Everything else adds no width beyond what the project holds.** At best: score state, server and break/set/match-point flags. Enetpulse, api-tennis.com, Matchstat / Tennis-API.com and its apparent white label SportsAPI365, Goalserve, DSG, BetsAPI, Broadage, Podium, the OnCourt replay, Flashscore and the SofaScore resellers on RapidAPI.
   - **DSG:** none of its 24 tennis methods returns point history; only the live current-game fields `game_point_a/b` and `game_serve`.
   - **Enetpulse:** its per-point `ut` stamps are batch update times, not point times; in its own example all four points of a game are stamped within 1 second.
7. **Tracking:** nothing purchasable beyond R3. New items in §2.10.

## 1. Width matrix

**Codes:** D = documented; O = observed; DO = both; agg = match or set total only; inf = derivable only by inference; live = current state only, no per-point history; no = absent or explicitly not provided; NS = not stated. "Reg" = already in `source-register.md`.

| Vendor / feed | Winner & order | Server | Score | BP/SP/MP | Ace | DF | 1st-serve fault / serve no. | End type W/UE/FE | Ending stroke | Rally | Serve speed | Placement | Per-point time | Shot sequence | Tracking | Point-level history | Reg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Held, non-Slam** (SofaScore, TennisLive, LTA sample) | O | O | O | O | O | O | no | no | no | no | no | no | LTA sample only | no | no | — | — |
| **Sportradar widget backend "gismo"** | O | O (note a) | O | O | O | O | **O**; serve no. derivable | no | no | inf (serve-to-point-end seconds) | no | NS | **O** (UNIX s, per serve and per point) | no | no | points ≈11–18 days; serve/game events ≥59 days | **No** |
| **Sportradar Tennis API v3** | DO | DO | DO | live only | D | D | **DO** | agg (Tier 1) | agg (Tier 1) | no | no | NS | **DO** | no | no | rolling: current + 2 adjacent seasons | Yes |
| **Sportradar Live Data** | D | D | D | NS | D | D | **D** (+ foot fault / net) | NS | NS | NS | NS | D (zones, `posx`/`posy`; deep coverage only) | D (ms) | no | bounce zone only | NS (live feed) | No |
| **Sportradar DDE, legacy IMG ARENA** (Slams) | DO | DO | DO | DO | DO | DO | DO | **DO** | **DO** | **DO** | **DO** | **DO** | DO (ms) | **DO** | **DO** | live only | partly |
| **Stats Perform MA21 detailed** | inf | D | D | D | NS | NS | **D** | NS | **D** (codes NS) | NS | NS | D? (`zone`, meaning unclear) | D (ms) | NS | NS | from 2021 | Yes |
| **STATSCORE** incidents | D | D | D | partial | D | D | **D** | no | no | no | no | NS | NS | no | no | NS | Yes |
| **LSports** Hyper Livescore | live | live | live | live | agg/inf | agg/inf | agg/inf | agg/inf | no | no | no | no | NS | no | planned (claim) | live only | Yes |
| **Enetpulse** | inf | D (per game) | DO | no | agg | agg | agg | agg (Slams only) | no | no | no | no | batch times, not per point | no | no | since 2020 (sold separately) | Yes |
| **Live Tennis API** | D | D | DO | D | **D** | **D** | **D** (not ITF) | **D** (ATP & Challenger) | MCP only | MCP only | no | no | D (observed rows only) | MCP only | no | tags only from 12 Sep 2026 | Yes |
| **api-tennis.com / allsportsapi** | inf | DO (per game) | DO | DO | agg | agg | no | no | no | no | no | no | no | no | no | NS | Yes |
| **Matchstat / Tennis-API.com** (+ SportsAPI365) | inf | DO (per game) | DO | DO | NS | NS | NS | NS | no | no | marketing only | no | marketing only | no | no | NS | Yes / SportsAPI365 No |
| **Goalserve** | live | live | live | NS | agg | agg | NS | NS | no | no | no | no | NS | no | no | claimed, not shown in samples | Yes |
| **DSG** | live | live | live | no | agg (per set) | agg | agg | no | no | no | no | no | no | no | no | no point method | Yes |
| **BetsAPI** | live | live | live | NS | agg | agg | no | no | no | no | no | no | no | no | no | none | Yes |
| **Broadage** | no | no | set scores | no | no | no | no | no | no | no | no | no | no | no | no | ±7 days | Yes |
| **Podium** | D | D | D | NS | NS | NS | NS | NS | NS | NS | NS | NS | NS | no | no | live only | No |
| **OnCourt replay** | inf | O | O | no | no | no | no | no | no | no | no | no | no | no | no | "most matches"; depth NS | Yes |
| **Flashscore** (via Apify) | inf | 3P | 3P | 3P | NS | NS | NS | NS | NS | NS | NS | NS | NS | no | no | NS | No |
| **ITF / Infront data levels** | D (L1) | D | D | NS | D | D | NS | D (L2, streamed M25+ from 2025) | D (L2) | D (L2) | NS | NS | NS | NS | D (L3) | none stated | Yes |

- **Note a:** on a game-ending point the gismo `service` field already shows the next game's server. Take the server from the preceding `service_taken` event instead; that gave consistent ace and double-fault attribution in both matches checked [observed].
- **Could not assess:** SportDevs (DNS failed); SportsDataIO (tennis docs 404); SofaScore resellers on RapidAPI (same width as SofaScore, *R1*).

## 2. Ranked leads

### 2.1 Sportradar public widget backend ("gismo"). Not in the register.

- **URLs**
  - Per-point timeline: `https://lsc.fn.sportradar.com/common/en/Etc:UTC/gismo/match_timeline/{id}`; the same path on `stats.fn.sportradar.com` returned an identical payload.
  - Set-level box score: `match_detailsextended/{id}`.
  - Tennis tournament tree: `config_tree_mini/41/0/5`.
  - Season fixtures with match ids: `stats_season_fixtures2/{seasonId}/1`.
  - Refused: `lmt.fn.sportradar.com/common/…`.
  - Endpoint pattern documented by a third party in `github.com/victorratts13/radar-sport-api`.
- **Granularity:** point level, plus timing for each serve. No shot level.
- **Exact fields** [observed, ATP Challenger Szczecin 2026, qualifying round 1, match 74627948, 13 Sep]:
  - A point: `"type":"score_change_tennis","_typeid":"1025","uts":1789288715,"team":"away","set_score":{…},"game_score":{…},"game_points":{"home":"0","away":"15"},"service":"1","pointtype":"0","pointflag":"","pointflagtranslation":""`
  - A fault: `"type":"first_serve_fault","_typeid":"1032","uts":1789288700,"team":"home","faulttype":""`
  - A serve: `"type":"service_taken","_typeid":"1061","uts":…,"team":…`
  - Observed `pointflag` values: Game point, Break point, Set point, Match point, Game, Break, Set, Match.
- **Code meanings.** Sportradar's Live Data dictionary uses the same type ids [provider claim, `docs.sportradar.com/live-data/introduction/information-per-sport/tennis.md`]: 1025 "0 = Standard 1 = Ace 2 = Double fault opponent 3 = None 4 = Code violation point penalty …"; 1032 "Tennis service fault … 0 = Not specified 1 = Foot fault 2 = Net".
- **Validation** [observed]: `match_detailsextended` reported aces `{'home': 3, 'away': 2}` and double faults `{2, 1}`, equal to the `pointtype` counts. "1st Serve Successful" of 74/110 and 50/93 equals the 36 and 43 `first_serve_fault` events.
- **Event order** [observed]: `service_taken` 08:38:16 → `first_serve_fault` 08:38:20 → `service_taken` 08:38:26 → `score_change_tennis` 08:38:35. This makes the serve number exact [inference], and the serve-to-point-end gap is a rough proxy for rally duration [inference]. An ATP 250 match the same day (Chengdu, 74923152) had the same event types: 128 points and 46 faults.
- **New compared with held data:** first-serve fault per point (so serve number), per-point and per-serve UTC timestamps, a timing proxy for point length, an independent check on aces and double faults.
- **Coverage** [observed]: ATP (135 tournament entries), Challenger (538, including doubles), WTA, WTA 125K, UTR, team events and juniors. No ITF category.
- **History** [observed]:

  | Match | Age | Point events? |
  |---|---|---|
  | Szczecin qualifier, 13 Sep | 11 days | present |
  | Como final, 6 Sep | 18 days | gone |
  | Como qualifier, 30 Aug | 25 days | gone |
  | ATP Washington R32, 27 Jul | 59 days | gone (293 `service_taken` kept) |

  A 2024 docs example id returned "No such match" (inconclusive).
- **Finding ids** [observed]: walk the config tree, then season fixtures. The ids equal Sportradar's `sr:sport_event` numbers (73163852 from the v3 docs resolved). A finished tournament's `currentseason` already points at the next edition.
- **Access:** free, no key.
- **Terms** [provider claim]: "ClientId is a one-time indentifier each Sportradar customer gets upon obtaining a license for Sportradar products" (`apidocs.sportradar.com/…/getting-identifiers.md`). The ATP addendum bars licensees from "unofficial TDI feeds" *(R2)*.
- **Confidence: MEDIUM.** Technically trivial and observed for Challenger qualifying, but about two weeks of depth, unlicensed, and the endpoints could close.

### 2.2 Live Tennis API per-point `serve` and `outcome`. In the register (`livetennisapi_history`).

- **URLs:** `github.com/livetennisapi/openapi` (`openapi.yaml`, `CHANGELOG.md` 1.13.34–1.13.42).
- **Fields** [provider claim]:
  - `serve` (1/2): "Observed rows only: null on every reconstructed row". Stated for "ATP main tour, ATP Challenger, WTA 1000/500/250/125, UTR and the top Davis Cup tiers; not stated on the ITF World Tennis Tour".
  - `outcome` enum `[ace, double_fault, winner, forced_error, unforced_error, null]`: "ATP 250 / 500 / 1000: … outcome full … from the tour's own per-point console"; "ATP Challenger … states all five"; "The ITF World Tennis Tour: ace and double fault"; "Grand Slams and UTR: none".
  - Other row fields: `origin`, `winner`, `server`, `points`, `games`, `sets`, `is_tiebreak`, `timestamp`, `meta.enrichment`.
  - 23 Sep correction of what the endpoint publishes: Challenger qualifying `serve` "137 of 197", `outcome` "134 of 197"; ITF qualifying men's `outcome` "181 of 215".
- **Shot level:** only for Match Charting Project matches, which the project holds ("COVERAGE IS CURATED — 11,803 charted matches…").
- **New compared with held data:** per-point winners, forced errors and unforced errors for Challenger including qualifying; serve number; timestamps. Only from 12 Sep 2026.
- **Price** *(R1)*: $9.99 a month for per-match reads; $29–99 a month for bulk.
- **Terms** *(R1)* §3(c): "Scrape, cache, or store the data beyond what is reasonably necessary…". Upstream unnamed.
- **Confidence:** MEDIUM for data from now on; none for anything earlier.

### 2.3 Sportradar Tennis API v3 (licensed). In the register.

- **Schema** (public OpenAPI, `api.sportradar.com/tennis/trial/v3/openapi/openapi.yaml`):
  - Event types: `match_started, match_called, deciding_team, first_serve, period_start, point, period_score, match_ended, match_suspended, match_resumed, tie_break_points, service_fault, ball_position` (the push stream adds `stats_update`).
  - Event fields include `first_serve_fault`, `result`, `server`, `time`, `updated_time`.
  - Point types (`game, break, set, match`) appear only in the live game state.
  - No position, speed, rally or stroke property on the event object.
  - `enhanced_stats` lists match-level forehand/backhand/volley/lob winners and errors.
  - A `competitors/itf_mappings` path maps Sportradar competitors to ITF ids.
- **Tiers** (coverage page, verbatim): "2 | ATP 1000 … ATP 250, Challenger | Official data … Point-by-point from round 1"; "5 | ITF (up to 2024 only)"; "6 | WTA International, WTA 250, WTA 125k | … Point-by-point from the semifinals".
- **History and terms:** as in R2 (rolling window, evaluation-only trial, display-only licence, destroy on termination).
- **Confidence: LOW,** because of price and licence rather than width.

### 2.4 STATSCORE. In the register.

- **Source:** public Confluence pages read through its REST API: SCOUT page 3178103441 (updated 27 Jul 2026) and API page 5786861577 (updated 22 Sep).
- **Incidents** [provider claim]: score "249 | 0", "240 | 15", "241 | 30", "242 | 40", "243 | A"; serve "204 | First service", "244 | First service in", "205 | Service fault", "206 | Net - first service", "207 | Second service", "208 | Double fault", "209 | Net - second service", "210 | Service ace"; other "2253 | Foot fault", "218 | Challenge", "2216 | Set ball", "2217 | Match ball". No winner, error, stroke, rally or speed incident.
- **Coverage claim:** "ATP Tour. WTA Tour. ATP Challenger. ITF. Grand Slam."
- **Access claim:** "INCIDENTS is a separate add-on — it is not included automatically in Legend/VIP or any standard plan", at `api.statscore.com/v2/events/{id}/incidents`.
- **History and price:** not stated. **Confidence: LOW.**

### 2.5 Stats Perform MA21 detailed. In the register.

- **Source:** `developers.statsperform.com/feed-ma21-tennis-detailed-predictions`.
- **Point fields** [provider claim]: "shotType … Integer isVolley … isTeam1Serving … isFirstServe Yes Wether it is a first serve … zone Yes The zone of the team … stroke No Indicated the type of stroke. Integer". Timestamp in milliseconds.
- **Coverage levels:** "3 = Point by Point scores available along with match events (WTA)".
- **Archive and licence** *(R2)*: from 2021; the licence bars ML training and archive building. **Confidence: LOW.**

### 2.6 Sportradar Live Data (bookmaker feed). Not in the register as its own product.

- "1062 | Ball position | … sent out when the ball bounces. This event does not get sent by default … | XSA (DC)". Attributes `posx` and `posy`, each 0 to 100. Deep coverage "will enable coordinates for deeper coverage tennis matches".
- **Confidence: LOW** (licensed bookmakers only).

### 2.7 Sportradar DDE, the legacy IMG ARENA feed, with player and ball tracking (Slams). Partly in the register.

- **Rally summary keys:** `breakPoint, conclusion{stroke,result,action,speed}, decidingPoint, distance, playersDistanceTravelled, serve{side,speed}, shots…`. Per-rally events: `spin{type,rpm,rps}, speed, result, call, duration`. Ball arcs: `x`/`y`/`z` arc parameters, plus `groundMark`.
- **Delivery:** live only; the legacy DDE REST host shuts down on 30 Sep 2026.
- **Confidence: LOW.**

### 2.8 LSports Hyper Livescore. In the register.

- Running counters include "2381 | Winners", "2382 | Unforced errors", "2205 | 1st Serve Attempts (Raw)", "2410 | Aces on 1st Serve (Raw)", "2626 | Turn". A per-point type could only be recovered by differencing successive counters in the live stream [inference]. **Confidence: LOW.**

### 2.9 Enetpulse. In the register.

- Score after each point; server and hold/break per game; "we keep the pbp history since 2020 year". Winners and unforced errors are match-level and Grand Slam only. Timestamps are batch update times [observed in its own example]. **No new width. Confidence LOW.**

### 2.10 Tracking: items new since R3

- **TennisViz "Data Collection services":** "Traditional statistics (Level 2 data) … capture the key statistics in real-time". Contact by callback form only.
- **TDI platform:** "launched … in January … open 'sandbox' environment" [search excerpt]; the page still returns 403.
- **UTR Pro Tennis Tour:** since 9 Apr 2026, public live scores only.
- Not re-checked: Hawk-Eye, Golden Set Analytics, Bolt6, Foxtenn, PlayReplay, SwingVision. The R3 judgements stand.

### 2.11 No new width

- **api-tennis.com:** per point only `number_point, score, break_point, set_point, match_point` (observed documentation keys).
- **Matchstat:** its marketing example includes `serve_speed_kmh` and `updated_at`; the docs example has neither. **SportsAPI365:** probably a Matchstat white label [inference].
- **Goalserve:** its four tennis samples (34 live score, 35 odds, 72 profiles, 75 rankings) have no point elements.
- **DSG:** Challenger is covered at match and set level only (its own docs example is a Lexington Challenger 2025 match).
- **Broadage:** "Match List data can be retrieved for only ± 7 days" (corrects R1, which said it had no tennis product).
- **OnCourt:** the replay screenshot shows only score and server.
- **Podium and Flashscore:** score and server only.

## 3. Dead ends

- Sportradar LMT host refuses the "common" path; its widget docs have no tennis field documentation.
- DataCore tennis event types: on a JavaScript-rendered page that could not be read.
- IMG ARENA "Event Centre": no documentation found.
- Stats Perform's AI Q&A page: no answer on tennis coverage or archive depth.
- SportDevs: DNS failure. SportsDataIO: tennis docs 404.
- TXODDS and Swish: no tennis data product. Sporttrader: nothing found. Kambi and Oddin: not researched.
- Genius Sports: no point-level product *(R2)*.

## 4. Probe log (24 Sep 2026, UTC)

Each probe was a single `curl` request with a Mozilla user agent and no credentials.

| # | Time | Request | Result |
|---|---|---|---|
| 1 | 15:40:49 | lmt config tree | "Unauthorized feed" |
| 2 | 15:42:09 | lmt timeline 73163852 | "Unauthorized feed" |
| 3 | 15:42:18 | lsc timeline 73163852 (ATP Washington, 27 Jul) | 345 events, no point events |
| 4 | 15:42:18 | stats host, same | identical |
| 5 | 15:42:50 | box score 73163852 | set-level stats |
| 6 | 15:43:34 | timeline delta 73163852 | 0 events |
| 7 | 15:43:43 | lsc config tree | 2.7 MB; no ITF |
| 8 | 15:43:59 | fixtures, Szczecin 2026 | 51 matches |
| 9 | 15:44:08 | timeline 74627948 (Szczecin qualifier, 13 Sep) | 616 events; 203 points; 79 faults |
| 10 | 15:44:23 | box score 74627948 | matches the events |
| 11 | 15:44:57 | fixtures, Chengdu | 40 matches |
| 12 | 15:45:03 | timeline 74923152 (Chengdu, same day) | point events present |
| 13 | 15:45:13 | fixtures, Como | 49 matches |
| 14 | 15:45:19 | timeline 74171290 (30 Aug) | no point events |
| 15 | 15:45:30 | timeline 74086414 (6 Sep) | no point events |
| 16 | 15:57:02 | timeline 51041587 | "No such match" |

Disclosures: after the LMT host refused the "common" path, the `lsc` and `stats` hosts were used, which serve that path openly; no credentials were used and nothing was forged. 16 requests in total, at most 5 on any one match.

## 5. Leads passed to other lanes

- **ATP / TDI:** find "the tour's own per-point console" that Live Tennis API reads (serve number and all five outcomes for ATP and Challenger including qualifying; WTA and ITF consoles give aces and double faults only). Candidates: `results.tennisdata.com`, ATP live scoring, ITF live scores.
- **Slams:** Sportradar's Live Data lists events from "External feed (ATP, GS*)" for Roland-Garros, the US Open and Wimbledon; gismo probably holds Slam point events for about two weeks after each match [inference, not probed].
- **Open datasets:** check whether newer Live Tennis API Zenodo or bulk files are `schema_version` 2 with `serve`, `outcome` and `winner`.
- **SofaScore:** Sportradar's code-1025 list (0 Standard, 1 Ace, 2 Double fault opponent) probably explains SofaScore's `pointDescription` 0/1/2 [inference]. Check whether SofaScore's `serving` has the same next-server shift at game boundaries that gismo shows.
