# Research archive: crypto-marketmaker-books

*Raw structured output from the 2026-06-10 multi-agent research run. Facts below are as-reported by research agents; entries in the Verifications section were independently adversarially checked.*

## Facts

### Pinnacle crypto deposits (high) **[decision-critical]**
Pinnacle's international site accepts cryptocurrency deposits in Bitcoin, Litecoin, and Tether (ERC20 and TRC20) processed via third-party converters such as BitPay; crypto is converted into the fiat currency of the player account (no crypto-denominated balances), with reported deposit maximums around $50,000 for BTC and up to $125,000 for USDT as of 2026.

Source: https://www.pinnacle.com/en/payment-options/bitpay

### Pinnacle Canada/Ontario licensing (high) **[decision-critical]**
Pinnacle has been licensed by AGCO/iGaming Ontario since October 2022 and serves Ontario through pinnacle.ca; Canadians outside Ontario are served under Pinnacle's international licenses (Curaçao, plus MGA per reviews), so Pinnacle is usable from every Canadian province as of 2026.

Source: https://footballwhispers.com/ca/betting/pinnacle/legal/

### Pinnacle Ontario crypto ban (medium) **[decision-critical]**
Ontario's regulated iGaming framework (AGCO/iGaming Ontario) does not permit cryptocurrency deposits at licensed operators, so the Ontario product pinnacle.ca is fiat-only; Pinnacle's crypto deposit rails are only available on the international site used by non-Ontario players — decisive for a crypto-funded bettor located in Ontario.

Source: https://www.canadasportsbetting.ca/online-sportsbook-reviews/deposit-methods/bitcoin.html

### Pinnacle API closure (high) **[decision-critical]**
Pinnacle's official API documentation README states: 'Access to Pinnacle API suite has been closed for the general public since July 23rd, 2025'; remaining access is bespoke for 'select high value bettors & commercial partnerships' plus academics and pregame handicapping projects, by emailing a use-case description to api@pinnacle.com — ordinary customers can no longer self-serve odds or bet-placement API access.

Source: https://github.com/pinnacleapi/pinnacleapi-documentation/blob/master/README.md

### Pinnacle Solution is B2B (low) **[decision-critical]**
Pinnacle Solution is Pinnacle's B2B brand (odds feed / turnkey sportsbook for licensed operators), not a product an individual bettor can subscribe to; for a solo quant the realistic automation routes are the bespoke api@pinnacle.com application or a betting broker that fronts PS3838 (Pinnacle's B2B/Asian-facing brand).

Source: https://www.pinnacle.com/en/solution/

### Pinnacle winners-welcome policy (high) **[decision-critical]**
Pinnacle's published 'Winners Welcome' policy states it does not limit, discriminate against, or close accounts of winning players and explicitly tolerates arbitrage; this is the book's own claim, but it is the industry-consensus archetype of a true market-maker and the claim has stood publicly for over a decade.

Source: https://www.pinnacle.com/betting-resources/en/educational/winners-welcome-at-pinnacle

### Pinnacle margin class (medium) **[decision-critical]**
Pinnacle operates margins of roughly 2-3% on major markets (a 102-103% two-way book) versus an industry standard 5-7%; no public 2026 tennis-specific margin measurement was found, but main-tour ATP/WTA moneylines are consistently described in the 102-103% class — the sharp-book reference price.

Source: https://www.pinnacleoddsdropper.com/blog/complete-guide-to-pinnacle-sports-betting-strategies-odds-and-tips-for-every-sport-2025

### Pinnacle limits and re-betting (medium) **[decision-critical]**
Pinnacle posts the maximum stake on each bet slip, runs limits described as the highest in the industry (about $30,000 on football and major North American mainlines per reviews, five-figure maximums on big tennis events), and allows re-betting up to the maximum on the same market after a short interval whether or not the price moved, so cumulative position size is effectively a multiple of the posted max.

Source: https://globalextramoney.com/pinnacle-sports-review

### Pinnacle tennis coverage (medium)
Pinnacle offers pre-match and in-play tennis across ATP, WTA, and Challenger tours (moneyline, handicap, totals) via its tennis matchups hub; ITF-level coverage is not clearly documented on its public pages.

Source: https://www.pinnacle.com/en/tennis/matchups/

### Pinnacle tennis retirement rule (high) **[decision-critical]**
Pinnacle's tennis settlement rule: if a player retires or is disqualified, Match Money Line bets have action as long as one full set has been completed, otherwise they are void; all other tennis markets require their relevant period to be completed — this 'one-set rule' defines how match bets settle on retirements.

Source: https://www.pinnacle.com/en/future/betting-rules

### BetOnline crypto deposits (medium) **[decision-critical]**
BetOnline accepts roughly 17 cryptocurrencies including BTC, ETH, LTC, USDT, USDC, SOL, ADA, and DOGE, with crypto deposits from about $10-20, no deposit fees, and crypto withdrawals up to $500,000 per transaction processed within ~24 hours.

Source: https://help.betonline.ag/en/articles/185149-how-to-deposit-with-cryptocurrency

### BetOnline Canada access (medium) **[decision-critical]**
BetOnline accepts players from all Canadian provinces including Ontario, but holds no Canadian or Ontario license — it operates as an unregulated offshore (grey-market) book from the Canadian regulator's perspective, with no local recourse.

Source: https://www.snbet.ca/betonline-canada-review

### BetOnline tennis coverage (medium)
BetOnline covers ATP, WTA, Challenger, and ITF tournaments with live in-play betting, and was rated the top offshore tennis sportsbook by Dot Esports in 2025 partly for this coverage breadth.

Source: https://dotesports.com/betting/tennis

### BetOnline margin class (low) **[decision-critical]**
BetOnline is not a uniformly low-margin book: reduced-juice pricing (-105/-106) applies only to selected markets and promos while the baseline is standard ~-110 (≈104.8% book); no published tennis-specific margin measurement exists as of June 2026, so its tennis margin class must be measured empirically from odds feeds.

Source: https://sportsintensity.com/us/sportsbooks/offshore/reduced-juice/

### BetOnline limits behavior (medium) **[decision-critical]**
BetOnline marketing emphasizes high limits and a 61-second re-bet allowance on the same market, but Sportsbook Review forum reports document winning players being limited (e.g., a live-betting limit cut from $1,000 to $250, ~25% of normal), and users note moving to clone sites sportsbetting.ag / TigerGaming for fresh limits — BetOnline is sharp-tolerant on mainlines but is NOT a pure market-maker that never profiles winners.

Source: https://www.sportsbookreview.com/forum/sportsbooks-industry/1783973-does-betonline-limit-betting

### BetOnline tennis retirement rule (medium) **[decision-critical]**
BetOnline's tennis rules require one full set to be completed for ATP/WTA head-to-head (moneyline) wagers to stand on retirement, otherwise void; the full match must be completed for props except already-completed 1st-set markets — same one-set convention as Pinnacle.

Source: https://help.betonline.ag/en/articles/185194-tennis-rules

### Bookmaker.eu crypto deposits (high) **[decision-critical]**
Bookmaker.eu's own payments page lists BTC, ETH, LTC, USDT (ERC20), and USDC (ERC20) for deposits and withdrawals with no book-side fees and fee reimbursement on deposits ≥$100; crypto payouts are capped at 5 per week and $10,000 per payout, which is a real constraint for scaling a winning bankroll out (book's own page; the '90% of customers use Bitcoin' line is marketing).

Source: https://www.bookmaker.eu/bitcoin-sportsbook

