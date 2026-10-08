# Pre-registration: return leverage (RL) and serve leverage (SL), trait gate (outcome-free)

Written 6 Oct 2026 by TESTER-1 from the binding spec (scoped audit, section 2, item A), before any importance weight,
leverage value, permutation or reliability was computed. Frozen by its SHA-256 in `lev_prereg.sha256`; `lev_run.py`
refuses to run if the hash differs. Deviations go to `lev_results.json` under "deviations", never here.

## Population (no match result is read)

Item 1's population (`trait_population.parquet`): Stage 0 completed, standard-format matches with a tier 0–1 complete
point sequence; men 2013–2024 (65,968 matches), women 2016–2024 (28,110). Pre-match serve probabilities `p_serve_a`,
`p_serve_b` from `stage3_ratings.parquet` (a sequential own-history rating; safe under the 5 Oct timing decision).
Matches without both are dropped and counted.

## The statistic

* Importance of a point: w = P(A wins the match | A wins the point) − P(A wins the match | A loses it), from the score
  before the point (sets, games, points or tie-break points, server, tie-break first server), under the iid model at
  the match's **pre-match** p_serve_a / p_serve_b, with the match's best-of and deciding-set rule (tb7, tb10 at 6–6,
  advantage, tb7 at 12–12). It is the same quantity as `stage2_pbp.Chances.importance`; it is computed by a vectorised
  re-implementation that a test checks against `Chances.importance` (read-only import) to 1e-9 on matches of every rule.
* For player P in a match: **RL** over P's return points: X = Σ w (y − ȳ), D = Σ w, y = P won the point, ȳ = P's
  return-point share in that match. **SL** the same over P's serve points (ȳ = P's serve-point share). All points,
  tie-breaks included. A player's value over matches is ΣX/ΣD. Higher = wins more of the important points than of all
  points (in importance-weighted share). Per match RL of P = −SL of the opponent (same points).

## Null: exact within-set permutation, re-scored and re-weighted

* World "X shuffled" (X = side A or side B): in every set, X's regular-game serve-point outcomes are put in a uniformly
  random order, and X's tie-break serve-point outcomes (if the set had a tie-break) are permuted among X's tie-break
  slots. The opponent's points keep their real order. The set is re-scored: X's stream is cut into games by the game
  rule (deuce / advantage), the games alternate with the opponent's real games from the set's real first server, and
  the tie-break follows its real serving order.
* **Accepted only if the set is valid and unchanged at its boundaries:** X's stream forms exactly the real number of
  complete games, with the real number of holds (hence the real final set score, set winner and set length); no
  earlier game ends the set or starts a tie-break; and the tie-break (if any) ends exactly on its last point. Regular
  part and tie-break are drawn independently (rejection sampling: uniform among valid orders). Up to 2,000 draws each;
  a set part with no accepted draw keeps its real order (conservative; counted).
* Importance is recomputed on the permuted match at the same pre-match p_serve. In world "X shuffled", SL of X and RL of
  the opponent are under the null. **3 shuffles** per side, seeds `[20261006, 91, side, j]`.
* **Calibration of the shuffle** (as for S4): the V1 iid replays (`trait_build.py` seeds, regenerated) with importance
  at the same pre-match p_serve, and one shuffle of each replay per side (seeds `[20261006, 92, side, r]`):
  Δ_iid = replay r − shuffled-replay r, and the population mean replay − shuffled.
* **Secondary benchmark**: the V1 replay itself (Δ_V1 = real r − replay r).

## Endpoint and pass rule

* Split-half reliability as `trait_reliability.run_population`: players with ≥ 40 population matches (≥ 20 per half;
  primary) and ≥ 100 (≥ 50 per half; reported); 50 random splits; the same splits for every world; r = Pearson across
  players of the per-half ΣX/ΣD; reliability = mean r over splits. **Δ = real r − null r** (null = mean of the 3
  shuffles). 2,000-resample player bootstrap; 95% percentile interval; two-sided p = 2Φ(−|Δ|/SE).
* **Ability**: across eligible players (≥ 20 per half), Pearson r of the player's real RL with her/his break rate, and of
  SL with hold rate (all their population matches).
* **Depth-held-out ρ²**: as item 1 (`trait_reliability.rho2_depth` logic): empirical-Bayes constants on seasons ≤ 2018
  per world; targets men 2014–2024, women 2017–2024 with a 52-week memory (by `obs`) holding importance > 0; ρ² of the
  shrunk 52-week value with the career truth **excluding the memory and the target** (disjoint truth). Overall and by
  depth quartile; real against the null (mean of 3 shuffles).
* **Pass, per statistic × tour (Holm over 4 = {RL, SL} × {men, women})**: at ≥ 20 per half, Δ ≥ 0.10 with Holm-adjusted
  p < 0.05 and Δ > 0; |r| with break rate (RL) or hold rate (SL) < 0.3; and overall disjoint ρ² real > null. If the
  calibration's Δ_iid interval excludes 0 for that tour × statistic, Δ − Δ_iid ≥ 0.10 is also required.
* Reported, not pass-defining: ≥ 50 per half, Δ_V1, population means real − null (and replay − shuffled replay), the
  sign of the population mean (the later residual screen treats a negative sign as a fail).

## Diagnostic: importance mass lost

Per tour, the universe = Stage 0 completed standard-format matches in the window holding at least one linked point
sequence (any source, any tier). Lost = universe minus population. Each lost match's importance mass (Σ w over all its
points) is estimated by the mean mass of population matches with the same official score (Stage 0 `score`, tie-break
points stripped) and best-of, else the mean by best-of × sets × tie-breaks. Reported: matches and estimated mass lost
(share), tie-break matches' share among lost and kept, the WTA umpire log's tie-break matches separately, and the share
of mass carried by tie-break points in kept matches with a tie-break.
