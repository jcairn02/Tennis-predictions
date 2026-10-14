9 October 2026 · The independent reviewer's independent position (round 1), written before seeing the lead's in the [lean review](../README.md)'s debate: an Opus 5.5 subagent with read-only access to the repository. It ran its arithmetic from the session's scratch folder; copies are in `src/eda/lean_review/`, with their printed outputs in `data/studies/lean_review/` · **Verbatim below.**

---

# Round 1, independent reviewer: stage 2, the per-surface IOS profile, the short IOS memory

**Keys.** mLL per match. **+ = the part (or the first-named arm) is better.** Intervals are 95%. "obs" = stated in a file; "inf" = my reasoning; † = my arithmetic on documented numbers (`scratchpad/debate/arith.py`). I scored no matches.

**Two facts that change the frame (obs).**
* **Early prices exist on ≤ 2024.** The framework says they exist only for 2025–26 (README §1). OddsTrader holds **Pinnacle's timed opening line for Jan 2018 – Sep 2025**: a median 35.5 h out, 76–96% of matches a season, and 3.94 mLL [2.18, 5.69] softer than its last line (`odds_sources` §2, §3.4). So each part can be read at an early sharp price on 2020–24 without spending 2025–26.
* **The live input is now Pinnacle's current line** at every venue (`2026-10-09-pinnacle-first-odds-input.md`). The Polymarket-fed 24-hour readings no longer describe the decided configuration.

## 1. Stage 2: the speed adjustment (men)

1. **Why it was included (obs).**
   * The pre-registered primary, speed as a TabPFN column, read +0.07 [−0.05, +0.18]: TabPFN used about 8% of the information.
   * The information beyond the base read +0.065 [+0.012, +0.118].
   * The nudge, a secondary, read +0.41 [+0.04, +0.78] on men 2024–26 (`serve_speed_tabpfn` §6).
   * The 28-day memory came after two more outcome runs on those same seasons.
2. **Does that logic still hold?**
   * **The information: yes.** It replicated blind on 2025–26 (+0.103 [+0.029, +0.178]). It has a result-free mechanism (+0.33 pp first-serve points won per SD of speed form). The closing odds explain 0.3% of its variance. It is the only re-tested result that "held" (`feature_provenance` §5), and it is exactly the owner's point-level thesis.
   * **The procedure: not yet.**
     * 2020–24 reads −0.26 [−0.59, +0.06]. Adding 2025 (+0.32) and 2026 (+0.73) gives **2020–26 ≈ −0.06 [−0.31, +0.19], P(better) 0.32†**: break-even over seven walk-forward seasons.
     * The loss is one season: 2023, −1.26. Its b̃ of 0.07 was fitted on three sparse seasons plus 2022's +0.15, and met a season effect of −0.05 (`infosys_atp_backfill` §5).
     * The seasons disagree (I² ≈ 50%), but the shrinkage uses the pooled maximum-likelihood SE. A heterogeneity-aware posterior would have set b ≈ 0.029 for 2023, giving −0.45 instead of −1.43 on the backfill study's approximation†. That is hindsight, not credit, but it names the flaw.
   * **Its target was never read.**
     * *Inf:* the price barely holds speed form, so the gain at an early line should be at least the close's.
     * **A gate gap (obs):** Challenger speeds enter the live `spd_L` unguarded. There are 940 rows in 2026, against about 89 a season when b̃ was fitted (`lower_level_evidence` §1.4).
3. **Options:** keep (checklist item 7), keep with changes, shadow, remove.
4. **Recommendation: keep it live as item 7's logged lean (no stakes credit), with three changes.**
   * **(a) Set b to the posterior mean of the season-effect mean,** under a N(0, 0.05²) prior, with the between-season variance included. That is ≈ 0.032 for 2027 instead of 0.0444†. Expected next-season gain, new b against current†: on 2019–26 evidence +0.22 vs +0.23; on 2019–24 only +0.06 vs +0.02; with no signal −0.12 vs −0.24; in a −0.05 season −0.51 vs −0.77.
   * **(b) Restrict `spd_L` to the levels it was fitted on,** and add it to the input check.
   * **(c) Put item 7's checkpoint at ≥ 2,000 men's matches,** with alarms only before that. At 300 matches, the P ≤ 0.2 cut-off drops a true +0.15 stage 2 16% of the time and catches a 2023-size season only half the time. At 2,000: 10% and 91%†.
   * **Framework line.**
     * **Target:** the men's bet-time line.
     * **Provenance:** best of about 3 forms plus 3 memories on 2024–26, on top of a blind-replicated mechanism.
     * **c:** ≈ 0 against shadow (the feed runs either way, and the owner wants it); ≈ 0.05 against removal.
     * **B·(est − sel)** on the 2024–26 reading (+0.38, sel 0.2): +0.008 at τ 0.03 and +0.06 at τ 0.1†.
     * **Where I depart:** τ 0.03 describes TabPFN inputs that overlap the close. This is an output-layer term on information the price lacks. Its structural EV is about +0.15 per men's match (−0.12 to +0.25), with roughly a one-in-three losing season. Shadow forgoes that EV and saves nothing.
   * **Confidence: 60%.**
5. **What would change my mind:** the decision bootstrap putting the form and memory luck above about 0.3; 2025–26's effect traced to the newly dense Challenger and Infosys rows; or a sealed season below the alarm. No ≤ 2024 test is decisive (2022–24 are the only dense seasons, and they are spent). One declared check is worth adding: move stage 2 to shadow if, at Pinnacle's opening line on men 2020–24, its 95% interval lies below 0.

## 2. The per-surface long-memory IOS profile (21 inputs)

