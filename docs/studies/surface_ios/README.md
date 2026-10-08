# Surface IOS: the long-memory profile, built per surface

6 October 2026 · Research evidence, not a production, model or betting decision.

> **Owner decision, 6 Oct 2026: keep the surface profile in the model** ([decision record](../../decisions/2026-10-06-surface-ios-profile.md)). The reasons: it is neutral with the closing odds, it helps without them (men), and bets may be placed before the close. Open: men only, since no women's test shows a benefit.

**The owner's request (6 Oct 2026).** Explore and audit one idea for improving the best 2026 model: build its long-memory IOS profile (each player's opponent-adjusted serve and return strength, statistic by statistic) separately for each surface, with shrinkage towards the player's all-surface value. Derive from our own evidence how to represent it; have an independent agent audit the plan; lock it; then test it with TabPFN-3.5 (non-thinking) in five expanding windows, one test season each, 2022–2026, with and without the change.

**Keys.** Match results are milli-log-loss per match: **positive = the named arm has the lower log loss (better)**; a 95% interval that spans 0 is a **tie**. Statistic forecasts are milli-log-loss per unit of the statistic (per serve point, per service game, …), higher is better. **Observed** = computed here; **inferred** = reasoning; **proposal** = not decided.

**Documents.** The evidence, the strategy and the locked plan, written before the test: [strategy.md](strategy.md). The independent audit, verbatim: [audit.md](audit.md).

## In short

* **Observed. The idea is right about tennis.** Built per surface, with IOS's opponent adjustment and heavy shrinkage towards each player's all-surface value, the profile forecasts every serve and return statistic better, on both tours, out of sample. Men's holds and breaks gain +0.40 [+0.34, +0.46] milli per service game in 2019–2026, and +0.88 on grass. Surface specialisation is durable: a man's clay return deviation in one three-year period correlates 0.40–0.49 with the next.
* **Observed. It does not improve the model given the closing odds.** Primary test, decided before the test seasons were scored: the surface profile (R1) against today's inputs, local TabPFN-3.5, four seeds, recalibrated, both tours, 2022–2026, 23,819 matches: **+0.01 [−0.10, +0.13] milli-log-loss, a tie.**
  * Men +0.07 [−0.11, +0.26]; women −0.05 [−0.21, +0.11]; every season a tie.
  * The two other representations (eight surface deviations; one net-shift column) tie too. The one-column arm is indistinguishable from its own shuffled placebo: −0.00 [−0.09, +0.09].
  * The test is tighter than planned: it rules out a gain larger than about +0.13, a tenth of the model's edge over the price.
* **Observed. Without the odds it helps the men's model.** Surface profile against base with no odds column, 2022–2026:
  * men **+0.83 [+0.39, +1.27]** (+0.98 in 2019–2021);
  * women −0.33 [−0.84, +0.18], a tie;
  * both tours, the pre-declared primary, +0.27 [−0.03, +0.58], a tie.
* **Inferred. The surface information is real, but the closing price already has it.** A linear check found the same before the test. Process suspects, per the owner's premise, are listed under "What next".
* **Observed. A free improvement found by the audit.** The local TabPFN-3.5 with one calibration slope per tour (fitted on its own 2019–2021 forecasts) beats the recalibrated closing price by +1.60 [+0.84, +2.36] for men in 2022–2026. That is level with the paid thinking fit (head to head +0.07 [−0.35, +0.48], a tie).

## The question, and what changed on the way

The best 2026 model is TabPFN-3.5 given the closing odds plus 53 pre-match inputs. Its 22 IOS inputs, the group it leans on most, give each player one offence and one defence rating per statistic, pooled over surfaces (each match is compared with the tour's average on its surface, but the player's level is the same everywhere). The suggestion: make that profile surface-specific, prioritising the return side.

Two things changed while the work ran, and both are recorded where they matter:

