# Round 2 builds · EDA analyst MARKET

6 October 2026 · Research evidence, not a decision. Built to the round-2 [hypothesis family](../hypothesis_family.md) and [rulings](../rulings.md), which supersede the round-1 cards where they differ, and to the contract in [builders.md](../../builders.md). **No result was read.** No column is related to `a_won`, and no season after 2024 is loaded: the long table is cut at the panel's last earliest-start day. Nothing was committed and nothing deleted. The screen has not been run.

Every module passes `./python.sh src/eda/feature_interactions/screen_batch.py --prepare --module <module>`. That covers swap tests on x and the controls, plus coverage and novelty; the partial tables are under `data/studies/feature_interactions/hypotheses/`. Each row's column and controls are described below; the numbers are in `data/studies/feature_interactions/round2/market/`.

## Status

Coverage (both players' columns defined) is 99.9–100% in every tour × window (2014–2021 and 2022–2024; `diagnostics.json`). The 2025–2026 rows were not loaded: the feasibility audit counted 8,593 test rows. Novelty is the R² of the candidate column on the 58 inputs, 2014–2021: s·η for price slopes, the `eta_model` version for `x_of_eta` rows. "+M" adds the M-set (η, η³, η|η| per tour).

| hid | module | test · sign · weight · trait | candidate | swap | R² on 58 (+M) | gate, probe |
|---|---|---|---|---|---|---|
| I-036 | f10 | single · + · 1 · slow | η·O | ✓ | 0.27 (0.31) | – |
| I-084 | f10 | single · + · 0.5 · slow | η·ΣR | ✓ | 0.26 (0.31) | – |
| I-049 | f10 | single · + · 0.5 · none | η·E | ✓ | 0.04 (0.04) | – |
| B-FLB | f10 | signed sum · + · 0.5 · none | η·(L̃ + H̃P) | ✓ | 0.14 (0.20) | – |
| I-042 | f11 | single · + · 1 · slow | τ(η), `x_of_eta` | ✓ | 0.66 (0.89) | hazard SD 1.03 / 1.56 pp ≥ 1; weight 2 → 1 by the addendum; probe passed |
| I-082 | f12 | single · + · 1 · none | Δ(w̃_L s_L) | ✓ | 0.38 (0.38) | – |
| B6 | f13 | signed sum · − · 1 · slow | η·(flux + Σ\|age − 28.5\| + U_rest) | ✓ | 0.03 (0.03) | I-028 dropped (split-half 0.05 < 0.3); flux gate 74% ≥ 5% |
| B-ANCHOR | f14 | signed sum · per member · 0.5 · none | −η·a + k(2fam − 1), `x_of_eta` | ✓ | 0.16 (0.17) | – |
| B-RECAL | f15 | Wald 2 df · ± · 0.5 · none | r̄·adj, adj³ | ✓ | 0.07 / 0.42 (0.08 / 0.89) | – |
| B-REPUTE | f16 | signed sum · − · 1 · slow | Δ(g a) + Δ(F R) + sign(η)\|ΔFat\|, `x_of_eta` | ✓ | 0.33 (0.37) | – |
| LIT-2 | f16 | single · + · 0.5 · slow | \|η\|·ΔF, `x_of_eta` | ✓ | 0.70 (0.82) | – |
| B-INFO | f17 | signed sum · + · 1 · slow | Δ1(−A) + (F − z)O_min + s·Δ(w̃_q s_q) | ✓ | 0.09 (0.11) | – |
| B-OVERREACT | f18 | signed sum · per member · 0.5 · none | −ΔΛ + \|r\| sign F − Δs·1[QF+] − raw·1[n ≥ 3] | ✓ | 0.16 (0.18) | β_f probe passed; luck split-half 0.16 < 0.2 |
| B-MOTIV | f19 | signed sum · − · 0.5 · slow | s·Δtop + Δpost | ✓ | 0.05 (0.06) | – |

All 14 rows pass the batch's swap test on x and on the controls (the ten modules run together in 124 s). For `x_times_eta` rows the batch's own novelty column is the R² of the symmetric s: 0.59 for I-049 and 0.68 for B-FLB, functions of the context inputs. The table gives the candidate s·η instead. The I-042 probe also covers estimators (b) and (c); the I-025 probe covers β_f.

## Shared construction (`features/mkt_common.py`)

* **Std controls.** The three model inputs most correlated (|corr|, 2014–2021 rows) with the candidate column: s·η for a price slope, x otherwise. Candidates are the antisymmetric inputs other than `odds_logit` (the base already carries the price), plus the two switch pairs as A − B. The batch records the names.
* **Modulators.** Symmetric modulators are centred per tour on the 2014–2021 rows, except where the family writes a literal uncentred indicator whose difference is held (I-086, I-091, INFO-2, B-MOTIV).
* **Block members.**
  * Antisymmetric members are divided by their RMS on 2014–2021; symmetric ones are centred and divided by their SD.
  * A member missing in a row counts 0 there, with its missing indicator as a control.
  * Blocks whose members share one sign (B6, B-REPUTE, B-MOTIV: "−"; B-INFO: "+") sum the members as they are and carry that sign. Blocks with signs declared per member (B-ANCHOR, B-OVERREACT) multiply each member by its sign and are tested +. The two forms are the same test.
* **Fat (I-054, I-055, I-049's control).** Fat comes from the body analyst's `f20_fatigue.prepare_fat` (I-052's kernel, τ2 = 3 days, walk-forward imputation), so the family has one Fat. The imputed-share difference is a control, and 1[share > 0.5] an η-modulator.
* **Base-dependent columns.** I-042, B-ANCHOR (I-037's η·a), B-REPUTE (I-055's sign(η)) and LIT-2 return the coordinator's `x_of_eta(eta, rows)` hook. Their `x` is the `eta_model` version, as the batch asks. Inside a composite, `x_of_eta` standardises the members on the given rows' 2014–2021 part, so each base's members get their own scale.
* **History.** Own-sequence quantities come from strictly earlier rows, so they are safe by construction. The clock `t` is each player's running maximum of the best-estimate day (`history.py`'s `obs_mono`), so it stays monotone under the harness verifier's corrected ordering, where rounds of undated events no longer reverse. Every module and diagnostic was re-run on that ordering. Anything pooled over players (I-042's tour rate, I-025's β_f, and estimators b and c) is fitted per target season on matches with lf + 1 ≤ that season's earliest start, and probed.

## The rows

### Price slopes (`f10_price_slopes.py`)

* **I-036.**
  * Built: O = max(log rank_A, log rank_B) minus the tour's median on 2014–2021; unranked = 1500, with the flag (0.2% of rows).
  * Fitted jointly with I-084 (ΣR), B-FLB (L, HP) and B-LEVER. B-LEVER's modulators are imported from `f02_leverage`: its B-LEVER row when present, else I-001's κ_pair and I-006's 1[bo5].
  * Std: elo_overall, elo_games, ratings_iid (corr 0.19–0.21 with η·O).
  * Anchor [A/I]: rerun on Pinnacle descriptively. Pinnacle covers 98.9–99.9% of rows per season, 2013–2024.
* **I-084.**
  * Built: ΣR = R_A + R_B overall Elo, centred per tour and standardised.
  * Controls: η × level (four level indicators); I-036's O, B-FLB's L and HP; Std points_52w (0.40), ios_points_short, iosD_bp_saved.
  * Corr of η·O with η·ΣR is −0.68 (the audit's −0.70).
* **I-049.**
  * Built: E = 1[min(n_A, n_B) < 3], centred.
  * Fitted jointly with B6's BOD-C2 (Σ log1p rest) and I-054 (ΣFat, f20). Corr with η·ΣFat is −0.31.
  * Novelty: nearly orthogonal to the 58 (R² 0.04). The rival BOD-C2 predicts the opposite sign.
* **B-FLB** (new: LIT-1 + MAT-L1).
  * L = 1[not the draw's first main-draw round]. The first round comes from the draw size; a Finals round robin counts as the event's first stage.
  * HP = 1[Slam or Tour Finals].
  * Each centred and standardised, summed (+); fitted jointly with I-036, I-084 and B-LEVER.
  * Correlations: HP·η with bo5·η 0.72 (the rebuttal's 0.71); L·η with I-036 −0.32.
  * L·η with HP·η is −0.05 once centred. The rebuttal's −0.56 was for the uncentred products.
  * Round depth is a sensitivity, not built.

### I-042, retirement hazard × price (`f11_retirement.py`)

* **Column.** τ = ĥ_B/p − ĥ_A/(1 − p), p = σ(η), through `x_of_eta`, so each base uses its own η. `x` is the `eta_model` version; it correlates 0.93 with the price version.
* **Controls.** M-set and Std only (ratings_iid, elo_games, elo_overall; corr ≈ −0.75): no Δĥ (MAT-R1a) and no Σĥ·η.
* **Novelty.** τ is 66% spanned by the 58 and 89% with the M-set, because its Σĥ·sinh z part is a smooth odd function of the price. The screen therefore tests the hazard-specific remainder, an RMS of about 0.036 logit.
* **Hazard estimator (a)**, MKT-20's shrunk rate: (retirements in the last 730 days + k·r̄)/(played matches in them + k), k = 160.
  * r̄ is the tour's in-match retirement rate per played match, all levels. It is fitted per target season on matches with lf + 1 ≤ the season's earliest start.
  * Spread at model rows: mean 1.53%, SD 0.58 pp, 1st–99th percentile 0.79–3.4%.
* **Choice of estimator** (look-ledger note 1). Out-of-sample log loss on each side's own retirement in the 2013–2018 panel matches: 55,626 player-rows, 862 retirements; milli-log-loss per row, lower is better.

| estimator | log loss | vs base rate |
|---|---|---|
| tour base rate | 79.917 | 0 |
| (a) k = 5 / 20 / 40 / 80 | 84.011 / 80.650 / 79.433 / 78.728 | −4.09 / −0.73 / +0.48 / +1.19 |
| **(a) k = 160** | **78.574** | **+1.34** |
| (a) k = 320 | 78.808 | +1.11 |
| (b) MAT-W2, k = 160 (best of b) | 78.931 | +0.99 |
| (c) BOD-12 logistic | 78.591 | +1.33 |

  * Gains are versus the base rate, higher is better.
  * The first grid (k ≤ 80) chose its edge and was extended once.
  * (c) wins for men (84.18 vs 84.37) and (a) for women (73.47 vs 73.68); pooled, (a) wins.
  * (b), (c) and the moment-K beta-binomial (MAT-R1b) are sensitivities.
* **Hazard-spread precheck** (result-free; split-half over own-order parity, players with 20+ matches a half, 2010–2018).
  * The de-noised persistent SD is 1.03 pp on the main tour (775 players; split-half r 0.28; method of moments 1.05) and 1.56 pp at all levels (4,330; r 0.40).
  * Both are ≥ 1 pp, which by the round-1 rule would keep weight 2.
  * The estimator's own spread is 0.58 pp. The bound ½σ²E[2 cosh z] at that spread is ≈ 0.06 mLL (men), against 0.19 at the persistent 1.03 pp.
  * **Weight 1** (the rulings' addendum, late 6 Oct): 89% of τ is spanned by the 58 plus the M-set, so the rule's premise that all of τ is identifiable fails. The column, sign and controls are unchanged.
* **Probe.** Cuts at 15 Jun 2016, 28 Aug 2019 and 7 Sep 2022. Every match that surely started after the cut had its winner reversed, or was removed, and the hazards were rebuilt.
  * (a), (b) and (c): the largest change at any match that surely finished by the cut is 1.3e-12 (tolerance 1e-9, the project probe's). 61–96% of later matches moved, so the probe is not vacuous.
  * It caught two real leaks, both fixed. A missing age had been filled with the median over all rows; it is now a constant 26. The minutes-imputation medians had come from 2010–2018; they now come from the 2010–2012 warm-up.
* **Open.** The books' settlement rules are unverified in all three sources. The shape test (Δĥ free) is a secondary, not built.

### I-082, salience-weighted evidence (`f12_salience.py`)

* **Column.** x_L = Σ d n z / (Σ d n + 200) over each player's low-visibility matches: Challenger and WTA 125 main draws and qualifying, plus tour and Slam qualifying.
  * d = 2^(−age/14 days); n = points played; z = Stage B's per-match z_adjperf_tpw, the model's adjperf source. Corr 0.994 with the panel's form when rebuilt.
  * Primary Δx_L (+), a TabPFN difference column.
* **Controls.** adjperf_tpw_2w; the nearest form_* (form_brk); Std (form_rpw_first, sets_14d, form_rpw_second); the high-visibility analogue Δx_H; the lower-level-evidence indicator A − B.
* **Coverage and novelty.** Defined for every row. 47% (men) and 41% (women) of player-rows have lower-level evidence in the last 91 days. R² 0.38 on the 58.
* **Open.** Lower-level box scores more than double in 2025: a covariate shift into the test.

### B6, transient uncertainty (`f13_uncertainty.py`; rebuilt to the rulings' addendum)

* **Members** (all −, each centred per tour and standardised on 2014–2021, summed as they are).
  * **I-033 flux.** Σ(form − ℓ*)². form = adjperf_tpw_2w; ℓ* = r·ℓ52, the 52-week level on the form's own scale. Stage B's tpw constants: K3 = 10 men, 20 women; half-life 2 weeks. So form − ℓ* = r(raw two-week mean − ℓ52), free of the shrinkage gap.
  * **BOD-L2.** Σ|age − 28.5| (Stage 0 age).
  * **U_rest (I-054 + BOD-C2).** R² minus its mean (per tour, 2014–2021), R = [std Σlog1p(rest) − std ΣFat]/√2, each standardised per tour on 2014–2021. rest = days since the previous played match at any level; Fat from f20.
  * The two linear columns correlated −0.944 and shared the sign −, so the addendum makes them one pre-declared U: flatter at both ends of one rest axis. They are now sensitivities.
* **Controls.** ΔFat, the Fat-imputed difference, M-set, Std (surf_layoff A − B, sets_14d, age).
  * η-modulators: R (the axis's linear slope, so U_rest is identified by curvature alone), I-049's E (jointly fitted), and the missingness indicators (1[imputed share > 0.5], flux missing, rest missing).
* **Gates.**
  * I-028 drops: pooled split-half 0.051 under the corrected history order (0.041 before). That is 0.011 for men (508 players, 50+ matches a half) and 0.154 for women (198); at 25+ a half, 0.108 and −0.005. Computed on 2010–2018 with f06's own measure; between-player variance ≈ 0.
  * I-033's feature-only gate passes: 74% of matches have implied flux variance (β²·F_pair, β the price's loading on the form difference: 2.41 men, 3.93 women) above 0.03 logit², against the ≥ 5% required.
* **Numbers.** Members correlate between −0.12 and 0.06, so they no longer cancel.
  * Novelty of each member's s·η: I-033 0.04, BOD-L2 0.05, U_rest 0.03. The block 0.03 (0.03 with the M-set).

### B-ANCHOR, artefacts of the average close [A] (`f14_anchor.py`)

* **I-037 (−).** a = 1 − (1/max_A + 1/max_B), centred, × η. The member depends on the base, so the block is `x_of_eta`. Its `x` (`eta_model` version) correlates 0.996 with the price version.
  * Positive a in 43% of rows: the best prices cross routinely.
  * Rules: incoherent pairs (a maximum below the average, 0.07%) are missing; a is winsorised at its 0.5% and 99.5% quantiles on 2014–2021.
* **I-038 (+).** k·(2fam − 1), literally as the family writes it. k = logit p_max(A) − z, winsorised symmetrically at ±(the 99.5% quantile of |k|); fam = 1[sign(k) = −sign(ΔF)].
  * Equal fame (20% of rows) gives fam = 0, so −k there. Setting ties to 0 is a sensitivity, not registered.
  * Fame F = log(1 + main-tour titles + Slam QF-or-better events), strictly earlier. It is counted from 2010, so careers that began earlier are left-censored.
* **Controls.** k, ΔF, M-set; Std (elo_games, elo_overall, ratings_iid, corr ≈ −0.38).
* **Numbers.** Members correlate 0.19. The I-038 member is 66% spanned by the 58: k leans with the price, and k is held.
* **Open.** OddsPortal's maximum may include exchanges (unknown). Bet-time quotes are needed to deploy.

### B-RECAL, the model's own adjustment (`f15_recal.py`)

* **Built.** adj = eta_model − odds_logit (the current best's adjustment, fixed for both bases). x = [r̄·adj, adj³], Wald 2 df.
  * r̄ = I-032's evidence weight, the harmonic mean of n/(n + 20) over surface matches rated, centred.
* **Controls.** adj, M-set, Std: three nearest per member (elo_games, elo_overall, age; ratings_iid, ios_points_short, points_52w).
* **Novelty.** r̄·adj is new (R² 0.07). adj³ has R² 0.42 on the 58 but 0.89 with the M-set: (η − z)³ shares η³ and z with the screen's nuisance. Its remainder has RMS ≈ 0.066 logit, so the I-041 column is mostly the screen's own cubic. Flagged.

### B-REPUTE and LIT-2 (`f16_repute.py`)

* **B-REPUTE (sign −, each member summed as it is).**
  * I-071: Δ(g·a). g = ê(log rank) − Elo, where the line ê is Elo on log rank per tour, 2013–2018 rows, ranked players only, no outcome; a = (age − 27)/5; Stage 1's unranked rule plus a flag.
  * I-083: Δ(F·R). R = career-peak overall Elo since 2010 minus current Elo, ≥ 0; F is fame as above.
  * I-055: sign(η)·|ΔFat|, η the base's, so the block is `x_of_eta`. sign(price) ≠ sign(η_model) in 2.2% of rows.
  * Members correlate −0.31 (I-071, I-083), 0.04 and 0.14. Block R² 0.33.
  * Controls per member: Δg, Δunranked, ΔF, ΔR, ΔFat, the Fat-imputed difference; Std forced elo_overall and age, plus elo_games and ratings_iid.
  * η-modulators: Σg, Σa, ΣF, ΣR, |ΔFat|, and LIT-2 jointly as sign(η_model)·ΔF·η. That equals LIT-2's |η|ΔF exactly at the model base.
* **LIT-2 (+, new).** |η|·ΔF via `x_of_eta`.
  * Controls: ΔF, M-set, B-REPUTE's x (`eta_model` version) jointly, and Std (elo_games, elo_overall, ratings_iid, corr ≈ 0.79).
  * R² 0.70 on the 58 (0.82 with the M-set). Corr with I-083 0.48 (the rulings' 0.50).
* **Open.** The joint-fit controls are exact at the model base (the gating one). At the market base they hold the `eta_model` version, a difference confined to the 2.2% of rows where the signs differ.

### B-INFO, thin information (`f17_info.py`; I-081 and I-087 withdrawn, MKT-R1 and MKT-R2)

* **I-080 (+).** Δ1·(−A). Δ1 = ratings_iid's view minus offset Elo's, each rescaled to the price's SD within tour on 2013–2018, with SDs taken after a 0.5/99.5% winsorisation (ratings_iid saturates at ±9.21).
  * A is the mean of four components, each standardised on 2013–2018 (the originator's window): level, round depth, star power, and crowding (the other main-draw matches of both tours on the same day).
* **C-2 (+, new).** (F − z)·O_min. F = c·(elo_overall + elo_surf_offset), c = SD(price)/SD(offset Elo) per tour on 2014–2018 (fit-free, MKT-R4; corr 0.92 with the price).
  * O_min = the better-ranked player's log rank, centred per tour.
* **INFO-2 (+, new).** s·Δ(w̃_q s_q).
  * s = 1[the draw's first main-draw round, and exactly one player is a fresh Q or LL: a qualifying match already played at this event, rest ≤ 1 day].
  * w̃_q s_q = Σ n z/(Σ n + 200) over that player's earlier qualifying matches at the event. Nonzero in 5.8% of rows.
* **Controls.** Δ1, F − z, the linear Δ(w̃_q s_q), I-082's column, I-076's column (`f24_onsite`), Std.
  * η-modulators: A, O_min, the INFO-2 flag, the both-unranked flag. No M-set (not listed).
* **Numbers.** Members correlate −0.35 (I-080 with C-2) and ≈ 0 with INFO-2. Block R² 0.09.

### B-OVERREACT, over-reaction to salient results (`f18_overreact.py`)

* **I-025 (−).** ΔΛ, MEC-08's 13-week index with shrinkage 3. Over completed box-score matches, e = y − σ(β_f(t − ½)), t = the points share.
  * β_f is a no-intercept logistic per tour × best-of, fitted walk-forward per target season (lf + 1 ≤ the season's earliest start). Typical values: 131–133 (men, Bo3), 156–159 (Bo5), 128–149 (women).
  * Women's Bo5 has no rows and takes the Bo3 slope.
  * Probe: the same three cuts, reversed and removed; the largest change at earlier matches is exactly 0, while 99% of later matches move.
  * MEC-08's skill gate: split-half r of e = 0.16 (962 players, 30+ a half) < 0.2, so it stays luck.
* **I-085 (+).** |r|·sign F, r = z − F with r held (MKT-R4), F the fit-free Elo forecast above. Sign disagreement in 52% of rows; SD(r) 0.39.
  * The no-odds TabPFN sibling exists only from 2019. The fallback is fit-free and covers 100%, with one source for every season.
* **I-086 (−).** Δs·1[round ≥ QF], s = 1 − own de-vigged price in the previous main-draw match at this event.
  * S11: 0 without such a match, after a walkover, or after a round-robin loss; missing only when unpriced.
  * Coverage 99.9%, including 99.9% of QF+ rows (the rulings' 99.6–99.9%); the column is nonzero in 16.5% of rows.
* **I-091 (−).** raw·1[n ≥ 3] over earlier played meetings at every level (n ≥ 3 in 21% of rows).
  * The shrunk Elo residual Σ(y − p_elo)/(n + 2) is held; k = 2 is MEC-08 arm b's pair shrinkage.
* **Controls.** I-025's elo_games, elo_overall, adjperf_tpw_2w, points_52w; r; Δs; the missing-price difference; the head-to-head residual; M-set; Std.
  * η-modulators: the disagreement indicator, 1[QF+], missing price, 1[n ≥ 3].
* **Numbers.** Members correlate within ±0.16. Block R² 0.16.

### B-MOTIV, calendar effort (`f19_motiv.py`)

* **Members (both −, summed as they are).** s·Δtop, with s = 1[250/500]·1[a Slam main draw starts within 8 days of es] and top = 1[rank ≤ 20]. Δpost, with post = a Slam QF-or-better at another event, finishing within 21 days.
* **Prevalence.** s holds in 7.4% of rows; the members are nonzero in 1.7% and 2.1%.
* **Controls.** Δtop; s·η; Std (elo_overall, elo_games, ratings_iid). Δdef deferred.
* **Note.** Slam start days are calendar facts, read only up to the panel's last day. This is harmless now: no 2024 match falls within 8 days of a 2025 Slam.


## Look-ledger notes (for the meta-auditor)

1. **I-042's estimator choice.** I read the retirement label (each side's own in-match retirement) of the 2013–2018 panel matches, out of sample, to compare the tour base rate, estimator (a) at k ∈ {5 … 320}, (b) at the same grid and (c). That is the statistic target the round-1 ruling prescribed. The grid was extended once, from k ≤ 80 to 320, because the first grid chose its edge. Nothing else was tuned on it, and `a_won` was never read.
2. **Prices as scale constants.** Δ1's two views (2013–2018), the Elo forecast F (2014–2018: I-085, C-2) and I-033's flux gate use SDs or slopes of the price, without outcomes. The math audit's ledger row 6 covers prices as regressors.
3. **Feature-only gates.** These read statistics, not results: I-042's hazard spread (retirements), I-028's split-half reliability (set scores and serve points) and I-025's split-half (past wins against points shares).

## Open issues for the orchestrator

0. **B6's cancellation** is resolved by the addendum's U_rest; the rebuilt block's members correlate within ±0.12.
1. **Cross-module dependencies, which change my hashes when they change.**
   * Fat comes from `f20_fatigue.prepare_fat` (B6, I-049, B-REPUTE).
   * I-076's column comes from `f24_onsite` (B-INFO), and B-LEVER's modulators from `f02_leverage` (I-036, B-FLB).
   * Re-run `--prepare` after the structure and body analysts' last edits. When f02 gains its B-LEVER row with κ_surf, my rows pick it up automatically.
2. **Base-dependent joint fits.** I-042, B-ANCHOR, B-REPUTE and LIT-2 use `x_of_eta`. The controls that carry one of them into another row's fit (LIT-2 inside B-REPUTE, B-REPUTE inside LIT-2) are exact at the model base and approximate at the market base.
3. **Mostly spanned columns** (ruled in the addendum). I-042's τ (89% with the M-set) is now at weight 1. B-RECAL's adj³ (89%) stays as built: the remainder (RMS ≈ 0.066 logit) is I-041's own hypothesis.
4. **Fame is left-censored at 2010** (B-ANCHOR's fam, I-083, LIT-2). Veterans' early-season F understates their pre-2010 titles.
5. **The batch's `module_hashes()`** covers `f*.py` and the top-level files, not `features/mkt_common.py`, my shared helper. The x and control hashes still catch any output change; adding the helper to the hashed set would close the gap.
6. **Not built.** I-028, by its gate. I-042's shape test, I-085's no-odds TabPFN form, B-MOTIV's Δdef, the venue arm of I-091, round depth for B-FLB, and B-ANCHOR's tie-to-0 variant are all sensitivities.
7. **Process.** Early in the session I overwrote the structure analyst's scratch `explore1.py` in the shared scratchpad root (a dev script, no project file). My scratch now lives in `scratchpad/market/`.


## Files

* Modules: `src/eda/feature_interactions/features/f10_price_slopes.py`, `f11_retirement.py`, `f12_salience.py`, `f13_uncertainty.py`, `f14_anchor.py`, `f15_recal.py`, `f16_repute.py`, `f17_info.py`, `f18_overreact.py`, `f19_motiv.py`; shared helpers `mkt_common.py`.
* Diagnostics: `src/eda/feature_interactions/round2/market_build/diagnostics.py`. The estimator comparison, precheck and probe for I-042 run from `f11_retirement.py`; β_f, the split-half and the probe for I-025 from `f18_overreact.py`.
* Outputs: `data/studies/feature_interactions/round2/market/i042.json`, `b_overreact.json`, `diagnostics.json`; partial tables `data/studies/feature_interactions/hypotheses/partial_f1*.csv`.