1. **Why it was included (obs).**
   * The pooled profile entered on 2 Oct against a null linear result (Stage D, with products: −0.21 (−0.67, +0.26)), on the owner's per-statistic thesis. TabPFN then leaned on it most (shuffle shares 0.62 and 0.74).
   * The per-surface build tied its locked primary at the close: +0.01 [−0.10, +0.13].
   * The owner kept it on a criterion declared afterwards: "neutral with the odds, + without… especially since we may bet early". Men without the odds read +0.83 [+0.39, +1.27].
2. **Does that logic still hold?** The owner's own criterion, re-applied with the offset Elo in (`surface_rating_race/composed_results.csv`; + = per surface better):
   * **Neutral with the close: still true.** Both tours −0.01 (P 0.39); men +0.00; women −0.03.
   * **"+ without the odds": now men only.** Men +0.19 [−0.05, +0.42] (P 0.94); women −0.06 (P 0.29)†. The offset Elo absorbed about 80% of the men's +0.84.
   * **"Bet early": unanswered.** Polymarket 24 h: −0.06 [−0.43, +0.31]. That reading is uninformative (SE 0.19), and that price is no longer the live input.
   * **Women:** no reading at any price ever favoured it. Without the odds it was worse in 2022–24: −0.73 [−1.14, −0.32].
   * **The tuning leaned to pooling:** the heaviest penalty tested (30×) was best for 5 of the 16 tour × statistic cells.
   * **The cost:** 1.7 times the pooled IOS compute, and more parameters exposed to finding #6 and the ITF data due about 31 Oct.
3. **Options:** keep; pooled on both tours (item 8); split (men per surface, women pooled); drop the whole profile; shadow, which is pointless for inputs (live data cannot settle ±0.1 within a decade).
4. **Recommendation: change to pooled, for women now, and for men unless they clear the bar at the target.**
   * **Provenance:** a mechanism, kept on a criterion declared after the test (K 2). **c ≈ 0.01.**
   * **B·est:** at the close (τ 0.03), −0.004 both tours, +0.000 men. Without the odds (τ 0.1), men +0.075, women −0.028†.
   * Women fail everywhere. Men pass only without the odds, a proxy that overstates a sharp-line target.
   * EV for betting ≈ 0 either way (|effect| ≲ 0.05).
   * **Don't drop the whole profile without an ablation:** it is TabPFN's most-used group, and no in-model ablation is documented.
   * **Confidence: 60%** (women 75%, men 55%).
5. **Test (pre-declared).** Item 8's build.
   * **Primary:** Pinnacle's opening line, 2020–24, per tour, seeds 0–3 paired, without OddsTrader's 2021 US Open. **Harm check:** the close.
   * **Rule:**
     * a tour keeps the per-surface build only if B·est > 0.01 at τ 0.05 (about est > +0.03);
     * either tour reverts to per surface if pooled is worse at the close by more than 0.1.
   * **Optional:** the 37-input ablation without the profile. Drop the profile if B·est_drop > −0.03 (τ 0.1; about 0.03 of upkeep saved).

## 3. The short-memory IOS points matchup (`ios_points_short`)

1. **Why it was included (obs).**
   * Stage B added it as an untuned diagnostic after the all-season rundown:
     * given Elo: men +3.72, women +5.02;
     * given Elo and the iid ratings: +0.50 and +0.64;
     * given the odds: +0.13 and +0.01.
   * The audit's ladder before the repairs (2022 on, Challenger and qualifying included), after the two-week adjusted points: men +0.13 [+0.05, +0.20], women +0.25.
2. **Does that logic still hold?**
   * **It duplicates other inputs.** It is one of four points-won aggregates, with `adjperf_tpw_2w`, `points_52w` and `ratings_iid`, and these are priced-in controls under the owner's thesis.
   * **Repaired, it adds nothing measurable beyond the adjusted points:** men −0.013 [−0.091, +0.066] (P 0.37), women −0.052 (P 0.12).
   * **But the repaired history is main-tour only.** The model's leak-proof version keeps every level, and the leak fix barely moved it (r ≈ 0.998, `tabpfn_leakproof`).
     * *Inf:* the collapse reflects the thinner history, so neither figure measures the model's input.
     * Its in-model value is unmeasured.
   * **No selection luck:** pre-2022 seasons pick the same memory.
3. **Options:** keep, remove, change the memory (an axis of the rebuild), or shadow (pointless).
4. **Recommendation: remove it through a drop-one candidate, unless the harm rule fires.**
   * Designing today, an input with no in-model increment wouldn't clear c ≈ 0.01. B·est (τ 0.03): men −0.005, women −0.016†.
   * EV for betting ≈ 0.
   * **Confidence: 55%.**
5. **Test.** The reference frame without the input (57 inputs), seeds 0–3, fitted on 2019–24.
   * **Primary:** both tours at Pinnacle's opening line, 2020–24. **Harm check:** the close.
   * **Rule:** remove if B·est_removal > −0.01 (τ 0.03), i.e. not worse by more than about 0.02.
   * **Flag, not a verdict:** matches whose two players' lower-level shares differ by half or more. That is where a level-corrected short form could matter.

## Summary

* **Stage 2: keep** (item 7's lean, plus a heterogeneity-aware b, a Challenger guard and a 2,000-match checkpoint) · 60% · the speed information replicated blind and lies outside the price; the 2020–24 loss is one season with an oversized coefficient.
* **Per-surface IOS: change** to pooled (women now; men unless they clear the bar at Pinnacle's opening line) · 60% · with the offset Elo in, it reads nothing at the close or at 24 hours, and the offset Elo absorbed about 80% of its no-odds gain.
* **Short IOS: remove,** after a drop-one harm check · 55% · no in-model increment is documented, its one increment test fell to about 0, and it duplicates three points-won controls.
