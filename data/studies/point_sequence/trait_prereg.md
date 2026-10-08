# Pre-registration: A1-T (momentum and streak traits, outcome-free) and I2 (the women's points-share anomaly)

Written 6 Oct 2026 by TESTER-1, **before any reliability, correlation, replay statistic or log loss was computed**.
Up to this point only the population was counted (matches and players per tour after the filters below).
Binding plan: the auditor's round-3 build list (items 1 and 4). Code: `src/eda/point_sequence/trait_*.py`,
`src/eda/point_sequence/i2_points_share.py`; outputs `data/studies/point_sequence/trait_*`, `i2_*`.
Any later change is recorded under **Deviations** at the end, with its reason and whether results had been seen.

Inputs received before writing (from the coordinator, 6 Oct): (1) `stage2_anatomy.denoised_rates` fits its prior on
whatever it is given, so the prior is re-implemented here and fitted on ≤ 2018 rows only; (2) a carry-over tester saw
set-1 and late-set serve residuals correlate 0.27 in day-rate replays against 0.08 in real matches, so the between-set
correlation is reported as a calibration diagnostic and every verdict is checked across the variance variants;
(3) dates come from `match_timing/timing.parquet` `obs` (best-estimate match day), never the tournament day.

## 1. Population (item 1)

* Stage 0 matches with a chosen, usable sequence (`seq_matches`: `chosen`, `usable`), **tier 0 or 1** (a complete
  replay reproducing the official score), replay `complete`, Stage 0 `status == completed` (retirements, walkovers
  and anything else out), Stage 0 `format == standard`, and `rule` one of bo3/bo5 × {tb, tb10, adv, tb12}.
* Men 2013–2024, women 2016–2024 (Stage 0 season). 2025–26 is not read.
* Every level the table holds (Slams, Finals, 1000/500/250, team events, Challenger/125, ITF, qualifying).
* The sequence's own winner (last point) must equal Stage 0's `a_won`; disagreements are dropped and counted.
* Players are Stage 0 `player_a_id` / `player_b_id`; side 1 = A, side 2 = B in `sequences.parquet`.
* Counted so far: men 65,968 matches, women 28,110; players with ≥ 40 matches: men 754, women 347; ≥ 100: 376 / 204.

## 2. The statistics (per player-match; identical code on real and replayed sequences)

Games are formed from the points (`game_idx`); a regular game's server is its points' server, its winner the winner of
its last point. "Previous game" means the game immediately before **in the same set**, a regular game (the shot-level
study's convention). Tie-breaks are never a trigger and never a target in S1, S2, S4, P0. Each statistic is stored as a
numerator X and a denominator D summed over matches; a player's value over any set of matches is ΣX / ΣD.

* **S1, hold after breaking (excess).** P's regular service games whose previous game was the opponent's service game
  broken by P: n1 games, h1 held. P's other regular service games in the match: n0, h0.
  X = h1 − n1·h0/n0, D = n1 (n0 ≥ 1). Holds per after-break game above P's hold rate in the other games of that match.
  Higher = holds better right after breaking than otherwise that day.
* **S2, break back (excess).** The opponent's regular service games whose previous game was P's service game, broken:
  n1 games, b1 won by P. The opponent's other regular service games: n0, b0. X = b1 − n1·b0/n0, D = n1.
  Higher = breaks back more often than P breaks otherwise that day.
* **S3, serve-point serial dependence with score-state fixed effects.** P's serve points in regular games with a
  previous point in the same game (pt_no ≥ 2). y = P won the point, x = P won the previous point. State = the game
  score before the point (server's points, receiver's points; 0–3 each, and from 3–3 on: deuce, advantage server,
  advantage receiver). Cells = player-match × state; x̄ = the cell's mean of x.
  X = Σ (x − x̄)·y, D = Σ (x − x̄)². X/D is the within-cell slope: won after won minus won after lost, the same match
  and score state. Higher = streakier (hot hand).
* **S4, game-level overdispersion of serve points (D − 1).** P's regular service games g: n_g serve points, w_g won;
  p̂ = Σw/Σn over them. X = Σ (w_g − n_g p̂)² − Σ n_g p̂(1 − p̂), D = Σ n_g p̂(1 − p̂) (D = 0 when p̂ is 0 or 1).
  X/D = dispersion index − 1. Higher = service games more unlike each other (streakier at game level).
* **S4r, runs (secondary, not in the Holm family).** Per P regular service game with both outcomes present: runs R of
  the serve-point outcome sequence, and the exchangeable expectation E = 1 + 2ab/n and variance
  V = 2ab(2ab − n)/(n²(n − 1)) (a won, b lost, n = a + b). X = Σ (E − R), D = Σ V. Higher = fewer runs = streakier.
* **S5, set-to-set swing.** P's serve points per set k (tie-break serve points included): n_k, w_k; p̂ = Σw/Σn.
  X = Σ_k (w_k − n_k p̂)² − Σ_k n_k p̂(1 − p̂), D = Σ_k n_k p̂(1 − p̂). Higher = sets less alike.
* **P0, placebo: hold after holding (excess).** P's regular service games whose previous own service game in the same
  set (two games back) was held: n1, h1. P's other regular service games (the first in each set, and those after
  being broken): n0, h0. X = h1 − n1·h0/n0, D = n1.
