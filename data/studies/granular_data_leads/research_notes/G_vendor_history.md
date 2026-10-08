# Lane G: which vendors sell historical Grand Slam point-by-point data (24 Sep 2026)

This is a follow-up lane for [access routes](../../../../docs/research/granular-data-leads/access-routes.md).

**Question.** Which commercial vendors sell historical point-by-point data for Wimbledon, the US Open and the Australian Open (2019–2026), and how close does each come to what the Slams' own sites show?

**Scope.** Two routes were out of scope: asking a rights holder for permission, and scraping a site whose terms forbid it. A paid reseller of such a scrape is flagged as one.

**Method.** Public docs, terms and posted samples only. No sign-up, purchase or contact.

**Provenance.** This is the agent's report as returned, lightly edited. Raw captures stayed in the session scratchpad.

**Labels:** [observed], [provider claim], [third-party report], [search excerpt], [inference], [not stated]; WebFetch-summarised quotes are marked (WF).

## Bottom line

No vendor was found that sells licence-clean Grand Slam point-by-point history for 2019–2026 with outcome tags.

The data closest to the Slams' own sites belongs to Sportradar, which bought IMG ARENA in November 2025. Its docs show that data only as live per-event streams, and Sportradar's API licence blocks prediction-market use.

Everything purchasable self-serve is mostly score-only for the Slams. Several products are built partly or wholly on scrapes or on non-commercial data.

## Vendor table

| Vendor / product | Slams and years | History purchasable? | Per-point fields vs target | Who may buy / price | Licence (archive / ML / betting and prediction markets) | Upstream | Verdict |
|---|---|---|---|---|---|---|---|
| **Sportradar Tennis API v3** | All 4 Slams, "100% point-by-point from round 1"; qualifying "often lower". Only the current season and two adjacent editions are kept; with the 2027 stub listed, that is probably 2025–26 [observed; years inferred] | No. The docs tell you to archive before a season drops out of the window [observed]. The contract defines a "Complete History" tier, but tennis shows no deeper seasons [inference] | Clock time, server, first-serve fault, result (ace / double fault / server won / receiver won). No per-point winner or error type, stroke, rally length or speed. Winners and errors by forehand/backhand are match totals only [observed in the OpenAPI] | Sales only. The 30-day self-serve trial is for evaluation only. No price [observed] | Display-only licence. All data, "including all historical data", is destroyed on termination. Prediction markets and betting need written consent. An AI clause also applies [observed] | "official data for ATP tournaments only", so the Slams are collected independently [observed] | **Paid but licence blocks our use** |
| **Sportradar DDE (ex-IMG ARENA)**: umpire event stream plus player and ball tracking | Tournament organisers listed: ATP, AELTC, USTA, FFT; no Tennis Australia. The RG 2024 sample includes qualifying and doubles. Tracking availability: "please contact" [observed] | No archive documented. A stream can be replayed from a position number, and a 2022 sample event is still served [observed]. History as a product is not stated | **Umpire stream:** timestamp, point winner, Ace / DoubleFault / Standard, Fault / FootFault events (so serve number can be derived). **Tracking rally summary:** start/end time, serve number, shot count, final stroke plus result plus Forced/Unforced, speeds, serve side. That meets or exceeds the Slam sites [observed] | Licensed per event, B2B. No price | Terms not public | Umpire-entered official data plus tracking | **Live/rolling only** |
| **Sportradar Live Data** (bookmaker scout feed) | Not verifiable: the docs return 401 | Not stated | Not verifiable | Sportsbooks | Not public | Scouts | **Live/rolling only** [inference] |
| **Stats Perform (Opta) MA21** plus its prediction-market archive | Tennis archive "from 2021" [provider claim]. Slam point coverage not stated. WTA umpire data is official | Sold via sales as a "training and calibration layer for prediction market pricing" [provider claim] | Point index, first serve yes/no, server, shot type and stroke as undocumented integer codes, zone, millisecond timestamp [observed] | Organisations through sales. No price | Standard licence (Dec 2025): no ML training; "shall not bulk download or otherwise build archival files"; no betting [observed]. Prediction-market deal terms not public | Own collection; WTA official | **Paid but licence blocks our use** (standard terms) |
| **Enetpulse** | Point-by-point for ATP/WTA "including Grand Slams". History "since 2020" [observed] | Yes, as an "exclusive product" via Sales [observed] | Running score per point only. Update timestamps are batched: four points share one second in their example. Winners and unforced errors are match-level, "Available only for Grand Slams" [observed] | B2B. Free test weeks. No price | Data licence not public; only website terms found | Not stated | **Viable paid, score-only; licence unverified** |
| **Live Tennis API** (JSB Holdings) | 2013–22 reconstructed, score-only; Slam main draws 98.0% (ATP) and 97.4% (WTA), qualifying 16–18%. Its own tape from 2023. Timestamped rows are recent only [observed] | Yes, self-serve. History $29 / $99 / $299 per month; $49 for one month; $399 for one year [observed] | Slams: outcome is null. Serve number comes from "a different source", only since 12 Sep 2026. Timestamps are when the vendor accepted the state, not the court clock [observed] | Individuals, self-serve | Terms bar "Scrape, cache, or store the data beyond what is reasonably necessary". No ML or betting clause [observed] | Reads the tours' "own per-point console". Resells Match Charting Project data, whose licence says "Non-commercial use only" [observed] | **Partly resells a scrape or non-commercial data**; Slams are score-only |
| **api-tennis.com** | All tours; a docs example queries a 2019 date | Historical queries by date range; depth not stated | Point number, score, break/set/match-point flags; server and game winner per game. No time, ace/double fault or outcome [observed] | $40–$120 per month; 14-day trial | Terms say nothing on storage, ML or betting | Not stated | **Viable paid, score-only**; upstream unknown |
| **Goalserve** | Claims Slams and "detailed point by point tennis match history" | Depth not stated | Public samples show no point structure | $150 per month; $900 for 6 months; $1,200–1,500 per year | Terms have no data-use clauses | Not stated | Unverified |
| **Matchstat / tennis-api.com** (also sold via SportsAPI365 and RapidAPI) | Slams included; point endpoints by IDs or by names plus date; "Live events are singles-only" | History depth not stated | The marketing example shows Ace and `serve_speed_kmh` "where available"; response schema not public | $29 / $59 / $99 per month | Terms not found | Not stated | Unverified |
| **STATSCORE** (owned by LSports since Nov 2022) / **LSports** | Both claim Slams down to qualifying | Not stated | "aces… double faults… service faults"; point schema not public | From "€1,000"; bookmakers | Not public | Scouts; LSports also claims "web scouting" | Unverified B2B; "web scouting" may mean scraping |
| **Podium** | Slam singles main draw has point-by-point; Slam doubles and qualifying have none [observed] | Not stated | Score plus server, updated every "2 to 15 seconds" | Sportsbooks | Not public | Not stated | **Live/rolling only** |
| **Data Sports Group** | "Point-by-Point feeds, Ace/Fault stats"; add-on "Historical data per season" | Unclear | Not public | Free trial | Not public | Not stated | Unverified. The 24 Sep lane C found no point method in its 24 tennis methods |
| **SportsAPI Pro** | Has a tennis point-by-point endpoint | Terms allow keeping data, ML and "your own wagering analysis" [observed] | Schema looks like SofaScore's (same status codes, `startTimestamp`) | From $45 per month | No redistribution | Probably SofaScore [inference] | **Likely resells a scrape** |
| **Apify "SofaScore Tennis Scraper"**; **BetsAPI** (Bet365, BWin and Betfair APIs at $100–150 per month) | — | Apify back-fills history | Apify returns SofaScore point types (WF) | $4–8 per 1,000 matches; BetsAPI from $10 per month | — | SofaScore; bookmaker sites | **Resells a scrape** |

