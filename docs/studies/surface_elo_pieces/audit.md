# Audit of the surface-Elo strategy, its evidence and its harness

6 October 2026 · Independent audit of [strategy.md](strategy.md) (draft for audit), `src/eda/surface_elo_pieces/`, `test/surface_elo_pieces/` and `data/studies/surface_elo_pieces/`. This is not a decision.

**Labels.** *Observed*: computed in this audit or read from a file. *Inferred*: a reading of observations. *Suggestion*: a proposal.

**Key for every score.** Log loss: lower is better. Gains are in milli-log-loss (mLL); a positive gain means the named model (or the second-named) has the lower log loss and is better. Brackets are paired 95% intervals clustered in four-week blocks of tournament dates. A range that spans 0 is a **tie**.

**Scope and constraints.**
* No paid call or network request was made. No existing file was edited.
* Every new number comes from the scratch scripts listed in the appendix (`data/studies/surface_elo_pieces/audit_scratch/`).
* No 2022–2026 result was computed for the new inputs, so the test seasons stay unseen. The 2026 identity check below reads features and market prices only.

---

## 1. Verdict

**The confirmation stage should not run as pre-registered until two zero-cost amendments are made (B1, B2).** The pilot can run once two things are settled:
* **S1, the composition of `primary`.** The pilot runs `primary`.
* **S3, a usage reading between fit and prediction.** Without it the pilot cannot meet its stated purpose of confirming that the fit is unbilled.

What holds up (observed):
* **No leak found** in any new input. Independent probes cover:
  * the two new Elo modes, which the author did not probe;
  * a brute-force recomputation of the four surface-switch quantities;
  * a probe that deletes later matches;
  * the season boundary.
* **The evidence reproduces.** Every headline number in strategy §3–4 matches to the printed precision. Most were recomputed with independent code (sklearn fits, own cluster interval); the rest were recomputed from the logged counts (§3).
* **The base arm is exact.**
  * It is the leak-proof upload value for value, including the 2022 fold's training set.
  * All 97 job fingerprints recompute from `frame.parquet`.
  * The 10 tests pass.
* **The guard is safe.** It cannot bill a prediction twice or silently re-use another job's probabilities.
* **The offset Elo's gain is genuinely about surface** (new control below). This is stronger support for principle 1 than the strategy itself gives.

What must change:
* **B1. The 2026 identity split.** WTA players re-appear under new IDs from June 2026, with no history at all. This affects:
  * 73 test matches;
  * 55 of the 297 women's grass matches of 2026;
  * 6.6% of the "grass and both new" cell.

  The strategy (§7) understates this. Pre-register how these matches are handled.
* **B2. Power.** Projected from a free flexible model on the pilot's folds, the confirmation's minimum detectable effect at 80% power is about 0.8 mLL. The strategy expects any gain within ±0.4 mLL, so a tie is the likely outcome even if the idea helps. Pre-register:
  * the MDE, computed from the pilot;
  * how a tie will be read;
  * a seed rule.
* **S1 (should fix, before the pilot).** Two of the four new pairs have negative or null evidence:
  * career surface counts are worse or tied beside the offset Elo in every linear fit, including capped forms;
  * last season's form adds about nothing.

  Without the odds, the evidence supports the offset Elo, this season's surface counts and the layoff. With the odds, every piece ties.

---

## 2. Findings

### BLOCKING: amend before the confirmation stage

**B1. The 2026 WTA identity split contaminates the test, and most of all its grass and "both new" subsets.**

*Observed* (`check_frame_jobs.py`; the queries in §5):
* **Rows with almost no history.** Frame rows with a player who has fewer than 20 rated matches number 0–16 per season and tour in 2013–2025, and **73 in 2026 WTA**.
  * By month in 2026 WTA: January–May 0; June 55 of 297; July 18 of 181.
  * 43 of these matches have a player with **zero** rated matches. Many Queen's Club and 's-Hertogenbosch 2026 matches have both players at zero (`N_a = N_b = 0`), at normal prices.
