# Which bookmakers' prices to train the model on and feed it live: recording quality and drift

9 October 2026 · Written for the owner · Research evidence, not a decision.

**The owner's questions** (9 Oct 2026, after the [bet-timing study](../bet_timing/README.md)):
* OddsTrader lists other books besides BetOnline: "Do we have a history here? how much drift do we expect from which sports books used for this?"
* "Id like to keep it as a weighted average of the sharpest books with vig extracted ideally and then do the same live. I plan to betting on betonline, polymarket and pinnacle mostly. If that means training simply pinnacle/betonline after some year than maybe thats it. It seems like scraping from oddsportal live is a hassle and its drifting from training as of now."
* "An idea to check too is if pinnacle/betonline data has potential recording flaws. If we use them as history and some matches show -600/+400 while the oddsportal has it -110/-110 it shows that there may be some data issues and we may want to use the more stable books rather than the outlier."
* "Do some dive into the data quality here and then propose a final suggestion."

**How to read the numbers.**
* **Log loss** is in milli-log-loss (mLL, thousandths of a nat); lower is better. Every price has its margin removed proportionally, as the model's own input.
* **"A − B" in mLL: + = A worse.** Each table says which way it runs.
* **Intervals** are 95%, over four-week blocks. **Better** or **worse** means the interval clears 0. Otherwise the result is **unresolved**, with P(better) = Φ(est/SE).
* **A gross disagreement** is a price over 1.0 in log-odds *and* over 10 points of chance from the median of at least 3 other books that agree among themselves (interquartile range under 0.35).
  * The owner's example, −600/+400 against −110/−110, is 1.45 in log-odds and 31 points.
  * **Swapped** means a gross price that is the mirror image of the others' (the two sides exchanged).

## The answer in short

1. **Yes, there is a history.** OddsTrader serves the last line of about 60 books, not only BetOnline's. It was pulled on 9 Oct for every main-tour match of 2018–2026: 491 requests, no block.
   * About 30 books price the median match in 2018–2021, 23 in 2024–2025 and 11 in 2026.
   * One of them (id 20) is **Pinnacle, with times: opening and last line, January 2018 to 7 September 2025**. It is a second, independent recording of Pinnacle's close.
2. **The closes the model trains on are clean. The real hazards are elsewhere.**
   * Gross disagreements per 1,000 matches:
     * tennis-data's Pinnacle 0.08 (5 of 60,910; in 4 of the 5 the books' average sided with Pinnacle, so the referees were wrong);
     * the books' average 0.18 (12 of 65,330, five of them in 2026);
     * Bet365 0.15;
     * BetOnline 0.03 once lines stamped over 30 minutes after the listed start are dropped.
   * The hazards:
     * **some OddsTrader books' "last line" is an in-play price**, recorded hours after the start;
     * **OddsTrader's copy of Pinnacle failed at the 2021 US Open**;
     * **tennis-data's Pinnacle column stopped being Pinnacle's close in August 2025**, five months before it stopped altogether.
3. **When Pinnacle is the outlier, it is usually right.** In the 95 matches where Pinnacle and BetOnline were more than 0.5 apart in log-odds, the other books sided with BetOnline 83 times. Yet Pinnacle's log loss was lower:
   * than BetOnline's by 53 mLL [13, 92], better;
   * than the other books' median by 34 [2, 66], better.

   So don't drop Pinnacle for disagreeing. Pinnacle moves first.
4. **Drift is real, and it is mostly in the average.**
   * The books' average (the current input) has been less accurate than Pinnacle every season since 2018: +0.74 mLL [+0.43, +1.05] over 2018–2025 (+ = the average worse). Its margin went from 5.2% (2018) to 6.2% (2026).
   * Pinnacle's margin crept from 2.5% to 2.85%.
   * BetOnline: +0.59 [+0.26, +0.92] behind Pinnacle, with no trend by season.
   * Each book's calibration moves from season to season, but every book moves together. Choosing a book adds no calibration drift of its own.
