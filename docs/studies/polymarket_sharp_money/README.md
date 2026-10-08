# How beatable is Polymarket tennis? Sharp and casual money

**Polymarket tennis can be beaten before the match, but narrowly and by few accounts.** Every bet placed before the start of 27,968 settled matches ($574M) was valued at the closing price, the book's midpoint in the last minute before the scheduled start. Each account was sorted using only its other matches. 831 of the 18,804 accounts with 10+ pre-match matches (4.4%) clearly beat the closing price; 2,815 (15%) clearly lose to it. On matches they were not sorted on, the clear winners beat the close by +1.26¢ per $1 bet (range +0.97 to +1.58), +0.93¢ after the fees they paid. Clear losers gave up 1.44¢ (2.46¢ after fees). The closing price is accurate: favourites priced at 74.7¢ on average won 75.1% of the time, and every price band and level of play is within about 1.5 points.

**By level of play the winners' edge is similar, 1–2¢ per $1 before fees.** It is highest at Challenger and WTA 125 events (+1.75¢, +1.33¢ after fees, with narrow ranges; +1.62¢ with a close 30 minutes earlier). It is lowest and least certain at the Grand Slams (+0.68¢, not clearly above zero after fees, though +1.13¢ with the earlier close). What differs is the pool: $202M bet before Grand Slam matches, $76M before Challenger and WTA 125 matches, $7M before ITF matches. The lower the level, the more of the money comes from accounts that beat the close: 22% at the Slams, 31% at Challenger and WTA 125, 32% at ITF.

**Status: study, not a decision.** It measures who beats Polymarket's pre-match tennis prices and by how much; it does not choose a market, a strategy or a venue.

| Item | Where |
|---|---|
| Report for readers (HTML: how beatable, by level of play, in plain language) | [report.html](report.html) |
| Trade download (adapter) | [`src/ingest/public_dump/polymarket_trades.py`](../../../src/ingest/public_dump/polymarket_trades.py) → `data/raw/public_dump/polymarket_trades/` (raw bodies, receipts) and `data/dump/odds/polymarket/trades/` (staged fills) |
| Positions, fees, market table | [`build_positions.py`](../../../src/eda/polymarket_sharp_money/build_positions.py) → `markets.parquet`, `wallet_markets.parquet`, [build_summary.json](../../../data/studies/polymarket_sharp_money/build_summary.json) |
| **Pre-match closing-price analysis** | [`prematch.py`](../../../src/eda/polymarket_sharp_money/prematch.py) → [prematch.json](../../../data/studies/polymarket_sharp_money/prematch.json), [prematch_buffer30.json](../../../data/studies/polymarket_sharp_money/prematch_buffer30.json) (close 30 minutes earlier), `prematch_positions*.parquet` |
| Fee calibration and check | [`calibrate_fees.py`](../../../src/eda/polymarket_sharp_money/calibrate_fees.py) → [fee_timeline.json](../../../data/studies/polymarket_sharp_money/fee_timeline.json); [`check_fees.py`](../../../src/eda/polymarket_sharp_money/check_fees.py) → [fee_check.json](../../../data/studies/polymarket_sharp_money/fee_check.json) |
| Taker/maker check | [`check_taker_order.py`](../../../src/eda/polymarket_sharp_money/check_taker_order.py) → [taker_order_check.json](../../../data/studies/polymarket_sharp_money/taker_order_check.json) |
| Earlier cut: all money, experience tiers | [`classify.py`](../../../src/eda/polymarket_sharp_money/classify.py), [`composition.py`](../../../src/eda/polymarket_sharp_money/composition.py) → [composition.json](../../../data/studies/polymarket_sharp_money/composition.json) |
| Report rendering | [`render_report.py`](../../../src/eda/polymarket_sharp_money/render_report.py) + [`report_text.py`](../../../src/eda/polymarket_sharp_money/report_text.py) + `report_template.html` |
| Posting versus taking prices | [`maker_economics.py`](../../../src/eda/polymarket_sharp_money/maker_economics.py) → [maker_economics.json](../../../data/studies/polymarket_sharp_money/maker_economics.json), `maker_cells.parquet` |
| Tests | `test/polymarket_sharp_money/` (25 offline tests) and `test/public_data_dump/test_polymarket_trades.py` (5) |

