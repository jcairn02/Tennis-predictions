# M1: how checkpoint 1's required changes were made

7 October 2026 · Orchestrator. Every item of [checkpoint 1](checkpoint_1.md)'s "Required changes", before the freeze. No result was read.

| # | Change | Done |
|---|---|---|
| X-1 | the open M2 choices | written into [plan.md](../plan.md), section "Fixed at M1": eligibility, ranking and the cap (H-S2 exempt from the column cap), deployment route by the family's form, the G5 arm (2016–2024, seeds 0–2), harm (calibrated gain on 2020–2024 below −0.10 mLL moves the member to a nudge), capture (slope ≥ 0.5 on b̂·x from one pooled 2014–2024 fit), the bundle arm and the exact nudge layer, C3 dropped, the empty outcomes, Tweedie shrinkage |
| F-1 | INFO-1 out of B-STATE | `f28_state.USE_INFO1 = False`; B-STATE is BOD-C1 alone, nearest inputs recomputed (form_brk, form_hold, form_rpw_first); INFO-1's column kept as a descriptive sensitivity (body analyst); family text updated (mathematical auditor) |
| F-2 | B7 and B9a gate on × 1.25 | both rows `"trait": "slow"` with `trait_cols ["height"]` kept; `screen.run` folds the permutation only for fixed traits and reports it as a diagnostic otherwise (`p2_folded`) |
| F-3 | H-S2 widening | `s2_row` divides t₁ and t₂ by √1.25 before the joint z, the filter and the replication |
| F-4 | family text; the multipliers column | family and CSV corrected (I-045: ΔDec = −ΔTr; B-STATE: BOD-C1); the table carries `member_multipliers` (hashed), and the family a `multipliers` column |
| F-5 | inputs manifest | `screen_batch.recording_reads()` records every data file read while the panel, the history, every builder, the known nulls and the screen frame are built; their SHA-256 (and the forecast files') go into `prepare.json`; `--screen` refuses if `FROZEN_INPUTS_SHA256` is missing or any file changed |
| F-6 | the batch's scope | in the batch, descriptive: every module's `SENSITIVITIES` and the sharp-anchor diagnostic C-1; never run: MAT-K2's s̃·η (plan.md) |
| F-7 | P3's consequence | plan.md |
| F-8 | the 2025–2026 forecast hashes | every `model` and `levels` forecast file on disk (seeds 0–15 for the base in 2019–2026) is hashed into the inputs manifest |
| F-9 | the hash test | `test_table_hash_sees_eta_modulator_values` (32 tests pass) |
| F-10 | the verifier's post-fix reruns, synthetic outcomes only | below |

## F-10: the reruns on the fixed harness (synthetic outcomes; the real results never used)

**Effect sizes** (`verify/sizes_check_postfix.py`, the harness's own nuisance, no patch; mLL, planted truth against the screen's estimate, mean over draws):

| Column | Δ planted | Draws | 2014–2021: true / estimated (leave-one-season-out) | 2022–2024: true / estimated (forward) | mean z_joint | P1 null SD |
|---|---|---|---|---|---|---|
| random | 0.3 | 30 | 0.299 / 0.253 | 0.302 / 0.308 | 5.10 | – |
| surface IOS | 0.3 | 30 | 0.364 / 0.323 | 0.154 / 0.127 | 5.03 | – |
| random | 0 | 6 | 0 | 0 | 0.15 | 0.95 |
| age | 0.2 | 6 | 0.206 | 0.187 | 5.06 | 0.98 |

**The Wald path** (`verify/planted_wald.py --tag postfix`, the smallest W of three covariances against F(k, G − k)):

| Block | k | Δ (mLL) | p_joint < 5% | < 1% | mean W/k | the full gate (filter, replication, p < 5%) |
|---|---|---|---|---|---|---|
| KN-SDEV | 8 | 0 | 0.02 | 0.00 | 0.95 | 0.02 |
| | | 0.1 / 0.2 / 0.3 | 0.46 / 0.83 / 0.97 | 0.27 / 0.59 / 0.89 | | 0.19 / 0.26 / 0.39 |
| S2-like | 2 | 0 | 0.01 | 0.01 | 0.93 | 0.01 |
| | | 0.1 / 0.2 / 0.3 | 0.74 / 0.96 / 1.00 | 0.56 / 0.93 / 0.99 | | 0.58 / 0.80 / 0.93 |

Before the fix the 8-column block passed 9.7% of nulls at 5%; now 2%. Wide Wald blocks are conservative through the full gate, mainly because replication along an 8-dimensional discovery direction is noisy.
