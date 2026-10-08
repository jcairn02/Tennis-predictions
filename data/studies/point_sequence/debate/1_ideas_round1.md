# Brainstorm, round 1: new point-by-point statistics for the best model

Brainstormer agent, 6 Oct 2026. **These are suggestions, not decisions.** Labels: **observed** = I measured it read-only today or it is quoted from a named report; **inferred** = my reading; **suggestion** = a proposal.

**Units and direction.** mLL = milli-log-loss. "Gain" always means **positive = the forecast with the new input is better** (second-named better). A 95% interval that spans 0 is a **tie**. "P(gain)" is my honest probability that the idea shows a gain over the recalibrated close whose interval excludes 0 (2022–2026), not the probability that the information exists.

---

## 0. What I checked before proposing (observed, read-only)

1. **Point coverage of the model's frame.** I joined `data/studies/surface_ios/base_frame.parquet` (63,737 matches) to the match-timing link tables, and compared marcosjn2's main-draw counts with the frame's matches per year.

   | | Men | Women |
   |---|---|---|
   | 2013–15 | 91–95% (Sackmann point strings, `pbp_copy` link) | 3–9% linked (charts); Sackmann's Slam pbp adds about 20 points (Slam main draws are about 21% of women's frame matches) |
   | 2016–17 | marcosjn2 main draw ≈ 64–71% of frame matches; charts 6–8% | marcosjn2 ≈ 45–57% |
   | 2018 | no men's odds file (not in frame) | marcosjn2 ≈ 63% |
   | 2019–21 | marcosjn2 ≈ 76–88%; Slam feeds 5–10%; Infosys 14% (2021) | WTA umpire log 54% / 63% / 75% (2019/20/21); marcosjn2 64–81% |
   | 2022–26 | linked sources 96–100% (Infosys 76–79% in 2022–24; SofaScore 89–91% in 2025–26; TDI 15% of 2026) | linked 98–99% (WTA log 77–99%) |

   Women 2013–15 is the one large hole (mostly imputation). The marcosjn2 rows are inferred from counts. The union still has to be measured once the table is built (A1).
2. **The WTA umpire log** (`data/dump/points/wta/events/`), singles main draw and qualifying, 2021–2026. Share of matches with each kind of record:
   * medical treatment: 15.5–16.7%;
   * physio called: 15.8–17.4%;
   * explicit reason Injury, Illness or Heat: 3.5–4.9%;
   * toilet or clothing break: 31–41%;
   * time violation: 4.8–7.6%;
   * code violation: 4.0–5.4%;
   * suspension: 7–12%.

   Every treatment record names the player. Every point carries a timestamp to the millisecond and the serve it was played on.
3. **Exact start times** (Flashscore, SofaScore and WTA links). Men: 98–100% of frame matches in 2013–2025 and 89% in 2026. Women: 68–71% in 2013–18 and 83–100% in 2019–25. The SofaScore editions table also has set durations (`time_set1..5`).
4. **Polymarket in play.** `line_sharpening/markets.parquet` holds 33,822 singles markets of 2026. A validated start of play exists for 86–99% of them, depending on level. The median in-play window is 1.7–2.0 h. Minute prices run through play, and fills are timestamped.
5. **marcosjn2** holds only the point winner, the server, and the game and set structure: no clock, serve number, ace or double fault. Its `event_id` is a SofaScore id.

**The lesson from earlier work (inferred)** is that stable traits have never beaten the close: style, clutch play and the Stage 1–3 sequence statistics all failed. Everything that has hinted at an edge over the market is a recent **state**:
* the 2-week box-score form (already in the model);
* 14-day workload: +0.23 / +0.29 mLL given the market, in the old harness;
* the men's recent serve-speed drop: +0.24 [+0.07, +0.41] mLL given the odds in 2022–26.

So I rank last-match state signals above new traits. I also rank tests with sensitive targets above match outcomes:
* the next match's serve points, about 145 outcomes a match;
* the price move from 24 h to the close.

On match outcomes, edges of 0.25 mLL or less are close to invisible. Stage 3's oracle detected 0.25 in only 0–70% of draws.

---

## 1. Shared test ladder (each idea refers to T0–T4)

* **T0. Build and audit.**
  * Measure coverage by tour and year against the frame, and replay every match to its official score.
  * Use own-history features in order. Anything cross-player goes on the leak-proof clock (`timing.parquet`) and passes `src/eda/match_timing/probe.py`.
* **T1. Signal at all?**
  * *Traits:* split-half reliability against the pure-luck replay (`stage2_iid.simulate` at de-noised day rates), with the same number of matches per half.
  * *States:* does the feature predict the next match's serve and return points won? Use Stage 3 part A's binomial walk-forward, given the ratings and box-score form. This is the most sensitive outcome test the repo has.