* **The players are new IDs.** IDs of the form `wta:3xxxxx` fill 3.4% of the 2026 WTA player slots and none in 2021–2025.
* **A clean rule finds the same matches.** "A player whose first Stage 0 match (any level) is in the current season" flags exactly the same 73 matches in 2026, against 0–7 main-tour matches per season in 2014–2025.
* **Share of each test cell:**

  | Cell | Affected | Share |
  |---|---|---|
  | All test matches | 73 of 23,819 | 0.31% |
  | Grass | 55 of 3,089 | 1.8% |
  | Both new | 51 of 2,159 | 2.4% |
  | Grass and both new | 50 of 753 | 6.6% |
  | The 2026 season | 73 of 3,488 | 2.1% |

* **The split players look brand new.** In 2026, 1.0% of player-A rows sit at the layoff cap ("never on this surface"), against 0.04–0.23% in other seasons.

*Inferred.*
* In these matches every arm sees established players as brand-new (Elo 1500 and reset histories), at odds that say otherwise.
* `primary`, `literal` and `switch_only` add eight columns that all say "never played this surface" (career 0, layoff at the cap, form 0). The training data holds almost no such rows, so the damage can differ by arm.
* 73 matches are a small share of the pooled endpoint. But a per-match log-loss difference of 0.05 between arms on them would move the pooled gain by about 0.15 mLL, the same order as the effect the study expects. They dominate the grass subset of 2026 and weigh on the 2026 season-as-sample.

*Fix.* Before any confirmation call, pre-register one of these:
* **(a) Recommended, costs nothing.** Leave the 73 matches out of the primary endpoint and every secondary. Define them by the rule above: a player whose first Stage 0 match is in 2026. Report the full population as a sensitivity. The jobs, fingerprints and quotes do not change.
* **(b)** Repair the IDs and rebuild. This is not advised now: the 53 inherited base inputs carry the same split, so the base arm would stop being the best model's representation.

Also correct §7 of the strategy: the split is concentrated, not diffuse.

**B2. The confirmation is not powered for the effect it expects, and the pre-registration does not say so.**

*Observed* (`career_caps_and_power.py`):
* **Proxy run on the pilot's folds.** A free flexible model was trained exactly like the pilot: sklearn HistGradientBoosting, with the odds, season Y in 2019–2021 trained on 2013 to Y − 1, both orientations averaged.
  * `primary` against `base`: **−0.02 [−0.86, +0.83], a tie**, on 12,105 matches. The paired SE is 0.41 mLL and the RMS log-odds difference between the arms is 0.092.
* **Projected to the confirmation's 23,819 matches:**
  * SE 0.29 mLL, a 95% half-width of 0.58;
  * **MDE at 80% power 0.82 mLL**;
  * power 17% for a true +0.3 mLL and 40% for +0.5.
* **SE tracks how far two forecasts move apart.** On the same 23,819 test matches (57 blocks), existing forecast pairs, none using the new inputs, give SE ≈ 2.4–2.8 mLL per unit of RMS log-odds difference:

  | Pair | SE (mLL) | RMS log-odds difference |
  |---|---|---|
  | Market vs TabPFN-Thinking | 0.32 | 0.134 |
  | TabPFN-Thinking vs its leak-proof refit | 0.040 | 0.015 |
  | Linear "everything" vs + profile | 0.25 | 0.092 |
  | Additive boosting vs full boosting | 0.26 | 0.095 |
  | Linear (odds + all 47 inputs) vs boosting with odds | 0.45 | 0.167 |

  So **MDE80 ≈ 7 × the RMS log-odds difference** between `primary` and `base`: about 0.4 mLL if they differ by 0.05, and about 0.7 if they differ by 0.10.
* **The strategy's own expectation sits below that** (§5, line 128): "any gain within ±0.4 mLL".

*Inferred.*
* The most likely confirmation outcome is a tie, whatever the truth at the +0.3 to +0.5 level.
* A tie read as "the idea does not help" would be an over-reading.
* The seasons-as-samples interval (t on 4 degrees of freedom, multiplier 2.78, a partial 2026) is weaker still.

*Fix* (text only, before the confirmation):
1. **The MDE.** Compute it from the pilot: the paired SE of `primary_s0` against `base_s0` on 2019–2021, scaled by √(12,105 / 23,819). Allow for seed averaging using the pilot's own seed-noise estimate. Record the result before any confirmation call.
2. **The reading.**
   * Interval above 0: better.
   * Interval below 0: worse.
   * Otherwise: a tie, reported with its MDE.
   * A tie with MDE > 0.4 mLL is "inconclusive at the expected effect size", not "no effect".
