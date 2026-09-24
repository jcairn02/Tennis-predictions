# R1: Self-serve / low-cost APIs that may sell historical point-by-point tennis data

- **Status:** external-source research notes. Not a decision and not a recommendation to buy.
- **Accessed:** 23 September 2026 (all URLs below, unless stated otherwise).
- **Question:** which self-serve or low-cost vendors sell *historical* point-level (or shot-level) data for professional **men's** matches from 2019 to 2026, especially ITF M15/M25 and ATP Challenger (main draw and qualifying)?
- **Already in use, so not researched here:** Sackmann match files and Grand Slam point archive, Match Charting Project (MCP), Tennis My Life, tennis-data.co.uk, Open Tennis Data, the Live Tennis API Zenodo sample (June 2026), Polymarket.

## Labels used

| Label | Meaning |
|---|---|
| **PC** | Provider claim: the vendor's own page or docs say so. |
| **OBS** | Observed: I saw an example payload containing the data. Every OBS item here is a vendor-published documentation example or public preview. I did not audit any purchased payload. |
| **3P** | Third-party report. |
| **INF** | My inference, not evidence. |
| **NS** | Not stated. |
| *(raw)* | Quote copied exactly from the page HTML/JSON, which I downloaded with a plain HTTP GET. |
| *(WF)* | Quote returned by the web-fetch tool's summariser after I asked for verbatim text. Wording should be close, but punctuation or phrasing may be slightly normalised. |

## Method and limits

- I used public pages only. I did not sign up, log in, start a trial, submit a form, contact a vendor or buy anything. I did not try to get around any block or paywall; blocked pages are listed in §6.
- **RapidAPI listing pages** (now branded "Nokia API Hub": "Previously known as Rapid, Nokia API Hub…" *(raw)*) render client-side, so the fetch tool returned only the page title. I downloaded the public listing HTML with `curl` (no login) and read the embedded metadata: OpenAPI specs, endpoint lists and plan prices. I parsed it with scratch scripts run through `./python.sh`.
- The session's web-search quota (200/200) ran out near the end. After that I followed leads by reading pages directly.
- The reference population is ~50% ITF M15/M25 main draws, 33% Challenger main draws, 9% Challenger qualifying, 5% ATP-level qualifying and 3% ATP main draws. That is why the judgements below weight ITF and Challenger heavily.

---

## 1. Bottom line

1. **Only one self-serve vendor publishes quantified, tier-level claims of historical point sequences for ITF men: Live Tennis API.** Its coverage starts in 2023.
   - **2023 onward (PC):** of the matches in its own index, 35,377 of 35,642 ITF men's singles (99.3%), 36,710 of 36,851 Challenger men's singles (99.6%) and 16,393 of 16,476 ATP singles (99.5%) "carry a point sequence" (measured 22 August 2026).
   - **Caveats, all stated by the provider:**
     - Only **60.5%** of all completed 2023+ matches are "measured point-complete".
     - A separate statement says **"ITF point depth from 2025"**.
     - Real per-point timestamps exist only on rows the vendor watched live. Capture started on 12 October 2025, and those rows appear in the product from March 2026.
     - The 2023–2025 sequences are post-match reconstructions from an **unnamed third-party feed**.
   - **2013–2022 archive:** ITF is explicitly **not covered** (68 of 19,162 M15 and 48 of 9,380 M25 matches have a tape). Challenger has 55.3% of main draws and 33.6% of qualifying (2013–2022 pooled). None of those rows has a timestamp.
2. **api-tennis.com and allsportsapi.com** return a `pointbypoint` array inside every fixture.
   - Their docs show a finished **17 June 2022 ITF M25 Wichita** men's match with point-level rows (OBS, abbreviated).
   - Both sites use identical example event keys, so they probably share one backend (INF).
   - Historical depth and per-tier completeness are **not stated**. The 14-day trial is the cheapest way to measure them.
3. **Low-cost RapidAPI wrappers of SofaScore** (TennisApi, AllSportsApi, SofaSport) expose a per-match `point-by-point` endpoint for $0–$25 a month.
   - AllSportsApi states: "Data sourced from sofascore public endpoints" *(raw)*.
   - Historical depth for ITF and Challenger is **not stated**, and the chain of licences is a red flag.
4. **Matchstat / Tennis-API.com** and **Goalserve** both claim point-by-point, but for neither is historical depth stated. Matchstat's pbp is part of its "live" endpoint family and uses a score-string format.
5. **BetsAPI** keeps history since September 2016, but none of its historical endpoints documents tennis point-level content. Its bet365 in-play tennis sample holds only the current point score.
6. **Nothing self-serve offers shot-level data or ball/player tracking for ITF or Challenger.**
   - Live Tennis API's Ultra tier offers "shot-by-shot rally construction" for 11,822 charted matches back to 1960. Its scale and fields look like MCP-style charting (INF), which the project already has.
7. **The 2019–2022 ITF gap stays open.** No self-serve source documents point-level ITF men's coverage for 2019–2021. For 2022 there is one abbreviated docs example (api-tennis.com / AllSportsAPI).

## 2. Ranked summary

Judgement = how likely the source is to provide point-level data for 2019–2026 ITF and Challenger men's matches.

