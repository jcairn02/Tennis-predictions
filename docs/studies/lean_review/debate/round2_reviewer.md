9 October 2026 · The independent reviewer's rebuttals, final positions and joint test plan (round 2) in the [lean review](../README.md)'s debate: an Opus 5.5 subagent with read-only access to the repository. It ran its arithmetic from the session's scratch folder; copies are in `src/eda/lean_review/`, with their printed outputs in `data/studies/lean_review/` · **Verbatim below.**

---

# Round 2, the reviewer: rebuttals, final positions, and a joint test plan

**Keys.** mLL per match; **+ = the named change is better**; intervals are 95%. † = my arithmetic on documented numbers (`arith_r2.py`). I scored no matches.

## The five challenges

**1. Stage 2's realised record argues for shadow: partly conceded; I keep it, now at 55%.**
* **Conceded: the keep case leans on 2025–26.** On strict ≤ 2024 evidence, the heterogeneity-aware posterior for the speed effect is μ ≈ 0.014. That gives about +0.02 per men's match at the best b, and b = 0.032 would read −0.01†.
* **Disputed: the framework's class for stage 2.** The ledger files it under "best of K": decisive after removing the winner's luck. It is not "a pattern found in the scored seasons", which would make it a lead only.
  * The idea has data outside its discovery: it replicated on 2022–24 (+0.090) and again blind on 2025–26, at +0.103 [+0.029, +0.178].
  * What failed outside the choosing seasons was the coefficient rule (b̃ 0.07 in 2023), not the information.
* **Counting 2025–26, with a discount, is legitimate for a part.**
  * The template's own refit uses 2019..Y−1.
  * The provenance audit says to treat 2025–26 as development.
  * Cutting each of 2025 and 2026 by 0.01–0.03 for the memory pick leaves an expected gain of +0.08 to +0.11 per men's match†.
* **Most of the live failure modes are already in the backtest.**
  * Edition offsets are learned as of each match: Wimbledon 2025's +8.5 km/h radar break is inside the 2025 reading.
  * Late speeds are the "today's sources" scenario.
  * A silent collector lets the column decay to 0, which is stage 1.
  * What is new: the Challenger rows, which the guard closes, and code drift, which a speed replay closes (T0).
* **The heterogeneity-aware b fixes a documented flaw; it is not a tune.** The rule's SE ignores I² ≈ 50%, which was documented on 2019–24 before this debate. The fix moves b toward the reference, at a cost of 0.04 or less in the good case. Adopt it on mechanism and claim nothing for it. I concede it cannot be tested cleanly.

**2. The Pinnacle-first base: agreed, the decision waits.** Waiting costs nothing, because no live step reads Pinnacle's line yet.
* A 2020–24 mLL reading would again be dominated by 2023's coefficient.
* What matters is how much the sharper price absorbs: r = β(Pinnacle-first) / β(reference), pooled over 2019–24.
* My prior is little attenuation. That model is level with the reference (−0.02 [−0.34, +0.31], `odds_sources` §5), and speed form's R² on the close is 0.003.

**3. The IOS split and the ablation: both conceded.**
* **One rule for both tours.** Split only if one tour clears the bar and the other is worse with P(better) ≤ 0.2.
* **The cost was too low.** About 0.05 for the profile and 0.06 for the whole IOS chain. That chain covers:
  * items #5 and #8;
  * finding #6;
  * one of the ITF flood's two main entry points;
  * the women's prior bias.

  `ratings_iid` is a separate solve and stays.
* **Declare the ablation and run it first, as a 2×2 with `ios_points_short`.** The two are substitutes, so their effects need not add up.
* **The rule I'd sign:** B·est + c_saved > 0 (see point 5).

**4. Base and target: agreed; the opening-line primary is cheap.**
* **Base:** the Pinnacle-first instance, with a paired scorer.
* **Cost:** opening-line test rows can be predicted in the same fit calls as close-fed rows (same context). Only the base arm's 24 fits rerun, about 13 minutes. Each yardstick gets its own walk-forward slopes.
* **Why bother:** Pinnacle's opener is 3.9 mLL softer than its close. The offset Elo precedent says parts can flip between prices.
* **If the code is late,** run the close as the harm check now and hold the decisions.