3. **The seed rule.** If base seed 0 and seed 1 return identical probabilities, run the confirmation with seed 0 only. `random_state` is part of the classifier config the SDK sends (`tabpfn_client/api_models.py:79`), but whether the hosted model honours it is unverified. Without the rule, two thirds of the 1.27M quoted tokens could buy nothing.

### SHOULD FIX

**S1. `primary` includes two pieces that the design-year evidence says are null or harmful.** Decide this before the pilot, which runs `primary`.

*Observed* (`rederive_evidence.py`, `career_caps_and_power.py`; linear fits forward-chained over 2016–2021, own code):

| Added beside the offset Elo | Men | Women |
|---|---|---|
| **No odds**, main tour, against the offset Elo alone: |  |  |
| this season's surface counts (log difference) | **+2.11 [+0.99, +3.23] better** | **+3.66 [+2.50, +4.83] better** |
| days since the last surface match | **+1.70 [+0.87, +2.53] better** | **+1.93 [+0.84, +3.01] better** |
| last season's form | +0.17 [+0.00, +0.34], better by a hair | −0.06 [−0.18, +0.06] tie |
| career surface counts (log difference, as in `evidence.py`) | **−0.75 [−1.41, −0.08] worse** | −0.20 [−0.51, +0.10] tie |
| career counts capped at 10 / 20 / 40, or an indicator for fewer than 20 | −0.20 to −0.44, all ties | +0.04 to +0.15, all ties |
| **With the odds**, against odds + offset Elo: |  |  |
| career counts (log difference) | **−0.13 [−0.23, −0.04] worse** | −0.10 [−0.34, +0.14] tie |
| career counts capped at 40 | −0.11 [−0.21, −0.00], worse | −0.12 tie |
| career counts capped at 10 / 20, or the indicator | ties (−0.07 to −0.09) | ties (−0.02 to −0.12) |
| **With the odds**, against the odds alone: |  |  |
| this season's counts alone | +0.00 [−0.08, +0.08] tie | +0.41 [−0.01, +0.82] tie |
| both tours pooled | +0.22 [−0.01, +0.44] tie | |

Further observations:
* **No odds, beyond the offset Elo alone** (paired against the same offset-only fit):
  * season counts + layoff: +2.56 [+1.36, +3.75] (men), +3.83 [+2.53, +5.12] (women), both better;
  * all four pieces: +2.11 [+0.85, +3.36] (men), +3.77 [+2.43, +5.12] (women), both better.

  Comparing these two point estimates (no interval of its own), adding career counts and form to season counts + layoff costs about 0.45 (men) and 0.06 (women).
* **The inexperience penalty principle 3 relies on is smaller beside the offset Elo, and priced.** Wins minus expectation for players with ≤ 5 / 6–10 / 11–20 career surface matches, on rows with odds:

  | | ≤ 5 | 6–10 | 11–20 |
  |---|---|---|---|
  | Men, against overall Elo (pts) | −5.8 | −4.8 | −4.7 |
  | Men, against the offset Elo | −3.8 | −2.3 | −2.1 |
  | Women, against the offset Elo | −1.9 | −1.2 | −1.4 |
  | Men, against the recalibrated market | +1.5 (SE 2.5) | −0.1 (2.2) | −0.5 (1.3) |

  Against the market the penalty is a tie.
* **Career counts drift because history starts in 2010.** The median career surface count on player-A rows rises from 100 (2013) through 172 (2016) to 215 (2025). The share below 20 matches is 7.4% in 2013 and 3.3–4.9% in 2015–2025. The input means less experience in the early training seasons than in the test seasons. The 3-year layoff cap has no such problem (see below).

*Inferred.*
* Principle 3 is not evidence-based as written. Nothing in the linear evidence, with or without the odds, favours career counts beside the offset Elo.
* Last season's form is redundant with the offset, which already integrates every past surface residual.
* Bundling these into `primary` lowers the chance of detecting the gain from the pieces that do carry signal, and B2 says that chance is already small.