### Bookmaker.eu Canada and license (medium) **[decision-critical]**
Bookmaker.eu (BetCRIS group, Costa Rica, unregulated) accepts Canadian players nationwide including Ontario; bonus terms carve out US/Canadian residents for some promos, confirming Canadians are an accepted customer class.

Source: https://www.mytopsportsbooks.com/reviews/bookmaker/

### Bookmaker.eu winners tolerance (medium) **[decision-critical]**
Bookmaker.eu markets itself as 'where the line originates' and officially 'welcomes all winners' with high limits (reviews cite $40,000+ on NBA sides), but a Sportsbook Review forum thread titled 'Bookmaker.eu limits winning players' and 2025-2026 review commentary document sharp winners being limited — its market-maker reputation is partially historical and should be treated as degraded.

Source: https://www.sportsbookreview.com/forum/sportsbooks-industry/3606057-bookmaker-eu-limits-winning-players.html

### Bookmaker.eu tennis depth (low)
Bookmaker.eu offers tennis betting including live in-game, but it is a US-sports-first book; no documentation of Challenger/ITF depth or any measured tennis margin was found in 2026 sources.

Source: https://www.bookmaker.eu/bet-TENNIS

### Bet105 crypto-only banking (medium) **[decision-critical]**
Bet105 is a crypto-only sportsbook (no cards or bank transfers) accepting BTC, ETH, USDT (TRC20 and ERC20), and USDC, with a $5 minimum deposit, ~$250,000 per-transaction maximum, withdrawals reported completed in under two hours, and a $250,000/week withdrawal cap.

Source: https://www.offshoresportsbooks.com/bet105/

### Bet105 pricing class (medium) **[decision-critical]**
Bet105's signature pricing is -105/-105 (≈102.4% two-way book, ~2.4% vig) on major spreads and totals, lower than the -110 standard; however its review coverage does not confirm that the reduced-juice pricing extends to tennis moneylines — tennis margin class is unverified.

Source: https://punter2pro.com/bet105-review/

### Bet105 winners and limits (medium) **[decision-critical]**
Bet105 claims profitable players are not restricted and displayed betslip limits apply equally to all accounts regardless of performance, with reviewers reporting five-figure bets routinely accepted; this is largely the book's own positioning ('Winners Welcome') echoed by affiliate reviewers — the book only relaunched in 2024 and is registered in Costa Rica with no regulator, so the track record is shallow.

Source: https://punter2pro.com/bet105-review/

### Bet105 Canada access (medium) **[decision-critical]**
Bet105's restricted-country list per its review coverage is Russia, Ukraine, India, Nigeria, South Africa, Iran, Vietnam, and Venezuela — Canada (including Ontario) is not restricted.

Source: https://punter2pro.com/bet105-review/

### Bet105 API (medium) **[decision-critical]**
No API or automation access is offered or mentioned anywhere for Bet105 — programmatic interaction would require unofficial scraping.

Source: https://punter2pro.com/bet105-review/

### Cloudbet customer API (high) **[decision-critical]**
Cloudbet publishes official public APIs — Feed API (real-time odds), Trading API (programmatic bet placement), and Account API (balances) — and ordinary customers self-generate an API key from 'My Account → API' in the player account; documentation is public at cloudbet.github.io/wiki and github.com/Cloudbet/docs, making Cloudbet the only conventional sportsbook in this comparison with self-serve bet-placement API access in 2026.

Source: https://cloudbet.github.io/wiki/en/docs/sports/api/

### Cloudbet crypto coins (medium) **[decision-critical]**
Cloudbet is crypto-native and accepts 20+ cryptocurrencies including BTC, ETH, USDT, LTC, DOGE, XRP, ADA, DASH, TRX, and DAI, plus in-app fiat-to-crypto purchases via Visa/Mastercard/Apple Pay/Google Pay.

Source: https://punter2pro.com/cloudbet-review/

### Cloudbet tennis coverage (medium)
Cloudbet offers match betting on all ATP and WTA events plus extensive Challenger and ITF coverage, with live betting that extends to lower-tier tournaments (per a tennis-specialist review).

Source: https://www.tennisnerd.net/tennis-betting/cloudbet

### Cloudbet margin class (medium) **[decision-critical]**
Punter2Pro's testing measured ~5.9% margin on Cloudbet's popular 1x2 markets, with other reviews citing 3.45-5.1% on majors and occasional promotional 'zero-margin' events — Cloudbet prices like a mid-margin crypto book, NOT in Pinnacle's 102-103% market-maker class on typical markets despite sharp-bettor marketing.

Source: https://punter2pro.com/cloudbet-review/

### Cloudbet tennis limits (medium) **[decision-critical]**
A tennis-specialist review observed Cloudbet tennis match max stakes around 0.02 BTC typical (~$1,280 at the time of review) and up to 0.06 BTC (~$3,845) on bigger matches — far below Pinnacle's tennis limits; Cloudbet's '10 BTC limits' marketing applies to major (non-tennis) markets, and multibet payouts cap around €300,000. Tennis-specific limits in 2026 need account-level verification as this observation is dated.

Source: https://www.tennisnerd.net/tennis-betting/cloudbet

### Cloudbet Canada/Ontario status (high) **[decision-critical]**
Cloudbet's official restricted-jurisdictions help article (fetched June 2026) lists Australia, Austria, Belgium, China, Macau, Hong Kong, Curaçao, Cuba, France, Germany, Iran, Lithuania, Malta, Myanmar, Netherlands, North Korea, Singapore, Syria, Spain, UK, USA, and parts of Ukraine — neither Canada nor Ontario appears; some third-party reviews nevertheless claim Ontario signups are blocked under AGCO pressure, so Ontario status is conflicting but the official list permits all of Canada.

Source: https://www.cloudbet.com/en/support/articles/101693-which-countries-are-restricted-from-using-cloudbet

### Cloudbet winners claim (low) **[decision-critical]**
Cloudbet markets itself as 'built for sharp bettors' that welcomes professional/winning players without restrictions; no independent verification (long-run winner case studies or credible forum evidence) of this tolerance was found — treat as the book's own claim.

Source: https://punter2pro.com/cloudbet-review/

### Cloudbet license (medium)
Cloudbet operates under Curaçao eGaming licence No. OGL/2024/328/0599 (Halcyon Super Holdings B.V.) and has run continuously since 2013, making it one of the longest-standing crypto sportsbooks.

Source: https://punter2pro.com/cloudbet-review/

### Sportsbet.io crypto and Canada (medium) **[decision-critical]**
Sportsbet.io (Yolo Group) is a crypto-native sportsbook (BTC, ETH, USDT and others) whose restricted list includes Ontario, Canada — players in other Canadian provinces can access it, but Ontario is excluded; it holds no Canadian licensing.

Source: https://cryptoslate.com/crypto-sportsbooks/sportsbet-io-sportsbook-review/

### Sportsbet.io tennis margin (medium) **[decision-critical]**
A 2026 review measured Sportsbet.io tennis match lines at roughly 108% books (≈8% margin, ~92% payout) on popular events — squarely soft-book/retail pricing, the worst tennis margin class in this comparison; single-source measurement, but directionally consistent with its recreational positioning.

Source: https://cryptoslate.com/crypto-sportsbooks/sportsbet-io-sportsbook-review/

### Sportsbet.io winners tolerance (medium) **[decision-critical]**
Sportsbet.io review coverage reports that accounts triggering risk flags can be restricted and recurring user complaints involve limits and verification around wins — it behaves like a retail book toward winners, not a market-maker.

