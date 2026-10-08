# Lane H: WTA official point data, its terms and paid routes (24 Sep 2026)

This is a follow-up lane for [access routes](../../../../docs/research/granular-data-leads/access-routes.md).

**Question.** Can the WTA API's point data (row 6 of the [granular data leads](../../../../docs/research/granular-data-leads/README.md)) be obtained through either route?
- (a) A public source whose terms permit automated collection and reuse.
- (b) A paid service.

Asking the WTA did not count. Neither did "public, but the terms forbid scraping".

**What was fetched.** Read-only. The agent made exactly 3 GET requests to the API, all for match 1045/2026/LS025: `point-by-point`, `win-probability-momentum` and `advanced-stats`. These were to read headers and metadata, not to collect data. It also fetched the API host's robots.txt. Kaggle's API returned a reCAPTCHA, so the agent stopped there.

This is the agent's report as returned, lightly edited. Scratch files stayed in the session scratchpad.

**Labels:** [observed], [provider claim], [third-party report], [search excerpt], [inference], [not stated]; (WF) marks a quote taken through WebFetch.

## Bottom line

- **(a): no.** The WTA's terms forbid automated collection and any reuse beyond personal use. No API terms say otherwise.
- **(b): no clean route.** The only paid route to the same data runs through Stats Perform, and its standard licence bans model training, archive building and betting. No paid route is clearly usable.

## 1. Terms

**Website terms.** https://www.wtatennis.com/terms-and-conditions, "Last Updated: April 06, 2020" [observed]. They cover "websites, pages, social media accounts, and applications owned, operated, or controlled by WTA Tour, Inc." Under "You must not:":
- "\"harvest\" (or collect) information from the WTA Sites using an automated software tool or manually on a mass basis (unless we have given you separate written permission to do so)."
- "use automated means to access the WTA Sites … This prohibition does not apply to search engines accessing the WTA Sites solely for web indexing purposes."
- "circumvent or reverse engineer the WTA Sites or their systems."

On content, the terms say: "You may use the WTA Sites … for your own personal use. You may not modify, copy, reproduce, republish, … sell, create derivative works of, exploit, or distribute … any material from the WTA Sites unless explicitly authorized". Single pages may be kept "for your personal, non-commercial use". The terms say nothing on betting, gambling, text or data mining, robots, or AI and model training [observed: zero matches].

**robots.txt.**
- www.wtatennis.com has `User-agent: *` / `Disallow:` / `Sitemap: https://www.wtatennis.com/sitemap/index.xml` [observed].
- api.wtatennis.com returns HTTP 404 [observed].
- robots.txt is not a licence, and the terms exempt only search indexing [inference].

**No public API terms.** developers.wtatennis.com ("WTA Data API Documentation", last modified 18 Sep 2026) sits behind a Microsoft login [observed].
- It documents a separate "V2" API (`wta-webapi-prod-apimanagement.azure-api.net/api/v2`) with `point-by-point`, `win-probability-momentum` and `advanced-stats` [provider claim].
- It also documents an `/events` feed of "serves, aces, double faults, winners, errors … each with a timestamp … shot details" [provider claim].
- Access uses "OAuth 2.0 / OIDC (Bearer tokens) or API keys in headers", with "Role or permission checks at the endpoint level". It says "The V2 APIs are currently in Beta".
- No sign-up, price or licence was found. Access would therefore be an ask.

**API responses** carry no licence, copyright or "powered by" information in their headers or JSON [observed].

**The app.** The site's app link goes to "ATP WTA Live", made by "ATP Tour, Inc." [observed]. No app-specific terms were found. The ATP website terms (WF) say:
- "Systematic retrieval of data … including … scores, statistics … is prohibited absent prior express written permission".
- "commercial, gambling or wagering purposes" also require permission.

## 2. Who powers the data and who holds the rights

