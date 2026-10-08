# Round 0 ideas: the market lens

6 October 2026 · Brainstormer "market" · Ideas only: research suggestions, not decisions. No feature was related to match outcomes for this file (what was read and computed is listed at the end).

**Lens.** Where the closing price errs, and how that error depends jointly on the price and on match statistics or context. An interaction belongs here when the market's error depends on two things at once.

## Conventions

* **Notation.**
  * z = `in_odds_logit` = logit π, where π = (1/avg_A) / (1/avg_A + 1/avg_B) is the proportionally de-vigged average close from tennis-data.co.uk. Per-player quantities are x_A and x_B, and Δx = x_A − x_B.
  * **Δ1**, used in several ideas, is the points-based view minus the results-based view of the same match: c_iid·`in_ratings_iid` − c_elo·(`in_elo_overall` + `in_elo_surf_offset`). Each view is rescaled by its own per-tour calibration slope, fitted walk-forward on earlier seasons. Both inputs appear to be on a log-odds scale (*inferred* from their 2013–2021 ranges, to confirm: `in_ratings_iid` spans ±9.21, which is logit 0.9999; its SD is 1.56 against 1.08 for Elo). The rescaling stops the iid model's over-confidence from dominating the contrast.
  * **N** is the profile nudge index. It is the out-of-fold linear predictor of a ridge fit of the result on the 37 profile inputs (`form_*`, `formdef_*`, `iosO_*`, `iosD_*`, `prod_*`), with z as an unpenalised offset and no intercept. It is refitted on each training window, which is the market-anchoring study's form.
* **Column kinds** follow the model frame's flip rule:
  * *diff* is negated when A and B swap;
  * *context* is unchanged;
  * *pair* is exchanged.

  diff × context gives a diff. diff × diff is symmetric, so it can only act as context. f(A) − f(B) is always a diff. Every formula states its kind and its swap check (✓).
* **One primary column per idea**, pre-declared for the screen to limit forking paths. The rest are secondary. "Main effects" lists what the screen must hold so that the interaction is tested beyond them (gate G3).
* **Anchor class.**
  * **[I] information error.** The price lacks the information. The effect should survive a sharp anchor (Pinnacle, which exists alongside the average in 2013–2021) and should still exist at bet time on an exchange.
  * **[A] anchor-construction error.** An artefact of the tennis-data average: its margin, stale quotes or shaded quotes. It improves the score against the average, but not against Pinnacle, Betfair or Polymarket, unless the bet-time price is itself a bookmaker quote. The [sharp benchmark](../../sharp_benchmark/README.md) found Betfair and Polymarket as sharp as Pinnacle.
* **Quoted scores** are milli-log-loss (mLL) gains. Higher is better for the named arm; an interval spanning 0 is a tie. A prior measured on seasons from 2022 on is flagged "(seen on 2022+)", because those seasons now serve as replication or test.

## Framing: what the market lens adds

1. **Two kinds of price error, and only one is betting-relevant.** An [A] fix is cheap and real for the research benchmark. The owner's direction, though, is betting on venues as sharp as Pinnacle. **Suggestion:** re-run every candidate on 2013–2021 with Pinnacle's de-vigged log-odds as the anchor. Use it as a classification check, not a gate.
2. **Where an information error can survive the close.**
   * The price is very good at *who is better*. Surface Elo, surface IOS, TrueSkill Through Time and recent form all tie with the odds.
   * It may still misprice four things:
     * the *structure* of a matchup that A − B differences hide: sums of serve strengths, variances, format leverage;
     * evidence it barely *sees*: matches below the main tour;
     * *incentives and settlement*: retirements, motivation;
     * matches where its *own information is thin*: low attention, unsettled books, a short time to form the price.
3. **Price × context terms can also live in the calibration step.** The model's calibration is one slope per tour, and TabPFN learned no dependence on context: interactions explain about 2% of its adjustment, and context carries nothing ([thinking report](../../tabpfn_thinking/README.md)). **Suggestion:** test each slope idea (MKT-01, 02, 03, 05, 06, 08, 14) both as a TabPFN input and as a slope modifier in the calibration: logit p = b·logit p_model + Σ c_k·(ctx_k × logit p_model). Earlier studies found calibration worth more than any input tested.
4. **Data notes for the cartographer.** These were observed from header rows and coverage counts in this session; the cartographer should verify them.
   * **tennis-data bookmaker columns by season:**
     * 2010–2014: B365, EX, LB, PS and SJ (SJ through 2013 at least), plus Max and Avg;
     * 2015–2018: B365, EX, LB, PS, Max, Avg;
     * 2019–2024: B365, PS, Max, Avg;
     * BFE (Betfair Exchange) from August 2025.
     `stage1_odds.parquet` carries avg, ps, max and b365 per side.
   * **Max and Avg** are OddsPortal's ("maximum/average odds as shown by Oddsportal.com", provider notes). Whether Max can be an exchange back price is unknown. It matters for MKT-14.
   * **A men's 2018 workbook is on disk:** `data/raw/public_dump/tennis_data_couk/atp/2018.xlsx`, with the standard columns including PSW/PSL. The brief and Stage 1 say the men's 2018 season has no odds file. Check whether it is a later download and whether it is linked into the model frame.
   * **Pinnacle ends on 13–14 January 2026.** Pinnacle-based features are missing for most of the 2026 test.
   * **Polymarket and Betfair exist only for 2025–2026.** Rule 1 forbids discovering anything on them, so no feature here uses them.
   * **Box-score coverage, 2013–2021.**
     * Men: Challenger 99%, tour qualifying 90–95%, Slam qualifying 59%.
     * Women: WTA 125 86–88%, tour qualifying 84–85%.
     * ITF: none.
   * **Entry codes present:** Q, WC, LL, ALT, SE, PR, SR, JE, IR, JR.
   * **Match minutes are sparse** across all levels: 34% (men), 12% (women).

---

## A. The price's calibration by match structure and context

### MKT-01 · Margin-aware de-vig: overround × price level [A]

