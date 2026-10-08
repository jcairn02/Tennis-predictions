# Round 2 · Market lens: rebuttals, literature additions, contrarian ideas, information timing

6 October 2026 · Brainstormer "market" · Research evidence, not a decision.

**No result was read.** Nothing was related to `a_won`, and no price was compared with an outcome. Every number below is result-free. It was computed on `data/studies/feature_interactions/round1/_panel_aug.parquet`, with `a_won` dropped at load and seasons 2014–2021 only, using the feasibility builders. The scripts are in the session scratchpad. Prices enter only as regressors or modulators (look-ledger row 6).

**Keys.**
* Gains are in mLL; higher is better. An interval that spans 0 is a tie.
* η is the current best model's out-of-sample log-odds, z is the de-vigged close, and adj = η − z.
* F = c·(`in_elo_overall` + `in_elo_surf_offset`) is a price-free forecast. The factor c = SD(z)/SD(Elo) is fixed per tour on 2014–2018: 0.892 (men), 0.881 (women). This is the audit's own result-free rescaling.

**Accepted without rebuttal:**
* the audit's findings 1 and 2 (price-slope controls; N → adj; Δ1 rescaled to the price's SD). Note that the feasibility builds still use a raw Δ1;
* the I-035 deferral. I checked that (π − ½)/(π(1 − π)) = sinh z, so shin_gap ≈ (Q − 1)·sinh z;
* I-006 tested as a two-sided format slope;
* I-002 and I-030 as sensitivities;
* I-037 and I-038 in B-ANCHOR (a > 0 in 46% of matches: my arbitrage reading was wrong);
* I-039 after M1 using adj;
* I-042's identity τ = −Δh(1 + cosh z) − Σh·sinh z, which I re-derived, and its weight rule.

## 1. Rebuttals (one per contested verdict, at most 150 words each)

**R-1 · I-081 in B-INFO: withdraw it (algebra and a number).**
* With N replaced by adj, I-081's column is adj·(1 − 4π(1 − π)) = adj·tanh²(z/2), since 1 − 2π = −tanh(z/2). That is exactly W-16's column (adjustment × lopsidedness).
* W-16 was killed by calculation (< 0.01 mLL), and the auditor confirmed the kill.
* A known-null member in a three-member composite scales the block's z, for the signal carried by the others, by √(2/3) = 0.82. Its MDE rises by a factor of 1.22.
* The feasibility build (`d1_x_lopsided`, R² 0.67 on the 58) used Δ1 instead: a third construction that neither audit ruled on.
* **Fix:** drop I-081 from B-INFO and from the study.

**R-2 · I-087 in B-INFO: withdraw it (computed).**
* Computed on 34,890 matches: w ≤ 1 day in 62.1% of matches. That is 93.0% from the round of 16 on, against 45.3% before it; corr(round code, 1[w ≤ 1]) = 0.48. So I-087's modulator is mostly round depth.
* I-080's attention index rises with round depth, and the two B-INFO columns correlate −0.27. Declared with the same sign, they partly cancel: a signal in one member keeps z × 0.60 in the composite instead of 0.71.
* With adj in place of N, I-087 is also a κ²-bounded rescaling (≤ 0.03).
* **Fix:** drop I-087; B-INFO becomes I-080 alone (weight 1). Its information-timing core returns as INFO-2, defined by an event that delays price formation rather than by the round.

**R-3 · I-034 in B6: withdraw it (algebra).**
* Take two unbiased Gaussian estimates of the same log-odds with variances σ₁² and σ₂². The posterior variance is (σ₁⁻² + σ₂⁻²)⁻¹, whatever their disagreement x₁ − x₂.
* So abs(Δ1) says nothing about how flat the price should be, and the declared sign "−" has no derivation.
* A sign needs heavy tails or a change of level. A change of level is I-033's flux, not a disagreement between two views. I-034's linear part, Δ1, is already formed from two inputs.
* **Fix:** drop I-034. B6 keeps I-033 and I-054, and a null third member no longer costs the block a factor √(3/2) in z.

**R-4 · I-085, deferred at feasibility: a forecast that needs no fit, and the identifiable column (computed, then algebra).**
* Use F above. It needs no fit, and coverage is 100% from 2014.
* Computed: the price drifts against the Elo favourite in 51.9% of matches. The RMS of r = z − F is 0.39 and that of the column is 0.30; 10.1% of matches drift by more than 0.5 against the favourite.
* Algebra: r·1[sign r ≠ sign F] = ½r − ½·abs(r)·sign F. With r controlled, the test is the coefficient on abs(r)·sign F.
* **Fix:** that antisymmetric column has no indicator jump; make it the primary, with sign + (the drifted favourite is better than priced).

