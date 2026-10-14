# Pre-registration, addition 4: the owner's decision of 9 October replaces the decision layer

Written by the lead, 10 October 2026, about 03:00 UTC (the exact time is in `status.log` at hashing). Own SHA-256:
`preregistration_addition_4.sha256`.

## When this was written

* **No model-level score of any arm of this run exists.**
  * SEP_ALL and REF_noITF have fits and compare.py's part 1 (the input check) only. No `scores.csv` exists.
  * No dev or holdout reading has been computed.
  * `holdout_unlock.json` does not exist.
* **Earlier files are unchanged:**
  * `preregistration.md`: `cc65bcd5…`
  * addition 1: `c718e6d0…`
  * addition 2: `3f536796…`
  * addition 3: `f2063433…`

## The source

**The owner's decision of 9 October 2026.** `docs/decisions/2026-10-09-adoption-by-change-class.md`, sha256 `e72e9ae213b52936b4e2c7b16e6b94c80c060e3fe4e9947ecd43766785140d82`, quoting the owner: "I accept your adoptation logic, implement it."

**Its application to this study.** `data/studies/lower_level_evidence/system/owner_decision_2026-10-09.md`, sha256 `7e7f35da2a7c819f60dd897dd7ec98d299563b3c606de2a927db42debe25e7f0`.
* Session `tennis-predictions-cc` wrote it at the owner's instruction. Its file time is 02:55 UTC; its text gives "02:55–03:15 UTC".
* That session read no score of this run.

**This addition adopts that file's sections 1–5 as this study's decision layer.** They are restated below in the lead's words. Where the two texts differ, the owner's file governs.

## What changes and what does not

**Unchanged: everything that measures.**
* the arms, builds, gates and parameters (addition 3's frozen internals);
* the scorer's readings, intervals and labels;
* addition 2's eight Holm-corrected holdout readings and its 2026 speed rule;
* the holdout's single opening, with its three conditions;
* every registered reading, which is still computed and reported in full.

**Replaced: the rules that turn readings into a selection, a recommendation, or the rule test's interpretation.** That is the original pre-registration's "Selection rule" steps 1–2 and "Recommendation", and addition 1's "Interpretation".

## The decision layer, as it now stands

**Harm.** A reading shows harm when the named model is worse by more than 0.10 mLL with its whole 95% interval below 0. An input flag shows harm only when F's hashed expected unevenness, read against the tour-season's dose, does not explain it.

**Selection on dev (men, 2020–2024, both stages).**
* SYS is selected unless a challenger reads "better" than SYS: its 95% interval against SYS clears 0.
  * The challengers: SYS_w0, SYS_w50, SYS_w100, SEP_ALL, SYS_NOCLASS, SYS_S2 and R_S2.
  * If several qualify, the one with the largest point gain is selected.
  * Its estimate is also reported after the winner's luck of seven challengers (SE × 1.35).
* REF is selected instead (no change) only if the selected arm shows harm against REF for men on dev.

**Recommendation (men).** SELECTED is recommended for the men's final model unless either of these shows harm:
* the holdout primary (SELECTED against REF, men, 2025–2026);
* any of addition 2's eight readings, Holm-corrected.

If harm shows, REF is recommended and what drove the harm is reported. No edge credit either way: the edge that sizes stakes comes only from untouched matches at the venue's price.

**The rule test (addition 1), as it now reads.**
* **The question.** Does the excluded data harm the model when it enters by the route its statistic-level evidence supports? That route is the system's treatment, NEW_SYS_BOTH:
  * role B's translation and weights for every new box score;
  * B's w_results for every new result;
  * w = 0 where B's fits or the pre-registration set it, for example ITF and ITFQ box scores until P7.
* **The default.** C0_now's additions are recommended for entry by that route, for each tour whose treatment is the system's, unless NEW_SYS_BOTH against SYS_BOTH shows harm for that tour:
  * on dev, for the additions of 2018–2024;
  * on the holdout, for those of 2025–2026.
* **If REF is recommended for men,** the men's results keep a supported route: B's w_results, as in RES_ONLY. RES_ONLY on C0_now is then registered as the next candidate.
* **Women** follow their treatment after P7. Women's part of this recommendation, and the 2025–26 ITF box scores already in the reference (REF_noITF against REF), are decided with that treatment by the same rule. Those readings are its harm evidence.
* **NEW_ASIS and NEW_ASIS_PRE** are read and reported, but they do not decide entry. They show what the rule of 8 October protects against.
* **Struck:** "the rule costs nothing to keep". The report names what keeping data out forgoes.

**The rates.** The owner's file, section 6 (`src/eda/adoption_framework/level_evidence_rules.py`) gives how often these rules adopt a SYS that helps and how often one that harms. The final report quotes them beside the readings.

## Implementation

Role D implements this layer without changing what the frozen scorer measures. It writes the selection and the recommendation under these rules, and the registered rules' outcome beside them for the record.

Any code it adds or changes is hashed in a short dated addition (4b) before the first dev score. D's guard requires that addition. Section 1 of the owner's file (the harm tolerance) may not be loosened once any score it governs exists.
