# Feature interactions, round 2: rebuttals and additions, mathematics lens

6 October 2026 · Brainstormer "mathematics" (Opus) · Research evidence, not a decision.

**Read:**
* [plan.md](../plan.md) and the [master list](../master_list.md);
* the mathematical audit: summary, families 01–03, 06–09 and 15, and [blocks](../round1/math_audit/withdrawn_and_blocks.md);
* the [feasibility audit](../round1/feasibility.md);
* the [literature](../round0/literature.md);
* the inventory's data-defect list (§6).

**No results.**
* Nothing was related to `a_won`, and no price was set against outcomes.
* Seasons ≤ 2021 throughout, except one feature-only spread read up to 2024.
* The matches' own serve-point counts were read as a *statistic target*, the quantity Stage 3's constants and the IOS fits are built from. This is listed for the look ledger's discretion.

**Files.**
* Scripts, in `src/eda/feature_interactions/round2/mathematics/`: `day_noise_precheck.py`, `novelty_r2.py`, `measurement_checks.py`.
* Outputs, in `data/studies/feature_interactions/round2/mathematics/`: `day_noise_precheck.json`, `novelty_r2.json`, `measurement_checks.json`.

**Keys.**
* "Gap residual" e_A − e_B: the logit of each player's realised serve-point rate minus its pre-match surface-IOS expectation. A's minus B's, which cancels shared conditions.
* "Binomial part": simulated exactly by redrawing the counts at the expected rates.
* mLL values are gains over the price, higher is better.

## Numbers computed for this round (result-free)

| # | Quantity | Men | Women |
|---|---|---|---|
| N1 | Gap-residual variance beyond binomial (logit²) | 0.167 (Bo3 0.176, Bo5 0.131) | 0.195 |
| N2 | Persistent rating error, from the lag covariance of a player's residuals (pair-level) | 0.013 | 0.011 |
| N3 | Idiosyncratic per-match noise on the gap, N1 − N2 | 0.154 | 0.183 |
| N4 | Excess cov(e_A, e_B): serve and return "days" move together | −0.032 | −0.039 |
| N5 | Two-level split (Bo3 against Bo5): match-constant / per set | 0.046 / 0.28 | – |
| N6 | Implied true Bo5/Bo3 log-odds ratio (exact chain, two-level noise) | 1.197 | – |
| N7 | Damping of a serve-dominance leverage change (Bo3 / Bo5) | 0.39 / 0.35 | – |
| N8 | B5 precheck, simple estimator: de-noised pair CV; split-half reliability | 0.20; 0.23 | 0.24; 0.33 |
| N9 | B5 precheck, first differences (removes rating drift): pair CV; reliability | 0.19; 0.15 | 0.18; 0.16 |
| N10 | Stable pair-specific variance of the gap: same-pair minus player-level covariance | 0.0045 ± 0.0033 | 0.0002 ± 0.0037 |
| N11 | SD of the pair's serve dominance by season | 0.138 (2015) → 0.107 (2024) | 0.094–0.101, flat |
| N12 | Next-match serve points, 2018–2021, log loss per point (lower is better): serve-point IOS; composed components; best blend chosen on 2013–2017 | 0.65289; 0.65296; 0.65289 | 0.68199; 0.68213; 0.68201 |
| N13 | R² of the pair's serve dominance on the 58 inputs: OLS; OLS + \|x\|; boosting, 3-fold CV | 0.004; 0.24; **0.56** | −0.009; 0.10; **0.47** |
| N14 | I-042: share of the hazard term's value left when Δh is a free linear control | 32% | 24% |
| N15 | z_spw (R4): R² on the 58; residual SD (log-odds); corr with ratings_iid | 0.971; 0.25; 0.91 | 0.974; 0.21; 0.95 |
| N16 | Count-identity violations, 7 inequalities, 354,192 box scores 2013–2024 | 0 | 0 |
| N17 | Events (≥ 40 player-matches) whose first-serve share is shifted > +3 pp at z > 4 | 6.9% of 4,117 (both tours) | |

## 1. Rebuttals (at most 150 words each)

### R1 · I-042: do not control the hazard difference

The label identity makes τ = −Δh(1 + cosh z) − Σh·sinh z a single structural column. Δh is not an input and no other hypothesis tests it, so a free linear Δh control removes the column's own leading term.

