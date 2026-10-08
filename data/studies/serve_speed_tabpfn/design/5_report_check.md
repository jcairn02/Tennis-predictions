# R5: the report checked against the outputs (agent 4, auditor)

7 October 2026, after the one scoring run. Pre-registration step 7.

**What was checked.** `docs/studies/serve_speed_tabpfn/README.md`, against:
* `results.json` and `results.csv`;
* `check.json`;
* `features/speed_meta.json`;
* `checks/repro_check.json`;
* `preregistration.md`;
* the design files it cites.

**Precondition.** The pre-registration's SHA-256 is recomputed as `19b5ac0d…8b0dde`. It equals `preregistration.sha256` and the README.

**Rules followed.**
* No result was re-run (`--run` refuses anyway).
* `preregistration.md`, the code and `results.*` are untouched.
* One script is new: `auditor_r5_gate_sd.py`. It prints a feature SD on rows of seasons ≤ 2023; see Looks.

## Verdict: **faithful after 18 minimal edits; nothing changes a result or the decision.**

**The headline is right.**
* Every number derived from the results matches `results.json` and `results.csv`, to the stated rounding:
  * P2 +0.07 [−0.05, +0.18] mLL, a tie;
  * S0–S14;
  * the decision (row 3);
  * the multiplicity count.
* Directions are present.
* "Tie" appears exactly where an interval spans 0.
* The nudge (S9) is a pre-registered secondary throughout.

**What was wrong:**
* one unit error, in the gate effects;
* two overclaims:
  * "predicts next-match speed better than the window", which rests on the biased R1 target;
  * "the leaky controls fired every time", which holds for the red team's probes, not the builder's;
* missing qualifiers on blindness, the capture's uncertainty and the market;
* a paraphrase where the decision-table text had to be quoted.

## 1. Changes made to the README

Every change is one minimal edit in place. The structure and style are kept.

