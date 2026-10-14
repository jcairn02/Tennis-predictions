# Pre-registration, addition 1: testing the rule of 8 October

Written 9 October 2026, about 20:45 UTC, by the lead. It was written before any score of this run had been read. The only reading so far is role D's harness check, which re-reads the first run's FP numbers, published before this run.

This file has its own SHA-256 (`preregistration_addition_1.sha256`). The original pre-registration is unchanged (`cc65bcd5…`).

## The owner's request (9 Oct, verbatim)

"Id also like it explored as if we are using some of the data the october 8th rule said not to use (explore it dont
guarntee it to be added, if this rule isnt in place it probabily would be added, so this helps check if it SHOULD or
not. if the oct 8 rule is helpful or harmful)"

## The question

**Is the rule of 8 October helpful or harmful?** The rule says that new lower-level matches, past box scores and new sources enter the model only as a tested candidate.

**The counterfactual.** Without the rule, the template would take any wired lower-level data as equivalent evidence.

**The data the rule keeps out today.**
* The live Stage 0 equals the frozen one: `history.py` on 9 Oct, 20:30 UTC, found 0 differences.
* Every new source is on disk but not wired in.
* Role F builds the candidate Stage 0 **C0_now**:
  * the frozen Stage 0;
  * plus the excluded data on disk on 9–10 Oct that can be linked with validated identity;
  * with the same code re-run as later packages land (P5, P6, P7, P8).
* A natural experiment is already in the reference. ITF box scores of 2025–26 entered its inputs as equivalent before the rule existed, while its training seasons have none.

## New arms

None of them enters the men's selection rule.

| Arm | Definition | Question |
|---|---|---|
| SYS_ITFASIS | SYS, with ITF and ITFQ box scores as the reference treats them (equivalent) instead of excluded; men | Does the system's own entry rule help? |
| SYS_BOTH_ITFASIS | SYS_BOTH, with ITF box scores as-is | The same, for women |
| NEW_ASIS | the template recipe, with no layer, on C0_now | No rule: the new data as equivalent |
| NEW_SYS_BOTH | the SYS_BOTH config on C0_now | The new data through the system |

## Readings

* **Where they are read.** Dev 2020–2024 and the holdout 2025–2026, on both tours together and on each tour.
* **The scoring is unchanged.** Two exceptions:
  * SYS_ITFASIS and SYS_BOTH_ITFASIS are read on the holdout only, because their inputs before 2025 equal those of SYS and SYS_BOTH.
  * For C0_now, its 2018–2024 additions are read on dev and on 2020–2026 pooled, and its 2025–26 additions on the holdout.

The pairs:
* REF_noITF against REF: already registered;
* SYS against SYS_ITFASIS, and SYS_BOTH against SYS_BOTH_ITFASIS;
* **NEW_ASIS against REF:** what the rule is worth for today's excluded data;
* **NEW_SYS_BOTH against SYS_BOTH:** the excluded data under the system;
* NEW_SYS_BOTH against NEW_ASIS.

Also read: the input check on every arm. Role F writes the expected unevenness down before any of these arms is scored.

## Interpretation (guiding; the owner decides)

For each data set: the 2025–26 ITF box scores, and C0_now's additions:
* **The rule is protective** if adding the data as-is reads worse than leaving it out: "worse", or "unresolved" with P(better) ≤ 0.20.
* **The rule is holding the model back** if adding the data reads better, as-is or through the system.
* **Otherwise, unresolved.** The rule costs nothing to keep, so the default stays: new data is a candidate.
