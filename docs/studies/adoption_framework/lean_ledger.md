# The lean ledger: parts of the current best model adopted on a lean

9 October 2026 · For the owner, and for the agents who suggest adoptions under the [adoption framework](README.md) · **A ledger, not a decision.** It starts the record the framework asks for in [§ 9](README.md#9-the-ledger). It reads no new result: every number is copied from the linked document, or is arithmetic on copied numbers, marked † ([how](#how-the-numbers-were-made)).

**What it is for.**
* **Revisiting leans.** Each row says what would reverse the part, and when it is next read.
* **Correcting the claimed edge for luck.** Each row gives the luck its reading carries because the part was picked on the seasons that measured it. The total is set against the [clean-holdout forecast](../clean_holdout_rebuild/02_contamination_and_forecast.md#3-the-forecast).

**What counts as a lean** ([checklist](checklist.md), item 2): an adopted part of the [current best model](../../decisions/2026-10-08-current-best-model.md) whose support at its own target is unresolved, or whose support comes from seasons that also chose it.

**Keys.**
* Readings are mLL per match. **+ = the lean is better** than what it replaced or beat; each row names both.
* Intervals are 95%. One that clears 0 reads "better" or "worse"; otherwise "unresolved", with P(better) = Φ(est / SE) ([§ 7](README.md#7-reporting)). Verdicts belong to a declared primary; other cells are flags.
* **Luck** is a reading's expected selection inflation, about s · m_K ([§ 4](README.md#4-weighing-it-shrunk-gain-against-cost)): s is the reading's standard error and K the number of variants it was picked from. A single declared test carries none.
* **This file quotes 2025–26 results.** Keep it out of the clean room of the [clean-holdout rebuild](../clean_holdout_rebuild/README.md), whose briefs hold none.

## In short

* **Eleven leans.**
  * the seven the checklist names;
  * two structural choices made on 2022–26: the walk-forward calibration slopes, and feeding the odds as an input;
  * the Pinnacle-first odds input, decided after this ledger was started (row 11).
* **Rows 1, 3, 4 and 6 were reviewed on 9 Oct** in a debate with an independent reviewer, then tested on 2020–24 ([lean review](../lean_review/README.md#results-9-oct-2026)):
  * the long-memory profile stays, and stays per surface. Dropping it hurts at the close, and per surface reads slightly better than pooled;
  * `ios_points_short` reads about 0 at both prices: **the owner dropped it on 9 Oct** (row 6 is [settled](#settled));
  * stage 2 stays as a logged lean, with three proposed changes and two checks not yet run.
* **None earns stakes credit.** The edge that sizes stakes comes only from untouched matches at the venue's price ([§ 6](README.md#6-three-lanes)). A lean's real worth is already inside that measurement; its backtest gain is never added to it.
* **Three lean worse where it matters** (flags, not verdicts):
  * **stage 2, outside the seasons that chose it:** men 2020–24, −0.26 [−0.59, +0.06], P 0.05, seeds paired ([seed check](../../../data/studies/adoption_framework/seed_term_check.out));
  * **the per-surface IOS profile at the 24-hour price,** the reason it was kept: −0.06 [−0.43, +0.31], P 0.38† ([race § 5](../surface_rating_race/README.md#5-after-the-owners-decision-the-swap-in-the-model-as-it-stands));
  * **the short-memory IOS input after the repairs:** men −0.013 [−0.091, +0.066], P 0.37† ([repairs](../feature_alpha_audit/repairs.md#what-adds-beyond-elo-on-the-repaired-cohort)).
* **The luck this ledger can itemize** in the claimed closing-line edge ([provenance § 5](../feature_provenance/README.md#5-how-overfitted)):
  * stage 1, both tours: ≈ 0.2 (offset Elo 0.14, surface IOS 0.03, calibration 0.02; same source);
  * stage 2, men: ≈ 0.2 (its form 0.16, its memory 0.04†), at most ≈ 0.3.
* **The clean-holdout forecast** for the current model read on 2025–26: ≈ 0.35 (0.2–0.6) for stage 1, ≈ 0.25 (0.1–0.4) per men's match for stage 2 ([02 § 3](../clean_holdout_rebuild/02_contamination_and_forecast.md#3-the-forecast)).
  * Stage 2's items account for its forecast.
  * Stage 1's account for about 0.2 ([provenance § 5](../feature_provenance/README.md#5-how-overfitted)) of the 0.35 ([02 § 3](../clean_holdout_rebuild/02_contamination_and_forecast.md#3-the-forecast)). The rest sits in choices the documents do not bound one by one: the two-week profile's role, age, the odds as an input, the learner, and the designers' repeated looks.
* **Suggestion:** subtract the forecast, not the itemized sum, from an edge read on 2025–26: ≈ 0.35 for stage 1, and ≈ 0.48† per match for both stages on both tours ([the total](#the-total-against-the-clean-holdout-forecast)).
* **No look at the matches from 29 Jul 2026 against a price is on record** ([looks](#looks-at-the-matches-from-29-jul-2026)). The count starts here.

## The ledger

+ = the lean better; the seasons read are in brackets.

| # | Lean | Target | Reading at the target | Luck to subtract | Next read |
|---|---|---|---|---|---|
| 1 | [Per-surface IOS profile](#1-the-long-memory-ios-profile-built-per-surface-21-inputs) (21 inputs) | bets before the close; both tours | Polymarket 24 h out (2025–26), with the offset Elo in: −0.06 [−0.43, +0.31], unresolved, P 0.38† ([race § 5](../surface_rating_race/README.md#5-after-the-owners-decision-the-swap-in-the-model-as-it-stands)) | none in that reading; ≈ 0.03 in the close edge ([prov. § 5](../feature_provenance/README.md#5-how-overfitted)) | read on 9 Oct by the [lean review](../lean_review/README.md#results-9-oct-2026) (T2, T3): keep it, per surface |
| 2 | [Offset Elo](#2-the-offset-elo-6-inputs) (6 inputs) | bets before the close; both tours | 24 h out (2025–26): +0.78 [+0.03, +1.54], better, P 0.98† ([race § 4](../surface_rating_race/README.md#4-before-the-close-the-owners-question)) | 0.22–0.33† (K 2–3) in that reading; ≈ 0.14 in the close edge ([prov. § 5](../feature_provenance/README.md#5-how-overfitted)) | none scheduled |
| 3 | [Stage 2](#3-stage-2-the-walk-forward-serve-speed-adjustment), the speed adjustment | men; the backtest with the close as an input | 2024–26: +0.41 [+0.04, +0.78], better, P 0.99† ([study § 6.4](../serve_speed_tabpfn/README.md#64-the-nudge-the-same-information-applied-directly-s9)). 2020–24: −0.26 [−0.59, +0.06], P 0.05 ([seed check](../../../data/studies/adoption_framework/seed_term_check.out)) | 0.16 (K ≈ 3) ([prov. § 5](../feature_provenance/README.md#5-how-overfitted)) | the [lean review](../lean_review/README.md)'s T0 and T1; then item 7's first checkpoint, proposed at ≥ 2,000 men's matches |
| 4 | [Its 28-day memory](#4-stage-2s-28-day-memory) | as stage 2 | 28 against 14 days (2024–26): +0.13 [+0.05, +0.21], better, P > 0.99† ([adaptive](../serve_speed_tabpfn/adaptive.md#the-result)) | 0.04† (K 3) | with stage 2 |
| 5 | [Two-week profile](#5-the-two-week-profile-16-inputs) (16 inputs) | the close; men | given the odds, linear (2013–26): +0.51 [−0.11, +1.13], unresolved, P 0.95† ([audit](../feature_alpha_audit/README.md#the-closing-line-lead-survived-a-useful-challenge)) | 0.28–0.40† in that reading (K 6); unbounded in the edge ([prov. § 5](../feature_provenance/README.md#5-how-overfitted)) | none scheduled |
| 6 | [Short IOS memory](#6-the-short-ios-memory) | prediction beyond Elo; both tours | the input after two-week points, repaired (2019 on): men −0.013 [−0.091, +0.066], unresolved, P 0.37† ([repairs](../feature_alpha_audit/repairs.md#what-adds-beyond-elo-on-the-repaired-cohort)) | ≈ 0, not measured ([02 § 1](../clean_holdout_rebuild/02_contamination_and_forecast.md#1-why-re-selecting-cannot-clean-everything)) | **[settled](#settled):** dropped by the owner on 9 Oct, after the [lean review](../lean_review/README.md#results-9-oct-2026)'s T2 |
| 7 | [Age](#7-age-2-inputs) (2 inputs) | prediction beyond Elo; both tours | men, given Elo (2013–26): +1.42; before 2022 +0.37; no interval documented ([provenance_58](../../../data/studies/feature_provenance/provenance_58.csv)) | ≈ 0, not measured; the risk is the era ([02 § 1](../clean_holdout_rebuild/02_contamination_and_forecast.md#1-why-re-selecting-cannot-clean-everything)) | none scheduled |
| 8 | [ATP speed backfill](#8-the-atp-speed-backfill) | stage 2 at the close; men | 2020–24: +0.027 [−0.012, +0.066], unresolved, P 0.92 ([fix check](../../../data/studies/adoption_framework/seed_fix_check/scores.csv)) | 0: one declared test | none needed |
| 9 | [Walk-forward calibration](#9-the-walk-forward-calibration-slopes) | every forecast; both tours | against the fixed 2019–21 slope (2022–26): +0.10 [−0.03, +0.23], unresolved, P 0.93† ([surface IOS study](../surface_ios/README.md#side-finding-the-free-local-model-plus-one-slope-matches-the-paid-thinking-fit-observed)) | 0.04† (K 2); ≈ 0.02 in the close edge ([prov. § 5](../feature_provenance/README.md#5-how-overfitted)) | refitted each season; no comparison scheduled |
| 10 | [Odds fed as an input](#10-the-odds-fed-as-an-input-not-stacked) | the close; both tours | men, free models (2022–26): +0.79 fed directly against +0.10 stacked; no interval ([TabPFN-Thinking](../tabpfn_thinking/README.md#design-fixed-before-the-paid-call)) | not computable; 0.03 (0–0.1) in the rebuild ([02 § 2](../clean_holdout_rebuild/02_contamination_and_forecast.md#2-the-channels)) | none scheduled |
| 11 | [Pinnacle-first odds input](#11-the-pinnacle-first-odds-input) | bets at BetOnline, Pinnacle and Polymarket between the opening and the close; both tours | at BetOnline's last line (2020–25), against the model fed the books' average: −0.02 [−0.34, +0.31], unresolved, P 0.46 ([odds sources § 5](../odds_sources/README.md#5-the-model-retrained-on-pinnacle-first)) | ≈ 0.18 in that kind of reading, if counted as the best of four arms ([odds sources § 6](../odds_sources/README.md#6-the-suggestion-what-to-train-on-and-what-to-feed-venue-by-venue)) | its comparison with the frozen reference, run on 9 Oct |

**Stakes credit: no, for every row.** This is the framework's default ([§ 6](README.md#6-three-lanes)), and for stage 2 it is item 7's rule. A row's gain may count only once untouched matches show it at the venue's price, after costs; accepting that is the owner's call.

## Each lean

### 1. The long-memory IOS profile, built per surface (21 inputs)

* **What was adopted.** The offence, defence and matchup products of seven statistics. They entered the 53 inputs on 2 Oct; on 6 Oct the owner kept them built per surface ([decision](../../decisions/2026-10-06-surface-ios-profile.md)).
* **Target.** Bets before the close: "Especially since we may bet early before the close" (the owner, [decision](../../decisions/2026-10-06-surface-ios-profile.md)). Both tours, though the decision notes that the evidence supports men only. The only early-price history is Polymarket's price 24 hours out, 2025–26.
* **Reading at the target** (+ = built per surface better than pooled; 2,648 matches, [race § 5](../surface_rating_race/README.md#5-after-the-owners-decision-the-swap-in-the-model-as-it-stands); 2025–26 only):
  * with the offset Elo in, the model as it stands: −0.06 [−0.43, +0.31], unresolved, P 0.38† ([race § 5](../surface_rating_race/README.md#5-after-the-owners-decision-the-swap-in-the-model-as-it-stands));
  * on the original inputs: −0.02 [−0.42, +0.38], unresolved, P 0.46† (same source).
* **The readings it was adopted on** (2022–26, so 2025–26 included):
  * the declared primary, with the close, both tours: +0.01 [−0.10, +0.13], unresolved, P 0.57 ([framework § 4](README.md#4-weighing-it-shrunk-gain-against-cost); [study](../surface_ios/README.md#in-short));
  * without the odds, men: +0.83 [+0.39, +1.27], better. Both tours, that test's declared primary: +0.27 [−0.03, +0.58], unresolved, P 0.96† ([study](../surface_ios/README.md), "Without the odds").
* **Once the offset Elo is in, it adds nothing detectable** ([race § 5](../surface_rating_race/README.md#5-after-the-owners-decision-the-swap-in-the-model-as-it-stands)): at the close −0.01 [−0.10, +0.08] (P 0.41†); without a price +0.07 [−0.07, +0.21] (P 0.84†).
* **How it arose.**
  * **Inclusion, 2 Oct: a pattern found in the scored seasons.** It rests on the owner's per-statistic thesis, and entered against a null linear result: men, IOS profile with products, given the odds, −0.21 (−0.67 to 0.26) ([Stage D](../ufc_ideas/stageD.md), part 2). Its premise was read off TabPFN's 2022–26 outputs ([provenance_58](../../../data/studies/feature_provenance/provenance_58.csv)).
  * **Per surface, 6 Oct: a mechanism stated before one declared test,** then kept on a second criterion declared after that test was read ([provenance § 1](../feature_provenance/README.md#1-the-58-inputs)).
  * **K.** The representation R1 was chosen among three, plus a placebo, on 2019–21, before any test-season result: R1 +0.15, P1 +0.10, its placebo +0.06, R2 +0.03 ([study](../surface_ios/README.md), "The strategy, the audit, the plan"). The keep chose between 2 criteria: K = 2.
* **Luck to subtract.**
  * From the 24-hour reading: none. It was read after the decision and chose nothing.
  * From the men's no-odds reading that kept it: SE 0.22† × m_2 0.56 = 0.13†.
  * From the claimed close edge: ≈ 0.03 (2 arms, SE 0.06; [provenance § 5](../feature_provenance/README.md#5-how-overfitted)). In the rebuild: 0.01 (0–0.03) ([02, channel 2b](../clean_holdout_rebuild/02_contamination_and_forecast.md#2-the-channels)).
* **What would reverse it, and when.**
  * **Per surface to pooled: checklist item 8,** first in the build queue once item 1 is done. Its pre-declared rule: switch to pooled unless pooled is worse by more than 0.1 mLL, or worse with P(better) ≤ 0.2, on seasons ≤ 2024 ([checklist](checklist.md), item 8).
  * **At its own target:** a pre-declared read at the early price on the matches from 29 Jul 2026. Live data settles a part this size only over years: an input swap worth 0.1 takes about 7 years to reach z = 2 at the close ([decision review](../../../data/studies/adoption_framework/decision_review.out), section G; [§ 8](README.md#8-what-live-data-can-and-cannot-settle)).
* **Women.** No match-level test showed a benefit; the analyst recommended per surface for men and pooled for women ([decision](../../decisions/2026-10-06-surface-ios-profile.md), "Not decided").
* **Reviewed on 9 Oct 2026** ([lean review § 2](../lean_review/README.md#2-the-per-surface-long-memory-ios-profile-21-inputs)).
  * Once the offset Elo is in, none of the owner's three reasons holds at a sharp line.
  * Proposal: pooled on both tours, if the long-memory profile itself survives the review's 2×2 test (T2), read at Pinnacle's opening line on 2020–24.
  * Item 8 becomes the review's T3.
* **Read on 9 Oct 2026** by the review's tests ([results](../lean_review/README.md#results-9-oct-2026)). 2020–24, on the Pinnacle-first base; seeds paired.
  * **Dropping the whole profile** (+ = without it better):
    * at Pinnacle's opening line, the target: −0.18 [−0.56, +0.19], unresolved, P(better) 0.16 ([t2_summary.json](../../../data/studies/lean_review/t2_summary.json));
    * at the close: −0.29 [−0.63, +0.04], unresolved, P(better) 0.04; worse in all five seasons, mostly the men's ([t2_scores.csv](../../../data/studies/lean_review/t2_scores.csv)).
    * The profile stays (the rule's veto). It is about a quarter of the model's lead over the price.
  * **Per surface against pooled** (+ = per surface better):
    * at the opening line: +0.055 [−0.054, +0.163], unresolved, P(better) 0.84 ([t3_summary.json](../../../data/studies/lean_review/t3_summary.json));
    * at the close: +0.045 [−0.058, +0.149], P 0.81 (same source).
    * The shrunk gain clears the bar: **stay per surface.** Item 8 is answered.

### 2. The offset Elo (6 inputs)

* **What was adopted.** On 6 Oct the owner replaced the old Elo blend and `surface_first` with overall Elo, the surface offset, and two surface-switch pairs ([decision](../../decisions/2026-10-06-offset-elo.md)).
* **Target.** Bets before the close: "our plan is not to bet at the close but before the close" (the owner, [decision](../../decisions/2026-10-06-offset-elo.md)). Both tours. Tested at Polymarket's price 24 hours out, 2025–26.
* **Reading at the target** (+ = the offset Elo better than the old blend; 2,648 matches, [race § 4](../surface_rating_race/README.md#4-before-the-close-the-owners-question); 2025–26 only):
  * in the race, base → `elo_off`: +0.78 [+0.03, +1.54], better, P 0.98† ([race § 4](../surface_rating_race/README.md#4-before-the-close-the-owners-question)). A secondary of the race's plan, whose endpoints compared the two offset ratings ([plan](../surface_rating_race/plan.md));
  * in the model as it stood: +0.74 [+0.04, +1.45], better, P 0.98†. Run after the decision, not pre-registered ([race § 5](../surface_rating_race/README.md#5-after-the-owners-decision-the-swap-in-the-model-as-it-stands));
  * flags: clean event openers +0.88 [−0.38, +2.13], P 0.92† ([race § 4](../surface_rating_race/README.md#4-before-the-close-the-owners-question)); in the model, men +0.44 [−0.71, +1.58], P 0.77†, and women +1.11 [+0.04, +2.18], P 0.98† ([race § 5](../surface_rating_race/README.md#5-after-the-owners-decision-the-swap-in-the-model-as-it-stands)).
* **Other prices** ([race § 3](../surface_rating_race/README.md#3-inside-the-model-the-race); 2022–26): without a price +1.01 [+0.18, +1.84], better. At the close −0.05 [−0.24, +0.14], P 0.30†: a flag for bets at the close, not its target.
* **How it arose: the best of K variants.**
  * The owner's items 5–6 of 6 Oct, motivated by a 2019–26 market-anchoring reading. The offset structure was built on 2010–21 design years ([provenance_58](../../../data/studies/feature_provenance/provenance_58.csv)).
  * **K.** About 8 representations competed inside TabPFN, under up to four price conditions; about 45 variants were scored on windows containing 2022–26 before the swap ([provenance § 2](../feature_provenance/README.md#2-how-the-set-was-built)). The decisive arms were 2–3 ([02, channel 2a](../clean_holdout_rebuild/02_contamination_and_forecast.md#2-the-channels)): the old blend, the offset Elo and the TTT offset, which lost on the race's pre-registered cheaper-rating rule ([race](../surface_rating_race/README.md#the-answer)).
* **Luck to subtract.**
  * From the 24-hour reading: SE 0.385† × m_2–m_3 = 0.22–0.33†. If all 8 representations counted, with independent noise: × m_8 1.42† = 0.55†. After luck the reading is +0.45 to +0.56†, and +0.23† at worst: it still points the right way.
  * From the claimed close edge: ≈ 0.14 (K ≈ 8, SE 0.10; [provenance § 5](../feature_provenance/README.md#5-how-overfitted)). In the rebuild: 0.04 (0.02–0.11) ([02, channel 2a](../clean_holdout_rebuild/02_contamination_and_forecast.md#2-the-channels)).
* **What would reverse it, and when** (proposed; the owner's call).
  * **Its own target on untouched matches:** a pre-declared read at the early price, both tours, on the matches from 29 Jul 2026. 987 of them carry a Polymarket close, and 757† (330 ATP + 427 WTA) the price 24 hours before ([provenance § 7](../feature_provenance/README.md#7-untouched-data-on-disk); [counts](../../../data/studies/feature_provenance/counts/links_2025on.txt)).
  * **A faster signal, with no result read:** whether the price drifts toward its view between 24 hours and 30 minutes before the start. After the swap it drifted +0.23 [+0.04, +0.43] beyond the old model's view ([§ 8](README.md#8-what-live-data-can-and-cannot-settle)).
  * **Its luck, measured:** the decision bootstrap's C5 on stored forecasts ([plan, phase 3](../feature_provenance/plan.md#4-phase-3-the-decision-bootstrap-cheap-cpu-stored-forecasts)).
  * Next read: none scheduled.

### 3. Stage 2: the walk-forward serve-speed adjustment

* **What was adopted.** logit q = s_tour · η + b̃ · `spd_L`, for men; the women's column is 0 ([decision of 7 Oct](../../decisions/2026-10-07-speed-nudge.md); [template](../../decisions/2026-10-08-current-best-model.md)).
* **A logged lean, as checklist item 7 describes** ([checklist](checklist.md), item 7: the version the owner chose on 9 Oct 2026). Item 7 writes the decision amendments and sets the checkpoint; until then this row records its terms, all proposed there and the owner's call in their exact numbers:
  * stage 2 stays in the betting forecast, unchanged, and the daily speed collector keeps running;
  * **no stakes credit:** none of its backtest gain counts toward the edge estimate that sets stakes or decides whether to bet;
  * **the read:** the paired gain of both stages over stage 1, men, at the venue's bet-time price, on matches with speeds from 29 Jul 2026. Item 7 proposes the first checkpoint;
  * **the cut-off:** it leaves the betting forecast if that read lands at P(better) ≤ 0.2. It leaves earlier, as an alarm, if a season's reading is clearly worse: for example below −1.0 mLL with P(better) ≤ 0.1, the size of 2023's −1.26 ([backfill § 5](../infosys_atp_backfill/README.md#5-the-features-future-predictability));
  * **full adoption, with edge credit:** P(better) ≥ 0.8, with the shrunk gain above the feed's cost ([checklist](checklist.md), item 7).
* **Target.** Men. Adopted on the backtest with the closing odds as an input, scored against the average close. **At a bet-time price the adjustment was never read.** The speed *column* read +0.15 [−0.11, +0.40] at Polymarket's 24-hour price (men 2025–26, 1,442 matches; [study § 6.5](../serve_speed_tabpfn/README.md#65-women-no-odds-polymarkets-early-price)).
* **Reading at the target** (+ = with the adjustment better than calibrated stage 1; 2024–26, so 2025–26 included):
  * at adoption, men, 7,068 matches, the 14-day memory, instant speeds: +0.41 [+0.04, +0.78], better, P 0.99† ([study § 6.4](../serve_speed_tabpfn/README.md#64-the-nudge-the-same-information-applied-directly-s9)). The pre-registered primary, the speed as a TabPFN column, read +0.07 [−0.05, +0.18] ([study § 6.1](../serve_speed_tabpfn/README.md#61-the-primary-the-speed-column-in-tabpfn));
  * as decided, with the 28-day memory: instant speeds +0.54 [+0.13, +0.95]; today's sources +0.38 [+0.11, +0.64]; both better ([adaptive](../serve_speed_tabpfn/adaptive.md#the-result)).
* **Outside the seasons that chose it** (+ as above; no 2025–26):
  * men 2020–24, 11,672 matches, the frozen reference's stage 2 (28-day memory, today's sources): −0.26 [−0.59, +0.06], unresolved, P 0.05 with the seeds paired; −0.26 [−0.60, +0.07], P 0.06 as `compare.py` reports it ([seed check](../../../data/studies/adoption_framework/seed_term_check.out));
  * by season ([backfill § 5](../infosys_atp_backfill/README.md#5-the-features-future-predictability)): 2020 −0.03, 2021 −0.04, 2022 +0.16, 2023 −1.26 [−2.63, +0.10], 2024 +0.00. For the record, 2025 +0.32 and 2026 to 28 Jul +0.73 (same source).
* **Next season, as the backfill study infers it:** about +0.2 to +0.3 per men's match, with roughly a one-in-three chance of a losing season. From 2019–24 evidence alone: +0.10, with a 40% chance of a loss ([backfill § 5](../infosys_atp_backfill/README.md#5-the-features-future-predictability)).
* **How it arose: the best of K variants.**
  * A pre-registered secondary, adopted when the primary was unresolved. K ≈ 3 forms: the column, the adjustment shrunk and unshrunk ([provenance § 5](../feature_provenance/README.md#5-how-overfitted)).
  * 4 of 30 secondary intervals excluded 0, a 1.7% event under the simulated null ([study § 6.6](../serve_speed_tabpfn/README.md#66-multiplicity)). Men's 2024–26 was read four times in about 24 hours ([provenance § 2](../feature_provenance/README.md#2-how-the-set-was-built)).
  * The speed signal itself replicated blind: +0.103 [+0.029, +0.178] log-odds per SD in 2025–26 ([study § 6.2](../serve_speed_tabpfn/README.md#62-is-the-information-there-yes)).
* **Luck to subtract.** SE 0.19† × m_3 0.85 = 0.16; the audit's bound is ≈ 0.16 ([provenance § 5](../feature_provenance/README.md#5-how-overfitted)). In the rebuild: 0.07 (0.03–0.15) for the form, and 0.03 (0–0.06) for promoting the speed idea on 2022–26 ([02, S1 and S3](../clean_holdout_rebuild/02_contamination_and_forecast.md#2-the-channels)).
* **What live data can settle** ([decision review](../../../data/studies/adoption_framework/decision_review.out), section G). At about 0.35 SE per season, a true +0.28 takes about 6 years to reach z = 2, and +0.10 about 49. An alarm is quicker: a −1.3 season reaches z ≈ −2 within about a season ([statistics review](review_statistics.md), finding 6).
* **Next read:** item 7's first checkpoint, not yet set. Item 7 completes this row: it links its amendments and the checkpoint.
* **Reviewed on 9 Oct 2026** ([lean review § 1](../lean_review/README.md#1-stage-2-the-walk-forward-serve-speed-adjustment)): keep as item 7's logged lean, with 55–60% confidence.
  * Counting every season it has run, the choosing ones included, its walk-forward record over 2020–26 is −0.06 [−0.31, +0.19] ([arith.out](../../../data/studies/lean_review/arith.out)).
  * Proposed changes to item 7:
    * a coefficient that allows for season-to-season disagreement (b ≈ 0.030 for 2027 instead of 0.0444; [arith_r2.out](../../../data/studies/lean_review/arith_r2.out));
    * Challenger speeds kept out;
    * the first checkpoint at ≥ 2,000 men's matches ([lean review § 1](../lean_review/README.md#1-stage-2-the-walk-forward-serve-speed-adjustment)).
  * Two checks first: T0, a speed replay, and T1, that the Pinnacle-first base absorbs at most half of the speed information.

### 4. Stage 2's 28-day memory

* **What was adopted.** `spd_L`, the speed form with a 28-day half-life, for every match (the owner, 8 Oct; [decision](../../decisions/2026-10-07-speed-nudge.md)).
* **Target.** As stage 2.
* **Reading at the target** (+ = the 28-day memory better than the 14-day one; men 2024–26, so 2025–26 included; [adaptive](../serve_speed_tabpfn/adaptive.md#the-result)):
  * instant speeds, where the switch equals the 14-day memory: +0.13 [+0.05, +0.21], better, P > 0.99†;
  * today's sources, against the switch: +0.09 [+0.02, +0.16], better (same source);
  * the 28-day memory led in all 12 season × scenario cells (same source).
* **How it arose: the best of K variants, K = 3** (14-day, 28-day, the switch). The value 28 was the arg-max of a result-free target ([provenance_stage2](../../../data/studies/feature_provenance/provenance_stage2.csv)). It was adopted after two outcome runs on men's 2024–26 ([adaptive](../serve_speed_tabpfn/adaptive.md#caveats), caveats).
* **Luck to subtract.**
  * From its own reading: SE 0.041† × m_3 0.85 = 0.035†.
  * From stage 2's gain: at most 0.16, a worst case that uses stage 2's SE rather than the difference's ([provenance § 5](../feature_provenance/README.md#5-how-overfitted)). In the rebuild: 0.04 (0–0.07) ([02, S2](../clean_holdout_rebuild/02_contamination_and_forecast.md#2-the-channels)).
* **What would reverse it, and when.** The decision bootstrap's C8 finding the 28-day advantage to be luck ([plan, phase 3](../feature_provenance/plan.md#4-phase-3-the-decision-bootstrap-cheap-cpu-stored-forecasts)). Next read: with stage 2's checkpoint, as a flag.
* **Reviewed on 9 Oct 2026** with stage 2 ([lean review § 1](../lean_review/README.md#1-stage-2-the-walk-forward-serve-speed-adjustment)): unchanged; the memory rides with stage 2.

### 5. The two-week profile (16 inputs)

* **What was adopted.** `form_<12>` and `formdef_<4>`: two-week opponent-adjusted form on twelve statistics, and its defensive mirror on four. In the model since the 53 inputs of 2 Oct ([provenance § 1](../feature_provenance/README.md#1-the-58-inputs)).
* **Target.** The close: it entered as "the main closing-line lead" ([audit](../feature_alpha_audit/README.md)). The lead was the men's; the inputs serve both tours.
* **Reading at the target** (+ = with the profile better than the odds alone; the linear harness; men):
  * all scored seasons, 2013–26 (2025–26 included), 31,661 matches: +0.51 [−0.11, +1.13], unresolved, P 0.95†. Calendar-week intervals; the original [−0.05, +1.07] treated matches as independent ([audit](../feature_alpha_audit/README.md#the-closing-line-lead-survived-a-useful-challenge));
  * by era ([Stage D](../ufc_ideas/stageD.md), part 2): 2013–16 −0.07, 2017–19 −0.01, 2020–21 +1.49, 2022–26 +0.92;
  * repaired chronology, men 2019 to 13 Jan 2026, 16,333 matches, beyond recalibrated Pinnacle: +0.355 [−0.251, +0.961], unresolved, P 0.87†. From 2022 on: +0.273 [−0.597, +1.143], P 0.73† ([repairs](../feature_alpha_audit/repairs.md#closing-line-comparisons-after-rebuilding));
  * women: +0.02 [−0.51, +0.54], P 0.53† ([Stage D](../ufc_ideas/stageD.md), part 2);
  * inside TabPFN, with and without the profile: no reading is documented.
* **How it arose: a pattern found in the scored seasons** ([§ 2](README.md#2-how-the-idea-arose)), so a lead only.
  * The owner asked on 2 Oct for offence and defence ratings of individual statistics; the constants were fitted on 2013–18 ([provenance_58](../../../data/studies/feature_provenance/provenance_58.csv)).
  * Its role as the closing-line lead was found in the scored seasons: "positive in every season from 2020 on and absent before" ([Stage D](../ufc_ideas/stageD.md), part 2).
  * **K = 6** ([statistics review](review_statistics.md), finding 9); Stage D's part 2 scored 10 models ([Stage D](../ufc_ideas/stageD.md), part 2).
* **Luck to subtract.**
  * From its own reading: SE 0.316† × m_6 1.27 = 0.40†, or 0.28† if the six variants' noise correlates 0.5 ([decision review](../../../data/studies/adoption_framework/decision_review.out), section E). After luck, +0.11 to +0.23†.
  * From the claimed edge: unbounded. The audit could not bound the 2 Oct family choice ([provenance § 5](../feature_provenance/README.md#5-how-overfitted)). In the rebuild, the whole family set leaves 0.01 (0–0.05) ([02, channel 2e](../clean_holdout_rebuild/02_contamination_and_forecast.md#2-the-channels)).
* **What would reverse it, and when.** The hindsight replay at 2022, whose menu offers two-week memories of 1, 2, 4 or 8 weeks, or 52 weeks ([plan, phase 4](../feature_provenance/plan.md#5-phase-4-the-hindsight-replay-moderate-already-seen-data)). Live data cannot settle a part this size ([§ 8](README.md#8-what-live-data-can-and-cannot-settle)). Next read: none scheduled.

### 6. The short IOS memory

**[Settled](#settled) on 9 Oct 2026: the owner dropped `ios_points_short` from the model** ([amendment](../../decisions/2026-10-08-current-best-model.md)). The record below is kept as it was.

* **What was adopted.** `ios_points_short`: the IOS points matchup with a memory of 4 weeks for men and 13 weeks for women. Its κ and τ were fitted on 2013–18; the memory is the one constant of the 58 picked on all seasons ([provenance § 3](../feature_provenance/README.md#3-what-was-fitted-to-the-current-era)).
* **Target.** Prediction beyond Elo, both tours: the screens' measure. In the model it sits beside the odds.
* **Readings at the target** (+ = with the input better; gains over Elo, no odds; 2025–26 included):
  * **the memory**, all seasons ([Stage B](../ufc_ideas/stageB.md#the-ten-strongest-rows-per-tour)): men 4 weeks 3.72 (3.30 to 4.13) against 13 weeks 3.42 (2.92 to 3.92); women 13 weeks 5.02 (4.16 to 5.88) against 4 weeks 4.58 (3.75 to 5.42). The ranges treat matches as independent and are not paired;
  * before 2022 alone the same memories win: men +3.16 against +2.60, women +6.38 against +6.01 ([provenance_58](../../../data/studies/feature_provenance/provenance_58.csv));
  * in 2022–26 the men's 13 weeks scored higher, 4.56 against 4.49, so those seasons did not drive the men's pick ([Stage B](../ufc_ideas/stageB.md#the-ten-strongest-rows-per-tour));
  * **the input after the two-week adjusted points,** repaired cohort, 2019 on: men −0.013 [−0.091, +0.066], unresolved, P 0.37†; women −0.052 [−0.139, +0.035], P 0.12† ([repairs](../feature_alpha_audit/repairs.md#what-adds-beyond-elo-on-the-repaired-cohort)). Before the repairs, 2022 on: men +0.13 [+0.05, +0.20] ([audit](../feature_alpha_audit/README.md#what-really-adds-beyond-elo)).
* **How it arose: the best of K variants, K = 2.** The IOS diagnostics were added after the first all-season rundown had been read: two memories and one ridge, none tuned ([Stage B](../ufc_ideas/stageB.md#limitations), limitations). 42% of the men's and 69% of the women's matches in that pool were from 2022–26 ([provenance § 3](../feature_provenance/README.md#3-what-was-fitted-to-the-current-era)).
* **Luck to subtract.** About 0, not measured. Pre-2022 data pick the same memories, so the pick hardly depended on the later seasons' noise ([02 § 1](../clean_holdout_rebuild/02_contamination_and_forecast.md#1-why-re-selecting-cannot-clean-everything), point 5). In the rebuild: 0, since the memory becomes an axis chosen on development data ([02, channel 1](../clean_holdout_rebuild/02_contamination_and_forecast.md#2-the-channels)).
* **What would reverse it, and when.** A memory chosen on development data only, or the decision bootstrap's C3 ([plan, phase 3](../feature_provenance/plan.md#4-phase-3-the-decision-bootstrap-cheap-cpu-stored-forecasts)). Next read: none scheduled.
* **Reviewed on 9 Oct 2026** ([lean review § 3](../lean_review/README.md#3-ios_points_short-the-short-memory-ios-points-matchup)).
  * Its value inside the model has never been measured.
  * The repaired reading above was on a main-tour-only history, not the model's.
  * Proposal: remove it if the review's 2×2 test (T2) allows, read at Pinnacle's opening line.
* **Read on 9 Oct 2026** by the review's T2 ([results](../lean_review/README.md#results-9-oct-2026)). 2020–24, on the Pinnacle-first base; + = without the input better:
  * at Pinnacle's opening line: −0.03 [−0.11, +0.06], unresolved, P(better) 0.25 ([t2_summary.json](../../../data/studies/lean_review/t2_summary.json));
  * at the close: −0.00 [−0.09, +0.08], P 0.47 (same source).
  * Nothing measurable either way. The rule fixed in advance proposes removal by +0.0004 on a bar of 0: its shrunk worth and its assumed upkeep are almost equal (same source). The owner decides.

### 7. Age (2 inputs)

* **What was adopted.** Age and squared age around 25, A − B ([provenance § 1](../feature_provenance/README.md#1-the-58-inputs)).
* **Target.** Prediction beyond Elo, both tours: Stage 4's screen. The audit kept it in "the prediction baseline" ([audit](../feature_alpha_audit/README.md)).
* **Readings at the target** (+ = with age better than Elo alone; 2025–26 included):
  * men +1.42 over all scored seasons and +2.88 in 2022–26, a "finding" ([Stage 4 § 2](../predictability_diagnostic/stage4.md#2-the-rundown)); women +0.56, "possible" ([provenance_58](../../../data/studies/feature_provenance/provenance_58.csv));
  * the reports give no interval for it, and Stage 4's intervals assume independent matches, so they are too narrow ([provenance § 1](../feature_provenance/README.md#1-the-58-inputs));
  * **by era** ([provenance_58](../../../data/studies/feature_provenance/provenance_58.csv)): men before 2022 +0.37, with 2013–16 −1.10, worse than Elo alone; 2020–21 +4.19; 2022–26 +2.88. Women before 2022 +0.02;
  * at the close: no reading of age alone. The audit's block of age, surface familiarity and load added +4.90 [+4.16, +5.64] given Elo (men, 2022 on), and its separate ablations were added after the block was read ([audit](../feature_alpha_audit/README.md#what-really-adds-beyond-elo)).
* **How it arose: many ideas screened.** Stage 4's 59 candidates were listed before any result, and scored as 325 versions ([provenance § 2](../feature_provenance/README.md#2-how-the-set-was-built)). Its value comes from the 2020+ seasons.
* **Luck to subtract.** About 0 in its own reading, not measured: picks made on gains over Elo are near-certain, with effects of 1–5 mLL against noise of 0.1–0.3 ([02 § 1](../clean_holdout_rebuild/02_contamination_and_forecast.md#1-why-re-selecting-cannot-clean-everything), point 5). The risk is the era, not the pick. Its share of the claimed edge is not measured.
* **What would reverse it, and when.** The hindsight replay's "age in or out" axis ([plan, phase 4](../feature_provenance/plan.md#5-phase-4-the-hindsight-replay-moderate-already-seen-data)). Next read: none scheduled.

### 8. The ATP speed backfill

* **What was adopted.** The ATP's decrypted Stats Centre files of 2018 to Oct 2021, in stage 2's speed history since the evening of 8 Oct ([amendment](../../decisions/2026-10-08-current-best-model.md); [study](../infosys_atp_backfill/README.md)).
* **Target.** Stage 2 at the close, men: the frozen-reference comparison on 2020–24.
* **Reading at the target** (+ = with the backfill better; 2020–24, so no 2025–26):
  * men, 11,672 matches: +0.027 [−0.012, +0.066] with the seeds paired, unresolved, P 0.92 ([fix check](../../../data/studies/adoption_framework/seed_fix_check/scores.csv), checklist item 1). As first reported, unpaired: [−0.073, +0.128], P 0.71 ([study § 4.1](../infosys_atp_backfill/README.md#41-the-official-comparison-with-the-frozen-reference); [seed check](../../../data/studies/adoption_framework/seed_term_check.out));
  * both tours: +0.014 [−0.006, +0.035], P 0.92; first reported as [−0.073, +0.102], P 0.63 (same sources).
  * The study also read 2025 to 28 Jul 2026 twice, in exploratory runs; no choice was made on it ([study § 6](../infosys_atp_backfill/README.md#6-looks-at-the-proposed-clean-holdout)).
* **How it arose: more of a kind of data already used** ([§ 2](README.md#2-how-the-idea-arose)), one declared comparison, K = 1. Free and reversible; the framework's worked example adopts it and claims no edge ([§ 4](README.md#4-weighing-it-shrunk-gain-against-cost)).
* **Luck to subtract.** 0.
* **What would reverse it, and when.**
  * Only a bug in the files: the data lane.
  * No outcome read can settle it. Live, it changes one coefficient: b̃ for 2027, 0.0432 → 0.0444 ([study § 4.1](../infosys_atp_backfill/README.md#41-the-official-comparison-with-the-frozen-reference)). A true +0.027 takes about 10 years to reach z = 2 at the paired SE ([decision review](../../../data/studies/adoption_framework/decision_review.out), section G).
  * To undo, drop `speed_panel_backfilled.parquet` ([amendment](../../decisions/2026-10-08-current-best-model.md)). Next read: none needed.

### 9. The walk-forward calibration slopes

* **What was adopted.** One slope per tour on the base's log-odds, refitted each season on 2019..Y−1; stage 2 fits them jointly with b ([template](../../decisions/2026-10-08-current-best-model.md)).
* **Target.** Every forecast, both tours; read at the close.
* **Reading at the target** (+ = the walk-forward slopes better than the fixed 2019–21 slope; both tours 2022–26, so 2025–26 included): +0.10 [−0.03, +0.23], unresolved, P 0.93† ([surface IOS study](../surface_ios/README.md#side-finding-the-free-local-model-plus-one-slope-matches-the-paid-thinking-fit-observed), side finding).
  * Calibrating at all is not a lean. Against the close, the local model gains +0.53 [−0.35, +1.42] raw, +1.20 [+0.51, +1.89] with the fixed slope and +1.30 [+0.65, +1.94] walk-forward (same source).
* **How it arose: structural.** The need was found on 2022–26 by an audit's side finding, and the slopes were fitted on 2019–21. The walk-forward refit was added after the women's drift showed on 2022–26 ([provenance_stage2](../../../data/studies/feature_provenance/provenance_stage2.csv)). K = 2 forms; the audit counts 2–3 ([provenance § 2](../feature_provenance/README.md#2-how-the-set-was-built)).
* **Luck to subtract.**
  * From its own reading: SE 0.066† × m_2 0.56 = 0.04†.
  * From the claimed close edge: ≈ 0.02, from an assumed SE of 0.03 ([provenance § 5](../feature_provenance/README.md#5-how-overfitted)). The documented interval implies SE 0.066†, which gives 0.04†. In the rebuild: 0.01 (0–0.02) ([02, channel 2c](../clean_holdout_rebuild/02_contamination_and_forecast.md#2-the-channels)).
* **What would reverse it, and when.** The decision bootstrap's C6 ([plan, phase 3](../feature_provenance/plan.md#4-phase-3-the-decision-bootstrap-cheap-cpu-stored-forecasts)), or the realisation slope on untouched matches ([§ 5](README.md#5-checks-before-suggesting-adoption)). The slopes are refitted every season by rule; no comparison is scheduled.

### 10. The odds fed as an input, not stacked

* **What was adopted.** The closing odds' log-odds as the first of the 58 inputs. The alternative was a no-odds forecast stacked with the odds afterwards ([TabPFN-Thinking](../tabpfn_thinking/README.md#design-fixed-before-the-paid-call), 2 Oct).
* **Target.** The close, both tours.
* **Reading at the target** (+ = the odds fed directly better; men, free linear models, 2022–26, so 2025–26 included; same source): fitted directly beside the odds, the profile gained +0.79 over the recalibrated odds; a no-odds forecast from all the inputs, stacked with the odds, gained +0.10. No interval for the difference is documented, so P(better) is not computable.
* **How it arose: structural,** and standard practice ([provenance_58](../../../data/studies/feature_provenance/provenance_58.csv)). Chosen between 2 designs on the free models' 2022–26 scores: K = 2.
* **Luck to subtract.** Not computable from the documents. In the rebuild: 0.03 (0–0.1) ([02, channel 2d](../clean_holdout_rebuild/02_contamination_and_forecast.md#2-the-channels)).
* **What would reverse it, and when.** The decision bootstrap's C1 ([plan, phase 3](../feature_provenance/plan.md#4-phase-3-the-decision-bootstrap-cheap-cpu-stored-forecasts)), or the rebuild's check on development data ([02, channel 2d](../clean_holdout_rebuild/02_contamination_and_forecast.md#2-the-channels), Q6). Next read: none scheduled.

### 11. The Pinnacle-first odds input

* **What was adopted.** On 9 Oct the owner made the model's odds input "Pinnacle first", in training and live ([decision](../../decisions/2026-10-09-pinnacle-first-odds-input.md)):
  * in training, Pinnacle's margin-free close, then BetOnline's close where Pinnacle has none, then the books' average where neither prices a match;
  * live, Pinnacle's current line at every venue.
* **Target.** Bets at BetOnline, Pinnacle and Polymarket between the opening and the close, both tours ([odds sources § 6](../odds_sources/README.md#6-the-suggestion-what-to-train-on-and-what-to-feed-venue-by-venue)).
* **Reading at the target** (+ = Pinnacle first more accurate). At BetOnline's last line, 2020–25, so 2025 is included and 2026 is not; 25,637 matches; seeds 0–3; no speed stage ([odds sources § 5](../odds_sources/README.md#5-the-model-retrained-on-pinnacle-first)):
  * against the earlier model fed the books' average, the declared primary: −0.02 [−0.34, +0.31], unresolved, P(better) 0.46 (same source);
  * against the earlier model fed BetOnline's own line, the alternative that needs no new feed: +0.41 [+0.05, +0.76], better (same source);
  * at BetOnline's opening, each fed the opening line: +0.25 [+0.00, +0.49], better (borderline; same source);
  * realisation against its own input: 1.06 [0.74, 1.37] (same source).
* **How it arose: structural** (how the price enters the learner), on the owner's mechanism: a weighted average of the sharp books, whose walk-forward weights fell almost all on Pinnacle. Nine price candidates were compared on 2019–25, then one declared model arm was fitted ([odds sources § 6](../odds_sources/README.md#6-the-suggestion-what-to-train-on-and-what-to-feed-venue-by-venue)).
* **Luck to subtract.** About 0.18 in its reading against the model fed BetOnline's line, if counted as the best of four retrained arms (same source). It is not in the totals below, which the forecast predates.
* **What would reverse it, and when.** The study's conditions (same source):
  * the candidate build reading clearly worse than the reference;
  * Pinnacle's guest feed failing, or being withheld at bet time;
  * Pinnacle's live prices drifting away from its closes.

  Next read: the instance's decided comparison with the frozen reference, run on 9 Oct (`data/studies/current_best_model/pinnacle_first_2026-10-09/vs_reference_2026-10-08/`; [report](../pinnacle_first/README.md), being written).

## Settled

| Row | Lean | How it was settled | The reading that settled it |
|---|---|---|---|
| [6](#6-the-short-ios-memory) | `ios_points_short`, the short IOS memory | **Dropped by the owner on 9 Oct 2026:** "Drop ios_points_short" ([amendment](../../decisions/2026-10-08-current-best-model.md)). The model has 57 inputs | The [lean review](../lean_review/README.md#results-9-oct-2026)'s T2, 2020–24, Pinnacle-first base, + = without it better: −0.03 [−0.11, +0.06] at Pinnacle's opening line (P(better) 0.25), −0.00 [−0.09, +0.08] at the close (P 0.47) ([t2_summary.json](../../../data/studies/lean_review/t2_summary.json)) |

Its luck (about 0, row 6) leaves the totals below unchanged.

## The total, against the clean-holdout forecast

| | Stage 1, both tours | Stage 2, men (its gain over stage 1) |
|---|---|---|
| **Itemized here, in the claimed close edge** | offset Elo 0.14 + surface IOS 0.03 + calibration 0.02 ≈ **0.2** ([provenance § 5](../feature_provenance/README.md#5-how-overfitted)) | form 0.16 ([provenance § 5](../feature_provenance/README.md#5-how-overfitted)) + memory 0.04† ≈ **0.2**; at most 0.16 + 0.16 ≈ 0.3 (same source) |
| **Not itemized:** no per-choice bound in the documents | the two-week profile's role, age, the short IOS memory, the odds as an input; the learner, kept after its first test on 2022–26; the designers' repeated looks | promoting the speed idea on 2022–26 |
| Their residual even after a rebuild, so a floor for the current model | 2d 0.03 + 2e 0.01 + 3 0.03 + 4 0.05 ≈ 0.12† ([02 § 2](../clean_holdout_rebuild/02_contamination_and_forecast.md#2-the-channels)) | S3 0.03 ([02 § 2](../clean_holdout_rebuild/02_contamination_and_forecast.md#2-the-channels)) |
| **The forecast for the current model read on 2025–26** | **≈ 0.35 (0.2–0.6)** ([02 § 3](../clean_holdout_rebuild/02_contamination_and_forecast.md#3-the-forecast)) | **≈ 0.25 (0.1–0.4)** (same source) |

**Reading** (inferred).
* **Stage 2:** the items (≈ 0.2) plus the floor (0.03) ≈ 0.23†, close to the forecast. The luck is large against stage 2's own size: about 0.25 of a +0.38 to +0.54 reading.
* **Stage 1:** the items (0.19†) plus the floor (≈ 0.12) ≈ 0.3†, close to the forecast's 0.35. The items alone sit at the bottom of its range.
* **Both stages, both tours.** Stage 2's luck is per men's match, and men are 4,394 of the 8,593 matches of 2025 to 28 Jul 2026 ([02 § 3](../clean_holdout_rebuild/02_contamination_and_forecast.md#3-the-forecast)). It adds 0.25 × 0.51 ≈ 0.13† per match, so ≈ 0.48† in all.
* **Where it applies** ([02 § 1](../clean_holdout_rebuild/02_contamination_and_forecast.md#1-why-re-selecting-cannot-clean-everything), point 2):
  * in full, to an edge read inside the choices' windows (2022–26; 2024–26 for stage 2);
  * in proportion to the share of matches inside them, for a wider window;
  * not at all on the matches from 29 Jul 2026, which no choice has read.
* **Suggestion** (the owner's call). Quote an edge read on 2022–26 or 2025–26 with the forecast subtracted: ≈ 0.35 for stage 1, ≈ 0.48† for both stages on both tours. Give the itemized ≈ 0.2 beside it, as the part accounted for. The decision bootstrap would replace these bounds with measurements; it needs only the CPU and stored forecasts, and reads no new season ([plan, phase 3](../feature_provenance/plan.md#4-phase-3-the-decision-bootstrap-cheap-cpu-stored-forecasts)).

## Looks at the matches from 29 Jul 2026

The framework asks for every look at sealed data to be counted ([§ 9](README.md#9-the-ledger)).
* **On record at 9 Oct 2026: no look against a price.**
  * The bet-timing study: the matches "from 29 July 2026 onward, which no study has read" ([bet timing](../bet_timing/README.md#what-it-does-and-does-not-show)).
  * The only reads are older. Studies of the 30 Sep build scored 787 of the 1,014 post-frame main-tour matches without odds; 227 are untouched ([provenance § 7](../feature_provenance/README.md#7-untouched-data-on-disk)). The 787 made up about 0.2% to 3% of the matches those studies scored ([provenance § 6](../feature_provenance/README.md#6-the-rebuild-question-how-much-leakage-do-these-features-bring)).
* **The seal itself is proposed, not decided** ([provenance § 9](../feature_provenance/README.md#9-decisions-for-the-owner), decision 1; [rebuild log](../clean_holdout_rebuild/decision_log.md), entry 0.8).
* Log each future look below.

| # | Date | Who | Matches | What was read | Why |
|---|---|---|---|---|---|
| – | – | – | – | none yet | – |

## Not in the ledger, and why

* **The 19 inputs of group A.** Their target was prediction beyond Elo, and pre-2022 evidence alone makes the same choice ([provenance § 1](../feature_provenance/README.md#1-the-58-inputs)). The odds' form of entry is row 10.
* **Data fixes:** the Slam box-score overrides, the corrections of 8 Oct, and the 130 impossible speed records. They were decided on data evidence; an outcome reading is a bug check only ([§ 2](README.md#2-how-the-idea-arose)).
* **The learner and its settings.**
  * TabPFN was the owner's choice before any tennis test. Its 8 estimators and temperature 0.9 are the UFC project's settings, never varied here ([provenance_stage2](../../../data/studies/feature_provenance/provenance_stage2.csv)).
  * The local checkpoint replaced the paid Thinking fit after the two read level: +0.01 [−0.37, +0.39], unresolved, P 0.52†. The cheaper one was kept ([surface IOS study](../surface_ios/README.md#side-finding-the-free-local-model-plus-one-slope-matches-the-paid-thinking-fit-observed), side finding).
  * Its imprint on 2025–26 is the forecast's channel 3 ([02 § 2](../clean_holdout_rebuild/02_contamination_and_forecast.md#2-the-channels)).
* **Stage 2's constants:** τ = 0.05 was pre-registered, and the speed filter was tuned on speeds of 2022 and earlier against the next match's speed, not results ([provenance_stage2](../../../data/studies/feature_provenance/provenance_stage2.csv)).

## How to keep it

* **A lean read again:** add the reading under its row, with the date, the seasons and the look. A look at the matches from 29 Jul 2026 also goes in the looks table.
* **A part adopted on a lean:** add a row with the same fields. Checklist items 7 (stage 2's checkpoint), 8 (if pooled replaces per surface) and 9 (the lower-level share, if adopted) point here.
* **A lean settled:** move it under a "Settled" heading with the reading that settled it. Whether its gain may then count toward the stakes edge is the owner's call.
* **When the decision bootstrap runs:** replace the bounds with its measured luck.

## How the numbers were made

* **Copied numbers** link to the document that holds them.
* **† marks arithmetic on copied numbers,** done for this ledger without reading any data:
  * SE = (upper − lower) / 3.92, from the copied 95% interval, and P(better) = Φ(est / SE) ([§ 7](README.md#7-reporting)). For an interval built on a t quantile this overstates the SE slightly. P values a document states are copied as they are;
  * luck = SE × m_K, with m_2 0.56, m_3 0.85 and m_6 1.27 from [§ 4](README.md#4-weighing-it-shrunk-gain-against-cost), and m_8 1.42 by the same formula, the expected maximum of K standard normals. Noise shared by the variants, at correlation ρ, scales it by √(1 − ρ) ([decision review](../../../data/studies/adoption_framework/decision_review.out), section E);
  * sums and the men's share, as shown where they appear.
* **Readings published before the seed-term fix of 9 Oct** (checklist item 1) keep their wider intervals where the arms share seed numbers ([known problems](README.md#known-problems-in-the-tools-9-oct-2026)). Their P(better) sits nearer 0.5 than it should; the seed-paired figures are given where they exist.
