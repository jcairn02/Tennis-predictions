# R1 design proposal: integration strategist (TabPFN and market)

7 October 2026 · agent 3 of 5 · written independently (no other `design/1_*.md` read).

* **Labels:** **observed** = computed here (scripts and outputs in §12); *inferred* = reasoning; *suggestion* = not decided.
* **Gains** are in mLL; **positive = the named arm is better**. A 95% interval spanning 0 is a tie.

## 0. Recommendation in five lines

1. **Add one diff column, `spd_chg`.** It is A − B of each man's posterior 14-day first-serve-speed change, in a frozen SD, clipped at ±4. A side without a timed match in the last 14 days enters at its prior mean, 0. The column is NaN only when neither side has one, and **NaN for every woman**. There is no level, pair or precision column.
2. **Run four arms on the 58 inputs:** A1 `spd` (the primary); A2 `spd_raw`; A3, the auditor's pick; and A1's no-odds twin. The seeds are 0–15 (A1) or 0–7 (the others) in 2024–26, and 0–3 in 2019–23 for calibration. That is **220 fits, 2.1 h** at the logged speeds.
3. **Test men's 2024–26 in a fixed sequence.** **P1** is the coefficient of `spd_chg` given the calibrated base: is the information there? Then **P2** is A1's calibrated paired mLL gain over the base: the owner's "by how much". Everything else is descriptive.
4. **Power is low.** At a planning β of 0.05, P2 has 11–15% power and P1 about 30%. At the replication's β of 0.09 they have 45–51% and 73%. **A tie in P2 is the expected reading**; P1 tells "no information" apart from "TabPFN does not use it".
5. **Code:** this study's own `arms.py`, `local_fits.py` and `score.py`. The base's 16 seeds are reused read-only after checks. `score.py --synthetic` cannot load `a_won`.

## 1. Definitions

* **x̂_P(m):** the modeller's posterior mean of P's first-serve-speed change before match m, in km/h. It uses P's own history in order, with prior mean 0.
* **r_P(m):** 1 if P has a timed match with `obs` at most 14 days before m, else 0.
* **`spd_chg`(m)** = clip((x̂_A − x̂_B)/s, −4, 4) for men with r_A + r_B ≥ 1, otherwise NaN.
  * s is the SD over men's model-frame matches 2014–2023 with r_A·r_B = 1, frozen.
* **`spd_raw`(m)** = clip(x_raw/5.998, ±4) for men with r_A·r_B = 1, otherwise NaN. This is the registered statistic, on the new panel.
* **η_arm,Y:** the logit of the seed mean of the symmetrised P(A wins), from fits trained on 2013..Y−1.
* **The decided calibration:** q = expit(s_tour,Y·η), with one slope per tour and no intercept. It is fitted on the arm's own out-of-sample seasons 2019..Y−1, using seeds 0–3.
* **P1:** logit P(A wins) = Σ_season a_s·η_B + c·η_B³ + b·z, men 2024–26, where z is `spd_chg` with NaN set to 0 and η_B is the 16-seed raw base.
  * This is `tabpfn_tests.encompassing`: union-clustered variance (four-week blocks and shared players), t on G − 1 degrees of freedom.
  * **Positive b = the man whose speed rose more wins more often than the base says.**
* **P2:** G = 1000·mean[LL(q_B) − LL(q_A1)] over men's model-frame matches 2024–26, debut seasons out. **Positive = A1 is better.**
  * Its interval is the four-week-block t interval with the seed variance added (the surface-IOS convention).
* **Capture:** the slope, without intercept, of η_A1 − η_B on 0.090·z. It is the share of the published effect that TabPFN applies.
* **Nudge F** (secondary): logit q_F = s·η_B + b̃_Y·z.
  * b̃_Y = b̂_Y·τ²/(τ² + SE_Y²), with b̂_Y the walk-forward maximum-likelihood estimate on 2019..Y−1 and τ = 0.05.

## 2. Data needed from the build

The build must supply one row per model-frame match (63,737 matches, 2013–26) with `spd_chg`, `spd_raw`, r_A and r_B, joined by `match_id` one-to-one.

