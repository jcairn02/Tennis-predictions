# Historical tennis market data and odds

This is an evidence audit, not a provider selection, architecture approval, or roadmap. The period of interest is **10 September 2025 to 10 September 2026**. Source access and the direct API observations below occurred on 10 September 2026. Prices are displayed subscription prices on that date; taxes, negotiated rights, and download costs may differ.

Historical tennis prices are available from several independent routes, including public Polymarket APIs, licensed Betfair files, bookmaker aggregators, and specialist prediction-market archives. The inherited suggestion that nobody sells timestamped history is not supportable. The difficult question is which source retains the relevant **tennis contract, timestamp, settlement definition, and executable liquidity**, with enough provenance to assess missing data.

## What “historical data” means here

| Data layer | What it establishes | What it does not establish |
|---|---|---|
| Event/market metadata | A market existed; identifiers, participants, description, contract type | That it had quotes, trades, or sufficient liquidity at a chosen time |
| Sporting result | Who advanced, score, retirement/default/walkover state | The contractual payout on every venue |
| Price chart or bookmaker snapshot | A recorded price at an observation time | A continuously executable price, available size, or a fill |
| Matched trade | A historical transaction at a price and size | Orders canceled without execution or the full resting book |
| L2 order book | Displayed quantity at each price level at capture time | Individual queue position, hidden intent, or guaranteed fills after latency |
| Settlement record | Actual payout or void treatment for a specific contract | A complete contemporaneous revision history of its rules |

These distinctions matter particularly for in-play tennis: a point can finish between two snapshots; a market can be suspended while a displayed price remains unchanged. A quote source also needs its capture time, upstream timestamp, suspension state, and the relevant line or period. “Tennis moneyline” alone is an insufficient join key.

## Public Polymarket history: documentation and direct observations

Polymarket's legacy CLOB endpoint accepts an outcome token ID as `market`, explicit Unix-second bounds, and a minute `fidelity`. It returns timestamp/price pairs. The current documentation additionally describes Data API v2 history with cursor pagination, ranges limited to 15 days, and retention tiers: minute data for at least seven days, five-minute for at least 60, thirty-minute for at least 90, and permanent three-/twelve-hour aggregates. Those are retention floors, not a promise that every market has every observation. [Legacy endpoint](https://docs.polymarket.com/api-reference/markets/get-prices-history), [current history documentation](https://docs.polymarket.com/market-data/prices-order-books).

**Actual responses differ materially between these endpoints.** Three conveniently selected resolved tennis moneylines were queried over bounded windows. This is a functional sample, not a random or complete coverage audit.

| Match and requested UTC window | Legacy CLOB `fidelity=1` | Data API v2 | Interpretation |
|---|---|---|---|
| Korea Open Tauson–Joint; 16–22 Sep 2025 | 1,669 points; mean interval 60.00 seconds, maximum 83 | Auto and 10,800-second queries: two observations 12 hours apart; 60-second query empty | Almost year-old minute history was still retrievable through the legacy endpoint |
| Wimbledon Parry–Kalinskaya; 29 Jun–3 Jul 2026 | 2,535 points; mean 60.83 seconds; largest gap 2,213 seconds | Auto and 1,800-second queries: four observations 12 hours apart; 60/300-second queries empty | Dense chart history contains a substantial gap; v2 emptiness does not prove no legacy history |
| US Open Medvedev–Rinderknech; 1–7 Sep 2026 | 2,649 points; mean 60.00 seconds; maximum 104 | Auto: 533 points; 60-second: 2,431; 10,800-second: 17 | Recent v2 history is finer, but requested resolution changes both count and starting observation |

Every request returned HTTP 200. The raw v2 `timestamp` values in these samples are **Unix seconds**; the SDK examples describe converted timestamps in milliseconds/datetimes. In the older samples, the returned `resolution_seconds` value was 10,800 or 1,800 even though adjacent observations were 43,200 seconds apart. Therefore timestamps, actual deltas, and gaps must be inspected independently of the requested or returned resolution. These observations do not establish whether missing buckets were never recorded, removed, aggregated, or omitted for another reason.

The raw bodies, exact URLs, retrieval times and hashes are in [market-history evidence](../../../data/studies/tennis_data_audit/market_history/). The early/recent probes are reproducible with the read-only [PowerShell utility](../../../src/eda/probe_market_history.ps1); `-IncludeJuly` repeats the July case under different filenames. It refuses to replace existing captures. The initial July probe URLs are in `probes.jsonl`.