| # | Where | Was | Now | Why (evidence) |
|---|---|---|---|---|
| 1 | In short, "The test" | "fixed and hashed before any 2024–2026 result was read" | "…before this study read any 2024–2026 result (§5 lists what was not blind)" | Not fully blind: 2024 was in the published replication, and the base's 2025–26 forecasts were scored by feature interactions (pre-registration §2) |
| 2 | In short, "What the feature predicts" | "+0.33 … first-serve points won **per unit** [+0.20, +0.46]" | "…per SD of his speed state (1.12 km/h)" | **Unit error.** The gate standardised a single player's f̂: SD 1.118 km/h on its 29,523 rows (`auditor_r5_gate_sd.py`). A unit of `spd_f` is 2.224 km/h of the A − B difference |
| 3 | Same | "It predicts his next match's speed better than the published 14-day window. Out-of-sample R² 0.051 against 0.019, filter better" | Replaced by the like-for-like gate: fitted together, f̂ +0.45 [+0.30, +0.59] pp per SD, the window −0.17 [−0.32, −0.01] (`auditor_gate2.json`) | **Overclaim.** The R² pair is the R1 frozen-offset version on a target the audit found biased (2_audit M1). On the clean within-match target the speed forecasts tie. The gate is the valid "more than the window" evidence |
| 4 | Answers table | S12 "It matches the published +0.090"; S10 "8%"; S9 row unlabelled; unshrunk "[+0.00, +0.91]" | "Consistent with…"; "(a point value)"; S9 marked "a pre-registered **secondary**" and "Better (descriptive)"; "[+0.002, +0.91]" | Faithful wording. +0.00 read as touching 0, but the scorer's lower bound is +0.0021 |
| 5 | In short, "Reading" | A paraphrase | Added the **verbatim** row-3 text (`results.json` → `decision.reading`). "Information the best model and the market do not have" became "beyond the best model, which already holds the closing odds". "Because TabPFN applies only 8%" is now labelled *inferred*. "It improves men's log loss by about 0.4 mLL" became "(S9), it was better by about 0.4 mLL [+0.04, +0.78]" | The quote is required. S0 tests beyond the base, not the market separately. The causal "because" is inference. The nudge is a secondary result, not a claim |
| 6 | §3, "Evidence that 0 is the right value" | "slopes … are near 1 (0.87 / 0.97 / 0.68)" | "…are 0.68–0.97 … Even decayed values carry information"; the target is named (the within-match speed difference) | 0.68 is not near 1 (`auditor_centring.json` part 1) |
| 7 | §3, "Next-match speed" | The R² pair alone | Kept, plus two sub-bullets: the R1 frozen-offset version on a biased target; and on the clean target the full forecasts tie, window − filter −2.12 [−6.24, +1.92] km/h², negative = window better | As in #3 |
| 8 | §3, the gate | "per unit" | "per SD of his speed state, 1.12 km/h" | As in #2 |
| 9 | §3, "New to the model and the market" | R² 0.12 / 0.003 | "(R1 version, in sample)" | `modeller_redundancy.json` is the R1 column, in sample |
| 10 | §3, "Leak-proof" | "the deliberately leaky controls fired every time" | The red team's at every cut; the builder's at 24 of 26 order cuts and on 16 of 26 days | **Overclaim.** `speed_meta.json` probes A and B; `4_redteam.md` §2 |
| 11 | §5, power | "0.09 per unit of `spd_f`, about the published size … 43–76% power, depending on how much of the signal TabPFN would use" | "…(numerically the published value, which was per SD of x_raw) … at a capture of 1.0–0.5". Added: "The observed capture, 8% (§6.3), was far below the 0.5–1.0 assumed" | The units differ (pre-registration §10). The power assumptions were not met, which the owner needs to read the tie |
| 12 | §6.2 | "with the base model's forecast as an offset" | "with the base model's log-odds as controls (a slope per season and a cubic)" | S0's specification (pre-registration §8) is not an offset |
| 13 | §6.3 | "capture of 8% (7% calibrated)"; "saw the same pattern: B-INJ 39%" | Added "a point value; across S0's interval it runs from about 4% to 42%"; "also saw partial capture" | a / b over b ∈ [0.012, 0.118] gives 0.044–0.421. 39% is not 8% |
| 14 | §6.4 | "against a true 0.065"; unshrunk "[+0.00, +0.91]" | "against S0's 0.065"; "[+0.002, +0.91]" | 0.065 is an estimate; consistency with #4 |
| 15 | §6.5, women A3 | One value | Added "without the 21 id-conflict matches +0.04 [−0.11, +0.19]", reading "Ties" | Pre-registered in S4 (`results.csv` `S4_A3_women_no_conflict`) |
| 16 | §7, "Observed" | "beyond the model and the market … S0 and S12 in blind 2025–26"; the power sentence unlabelled | "beyond the model, which already holds the closing odds … S0 (2024–26) and S12 (blind 2025–26)"; the power sentence marked *inferred* | S0 includes 2024, which is not blind. The power reasoning is inference |
| 17 | §7 suggestion 5; §7 suspects; §10 | "speed added nothing"; error tail "4–7%" | "showed no detectable gain (ties)"; "4–7.5%" | A tie is not "nothing" (S6a +0.15). `auditor_ks_tail.json`: 4.0–7.5% |
| 18 | §8, auditor row | "the reused base fits carried no fingerprints" | "the rating race's reused base fits (seeds 0–2)…" | The feature-interactions fits carry fingerprints (`checks/fingerprint_check.json`) |

## 2. Verified, no change needed (observed)

**Results** (`results.json`, `results.csv`):

