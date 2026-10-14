# 02: How 2025–2026 is already known, what the rebuild removes, and the forecast of what remains

Units are mLL per match. Here **+ = the holdout overstates the edge**: an expected bias, not a result. **This document quotes no 2025–2026 result.** It uses only interval widths (noise levels) and D-only figures. The channels come from the [feature-provenance audit](../feature_provenance/README.md), which reviewers with the holdout-auditor role may read.

## 1. Why re-selecting cannot clean everything

**1. The inflation of a picked arm.** A choice picks among k arms on a window W. The picked arm's estimated advantage is inflated by its selection bias β = E[noise | picked]. With equal true arms, β ≈ σ · m_k:
* σ is the standard error of the arms' difference;
* m_k is the expected maximum of k standard normals: 0.56, 0.85, 1.03, 1.27 and 1.54 for k = 2, 3, 4, 6 and 10.

**2. A holdout inside the decision window inherits all of it.** If n_C of the holdout's n_H matches lie in W, the holdout's expected inflation is (n_C / n_H) · β. A holdout entirely inside the window (2025–2026 inside a 2022–2026 or 2013–2026 window) carries the full β. A bigger W helps only because σ shrinks.

**3. Re-deciding on D does not undo it.** Treat the picked arm as a modification of its alternative. The original pick conditioned the holdout's noise in the modification's favour.
* If the rebuild picks the same arm, its H edge carries about β.
* If it picks the alternative, about 0.
* With p the probability that the rebuild repeats the choice, the expected residual is about p · β.
* D's evidence agreed with most of the earlier choices (the audit's group A), so p is high. Most of the imprint survives re-selection.

**4. Choices made on another metric carry over only partly.** A choice made on metric A (no odds, the 24-hour price, gain over Elo) inflates the closing-line metric B by β_A · ρ · σ_B / σ_A ≤ ρ · σ_B · m_k, where ρ is the correlation of the two metrics' noise. A choice made on a noisy metric leaks into the precise closing-line metric only through σ_B, which is small for arms of the same model.

**5. Near-certain choices carry little bias.** If the choice would have been made under almost any noise draw (a large effect, or an a-priori commitment), the conditioning is weak and β is near 0. Most inclusions on gains over Elo are of this kind: effects of 1–5 mLL against noise of 0.1–0.3.

**Noise levels used below** (interval half-width / 1.96, from the studies):

| Comparison | SE |
|---|---:|
| Two arms of the same model at the close: surface-IOS swap | ≈ 0.06 |
| The offset-Elo swap | ≈ 0.10 |
| Speed as a TabPFN column against the base (men, 3 seasons) | ≈ 0.06 |
| The speed adjustment against the base (men, 3 seasons) | ≈ 0.19 |
| A model against the close, per match | sd ≈ 43–50 |

## 2. The channels

**Stage 1, both tours.** "Residual" is the expected bias left in the rebuild's raw H edge, central (plausible range).

| # | Channel | How 2025–2026 got in (audit) | Rebuild action | Residual |
|---|---|---|---|---|
| 1 | Constants fitted on H | Only the short IOS memory (4 or 13 weeks), picked on all seasons. Every other constant was fitted on 2013–2018 | The memory becomes an axis chosen on D; the rest stay, as D-fitted | 0 |
| 2a | Offset Elo over the blend | Owner, 6 Oct, with 2022–26 (no price, close) and 2025–26 (24-hour price) readings in view | D decides between blend, offset and overall (pre-2022 evidence favours the offset, p ≈ 0.8); cross-metric, ρ ≈ 0.5; k ≈ 2–3 decisive arms | 0.04 (0.02–0.11) |
| 2b | Surface over pooled IOS | Kept on a criterion declared after the pre-registered 2022–26 test had been read | An axis on D (p ≈ 0.7) | 0.01 (0–0.03) |
| 2c | Calibration form (walk-forward slope) | Need found and form added on 2022–26 | Form and start year chosen on D | 0.01 (0–0.02) |
| 2d | The odds as an input, not stacked | Chosen from free models' 2022–26 scores; also standard practice | Fixed by mechanism, written before any score; or checked on D (Q6) | 0.03 (0–0.1) |
| 2e | The 2 Oct family set | Chosen mostly on large gains over Elo, pooled 2013–2026 | The whole menu competes on D | 0.01 (0–0.05) |
| 3 | Ideas that exist because of H-inclusive results | The learner kept after its first test on 2022–26, though it was the owner's choice beforehand; the surface-IOS premise read off TabPFN's 2022–26 outputs (counted in 2b) | Cannot be removed; disclosed; the a-priori-menu sensitivity (Q26) measures part of it | 0.03 (0–0.1) |
| 4 | Knowledge of H in the protocol's design | Authors and reviewers have read H results | Symmetry rule, D-only justifications, blind executors, review rounds | 0.05 (0–0.15) |
| 5 | Data fixes found while looking at 2025–26 data | input_data_audit found errors by inspecting data, not outcomes | Every fix decided on data evidence, applied to all seasons before the look | ≈ 0 |
| 6 | Picking the headline among many H readings | — | One pre-registered primary | 0 |
| 7 | Walk-forward inside H (2026 trained on 2025 outcomes) | — | Mechanical, frozen rules | 0 |
| | **Total, raw** | | | **≈ 0.2 (0.05–0.45)**. Every worst case added together gives about 0.6, an unlikely combination |

