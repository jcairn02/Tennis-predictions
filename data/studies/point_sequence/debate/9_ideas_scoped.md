# Point-derived match statistics: scoped ranking (6 Oct 2026)

mLL: positive = with the statistic better.

## 1. Ranked

1. **Serve speed** (first-serve speed against the player's 52-week norm; fade within the match).
   * *Needs more data:* ATP non-Slam speeds from 2025–26, only by decrypting ATP files (an owner decision).
   * *Novel combination:* pair it with box-score serve form.
   * The only point statistic with a gain over the close: profile +0.24 [+0.07, +0.41] (2022–26). The change alone is +0.14, a tie.
2. **Return leverage** (importance-weighted return points won minus the plain share).
   * *Build now and test.* If it passes, *novel combination:* IOS-style offence/defence × the matchup's expected big-point mass.
   * Persisted beyond luck at the Slams (0.21 men / 0.19 women); never tested at full depth.
3. **Scoreline luck** (games won minus the iid expectation from the match's own points). *Build now*, price-only gate.
4. **Own-serve tempo** (pace, and pace under pressure).
   * *Build now* for women (WTA log clocks).
   * *Needs more data* for men: non-Slam point clocks (TDI's weekly capture, free).
5. **Serve leverage.** *Build now*, free alongside #2. Luck-level at the Slams; expect closure.
6. **Closed:**
   * **S4** (within-set clustering): permutation Δ +0.055 [−0.004, +0.116]; disjoint ρ² 0.055 in the deepest men's quartile, about 0 elsewhere.
   * **Finishing form:** about 0.1 mLL even if real.
   * **S1–S3 and S5:** ties on both tours.
   * **Fade markers**, and **rally, ending, net and placement rates.**

## 2. Top three buildable now

**Return leverage.**
* *Definition:* over P's return points i, w_i = P(P wins the match | wins i) − P(P wins the match | loses i), from the score before point i at tour × surface serve rates frozen on ≤ 2018 (`stage2_pbp` code). RL = Σw_i(y_i − ȳ) / Σw_i, where ȳ is P's plain return share in that match.
* *Benchmark:* replays that draw both players' rates jointly, plus the variance variants.
* *Gate:*
  * real − replay split-half Δ ≥ 0.10 at ≥ 20 matches a half, Holm over the two tours;
  * |r| with break rate < 0.3;
  * disjoint ρ² above the replay's.

**Scoreline luck.**
* *Definition:* L = games won − E_iid[games won] at the match's de-noised serve rates. Pre-match: the sum over the current event and an 8-week decayed sum.
* *Benchmark:* the iid replay.
* *Gate:* regress logit p_mkt − logit p_noodds (stored forecasts, 2015–24) on L_A − L_B. A zero loading closes it; a positive loading earns one outcome screen.

**Own-serve tempo.**
* *Definition:* the median seconds between points in P's service games, net of serve number and pressure, excluding game openers and interruptions.
* *Benchmark:* within-match permutation of gaps across score states.
* *Gate:* reliability, and R² with the 58 inputs below 0.1.

## 3. Where not to spend more data

* **More point sequences for momentum or streak traits.** Full depth closed them.
* **Charts or decrypted ball tracking for rally, net, placement or ending rates.**
* **Exceptions:** ATP per-point speeds; men's point clocks only if tempo passes on women.