Source: https://cryptoslate.com/crypto-sportsbooks/sportsbet-io-sportsbook-review/

### Stake.com Canada access (medium) **[decision-critical]**
Stake.com is accessible from all Canadian provinces EXCEPT Ontario, which it geo-blocks (no iGaming Ontario license); a regulated fiat-only Stake.ca product for Ontario has been expected to launch in 2026 but would be a fundamentally different product from the crypto platform.

Source: https://www.sportsgambler.com/review/stake/canada/

### Stake.com crypto and CAD support (medium) **[decision-critical]**
Stake.com accepts 20+ cryptocurrencies (BTC, ETH, USDT, SOL, XRP and others) and also supports CAD fiat balances for Canadian players, covering 40+ sports including tennis.

Source: https://www.canadasportsbetting.ca/online-sportsbook-reviews/stake/

### Stake.com tennis margins (medium) **[decision-critical]**
Review measurements put Stake's football/tennis margins at ~4-5% on average, tightening to 2-3% on Grand Slam tennis and widening to 6-8.1% on minor events; coverage spans ATP, WTA, and ITF — a mid-margin retail book that gets competitive only on the biggest tennis events.

Source: https://worldpokerdeals.com/betting/stake-sportsbook-review

### Stake.com API (medium) **[decision-critical]**
Stake.com has no official customer-facing betting API; its odds are only available programmatically through third-party commercial feed vendors such as OpticOdds — automation of bet placement is not officially supported.

Source: https://opticodds.com/sportsbooks/stake-api

### BC.Game platform and crypto (medium) **[decision-critical]**
BC.Game accepts 130-140+ cryptocurrencies (BTC, ETH, USDT, LTC, DOGE, XRP, TRX, Monero and many more) and runs its sportsbook on the third-party Betby engine ('BC Engine'); tennis carries ~50 live in-play markets and reviews place its football/basketball margins at about the average of peer crypto sportsbooks — no low-margin claim, no customer API.

Source: https://cryptoslate.com/crypto-sportsbooks/bc-game-sportsbook-review/

### BC.Game license risk (high) **[decision-critical]**
BC.Game voluntarily withdrew from its Curaçao gaming license in December 2024 amid regulatory pressure (following a Curaçao court bankruptcy dispute involving its operating entity) and now operates under an Anjouan (Union of Comoros) license — a materially weaker license with less recourse, a significant counterparty-risk downgrade for holding a betting bankroll there.

Source: https://lcb.org/news/bc-game-announces-withdrawal-from-curacao-jurisdiction

### BC.Game Canada access (medium) **[decision-critical]**
BC.Game is usable from most of Canada but excludes Ontario, where it holds no iGaming Ontario license and is not part of the regulated market.

Source: https://rg.org/en-ca/sportsbooks/bcgame/is-bcgame-legit-in-canada

### Polymarket tennis markets 2026 (high) **[decision-critical]**
Polymarket runs substantial tennis markets in 2026: a dedicated tennis section with daily match-level (moneyline-equivalent) markets for ATP/WTA, props, and Grand Slam futures; the 2026 Men's French Open Winner market alone traded ~$42.2M since January 2026, and roughly 441 tennis markets were live in the sports category as of mid-2026 — tennis on Polymarket is real and liquid at the top level.

Source: https://polymarket.com/sports/tennis

### Polymarket Ontario ban (high) **[decision-critical]**
Polymarket is permanently banned from serving Ontario following an April 2025 Ontario Securities Commission settlement (CAD $200,000 penalty, province-wide trading ban until at least April 2027); Polymarket's own geoblock documentation lists 'Canada (CA) | Ontario | ON' as a blocked region where order placement (frontend and API) is rejected, while other Canadian provinces are not blocked.

Source: https://docs.polymarket.com/api-reference/geoblock

### Polymarket fees on sports markets (high) **[decision-critical]**
Polymarket's official fee docs (2026): makers are never charged fees (and receive 20-25% maker rebates); takers on sports markets pay fee = shares × feeRate × price × (1 − price) with a sports feeRate of 0.03-0.04, peaking around 0.75-1% of notional at a 50/50 price — i.e., an effective ~101% 'book' for takers at evens, far below any sportsbook margin; API users must query each market's feeSchedule (getClobMarketInfo) since fees apply per-market based on creation date.

Source: https://docs.polymarket.com/trading/fees

### Polymarket API and funding (high) **[decision-critical]**
Polymarket offers a fully public CLOB trading API with an official Python client (py-clob-client) for programmatic order placement and market data; funding/settlement is USDC on Polygon (wallet-based, crypto-native) — ideal for an automated pipeline, subject to the Ontario geoblock on order placement.

Source: https://docs.polymarket.com/api-reference/geoblock

### Canada prediction-market regulatory risk (medium)
In 2026 Canadian securities regulators (CSA members) publicly warned prediction-market operators to get licensed or face enforcement, signaling that non-Ontario Canadian access to Polymarket-style platforms could tighten — a forward regulatory risk for relying on prediction markets from Canada.

Source: https://gamingamerica.com/news/1057414/canadian-regulators-warn-prediction-market-industry-get-licensed-or-face-enforcement

### SX Bet profile and API (high) **[decision-critical]**
SX Bet is a peer-to-peer blockchain betting exchange (SX Network, Polygon-family rollup) where stakes are posted in USDC and bets settle on-chain; it exposes a fully public API — read endpoints require no API key and an authenticated betting API supports programmatic order placement — with tennis as sport ID 7 in the API and order-book (back/lay) depth at multiple price levels.

Source: https://api.docs.sx.bet/

### SX Bet fees (medium) **[decision-critical]**
SX Bet currently charges no trading fees on single bets (the cost to bettors is the order-book spread), per its own help-center fee article — combined with the exchange model this places effective pricing near Polymarket's class rather than sportsbook margins, though realized cost depends on liquidity.

Source: https://help.sx.bet/en/articles/2798017-sx-bet-fees

### SX Bet Ontario restriction (high) **[decision-critical]**
SX.bet's terms and conditions list 'Ontario, Canada' first among restricted jurisdictions (alongside Australia, Austria, France, Germany, Netherlands, Spain, UK, USA and sanctioned countries); the rest of Canada is not restricted; the service is governed by Costa Rica law with Ontario courts having jurisdiction for non-arbitration disputes (the operator has Toronto roots).

Source: https://help.sx.bet/en/articles/3613372-terms-and-conditions

### SX Bet tennis depth (medium)
SX Bet's order-book depth is concentrated in soccer, MLB, NHL, tennis, and MMA per developer-facing coverage, but it is a niche exchange whose absolute tennis liquidity is far below Betfair or Pinnacle and is unquantified publicly — depth must be sampled via its API before relying on it.

Source: https://oddspapi.io/blog/sx-bet-api-crypto-sports-exchange/

### SX Bet tennis retirement rule (high) **[decision-critical]**
SX.bet settles tennis match moneylines with action if at least one full set was completed before retirement/disqualification, void otherwise — identical to the Pinnacle/BetOnline one-set convention, which keeps settlement consistent if arbitraging or hedging across these venues.

Source: https://help.sx.bet/en/articles/5090684-tennis-betting-rules

### Betfair Exchange Canada (high) **[decision-critical]**
Betfair Exchange is not available to Canadian residents in 2026 — Canadians cannot register, Canada is restricted in Betfair's terms, and existing accounts cannot legally be used from Canada — ruling out the world's largest tennis exchange for this bettor regardless of its merits.

Source: https://caanberry.com/betfair-legal-countries/

