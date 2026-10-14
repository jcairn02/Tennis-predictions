# Pre-registration, addition 4b: the code that implements addition 4

Written by the lead on 10 October 2026, about 03:09 UTC. The exact time is in `status.log` at hashing. Its own SHA-256 is in `preregistration_addition_4b.sha256`.

**When it was written.** No score of any arm of this run existed. The results folder held no score file, no `selection.json` and no reading. SEP_ALL and REF_noITF had fits and input checks only.

**The earlier files are unchanged:**

| File | SHA-256 (first 8) |
|---|---|
| `preregistration.md` | `cc65bcd5…` |
| addition 1 | `c718e6d0…` |
| addition 2 | `3f536796…` |
| addition 3 | `f2063433…` |
| addition 4 | `754e055c…` |

## Role D's implementation of the owner's decision layer (addition 4)

The full SHA-256 of each file, as on disk at hashing:

| File | SHA-256 | What it is |
|---|---|---|
| `src/eda/lower_level_evidence/system_decide.py` | 34ac7071a638182698507046bf764f410243f99ec2a919b23d7dc015134bdcf7 | NEW. Applies sections 1–5 of the owner's file to the scorer's saved readings and measures nothing. Writes `selection.json` with the decision layer's marker, with the registered rules' outcome beside every decision |
| `src/eda/lower_level_evidence/system_pairs.py` | a486aed9aa28cab1ef36dc3ae50be4d4cffa5a61a274606445039f33a5f4d898 | CHANGED in its non-measuring parts only, listed below. The harness re-run still reproduces the first run's FP readings exactly |
| `src/eda/lower_level_evidence/system_fits.py` | e8831b1febd0e7987d20c0070335de6c1d93a8d628f463fa2c261f94234c5362 | unchanged since addition 3 |

**The changes to `system_pairs.py`:**
* its dev run writes the registered selection to `selection_registered.json`;
* the holdout run takes SELECTED only from the decision layer's `selection.json`;
* its guard accepts each required hash from any verified addition, and adds `system_decide.py` to the frozen list.

**Two notes on how D applies the layer:**
* **Input flags.** Whether an input flag is harm (owner's file, section 1) is a reading: the flag judged against F's hashed expected unevenness and the dose. `system_decide.py` lists the flags, and D judges them in its report, as the owner's file (section 7) allows.
* **Arms whose only difference before a date is solver rounding below 1e-12** (REF_noITF, and possibly SYS_ITFASIS and SYS_BOTH_ITFASIS) are fitted in full rather than copied, under the lead's ruling of 03:05 UTC.

## Order of work (unchanged)

1. Dev scoring runs once the selection set has its 2019–2024 fits.
2. `system_decide.py` writes the selection.
3. The red team audits (CP2).
4. The lead writes `holdout_unlock.json`, holding the hashes of every pre-registration file (including this one) and of `selection.json`.
5. The holdout is read once.
