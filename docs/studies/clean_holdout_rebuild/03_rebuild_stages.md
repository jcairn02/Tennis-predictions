# 03: What has to be rebuilt, and how

The rules are [01_contract.md](01_contract.md). Paths are relative to the repository root. "D-fitted" means tuned on outcomes of 2013–2018 (or 2010–2018 statistics) and kept. "Axis" means the current choice becomes one of several alternatives, chosen on D. "Mechanism" means set by a written rule before any score.

## 1. Inventory

### Data (outcome-agnostic; applied to every season before stage 3)

| Component | State today | Action |
|---|---|---|
| Stage 0 matches (`predictability_diagnostic/stage0_matches.parquet`) | rebuilt 7 Oct; results to 5 Oct | refresh, then freeze with a hash |
| Known data faults (`docs/studies/input_data_audit/README.md`) | most corrected at source by the [8 Oct decision](../../decisions/2026-10-08-corrupt-data-fixes.md), wherever three independent reviewers agreed, applied at the coordinated Stage 0 rebuild planned for 8 Oct; the rest open | see the list below |
| Odds (`stage1_odds.parquet`) | tennis-data to 27–29 Sep | refresh; men's 2018 joins (2,620 matches with the average close); margin removal unchanged; Pinnacle as a sensitivity only up to Jan 2026 |
| Match clock (`match_timing/timing.parquet`) | 7 Oct | `src/eda/match_timing/refresh.py` |
| Speed panel (`serve_speed_tabpfn/`) | ManTennisData, AO/RG, Slam feeds | refresh; filter constants frozen (tuned on speeds ≤ 2022, without results) |

**The known faults.**
* **Corrected by the 8 Oct decision** (three-reviewer consensus, from raw files and independent records):
  * WTA events of Feb–Aug 2015 counting serve points without double faults;
  * box scores exchanged between winner and loser (Abu Dhabi and Phillip Island 2021, among others);
  * Adelaide 2 2022 carrying 2021's box scores;
  * box scores copied from another meeting of the same pair;
  * players split across two ids (nine women from June 2026, and two others);
  * mis-written or frozen ages;
  * seven odds rows.
* **Still open**, each to be decided on data evidence alone, applied to every season and logged:
  * Roland Garros 2022–25 and the Paris Olympics booking second serves as first (no per-match record is held);
  * the split votes (some candidate exchanges, three in-play odds averages, same-pair copies);
  * IOS scale drift with the ITF data of 2025–26;
  * women's workload reading "rested" after the splice;
  * 130 impossible serve-speed records. Their exclusion table is written but not applied, and applying it to the live panel is the owner's call.

None of these may be decided by looking at how the model does (Q19).

### Features: every family rebuilt over 2010–2026, with its axes

| Family | Columns now | Constants | Rebuild |
|---|---|---|---|
| Ratings: overall Elo, offset Elo + switch pairs; blend and surface-only Elo | 6 (+ alternatives) | K tuned on 2013–18 | D-fitted constants; **axis**: blend / offset + switch pairs / overall only |
| Games-weighted Elo; serve/return ratings through the iid model | 2 | 2013–18 | D-fitted; candidates |
| TrueSkill Through Time (leak-proof; decided and offset forms), Glicko-2, TrueSkill, correlated surfaces | in the store (`alt__`, `rt__`) | 2013–18 | candidates (TTT costs about 20 min per pass) |
| Two-week profile: 12 adjperf + 4 adjdef + total points | 17 | memory, K and τ tuned in-sample 2013–18 | D-fitted; **memory axis**: 1, 2, 4 or 8 weeks, or 52 weeks. 1, 4 and 8 weeks need building (Stage B code with h3 changed; nothing else retuned) |
| Short-memory IOS points matchup | 1 | κ and τ D-fitted; **memory H-exposed** | **axis**: none / 4 / 13 / 26 weeks (26 needs building) |
| 52-week points matchup | 1 | rule | candidate |
| Long-memory IOS, offence/defence by statistic, and products | 21 | 2013–18 | **axis**: pooled / surface; products in or out |
| Load: sets over 14 days; alternatives sets over 7 days, minutes | 1 (+) | rules | candidates |
| Age, age² | 2 | rule | candidates |
| Context: tour, surface, level, indoor (men), best of, round | 6 | rules | scaffold; women's indoor (`fp__f09_venue__f09_indoor`) a candidate |
| Feature-interactions columns (`fi__`, `fp__`): rest, break length, matches since the return, matches at this event, venue pace, and others | about 216 on the menu | screened on 2014–2024 (D) | candidates, apart from the 10 that read the current model's forecast (mechanism exclusion) |
| Level sums (`lv__`), player background (`pp__`), ranks, height, hand | in the store | rules | candidates |
| Market-internal columns (`mk__`, B-ANCHOR) | 8 | — | excluded by mechanism (Q10) |
| Serve speed | stage 2, 28-day memory | filter ≤ 2022 (without results); τ = 0.05 set before 2024–26 was read | **axis** (men): none / column in stage 1 / stage-2 adjustment; memory 14 or 28 days; τ kept or given an axis (Q12) |

