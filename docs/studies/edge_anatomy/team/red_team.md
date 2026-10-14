# Red team (round 2): what is wrong, overstated or fragile in the edge-anatomy draft

12 Oct 2026 · Role: the red team ([brief](../briefs/04_red_team.md)) · Claude Opus 5.5, a subagent of session `6483c720-30a3-46ff-9519-287690b6f9d8` · For the lead's synthesis, not the owner's report.

* **Outcomes read:** H-exposed and earlier only. I read `analysis.parquet` (ends 28 Jul 2026), and `model_frame.parquet` of the instance and of the frozen 8 Oct reference with `tournament_date < 2026-07-29` applied in the read. **No sealed match was read.**
* **My code** is in `data/studies/edge_anatomy/team/red_team/` (`rt_*.py`, outputs `rt_*.csv`). It imports none of the lead's `edge_anatomy` modules. It reads the 4-seed L1/L2 fit files and the lead's CSVs only to compare.
* **Conventions:** mLL, + = the second-named forecast better. "Better"/"worse" only when the 95% interval (four-week blocks, t on G − 1) clears 0. Otherwise "unresolved (P …)".

## 0. In brief

* **Every headline number reproduces.** That includes the stored forecasts themselves, rebuilt from the 16 seeds to 1.8e-12. The arithmetic is sound and no sealed result was read.
* **The problems are in the reading:**
  * **in-sample numbers presented as forward-looking;**
  * **a women's "fade"** that coincides with the switch of the odds feed;
  * **a recommended process** whose "confirm on recent closes" step was tested and made things worse;
  * **a wrong "price alone" figure;**
  * **a banned "tie";**
  * **attributions that move** with collinear families;
  * **a multiplicity claim** that does not hold;
  * **a map** that does not match the study's own ledger.

## 1. Re-derivations

| README claim | README | Mine (independent code) | Verdict |
|---|---|---|---|
| § 3 gain over the recalibrated price, 2025–26 | both +1.71, men +2.83, women +0.53 | +1.71 [+0.74, +2.68]; +2.83 [+1.27, +4.39]; +0.53 [−0.67, +1.73] (P 0.82) | exact. Robust to block shifts for the window, not for single seasons (men 2025 becomes [−0.35, +5.17] with blocks shifted 14 days) |
| § 3 money, men at BetOnline | +5.3% [+2.3, +9.8] | +5.32% [+2.2, +9.8] | same |
| § 5.2 men's schedule / IOS worth | +1.11 / +0.83, better | +1.105 [+0.073, +2.137] / +0.832 [+0.160, +1.504] | exact (but see F6) |
| § 4 transparent model against the current model | +1.75 vs +1.71, difference +0.04 | +1.75 [+0.54, +2.96]; +0.04 [−0.50, +0.57]; same λ path (1000, 10, 10, 1000, 10000, 10, 1000) | exact (but see F5) |
| § 6 the process test | decade +1.47 [+0.67, +2.27]; recent +0.00 | identical; selection z's to 1e-15 | exact (but see F3) |
| § 4.4 "price alone" | +0.25, about a seventh | **stage 1: −0.07 [−0.53, +0.39]** | **wrong row** (F4) |
| § 2 favourite disagreements | 2.5% | 2.7% | minor |

## 2. Findings

**F1. Blocker: § 1 presents an in-sample edge and return as if bankable.**
* **What § 1 says:** "The recent edge is real for men", "+5% per unit staked".
* **Why it is in-sample:**
  * Every input, the stage-2 speed term (decided on 2024–26) and the Pinnacle-first input (decided on 2020 – Jul 2026) were chosen with 2025–26 in view.
  * `feature_provenance` says to "treat 2025–2026 as development, not as a holdout".
  * CLAUDE.md: "The edge that sizes bets comes only from matches no choice has seen."
* **Regression to the mean:**
  * Men moved from +1.23 (2020–24) to +2.83 (2025–26): a difference of +1.60, z 1.88, p 0.06.
  * The seasons range from −0.86 (2023) to +3.45 (2026).
  * The better forward estimate is the pooled **2020–26 men's +1.67 [+0.94, +2.39]**. Men's return at BetOnline was +2.1% in 2020–24.
* **Against Pinnacle's own closes (Jan–Jul 2025)**, the men's gain is +1.63 [−1.32, +4.59] (P 0.88).
* **Fix:**
  * Lead with "2025–26 helped choose the model; it is a backtest, not a test".
  * Give 2020–26 as the expected size. Say the sealed matches decide.
  * Quote no ROI without that caveat beside it.