*Fix.*
* **`primary`:** `base − elo_logit − surface_first + elo_overall + elo_offset + surf_season_a/b + surf_layoff_a/b` (58 columns).
* **`literal`:** keep career counts and form, which tests the owner's items 5 and 6 as written.
* **`switch_only`:** make it `base − surface_first + surf_season_a/b + surf_layoff_a/b`, so that `elo_only` and `switch_only` still decompose `primary`.
* **If career counts stay in `primary`,** say why against this evidence, and cap them at about 20.
* **Rebuild** the frame, jobs and quotes before the pilot.

**S2. One permanently failed seed job silently removes a whole season from the primary endpoint.**

*Observed* (`score_dryrun.py`; synthetic predictions in a scratch receipt folder):
* In `score.load`, `score.py:84-87` averages only rows where every seed is present.
* With one job missing (`confirm__primary__2024__seed2`), `p_primary` is missing for all 5,141 matches of 2024.
* The "pooled" primary comparison then runs on 18,678 of 23,819 matches, with no warning.
* The per-arm log-loss table (`score.py:151-154`) then also compares arms on different rows.
* The guard is designed so that a prediction with an unknown outcome is never retried (`guard.py:190-191`), so a permanently missing job is a realistic event.

*Fix.*
* Assert that every confirmation job of `base` and `primary` exists before the primary endpoint is computed.
* Pre-register the fallback. The cleanest: if any seed of either arm is lost for a season, the primary endpoint uses the seeds complete for both arms in every season, the same seeds for both.
* Report row counts beside every log loss.

**S3. As coded, the pilot cannot show that the non-thinking fit is unbilled.**

*Observed.*
* `guard.py:193` reads usage before the fit and `guard.py:217` after the prediction, with nothing in between. The bill delta therefore mixes fit and prediction.
* Bills have run below quotes before, so the quote cannot separate them.
* `LiveBackend.fit` uses the SDK's SYNC `_fit`, whose backoff retries once on a timeout (`tabpfn_client/client.py:622-638`).
* If fits are in fact billed, one timeout bills a fit twice. The strategy (§6, line 174) lists "confirm the non-thinking fit is not billed" as a pilot purpose.

*Fix.*
* Add a third `backend.usage()` reading between fit and prediction and save it in `COMPLETE.json`.
* In the pilot, check that the fit delta is 0.
* Keep the served model's identity from the returned metadata (`billing_model_version`, `tabpfn_config`), which the guard already stores, and confirm it is the intended non-thinking v3.5.

**S4. Pilot mechanics.**

*Observed.*
* In the pilot, `p_base` is the mean of seeds 0 and 1, but `p_primary` and `p_literal` are seed 0 only (`score.py:84-87`; dry run).
* The pooled pilot comparison "`primary` against `base`" therefore credits `base` with a two-seed ensemble. The seed-matched rows (`base_s0` against `primary_s0`) exist in the output.
* §6, line 176 says "a broken input would be fixed and the pilot re-run". But a fixed input changes the fingerprint, and the guard refuses a job directory that holds a different request (`guard.py:181-183`, `OnceOnlyError`).

*Fix.*
* Pre-register that the pilot is read seed-matched (`base_s0` against `primary_s0`).
* Name any re-run as a new stage (for example `pilot2`) with its own job IDs, so that receipts are never deleted.

**S5. Corrections to the strategy text.** Each is observed, from the files or the scratch outputs.

**Claims that misread or overstate the evidence:**
1. **The offset "grows with evidence"** (line 72–73: "with evidence it grows, so it weighs evidence by construction").
   * The offset averages, for players with more than 160 matches on a surface: men hard +60.1 (SD 20.9), men clay +76.9 (SD 23.3), women hard +48.0, women clay +60.2. It is positive on every surface, so it is a systematic shift, not "evidence".
   * *Inferred:* experienced players' offsets drift up as they beat surface newcomers, whom overall Elo overrates. The offset mirrors the inexperience penalty rather than measuring surface skill alone.
   * The new control shows that the gain is still surface-specific: R + D wins and a surface-blind version does not (§3). Say both.
2. **Principle 3** (lines 118–119, "3–7 points").
   * That range is men against overall Elo. Women are 2.4–2.8.
   * Beside the offset Elo, which `primary` includes, it is 2–4 points (men) and 1–2 (women).
   * The calibrated market prices it, and career counts make the linear fits worse (S1).