**Computed** on the 2013–2021 prices, weighted by p(1 − p) (N14): with Δh free, only 32% (men) and 24% (women) of ½σ_h²E[2 cosh z] remains. At σ_h = 1 pp that is 0.057 instead of 0.18 mLL for men, and 0.037 instead of 0.16 for women: below the weight-2 MDE (0.12) up to σ_h ≈ 1.5 pp.

**Fix:**
* primary: τ alone (b = the share of the risk the close omits), with the M-set and Std;
* secondary: the shape test, with Δh free.

**Estimator** (finding 2): fix it now as a beta-binomial empirical-Bayes rate, K from moments of the 2010–2018 counts. Nothing is then chosen on a target.

### R2 · I-007: the substitute measures the price, not the truth

Finding 5's substitute, the close's Bo5/Bo3 ratio of 1.19–1.27, says what the market does. I-007 asked what is true, and a result-free version exists.

**Computed (N1–N6):**
* For men, the gap residual's excess is 0.176 (Bo3) and 0.131 (Bo5).
* Persistent rating error is only 0.013.
* The rest splits into a match-constant part of 0.046 and a per-set part of 0.28.
* Only the match-constant part compresses Bo5 against Bo3. Through the exact chain, the implied true ratio is **1.197**, inside the price's range.

So the price's format leverage matches the decomposed truth. The mispricing I-006 tests (not mine) is expected ≈ 0: |κ| ≲ 3% on Bo5 rows, ≈ 0.01 mLL. Set dependence [R13] could push the truth up, so two-sided remains right.

I-007's post-M1 row is now redundant. A sharper result-free check: the within-match set-to-set covariance of per-set residuals, from the point-sequence table.

### R3 · I-001 (my idea): a lower weight, in a block

Two result-free facts put I-001 below the G2 line.

1. **Damping.** Under the measured two-level noise, a leverage change reaches the pre-match odds multiplied by 0.39 (Bo3) and 0.35 (Bo5) (N7), not by the audit's 0.5–0.75. The within-cell bound (0.33 mLL, men, undamped) becomes ≈ 0.05 for men and ≈ 0.03 pooled, even if the price ignores dominance entirely.
2. **Decline of specialization** (literature §1): the men's spread of pair dominance fell 22% over 2015–2024 (N11), so test-season value is ≈ 0.6× discovery. Women's: flat.

**Proposal:** weight 0.5 in a block B-LEVER, "the price's leverage by match structure", Wald 3 df. Members:
* I-001 (+);
* I-006's format slope (±);
* the surface-level slope κ_surf·η (+): the part I-001's cell controls remove, RMS κ 3.2% for men, ≤ 0.08 mLL undamped (computed).

**Fix:** compute κ at full match dominance, adding I-072's event intercept once built (Ingram: ±0.15 logit).

### R4 · I-008 (my idea): compose the serve-point IOS, not its three components

The components forecast serve points worse than the serve-point IOS they decompose (N12: statistic target, 2018–2021, blend chosen on 2013–2017).
* Composed components lose 0.07 (men) and 0.14 (women) milli per serve point against the serve-point IOS.
* The best blend gains nothing.

So part of z_C1's residual on the 58 (0.21/0.10) is the components' extra noise.

**Fix:** the primary becomes z_spw = logit P_iid(expit(μ + O^spw_A − D^spw_B), expit(μ + O^spw_B − D^spw_A); format), from `srf_O_eff_spw`/`srf_D_eff_spw`. The model holds neither.

**Computed (N15):**
* R² on the 58 is 0.971 (men) and 0.974 (women), with residual SD 0.25 and 0.21 log-odds, more than z_C1 leaves.
* Its correlation with ratings_iid is 0.91 and 0.95.

z_C1 becomes a sensitivity, and the weight stays 2. This is also the cleanest carrier of I-001's leverage, since the pair dominance enters exactly.

### R5 · B5 (I-028, I-029; mine): the precheck, run

**Computed (N8–N9)** on per-player gap residuals, 2013–2021: 140 men and 134 women with ≥ 100 matches, halves of ≥ 50.
* **Simple estimator:** de-noised pair CV 0.20 (men) and 0.24 (women); split-half reliability 0.23 and 0.33.
* **First differences,** which stop risers and decliners passing for volatile: CV 0.19 and 0.18; reliability 0.15 and 0.16.

By the rule fixed in `withdrawn_and_blocks.md`, I-029's between-match column drops. The women's simple-estimator pass is inflated by drift.

**Accept:** drop I-029. B5 survives only if I-028's within-match column passes its own reliability gate, which is not computed here.

