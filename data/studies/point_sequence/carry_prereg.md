# B1 finishing-form carry-over: pre-registration

Written 6 Oct 2026 by TESTER-3, between 18:47:49 and 18:49:23 PDT. It runs item 3 of the auditor's round-3 build list (B1: a difference in differences on triples). It was written **before any estimate of Δ, or of any coefficient on a real endpoint, was computed**.

The order is shown by timestamps on disk:

* `carry_sim.py` was last edited at 18:47:49, just before this file was written;
* `test_carry.py` was edited at 18:49:23, just after;
* the one analysis run started at 18:49:41, when `carry_fit_run1.log` was created in the session scratchpad, and wrote `carry_results.json` at 18:50:51.

Later edits re-created this file, so its own creation time no longer shows the order. Sections 1–10 below are the text as pre-registered; only this header was corrected afterwards (it first gave a wrong, guessed time). Everything added after estimation is under "Deviations after estimation" and "Result".

Before writing it I had built the triple table (`carry_triples.parquet`: counts, exposures, controls) and timed one simulation-only replay. I had also compared the spread and correlation of the set-1 and late-set residuals between real matches and that replay. None of these steps reads an endpoint outcome jointly with an exposure. Nothing from 2025–26 was loaded: every reader filters to year ≤ 2024. Later changes go in a **Deviations** section at the end, with dates.

## 1. Question

Does how a player finished match t carry into the next match at the same event, beyond what that same finish says about the player's previous match?

Here "how a player finished" means the late-set serve-point residual minus the first-set residual.

* **H1 (carry-over):** the late-set residual predicts serve points in t+1 more strongly than the set-1 residual does, by more than the same contrast predicts serve points in t−1 on the same triples.
* **H0:** the late and early sets are exchangeable in what they say about neighbouring matches, apart from differences in measurement quality, which are the same in both time directions.

## 2. Data and units

* **Triple.** Three consecutive matches (t−1, t, t+1) of one player at one event. An event is a Stage 0 `tournament_id`, with qualifying and main draw together.
  * Consecutive is by round order within the player's chain, then the clock's best-estimate day, then match number.
  * All three matches must be `completed`.
  * Both gaps (t−1 → t and t → t+1) must be 0–3 days on the clock's best-estimate day (`timing.parquet` column `obs`; see Deviation D1).
* **Chain rules.**
  * Walkovers are left out of the chain, since no ball was struck.
  * Retirements, defaults and unknown endings stay in the chain and break every triple that contains them.
  * Team events (TEAM), season finals (FIN) and every round-robin round are excluded, because the draw does not fix their order.
  * A player-event with two matches in one round is dropped (58 player-events).
  * A negative gap on the clock is an impossible order, so the triple is dropped (3,673 candidates).
* **Match t** needs a usable sequence: `sequences.parquet`, chosen rows with `usable` (tiers 0–2), best of 3 or 5, not short sets. The sequence's winner must equal Stage 0's, both by the replay winner (converted to Stage 0 orientation with `a1`) and by the last point.
* **Endpoints t−1 and t+1:** the player's serve points played and won. They come from the usable sequence when there is one, else from the Stage 0 box score (`spw_n` / `spw_d`). A triple without both endpoints is dropped (6,723).
* **Offsets:** `stage3_ratings.parquet` `p_serve` for the player (and the opponent) in t−1, t and t+1. This is a sequential own-history serve/return rating, the pre-match value, constants frozen on 2013–18.
* **Windows** (year of match t):
  * discovery 2013–2021;
  * replication 2022–2024;
  * 2011–2012 is warm-up and never analysed;
  * 2025–26 is never read.
* **Observed counts after every rule** (`carry_data_summary.json`):

| window | men | women | players | best of 5 (men) |
|---|---|---|---|---|
| discovery 2013–21 | 19,259 | 7,452 | 1,560 | 1,932 |
| replication 2022–24 | 4,739 | 5,837 | 843 | 674 |

* **Source of match t, discovery:**
  * Sackmann strings 11,461 (men; 2013 to Jan 2017; CH, ITF, tour and qualifying);
  * marcosjn2 7,610;
  * Slam point-by-point 3,445;
  * WTA umpire log 2,339 (from June 2019);
  * MCP 1,250;
  * others 606.
* **Source of match t, replication:**
  * WTA log 3,590;
  * marcosjn2 2,901;
  * Infosys 1,126;
  * SlamTracker 929;
  * MCP 652;
  * others 1,378.
