# Rhythm and body: what was built and how it screens on 2013–24 (S2a, round 2)

13 Oct 2026 · Role S2a, the rhythm-and-body builder ([brief](../briefs/08_rhythm_builder.md)) · Claude Opus 5.5, a subagent of the lead's session `e1ffc84e-fa2d-42f9-9d17-7c936a046c45` · Code: `src/eda/unpriced_leads/build_rhythm.py` (one command, deterministic; 7 minutes on an idle machine, 40 under load) · Outputs: `data/studies/unpriced_leads/candidates/rhythm/`

* **Outcomes read:** only through the harness, matches before 1 Jan 2025. Nothing on results, line moves or sealed-set counts from 2025 on; for 2025–26 only presence shares.
* **Reading the numbers:** labels are *observed*, *inference* and *suggestion*. z is the harness's cluster-robust z (null SD about 1.08); + means the player higher on the statistic beats the close. About 37 statistics × raw/orthogonal × 3 tour sets were screened, so a single |z| < 3 is weak.

## Summary

1. **Clock times, settled (observed).**
   * The clock is day-level.
   * Flashscore's start is the actual first point (minus the Slam feeds' start: median −0.05 min).
   * OddsTrader's and SofaScore's times are schedules, 10 min earlier at the median.
   * TennisLive's time is a placeholder, but its date is the local match day.
   * Both scouts were right, about different files.