**Store.**
* Rebuild the feature-universe store (`src/eda/feature_universe/`) over every season, men's 2018 and the post-frame matches included, with the axis variants added.
* Run `src/eda/match_timing/probe.py` on every cross-player column.
* Copies are collapsed by the registry's rules, as today (`menu.csv`).

### Model

| Item | Now | Rebuild |
|---|---|---|
| Learner | local TabPFN-3.5 | **mechanism**: the owner's choice, before any tennis result, with a prior from the UFC project. A D check against TabICL and ridge is reported, not decisive (Q6) |
| Settings | 8 estimators, temperature 0.9 | 8 estimators (rule). Temperature: neutral 1.0, or {0.8, 0.9, 1.0} on D with the interior value as tie-break (Q7) |
| Training floor | 2013 | rule |
| Symmetrisation, seeds | both orientations; seeds 0–3 | the same; 3 seeds during selection, 8 for the final design |
| Calibration | one slope per tour, walk-forward from 2019 | **axis on D**: fixed or walk-forward × start 2016 or 2019; tie to walk-forward from 2016 (neutral: more data). Also a two-part form: one slope for the close, a separate scale for the model's disagreement with it (Q29) |
| Training window | expanding from 2013 | **axis on D**: expanding (neutral) / the last N seasons / recency-weighted (Q28) |
| Stage 2 | the adjustment, 28 days, τ 0.05 | decided on D (men, 2022–2024) as an axis (§5) |

## 2. Stage 0: freeze, seal and the clean room

1. **Seal H-sealed.** Write `data/studies/feature_provenance/seal.json` (the feature-provenance plan, phase 0): the rule and today's match ids, with no results.
2. **Hash the inputs** (Stage 0, odds, clock, speed panel) into `data/studies/clean_holdout_rebuild/snapshot.json`.
3. **Create the clean room.** A folder holding only the D tables (written in stage 3), the selection code and this protocol. Executors run with it as their working folder. Their tool logs are kept for the holdout auditor.
4. **Start the logs:** `look_ledger.md` (every touch of H outcomes) and `decision_log.md` (every ruling).
5. **Commit or hash.** Git's last commit predates every feature study (23 Sep 2026). A commit, or a hashed manifest of `src/` and `docs/` taken now, gives the rebuild a dated starting point (owner's call).

## 3. Stage 1: data

Refresh and apply the inventory's data actions. Each fix goes in a changelog with its evidence: source against source, never the model's errors. Rebuild Stage 1's odds link (men's 2018 joins) and the match clock.

## 4. Stages 2–3: features, quarantine

**Stage 2.**
* Rebuild every family at its frozen constants over 2010–2026, plus the axis variants.
* The rebuild steps of the current pipeline are listed in the [offset-Elo decision](../../decisions/2026-10-06-offset-elo.md) and the [surface-IOS decision](../../decisions/2026-10-06-surface-ios-profile.md).
* Their checks against the frozen 5 Oct upload must be re-based: equality is now checked against the new snapshot, and the differences are reported.

