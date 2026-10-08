# Point sequences: momentum, streaks and in-match state

**Status: study, not a decision.** The owner's request of 6 October 2026:

> "Where did we leave off on rebuilding point by point data in a way to potentially generate new statistics for the best performing 3.5 tabpfn non thinking model? So, info about momentum and streaks. Building summary statistics of many types that currently dont exist as standalone measured stats in the other data. Explore creative new possibilities with that data and explore what has the most promise to explore either getting more data for it or combining it in novel ways with other statistics. Spawn a brainstorming agent, an auditor and converse back and forth between you before you settle on a conclusion."

**Units.**
* Scores are milli-log-loss (mLL) per match. In this report, **positive = the model (or the feature) is better** than the named benchmark.
* Intervals are 95%, over four-week blocks of tournament dates unless stated otherwise. An interval that spans 0 is a **tie**.

**Labels.** **Observed** = measured here. **Inferred** = a reading of measurements. **Suggestion** = a proposal.

**Holdout.** The concurrent [feature-interactions study](../feature_interactions/brief.md) keeps 2025–2026 closed until one final pre-registered test. This study adopts the same rule:
* outcome tests use discovery ≤ 2021 and replication 2022–2024;
* nothing here reads 2025–2026 outcomes.

## In short

* **Where we had left off.** No momentum or streak statistic had ever been built properly. The shot-level study's small "point sequence" family rested on thin per-player histories (5–58 games a year) and added nothing to the close. Three large point sources downloaded since had never fed any feature. The current best model has no point-sequence input.
* **What was built today.** One validated point-sequence table: 124,846 usable matches, 19 million points, from 13 sources. Each model-frame player has a median of 182 (men) and 77 (women) earlier sequenced matches, one to two orders of magnitude deeper than before.
* **How the conclusion was reached.**
  * A brainstorming agent proposed 31 ideas.
  * An independent auditor scored them, showed that pre-match tests against the close are badly under-powered for effects this size, and forced every idea through a cheap pre-registered gate first.
  * Four gates ran, plus a diagnostic of where the current edge lives.
  * After the owner narrowed the question to point-derived match statistics, a scoped round chose three more screens: serve-speed change, leverage, tempo. The one statistic that passed its trait gate (pressure pace) then got its residual screen.
* **Results** (*observed*; discovery ≤ 2021, replication 2022–2024; 2025–2026 untouched):
  * **Momentum and streaks are not stable player traits.** All ten statistics (hold after breaking, break back, point-to-point dependence, game dispersion, set swings; men and women) fail against pure-luck replays.
  * **The one men's lead, game-to-game serve dispersion,** fails an exact shuffle check at the registered depth: +0.055 [−0.004, +0.116], positive = more trait-like than random order. A weak trait shows only in players with 100+ matches: +0.163 [+0.086, +0.235].
  * **Finishing form carried into the next match is inconclusive.** Discovery ties; replication +0.0109 [+0.0003, +0.0216]. At most about 0.2 mLL if real.
  * **The women's "points share decides less than luck" anomaly was a data error:** mirrored box scores in three WTA events of 2021–2022.
  * **A physio treatment in a WTA player's previous match more than doubles her chance of retiring or withdrawing next time:** risk ratio 2.27 [1.69, 3.06] in replication. It moves the match result too little to resolve against the model or the close.
  * **The model's edge over the close is uniform** across previous-match states (later rounds, rest, long matches): +0.55 in 2015–2021, +1.39 in 2022–2024 (positive = model better).
  * **Big-point play is not a trait.** Return and serve leverage, weighted by how much each point mattered, tie on both tours against an exact within-set shuffle.
  * **Women's tempo is a reliable style that adds nothing.** Seconds between points, and the pace on pressure points, tie given the model and the close.
  * **Men's serve-speed change is the one replicated signal.** Replication +0.090 [+0.017, +0.162] log-odds per SD given the model (positive = a recent rise in speed wins more than the model says). Discovery, only 860 matches, ties, so it fails its registered rule.
* **Which point-to-point statistics have promise** (section 6):
  1. **Serve-speed change (men): the only one, and the one to get more data for.** It needs ATP non-Slam per-point speeds for 2025–2026, which exist only in encrypted files: the owner's decision. The novel combination is the speed family together (14-day change, within-match speed fade, box-score serve form), registered now and judged on the closed 2025–2026 holdout.
  2. **Finishing form carried into the next match:** inconclusive and small; no more data.
  3. **Men's within-set serve clustering:** a weak trait in deep histories, useful at most as a variance input for totals and handicaps.
  4. **Closed, no more data:** momentum, streaks, pressure, big-point leverage, tempo, within-match fade and the shot-style rates.

  Findings outside that question (data repairs that feed the model, the WTA medical-retirement hazard, in-play, venue) are summarised at the end of section 6.

## 1. Where we had left off

