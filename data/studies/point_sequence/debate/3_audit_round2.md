# Audit, round 2: the brainstormer's 31 ideas

Auditor, 6 Oct 2026. Rubric, gates and power figures from `audit_round1.md`.

* Gains are mLL per match; **positive = the forecast with the feature (or the second-named) is better**, and "tie" when the 95% interval spans 0.
* Labels: **observed** = checked read-only today; **inferred** = my reasoning; **suggestion** = proposal.

## 0. Verification of the brainstormer's claims, and my own corrections

**My round-1 errors (corrected; observed):**

* **Men's 2013–15 training window is not thin.**
  * Sackmann's point strings (`data/studies/match_timing/links/pbp_copy.parquet`, linked but not staged) cover 91.5% / 94.7% / 94.7% of the men's frame matches in 2013 / 2014 / 2015, at every level (Slams 0.94–0.96, Finals 1.0, 1000s 0.90–0.95, 500s 0.92–0.95, 250s 0.90–0.95).
  * They cover 0% in 2016 and 9% in 2017; marcosjn2 covers about 64–71% of those years.
  * The data map's catalog lists only T250/TQ/CH/ITF for this source; that list is incomplete.
* **`src/eda/point_sequence/` is this session's builder agent**, as the coordinator noted.
* **The SofaScore server-shift caveat is documented:** 161 of 8,861 ace-coded points were won by the player marked receiving, and 94 of 6,784 double-fault-coded points by the player marked serving. It is small, consistent with the 99.22% game-server agreement.

**The brainstormer's "observed" claims, checked:**

| Claim | Verdict |
|---|---|
| Men 2013–15 at 91–95% via Sackmann strings | **Correct** (above) |
| Exact start times: men 98–100%; women 68–71% (2013–18), 83–100% (2019–25) | **Correct**. My union of the link tables: men 0.98–1.00 every season including 2026; women 0.68–0.71 (2013–18), 0.85 / 0.91 / 0.96 (2019 / 20 / 21), 0.98–1.00 (2022–26) |
| WTA log incidence (treatment 15.5–16.7%, toilet 31–41%, …) | **Correct**; it matches my 2022–25 count |
| E1: "frame link share 0.54 in 2019 and 0.63–0.99 in 2020–26" | **Overstated for the event log.** The 2024–26 link shares (0.89 / 0.99 / 0.98) include Slam matches, which the API lists from 2024 (box scores only) but whose **event logs are empty**. Event-log coverage of the women's frame is at most 1 − Slam share, about 0.78–0.80. Non-Slam coverage is 0.97–1.00 from 2020 and 0.68 in 2019 |
| E2: the change in first-serve speed, "+0.06 [−0.02, +0.15]" | Correct for Stage 2 over 2013–26. In 2022–26 it is +0.14 [−0.00, +0.28], a tie |
| Stage 3's oracle "detected 0.25 in only 0–70% of draws" | Correct |
| A05, B09, B10, C07 untested | **Correct** (`docs/studies/predictive_frontier/research.md`). Untested, but each has a tested neighbour (§5) |
| G2: "the overlap is several thousand matches" | **Overstated.** Official point clocks exist for about 1,896 of 2026's main-tour Polymarket markets (WTA 1,269, Slam feeds 371, TDI 256), plus an estimated 400–600 WTA matches in late 2025. That is about 2,300–2,500 matches, about 75% women, and about 500 men |

## 1. Scores for all 31 ideas

* Criteria and weights: C1 mechanism and why the price lacks it (15); C2 evidence of a trait or dynamic beyond the replay (15); C3 coverage, including training years (15); C4 power (10); C5 leakage and selection risk, scored in reverse (15); C6 testability (10); C7 economic path (10); C8 value even if null (10).
* Gates: G1 reads 2022–26 outcomes in design (2025–26 is closed); G2 cross-player feature without the clock and probe; G3 target state or format read from its own score, or prices after the point; G4 data not held or not approved; G5 no replay benchmark.
* Bands: ≥ 75 build now; 55–74 build after a cheap gate; 40–54 park; < 40 reject.