**R-5 · I-086, deferred at feasibility: apply S11 (a rule already adopted).**
* The built column is multiplied by 1[round ≥ QF]. In those rounds the previous match is the won round of the same event, so the missing values (previous match lost, or unpriced) fall almost entirely on rows multiplied by 0.
* **Fix:** apply S11: set a missing difference to 0 and keep the missingness controls the audit lists. Coverage becomes 100%; nothing else changes.

## 2. Literature additions (two; the template plus the S6 fields)

**Checked first, as asked.** The favourite–longshot bias by rank tier is already covered. I-036 uses the lower-ranked player's obscurity and I-084 the pair's prominence, and both cite Lahvička for their bounds. Not covered: Lahvička's **round** and **profile** slopes, which appear only as *controls* in I-036's fit, and the literature's **attention-asymmetry** result. Workload, home advantage and volatility from the review are covered by the body lens's rows and by B5.

### LIT-1 · Later-round and high-profile price slopes, tested as hypotheses (Lahvička)

| Field | Content |
|---|---|
| ID, name | LIT-1, context favourite–longshot slopes |
| Mechanism | *Reported* (Lahvička [R28], 44,871 Bet365 matches, men 2002–13 and women 2007–13, proportional de-vig): with interactions, the base slope is 1.005, so there is no bias in ordinary matches. The bias sits in three contexts: <br>• +0.0918 when both players are outside the top 50; <br>• +0.0358 in later rounds; <br>• +0.0704 at Slams and finals. <br>Exchanges show the same pattern [R29]. The author reads it as books protecting against insiders and a public that reacts to news. |
| Why the price might miss it | One slope per tour cannot follow a bias that depends on context. A context slope on the average is not a de-vig artefact: the margin's SD is 0.55 pp (W-15), so that channel is ≤ 0.006 mLL. |
| Type | M × S |
| Formula | L = 1[not the event's first main-draw round], defined against the draw (the event's minimum round code); HP = 1[Slam or Tour Finals]. Both are context ✓. Columns L·η and HP·η (diff ✓). One-sided +, as one block of two. |
| Data | Model frame (`in_round`, `level`) and Stage 0 draws. Safe by construction. |
| Why the model cannot already do it | TabPFN learned no context dependence; calibration is one slope per tour; in the screen these products are only controls of I-036. |
| Expected effect | Sign +. Computed coverage 100%: L 53.2% of matches, HP 21.8%. |
| S6: prior Δ | Lahvička's slopes as RMS slope modulations, κ = δ·√share: <br>• L: 0.026, giving 79κ² = 0.055 mLL (men), 0.047 (women); <br>• HP: 0.031, giving 0.078 and 0.067. <br>These are for one soft book. For the average close beyond the current best, central ≈ 0.02–0.03 each: block material. |
| S6: M2 decomposition | s = L or HP, centred; d = η. <br>• Controls: the M-set; I-036 and I-084 in the same fit; I-006's 1[bo5]·η; Std. No main effect of s. <br>• Computed: corr(HP·z, bo5·z) = 0.71. Women's Slams and both tours' Finals separate profile from the men's format. <br>• corr(L·z, HP·z) = −0.56 and corr(L·z, I-036) = −0.26: fit them jointly. |
| S6: deployment | Nudge (a calibration slope modifier); TabPFN already has level and round. |
| S6: seen 2025–26? | No. Lahvička covers 2002–2013. The thinking study's Slam gains (seen on 2022+) are motivation only and are not used for the weight. |
| Kill test | In the batch, both coefficients ≤ 0 or spanning 0. Classify it [A] if it vanishes with the Pinnacle anchor. |

### LIT-2 · Attention to the favourite deepens the bias: the counterweight to I-083 (Abinzano; van Rheenen)