* **Observed: orientation agrees.**
  * The model frame's side A is Stage 0's `player_a`: `p_mkt` equals Stage 1's `p_avg_a` on 50,003 of 50,003 matches ≤ 2023.
  * `player_a` is unchanged by the 7 October rebuild on all 50,116 speed ids ≤ 2024.
* **Observed: the old feature file does not cover the model frame.** `speed_features.parquet` covers only 91% of model-frame ids ≤ 2024, because it was built on the meta-stack frame.
  * The R3 panel must therefore be built on the model frame's own ids.
  * The model frame has no men's matches in 2018.

## 3. Missing data

* **Observed (counts, men 2024, held data):**
  * both sides timed within 14 days: 1,429 of 2,676 (53%);
  * at least one side timed: 2,206 (82%).
* *Inferred:* a one-sided match carries half the information of a two-sided one. So the prior-mean rule adds about **27% effective information**.
  * In simulation it lifts P1's power from 0.26 to 0.30 (β 0.05) and from 0.63 to 0.73 (β 0.09).
  * One diff column with this rule captures what per-side pair columns would offer: a usable value when only one side is known.
* **Observed (TabPFN-3.5 source, `tabpfn_v3_5.py`):** each NaN cell gets an indicator, then the training mean, then scaling.
  * So NaN natively means "mean plus indicator", and a hand-made presence column is redundant.
  * NaN is kept for "no information at all". The prior mean, 0, is used for a missing side next to a known one.
* **No precision input in A1** (*inferred*). The posterior mean already shrinks for reliability, and a weak effect cannot teach TabPFN an interaction.

## 4. How it enters TabPFN, and whether it will be used

* **Redundancy (observed, seasons ≤ 2023, a logged look).**
  * x_raw's R² on the 58 inputs is 0.107 in sample but **0.040 out of season**; gradient boosting gives −0.03.
  * Its correlation with `odds_logit` is **+0.044**.
  * So about 96% of it is new to the model, and the close does not hold it. This is consistent with β given the close ≈ β given the model.
  * The largest correlations are `form_first_in` −0.136 (*inferred*: the trade-off between speed and accuracy) and `form_first_won` +0.088.
* **No level input (observed).** The 364-day speed level has R² **0.69** on the 58 inputs out of season, and correlates 0.81 with `iosO_ace`. It is a trait the IOS serve profile already carries.
* **One diff column (inferred).** The hypothesised effect is antisymmetric and near-linear, and its training evidence for the 2024 fit is only about z = 2 (Σ p(1−p)z² ≈ 750 on ≤ 2023, SE 0.036). Pair columns double what TabPFN must learn.
  * Every estimator sees every column: `max_features_per_estimator` is 500, and the model has 59 inputs.
* **Use (inferred).**
  * B-INJ (z 3.9 on 2014–24, with a value on every match) was used at **capture 0.39** (`binj_g5.json`).
  * Its column arm tied in 2025–26 (men −0.02 [−0.34, +0.30]).
  * The speed column is sparser and weaker in training, so expect a capture of **0.2–0.5**.
* **An extra noise column costs nothing systematic (observed).** The surface-IOS placebo column moved men's forecasts by 0.013 log-odds RMS. That is about what reseeding does: two disjoint 4-seed means differ by 0.014.
* **Women are NaN.** Both published windows tie, and their values exist only at Slams (about 12% of matches).
* **Clipping and a frozen SD** matter little to TabPFN but protect P1 and the nudge.

## 5. Arms, seeds and GPU

| Arm | Inputs | Seeds 2019–23 / 2024–26 | Compared with |
|---|---|---|---|
| A1 `spd` | 58 + `spd_chg` | 0–3 / 0–15 | `model` 0–15 (reused) |
| A2 `spd_raw` | 58 + `spd_raw` | 0–3 / 0–7 | `model` 0–7 |
| A3 | A1 + the auditor's second statistic (e.g., second-serve or fault-speed change, within-match fade, precision pair); if none passes its gates, `spd_perm` (A1's column permuted within season × presence, a placebo) | 0–3 / 0–7 | `model` 0–7 |
| A1_noodds | 57 + `spd_chg` | 0–3 / 0–7 | `model_noodds` 0–7 (seeds 3–7 new in 2024–26, seed 3 new in 2019–23) |

