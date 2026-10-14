# Pre-registration, addition 3: checkpoint 1, SYS's internals frozen

Written by the lead on 10 October 2026 at about 01:50 UTC. The exact time is in `status.log` at hashing.

When it was written:
* The red team's checkpoint-1 verdict was in: pass with conditions (`E_red_team.md`, CP1 and CP1b).
* No SYS-family arm had been built.
* No model-level score of any arm of this run had been read.

This file has its own SHA-256 (`preregistration_addition_3.sha256`). The earlier files are unchanged:

| File | SHA-256 | Note |
|---|---|---|
| `preregistration.md` | `cc65bcd5…` | |
| `preregistration_addition_1.md` | `c718e6d0…` | Its text says "about 20:45 UTC"; it was hashed at 20:51:52 UTC |
| `preregistration_addition_2.md` | `3f536796…` | |

## 1. The files that define SYS

Full SHA-256, as on disk at hashing:

| File | SHA-256 |
|---|---|
| `classes/classes.csv` (role A) | 58e7862273bfaf8bfbe6283c72b54e80f219ff36c0f83df795076d52ae940c26 |
| `classes/thresholds.json` | d8eb62d2c499b5571427cf00dce655a46aaf1c2992a60959a9439f586052861f |
| `classes/strength_elo.parquet` | 4fa9a573e7d0fbc34ab95f5f6c5efc97b835471a0f676bb5f14c182321c34d0d |
| `src/eda/lower_level_evidence/classify.py` | 5eecfaf34fbaa573459af5629e09490ba55decbd54912ada219a98578a2fbb4d |
| `relationship/params.parquet` (role B; 3,808 rows; the 2025–26 rows produced mechanically, unread) | 4c559abd356f7c9f0f53c958c5d8293ae55d0cdfa62c4e9da689c94c91a801fb |
| `relationship/params_noclass.parquet` (SYS_NOCLASS) | 4018747db6cbbd01bfb5591bb32a9f57ba47f1df853eb9d4d9d455543a1a4e94 |
| `relationship/method_freeze.json` | 5a60089732cb359b564ae8d1c9d093f059e42e7ab2e8d39ede3a41d863917461 |
| `src/eda/lower_level_evidence/relationship.py` | 06a85f00a2051a53063bdc706d06d360e80e2bd11bf2532aa2abb600df982575 |
| `src/eda/lower_level_evidence/level_layer.py` (role C1; with the cap) | 26e21291822f42e4c9e7771f518149d1cb85116bdeb5196285fa22eeca37411f |
| `src/eda/lower_level_evidence/level_layer_ios.py` (role C2; with the pooled form-(b) fix of 01:00 UTC) | 3fa5f69e592118fc204809ce0ec6afa627e5b979af3e33752e91e89f154c05c3 |
| `src/eda/lower_level_evidence/system_sandbox.py` | ebf4520a9a4a26309c3da89bd0b3ba5b8a731548b09a2dd46d891584500b264b |
| `src/eda/lower_level_evidence/system_gates.py` | 0adbf1a5a9300645f550352e46cdb33ea470900593b60a863c4e27b979f3e4a8 |
| `src/eda/lower_level_evidence/system_arms.py` | 3e3b9b6b8f67d33c262292067b3890fa8fc7b48a490181b4395a2b8eb1322cdf |
| `src/eda/lower_level_evidence/system_pairs.py` (role D; the scorer) | f38f9205123b99bb2a73636ec8cd443852160dd96be901ad91eab22c4efdb2a1 |
| `src/eda/lower_level_evidence/system_fits.py` | e8831b1febd0e7987d20c0070335de6c1d93a8d628f463fa2c261f94234c5362 |

**Changing a file after this point.**
* A change to the classes, parameters, estimator, layer or scorer needs a new dated addition before any score it touches. Role D's guard refuses otherwise.
* A change to the build code that leaves every SYS-family arm's inputs unchanged is recorded in a later addition. Examples: support for lane 0 and the NEW arms.

## 2. What SYS is