| Field | Content |
|---|---|
| ID, name | LIT-2, fame asymmetry × lopsidedness |
| Mechanism | *Reported:* <br>• on exchanges, mispricing rises with the relative attention paid to the favourite [R29]; <br>• in men's Slams, popular players were under-priced in finals and Big Four matches, though not exploitably [R33]. <br>*Inferred:* books shade against the expected flow toward a famous favourite more than that flow warrants. This is the opposite sign to I-083's fallen-star premium; the two are separated by the decline term R. |
| Why the price might miss it | The shading against fan money is the error, and it varies with the fame gap, which no price input carries. |
| Type | M × S, equivalently W: the identity s·η = abs(η)·ΔF |
| Formula | F = log(1 + titles + Slam quarter-finals or better), strictly earlier, as for I-083. s = sign(η)·ΔF, the favourite's fame minus the underdog's: symmetric ✓, since both factors flip. **Primary:** s·η = abs(η)·ΔF (diff ✓). |
| Data | Panel `titles_before`, `slam_qf_before` (already built). Safe. |
| Why the model cannot already do it | It has no fame input. |
| Expected effect | Sign +. Computed: ΔF ≠ 0 in 80% of matches; corr 0.50 with I-083's column and 0.48 with I-084's. |
| S6: prior Δ | The sources give no size. Central ≈ 0.01–0.04 mLL; coverage 100%. |
| S6: M2 decomposition | s = sign(η)·ΔF, d = η. Controls: the M-set; ΔF (linear); I-083 and I-084 in the same fit; Std. Recommendation: fit B-REPUTE's I-083 (−) jointly with LIT-2 (+), so that a one-sided composite does not absorb a fame effect of the opposite sign. |
| S6: deployment | Nudge |
| S6: seen 2025–26? | No: van Rheenen covers 2000–16; Abinzano was published in 2016. |
| Kill test | Coefficient ≤ 0 or spanning 0 in the joint fit with I-083. Classify it [A] if it vanishes with the Pinnacle anchor. |

## 3. Two contrarian ideas (critique S5)

### C-1 · The edge is the average's lag behind sharp money, not information the market lacks

