# Pre-registration: men's S4 against a within-set permutation null (no rate model)

Written 6 Oct 2026 by TESTER-1 at the coordinator's request, before any permutation was drawn and before any reliability
under this null was computed. This file is frozen by its SHA-256 in `trait_s4_perm_prereg.sha256`; any deviation is
recorded in `trait_s4_perm_results.json` under "deviations", never here.

**Already seen** (from the A1-T run, `trait_tests.csv`, `trait_reliability.csv`, `trait_s4_explore.csv`): S4 against the
de-noised day-rate replay (V1) is Δ +0.074 [+0.010, +0.137] (men, ≥ 20 per half) and +0.225 [+0.135, +0.310] (men,
≥ 50); women +0.100 [−0.014, +0.201] at ≥ 50; the replay's sets are more alike than real sets (between-set residual r
0.42 against 0.27, men best of three). The question here: is men's S4 a player trait beyond random order of the same
serve points, with no model of rates at all?

## Data

* Item 1's population (`trait_population.parquet`): men 2013–2024 (65,968 matches), women 2016–2024 (28,110); all
  seasons ≤ 2024; tier 0–1 complete sequences, completed matches, standard format. No match outcome (winner) is read.
* S4 exactly as pre-registered in `trait_prereg.md`: per player-match, over the player's **regular** service games g
  (n_g serve points, w_g won), p̂ = Σw/Σn; X = Σ (w_g − n_g p̂)² − Σ n_g p̂(1 − p̂), D = Σ n_g p̂(1 − p̂).
* **Tie-break points are excluded** (S4 never used them): they are not permuted and do not enter S4.

## The null

* Pool = one server's serve points in the regular games of one set, in match order (match × set × server).
* A permutation draws a uniformly random order of the pool's outcomes (won/lost), then re-scores it into games with the
  game rule (a game ends when one side has at least 4 points and leads by 2: deuce and advantage). An order is
  **accepted only if its last point ends a game** (every point in a complete game); otherwise the pool is redrawn
  (rejection sampling: a uniform draw among the orders that form complete games). Up to 5,000 draws per pool; a pool
  with no accepted draw keeps its real order (conservative; counted and reported).
* The server's per-set count of serve points won and served is preserved exactly, hence p̂. The number of service games
  in a pool, and its holds, may differ from the real ones (reported).
* **3 permutations per match**, seeds `[20261006, 77, j]`, j = 0, 1, 2.
* Identity check: re-scoring each pool in its real order must reproduce the stored real S4 (`trait_player_matches`).
* Computation: the permuted games are written as point arrays and passed through `trait_common.point_stats` (the
  existing pipeline); only S4 (and service games / holds, for diagnostics) is read from it.

## Endpoint

* Split-half reliability with `trait_reliability.run_population`: players with ≥ 40 (≥ 20 per half; primary) and ≥ 100
  (≥ 50 per half) population matches; 50 random splits (fixed seed), the same splits for the real and the permuted
  worlds; r = Pearson correlation across players of per-half ΣX/ΣD; reliability = mean r over the splits.
* **Δ = real r − permuted r** (permuted = mean of the 3 permutations). Higher Δ = more trait-like beyond random order.
  Player bootstrap: 2,000 resamples of eligible players; 95% percentile interval.
* Ability: across eligible players (≥ 20 per half), Pearson r of the player's real S4 (ΣX/ΣD over all their matches)
  with their hold rate and with their break rate over the same matches.
* **Pass** (men primary; women secondary, same rule): at ≥ 20 per half, Δ ≥ 0.10 with the interval excluding 0
  (lower bound > 0), **and** max(|r_hold|, |r_break|) < 0.3. No multiplicity correction (one primary test).
* **Population level**: pooled ΣX/ΣD over all player-matches, real − permuted (mean of 3), per tour, with a 1,000-
  resample player-cluster bootstrap interval. Positive with the interval above 0 = serve points cluster into games
  beyond random order within a set.
* Diagnostics: acceptance rate and draws per pool; pools left in real order; service games per pool and hold rate,
  real against permuted.

## Reading, stated in advance

* Men pass: a variance trait (players differ in within-set clustering of serve points into games) that the replay's
  rate model did not create.
* Men fail at ≥ 20 and the ≥ 50 interval covers 0: the earlier S4 signal was an artefact of the de-noised replay.
* Men fail at ≥ 20 but the ≥ 50 interval excludes 0: a weak trait, real beyond random order, below the pass margin at
  the pre-registered depth (not a pass).
