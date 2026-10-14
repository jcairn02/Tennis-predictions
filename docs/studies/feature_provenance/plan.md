# Estimation plan: overfitting and design leakage of the current best model

8 October 2026 · Written for the owner and for the session that runs it · A proposal, not a decision. Nothing here has been run except phase 1 (the [audit](README.md)).

**What the plan is for.**
* It measures how much of the current best model's reported edge comes from choices made with the test seasons in view, and how much would survive on matches no choice has seen.
* It sets up a rebuild of the feature selection whose holdout cannot be contaminated by the existing features.

**The rules for every phase.**
* Each phase is pre-registered before its first exact score: the question, the arms, the seeds, the windows, the reading rule and the files, hashed.
* Every read of an outcome is logged in a look ledger, as the serve-speed and feature-interactions studies did.
* Units are mLL (milli-log-loss per match). **+ = the model, or the named arm, is better.** A 95% interval spanning 0 is a tie.

## 1. Terms, and why the holdout's location decides the leakage

**Estimands.**
* **Edge.** E(M, S) is the mean over matches S of (the recalibrated close's log loss minus model M's), × 1000.
* **The comparator.** M58 is today's current best model, both stages, as defined on 7–8 Oct 2026.
* **Total optimism.** O = E(M58, 2022–2026) − E(M58, future matches).
* **Hindsight premium.** HP(T) = E(M58, seasons ≥ T) − E(M_T, seasons ≥ T). M_T is the model a codified selection with no incumbent in any rule would build from outcomes before T only.
* **Selection bias of a choice.** β_j is the expected inflation of choice j's chosen arm, on the closing-line metric, on the window where j was made.
* **Design leak of a rebuild with holdout H.** B(H) is the part of the rebuild's edge on H that comes from choices made with H's outcomes in view.

**The algebra behind the audit's claims (standard).**
1. **The inflation of a picked arm.** A choice picks the best of k arms on window W (n_W matches). Each arm's estimated advantage is its true value plus noise ε_W, the mean of per-match noise with variance s². Picking the best arm conditions on large ε_W: E[ε_W | picked] = β. With k truly equal arms, β ≈ σ_W · m_k, where σ_W is the standard error of the arms' difference and m_k is the expected maximum of k standard normals:

   | k | 2 | 3 | 4 | 5 | 6 | 8 | 10 | 20 | 30 | 50 |
   |---|---|---|---|---|---|---|---|---|---|---|
   | m_k | 0.56 | 0.85 | 1.03 | 1.16 | 1.27 | 1.42 | 1.54 | 1.87 | 2.04 | 2.25 |