3. **"Re-anchoring … loses"** (line 45; the Elo-only table).
   * This tests the re-anchored rating moved with Stage 1's untuned K: 600 / (n + 2)^0.6 ≈ 396 Elo points at the first surface match for men (`pieces.py:138-140`).
   * It is not a test of re-anchoring as such.
   * The evidence-weighted anchored variant (k = 2 men, 10 women; men main tour +0.35 [−0.15, +0.85], tie) is not shown.
4. **The "only 0.1–0.8 mLL" weight-by-bin gains** are in-sample bests over 21 weights with an in-sample slope, so they are upper bounds. The range is 0.0–0.8.

**Omissions:**

5. **Career counts are missing from the evidence tables.** Line 48 lists what season counts, layoff and form add beyond the offset, but not career counts: −0.75 [−1.41, −0.08], worse (men). The "about" differences now have paired intervals (S1 table).
6. **The offset's gain is not stable over time.** Without the odds it is concentrated in 2019–2021 for men: +0.54 [−1.53, +2.61] tie in 2016–2018, against +4.17 [+1.82, +6.52] better in 2019–2021.
   * This is the opposite of what in-sample tuning on 2013–2018 would produce, so it is not overfitting.
   * It is heterogeneity worth a line. The same split with the odds is in §3.
7. **The priced table compares two populations** (`evidence.py:312-314`).
   * Elo residuals use all rows, including the men's 2018 season, which has no odds. Market residuals use the rows with odds and the raw, not recalibrated, market (`evidence.py:295`).
   * On one population with the recalibrated market, the reading holds. Men with ≤ 5 matches become −5.8 against Elo and +1.5 (SE 2.5) against the market.
   * The "> 200 days" hint is a tie in every cell: SE 1.2–2.7 points.
8. **The 31–34 mLL quote** (line 49) describes the men's main tour only, as does the whole market-anchoring study.
9. **Two clauses need the fixes above.** "A probe that flips later results moved no earlier value" (line 210) is true but tests only one quantity (suggestion G1). The §7 duplicate-ID line needs B1.

**A strength the strategy should state:**

10. **The 3-year layoff cap neutralises the 2010 truncation for every training season.** A player whose last surface match predates 2010 has a true layoff of at least 3 years at any match from 2013 on, so the capped value is exact. Observed: the share at the cap is 0.04–0.23% in every season except 2026, where B1 raises it.

### SUGGESTIONS

* **G1. Replace the surface-switch leak probe** (`pieces.py:236-258`).
  * It flips later results and the overall-Elo probabilities of later rows. That is a meaningful perturbation for `prev_res`.
  * But `season_n`, `days_since` and `prev_n` depend only on dates, statuses and surfaces, so the probe cannot move them by construction.
  * `check_switch_bruteforce.py` holds a truncation probe that deletes every match from a cut week on. Across four cuts it found no moved row.
  * Also run Stage 1's `probe_by_round` on the `anchored` and `offset` modes inside `pieces.py`. They pass (§3) but are not probed there.
* **G2. Give the offset as its own column.**
  * `elo_overall` and `elo_offset` correlate 0.980 in the frame. Their difference (L10 × (D_a − D_b)) has SD 0.228 log-odds, against 1.055 for `elo_overall`.
  * `elo_overall` beside the offset difference carries the same information with far less collinearity.
  * Information-equivalent in a linear model. For TabPFN it is a robustness choice, not a correctness issue.
* **G3. Pairs against difference + sum.**
  * The per-player pairs are information-equivalent to (A − B, A + B), so "both new" stays distinct either way.
  * Pairs let TabPFN learn g(x_A) − g(x_B) with a non-linear g. That suits an inexperience effect concentrated at low counts and TabPFN's mostly additive behaviour (thinking study: interactions explain about 2% of its adjustment).
  * Keep the pairs. Note that this encoding is untested in any free model here; the linear evidence used differences.
* **G4. Subset intervals.**
  * Over 2022–2026, grass has 10 four-week blocks (23 calendar weeks), "both new" 39 and "early" 55.
  * The design-year evidence already shows grass intervals such as women's 2019–2021 [−81, +73].
  * Report grass by calendar-week clusters or label it directional only.
* **G5. Harness housekeeping.**
  * `dispatch.py:59` overwrites the registered `quotes_<stage>.json` on every `--run`; write run-time quotes to a new file.
  * `guard.py:179` puts `http_timeout_s` in `request.json`, so changing only the timeout locks a job whose fit failed; leave it out of the comparison as the binding does.
  * Carry the raw season counts in the frame rather than `expm1(log1p(x))`. The round trip is exact at the threshold (3 → 3.0; 2 → 2.0000000000000004 < 3), so it is fragile, not wrong.