**Stage 3: quarantine.**
* Split the store into a D store (seasons ≤ 2024) and an H store (seasons 2025–2026, events through the look date). Hash both.
* The H store goes in a sealed folder outside the clean room.
* A test asserts that no table in the clean room holds a season after 2024.

## 5. Stage 4: pre-registering the selection

Written into `decision_log.md` and hashed before the first exact score.

**1. Scaffold (mechanism).** The odds (`odds_logit`), overall Elo and the six context columns: the anchor, a base rating and the description of the match.

**2. Families and axes.** About 20 families. Each enters whole, with its axis members as alternatives. Examples:
* blend / offset / overall Elo;
* the two-week profile at 1, 2, 4, 8 or 52 weeks;
* pooled or surface IOS, with products in or out;
* the short IOS matchup: none / 4 / 13 / 26 weeks;
* speed: none / column (stage 1);
* rest and break length;
* matches at this event;
* venue pace;
* age;
* load;
* the alternative ratings;
* the background group.

Every axis names its **neutral member** in advance: the plainest or longest form, or "none". Ties go to it.

**3. The scoring unit: an era fit.**
* **E1:** TabPFN trained on 2013–2019 forecasts 2020–2021.
* **E2:** trained on 2013–2021, it forecasts 2022–2023.
* Each fit uses 3 seeds and is symmetrised.
* **Slopes.** The model's slope comes from its forecasts of the preceding seasons: E1 from a fit on ≤ 2017 forecasting 2018–2019; E2 from E1's forecasts. The close is recalibrated the same way.
* **The score** of a list is its pooled paired gain over E1 ∪ E2, against the list it extends, with the four-week-block interval. Era fits cost two fits per seed instead of one per season (Q9).

*Items 4–7 were redrafted on 9 Oct 2026, after the owner ruled on Q8 in principle. The ruling is a decision record on adoption by kind of change, which is off limits to reviewers under `04` §1. Its content for this protocol is stated in item 4 below. The first draft's items 4–7 are kept at the end of this section.*

**4. The cluster tree, and top-down removal.**
* **Why the redraft.** The first draft added families forward, one at a time, each against a one-SE bar. That is one-at-a-time testing at the family level:
  * families that only help together never enter, since neither passes alone;
  * a small real family passes the bar half the time or less;
  * yet with about 20 families searched and no real effects, the best one clears one SE about 97% of the time: 1 − Φ(1)^20, the adoption framework's statistics review, finding 9. *Not linked: that review quotes 2025–2026 results elsewhere, so it is outside this blinded brief.*

  **The principle now:** decide at the coarsest level a comparison can see. Below that, decide by structure and simplicity, not by readings.
