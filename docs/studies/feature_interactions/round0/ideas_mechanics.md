# Round 0 ideas: the mechanics of points and matches

6 October 2026 · Brainstormer **MECHANICS** (Opus 5.5), working blind to the other brainstormers and the literature scout, as [team.md](../team.md) requires. These are research suggestions, not decisions.

**Labels.** **Observed** means computed here, and every observed number is outcome-free (see the next section). **Inferred** means a reading of those numbers. **Suggestion** means a proposal. Earlier studies' results are quoted with their direction: "gain, higher is better", and "tie" when the 95% interval spans zero. They come from the original, pre-repair rundowns unless a study is named.

**What was read.** No match result (`a_won`, `won`), no price (`odds_logit`, `p_mkt`) and no row from 2022 or later entered any calculation. The calculations are of two kinds:

* arithmetic on the iid point model;
* the spread of pre-match features and box-score statistics in seasons up to 2021.

## In short

* **Observed. Leverage depends on serve dominance.** Under the iid model, a fixed serve/return strength edge buys much less match log-odds when both players serve well. Relative to an average men's hard-court match (both win 62% of serve points), the leverage is:
  * 1.11 when both win 54% of serve points;
  * 0.82 at 70%;
  * 0.71 at 74%.

  The curve is the same for best of three and best of five. Within a men's surface the matchup moves leverage over 0.81–1.04 (hard courts, 5th–95th percentile). Tour, surface and indoor explain only 66% of serve dominance.
* **Observed. Dominance is a sum, which the model cannot see.** The model's inputs are differences, and with side A random a sum is uncorrelated with every difference. It also cannot rescale the price.
  * If the price ignores dominance within a surface, rescaling it is worth up to about 0.40 milli-log-loss for men (gain, higher is better), or 0.10 if the price already holds half of the effect. For women the figures are 0.06 and 0.015.
  * This is my first idea (MEC-01).
* **Observed. Two outcome-free kills.**
  * Under the iid model a service game's sensitivity splits exactly half and half between deuce-court and ad-court points, though the ad court hosts three-quarters of break points. A left-hander's ad-court slice therefore earns no extra on big points.
  * Expected points per match depend on how close the match is (which the price already holds), not on serve dominance. Attrition ideas must rest on rally pace, not on the iid model.
* **Observed. Structural terms of the serve point are real but small.** Two candidates:
  * **The free-point shield.** Aces are beyond the returner's reach: the returner's leverage falls from 0.93 to 0.56 as a server's free-point share rises from 10% to 40%.
  * **First/second-serve exposure.** It moves 1.0 point of serve points won between extreme server types.

  On real matches, after the model's 21 IOS inputs are accounted for linearly, each term keeps a standard deviation of about 0.06 match log-odds (men).
* **Observed. Venue pace is a persistent trait below the level of surface.** Adjusted for who served and who returned, a venue's ace rate carries over to its next edition at r = 0.52 (men) and 0.42 (women).
* **21 ideas, a style map, 9 ideas set aside with reasons, and a ranked top 8** (end of this file).

## What I computed before choosing

| Script (run with `./python.sh`) | Output | Reads |
|---|---|---|
| `src/eda/feature_interactions/round0/mechanics/iid_mechanics.py` | `data/studies/feature_interactions/round0/mechanics/iid_mechanics.json` | No data. The iid model (`src/eda/predictability_diagnostic/stage2_iid.py`, imported read-only) on synthetic serve-point probabilities at published tour averages |
| `src/eda/feature_interactions/round0/mechanics/feature_spread.py` | `.../feature_spread.json` | For model-frame matches up to 2021: per-player surface IOS (`data/studies/surface_ios/surface_features.parquet`), box-score counts, hands and tournament ids (`stage0_*`), and surface averages (`stage4_constants.csv`). No result or price column is read |

**Observed (iid arithmetic).**

1. **Leverage: the match log-odds per unit of serve-point log-odds edge, d logit P(match) / dΔ.**
   * Best of three: 4.78 when both serve at 62%.
   * Best of five: 5.98, exactly 1.25 times best of three at every dominance level.

   Relative to both serving at 62%:

   | Both players' serve-point rate | 0.54 | 0.58 | 0.62 | 0.66 | 0.70 | 0.74 |
   |---|---|---|---|---|---|---|
   | Leverage, relative | 1.108 | 1.066 | 1.000 | 0.915 | 0.817 | 0.712 |

   For a fixed edge in probability units (the two serve rates 0.02 apart), the match log-odds still falls from 0.43 to 0.37 between serve rates of 0.50 and 0.70.
2. **Match length.**
   * An even best-of-three match lasts 164–166 points whatever the dominance (both serving at 0.56 to 0.70). It shortens to 122–131 points when the serve rates are 0.16 apart.
   * Tiebreaks per even best-of-three match rise from 0.35 (both serving at 0.56) to 0.53 (0.63) and 0.95 (0.70).
   * Break points per service game fall from 0.59 at a serve rate of 0.62 to 0.33 at 0.70.
3. **Courts.** At every serve rate p, ∂hold/∂p on the deuce court equals ∂hold/∂p on the ad court.
   * The reason: the first six points are exchangeable (three on each court), and every deuce–advantage pair holds one point on each court.
   * The ad court hosts 0-40, 30-40 and advantage-out, about 77% of break points; the deuce court hosts 15-40.
   * Moving 2 points of serve-point rate from one court to the other changes the hold rate by at most 0.0003.
4. **First/second-serve composition.** Two servers win 62.0% of serve points against an average returner: one lands 68% of first serves, the other 54%.

   | Returner | Server landing 68% | Server landing 54% |
   |---|---|---|
   | +0.3 log-odds better only against second serves | 59.6% | 58.6% |
   | +0.3 better only against first serves | 57.3% | 58.6% |

   Against the second-serve specialist the gap is 1.0 point of serve points, 0.21 match log-odds over best of three.
5. **Free points.** A serve point is either free (an ace or an unreturned serve), with probability a, or a rally the server wins with probability r: p = a + (1 − a)·r. The log-odds elasticity of p to the returner's rally skill is:

   | Server's serve-point rate | 10% free points | 40% free points | 50% free points |
   |---|---|---|---|
   | 0.60 | 0.93 | 0.56 | – |
   | 0.66 | 0.94 | 0.66 | 0.48 |
   | 0.72 | 0.96 | 0.74 | – |

**Observed (feature spreads, model-frame matches up to 2021: 19,331 men's, 20,533 women's).**

6. **Serve dominance m** (defined under Notation) and the leverage ratio λ it implies, read off the absolute curve:
   * Tour, surface and indoor explain 65.75% of m's variance.

   | | Men, hard | Men, clay | Men, grass | Women |
   |---|---|---|---|---|
   | λ, 5th to 95th percentile | 0.81 to 1.04 | 0.91 to 1.07 | 0.76 to 0.99 | 0.98 to 1.12 |
   | Standard deviation of λ | 0.068 | 0.053 | 0.070 | 0.025 to 0.036 |

   Rescaled within each tour × surface × indoor cell, the standard deviation is 0.067 (men) and 0.026 (women).
