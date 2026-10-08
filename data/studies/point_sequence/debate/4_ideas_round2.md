# Brainstorm, round 2: rebuttals, the I1 result, and the final build list

Brainstormer agent, 6 Oct 2026. **Suggestions, not decisions.**

* Labels: **observed** = read-only check today, or a number quoted from the audit or the main session; **inferred** = my reasoning; **suggestion** = a proposal.
* Units: mLL per match, **positive = the second-named forecast (or the one with the feature) is better**. "Tie" when the 95% interval spans 0.

---

## 0. Where I moved

* **I accept the power argument and the holdout discipline in full.** Every pre-match idea now starts on a gate with a target that is either not the market or prices only:
  * next-match retirement or withdrawal;
  * next-match serve points won;
  * the 24 h → close price move.

  Outcomes run only on discovery (≤ 2021) and replication (2022–24). 2025–26 stays closed.
* **My evidence base for "states beat traits" was thinner than I said.** The auditor is right on two points:
  * the serve-speed figure I cited (+0.24) was the three-input profile; the change alone is +0.14 [−0.00, +0.28], a tie;
  * workload is a tie by interval: men +0.23 [−0.01, +0.48], women +0.29 [−0.06, +0.64].
* **I1 then cuts against the ranking itself.** Directionally, the model's edge is largest when nobody has a fresh match.
* **So my state ideas are now explicit bets on one reading.** That is reading A below: the market holds fresh information that the model lacks. I add a cheap test (**I1b**) that separates A from the alternatives before any further state feature is built.
* **Final build list** (CPU only, about 2½–3 days):
  1. I1b, the information-age decomposition;
  2. the E1 mechanism gate, with the women's E2 fade markers in the same pass;
  3. the B1 finishing-form test (difference in differences);
  4. I2.

---

## 1. Point by point: my top 8

### E1: the WTA medical log (auditor 65)

* **Coverage overstated, because the 2024–26 link shares include Slams with empty logs.**
  * **Accept.** The correct figure is about 0.97–1.00 of non-Slam women's frame matches from 2020, 0.68 in 2019, and at most about 0.78–0.80 of the whole women's frame.
* **The injury reason (about 4%) is under-powered as the market primary; make "treated" the primary.**
  * **Accept for the market test. Refine for the mechanism gate.**
  * Next-match retirement or withdrawal is a rare binary endpoint. The injury reason is where a large risk ratio is plausible. With about 400 injury-flagged pairs and a base rate of about 2%, about 8 events are expected under the null; a risk ratio of 2.5 or more is detectable there (inferred).
  * So both exposures stay in the mechanism family, with Holm correction over two exposures × two endpoints. "Treated" is the market primary.
* **Survivorship: the worst-injured withdraw, and walkovers are not in the frame, so the effect is diluted toward 0.**
  * **Accept, with one distinction.**
  * For the mechanism estimate, withdrawals belong in the first endpoint (M1).
  * The dilution only biases toward a null. It costs power and cannot create a false positive.
  * For the market estimand, conditioning on the next match being played is the right population, because a bet exists only for matches that are played or settled. The venue's walkover and retirement rules must be checked.
  * Stratify by the previous result: an in-event next round after a win, against the next event after a loss.
* **Missingness: "no flag" mixes "no treatment" with "previous match at a Slam or ITF". Use three states.**
  * **Accept, and go further.** The primary contrasts compare **flagged with logged-unflagged only**; unlogged pairs are excluded from every mechanism and screen test.
  * In any later TabPFN arm the three states are explicit, with a missingness-only placebo arm.
* **The expected-rate baseline is frozen on ≤ 2021.** Accept.
* **Refinement, not in the audit: more power for free.**
  * The mechanism endpoints need no closing odds. So use every logged pair: a previous match at WTA tour, 125 or qualifying level, followed by a next match at any level with a log, box score or result.
  * That roughly doubles the frame-only n (inferred). The market screen stays on frame matches.

### E2: fading markers within the last match (auditor 56)

* **The speed figures.** **Accept the correction.** The change alone was +0.06 [−0.02, +0.15] over 2013–26 and +0.14 [−0.00, +0.28] in 2022–26, both ties; +0.24 is the profile.
* **G4 for deploying the men's version:** there are no non-Slam ATP speeds for 2025–26. **Accept.** The men's speed fade is research-only unless H1 happens.
* **Women's markers from the WTA log now; men's speed on Slams ≤ 2021.** **Accept.** The women's markers go in E1's pass: same log, same targets.
* **Tempo as a control, not E5 standalone.** **Accept.**

