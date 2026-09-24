# R4: Public websites and public datasets for historical point-by-point and shot-level men's tennis data (ITF and Challenger focus)

- **Accessed:** 23 September 2026, for every URL unless a note says otherwise.
- **Status:** research notes only. Nothing here is a decision. Any "next step" below is an option for the owner.
- **Scope:** Flashscore, Livesport and Tennis24; SofaScore; OnCourt; ten other score and stats sites; public datasets from 2018 or later.
- **Excluded (already in use):** Sackmann's match files and Grand Slam point archive, the Match Charting Project (MCP) export, Tennis My Life, tennis-data.co.uk, Open Tennis Data, the Live Tennis API Zenodo sample, and Polymarket. Mirrors of these are flagged but not evaluated.

## How to read the evidence labels

| Label | Meaning |
|---|---|
| **provider claim** | Statement by the operator or data owner. |
| **observed** | I saw the actual data, or file metadata, on a public page. |
| **third-party report** | Scraper documentation, dataset cards, papers or forums. |
| **search-engine excerpt** | Text shown by the search tool for a page I could not open. It is weaker than a third-party report and is not verbatim-verified. |
| **inference** | My own reasoning. It is always marked. |
| **not stated** | The source says nothing on the point. |

**Caveat on quotes.** Pages were read through a fetch tool that returns model-processed text. I asked for verbatim wording every time, and the quotes below are what the tool returned. They are very likely accurate but are not byte-checked. Re-read any terms-of-use clause directly before relying on it for a decision.

---

## 0. Bottom line (point-level data for 2019–2026 ITF and Challenger men's matches)

1. **TennisLive.net is the only public website where I observed historical point sequences for ITF M15/M25 main draws and for Challenger main-draw and qualifying matches.**
   - Coverage runs from 2018 (ITF) and 2016 (Challenger) to 2026, on ordinary public match pages.
   - Its terms, updated 13 Sep 2026, say: "Systematic scraping, bulk extraction, automated redistribution and commercial reuse require permission or another valid legal basis." Using it in bulk needs permission.
   - Gaps observed:
     - ITF qualifying had no point-by-point (0 of 2 checked, Dec 2025).
     - ITF main draw had no point-by-point in January 2025 (0 of 2 checked).
     - Several opening games look incomplete.
     - No per-point timestamps were seen.
2. **Flashscore and Tennis24 (both Livesport) have a "Point by point" tab, but I could not verify how far back it goes.**
   - The provider claims it for "all ATP and WTA matches".
   - Third-party scrapers say Challenger and ITF matches have it now, but "Lower-tier ITF and some doubles matches may have no PBP feed".
   - Checking historical depth would mean extracting from Flashscore's data feeds, which the terms forbid.
   - Livesport's B2B route is **Enetpulse**, which Wikipedia says Livesport owns. Enetpulse sells "Point by Point History" as "an exclusive product" and says it keeps "the pbp history since 2020 year". Its coverage claim names Grand Slams, ATP, WTA and Challenger. ITF and price are **not stated**.
3. **SofaScore offers no data API and does not name its data providers.**
   - Its FAQ says it is "unable to share the data sources in the form of API endpoints".
   - Its terms, as excerpted by a search engine, forbid automated access and data mining.
   - Third-party reports say finished Challenger and ITF matches currently carry point-by-point. Historical depth is "undetermined".
4. **OnCourt advertises "Point-by-point replay of most matches", but nothing public says which tiers or years, or whether the points are in the Access database or the MySQL service.**
   - It is cheap (EUR 48.95 per year).
   - Only a purchase could settle this, which is the owner's decision.
5. **Public datasets:** apart from the Live Tennis API corpus (in use) and its mirrors, no public dataset has 2019–2026 ITF or Challenger point data.
   - Sackmann's 2011–2017 non-Grand Slam point-by-point data survives only in mirrors. It covers Futures, Challengers and qualifying, and the original repo now returns 404.
   - Everything else is one of:
     - Grand Slam or tour-level only: the 2024 MCM momentum data (Wimbledon 2023), Wimbledon 2024, F3Set and OSL.
     - Derived from MCP.
     - Amateur.
     - Undocumented.
6. **2025 supply-chain change (context).** From 2025 the ITF's data partner changed from Sportradar to Infront. Forum users reported that third-party apps lost ITF point-by-point after an ITF live-score change around the start of 2025. That matches the January 2025 gap I saw on TennisLive.

---

## 1. Method, access log and limits

- **Tools.**
  - Web search was used until the session's web-search quota (200 calls) ran out partway through.
  - After that I used direct page reads and public metadata APIs:
    - Kaggle dataset-list and dataset-view API
    - Hugging Face datasets API and datasets-server
    - GitHub repository-search API
    - Zenodo records API
    - Harvard Dataverse search API
    - Mendeley Data search API
    - arXiv API
- **What I did not do.**
  - I did not sign up, log in, submit forms, contact anyone or buy anything.
  - I did not call any Flashscore or SofaScore internal feed or API.
  - I did not download any dataset file larger than a few kilobytes. The one small file read was the 3 kB MCM data dictionary.
- **TennisLive.net load (disclosure).** About 65 single page requests to public pages, made one to three at a time across the session to spot-check availability. Nothing was collected in bulk and nothing was kept beyond the quoted samples.
- **Blocked or unavailable pages.** I did not try to get around any of these.

| Page | What happened |
|---|---|
| menstennisforums.com and tennisforum.com threads | Redirected to TollBit, a bot paywall. Recorded as blocked; only search-engine excerpts used. |
| matchstat.com (site and blog pages) | HTTP 403 |
| aiscore.com (homepage and tennis page) | HTTP 403 |
| Scores24 match page and homepage | HTTP 403 |
| tenipo.com | HTTP 403 |
| web.archive.org | Could not be fetched by the tool |
| SofaScore, LiveScore and 365Scores terms pages | Text rendered by JavaScript, not retrievable |
| 365Scores news category page | HTTP 500 |
| Figshare search | The GET search ignored the query, so Figshare was effectively not searched |

---

## 2. Flashscore / Livesport / Tennis24 (Livesport s.r.o., Prague)

**URLs.**
- Sites: https://www.flashscore.com/tennis/ · https://www.livesport.com/en/tennis/ · https://www.tennis24.com/
- Terms: https://www.flashscore.com/terms-of-use/ · https://www.tennis24.com/terms-of-use/ · https://www.livesport.com/terms-of-use/
- FAQ: https://www.flashscore.com/faq/data/
- robots.txt: https://www.flashscore.com/robots.txt
- B2B (Enetpulse): https://enetpulse.com/tennis-data/ · https://enetpulse.com/sports-coverage/ · https://eclient.enetpulse.com/docs/xml-data/what-enetpulse-provides-for-tennis-events
- Ownership: https://en.wikipedia.org/wiki/Livesport

