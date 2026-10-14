# Role D: the evaluator's verification of the level-evidence system

10 October 2026 · Role D (evaluator) of the level-evidence system run · Written progressively; this is the state at
checkpoint 3: the holdout readings and the recommendation, with the dev readings, checks and fits behind them. Research
evidence, not a decision: choosing a model is the owner's call.

## In short

* **The holdout primary is unresolved** (Observed). SYS against REF, men, 2025–2026, both stages: **+0.011 [−0.425,
  +0.447] mLL, P(better) 0.52** (4,810 matches).
  * Pooled 2020–2026: −0.003 [−0.164, +0.159], P 0.49.
  * Leaving out the 909 matches without a speed memory: +0.043, P 0.57.
* **The recommendation** (Observed, `results/holdout/decision.json`).
  * The owner's decision layer (addition 4): **SYS for men.** The primary shows no harm, and none of addition 2's eight
    readings is worse, raw or after Holm.
  * The registered rules: unresolved (P 0.52), no recommendation.
  * No edge credit either way.
* **Flag: the placebo reads better on the holdout.** SYS_PLACEBO against REF, both tours: +0.215 [+0.031, +0.398]; men
  +0.350 (P 0.97). On dev it leaned worse.
  * *Inferred:* a mechanism-free change of SYS's size moves holdout log loss by ±0.2–0.35 mLL. Every holdout reading
    sits inside that noise.
* **Flag: the holdout is wider than expected.** SE about 0.22 (addition 6 expected 0.12), so "no harm" only rules out a
  harm of about 0.45 mLL or more.
  * *Inferred:* the case for SYS rests on B's statistic-level evidence, with the model-level readings as a weak harm
    check.
* **Dropping lower-level box evidence is the one resolved harm** (Observed): SYS_w0 against REF, men, −0.586 on dev,
  −0.502 [−0.872, −0.131] pooled 2020–2026 (both worse).
  * The dose curve rises with w on dev and on the holdout.
  * The fitted w (SYS) and w = 1 read the same.
* **The ITF natural experiment is unresolved** (Observed): REF_noITF against REF, holdout. Men −0.073 (P 0.24: the ITF
  box scores as-is lean better). Women +0.166 (P 0.78: leaving them out leans better).
* **Checkpoint 2 (dev):** SYS was selected; the registered rules would have chosen the share arm SYS_S2.
  * compare.py equals the scorer on 54 rows; the harness is exact; 55 tests pass.
  * The unlock and the freeze were verified, and the holdout was opened once.
* **The rule test** (addition 4; NEW_SYS_BOTH against SYS_BOTH, men): C0_now's additions are **recommended for entry
  by the system's route**, for 2018–2024 (dev) and 2025–2026 (holdout).
  * Dev reads −0.029 [−0.055, −0.003], worse but inside the 0.10 harm tolerance.
  * The holdout reads +0.031 [−0.035, +0.097], unresolved.
  * Women wait for P7. Every late arm's reading of record is in "The late arms".

## The holdout readings (checkpoint 3)

*Observed* (the main holdout run, once, 08:37–08:38 UTC, 10 Oct: `results/holdout/readings.json`, `pairs.csv`,
`pairs_drop909.csv`, `dose_curve*.csv`; the decision: `results/holdout/decision.json`).
* **Before the run:**
  * the unlock (`56864fed…`) held all nine pre-registration files, including addition 6, and `selection.json`
    (`b5fbec82…`);
  * the freeze passed; `readings.json` did not exist (the holdout opens once);
  * SELECTED = SYS, from the decision layer's `selection.json`.
* **Scored:** REF and the 11 arms complete at that moment: SYS, SYS_w0, SYS_w50, SYS_w100, SEP_ALL, SYS_NOCLASS, SYS_S2,
  R_S2, SYS_PLACEBO, REF_noITF and RES_ONLY.
  * SYS_BOTH (not built) was waived on the lead's word. The ITFASIS and C0_now arms were absent. They come through the
    supplementary mode, and each arm's first holdout reading is the one of record (addition 6).
