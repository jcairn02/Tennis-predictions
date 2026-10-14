# Luck builder (S2b): scoring luck read as skill, seasons ≤ 2024

13 Oct 2026 · Role S2b ([brief](../briefs/06_luck_builder.md)) · Claude Opus 5.5, a subagent of session `e1ffc84e-fa2d-42f9-9d17-7c936a046c45` · Code: `src/eda/unpriced_leads/build_luck.py` (one command, about 8 minutes) · Outputs: `data/studies/unpriced_leads/candidates/luck/` · Definitions: [point_structure.md](point_structure.md) §§ 3–4, 7

* **Outcomes read:**
  * through the harness only (matches before 2025);
  * per-match residuals of matches finished before 2025 (persistence);
  * 2010–12 (calibration).

  2025–26 values were computed for every frame match; nothing from 2025 on was compared with a result or a line move.
* **Key:** z and β, + = the player higher on the statistic beats the close (− = he does worse). "Clears 0" means |z| ≥ 1.96; otherwise the reading is "unresolved" with P(β<0).
* The harness z has SD ≈ 1.08 under the null, and I ran 44 statistics × 2 forms, so a single |z| < 3 is weak.
* *Observed* = the outputs; *inferred* = my reading.

## Summary

1. **Built:**
   * 14 primary statistics: PS01; PS06 close and deciding; PS03 save, faced, conversion and chance, plus hold, break and net; PS04 run luck and flattery; PS11; PS02 Elo gap;
   * the pool's I-025 beside them;
   * 5 secondaries;
   * 24 decay variants.

   **Timing probes: 0 changed values** in both builders at all cuts; a deliberately leaky variant is caught.
2. **The PS01 bias is large, not "conservative"** (observed, 2010–12).
   * At the match's own rates the iid tiebreak chance is far too flat: at π ≈ 0.525, men win 58.1% (SE 1.0) and women 62.3% (SE 2.0) of tiebreaks.
   * Without the tiebreak's own points in the rates, the iid model fits (slope 0.88–1.01).
   * I therefore recalibrated every set-level expectation on 2010–12, before any screen. The three PS01 forms correlate 0.97–0.98 in the decayed sums.
3. **Beside the close, 2013–24, both tours** (raw / orthogonal z): hold luck −3.6 / −2.0, flattery −3.6 / −2.4, net break-point luck −3.1 / −2.3, close sets −3.1 / −2.4, tiebreaks −2.6 / −2.3, conversion −2.6 / −2.3, save −2.6 / −1.2, I-025 −2.1 / −1.6.
   * The luckier player does worse than the close; each reading clears 0.
   * Every negative-registered statistic reads negative, except chance creation (+2.8). Faced luck (registered +) reads −2.5 for men.
   * Best BH q is 0.03.
4. **Gate** (prices only): given point-based skill, the close loads positively on luck in 8/8 tour-era cells for tiebreak, close-set, deciding-set, conversion, hold, break and net luck, the Elo gap and I-025.
   * Save and flattery are positive in 6/8 cells under the brief's Z, and in 7/8 and 8/8 under c_pts.
   * Faced, chance and run luck are negative.
   * Outcomes take back about half to all of the loading for component luck (β/c_pts −0.5 to −1.3).
   * They take back only 15–35% for match-level luck (Elo gap, I-025, deciding set).
5. **Persistence looks like luck:** split-half ≤ 0.09 for every residual, against 0.68 (men) and 0.60 (women) for the serve-point rate.
6. **Weak spots:**
   * Tiebreak and close-set luck sit in 2017–22 and are near 0 in 2023–24, one of the analyst's kill criteria.
   * Flattery's gate support needs c_pts.
   * The Elo gap fails β ≈ −c.

## 1. Construction

* **Eligible rows** (574,394 of 1,746,874 `H.long_table` rows): completed, a box score, standard format, a complete best-of-3/5 score (best-of read from the score), consistent point counts.
  * p_i = spw_n/spw_d and p_j = 1 − rpw_n/rpw_d, both clipped to [0.01, 0.99].
  * Rule: `stage2_iid.deciding_set_rule`.
