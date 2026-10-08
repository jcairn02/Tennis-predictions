# Independent audit of the surface-IOS strategy (6 Oct 2026)

Written by an independent Claude Opus 5.5 agent, read-only in the repository, before any 2022-2026 result of a surface arm existed; it saw no validation result of a surface arm. Kept verbatim; the main analyst's responses are in [strategy.md](strategy.md), section 7. The scripts it cites were scratch files outside the repository; its two decisive checks (the local model's calibration and the seeds' variance) are reproduced by `score.py`.

---

# Surface IOS: independent audit (6 Oct 2026)

**Units.** Match numbers are milli-log-loss per match. Positive means the second-named forecast is better. A 95% interval that spans 0 is a tie. **Labels:** *Obs* = observed (file or check named), *Inf* = my inference. All my scripts are in `scratchpad/audit/`. I used no outcomes from 2019 onward with surface inputs. The only outcomes I read were the existing base arm's.

## Verdict

* **The construction is correct and leak-proof.** I found no bug in the solver, the incremental step or the arms mapping.
* **The statistic-forecast evidence is solid.** All 16 tour × statistic gains are positive out of sample over 2019–2026 (`oos_scores.csv`).
* **The match-level test is not ready.**
  * The local reference model is mis-calibrated (fixable).
  * The interval leaves out seed variance.
  * The test can only detect effects well above any plausible effect, so a tie is the expected result and cannot settle the idea.
* **Arm R2 is the weaker representation.** I propose a one-column alternative.

## 1. Construction

**Checks**
* *Obs.* The normal equations in `ios_surface.py` (lines 211–224) match the model term by term. The preconditioner is the exact arrowhead block.
* *Obs.* The incremental step (lines 323–337) is the exact block re-solve. Its right-hand side uses the snapshot normal equation. The opponent's effective rating comes from the gap match's own snapshot, so it is earlier than the target match and cannot leak.
* *Obs.* `arms/checks.json`: the 21 rebuilt current inputs match the base frame to within 5.3e-15. My rerun (`features_check.py`) gives the same 5.3e-15.
* *Obs.* `probe.json`: PASS. At four cut days, 0 of 13,758–31,163 earlier matches moved, and the largest difference was exactly 0.
* *Obs.* Every full run converged (maximum 23 PCG iterations).
* *Obs.* The products' signs and the swap symmetry of the new columns are correct.