* **The 2026 speed rule:** 909 matches without a speed memory (416 men's) get no stage-2 nudge. The sensitivity leaves
  them out.

**The primary and the recommendation** (men, 2025–2026, both stages; 4,810 matches; + = SYS better):

| Reading | mLL [95%] | Label |
|---|---|---|
| **SYS vs REF, holdout (the primary)** | **+0.011 [−0.425, +0.447]** | unresolved, P(better) 0.52 |
| Sensitivity, the 909 matches left out (4,394) | +0.043 [−0.435, +0.522] | unresolved, P 0.57 |
| Pooled 2020–2026 (16,482) | −0.003 [−0.164, +0.159] | unresolved, P 0.49 |
| Pooled, the 909 left out | +0.006 [−0.160, +0.171] | unresolved, P 0.53 |
| Stage 1 alone, holdout | −0.015 [−0.453, +0.423] | unresolved |
| Women; both tours (SYS is men-only) | −0.013 [−0.193, +0.168]; −0.001 [−0.251, +0.250] | unresolved, P 0.44; 0.50 |

* **Under the decision layer** (addition 4; `decision.json`): **recommend SYS for men.** The primary shows no harm, and
  none of the eight readings is worse after Holm. The same holds under the sensitivity.
  * There is no edge credit: the edge that sizes stakes comes only from untouched matches at the venue's price.
* **Under the registered rules** (for the record): **unresolved, P(better) 0.52.** P is under 0.80 and the pooled
  primary is not better, so they report P(better) and recommend nothing. The sensitivity gives the same, P 0.57. The
  t-CDF check agrees.

**Addition 2's eight readings** (men, SYS vs REF, holdout): none is worse, raw or after Holm.

| Reading | Matches | mLL [95%] | Two-sided p | After Holm |
|---|---:|---|---|---|
| Season 2025 | 2,620 | +0.111 [−0.474, +0.696] | 0.68 | 1.00 |
| Season 2026 | 2,190 | −0.109 [−0.896, +0.678] | 0.76 | 1.00 |
| Less-exposed side under 10 main-tour results | 1,049 | −0.165 [−1.292, +0.962] | 0.76 | 1.00 |
| 10 or more | 3,761 | +0.060 [−0.333, +0.453] | 0.75 | 1.00 |
| Share gap ≥ 0.5 | 1,529 | −0.277 [−1.311, +0.757] | 0.58 | 1.00 |
| Share gap < 0.5 | 3,278 | +0.141 [−0.332, +0.614] | 0.54 | 1.00 |
| Falsification | 877 | −0.222 [−1.072, +0.629] | 0.59 | 1.00 |
| Stage 1 alone | 4,810 | −0.015 [−0.453, +0.423] | 0.94 | 1.00 |

**The decomposition and the ITF natural experiment** (holdout; + = the first-named better):

| Comparison | Men | Women | Both tours |
|---|---|---|---|
| SYS vs REF_noITF (all the system changes but the ITF box-score exclusion, Elo weights included) | +0.083 [−0.227, +0.394], P 0.71 | −0.179 [−0.661, +0.303], P 0.22 | −0.046 [−0.362, +0.271], P 0.38 |
| REF_noITF vs REF (the ITF box scores left out against as-is) | −0.073 [−0.282, +0.136], P 0.24 | +0.166 [−0.272, +0.604], P 0.78 | +0.045 [−0.181, +0.270], P 0.66 |

* *Inferred:* for men, taking the ITF box scores out leans worse (P 0.24 that leaving them out is better). For women it
  leans better (P 0.78). Both are unresolved.
  * SYS is men-only, so its women's readings move only through training on the changed men's rows.

**Every arm against REF, holdout, men** (all unresolved):
* the dose curve:
  * SYS_w0 −0.296 [−0.911, +0.319] (P 0.16);
  * SYS_w50 −0.147 (P 0.25);
  * SYS +0.011 (P 0.52);
  * SYS_w100 +0.013 (P 0.53);
* SEP_ALL −0.315 (P 0.25);
* SYS_NOCLASS +0.032 (P 0.55);
* RES_ONLY +0.055 [−0.076, +0.187] (P 0.81);
* R_S2 +0.021; SYS_S2 +0.099;
* **SYS_PLACEBO +0.350 [−0.034, +0.733] (P 0.97);**
* REF_noITF −0.073.

**Arm against arm, holdout, men:**
* SYS vs SYS_NOCLASS −0.021 (P 0.35);
* SYS vs SYS_w100 −0.003; SYS vs SYS_w50 +0.158 (P 0.90); SYS vs SYS_w0 +0.307 (P 0.86); SYS vs SEP_ALL +0.326
  (P 0.78);
* SYS vs RES_ONLY −0.045 (P 0.40): the box-score layer beyond the Elo weighting;
* SYS vs R_S2 −0.010 (P 0.49); SYS_S2 vs SYS +0.088 (P 0.66);
* SYS vs SYS_PLACEBO −0.339 [−0.958, +0.280] (P 0.13).

All unresolved.

**Pooled 2020–2026, men:**
* SYS −0.003 (P 0.49); SYS_w100 +0.028 (P 0.66); SYS_w50 −0.132 (P 0.08);
* **SYS_w0 −0.502 [−0.872, −0.131], worse.** Both tours −0.233, worse.

Every model stays better than its calibrated close on the holdout: men, REF +2.673 and SYS +2.683 mLL.

**Flagged:**
1. **The placebo reads better on the holdout.** SYS_PLACEBO against REF, both tours: **+0.215 [+0.031, +0.398],
   better**. Men +0.350 (P 0.97). On dev it leaned worse (men −0.161, P 0.05).
   * A mechanism-free change of SYS's size (SYS's change permuted within tour × season) moves holdout log loss by about
     ±0.2–0.35 mLL, in either direction.
   * *Inferred:* the holdout readings of every arm, SYS included, sit inside that noise. This is the power note's N8, at
     full strength.
2. **The primary's interval is wider than addition 6 expected:** ±0.44 mLL (SE about 0.22), against the expected SE of
   0.12.
   * At this SE, the harm rule flags a holdout reading only below about −0.45 mLL.
   * *Inferred:* "no harm" on the holdout is weaker evidence of safety than addition 6 stated. The recommendation rests
     on the statistic-level evidence and on the pooled 2020–2026 reading (−0.003 ± 0.16), as addition 6 anticipated.
3. **Removing the lower-level box evidence is the only resolved harm,** and it repeats on dev and pooled (SYS_w0).
4. **Not yet read:** SYS_BOTH, SYS_ITFASIS, SYS_BOTH_ITFASIS and the C0_now arms, so the rule test's verdicts are not
   yet scored. They come through the supplementary mode.

## The late arms: supplementary readings of record (addition 5; rulings of addition 7)

*Observed* (`results/supplementary/<dev|holdout>/<ARM>_pairs*.csv`, `rule_test*.json`).
* Each arm's first reading is its reading of record (addition 6, §2).
* None of these arms enters the selection, the Holm family or the men's recommendation.
* The main holdout readings of record (08:37 UTC) were not re-run.
* **Fits** (all 32 per arm, every check passed):
  * SYS_ITFASIS: 10:03–10:21, by the queue. Its inputs to 2024 differ from SYS's in 22 inputs, so it was fitted in full.
  * SYS_BOTH: 14:00–14:17. The queue launched it just before I stopped the queue to follow the lead's order.
  * NEW_ASIS: 14:17–14:34; NEW_ASIS_PRE: 14:35–14:51. Both were released from the frame check under addition 7's
    `debut_season` waiver (10 matches; no unexpected move; all 67,226 matches shared).
  * SYS_BOTH_ITFASIS: 14:51–15:08.

| Arm, pair (+ = the first-named better) | Dev 2020–2024 | Holdout 2025–2026 |
|---|---|---|
| RES_ONLY vs REF, men (the Elo weighting alone) | −0.038 [−0.112, +0.036], P 0.15 | +0.055 [−0.076, +0.187], P 0.81 (main run) |
| RES_ONLY vs REF, women | +0.036 [−0.011, +0.082], P 0.94 | −0.038 [−0.106, +0.030], P 0.13 (main run) |
| SYS vs RES_ONLY, men (the box-score layer beyond it) | +0.030 [−0.102, +0.161], P 0.67 | −0.045 [−0.428, +0.339], P 0.40 (main run) |
| SYS vs SYS_ITFASIS, men (+ = ITF box scores out is better) | −0.000 [−0.001, +0.001] (rounding only) | −0.028 [−0.211, +0.155], P 0.37 |
| SYS_BOTH vs REF, women | −0.048 [−0.248, +0.152], P 0.32 | +0.039 [−0.390, +0.468], P 0.57 |
| SYS_BOTH vs REF, men | +0.012 [−0.178, +0.203], P 0.55 | +0.005 [−0.428, +0.438], P 0.51 |
| SYS_BOTH vs SYS_BOTH_ITFASIS, women | +0.017 [−0.016, +0.050], P 0.85 | −0.021 [−0.475, +0.433], P 0.46 |
| SYS_BOTH vs SYS_BOTH_ITFASIS, men | +0.002 [−0.001, +0.005] | −0.037 [−0.257, +0.183], P 0.36 |
| NEW_ASIS vs REF, men (C0_now as-is) | −0.021 [−0.064, +0.022], P 0.16 | +0.055 [−0.029, +0.139], P 0.91 |
| NEW_ASIS vs REF, women | +0.019 [−0.066, +0.103], P 0.67 | −0.029 [−0.351, +0.293], P 0.43 |
| NEW_ASIS_PRE vs REF, men (additions to 2024-12-29) | identical to NEW_ASIS (same inputs through 2024) | +0.049 [−0.033, +0.130], P 0.89 |
| NEW_ASIS vs NEW_ASIS_PRE, men (the 2025–26 additions) | 0 exactly | +0.006 [−0.031, +0.043], P 0.64 |