* **Calibration, frozen** (`calibration.json`): side-A eligible matches of 2010–12 that surely finished before 2013 and are not frame matches (men 26,153, women 10,137).
* **Aggregation:** over strictly earlier eligible rows at every level, S = Σ 2^(−Δdays/91)·e (secondaries h = 365 and a flat 52-week sum).
  * Days come from the clock's `obs`.
  * Prefix sums are shifted one row (bit-exact).
  * 0 plus a `hist` flag without history; decayed counts are companions.
* **Screened column:** A − B, and `H.orthogonal_part` (frozen projections in `orth_coef.json`).

**Frozen constants:**

| Constant | Men | Women |
|---|---|---|
| Recalibration slope a, tiebreak (bo3/bo5) | 1.79 / 1.49 | 2.03 |
| a, tiebreak without its own points | 0.88 / 0.98 | 1.01 |
| a, close sets / 7–5 remainder / deciding set | 1.75 / 1.63 / 2.74 | 2.07 / 2.07 / 4.09 |
| s̄(p) = expit(c0 + c1 logit p) | c0 −0.002, c1 1.110 | c0 0.025, c1 1.063 |
| φ̄ constant (× `f08_clutch.bp_per_game`) | 0.998 | 1.005 |
| β of Λ_P (bo3/bo5); κ of flattery | 5.01 / 4.85; 2.17 | 5.74; 2.40 |

## 2. The statistics (A − B; registered sign in brackets)

* **PS01 tiebreak (−):** tiebreaks won − Σ π̃_TB(p_i, p_j, target); target 10 for a deciding tiebreak under a 10-point rule.
  * Primary: recalibrated at the match's rates (the brief's p).
  * Secondary `tb_ex`: rates without the tiebreaks' points (the bracket gives the loser's points; each player served half; his points split serve:return as p_i : 1 − p_j).
  * Sensitivity `tb_raw`: the literal uncalibrated form.
* **PS06 close (−):** sets won among sets that reached 5–5 − Σ π̃_55.
  * 5–5 is identifiable from the score: the loser of the set has 5+ games. So all such sets are used, tiebreak sets included.
  * π_55 = w + t·π_TB (tiebreak at 6–6), w/(w+l) (advantage set), w(1−t⁷)/(1−t) + t⁷π_TB7 (tiebreak at 12–12), with w = h_i(1−h_j), l = (1−h_i)h_j and t = 1−w−l. Serving order does not matter; this matches a DP to 4e-16.
  * Secondary `close_notb`: 5–5 sets that ended without a tiebreak.
* **PS06 deciding (−):** 1[won] − π̃_set(rule) in deciding-set matches.
* **PS03 (break points):**
  * save S − F·s̄(p_i) (−); faced F − G·φ̄(p_i) (+); conversion C − Ch(1 − s̄(p_j)) (−); chance Ch − G_opp·φ̄(p_j) (−).
  * Combined (all −): hold = e_S − (1−s̄_i)e_F (exact excess holds); break = e_C + (1−s̄_j)e_Ch; net = hold + break.
  * G is scaled so that G + G_opp equals the score's non-tiebreak games.
  * **Women's service games are missing in all of 2010–12 and 56% of 2013–16**: there, G = half the non-tiebreak games (flagged).
  * Within a match, break_A = −hold_B, conv_A = −save_B and chance_A = faced_B. The statistics differ only through each player's own history.