| ID | Idea | Gates | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | **Total** | Band and verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | WTA medical and distress events | pass (expected-rate baseline frozen ≤ 2021) | 13 | 8 | 9 | 3 | 11 | 9 | 6 | 6 | **65** | **Build after a cheap gate**: a mechanism check on 2019-06 – 2024 first. Women only |
| G1 | 24 h → close move screen | pass with a time split | 8 | 6 | 9 | 8 | 11 | 9 | 5 | 7 | **63** | **Build** as a tool, explore half only, applied to features that pass their own gate |
| I2 | Is the women's points-share anomaly real? | pass if ≤ 2024 | 5 | 8 | 12 | 8 | 11 | 9 | 2 | 7 | **62** | **Do now** (it is the cheap gate for B3) |
| D1 | Conversion luck | pass (format from schedule rules) | 6 | 6 | 14 | 3 | 12 | 9 | 5 | 6 | **61** | **Build after a cheap gate**: a residual screen against the model's own out-of-sample forecast. Most of it is already tested (§5) |
| I1 | Where the current edge lives | pass if ≤ 2024 | 5 | 5 | 14 | 4 | 12 | 10 | 3 | 7 | **60** | **Do now**, on stored forecasts for 2014–24 |
| B1 | Finishing-form carry-over | pass (exchangeable sets plus a reverse-time placebo) | 7 | 7 | 11 | 5 | 12 | 8 | 3 | 7 | **60** | **Build after a cheap gate**: a Slam first pass on ≤ 2021 |
| G2 | In-play reaction | **fails G1 and G3 as proposed**: "sets the prior for D1/D2" is a holdout leak, and prices must precede the point | 8 | 7 | 9 | 9 | 9 | 7 | 4 | 7 | **60** | **Build after redesign**: firewall it from pre-match design, time split, price strictly before each point. Pilot on the explore half |
| E3 | Real rest hours and late finish | pass for the close; **fails G4 for the 24 h angle** (no historical order of play) | 9 | 5 | 12 | 2 | 11 | 9 | 5 | 5 | **58** | **Build after a cheap gate**: the next-day subset first, residualised on day gaps and load |
| E2 | Fade in non-outcome markers | pass for research; **G4 for men's deployment** (no 2025–26 non-Slam speeds) | 11 | 7 | 7 | 3 | 11 | 7 | 4 | 6 | **56** | **Build after a cheap gate**: women's first-serve, double-fault and tempo fade from the WTA log now; men's speed fade on Slams ≤ 2021 |
| A1 | Unified table, then a depth re-test | pass if career truths use ≤ 2024 | 4 | 6 | 12 | 1 | 10 | 8 | 2 | 10 | **53** | **Park the outcome re-test.** The table proceeds as infrastructure. Run only the outcome-free recovery gate (ρ² against the career truth, by depth) when it lands |
| G6 | Totals and handicaps | **G4**: prices not fetched (free) | 9 | 7 | 6 | 5 | 10 | 5 | 4 | 6 | **52** | Park. A liquidity census first (an acquisition lead) |
| B3 | Within-match volatility | pass | 8 | 4 | 11 | 3 | 10 | 6 | 3 | 5 | **50** | Park; gated on I2 and outcome-free reliability against the replay |
| C1 | Leverage beyond luck, every tour | pass | 4 | 8 | 11 | 2 | 10 | 7 | 2 | 5 | **49** | Park. Outcome-free reliability on the unified table only. Prior market tests are ties |
| G3 | In-play medical events | as G2 | 9 | 5 | 6 | 4 | 9 | 8 | 4 | 4 | **49** | Park; an add-on to the G2 pilot (about 270 events) |
| B2 | Dynamic rating with within-match drift | G2: probe needed | 5 | 6 | 11 | 3 | 8 | 4 | 4 | 6 | **47** | Park. The stop rule is wrong (§4): σ²_pt (within a match) is not σ²_day (carry-over). Only after B1 |
| C3 | Coasting index | pass | 7 | 4 | 11 | 2 | 9 | 7 | 3 | 4 | **47** | Park |
| E4 | Intensity-weighted load | pass | 6 | 4 | 9 | 2 | 11 | 8 | 3 | 4 | **47** | Park. Points played over 14 days come from box scores; fold them into E3 as a control |
| H3 | Live capture for in-play | **G4**: owner decision | 7 | 5 | 6 | 6 | 8 | 4 | 6 | 5 | **47** | **Acquisition lead**: passive Polymarket book recording now; a live point feed only after G2 |
| H2 | SofaScore metadata for marcosjn2 ids | **G4**: scope check | 5 | 4 | 9 | 3 | 10 | 5 | 3 | 6 | **45** | Acquisition lead, conditional on E3 |
| D2 | Last-match drama | pass | 6 | 4 | 9 | 2 | 9 | 5 | 4 | 4 | **43** | Park; fold its continuous "drama load" into D1 later. Rare flags are under-powered |
| G5 | Sharp wallets' early flow | **G1 risk** if wallet classes used 2025–26 P&L | 6 | 4 | 8 | 4 | 7 | 6 | 3 | 5 | **43** | Park; descriptive only |
| B4 | Slow starters and response to losing a set | pass | 6 | 4 | 9 | 2 | 8 | 5 | 4 | 4 | **42** | Park |
| H1 | ATP serve speeds 2025–26 | **G4**: decryption is outside the 24 Sep limits | 8 | 6 | 5 | 3 | 9 | 3 | 4 | 4 | **42** | Acquisition lead, conditional on E2-men replicating |
| C2 | State-dependent serve rates through the engine | pass | 5 | 3 | 11 | 2 | 10 | 5 | 2 | 3 | **41** | Park; the state effects are luck-level traits |
| E5 | Tempo profile | pass | 4 | 6 | 8 | 1 | 10 | 7 | 2 | 3 | **41** | Park; use tempo as a control in E2 |
| B5 | Swing games | pass (streak bias must be handled) | 5 | 3 | 10 | 2 | 7 | 7 | 3 | 3 | **40** | Park; at most a trigger in G2 |
| B6 | Rally recovery | pass | 7 | 3 | 6 | 2 | 9 | 7 | 2 | 3 | **39** | **Reject** standalone; a secondary fade marker in E2 at most |
| H4 | Weather at match time | – | 4 | 3 | 7 | 2 | 9 | 5 | 2 | 3 | **35** | Park |
| B7 | Tilt signature | pass | 5 | 2 | 7 | 2 | 7 | 6 | 2 | 3 | **34** | **Reject** ("after a lost point" is chance) |
| C4 | Pressure and volatility products | conditional | 4 | 2 | 10 | 1 | 8 | 5 | 2 | 2 | **34** | **Reject** unless C1 or B3 pass |
| G4 | Last match's in-play residual | **fails G1**: exists only in 2025–26, so any outcome test reads the closed holdout | 7 | 3 | 4 | 2 | 6 | 5 | 3 | 3 | **33** | **Reject now**; a price-only move screen at most; revisit with 2027 data |