| Field | Content |
|---|---|
| ID, name | MKT-01, margin-aware de-vig |
| Mechanism | Bookmakers load more margin on the longshot. Proportional de-vigging of the average therefore leaves the favourite–longshot bias (FLB) in the anchor. How much is left depends on the price level and on that match's overround together. For two outcomes, Shin's method equals the additive rule p = (1 + q_A − q_B)/2 (the sharp-benchmark study checked this numerically). That rule differs from the proportional π by exactly (Q − 1)(π − ½). |
| Why the price might miss it | This is the anchor's error, not the market's. *Observed* (market anchoring, 2013–2025): the average's calibration slope is 1.09 (SE 0.015), against 1.03 for Pinnacle. *Observed* (sharp benchmark, seen on 2026; motivation only): Betfair's 1.6 mLL edge over the average, found with proportional de-vigging, disappeared under power or Shin de-vigging. A global slope corrects the mean margin with a linear shape. The additive correction is convex in z and scales with each match's own margin. |
| Type | M |
| Formula | q = 1/odds, Q = q_A + q_B, π = q_A/Q. p_S = clip(π + (Q − 1)(π − ½), 0.005, 0.995). **Primary:** shin_gap = logit p_S − z. It is a diff ✓: π → 1 − π with Q unchanged gives p_S → 1 − p_S. Secondary: m = Q − 1 (context ✓). Also the power-method gap: k solves q_A^k + q_B^k = 1, which is symmetric in A and B, so p_A → 1 − p_A ✓. Main effects: m. |
| Data | `stage1_odds.parquet`: avg_a, avg_b, overround_avg, avg_coherent; 2010–2026. Safe by construction: the match's own quotes. |
| Why the model cannot already do it | It sees only z. Q is not an input, and the calibration after the model is one slope per tour-season. TabPFN can bend z but cannot tie the bend to the match's margin. |
| Expected effect | Positive coefficient: near 1 if the additive rule is right, less if TabPFN's curvature already absorbs it. *Derived:* odds of 1.03/15.0 give π = 0.936 and p_S = 0.952, a shift of 0.31 log-odds, against 0.24 from a slope of 1.09. Gain beyond the best model: about +0.03 to +0.2 mLL, concentrated in heavy favourites, high-margin seasons and women. **Bet-time value:** an exchange price has no bookmaker margin, so training on a margin-corrected anchor brings the training input closer to what the model is fed at Polymarket. |
| Kill test | In discovery (2013–2021), shin_gap adds ≤ 0 beyond the best model's out-of-sample (OOS) forecast with m included, or its interval spans 0. Or it fails to replicate in 2022–2024. |

### MKT-02 · Early-surface-season under-confidence [I, partly A]

| Field | Content |
|---|---|
| ID, name | MKT-02, early-season slope |
| Mechanism | At the start of a surface season the books know less (off-season form, fitness) and shade toward 50%, so favourites win more often than priced. *Observed* (market anchoring §6.4, 2013–2025 fits, seen on 2022+): <br>• average-price slope 1.15 (SE 0.03) early on hard courts, against 1.06 for the rest of the season; <br>• Pinnacle 1.09 against 1.00; <br>• early grass 1.13 against 1.03. |
| Why the price might miss it | The caution itself is the error. Pinnacle shows it too, so it is not only a feature of how the average is built. |
| Type | M × S |
| Formula | E = 1[min(n_A, n_B) < 3], with n the matches on this surface this season. If `in_surf_season_*` is log(1 + n) (*inferred* from its range of 0–4.19; to confirm), this is min(`in_surf_season_a`, `in_surf_season_b`) < log 4. E is context ✓ because min is symmetric. **Primary:** z × E (diff ✓). Secondary: z × E × 1[hard], z × E × 1[grass]; a graded E′ = exp(−min(n_A, n_B)/3). Main effects: E. |
| Data | Model frame: `in_surf_season_a/b`, `in_surface`, `in_odds_logit`. Safe by construction. |
| Why the model cannot already do it | TabPFN has every piece but learned an additive, context-free adjustment. The calibration uses one slope for the whole season. |
| Expected effect | Positive coefficient: steepen the price early in the season. Strongest in the Australian summer and at the grass openers. Overall +0.05 to +0.2 mLL. *Prior* (market anchoring), a slope varying with early season, best of five, surface and level: <br>• +0.12 [−0.08, +0.32] over 2019–2025, a tie; <br>• +0.31 [+0.003, +0.62] on top of profile + context over 2019–2026 (seen on 2022+). |
| Kill test | The primary spans 0 or is ≤ 0 in discovery beyond the best OOS forecast, or does not replicate in 2022–2024. Classify it [A] if it vanishes with the Pinnacle anchor. |

### MKT-03 · Best-of-five leverage the price under-transmits [I]

| Field | Content |
|---|---|
| ID, name | MKT-03, format leverage |
| Mechanism | Five sets compound the same point edge into a larger match edge. *Derived here* (iid arithmetic, no data): for the same serve-point probabilities, best-of-five log-odds are about 1.26 times best-of-three ones. Examples: 1.066 against 0.847 at 0.60/0.56; 0.944 against 0.751 at 0.72/0.68. <br>*Observed* (Stage 1, 2013–2026, seen on 2022+): market favourites won 2.0 points more than priced at best of five, against 0.4 at best of three. <br>*Observed* (thinking report, 2022–2026): TabPFN's largest gain is at the Slams (+2.75, men). Beyond a cubic + Slam + best-of-five odds calibration, +1.94 remains there, so it is not only a slope. |
| Why the price might miss it | Most betting volume and intuition is built on best of three. If the price applies only part of the leverage, its error grows with the leverage of that match's point edge. A slope on z cannot represent that when the statistics and the price disagree about the point edge. |
| Type | C, S |
| Formula | From the per-player serve-point probabilities behind `in_ratings_iid`: u = logit P_iid(p_a, p_b; actual format) and v = logit P_iid(p_a, p_b; best of three). Serve order is averaged, which makes both exactly antisymmetric. **Primary:** L = 1[bo5] × (u − v). It is a diff ✓: P → 1 − P on swap. Secondary: 1[bo5] × (u − z) (diff ✓). Main effects: z × 1[bo5]; `in_ratings_iid` is already in the model. *Theory:* L's coefficient is the share of the leverage the price leaves out: 0 if fully priced, 1 if priced as best of three. |
| Data | Model frame: `in_best_of`, `in_ratings_iid`. Per-player serve-point probabilities: `stage3_ratings.parquet` (p_serve_a/b), or the repaired ratings behind `in_ratings_iid` (the cartographer should locate them). Stage 2's iid code. Timing class as for those ratings (sequential, so safe; to confirm). |
| Why the model cannot already do it | The best-of-three counterpart is not an input. The effect needs a three-way term (format × ratings × price), and the model's adjustment ignores context. |
| Expected effect | Positive coefficient, about 0.1–0.4. Men's Slams only: about +0.3 to +1 mLL on those matches, about +0.1 overall. |
| Kill test | L's coefficient spans 0 on men's Slam matches of 2013–2021. Or z × 1[bo5] alone does as well, in which case the effect is a slope and is re-filed with MKT-02 and MKT-06. |