* **Other observed facts about the triples:**
  * the player won t−1 in 99.1% of triples and won t in 98.3% (the rest are lucky losers);
  * all three matches are exact-dated in 98.5%;
  * 96.5% of match-t sequences are strict;
  * the mean player serve points are 30.7 in set 1, 29.9 in the late set, 71.3 in t−1 and 76.4 in t+1.

## 3. Exposures (match t, the triple's player)

* **EARLY:** rE = (won₁ − n₁ · ps_t) / n₁, the set-1 serve-point residual as a share. ps_t is the player's pre-match p_serve in t.
* **LATE:** rL, the same for set 2 in best of three or set 3 in best of five. These sets are always played. A match tie-break deciding set (`mtb10`) does not affect a best-of-three LATE, since set 2 is a regular set.
* Tie-break points count as serve points of their set.
* **Scaling:** the model enters 10 × rE and 10 × rL, so coefficients are per 10 percentage points of set residual.

## 4. Endpoint model (primary)

* **One binomial GLM on stacked rows**, two per triple, the same triples in both blocks:
  * **forward row:** y = serve points won in t+1 of n played, offset = logit(ps_{t+1});
  * **reverse row:** y = serve points won in t−1 of n played, offset = logit(ps_{t−1}).
* **Direction-specific coefficients** (d = fwd, rev):

  logit P(won) = offset + α_{d,tour} + β_{d,E} · 10 rE + β_{d,L} · 10 rL + γ_d · 10 FORM + δ_{d,2} · 1{1 < gap_d ≤ 2} + δ_{d,3} · 1{2 < gap_d ≤ 3}

  * **α:** intercepts per direction × tour (men, women).
  * **FORM** ("box-score form"): the player's decayed serve-point residual as of match t−1, the same value in both rows.
    * It is computed over the player's earlier matches under the own-history rule (an earlier tournament date, or an earlier round of the same event) that have known serve points (sequence or box score), within 180 days.
    * Weights: w = 0.5^(days/14). Formula: Σ w (won − n · p_serve) / (50 + Σ w n).
    * It is the same in both directions so that the controls are symmetric; see Deviation D3.
  * **gap_d** is the endpoint's own gap: t → t+1 forward, t−1 → t reverse. The reference is one day or less (half days arise where sources disagree by a day).
* **Primary statistic:** Δ = (β_{fwd,L} − β_{fwd,E}) − (β_{rev,L} − β_{rev,E}).
  * Units: endpoint serve-point log-odds per 10 percentage points of set residual.
  * **Positive = late form carries forward more than backward** (the H1 direction).
  * Δ near 0 means no carry-over beyond measurement quality.
* **Tours pooled** (one Δ with common slopes and tour intercepts); men and women are reported separately as secondary breakdowns.
* **Inference:**
  * Newton–Raphson maximum likelihood.
  * Covariance clustered by the triple's player: CR1, with G/(G−1) · (N−1)/(N−K). Both rows of a triple and all of a player's triples share a cluster.
  * Primary interval: 95% Wald interval.
  * Check: a player-cluster bootstrap (999 replicates with multinomial cluster weights), percentile interval.
  * Wording: "tie" or "no effect" whenever an interval spans 0.

## 5. Placebos