For the record: the measured c² is lower (0.42), so each unit of CV moves the odds more (d ln z/d ln V = −0.29). But at reliability ≈ 0.3 the usable value is ≈ 0.1 mLL at most.

### R6 · Cross-cutting findings 1–3: correct, with notes

* **Finding 1 is right.** R1 is its W × M analogue: there too the control equals the hypothesis's leading term.
* **Finding 2 is right.** Add R1's fixed estimator. For I-010's V, use the measured 0.154 (men) and 0.183 (women), or N5's split, not Stage 3's over-dispersion. That bound assumed independent serve and return days, and N4 shows they move together.
* **Finding 3 is right,** and it should govern the feasibility deferrals too. I-008 (R² 0.980), I-009, I-012 and I-015 were deferred on R² alone. The fix ("test the remainder after a result-free projection") is equivalent by Frisch–Waugh and lifts them.
* **Extension.** For S and C columns, linear R² overstates novelty to a nonlinear learner (K2): boosting recovers 56% and 47% of the pair's dominance from the 58 inputs (N13).

### Note for a block not mine (not a rebuttal)

B4's target, the stable pair-specific deviation, is 0.0045 ± 0.0033 for men and ≈ 0 for women (N10). So B4 is men-only in substance. With 1–3 past meetings an estimator recovers 2–5% of it: ≈ 0.05 mLL, consistent with the audit.

## 2. Literature addition (one; the rest of the literature maps onto existing rows)

**How the rest maps:**
* serve level × difference: I-001, I-002 (R3);
* Lahvička's low-rank and high-profile slopes: I-036, I-084;
* volatility: B5;
* load: family 11; home: B-HOME; event speed: B-VENUE; handedness: I-021; height: I-023;
* clutch and momentum: B-CLUTCH and B-OVERREACT;
* low-level serve composition: I-008;
* latent "blade-chest" matchups: an estimator variant of B4's quantity (N10 bounds it);
* grass underdogs: the surface slope inside B-LEVER (R3).

### MAT-L1 · The later-round price slope: Lahvička's third slope

| Field | Content |
|---|---|
| ID, name | MAT-L1, the later-round price slope, completing the three-slope fit |
| Mechanism | Lahvička [R28] (Bet365, 44,871 matches, proportional de-vig) fitted three slope modifiers *jointly*: LowerRank +0.092, LaterRound +0.036, HighProfile +0.070, on a base of 1.005. I-036 and I-084 carry the first and third. The three correlate: later rounds are more prominent and less often low-ranked, so testing two of three invites an omitted-variable sign error in both. The source reads it as insiders and news concentrating late in events |
| Why the price might miss it | A shading pattern of soft books. The average close includes them, so part may survive the average's de-vig |
| Type | M × S |
| Formula | s = round depth (in_round standardised within tour), d = η (z in the price version). s is symmetric, so s·η is antisymmetric. Fit jointly with I-036 and I-084 |
| Data | Model frame: in_round, odds. Schedule only: safe |
| Why the model cannot already do it | TabPFN has round and odds and could form the product, but its adjustment uses no context (thinking report). Computed: R² of depth·z on the 58 is 0.19 (men) and 0.09 (women) |
| Expected effect (S6) | Sign +: steeper true odds late in events. The source's κ ≈ +0.036 on about half of matches gives RMS κ ≈ 0.018 and ≈ 0.025 mLL pooled, if it holds at the average close. Coverage 100%. **Main effect:** none (s symmetric). **Deployment:** nudge. **2025–26 seen:** no (data 2002–2013) |
| Kill test | Joint fit with I-036 and I-084: the CI on b includes 0 → kill. Proposed home: B-INFO's joint fit, at weight 0.5 |

## 3. Contrarian ideas (critique S5)

### MAT-K1 · The per-statistic profile adds nothing at the point level to one serve-point rating

*Contradicts the brief:* "the edge lives in per-statistic offence/defence profiles and point-level data".