* **The model.** The owner asked for TabPFN-3.5 Plus (the API's non-thinking model).
  * Later the same day another session relayed the owner's concern about API costs ("I think they are using the online version at the moment and costing me money"). It also relayed that the free offline TabPFN-3.5 (the open checkpoint `tabpfn-v3.5-20260909`, on this machine's GPU) could be used instead.
  * No rule was recorded. This study treated paid calls as the owner's to approve and made none; it fetched only free server quotes, before the relay.
  * Every fit here is local. Whether the local open model equals the hosted Plus model is unknown.
* **A validation phase.** Local fits are free, so the representation was chosen on 2019–2021 (three more expanding windows) before any 2022–2026 result of a surface arm was seen.

## What was built (observed)

* **A surface IOS** (`src/eda/surface_ios/ios_surface.py`): today's leak-proof IOS with a surface deviation for every player, y = O_server + E_server,surface − D_returner − F_returner,surface, a second ridge penalty shrinking the deviations towards zero (the player's all-surface value), solved day by day on the match clock. With the deviations switched off it reproduces today's inputs exactly.
* **Checks**: 14 tests (`test/surface_ios/`); the match-timing study's real-date leak probe, passed at all four cut days (none of 13,758–31,163 earlier matches moved); today's 21 IOS inputs rebuilt to within 5 × 10⁻¹⁵.
* **Constants** tuned on 2013–2018 only (Stage B's protocol), 208 runs: the surface penalty, the memory, and serve-and-return against return-only deviations.

## The evidence before the test (observed; [strategy.md](strategy.md), section 3)

1. **Surface terms forecast every statistic better**, on both tours, in tuning and out of sample. Men's holds and breaks: +0.45 [+0.35, +0.55] milli per service game in 2013–2018, +0.40 [+0.34, +0.46] in 2019–2026 (+0.60 on the main tour, +0.88 on grass); every one of the 16 tour × statistic pairs gains. The gain is 1–3% of IOS's own skill, mostly on clay and grass.
2. **Heavy shrinkage is right** (a penalty 10–30 times the all-surface one); surface-only ratings are worse than pooling. **A longer memory does not help** in the form tested.
3. **Surface specialisation is durable.** For men on clay, a player's deviation in one three-year period correlates 0.40–0.49 with the next for return points won, breaks and serve points won, and its stable part is two-thirds to all of the stable spread between players.
4. **Both sides matter.** The suggestion's "serve stats barely deviate" holds for aces and first serves in, not for serve points won or holds; return-only deviations keep only 40–60% of the gain in the two-sided statistics.
5. **Linearly, the closing price already has it.** Given the price, surface deviations add nothing out of sample (2013–2018), as the market-anchoring study found for raw surface statistics.

## The strategy, the audit, the plan (observed; [strategy.md](strategy.md), sections 4–7)

* **Candidates.** R1 `sprof`: the same 54 inputs, the 21 IOS profile inputs computed per surface (matchup products become surface matchups). R2 `sdev`: the 54 inputs plus eight serve and return surface deviations for the four statistics the suggestion prioritised.
* **The audit** (an independent Opus 5.5 agent, blind to validation results) found no bug and no leak, but found the test not ready: the local model is over-confident (one slope per tour fixes it, see the side finding below), the intervals ignored the seeds' variance, power was unstated, and R2 mixes two models. It proposed P1 `snet1`: a single column, the surface model's net change in A's point advantage, with a permuted placebo.
* **Locked plan.** Recalibrated forecasts (each arm's slope per tour fitted on its 2019–2021 forecasts) are primary; intervals include the seeds' variance; the primary arm is chosen on recalibrated, cross-fitted validation gains. **R1 was chosen** (+0.15 [−0.08, +0.38] over base in 2019–2021, a tie; P1 +0.10, its placebo +0.06, R2 +0.03). **Pre-registered power: about +0.26 milli-log-loss** (80%) on 2022–2026; a tie was the expected outcome.

## Results, 2022–2026 (observed; `results.csv`, `results.json`, `residual_check.json`)

Local TabPFN-3.5, four seeds per arm and window, expanding windows from 2013; every forecast recalibrated per tour on its own 2019–2021 forecasts. Gains in milli-log-loss, **positive = the named arm has the lower log loss (better)**. Arm-against-base intervals include the seeds' variance.

**The primary comparison: R1 (surface profile) against base.**

| | Both tours | Men | Women |
|---|---|---|---|
| 2022–2026 | **+0.01 [−0.10, +0.13] tie** | +0.07 [−0.11, +0.26] tie | −0.05 [−0.21, +0.11] tie |
| 2022 | +0.00 [−0.30, +0.31] tie | +0.23 [−0.31, +0.76] tie | −0.25 [−0.59, +0.10] tie |
| 2023 | +0.07 [−0.29, +0.42] tie | +0.06 [−0.50, +0.61] tie | +0.08 [−0.29, +0.45] tie |
| 2024 | +0.05 [−0.10, +0.20] tie | +0.27 [−0.02, +0.55] tie | −0.19 [−0.48, +0.10] tie |
| 2025 | −0.14 [−0.43, +0.16] tie | −0.36 [−0.78, +0.06] tie | +0.10 [−0.26, +0.46] tie |
| 2026 | +0.12 [−0.53, +0.76] tie | +0.24 [−0.60, +1.07] tie | −0.00 [−0.58, +0.57] tie |
| 2022–2024 | +0.04 [−0.07, +0.15] tie | +0.18 [−0.02, +0.38] tie | −0.12 [−0.30, +0.07] tie |
| 2025–2026 | −0.03 [−0.30, +0.23] tie | −0.12 [−0.50, +0.26] tie | +0.06 [−0.21, +0.33] tie |

Raw (not recalibrated) forecasts give +0.06 [−0.09, +0.22], a tie.

**The other arms against base, 2022–2026, both tours** (all ties):

| Arm | Gain |
|---|---|
| R2: eight surface deviations | −0.06 [−0.18, +0.07] |
| P1: one net-shift column | +0.03 [−0.06, +0.11] |
| P1's placebo: the same column shuffled within tour × surface × season | +0.03 [−0.04, +0.10] |
| P1 against its placebo | −0.00 [−0.09, +0.09] |

**Against the closing price** (recalibrated on each window's training seasons; positive = better than the price), 2022–2026:

| Arm | Both tours | Men | Women |
|---|---|---|---|
| base | +1.20 [+0.51, +1.89] | +1.60 [+0.84, +2.36] | +0.76 [−0.35, +1.87] tie |
| R1 surface profile | +1.21 [+0.52, +1.90] | +1.67 [+0.89, +2.45] | +0.71 [−0.38, +1.81] tie |
| R2 deviations | +1.14 [+0.47, +1.81] | +1.60 [+0.87, +2.33] | +0.64 [−0.45, +1.74] tie |
| P1 net shift | +1.22 [+0.53, +1.92] | +1.67 [+0.89, +2.46] | +0.74 [−0.36, +1.84] tie |

**Pre-declared subgroups, R1 against base, both tours** (block intervals; several were looked at, so these are directions):

| Subgroup | 2019–2021 (validation) | 2022–2026 (test) |
|---|---|---|
| Early in the surface season | +0.42 [+0.02, +0.81] | +0.05 [−0.27, +0.36] tie |
| Later in the season | +0.06 [−0.11, +0.22] | +0.00 [−0.10, +0.11] tie |
| Hard | +0.20 [+0.00, +0.39] | +0.03 [−0.07, +0.14] tie |
| Clay | −0.14 [−0.46, +0.19] | −0.04 [−0.22, +0.14] tie |
| Grass | +0.67 [−0.16, +1.51] | +0.04 [−0.65, +0.73] tie |

The validation's early-season lead did not replicate.

**The linear residual check** (the audit's): the recalibrated base plus the net shift, fitted on 2019–2021, scored on 2022–2026: −0.09 [−0.20, +0.01] (both tours), a tie. The net shift's 2019–2021 coefficient is small and of opposite sign by tour (z +0.55 men, −0.82 women).

## Without the odds (observed; added after the test, pre-declared in [strategy.md](strategy.md) section 8)

The owner's question after the result: if the odds were not in the model, would the surface profile add to it? It was tested with the same design, recalibration and seed-variance intervals, on the same matches, comparing two arms:

* today's 53 sporting inputs without the closing odds' column (`base_noodds`);
* the same 53 with the surface profile, R1 (`sprof_noodds`).

Gain of the surface profile over base, milli-log-loss, positive = surface better:

| Without the odds | Men | Women | Both tours (primary) |
|---|---|---|---|
| 2022–2026 | **+0.83 [+0.39, +1.27] better** | −0.33 [−0.84, +0.18] tie | +0.27 [−0.03, +0.58] tie |
| 2019–2021 (validation) | +0.98 [+0.42, +1.54] better | −0.09 [−0.63, +0.46] tie | +0.47 [+0.05, +0.89] better |
| 2022 / 2023 / 2024 / 2025 / 2026 | +0.75 / **+1.01** / **+1.48** / −0.10 / +1.07 | **−1.12** / −0.13 / **−0.96** / +0.78 / −0.26 | −0.14 / +0.47 / +0.31 / +0.33 / +0.42 |
| 2022–2024 / 2025–2026 | **+1.08** / +0.37 | **−0.73** / +0.36 | +0.22 / +0.37 |

Bold marks an interval that clears zero. Raw (not recalibrated) forecasts give larger figures: men +1.24 [+0.69, +1.79], both tours +0.51 [+0.15, +0.87].

* **Men: yes.** Without the odds the surface profile adds +0.8 to +1.0 milli-log-loss in both the validation and the test seasons, and is positive in four of five test seasons. The gain shows on hard courts (+0.95 [+0.45, +1.46], block interval) and clay (+0.91 [+0.10, +1.71]). Hard courts gain through the level correction: a clay specialist is no longer rated up on hard courts. It also shows early in the surface season (+1.28 [+0.26, +2.29]). It closes about a tenth of the men's gap to the market: −8.47 → −7.64 against the recalibrated close.
* **Women: no.** A tie overall, and worse in 2022 and 2024. *Inferred:* the women's surface deviations rest on a shorter box-score history (hold box scores begin in 2015). Their statistic-forecast gains were half the men's (section 3.1 of strategy.md), and their persistence was noisier.
* **Both tours together**, the pre-declared primary, is a tie (+0.27, its interval just reaching zero).
* **So the information is real; the price already has it.** With the odds in the model, the men's gain disappears (+0.07, a tie). The sibling study found the same for surface Elo: men +2.74 [+1.23, +4.25] without the odds, a tie with them.

## One model, or one per court type? (observed; added after the owner's decision, pre-declared in [strategy.md](strategy.md) section 9)

The owner asked whether the model needs to be split by court type. The comparison:

* **One model:** the decided model (the surface profile, with the odds) for all surfaces, surface being one of its inputs.
* **Three models:** the same model per court type (hard with the rare carpet, clay, grass), each trained only on its surface's matches.

Same seasons, seeds and recalibration as before. Positive = separate models better:

| | Both tours | Men | Women |
|---|---|---|---|
| 2022–2026 | −0.28 [−0.77, +0.21] tie | −0.17 [−0.93, +0.60] tie | −0.40 [−1.07, +0.26] tie |
| 2019–2021 | −0.24 [−0.74, +0.27] tie | −0.18 tie | −0.30 tie |
| Grass, 2022–2026 | −1.16 [−4.83, +2.50] tie | +1.22 tie | **−3.58 [−7.02, −0.14] worse** |
| Clay / hard, 2022–2026 | −0.41 / −0.02, ties | | |
| Early in the surface season | −1.26 [−2.53, +0.01] tie, nearly worse | | |
| Against the recalibrated close | separate +0.93 [−0.00, +1.86], one model +1.21 [+0.52, +1.90] | | |

The grass, clay, hard and early-season rows use block intervals.

* **One model distinguishes court types at least as well.** It knows the surface from three things: its surface column, the surface-specific profile values (a grass match carries grass ratings), and surface Elo with the surface-familiarity flag.
* **Splitting costs data where data is scarce.** A grass-only model learns from about 4,400 matches before 2022, against 39,900 for the pooled model. It does worst exactly there: grass, and early in a surface season. Its forecasts are also about twice as noisy from seed to seed.

## What it means, and what next

* **Inferred.** Surface specialisation is a real, durable trait of players' serve and return games, and IOS can measure it. But the closing price already reflects it: given the price, neither a linear nudge (2013–2018, and 2022–2026) nor TabPFN finds anything, to within about a tenth of a milli-log-loss. This is the same answer the market-anchoring study reached with cruder statistics, now with the measurement done properly. A sibling study the same day reached it independently for surface Elo ([Elo by surface: give the model the pieces](../surface_elo_pieces/README.md): with the odds a tie, −0.01 [−0.24, +0.21]; without them a clear gain).
* **Observed there.** That study first found the paid TabPFN-3.5 Plus trailing the Thinking fit and not significantly beating the price (+0.70, a tie). The local model here behaved the same way until one slope per tour was fitted on earlier seasons, after which it matched Thinking.
  * That study then recalibrated its Plus forecasts the same way (`src/eda/surface_elo_pieces/recalibrated.py`, `recalibrated.csv`; slopes men 0.885, women 0.96).
  * Plus against Thinking became +0.12 [−0.24, +0.49], a tie (men +0.09, women +0.16).
  * Against the close it scores +1.34 [+0.72, +1.96] for both tours and +1.62 [+0.81, +2.43] for men, where Thinking scores +1.22.
  * So "Plus trails Thinking" was calibration, for the paid non-thinking model as for the local one.
* **Process suspects** (the owner's premise: a null against the close is a process flaw to hunt):
  1. **The benchmark is the closing price.** Surface knowledge may be priced only by the close. Test the same inputs against Polymarket's price hours before the start (the market-anchoring study's suggestion 3), where it could still be ahead of the market.
  2. **Thinner markets.** Challenger, WTA 125 and ITF matches, where the Polymarket study found the most accounts beating the close. The model covers the main tour only.
  3. **A stronger surface signal** (strategy.md 7.4): a long-memory deviation estimated from pre-match residuals, a penalty per surface, serve-only deviations for the serve-only statistics, indoor hard as its own surface. The audit's tension says a better estimator might pass more of the stable trait, though section 3.2 suggests the gain would be small.
  4. **Thinking.** One paid TabPFN-3.5-Thinking fit of R1, only if the owner approves the cost. The local model plus a slope already matches thinking on the base inputs, so this is low priority.
* **Recommended now:** whatever the base model becomes, recalibrate it per tour on earlier seasons, refitting the slope each season on all earlier out-of-sample seasons. The women's over-confidence grows over time. For the local TabPFN-3.5 this is worth about +0.8 milli-log-loss on 2022–2026 (both tours: +0.53 raw → +1.30 against the close), more than any input tested here.

## Side finding: the free local model plus one slope matches the paid thinking fit (observed)

On the best model's own 23,819 test matches of 2022–2026, the local TabPFN-3.5 (four seeds, expanding windows) ties the recalibrated closing price as it comes: +0.53 [−0.35, +1.42] (both tours), +0.85 [−0.27, +1.96] (men). It is over-confident: its deviations from the price are 59% larger than the paid thinking fit's. One slope per tour on its log-odds, fitted on its own 2019–2021 forecasts (men 0.886, women 0.964), gives +1.20 [+0.51, +1.89] (both tours) and **+1.60 [+0.84, +2.36] (men)**. Against the same price the paid TabPFN-3.5-Thinking refit scores +1.19 [+0.57, +1.81] (both) and +1.53 [+0.78, +2.29] (men). Head to head, the recalibrated local model against the paid fit is +0.01 [−0.37, +0.39] (both tours; men +0.07 [−0.35, +0.48], women −0.05 [−0.65, +0.55]): a tie. Found by the audit, reproduced here. *Inferred:* most of what thinking added over the local model is calibration, which a slope fitted on earlier seasons recovers for free. (The price here is recalibrated per window on each window's training seasons, so its numbers differ by a few hundredths from the leak-proof study's single recalibration.)

**Added after the study, the same evening.**

* **Replicated on an independent fit.** Another session applied the same slopes to its own single-seed local fit, trained once on 2013–2021 (`data/studies/tabpfn_local/leakproof/`). Against the close: men +1.48 [+0.78, +2.17], both tours +1.10 [+0.44, +1.77]. Against the paid thinking fit: men −0.04, women −0.11, both −0.07, all ties.
* **The women's calibration drifts; walk-forward slopes track it.** That session noted its women's forecasts are more over-confident in 2022–2026 than the 2019–2021 slope corrects. The same holds here: fitted in-sample on 2022–2026, for diagnosis only, the slopes are men 0.905 and women 0.893.
* **Refitting each season's slope on all earlier out-of-sample seasons** (2019 up to the season before) gives:
  * the slopes: men 0.886–0.909 and steady; women falling from 0.964 to 0.912;
  * against the close, both tours: **+1.30 [+0.65, +1.94]** (men +1.57, women +1.00 [−0.01, +2.00]);
  * against the fixed 2019–2021 slope: +0.10 [−0.03, +0.23], a tie leaning walk-forward.
* **The primary result does not depend on the recalibration.** Under walk-forward slopes, R1 against base is +0.02 [−0.10, +0.13], still a tie.

## Limitations

* **Local, not the API's Plus model**, and not thinking. The owner's concern about API costs moved every fit to the local open checkpoint. The paid thinking fit was not repeated.
* **The test's power** is about +0.26 milli-log-loss (80%) for the primary arm; smaller effects read as ties.
* **2019–2026 have been inspected by earlier studies** (and 2019–2021 here, to choose the arm), so 2022–2026 is a clean test of this arm, not an untouched holdout for the project.
* **Closing prices** are archived average closing quotes, not executable bet-time prices; a log-loss gain is not a betting return.
* **The construction** was not pushed further (a 100× penalty, a penalty per surface, serve-only deviations, a long-memory deviation, indoor hard as a surface): deferred as follow-ups (strategy.md, 7.4).
* **Data**: women's hold box scores are absent before 2015 and the men's 2018 season has no odds; lower-level box scores more than double in 2025 (hence the 2022–2024 / 2025–2026 split).

## Files and how to run

Code in `src/eda/surface_ios/`, tests in `test/surface_ios/`, outputs in `data/studies/surface_ios/`. Run with `./python.sh` unless noted:

| Step | Script | Writes |
|---|---|---|
| Solver inputs (1 min) | `build_cache.py` | `cache/` |
| Solver checks | `verify_solver.py` | `verify_solver_*.json` |
| Tuning on 2013–2018 (about 2 h on 14 cores) | `tune.py`, then `tune.py --grid return` | `tuning/` |
| Tuning summary and choice | `summarise_tuning.py` | `tuning_summary.csv`, `tuning_choice.json` |
| Persistence | `persistence.py` | `persistence.csv`, `persistence.json` |
| Full-history runs and per-match inputs (about 30 min) | `build_features.py` | `full_runs/`, `surface_features.parquet`, `oos_scores.csv` |
| Real-date leak probe (about 20 min) | `probe.py` | `probe.json` |
| Subgroups | `subgroups.py` | `subgroups.parquet` |
| The model's frame, arms | `frames.py`, `arms.py` | `base_frame.parquet`, `arms/` |
| Diagnostics | `diagnostics.py` | `diagnostics.json`, `diagnostics_*.csv` |
| Uploads (fingerprinted) | `dispatch.py --prepare` | `uploads/` |
| Local TabPFN-3.5 fits (env `tennis-tabpfn-local`) | `./python_tabpfn_local.sh src/eda/surface_ios/run_local.py --phase validation`, then `--phase test` | `local/` |
| Scoring, primary arm | `score.py`, `choose_primary.py` | `results.csv`, `results.json`, `residual_check.json`, `test_predictions.parquet`, `primary.json` |
| Tests | `./python.sh -m pytest test/surface_ios` | 14 tests: solver and guard |

`guard.py` and `dispatch.py --run` are the paid-API path (one fit and one prediction per registered slot). They were not used. Ask the owner before any use: the owner has raised concern about API costs, and no rule is recorded yet.
