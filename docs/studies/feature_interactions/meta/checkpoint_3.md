# Checkpoint 3 (M3): the report against the evidence

7 October 2026 · Meta-auditor · Research evidence, not a decision. I checked every claim in [README.md](../README.md), and the corrected reading in [round3/screen.md](../round3/screen.md), against the evidence files. I did not edit either file.

**Evidence read:**
* the final run's outputs: `final/final_primary.json`, `final_results.json`, `final_run.log`;
* the screen's outputs: `hypotheses/screen_results.csv`, `known_null_results.csv`, `descriptive_results.csv`, `exploratory_binj_members.csv`;
* `preregistration.md` (its SHA-256 equals the frozen `3d8348af…` and the run's own record), the final-test verification addendum, `red_team.md`, `master_list.md`, `round0/literature.md` and `round0/inventory.md`.

**Computed:** nothing on any 2025–2026 match. I recomputed the family's Holm and BH on the price-base rows of the screen's output (no new fit). Ledger rows 34–35 record this checkpoint and close the ledger.

## Verdict: accurate after the listed corrections

**The central result is reported correctly.** Every figure below matches the output files to the printed precision:
* the primary b, −0.21 [−1.35, +0.93], a tie;
* the three effect sizes, which add exactly;
* the subsets, the fault-clean subset, the column arm and Polymarket;
* the screen table.

**So are the labels and limits.**
* "Not confirmed" is the pre-registered reading.
* README.md describes B-INJ as rust after a break, not impairment.
* The column arm is reported as a tie and rescues nothing.
* The recommendation (keep the current best; do not deploy B-INJ) follows from the readings.

**The corrections fall into six groups:**
1. **Omissions that change the impression.**
   * B-INJ's own out-of-sample gains in the screen were ties.
   * The owner's price lens would have made a second member eligible.
   * The per-tour and per-season b's are pre-registered but missing.
2. **Over-statements.** "The true interactions do not beat the model", "against the price", "did not carry", "worth less than about 0.1 mLL each", "strongly".
3. **Inferences without the "inferred" label**, mostly in the side findings.
4. **Direction keys missing** on three rows of the final table.
5. **"Hidden impairment" still labels B-INJ** in the header and table of `round3/screen.md`.
6. **Missing limitations.**

None of these changes the reading.

## 1. Verified as reported (observed)

| Claim | Evidence | Status |
|---|---|---|
| 116 ideas, 96 live, 20 closed, 91 master IDs | `master_list.md` counts | correct |
| 35 hypotheses, 34 after B4 | family, plan.md | correct |
| B-INJ: z₁ +3.51, z₂ +1.93, joint +3.99, Holm 0.002, BH 0.002 | `screen_results.csv` (Holm and BH 0.0016) | correct |
| without 2020–2021: joint +3.48 | ledger row 28, `red_team.md` | correct (exploratory) |
| screen table rows (B-VENUE to B-LEVER) | `screen_results.csv` | correct |
| G5: harm +0.044 [−0.157, +0.245], capture 0.39 | `g5/binj_g5.json` | correct |
| primary −0.21 [−1.35, +0.93], two-sided p 0.71 | `final_primary.json` (−0.206 [−1.346, +0.934], 0.710) | correct |
| F vs B₁₄ −0.27 [−0.64, +0.10]; B₁₄ vs B +0.06 [−0.07, +0.20]; F vs B −0.21 [−0.61, +0.20] | `final_primary.json`; the parts sum: −0.2685 + 0.0628 = −0.2057 | correct |
| men / women F vs B₁₄; 2025 / 2026; fault-clean; column arm; Polymarket F vs B and move slopes | `final_results.json` | correct |
| power 19–26% at 0.12–0.16 mLL; MDE about 0.57 | the pre-registration | correct |
| observed −0.27 "about two standard errors" below the expected gain | half-width 0.37 over 21 blocks: about 2.2–2.4 SE | correct |
| Pinnacle: +1.06 [+0.27, +1.85] and +1.19 [+0.47, +1.91] (2022–2024) | `descriptive_results.csv` (15,143 matches) | correct, but the discovery ties are left out (correction 6) |
| serve-dominance pricing: 43% / 34% / 36%, 39% damped | ledger row 7, rulings MAT-R3 | correct, with qualifiers (correction 5) |
| near relative scored on 2025–2026 and tied | inventory register | correct |

## 2. Corrections to README.md (exact)

Line numbers refer to the README as of 10:22 on 7 October.

**In short.**
1. **Line 23.** Replace "stronger with age, a retirement just before the break, or a protected ranking" with "stronger with age past 28, a retirement or a walkover given just before the break, or a protected ranking (PR or SR entry)".
2. **Lines 24–25.**
   * After "+1.93 on 2022–2024", add: "Its out-of-sample gains in the screen were ties: +0.19 [−0.03, +0.42] mLL (2014–2021, leave-one-season-out) and +0.02 [−0.31, +0.36] (2022–2024, forward). The claim rested on the coefficient test, as pre-registered."
   * Write "(exploratory)" after "+3.48".
3. **Line 27.** After "leaning worse", add: "Both intervals reach only to about the expected size: b's to +0.93, where 1 is the nudge as fitted and the shrunk expectation is about 0.86 (the Tweedie ratio 3.41/3.99), and the effect size's to +0.10 mLL, against an expected 0.12–0.16."
4. **Lines 28–31.**
   * Replace the heading "Observed: the true interactions do not beat the model" with "Observed: no other member passed the gates".
   * Replace "passed, against the price or against the model:" with "passed against the model (the gating base):".
   * Add a bullet: "The price lens, the owner's ranking, was reported but not gated. Under the family's own rules it would also have made **B-VENUE** (venue pace × the server's ace offence) bundle-eligible: joint z +2.72, q 0.075, against +2.50 and q 0.15 against the model (`screen_results.csv`, market rows)."
5. **Lines 32 and 114.**
   * Replace "the measured damped truth is 39%" (and "Day-to-day noise damps the true scaling to about 39%") with "the damped truth estimated from the day-noise split is about 39% (men, best of three; ruling MAT-R3)".
   * Mark "The price is about right." as **inferred**.
6. **Lines 34 and 110.**
   * After the 2022–2024 figures, add: "(2014–2021: +0.21 [−0.37, +0.78] against Pinnacle and +0.28 [−0.28, +0.83] against the average, both ties)".
   * Mark "an artefact of the average close that a sharp venue would not leave" as **inferred**.
7. **Lines 35 and 111.**
   * Delete "strongly".
   * Mark "the model is too steep for elite pairs" (and "the forecast is too steep for pairs of high combined Elo") as **inferred**.
   * Add: "one of 34 one-sided tests; a reversal was never a registered hypothesis".

**The team.**

8. **Line 44.** Replace "no published statistic-based feature or interaction beats a sharp close out of sample" with "found no published statistic-based feature or interaction that beats a sharp close out of sample". The scout reported an absence of evidence, not evidence of absence.

**The screen.**

9. **Line 75.**
   * Replace "The other 27 members tie." with: "The other 27 are not eligible. 21 single-coefficient members have a joint |z| below 1.96, and the four Wald blocks have joint p above 0.3. B-MOTIV reaches +2.27 but fails replication (z₂ +0.49). I-084 points against its declared direction (−2.99)."
   * After "+0.25 (2014–2021) and +0.09 (2022–2024) mLL", add: "(point estimates: the exploratory script computed no intervals)".

**From the screen to the test.**

10. **Line 82.**
    * Replace "never binds" with "almost never binds (it blocks 7 of 106,296 returns)".
    * Replace "not 'hidden impairment'" with "not 'hidden impairment' or an 'unplanned layoff'".

**The final test table** (lines 87–100).

11. **Give every row its own direction key.**
    * "B₁₄ against B: positive = B₁₄ better".
    * "Column arm against B: positive = the arm better".
    * "The price's move: the slope of logit P(30 min) − logit P(24 h) on b·x, positive = the price moved in the nudge's direction".
12. **The clean-opener reading.** It is "interval above 0 (descriptive)", not "tie".
13. **Intervals for the 2025 / 2026 row:** [−0.78, +0.33] / [−0.93, +0.26].
14. **Add pre-registered secondary 1, the per-subset b**, all ties:
    * men −0.33 [−2.04, +1.37];
    * women −0.09 [−1.62, +1.44];
    * 2025 −0.04 [−1.54, +1.47] (11 df);
    * 2026 −0.49 [−2.63, +1.66] (8 df);
    * fault-clean −0.04 [−1.19, +1.12].
15. **Add B₁₄ against B by season** (descriptive): 2025 +0.18 [+0.0002, +0.35], B₁₄ better by a hair; 2026 −0.11 [−0.30, +0.08], a tie.

**Reading** (lines 102–106).

16. **Line 105.** Replace "That is one descriptive secondary among several" with: "That is one of about 30 descriptive estimates. Two have intervals that exclude 0 (this move, and B₁₄ against B in 2025), about what chance alone gives. The direct comparison at that price ties: F against B, both fed the 24-hour price, +0.22 [−1.01, +1.46] on the clean openers and +0.06 [−0.59, +0.70] on all 2,648."
17. **Line 106.** Replace "that did not carry into 2025–2026" with "that was not confirmed on 2025–2026 (the effect size leaned worse)".

**Side findings, and what next.**

18. **Line 112.** Mark "a sign the model over-weights the rating it already holds" as **inferred**. Add: "One of six known nulls at p 0.011 has about a 6.6% chance under the global null."
19. **Line 118.** The paragraph claims more than the screen can show. Replace "Interactions are not where the remaining edge is, for these inputs … worth less than about 0.1 mLL each, below what 2025–2026 can show." with:

    > No interaction passed the gates. The screen's 80% MDE was about 0.12–0.19 mLL per member, depending on its weight, test and trait, so effects of that size would probably have been found, while smaller ones were beyond its reach. B-VENUE (joint z +2.50) and B-OVERREACT (+2.13) remain unresolved. TabPFN's near-additive adjustment is consistent with little interaction signal left beyond its 58 inputs; it does not prove it.

20. **Line 120.** After "+0.62", add: "(one descriptive estimate among about 30, uncorrected for multiplicity, so a hypothesis for a pre-registered test against the 24-hour price, not evidence)". Change "hints that … is information the early price lacks" to "is consistent with the early price lacking it".
21. **Line 121.** After "about 0.25 mLL by the end of 2027", add "(the critique's estimate, C1)".

**Limitations** (lines 127–131). Add:

22. **The screen's own gains for B-INJ were ties** (correction 2). The 2022–2024 forward gain was +0.02 mLL.
23. **Selection.** The nudge's b was fitted on the same 2014–2024 data that selected B-INJ. Tweedie's formula shrank its z from 3.99 to 3.41, about 15%.
24. **The construction.**
    * As built, B-INJ is not its registered mechanism: the field-norm condition almost never binds.
    * I-044 carries about 17% of the test's leverage and is null on its own.
    * I-045 is exposed to the first-serve fault.
    * 101 rows of 2026 lack I-043 (missing ages); they count as 0.
25. **The price lens was reported, not gated** (correction 4).
26. **Code changed after the freeze.** Two changes are logged only in ledger row 34: `tabpfn_tests`' one-tour fix, and R2-1, made after the verifier's last check. Neither touches the primary.
27. **The test seasons.**
    * 2026 is partial, ending in early October.
    * The primary has 21 four-week blocks, so t on 20 df.
    * The base's 2025–2026 seeds 0–2 are the rating race's fits, which that study had already scored. Only B-INJ and its column arm were new there.

## 3. Corrections to round3/screen.md

28. **Line 12.** Replace "B-INJ, hidden physical impairment" with "B-INJ (registered as hidden physical impairment; as measured, rust after a break of six weeks or more)".
29. **Line 16.** Replace the label "B-INJ hidden impairment" with "B-INJ rust after a break (registered: hidden impairment)".
30. **Line 27.** Replace "The other 24 members tie" with "The other 24 are not eligible". I-084's −2.99 is not a tie.
31. **Lines 28, 35, 46–47.** Mark as **inferred**:
    * "too steep, not too flat";
    * "a sign the model over-weights the rating it already holds";
    * "Pinnacle is sharper than the average";
    * "The model's edge is not just the average lagging Pinnacle".

    Also add the 6.6% chance for KN-TTTLOGIT (correction 18).
32. **The exploratory table.**
    * Replace the label "I-043 rust after an unplanned layoff" with "I-043 rust after a break of six weeks or more".
    * Note that its gains are point estimates without intervals.
33. **The reading, "What it means for the price".** Add: "in 2014–2024; not confirmed on 2025–2026 (README)".

## 4. The claim limits set at checkpoints 2 and 3

| Limit | In the report |
|---|---|
| The column arm never rescues a tie | kept: reported as a tie, −0.01 [−0.23, +0.21], and not used for B-INJ |
| The clean-opener move is one descriptive secondary | kept in the reading (line 105). In the next steps (line 120) it is used as a lead and needs the qualifier (corrections 16 and 20) |
| Nothing is "confirmed" | kept: "not confirmed" throughout; no other use of "confirm" |
| B-INJ is rust, not impairment or an unplanned layoff | kept in README.md. Not yet in `screen.md`'s header and table (corrections 28–29). "Unplanned" goes too (correction 10) |
| A positive result would support the rust reading only | moot (the primary tied) |

## 5. The ledger

* **Complete through the final run.** It runs from row 1 to row 35, numbered in order, with no duplicates.
* **Rows added at this checkpoint:**
  * **34** discloses the two post-freeze code changes that had no row: the `tabpfn_tests` one-tour fix (09:34), and R2-1 (10:20:53). R2-1 was made after the verifier's round-2 check of the 10:07 version and was not itself re-verified. It touches only the secondaries, after the primary is on disk, and every subset completed;
  * **35** records this checkpoint and **closes the ledger**.
* **What the run read.** The final test read 2025–2026 once (row 33). Every 2025–2026 number in the report comes from that run's two output files, and I found no other look at 2025–2026.

## 6. Process notes (no correction needed)

* **The run's integrity holds.**
  * `final_primary.json` records the pre-registration's SHA-256, `3d8348af…`, which equals the file on disk.
  * The primary was written before any secondary.
  * The run passed every input and code gate, or it would have refused.
* **The README was written 98 seconds after the run** (10:22:52), presumably from a prepared draft. Its 2025–2026 numbers all match the outputs. The corrections above are about framing, not figures.