* All are unresolved, with one exception. RES_ONLY against REF, men, dev, reads **worse** in the stratum where the
  less-exposed side has fewer than 10 main-tour results: −0.180 [−0.313, −0.046]. Its season 2021 reads −0.249, worse
  too. These are reported, with no decision.
* Pooled 2020–2026, NEW_ASIS against REF, men: +0.001 (P 0.52).
* **NEW_SYS_BOTH** (option c, addition 7) was READY at 15:34 and fitted 15:35–15:51 (968 s; checks pass).
  * Its frame failed only the waived `debut_season`.
  * Its strength file is `NEW_C0_now_elo_optC.parquet`.
  * The option-(a) build was never fitted or scored.

**The rule test's verdicts** (addition 4, section 5; `system_decide.rule_test` on the supplementary readings; of record):

| C0_now's additions | Reading that decides: NEW_SYS_BOTH vs SYS_BOTH, men | Harm? | Verdict, men |
|---|---|---|---|
| 2018–2024 (dev) | **−0.029 [−0.055, −0.003], worse** | no: within the 0.10 tolerance | **recommended for entry by the system's route** |
| 2025–2026 (holdout) | +0.031 [−0.035, +0.097], unresolved, P 0.84 (drop-909 +0.015, P 0.77) | no | **recommended for entry by the system's route** |
| Pooled 2020–2026 (reported) | −0.011 [−0.039, +0.016], P 0.21 | no | — |

* **Women** wait for P7 (dev −0.010; holdout −0.086 [−0.435, +0.263], P 0.31). These readings, and REF_noITF against
  REF, are the evidence for that decision.
* **No RES_ONLY-on-C0_now flag:** the men's recommendation is SYS.
* **Reported, not decisive:** NEW_SYS_BOTH against NEW_ASIS, men, dev +0.005, holdout −0.019; NEW_ASIS and
  NEW_ASIS_PRE in the table above.
* **Flag** (*Inferred*): on dev, the new data through the system's route reads resolved-worse for men by 0.029 mLL. That
  is small and inside the harm tolerance, so the rule recommends entry. The holdout points the other way (+0.031,
  unresolved).
* The interim "not scored" `rule_test.json` files are kept as `rule_test_before_NEW_SYS_BOTH.json`.

## The dev readings and the selection (checkpoint 2)

*Observed* (the first dev run, 08:09–08:25 UTC, 10 Oct: `results/dev/pairs.csv`, `results.json`, `dose_curve.csv`,
`stratum_inputs.csv`, `addition1_pairs.csv`; `results/selection.json`, `selection_registered.json`,
`results/dev/decision.json`).
* **The run.** 2020–2024, both stages, 22,265 matches (men 11,672, women 10,593); results of seasons ≤ 2024 only.
  * Scored: REF and the six selection arms (SYS, SYS_w0, SYS_w50, SYS_w100, SEP_ALL, SYS_NOCLASS); R_S2, SYS_S2 and
    SYS_PLACEBO (report-only); REF_noITF (addition 1's dev pair).
  * Waived on the lead's word, because they were not fitted by then: SYS_BOTH (not built) and RES_ONLY (READY at
    08:10, fitting now). Their dev readings come in a second run, which does not touch `selection.json`.
  * compare.py's own primary rows equal the scorer's on all 54 rows compared (largest difference 0.0).
  * The freeze (additions 3, 4b, 4c) was verified, and no unlock existed.
* **The selection in force: SYS** (`selection.json`, SHA-256
  `b5fbec82b54229c6d424c3c5e7f22bd927de6fb52ade710dac97e062b84e3ee1`; the unlock must hold it).
  * None of the five challengers reads better than SYS. The table below gives SYS against each (men, + = SYS better).
  * SYS shows no harm against REF (men): −0.008 [−0.162, +0.145], unresolved, P(better) 0.46.
* **The registered rules would have selected SYS_S2.** Their qualifiers were SYS_S2 (P(better than SYS) 0.95) and R_S2
  (0.90), the largest gain SYS_S2's (+0.167). SYS_S2 against REF, men: P(better) 0.90.
  * The two qualifiers are the share arms that erratum 1 took out of the selection before any score: a new feature
    found on 2020–2024.
  * The t-CDF check agrees.

**SYS against each challenger** (men, dev, both stages; + = SYS better):

| Challenger | SYS against it, mLL [95%] | Reading | The challenger reads better than SYS? |
|---|---|---|---|
| SYS_w0 | +0.578 [+0.137, +1.019] | **better** (SYS) | no |
| SYS_w50 | +0.118 [−0.022, +0.258] | unresolved, P(SYS better) 0.95 | no |
| SYS_w100 | −0.042 [−0.156, +0.072] | unresolved, P 0.23 | no |
| SEP_ALL | +0.584 [+0.011, +1.156] | **better** (SYS) | no |
| SYS_NOCLASS | +0.015 [−0.066, +0.096] | unresolved, P 0.64 | no |
| *R_S2 (pool lead)* | −0.161 [−0.407, +0.086] | unresolved, P 0.10 | not a challenger |
| *SYS_S2 (pool lead)* | −0.167 [−0.369, +0.035] | unresolved, P 0.05 | not a challenger |

**Every arm against REF** (dev, both stages; + = the arm better; P = P(better)):

| Arm | Men | Women | Both tours |
|---|---|---|---|
| SYS | −0.008 [−0.162, +0.145], P 0.46 | −0.037 [−0.169, +0.096], P 0.29 | −0.022 [−0.133, +0.089], P 0.35 |
| SYS_w0 | **−0.586 [−1.055, −0.118], worse** | +0.060 [−0.222, +0.342], P 0.67 | −0.279 [−0.572, +0.014], P 0.03 |
| SYS_w50 | −0.126 [−0.315, +0.062], P 0.09 | −0.030 [−0.185, +0.125], P 0.35 | −0.081 [−0.208, +0.046], P 0.10 |
| SYS_w100 | +0.034 [−0.085, +0.152], P 0.72 | −0.044 [−0.159, +0.071], P 0.22 | −0.003 [−0.087, +0.080], P 0.47 |
| SEP_ALL | −0.592 [−1.187, +0.002], P 0.02 | +0.090 [−0.231, +0.410], P 0.71 | −0.268 [−0.638, +0.102], P 0.07 |
| SYS_NOCLASS | −0.023 [−0.180, +0.134], P 0.39 | −0.045 [−0.180, +0.091], P 0.26 | −0.033 [−0.139, +0.073], P 0.27 |
| SYS_PLACEBO | −0.161 [−0.354, +0.031], P 0.05 | +0.030 [−0.068, +0.128], P 0.73 | −0.070 [−0.174, +0.033], P 0.09 |
| R_S2 (pool lead) | +0.152 [−0.052, +0.357], P 0.93 | −0.111 [−0.321, +0.098], P 0.14 | +0.027 [−0.128, +0.182], P 0.64 |
| SYS_S2 (pool lead) | +0.159 [−0.089, +0.406], P 0.90 | −0.040 [−0.291, +0.211], P 0.38 | +0.064 [−0.122, +0.251], P 0.76 |
| REF_noITF (addition 1) | −0.002 [−0.007, +0.002], P 0.12 | +0.007 [−0.014, +0.028], P 0.75 | +0.002 [−0.008, +0.012], P 0.66 |