* Also per player-match: service games and holds, return games and breaks (for the ability check), serve points won
  per set and in total (for the replay rates and the between-set diagnostic).

## 3. The replay (benchmark)

* Every population match is replayed **3 times** point by point under iid serve points: the same best-of, deciding-set
  rule (`seq_matches.rule`), and the same first server as the real match; every set but the deciding one has a 7-point
  tie-break at 6–6. A vectorised point-level replayer emits point sequences in the real schema; the same statistic
  code then runs on them. A test checks every replayed sequence against the builder's `replay.replay` (complete, same
  set/game/point labels) and `replay.rule_servers`.
* **Day rates, de-noised; priors frozen on ≤ 2018** (re-implementation of `stage2_anatomy.denoised_rates`): measured
  rate P = serve points won / served in the real match (from the sequence, tie-breaks included), noise = P(1 − P)/N.
  Per tour × surface, on population rows with season ≤ 2018 (men 2013–18, women 2016–18): mean μ, measured variance,
  true variance v = measured variance − mean noise; groups under 400 player-matches use the tour's ≤ 2018 prior.
  Each player-match draws its true rate from N(μ + s(P − μ), s·noise), s = v/(v + noise), clipped to [0.02, 0.98];
  the two players independently.
* **Variants** (3 replays each): **V1** (true variance × 1; item 1's primary benchmark and item 4's shared replays),
  **V05** (× 0.5), **V15** (× 1.5), and **VPS**, a per-player-season prior: the centre is μ plus the player's
  leave-one-out mean residual (P − μ) over their other population matches of that season, shrunk by its reliability
  (between-player-season variance v_b over v_b + (v_w + mean noise)/n), with the prior variance v_w + v_b(1 − λ);
  v_w (within-player-season day variance less noise) and v_b = v − v_w are fitted on ≤ 2018 per tour. ("Per
  player-season rates" in the plan is read as this de-noising prior; the reading is mine.)

## 4. Item 1 endpoint: split-half reliability, real against replay

* Per tour, players with **≥ 40** population matches (≥ 20 per half; primary) and **≥ 100** (≥ 50 per half; reported).
* **50 random splits** (fixed seed): each eligible player's population matches are split at random into two halves of
  equal size (± 1). Per half, the statistic is ΣX/ΣD; a player-half with ΣD = 0 is left out of that split for that
  statistic. r = Pearson correlation across players of half 1 against half 2; the reliability is the mean r over the
  50 splits. The **same splits** (same match-to-half assignment) are used for the real data and every replay.
* Replay reliability = the mean over its 3 replays. Difference **Δ = real r − replay r** (V1 primary).
  Higher Δ = more trait-like beyond scoring luck.
* **Player bootstrap**: 2,000 resamples of the eligible players (with replacement; each brings its per-split half
  values); Δ recomputed in each. 95% interval = 2.5–97.5 percentiles; two-sided p = 2Φ(−|Δ|/SE_boot).
* **Ability check**: across the eligible players, Pearson r of the player's statistic (ΣX/ΣD over all their matches)
  with their hold rate and with their break rate over the same matches; the criterion uses max(|r_hold|, |r_break|).
  Also reported: the cross-half version (statistic in one half against the rate in the other, mean over splits).
* **Pass, per statistic × tour (Holm over 10 = S1–S5 × 2 tours, α = 0.05):** at ≥ 20 per half, Δ ≥ 0.10, Δ > 0 with
  Holm-adjusted p < 0.05 (the interval excludes 0 at the Holm level), **and** max(|r_hold|, |r_break|) < 0.3.
* **Placebo P0** must sit on the replay: its Δ interval (95%, unadjusted, V1) covers 0. If it does not, the benchmark
  is taken as biased by at least the placebo's Δ, and a statistic of that tour passes only if Δ_stat − Δ_P0 ≥ 0.10 too.
* **Robustness to the replay**: Δ under V05, V15 and VPS for every statistic; a verdict that differs between variants
  is reported as replay-dependent. Secondary: S4r (Holm over its 2 tours); ≥ 50 per half; the `strict` subset (box-score
  serve points agree); source-centred statistics (X − D·mean of X/D over the tour × source, per world).
* **Population means** (context, not a trait test): pooled ΣX/ΣD over all player-matches, real against replay, with a
  player-cluster bootstrap interval: within-match dynamics at population level.

## 5. Item 1 endpoint: recovery of the career truth by depth

* Empirical-Bayes constants (Stage 3's method of moments, `stage3_traits.eb_constants`) per statistic × tour on
  player-season windows with season ≤ 2018, separately in each world (real; each replay).
* Targets: player-matches of seasons 2014–2024 (men) and 2017–2024 (women). **52-week value**: the player's earlier
  population matches (own order: `obs` day, then round order; an earlier match of the same event counts) with `obs`
  within the 364 days before the target's `obs`, ΣX and ΣD, shrunk: (ΣX + Kμ)/(ΣD + K). **Career truth**: the same
  shrunk value over all the player's population matches ≤ 2024 (the plan's version; it overlaps the 52-week memory).
  Also reported: a **disjoint truth** (career minus the 52-week memory and minus the target match).
* Depth = ΣD in the 52-week memory; quartiles over targets with depth > 0 (per tour × statistic). ρ² = squared Pearson
  correlation of 52-week value and truth, per quartile and overall, real against replay (mean of 3). If K is infinite
  (no true spread on ≤ 2018), the unshrunk 52-week rate is used and flagged.

## 6. Calibration diagnostic (coordinator's request)

Per player-match: set-1 serve residual and late-set serve residual (set 2 in best of three, set 3 in best of five),
each (won − n·p)/√(n·p(1 − p)) with p = `stage3_ratings` pre-match `p_serve`. Pearson r across player-matches per tour,
real against each variant. Reported beside S5.

## 7. Item 4 (I2): the women's points-share anomaly

* **Women (primary):** `source == wta` (umpire log), non-Slam, standard best of three, `obs` on or after 1 Jun 2019,
  season ≤ 2024, the item-1 quality filters. **Men's control (primary):** all sources, non-Slam, best of three,
  2013–2024, the same filters.
* **Endpoint:** five-fold cross-validated logistic regression without intercept (`stage2_anatomy.oof_logit`) of the
  winner on 100 × (points share of A − 0.5), points counted from the sequence; log loss per match. The same on
  logit of the iid plug-in chance (`stage2_iid.match_win_by` at the match's measured serve rates and its rule).
  Fitted separately in the real matches and in each replay world.
* **Gap = real − replay** log loss in milli-log-loss, per match paired (replay = mean of its 3 replays), 95% interval
  mean ± 1.96 SE. Positive = the real points share decides matches less well than iid luck (the anomaly's direction).
* **Variants:** V05, V1 (item 1's replays), V15, VPS.
* **Pass:** the women's points-share gap has a 95% interval excluding 0 under **every** variant, **and** the men's
  covers 0 under V1. Also reported: whether the men's covers 0 under each variant, the women − men difference of gaps,
  and the plug-in-chance version (secondary).
* **Diagnostics** (real against each replay): tie-breaks per match, share won with fewer points, SD of the points share,
  winners' mean share, the fitted slope.
* **Secondary:** women all sources non-Slam; women Slams (best of three); men Slams (best of five); and the **box-score
  points share** (Stage 0 `tpw`) on the same primary matches, real only, against the sequence's: the box-score-error
  reading of Stage 2's 0.118 against 0.103.

## 8. What a result closes or opens (from the plan)

* Item 1 null: closes momentum, streak and pressure-reaction as stable player traits at full depth (within-match
  dynamics may exist; players do not differ measurably); B3, B5 and C1–C3 go as pre-match traits; what remains is the
  in-play question (G2) and state carry-over (item 3). A pass: a residual screen against `p_base` next (not run here).
* Item 4 null: closes the anomaly as evidence of streakiness (box-score error or replay misspecification) and parks
  B3 for women. A pass, read with S5, says whether within-match swings are real and whether they are player traits.

## Deviations

* **D1 (clarification of item 4's pass, written before any I2 log loss was computed, but after the build's match-structure
  diagnostics were seen**: real matches have fewer tie-breaks and fewer wins with fewer points than every replay).
  "Excluding 0" is read in the anomaly's direction: the women's gap must be **positive** (real points share less decisive
  than iid) with its interval excluding 0 under every variant. A significantly negative gap is reported as the opposite
  finding, not as a pass. Also added before any I2 number: a secondary men's control on the women's period (non-Slam,
  Jun 2019–2024), so the two tours are compared on the same years.
* **D2 (post-hoc exploration, after all pre-registered item-1 results were seen; not part of any verdict).**
  `trait_s4_explore.py`: the men's S4 signal at ≥ 50 per half re-tested on strict sequences, source- and
  event-centred statistics, main tour only, each era, rank correlation, and S4 recomputed around per-set, per-end and
  per-set × end rates. Labelled exploratory everywhere; it would need its own pre-registration before any use.
* **D3 (code, no effect on results).** `trait_reliability.reliability_block` takes the number of statistics from its
  input (needed by the exploration); the pre-registered outputs were produced before the change and are unchanged.
* **D4 (I2 diagnostics added after the I2 run, read-only).** The WTA log's loss of tie-break matches was quantified
  against Stage 0, and Stage 2's own women's table was refitted without the two events whose box scores are mirrored.
