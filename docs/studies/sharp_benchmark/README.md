# Sharp benchmark for 2026: Betfair Exchange and Polymarket against Pinnacle

**Betfair Exchange and Polymarket are as sharp as Pinnacle was.** With each venue's margin removed, the three venues' closing prices have the same log loss on the matches they share, to within a milli-log-loss or so. Betfair minus Pinnacle is −0.3 milli-log-loss (95% range −2.3 to +1.6) on 1,223 matches from 17 Aug 2025 to 14 Jan 2026. Polymarket minus Pinnacle is +0.3 (−4.9 to +5.8) on 745 matches. Polymarket minus Betfair is −0.9 (−3.1 to +1.4) on 4,576 matches from 19 Sep 2025 to 29 Sep 2026. Taken year by year as asked, Betfair in 2026 (log loss 0.5774) and Polymarket in 2026 (0.5783) beat Pinnacle in 2025 (0.5959) by 17–18 milli-log-loss. That gap belongs to the matches, not the venues: the market average and Bet365 improve by as much between the same two years. Measured against either yardstick, neither venue differs from Pinnacle: Betfair −1.4 (−2.9 to +0.4), Polymarket −1.9 (−4.6 to +0.8).

**Sharpness drifts before the match, not over the calendar.** No venue's distance from the market average shows a trend over 2025–2026. Before the match, Polymarket's main-tour price reaches Betfair's closing sharpness about six hours before the listed start and changes little after that. At the Slams and 1000s the price is set a day ahead. At Challenger and ITF events it forms on match day: 20 and 76 milli-log-loss of the improvement come in the last 24 hours. Polymarket's last price before the listed start looks 3.1 milli-log-loss sharper than Betfair's close. Most of that, 2.4, comes from the 2% of markets whose price jumps in the last half hour, mostly toward the eventual winner: matches already under way. For that reason the benchmark price here is Polymarket's price 30 minutes before the listed start.

**How to read the numbers.** Log loss: lower is better. "A − B" is a difference in milli-log-loss (thousandths of a nat): negative means A is sharper, positive means B is. When the 95% range includes zero, the two are tied, whatever the sign.

**Status: study, not a decision.** It measures the venues as benchmarks; no benchmark has been chosen. Numbers are from the refresh of 5 Oct 2026, 23:25 UTC; every refresh re-runs the study, and [results.json](../../../data/studies/sharp_benchmark/results.json) holds the current figures.

