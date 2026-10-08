# Scoped audit: point-derived match-level statistics

Positive = the statistic (or real data) is better; "tie" = the interval spans 0.

## 1. Ranking

1. **Serve-speed change.** Agree it is the top lead, with weak evidence:
   * the change alone: +0.14 [−0.00, +0.28], a tie;
   * the +0.24 belongs to a 3-input profile picked among about 300 rows.

   Its reliability is already known (0.99), so it skips the trait gate.
2. **Return leverage.** Agree. It is the only point statistic beyond luck: 0.21 / 0.19 at the Slams. But pre-match it took the **wrong sign** given Elo (+0.09) and tied given the market (−0.05 / −0.09). Depth can settle it.
3. **Own-serve tempo** (women). Agree, but expect "reliable style, no edge"; the tempo fade already tied.
4. **Serve leverage.** Free alongside #2; expect closure.
5. **Scoreline luck: disagree with the brainstormer's #3.**
   * Box scores give it; no sequences are needed.
   * Its parts tie given the market: tiebreak record −0.02 / +0.03; results above Elo −0.04 / −0.06.
   * It is results minus points won, the framing the owner dislikes.
   * A trait screen is pointless (luck has about zero reliability). At most a one-hour price-only check.

Closed, agreed:
* **S4** (exact null): +0.055 [−0.004, +0.116] at ≥ 20 per half, a tie; r −0.24 with hold rate.
* **S1–S3, S5,** the fade markers and the shot-level rates.

## 2. Screen now

**A. Return and serve leverage.**
* *Definition:* RL = Σw(y − ȳ) / Σw over P's return points.
* *Weight:* w = match-win importance at the score before each point, at both players' **pre-match** p_serve (`stage3_ratings`).
  * The match's own rates would leak the outcome into the weights.
  * Tour averages mis-weight lopsided matches.
* *Benchmark:* an exact within-set permutation of P's return-point outcomes, re-scored and re-weighted. It uses no rate model, so it sidesteps the mis-calibrated replay. Its re-scoring bias is calibrated on iid replays; the V1 replay is secondary.
* *Pass* (Holm over 2 tours × 2 sides):
  * real − null split-half Δ ≥ 0.10 at ≥ 20 per half, interval above 0;
  * |r| with break (or hold) rate < 0.3;
  * ρ² above the null's.
* *Next:* a residual screen against `p_base`. Discovery 2015–21, replication 2022–24. **A negative sign is a fail** (luck pattern).
* *Trap:* 68% of WTA-log tie-break matches are unusable, so the biggest points are missing.

**B. Own-serve tempo** (women, WTA log, 2019-06 – 2024).
* *Measure:* the median gap between own-serve points.
* *Exclusions:* game openers; points next to lets, challenges, or medical, toilet or suspension records.
* *Net of:*
  * the **umpire**, whose entry latency adds to every gap;
  * event-year (shot clock);
  * score class;
  * whether the previous point was an ace or double fault. There is no rally length, which is a trap.
* *Pressure pace:* pressure minus normal gap, against pressure labels permuted within the match.
* *Pass:*
  * pressure pace: Δ ≥ 0.10 against the null;
  * tempo level: partial R² < 0.1 with the 58 inputs.
* *Next:* a residual screen (discovery 2020–21, replication 2022–24).

**C. Speed change** (no trait gate).
* *Test:* a residual screen against `p_base`, on 2-week minus 52-week first-serve speed.
* *Windows:* discovery ≤ 2021 (Slams), replication 2022–24 (Infosys + Slams).
* *Pass:* a replication interval above 0.

## 3. More data, only after a pass

* **ATP non-Slam per-point speeds 2025–26**, if C passes. Decryption is the owner's decision.
* **WTA tie-break point winners**, rebuilt from marcosjn2 and SofaScore overlaps, for A.
* **Men's non-Slam point clocks** (TDI weekly, free), if B passes.
* **Infosys Challenger points 2021–24**, rebuilt from the handoff, for depth in A.

**Not justified:** more sequences for momentum or streak traits; charts or tracking for rally, net, placement or ending rates.
