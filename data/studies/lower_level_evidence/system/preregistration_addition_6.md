# Pre-registration, addition 6: the conditions of checkpoint 2, written before the holdout opens

Written by the lead on 10 October 2026, about 08:35 UTC, after the red team's CP2 verdict ("pass with conditions";
`docs/studies/lower_level_evidence/system/E_red_team.md`, "Checkpoint 2"). Its own SHA-256 is in
`preregistration_addition_6.sha256`.

When this was written, no holdout reading existed and `holdout_unlock.json` did not exist.

The earlier files are unchanged:

| File | SHA-256 |
|---|---|
| `preregistration.md` | `cc65bcd5…` |
| Addition 1 | `c718e6d0…` |
| Addition 2 | `3f536796…` |
| Addition 3 | `f2063433…` |
| Addition 4 | `754e055c…` |
| Addition 4b | `f4e2e405…` |
| Addition 4c | `7c7ff69a…` |
| Addition 5 | `f9d12ac4…` |

## 1. The harm check's real rates, from the observed SE (E's condition C1)

**The observed SE.** The dev reading of SYS against REF, men, is −0.008 [−0.162, +0.145] mLL, an SE of about 0.078.
Almost all of that is the four-week block term (0.075). The seed term is 0.013, as in the first run. SYS moves forecasts
about twice as much as the first run's FP did, so its paired interval is wider than the power note's 0.08 half-width.
On the holdout the SE is expected to be about 0.12.

**What the harm rule then needs.** The rule (addition 4, from the owner's file, section 1): worse by more than 0.10 mLL,
with the whole 95% interval below 0. At SE 0.12, a holdout reading shows harm only when its estimate falls below about
−0.24.

**How often it then flags a true harm** (E's computation, `audit/cp2/`):
* a true −0.10: about 11% of the time;
* a true −0.20: about 35%.

The owner's file (section 6) stated 31% and 86%. Those figures assumed an SE of 0.063.

**What it means, written before the holdout is read.**
* The holdout's harm check can catch only a large harm, of roughly 0.3 mLL or more.
* A reading of "no harm" is weak evidence of safety.
* The recommendation rests mainly on the statistic-level evidence, as the owner's decision intends for a repair. The
  final report says this plainly beside the readings.

## 2. The reading of record (E's condition C2)

* **Each arm's first holdout reading is the one of record,** whether it comes from the main holdout run or from the
  supplementary scorer (addition 5). Later runs of the same arm and pair are reproductions. They are reported as such,
  never as replacements.
* **The same holds for dev readings made in supplementary mode,** and for the rule-test verdicts. NEW_SYS_BOTH's
  holdout reading decides entry for C0_now's 2025–26 additions.

## 3. What the unlock holds (E's condition C3)

`holdout_unlock.json` holds the SHA-256 of:
* every pre-registration file on disk, including this one;
* the dev selection, `results/selection.json` (`b5fbec82…`);
* the decision layer's other sources:
  * the owner's file, `owner_decision_2026-10-09.md` (`7e7f35da…`);
  * its erratum, `owner_decision_2026-10-09_erratum_1.md` (`edb9b377…`);
  * the owner's decision record, `docs/decisions/2026-10-09-adoption-by-change-class.md` (`e72e9ae2…`);
  * `system_decide.py` (`82956043…`).

## 4. Facts recorded for the final report (from E's CP2)

* **The decision layer was applied exactly.** No challenger reads "better" than SYS for men. SYS against REF is not harm,
  so SYS is selected.
* **What the registered rules would have done.** They would have selected SYS_S2 at step 1 (P 0.95 of beating SYS).
  Under their step 2, REF would then have been preferred to SYS (P 0.46 < 0.50).
* **What made the difference: the threshold, not the erratum.** Addition 4's rule with all seven challengers also gives
  SYS, because no challenger reads "better" at 95%.
* **When the threshold was set.** The owner's file and its erratum were written before any score of this run. They were
  written knowing the first run's published dev reading of R_S2 (P 0.93).
* **SYS reaches the holdout on its statistic-level evidence.** Its model-level dev reading neither helps nor harms.
