# The owner's decision of 9 October 2026, applied to this study's decision rules

Written 10 October 2026, 02:55–03:15 UTC (9 Oct, 19:55 local), by session `tennis-predictions-cc`, not the lead, at the
owner's instruction: "I accept your adoptation logic, implement it" (9 Oct 2026). The decision is
[`docs/decisions/2026-10-09-adoption-by-change-class.md`](../../../../docs/decisions/2026-10-09-adoption-by-change-class.md).
This file has its own SHA-256 (`owner_decision_2026-10-09.sha256`). It edits none of the lead's files.

## When it was written

* **No model-level score of any arm of this run existed.**
  * SEP_ALL and REF_noITF had fits and compare.py's part 1 (the input check); their folders hold no score file.
  * SYS_w0 was being built. No other SYS-family arm had fits, no NEW arm existed, and `holdout_unlock.json` did not
    exist.
* **The writer read no score, no part-1 output and no line of `status.log`.** The state above comes from file names and
  times only.
* **The lead's files are unchanged** (SHA-256 at writing, equal to the recorded ones):

| File | SHA-256 |
|---|---|
| `preregistration.md` | cc65bcd5eb402326814291156d30c8d7ff4318d7344dd1f636d174bfd6068ae9 |
| `preregistration_addition_1.md` | c718e6d0696448c7f2a5849cd6e5d2f4443f5e29173b71900f782048a0d48b8a |
| `preregistration_addition_2.md` | 3f5367969b39003aff28e9e5d29fa35027cf9362d7a4cc321c4eef7249e7a27b |
| `preregistration_addition_3.md` | f206343347895152cf1ddb70bc0229e6c3d1831d4545bf4ee91d5b52225a27ca |

## What changes, and what does not

* **Changed: only the rules that turn readings into a selection or a recommendation.** Sections 2–5 below replace them.
* **Unchanged: everything that measures.** The arms, builds, gates, scorer, intervals and labels; the holdout's single
  opening and its conditions; addition 2's eight Holm readings; addition 3's frozen internals. Every registered
  reading is still computed and reported in full.

## Why

* **The study's own power note** (addition 3, section 6) says the registered rules cannot do their job:
  * resolution about 0.08 mLL for men on dev and 0.12 on the holdout;
  * "an 'unresolved' holdout primary is the expected outcome even if the system helps a little";
  * the selection "switches on noise in 19–52% of worlds where no challenger truly differs".
* **SYS's route already rests on resolved statistic-level evidence**
  ([B](../../../../docs/studies/lower_level_evidence/system/B_relationship.md), "In short"; milli-log-likelihood per
  unit, + = the frozen method better):
  * against pooling as equivalent: men +0.409 [+0.344, +0.474], women +0.190 [+0.152, +0.227];
  * against main-tour-only: +0.344 (men) and +0.256 (women).
* **Under the decision:**
  * SYS repairs how data already in the model enters its inputs;
  * C0_now's additions are an expansion.

  For both, the statistic-level evidence decides the route, and the model-level readings are a harm check with a
  stated tolerance. A reading that cannot see the plausible effect does not decide.

## 1. The harm rule

* **A reading shows harm** when the named model is worse by more than **0.10 mLL** with its whole 95% interval below 0.
  This is the form of the owner's Roland Garros rule
  ([decision](../../../../docs/decisions/2026-10-09-roland-garros-box-scores.md)).
* **An input flag shows harm** only when F's hashed expected unevenness, read against the tour-season's dose (SPEC
  section 8), does not explain it.

## 2. Selection on dev (replaces step 1 of the selection rule)

* **SYS is selected,** unless a challenger reads **"better" than SYS for men on dev** (its 95% interval clears 0).
  * Registered: P(better than SYS) ≥ 0.90.
  * The challengers are unchanged.
* If more than one challenger reads better, the one with the largest point gain is selected. Its estimate is also
  reported after the winner's luck of seven challengers (SE × 1.35).

## 3. REF instead of the selected arm (replaces step 2)

* **REF is selected (no change) only if the selected arm shows harm against REF for men on dev** (section 1).
* Registered: P(better than REF) < 0.50, the sign of a reading that cannot see the effect.

## 4. The recommendation (replaces "The recommendation")

* **Recommend SELECTED for men unless one of these shows harm:**
  * the holdout primary (section 1);
  * any of addition 2's eight Holm-corrected holdout readings reads "worse". Holm stays as the guard against a harm
    confined to a subgroup.
* **If harm shows,** recommend REF and report what drove it.
* **No edge credit.** A SYS adopted this way adds nothing to the edge used for stakes. That edge comes only from
  untouched matches at the venue's price (the adoption framework's section 6).