### MKT-04 · Serve-dominance compression: the sum that the price, and the model, never see [I]

| Field | Content |
|---|---|
| ID, name | MKT-04, serve-dominance compression |
| Mechanism | At a fixed serve-point gap, two dominant servers decide their match on rare breaks and tiebreaks, so it is closer to a coin flip than the same gap between two returners. *Derived here* (iid arithmetic, no data), with a gap of 0.04: raising the sum of serve-point probabilities from 1.16 (0.60/0.56) to 1.40 (0.72/0.68) lowers the best-of-three log-odds from 0.847 to 0.751, and the best-of-five from 1.066 to 0.944. That is about 11% of the log-odds. |
| Why the price might miss it | Ratings, rank and pricing heuristics say who is better, not how decisive the matchup is. Whether the average close fully prices hold-based structure is an open question. The model cannot see this at all: every input is a difference, and a difference hides the sum (brief). |
| Type | M × S, with a C derivation |
| Formula | p_a = P(A wins a point on his serve against B), and p_b likewise. They come from leak-proof surface IOS serve points won (server offence − returner defence + surface mean), or from Stage 3's p_serve. D = p_a + p_b − 2μ_tour,surface (context ✓: a swap exchanges the two terms). **Primary (structural):** comp = logit P_iid(p_a, p_b) − logit P_iid(μ + g/2, μ − g/2), with g = p_a − p_b. It is a diff ✓: P(p_b, p_a) = 1 − P(p_a, p_b) with serve order averaged, and g → −g. Secondary: z × D (diff ✓), and the tiebreak propensity T = P(a set reaches 6–6) as context. Main effects: D, T. *Theory:* comp's coefficient is the share of the compression the price ignores, between 0 and 1. |
| Data | `surface_features.parquet`: cur_O_spw_a/b, cur_D_spw_a/b, srf_*_eff_spw_*. These are built on the match clock (leak-proof). Or `stage3_ratings.parquet`: p_serve_a/b, mu_logit. Needs the leak-proof clock for IOS. |
| Why the model cannot already do it | Differences hide the sum. The `prod_<s>` columns are differences of cross-products, not sums. `in_ratings_iid` carries the compression inside its value, but nothing tells the model whether the price carries it. |
| Expected effect | Positive on comp, negative on z × D. If the price ignores the compression entirely: typical log-odds errors of 0.03–0.05, about +0.1 to +0.2 mLL overall. Larger on grass and fast indoor hard, men more than women. On clay the sign of D flips: favourites should be extended. |
| Kill test | comp's coefficient spans 0 in discovery beyond the best OOS forecast. Or the gain vanishes once z × surface dummies are included, which would make it a surface slope rather than matchup structure. |

### MKT-05 · Volatility compression: the price prices means, not variance [I, U]

| Field | Content |
|---|---|
| ID, name | MKT-05, volatility compression |
| Mechanism | Two erratic players produce a more random match than their mean levels imply. The market anchors on mean strength: ratings, rank, recent results. *Observed* ([predictive frontier](../../predictive_frontier/README.md), men, 2019+): reliability/variability was the best of five families against the Pinnacle + profile model, +0.232 [−0.038, +0.502], a tie (seen on 2022+). Against the strong Elo model it gained +2.02. |
| Why the price might miss it | A price is a single number. Nobody quotes a player's consistency, and recreational money follows means. |
| Type | U; M × S |
| Formula | σ_i = shrunk SD of player i's match-level residuals of total points won against his pre-match expectation, over 52 weeks. V = σ_A² + σ_B² (context ✓). **Primary:** z × V (diff ✓). Secondary: Δ1 × V. Main effects: V. In an iid-type model the spread of the outcome depends on the sum of the variances, so who is the erratic one does not enter. |
| Data | `frontier_features.parquet` holds only differences (pf_instability_diff, pf_instability_elo). Per-player σ must be rebuilt with `src/eda/predictive_frontier/features.py`, or from Stage 0 box scores. Expectations from sequential ratings are safe; from IOS they need the leak-proof clock. |
| Why the model cannot already do it | Its inputs are differences of means: it sees no variance and no sum. |
| Expected effect | Negative coefficient: shrink toward 50%. Mainly erratic young players and the WTA. +0.05 to +0.3 mLL. |
| Kill test | The coefficient is ≥ 0 or spans 0. Or it adds nothing beyond MKT-08, in which case the two merge into one shrinkage term. |

### MKT-06 · Obscure-match slope: FLB by level, round and the players' fame [A/I]

| Field | Content |
|---|---|
| ID, name | MKT-06, obscure-match slope |
| Mechanism | The FLB has two sources, and both vary across matches. <br>• Recreational money (longshot lottery tickets, favourites as accumulator "bankers") is heaviest in famous, televised matches. <br>• Integrity risk is highest in obscure matches between low-ranked players at 250s. Books guard against it by widening margins and shortening sides (*inferred*; no source checked in this round). <br>So the slope the price needs depends on the type of match. |
| Why the price might miss it | One slope per tour cannot follow an FLB that varies with the type of match. The model has no rank input. |
| Type | M × S |
| Formula | Contexts ✓: <br>• S250 = 1[250]; <br>• R = round depth (first round of the draw 0, final 1); <br>• O = max(log rank_A, log rank_B) − the tour median (the obscurity of the lower-ranked player; max is symmetric). <br>**Primary:** z × O (diff ✓). Secondary: z × S250, z × R. Main effects: O. |
| Data | Model frame (level, round); Stage 0 rank, with unranked players handled by Stage 1's rule plus a flag. Safe. |
| Why the model cannot already do it | No rank input, and context × price is not learned. |
| Expected effect | Positive on z × O: in obscure matches, proportional de-vigging leaves more FLB, so favourites are under-priced. +0.05 to +0.15 mLL. Overlaps MKT-01, because margins are higher where matches are obscure. |
| Kill test | The primary spans 0 in discovery. Or it vanishes once MKT-01's m and shin_gap are in, which would make it the margin. |

---

## B. Disagreement: price, ratings, rank and profile

### MKT-07 · Attention-modulated disagreement: the profile matters most where the market looks least [I]