**F2. Major: the women's edge has not been shown to have faded. The shortfall coincides with the odds-feed switch.**
* **The difference test:** 2025–26 against 2020–24 is −0.49, z −0.68, p 0.49. The women's 2022 season alone was −0.18.
* **Split by feed:**
  * Fed Pinnacle's close (to 7 Sep 2025): **+1.24 [−0.44, +2.93] (P 0.94)**, the 2020–24 level (+1.02). By source: tennis-data +1.23, OddsTrader +1.86.
  * Fed BetOnline's line: −0.15 (by source −0.59 [−2.34, +1.17]). Against the books' average close in 2026: −2.10 (P 0.13).
* **§ 5.4 does not hold at the level of the whole edge.** It says "both stopped working in 2025, already before the switch".
  * Before the switch, schedule (+0.90, P 0.95), form (+0.73, lower bound 0.00) and price shape (+0.35) still carried it.
  * After it, form, IOS and price shape are all negative.
* **A plausible mechanism:** the women's edge was "mostly a curved calibration of the odds" (`tabpfn_thinking`). A curve learned on Pinnacle inputs need not transfer to BetOnline's line.
* **Fix:**
  * Say: "unresolved; not distinguishable from 2020–24; the shortfall starts when the input switched to BetOnline".
  * Test the feed (a slope per source, the architect's #4) before any market reading.
  * Re-read after Pinnacle's 2025–26 closes are obtained.

**F3. Major: the recommended process is not what was tested, and its "confirm" step was tested and hurt.**
* **The confirm step.** § 1 and § 6 recommend "discover over many seasons, **confirm on the most recent closes**, estimate on everything". `advice.py` tested the confirm step as its "both" rule (decade, and the same sign in 2023–24), and the README omits it.
  * Both tours, against the decade rule alone: **−0.58 [−0.96, −0.20], worse**. Men −0.45, worse; women −0.71, worse.
  * It dropped exactly the statistics that turned out strongest in 2025–26: men's speed (2023–24 z −0.45) and women's `form_ace` (−0.15).
  * The process with confirmation delivered +0.89, about 52% of the edge, not 85%.
* **"Recent found nothing" is a threshold artefact.**
  * At |z| ≥ 2 the recent rule kept 3–4 inputs.
  * With as many inputs as the decade rule, recent selection gets **+0.84 [+0.35, +1.34], better**. Decade minus recent is then +0.63 [−0.02, +1.28] (P 0.97), unresolved.
  * At |z| ≥ 1.5, recent gets +1.06 [+0.49, +1.64].
  * The direction favours the decade rule; the size is overstated about 2.3 times.
* **"Never saw 2025–26"** is true of the code, not of the analyst.
  * `advice.py` was written after the ledger of 2025–26 per-input results had been read: "persistent… speed, sets_14d, age, surf_layoff".
  * The pool was itself chosen on 2022–26.
* **For the lead:** 60 random subsets of the same size (λ 1000) reach a median of +0.57, at most +1.15, never +1.47. The decade rule does beat chance selection.
* **Fix:**
  * Report the equal-size and confirm-step rows.
  * Restate the rule: "discover and estimate on many seasons; use recent seasons to monitor, not to veto".
  * Drop "never saw" for "selection code read no 2025–26 result".

**F4. Major (factual): "+0.25, about a seventh" is the both-stages row of arm L1.**
* That row includes the men's speed offset: men +0.61 with stage 2, −0.01 without.
* **The price-only TabPFN (stage 1):**
  * **−0.07 [−0.53, +0.39]** in 2025–26;
  * **+0.26 [+0.04, +0.48], better**, in 2020–24.
* Price plus context (L2, stage 1): −0.09 in 2025–26; **+0.32 [+0.09, +0.54], better**, in 2020–24.
* A walk-forward tour × level slope recalibration: −0.07 (2025–26), −0.24 (2020–24).
* The conclusion strengthens: in 2025–26 no re-drawing of the price is worth anything.
* **Fix:** correct the number. Use L1/L2's 2020–24 → 2025–26 change as the README's example of a vanished part (see F6).

**F5. Major: "ties", and a selected window.**
* The reporting rule bans "tie". § 4 point 2 "ties it" and § 1 "scores the same" break it.
* **2025–26 is the transparent model's best window:**
  * 2020–24: −0.36 [−0.75, +0.04] (P(better) 0.04);
  * **2020–26: −0.25 [−0.57, +0.07] (P 0.06)**;
  * every λ between 10 and 1000 gives +0.05 to +0.09 in 2025–26, so the result is not λ luck.
* **Fix:** "Indistinguishable in 2025–26 (+0.04, P 0.56). Over 2020–26 the glass-box model gets about 80% of the edge and trails by 0.25 (P(better) 0.06)." The conclusion that architecture is not the bottleneck survives.

**F6. Major: the anatomy's parts overlap, so their sizes and ranks depend on the attribution.**
* **The parts do not add up.** Men 2025–26: they sum to **+3.83** against a total of +2.83. Some parts offset others:
  * ratings and price shape, r −0.35 (−0.60 in 2020–24);
  * form and IOS, −0.33;
  * ratings and IOS, +0.37.
* **Two other defensible attributions:**
  * *unique:* the surrogate refitted without the family;
  * *alone:* the family with price shape only.
* **What survives them:**
  * Schedule's "better" (+1.11 [+0.07, +2.14]) does not: unique +0.58 [−0.19, +1.36], alone +0.73 [−0.04, +1.50].
  * IOS does: unique +0.66 [+0.07, +1.25], alone +1.17.
  * **§ 6's market-learning example fails.** "Ratings added +0.65 for men in 2020–24 and nothing in 2025–26": the unique ratings part in 2020–24 is +0.13 [−0.10, +0.37]. The scan's ratings family is about 0 in every era. BetOnline's close already priced ratings in 2020–24 (z_close −1.15 to +1.11).
* **Men's 2025–26 looks like 2020–24 scaled up.** Schedule, form and IOS hold similar shares in both windows, each realised about twice as strongly. That fits a common factor (luck, or the softer 2026 benchmark) better than family-specific market change.
* **Fix:**
  * Say the parts overlap and give unique-part ranges.
  * Drop the ratings example.
  * Rank only what survives every attribution: IOS for men, schedule for women.

**F7. Major: § 9's multiplicity sentence is false as written.**
* **On the lead's own normal p-values** (`ledger.csv`), men's `sets_14d` and `age` have q 0.11, so § 1's first-listed source fails a 10% FDR in 2025–26.
* **With 21 blocks, p should come from t(20):**
  * Men pass at 5%: `iosO_hold` 0.012, `iosO_bp_saved` 0.019, speed 0.019, `iosD_first_won` 0.048.
  * Men at 10% only: `prod_hold`, `prod_bp_saved`, `form_bp_saved` (0.079).
  * Men failing 10%: `surf_layoff` 0.110; `sets_14d` and `age` 0.147.
  * **No women's lead passes 5%:** `form_ace`, `form_first_won` and `surf_layoff` 0.063; `form_bp_saved` 0.092; `form_hold` 0.107; `sets_14d` 0.144.
* **The count overstates the independent signals.**
  * The seven men's discoveries are about three: the serve/return cluster, speed, `form_bp_saved`.
  * The "never priced" label's second z (BetOnline's close) re-uses the same matches, with the same price in 2026.
