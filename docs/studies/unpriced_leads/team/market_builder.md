# Market and incentives builder (S2c): totals, line momentum, the record against the close, ranking cliffs, points to defend

13 Oct 2026 · Unpriced-leads team, round 2 · Role S2c ([brief](../briefs/07_market_builder.md), binding) · Claude Opus 5.5, a subagent of session `e1ffc84e-fa2d-42f9-9d17-7c936a046c45` · Discovery evidence for the lead's synthesis, not a decision.

* **Code:** `src/eda/unpriced_leads/build_market.py`, one deterministic command (about 15 minutes, CPU). Every construction choice is in its docstring.
* **Outputs** (`data/studies/unpriced_leads/candidates/market/`): `values.parquet` (every frame match 2013–2026, no result column; MP-01/02 are match-level, one column each), `splits.parquet` (splits and the books' own log-odds; gitignored), `long.csv`, `summary.csv`, `probes.json`, `coverage.json`, `extras.json`, and the post-hoc `diagnostics_*.csv`.
* **Outcomes read:** seasons ≤ 2024 only, through the harness and (MP-10) the long table's `won` for frame matches before 2025. No 2025–26 result or market-response reading.
* **Labels:** [Obs] = computed here; [Inf] = inference.
* **How to read z.** Difference statistic: + = the player higher on it beats the close. Context statistic: + = the price should be steeper where it is high. Null SD ≈ 1.08 over 62 screens, so a single |z| < 3 is weak.

## In short

1. **Nothing reaches |z| = 3 beyond the close** [Obs]: 13 statistics, raw and orthogonal, beyond the odds input and beyond each book's own close.
2. **The best weak reading is MP-01c, the totals' move net of the moneyline's** (+ = favourites under-priced when the totals moved toward a lopsided match).
   * z +2.3 beyond the odds input and +2.7 beyond BetOnline's close, positive in all 3 eras; orthogonal +1.8 / +2.0; R² ≤ 0.04.
   * But −0.4 beyond the model's forecast. Net of the favourite–longshot curvature (post hoc, § 4.2) it keeps +2.1 / +2.3.
3. **The clearest finding is outcome-free: the moneyline learns the totals' opening view.** When BetOnline's opening total implies a more lopsided match than its opening moneyline, the favourite firms by the close (move lens z +10.4). Beyond the close that excess reads −0.9.
4. **Line momentum: no continuation at either book** (BetOnline −1.0, Pinnacle −0.8, each beyond its own close). Fresh closes show weak reversal (−1.9), stale ones weak continuation (+1.6).
5. **MP-10 is noise.** Split-half r = −0.04 [−0.14, +0.05], so the pre-stated gate failed (no role members). It reads −1.4 beyond the close, yet BetOnline's line moves toward good records (move lens +8.8).
6. **MP-08 and MP-09: nothing.** |z| ≤ 1.2 pooled and ≤ 1.6 in any tour, beyond the close or the model.
7. **Two data faults** (§ 1.1). 93 impossible total-games lines had inflated the practitioner's residual SD (best of 3 at the close leaves about 0.5 games, not 0.94). OddsTrader's Pinnacle copy has recording failures.

## 1. What was built

### 1.1 Prices and data faults

**Sources.**
* BetOnline's opening and last lines (moneyline and totals): OddsTrader's matches table, linked by the instance's `odds_sources` eid (its `a_won` never loaded).
* Oriented to A by matching prices with `ot8_a/ot8_b`; validity as bet_timing (overround 1.00–1.20, unflagged, the opening before the listed start).
* [Obs] My chances equal bet_timing's exactly on 35,258 openings and 34,831 last lines. About 1,900 more rows are covered (half of 2018's ids changed in the 7 Oct rebuild).

**Data-quality rules,** fixed after an outcome-free look at the values, before any screen:
* **Total lines** [Obs]: 10 opening and 83 last lines before 29 Jul 2026 are impossible (0.5, 106.5, 190.5, 211.5; best-of-3-sized lines on best-of-5 matches). Lines outside 12.5–30.5 (best of 3) and 23.5–50.5 (best of 5) are dropped.
* **MP-01's standardised statistics** are clipped at ±4 SD (0.3–0.6% of rows).
* **Pinnacle** (OddsTrader id 20, to 7 Sep 2025):
  * the last line must be stamped ≤ 30 min after the listed start and, to 31 Jul 2025, lie within 0.5 log-odds of tennis-data's Pinnacle close (258 dropped, mostly the 2021 US Open);
  * 2 mirror-image (swapped) openings give no move; moves are clipped at ±1.5 log-odds (8 at BetOnline, 13 at Pinnacle).

### 1.2 MP-01, the totals market against the moneyline (match level, two-sided)