| Field | Content |
|---|---|
| ID, name | MKT-07, attention × disagreement |
| Mechanism | The close mixes money that follows ratings and rank with sharp money that follows the profile. Sharp money concentrates where limits and liquidity are high: Slams, 1000s, late rounds, famous players. Where attention is low, the price leans on ratings and rank, so a points-versus-results disagreement is priced less. <br>*Observed* ([Polymarket study](../../polymarket_sharp_money/README.md), 2025–2026): accounts that beat the close earn most at Challenger and WTA 125 events (+1.75¢ per $1) and least at the Slams (+0.68¢). <br>*Observed* (thinking report): TabPFN's gain was largest at the Slams (+2.75). That runs against this idea, unless MKT-03 explains the Slams. |
| Why the price might miss it | The price's weight on the profile is not constant. A constant, additive correction (what TabPFN learns) under-corrects low-attention matches and over-corrects high-attention ones. |
| Type | S |
| Formula | Attention A (context ✓) is pre-declared as the mean of four components, standardized on 2013–2018: <br>• level (250 = 0, 500 = 1, 1000 = 2, Slam or Finals = 3); <br>• round depth; <br>• star power, −min(log rank_A, log rank_B); <br>• crowding, −log(1 + other tour-level main-draw singles matches scheduled that day). <br>**Primary:** Δ1 × (−A) (diff ✓). Secondary: N × (−A); each component on its own. Main effects: Δ1 (formed from the inputs), A. |
| Data | Model frame; Stage 0 rank and round; same-day counts from `stage1_odds` td_date or `timing.parquet` es. The counts are schedule information, known from the order of play: count matches scheduled, not matches completed. Safe; N is walk-forward. |
| Why the model cannot already do it | No rank and no schedule inputs. TabPFN's interaction share is about 2%, and context carries nothing. |
| Expected effect | Positive coefficient, largest in early rounds of 250s, with obscure players, on crowded days. +0.1 to +0.4 mLL. |
| Kill test | The primary spans 0 in discovery, or its sign reverses in 2022–2024. |

### MKT-08 · Conflict shrinkage: when statistics and ratings disagree, the price is too sure [I, U]

| Field | Content |
|---|---|
| ID, name | MKT-08, conflict shrinkage |
| Mechanism | When the points-based and the results-based view of the same two players conflict, the true uncertainty is larger than either view suggests, whichever of them is right. A price anchored on the ratings states the ratings' confidence. |
| Why the price might miss it | A price carries no uncertainty, and a conflict between evidence sources is invisible in a rating gap. |
| Type | U, M |
| Formula | **Primary:** z × abs(Δ1) (diff ✓: abs is unchanged, z negates). Secondary: z × abs(N); abs(Δ1) as context. Main effects: Δ1, abs(Δ1). |
| Data | Model frame only. Safe. |
| Why the model cannot already do it | It would need a nonlinear function of a contrast between two inputs, multiplied by a third input. |
| Expected effect | Negative coefficient: shrink the price. Mostly in mismatches where the statistics see a closer match. +0.05 to +0.2 mLL. |
| Kill test | The coefficient is ≥ 0 or spans 0. |

### MKT-09 · Profile weight by price level: where the market leans on names [I]

| Field | Content |
|---|---|
| ID, name | MKT-09, profile × lopsidedness |
| Mechanism | Recreational money concentrates in lopsided matches: favourite "bankers" in accumulators and longshot lottery tickets. There the price is anchored on names. Near-even matches attract model-driven money. The profile's correction may therefore be larger in lopsided matches, telling which favourites are vulnerable and which longshots are live. |
| Why the price might miss it | The share of name-driven money varies with the price level. |
| Type | M |
| Formula | v = 4π(1 − π) (context ✓: unchanged when π → 1 − π). **Primary:** N × (1 − v) (diff ✓). Secondary: Δ1 × (1 − v). N × z would be symmetric and could act only as context; v is the allowed form. Main effects: N, v. |
| Data | Model frame. Safe; N is walk-forward. |
| Why the model cannot already do it | N is a constructed index of 37 inputs, and TabPFN's adjustment is near-additive. |
| Expected effect | Sign open, leaning positive. +0.05 to +0.2 mLL. |
| Kill test | The primary spans 0 in discovery. |

### MKT-10 · Rank anchoring × career trajectory: young risers, ageing decliners [I]

| Field | Content |
|---|---|
| ID, name | MKT-10, rank gap × age |
| Mechanism | The official rank is a 52-week sum of points. It lags a rising young player and flatters an ageing one, and Elo lags genuine trajectories too (a small K for established players). If the price anchors partly on rank, its error grows with the gap between rank and level, and that gap means different things at 20 and at 32. <br>*Observed* (market anchoring §6.6, 2013–2025): age is the strongest single nudge given the price; older players do worse than priced (z = −3.7). <br>*Observed* (Stage 4), given the market, both small gains with signs not reported: <br>• the women's ranking adds +0.32 [0.01, 0.62]; <br>• the gap between rank and Elo adds +0.27 [−0.01, 0.55]. |
| Why the price might miss it | Rank is what the public sees, and ratings lag behind real change. Trajectories are not quoted anywhere. |
| Type | W |
| Formula | Per player: <br>• g = ê(log rank) − Elo, where ê maps log rank to the Elo scale per tour, fitted on earlier seasons only (positive = ranked better than rated); <br>• T = overall Elo now − 52 weeks earlier; <br>• a = (age − 27)/5. <br>**Primary:** Δ(g × a) (diff ✓). Secondary: Δg; Δ(T × 1[age ≤ 23]); Δ(T × 1[age ≥ 30]). Main effects: Δg, ΔT, plus Δage (in the model). |
| Data | Stage 0 rank (as of the tournament start) and age; Elo history (`stage1_baselines.parquet`, or the surface-Elo-pieces study's `pieces.parquet`). Safe by construction. |
| Why the model cannot already do it | Rank and trajectory are not inputs. Age enters only as A − B, so a player's age cannot be combined with his own rank gap. |
| Expected effect | Δg negative: a player ranked above his level is over-priced. Δ(g × a) negative: more so when older. Trajectory terms positive: trajectories continue. Women more than men. +0.1 to +0.4 mLL. |
| Kill test | The primary and Δg both span 0 in discovery. Classify it [A] if it vanishes with the Pinnacle anchor. |

### MKT-11 · Salience-weighted evidence: form earned where nobody watches [I]

| Field | Content |
|---|---|
| ID, name | MKT-11, visibility discount |
| Mechanism | The market weights evidence by how visible it is. A run through a Challenger or through qualifying is seen by few bettors and reaches the main-tour price mainly through the rank, slowly. A Slam quarter-final is seen by everyone. Points are equally informative wherever they are played. *Observed:* lower-tier Polymarket lines form late and thin ([line sharpening](../../line_sharpening/README.md)). The model's two-week profile pools every level. |
| Why the price might miss it | It under-weights form from low-visibility matches, and possibly over-weights form from high-visibility ones. |
| Type | W |
| Formula | Per player, with the two-week profile's decay (half-life 14 days): <br>• s_L and s_H are opponent-adjusted total points won above expectation (adjperf_tpw). L covers low-visibility matches: Challenger and WTA 125 main draws and qualifying, and tour and Slam qualifying. H covers tour-level main draws. <br>• w̃ = w/(w + k), where w is the decayed number of points played in that class and k is fixed in advance (200 points, the predictive frontier's constant). <br>**Primary:** Δ(w̃_L × s_L) (diff ✓). Secondary: Δ(w̃_H × s_H); the low-visibility share Δ(w_L/(w_L + w_H)). Main effects: the pooled two-week form (in the model). Hypotheses: β_L > 0 beyond the best model, and β_L > β_H. |
| Data | Stage 0 box scores (coverage in the data notes above), levels, rounds. Opponent adjustment through sequential ratings is safe; through IOS it needs the leak-proof clock. Lower-level box scores more than double in 2025 (surface-IOS study), a shift between discovery and test. |
| Why the model cannot already do it | The two-week profile pools all levels, so the model cannot tell where the form was earned. |
| Expected effect | β_L positive, men more than women. Concentrated in players arriving from Challengers and qualifying. +0.1 to +0.5 mLL. |
| Kill test | β_L ≤ 0 or spans 0 in discovery, or β_L ≤ β_H. |