Every model stays better than its calibrated close on both tours: REF +1.374, SYS +1.353, SYS_S2 +1.439, SYS_w0 +1.096
mLL (all "better"). R_S2's dev readings equal the first run's: they are the same fits.

**The dose curve, men** (each arm against REF): w = 0 −0.586 (worse); w = 0.5 −0.126 (P 0.09); SYS, with B's fitted w
(capped at 1), −0.008 (P 0.46); w = 1 +0.034 (P 0.72).
* *Inferred:* the curve rises with the weight on lower-level box scores. Discarding them (w = 0, and SEP_ALL) is the one
  clear harm on dev. Between w = 0.5 and 1 the readings cannot be told apart at this resolution (SYS against SYS_w100:
  P(SYS better) 0.23), as the power note expected.

**SYS against REF in the pre-registered strata** (men; inputs moved = the mean over the 44 moved inputs of the median
|change|, in the reference's SD):

| Stratum | Matches | Inputs moved | SYS vs REF, mLL [95%] |
|---|---:|---:|---|
| Less-exposed side under 10 main-tour results | 2,885 | 0.150 | −0.161 [−0.535, +0.212], P 0.19 |
| 10 or more | 8,787 | 0.073 | +0.042 [−0.119, +0.203], P 0.70 |
| Share gap ≥ 0.5 | 3,600 | 0.138 | +0.150 [−0.168, +0.467], P 0.83 |
| Share gap < 0.5 | 8,046 | 0.071 | −0.065 [−0.221, +0.091], P 0.20 |
| Falsification (both 20+, both shares < 0.10) | 2,001 | 0.047 | −0.041 [−0.334, +0.252], P 0.39 |

* Each season, men: 2020 +0.004, 2021 −0.192, 2022 +0.007, 2023 −0.053, 2024 +0.185 (P 0.84). All are unresolved.
* SYS against SYS_PLACEBO, men: +0.153 [−0.048, +0.354], unresolved, P 0.94.
  * The placebo itself, against REF, men: −0.161 (P 0.05). It reads worse in the falsification stratum (−0.574
    [−0.974, −0.174]) and in the 10-or-more stratum, where SYS barely moves the inputs.
  * The power note warned that beating the placebo is easy (N8). That holds here.

**Reading it** (*Inferred*):
* **At the model level, on dev, SYS is indistinguishable from the reference for men.** The estimate is −0.008 mLL, and
  the interval half-width is 0.15 mLL, wider than the power note's 0.08. It shows no harm.
  * The decision layer keeps SYS on the strength of B's statistic-level evidence. The comparison can see neither a gain
    nor a harm of the plausible size.
  * The registered rules would have switched to the share arm.
* **Removing lower-level box evidence is a resolved harm** (SYS_w0 −0.59; SEP_ALL −0.59, P 0.02).
  * Equivalent pooling (REF) and the system read the same.
  * The direction is the first run's: lower-level evidence informs the model.
* **The share inputs lean better for men** (R_S2 +0.15, SYS_S2 +0.16, P 0.90–0.93), and worse for women (R_S2 −0.11).
  This is lead evidence for the pool, from the seasons that found the feature (erratum 1). It decides nothing.
* **Not yet read:** RES_ONLY (the Elo weighting alone; SYS's Elo inputs equal RES_ONLY's bit for bit), SYS_BOTH, the
  ITFASIS arms and the C0_now arms (rule test); the holdout.

## Keys

* **Labels.** *Observed* = computed here (file cited) or read in code (`path:line`). *Inferred* = reasoning.
  *Suggestion* = a proposal.
* **Scores** are in mLL (milli-log-loss per match). **+ = the first-named model has the lower log loss (better).**
  * "Better" or "worse" when the 95% interval clears 0; otherwise "unresolved", with P(better).
  * Intervals: four-week blocks plus the seeds' variance, paired by seed (compare.py's `paired`).
* **Paths.** `system/` is `data/studies/lower_level_evidence/system/`; `results/` is `system/results/`.

## What the readings can show (E's power note, written before any score)

*Inferred* (E's checkpoint 1, `E_red_team.md`, "What the readings will and will not be able to show" and S3, N8, from
the first run's intervals and E's simulation `audit/power_cp1.json`). Recorded here, as the lead asked, before any score
of this run exists.
* **Resolution.**
  * Men, dev: about 0.08 mLL. An arm that changes inputs reads against REF with an SE of 0.03–0.04 mLL.
  * Men, holdout: about 0.12 mLL. The primary's SE is about 0.063 mLL on about 4,810 matches.
  * Men, pooled 2020–2026: about 0.067 mLL.
  * If SYS is as good as the first run's FP (+0.083 mLL on dev), the holdout primary reads "better" only about 26% of
    the time, and P(better) ≥ 0.80 about 68% of the time. An unresolved holdout will not rule out a gain of that size.
* **Expected to read unresolved:**
  * SYS against SYS_w100 and SYS_w50: B measured +0.006 per unit of w over w = 1 at the statistic level;
  * SYS against SYS_NOCLASS: B measured −0.000;
  * probably SYS against R_S2, and SYS_S2 against SYS (SE about 0.10).

  The model-level dose curve applies one w to TQ, GSQ, CH and CHQ together. It cannot say what a Challenger match is
  worth; B's statistic-level w answers that.
* **A switch away from SYS on dev is weak evidence.** Suppose no challenger truly differs from SYS. At least one still
  reaches P(better than SYS) ≥ 0.90 by noise with probability 0.52 (independent readings), 0.34 (correlation 0.5) or
  0.19 (correlation 0.9).
  * The selected arm's dev reading is then biased upward: it is the best of eight.
  * Only the holdout primary is free of the selection.
  * R_S2's dev readings were published in the first run, so SYS against R_S2 on dev is not blind.
* **SYS beating SYS_PLACEBO does not by itself show that SYS helps.** In the first run, FP_placebo against the reference,
  men, read −0.114 [−0.233, +0.005]. FP against FP_placebo read +0.197 [+0.059, +0.335], while FP against the
  reference read only +0.083. A random change of that size costs about 0.1 mLL, so beating the placebo is easy.
* **Holm's eight readings can flag only a large harm.** The strata's SEs on the men's holdout are about 0.13–0.20 mLL.

## The scorer: `src/eda/lower_level_evidence/system_pairs.py`

*Observed* (the code).