**Data unit.** A point sequence within each game: who served the game, the running game score, and flags for lost serve, break points, set points and match points.
- Point attributes (ace, double fault, winner): **not stated**.
- Shot-level data: none.

**Coverage by men's tier (public pages)**

| Tier | Point-level? | Earliest year | Basis |
|---|---|---|---|
| ITF M15/M25 main draw | yes, currently, but some matches lack it | unknown | third-party report (Apify scraper docs) |
| ITF qualifying | unknown | unknown | — |
| Challenger main draw | yes, currently | unknown | third-party report |
| Challenger qualifying | unknown | unknown | — |
| ATP main draw | yes | unknown | provider claim ("all ATP and WTA matches") |
| ATP qualifying | unknown; the provider does not say whether "all ATP matches" includes qualifying | unknown | — |

**Historical access.**
- Public match pages exist, but they are built by JavaScript from internal feeds.
- There is no download and no public API.
- Any bulk retrieval would be the kind of extraction the terms forbid.
- Third-party scrapers describe a date feed that reaches 7 days back. That limits browsing by date; it does not say whether old match pages keep their point-by-point, which remains **unverified**.
- **Timestamps.** Per-point timestamps are not stated. One scraper says it does not provide timestamp data for individual points. Match start times are shown.
- **Price.** Free to view. The B2B price is not stated.

**Terms (provider, "Effective Date: April 1, 2023"; the same text is on Tennis24 and Livesport).**
- 2.2: "You may not use the Site for any commercial purpose." Use is "for your personal use only".
- 2.8: "the use of Copyright Works in the form of reproduction (copying) for direct or indirect economic gain...is not permitted without our explicit consent"
- 2.9: "no extraction (copying) or utilization (making available to the public) of Database Content or of a qualitatively or quantitatively substantial part thereof is permitted without our explicit consent"
- 2.10: "You may not burden our server on which the Site is hosted with automated requests, nor may you assist any third party in such activity." and "you are not permitted to use the content of the website by embedding, aggregating, scraping or recreating it without our express consent"
- AI or machine-learning training is **not mentioned** in section 2 (observed).
- robots.txt (observed) blocks named AI and bot crawlers, including CCBot, Bytespider, cohere-ai, Meta-ExternalAgent, AI2Bot, Diffbot and DuckAssistBot. For all user agents it disallows the date pages `*/day-7/$` through `*/day+7/$`.

**Evidence**

| Label | URL | Quote |
|---|---|---|
| provider claim | https://www.livesport.com/en/tennis/ | "Follow ATP and WTA matches point by point! You will find the 'Point by point' tab with highlighted lost serves, break points, set- and match points in match details of all ATP and WTA matches." |
| provider claim | https://www.livesport.com/en/tennis/ | "scores service from more than 5000 tennis competitions from around the world - ATP tournaments, WTA tour, challengers, ITF tournaments and also team competitions" |
| provider claim | https://www.flashscore.com/tennis/ | "...odds comparison, H2H, news, video highlights or point by point match history." |
| provider claim | https://www.flashscore.com/faq/data/ | "For football, we use Opta as the primary data provider. For the 40+ other sports, it's a variety of providers and sources." |
| provider claim | https://www.flashscore.com/faq/data/ | "some competitions or historical data may be missing due to challenges in sourcing reliable information for certain leagues or events." |
| third-party report | https://apify.com/humin93/flashscore-tennis-pbp | "Lower-tier ITF and some doubles matches may have no PBP feed" |
| third-party report | https://apify.com/sourabhbgp/flashscore-tennis-scraper | "Flashscore only serves a rolling 9 day window: 7 days back through 1 day ahead." |
| third-party report | https://apify.com/sourabhbgp/flashscore-tennis-scraper | "every point of a match in the order it was played, grouped into sets and games" |
| third-party report | https://apify.com/clearfetch/flashscore-tennis-scraper and https://github.com/clearfetch/flashscore-tennis-scraper | Covers "ATP, WTA, ITF and Challenger tennis matches". "Day offsets from today, from -7 to 7" (from the GitHub README). |
| search-engine excerpt | menstennisforums thread (TollBit-blocked) | Around the ITF live-score change, "3rd party livescoring apps like flashscore or sofascore and even betting sites are unable to provide point by point updates on ITF matches". Paraphrase-level; page not opened. |

None of these scraper pages say Livesport consented (**not stated**). **Inference:** using them would breach the project's no-scraping-against-terms rule.

**Livesport B2B (Enetpulse)**

| Label | URL | Quote |
|---|---|---|
| third-party report | https://en.wikipedia.org/wiki/Livesport | "In January 2015, Livesport acquired a share in the Danish B2B sports data provider Enetpulse." "After a few months, Livesport became the sole owner." |
| provider claim | https://eclient.enetpulse.com/docs/xml-data/what-enetpulse-provides-for-tennis-events | "Point by point result updates (we keep the pbp history since 2020 year)" |
| provider claim | same | "Point by Point History (It's an exclusive product, so please contact Sales for more information)" |
| provider claim | https://enetpulse.com/sports-coverage/ | "Every match, set, game, and point from Grand Slams, ATP, WTA, and Challenger tournaments." |
| provider claim | https://enetpulse.com/tennis-data/ | "Live, point-by-point scoring as play happens, on most ATP and WTA tour-level matches"; "offer competitive pricing models to our clients" |

Enetpulse's own "about" page does **not** mention Livesport ownership (observed), so 2026 ownership is **unverified**.

**Unknowns.**
- Whether old ITF and Challenger match pages still show point-by-point, and from what year.
- Whether qualifying matches are covered at any tier.
- Whether Enetpulse's point history covers ITF M15/M25 and qualifying.
- Whether Flashscore and Enetpulse share one point feed (**not stated**).
- Enetpulse's price, and its storage and machine-learning terms.

**Judgement.**
- Flashscore public pages: **Low.** Point-by-point exists, but the terms bar extraction and the historical depth for ITF and Challenger is unverified.
- Enetpulse licence: **Medium, low confidence.** It is a lawful paid route, and point history is claimed from 2020. Challenger appears in the general coverage claim, but the tiers in the history product, ITF coverage and price are not stated.

---

## 3. SofaScore (Sofascore, Zagreb)