* **G6. Interpretation risks to state before the test.**
  * Results apply to non-thinking TabPFN-3.5. Whether they carry to the thinking model is untested.
  * The base inputs were chosen after their 2022–2026 results were seen. An arm that drops two of them (`elo_logit`, `surface_first`) loses that selection advantage, so the caveat does not "apply equally to every arm" (§2, line 34): it slightly favours `base`.
  * The ablations (`elo_only`, `switch_only`) have even less power than the primary endpoint, so attribution between the Elo and switch pieces will be weak.
  * The diagnostic's two readings omit two cases: both comparisons better, and better only with the odds. Its "priced in" reading of a tie with the odds inherits B2's MDE.
  * 2026 is a partial season (4 January to 28 July) heavy in clay and grass (40% and 17%, against about 28% and 12% in full seasons), so it is not exchangeable with the others as a season-sample.
* **G7.** `tune_offset` minimises the raw combined forecast's log loss (`pieces.py:168-169`), while every use recalibrates it: the offset's slope is 0.915 for men. Tuning on the recalibrated loss would match how it is used. Minor; Stage 1 does the same.

---

## 3. Numbers re-derived

### Strategy claims against independent code

*Observed.* Every strategy number below reproduces. Most rows were recomputed with independent code (sklearn logistic, own cluster interval). Rows marked † were recomputed from the counts and grids in `evidence.log` and `pieces_meta.json`.

| Claim (strategy.md) | Strategy | Re-derived | Match |
|---|---|---|---|
| Surface rating minus overall, men main tour, ≤ 0 / 3–5 / 160+ matches | −445 / −459 / −18 | −445.2 / −459.1 / −17.6 | yes |
| Re-anchored, men, 1–2 / 3–5 | −145 / −196 | −145.2 / −195.8 | yes |
| Offset, men, 81–160 / 160+ | +43 / +65 | +43.1 / +64.7 | yes |
| Elo-only 2019–2021, offset vs Stage 1 blend, men main tour | +4.50 [+2.06, +6.94] | +4.50 [+2.06, +6.94], better | yes |
| … men, all evaluation levels | +1.57 [+0.31, +2.83] | +1.57 [+0.31, +2.83], better | yes |
| … women main tour / all evaluation levels | +1.81 [−0.99, +4.61] / +1.44 [−0.27, +3.16] | the same, both ties | yes |
| Overall Elo alone vs blend, men main tour | −4.84 [−7.24, −2.44] | −4.84 [−7.24, −2.44], worse | yes |
| Re-anchored blend, men all evaluation / women main tour | −0.51 [−0.82, −0.20] / −0.55 [−1.08, −0.02] | −0.51 [−0.82, −0.19] / −0.55 [−1.08, −0.02], both worse | yes |
| With odds, Stage 1 blend, men / women | −0.06 / −0.04, ties | −0.058 [−0.147, +0.032] / −0.040 [−0.123, +0.044], ties | yes |
| With odds, literal pieces, men | −0.27 [−0.46, −0.08] | −0.267 [−0.460, −0.075], worse | yes |
| With odds, offset pieces, men / women | −0.09 / +0.06, ties | −0.085 / +0.062, ties | yes |
| With odds, switch differences, men / women | −0.05 / +0.40, ties | −0.048 [−0.210, +0.114] / +0.398 [−0.074, +0.870], ties | yes |
| No odds, offset vs blend, men / women | +2.16 [+0.58, +3.73] / +1.44 [+0.10, +2.77] | +2.156 [+0.578, +3.735] / +1.437 [+0.100, +2.774], both better | yes |
| No odds, overall + 1500-started surface rating, men | +0.10 [−0.23, +0.42] | +0.096 [−0.230, +0.422], tie | yes |
| No odds, the same + career counts, men | −0.83 [−1.76, +0.11] | −0.826 [−1.763, +0.112], tie | yes |
| Beyond the offset: season counts / layoff / form | about 2.1 / 1.7 / 0.2 (men); 3.7 / 1.9 / −0.1 (women) | see the S1 table (paired intervals) | yes |
| Opening grass week, both players flagged, men / women † | 61% / 62% | 60.7% / 62.1% | yes |
| Flag difference zero, men hard / clay / grass † | 92% / 80% / 65% | 91.8% / 80.1% / 64.8% | yes |
| Under 20 surface matches, share of grass player-rows, men / women † | 31% / 34% | 31.0% / 33.5% | yes |
| Priced: ≤ 5 career matches, men, against Elo / market | −6.9 / +0.5 pts | the same on the strategy's populations. On one population: −5.8 / +0.5 (raw market), +1.5 (recalibrated, SE 2.5) | the numbers yes, the population no (S5.7) |
| Priced: more than 400 days, men, against Elo / market | −14.1 / −5.0 | −14.1 / −5.0 (raw), −4.5 (recalibrated, SE 2.7, tie) | yes |
| k cost, men / women † | 0.6–1.8 / 0.4–1.0 mLL | 0.60–1.81 / 0.36–0.97 | yes |
| Offset tuning: best inside the grid † | yes | men (80, 10, 0.6), women (80, 20, 0.6); both interior | yes |
| Stage 1 reproduced by mode `stage1` | exact | exact (0.0). The `offset` and `anchored` passes also reproduce `pieces.parquet` exactly | yes |
| The 2022 fold equals the best model's training set | 39,918 | identical values, labels and order, against the leak-proof upload | yes |
| Quotes, pilot / confirmation | 138,724 / 1,268,961 | the same as `quotes_*.json` | yes |
| Tests | 10 pass | 10 pass | yes |