| Data type | Supplier | Rights holder | Evidence |
|---|---|---|---|
| Point-by-point, with a time for each point | Chair-umpire scoring; Stats Perform collects and distributes it exclusively [provider claim] | WTA Tour, Inc.; its commercial arm, WTA Ventures, was set up in March 2023. Stats Perform is the exclusive official data and betting partner from 2021 to "the end of the decade" | Stats Perform, 24 Nov 2020: the WTA "named Stats Perform its Official WTA Data Supplier … exclusive umpire-derived data feed". WTA, 08 Dec 2023: "extended its exclusive agreement … to collect and distribute official WTA data and live streams to licensed sportsbooks until the end of the decade". Trade press gives the end as "2030" [search excerpt]. Stats Perform rights page, 15 Jun 2026: "exclusive official WTA Umpire Chair data" |
| Advanced stats | Probably Stats Perform's shot-by-shot feed, collected by Opta analysts [inference] | Same | 2020: "ultrafast data feed collected by Stats Perform's Opta analysts … down to rally and shot level". 2023: "a more detailed in-venue data feed, alongside the umpire data feed". No credit on the page or in the API [observed] |
| Win probability and momentum | Probably a Stats Perform/Opta model [inference, strong] | Same | WTA, 2023: "New AI enriched Opta metrics like clutch points and win probabilities". Opta Analyst, 4 Mar 2022: "two new Stats Perform metrics – leverage and momentum … in WTA tennis matches", from a model built on "1.5 million points played on the WTA tour between 2012 and 2020". The MA21 feed has `momentum` and `leverage` fields |
| Betting-feed resale | Sportradar, which licenses Stats Perform's WTA data for in-play odds outside the USA | Stats Perform | Sport Industry Group, 17 Mar 2021 [third-party report]. The same report says IMG held the rights before 2021 and had sub-licensed them to Genius Sports |

**Candidates not supported by the evidence:**
- **SAP.** The site has "SAP Logo" and "Insights from" strings, but nothing was found that renders them, and SAP is absent from the partner footer.
- **Hawk-Eye.** There are no speed or placement fields.
- **TDI.** It covers the ATP only.
- **IMG ARENA.** Sportradar's 2025 acquisition release does not mention the WTA.
- **Prediction markets.** The WTA has no official prediction-market partner [search excerpt].
- The site runs on the Pulselive platform [observed].

## 3. Paid routes