**URLs.**
- Sites: https://www.sofascore.com/tennis · https://www.sofascore.com/terms-and-conditions (text not retrievable, JavaScript-rendered)
- FAQ: https://sofascore.helpscoutdocs.com/article/129-sports-data-api-availability · https://sofascore.helpscoutdocs.com/article/54-my-bet-is-void-because-of-you-data-what-should-i-do
- Corporate: https://corporate.sofascore.com/about · https://corporate.sofascore.com/widgets
- UTR partnership: https://www.sofascore.com/news/sofascore-and-utr-sports-join-forces-to-bring-smarter-tennis-insights-to-fans
- robots.txt: https://www.sofascore.com/robots.txt
- Third-party: https://apify.com/scrapersdelight/sofascore-tennis-scraper · https://github.com/pseudo-r/Public-Sofascore-API

**Data unit.** A point sequence. The third-party schema has `homePoint`, `awayPoint`, `homePointType` and `awayPointType`, plus "point-by-point with serving player". Per-point timestamps are not documented (third-party).

**Coverage by men's tier**

| Tier | Point-level? | Earliest year | Basis |
|---|---|---|---|
| ITF main draw | yes, currently (29 of 30 finished Challenger/ITF matches in one scraper run had stats and point-by-point) | unknown | third-party report |
| ITF qualifying | unknown | unknown | — |
| Challenger main draw | yes, currently (same run) | unknown | third-party report |
| Challenger qualifying | unknown | unknown | — |
| ATP main draw | yes, currently ("41 / 41 (100%)" finished matches in one run; tier mix not stated) | unknown | third-party report |
| ATP qualifying | unknown | unknown | — |

**Data providers.** Not named anywhere.

| Label | URL | Quote |
|---|---|---|
| provider claim | FAQ article 129, "Last updated on November 6, 2025" | "due to agreements with our data providers, we are unable to share the data sources in the form of API endpoints." |
| provider claim | FAQ article 54, November 7, 2025 | "does not directly supply sports data to any online or offline bookmakers"; "the data sources we utilize may coincide with those used by bookmakers" |
| provider claim | https://corporate.sofascore.com/about | "With top-tier data providers in our corner, Sofascore works with reliable deep stats for teams, players, and matches." |
| provider claim | UTR partnership news, 20 Aug 2025 | "UTR Rating data will be directly integrated into tennis player profiles". This is ratings only; point data is not mentioned. |

**Terms and licensing.**
- **search-engine excerpt (not verified; the terms page did not render):** users must not "use any automated means to use the Platform, such as the use of robots or scripts, scraping, crawling, simulation or automated browsing techniques", nor use "data mining, robots or similar gathering or extraction methods in respect of any content on our Platform".
- robots.txt (observed): for all user agents it disallows date-based paths for 2017–2025 (for example `/*/2024-`) and standings pages. Bytespider is fully blocked.
- Licensing offer: there is no data API or data licence. Widgets are free: "Using widgets is completely free and without any limitations." Widgets are live displays, not historical data.
- Historical depth:
  - The Apify scraper says: "As far as SofaScore keeps the season."
  - The pseudo-r API documentation says: "How far back season logs go for minor leagues is undetermined."
  - It also reports bot protection: "Basic cURL or `requests` in Python will return a `403 Forbidden`."
- 2025 ITF disruption: see the forum excerpt in section 2 (applies to SofaScore too).

**Unknowns.**
- The tennis data provider or providers.
- The earliest year of point-by-point by tier, and ITF gaps in 2025.
- Qualifying coverage.
- The full current terms text, including any clause on AI.

**Judgement.** **Low** for this project's compliant use. There is no licence route, the terms (as excerpted) bar automation, and depth is unknown. A separate process is handling SofaScore.

---

## 4. OnCourt (oncourt.info, KAN-soft)

**URLs.** https://www.oncourt.info/ (index.html) · /order.html · /tennis_provider.html · /download.html · /index_rus.html · https://www.kan-soft.com/

**Data unit.** The program replays a match point by point, "like a real-time livescoring".
- Whether the points are stored as data a user can reach in `OnCourt.mdb` or the MySQL dump: **not stated**.
- Point attributes: **not stated**.

**Coverage by men's tier.** Point-level: **unknown for every tier** (not stated). Results coverage below is results only, not points.

| Tier | Results coverage (provider claim) | Point replay |
|---|---|---|
| ITF / Futures main draw | "Results of the main draw of ATP Futures and Satellites since 2004" | not stated |
| ITF qualifying | not listed for men | not stated |
| Challenger main draw | "Results of the main draw of ATP Challengers since 1998" | not stated |
| Challenger and ATP qualifying | "Results of the qualifying rounds to all ATP World Tour and Challengers tournaments since 2000" | not stated |
| ATP main draw | "since 1990" | not stated |

**Access and price (provider claims)**

| Item | Detail |
|---|---|
| Desktop program | Latest is 7.0.3 |
| Access database | "After purchasing a license for OnCourt, you can get a password for the database (OnCourt.mdb, Microsoft Access) and use our data in your own developments!" |
| Licence prices | One-Year 48.95 EUR; Lifetime 88.95 EUR; One-Year + Android or iOS 64.95 EUR; renewal 24 EUR |
| MySQL service for websites | Setup $200, then $50 per month. Contents: "ALL information available within the program like players, tournaments, rankings, match statistics, bookmaker odds etc."; "database is updated automatically, several times per day". The page does not mention point-by-point at all (observed). |
| LIVE (XML) service | $0 setup, $50 per month |
| Timestamps | not stated |

**Terms.**
- The Access database may be used "in your own developments".
- Redistribution, commercial use and machine-learning use: **not stated**.
- No licence agreement (EULA) was found online. The MySQL service is "for use on your site".

**Evidence (provider claim, index page).** "Point-by-point replay of most matches, like a real-time livescoring, but after match is completed". The Russian page adds no detail on replays (observed).

**Unknowns.**
- Which matches have replays ("most matches" is undefined), from which year, and for which tiers.
- Whether replay data sits in the `.mdb` file, the MySQL dump or neither (possibly fetched online on demand, which is **inference**, unverified).
- Where the replay data comes from.

**Judgement.** **Medium, low confidence.** It is cheap and its results coverage reaches ITF and Challenger, but whether point data is included and exportable is unknown. The only way to settle it is a purchase, which is the owner's decision.

---

## 5. Other score and statistics sites (item 4)

### 5.1 TennisLive.net (eHM, s.r.o., Slovakia) — the strongest public web lead

**URLs.**
- Site: https://www.tennislive.net/
- Terms: https://www.tennislive.net/terms/
- robots.txt: https://www.tennislive.net/robots.txt
- Date pages, for example https://www.tennislive.net/2019-12-14/
- Match pages, for example https://www.tennislive.net/atp/match/manuel-guinard-VS-niels-lootsma/m15-cairo-2019-8/

**Data unit.** A point sequence for each game, in this form:

`"0-0 →1-1 <server> serves 15-0 · 15-15 · 30-15 · 40-15 → <player> wins the game"`