1. **Replay null (required by the pass rule).**
   * Every triple's match t is replayed point by point as iid draws at de-noised day rates.
   * Each player's measured whole-match serve share in t is shrunk to a tour × surface prior frozen on 2013–18 Stage 0 box scores (empirical Bayes, as `stage2_anatomy.denoised_rates`), and a true rate is drawn from the posterior.
   * The format, first server and deciding-set rule are the real ones. The replay is conditional on the real winner: rates and points are redrawn together until the winner matches, at most 200 rounds.
   * rE and rL are recomputed from the replayed sets, against the same ps_t. The endpoints, offsets and controls stay real. The whole pipeline is then refitted.
   * **R = 50 replays** for the primary (tour × surface) de-noising, in discovery and in replication.
   * **Acceptance band:** the replay null is "inside its null" if |mean_r Δ_r| ≤ max(1.96 · SD_r / √R, 0.25 · SE(Δ̂_discovery)). In words: its mean is not distinguishable from 0, or is negligible against the real estimate's standard error.
   * Also reported:
     * the replay spread;
     * the share of replays whose own interval excludes 0;
     * where the real Δ falls in the replay distribution (descriptive only: the replay spread omits the endpoints' sampling noise).
   * **Secondary replay variant** (R = 20, descriptive):
     * the day rate is de-noised toward the player's own ps_t, with a frozen tour variance of day deviations (2013–18 box scores against stage3 p_serve);
     * reason: the tour-mean de-noising gives set residuals a common component larger than in real matches (one replay: correlation of rE and rL 0.26 against 0.08 real);
     * it must also centre on 0.
2. **Label swap.**
   * Within each triple, EARLY and LATE are exchanged with probability 1/2, the same in both rows, and the model is refitted.
   * 500 swaps per window. The swap distribution is centred on 0 by construction.
   * The two-sided permutation p of the observed Δ against it is reported as a randomisation check of the primary inference.

## 6. Secondary analyses (descriptive; none enters the pass rule)

* **Fade by gap.** E and L are interacted with the triple's forward-gap class (1 day or less / 2 days / 3 days) in both blocks, giving Δ per class. Fade = Δ(1 day) − Δ(3 days): positive = the carry-over fades with rest. Expected cell sizes are about 17k / 8.7k / 0.9k in discovery, so the 3-day cell is small.
* **Breakdowns:**
  * men; women;
  * best of 3; best of 5;
  * tour-level main draw (GS, 1000, 500, 250) against qualifying, Challenger and ITF.
* **Sensitivities:**
  * (a) symmetric outcome selection: only triples where the player also won t+1. The reverse endpoint is almost always a won match and the forward endpoint is not, and that asymmetry could bias Δ if the late set measures form better than the early set;
  * (b) strict sequences only;
  * (c) all three matches exact-dated;
  * (d) match t's whole-match serve residual added as a control in both rows;
  * (e) the audit-literal form control: form as of each endpoint, so the forward form includes t−1 and t;
  * (f) no form control.
* **Exploratory:** the return-point twin (set-1 and late-set return residuals against 1 − opponent's p_serve; endpoint return points won, offset logit(1 − opponent's p_serve); no form control).

## 7. Pass rule (binding; one primary test)

**PASS** if all three hold:

1. discovery Δ > 0 with its 95% clustered Wald interval excluding 0;
2. the discovery replay null (primary de-noising) is inside its acceptance band;
3. replication Δ > 0 (the same sign; significance not required).

Otherwise **FAIL**.

* If the rule passes but the bootstrap interval spans 0, or sensitivity (a) flips sign, the result is reported as "pass, fragile".
* If the replay null falls outside its band, the pipeline is not interpretable and the result is FAIL until the cause is found (recorded as a deviation).

## 8. Power (inferred before scoring)

