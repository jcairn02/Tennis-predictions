# Pre-registration, addition 4c: erratum 1 to the owner's file (the share arms are reported, not selected)

Written by the lead on 10 October 2026 at about 03:58 UTC. The exact time is recorded in `status.log` when the file is
hashed. The file's own SHA-256 is in `preregistration_addition_4c.sha256`.

**When it was written.** No score of any arm of this run existed. No `scores.csv` and no `selection*.json` was in the
study's folders (checked at 03:57 UTC). SYS-family arms had no fits.

**Earlier files, unchanged:**

| File | SHA-256 |
|---|---|
| `preregistration.md` | `cc65bcd5…` |
| Addition 1 | `c718e6d0…` |
| Addition 2 | `3f536796…` |
| Addition 3 | `f2063433…` |
| Addition 4 | `754e055c…` |
| Addition 4b | `f4e2e405…` |

## The source

Erratum 1 to the owner's file: `data/studies/lower_level_evidence/system/owner_decision_2026-10-09_erratum_1.md`,
sha256 `edb9b377e76e44465593bec8b18ae6a32477b9f6ba09c8d9f0958a1141d7b876`. Session `tennis-predictions-cc` wrote it at
03:54 UTC, after an independent review. Like the owner's file, it governs where it differs from additions 4 and 4b.

## The change to the decision layer

**The dev challengers** are SYS_w0, SYS_w50, SYS_w100, SEP_ALL and SYS_NOCLASS.

**R_S2 and SYS_S2 are reported, not selected.**
* They are still fitted, scored and reported against REF and against SYS, as registered.
* Their readings are lead evidence for the feature pool, with their seasons recorded: 2020–2024 on dev, 2025–2026 on
  the holdout.
* The reason: the two share inputs are a new feature found on 2020–2024. Under the owner's decision of 9 October
  (point 6), a new feature goes to the pool, and a selection round decides. Selecting one of these arms on its
  discovery seasons would contradict that.

**The winner's-luck figure** stays SE × 1.35, with the number of challengers (five) recorded beside it. The registered
rules' selection is still computed, with its seven challengers, for the record.

**The harm tolerance of 0.10 mLL** is the other session's choice, in the form of the owner's Roland Garros rule. The
owner may set another. It may not be loosened once any score it governs exists.

## The code

| File | SHA-256 |
|---|---|
| `src/eda/lower_level_evidence/system_decide.py` (changed: the challenger list only) | 829560436830ee2543c7be88e25f31af53f38ca1605cf3d3c21c43dfd0948870 |
| `src/eda/lower_level_evidence/system_pairs.py` (unchanged since 4b) | a486aed9aa28cab1ef36dc3ae50be4d4cffa5a61a274606445039f33a5f4d898 |
| `src/eda/lower_level_evidence/system_fits.py` (unchanged since 3) | e8831b1febd0e7987d20c0070335de6c1d93a8d628f463fa2c261f94234c5362 |

Role D's tests (48 pass) include both cases:
* If R_S2 or SYS_S2 reads "better" than SYS, SYS stays selected.
* If a remaining challenger reads "better", it is selected.