| Vendor / product | WTA tiers and years | Can past seasons be bought? | Fields compared with the WTA API | Who may buy / price | Licence limits | Verdict |
|---|---|---|---|---|---|---|
| **Stats Perform**: umpire feed, shot-by-shot feed, MA21 predictions | "50+ tournaments per year", qualifiers included. MA21 level "3 = Point by Point scores available along with match events (WTA)" [provider claim]. WTA 125 coverage [not stated] | "Tennis: from 2021" (page dated 28 Jul 2026). MA21 can be queried "by point number or point ranges" [provider claim] | All three types. Per-point millisecond timestamp; `shotType`, `stroke`, `isFirstServe`, `isVolley`, `zone` for each point; win probabilities (match, set, game, next point), momentum, leverage, clutch [provider claim] | Licensed sportsbooks, media and prediction-market operators; sales only; price [not stated] | Master licence (Dec 2025): no ML training, no archive, no betting, and material returned or destroyed at the end (clauses in **Licence details** below). A negotiated order form overrides this ("the Work Order shall prevail"). Stats Perform markets its history as "the training and calibration layer for prediction market pricing" | **Paid, but the licence blocks our use** under standard terms. A custom deal looks aimed at operators, not individual traders [inference] |
| **Sportradar Tennis API v3** | Tier 3, "WTA Finals, WTA 1000, WTA 500 …": "Point-by-point from round 1". Tier 6, "WTA International, WTA 250, WTA 125k": "Point-by-point from the semifinals". WTA tiers are not marked "Official data" [provider claim] | Rolling window: "at least the current season and the two adjacent editions" | Server, winner, score, result, first-serve fault, UTC time (from lane C; not re-fetched). Winners and errors by wing only at Grand Slams | Sales; price [not stated] | Terms dated 5 Aug 2026: no prediction-market or gambling use, and all historical data destroyed at the end (clauses in **Licence details** below) | **Paid, but the licence blocks our use**; rolling window only |
| Sportradar Live Data (carries Stats Perform's WTA data) | As sub-licensed | No | Live | Licensed bookmakers | — | **Live/rolling only** |
| **Live Tennis API** (JSB Holdings LLC) | "WTA 1000/500/250/125: ace and double fault where the tour's console reports the match". Tags from 12 Sep 2026 [provider claim] | Timestamped rows from 12 Oct 2025; rebuilt 2023–25 rows have no timestamps | Score, server, capture time, ace or double fault, first or second serve. Its win probability comes from its own model. No WTA advanced stats | Self-serve, open to individuals: $9.99, $29.99 or $99.99 a month | Its terms limit storage and bulk datasets (clauses in **Licence details** below); ML and betting [not stated]. Its WTA source is "the tour's own per-point console" [provider claim], probably the WTA's own feed [inference] | **Paid, but the licence blocks our use** (storage clause; source likely unlicensed) |
| Enetpulse | "most ATP and WTA tour-level matches" | "we keep the pbp history since 2020 year", sold as an "exclusive product" through sales | Score after each point; `ut` stamps are batch update times, not point times. No win probability | B2B; price [not stated] | Data licence [not stated]; the public terms (22 Sep 2022) cover the website only | Unverified: licence not public, and fields are weaker than the WTA API's |
| STATSCORE | Claims the "WTA Tour", from its own scouts | [not stated] | Serve incidents, aces, double faults, foot faults; no winners or errors | B2B; the incident timeline is "a separate add-on" | [not stated] | **Live/rolling only** as documented |
| LSports | "exclusive ITF, ATP, and WTA premium packages"; "web scouting, TV/in-venue scouts" | [not stated] | Live counters | Bookmakers | [not stated] | **Live/rolling only** |
| Genius Sports | No WTA product found | — | — | — | — | **Not sold** |

**Licence details.**
- **Stats Perform**, master licence (Dec 2025):
  - §4(c): the licensee may not "utilize the Licensed Materials to create, develop, test, train … machine learning … models", and "shall not bulk download or otherwise build archival files".
  - §4(r): no "Betting Activities".
  - §10(b)(iii): licensed materials must be returned or destroyed.
- **Sportradar**, terms dated 5 Aug 2026:
  - §2.1: no use "for any prediction market, trading platform, financial product … without Company's prior written consent".
  - §2.10: "No Gambling".
  - §7.4: destroy "all historical data … together with any derivatives".
  - §2.2 grants a "perpetual (solely for archiving purposes)" licence, which conflicts with §7.4.
- **Live Tennis API**:
  - §3(c): users may not "Scrape, cache, or store the data beyond what is reasonably necessary to operate your application".
  - §3(a): no bulk datasets.

## 4. Open datasets

- **Live Tennis API sample on Zenodo** (record 22058943, v1.0.1, 22 Aug 2026, CC BY-NC 4.0) [observed].
  - 951,064 "observed" point states from June 2026, including WTA matches. Each carries the score, server and "live capture time, UTC".
  - No winners, errors or win probability.
  - The full dataset is for "non-commercial research and teaching only; no redistribution".
  - Sources: "our own collection" and a "third-party data feed", neither named [provider claim]. Whether it came from wtatennis.com [not stated].
  - A non-commercial licence probably excludes betting [inference].
  - The project already holds this sample.
- **Match Charting Project, women's points** (CC BY-NC-SA, "Non-commercial use only") [observed]. Crowdsourced from video; winners and errors by wing and rally length, but no timestamps and no official status. Held.
- **Sackmann repositories** `tennis_pointbypoint`, `tennis_wta` and `tennis_slam_pointbypoint` all return 404 today [observed]; see [lane I](I_open_datasets.md).
- **No licensed dataset built from wtatennis.com was found.**
  - GitHub code search shows 13 files that call its `point-by-point` endpoint, for example robertyang87/tennislive, and thekasser/tennis-wta-atp, which calls the endpoint "Undocumented; assumed CC-equivalent". These are code, not licensed data [observed].
  - Hugging Face has only unlicensed re-uploads.

## 5. Not determined

- **Who powers the site's figures.** Nothing on the page or in the API credits the advanced stats or the win probability, so it is unconfirmed that they come from Stats Perform.
- **The V2 API.** Who can get access on developers.wtatennis.com, and under what licence.
- **Stats Perform.** Its price; the depth of its WTA 125 and qualifying coverage; what "from 2021" actually includes; whether individuals can buy; whether a custom deal would allow model training or prediction-market use.
- **Sportradar.** Whether its WTA data is official (through Stats Perform) or its own scouting, and whether its "Complete History" tier is sold for tennis.
- **Enetpulse and STATSCORE.** Enetpulse's licence, and STATSCORE's history depth.
- **Live Tennis API.** The exact WTA source behind it.
- **Other partners.** SAP's current role, and whether Hawk-Eye is involved at all.
- **Stats Perform's term.** Whether "end of the decade" means 2029 or 2030.