### Betfair crypto support (medium) **[decision-critical]**
Betfair does not accept cryptocurrency deposits in any form (fiat cards, bank transfer, PayPal, Skrill/Neteller only); crypto can only reach Betfair indirectly by converting to fiat via an e-wallet — moot for this bettor given the Canada block, but it fails the crypto criterion too.

Source: https://nowpayments.io/blog/does-betfair-accept-bitcoin

### Sportmarket books and pricing (medium) **[decision-critical]**
Sportmarket (betting broker, est. 2004, Isle of Man regulated) provides one-account access to PS3838 (Pinnacle's B2B brand), SBObet, IBCbet/Maxbet, BetISN and exchanges (Betfair, Matchbook, Smarkets, Betdaq, Molly Exchange); it charges no commission on bookmaker bets (costs embedded in odds, so tennis prices at the underlying books' ~102-103% sharp class) while exchange commissions pass through (e.g., Betfair 2.3%, Matchbook 1.8%); maximums are shown per bet slip and vary by underlying book.

Source: https://punter2pro.com/sportmarket-review/

### Sportmarket crypto and Canada (medium) **[decision-critical]**
Sportmarket accepts crypto deposits in BTC, USDT, and USDC (plus bank transfer, cards, Skrill, Neteller, MuchBetter) with no deposit fees and KYC verification required before depositing; its restricted countries are the US, UK, France, Spain, and Portugal — Canada is accepted; it also advertises that it never limits winning players (broker claim consistent with the market-maker books it fronts).

Source: https://bookie.broker/sportmarket/

### BetInAsia crypto and Canada (medium) **[decision-critical]**
BetInAsia accepts crypto deposits in BTC, ETH, USDT, and USDC with no fees on USDT deposits (only card deposits carry a 3% fee); its published restricted list (USA, UK, France, Germany, Netherlands, North Macedonia, Portugal, Sweden, Singapore, Turkey, Afghanistan, Iran, North Korea) does not include Canada, so Canadians are accepted.

Source: https://bookie.broker/betinasia/

### BetInAsia BLACK API (medium) **[decision-critical]**
BetInAsia BLACK (Mollybet-powered trading platform) offers Pull and Push API connections aggregating 10+ sharp bookmakers and exchanges in a single connection, but API access costs a non-refundable 600 EUR connection fee and is terminated for any user turning over less than £50,000 per month — a viable automation path only at meaningful volume.

Source: https://betinasia.zendesk.com/hc/en-us/articles/360013835620-Can-I-have-an-API-connection-on-BetInAsia-BLACK

### AsianConnect crypto and Canada (medium) **[decision-critical]**
AsianConnect (betting broker est. 2002, fronts Pinnacle/PS3838 and Asian books via platforms like Asianodds) accepts Bitcoin and Tether deposits (minimum ~10 EUR; 50 EUR to open an Asianodds account); its official restricted-country list (Philippines, China, Taiwan, Hong Kong, Malaysia, Singapore, USA, Thailand, Vietnam, Indonesia and others) does not include Canada — Canadians are accepted.

Source: https://asianconnect88.zendesk.com/hc/en-us/articles/900002884103-What-are-the-countries-restricted-from-registering-an-account-to-Asianconnect

### Broker winner-tolerance rationale (medium) **[decision-critical]**
Betting brokers route stakes into Asian market-maker books (PS3838, SBObet, IBCbet) whose business model prices winners rather than banning them, and the brokers themselves advertise no winner limiting — since Pinnacle's direct customer API closed in July 2025, brokers are the standard remaining route for a winning automated bettor to get sharp-book tennis prices at scale.

Source: https://globalextramoney.com/bookmakers/bet-broker

### Third-party odds APIs for CLV tracking (medium) **[decision-critical]**
Tennis odds from Pinnacle, BetOnline, Stake and other books remain programmatically accessible through commercial aggregator APIs (e.g., The Odds API's tennis endpoints covering ATP/WTA moneylines, OpticOdds for Stake), which covers the closing-line-value tracking and margin-measurement needs of a model pipeline even where the books themselves offer no API.

Source: https://the-odds-api.com/sports/tennis-odds.html

### Ontario carve-out pattern (medium) **[decision-critical]**
The bettor's province determines the entire menu: compliance-conscious crypto operators (Stake.com, BC.Game, Sportsbet.io, SX Bet, Polymarket — and per some reviews Cloudbet) all geo-exclude Ontario specifically while serving the rest of Canada, whereas Costa Rica grey books (BetOnline, Bookmaker.eu, Bet105) serve all provinces including Ontario, and Pinnacle serves Ontario only through its fiat-only AGCO-licensed pinnacle.ca product.

Source: https://cricketca.ca/is-stake-legal-in-canada/

## Gaps noticed by the research agent
- No source publishes measured 2026 tennis-specific margins for BetOnline, Bookmaker.eu, Bet105, or BC.Game — margin class for ATP/WTA moneylines at these books must be computed empirically (e.g., overround snapshots via The Odds API), which the bettor's existing pipeline could do in a day.
- Whether Bet105's signature -105 reduced juice applies to tennis moneylines (vs only US-sport spreads/totals) is undocumented anywhere.
- Cloudbet's actual 2026 tennis max stakes are unknown — the only public observation (~$1,300-3,800 per match) is from a dated review, conflicting with '10 BTC limit' marketing; needs account-level verification before treating Cloudbet as a primary venue.
- Stake.com's tolerance of winning players is undocumented in either direction — no credible limiting reports and no winners-welcome policy; same gap for BC.Game.
- Polymarket and SX Bet tennis order-book depth below Grand Slam level (regular ATP/WTA draws, any Challenger coverage) is unquantified anywhere; both expose free APIs, so liquidity should be sampled programmatically before allocating bankroll.
- Unresolved conflict: several third-party reviews claim Cloudbet blocks Ontario signups, but Cloudbet's own restricted-jurisdictions article omits Canada entirely — needs a signup test or support confirmation.
- Whether non-Ontario Canadians on pinnacle.com retain crypto deposit rails versus being migrated onto fiat pinnacle.ca rails is not cleanly documented — conflicting secondary sources; needs a live account test from the bettor's province.
- Tennis retirement/settlement rules were only confirmed for Pinnacle, BetOnline, and SX Bet (all one-completed-set conventions); nobody compiles the equivalent rules for Stake, Cloudbet, BC.Game, Sportsbet.io, Polymarket resolution criteria, or the brokers' underlying Asian books — rule mismatches create settlement risk when hedging the same match across venues.
- Broker per-book tennis limit schedules (e.g., PS3838 ATP/Challenger max stakes via Sportmarket or AsianConnect) are not published — only visible on the bet slip after registration; Sportmarket's own API/automation support is also undocumented (only BetInAsia BLACK's API terms are public).
- Pinnacle's post-July-2025 bespoke API acceptance criteria ('select high value bettors') are unpublished — unknown what volume a solo quant needs to qualify via api@pinnacle.com, worth a direct application email since rejection costs nothing.
- No source addresses CAD-denomination practicalities for a Canadian crypto bettor: FX/conversion spreads when books force fiat account currencies (Pinnacle converts crypto to fiat at third-party rates) versus staying USDT/USDC-denominated at brokers, Cloudbet, Polymarket, or SX Bet — a real cost difference worth modeling.
- Nobody covers ITIA integrity-driven market suspensions/voids (e.g., markets pulled mid-match on suspicious betting) and how each venue settles affected bets — relevant for in-play automation on lower-tier tennis where most integrity alerts originate.

## Verifications (adversarial)