* **Seeds (observed).**
  * One seed's log-odds scatter by an SD of 0.019 around the seed mean.
  * 4-seed and 16-seed means calibrate alike (slope 0.9992).
  * Using the same seed numbers barely pairs two arms: the noise correlation is 0.07–0.20 once a column is added. What matters is equal seed counts.
  * 32 seeds would add 2–6 points of power for 1.1 h. Not worth it.
* **GPU (observed, from the runner logs).**
  * A fit takes 15 s (2019) to 47 s (2026), not 1–1.5 min.
  * One seed's sweep of 2019–26 takes about 237 s.
  * The plan is **220 fits, 2.05 h**, or 3.1 h with a 1.5× margin.
  * P1, the nudge and the capture need no GPU.

## 6. The test (to be frozen)

**Population:** men's model-frame matches 2024–26, debut seasons out: 2,674 + 2,620 + 1,774 = **7,068** matches, in 33 four-week blocks.

**Primary family: a fixed sequence, each step two-sided at 95%.**
* **P1 passes** if b's interval lies above 0. If it lies below 0, that is a reversal.
* **P2 is confirmatory only after P1 passes.**
  * Interval above 0: "A1 **improves** the score by G [lo, hi]".
  * Interval below 0: A1 is worse.
  * Otherwise: a tie.
  * P2 is always reported.
* In simulation, P2 passes without P1 in at most 1.3% of runs, so the sequence costs P2 almost nothing.

| P1 | P2 | Reading |
|---|---|---|
| above 0 | above 0 | The information is confirmed, and A1 improves the score by G |
| above 0 | tie | The information is present, but the column does not deliver it. Suspects: capture, seeds, representation. Next step: a prospective test of the nudge |
| tie | any | No detectable speed information beyond the model in 2024–26; b's interval bounds it |

**Secondaries (descriptive, each with its direction):**
* **S1:** each season.
* **S2:** 2025–26, the blind seasons (2024 was part of the replication).
* **S3:** matches with and without a value. Without a value the gain should be about 0 (a harm check).
* **S4:** women (harm) and both tours.
* **S5:** the no-odds twin.
* **S6:** Polymarket's price 24 hours before the start (1,442 men; about 2,690 both tours).
  * A1 against the base, both fed that price and calibrated as at the close.
  * The 24 h → 30 min price move, regressed on η_A1 − η_B.
* **S7:** raw forecasts.
* **S8:** A2 and A3 against the base and against A1.
* **S9:** the nudge F, shrunk and unshrunk.
* **S10:** the capture.
* **S11:** P2 with block-only and calendar-week intervals.

**Multiplicity.** Only P1 → P2 is confirmatory. Report how many descriptive intervals exclude 0, against chance's roughly 5%.

## 7. Expected effect and power

*Inferred planning β:* pooling the published discovery (−0.018 ± 0.098) and replication (+0.090 ± 0.037) gives 0.077 ± 0.035. A sceptical N(0, 0.05²) prior for selection (one statistic of about ten passed) shrinks this to about 0.05.

**Observed (synthetic Monte Carlo, 2,000 replicates).** The real inputs are the 2024–26 counts, the blocks and the spread of the base forecast; the assumptions are in §10.

| Men, 2024–26 | β 0.05 | β 0.077 | β 0.09 |
|---|---|---|---|
| Oracle gain (β known, all matches) | +0.15 | +0.36 | +0.49 |
| A1's expected gain, capture 0.25–0.5 | +0.07 to +0.12 | +0.16 to +0.27 | +0.22 to +0.38 |
| **P2 power** (seed variance added) | 11–15% | 33–37% | 45–51% |
| P2 power, structural column noise 0.02 | 8% | 23% | 35% |
| **P1 power** | 29–31% | 58–60% | 72–74% |
| Nudge F power, shrunk / unshrunk | 10% / 7% | 24% / 16% | 34% / 22% |
| 2025–26 only: P2 / P1 | 9% / 20% | 24% / 41% | 30% / 50% |
| Registered column (A2): P2 / P1 | 12% / 26% | 30% / 51% | 38% / 63% |