| Rank | Source | ITF men 2019–22 | ITF men 2023–26 | Challenger men 2019–22 | Challenger men 2023–26 | Per-point wall-clock time | Cheapest documented route to history | Judgement |
|---|---|---|---|---|---|---|---|---|
| 1 | **Live Tennis API** | **No.** "ITF not covered" (PC) | **Yes (PC).** 99.3% of indexed ITF men's singles have a sequence. But "ITF point depth from 2025"; 60.5% point-complete overall | **Partial (PC).** Main 55.3%, qualifying 33.6% (2013–22 pooled) | **Yes (PC).** 99.6% of indexed | Observed rows only (capture from 12 Oct 2025; in product from Mar 2026) | $49 one-off = 1 month of Pro-level access including bulk downloads; or $9.99/mo per match | **High for 2023–26; none for ITF 2019–22; medium for Challenger 2019–22** |
| 2 | **api-tennis.com / allsportsapi.com** (shared backend, INF) | Unknown. One 2022 ITF M25 docs example has pbp (OBS) | Field documented; share NS | Unknown | Field documented; share NS | None per point | 14-day trial; then $40/mo (api-tennis) or $82/mo "World Wide" (AllSportsAPI) | **Medium** |
| 3 | **SofaScore-derived RapidAPI wrappers** (TennisApi, AllSportsApi, SofaSport) | NS | NS. 3P: in one recent scraper run, 29 of 30 Challenger+ITF matches had pbp | NS | NS | NS | Free tiers (50/day to 200/month); paid from $9.99/mo | **Low–medium**, plus a licensing red flag |
| 4 | **Matchstat / Tennis-API.com** (RapidAPI "Tennis API – ATP WTA ITF") | NS | NS | NS | NS | None in example | RapidAPI Ultra $59/mo (pbp tier per vendor) | **Low** |
| 5 | **Goalserve** | NS | NS | NS | NS | NS | 30-day free trial; $150/mo | **Low** |
| 6 | **Apify scraper actors** (SofaScore, Flashscore) | NS | NS | NS | NS | NS | Pay per result (~$0.004–$0.008 a match; "$5.00 / 1,000 match point-by-points") | **Low.** Unlicensed scraping, not a data vendor |
| 7 | **BetsAPI** | No point-level content documented | Same | Same | Same | n/a | Tennis events API $10/mo | **None / very low** |
| – | SportDevs | Site unreachable on 23 Sept 2026 | | | | | | Unknown |
| – | SofaScore (apidojo), Tennis Live Data (sportcontentapi) on RapidAPI | Listing content not retrievable | | | | | | Unknown |
| – | Sportmonks, Broadage | No tennis product | | | | | | None |
| – | Ultimate Tennis (RapidAPI), live-tennis-api.com (a different company from livetennisapi.com) | No point-by-point claim found | | | | | | None |
| – | Data Sports Group, Sportradar, TheSports | Sales-led or enterprise; not self-serve | | | | | | Out of scope |

---

## 3. Source by source

### 3.1 Live Tennis API (livetennisapi.com), operated by JSB Holdings LLC

**URLs**

| Page | URL |
|---|---|
| Product | https://livetennisapi.com/historical-tennis-data-api |
| Academic | https://livetennisapi.com/data/academic |
| Core pricing | https://livetennisapi.com/pricing |
| Terms | https://livetennisapi.com/terms |
| Docs | https://docs.livetennisapi.com/reference.html |
| OpenAPI | https://github.com/livetennisapi/openapi |
| Counts | https://livetennisapi.com/facts.json |
| Studies | https://blog.livetennisapi.com/studies.json and https://blog.livetennisapi.com/blog/tennis-hold-rate-by-surface |
| Operator's self-measurement site | https://besttennisapi.com/methodology |

**Operator:** "Provider: JSB Holdings LLC, a Delaware limited liability company" *(raw, terms)*.

**Data unit**
- **Content:** a point sequence (the score state after each point), with the server and the point winner. It also carries tape-level flags for provenance and completeness, and a model win probability on rows the vendor watched live.
- **Not included:**
  - "Serve speed, serve direction and shot-level data are not in the dataset." *(raw, academic)*
  - "a historical score sequence does not let you recover unavailable first-serve attempts, serve speed, medical incidents or real court timestamps." *(raw, product)*
- **Per-point flags:** there are no ace or double-fault flags per point (NS). The academic page lists "who served, the score before and after each point, break points, tiebreaks" *(WF)*.

**Per-point fields (docs, WF):** `set`, `game`, `number` (point within game), `score`, `sets`, `games`, `server`, `winner` ("null if not attributable"), `timestamp` ("null on reconstructed tape"), `win_probability_p1`, `pbp_coverage` (`"point"` or `"game"`).
- The public preview rows (OBS, *raw*) show that the archive rows use `point_winner`:
  - Observed row: `"timestamp": "2026-07-27T21:08:22.773825Z", "win_probability_p1": 0.39962309494767223, "danger": 0.05732571932609154`
  - Archive row: `"point_winner": 2, "timestamp": null, … "win_probability_p1": null, "danger": null`
  - Archive metadata: `"point_source_detail": "reconstruction from public record"`

**Coverage and provenance flag names**
- **`coverage`:** `from_start`, `partial`, `reconstructed`, `reconstructed_partial` or `none` *(WF)*.
- **`meta.point_source`:** `observed`, `mixed` or `reconstructed` *(WF)*.
- **`meta.points` verdict:** "Every tape read carries a meta.points verdict measured for that match. Where that verdict is complete, ?points=complete serves the sequence in full: score after each point, with server and point winner." *(raw)*
- **Row level:** `pbp_coverage`, where `"game"` means only the score path at game level *(WF docs)*.
- **Archive labels:** "reconstructed, on 94,307 matches (96.33%) … reconstructed_partial on 3,594 (3.67%)" *(raw)*.

#### Two collections

**(a) 2013–2022 "reconstructed archive"**
- "97,901 ATP, WTA and Challenger matches played between 2013 and 2022, 14,340,663 point rows." *(raw)*
- "It is rebuilt from the public record, not a recording" *(raw)*
- "Tours: ATP, WTA and Challenger. ITF not covered" *(raw)*
- "Challenger sits inside the ATP figure, since it is ATP-sanctioned." *(raw)*
- "30,306 of the 97,901 matches (31.0%) are qualifying play, and 67,595 (69.0%) main draw." *(raw)*
- "Every season from 2015 on is wholly point-granular." *(raw)*

**(b) January 2023 onward "tape"**
- "The live point-by-point tape runs from January 2023 through September 2026, across ATP, WTA, Challenger, ITF and doubles." *(raw)*
- "Four tours. ATP, WTA, Challenger and ITF, singles and doubles. ITF point depth from 2025 via the governing body's own umpire feed." *(raw)*
- "Earlier matches (all of 2023 to 2025) carry point sequences expanded after the match from a third-party feed, without capture timestamps." *(raw, academic)*