- It shows the server, the score after each point, "BP" markers and a "Serve lost" note.
- Match statistics sit alongside: first-serve %, break points, aces, double faults and total points.
- Per-point timestamps: none observed.
- Shot-level data: none.

**Observed spot checks (sample, not a census)**

| Match date | Event (tier, round) | Point-by-point | Stats | URL |
|---|---|---|---|---|
| 2013-06-11 | Kosice Challenger R2 | **No**: "Complete game and point progress is not available for this match." | yes | https://tennislive.net/atp/match/mikhail-kukushkin-VS-guilherme-clezar/kosice-challenger-2013/ |
| 2016-06-14 | Perugia Challenger R2 | yes | yes | https://www.tennislive.net/atp/match/blaz-rola-VS-yannick-maden/perugia-challenger-2016/ |
| 2017-06-13 | Hungary F4 Futures R2 | **No** (same message) | yes | https://www.tennislive.net/atp/match/facundo-mena-VS-vitaliy-sachko/hungary-f4-gyula-2017/ |
| 2018-06-12 | Hungary F4 Futures R2 | yes; game 1 reads "0-15 · 15-30 · 30-30 · 40-30", apparently skipping a point | yes | https://tennislive.net/atp/match/pascal-brunner-VS-petr-michnev/hungary-f4-gyula-2018/ |
| 2019-03-12 | M25 Bakersfield R1 | yes; game 1 starts at "30-0" | yes | https://www.tennislive.net/atp/match/takanyi-garanganga-VS-boris-arias/m25-bakersfield-2019/ |
| 2019-12-13 | M15 Cairo semi-final | yes | yes | https://www.tennislive.net/atp/match/manuel-guinard-VS-niels-lootsma/m15-cairo-2019-8/ |
| 2020-12-15 | M15 Antalya R1 | yes; game 1 starts at "30-0" | yes | https://www.tennislive.net/atp/match/ivan-nedelko-VS-berk-ilkel/m15-antalya-2020-14/ |
| 2021-12-14 | M15 Antalya R1 | yes | yes | https://www.tennislive.net/atp/match/toby-martin-VS-oscar-galimardanov/m15-antalya-2021-34/ |
| 2022-06-11 | Ilkley Challenger Q1 | yes | yes | https://tennislive.net/atp/match/daniel-masur-VS-luca-pow/ilkley-challenger-2022/ |
| 2022-06-11 | Corrientes Challenger Q1 | yes | yes | https://tennislive.net/atp/match/julian-cundom-VS-benjamin-denis-alarcon/corrientes-challenger-2022/ |
| 2022-12-13 | M15 Antalya R1 | yes | yes | https://tennislive.net/atp/match/oscar-moraing-VS-andrea-bolla/m15-antalya-2022-26/ |
| 2023-05-07 | Rome ATP Masters Q1 | yes | yes | https://tennislive.net/atp/match/franco-agamenone-VS-otto-virtanen/internazionali-bnl-ditalia-rome-2023/ |
| 2023-12-12 | M15 Antalya R1 | yes; game 1 reads "0-15 · 0-30 · 15-40", apparently skipping a point | yes | https://www.tennislive.net/atp/match/dmitry-popko-VS-louroi-martinez/m15-antalya-2023-19/ |
| 2024-06-11 | Bratislava 1 Challenger R1 | yes | yes | https://www.tennislive.net/atp/match/alexey-zakharov-VS-zsombor-piros/bratislava-1-challenger-2024/ |
| 2024-12-10 | M15 Antalya R1 | yes | yes | https://tennislive.net/atp/match/franco-agamenone-VS-noah-perfetti-perfetti-noah/m15-antalya-2024-18/ |
| 2025-01-14 | M15 Antalya R1 (×2) | **No** in both | yes | https://tennislive.net/atp/match/carlos-sanchez-jover-VS-miljan-zekic/m15-antalya-2025-1/ · https://tennislive.net/atp/match/savva-polukhin-VS-john-hallquist-lithen/m15-antalya-2025-1/ |
| 2025-09-09 | M15 Hurghada doubles | **No** (empty section) | no | https://tennislive.net/atp/match/attila-boros-bence-boros-VS-timofei-derepasko-viktor-frydrych/m15-hurghada-2025-1/ |
| 2025-12-06 | M15 Antalya Q1; M15 Ceuta Q1 | **No** in both | no | https://tennislive.net/atp/match/daniil-stepanov-VS-mattis-jux/m15-antalya-2025-16/ · https://tennislive.net/atp/match/mario-arce-fernandez-VS-david-munoz-esp/m15-ceuta-2025/ |
| 2025-12-09 | M15 Antalya R1; M15 Hamilton R1 | yes in both | yes | https://tennislive.net/atp/match/maxwell-exsted-VS-imanol-lopez-morillo/m15-antalya-2025-16/ · https://tennislive.net/atp/match/jake-dembo-VS-arjun-mehrotra/m15-hamilton-2025/ |
| 2026-02-03 | M15 Antalya R1 | yes | yes | https://www.tennislive.net/atp/match/attila-boros-VS-noah-perfetti-perfetti-noah/m15-antalya-2026-1/ |
| 2026-06-13 | M15 Nyiregyhaza final | yes | yes | https://www.tennislive.net/atp/match/yannik-kelm-VS-attila-boros/m15-nyiregyhaza-2026/ |

**Coverage by men's tier** (observed; earliest year is the earliest seen in the sample)

| Tier | Point-level? | Earliest year seen | Notes |
|---|---|---|---|
| ITF M15/M25 main draw | yes | 2018 | Absent in the one 2017 sample. Present each December 2019–2025. Absent in January 2025 (0 of 2). |
| ITF qualifying | no in 0 of 2 checked | — | Checked December 2025 only. |
| Challenger main draw | yes | 2016 | Absent in the one 2013 sample. |
| Challenger qualifying | yes | 2022 | Earlier years not checked. |
| ATP main draw | not checked | — | — |
| ATP qualifying | yes | 2023 | Earlier years not checked. |

**Other access details.**
- **Historical access:** public, server-rendered HTML pages plus per-day index pages.
  - robots.txt allows `/` and disallows `/api/...` endpoints.
  - No API or export is mentioned (**not stated**).
- **Data source:** **not stated**. The terms say only that "third-party photographs, logos and supplied data remain subject to their owners' rights and licences".
- **Price:** free to view. Permission is needed for bulk use.

**Terms (provider; operator "eHM, s.r.o., Rudník 232, 044 23, Slovakia"; "Effective and last updated: 13 September 2026").**
- "Systematic scraping, bulk extraction, automated redistribution and commercial reuse require permission or another valid legal basis."
- "Our original texts, design, software and database arrangements are protected"
- "Sporting facts are not automatically our exclusive property."
- "Requests for reuse or notices of infringement should identify the material and be sent through Contact."
- Accuracy: "Scores and match status may be delayed, incomplete or corrected, including after a match ends".
- Machine-learning training and storage: **not stated**. The only AI mention concerns the site's own AI-written previews.
- Coverage claim on the homepage: "Challenger and ITF tournaments worldwide".