### I1: where the edge lives (auditor 60; run by the main session on 2022–24)

* **Accept the design**: five splits, discovery 2015–21, Holm correction.
* **Holdout note (inferred):** 2022–24 was read *before* discovery. Any hypothesis that merely re-expresses I1's subset contrast can therefore be discovered only on 2015–21 and confirmed only at the final 2025–26 test, not "replicated" on 2022–24.
  * New variables, such as I1b's fresh-information components, have not been read on 2022–24 and may still use it as replication.

### B1: finishing-form carry-over (auditor 60)

* **First sets may be noisier (warm-up, slow starts), so β(late) > β(early) could appear without carry-over. Make the reverse-time placebo part of the primary statistic.**
  * **Accept; good catch.** The difference in differences cancels any measurement-quality asymmetry: the late set is the better measure of level both forwards and backwards. Only temporal asymmetry survives.
  * **Refinement:** run forward and reverse on the **same triples** of consecutive rounds (t−1, t, t+1), so players and selection are identical in both directions.
  * **Add a replay-history placebo:** the full pipeline on iid replays of match t must give Δ ≈ 0.
* **Slam first pass on ≤ 2021, then the unified table for 2022–24.** **Accept.**
  * **Add:** the WTA umpire log for June 2019 – 2021 is in discovery too. Consecutive tour rounds 1–2 days apart are the best setting for carry-over, and its replay already exists (`verify_wta.py`).

### B2: within-match drift (auditor 47, parked)

* **"Its stop rule is logically wrong: σ²_pt is not σ²_day."**
  * **Rebut the logic.**
  * If σ²_pt = 0, a player's level is constant within the match. Early and late sets are then exchangeable noisy measures of one level, so B1's Δ must be 0. "No within-match drift ⇒ no finishing-form carry-over" is valid.
  * What fails is the converse: σ²_pt > 0 does not imply carry-over, since drift could reset overnight. I never claimed that.
* **"σ²_pt > 0 will be significant from any non-stationarity (score state, new balls, conditions)."**
  * **Accept.** This makes the stop rule toothless in practice: it would almost never fire. Valid, but useless as a gate.
* **Respecification (suggestion):** B2's estimand should be a carry-over share λ, the fraction of the end-of-match deviation that persists into the next match.
  * Use explicit covariates (score state, ball changes, serve order) so that fixed within-match patterns do not load into drift.
  * Only after B1 passes. **Accept parking.**

### E3: real rest hours (auditor 58)

* **"Fails G4 for the 24 h angle: there is no historical order of play."**
  * **Accept** for any 24 h test that uses the realised start.
  * **Rebut "no 24 h content".** The previous match's end time is known as soon as it ends, usually before the 24 h mark. So are:
    * the late-finish flag;
    * a **lower-bound rest**: previous end → the earliest possible start of the target's day.

    The leak-proof clock already defines that earliest start (es); the event's first scheduled hour is an alternative. None of this needs the order of play. At the close, the realised start is known, so close-based tests are valid.
* **"E3 waits until I1 shows short-rest or late-round concentration."**
  * **Rebut the logic.** Under reading A, a missing state input pays where the model is **weakest** relative to the market, not where its edge is concentrated.
  * I1 shows exactly that weakness, directionally: ≤ 1 day of rest +0.67 (tie) against > 7 days +2.95 [+0.69, +5.22] (positive = model better).
  * So I1 makes E3 a direct test of A rather than a reason to wait. Under B it would be worthless.
* **"Expect a tie (the subset is small)."** **Accept the power point.**
  * That is why E3's first step now sits in I1b's **price-only** step: does the market's deviation from the no-odds model load on rest hours in next-day matches? That has high power.
  * Its outcome residual screen follows in the same pass.
* **Day-level rest is covered; recovery context ties.** **Accept.** E3's only new content is hours within next-day matches.

### D1 (+ D2): conversion luck and drama (auditor 61 and 43)