| Field | Content |
|---|---|
| ID, name | MAT-K1, the per-statistic profile is a noisier serve-point rating |
| Mechanism | Under iid, who wins depends only on each side's serve-point probability, and the profile (first serves in, first- and second-serve points won, aces, double faults, holds) decomposes the same points. **Computed (N12):** composed, the components forecast the next match's serve points *worse* than the serve-point IOS: −0.07 (men) and −0.14 (women) milli per point, 2018–2021. A blend chosen on 2013–2017 adds nothing. **Literature agrees:** component point models trail Elo (Barnett–Clarke 0.649 against Elo 0.586 [R39]; Ingram 0.592 against 0.586 [R5]). So any edge the profile holds against the close must come through non-iid channels (style, curvature, matchups), or it is noise TabPFN fits |
| Why the price might miss it | Contrarian: it does not. The profile's point-level content is serve-point strength, and that is priced |
| Type | C (representation) |
| Formula | A TabPFN arm, "spw-only": the 21 IOS profile inputs (iosO_s, iosD_s, prod_s) replaced by ΔO^spw and ΔD^spw (the surface IOS of serve points won) plus z_spw (R4). All antisymmetric. For the screen, the remainder z_C1 − z_spw is tested two-sided, b = 0 predicted |
| Data | surface_features spw and components. Leak-proof |
| Why the model cannot already do it | The serve-point IOS is not among the 58 inputs. The model has its components and Stage 3's ratings_iid |
| Expected effect (S6) | **If K1 holds,** the arm ties the current best (\|Δ\| < 0.1 mLL) with 18 fewer inputs. **If the per-statistic detail carries the edge,** the arm loses up to the IOS group's share of TabPFN's adjustment (≈ 0.5–1 mLL, men). Coverage 100%. **Novel variance:** z_spw R² 0.971/0.974, residual 0.25/0.21. **Deployment:** TabPFN columns. **2025–26 seen:** no |
| Kill test | **Result-free, passed:** the components would have to beat the serve-point IOS on next-match serve points by ≥ +0.1 milli per point (they lose). **After M1:** if the spw-only arm loses by more than 0.1 mLL on 2016–2024, K1 dies and the owner's thesis stands for TabPFN |

### MAT-K2 · The A − B frame already sees half of the pair's levels

*Contradicts the brief:* "the model never sees either player's level separately, so it cannot form anything that depends on A's and B's values other than through their difference".

| Field | Content |
|---|---|
| ID, name | MAT-K2, levels leak through composed and product inputs |
| Mechanism | `ratings_iid` and `ios_points_short` are non-linear in both players' levels, and prod_s are cross-products. Even functions of them (absolute values, ratios to linear differences) carry sums. **Computed (N13):** 3-fold CV gradient boosting recovers R² 0.56 (men) and 0.47 (women) of the pair's serve dominance ΣY/2 from the 58 inputs. Linear OLS recovers 0.004 and −0.009; OLS with \|x\| terms 0.24 and 0.10 |
| Why the price might miss it | n/a: this is a claim about novelty, not the market |
| Type | S (novelty correction) |
| Formula | s̃ = s − ĝ(x₅₈), with ĝ a cross-fitted gradient-boosting regression on the 58 inputs (features only), symmetrised as ½[ĝ(x) + ĝ(flip x)] so s̃ stays symmetric. Each S candidate is tested as s̃·η beside s·η |
| Data | Model frame and surface features, 2013–2021. Result-free |
| Why the model cannot already do it | Contrarian: it partly can. Whether TabPFN does is what the screen's offset η decides |
| Expected effect (S6) | No column of its own. **If TabPFN uses the recoverable half,** S2's levels arm and the S-type bounds roughly halve. **If it does not,** b(s·η) ≈ b(s̃·η): context carries nothing, so this is plausible. Coverage 100%. **2025–26 seen:** no |
| Kill test | **Result-free, survived:** the brief's claim would hold at a boosting CV R² < 0.2 (it is 0.56/0.47). **In the screen:** report b for s·η and s̃·η side by side for I-001, I-036, I-084 and S2's sums. G2 and G5 should judge S novelty by flexible, not linear, R² |

## 4. Measurement reliability (critique C7)

### MAT-R1 · Event-level recording faults: a residual detector and evidence weights

