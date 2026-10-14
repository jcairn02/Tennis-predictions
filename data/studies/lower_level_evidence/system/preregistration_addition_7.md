# Pre-registration, addition 7: the late arms (rulings and code before their first reading)

Written by the lead on 10 October 2026, about 14:02 UTC. The exact time is recorded in `status.log` when the file is
hashed; the file's own SHA-256 is in `preregistration_addition_7.sha256`.

**When it was written.** The main holdout run had been read once, at 08:37 UTC. No reading of any arm named here existed:
* no supplementary output (`results/supplementary/` was empty or absent);
* no score for NEW_ASIS, NEW_ASIS_PRE, NEW_SYS_BOTH, SYS_BOTH or SYS_BOTH_ITFASIS;
* NEW_ASIS and NEW_ASIS_PRE were held, unfitted, by role D's frame check.

`holdout_unlock.json` stands as written at 08:36:26 UTC. This addition does not touch the readings of record already made.

## 1. NEW_SYS_BOTH's opponent strength

**The amendment.** This amends addition 3, section 4, before NEW_SYS_BOTH has any reading. NEW_SYS_BOTH's opponent
strength now comes from two sources:
* **The reference's own matches (873,437):** the reference's pre-match Elo (`strength_elo.parquet`), as in SYS_BOTH.
* **The 298,008 matches C0_now adds:** the plain Elo of NEW_ASIS's build (C0_now, the reference's K, no w_results), re-centred onto the reference's scale by tour and season. This is role C1's option (c), as C1 specifies it in `C_layer.md`.

**Why** (Observed, C1):
* The plain Elo on C0_now shifts the rating scale. Women move by about +75 to +92 Elo in every season; men rise to about +85 by 2024.
* Role B's γ term is anchored to `strength_ref` on the reference's scale. Under addition 3's option (a), every translation would shift by up to γ × 0.9.
* The comparison NEW_SYS_BOTH against SYS_BOTH would then measure that rescaling, not the data.
* Under option (c), the reference's matches carry exactly SYS_BOTH's strengths, so the pair differs by the new data alone.

**The build already made with option (a)** is kept on disk, unread, as `NEW_SYS_BOTH` under C1's records. It is renamed if C1's tools need the name. It is not scored.

## 2. Rulings

**SYS_BOTH and SYS_BOTH_ITFASIS: READY.** One women's G3 cell, `formdef_df`, is recorded as an exception.
* That input is an OPP-class defence statistic with weak opponent dependence: women's γ is −0.025.
* The arm moves it by about 6% of an SD. Its correlation with the share gap is about 0, where a small positive one was expected.
* Every other cell passes, and SYS_BOTH's 22 IOS inputs equal role C2's `SYS_BOTH_cap` bit for bit, so there is no sign error.
* Any other G3 failure still holds an arm.

**The NEW arms' `debut_season`.** It differs from the reference on 10 of 67,226 matches (3 men's, 7 women's). C0_now adds earlier matches that end some players' debuts, so the difference is legitimate.
* Role D's frame check waives it for NEW_ASIS, NEW_ASIS_PRE and NEW_SYS_BOTH.
* Scoring takes the match facts from the reference frame, as compare.py does on the matches both frames hold.

**Readings of record.** The first reading of each of these arms is its reading of record (addition 6, section 2):
* SYS_ITFASIS (holdout, and dev where its inputs before 2025 differ from SYS's);
* SYS_BOTH and SYS_BOTH_ITFASIS;
* NEW_ASIS, NEW_ASIS_PRE and NEW_SYS_BOTH;
* RES_ONLY's dev reading.

## 3. Code changed since addition 5 (role C1; build and gate code only)

| File | SHA-256 |
|---|---|
| `src/eda/lower_level_evidence/system_arms.py` | 793a0fa1d1535c66a950b1138816ff7cfb26a209492811eb99a13a2423f68a32 |
| `src/eda/lower_level_evidence/system_gates.py` | 29b909cdd0eed6d62e3c22be8a124ec82172b2d81a3f6c49cf384449cf6eac10 |
| `src/eda/lower_level_evidence/system_new_arms.py` (new: the NEW arms' builds) | f931960c3a71e3d4fa5d6a96918bbe9fd29e6e204b9f91704e58d0b5ec4cea65 |
| `src/eda/lower_level_evidence/level_pins.py` (new: the NEW arms' constant pins) | 381c8596a5a2f339c2149b4a8557b453dc881a593ecafb7d338c2d5ab3db4a5f |

**Unchanged:**
* `level_layer.py` (26e21291…), `level_layer_ios.py` (3fa5f69e…) and `system_sandbox.py` (ebf4520a…);
* the scorer and decision code: `system_pairs.py`, `system_decide.py`, `system_supplementary.py` and `system_fits.py`.

**What the gate change does.** G2's date rule now uses the match clock as well as event dates. REF_noITF's first G2 run flagged 7 late-round women's matches that the layer had reached legitimately on the clock; the rerun passed.

## 4. Also recorded for the owner

Another session's uncommitted change to `src/eda/tabpfn_thinking/build_frame.py` fills women's `indoor` input from the WTA calendar. It has done so since 10 Oct, 01:14 UTC. A template build made with it would differ from the frozen reference on that input.
* This run's arms are built on the validated code snapshot (`arms/validated_src/`), so the change does not reach them.
