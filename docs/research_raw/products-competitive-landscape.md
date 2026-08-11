# Research archive: products-competitive-landscape

*Raw structured output from the 2026-06-10 multi-agent research run. Facts below are as-reported by research agents; entries in the Verifications section were independently adversarially checked.*

## Facts

### Tennis Abstract scope (high)
Tennis Abstract (Jeff Sackmann) publishes free ATP and WTA Elo rating tables (players with 10+ tour-level matches), year-only 'yElo' tables, and Elo-based tournament/match forecasts; Sackmann explicitly tells readers NOT to use the forecasts as betting advice.

Source: https://tennisabstract.com/reports/atp_elo_ratings.html

### Tennis Abstract gaps (medium)
Tennis Abstract's forecast pages have no odds integration, no API, no calibration-vs-market reporting, and no live win-probability product for bettors; win-probability work appears as blog analyses (Heavy Topspin category pages) rather than a queryable feed.

Source: https://www.tennisabstract.com/blog/category/win-probability/

### Sackmann GitHub data license (high) **[decision-critical]**
JeffSackmann/tennis_atp (and tennis_wta) on GitHub provide rankings 1985-present and tour-level results 1968-present with match stats from 1991, include 2025/2026 CSV files, contain NO betting odds, have had doubles updates suspended since late 2020, and are licensed CC BY-NC-SA 4.0 (non-commercial use only, attribution required).

Source: https://github.com/JeffSackmann/tennis_atp

### Ultimate Tennis Statistics (high)
Ultimate Tennis Statistics (ultimatetennisstatistics.com) is a free site with a tennis-customized Elo (K-factor scaled by tournament level 70-100%, round, best-of-3 vs best-of-5; surface/indoor/set/game variants; inactivity penalty) and is open-sourced as mcekovic/tennis-crystal-ball on GitHub; it has no odds integration and no betting/EV layer.

Source: https://www.ultimatetennisstatistics.com/about