**Bugs and hazards**
1. **Stale cache in `build_features.py:88`.** Runs are skipped when `{tour}_{stat}_{kind}.npz` already exists, and the constants are neither stored nor checked. If the tuning grid is re-run, old surface runs would be reused without warning. Today's runs are consistent with `tuning_choice.json`.
2. **R2 mixes two models.** It adds the surface model's deviations E and F to today's pooled levels. But E is measured from the surface model's own level, not today's. What R2 should carry is the change the surface model makes, its effective value minus today's.
   * *Obs.* The deviations correlate only 0.84–0.95 with that change (`features_check.py`), so they explain 71–90% of its variance.
   * *Obs.* They miss the level correction (a clay specialist's level is no longer inflated on hard). Hard courts carry about 23% of the men's hold gain in tuning, and in that gain-share sense hard is not a null subgroup.
3. **Data regime change in 2025.** *Obs* (cache): box-score rows jump from 27k to 60k (men) and from 10k to 44k (women) in 2025, almost all below evaluation level. *Obs:* women's hold box scores are absent before 2015, so the hold columns are about 0 on the 2013–2014 training rows (SD of the net shift 0.001 in 2013).
4. **R1 injects noise into return-side double faults and first serves in.** *Obs* (`diagnostics_movement.csv`): R1 moves those inputs and their products by 33–60% of their SD on clay and grass. Yet section 3.4 shows the return side carries only 0–21% of the gain for these two statistics. The grid has no serve-only variant (κ_F = ∞).
5. **Indoor and outdoor hard are pooled** as one surface.

## 2. Evidence (section 3)

* **The tuning is sound.** Main-tour gains are as large or larger than all-level gains (*Obs*, `runs.jsonl`: men's holds +0.60 against +0.45), so including the Challenger rows does not drive the choice.
* **Grid boundary.** 30× is the best penalty for 5 of 16 pairs (men's first-serve and second-serve points won and holds; women's aces and serve points won), so the optimum may lie beyond the grid.
* **Penalty by surface.** Men's holds favour a lighter penalty on clay (10×: 0.85 against 30×: 0.78) but a heavier one on grass (0.31 against 0.78) and hard (0.05 against 0.18). A penalty per surface is indicated.
* **Section 3.2 overstates.**
  * "Net worse for every statistic" is wrong for women's break points saved: twice the memory scores +0.023 against +0.016.
  * "A two-timescale model ≤ +0.01" is extrapolated, not tested. The double-memory runs lengthen the level's memory as well.
* **Persistence (section 3.3).**
  * (a) The adjusted-against-raw comparison is confounded by shrinkage: ridge-shrunk adjusted values against unshrunk raw means. "Opponent adjustment sharpens it" is therefore not shown, and ace suppression goes the other way (0.25 against 0.32).
  * (b) *Inf:* There is a tension. The persistent deviation is 0.67–0.93 of the level spread, but at the chosen penalties the estimated deviations' SD is only 0.16 (serve) and 0.20 (return) of the level's for men's holds on clay. The decayed window passes on only about a quarter of a stable trait. That is the case for a long-memory deviation, which section 3.2 did not test.
* **`diagnostics_priced.csv`.**
  * *Obs.* The in-sample block gains (+0.62 to +0.87) equal the expected over-fitting of k/(2N) (0.54–0.81). They are not evidence.
  * *Obs.* Fitted on 2013–2016 and scored on 2017–2018, every gain is ≤ 0. The women's −2.52 [−3.99, −1.06] is partly the 2013–2014 hold gap.
* **My check (`priced_check2.py`).** Annual expanding refits, outcomes 2015–2018 only; positive means the net shift helps.
  * Closing price + net shift (serve points won, holds): men +0.03 [−0.25, +0.32] (7,834 matches), women +0.07 [−0.66, +0.79] (4,935). Both ties.
  * With today's 21 IOS inputs as controls: men −0.04, women −0.03. Both ties.
  * *Inf:* No unpriced surface signal can be detected. This matches the market-anchoring study's section 6.3.

## 3. Representation and protocol

**The reference model is mis-calibrated.** This is the main finding (*Obs*: `cmp_local_paid.py`, `shrink2.py`; all 23,819 matches of 2022–2026).
* The local base (4-seed mean) **ties** the recalibrated price: +0.54 [−0.35, +1.42].
* The paid thinking refit beats the same price: +1.19 [+0.57, +1.81]. It also beats the local base directly: +0.65 [+0.12, +1.19].
* The local model's deviations from the price are 59% larger (SD 0.215 against 0.135 logits), and the two models' deviations correlate 0.86.
* One slope per tour on the local logit, fitted on 2019–2021, is 0.886 for men (about 0.9, the softmax temperature) and 0.964 for women. Applied to 2022–2026, it lifts the local base to **+1.20 [+0.51, +1.89]** against the price.
* The paid fit against the recalibrated local model is −0.01 [−0.39, +0.37]: a tie, so the two are level.
* The recalibration's gain over the raw local model, season by season: +0.48, +0.83, −0.02 (a tie in 2024), +1.57 [+0.84, +2.30] in 2025, and +0.35.
* *Inf:* There is also a bias channel. The net shift correlates +0.06 to +0.23 with the price's log-odds. An over-confident model is punished for pushing favourites further, so any arm whose change moves with the favourite gains or loses log loss through calibration rather than information.

**Seed variance is missing from the interval.** *Obs* (`seed_var.py`): single-seed pooled log loss varies with SD 0.068 (2022–2026). The seed SE of a difference between two 4-seed means is about 0.048, against a block SE of 0.075 for seed-against-seed differences. The intervals are 7–19% too narrow.

**Power.** *Obs/Inf.* On 23,819 matches the paired SE in milli is about 2.8 × the SD of the per-match logit difference between arms. Seeds differ by 0.023–0.028 logits, which gives an SE of 0.075.
* The minimum detectable effect (80% power, seed variance included) is about 0.25 if an arm moves forecasts no more than another seed does, and 0.4–0.65 if it moves them by 0.05–0.08 logits.
* That is 20–50% of the base's whole recalibrated edge.
* The prior evidence (section 2 above and the market-anchoring study) puts the plausible effect well below that.

**Validation.**
* The choice rule's "if neither is ahead" is undefined.
* 2020 has no grass and an October Roland Garros.
* Choosing on raw forecasts inherits the calibration channel.

**What a tie would mean.**
* It means the arm adds less than about 0.3–0.6 through local TabPFN at a fixed temperature. It says nothing about the paid model, the idea, or the market.
* Say this before the test, and pre-register the follow-ups.

## 4. Proposals

* **P1, `snet1`: the 54 inputs plus one column.** The column is Δnet_spw = Δ(iosO_spw) + Δ(iosD_spw), where each Δ is the surface-effective A − B value minus today's A − B value, built from `srf_O_eff`/`cur_O` and `srf_D_eff`/`cur_D` in `surface_features.parquet`. It is the surface model's change in A's expected serve-and-return point advantage on this surface. Why it is better:
  * It is the whole innovation, including the hard-court level correction R2 misses.
  * One dimension carries it: Δnet_spw and Δnet_hold correlate 0.86–0.94.
  * It is nearly independent of today's points matchup (|r| ≤ 0.17).
  * One column replaces eight, so there is less dilution.
* **P2, `siid`: the 54 inputs plus one column.** The column is Δ logit P(A wins) from the iid point model. Set p_A = expit(μ_spw,tour,surface + O_eff,A − D_eff,B), and p_B the same way. Compute the match probability with `in_best_of`, once with surface-effective ratings and once with today's, and take the difference. It puts the nudge on the odds' own scale, weighted by format and closeness. *Inf:* TabPFN should read it most easily.

## 5. Priorities

**MUST-FIX before the test**

1. **Recalibrate each arm.** Fit one slope per tour on each arm's own logit using 2019–2021, and apply it to 2022–2026. Make the primary endpoint the recalibrated comparison and report the raw one as secondary. For choosing the arm, cross-fit inside validation: fit on two seasons, score the third.
2. **Widen the interval for seeds.** SE² = SE_block² + (s²_arm + s²_base)/4, where s is the SD of single-seed pooled log loss.
3. **Pre-register power.** Compute the SD of the arm-against-base logit difference on validation, state the minimum detectable effect, state that the expected effect is below it, and list the follow-ups for a tie: the linear residual check (SHOULD item 2) and the early-season subgroup.
4. **Define the choice rule precisely.** For example: "the arm with the larger recalibrated, cross-fitted gain over base; R1 if both are ≤ 0."
5. **Fix the cache.** Store h, κ, κ_E and κ_F in each `.npz` and check them on load, before any re-tune.
6. **Report only out-of-sample "priced" rows,** and flag the women's hold gap.

**SHOULD consider**

1. **Replace R2 with P1,** or add P1 as a third candidate. For any arm that adds columns, add a placebo arm: the same columns permuted within tour × surface × season.
2. **Add a linear residual check.** Fit logit p = a·logit p_base,recalibrated + b·Δnet_spw on 2019–2021 and score it on 2022–2026. It is the lowest-variance test of the same question.
3. **Extend the tuning, on 2013–2018 only.** Add a 100× penalty, a penalty per surface, serve-only variants for double faults and first serves in, and a long-memory deviation estimated from pre-match residuals.
4. **Pre-declare a 2022–2024 against 2025–2026 split** for the 2025 data change.
5. **Fix the wording of section 3**: section 3.2, the adjustment claim in 3.3, and "clay and grass are where it matters".

**NICE to have**
* Indoor hard as a separate surface for men.
* Restore the men's 2018 odds.
* Eight seeds.
* Justify design changes with 2013–2021 evidence, not the 2022–2026 scores in `oos_scores.csv`.