| Field | Content |
|---|---|
| ID, name | MAT-R1, a recording-fault detector per event × statistic, with evidence weights in the histories |
| Mechanism | **Systematic miscoding passes every count identity.** Examples are second serves recorded as first, or a source's own ace and double-fault counts. Computed: 0 violations of 7 identities in 354,192 box scores, 2013–2024 (N16). Such miscoding shifts a whole event instead. **Detector:** each event's mean residual of a statistic against the players' own means, with its z. **Computed** for first serves in, 6.9% of 4,117 events exceed +3 pp at z > 4 (N17). Flags include: <br>• Roland Garros qualifying 2022, men +6.9 pp (z 10.2), the known fault; <br>• the same event for women, +6.5 pp (z 10.0), which the inventory does not list; <br>• the Bratislava Challenger, shifted +2.5 to +7.9 pp in every year 2013–2023 and flagged in most (a venue regularity: convention or conditions, not yet separated); <br>• the Paris Olympics 2024 (+8.2 pp). <br>Flagged records enter IOS and form at full weight, and a first/second-serve swap corrupts first_in, first_won and second_won together |
| Why the price might miss it | It does not: the price measures the players; our inputs mis-measure them. The fix is model-side |
| Type | U |
| Formula | **Weight:** w_e,s = 1/(1 + (z_e,s/4)²) (or 0 when flagged) in the IOS and form rebuild. **Per player:** q_i,s = the share of evidence weight from flagged events. **Column:** the rebuilt difference, or Δ_s·(1 − q̄_s). Weights are per player, so the swap holds |
| Data | Stage 0 box scores and source; the player's own history. The detector reads only an event's own box scores, so it is available from lf + 1. For the event's own later rounds, the venue's flag from earlier years is the real-time prior. **Separating miscoding from conditions:** the signature of a first/second swap is first_in up with first_won down; fast conditions raise both |
| Why the model cannot already do it | No provenance or quality input exists |
| Expected effect (S6) | Small in 2014–2024: flagged events are mostly Challengers and qualifying, so a main-tour player's flagged share is a few percent and the bias is ≲ 0.3 pp of first_in. ≈ 0.01–0.03 mLL. **Its value is robustness in 2025–26** (R2). **Deployment:** an input rebuild, not a column. **2025–26 seen:** no |
| Kill test | **Result-free:** the venue flags persist across years at split-year reliability ≥ 0.5, and the swap signature holds; otherwise the detector flags conditions and stops. **In the screen:** the rebuilt profile ties the original → keep it as a robustness fix only |

### MAT-R2 · The 2025–26 measurement shift: attenuate or rebuild before the final test

| Field | Content |
|---|---|
| ID, name | MAT-R2, train/test reliability shift in the Tennis My Life (TML) faults |
| Mechanism | Training inputs (2013–2024) are Sackmann-sourced (inventory §6). Test-season histories carry the documented faults: <br>• TML women's aces and double faults, Dec 2024 – Feb 2026, agree with Sackmann only 57% and 18% of the time; <br>• men's Slam first serves miscoded since about Aug 2025; Wimbledon and the US Open 2026 were already replaced. <br>A model trained on clean inputs applies its coefficient b to an input whose test-season error variance is larger. The optimal coefficient is b·λ, with λ_i = var(x)/(var(x) + q_i·σ²_err), where q_i is the contaminated share of player i's evidence. TabPFN cannot know q |
| Why the price might miss it | n/a: this avoids harm in the final test |
| Type | U (deployment) |
| Formula | **Preferred:** rebuild the affected histories from Sackmann or official feeds. **Otherwise:** x′ = λ·x for women's iosO/iosD and form inputs of ace and df, and for men's first_in, first_won and second_won wherever 2025–26 Slam records enter the memory |
| Data | Stage 0 `source` and `tml_link`. The contaminated shares are counts, computable at M2 without results |
| Why the model cannot already do it | It has no provenance input, and training never saw the fault |
| Expected effect (S6) | None in the screen: 2014–2024 is clean, apart from the qualifying fault R1 found. In the final test it protects against a harm of unknown size: if 40–80% of women's 2025 ace and df counts are wrong, those inputs are partly noise in the test while the model trusts them at their training weight. **Deployment:** an input fix pre-registered at M2. **2025–26:** the fault is documented, its effect unseen |
| Kill test | At M2, counts only: if the contaminated share of every affected input's evidence is < 5%, no action |

## 5. What these ask the rulings to change

1. **I-042:** primary = τ without a Δh control; the estimator fixed now (R1).
2. **I-007:** retired in favour of the result-free decomposition (R2). The note to I-006's ruling: expected ≈ 0.01 mLL.
3. **I-001:** weight 0.5 in B-LEVER with I-006 and κ_surf·η (R3).
4. **I-008:** primary z_spw, with z_C1 as a sensitivity (R4).
5. **B5:** I-029 dropped by its own precheck (R5).
6. **G2/G5:** judge C columns by residual SD (finding 3) and S columns by flexible R² (K2). Lift the R²-only deferrals.
7. **Additions:** L1 (into the Lahvička joint fit), K1 (an M2 arm), K2 (a novelty rule), R1 (a robustness rebuild), R2 (an M2 pre-registration item).
