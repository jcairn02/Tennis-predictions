# Feature interactions, round 0: the mathematics lens

6 October 2026 · Brainstormer "mathematics" (Opus) · Research evidence, not a decision.

Written blind to the other brainstormers and to the literature, as [team.md](../team.md) sets. Shared context: [brief.md](../brief.md).

**Keys.**
* **Computed**: an exact mechanistic calculation made in this round. No match result was read, and no feature was related to results or prices. Every calculation uses seasons up to 2021 only; later rows are dropped as each table is loaded. Feature tables were read for their own distributions, and the 2013–2021 closing odds (average, Pinnacle, overround) for their own distribution: the shape of the log-odds, the margin, and the average against Pinnacle.
* **Inferred**: reasoning. **Suggestion**: a proposal.
* **Value bounds** are milli-log-loss (mLL) of gain over the price, higher is better. They are upper bounds under the stated assumption, not measured scores.

**Files.**
* Script: `src/eda/feature_interactions/round0/mathematics/markov_composition.py`. Run it with `./python.sh`; it takes about 2 seconds.
* Outputs: `data/studies/feature_interactions/round0/mathematics/`, with `results.json` and the CSV grids.
* Tests: `test/feature_interactions/test_round0_mathematics.py`, 11 passing. They cover:
  * the iid model against `stage2_iid.py` (agreement to 3e-16) and the textbook hold of 73.57% at p = 0.60;
  * antisymmetry, and that the first server does not matter;
  * the serve/return exchange invariance;
  * the quadratic identity behind `prod_<s>`;
  * the de-vig inversions;
  * the day-noise attenuation.

## Five results to read first

1. **Under the iid model, four numbers reduce to two, and the A − B frame holds only one of them.**
   * Serve points are logit-additive: logit p_AB = μ + S_A − R_B. So the four per-player levels reach the match only through two quantities:
     * ΔT = (S_A + R_A) − (S_B + R_B), the total-strength gap;
     * ΣY = (S_A − R_A) + (S_B − R_B), the pair's serve dominance.
   * The style difference ΔY and the pair's total strength ΣT are irrelevant to the outcome.
   * The model's differences carry ΔT, and also ΔY, which is irrelevant under iid. They cannot carry ΣY.
   * Computed on the 39,918 training rows of 2013–2021 (leak-proof surface IOS of serve points won), the pair part of the serve dominance has SD 0.131 logit for men and 0.097 for women. That is **twice the spread due to surface** (0.067 and 0.043). Surface is the smaller part of a match's character.
2. **The leverage of a point-level gap falls with serve dominance, and the fall is twice as large on the logit scale as on the probability scale.**
   * Leverage on the logit scale, β_L = ∂logit P/∂Δ, falls by 4.0%, 4.8% and 5.5% per 0.1 logit of dominance on men's clay, hard and grass. Women's: 2.0–3.4%.
   * ∂P/∂(p_A + p_B) at fixed p_A − p_B is negative for the favourite. At a mean serve probability of 0.62 and d = 0.04 (Bo3) it is −0.080: if both players win one more serve point in a hundred, the favourite's match probability falls by 0.16 pp.
   * Bo5 multiplies the leverage by exactly 1.25 near an even match.
   * The match probability is **exactly invariant under exchanging serve and return**: P(p_A, p_B) = P(1 − p_B, 1 − p_A), to 1e-14 under every set rule. So leverage is an even function of the serve dominance around ½: the modulation is zero to first order at m = ½ and grows with the distance from it. This is why the women's modulation (m ≈ 0.56) is two to three times weaker in its relative slope than the men's (m ≈ 0.63), and about eight times smaller in value.
3. **Day-to-day noise damps every leverage effect.**
   * Stage 3's over-dispersion: opponent-adjusted serve and return rates vary 1.6–1.7 times as much as binomial chance from match to match (constants from 2013–2018).
   * That implies a day noise on the point-level gap of variance ≈ 0.075 logit² for men and 0.069 for women.
   * The pre-match log-odds is then c·β·Δ, with c² = 0.47–0.75 (Bo3) depending on the assumptions.
   * A change of leverage reaches the pre-match odds multiplied by c². For example, the Bo5/Bo3 log-odds ratio falls from 1.25 to 1.10–1.13.
   * A consistency check, comparing two marginal spreads only: the price's log-odds have SD 1.09 (men) and 0.95 (women) in 2013–2021. That is 0.74 and 0.73 of the spread of the iid log-odds composed from the surface IOS, close to the implied c = 0.69–0.77.