| Item | Where |
|---|---|
| Match table: tennis-data rows of 2025–2026 with every book's odds and the linked Polymarket market at nine horizons | [`build.py`](../../../src/eda/sharp_benchmark/build.py) → `data/studies/sharp_benchmark/matches.parquet`, `pm_markets.parquet`, [link_summary.json](../../../data/studies/sharp_benchmark/link_summary.json) |
| Margin removal, log loss, bootstrap | [`devig.py`](../../../src/eda/sharp_benchmark/devig.py) |
| Comparisons, sensitivity, drift | [`evaluate.py`](../../../src/eda/sharp_benchmark/evaluate.py) → [results.json](../../../data/studies/sharp_benchmark/results.json) |
| One-command refresh of every odds source, then this study | [`src/ingest/refresh_odds.py`](../../../src/ingest/refresh_odds.py) |
| Betfair historical tick data (adapter, not yet run: needs an account) | [`src/ingest/betfair_history.py`](../../../src/ingest/betfair_history.py) |
| Tests | `test/sharp_benchmark/` (19 offline tests: margin removal incl. a numerical Shin check, linking, odds cleaning, the Betfair stream parser, the refresh's step plan), plus 5 in `test/public_data_dump/` for the Polymarket revisit and re-fetch rules |

## Question

The owner asked on 5 Oct 2026 for the Betfair and Polymarket exchange prices already in the project's files to serve as the sharp benchmark for 2026. Pinnacle's closing odds stop in mid-January 2026 in tennis-data.co.uk, after Pinnacle closed its public API on 23 Jul 2025. The second part was how those venues compare with Pinnacle's 2025 closing odds by log loss once the margin is removed. During the work the owner added a third: how much the sharpness of these markets drifts over time, with tick data for 2025–2026 from both. A fourth followed: a script that refreshes all of it.

"Drift over time" is answered both ways it can be read. One is across the calendar: is a venue's closing price sharper in some months than others? The other is across the hours before a match: how sharp is the price a day, six hours or an hour before the start?

## Data

| Source | What was used | Accessed | Limits |
|---|---|---|---|
| tennis-data.co.uk 2025 and 2026 season workbooks, ATP and WTA (register `tennis_data_odds`) | Results and closing odds: Pinnacle `PSW/PSL`, Betfair Exchange `BFEW/BFEL`, Bet365 `B365W/L`, OddsPortal's market average `AvgW/AvgL`; 9,544 rows | Downloaded from the relaunched live site on 5 Oct 2026 at 20:01 UTC, in a concurrent session's refresh of the adapter; the earlier Internet Archive captures of 3 Aug 2026 are kept under `data/raw/public_dump/tennis_data_couk/superseded/`. Fetched again by the refresh at 23:25 and 23:48 UTC, same bytes. Files last modified: ATP 2026 on 29 Sep, WTA 2026 on 27 Sep 2026 | The provider's notes do not define `BFEW/BFEL`; they predate the columns. Reading them as Betfair Exchange is inference, from the name and from a median overround of 0.64–0.73%, typical of best back prices on an exchange. Odds carry no timestamp; "generally the most recent before play starts" is the provider's claim. Pinnacle runs to 13–14 Jan 2026, Betfair from 17 Aug 2025. Main tour only. Odds of 0 or 1.00 are missing; a pair outside overround 1.00–1.20 is not a coherent quote. That drops 11 Betfair pairs: five walkovers or retirements, two garbled pairs, and four extreme-favourite pairs whose back prices sum to 0.98–1.00. Keeping those four moves Betfair's 2026 log loss by +0.3 milli-log-loss and its difference from the average by +0.1 |
| Polymarket Gamma index (census of 10 Sep 2026, catalog extensions of 22 Sep and 5 Oct 2026, revisits of 5 Oct 2026) | Every singles match-winner market: players, outcome labels, listed start (`gameStartTime`), settlement | 10 Sep, 22 Sep, 5 Oct 2026 | Current metadata, not a revision history. The listed start is not the actual start |
| Polymarket minute price history, `clob.polymarket.com/prices-history` (`fidelity=1`, first outcome) | Price at 48, 24, 12, 6, 3 and 1 hours and 30, 10 and 0 minutes before the listed start: the last point before each cut-off, if from the hour before it | 22 Sep 2026; topped up 5 Oct 2026 (3,888 requests, then 594 in the refresh, 451 of them replacing histories cut short; no errors) | The earlier study treats the value as the book's midpoint. 11 linked markets show exactly 0.50 at the listed start, an emptied book |
| Polymarket trades, `data-api.polymarket.com/trades` | Not used in the scores; held as tick data (below) | 25 Sep 2026; topped up 5 Oct 2026 (4,285 markets, then 347 in the refresh, 214 of them re-fetched) | Fees not in the records |
| Tennis My Life ATP 2026 | Settles one result conflict (below) | on disk | |
| Betfair Historical Data | **Not on disk.** Every plan, including the free BASIC one, needs a Betfair account; nothing was bought or registered | — | See "Tick data" |

## Method

1. **Matches.** Every row of the 2025 and 2026 tennis-data files (main tour: Slams, 1000s, 500s, 250s, the Finals). Scores use completed matches (9,179, less one result conflict, point 4); retirements are added back as a check. A row dated outside its file's season would take the file's year. The archived WTA 2026 file had one written as 2029; the live file has none.
2. **Margin removal.** Implied chances `1/odds`, normalised so the pair sums to one (proportional, the project's convention). The power method and Shin's method are checks. With two outcomes Shin's method has a closed form, `(1 + q_w − q_l)/2`, which the tests confirm against a numerical solution. Betfair's back prices carry a small overround of their own (median 1.0065); its commission is charged on winnings and is not in the price. A Polymarket price needs no removal, since its two outcomes are one book.
3. **Polymarket benchmark price.** The price 30 minutes before the market's listed start (`pw_pm_m30`), not the last price before it. In the last half hour, 106 of 4,572 linked markets (2.3%) move by more than 10 points, against 31 in the half hour before. Those that move more than 20 points move toward the eventual winner 74% of the time, as in-play prices do. Those markets carry all of the last half hour's gain in log loss (2.4 milli-log-loss): they are matches already under way when the listed start arrives. The price at 60, 10 and 0 minutes is reported as a check.
4. **Linking.** tennis-data names are "Surname I.", Polymarket's full names. A market links to a row when a "surname span + first initial" form of each player (`td_variants` of the merge-feasibility study) gives the row's winner > loser pair. It must be on the same tour, with the listed start from 3 days before to 2 days after the match day. The nearest day wins, then a market with a price, then the most traded; each row takes one market and each market one row. The outcome labels give which outcome is the row's winner; they found it in all but one market. **4,993 of the 5,235 rows since 19 Sep 2025 link (95.4%).** Polymarket main-tour markets left unlinked include rain-delayed matches it listed twice (both settled), matches that never took place (settled 50/50), the Next Gen Finals (not in tennis-data), and names spelt differently (Moeller and Møller). Polymarket's settlement agrees with tennis-data's winner in 4,810 of 4,811 completed matches and 140 of 141 retirements. In the completed exception (Rotterdam 2026, Bergs v Medjedovic) Tennis My Life sides with Polymarket (Medjedovic 7-6 7-6), so tennis-data has the names the wrong way round. Both conflicting rows are left out.
5. **Scoring.** Log loss is −log of the chance given to the winner, in nats, averaged over matches. Differences are in milli-log-loss (thousandths). A comparison uses only matches where every venue in it has a price. 95% ranges come from 2,000 Poisson-bootstrap draws over matches, with shared weights for comparisons on the same matches. Each comparison seeds its own draws from what it compares, so a refresh that adds matches to one comparison leaves the ranges of the others unchanged.
6. **Across years.** A raw difference between two years mixes the venue with the matches. Each venue's distance from a yardstick quoted on the same matches is therefore compared instead: the market average, or Bet365.

## Results

### 1. Each venue in its own year: the comparison as asked

| Venue, year | Completed matches | Dates | Log loss (95% range) | Venue minus market average, same matches | Venue minus Bet365 |
|---|---:|---|---:|---:|---:|
| **Pinnacle 2025** | 4,723 | 29 Dec 2024 – 16 Nov 2025 | **0.5959** (0.5851–0.6067) | −0.2 (−1.2 to +0.7) | −0.2 (−1.3 to +0.9) |
| **Betfair 2026** | 4,028 | 4 Jan – 29 Sep 2026 | **0.5774** (0.5658–0.5894) | −1.6 (−2.8 to −0.3) | −1.2 (−2.4 to −0.03) |
| **Polymarket 2026** | 4,061 | 4 Jan – 29 Sep 2026 | **0.5783** (0.5662–0.5911) | −2.2 (−4.8 to +0.4) | −2.2 (−4.7 to +0.4) |
| Pinnacle 2026 (to 14 Jan) | 167 | 4–14 Jan 2026 | 0.5824 (0.5393–0.6295) | +0.0 (−3.7 to +3.9) | −1.7 (−6.4 to +2.9) |
| Betfair 2025 (from 17 Aug) | 1,221 | 17 Aug – 16 Nov 2025 | 0.5774 (0.5555–0.5997) | −1.2 (−3.3 to +1.1) | +0.1 (−2.0 to +2.3) |
| Polymarket 2025 (from 19 Sep) | 713 | 19 Sep – 16 Nov 2025 | 0.5859 (0.5575–0.6142) | +2.0 (−3.3 to +8.3) | +3.1 (−2.2 to +9.4) |

| 2026 venue against Pinnacle 2025, milli-log-loss (negative = the 2026 venue sharper) | Raw | Against the market average | Against Bet365 | Better |
|---|---:|---:|---:|---|
| Betfair 2026 − Pinnacle 2025 | −18.5 (−35.5 to −2.3) | −1.4 (−2.9 to +0.4) | −1.0 (−2.6 to +0.6) | Raw: Betfair 2026, because its matches were easier. Against either yardstick: tie |
| Polymarket 2026 − Pinnacle 2025 | −17.5 (−34.4 to −1.6) | −1.9 (−4.6 to +0.8) | −1.9 (−4.6 to +0.9) | Raw: Polymarket 2026, because its matches were easier. Against either yardstick: tie |

The raw gap is real but is not about the venues. The market average's own log loss falls from 0.5958 on Pinnacle's 2025 matches to 0.5799 on Betfair's 2026 matches; the women's matches of 2026 are especially predictable (Betfair 0.5619 against 0.5947 for Pinnacle on the 2025 women's matches). Against either yardstick no venue is clearly different from Pinnacle.

### 2. The same matches: the like-for-like test

| Venues on the same completed matches (log loss: lower is better) | Matches | Dates | Market average | Pinnacle | Betfair | Polymarket | Difference, milli-log-loss | Better |
|---|---:|---|---:|---:|---:|---:|---|---|
| Pinnacle and Betfair | 1,223 | 17 Aug 2025 – 14 Jan 2026 | 0.5887 | 0.5880 | 0.5877 | | Betfair − Pinnacle −0.3 (−2.3 to +1.6) | Tie (Betfair nominally) |
| Pinnacle and Polymarket | 745 | 19 Sep 2025 – 14 Jan 2026 | 0.5908 | 0.5904 | | 0.5907 | Polymarket − Pinnacle +0.3 (−4.9 to +5.8) | Tie (Pinnacle nominally) |
| Betfair and Polymarket | 4,576 | 19 Sep 2025 – 29 Sep 2026 | 0.5803 | | 0.5790 | 0.5781 | Polymarket − Betfair −0.9 (−3.1 to +1.4) | Tie (Polymarket nominally) |
| All three | 741 | 19 Sep 2025 – 14 Jan 2026 | 0.5895 | 0.5890 | 0.5889 | 0.5893 | every pair within 0.4 | Tie |

By tour the picture is the same. Betfair − Pinnacle is −0.2 (men) and −0.4 (women). Polymarket − Pinnacle is +0.1 and +0.5. Polymarket − Betfair is +0.0 (−3.3 to +3.1) for men and −1.8 (−4.9 to +1.4) for women. Where the prices disagree, they disagree by little: the mean gap between Polymarket's and Betfair's chances is 0.8–2.6 percentage points a month (median 0.6–0.9), and between Pinnacle and Betfair 1.0–1.3.

### 3. Sensitivity

| Check, milli-log-loss | Proportional | Power | Shin |
|---|---:|---:|---:|
| Pinnacle − average, 2025 | −0.2 | −0.0 | +0.1 |
| Betfair − average, 2026 | **−1.6 (−2.8 to −0.3)** | +0.3 (−0.7 to +1.3) | −0.1 (−0.9 to +0.7) |
| Betfair − Pinnacle, same matches | −0.3 | +0.5 | +0.3 |
| Polymarket − Betfair, same matches | −0.9 | −0.7 | −0.8 |

* **Betfair's edge over the market average is an artefact of proportional margin removal.** The average carries a 6% margin, and proportional removal leaves favourite–longshot error in it. The power and Shin methods remove that error, and the edge vanishes. None of the venue-against-venue results depend on the method.
* **Retirements included:** Betfair − Pinnacle +0.2, Polymarket − Pinnacle +0.6, Polymarket − Betfair −0.9 (4,710 matches).
* **Polymarket's price time:** against Betfair, −0.9 at 60 minutes before the listed start, −3.2 (−5.8 to −0.8) at 10 minutes, −3.1 (−6.1 to −0.3) at the listed start. The last two contain in-play prices (method, point 3). Without the 106 markets that moved more than 10 points in the last half hour, the listed-start price is −1.1 against Betfair.

### 4. Drift over the calendar

Each venue's log loss minus the market average's on the same matches, by quarter, in milli-log-loss (negative = the venue sharper than the average; matches in brackets):

| Quarter | Pinnacle | Betfair | Polymarket | Polymarket − Betfair |
|---|---:|---:|---:|---:|
| 2025 Q1 | −0.1 (1,362) | | | |
| 2025 Q2 | −1.4 (1,403) | | | |
| 2025 Q3 | +1.0 (1,417) | −2.9 (612) | +2.8 (153) | +6.4 (−1.5 to +17.4) |
| 2025 Q4 | −0.5 (475) | +0.5 (607) | +1.8 (560) | +1.1 (−5.3 to +7.6) |
| 2026 Q1 | +0.0 (167) | −0.9 (1,436) | −2.2 (1,373) | −1.4 (−4.2 to +1.1) |
| 2026 Q2 | | −1.7 (1,255) | +0.4 (1,398) | −0.2 (−4.7 to +4.1) |
| 2026 Q3 | | −2.1 (1,336) | −4.8 (1,290) | −2.6 (−8.2 to +2.3) |
| **Linear trend per year** | +0.9 (−2.1 to +4.2) | −0.5 (−3.9 to +2.7) | −5.0 (−14.0 to +2.8) | −3.5 (−11.7 to +4.4) |

No venue drifts measurably. Polymarket started its tennis markets in September 2025 slightly behind Betfair and ended the period slightly ahead, consistent with a market that matured as its volume grew. The trend's range includes zero, so that is a direction, not a finding. Pinnacle's last half-year (after its API closed in July 2025) shows no deterioration.

### 5. Drift before the match: Polymarket

Log loss of Polymarket's price at each horizon on the same 4,460 completed linked matches, all priced from 12 hours out, with Betfair's close on the same matches:

| Hours before the listed start | 12 | 6 | 3 | 1 | 0.5 (benchmark) | Betfair close |
|---|---:|---:|---:|---:|---:|---:|
| Log loss | 0.5826 | 0.5797 | 0.5793 | 0.5788 | 0.5788 | 0.5794 |
| Minus Betfair's close, milli-log-loss (negative = Polymarket sharper) | +3.2 (+0.3 to +6.0) | +0.3 (−2.0 to +2.7) | −0.1 (−2.2 to +2.2) | −0.6 (−2.8 to +1.7) | −0.6 (−2.8 to +1.7) | |

On the 3,093 matches priced from 24 hours, Polymarket is 4.7 (+0.2 to +9.0) behind Betfair's close a day out and level with it from six hours. On the 437 that also have Pinnacle (late 2025), it is level with Pinnacle's close from about 12 hours out (−0.1 at 12 h, −4.7 at 30 minutes, ranges ±10).

How much the price improves from 24 hours to 30 minutes before the listed start, by level, on every settled Polymarket singles market priced at every horizon (Polymarket's settlement as the label; a positive improvement means the 30-minute price is sharper):

| Level | Markets | Log loss at 24 h | At 30 min | Improvement in the last day, milli-log-loss | Of which from 6 h |
|---|---:|---:|---:|---:|---:|
| Grand Slams | 942 | 0.5275 | 0.5255 | 2.0 (−3.6 to +8.2) | 0.6 |
| 1000s and Finals | 1,193 | 0.5965 | 0.5946 | 1.9 (−5.4 to +8.9) | −1.3 |
| 500s and 250s | 1,464 | 0.6046 | 0.5922 | 12.4 (+4.5 to +19.8) | 3.2 |
| Qualifying | 352 | 0.6079 | 0.5785 | 29.4 (+10.4 to +50.3) | 0.3 |
| Challenger and WTA 125 | 3,325 | 0.6262 | 0.6062 | 20.0 (+13.9 to +26.2) | 2.4 |
| ITF | 810 | 0.5879 | 0.5116 | 76.3 (+56.6 to +96.2) | 10.5 |

The lower the level, the later the price forms. At Challenger and ITF level a price taken the evening before is far from sharp; at the Slams it hardly moves on the day. The 24-hour sets hold only markets listed a day ahead, which at the lower levels are the minority (810 of 10,009 ITF markets priced from 12 hours).

Betfair's own curve cannot be drawn: it needs Betfair's historical tick data.

## Tick data: what is on disk, and keeping it current

**One command brings every odds source up to date:** `./python.sh -m src.ingest.refresh_odds`. It runs these steps:

1. Re-downloads tennis-data.co.uk's last and current seasons.
2. Adds Polymarket events listed since the last run.
3. Fetches again any Polymarket event captured while its matches were still to be played, for their results.
4. Fetches prices and trades for markets whose match day has passed, and again for any fetched before their market closed.
5. Downloads Betfair's tick files, if `BETFAIR_SSOID` is set.
6. Rebuilds this study.

Each step is resumable. Until 5 Oct 2026 the Polymarket adapters never revisited a market they had captured open. Match-winner markets of 21–24 Sep and 4–7 Oct sat without a result (893 of them among the singles), and histories fetched mid-match stayed cut short. The first run of the fixed refresh (5 Oct) fetched 921 such events again; 796 of their match-winner markets had since settled, and the rest were still being played. It replaced 451 cut-short price histories and 214 trade histories, and touched nothing already complete.

* **Polymarket, complete for its tennis life (Sep 2025 – 5 Oct 2026).** The catalog runs to matches listed for 7 Oct 2026. The price history covers every match-winner market whose match day had passed by 5 Oct: 40,292 markets with 69.3 million minute-level points. The trade history holds 38.1 million fills: every fill, both sides, with timestamp, price, size and account. Polymarket had no tennis markets before September 2025, so there is nothing earlier to fetch. Order books (full depth) are not public history; the register's paid archives (PMXT from April 2026, Telonex, PolymarketData) hold them.
* **Betfair: closing prices only.** The tennis-data files hold Betfair's closing odds from 17 Aug 2025 to 29 Sep 2026, but no history within a match day. Betfair's tick data comes only from Betfair Historical Data. Its BASIC plan is free (last traded price each minute), ADVANCED and PRO are paid (one-second and 50 ms, with prices and volume at each level). Every plan needs a Betfair account, and the data has to be added to the account in the portal before it can be downloaded. [`src/ingest/betfair_history.py`](../../../src/ingest/betfair_history.py) does the rest. It lists and downloads the account's tennis Match Odds files through the portal's API, using a session token read from `BETFAIR_SSOID` and never written to disk, and stages them as tick tables. Its parser is tested on a synthetic stream in Betfair's documented format; the API calls have not been run, because no account was available.

## Limitations

* **Listed, not actual, start times.** Polymarket's benchmark price is 30 minutes before the listed start, which is earlier than a true close when a match starts late. That handicaps Polymarket slightly: over the last six hours the curve improves by about 0.1–0.4 milli-log-loss an hour. A few markets will still be in play 30 minutes before the listed start: 31 moved more than 10 points between 60 and 30 minutes out. Actual start times (the official point feeds, SofaScore) would allow a true close; they were not joined here.
* **tennis-data's closing odds are untimed.** Whether Betfair's "close" is the last pre-play price, and how near the start Pinnacle's was taken, is the provider's claim. Betfair's tick data would settle this for Betfair.
* **Betfair's columns are inferred.** `BFEW/BFEL` are undocumented in the provider's notes. Their overround and their agreement with Pinnacle (mean gap 1.0–1.3 points) fit Betfair Exchange back prices, but no definition was found.
* **Main tour only for the cross-venue tests.** tennis-data holds no lower-tier odds, so Challenger and ITF are compared only within Polymarket.
* **Populations.** Pinnacle's 2025 matches run January to November. The 2026 matches stop at the end of September, before the Asian swing and the indoor season, and the 2026 women's matches were unusually predictable. The yardstick comparison absorbs differences in mix that move all venues alike, not mix that favours one.
* **One season of overlap with Pinnacle.** Pinnacle and Betfair share 1,223 matches, Pinnacle and Polymarket 745, so differences of about 2 and 5 milli-log-loss respectively cannot be ruled out.

## Reproduce

```
./python.sh -m src.ingest.refresh_odds                # every odds source to today, then build.py and evaluate.py (about 25 min)
./python.sh -m src.ingest.refresh_odds --only study   # rebuild the study from what is on disk (about 2 min)
./python.sh -m pytest test/sharp_benchmark test/public_data_dump -q
BETFAIR_SSOID=<token> ./python.sh -m src.ingest.refresh_odds --only betfair,study   # once an account holds Betfair's data
```

The refresh's steps can also be run one by one; their commands are in [`src/ingest/refresh_odds.py`](../../../src/ingest/refresh_odds.py).