7. **Composition.** The first/second-serve-composed serve-point edge is 99.73% (men) and 99.55% (women) linear in the model's 21 IOS inputs. The rest has a standard deviation of 0.013–0.014 serve-point log-odds, about 0.06 match log-odds.
8. **Free-point shield** (aces only, the box-score proxy):

   | | Spread of the term (serve-point log-odds) | Linear in the 21 IOS inputs | What is left, in match log-odds |
   |---|---|---|---|
   | Men | 0.050 | 94% | ≈0.06 |
   | Women | 0.031 | 94% | ≈0.04 |

   Its 1st–99th percentiles are ±0.13 (men).
9. **Cross-statistic products** (A's offence on one statistic times B's defence on another): how much of each is linear in the 21 IOS inputs (R²).

   | Product | Men | Women |
   |---|---|---|
   | First serves in × second-serve defence | 0.87 | 0.62 |
   | Double faults × second-serve defence | 0.85 | 0.67 |

10. **Venue pace.** For each venue edition, observed minus expected for the players present (from IOS), on the log-odds scale:

    | | Ace residual SD | Carry-over to the next edition | Serve-point residual SD | Carry-over | Pairs of consecutive editions |
    |---|---|---|---|---|---|
    | Men | 0.16 | r = 0.52 | 0.061 | r = 0.37 | 361 |
    | Women | 0.19 | r = 0.42 | 0.054 | r = 0.44 | 203 |

11. **Hands.**
    * Men: 24.3% of matches are a left-hander against a right-hander, 2.0% two left-handers.
    * Women: 15.2% and 0.65%.
12. **Size bound for MEC-01.** Suppose the price's log-odds ℓ were wrong by ℓ·(λ − 1) within each cell. A correct rescaling would then gain ½·E[p(1−p)·(ℓ(λ−1))²]:
    * men 0.40 milli-log-loss, or 0.10 if the price already holds half of the effect;
    * women 0.06, or 0.015.

    The price was not read: ℓ is stood in for by the input `ratings_iid`, whose spread (standard deviation 1.67, men) is wider than a price's, so the bound is generous.

**The general bound I use for "expected effect"** (inferred). A term δ in match log-odds that neither the price nor the model holds is worth about ½·E[p(1−p)·δ²] if it is exactly right. With p(1−p) ≈ 0.2:

* a spread of δ of 0.06 is worth at most 0.36 milli-log-loss;
* a spread of 0.03 at most 0.09.

Real gains sit well below these bounds, because the price holds part of each effect and the IOS ratings are estimates.

## Notation and the algebra every formula uses

* **Per-player ratings.**
  * s is a statistic: spw (serve points won), ace, df, fi (first serves in), fw (first-serve points won), sw (second-serve points won), hold, bps (break points saved).
  * O^s_P and D^s_P are player P's surface-IOS offence and defence on the match's surface (`srf_O_eff_<s>_<a|b>` and `srf_D_eff_<s>_<a|b>` in `surface_features.parquet`, both log-odds).
  * μ_s is the log-odds of the tour × surface average (`stage4_constants.csv`, "surface average").
