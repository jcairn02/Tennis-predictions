# Lane A: ATP and WTA tour-level official data (24 Sep 2026)

All pages accessed on 24 Sep 2026. Supporting files (probe bodies and headers, `probe_log.tsv`, the Tennis Results pages and scratch parsers, the SirGenkii SQL dumps, GitHub files) were kept in the session scratchpad, not in the repository. Largest file saved: 3.3 MB.

**How the work was done:**
- Nothing was decrypted. The only check on the encrypted blobs was that each decodes from base64 to a length that is a multiple of 16 bytes, which is what an AES block cipher produces.
- Every request was a single one, spaced 2–3 s apart; most Infosys requests were HEAD requests.
- The only header change was a Chrome User-Agent plus `Referer` and `Origin` (what a browser sends).
- 9 WebSearch calls. Python from the project's `tennis` environment, run by its full path; nothing installed; no project file changed.

**Evidence labels:** [obs] = the page or data file was seen; [prov] = the organisation that runs the source says it; [3p] = someone else reports it (GitHub repo, Q&A site, blog); [search] = search-engine text; [inf] = reasoning; [n/s] = not stated.

## A. Which "per-point console" does Live Tennis API read?

Live Tennis API's own statements [3p, github.com/livetennisapi/openapi, v1.13.34–1.13.42]:
- "ATP 250 / 500 / 1000: serve stated, outcome full (ace, double fault, winner, forced error, unforced error) from the tour's own per-point console."
- "`serve` and `outcome` are joined from *different* outside sources … the tour's own per-point console does not carry team ties or Slams … but the source that states the serve number does carry them."
- "Since 2026-09-22 … a COMPLETED match is re-joined after the match against the console's complete sequence."