* **The tree.** It is fixed in the pre-registration, before any exact score.
  * **Level 0, the scaffold** (item 1): always in.
  * **Level 1, about six blocks,** each large enough for its removal to be seen:
    * the ratings beyond the scaffold (the offset Elo pairs, games-weighted Elo, the alternative ratings);
    * the per-statistic profiles (the two-week profile, the long-memory IOS profile, the short IOS matchup, serve-and-return ratings, points over 52 weeks);
    * schedule and load (rest, break length, matches at this event, sets in 14 days, venue pace);
    * player background (age, and the background group);
    * speed, as the stage-1 column (stage 2 stays § 7's separate decision);
    * the remaining families, grouped by mechanism before any score.
  * **Level 2, inside the per-statistic block:**
    * serve, return, pressure (break points) and style (aces, double faults, first serves in);
    * within each, offence and defence, short and long memory, differences and matchup products;
    * statistics the player drives against those the opponent drives. The level-evidence study's role A measured this within the main tour, without match results.
  * **Merged without reading results:** families whose columns correlate strongly on D's features (|r| ≥ 0.8 on average) become one node. Removal cannot tell substitutes apart.
  * **Each node** names its neutral member, as the axes do (item 2), and has a column budget.
    * A node over its budget may enter compressed: its first principal components on D's features, which reads no result.
    * The compressed form is an axis member against the full columns, and ties go to it.
* **The rule, top-down.**
  1. **Start from the full list:** the scaffold, plus every level-1 block at its neutral members.
  2. **Level 1.** Score the removal of each block: the pooled paired gain over E1 ∪ E2. Call g the gain of keeping it.
     * **A block goes only when the comparison shows it is not worth its columns.** That means the upper end of g's 95% interval is below the block's column price c. Its shuffled twin measures c: the same columns permuted within each era, three draws.
     * **Otherwise it stays whole,** whether its reading is better or unresolved. The tree was fixed by mechanism before any score, so an unresolved block is not dropped on noise.
     * **No winner's-luck correction.** Each block's keep-or-drop is its own question, declared in advance, not a pick among blocks.
     * **A power check before any score.** The pre-registration states each block's plausible effect and the comparison's expected resolution. A block expected to sit below resolution is merged with its nearest block, or kept whole by mechanism.
     * *Corrected the same day, after an independent review:*
       * the first redraft dropped a block unless B·(g − sel) > c, so a block below resolution went on noise;
       * on D, removing the 21-input long-memory profile read −0.29 [−0.63, +0.04] mLL at the close (2020–2024; + = without it better), which is unresolved.
  3. **Level 2,** inside each kept block. Descend only where a node's plausible effect is at or above the comparison's resolution (its 95% half-width). Where it is not, the block stays whole: members are never pruned on noise.
  4. **Axes,** inside each kept node: memories, representations, pooled or per surface. They are chosen on E1 ∪ E2 with the winner's-luck correction; ties go to the neutral member.
  5. **Stop** when no node left is resolvable.

**5. Stability.**
* Each level-1 and level-2 decision is repeated:
  * in each era alone (E1, E2);
  * on 200 bootstrap resamples of E1 ∪ E2's four-week blocks. These reuse the same fits: the scored matches are resampled, not refitted.
* A node is dropped only if dropping it is supported in both eras and in at least two thirds of the resamples. Otherwise it stays, and an unstable reading is flagged.
* *Corrected the same day:* the first redraft kept a node only if it was kept everywhere, which pushed toward removal.

**6. Confirmation (E3, 2024).**
* Read the frozen list and every leave-one-node-out variant on 2024, trained on ≤ 2023.
* A node whose removal improves 2024 by more than 1 SE is flagged to the owner. It is not removed automatically.
* **The fragile window** (2016–2019) is read the same way. A sign flip is labelled a regime bet.

**7. Finalists and winner's curse.**
* **Finalists:** about four:
  * the top-down list;
  * the full list (the scaffold and every block);
  * the lists that swap in the runner-up member wherever an axis was decided within 1 SE.
* **Scoring:** each is re-scored with two new seeds on E1 ∪ E2 and on E3.
* **Winner's-curse correction.** The published D estimate is the winner's mean minus σ · m_F, where σ is the SE of the difference between finalists and F is the number of finalists.
* **Choosing among finalists.** The best corrected D estimate wins. Ties go to the smaller list.

**8. Per tour.** Report each family's gain by tour. The pre-written rule:
* a family that is worse for one tour by more than 1 SE, while better for the other, enters gated by tour (0 for the losing tour);
* otherwise both tours share it, as the pooled model does today (Q11).

**9. Costs.**
* **As redrafted (9 Oct 2026),** at 6 fits per evaluation and about 25–35 s a fit:
  * about six level-1 removals, up to about fifteen level-2 removals, and about twenty axis evaluations;
  * plus a three-draw twin for each block.

  That is roughly 400 fits, about 3–4 GPU hours. The stability resamples reuse those fits.
* **With the finalists and the rehearsal,** well under the first draft's estimate below.
* **The first draft's estimate.** About 40 candidate evaluations per round × 6 fits, plus twins for the round's leader, came to about 250 fits a round: about 2 hours a round for about 8 rounds. With the backward pass, finalists and the rehearsal, about 15–40 GPU hours.
* A pilot measures the fit times first.

**The first draft's items 4–7, superseded on 9 Oct 2026** (kept for the record):
* *4. Add rule (forward).* In each round: score every family not yet in, with each of its axis members; keep the family's best member. The round's best family enters only if its gain exceeds the noise bar, one paired SE, and it beats its own shuffled twin: the same columns permuted across matches within each era, three draws, the same members. Stop when no family passes. Ties between members go to the neutral member.
* *5. Backward clean-up.* Try removing each added family. Remove it if the pooled gain improves by more than the noise bar.
* *6. Confirmation (E3, 2024).* As now, by family.
* *7. Finalists:* the forward list; the backward-cleaned list; and the lists that swap in the runner-up member wherever an axis was decided within 1 SE. The scoring, the correction and the choice among finalists were as now.

## 6. Stage 5: rehearsal

Run stages 4–7 on D′ = seasons ≤ 2022:
* choosing eras 2018–2019 and 2020–2021;
* confirmation 2022;
* pseudo-holdout 2023–2024, scored once.

This is process evidence, not a result about the model. It asks: does the chosen list beat the scaffold on the pseudo-holdout, and by how much less than on its choosing eras?
* **A large drop** means the selection overfits D. Change the protocol now, before H is used.
* **A reasonable transfer** means the protocol is kept and rerun on all of D.

(2023–2024 have been read by earlier studies; that does not matter for a process check.)

## 7. Stages 6–7: selection, and the stage-2 decision

* **Who runs it.** The executors run stage 4's rules in the clean room. Every score is logged per round: members, gains, intervals, twins and the rule's verdict.
* **Deviations.** A deviation from the pre-registered rules is logged before it is acted on, and needs the owner's ruling if it changes a choice.
* **The stage-2 decision (men).** With stage 1 frozen:
  * write stage 1's walk-forward forecasts for 2019–2024;
  * choose among none / adjustment (14- or 28-day memory, τ as registered) on the paired gain over 2022–2024 against "none", ties to "none".
  * The speed column was already a stage-1 candidate. If it entered there, the adjustment is not also applied.
  * Speed data for 2022–2024 come from ManTennisData (ATP tour level from October 2021) and the Slam feeds.

## 8. Stage 8: the H forecasts and the one look

1. **Freeze.** Hash the design: list, members, settings, calibration rule, stage 2. Log it.
2. **Forecasts.** A forecasting script writes H forecasts without reading results:
   * 2025 from fits on ≤ 2024;
   * 2026 from fits on ≤ 2025;
   * 8 seeds;
   * slopes and stage-2 coefficients refitted by their frozen rules;
   * plus the D-only variant.
3. **Score.** A scoring script reads the H results once and writes every pre-registered estimand.
4. **Correct.** Open the auditor's sealed bias estimates and apply them (`02_contamination_and_forecast.md` §4).
5. **Log the look.** Write the look into `look_ledger.md` with the hashes.

## 9. Stages 9–10: report and continuation

**Stage 9: the report.**
* The primary estimand three ways: raw, corrected and H-sealed.
* The secondary estimands.
* The contamination diagnostics.
* The current model as a report-only anchor.
* The decision under the pre-registered responses.

**Stage 10: continuation.** H-sealed keeps accruing. Each checkpoint (about 2,500, 5,000 and 7,700 sealed matches) is one logged look at the frozen design.

## 10. Executor instructions (to hand over with the clean room)

* Read only this folder and the clean room. If a needed fact is missing, log the gap and ask the owner. Do not search the repository for it.
* Never open the H store, the sealed estimates, or any file under `docs/studies/` outside this folder.
* Before each round, write what you will run. After it, write what you ran and the rule's verdict.
* If a rule is ambiguous, take the neutral member and log the ambiguity.
* No result of the current model is a target. Its values are not baselines, tie-breaks or fallbacks.

## Open questions in this document

Q5 (re-tune the 2013–2018 constants on recent D eras?), Q8 (forward families, a backward walk, or both), Q9 (era fits or per-season fits), Q10 (market-internal columns), Q11 (per-tour rule), Q12 (stage-2 axes and τ), Q14 (is the clean room enough?), Q17 (the rehearsal's worth), Q18 (men's 2018 in D), Q19 (the data-fix list), Q21 (missing speed in stage 2), Q22 (the scored population), Q23 (seeds), Q24 (the finalist correction).