*Inferred, overall:*

* No idea reaches "build now" (≥ 75). Every candidate is capped by **power**: C4 is ≤ 5 for every pre-match idea, because the 2022–24 replication window detects about 1.2 mLL (both tours, one input), against plausible effects of 0.1–0.3.
* The pre-match ideas therefore earn their place through **mechanism gates on sensitive non-market targets**:
  * next-match retirement;
  * next-match serve points won, about 130–145 outcomes per match;
  * the 24 h → close price move.
* Only ideas that pass such a gate should reach a market test.

## 2. The cheapest decisive test for each idea at 55 or above

Shared rules:

* **Windows.** Discovery ≤ 2021; replication 2022–24; 2025–26 closed for outcome tests.
* **Constants.** Every normalising constant (tour baselines, K, expected rates) is frozen on ≤ 2018, or ≤ 2021 for sources that start in 2019.
* **Market screens** are residual screens: a logistic with offset logit(the model's own out-of-sample forecast), plus the feature, with four-week block intervals.
  * The stored forecasts are `data/studies/meta_stack/walkforward.parquet`: the 54-input predecessor, 4 seeds, 2014–26.
  * The 58-input model has no stored forecasts yet.
  * The recalibrated close is the secondary baseline.
* **Placebos.** Every screen carries a placebo: values shuffled within tour × season (and × source) with the missing-value mask kept.

**E1: WTA medical events (65).**

* *Decisive test: the mechanism, before any market test.* Per target women's frame match, flag each player's previous match within 21 days that has a complete log:
  * **treated**: MedicalTreatment, or PhysioCalled not cancelled;
  * **injury**: an explicit Injury, Illness or Heat reason.
* *Endpoints:*
  * M1, next-match retirement, plus withdrawal before the next scheduled match (from the WTA match lists' walkover entries; walkovers are not in the frame);
  * M2, next-match serve- and return-point residuals: binomial, with offset from `stage3_ratings.parquet` `p_serve_a/b`.
* *Controls:*
  * the previous match's result, minutes and retirement status;
  * days since that match; age; surface;
  * the expected treatment rate, frozen ≤ 2021;
  * toilet break as a **negative control** (expected null);
  * the opponent's flag as a mirror;
  * flags permuted within season × previous result × minutes decile;
  * a missingness model (log present or absent against level and previous-event type).
* *Windows:* discovery 2019-06 – 2021 (about 3,700 log-covered frame matches); replication 2022–24 (about 5,800).
* *Pass rule:* M1 risk ratio > 1.5, or an M2 shift ≤ −0.5 pp, with the interval excluding no effect, in discovery; same sign in replication.
* *Only then* a residual market screen (women; discovery 2020–21, replication 2022–24), and G1 on the explore half.
* *Power note (inferred):* about 1,500 treated-flag matches in replication give a within-subset detectable gain of about 12 mLL; about 400 injury-flag matches give about 47. **The market test is directional unless the mechanism is strong.** Make "treated" the market primary and "injury" secondary, the reverse of the brainstormer's choice (§4).

**G1: 24 h → close move screen (63).**

* *Test:* H4 design (`surface_rating_race`).
  * Regression without intercept of M = logit P(30 min) − logit P(24 h) on standardised x, plus b = logit(the model's no-odds view).
  * Clean event openers and all priced matches; four-week clusters.
* *Window:* explore Sep 2025 – Mar 2026. **Freeze the feature list and the specification**, then confirm on Apr – Oct 2026.
* *Controls:*
  * validated starts; drop markets decided before the close;
  * x must be computable at 24 h (no actual start times, no late news);
  * a placebo x shuffled within week.
* *Pass rule:* slope > 0 with a 95% interval excluding 0 in explore, same sign in confirm, and a move of at least 0.5¢ per standard deviation (below that, worthless against costs of about 1–2¢).

**I2: the women's points-share anomaly (62).**

* *Test:*
  * Refit the points-share → winner logistic on the WTA log's point counts (non-Slam, singles, 2019-06 – 2024; 98.5% replay to the official score).
  * Refit it on its iid replay at de-noised day rates, varying the de-noising prior: true variance × 0.5, 1 and 1.5, and per-player-season rates.
  * Men on the Slam, Infosys and TDI sequences ≤ 2024 as the control.
* *Diagnostics:* the replay's tie-breaks per match and wins with fewer points against the real values.
* *Pass rule:* the women's real-minus-replay log-loss gap (0.118 against 0.103 in Stage 2) survives every replay specification while the men's stays about 0. Only then does B3 get a reliability test.

**D1: conversion luck (61).**

* *Build:*
  * Per past match, L_sets and L_games: actual minus expected under `stage2_iid` at that match's de-noised serve rates, with the format from the repaired schedule rules.
  * Per player: the cumulative luck of the current event's earlier rounds, and an 8-week decayed sum. K frozen ≤ 2018; A − B.
* *Test:* residual screen against the stored out-of-sample forecast (both tours; discovery 2015–21, replication 2022–24). Then G1 (explore half). The sign is pre-registered as negative (the market over-credits luck), tested two-sided.
* *Controls:*
  * report the R² of D1 on (`elo_overall` − `ratings_iid`) and `elo_games`, to show how much the model already spans;
  * run the in-event window only on matches with at least one earlier round in the event;
  * the shuffle placebo.
* *Pass rule:* a replication gain over the model's forecast with an interval above 0, or a G1 slope above 0. Otherwise close D1 and A05. A TabPFN arm only if both pass.

**I1: where the current edge lives (60).**

* *Test:* per-match d = LL(recalibrated close) − LL(recalibrated model); positive = model better.
* *Five pre-declared splits:*
  1. first match at the event against later rounds;
  2. days since the last match: 0–1, 2–6, 7+;
  3. the last match: straight sets against a deciding set;
  4. level: Slam, 1000, 500/250;
  5. tour.
* *Windows:* discovery 2015–21; replication 2022–24; Holm over the 5 contrasts.
* *Pass rule:* a contrast ≥ 1 mLL, with a Holm interval excluding 0 in discovery and the same sign in replication, redirects effort. Otherwise "uniform".
* *Caveat:* this is the 54-input predecessor, not the 58-input model.

**B1: finishing-form carry-over (60).**

* *First pass on data held now:*
  * Slam point sequences 2011–21 (`predictability_diagnostic/stage2_pbp_points.parquet`, 9,948 matches; AO/RG to 2021, W/USO to 2021 used).
  * Consecutive-round pairs, about 1–2 days apart: the best setting for carry-over.
* *Residuals:*
  * per set, serve and return points against `stage3_ratings` p_serve (pre-match);
  * women: set 2 (late) against set 1 (early);
  * men: set 3 (late, always played in best of five) against set 1.
* *Target:* the next round's serve points won (binomial, from the Stage 0 box score), with offset at its own pre-match p_serve, plus box-score form.
* *Primary statistic:* Δ = [β(late) − β(early)] forward − the same in reverse time (the *previous* round's serve points regressed on this match's residuals). This removes measurement-quality differences, such as noisier first sets.
* *Controls:*
  * days gap; previous-match length;
  * retirements excluded;
  * clusters by player.
* *Pass rule:* Δ > 0 with an interval excluding 0. Then replicate on the unified table in 2022–24: WTA log, marcosjn2, Infosys and SofaScore, all levels. If not, **close carry-over (B1 and B2)**.

**G2: in-play reaction (60, after redesign).**

* *Pilot:*
  * explore half only: WTA Sep 2025 – Mar 2026 from the event log's millisecond clock, plus AO 2026 (entry-time clock; drop out-of-order stamps);
  * Polymarket minute mids (spread ≤ 10¢) and fills.
* *Tests:*
  * (a) Δlogit(mid) in the 1–3 minutes after a break or set end, regressed on Δlogit(fair). The fair value comes from an iid Markov engine at serve rates calibrated to the pre-match price.
  * (c) Drift 5–15 minutes after runs.
  * Both are price-only.
  * The **pre-event price is the last minute strictly before the earliest possible start** of the triggering point (the previous point's end).
* *Controls:*
  * clock checks (out-of-order stamps, day jumps);
  * validated starts;
  * clusters by match.
  * The outcome-based efficiency test (b) waits for pre-registration and the confirm half.
* *Pass rule:* a mis-reaction or drift ≥ 1¢ with an interval excluding 0. Then measure in-play spreads from PMXT books (acquisition) and run the confirm half. **Nothing from G2 feeds pre-match design.**

**E3: real rest hours (58).**

* *Build:*
  * rest_h = target start − end of the previous match (last-point clock, else start + minutes);
  * flags: finish after 23:00 local, rest_h < 20, resumed overnight;
  * all residualised on the day gap, `sets_14d` and minutes over 14 days.
* *Test:* residual screen restricted to the **next-day subset** (gap ≤ 1 day), pre-registered.
  * Men: discovery 2014–21.
  * Women: discovery 2019–21, where start times are 85–96%.
  * Replication 2022–24.
* *Caveat:* backtests use the actual start; a bet at 24 h would need the scheduled slot, which is not held historically (G4). **No G1 move test without order-of-play data.**
* *Pass rule:* a subset gain with an interval excluding 0 in both windows.
* *Power (inferred):* a 5–10% subset means a within-subset detectable gain of about 8–16 mLL. Expect a tie.

**E2: within-match fade (56).**

* *Women, now:* from the WTA log, per-point slopes of first-serve-in, double-fault rate and own-serve tempo against point index, with state controls (pressure class, tie-break, serve number, deuce or ad court). Excess over tour norms for matches of that length, norms frozen ≤ 2021.
* *Men:* Slam speeds ≤ 2021 (discovery) and Infosys + Slams 2022–24 (replication).
* *Target:* the next match's serve points won (binomial, as in B1), with the reverse-time placebo.
* *Controls:*
  * exclude retirements;
  * the last match's length;
  * the existing speed-change input (men).
* *Pass rule:* as B1.
* *Deployment note:* even if the men's speed fade passes, non-Slam 2025–26 speeds do not exist (H1).

## 3. Holdout discipline

**I agree with the coordinator's position, with four refinements.**

1. **I1 can use more than 2022–24.** Stored out-of-sample forecasts exist for 2014–21 (`meta_stack/walkforward.parquet`, 34k matches; observed). So I1 should be discovery 2015–21 and replication 2022–24. Restricting it to 2022–24 alone wastes the cleaner discovery window.
2. **E1's discovery starts in June 2019, not 2020.** The event log is complete from 4 June 2019 (1,644 matches): discovery 2019-06 – 2021, replication 2022–24.
3. **The Polymarket tracks do not contaminate the model's close-based holdout, as long as two rules hold.**
   * **G1 (price-only).** M = logit P(close) − logit P(24 h) is a price, not an outcome. Screening features on it reads no outcome noise, so the later close-based test of the model on 2025–26 stays clean. If anything, it is biased against: a feature the close absorbed has less left beyond the close.
   * **The catch is the 24-hour outcome test.** The close predicts outcomes better than the 24-hour price. So a feature selected for "price moved toward it" on some matches will look good against the 24-hour price **on those same matches**. Hence the time split: explore Sep 2025 – Mar 2026; freeze; confirm Apr – Oct 2026. Any 24-hour *outcome* test runs on the confirm half only.
   * **G2 and G3.** Tests (a) reaction and (c) drift are price-only: explore half, then the confirm half after freezing. Test (b) efficiency reads 2025–26 outcomes. It is legitimate **for in-play questions only**: explore half until pre-registration, then the confirm half once.
   * **Firewall.** The brainstormer's "G2 sets the prior for D1 and D2" is precisely the contamination channel. No in-play result may shape a pre-match feature, constant or arm until the pre-match pre-registration is frozen.
4. **Two studies share one closed holdout.** `feature_interactions` and this study each plan "one pre-registered test" on 2025–26. Coordinate the date and the code, and apply a Holm correction over **all arms of both studies' final tests**. Otherwise the shared holdout is used twice without correction.
   * 2022–24 is not virgin for the base model, whose per-season results are published, but it is virgin for these *new* features. Replication there remains meaningful.

**What each top idea may and may not look at:**

| Idea | Outcomes it may read | Non-outcome data it may read | It may not |
|---|---|---|---|
| I1 | Stored forecasts and results 2015–21 (discovery), 2022–24 (replication) | – | read 2025–26 rows; add splits after seeing 2022–24 |
| E1 | Women 2019-06 – 2021 (discovery), 2022–24 (replication), for both mechanism and market | Flag counts and coverage for every year, 2025–26 included (counts only) | tune the expected-rate baseline on ≥ 2022; read 2025–26 outcomes |
| E1 at 24 h (G1) | none | Polymarket moves: explore Sep 2025 – Mar 2026, confirm Apr – Oct 2026 | run a 24 h outcome test on the explore half |
| D1 | 2015–21, 2022–24 | G1 moves as above | read 2025–26 outcomes; tune K after 2018 |
| B1 / E2 | Slam pbp, Sackmann strings and marcosjn2 ≤ 2021; unified table 2022–24 | Feature distributions in any year | use 2025–26 next-match outcomes |
| E3 | 2014–21 (men), 2019–21 (women), 2022–24 | – | build a 24 h test on realised start times |
| I2 | WTA log and Slams 2019–24 (in-match results) | – | read 2025–26 |
| A1 recovery gate | none (the career truth is a statistic), built from ≤ 2024 | everything ≤ 2024 | include 2025–26 in the truths |
| G2 / G3 | (b) explore half after pre-registration; confirm half once | (a), (c) explore half, then confirm half | feed pre-match design |
| G4 | **none possible**: no ≤ 2021 discovery exists | price-only moves | any outcome test before the 2025–26 final test or 2027 data |

## 4. The brainstormer's anticipated attacks and defences

**E1 (medical log).**

* **"One pre-registered primary, the injury reason (about 4%)": holds for multiplicity, fails on power.**
  * About 400 such matches in replication give a within-subset detectable gain of about 47 mLL (an RMS move of about 15 pp): a near-certain tie.
  * Make the **mechanism** the primary gate (M1 retirement and withdrawal; M2 serve-point residual). For the market test, use **"treated"** (about 16% of matches; about 1,500 flagged in replication; detectable gain about 12 mLL) as primary and the injury reason as secondary.
* **"Mechanism first, without the market": holds.** It is the right design. But next-match outcomes are outcomes, so it stays ≤ 2024.
* **"Survivorship handled within next-match players": does not hold fully.** The worst-injured *withdraw*, and walkovers are not in the frame, so the measured effect is diluted toward 0.
  * Count withdrawals as an M1 endpoint.
  * Stratify by the previous match's result: an in-event next round after a win is a different population from the next event after a loss.
* **"Priced in is the hypothesis": holds as logic.** But the owner's "a null is a process flaw" frame does not require running an under-powered market test. The mechanism gate is what makes a null informative.
* **"Cheapest data; T3 tests 24 h": holds on cost.** The explore-half sample is small (about 100–150 flagged women's matches with both prices), so it is directional only.
* **An attack it did not anticipate: missingness.**
  * Logs exist only for WTA tour, 125 and qualifying draws: never Slams or ITF.
  * "No flag" therefore mixes "no treatment" with "previous match at a Slam or ITF".
  * The NaN or zero pattern encodes the previous event's level. This needs the missingness-indicator placebo, and an explicit three-state coding: flagged, unflagged-logged, unlogged.

**G2 (in-play).**

* **"A diagnostic first": holds.**
* **"Clock faults are documented": partly.**
  * Listed faults can be dropped.
  * The general problem remains: minute mids cannot separate a 5-second reaction from a 55-second one.
  * Look-ahead is a real risk if a point's stamp lags play. Use the price strictly before the point's earliest possible start.
* **"Fills beside mids": partly.** Trades run only to 21 Sep 2026, and fills alone do not give the spread. In-play costs are unmeasured until PMXT books are read (an acquisition lead).
* **"An enormous sample": overstated.**
  * Point–price pairs within a match are dependent. Outcome tests have about 2,400 matches (about 75% women, about 500 men).
  * Drift tests do have tens of thousands of game increments: a detectable drift of about 0.3¢ per game.
* **"A null closes in-play momentum": partly.** It closes mis-reactions above about 0.5–1¢ at minute grain. It cannot speak to sub-minute latency edges, which belong to courtsiders anyway.
* **"It informs D1 and D2": rejected.** That is the holdout leak (§3).
* **Missing from its list:**
  * the owner bets pre-match;
  * point feeds are collected after events under a "non-commercial research" basis, so live use needs an owner decision;
  * Polymarket's resolution rules for retirements.

**B1 / B2 (carry-over).**

* **"A different estimand, state rather than trait": holds.** It is genuinely untested.
* **"Always-played sets avoid stopping-rule selection": holds for the stopping rule.**
  * It opens another confound: if first sets are noisier (warm-up, slow starts), the late set measures current level better, so β(late) > β(early) would appear without any carry-over.
  * The reverse-time placebo removes this, so make it **part of the primary statistic** (the difference of differences), not a side check.
* **"B2's likelihood inference is immune to the stopping rule": correct in principle (non-informative stopping), but beside the point.**
  * With millions of points, σ²_pt > 0 will be "significant" from any within-match non-stationarity: score-state effects (servers are slightly worse on big points), new balls, conditions.
  * That says nothing about momentum carrying over.
  * Its stop rule, "if σ²_pt's interval includes 0, B1 closes too", is **logically wrong**: within-match drift (σ²_pt) and across-match carry-over (σ²_day) are different parameters. B2 is parked behind B1.
* **"Stage C observed within-match shifts beyond iid": holds** (men's third set alone: 0.014 against 0.001 points per point, real against replay). This is the best motivation in the list.
* **"One pre-registered test closes it": holds**, because the serve-point target is sensitive. Use discovery ≤ 2021 and replication 2022–24.

**D1, the runner-up attack ("points in disguise").**

* **The framing defence holds:** it is a luck residual with a pre-set sign.
* **The substance is mostly already tested** (§5), and the model already holds both halves: results-based Elo and points-based ratings, plus games-weighted Elo for margin. TabPFN can form "results minus points" itself.
* What is genuinely new is only:
  * the **in-event window** (luck in this tournament's earlier rounds);
  * the explicit sets-and-games decomposition (register A05);
  * the **24-hour retail** angle.
* That justifies a residual screen against the model's own forecast plus G1, not an arm.

## 5. Prior evidence the list under-uses

* **D1 against earlier tests** (old harness, given the market; positive = feature better):
  * Stage C "results above Elo's expectation": men −0.04 [−0.10, +0.01], women −0.06 [−0.15, +0.04], ties.
  * Stage 4 tiebreak record (52 weeks): men −0.02 [−0.12, +0.07], women +0.03 [−0.13, +0.19]; decayed: men −0.04 [−0.10, +0.03], women −0.01 [−0.12, +0.11]; all ties.
  * Big points on return: men −0.05 [−0.13, +0.03], women −0.09 [−0.27, +0.08], ties.
  * Women's break points above expectation: −0.05 to +0.01, ties (men: no spread, so a constant).
  * Stage 4 "luck as a correction to Elo": the tiebreak record helps *given Elo* (+0.14 / +0.23, negative coefficient), but not given the market.
  * Games-weighted Elo given the market: −0.03 / −0.03.
  * **Does D1 survive?** As a 52-week or decayed luck record, **no**: already a tie. What survives is the in-event window and the 24-hour angle. Expect the residual screen against the model's own forecast to be about 0. Run it because it costs an hour and closes A05, not because a gain is likely.
* **E3 against the frontier's "recovery context"** (observed gaps, retirement losses and coverage, jointly with strength):
  * over market plus profile: men −0.069 [−0.218, +0.081], women −0.240 [−0.487, +0.006], ties, women leaning worse;
  * over Elo: +0.240 [−0.069, +0.548] / +0.143 [−0.206, +0.492], ties.
  * Day-level rest is therefore covered and null. E3's only new content is **hours within the next-day subset**: late finishes, overnight resumptions, same-day doubles.
  * It survives only as a pre-registered subset test, residualised on day gaps and load, with dilution stated.
* **The frontier register entries** (`research.md`; all untested, with tested neighbours):
  * **A05** (scoring-conversion residual) is D1. Its neighbours, above, are ties.
  * **B09** (late-match deterioration carried forward: a speed or point-residual slope after state control; "medium; radar calibration, serve selection and score effects") is E2 and B1. Its neighbours are the speed profile (+0.24 [+0.07, +0.41] in 2022–26, better; the change alone +0.14, a tie) and the frontier's own-expected form (over market plus profile −0.036 / −0.131, ties).
  * **B10** (point-state serve effects; "earlier big-point feature already covers part, and rich state cells are sparse") is C2. Pressure excesses are near-luck traits, so C2 stays parked.
  * **C07** (real rest hours, late finish, suspensions, same-day doubles, scheduled start) is E3. Its register note, "target actual start may be unknown at forecast time", is the same G4 issue I flag for the 24-hour test.
* **B3 against the frontier's "reliability / variability"** (between-match residual dispersion):
  * over Elo: +2.022 [+1.077, +2.968] men (better), +0.476 [−0.265, +1.217] women (tie);
  * over market plus profile: +0.232 [−0.038, +0.502] men, +0.077 [−0.114, +0.268] women, ties.
  * It is the closest prior and the best-scoring frontier family against the market, still a tie. B3's within-match version is new, but should be judged against it.
* **The stopping-rule and selection lessons** (Stage C, predictability Stage 2) apply directly to B4, B5, C3 and D2. The replay baseline is required (G5), and the hot-hand finite-sequence bias (Miller–Sanjurjo) applies to B5 and B7.

## 6. Recommendation: build and test four in this session (CPU; GPU only after a gate)

Order by cost × decisiveness. None needs the builder's unified table, which only feeds the replications later.

**1. I1: where the edge lives (about 1–2 h).** *Pre-registration sketch:*

* *Data:* `meta_stack/walkforward.parquet`, `p_base` (4-seed mean) and `p_mkt`.
* *Calibration:*
  * the model: one slope per tour, refitted each season on all earlier out-of-sample seasons, from 2015;
  * the close: recalibrated on each window's training seasons, as in the meta-stack study.
* *Endpoint:* d = LL(recalibrated close) − LL(recalibrated model), mLL, positive = model better.
* *Splits (fixed now):* the five in §2.
* *Windows and test:* discovery 2015–21; replication 2022–24. Holm over 5 contrasts; four-week blocks.
* *Decision:* a contrast ≥ 1 mLL that is Holm-significant in discovery and has the same sign in replication reorders the work: later rounds or short rest point to state features, uniform gains to neither. Otherwise "uniform", and no reprioritisation.
* *Stated before running:* this is the 54-input predecessor. 2025–26 is not read.

**2. E1 mechanism gate, with E2-women markers in the same pass (about half a day to a day).** *Pre-registration sketch:*

* *Data:* `data/dump/points/wta/events/` (or the builder's WTA events table when it lands), mapped to the women's frame through `match_timing/links/wta_api.parquet`.
* *Flags:* as in §2, coded in three states (flagged, logged-unflagged, unlogged).
* *Primary:* M1, next-match retirement or withdrawal, as a risk ratio; M2, next-match serve-point residual, binomial with offset `stage3_ratings` p_serve.
* *Exposure:* "treated" in the player's previous match within 21 days.
* *Negative control:* toilet break.
* *Secondary (separate family):*
  * the injury reason;
  * E2-women fade slopes (first-serve-in, double faults, tempo) against next-match serve points;
  * with the reverse-time placebo.
* *Windows:* discovery 2019-06 – 2021; replication 2022–24.
* *Decision:* pass, i.e. RR > 1.5 or M2 ≤ −0.5 pp with the interval excluding no effect, the same sign in replication, and the negative control null. Pass leads to a residual market screen and a G1 move screen. Fail closes E1 as a pre-match input, and leaves G3 as a curiosity.

**3. D1 residual screen, plus G1 move screens for D1 and E1 (about a day).** *Pre-registration sketch:*

* *D1:*
  * in-event cumulative and 8-week decayed L_sets and L_games;
  * `stage2_iid` exact model at de-noised day rates; format from the repaired schedule rules; K ≤ 2018.
* *Test:* residual logistic with offset logit(`p_base` out-of-sample), both tours.
  * Discovery 2015–21; replication 2022–24.
  * Two-sided, expected sign negative; placebo shuffled within tour × season.
  * Report the R² against `elo_overall` − `ratings_iid` and `elo_games` to show what the model already spans.
* *G1:* H4 specification on Polymarket.
  * Explore Sep 2025 – Mar 2026; x ∈ {D1 in-event, E1 treated (women)}, with b = logit(the model's no-odds view) as the control.
  * Frozen, then confirm Apr – Oct 2026.
* *Decision:* a TabPFN arm only if both the replication screen and the G1 confirm half are positive. Otherwise close A05 and D1.

**4. B1 Slam first pass (about a day).** *Pre-registration sketch:*

* *Data:* `stage2_pbp_points.parquet`, 2011–21; consecutive Slam rounds.
* *Residuals:* per set, serve and return against `stage3_ratings` p_serve. Late against early: set 2 against set 1 (women); set 3 against set 1 (men).
* *Target:* the next round's serve points won (Stage 0 box score), binomial, with offset at its own pre-match p_serve, plus box-score form.
* *Primary:* Δ = [β(late) − β(early)] forward − [the same] in reverse time; clusters by player.
* *Decision:* Δ > 0 with an interval excluding 0 leads to replication on the unified table for 2022–24 (all levels: WTA log, marcosjn2, Infosys, Sackmann strings). Otherwise **close momentum carry-over** (B1 and B2) and record it.

**Alternates, if time remains:**

* **I2** (an afternoon; gates B3);
* **the G2 pilot** (explore half; price-only tests (a) and (c); about a day).
* **E3** waits until I1 shows a short-rest or late-round concentration. Without that, its subset is too small to repay the end-time build.

**Not this session:** A1's outcome re-test, B2–B7, C1–C4, D2, E4, E5, G3–G6, H1–H4.

## 7. Data-acquisition leads (ranked by value per cost; suggestions)

1. **Polymarket order books.**
   * Record the CLOB `/books` endpoint for open tennis markets from now on (free, public; a scheduled task under the 6 Oct cadence decision).
   * Read the PMXT archive for 13 Apr – 10 Aug 2026 (about 0.8 TB of range requests, about 6 h).
   * *Why:* in-play spreads and depth are unmeasured, so G2 and G3 cannot be priced net of costs. It also extends the pre-match early-market onsets.
2. **Historical order of play and scheduled start slots** (tournament daily schedules, Wayback captures of order-of-play pages, any source with scheduled times).
   * *Why:* E3's 24-hour angle and any "information arriving between 24 h and the close" test need the slot known at 24 h, not the realised start.
   * *Cost:* unknown; a scoping session first.
3. **A Polymarket totals and handicaps census** (market list, volumes, prices for 2026; free, minutes).
   * *Why:* G6 rests on robust structural facts, such as real men's matches playing 0.379 tie-breaks per match against the iid replay's 0.427, but only matters if those markets have depth.
4. **Keep TDI's weekly forward capture running.** It is the only men's non-Slam per-point clock source, and the in-play men's sample is only about 500 matches.
5. **Staging Sackmann's point strings** (on disk; the builder lists `sackmann_pbp`). Not an acquisition, but the highest-value cheap step: it fills the men's 2013–15 training window at about 93%.
   * Also fix the data-map catalog's level list for this source.
6. **SofaScore event metadata for marcosjn2's ids (H2):** about 48k requests, about 27 h.
   * Adds start times and set durations, 2015–25; fills women's 2013–18 start times (68–71% now).
   * Only if E3 passes; check scope under the 23 Sep SofaScore decision.
7. **ATP non-Slam serve speeds 2025–26 (H1):** only if the men's speed fade replicates on 2022–24.
   * The known routes need decryption (outside the 24 Sep limits) or break atptour.com's terms, so it is probably infeasible without an owner decision.
8. **A live point feed for in-play (H3, second half):** only after a positive G2 confirm half. It needs licensing or an owner decision, since feeds are collected after events today.

