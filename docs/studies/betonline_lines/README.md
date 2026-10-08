# BetOnline's tennis closing lines against Pinnacle's, 2024–2025: sharpness and margin

**BetOnline's closing lines are as sharp as Pinnacle's; its margin is about a third higher.** With each book's margin removed, the two closes have the same log loss on the 9,272 completed main-tour matches they share (1 Jan 2024 – 16 Nov 2025): Pinnacle 0.5895, BetOnline 0.5897. BetOnline − Pinnacle is +0.3 milli-log-loss (95% range −0.3 to +0.9), a tie, and every year, tour and check is a tie too. The margin is not: BetOnline charges 3.75% against Pinnacle's 2.79%, 0.96 points more (1.34 times as much), and is wider on 94% of matches.

**How to read the numbers.** Log loss: lower is better. "A − B" is a difference in milli-log-loss (thousandths of a nat): negative means A is sharper, positive means B is. When the 95% range includes zero, the two are tied, whatever the sign. Margin is the overround minus one, 1/o_w + 1/o_l − 1, in percent: lower is cheaper for the bettor.

**Status: study, not a decision.** Numbers are from the run of 8 Oct 2026, 15:58 UTC; [sharpness.json](../../../data/studies/betonline_lines/sharpness.json) holds them.

| Item | Where |
|---|---|
| The study: linking, scores, margins | [`src/eda/betonline_lines/sharpness.py`](../../../src/eda/betonline_lines/sharpness.py) → [sharpness.json](../../../data/studies/betonline_lines/sharpness.json) (aggregates) and `sharpness_matches.parquet` (gitignored) |
| Reused from the sharp benchmark | tennis-data loading and cleaning, the linker ([`build.py`](../../../src/eda/sharp_benchmark/build.py)), margin removal ([`devig.py`](../../../src/eda/sharp_benchmark/devig.py)), the paired bootstrap ([`evaluate.py`](../../../src/eda/sharp_benchmark/evaluate.py)) |
| BetOnline's lines | [`src/ingest/oddstrader.py`](../../../src/ingest/oddstrader.py), pulled 7 Oct 2026 UTC under the [owner's decision](../../decisions/2026-10-06-oddstrader-betonline-lines.md); source research in [BetOnline tennis lines](../../research/betonline-lines/README.md) |
| Tests | `test/betonline_lines/` (15 offline tests, 4 for this study: American prices, which side won, margins on the same rows, line shopping) |

## Question

The owner asked on 8 Oct 2026 how sharp BetOnline's 2024 and 2025 tennis closing lines are next to Pinnacle's, by log loss with the margin removed, and what margin each charges.

## Data

| Source | What was used | Accessed | Limits |
|---|---|---|---|
| tennis-data.co.uk 2024 and 2025 season workbooks, ATP and WTA | Results; Pinnacle `PSW/PSL`, Bet365 `B365W/L` and OddsPortal's market average `AvgW/AvgL`; 10,342 rows | Live site, 5 Oct 2026 20:01 UTC (files last modified 28 Jul 2025 to 13 Apr 2026) | Odds carry no time; "generally the most recent before play starts" is the provider's claim. Main tour only |
| OddsTrader's odds service | BetOnline's opening and last match-winner line with their times (`betonline_matches.parquet`) | 7 Oct 2026 UTC | The close is the last line OddsTrader recorded. 124 linked closes are flagged uncertain (stamped over 30 minutes after the listed start, or not a two-sided market) and left out |

## Method

1. **Linking.** The sharp benchmark's linker, given OddsTrader's full player names. It matches each player's "surname span + first initial" to tennis-data's names, on the same tour, with OddsTrader's listed start 3 days before to 2 days after the match day; one row per match and one match per row. It also says which OddsTrader side won. **10,235 of the 10,342 rows link (99.0%)**: 9,884 on the same day, 338 listed a day early (inferred: matches played in Australia and Asia, whose UTC listing falls on the previous day).
2. **Prices.** A pair outside overround 1.00–1.20 is not a coherent quote. Coherent closes: Pinnacle 10,086, BetOnline 9,830 (with the 124 uncertain ones out), Bet365 10,294, market average 10,326.
3. **Scoring.** As in the sharp benchmark: completed matches (retirements return as a check); the winner's chance with the margin removed proportionally (power and Shin as checks); log loss in nats; each comparison on the matches where every book in it has a price; 95% ranges from 2,000 Poisson-bootstrap draws over matches, shared by the books in a comparison.
4. **Margin.** Each book's overround minus one on the matches where all four books are coherent (9,250): mean and median, BetOnline's minus Pinnacle's and its ratio with paired bootstrap ranges, and by how strong the favourite is (Pinnacle's margin-free chance).