### Pinnacle crypto deposits — vote 1 — **confirmed**
Corrected/current fact: Pinnacle's international site (pinnacle.com, Ragnarok Corporation N.V.) accepts exactly three cryptocurrencies for deposits — Bitcoin (branded via BitPay), Litecoin, and USDT Tether offered as both ERC20 and TRC20 (TRC20 not available for all country/currency combinations) — processed by third-party exchange providers that convert the crypto into the fiat currency of the player account; no crypto-denominated balances ("We do not offer Bitcoin/Litecoin/USDT Tether as an account currency"). Deposit maximums are per transaction and per account currency: BTC and LTC max $50,000 USD / $50,000 CAD / €50,000 (min ~$10-15/€10). USDT max is currency-dependent: $125,000 CAD, $100,000 USD, €82,500 EUR, $139,000 NZD — so the claim's "up to $125,000" is the Canadian-dollar ceiling, not USD (USD max is $100,000). USDT minimums are much higher than BTC/LTC: ~$610 CAD / $500 USD / €450 (TRC20 minimums may be lower). Deposits confirm in 30-60 minutes and are fee-free (network/mining fees not covered); a 3x deposit rollover applies before withdrawal else a 10% fee; crypto sourced from Garantex or similar is refused. Verified as of Jan 2026 (Litecoin page) and Dec 2025 (USDT page) archives plus a Jan 2026 third-party guide; no evidence of changes through June 2026.

Evidence: (1) Claimed source https://www.pinnacle.com/en/payment-options/bitpay is live (Google-indexed June 2026, same title) but returns HTTP 502 ("error code: 502") to scripted fetchers on /payment-options paths while pinnacle.com homepage returns 200 — bot protection, so content was verified via Internet Archive: snapshot 2025-05-23 (http://web.archive.org/web/20250523213932/https://www.pinnacle.com/en/payment-options/bitpay) shows BTC max $50,000 USD/$50,000 CAD/€50,000, "third party exchange providers that convert cryptocurrencies into the FIAT currency of your player account", "We do not offer Bitcoin as an account currency", 30-60 min processing. (2) Litecoin page snapshot 2026-01-24 (http://web.archive.org/web/20260124115103/https://www.pinnacle.com/en/payment-options/litecoin): same $50,000/€50,000 max and fiat-conversion language. (3) USDT Tether page snapshot 2025-12-16 (http://web.archive.org/web/20251216203406/https://www.pinnacle.com/en/payment-options/usdt_tether): explicit ERC20 + TRC20 options; deposit limits by account currency CAD $610-$125,000, USD $500-$100,000, EUR €450-€82,500, NZD $700-$139,000; "We do not offer USDT Tether as an account currency". (4) Payment-options index snapshot 2025-10-12 (http://web.archive.org/web/20251012215336/https://www.pinnacle.com/en/payment-options) lists exactly three crypto methods: bitpay, litecoin, usdt_tether. (5) Independent cross-check: SportsBoom Pinnacle deposits guide updated 2026-01-19 (https://www.sportsboom.com/betting/reviews/pinnacle/deposits/) matches EUR figures (BTC/LTC €50,000 max; USDT €450 min/€82,500 max, 30-60 min, fiat conversion, crypto not a supported account currency). (6) June 2026 web searches found no reports of Pinnacle dropping or adding crypto deposit options; live Google snippets for the bitpay and usdt_tether URLs match the archived content.

### Pinnacle Canada/Ontario licensing — vote 1 — **confirmed**
Corrected/current fact: Pinnacle is registered in Ontario (AGCO registration Sept 7, 2022; AGCO licence OPIG1236075) and its iGaming Ontario site pinnacle.ca went live Oct 26, 2022 — operator entity "Pinny (Ontario) Limited" is on iGaming Ontario's official registry with Casino + Sports Betting. Canadians outside Ontario are served by pinnacle.com under Ragnarok Corporation N.V., licensed by the Curaçao Gaming Control Board (licence OGL/2023/105/0084 — the current GCB licence, replacing the old 8048/JAZ2013-013 still cited on Pinnacle's corporate page); Pinnacle also holds an MGA licence (MGA/CL2/1069/2015, sports betting only) but that is not the licence covering Canadians. As of today (June 10, 2026) Pinnacle is indeed usable from every Canadian province — its T&C restrict only "Province of Ontario" within Canada (Ontario uses pinnacle.ca). HOWEVER, this stops being true on July 13, 2026: Alberta's regulated iGaming market launches that day, AGLC requires all unregulated operators to cease taking Alberta bets by July 13, 2026 (max case-by-case extension Oct 13, 2026; non-compliance risks unsuitability), and Pinnacle does NOT appear on AGLC's official registrant list (43 operators, in effect 2026-06-05) nor has it announced an Alberta application. Unless Pinnacle registers before launch, Alberta users lose access ~5 weeks from now — do not build an "all-province" assumption into the betting project beyond July 13, 2026.

Evidence: Checked the claimed source directly plus primary sources. (1) Claimed source https://footballwhispers.com/ca/betting/pinnacle/legal/ — states iGaming Ontario licence Oct 2022, rest of Canada via grey market under Curaçao/Malta licences, all provinces accessible; consistent with the claim but omits pinnacle.ca and the Alberta cutoff. (2) iGaming Ontario official operator registry https://www.igamingontario.ca/en/operator/operators?title=pinnacle&field_legal_entity_name_target_id=All&field_offerings_value=All&items_per_page=100 — lists Pinny (Ontario) Limited operating Pinnacle at https://www.pinnacle.ca/en/ (Casino, Sports Betting); AGCO defers its registry to this list (https://www.agco.ca/en/lottery-and-gaming/list-registered-internet-gaming-operators). (3) Pinnacle's own corporate licences page https://www.pinnacle.com/en/corporate/licenses — AGCO licence OPIG1236075 (Ontario), Curaçao, Malta MGA/CL2/1069/2015 (sports betting only), Sweden 18Li12898, Anjouan. (4) Pinnacle.com T&C, latest archived snapshot Mar 8, 2026: https://web.archive.org/web/20260308013232/https://www.pinnacle.com/en/termsandconditions/curacao — operator Ragnarok Corporation N.V. (Curaçao co. 79358), Curaçao Gaming Control Board licence OGL/2023/105/0084; restricted-territories list includes "Province of Ontario" as the only Canadian entry (no Alberta/Canada block as of that date; live pinnacle.com blocks US-based fetches so the archive is the latest verifiable version). (5) Launch dates: https://www.covers.com/industry/ontario-sports-betting-pinnacle-launches-in-igaming-market-october-2022 and https://igamingfuture.com/pinnacle-ca-site-to-go-live-next-week/ — AGCO registration Sept 2022 (registry date 2022-09-07), pinnacle.ca live Oct 26, 2022. (6) Alberta (the adversarial update): AGLC official Gaming Registrations in effect 2026-06-05 https://aglc.ca/sites/aglc.ca/files/2026-06/iGaming_Registrations_2026-06-05.pdf — full 43-entry iGaming-Operator list parsed, no Pinnacle/Pinny entity; AGLC Transition Period guidance (Mar 17, 2026) https://aglc.ca/sites/aglc.ca/files/aglc_files/AGLC%20iGaming%20Guidance%20Document%20-%20Transition%20Period%20Final.pdf — unregulated operators must apply and cease taking Alberta bets by July 13, 2026 (extension max Oct 13, 2026; failure may mean unsuitability); launch date July 13, 2026 per https://www.gamingintelligence.com/legal/228611-canadas-alberta-to-open-regulated-igaming-market-on-july-13/ and https://www.covers.com/industry/alberta-registrations-list-growing-sports-betting-igaming-launch-june-2026 (Pinnacle absent from named registrants). Verdict: claim confirmed as of today, but the "every province" part expires July 13, 2026 for Alberta, and the Curaçao licence detail is updated to GCB OGL/2023/105/0084 under Ragnarok Corporation N.V.