4. **What an interaction is worth.**
   * A missing log-odds term τ costs about ½E[p(1−p)τ²] per match. On the 2013–2021 price distribution, E[p(1−p)z²] = 0.157 for men and 0.136 for women.
   * **Rescaling the price by a relative κ is worth ≈ 79κ² mLL** (men; 68κ² women).
   * **Rescaling the model's own adjustment by κ is worth only ≈ κ² mLL.** The adjustment's RMS is about 0.1 logit (inferred from the thinking report's 1.7 pp average).
   * So interactions that only modulate the existing adjustment, by format, surface or match character, are worth under 0.05 mLL. This fits TabPFN's near-zero use of context.
   * Worthwhile interactions either modulate the price itself or bring per-player information the inputs do not hold.
5. **The detection threshold** (inferred). The surface-IOS study's 80% power was 0.26 mLL on 23,819 matches. Scaled by √n, that is ≈0.20 on the 39,918 discovery matches and ≈0.34 on 2022–2024.
   * Several composition ideas bound below the threshold after damping. They carry a **kill-by-calculation** verdict, so the cone can close them without EDA.

## What the A − B frame can and cannot express (the algebra this file uses)

* **Can:**
  * any function of the differences;
  * a difference times context (surface, level, best of, round, tour, indoor);
  * products of three differences, which are antisymmetric (for example, the convexity in Δ);
  * the two surface-switch pairs.
* **Cannot:**
  * pair sums: serve dominance ΣY, prominence ΣT, the variance sum ΣV, the uncertainty sum Σv;
  * within-player non-linear terms f(x_A) − f(x_B) for non-linear f;
  * per-player reliabilities and hazards;
  * anything about the market beyond the de-vigged log-odds, such as the overround or the dispersion between books.
* **The one place sums hide.** `ratings_iid` and `ios_points_short` compose point ratings through the iid model with the scheduled format. Each holds ΣY inside one number that the model cannot decompose.
* **Quadratic identity** (tested). With x_A = O_A − D_B and x_B = O_B − D_A:
  * x_A² − x_B² = (O_A² − O_B²) − (D_A² − D_B²) + 2·prod_s, where prod_s = O_A(−D_B) − O_B(−D_A) is the model's column.
  * The second-order term of any logit-scale statistic's effect on points needs the within-player squares, which the model lacks, as well as prod_s.
* **Identifiability.** A symmetric column has no main effect on P(A) − ½, so an S × Δ term is identified cleanly given the main effect of Δ. For W ideas, the test is the curvature beyond the linear difference.

## The ideas

Grouped by type: C composition (7), W within-player (2), X cross-player (2), S symmetric × difference (5), U uncertainty (5) and M market state (6), 27 in all. Seven carry a kill-by-calculation verdict: C6, C7, S3, U3, U5, M4 and M6.

### MAT-C1 · The long-memory surface profile composed into a match log-odds

| Field | Content |
|---|---|
| ID, name | MAT-C1, composed surface-IOS match log-odds (points route) |
| Mechanism | A serving to B wins a serve point with p_AB = fi·fw + (1 − fi)·sw. Each component comes from the leak-proof surface IOS: fi_AB = expit(μ_fi + O^fi_A − D^fi_B), and likewise for first-serve points won (fw) and second-serve points won (sw). The iid chain with the scheduled format turns (p_AB, p_BA) into a match probability. One column then carries what the IOS profile says about who wins, with the structurally right weights: each component's difference weighted by the pair's own means (first serves in; the first-minus-second gap), the expit curvature, the pair's serve dominance and the format. |
| Why the price might miss it | It adds no new raw information; the case is efficiency. The owner's thesis places the edge in the per-statistic profile, and TabPFN leans on the IOS group most (its share of the thinking fit's adjustment: 0.62 men, 0.74 women). An additive learner must otherwise rebuild a non-additive composition from 21 noisy columns. One structurally weighted column lets any market-orthogonal part enter with a single weight. |
| Type | C (with S and X content) |
| Formula | z_C1 = logit P_iid(p_AB, p_BA; best of, deciding-set rule). **Swap:** p_AB ↔ p_BA, so P → 1 − P and z_C1 → −z_C1 (antisymmetry checked to 9e-16). **Variants:** the noise-integrated version (MAT-C4); the residual z_C1 − ratings_iid, which is what the long-memory surface profile says beyond the Stage 3 points ratings. |
| Data | `data/studies/surface_ios/surface_features.parquet` (`srf_O_eff_*`, `srf_D_eff_*` for first_in, first_won, second_won, A and B). Surface averages from `predictability_diagnostic/stage4_constants.csv`. Format and deciding-set rule from `stage4_features.scheduled_iid_prob`. **Timing:** the surface IOS is a cross-player solve on the leak-proof clock (probe passed in the surface-IOS study); the composition is a per-match function of it and inherits that. **Coverage:** every 2013–2021 training row joins (share 1.000). |
| Why the model cannot already do it | It has iosO_s, iosD_s and prod_s, all differences. **Computed:** the composed log-odds differs from the best "sum-free" version (each statistic's pair sum set to the surface mean, every difference kept) by RMS 0.139 logit for men and 0.103 for women. That is 9.8% and 9.0% of the composed log-odds' RMS (1.41, 1.14). The serve-point gap's own linearisation error is 7–8% (RMS 0.0043 of 0.059), and almost all of it needs pair sums. `ratings_iid` composes the Stage 3 points ratings and `ios_points_short` a 4- or 13-week points IOS; neither composes the long-memory surface profile. The composed serve-point gap correlates 0.987 (men) and 0.979 (women) with the surface IOS of serve points won, so C1 is close to a long-memory surface points rating passed through the iid model, which the model lacks. |
| Expected effect | **Sign:** none a priori (a representation). **Bound:** if the price ignored the pair-specific composition entirely, 0.8–1.35 mLL (men) and 0.5–0.8 (women) after day-noise damping (A6). Realistically far less: the price is a match-level price and embeds composition. **Where:** men, grass and Bo5, where leverage and the dominance spread are largest. |
| Kill test | In the shared screen on 2013–2021, beyond the price and the current best's forecast: z_C1, or its residual on ratings_iid, gains < +0.1 mLL on both tours, or its coefficient changes sign between 2013–2017 and 2018–2021. **Feature-only precheck:** if corr(z_C1, ratings_iid) ≥ 0.98, screen only the residual. |

### MAT-C2 · The games route, and the points-versus-games residual

| Field | Content |
|---|---|
| ID, name | MAT-C2, hold-IOS composition and its residual against the points route |
| Mechanism | **Compose the hold IOS** (h_AB = expit(μ_hold + O^hold_A − D^hold_B)) through sets and the match. Tiebreaks use the serve-point rate whose hold is h (`stage4_features.serve_rate_for_hold`). Call the result z_C2. **The residual** r = z_C2 − z_C1 measures, per pair, who holds and breaks more than their serve-point rates imply: break-point play on both sides. Stage 2 found that mostly luck. The exception is a persistent return component in the Slam point-by-point data: split-half 0.21 (men) and 0.19 (women), against ≈0 under luck. The long-memory IOS is the least noisy measure of that persistent part. |
| Why the price might miss it | Results-based ratings fold games won into strength. A structural residual that mixes luck with a small skill can be mis-weighted in either direction. |
| Type | C (X) |
| Formula | r = z_C2 − z_C1. Both terms are antisymmetric, so r is. |
| Data | surface_features (hold and the three serve components). Leak-proof clock, inherited. |
| Why the model cannot already do it | It has iosO_hold, iosD_hold, prod_hold and the components, all as differences. **Computed:** hold and points are nearly linear on their logit scales: d logit(hold)/d logit(p) = 2.50 at p = 0.50, 2.61 at 0.62, 2.99 at 0.76. So the per-player residual is close to a linear combination the model already has. What it lacks is the set and match level, where the share of sets reaching 6-6 moves from 0.12 to 0.53 across m = 0.50–0.74. |
| Expected effect | Small. Positive weight on r if return big-point skill persists. Not boundable mechanistically; prior ≤0.1 mLL. |
| Kill test | **Feature-only first:** split-half reliability of the per-player residual of hold over composed hold (50+ matches a half) < 0.3 → kill. **Otherwise:** screen gain < +0.1 mLL → kill. |

### MAT-C3 · The pair's serve dominance as match context

| Field | Content |
|---|---|
| ID, name | MAT-C3, pair serve dominance m_pair, and the tiebreak share, as symmetric context columns |
| Mechanism | ΣY/2 + μ_surface is the match's serve dominance. It sets the leverage of the gap: on the logit scale −4.0%, −4.8% and −5.5% per 0.1 logit on men's clay, hard and grass, and −2.0% to −3.4% for women. It also sets how often sets reach a tiebreak: 0.20 at m = 0.62, 0.32 at 0.68 and 0.42 at 0.71 (Bo3 grid). |
| Why the price might miss it | Point-based bookmaker models include it; Elo-like and ranking-based pricing do not. The mix in the close is unknown. |
| Type | S (enables S × Δ and M × S) |
| Formula | m_pair = ½(logit p_AB + logit p_BA) − μ_surface, from the surface IOS of serve points won. tb_share = P(set reaches 6-6 \| p_AB, p_BA). **Swap:** both are symmetric, since a swap exchanges p_AB and p_BA. Computed: reaching 6-6 does not depend on who serves first (checked on three pairs to 1e-6). Having no main effect, they act only through interactions. |
| Data | surface_features `srf_O_eff_spw_*`, `srf_D_eff_spw_*`. Leak-proof. |
| Why the model cannot already do it | Differences cannot carry a sum. **Computed:** in 2013–2021 the pair part has SD 0.131 logit (men) and 0.097 (women), against 0.067 and 0.043 for the surface part. It is uncorrelated with the gap (r = −0.004 and −0.013), so no difference proxies it. `ratings_iid` holds it inside one composed number. Realistic mean serve probabilities of a pair, 5–95%: men 0.586–0.698, women 0.524–0.609. |
| Expected effect | Only through products. For the product with the price and its bound, see MAT-M1 (≤0.22 mLL men after damping). |
| Kill test | Jointly with MAT-M1. As a TabPFN arm on the 2019–2021 validation windows, ties the current best (< +0.1 mLL) → kill. |

### MAT-C4 · Noise-integrated composition

| Field | Content |
|---|---|
| ID, name | MAT-C4, compose with day-to-day noise: E_u[P_iid] instead of P_iid |
| Mechanism | A player's level varies from day to day, so the pre-match probability is the iid probability averaged over that noise. **Computed:** with the day-noise variance from Stage 3's over-dispersion, the pre-match log-odds is c·β·Δ. c² is 0.60 (men Bo3), 0.49 (men Bo5) and 0.57 (women). The Bo5/Bo3 log-odds ratio becomes 1.13, or 1.10 if a player's serve and return days correlate 0.5, instead of the iid 1.25. `ratings_iid` and `ios_points_short` are composed with the noiseless model. Their Bo5 values are therefore 11–14% too large relative to Bo3, and their dominance modulation 1.3–2 times too strong (1/c²). |
| Why the price might miss it | It need not: the price is empirical. This corrects the model's composed inputs, whose scale is wrong by format and dominance in a way the A − B frame cannot fully undo. |
| Type | C |
| Formula | z_C4 = logit ∫ P_iid(μ_pair + (Δ + u)/2, μ_pair − (Δ + u)/2; format) φ(u; 0, V) du, by Gauss–Hermite with 48 nodes (`gh_expect_P`). **Swap:** the swap maps (Δ, u) to (−Δ, −u) with u symmetric, so z_C4 → −z_C4. **V:** from `stage3_shrinkage.csv` (2013–2018), or tuned on 2013–2018 by the composed forecast's own log loss without odds. |
| Data | As MAT-C1 and C3, plus Stage 3's constants. Timing inherited. |
| Why the model cannot already do it | TabPFN can rescale `ratings_iid` by best_of (both are inputs), but not by the pair's dominance (absent). |
| Expected effect | As a replacement for `ratings_iid`/`ios_points_short`, ≤0.1 mLL (inferred from the leverage bounds). Its main value is diagnostic: if V ≈ 0.07 fits better than V = 0 in 2013–2018 without odds, the damping that bounds C3, C5, M1 and S3 is confirmed. |
| Kill test | Without odds, 2013–2018: the noise-integrated version does not beat the noiseless one by ≥ +0.1 mLL → revisit the damping. If damping is absent, the leverage ideas' bounds rise by up to 1/c⁴ ≈ 2–4. |

### MAT-C5 · The price on the point scale

| Field | Content |
|---|---|
| ID, name | MAT-C5, invert the price to a point-level gap and express the profile's disagreement there |
| Mechanism | Δ_mkt solves P_iid(·; m_pair, format) = p_mkt, or the noise-integrated equivalent. On the point scale, the profile's view and the price's view add without format or dominance leverage. Recomposing then gives each adjustment its correct match-level weight automatically: larger at Bo5 (×1.10–1.13 after damping), larger for lopsided matches, smaller for big-server pairs. **Computed:** the marginal leverage at Δ = 0.5 logit is 1.27 times (Bo3) and 1.41 times (Bo5) its value at Δ = 0. |
| Why the price might miss it | It does not; this is about how the model applies its adjustment. |
| Type | C × M |
| Formula | d_pt = Δ_prof − Λ⁻¹(z_mkt; m_pair, format). **Swap:** Λ is odd in Δ at fixed m_pair, so Λ⁻¹(−z) = −Λ⁻¹(z) and d_pt is antisymmetric. |
| Data | As C1 and C3, plus odds_logit. |
| Why the model cannot already do it | Format and lopsidedness are learnable, since best_of and odds_logit are inputs; m_pair is not. |
| Expected effect | By the rule of thumb (an adjustment of RMS ≈ 0.1 logit rescaled by κ is worth ≈ κ² mLL), with κ ≈ 0.1–0.4 in the affected subsets: ≤0.05 mLL overall. **Do not screen unless MAT-C1 passes.** |
| Kill test | Dies with C1. Otherwise C5 against C1 in the screen < +0.05 mLL → kill. |

### MAT-C6 · The deciding-set rule as an input (kill by calculation)

| Field | Content |
|---|---|
| ID, name | MAT-C6, the Slams' deciding-set rule (advantage, 10-point tiebreak, tiebreak at 12-12) as context |
| Mechanism | The rule changes the leverage of the deciding set. |
| Why the price might miss it | Unlikely; and it is negligible. |
| Type | S |
| Formula | A rule code (symmetric). |
| Data | `stage2_slam_final_set_rules.csv` |
| Why the model cannot already do it | It is absent from the 58 inputs. |
| Expected effect | **Computed**, against a 7-point tiebreak at 6-6, at d = 0.02–0.05: P(match) rises by 0.04–0.08 pp with a 10-point tiebreak and by 0.13–0.32 pp with an advantage set or a tiebreak at 12-12 (≤0.019 logit). Only in matches that reach a deciding set. Bound < 0.01 mLL. |
| Kill test | Killed by calculation; no EDA. |

### MAT-C7 · Hold-versus-points scale interaction (kill by calculation)

| Field | Content |
|---|---|
| ID, name | MAT-C7, interaction between the hold profile and the point profile through their scales |
| Mechanism | Hold and serve-point IOS live on different logit scales, so combining them might need an interaction. |
| Why the price might miss it | n/a |
| Type | W |
| Formula | d logit g(p)/d logit p, with g the hold function. |
| Data | None (mechanistic). |
| Why the model cannot already do it | It can: the relation is near-linear. |
| Expected effect | **Computed:** the slope is 2.50 (p = 0.50), 2.61 (0.62), 2.80 (0.70) and 2.99 (0.76). Within the men's realistic range it stays within ±5% of 2.65, so a linear combination suffices. |
| Kill test | Killed by calculation. |

### MAT-W1 · Within-player squares that complete prod_s

| Field | Content |
|---|---|
| ID, name | MAT-W1, per-statistic curvature: sq_s = (O_A² − O_B²) − (D_A² − D_B²), or the probability-scale edge e_s |
| Mechanism | IOS is additive on the logit scale, but points are won on the probability scale. By the quadratic identity, the second-order term of σ(μ + x_A) − σ(μ + x_B) needs the within-player squares as well as prod_s. For a low-rate statistic the curvature is large: a big server's ace edge on the probability scale is convex in his logit rating. Aces are also the most reliable per-match statistic: half signal in 1.9 matches (Stage 3). |
| Why the price might miss it | If the market reads serve strength roughly linearly from reputation or ranking, the convex tail (extreme servers and returners) is where it would err. |
| Type | W (with X) |
| Formula | sq_s, or e_s = expit(μ_s + O_A − D_B) − expit(μ_s + O_B − D_A). **Swap:** both antisymmetric (tested). Start with s ∈ {ace, df, hold, first_won}. |
| Data | surface_features O_eff and D_eff for these statistics. Leak-proof. |
| Why the model cannot already do it | The squares need each player's level. **Computed, 2013–2021**, the non-linear part as a share of the probability-scale edge's RMS (men, women): aces 32%, 37%; double faults 21%, 22%; holds 18%, 9%; first-serve points won 9%, 5%; first serves in ≤8%; second-serve points won 1%. prod_s alone explains R² 0.01–0.12 of that non-linear part; prod_s with the squares explain 0.85–0.99. prod and the squares are strongly anti-correlated (men: −0.64 aces, −0.90 first-won, −0.92 hold), which is why prod alone captures so little. |
| Expected effect | **Sign:** favours the stronger extreme (big servers on fast courts). **Size** against the price is unknown; plausibly 0–0.3 mLL. **Where:** men, grass and indoor hard. |
| Kill test | Screen 2013–2021 with e_ace, e_df and e_hold (or sq_s): < +0.1 mLL beyond the price and the current best → kill. |

### MAT-W2 · Retirement hazard enters as h_B/p − h_A/(1 − p)

| Field | Content |
|---|---|
| ID, name | MAT-W2, per-player retirement hazard with the exact odds-level weighting |
| Mechanism | The population includes retirements, and the label is "the player who advanced". With hazards h_A and h_B and a played-out probability P_c: P(A advances) = (1 − h_A − h_B)P_c + h_B. On the log-odds scale the correction is τ ≈ h_B/P_c − h_A/(1 − P_c). A favourite's own hazard is multiplied by 1/(1 − P_c): ×5 at P_c = 0.8, ×10 at 0.9. If per-player hazards beyond the price's knowledge have SD σ_h, knowing them is worth ½σ_h²·E[2 cosh z]. |
| Why the price might miss it | Bookmakers' retirement rules differ (some void bets when a player retires early), so an averaged close may price only part of the retirement risk our label counts. And chronic fragility differs from an acute, visible injury. |
| Type | W × M |
| Formula | τ_hz = ĥ_B/p_mkt − ĥ_A/(1 − p_mkt). ĥ_i is a shrunk per-player rate of retirements (and walkovers), with recent-retirement and layoff modifiers. **Swap:** p → 1 − p and A ↔ B give τ_hz → −τ_hz. |
| Data | `stage0_matches` status over each player's history: the player's own matches in order, safe by construction. odds_logit. The mean hazard is about 3%: Stage 2 counts 3.4% of men's and 2.9% of women's (2019+) evaluation matches ending in retirement. |
| Why the model cannot already do it | No retirement or injury history is among the 58 inputs, and the effect is not additive in log-odds: it needs p. surf_layoff_a/b is a weak proxy. |
| Expected effect | **Computed bound**, if the price ignores the persistent hazard: E[2 cosh z] = 3.63 (men) and 3.13 (women). That gives 0.05/0.04 mLL at σ_h = 0.5 pp, 0.18/0.16 at 1 pp, 0.73/0.63 at 2 pp. The value is concentrated in lopsided matches: \|z\| > 1.5 in 17% of men's and 11% of women's matches. **Sign:** lowers fragile favourites. |
| Kill test | **Feature-only first:** the de-noised SD of a persistent per-player retirement rate (split-half, as in Stage 3) < 0.5 pp → kill (bound < 0.05). **Then** screen < +0.1 mLL → kill. **Overlap:** body lens (injury), market lens (settlement rules). |

### MAT-X1 · The iid sufficient statistics: a rotation and a structural null

| Field | Content |
|---|---|
| ID, name | MAT-X1, (ΔO, ΔD) → (ΔT, ΔY): total strength against style difference |
| Mechanism | Under the iid model the outcome depends only on ΔT and ΣY. The style difference ΔY and the total ΣT carry no information about who wins. So, given the price, any weight on ΔY can only come from two sources: non-iid structure (clutch, momentum, stamina in long rallies) or a market style bias, for example the public overrating big servers. |
| Why the price might miss it | That is the test: a style bias in the market is a market-orthogonal signal. |
| Type | X (representation and test) |
| Formula | ΔT_s = iosO_s + iosD_s and ΔY_s = iosO_s − iosD_s; both antisymmetric. |
| Data | The model frame's in_iosO_s and in_iosD_s. Leak-proof. |
| Why the model cannot already do it | Linearly it can: this is a rotation. The contribution is the structural prediction, plus a basis in which TabPFN's per-input curves follow the mechanism. **Computed:** per-player style has SD 0.185 logit (men) and 0.137 (women), total strength 0.222 and 0.193. Opponents' totals correlate 0.28 (draw structure); their styles do not. |
| Expected effect | Under iid and an efficient price, the coefficient on ΔY given the price and ΔT is 0. A non-zero coefficient is a lead, and its sign says which style the price under-rates. |
| Kill test | Discovery: the ΔY composite's coefficient CI includes 0 on both tours → no feature; record it as structural confirmation. |

### MAT-X2 · Second-serve exposure (a cross-statistic matchup)

| Field | Content |
|---|---|
| ID, name | MAT-X2, A's second-serve exposure against B's second-serve return |
| Mechanism | p_AB − p_BA contains (1 − fi_AB)sw_AB − (1 − fi_BA)sw_BA: how often a player must hit a second serve, times how well the opponent punishes it. prod_s pairs only the same statistic; this pairs first serves in with second-serve returns. |
| Why the price might miss it | It is matchup-specific, invisible in either player's record alone. |
| Type | X |
| Formula | E_2 = (1 − fi_AB)(1 − sw_AB) − (1 − fi_BA)(1 − sw_BA), the second-serve points lost per serve point; antisymmetric. |
| Data | surface_features (first_in, second_won). |
| Why the model cannot already do it | Cross-statistic products are absent. |
| Expected effect | **Computed:** the whole non-linearity of the composed serve-point gap is RMS 0.0043 (7%), mostly expit curvature, so this term is a small part of MAT-C1. Listed so the auditors can choose an interpretable form if C1 passes. |
| Kill test | Dies with C1. |

### MAT-S1 · Pairs instead of differences for the composition-relevant levels

| Field | Content |
|---|---|
| ID, name | MAT-S1, give TabPFN (O^spw_A, O^spw_B) and (D^spw_A, D^spw_B) as two exchanged pairs |
| Mechanism | The model already takes two inputs as pairs exchanged at swap: surf_season_a/b and surf_layoff_a/b. Doing the same for the serve-point offence and defence gives it ΔT, ΣY, ΔY and ΣT at once. It could then learn any S × Δ, W or X form itself instead of being handed one. |
| Why the price might miss it | Only through what TabPFN then finds (MAT-C3, M1, S2, W1). |
| Type | S (enabler) |
| Formula | Four columns. A swap exchanges a and b; forecasts are symmetrised over both orientations as now. |
| Data | surface_features spw. Leak-proof. |
| Why the model cannot already do it | Differences hide levels. **Observed:** the runner trains on the stored orientation only (`local_fits.py`, `arms.job_data`) and symmetrises at prediction time. So TabPFN must learn the exchange symmetry from about 40,000 rows. Training on both orientations would impose it, a suggestion that matters for every S-type column. |
| Expected effect | Bounded by what it enables: ≤0.2 mLL by this file's bounds unless an unmodelled structure exists. Cost: 4 inputs. |
| Kill test | TabPFN arm on the 2019–2021 validation windows: < +0.1 mLL over base → kill. |

### MAT-S2 · Pair prominence modulates how much the price knows

| Field | Content |
|---|---|
| ID, name | MAT-S2, ΣT (the pair's total strength) × the price, and × the profile |
| Mechanism | Under iid, ΣT is irrelevant to the outcome given ΔT. It is not irrelevant to the market: matches between two strong players draw more money and information. So the price's optimal slope, and the profile's weight beside it, may vary with ΣT. The model has only crude proxies (level, round). |
| Why the price might miss it | That is the premise: liquidity and attention differ by match, and so does the close's error. |
| Type | S × M |
| Formula | z_mkt·(ΣT − mean ΣT) and Δprofile·(ΣT − mean ΣT). ΣT is symmetric, so the products are antisymmetric. ΣT comes from the surface IOS (O + D of serve points won, summed over both players) or from offset-Elo levels. |
| Data | surface_features; per-player Elo levels (the cartographer to locate). Leak-proof. |
| Why the model cannot already do it | No sums. |
| Expected effect | **Computed rule:** a price slope that varies with RMS κ across matches is worth 79κ² mLL (men) and 68κ² (women): κ = 4% gives 0.13 mLL, κ = 8% gives 0.50. **Sign:** a steeper price slope for prominent pairs. **Overlap:** market lens. |
| Kill test | Discovery 1-df slope interaction, CI includes 0 → kill. |

### MAT-S3 · Format × the model's adjustment (kill by calculation)

| Field | Content |
|---|---|
| ID, name | MAT-S3, best of 5 × the profile's adjustment |
| Mechanism | An adjustment learned mostly on Bo3 should be 1.10–1.13 times as large at Bo5 (1.25 times without day noise). |
| Why the price might miss it | n/a (model-side). |
| Type | S |
| Formula | best_of × Δprofile (context × difference: antisymmetric) |
| Data | Model frame |
| Why the model cannot already do it | It can: best_of is an input. |
| Expected effect | **Computed:** κ = 0.10–0.25 on the 20% of men's rows at Bo5 gives ≈ 0.2 × κ² ≈ 0.002–0.013 mLL. |
| Kill test | Killed by calculation. |

### MAT-S4 · Volatility: the pair's day-to-day variance flattens the odds

| Field | Content |
|---|---|
| ID, name | MAT-S4, per-player day-to-day variance; the pair's sum modulates the log-odds |
| Mechanism | Take two players with equal mean strength but different day-to-day variance σ_i² on the point-level scale. Then P = E_u[P_iid(Δ + u_A − u_B)], so z ≈ βΔ/√(1 + πβ²(σ_A² + σ_B²)/8). **Computed:** d ln z/d ln V = −½(1 − c²), which is −0.20 (men Bo3, c² = 0.60) to −0.25 (c² = 0.50). A pair 30% more erratic than average has log-odds 6–8% flatter. At this order only the sum matters; skew adds an antisymmetric term, folded into MAT-W2. |
| Why the price might miss it | Ratings, rankings and the public price means. Variance is a second moment that most models ignore, and bookmakers' Markov models use fixed rates. |
| Type | S (× U) |
| Formula | V_pair = σ̂_A² + σ̂_B² (symmetric). Terms z_mkt·(V_pair/V̄ − 1) and Δprofile·(V_pair/V̄ − 1), antisymmetric. σ̂_i² is the player's long-memory mean of squared per-match residuals of opponent-adjusted serve and return (logit scale), minus the binomial part 1/(n p(1 − p)), shrunk. |
| Data | Per-match residuals against pre-match ratings (Stage 3 ratings or IOS), or the per-match z in `ufc_ideas/stageB_adj.parquet`. **Timing:** aggregated per player, but the residuals use cross-player ratings, so the leak-proof clock and `probe.py` apply. |
| Why the model cannot already do it | Every input is a mean or a difference of means. |
| Expected effect | **Computed bound** if the price ignores it, by the pair variance's coefficient of variation (CV), both tours: CV 0.1 gives 0.03–0.05 mLL; 0.2 gives 0.12–0.20; 0.3 gives 0.28–0.45; 0.5 gives 0.77–1.25. If conditions explain half the over-dispersion, the bound at CV 0.3 is 0.11. The pair CV is about the per-player CV divided by √2. **Sign:** negative on z_mkt × V_pair. |
| Kill test | **Feature-only first:** split-half reliability of σ̂_i² (50+ matches a half) < 0.3, or a de-noised pair CV < 0.2 → kill (bound < 0.2 mLL). **Then** the 1-df screen. |

### MAT-S5 · Within-match streakiness

| Field | Content |
|---|---|
| ID, name | MAT-S5, set-to-set swings beyond iid, per player |
| Mechanism | Swings of form within a match add set-level randomness and shrink the leverage of a point-level edge. Stage 2 saw a tour-level sign of it: the women's points share decides matches less than an iid replay predicts (log loss 0.118 against 0.103). If streakiness is a player trait, the pair's sum modulates the log-odds as in MAT-S4. |
| Why the price might miss it | It is invisible in match-level records. |
| Type | S (× U) |
| Formula | K_pair = κ̂_A + κ̂_B. κ̂_i is the excess variance of the player's per-set game share beyond what the iid model gives at the match's own rates (from set scores), shrunk. Term: z × (K_pair − K̄). **Swap:** K_pair is symmetric, so the term is antisymmetric. |
| Data | Stage 0 scores (per-set games), and point-by-point data where it exists. The player's own history: safe by construction. |
| Why the model cannot already do it | Nothing within a match enters the model. |
| Expected effect | Below MAT-S4, since the tour-level part is already in `tour`. ≤0.1–0.2 mLL. |
| Kill test | Split-half reliability of κ̂_i < 0.3 → kill. |

### MAT-U1 · Re-anchor the two-week form on each player's long-memory level

| Field | Content |
|---|---|
| ID, name | MAT-U1, Bayes re-anchoring of the short-memory profile with per-player reliability |
| Mechanism | form_s is a 2-week-decayed mean of per-match opponent-adjusted z, shrunk toward zero (the population) with K3 reference matches. A player with few recent matches therefore reads as "average recent form", not "unknown, presumably his usual level". The Bayes-correct short-memory estimate shrinks toward the player's own long-memory level ℓ_i: form*_i = ℓ_i + r_i(raw_i − ℓ_i), with r_i = Σw_i/(Σw_i + K′). |
| Why the price might miss it | The price knows long-run levels; the orthogonal part of form is its reliable deviation from them. Mis-anchored form mixes "few recent matches" with "average form", so the model's weight on form is a compromise across players of very different reliability. |
| Type | U (W) |
| Formula | Δform*_s = form*_A − form*_B (antisymmetric), or (r_A, r_B) given as a pair. ℓ_i is on the same z scale: the player's 52-week or career adjperf (Stage B builds all three forms). |
| Data | `ufc_ideas/stageB_adj.parquet` (per-match z); Stage B's decayed sums (S0 per player); the 52-week and career forms. **Timing:** the player's own history; the opponent norms from the leak-proof per-player build (`match_timing/perplayer_features.parquet`). |
| Why the model cannot already do it | It sees form_A − form_B and the long-memory differences, not r_A, r_B or each player's level. The optimal combination r_A(…) − r_B(…) is not a function of the differences. |
| Expected effect | **Inferred:** weighting each match by its reliability recovers about CV(r)² of the form's own market-orthogonal value. The two-week profile is TabPFN's second or third most-used group (share 0.44 men, 0.24 women in the thinking fit). Plausibly +0.1 to +0.4 mLL, more for men. **Sign:** positive. |
| Kill test | **Feature-only precheck:** CV of r_i across 2013–2021 main-tour matches < 0.2 → kill (nothing to weight). **Then:** Δform* (16 columns or a composite) gains < +0.1 mLL in the screen, or a TabPFN arm on 2019–2021 ties → kill. |

### MAT-U2 · Unknown is not average: the evidence behind each IOS value

| Field | Content |
|---|---|
| ID, name | MAT-U2, per-player evidence (box-score units) behind the surface IOS, as a pair or as a weight |
| Mechanism | The surface IOS is a ridge solve. A player with little box-score evidence on the surface is shrunk toward the tour mean: surface newcomers, women's holds before 2015, players rising from levels with no box scores before 2025. A small IOS difference then means either "equal" or "unknown", and only the price can tell which. The profile's adjustment to the price should be trusted only where both players have evidence. |
| Why the price might miss it | It does not miss it; the model does. Without the evidence, TabPFN's IOS-based adjustment is diluted by the unknown cases. |
| Type | U |
| Formula | (n_A, n_B) as a pair, or ΔIOS × r̄ with r̄ = 2r_A·r_B/(r_A + r_B) and r_i = n_i/(n_i + K_s): a symmetric weight times an antisymmetric difference. |
| Data | The surface-IOS solver's per-player information (`src/eda/surface_ios/ios_surface.py` outputs), or counts of each player's box-score units on the surface within the IOS memory (the player's own history: safe). |
| Why the model cannot already do it | It has no evidence counts; surf_season_a/b (matches on the surface this season) is a partial proxy. |
| Expected effect | Positive: women (box-score holes), grass, early in a surface season. Size unknown, plausibly 0.1–0.3 mLL. Caution: for the Stage 3 points ratings, posterior variances are nearly uniform among main-tour matches (MAT-U3); check the per-surface IOS evidence the same way first. |
| Kill test | **Feature-only precheck:** CV of r̄ across main-tour matches < 0.15 → kill. **Then** screen < +0.1 mLL → kill. |

### MAT-U3 · Posterior-variance attenuation of the price (kill by calculation)

| Field | Content |
|---|---|
| ID, name | MAT-U3, z × (1 + kβ²(V + v_A + v_B))^(−½) from rating posterior variances |
| Mechanism | Integrating the logistic over a posterior variance v of the gap flattens the odds. |
| Why the price might miss it | n/a |
| Type | U × M |
| Formula | As in the name. v is symmetric. |
| Data | `stage3_ratings.parquet` sd_serve and sd_return, A and B. |
| Why the model cannot already do it | v is absent. |
| Expected effect | **Computed** (2013–2021 training rows). v has median 0.0135 (men) and 0.0116 (women); p10–p90 0.009–0.018, p99 0.025–0.031. That is small beside the day noise (0.075) and nearly uniform. The implied slope modulation has RMS 0.7% (men) and 1.2% (women) with day noise; value ≤0.01 mLL (≤0.025 without day noise). |
| Kill test | Killed by calculation. |

### MAT-U4 · Flux: when short and long memory disagree

| Field | Content |
|---|---|
| ID, name | MAT-U4, the pair's short-versus-long-memory disagreement as an uncertainty modulator |
| Mechanism | A player whose recent form departs from his long-run level (injury, a technique change, confidence) has an uncertain current level beyond the posterior variance. Both the price and the profile are then less reliable. The symmetric twin of MAT-U1. |
| Why the price might miss it | Markets adjust quickly to visible form, but may over- or under-react. |
| Type | U × M (S) |
| Formula | F_pair = (form_A − ℓ_A)² + (form_B − ℓ_B)² (symmetric) × z_mkt (antisymmetric). |
| Data | As MAT-U1. |
| Why the model cannot already do it | Per-player disagreements are not differences. |
| Expected effect | By MAT-U3's arithmetic, flux matters only if its variance is comparable to the day noise (≈0.075 logit² on the gap). For example, an extra 0.04 flattens the men's odds by about 6%. Likely ≤0.1 mLL; low priority. |
| Kill test | Feature-only: matches with implied flux variance > 0.03 logit² are < 5% of the total → kill. |

### MAT-U5 · Measurement noise in the average close (kill by calculation)

| Field | Content |
|---|---|
| ID, name | MAT-U5, errors-in-variables attenuation of the price, heterogeneous by match |
| Mechanism | Noise in the de-vigged average close attenuates its optimal slope, by different amounts in different matches. |
| Why the price might miss it | n/a |
| Type | U × M |
| Formula | z_mkt × λ, with λ the reliability of the average (symmetric), so the term is antisymmetric. |
| Data | `stage1_odds.parquet` (average and Pinnacle), odds only. |
| Why the model cannot already do it | Dispersion between books is absent. |
| Expected effect | **Computed** (2013–2021): the average's and Pinnacle's log-odds differ by SD 0.114 (men) and 0.089 (women). Even if half that variance were noise in the average, its reliability is ≥0.994, so heterogeneity of the slope is negligible (< 0.001 mLL). Pinnacle as a second price is a main effect, for the market lens. |
| Kill test | Killed as an interaction. |

### MAT-M1 · The price × the pair's serve dominance

| Field | Content |
|---|---|
| ID, name | MAT-M1, z_mkt × m_pair: a composition-implied leverage correction of the price |
| Mechanism | Suppose the price turns a strength gap into odds with a leverage that knows surface and format but not the pair's serve dominance. Its log-odds are then too steep for big-server pairs and too flat for grinder pairs. **Computed:** κ = β_L(μ_pair)/β_L(μ_surface) − 1 has RMS 7.1% (men) and 2.8% (women). The men's 5–95% range is −15.6% to +5.6%, skewed: big-server pairs lose the most leverage. On the probability scale the same modulation is about half (RMS 3.2% and 1.3%). |
| Why the price might miss it | Elo-like and ranking-based parts of the price ignore it; point-based models include it. |
| Type | M × S |
| Formula | z_adj = z_mkt(1 + b·κ_pair), or z_mkt + b′·z_mkt·m_pair. The predicted b is ≈ c² ≈ 0.5–0.75 if the price ignores dominance, and 0 if it prices it. κ symmetric × z antisymmetric = antisymmetric. |
| Data | As MAT-C3, plus odds_logit. |
| Why the model cannot already do it | m_pair is absent. |
| Expected effect | **Computed bounds:** men ≤0.40 mLL undamped on the logit scale, 0.10–0.22 after day-noise damping, ≤0.08 on the probability scale; women ≤0.05 (≤0.03 damped). Near or below the ≈0.20 detection threshold. **Sign:** a negative coefficient on z_mkt × m_pair. |
| Kill test | Discovery 1-df test, run after MAT-M5: b′'s CI includes 0, or has the wrong sign → kill MAT-M1 and the price use of MAT-C3. |

### MAT-M2 · Context-dependent recalibration of the final forecast

| Field | Content |
|---|---|
| ID, name | MAT-M2, the slope on the model's adjustment as a function of evidence, adjustment size and format |
| Mechanism | Calibration was worth more than any input tested (brief). The local model's over-confidence sits in its adjustment, a noisy estimate. The adjustment's optimal shrinkage depends on how reliable its inputs are (MAT-U2's r̄), how large it is, and the format. Recalibrate as z_final = a·z_mkt + (b0 + b1·c)(z_model − z_mkt), for one to three symmetric c. |
| Why the price might miss it | Not about the price: it recovers the model's own edge more cleanly. |
| Type | M × U |
| Formula | (z_model − z_mkt) antisymmetric × c symmetric = antisymmetric; no intercept. |
| Data | The current best's walk-forward out-of-sample forecasts from 2014 (meta-stack and surface-IOS local fits), with the context columns. |
| Why the model cannot already do it | Recalibration sits outside TabPFN, and its over-confidence is a property of the prior and the ensemble. Meta-stack's E2, a separate weight on the close, tied; a context-dependent weight on the adjustment is untested. |
| Expected effect | Each extra parameter costs ≈ tr(J⁻¹K)/(2nW) ≈ 0.4/W mLL (meta-stack): about 0.05 with eight seasons. Plausibly 0.1–0.3 mLL, if the over-confidence differs by evidence. |
| Kill test | Prequential 2019–2021 (the meta-stack design): b1's CI includes 0 for every c, or the gain is < +0.05 mLL → kill. |

### MAT-M3 · Non-linear shrinkage of the adjustment

| Field | Content |
|---|---|
| ID, name | MAT-M3, an odd non-linear map of the model's deviation from the price |
| Mechanism | Suppose the true market-orthogonal signal is sparse (none in most matches, large in a few) and the model's noise is Gaussian. Then the Bayes-optimal transform of the estimated deviation shrinks small deviations most (a soft threshold). With heavy-tailed noise, it shrinks large deviations most. One slope does neither. |
| Why the price might miss it | n/a (model-side). |
| Type | M |
| Formula | z_final = z_mkt + g(z_model − z_mkt), with g odd (for example b1·a + b3·a³, or a soft threshold); antisymmetric. |
| Data | As MAT-M2. |
| Why the model cannot already do it | As MAT-M2. The meta-stack's signed-square term (S3q) tied, but it was a no-odds model inside a stack; on the current best's deviation it is untested. |
| Expected effect | Unknown; 0–0.2 mLL. |
| Kill test | Prequential 2019–2021: b3's CI includes 0 → kill. |

### MAT-M4 · Odds × overround (kill by calculation as an interaction)

| Field | Content |
|---|---|
| ID, name | MAT-M4, the de-vig's margin loading × the match's overround |
| Mechanism | The average close is de-vigged proportionally. If the margin is loaded like the power rule or Shin's model, the de-vigged favourite comes out too low, and the slope needed grows with the overround and with \|z\|. |
| Why the price might miss it | This is the de-vig, not the market. |
| Type | M |
| Formula | z_mkt × overround (the overround is symmetric, so the term is antisymmetric) |
| Data | `stage1_odds.parquet` overround_avg (2013–2021) |
| Why the model cannot already do it | The overround is absent from the 58 inputs. |
| Expected effect | **Computed.** At the median overround of 5.75%, the implied slope is 1.10 (power) or 1.07 (Shin) at \|z\| = 1, and 1.17 or 1.10 at \|z\| = 2. That is the size of the observed recalibration slope, 1.09–1.10. For two outcomes, Shin's model coincides exactly with an equal margin per side (derived; the numbers agree). Pinnacle's log-odds are 1.07 times (men) and 1.06 times (women) the average's, consistent with its lower margin. **But** the overround is uniform (SD 0.5 pp; 5–95%: 4.8–6.4%), so its part of the slope varies by RMS 0.6–0.9%: ≤0.007 mLL. |
| Kill test | Killed as an interaction. Suggestion kept: a power or Shin de-vig is a more faithful odds input. The curvature in \|z\| is one-dimensional, and TabPFN already learns it from odds_logit. |

### MAT-M5 · The Bo5 damping check (a diagnostic that gates the leverage cluster)

| Field | Content |
|---|---|
| ID, name | MAT-M5, does reality amplify Bo5 like an iid model (×1.25) or like a day-noise model (×1.10–1.13)? |
| Mechanism | **Pure iid:** Bo5 log-odds are 1.25 times Bo3's at the same point-level gap (1.27 at Δ = 0.3). **With Stage 3's day noise:** 1.13, or 1.10 if serve and return days correlate 0.5. `ratings_iid` carries the full 1.25 in its Bo5 values. If the day-noise model holds, the fitted slope of results on `ratings_iid` should be about 0.88–0.90 times as large at Bo5 as at Bo3. This one measurement fixes c², the factor that bounds MAT-C3, C4, C5, M1 and S3. |
| Why the price might miss it | The thinking study's separate Slam and Bo5 slopes on the odds added ≈0.04 mLL, so the price's own Bo5 calibration is close. This check concerns the model's composed inputs and the damping. |
| Type | M × S (diagnostic) |
| Formula | Logistic slopes of the result on ratings_iid, by best_of (men, 2013–2021). |
| Data | Model frame; results (EDA round only). |
| Why the model cannot already do it | n/a |
| Expected effect | A ratio of ≈0.88–0.90 confirms the damping and closes the leverage cluster. A ratio near 1.0 raises the bounds by up to 1/c⁴ ≈ 2–4 and moves MAT-M1 up. |
| Kill test | n/a: it decides the others. |

### MAT-M6 · Adjustment × lopsidedness (kill by calculation)

| Field | Content |
|---|---|
| ID, name | MAT-M6, a point-level adjustment moves lopsided matches more |
| Mechanism | logit P is convex in the point-level gap. **Computed:** logit P/(β_LΔ) is 1.09 (Bo3) and 1.14 (Bo5) at Δ = 0.5 logit, and 1.32 and 1.48 at Δ = 1. The marginal leverage at Δ = 0.5 is 1.27 times (Bo3) and 1.41 times (Bo5) its value at 0. |
| Why the price might miss it | n/a (model-side). |
| Type | M |
| Formula | \|z_mkt\| × adjustment (symmetric × antisymmetric = antisymmetric) |
| Data | Model frame |
| Why the model cannot already do it | It can: odds_logit is an input. |
| Expected effect | It only rescales the model's adjustment, worth ≈ κ² mLL with κ ≤ 0.3, and only on the ≈6% of men's matches with \|Δ\| > 0.5: < 0.01 mLL. |
| Kill test | Killed by calculation. |

## What TabPFN could learn by itself, and what it cannot

| Interaction class | Inputs present? | Learnable from ≈40,000 rows? | Note |
|---|---|---|---|
| Curvature of the odds calibration (1-D) | yes | yes | the margin-loading shape (MAT-M4) |
| Price or a difference × context (surface, level, best of, round, tour, indoor) | yes | in principle | Modulations of the adjustment are worth ≈ κ² mLL (< 0.05), and TabPFN rightly ignores them. A price × context modulation of a few percent is worth 79κ², learnable only if ≳0.2 mLL. |
| A function of two differences (form against IOS; ratings_iid against the odds) | yes | yes | |
| Convexity in a difference (Δ³) | yes | yes | |
| Pair sums: serve dominance ΣY, prominence ΣT, volatility ΣV, uncertainty Σv | no | no | Information absent. `ratings_iid` holds ΣY only inside one composed number. |
| Within-player curvature (O_A² − O_B²) | only prod_s | no | prod_s carries R² 0.01–0.12 of it |
| Per-player reliability r_i and evidence n_i | partial proxies (surf_season, surf_layoff pairs) | no | MAT-U1, U2 |
| Per-player hazards and variances | no | no | MAT-W2, S4 |
| Bookmaker margin and dispersion; deciding-set rule | no | no | negligible as interactions (MAT-M4, U5, C6) |

**Inferred.** The interactions TabPFN can reach are the ones this file bounds as small. The ones with room are absent from its inputs. So what the cone builds should be new per-player columns (U1, U2, S4, W2, W1, C1), not products of existing columns. Exactly symmetric training (both orientations, MAT-S1) would help TabPFN use any new symmetric column.

## Appendix: the exact calculations

All numbers are from `markov_composition.py` (`results.json` and the CSVs). Seasons up to 2021 only.

### A1. The iid model, checked

* **The model.** Game, tiebreak (7 and 10 points), set (tiebreak at 6-6 or 12-12, or advantage) and match (Bo3, Bo5, any deciding-set rule).
* **Checks.**
  * Against `stage2_iid.py`: largest gap 3.3e-16 over 400 random pairs, all rules and formats. Textbook hold at p = 0.60: 0.73573.
  * Antisymmetry P(a, b) + P(b, a) = 1 to 8.9e-16. Set probability independent of the first server to 4.4e-16.
  * **New:** invariance under exchanging serve and return, P(p_A, p_B) = P(1 − p_B, 1 − p_A), to 1.7e-14 for every set rule. In (m, d) coordinates, P(m, d) = P(1 − m, d), so ∂P/∂m = 0 at m = ½.

### A2. ∂P/∂(p_A + p_B) at fixed d = p_A − p_B

**How to read the tables.**
* m = (p_A + p_B)/2. β_P = ∂P/∂d at d = 0, per unit of d.
* "Sets reaching 6-6" is at d = 0.
* ∂P/∂s is per unit of s = p_A + p_B. Multiply by 2 for the change in percentage points when each player's serve-point probability rises by one point.
* The iid model knows no tour: women's Bo3 is the same function as men's, read at a lower m.
* Realistic pair means, 5–95% of 2013–2021 training rows: **men 0.586–0.698** (median 0.633), **women 0.524–0.609** (median 0.564). |d| has median 0.038 (men) and 0.036 (women), and 90th percentile 0.099 and 0.092.

**Best of 3 (both tours):**

| m | Within the 5–95% range of | sets reaching 6-6 | β_P | P at d = 0.04 | ∂P/∂s, d = 0.02 | d = 0.04 | d = 0.06 | d = 0.10 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | | 0.123 | 5.367 | 0.705 | 0.000 | 0.000 | 0.000 | 0.000 |
| 0.53 | women | 0.127 | 5.348 | 0.704 | −0.012 | −0.022 | −0.028 | −0.026 |
| 0.56 | women | 0.141 | 5.290 | 0.702 | −0.024 | −0.044 | −0.055 | −0.052 |
| 0.59 | men and women | 0.163 | 5.198 | 0.699 | −0.035 | −0.063 | −0.080 | −0.077 |
| 0.62 | men | 0.198 | 5.074 | 0.694 | −0.044 | −0.080 | −0.102 | −0.101 |
| 0.65 | men | 0.248 | 4.927 | 0.689 | −0.050 | −0.092 | −0.118 | −0.120 |
| 0.68 | men | 0.319 | 4.765 | 0.684 | −0.054 | −0.099 | −0.129 | −0.134 |
| 0.71 | (men's top 5%) | 0.416 | 4.594 | 0.677 | −0.056 | −0.103 | −0.135 | −0.145 |
| 0.74 | | 0.533 | 4.423 | 0.671 | −0.055 | −0.102 | −0.134 | −0.148 |

**Best of 5 (men's Slams; a 7-point final-set tiebreak):**

| m | β_P | P at d = 0.04 | ∂P/∂s, d = 0.02 | d = 0.04 | d = 0.06 | d = 0.10 |
|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 6.709 | 0.749 | 0.000 | 0.000 | 0.000 | 0.000 |
| 0.56 | 6.613 | 0.746 | −0.030 | −0.051 | −0.058 | −0.040 |
| 0.59 | 6.497 | 0.742 | −0.043 | −0.073 | −0.084 | −0.060 |
| 0.62 | 6.343 | 0.737 | −0.054 | −0.093 | −0.108 | −0.080 |
| 0.65 | 6.159 | 0.731 | −0.062 | −0.107 | −0.126 | −0.097 |
| 0.68 | 5.956 | 0.725 | −0.067 | −0.116 | −0.139 | −0.112 |
| 0.71 | 5.743 | 0.718 | −0.069 | −0.121 | −0.147 | −0.125 |
| 0.74 | 5.528 | 0.710 | −0.068 | −0.120 | −0.148 | −0.131 |

* With the 10-point final-set tiebreak (Slams from 2022) every entry moves by ≤0.006 in β_P and ≤0.01 in ∂P/∂s (`grid_prob_scale.csv`).
* **Reading.**
  * At fixed d, higher joint serve dominance always lowers the favourite's chance.
  * Across the men's realistic range (0.586–0.698) the leverage β_P falls about 10% (Bo3); across the women's (0.524–0.609) about 4% (interpolated in the table).
  * At d = 0.10 in Bo5 the derivative shrinks again, because P is near 0.94.

### A3. The logit scale

| Case | Best of | p̄ | β_L | (1/β)dβ/dμ per logit | per 0.1 logit | logit P/(β_LΔ) at Δ = 0.5 | at Δ = 1 | Bo5/Bo3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| men clay | 3 | 0.604 | 4.92 | −0.40 | −4.0% | 1.097 | 1.342 | |
| men clay | 5 | 0.604 | 6.15 | −0.40 | −4.0% | 1.153 | 1.506 | 1.250 |
| men hard | 3 | 0.628 | 4.70 | −0.48 | −4.8% | 1.090 | 1.322 | |
| men hard | 5 | 0.628 | 5.88 | −0.48 | −4.8% | 1.141 | 1.478 | 1.250 |
| men grass | 3 | 0.655 | 4.43 | −0.55 | −5.5% | 1.081 | 1.298 | |
| men grass | 5 | 0.655 | 5.53 | −0.55 | −5.5% | 1.127 | 1.443 | 1.250 |
| women clay | 3 | 0.550 | 5.26 | −0.20 | −2.0% | 1.109 | 1.374 | |
| women hard | 3 | 0.558 | 5.22 | −0.23 | −2.3% | 1.108 | 1.371 | |
| women grass | 3 | 0.587 | 5.05 | −0.34 | −3.4% | 1.102 | 1.354 | |

* The composition's quadratic coefficient is h = dβ_L/dμ: −2.25 (men hard Bo3), −1.20 (women hard).
* The ratio of the women's to the men's relative slope follows μ, as the exchange invariance predicts: β_L is even in μ, so its relative slope ∝ μ near 0.

### A4. What the A − B frame hides: the pair's serve dominance (2013–2021 training rows, features only)

| | Men | Women |
|---|---:|---:|
| Matches | 19,331 | 20,587 |
| SD of the gap Δ (logit) | 0.266 | 0.232 |
| SD of the pair's serve dominance ΣY/2 | **0.131** | **0.097** |
| SD of the surface part μ_surface | 0.067 | 0.043 |
| corr(Δ, ΣY/2) | −0.004 | −0.013 |
| Per player: SD of O, of D; corr(O, D) | 0.154, 0.133; 0.18 | 0.128, 0.108; 0.34 |
| Per player: SD of style Y = O − D; of total T = O + D | 0.185; 0.222 | 0.137; 0.193 |
| RMS of the iid log-odds composed from the IOS | 1.47 | 1.30 |
| SD of the price's log-odds | 1.09 | 0.95 |
| Ratio, against the day-noise c (A5) | 0.74 against 0.70–0.77 | 0.73 against 0.69–0.76 |
| RMS of what the pair's dominance adds to the iid log-odds | 0.112 (7.6%) | 0.045 (3.5%) |
| Leverage modulation κ, logit scale: RMS (5–95%) | 7.1% (−15.6% to +5.6%) | 2.8% (−5.9% to +2.2%) |
| κ on the probability scale: RMS | 3.2% | 1.3% |
| Bound if the price ignores it, undamped (logit; probability scale) | 0.40; 0.08 mLL | 0.05; 0.01 mLL |
| Bound after day-noise damping (c² 0.47–0.75) | 0.10–0.22 mLL | 0.01–0.03 mLL |

Stage 3's method-of-moments constants (2013–2018) give the true between-player SD of opponent-adjusted serve points won as 0.189 logit (men) and 0.153 (women), and of return points won 0.149 and 0.124. The IOS spreads above are shrunk estimates, slightly smaller, as they should be.

### A5. Day-to-day noise and its damping

The noise comes from Stage 3's over-dispersion of opponent-adjusted rates (2013–2018):
* serve points won 1.65 (men) and 1.59 (women) times binomial, over 73.5 and 70.9 serve points per match;
* return points won 1.66 and 1.61 times binomial.

So σ_serve² + σ_return² ≈ 0.0375 (men) and 0.0345 (women) logit² per player and match. This is an upper bound: it includes conditions and adjustment error.

| Case | var of the gap's day noise | SD of the match-logit noise (Bo3) | c² Bo3 | c² Bo5 | Exact damping of a leverage change (Bo3) |
|---|---:|---:|---:|---:|---:|
| Men, serve and return days independent | 0.075 | 1.31 | 0.595 | 0.486 | 0.592 |
| Men, serve and return days correlate 0.5 | 0.113 | 1.61 | 0.495 | 0.387 | 0.492 |
| Men, conditions take half the excess | 0.038 | 0.93 | 0.746 | 0.654 | 0.743 |
| Women, independent | 0.069 | 1.37 | 0.574 | | 0.573 |
| Women, correlate 0.5 | 0.103 | 1.68 | 0.473 | | 0.473 |
| Women, half conditions | 0.034 | 0.97 | 0.729 | | 0.727 |

* c² is exact by 48-node Gauss–Hermite; the probit approximation 1/(1 + πσ²/8) agrees to 0.003.
* **Men's Bo5/Bo3 log-odds ratio:** 1.251 (Δ = 0.05) and 1.274 (Δ = 0.3) without noise; 1.129 and 1.136 with independent days; 1.104 and 1.109 with correlated days.
* **Derived:** d ln z/d ln β = c² and d ln z/d ln V = −½(1 − c²).

### A6. The profile composed into serve-point probabilities (first serves in, first- and second-serve points won)

| | Men | Women |
|---|---:|---:|
| RMS of the composed serve-point gap Δp | 0.0588 | 0.0504 |
| Its linearisation error in the A − B inputs | 0.0043 | 0.0041 |
| Its part that needs pair sums | 0.0042 | 0.0040 |
| RMS of the pair's mean serve probability minus the surface mean | 0.031 | 0.023 |
| RMS of the composed match log-odds | 1.411 | 1.142 |
| Hidden from the A − B frame (exact minus sum-free) | 0.139 | 0.103 |
| … of which the pair's overall dominance (leverage) | 0.043 | 0.017 |
| … of which the composition of Δp | 0.106 | 0.094 |
| corr of the composed gap with the surface IOS of serve points won | 0.987 | 0.979 |

The two parts are RMS values of per-match pieces that correlate (0.70 men, 0.41 women), so they do not add in quadrature to the total.

**Bound in the extreme case** where the price ignores composition entirely: damp the leverage part by c² (a change of leverage) and the Δp part by c (a change of the gap itself), keeping their cross term. That gives 1.03 mLL for men and 0.61 for women with independent days; the range over the A5 cases is 0.82–1.35 (men) and 0.49–0.78 (women).

**Per statistic: the non-linear share of the probability-scale edge, and how much of it prod_s carries.**

| Statistic | Mean rate (men, women) | Non-linear share of RMS (men, women) | R² on prod_s alone (men, women) | R² on prod_s + squares (men, women) | corr(prod, squares) (men, women) |
|---|---|---|---|---|---|
| Aces | 0.069, 0.035 | 32%, 37% | 0.009, 0.076 | 0.91, 0.85 | −0.64, −0.46 |
| Double faults | 0.041, 0.053 | 21%, 22% | 0.061, 0.116 | 0.98, 0.97 | −0.21, −0.07 |
| Holds | 0.768, 0.639 | 18%, 9% | 0.013, 0.019 | 0.99, 0.89 | −0.92, −0.81 |
| First-serve points won | 0.703, 0.625 | 9%, 5% | 0.008, 0.000 | 0.99, 0.96 | −0.90, −0.79 |
| First serves in | 0.609, 0.621 | 3%, 8% | 0.059, 0.025 | 0.95, 0.98 | −0.12, −0.02 |
| Second-serve points won | 0.501, 0.451 | 1%, 1% | 0.087, 0.104 | 0.29, 0.71 | −0.87, −0.68 |

The identity x_A² − x_B² = squares + 2·prod holds to 2e-15 on every row.

### A7. Uncertainty, volatility, hazard: the bounds

**Weights of the 2013–2021 price** (odds only):

| | Men | Women |
|---|---:|---:|
| SD of the log-odds z | 1.09 | 0.95 |
| E[p(1 − p)] | 0.201 | 0.210 |
| E[p(1 − p)z²] | 0.157 | 0.136 |
| E[2 cosh z] | 3.63 | 3.13 |
| Share of matches with \|z\| > 1.5 | 16.7% | 11.4% |
| Share with \|z\| > 2.2 | 5.0% | 2.2% |

**Posterior variance of the gap** (Stage 3 ratings):
* median 0.0135 (men) and 0.0116 (women); p10–p90 0.011–0.018 (men) and 0.009–0.018 (women); p99 0.025 and 0.031;
* slope modulation RMS 0.7% and 1.2% with day noise (1.2% and 1.9% without);
* bound 0.004–0.025 mLL.

**Volatility** (MAT-S4). The bound in mLL when the price ignores the pair's day variance, by that variance's coefficient of variation (CV):

| Case | CV 0.1 | CV 0.2 | CV 0.3 | CV 0.5 |
|---|---:|---:|---:|---:|
| Men, independent days | 0.03 | 0.13 | 0.29 | 0.80 |
| Men, correlated days | 0.05 | 0.20 | 0.45 | 1.25 |
| Men, half conditions | 0.01 | 0.05 | 0.11 | 0.32 |
| Women, independent / correlated / half conditions (at CV 0.3) | | | 0.28 / 0.43 / 0.11 | |

**Retirement hazard** (MAT-W2), at σ_h = 0.5, 1 and 2 pp: men 0.05, 0.18, 0.73 mLL; women 0.04, 0.16, 0.63.

### A8. De-vigging (2013–2021, odds only)

The slope needed on a proportionally de-vigged price, by margin-loading rule:

| Rule | Overround 3%, \|z\| = 1 / 2 | 5.8% (the median), \|z\| = 1 / 2 | 10%, \|z\| = 1 / 2 |
|---|---:|---:|---:|
| Power | 1.053 / 1.084 | 1.105 / 1.165 | 1.190 / 1.295 |
| Shin (= an equal margin per side) | 1.035 / 1.054 | 1.068 / 1.102 | 1.117 / 1.173 |

**The overround of the average close:**

| | Mean | SD | 5% | 50% | 95% |
|---|---:|---:|---:|---:|---:|
| Men | 5.69% | 0.55 pp | 4.80% | 5.75% | 6.45% |
| Women | 5.71% | 0.52 pp | 4.87% | 5.75% | 6.48% |

**Average against Pinnacle:**
* SD of the log-odds gap: 0.114 (men), 0.089 (women);
* slope of Pinnacle's log-odds on the average's: 1.071 and 1.059.

### A9. The value formula and the threshold

**The formula.** A correct log-odds term τ that the model lacks is worth about 1000·½·E[p(1 − p)τ²] mLL. That is the second-order expansion of the expected log loss at the truth.
* **Rescaling the price:** τ = κz, so the value is 78.6κ² (men) or 68.2κ² (women).
* **Rescaling the adjustment:** with an RMS of ≈0.1 logit, the value is ≈1.0κ².

**The threshold** (inferred). About 0.20 mLL for 80% power on 2013–2021, and about 0.34 on 2022–2024. This scales the surface-IOS study's 0.26 on 23,819 matches by √n.

**Redundancies by construction.** These are not interactions:
* **Serve points:** spw = fi·fw + (1 − fi)·sw.
* **Breaks:** per match, 1 − hold = (break points faced per game)·(1 − break points saved), since breaks = break points faced − break points saved. So hold, bp_faced_pg and bp_saved repeat one quantity on the log scale of 1 − hold, with different noise. An "interaction" between them is mostly a scale artefact.
* **Points won:** total points won is the points-weighted mean of serve and return points won.
* **Mirrors:** within a match, each return statistic is the opponent's serve statistic turned over.

**A data gap worth noting.** A totals (over/under games) line is the market's own reading of ΣY. Only match odds are on file.

## Top 8, ranked

1. **MAT-U1.** Re-anchor the two-week form on each player's long-memory level, with per-player reliability. It fixes a mis-specified prior in a heavily used group, with information TabPFN cannot reach.
2. **MAT-S4.** Per-player day-to-day volatility: the pair's variance flattens the odds by ½(1 − c²) per unit of relative variance. If unpriced, worth 0.28–0.45 mLL at a pair CV of 0.3 and up to 1.25 at 0.5. Gate it on the trait's reliability first, a feature-only check.
3. **MAT-W2.** Retirement hazard entering as h_B/p − h_A/(1 − p). New information with an exact odds-level weighting: 0.16–0.73 mLL at σ_h = 1–2 pp, with differing settlement rules as the market-orthogonal route.
4. **MAT-C1.** The long-memory surface profile composed into a match log-odds. One column carries the ≈10% of the profile's composition that the A − B frame cannot express, in TabPFN's most-used group.
5. **MAT-U2.** "Unknown is not average": the box-score evidence behind each player's surface IOS, as a pair or as a weight.
6. **MAT-W1.** Within-player squares completing prod_s, or probability-scale edges for aces, double faults and holds. prod_s carries only R² 0.01–0.12 of the curvature.
7. **MAT-M2.** Context-dependent recalibration of the final forecast's adjustment (evidence, size, format). Cheap, and calibration has been the largest single lever.
8. **MAT-M1 with C3**, after the MAT-M5 damping check. The price × the pair's serve dominance, the canonical composition interaction, bounded at ≤0.22 mLL (men) after damping; one 1-df test.