* **PS04:**
  * Run luck (−): Σ(y − Λ_P) over earlier eligible matches at this event (U-138's segments, qualifying included); `run_complete` flags gaps.
  * Flattery (−): logit(games share) − κ·logit(points share) of the previous played match at any event. Secondary `flat_event`: only if that match was at this event.
* **PS11 (+):** over the last 10 eligible matches, losses with more points minus wins with fewer.
* **PS02 (−):** Elo gap (R_y − R_Λ)·ln10/400, from Stage 1's Elo pass and frozen "ret" constants, run on results and with Λ_P on eligible matches.
  * The results run reproduces Stage 1's stored ratings exactly in 2010.
  * Secondary PS02 match: a decayed sum of y − Λ_P.
* **Against the pool:**
  * I-025 is one shrunk 13-week mean with a walk-forward β.
  * market_anchoring's luck is men-only, uncalibrated, per game.
  * Mine are split into components, calibrated and frozen on 2010–12, decayed sums, for both tours at every level.

## 3. Timing and coverage

* **Probes** (`probes.json`): 0 changed of 626k / 916k / 1.25M pre-cut rows, and 0 of 21,705 / 17,675 / 12,793 first-post-cut rows (cuts 2016, 2019, 2022). This holds for all 52 player columns and for the Elo gap.
* **Negative control:** inclusive sums change 2,457 own rows.
* **Cross-player construction:** none, apart from the 2010–12 constants.

**Coverage** (frame rows before 29 Jul 2026, debut seasons out; share where both players have the history needed):

| | Men 2013–24 | Men 2025–26 | Women 2013–24 | Women 2025–26 |
|---|---:|---:|---:|---:|
| Rows | 29,895 | 4,394 | 27,836 | 4,197 |
| Decayed sums, PS11, PS02 | 99.9% | 100% | 99.2% | 100% |
| PS04 run / flattery | 92.2 / 89.9% | 92.1 / 88.1% | 86.8 / 79.5% | 92.7 / 86.9% |
| I-025 (store) | 91.2% | 100% | 100% | 99.0% |

The store lacks 52% of the current frame's 2018 matches (men) and 22.5% of 2026's.

## 4. Readings, 2013–24, both tours

* z and the eras, model lens (beyond the current instance's forecast), move lens (+ = the line moves toward him) and R² are the harness's.
* c is the close's loading (Z = the brief's inputs); c_pts uses the points-only Z (§ 5).
* β and c are pooled over the 8 tour-era cells, per RMS unit.

| Statistic (sign) | z | eras | z orth | model | move | R² | c (z) | c_pts | β | Reading |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Tiebreak (−) | −2.60 | 4 | −2.28 | −1.20 | −0.89 | 0.08 | .037 (19) | .033 | −.018 | clears 0 |
| Close sets (−) | −3.06 | 3 | −2.36 | −0.99 | −0.66 | 0.09 | .041 (20) | .041 | −.022 | clears 0 |
| Deciding (−) | −1.65 | 3 | −1.26 | −2.27 | −3.69 | 0.20 | .040 (22) | .050 | −.017 | P(β<0) 0.95 |
| Save (−) | −2.60 | 4 | −1.16 | −0.43 | +0.08 | 0.41 | .007 (3) | .021 | −.025 | clears 0 |
| Faced (+) | −1.24 | 3 | −0.54 | +0.44 | +0.43 | 0.35 | −.005 (−2) | −.006 | −.014 | P(β<0) 0.89 |
| Conversion (−) | −2.63 | 3 | −2.35 | +0.19 | −1.24 | 0.45 | .028 (10) | .022 | −.029 | clears 0 |
| Chance (−) | +2.77 | 3 | +2.58 | +0.39 | +1.01 | 0.39 | −.012 (−5) | .004 | +.028 | clears 0, wrong sign |
| Hold (−) | −3.60 | 4 | −2.04 | −1.96 | −0.86 | 0.29 | .019 (8) | .045 | −.035 | clears 0 |
| Break (−) | −1.10 | 2 | −1.03 | +0.83 | −0.54 | 0.27 | .032 (14) | .049 | −.009 | P(β<0) 0.86 |
| Net (−) | −3.13 | 4 | −2.35 | −0.70 | −0.90 | 0.28 | .037 (15) | .061 | −.029 | clears 0 |
| Run luck (−) | −1.18 | 3 | −1.33 | −0.06 | −8.39 | 0.09 | −.023 (−13) | −.022 | −.017 | P(β<0) 0.88 |
| Flattery (−) | −3.55 | 4 | −2.40 | −1.48 | −3.32 | 0.09 | .006 (3) | .015 | −.039 | clears 0 |
| PS11 (+) | +1.23 | 3 | +0.81 | +0.94 | +2.09 | 0.05 | −.020 (−11) | −.025 | +.011 | P(β>0) 0.89 |
| Elo gap (−) | −1.29 | 3 | −0.39 | −1.22 | −1.69 | 0.28 | .065 (34) | .079 | −.012 | P(β<0) 0.90 |
| I-025 (−) | −2.11 | 4 | −1.58 | −2.32 | −2.86 | 0.17 | .041 (21) | .053 | −.017 | clears 0 |

* **By tour** (men / women, raw z): tiebreak −1.77 / −1.21; close −1.66 / −1.80; deciding −0.65 / −1.98; save −3.26 / −0.78; faced −2.52 / +0.17; conversion −1.98 / −2.02; chance +2.18 / +2.10; hold −3.31 / −2.20; net −2.43 / −1.92; run −2.88 / +0.11; flattery −3.59 / −1.88; Elo gap −0.26 / −1.56; I-025 −1.00 / −1.89.
* **Eras** (2013–16 / 2017–19 / 2020–22 / 2023–24): tiebreak −0.07 / −2.83 / −1.47 / −0.26; close +0.02 / −3.46 / −1.68 / −0.11; hold −1.44 / −1.45 / −3.04 / −1.41; flattery −3.17 / −0.99 / −1.47 / −1.13.
* **Secondaries** (raw / orthogonal): `tb_ex` −2.19 / −2.20; `tb_raw` −2.26 / −2.23; 7–5 remainder −0.84 / −0.28 (PS06's signal is its tiebreak part); `flat_event` −3.09 / −1.75 (women −3.15); PS02 match −1.47 / −0.96.
* **Decay variants:** h = 365 and the 52-week sums read weaker (|z| ≤ 1.3 for tiebreak, close, hold and net) with larger c (tiebreak h = 365: c +0.048, β −0.004). Conversion (−2.3) and chance (+2.1) keep their signs. Inferred: luck summed over a year is priced correctly or carries skill.

## 5. The gate: c against β

* **The fit:** per tour and era, L_close = Z·b + c·x, clustered by four-week block. Z holds the brief's 44 inputs. The analyst predicts β ≈ −c for pure luck.
* **Component luck** (tiebreak, close, save, conversion, hold, net): c > 0 in 8/8 cells (save 6/8; 7/8 under c_pts), β/c_pts −0.5 to −1.3. This is consistent with the mechanism.
* **Match-level luck:** large c, small β. Elo gap c +0.065 with β −0.012; I-025 +0.041 with −0.017; deciding set +0.040 with −0.017. Inferred: the close largely uses it legitimately; men's match luck has a small persistent part.
* **Flattery:** β ≈ −2.6·c_pts. Men's c is 0.000 under the brief's Z, c_pts +0.013 (4/4 eras).
* **Run luck:** c < 0 and β < 0 (men −2.9), and the line moves strongly against it before the close (−8.4). That is not luck read as skill; inferred: struggle the market partly learns.
* **Chance:** β > 0 with c_pts ≈ 0. It correlates −0.84 with conversion luck; combined break luck reads −1.1.
* **Why c_pts:** the brief's Z contains conversion results that carry the tested luck: `form_hold`, `form_brk`, `form_bp_saved`, `form_bp_conv`, `form_bp_faced_pg`, `iosO/D_hold`, `iosO/D_bp_saved` and the prod pair. Save luck correlates 0.50 with `form_bp_saved`.
  * c_pts drops these 12 inputs.
  * It was **added after the first gate readings**, for that structural reason; it reads prices only.

## 6. Persistence (≤ 2024; `persistence.csv`)

Split-half correlation, alternate matches of a player-season, 10+ matches per half (5,405 men's, 2,196 women's player-seasons), men / women:
* **Tiebreak and set pieces:** tiebreak 0.02 / 0.00; close 0.05 / −0.02; 7–5 remainder 0.01 / 0.00; deciding 0.06 / 0.02.
* **Break-point pieces:** save 0.00 / 0.02; faced −0.01 / 0.03; conversion 0.02 / 0.00; chance 0.00 / 0.02; hold 0.02 / 0.03; break 0.07 / 0.02; net 0.06 / 0.04.
* **Match level:** match 0.09 / 0.02; flattery 0.09 / 0.03; PS11 0.07 / 0.03.
* **Reference:** the serve-point rate reads 0.68 / 0.60.
* **Season-to-season** correlations are higher for net (0.17 / 0.11), match luck (0.12 / 0.07) and flattery (0.16 / 0.05).
* Inferred: a small skill part in break-point play and match conversion, mostly men's. The tiebreak and set pieces stay at about 0.

## 7. Correlations (frame ≤ 2024, A − B; `correlations.csv`)

* **Near-copies:**
  * tiebreak ~ close 0.83, ~ `tb_ex` 0.97;
  * deciding ~ PS02 match 0.91, ~ I-025 0.84, ~ Elo gap 0.77;
  * PS02 match ~ I-025 0.92;
  * PS11 ~ match −0.66;
  * save ~ faced 0.81; conversion ~ chance −0.84;
  * flattery ~ `flat_event` 0.77.

  The tiebreak and break-point families are nearly uncorrelated (|r| ≤ 0.13).
* **With `sets_14d`:** |r| ≤ 0.05, except run luck 0.13.
* **With U-138** (store `on_n` difference; my rebuilt `on_n` equals it, r 1.000): run luck 0.23, others |r| ≤ 0.10.
* **With in-model inputs:** save ~ `form_bp_saved` 0.50; hold ~ `form_bp_saved` 0.35; Elo gap ~ `elo_overall` 0.22.

## 8. Promising and not (inferred)

* **Promising:**
  * **Hold luck** (serve-side break-point luck): 4/4 eras, orthogonal part −2.0, beyond the model −2.0, c_pts > 0 in 8/8 cells. It is the luck reading of "serving over-rated".
  * **Tiebreak or close-set luck** (take one): the cleanest luck (persistence about 0, R² < 0.1), but weak in 2023–24.
  * **Flattery:** 4/4 eras, the line moves against it, beyond the model −1.5.
  * **Net break-point luck:** the one-number PS03 alternative.

  These three families are nearly uncorrelated with each other (|r| ≤ 0.14) and with `sets_14d` and U-138.
* **Not promising:**
  * Elo gap (orthogonal part −0.4) and the decay variants;
  * the 7–5 remainder and break luck alone;
  * PS11 (weak);
  * run luck (c < 0; women +0.1; the line moves before the close: an early-bet question);
  * the four PS03 pieces separately (mirror pairs; chance reads against its sign).
* **I-025** belongs to the match-luck cluster (r 0.92 with PS02 match).

## 9. Caveats

* **Women's service games** are imputed for all 2010–12 calibration rows and 56% of 2013–16 rows.
* **Calibration drift:** men's faced residual drifts +0.01 to +0.04 per match in 2015–24 (1–2% of its SD; `residual_drift.csv`). Its A − B correlation with the decayed-count difference is ≤ 0.10.
* **Coverage gaps:** ITF has no box scores (arrivals start with no luck history); women's box scores are thin in 2013–16; I-025 has the 2018 hole.
* **Inherited choices:** the Elo constants were tuned on 2013–18 inside Stage 1, an inherited in-sample choice.
* **Multiplicity:** the best of 44 × 2 screens. No |z| reaches 4, and the families overlap.

## 10. Process notes (for the lead's log)

1. Read the brief, CLAUDE.md, the log, the harness, the memo and CSV, the Stage 2 code, `f18_overreact`, `f08_clutch`, market_anchoring's `luck.py`, `stage1_baselines` and the registry.
2. Took outcome-free counts ≤ 2024.
3. 2010–12 calibration revealed the PS01 bias; I tested the ex-tiebreak rates on 2010–12, then fixed the PS01 forms and the service-game imputation.
4. Ran the probes, the negative control, the Elo and DP checks.
5. Pinned BLAS to one thread (the lenses were 100× slower on the busy machine). The first full run crashed after the screens (a pandas read-only array) before anything was printed.

**All of steps 1–5 came before any screen result.** I first looked at readings in run 2, then added c_pts and reran: the readings are identical. **No statistic definition changed after a screen.**