### New observations from this audit

**Leakage and time rule:**

| Check | Result |
|---|---|
| Stage 1's date-and-round probe, `offset` and `anchored` modes, 8 cuts per tour, men | 0 of 3,388,099 protected match-rows changed (335,061 later rows changed) |
| The same, women | 0 of 2,953,488 changed |
| Brute-force recomputation of `season_n`, `days_since`, `prev_n`, `prev_res` | 0 mismatches on 21,002 player-rows (400 random players) |
| Truncation probe: every match deleted from a cut week on (2018-06-20, 2023-07-24, 2024-08-19, 2024-12-09) | 0 rows moved |
| Season boundary | 0 player-rows whose previous-season surface matches include a match dated on or after the row's own date. The year label is the season: 2,171 matches dated 27–31 December carry the next year's label, consistently for `season_n`, `prev_n`, `prev_res` and Stage 4 |

**Frame and jobs:**
* 97 of 97 job fingerprints recompute from `frame.parquet`, with the right columns, windows and flips.
* The new inputs equal an independent recomputation (largest difference 0).
* `elo_logit` equals Stage 1's blend recomputed from the pieces (largest difference 2 × 10⁻¹⁴).

**Server limits** (v3.5, from the leak-proof preflight receipt):
* The limits are 1M training rows, 200M cells and 2.5 × 10¹¹ row-pairs.
* The largest job is 60,249 × 62 (3.7M cells) with 4.2 × 10⁸ row-pairs.
* In tabpfn-client 0.6.0 the classifier sends one `_predict` POST per prediction, with no chunking.

**The general-offset control** (`general_offset.py`). The same pass with every known surface mapped to one code, so the offset moves on every match; its K is re-tuned on the same rows and grid. 2019–2021, each forecast recalibrated on 2013–2018:

| | Men, all evaluation levels | Men, main tour | Women, all evaluation levels | Women, main tour |
|---|---|---|---|---|
| General offset vs Stage 1 blend | −4.39 [−5.72, −3.07] worse | −4.66 [−7.07, −2.26] worse | −3.56 [−5.19, −1.93] worse | −2.85 [−4.73, −0.98] worse |
| **Surface offset vs general offset** | **+5.97 [+4.04, +7.89] better** | **+9.16 [+5.81, +12.51] better** | **+5.00 [+2.81, +7.19] better** | **+4.66 [+1.77, +7.55] better** |

The general offset tunes to the grid's low-K corner (men 20, 40, 0.8; women 20, 2, 0.8) and performs like overall Elo alone. *Inferred:* the offset Elo's advantage comes from the surface structure, not from a second, general correction of the overall rating.