* **"Mostly already tested."**
  * **Partial rebuttal.** The tested neighbours are single components:
    * the tiebreak record;
    * the break-point record;
    * big points on return.

    Or a different construct: "results above Elo's expectation" is over-performance against a prior, which is mostly real form, not conversion luck. The composite was never tested: sets and games won minus what the day's points earned, under iid. Nor was its in-event window.
  * **Accept the substance**:
    * every component ties given the market;
    * luck as an Elo correction helps given Elo but not given the market, so the market already discounts it;
    * the model holds both results-based and points-based inputs.
  * **New evidence from I1 cuts further.** D1's in-event mechanism is "the market over-reacts to fresh lucky wins". That predicts the model, which does not over-react, should gain *more* in later rounds. I1 shows the opposite direction.
* **Decision:** D1 is **no longer a standalone item.** It rides along as one pre-declared component of I1b's fresh-information screen (F2). That costs nothing extra and closes register entry A05 either way.
* D2's rare flags are dropped. Its box-score proxies (deciding set, minutes) enter I1b as part of the physical component (F4).

### A1: unified table and depth re-test (auditor 53)

* **Accept every point:**
  * park the outcome re-test;
  * the table proceeds as the builder's infrastructure;
  * run only the outcome-free recovery gate: ρ² with the career truth by depth quarter, with truths built from ≤ 2024;
  * Stage 3 already rules out an edge of 0.5 mLL or more for the men's "holds right after breaking".
* **Note:** under reading B (§2), A1 is the main *trait-side* investment. Its recovery gate should run as soon as the table lands, whatever I1b says.

### G2: in-play reaction (auditor 60 after redesign)

* **"Sets the prior for D1 and D2" is a holdout leak.** **Accept; withdrawn.** It is firewalled from pre-match design.
* **Prices strictly before each point's earliest possible start.** **Accept.**
* **The overlap is about 2,300–2,500 matches (75% women, about 500 men), not "several thousand".** **Accept.**
* **Other limits, all accepted:**
  * minute mids cannot resolve the seconds after a point;
  * fills run only to 21 Sep 2026;
  * in-play spreads are unmeasured;
  * live use needs an owner decision;
  * retirement settlement rules need checking.
* **Not on this session's list.** It is the first item for the next session: the explore half, price-only tests (a) and (c).

### On power generally

* **Accept:** a pre-match outcome test of one input detects only about 1.2 mLL on 2022–24.
* **One addition for later stages:** a feature that clears its gate should be judged by **arm against base** on the 58-input frame, not by feature against the close. The auditor's own power table puts the realised-gain MDE at about 0.30–0.45 mLL (both tours) for an arm that moves forecasts by RMS 0.03–0.05. Plant a known edge through TabPFN first (audit D.16).

---

## 2. What I1 does to the state-over-trait thesis

**Observed (main session; 2022–24; the adopted `elo_off` arm against the recalibrated close; positive = model better):**

| Subset | Gain |
|---|---|
| Overall | +0.98 [+0.24, +1.72] |
| Both players' first match at the event | +1.74 [+0.18, +3.29] |
| Both in later rounds | +0.81 (tie) |
| One later | +0.40 (tie) |
| Minimum rest > 7 days | +2.95 [+0.69, +5.22] |
| Minimum rest ≤ 1 day | +0.67 (tie) |

Every contrast between subsets is a tie.

**Four readings (inferred):**

* **A. Fresh-information gap.** In later rounds the market holds previous-round information that the model lacks or under-weights: how a player looked, injuries, fatigue, how far to trust the most recent match.
  * The model then partly *fights justified moves* of the close.
  * State features close that gap. That is still a gain over the close in those matches.
  * *Rough ceiling:* (first-round edge − later-round edge) × the later-round share ≈ 0.93 × about 0.45 ≈ **+0.4 mLL overall**. The share is my assumption from draw structure: later rounds are about 45–48% of a draw's matches. The interval is wide, since the contrast is [−0.74, +2.73].
* **B. Long-memory under-weighting.** When no fresh match exists, the market leans on rankings and recent results and under-weights long-memory, surface-specific profiles, which the model reads well. Once a fresh match exists, both sides update on it, and the profile's relative value falls.
  * State features gain about 0 through this channel. Investment goes to long-memory profiles.
  * *Consistent prior evidence:* the offset structure's gains concentrate where the price is stale. In the surface-race study, offset Elo was +0.78 at the 24 h price and +1.01 without a price, but −0.05 at the close.