| Field | Content |
|---|---|
| ID, name | C-1, the sharp anchor |
| Brief claim contradicted | That the +1.30 mLL over the recalibrated close is information beyond the market, living in the per-statistic profiles (the owner's thesis). Contrarian reading: much of it is the tennis-data average lagging the sharp price, through stale and shaded quotes. The profiles partly reconstruct that lag, and against a sharp anchor the gain shrinks. |
| Mechanism | *Observed:* <br>• on the same matches (2010–2026), the average is 0.7 mLL (men) and 0.6 (women) worse than Pinnacle (Stage 1); <br>• their log-odds differ by an SD of 0.114 and 0.089 (W-14). <br>*Inferred:* what moves Pinnacle before the average (news, sharp money) is what statistics-based models partly predict. |
| Why the price might miss it | The anchor the model is scored on is the soft average, not the sharp price. |
| Type | New main effect (labelled as such) plus a descriptive check |
| Formula | **Primary:** s_PS = logit p_PS − z, Pinnacle de-vigged proportionally (diff ✓), as a main effect beyond η. **Secondary, descriptive, in the batch:** η's gain against calibrated Pinnacle and against the calibrated average, on the same 2014–2024 matches. |
| Data | `stage1_odds` ps_a/b. Pinnacle covers 99.4% of 2014–2024 and ends in January 2026. Safe. |
| Why the model cannot already do it | It has no Pinnacle input; W-14 left Pinnacle as a second price to the market lens. |
| Expected effect | Contrarian prediction: a positive coefficient on s_PS beyond η, and η's gain over calibrated Pinnacle at most half its gain over the average. |
| S6: prior Δ | If half of s_PS is information η lacks: 99·¼·0.114² = **0.32 mLL** (men) and 0.20 (women), with the raw 0.7/0.6 as the ceiling. Sign +; coverage 99.4%. *Contrary prior:* the market-anchoring profile nudge gained about as much against Pinnacle as against the average (+0.44 against +0.52, 2019–2025, seen on 2022+). |
| S6: M2 decomposition | A main effect, d = s_PS. Controls: the M-set; Std (`in_odds_logit`). |
| S6: deployment | Not a test-season feature: Pinnacle ends in January 2026. If confirmed, M2 should train on a sharp anchor (Pinnacle through 2025, then Betfair) and restate the edge against it. |
| S6: seen 2025–26? | Stage 1's gap includes January 2026 (seen), as does the contrary prior; neither sets a weight. |
| Kill test | s_PS spans 0 beyond η, **and** η beats calibrated Pinnacle by at least half its margin over the average. |

### C-2 · Ratings are not priced in where the market is thin

| Field | Content |
|---|---|
| ID, name | C-2, rating against price × obscurity |
| Brief claim contradicted | "Ratings and win/loss information are priced in", which was measured over all main-tour matches. Contrarian: in matches between two obscure players the price's information is thin (low limits, few sharp bettors, late formation), and the results-based rating's disagreement with the price is informative. |
| Mechanism | *Reported:* the favourite–longshot bias is strongest when both players are outside the top 50 (Lahvička, slope +0.09). *Seen, motivation only:* Polymarket's lower tiers are the least efficient (2025–26). |
| Why the price might miss it | Books protect themselves in obscure matches by shading toward rank and their own caution, not toward the rating. |
| Type | S |
| Formula | O_min = log(min(rank_A, rank_B)) − its mean: the obscurity of the better-ranked player (symmetric ✓); unranked players follow Stage 1's rule plus a flag. **Primary:** (F − z)·O_min (diff ✓). |
| Data | Stage 0 rank; model frame; F as above. Safe. |
| Why the model cannot already do it | It has no rank input, and the rating–price disagreement is not modulated by anything. |
| Expected effect | Sign +. Computed: both players are outside the top 50 in 30.2% of matches; RMS of F − z is 0.39; abs(corr) ≤ 0.11 with every other price-slope column (I-036, I-084, I-083, I-006, LIT-1, LIT-2). It is new. |
| S6: prior Δ | ≈ 99·w²·0.39²·0.30 for a weight w on the rating's disagreement in obscure matches: w = 0.1 gives 0.04 mLL, w = 0.2 gives 0.17. Central 0.03–0.08; coverage 100%. |
| S6: M2 decomposition | s = O_min, d = F − z. Controls: F − z (linear); the M-set; O_min·η; I-036 and I-084 in the same fit; Std. |
| S6: deployment | Nudge; rank as a TabPFN context column is a sensitivity. |
| S6: seen 2025–26? | Only the Polymarket motivation (no weight); Lahvička covers 2002–13. |
| Kill test | Coefficient ≤ 0 or spanning 0. Classify it [A] if it holds against the average but not against Pinnacle. |

## 4. The missing lens: information timing (critique C7)

### INFO-1 · The clock's one-day blind spot: the player's own last result is missing from every cross-player input

| Field | Content |
|---|---|
| ID, name | INFO-1, own-result update of the IOS inputs |
| Mechanism | *Observed* (computed): <br>• For an exactly-dated match the clock sets lf = es + 1 (for example es 16066, lf 16067, width 2 days), because play can pass midnight or cross time zones. A result counts from lf + 1, so a result from day D reaches cross-player inputs only from D + 2. <br>• With rest = es − lf of the player's previous match, rest ≤ 0 marks a last result not yet counted. That holds in **26.3% of player-matches**, in **35.7% of matches** for at least one player, and in **45.2%** when the previous match was at the same event (consecutive-day rounds), against 1.7% otherwise. <br>• In those matches the 22 leak-proof IOS inputs (offence, defence, products, `ios_points_short`; TabPFN's most-used group) lack the player's last match, while the price, set after it, has it. The sequential per-player inputs (Elo, two-week form, `ratings_iid`) include it. |
| Why the price might miss it | It does not. This is the model's information deficit, an asymmetry in the price's favour, and the column recovers what the price already knows. |
| Type | W (an update along the player's own sequence), with an S reading through Σx |
| Formula | Per player: <br>• x = 1[rest ≤ 0]; <br>• u = the residual of his own last match on the IOS scale: observed serve and return points won minus their expectation from both players' leak-proof IOS at that match's es, times the short-memory solver's one-match weight (fixed from its decay, not tuned). <br>**Primary:** Δ(x·u) = ½[Δx·Σu + Σx·Δu] (diff ✓). The seven per-statistic versions are sensitivities. |
| Data | Panel `rest_min_a/b`; Stage 0 box score of the previous match; leak-proof IOS states at the previous match's es (`match_timing/ios_features.parquet` or surface IOS; their coverage of lower-level previous matches is to confirm). |
| Timing class | Safe by construction for u: a player cannot start a match before his previous one has finished. Its expectations come from IOS states already on the clock. Run `probe.py` on the finished column anyway. |
| Why the model cannot already do it | The IOS inputs are frozen by the clock. The two-week form holds the last match only inside a pooled, decayed mean, not as an update to the long-memory ratings. |
| Expected effect | Sign +. Bound: a one-match weight of 0.1–0.25 times a single-match residual of RMS ≈ 0.2 logit gives an input error of 0.02–0.05 logit on 26% of player-matches. |
| S6: prior Δ | ≈ 0.01–0.05 mLL beyond the form; coverage 100% (x = 0 elsewhere). |
| S6: M2 decomposition | W. Controls: Δu (linear), Δx, Σx·η; Std (`adjperf_tpw_2w`, `ios_points_short`). |
| S6: deployment | A process fix as much as a column: at bet time, recompute the IOS inputs with each player's own last result added, which is leak-free for that player. Otherwise a TabPFN difference column. |
| S6: seen 2025–26? | No evidence used. |
| Kill test | Coefficient spans 0; or the column's R² on the 58 is ≥ 0.95, which would mean the form already carries it. |

### INFO-2 · A first-round price formed late: the qualifier known only the day before

| Field | Content |
|---|---|
| ID, name | INFO-2, late-formed price × on-site qualifying form |
| Mechanism | The main-draw slot "Qualifier" is unknown until qualifying ends, usually the day before. Such a first-round price exists only from then, while direct-entry first rounds are priced from the draw, days earlier. The qualifier also brings two or three fresh box scores from these courts. *Computed:* <br>• 10.5% of all matches are first rounds with exactly one Q or LL who played on site and rests ≤ 1 day; that is 22.4% of first rounds; <br>• the qualifier has 2 (70%) or 3 (28%) on-site matches. <br>*Seen, motivation only:* main-tour lines settle 9–24 hours before the close (line sharpening, 2026). |
| Why the price might miss it | A younger price is less mature, and the on-site form reaches it last. |
| Type | S × W |
| Formula | s = 1[first round and exactly one player is a fresh Q or LL]. It is context ✓, because "exactly one" is symmetric. s_q = the qualifier's opponent-adjusted points won above expectation in this week's qualifying (0 for the direct entrant); w̃_q = w/(w + 200), with w his on-site points. **Primary:** s·Δ(w̃_q·s_q) (diff ✓). |
| Data | Stage 0 qualifying box scores (men's tour qualifying 90–95%, Slam qualifying 59%; women 84–85%); entry codes; panel `onsite_n`, `rest_min`. Safe by construction. |
| Why the model cannot already do it | The two-week form pools these matches with all others. No input marks a late-formed price, and there is no entry input. |
| Expected effect | Sign +. |
| S6: prior Δ | An RMS log-odds term of 0.05–0.10 on 10.5% of matches gives 99 × 0.105 × (0.0025–0.01) = 0.03–0.10 mLL; central ≈ 0.03. Coverage 100% (0 outside the subgroup). |
| S6: M2 decomposition | Controls: Δ(w̃_q·s_q) (linear), s·η; Std (`adjperf_tpw_2w`, I-082's low-visibility column, I-076's rhythm column). |
| S6: deployment | TabPFN difference column plus the context flag. |
| S6: seen 2025–26? | Only the line-sharpening motivation (no weight). |
| Kill test | Coefficient ≤ 0 or spanning 0, or no gain beyond I-082's column in the same fit. It replaces I-087's timing claim with an event that can be identified. |

## 5. Requested changes, in one place

| Item | Request | From |
|---|---|---|
| I-081 | Withdraw (it is W-16 with adj) | R-1 |
| I-087 | Withdraw; INFO-2 carries its timing claim | R-2 |
| I-034 | Withdraw (no Gaussian derivation of the sign) | R-3 |
| B-INFO | I-080 alone, weight 1 | R-1, R-2 |
| B6 | I-033 and I-054 | R-3 |
| I-085 | F without a fit; primary abs(r)·sign F, sign + | R-4 |
| I-086 | Apply S11 | R-5 |
| New rows for the hypothesis table | LIT-1 (block of two), LIT-2 (fit jointly with I-083), C-1, C-2, INFO-1, INFO-2 | §2–§4 |

## What was computed (all result-free)

* All on seasons 2014–2021, with `a_won` dropped at load and no season after 2024 loaded.
* Overlaps and shares from the feasibility builders (`builders_a/b/c`) on 34,890 matches:
  * the I-080 and I-087 columns, and round depth against the short-window flag;
  * the drift column of I-085 with F;
  * correlations among the price-slope columns (I-036, I-084, I-083, I-006, LIT-1, LIT-2, C-2);
  * the clock's rest ≤ 0 shares and the qualifier counts.
* The clock's es/lf convention, read from `timing.parquet` (schedule fields only).
* Scripts: `r2_overlap.py`, `r2_drift.py`, `r2_lit.py`, `r2_timing.py` in the session scratchpad, plus two inline checks.
* No fit, no GPU, no Git command, nothing deleted.