| Item | Values |
|---|---|
| P2 | +0.0671 [−0.0496, +0.1837] |
| S11 | Block-only [−0.019, +0.153]; calendar-week [−0.050, +0.184] |
| S14 | +0.027 [−0.019, +0.074] |
| S7 | +0.094 [−0.044, +0.232] |
| S1 | 2024 +0.098 [−0.128, +0.323]; 2025 +0.009 [−0.117, +0.134]; 2026 +0.107 [−0.186, +0.401] |
| S2 | +0.048 [−0.077, +0.174] |
| S3 | Both +0.063 / one +0.083 / neither +0.077, all ties |
| S0 | +0.0650 [+0.0124, +0.1176], p 0.017 |
| S12 | +0.1034 [+0.0291, +0.1778], p 0.0088 |
| S10 | a 0.00523, a_cal 0.00474; ratios 0.0804 / 0.0730 |
| S9 | b 0.0404 / 0.0404 / 0.0452; shrunk 0.0305 / 0.0334 / 0.0389 |
| S9, gains | Shrunk +0.410 [+0.045, +0.775]; unshrunk +0.454 [+0.0021, +0.906] |
| S13 | +2.200 [+1.104, +3.296]; P2 / S13 0.0305 |
| S8 | A2 +0.095 [−0.070, +0.260]; A3 +0.147 [−0.044, +0.337]; A1 − A2 +0.008; A3 − A1 +0.044, all ties under the registered interval |
| S4, S5 | Women A1 +0.018; both tours +0.043; women A3 +0.038; no-odds −0.010, all ties |
| S6 | (a) +0.146 / +0.111; (b) +0.78 / −0.19 / +3.19 / +0.95, all ties |
| Multiplicity | 4 of 30 (S0, S9 ×2, S12) |
| Null reference | Mean 0.62; P(≥ 3) 5.0%; P(≥ 4) 1.7% (`4_verifier.md`) |

**Counts** (`check.json`):
* Men 7,068 (2,674 / 2,620 / 1,774), 33 blocks; 2025–26: 4,394.
* Recency 5,420 / 1,130 / 518. The coverage shares 79/95, 74/90 and 78/93% follow from it.
* Women 6,586; both tours 13,654.
* Polymarket 1,442 / 582.
* 21 id-conflict matches scored.
* `spd_f` non-zero on 7,066.

**Build and data:**
* 43,089 / 42,900 rows.
* Sources 19,707 / 11,362 / 370 / 474 / 36; women 10,951.
* Ceiling 81.5%; 27 broken values; 10 QF.
* Breaks +8.5 / +3.5 / +9.7.
* Event SD 1.7 / 1.0; qualifying 1.3–3.7.
* T1 +4.47 [+2.19, +6.75].
* The 14-day shares 61 / 50 / 52%.
* Constants; s_f 2.224.
* Prior correlations 0.51 / 0.14.
* Gate values +0.33 / +0.32 / +0.11.
* Training coverage 24% / 42% (2024 fit) and 33% / 51% (2026 fit), recomputed from `speed_meta.json`.
* 223 fits; reproduction 0.0 in every block; 49 tests collected.
* Point-sequence citations "0.25–0.4" and "13%"; the verifier's V1 (24–43%), V2 and "three misleading texts".

**Inferred arithmetic** (recomputed):

| Claim | Recomputed |
|---|---|
| One unit at 50–50 | +1.62 points |
| 5 km/h | 2.248 units, +3.65 points |
| The nudge's expected gain, 1000 · E[p(1−p)] · E[z²] · (βb − b²/2) with E[p(1−p)] 0.194 and E[z²] = 1.106² | 0.39 mLL at b 0.035 (0.385 at the season-weighted shrunk b 0.0337; 0.50 if b = β) |
| Nudge / S13 | 18.6%, "about 19%" |

## 3. Notes for the lead (no edit made)

* **Same footing.** The nudge's block-only interval and P2's seed-variance interval are not on the same footing. The README says why (the same base forecasts on both sides). A reader comparing "+0.41, better" with "+0.07, tie" should know that P2's registered interval is conservative near 0 (§5 says so).
* **S8 block-only intervals.** A2's and A3's block-only intervals exclude 0 (+0.009 and +0.011 lower bounds). Under the registered interval they tie, and the README reports that correctly. Not adding it avoids reading a liberal interval as a claim.
* **Ledger.** It runs to row 35. My R5 look is below for row 36.

## Looks

| # | Seasons | What was related to what | Script |
|---|---|---|---|
| R5-1 | Men 2022–2023 | Feature values only: the SD of a player's f̂ on the R2 gate's rows (29,523; the row set needs the ≤ 2023 box-score histories to exist). Nothing related to a target, result or price | `auditor_r5_gate_sd.py` |
| R5-2 | 2024–2026 | Reading the frozen outputs (`results.json`, `results.csv`, `check.json`) after the one run; no re-run | – |