**Unknowns.**
- Completeness rate by tier and year.
- How long the 2025 ITF gap lasted.
- ATP main-draw coverage.
- Upstream data source.
- Whether the first-game gaps are a real data defect or an artefact of the fetch tool.
- Whether permission would be granted, and on what storage and machine-learning terms.

**Judgement.** **High if written permission is obtained; not usable for bulk otherwise.** It is the only public source where I saw 2018–2026 ITF main-draw and Challenger point sequences, but it has no timestamps and has known gaps.

### 5.2 Tennis Insight (tennisinsight.com)

- **URLs:** https://tennisinsight.com/guide/ · https://tennisinsight.com/terms-and-conditions/
- **Data unit:** match statistics only. Point-by-point is **not mentioned** (observed on the guide).
- **Tiers (provider claim):** "TennisInsight.com contains all Main Tour and Challenger results (including qualifying) along with certain exhibition results for the ATP Tour dating back to January 2000."
- **Point level, all tiers:** no.
- **Source of stats (provider claim):** "Match stats are difficult to get, especially for the current week where the only source is typically the official Flash scoreboard."
- **API (provider claim):** "We are currently trialing out an API that can be used to access the TI stats through a programming interface such as an VB within Excel or PHP." Stats only.
- **Price:** Premium membership; amount not stated.
- **Terms:** "Engage in unauthorized "spidering", "scraping," or harvesting of content..." is prohibited.
- **Judgement: None.** No point data.

### 5.3 TennisStats.com

- **URLs:** https://tennisstats.com/ · https://tennisstats.com/download-data · https://tennisstats.com/terms-and-conditions
- **Data unit:** match and player statistics. Point-by-point was **not observed** on the pages checked.
- **Download (provider claim):** "Download ATP & WTA Player Data (Excel & CSV)"; "Downloading requires a subscription to Premium services"; "Data updated about 30 minutes after each match." Price not stated.
- **Terms (updated "February 04, 2022"; Canadian operating company):**
  - Prohibited: "use any data mining, robots, or similar data gathering and extraction tools"
  - Prohibited: "Systematically retrieve data or other content from the Site to create or compile, directly or indirectly, a collection, compilation, database, or directory without written permission"
- **Judgement: None.** No point data observed, and the downloads are player-level.

### 5.4 Matchstat.com (and its Tennis API, tennis-api.com)

- **URLs:**
  - matchstat.com returned **HTTP 403** (blocked).
  - https://tennisapidoc.matchstat.com/ · https://tennis-api.com/tennis-point-by-point-api/ · https://tennis-api.com/api-coverage/
- **Data unit (provider claim, live):** "match_id, players, tournament, set, game, point_number, server, score_before_point, score_after_point, event type, timestamp"
- **Documentation claims:** "live scores, match stats, point-by-point action, event timelines"; "historical odds going back as far as 2010". The API covers ATP, WTA, ITF, Grand Slams, Masters and Challengers.
- **Historical point-by-point depth:** **not stated**. The coverage page names point-by-point and timeline only as a live/WebSocket feature.
- **Price:** point-by-point and timeline are in the "Mega plan ($99/mo with WebSocket access)". Sold through RapidAPI or direct.
- **Terms:** no terms or licence link found on the pages read (**not stated**).
- **Point level on the public website for historical ITF/Challenger matches:** unknown (site blocked).
- **Judgement: Low.** Paid, with only live point-by-point documented and historical depth unstated.

### 5.5 Tennis Explorer (tennisexplorer.com; operated by Livesport s.r.o.)