* **Expected rates.**
  * π^s_{P→Q} = σ(μ_s + O^s_P − D^s_Q) is the expected rate of statistic s when P serves to Q (IOS's own predictor).
  * p_{P→Q} = π^spw_{P→Q}.
* **Differences and sums.** Δx = x_A − x_B; Σx = x_A + x_B.
* **The iid model.** P_iid(p_A, p_B; f) is `stage2_iid.match_win` under the match's format f: best of three or five, and the deciding-set rule from `stage2_slam_final_set_rules.csv`. P_iid(p_B, p_A) = 1 − P_iid(p_A, p_B) (tested in Stage 2).
* **Serve dominance.** m_AB = μ_spw + ½(ΣO^spw − ΣD^spw).
* **Leverage.** L(m) is the leverage curve (`iid_mechanics.json`). λ = L(m)/L̄_c, where L̄_c is the mean of L over the training seasons' matches in the cell c = tour × surface × indoor.
* **Swap.** A ↔ B. Anti: the feature changes sign. Sym: the feature is unchanged.

**Algebra** (from the [brief](../brief.md)):

* x_A·y_B − x_B·y_A = ½(Δx·Σy − Σx·Δy).
* f(A) − f(B) for a non-linear f needs the levels, not only Δ.
* With side A random, E[Σx·Δy] = 0: every sum is invisible to the model except through tour, surface, indoor and the two surface-switch pairs.

**Under the additive iid model, style alone does nothing** (inferred, exact). With logit p_A = μ + O_A − D_B and logit p_B = μ + O_B − D_A, the match depends only on two quantities:

* strength, Δ(O + D);
* dominance, Σ(O − D).

The style contrast Δ(O − D) ("server-type against returner-type", at equal strength and dominance) does not enter. Any style effect beyond strength therefore needs either the leverage (a sum) or a departure from additivity: free points, the composition of the serve point, hand, venue, or style pairs.

**Timing classes.**

* **Own-order:** each player's own matches in order, each result counted from its latest possible finish plus a day. Safe by construction.
* **Leak-proof IOS:** inherits `surface_features.parquet`, which was solved on the match clock and passed the real-date probe.
* **Field:** combines different players' results. Needs `data/studies/match_timing/timing.parquet` and `src/eda/match_timing/probe.py`.

New box-score-derived columns must be joined to the model frame through `data/studies/data_continuity/rebuilds/2026-10-07T0005Z/id_map.csv` (Stage 0 was rebuilt on 6 Oct and some ids changed).

## A style map (inferred directions only)

| Matchup | Mechanism | Who an additive, average-leverage view misprices |
|---|---|---|
| Big server against big server | Low leverage (λ ≈ 0.8); about one tiebreak per best-of-three match | The favourite is priced too short |
| Returner against returner (clay; women generally) | High leverage (λ ≈ 1.1) | The favourite is priced too long |
| Elite returner against big server | The free points shield the server from return skill | The returner is overrated |
| Elite returner against server with few free points | Full exposure to return skill | The returner is underrated |
| Server with a low first-serve percentage against a second-serve attacker | More second serves exposed | The low-percentage server is overrated |

## The ideas

### A. Match character and the price's leverage

#### MEC-01 · Serve-dominance leverage of the price

| Field | Content |
|---|---|
| ID, name | MEC-01 · Serve-dominance leverage of the price |
| Mechanism | **How a strength gap converts into a match result depends on serve dominance** (observed, item 1). With 62% serve-point rates, a unit serve-point log-odds edge buys 4.78 match log-odds over best of three (5.98 over best of five); at 70% it buys 0.82 of that; at 54%, 1.11.<br>• Two big servers hold most games and play about one tiebreak per best-of-three match. A set hinges on a dozen points, so the same strength gap buys less.<br>• Two returners break often, and the stronger player turns his edge into games more reliably. |
| Why the price might miss it | **The usual sources of a price apply one average leverage.** Prices built on results-based ratings (Elo, rankings, form) map strength to probability with one average curve.<br>• "Big-server matches are coin flips" is folklore; nobody publishes the size.<br>• Dominance varies inside a surface: men's hard courts span λ 0.81–1.04 (observed, item 6), and tour × surface × indoor explain only 66% of it. A price that uses the surface but not the players' dominance is too long on the favourite in serve-dominated matchups and too short in return-dominated ones. |
| Type | **M × S** |
| Formula | **Inputs.** m_AB = μ_spw + ½(O^spw_A + O^spw_B − D^spw_A − D^spw_B), and λ_AB = L(m_AB) / L̄_c.<br>**Arm (a), primary:** x = ℓ·(λ_AB − 1), with ℓ = `odds_logit`.<br>**Arm (b):** λ_AB as a context column.<br>**Swap:** m and λ are sym, ℓ is anti, so x is anti ✓.<br>**Pre-declared direction:** if the true log-odds are ℓ·(1 + γ(λ − 1)), then γ > 0 (the price under-adjusts). γ < 0 would mean it over-adjusts; that is still usable, so the test is two-sided. |
| Data | Surface IOS for spw, A and B (`surface_features.parquet`); μ from `stage4_constants.csv`; L from `iid_mechanics.json` (best of three and five share the relative curve). L̄_c from training seasons only, refitted each walk-forward season. **Timing:** leak-proof IOS. Coverage: every model match. |
| Why the model cannot already do it | m is a sum, uncorrelated with every difference. The model reaches it only through tour, surface and indoor (66%).<br>`ratings_iid` and `ios_points_short` apply leverage to their own strength edges, never to the price. ℓ·λ is not a function of the inputs. |
| Expected effect | **Men.** Bound 0.40 milli-log-loss (gain, higher is better) if the price ignores dominance within the cell, 0.10 if it holds half (observed, item 12).<br>• **Women:** at most 0.06 (λ's spread is a third of the men's).<br>• **Where:** men's grass, fast and indoor hard courts, and men's clay matches between two returners.<br>Realistic: 0.05–0.15 (men). |
| Kill test | **Screen:** discovery 2014–2021, cross-fitted by season, per tour. A logistic regression of the result on [the current best model's out-of-sample log-odds, x], against the same without x.<br>**Placebo:** λ shuffled within tour × surface × season.<br>**Kill** if the men's gain is under 0.05 milli-log-loss, or not above the placebo, or γ's 95% interval spans 0. |

#### MEC-02 · Four sums: let the model build cross-player products itself

| Field | Content |
|---|---|
| ID, name | MEC-02 · Four sums as match-character columns |
| Mechanism | Every bilinear matchup (A's x against B's y, minus the reverse) equals ½(Δx·Σy − Σx·Δy). The model has every Δ and no Σ.<br>Four sums with a point-structure meaning, given as context, would let TabPFN form the cross-player terms of MEC-01, -04, -06 and -07 itself:<br>• both players' serve, ΣO^spw;<br>• both players' return, ΣD^spw;<br>• free points, ΣO^ace;<br>• second-serve exposure, ΣO^fi. |
| Why the price might miss it | It inherits whatever cross-player terms the price lacks. This is a representation, not a new fact. |
| Type | **S** |
| Formula | σ1 = ΣO^spw, σ2 = ΣD^spw, σ3 = ΣO^ace, σ4 = ΣO^fi, each centred on its training-season mean in the tour × surface cell. Enter as context columns.<br>**Swap:** sym ✓; TabPFN's products Δx·σk are anti. |
| Data | Surface IOS. **Timing:** leak-proof IOS. |
| Why the model cannot already do it | Sums are orthogonal to differences. The only cross-player terms present are the seven same-statistic `prod_<s>` (O_A·(−D_B) − O_B·(−D_A)). |
| Expected effect | Unknown. At most the combined effect of MEC-01, -04 and -06.<br>**Risk:** today's match context carries about nothing of TabPFN's adjustment, so it may ignore the sums. |
| Kill test | **Local TabPFN arm** against base on the 2019–2021 validation windows, with a placebo arm (sums shuffled within tour × surface × season). Kill if the gain is under 0.05 milli-log-loss, or not above the placebo.<br>**EDA proxy:** a ridge-penalised logistic regression with the 21 IOS Δs times σ1–σ4, beyond the model's out-of-sample forecast. |

#### MEC-03 · Venue pace from earlier editions

| Field | Content |
|---|---|
| ID, name | MEC-03 · Leak-proof venue pace, interacting with each player's serve/return shape |
| Mechanism | **Pace differs inside a surface**: courts, balls, altitude and roofs (Indian Wells against Shanghai; Monte Carlo against Madrid at 650 m). Observed (item 10): adjusted for who played, a venue's ace residual carries over to its next edition at r = 0.52 (men) and 0.42 (women); serve points at 0.37 and 0.44.<br>**Two routes:**<br>(i) A persistent serve-point shift of about 0.04 log-odds moves λ by only about 2%: small through MEC-01.<br>(ii) The main route is style. Fast venues raise free points, which shield big servers (MEC-04) and amplify the serve half of the profile. |
| Why the price might miss it | Published speed indices exist, so part of this is priced. A leak-proof, IOS-adjusted venue shift crossed with each player's shape is not standard.<br>The model knows surface and, for men only, indoor. The women's `in_indoor` is empty. |
| Type | **S** (× Δ) |
| Formula | **Edition residual:** R_j = logit(aces_j/points_j) − logit(expected aces_j/points_j), the expectation summing π^ace over the players present.<br>**Venue pace:** v_e = Σ_j w_j n_j R_j / (Σ_j w_j n_j + K_v), over earlier editions with lf < the target's es; w_j = 2^(−years/2); K_v fixed in advance (2,000 serve points). The current edition's earlier days are added the same way.<br>**Inputs:** v_e (context); v_e·ΔO^ace and v_e·ΔD^spw (anti ✓). The serve-point analogue of v_e is added into m for MEC-01. |
| Data | `stage0` box scores and tournament ids. The venue key is the id after the year; check moved, renamed and cross-tour ids. Surface IOS for expectations. **Timing:** field (leak-proof clock, `probe.py`). |
| Why the model cannot already do it | Venue pace is a field quantity shared by both players, not a player difference. The model has only surface and indoor. |
| Expected effect | Big servers gain at fast venues (positive coefficient on v·ΔO^ace).<br>**Size:** men, hard and indoor courts and altitude; at most 0.1 milli-log-loss.<br>**Prior:** a thinner proxy (the same edition's earlier days only, shrunk with 800 points) tied: predictive_frontier event speed × style, men, +0.07 [−0.15, +0.30] given Pinnacle (gain, higher is better; a tie). |
| Kill test | (1) **Outcome-free:** on 2014–2021, v_e from earlier editions must forecast the edition's own residual at r ≥ 0.3.<br>(2) **Screen:** the two products add under 0.05 milli-log-loss beyond the model's out-of-sample forecast → kill. |

### B. The structure of the serve point

#### MEC-04 · The free-point shield

| Field | Content |
|---|---|
| ID, name | MEC-04 · Free-point shield: aces are beyond the returner's reach |
| Mechanism | **Returners act mainly on rallies.** A serve point is free (an ace, or a serve not returned) or a rally, and the returner's skill acts mainly on the rally. With p = a + (1 − a)·r, the log-odds elasticity of p to return skill falls from 0.93 at 10% free points to 0.56–0.66 at 40% (observed, item 5).<br>• IOS assumes elasticity 1 for every server (y = O − D).<br>• So an elite returner takes less off a big server than IOS says, and more off a server with few free points.<br>• **Mirror:** a returner whose strength is suppressing aces (D^ace) is worth more against big servers. |
| Why the price might miss it | Point models combine aggregate serve and return percentages additively; Elo knows only results.<br>"Big server against elite returner" is a famous narrative with no published number for how much of a server's game is out of reach. |
| Type | **C / X** |
| Formula | For P serving to Q:<br>• a = π^ace_{P→Q}; a0 = σ(μ_ace + O^ace_P); p0 = σ(μ_spw + O^spw_P); r0 = (p0 − a0)/(1 − a0).<br>• r = σ(logit r0 − k·D^spw_Q), with k = p̄(1−p̄)/((1−ā)·r̄(1−r̄)) from the cell averages, so that the mean elasticity is 1.<br>• p^struct = a + (1 − a)·r; correction c_{P→Q} = logit p^struct − logit p_{P→Q}.<br>**Feature:** x = c_{A→B} − c_{B→A} (serve-point log-odds), or composed: x′ = logit P_iid(p^struct_{A→B}, p^struct_{B→A}; f) − logit P_iid(p_{A→B}, p_{B→A}; f).<br>**Swap:** c_{A→B} and c_{B→A} exchange, so x and x′ are anti ✓.<br>**Rich arm:** free points = aces + serves not returned, from shot-level "returns put in play" (split-half 0.86–0.91). |
| Data | Surface IOS for ace and spw (held). **Timing:** leak-proof IOS.<br>The rich arm needs a returns-in-play IOS (field: leak-proof clock and probe) on about 17,000 men's matches with point data, mostly Slams and charted matches. |
| Why the model cannot already do it | The term is cross-statistic (A's ace offence times B's serve-point defence) plus curvature. `prod_ace` crosses aces with aces only.<br>94% of it is linear in the 21 IOS inputs. The rest, about 0.06 match log-odds (men) and 0.04 (women), needs both players' levels (observed, item 8). |
| Expected effect | Positive: it favours the big server against strong returners.<br>• **Where:** men > women; grass and fast hard courts.<br>• **Size:** bound about 0.35 milli-log-loss (men) if wholly unpriced; realistic 0–0.1; more with the rich arm. |
| Kill test | (1) **Statistic level** (no winners): on 2014–2021 matches, compare the matchup's serve points won under p^struct and under the additive IOS (log loss per serve point). Kill if the gain is under 0.02 milli per point, or if the fitted returner elasticity does not fall with the server's ace share.<br>(2) **Screen:** under 0.05 milli-log-loss beyond the model's out-of-sample forecast. |

#### MEC-05 · The profile composed through the iid model

| Field | Content |
|---|---|
| ID, name | MEC-05 · The surface-IOS profile composed into a match probability |
| Mechanism | **The model's strongest family never passes through the point-to-match map.** The long-memory surface IOS profile enters as linear differences and same-statistic products. The map is non-linear in the levels: it rescales the edge by dominance (MEC-01) and builds the serve point from its parts, p = fi·fw + (1 − fi)·sw, each part an IOS matchup. |
| Why the price might miss it | The profile's opponent-adjusted, per-statistic ratings are the model's private information (where its edge comes from). Composing that private information correctly sharpens what the model already adds over the price. |
| Type | **C** |
| Formula | **Parts:** fi = π^fi_{P→Q}, fw = π^fw_{P→Q}, sw = π^sw_{P→Q}; p^c_{P→Q} = fi·fw + (1 − fi)·sw.<br>**Feature:** x = logit P_iid(p^c_{A→B}, p^c_{B→A}; f).<br>**Variant:** x_res = x − logit P_iid(p_{A→B}, p_{B→A}; f), the composition alone.<br>**Swap:** P_iid(p_B, p_A) = 1 − P_iid(p_A, p_B), so x is anti ✓. |
| Data | Surface IOS for fi, fw and sw; `stage2_iid`; the deciding-set rules. **Timing:** leak-proof IOS. |
| Why the model cannot already do it | The composed edge is 99.7% linear in the 21 inputs. The remainder (about 0.06 match log-odds, observed, item 7) depends on levels, for example A's first-serve rate times B's second-serve return.<br>`ratings_iid` and `ios_points_short` are composed, but from other systems' total serve-point ratings (Stage 3 online ratings; short-memory IOS), not from the profile TabPFN leans on most. |
| Expected effect | Positive on x_res. Bound about 0.3 milli-log-loss; realistic 0–0.1. Women relatively more: their cross products are less linear in the inputs (R² 0.62 against 0.87 for men). |
| Kill test | (1) **Statistic level:** on 2014–2021 serve points, p^c no better than the additive spw IOS (under 0.02 milli per point) → kill.<br>(2) **Screen:** x_res under 0.05 milli-log-loss beyond the model's out-of-sample forecast. |

#### MEC-06 · Second-serve exposure × the returner's second-serve specialisation

| Field | Content |
|---|---|
| ID, name | MEC-06 · First-serve percentage × second-serve return specialisation |
| Mechanism | **Exposure meets specialisation.** A server who lands few first serves plays more points on his second serve. A returner who is specifically strong against second serves, relative to first, collects them.<br>Observed (item 4): equal-strength servers landing 68% and 54% of first serves differ by 1.0 point of serve points (0.21 match log-odds) against a second-serve specialist; the order flips against a first-serve specialist. |
| Why the price might miss it | Aggregate serve-percentage-against-return-percentage models and Elo have no exposure × specialisation cross. Viewers see "first-serve %" and "good returner" separately. |
| Type | **X** |
| Formula | **Specialisation of a returner Q,** in serve-point probability units: c_Q = w2·D^sw_Q − w1·D^fw_Q, with w1 = f̄w(1−f̄w) and w2 = s̄w(1−s̄w) from the cell averages.<br>**Feature:** x = [(f̄i − π^fi_{B→A})·c_A − (f̄i − π^fi_{A→B})·c_B] / (p̄(1−p̄)). Positive favours A.<br>**Derivation:** first-order expansion of p = fi·fw + (1−fi)·sw in the returner's D's; this is the level-dependent remainder.<br>**Swap:** anti ✓. MEC-05 contains it; this is its targeted single column. |
| Data | Surface IOS for fi, fw and sw. **Timing:** leak-proof IOS. |
| Why the model cannot already do it | It needs A's first-serve level times B's specialisation level. The raw product O^fi × D^sw is only 87% (men) and 62% (women) linear in the 21 inputs. |
| Expected effect | Positive coefficient on x. Women > men: the women's second serve is weaker (45% of second-serve points won against 50%). At most 0.1 milli-log-loss. |
| Kill test | **Serve-point level:** on 2014–2021 matches, regress the residual of the matchup's serve-point log-odds (actual minus additive IOS) on (f̄i − π^fi)·c_returner. Kill if the slope's 95% interval includes 0.<br>Then the usual screen. |

#### MEC-07 · Second-serve risk against second-serve attack

| Field | Content |
|---|---|
| ID, name | MEC-07 · Risky second servers against second-serve attackers |
| Mechanism | **A server facing a second-serve attacker must choose:** play safe and lose the rally, or go for it and double-fault. A server who already takes risk on the second serve (many double faults, many second-serve points won) has less to adjust.<br>The sign is not known in advance: risk may shield, or double faults may multiply under pressure. |
| Why the price might miss it | No public number crosses double-fault style with the opponent's second-serve return. |
| Type | **X** |
| Formula | **Risk index:** ρ_P = z(O^df_P) + z(O^sw_P), each standardised within tour × surface.<br>**Feature:** x = ρ_A·D^sw_B − ρ_B·D^sw_A.<br>**Swap:** anti ✓. Two-sided. |
| Data | Surface IOS for df and sw. **Timing:** leak-proof IOS. |
| Why the model cannot already do it | Cross-statistic and level-dependent. O^df × D^sw is 85% (men) and 67% (women) linear in the inputs; `prod_df` and `prod_second_won` are same-statistic products. |
| Expected effect | Small, either sign. Women more (double faults 5.3% of serve points against 4.1%). |
| Kill test | **Statistic level:** the log-odds residuals of second-serve points won and double faults (actual minus IOS) against ρ_server × D^sw_returner. Kill if both slopes' intervals include 0. |

### C. Scoring luck

#### MEC-08 · Conversion luck: results beyond the points (player and pair)

| Field | Content |
|---|---|
| ID, name | MEC-08 · Conversion luck |
| Mechanism | **Points become results through a noisy map.** Stage 2:<br>• 4.4% of men's matches go to the player who won fewer points;<br>• tiebreak and break-point over-performance barely carry over (split-half 0.05–0.06 for 25+ matches a half);<br>• winners won 80% of tiebreaks against 60% expected.<br>Rankings, Elo, win streaks and head-to-head counts treat that luck as skill. |
| Why the price might miss it | Results drive the visible numbers, and so public money.<br>**Caution:** the 52-week tiebreak record added −0.02 [−0.12, +0.07] milli-log-loss given the odds (men; a tie, original rundown). The market discounts tiebreak luck at least linearly.<br>Untested: the broader, short-memory luck index (all scoring luck) and the pair arm. |
| Type | **W** (pair arm: **M / X**) |
| Formula | **Per earlier completed match k of player P:** e_k = y_k − σ(β_f·(t_k − ½)), with y_k = 1 if P won and t_k = P's share of all points. β_f is fitted per tour and best-of on completed matches of 2010–2018. It is an in-match relation; Stage 2's fit cannot be reused, because it includes 2025–2026.<br>**Index:** Λ_P = Σ_k 2^(−age_k/13 weeks)·e_k / (Σ_k 2^(−age_k/13 weeks) + 3).<br>**Arm (a):** x = Λ_A − Λ_B.<br>**Arm (b), head-to-head luck:** x_h = Σ_meetings e^A_k / (n_AB + 2), with e^B_k = −e^A_k.<br>**Swap:** both anti ✓. |
| Data | `stage0_match_players` (points won and played) and earlier results. **Timing:** own-order; each earlier result counts from its lf + 1. Coverage: box-score histories, about 99% on the main tour. |
| Why the model cannot already do it | The model has results-based Elo (`elo_games`, `elo_overall`, `elo_surf_offset`) and points-based aggregates (`adjperf_tpw_2w`, `points_52w`, `ios_points_short`).<br>Their linear contrast mixes luck with level, and weights luck by Elo's K-factor and long memory rather than the market's short one. There is no head-to-head input at all. |
| Expected effect | Negative coefficient (lucky players are priced too short). 0–0.15 milli-log-loss, both tours. Best of three more than best of five. |
| Kill test | If player-level e carries over between split halves at r > 0.2, it is skill: reframe the idea.<br>Otherwise kill if the gain beyond the model's out-of-sample forecast is under 0.05 milli-log-loss, or its interval spans 0. |

### D. Opponent-specific deviations

#### MEC-09 · Returner-by-server-hand deviation

| Field | Content |
|---|---|
| ID, name | MEC-09 · How each player serves to, and returns against, left-handers |
| Mechanism | **The left-hander reverses the usual spin geometry.** The slice wide on the ad court and the kick on the deuce court both go to a right-hander's backhand. Some right-handers handle it, some do not; it is a per-returner deviation.<br>Observed (item 3): the iid game weights deuce and ad courts exactly equally, so there is no break-point bonus. The effect is an average serve/return deviation, specific to the matchup. |
| Why the price might miss it | The market knows a player is left-handed. "Struggles against lefties" is folklore for a few stars, with no measured per-player number.<br>Earlier crude tests found nothing (original rundown, given the odds, a gain, higher is better):<br>• the left-handed indicator: −0.04 [−0.13, +0.06] (men; a tie);<br>• the career raw record against the opponent's hand: −0.02 [−0.07, +0.03] (men; a tie), −0.03 [−0.06, −0.00] (women; worse, its interval just below zero). |
| Type | **X** |
| Formula | **Extended IOS:** y_{S→R} = μ + O_S − D_R + E_S·L_R − F_R·L_S, with L = 1 for a left-hander, and E and F ridge-shrunk towards 0 (penalty at least 10 times the base one, as for surface deviations).<br>**Feature:** x = (E_A L_B − F_B L_A) − (E_B L_A − F_A L_B), in serve-point log-odds, times L(m) for match log-odds. Swap: anti ✓.<br>**Arm (b):** Δlefty, so TabPFN can cross it with surface.<br>**Arm (c), exposure:** e_P = the share of P's 52-week opponents who were left-handed; x_e = L_A(ē − e_B) − L_B(ē − e_A), anti ✓. |
| Data | `stage0` hand (known for 99.7% of men's and 98% of women's main-tour matches) and box scores. **Timing:** field: a new IOS solve on the leak-proof clock, plus `probe.py`. Applies to 24% of men's and 15% of women's matches. |
| Why the model cannot already do it | Hand is not among the 58 inputs. The deviation is per player and needs the opponent's hand. |
| Expected effect | Only in left-hander against right-hander matches. At most 0.1 milli-log-loss overall. |
| Kill test | **Persistence first (no winners):** across right-handed returners with at least 1,500 return points against left-handers, correlate F_R between odd and even seasons. Kill if under 0.15, or not above a placebo with shuffled hands. |

#### MEC-10 · Style-pair residual table

| Field | Content |
|---|---|
| ID, name | MEC-10 · A pooled k × k table of style-against-style serve residuals |
| Mechanism | Beyond the structural terms, some style combinations may deviate systematically from additive IOS. Pooling players into a few styles makes a matchup effect estimable where pair histories are thin. |
| Why the price might miss it | Style labels are folklore; no pooled, opponent-adjusted style-pair table is public. |
| Type | **X** |
| Formula | **Styles:** each player at each match date is clustered into k = 6 styles (fixed in advance) by k-means on standardised (O^spw, D^spw, O^ace, O^fi, O^df, hand). The centroids are fitted on 2010–2016 and frozen.<br>**Table:** τ_ij = the shrunk mean, over earlier matches, of the serve-point log-odds residual (actual minus IOS) for style i serving to style j.<br>**Feature:** x = τ_{s(A)s(B)} − τ_{s(B)s(A)}. Swap: anti ✓. |
| Data | IOS and box scores. **Timing:** field (leak-proof clock, probe). |
| Why the model cannot already do it | A style pair needs both players' levels on several statistics. |
| Expected effect | Small; at most 0.05 milli-log-loss. |
| Kill test | Kill if τ fitted on 2010–2016 correlates under 0.3 with τ fitted on 2017–2021, cell by cell, or if the out-of-sample serve-point log loss gains under 0.02 milli per point. |

#### MEC-11 · Points-based head-to-head residual

| Field | Content |
|---|---|
| ID, name | MEC-11 · The pair's serve points beyond IOS in earlier meetings |
| Mechanism | **Head-to-head results are strength plus luck.** The points inside earlier meetings carry evidence of a style matchup with far less noise: about 150 points against one result. |
| Why the price might miss it | The public reads head-to-head *results*. Earlier tests of the results form were null or worse given the odds (men, 52 weeks: −0.40 [−1.22, +0.43], a tie; on the surface −0.59 [−1.06, −0.12], worse; a gain, higher is better). A points form is the only one with a mechanism. |
| Type | **X** |
| Formula | **Per earlier meeting k:** u^A_k = A's serve points won minus π^spw_{A→B} (as of that date) times A's serve points; u^B_k likewise.<br>**Feature:** r_AB = Σ_k (u^A_k − u^B_k) / (Σ_k points_k + 1,000). Swap: r_BA = −r_AB ✓. |
| Data | `stage0` box scores. **Timing:** the pair's own meetings in order (safe); the expectations use leak-proof IOS. Pairs met before in about 60% of main-tour matches. |
| Why the model cannot already do it | No pair-specific input exists. |
| Expected effect | Tiny. |
| Kill test | For pairs with at least 3 meetings, the correlation between the residual of meetings 1 to k−1 and of meeting k. Kill if under 0.05. |

#### MEC-12 · Kick serve against a short returner

| Field | Content |
|---|---|
| ID, name | MEC-12 · Second-serve quality × the returner's height |
| Mechanism | **A strong kick second serve bounces above a short returner's strike zone,** especially a one-handed backhand's. A tall returner takes it at shoulder height.<br>**Note (inferred, exact):** a height × height term cancels after antisymmetrisation (a = h_A − h̄, b = h_B − h̄ give −ab − (−ab) = 0). "Tall against short" is only a symmetric character; an asymmetric partner is needed. |
| Why the price might miss it | Height is public but never crossed with second-serve quality. |
| Type | **X** |
| Formula | x = O^sw_A·(h̄ − h_B) − O^sw_B·(h̄ − h_A), with heights in cm centred on the tour mean. Swap: anti ✓. |
| Data | `stage0` height: men 99.5% of main-tour matches; women 80%, and only 37% in 2022–2026, so men only. **Timing:** static height and leak-proof IOS. |
| Why the model cannot already do it | Height is not an input; the term needs levels. |
| Expected effect | Tiny; men. |
| Kill test | **Statistic level:** the slope of second-serve points won (residual from IOS) on O^sw_server × (h̄ − h_returner). Kill if its interval includes 0. |

#### MEC-13 · Indoor deviation in the serve/return profile

| Field | Content |
|---|---|
| ID, name | MEC-13 · Per-player indoor deviations |
| Mechanism | **Indoors there is no wind or sun and a stable temperature.** First serves land more and tosses are steady. Some players (high tosses, wind-sensitive kick serves) gain more than others.<br>The surface IOS study listed "indoor hard as its own surface" as a follow-up and did not test it. |
| Why the price might miss it | Indoor specialists are partly folklore. The women's model has no indoor column at all. |
| Type | **S** × a new difference |
| Formula | **Extended IOS:** y = μ + O_S − D_R + I·(G_S − H_R), with I = 1 indoors.<br>**Feature:** x = I·[(G_A − H_B) − (G_B − H_A)] = I·(ΔG + ΔH). Swap: anti ✓. |
| Data | `stage0` indoor flag (check the women's coverage first). **Timing:** field (a new IOS term, leak-proof clock, probe). |
| Why the model cannot already do it | There is no per-player indoor deviation. |
| Expected effect | Small. **Prior:** surface deviations, real for the statistics, were priced in (surface IOS against base: +0.01 [−0.10, +0.13] milli-log-loss, a tie). |
| Kill test | Kill if G and H carry over between split seasons at r < 0.15. |

### E. Within-player non-linear terms

#### MEC-14 · Age reshapes the profile: return and rally decay first

| Field | Content |
|---|---|
| ID, name | MEC-14 · Age × the profile's shape |
| Mechanism | **Different skills age at different rates.** Serving holds up with age; movement, the base of return and rally, declines earlier. Young players' serve power arrives later than their movement.<br>The long-memory IOS (half-lives of 52–104 weeks) therefore lags most for ageing return-and-rally players, overrating them, and for young return-first players, underrating their coming serve. |
| Why the price might miss it | It is the model that errs here. The price sees recent results that already show the decline; TabPFN leans on the lagging profile.<br>The screen tests against the model's own forecast, so correcting the model's bias counts. |
| Type | **W** |
| Formula | **Per player:** g_P = (age_P − 28)·[(D^spw_P − D̄_c) − (O^spw_P − Ō_c)].<br>**Feature:** x = g_A − g_B. Swap: anti ✓.<br>One pre-declared variant: a hinge, (age − 29)₊. |
| Data | Age (`stage0`) and surface IOS. **Timing:** leak-proof IOS; age is static. |
| Why the model cannot already do it | It needs A's age times A's own profile shape. The model has Δage, Δage² and Δ of each O and D, never their within-player products. |
| Expected effect | Negative coefficient. Men mainly; 0.05–0.15 milli-log-loss. |
| Kill test | **Outcome-free first:** the drift of IOS forecast residuals with age (next-match return points won against serve points won, players 29 and older). Kill if the return residual does not drift more negative than the serve residual. Then the screen. |

#### MEC-15 · Early in a surface season, return-heavy profiles are stalest

| Field | Content |
|---|---|
| ID, name | MEC-15 · Surface switch × the profile's shape |
| Mechanism | **Serve skill transfers across surfaces better than return skill** (opponent-adjusted, hard to clay: 0.69 against 0.62 for men, 0.64 against 0.54 for women; Stage 3). So in a player's first matches on a surface, a return-heavy profile is the stalest. |
| Why the price might miss it | Uncertain. The price may track early-season results directly. |
| Type | **W / U** |
| Formula | **Per player:** g_P = q_P·[(D^spw_P − D̄_c) − (O^spw_P − Ō_c)], with q_P the model's own first-matches-on-the-surface flag (`surf_season_a/b`).<br>**Feature:** x = g_A − g_B. Swap: anti ✓ (q is exchanged). |
| Data | The model frame and surface IOS. **Timing:** leak-proof IOS. |
| Why the model cannot already do it | TabPFN can form (q_A + q_B)·Δ, but not q_A·shape_A − q_B·shape_B, because shape enters only as differences. |
| Expected effect | Small. **Prior:** the surface study's early-season subgroup did not replicate (validation +0.42 [+0.02, +0.81], test +0.05 [−0.27, +0.36], a tie; a gain, higher is better). |
| Kill test | Kill if the screen gain is under 0.05 milli-log-loss in early-season matches. |

#### MEC-16 · Height as the serve prior for thin histories

| Field | Content |
|---|---|
| ID, name | MEC-16 · A height-informed shrinkage target for young servers |
| Mechanism | **For a player with few rated serve points,** IOS shrinks the serve towards the tour average. Height predicts the serve and where it is heading, so young tall players' serves are underrated in their first seasons. |
| Why the price might miss it | Prices of young players and qualifiers rest on rankings and recent results. |
| Type | **U / W** |
| Formula | **Prior:** O^ace,prior_P = β_h·(h_P − h̄), with β_h fitted on established players' O^ace against height, up to 2018 (no outcomes).<br>**Blend:** Õ^ace_P = (n_P·O^ace_P + K_h·O^ace,prior_P) / (n_P + K_h), with n_P = rated serve points.<br>**Feature:** x = ΔÕ^ace − ΔO^ace. Swap: anti ✓. |
| Data | Height (men only, as for MEC-12) and IOS. **Timing:** static height and leak-proof IOS. |
| Why the model cannot already do it | Height is not an input, and the shrinkage target is fixed at the average.<br>**Prior:** the height difference added −0.02 [−0.10, +0.06] milli-log-loss given the odds (men; a tie). That was a main effect over everyone; this idea targets thin histories only. |
| Expected effect | Concentrated on young men; at most 0.05 milli-log-loss overall. |
| Kill test | **Statistic level:** for players with fewer than 1,000 rated serve points, height must improve next-match ace and serve-point forecasts by 0.05 milli per point or more; otherwise kill. |

### F. Variance

#### MEC-17 · Volatility: within-match swings and between-match serve variance

| Field | Content |
|---|---|
| ID, name | MEC-17 · Player volatility compresses the price |
| Mechanism | **The iid model draws every point at fixed rates; real matches swing.** For the women, the points share decides less than the pure-luck replay predicts (log loss 0.118 against 0.103; Stage 2).<br>Averaging P_iid over uncertain day rates shrinks favourites towards 50%.<br>**Two measures per player:**<br>(i) within a match, the excess dispersion of the games share across sets beyond the iid dispersion at that match's own serve rates;<br>(ii) between matches, the excess variance of match-level serve-point log-odds residuals (actual minus IOS) beyond binomial. |
| Why the price might miss it | "Erratic" players are named by commentators, but the size of their volatility is not measured. |
| Type | **U / M** |
| Formula | V_P = the shrunk, decayed mean of measure (i), with (ii) as a second arm.<br>**Symmetric character:** v = V_A + V_B.<br>**Primary arm:** x = ℓ·(v − v̄_c), with a negative coefficient pre-declared.<br>**Secondary arm:** V_A − V_B.<br>**Swap:** v is sym; x and V_A − V_B are anti ✓. |
| Data | `stage0` set scores and box scores. **Timing:** own-order (safe). |
| Why the model cannot already do it | There is no variance input; v is a sum.<br>**Overlap:** predictive_frontier's reliability/variability family (excess residual dispersion), +0.23 [−0.04, +0.50] milli-log-loss given Pinnacle for men (a tie). This idea adds the within-match measure and the price-compression form. |
| Expected effect | Women > men; at most 0.2 milli-log-loss. |
| Kill test | **Outcome-free:** kill measure (i) if its split-half carry-over is 0.1 or below, or not above the iid replay. Then the screen. |

### G. Pressure, sequence and attrition

#### MEC-18 · Big-point return skill × the scarcity of break points

| Field | Content |
|---|---|
| ID, name | MEC-18 · Big-point return play weighted by how rare break points will be |
| Mechanism | **Big-point return play is the one big-point skill that persists beyond luck** (Grand Slam point by point, split-half 0.21 men and 0.19 women at 10+ matches a half, against 0.01 and −0.01 in the replays).<br>In serve-dominated matchups break points are scarce (0.33 per service game at a 70% serve rate, against 0.59 at 62%), and each one decides a set. |
| Why the price might miss it | Big-point records are not public in a usable form. |
| Type | **S × Δ** |
| Formula | **Skill:** b_P = shrunk importance-weighted minus plain return points won.<br>**Scarcity:** β̂_AB = expected break points per service game from the iid model at p_{A→B} and p_{B→A}.<br>**Feature:** x = (b_A − b_B)·(β̄_c/β̂_AB). Swap: β̂ is sym, so x is anti ✓. |
| Data | Point-by-point data (`data/studies/shot_level/`): Slams 2011–2024 in part, plus tour-level feeds. **Timing:** own-order (safe). |
| Why the model cannot already do it | No big-point input; scarcity is a sum. |
| Expected effect | Tiny. **Prior:** the main effect added −0.05 [−0.13, +0.03] milli-log-loss given the odds (men; a tie). |
| Kill test | Kill if the screen gain is under 0.05, or coverage is under 30% of the 2014–2021 main-tour matches. |

#### MEC-19 · Resilience excess: breaking back and consolidating

| Field | Content |
|---|---|
| ID, name | MEC-19 · Non-iid sequence traits beyond a player's own hold and break rates |
| Mechanism | **Under iid, games are independent,** so breaking back right after being broken happens at the player's ordinary break rate. The shot-level study found these raw sequence rates repeat (split-half 0.43/0.49 for holding right after breaking, 0.38/0.52 for breaking back, men/women). But they include ordinary hold and break strength.<br>The excess over the player's own rates in the same matches would be a genuine non-iid trait. |
| Why the price might miss it | "Resilience" is narrative, not measured. |
| Type | **W** (with an S arm) |
| Formula | **Trait:** R_P = shrunk excess (breaks back plus consolidations, minus their expectation from P's own break and hold rates in each match).<br>**Feature:** x = R_A − R_B.<br>**S arm:** x·4p(1−p), with p from the price (closeness).<br>**Swap:** anti ✓. |
| Data | Point-by-point sequences (19,500 men's and 9,900 women's matches). **Timing:** own-order (safe). |
| Why the model cannot already do it | No sequence input. |
| Expected effect | Tiny. |
| Kill test | Kill if the excess's split-half carry-over is 0.1 or below. |

#### MEC-20 · Rally pace × load and age: attrition exposure in minutes

| Field | Content |
|---|---|
| ID, name | MEC-20 · Expected minutes × physical-state differences |
| Mechanism | **Length in points is already in the price** (observed, item 2: it depends on closeness, not dominance). Minutes per point is a style trait (rally length and time between points; the share of long points repeats at 0.85). Two baseliners on slow clay play long matches, which tax the older or more loaded player. |
| Why the price might miss it | The price knows closeness and the format, not the expected minutes of this pairing. |
| Type | **S × Δ** |
| Formula | **Pace:** mpp_P = shrunk mean minutes per point over P's earlier matches.<br>**Expected minutes:** E_min = E_points(the price's closeness, f) × (mpp_A + mpp_B)/2.<br>**Inputs:** E_min·Δ`sets_14d` and E_min·Δ`age`. Swap: anti ✓. |
| Data | `stage0` minutes (men 91% of main-tour matches; women 70%, sparse before 2016). **Timing:** own-order (safe). |
| Why the model cannot already do it | The model has Δload and Δage, but no modulator of length except best of. |
| Expected effect | Small. **Prior:** fatigue × expected length showed no sign given Elo (UFC-ideas Stage C). |
| Kill test | Kill if the screen gain is under 0.05 milli-log-loss. |

#### MEC-21 · Lost serve speed × the returner

| Field | Content |
|---|---|
| ID, name | MEC-21 · A drop in first-serve speed, crossed with the returner's strength |
| Mechanism | **A drop in first-serve speed (injury, fatigue) costs free points.** By MEC-04's structure, it costs most against returners who punish what comes back.<br>The men's recent serve-speed change was the shot-level study's one direction to watch: +0.24 milli-log-loss given the odds in 2022–2026 (gain, higher is better), absent before. |
| Why the price might miss it | Serve speed is visible on broadcasts but not archived in a form markets use. |
| Type | **X** |
| Formula | **Change:** s_P = shrunk change in first-serve speed (last 5 matches against the 52-week mean, km/h).<br>**Feature:** x = s_A·D^spw_B − s_B·D^spw_A; a drop facing a strong returner is negative for A. Swap: anti ✓. |
| Data | Shot-level serve speeds: about 10,200 men's matches, partial. **Timing:** own-order (safe). |
| Why the model cannot already do it | There is no speed input; the term needs levels. |
| Expected effect | Men; small; limited by coverage. |
| Kill test | Infeasible if under 30% of 2014–2021 men's main-tour matches carry speeds. Otherwise the screen at 0.05. |

## Considered and set aside

| Idea | Why set aside |
|---|---|
| A left-hander's ad-court slice as a big-point bonus | **Killed by the iid identity** (observed, item 3): deuce and ad courts each carry exactly half of a game's sensitivity. A ±2-point court split moves the hold rate by at most 0.0003. What remains is an average effect (MEC-09). |
| Attrition driven by serve dominance | **Killed** (observed, item 2): expected points depend on closeness, not dominance (an even best-of-three match lasts 164–166 points at serve rates of 0.56–0.70). |
| First serves under pressure × second-serve return | **Bounded:** a 3-point drop in first serves landed on pressure points moves the hold rate by about 0.3 points at most, even against a second-serve specialist. |
| Style contrast at equal strength and dominance | **Exactly zero under the additive iid model** (notation section). Real style effects need MEC-04, -06, -07, -09 or -10. |
| Height × height ("tall against short") | Identically zero after antisymmetrisation. Only the asymmetric version (MEC-12) can carry a sign. |
| Rally-length matchups (first-strike against grinder) | Tested in the shot-level study, nothing given the odds; no new mechanism here. |
| Serving first in a set or match | Unknown before the toss, and under iid the set probability does not depend on it (Newton–Keller, tested in Stage 2). |
| Weather, heat, wind, day or night sessions | No archived forecasts or start times are held. |
| Returners adapting to big servers over best of five | The late-match decline is not a player trait (UFC-ideas Stage C), so there is no stable quantity to cross. |

## Top 8, ranked

1. **MEC-01 · Serve-dominance leverage of the price** (M × S). It is the only idea that rescales the price itself, where the signal is.
   * The leverage is computed exactly and varies 0.81–1.04 inside men's hard courts.
   * It is invisible to the model by symmetry.
   * Bound: 0.40 milli-log-loss for men (0.10 if half priced).
2. **MEC-04 · Free-point shield** (C / X). The cleanest structural cross-player term: return elasticity falls from 0.93 to 0.56 as free points rise. It makes a directional prediction (big servers against elite returners) and needs both players' levels.
3. **MEC-05 · The profile composed through the iid model** (C). It composes the model's own strongest family through the exact point-to-match map in one column. About 0.06 match log-odds of it cannot be formed linearly.
4. **MEC-14 · Age × the profile's shape** (W). It corrects the long-memory IOS's age lag where the lag should be largest; cheap, with an outcome-free first check.
5. **MEC-06 · Second-serve exposure × second-serve specialisation** (X). Computed at 1.0 point of serve points for extreme types; the least redundant term for women (R² 0.62).
6. **MEC-08 · Conversion luck** (W, pair arm M). A clean results-against-points mechanism aimed at the market's reliance on results; tempered by tiebreak luck already looking priced (−0.02, a tie).
7. **MEC-03 · Venue pace from earlier editions** (S). A persistent condition below the level of surface (aces r = 0.52 between editions), built leak-proof; it feeds MEC-01 and MEC-04. A thinner proxy tied before.
8. **MEC-02 · Four sums** (S). A cheap, general way to let TabPFN form every bilinear matchup itself. It must beat a placebo, because TabPFN ignores context today.

Next in line: MEC-09 (hand deviations; 24% of men's matches carry the information, but the crude version failed) and MEC-17 (volatility; persistence unknown).

## Files

| What | Where |
|---|---|
| This list | `docs/studies/feature_interactions/round0/ideas_mechanics.md` |
| iid arithmetic (no data rows) | `src/eda/feature_interactions/round0/mechanics/iid_mechanics.py` → `data/studies/feature_interactions/round0/mechanics/iid_mechanics.json` |
| Feature spreads (seasons up to 2021; no result or price read) | `src/eda/feature_interactions/round0/mechanics/feature_spread.py` → `data/studies/feature_interactions/round0/mechanics/feature_spread.json` |