### Dimers/Stats Insider tennis (high)
Dimers (US arm of Australia's Stats Insider) publishes free simulation-based predictions (10,000 sims/match) for every ATP/WTA match including Slams, flags +EV bets against retail sportsbook odds, and gates 'every model-recommended bet' behind Dimers Pro at $24.99/month or $199.99/year (June 2026).

Source: https://www.dimers.com/best-bets/ten

### Dimers Pro pricing source (medium)
Dimers Pro is priced at $24.99/month or $199.99/year per Dimers' own subscription pages and 2026 reviews; its EV is measured against US retail books (DraftKings/FanDuel-class), not Pinnacle, and it offers no probability export/API, no calibration report, and no CLV tracking.

Source: https://www.dimers.com/subscription

### Stats Insider free tier (high)
Stats Insider (statsinsider.com.au) provides free tennis predictions for ATP/WTA tours and all four Grand Slams based on 10,000+ simulations per match, aimed at Australian recreational bettors with no quant export or odds-capture features.

Source: https://www.statsinsider.com.au/

### MatchSignal tennis SaaS exists (high)
MatchSignal.com (formerly TopTennisTips, operating since 2014) is a tennis-specific ML value-bet SaaS covering ATP, WTA, Challenger and ITF, pre-match and live; each tip carries a model probability and expected value, with filters by market/odds/min-EV and fractional-Kelly staking plus historical backtest views.

Source: https://www.matchsignal.com/

### MatchSignal pricing (high) **[decision-critical]**
MatchSignal's tennis match-winner plans cost €799/month (Core), €1,199/month (Pro), €1,949/month (Expert) and €2,749/month (Ultimate) as of June 2026, with claimed monthly profits of +48 to +191 units shown on the pricing page (self-reported, unaudited) and no trial or annual plans listed; the reference bookmaker for its EV is not specified on the pricing page.

Source: https://www.matchsignal.com/pricing/

### OnCourt price (high) **[decision-critical]**
OnCourt (oncourt.info) costs 48.95 EUR for a 1-year Windows license, 88.95 EUR lifetime, 24 EUR/year renewal (Windows+Android or Windows+iOS bundles 64.95 EUR/year), and accepts credit cards, PayPal, and USDT cryptocurrency (Tron wallet) — crypto payment matches this bettor's funding rails.

Source: https://www.oncourt.info/order.html

### OnCourt data depth (high) **[decision-critical]**
OnCourt contains 1.6M+ matches: ATP from 1990, WTA from 1997, Challengers from 1998, qualifying from 2000, Futures/ITF from 2002-2004, juniors from 2003, with Grand Slam match statistics, post-match point-by-point replay for most matches, and daily online database updates.

Source: https://www.oncourt.info/

### OnCourt odds and DB access (high) **[decision-critical]**
OnCourt includes Pinnacle bookmaker odds with odds-movement history for both upcoming and past matches (no other books mentioned), Excel export, and gives licensed users the underlying Microsoft Access database file (OnCourt.mdb) for custom development — i.e., direct programmatic access to results + Pinnacle odds without scraping.

Source: https://www.oncourt.info/

### OnCourt gaps (medium) **[decision-critical]**
OnCourt is a Windows desktop app, not an API service: odds are Pinnacle-only (no multi-book), the granularity/timestamping of its odds-movement records (true opening line vs sampled snapshots) is not documented publicly, and automation requires reading the .mdb yourself.

Source: https://www.oncourt.info/

### OddsJam pricing (medium)
OddsJam's full package costs about $199/month in 2026 (positive-EV-only plans cited around $99/month, entry tiers from ~$39/month per reviews); it covers 100+ sportsbooks with US/Canada focus.

Source: https://xclsvmedia.com/oddsjam-review-2026-is-this-199-month-betting-tool-worth-it/

### OddsJam workflow direction (high) **[decision-critical]**
OddsJam's +EV tool computes a no-vig fair price from sharp books (Pinnacle, Circa, Bookmaker) or market consensus and then flags RETAIL books (DraftKings, BetMGM, etc.) whose odds beat that fair price — i.e., Pinnacle is the benchmark you compare against, not the book you are directed to bet at, which is the inverse of a market-maker-only workflow.

Source: https://oddsjam.com/betting-tools/positive-ev

### RebelBetting pricing (high)
RebelBetting (value betting + sure betting combined) costs €99/month Starter (€69/month billed annually) and €199/month Pro (€139/month annually); Pro adds sharp bookmakers, brokers and exchanges to the 100+ covered books; a 14-day free trial exists and a BetTracker with automatic settlement is included in all tiers.

Source: https://www.rebelbetting.com/pricing

### RebelBetting value AT Pinnacle is rare (high) **[decision-critical]**
RebelBetting's own community forum says finding value bets AT Pinnacle is 'super rare', that Pinnacle functions as the sharp reference, that any value found there averages only ~1% margin, and that value bets should be placed at soft books like Bet365/Unibet/Bwin — confirming the product cannot drive a Pinnacle-only betting workflow.

Source: https://community.rebelbetting.com/t/value-bets-on-pinnacle/2189

### RebelBetting CLV tracking (medium)
RebelBetting's BetTracker stores Closing Line Value for all placed value bets (shown in BetTracker and Reports), with EV computed against sharp-line references (mainly Pinnacle/Betfair/market average) — one of the few consumer tools that grades bets against a sharp closing line, though only for bets sourced through its own scanner.

Source: https://www.rebelbetting.com/valuebetting/closing-line

### BetBurger pricing (high)
BetBurger Valuebets costs €79.99/30 days prematch, €279.99/30 days live, €319.99/30 days for the prematch+live bundle (per-day rates fall with longer subscriptions, e.g. €1.94-€5.99/day), with a free tier limited to valuebets up to 2% overvalue.

Source: https://www.betburger.com/gb/prices-valuebets

### BetBurger reference lines (medium) **[decision-critical]**
BetBurger's Valuebets V2 lets users pick the reference line that defines 'value': average market line (Avgline), Pinnacle no-vig, or Betfair no-vig — a configurable fair-value anchor closer to a quant workflow, but the bettable output is still overwhelmingly soft-book odds.

Source: https://www.betburger.com/news/meet-valuebets-v2

### BetBurger Pinnacle valuebet scarcity (medium) **[decision-critical]**
BetBurger's own bookmaker list shows Pinnacle averaging ~711 available surebets but only ~1 valuebet — quantitative confirmation that scanner-defined 'value' essentially never exists at Pinnacle itself, because Pinnacle is the price everything else is measured against.

Source: https://www.betburger.com/bookmakers

### Trademate Core vs Pro (high) **[decision-critical]**
Trademate Sports Core (€120/month or €300/3 months) finds value at 90+ slow-reacting SOFT bookmakers, while Trademate Pro (€400/month or €1,000/3 months) is the only mainstream productized workflow for taking value at SHARP books, Asian bookmakers and betting exchanges — books that do not limit winners.

Source: https://punter2pro.com/product/trademate-sports-core-pro-subscription/

### Trademate Pro caveats (medium) **[decision-critical]**
Trademate Pro's sharp-book edges are described by reviewers as much harder and thinner than soft-book value ('sharp bookmakers rarely make mistakes... efficient markets'), Trademate claims ~3.5% average ROI on turnover for its value betting generally, its pricing page did not surface tennis-specific coverage documentation, and the 'value' is defined by Trademate's own fair-odds model rather than the user's model.

Source: https://smartsportstrader.com/trademate-sports-review/

### Pinnacle Odds Dropper (medium) **[decision-critical]**
Pinnacle Odds Dropper (pinnacleoddsdropper.com) monitors Pinnacle 24/7 and alerts on odds drops and limit changes, with plans at $39 (Bronze), $75 (Silver), $99 (Gold) per month, line-history sheets and CLV metrics, and a 21-day money-back guarantee instead of a trial — a Pinnacle-native signal feed (steam/limit moves) rather than a value scanner, usable inside a market-maker-only workflow.

Source: https://www.pinnacleoddsdropper.com/

### Pikkit tracker (high) **[decision-critical]**
Pikkit is a free bet tracker whose Pro tier ($39.99/month or $299.99/year) auto-computes CLV on every synced bet, but its BookSync auto-sync covers 30+ US-regulated books (DraftKings, FanDuel, BetMGM, Caesars, ESPN BET, bet365, etc.) — it does NOT sync Pinnacle or crypto books, so a Pinnacle-only bettor gets no automatic capture and CLV referenced to US retail closing lines.

Source: https://pikkit.com/resources/sportsbooks

### Betstamp tracker (Canadian) (medium) **[decision-critical]**
Betstamp (Canadian company) offers free bet tracking with CLV computed for every main-market tracked bet against both the book where the bet was tracked and the best closing book, covers 50+ sportsbooks and prediction markets including Pinnacle in its odds comparison, and supports ATP/WTA odds — the most Pinnacle/Canada-compatible tracker found, though tennis bets must be entered manually (no Pinnacle account sync).

Source: https://www.betstamp.com/tracking

### Pinnacle legal in Canada/Ontario (medium) **[decision-critical]**
Pinnacle operates legally in Canada, including an Ontario-licensed entity (pinnacle.ca via iGaming Ontario/AGCO) alongside pinnacle.com for other provinces, so the user's Pinnacle-class anchor book is durably available in his jurisdiction as of 2025-2026.

Source: https://www.pinnacleoddsdropper.com/blog/is-pinnacle-legal-in-canada

### Betfair blocked in Canada (high) **[decision-critical]**
Betfair Exchange does not accept Canadian residents (Canada is on Betfair's blocked/restricted list as of 2025-2026), which makes the entire Betfair tennis-trading bot ecosystem (Bf Bot Manager, Gruss, Bet Angel, flumine bots) unusable for this bettor without relocation or ToS-violating workarounds.

Source: https://thebetmatrix.win/betting-exchanges/betfair-countries-accepted/

### Bf Bot Manager (medium)
Bf Bot Manager, an official API solution for Betfair/Betdaq/Matchbook since 2009, costs from £29.95/month to £149.95/year, supports rule-based tennis strategies, recently added free tennis live-score statistics enabling serve-based in-play trading automation, and offers a free trial.

Source: https://www.bfbotmanager.com/en

### Gruss Betting Assistant (high)
Gruss Betfair Betting Assistant costs £6/month or £60/year (£9/month / £100/year with Market Replay) with a 30-day free trial — cheap Excel-driven Betfair automation, but irrelevant to a Canadian who cannot access Betfair.

Source: https://www.gruss-software.co.uk/pricing

### flumine framework (high)
flumine is the standard open-source Python event-based trading framework for Betfair (betcode-org), actively maintained (release as recent as Feb 2025, tested on Python 3.9-3.14), with the betfair-down-under 'AwesomeBetfair' curated list and BowTiedBettor's BetfairBot as reference implementations — all exchange-dependent and therefore Canada-blocked for this user.

Source: https://betcode-org.github.io/flumine/

### Tennis trading edge claims credibility (medium)
Betfair tennis-trading communities and educators (Tennis Profits community, Caan Berry guides, Bet Angel academy, thetrader.bet strategy lists) claim repeatable in-play edges (e.g., 'laying at low odds', serve-hold momentum trades) but publish no independently audited long-term records; reviewers note the educational content is real while profitability verification is absent — treat edge claims as low-credibility marketing.

Source: https://www.honestbettingreviews.com/tennis-profits/

### GitHub: ATPBetting (most-starred) (high)
edouardthom/ATPBetting (~454 stars, 189 forks) is the most-visible open-source tennis betting repo — 'Beating the bookmakers on tennis matches' with a confidence-based stake-selection strategy on tennis-data.co.uk odds — but it is abandoned (last substantive activity ~2019), ATP-only, has open issues about broken data paths, and predates 2020s market conditions.

Source: https://github.com/edouardthom/ATPBetting

### GitHub: taralloc/tennis-prediction honesty (high)
taralloc/tennis-prediction reimplements the 'Machine Learning for the Prediction of Professional Tennis Matches' paper with Kelly staking and honestly reports NEGATIVE profit when backtested since 2004, despite the original paper's claimed positive ROI — a rare walk-forward-honest data point showing published academic tennis edges often fail out-of-sample.

Source: https://github.com/taralloc/tennis-prediction

### GitHub: Tennis-Betting-ML weaknesses (high)
BrandoPolistirolo/Tennis-Betting-ML (51 stars) uses logistic regression on ~125k ATP matches with a random 70/30 split (no walk-forward), reports 66% accuracy and ROC-AUC ~0.72 but NO ROI, excludes WTA, and does not address retirements — typical of the methodological weaknesses across public tennis repos.

Source: https://github.com/BrandoPolistirolo/Tennis-Betting-ML

### GitHub: other notable repos (medium)
Other public tennis-betting repos are small and dated: jgollub1/tennis_match_prediction (point-level serve/win-probability research, no betting product), Matyyas/Tennis-Prediction (ML betting strategy demo), 0xsimulacra/MLT (ATP+WTA with odds data), rajdua22/tennis_betting (neural net 2003-2017 with fractional Kelly simulated 2013-2017); GitHub's 'tennis-betting' topic page surfaces only 2 minor repos in 2026 — no maintained production-grade open-source tennis betting stack exists.

Source: https://github.com/topics/tennis-betting

### Academic SOTA 2025 (GNN) (high) **[decision-critical]**
An October 2025 arXiv paper (2510.20454) models intransitive player dominance with temporal directed-graph neural networks, reports 65.7% accuracy, 0.215 Brier score and +3.26% ROI with Kelly staking over 1,903 bets specifically against Pinnacle odds (finding Pinnacle 'poorly handles matches with high intransitive complexity'), using ATP+WTA data 2014-June 2025 with a chronological validation (2019-2022) / out-of-sample test (2023-2025) split — the most credible recent public evidence that a beatable Pinnacle tennis edge exists; code release unconfirmed.

Source: https://arxiv.org/abs/2510.20454

### tennis-data.co.uk free Pinnacle odds (medium) **[decision-critical]**
tennis-data.co.uk provides free downloadable historical ATP/WTA results CSVs with bookmaker odds columns including PSW/PSL (Pinnacle match-winner odds, available since ~2010) plus Bet365/max/average columns — the de-facto free backtest odds source most public repos use; it provides closing-style snapshot odds only, with no documented opening-line columns for tennis.

Source: http://www.tennis-data.co.uk/data.php

### Tipstrr acquired Pyckio (medium)
Tipstrr acquired Pyckio in late 2024 and migrated all Pyckio tipsters to Tipstrr — Pyckio had been the main platform proofing tipsters against Pinnacle prices, so Pinnacle-benchmarked tipster verification now lives under Tipstrr.

Source: https://mikecruickshank.com/pyckio-tipsters-review/

### Tipstrr pricing/verification (medium)
Tipstrr is free to join with automated odds-at-post-time proofing (tips cannot be edited/deleted); individual tipster subscriptions typically run £10-£25/month (premium up to £50/month), many offer £1 trials, and Tipstrr Pro bundles several premium tipsters for £39/month.

Source: https://punter2pro.com/tipstrr-review-find-follow-tipsters-portfolio/

### Verified tennis tipsters at Pinnacle prices (medium)
Verified tennis tipster records at Pinnacle prices do exist but are scarce: 'Aidan' (Pyckio/SBC-reviewed) shows 12.7% ROI over 1,092 bets since 2019 with all bets advised at Pinnacle, and 'Nishikori' showed 8.4% yield over 3,283 ATP picks across 4 years registered at Pinnacle prices — demonstrating beatable Pinnacle tennis prices, though advised-odds decay when followers pile in is not measured.

Source: https://smartbettingclub.com/blog/our-latest-tipster-review-looks-at-a-service-with-a-12-7-roi-at-pinnacle/

### Smart Betting Club (medium)
Smart Betting Club (since 2006) independently proofs and reviews tipsters (including tennis tipsters benchmarked against Pinnacle), sells quarterly/bi-annual/annual memberships (prices raised July 2025; exact current price not captured), and offers a 90-day money-back guarantee — a meta-layer for vetting tennis tipsters rather than a model or scanner.

Source: https://smartbettingclub.com/subscribe/

### Betting Gods (medium)
Betting Gods hosts proofed tipsters across sports including tennis, with £10 trials and typical subscriptions around £29/month (entry offers from £7.99/month), claiming independent real-time verification of every tip at the odds available at release; it does not benchmark against Pinnacle closing specifically.

Source: https://punter2pro.com/betting-gods-review-tipster-proofing-website/

### Broker route to sharp books (low) **[decision-critical]**
VOdds is a bet-broker/aggregator (not a bookmaker) that routes orders through one account to sharp books and exchanges such as Pinnacle, SBOBET, Betfair and Matchbook — a possible execution layer for a market-maker-only workflow, though Canadian acceptance and crypto funding terms were not verified in this research pass.

Source: https://plisio.net/education/crypto-bookmakers-vodds

### OnCourt vs competitors uniqueness (medium) **[decision-critical]**
Among all products surveyed, OnCourt is the only sub-€50/year product combining a full historical match database (incl. Challengers/ITF), Grand Slam stats, point-by-point replays, AND Pinnacle odds with movement history in a locally queryable database file — the closest off-the-shelf analogue to the flat-file + odds foundation of the user's UFC pipeline.

Source: https://www.oncourt.info/

## Gaps noticed by the research agent
- No commercial product serves a 'find value AT Pinnacle-class books' workflow except Trademate Pro (€400/month) — and even that grades value by Trademate's own fair-odds model, not the user's model; every other scanner (OddsJam, RebelBetting, BetBurger) structurally defines value as soft-book deviation FROM Pinnacle, so Pinnacle itself shows ~1 valuebet on average (BetBurger's own stat) and the products are useless to a bettor who can only bet at market makers.
- No bet tracker auto-syncs Pinnacle (or any crypto book) bets: Pikkit's BookSync is US-retail-only, Betstamp tracking of Pinnacle bets is manual, RebelBetting's CLV tracker only covers bets sourced from its own scanner — a solo quant must build his own Pinnacle bet log + CLV capture, exactly as he already does for UFC.
- Opening-line capture is unproductized for tennis: tennis-data.co.uk gives free Pinnacle closing-style odds but no opening columns; OnCourt has Pinnacle 'odds movement' of undocumented granularity/exportability; Pinnacle Odds Dropper holds line history but as an alert UI, not bulk export. Nobody sells timestamped Pinnacle open→close pairs for ATP/WTA that a quant can join to model probabilities for leak-free training and CLV-vs-open analysis.
- Open-source tennis betting repos are uniformly stale (mostly 2017-2020), ATP-biased (WTA second-class or absent), validated with random splits instead of walk-forward, report accuracy instead of calibration/ROI, ignore retirement handling and settlement rules entirely, and never distinguish opening vs closing odds in training — the methodological bar (odds-aware features, temporal validity, calibration, fractional Kelly, CLV) that the user's UFC pipeline already clears is unmet publicly, so porting his stack IS the edge.
- Retirement/walkover handling is a blind spot across the entire landscape: no stats site, SaaS, scanner, or public repo documents how mid-match retirements are treated in training labels or how different books' void rules affect EV — material in tennis where retirements are frequent (and where book-specific settlement rules change effective payout distributions).
- The Betfair in-play trading ecosystem — the largest body of tennis 'edge' tooling and community knowledge — is entirely inaccessible from Canada (Betfair blocks Canadian residents), and its edge claims are unaudited; this removes exchange trading, lay hedging, and in-play exit options from the user's strategy space and pushes him to pre-match/live betting at Pinnacle-class books only.
- Scanner coverage of crypto-funded books (Cloudbet, Stake, Sportsbet.io; BetOnline appears only in some lists) is thin and undocumented — even if the user wanted scanner-driven value bets, the bettable-book overlap with his crypto/market-maker book set is near zero.
- Tennis-specific prediction SaaS with EV output exists (MatchSignal: ATP/WTA/Challenger/ITF, probabilities + EV + Kelly) but at €799-€2,749/month with self-reported unaudited profit claims — priced for syndicates, not solo quants, and it sells picks rather than data/probabilities a quant can validate or blend.
- Free model sites (Tennis Abstract, UTS, Dimers/Stats Insider) publish win probabilities but none expose calibration diagnostics, an API, or odds-joined histories; Sackmann's canonical free data is CC BY-NC (non-commercial) with no odds and lagging/irregular updates — anyone building a betting product must assemble results+odds independently (OnCourt's .mdb plus tennis-data.co.uk are the cheapest viable spine).
- Tipster verification platforms benchmark at advised or post-time odds, rarely at Pinnacle closing, and never publish follower-attainable CLV; the handful of Pinnacle-proofed tennis records (12.7% ROI/1,092 bets; 8.4% yield/3,283 picks) suggest Pinnacle tennis is beatable but offer no reproducible signal a quant can integrate.
- Nobody offers Pinnacle limit-change/steam data as a clean historical dataset (Pinnacle Odds Dropper alerts on it live but doesn't sell history) — yet limit moves at a market maker are exactly the 'market momentum' signal class the user already studied for UFC; DIY archiving of Pinnacle tennis lines+limits from day one would build a proprietary asset no competitor sells.

## Verifications (adversarial)

### Sackmann GitHub data license — vote 1 — **confirmed**
Corrected/current fact: As of 2026-06-10, JeffSackmann/tennis_atp and JeffSackmann/tennis_wta on GitHub are actively maintained (both last pushed 2026-06-08) and provide: tour-level match results for every year 1968 through 2026, including atp_matches_2025.csv, atp_matches_2026.csv, wta_matches_2025.csv and wta_matches_2026.csv; ATP rankings "mostly complete from 1985 to the present" (with intermittent extra coverage back to 1973 and 1982 missing) and WTA rankings beginning January 1984; NO betting odds in any file or column (49 documented columns, none odds-related); and a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International license declared in both READMEs (attribution required, non-commercial use only; no machine-readable LICENSE file, so GitHub's API license field is null). Two refinements to the original claim: (1) "match stats from 1991" holds only for ATP tour-level matches (ATP README: 1991-present tour-level, 2008-present challengers, 2011-present tour-level qualifying) — WTA match-stat columns are empty in 1991 and stay essentially empty through the 1990s, trace-level in 2003, partial 2008-2012, and only substantially populated from ~2016 onward; (2) the doubles note ("Doubles updates are temporarily suspended as of late 2020", latest file atp_matches_doubles_2020.csv) applies to the tennis_atp repo only — tennis_wta contains no doubles files at all.

Evidence: Checked primary sources directly on 2026-06-10. (1) ATP README (https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/README.md): verbatim quotes — "ATP rankings are mostly complete from 1985 to the present. 1982 is missing, and rankings from 1973-1984 are only intermittent."; "In general, that means 1991-present for tour-level matches, 2008-present for challengers, and 2011-present for tour-level qualifying."; "Doubles updates are temporarily suspended as of late 2020."; license = "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License", attribution required, non-commercial only. (2) WTA README (https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/README.md): same CC BY-NC-SA 4.0 statement; no doubles or odds mention. (3) Full git trees (https://api.github.com/repos/JeffSackmann/tennis_atp/git/trees/master and .../tennis_wta/git/trees/master, both truncated=false): match files 1968-2026 in both repos; atp_matches_2025.csv (617 KB) and atp_matches_2026.csv (300 KB) exist; wta_matches_2025.csv and wta_matches_2026.csv exist; no filename contains "odds"; latest ATP doubles file is atp_matches_doubles_2020.csv; WTA tree has zero doubles files; ATP ranking files span atp_rankings_70s.csv-atp_rankings_current.csv, WTA span wta_rankings_80s.csv-wta_rankings_current.csv. (4) Data dictionary (https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/matches_data_dictionary.txt): all 49 match columns listed (tourney/player IDs, score, serve stats w_ace...l_bpFaced, ranks/points) — no betting-odds, bookmaker or moneyline column. (5) Repo metadata (https://api.github.com/repos/JeffSackmann/tennis_atp and .../tennis_wta): pushed_at 2026-06-08T12:36:55Z and 2026-06-08T12:55:34Z respectively (actively updated this week); license field null (README-declared license, no LICENSE file). (6) Raw data samples via HTTP range requests: wta_rankings_80s.csv first row = 19840102 (WTA rankings start Jan 1984); wta_matches_1991.csv rows have ALL stats fields empty while atp_matches_1991.csv rows carry full stats (minutes, aces, bp etc.); counts of rows with non-empty w_ace in first 80 KB of wta_matches_YYYY.csv: 1997=0, 2003=2, 2008=41, 2012=37, 2016=388, 2020=388 — confirming WTA stats are not available from 1991 and only become substantially complete around 2016. Verdict: every load-bearing element of the claim (1968-present results, 1985-present rankings framing, 2025/2026 files present, no odds, ATP doubles suspended late 2020, CC BY-NC-SA 4.0 non-commercial license) is confirmed against the primary source today; the only sub-part needing refinement is attributing "match stats from 1991" to the WTA repo.

### MatchSignal pricing — vote 1 — **confirmed**
Corrected/current fact: As of June 2026, MatchSignal's tennis Match Winner plans on https://www.matchsignal.com/pricing/ cost 799 EUR/month (Core), 1,199 EUR/month (Pro), 1,949 EUR/month (Expert), and 2,749 EUR/month (Ultimate), with self-reported "Average profit" figures of +48.3, +92.9, +159.5, and +191.1 units/month respectively (no audit or third-party verification cited; the only disclaimer is "Results in sports betting cannot be guaranteed. Individual results will vary."). No trial, free, annual, or discount option is listed on the pricing page, and no reference bookmaker or odds basis for the EV/units is specified there. Minor refinement: actual subscription checkout is via Patreon (patreon.com/MatchSignal), where tiers are billed in USD at different sticker prices (e.g., a $671.50/month tier; tiers reportedly start around $184/month), so the EUR figures on the pricing page are display prices rather than the literal checkout amounts.

Evidence: Checked the primary source directly: fetched https://www.matchsignal.com/pricing/ live (June 10, 2026) twice — once for a structured summary and once for verbatim extraction. Verbatim results: "Tennis Match Winner - Core" "799 EUR / month" "+48.3 units / month"; "Pro" "1199 EUR / month" "+92.9 units / month"; "Expert" "1,949 EUR / month" "+159.5 units / month"; "Ultimate" "2,749 EUR / month" "+191.1 units / month". Targeted verbatim searches for "trial/free/annual/year/yearly/discount" and for any bookmaker name or odds-basis phrase both returned NONE FOUND on the pricing page. Only results disclaimer: "Results in sports betting cannot be guaranteed. Individual results will vary." Cross-checked the checkout channel at https://www.patreon.com/MatchSignal (USD billing, $671.50/month tier visible; web search snippet indicates tiers from ~$184/month) and confirmed via web search that matchsignal.com (formerly TopTennisTips) is the operating site with the pricing page at the claimed URL.

### OnCourt price — vote 1 — **confirmed**
Corrected/current fact: Confirmed as of 2026-06-10 against the live official order page: OnCourt for Windows costs 48.95 EUR (one-year license) or 88.95 EUR (lifetime); Windows+Android and Windows+iOS one-year bundles are each 64.95 EUR; subscription renewal is 24 EUR/year via credit card or PayPal. Payments accepted: credit cards and PayPal (secure online ordering) plus USDT to wallet TH974iEwymcQ963YzmsX7tg5WfVJ2XQXRM — a Tron-format (T-prefix) address, so the "Tron wallet" characterization is correct, though the page does not explicitly name the network. Minor refinement: renewal paid by USDT instead of card/PayPal costs 28 USDT (email info@oncourt.info with the user name). Also unstated in the claim but on the page: OnCourt+AllSnooker.Info bundles at 68.95 EUR/year and 124.95 EUR lifetime.

Evidence: Checked the primary source directly two independent ways on 2026-06-10: (1) fetched https://www.oncourt.info/order.html via web fetch tool — returned all claimed prices and payment methods; (2) pulled the raw HTML of the same URL via curl and grepped it — exact strings present: "OnCourt for Windows (One-Year License) ... 48.95 EUR", "(Lifetime License) ... 88.95 EUR", "OnCourt for Windows + OnCourt for Android (One-Year License) ... 64.95 EUR", same 64.95 EUR for the iOS bundle, "Renew of a subscription costs 24 EUR one year", "Credit Cards or PayPal via Secure Online Ordering", "transfer 28 USDT and inform on info@oncourt.info", and "USDT ... Our wallet: TH974iEwymcQ963YzmsX7tg5WfVJ2XQXRM" (T-prefix base58 = Tron/TRC-20 address format; the word "Tron" itself does not appear on the page). Order links route to the official processor at oncourt.org/cgi-bin/order.cgi. Cross-checked via web search ("OnCourt oncourt.info price license EUR tennis software 2026") — oncourt.info confirmed as the official KAN-soft site (https://www.oncourt.info/); no source contradicted the current prices. The claim is current, not outdated.

### OnCourt data depth — vote 1 — **confirmed**
Corrected/current fact: OnCourt (oncourt.info) currently contains ~2.02 million matches (live database counter on 2026-06-10: 2,023,382 total, database version 107021), so the claim's "1.6M+" is true but understated — 1.6M is the site's stale static homepage text. Coverage start years confirmed verbatim from the live homepage: ATP World Tour main draws since 1990; WTA Tour since 1997; ATP Challengers since 1998; ATP/Challenger and WTA qualifying since 2000; women's ITF $25K+ since 2002 (and $10K ITF since 2005); men's ATP Futures/Satellites since 2004; junior GRAND SLAM tournaments (not all juniors) since 2003; plus ATP/WTA doubles since 2003 and Davis/Fed Cup since 1997. Match statistics are NOT limited to Grand Slams: the site advertises "full statistics for all basic matches (aces, double faults, 1st serve %, total points won, etc)" and the live counter shows 778,492 matches with stats (~38% of the database) — the "Grand Slam statistics" phrasing is older marketing copy. Post-match point-by-point replay of most matches: confirmed verbatim. "Daily on-line database updates": confirmed verbatim, and in practice intraday — the live widget showed "Updated: 49 min. ago". Licensed users get direct access to the underlying Microsoft Access database (OnCourt.mdb) for their own development, which matters for a betting-model pipeline.

Evidence: (1) Live homepage https://www.oncourt.info/ fetched 2026-06-10 — raw HTML pulled via curl and read verbatim. Contains: "more than 1.6 million tennis matches... since 1990"; the full men's/women's coverage lists (ATP 1990, Challengers 1998, qualifying 2000, doubles 2003, Davis Cup 1997, Futures/Satellites 2004, junior Grand Slams 2003; WTA 1997, WTA qualifying 2000, ITF $25K+ 2002 / $10K 2005, Fed Cup 1997); "The full statistics for all basic matches (aces, double faults, 1st serve %, total points won, etc)"; "Point-by-point replay of most matches, like a real-time livescoring, but after match is completed"; "Daily on-line database updates..."; also Pinnacle odds-movement feature and OnCourt.mdb (MS Access) DB-password offer for licensees. (2) The site's own live database widget https://www.oncourt.info/cgi-bin/db.cgi?lang=en (the JS include the homepage loads) — fetched 2026-06-10: "Database version 107021; Updated 49 min. ago; Total matches 2,023,382; With stats 778,492". This is the adversarial key finding: actual current depth is ~2.0M matches and updates are intraday, making the claim a conservative understatement rather than an overstatement. (3) Apple App Store listing https://apps.apple.com/us/app/oncourt/id1183505662 — OnCourt iOS v3.7.4 released 2025-11-15 ("Results for season 2025") still says "more than 1.5 million matches", confirming the developer's static blurbs lag the live counter and the product is actively maintained. (4) Web search cross-check (third-party mirrors windows10download.com, software.informer etc.) shows older "1.5 million" copies of the same text, consistent with the 1.5M→1.6M→2.0M progression. No primary-source evidence contradicted any component of the claim.

### OnCourt odds and DB access — vote 1 — **confirmed**
Corrected/current fact: Confirmed as of 2026-06-10, with one mechanical refinement. The live oncourt.info homepage (current desktop version 7.0.3) advertises verbatim: (1) "Odds movement both for upcoming and past matches in Pinnacle bookmaker" — Pinnacle is the only bookmaker named anywhere on the page, so "no other books mentioned" holds; (2) "The possibility of exporting the data into Microsoft Excel keeping the original colors..."; (3) "After purchasing a license for OnCourt, you can get a password for the database (OnCourt.mdb, Microsoft Access) and use our data in your own developments!" Refinement: the license does not deliver a separate database file — the OnCourt.mdb is installed locally with the program, and the license entitles you to obtain the PASSWORD that unlocks it ("you can get" implies on request; whether the password costs extra is not stated on the site). Net effect matches the claim: direct programmatic access to results + Pinnacle odds without scraping, for 48.95 EUR/1-year or 88.95 EUR/lifetime Windows license (renewal 24 EUR/year). Separately, OnCourt sells a website/developer data feed (full database as MySQL dump with perl auto-update script: $200 setup + $50/month; or live XML: $0 setup + $50/month) — relevant if the desktop .mdb route proves restrictive. Unverified residuals: whether the .mdb internally contains odds from books other than Pinnacle, and whether the password is granted automatically vs. by emailing support — neither contradicts the claim as worded.

Evidence: Checked the primary source directly (live fetches on 2026-06-10): (1) https://www.oncourt.info/ — homepage feature list contains all three exact quotes above ("Odds movement both for upcoming and past matches in Pinnacle bookmaker"; Excel export sentence; "After purchasing a license ... password for the database (OnCourt.mdb, Microsoft Access) ... your own developments!"); a full-page scan found NO bookmaker name other than Pinnacle. (2) https://www.oncourt.info/order.html — current prices: 1-year Windows 48.95 EUR, lifetime 88.95 EUR, Windows+mobile 64.95 EUR, renewal 24 EUR/year; no database mention on this page. (3) https://www.oncourt.info/download.html — current build OnCourtSetup703.exe (v7.0.3), confirming the site is actively maintained. (4) https://www.oncourt.info/tennis_provider.html — separate developer/website feed: "full version of OnCourt database" as "database MySQL dump" + perl auto-update script, $200 setup + $50 USD/month, or live XML $0 setup + $50/month. (5) https://www.oncourt.info/faq.html returns HTTP 404 — no FAQ page exists to add conditions. (6) Adversarial web searches ("site:oncourt.info Pinnacle OR Marathon odds"; "OnCourt.mdb password license") surfaced no contradicting or more-current information — third-party download mirrors (e.g., https://oncourt.en.uptodown.com/windows) only repeat the official description. Could not refute any element; the claim mirrors the site's current statements.

### OnCourt gaps — vote 1 — **confirmed**
Corrected/current fact: As of June 2026, OnCourt (oncourt.info, KAN-soft) is a licensed Windows desktop program (current v7.0.3, OnCourtSetup703.exe; iOS/Android companions exist) with no public/REST API. Its odds feature is Pinnacle-only — the official site's sole odds bullet is "Odds movement both for upcoming and past matches in Pinnacle bookmaker" (forum-archived release notes: Pinnacle base, ATP since 2004, WTA since Aug 2006, incl. handicaps/totals) — and no other bookmaker appears in any official or community source. The granularity/timestamping of the odds-movement records (true opening line vs sampled snapshots) is not documented publicly anywhere — the official documentation is one feature bullet plus a screenshot, with no schema or timestamp spec. Automation under the standard license means reading the OnCourt.mdb (Microsoft Access) yourself, for which the site provides a password after purchase ("use our data in your own developments"); community projects (damienld/Tennis-predict, RileyCullen/oncourt-parser) confirm this is the working pattern. One refinement: KAN-soft also sells a separate webmaster data service ("Tennis statistic and Live for your website") — a MySQL database dump with cron auto-update scripts ($200 setup + $50/month) and a LIVE XML feed ($50/month) that includes "bookmaker odds etc." — a paid machine-readable feed, though not a documented odds API and not part of the normal app license.

Evidence: Checked the official site directly on 2026-06-10: homepage https://www.oncourt.info/ (verbatim: "Odds movement both for upcoming and past matches in Pinnacle bookmaker"; "After purchasing a license for OnCourt, you can get a password for the database (OnCourt.mdb, Microsoft Access) and use our data in your own developments!"; Windows download link kan-soft.com/OnCourtSetup703.exe); https://www.oncourt.info/download.html (v7.0.3 Windows installer); https://www.oncourt.info/order.html (only app licenses sold: 48.95 EUR/yr, 88.95 EUR lifetime — no API/data product, no odds details); https://www.oncourt.info/tennis_provider.html (B2B MySQL dump $200+$50/mo and XML LIVE feed $50/mo including "bookmaker odds etc.", bookmakers unnamed, not termed an API); https://www.kan-soft.com/ (developer landing page, no API/docs). Community corroboration of .mdb-based automation and Pinnacle-only odds fields: https://github.com/damienld/Tennis-predict ("data is collected from the MS Access Db provided with OnCourt software"; CSV fields "Odds1: pinnacle odds for P1") and https://github.com/RileyCullen/oncourt-parser. Forum-archived release notes (https://www.tennisforum.com/threads/oncourt-4-2.116203/, https://www.menstennisforums.com/threads/oncourt-5-3.10936/ via search excerpts): Pinnacle odds base ATP since 2004 / WTA since Aug 2006, handicaps/totals from pinnaclesports.com, Excel export of odds movements. Searches for any public schema/timestamp documentation (odds_atp / ID_B_O / opening-vs-closing definitions) returned nothing official, supporting the "not documented publicly" part; no source showed any non-Pinnacle book in the data.

### OddsJam workflow direction — vote 1 — **confirmed**
Corrected/current fact: OddsJam's +EV tool computes no-vig fair odds from a set of sharp bookmakers — its own docs name Pinnacle, BetOnline, Heritage, Circa, and the Betfair Exchange (not "Bookmaker," the one inaccuracy in the claim's parenthetical) — or from a market consensus/weighted average, and then flags retail books (DraftKings, BetMGM, FanDuel, BetRivers, etc.) whose odds beat that fair price; the user is directed to place the bet at the retail book, while Pinnacle/sharps serve only as the benchmark. This is structurally guaranteed: a sharp book's own vigged odds can never beat its own no-vig fair price, so the tool is indeed the inverse of a bet-at-the-market-maker workflow. Confirmed current as of June 2026 (no change after Gambling.com Group acquired OddsJam's parent in Jan 2025). Caveat on the cited URL: oddsjam.com/betting-tools/positive-ev is now marketing copy that confirms only the bet-at-retail direction ("You make the bet on the book (FanDuel, DraftKings, etc)"); the sharp-book/no-vig methodology lives on OddsJam's betting-education pages.

Evidence: (1) Claimed source https://oddsjam.com/betting-tools/positive-ev — fetched directly; page states "We tell you the exact sportsbook... You make the bet on the book (FanDuel, DraftKings, etc)", confirming users are directed to retail books, but it no longer details the fair-price methodology. (2) https://oddsjam.com/betting-education/how-do-positive-ev-sports-betting-filters-work — OddsJam's own explainer: "The filters ensure that a bet is Positive EV to the no-vig fair odds of a variety of sharp bookmakers", naming Pinnacle, BetOnline, Heritage, Circa and the Betfair Exchange as the sharp set, with the worked example placing the wager at FanDuel (retail). (3) https://oddsjam.com/betting-education/market-width — calls Pinnacle "the sharpest sportsbook", computes no-vig fair odds from its line, then recommends betting the flagged price at Barstool/BetRivers (retail). (4) https://oddsjam.com/betting-education/no-vig-fair-odds and https://oddsjam.com/betting-calculators/no-vig-fair-odds — the no-vig math (backing the vig out of implied probabilities). (5) Currency check: https://www.rotowire.com/betting/oddsjam-review (2026 review) — "The OddsJam EV tool scans for 'big line discrepancies' by comparing a sportsbook's odds to a sharp book (like Pinnacle) or a consensus market average", with one-click bet links to retail books; no methodology change reported post-acquisition. All sources agree: sharp books are the benchmark, retail books are where you bet.

### RebelBetting value AT Pinnacle is rare — vote 1 — **confirmed**
Corrected/current fact: Confirmed in substance, with three refinements. (1) The cited forum thread is real and says what is claimed, but the statements are from community users, not RebelBetting staff: "It's super rare to find value bets in pinnacle" (user waidas, Jan 2020); "Use a soft bookie instead. Bet365, unibet, Bwin" (user Nifty, Nov 2019); "value bets all the time but profit margin is only a percent or so on average" at Pinnacle (user Niel_S, Apr 2024). Note the 2024 post says Pinnacle value bets appear constantly but with only ~1% edges — "frequent but tiny" rather than "super rare". (2) Pinnacle as the sharp reference is confirmed by RebelBetting's own official pages: value is computed against sharp lines (mainly Pinnacle/Betfair/market average) and softs are the recommended betting venue. (3) The conclusion needs updating: since Jan 13, 2021 RebelBetting's ValueBetting Pro tier DOES mechanically support a Pinnacle-only workflow (it lists value bets at sharps including Pinnacle), but RebelBetting's own staff-published results show it is unprofitable — realized yield at Pinnacle was negative (−3.72%, later −3.18%) and staff stated "I would be surprised if Pinnacle turns positive, except on a few specific markets." So the practical bottom line stands, on stronger evidence than the claim cited: RebelBetting cannot drive a PROFITABLE Pinnacle-only value-betting workflow; its product is built to bet soft books against sharp reference prices.

Evidence: (1) Primary source verified verbatim via Discourse print view: https://community.rebelbetting.com/t/value-bets-on-pinnacle/2189 (and /print) — 7 posts, Nov 2019–Apr 2024; exact quotes "It's super rare to find value bets in pinnacle" (waidas), "Use a soft bookie instead. Bet365, unibet, Bwin" (Nifty), "profit margin is only a percent or so on average" (Niel_S); all regular users, no staff. (2) Official staff announcement "Update: value betting on sharp bookmakers" (Simon, Jan 13 2021, updated Feb 9 2022): https://community.rebelbetting.com/t/update-value-betting-on-sharp-bookmakers/4918 — sharp value betting added to ValueBetting Pro incl. Pinnacle; tracked Pinnacle yield −3.72% then −3.18%; staff quote "I would be surprised if Pinnacle turns positive, except on a few specific markets." (3) Official FAQ: https://www.rebelbetting.com/faq/value-betting-on-sharps — profit on sharps "more difficult", smaller edges, Pro plan required, beginners advised to start at softs; Pinnacle partnership since 2009. (4) Current supported-bookmakers page: https://www.rebelbetting.com/en-us/bookmakers — Pinnacle listed (recommended for sure betting / as sharp that won't limit), soft books positioned as the primary value-betting venue, sharps Pro-only. (5) Corroborating community thread: https://community.rebelbetting.com/t/value-betting-on-sharp-bookies-as-pinnacle-worthwhile/3635 (Jul–Nov 2020) — users: "There is basically no value bets for pinnacle on Rebelbetting"; ~2% yield achievable on other sharps (SBO/Sportmarket), not Pinnacle. No 2025–2026 source found reversing any of this; official pages current as of June 2026 still match.