**The expectation.**
* E[total line | moneyline]: least squares on 2019–2024 frame matches (no outcome), by group (men best of 3, men best of 5, women). Frozen and applied to every season.
* Regressors: |L| and L² (L = BetOnline's own margin-free moneyline at the same moment, opening with opening, last with last); surface, indoor and level dummies; the pair's serve levels (the store's leak-proof level sums U-222, U-229, U-217). Rows without the sums use the fit without them (37 rows before 29 Jul 2026, all in 2026).
* [Obs] At the close: R² 0.82 / 0.92 / 0.83 and residual SD 0.51 / 1.11 / 0.48 games (men bo3 / men bo5 / women). The sums add 0.17 of R² for men's best of 3. Opening and closing excess correlate 0.41.
* `excess` = (line − E) / the group's residual SD.

**The members:**
* **a.** `mp01_lop_close` (context) = −excess at the last lines. + = the totals expect a more lopsided match than the moneyline does.
* **b.** `mp01_lop_open` (context): the same at the opening lines.
* **c.** `mp01_lop_move` (context) = minus the standardised residual of the totals' open-to-last move on the moneyline's move (Δ|L|, ΔL²; fitted on 2019–24 by group).
* **d.** `mp01_diff_close` (difference) = sign(L_A)·(u* − |L_A|). u* inverts the close fit (the total-implied |L| on the curve's decreasing branch, clamped to [0, the 99.5th percentile]); at 0 for 11% of rows, at the cap for 0.4%.

### 1.3 MP-02, line momentum (match level, two-sided)

* **The statistics:**
  * `mp02_bol` = logit(BetOnline's last line) − logit(its opening), oriented to A;
  * `mp02_pin` = the same for Pinnacle at OddsTrader.
* **Tested** beyond the book's own last line (`L_bol`; `L_pin_ot`) and beyond the odds input.
* **Tiers:** tour; Slam/1000/Finals against 500/250; round ("first" when neither player has an earlier match at this event, qualifying included, else "later"); price (the favourite's chance by the book's last line < 0.60, 0.60–0.75, ≥ 0.75); for BetOnline, a fresh last line (stamped within 60 minutes before the listed start, or after it) against a stale one.

### 1.4 MP-10, each player's record against the close (A − B)

* **Pool:** r = won − p over frame matches with tournament_date < 1 Jan 2025 (p = the frame's `p_mkt` for that player). It holds no 2025+ match, so every 2025–26 value is frozen at 31 Dec 2024. [Obs] It equals `load_frame`'s y − p on all 57,867 rows.
* **Statistic** for match M: Σr / (n + 30) over the player's last ≤ 60 pool matches with lf + 1 ≤ es(M).
* **Gate,** stated in the code before it ran: odd- against even-match mean residuals of players with ≥ 40 pool matches, Pearson r across players; role members only if its 95% bootstrap interval is above 0. It was not (§ 4).

### 1.5 MP-08, ranking cliffs (A − B; my approximations)

* **Dates:** Slam Monday T from Stage 0; seeding ranking date T − 7 days, direct-entry date T − 42. A match is in a window when its best-estimate day (the clock's `obs`) falls in the 28 days before.
* **Lines:** 32 seeds (band 28–40), 104 direct entries (band 90–120), both tours, every year.
* **"Could carry him across":** outside the line and P + W ≥ P*.
  * P = his ranking points; W = this match's win points from one standard table per tour (`POINTS` in the code and `extras.json`).
  * P* = the line rank's points in the same week's ranking list (Stage 0's rank and rank_points of every player row that week): published, but cross-player.
* **The members:**
  * `mp08_seed` / `mp08_entry` = +1 if he could cross, −1 otherwise, 0 outside the window or band;
  * `mp08_seed_band` / `mp08_entry_band` (secondary) = the unsigned 1[in window and band].
* [Obs] Only 14–18% of in-band player rows are "live" (+1).

### 1.6 MP-09, points to defend (A − B)

* **Previous edition:** same tour, same normalised name (else the id after its year prefix; ids change across sources), 300–420 days earlier, nearest 364.
* **Points:** the round reached in his last main-draw row there, from the same table (qualifying ignored; Finals: the sum of his wins).
* **Members:** `mp09_defend` = points / his current ranking points, capped at 1; `mp09_champ` = 1[won it]; 0 if he did not play it.

## 2. Timing probes [Obs]

* **`H.timing_probe`** (cuts 1 Jun 2016, 1 Mar 2019, 1 Sep 2022): **0 changed rows** for MP-10, MP-08 and MP-09, future and own rows alike.
  * Compared: 626k / 916k / 1.25M long-table rows, own rows 21.7k / 17.7k / 12.8k (only frame rows carry values).
  * The long table passed holds every column the builders read; `won` is its only result column.
* **MP-01 and MP-02** read only the match's own lines, so no probe applies (MP-01's expectation is a no-outcome fit across 2019–24 lines, as the brief specifies).
* **MP-08 reads no result** (its probe is a formality). P* uses the same week's published list, which predates the week's matches.

## 3. Coverage [Obs]

Share of frame matches present, 2013–24 / 2025–26 (to 28 Jul 2026), outcome-free:

| Statistic | Men | Women | Where it is |
|---|---|---|---|
| MP-01 members | 0.39 / 0.88 | 0.37 / 0.85 | From 2019: 2019 40%, 2020–23 85–98%, 2024 80%, 2025 79–85%, 2026 93–94% |
| mp02_bol | 0.50 / 0.97 | 0.48 / 0.93 | From 2018 (71–72%) |
| mp02_pin | 0.51 / 0.48 | 0.48 / 0.46 | 2018 – 7 Sep 2025; none in 2026 |
| mp10_rec | 1.00 / 1.00 | 1.00 / 1.00 | Nonzero ≥ 99.5% |
| mp08 seed / entry (nonzero) | 6.8% / 5.8%; 4.8% / 6.3% | 7.0% / 6.5%; 5.3% / 5.8% | |
| mp09_defend (nonzero) | 58% / 67% | 62% / 69% | Previous edition found: men 88% / 98%, women 83% / 94% (2021: 33% / 27%, the COVID gap) |

## 4. Readings (seasons ≤ 2024)

### 4.1 Both tours

* Each cell: pooled z, raw / orthogonal.
* "Eras" counts eras with the pool's sign, raw. MP-01 has 3 eras with data (2019 to 2024), MP-02 has 3 (2018 to 2024), the rest have 4.
* Model lens: beyond the model's own forecast, 2020–24. Move lens: BetOnline's open-to-close move, 2018–24 (outcome-free).
* R²: the harness's, with the 49 inputs. For context statistics, mine in brackets: symmetric functions of the inputs.

| Statistic | Beyond odds input | Eras | Beyond own book's close | Model lens | Move lens | R² |
|---|---|---|---|---|---|---|
| a lop_close | +0.98 / −0.03 | 2 of 3 | +1.72 / +0.73 | +1.48 | −9.7, circular | 0.01 [0.05] |
| b lop_open | −0.90 / −1.50 | 1 of 3 | −0.47 / −1.15 | −0.18 | **+10.4** | 0.01 [0.04] |
| c lop_move | **+2.29 / +1.80** | 3 of 3 | **+2.70 / +2.04** | −0.41 | circular | 0.01 [0.04] |
| d diff_close | −0.22 / −0.09 | 2 of 3 | +0.05 / +0.17 | −0.30 | −10.4, partly circular | 0.01 |
| mp02_bol | −0.20 / −0.91 | 1 of 3 | −1.01 / −1.84 | −0.26 | — | 0.05 |
| mp02_pin | −0.26 / −1.22 | 2 of 3 | −0.81 / −1.83 | −1.79 | — | 0.11 |
| mp10_rec | −1.43 / −1.55 | 3 of 4 | — | −1.29 | **+8.8** | 0.24 |
| mp08_seed | +0.62 / +0.47 | 3 of 4 | — | +0.46 | −0.9 | 0.01 |
| mp08_entry | −1.18 / −1.04 | 3 of 4 | — | −1.55 | +0.1 | 0.01 |
| mp08_seed_band | −0.76 / −0.54 | 3 of 4 | — | −0.02 | +1.1 | 0.01 |
| mp08_entry_band | +1.15 / +0.90 | 4 of 4 | — | +0.76 | −0.3 | 0.02 |
| mp09_defend | +0.33 / +0.54 | 1 of 4 | — | −0.55 | +2.4 | 0.06 |
| mp09_champ | +0.71 / +0.75 | 2 of 4 | — | +0.12 | +1.4 | 0.07 |

**By tour** (beyond the own book's close, raw): lop_close men +2.59 (3 of 3 eras; orthogonal +1.42), women +0.13; lop_move men +1.80, women +2.04; mp02_bol men −1.57, women +0.02; all others |z| < 2 in each tour.

**MP-02 tiers** (beyond the book's own close, both tours):
* BetOnline:
  * level: 500/250 −1.40 (men −1.89), Slam/1000 −0.08;
  * round: first −0.77, later −0.52;
  * price: mid −1.78, favourite ≥ 0.75 +1.56 (women +1.93);
  * freshness: fresh −1.92 (3 of 3 eras), stale +1.60.
* Pinnacle: every tier |z| ≤ 1.3.
* Stale minus fresh, from the tier coefficients: about +0.07 per RMS unit, ≈ 2.4 SE (approximate: disjoint rows, overlapping blocks).

**Correlations** (≤ 2024; absolute values for context statistics) with the odds input: MP-01 ≤ 0.06 except lop_move 0.16; mp02_bol 0.20, mp02_pin 0.33; mp10 0.15; mp09_champ 0.23, mp09_defend 0.15; MP-08 ≤ 0.10. With `sets_14d`: all ≤ 0.07.

**MP-10's reliability** [Obs]:
* split-half r −0.04 [−0.14, +0.05] (567 players, mean 189 matches); men −0.09, women +0.01;
* player-seasons (≥ 20 matches): −0.035 [−0.081, +0.008].

### 4.2 Post-hoc check: is MP-01c the favourite–longshot curvature?

Added after § 4.1 was seen; reported as it came out (`diagnostics_summary.csv`). The close lens has a free slope per tour but no curvature term, so a context statistic correlated with |L| (MP-01c: r 0.16) can borrow the favourite–longshot curvature.

* **The curvature alone** (s = |L|) [Obs]: z +4.6 beyond the odds input (all 4 eras positive) and +5.1 beyond BetOnline's close. + = the close should be steeper in lopsided matches, so favourites are under-priced at the extremes; women +4.6, men +2.3.
* **MP-01's context statistics residualised on 1, |L|, L²** (by tour):
  * c: +2.29 → +2.08 beyond the odds input, +2.70 → +2.28 beyond BetOnline's close, positive in every era;
  * a: +0.98 → +0.90, men beyond BetOnline +2.59 → +2.58;
  * b: −0.90 → −1.00.
* [Inf] The curvature explains a sliver of c, not most of it. For the registration, I recommend testing every context statistic with a curvature term in the base, or residualised as here.

## 5. What looks promising, what does not

**The totals market (MP-01).**
* [Inf] The opening totals carry a lopsidedness view that the moneyline then adopts (move lens +10.4); by the close it is priced (b: −0.9).
* What is left at the close is weak: the totals' late move (c: +2.3 / +2.7; +2.1 / +2.3 net of curvature; every era positive) and men's close excess beyond BetOnline's close (a: +2.6; orthogonal +1.4). Neither shows beyond the model's forecast (−0.4, +1.5). d is dead.
* **My recommendation:** if the lead wants a market group, register c (with a for men) as one "totals' late view" score.
  * Two-sided, with a curvature term in the base, beyond BetOnline's close and beyond the odds input; report the BetOnline period separately (2025–26 coverage 0.85–0.88).
  * Expect it to read unresolved on Look A (β ≈ 0.03–0.045 per RMS unit against SE ≈ 0.03–0.036): a bundle member, not a lead alone.

**Line momentum (MP-02).**
* No continuation at either book, overall or in any tier; the practitioner's kill condition (§ 3.3) nearly holds.
* The one pattern, fresh-close reversal against stale-close continuation (≈ 2.4 SE apart), fits "a stale close has not finished its move". It is a design note (split fresh from stale closes), not a lead.

**The record against the close (MP-10).**
* Dead as a player trait: no reliability, and a slightly negative coefficient.
* [Inf] Its move lens (+8.8) shows the line chasing over-performance that does not persist: the luck group's "luck read as skill", seen in prices. A sentence for that group, not a group.

**Incentives (MP-08, MP-09).**
* Nothing, beyond the close or the model. Cliffs touch only 5–7% of matches, with approximate dates and tables. I would not register them.

## 6. Caveats

* **Approximations:**
  * MP-08's dates, lines, table and same-week P* (drops ignored);
  * the 2020 ranking freeze and Wimbledon's pre-2021 men's seeding formula are not modelled;
  * MP-09 sets COVID gaps to 0, though the ATP's 2021 rules kept 2019 points live.
* **MP-01's expectation is fitted in-sample** on 2019–24 lines (no outcomes; the brief's design), frozen for 2025–26.
* **The harness's R² for context statistics is near 0 by construction** (an antisymmetric L·s against symmetric regressors). The bracketed R² is the informative one.
* **OddsTrader:** its "opening" is its first sighting; BetOnline's last line is stale (> 60 min before the listed start) in 33–41% of priced matches a season (2020–25); its Pinnacle copy ends 7 Sep 2025.
* **MP-10's frozen values age** (up to 18 months by mid-2026).
* **Near-copies:** the signed and band MP-08 members (r −0.69 / −0.61); MP-01 a, b and c (|r| 0.42–0.56); the BetOnline and Pinnacle moves (0.74). None copies a pool column (B-MOTIV, I-085: |r| ≤ 0.12); U-010 (line movement) and U-174 (points to defend) had never been built.
* **Disclosure** [Obs]: my first build-only run printed orientation counts over all frame rows, the sealed set included. No sealed statistic or result was looked at; counts were then restricted to before 29 Jul 2026.

## 7. Reproduce

`./python.sh src/eda/unpriced_leads/build_market.py`. A second full run reproduced `values.parquet` (67,226 × 28) and `summary.csv` (162 rows) exactly: maximum difference 0.