**No Slam point data found:**
- SportsDataIO: its tennis doc URLs return 404.
- Genius Sports.
- BigDataBall: match-level Excel files.
- fault.bet: match-level analytics from 2022.
- live-tennis-api.com: scores only.
- Snowflake: only a Stats Perform "Tennis Schedule and Results" sample [search excerpt].
- AWS Data Exchange: nothing found.
- Datarade: an odds-only listing [search excerpt].

Kambi and Oddin were not examined.

## Key quotes (accessed 24 Sep 2026)

**Sportradar**
- History: "The season catalog carries a rolling window per competition: at least the current season and the two adjacent editions." (developer.sportradar.com/tennis/docs/tennis-ig-historical-data.md)
- Official status: "In the case of Tennis, we provide official data for ATP tournaments only." (developer.sportradar.com/tennis/reference/faq.md)
- Contract (updated 5 Aug 2026), from developer.sportradar.com/sportradar-updates/page/terms-and-conditions.md:
  - "for the sole purposes of displaying Data and Content…"
  - "Customer shall not use… any related data… for any prediction market… without Company's prior written consent"
  - on termination, destruction of "all historical data"
  - it also grants a licence that is "perpetual (solely for archiving purposes)", which conflicts with the destruction clause.
- DDE umpire stream: it "generally corresponds to data being entered by the umpire on the court". (docs.sportradar.com/tennis/stream-endpoints-websockets/events-id-stream-tennis.md)

**Stats Perform**
- Licence: "shall not… utilize the Licensed Materials to create, develop, test, train… machine learning… Licensee shall not bulk download or otherwise build archival files". (statsperform.com/legal/mla-december-2025/)
- History: "Tennis: from 2021". (developers.statsperform.com/historical-sports-data-for-pricing-models)

**Enetpulse** (eclient.enetpulse.com/documentation/article_view/124/2)
- "Point by point result updates (we keep the pbp history since 2020 year)"
- "Point by Point History (It's an exclusive product, so please contact Sales…)"

**Live Tennis API and the Match Charting Project**
- Live Tennis API: "Grand Slams and Davis Cup are not on that console, so outcome reads null there". (docs.livetennisapi.com/reference.html)
- The Match Charting Project, which Live Tennis API resells: "Non-commercial use only." (github.com/JeffSackmann/tennis_MatchChartingProject)

## Not determined

- **Sportradar DDE:** the licence terms; which Slams and years its tracking feeds cover; whether a historical DDE or tracking product exists.
- **Sportradar "Complete History" tier:** whether it reaches tennis seasons older than the rolling window.
- **Stats Perform:** what its prediction-market terms allow; whether it has Slam point coverage; what the MA21 shot and stroke codes mean. A search result shows a Stats Perform release on exclusive distribution of Tennis Australia data (2023–25); [lane F](F_slam_licensees.md) covers that deal.
- **Other vendors' licences:** the data licences and upstream sources of Enetpulse, Goalserve, api-tennis.com, Matchstat, STATSCORE, LSports and Data Sports Group, and their depth for Slam doubles and qualifying.
- **Live Tennis API:** where its 2013–22 "public record" reconstruction comes from.
- **Betradar Live Data:** its tennis fields. The docs need a login (401), so this was not pursued.
