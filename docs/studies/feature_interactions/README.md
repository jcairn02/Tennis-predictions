# Feature interactions: a multi-agent cone, from 116 ideas to one test

7 October 2026 · Research evidence, not a production, model or betting decision. Checked against the evidence by the meta-auditor ([checkpoint 3](meta/checkpoint_3.md)).

**The owner's request (6 Oct 2026).**
* Flesh out reasonable **interactions** between features of the feature universe of the best local, non-thinking TabPFN-3.5 model, including features it does not use yet. Reason about which match-level statistics interact, not only which are predictive alone.
* Research what other modellers have published.
* Narrow the universe like a cone with a team of Opus agents (brainstormers, auditors, a meta-auditor) working back and forth, explore with EDA, and test the best candidates in the model.
* Keep 2025–2026 for the test.

**Keys.**
* **z** is a coefficient's z: positive = in the candidate's declared direction.
* **Gains** are milli-log-loss (mLL) per match, paired: **positive = the named forecast has the lower log loss (better)**.
* A 95% interval that spans 0 is a **tie**.
* **Observed** = computed here; **inferred** = reasoning; **suggestion** = not decided.

## In short

* **Observed: the cone.**
  * 116 round-0 ideas from four independent brainstormers (96 live, 20 closed by their own authors' calculations) became 91 master ideas.
  * The auditors and a rebuttal round turned those into a family of 35 pre-registered hypotheses, 34 after a dropped block.
  * The family was frozen by hash and screened once on 2014–2024 against the current best model's own forecast.
  * **One hypothesis passed every gate:** B-INJ, which as measured is **rust after a break of six weeks or more** (mostly the off-season). It fades over the matches since the return, and is stronger with age past 28, after a retirement or walkover the player gave just before the break, and with a protected ranking (a PR or SR entry).
    * Its joint z is **+3.99**: +3.51 on 2014–2021 and +1.93 on 2022–2024.
    * Its out-of-sample gains in the screen were ties: +0.19 [−0.03, +0.42] mLL (2014–2021, leave-one-season-out) and +0.02 [−0.31, +0.36] (2022–2024, forward). The claim rested on the coefficient test, as pre-registered.
    * Weighted Holm gives 0.002. It survives without the 2020–2021 pandemic seasons (+3.48, exploratory).
    * The red team re-implemented it to 8.6e-12 and found no leak.
* **Observed: the final test on 2025–2026 does not confirm it.**
  * The pre-registered primary, the disjoint-seed encompassing coefficient of the bundle beyond the current best, is **b = −0.21 [−1.35, +0.93], a tie**.
  * B-INJ's own effect size is **−0.27 [−0.64, +0.10] mLL, a tie**, leaning worse.
  * Both intervals reach only to about the expected size: b's to +0.93, against an expectation of about 0.86 (1 is the nudge as fitted; the Tweedie ratio is 3.41/3.99); the effect size's to +0.10 mLL, against an expected 0.12–0.16.
  * The test had 19–26% power at the expected gain, so a tie was the likely reading even if B-INJ is real. The 2014–2024 evidence stands as stated, but **the finding is not confirmed out of sample**.
* **Observed: no other member passed the gates.** Not one of the serve/return matchup, serve-dominance, composition, style, fatigue × style or market-calibration interactions passed against the model (the gating base):
  * the serve-dominance leverage that three lenses and the literature ranked first: Wald p 0.21;
  * the composed serve-point profile, the highest-weighted idea: it does not replicate;
  * the TabPFN arm given both players' levels (17 sums): joint p 0.042, not eligible.
* **Observed: the price lens.** It was the owner's ranking, reported but not gated. Under the family's own rules it would also have made **B-VENUE** (venue pace × the server's ace offence) bundle-eligible: joint z +2.72, q 0.075, against +2.50 and q 0.15 against the model.
* **Inferred: why the interactions fail.**
  * The close applies 43% of the iid point model's serve-dominance scaling at matched strength. The damped truth, estimated from the day-noise split, is about 39% (men, best of three; ruling MAT-R3). The price is about right (inferred).
  * TabPFN's 58 inputs recover much of the rest non-linearly.
  * The one survivor is a within-player interaction of the calendar (break length × matches since × age × the last match's status), not a match-level statistic.
* **Observed, side findings.**
  * The current best beats the calibrated **Pinnacle** close too: +1.06 [+0.27, +1.85] mLL on 2022–2024 (2014–2021: +0.21 [−0.37, +0.78] against Pinnacle and +0.28 [−0.28, +0.83] against the average, both ties). Its edge in 2022–2024 is not just the average close lagging Pinnacle.
  * Pair prominence × the forecast came out against its declared direction (z −2.99): one of 34 one-sided tests, and a reversal was never a registered hypothesis. Inferred: the model may be too steep for elite pairs. A one-sided rule cannot count it; it is a lead.

## The team and how it worked

The configuration ([team.md](team.md)) was fixed before the first agent ran and critiqued at once ([team_critique.md](round0/team_critique.md)); the adopted amendments are in [plan.md](plan.md).

| Role | What it did |
|---|---|
| Four brainstormers (mechanics, mathematics, market, body and schedule) | independent idea lists, blind to each other and to the literature, then one rebuttal round with literature additions, contrarian ideas and two missing lenses |
| Literature scout | [literature.md](round0/literature.md): found no published statistic-based feature or interaction that beats a sharp close out of sample (an absence of evidence, not evidence of absence); the top literature idea is the pair's serve dominance |
| Data cartographer, then feasibility auditor | the [inventory](round0/inventory.md) (per-player values for 48 of 51 inputs, a tried-before register); built 76 primary columns; ruled on data and leaks |
| Configuration critic | made the screen a coefficient test, the discovery and replication windows one joint analysis, and the final test a disjoint-seed encompassing test (power, multiplicity, clustering) |
| Synthesizer | merged the lists by algebra only ([master_list.md](master_list.md)) |
| Mathematical auditor | ruled on every idea (hard kills only), formed 22 blocks, wrote the [family](round2/hypothesis_family.md) |
| Three EDA analysts | built the 34 hypotheses result-free, with leak probes and pre-declared gates ([builds](round2/builds/)) |
| Harness verifier | found 14 bugs before the screen ran ([harness_verification.md](meta/harness_verification.md)) |
| Red team | re-implemented the finalist and attacked it ([red_team.md](meta/red_team.md)) |
| Final-test verifier | checked the one-shot test's code on synthetic outcomes ([final_test_verification.md](meta/final_test_verification.md)) |
| Meta-auditor | three checkpoints on process ([checkpoint 1](meta/checkpoint_1.md), [checkpoint 2](meta/checkpoint_2.md), [checkpoint 3](meta/checkpoint_3.md)); kept the [look ledger](meta/look_ledger.md) |

**Discipline.**
* No candidate was related to a match result before the freeze (M1).
* The screen ran once, by hash, over the table, every builder file and every input file.
* Six known-null placebos ran through the same pipeline; **none passed**.
* 2025–2026 was opened once, after a hashed pre-registration ([preregistration.md](preregistration.md)).

## The screen (2014–2024, run once; [round3/screen.md](round3/screen.md))

Each member was tested against the current best's out-of-sample log-odds η, with free slopes per tour × season, a cubic, the member type's marginality controls and clustering by four-week blocks and shared players. Discovery was 2014–2021, replication 2022–2024, combined in one joint analysis, then weighted Holm (claims) and weighted BH (the bundle).

| Member | z₁ | z₂ | joint z | Holm | BH q | Reading |
|---|---|---|---|---|---|---|
| **B-INJ** rust after a break (I-043 + I-044 + I-045) | +3.51 | +1.93 | **+3.99** | **0.002** | **0.002** | the only claim |
| B-VENUE venue pace × serve | +2.13 | +1.32 | +2.50 | 0.29 | 0.15 | not eligible (eligible on the price lens: q 0.075) |
| B-OVERREACT over-reaction to recent results | +1.64 | +1.38 | +2.13 | 0.77 | 0.23 | not eligible |
| B11 on-site rhythm | +1.35 | +1.54 | +1.97 | 1 | 0.23 | not eligible; its signal is the on-site match count, a main effect |
| H-S2 TabPFN with both players' levels | +1.37 | +1.05 | +1.73 | 0.94 | 0.23 | not eligible |
| I-008 the composed serve-point profile (weight 2) | +1.07 | −0.41 | +0.67 | 1 | 1 | does not replicate |
| B-LEVER serve-dominance leverage (Wald, 3 df) | – | – | p 0.21 | 1 | 1 | null |

**The other 27 are not eligible.**
* 21 single-coefficient members have a joint |z| below 1.96, and the four Wald blocks have joint p above 0.3.
* B-MOTIV reaches +2.27 but fails replication (z₂ +0.49).
* I-084 points against its declared direction (−2.99).

**What carries B-INJ** (exploratory, after the batch) is its member I-043, rust: joint z +4.05, out-of-sample gains +0.25 (2014–2021) and +0.09 (2022–2024) mLL. These are point estimates; the exploratory script computed no intervals. Return-from-injury × reputation (I-044) and within-event serve decay (I-045) are weak.

## From the screen to the test (M2, by rules fixed before the screen)

1. **The column arm and the capture rule.** B-INJ received a TabPFN arm (the 58 inputs plus its three columns, 2016–2024).
   * It was not harmful: +0.044 [−0.157, +0.245] mLL, calibrated, 2020–2024, a tie.
   * But TabPFN used only 39% of the screen's term (capture slope 0.39 below 0.5), so B-INJ was deployed as a **nudge**: logit P_F = s_tour·η_B + b·x, fitted walk-forward on the model's out-of-sample forecasts.
2. **The red team.** B-INJ passed with caveats. The registered "longer than the field's norm" condition almost never binds (it blocks 7 of 106,296 returns). So the claim is rust after any break of six weeks or more, not "hidden impairment" or an "unplanned layoff".
3. **The pre-registration.** It was hashed after a calibration control B₁₄ was added (checkpoint 2). B₁₄ separates B-INJ's gain from the change of calibration window.

## The final test (2025–2026, once; `data/studies/feature_interactions/final/final_results.json`)

8,520 matches (4,394 men's, 4,126 women's), the frozen inputs. Gains in mLL; each row's direction is stated.

| Endpoint | Result | Reading |
|---|---|---|
| **Primary**: the bundle's encompassing coefficient b, disjoint seeds (positive = the bundle adds information) | **−0.21 [−1.35, +0.93]**, p 0.71 | **tie: not confirmed** |
| The same b by subset (pre-registered secondary 1) | men −0.33 [−2.04, +1.37]; women −0.09 [−1.62, +1.44]; 2025 −0.04 [−1.54, +1.47] (11 df); 2026 −0.49 [−2.63, +1.66] (8 df); fault-clean −0.04 [−1.19, +1.12] | all ties |
| **Effect size**: F against B₁₄, B-INJ's part (positive = F better) | **−0.27 [−0.64, +0.10]** | tie |
| B₁₄ against B, the calibration window's part (positive = B₁₄ better) | +0.06 [−0.07, +0.20]; by season 2025 +0.18 [+0.0002, +0.35], 2026 −0.11 [−0.30, +0.08] | tie overall; 2025 B₁₄ better by a hair (descriptive) |
| F against B, the deployment gain (positive = F better) | −0.21 [−0.61, +0.20] | tie |
| Men / women, F against B₁₄ (positive = F better) | −0.31 [−0.88, +0.26] / −0.22 [−0.64, +0.19] | ties |
| 2025 / 2026, F against B₁₄ (positive = F better) | −0.23 [−0.78, +0.33] / −0.33 [−0.93, +0.26] | ties |
| Fault-clean matches (8,145), F against B₁₄ (positive = F better) | −0.21 [−0.59, +0.18] | tie |
| Column arm (B-INJ inside TabPFN) against B (positive = the arm better) | −0.01 [−0.23, +0.21] | tie |
| At Polymarket's price 24 hours out (2,648): F against B, both fed that price (positive = F better) | +0.06 [−0.59, +0.70]; clean openers (1,067) +0.22 [−1.01, +1.46] | ties |
| The price's move: the slope of logit P(30 min) − logit P(24 h) on b·x (positive = the price moved in the nudge's direction) | all 2,648: +0.01 [−0.59, +0.61]; clean openers (1,067): **+0.62 [+0.03, +1.21]** | all: tie; clean openers: interval above 0 (descriptive) |

**Reading (the pre-registered table).**
* The primary spans 0, so the bundle is **not confirmed**. Gains below about 0.57 mLL remain possible.
* **Expected against observed.** The expected gain was 0.12–0.16 mLL; the observed −0.27 is about two standard errors below it, an unlucky draw or a smaller or absent effect in these seasons.
* **The clean-opener move is one of about 30 descriptive estimates.** Two have intervals that exclude 0 (this move, and B₁₄ against B in 2025), about what chance alone gives. The direct comparison at that price ties: F against B, both fed the 24-hour price, +0.22 [−1.01, +1.46] on the clean openers and +0.06 [−0.59, +0.70] on all 2,648.
* **Inferred.** B-INJ stays a 2014–2024 finding (z +3.99, both windows) that was not confirmed on 2025–2026; the effect size leaned worse. It is not a deployable improvement now.

## Side findings (descriptive or exploratory)

* **The current best against Pinnacle.** It beats the calibrated Pinnacle close on 2022–2024 by +1.06 [+0.27, +1.85] mLL, and the calibrated average by +1.19 [+0.47, +1.91] (2014–2021: +0.21 [−0.37, +0.78] and +0.28 [−0.28, +0.83], ties). Pinnacle's own deviation from the average still adds beyond the model (z +2.98). Inferred: an artefact of the average close that a sharp venue would not leave.
* **Against declared directions.**
  * Pair prominence × η (I-084) has z −2.99, one of 34 one-sided tests; a reversal was never a registered hypothesis. Obscurity × η (I-036) has z −1.65.
  * Inferred: the forecast may be too steep for pairs of high combined Elo.
  * Not claimable under the one-sided rule; a lead for a new study.
* **The known nulls.**
  * None passed.
  * The decided TTT's log-odds carries a negative coefficient beyond the model (z −2.53, p 0.011). One of six known nulls at p 0.011 has about a 6.6% chance under the global null.
  * Inferred: possibly a sign the model over-weights the rating it already holds.
* **INFO-1's false premise.** The idea that the leak-proof clock leaves a player's previous-day result out of the IOS was false: the IOS already folds in each player's own uncounted match. That was found result-free, and the descriptive column was null.
* **Where serve dominance is priced.** At matched strength, the close applies 43% (men) and 34% (women) of the iid model's dominance scaling, and the current best 36% (men). The damped truth, estimated from the day-noise split, is about 39% (men, best of three). The price is about right (inferred).

## What it means, and what next (inferred; suggestions)

* **No interaction passed the gates.**
  * The screen's 80% MDE was about 0.12–0.19 mLL per member, depending on its weight, test and trait. Effects of that size would probably have been found; smaller ones were beyond its reach.
  * B-VENUE (joint z +2.50) and B-OVERREACT (+2.13) remain unresolved.
  * TabPFN's near-additive adjustment is consistent with little interaction signal left beyond its 58 inputs; it does not prove it.
* **Process suspects, per the owner's premise:**
  1. **The benchmark.** Every test here is at the close. The clean-opener move toward the nudge (+0.62) is one descriptive estimate among about 30, uncorrected for multiplicity. It is a hypothesis for a pre-registered test against the 24-hour price, not evidence. It is consistent with the early price lacking the calendar's rust. That test needs more price history than 2025–2026 holds.
  2. **Power.** The final test could only see gains of about 0.57 mLL. A prospective continuation of the same pre-registered test (critique C1), adding matches after 7 October 2026, would reach about 0.25 mLL by the end of 2027 (the critique's estimate, C1).
  3. **The opposite-direction leads.** Prominence and obscurity × η, and the TTT's negative coefficient, point at the model's calibration by pair strength: one pre-registered hypothesis for a new study. B-VENUE, eligible on the price lens, is another.
* **Recommended to the owner:** keep the current best unchanged. B-INJ is not confirmed and should not be deployed. Every member here stays available for a prospective test on matches after 7 October 2026.

## Limitations

* **2014–2024 was seen by earlier studies** for other features; the family's members were new constructions. Only B-INJ was opened on 2025–2026, and a near relative (the predictive frontier's recovery context) had been scored there before and tied.
* **The screen's own gains for B-INJ were ties.** The 2022–2024 forward gain was +0.02 mLL.
* **Selection.** The nudge's b was fitted on the same 2014–2024 data that selected B-INJ. Tweedie's formula shrank its z from 3.99 to 3.41, about 15%.
* **The construction.**
  * As built, B-INJ is not its registered mechanism: the field-norm condition almost never binds.
  * I-044 carries about 17% of the test's leverage and is null on its own.
  * I-045 is exposed to the first-serve fault.
  * 101 rows of 2026 lack I-043 (missing ages); they count as 0.
* **The price lens** was reported, not gated.
* **Code changed after the freeze.** Two changes are logged in ledger row 34: `tabpfn_tests`' one-tour fix, and the guard that keeps a failed subset from losing the rest, made after the verifier's last check. Neither touches the primary.
* **The test seasons.**
  * 2026 is partial, ending in early October.
  * The primary has 21 four-week blocks, so t on 20 df.
  * The base's 2025–2026 seeds 0–2 are the rating race's fits, which that study had already scored. Only B-INJ and its column arm were new there.
* **The power.** The final test's MDE was about 0.57 mLL.
* **The data.** The final test used the frozen pre-rebuild inputs: the Tennis My Life men's Slam first-serve fault is not repaired. It touches the base and the bundle alike, and the fault-clean subset agrees.
* **Closing prices** are archived average closes, not executable bet-time prices; a log-loss gain is not a betting return.
* **The local TabPFN** is the open checkpoint, not the API's Plus or Thinking; no paid call was made.

## Files

| What | Where |
|---|---|
| The brief, the team, the plan (adopted amendments, the M1 freeze, M2's rules and outcome) | [brief.md](brief.md), [team.md](team.md), [plan.md](plan.md) |
| Round 0: inventory, literature, four idea lists, the critique | [round0/](round0/) |
| Rounds 1–2: master list, audits, rebuttals, rulings, the family, build notes | [master_list.md](master_list.md), [round1/](round1/), [round2/](round2/) |
| The screen | [round3/screen.md](round3/screen.md); `data/studies/feature_interactions/hypotheses/` |
| The final test | [preregistration.md](preregistration.md); `data/studies/feature_interactions/final/` |
| Meta: the look ledger, the verifications, the red team, the checkpoints | [meta/](meta/) |
| Code | `src/eda/feature_interactions/`: `screen.py`, `screen_batch.py`, `panel.py`, `history.py`, `features/`, `local_fits.py`, `tabpfn_tests.py`, `g5_build.py`, `g5_score.py`, `shrinkage.py`, `final_test.py` |
| Tests | `test/feature_interactions/` (32 tests) |
