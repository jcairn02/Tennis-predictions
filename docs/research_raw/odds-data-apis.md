# Research archive: odds-data-apis

*Raw structured output from the 2026-06-10 multi-agent research run. Facts below are as-reported by research agents; entries in the Verifications section were independently adversarially checked.*

## Facts

### tennis-data.co.uk coverage (high) **[decision-critical]**
tennis-data.co.uk offers one results+odds file per season: ATP (men) 2000 through 2026 and WTA (women) 2007 through 2026; download links on alldata.php are .xls for 2000-2012 and .xlsx for 2013-2026 (no .csv/.zip links remain on the page as of 2026-06-10, despite site text still saying 'CSV/Excel format'). Men's results go back to January 2000, head-to-head betting odds to 2001, WTA results+odds from 2007.

Source: http://www.tennis-data.co.uk/alldata.php

### tennis-data.co.uk odds definition (high) **[decision-critical]**
Per the official notes.txt, tennis-data odds 'generally represent the most recent before play starts, as reported by oddsportal.com and the individual bookmakers' — i.e., closing-line-ish prices, not opening lines. Documented bookmaker columns: B365 (Bet365), B&W (Bet&Win), CB (Centrebet), EX (Expekt), LB (Ladbrokes), GB (Gamebookers), IW (Interwetten), PS (Pinnacle), SB (Sportingbet), SJ (Stan James), UB (Unibet), plus MaxW/MaxL and AvgW/AvgL computed from Oddsportal.

Source: http://www.tennis-data.co.uk/notes.txt

### tennis-data.co.uk modern columns (high)
Verified by parsing the live files on 2026-06-10: the 2024 ATP file carries only B365W/L, PSW/L, MaxW/L, AvgW/L as odds columns; the 2025 and 2026 ATP and WTA files add BFEW/BFEL (Betfair Exchange winner/loser odds), a column pair NOT documented in notes.txt. Older bookmaker columns (CB, EX, LB, UB, SJ, GB, IW, SB, B&W) only exist in earlier-era files.

Source: http://www.tennis-data.co.uk/2025/2025.xlsx

### tennis-data.co.uk Pinnacle gap (PSW/PSL blanks) (high) **[decision-critical]**
Verified by direct parse on 2026-06-10: Pinnacle columns PSW/PSL are 0.4% blank in ATP 2024 (2691/2703 filled), 4.2% blank in ATP 2025 (degradation starts Oct 2025: 228/291 Oct, 65/72 Nov), and 94.5% blank in ATP 2026 — 71/238 matches filled in Jan 2026 and ZERO filled from Feb 2026 onward (0/293 Feb, 0/223 Mar, 0/259 Apr, 0/272 May, 0/11 Jun). WTA 2026 is similar: 101/1248 filled. The columns still exist but are empty; B365 and Max/Avg remain ~fully populated.

Source: http://www.tennis-data.co.uk/2026/2026.xlsx

### tennis-data.co.uk Pinnacle gap cause (medium) **[decision-critical]**
tennis-data.co.uk publishes no explanation for the PSW/PSL blanks, but the timing matches Pinnacle closing its public API on July 23, 2025 and odds aggregators subsequently dropping Pinnacle from monitoring (e.g., WinnerOdds publicly stopped monitoring Pinnacle); tennis-data sources its odds via oddsportal.com, so once Pinnacle disappeared from its source the column went blank. Inference, not an official statement.

Source: https://winnerodds.com/we-stop-monitoring-pinnacle/

### tennis-data.co.uk Betfair replacement (high) **[decision-critical]**
Verified by direct parse: the BFEW/BFEL (Betfair Exchange) columns introduced in the 2025 files are filled for 24.6% of ATP 2025 rows (added mid/late season) and 92.4% of ATP 2026 rows — making Betfair Exchange odds the de facto sharp-price column in tennis-data files from 2026 onward, replacing Pinnacle for closing-line benchmarking.

Source: http://www.tennis-data.co.uk/2026/2026.xlsx

### tennis-data.co.uk update cadence (high)
Files are 'updated weekly at the end of each tournament (2 weeks after Grand Slams)' per the site's data.php; verified current on 2026-06-10: homepage banner says 'Data Updated: 7th June 2026' and the 2026 ATP file's last match date is 2026-06-07 (WTA 2026-06-06) — i.e., ~3 days behind real time.

Source: http://www.tennis-data.co.uk/data.php

### tennis-data.co.uk terms of use (high)
tennis-data.co.uk data is 'completely FREE' and 'free to use' (site is funded by bookmaker advertising); there is no formal license or API terms page, only a liability disclaimer and privacy policy, and content is marked 'All Rights Reserved' — fine for personal modeling use, no redistribution license granted.

Source: http://www.tennis-data.co.uk/

### Pinnacle public API shutdown (high) **[decision-critical]**
Pinnacle's official API documentation states: 'Access to Pinnacle API suite has been closed for the general public since July 23rd, 2025. We offer bespoke data services for select high value bettors & commercial partnerships. We also support academics and pregame handicapping projects' — applications via api@pinnacle.com; API use also requires a funded Pinnacle account.

Source: https://github.com/pinnacleapi/pinnacleapi-documentation