2. **Strongest new reading: RB14, the bye seed's cold start.**
   * Bye draws of 28, 48, 56 and 96 players: z +3.54 raw, +3.00 orthogonal; 4 of 4 eras; BH q 0.02.
   * It is a slice of the pool's U-138: with bye matches zeroed, U-138's orthogonal z falls from +2.45 to +0.88.
   * A placebo (seeds' first match without a bye) leans the same way at about half the strength (+1.66).
   * Weaknesses: it is concentrated in 2017–19, and BetOnline's line moves toward it (move z +6.8).
3. **New information: RB01, doubles played at other events in the previous 7 days.**
   * z +2.89 raw, +2.83 orthogonal; 3 of 3 eras; positive on both tours.
   * Men's 2013–16 replicate it on Sackmann's files (z +2.24).
   * Beyond the model, z +1.9; the line does not move toward it; R² 0.02.
   * It is strongest where BetOnline's last line came within 60 min of the start.
   * Doubles at this event read +0.20.
4. **Rest in hours: only the tail.**
   * Rest under 20 h: z −2.13 raw, −2.37 orthogonal; 4 of 4 eras; but about 5% of matches.
   * The continuous shortness reads −0.18; the within-round gap +1.50 (men only).
5. **The rest is null, priced, or split by tour.**
   * Null: RB05, RB06, RB02, RB20, RB23, MP-22.
   * Spanned by the inputs: the qualifier cost, which is its tag (r 0.998; orthogonal z −0.34).
   * Split by tour: RB10 and RB15 flip sign between men and women.
   * Every probe reads 0. The stale-line trap does not apply to rest (0.36% of lines predate the information).

## 1. Which clock times are real (observed, `time_sources.json`)

| Source | Is | Evidence |
|---|---|---|
| Match clock | day-level | 0% of `start` values have a fraction |
| Flashscore start | the actual first point | minus the Slam feeds: median −0.05 min (IQR −1.6 to +1.5); minus the WTA API: +0.4 |
| api-tennis, Live Tennis API | copies of Flashscore | 0.0 at every quantile |
| OddsTrader listed, SofaScore | schedules | Flashscore later by a median 10 min (P5–P95: 5–20); 98% within 60 min |
| TennisLive | a placeholder time, a real date | 09:00 on 99.8% of tour singles; date = the clock's day for 99.5% |
| Flashscore end | real | end − start within 10 min of Stage 0's minutes for 92–98% each season (≤ 2024) |

By tour and season:
* **Men:** actual starts 98–100% every season. Flashscore ends 90–98% to 2024, then 15% (2025) and 14% (2026), so start + minutes is used there. Minutes are missing for 48% of 2015.
* **Women:** actual starts 68–71% in 2013–18 (SofaScore's schedules add 25% in 2018), then 83% (2019) rising to 100% (2023 on). 2013–15 have no minutes, so an end exists only with a Flashscore record (69–71%).

## 2. Construction and choices (definitions in the code's docstring)

* **RB01, doubles (TennisLive 2018–26).**
  * The data: played rows (walkovers out), deduplicated: 135,719 matches. Names map to Stage 0 ids through the lower-level crosswalk (95.6% of member-rows); events through their singles rows (94.3%).
  * The window: days d−7..d−1 by `obs` (same-day doubles out).
  * Validation: TennisLive recovers 98% of Sackmann's men's participations at the same event (2018–20).
  * The ITF shift is immaterial: 0.35% of 2020–24 frame player-rows have ITF doubles in the window, under a 1% rule fixed beforehand. So the primary counts every level (the variants correlate 0.97–0.99 with it).
  * The real shift is behaviour: men's matches with differing counts fell from 42% (2018) to 25% (2025–26); women's held at 36–42%.
  * Men 2013–17 (flagged), from Sackmann's event-level files: `rb01s_entered` (in this event's doubles draw) and `rb01s_prev` (doubles at events ending in d−8..d−1).
* **RB03, RB04, RB05: rest in hours.** rest_h = this match's actual start minus the previous played match's end (any level).
  * The end is Flashscore's (implied duration 15–420 min), else start + minutes, the same rule every season. Minutes-first gives r 0.995.
  * Without hours, a clock day gap of at least 2 days gives s = 0.
  * RB04 is match-level, and 0 when either rest is at least 72 h.
* **RB06** is time-zone free: the previous match was on day d−1 and was the last to end at its event-day, and this match started within 150 min of that day's first start (a proxy for first or second on court). For safety, every end that day must precede this match's start. It is non-zero in about 3.5% of matches.
* **RB13: qualifier and lucky-loser cost.**
  * Points come from box scores, else games × points per game (2010–12: 6.34, 6.25 for best of 5, 6.59 women). 2015's qualifying box scores are only 24% complete.
  * The cost is about 5.7 times the tag, so two variants were added before any screen: `rb13_qtag` and `rb13_qcost_dev` (cost beyond its 2010–12 mean for the run's length).
* **RB10: style-specific ageing.**
  * From `surface_features.parquet`, the store's source, identical on shared rows (99.8% coverage; the store has 48% of 2018).
  * A statistic is O(server) − D(returner), so a higher D is a better returner (double faults reversed).
  * Values are z-scored by tour on 2013–24; RS = D̄/(|Ō| + |D̄| + 0.25).
* **RB15:** the 42-day condition is vacuous inside 28 days, hence `rb15_r90` (90 days, no 42-day break since). MP-22 lacks withdrawals (not held).
* **RB14:** the draw is read from its structure, entrants = bracket/2 + first-round matches (see the data faults in § 7). The value is −1 for a bye seed whose opponent has played here, so A − B is signed toward the opponent. A placebo was defined after run 2 and before it was read: `rb14_seed_r1_nobye`, a seed's first match in a draw without byes.
* **The pool:** my U-138 equals the store's on every shared row; my days since the last match match U-132 at r 0.9999.

## 3. Timing probes (observed, `probes.json`)

| Builder | Result columns scrambled | Future rows changed | Own rows changed |
|---|---|---|---|
| rest (RB03–05, U-132), RB06, RB20 | 3 | 0 | 0 |
| RB13 | 5 | 0 | 0 |
| RB15 | 2 | 0 | 0 |
| on-site (U-138, RB14), RB02 | 1 | 0 | 0 |
| RB23, RB10 | 0 (only clock days and age) | 0 | 0 |

The counts are at each cut (2016, 2019, 2022), with 0.6–1.2 million future rows and 13–22 thousand own rows compared.

* **Doubles have their own checks.** Dropping every doubles row after each cut moves 0 earlier values. A doubles match added on each player's last match day moves 0 of 1,881 values; added a day earlier, it moves 1,421, so the check bites.
* **RB10 and RB23 rest on construction:** strictly earlier rows, and the leak-proof IOS file.
* **One fault the probe found (numerical):** RB20 first showed 17–19 own-row changes. The exclusive sum `cumsum − current` kept the current row in its last floating-point bits. Fixed; 0 now.

## 4. Coverage (observed, `coverage.json`, to 28 Jul 2026)

Every statistic is present for 97.5–100% of 2025–26 matches, except the Sackmann version (2013–17 by design). For 2013–24, RB01 covers 2018–24, women's hour-based statistics 77–85% (55–70% in 2013–17), and the others 99–100%.

| A − B non-zero | Men 2013–24 | Men 2025–26 | Women 2013–24 | Women 2025–26 |
|---|---|---|---|---|
| rb01_d7 (2018–24) | 37% | 25% | 39% | 36% |
| rb01_d7_else (2018–24) | 15.7% | 8.8% | 18.5% | 15.3% |
| rb03_lt20 | 5.4% | 4.0% | 4.8% | 5.2% |
| rb04_gap | 43% | 41% | 32% | 41% |
| rb14_cold28 | 12.6% | 13.6% | 7.0% | 13.0% |
| rb13_qtag | 13.3% | 14.8% | 13.6% | 15.2% |

## 5. Readings (observed, `summary.csv`, `long.csv`)

Columns, both tours unless stated:
* **z raw / orth:** pooled 2013–24 close lens, on the raw A − B and on its orthogonal part.
* **Eras:** eras sharing the pooled sign.
* **Model:** beyond the model's forecast, 2020–24.
* **Move:** BetOnline's open-to-close move, 2018–24.
* **R²:** on the 49 inputs.

| Statistic | z raw | z orth | men | women | eras | model | move | R² |
|---|---|---|---|---|---|---|---|---|
| rb01_d7 | +2.02 | +2.25 | +2.24 | +1.30 | 3/3 | +1.82 | +0.0 | 0.02 |
| rb01_d7_here | +0.20 | +0.61 | +0.26 | +0.01 | 1/3 | +0.72 | +0.8 | 0.02 |
| **rb01_d7_else** | **+2.89** | **+2.83** | +2.93 | +1.74 | 3/3 | +1.88 | −0.6 | 0.02 |
| rb01_d1 | −0.89 | −0.40 | −0.55 | −0.92 | 2/3 | +0.06 | +0.8 | 0.01 |
| rb01_d7_tour / _nonitf | +2.02 / +2.09 | +2.34 / +2.34 | | | 3/3 | | | 0.02 |
| rb01s_entered (men 13–17) | +1.26 | +2.10 | | | 2/2 | | | 0.08 |
| rb01s_prev (men 13–17) | +1.78 | +1.41 | | | 1/2 | | | 0.06 |
| rb03_short | −0.18 | −0.64 | −0.99 | +0.60 | 3/4 | +0.14 | −1.2 | 0.03 |
| **rb03_lt20** | **−2.13** | **−2.37** | −1.30 | −1.55 | 4/4 | −1.32 | −1.1 | 0.01 |
| rb04_gap | +1.50 | +1.57 | +1.93 | −0.39 | 3/4 | −0.56 | +1.7 | 0.01 |
| rb05_ratio | +0.27 | +0.29 | −0.27 | +0.69 | 2/4 | +0.31 | −10.2 | 0.02 |
| rb06_late | −0.53 | −0.60 | −0.96 | +0.41 | 2/4 | +0.67 | +2.0 | 0.00 |
| rb13_qcost | +1.47 | −0.27 | +0.16 | +1.94 | 3/4 | +1.15 | +5.9 | 0.26 |
| rb13_qtag | +1.47 | −0.34 | +0.15 | +1.99 | 3/4 | +0.96 | +6.3 | 0.27 |
| rb13_qcost_dev | +0.68 | +0.60 | +0.58 | +0.65 | 3/4 | +0.80 | −4.4 | 0.02 |
| rb13_qrest | +0.89 | −0.42 | −0.35 | +1.60 | 2/4 | +1.40 | +3.7 | 0.18 |
| rb13_ll / ll_on | +0.11 / +0.82 | −0.73 / −0.06 | −1.33 / +0.96 | +1.27 / +0.19 | | | | 0.03 / 0.04 |
| rb10_drift | +0.34 | −0.27 | −0.94 | +1.69 | 3/4 | +1.23 | +2.4 | 0.19 |
| rb15_r28 | +0.34 | +0.52 | +2.37 | −1.79 | 3/4 | −0.47 | −3.8 | 0.01 |
| rb15_r90 | −1.22 | −1.25 | +0.62 | −2.29 | 4/4 | −1.65 | −3.2 | 0.01 |
| mp22_slam_r1 | −0.47 | −0.35 | +0.07 | −0.90 | 2/4 | −0.01 | −1.9 | 0.00 |
| rb14_cold (48/56/96) | +2.20 | +1.53 | +1.54 | +1.56 | 4/4 | +1.00 | +4.8 | 0.17 |
| **rb14_cold28** | **+3.54** | **+3.00** | +2.98 | +1.65 | 4/4 | +0.84 | +6.8 | 0.27 |
| rb14 placebo: seed's first match, no bye | +1.66 | +1.42 | +1.40 | +1.15 | 3/4 | +0.23 | −2.7 | 0.15 |
| rb02_dblrust | −0.25 | +0.97 | −0.98 | +0.04 | 1/3 | +0.03 | −2.1 | 0.11 |
| rb20_excess | +0.66 | +0.58 | +0.23 | +0.80 | 3/4 | −0.67 | −15.5 | 0.15 |
| rb23_offseason | +0.57 | +0.91 | −0.91 | −0.16 | 2/4 | −0.99 | −1.1 | 0.01 |
| *pool* u138 (store / mine) | +4.28 / +4.41 | +2.27 / +2.45 | +3.09 | +3.42 | 4/4 | +2.03 | +7.0 | 0.49 |
| u138 without bye matches | +2.78 | +0.88 | +0.98 | +3.12 | 4/4 | +1.75 | +5.3 | 0.30 |
| *pool* u132 (days / log days) | −0.93 / −3.91 | +1.31 / −0.48 | | | | | | 0.17 / 0.79 |

**Eras** (2013–16, 2017–19, 2020–22, 2023–24):
* rb14_cold28: +1.06, +4.29, +1.56, +0.25.
* rb01_d7_else: +2.02, +2.33, +0.57 (no data in 2013–16).
* rb03_lt20: −1.93, −1.02, −0.21, −1.37.
* Men's rb10_drift, orthogonal: −3.05, −1.88, +1.59, +0.02.

## 6. The stale-line trap (observed, `stale_line.csv`)

* **What predates what.** BetOnline's last line predates a player's previous-match end in 0.36% of the 26,366 determinable matches of 2018–24 (0.28–0.56% a season). *Inference:* a later round's line cannot be posted before the matchup exists.
* **The fresh subset changes nothing.** Restricted to lines that postdate the information, rest under 20 h reads −1.02 at the odds input and −1.03 at BetOnline's own close (26,271 matches); the gap reads +0.31.
* **The practitioners' broader split.** BetOnline's last line came more than 60 min before the listed start in 34.5% of 2018–24 matches.
  * Odds input / BetOnline's close, last line within 60 min (17,437 matches) against earlier (9,204):

    | Statistic | Within 60 min | Earlier |
    |---|---|---|
    | rb01_d7_else | +2.58 / +2.60 | +0.54 / +0.54 |
    | rb01_d7 | +1.34 / +1.36 | +1.83 / +1.81 |
    | rb03_lt20 | −0.60 / −0.59 | −0.98 / −1.01 |
    | rb13_qrest | +0.64 / +0.72 | +1.35 / +1.36 |

  * The doubles signal sits in the fresh lines, the opposite of a stale-line artefact. The rest readings lean the other way, too weakly to say.

## 7. Correlations, near-copies and data faults (observed)

* **New information:** RB01 correlates with `sets_14d`, U-138 and U-132 at 0.03, −0.10 and 0.00 (its "else" part 0.09, −0.06, −0.07); rb03_lt20 at 0.04, 0.05, −0.09.
* **Near-copies:**
  * rb13_qcost is the qualifier tag (r 0.998); both correlate 0.74 with U-138.
  * rb14_cold28 correlates 0.45 with U-138 and −0.49 with U-132.
  * The doubles parts are orthogonal (here against else, 0.03); day d−1 is mostly "here" (0.71).
  * RB10's two forms correlate 0.93.
* **U-138 mixes three populations:**
  1. qualifiers (r 0.84 with the tag once byes are removed);
  2. opponents of cold bye seeds;
  3. later rounds, nearly symmetric.

  On 2013–24 only the second keeps an orthogonal signal (+3.00, against +0.88 for the rest and −0.34 for the tag).
* **Data faults:**
  * Stage 0's `draw_size` is the entrant count in 2012–15 and 2025–26 but the bracket size in 2016–24 (Indian Wells: 128).
  * In 2016–19 only, the men's and women's events of a combined tournament share one tournament id. Fixed by grouping events by tour.
  * The store lacks about half of 2018.
  * Women's 2013–15 have no minutes.

## 8. What looks promising (suggestion), and what does not

1. **On-site rhythm: RB14 with U-138.** It is the strongest and most coherent reading, with weaknesses:
   * most of it is 2017–19;
   * the line moves toward it (perhaps learned by 2023–24, +0.25);
   * it is a slice of U-138. U-138 has not been read on 2025–26, and coverage holds there (13–14%);
   * the no-bye placebo reads +1.66.

   *Inference:* part of the effect may be seeds under-performing in any first match, and the bye adds to it. The line moves against bye seeds (+6.8) but toward non-bye seeds (−2.7).

   I would register it as a member beside U-138, or split U-138 into its bye part and the rest, not as a group of its own.
2. **RB01's "else" part: doubles elsewhere in the last week.**
   * The mechanism: doubles live in another feed, and no singles rating reads them.
   * The evidence: consistent across eras and tours; replicated on a second source; not moved toward by the line; nearly orthogonal to the pool and the model.
   * But its effect, +0.03 per RMS unit, is below Look A's resolution (about 0.064, one-sided), and men's non-zero share halves in 2025–26. So it needs a bundle or Look B.
   * *Inference:* it may measure rhythm without survival (the scout) or health (an injured player skips doubles).
3. **rb03_lt20 as a bundle member.** Its sign is steady and matches the scout's threshold expectation, but it is rare and small.

**Not promising:**
* The continuous rest measures and RB06.
* RB05 and RB20: the line moves against them before the close (move z −10.2, −15.5) and the close is null, so they are priced.
* The qualifier cost: only its tag, which the inputs span.
* RB02, RB23, MP-22.
* RB15: each tour is consistent across its eras, but the signs are opposite (men's r28 +2.37 in 4 of 4, women's −1.79 in 4 of 4), with no mechanism.
* RB10: the men's reading flips sign across eras, and the women's is opposite.

**Against the scout's § 7 expectations:** doubles positive at 7 days, yes (but stronger for men, and in the "else" part); previous-day doubles negative, weakly (−0.89); rest a cost only below about 20 h, yes; older returners declining among men, early eras only; lucky losers carrying U-138, no.

## 9. Caveats

* **Selection:** these are discovery readings, the best of many. BH q under 0.05 over the 210 summary rows: rb14_cold28 (both tours raw 0.020, orthogonal 0.049) and rb01_d7_else's men's orthogonal part (0.041). rb01_d7_else, both tours: 0.057. The pool's U-138: 0.002.
* **Bet time differs from history.** The start is then a schedule, about 10 min before the actual first point, and delays are unknown. Men's 2025–26 ends are start + minutes, so the rest after a suspended match is slightly overstated. A live doubles feed is needed (the TennisLive collector exists).
* **Thin data:**
  * RB01 rests on three eras.
  * The men's replication uses a coarser, event-level definition.
  * Women's pre-2018 hour data covers 55–70% (RB06 89%).
  * 4.4% of doubles member-rows are unmapped, so counts are slightly low.
* **IOS vintage:** RB10's IOS file predates the 8 Oct corrections.

## 10. Process notes (for the lead's log)

* **Read:** CLAUDE.md, the log's §§ 1–3 and chronology, the harness, the scout's memo, CSV and scripts, the practitioner's § 3.6 and MP rows, the store and universe rows. The luck builder's header was read for conventions only; no other builder's file was touched.
* **Before any screen**, outcome-free checks (session scratchpad: `explore_*.py`, `smoke*.py`, `overlap.py`) prompted: the draw from its structure, events grouped by tour, RB02 clipped, the RB13 variants.
* **Run 1** printed six RB01 readings, then crashed: the move lens is singular for the all-zero Sackmann version.
* **Mechanical fixes after it:** exact exclusive sums; the same-day doubles test; a lens guard (at least 200 non-zero rows). No definition changed; run 2 reproduced run 1's readings exactly.
* **Run 3**, adding the 60-minute split, was stopped halfway (its readings matched run 2's) when I added RB14's placebo.
* **Run 4**, the final run, produced every output file. Both additions came after run 2's readings had been seen; they are readings only, and no statistic changed.
* **Not built:** RB07 heat and RB16 withdrawals (downloads).