### MKT-12 · Drifting favourite: does the price over-react to news against the ratings favourite? [I]

| Field | Content |
|---|---|
| ID, name | MKT-12, drift asymmetry |
| Mechanism | The price's residual on the fundamentals is mostly news: injury, illness, practice reports. Bad news about a favourite is amplified by recreational money and by books' caution, while good news is absorbed slowly. If so, a drift against the fundamentals favourite overshoots. |
| Why the price might miss it | Asymmetric over-reaction is a known behavioural pattern, and the close inherits it unless sharp money fully corrects it. |
| Type | M, W |
| Formula | F = the log-odds of a price-free forecast: the best model's no-odds sibling, walk-forward (fallback: the rescaled Elo log-odds). r = z − F. **Primary:** r × 1[sign(r) ≠ sign(F)] (diff ✓: r and F both negate, so the indicator is unchanged). Main effects: r. |
| Data | Model frame; walk-forward no-odds forecasts (the surface-rating-race and meta-stack base_noodds arms). Safe if walk-forward. |
| Why the model cannot already do it | It would have to build F from 57 inputs and then condition on its sign. |
| Expected effect | Negative coefficient: the drifted favourite is better than priced. +0.05 to +0.15 mLL. *Prior:* the symmetric version (signed square of the disagreement) tied, −0.03 [−0.09, +0.02] ([meta stack](../../meta_stack/README.md); seen on 2022+). The asymmetry is untested. |
| Kill test | The primary spans 0 or is positive. |

### MKT-13 · Last-round narrative: surprise wins and flattering scorelines [I]

