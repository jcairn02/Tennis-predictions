# Part F: the odds input where Pinnacle's close is missing (subagent 5's report)

16 Oct 2026 · Written by subagent 5 for the lead; saved here by the lead because the harness refused the subagent's own write of this file. The text below is the subagent's report as returned, unedited apart from this header. The lead's re-checks are in the study's process log and README, not here.

## Summary

**Template frame** (`template_2026-10-14`, 67,226 rows; `template_counts.json`):
- **4,993 rows carry BetOnline** as their odds input: 4,976 from 1 Aug 2025, plus 17 isolated rows from 2021–25.
- **537 rows carry neither Pinnacle nor BetOnline** (the books' average): 305 from Aug 2025, 232 earlier.
- The gap rows number 5,281: 4,340 played before the seal (4,086 BetOnline, 254 average) and 941 sealed.
- Re-running `odds_input.construct` reproduces the frame's input on all rows.

**The best stand-in, against results.** It is the equal log-odds average of BetOnline's last line, Betfair's close and Polymarket's price 30 minutes before the start. It uses whichever of the three price the match, else the books' average (rule `sharp3`). On all 4,340 gap rows before the seal, against today's rule:
- **−1.79 mLL [−2.75, −0.82], better** (+ = candidate worse throughout).
- It survives Holm across the 31 declared readings, and 12 of 13 four-week blocks are negative.
- After each price gets its own calibration slope: −1.46 [−2.30, −0.62]. So the gain is information, not calibration.
- With Polymarket's 60-minute price instead: −1.47 [−2.39, −0.55].
- Polymarket is what does the work. The BetOnline + Betfair rule is worse than `sharp3` by +1.12 [+0.27, +1.97]. Adding OddsTrader's median changes nothing (+0.14, unresolved).
- The gain is resolved in 2026 (−2.09) and for women (−2.89). It is unresolved for Aug–Nov 2025 (−0.68, P 0.91) and for men (−0.73, P 0.89).

**No single price beats BetOnline alone** with a resolved interval: −0.4 to −0.9 mLL, P(better) 0.66–0.95. Betfair's −0.56 drops to −0.06 after calibration.

**tennis-data's PS after July 2025** are probably Pinnacle prices taken before the close (inference):
- Pinnacle's 2.8% margin is kept every month.
- Same price as Pinnacle's last line on 14% of matches (50–72% before); as its opening on 2–3%.
- About 73–89% of the late line move is made, against about 88–105% before.
- Worse than Pinnacle's own close by +3.05 [+0.06, +6.05].
- They cover only 21% of the gap rows, so they are unusable.

**The Pinnacle proxy:**
- Out of sample it is nearer Pinnacle than BetOnline in every season 2019–2025.
- But it leans 0.71–0.85 on the books' maximum, which tracked Pinnacle only until the August 2025 panel change.
- In the gap it is unresolved against BetOnline: −1.19 [−2.72, +0.35]. I don't recommend it.

**Bet105** (OddsTrader id 130) is the book nearest Pinnacle's own close after the change: KL 0.200 mLL, against 0.387 for BetOnline. That reads no result. Against results it is unresolved, and its rule is worse than `sharp3` by +1.55 [+0.55, +2.55].

**Checks:**
- **Hand checks all agree:** 10 tennis-data, 5 BetOnline, 5 Bet105, 5 Polymarket (traced to the raw minute price history) and 5 each for my two joins. Side A was identified by name from the Stage 0 snapshot.
- **The seal held:** results are read through a parquet filter on both dates.
- **Live Stage 0 unchanged:** it still matches the manifest's SHA-256.
- **One slip:** a stray system `python -c "print(1)"` ran once at the start. It ran no project code.

**Recommendation:**
- Use `sharp3` as the stand-in, as a candidate build.
- I read it as a repair of training rows only: the live input stays Pinnacle's current line.
- `compare.py`'s 2020–2024 window holds none of the affected rows, so the decided comparison cannot see this change.
- The rule needs the Betfair columns and the sharp benchmark's Polymarket table at build time, not live. That table was last refreshed 5 Oct 2026.

---

### Conventions
- Prices are made margin-free proportionally, as `odds_input.py` does. Combinations average log-odds. Differences are in mLL, **candidate − base, + = the candidate worse**.
- 95% intervals cluster on four-week blocks.
- **P(better)** uses the interval's t distribution on G−1 degrees of freedom, not Φ. This departs from odds_sources: with 3–13 blocks, Φ overstated P.
- Labels: *observed* (computed here) / *inference* / *unknown*.

### 1. What I built
All code is in `src/eda/source_reconciliation/`. Run in this order: `odds_coverage` → `odds_psx` → `odds_proxy` → `odds_score` → `odds_checks` → `odds_summary`.
- **`odds_common.py`** loads the template's `odds_sources.parquet` without `a_won`. It drops late OddsTrader lines (`quality.drop_late`) and attaches `odds_input.construct`'s kind and `pools.reconciled`'s Pinnacle. Its `results()` reads `a_won` only through a pyarrow filter (`tournament_date` and `td_date` both before 2026-07-29), then asserts it.
- **`odds_coverage.py`** gives template counts and coverage of the gap rows. It reads no result.
- **`odds_psx.py`** examines PS after July: identity, timing slopes, and accuracy by period.
- **`odds_proxy.py`** fits the proxies (per-pattern least squares, no intercept) and measures KL to Pinnacle. It reads no result.
- **`odds_score.py`** scores every candidate against results, sections A–H.
- **`odds_checks.py`** runs the hand checks.
- **`odds_summary.py`** collects the headline numbers.
- I edited no existing file.

### 2. Output files
**Tracked:**
- `declared.json`: the design (21:15:40 UTC) and the Bet105 addition (21:23:44 UTC).
- `template_counts.json` and `.csv` (`tour, season, odds_input, rows`).
- `coverage.csv` (`tour, month, candidate, rows, priced, share, sealed_rows`) and `coverage.json`.
- `psx.json` / `psx_tables.md`.
- `proxy.json` / `proxy_tables.md` (coefficients per pattern, KL tables).
- `scores.json` / `scores_tables.md`. Each reading has `est, lo, hi, n, blocks, se, p_neg (= P(better)), p_two_sided, ll_a, ll_b`.
- `hand_checks.json` (match ids and flags only) and `summary.json`.

**Gitignored:**
- `gap_prices.parquet`: 5,281 gap rows × `p_<candidate>` (chance of side A), with no result column.
- `hand_checks.parquet`.

### 3. Definitions
- **Gap rows:** `td_date ≥ 2025-08-01` and the model's input is BetOnline or the average. Of the 5,281, 4,340 are scored.
- **Declared candidates:**
  - Singles: `bol`, `bfe`, `pm` (30 min), `psx`, `b365`, `avg`, `max`, and `otmed`.
  - `otmed` is the median of OddsTrader's other books, at least 3. It leaves out ids 8, 131 and 20, and ids 88 and 63 (found faulty earlier).
  - 9 equal and 4 walk-forward combinations, 4 proxies and 6 full-coverage rules.
- **Added after a results-free distance check:** `b105` and `b105_pre`.
- **Rules:** a mean over whichever members price the match, else the average. Today's rule equals the model's input on every gap row.
- **`sharp3` composition before the seal:** all three prices on 3,659 rows, two on 553, one on 108, none on 20.
- **Walk-forward weights** are refitted per block on all earlier rows from 2018 and normalised. A block needs at least 500 training rows, so the Polymarket sets start in Jan 2026.
- **Aside:** OddsTrader's Pinnacle actually runs to 15 Sep 2025 for 57 matches of 8–18 Sep. Those are Pinnacle rows, not gap rows.

### 4. Results

**4.2 Coverage of the 4,340 rows before the seal**

| Price | Coverage | Notes |
|---|---:|---|
| BetOnline | 94.1% | 89–100% every month |
| Betfair | 94.4% | from 17 Aug 2025; 57–64% in April 2026 |
| Polymarket 30 min | 92.3% | none in Aug 2025; 65–74% in Sep 2025; 88–98% after |
| PS after July | 21.3% | Aug 2025 – mid-Jan 2026 only |
| Bet365 | 99.3% | |
| Average | 100% | |
| Maximum | 92.6% | |
| OddsTrader median | 97.5% | 9–11 other books per row from Feb 2026, 18–21 before |
| Bet105 | 89.0% | |
| All three (BetOnline, Betfair, Polymarket) | 84.3% | |

The tour × month breakdown is in `coverage.csv`.

**4.3 What PS is after July 2025**
- **Margin:** median overround 1.0277–1.0295 every month, Aug 2025 – Jan 2026 (1.0256–1.0323 before).
- **Same price:** as Pinnacle's last line on 14% of matches (50–72% before); as its opening on 2–3%; as BetOnline on 3–5%.
- **Bet105** is the book most often at PS's price, both before (17–28%) and after (15–34%).
- **Timing slope**, the share of a line's opening-to-last move that PS has made:
  - against Pinnacle's own move: 0.95–1.00 before → 0.87 (Aug) and 0.83 (Sep);
  - against BetOnline's move: 0.88–1.05 before → 0.73–0.89 after;
  - Pinnacle's own last line against BetOnline's move: 0.91–1.04.
- **Against results:**
  - PS − Pinnacle's close: +0.26 (Oct 2024 – Jul 2025); **+3.05 [+0.06, +6.05], worse** (1 Aug – 7 Sep 2025, match-day clusters).
  - PS − BetOnline: −1.28 [−3.88, +1.32], unresolved (8 Sep 2025 – Jan 2026).
- **Inference:** these are Pinnacle prices taken some hours before the close.
- **Unknown:** exactly when, and by which route they reached tennis-data.

**4.4 Distance to Pinnacle (no result read)**

In the post-change window (1 Aug – 7 Sep 2025, 538 matches), KL(Pinnacle‖candidate) in mLL, lower = nearer:

| Candidate | KL | − BetOnline |
|---|---:|---|
| Bet105 | 0.200 | −0.165 [−0.237, −0.092] |
| BetOnline + Bet105 | 0.204 | |
| Proxy with Bet105 | 0.241 | |
| Proxy | 0.308 | −0.079 [−0.157, −0.001] |
| BetOnline + Betfair | 0.311 | −0.137 [−0.209, −0.064] |
| OddsTrader median | 0.369 | |
| **BetOnline** | **0.387** | — |
| Maximum | 0.411 | |
| Average | 0.513 | |
| Bet365 | 0.545 | |
| PS after July | 0.613 | |
| Betfair | 0.622 | +0.174 [+0.067, +0.282] |

- Polymarket has no overlap with Pinnacle's close, so its distance is **unknown**.
- **Walk-forward by season, 2019–2025:** proxy KL 0.24–0.67 against BetOnline's 0.34–0.93. The proxy is nearer in every season (−0.09 to −0.32, all resolved).
- **Maximum:** KL 0.14–0.61 a season (0.14–0.34 outside 2021), 0.29 in 2025 to July, 0.41 after the change. The proxy puts 0.71–0.85 weight on it.

**4.5 Against results: gap rows before the seal**

*A. Primary: each candidate − BetOnline, on matches both price*

| Candidate | Matches | − BetOnline | Verdict |
|---|---:|---|---|
| Betfair | 3,876 | −0.56 [−1.85, +0.73] | unresolved, P 0.82 |
| Polymarket | 3,850 | −0.93 [−3.20, +1.34] | unresolved, P 0.81 |
| PS after July | 894 | −0.49 | unresolved, P 0.67 |
| Bet365 | | −0.46 | unresolved, P 0.66 |
| Average | | −0.66 | unresolved, P 0.73 |
| Maximum | | −0.51 | unresolved, P 0.79 |
| OddsTrader median | | −0.43 [−0.93, +0.08] | unresolved, P 0.95 |
| Bet105 | 3,747 | −0.60 [−1.48, +0.28] | unresolved, P 0.92 |
| BetOnline + Betfair | 3,876 | −0.61 [−1.33, +0.12] | unresolved, P 0.95 |
| BetOnline + Polymarket | 3,850 | **−1.44 [−2.56, −0.33]** | better |
| Betfair + Polymarket | | **−1.70 [−3.07, −0.32]** | better |
| **All three** | 3,659 | **−1.58 [−2.58, −0.59]** | better |
| All three + OddsTrader median | | −1.49 [−2.22, −0.77] | better |
| BetOnline + OddsTrader median | | −0.29 [−0.54, −0.03] | better |
| Walk-forward BetOnline + Polymarket | | −1.32 [−2.14, −0.50] | better |
| Walk-forward all three | | −1.52 [−2.52, −0.52] | better |
| Proxy | 4,086 | −1.19 [−2.72, +0.35] | unresolved, P 0.94 |
| BetOnline rescaled ×1.025 | | −0.21 | unresolved |
| Proxy with Bet105 | | −1.06 [−2.13, −0.00] | better, borderline |

After each price's own calibration slope: Betfair −0.06 and Polymarket −0.52 (both unresolved); BetOnline + Polymarket −1.18 [−2.27, −0.10]; all three −1.21 [−2.12, −0.31]; all three + OddsTrader median −1.26 [−1.94, −0.59].

*D. Full-coverage rules on all 4,340 rows, − today's rule*

| Rule | All rows | After own slope | 2025 (924) | 2026 (3,416) | Men | Women |
|---|---|---|---|---|---|---|
| BetOnline + Betfair | −0.67 [−1.33, −0.01] | −0.38 u | −0.42 u | −0.74 [−1.34, −0.13] | −0.26 u | −1.09 u |
| BetOnline + Polymarket | −1.62 [−2.78, −0.46] | −1.36 [−2.44, −0.28] | −0.11 u | −2.03 [−3.41, −0.65] | −0.44 u | −2.86 [−4.48, −1.23] |
| **sharp3** | **−1.79 [−2.75, −0.82]** | **−1.46 [−2.30, −0.62]** | −0.68 u (P 0.91) | **−2.09 [−3.23, −0.95]** | −0.73 u (P 0.89) | **−2.89 [−4.60, −1.18]** |
| sharp4 (+ OddsTrader median) | −1.65 [−2.37, −0.92] | −1.43 [−2.08, −0.79] | −0.62 [−1.09, −0.15] | −1.93 [−2.76, −1.09] | −0.79 [−1.58, −0.01] | −2.55 [−3.98, −1.11] |
| BetOnline + Bet105 | −0.24 u | −0.13 u | +0.34 u | −0.39 u | −0.37 u | −0.10 u |
| Proxy | −1.12 u (P 0.94) | −1.06 u | −0.09 u | −1.40 u | −0.57 u | −1.71 u |

u = unresolved. Where an interval is shown and clears 0, the rule is better.

*Head to head* (+ = first named worse):
- sharp4 − sharp3: +0.14 [−0.14, +0.42], unresolved.
- BetOnline + Polymarket − sharp3: +0.17, unresolved.
- BetOnline + Betfair − sharp3: +1.12 [+0.27, +1.97], worse.
- Proxy − sharp3: +0.66, unresolved.
- Bet105 rule − sharp3: +1.55 [+0.55, +2.55], worse.

*sharp3 robustness:*
- Weekly clusters: −1.79 [−2.88, −0.70], 46 weeks.
- By four-week block: 12 of 13 negative.

*C. Common sets*
- On 3,134 matches where every widely available source prices: Betfair + Polymarket −1.41, all three −1.32, BetOnline + Polymarket −1.30, all better. Every single price is unresolved.
- On the 642 matches that also have PS: only the three-price and four-price averages resolve (better).

*Multiplicity (Holm at 5%)*
- Survivors: rule sharp4 (p 0.0003), walk-forward four-price, equal four-price, and rule sharp3 (p 0.0016).
- Equal three-price (p 0.005) and BetOnline + Polymarket (p 0.016) do not survive.

*F. Sweep (246 combinations; ranked on even blocks, confirmed on odd blocks)*
- The top discovery combinations involve PS and do not confirm.
- The ones that confirm all contain Polymarket.
- Nothing beats the declared sharp3 rule.

*G. Checks*
- Polymarket at 60 min − at 30 min: +0.33, unresolved.
- BetOnline + Polymarket 60 − BetOnline: −1.24 [−2.27, −0.22], better.
- Walk-forward weights in the last block before the seal: all three 0.29 / 0.28 / 0.43, close to equal. The four-price set is unstable (BetOnline −0.72, OddsTrader median +1.37).

**4.6 Where Pinnacle's close is known**

1 Aug – 7 Sep 2025, match-day clusters, candidate − Pinnacle:
- BetOnline +3.30 [+1.60, +5.00], worse.
- OddsTrader median +2.27 [+0.32, +4.23], worse.
- Unresolved: Betfair +0.28 (313 matches), Bet105 +0.92, BetOnline + Betfair +1.72, proxy +1.94.
- Against BetOnline in the same window: Betfair −3.93 [−6.47, −1.38] and Bet105 −2.30 [−3.93, −0.67], both better.
- This is five weeks dominated by the US Open; read it as a flag.

2024 and 2025 to July, proxy fitted walk-forward: proxy − Pinnacle +0.08 and −0.11; proxy − BetOnline −0.03 and −0.55. All unresolved.

**4.7 Calibration slope in the gap**
- BetOnline 1.076, Betfair 1.026, Polymarket 1.010, all three 1.050, average 1.113.
- Pinnacle in 2024 – Jul 2025: 1.029. All books' slopes rose in 2026, so these are not directly comparable.

### 5. Checks
- **Hand checks, all agreeing:**
  - 10 tennis-data rows: PSW/PSL, BFEW/BFEL, B365, Avg and Max against the staged workbook row (Stage 1 file and position). One incoherent max pair is correctly blank.
  - 5 BetOnline and 5 Bet105 rows against `books_lines.parquet` and the `events.parquet` names.
  - 5 Polymarket rows against the raw minute history at start − 30 min.
  - 5 each for my BetOnline-opening and Polymarket-60 joins.
  - Seed 20261016; the keys are in `hand_checks.json`.
- **Invariants:**
  - `construct` matches the frame on 67,226 of 67,226 rows.
  - The BetOnline-opening join oriented 37,328 of 37,837 rows.
- **Seal:** `results()` returned 66,285 rows; the scorer raises if a sealed row has a result.
- **Hashes:** live Stage 0 matches the manifest, and the inputs' SHA-256 were unchanged across runs (both in `summary.json`).

### 6. Process: what had been seen when each choice was made
1. **21:15:40 UTC:** the design was declared before any result.
2. **First results:** `odds_psx` section 3 (PS accuracy only).
3. **21:23:44 UTC:** Bet105 added, after a distance-to-Pinnacle table that reads no result. No Bet105 result had been seen.
4. **Then** `odds_proxy` (no result), then `odds_score`: all gap results seen.
5. **Changes made after seeing results:**
   - P(better) switched to the t distribution. No estimate or interval changed.
   - The Polymarket-60 join key fixed; the first version returned no rows.
   - Added as checks: the recalibrated readings, H, Holm, weekly clusters, head-to-head, and sharp3 with Polymarket at 60 min.
   - None of these changed the declared primary or the ranking of the rules.

### 7. Could not do, and caveats
- **No model-level test.** That needs a candidate build and GPU fits, which is your call. A 2026 model reading must stop at the seal.
- **Faithfulness to Pinnacle is unknown for Polymarket**, and the check for the others rests on one five-week window.
- **Sharper is not the same as more Pinnacle-like.** Where it could be checked, every candidate was worse than Pinnacle's close, so there is no sign that sharp3 overshoots Pinnacle. That is unresolved.
- **The 2026 part overlaps odds_sources' 2026 reading**, which also read sealed rows, so it is not independent confirmation of it.
- **Timing:** Betfair's and Pinnacle's tennis-data closes are untimed. BetOnline's last line is stamped a median 6–44 minutes before the listed start, month by month in the gap.
- **No sign of in-play prices:** Betfair carries no extra information after calibration, and Polymarket at 60 minutes keeps most of the gain.

### 8. Surprises
- Before August 2025 the books' maximum was nearly Pinnacle, and that broke silently with the panel change.
- Betfair is far from Pinnacle in KL but as accurate as Pinnacle against results. Inference: its close is timed differently (at the off).
- Bet105 looks like a Pinnacle line-follower (inference). It has been listed on OddsTrader only since April 2025.
- Polymarket was weak in its first months: in October 2025 it had made only 0.40 of BetOnline's late move.
- BetOnline was 3.3 mLL behind Pinnacle in Aug – early Sep 2025, against 0.6 long-run.

### 9. Reproduce
```
./python.sh src/eda/source_reconciliation/odds_coverage.py
./python.sh src/eda/source_reconciliation/odds_psx.py
./python.sh src/eda/source_reconciliation/odds_proxy.py
./python.sh src/eda/source_reconciliation/odds_score.py
./python.sh src/eda/source_reconciliation/odds_checks.py
./python.sh src/eda/source_reconciliation/odds_summary.py
```
On Windows, set `PYTHONIOENCODING=utf-8` before the scripts that print tables.