* **C. Composition and attention.** Later rounds have stronger, better-known players and sharper prices. Round 1 has more lopsided matches, where calibration (the women's main gain) matters more. Information age is then incidental.
* **A′. The market over-reacts to fresh results** (the mechanism behind D1's in-event window and D2). This predicts the model gains *more* in later rounds, which I1 directionally contradicts.

**Which reading each idea bets on:**

| Idea | Reading | What would promote or kill it |
|---|---|---|
| E1 medical log | A, plus an independent channel: treatments are in no score, so even the market may miss them at low-profile events | Its mechanism gate stands alone. Its market value rises if I1b supports A |
| E2 fade markers | A | as E1 |
| E3 rest hours (now I1b's F4) | A, in the exact subset where the model is weakest | killed at outcome level if F4 is null; promoted if the price-only step shows the market loads on rest |
| B1 / B2 carry-over | A | the B1 gate stands alone. A positive Δ plus A → a feature |
| D1 in-event, D2 | A′ | weakened by I1. F2 and F3 signs against the price decide |
| D1 over 8 weeks | B (the market over-weights recent results against points) | the tested components already tie |
| A1 depth, C1, C3 | B (long-memory traits) | promoted if B |
| B3 (via I2) | B, plus calibration | promoted if B and I2 passes |
| N2 information-age inputs and shrinkage | A or B | promoted by either |
| N3 qualifier fresh form | A | promoted if the one-fresh contrast is where the model is weakest |
| G1 | neutral tool | – |
| G2, G3 | in-play, firewalled | – |

**The cheap separating test is I1b** (pre-registration in §3). It has three parts:

* **Price-only first:** what does the market use beyond the no-odds model, and in which subset? The stored `p_noodds` makes this possible.
* **Outcomes second:** is the market right to use it?
* **Natural experiments:** they vary information age at a fixed round and level, which separates A/B from C.

---

## 3. Final build list for this session (CPU only)

Order: F1 → F2 → F3 → F4. F1 may reorder the rest. No GPU, and nothing reads 2025–26.

### F1. I1b: information-age decomposition (new; about half a day to a day)

* **Data:**
  * `meta_stack/walkforward.parquet`: the 54-input predecessor, 4 seeds, 2014–26, with `p_base`, `p_noodds` and `p_mkt`. Robustness check: the `elo_off` arm's stored forecasts for 2019–24.
  * The frame's inputs.
  * Stage 0 box scores and minutes; Flashscore `start_utc`; the match-timing tz modules.
  * `stage3_ratings` p_serve: a sequential Glicko-type rating in event and round order, safe under the 5 Oct classification, constants tuned 2013–18.
  * `stage2_iid`, with de-noising priors frozen on ≤ 2018.
* **Subsets (match level), as the main session's I1 uses them:**
  * **S_stale:** both players' first match at the event, and at least 7 days since each player's last match;
  * **S_fresh:** both players' previous match in the same event, within 3 days;
  * **S_mixed:** exactly one fresh.
* **Exposures.** Fresh-information components, per player, as A − B, from the previous match only (own history, in order):
  * **F1, performance:** serve plus return points won minus the expectation at pre-match p_serve, as a z-score;
  * **F2, luck (D1 / A05):** sets and games won minus the iid expectation at the day's de-noised rates, with format from the repaired schedule rules;
  * **F3, market surprise (A16):** result minus that match's recalibrated close;
  * **F4, physical (E3-lite, S_fresh only):** previous minutes, deciding set, and rest hours to the target. Rest hours use (start + minutes) → realised start for the close test, and es for the lower bound. Plus the local late-finish flag.
* **Projections.** D = logit `p_noodds` − logit `p_mkt`. D_L and D_S are its OLS projections on the long-memory inputs (Elo levels, per-surface IOS, `ratings_iid`, `points_52w`, `elo_games`) and the short-memory inputs (form, formdef, `adjperf_tpw_2w`, `ios_points_short`, `sets_14d`). Fitted on 2015–21 and frozen.
* **Step 1, price-only (high power, no outcomes):**
  * Dev = logit `p_mkt` − logit `p_noodds`, regressed on F1–F4 and on D_L and D_S, by subset.
  * Windows: 2015–21; check 2022–24.
  * Reports loadings with 4-week block intervals: what the market uses beyond the model, and when.
* **Step 2, outcomes (discovery 2015–21; replication 2022–24 for the F tests only):**
  * **A-tests:** y ~ offset(logit `p_base`, calibrated) + c_k·F_k in S_fresh, k = 1–4. Mirror: the same with offset(logit `p_mkt`, recalibrated). The mirror's sign says whether the market under- or over-reacts.
  * **B-test:** y ~ offset(logit `p_mkt`, recalibrated) + a_L·D_L + a_S·D_S, interacted with S_stale against S_fresh. Primary contrast: a_L(S_stale) − a_L(S_fresh).
  * **C-test:** the model's gain d = LL(close) − LL(model), in mLL, positive = model better:
    * in round 1, matches with exactly one qualifier against none;
    * in round 2, matches where one player had a bye against none;

    with level fixed effects and |logit p_mkt| bins, for the favourite–longshot and calibration composition.
  * **Secondary:**
    * within S_stale, surface-switch against same-surface previous match (B′: surface long memory);
    * subset-specific disagreement shrinkage, p = expit(logit p_mkt + s_subset·(logit p_base − logit p_mkt)), with s fitted on 2015–21 and scored on 2022–24. This is the cheapest direct use of the I1 pattern, labelled not blind.
* **Pass rules** (Holm over 6 primaries: four A-tests against `p_base`, the B contrast, the C-qualifier contrast):
  * **A supported:** at least one c_k is Holm-significant in discovery with the same sign in replication, **and** the Step 1 loading of Dev on that F_k in S_fresh has the matching sign.
  * **B supported:** a_L(S_stale) − a_L(S_fresh) > 0, Holm-significant in 2015–21. 2022–24 was seen through I1, so its confirmation is the final 2025–26 test.
  * **C indicated:** the qualifier and bye contrasts are about 0, and the subset gap disappears with level and |logit p| controls.
* **Placebos and controls:**
  * **stale-F:** the same components from the player's match two events earlier; must be about 0 against `p_base` in S_fresh;
  * F shuffled within tour × season × subset, NaN mask kept;
  * a missingness model for F3 (it needs the previous match in the frame with odds).
* **Power, stated now (inferred):** S_fresh is about 40–48% of matches. Discovery n ≈ 12–14k gives an outcome MDE of about 1.3–1.6 mLL within the subset: 15.68/n, × 1.19 for one input. **Only large effects show on outcomes.** The decisive read is Step 1 plus the sign pattern.
* **What a null closes:**
  * **A null:** the model is not missing fresh information visible in box scores. Any remaining gain from states must come from information outside box scores (E1, E2, B1). E3's rest hours close at outcome level, and so do D1 / A05.
  * **B null:** no evidence the edge is specific to long memory in stale matches.
  * **Both null, C indicated:** I1's pattern is composition. No reprioritisation between states and traits.

### F2. E1 mechanism gate, with the women's E2 fade markers (about a day)

* **Units:** pairs of the player's previous and next match.
  * Previous: a WTA singles match with a complete umpire log (tour, 125 or qualifying, from 4 Jun 2019).
  * Next: the player's next singles match within 21 days, at any level with a log, box score or result.
  * Pairs whose previous match ended in the player's retirement are excluded from the primary analysis (included as a sensitivity).
* **Exposures,** coded in three states (flagged / logged-unflagged / unlogged; unlogged excluded):
  * **TREATED:** MedicalTreatment, TreatmentInProgress, or PhysioCalled not cancelled, naming the player;
  * **INJURY:** reason Injury, Illness or Heat (nested in TREATED).
* **Endpoints:**
  * **M1:** next match retired, or a walkover given before it. WTA list codes 4/5 and 6/7 are attributed to the player; results are used for non-WTA levels.
  * **M2:** next-match serve-point residual, binomial, with offset at pre-match p_serve, in percentage points.
  * Return-point residual: secondary.
* **Adjustment:** previous minutes (deciles), previous result, days since, surface, age, and a treatment-propensity score fitted on ≤ 2021.
* **Pre-declared strata:** previous win followed by an in-event next match (fresh), against previous loss followed by the next event (stale). This links E1 to I1b's readings.
* **Negative control and placebo:**
  * **TOILET** (toilet or clothing break) must show nothing on M1 or M2;
  * TREATED permuted within season × previous result × minutes decile;
  * the opponent's flag as a specificity mirror.
* **Windows:** discovery 4 Jun 2019 – 2021; replication 2022–24; 2025–26 counts only.
* **Pass** (Holm over {TREATED, INJURY} × {M1, M2}): a risk ratio above 1.5 on M1 or a shift of −0.5 pp or less on M2, with the interval excluding no effect in discovery, the same sign in replication, and the toilet control null.
  * **Then:**
    1. a residual screen of the women's frame against `p_base` (TREATED primary);
    2. G1 on the Polymarket explore half (Sep 2025 – Mar 2026);
    3. the confirm half.
* **Secondary family (women's E2; separate Holm, k = 3):**
  * *Markers:* within the logged previous match, per-point slopes of first-serve-in, double-fault rate and own-serve tempo against points played, controlled for score state, tiebreak, serve number and court side.
  * *Baseline:* excess over tour norms by match length, frozen on ≤ 2021.
  * *Target:* M2, with the difference-in-differences statistic: next match against the match before the previous one.
* **Power (inferred):**
  * About 9–10k logged pairs in discovery, about 8% treated per player-match, so about 750 treated pairs.
  * M1 at a base rate of about 1.5–3% per player (inferred): a risk ratio of 2 or more is detectable; 1.5 is marginal.
  * M2 standard error about 0.2–0.25 pp, so −0.5 pp is detectable.
* **What a null closes:**
  * E1 as a pre-match input, together with its market and G1 tests;
  * G3 (in-play medical events) downgraded;
  * the women's in-match fade markers (first serves in, double faults, tempo) as pre-match state signals.

### F3. B1: finishing form, difference in differences (about a day)

* **Units:** triples of consecutive matches of one player at one event (t−1, t, t+1).
  * Each gap is 3 days or less.
  * All three are completed (no retirement).
  * The same triples are used forwards and backwards.
* **Data:**
  * *Discovery:* the Slam point sequences 2011–21 (`stage2_pbp_points.parquet`) and the WTA umpire log, 4 Jun 2019 – 2021 (tour, 125, qualifying).
  * *Replication:* 2022–24 on the unified table when it lands (WTA log, Slam feeds and the Hawk-Eye copy, marcosjn2, Infosys).
* **Exposures** (in match t, against pre-match p_serve):
  * **EARLY** = the set-1 serve-point residual;
  * **LATE** = set 2 in best of three, set 3 in best of five (always played).
  * Return residuals are secondary.
* **Targets:**
  * forward: serve points won in t+1, binomial, with offset at that match's pre-match p_serve, plus box-score form and the day gap;
  * reverse: the same for t−1.
* **Primary statistic:** Δ = [β_LATE − β_EARLY]_forward − [β_LATE − β_EARLY]_reverse, clustered by player.
* **Placebos:**
  1. the whole pipeline on iid replays of match t at de-noised day rates, where Δ's null distribution must centre on 0;
  2. EARLY and LATE labels swapped at random within match.
* **Secondary:** dose–response. Carry-over should fade from a 1-day to a 3-day gap, and vanish for the next event.
* **Pass:** Δ > 0 with the interval excluding 0 in discovery, the replay placebo inside its null, and the same sign in replication.
* **Power (inferred):**
  * About 5k Slam triples (62 per draw per year) and about 3–4k WTA-log triples (counting qualifying-to-main-draw sequences) in discovery, with about 70 serve points per target.
  * Detectable if about 10–15% of the late deviation persists. The exact figure comes from the replay null before scoring.
* **What a null closes:** finishing-form carry-over across matches (B1, and B2 with it) for pre-match use; momentum as a pre-match state signal. Within-match momentum stays an in-play question (G2's firewalled track).

### F4. I2: is the women's points-share anomaly real? (an afternoon)

* **Data:**
  * WTA umpire log: non-Slam singles, complete logs, Jun 2019 – 2024.
  * Men's control: Slam point sequences and Infosys tour matches, ≤ 2024.
* **Test:** a cross-validated logistic of the winner on the points share (and on the iid plug-in chance). Log loss, real against the iid replay at de-noised day rates.
  * *Replay variants:* true variance × 0.5, × 1 and × 1.5; per player-season rates.
  * *Diagnostics:* tiebreaks per match, wins with fewer points, and the spread of the points share, real against each replay.
* **Pass:** the women's real-minus-replay gap (Stage 2: 0.118 against 0.103 log loss) excludes 0 under every replay variant, while the men's covers 0. Then B3's outcome-free reliability test runs: split-half, real against replay.
* **Negative control:** men.
* **What a null closes:** the anomaly as evidence of within-match streakiness. It came from box-score error or replay misspecification. B3 parks for women, and predictability Stage 2's open question 7 is answered.

---

## 4. Dropped, parked, and new

**Dropped or rejected:**
* B5 (swing games);
* B6 (rally recovery; at most a secondary fade marker in E2);
* B7 (tilt; "after a lost point" is chance);
* C4 (matchup products);
* G4 (needs 2025–26 outcomes; revisit with 2027 data);
* H4 (weather);
* D2's rare flags (match points saved and the like: under-powered and A′-type, which I1 weakens).

**Folded into other items:**
* D1 → I1b F2;
* E3 → I1b F4 (standalone only if Step 1 shows the market loads on rest hours);
* E4 → a control in F4;
* E5 → a tempo control in the E2 markers.

**Parked:**
* A1's outcome re-test (the table proceeds, with the recovery gate only);
* B2 (respecified as λ, after B1);
* B3 (after I2);
* B4, C1, C2, C3;
* G3 (an add-on to the G2 pilot);
* G5 (descriptive only);
* G6 (a free liquidity census of Polymarket's totals and handicaps first);
* H1–H3 (acquisition leads, each conditional, as the auditor ranked them).

**Kept as tools:** G1 (explore half, only for features that pass their gate). G2's pilot is the first item next session.

**New ideas from the critique and I1:**

* **N1. I1b, the information-age decomposition** (F1 above). The price-only step is the new piece: the stored no-odds forecasts let the market's information be measured without outcome noise.
* **N2. Information-age context for the model** (suggestion; after I1b).
  * *Subset-specific shrinkage* of the model's disagreement with the close (CPU, minutes; inside F1).
  * *If A or B holds:* an arm with explicit information-age inputs, so TabPFN can modulate its trust in the close: days since each player's last match, same-event flag, qualifier flag, and the logged / unlogged state.
  * The model now has only `round` and `sets_14d` as proxies.
* **N3. Qualifiers' fresh form** (suggestion; if I1b's one-fresh contrast shows the model weakest).
  * *Observed* (Stage 0, 2015–24): box scores exist for 86–99% of tour qualifying matches, but only 67–68% of **Slam qualifying** matches and 0% of ITF matches.
  * A qualifier entering a Slam's round 1 often lacks its freshest matches in the model's form inputs, while the market watched them.
  * The Slam feeds (Wimbledon 2019 and 2021+; US Open 2022+, fully from 2025) can fill part of that from points. This is a data repair with a precise target.
* **N4. Long memory after a surface switch** (B′; the secondary contrast in F1).
  * If the stale-match edge concentrates after surface switches or long layoffs, the trait-side investment is deeper per-surface point profiles from A1's table.
  * That is where point-by-point data would serve reading B.

---

## 5. Notes for the main session

* **Stored forecasts:** `meta_stack/walkforward.parquet` (the 54-input predecessor) is the only full 2014–24 source with both `p_base` and `p_noodds`. Use the `elo_off` arm (2019+) as a robustness check. Any arm that eventually runs must be built on the 58-input frame.
* **`stage3_ratings` p_serve is a sequential Glicko-type serve/return rating:** event and round order, earlier rounds of the same event included, constants tuned 2013–18. It counts as own-history in order under the 5 Oct classification, so it is usable as the pre-match offset in F1–F3.
  * **Pooled constants are cross-player** and are frozen on ≤ 2018: the de-noising priors, tour norms and propensity baselines.
* **The 2022–24 window has been read for I1's subsets.** Label every 2022–24 result that re-expresses those subsets "not blind", and carry them to the shared 2025–26 final test. Holm across both studies' arms there, as the auditor asks.
* **Ledger:** F1 has 6 primaries; F2 has 4 (plus 3 secondary); F3 has 1; F4 has 1. Everything else is labelled exploratory.