* **With no effect (β = 0):**
  * P1 rejects in the positive direction in 1.5–3% of runs (nominal 2.5%).
  * P2 rejects in 0.1–1%: the seed-variance term is conservative.
  * Published seed-against-seed block intervals exclude 0 in 8.3% of 576 rows. Block-only intervals are therefore slightly liberal, which is why S11 reports both.
* **80% detectable effects:** P1 at β ≈ 0.10; P2 at β ≈ 0.13, a gain of about 0.5–0.8 mLL.
* *Inferred:* P2's power falls as capture rises, because the noise grows with the applied term. The unshrunk walk-forward nudge is the noisiest option.

## 8. Result-free gates (strategist)

* **G-S1, redundancy:** out-of-season R² on the 58 inputs ≤ 0.10, men ≤ 2023. x_raw passes (0.040); the level fails (0.69).
* **G-S2, price:** the correlation with `odds_logit`, reported on ≤ 2023.
* **G-S3, harness:** the flip is an involution with NaN; the 58 base columns match `model_frame.parquet`'s hash; the join is one-to-one; coverage is counted per season.
* **G-S4, leaks:** the build's leak probes pass before any fit. The runner refuses a feature file without a probe record.
* **G-S5, synthetic recovery:** the verifier recovers a planted β, and the null is rejected at the nominal rate.

Nothing is tuned on results; the SD is frozen on ≤ 2023.

## 9. Leak argument