| Candidate | Per-point outcome and serve number public? | How far back finished matches keep them | Endpoint pattern |
|---|---|---|---|
| **results.tennisdata.com** (TDI's "Tennis Results") | **Yes [obs].** Every point carries `pointBreakdown.serve` (FIRST, SECOND, ACE or DOUBLE FAULT) and `pointBreakdown.outcome` (winner, forced or unforced), which maps onto Live Tennis API's five values; also `errorType`, `totalShots`, `winningShotType`, `situation`, serve/fault/let events and UTC timestamps. Published after the match only: "published 15 minutes after the match has concluded", "not available whilst matches are in-play" [prov, FAQ]. | The listing goes back about 3 months [prov; obs]. Older match pages return **HTTP 404 but still carry every point** [obs, 10 of 10, back to 31 Dec 2024]. Outcome filled at tour level from at least 31 Dec 2024; at Challenger level from somewhere **between 14 Jul 2025 and 17 Mar 2026**; before that, Challenger pages have serve number, ace/double fault and faults only [obs]. | `GET /en/results/{uuid}` returns HTML with the data embedded; listing `GET /en?date=YYYY-MM-DD` with `tournamentId` and `playerId` filters. The site's own API is tRPC at `/api/trpc` (not called). |
| **ProTennisLive** | **No.** `www.protennislive.com/` and `/LSHD/main.html?...` return **503** [obs]. The feeds API publishes its specification [obs], but every endpoint requires "Tournament Claims" (a bearer token) and it has **no per-point structure**, only aggregate `PointStats`. | n/a | `https://api.protennislive.com/feeds/...`, token only |
| **atptour.com live match centre** | **(a) ATP app gateway [obs, 200 with UA + Referer + Origin]:** `https://app.atptour.com/api/v2/gateway/livematches/website?scoringTournamentLevel={tour\|challenger}`: one live snapshot per match with a `KSeq` counter and an `ExtendedMessage` describing the last point ("… wins the point on the 1st serve of …"). Serve number is public while live, for the latest point only. **(b) Infosys MatchBeats:** the live route `/prod/api/match-beats/data/…` returns 403 [obs]; per point it carries `serve` (1/2) and `result` (A, DF, W, UE, FE) [3p, courtside parser]. | (a) live only. (b) static encrypted files remain for completed matches: tour level from 2021 [3p], Challenger from at least 2023 [obs]; a Buenos Aires Challenger match got its file 24 s after its last point [obs]. | (a) as above. (b) `…/static/prod/match-beats/{y}/{e}/{MID}/data.json` |

Reading [inf, medium confidence]: the "outcome console" is most likely ATP/TDI's official point feed, which both TDI Tennis Results and Infosys MatchBeats publish (same five values; ATP 250/500/1000 and Challenger including qualifying; no Slams or team ties). The separate serve-number source that also covers team ties fits the ATP gateway's `ExtendedMessage`.

## B. Ranked leads

### 1. TDI Tennis Results match pages (results.tennisdata.com)

- **Access:** Next.js on Vercel behind Cloudflare. A plain Chrome-UA GET returned 200 (the 23 Sep pass had got 403). The per-point data is embedded in the page (React Server Components payload, `self.__next_f.push`), so no JavaScript has to run [obs].
- **Granularity:** point level with how each point ended, plus match and set summaries.
- **Per-point fields, verbatim [obs]** (`ExpandedPointDetails`):
  - identity and timing: `id`, `time` (e.g. "2026-09-23T11:39:05.5770000+00:00"), `completedDateUtc` (filled on recent pages, null on old ones);
  - players and score: `winner`, `teamServing`, `playerServing`, `playerReceiving` (player UUIDs), `teamAScore`, `teamBScore`;
  - position: `setNumber`, `gameNumber`, `pointNumber`, `pointSequence`;
  - serve and point events: `rally`, a list of `SERVE`, `FAULT`, `LET`, `ACE`, `POINT_COMPLETE` events (first-serve fault flag and lets);
  - `pointBreakdown`: `outcome` (winner, forced, unforced); `serve` (FIRST, SECOND, ACE, DOUBLE FAULT); `totalShots` (rally length); `winningShotType` (serve, return, forehand, backhand, volley); `errorType` (out, net); `situation` (baseline, serving, returning, player1_at_net, player2_at_net, both_at_net);
  - flags: `ace`, `isBreakPoint`, `isBreakSave`, `isDeuce`, `gamePoint`, `setPoint`, `gameWon`, `setWon`, `streak`.
- **Per match and per set [obs]:** points won, service and return games, aces, double faults, break points, forced and unforced errors, winners, and TennisViz metrics: "Performance Rating (0-10)"; Serve, Return, Forehand and Backhand "Shot Quality (0-10)"; "Shots In Attack"; "Conversion Score"; "Steal Score". Example, Comesana v Estevez (Buenos Aires Challenger): Serve Shot Quality 7.6 v 6.6; Shots In Attack 23% v 25%; Conversion 56% v 62%.
- **Definitions [obs, `/en/definitions`]:** "Rally Length – Total number of completed shots in the rally. Shots that end in an error are not counted." "Last Shot Type – … If the last shot in the rally is an error, it is the shot type of the error that counts."
- **Which periods are filled (13 pages read) [obs]:**

  | Level | Period | Result |
  |---|---|---|
  | Tour | Brisbane, 31 Dec 2024 | full fields and TennisViz values |
  | Tour | Hangzhou, 23 Sep 2026 | full fields and TennisViz values |
  | Challenger singles | 14 Jan, 6 Mar, 17 Apr, 24 Apr (two pages), 14 Jul 2025 | winner, server, score, serve events and `time` on 100% of points; outcome, rally length, shot type and TennisViz null or "–" |
  | Challenger doubles | Sep 2025 | as the 2025 Challenger singles |
  | Challenger and Challenger qualifying | 17 Mar, 17 Apr, 18 May, 22 Sep 2026 | full fields and TennisViz values |

  [inf] TennisViz Shot Quality ("speed, spin, depth, width") at Challengers implies some ball tracking at Challengers in 2026; its source is not stated.
- **New compared with held data:** official point records for **all ATP Tour (non-Slam) and Challenger matches, singles and doubles, main draw and qualifying, from Jan 2025** [prov, FAQ: "all ATP Main Tour and Challenger Tour tournaments … Singles & Doubles main draw & qualifying"]. Width not held outside Slams and charts: first-serve fault on every point; winner / unforced / forced error; net or out; last-shot type; rally length; who was at the net; per-point UTC time; TennisViz metrics. Not included: serve speed, coordinates.
- **For the ten reference careers [inf from the ATP activity files]:** about 446 matches with full per-point outcome data (129 tour-level non-Slam matches of 2025–26 and 317 Challenger matches of 2026), plus part of their 137 Challenger matches of Jul–Dec 2025; their 302 Challenger matches of 2025 have serve and timing fields only.
- **Terms [obs, `/en/terms-and-conditions`]:** "No text or data mining, or web scraping – You must not conduct … any text or data mining or web scraping … for any purpose, including use of our Tennis Data to offer or settle bets or the development, training, fine-tuning or validation of odds feeds, statistical models or AI systems or models." The rights reservation is made under "Article 4(3) of the Digital Copyright Directive ((EU) 2019/790)". "You may use the Content for your own personal, domestic purposes only." Owners: TDI Database (UK) and TDI Database (EU). No robots.txt. A string in the site's code says "not available in your region".
- **Launch [prov, tennisdata.com story dated "4 Feb" 2025]:** "detailed results on every point played, revealing not just who won the point, but how they won it", linked to Sportradar micro-markets such as "'Total Shots' in the point".
- **Confidence:** high technically (any match whose page id is known returns the full data to a plain GET); low lawfully (the terms forbid exactly this use without TDI's permission).

### 2. Infosys ATP Stats Centre static files: MatchBeats, Rally Analysis, Stroke Analysis, Key Stats

- **Templates:** `https://itp-atp-sls.infosys-platforms.com/static/prod/{match-beats|rally-analysis}/{y}/{e}/{MID}/data.json`, `…/stroke-analysis/v2/{y}/{e}/{MID}/data.json`, `…/stats-plus/{y}/{e}/{MID}/keystats.json`: **200 to UA + Referer + Origin, 403 to a plain request** [obs]. The `/prod/api/...` routes stay 403 [obs]. Full route list in glad94's `references/api-info/atp-infosys-api-info.json` (includes `match-beats/status|data`, `stats-plus/v1/keystats`, `stroke-analysis/rally/v2`, `court-vision/belowCourt`, `assisted-journalism/insights`, `ytdStats`).
- **Payload [obs]:** `{"lastModified": <ms>, "response": "<base64>"}`. Files for 2023–2025 matches were rewritten in May–Sep 2026 [obs]; [inf] the key changes with every rewrite.
- **Encryption as others describe it (not run):** StackOverflow answer by Gabjauf, 11 Jan 2023 [3p]: "they are just using the lastModified field … as a key to encrypt the data with AES128"; key `"#" + base36(int(str(ms),16)) + base24((yr+rev(yr))*(day+rev(day)))` padded or trimmed to 14 characters, followed by `"$"`; IV = the key in upper case; CBC with PKCS7. Same method in glad94/infotennis `scrape_match_data.py`; nipunagarwalla/courtside `decrypt.py` (Jul 2026): "Source: atptour.com main.js module 326".
- **Documented fields [3p]:** MatchBeats `setData[].gameData[].pointData[]` with `server`, `scorer`, `tm1GameScore`, `tm2GameScore`, `tm1Rally`, `tm2Rally`, `serveSpeed`, `result` (A, DF, W, UE, FE), `stroke`, `serve` (1/2), `isBrkPt`, `isCspPt`. Rally Analysis: points grouped by shot number ("Serve", "Return", "3rd shot" … "10+ even shots"), each with `pointEndType` (WINNER, ACE, DOUBLE FAULT, FORCED ERROR, UNFORCED ERROR, UNCLASSIFIED), `pointId`, `serve`, `serveSpeed`, `score`, `crucialPoint`, break-point and net-point flags. Stroke Analysis: forehand/backhand by shot type with the point ids of winners and errors.
- **Coverage [obs, file exists; contents not decrypted]:** tour level (2022 ATP Finals, Paris 2025 final, Miami 2026 final, Bucharest 2026 R32, Acapulco 2026 R32); Masters qualifying (Rome 2025 Q1; Miami 2026 QS001 absent, possibly wrong id); Challenger main draw 2023, 2024, 2025, 2026 (MatchBeats 48–134 KB); Challenger qualifying 2025, 2026; ITF absent (M25 Pensacola 2026).
- **New:** serve speed on every point at tour level (TDI lacks it); Challenger point records back to 2023. [inf] Challenger files from before about 2025 probably lack point-ending type, as TDI's own 2025 Challenger records do.
- **Terms:** atptour.com prohibits "Systematic retrieval of data" and "gambling or wagering" use; Infosys terms [n/s].
- **Confidence: Medium** (files download today, but using them needs decryption and an explicit owner decision under ATP's terms).

### 3. Infosys Court Vision: ball and player tracking

- **Template:** `…/static/prod/court-vision/{y}/{e}/{MID}/data.json`: 200 with the same headers [obs]; 0.5–3.3 MB per match.
- **Fields [3p: glad94 mapping, notebook output for 2022/605/MS001, issue #7]**, keys anonymised as `a<N>`: `a12` ball trajectory x/y/z at hit, peak, net, bounce and last; `a32`/`a33` server and receiver positions; `a16`/`a21` speed (e.g. "189.34 KPH"); `a19` spin; `a20`/`a22` net clearance (e.g. "1.01 Metre"); `a23`/`a24` distance outside the court; `a93` rally length; `a95` point-end type ("Ace", "Faulty Serve"); `a90` error type; `a91` winner placement; `a96` serve type ("Slice", "Flat"); `a103` hand; `a149` "the time in seconds". Coordinates for every shot; other attributes describe the last shot.
- **Coverage [obs]:** tour level, including an ATP 250 R32 in 2026 and Masters qualifying in 2025; none for the Challenger samples.
- **New:** all of it (no coordinates held anywhere; no non-Slam tracking).
- **Confidence: Medium–Low** (same decision as lead 2).

### 4. SirGenkii/infotennis fork: committed, decrypted, processed 2025 dataset

- **Location:** https://github.com/SirGenkii/infotennis/tree/HEAD/backup_sql, committed Apr 2025 [obs].
- **Contents:** `atp_rally_analysis` (21 MB, about 136,900 main-draw point rows: `point_end_type`, `shot_number` 1…8, "9+_odd", "10+_even", `serve` 1/2, `serve_speed` (0 at some events), score, break-point and net-point flags); `atp_court_vision` (8 Monte-Carlo 2025 matches, 6,992 per-shot rows with x/y/z); `atp_key_stats` (929 matches: 645 main draw, 284 qualifying; winners and unforced errors on 888). Scope: Hong Kong, Brisbane, Adelaide and Auckland through Monte-Carlo, Jan–Apr 2025.
- **Rights:** MIT licence covers code only; data belongs to ATP/TDI [inf]. Other forks and glad94/infotennis_v2 hold no data.
- **Confidence: High** to download; small, rights unclear.

### 5. WTA official API (api.wtatennis.com)

- **Endpoints [obs, 200 to a plain request, no login]:** `https://api.wtatennis.com/tennis/tournaments/{id}/{year}/matches/{mid}/{point-by-point|stats|advanced-stats|win-probability-momentum}` (type names from the site's `store.js`).
- **Fields [obs]:** `point-by-point`: `server`, `pointWinner`, `scoreAfterPoint`, `timestamp` (UTC) for every point, no ace, double-fault or winner/error flag. `advanced-stats` (match and set level): winners, unforced and forced errors by forehand/backhand; fault reasons (net, out, foot fault); rally statistics (longest, average, 0–4 / 5–8 / 9+ shot buckets); net approaches; rich in 2026, sparse in 2022 and 2024. `win-probability-momentum`: a value for every point.
- **Depth [obs]:** point-by-point for 2022, 2024 and 2026; the 2019 request returned 404.
- **Confidence: High.** Terms not retrieved in this pass. They were retrieved later the same day and forbid automated access; see [H_wta.md](H_wta.md).

### 6. TennisViz "Tennis Insights"

- Public per match and per set on TDI pages [obs] (tour 2025–26, Challenger 2026). Tour averages on TDI: Performance Rating 7.44, Conversion 69%, Steal 31% [obs, `/en/insights`]. atptour.com has a player-level "TDI Leaderboard" [search] (Cloudflare challenge).
- Per-shot data only through TennisViz's B2B product [prov]: "ball and player tracking data" used "to calculate shot type, shot quality, situation, phase of play and tactic for every shot".

## C. Dead ends

- Infosys `/prod/api/*` routes: 403 with or without browser headers.
- atptour.com `/-/Hawkeye/MatchStats/Complete`: a box score even for a tour-level match (Paris 2025 final), with no speed, rally, distance, net or winner/error fields [obs]; the next request returned a Cloudflare challenge.
- ProTennisLive: LSHD pages 503; API token-only and without per-point data.
- ATP gateway live feed: no history once a match ends.
- Infosys Court Vision for Challengers (Heilbronn 2025, Ostrava 2026) and Infosys for ITF: files absent.
- glad94's "court_vision" flag reflects the "second screen" feature, not Court Vision coverage [3p].
- GitHub repository search ("matchbeats", "atp stats centre", …): no datasets.
- tennisviz.com: no coverage, pricing or API details.
- TDI listing: a date older than about 3 months silently falls back to today's list.

## D. Probe log (24 Sep 2026, UTC; summary)

"b" = Chrome UA plus `Referer: https://www.atptour.com/` plus `Origin: https://www.atptour.com`; HEAD-b = HEAD with the same headers.

| Time | URL | Mode | Status | Finding |
|---|---|---|---|---|
| 15:43:42–44:39 | Infosys static stats-plus, rally-analysis, stroke-analysis v2, court-vision, match-beats for 2025/352/MS001 | plain / b | 403 / 200 | encrypted envelope (`lastModified`, `response`); 31,660; 54,316; 26,028; 3,304,536; 77,712 bytes |
| 15:44:26–39 | Infosys `/prod/api` match-beats data, keystats v1, court-vision pointId 0_0_0 | plain / b | 403 / 403 | "Request blocked" |
| 15:45:09–42 | match-beats, rally, court-vision for 2026/403/MS001, 2026/403/QS001, 2025/460/MS001, 2022/605/MS001 | HEAD-b | mixed 200/403 | Challenger final: MatchBeats and Rally present |
| 15:46:48–47:15 | match-beats for 9 matches (Challenger 2023–26, Challenger qualifying, ATP 250, ATP 500, Masters qualifying) | HEAD-b | 200 ×9 | present (48–134 KB) |
| 15:47:15 | match-beats 2026/4674/MS001 (ITF) | HEAD-b | 403 | absent |
| 15:47:31–55 | rally ×4, stroke, keystats, court-vision ×3 | HEAD-b | 200 except court-vision for the Challenger match (403) | Court Vision at tour level only |
| 15:48:07–15 | range request, first 200 bytes of 4 files | b | 206 | all encrypted envelopes |
| 15:48:32–36 | atptour.com Hawkeye MatchStats 2025/352/MS001 | plain / b | 403 / 200 | box score only |
| 15:48:47 | …2026/1797/MS009 | b | 403 | Cloudflare challenge |
| 15:49:16–50:34 | results.tennisdata.com `/en`, `/robots.txt`, 2 match pages, 5 information pages | Chrome UA | 200 | points embedded in the page |
| 15:53:01; 15:56:57–16:01:43 | 11 older TDI match pages | Chrome UA | 404 | all still embed their points |
| 15:53:19; 16:03:39 | TDI `?date=2026-05-18`; `?date=2026-08-01` | Chrome UA | 200 | old date ignored; recent date works |
| 15:53:36–55:55 | WTA point-by-point ×4 (2026, 2024, 2022, 2019), stats, base URL, advanced-stats ×3, win-probability-momentum | plain | 200 except base URL and 2019 (404) | as in lead 5 |
| 15:56:39 | tennisdata.com launch story | Chrome UA | 200 | "4 Feb" 2025 |
| 15:57:44 | atptour.com TDI leaderboard | b | 403 | Cloudflare challenge |
| 16:09:05–10:04 | protennislive.com root and LSHD main page | Chrome UA | 503 | "The service is unavailable" |
| 16:10:12–36 | api.protennislive.com swagger | Chrome UA | 200/404 | token-only; no per-point data |
| 16:12:03–06 | ATP app gateway `livematches/website`, tour and challenger | b | 200 | `ExtendedMessage` snapshot of the last point |
| 16:12:49–53 | match-beats 2026/7395/MS012 (live), MS016 (finished) | HEAD-b | 403; 200 | static file written 24 s after the last point |

Also fetched: 4 TDI JavaScript chunks, 11 wtatennis.com script modules, 2 StackExchange API calls, about 70 GitHub API and raw-file reads (including range reads of the fork's SQL dumps), 2 WebFetch calls.

## E. Leads passed to other lanes

- **Slams:** hawkilol/tennisSlamBallTracking (decrypted Infosys Court Vision JSON for AO 2020–24 and RG 2019–24, plus point-by-point CSVs); tools ryurko/hawkeye, petertea96/tennis_analytics, wyatt-ai/courtvisionpython, skoval/courtvisionr, lfavole/rolandgarros-scores, glad94/tennis-web-scraping (on 19 Jun 2025 glad94 said the AO/RG code should "still work for 2025 I believe"); nipunagarwalla/courtside (backfills from IBM SlamTracker).
- **Vendors:** Sportradar "Player & Micro markets" rely on point-level fields such as "Total Shots" [prov, TDI].
- **Public websites:** a Flashscore data feed `local-global.flashscore.ninja/2/x/feed/df_st_1_{id}` (header `x-fsign`) giving match and set statistics [3p, robertyang87/tennislive; about 15 GB repo, not inspected].