2. **How much of it a holdout inherits.** A holdout H has n_H matches, n_C of them inside W. With independent per-match noise:
   * Cov(ε_H, ε_W) = n_C s² / (n_H n_W) and Var(ε_W) = s² / n_W;
   * so **E[ε_H | picked] = (n_C / n_H) · β**.
   * A holdout entirely inside the decision window (2025–2026 inside a 2022–2026 or 2013–2026 window) inherits the whole β. A larger W helps only by making β smaller.
   * A holdout outside every decision window (future matches; men's 2005–2012) inherits nothing.
3. **Choices made on one metric and read on another.** If a choice is made on metric A (no odds, the 24-hour price) and read on metric B (the closing-line edge), B's inflation is β_A · ρ_AB · σ_B / σ_A ≤ ρ_AB · σ_B · m_k. ρ_AB is the correlation of the two metrics' noise. A choice made on a noisy metric leaks into a precise metric only through σ_B.

**Noise levels, read from the studies' intervals** (SE = half-width / 1.96):

| Comparison | SE (mLL) | Per-match sd |
|---|---:|---:|
| Model against the close, men 2022–26 (12,352 matches) | 0.38 | ≈ 43 |
| Model against the close, both tours 2022–26 (23,819) | 0.32 | ≈ 50 |
| Two arms of one model at the close: surface IOS swap / offset-Elo swap | 0.06 / 0.10 | ≈ 9 / 15 |
| Leak-proof refit against the original (correlation 0.9999) | ≈ 0.04 | ≈ 5 |
| Arms without a price | 0.4–0.6 | — |

## 2. Phase 0: seal and freeze (now; no computation; needs the owner's approval)

1. **The fresh holdout.**
   * **Definition.** H_fresh = every match of an event starting on or after 29 Jul 2026. The main-tour main draws are the primary population; other levels are recorded.
   * **The seal file.** Write `data/studies/feature_provenance/seal.json`, holding:
     * the rule;
     * the match ids known today, with no result field: 1,023 main-tour rows in the 7 Oct Stage 0, of which 1,014 are completed or retired;
     * the split into 787 rows scored only without odds by the 30 Sep build, and 227 untouched;
     * the date.
   * **Reads after sealing.** No study reads H_fresh results except through a pre-registered look entered in `docs/studies/feature_provenance/look_ledger.md`.
   * **Price-only studies** (market against market, no model forecast) may continue, logged, and never joined to a model forecast.
   * Report the 227-plus-later subset as a sensitivity at every look.
2. **Freeze M58 as the comparator.**
   * Write a manifest with SHA-256 hashes of:
     * `model_frame.parquet` and `model_inputs.json`;
     * the stage-2 column and coefficient files (`serve_speed_tabpfn/adaptive/`);
     * the code paths of both stages.
   * Git has no commit after 23 Sep 2026. The manifest gives the freeze a date whatever the owner decides about committing.
3. **Pre-register phase 6** (the prospective read) before any H_fresh forecast is written.

## 3. Phase 2: training size against era (cheap; already-seen data)

**Question.** In 2015–2019 the model ties the close; from 2020 it leads by about +1.5 (audit section 4). Is the early tie a smaller-training-set effect? Training grew from 10,051 matches (2015) to 50,003 (2024).

**Arms.** All use stage 1 exactly (local TabPFN-3.5, 8 estimators, temperature 0.9, symmetrised), seeds 0–2, test seasons 2015–2024:

| Arm | Training set for season Y |
|---|---|
| expanding | 2013..Y−1 (exists: `feature_interactions/local`, `surface_rating_race/local`) |
| recent-15k | the most recent 15,000 matches before Y |
| random-15k | 15,000 matches drawn at random from 2013..Y−1, three draws |
| recent-25k | the most recent 25,000 matches before Y, for Y ≥ 2019 |

**Calibration.** For each arm, walk-forward slopes per tour, fitted on that arm's own forecasts of 2015..Y−1. The scored seasons are 2016–2024; `edge_by_season.py` holds the scoring code.

**Estimand.** Δ_era(arm) = E(2020–2024) − E(2016–2019), with a paired interval over four-week blocks.

**Reading.**
* If Δ_era shrinks to about 0 under the fixed-size arms, training size explains the pattern, and the full history matters more than the era.
* If Δ_era stays near +1.3, size does not explain it.
* Random-15k against recent-15k separates "more data" from "more recent data".

**Coverage control.** Repeat the expanding arm on matches where every box-score input exists for both players. Women's service-game statistics cover only 74% of 2013–2021, so coverage itself changed over time.

**Men's 2018, one look.** 2,620 matches with the average close; never in a market test.
* Build their frame rows. The features exist; the frame dropped these matches for want of odds, and Stage 1 has odds since 7 Oct.
* Forecast with training on 2013–2017 and score once against the recalibrated close (slopes from 2014–2017). Leave every other season's training set unchanged.
* **Pre-registered reading.** The era account predicts about 0 (SE about 0.9). An edge above +1.8 would contradict it.

**Cost.** About 10 seasons × 4 arms × 3 seeds ≈ 120 local fits, plus 3 for men's 2018: a few GPU hours.

## 4. Phase 3: the decision bootstrap (cheap; CPU; stored forecasts)

**Question.** By how much did each choice made on 2022–2026, or on windows containing it, inflate the closing-line edge read on those seasons? This replaces the audit's worst-case bounds (README section 5) with measurements.

**For each choice j:**
1. **Re-decide on pre-2022 data where the forecasts exist,** with the same rule: same choice or not.
2. **Bootstrap the decision.** Use B = 2,000 resamples of four-week blocks of the choice's window. On each resample:
   * re-apply the recorded rule to pick arm a_b;
   * record that arm's closing-line advantage on the resample, minus its advantage on the original data.

   The mean of that difference is β_j, the optimism of "pick, then report", in the bootstrap world where the original data play the truth. The share of resamples that pick the original arm is the decision's stability.
3. **Report** β_j with a bootstrap interval, the stability, and the cross-metric correlation ρ_AB.

**The choices and their stored forecasts:**

| Choice | Window | Deciding metric | Forecasts |
|---|---|---|---|
| C1 odds fed as an input rather than stacked | 2022–26 | gain over the close (free models) | `tabpfn_thinking/baselines.parquet` |
| C2 the 2 Oct family set (dropping BT, MESR, schedule strength, revaluation, grinder; keeping the IOS profile) | 2013–26 | gains over Elo and over the odds (linear harness) | the Stage 4 and UFC B/D rundown outputs, if stored per match. Otherwise phase 4 covers it |
| C3 short-IOS memory, 4 or 13 weeks | 2013–26 | gain over Elo | Stage B diagnostic rows |
| C4 surface IOS kept | 2019–21, 2022–26 | close, then no odds | `surface_ios` predictions |
| C5 offset Elo swapped in, among 8 representations | 2022–26; 24-hour price 2025–26 | no price, 24-hour price | `surface_rating_race/predictions.parquet` (2019–26, 73 columns), `predictions_early` |
| C6 calibration rule (fixed 2019–21 against walk-forward) | 2022–26 | close | the stored stage-1 forecasts |
| C7 stage 2 adopted (adjustment, unshrunk, column) | men 2024–26 | close | `serve_speed_tabpfn` outputs |
| C8 28-day memory, among 14, 28 and the switch | men 2024–26 | close | `serve_speed_tabpfn/adaptive` |

**Output.** `decision_bootstrap.csv` and a leak budget: Σβ over C1 and C3–C6 for stage 1, and over C7–C8 for stage 2, against the reported edges.

**Optional.** An empirical-Bayes pass over the roughly 150 "given the odds" feature results in the register (`feature_interactions/round0/inventory.md` §3) would estimate the spread of true effects, and so how far a selected market lead should shrink. It is crude, because those results overlap.

## 5. Phase 4: the hindsight replay (moderate; already-seen data)

**Question.** Would an honest process, using only outcomes before T, have built a model with the same edge on seasons from T on?
* **T = 2022 is the primary.** It measures how much the 2022–2026 headlines owe to choices made with those seasons in view.
* **T = 2020 is a secondary.** It asks whether the 2020+ edge could be found from pre-2020 data at all.

**1. The menu at T.**
* Every column of the feature-universe store (`feature_universe/menu.csv`, 603 columns, all built as of each match).
* Each exposed choice is replaced by its axis of alternatives:
  * two-week form memory of 1, 2, 4 or 8 weeks, or 52 weeks;
  * long-memory IOS pooled or by surface, with the products in or out;
  * short-memory points matchup with no memory term, or 4, 13 or 26 weeks;
  * Elo as the blend, as the offset with the switch pairs, or overall only, plus the timed TrueSkill Through Time forms in the store;
  * age in or out;
  * load as sets over 7 or 14 days, or minutes;
  * points aggregates over 2 or 52 weeks.
* Context stays in by mechanism. Constants stay as tuned on 2013–2018.

**2. A codified selection with no incumbent in any rule.** Adapted from the UFC v4 rebuild's mechanisms M1–M7:
* **Scaffold, by mechanism:** the odds, overall Elo and the context.
* **Adding families.** Families are added greedily by their paired gain against the close (TabPFN, calibrated walk-forward):
  * for T = 2022, chosen on 2018–2020 and confirmed on 2021;
  * for T = 2020, chosen on 2016–2018 and confirmed on 2019.
* **Each add is judged against a shuffled twin of its own shape.**
* **Axes.** The members of an axis compete inside their family. A tie goes to the plateau's interior point, else to the neutral default written down beforehand.
* **Stop** when no family beats its twin, pooled.
* **No M58 value** may serve as a baseline, tie-break, fallback, grid centre or scaffold member.

**3. Score.** Freeze M_T, forecast seasons T..2024 walk-forward, and read E(M_T) and E(M58) on the same matches. Compute HP(T) with a paired interval. 2025 to Jul 2026 is reported as a secondary: those seasons have been read many times already.

**Reading.**

| Result | Meaning |
|---|---|
| HP(2022) ≈ 0 | The 58-input design could have been found in 2021. The 2022–2026 headlines are honest up to phase 3's choice-level β |
| HP(2022) ≈ the edge | The 2022–2026 edge depends on hindsight; trust only H_fresh |
| HP(2020) large and HP(2022) small | The value appeared in 2020–21 and was detectable by then. That is a real change or selection on 2020–21, which only prospective data separate |

**Caveat.** The project's actual choices were judgements by people and agents, not this rule. HP measures what hindsight added over a defensible rule.

**Cost.** Several hundred local fits per origin (about 12 families × 3 axis members × 3–4 seasons × 3 seeds, with pruning): GPU hours, up to a day.

## 6. Phase 5: the backcast, men 2005–2012 (optional; data work)

**Question.** Do the design choices hold, and is there an edge, in an era that no choice and no constant ever saw?

**Data.** On disk, apart from three downloads:
* Sackmann's ATP tour-level files 2000–2009, with box scores on about 88% of matches;
* Stage 0's 2010–2012;
* tennis-data ATP odds for 2001, 2003, 2005 and 2007–2012. ATP 2002, 2004 and 2006 must be downloaded (failed Wayback captures, never retried; collection is approved).

**The odds input.** Pinnacle where present (2005, 2007, 2008, 2010–2012), else the mean of the available books. The books' average starts in mid-2010.

**The build.** A separate backcast Stage 0, not the live one (`FIRST_YEAR = 2010` is shared). It needs:
* match-clock windows for 2000–2012 (event dates and cautious windows; no point-log days);
* ratings warmed from Sackmann's history back to 1968;
* features at their frozen constants, with no retuning;
* the leak probe on the cross-player features.

**Arms.** The M58 design; each exposed choice's alternatives, as in phase 3's list; and odds + Elo + context.

**Scoring.**
* TabPFN trained on 2001..Y−1 for Y = 2005–2012, seeds 0–2, with slopes walk-forward from the first two scored seasons.
* Read against recalibrated Pinnacle, or the books' mean.
* About 20,000 matches, so SE ≈ 0.3 for the edge and about 0.1–0.2 for design comparisons.

**Reading.**
1. **The main product is a durability table:** each exposed choice's advantage in 2005–2012 against its advantage in 2022–2026.
2. **The design's edge in an untouched era.** Era differences confound it (margins, books, no serve speed), so read it beside phase 2.

**Women.** Not feasible before 2010: no box scores are on disk. Whether Sackmann's WTA files carry statistics is unverified.

**Cost.** One to two days of data work and rebuild; about 8 seasons × 8 arms × 3 seeds ≈ 200 fits.

## 7. Phase 6: the prospective read (the verdict)

**Before the first look:**
* **Extend the frame to H_fresh** with the rebuild steps in the [offset-Elo decision](../../decisions/2026-10-06-offset-elo.md). The frozen-upload checks need re-basing.
* **Build the stage-2 speed columns** from ManTennisData weekly, or the daily collector once it exists.
* **Write forecasts for the comparison set:**
  * **M58 (both stages).** For 2026 it uses the existing fits trained on 2013–2025 and the coefficients in force. For 2027 it is refitted by its own walk-forward rule. Those mechanical refits use H_fresh's 2026 results as training data. That is allowed, because no person reads them outside a checkpoint.
  * **M_clean**, the rebuild's model, if it is frozen before the look;
  * **the scaffold:** odds + Elo + context;
  * **the recalibrated close**, by the decided rule.

**Benchmarks.**
* **Primary:** the tennis-data average close, for continuity with every reported number. Pinnacle ends in January 2026.
* **Secondary:** the Betfair Exchange close (BFE; 949 of 950 rows after 28 Jul) and the Polymarket close.
* **For betting reads:** BetOnline's close.

**Checkpoints.** Main-tour matches with the average close, debut seasons excluded, at about 5,000 a year:

| Look | Matches | Expected around | SE | Power for +1.3 | Power for +0.7 |
|---|---:|---|---:|---:|---:|
| L1 | 2,500 | Feb 2027 | 0.92 | 41% | 19% |
| L2 | 5,000 | Jul 2027 | 0.65 | 64% | 29% |
| L3 | 7,700 | early 2028 | 0.52 | 80% | 38% |
| (later) | 10,000 | mid 2028 | 0.46 | 88% | 45% |

The power figures are one-sided at 5%, with a per-match sd of 46 mLL (the studies' range is 43–50). Stage 2 is read on men with speeds only, which gives fewer matches.

**Estimands at each look (each look once, logged):**
* **E(M58, H_fresh)** and **O = E(M58, 2022–26) − E(M58, H_fresh)**. The reported 2022–26 values are +1.18 to +1.30 (both tours) and +1.66 to +1.71 (men).
* **The design leak**, if M_clean exists: DiD = [E(M58) − E(M_clean)] on H_fresh, minus the same on 2022–26. Its per-match sd is about 15–25, so SE is about 0.2–0.35 at 5,000 matches.
* **Stage 2's gain** on men with speeds.
* **Betting returns** at the venue: reported, never used to choose.

**Pre-registered responses.**
* At L3, a lower bound above 0 confirms the edge.
* A point estimate below +0.5 at L2 marks the 2022–26 headline as inflated, whether by the era or by selection. The diagnosis then proceeds on development data only.
* Under no outcome is anything tuned on H_fresh.

## 8. Phase 7: the rebuild protocol (keeping the leak small and measurable)

Adapted from the UFC v4 rebuild (`UFC-Predictions/docs/v4_rebuild/01_principles.md` §2, §5; `02_windows_and_holdout.md`). The tennis applicability of each point is noted.

* **Windows.**
  * D = events starting on or before 28 Jul 2026.
  * H = H_fresh.
  * V = men's 2018, with one look, and the backcast if it is built.
  * 2025–2026 is development data. It is no longer a holdout for any incumbent.
* **No incumbent value in any rule.** M58's list, constants and arms may appear only as report-only anchors after a decision is logged. Keep decision constants in a module separate from anchors, and test that no decision driver imports the anchors.
* **The pool.**
  * `menu.csv` plus the axes of phase 4, with provenance tags from this audit's ledger, for reporting only.
  * No earlier verdict is applied in either direction.
  * Interaction and product columns face their own shuffled twins at the end.
* **Era layout inside D.**
  * **Choosing seasons must include 2020+,** where the edge lives: for example 2020–21, 2022–23 and 2024.
  * **Confirmation:** 2025 to Jul 2026.
  * **Fragility window:** 2015–2019. A sign flip there marks a regime bet; it is not a veto on its own.
* **Nulls.**
  * shuffled twins for adds;
  * a spread of mechanism-free perturbations for in-place changes;
  * placebo walks for the depth of selection;
  * a winner's-curse-corrected expected gain for the finalists (best mean + about 1.2 SE for 6 finalists).
* **Rehearsal.** Run the protocol once with 2025 to Jul 2026 as a pseudo-holdout, as process evidence, then rerun it on all of D.
* **Per tour.** Several incumbents entered both tours on the men's evidence. Select, or at least read, per tour.
* **One look at H** at each of phase 6's checkpoints.

## 9. Order, dependencies and cost

| Phase | Needs | Cost | Can start |
|---|---|---|---|
| 0 Seal and freeze | owner approval | minutes | now |
| 2 Training size; men's 2018 | stored forecasts; men's 2018 frame rows | ~120 local fits | now |
| 3 Decision bootstrap | stored per-arm forecasts | CPU, hours | now |
| 4 Hindsight replay | the menu with axes; a codified rule, pre-registered | several hundred fits per origin | after phase 3's tooling |
| 5 Backcast | three downloads; separate Stage 0 | 1–2 days + ~200 fits | any time; optional |
| 6 Prospective | frame extension; speed columns; phase 0 seal | days to build; looks from Feb 2027 | build now |
| 7 Rebuild | phase 0; ideally phases 2–4 first | the rebuild | after phase 0 |

## 10. What would change the plan

* **Phase 2 finds the era pattern is training size.** The era worry shrinks. The rebuild should keep the full history, and the edge is more likely to persist.
* **Phase 3's Σβ comes out well below the edge.** Choice-level selection is not the problem; the question narrows to the family choice and the era (phase 4).
* **Phase 4 finds HP(2022) near 0.** The 2022–2026 headlines stand up to choice-level β, and the rebuild can lean on its development data.
* **Phase 4 finds HP(2022) near the edge.** Treat the current edge as a hindsight effect until H_fresh says otherwise, and size bets accordingly.
* **The backcast reverses several choices.** Those choices are regime bets. Keep them only if 2020+ evidence and H_fresh support them.