* **Fix:** use t(G − 1) p-values. Say which leads survive. Defend the schedule items by their pooled 2013–24 evidence (z 3.5 for `sets_14d`), which is their real support.

**F8. Major: the map (§ 5.1) does not match the study's own ledger.**
* **"Learned by the close: every win/loss rating".**
  * In 2025–26 the ledger gives that label to **one** rating, women's `elo_surf_offset`.
  * Men's overall Elo moves −0.26, ranking points +1.25, games-Elo +1.54.
  * Under `leads.py`'s own rule (|z_open| ≥ 2), most ratings were "priced" in 2020–24 too.
* **"Never priced… Both: rust on the surface, recent match load".** The ledger says men "mixed" and women "partly learned".
* **"Priced… double faults".** Men's `form_df` is "never priced" (z 2.18).
* **§ 5.1 against § 5.2:** "men's form: priced", yet form is worth "+0.81, better". Explain that the family helps jointly although no single form statistic beats the close.
* **The open is soft.** It is BetOnline's first OddsTrader capture. A move toward any strength-correlated input partly measures that soft line converging, not bettors "learning".
* **Fix:** generate the table from `ledger.csv`, and footnote the open.

**F9. Major: speed is presented as durable and "never priced". Net over 2020–26 it adds nothing.**
* **Stage 2, men, by season:**
  * 2022 +0.33, better;
  * **2023 −1.32 (P 0.03)**;
  * 2025 +0.37;
  * 2026 +0.80;
  * **2020–26 −0.02 [−0.30, +0.25]**;
  * 2020–24 −0.24 (P 0.09).