#### Coverage by men's tier

**Table A: 2013–2022 archive.** Source: "Tape coverage by tier and draw, measured September 1, 2026", a list of selected tiers *(raw)*.

| Tier | With tape | Played | Share |
|---|---|---|---|
| ATP Masters, main | 4,775 | 4,837 | 98.7% |
| ATP Grand Slam, main | 4,702 | 4,797 | 98.0% |
| ATP 250/500, main | 12,219 | 12,802 | 95.4% |
| ATP Challenger, main | 23,802 | 43,038 | 55.3% |
| ATP Challenger, qualifying | 7,212 | 21,455 | 33.6% |
| ATP Grand Slam, qualifying | 706 | 4,412 | 16.0% |
| ITF and futures, all draws | 141 | 145,117 | under 0.1% |

- "ITF and futures are not covered. Only 25 of 116,575 ATP futures, 68 of 19,162 ITF M15 and 48 of 9,380 ITF M25 matches carry a tape. If your work is ITF, this corpus is not for you…" *(raw)*
- **Year by year:** "Coverage roughly doubles from 2017 on and holds there, and 2020 is the short covid season. Year by year: 2013 14.0%, 2014 13.2%, 2015 13.6%, 2016 12.5%. Then 2017 21.3%, 2018 22.9%, 2019 22.7%, 2020 25.9%, 2021 25.5%, 2022 24.2%." *(raw)*
  - The page gives no year-by-tier breakdown.
  - These yearly shares seem to use the whole results table as the denominator, uncovered ITF and futures included (INF).

**Table B: 2023 onward.** Source: academic page, "Numbers measured 2026-08-22 on the production database" *(raw)*. I computed the percentages.

| Tier | Completed matches | With point sequence | Live-observed |
|---|---|---|---|
| ITF men (singles) | 35,642 | 35,377 (99.3%) | 4,896 (13.7%) |
| Challenger men (singles) | 36,851 | 36,710 (99.6%) | 4,305 (11.7%) |
| ATP (singles) | 16,476 | 16,393 (99.5%) | 1,785 (10.8%) |
| Challenger men (doubles) | 9,999 | 9,880 | 846 |

- **Overall, all tours (PC):**
  - facts.json: `"matches_with_tape": 179578`, `"completed_matches": 187832`, `"share": "96%"`, `"point_complete_share": "60.5%"`.
  - "As of September 21, 2026, 60.5% of completed matches since 2023 are measured point-complete, and the running backfills keep raising that share." *(raw)*
  - Academic: "98.2% of them (170,527 matches) carry a point-by-point score sequence" *(raw)*.
- **Hold-rate study (PC, WF):** "ITF (men): 529,948 service games", "counted from the point-by-point tape" (2023-01-01 to 2026-09-14, finished best-of-three singles). On their own ITF+Challenger count, the product page says: "91,883 of those matches are Challenger or ITF, the tier most public tennis data stops short of." *(raw)*

**Per-tier status against the requested list**