* **T2. Market screen (CPU only).**
  * A walk-forward logistic on logit(close) + feature, and on logit(the current best's calibrated forecast) + feature.
  * Matches from 2016 (2013 where covered) to 2026; 4-week block intervals; 2022–26 reported separately.
  * Constants are frozen before T2. Every row counts toward a family-wide multiplicity line.
* **T3. Timing screen.** The H4 design on Polymarket 2025–26 main-tour matches: regress M = logit P(close) − logit P(24 h) on the feature, controlling for the model's no-odds view. A slope above 0 means the price moves toward the feature after 24 h. That is the owner's operating point, and a price move is much less noisy than a result.
* **T4. TabPFN arm.** The current best plus 1–3 inputs, run in the surface_ios harness (five expanding windows, slope per tour), scored at the close and at the 24 h price.
  * Never 10+ inputs unpenalised: Stage 3 measured about −0.5 mLL of pure fitting cost per 10 inputs.
  * A feature that is dense only from 2022 needs its arm or logistic started where the data become dense, since the 2013–21 training window would see it mostly missing.

---

## 2. The ideas (31)

### A. Foundation

**A1. Unified point-sequence table, then a depth re-test of the sequence family** (foundation / streaks)
* **Def:** one row per point for every frame match from every held sequence source, keyed to Stage 0 ids.
  * *Fields:* set, game, point index, server, winner, tiebreak flag, score before the point (server first), and Klaassen–Magnus (KM) importance at tour-average rates (`stage2_pbp` already computes it).
  * *Where present:* serve number, first-serve fault, ace/double fault, start and end clock, speed, rally length.
  * *Source priority:* official feeds (WTA log, Slam feeds, AO, TDI) > Infosys > Sackmann Slam files > SofaScore > marcosjn2 > Sackmann point strings.
  * *Replay rules:* drop marcosjn2's trailing tiebreak point; apply the WTA log's correction rules; drop TDI's stopped games.
  * *Statistics:* recompute Stage 1's six sequence statistics and add three: blown-lead rate (a set lost after leading by a break), consolidation within two games, and KM-weighted serve and return excess.
  * *Pre-match:* Stage 2's three memories and three kinds; K re-estimated on the deeper data; the IOS version on the leak-proof clock.
* **Baseline:** the pure-luck replay of the same statistic.
* **Data:** the table above; men's training seasons mostly covered, women's 2013–15 imputed.
* **Why the price may miss it:** it may not. The case is Stage 3's own caveat.
  * Up to 1–2 mLL could hide in noisy statistics, which pre-match features carried at only 15–34% of the truth because the history was "mostly Slams".
  * marcosjn2, the WTA log and SofaScore add every tour-level match outside the Slams, roughly 3–5× the per-player sequence history (inferred).
* **Use:** an enabler for B, C, D2, E2 and G2, and a pre-match re-test.
* **Prior evidence:** the sequence family is a set of traits (split-half 0.31–0.52) with no gain over the close (best rows about 0.0–0.05; the ridge profile about 0).
  * Stage 3's planted-edge test covered only one sequence statistic, holds right after breaking. For men it already rules out an edge of 0.5 or more.
  * So the upside lies in the untested ones (break back, serving for the set, pressure, KM).
* **Test:**
  1. Build the table. The replays exist in `marcosjn2_links.py`, `verify_wta.py`, `verify_tdi.py` and the Slam checkers.
  2. Rerun Stage 3 part C's recovery (corr² of the pre-match feature with the career truth, by depth quarter).
  3. If corr² does not rise toward 0.5, the "thin data" excuse is closed for this family. Otherwise run Stage 2's rows and the ridge profile, pre-registered.
* **Prior:** P(gain) about 5%; size +0.1 to +0.2 mLL. Its value is as infrastructure and as a closure test.

### B. Momentum and streaks proper

**B1. Finishing form: does the end of the last match carry into the next one?** (momentum)
* **Def:**
  * *Residuals:* per player-match, the serve-point and return-point residuals in set 1 (R1) and set 2 (R2), against the pre-match iid expectation (ratings_iid rates). Both sets are always played in best of three; use sets 1–3 in best of five.
  * *Feature:* the next match (within 14 days) gets "finishing form" R2 − R1, plus R2 alone.
  * *Shortcut:* IBM's per-point momentum score in the Slam archive is a quick proxy at the Slams.
* **Baseline:** under iid, sets 1 and 2 are exchangeable, even given who won the match, so they must predict the next match equally; the replay confirms it.
  * Using only always-played sets avoids the stopping-rule selection that made Stage C's late decline mostly selection.
* **Data:**
  * *First pass now:* Stage 2's Slam point-by-point (2011–24) and Stage 1's table (38k matches).
  * *Full run:* A1's 96–100% in the test window.
* **Why the price may miss it:** Stage C found real within-match level shifts beyond iid (men's third set alone: 0.014 against 0.001 points per point, real against replay).
  * If they carry across days, the end of a match is the freshest read of form.
  * Box-score form and the market weight the whole match equally.
* **Use:** a diagnostic, then one pre-match input. In-tournament next-day matches are where freshness should matter most, so the gap since the last match is a dose–response check.
* **Prior evidence:** untested. Stage C's late decline was a career trait (no sign); this is state carry-over, a different estimand.
* **Test (T1):** regress the next match's serve points won on R1 and R2 (H0: β(R2) = β(R1)). Placebo: run it backwards in time. If β(R2) ≤ β(R1), close momentum carry-over across matches, together with B2.
* **Prior:** P(β(R2) clearly > β(R1)) about 25%; P(gain) about 8%; size +0.05 to +0.2.

**B2. A point-level dynamic serve/return rating with within-match drift** (momentum, model-based)
* **Def:**
  * *Model:* latent serve s and return r per player, as random walks with variance σ²_pt per point played and σ²_day per day; P(server wins the point) = logistic(s_server − r_receiver + tour × surface terms).
  * *Fit:* a Kalman / expectation-propagation filter over A1's table on the leak-proof clock, with hyperparameters by maximum likelihood on 2013–18.
  * *Inputs:* the filtered state turned into an iid match probability, plus the state's uncertainty.
* **Baseline:** σ²_pt = 0 nests "no momentum".
  * The likelihood-ratio test is decisive and is unaffected by the stopping rule: the match ends on observed points only, so likelihood inference ignores it.
  * That is the selection trap the earlier "late minus early" contrasts fell into.
* **Data:** as A1. Cross-player, so `probe.py` is mandatory.
* **Why the price may miss it:** as B1, with optimal weighting. It also serves as G2's in-play prior.
* **Use:** a pre-match input and the in-play fair value.
* **Prior evidence:** no point-grain dynamic model exists in the repo (IOS, TTT and Elo are match grain). The owner treats ratings as priced in, so score it only as "drift carried over": the same filter with σ²_pt = 0 first, then the close.
* **Test:** an ML fit of σ²_pt on one season. If its interval includes 0, stop: it closes B1 too.
* **Prior:** P(σ²_pt clearly > 0) about 35%; P(gain) about 6%; size +0.05 to +0.2.

**B3. Within-match volatility ("streakiness") as a variance input** (streaks / calibration)
* **Def:**
  * *Measure:* per player-match, the overdispersion of serve (and return) performance across service games, D = Σ(won − n·p̂)² / Σ n·p̂(1 − p̂), with p̂ the match rate. Or the likelihood ratio of a two-state hot/cold hidden Markov model against a constant rate.
  * *Trait:* the shrunk mean of (D − D_replay) over 52 weeks or the career.
  * *Inputs:* vol_A + vol_B, entered as an interaction with |logit p_close| ("flatter than the price"), and vol_A − vol_B.
* **Baseline:** the replay (D_replay ≈ 1); reliability against the replay's.
* **Data:** A1. Diagnostic I2 comes first.
* **Why the price may miss it:** prices are calibrated on average. If volatility is a player trait, calibration should be heterogeneous.
  * The women's gain is "mostly calibration" (brief §2).
  * The women's points share decides matches less than iid luck predicts (log loss 0.118 against 0.103; predictability Stage 2). That is the one open lead pointing here.
* **Use:** a pre-match calibration interaction, and totals (G6).
* **Prior evidence:**
  * Point-to-point serial dependence is not a trait: serving after a lost point is at chance on both tours.
  * Between-match residual dispersion (the frontier's "reliability / variability") gained +2.02 over Elo for men but only +0.23 [−0.04, +0.50] over market and profile (a tie).
  * Different here: within-match clustering, used as a price interaction, not as a mean.
* **Test:**
  1. I2.
  2. T1 reliability at 20+ matches per half (thousands of players with A1's depth).
  3. T2 with logit(p_close) × (vol_A + vol_B); the expected sign is negative.
* **Prior:** P(trait beyond luck) about 30%; P(gain) about 7%; size +0.05 to +0.3, mostly women.

**B4. Set-transition profile: slow starters, and the response to losing a set** (momentum, in play)
* **Def:** per player-match, the set-1 residual minus the later-set residual (slow start). Response = the residual in set k+1 after losing set k, minus after winning it. Shrunk into a career trait.
* **Baseline:** the replay, which reproduces which sets get played.
* **Data:** A1.
* **Why the price may miss it:** the in-play price after set 1 uses the score and pre-match strength, not a player's tendency to rebound. Pre-match it adds about nothing, because set averages already count it.
* **Use:** in play (Polymarket at the end of set 1); possibly best-of-five Slams.
* **Prior evidence:** none at set level. The game-level analogues (break back, hold after breaking) are traits with no pre-match gain.
* **Test:** T1. Then, for 2026 set-1 losers, regress the result on logit(the Polymarket mid at the end of set 1) + trait.
* **Prior:** P(trait beyond luck) about 20%; P(in-play edge after costs) about 5%; pre-match about 0.

**B5. Swing games: the next game after an escape or a missed chance** (momentum)
* **Def:**
  * *Escape:* after holding serve from break point down, the player's return residual in the next game.
  * *Missed chance:* after failing to convert break points, the player's serve residual in the next game (the hangover).
  * *Trait:* shrunk; also a per-match swing count.
* **Baseline:** the replay.
* **Data:** A1. A first pass works on Stage 1's table.
* **Why the price may miss it:** a systematic psychological swing is in neither results nor box scores, and in-play prices treat games as independent.
* **Use:** mainly in play.
* **Prior evidence:** break back (0.38 / 0.52) and hold after breaking (0.43 / 0.49) are traits with no pre-match gain; these triggers are new.
* **Test:** T1 (an hour).
* **Prior:** P(trait beyond luck) about 15%; P(gain) about 2%.

**B6. Rally recovery: the point after a long rally** (fitness)
* **Def:** P(win the next point | the previous rally was 9+ shots) − P(win | ≤4 shots), on own serve and on return. The next point has the same server within a game; adjust for the score state and for who won the rally. Kept as a trait and as a last-match state.
* **Baseline:** a within-match permutation of rally lengths among points with the same server and score class (the replay has no rallies).
* **Data:** Stage 1's ≈30k matches with rallies (Slams, Infosys 2021–24, TDI, charts, Hawk-Eye). Men 2022–24 dense; women Slams and charts only.
* **Why the price may miss it:** a fitness signal absent from box scores.
* **Use:** pre-match and in play.
* **Prior evidence:** none (Stage 1 had "after a lost point" only).
* **Test:** T1 on `stage1_points_*.parquet`.
* **Prior:** P(gain) about 3%.

**B7. Tilt signature: losing runs × tempo** (temperament)
* **Def:** the excess point-loss rate after two or more consecutive lost points (against iid at the state). Split by whether the next point started faster than the player's own median gap (rushing). Add violations after runs (WTA log).
* **Baseline:** the replay; the player's own tempo norm.
* **Data:** point clocks from the WTA log (women, 2019–26), TDI 2026 and the Slam feeds.
* **Use:** in play; pre-match small.
* **Test:** T1 on the WTA log.
* **Prior:** P(gain) about 2%.

### C. Pressure and leverage

**C1. KM leverage on return and serve beyond luck, on every tour** (pressure)
* **Def:**
  * *Measure:* per player-match, the importance-weighted share of return (and serve) points won minus the plain share. Importance comes from the score at tour-average rates.
  * *Trait:* a shrunk 52-week or career mean, minus its replay expectation.
  * *Variant:* an IOS offence/defence version on the leak-proof clock.
* **Baseline:** three point-by-point replays (Stage 2 pbp).
* **Data:** A1.
* **Why the price may miss it:** honestly, it mostly cannot. Results-based ratings and the market already see big-point skill through results. Help is plausible only where results are few.
* **Use:** pre-match.
* **Prior evidence:**
  * Big points on return persist beyond luck at the Slams (0.21 / 0.19 at 10+ matches per half; 0.45 / 0.32 at 20+). On serve, nothing beyond luck.
  * Stage 1's crude serve-side pressure excess: 0.17 (men) / chance (women), and no gain.
* **Test:** T1 outside the Slams with A1's depth, then T2.
* **Prior:** P(gain) about 4%; size at most +0.1.

**C2. State-dependent serve rates run through the scoring engine** (pressure)
* **Def:**
  * *Model:* a hierarchical logistic per player of serve points won by state class: break point against, game point for, 30-30 or deuce, tiebreak, serving for the set or match. Random effects are shrunk to the tour.
  * *Input:* plug the state effects into the exact Markov match model; Δ = logit P(match with state effects) − logit P(match, iid at the same average rates). One input.
* **Baseline:** Δ = 0 with no state effects; the replay.
* **Data:** A1.
* **Why the price may miss it:** earlier pressure features entered raw excesses linearly. The engine weights them by how often each state occurs in this matchup: a big server rarely faces break points.
* **Use:** pre-match.
* **Prior evidence:** Stage 1–2 pressure excesses; B10 in the frontier register (untested).
* **Test:** T1, then T2.
* **Prior:** P(gain) about 3%.

**C3. Coasting index: leverage-filtered strength** (effort allocation)
* **Def:** per player-match, the residual on competitive points (importance above the match's 30th percentile) minus the residual on dead points (set decided, e.g. down 1-5). Shrunk into a trait.
* **Baseline:** the replay.
* **Data:** A1.
* **Why the price may miss it:** games-weighted Elo (`elo_games`) and the points aggregates in the model read garbage-time points literally, so a player who coasts in lost sets is under-rated by them. Retail prices follow scorelines.
* **Use:** pre-match; totals.
* **Prior evidence:** none.
* **Test:** T1; check its correlation with the gap between results-based and games-based Elo; then T2.
* **Prior:** P(gain) about 4%.

**C4. Matchup products of pressure and volatility** (matchup)
* **Def:** antisymmetric products like the model's prod_*: A_lev_ret × B_lev_srv − B_lev_ret × A_lev_srv; volatility × serve dominance.
* **Gate:** only if C1 or B3 passes T1.
* **Prior:** P(gain) about 2%.

### D. Conversion and narrative (market-bias tests, not ratings)

**D1. Conversion luck: recent results against what the points earned** (market bias)
* **Def:**
  * *Per past match:* L_sets = sets won − E_iid[sets], and L_games = games − E_iid[games], exact from the day's serve rates (`stage2_iid`). Components: tiebreak luck and break-point luck. Point-by-point adds "timing luck" (important points won beyond the iid share).
  * *Pre-match:* decayed sums over the current event (the tournament run) and over 8 weeks, shrunk; A − B.
  * *Sign:* expected negative given the price (the market over-credits lucky results); tested two-sided.
* **Baseline:** the iid expectation (mean 0 by construction); the replay for its noise.
* **Data:** box scores for every frame match (100%, no imputation); the point refinement on A1's coverage.
* **Why the price may miss it:** results drive rankings, Elo and narrative, and a title run built on tiebreaks looks like form. The retail-heavy 24 h Polymarket price is the likeliest place. The model has results-based and points-based inputs, but no explicit recent luck.
* **Use:** pre-match; 24 h timing.
* **Prior evidence:** A05 in the frontier register (untested). Tiebreak and break-point over-performance are luck, and a good tiebreak record predicts slightly worse results given Elo (predictability Stage 2).
* **Test:** T2 on 2013–26 (≈63,700 matches; in-tournament window first), then T3. Frame it as a test of the market's bias, never as a points rating.
* **Prior:** P(gain) about 10%; size +0.05 to +0.2, larger against the 24 h price.

**D2. The drama of the last match: max adversity, match points saved, leverage load** (narrative)
* **Def:** an in-match win-probability path from the iid engine, with serve rates implied by that match's closing price (the market's own view of the path). Then:
  * the minimum win probability the eventual winner reached;
  * match points faced and saved;
  * the sum of point importance (drama load);
  * won from a set down;
  * won a deciding-set tiebreak;
  * broken while serving for the match.

  Each player's value enters the next match; A − B.
* **Baseline:** the replay's distribution of the same quantities among winners at the same pre-match odds.
* **Data:** A1 sequences; the previous match's close (main tour; Elo-implied elsewhere).
* **Why the price may miss it:** the market may over-react to "resilience", or under-react to the cost of a saved-match-point marathon. Neither is in the next match's inputs except through sets and minutes.
* **Use:** pre-match; 24 h timing.
* **Prior evidence:** none at market level. Clutch records are luck, so any market reaction to them is bias.
* **Test:** descriptive first (y − p_close by bins of minimum win probability), then T2 and T3.
* **Prior:** P(gain) about 7%; size +0.05 to +0.15.

### E. Physical state in the last match(es)

**E1. WTA umpire log: medical and distress events** (physical state)
* **Def:** per player-match from `data/dump/points/wta/events/`:
  * medical treatment, and physio called (including cancelled);
  * an explicit reason of Injury, Illness or Heat;
  * toilet or clothing breaks (and whether right after losing a set);
  * time and code violations;
  * suspension.

  Pre-match: the last match's (within 21 days) treatment and injury-reason flags; a 30-day decayed count; the opponent's flags; interactions with the last match's result and length.
* **Baseline:** the expected treatment rate given minutes, heat, surface and age; features are the excess. Comparisons stay within players who appear in a next match (mostly winners).
* **Data (observed):** treatment in about 16% of WTA singles matches; the player is named on every record. Frame link share is 0.54 in 2019 and 0.63–0.99 in 2020–26.
  * *Gaps:* no Slam logs, so Slam rounds 2+ and first matches after a Slam are missing (about 10–20% of women's matches, inferred). The men have no source.
  * *Training:* the 2013–21 window holds only 2019–21, so use T2 walk-forward on 2020–26 before any arm.
* **Why the price may miss it:** treatments appear in no score, box score, ranking or model input, and few bettors watch a WTA 250 or 125. Retirement risk, a component of the win probability, rises after an injury treatment.
* **Use:** a pre-match input (women); 24 h timing; in play (G3).
* **Prior evidence:** none (never used).
* **Test:**
  1. Mechanism: the next-match retirement rate and serve-point residual, flagged against unflagged (minutes of work).
  2. T2 on women 2020–26 (≈15k matches with odds, ≈12–15% flagged on either side, inferred). Pre-registered primary: the injury-reason flag, two-sided, expected negative.
  3. T3.
  4. A women's arm with 2–3 inputs.
* **Prior:** P(gain) about 15%; size +0.1 to +0.3 on all women's matches (about 1–2 mLL within flagged matches).

**E2. Fade in non-outcome markers within the last match: speed, first serves in, double faults, tempo** (physical state)
* **Def:** per player-match, the slope over points played of:
  * first-serve speed (first serves in);
  * first-serve-in rate;
  * double-fault rate;
  * seconds between own-serve points.

  Each slope comes from a per-point regression with state controls (pressure class, tiebreak, court side, serve number). It is taken as an excess over the tour slope for matches of that length and over the player's own historical slope.
  * *Fade index:* the standardised sum.
  * *Level drop:* the last match's mean minus the 52-week mean, which is the existing speed lead at match grain.
  * *Pre-match:* the last match's values (within 14 days), decayed.
* **Baseline:** tour and player norms. Markers are not the outcome, so the stopping-rule selection that sank late decline in points won is largely avoided. The late-match mix of pressure points is controlled point by point.
* **Data:**
  * *Speed:* men 2022–24 ≈80–90% of the main tour (Infosys + Slams; exact share to be measured). Men 2025–26 only the Slams (≈15%) plus SirGenkii (Jan–Apr 2025); women Slams only.
  * *First serves in and double faults:* women 2020–26 from the WTA log (near-complete). Men: Infosys 2021–24, Slams, charts, TDI from Jun 2026. Men's non-Slam matches of Jul 2025 – Jun 2026 are missing (SofaScore has no serve number).
  * *Tempo:* the WTA log (women); Slams and TDI (men).
  * *Training:* dense only from 2022 for men, so run T2/T4 on an expanding window that starts where the data become dense.
* **Why the price may miss it:** the shot study's one lead is the men's recent serve-speed drop, +0.24 [+0.07, +0.41] given the odds in 2022–26 and positive every season from 2022. A fade inside the last match is the sharpest form of that physical signal, and it is invisible in scores.
* **Use:** pre-match (men 2022–24 and the Slams; women through first serves and tempo); 24 h timing.
* **Prior evidence:**
  * The change in first-serve speed alone: +0.06 [−0.02, +0.15]. The speed profile in 2022–26: +0.24; ridge +0.12 [0.00, +0.24].
  * B09 in the frontier register is untested.
  * New here: the within-match trajectory, and non-speed markers.
* **Test:**
  * *Men 2022–24:* T1 (does it predict next-match serve points given the ratings, box-score form and the existing speed-change input?), then T2, then a pre-registered arm together with the speed-change input.
  * *Women:* the first-serve and tempo fade from the log, T1–T3.
* **Prior:** P(gain) about 15%; size +0.1 to +0.3 (men).

**E3. Real rest hours, late finishes, overnight resumptions, same-day doubles** (physical state; timestamps)
* **Def:** rest_h = the start of the target match − the end of the previous one. The end is the last point's clock where a feed has one, otherwise start + minutes.
  * *Flags:* the previous match ended after 23:00 local time; rest_h < 20; the previous match was suspended and resumed (two matches in one day); doubles minutes since the last singles match (WTA log, Slam feeds, TDI, Flashscore).
  * *Inputs:* A − B and raw; interactions with age and the previous match's length.
* **Baseline:** days of rest and sets / minutes over 14 days (sets_14d is in the model); the feature is residualised on them.
* **Data (observed):** start times 98–100% for men in 2013–25 (89% in 2026). For women 68–71% in 2013–18 and 83–100% in 2019–25. Minutes come from Sackmann (women sparse before 2016; exact from 2019 through the log), and time zones from match_timing's tz modules.
* **Why the price may miss it:** markets price "played yesterday", rarely hours of recovery or a 2 a.m. finish. The order of play is often published after the 24 h mark, so this is also information that arrives between 24 h and the close.
  * Caution: for a pre-close bet use the scheduled slot, never the actual start.
* **Use:** pre-match; timing around the publication of the order of play.
* **Prior evidence:** C07 in the frontier register is untested. "Recovery context" (gaps in days) ties given the market: −0.07 / −0.24. sets_14d: +0.23 / +0.29.
* **Test:** T2 on 2013–26 (≈60k matches with start times), then T3, then an arm.
* **Prior:** P(gain) about 12%; size +0.05 to +0.2.

**E4. Intensity-weighted load: points, shots, long rallies, metres run** (physical state)
* **Def:** over 14 days and within the current event: points played, total shots, rallies of 9+ shots, distance run (Slam feeds), each as log(1 + x); A − B; residualised on sets_14d.
* **Baseline:** sets_14d.
* **Data:** points played near-full from A1; shots and rallies partial (men 2022–24 good, women Slams only); metres at the Slams only.
* **Why the price may miss it:** sets_14d's gain is partly "still in the draw" (survival), not strain (inferred from Stage 4 and C). Intensity separates the two.
* **Use:** pre-match; Slam best of five, rounds 2–4.
* **Prior evidence:** sets_14d +0.23 / +0.29 given the market; minutes × late decline, no sign.
* **Test:** T2 for men 2022–24 and the Slams; an arm that augments sets_14d.
* **Prior:** P(gain) about 8%; size +0.05 to +0.15.

**E5. Tempo profile: pace, pace under pressure, pace mismatch** (tempo)
* **Def:** the median seconds between own-serve points, net of changeovers, faults and lets (and rally length where known). Pressure pace = break or game point pace − normal pace. Men without point clocks get a coarse pace: set duration / points in the set (Flashscore set durations, ATP to Apr 2025; SofaScore 2025–26). Mismatch = |pace_A − pace_B| × serve dominance.
* **Baseline:** pace norms by event (the shot-clock era), with state controls.
* **Data:** women from the WTA log 2019–26; men per point from the Slams, TDI and AO; men coarse from set durations (Flashscore fill not verified).
* **Why the price may miss it:** it is a style absent from every input, but style has never beaten the close. The state part (slowing down) is in E2.
* **Use:** pre-match (low); heat interaction; totals.
* **Test:** T1 (pace will be highly reliable), then T2.
* **Prior:** P(gain) about 3%.

### G. Market side

**G1. The 24 h → close move screen: point information absorbed late** (bet timing)
* **Def:** for each candidate x (A − B, standardised), on Polymarket main-tour matches of 2025–26, regress M = logit P(close) − logit P(24 h) on x and the model's no-odds view. This is the H4 design: no intercept, 4-week clusters, clean openers and all priced matches.
* **Baseline:** slope 0.
* **Data:** ≈2,600–2,900 matches with both prices; the features exist on about 100% of 2025–26.
* **Why the price may miss it:** early lines are set on visible results, and sharps who watched or modelled the last match move them later. The market already moves 7–10% toward the model's no-odds view (H4 +0.09 to +0.11).
* **Use:** bet timing at 24 h, and a cheap, sensitive screen for every idea here.
* **Prior evidence:** H4 is positive; the line-sharpening money test ties.
* **Test:** minutes per feature.
* **Prior:** P(at least one point-level feature shows a clear positive slope) about 30%. Moves are 1–2¢, so it is worth money only beside a real edge.

**G2. In-play reaction to breaks, runs and set ends** (in play)
* **Def:** align every timestamped point with the Polymarket minute mid and fills of the same match in 2026. The clocks are WTA log milliseconds, TDI UTC, the Slam feeds' `EpochTimeEnd` and AO.
  * *Fair value:* an iid Markov chain from the current score, with serve rates calibrated so the pre-match iid probability equals the pre-match price, updated within the match by a beta-binomial (prior strength fitted on 2013–24 points).
  * *(a) Reaction:* Δlogit(price) over 1–3 minutes after a break, a set end or a run of k points, regressed on Δlogit(fair). A slope above 1 is an over-reaction.
  * *(b) Efficiency:* the result regressed on logit(price) and logit(price) − logit(fair).
  * *(c) Reversal:* price drift over the 5–10 minutes after a run.
* **Baseline:** the fair-value engine; results; staleness checks of mids against fills.
* **Data (observed):** 33,822 singles markets of 2026, 86–99% with a validated start, a median 1.7–2.0 h of play. Point clocks: WTA 2026, ATP and Challengers from 23 Jun 2026 (TDI), the 2026 Slams. The overlap is several thousand matches (inferred).
* **Why the price may miss it:** retail in-play traders react to scores, may chase runs or lag, and the books are thin.
* **Use:** in-play betting, a new venue use. It also sets the prior for D1 and D2: traders who over-react to in-match runs plausibly over-react to last-match narratives.
* **Prior evidence:** none; all Polymarket work so far is pre-match.
* **Test:** one month of TDI and WTA matches plus Wimbledon 2026. Extend `starts_check.py`'s first-point-to-price join to every point, and run (a) on breaks.
* **Prior:** P(a mis-reaction of at least 1¢ at breaks or set ends) about 35%; P(profitable after taker fees, 5% × (1 − p) since July, plus spread) about 10%. Posting rather than taking would change the arithmetic.

**G3. In-play medical events** (in play)
* **Def:** the WTA log's treatment, physio and toilet timestamps against Polymarket minute prices: the price change in the 10 minutes after the call against the fair change from the score, and the result (retirement included) against the price at the call + 5 minutes.
* **Data:** WTA matches of 2026 (and late 2025) with markets; treatments in about 16% of matches, so several hundred events (inferred).
* **Why the price may miss it:** treatments are not in score feeds.
* **Use:** in play.
* **Test:** an event study.
* **Prior:** P(under-reaction) about 25%; P(profitable) about 8%; the sample is small.

**G4. The last match's in-play residual: what the watchers saw** (state from market)
* **Def:** over the player's previous match, the mean of logit(in-play mid) − logit(fair from the score), signed for the player (G2's engine). Positive means traders rated the player above the score, for example on visible condition. Enters the next match as A − B.
* **Data:** 2026 only; ≈1,000–2,000 next matches with prices (inferred).
* **Test:** T2 and T3; directional only.
* **Prior:** P(gain) about 5%.

**G5. Who prices point-level information? Sharp wallets' early flow** (diagnostic)
* **Def:** with the sharp-money study's wallet classes, the net signed sharp flow in a next-match market's first hours, regressed on the previous match's E1, E2, D1 and D2 features.
* **Data:** trades with wallets, Sep 2025 – Sep 2026.
* **Why it matters:** features the informed money already trades on are partly priced; features nobody trades are the candidates.
* **Prior:** P(informative) about 15%.

**G6. Totals and handicaps from point-sequence traits** (new market)
* **Def:** simulate the game total and the set handicap from the model's rates (or rates implied by the winner price), with corrections:
  * tiebreak frequency beyond iid (observed: real men's matches play 0.379 tiebreaks against the replay's 0.427);
  * volatility (B3);
  * coasting (C3).

  Compare with Polymarket's total and handicap prices.
* **Baseline:** iid at price-implied rates.
* **Data:** Polymarket lists these contracts, but their prices were never fetched (data map). The fetch is cheap; outcomes come from scores.
* **Why the price may miss it:** totals depend on variance and on state-dependent play. A market priced iid-like would carry the observed tiebreak excess as a systematic bias.
* **Use:** a new market.
* **Prior evidence:** Stage 3 lists other markets as untested.
* **Test:** fetch 2026; check liquidity; calibrate against iid totals; then add the traits.
* **Prior:** P(totals softer than winner markets) about 20%; P(traits add) about 8%.

### I. Diagnostics (near-free)

**I1. Where does the current edge live?** Split the current best's out-of-sample gain over the recalibrated close (2022–26; +1.30 both tours, positive = model better) by:
* first match at an event against later rounds;
* days since the last match;
* the last match's closeness and length;
* whether the last match has point data;
* tour and level.

It uses only the stored predictions and takes an hour. If the edge sits in later rounds and short rests, state features (E1–E4, D1–D2, B1) are the right bet; if it is uniform, traits are. P(informative split) about 60%.

**I2. Is the women's "points share decides less than iid" real?**
* *Rebuild:* recompute predictability Stage 2's points-share logistic and its replay on the WTA log's own point counts, which replay 98.5% of matches to the official score, instead of box scores.
* *Why:* the Stage 0 audit's P2 found break counts that do not add up in 1.67% of women's box scores, which alone could create the gap.
* *If it survives:* decompose it (B3, B4, serve-state dependence), and B3 becomes the women's priority.
* *Cost:* an afternoon. P(the gap survives) about 50%.

### H. Data-acquisition leads

**H1. ATP serve speeds for 2025–26.** Without them, the speed lead and E2 cannot be tested where the owner bets: non-Slam 2025–26 has neither TDI speeds nor SofaScore speeds.
* *Route:* the ATP Stats Centre files (MatchBeats / Court Vision) need decryption, which is the owner's decision; atptour.com forbids systematic retrieval.
* *When:* if E2 or the speed lead passes on 2022–24.

**H2. SofaScore event metadata for marcosjn2's event ids.** About 48,000 requests, roughly 27 h at 2 s each.
* *Adds:* start times, set durations (coarse tempo) and possibly statistics for 2015–25. It would fill the women's start times of 2013–18 (68–71% now).
* *Scope:* check whether this falls under the owner's SofaScore decision.

**H3. Live capture for in-play.** Only if G2 or G3 is positive:
* record Polymarket order books (the CLOB `/books` endpoint) for open tennis markets;
* a live point feed (Sportradar's widget keeps points 11–18 days; unlicensed; the owner's decision).

TDI's weekly capture already gives ATP point clocks after the fact.

**H4. Weather at match time.** Archived hourly weather by venue, for heat × E1 / E2 / E5. The WTA log already marks Heat treatments and suspensions. Low priority.

---

## 3. Top 8 by expected value of information (promise × cheapness × decisiveness)

1. **E1 – WTA umpire log: medical and distress state.**
   * The data are on disk and staged, and the player is named on every record. Treatments occur in about 16% of matches.
   * It is new information absent from every input, and a test takes about a day: next-match retirement as the mechanism check, T2 on about 15k women's matches, T3.
   * P(gain) about 15%, +0.1 to +0.3 mLL (women).
2. **E2 – Fade in non-outcome markers within the last match.**
   * It is the only idea that extends the one live lead (men's speed, +0.24 [+0.07, +0.41]), and it avoids the stopping-rule selection.
   * Decisive on men 2022–24 through the serve-point target.
   * P(gain) about 15%, +0.1 to +0.3.
3. **I1 – Where the current edge lives.** An hour on stored predictions tells whether to invest in states or traits. P(informative) about 60%.
4. **B1 → B2 – Finishing form, and drift by likelihood.**
   * One sensitive test settles "momentum across matches": the next match's serve points, with a placebo.
   * A first pass runs on existing Slam and Stage 1 tables before A1. If it is null, all momentum carry-over closes.
   * P(signal) about 25%; P(gain) about 8%.
5. **E3 – Real rest hours, late finish, doubles.**
   * Start times exist on 89–100% of men's matches and 68–100% of women's. It is untested and costs a day or two, with a timing angle in the order of play.
   * P(gain) about 12%, +0.05 to +0.2.
6. **D1 (+ D2) – Conversion luck and last-match drama, as tests of the market's bias.**
   * D1 needs no new data (box scores, 100% coverage, ≈63k matches) and is the best candidate for the 24 h Polymarket gap.
   * P(gain) about 10%, +0.05 to +0.2.
7. **A1 – Unified sequence table and depth re-test.**
   * The enabler for B, C, D2 and G2. One decisive question: does 3–5× deeper history lift the noisy sequence statistics' share of the truth? If not, the "thin data" excuse is closed for the family.
   * P(gain) about 5%; high value as infrastructure.
8. **G2 – In-play reaction efficiency.**
   * It opens a new venue use. The data are on disk, and thousands of matches give hundreds of thousands of point–price pairs.
   * Decisive on whether Polymarket mis-prices momentum; it also informs D1 and D2.
   * P(mis-reaction) about 35%; P(profitable) about 10%.

**Also do now, because they cost almost nothing:**
* I2 (an afternoon; decides B3, the women's calibration channel);
* G1 (the move screen), applied to every feature that passes T2.

**Not recommended before the top 8 have reported:** B5–B7, C2–C4, E5, G4 (low prior, or dependent on others passing T1).

---

## 4. The three ideas the auditor will attack hardest, and my defence

**1. E1, the WTA medical log.**
* *Expected attacks:*
  * treatments are public and priced in;
  * 16% of matches have one, so most are routine (blisters, taping);
  * survivorship: players treated who still won are tough;
  * women only, with a Slam gap;
  * many flags give multiple-testing room.
* *Defence:*
  * Pre-register one primary (the explicit Injury / Illness / Heat flag, about 4% of matches, two-sided), with the routine flags secondary.
  * Check the mechanism without the market first: if flagged players do not retire more or win fewer serve points next time, stop before any market test.
  * Survivorship is handled by comparing within next-match players, who are mostly winners.
  * "Priced in" is the hypothesis under test, not a premise. The owner's frame forbids concluding "unbeatable" from a null without naming suspects, and this is new information that no input carries.
  * It is the cheapest new data on disk, and T3 on Polymarket tests the 24 h angle directly.

**2. G2, in-play reaction.**
* *Expected attacks:*
  * the owner bets pre-match;
  * minute mids are not executable;
  * point clocks are entry times (out of order in 0.4% of AO points; a spurious day jump in 28 Wimbledon matches);
  * latency, thin in-play books, fees of 5% × (1 − p).
* *Defence:*
  * It is a diagnostic first, with a clear decision value: does Polymarket mis-price runs? Fills (to the second) are used beside mids.
  * Clock faults are documented and listed, so they can be dropped. Official first points are already joined to Polymarket price paths (`starts_check.py`, start validated in 97% of checked matches). Extending that join to every point is new but mechanical work.
  * The sample is enormous compared with any pre-match test.
  * A null closes in-play momentum at almost no cost. A positive both opens a venue and informs the pre-match narrative tests (D1, D2).

**3. B1 / B2, momentum carry-over.**
* *Expected attacks:* "already dead":
  * serving after a lost point is at chance;
  * late decline is not a trait for men;
  * clutch is luck, and Klaassen–Magnus found iid a good approximation;
  * more data on a dead idea is p-hacking.
* *Defence:*
  * *Different estimand:* those tests measured a player's momentum trait. This measures whether the level at the end of a match carries into the next match: a state, not a trait.
  * *Selection:* the earlier contrasts were outcome-selected by the stopping rule (Stage C showed most of the winners' late edge was selection). B1 uses only always-played sets, and B2 uses likelihood inference, which the stopping rule cannot bias.
  * *Prior evidence:* Stage C itself observed within-match level shifts beyond iid even in the men's third set alone (0.014 against 0.001). Whether they persist across days was never asked.
  * *Discipline:* one pre-registered test, a sensitive target (next-match serve points) and a reverse-time placebo. If it is null, it closes the question for good rather than leaving it open.

**Runner-up attack: D1** ("a points-won aggregate in disguise, which the owner rejects"). It is a luck residual, results minus what the points earned, with a pre-registered sign. It tests whether the market over-credits results; it is never headlined as a rating.

---

## 5. Suggested order of work (suggestion)

1. **Day 1:** I1 and I2 on stored predictions and the WTA log. Then E1's mechanism check and T2. Then a B1 first pass on the Slam and Stage 1 tables.
2. **Days 2–3:** E3 (T2 and T3). D1 (T2 and T3). E2 for men 2022–24 (T1, then T2).
3. **Days 3–6:** A1, the unified table. The B2 σ²_pt likelihood test. D2. The G2 pilot on one month plus Wimbledon 2026.
4. **Then:** a TabPFN arm only for the items that pass T2 or T3, at most three inputs per arm. H1 if E2 passes.
5. **Throughout:** one multiplicity ledger. Every number reported with "mLL, positive = with-input better", and "tie" when the interval spans 0.