* **It was decided on 2024–26.**
* **Its 2025–26 z is concentrated in the BetOnline-fed months:** 4.05 against 1.56 Pinnacle-fed. By era: 0.38, 1.29, 3.89, −0.45, 3.79.
* **Fix:** "unstable: helped in 2022 and 2025–26, cost 1.3 in 2023; about zero net; the 2025–26 reading is in-sample".

**F10. Major (narrative): the causal stories are untested, and one is contradicted.**
* **Break points.** "Break-point saving is luck that bettors read as skill" predicts the same sign on both tours. Women's recent break points saved is **+2.96** in 2025–26; men's is −2.79.
* **Fatigue.** "Match rhythm beats the market's fear of fatigue": `sets_14d` counts this event's sets, so it also measures progress through the draw.
* **The men's serve/return asymmetry** is absent in 2024 (z +0.42). The sign is unstable since 2013 (+1.01, −2.25, −0.66, −0.61, −4.44).
  * *In its favour (my check):* it survives both feeds (−2.84 / −3.15), outside the Slams (−4.47), and in the pre-layer 8 Oct frame priced on the books' average (−3.85). It is not a data artefact I could find.
  * But it is a one-window lead, and § 1 lists it without § 5.4's caveat.
* **Men's `sets_14d` and `age`** are concentrated in the Pinnacle-fed months: z 4.18 / −2.71 there, 0.39 / −0.92 after.
* **Fix:** label the mechanisms as hypotheses. Carry the caveat into § 1.

**F11. Minor: the underdog bullet overreaches.**
* "Rules out the classic explanation…": the underdog-lean minus favourite-lean gain is **+1.09 [−1.04, +3.22]**, unresolved.
* The benchmark already carries a per-tour slope, which removes a linear favourite–longshot bias by construction.
* "59% of the gain in the top fifth" is what any right-sized nudge gives: that fifth holds 65% of E[w·d²].

**F12. Minor: "Three independent views agree" is premature.**
* View 3 (§ 5.3) is pending.
* The views read the same outcomes, so they are not independent.
* The scan's cross-fitted families resolve only speed for men: schedule +0.31, form +0.22, IOS +0.46, each unresolved.

**F13. Minor: inconsistencies.**
* BetOnline's softness: 0.8 mLL in § 3 against the same-match check's +0.43 (men +0.50).
* Favourite disagreements: 2.7%, not 2.5%.
* "About 9 statistics per tour": 10 men, 8 women.
* "Unpriced in nearly every season since 2013": these are eras, consistent in sign but significant in 1–3 of 5. Men's schedule family is −0.07 in 2013–16 and 0.00 in 2023–24.
* § 4.3: compare like with like. Against the expanding transparent model: last-2 −1.01 [−1.95, −0.07], worse; last-4 −0.61, worse; decay −0.33 (P 0.08).
* "Women's two parts worked in 2020–24" omits schedule (+0.65) and form (+0.43), both better. The non-linear rest was −0.46, worse, for women in 2020–24, not "worth about nothing".
* Verdicts on tour slices in § 1 go beyond the declared primary (both tours).

**F14. Minor: intervals with few blocks.**
* The men's OddsTrader-Pinnacle row (318 matches, G 8) reads +8.04 [+6.60, +9.48]. Its cluster SE is 0.61 against an iid 2.39.
* Do not quote intervals with G < 10.
* The headline's cluster and iid SEs agree (ratio 0.96–1.04).

**F15. Minor (hygiene).**
* The practitioner loaded the full frame, a_won included, to list columns. No value was used, but `pq.read_schema` avoids it.
* The process log should note that `advice.py`'s rule was designed after the 2025–26 ledger was read. Its "results seen" column implies it; the README contradicts it.

**What held up:**
* No sealed read.
* Correct walk-forward slopes and λ selection.
* The surrogate reads no outcome.
* The men's 2026 edge holds against the books' average close (+3.40 [+0.24, +6.57]), not only against BetOnline.
* Recent-window training is worse.
* The decade rule beats random selection.
* The men's serve/return lead is not a layer, feed or Slam artefact.

## 3. The scout's five expectations, scored