**5. What I think is wrong in the lead's memo.**
* **"Every positive reason is gone".** Not for men: their no-odds residual is +0.19 [−0.05, +0.42], P 0.94, hidden by the both-tours +0.07. The conclusion survives, because no-odds is the wrong proxy for a sharp line.
* **"24 h … no support".** With SE 0.19 that reading is uninformative, not evidence against.
* **`ios_points_short`.** By your own flip condition, the repaired −0.013 does not transfer: main-tour-only history, and r ≈ 0.998 between the leak-proof and original IOS inputs. Removal rests on the drop-one test alone.
* **The "P(better) ≤ 0.2" rules ignore cost.** At paired SEs of 0.02–0.03 they fire at −0.017 to −0.025†, and would keep a 21-input profile for a gain below its upkeep.

## Final positions

* **Stage 2: keep** · 55% · Item 7's lean, plus the heterogeneity-aware b (≈ 0.030 for 2027), the Challenger guard and a 2,000-match checkpoint. Subject to T0 and T1.
* **Per-surface IOS: change to pooled, both tours** · 65% · If the profile survives T2.
* **`ios_points_short`: remove** · 55% · Pending T2.

## Joint test plan (fixed now)

**Common to all tests.**

| Element | Setting |
|---|---|
| Base | The Pinnacle-first instance |
| Fits | Seeds 0–3, paired; fitted 2019–24; scored 2020–24. No 2025–26 result is read |
| Calibration | Walk-forward per tour on each arm's own 2019..Y−1 |
| Stages and matches | Both stages; debut seasons out |
| Yardstick (C) | The Pinnacle-first close |
| Yardstick (O) | Pinnacle's opening line (OddsTrader, timed). Without the 2021 US Open; complete cases |
| Also reported | The realisation slope at (O) |
| Outcomes | Proposals only; the owner decides |

**T0: speed replay (a gate; reads no outcomes).** One past day run through the live chain must reproduce the backtest `spd_L` to machine precision, with the Challenger filter on both sides. On failure, stage 2 is off live until it is fixed.

**T1: stage 2.**
* **Arms:** stage 1, and stage 1 + stage 2 (heterogeneity-aware b; Challenger-filtered speeds).
* **Primary:** r, men, pooled over 2019–24, on the same matches and the same `spd_L`.
* **Secondary:** the walk-forward gain, men 2020–24, at (C) and (O).
* **Rule:**
  * keep live if r ≥ 0.5, which means an expected gain of at least about +0.03†;
  * otherwise move it to shadow until the sealed checkpoint;
  * alarm: move it to shadow if the (O) secondary's 95% interval lies below 0.

**T2: the IOS 2×2.** Column drops only; it runs first.
* **Arms:** A0, the base (58 inputs); A1, without the profile (37); A2, without `ios_points_short` (57); A3, without both (36).
* **Primary:** (O), both tours. **Secondary:** (C), plus per-tour flags.
* **Rule:** for each removal X, propose it if B·est_X + c_X > 0 at (O).

  | Removal X | τ | c_X | Bar at the expected SE† |
  |---|---|---|---|
  | Both | 0.1 | 0.06 | est > −0.10 |
  | The profile | 0.1 | 0.05 | est > −0.06 to −0.08 |
  | `ios_points_short` | 0.03 | 0.01 | est > −0.02 |

  * **Veto:** any removal worse at (C) by more than 0.1 with P(better) ≤ 0.1.
  * **Order:** remove both if both qualify; otherwise the single removal with the larger B·est + c; otherwise neither.
  * If the profile goes, cancel #8 and #5.

**T3: item 8, only if the profile stays.**
* **Arms:** A0 against the pooled-profile build, carrying T2's decision on `ios_points_short`.
* **Primary:** (O), both tours. **Secondary:** (C), per tour.
* **Rule:**
  * switch to pooled unless the per-surface build's B·est > 0.01 (τ 0.05, about est > +0.024†);
  * split only if one tour clears and the other is worse with P(better) ≤ 0.2;
  * veto: pooled worse at (C) by more than 0.1.