### Pinnacle Ontario crypto ban — vote 1 — **confirmed**
Corrected/current fact: Confirmed as stated, current as of June 2026: Ontario's regulated iGaming framework bans crypto deposits — AGCO Registrar's Standards for Internet Gaming, Standard 5.69 (Deposits), states "Cryptocurrency is not legal tender and shall not be accepted" (standards last updated May 14, 2026; the 2026 changes concerned self-exclusion, not payments). Pinnacle's Ontario product pinnacle.ca (listed in iGaming Ontario's authorized-operator directory) is therefore fiat-only — reviews of the Ontario cashier list only Visa, Mastercard, Interac/Interac e-Transfer, iDebit/Instadebit, MuchBetter, ecoPayz. Pinnacle's crypto rails (Bitcoin, USDT Tether, Litecoin via BitPay/third-party exchanges) exist only on international pinnacle.com, which serves non-Ontario players (including rest-of-Canada — it even offers Interac e-Transfer). Two refinements for a crypto-funded Ontario bettor: (1) the ban is regulator-level, so NO AGCO-licensed Ontario book takes crypto, not just Pinnacle; (2) even on international Pinnacle, crypto deposits are converted to the account's fiat currency by third-party exchange providers — Pinnacle holds no crypto balances, and Ontario residents are required to use pinnacle.ca rather than the international site.

Evidence: PRIMARY SOURCES CHECKED: (1) AGCO Funds Management standards page — Standard 5.69 (Deposits) note verbatim: "Cryptocurrency is not legal tender and shall not be accepted" — https://www.agco.ca/funds-management; full Registrar's Standards for Internet Gaming doc shows last update May 14, 2026, with 2026 revisions limited to Centralized Self-Exclusion (no payment-rule change) — https://www.agco.ca/en/book/export/html/245361 and https://www.agco.ca/en/lottery-and-gaming/guides/registrars-standards-internet-gaming. (2) iGaming Ontario regulated-market directory (44 operators / 78 sites as of June 8, 2026) lists Pinnacle with site pinnacle.ca — https://igamingontario.ca/en/player/regulated-igaming-market. (3) Pinnacle international crypto rails: live pages https://www.pinnacle.com/en/payment-options/bitpay and https://www.pinnacle.com/en/payment-options/usdt_tether; Wayback snapshot of https://www.pinnacle.com/en/payment-options (2025-10-12, http://web.archive.org/web/20251012215336/https://www.pinnacle.com/en/payment-options) contains bitcoin/USDT/Tether/Litecoin/cryptocurrency alongside Interac e-Transfer; Pinnacle help/payment FAQs confirm crypto deposits are converted to fiat account currency by third-party exchanges (no BTC/USDT account currency). Direct fetches of pinnacle.ca/payment-options were bot-blocked (HTTP 502) and no Wayback snapshot exists, so the Ontario cashier list was corroborated via Ontario-specific reviews: next.io ("In Ontario, the deposit options are limited to Visa, Mastercard, Interac, MuchBetter, and Instadebit") https://next.io/betting-sites-on/pinnacle/ and ontariobets.com (Visa/MC, ecoPayz, iDebit, Instadebit, Interac, MuchBetter; no crypto mentioned) https://www.ontariobets.com/pinnacle. (4) Claimed source checked directly — https://www.canadasportsbetting.ca/online-sportsbook-reviews/deposit-methods/bitcoin.html states Ontario "does not allow the use of Bitcoin or any other cryptocurrencies... in accordance with the AGCO and iGaming Ontario" but does not itself distinguish pinnacle.ca from international Pinnacle; the distinction is established by the primary sources above. ADVERSARIAL CHECK: searched for 2026 regulatory changes permitting crypto — none found; articles claiming Ontario operators "added BTC/ETH rails" (coinpedia.org, coinranking.com guest/SEO posts) describe offshore sites and are contradicted by the live AGCO standard.

### Pinnacle API closure — vote 1 — **confirmed**
Corrected/current fact: Confirmed as stated and still current as of June 2026: Pinnacle's official API documentation README (github.com/pinnacleapi/pinnacleapi-documentation) states verbatim "Access to Pinnacle API suite has been closed for the general public since July 23rd, 2025." Remaining access is bespoke — "We offer bespoke data services for select high value bettors & commercial partnerships. We also support academics and pregame handicapping projects." — applied for by emailing a short use-case description to api@pinnacle.com. Ordinary customers cannot self-serve odds or bet-placement API access. (Minor context: this is Pinnacle's second closure — public access was also restricted circa 2019, partially clarified in 2022; July 23rd, 2025 is the operative current date.)

Evidence: (1) Primary source fetched directly: https://raw.githubusercontent.com/pinnacleapi/pinnacleapi-documentation/master/README.md — contains every quoted fragment word-for-word (closure since July 23rd, 2025; "select high value bettors & commercial partnerships"; "academics and pregame handicapping projects"; apply via api@pinnacle.com). Same text on the rendered repo page https://github.com/pinnacleapi/pinnacleapi-documentation. (2) Officialness: https://pinnacleapi.github.io/ redirects to that GitHub repo; commits authored by "Pinnacle API"; pinnacle.com/API/ indexed with the repo title (pinnacle.com itself returned HTTP 502 to fetcher). (3) Date corroboration via commit history https://api.github.com/repos/pinnacleapi/pinnacleapi-documentation/commits?path=README.md — "API Status details change" 2025-07-04 and commits dated exactly 2025-07-23; later commits (2025-10-16, 2026-03-31) left the closure statement intact, so it is current as of June 2026. (4) Independent corroboration of enforcement and no 2026 reversal: https://odds-api.io/blog/pinnacle-api-shutdown-alternatives (July 2025 shutdown, providers losing access, only select HVB/commercial partners retained) and Arbusers thread title "Access to Pinnacle API closed since July 23rd, 2025" (https://arbusers.com/access-to-pinnacle-api-closed-since-july-23rd-2025-t10682/ — body 403 to fetcher); web searches found no announcement of reopened general-public access.

### Pinnacle Solution is B2B — vote 1 — **confirmed**
Corrected/current fact: Substance confirmed, source URL and one detail updated (as of June 2026): Pinnacle Solution is Pinnacle's B2B brand — an iFrame API odds/sportsbook integration and turnkey sportsbook for licensed operators (launched 26 Apr 2018, contact b2b@pinnaclesolution.com) — with no individual-bettor subscription. The claimed URL https://www.pinnacle.com/en/solution/ is now a 404; current official sources are https://www.pinnaclesolution.com/en and the press release at https://www.pinnacle.com/en/corporate/press/press-release/pinnacle-launches-pinnacle-solution. For a solo quant the realistic automation routes are exactly as claimed, and the api@pinnacle.com leg is now even stronger: Pinnacle's official API docs state public API access has been CLOSED since 23 July 2025, leaving only bespoke access (select high-value bettors, commercial partnerships, academics, pregame handicapping projects) via a use-case email to api@pinnacle.com. PS3838 is accurately characterized: a Pinnacle-powered white-label, Asian-facing, B2B/agent-only brand (no direct retail registration, Curacao-licensed) reachable only through betting brokers (BetInAsia, AsianConnect, Sportmarket, VOdds, Piwi247, Brokerstorm), with its own official betting API (api.ps3838.com, docs at ps3838api.github.io). One practical refinement: broker choice matters for automation — Sportmarket explicitly provides no API support, while BetInAsia accounts include API access (e.g., smartbet.io automation).