**What it computes.** compare.py's recipe through compare.py's own functions, unchanged: seed tables with their file
checks, the walk-forward calibration slopes and stage 2's b̃ (2019 .. Y − 1, debut seasons out, τ = 0.05), forecasts,
and the paired log loss. The match facts are the reference's, on the matches every frame of a group holds. Stage 2's
speed column is the reference's in every arm: role A's table leaves `spd_L` untouched by the layer.

**The readings,** each for both tours, men and women:
* every arm against REF, both stages (and stage 1 alone, overall), overall, in each stratum and in each season;
* SYS against each challenger, SYS_PLACEBO and RES_ONLY (and the optional SYS_w25, SYS_w75), overall and by season;
* SYS_S2 against SYS;
* the dose curve (SYS_w0, SYS_w25, SYS_w50, SYS_w75, SYS_w100 and SYS), each against REF and against SYS;
* each model against its calibrated close, for scale;
* **RES_ONLY** (the lead's ruling after E's M3; to be pre-registered in the checkpoint-1 addition; not in the selection):
  * RES_ONLY against REF: the Elo weighting alone;
  * SYS against RES_ONLY: the box-score layer beyond the Elo weighting.
* **The strata** are the first run's definitions, from `sides.parquet` (counts only): the less-exposed side has fewer
  than 10 main-tour results in 365 days (or 10 or more); the 365-day lower-level box-score share gap is 0.5 or more (or
  under 0.5; unknown left out); falsification: both sides have 20+ main-tour results and both shares are under 0.10.
  `sides.parquet`'s hash is written with the dev selection, and the holdout refuses if it changed.

**The selection rule, applied mechanically** (`select`, `results/selection.json`). Men, dev, both stages.
1. A challenger qualifies when P(it is better than SYS) = Φ(gain / se) ≥ 0.90, where gain = −(SYS against it). SYS stays
   selected if none qualifies; of several, the largest point gain over SYS wins (a tie: the first in the challengers'
   order).
2. REF is selected if the step-1 arm's P(better than REF) < 0.50.
3. Women: no selection. RES_ONLY, SYS_PLACEBO, SYS_BOTH, the optional arms and addition 1's arms never enter it.

**P(better) = Φ(estimate / se)** (addition 2 §4). compare.py's t value is kept beside it. Any step of the selection or the
recommendation on which the two would disagree is flagged. In the harness they differ by at most 0.003.

**The holdout readings.**
* **The primary:** SELECTED against REF, men, both stages, 2025–2026.
* **The decomposition,** both tours and each tour:
  * **SELECTED against REF_noITF:** everything the system changes except the ITF box-score exclusion, Elo weights
    included. This is the lead's relabelling after E's M3; it is not "the Challenger and qualifying part".
  * **REF_noITF against REF:** the ITF box scores as the reference has them, against left out.
