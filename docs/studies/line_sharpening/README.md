# Polymarket tennis lines in 2026: how much they sharpen between the early market and the close

**Once you can bet $300 at market on both players, the line is already close to its final form.** On the main tour the early market, defined below, opens about a day before the close at the 1000s (the Grand Slams are assumed to match) and 10–14 hours before it at 500s and 250s. At that moment the Slam and 1000 line is statistically level with the closing line (+2.4 milli-log-loss for the early line, range −1.6 to +6.3: a tie). The 500 and 250 line is measurably, but only slightly, worse than the close (+4.9, range +1.9 to +7.7). At Challenger, WTA 125 and qualifying events the early market opens only 1½–4 hours before the close, and by then the line is the close (a tie). ITF markets never offer $300 at market: 3% of them ever did, and half of all ITF markets trade under $15 before the match.

**The market toughens a lot, but almost all of it happens before there is size to bet into.** The first price a market shows is 13–14¢ from its close on average and 80–100 milli-log-loss less accurate. The line at the early market is 1–2.5¢ from the close. For the lower tiers the gap at 12–24 hours out is large (Challenger +19 at 24 hours, ITF +60 at 12 hours), but those books hold a few dollars within a cent of the mid. A softer line is available at a price. Accept an average fill up to 2¢ off the mid instead of 1¢ and the early market opens earlier, on a softer line: 1000s 44 hours out at +30 (range +12 to +49), Challengers 13 hours out at +11.5 (+7.8 to +15.1).

**Volume says when a line has matured, especially lower down.** Twelve hours before the close, a lower-tier market that has not traded yet is 80 milli-log-loss from its close. One with a few hundred dollars traded is 3.5 away. On the main tour the line is within a few milli-log-loss of the close once 5% of its pre-match money has traded, typically $900–1,400 and 14–18 hours out.

**The early line still moves, by about as much as it costs to take it.** Between the early market and the close the main-tour line moves 1.8–2.5¢ on average (median 1–2¢), and 19–29% of lines move 3¢ or more. Since July 2026 a taker pays 5% × (1 − price) of the stake in fees, 2.5¢ per $1 at even money, plus about half a cent of spread. So the early market's softness pays only for someone who can tell which way it will move.