The Parquet tables are gitignored and rebuilt by the scripts; see [LARGE_FILES.md](../../../data/LARGE_FILES.md#6-polymarket-trade-fills).

## Question

How much "sharp" versus "casual" money is there in Polymarket's tennis markets, by event type? On 25 Sep 2026 the owner sharpened the question to: how beatable is tennis on Polymarket, by how much, and at which level of play. The yardstick is the closing price. Accounts are split into those that clearly beat it, those that are unsure, and those that clearly lose to it. Only bets placed before the match count, and behavioural tendencies (taking or posting prices, experience) are not used to sort accounts.

## Data

| Source | What was used | Accessed | Limits |
|---|---|---|---|
| Polymarket Gamma catalog (the project's census of 10 Sep 2026 and its extension of 22 Sep) | Every tennis moneyline with its match scheduled on or before 21 Sep 2026: 35,756 markets requested, 33,694 with trades | 10 and 22 Sep 2026 | Current metadata, not a revision history; tournament level is inferred from names |
| `https://data-api.polymarket.com/trades?market=…&takerOnly=false` | 36,037,873 fill records (taker plus each matched maker order, with account), 36,028 requests, no errors | 25 Sep 2026 | Offset capped at 10,000 per query, so pages are chained by timestamp (`end` is inclusive; repeats removed); fees are not in the records |
| Polymarket price history (`clob.polymarket.com/prices-history`, staged by `polymarket_prices.py`) | Minute-level midpoint of the first outcome, for the closing price | 22 Sep 2026 | 32,435 of 32,801 settled markets have a point in the hour before the start (99% within a minute) |
| `https://data-api.polymarket.com/activity` | Cash actually paid on 303 (calibration) + 70 (independent check) sampled taker fills | 25 Sep 2026 | Samples, not a full reconciliation |
| Polymarket fee documentation, `https://docs.polymarket.com/trading/fees` | Taker fee formula `shares × rate × p × (1 − p)`; maker rebates | 25 Sep 2026 | The per-market schedule in the metadata is the current one, not the one in force at trade time |
| Dump player lists (Sackmann ATP and WTA players, Live Tennis API players) | Gender of ITF matches from the players' full names | on disk | Found for 13,645 of 15,109 ITF markets (90%) |

Polymarket's data is used under its API terms; nothing here is redistributed beyond the project.

## Method (pre-match analysis)

1. **Fills to bets.** Each record becomes the outcome it backs. A BUY of a player at *p* backs that player at *p*; a SELL backs the opponent at 1 − *p*. Outcome indexes come from Gamma's token order; the API's own index was swapped in 109,630 records. Takers are the first record of each transaction, as confirmed in 24,649 of 24,649 transactions against `takerOnly=true`.
2. **Before the match.** Fills before the scheduled start, at 5–95¢: 5,775,178 fills, $574M. In the 30 minutes before the scheduled start prices move a median 0.5¢ (4% of markets more than 10¢); in the 30 minutes after, a median 5¢ (34% more than 10¢).
3. **Closing price and edge.** The closing price is the midpoint in the last price-history point before the scheduled start. A bet's edge is shares × (closing price of the side backed − price paid), which is its expected profit before fees if the close is the true chance. Edges sum to zero across the two sides of every trade: the residual over all $574M is −$5,725.
4. **Fees.** Taken from the data where they show: 1,805,737 taker BUYs from 29 Mar to 28 Apr 2026 received fewer shares than their makers sold. From 28 Apr 2026 11:00 UTC fees are modelled as `rate × p × (1 − p)` in cash (measured start; no cash fee before). Maker rebates (15–25% of fees) are shared by maker volume within each market, an approximation. "After fees" subtracts the fees each account paid and adds its rebates.
5. **Sorting accounts.** Matches are in five groups (by physical match). An account's group for a match comes from its pre-match bets in the other four. Its edge per $1 there has a standard error computed with each match as one observation. **Clearly beats the close**: 10+ other matches, edge ≥ 2 standard errors above 0. **Clearly loses**: 10+, ≤ −2. **Unsure**: everyone else. Whole-year verdicts (every match) count accounts; edges and money shares always use the held-out sorting.
6. **Ranges.** 95%, from 1,000 Poisson bootstrap draws over markets. A level stands alone with 150+ markets and share ranges no wider than ±5 points.
7. **Checks.** Closing-price accuracy (favourite's closing price against how often it won); realised results after fees per group; the whole analysis repeated with the close taken 30 minutes before the scheduled start (`--buffer-minutes 30`).

## Results (pre-match)

### The three groups, all tennis

| Group | Accounts (whole year) | Share of pre-match money | Edge per $1 before fees | After fees | Actual result per $1 after fees |
|---|---:|---:|---:|---:|---:|
| Clearly beat the close | 831 | 23% | +1.26¢ (+0.97 to +1.58) | +0.93¢ (+0.64 to +1.24) | +1.85¢ (−0.95 to +4.30) |
| Unsure | 88,311 (15,158 of them with 10+ matches) | 66% | −0.22¢ (−0.33 to −0.12) | −0.80¢ (−0.93 to −0.70) | −0.73¢ (−1.58 to +0.23) |
| Clearly lose to the close | 2,815 | 11% | −1.44¢ (−1.81 to −1.10) | −2.46¢ (−2.84 to −2.09) | −4.92¢ (−8.60 to −1.18) |

### By level of play (men and women together)

| Level of play | Money bet before matches | Matches | Clear winners (accounts) | Winners' share of money | Winners' edge per $1 | After fees | Losers' edge per $1 | Winners' edge, close 30 min earlier |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| All tennis | $574.4M | 27,968 | 831 | 23% | +1.26¢ (+0.97 to +1.58) | +0.93¢ (+0.64 to +1.24) | −1.44¢ (−1.81 to −1.10) | +1.26¢ (+0.94 to +1.56) |
| Grand Slams | $201.7M | 977 | 506 | 22% | +0.68¢ (−0.04 to +1.27) | +0.37¢ (−0.34 to +0.96) | −1.00¢ (−2.14 to +0.07) | +1.13¢ (+0.31 to +1.66) |
| Masters 1000, WTA 1000 and Finals | $133.4M | 1,577 | 645 | 19% | +1.54¢ (+0.99 to +2.21) | +1.26¢ (+0.72 to +1.92) | −1.07¢ (−1.52 to −0.66) | +1.50¢ (+0.93 to +2.21) |
| 500 events | $57.8M | 955 | 608 | 22% | +1.42¢ (+0.37 to +2.34) | +1.20¢ (+0.14 to +2.14) | −1.72¢ (−2.68 to −0.84) | +0.87¢ (−0.26 to +2.05) |
| 250 events | $69.5M | 1,487 | 663 | 27% | +1.24¢ (+0.78 to +1.76) | +0.88¢ (+0.40 to +1.40) | −1.81¢ (−2.96 to −0.78) | +1.15¢ (+0.53 to +1.79) |
| Qualifying (Slams and tour) | $28.2M | 2,362 | 593 | 30% | +1.69¢ (+1.20 to +2.17) | +1.31¢ (+0.82 to +1.78) | −1.82¢ (−3.24 to −0.66) | +1.19¢ (+0.76 to +1.66) |
| Challenger and WTA 125 | $75.7M | 6,563 | 688 | 31% | +1.75¢ (+1.36 to +2.19) | +1.33¢ (+0.94 to +1.77) | −1.87¢ (−2.23 to −1.51) | +1.62¢ (+1.26 to +1.99) |
| ITF | $7.3M | 12,492 | 279 | 32% | +1.75¢ (+1.01 to +2.61) | +1.14¢ (+0.40 to +2.00) | −2.50¢ (−3.60 to −1.47) | +1.33¢ (+0.55 to +2.53) |
| Doubles, juniors, team events | $0.8M | 1,555 | 211 | 21% | +2.20¢ (+1.20 to +3.04) | +1.66¢ (+0.47 to +2.57) | −4.75¢ (−7.91 to −1.84) | +1.34¢ (+0.07 to +3.26) |

### Men's events only

| Men's level | Money bet before matches | Winners' edge per $1 | After fees | Losers' edge per $1 |
|---|---:|---:|---:|---:|
| Grand Slams, men | $139.3M | +0.50¢ (−0.34 to +1.31) | +0.21¢ (−0.64 to +1.02) | −0.90¢ (−2.52 to +0.65) |
| Masters 1000 and Finals | $90.4M | +1.44¢ (+0.80 to +2.28) | +1.21¢ (+0.57 to +2.04) | −1.01¢ (−1.56 to −0.50) |
| ATP 500 | $33.6M | +1.79¢ (+0.89 to +2.73) | +1.63¢ (+0.74 to +2.58) | −1.85¢ (−3.30 to −0.64) |
| ATP 250 | $48.3M | +1.23¢ (+0.68 to +1.82) | +0.91¢ (+0.36 to +1.51) | −2.05¢ (−3.43 to −1.00) |
| ATP Challenger | $57.8M | +1.63¢ (+1.27 to +2.00) | +1.25¢ (+0.88 to +1.61) | −1.91¢ (−2.30 to −1.51) |
| ITF men | $3.3M | +1.05¢ (+0.32 to +1.88) | +0.41¢ (−0.30 to +1.24) | −1.09¢ (−2.84 to +0.60) |

### What +1.5¢ per $1 means

If the closing price is the true chance of winning, an edge of +1.5¢ per $1 is an expected profit of $1.50 per $100 bet. That is like taking +100 on a bet whose fair price is about −103. It is before fees. Since 28 Apr 2026, accepting a posted price costs 5% × (1 − price) of the amount bet, 2.5¢ per $1 at even money. That is more than the whole edge, so the winners' after-fee figure depends on how often they post their own prices, which is free.

## Posting prices versus taking them

[`maker_economics.py`](../../../src/eda/polymarket_sharp_money/maker_economics.py) → [maker_economics.json](../../../data/studies/polymarket_sharp_money/maker_economics.json). The question was the owner's hypothesis of 25 Sep 2026: posting prices is where the edge is, because makers pay no fee. Each fill's edge against the close is split into the **spread** (midpoint at the fill, from the minute-level price history, minus the price paid) and the **drift** (closing midpoint minus the midpoint at the fill). The split is approximate, but their sum is exactly the edge. Fees and estimated rebates are added. This covers the cash-fee period, 28 Apr – 21 Sep 2026. Figures are per $1, with 95% ranges.

| Pre-match, per $1 | Money | Spread | Drift | Fee or rebate | After fees and rebates |
|---|---:|---:|---:|---:|---:|
| All posted (maker) money | $189.2M | +1.90¢ | −1.64¢ | +0.27¢ rebate | +0.52¢ (+0.19 to +0.86) |
| All taken (taker) money | $228.6M | −1.57¢ | +1.36¢ | −1.45¢ fee | −1.66¢ (−2.01 to −1.34) |
| Clear winners, posting | $66.6M | +2.20¢ | −1.12¢ | +0.26¢ | +1.34¢ (+0.96 to +1.68) |
| Clear winners, taking | $39.9M | −1.31¢ | +2.76¢ | −1.40¢ | +0.05¢ (−0.66 to +0.76) |
| Unsure accounts, posting | $111.1M | +1.71¢ | −1.99¢ | +0.28¢ | −0.00¢ (−0.41 to +0.42) |

* **For accounts that beat the close, posting beats taking by about 1.3¢ per $1.** Their taken bets have the larger edge before fees (+1.46¢, against +1.08¢ posted), but the fee erases it.
* **For everyone else, posting only breaks even.** The market moves against an average maker by about as much as the spread it earns, and the rebate makes up the difference. Takers' fees mostly go to Polymarket: about a fifth comes back to makers as rebates, and that estimate is roughly half of the average maker's result.
* **By level** (all posted money, after rebates): 250 events +1.06¢ (+0.60 to +1.55) and qualifying +1.01¢ (+0.49 to +1.55) are best. Grand Slams +0.38¢ and Masters/WTA 1000 +0.32¢ are not clearly above zero. Challenger and WTA 125 are +0.44¢ (+0.02 to +0.83). ITF is −0.52¢ (−1.54 to +0.38): the spread is 4.2¢, but the drift against makers is 5.0¢.
* **During matches posting is a break-even speed game.** Makers earn a 2.44¢ spread and lose 2.39¢ within five minutes. The actual result after rebates is +0.07¢ (−0.68 to +0.78), against −1.42¢ for takers. Ten accounts supply 60% of in-play maker money, and one account 20%. Before the match the top ten supply 31% (52% at ITF).
* **Actual results** agree where they are precise enough: clear winners posting at Challenger, WTA 125, qualifying and ITF made +2.69¢ per $1 after rebates (+0.32 to +5.41).

## Earlier cut: all money, including bets during the match

The first version of this study sorted all money (before and during matches, $2.53B at 5–95¢) by the wallet's experience and its net profit-and-loss record. In play, most tennis money trades after the scheduled start. On that cut, casual money (wallets with fewer than 10 other matches) was 8.3% of the money at men's Slams, 2.2% at ATP Challengers and 1.5% at men's ITF events, and it lost 5.9¢ per $1 overall (−10.3 to −1.4). Wallets with a winning profit-and-loss record made +1.47¢ per $1 after fees (+1.01 to +1.95). Full tables are in [composition.json](../../../data/studies/polymarket_sharp_money/composition.json), with the split-half reliability test under `reliability`: a wallet's return in one half of its matches predicts the other half with correlation 0.08 at 5+ matches per half and 0.29 at 100+. That noise is why the pre-match analysis uses the closing price, which is far less noisy than win-or-lose results.

Two per-wallet scores were also tried on the main-tour subset and dropped for failing their out-of-sample check (calibration slope 0.18 and about 0.1). Neither script is kept.

## Limitations

* An account is not a person. One bettor can use several accounts, and some of the 831 clear winners cleared the bar by luck. The edges are measured on held-out matches, so they include the lucky ones.
* The closing price is right on average, not in every match. Edges show up over many bets.
* Scheduled, not actual, start times. A match that starts early puts a few bets placed during it into the pre-match count. The 30-minute check leaves the overall answer unchanged and moves the level figures within their ranges.
* "Value taken" and edges are measured at closing prices. Actual results agree in direction but are far noisier.
* Fees after 28 Apr 2026 are modelled. An independent sample of 70 fills matched within $0.0001 a share in 66 cases. Maker rebates are approximate.
* Match-winner markets on international Polymarket only, 18 Sep 2025 to 21 Sep 2026 (ITF from 13 May 2026). Set, total and handicap markets and Polymarket US were not studied.

## Reproduce

```
./python.sh -m src.ingest.public_dump.polymarket_trades --buckets all --workers 8 --rps 14   # about 55 minutes
./python.sh src/eda/polymarket_sharp_money/build_positions.py      # about 3 minutes, 36M fills
./python.sh src/eda/polymarket_sharp_money/prematch.py             # about 5 minutes
./python.sh src/eda/polymarket_sharp_money/prematch.py --buffer-minutes 30 --tag buffer30
./python.sh src/eda/polymarket_sharp_money/maker_economics.py      # about 8 minutes; needs prematch_positions.parquet
./python.sh src/eda/polymarket_sharp_money/classify.py             # earlier cut
./python.sh src/eda/polymarket_sharp_money/composition.py          # earlier cut
./python.sh src/eda/polymarket_sharp_money/render_report.py
./python.sh src/eda/polymarket_sharp_money/calibrate_fees.py --per-cell 4    # live checks; results change with sampling
./python.sh src/eda/polymarket_sharp_money/check_fees.py --per-stratum 2
./python.sh src/eda/polymarket_sharp_money/check_taker_order.py --per-bucket 3
./python.sh -m pytest test/polymarket_sharp_money test/public_data_dump/test_polymarket_trades.py
```

The price history must be staged first (`polymarket_prices.py`, see [LARGE_FILES.md](../../../data/LARGE_FILES.md)). The fee start time (`FEE_CASH_START` in `build_positions.py`) came from `calibrate_fees.py` together with the in-share fee records.