* **Every secondary;** the pooled 2020–2026 primary and dose curve.
* **The recommendation**, applied mechanically.
  * **"No secondary is worse"** (addition 2 §3, the lead's ruling of 10 Oct) means: none of eight men's holdout readings
    of SELECTED against REF is worse after Holm. The eight are seasons 2025 and 2026, the six strata other than
    "unknown" (both stages), and stage 1 alone overall.
  * **"Worse after Holm"** means the estimate is below 0 and the Holm-adjusted p is under 0.05, where
    p = 2·(1 − Φ(|estimate| / SE)), two-sided normal.
  * The raw labels of the eight are reported too. Every other reading is reported with no condition.
  * A missing primary of a selected arm other than REF refuses; it never becomes "REF (no change)".

**The 2026 speed rule** (addition 2 §1; the lead's ruling of 10 Oct).
* **The gap:** the reference's speed memory is missing for 909 matches of 2026, 416 of them men's.
* **The primary, in every reading:** no stage-2 nudge for a match without a speed memory (b̃ · `spd_L` = 0), the same
  matches in every arm.
* **The sensitivity, written beside it** (`holdout/*_drop909.*`, `readings.json` key `sensitivity_drop909`): the same
  readings with all 909 matches left out, both tours.
* A scored men's match without a speed value outside that gap refuses.

**Loud failures** (the lead's ruling of 10 Oct; E's M5 and S8).
* **Fit provenance at scoring.** Every fit of a scored model must record its own frame's SHA-256, or be a copy that the
  fit queue registered and whose bytes are unchanged. A fit left from before a rebuild is never scored. REF's 32 fits
  and R_S2's 32 pass.
* **A compared arm with a missing or foreign fit refuses.**
  * The pre-registered arms are required: SYS, the seven challengers, SYS_PLACEBO, SYS_BOTH and RES_ONLY, plus
    REF_noITF and SELECTED on the holdout. A missing one refuses.
  * An optional arm (SYS_w25, SYS_w75, NEW_ASIS_PRE) whose fits are incomplete is skipped and recorded.
  * An addition-1 arm whose frame exists but whose fits are incomplete refuses; one never built is recorded as absent.
  * `--allow-missing ARM` waives an arm, on the lead's word only; the waiver is written into the outputs.
* **Dev prints nothing** until every required arm and the reference pass these checks. All arms, the candidate-Stage-0
  group included, are gathered before anything is read.

**Opened once.**
* The holdout refuses unless `holdout_unlock.json` holds, as 64-hex strings under any keys:
  * the SHA-256 of every pre-registration file on disk: `cc65bcd5…`, addition 1 `c718e6d0…`, addition 2 `3f536796…`,
    and the checkpoint-1 addition;
  * the SHA-256 of the written `results/selection.json`, printed by dev.
* It refuses if `results/holdout/readings.json` exists, which is written last.
* Dev refuses once the unlock exists.

**The checkpoint-1 freeze** (E's M4). Dev and holdout refuse unless a verified dated addition holds the SHA-256, as on
disk now, of seven files:
* `system/classes/classes.csv` and `system/relationship/params.parquet`;
* `relationship.py`, `level_layer.py`, `level_layer_ios.py`, `system_pairs.py` and `system_fits.py`.

The hashes of `params_noclass.parquet`, `system_arms.py`, `system_sandbox.py` and `compare.py` are recommended: reported
when absent, not required. `--without-addition` overrides the freeze, on the lead's word only.

**Addition 1** (the rule of 8 October; none of it enters the selection, the Holm family or the recommendation):
* **The pairs** (`results/<mode>/addition1_pairs.csv`, `addition1.json`), both tours and each tour:
  * REF_noITF against REF;
  * SYS against SYS_ITFASIS and SYS_BOTH against SYS_BOTH_ITFASIS. On the holdout always; on dev too where the arm's
    inputs differ before 2025 (addition 2 §2), that is, where the queue did not copy its dev fits;
  * NEW_ASIS against REF, NEW_SYS_BOTH against SYS_BOTH and against NEW_ASIS, and the optional NEW_ASIS_PRE against REF
    and NEW_ASIS against NEW_ASIS_PRE, on dev, the holdout and pooled 2020–2026.
* **The candidate-Stage-0 arms** are loaded apart, with SYS_BOTH and REF, on the matches all their frames hold. Their
  extra matches are counted, never scored.
* **The guiding reading** per data set, period and tour: protective, holding the model back, mixed or unresolved. The data
  sets are the 2025–26 ITF box scores, C0_now's additions, and C0_pre's when built.

**Tests** (`test/lower_level_evidence/test_system_pairs.py`, 33, all pass):
* the lock, refused before any read: no unlock; a wrong or missing hash; an unreadable file; an edited
  pre-registration; a hash file pointing elsewhere; an unlock lacking addition 1's hash;
* the holdout's preconditions: a final selection, its hash held by the unlock, opened once, the checkpoint-1 addition;
* the real pre-registration's three hashes; the additions' hashes;
* the checkpoint-1 freeze: recognised by its seven hashes, refused once a file moves on, not opened by additions 1 or 2;
  dev refused after the unlock;
* the filtered results read;
* missing, foreign, registered and altered copies of fits; the loud `gather`, the optional skip and the waiver;
* the 2026 speed rule (zero, and the drop over both tours);
* P(better) = Φ; the two-sided normal p (E's example: z = −2.75 gives 0.0060); Holm's adjustment; Holm's family (raw
  worse but not worse after Holm; a better reading never "worse"; an incomplete family);
* the recommendation's branches and its refusal of a missing primary;
* the selection rule; RES_ONLY and addition 1's arms kept out of it;
* addition 1's reading; the lead's queue order; the strata; the placebo's permutation; the 58 inputs' families.

## The decision layer (addition 4): `src/eda/lower_level_evidence/system_decide.py`

*Observed* (the code; sources: `docs/decisions/2026-10-09-adoption-by-change-class.md`, `system/owner_decision_2026-10-09.md`
sections 1–5, `system/preregistration_addition_4.md`). The owner replaced the decision layer before any score of this
run existed. Every measurement is unchanged; only the rules that turn readings into decisions changed.
* **Harm:** worse by more than 0.10 mLL (estimate < −0.10) with the whole 95% interval below 0 (hi < 0). An estimate of
  exactly −0.10, or an interval touching 0, is not harm.
  * An input flag shows harm only when F's expected unevenness, read against the dose, does not explain it. That is a
    reading of the input checks, written in this report. The module lists the flags and never decides them (the
    owner's file, §7).
* **Selection** (men, dev, both stages):
  * SYS, unless a challenger reads "better" than SYS (its interval against SYS clears 0). Of several, the largest gain
    wins.
  * The challengers are five: SYS_w0, SYS_w50, SYS_w100, SEP_ALL and SYS_NOCLASS (erratum 1 to the owner's file,
    `owner_decision_2026-10-09_erratum_1.md`, `edb9b377…`).
  * R_S2 and SYS_S2 add the two share inputs, a new feature found on 2020–2024. They are fitted, scored and reported
    against REF and SYS as registered, labelled "lead evidence for the pool, seasons 2020–2024 (2025–2026 on the
    holdout)", and never selected.
  * The winner's gain is also reported after the winner's luck: gain − 1.35 × SE. The figure is the owner's file's, and
    the five challengers are recorded beside it.
  * REF only if the selected arm shows harm against REF.
  * The registered rules' selection keeps its own seven challengers, for the record.
* **Recommendation** (men): SELECTED unless the holdout primary shows harm or any of addition 2's eight readings is worse
  after Holm. Then REF, with the drivers named, and no edge credit. It is applied to the primary speed rule and,
  beside it, to the 909-match drop.
* **Rule test:** C0_now's additions are recommended for entry by the system's route (NEW_SYS_BOTH), unless NEW_SYS_BOTH
  against SYS_BOTH shows harm for men.
  * Dev decides the 2018–24 additions; the holdout decides the 2025–26 additions.
  * Women wait for P7; their readings and REF_noITF against REF are reported as harm evidence.
  * NEW_ASIS and NEW_ASIS_PRE are reported, never decisive.
  * If REF is recommended for men, the flag "register RES_ONLY on C0_now next" is raised.
* **The registered rules still compute:**
  * the scorer's dev run writes their selection to `selection_registered.json`;
  * its holdout run writes their recommendation into `readings.json`;
  * the decision files carry both outcomes, and say whether they agree.
* **The files:**
  * `system_decide.py --dev` writes `results/selection.json`, the selection in force, with the decision layer's marker.
    It also writes `dev/decision.json` (the 2018–24 rule test, the RES_ONLY readings and the input flags).
  * `--holdout` writes `holdout/decision.json`.
* **What changed in `system_pairs.py`** (nothing that measures):
  * the registered selection's file name;
  * the holdout's check for the marker;
  * the freeze's file list, now with `system_decide.py`;
  * the freeze's matching: each hash may sit in any verified addition, so addition 4b can list only what changed.

  The harness re-run is exact (9e-17, 4e-16).
* **Tests:** `test_system_decide.py`, 14 tests (after erratum 1: share arms reading better leave SYS selected; a remaining challenger reading better is selected).
  * the harm edges;
  * the switch rule, where the registered rule would switch at P 0.93 and the amended one does not;
  * the largest gain and the winner's luck;
  * REF only on harm, where the registered rule would fall back on a resolved −0.05;
  * the recommendation's refusals;
  * the rule test per tour, and the RES_ONLY flag;
  * dev end to end.

  `test_system_pairs.py` has 34 tests, including the marker and the spread-out hashes.

## The supplementary mode (addition 5): `src/eda/lower_level_evidence/system_supplementary.py`

*Observed* (the code; the lead's ruling of 10 Oct, option 2). It scores the arms outside the selection set when they are
fitted, before or after the unlock, so the men's primary is not held while they are built.
* **Scope:**
  * RES_ONLY and SYS_BOTH on dev and holdout (against REF, with strata and seasons; SYS against RES_ONLY);
  * SYS_ITFASIS and SYS_BOTH_ITFASIS on the holdout, and on dev only where their inputs differ before 2025 (addition 2
    §2);
  * NEW_ASIS, NEW_SYS_BOTH and NEW_ASIS_PRE on dev and holdout, with addition 1's pairs and addition 4's rule-test
    verdict (`system_decide.rule_test`, unchanged): dev decides the 2018–24 additions, the holdout the 2025–26 ones.
* **Refused:** the six selection arms, and anything outside the scope.
* **Never touched:** `selection.json`, the primary and any selection arm's reading. SYS and SYS_BOTH enter only as the
  comparators the pairs name.
* **Measurement:** the scorer's own functions (`load_models`, `readings`, `pair_rows`); the 2026 speed rule as the main
  run's, with the drop-909 sensitivity beside it. Holdout seasons need the unlock; dev seasons read to 2024.
* **Where:** `results/supplementary/<dev|holdout>/`: `<ARM>_pairs.csv`, `<ARM>.json`, `rule_test.json`, and the
  `_drop909` versions.
* **The freeze:** it refuses unless its own SHA-256, and those of the scorer's frozen files, are in verified additions
  (addition 5).
* **Tests** (`test_system_supplementary.py`, 7):
  * the selection arms and out-of-scope arms are refused;
  * it runs after a real unlock, while the main dev run refuses;
  * `selection.json` is unchanged byte for byte, and nothing is written outside `supplementary/`;
  * the rule-test verdicts per period, and the RES_ONLY flag read from the main holdout decision;
  * the freeze.

  All D tests: 55 pass.

## The harness check

*Observed* (`results/harness/harness.json`, `pairs.csv`; re-run on the final code). The first run's FP and R_S2
(`candidates/`, read only) went through the scorer, 22,265 matches (men 11,672, women 10,593).

| Comparison, both stages, 2020–2024 | This scorer | The first run |
|---|---|---|
| FP vs REF, both tours | +0.024 [−0.047, +0.096], unresolved, P(better) 0.751 (t: 0.750) | +0.024 [−0.047, +0.096], P 0.75 |
| FP vs REF, men | +0.083 [+0.002, +0.164], **better** | +0.083 [+0.002, +0.164], better |
| FP vs REF, women | −0.040 [−0.154, +0.073], unresolved, P 0.24 | −0.040 [−0.154, +0.073], P 0.24 |
| FP vs R_S2, both tours | −0.003 [−0.165, +0.160], unresolved, P 0.49 | −0.003 [−0.165, +0.160], P 0.49 |
| FP vs REF, share gap ≥ 0.5 | +0.165 [+0.004, +0.326], **better** | +0.165 [+0.004, +0.326], better |

* **Against compare.py** (FP's `scores.csv`; both stages and stage 1; three tours): 6 rows, the largest difference 9e-17.
* **Against the first run's scorer** (`candidates/results/pairs.csv`): 27 rows. They cover FP against REF in every
  stratum and season, R_S2 against REF, FP against R_S2, and each model against its close. The largest difference is
  4e-16; the t-CDF P(better) differs by at most 1e-16.

## The fit queue: `src/eda/lower_level_evidence/system_fits.py`

*Observed* (the code).
* **The runners are reused, never edited.**
  * 58 inputs: `model_rebuild/fits.py --out <arm> --seeds 0-3 --seasons 2019-2026 --wait-memory-only`.
  * 60 inputs (SYS_S2, R_S2): `candidate_fits.run`, called by `--fit60`. The first run's G5 check must have passed.
  * Both go through `./python_tabpfn_local.sh`, one fit at a time. Each fit waits for 12 GB free on the card. Another
    session's runner shares the card, so a fit takes about twice its solo time.
* **Fitting reads training outcomes only:** season Y trains on 2013 .. Y − 1. No score is computed.
* **The frame check** (`results/checks/<ARM>_frame.json`), before any fit. It requires:
  * 67,226 matches in the reference's ids and order. The candidate-Stage-0 arms instead need no duplicate ids, and are
    read on the matches both frames hold; E found these arms could never pass before, and that is fixed;
  * the identifiers equal; the training labels to 2025 equal (a hash; only the equality leaves the function);
  * the inputs as the reference's, plus only registered extras;
  * every moved input and tour inside the arm's written expectation.

  For RES_ONLY it also reports whether its Elo inputs equal SYS's. A failed check holds the arm; it is not fitted.
* **The input check** (`--part1`): compare.py's part 1, with no result read. It refuses until the arm's expected change
  is written down. Its flags are read against each tour-season's evidence mix, not a median split.
  * *Observed,* on the first run's FP: `points_52w`'s change ranks with the tour-season's mean lower-level share
    (Spearman 0.63, men and women). That is the broad change the first run argued for.
* **D-built arms** (`results/arms/`):
  * R_S2: a hashed copy of `candidates/R_S2`, with 2025–2026 added;
  * SYS_PLACEBO: SYS's per-match change, permuted within tour × season, `default_rng(20261009)`;
  * SYS_S2: SYS plus R_S2's two share columns. *Inferred:* those columns count ITF box scores, which SYS excludes; this
    matters only in 2025–2026, and for women from 2022.
* **Copies** are registered with their hashes (`copied_registry`), and `--check-fits` fails any other fit made on
  another frame. Two rules decide when a copy is made:
  * REF_noITF: the reference's 2019–2024 fits only if its inputs to 2024 are identical and one refit (2024, seed 0)
    equals the stored fit exactly;
  * SYS_ITFASIS and SYS_BOTH_ITFASIS: their base arm's 2019–2024 fits only if every input is identical through 2024.

  Otherwise every season is fitted (addition 2 §2).
* **Women's ITF box scores before 2025** (Observed, Stage 0 count, no outcome): 31 matches in 2022. Men have none before
  30 Dec 2024. So REF_noITF's and SYS_BOTH_ITFASIS's women's inputs may differ before 2025. Their expectations were
  amended before the arms existed, and the earlier text is kept.
* **The continuous queue** (`--poll`, one at a time: `results/poller.json`). The highest-priority READY arm goes next,
  each arm's 2025–2026 fits right after its 2019–2024 fits. The order is the lead's of 10 Oct:
  1. SEP_ALL, REF_noITF, SYS, SYS_w0, SYS_w100, RES_ONLY;
  2. SYS_S2, SYS_PLACEBO, SYS_w50, SYS_NOCLASS, SYS_BOTH;
  3. SYS_ITFASIS, SYS_BOTH_ITFASIS, NEW_ASIS, NEW_SYS_BOTH, NEW_ASIS_PRE;
  4. the optional SYS_w25 and SYS_w75.

  * It ran from 21:03 UTC. It was stopped idle at 00:38 UTC, with no arm READY, and restarted on the fixed code.
  * It runs no score.
* **Fit times** by season: `results/fit_times.csv`, `fit_times_by_season.csv`.

## The fits so far

*Observed* (`results/fits_queue.log`, `results/fit_times_by_season.csv`).

| Arm | Seasons | Fits | Seconds per fit | Notes |
|---|---|---|---|---|
| R_S2 | 2025 | 4 | 88–94 (free card: 44) | the 2019–2024 fits are the first run's, copied with their hashes |
| R_S2 | 2026 | 4 | 105–113 (free card: 54) | 20:16–20:30 UTC for the 8 (807 s) |
| SEP_ALL | 2019–2026 | 32 | 23 (2019) – about 75 (2026) | 02:00–02:26 UTC (1,549 s); frame and fit checks pass |
| REF_noITF | 2019–2026 | 32 | 37–77 by season (mean) | 02:32–03:01 UTC (1,753 s), fitted in full by hand; fit checks pass |
| SYS | 2019–2026 | 32 | | READY 05:12; 05:14–05:38 UTC (1,463 s); frame and fit checks pass |
| SYS_w0 | 2019–2026 | 32 | | READY 05:19; 05:39–06:01 UTC (1,351 s); frame and fit checks pass |
| SYS_PLACEBO | 2019–2026 | 32 | | built 05:2x from SYS; 06:02–06:19 UTC (1,043 s), in the idle gap; checks pass |
| SYS_S2 | 2019–2026 | 32 | | built 05:2x from SYS; 06:19–06:37 UTC (1,047 s), in the idle gap; checks pass |

* **The order of work** (the lead's message of about 05:00 UTC).
  * The selection set (SYS, SYS_w0, SYS_w50, SYS_w100, SEP_ALL, SYS_NOCLASS) is fitted first, as each arm is READY.
  * Report-only arms are fitted only in idle gaps, and only while two or more selection arms are still unbuilt, so
    they cannot delay the dev scoring.
  * The frozen queue's own order differs, so it was stopped while idle (05:02 UTC). Since then I run the frozen
    `system_fits.py` commands by hand: `--verify`, `--part1`, `--fit` and `--check-fits`.
* **SEP_ALL's input check** (no result read):
  * 44 inputs changed, all men's, in every season from 2013. All are inside the written expectation.
  * Missing values appear where lower-level evidence leaves: forms 585 rows, `points_52w` 1,066.
  * Every changed input reads "uneven" by construction, since women's seasons never change.
  * Against the evidence mix, the flagged changes are broad men-only changes in every era (scale ratios 0.37–1.43,
    level shifts within ±0.05 SD), as complete separation implies.
* **REF_noITF: the waiver** (the lead's ruling of 10 Oct; E's CP1b).
  * My frame check (exact equality, by season) held it on solver rounding only. Before each tour's first ITF box score
    (men 30 Dec 2024; women 2 May 2022, by match start), the largest change is 4.0e-15. C2's gates document this as
    the decided solver's own rounding.
  * Seven women's matches of an event starting 28 Apr 2022 do change for real. They are played after 2 May, so the
    ITF results legitimately reach them.
  * So it was fitted in full (32 fits, no reference fit copied) through the frozen `--fit`.
  * The same rule holds for any later arm whose only pre-2025 difference is rounding below 1e-12: fit it in full and
    record it here.
* **REF_noITF's input check:** 41 box-score inputs changed (Elo untouched). The flags sit only in 2025–2026 cells (the
  products and `ratings_iid`). For women they track the ITF share (Spearman 0.9–1.0): finding #6 reversed, as C2
  predicted.
* **SYS's input check** (no result read; `arms/SYS/vs_reference_2026-10-08/`). 44 inputs changed, all men's, in every
  season; women are identical (also C1's G2). Few new missing values: forms 3 rows, `points_52w` 4. The largest median
  changes, in the reference's SD, are `points_52w` 0.46, `adjperf_tpw_2w` 0.24 and the forms 0.18–0.22. 10 inputs are
  flagged, in 56 tour-season cells (scale ratio 0.70–1.43; level shift −0.068 to +0.020 SD).
  * `points_52w` is flagged in 13 of 14 men's seasons, a broad widening in every era. That is the first run's FP
    pattern, not finding #6's shape.
  * The six products are flagged in 2016–2021 and 2025–2026. In 2025–2026 the size of the change tracks the ITF share
    (Spearman 0.42–0.56): SYS excludes the ITF box scores, as REF_noITF does. In 2016–2021 it tracks the lower-level
    share (0.28–0.49), and 2016–17 is when men's Challenger-qualifying rows get w = 0.
  * Three single-season form flags (2022, 2023) sit just over the 10% line.
  * *Inferred:* every flag is explained by the tour-season's dose: the lower-level and ITF shares, and the registered
    conventions. None shows input-flag harm in the owner's sense (section 1).
* **SYS_w0's input check:** the same 44 inputs, larger changes. Products move by up to 0.54 SD, and missing values
  appear as in SEP_ALL (forms 585 rows, `points_52w` 1,066), since w = 0 removes lower-level box evidence. It has 31
  flagged inputs in every era, the broad pattern of complete separation for statistics.
* **SYS_PLACEBO's input check:** the same 44 inputs move by the same size as SYS's. `points_52w` is flagged in all 14
  seasons (SYS: 13), and `prod_df` once. Its frame passes (`provenance_D.json`): change SD ratio to SYS's 0.999–1.000,
  |correlation| with SYS's change ≤ 0.023. Up to 4 cells per input keep the reference's value, where SYS changes the
  missing pattern.
* **SYS_S2's input check:** SYS's 44 changes exactly, plus the two share inputs.
* **R_S2's frame check passes.** Its 58 base inputs are the reference's, and its two extras are as registered.
* **All 32 R_S2 fits pass** the fit-file and provenance checks. No forecast was compared with a result.
* **R_S2's input check:** none of the 58 inputs changed; nothing is flagged.

## Open points for the lead

1. **The unlock must hold** the hash of every pre-registration file on disk (the original, additions 1–4, 4b, 4c)
   and of the dev `selection.json`: `b5fbec82b54229c6d424c3c5e7f22bd927de6fb52ade710dac97e062b84e3ee1`.
2. **The dev rule test needs a decision before the unlock.** Section 5's dev verdict on C0_now's 2018–24 additions
   needs NEW_SYS_BOTH's and SYS_BOTH's dev readings, which do not exist yet.
   * In the frozen code, only `system_decide.py --dev` writes that verdict. It also rewrites `selection.json` (the same
     selection, a new time stamp, so a new hash), and it refuses once the unlock exists.
   * So either those arms are scored, and `--dev` re-run, before the unlock, with the unlock holding the final hash;
     or the dev verdict is added after the unlock through a new addition (a code change).
3. **The second dev run** (RES_ONLY, SYS_BOTH, the ITFASIS and C0_now arms once fitted) uses `system_pairs.py --dev`.
   It rewrites `selection_registered.json` and `dev/*.csv`, never `selection.json`, and it refuses after the unlock.
4. **Addition 1's C0 arms** wait on F's fixes and E's re-audit (E's S9). Their frame check admits them.

## What it does not show

* **Dev only.** These are the readings of 2020–2024, seasons many earlier studies have read. The selection was made on
  them. Only the holdout primary is free of the selection.
* **Resolution.** For men, SYS against REF has a 95% half-width of about 0.15 mLL on dev. A true gain of the first
  run's size (+0.08) would usually read unresolved, and so would a harm under 0.15.
* **The harness checks the arithmetic, not the arms.** C1's frames are checked by the frame and input checks and by C1's
  gates; the readings take the arms as built.
* **P(better) under Φ and under the t CDF** can differ near a threshold (0.90, 0.80 or 0.50). Both are recorded, but
  only Φ decides, as pre-registered.
* **Holm's p is normal, the interval is t.** A reading can therefore be worse after Holm while its raw label is
  unresolved. This is the lead's ruling; the raw labels are reported beside it.
* **Four seeds.** Seeds 0–3 only, as pre-registered. The decided application averages 16.
* **The queue trusts READY.** If C1 rebuilds an arm after READY, the provenance check refuses its stale fits at scoring.
  Nothing stops a rebuild while a fit is running.