| Field | Content |
|---|---|
| ID, name | MKT-13, last-round narrative |
| Mechanism | A player who has just beaten a much better player, or won 6–1 6–2, is backed in the next round. Both the price and Elo move most after a surprise. A single upset, or a scoreline flattered by break points and tiebreaks, is mostly noise. |
| Why the price might miss it | Salience: bettors see the scoreline and the upset, while the points are what predicts. |
| Type | W |
| Formula | For each player's previous main-draw match at this event: <br>• s = 1 − p_prev, the surprise of that win against his own de-vigged price then (missing, with a flag, if that match had no price); <br>• λ = games share − E[games share given the serve and return points he won], using the iid expectation. <br>**Primary:** Δs × 1[round ≥ QF] (diff × context ✓). Secondary: Δs; Δλ. Main effects: Δs. |
| Data | `stage1_odds` (the previous match's odds); Stage 0 rounds, scores, games_won_n/d and box scores. Safe by construction: the player's own earlier match. |
| Why the model cannot already do it | It has the updated Elo and the two-week profile, but not how surprising the last result was against its own price, nor the luck in the last match. *Prior:* decayed conversion luck added nothing given the price, −0.01 [−0.10, +0.09] (market anchoring, 2019–2025). |
| Expected effect | Negative coefficient: fade the narrative. +0.02 to +0.15 mLL. |
| Kill test | The primary spans 0 or is positive. |

---

## C. Market state: book disagreement and price maturity

### MKT-14 · Book dispersion as uncertainty [A/I, U]

| Field | Content |
|---|---|
| ID, name | MKT-14, dispersion |
| Mechanism | When books disagree at the close, the average is a noisier and lagging estimate of the sharp price. Causes include stale quotes after a late move, news reaching some books first, and thin markets. Errors-in-variables logic says the price then deserves less weight and other evidence more. *Observed* (surface Elo pieces §5.7; post hoc, about 60 cells, seen on 2022+): in the most dispersed third (best price against the average), the new Elo representation helped +0.40 [+0.02, +0.78] (men +0.88 [+0.29, +1.48]) and tied elsewhere. |
| Why the price might miss it | Dispersion is information about how reliable the price is, and the price itself does not carry it. |
| Type | U |
| Formula | **Arbitrage** a = 1 − (1/max_A + 1/max_B) (context ✓). It is positive only when the best prices on the two sides cross, so it is not just the average's margin. **Spread** d = log(max_A/avg_A) + log(max_B/avg_B) (context; secondary, because it mixes in the margin). **Primary:** z × a (diff ✓). Secondary: N × a and Δ1 × a (diff ✓). Main effects: a. |
| Data | `stage1_odds`: max_a/b, avg_a/b, 2010–2026. Needs rules for outliers and incoherent pairs. Safe. Unknown: whether OddsPortal's Max includes exchange back prices. |
| Why the model cannot already do it | It has no book-level input. |
| Expected effect | Negative on z × a, positive on N × a. +0.1 to +0.3 mLL. **Deployment:** it needs bookmaker quotes at bet time; Polymarket alone has none. |
| Kill test | Both columns span 0 in discovery. Classify it [A] if it vanishes with the Pinnacle anchor. |

### MKT-15 · Best-price skew: steam or shading, told apart by fame [A]

| Field | Content |
|---|---|
| ID, name | MKT-15, best-price skew |
| Mechanism | Where the best prices sit relative to the average carries a direction, with two opposite readings. <br>• **Steam.** After a late move toward A, slow books keep A's old, longer price, so the max-implied chance of A falls below the average-implied one. The truth lies above the average. *Worked example:* old odds 2.00/1.85, new 1.70/2.20, a fifth of books stale. Then p_avg(A) = 0.548, p_max(A) = 0.524, and the new consensus is 0.564. <br>• **Shading.** Soft books shorten a popular player's price, so his best price sits at a sharp book, and again p_max < p_avg. But now he is over-priced. <br>Fame should tell the two readings apart. |
| Why the price might miss it | The average blends lagging quotes with shaded ones, and neither is visible in z. |
| Type | M |
| Formula | p_max(A) = (1/max_A)/(1/max_A + 1/max_B). k = logit p_max(A) − z (diff ✓). fam = 1[sign(k) = −sign(ΔF)], meaning the skew points at the more famous player (unchanged on swap ✓). F is MKT-18's fame. **Primary (a pair, one hypothesis):** k × (1 − fam) and k × fam (diff ✓), expected to take opposite signs, negative and positive respectively. Secondary: Bet365 shading, sh = logit p_B365(A) − z, × fam. Main effects: k, ΔF. |
| Data | `stage1_odds`: max, avg, b365, 2010–2026; fame from Stage 0. Safe. |
| Why the model cannot already do it | It has no book-level and no fame inputs. |
| Expected effect | As stated in the formula. +0.05 to +0.2 mLL. [A] by construction. |
| Kill test | Both columns span 0, or both take the same sign, in which case fame does not separate the readings. |

### MKT-16 · Sharp–soft divergence: is the profile's edge just the average lagging Pinnacle? [A; diagnostic]

| Field | Content |
|---|---|
| ID, name | MKT-16, sharp–soft split |
| Mechanism | Let s be Pinnacle's de-vigged log-odds minus the average's. <br>• If the profile's value against the average sits where Pinnacle has already moved in the profile's direction, the model's edge over the average is the average's lag. It is not information the sharp market lacks. <br>• If it sits where Pinnacle disagrees with the profile, the profile carries information beyond sharp money. <br>Whether the edge holds at bet time depends on the answer. |
| Why the price might miss it | The average lags. The question is whether the model's edge is that lag. |
| Type | S (agreement indicator) |
| Formula | s = logit p_PS − z (diff). α = 1[sign(s) = sign(N)] (context ✓: both negate). **Primary:** N × α against N × (1 − α) (diff ✓), compared with each other. Secondary: s. Main effects: N, s. |
| Data | `stage1_odds` ps_a/b, 2010 to mid-January 2026, plus the men's 2018 workbook if it is linked. Safe. |
| Why the model cannot already do it | It has no Pinnacle input. |
| Expected effect | A diagnostic: either outcome is informative. As a feature, s is worth at most the 0.7 mLL gap between the average and Pinnacle (Stage 1), less whatever calibration recovers. It cannot be a 2026 feature, since Pinnacle stops in January. |
| Kill test | As a feature only: the two coefficients are equal (their difference spans 0) and s adds nothing beyond the best model. Report the split regardless. |

### MKT-17 · Price-formation window: a short turnaround leaves a less mature close [I/A]

| Field | Content |
|---|---|
| ID, name | MKT-17, formation window |
| Mechanism | The close is the end of a process. *Observed* (line sharpening, 2026, seen on 2022+): the main-tour line settles 9–24 hours before the close. When a match follows the previous round the next day, or the same day after rain, the market has little time to absorb the last round. The close is less mature, and the statistics are priced less. |
| Why the price might miss it | Maturity takes time, and the price does not carry its own age. |
| Type | S |
| Formula | w = min over the two players of (es of this match − lf of his previous match), in days (context ✓). **Primary:** N × 1[w ≤ 1] (diff ✓). Secondary: Δ1 × 1[w ≤ 1]; z × 1[w ≤ 1]. Main effects: 1[w ≤ 1]. |
| Data | `timing.parquet` es and lf. Day resolution only (no hours), which limits the idea. Safe. |
| Why the model cannot already do it | It has no timing inputs. |
| Expected effect | Positive coefficient. Later rounds of 250s and 500s, and rain-hit weeks. +0.02 to +0.1 mLL. |
| Kill test | The primary spans 0. |

---

## D. Behavioural biases

### MKT-18 · Fallen-star premium: reputation outlives level [I]

| Field | Content |
|---|---|
| ID, name | MKT-18, fallen star |
| Mechanism | Famous players attract recreational money, most of all after their peak. The public remembers the peak, and Elo decays slowly. Their price is shorter than their current level warrants. |
| Why the price might miss it | Fame is what the public bets on. The model has age and Elo but nothing for reputation. |
| Type | W, M |
| Formula | Per player, from strictly earlier own history: <br>• F = log(1 + tour-level titles + Slam quarter-finals or better); <br>• R = career-peak overall Elo to date − current overall Elo (≥ 0). <br>**Primary:** Δ(F × R) (diff ✓). Secondary: ΔF; Δ(F × R) × (1 − v), i.e. in lopsided matches (diff × context ✓). Main effects: ΔF, ΔR. |
| Data | Stage 0 rounds and levels; Elo history. Safe by construction. |
| Why the model cannot already do it | It has no fame or peak input. |
| Expected effect | Negative coefficient: fallen stars are over-priced. Men, ageing former top-10 players. +0.05 to +0.2 mLL. If it vanishes with the Pinnacle anchor, it is soft-book shading [A]. |
| Kill test | The primary is ≥ 0 or spans 0. |

### MKT-19 · Title last week: a recency premium against a letdown [I]

| Field | Content |
|---|---|
| ID, name | MKT-19, title last week |
| Mechanism | A player who won a title, or reached a final, last week arrives with a higher Elo, a hot two-week profile and public attention. He often also brings fatigue, travel, a surface change and an emotional letdown. A special exemption ('SE') is exactly this case. The price follows the form, and the letdown comes on top. |
| Why the price might miss it | To the market and to the model, load reads as form: sets_14d gains given Elo because winners play more. The first match after a title is a specific exception. |
| Type | W |
| Formula | Per player: <br>• τ = 1[won a title at an event whose final ended (lf) at most 9 days before this match's es]; <br>• φ = the same for a lost final; <br>• first = 1[first match at this event]; <br>• sw = 1[surface differs from his last event]. <br>**Primary:** Δ(τ × first) (diff ✓). Secondary: Δ(φ × first); Δ(τ × first × sw). Main effects: Δτ, Δfirst. |
| Data | Stage 0 rounds, events, surfaces and entry; `timing.parquet`. Safe. |
| Why the model cannot already do it | sets_14d cannot tell a title run from scattered matches, nor mark the first match of the next event. |
| Expected effect | Negative coefficient. Affects about 2–4% of matches. +0.05 to +0.2 mLL. |
| Kill test | The primary is ≥ 0 or spans 0. |

### MKT-20 · Retirement hazard and settlement rules [I]

| Field | Content |
|---|---|
| ID, name | MKT-20, retirement hazard |
| Mechanism | The population counts a retirement as a loss for the player who retires. Bookmakers' settlement rules for retirements differ; some void match bets unless a set has been completed (provider rules, to verify). Where a book voids, its price is P(win, given the match completes), which over-states the chance that a player likely to retire advances. Separately, the market may under-price fragile players. With small hazards h_A and h_B independent of the score: P(A advances) ≈ (1 − h_A − h_B)·π + h_B. |
| Why the price might miss it | By construction, if a share of the books that set the price void bets on retirement. |
| Type | W × M |
| Formula | h_i = shrunk retirement rate = (retirements in the last 24 months + k·r̄)/(matches + k), with r̄ the tour rate. c = h_B(1 − π) − h_A·π. **Primary:** c/(π(1 − π)), which converts it to log-odds. It is a diff ✓: a swap gives h_A·π − h_B(1 − π) = −c, and the denominator is symmetric. Secondary: Δh; Δ(h × 1[age ≥ 30]); 1[retired in the last 30 days]. Main effects: Δh. *Theory:* the coefficient is 1 if every book voids and the hazards are right, and 0 if all books settle on advancement and fragility is priced. |
| Data | Stage 0 status (retired, walkover); the player's own history at all levels. Safe by construction. |
| Why the model cannot already do it | It has no retirement input. The frontier's pf_retired_loss_* columns are not among the 58. |
| Expected effect | Positive coefficient, about 0.2–1. *Derived:* π = 0.8, h_A = 0.05, h_B = 0.02 gives c = −0.036, which is −0.23 log-odds. Concentrated in high-hazard favourites. +0.05 to +0.3 mLL. *Prior:* the frontier's recovery family, which includes recent retirement losses, tied given the market (−0.07 men, −0.24 women). That was a different construction. |
| Kill test | The primary is ≤ 0 or spans 0. Also check the retirement rules of Pinnacle, Bet365 and OddsPortal's panel. If every book settles on advancement, only the fragility arm remains. |

### MKT-21 · Returning from injury: reputation against rust [I]

| Field | Content |
|---|---|
| ID, name | MKT-21, injury return |
| Mechanism | After an injury break, the market prices a returning player on reputation and a protected ranking ('PR'). His first matches back are rusty, and re-injury is likely. Scheduled breaks such as the off-season are common to all and priced; injury breaks are specific to the player. |
| Why the price might miss it | Reputation is visible. Rust and re-injury risk are not. |
| Type | W, U |
| Formula | Per player: <br>• L = days since his last match at any level; <br>• inj = 1[the match before the break ended in his retirement or in a walkover he gave, or his entry is 'PR']; <br>• m = matches played since his return; <br>• e_pre = Elo before the break − the tour mean. <br>**Primary:** Δ(inj × 1[L ≥ 56] × 1[m ≤ 2] × e_pre) (diff ✓). Secondary: the same without e_pre. Main effects: that term; `in_surf_layoff` (in the model). |
| Data | Stage 0 status, entry and dates; Elo. Safe. |
| Why the model cannot already do it | surf_layoff counts days since the last match on this surface, not injury; there is no entry input. |
| Expected effect | Negative coefficient. About 1–2% of matches. +0.02 to +0.1 mLL. *Prior:* the frontier's absence × Elo tied given the market. |
| Kill test | The primary is ≥ 0 or spans 0. Or the effect is the same for non-injury breaks, in which case it is rust, which has already been tested. |

### MKT-22 · Event rhythm against a cold start: qualifiers, lucky losers, seeds after a bye [I]

| Field | Content |
|---|---|
| ID, name | MKT-22, rhythm vs cold start |
| Mechanism | A qualifier or lucky loser has already played two or three matches this week on these courts, with these balls. A direct entrant, or a seed after a bye, may arrive from another surface or continent and plays his first match here. The price is built from rank and ratings, where 'Q' reads as weak, and under-weights this asymmetry. |
| Why the price might miss it | Entry status is salient and coded by rank. Acclimatisation is not quoted. |
| Type | X |
| Formula | Per player: <br>• r = matches already played at this event, qualifying included; <br>• c = 1[first match at this event] × 1[previous match on another surface, or more than 10 days earlier]. <br>**Primary:** X = r_A·c_B − r_B·c_A (diff ✓: a swap exchanges the two products and negates X). Secondary: 1[exactly one player is Q or LL] × Δr. Main effects: Δr, Δc. |
| Data | Stage 0: qualifying matches and their event ids, and entry codes Q and LL. The cartographer should check that qualifying links to its main draw. `timing.parquet`. Safe. |
| Why the model cannot already do it | surf_season and surf_layoff record surface recency, not whether a player has played here this week, nor the asymmetry between the two players. |
| Expected effect | Positive coefficient, in first and second rounds. +0.05 to +0.2 mLL. |
| Kill test | The primary is ≤ 0 or spans 0. |

### MKT-23 · Home hype: home wildcards and home players at small events [I/A]

| Field | Content |
|---|---|
| ID, name | MKT-23, home hype |
| Mechanism | Local bookmakers and patriotic money shade prices toward home players, most visibly young home wildcards. Genuine home advantage (the crowd, no travel) pushes the other way. The balance likely depends on the event's size and on the player's entry: a 250's betting pool is local, a Slam's is international. |
| Why the price might miss it | Shading is a soft-book effect, and the real home advantage may be under-weighted by sharp money. |
| Type | W, S |
| Formula | home_i = 1[player's country = event country], using Stage 4's table and code aliases. wc_i = 1[entry = WC]. **Primary:** Δ(home × wc) (diff ✓). Secondary: Δhome × (1 − 1[Slam]) (diff × context ✓). Main effects: Δhome, Δwc. |
| Data | Stage 0 country and entry; `stage4_event_country.csv` (Kingston blank; Monte Carlo coded Monaco). Safe. |
| Why the model cannot already do it | It has no country or entry inputs. |
| Expected effect | Sign open; at most +0.1 mLL. *Prior:* as a main effect, home country added nothing given the market (Stage 4). |
| Kill test | Both columns span 0. |

### MKT-24 · Calendar motivation: the week before a Slam, the weeks after a deep Slam run, points to defend [I]

| Field | Content |
|---|---|
| ID, name | MKT-24, calendar motivation |
| Mechanism | <br>• Top players treat the event before a Slam as preparation, so their effort and their rate of finishing matches fall in its late rounds. <br>• A Slam quarter-final or better is followed by fatigue and a letdown. <br>• A defending champion is motivated by the points at stake. <br>The price is set from level and form, not from incentives. |
| Why the price might miss it | Incentives are inferred, never quoted, and ratings do not know the calendar. |
| Type | W, S |
| Formula | Per player: <br>• top = 1[rank ≤ 20 at the tournament start]; <br>• pre = 1[this event ends within 8 days of a Slam main draw starting]; <br>• post = 1[reached a Slam quarter-final or better, finishing at most 21 days before es]; <br>• def = the share of his ranking points earned at this event last year. <br>**Primary:** Δ(top × pre) × 1[round ≥ QF] (diff × context ✓). Secondary: Δpost; Δdef. Main effects: Δ(top × pre). |
| Data | Stage 0 calendar, rank and rank_points. "def" needs a hand-made points table by level and round (cartographer). Safe. |
| Why the model cannot already do it | It has no calendar or incentive input. |
| Expected effect | Negative for pre and post, positive for def. +0.05 to +0.15 mLL. |
| Kill test | All columns span 0. |

### MKT-25 · Public narrative statistics: head-to-head and venue records [I]

| Field | Content |
|---|---|
| ID, name | MKT-25, H2H and venue narratives |
| Mechanism | Head-to-head records and "he always plays well here" are the most displayed pre-match statistics. Both rest on few matches, often played in old conditions. If the price over-weights them, their raw form predicts against the price once a luck-free residual is held. |
| Why the price might miss it | Display and narrative. The residual against Elo at the time removes the part the ratings already explain. *Observed* (Stage 4), given the market: the men's head-to-head rows fell below their null band, so adding them raw hurt. That may be noise, or a record the price already over-uses. |
| Type | W |
| Formula | <br>• η = the shrunk residual of their previous meetings: (results − Elo-expected) ÷ (n + k). It is a diff ✓, since A's residual is minus B's. <br>• raw = (wins_A − wins_B)/(n + 1) (diff ✓). <br>• Venue: ν_i is the shrunk residual at earlier editions of this tournament; ρ_i is the raw win rate there. <br>**Primary:** raw × 1[n ≥ 3], with η held as a main effect (diff × context ✓). Secondary: Δρ, with Δν held. Hypothesis: negative raw coefficients. |
| Data | Stage 0 meetings, and tournament ids across seasons (their continuity needs checking); Elo. Safe: strictly earlier, the players' own matches. |
| Why the model cannot already do it | It has no head-to-head or venue inputs. |
| Expected effect | Negative and small: at most +0.1 mLL. |
| Kill test | Both columns span 0. |

---

## Not proposed, and why

* **Features from Polymarket or Betfair** (early prices, volume as attention, account flow). They exist only for 2025–2026, so rule 1 makes them impossible to discover. They should be revisited once seasons beyond the test exist.
* **Cross-book standard deviation over five books** (B365, EX, LB, PS, SJ). Only 2010–2018 have them, so the 2025–2026 test could not use it. MKT-14's arbitrage measure works in every season.
* **Main effects already tested against the close** (surface Elo, surface IOS, TTT, load, conversion luck, home country and entry types alone). Only their interactions appear above.
* **Dead rubbers at the Tour Finals.** About 2–4 matches a season: too few.

## Top 8, ranked

1. **MKT-04 Serve-dominance compression.** The model cannot see the sum of serve strengths, iid arithmetic gives an 11% swing in log-odds, and the column is built from leak-proof per-player IOS. [I], usable at bet time.
2. **MKT-11 Salience-weighted evidence.** Form earned below the main tour reaches the price late, through the rank. It splits a pooled input by visibility; the men's Challenger box scores have 99% coverage.
3. **MKT-10 Rank anchoring × trajectory.** Rank is not an input, age is the strongest nudge given the price, and the women's rank signals beyond the market.
4. **MKT-03 Best-of-five leverage.** TabPFN's largest gains are at the Slams. A column scaled by theory (best of five ≈ 1.26 × the log-odds of best of three) measures the share left unpriced.
5. **MKT-07 Attention-modulated disagreement.** The direct test of the owner's hypothesis that the profile matters where the price leans on ratings, with an attention index fixed in advance.
6. **MKT-20 Retirement hazard × settlement rules.** Orthogonal by construction to prices that assume the match completes, with a theoretical coefficient between 0 and 1.
7. **MKT-05 Volatility compression.** Variances are invisible to a model built on differences, and it was the predictive frontier's best family against the market.
8. **MKT-01 Margin-aware de-vig.** A cheap, convex FLB correction tied to each match's margin, which also aligns the training anchor with margin-free exchange prices at bet time.

Next in line: MKT-02 (early season) and MKT-14 (dispersion). **Run MKT-16 regardless, as a diagnostic:** it asks whether the model's edge over the average is only the average lagging Pinnacle.

## What this file read and computed

* **Read:** the brief and team files; the market-anchoring, sharp-benchmark, Polymarket sharp-money, line-sharpening, TabPFN-thinking, meta-stack, predictive-frontier, surface-Elo-pieces, surface-rating-race and surface-IOS reports; the predictability diagnostic's README, Stage 1, Stage 4 and summary; the UFC-ideas README. No literature, web search or other round-0 file.
* **Inspected (schema only):** column names of `stage1_odds`, `stage0_matches`, `stage0_match_players`, `stage3_ratings`, `timing`, `perplayer_features`, `frontier_features`, `surface_features` and `model_inputs.json`; header rows of the tennis-data workbooks; the provider's notes.
* **Coverage counts:** box scores by tour, level and qualifying, and minutes, both for 2013–2021. The entry-code tally ran over every season, including 2025–2026, as a schema check; no choice depends on its counts.
* **Input scales:** a descriptive summary of nine model inputs over 2013–2021, used to set the Δ1 rescaling and the log(1 + n) threshold in MKT-02. **Disclosure:** that check also printed the correlation of `in_odds_logit` with `in_ratings_iid` and `in_elo_overall` (about 0.9). It touches the odds; no idea, formula or ranking uses it.
* **Arithmetic:** iid match probabilities for fixed serve-point gaps (MKT-03, MKT-04), using pure probability formulas with no data.
* **Not run:** no outcome was related to any feature, no fit, no GPU, and no Git command.