**Betting our model at the early market instead of the close changes nothing measurable** (the owner's follow-up; [section below](#betting-our-model-at-the-early-market-instead-of-the-close)). On 2,933 main-tour matches of 2026, the current best model bet at the early market made the same money as at the close. The difference is $0.00 per 100 matches (range −0.86 to +0.91), and +$0.20 in expectation with the close as the yardstick (range −0.00 to +0.42). Between the two moments the market moves only 7% of the way toward the model. The one systematic effect is market-wide: favourites firm by about half a cent by the close. Backing the model's favourites early and its underdogs at the close is worth +$0.36 per 100 matches in expectation (+0.25 to +0.48), a tie in realized money.

**How to read the numbers.** Accuracy is log loss against the result, in milli-log-loss (thousandths of a nat; lower is better). Every comparison is the log loss of a market's price at some earlier point minus the log loss of the same market's closing price. **Positive means the earlier line was worse: the market toughened by that much.** The 95% range comes from 2,000 bootstrap draws over markets. When it spans zero the two are tied, whatever the sign. "Move" is the average absolute distance from the close in cents of probability.

**Status: study, not a decision.** It describes how Polymarket's tennis lines form. It does not choose a betting time, size, venue or strategy.

| Item | Where |
|---|---|
| PMXT order-book archive adapter (hourly files over HTTP range requests, tennis rows only) | [`src/ingest/public_dump/pmxt_books.py`](../../../src/ingest/public_dump/pmxt_books.py) → `data/dump/odds/polymarket/books_pmxt/`, receipts in `data/raw/public_dump/pmxt_books/` |
| Archive coverage audit (every 8th hour) | [`pmxt_coverage.py`](../../../src/eda/line_sharpening/pmxt_coverage.py) → [pmxt_coverage_summary.json](../../../data/studies/line_sharpening/pmxt_coverage_summary.json) |
| Markets, start of play, closes, price paths, taker orders | [`build.py`](../../../src/eda/line_sharpening/build.py) → `markets.parquet`, `prices.parquet`, `takers.parquet`, [build_summary.json](../../../data/studies/line_sharpening/build_summary.json) |
| Start-of-play check against official first points | [`starts_check.py`](../../../src/eda/line_sharpening/starts_check.py) → [starts_check.json](../../../data/studies/line_sharpening/starts_check.json) |
| Order-book replay, minute by minute | [`books.py`](../../../src/eda/line_sharpening/books.py) → `book_minutes.parquet`, [book_summary.json](../../../data/studies/line_sharpening/book_summary.json); check: [`books_check.py`](../../../src/eda/line_sharpening/books_check.py) → [books_check.json](../../../data/studies/line_sharpening/books_check.json) |
| Early-market onset and the rules that carry it to every market | [`calibrate.py`](../../../src/eda/line_sharpening/calibrate.py) → `book_onsets.parquet`, `early_onsets.parquet`, [calibration.json](../../../data/studies/line_sharpening/calibration.json) |
| Checkpoints and scores | [`evaluate.py`](../../../src/eda/line_sharpening/evaluate.py) → [results.json](../../../data/studies/line_sharpening/results.json) (main close), [results_ext.json](../../../data/studies/line_sharpening/results_ext.json) (true close), `checkpoints.parquet` |
| Betting early versus at the close: sample, model forecasts (local TabPFN-3.5, GPU), betting simulation | [`timing_frame.py`](../../../src/eda/line_sharpening/timing_frame.py) → `timing_frame.parquet`, [timing_frame_counts.json](../../../data/studies/line_sharpening/timing_frame_counts.json); [`timing_local.py`](../../../src/eda/line_sharpening/timing_local.py) → `local/`; [`timing_bets.py`](../../../src/eda/line_sharpening/timing_bets.py) → [timing_results.json](../../../data/studies/line_sharpening/timing_results.json) |
| Shared definitions (tiers, start detector, lookups) | [`common.py`](../../../src/eda/line_sharpening/common.py) |
| Tests | `test/line_sharpening/` (17 offline tests: start detection and validation, lookups, scoring, bootstrap, book arithmetic, replay and its repair, the betting rule) |

## Question

The owner asked on 6 Oct 2026 for a deep dive into Polymarket's 2026 tennis lines: how they sharpen as time passes towards the close, as a function of volume. The opening price does not count, because there is no reasonable liquidity behind it. Instead:

* develop a criterion for the "early" market: enough consistent liquidity to bet more than $300 at market on both sides;
* show how much the market toughens from there to the close, against how tough it already is when it opens;
* split by level of event: lower, higher and highest.

The tiers used here, taken from the earlier Polymarket studies' event types:

| Tier | Levels |
|---|---|
| Highest | Grand Slam main draws, Masters 1000 and WTA 1000, the Finals |
| Higher | ATP and WTA 500 and 250 |
| Lower | Challenger, WTA 125, ITF, and Grand Slam and tour qualifying |

Every table also gives the seven levels separately. ITF is two-thirds of the lower tier's markets and behaves unlike the rest of it, so lower-tier results are best read level by level.

## Data

| Source | What was used | Accessed | Limits |
|---|---|---|---|
| Polymarket market index (Gamma census of 10 Sep 2026 and catalog extensions to 5 Oct 2026; `data/dump/odds/polymarket/`) | Every singles match-winner market listed to start from 2 Jan to 4 Oct 2026 and settled decisively: 33,822 markets | 10 Sep – 5 Oct 2026 | Current metadata, not a revision history. Tier inferred from names (earlier studies) |
| Polymarket minute price history (`clob.polymarket.com/prices-history`, first outcome) | 42.3 million pre-match points; the price at each checkpoint | Topped up 5 Oct 2026 | The series is the book's midpoint when the spread is 10¢ or less; checked against the books below |
| Polymarket trades (`data-api.polymarket.com/trades`, both parties of every fill) | 2.10 million pre-match taker orders: time, side, stake, average and worst price | Topped up 5 Oct 2026 | Fees are not in the records |
| **PMXT order-book archive v2** (`https://r2v2.pmxt.dev/polymarket_orderbook_<YYYY-MM-DDTHH>.parquet`, docs `https://archive.pmxt.dev/docs/v2-data-overview`) | Every book snapshot and level change of every tennis moneyline from 31 Jul 00:00 to 3 Aug 23:59 UTC 2026: 96 hourly files, 32.0 GB read over range requests, 100.6 million tennis rows kept | 6 Oct 2026 | Public HTTPS, no credentials. The hosted plans are for personal use, and the SDK's MIT licence does not by itself license the data, so this is kept for research only. Files exist from 13 Apr 19:00 to 10 Aug 2026 00:00 (later hours return 404; the index page refused connections). Tennis coverage is 75%, with long gaps (below) |
| Official first points (match-timing study links: TDI, the Grand Slams' feeds, the WTA API) | When 2,720 main-tour matches of 2026 really started, to check the start-of-play detector | Links rebuilt 7 Oct 2026, 00:35 UTC (the coordinated Stage 0 rebuild; the first check, on the links of 5 Oct, had 1,896 matches and the same conclusions) | Main tour only |

### The PMXT archive's tennis coverage

`pmxt_coverage.py` read only the `market` column of every 8th hourly file (about 2.5 MB of each file, which averages 408 MB) and compared it with the tennis markets our own trade record shows trading in that hour. Of 27,242 market-hours, 20,441 are in the archive (75.0%). The gaps run long:

* nothing at all from 12 to 29 June (the grass season to the first day of Wimbledon) or from 10 to 14 July;
* partial coverage on 21–22 May, 30 June – 1 July and 8–9 July.

The pattern is a decay followed by a recovery, as if the recorder stopped subscribing to newly listed markets until it restarted. The whole archive is about 1.16 TB. The sample block (31 Jul – 3 Aug) is fully covered. Every audited hour of it held every tennis market that traded.

## Method

1. **Markets.** Singles match-winner markets of the sharp-benchmark study's loader, settled decisively, at a level in the tier table: 33,822. Of these, 431 have no price within the hour before the close and 83 are flagged by the check in point 2, which leaves **33,360** (highest 2,342, higher 2,095, lower 28,923).

2. **When play starts, and the close.** Polymarket's listed start is within 5 minutes of the official first point in only 54% of the 2,720 main-tour matches that could be checked, and 5% of them start more than half an hour after it. At ITF events a quarter of matches are detected starting more than 75 minutes after their listed time. So the start is detected from the price path. Play begins at the first price point from which the price moves at least 4¢ within 5 minutes and 15¢ within 30 minutes, searched from 6 hours before to 30 hours after the listed start. Thin lower-tier books swing like that before play too. A detection 3–7 hours before the listed start is followed by the match being decided (price beyond 3¢/97¢ for good) within 4 hours in only 1–11% of cases, against 90–100% near the listed start. So a detection counts only if the match is decided 0.4–4.5 hours after it (6.5 at a Slam); otherwise the next candidate is tried.

   Against the official first points, the validated start is found in 97% of matches: within 5 minutes in 86%, within 15 in 94%, more than 15 minutes late in 3.2%. The **main close** is the last price at the earlier of 30 minutes before the listed start and 5 minutes before a validated start. It falls after the real first point in 1.4% of checked matches, a median 33 minutes before play. The **true close**, 5 minutes before the validated start, falls after the first point in 4.4%, a median 5 minutes before play. The main close is used throughout and the true close is a sensitivity check (section 7). Markets decided less than 0.4 hours after the main close are left out (83).

3. **Order books.** The archive's events of each market's first outcome are replayed in order. A snapshot replaces the book; a level change sets one level's size. The second outcome's book mirrors the first (its bids are 1 minus the first's asks, same sizes), so one book gives both players; their level-change counts agree to 0.001%. Each level change also carries the exchange's own best bid and ask. The archive sometimes lacks the rows that removed levels: a maker pulling its quotes shows as a jump in the exchange's best price with no removal rows. Left alone, that would leave stale quotes in the replay and overstate depth. So after every row, levels better than the exchange's best are deleted (72,067 times in 20.5 million rows).

   After that repair, the replay's best bid and ask equal the exchange's in 96.0% of sampled minutes. In the other 4.0% the replay's quote is always the worse one: a missing level, which can only understate depth. The replayed mid agrees with Polymarket's minute price to within half a cent in 98.5% of minutes when the spread is 10¢ or less.

   At the end of every pre-match minute the book gives, for each player, the average price of a $100, $300 and $1,000 market buy, and the most that can be bought while the average price stays within 1¢ and 2¢ of that player's mid.

4. **The early market.**
   * A minute is **bettable** when a $300 market buy of each of the two players fills at an average price no more than 1¢ above that player's mid. With a 1¢ spread the best price is half a cent above the mid, so the order fills at the best price with at most half of it one cent worse.
   * The **early market opens** at the first minute from which the market is bettable in at least 90% of the remaining pre-match minutes, and bettable at that minute.

   Variants: 2¢ instead of 1¢, and $100 or $1,000 instead of $300. Minutes before a market's first book in the block count as not bettable. A market listed before the block began is censored and left out of the onset statistics.

5. **From the sample to every market.** The books cover four days. The onset is carried to every 2026 market by rules computed from what the trade record shows. The **typical onset** is the close minus the median book-measured lead of the market's level. Slams take the 1000s' lead, because no Slam was played in the block; Slam markets carry more money, so this is if anything late. Volume rules (the first moment $1,000, $2,000 or $5,000 of pre-match stake has traded) are reported beside it. On the 149 block markets whose onset was measured, the typical onset is unbiased (median error 0–1 hours) and lands within a median 2.3 hours of the book onset at the 500s and 250s and 2.2 hours lower down. At the 1000s, whose depth builds gradually, it is within a median 12.7 hours; the volume rules do better there (6–7 hours). The typical onset gives every market of a level an early market, but in the block only 35% of Challenger and WTA 125, 75% of qualifying and 3% of ITF markets reached one.

6. **Checkpoints and scores.** Each market's price is taken at:
   * fixed hours before the close (72 down to a quarter);
   * the moment its pre-match stake reaches $100 to $500,000;
   * the moment a share of its own pre-match volume (5–90%) has traded;
   * its first quoted price;
   * the early-market onset of each rule.

   Each is scored against the same market's close: the log-loss difference, the absolute move in cents, and the perfect-foresight value. That is what a bettor who knew the close would make per $1 by backing, at the checkpoint price, the side the close moved toward, before spread and fees. It is an upper bound on what the early line offers.

## Results

### 1. When the early market opens

Measured from the books, 31 Jul – 3 Aug 2026: the Canada 1000s (both tours), the Washington 500, the Los Cabos and Memphis 250s, and 12 Challenger and WTA 125, 50 ITF and 2 qualifying events. Markets listed before the block began are left out.

| Level (events in the block) | Markets | Reach the early market ($300 within 1¢) | Opens, median hours before the close | Reach it within 2¢ | Opens within 2¢, median hours |
|---|---:|---:|---:|---:|---:|
| 1000s (Canada) | 79 | 76% | 24.2 (quartiles 14.2–38.2) | 85% | 43.7 |
| 500 (Washington) | 9 | 100% | 14.3 | 100% | 17.9 |
| 250 (Los Cabos, Memphis) | 8 | 100% | 10.4 | 100% | 15.0 |
| Challenger and WTA 125 | 119 | 35% | 4.0 | 66% | 13.1 |
| Qualifying | 28 | 75% | 1.5 | 96% | 7.6 |
| ITF | 330 | 3% | 0.4 | 21% | 1.4 |

How much a market buy can take on the thinner side within 1¢ and within 2¢ of the mid (median over minutes, $), and the typical spread:

| Level | Spread | 24–48 h | 12–24 h | 6–12 h | 3–6 h | Last 3 h |
|---|---|---|---|---|---|---|
| 1000s | 1¢ (2¢ beyond 48 h) | 350 / 4,100 | 1,100 / 6,600 | 3,000 / 8,500 | 2,800 / 9,900 | 1,900–3,300 / 9,500–10,100 |
| 500 | 1¢ | 4,100 / 18,900 | 1,000 / 8,000 | 5,600 / 12,500 | 5,500 / 15,600 | 9,700–9,900 / 19,000 |
| 250 | 1¢ | — | 70 / 1,400 | 1,900 / 8,100 | 6,600 / 14,200 | 6,100–6,400 / 17,000 |
| Challenger and WTA 125 | 1¢ inside 24 h, 3¢ at 24–48 h | 0 / 10 | 9 / 66 | 75 / 1,700 | 240 / 3,300 | 590–680 / 4,400–4,700 |
| Qualifying | 1¢ inside 6 h | — | 0 / 0 | 3 / 48 | 290 / 1,700 | 490 / 2,600–2,900 |
| ITF | 2¢ | 0 / 0 | 0 / 7 | 2 / 20 | 3 / 37 | 2 / 52–57 |

At the 1000s a $300 bet within 1¢ is there in about half the minutes 24–48 hours out and in 83–87% of the minutes in the last 12 hours. The block's main-tour books are 1¢ wide almost throughout. At ITF the book within 2¢ of the mid typically holds $20–60.

Measured on cumulative volume instead, the main tour is bettable at $300 within 1¢ in 59–63% of minutes once $250–1,000 has traded, 82–84% from $2,500 and 90–98% from $5,000 (except the highest tier's most-traded minutes, above $100,000, at 63%). Lower down it is 22% from $250, 46% from $2,500 and 56% from $5,000 ([calibration.json](../../../data/studies/line_sharpening/calibration.json), `bettable_by_volume`).

### 2. How far the early line is from the close (all 2026 markets)

The typical onset applied to every 2026 market of the level, whether or not it would have reached the criterion (lower down most would not: section 1). Early minus close, milli-log-loss; positive = the early line was worse.

| Level | Markets | Early market, hours before the close | Early minus close (95% range) | Who is better | Move to the close, mean (median) | Lines moving 3¢+ | Perfect-foresight value, ¢ per $1, mean (median) | Pre-match money still to come |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| **Grand Slam** | 935 | 24.2 | +2.4 (−3.1 to +7.9) | tie | 2.0¢ (1.0) | 19% | 5.0 (2.5) | 96% |
| **1000s and Finals** | 995 | 24.2 | +2.4 (−3.1 to +8.0) | tie | 2.3¢ (1.5) | 26% | 5.2 (3.0) | 97% |
| *Highest tier* | 1,930 | 24.2 | +2.4 (−1.6 to +6.3) | tie | 2.2¢ (1.0) | 23% | 5.1 (2.8) | 97% |
| **500** | 781 | 14.3 | +6.3 (+0.6 to +11.9) | close better | 2.5¢ (2.0) | 29% | 6.0 (3.4) | 95% |
| **250** | 1,219 | 10.4 | +4.0 (+1.0 to +7.0) | close better | 1.8¢ (1.0) | 20% | 4.0 (2.6) | 88% |
| *Higher tier* | 2,000 | 10.4–14.3 | +4.9 (+1.9 to +7.7) | close better | 2.1¢ (1.5) | 23% | 4.8 (2.9) | 91% |
| **Challenger and WTA 125** | 7,167 | 4.0 | −0.1 (−1.2 to +1.0) | tie | 1.2¢ (1.0) | 9% | 3.0 (1.6) | 49% |
| **Qualifying** | 2,185 | 1.5 | −1.3 (−2.9 to +0.3) | tie | 0.9¢ (0.5) | 5% | 4.0 (1.2) | 21% |
| **ITF** | — | none: 3% of markets ever open | — | — | — | — | — | — |

With the 2¢ rule (earlier and softer):

| Level | Hours before the close | Early minus close (95% range) | Who is better | Move to the close |
|---|---:|---:|---|---:|
| Grand Slam | 43.7 | +5.3 (−4.1 to +14.8) | tie | 2.8¢ |
| 1000s and Finals | 43.7 | +30.4 (+11.6 to +48.5) | close better | 4.6¢ |
| 500 | 17.9 | +12.5 (+1.3 to +23.1) | close better | 3.6¢ |
| 250 | 15.0 | +5.4 (−0.3 to +10.8) | tie | 2.5¢ |
| Challenger and WTA 125 | 13.1 | +11.5 (+7.8 to +15.1) | close better | 3.6¢ |
| Qualifying | 7.6 | +6.9 (+2.8 to +11.3) | close better | 2.7¢ |
| ITF | 1.4 | +0.7 (−0.1 to +1.6) | tie | 0.9¢ |

On the block's own markets, with the onset measured from their books rather than predicted, the picture is the same but less precise:

| Tier | Markets | Early minus close (95% range) | Who is better | Move |
|---|---:|---:|---|---:|
| Highest | 60 | +3.7 (−8.4 to +16.7) | tie | 1.7¢ |
| Higher | 17 | −45.4 (−138.3 to +21.1) | tie | 3.7¢ |
| Lower | 72 | −1.1 (−9.7 to +6.7) | tie | 1.0¢ |

The volume rules give the same answer. At the first moment $1,000 has traded (17, 12 and 5 hours before the close, median), the early line is +1.7 for the highest tier (range −1.9 to +5.5, a tie), +4.9 for the higher tier (+1.1 to +9.0, the close better) and +3.8 for the lower tier (+1.7 to +5.9, the close better).

### 3. The path to the close

The same markets at every horizon, priced from 24 hours before the close (lower tier: mostly Challengers, the markets listed that early). Earlier line minus close, milli-log-loss:

| Hours before the close | Highest (1,933) | Higher (1,188) | Lower (4,400) |
|---|---:|---:|---:|
| 24 | +2.4 (−1.4 to +6.3), tie | +7.0 (−0.2 to +14.6), tie | +28.6 (+22.9 to +34.2), close better |
| 18 | +3.6 (−0.3 to +7.8), tie | +5.3 (+0.1 to +10.6), close better | +13.4 (+9.0 to +17.6), close better |
| 12 | +0.9 (−1.0 to +3.0), tie | +4.4 (+1.6 to +7.4), close better | +6.4 (+3.3 to +9.3), close better |
| 9 | +1.0 (−0.8 to +2.8), tie | +2.1 (−0.4 to +4.8), tie | +2.5 (+0.5 to +4.4), close better |
| 6 | +0.6 (−1.1 to +2.2), tie | +1.4 (−0.9 to +3.7), tie | +1.8 (+0.2 to +3.3), close better |
| 3 | +0.8 (−0.5 to +2.1), tie | +1.4 (−0.4 to +3.3), tie | −0.0 (−1.2 to +1.1), tie |
| 1 | +0.4 (−0.5 to +1.4), tie | +0.6 (−0.8 to +2.0), tie | −0.1 (−0.8 to +0.6), tie |

All markets of each level at the horizons they reach (each horizon on its own markets):

| Hours before the close | Grand Slam | 1000s | 500 | 250 | Challenger and WTA 125 | Qualifying | ITF |
|---|---:|---:|---:|---:|---:|---:|---:|
| 24 | +2.1, tie | +2.7, tie | +6.0, tie | +7.7, tie | +19.4 | +25.8 | +67.3 |
| 12 | +1.6, tie | +2.4, tie | +3.6, tie | +2.7, tie | +9.4 | +20.9 | +60.5 |
| 6 | +1.9, tie | −0.3, tie | +1.3, tie | +2.1, tie | +1.1, tie | +3.9 | +15.3 |
| 3 | +1.5, tie | +0.1, tie | +1.0, tie | +0.9, tie | −0.0, tie | −0.2, tie | +2.4 |
| 1 | +0.9, tie | +0.1, tie | +0.8, tie | +0.0, tie | +0.0, tie | −1.1, tie | +0.7, tie |

Unmarked values are significant: the close is better. The highest tier is settled a day out. The 500s and 250s are still slightly soft 12–18 hours out (+4 to +5 on the fixed panel) and level with the close from about 9 hours out. Challengers settle 6 hours out, qualifying 3–6, and ITF keeps improving into the last 2–3 hours.

### 4. Volume

**The share of a market's own pre-match money traded** is the cleanest volume clock, because every market reaches every share. Unmarked values are significant: the close is better.

| Share of the market's pre-match stake traded | Highest: hours before the close, early minus close | Higher | Lower |
|---|---|---|---|
| 5% | 17.9 h, +3.0 (−0.6 to +6.6), tie | 13.9 h, +4.5 (+0.7 to +8.5) | 8.3 h, +14.8 (+12.7 to +16.9) |
| 10% | 13.1 h, +2.5, tie | 10.9 h, +4.3 (+0.2 to +8.2) | 7.4 h, +12.6 |
| 25% | 7.9 h, +1.7, tie | 6.4 h, +1.8, tie | 5.6 h, +7.7 |
| 50% | 3.6 h, +1.9, tie | 2.9 h, +2.5 (+0.0 to +5.0), borderline | 4.0 h, +5.0 |
| 75% | 1.6 h, +1.0, tie | 1.3 h, +0.4, tie | 2.5 h, +3.0 |
| 90% | 0.7 h, +0.7, tie | 0.6 h, +0.4, tie | 1.5 h, +2.1 |

**At the same hours before the close, markets that have traded more are closer to their close**, strongly so lower down. Markets split into thirds by the stake traded so far:

| Tier, hours before the close | Least traded third (median stake), early minus close | Middle third | Most traded third |
|---|---|---|---|
| Lower, 12 h | $0: +79.7 (+71.5 to +88.3) | $4: +28.6 | $320: +3.5 (+1.4 to +5.5) |
| Lower, 6 h | $0: +26.9 | $14: +3.2 | $511: +1.3 (+0.1 to +2.4) |
| Higher, 24 h | $20: +15.3 (+0.5 to +29.6) | $369: +3.5, tie | $2,363: +2.2, tie |
| Highest, 12 h | $255: +5.2 (+0.8 to +10.0) | $1,987: +0.6, tie | $10,623: +0.5, tie |

**Fixed dollar milestones** mix volume with selection: the few lower-tier markets that ever reach $10,000–$25,000 are the ones where something happened. Their line at the milestone is further from the close (+15 to +43) than at $1,000 (+3.8). On the main tour the milestones agree with the rest. The highest tier is a tie from $250 traded (+3.7, range −0.7 to +8.1). The higher tier is +4.9 at $1,000 (range +1.1 to +9.0), a tie from $2,500 (+1.6, range −2.0 to +5.1).

### 5. The opening line

The first price a market shows, first price minus close:

| Tier | Markets | Hours before the close | First price minus close | Move | Lines moving 3¢+ |
|---|---:|---:|---:|---:|---:|
| Highest | 2,342 | 41.4 | +81.4 (+66.8 to +96.2) | 13.9¢ | 76% |
| Higher | 2,095 | 34.4 | +96.1 (+76.9 to +114.9) | 13.9¢ | 81% |
| Lower | 28,923 | 13.2 | +89.3 (+85.1 to +93.6) | 13.5¢ | 68% |

Forty-five percent of markets open at exactly 50¢, a placeholder that persists a median 0.4 hours. The first price away from 50¢ is no better (+80 to +101). A 500 or 250 market's first price is, on average, less accurate than a coin flip. Against a coin flip's log loss, the highest tier's first price carries 37% of the information the close carries, and its early-market price 98%.

### 6. Over the year

Month by month (listed start, January to October), no tier's early line moves closer to its close. The highest tier's early-market gap is a tie in every month. The lower tier's distance at 6 hours out varies between months (0 to +19) without a trend. The number of lower-tier markets grew from 361 in January to 7,795 in September; ITF markets began on 13 May. See `by_month` in [results.json](../../../data/studies/line_sharpening/results.json).

### 7. Sensitivity: the true close

With the close at 5 minutes before the validated start rather than 30 minutes before the listed start, the early-market gaps change little:

| Level | Main close | True close |
|---|---:|---:|
| Highest, 24 h | Grand Slam +2.4, 1000s +2.4 (ties) | Grand Slam −2.0, 1000s +1.4 (ties) |
| 500 | +6.3 (+0.6 to +11.9) | +5.8 (−0.3 to +11.8), tie |
| 250 | +4.0 (+1.0 to +7.0) | +3.8 (+0.3 to +7.5) |
| Challenger and WTA 125 | −0.1, tie | +0.2, tie |
| Qualifying | −1.3, tie | −0.5, tie |

For Slams the true close looks slightly *less* accurate than the price an hour earlier: one hour out minus the true close is −3.9 (range −8.6 to −0.2). That hints at noise or the odd in-play price in the last minutes of the longest-delayed Slam matches. It is one reason the main close stays the conservative one.

## What it costs to take the early line

From the block's books, a $300 market buy on a main-tour market inside the early market pays a median 0.5¢ over the mid: half the 1¢ spread, nothing more. Polymarket's taker fee on tennis, as the sharp-money study measured it:

* none before 29 March;
* from 29 March to 28 April, taker buys received about 6% × (1 − price) fewer shares;
* from 28 April, 3% × (1 − price) of the stake in cash, and 5% × (1 − price) on markets of July onward (each market's current fee schedule).

So since July, taking at even money costs about 2.5¢ in fee plus 1¢ in spread per $1, and taking an 80¢ favourite about 1.6¢. The early line's move to the close averages 1.8–2.5¢ of probability on the main tour (median 1–2¢), and the perfect-foresight value is 2.5–3.4¢ per $1 at the median. The softness is about the size of the cost of taking it. Posting prices instead of taking them costs no fee and earns a rebate. The sharp-money study found that accounts not clearly beating the close break even by posting, and that accounts which beat it earn about 1.3¢ per $1 more by posting than by taking.

## Betting our model at the early market instead of the close

The owner's follow-up of 6 Oct 2026: if we bet at this early market instead of at the close (crossing the spread), how different is our performance?

**Set-up.**

* **The model** is the current best: the local TabPFN-3.5 on the closing odds plus 53 inputs ([meta-stack study](../meta_stack/README.md)), trained on 2013–2025 with the surface-Elo study's settings (seeds 0, 1 and 2; [`timing_local.py`](../../../src/eda/line_sharpening/timing_local.py)) and calibrated with its own 2026 slope per tour (men 0.897, women 0.912). Each 2026 match is queried with its odds input set to the Polymarket price at the early market, at the looser 2¢ early market, and at the main close. Fed the tennis-data close instead, it reproduces the meta-stack study's forecasts (log-odds correlation 0.99999, mean gap 0.07 points).
* **The sample** is 2,933 main-tour matches of 2026 priced at both moments: 673 Slam, 631 1000, 634 500 and 995 250 matches. The early market comes a median 14.3 hours before the close (the 2¢ one 17.9 hours).
* **The bet.** Back the player with the higher expected value (model probability ÷ ask − 1 − fee, per $1) if it reaches a threshold of 0, 2, 4 or 6%, at $1 flat stakes. The ask is the mid plus half a cent, the fee the one in force at that moment.
* **The yardsticks.** Realized profit per $1 staked, and expected profit with the closing mid as the true chance. Bets at the close score exactly minus their costs on the second; early bets gain where the price moved their way. The comparison is paired: each strategy's profit per match, early minus close, with matches it passes on scored at zero.
* **Lower tiers are not in it.** The model covers the main tour only. There, the early market opens 1.5–4 hours before the close, when the line already is the close (section 2), so the timing cannot matter.

**The answer: the same performance.**

| Threshold | Moment | Bets | Realized profit per $1 | Expected profit per $1 (close as truth) | Realized profit per 100 matches |
|---|---|---:|---:|---:|---:|
| 0 | Early market | 2,072 | +4.3% (+0.3 to +8.1) | −1.36% | +$3.01 |
| 0 | Close | 2,103 | +4.2% (+0.3 to +8.1) | −1.62% | +$3.01 |
| 2% | Early market | 1,173 | +5.5% (+0.3 to +10.7) | −1.43% | +$2.21 |
| 2% | Close | 1,160 | +4.4% (−0.7 to +9.7) | −1.61% | +$1.75 |

Early minus close, per 100 matches available (positive = early better):

| Threshold | Realized | Expected (close as truth) | Who is better |
|---|---:|---:|---|
| 0 | +0.00 (−0.86 to +0.91) | +0.20 (−0.00 to +0.42) | tie |
| 2% | +0.47 (−0.17 to +1.17) | +0.07 (−0.10 to +0.24) | tie |
| 4% | +0.07 (−0.49 to +0.61) | −0.04 (−0.16 to +0.08) | tie |
| 6% | −0.08 (−0.45 to +0.30) | −0.03 (−0.12 to +0.08) | tie |

The highest and higher tiers alone are ties too: −0.33 (−1.53 to +0.88) and +0.27 (−0.94 to +1.52) realized at threshold 0. If a $300 bet pays the definition's full 1¢ over the mid early instead of half a cent, early is slightly worse, −1.09 (−2.49 to +0.33).

**Why.** The slope of the close's move on the model's disagreement with the early price measures how much of that disagreement the market closes. It is +0.066 (+0.028 to +0.102): the market moves 7% of the way toward the model, 6% at the highest tier and 8% at the higher. A typical disagreement, 0.22 in log-odds or about 5 points of probability, closes by about a third of a point, which is worth less than the half-cent spread.

**Earlier is a little different, but the extra cost eats it.** From the 2¢ early market (44 hours out at the Slams and 1000s), the market moves 25% of the way to the model (16 to 37%). At the 1000s alone it moves about all the way (slope 1.2, range 0.5 to 2.0, 218 matches). With half-cent fills that is worth +0.97 per 100 matches in expectation (+0.51 to +1.46), about +1.35¢ per $1 bet. But a $300 bet there can pay up to 2¢ over the mid. At 1¢ the expected gain falls to +0.61 (+0.18 to +1.04), and at 1.5¢ to +0.52 (+0.15 to +0.90). The realized differences are ties (−0.24 to +0.26 at threshold 0).

**The one systematic effect: favourites firm up.** Between the early market and the close the favourite's price rises by +0.47¢ on average (+0.33 to +0.59): Slams +0.64, 1000s +0.54, 250s +0.42, 500s +0.30 (a tie); men +0.69, women +0.22. It is in the market alone; backing every favourite early instead of at the close gains it. For the model's own bets:

* its favourite bets are worth +0.7¢ per $1 more early (expected −0.53% against −1.24% at the close);
* its underdog bets are worth 0.7¢ less early (−3.21% against −2.49%).

Betting the model's favourites at the early market and its underdogs at the close beats betting everything at the close by +0.36 per 100 matches in expectation (+0.25 to +0.48). Realized, it is +0.23 (−0.41 to +0.86), a tie. That is about half a cent per $1 bet.

**A note on 2026's realized profit.** The model made money at both moments, +4% per $1 at threshold 0, but against Polymarket's close it ties in log loss:

* +0.21 milli-log-loss at the close (−2.58 to +2.83; positive = model better), +0.40 at the early market and +1.25 at the 2¢ early market;
* its bets' expected profit with the close as the truth is the costs, −1.6% per $1.

Market-only rules (back player A, the favourite, the underdog) lose about their costs in the same sample, and Polymarket's close is calibrated to within a point in every price band. So the arithmetic is sound, and one season cannot separate the model's small edge over Polymarket from luck. The timing comparison above is paired and does not depend on that.

## Limitations

* **Four days of books.** The early-market criterion is measured on one block, 31 Jul – 3 Aug 2026: the Canada 1000s and three 500/250 events (17 uncensored higher-tier markets). The typical leads carry it to the rest of the year, but books in other weeks, other surfaces and the Slams were not observed. Slams are assumed to open like the 1000s. The archive holds about 75% of the tennis markets from 13 April to 10 August, with long gaps. The whole archive is about 1.16 TB; the needed columns of the rest about 0.8 TB.
* **The replay understates depth slightly.** In 4% of minutes the archive lacks a level the exchange shows, so the replay's quote is worse than the exchange's. It is never better.
* **Volume is taker stake.** It is money bet at market, one side per trade, before the main close. Counting the makers' side as well would roughly double it.
* **Perfect-foresight value is an upper bound.** It assumes the close is known. Means are pulled up by long shots; medians are quoted beside them.
* **Start of play.** The detector was checked on the main tour only. The main close is the earlier of 30 minutes before the listed start and 5 minutes before the validated start, so a match that starts hours after its listed time (common at ITF) closes early, and its late pre-match drift is not counted. The true close (section 7) counts it.
* **Markets, not matches.** A few matches have two markets (rain-delayed relistings); each is scored as listed.
* **2026 only.** Polymarket's tennis markets began in September 2025; the year's growth (ITF from May, fees from April) changes the population month by month.

## Possible follow-ups (suggestions, not decisions)

1. **Read the rest of the archive** (about 0.8 TB of range requests, roughly 6 hours at this session's rate of six parallel readers; tennis is about 1.3% of the rows kept). That would give book-measured onsets for April – August, including Roland Garros and the part of Wimbledon the archive holds, in place of the typical leads.
2. **Record live books** from now on (the CLOB's `/books` endpoint, every few minutes for open tennis markets). That gives the early market of the autumn events, and of any future Slam, directly.
3. **Test the move, not just its size.** The early line moves about as much as it costs to take. Whether the project's models or the market's own early order flow predict the direction of that move is the question that decides whether the early market is worth betting.

## Reproduce

```
./python.sh -m src.ingest.public_dump.pmxt_books --start 2026-07-31T00 --end 2026-08-04T00 --workers 6   # 96 hours, 32 GB read, about 20 minutes
./python.sh src/eda/line_sharpening/pmxt_coverage.py          # resumes; every 8th hour's market column, about 1 GB read
./python.sh src/eda/line_sharpening/build.py                  # about 15 minutes
./python.sh src/eda/line_sharpening/starts_check.py
./python.sh src/eda/line_sharpening/books.py                  # about 2 minutes on 12 processes
./python.sh src/eda/line_sharpening/books_check.py
./python.sh src/eda/line_sharpening/calibrate.py
./python.sh src/eda/line_sharpening/evaluate.py               # about 5 minutes
./python.sh src/eda/line_sharpening/evaluate.py --close ext --tag ext
./python.sh src/eda/line_sharpening/timing_frame.py           # the early-versus-close sample (needs the surface-Elo study's frames)
./python_tabpfn_local.sh src/eda/line_sharpening/timing_local.py   # 3 GPU fits, about a minute each
./python.sh src/eda/line_sharpening/timing_bets.py
./python.sh -m pytest test/line_sharpening -q
```

The price history and trades must be staged first (`polymarket_prices.py`, `polymarket_trades.py`, or `src/ingest/refresh_odds.py`). The Parquet outputs are gitignored and rebuilt by these scripts; see [LARGE_FILES.md](../../../data/LARGE_FILES.md).