## Results

### 1. Sharpness at the close

| Completed matches | Matches | Pinnacle | BetOnline | BetOnline − Pinnacle | Better |
|---|---:|---:|---:|---:|---|
| **2024–2025** | 9,272 | 0.5895 | 0.5897 | **+0.3 (−0.3 to +0.9)** | Tie (Pinnacle nominally) |
| 2024 | 4,671 | 0.5832 | 0.5833 | +0.0 (−0.7 to +0.8) | Tie |
| 2025 | 4,601 | 0.5958 | 0.5963 | +0.5 (−0.4 to +1.5) | Tie (Pinnacle nominally) |
| Men | 4,833 | 0.5885 | 0.5888 | +0.3 (−0.6 to +1.1) | Tie |
| Women | 4,439 | 0.5905 | 0.5908 | +0.3 (−0.6 to +1.2) | Tie |
| Men 2024 / 2025 | 2,438 / 2,395 | | | −0.3 (−1.4 to +0.8) / +0.9 (−0.4 to +2.3) | Ties |
| Women 2024 / 2025 | 2,233 / 2,206 | | | +0.4 (−0.7 to +1.5) / +0.2 (−1.3 to +1.7) | Ties |

The two prices nearly coincide. Their margin-free chances differ by a median of 0.7 percentage points (mean 0.9). They differ by more than 2 points on 10% of matches and by more than 5 on 0.4%. The gap is a little wider in 2025 (median 0.8) than in 2024 (0.6).

**Yardsticks on the same 9,250 matches:** market average 0.5901, Bet365 0.5902, Pinnacle 0.5896, BetOnline 0.5899. BetOnline − average −0.2 (−0.8 to +0.4); Pinnacle − average −0.5 (−1.2 to +0.1): ties. In 2024 alone both beat the average narrowly, BetOnline by 0.8 (−1.6 to −0.1) and Pinnacle by 0.8 (−1.6 to −0.04); in 2025 neither does.

### 2. Checks

| Check | Matches | BetOnline − Pinnacle | Better |
|---|---:|---:|---|
| Power method | 9,272 | +0.1 (−0.5 to +0.8) | Tie |
| Shin's method | 9,272 | +0.1 (−0.5 to +0.7) | Tie |
| Retirements included | 9,574 | +0.4 (−0.2 to +1.0) | Tie |
| BetOnline's uncertain closes included | 9,387 | +0.2 (−0.6 to +1.1) | Tie |

**BetOnline's opening line is measurably softer than its close.** On 9,191 matches, BetOnline opening − BetOnline close is +2.7 (+1.1 to +4.2), and BetOnline opening − Pinnacle close is +2.9 (+1.4 to +4.5): the close is better in both. Its opening comes a median of 19 hours before the listed start ([pull results](../../research/betonline-lines/README.md#pulled-from-oddstrader-7-october-2026-utc)).

### 3. Margin

| Same 9,250 matches | Pinnacle | BetOnline | Bet365 | Market average | BetOnline − Pinnacle, points | BetOnline ÷ Pinnacle |
|---|---:|---:|---:|---:|---:|---:|
| **Mean margin, 2024–2025** | **2.79%** | **3.75%** | 5.23% | 5.58% | **+0.96 (+0.95 to +0.98)** | **1.34 (1.34 to 1.35)** |
| Median margin | 2.76% | 3.71% | 5.34% | 5.66% | | |
| 2024 | 2.74% | 3.68% | 5.17% | 5.58% | +0.95 | 1.35 |
| 2025 | 2.84% | 3.82% | 5.29% | 5.58% | +0.98 | 1.34 |
| Men | 2.65% | 3.74% | 5.22% | 5.58% | +1.08 | 1.41 |
| Women | 2.93% | 3.76% | 5.24% | 5.57% | +0.83 | 1.28 |