| Tier | 2013–2022 | 2023+ | Earliest claimed year |
|---|---|---|---|
| ITF M15/M25 main | No (<0.4%) | Yes for sequences (99.3% of indexed ITF men's singles); "point depth from 2025" | 2023 (sequence); 2025 ("ITF point depth") |
| ITF qualifying | No | Unknown. No draw split published; round codes `Q`, `Q1`–`Q4` exist (docs) | NS |
| Challenger main | Partial, 55.3% | Yes, 99.6% of indexed Challenger men's singles (main and qualifying not split) | 2013 |
| Challenger qualifying | Partial, 33.6% | Unknown split | 2013 |
| ATP main | 95.4–98.7% | Yes, 99.5% | 2013 |
| ATP qualifying (non-Slam) | NS (not in the "selected tiers" table) | NS | NS |
| Grand Slam qualifying | 16.0% | NS | 2013 |
| Davis Cup | NS. A `davis_cup` tier code exists (docs, WF) | NS | NS |

#### Historical access

- **Per match:**
  - `GET /history/matches/{matchId}` for 2023+ tape (Basic plan or higher).
  - `GET /history/archive/matches/{archiveId}/tape` for 2013–2022 *(WF docs)*.
- **Bulk:** `GET /history/packages/{period}` (monthly JSONL + CSV).
  - "GET /history/packages/{YYYY}?kind=archive_tape (core ULTRA, or Historical Data Pro, Business or an active one-off package)." *(raw)*
- **Coverage roll-up:** `GET /history/coverage`, "Measured completeness rollup per tour × draw bucket" (Basic) *(WF docs)*. This is the endpoint that would give 2023+ coverage per draw.
- **Missing tapes:** "A match with no tape answers 404 not_found, which is also the answer when a tape exists and failed the identity proof." *(raw)*

#### Timestamps

- "Real UTC timestamp on every observed row. Observed rows begin March 2026. Capture itself started 12 October 2025 at low volume." *(raw)*
- "As of August 27, 2026, 25,747 completed matches carry at least one, across 6.2 million such rows." *(raw)*
- Archive: "Every row is null on timestamp, win_probability_p1 and danger" *(raw)*.
- The archive date field "is the tournament start date, not the date or start time of this final." *(raw)*
- The academic match index includes "scheduled time (UTC)" *(raw)*.

#### Price and trial

- **Core API:**
  - Free: "100 requests/day"; no history.
  - Basic: $9.99/mo ($99/yr). Includes "Historical match results (completed matches)" and "Point-by-point match tape, per match".
  - Pro: $29.99/mo ($299/yr). Adds "Bulk history packages (monthly downloads)".
  - Ultra: $99.99/mo ($999/yr). Adds "Shot-by-shot rally construction … (11,822 charted matches, both tours, back to 1960)" *(WF, pricing)*.
  - "A History plan adds the point-by-point tape to a free API key without changing tier" *(WF)*.
- **History plans** *(raw)*: "Starter Pro Business Price $29/mo $99/mo $299/mo". Starter gives per-match reads. Pro adds "Bulk monthly downloads" and "2013-2022 archive, per-year files". Business adds "Year-scale package exports".
- **One-off packages:** "$49 for a full month of history, or $399 for a full year. While it's active, a package works as Pro-level access for its window. That means tape reads (both halves, including the 2013-2022 archive), its per-year archive files and the bulk monthly downloads." *(raw)*
  - This reads as an access window, not one month of data.
- **Academic (free):** "Access is free for non-commercial academic research and teaching. Data is delivered as bulk CSV snapshots with a seven-day embargo after match completion." *(raw)*
  - The reconstructed 2023–2025 point layer "is not in the public files. Availability under the programme is decided per request." *(raw)*
- **Free trial of history:** NS.

#### Licence

- **§1:** "JSB Holdings grants you a limited, non-exclusive, non-transferable, revocable license. It covers accessing the API and using its responses within your own applications and services." *(raw)*
- **§3 Acceptable Use:** "(a) Resell, redistribute, sublicense, or republish the raw API responses as a competing data feed or bulk dataset. … (c) Scrape, cache, or store the data beyond what is reasonably necessary to operate your application." *(raw)*
- **§4:** the data compilation "and all model outputs … are the property of JSB Holdings" *(raw)*.
- **§5:** "Sports data and model outputs are provided for informational purposes only and are not betting, wagering, investment, or financial advice." *(raw)* This is a disclaimer, not a ban on betting use.
- **ML training:** NS in the terms. The marketing says "Built for analysis. Structured for backtesting, model training and match research." *(raw)*
- **Product page:** "Need observed serve statistics, a particular qualifying draw, or commercial storage and redistribution rights? Confirm the exact coverage and terms for your use." *(raw)*
- **Academic terms:** "non-commercial research and teaching only · no redistribution of raw data … Commercial use converts to commercial terms." *(raw)*

#### Unknowns and red flags

1. **The denominator is the vendor's own index.** "Completed matches" means matches in their index. Whether that index contains every ITF M15/M25 main-draw and qualifying match is NS. 35,642 ITF men's singles matches over about 3.6 years (~9,900 a year) should be checked against an independent count, for example the project's own ITF results (INF).
2. **ITF depth is internally inconsistent.** 99.3% of ITF men's singles have a "point sequence" from 2023, yet "ITF point depth from 2025". The 2023–2024 ITF tapes may be partly `pbp_coverage: "game"` or incomplete (INF). The point-complete share for ITF alone is NS.
3. **Upstream of the 2023–2025 reconstructions is unnamed** ("a third-party feed"), so the licence chain is unknown.
4. **The capture start date appears two ways:** "12 October 2025" and "Observed rows begin March 2026". Both appear verbatim; they describe capture start and product inclusion respectively.
5. **Storage is the key licence risk.** Terms §3(c) conflicts with bulk-download-and-train use. Written confirmation would be needed (per the vendor's own "Confirm the exact coverage and terms" prompt).
6. **Two parallel price ladders** (core Basic/Pro/Ultra vs History Starter/Pro/Business) name different "Pro" plans.
7. **The metrics are self-published.** "besttennisapi.com is operated by JSB Holdings LLC, which also operates Live Tennis API. This site is not independent." *(WF)*
   - The vendor does state: "Across three independent audits, 70 matches were checked against outside sources (Wikipedia draws, a third-party vendor) with 0 mismaps." *(raw)*
8. **The source of the 2013–2022 "public record" is not named.** It may overlap open pre-2018 point-by-point sources (INF, not verified).
9. **The Ultra rally-construction corpus (11,822 matches, back to 1960) has no stated source.** Its size and fields ("serve direction, every stroke with its wing, direction and depth, the rally length", WF) resemble MCP-style charting (INF). The project already holds MCP.

**Judgement**
- **2023–2026: high.** It is the only self-serve vendor with explicit, dated, per-tier counts for ITF men and Challenger men.
- **2019–2022 ITF: none.** Explicitly excluded.
- **2019–2022 Challenger: medium.** 55.3% of main draws and 33.6% of qualifying, pooled over 2013–2022, with no year-by-tier split.

---

### 3.2 api-tennis.com (and allsportsapi.com, which appears to share its backend)

**URLs**

| Page | URL |
|---|---|
| api-tennis.com (pricing is on the homepage) | https://api-tennis.com/ |
| Docs | https://api-tennis.com/documentation |
| WebSocket | https://api-tennis.com/documentation_websocket |
| Terms | https://api-tennis.com/terms-of-use |
| AllSportsAPI tennis | https://allsportsapi.com/tennis-api |
| AllSportsAPI docs | https://allsportsapi.com/tennis-api-documentation |
| AllSportsAPI terms | https://allsportsapi.com/terms-of-use |

**Shared backend (INF):** both docs pages use the same example matches, event_key 143104 (Navone vs Gomez-Herrera, Corrientes Challenger) and 143113 (Chidekh vs Cassone, ITF M25 Wichita), both dated 2022-06-17 *(raw)*.

**Data unit (OBS, docs example)**
- A `pointbypoint` array per game: `set_number`, `number_game`, `player_served`, `serve_winner`, `serve_lost`, `score` (games after the game), and `points[]` with `number_point`, `score`, `break_point`, `set_point`, `match_point`.
- Match-level `statistics` sit alongside.
- Per-point ace/DF, serve speed, rally length and timestamps: none shown (NS).
- "Returns tennis fixtures included in your current subscription plan. Each match also includes pointbypoint, scores and statistics inline (empty arrays when not yet available) — no separate call is needed for a match's set scores or per-player statistics (aces, serve percentages, break points, etc.)." *(raw, api-tennis docs)*

**Example (OBS, raw, api-tennis docs, abbreviated by the vendor with `.........`)**
```
"event_key": "143113", "event_date": "2022-06-17", "event_time": "01:05",
"event_final_result": "2 - 0", "event_status": "Finished",
"event_type_type": "Itf Men Singles", "tournament_name": "ITF M25 Wichita, KS Men",
"pointbypoint": [ { "set_number": "Set 1", "number_game": "1", "player_served": "First Player",
  "serve_winner": "First Player", "serve_lost": null, "score": "1 - 0",
  "points": [ { "number_point": "1", "score": "15 - 0", "break_point": null,
                "set_point": null, "match_point": null }, ......... ] }
```

**Coverage by men's tier**

| Tier | Point-level | Evidence |
|---|---|---|
| ITF M15/M25 main | Field present; one 2022 example populated (OBS) | Above |
| ITF qualifying | Unknown | `"event_qualification": "False"` field exists *(raw)*; the draw endpoint has `include_qualification` ("also include qualification/wild-card brackets", WF) |
| Challenger main | Field present; share NS | The Challenger example was not yet played (`"pointbypoint": []`) |
| Challenger qualifying | Unknown | |
| ATP main | Field present; share NS | "Atp Singles" is an event type |
| ATP qualifying | Unknown | |
| Grand Slam qualifying | Unknown | |
| Davis Cup | NS | Not among the example event types |

- **Earliest claimed year:** NS. The docs examples date from 2022.
- **Historical access:** `get_fixtures` with `date_start` / `date_stop` (plus event_type, tournament, season, match and player filters), per request. No bulk export is documented. The docs' parameter table gives no lookback limit or earliest date (NS).
- **Timestamps:** match `event_date` / `event_time` only, with a timezone parameter. No per-point time.

**Price and trial**
- **api-tennis.com:** Starter $40/mo (8,000 requests/day), Premium $60 (80,000), Business $80 (200,000; adds in-play odds and WebSockets), Ultra $120 (2,000,000). "14 day trial". Discounts of −5%, −10% and −15% for 3, 6 and 12 months *(WF)*.
- **AllSportsAPI tennis:**
  - "ATP PLAN" covers "ATP single and ATP double" only.
  - "WORLD WIDE PLAN" and "ULTIMATE PLAN" have "All Tournaments included".
  - All three list "Point By Point" and a "14 day trial".
  - Shown prices are $59, $82 and $111 a month. These appear to be 25%-off prices from $79, $109 and $149 (WF extraction was ambiguous; INF).

**Licence**
- **api-tennis.com:**
  - "Accounts are individual and must not be shared with other developers."
  - "The data is provided as is and no guarantees are provided."
  - "We hold no responsibility for how you use the feed or the consequences of using our data." *(WF)*
  - Storage, ML training and betting: NS. Company name: NS.
- **AllSportsAPI (operator "SC Sattina Softacular Concept SRL", Romania):**
  - "distribution, transfer and storage of the data provided by the Service are allowed, but re-selling the Product offering of AllSportsAPI.com is prohibited without the prior permission"
  - It also says "The use of material of AllSportsAPI.com is solely provided for your personal, non-commercial use." *(WF)*, which contradicts the first clause.
  - Betting: users must be "over 18 years of age" and "the availability of odds is not guaranteed" *(WF)*.
  - ML training: NS.

**Unknowns and red flags**
- Historical depth is not stated anywhere, and neither are per-tier completeness and the data source.
- The only pbp example is abbreviated.
- The docs describe fixtures "included in your current subscription plan", but tier gating is not listed on the api-tennis plans.
- AllSportsAPI's cheapest plan is ATP-only.
- `/pricing` and `/coverage` return 404.

**Judgement: medium.** It is the only low-cost source besides Live Tennis API whose own docs show a finished ITF M25 men's match (2022) with point-level rows, and a 14-day trial could measure 2019–2026 depth. But depth, completeness and provenance are all unstated.

---

### 3.3 BetsAPI (betsapi.com / b365api.com)

**URLs**

| Page | URL |
|---|---|
| Docs home | https://betsapi.com/docs/ |
| Events summary | https://betsapi.com/docs/events/ |
| Event View | https://betsapi.com/docs/events/view.html |
| Ended | https://betsapi.com/docs/events/ended.html |
| Event History | https://betsapi.com/docs/events/history.html |
| Stats Trend | https://betsapi.com/docs/events/stats_trend.html |
| bet365 Result | https://betsapi.com/docs/bet365/result.html |
| bet365 in-play tennis sample | https://betsapi.com/docs/samples/bet365_event.tennis.json |
| Pricing | https://betsapi.com/mm/pricing_table |
| API spec (HTTP 403) | https://betsapi.com/api-doc/index.html |
| Website tennis pages (HTTP 403) | e.g. https://betsapi.com/tennis/l/17951/ITF-M15-Eupen |

**Data unit**
- **Event View** (`/v1/event/view`): its samples are soccer, basketball and table tennis. No tennis example, and tennis contents NS.
- **Soccer sample `events` (OBS):** incident strings such as "12' - 1st Corner - Man City".
- **Event History:** "History events of Home/Away Team before this event" *(WF)*. These are head-to-head past matches, not a point history.
- **Stats Trend:** "Soccer only. Only available for events after Oct 2019." *(WF)*
- **bet365 Result:** no tennis example; its sample is soccer *(WF)*.
- **bet365 in-play tennis sample (OBS):** only the current state, e.g. `"XP": "15-15"` (current point score) and `"SS": "3-6,0-1"`. No list of earlier points *(WF)*.

**Coverage by men's tier**
- Point-level is **not documented for any tier**.
- ITF M15 events exist on the site (3P: search listings titled e.g. "ITF M15 Tokyo - Tennis - BetsAPI"). The pages themselves returned HTTP 403.

**Historical access**
- `GET /v3/events/ended?sport_id=…&day=YYYYMMDD`. The `day` parameter is "min 20160901"; "we only allow max page=100 on all time" *(WF)*.
- "keeps history data (since Sep 2016)" *(WF, events summary)*.
- **Timestamps:** n/a for points.

**Price and trial**
- "Other Sports (… Tennis …)" costs "$10/mo" each, at 3,600 requests/hour.
- The bet365 API costs "$150/mo". Trials: "1-Day Trial … $1.00/1d" and "3-Day Trial … $5.00/3d", with "The price will be doubled up after each buy" *(WF)*.

**Licence:** not retrieved, because the website returns 403. Storage, ML and betting terms: NS.

**Unknowns and red flags**
- What a tennis Event View contains (perhaps game-level text; INF, unverified).
- The main site and API spec are blocked to automated reads.

**Judgement: none / very low.** No historical endpoint documents tennis point sequences, and the only tennis sample carries just the live current point.

---

### 3.4 Goalserve (goalserve.com)

**URLs**

| Page | URL |
|---|---|
| Prices | https://www.goalserve.com/en/sport-data-feeds/tennis-api/prices |
| Description | https://www.goalserve.com/en/sport-data-feeds/tennis-api/description/14 |
| Coverage | https://www.goalserve.com/en/sport-data-feeds/tennis-api/coverage |
| Samples | https://www.goalserve.com/en/sport-data-feeds/tennis-api/samples |
| Live-score sample | https://www.goalserve.com/en/sport-data-feeds/tennis-api/sample/34 |
| Terms | https://www.goalserve.com/en/terms-and-conditions |

**Claims (PC, WF)**
- "We provide detailed point by point tennis match history. Live point by point scores are updating every 5 seconds."
- The Tennis Package includes "Tennis Live score data," "Tennis Point by Point," "Tennis Live game stats," "Tennis Odds comparison," "Tennis Profiles".
- Coverage: "ATP tour, WTA tour, Challenger, Olympics, ITF, Davis Cup, Fed Cup, Exhibition games, Juniors".
- In the coverage table, Challenger and ITF carry a different icon for "Live Stats / Lineups" (INF: possibly limited).

**Observed:** the live-score sample shows set and game scores but no point elements (OBS of absence). No separate point-by-point sample is listed.

**Coverage by men's tier:** point-level NS for every tier.

**Historical access:** access by date and archive depth are NS.

**Timestamps:** NS.

**Price and trial:** Tennis Package "$150/month". Full package "$800/month". "We provide free 30 days trial." *(WF)*

**Licence:** the general T&Cs I read had no data-use clauses on storage, redistribution, betting or ML *(WF)*.

**Red flags:** the "point by point … match history" claim sits next to a live-update statement, with no documented archive.

**Judgement: low.** The claim is unquantified and appears live-oriented, and no historical retrieval is documented.

---

### 3.5 RapidAPI tennis APIs

**Method note:** everything marked *(raw)* in this section was read from the listing's embedded metadata. The listing HTML also contains "Bandwidth Platform Fee … A platform fee for bandwidth usage. Each unit is 1MB." *(raw)*, so bandwidth charges may apply on top of plan prices.

#### 3.5a TennisApi (provider "fluis.lacasse", host `tennisapi1`)

**URLs:** https://rapidapi.com/fluis.lacasse/api/tennisapi1 and the provider's examples at https://github.com/lacassef/recodex-api-examples

**Point-by-point endpoint (raw, embedded OpenAPI):** `/api/tennis/event/{id}/point-by-point`, "Get point-by-point data", "Retrieves a detailed, chronological list of points and games for a tennis match."
- A 204 response means "No content. The requested route exists but there is no data available for the given parameters".
- The response schema is a generic `JSONResult`, so fields are not documented.

**Historical discovery routes (raw):** `/api/tennis/events/{day}/{month}/{year}`, `/api/tennis/tournament/{tournamentId}/season/{seasonId}/events/last/{page}`, `/api/tennis/player/{id}/events/previous/{page}`. Access is per match; there is no bulk export.

**Stated origin:** "All statistics and informations provided by this API are from third party sources, we only collect, organize and provide them." *(raw)*
- The route set mirrors SofaScore's public API: `tennis-power`, `graph/sequence`, `votes`, `cup-trees` (INF).
- Its sibling AllSportsApi, from the same provider, says outright that it is SofaScore-sourced (§3.5b).

**Description:** "TennisApi offers tennis scores for more than 500 tennis tournaments…" *(raw)*

**Per-point fields:** NS in this listing. For the SofaScore structure as reported by a scraper, see §3.6 (3P).

**Plans (raw):** BASIC $0 (50 requests/day, hard limit); PRO $9.99/mo (15,000/day); ULTRA $14.99/mo (50,000/day); MEGA $24.99/mo (quota not parsed).

**Terms:** `"termsOfService":null` *(raw)*. RapidAPI's marketplace terms apply (not reviewed). No SofaScore licence is stated.

**Coverage by men's tier:** point-level NS for every tier. Earliest year NS.

**Judgement: low–medium.** The endpoint exists and is cheap to probe. Historical ITF and Challenger depth is undocumented, and the data is resold SofaScore output with no stated licence.

#### 3.5b AllSportsApi (same provider; host `allsportsapi2`; not related to allsportsapi.com)

**URLs:** https://rapidapi.com/fluis.lacasse/api/allsportsapi2 and the OpenAPI at https://github.com/lacassef/recodexapicodeexamples/tree/master/allsportsapi/openapi

- **Origin:** "Data sourced from sofascore public endpoints" *(raw)*.
- **Endpoint:** the tennis event route's allowed values include `point-by-point` ("Allowed values: duel, graph, highlights, odds, official-tweets, point-by-point, statistics, streak, tennis-power, votes.") *(raw)*.
- **Plans (raw):** BASIC $0 (100/day); PRO $19.99; ULTRA $39.99; MEGA $59.99 (quotas not parsed).

**Judgement:** as for 3.5a, low–medium, with an explicit SofaScore-sourcing red flag.

#### 3.5c SofaSport (provider "tipsters", host `sofasport`)

**URLs:** https://rapidapi.com/tipsters/api/sofasport and the tutorial at https://sofasport.rapi.one/Complete_Tutorial

- **Endpoint:** `/v1/events/point-by-point`, "Get point by point data by event_id. (tennis)" *(raw)*.
- **Origin:** "You get data similar to: (Opta sports) statsperform.com , sofascore.com, aiscore.com" *(raw)*.
- **Plans (raw):** BASIC $0 (200/month); PRO $15 (10,000/month); ULTRA $70 (90,000/month); MEGA $99.
- **Historical depth:** NS.

**Judgement: low–medium.** Same unknowns as 3.5a.

#### 3.5d SofaScore (provider "apidojo")

**URL:** https://rapidapi.com/apidojo/api/sofascore

The listing, `/details` and `/playground` HTML held no API metadata on 23 September 2026. Endpoints, pricing and even whether it is still listed are unknown.

**Judgement: unknown.**

#### 3.5e Tennis Live Data (provider "sportcontentapi")

**URL:** https://rapidapi.com/sportcontentapi/api/tennis-live-data

Same situation as 3.5d: no API metadata in the HTML.

**Judgement: unknown.**

#### 3.5f Matchstat's Tennis API (RapidAPI "Tennis API - ATP WTA ITF", host `tennis-api-atp-wta-itf`; also sold as **Tennis-API.com**)

**URLs**

| Page | URL |
|---|---|
| RapidAPI listing | https://rapidapi.com/jjrm365-kIFr3Nx_odV/api/tennis-api-atp-wta-itf |
| Docs | https://tennisapidoc.matchstat.com/ |
| Live-event and odds docs | https://tennisapidoc.matchstat.com/live-event-and-odds |
| Getting started | https://tennisapidoc.matchstat.com/getting-started |
| Tennis-API.com pages | https://tennis-api.com/tennis-point-by-point-api/, https://tennis-api.com/api-coverage/, https://tennis-api.com/api-pricing/ |
| Tennis-API.com docs (base URL is the RapidAPI host) | https://docs.tennis-api.com/ |

**Endpoints (raw)**
- `GET /tennis/v2/extend/api/event/pbp/{player1_id}/{player2_id}/{tournament_id}/{round_id}`: "Point-by-Point by IDs", "Returns point-by-point data using player, tournament and round IDs."
- The "Point-by-Point by Player Names and Date" endpoint (`…/event/points-by-points/{player1}/{player2}/{date_only}`, WF).
- `GET /tennis/v2/extend/api/event/timeline/{event_id}`: "Returns the chronological timeline for an event."
- Docs (WF): "Path segments come from the live event's matchId field (player1Id-player2Id-tournamentId-roundId), not from the live event id used for odds." This suggests pbp exists only for matches seen by their live feed (INF).

**Example (OBS, raw, docs example: Fritz vs Cerundolo)**
- Per game: `"server": 1, "tiebreak": false, "finalScore": "1-0", "gameNumber": 1, "fifteens_content": "15:0, 30:0, 40:0"`.
- Break points are marked inline, e.g. `"0:15, 0:30, 15:30, 30:30, 30:40 BP, 40:40, A:40"`.
- The timeline example is game-level text: `"Game 1 - Julia Adams - breaks to 30"`.
- The example has no per-point timestamps and no ace or DF flags.

**Marketing (PC, WF):** tennis-api.com lists `"serve_speed_kmh"` and `"updated_at"` among point-by-point outputs. Neither appears in the documented pbp example (red flag).

**Coverage claims (raw):**
- "Detailed ATP, WTA, ITF player profiles, recent and historical match information for all players since 1930".
- "historical odds (going back as far as 2010 for all professional matches)".
- An H2H parameter acknowledges "Challenger, Futures/ITF and qualifying-round matches".

**Coverage by men's tier:** point-level depth NS for every tier.

**Plans**
- RapidAPI (raw): BASIC $0 (50/day); PRO $29 (150,000/month); ULTRA $59 (1,200,000/month); MEGA $99 (3,800,000/month).
- tennis-api.com says PBP and timeline sit in the "Ultra ($59/mo) and Mega ($99/mo)" tiers (WF summary).
- tennis-api.com/api-pricing instead lists "$10/month … 10,000 monthly requests" and "$39/month … 75,000 monthly requests" (WF). The prices are inconsistent across the vendor's pages.

**Terms:** NS in the docs. "A server-side throttle of 100 requests per minute per IP applies to all endpoints." *(WF)*

**Judgement: low.** The pbp endpoint belongs to the live family, the format is a score string with no timestamps, and nothing states how far back pbp exists for ITF or Challenger.

---

### 3.6 Other vendors and channels (included only where a point-level claim exists or was checked)

| Source | URL(s) | What I found | Judgement |
|---|---|---|---|
| **Apify: SofaScore Tennis Scraper** (scrapersdelight) | https://apify.com/scrapersdelight/sofascore-tennis-scraper | See the note below the table. | Low (scraping; not licensed) |
| **Apify: Flashscore Tennis PBP** (humin93) | https://apify.com/humin93/flashscore-tennis-pbp | "A Flashscore scraper for tennis point by point data and tennis odds history"; "server of every game, the exact score path (0:15, 0:30, 30:30, 40:30, …), break/set/match points flagged per point"; "from $5.00 / 1,000 match point-by-points"; historical depth NS (WF) | Low (scraping) |
| **SportDevs** | https://sportdevs.com/tennis, https://docs.sportdevs.com/docs/category/tennis | Both hosts failed to resolve or connect on 23 September 2026. A search snippet (3P) claimed real-time "points-by-points". | Unknown |
| **Sportmonks** | https://www.sportmonks.com/ | "Three sports today: football …, cricket …, and Formula 1" (WF). No tennis. | None |
| **Broadage** | https://www.broadage.com/ | Homepage lists Soccer, Basketball, Football, Volleyball, Ice Hockey, Baseball and Handball. No tennis (WF). | None |
| **Ultimate Tennis** (RapidAPI) | https://rapidapi.com/cantagalloedoardo/api/ultimate-tennis1 | 16 routes; no pbp route. `match_details` gives aggregates such as "Aces, Break points, First Serve %" *(raw)*. | None |
| **live-tennis-api.com** (FORCESCRIPTS LTD, UK; unrelated to livetennisapi.com) | https://live-tennis-api.com/ | "50+ Tournaments" including "Grand Slams, ATP Masters 1000, WTA 1000, Davis Cup"; credits "starting at $0.001"; no pbp claim found (WF) | None |
| **Data Sports Group** | https://datasportsgroup.com/coverage/tennis/ | "Real-time Point-by-Point feeds, Ace/Fault stats" (live); "Historical data per season" as an add-on; "CONTACT SALES", no public price (WF) | Out of scope (not self-serve) |
| **Sportradar** | https://developer.sportradar.com/tennis/reference/overview | "Sport Event Timeline … play-by-play event timeline"; "Competitions will return a maximum of three seasons of data"; no public price (WF) | Out of scope (enterprise) |
| **TheSports** | https://www.thesports.com/pricing | "15Days API Free Trial"; contact form; no tennis specifics (WF) | Out of scope |

**SofaScore Tennis Scraper details** (all quotes WF):
- **Output structure:** `pointByPoint = [{ set, games: [{ game, homeGames, awayGames, serving, scoring, points: [{ homePoint, awayPoint, homePointType, awayPointType, pointDescription }] }] }]`.
- **Point codes:** described as "SofaScore's own point classification codes (which side won the point and how — ace, double fault, break point, and so on)".
- **Recent ITF/Challenger run:** "A second run restricted to Challenger + ITF, finished matches only, returned 30 matches in 98 s: 29 / 30 carry a full statistics sheet and 29 / 30 carry point-by-point" (3P; run date NS).
- **Historical depth:** "As far as SofaScore keeps the season."
- **Price:** "$0.004" per match, plus "$0.004" for enrichment.
- **Disclaimer:** "Not affiliated with, endorsed by or sponsored by SofaScore."

---

## 4. Cross-cutting observations

1. **Upstreams repeat, so more vendors does not mean independent data (INF).**
   - api-tennis.com and allsportsapi.com share example IDs.
   - Three RapidAPI listings resell SofaScore.
   - Live Tennis API's 2023–2025 layer comes from an unnamed "third-party feed".
   - Where coverage matters, measure it directly rather than counting vendors.
2. **Wall-clock time per point is rare.**
   - Only Live Tennis API offers it, and only on rows it watched live (capture from 12 October 2025).
   - None of the other documented pbp schemas (api-tennis, Matchstat, the SofaScore structure as reported) shows a per-point timestamp.
3. **Per-point attributes are thin.**
   - Available: server, score path and point winner, plus break, set and match point flags (api-tennis) or `BP` markers (Matchstat).
   - SofaScore-derived output may carry ace and DF codes (3P).
   - Serve speed, rally length and shot-level data were not documented for ITF or Challenger by any self-serve source.
4. **The 2019–2022 ITF men's window is the gap.**
   - The only self-serve evidence is a single abbreviated 2022 ITF M25 docs example (api-tennis.com / AllSportsAPI).
   - SofaScore-derived depth is undocumented.
   - Live Tennis API explicitly excludes ITF before 2023.
5. **Tournament and match dates.** Live Tennis API's archive date field is the tournament start date, per its own statement. This matches the project rule that tournament start dates are not match timestamps.

## 5. Low-cost checks that would settle the main unknowns

These are not executed. Each one except the first requires the owner to sign up, pay or contact a vendor.

1. **No purchase needed.** In the Live Tennis API June 2026 Zenodo sample the project already holds, measure `pbp_coverage` ("point" vs "game"), the coverage flags and the timestamp presence for ITF men's and Challenger men's matches.
2. **Live Tennis API.** One month of core Basic ($9.99) gives access to `GET /history/coverage`, the per tour × draw completeness roll-up.
   - Then sample `/history/matches` for the reference players' 2023–2026 ITF and Challenger matches (main and qualifying).
   - Ask in writing about Terms §3(c) (storage for model training) and about the upstream "third-party feed".
3. **api-tennis.com.** Use the 14-day trial to call `get_fixtures` for sample dates in 2019, 2020, 2021 and 2022, filtered to "Itf Men Singles" and "Challenger Men Singles".
   - Measure the share of non-empty `pointbypoint`.
   - Check `event_qualification` = True rows.
4. **TennisApi (RapidAPI BASIC, free, 50 requests a day).** Call `/api/tennis/events/{d}/{m}/{y}` for 2019–2022 dates, then `/event/{id}/point-by-point` on ITF M15/M25 and Challenger matches. Count 200 vs 204 responses.
   - Assess the SofaScore licensing question before any real use.

## 6. Blocked or unreachable pages (23 September 2026)

- **HTTP 403:**
  - https://betsapi.com/api-doc/index.html
  - https://betsapi.com/tennis/l/17951/ITF-M15-Eupen
  - https://betsapi.com/cip/tennis
  - https://matchstat.com/predictions-tips/tennis-api-for-atp-wta-itf-the-data-engine-behind-matchstat/
  - https://sportsapi.com/api-directory/api-tennis/
  - https://www.toolify.ai/ai-model/sofascore
- **HTTP 404:**
  - https://api-tennis.com/pricing
  - https://api-tennis.com/coverage
  - https://allsportsapi.com/pricing
  - https://tennisapidoc.matchstat.com/ms-live (the working equivalent is `/live-event-and-odds`)
  - https://betsapi.com/docs/faq.html
- **DNS or connection failure:** sportdevs.com and docs.sportdevs.com.
- **Client-rendered or empty for the fetch tool:** all RapidAPI listings. Raw HTML was used instead. The apidojo SofaScore and Tennis Live Data listings contained no API metadata even in raw HTML.

## 7. Scratch files created by this research

All in the session scratchpad; none deleted:
- **Downloaded pages:** `rapid_tennisapi1.html`, `fluis.lacasse_api_tennisapi1.html`, `fluis.lacasse_api_allsportsapi2.html`, `jjrm365-kIFr3Nx_odV_api_tennis-api-atp-wta-itf.html`, `apidojo_api_sofascore*.html`, `sportcontentapi_api_tennis-live-data*.html`, `cantagalloedoardo_api_ultimate-tennis1.html`, `tipsters_sofasport.html`, `allsports_tennis_doc.html`, `apitennis_doc.html`, `lta_hist.html`, `lta_acad.html`, `lta_terms.html`
- **Derived text:** `rt1.txt`, `ms.txt`
- **Parsers:** `rapid_extract.py`, `routes.py`, `peek.py`, `ms_pbp.py`, `docpbp.py`, `strip.py`
