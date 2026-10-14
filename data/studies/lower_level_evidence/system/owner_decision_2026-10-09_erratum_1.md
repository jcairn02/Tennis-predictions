# Erratum 1 to `owner_decision_2026-10-09.md`: the share arms are report-only, and the tolerance is Claude's choice

Written 10 October 2026, about 04:00 UTC (9 Oct, 21:00 local), by session `tennis-predictions-cc`, after an independent
review of the amendment. This file has its own SHA-256 (`owner_decision_2026-10-09_erratum_1.sha256`).

**When it was written.**
* No score of this run existed: no arm's `vs_reference_2026-10-08/` folder held a `scores.csv`, and there was no
  `selection.json` or `selection_registered.json`.
* SYS-family arms had no fits.
* The lead's additions 4 and 4b were on disk.
* The writer read no score, no part-1 output and no line of `status.log`.

**The files it corrects are unchanged:** `owner_decision_2026-10-09.md` (`7e7f35da…`) and the lead's addition 4
(`754e055c…`) and 4b. This erratum governs where it differs from them, as the owner's file does.

## 1. R_S2 and SYS_S2 are reported, not challengers (corrects section 2)

* **The error.** Section 2 kept the registered challengers, which include R_S2 (the reference plus the two box-score
  share inputs) and SYS_S2 (SYS plus the same two inputs). Under section 4, a challenger selected on dev is recommended
  unless harm shows.
* **Why that contradicts the decision.**
  * The two share inputs are a new feature, found on 2020–2024: the event-levels study's mispricing and the first
    run's R_S2.
  * Under the decision's point 6, a new feature goes to the pool, and a selection round decides. A lead is confirmed
    outside the seasons that found it.
  * Selecting one of these arms on its 2020–2024 dev reading would adopt that lead on its discovery seasons.
  * The decision re-files the share signal as a pool admission
    ([feature universe](../../../../docs/studies/feature_universe/README.md), § 9).
* **The correction.**
  * The challengers are SYS_w0, SYS_w50, SYS_w100, SEP_ALL and SYS_NOCLASS.
  * R_S2 and SYS_S2 are still fitted, scored and reported, against REF and against SYS, as registered. Their readings
    are lead evidence for the pool, with their seasons recorded. They do not enter the selection.
* **The rates with five challengers** (SE 0.035; ρ = 0 / 0.5 / 0.9; `level_evidence_rules.out`):
  * no challenger truly differs: the amended rule switches 0.12 / 0.09 / 0.05 of the time (the registered rule
    0.41 / 0.29 / 0.17);
  * one challenger truly better by 0.10: 0.83 / 0.82 / 0.82.

## 2. The 0.10 tolerance is Claude's choice (corrects section 6's last sentence)

* Section 6 said: "That trade is the decision's." That overstates it.
* The owner accepted the logic: a harm check with a stated tolerance. The value 0.10 is Claude's choice, in the form of
  the owner's Roland Garros rule. It accepts a true 0.05 harm about 70% of the time.
* The owner may set another value. Until then, 0.10 stands. It may not be loosened once any score it governs exists
  (section 7).

## 3. For the lead

* `system_decide.py` (addition 4b) lists the challengers. Removing R_S2 and SYS_S2 from that list is a code change
  that needs a dated addition (4c) before the first dev score.
* Everything else in additions 4 and 4b stands.