BetOnline's margin is the wider of the two on 94% of matches (men 97%, women 90%). It varies little: 3.7–3.8% by year and tour, 3.4–4.0% by favourite strength. So the ratio mostly follows Pinnacle's, which is lower on men's matches and much lower on heavy favourites:

| Pinnacle's chance for the favourite | Matches | Pinnacle | BetOnline | BetOnline ÷ Pinnacle |
|---|---:|---:|---:|---:|
| 50–60% | 2,945 | 2.84% | 3.94% | 1.39 |
| 60–70% | 2,748 | 2.85% | 3.41% | 1.20 |
| 70–80% | 2,002 | 2.85% | 3.80% | 1.33 |
| 80–90% | 1,142 | 2.66% | 3.91% | 1.47 |
| 90% and over | 413 | 2.05% | 3.96% | 1.93 |

Every ratio's 95% range is within ±0.05 of it. BetOnline's opening margin (3.79%) is almost the same as its closing one (3.76%), on 9,363 matches.

### 4. Betting at whichever book is better

The owner asked the same day whether holding both books lowers the margin. It does. Take the better price on each side, each side from either book. The market this makes has margin 1/best_w + 1/best_l − 1, which can never exceed the cheaper book's own. It equals it when one book is best on both sides, and it is lower only when the books split the two sides. Below zero would be an arbitrage on paper.

| Same 9,272 completed matches | Pinnacle | BetOnline | Best of both | Best of both − Pinnacle, points | Books split the sides | Best prices sum below one |
|---|---:|---:|---:|---:|---:|---:|
| **2024–2025** | 2.79% | 3.75% | **2.19%** (median 2.34%) | **−0.59 (−0.61 to −0.57)** | 56% | 1.6% |
| 2024 | 2.74% | 3.68% | 2.23% | −0.51 | 55% | 1.0% |
| 2025 | 2.84% | 3.82% | 2.16% | −0.68 | 57% | 2.3% |
| With Bet365 as a third book (9,256 matches) | 2.79% | 3.75% | **1.89%** (median 2.11%) | −0.90 (−0.93 to −0.88) | 71% | 3.7% |

When the books split, the best-of-both margin averages 1.86%. Since the two prices are equally sharp, their disagreements look like noise around the same view, and taking the better side of each disagreement removes about a fifth of Pinnacle's margin.

A bettor backs one side, so the gain shows up as a better price on that side. **On the underdog, BetOnline's price beats Pinnacle's on 36% of matches, and on the favourite on 23%** (Pinnacle's is better on 60% and 62%; the rest are the same price). Taking the better of the two improves the odds by 1.06% on average on the underdog and 0.43% on the favourite, over Pinnacle alone. With Bet365 as well: 1.72% and 0.62%.

**Treat these as an upper bound.** The two closes were not taken at the same moment. Pinnacle's is tennis-data's untimed close; BetOnline's is its last recorded line. Some splits, and probably most of the 1.6% that sum below one, are one book's price before a move and the other's after. Prices taken at one instant would split less often. Limits and account restrictions are not in the data.

## Limitations

* **Untimed closes on both sides.** Pinnacle's close is tennis-data's untimed "most recent before play" price. BetOnline's is the last line OddsTrader recorded, with a time; the 124 uncertain ones were tested in and out with the same result.
* **Main tour only.** tennis-data holds no lower-tier odds. BetOnline's lines on OddsTrader also stop at tour level and Slam qualifying.
* **Ties are tight, not exact.** The paired ranges are about ±0.6 milli-log-loss overall and ±1.1–1.5 for a tour in a year. Differences beyond that are ruled out; smaller ones are not.
* **Margin is not cost alone.** A bettor's cost also depends on limits and on whether either book shades lines for an account; neither is in the data.
* **2026 is not compared.** Pinnacle's odds in tennis-data stop on 13–14 Jan 2026.

## Reproduce

```
./python.sh -m src.ingest.oddstrader --stage-only           # BetOnline's tables from the raw responses
./python.sh src/eda/betonline_lines/sharpness.py           # this study (about a minute)
./python.sh -m pytest test/betonline_lines -q
```
