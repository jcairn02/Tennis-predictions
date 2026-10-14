# Pre-registration, addition 5: build code, gate code and the supplementary scorer, before the holdout opens

Written by the lead on 10 October 2026 at about 08:35 UTC. The exact time is in `status.log` at hashing. Own SHA-256:
`preregistration_addition_5.sha256`.

**When this was written.**
* The dev readings of the six selection arms and the selection existed (`selection.json` `b5fbec82…`, 08:2x UTC).
* No holdout reading existed. `holdout_unlock.json` did not exist.
* The red team's CP2 audit was in progress.

**Earlier files, unchanged:**

| File | SHA-256 |
|---|---|
| `preregistration.md` | `cc65bcd5…` |
| Addition 1 | `c718e6d0…` |
| Addition 2 | `3f536796…` |
| Addition 3 | `f2063433…` |
| Addition 4 | `754e055c…` |
| Addition 4b | `f4e2e405…` |
| Addition 4c | `7c7ff69a…` |

## 1. The supplementary scorer (role D)

Some arms are fitted after the main runs, so they are read in a separate mode:
* RES_ONLY and SYS_BOTH, on dev and the holdout;
* SYS_ITFASIS and SYS_BOTH_ITFASIS, on the holdout, and on dev wherever their inputs before 2025 differ from SYS's or SYS_BOTH's (addition 2, section 2);
* NEW_ASIS, NEW_SYS_BOTH and NEW_ASIS_PRE, on dev and the holdout, with addition 1's pairs and addition 4's rule-test verdict.

What the supplementary scorer does and does not do:
* It refuses the six selection arms.
* It never reads `selection.json` for a decision, and never writes it.
* It never recomputes the primary or the selection.
* It writes only to `results/supplementary/`.
* It may run after the unlock.
* The main holdout run is unchanged and opens once.

| File | SHA-256 |
|---|---|
| `src/eda/lower_level_evidence/system_supplementary.py` (new) | 5dcefc1e6fa2135a4299de270ffbdf14b9d4e0b5aec1f7e34a00036bd3b97045 |
| `system_pairs.py` (unchanged since 4b) | a486aed9aa28cab1ef36dc3ae50be4d4cffa5a61a274606445039f33a5f4d898 |
| `system_decide.py` (unchanged since 4c) | 829560436830ee2543c7be88e25f31af53f38ca1605cf3d3c21c43dfd0948870 |
| `system_fits.py` (unchanged since 3) | e8831b1febd0e7987d20c0070335de6c1d93a8d628f463fa2c261f94234c5362 |

## 2. Build and gate code changed since addition 3 (role C1)

Neither change alters what any arm's inputs are meant to be. Every arm's G1 and G2 still compare it with the reference.

| File | SHA-256 at addition 3 | Now | Why |
|---|---|---|---|
| `system_gates.py` | `0adbf1a5…` | f4cb45c6a0a32d33c7e8a61a9f7cbef82baf5ea80cc9496c3a1c804c5e074dc7 | See below |
| `system_arms.py` | `3e3b9b6b…` | 64457222bc2e283c41a5ca3746891981b033743d4731ba01eefac181de8f78a2 | Every build or resume first restores the sandbox's chain code to the validated snapshot, and refuses if a patched builder differs |
| `system_sandbox.py` | `ebf4520a…` | ebf4520a… (unchanged) | |
| `level_layer.py` | `26e21291…` | unchanged | |
| `level_layer_ios.py` | `3fa5f69e…` | unchanged | |

**The `system_gates.py` changes:**
* The identity arms' C2 file fingerprint is no longer compared, because it is the reference's own.
* The lead's G3 rule for ENV-class inputs that take δ only (10 Oct, about 05:05 UTC). Each such input is judged by its by-season cells:
  * it passes where those cells follow the sign of B's fitted δ;
  * it is not required where the weighted δ shift stays below 0.05;
  * any other G3 failure holds the arm.

**The validated code snapshot.** `arms/validated_src/` holds the chain's code exactly as IDENTITY_ALL ran it, when G1 validated it (MANIFEST sha256 `1e95dbfe176efbc750a79c268059465378a5784b5e384838375c41809e17b5e5`). It exists because of an incident:
* At 01:14 UTC another session's uncommitted change made `src/eda/tabpfn_thinking/build_frame.py` fill women's `indoor`.
* That change reached the one sandbox set up after it (`tnr_sys5`).
* G2 caught it on SYS_w100, and the arm was rebuilt on the snapshot.
* The arms built earlier ran code equal to the snapshot.

## 3. Rulings recorded

* **Solver rounding.** Arms whose only difference before a date is solver rounding below 1e-12 are fitted in full, not copied: REF_noITF, and the ITFASIS arms if it applies. The lead ruled this at 03:05 UTC.
* **The selection set's gates.** G1 (IDENTITY_ALL) passes on the frozen modules. G4 (dose) passes. Each READY arm passes G2, G3 (with the ENV rule), the constants check and the builders' probes.