*Observed* (from the repo's reports; corrected by the auditor):

* **No study had built momentum or streak statistics proper.**
* **The closest work** is the [shot-level study](../shot_level/README.md) of 2 October. It drew on a point table from eight annotated sources (38,293 matches) and built:
  * a small "point sequence" family: hold right after breaking, break back right after being broken, hold when serving for the set;
  * three "under pressure" excesses;
  * serve points won right after a lost point.
* **Those statistics were mostly ability in disguise.**
  * Hold after break and break back correlate with hold and break strength, which the price knows (R² 0.22–0.25 with odds and Elo).
  * The pressure and after-a-lost-point statistics were at or near pure luck.
* **None of them added to the closing odds.**
* **Depth per player was the binding constraint, not coverage.**
  * Those features already existed on about 95% of test matches.
  * But they rested on a median of 5–58 relevant games per player per year.
  * So they tracked the players' true values with a squared correlation of only 0.15–0.35.
* **Earlier tests of related ideas** (all in the old harness):
  * clutch and big-point records, and late-match decline, are luck plus selection ([predictability diagnostic, Stage 2](../predictability_diagnostic/stage2.md); [UFC ideas, Stage C](../ufc_ideas/stageC.md));
  * the one clutch measure that persisted beyond luck, big points on return, failed as a pre-match feature, with the wrong sign.
  * Two signals were never followed up:
    * real winners improve late in matches more than independent points would allow;
    * the women's points share decides matches less than pure luck predicts.
* **Three large point sources downloaded since then had never fed any feature:**
  * the Kaggle SofaScore scrape `marcosjn2`: 48,479 tour-level matches, 2015–2025;
  * the WTA umpire logs: 2019–2026, millisecond times, medical and toilet breaks, violations;
  * SofaScore's tour-level points for 2025–2026.
* **The current best model has no point-sequence input.** It is the local, non-thinking TabPFN-3.5 with 58 inputs, after the owner's decisions of 6 October on the [offset Elo](../../decisions/2026-10-06-offset-elo.md) and the [surface IOS profile](../../decisions/2026-10-06-surface-ios-profile.md).

## 2. How the conclusion was reached: brainstormer and auditor

Two independent agents (Opus 5.5) debated for three rounds. The main session relayed between them, checked their claims on disk and ran the diagnostics they asked for. Every round is kept in [`data/studies/point_sequence/debate/`](../../../data/studies/point_sequence/debate/):

| Step | File | What it holds |
|---|---|---|
| Brief | `0_brief.md` | The main session's starting brief, with section 7 holding the auditor's verified corrections |
| Ideas, round 1 | `1_ideas_round1.md` | 31 ideas in 8 families, each with a definition, a luck baseline, coverage, mechanism, prior evidence, the cheapest test and an honest prior |
| Audit, round 1 | `2_audit_round1.md` | Errors in the brief, why every earlier sequence measure failed, power calculations, a failure-mode checklist, and a 100-point rubric with hard gates |
| Audit, round 2 | `3_audit_round2.md` | Every idea scored; no idea reached "build now" |
| Ideas, round 2 | `4_ideas_round2.md` | Rebuttals, a revised list and pre-registration sketches |
| Audit, round 3 | `5_audit_round3.md` | The final adjudicated build list |

**The auditor's power argument carried the debate.** *Inferred*, from its calculations:

* On the 2022–2024 replication window, a pre-match test against the close can detect about **1.2 mLL** (both tours, one input, 80% power).
* A noisy sequence statistic passes only ρ² of a player's true value. So a real edge in the underlying trait must be about **4.5–8 mLL per tour** to be seen.
* The best features this project has ever found against the close are 0.25–0.4.

Every pre-match idea therefore has to pass a gate on a sensitive target that is not the market first:
* next-match retirements;
* next-match serve points;
* the persistence of a trait against pure-luck replays.

**The brainstormer's main argument also carried.**
* Stable traits (style, clutch, sequence statistics) have never beaten the close.
* Every hint of an edge has been a recent **state**: the two-week form, the 14-day workload, and the men's recent serve-speed profile.
* So condition carried from the last match was ranked above new traits.

**Scores** from the auditor's rubric (out of 100; 75+ build now, 55–74 build after a cheap gate, 40–54 park, below 40 reject):

| Score | Ideas |
|---|---|
| 65 | WTA medical events |
| 63 | The 24 h → close move screen |
| 62 | The women's points-share anomaly |
| 61 | Conversion luck |
| 60 | Where the edge lives; finishing form carried into the next match; in-play reaction (after a firewall and time split) |
| 58 | Rest hours |
| 56 | Within-match fade |
| 53 | Depth re-test |
| 40–54, parked | Totals and handicaps, within-match volatility, leverage on return, in-play medical events, a point-level dynamic rating, coasting, intensity load, last-match drama, sharp wallets, set transitions, state-dependent serve, tempo, swing games |
| Below 40, rejected | Rally recovery, tilt, matchup products of pressure, the last match's in-play residual |

## 3. The unified point-sequence table

Built today (`src/eda/point_sequence/build.py`, about 2 minutes; 23 tests in `test/point_sequence/`). *Observed:*

* **Size.** 130,751 Stage 0 matches have one chosen sequence (19.17 million points). 124,846 are **usable**: replayed to completion, agreeing with the official score and with any second source.
* **Sources.** Eight sources are new to any feature:
  * Sackmann's point strings (79,003 matches);
  * marcosjn2 (48,479);
  * the WTA umpire log (27,116);
  * the WTA point-by-point feed;
  * SofaScore;
  * a corrected Australian Open feed.

  The eight sources of the shot-level study are reused.
* **Checks.**
  * Re-replaying the final table reproduces the official winner in all 123,282 complete usable matches.
  * Each player's serve points match the Stage 0 box score exactly in 96.5% of 102,732 matches; a `strict` flag marks those.
  * 39,082 matches are held by two or more sources: the official Slam feeds agree with Sackmann's Slam files in 99.95%, and SofaScore with marcosjn2 in 99.5%.
* **Depth, in the model's matches.** Each player has a median of 182 earlier usable sequences (men) and 77 (women), about 4,500 and 1,650 games. That is one to two orders of magnitude above the shot-level study.
* **Coverage of the model's own matches** (the usable sequence of the match itself):

| Season | Men | Women |
|---|---|---|
| 2013–2015 | 92–96% | 15–38% |
| 2016–2017 | 73–81% | 61–72% |
| 2019–2024 | 87–96% | 87–99% |
| 2025–2026 | 90–99% | 88–92% |

  Women's 2013–2015 history stays thin.

## 4. Where the current edge lives (diagnostic I1)

The question was whether the model's edge over the recalibrated close concentrates where the previous match matters: later rounds, short rest, a long or deciding previous match.

* **Forecasts.** The meta-stack's walk-forward forecasts of the 54-input model and the close, both recalibrated season by season on earlier seasons only (`src/eda/point_sequence/diag_edge_split.py`).
* **Contrasts.** Six fixed contrasts, Holm-adjusted.

*Observed:*

| Contrast (first group's gain minus second's; positive = the edge is larger in the first group) | Discovery 2015–2021 | Replication 2022–2024 |
|---|---|---|
| Overall gain of the model over the close (positive = model better) | **+0.55 [+0.05, +1.05]** | **+1.39 [+0.71, +2.06]** |
| Both players' first match at the event, minus both in a later round | −0.39 [−1.52, +0.79], tie | +0.92 [−0.51, +2.46], tie |
| Rest of more than 7 days, minus 1 day or less (the smaller of the two players' rests, in best-estimate match days) | +0.12 [−1.52, +1.74], tie | +2.15 [+0.13, +4.25], tie after Holm (p 0.20) |
| Neither previous match went the distance, minus at least one did | +0.58 [−0.53, +1.64], tie | +0.16 [−1.32, +1.61], tie |
| Early rounds, minus round of 16 and later | −0.74 [−1.64, +0.19], tie | +0.61 [−0.70, +2.04], tie |
| Grand Slams, minus other levels | +0.24 [−0.91, +1.35], tie | +1.71 [+0.15, +3.18], tie after Holm (p 0.22) |
| Men, minus women | +0.53 [−0.46, +1.53], tie | −0.80 [−2.02, +0.47], tie |

**A correction made during the session.** The first run measured rest from the timeline's `start` column, which is the **tournament's** start day, not the match day. The best-estimate match day is `obs`. The table uses `obs`. The rest contrast moved from +0.07 / +1.95 to the values shown, and nothing else changed. The same slip came from the main session's instructions. The medical-gate tester caught it, and the carry-over tester was told (see section 5 for what changed there).

**Inferred.** The edge is roughly uniform across the state players bring from their previous match.
* The "cold start" pattern seen first on 2022–2024 (larger edge when nobody has a fresh match) flips sign in discovery.
* The 2022–2024 rows for the first, second and fourth contrasts are **not blind**: those subsets were looked at on that window before discovery ran.
* So no subset points to a place where the market is weak and point-level state would pay. This removed the brainstormer's "information-age" decomposition from the build list.

## 5. The four gates

Each gate was pre-registered by its tester before any outcome was read. The registrations and deviation logs are `data/studies/point_sequence/{trait,med,carry}_prereg.md`. Windows: discovery ≤ 2021, replication 2022–2024.

### 5.1 Momentum and streak traits at full depth: all ten fail

**Question.** Do players differ, stably, in momentum and streakiness? This reads no match result. Tester: `trait_*.py`.

**Statistics.** Five per player-match, each an excess within the match, so the player's level that day cancels:
* **S1** hold right after breaking, minus the player's hold rate in other service games;
* **S2** break back right after being broken, minus the player's break rate in other return games;
* **S3** point-to-point dependence on serve: won after won minus won after lost, within games, by score state;
* **S4** game-to-game dispersion of serve points won;
* **S5** set-to-set swing.

**Benchmark.** Each statistic's split-half reliability across players (50 random splits) is compared with the same pipeline run on replays of every match in which each point is an independent draw at that day's serve rates. Such replays have no momentum by construction, and they absorb the streak and stopping-rule biases that fooled earlier tests.

**Data.** Men 2013–2024: 65,968 matches; 754 players with at least 20 matches per half (median 98.5). Women 2016–2024: 28,110 matches; 347 players (median 128).

*Observed.* Δ is real minus replay reliability; higher = more trait-like beyond luck. The pass rule is Δ ≥ 0.10 with the interval above 0 and a correlation with hold or break rate below 0.3, Holm over 10.

| Statistic | Men: Δ [95%] | Women: Δ [95%] |
|---|---|---|
| S1 hold after breaking | +0.012 [−0.062, +0.089], tie | −0.064 [−0.163, +0.029], tie |
| S2 break back | −0.030 [−0.101, +0.033], tie | +0.063 [−0.034, +0.156], tie |
| S3 point-to-point dependence | −0.000 [−0.058, +0.057], tie | −0.015 [−0.111, +0.076], tie |
| S4 game-to-game serve dispersion | **+0.074 [+0.010, +0.137]**, below the 0.10 margin (Holm p 0.21) | −0.009 [−0.099, +0.090], tie |
| S5 set-to-set swing | −0.047 [−0.111, +0.017], tie | +0.020 [−0.085, +0.125], tie |
| Placebo: hold after holding | +0.054 [−0.020, +0.136], on the replay as required | +0.045 [−0.061, +0.161] |

* **Swings exist across the population; players do not differ in them.** Real matches show more set-to-set swing than the replays (men +0.053, women +0.036 in dispersion units), more game-level dispersion, and slightly more holds right after breaking (+0.0065 holds per game, men). But no statistic separates players beyond luck.
* **The one lead is men's S4: game-to-game variation in serve within a set.**
  * At 50 or more matches per half (a pre-registered secondary): +0.225 [+0.135, +0.310], against −0.006 in the replay.
  * Post hoc, it survives strict sequences, centring by source and by event, and the main tour alone (+0.30).
  * It correlates −0.28 with hold rate.
  * At 20 or more per half it passes only under one of four replay variants, so its verdict depends on how the replays are built.
* **The replays are not fully calibrated.** In every variant the two sets of a replayed match are more alike than in real matches. For example, the set-1 and late-set residuals of men's best-of-three matches correlate 0.42 in the main variant against 0.27 in real ones. The inherited de-noising (`stage2_anatomy.denoised_rates`) draws the two players independently and loses part of the gap in skill between them. A null verdict is robust to this; the S4 lead is not yet.

**Inferred.** Momentum, streaks and pressure reactions are not stable player traits at full depth. That closes them as pre-match trait features (and with them the brainstormer's swing-game and leverage ideas). Within-match dynamics remain an in-play question.

### 5.2 WTA medical events: the retirement mechanism passes, the result screen does not

**Question.** Does a physio treatment in a player's previous logged match change her next match? Tester: `med_*.py`.

**Data.** The WTA umpire logs:
* pairs of a previous match and the next one within 21 days;
* 9,962 primary pairs in discovery (4 Jun 2019 – 2021) and 20,762 in replication (2022–2024);
* treated in 6.0% and 6.2% of pairs, stable by season.

**Results.** *Observed.* The risk ratio is next-match retirement or walkover, treated against untreated; above 1 = treated players retire more. The serve-point shift is in percentage points; negative = treated players serve worse.

| | Discovery | Replication | Decision |
|---|---|---|---|
| Treated: next-match retirement or walkover (M1), risk ratio | **2.39 [1.48, 3.84]** (4.5% against 1.9%) | **2.27 [1.69, 3.06]** (4.3% against 1.9%) | **Passes** (Holm p 0.0014; permutation-based 0.048) |
| Treated: next-match serve-point shift (M2) | −0.48 [−1.14, +0.18] | −0.04 [−0.47, +0.39] | Tie |
| Toilet break (negative control): risk ratio | 0.98 [0.66, 1.45] | 0.88 [0.65, 1.19] | Null, as required |
| Toilet break: serve-point shift | +0.15 [−0.35, +0.64] | −0.22 [−0.51, +0.07] | Null, as required |
| Injury reason (nested) | 7 pairs | 29 pairs | Not testable: the reason exists only on suspension records, which name no player |
| Women's fade markers within the last match (first serves in, double faults, tempo) | all ties | all ties | Fails |

* **Concentration.** The effect sits in fresh pairs: she won, and plays the next round 1–2 days later. Risk ratio 3.40 [2.12, 5.46] and 2.67 [1.83, 3.90]. After a loss, with the next match at a later event, both windows tie.
* **Not a retirement-prone player.** Adding her own 365-day history of retirements, walkovers and treatments barely moves it: 2.24 and 2.01. This check was added after the result and is labelled exploratory.

**The residual screen** (`med_residual_screen.py`; registered in its docstring before it ran). The question here is whether the treatment reaches the match result beyond what the benchmarks already say. The benchmarks are the 54-input model and the close, each recalibrated on earlier seasons only. The data are the women's main-tour matches of the model frame. *Observed.* Log-odds shift per treated side; negative = the treated player wins less often than the benchmark says.

| | Discovery (4,566 matches, 315 with a treated side) | Replication (7,308; 586) |
|---|---|---|
| Given the model | −0.22 [−0.46, +0.02], tie | +0.07 [−0.11, +0.25], tie |
| Given the close | −0.21 [−0.45, +0.04], tie | +0.09 [−0.09, +0.27], tie |

**Inferred.**
* The mechanism is real: a treated player is more than twice as likely to retire or withdraw next time, mostly when she plays again a day or two later.
* For the match-winner market it is worth little. The excess is about 2 points of retirement risk; about three quarters of the events are retirements, and some of those matches would have been lost anyway. So a 2.3× risk shifts a treated player's win chance by roughly one point, and only in the 7–8% of the frame's women's matches that have a treated side. The screen sees no shift beyond the model or the close: discovery leans negative, replication leans positive, both ties.
* It is a lead for markets whose settlement depends on a retirement, and for in-play (medical calls during a match).
  * Many bookmakers void game handicaps and totals when a player retires, by general practice. Polymarket's own rule was not checked.
  * It is not a lead for the pre-match winner price.

### 5.3 Finishing form carried into the next match: fails the registered rule

**Question.** Does how a player finished match t carry into her or his next match at the same event? The measure is the late set's serve residual minus the first set's. The forward association is compared with the reverse one: how match t's ending relates to the match **before** it, on the same triples. Tester: `carry_*.py`. Triples are consecutive completed matches at one event, at most 3 days apart:
* discovery 2013–2021: 26,711 (men 19,259, women 7,452);
* replication 2022–2024: 10,576.

*Observed.* Δ is in serve-point log-odds of the next match per 10 points of set residual; positive = late form carries forward more than backward.

| | Discovery | Replication |
|---|---|---|
| Δ (primary) | **+0.0038 [−0.0030, +0.0107], tie** | +0.0109 [+0.0003, +0.0216], positive |
| Forward, late minus first set | +0.0038 [−0.0012, +0.0087] | +0.0086 [+0.0011, +0.0161] |
| Reverse, late minus first set | −0.0001 | −0.0024 |
| Replay null (50 replays of match t) | centred +0.0006, inside its band | centred −0.0018; 100 more replays centre at +0.0002 |
| Label-swap placebo | centred on 0; real Δ's p = 0.28 | p = 0.040 |
| Fade with rest (1 day minus 3 days) | −0.0057 [−0.045, +0.034], tie | tie |

**Verdict: fails**, because discovery ties. Other readings:
* The two windows pooled give +0.0059 [+0.0002, +0.0117]. This pool was not registered.
* Restricting discovery to triples the player also won flips it to −0.0068, a tie.
* Women's replication is +0.0145 [+0.0006, +0.028]. Men tie in both windows.

**Inferred.**
* A large carry-over of finishing form across matches is ruled out as a pre-match signal.
* A small one is not. The replication-sized effect, about 0.2 points of next-match serve points per SD, is roughly one point of match-win chance at even odds.
* Testing it again needs a new registration, for example on the closed 2025–2026 holdout. That is the owner's decision.

**Side observation, consistent with [Stage C](../ufc_ideas/stageC.md).** The winners of match t serve about 0.4–0.5 points better in the late set than in set 1, against about 0 in replays held to the same winner. In the replays, the set-1 and late-set residuals correlate 0.27, against 0.08 in real matches. Either the replays' day-to-day variance is too large, or real sets differ more from each other than independent points allow. Within-match swings are real; whether they carry across days is what this test could not establish.

### 5.4 The women's points-share anomaly: box-score error, not momentum

[Predictability Stage 2](../predictability_diagnostic/stage2.md) left one question open: the women's points share decides matches less than pure luck predicts (log loss 0.118 against 0.103). That could have been a sign of within-match streakiness. Tester: `i2_points_share.py`.

*Observed.* The gap is real minus replay cross-validated log loss of the winner on the points share; positive = the anomaly's direction.

| Population | True-rate variance × 0.5 | × 1 | × 1.5 | Per player-season |
|---|---|---|---|---|
| Women, WTA log, non-Slam, Jun 2019 – 2024 (13,747 matches) | −38.6 | −22.8 | −14.2 | −24.2 |
| Women, all sequence sources (16,919) | −19.2 | −6.0, tie | +2.9, tie | −7.3 |
| Men (control), non-Slam 2013–2024 (57,666) | −21.6 | −4.0 | +1.9, tie | −6.5 |

* **No positive gap appears anywhere.**
* **The source of the anomaly is the box score.** On the same matches, the women's points share from Stage 0's box scores decides with log loss 0.109, against 0.0786 from the point sequences (+30.4 mLL worse; the men's difference is 0.0).
  * 31 of 33 matches with the winner on the wrong side are in two WTA events of 2021 (ids 2021-2027 and 2021-2028), whose box scores are mirrored.
  * Refitting Stage 2's women's table without those two events (140 matches) moves its log loss from 0.1182 to 0.1049, against the replay's 0.103.

**Inferred.** Stage 2's open question 7 is answered: the anomaly was a data error, not momentum. The mirrored box scores also feed the current model's form inputs; see section 7.

**A caveat on the WTA log.** Its tie-break points are often unrecorded, which leaves 68% of logged matches with a tie-break unusable. So the WTA-log population leans toward decisive matches (0.092 tie-breaks per match, against 0.226 across all sources). This biases that row of the table, not the conclusion, which the all-source row shares.

### 5.5 Men's game-to-game serve dispersion: an exact check with no rate model

The auditor suspected the one surviving lead (men's S4, section 5.1) was an artefact of the mis-calibrated replay, and proposed a null that needs no rate model.
* **The null.** Shuffle the order of each server's points within each set, keeping every point's outcome, and re-score the shuffled sequence into games. Each player's per-set serve rate is kept exactly; only the order is random.
* **Registration.** The registration (`trait_s4_perm_prereg.md`) was hashed before any permutation ran (SHA-256 `2caab7e1…b156378`, in `trait_s4_perm_prereg.sha256`), and the script refuses to run if the file changes.
* **Scope.** Tie-break points are excluded. Three permutations per match; seasons ≤ 2024; no match result read.

*Observed.* Δ is real minus permuted split-half reliability; higher = more trait-like beyond random order.

| | Real r | Permuted r | Δ [95%] | Verdict |
|---|---|---|---|---|
| Men, ≥ 20 matches per half (the registered depth) | 0.091 | 0.035 | +0.055 [−0.004, +0.116] | **Fails**: below 0.10, interval reaches 0 |
| Men, ≥ 50 per half | 0.234 | 0.071 | **+0.163 [+0.086, +0.235]** | Clears 0, reported only |
| Women, ≥ 20 | 0.010 | −0.004 | +0.013 [−0.084, +0.109] | Tie |
| Women, ≥ 50 | 0.054 | −0.005 | +0.059 [−0.053, +0.169] | Tie |

* **Ability.** The men's statistic correlates −0.24 with hold rate and +0.16 with break rate, so it is not just ability.
* **Calibration of the null.** Run on the iid replays, where order is random by construction, the shuffle is unbiased for reliability. At the population level it is biased: it makes about 2.7% more, shorter games. Net of that bias, real games are slightly more dispersed than random order (men +0.026, women +0.012).

**Inferred.**
* About 0.16 of the replay-based 0.23 (at ≥ 50 per half) is genuine: some men's serve points cluster within service games more than others. The rest came from the replay's calibration, as the auditor suspected.
* The trait is weak. It shows only with deep histories, and a 52-week window recovers at most ρ² 0.055 of a player's value elsewhere in his career.
* **Not usable as a pre-match winner feature as built.** It stays a men-only lead for a variance input (totals and handicaps), and would need its own pre-registration.

### 5.6 The scoped round: point-derived match statistics with any promise

**Why there is a second round.** After the first conclusion the owner narrowed the question: "When I asked what has promise, I meant specifically for point to point statistics that we build into our own match level statistics not in general for the model."
* The brainstormer ranked the candidates ([`9_ideas_scoped.md`](../../../data/studies/point_sequence/debate/9_ideas_scoped.md)), and the auditor adjudicated ([`10_audit_scoped.md`](../../../data/studies/point_sequence/debate/10_audit_scoped.md)).
* Three screens followed. Each registration was hashed (SHA-256) before any estimate, and its script refuses to run if the file changes.

**Serve-speed change** (`speed_*.py`; registration hash `b817cb92…ecaefeaa`).
* **Statistic.** Mean first-serve speed over the last 14 days minus over the last 364 days, own history in order, scaled per SD (men 6.0 km/h).
* **Test.** A residual screen against the model's and the close's recalibrated forecasts. Speed is a near-perfect trait (split-half 0.99), so there is no trait gate.
* **Coverage.** Men: 860 of 4,868 matches in discovery (Slams to 2020, all of 2021) and 3,534 of 7,958 in replication.

*Observed.* β is in log-odds per SD; positive = the player whose recent first-serve speed rose more against his own norm wins more often than the benchmark says.

| Men | Against the model | Against the close |
|---|---|---|
| Discovery | −0.018 [−0.209, +0.174], tie | −0.026, tie |
| Replication | **+0.090 [+0.017, +0.162]** | **+0.097 [+0.024, +0.170]** |
| Implied gain in replication, matches with the feature (mLL, positive = feature better) | +0.36 [−0.88, +1.59], tie | +0.41 [−0.83, +1.64], tie |

**Verdict: fails the registered rule** (the discovery sign).

**Inferred.**
* Discovery is too small to confirm or contradict anything: its standard error, 0.098, is wider than the replication effect.
* Replication is consistent across three feature versions, both benchmarks and all three seasons (+0.09, +0.13, +0.05). It is borderline: without clipping, the block interval reaches −0.002. It is also small, about 0.4 mLL where the feature exists.
* The only clean confirmation left is the closed 2025–2026 holdout. With Slam speeds alone that test has about 15% power; adding ATP non-Slam per-point speeds for 2025–2026 raises it to about 50%. Those speeds exist only in ATP's encrypted Stats Centre files, so getting them is the owner's decision.

**Return and serve leverage** (`lev_*.py`; registration hash `6f5f692c…74c8bb1f`).
* **Statistic.** Each point the player returned (or served) is weighted by its importance: P(win the match | win the point) − P(win the match | lose it). The importance is computed from the score before the point at the two players' **pre-match** serve probabilities, so the match's own result cannot leak into the weights. The statistic is the weighted share of those points won minus the plain share.
* **Null.** An exact within-set shuffle of the player's point outcomes, re-scored and re-weighted. On iid replays it was shown to be unbiased.

*Observed.* Δ = real minus shuffled split-half reliability; higher = more trait-like beyond random order. 754 men and 347 women at ≥ 20 matches per half.

| | Men | Women |
|---|---|---|
| Return leverage | −0.014 [−0.037, +0.007], tie | +0.001 [−0.038, +0.039], tie |
| Serve leverage | +0.021 [−0.001, +0.043], tie | −0.003 [−0.035, +0.032], tie |

* **All four fail.** At ≥ 50 matches per half all four are ties as well.
* The women's leverage statistics also track ability: serve leverage correlates 0.34 with hold rate, and return leverage 0.40 with hold rate.
* Missing tie-breaks remove only 2.6–3.3% of the importance mass, because other sources fill most WTA tie-break matches.
* **Inferred.** The earlier Slam-only finding that "return big points persist beyond luck" (0.21 / 0.19) was set structure and ability, not players who win the big points. Leverage closes at full depth on both tours.

**Women's own-serve tempo** (`tempo_*.py`; registration hash `1de0c087…df06c7`).
* **Statistic.** The gaps between points on her serve in the WTA umpire log (June 2019 – 2024: 13,747 matches, 1.48 million gaps). Gaps next to lets, challenges, medical or toilet breaks and suspensions are dropped. The gaps are adjusted for umpire, event-year, score class and the type of the previous and current point.
* **Tempo level** is a near-perfectly stable style: split-half r 0.980 [0.976, 0.984]. It fails the new-information bar: the 58 model inputs explain 12–14% of its A − B variance, above the 10% bar.
* **"Pressure pace"** (the gap on pressure points minus the normal gap) passes its trait gate by a wide margin: +0.750 [+0.683, +0.809] against shuffled labels. But post hoc, game points and late non-pressure points show the same. It is a score-state tempo signature, not a reaction to pressure.

**The residual screen of pressure pace** (`pace_screen.py`; registration `pace_screen_prereg.md`, hash `5ed9bf06…8d83ed6`, recorded before the script was written).
* **Population.** Women's model-frame matches where both players have five or more logged matches in the previous year. Discovery 2020–2021: 2,874 matches; replication 2022–2024: 6,721.

*Observed.* β is in log-odds per SD of the A − B difference; positive = the player who slows down more on pressure points wins more often than the benchmark says.

| | Discovery | Replication | Gain in replication with the discovery β (mLL, positive = feature better) |
|---|---|---|---|
| Pressure pace, given the model | −0.060 [−0.141, +0.021], tie | −0.008 [−0.060, +0.045], tie | −0.28 [−0.96, +0.40], tie |
| Pressure pace, given the close | −0.054, tie | −0.005, tie | −0.25, tie |
| Tempo level, given the model (secondary) | −0.037, tie | −0.026, tie | +0.07, tie |

* **Fails.**
* **Inferred.** Women's tempo signatures are reliable styles that carry nothing the model's inputs and the close do not already hold. Men's point clocks (TDI's capture) are therefore not worth pursuing for tempo.

## 6. Conclusion: which point-to-point statistics have promise

The owner's question, as clarified: which statistics that **we build ourselves from the point-by-point data into match-level statistics** have promise, either to get more data for or to combine in novel ways.

The answer was settled after the scoped round ([brainstormer](../../../data/studies/point_sequence/debate/9_ideas_scoped.md), [auditor](../../../data/studies/point_sequence/debate/10_audit_scoped.md)) and the screens of sections 5.1–5.6. Every statistic was built from the unified table and tested at full depth, with registrations fixed in advance. Everything below is a **suggestion**.

### The answer, statistic by statistic

| Point-derived match statistic | What it measures | Result (positive = more trait-like, or better than the benchmark) | Verdict | More data? | Novel combination? |
|---|---|---|---|---|---|
| **Serve-speed change** (men) | First-serve speed over the last 14 days minus over the last 364, from the points' speeds | Replication +0.090 [+0.017, +0.162] log-odds per SD given the model (+0.097 given the close); discovery −0.018, a tie, on only 860 matches; about +0.4 mLL where available | **The only statistic with a replicated signal. Fails its registered rule because discovery is too small to judge.** A state, not a trait | **Yes, the one case.** ATP non-Slam per-point speeds for 2025–2026 raise the power of one clean confirmation from about 15% to about 50%. They exist only in ATP's encrypted Stats Centre files, so getting them is the owner's decision | Pair it with box-score serve form, and with the within-match speed fade, on the same matches. Untested |
| **Finishing form carried into the next match** | Late-set minus first-set serve residual, carried into the next round | Discovery +0.0038, a tie; replication +0.0109 [+0.0003, +0.0216] | **Inconclusive.** A state; at most about 0.2 mLL if real | No | No |
| **Within-set serve clustering, S4** (men) | How unevenly a player's serve points fall across service games within a set | Exact shuffle null: +0.055 [−0.004, +0.116] at ≥ 20 matches per half (fails); +0.163 [+0.086, +0.235] at ≥ 50 | **A weak trait, visible only in deep histories.** Not a winner feature | No | Only as a variance input for game totals and handicaps |
| Hold after breaking, break back, point-to-point dependence, set swings (S1–S3, S5) | Momentum and streaks | All ties against pure-luck replays, both tours | **Closed** | No | No |
| Return and serve leverage (Klaassen–Magnus importance) | Big-point play | All four ties against an exact shuffle | **Closed**; the earlier Slam result was set structure and ability | No | The IOS and matchup versions were conditional on a pass |
| Women's tempo (level and pressure pace) | Seconds between points on her own serve | Reliable styles (r 0.98 and +0.75 beyond shuffle), but the residual screens tie: pressure pace −0.008, tempo level −0.026 in replication | **Closed** as a pre-match statistic | No: men's point clocks are not worth pursuing for this | No |
| Women's within-match fade (first serves in, double faults, tempo) | Physical decline inside the last match | All ties | **Closed** | No | No |
| Shot-level rates (rally length, how points end, net play, placement, return depth, wing) | Style ([shot-level study](../shot_level/README.md)) | Real traits; nothing given the close | **Closed** for winner markets | No | No |

### What this means

* **Point-derived traits are closed. What remains are states, and they are small.**
  * Every statistic that describes how a player *is* has failed at full depth: momentum, streaks, pressure, leverage, tempo, style.
  * The only signals left describe how a player *is right now*: the change in serve speed, and, inconclusively, how the last match ended.
  * This is the brainstormer's "states, not traits" pattern. It holds for point statistics even though its subset version (section 4) did not.
* **The one place to get more point data is serve speed, men's non-Slam, 2025–2026.**
  * It is the only point-derived statistic with a replicated positive result: +0.090 per SD given the model in 2022–2024.
  * It is still small, about 0.4 mLL where available. That is the size of the best features this project has found (0.25–0.4), well below the model's lead over the close.
  * Getting it needs decryption of ATP's files: the owner's call.
* **The one novel combination worth building** is the speed family together on the same matches: the 14-day speed change, the within-match speed fade, and box-score serve form.
  * Men 2022–2024 is the only window with speeds outside the Slams (Infosys), and its 2022–2024 rows are no longer blind.
  * So the combination should be registered now and judged on the closed 2025–2026 holdout, alone or in the shared final test with the feature-interactions study.
* **Not worth more data** for point-derived statistics:
  * more point-winner sequences for momentum or streaks;
  * charts or ball tracking for style rates;
  * men's point clocks for tempo;
  * the WTA tie-break recovery (it barely affects any of these statistics).

### Why the nulls are not the imputation the owner feared

* The table covers 91% of the men's and 73% of the women's model matches with their own sequence.
* The trait tests used 754 men and 347 women with at least 20 matches per half.
* So the nulls come from the statistics, not from gaps.
* **Process suspects** (per the owner's premise that a null is a process flaw):
  * the iid replay is mis-calibrated, but the exact shuffle nulls (S4, leverage) avoid it and agree;
  * men's Challengers of 2021–2024 are holed (Infosys), which thins men's depth below the main tour;
  * serve speed is the one statistic limited by data rather than by its nature.

### Outside the question: findings for the model, the venue and in-play

The first conclusion of this study ranked these. They are kept briefly because they matter, but they are not point-to-point statistics:

* **Data repairs that feed the model.** Stage 0 box scores with the players exchanged (three WTA events of 2021–2022) feed the women's form and IOS inputs. The point sequences can find every such flip. The 58-input model has not been scored as a whole since 6 October.
* **The WTA medical-event hazard (umpire log, not points).** A treatment in the previous match more than doubles next-match retirement or walkover: 2.27 [1.69, 3.06] in replication. Its effect on the result is unresolved, and its value depends on how the venue settles walkovers and retirements; Polymarket settled sampled 2026 walkovers at 0.50 / 0.50. It belongs with the feature-interactions study's retirement-hazard family (I-042).
* **In-play.** Real matches carry slightly more within-set clustering than random order, shared by all players. An in-play price that treats points as independent could miss it; the price-only in-play pilot would test that.
* **Venue and timing.** The model's edge over the close is uniform (+0.55 in 2015–2021, +1.39 in 2022–2024), but betting at the early market made $0.00 per 100 matches.

## 7. Side findings (data defects found on the way)

*Observed* by the table's builder; reported, not fixed:

* **Stage 0 box scores with the two players exchanged** in 55 matches confirmed by two point sources.
  * 41 of them are in two WTA events of February 2021 (ids 2021-2027 and 2021-2028); the trait tester also found the event 2022-2030.
  * These feed the model's box-score form inputs (the women's `form_*`, `iosO_*`, `iosD_*` and `prod_*` histories).
  * They also created the women's points-share anomaly (section 5.4).
  * **Worth fixing first** (suggestion).
* **`timing.parquet`'s `start` is the tournament's start day, not the match day.** The best-estimate match day is `obs`. CLAUDE.md's summary of the clock ("a match reads the state as of `es`") is right; only the column name `start` invites the misreading made here.
* **The iid replay's de-noising** (`stage2_anatomy.denoised_rates`) has two problems:
  * it fits its prior on whatever data it is given, so it is not frozen;
  * it draws the two players independently, so replayed matches have too many tie-breaks, and their sets are more alike than real sets.

  The testers re-implemented it with priors frozen on ≤ 2018. Any future replay benchmark should model the two players jointly.
* **The shot-level study's Australian Open table lacks each game's last point.** `src/eda/shot_level/points.py::ausopen` keeps only rows of type `point`, but the feed writes each game's winning point as `game`, `set` or `match`. That study's AO statistics are affected. A corrected adapter (`ausopen_mc`) is used here.
* **Sackmann's point strings skip 2016 entirely.** The two snapshots cover July 2011 – December 2015 and January–February 2017; the data map's catalogue says "2011 to January 2017".
* **The reused Infosys and SirGenkii point tables drop points with no shot group.** 46% and 28% of their sequences have holes, so men's Challengers of 2021–2024 are almost absent from the usable table. An adapter that keeps those points would recover them.
* **WTA umpire logs write many tie-break points as "0-0"**, so 4,947 logs have points with unknown winners. Those matches fall back to other sources.
* **SofaScore's server fields are unreliable on tie-breaks.** Its `firstToServe` field matches the actual first server only 51% of the time, so servers are rebuilt from the alternation of service games.

## 8. Files and rebuild

All code is in `src/eda/point_sequence/`, outputs in `data/studies/point_sequence/`, tests in `test/point_sequence/`. Run everything with `./python.sh` from the repository root.

| Part | Code | Outputs |
|---|---|---|
| Unified point-sequence table | `common.py`, `replay.py`, `adapters.py`, `build.py` (about 2 minutes; `--refresh all` re-reads every source) | `sequences.parquet` (one row per point; use `usable`), `seq_matches.parquet`, `points_*.parquet` and `matches_*.parquet` (new sources), `wta_events.parquet` (646,726 non-point umpire-log records), `agreement.csv`, `coverage_model.csv`, `coverage_stage0.csv`, `build_summary.json` |
| Where the edge lives (I1) | `diag_edge_location.py`, `diag_edge_split.py` | `diag_edge_location.csv/.json`, `diag_edge_split.csv` |
| Momentum and streak traits; the women's anomaly; the exact S4 check | `trait_common.py`, `trait_build.py`, `trait_reliability.py`, `trait_s4_explore.py`, `trait_s4_perm.py`, `trait_s4_perm_calib.py`, `i2_points_share.py` | `trait_prereg.md`, `trait_s4_perm_prereg.md` (+ `.sha256`), `trait_*.csv/.json/.parquet`, `i2_*` |
| Medical events | `med_build.py`, `med_stats.py`, `med_estimate.py`, `med_explore.py`, `med_residual_screen.py` | `med_prereg.md`, `med_results.json/.csv`, `med_placebo.csv`, `med_pairs.parquet`, `med_explore.json`, `med_residual_screen.json` |
| Finishing-form carry-over | `carry_data.py`, `carry_sim.py`, `carry_fit.py`, `carry_posthoc.py` | `carry_prereg.md`, `carry_results.json`, `carry_estimates.csv`, `carry_replay_null.csv`, `carry_label_swap.csv`, `carry_posthoc*.{json,csv}`, `carry_triples.parquet` |
| Serve-speed change (scoped round) | `speed_build.py`, `speed_screen.py` | `speed_prereg.md` (+ `.sha256`), `speed_results.json`, `speed_estimates.csv`, `speed_features.parquet`, `speed_build_summary.json` |
| Return and serve leverage (scoped round) | `lev_common.py`, `lev_run.py` | `lev_prereg.md` (+ `.sha256`), `lev_tests.csv`, `lev_reliability.csv`, `lev_rho2.csv`, `lev_mass.csv`, `lev_results.json`, `lev_player_matches.parquet` |
| Women's tempo and its residual screen (scoped round) | `tempo_run.py`, `tempo_diag.py`, `pace_screen.py` | `tempo_prereg.md` (+ `.sha256`), `tempo_reliability.csv`, `tempo_results.json`, `tempo_player_matches.parquet`, `pace_screen_prereg.md` (+ `.sha256`), `pace_screen_results.json` |
| The debate | – | `debate/0_brief.md` … `debate/10_audit_scoped.md` |

Tests: `./python.sh -m pytest test/point_sequence`.

**Big files.** Git ignores the Parquet files: `sequences.parquet` (≈94 MB), `trait_player_matches_variants.parquet` (≈62 MB), the `points_*.parquet` files and `cache/`. Every one is rebuilt from the scripts above, and the replay tables are regenerated from fixed seeds.

**Not done here (suggestions for the owner):** none of the new statistics was added to the model, and no GPU fit or paid call was made. No gate passed a stage that would justify one.