**The relationship: role B's method F4, both tours.**
* **The translation.**
  * A lower-level row is translated by γ · (the opponent's pre-match Elo − the main-tour reference) + δ.
  * γ is role A's opponent dependence per statistic and tour.
  * δ applies only at the levels A's `delta_levels` allows. It is a forecasting offset fitted walk-forward, not a measured "conditions" effect: the red team found it 2–3 times the same-player residual.
* **The exchange rate.** w is fitted per statistic, tour and level, with shrinkage across statistics; the recency half-life is chosen per season.
* **The prior is the pool.** No newcomer prior, by B's rule logged before the comparison.
* **One-step forms.** Each norm row is translated as an observation about its owner, with the strength of the owner's opponent at that row and the mirror statistic's own parameters. The match's own value takes δ only.

**The weights.**
* **Capped at 1.0.** Fitted w, w_joint and w_results above 1 are set to 1 (`fitted_cap = fitted_cap_results = 1`). A lower-level observation never counts for more than a main-tour one.
  * The red team traced B's values above 1 (up to 2.82) to the pool prior.
  * The cap is the owner's premise: informative, never more than equivalent.
  * The uniform dose arms use 0, 0.5 and 1.
* **The results channel.** w_results is B's fitted value at every lower level, including ITF and ITFQ, capped at 1.
  * The pre-registration's "w_results fitted" governs.
  * SPEC §3's sentence "ITF results stay in Elo as today" meant only that the box-score exclusion removes no results.
  * A discounted result advances Elo's rated-match count by w_results.

**The joint solves** (`iosO_*`, `iosD_*`, `ios_points_short`; the products follow).
* The level term is estimated inside each snapshot's solve (form b), only at the levels in `delta_levels`.
* Each observation's weight is B's `w_joint`, capped.
* The prior is the pool.

**The conventions.**
* A row is translated with its own season's parameters. Rows of 2010–2012 use 2013's (`params_season_floor` 2013).
* Cells with no parameters stay as the reference has them (`missing_params` 'untouched'). This covers women's hold, brk, bp_faced_pg and def_bp_faced_pg in 2013–15, which touch SYS_BOTH only.
* Men's Challenger-qualifying rows of 2016–17 get w = 0, because the level is fitted only from 2018.
* ITF and ITFQ box rows get w = 0 (`itf_box` exclude), except in SYS_ITFASIS and SYS_BOTH_ITFASIS.
* The opponent strength is the reference build's pre-match Elo (`strength_elo.parquet`) in every arm built on the reference's Stage 0.

## 3. New arm: RES_ONLY

**The arm.** The reference plus role B's fitted w_results (capped at 1) at every lower level, in the Elo family only. No box-score input changes.

**The pairs.** Read on dev and the holdout, for men and women. Neither enters the selection.
* RES_ONLY against REF: the Elo weighting alone.
* SYS against RES_ONLY: the box-score layer beyond the Elo weighting.

**The label.** "SELECTED against REF_noITF" reads as "everything the system changes except the ITF box-score exclusion", Elo weights included. It is not "the Challenger and qualifying part".

## 4. The rule test's arms (addition 1), as built

**The candidate Stage 0s** (role F):
* `system/stage0/C0_now`: 298,008 new lower-level matches and 1,644 box completions.
* `system/stage0/C0_pre`: the additions dated up to 2024-12-29 only.
* F's expected unevenness was written and hashed before any NEW arm existed: `expected_unevenness.txt`, sha256 `edcab8a7…`. Its file time is 00:36 UTC; its text says about 00:45.
* Before any NEW arm is built, the 2 windows the red team flagged are widened: atp 2026-9552 SF, and wta 2025 ITF USA-21 R16.

**How the NEW arms are built.**
* **NEW_ASIS:** the template recipe on C0_now, with every tuned constant pinned to the reference's: Stage 1's Elo K, the offset Elo's kd, Stage 3, Stage B, and `IOS_CONSTANTS_VERSION=2026-10-08_reference`. The data is then the only difference.
* **NEW_SYS_BOTH:** the SYS_BOTH config on C0_now, with three choices:
  * role B's frozen parameters;
  * the opponent strength from that build's own pre-match Elo, under the reference's K;
  * the ITF box rows excluded, as in SYS. Their translation is not fitted on training seasons.
* **NEW_ASIS_PRE** (registered here; optional): the template recipe on C0_pre, with the same pinning.

**The pairs.** Read on dev and the holdout, for both tours and each tour:
* NEW_ASIS_PRE against REF: the historical backfill alone;
* NEW_ASIS against NEW_ASIS_PRE: the 2025–26 additions, mostly the fill of the reference's publication lag.

## 5. Order of work

* **SYS-family arms may be built now,** on the frozen code, in parallel with C1's IDENTITY_ALL build.
* **No SYS-family arm is marked READY or fitted until IDENTITY_ALL passes G1:** all 58 inputs exact on all 67,226 matches, with both patches and the frozen modules above.
* If IDENTITY_ALL fails, every SYS-family build is discarded and the fix is recorded in a new addition.

## 6. Interpretation, written before any score (the red team's power analysis)

* **Resolution.** About 0.08 mLL for men on dev, and about 0.12 mLL for men on the holdout. With 4 seeds, smaller true effects usually read "unresolved".
* **An "unresolved" holdout primary is the expected outcome even if the system helps a little.** If SYS's true gain equals the first run's FP (+0.083 mLL, men), the holdout primary reads "better" only about 26% of the time.
* **The dose arms cannot measure the exchange rate.** SYS against SYS_w100, SYS_w50 and SYS_NOCLASS is expected to read "unresolved". Role B's statistic-level dose curve is the evidence for w.
* **A dev switch away from SYS is weak evidence.** The selection rule switches on noise in 19–52% of worlds where no challenger truly differs.
* **SYS beating SYS_PLACEBO does not by itself show that SYS helps.** The first run's placebo cost about 0.11 mLL on its own.
