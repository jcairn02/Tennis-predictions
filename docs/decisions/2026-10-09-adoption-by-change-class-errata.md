# Errata to "Adoption by kind of change" (9 October 2026)

Written 9 October 2026 (local), after an independent review of the implementation. The
[decision record](2026-10-09-adoption-by-change-class.md) is left byte for byte as decided: the level-evidence study's
addition 4 cites its SHA-256 (`e72e9ae2…`). These errata govern where they differ from it.
* **E1–E3 correct mistakes.**
* **E4–E7 make explicit what the decision implied.**
* **E8 corrects its application to the level-evidence study.**

They change nothing the owner decided. E1 changes how the holdback is run, and is Claude's recommendation. The owner may
overrule any of them.

## Corrections

* **E1. The holdback's control (point 5).**
  * The decision named the frozen reference of 8 Oct as the holdback's control. It differs from the template by the
    Pinnacle-first odds input, which moves every forecast.
  * A comparison across that change resolves only about ±0.3 mLL. The indoor fill against the reference read +0.007
    [−0.306, +0.320] (+ = the fill better; [indoor fill](../studies/indoor_fill/README.md)). That is too wide to see a
    batch of small changes.
  * **The control is therefore the most recent frozen instance that carries every structural change made since the
    reference.** Today that is the Pinnacle-first instance of 9 Oct
    (`data/studies/current_best_model/pinnacle_first_2026-10-09/`).
  * The frozen reference stays the yardstick for structural changes and for the model as a whole.
  * **Approved by the owner on 9 Oct 2026:** "yes that makes sense and is approved".
* **E2. The resolution (context).**
  * "About 0.02–0.12 mLL" holds for input changes. The 0.12 is the level-evidence study's 2025–2026 men's holdout, not a
    2020–2024 reading.
  * A structural change read on 2020–2024 resolves about ±0.3 (Pinnacle first against the reference).
* **E3. The "about 96%" (context).**
  * It is in [resolution_check.out](../../data/studies/adoption_framework/resolution_check.out), not
    `level_evidence_rules.out`.
  * It is an inference, for the men's dev reading of the data as it stands. It holds for a true gain of 0.01 mLL or less
    (about 90% at 0.02).

## Made explicit

* **E4. Which kinds a visible reading decides (points 3–4).**
  * "When the comparison can see the effect, the reading decides" applies to the kinds decided by evidence: structural,
    tuning, and a feature tested alone.
  * **A repair is decided on data evidence even when its reading is visible.** A correct fix is not vetoed by its
    outcome (framework § 2).
  * **For expansion and accretion, a visible harm inside the tolerance is reported, and the route re-examined before
    adoption.** That is a reading worse than 0, with its interval below 0, by less than 0.10. In the owner's words of
    8 Oct: "if it harms results we will want to make some modifications".
  * **Below resolution:** tuning keeps the default; a structural change is undecided and goes to mechanism, cost and
    the realisation gate. The sign of such a reading decides neither.
* **E5. What counts as a repair (point 1).** "A fix of a measured bias" means a bias in an input already in the model. A
  new input aimed at a market bias is a new feature, and goes to the pool.
* **E6. A costly change pays for itself (points 1 and 4).** "Adopt unless harm" is for free changes. An expansion that
  needs a new live feed carries the framework's cost bar (about 0.05) and is weighed by the arithmetic.
* **E7. The in-season refit's cost (point 7).**
  * It is taken as 0, not the framework's 0.01 for "more fits".
  * It adds minutes to a prediction run that already rebuilds the frame (about 2 hours). It adds no input, no upkeep and
    no live dependency.

## Its application to the level-evidence study

* **E8. Point 9.**
  * R_S2 and SYS_S2 add the two share inputs, a new feature found on 2020–2024, so they are report-only and not
    selection challengers. The study's erratum
    ([owner_decision_2026-10-09_erratum_1.md](../../data/studies/lower_level_evidence/system/owner_decision_2026-10-09_erratum_1.md),
    written before any score) corrects this.
  * The 0.10 harm tolerance there is Claude's choice, in the form of the owner's Roland Garros rule.