* **Training:** each season Y's fit trains on 2013..Y−1 only.
* **The column:** it uses own history in order, with field constants frozen on ≤ 2023 or taken from the leak-proof clock (the build's own probes).
* **Calibration and nudge:** they use seasons before Y only; the code asserts it.
* **The 24-hour price:** it only replaces `odds_logit` at prediction time.
* **Reused base fits:**
  * they are checked by columns, training shape and query ids;
  * their stored fingerprints are rechecked for seasons ≤ 2024;
  * the fits are deterministic: feature interactions' and the race's 2019 seed 0–2 forecasts are identical.
* **Synthetic mode:** `--synthetic` never selects `a_won`, and a test asserts it.

## 10. Risks

1. **Low power:** a tie is likely even if the effect is real. P1 and the capture make the tie diagnosable.
2. **The power assumptions:** the 2025–26 one-sided share (the build will count it), a normal x and a calibrated base.
3. **Measurement artefacts** (event families, key statistic against point mean, AO 2024) can be learned by TabPFN. S3 and the build's harmonisation guard against this.
4. **Not blind:** 2024 was in the replication, and 2025 was opened through `x_shot`. Both are labelled.
5. **Equal seed counts** in every comparison.
6. **The model frame** is the 30 September snapshot. Men's ids agree with the rebuilt Stage 0.

## 11. Code plan (R3) and pre-registration skeleton

All code goes in `src/eda/serve_speed_tabpfn/`:
* **`common.py`:** paths, the seed plan and the configuration. Output goes to `data/studies/serve_speed_tabpfn/local/`; the base folders are read-only.
* **`arms.py`:** feature interactions' version, with this study's `features/registry.json` and an `assert_base_unchanged` check.
* **`local_fits.py`:** feature interactions' runner, plus:
  * `--plan` (CPU): lists the jobs and estimates their time;
  * it refuses to fit `model` with the odds;
  * it adds `model_noodds` seeds only where the race has none;
  * it stores the feature file's SHA-256 in each fit's metadata.
* **`forecasts.py`:**
  * loads base arms from this study's folder, then feature interactions', then the race's;
  * checks columns, shapes and ids;
  * symmetrises and averages over seeds.
* **`score.py`:**
  * `--check`: result-free;
  * `--run`: once; writes P1, P2 and S1–S11 to `results.json` and `results.csv` with directions;
  * `--synthetic --beta B --capture c --reps R`:
    * outcomes for 2019–26 are drawn from the calibrated base + B·z;
    * the arms are synthetic, or the real fits once they exist;
    * it reports the null rejection rates and how well β and the gain are recovered.
* **Tests (`test/serve_speed_tabpfn/`):** flip with NaN; one-to-one join; base columns unchanged; calibration and nudge on seasons before Y only; signs; no `a_won` in synthetic mode; the job list equals the pre-registration's.

**`preregistration.md` skeleton:**
1. The question and the estimands.
2. What existed at the hash: the look-ledger rows, the build, the probes and the coverage counts.
3. The frozen inputs, by SHA-256: the model frame, the feature file and its builder, the registry, the early-price frame and the scorer.
4. Arms and seeds.
5. Forecasts and calibration.
6. Population and subsets.
7. P1 → P2, with the reading table.
8. S1–S11.
9. Multiplicity.
10. Power and detectable effects.
11. The run order: the fits, then `--check`, then `--run` once.
12. Deviations, recorded in `results.json`.

## 12. Claims checked on disk

Scripts are in `src/eda/serve_speed_tabpfn/design/`; outputs are in `data/studies/serve_speed_tabpfn/design/`.

| Claim | Number | Script → output |
|---|---|---|
| Side A is Stage 0's `player_a`; unchanged by the rebuild | 100% of 50,003 and of 50,116 | `strategist_redundancy.py` → `.json` |
| x_raw against the 58 inputs, men ≤ 2023 (3,148) | R² 0.107 in sample / 0.040 out of season / gradient boosting −0.028; corr with odds +0.044 | same |
| Women ≤ 2023, mostly Slams (1,470) | R² 0.138 in sample / 0.028 out of season; corr with odds −0.009 | same |
| The level against the 58 inputs (16,642) | R² 0.69; corr 0.81 with `iosO_ace`; corr 0.004 with x_raw | same |
| The rebuilt x_raw equals the published one | max difference 0.0 km/h | same |
| Coverage, men 2024: both sides / at least one | 1,429 / 2,206 of 2,676 | same |
| Timed first serves in the 14 days | median 102, 10th percentile 40 | same |
| Seed noise; 4-seed against 16-seed means | 0.019; slope 0.9992 | `strategist_noise.py` → `.json` |
| Placebo column; same-seed noise correlation; B-INJ's excess | 0.013; 0.07–0.20; 0.030 | same |
| Mean p(1−p), men's base | 0.194 | same |
| Fit times; one seed's sweep; the plan | 15–47 s; 237 s; 2.05 h | `strategist_gpu.py` → `.json` |
| Power | §7 | `strategist_power.py`, `_nudge.py`, `_joint.py` → `.csv` |
| Determinism; seed-against-seed intervals | identical (3 pairs); 8.3% exclude 0 | `strategist_checks.py` → `.json` |
| B-INJ's capture; its column arm, men 2025–26 | 0.39; −0.02 [−0.34, +0.30] | same (published files) |
| TabPFN's NaN handling; no feature subsampling | indicator + mean; cap 500 | `tabpfn` source: `tabpfn_v3_5.py`, `preprocessing/configs.py` |

## 13. Looks

| # | Seasons | What was related to what | Why |
|---|---|---|---|
| 1 | Men 2014–2023; women ≤ 2023 (mostly Slams) | Registered x_raw against the 58 inputs, **closing odds included** (R², correlations); no result, no statistic target | Redundancy and a price look |
| 2 | Men 2014–2023 | The 364-day speed level against the 58 inputs, odds included; no result | The case for a level input |
| 3 | 2015–2024 | Coverage counts | Coverage |
| 4 | 2019–2023 | Saved forecasts only: the base's 16 seeds, `binj`, `levels`, `snet1(_perm)`, `sprof`; no result, no speed | Fit noise |
| 5 | 2024–2026 | Match counts and four-week blocks; outcomes **synthetic** | Power |
| 6 | Published | Surface-IOS `results.csv`, `binj_g5.json`, `final_results.json`, `composed_results.csv`; re-read only | Noise references |

No speed feature was related to any match result in any season.
