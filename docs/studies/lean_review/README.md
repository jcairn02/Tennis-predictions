# Three leans reviewed: stage 2, the per-surface IOS profile and the short IOS memory

9 October 2026 · For the owner · **A debate record and a proposal, not a decision.** Nothing in the model or the decisions changed.

**The owner's request** (9 Oct 2026), on three parts the [lean ledger](../adoption_framework/lean_ledger.md) flags as reading worse where they matter:

> "Consider removing/changing these from the current best model. Have you and an agent debate back and forth if its best to remove. Note the model isnt locked, so dont treat the decision that its in the model already with tooo much weight. Review the logic of why it was originally included and still if it still holds."

**How it was done.**
* **Two independent positions.** The lead (the session that wrote the ledger) and an independent Opus 5.5 reviewer, read-only on the repository, each wrote one before seeing the other's.
* **Three rounds of exchange.** The reviewer was told to attack where it disagreed and not to soften. The lead pushed hardest where the two agreed. Every round is kept verbatim in [debate/](debate/).
* **Incumbency counted for little,** as asked: each part was judged as if the model were designed today.
* **The debate scored no match and fitted no model.** Its numbers are copied from a linked document or stored output, or are arithmetic on such numbers, marked † (`src/eda/lean_review/`, outputs in `data/studies/lean_review/`).
* **The tests ran afterwards,** at the owner's word, on seasons ≤ 2024 ([results](#results-9-oct-2026)).
* **This file quotes 2025–26 results.** Keep it out of the clean room of the [clean-holdout rebuild](../clean_holdout_rebuild/README.md).

**Keys.** mLL per match. **+ = the named part or change is better.** Intervals are 95%: "better" or "worse" only when one clears 0, otherwise "unresolved" with P(better).

## In short