Evidence: Checked primary sources directly. (1) Claimed source https://www.pinnacle.com/en/solution/ — fetched, returns HTTP 404 (dead). (2) Official Pinnacle press release https://www.pinnacle.com/en/corporate/press/press-release/pinnacle-launches-pinnacle-solution — Pinnacle Solution launched 26 Apr 2018 as a B2B platform; two core products (iFrame API + turnkey sportsbook); contact b2b@pinnaclesolution.com; no individual access. (3) Official site https://www.pinnaclesolution.com/en — live and indexed as the B2B home ("partners", b2b@pinnaclesolution.com); direct fetch from this environment was connection-refused (likely bot/geo block), so content corroborated via search index + press release. (4) Pinnacle's official API repo https://github.com/pinnacleapi/pinnacleapi-documentation/blob/master/README.md — quote: "Access to Pinnacle API suite has been closed for the general public since July 23rd, 2025"; bespoke data services for "select high value bettors & commercial partnerships," academics and pregame handicapping projects; apply with use case to api@pinnacle.com. FAQ (same repo, FAQ.md): esports endpoints require b2b@pinnacle.com authorization. (5) PS3838: https://bookie.broker/ps3838/ — "white-label version of Pinnacle," "no direct registration option on the website, accounts... exclusively possible through partnering brokers" (lists Asianconnect, BetInAsia, Sportmarket, Piwi247, Brokerstorm, Vodds); https://help.sportmarket.com/en/articles/7181624-ps3838-powered-by-pinnacle — "PS3838 Direct Bookmaker Account... powered by Pinnacle," individuals activate via the broker, "Sportmarket does not provide API support" though PS3838 itself offers "optional API access"; https://betinasia.com/ps3838-agent/ (via search) — BetInAsia PS3838 login includes API access / smartbet.io automation; official PS3838 API docs exist at https://ps3838api.github.io/docs/ and https://www.ps3838.com/static/index.php/en-us/help/api-user-guide-en-us (endpoints on api.ps3838.com). Direct fetches of ps3838.com (empty/JS-rendered) and betinasia.zendesk.com (403) were blocked, so those legs rest on the broker help pages and official API docs above.

### Pinnacle winners-welcome policy — vote 1 — **confirmed**
Corrected/current fact: Pinnacle's "Winners Welcome" positioning is real, live as of June 2026, and has stood publicly for 13+ years — but with three refinements: (1) The claimed URL (pinnacle.com/betting-resources/en/educational/winners-welcome-at-pinnacle) is live but its current text promises HIGHER limits, not no limits ("we are not trying to restrict your actions as a player just because you might be winning"; "Pinnacle's strategy is not to limit sharp players, but rather to learn from them"; examples: $250k Super Bowl LVIII, $500k World Cup spreads) and does NOT mention arbitrage; the explicit arbitrage tolerance lives on pinnacle.com/en/why-pinnacle ("Pinnacle is one of the few online bookmakers that welcomes arbitrage betting... happy to take bets that are part of an arbitrage strategy"), and the explicit "doesn't close winning accounts" language is the live title of its companion article (the maths-behind piece). (2) The claimed URL itself only dates to ~2024 (earliest archive 2024-05-26); the decade-plus history attaches to the policy, verified via archived Pinnacle Sports pages from Feb 2013 ("We won't close arbitrage bettors accounts, or restrict their activity") and 2016 ("we don't restrict or ban successful players"). (3) It remains marketing, not contract: Pinnacle's current Terms reserve the right to "refuse, restrict, cancel or limit any bet at any time for whatever reason" and to "set further limits on gaming accounts, restrict access or close gaming accounts," and practitioner forums contain disputed reports of limiting — consistent with the claim's framing as "the book's own claim." Its market-maker archetype status is corroborated by independent 2026 reviews and the academic use of Pinnacle closing lines as an efficiency benchmark.

Evidence: (1) Fetched the claimed URL live (2026-06-10) via curl and extracted the full article body from embedded __NEXT_DATA__ JSON: https://www.pinnacle.com/betting-resources/en/educational/winners-welcome-at-pinnacle — confirms live winners-welcome text ("not trying to restrict your actions as a player just because you might be winning"; "strategy is not to limit sharp players"), frames policy as higher (not unlimited) limits, contains no mention of arbitrage; hero image asset dated 2025-02. (2) Fetched https://www.pinnacle.com/en/why-pinnacle live — explicit arbitrage tolerance: "Pinnacle is one of the few online bookmakers that welcomes arbitrage betting"; "Most bookmakers... will ban anyone who does it. This isn't the case at Pinnacle." (3) Fetched https://www.pinnacle.com/betting-resources/en/educational/the-maths-behind-pinnacles-winners-welcome-policy/n6rjx78p6nrd6zyk — live HTML title "Why Pinnacle doesn't close winning accounts | Profitable bettors welcome" (author Joseph Buchdahl). (4) Wayback CDX: earliest snapshot of the claimed URL is 2024-05-26 (page is new). (5) Wayback primary evidence the POLICY is 13+ years old: http://web.archive.org/web/20130213134746/http://www.pinnaclesports.com:80/betting-promotions/arbitrage-friendly ("Pinnacle Sports is the only bookmaker to welcome arbitrage betting. We won't close arbitrage bettors accounts, or restrict their activity" — Feb 2013, with "Winners Welcome" listed as a sibling promotion in the same nav) and https://web.archive.org/web/20160608065232/http://www.pinnacle.com/betting-promotions/winners-welcome ("Winners Are Welcome — Unlike other bookmakers, we don't restrict or ban successful players", June 2016). (6) Counter-evidence checked: Pinnacle T&C (https://www.pinnacle.com/en/termsandconditions/curacao, live page bot-blocked 502/15-byte response, clauses obtained via search excerpts) reserves right to "refuse, restrict, cancel or limit any bet at any time for whatever reason" and to "set further limits on gaming accounts, restrict access or close gaming accounts"; practitioner skepticism threads exist (https://www.sportsbookreview.com/forum/sportsbooks-industry/1407405-pinnacle-doesn-t-limit-winning-players-is-lie, https://arbusers.com/pinnacle-limiting-winners-t10780/). (7) Third-party archetype corroboration: Odds Shark 2026 review (https://www.oddsshark.com/sportsbook-review/pinnacle-sportsbook), Punter2Pro 2026 (https://punter2pro.com/pinnacle-sports-review/).

