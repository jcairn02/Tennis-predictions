# Lead notes

## 7 Oct 2026, after R2 (`2_audit.md`)

**The auditor's rulings stand in full. No rebuttal round is held.**

* **Contested points 1–2 (centring, basis).**
  * The audit states narrow conditions for change:
    * a leak the as-of build cannot avoid;
    * ≤ 2023 evidence that as-of centring, or ks-first, loses f̂'s *change* information beyond its interval.
  * The audit's own runs already show the change part is the same under both centrings (men +5.02 vs +4.93 km/h²) and under both bases (FE gate +0.34 vs +0.36 pp/SD).
  * A rebuttal could not meet the bar, so it would only add delay. The builders may still record disagreement in their R3 notes, and the R4 probes test the leak condition directly.
* **Contested point 3 (women in A1): the primary population stays men.** The owner's quote and the published signal are men's. Women's values are tested in A3, as ruled.
* **Contested point 4 (P1 → P2, and A3).**
  * **P2 alone is the primary.** The owner asked "by how much", and the strategist's own simulation shows the gate adds no power.
  * **S0 is reported beside P2,** with the decision table in C6.
  * **A3 is `spd_all`.** The women question is open and decision-relevant; a placebo's answer is close to known (column noise ≈ reseeding noise).

**R3 working arrangements.**
* **Test file names carry the study prefix** (`test_ssp_*.py`), so pytest does not confuse them with other studies' tests of the same name.
* **The panel API** (engineer) that features.py (modeller) builds on is fixed in the R3 prompts.
* **Fits:** the lead runs every GPU fit once the panel and the features pass their tests and the auditor's R4 re-implementation agrees. Forecasts are not scored before the pre-registration is hashed.