**Tested on 9 Oct** ([results](#results-9-oct-2026); 2020–24; Pinnacle-first base; rules fixed before any fit). The proposals below are the owner's call:

| Part | What the tests say | Proposal |
|---|---|---|
| **The long-memory IOS profile** (21 inputs) | **Removing it hurts.** At the close: −0.29 [−0.63, +0.04], P(better) 0.04, worse in all five seasons. At the opening line: −0.18 [−0.56, +0.19], P 0.16. It is about a quarter of the model's lead over the price, mostly the men's | **Keep it** |
| **Per surface or pooled** | **Per surface reads a little better:** +0.055 [−0.054, +0.163] at the opening line (P 0.84), +0.045 at the close (P 0.81). The shrunk gain clears the cost bar | **Keep it per surface.** That answers item 8 |
| **`ios_points_short`** (1 input) | **Nothing measurable either way:** −0.03 [−0.11, +0.06] at the opening line (P(better) 0.25), −0.00 at the close (P 0.47) | The rule removed it at its threshold (+0.0004 on a bar of 0). **Dropped by the owner on 9 Oct:** "Drop ios_points_short" ([amendment](../../decisions/2026-10-08-current-best-model.md)). The model has 57 inputs |
| Stage 2 | Not tested: T0 and T1 belong to item 7 | As below |

**Both IOS outcomes run against the debate's priors.** The debate leaned toward simplifying both, and the tests, at a sharp early price neither debater had, kept the profile per surface.

**The debate's proposals, before the tests:**

| Part | Why it went in | Does that still hold? | Proposal | Confidence (lead / reviewer) |
|---|---|---|---|---|
| **Stage 2,** the speed adjustment (men) | A replicated serve-speed signal the price lacks; the pre-registered nudge read +0.41 on 2024–26 ([study](../serve_speed_tabpfn/README.md#64-the-nudge-the-same-information-applied-directly-s9)) | **The signal, yes. The procedure, not yet:** its walk-forward record is −0.06 [−0.31, +0.19]† over 2020–26, the choosing seasons included | **Keep live as a logged lean,** with three changes, if two checks pass (T0, T1) | 60% / 55% |
| **Per-surface IOS profile** (21 inputs) | Neutral with the odds, + without them, "we may bet early" | **No.** Once the offset Elo is in, it reads nothing at the close or at 24 hours. Men's no-odds edge is the wrong proxy for a sharp line | **Pooled on both tours,** if the profile itself survives T2 (then T3) | 70% / 65% |
| **`ios_points_short`** (1 input) | The strongest single input given Elo in Stage B, and +0.13 beyond adjusted points ([audit](../feature_alpha_audit/README.md#what-really-adds-beyond-elo)) | **Unknown inside the model.** Its one increment test fell to about 0 after the repairs, on a history that is not the model's | **Remove,** if T2's rule passes | 60% / 55% |

**Three facts surfaced in the debate that change the plan** (each verified):
1. **Early prices exist before 2025.** OddsTrader recorded Pinnacle's timed opening line from January 2018 to 7 September 2025. It came a median 35.5 hours before the start, on 76–96% of matches a season, and is 3.94 mLL [2.18, 5.69] softer than Pinnacle's last line ([odds sources § 3.4](../odds_sources/README.md)). Every part can therefore be read at an early sharp price on 2020–24 without spending 2025–26. The framework's "early-price history exists only for 2025–26" is out of date.
2. **The model's odds input changed today** to "Pinnacle first", in training and live ([decision](../../decisions/2026-10-09-pinnacle-first-odds-input.md)). Every stage-2 and IOS reading so far is on a base fed the books' average.
3. **Challenger serve speeds enter the live stage 2 unguarded.** Usable Challenger speed rows rose from about 89 a season, when the coefficient was fitted, to 940 in 2026 ([lower-level evidence § 1.4](../lower_level_evidence/README.md)).

**Done since.** The owner dropped `ios_points_short` on 9 Oct ([amendment](../../decisions/2026-10-08-current-best-model.md)):
* The chain still builds the column.
* `src/eda/current_best_model/template_inputs.py --apply <folder>` writes the 57-input list.
* The fit runner accepts that list or the chain's 58, and a prediction run applies the 57-input list when it collects.
* The frozen reference and the Pinnacle-first instance stay 58-input builds.

**What is left:**
* **Item 8 is answered (stay per surface),** so item 5 centres the per-surface products.
* **Stage 2's checks T0 and T1** remain, with item 7.

## 1. Stage 2, the walk-forward serve-speed adjustment

**Why it went in** ([decision](../../decisions/2026-10-07-speed-nudge.md); [study](../serve_speed_tabpfn/README.md)):
* **The men's serve-speed change was the one point-derived signal that replicated:** +0.090 [+0.017, +0.162] log-odds per SD in 2022–24, given the model ([study § 1](../serve_speed_tabpfn/README.md#1-the-question-and-the-starting-point)).
* **Its mechanism is result-free:** +0.33 percentage points of first-serve points won [+0.20, +0.46] per SD of speed form, beyond box-score form ([study, in short](../serve_speed_tabpfn/README.md#in-short)).
* **The pre-registered primary was unresolved:** the speed as a TabPFN column read +0.07 [−0.05, +0.18], because TabPFN used about 8% of the information ([study § 6.1](../serve_speed_tabpfn/README.md#61-the-primary-the-speed-column-in-tabpfn)).
* **The nudge was a pre-registered secondary.** It read +0.41 [+0.04, +0.78] on men 2024–26, and the owner adopted it on 7 Oct ([study § 6.4](../serve_speed_tabpfn/README.md#64-the-nudge-the-same-information-applied-directly-s9)).
* **The 28-day memory followed on 8 Oct,** after two more outcome runs on the same seasons: +0.54 [+0.13, +0.95] with instant speeds, +0.38 [+0.11, +0.64] with today's sources ([adaptive](../serve_speed_tabpfn/adaptive.md)).

**Does it still hold?**
* **The information: yes.**
  * It replicated blind on 2025–26: +0.103 [+0.029, +0.178] ([study § 6.2](../serve_speed_tabpfn/README.md#62-is-the-information-there-yes)).
  * The closing odds explain R² 0.003 of it on 2022–23 ([study § 3](../serve_speed_tabpfn/README.md#3-the-feature-what-it-is-and-how-it-handles-thin-data)).
  * It is point-level data, the owner's thesis.
* **The procedure: not yet.**
  * Men 2020–24, outside the seasons that chose it: −0.26 [−0.59, +0.06], P(better) 0.05 ([seed check](../../../data/studies/adoption_framework/seed_term_check.out)).
  * Counting every season it has run, the choosing ones included, 2020–26: −0.06 [−0.31, +0.19], P(better) 0.32†.
  * The loss is one season, 2023. A coefficient fitted on 2019–22 (b̃ 0.07) met a season whose effect was −0.05 ([backfill § 5](../infosys_atp_backfill/README.md#5-the-features-future-predictability)).
* **The target: never read.** The adjustment was never scored at a bet-time price.

**The debate** ([round 2](debate/round2_lead.md), [reply](debate/round2_reviewer.md)).
* **The case for shadow (the lead):**
  * the realised record is at or below 0 outside the window that chose it;
  * the forward value leans on 2025–26, where the memory was picked;
  * a best-of-K secondary is "a lead" in the framework.
* **The case for keeping (the reviewer):**
  * what failed outside the window was the coefficient rule, not the information;
  * the signal replicated on two windows;
  * most live failure modes are already inside the backtest: radar breaks are learned as of each match, late speeds are the "today's sources" scenario, and a silent collector decays to stage 1;
  * live and shadow differ only in which forecast the bets use. The sealed evidence accrues either way, and the speed feed runs either way.
* **Where it settled: keep, as item 7's logged lean, with no stakes credit.** The expected gain is small. Per men's match next season, with the coefficient set by proposal (a) below ([arith.out](../../../data/studies/lean_review/arith.out), [arith_r2.out](../../../data/studies/lean_review/arith_r2.out)):

  | Evidence counted | Coefficient b | Expected gain |
  |---|---|---|
  | Strict ≤ 2024 evidence | its own posterior, 0.014† | +0.02† (−0.01† at b 0.032) |
  | 2019–26, with 2025–26 cut by 0.01–0.03 for the memory pick | 0.025–0.030† | +0.08 to +0.11† |
  | No signal at all | 0.032 | −0.12† |
  | A season like 2023 (effect −0.05) | 0.032 | −0.51†, against −0.77† at today's 0.0444 |

**Proposed changes to item 7** (the owner's call):
* **(a) A coefficient that allows for season-to-season disagreement.**
  * b = the posterior mean of the average season effect, with the same prior N(0, 0.05²) and the between-season variance included.
  * The current rule's standard error ignores that the seasons disagree (I² ≈ 50%, [backfill § 5](../infosys_atp_backfill/README.md#5-the-features-future-predictability)).
  * For 2027 this gives b ≈ 0.030 instead of 0.0444†. It would have set 2023's at 0.029, not 0.07†.
  * It moves b toward 0 and costs at most 0.04 in the good case. Adopt it on its mechanism and claim nothing for it: it cannot be tested cleanly, since the season that exposed the flaw is in every window.
* **(b) Keep Challenger speeds out of `spd_L`** until a candidate shows they belong, as the [lower-level study](../lower_level_evidence/README.md) (§ 8.4) already proposes.
* **(c) Item 7's first checkpoint at ≥ 2,000 men's matches,** with only the alarms before that. At 300 matches the P(better) ≤ 0.2 cut-off removes a truly helpful stage 2 (+0.15) 16% of the time, and catches a −0.77 one only half the time. At 2,000 those are 10% and 91%† ([arith.out](../../../data/studies/lean_review/arith.out)).
* **Gates: T0 and T1** ([below](#the-test-plan-fixed-on-9-oct-2026-before-any-of-it-runs)).

**The strongest case against, in the reviewer's closing words** ([round 3](debate/round3_reviewer.md)): "the procedure has never shown a positive cumulative record outside the seasons that chose it … The speed signal replicated there; the procedure built on it has not yet earned its place."

## 2. The per-surface long-memory IOS profile (21 inputs)

**Why it went in.**
* **The pooled profile entered the 53 inputs on 2 Oct against a null linear result,** with no rationale recorded. Men, with products, given the odds: −0.21 (−0.67 to 0.26) ([Stage D](../ufc_ideas/stageD.md), part 2; [provenance](../feature_provenance/README.md#1-the-58-inputs)).
* **TabPFN then leaned on it most:** shuffling the group lost 0.62 (men) and 0.74 (women) of its adjustment's explained variance ([TabPFN-Thinking](../tabpfn_thinking/README.md), "Which inputs"). That is importance, not marginal value.
* **On 6 Oct the per-surface build was kept** ([decision](../../decisions/2026-10-06-surface-ios-profile.md)):
  * neutral with the odds, +0.01 [−0.10, +0.13];
  * + without them: men +0.83 [+0.39, +1.27];
  * "Especially since we may bet early before the close."

**Does it still hold?** With the offset Elo in, per surface against pooled ([composed results](../../../data/studies/surface_rating_race/composed_results.csv); [arith.out](../../../data/studies/lean_review/arith.out)):

| Owner's reason | Now | Holds? |
|---|---|---|
| Neutral with the odds | Close, both tours −0.01 (P 0.39†); men +0.00, women −0.03 | Yes |
| + without the odds | Men +0.19 [−0.05, +0.42] (P 0.94†); women −0.06 (P 0.29†). The offset Elo absorbed about 80%† of the men's +0.84 | For men only, and no-odds is the wrong proxy for a sharp line |
| Early bets | 24 h, both tours: −0.06 [−0.43, +0.31] | Unanswered: SE 0.19 makes it uninformative, and that price is no longer the live input |

* **Women:** no reading at any price ever favoured it. Without odds it was worse in 2022–24: −0.73 [−1.14, −0.32] ([decision](../../decisions/2026-10-06-surface-ios-profile.md), "Not decided").
* **The tuning leaned toward pooling:** the heaviest surface penalty tested, at the edge of the grid, was chosen in 5 of 16 cells ([provenance_58](../../../data/studies/feature_provenance/provenance_58.csv)).
* **Cost:** 1.7 times the pooled build's compute, and its own refresh steps ([decision](../../decisions/2026-10-06-surface-ios-profile.md)).

**The bigger question the debate raised: the whole long-memory profile.**
* Its inclusion was never tested by removing it from the model. And [Stage D](../ufc_ideas/stageD.md) located the per-statistic value against the odds in recent form, not in long-memory traits.
* **If both the profile and `ios_points_short` go, the IOS chain leaves the model:**
  * items 5 and 8 become moot;
  * the exposure to finding #6 goes;
  * so does one of the two main entry points of the ITF box scores due about 31 Oct, and the women's prior bias the [lower-level study](../lower_level_evidence/README.md) found in the joint solves.
* **Against it:** TabPFN's reliance on it, and the owner's per-statistic thesis. Both debaters say: don't drop it without T2.

**Proposal:**
* **T2 first.**
* **If the profile stays, T3** (item 8, amended): pooled on both tours unless the per-surface build clears est > +0.024 at Pinnacle's opening line.
* Keep the surface IOS for forecasting individual statistics, where it is better ([decision](../../decisions/2026-10-06-surface-ios-profile.md)).
* **The strongest case against the switch** (the reviewer): men's no-odds residual, +0.19 (P 0.94). If Pinnacle's opening line also lacks that information, T3 keeps the per-surface build for men.

## 3. `ios_points_short`, the short-memory IOS points matchup

**Why it went in.**
* **Stage B's IOS diagnostics,** added after the first all-season rundown was read, made it the strongest single row given Elo ([Stage B](../ufc_ideas/stageB.md#the-ten-strongest-rows-per-tour)):
  * given Elo: men 3.72 (4 weeks), women 5.02 (13 weeks);
  * given Elo and the iid ratings: +0.50 and +0.64 ([Stage B](../ufc_ideas/stageB.md#does-anything-add-to-the-ratings-through-the-iid-model));
  * given the market: +0.13 and +0.01.
* **The audit's ladder, before the repairs** (2022 on): beyond the two-week adjusted points, men +0.13 [+0.05, +0.20], women +0.25 ([audit](../feature_alpha_audit/README.md#what-really-adds-beyond-elo)).
* **Seasons before 2022 pick the same memories,** so the memory itself carries no selection luck ([provenance_58](../../../data/studies/feature_provenance/provenance_58.csv)).

**Does it still hold?**
* **It duplicates other inputs.** It is one of four points-won aggregates, beside `adjperf_tpw_2w`, `points_52w` and `ratings_iid`, which the owner's thesis treats as priced-in controls.
* **After the repairs it adds nothing measurable beyond the adjusted points:** men −0.013 [−0.091, +0.066] (P 0.37†), women −0.052 (P 0.12†) ([repairs](../feature_alpha_audit/repairs.md#what-adds-beyond-elo-on-the-repaired-cohort)).
* **But that repaired history kept only dated main-tour matches** ([TabPFN-Thinking](../tabpfn_thinking/README.md), "Does it survive the repaired features?"). The model's leak-proof version keeps every level, and the leak fix barely moved it: correlation 0.998 in the test seasons ([leak-proof refit](../tabpfn_leakproof/README.md)). So no reading measures the input as the model builds it.

**Proposal:** remove it if T2's rule passes. **The strongest case against** (the reviewer):
* Its value inside the model has never been measured.
* Its one plausible role is a short form for players arriving from Challengers. The close misprices exactly those players (+0.18 log-odds, [lower-level evidence](../lower_level_evidence/README.md)).
* Strength controls can matter more at a softer price, so the opening-line reading should decide.

## The test plan, fixed on 9 Oct 2026 before any of it runs

Agreed in [round 2](debate/round2_reviewer.md) with the amendments of [round 3](debate/round3_reviewer.md). Every outcome is a proposal; accepting it is the owner's call.

**Common settings.**

| Element | Setting |
|---|---|
| Base | The Pinnacle-first instance (`data/studies/current_best_model/pinnacle_first_2026-10-09/`) |
| Fits | Seeds 0–3, paired by seed; fitted 2019–24, scored 2020–24. No 2025–26 result is read |
| Calibration | Walk-forward per tour on each arm's own forecasts of 2019..Y−1, separately for each yardstick |
| Stages and matches | Both stages, debut seasons out. Stage 2 is the decided recipe (amendment A) |
| Yardstick (C) | The Pinnacle-first close, as fed in training |
| Yardstick (O) | Pinnacle's opening line, margin-free (`p_ot20o` in `data/studies/odds_sources/sources.parquet`). Complete cases only, without the 2021 US Open, whose recording failed ([odds sources § 2](../odds_sources/README.md)) |
| Also reported | The realisation slope at (O) |

**T0, the speed replay: a gate for stage 2. It reads no outcome.**
* One past day, run through the live speed chain, must reproduce the backtest's speed column to machine precision, with the Challenger filter applied on both sides.
* If it fails, stage 2 stays off live until it is fixed.

**T1, stage 2 on the Pinnacle-first base: no new fits, scoring only.**
* **Primary:** d = β_pf − β_ref, the paired difference of the pooled information coefficients. Men, 2019–24, the same matches and the same speed column, with a block bootstrap over four-week blocks.
* **Rule:**
  * keep stage 2 live if d ≥ −0.015, meaning the new base absorbs at most half of the documented 0.030;
  * otherwise move it to shadow until the sealed checkpoint.
* **Secondaries:** the walk-forward gain for men, 2020–24, at (C) and (O), under the decided coefficient rule and under (a). Nothing is selected on these.
* **Alarm:** move stage 2 to shadow if the (O) gain's 95% interval lies below 0.

**T2, the IOS 2×2: column drops only, no chain rebuild. It runs first.**
* **Arms:**

  | Arm | What it drops | Inputs |
  |---|---|---|
  | A0 | Nothing (the base, refitted to add the (O) queries) | 58 |
  | A1 | The long-memory profile | 37 |
  | A2 | `ios_points_short` | 57 |
  | A3 | Both | 36 |

* **Reproduction check (amendment C):**
  * A0's close-fed predictions must equal the Pinnacle-first instance's fits, seeds 0–3, to machine precision before anything is scored.
  * Query the (O) rows in a separate predict call, after the close-fed call on the same fitted model.
  * If the check fails, stop and report.
* **Primary:** (O), both tours. **Secondary:** (C), with per-tour flags.
* **Rule:** propose removal X if B·est_X + c_X > 0 at (O), where est_X is the paired gain of removing X (+ = without it better). The bars are arithmetic in [arith_r2.out](../../../data/studies/lean_review/arith_r2.out):

  | Removal | τ | c (upkeep saved) | Bar at the expected SE† |
  |---|---|---|---|
  | Both (the IOS chain leaves the model) | 0.1 | 0.06 | est > −0.10 |
  | The profile | 0.1 | 0.05 | est > −0.06 to −0.08 |
  | `ios_points_short` | 0.03 | 0.01 | est > −0.02 |

  * **Veto:** no removal that is worse at (C) by more than 0.1 with P(better) ≤ 0.1.
  * **Order:** both if both qualify; otherwise the single removal with the larger B·est + c; otherwise neither.
  * If the profile goes, items 8 and 5 are cancelled.
* **Note:** the c values are judgment calls. The chain is a live dependency of every prediction run, and the framework's class for that is about 0.05.

**T3, item 8, amended: pooled against per surface. It runs only if the profile stays.**
* **Arms:** A0 against the pooled-profile build, carrying T2's decision on `ios_points_short`.
* **Primary:** (O), both tours. **Secondary:** (C), per tour.
* **Rule:**
  * switch to pooled unless the per-surface build's B·est > 0.01 (τ 0.05, about est > +0.024†);
  * split by tour only if one tour clears and the other is worse with P(better) ≤ 0.2;
  * veto (item 8's clause): stay per surface if pooled is worse at (C) by more than 0.1.

**Settled before any fit ran** (9 Oct 2026, 11:55 PDT; the owner asked to run T2 and, if needed, T3). These fill in what the plan above left open; nothing below was chosen after a result.
* **The (O) matches.**
  * A coherent Pinnacle opening line (`p_ot20o`), stamped no later than OddsTrader's listed start.
  * The 2021 US Open is the Slam whose `tournament_date` is 2021-08-30; 248 of its 253 matches had a line, all left out.
  * Coverage 2019–24: 82–97% of matches a season (`data/studies/lean_review/check.json`).
* **(O)'s calibration and stage-2 coefficients** are fitted on the (O) matches' opening-fed forecasts of 2019..Y−1, debut seasons out. Stage 2 reads the reference's speed column, as `compare.py` does for the instance.
* **The rule's terms:** est_X and SE are the (O) primary reading (both tours, both stages, 2020–24; seeds paired); + = without X better; B = τ² / (τ² + SE²).
* **The order rule, read this way:**
  1. If "both" (A3 against A0) qualifies and is not vetoed, propose removing both.
  2. Otherwise, of the single removals (A1, A2) that qualify and are not vetoed, propose the one with the larger B·est + c.
  3. Otherwise, neither.
* **The veto** uses the (C) primary reading: est < −0.1 with P(better) ≤ 0.1.
* **The reproduction check** (amendment C): A0's close-fed predictions must equal the stored fits for all 24 jobs, max |Δp| ≤ 1e-12, with the same ids.
  * Before any fit, every A0 job's fingerprint (its training rows, labels and close-fed queries) already equals the stored fit's (`check.json`).
* **Reported, not used for the decision:**
  * per-tour, level and season rows;
  * stage 1 alone;
  * A3 against A1 and against A2;
  * each arm's realisation slope at (O): a logistic fit with no intercept of the result on logit p_open and logit q − logit p_open, clustered by four-week block.
* **T3 runs only if the profile stays,** that is, if neither A1 nor A3 is proposed.
* **T3's pooled profile** (settled 12:00 PDT, before any T2 or T3 result):
  * It is the leak-proof refit's 21 IOS inputs, the model's profile before 6 Oct: `ios_O_<s>|single`, `ios_D_<s>|single` and `prod_<s>|single` of `leakproof_features.parquet`, as the frozen reference holds it (`tables_later/`).
  * They are swapped into a copy of the Pinnacle-first frame (`src/eda/lean_review/t3.py --build`).
  * Checked: the table holds all 67,226 frame matches with the frame's sides, and its `ios_short` equals the model's input exactly. Only the 21 columns differ; they correlate 0.93–0.99 with the per-surface ones (`t3_build.json`).
  * No chain rebuild was needed. Adopting pooled would still need item 8's chain option, so that the template builds it.
* **T3's arms and rule, as coded:**
  * the per-surface twin (T2's A0, or A2 if T2 removes `ios_points_short`) against its pooled copy (P0 or P2);
  * est = per surface against pooled, + = per surface better, at (O), both tours, both stages;
  * keep per surface only if B·est > 0.01 at τ 0.05;
  * split by tour if one tour clears that bar and the other's per-surface reading has P(better) ≤ 0.2;
  * veto: stay per surface if per surface is better at (C) by more than 0.1.

**Cost.**
* T2: 96 fits at about 40–55 seconds, about 1.5 hours on the card after the Pinnacle-first fits running now. Those take 37–44 seconds each before the second predict call ([fits.log](../../../data/studies/current_best_model/pinnacle_first_2026-10-09/fits.log)).
* New code: a runner adapted from `src/eda/bet_timing/fits_cons_trained.py`, and a paired scorer built on `src/eda/current_best_model/compare.py`'s walk-forward and seed-paired intervals.
* T1: scoring only. T0: an engineering check, part of item 7.

## Results (9 Oct 2026)

Run at the owner's word: "perform the necessary tests to conclude these, when the GPU is free". That covers the per-surface profile and `ios_points_short`, so T2, then T3. T0 and T1 belong to stage 2 and were not run. Results of seasons ≤ 2024 only.

### T2, the IOS 2×2

**Checks.**
* A0 reproduced the Pinnacle-first instance's stored fits exactly: 24 of 24 jobs, max |Δp| 0.0 ([repro.json](../../../data/studies/lean_review/repro.json)).
* 96 fits, 12:21–13:47 PDT ([fits.log](../../../data/studies/lean_review/fits.log)).
* Matches: (O) 20,979, (C) 22,265 ([t2_summary.json](../../../data/studies/lean_review/t2_summary.json)).

**The readings** (both stages, 2020–24; + = without the dropped inputs better; seeds paired; [t2_scores.csv](../../../data/studies/lean_review/t2_scores.csv)):

| Removal | (O), the primary, both tours | (C), both tours | B·est + c at (O) | Outcome by the rule |
|---|---|---|---|---|
| The long-memory profile (A1) | −0.18 [−0.56, +0.19], unresolved, P(better) 0.16 | −0.29 [−0.63, +0.04], unresolved, P(better) 0.04 | +0.009, qualifies | **Vetoed:** worse at (C) by more than 0.1 with P ≤ 0.1. **The profile stays** |
| `ios_points_short` (A2) | −0.03 [−0.11, +0.06], unresolved, P(better) 0.25 | −0.00 [−0.09, +0.08], unresolved, P(better) 0.47 | **+0.0004**, qualifies | **Proposed: remove it** |
| Both (A3) | −0.21 [−0.59, +0.16], unresolved, P(better) 0.13 | −0.34 [−0.69, +0.01], unresolved, P(better) 0.03 | +0.013, qualifies | Vetoed, as A1 |

**Reading** (inferred).
* **The long-memory profile carries value inside the model.** This is the first time it was measured by removing it; earlier linear tests found nothing.
  * At the close, dropping it is worse in all five seasons: −0.18, −0.48, −0.13, −0.04, −0.59.
  * It is mostly the men's:

    | Dropping the profile | Men | Women |
    |---|---|---|
    | At (O) | −0.39 [−0.85, +0.08], P 0.05 | +0.05, P 0.57 |
    | At (C) | −0.39 [−0.81, +0.04], P 0.04 | −0.19, P 0.24 |

  * **It is about a quarter of the model's lead over the price.** Against its calibrated price, the full model reads +1.28 [+0.58, +1.99] at (O) and +1.09 [+0.43, +1.75] at (C). Without the profile: +1.10 and +0.80.
  * *Caveat:* 2022–24 fall in the window whose TabPFN outputs prompted keeping the profile on 2 Oct. The close readings of 2020–21 (−0.18, −0.48) point the same way.
* **`ios_points_short` neither helps nor hurts measurably,** at either price and in every season.
  * The rule removes it by a margin of +0.0004 on a bar of 0: its shrunk worth (−0.0096) and its assumed upkeep (c = 0.01) are almost equal.
  * That upkeep value matters less now that the IOS chain stays for the profile. Keeping it is equally defensible; the rule, fixed in advance, says remove.
* **No arm over-reacts.** Realisation at (O) runs from 0.93 (A3) to 1.09 [0.73, 1.45] (A0) ([t2_summary.json](../../../data/studies/lean_review/t2_summary.json)).

### T3, pooled against per surface (item 8, amended)

**Checks.**
* 24 fits of P2, 13:50–14:16 PDT ([t3_fits.log](../../../data/studies/lean_review/t3_fits.log)).
* The pooled frame differs from the instance's only in the 21 profile columns ([t3_build.json](../../../data/studies/lean_review/t3_build.json)).
* The per-surface twin is A2, because T2 proposed removing `ios_points_short`.

**The readings** (both stages, 2020–24; **+ = per surface better than pooled**; seeds paired; [t3_scores.csv](../../../data/studies/lean_review/t3_scores.csv), [t3_summary.json](../../../data/studies/lean_review/t3_summary.json)):

| Per surface (A2) against pooled (P2) | Both tours | Men | Women |
|---|---|---|---|
| (O), the primary | +0.055 [−0.054, +0.163], unresolved, P(better) 0.84 | +0.03 [−0.12, +0.17], P 0.65 | +0.09 [−0.09, +0.26], P 0.84 |
| (C) | +0.045 [−0.058, +0.149], unresolved, P(better) 0.81 | +0.03 [−0.12, +0.17], P 0.65 | +0.07 [−0.09, +0.22], P 0.80 |

* By season, per surface leads in 4 of 5 at both yardsticks; 2020 is the exception (−0.03 and −0.01).

**Outcome by the rule: stay per surface.**
* At (O), B·est = +0.025 (τ 0.05), against a bar of 0.01.
* Women clear the bar alone; men do not. Neither tour's per-surface reading is worse, so there is no split. No veto.

**Reading** (inferred).
* **Both debaters expected pooled** (65–70%), from readings at the books' average close and at Polymarket's 24-hour price.
* **At Pinnacle's opening line, on the Pinnacle-first base, per surface leans the other way,** by a small and unresolved amount, and in 4 of 5 seasons.
* Its better forecasts of the individual statistics seem to carry a little match-level value. The case for pooled was cost alone, and the gain clears that cost bar.
* **Item 8 is answered: stay per surface.** Item 5's centring then applies to the per-surface products.

## What this does not decide

* **Nothing changes until the owner accepts:** no decision record, no amendment and no `CLAUDE.md` line.
* **The proposals for item 7** (a)–(c), T0 and T1 are proposals. Item 7's prompt is the owner's.
* **The owner's per-statistic thesis against the framework's simplicity rule.** If T2 favours dropping the profile, choosing between them is the owner's call.
* **The upkeep values (c)** are judgment calls, stated before any reading.

## Files

| What | Where |
|---|---|
| The debate, verbatim: both independent positions, then rounds 2 and 3 | [debate/](debate/) |
| The reviewer's arithmetic (documented numbers only; no data read) | `src/eda/lean_review/arith.py`, `arith_r2.py` → `data/studies/lean_review/arith.out`, `arith_r2.out` |
| T2: the arms, the opening-line filter, the runner, the scorer | `src/eda/lean_review/common.py`, `fits.py`, `score.py` |
| T3: the pooled frames, their fits and the scorer | `src/eda/lean_review/t3.py` |
| Tests (8) | `test/lean_review/` |
| Checks | `data/studies/lean_review/check.json` (A0's fingerprints, coverage), `repro.json` (A0 reproduced exactly), `t3_build.json` (only the 21 profile columns differ) |
| Fits | `data/studies/lean_review/arms/<A0–A3, P2>/fits/model__<Y>__seed<k>.npz`, with each arm's `model_inputs.json`; P0 and P2's pooled `model_frame.parquet` (gitignored) |
| Results | `t2_scores.csv`, `t2_summary.json` (with the decision terms and realisation slopes), `t3_scores.csv`, `t3_summary.json`; logs `fits.log`, `t3_fits.log` |

Rerun from the repo root:

```
./python.sh src/eda/lean_review/arith.py                     # and arith_r2.py
./python.sh src/eda/lean_review/fits.py --check
bash src/eda/bet_timing/run_when_free.sh src/eda/lean_review/fits.py --run --arms A0,A1,A2,A3   # 96 fits, ~1.5 h
./python.sh src/eda/lean_review/fits.py --repro
./python.sh src/eda/lean_review/score.py
./python.sh src/eda/lean_review/t3.py --build
bash src/eda/bet_timing/run_when_free.sh src/eda/lean_review/t3.py --run --arm P2              # 24 fits, ~25 min
./python.sh src/eda/lean_review/t3.py --score --arm P2
./python.sh -m pytest test/lean_review -q
```