5. **The weighted average you asked for, fitted on the data, is Pinnacle alone.**
   * Walk-forward weights put 0.9–1.4 on Pinnacle and −0.4 to +0.1 on BetOnline, about 0 since 2023.
   * Pinnacle beats the books' average by 0.67 mLL [0.34, 1.00] (better).
   * The equal Pinnacle + BetOnline average is 0.17 [0.00, 0.34] behind Pinnacle (worse).
6. **The model, retrained on "Pinnacle first" and fed a faithful Pinnacle close, is level with the current model fed the books' average:** −0.02 mLL [−0.34, +0.31], unresolved (P(better) 0.46). It beats the current model fed BetOnline's own line by +0.41 [+0.05, +0.76], better (+ = Pinnacle first more accurate). It is right-sized: realisation 1.06.
7. **Suggestion: train on Pinnacle first and feed Pinnacle's current line live, at all three venues.**
   * Train on Pinnacle's close from its two recordings, with BetOnline's last line where Pinnacle has none (August 2025 on), keeping every season from 2013.
   * Feed Pinnacle's current margin-free line, from the guest service its website reads; BetOnline's where Pinnacle has none yet.
   * Record both from now. Drop the OddsPortal average. Treat a gross gap between the live prices as a reading error to skip, not an outlier to average away ([§ 6](#6-the-suggestion-what-to-train-on-and-what-to-feed-venue-by-venue)).

## Data

| Source | What | Accessed | Limits |
|---|---|---|---|
| tennis-data.co.uk, via Stage 1 of the [frozen reference](../../../data/studies/current_best_model/reference_2026-10-08/README.md) | The model's 67,226 matches, 2013–2026: the books' average (OddsPortal's), the maximum, Pinnacle, Bet365, with the results | Files of 5–7 Oct 2026 | Untimed closes ("generally the most recent before play starts", the provider's claim) |
| tennis-data, the sharp benchmark's loader | Expekt and Ladbrokes (to 2018), Betfair exchange (from Aug 2025), joined on tour, day, winner and loser | Same files | As above |
| OddsTrader's odds service (`src/ingest/oddstrader.py --books-eids`) | Every book's last match-winner line and Pinnacle's opening line, with times, for the 39,666 events linked to tennis-data's 2018–2026 rows; 39,197 of them are the model's matches | 9 Oct 2026, 14:42–15:15 UTC: 491 requests, all HTTP 200 | Raw prices are not committed (the repository is public). Names for 14 of the 60 ids ([research](../../research/betonline-lines/README.md#pulled-from-oddstrader-9-october-2026-utc-every-books-last-line-20182026)) |
| Polymarket | The 30-minute price of the sharp benchmark's table, 2025–2026 | As that study | 4,914 of the model's matches |
| Pinnacle's website | Four probe requests: live matchups and moneylines from the guest service its pages use | 9 Oct 2026 | Live only, no history |

## 1. What we hold, book by book

| Book | Where | Seasons | Coverage of the model's matches |
|---|---|---|---|
| **Pinnacle** | tennis-data | 2005 – 13 Jan 2026; **Pinnacle's own close only to July 2025** (§ 2.1) | 98–100% a season to 2024 |
| **Pinnacle** | OddsTrader (id 20), opening and last line, timed | Jan 2018 – 7 Sep 2025 | 76–96% a season |
| **BetOnline** | OddsTrader (id 8), opening and last line, timed | 2018 – now | 72–79% in 2018–19, 90–97% since |
| **The books' average and maximum** | tennis-data (OddsPortal's panel) | 2010 – now | 100% |
| **Bet365** | tennis-data; OddsTrader ids 5 and 106 | 2003 – now | ~100% |
| Betfair exchange | tennis-data | Aug 2025 – now | 25% of 2025, 95% of 2026 |
| Polymarket | Its own API (sharp benchmark) | 2025 – now | 749 of 2025's matches, 4,165 of 2026's |
| About 55 more books (Bookmaker, Heritage, Bovada, SBK, Bet105, MyBookie, Everygame, BetAnything, …) | OddsTrader | Each its own span | Median books a match: 30 (2018), 33 (2021), 28 (2023), 23 (2025), **11 (2026)** |

Pinnacle's live prices are readable without logging in: its website's guest service returned 106 upcoming matchups with moneylines on 9 Oct ([research](../../research/early-lines/README.md#update-9-october-2026-pinnacle-on-oddstrader-and-pinnacles-own-site)). OddsTrader's live lines come through the existing adapter.

## 2. Recording quality

### 2.1 Pinnacle recorded twice

tennis-data's untimed Pinnacle close against the last Pinnacle line OddsTrader recorded, on the same matches ([quality_tables.md](../../../data/studies/odds_sources/quality_tables.md) § 1):

| Season | Matches | Same price | Median gap (log-odds) | Gap over 1.0, per 1,000 | tennis-data − OddsTrader, mLL |
|---|---:|---:|---:|---:|---|
| 2018–2020 | 10,177 | 69–78% | 0.002–0.003 | 0–0.2 | +0.04, +0.06, −0.09: unresolved |
| 2021 | 4,344 | 61% | 0.003 | 26.0 | −7.16 [−20.30, +5.97], unresolved |
| 2022–2024 | 14,566 | 71–74% | 0.003 | 0–0.4 | −0.16, −0.19, +0.06: unresolved |
| 2025 (to 7 Sep) | 4,059 | 55% | 0.004 | 1.5 | +0.70 [−0.31, +1.72], unresolved (P(tennis-data better) 0.09) |

* **The two agree to the cent most of the time.** The median gap of 0.003 is under a tenth of a point of chance.
* **The gross gaps are OddsTrader's.** There are 118. In 115 of them OddsTrader's price was off the other books and tennis-data's was not. 101 are the **2021 US Open**, where OddsTrader's Pinnacle lines are squashed toward 50%: 63% for a favourite every other book had at 93%. On them, tennis-data − OddsTrader is −138 mLL [−197, −79] (tennis-data better).
* **tennis-data's column changes in August 2025.** By month, it matched Pinnacle's own last line (both sides the same price) on:
  * 55–72% of matches from October 2024 to June 2025, with a median gap of 0.002–0.004;
  * 50% in July (gap 0.008);
  * **14% in August and September**, with the median gap ten times wider (0.039 and 0.046).

  *Inference:* from August 2025 tennis-data's PSW/PSL are not Pinnacle's close. They continue to January 2026 all the same. Pinnacle closed its public API on 23 July 2025, and OddsTrader's Pinnacle stops on 7 September. This is also the month the books' average changed its panel (the [input audit](../input_data_audit/README.md) § 5).

### 2.2 Each source against the other books

Each source is compared with the median of the other books on the same match ([quality_tables.md](../../../data/studies/odds_sources/quality_tables.md) § 2):

| Source | Matches | Median gap | Gross per 1,000 | Gross, swapped | Who the result sided with on the gross ones |
|---|---:|---:|---:|---:|---|
| Pinnacle, tennis-data | 60,910 | 0.049 | **0.08** | 5, 3 | Pinnacle's favourite won 4 of 5; 4 of the 5 agree with the books' average, so the referees were off |
| The books' average | 65,330 | 0.017 | **0.18** (2026: 1.2) | 12, 3 | Five are 2026 matches, among them a Wimbledon semifinal with the sides swapped |
| Bet365, tennis-data | 65,207 | 0.042 | 0.15 | 10, 4 | — |
| BetOnline, OddsTrader | 37,837 | 0.032 | 0.69 as recorded; **0.03** without lines stamped over 30 min late | 26, 1 | 25 of the 26 were stamped over 30 minutes after the listed start (median 9 h) |
| Pinnacle, OddsTrader | 33,223 | 0.042 | 3.25 | 108, 18 | Its own favourite won 42% of the 45 splits: recording failures (2021 US Open) |
| Betfair exchange, tennis-data | 5,311 | 0.051 | 0.38 | 2, 1 | — |

**On the owner's example:** a −600/+400 against a −110/−110 happens about once in 5,000–12,000 matches in the closes the model trains on. When it involves Pinnacle, Pinnacle is usually the one that's right (§ 2.4).

### 2.3 In-play prices in OddsTrader's last lines

**For some books, the last line OddsTrader recorded is an in-play price.** Their gross disagreements were stamped hours after the listed start, and they were "too right":

| Book | Gross per 1,000, as recorded | Stamped (median min after listed start) | Its favourite won, on the splits | Gross per 1,000, lines over 30 min late dropped |
|---|---:|---:|---:|---:|
| OddsTrader id 18 | 71.2 | 112 | 97% of 418 | 0.31 |
| SBK | 18.0 | 111 | 81% of 191 | 0.09 |
| Bovada | 3.9 | 436 | 67% of 67 | 0.00 |
| MyBookie | 2.0 | 95 | 82% of 28 | 0.28 |
| Bookmaker | 0.8 | 148 | 85% of 13 | 0.13 |

* **Two ids stay faulty after the rule.** Id 88 is not a match-winner line at all (738 gross per 1,000). Id 63 sides against the result (2.6 per 1,000, 17% of its splits).
* **BetOnline and Pinnacle at OddsTrader show it too.** Their lines stamped over 2 hours after the listed start beat the other books:
  * BetOnline: −17.6 mLL [−57.6, +22.3], unresolved;
  * Pinnacle: −19.3 [−36.3, −2.2], better (+ = the line worse).

  BetOnline's lines stamped before the listed start or up to 30 minutes after it are within 0.2 mLL of the other books, all unresolved.
* **So:** any use of OddsTrader's lines drops those stamped over 30 minutes after the listed start. That is the adapter's rule for BetOnline's closes, now applied to every book in this study. Its median of books is then a usable referee.

### 2.4 When Pinnacle is the outlier

In the 95 matches where Pinnacle's close and BetOnline's last line were more than 0.5 apart in log-odds, with at least 3 other books ([pools_tables.md](../../../data/studies/odds_sources/pools_tables.md)):
* the other books sided with BetOnline 83 times, and with Pinnacle 12 times;
* Pinnacle − BetOnline: **−53 mLL [−92, −13], Pinnacle better**;
* Pinnacle − the other books' median: **−34 [−66, −2], Pinnacle better**;
* BetOnline − the other books' median: +19 [−2, +40], unresolved (P(BetOnline better) 0.04);
* the favourite won 97% of the time by Pinnacle's pick, 94% by BetOnline's.

A rule that drops the book furthest from the others (the "guard") made the Pinnacle + BetOnline average worse: +0.21 mLL [+0.02, +0.40] against Pinnacle alone, versus +0.17 unguarded (+ = worse). Part of Pinnacle's lead may be timing: its tennis-data close is untimed and may be later than BetOnline's last line. Even so, **dropping Pinnacle for disagreeing throws away the sharpest information.**

## 3. Drift

### 3.1 Margins (median overround − 1, %)

| Season | Books' average | Pinnacle | BetOnline | Bet365 |
|---|---:|---:|---:|---:|
| 2013 | 6.11 | 2.49 | — | 6.86 |
| 2018 | 5.16 | 2.54 | 3.27 | 6.67 |
| 2021 | 5.44 | 2.63 | 3.41 | 5.56 |
| 2024 | 5.65 | 2.71 | 3.59 | 5.33 |
| 2025 | 5.67 | 2.81 | 3.92 | 5.33 |
| 2026 | **6.19** | 2.85 (to Jan) | 3.98 | 5.33 |

Every season: [drift_tables.md](../../../data/studies/odds_sources/drift_tables.md).

### 3.2 Accuracy against Pinnacle, season by season

On the 31,834 matches of 2018–2025 that every source prices (mLL, + = the source worse than tennis-data's Pinnacle close):

| Season | Books' average | BetOnline | Bet365 | OddsTrader's median |
|---|---|---|---|---|
| 2018 | +0.93 [−0.03, +1.88] | +0.46 [−0.50, +1.42] | +1.81 | +0.88 |
| 2019 | +0.84 | +0.71 | +1.38 | +0.98 |
| 2020 | +0.73 | −0.11 | +0.86 | +0.65 |
| 2021 | +1.10 [+0.24, +1.96] | +0.73 | +1.86 | +0.99 |
| 2022 | +1.01 | +1.24 [+0.10, +2.38] | +0.96 | +0.91 |
| 2023 | +0.54 | +0.75 | +0.93 | +0.89 |
| 2024 | +0.69 | −0.07 | +1.01 | +0.29 |
| 2025 | +0.05 | +0.65 | +0.60 | +0.33 |
| **2018–2025** | **+0.74 [+0.43, +1.05], worse** | **+0.59 [+0.26, +0.92], worse** | **+1.18 [+0.81, +1.55], worse** | **+0.74 [+0.42, +1.07], worse** |

* **2013–2025** (62,256 matches): the average +0.60 [+0.34, +0.86], worse; Bet365 +0.91, worse.
* **"BetOnline got way sharper"** is not visible at the close. It trails Pinnacle by 0.6 mLL on average, and season by season it moves between −0.1 and +1.2 with no trend. Its margin rose (3.3% → 4.0%).
* **The average is the one that moved.** Its 2025 reading (+0.05) mixes in the August panel change, and its gross errors rose in 2026 (§ 2.2).

### 3.3 Calibration and drift cost

* **The slope by season** (1 = calibrated; above 1 = too timid: favourites win more often than the price says):
  * Pinnacle 0.98–1.07;
  * BetOnline 1.00–1.10;
  * the books' average 1.02–1.14, always the most timid.
* **All books move together:** every one is lowest in 2025 (0.98–1.02) and higher again in 2026.
* **The drift cost** is the log loss lost by using the slope of earlier seasons instead of the season's own. It is the same size for every book: 0.0–0.4 mLL a season, mostly under 0.1, and every interval spans 0.
* **So the season-to-season wobble belongs to the sport, not to the book.** Switching books adds none.

### 3.4 Pinnacle's opening line

* OddsTrader's first recorded Pinnacle line came a median **35.5 hours** before the listed start (10th–90th percentile 15–71 h), on 32,701 matches.
* It is **3.94 mLL [2.18, 5.69] worse** than Pinnacle's last line there, and 4.90 [3.84, 5.96] worse than tennis-data's close.
* For comparison, BetOnline's opening (a median 19 h out) was 2.7 behind its close in 2024–2025 ([BetOnline study](../betonline_lines/README.md)).
* **Pinnacle's early line is softer too.** The [bet-timing study](../bet_timing/README.md) found the model inherits nearly all of its input's softness, so betting earlier *at Pinnacle* should buy little. The timing gain comes from venues that lag Pinnacle.

## 4. Averages of several books

On the 28,891 matches of 2019–2025 where every candidate is defined (mLL, + = the candidate worse):

| Candidate | − the books' average (current input) | − Pinnacle | P(candidate better than Pinnacle) |
|---|---|---|---:|
| Pinnacle (tennis-data) | **−0.67 [−1.00, −0.34], better** | — | — |
| Pinnacle, its two recordings reconciled | −0.68 [−1.01, −0.35], better | −0.01 [−0.13, +0.11], unresolved | 0.57 |
| BetOnline | −0.06 [−0.38, +0.26], unresolved | +0.61 [+0.27, +0.96], worse | 0.00 |
| Pinnacle + BetOnline, equal | −0.50 [−0.77, −0.23], better | +0.17 [+0.00, +0.34], worse | 0.02 |
| … with the guard (§ 2.4) | −0.46 [−0.74, −0.17], better | +0.21 [+0.02, +0.40], worse | 0.02 |
| Weighted, walk-forward | −0.64 [−0.98, −0.30], better | +0.03 [−0.03, +0.09], unresolved | 0.14 |
| Weighted, with the average as a third input | −0.64 [−1.04, −0.24], better | +0.03 [−0.08, +0.15], unresolved | 0.30 |
| OddsTrader's median of books | +0.05 [−0.12, +0.22], unresolved | +0.72 [+0.38, +1.07], worse | 0.00 |

* **The walk-forward weights** (normalised; fitted on the seasons before):

  | Season | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
  |---|---:|---:|---:|---:|---:|---:|---:|---:|
  | Pinnacle | 1.28 | 1.41 | 0.98 | 0.89 | 1.04 | 1.05 | 0.97 | 0.98 |
  | BetOnline | −0.28 | −0.41 | 0.02 | 0.12 | −0.04 | −0.06 | 0.03 | 0.02 |

  BetOnline's weight rose from below 0 to about 0: it got closer to Pinnacle, but once Pinnacle is known it adds nothing.
* **Searched:** 9 candidates on 2019–2025, the seasons that also chose the current model's inputs. Pinnacle won by a clear margin. The close runners-up (reconciled, weighted) are Pinnacle by another name.

**2026, without Pinnacle** (3,814 matches; mLL, + = the candidate worse):

| Candidate | − the books' average | − BetOnline |
|---|---|---|
| BetOnline | −0.36 [−1.64, +0.91], unresolved (P(better) 0.71) | — |
| OddsTrader's median | −0.63 [−1.76, +0.49], unresolved | −0.27 [−0.83, +0.29], unresolved |
| Betfair exchange | −1.06 [−2.68, +0.55], unresolved | −0.70 [−1.54, +0.13], unresolved |
| BetOnline + Betfair | −0.99 [−2.55, +0.57], unresolved | **−0.63 [−1.11, −0.15], better** |
| BetOnline + Polymarket, 30 min before the listed start | **−2.36 [−4.55, −0.17], better** | **−2.00 [−3.34, −0.66], better** |

* **In 2026 the books' average is no better than BetOnline alone.**
* **A second sharp price helps:** Polymarket's near-start price, or Betfair's close.
  * Polymarket's is taken 30 minutes before the listed start, so it knows no more than a bettor then.
  * Betfair's close is untimed and may be later than BetOnline's last line.

## 5. The model retrained on "Pinnacle first"

**The arm** (`fits_cons_trained.py --arm pf`, one declared test, 28 GPU fits, 19 minutes). It is the current model's 58 inputs and settings, season Y trained on 2013 .. Y − 1, seeds 0–3, calibrated walk-forward per tour, as the bet-timing study's other retrained arms. Its odds input in training, as the walk-forward weights pointed:
* Pinnacle's close from its two recordings, tennis-data's only to July 2025 (`pools.py`, `pf`): 99.5% of rows to 2024;
* BetOnline's last line where Pinnacle has none (889 rows in 2025, 3,239 in 2026);
* the books' average where neither prices the match (under 1% of rows; 7% of 2026's).

**Scored as in the bet-timing study's § 7:** at BetOnline's last line, 2020–2025, 25,637 matches, debut seasons out. mLL against the current model fed BetOnline's own line, + = more accurate ([cons_trained_tables.md](../../../data/studies/bet_timing/cons_trained_tables.md)):

| Price fed | Current model (books' average) | Retrained P + B | Retrained BetOnline | **Retrained Pinnacle first** |
|---|---|---|---|---|
| BetOnline's own line | 0 (the baseline) | +0.08 [−0.11, +0.26] | +0.06 [−0.10, +0.22] | +0.08 [−0.14, +0.31] |
| Pinnacle's close | +0.12 [−0.26, +0.50] | +0.33 [−0.04, +0.70] | +0.29 [−0.07, +0.65] | +0.36 [−0.02, +0.75] |
| Pinnacle + BetOnline | +0.20 [+0.01, +0.40] | +0.34 [+0.11, +0.58] | +0.31 [+0.09, +0.53] | +0.35 [+0.09, +0.62] |
| The books' average | **+0.42 [+0.06, +0.79]** | — | — | — |
| A faithful Pinnacle close (its own construction) | — | — | — | **+0.41 [+0.05, +0.76]** |

Direct comparisons. The declared primary is the first row (+ = Pinnacle first more accurate):

| Pinnacle first, fed a faithful Pinnacle close, against … | All last lines (25,637) | Stamped within 1 h of the start (16,025) |
|---|---|---|
| **the current model fed the books' average** | **−0.02 [−0.34, +0.31], unresolved (P(better) 0.46)** | +0.14 [−0.28, +0.57], unresolved (P 0.75) |
| the current model fed BetOnline's own line | +0.41 [+0.05, +0.76], better | +0.49 [−0.02, +1.00], unresolved (P 0.97) |
| the current model fed Pinnacle's close | +0.29 [−0.01, +0.58], unresolved (P 0.97) | +0.33 [−0.09, +0.75], unresolved (P 0.94) |
| the P + B model fed P + B | +0.06 [−0.13, +0.25], unresolved (P 0.74) | +0.12 [−0.16, +0.39], unresolved (P 0.80) |

* **It matches the current model fed the books' average,** without needing the average.
  * 2020–22: +0.05; 2023–25: −0.07; both unresolved.
  * The 90% interval, [−0.29, +0.25], is too wide to call the two equivalent below a third of a milli-log-loss.
* **The realisation gate passes.** How much of the model's disagreement with its price comes true (1 = right-sized):
  * 1.06 [0.74, 1.37] against its own input, and 1.00 [0.76, 1.24] against BetOnline's line;
  * the current model: 1.12 and 1.02.
* **At BetOnline's opening,** fed the opening line: +0.25 [+0.00, +0.49] against the current model fed the same, better (borderline). P + B +0.22, BetOnline +0.24.
* **Money at BetOnline's last line,** the owner's staking, fed its own construction:
  * threshold 0: +1.9% [+0.6, +3.1] per unit staked on 10,199 bets;
  * against the baseline: +0.37 units per 100 matches [−0.68, +1.41], unresolved;
  * at 2% and 5% thresholds, also unresolved.

## 6. The suggestion: what to train on and what to feed, venue by venue

**Train on Pinnacle first.**
* Pinnacle's margin-free close from its two recordings. tennis-data's is good to July 2025; OddsTrader's timed one settles any difference and runs to 7 September 2025.
* BetOnline's last line where Pinnacle has none: so far August 2025 to now, about 5,000 matches.
* The books' average only where neither prices a match (under 1%).
* **Keep every season from 2013.** No need to start "after some year": Pinnacle's faithful closes go back to 2005, and the [training-window study](../training_window/README.md) found no shorter window better.

This *is* the weighted average of the sharpest books you asked for, with the weights fitted on the data: about all on Pinnacle (§ 4).

**Feed it, at every venue and any time, the same thing live:**
* Pinnacle's current margin-free line, from the guest service its website reads;
* BetOnline's current line (OddsTrader's adapter) when Pinnacle has none yet.

| Venue | What the model sees | Where an edge comes from |
|---|---|---|
| **Pinnacle** | Its own price | Only the model's other inputs. The [bet-timing study](../bet_timing/README.md): the model inherits nearly all of its input's softness, and Pinnacle's own early line is softer (§ 3.4). So betting Pinnacle earlier buys little; bet where the edge clears its ~2.8% margin |
| **BetOnline** | Pinnacle's price | BetOnline lagging Pinnacle (its opening is 2.7 mLL softer than its close, its close 0.6 behind Pinnacle's), plus the model's inputs |
| **Polymarket** | Pinnacle's price | Polymarket lagging: its 24–48-hour prices were the softest in the bet-timing study |

**Around it:**
1. **Record from now:** Pinnacle's and BetOnline's lines with their times for every main-tour match (a recorder on Pinnacle's guest feed and on OddsTrader). Future fits then have Pinnacle again for 2026 on, and early-price tests become possible.
2. **A reading check, not a modelling rule.** If the Pinnacle price read live differs from BetOnline's and Polymarket's by a gross amount (over 1.0 in log-odds and 10 points), don't bet that match. It is far likelier to be our own mistake (wrong match, swapped sides) than Pinnacle's: at the close a genuine gap that size occurs about once in 10,000 matches, and when Pinnacle disagrees it is usually right (§ 2.4).
3. **Drop the OddsPortal average.** No live scraper is needed. Its book set changed in August 2025, it is the most timid of the prices, and its gross errors rose in 2026.
4. **Don't feed OddsTrader's other books.** Their median is no better than BetOnline, and their number halved in 2026. They remain useful as a referee, with lines stamped over 30 minutes late dropped.
5. **Building it for real** goes through the decided procedure: a candidate build of the template (`run_chain.py --setup --candidate`, seeds 0–15, with the speed stage), then `compare.py --candidate`. The arm here used the bet-timing study's frame, seeds 0–3 and no speed stage.

**The suggestion line** (the [adoption framework](../adoption_framework/README.md) § 7):
* **Target:** bets at BetOnline, Pinnacle and Polymarket, between the opening and the close. Pinnacle's current margin-free line is fed; main tour; scored at BetOnline's last line, 2020–2025.
* **Provenance:** the owner's mechanism (a weighted average of the sharp books). This study's price comparison (9 candidates on 2019–2025) pointed to one declared model arm. It was tested on seasons that also chose the current model's inputs.
* **Cost class:** a new live dependency, c ≈ 0.05 mLL. The input that matches it, the OddsPortal average, needs a harder dependency of its own: encoded, region-dependent and drifting.
* **Against the current model fed BetOnline's line** (the no-new-feed status quo): est +0.41, SE 0.18. With τ = 0.2, B = 0.55. sel ≈ 0.18 if counted as the best of four retrained arms. B·(est − sel) ≈ 0.12 > c.
* **Against the current model fed OddsPortal's average:** est −0.02, so B·est ≈ 0. Accuracy does not choose between them; the live feed does.
* **Gates:** bet-time existence passes (Pinnacle's guest feed answered; BetOnline is already read); fallback is BetOnline's line; realisation is 1.06.
* **Outcome:** **adopt on a logged lean**, as a candidate build, once the live Pinnacle recorder exists. Until then, shadow it beside the current model.
* **What would change it:**
  * the candidate build reading clearly worse than the reference;
  * Pinnacle's guest feed failing or being withheld at bet time;
  * Pinnacle's live prices drifting away from its closes.

## 7. What it does not show

* **Closes, not mid-way prices.** Every accuracy here is at the close. Pinnacle's own early line is softer (§ 3.4), and BetOnline's too. What a mid-way price costs the model was measured in the bet-timing study: it inherits nearly all of the input's softness.
* **Untimed closes.** tennis-data's Pinnacle and average closes carry no time. Some of Pinnacle's lead on big disagreements (§ 2.4) may be a later price.
* **The 2019–2025 seasons chose the current model's inputs.** The ranking of prices here is not a choice made on them; it is a comparison of prices against results. The model-level test (§ 5) is one declared arm.
* **2026 rests on one season** without Pinnacle (3,814 matches). Its intervals are 1–2 mLL wide.
* **Names.** 46 of the 60 OddsTrader ids are unnamed; only Pinnacle, BetOnline and the named books are used in the suggestion.
* **Limits and account restrictions** are not in the data.

## Files and reproduce

| Step | Code | Output |
|---|---|---|
| Every book's lines | `src/ingest/oddstrader.py --books-eids` (new mode) | `data/raw/oddstrader/books/`, `data/dump/odds/oddstrader/books_lines.parquet` (gitignored) |
| The link and the table | `src/eda/odds_sources/table.py --link`, `--build` | `oddstrader_link.parquet`, `sources.parquet` (gitignored); `oddstrader_eids.csv`, `link_counts.json`, `sources_counts.json` |
| Recording quality | `src/eda/odds_sources/quality.py` | `quality.json`, `quality_tables.md` |
| Drift | `src/eda/odds_sources/drift.py` | `drift.json`, `drift_tables.md` |
| Averages of books | `src/eda/odds_sources/pools.py` | `pools.json`, `pools_tables.md`, `pools.parquet` (gitignored) |
| The retrained model | `src/eda/bet_timing/fits_cons_trained.py --arm pf`, `score_cons_trained.py` | `data/studies/bet_timing/local_cons_trained/pf__*.npz`, `results_cons_trained.json`, `cons_trained_tables.md` |
| Tests | `test/odds_sources/` (9), `test/betonline_lines/` (2 new for the adapter) | |

```
./python.sh -m src.ingest.oddstrader --books-eids data/studies/odds_sources/oddstrader_eids.csv --max-requests 600
./python.sh src/eda/odds_sources/table.py --link       # before the pull: the event ids
./python.sh src/eda/odds_sources/table.py --build
./python.sh src/eda/odds_sources/quality.py            # about 5 minutes
./python.sh src/eda/odds_sources/drift.py
./python.sh src/eda/odds_sources/pools.py
bash src/eda/bet_timing/run_when_free.sh src/eda/bet_timing/fits_cons_trained.py --run --arm pf   # 28 GPU fits, ~30 min
./python.sh src/eda/bet_timing/score_cons_trained.py
./python.sh -m pytest test/odds_sources test/betonline_lines -q
```