* **Rough standard error.** About 76 endpoint serve points and set residuals with an SD of about 0.10 (observed) give SE(β) ≈ 0.002–0.003 per coefficient, and SE(Δ) ≈ 0.004–0.006 in discovery. The minimum detectable Δ at 80% power is ≈ 0.012–0.017 log-odds per 10 pp.
* **What that means.** It corresponds to most of a 2-percentage-point late-set deviation carrying into the next match (inferred: the late residual's reliability for a within-match deviation of SD 2 pp is about 0.04). Only large carry-over is detectable.
* The replay run gives the exact standard error.

## 9. Deviations and operational choices fixed before estimation

* **D1. Clock column.** The brief named timing.parquet `start`, but `start` is the tournament's start date, the same for every round (observed: every candidate triple had gaps of 0). Days are the clock's best-estimate day `obs` (timing.py rule 5).
* **D2. Winner orientation.** `seq_matches.replay_winner` is in the source's orientation. Converted with `a1`, it agrees with Stage 0 on 100% of complete chosen sequences (observed).
* **D3. Symmetric form control.** The audit says "box-score form" for each endpoint. Form as of t+1 would contain match t's total in the forward row only. That is an asymmetric free regressor, which can make Δ ≠ 0 under H0 whenever the late and early sets differ in reliability, and the placebos would not show it. The primary therefore uses form as of t−1 in both rows. The literal version is sensitivity (e).
* **D4. Exclusions and discovery start.** Discovery starts in 2013: 2010–12 is the ratings' warm-up, and the audit names men 2013 on. TEAM, FIN and round robins are excluded (see §2).
* **D5. Secondary replay variant.** Player-centred de-noising is added as a secondary replay (see §5), on an observed difference in the residuals' spread and correlation between real matches and the replay.

## 10. Consequences (from audit round 3, item 3)

* **PASS:** no market or model test is run here. The main session decides the next step, such as a residual screen against `p_base` or a pre-match feature.
* **FAIL:** closes carry-over of finishing form across matches as a pre-match state signal (B1, and B2 with it). Momentum is then an in-play question only.

## Files

* Code:
  * `src/eda/point_sequence/carry_data.py` (triples);
  * `carry_sim.py` (replayer, de-noising);
  * `carry_fit.py` (model, placebos, secondaries).
* Tests: `test/point_sequence/test_carry.py`.
* Outputs in `data/studies/point_sequence/`:
  * `carry_triples.parquet` and `carry_data_summary.json`;
  * `carry_results.json` and `carry_estimates.csv`;
  * `carry_replay_null.csv` and `carry_label_swap.csv`.

## Deviations after estimation (6 Oct 2026, 18:51–19:00 PDT)

* **No deviation in the pre-registered analysis.** Every item in §4–§7 ran as written (`carry_fit.py`, one run: 50 + 20 replays, 999 bootstrap replicates, 500 swaps).
* **D1 confirmed** (added after estimation). The main session confirmed D1 that evening: the error was in its brief, and `obs` is to be used for every day gap.
  * No estimate was ever computed with `start`. The triple table had been rebuilt on `obs` before this file was written.
  * Effect of the column (counts only, no model; session scratchpad `carry_start_vs_obs.py`):
    * `start` equals `tournament_date` in 100% of rows to 2024.
    * At the candidate stage, `obs` drops 6,356 of 316,059 completed candidates: 3,673 in an impossible order on the clock and 2,683 with a gap over 3 days. `start` drops none.
    * In the final table, every one of the 41,147 `obs` triples is also in the `start` build. `start` adds 808 more: discovery 364 (men 191, women 173), replication 386 (men 186, women 200), warm-up 58.
    * Under `start` every gap is 0, so the gap control and the 1-against-3-day secondary could not have been estimated.
* **Observed, outside the pass rule.** The replication window's primary replay null (50 replays) centred at −0.0018, just outside its band of ±0.0014. The pass rule reads only the discovery replay null.
* **Post hoc 1** (`carry_posthoc.py`; labelled post hoc). 100 further replays per window with new seeds:
  * the replication replay centre is +0.0002 ± 0.0006 (SE), and all 150 replays give −0.0005 ± 0.0004;
  * discovery: all 150 give +0.0002 ± 0.0003.
  * So the −0.0018 was chance, not a structural offset.
  * Inside the replays, set 1 and the late set behave as exchangeable: the mean late-minus-early residual is −0.00002 (discovery) and −0.0002 (replication), and the spreads of the two residuals are equal to within 0.0003.
* **Post hoc 2** (not pre-registered; descriptive):
  * an inverse-variance pool of the two windows' Δ gives +0.0059 [+0.0002, +0.0117], an interval slightly optimistic because players recur across windows;
  * effect sizes per SD of late-minus-early residual (14.1 pp) are given in `carry_posthoc.json`.

## Result

**FAIL**, on criterion 1 of §7. Numbers are in `carry_results.json`; units are endpoint serve-point log-odds per 10 pp of set residual, positive = late form carries forward more than backward.

| | discovery 2013–21 | replication 2022–24 |
|---|---|---|
| **Δ** | **+0.0038 [−0.0030, +0.0107]**, a tie | **+0.0109 [+0.0003, +0.0216]**, positive: late form carries forward more |
| criterion | 1 fails | 3 holds (same sign) |
| bootstrap | [−0.0028, +0.0107] | [+0.0003, +0.0218] |

* **Replay null** (criterion 2): the discovery replay null is inside its band (mean +0.0006, band ±0.0010), so the criterion holds.
* **Label swap:** the permutation p is 0.28 in discovery and 0.040 in replication.
* **Consequence** (§10): finishing-form carry-over across matches closes as a pre-match state signal, for effects above the test's minimum detectable Δ ≈ 0.010 (80% power). That is about 0.16 pp of next-match serve points per SD of finishing form, or about 0.8 pp of match-win chance at even odds by the iid match model (inferred).
* **What stays open:** smaller effects, of the size of the replication estimate (0.19 pp per SD), are not excluded. The main session decides.