### Pinnacle margin class — vote 1 — **confirmed**
Corrected/current fact: Confirmed, with a live-measured refinement (2026-06-10, from Pinnacle's own production odds API). Pinnacle's main-tour ATP/WTA singles moneylines currently price as a ~102.8-103.5% two-way book (margin ~2.8-3.5%) on day-ahead lines: across all 25 main-tour matches up (ATP Stuttgart, ATP 's-Hertogenbosch, WTA 's-Hertogenbosch, WTA London/Queen's), ATP median book = 102.99%, WTA median = 103.38%; example: Hijikata +199 / Tiafoe -228 = 102.96% book. So "roughly 2-3% / the 102-103% class" is accurate for ATP and about half a point optimistic for WTA and for day-ahead (vs closing) lines — "102.5-103.5%, compressing toward ~102.5% at closing and at larger events" is the precise current statement. Two refinements matter for a tennis model: (1) margin widens on extreme favorites (Medvedev -1086/+686 = 104.29% book), and (2) the low-margin class applies ONLY to main-tour singles — measured live, ATP Challenger ≈ 103.8%, WTA 125 ≈ 104.7%, ITF ≈ 106.3% (median), doubles ≈ 105-107%, so do not assume 102-103% off the main tour. The "industry standard 5-7%" leg matches Pinnacle's own published comparison (typical Pinnacle margin 2-2.5%; "average bookmaker" 6%; some books price to 110%), though the 2026 industry spread on tennis mainlines is really ~3-10% (e.g., a third-party tracker lists 1xBet at 3.0% tennis margin, Tipbet at 10.1%). The "sharp-book reference price" description stands; no contrary primary evidence found.

Evidence: (1) Checked the claimed source directly: https://www.pinnacleoddsdropper.com/blog/complete-guide-to-pinnacle-sports-betting-strategies-odds-and-tips-for-every-sport-2025 — it does say "margins as low as 2-3% (compared to the industry standard of 5-7%)" but gives NO tennis-specific number, so it cannot carry the tennis claim alone. (2) Primary live measurement: pulled every tennis moneyline from Pinnacle's production guest API (the data source behind https://www.pinnacle.com/en/tennis/matchups/) — endpoints https://guest.api.arcadia.pinnacle.com/0.1/sports/33/matchups?withSpecials=false and https://guest.api.arcadia.pinnacle.com/0.1/sports/33/markets/straight?primaryOnly=true — on 2026-06-10; computed two-way overround from American prices for 195 priced matches; main-tour ATP singles n=12 median 102.99% (range 102.75-104.29%), WTA singles n=13 median 103.38% (102.80-104.26%), ATP Challenger n=12 median 103.83%, WTA 125 n=11 median 104.68%, ITF n=139 median 106.28%, doubles ~105.2-107.4%; all matches were next-day (June 11) lines, i.e., pre-closing. (3) Pinnacle primary doc: https://www.pinnacle.com/en/esports-hub/betting-articles/home/how-to-calculate-betting-margins — states typical Pinnacle margin 2.5% (MLB ML 1.5%, NHL 2%, soccer 2%) vs "average bookmaker" 6% and some books pricing to 110%; Pinnacle's dedicated margins article exists at https://www.pinnacle.com/betting-resources/en/betting-strategy/learn-more-about-pinnacles-margins/lah22jal3xrpkq42 (JS-rendered, body not fetchable here). (4) Industry-spread cross-check: https://www.top100bookmakers.com/betting-margins/ (82-book table; tennis margins from 3.0% (1xBet) to 10.1% (Tipbet); Pinnacle not listed), plus search corroboration that sharp books run 2-4% vs recreational 6-10%. Wayback Machine and oddspedia.com/bookmakers/pinnacle were blocked (403), and pinnacle.com's help-KB margin page 404'd; conclusions rest on the live API measurement plus Pinnacle's own published article.

### Pinnacle limits and re-betting — vote 1 — **confirmed**
Corrected/current fact: Core mechanics confirmed, numbers refined (as of June 2026): Pinnacle does display the maximum stake for each bet directly on the bet slip (official help: "The limit for any given bet will be displayed on your bet slip... limits tend to increase towards the start of the event"), and its long-documented official policy allows re-betting up to the maximum on the same market — immediately every time the price changes, or after "a set period of time has elapsed" at the SAME price if the line has not moved — so cumulative position size is indeed a multiple of the posted per-bet max (Pinnacle itself cites taking bets up to $1,000,000 and a $2,049,000 single-event payout to one bettor). Two refinements: (1) the explicit re-bet wording comes from Pinnacle's 2016 help article whose helpdesk domains are now offline; the current live betting rules do not restate it and add "All bets will be accepted or rejected purely at Pinnacle's discretion" — operationally the policy is still reported as active in 2026, but it is not a currently published contractual right. (2) The dollar figures are review-site folklore, not official: Pinnacle publishes no per-sport maximum table today (limits are dynamic, scale with liquidity, and the bet-slip number is the only authoritative max); the last official per-sport figures (2016-era helpdesk) were NBA $20,000 spreads/$10,000 moneylines/$5,000 totals and NCAA basketball $2,000 — below the claimed ~$30,000 for "major North American mainlines" — and no official tennis maximum exists anywhere; five-figure maxes on Grand Slam mainlines are plausible per 2026 third-party reviews ($30k majors, $50k NFL handicap) but unverifiable from primary sources. For a tennis betting model: treat the posted bet-slip max (or API maxRiskStake) at bet time as the unit, model total capacity as N × that unit via re-betting, and do not hard-code $30k.

Evidence: Checked the claimed source plus six official Pinnacle surfaces (live + archived). (1) Claimed source matches the claim but is an affiliate review (orig. 2016, updated 2026-01-01): https://globalextramoney.com/pinnacle-sports-review. (2) PRIMARY, re-bet policy verbatim — Pinnacle's own help article "Can I make the same bet more than once to increase my potential winnings?" (modified 17/08/16; live until ≥Feb 2023), Wayback snapshot: http://web.archive.org/web/20230201085850/https://en.help.pinnaclesports.com/en/support/solutions/articles/1000189645-can-i-make-the-same-bet-more-than-once-to-increase-my-potential-winnings- — "bet the maximum amount repeatedly each time the price changes... [or] bet again at the same price once a set period of time has elapsed"; same article was mirrored on the successor helpdesk https://help.future.pinnacle.com/en/support/solutions/articles/11000057746-... (domain now unreachable; en.help.pinnaclesports.com is NXDOMAIN — verified via DNS lookup, so both helpdesks are decommissioned). (3) PRIMARY, current rules — https://www.pinnacle.com/en/future/betting-rules: no per-sport max stakes published; only "$250,000" max accumulated multiples winnings/day; "All bets will be accepted or rejected purely at Pinnacle's discretion." (4) PRIMARY, live bet-slip max display — https://www.pinnacle.com/en/esports-hub/help/placing-a-bet: "The limit for any given bet will be displayed on your bet slip once you have selected what you want to bet on." (5) PRIMARY, highest-limits positioning — https://www.pinnacle.com/betting-resources/en/educational/what-can-bettors-learn-from-pinnacles-biggest-ever-payout/3392l676l3h4t2he: "we offer the highest limits online... happy to take bets of up to $1,000,000"; biggest payout $2,049,000 (2011 NFC Championship). (6) PRIMARY, current limits doctrine (published 2025-11-17, body extracted via the site's Next.js data endpoint /betting-resources/_next/data/z8MD4jLGcflXTYjXK3WPm/...) — https://www.pinnacle.com/betting-resources/en/educational/why-pinnacle-offers-higher-betting-limits-than-other-sportsbooks: "Higher betting limits than most competitors... Dynamic limits that increase as market liquidity builds closer to the event"; no dollar figures. (7) Historical official per-sport figures (dead 2016-era helpdesk, via search index): NBA $20k spread/$10k ML/$5k totals (https://en.help.pinnaclesports.com/en/support/solutions/articles/1000115292-when-are-nba-limits-and-odds-available-), NCAA bb $2k/$1k/$500 — below the claimed $30k. (8) Third-party 2026 figures for context only (not primary): https://surebetmonitor.com/knowledge-base/pinnacle-sports-betting-limits/ ($30k majors incl. tennis), https://ghanasoccernet.com/uk/wiki/pinnacle-betting-limits/ ($50k NFL handicap, $30k EPL/MLB). No official tennis maximum found in any current or archived Pinnacle document.