### Pinnacle direct API price (medium)
Pinnacle's own (now non-public) API was priced around EUR 5,000/month according to pinnodds.com's comparison table ('Pinnacle's own API was €5,000/mo and is no longer sold to the public') and community reports on Arbusers — i.e., direct access is not realistic for a solo bettor even where offered.

Source: https://pinnodds.com/

### the-odds-api Pinnacle inclusion (high) **[decision-critical]**
the-odds-api includes Pinnacle as bookmaker key 'pinnacle' in its EU region, with the caveat 'Odds are from public website which may incur a delay' — i.e., post-shutdown they scrape Pinnacle's public site rather than the API, so Pinnacle prices are still flowing as of June 2026 but are not tick-accurate.

Source: https://the-odds-api.com/sports-odds-data/bookmaker-apis.html

### the-odds-api plans (high) **[decision-critical]**
the-odds-api pricing (June 2026): free Starter tier 500 credits/month, then $30/mo for 20K credits, $59/mo for 100K, $119/mo for 5M, $249/mo for 15M; covers 70+ sports including tennis ('All Grand Slams and more') across 40+ bookmakers in US/UK/EU/AU regions.

Source: https://the-odds-api.com/

### the-odds-api historical odds (high) **[decision-critical]**
the-odds-api's Historical Sports Odds API provides snapshots back to June 6, 2020 at 10-minute intervals, improving to 5-minute intervals from September 2022; historical requests cost 10 credits per region per market (10x the live rate). It is snapshot-based: opening lines and full line movement must be reconstructed by stepping through snapshots — there is no dedicated opening-line or movement-history endpoint.

Source: https://the-odds-api.com/liveapi/guides/v4/#overview

### the-odds-api update intervals (high)
the-odds-api refresh intervals: featured markets (h2h/spreads/totals) 60s pre-match and 40s in-play; additional markets 60s/60s; outrights 5min; betting exchanges 20s pre-match and 10s in-play; intervals start tightening from the pre-match rate 6 hours before event start.

Source: https://the-odds-api.com/sports-odds-data/update-intervals.html

### the-odds-api tennis markets (medium)
For tennis, the-odds-api exposes tournament-level sport keys (e.g., ATP/WTA French Open) with h2h (match winner) as the core featured market; set-level period markets exist (h2h_s1, h2h_s2, spreads_s1, alternate_totals_s1), while full-match spreads/totals are 'mainly available for US sports and bookmakers' — so games-handicap/total-games coverage for tennis is thin compared to dedicated tennis feeds.

Source: https://the-odds-api.com/sports-odds-data/betting-markets.html

### BetsAPI Pinnacle feed (medium) **[decision-critical]**
BetsAPI operates a Pinnacle odds product whose API reference is hosted on Pinnacle's own official GitHub Pages org ('Pinnacle - Bets API Reference' at pinnacleapi.github.io/betsapi, a ReDoc spec), strongly indicating BetsAPI is a sanctioned redistribution channel for Pinnacle data after the public API shutdown.

Source: https://pinnacleapi.github.io/betsapi

### BetsAPI pricing and products (medium)
BetsAPI packages start around $10/month per API package with $1-$2 one-day trial packages (price doubles each repurchase, max 3 buys); products include the Events API (inplay events, event odds, odds summary), Bet365 InPlay/PreMatch, Betfair SportsBook + Exchange, BWin, Sbobet, and 1xBet endpoints, plus tennis rankings. Exact tier prices sit behind a Cloudflare-gated members area (betsapi.com/mm/pricing_table) and were not retrievable.

Source: https://betsapi.com/docs/pricing.html

### RapidAPI Pinnacle Odds (tipsters) (medium)
A 'Pinnacle Odds' API on RapidAPI (vendor 'tipsters') offers fixtures, live odds, special markets and event archives with a free plan and paid plans from ~$10/month including 'limited history' — one of the cheapest programmatic Pinnacle-price routes for an individual, though it is a third-party relay, not official.

Source: https://rapidapi.com/tipsters/api/pinnacle-odds

### bettingiscool Pinnacle archive (high) **[decision-critical]**
api.bettingiscool.com ('Pinnacle Data API') sells a Pinnacle-only historical archive: every chronological odds movement (including in-play), opening AND closing lines with devigged probabilities, moneylines/spreads/totals/alt lines, for tennis continuously from Jan 2021 to now; plans EUR 49/149/249 per month (Enterprise adds player props collected from March 2026); token billing = 1 token per request + 1 per returned row, with a full_history=1 parameter returning thousands of movement rows per event. This is the most complete Pinnacle tennis line-movement source available to individuals.

Source: https://api.bettingiscool.com/

### pinnodds live Pinnacle stream (high) **[decision-critical]**
pinnodds.com streams live+prematch Pinnacle odds over WebSocket/SSE from an authenticated connection to Pinnacle's own MQTT broker, claiming ~100-500ms delivery after a price change (vs ~10s polling APIs) and 'sub-second update latency'; tennis is covered with full period/spread/total depth; pricing $0-$299/month with a raw byte-identical MQTT passthrough add-on at +$99/month; payment via crypto (BTC/ETH/USDT/TRX through NowPayments) with no account signup — notable fit for a crypto-funded bettor. Unofficial/gray-area sourcing; longevity risk if Pinnacle cuts the broker connection.

Source: https://pinnodds.com/

### odds-api.io dropped Pinnacle (high) **[decision-critical]**
odds-api.io does NOT carry Pinnacle: after the July 2025 shutdown it replaced Pinnacle with Betfair Exchange, SingBet, Polymarket/Kalshi and FanDuel as 'sharp' references (its blog argues Betfair Exchange pricing is 'particularly strong' for soccer/tennis/cricket); plans are Free (100 req/hr, 2 bookmakers), then GBP 99/179/229 per month at 5,000 req/hr, WebSocket push costs 2x plan price; 265+ bookmakers, 34 sports including tennis.

Source: https://odds-api.io/blog/pinnacle-api-shutdown-alternatives

### OpticOdds and OddsJam (medium) **[decision-critical]**
OpticOdds (200+ sportsbooks) and OddsJam's API are operator/enterprise-focused with no public pricing — access requires a sales call; Pinnacle is not listed among supported books on OpticOdds' public sportsbook page despite a 'pinnacle-api' landing URL. OddsJam's consumer tool subscriptions run $99-$499/month but its data API is contact-sales only. Not realistic primary feeds for a solo bettor.

Source: https://opticodds.com/sportsbooks/pinnacle-api

### Other Pinnacle-inclusive aggregators (medium)
SportsGameOdds claims Pinnacle odds via REST API ('no scraping required') across 20+ sports including tennis, free plan available, paid $99-$499/month, with opening lines, lastUpdatedAt timestamps and closing odds; competitor oddspapi.io claims 350+ bookmakers including sharps/Pinnacle, a 250-request/month free tier and historical data included at no extra cost (custom pricing). Both are self-reported marketing claims — verify Pinnacle tennis coverage on a trial before committing.

Source: https://sportsgameodds.com/bookmakers/pinnacle-odds-api

### api-tennis.com (medium)
api-tennis.com is a tennis-specific API: livescores, fixtures, rankings, and odds at $40/mo (8K req/day), $60/mo (80K/day), $80/mo (200K/day, adds in-play odds), 14-day free trial; its get_odds documentation examples show bet365 prices and no Pinnacle is evidenced in the public docs — treat it as a scores/soft-odds source, not a sharp-price source.

Source: https://api-tennis.com/

### OddsPortal scraping viability 2026 (high) **[decision-critical]**
OddsPortal is scrapeable in 2026 at 'Medium' difficulty (3/5 per Scraperly's 2026 guide): odds require JavaScript rendering (or WebSocket interception which yields odds JSON before DOM render), ~200 requests/IP triggers 429 rate limiting, navigator.webdriver and header fingerprint checks exist, but no enterprise WAF (Cloudflare/Akamai/DataDome) is confirmed; datacenter proxies + curl_cffi or Playwright suffice. A May 2026 site change broke scrapers by returning empty odds arrays with HTTP 200 — validate non-empty results.

Source: https://scraperly.com/scrape/oddsportal

### OddsPortal scraper tooling (high)
OddsHarvester (github.com/jordantete/OddsHarvester) is actively maintained (v0.3.0 released May 20, 2026; 187 stars) and scrapes OddsPortal tennis markets (match_winner, total_sets/total_games over-under, asian_handicap, correct_score) for both historic seasons and upcoming matches, with per-bookmaker odds, average odds, and optional odds-movement history, via Playwright with proxy/user-agent/delay controls.

Source: https://github.com/jordantete/OddsHarvester

### Betfair historical data coverage (high) **[decision-critical]**
Betfair's Historic Data site (historicdata.betfair.com) contains complete historical Exchange data for nearly all markets since 2016 (when the current API launched), delivered as TAR archives of per-market JSON stream files; tennis is its own purchasable package (it is explicitly excluded from the 'Other Sports' bundle, alongside football, horse racing, cricket and golf).

Source: https://support.developer.betfair.com/hc/en-us/articles/8085210924957-Which-Sports-Are-Included-in-the-Other-Sports-package

### Betfair historical data tiers (high) **[decision-critical]**
Betfair historic data tiers: Basic = FREE, 1-minute intervals, last-traded price only, no volume; Advanced = paid, 1-second intervals, top-3 price ladder with traded volume; Pro = paid, full API tick intervals (~50ms) with full ladder and volume. Paid-tier prices are only displayed per sport/month at checkout after Betfair login (not publicly indexed); even free data goes through the 'purchase' flow.

Source: https://betfair-datascientists.github.io/data/usingHistoricDataSite/

### Betfair live API access cost (high) **[decision-critical]**
Betfair Exchange API: the delayed App Key is free for development; the Live App Key costs a one-off GBP 499 activation fee (non-refundable, debited from the Betfair account; older docs cited GBP 299), there are no ongoing API charges, personal betting use is allowed but read-only use of the live key is not permitted and commercial use needs Betfair approval. The Exchange Stream API (low-latency push of market/price/order changes) requires the Live App Key for live data.

Source: https://support.developer.betfair.com/hc/en-us/articles/115003864531-Are-there-any-costs-associated-with-API-access

### Official tennis data rights chain (high)
Official point-by-point tennis data flows from the chair umpire's tablet: ATP/Challenger rights are managed by Tennis Data Innovations (TDI, ATP joint venture est. 2020) and distributed via a multi-year Sportradar agreement (renewed for 2024-2029) including a 'secondary feed' of umpire-chair scores for betting; ITF data/streaming rights moved from Sportradar to Infront Bettor for 2025-2029, and the ITF World Tennis Tour left Sportradar's Tennis API in 2025. These are enterprise licenses, not available to individuals.

Source: https://sportradar.com/content-hub/news/tennis-data-innovations-and-sportradar-team-up-to-expand-official-tennis-data-distribution/?lang=en-us

### Sportradar pricing for individuals (medium) **[decision-critical]**
Sportradar API access requires a sales call and contract; reported entry pricing runs from ~$500-$1,000/month at the low end to enterprise contracts of $10,000+/month, with no self-service production signup (only limited free developer trial keys for evaluation) — effectively out of reach as a production feed for a solo bettor.

Source: https://sportsapi.com/api-directory/sportradar/

### Sportradar live-data latency (high)
Sportradar's own Live Data 'Latency Indicator' documentation classifies observed event-update latency into bands: Low ~0-<4s, Moderate ~4-<8s, High ~8-<12s, Very High ~12-<16s, Exceptional 16+s — i.e., even official-feed consumers see multi-second latency depending on coverage source.

Source: https://docs.sportradar.com/live-data/latency-indicator-beta

### Courtsiding latency reality (medium) **[decision-critical]**
In-play tennis markets suspend and reset after every point, with windows between winning shot and odds reopening as tight as 1-2 seconds; books rely on the umpire manually entering the score, which then flows to data companies (TDI's 'true real-time' system now fires a signal before the umpire presses the button); TV/stream viewers sit several seconds behind, and Betfair adds an in-play bet-execution delay (~5s typical, up to 10s) specifically to blunt courtsiders. Practical implication: an individual polling free scoreboards cannot win the in-play latency race in 2026 — courtsiding is reported as much harder and rarer in tennis now.

Source: https://g3newswire.com/game-set-tech/

### Sofascore unofficial access (medium)
Sofascore has no official public API; its internal API is scrapeable (still working per March 2025 reports and tooling like ScraperFC's Sofascore module), but users report needing ~25-30 seconds between calls to avoid Cloudflare bans and Varnish 503s, with weekend cutoffs at higher volumes — usable for pre-match/near-live stats, not for low-latency in-play betting; commercial wrappers exist on RapidAPI (apidojo 'Sofascore') and Apify.

Source: https://forum.betangel.com/viewtopic.php?t=30462

### Flashscore unofficial access (medium)
Flashscore has no official API; current access is via Playwright/Selenium scrapers (e.g., gustavofariaa/FlashscoreScraping) or paid Apify actors including a dedicated 'Flashscore Tennis Scraper' covering ATP/WTA/ITF/Challenger live scores, set-by-set results and fixtures — viable for results/fixtures harvesting, with anti-bot friction lower than Sofascore but latency unsuitable for in-play edges.

Source: https://apify.com/extractify-labs/flashscore-tennis-matches

### BetsAPI live tennis events (medium)
BetsAPI's Events API exposes in-play events with live scores and odds summaries, plus dedicated Bet365 InPlay endpoints (Bet365's tennis feed is backed by official scout data), at package prices starting ~$10/month — the cheapest semi-reliable programmatic live tennis score+odds combo for an individual, though latency vs courtside is multi-second and unspecified.

Source: https://betsapi.com/docs/pricing.html

### Kaggle mirror of tennis-data (medium)
Kaggle hosts mirrors of tennis-data.co.uk (e.g., 'ATP and WTA Tennis Results and Betting odds Data', 'ATP Tennis Data with betting odds') useful for bulk historical bootstrapping, but they lag the weekly-updated source files and inherit the same Pinnacle column gaps — always rebuild current-season data from tennis-data.co.uk directly.

Source: https://www.kaggle.com/datasets/hakeem/atp-and-wta-tennis-data

## Gaps noticed by the research agent
- tennis-data.co.uk gives NO official notice that PSW/PSL went dead in 2026 — notes.txt still documents the column and nobody (forums, Kaggle, GitHub) has written this up; any backtest spanning 2025-2026 must switch its sharp-line reference from PSW/PSL to BFEW/BFEL around Oct 2025-Jan 2026, and no public guide covers that splice (vig profile differs: exchange odds are commission-free gross prices, bookmaker odds carry vig).
- The BFEW/BFEL columns are undocumented in notes.txt (no definition of whether they are last-traded exchange price or SP, pre-commission); semantics need empirical validation against Betfair historic data before using them for CLV.
- No public source states when Pinnacle was added to the-odds-api's EU region, so how far back Pinnacle appears in their 2020+ historical snapshots is unknown — needs a cheap probe of the historical endpoint before buying credits for a Pinnacle CLV backfill.
- Betfair Advanced/Pro historical tier prices are only visible per sport-month at checkout behind login — nobody publishes a tennis price list, making cost forecasting impossible without an account.
- BetsAPI's exact Pinnacle-product pricing is Cloudflare/login-gated and unverifiable externally, despite the reference spec living on Pinnacle's official GitHub org — the cleanest 'is this an official partnership?' question has no public answer.
- Pre-2021 Pinnacle tennis line MOVEMENT data appears to exist nowhere publicly (bettingiscool starts Jan 2021; tennis-data has closing PSW/PSL only back to ~2010); 2007-2020 Pinnacle openers/movement may be permanently inaccessible to individuals.
- No published head-to-head latency benchmark exists for the feeds an individual can actually buy (Sofascore scrape vs BetsAPI inplay vs Betfair Stream vs pinnodds) for tennis points — pinnodds self-reports 100-500ms but nothing independent verifies any of them.
- Nobody covers Canada-specific terms: whether Pinnacle.com (vs the AGCO-licensed pinnacle.ca Ontario entity) availability affects which odds feed matches the prices the bettor can actually bet, a settlement-relevant mismatch worth checking before anchoring EV to any feed.

## Verifications (adversarial)

### tennis-data.co.uk coverage — vote 1 — **confirmed**
Corrected/current fact: Confirmed as of 2026-06-10 (site banner: "Data Updated: 7th June 2026"): tennis-data.co.uk/alldata.php offers exactly one season-level results+odds Excel file per tour-year — ATP (men) 2000–2026 and WTA (women) 2007–2026 — with .xls links for 2000–2012 and .xlsx for 2013–2026 (both tours), and zero .csv or .zip links anywhere on alldata.php. Men's results start 3 January 2000 (the 2000 file is labeled "Match results" only); head-to-head betting odds columns (Centrebet, Gamebookers, Interwetten, Sportingbet) begin with the 2001 files; WTA results+odds begin 2007 (no 2006w data exists). Both 2026 files are live mid-season (ATP ~210KB, WTA ~200KB). Two refinements to the claim's framing: (1) the site's "CSV/Excel" wording is NOT stale — individual per-tournament CSVs remain fully linked and live on the tournament pages in the right-hand data menu (e.g., 2000/adelaide.csv through 2026/ausopen.csv all return 200); there are simply no season-level CSVs; (2) season .zip archives still exist server-side at the legacy unlinked URL pattern (e.g., /2000/2000.zip returns 200) — only the alldata.php "(zipped)" wording is stale, since its links point to bare .xls/.xlsx. Also note the "January 2000 / 2001 / 2007" coverage sentence does not appear as prose on the current page (it is conveyed via link labels), and the site is HTTP-only (HTTPS refused) with intermittent 504/"temporarily unavailable" errors.

Evidence: Fetched primary sources directly via curl on 2026-06-10/11 UTC (site is HTTP-only; HTTPS connection refused; several transient 504s required retries). (1) http://www.tennis-data.co.uk/alldata.php — extracted all hrefs from raw HTML: ATP links 2000/2000.xls…2012/2012.xls then 2013/2013.xlsx…2026/2026.xlsx; WTA links 2007w/2007.xls…2012w/2012.xls then 2013w/2013.xlsx…2026w/2026.xlsx; case-insensitive grep found 0 ".csv" and 0 ".zip" occurrences in the page HTML; year labels read "2000 (Match results)" vs "2001 (Match results and betting odds)" onward; page text: "A complete Excel file (zipped) for each ATP season is available. Individual CSV files for each competetion are available through the links in the data menu to the right." (2) http://www.tennis-data.co.uk/ homepage — "historical computer-ready (CSV and Excel format) results and fixed odds betting data". (3) http://www.tennis-data.co.uk/2000/adelaide.csv — first match dated 03/01/00, header has NO odds columns; http://www.tennis-data.co.uk/2001/adelaide.csv — header adds CBW,CBL,GBW,GBL,IWW,IWL,SBW,SBL. (4) http://www.tennis-data.co.uk/notes.txt — odds-column key (B365/PS/Max/Avg etc.), "All data is in csv format". (5) Existence checks: 2026/2026.xlsx → 200 (209,730 B); 2026w/2026.xlsx → 200 (199,774 B); 2007w/2007.xls → 200 (970,752 B); 2006w/2006.xls(x) → 301 (nonexistent); 2012/2012.xls, 2013/2013.xlsx, 2012w/2012.xls, 2013w/2013.xlsx → all 200. (6) CSV-still-available proof: http://www.tennis-data.co.uk/ausopen.php links through 2026/ausopen.csv and 2026w/ausopen.csv; direct GET 2026/ausopen.csv → 200 (23,424 B); http://www.tennis-data.co.uk/wimbledon.php links 2000–2025(+w) CSVs. (7) Unlinked zip proof: http://www.tennis-data.co.uk/2000/2000.zip → 200 (175,612 B); /2000/2000.csv → "Multiple Choices" error listing only 2000.xls and 2000.zip (no season CSV).

### tennis-data.co.uk odds definition — vote 1 — **confirmed**
Corrected/current fact: The claim is accurate as a description of notes.txt. Verified verbatim from the live primary source (2026-06-10): "Betting odds for matches generally represent the most recent before play starts, as reported by oddsportal.com and the individual bookmakers" — i.e., near-closing prices, not opening lines (note the hedge "generally"; it is not a guaranteed strict closing line). Documented columns match exactly: B365 (Bet365), B&W (Bet&Win), CB (Centrebet), EX (Expekt), LB (Ladbrokes), GB (Gamebookers), IW (Interwetten), PS (written "Pinnacles Sports" in the file, i.e., Pinnacle Sports), SB (Sportingbet), SJ (Stan James), UB (Unibet), plus MaxW/MaxL and AvgW/AvgL "as shown by Oddsportal.com". IMPORTANT REFINEMENT for practical use: notes.txt is stale relative to the current data files. The 2026 ATP and WTA files contain only B365W/L, PSW/L, MaxW/L, AvgW/L, plus an UNDOCUMENTED BFEW/BFEL pair (Betfair Exchange); the other 9 documented bookmakers (B&W, CB, EX, LB, GB, IW, SB, SJ, UB) appear only in older historical years. Also, notes.txt says "csv format" but current downloads are .xlsx.

Evidence: (1) Fetched http://www.tennis-data.co.uk/notes.txt directly via curl (site is HTTP-only; WebFetch's HTTPS upgrade gets ECONNREFUSED) and confirmed the exact odds-timing sentence as the file's final line, plus the full "Key to match betting odds data" block listing B365W/L=Bet365, B&WW/L=Bet&Win, CBW/L=Centrebet, EXW/L=Expekt, LBW/L=Ladbrokes, GBW/L=Gamebookers, IWW/L=Interwetten, PSW/L="Pinnacles Sports", SBW/L=Sportingbet, SJW/L=Stan James, UBW/L=Unibet, and MaxW/MaxL/AvgW/AvgL "(as shown by Oddsportal.com)". (2) Cross-checked via web search snippet of the same URL (identical sentence). (3) Adversarial currency check: listed file links on http://www.tennis-data.co.uk/alldata.php, then parsed the header rows of the current files http://www.tennis-data.co.uk/2026/2026.xlsx (ATP) and http://www.tennis-data.co.uk/2026w/2026.xlsx (WTA) in-memory (stdlib zip+XML; no files written). Both headers end: ...,B365W,B365L,PSW,PSL,MaxW,MaxL,AvgW,AvgL,BFEW,BFEL — confirming only Bet365 + Pinnacle + Oddsportal Max/Avg survive in current files and that BFEW/BFEL (Betfair Exchange) is present but undocumented in notes.txt.

### tennis-data.co.uk Pinnacle gap (PSW/PSL blanks) — vote 1 — **confirmed**
Corrected/current fact: Confirmed by independent direct parse of tennis-data.co.uk on 2026-06-10 (files current through 2026-06-07 per the site's "Data Updated" banner): Pinnacle columns PSW/PSL are 0.44% blank in ATP 2024 (2691/2703 filled), 4.16% blank in ATP 2025 (2534/2644 filled; Oct 2025 = 228/291, Nov 2025 = 65/72, exactly as claimed), and 94.52% blank in ATP 2026 (71/1296 filled: Jan 71/238, then ZERO from Feb onward — 0/293 Feb, 0/223 Mar, 0/259 Apr, 0/272 May, 0/11 Jun). WTA 2026: 101/1248 filled (91.9% blank; all 101 in January, zero from Feb onward). PSW/PSL column headers still exist but are empty; B365W/L are 99.6-99.8% filled and MaxW/L / AvgW/L are 100% filled in both 2026 files. Two refinements: (1) mild PSW decay in ATP 2025 actually begins around July 2025 (Jul 337/350, Aug 273/283, Sep 122/127, i.e. 3.5-3.9% blank) before the sharp October break, so "degradation starts Oct 2025" slightly understates the onset; (2) the claim omits that 2025/2026 files added BFEW/BFEL (Betfair Exchange) columns that remain well populated (ATP 2026: 1198/1296 = 92.4%; WTA 2026: 1136/1248 = 91.0%) — the practical sharp-market substitute for the dead Pinnacle columns. The site posts no announcement explaining the Pinnacle gap; notes.txt still officially documents PSW/PSL as "Pinnacles Sports odds of match winner/loser".

Evidence: Primary-source verification, all fetched and parsed live on 2026-06-10 (xlsx parsed in-memory via stdlib zipfile+XML, blanks counted as absent/empty cells, months from the Excel Date column): (1) http://www.tennis-data.co.uk/2024/2024.xlsx — 2703 rows, PSW/PSL 2691 filled (0.44% blank): matches claim exactly. (2) http://www.tennis-data.co.uk/2025/2025.xlsx — 2644 rows, PSW/PSL 2534 filled (4.16% blank); monthly PSW: Dec24 27/28, Jan 233/235, Feb 285/289, Mar 205/206, Apr 276/278, May 272/272, Jun 211/213, Jul 337/350, Aug 273/283, Sep 122/127, Oct 228/291, Nov 65/72 — claimed Oct/Nov figures exact. (3) http://www.tennis-data.co.uk/2026/2026.xlsx (the claimed source) — 1296 rows spanning 2026-01-04 to 2026-06-07; PSW/PSL 71/1296 filled (94.52% blank); monthly: Jan 71/238, Feb 0/293, Mar 0/223, Apr 0/259, May 0/272, Jun 0/11 — every claimed figure exact; PSW/PSL headers present; B365W/L 1293/1296, MaxW/L and AvgW/L 1296/1296; BFEW/BFEL 1198/1296. (4) http://www.tennis-data.co.uk/2026w/2026.xlsx — 1248 rows; PSW 101/1248 filled, all in January (Jan 101/265, Feb-Jun all 0); B365 1244/1248, Max/Avg 1247/1248; BFEW/BFEL 1136/1248. (5) Official column documentation http://www.tennis-data.co.uk/notes.txt — "PSW = Pinnacles Sports odds of match winner; PSL = Pinnacles Sports odds of match loser; B365 = Bet365; Max/Avg = as shown by Oddsportal.com" — confirms the claim's column interpretation. (6) http://www.tennis-data.co.uk/index.php homepage — "Data Updated: 7th June 2026", no announcement about Pinnacle removal (consistent with only 11 June matches in the file as of today). (7) Web search ("tennis-data.co.uk Pinnacle odds PSW PSL missing 2026") surfaced no third-party reports or site notices explaining the gap — no contradicting source found. Notes: CSV variants do not exist (HTTP 300 on /2026/2026.csv), so xlsx is the only format; the site is HTTP-only (HTTPS connection refused). Verification was read-only: no files written, no git commands run.

### tennis-data.co.uk Pinnacle gap cause — vote 1 — **refuted**
Corrected/current fact: tennis-data.co.uk indeed publishes no explanation for the PSW/PSL blanks (notes.txt and homepage are silent), and its notes.txt confirms odds are sourced "as reported by oddsportal.com and the individual bookmakers." Pinnacle did close its public API to the general public on July 23, 2025 (confirmed by Pinnacle's official API docs). HOWEVER, the claimed timing match is false: tennis-data's own files show PSW/PSL ~95-97% populated through Aug-Sep 2025 (ATP July 2025: only 13/350 blank), degrading in Oct 2025 (~22-29% blank), with last populated values Jan 13-14, 2026 and 100% blank from Feb 2026 onward (both ATP and WTA). The actual proximate cause is that OddsPortal delisted Pinnacle in January 2026 — Wayback captures of oddsportal.com/bookmakers/ show Pinnacle present on 2025-11-16 and 2026-01-01 but absent on 2026-02-01 and 2026-05-05 — exactly bracketing the column cutoff. Whether OddsPortal's delisting was itself a delayed consequence of Pinnacle's data-access restrictions is unproven. The WinnerOdds example is also backwards: its "we stop monitoring Pinnacle" post was published 2024-09-11 (modified 2025-05-06), ~10 months BEFORE the API closure, citing strategic reasons (information leakage to Pinnacle, low profitability) — not the API shutdown, so "subsequently" is wrong; WinnerOdds is also a value-bet alert service unrelated to tennis-data's pipeline. The "inference, not official statement" framing remains correct — tennis-data has issued no statement.

Evidence: (1) http://www.tennis-data.co.uk/notes.txt (fetched live via curl): defines "PSW = Pinnacles Sports odds of match winner / PSL = ... loser"; states "Betting odds for matches generally represent the most recent before play starts, as reported by oddsportal.com and the individual bookmakers" and MaxW/AvgW "as shown by Oddsportal.com"; contains NO explanation for blanks — confirms sourcing + no-explanation sub-claims. (2) http://www.tennis-data.co.uk/ homepage (73KB real fetch): zero mentions of Pinnacle/PSW/discontinuation. (3) Empirical check of tennis-data's own files (http://www.tennis-data.co.uk/2025/2025.xlsx, /2026/2026.xlsx, /2025w/2025.xlsx, /2026w/2026.xlsx; parsed in-memory, requires Referer header): ATP 2025 monthly PSW blanks: Jul 13/350, Aug 10/283, Sep 5/127, Oct 63/291, Nov 7/72, last populated 2025-11-16; ATP 2026: Jan 167/238 blank, last populated 2026-01-13, Feb-Jun 100% blank; WTA mirrors (last populated 2026-01-14). B365W and AvgW columns continue normally — only Pinnacle cut off. REFUTES "timing matches July 23, 2025". (4) https://raw.githubusercontent.com/pinnacleapi/pinnacleapi-documentation/master/README.md (Pinnacle's official API docs repo): "Access to Pinnacle API suite has been closed for the general public since July 23rd, 2025" + api@pinnacle.com for access — confirms the API-closure date itself. Corroborated by https://arbusers.com/access-to-pinnacle-api-closed-since-july-23rd-2025-t10682/ and https://odds-api.io/blog/pinnacle-api-shutdown-alternatives. (5) https://winnerodds.com/we-stop-monitoring-pinnacle/ (claimed source, checked directly): page exists; HTML meta article:published_time = 2024-09-11T15:37:53+00:00, modified 2025-05-06T16:50:42+00:00; reasons given are strategic ("every bet we place there gives away valuable information", "low usability... few users can place bets above our Minimum Profitable Odds"), no API mention — refutes "subsequently dropped after API closure". (6) Wayback captures of https://www.oddsportal.com/bookmakers/ (via web.archive.org/web/TIMESTAMP/...): 20251116162129 → 6 "Pinnacle" mentions; 20260101150645 → 7; 20260201203843 → 0 (233KB page, bet365 x11 still present); 20260505065327 → 0 (393KB) — Pinnacle delisted from OddsPortal between Jan 1 and Feb 1, 2026, matching the PSW cutoff. Live https://www.oddsportal.com/bookmakers/ today: 0 Pinnacle mentions (geo-caveat: OddsPortal shows region-available bookies, so live check alone is weak; archived before/after pair from same crawler vantage is the stronger evidence).

### tennis-data.co.uk Betfair replacement — vote 1 — **confirmed**
Corrected/current fact: Confirmed by direct parse of the primary files (2026-06-10): tennis-data.co.uk introduced BFEW/BFEL columns in the 2025 files (absent in 2024.xlsx); in ATP 2025.xlsx they are filled for 651/2644 rows = 24.62%, first populated for matches on 2025-08-17 (late season); in ATP 2026.xlsx (current to the site's "Data Updated: 7th June 2026") they are filled for 1198/1296 rows = 92.44%. The "replacing Pinnacle" framing also holds de facto: PSW/PSL fill collapsed from 99.56% (2024) and 95.84% (2025) to 5.48% (71/1296) in ATP 2026 (WTA 2026: BFE 91.03%, PS 8.09%), leaving Betfair Exchange as the only high-coverage sharp price in 2026 files. Refinements: (1) tennis-data's own notes.txt is stale and does not document BFEW/BFEL — the "Betfair Exchange" meaning is confirmed via the same publisher's football-data.co.uk notes.txt ("BFEH/BFED/BFEA = Betfair Exchange ... odds" naming convention); (2) PSW/PSL columns still exist in the 2026 header, just ~5% filled — replaced in practice, not removed; (3) the 92.44% is a mid-season snapshot and will drift as the 2026 file grows; for closing-line benchmarking note that exchange prices embed commission, unlike Pinnacle's vigged book prices.

Evidence: All checks against primary sources, parsed in-memory over plain HTTP (the site refuses HTTPS on port 443, so its URLs are http-only). (1) http://www.tennis-data.co.uk/2025/2025.xlsx — header includes BFEW/BFEL; filled 651/2644 = 24.62%; first filled date 2025-08-17, last 2025-11-16; PSW/PSL filled 95.84%. (2) http://www.tennis-data.co.uk/2026/2026.xlsx — 1296 data rows spanning 2026-01-04 to 2026-06-07; BFEW/BFEL filled 1198/1296 = 92.44% (98 missing rows scattered 2026-02-17 to 2026-05-03); PSW/PSL filled only 71/1296 = 5.48%. (3) http://www.tennis-data.co.uk/2024/2024.xlsx — no BFEW/BFEL columns (confirms 2025 introduction); PSW/PSL 99.56% filled. (4) WTA mirrors: http://www.tennis-data.co.uk/2025w/2025.xlsx (BFE 25.47%, first filled 2025-08-17) and http://www.tennis-data.co.uk/2026w/2026.xlsx (BFE 91.03%, PS 8.09%). (5) http://www.tennis-data.co.uk/notes.txt — documents PSW/PSL ("Pinnacles Sports odds") but contains NO entry for BFEW/BFEL/Betfair Exchange (docs stale). (6) https://www.football-data.co.uk/notes.txt — same publisher's official definition of the BFE prefix: "BFEH = Betfair Exchange home win odds" etc., supporting the BFEW/BFEL = Betfair Exchange winner/loser reading. (7) http://www.tennis-data.co.uk/ and /alldata.php — banner "Data Updated: 7th June 2026", dating the 92.44% snapshot.

### Pinnacle public API shutdown — vote 1 — **confirmed**
Corrected/current fact: Confirmed and current as of June 2026. Pinnacle's official API documentation (README of github.com/pinnacleapi/pinnacleapi-documentation, a Pinnacle-run repo last updated 2026-03-31) states verbatim: "Access to Pinnacle API suite has been closed for the general public since July 23rd, 2025. We offer bespoke data services for select high value bettors & commercial partnerships. We also support academics and pregame handicapping projects. To apply for access please write a short description of your use case to api@pinnacle.com. Our team will get back to you with options." The same README's Authentication section states: "Please note that in order to access Pinnacle API, you must have a funded account." Two refinements: (1) July 23rd, 2025 is when Pinnacle posted the formal public-closure notice (added in commit 32d38c246c on that exact date); access was already approval-gated before then — from at least June 2022 the README required contacting Pinnacle Solution for approval, so the API was not openly available right up to mid-2025. (2) The same update added strict limits relevant to any project that does get access: odds endpoints are rate-limited to 1 request per 2 minutes per endpoint per sport, and access is capped at 2 distinct IP addresses per client.

Evidence: Checked the primary source directly, not via the claimed link alone: (1) Raw README text fetched verbatim — https://raw.githubusercontent.com/pinnacleapi/pinnacleapi-documentation/master/README.md — contains the quoted closure notice word-for-word, the api@pinnacle.com application instruction, and the funded-account requirement ("you must have a funded account") in the Authentication section. (2) Full commit history of README.md via GitHub API — https://api.github.com/repos/pinnacleapi/pinnacleapi-documentation/commits?path=README.md — shows the notice was introduced by Pinnacle in commit https://github.com/pinnacleapi/pinnacleapi-documentation/commit/32d38c246c on 2025-07-23 (matching the stated date), replacing prior language ("you must contact Pinnacle Solution for the approval", present 2022-06-07 through 2025-07-04); latest commits 2026-03-31 retain the notice, so it is current. (3) Officialness: https://api.github.com/users/pinnacleapi shows account name "Pinnacle API", website www.pinnacle.com, created 2017; 2026 commits authored by a pinnacle.com staff email (oljeg.popovic@pinnacle.com). (4) Live repo page https://github.com/pinnacleapi/pinnacleapi-documentation shows the same notice. (5) Third-party corroboration of the closure date: https://arbusers.com/access-to-pinnacle-api-closed-since-july-23rd-2025-t10682/ and https://odds-api.io/blog/pinnacle-api-shutdown-alternatives. No newer or contradicting Pinnacle policy found in searches as of 2026-06-10.

### the-odds-api Pinnacle inclusion — vote 1 — **confirmed**
Corrected/current fact: Confirmed with one timeline refinement. As of June 10, 2026, the-odds-api.com lists Pinnacle under bookmaker key 'pinnacle' in its EU region, and Pinnacle is the ONLY bookmaker on the page carrying the exact note "Odds are from public website which may incur a delay" — no deprecation/removal marker. So Pinnacle prices are still offered (per the actively maintained official docs; the live API feed itself could not be queried without an API key), and "not tick-accurate" is a fair reading of the unquantified delay caveat. REFINEMENT: the "post-shutdown they switched from the API to scraping the public site" story has the timeline backwards. Wayback snapshots show the 'pinnacle' key existed by March 2024 with NO note, and the public-website caveat was added between Nov 8, 2024 and Feb 17, 2025 — months BEFORE Pinnacle closed its API to the general public on July 23, 2025 (per Pinnacle's official API docs repo: "Access to Pinnacle API suite has been closed for the general public since July 23rd, 2025"; bespoke access only via api@pinnacle.com). the-odds-api was already sourcing Pinnacle from the public website pre-shutdown and simply continued unchanged through Aug 2025, Feb 2026, and today. Practical upshot for the tennis project is as claimed: delayed public-site-sourced Pinnacle prices via key 'pinnacle', region 'eu' — usable as a sharp reference but not for tick-accurate CLV timing.

Evidence: (1) Primary source, fetched live 2026-06-10: https://the-odds-api.com/sports-odds-data/bookmaker-apis.html — key 'pinnacle', EU region only, exact note "Odds are from public website which may incur a delay"; only bookmaker with that note; no deprecated/beta/removal markers on the page. (2) Wayback Machine history of that same page (via CDX API + snapshot fetches): 2024-03-03, 2024-05-16, 2024-07-18, 2024-11-08 snapshots — 'pinnacle' listed under eu, delay note ABSENT (e.g. https://web.archive.org/web/20241108121720/https://the-odds-api.com/sports-odds-data/bookmaker-apis.html); 2025-02-17 and 2025-03-22 — note PRESENT (https://web.archive.org/web/20250217071359/https://the-odds-api.com/sports-odds-data/bookmaker-apis.html); 2025-06-22 (pre-shutdown), 2025-08-16 (post-shutdown), 2026-02-17 — entry unchanged with note (https://web.archive.org/web/20250622151711/... , https://web.archive.org/web/20250816131700/... , https://web.archive.org/web/20260217212052/https://the-odds-api.com/sports-odds-data/bookmaker-apis.html). Page is actively maintained (e.g., pmu_fr row added between Aug 2025 and Feb 2026), so Pinnacle's retention is a live editorial choice. (3) Shutdown date primary source: https://github.com/pinnacleapi/pinnacleapi-documentation README — "Access to Pinnacle API suite has been closed for the general public since July 23rd, 2025... bespoke data services for select high value bettors & commercial partnerships" (contact api@pinnacle.com). Corroborated by https://arbusers.com/access-to-pinnacle-api-closed-since-july-23rd-2025-t10682/ (title; page 403'd) and competitor post https://odds-api.io/blog/pinnacle-api-shutdown-alternatives (note: odds-api.io is a DIFFERENT service that dropped Pinnacle for alternatives — do not conflate with the-odds-api.com). Limitations: could not query the live the-odds-api v4 endpoint (requires API key), so "prices flowing" is verified at the official-docs level, not feed level; no official statement quantifies the delay; web searches found no 2025-2026 reports of Pinnacle data being dropped or broken on the-odds-api.

### the-odds-api plans — vote 1 — **confirmed**
Corrected/current fact: Confirmed as of June 2026: the-odds-api pricing is free Starter tier 500 credits/month, $30/mo for 20K credits, $59/mo for 100K, $119/mo for 5M, $249/mo for 15M; covers 70+ sports including tennis ("All Grand Slams and more" — ATP/WTA Australian Open, French Open, Wimbledon, US Open plus Masters events) across 40+ bookmakers in US/UK/EU/AU regions. Minor refinements: regions are broader than claimed (also fr, se, us2, plus us_dfs DFS props and us_ex exchanges); the free tier offers "most" rather than all bookmakers; higher tiers beyond 15M exist after account creation; and credits ≠ API requests — one call costs markets × regions credits, and historical-odds endpoints cost 10x.

Evidence: Checked the primary source live: https://the-odds-api.com/ (pricing section fetched twice with independent prompts) shows exactly the five claimed tiers (free 500/mo; $30 = 20K; $59 = 100K; $119 = 5M; $249 = 15M), "over 70 sports," tennis billed as "All Grand Slams and more," and "over 40 bookmakers" in US/UK/EU/AU. Cross-checked same-site detail pages: https://the-odds-api.com/sports-odds-data/sports-apis.html (tennis: ATP+WTA entries for all four Grand Slams plus Masters tournaments) and https://the-odds-api.com/sports-odds-data/bookmaker-apis.html (20 US + 20 UK + 27 EU + 12 AU + 5 FR + 13 SE books; region keys us/us2/uk/eu/au/fr/se/us_dfs/us_ex — i.e., more than 40 books and more regions than claimed). Independent corroboration: https://oddspapi.io/blog/odds-api-pricing-2026-comparison/ (dated March 12, 2026) lists the identical tier/price/credit figures and notes the credits-vs-requests and 10x-historical caveats. A web search for 2026 pricing changes surfaced no evidence of any newer price change.