### Trades and the on-chain reconstruction route

The [public Data API trades endpoint](https://docs.polymarket.com/api-reference/core/get-trades-for-a-user-or-markets) provides condition/token IDs, price, size, timestamps and transaction hashes, but its documented legacy offset and limit are bounded at 10,000. A few pages of this endpoint are not a census of a busy market's history. The [CLOB trades endpoint](https://docs.polymarket.com/api-reference/trade/get-trades) is authenticated user history; its cursor does not make it an unrestricted archive of every trader.

On-chain history is a separate route. [Polymarket's data-resources page](https://docs.polymarket.com/resources/blockchain-data) points to Goldsky, Dune and Allium. A Polygon RPC or these providers can recover matched fills and settlement-related events, with market/token metadata joined separately. On-chain reconstruction cannot recover resting offers that were canceled without ever trading. Transaction/block ordering also differs from matching-engine or local receive time.

| Route | Evidence and useful detail | Limitation |
|---|---|---|
| [Goldsky](https://docs.goldsky.com/chains/polymarket) | Historical backfill and live `order_filled`/`orders_matched` datasets; fast backfill filters use block ranges | Explicit warning: old public subgraphs are incomplete/incorrect after the 28 Apr 2026 migration; metered infrastructure and account required |
| [Dune Polymarket tables](https://docs.dune.com/data-catalog/curated/prediction-markets/polymarket/overview) | Trade-level records, metadata, daily positions, hourly/daily prices; documented roughly daily refresh | Price tables are forward-filled from trades; no L2 reconstruction; query/export entitlement and completeness not tested |
| [Dune trade schema](https://docs.dune.com/data-catalog/curated/prediction-markets/polymarket/market_trades) | Block time/number, transaction/event index, condition ID, asset, maker/taker and amount | The schema's fee description is not a historical fee schedule; validate against period-specific venue records |
| [Allium schema](https://docs.allium.so/historical-data/predictions/schemas) | Separate trades and `market_orderbook` tables; book rows include side, price, quantity, source and ingestion times | Book capture horizon/cadence and tennis coverage are not documented sufficiently here; SQL access is commercial |
| [Polymarket contract registry](https://docs.polymarket.com/resources/contracts) | Current contract identities and links to source/audits | The full-year extraction must include prior contracts, not only today's addresses |

The year crosses the **28 April 2026 CLOB v2 transition**. The official changelog records new exchange contracts, changed collateral, and removal of pre-cutover resting orders. A backtest spanning that date cannot simply replay a preexisting book through the migration. Fee rules also changed during the year; current fee values cannot be retroactively applied to all trades. [Polymarket changelog](https://docs.polymarket.com/changelog/predictions).

[Paradigm's primary research](https://www.paradigm.xyz/2025/12/polymarket-volume-is-being-double-counted) identifies duplicate maker/taker representations in v1 `OrderFilled` events. Summing every emitted row double-counts economic activity. Its [prediction-market dashboard](https://predictions.paradigm.xyz/) is a separate aggregate exploration resource; it is not PMXT and is not a tennis L2 archive. No verified full-year tennis dataset from Flipside was established in this audit; that is an unconfirmed lead, not proof that private access is unavailable.

## Independently archived Polymarket prices and order books

The following are actual documented offerings. Unless marked observed, their coverage and quality assertions are **vendor claims**, and no paid payload was obtained. “Unlimited history” describes an account's lookback entitlement; it does not establish the first captured tennis market or absence of gaps.

| Source | Historical scope and granularity | Access and current displayed cost | Quality and rights audit |
|---|---|---|---|
| [PolymarketData](https://www.polymarketdata.co/) | Claims minute prices, metrics and full L2 from Aug 2025; nominally spans the target year | [Pricing](https://www.polymarketdata.co/pricing): free one-month/10-minute prices without books; $60/month one-month, $120 three-month, $360 unlimited lookback; bulk export by arrangement | Neither tennis payload nor all-market completeness verified. Terms retrieval failed; redistribution and post-subscription retention remain unknown |
| [Telonex](https://telonex.io/data/polymarket) | Off-chain trades, quotes, 5/25/full-depth books from **11 Oct 2025**; on-chain fills from Nov 2022; daily Parquet | [Plans](https://telonex.io/): free metadata, five trial files with account; $99/month single exchange, $199 Pro | The first month of the target year is absent from the stated book window. [Terms](https://telonex.io/terms) permit personal research/trading on personal plans; firms require Enterprise; no raw redistribution |
| [Dome](https://docs.domeapi.io/api-reference/endpoint/get-orderbook-history) | Historical ladders from **14 Oct 2025**, millisecond timestamps and separate `indexedAt`; max 200 snapshots/page | Key required; free tier increased to 10 QPS | [Acquisition notice](https://domeapi.io/blog/dome-joins-polymarket): paid billing canceled Feb 2026; no support/SLA guarantee after 31 Mar. The homepage's 2024 historical-book example conflicts with the endpoint's 2025 start |
| [PMXT archive](https://archive.pmxt.dev/docs/v2-data-overview) | v2 starts **13 Apr 2026 19:00 UTC**; book and delta events in hourly Parquet | Public HTTPS, no credentials; [hosted API](https://www.pmxt.dev/pricing) free 25k monthly credits, $29.99 Starter, $99.99 Pro | Maintainer says v1 missed roughly half of live markets; v2 claims improved subscriptions/redundancy. An hourly file is not an hourly observation. Hosted plans personal-use; SDK MIT license does not independently license archived venue data |
| [Poly Research & Robotics tennis pack](https://www.polyresearchrobotics.com/data/tennis-order-books?tier=tennis-full-932) | **2–21 Jun 2026**, 932 matches: 629 ITF, 192 ATP, 111 WTA; singles/doubles; one-second full-depth snapshots | 100 matches $5, 300 $10, 932 $20/8.9 GB | Claims complete captures through resolution; selection of complete matches can bias research. Token/condition/event fields documented; not independently checked |
| [Resolved Markets](https://resolvedmarkets.com/pricing) | Sports alongside full-depth snapshots; tennis start date not established | Sports excluded from free and $17 Pro; included with $49 Scale/$549 Enterprise monthly | Generic unlimited-history language does not prove any specified tennis period. No tennis payload inspected |
| [Rocklabs](https://github.com/rocklabs-io/polymarket-dataset) | Tick JSONL.zst; overview says Feb 2026 onward while CLOB section says Jan 2026 | Academic/research access by application; separate license | Internal date conflict; no access application or payload inspection. Full-year tennis not established |

The [PMXT v2 public index](https://archive.pmxt.dev/Polymarket/v2) was accessible and displayed actual filenames and sizes. Its rendered listing jumped between dates; that view alone cannot distinguish omitted listing pages from unavailable hours. The [v1 index](https://archive.pmxt.dev/Polymarket/v1) also displayed zero-size entries. Neither a directory listing nor the provider's subscription claim is a measured tennis coverage rate. File integrity, per-token membership, initialized books, reconnect resets, and gap intervals remain to be checked before using these files as execution evidence.

PR&R's [free sports sample](https://www.polyresearchrobotics.com/data/samples) includes tennis but requires an account and a verified Discord link. No account or external contact was created. Its [terms](https://www.polyresearchrobotics.com/terms) describe own research/bot development, prohibit resale without permission, retain upstream terms, and acknowledge possible gaps. This limits how strongly to read the sales page's “no gaps” claim.

Several highly visible search results are unsuitable for the tennis requirement. [PolyOrderbooks](https://polyorderbooks.com/polymarket-data-download) has real public samples, a DOI and CC BY 4.0 material, but its documented markets are crypto. [DepthFeed](https://polymarketpricedata.com/historical-data) likewise lists crypto contracts. [LuciferForge/ProtoDex's archive](https://github.com/LuciferForge/polymarket-historical-data) advertises March–June 2026 price snapshots and explicitly reports that approximately 94% of its book rows are nominal placeholders. These may help inspect schemas; none establishes tennis execution history for the year.

## Historical bookmaker and exchange odds

### Betfair

Betfair is a documented source of timestamped **tennis exchange** history, including in-play data. The [official specification](https://historicdata.betfair.com/files/Betfair-Historical-Data-Feed-Specification.pdf) says history begins May 2015, with Australia/New Zealand markets from October 2016. The [official automation hub](https://betfair-datascientists.github.io/modelling/dataSources/) describes the stream archive as beginning in 2016. Treat this as a start-date discrepancy to resolve per package, not as a reason to discard the well-documented 2025–2026 route.

| Package | Timing/content documented | Research consequence |
|---|---|---|
| BASIC | Free; minute last-traded prices; no traded volume | Useful price-history baseline; cannot measure spread or depth |
| ADVANCED | One-second updates; prices and traded volumes; best-available back/lay fields | Better microstructure information, but not the complete PRO ladder |
| PRO | 50-millisecond stream interval described by hub; all available back/lay levels and traded price-volume fields | Appropriate type of input for depth research; still needs stream reconstruction, suspension handling and latency assumptions |

Files use stream-like JSON in compressed archives. Metadata includes event/selection IDs, market type, scheduled start, in-play state, delay and settlement status. Use the distinct market type and handicap, not just participant names. Current paid tennis totals were not visible without selecting a package in the account portal; inventing a single monthly price would be misleading. [Download instructions](https://support.developer.betfair.com/hc/en-us/articles/360000402211-How-do-I-download-view-Betfair-Historical-Data), [historical download API](https://support.developer.betfair.com/hc/en-us/articles/12859956891932-How-Can-I-Make-HTTP-Requests-to-the-Historical-Data-API).

The download API operates on packages already added to the account's purchased data. This is not the same purchase as a live trading API key. No account, package purchase, or tennis payload inspection occurred here; a catalogue-level count of tennis moneylines/sets/totals across the target year remains unknown.

### Bookmaker aggregators and private feeds

| Source | Actual history and tennis scope | Access/quality implication |
|---|---|---|
| [The Odds API historical](https://the-odds-api.com/historical-odds-data/) | Featured-market snapshots from 6 Jun 2020; every five minutes since Sep 2022; additional markets from 3 May 2023 | Paid plans; snapshots closest at/before query time. A historical event must have been present in the feed then |
| [The Odds API tennis](https://the-odds-api.com/sports/tennis-odds.html) | Grand Slam history as early as 2020; current Grand Slams, ATP/WTA 500/1000; mainly moneyline, limited game spreads/totals | Does not claim full ATP250/Challenger/ITF or doubles archive. Per-book/competition inception dates need payload audit |
| [Tennis-data.co.uk](https://www.tennis-data.co.uk/alldata.php) | ATP result files from 2000, odds from 2001; WTA 2007 onward; season Excel and tournament CSV | Excellent inexpensive comparison lead, but a row of bookmaker odds is not an intraday sequence or depth record; companion file audit covers payload quality |
| [OpticOdds endpoint](https://developer.opticodds.com/reference/get_fixtures-odds-historical) | Says pre-match only and rolling two-month retention; `include_timeseries` requires separate permission | **Conflicts with [marketing](https://opticodds.com/historical-odds)** claiming years and changes through settlement. Do not assume a standard API license supplies a year of in-play tennis |
| [TxODDS / Tx LAB](https://txodds.net/our-products/) | Dedicated historical odds product; provider names tennis ATP/WTA/Grand Slams and claims decades/millions of fixtures | Quote-only; per-tennis year/book/market/granularity not established. “25 years” on football-focused pages must not be assigned to tennis |
| [BettingIsCool Pinnacle Data API](https://api.bettingiscool.com/) | Overall pre-match archive since 2021; live and specials begin Mar 2026; chronological movements/open/close/settlements | €99/€199/€299/€599 monthly. Tennis's dynamic coverage row was not exposed; exact tennis dates/markets and feed permissions remain unknown. De-vigged “true” odds are derived estimates |
| [Pinnacle official API](https://github.com/pinnacleapi/pinnacleapi-documentation) | General public API closed 23 Jul 2025; bespoke commercial, academic and pregame projects can apply | Direct private data access is a real lead, but a live snapshot/delta API is not proof of an arbitrary historical archive. No application sent |
| [OddsPapi](https://oddspapi.io/blog/historical-odds-csv-excel-backtesting/) | Per-fixture timestamped history arrays; tennis sport ID documented; v4 allows three books per call | Free historical access advertised, with 250 monthly free requests elsewhere in provider docs. Exact tennis/book history start and completeness unverified; v4/v5 documentation differs |
| [BetsAPI](https://betsapi.com/docs/events/) | Broad event history from Sep 2016; aggregated events product includes only 1–3 main markets | [Odds endpoint](https://betsapi.com/docs/events/odds.html) supports timestamps and reversed-match flags, but book coverage varies. Pinnacle is in the enum while the coverage table says no; Polymarket was added Jan 2026 |

The Odds API's [current pricing](https://the-odds-api.com/) starts at $30/month for 20,000 credits, then $59/100,000 and $119/5 million. A featured historical request costs ten credits per region per market; exhaustive five-minute downloads across many tournament keys can consume substantially more than a one-price-per-match study. Its [technical documentation](https://the-odds-api.com/liveapi/guides/v4/) warns that historical errors can persist even after live data is corrected and that sports/books appear only from their ingestion date. Its [31 August 2026 terms](https://the-odds-api.com/terms-and-conditions.html) explicitly allow indefinite retention and model training while prohibiting standalone raw-data redistribution. These are unusually useful rights details; the other vendors' entitlements should not be inferred from them.

OpticOdds' [getting-started guide](https://developer.opticodds.com/docs/odds-api-getting-started-guide) includes tennis and describes historical changes more broadly than the endpoint page. An all-fixtures history can also include fixtures with no odds. The discrepancy requires a concrete tennis export/entitlement statement, not choosing whichever marketing claim is more convenient. OddsJam retail subscription prices quoted by competitors are not evidence of what an OpticOdds raw-data license costs.

The [companion public-data audit](public-tennis-data.md) measures a material change in the **inherited local tennis-data.co.uk snapshots**, not a newly fetched current feed. Nonmissing Pinnacle winner odds fall from 2,534/2,644 ATP rows and 2,391/2,505 WTA rows in 2025 to 71/1,296 ATP and 101/1,248 WTA rows in the June 2026 snapshots. The last nonmissing Pinnacle date is 13 January 2026 for ATP and 14 January for WTA. The old suggestion that these columns remain broadly available through February is not supported by those files. This is not evidence that every Pinnacle feed stopped on those dates; it is evidence that blindly concatenating seasons creates a serious source-availability shift.

### Web archives and other exchanges

[OddsPortal tennis](https://www.oddsportal.com/tennis/) and [BetExplorer tennis](https://www.betexplorer.com/tennis/) expose broad competition/match archives, including lower tours and doubles. Their pages are useful for checking individual identities, results and quoted bookmaker odds. They are related evidence sources rather than automatically independent corroboration: BetExplorer identifies cooperation with OddsPortal for odds. An old result page, such as [Long Island 1996](https://www.betexplorer.com/tennis/atp-singles/long-island-1996/), does not establish that bookmaker prices from 1996 are available. Some returned match tables have empty odds columns.

[OddsPortal's terms](https://www.oddsportal.com/terms/) restrict automated extraction; a public page or an open-source scraper is not a licensed bulk dataset. The same caution applies to mirrors and Kaggle/GitHub uploads derived from these sites. No CAPTCHA bypass, authenticated scraping, or third-party resale purchase was performed.

| Exchange lead | Primary evidence | Historical limitation |
|---|---|---|
| [Matchbook](https://developers.matchbook.com/reference/get-events) | Event states include closed/graded, and current prices can include depth | `before`/`after` refer to event start. These parameters are not an observation-time replay API; year-long tennis L2 archive not verified |
| [Smarkets](https://help.smarkets.com/hc/en-gb/articles/34720906181021-Smarkets-API-Documentation-Resources) | Explicitly documents order books and price history; API application route | Publicly accessible material did not establish oldest tennis date, sampling, depth retention or bulk export rights |
| [BETDAQ](https://api.betdaq.com/v2.0/docs/WhatWebMethodsAreAvailable.aspx) | Current prices, changes and market-withdrawal history | Withdrawal history is not historical odds. [Access](https://api.betdaq.com/v2.0/Docs/Intro.aspx) requires a funded active account and authorization; no verified complete tennis archive found |

These are bounded unknowns. They should not be rewritten as “the data does not exist.”

## Settlement comparability: the same match can have different payoffs

Observed Polymarket rules are per-market evidence. [Parry–Kalinskaya, 1 July 2026](https://polymarket.com/sports/wimbledon/wta-parry-kalinsk-2026-07-01) uses a seven-day delay condition. [Parry–Vekic, 24 August 2026](https://polymarket.com/sports/wta/wta-parry-vekic-2026-08-24) uses a fourteen-day deadline. Both award the moneyline to the advancing player after a started match ends in retirement/default/disqualification; a pre-start walkover resolves 50–50. These examples are not a universal rule for all historical contracts.

An early-period counterexample proves why the distinction matters: [China Open Polina Kudermetova–Sofia Kenin, September 2025](https://polymarket.com/event/wta-kudermetova-vs-kenin-2025-09-27) explicitly awards a walkover to the player advancing to the next round. It also uses a seven-day unresolved condition. Therefore even the pre-first-serve walkover payoff changes across the year; a present-day rule template would mislabel at least some earlier contracts. The precise rollout date and exceptions have not been established.

| Situation | Sampled Polymarket moneyline | Other observed contract/rule | Consequence for labels |
|---|---|---|---|
| Retirement before a completed first set, but after play starts | Advancing player wins | [Betfair Exchange](https://support.betfair.com/app/answers/detail/exchange-tennis-rules/) and [Pinnacle](https://www.pinnacle.com/en/future/betting-rules/) require a completed set for moneyline action; otherwise void | Sporting advancement must not directly overwrite every venue's settlement |
| Walkover before first serve | 0.50/0.50 in the July/August 2026 examples; advancing player in the September 2025 counterexample | Stake-return/void rules are venue-specific | Preserve the historical contract; a 0.50 payout is not a refund of the acquisition price |
| Incomplete match | Moneyline may settle to advancing player | [Medvedev–Rinderknech exact-score contract](https://polymarket.com/sports/atp/atp-medvede-rinderk-2026-09-04) explicitly includes `Not Completed`; completion contract has different payout | Winner, exact set score and completion are different prediction targets |
| Delayed match | Seven or fourteen days in observed contracts | Pinnacle current tennis rules specify seven days | Preserve the actual contract deadline and historical rules version |
| Changed match length/surface | Read individual description | Betfair explicitly distinguishes length changes and surface changes | Event identity alone does not establish equivalent contracts |

For example, buying a share at 0.80 and receiving 0.50 loses 0.30 per share before fees; a sportsbook void normally returns the stake. Treating both as “push/zero return” would fabricate backtest returns. Similarly, normalizing two bookmaker implied probabilities does not remove settlement-rule differences or turn sampled bookmaker quotes into Polymarket bid/ask depth.

The minimum evidence needed to align a market to a sporting record is: provider IDs; tournament/edition; participants and pairings; round/draw; originally scheduled and actual start times; market family; line/period; outcome-token mapping; rules text/version; retirement/walkover/default status; actual payout; and the timestamp at which every input was available. Preserve unresolved joins. This is an audit criterion, not an approved implementation schema.

## Evidence conclusions and unresolved questions

1. **Timestamped history exists.** Public legacy Polymarket minute prices were directly observed for an almost year-old tennis match. Betfair and several paid/free aggregators document additional history. The unknown is coverage and fitness, not the existence of any history.
2. **Full-year tennis L2 remains unproven.** PolymarketData's August 2025 claim nominally covers the year; Telonex/Dome start in October; PMXT and PR&R cover later periods. None of the paid tennis depth payloads was independently audited here.
3. **Fine-history absence is endpoint-specific.** The direct legacy/v2 contradiction is substantial enough that a single empty call cannot be used as a global retention conclusion.
4. **Market breadth must come from the Polymarket census.** Main-tour bookmaker coverage cannot be assumed to cover ITF, qualifying, doubles, completion, set totals and exact-score markets. Per-source coverage should be measured against those specific market IDs.
5. **Rights are part of data quality.** Personal research permission, internal commercial modeling, post-subscription retention and redistribution are different entitlements. Public availability and a paid invoice alone do not establish all four.

Before any source can be described as covering the intended research universe, unresolved evidence includes per-token start/end/gap distributions, full-year market membership, schema changes, exact timestamp meaning, correction/revision behavior, settlement-version history, provider match-join errors, and license scope. These are outstanding questions; they are not a proposed timeline or approved procurement plan.

## Source inventory

The linked primary references above are the sources for their adjacent claims. The machine-readable [market source register](market-sources.json) contains 39 source entries with retrieval date, granularity, access, rights, evidence status and limitations, including investigated leads that do not provide demonstrated tennis history. Direct observations and documentation claims are intentionally kept separate.