- **URLs:** https://www.tennisexplorer.com/ · https://www.tennisexplorer.com/terms-of-use/
- **Observed:** an ATP match page (https://www.tennisexplorer.com/match-detail/?id=2344563, Rome 2023) shows score, head-to-head, player data and odds (home/away, over/under, Asian handicap, correct score). It has **no point-by-point**. ITF and Challenger pages were not checked.
- **Terms ("In Prague on 09.10.2023"):**
  - "You must not burden our server on which the Website is hosted with automated requests"
  - "you are not permitted to use our content available on the Website by embedding, aggregating, scraping or recreating it without our express consent"
  - "You may not use the Website or our content for commercial purposes."
- **Judgement: None.** No point data observed.

### 5.6 CoreTennis (coretennis.net)

- **URLs:** https://www.coretennis.net/ · https://www.coretennis.net/majic/pageServer/0d01000015/en/Legal-notice.html
- **Observed:** results, calendars and draws ("4,437,833 tennis match results"). No point-by-point was seen on the pages checked.
- **Legal notice (operator aldygo s.a.r.l., France):**
  - "The reproduction or representation of all or part of this site, on any medium whatsoever, is therefore strictly forbidden without the prior written consent of the editor."
  - "You may not reproduce (completely or partially), transmit ... or use the www.coretennis.net website for public or commercial purposes"
- **Judgement: None.**

### 5.7 AiScore (aiscore.com)

- **Blocked:** HTTP 403 on the homepage and tennis page. Point-by-point, terms and API are all unknown.
- **Judgement: Unknown.**

### 5.8 365Scores

- **URL:** https://www.365scores.com/news/%F0%9F%8E%BE-365scores-serves-you-something-new-the-tennis-live-match-tracker. The byline reads "09/10/2025"; the date format is ambiguous.
- **Provider claim:** a Live Match Tracker showing "an interactive court view that shows ball movement, serve direction, and player positioning in real-time". Readers are told to "open any live match", and the article points them to the "2025 Shanghai Masters".
- Historical or finished-match point data: **not stated**.
- Terms page: JavaScript-rendered, not retrieved.
- **Judgement: Low / none.** Live only; there is no evidence of historical data.

### 5.9 Scores24 (scores24.live)

- The tennis index (https://scores24.live/en/tennis) says: "live tennis scores and completed results together in one match centre".
- Match pages and the homepage returned **HTTP 403**. The terms URL tried returned 404.
- Point-by-point is unknown.
- **Judgement: Unknown.**

### 5.10 LiveScore.com (and livescores.com)

- **Observed:** a Challenger qualifying match page (https://www.livescores.com/tennis/atp-challenger/brisbane-challenger-qualification/blake-ellis-vs-james-mccabe/1734823/) shows only "Info" and "Comments" tabs, with no point-by-point.
- The terms page (/en/terms/) is JavaScript-rendered, not retrieved.
- **Judgement: None** (none observed).

### 5.11 Other sites seen in passing (not assessed)

- **tenipo.com:** HTTP 403.
- **TNNS app and Tennis Now:** search-engine excerpts claim point-by-point, live only.
- **ITF World Tennis Tour Live app:** see section 7.

---

## 6. Public datasets (item 5)

**Search coverage:**
- **Kaggle** (public list API) with queries: "tennis point", "tennis point by point", "sofascore tennis", "flashscore tennis", "challenger tennis", "itf tennis", "tennis momentum", "tennis shot", "tennis match charting", "wimbledon 2023", "tennis 2024", "tennis odds statistics point".
- **Hugging Face** (API) with queries: tennis (200 results), sofascore, flashscore, wimbledon, atp, point-by-point.
- **GitHub** (repository search) with queries: tennis point by point, sofascore tennis, flashscore tennis, flashscore point by point, itf tennis data, challenger tennis point, tennis play-by-play, F3Set, tennis shot dataset, tennis dataset broadcast, oncourt tennis.
- **Zenodo:** tennis, "point-by-point", tennis match data.
- **Harvard Dataverse:** tennis.
- **Mendeley Data:** tennis.
- **arXiv:** abstracts containing tennis and point.
- **Figshare:** not effectively searched (see section 1).

**Result:** no public dataset was found with **2019–2026 ITF or Challenger** point data other than the Live Tennis API corpus (already in use).

### 6.1 Summary table

Tier columns: **ITF-M** = ITF M15/M25 main draw, **ITF-Q** = ITF qualifying, **Ch-M** = Challenger main draw, **Ch-Q** = Challenger qualifying, **ATP-M** = ATP main draw, **ATP-Q** = ATP qualifying.

| # | Dataset | Unit | ITF-M | ITF-Q | Ch-M | Ch-Q | ATP-M | ATP-Q | Years | Size | Licence (as labelled) | Upstream | Last update | Flag | Useful |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1 | Live Tennis API corpus mirrors (Kaggle, GitHub, HF) | point sequence | yes | ? | yes | ? | yes | ? | Jan 2023–Aug 2026 | 12.5 MB sample (Kaggle) | CC BY-NC 4.0 (Kaggle); MIT (GitHub licence field); CC BY 4.0 (HF aggregates) | Live Tennis API (DOI 10.5281/zenodo.22048731) | 2026-08-22 / 2026-09-05 | **already in use** | n/a |
| D2 | Sackmann `tennis_pointbypoint` mirrors (Kaggle colinparker; HF Arg314) | point sequence (S/R string) | yes (Futures) | ? | yes | ? | yes | ? | 2011–2017 | 1.4 MB; 13.1k rows | CC BY-NC-SA 4.0 (Kaggle); MIT (HF, conflicts with upstream) | Sackmann `tennis_pointbypoint` (original repo now 404) | 2020-04-20; 2026-01-11 | **Sackmann re-upload** | Low (pre-2018) |
| D3 | marcosjn2 "Tennis Point-by-Point Match Dataset (2015–2026)" (Kaggle) | not stated | ? | ? | ? | ? | ? | ? | title says 2015–2026 | 263.5 MB (atp 145 MB, wta 118 MB, JSONL) | MIT | not stated | 2025-08-29 | provenance unknown | Unknown |
| D4 | 2024 MCM Problem C (Wimbledon 2023 featured matches) and mirrors | point attributes | no | no | no | no | Wimbledon 2023 only | no | 2023 | 1.19 MB CSV | Apache 2.0 (Kaggle mirror); COMAP terms not seen (gated) | COMAP; likely slam point archive (**inference**) | 2024-02-06 | likely Sackmann-slam derivative | None |
| D5 | Wimbledon 2024 point and match level (Kaggle) | point attributes | no | no | no | no | Wimbledon 2024 only | no | 2024 | 1.7 MB | Apache 2.0 | "originally sourced from" Sackmann slam point-by-point (stated) | 2025-06-27 | **Sackmann re-upload** | None |
| D6 | Aneeshers `tennis-sackmann-archive` (GitHub + HF) | slam point attributes and match files | no | no | no | no | slams | no | slams 2011–2024 | — | CC BY-NC-SA 4.0 | Sackmann (stated) | 2026-06-25 | **Sackmann mirror** | None (already held) |
| D7 | SofaScore-scraped samples (GitHub: ChiefOmid, kimia2328, shahabnajmosadatypy) | point sequence and stats | ? | ? | ? | ? | ? | ? | 60 days; Feb–Mar 2024 | "small sample" | MIT / none | SofaScore scraping | 2025–2026 | terms-problematic | None |
| D8 | F3Set (tennis) | shot-level | no | no | no | no | yes (plus Grand Slams, Olympics, WTA) | no | 2012–2023 | 114 matches, 42,846 shots | CC BY 4.0, "strictly intended for research purposes" | broadcast video (YouTube links only) | 2024-10 (repo) | — | None (tour-level) |
| D9 | OSL-loc-tennis-public (HF) | shot-timing events | no | no | no | no | Wimbledon/US Open only | no | 2015–2021 | 3,450 rows | AGPL-3.0 | broadcast video | 2026-09-08 | — | None |
| D10 | Harvard Dataverse, "Disequilibrium Play in Tennis" | serve/point | no | no | no | no | charted matches | ? | not stated | ~31 MB | CC0 | "Match Charting Data" from Tennis Abstract | 2024-02-23 | **MCP-derived** | None |
| D11 | Mendeley, "Tennis Shot Side-View and Top-View" | shot clips | no | no | no | no | no | no | — | 472 clips | CC BY 4.0 | lab / amateur | 2024-05-01 | — | None |
| D12 | HF Tang1166/TennisDB; Kaggle joekinder/st311-tennis | not stated | ? | ? | ? | ? | ? | ? | ? | 8.38 GB zip; 14.6 GB | none; unknown | not stated | 2026-09-22; 2025-05-04 | undocumented | Unknown |

### 6.2 Details and evidence

**D1 — Live Tennis API mirrors (already in use; flagged, not evaluated)**
- URLs: Kaggle https://www.kaggle.com/datasets/livetennisapi/tennis-point-by-point-dataset-atp-to-itf · GitHub https://github.com/livetennisapi/livetennisapi-data · HF https://huggingface.co/datasets/livetennisapi/tennis-match-outcome-studies
- Kaggle subtitle (third-party report): "173,571 matches with point sequences — free for academic research (DOI)"
- The card says data from October 2025 is "live-observed" with UTC timestamps. The 2023–2025 part was "reconstructed" from third-party feeds without timestamps.
- Licence labels differ across mirrors (observed): CC BY-NC 4.0 on Kaggle, MIT in the GitHub licence field, CC BY 4.0 for the HF aggregates.

**D2 — Sackmann `tennis_pointbypoint` mirrors**
- Kaggle https://www.kaggle.com/datasets/colinparker/pointbypoint-bo3-tennis-data-2011-2017:
  - Subtitle: "ATP Matches, including Qualifiers, Challengers, and Futures"
  - Card: "Data derived from 'Jeff Sackmann's Github tennis_pointbypoint repo'". Excludes Grand Slams. "Archive 2011–2015, current 2015–2017."
  - The card says files are split into qualifying and main draw, but it does not say which tiers have qualifying files, so the qualifying cells in 6.1 are "?".
- HF https://huggingface.co/datasets/Arg314/tennis_momentum_dataset:
  - Fields: `pbp_id`, `date`, tournament, `server1`, `server2`, `winner`, `pbp`, `wh_minutes`.
  - Provenance: **not stated**. **Inference:** the field names match Sackmann's `tennis_pointbypoint` format.
- Upstream https://github.com/JeffSackmann/tennis_pointbypoint returns **404** (observed).
- This data is not in the "already in use" list. Check whether the project holds it.

**D3 — marcosjn2** (https://www.kaggle.com/datasets/marcosjn2/tennis-point-by-point-match-dataset-20152025)
- Observed metadata:
  - "Description: None provided"
  - Files `atp-matches.jsonl` (145,024,923 bytes) and `wta-matches.jsonl` (118,527,233 bytes)
  - Licence MIT; 2 versions; last update 2025-08-29
- Provenance, tiers and fields are **not stated**. The title says 2015–2026 but the last update is August 2025.
- **Unknown.** Inspecting it would mean downloading at least part of a 138 MB file (not done).

**D4 — 2024 MCM Problem C**
- COMAP page https://www.comap.org/membership/member-resources/item/momentum-in-tennis says: "The data for this match is in the provided data set, 'match_id' of '2023-wimbledon-1701'". Also: "You must have a Mathmodels Membership to download..."
- Mirrors:
  - Kaggle https://www.kaggle.com/datasets/dengfengqi/2023-wimbledon-point-by-point-data: `Wimbledon_featured_matches.csv`, 1,194,113 bytes, plus `data_dictionary.csv`.
  - HF https://huggingface.co/datasets/saxasxa/2024_Wimbledon_featured_matches: the same byte sizes.
- The 46-column data dictionary (observed) includes `elapsed_time`, `server`, `serve_no`, `point_victor`, aces, winners, `winner_shot_type`, unforced errors, net points, break points, `p1_distance_run`, `rally_count`, `speed_mph`, `serve_width`, `serve_depth` and `return_depth`.
- Provenance: **not stated by COMAP** (page gated). **Inference:** it is the same layout as Grand Slam point-by-point files, like D5, whose card credits Sackmann's slam archive.
- Many small Hugging Face derivatives exist (sarahzhoo620, ShenZijie, zyyyhi, ttydsc30, zhennengchi).

**D5** (https://www.kaggle.com/datasets/rewantbhriguvanshi/wimbledon-2024-point-and-match-level-statistics)
- "over 48,000 rows"
- "Base data originally sourced from" Sackmann's slam point-by-point repository

**D6** (https://github.com/Aneeshers/tennis-sackmann-archive)
- "The `slam_pointbypoint` snapshot was taken from upstream commit `6febb77` (October 2024); the `atp` and `wta` snapshots from upstream commits made in June 2026."
- "It exists so the data remains available and citable."

**D7 — SofaScore-scraped samples**
- https://github.com/ChiefOmid/Tennis-Project:
  - Tables include `raw_point_by_point_parquet`
  - "60 days of professional tennis matches"; "Only a small sample of the dataset is included in this repository"
- https://github.com/kimia2328/tennis_data_analysis: "February 1 to March 31, 2024"
- **Inference:** a scraped SofaScore origin conflicts with SofaScore's terms as excerpted.

**D8 — F3Set** (https://arxiv.org/html/2504.08222 · https://github.com/F3Set/F3Set)
- "114 broadcast matches", "11,584 rallies", "42,846" shots, 2012–2023
- "Grand Slams, Olympics, and major ATP/WTA tournaments"
- The authors "do not redistribute video content, providing only YouTube links"

**D9 — OSL-loc-tennis-public** (https://huggingface.co/datasets/OpenSportsLab/OSL-loc-tennis-public)
- Wimbledon 2015–2019 and US Open 2019–2021 broadcasts
- Labels "swing" / "no_swing" with timestamps

**D10 — Disequilibrium Play in Tennis** (https://doi.org/10.7910/DVN/RQ6JVL)
- CC0
- Raw data from Tennis Abstract "Match Charting Data"

**D11 — Tennis Shot Side-View and Top-View** (https://data.mendeley.com/datasets/75m8vz7jr2)
- 472 clips of single strokes on institutional courts
- Not professional matches

**D12 — undocumented archives**
- https://huggingface.co/datasets/Tang1166/TennisDB: "8.38 GB" `data.zip`, no card
- https://www.kaggle.com/datasets/joekinder/st311-tennis: 14.6 GB, "No description provided"

**Checked; not point data or not relevant:**
- Kaggle: ehallmar (2M+ matches with betting data, 2018), diphibnh (814,047 matches), karimmaj (from tennis-data.co.uk), nixchamp, guillemservera.
- MCP copies: Kaggle ryanthomasallen, 2018; GitHub wongers6/kalshi_tennis, a copy of the MCP description.
- Zenodo: no tennis point dataset surfaced.
- Dataverse: "Line Movement Dataset" (betting lines).
- Hugging Face: several toy or anonymised sets (alifend910 3.81 kB; outragest `x0`–`x19` features).
- arXiv tennis point papers found use Grand Slam data: 2609.07617, 2602.08083, 2509.01243, 2506.05866, 2505.21882. 2604.16129 uses SofaScore match-level stats for 2016–2025 ATP, not point-by-point.

---

## 7. Context: changes to the ITF data supply that matter for 2025–2026

| Label | URL | Quote |
|---|---|---|
| provider claim | https://www.infobae.com/aroundtherings/articles/2021/07/12/itf-launches-official-live-scoring-mobile-app-for-itf-pro-circuit (page date 12 Jul 2021; the tournament counts suggest an older article, **inference**) | "The app offers point-by-point score updates straight from the umpire's chair at more than 1,200 Pro Circuit tournaments per year." "...will be powered by Sportradar AG." |
| third-party report | https://www.sportspro.com/news/infront-itf-data-streaming-partnership-lfp-ligue-1-2-betting-video-rights/ (18 Sep 2023) | "With its winning bid, Infront will replace Sportradar as the ITF's data partner." "Infront to provide data coverage for more than 58,000 tennis games each year beginning in 2025" |
| provider claim | https://developer.sportradar.com/sportradar-updates/changelog/tennis-api-coverage-updates | "Starting in 2025, the ITF World Tennis Tour will no longer be a part of the Tennis API." |
| search-engine excerpt | tennisforum and menstennisforums threads (TollBit-blocked) | After the ITF live-score change, third-party apps "are unable to provide point by point updates on ITF matches". The ITF match stats page "doesn't show the most important stats like first serve points percentage won". |

**Inference.** Sites that show ITF point-by-point probably depend on the ITF's official umpire-scoring feed. The January 2025 TennisLive gap (section 5.1) fits the switch. Any 2025 ITF point series from any source should be checked for a gap in early 2025.

---

## 8. Incidental observations (outside scope; flagged only)

- **Sackmann's public repositories.**
  - `github.com/JeffSackmann/tennis_atp`, `/tennis_slam_pointbypoint` and `/tennis_pointbypoint` all return **404**.
  - The profile shows "Repositories 1" (only `tennis_MatchChartingProject`, pushed 2026-09-18).
  - The GitHub API lists only that repository.
  - Mirrors exist (D2, D6), so the project's local copies may now be the canonical ones.
- **Live Tennis API mirrors.** Licence labels are inconsistent across mirrors, and the Kaggle card says the 2023–2025 data was reconstructed without timestamps (D1).

---

## 9. Ranked summary: usefulness for point-level data on 2019–2026 ITF and Challenger men's matches

| Rank | Source | Point-level ITF / Challenger 2019–26 | Access route | Terms position | Usefulness | Why (one sentence) |
|---|---|---|---|---|---|---|
| 1 | **TennisLive.net** | **Observed**: ITF main 2018→2026 (gap Jan 2025); Challenger main 2016→; Challenger Q 2022 | public HTML pages | bulk extraction "require[s] permission" | **High, conditional on permission** | The only public source where I saw ITF main-draw and Challenger point sequences across 2019–2026, but it has no timestamps, ITF qualifying lacks point-by-point, and bulk use needs permission. |
| 2 | **Enetpulse** (Livesport B2B) | claimed: point history kept "since 2020"; Challenger is named in the coverage claim, but whether the history product includes Challenger is not stated; ITF not stated | paid licence ("contact Sales") | licensed | **Medium (low confidence)** | A lawful paid route with point history claimed from 2020, but tier coverage of the history product, ITF, price and machine-learning terms are unknown. |
| 3 | **OnCourt** | "most matches" replayable; tiers and years not stated | EUR 48.95/yr program; Access DB; MySQL $200 + $50/mo | "use our data in your own developments" | **Medium (low confidence)** | Cheap and covers ITF and Challenger results, but it is unknown whether point replays are in the exportable database. |
| 4 | Flashscore / Tennis24 pages | third-party: current Challenger and ITF point-by-point, some ITF missing; history unverified | public JavaScript pages | scraping and extraction prohibited | **Low** | Point-by-point exists, but the terms forbid extraction and historical depth is unverified. |
| 5 | SofaScore | third-party: current Challenger and ITF point-by-point; depth "undetermined" | public JavaScript pages; no API | automated access prohibited (excerpt) | **Low** | No licence route, terms bar automation, and a separate process already covers it. |
| 6 | D2 Sackmann `tennis_pointbypoint` mirrors | Futures, Challenger and qualifying, **2011–2017 only** | download | CC BY-NC-SA 4.0 (upstream) | **Low** | Real lower-tier point data but before 2018; check whether the project already holds it. |
| 7 | D3 marcosjn2 JSONL (Kaggle) | unknown | download | MIT (as labelled) | **Unknown** | No card, provenance or tier information; it would need inspection before any judgement. |
| 8 | Matchstat / Tennis API | live point-by-point documented; historical depth not stated | paid API (point-by-point in $99/mo plan) | not stated | **Low** | Paid, with only live point-by-point documented and the website blocked. |
| 9 | 365Scores | live tracker only (article dated "09/10/2025") | app / web | not retrieved | **Low / none** | Live only, with no historical evidence. |
| 10 | D12 TennisDB (HF) / st311 (Kaggle) | unknown | download (8–15 GB) | none / unknown | **Unknown** | Undocumented large archives; provenance unknown. |
| 11 | Scores24; AiScore | unknown | blocked (403) | unknown | **Unknown** | Pages blocked, so nothing could be assessed. |
| 12 | D1 Live Tennis API mirrors | yes (2023–2026) | download (sample) | CC BY-NC 4.0 / MIT / CC BY 4.0 labels | **n/a (already in use)** | Same upstream as the Zenodo sample already in use. |
| 13 | Tennis Insight | no | subscription | anti-scraping | **None** | Match stats only. |
| 14 | TennisStats.com | no (not observed) | Premium downloads (player-level) | anti-scraping | **None** | No point data seen. |
| 15 | Tennis Explorer | no (ATP page observed) | public | anti-scraping (Livesport) | **None** | No point-by-point section. |
| 16 | CoreTennis | no | public | reproduction forbidden | **None** | Results and draws only. |
| 17 | LiveScore.com | no (Challenger Q page observed) | public | not retrieved | **None** | Only info and comments tabs. |
| 18 | D4 MCM 2024 / D5 Wimbledon 2024 / D6 archive | Grand Slam only | download | various | **None** | Wimbledon-only and slam-archive-derived, which the project already holds. |
| 19 | D8 F3Set / D9 OSL | tour-level shots only | download (annotations) | CC BY 4.0 / AGPL-3.0 | **None** | Broadcast shot data from top-level events only. |
| 20 | D10 Dataverse / D11 Mendeley / D7 SofaScore samples | no / no / tiny | download | CC0 / CC BY / MIT | **None** | Derived from MCP, amateur, or tiny scraped samples. |

---

## 10. Open questions that would change the ranking (options for the owner; none approved)

1. **TennisLive.net.** Would eHM, s.r.o. grant written permission or a licence for bulk historical access, and on what storage and machine-learning terms? Also:
   - What is their data source?
   - How complete are 2019–2026 ITF and Challenger point sequences?
   - Are the first-game gaps real?
2. **Enetpulse.** Does "Point by Point History" include ITF M15/M25 and qualifying? What are the earliest date, format, per-point timestamps, price and machine-learning terms?
3. **OnCourt.** Does `OnCourt.mdb` (or the MySQL dump) contain point replays? For which tiers and since when? Only a purchase (EUR 48.95) would answer this.
4. **Sackmann `tennis_pointbypoint`.** Does the project already hold the 2011–2017 lower-tier point-by-point data? The original repo now returns 404.
5. **D3 (marcosjn2).** What is it, and where does it come from? Only its metadata was read.