**Stage 2 (men's speed adjustment, its gain over stage 1).**

| # | Channel | Residual |
|---|---|---|
| S1 | The form (adjustment or column) chosen on men's 2024–26 (H inside that window); k ≈ 2, SE of the difference ≈ 0.18; the rebuild decides on 2022–2024 (p ≈ 0.7 that it repeats the choice) | 0.07 (0.03–0.15) |
| S2 | The memory chosen after two outcome runs on 2024–26 (the 28-day value itself came from a result-free target); p ≈ 0.6 | 0.04 (0–0.07) |
| S3 | The speed idea, promoted on a 2022–26 window when 2025–26 had few speed readings (about 13% of those matches) | 0.03 (0–0.06) |
| | **Total, raw** | **≈ 0.15 (0.05–0.3)** |

## 3. The forecast

| | Stage 1 (both tours) | Stage 2 (men) |
|---|---|---|
| **Rebuild, raw H edge** | ≈ 0.2 (0.05–0.45) | ≈ 0.15 (0.05–0.3) |
| **Rebuild, corrected** (§4 removes channels 2a–2e and S1–S2; channels 3, 4 and the correction's own error remain) | ≈ 0.1 (0–0.25) | ≈ 0.05 (0–0.15) |
| The current model, read on H-exposed as it is (every choice repeated with p = 1, plus the decisions to keep it after challengers were tested on 2025–26, plus repeated readings by its designers) | ≈ 0.35 (0.2–0.6) | ≈ 0.25 (0.1–0.4) |
| H's sampling noise, 1 SE | ≈ 0.50 (8,593 matches; per-match sd ≈ 46) | ≈ 0.25 (a paired gain on 4,394 men's matches; per-match sd ≈ 16) |

**In proportion.** The current design's edge over the close in 2020–2024 (D data only) was +1.46 [+0.84, +2.08] (+ = model better). If the rebuild's true edge is near that, the raw H edge overstates it by **about 15% (4–30%)**, and the corrected one by **about 7% (0–17%)**.

**Why most of the bias survives a rebuild.** Most of the residual sits in choices the rebuild will probably repeat because D agrees with them. Re-selection protects H from new choices. The old imprint is removed only by the correction (§4), or by matches that no choice saw (H-sealed).

**Where to spend effort.**
* **Stage 1:** leakage is not where the holdout's error will come from (±1.0 at 95% against a bias of 0.1–0.2). Extra rigour buys less than extra sealed matches. H-sealed adds about 5,000 matches a year.
* **Stage 2** is different. Its raw bias (≈ 0.15) is over half of its SE (≈ 0.25), so its reading leans on the correction, and on H-sealed men's matches with speeds.

## 4. The bias correction

1. **Who and when.** An auditor who is not an executor computes, before the look, an estimate β̂_j for each original choice j, on the closing-line metric, with an interval:
   * by a block bootstrap of the original decision on its original window, using the stored per-arm forecasts (the feature-provenance plan's phase 3): resample four-week blocks, re-apply the recorded rule, and average the chosen arm's in-resample advantage minus its original advantage;
   * or, where a choice's forecasts are not stored or its rule cannot be codified, by the bound ρ · σ · m_k with ρ = 1.
2. **Sealed.** The estimates are hashed and sealed. The executors never see them.
3. **At the look.** Corrected edge = raw − Σ β̂_j over the choices the frozen rebuild repeats. The β̂ uncertainty is added in quadrature to the interval.

**Caveats (for the statistician, Q13).**
* β̂_j is estimated in the current model's context and carried over to the rebuild's.
* It is an expected bias, not this draw's realised one.
* The bootstrap of a decision that people made by judgement is only as good as its codified rule.

## 5. Sensitivity

* **ρ near 1** rather than 0.5: the raw stage-1 figure rises to about 0.3.
* **The rebuild repeats every earlier choice** (p = 1): +0.05.
* **The protocol carries defaults that favour what is known to work on H:** up to +0.15. Catching these is the review's main job.
* **The rebuild departs from the current design** (different families win on D): the raw figure shrinks toward channels 3 and 4 alone.
* **Choices not listed here.** Each adds its p · β. The holdout auditor's first task is to find them.

## 6. What would show this forecast wrong

* **Raw minus corrected well above 0.3:** the imprint of earlier choices is larger than forecast.
* **H-exposed beating H-sealed by more than the corrections, once H-sealed can resolve it** (about 5,000 matches): unmodelled leakage, or a change of era. Only time separates the two.
* **The rehearsal (stage 5) shows a large drop from D to the pseudo-holdout:** the selection overfits D more than assumed. That lowers the true H edge but does not bias its estimate.

## Open questions in this document

Q13 (whether the correction is valid), Q25 (what if the rebuild reproduces the current model), Q26 (the a-priori-menu sensitivity). Reviewers are asked to challenge every p, ρ and k above.