**With the odds, 2019–2021 alone** (outside the constants' tuning years), both tours, against the recalibrated odds:

| Added to the odds | Gain |
|---|---|
| Offset pieces | +0.06 [−0.24, +0.35], tie |
| Switch differences | +0.28 [−0.13, +0.68], tie |
| Literal pieces | −0.05 [−0.31, +0.22], tie |

**Market calibration slope, design years** (in-sample): 1.091 men, 1.102 women. This matches the thinking study's 1.09–1.10.

**Power:** see B2.

---

## 4. Recommended changes to the arms, the endpoint and the decision rule

| Item | As registered | Recommended | Why |
|---|---|---|---|
| `primary` | base − `elo_logit` − `surface_first` + `elo_overall` + `elo_offset` + 4 pairs (62) | base − `elo_logit` − `surface_first` + `elo_overall` + `elo_offset` + `surf_season` pair + `surf_layoff` pair (58) | S1: career counts are worse or tied in every fit beside the offset; form is null |
| `switch_only` | base − `surface_first` + 4 pairs (61) | base − `surface_first` + `surf_season` pair + `surf_layoff` pair (57) | keeps `elo_only` + `switch_only` as a decomposition of `primary` |
| `literal`, `elo_only`, `base` | — | unchanged | `literal` tests the owner's items as written |
| Offset encoding | `elo_offset` = L10 × ((R + D)_A − (R + D)_B) | optional: L10 × (D_A − D_B) as the column beside `elo_overall` | G2: less collinear (0.980), same information |
| Population of every comparison | all 23,819 test matches | leave out the 73 identity-split matches (first Stage 0 match in 2026); report all rows as a sensitivity | B1 |
| Primary endpoint | `primary` vs `base`, both tours, 2022–2026 pooled, four-week blocks | unchanged, plus an assertion that every `base` and `primary` job exists, and a pre-registered fallback to seeds complete for both arms | S2 |
| Decision rule | "better" only if the interval lies above 0 | better if above 0; worse if below 0; otherwise a tie reported with the pilot-projected MDE, and "inconclusive" when MDE > 0.4 mLL | B2 |
| Seeds | 0, 1, 2 in the confirmation | the same, unless the pilot's seeds 0 and 1 return identical probabilities; then seed 0 only | B2 |
| Pilot reading | pooled `primary` vs `base` (two base seeds) | seed-matched `base_s0` vs `primary_s0`; output the MDE projection; read the fit's billing from a usage reading between fit and prediction | S3, S4 |

Not recommended:
* **A one-sided test.** Stay two-sided, as the project's convention.
* **Repairing the identity split now.** The inherited base inputs carry the same split.
* **Adding arms.** Power is the binding limit, not the budget. The confirmation is quoted at about 6% of the monthly quota, and bills have run below quotes.

---

## 5. Appendix: scratch files (`data/studies/surface_elo_pieces/audit_scratch/`)

| File | What it does | Output |
|---|---|---|
| `probe_elo_modes.py` | Stage 1's date-and-round probe on the `offset` and `anchored` modes; reproduction of D and XA | `probe_elo_modes.json` |
| `check_switch_bruteforce.py` | Brute-force `season_n`, `days_since`, `prev_n`, `prev_res`; truncation probe | `check_switch_bruteforce.json` |
| `check_frame_jobs.py` | Fold 2022 against the leak-proof upload; 97 fingerprints; the new inputs recomputed; population facts | `check_frame_jobs.json` |
| `rederive_evidence.py` | Strategy §3–4 numbers with own code; split by period; priced table on one population; offset residuals | `rederive_evidence.json` |
| `general_offset.py` | The surface-blind offset control | `general_offset.json` |
| `career_caps_and_power.py` | Career encodings; power proxy on design years; SE against RMS log-odds difference of existing forecasts | `career_caps_and_power.json` |
| `score_dryrun.py` | `score.load` on synthetic predictions (missing seed job, pilot averaging, market recalibration) | `score_dryrun.json`; synthetic receipts in `fake_tabpfn/` |

The season-boundary, identity-split, drift and cluster-count queries were run inline with `./python.sh -c` (this audit's session log).

Run any script with `./python.sh data/studies/surface_elo_pieces/audit_scratch/<name>.py`. The tests' temporary folder is `audit_scratch/pytest/`. None of these files needs to be kept once the findings are resolved; deleting them is the owner's call.