## 5. The rule test (replaces addition 1's "Interpretation")

* **The question is the owner's of 8 October:** does the data, entering by the route its statistic-level evidence
  supports, harm the model? In the owner's words, "if it harms results we will want to make some modifications, Either
  to ignore data, lower its weight, or find a way to mathematically change and integrate it so its useful"
  ([decision](../../../../docs/decisions/2026-10-08-current-best-model.md)).
* **The supported route is the system's treatment (NEW_SYS_BOTH):**
  * role B's translation and weights for every new box score;
  * its w_results for every new result;
  * w = 0 wherever B's fits or the pre-registration set it (ITF and ITFQ box scores until P7's training-period
    parameters exist).
* **C0_now's additions are recommended for entry by that route, for every tour whose treatment is the system's,
  unless NEW_SYS_BOTH against SYS_BOTH shows harm for that tour** (section 1):
  * on dev, for the additions of 2018–2024;
  * on the holdout, for those of 2025–2026.
* **If REF is recommended for men** (section 4), the men's results still have a supported route: B's w_results, as in
  RES_ONLY. The lead then registers RES_ONLY on C0_now as the next candidate, rather than keeping the data out.
* **Women:** their treatment waits for P7, as registered. Two things are decided with that treatment, by the same
  rule:
  * women's part of this recommendation;
  * the 2025–26 ITF box scores already in the reference (REF_noITF against REF).

  These readings are its harm evidence.
* **NEW_ASIS and NEW_ASIS_PRE are still read and reported.** They show what the rule of 8 October protects against.
  They do not decide entry: pooled as equivalent, opponent-dependent lower-level statistics predict worse than ignoring
  them ([lower-level evidence](../../../../docs/studies/lower_level_evidence/README.md), section 3.2).
* **Struck: "The rule costs nothing to keep, so the default stays."** Keeping data out has costs, and the report names
  them:
  * since June 2026, the live history lacks lower levels that the training seasons hold (same report, section 1.4,
    point 3);
  * lower-level results carry information: dropping them makes a plain Elo 6–7 mLL worse (section 3.4).

## 6. The rules' rates

The decision asks every decision rule to state two rates: how often it adopts a change that works, and how often one
that harms.
* **Source:** computed from the study's own standard errors, with no data read: dev 0.035, holdout 0.063, pooled
  0.034, and the eight Holm readings 0.065–0.20 (approximated from D's range).
* **Files:** `src/eda/adoption_framework/level_evidence_rules.py`, output
  `data/studies/adoption_framework/level_evidence_rules.out`.

**P(the rule recommends SYS), men** (true gain in mLL, + = SYS better than REF):

| True gain | −0.20 | −0.10 | −0.05 | 0 | +0.04 | +0.083 (the first run's FP) | +0.12 |
|---|---|---|---|---|---|---|---|
| Registered rules | 0.00 | 0.00 | 0.00 | 0.02 | 0.17 | 0.56 | 0.83 |
| Amended (sections 3–4) | 0.00 | 0.21 | 0.72 | 0.95 | 0.99 | 1.00 | 1.00 |

**P(switching away from SYS on dev)** (7 challengers, SE 0.035; ρ = how much their readings' noise overlaps):

| World | ρ = 0 / 0.5 / 0.9: registered (P ≥ 0.90) | Amended ("better") |
|---|---|---|
| No challenger truly differs | 0.52 / 0.35 / 0.19 | 0.16 / 0.11 / 0.06 |
| One challenger truly +0.10 | 0.97 / 0.94 / 0.94 | 0.84 / 0.82 / 0.82 |

**The new data's harm check** (NEW_SYS_BOTH against SYS_BOTH, men, dev, SE about 0.03). It flags harm with
probability:
* 0.000 at a true 0;
* 0.05 at −0.05;
* 0.50 at −0.10;
* 0.95 at −0.15.

**Reading the rates** (*Inferred*).
* **The registered rules** adopt a SYS worth the first run's +0.083 about half the time, and one worth +0.04 one time in
  six.
* **The amended rules:**
  * adopt a SYS that does no harm 95% of the time, and one that helps nearly always;
  * reject a 0.2 harm every time and a 0.1 harm four times in five;
  * accept a 0.05 harm about 70% of the time.
* **That trade is the decision's.** The statistic-level evidence makes a model-level harm unlikely, and an adoption made
  on a prior earns no edge credit.

## 7. For the lead

* **The lead's next addition may restate these rules in its own words.** It may not loosen section 1 once any score
  these rules govern exists.
* **If a rule here cannot be applied as written to an arm as built,** record the reading closest to its intent before
  scoring, and say why.