| # | Expectation | Result | Score |
|---|---|---|---|
| 1 | Men carry most of the gain, at the Slams and 250s | Men 85%. Within the men's gain: 1000s 44% (+4.50 [+1.60, +7.41], better), 250s 29% (+2.58, better), Slams 18% (+2.57, unresolved), 500s 7% | Half right: the 1000s lead, not the Slams |
| 2 | Larger where the lower-level share gap is ≥ 0.5, on-site counts differ, or a player returns after ≥ 6 weeks | No such columns in `analysis.parquet`. The nearest proxy, surface layoff, is a lead (men −2.47, women −3.26) | Untested |
| 3 | Stage 2 adds about +0.3 for men | +0.54 [+0.20, +0.89] in 2025–26, so the interval covers +0.3; −0.02 over 2020–26 | Consistent for the window |
| 4 | Part of 2026's gain sits at favourites ≥ 90% | 2026, ≥ 90%: −3.84 [−24.2, +16.5] (165 matches). Below 90%: +2.18, better | Not supported |
| 5 | A weak women's 2026 is a data flaw before a market verdict | Jun–Jul 2026 (lower levels missing): +0.85 (P 0.66), so not that flaw. The shortfall starts with the BetOnline feed (F2) | Right in spirit, wrong mechanism. The README read it as a market verdict |

## 4. Recommended changes to the README

1. **§ 1, bullet 3:**
   * Change it to: "In 2025–26 the model beat its price by +1.7 (men +2.8, women +0.5 unresolved). These seasons helped build the model. Over 2020–26 the edge is +1.3 (men +1.7). The sealed matches from 29 July decide."
   * Move § 9's first bullet here.
   * Pair "+5%" with "+2% in 2020–24".
2. **Women:**
   * Replace "has not held up" and "faded" with F2's wording.
   * Recommend a source-specific anchor test, and Pinnacle's 2025–26 closes (the decided retrain plan), before any market reading.
3. **§ 4:**
   * Remove "ties" and "scores the same". Report 2020–26 (−0.25, P 0.06).
   * Correct point 4 to −0.07 (stage 1). Add L2's −0.09.
4. **§ 5.2:**
   * Add one sentence: the parts overlap and do not add.
   * Give the unique-part column. Drop schedule's "better" for men, or show its range.
   * Re-label speed (F9). Drop "durable since 2013" from the table.
5. **§ 5.1:** rebuild from `ledger.csv`. Explain that "learned by the close" refers to BetOnline's first observed line.
6. **§ 5.4:**
   * Mark the mechanisms as hypotheses.
   * Report the women's opposite break-point sign.
   * Say the men's serve/return pattern was absent in 2024 but survives every artefact check run.
7. **§ 6:**
   * Replace the ratings example with L1/L2 (+0.26 / +0.32, better, in 2020–24, about 0 in 2025–26). It may be market learning or the feed change.
   * Add the equal-size and confirm-step rows.
   * Restate the process: **discover and estimate on many seasons; confirm on sealed future matches, not on the last two seasons.**
8. **§ 8, my recommendations:**
   * **(a)** Pre-register now, with signs, the five leads for one sealed look:
     * the men's serve/return cluster;
     * men's speed;
     * `sets_14d` (both tours);
     * surface layoff (both tours);
     * women's serve form.
     Use one look date, about 5,000 matches, early 2027. Bundles, not members.
   * **(b)** Obtain Pinnacle's closes from August 2025, the practitioner's #1. That settles the 2026 benchmark, the women's question and the retrain.
   * **(c)** Keep the family layer as a monitor only: re-sizing lost in walk-forward (`layer.py`).
   * **(d)** Keep the transparent model as a glass-box shadow for attribution, not as a replacement.
   * **(e)** Quarterly re-checks can watch for harm. At a quarter's sample they cannot admit or drop a single statistic: one tour-season resolves about 1.5 mLL.
9. **§ 9:** correct the multiplicity sentence (F7). Add: the 2025–26 numbers are in-sample for the speed stage and the odds-input rule.

## 5. Reproduction

`./python.sh data/studies/edge_anatomy/team/red_team/<script>`, CPU only, minutes each:
* `rt_headline.py`: § 3, block sensitivity, feed and source splits.
* `rt_anatomy.py`: § 5.2 and the alternative attributions.
* `rt_residual.py`: § 4 at every λ, 2020–26.
* `rt_advice.py`, `rt_advice_confirm.py`: § 6, thresholds, equal size, placebo, the confirm step.
* `rt_checks.py`: lead splits, t-based multiplicity, the underdog lean, return by feed, L1.
* `rt_reference_ios.py`: the serve/return lead on the 8 Oct frame.

Each writes `rt_*.csv` beside it.
