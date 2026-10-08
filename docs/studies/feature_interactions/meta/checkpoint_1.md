# Checkpoint 1 (M1): the hypothesis table and the screen plan

7 October 2026 · Meta-auditor · Research evidence, not a decision. This audits the process (forking paths, multiple testing, leakage, uneven gates, decisions after looking), not the ideas. My rulings on process disputes are final (team.md). From this checkpoint I keep the [look ledger](look_ledger.md).

**Read:** brief, team, plan (all decisions), the critique, the round-1 math and feasibility audits (with the per-family cards I needed), the rulings and addendum, the family (md and CSV), builders.md, the three build notes, the harness verification, the ledger; `hypothesis_table.csv`, `known_null_table.csv`, `prepare.json`; `screen.py`, `screen_batch.py`, `tabpfn_tests.py`, `history.py`, `panel.py` and the feature modules where a check needed them.

**Ran (no result read, nothing written to the study except this file and the ledger):** the table and builder hashes recomputed from disk; `pytest test/feature_interactions` (synthetic, 31 pass); an own-match invariance check (§2, scratchpad scripts). Nothing after 2024 was read.

## Verdict: sign off M1 after the listed fixes

The table is the family: 33 screen rows plus H-S2, B4's absence recorded, every weight, trait (one exception), test and sign as ruled. **No signed-sum block reverses its one-sided test**: every block's tested column, with its table sign, reproduces the declared direction of every member (§1.2). One member, I-045, follows its mechanism but contradicts the family's literal text, which must be corrected (R-5). The harness verifier's fixes B1–B14 are in the code (B9 through the orchestrator's alternative, B13 in part), but its post-fix reruns are missing (F-10). The reported probes hold, and my own-match check finds no builder reading its target match's result. **No candidate has been related to a match result.**

Two things must happen before the hash. First, the selection rules for M2 must be completed now, because the screen's results will be known before M2 (§6.2). Second, the changes F-1 to F-8 must be made, because each changes the table or the code hash, and the verifier's post-fix reruns must be done (F-10).

### Required changes

| # | Severity | Change |
|---|---|---|
| X-1 | **blocking** | Fix in plan.md, now and hashed with the table, the M2 choices still open: G5's window, harm and capture definitions, ranking under the cap, how multi-column candidates and H-S2's 17 columns count against the cap, the nudge model, C3's fate, the empty-outcome rules (§6.2) |
| F-1 | should fix before freeze | INFO-1 out of B-STATE (R-1). Set `f28_state.USE_INFO1 = False`, drop `bdst_info1` from B-STATE's deployment columns, recompute B-STATE's nearest inputs by the module's own result-free rule and fix them in `NEAREST`, and update the family row and CSV |
| F-2 | should fix before freeze | B7 and B9a gate on the slow-trait widening, variance × 1.25. P2 on height is computed and reported, never folded into `p_joint` (R-6) |
| F-3 | should fix before freeze | `s2_row`: divide H-S2's t₁ and t₂ by √1.25 before the joint z, the filter and the replication (R-7) |
| F-4 | should fix before freeze | Family and CSV text: I-045 is ΔDec = −ΔTr (R-5); B-STATE is BOD-C1 alone. Add a column to the table recording each block's applied member multipliers (convention §1.2), so the frozen table states its own orientation |
| F-5 | should fix before freeze | Inputs manifest: SHA-256 of every data file that the panel, the history, the builders and the screen read, in `prepare.json` and the frozen line. That is `panel.manifest()` plus the direct reads: `stage4_constants.csv`, `stage4_features.parquet`, `stageB_adj.parquet`, `stage1_match_stats`, `stage3_ratings.parquet`, `pieces.parquet`, the Court files, `ttt_timed.parquet`, the model frame and the forecast files. The screen refuses on a mismatch. If an input changes before the screen, the table is re-prepared and re-frozen only while no result has been read, with a ledger row |
| F-6 | should fix before freeze | Freeze the batch's scope. Decide which pre-declared descriptive outputs run inside the one batch and which never run: the sharp-anchor diagnostic (C-1 with I-039), MAT-K2's s̃·η beside s·η, each module's `SENSITIVITIES`, B11's per-member decomposition. None is in `screen()` today. Anything run later is an exploratory, logged look that cannot change a claim or the bundle |
| F-7 | should fix before freeze | Write P3's consequence into plan.md (R-11) |
| F-8 | should fix before freeze | Record now the SHA-256 of the 2025–2026 forecast files that already exist (`model` seeds 0–15; ledger row 18) |
| F-9 | low | Add the verifier's missing regression test for B4: a changed η-modulator must change the table hash |
| F-10 | should fix before freeze | Rerun the verifier's `verify/sizes_check.py` (nuisance patch removed) and `verify/planted_wald.py` on the fixed code (synthetic outcomes only), as the verification required, and record the result. No output is later than 22:00, and the fixes landed at 22:00–22:20 |

**Then:** run `--prepare` (every swap test true), write the `FROZEN_TABLE_SHA256` and `FROZEN_MODULES_SHA256` lines and the inputs hash into plan.md, and add a ledger row. The screen then runs once.

## 1. The table against the family and the rulings

### 1.1 Rows, weights, traits, tests (observed)

* **Rows.** The family has 35 rows. The table holds 33. H-S2 is scored inside the screen run as the 34th member (`s2_row`). B4 is absent, and its drop is recorded with a reason in plan.md and in structure.md.
* **Hashes.** They reproduce: the table hash recomputed from the CSV on disk is `77089d87dad828d5…`, and the builder-files hash is `2d8fda4c8047fdaa…`. No builder file has changed since `--prepare`. `mkt_common.py` is now among the hashed files, which closes the market analyst's open issue 5.
* **Weights.** All 33 rows equal the family after the addenda: I-008 at 2, I-042 at 1, B6 at 1, B2 at 0.5. The raw sum is 24.0 over 34 (24.5 less B4's 0.5). `weighted_holm` and `weighted_bh` normalise to mean 1 over the 34, giving 2.83 / 1.42 / 0.71. Holm's first line per unit of raw weight rises from 0.05/24.5 to 0.05/24, so the family's MDEs fall by under 1% (computed from the z thresholds).
* **Traits.** All rows agree except **H-S2**: the family says slow, `s2_row` writes "none" and applies no widening (R-7, F-3).
* **Tests.** Wald rows: B-LEVER (k = 3), B3 (2), B-RECAL (2), B-SWITCH (4) and B-HOME (2), all at 0.5 and two-sided, as the verifier's two-sided-weight note requires. Every other row is a single coefficient.

### 1.2 Sign conventions of the signed-sum blocks (read from the module code, as the coordinator asked)

**Two conventions are in use, never mixed inside a block.** (i): each member is multiplied by its declared sign and the block is tested "+". (ii): the members are summed as they are and the block is tested with the family's common sign. Both give the same one-sided test. The helpers `f01.signed_block` and `mkt_common.signed_sum` / `signed_sum_masked` turn any string other than "+" into −1; every call passes ASCII "+" or "-". `f20.block` takes numeric ±1.

| Row | Declared (family; members) | Code: member × multiplier | Table sign | Reproduces the declared direction? |
|---|---|---|---|---|
| B2 | + (I-012 +, I-013 +) | +e_ace, +shield | + | yes |
| B-FLB | + (L +, HP +) | +L̃, +H̃P (s·η) | + | yes |
| B-CLUTCH, B-VENUE, B-AGE | + (I-026; I-072; I-070) | one member, + | + | yes |
| B-INFO | + (I-080, C-2, INFO-2) | +, +, + | + | yes |
| B11 | + (On, I-075, I-076) | +1, +1, +1 | + | yes |
| B-STATE | + (INFO-1, BOD-C1) | +1, +1 | + | yes |
| B6 | − (I-033, BOD-L2, U_rest) | +, +, + (each an uncertainty measure; s·η) | − | yes, convention (ii) |
| B-REPUTE | − (I-071, I-083, I-055) | +, +, + | − | yes (ii) |
| B-MOTIV | − (I-089, I-090) | +, + | − | yes (ii) |
| B-LOAD | − (ΔFat, ΔOff) | −1, −1 | + | yes (i) |
| B-PREV | − (ΔPrevX, contrast) | −1, −1 | + | yes (i) |
| B10 | − (I-059, I-088, I-060, I-074) | −1 × 4 | + | yes (i) |
| B-INJ | − (Rust, inj·e_pre, "ΔTr") | −1 × 3 on Rust, inj·e_pre, **Dec = −slope** | + | I-043 and I-044 yes. **I-045: the mechanism's direction** (a decaying serve predicts losing), but the opposite of the family's literal "ΔTr (trend), −", since the code's minus is applied to −slope (R-5) |
| B7 | per member (I-023 +, I-031 +, I-032 +, I-048 −, −) | +, +, +, −, − | + | yes (i) |
| B9a | per member (I-024 −, −; I-058 +; I-061 −) | −1, −1, +1, −1 | + | yes (i) |
| B9b | per member (I-063 −, I-065 +, I-066 −) | −1, +1, −1; I-063's member is −D/κ, oriented like ΔFat (positive when A is the more tired) | + | yes (i) |
| B-ANCHOR | per member (I-037 −, I-038 +) | −, + | + | yes (i) |
| B-OVERREACT | per member (I-025 −, I-085 +, I-086 −, I-091 −) | −, +, −, − | + | yes (i) |

**Single-column rows.**

* I-008, I-036, I-042, I-049, I-082, I-084 and LIT-2 are tested "+" on un-negated A-oriented columns. τ = ĥ_B/p − ĥ_A/(1 − p); LIT-2 is |η|·ΔF.
* I-053 is tested "−" on x = Fat_A·a_A − Fat_B·a_B, not negated.

All reproduce their declared directions. No block mixes conventions, and no member's sign is applied twice or not at all, except I-045's, against the family's text only. The fix is F-4: a column stating the applied multipliers, because a reader of the table cannot see which convention a "+" means.

### 1.3 Price-slope rows and controls

* **The candidate is never among its own controls.** Every `x_times_eta` row (B-LEVER, I-036, I-084, I-049, B-FLB, B6) has the M-set, and none of its η-modulator controls is its own s. I checked the lists in `f02` / `f10` / `f13`:
  * B-LEVER holds 5: 1[Slam], O, the unranked flag, L and HP;
  * I-036 holds 7: the unranked flag, ΣR, L, HP and B-LEVER's three;
  * I-084 holds 7: the level dummies, O, L and HP;
  * B-FLB holds 5: O, ΣR and B-LEVER's three;
  * I-049 holds 2: Σlog1p(rest) and ΣFat;
  * B6 holds 6: R, E and four missingness flags.
* **`x_of_eta` rows** (I-042, B-ANCHOR, B-REPUTE, LIT-2) are re-evaluated with each base's η, and the M-set is on.
* **Controls follow the family, with three accepted deviations** (R-2, R-10):
  * B11 keeps ΔOn as a member, not as a control;
  * I-049's joint fit uses the pre-addendum linear rest and Fat columns, as its family row literally lists them;
  * B-REPUTE and B-OVERREACT carry an M-set that their family rows do not list.

### 1.4 Members dropped or kept by result-free gates

Every gate below was declared before the builds, in the round-0 kill test and/or the round-1 card. All are recorded with numbers in the build notes and their JSONs. Values are raw correlations, men / women.

| Member (row) | Declared gate (source) | Value | Outcome |
|---|---|---|---|
| I-028 (B6) | split-half ≥ 0.3 (MAT kill test; MAT-R5) | 0.051 pooled (0.011 / 0.154) | dropped |
| I-029, I-030 (B5) | kill if split-half < 0.3 or the de-noised pair CV < 0.2 (MAT kill test; the math audit's B5 rule) | r 0.279 / 0.225; pair CV 0.113 / 0.091 | B5 dissolved |
| I-009 (B-CLUTCH) | split-half ≥ 0.3 (MAT-C2; family) | 0.160 / 0.270 (Spearman–Brown 0.28 / 0.43) | dropped; raw binds (R-9) |
| I-027 (B-CLUTCH) | split-half > 0.1 (MEC-19; card) | −0.072 / −0.011 | dropped |
| I-068, I-069 (B-AGE) | after 29 the return residual drifts below the serve residual (MEC-14; card) | +0.0011 ± 0.0008 / +0.0005 ± 0.0013 | dropped |
| I-073 (B-VENUE) | split-season carry-over ≥ 0.15 (MEC-13; card) | G −0.006 / −0.083, H 0.124 / 0.077 | dropped |
| I-019, I-021 (B4) | persistence ≥ 0.05 (MEC-11); ≥ 0.15 and above a shuffled-hand placebo (MEC-09) | 0.032 / 0.043; 0.071 / 0.026 (placebo 95th 0.086 / 0.207) | dropped |
| I-018 (B4) | stability ≥ 0.3 (card) **and** an out-of-sample serve-point gain ≥ 0.02 milli per point (MEC-10) | 0.528 / −0.065; +0.002 / −0.016 | dropped by the orchestrator, so B4 is gone (R-8) |
| kept | I-058 above the replays (0.086 against a mean of −0.011); I-065 ≥ 0.3 (0.887); **I-045 above the replays (0.0096 against a mean of 0.0003; one replay is 0.0099)**; B7's CV(r) 0.584, CV(r̄) 0.176 and height-ace 0.40 ≥ 0.05; I-072 0.661 / 0.566 ≥ 0.3; I-016 (MEC-07: not both slopes null); I-022 (pooled); I-033 74% ≥ 5%; I-042's hazard SD 1.03 ≥ 1 pp (then weight 1 by the addendum); I-025's skill gate 0.16 < 0.2 (it stays luck) | | |

**Choices made after the values were seen** (all result-free; none reads an outcome or a price against an outcome):

1. "Raw, not Spearman–Brown". This changes only I-009 for women (R-9).
2. Adding MEC-10's second clause for I-018 (R-8).
3. Reading I-045's "above the replay" as above the replays' mean, as was done for I-058 (R-4).
4. K_h was tuned (grid 25–8,000) on the same next-match ace target as I-023's gate.
   * At the tuned K_h = 100 the height prior gains +0.40 milli per point over the plain IOS. At the audit's 1,000, which was only used for the novelty R², it would lose 0.24 (0.182558 against 0.182323).
   * Builders.md allows tuning on a statistic target, so the member stays. The gate passed at its own in-sample optimum, and the report must say so. Note only.
5. I-042's k grid extended once after it chose its edge (ledger row 13).

## 2. Leakage and timing

**The reported probes hold (observed in the build notes and JSONs).** Each reverses or removes every result after a cut and requires every earlier match's value to stay put:

* the structure analyst's field statistics (I-072 venue pace, I-029's state, B4's three fields): 0.0 at five cuts, with 1,858–35,775 later rows moving;
* the market analyst's hazards (I-042, estimators a, b and c): 1.3e-12 at three cuts. Its I-025 β_f: exactly 0, with 99% of later rows moving;
* the body analyst's eleven rows: 66 of 66 at tolerance 1e-9.

They found and fixed five real faults: a median age over all rows; minutes medians taken from 2010–2018; unfrozen block standardisation; and two cross-player rounding paths (a global prefix sum, and `clock_sum` before its per-key fix).

**The history-order fix is in** (B3). `history.long_table` places events by their earliest day and keeps rounds in order. `test_history_order_and_rest` asserts that `round_order` never decreases within a player's event. The body and market analysts rebuilt after 22:00. The structure analyst's figures are the post-fix ones (I-029 men 0.241 → 0.279).

**Builders and the result column: B10 holds only for the panel.** `build_all` drops `a_won`. But `history.long_table()` carries every match's own `won`, score, minutes and box score, the model match's own row included, and several builders read Stage B's per-match z. The probes test later-to-earlier leakage only, so nothing had tested whether a builder reads its **own** match. I tested it (ledger row 20):

* every model match starting on 20 Jan 2020 (88) and on 28 Jun 2022 (71) had its own result reversed in memory: the winner flag, both players' box scores and Stage B's z exchanged, `retired_self` recomputed;
* all 33 rows were rebuilt and compared.

| Day | Own columns that moved | Reading |
|---|---|---|
| 28 Jun 2022 | none (largest 2.3e-12) | clean. Later rows move (up to 6,277 rows for one hypothesis): the test has power |
| 20 Jan 2020 | seven blocks (B-INJ, B-OVERREACT, B-VENUE, B10, B6, B7, B9a) moved on almost **every** row, including all earlier ones | a column-wide rescale. Their **raw members** are unchanged on the reversed rows (largest 6e-14) and on every earlier row (0 moved), while later rows move (I-045 12,060, I-025 10,850, I-058 12,178). The blocks standardise each member by its 2014–2021 SD, which depends on later rows' (legitimately changed) values |

**Conclusion:** no builder reads its target match's result, through the history table or Stage B, on either day.

* The rescale is a single constant per member, like the screen's own scaling on discovery rows, and the probes rightly hold it fixed.
* It does mean a block's member weights depend faintly on the 2014–2021 feature distribution. For the final test, these constants must stay frozen at their 2014–2021 values (§6.3).
* Not covered: per-match tables I could not reverse. Stage 4's big-point values and Stage 3's ratings are pre-match by construction. The shot-level counts feed only the dropped I-027.
* Scripts: `own_match_check.py`, `own_match_members.py` and their two `*_compare.py` scripts, in this session's scratchpad (`C:\Users\zerom\AppData\Local\Temp\claude\c--Users-zerom-Documents-Tennis-predictions\1407378e-d38c-4499-b447-ebfa0da60f28\scratchpad\`). They can be copied to `src/eda/feature_interactions/verify/` and rerun after F-1 and F-2.

**Nothing after 2024.**

* `screen.load` filters 2014–2024 and asserts it. The panel is built with `max_season = 2024`.
* The builders cut the history at the panel's last season: f20 before 20 Dec 2024, `mkt_common.hist` at the panel's last earliest start, `f01.cut_history` at the last season.
* `screen.load`, `tabpfn_tests.frame` and `long_table` still read their whole files, 2025–2026 results included, into memory before filtering. Nothing uses those rows, but filtering at read time would make "never read" literal (note).

**Constants with a little look-ahead (accepted convention, note).** Several are scalars estimated on 2010–2018 or 2013–2018 statistics and applied to 2014–2018 rows:

* shrinkage K and τ² (I-029, I-045, I-058, I-065);
* β_h;
* the 2010–2016 style centroids;
* Stage 4's big-point K (2011–2018).

M5 allows statistic-target tuning on 2013–2018, and the probes hold these constants fixed. They carry no single match's result.

**One construction tuned on a result-derived label.** I-042's estimator and k were chosen on each side's own retirement in the 2013–2018 model matches (ledger row 13), a period inside the discovery window, and a retiree always loses. It is one constant from 13 options, chosen on an out-of-sample criterion and prescribed in round 1. Even so, I-042's z₂ (2022–2024) is the cleaner part of its evidence, and the report must say so.

## 3. The look ledger

The ledger is now complete for every disclosed look.

* **Renumbered.** The two rows numbered 11 are now 11 (the verifier) and 12 (the feasibility auditor); the market analyst's row is 13.
* **Added** (rows 14–20, with their own times):
  * 14: the feasibility auditor's round-1 R² on the 58 inputs, which include the price, and its 2025–2026 presence flags;
  * 15: the structure analyst's statistic-target gates and constants;
  * 16: the market analyst's I-025 β_f fits and skill gate, which use past results as inputs, and its price scale constants;
  * 17: the body analyst's statistic-target gates and constants, including I-063's κ;
  * 18: the orchestrator's local fits, which **include 2025–2026 base forecasts, unscored**;
  * 19: the point-sequence study's B1 and E1 result tests in another session: prior knowledge bearing on I-042, I-044 and I-045;
  * 20: this checkpoint.
* **No candidate was ever related to a match result.** Rows 1–3 and 11 relate results only to existing inputs, the current best's forecast or random features.

## 4. Rulings on the process disputes (final)

**R-1 · INFO-1 inside B-STATE: drop.**
* **Ruling.** INFO-1 leaves B-STATE before the freeze. B-STATE becomes BOD-C1 alone: sign +, weight 0.5, the same controls, nearest inputs recomputed by the module's rule (F-1).
* **Why M7 does not protect it.** M7's closed list of kill reasons governs judgement at G1 ("priced in", "TabPFN could form it"). It does not oblige the screen to carry a column whose construction rests on a false factual claim about the pipeline.
* **The premise is false.** The rulings define INFO-1 as the update from the player's own matches "the leak-proof IOS state has not counted". The body analyst showed, from the IOS code and on 22,696 player-matches, that the state already counts them: the panel's own IOS change correlates 0.879 with the update, slope 1.10 (0.877 and 1.14 where the match was already counted).
* **What the column would carry.** It re-measures what the inputs hold, plus implementation noise, and its prevalence collapses for women in 2022–2024 (2.6%). Kept, it would cost BOD-C1 roughly √(1/2) of its z, with no hypothesis left to test.
* **Status.** This is a construction-validity correction made before any result, of the same kind as the round-2 addenda (B6's U_rest, I-042's weight). INFO-1's column may be reported as a descriptive sensitivity. It never gates and never enters the bundle.

**R-2 · B11's controls: keep `STRICT_UNION = False`.**
* **Ruling.** The family lists I-051 (On) as a member of B11. The literal union of the per-member controls would add ΔOS (= ΔOn) and Δr, its linear twin, which would make that registered member unidentifiable. Membership governs.
* **Recorded now.** B11 tests on-site rhythm as a whole, including ΔOn's main effect. A B11 result may not be attributed to the interactions I-075 or I-076 unless the pre-declared per-member decomposition, if F-6 places it in the batch, supports it. The same reading applies to B10, where I-060 is identified only through its age term.

**R-3 · I-063's κ of the wrong sign: keep as built.**
* **The column does not depend on κ's sign.** The member is −D/κ. To first order D = −s(1 + η)κ·ΔFat, with s the iid leverage, so −D/κ ≈ s(1 + η)·ΔFat for either sign of κ, and the block standardises it. Using |κ̂| is therefore not a sign choice, and the declared direction (−) stands.
* **What κ̂ < 0 means.** κ̂ = −0.00274 ± 0.00016: recently loaded players beat Stage 3's expectation. This is a result-free sign of survival selection that bears on every fatigue member (B-LOAD, I-053, B9a, B9b). It is not a declared gate, so no member drops and no weight changes. It may not be cited at M2 for or against fatigue.

**R-4 · I-045's narrow gate: keep.**
* **Ruling.** The declared gate is "split-half reliability above the pure-luck replay" (BOD-30, card 09). The analyst compared with the replays' mean (0.0096 against 0.0003), the reading used for I-058. A stricter reading chosen now (above every replay, or a 2-SE margin) would be exactly the after-the-values choice the orchestrator refused for Spearman–Brown.
* **Recorded beside it.** One of the three replays (0.0099) exceeds the observed value. The margin is under 2 SE (SE 0.005). The "halves" are the first-in and first-won slopes, the analyst's operationalisation of the card. The member is probably noise and costs B-INJ some power, which M7 accepts.

**R-5 · I-045's direction: the code stands; the family text is corrected (F-4).**
* **The conflict.** The family row writes "ΔTr (box-score serve trend)" with the block's −. The code enters Dec = −(the shrunk slope) with −, so an improving serve raises a player's predicted chance. The literal family text would test the opposite.
* **Why the code's direction is the declared one.** The registered mechanism is that a falling serve signals impairment and predicts losing: BOD-30's title and mechanism, I-045's master entry, and the math audit's block list "I-045 serve decay (−)". No document argues that an improving serve predicts losing. BOD-30's "expected effect: negative" describes the decay.
* **Status.** The direction is fixed by the mechanism, before any result. The family and its CSV must read "ΔDec = −ΔTr (within-event serve decay), −".

**R-6 · The height permutation in mixed blocks (B7, B9a): gate on × 1.25.**
* **Ruling.** B7 and B9a gate on the slow-trait widening (variance × 1.25), as B3 and B-HOME already do. P2's permutation p is computed and reported as a diagnostic of the height members only (F-2).
* **Why the permutation tests the wrong null here.** Height enters only some members: I-023 in B7, I-024's two columns in B9a. Permuting heights leaves the other members' signal inside the null distribution. So `max(normal p, P2 p)` tests "the height members add beyond the others", not the registered block. It would make B7, at weight 1, unclaimable whenever its signal comes from I-031, I-032 or I-048.
* **The widening is conservative.** The verifier measured the fixed-trait null variance against the current best at 0.96 of the harness's own. Its stress test's 8.2% at a one-sided 5% falls to about 4.5% under × 1.25 (computed from that test's true null SD of 1.086).
* **Consistency.** The orchestrator chose this treatment for the Wald blocks with a fixed-trait member; applying it here removes an uneven gate.

**R-7 · H-S2: apply the slow-trait widening.**
* **Ruling.** H-S2's t₁ and t₂ are divided by √1.25 before the joint z, the filter and the replication (F-3).
* **Why.** The family classifies S2 as slow. plan.md's H-S2 text names the clustering but not M4's factor, and `s2_row` writes trait "none". M4, as adopted, says the most conservative variance is used. Exempting the one TabPFN member from what the 23 other slow rows receive would be an uneven gate.

**R-8 · B4 and the originators' kill tests: B4's drop stands.**
* **The rule applied.** The orchestrator applied MEC-10's second, result-free clause, declared in round 0 for the member as built: an out-of-sample serve-point gain ≥ 0.02 milli per point (observed +0.002 men, −0.016 women). The plan's rule is that pre-declared result-free gates bind as declared.
* **Evenness check.** Of the round-0 kill tests with result-free clauses, all were applied to the members as built, with three explained exceptions:
  * MEC-04 (I-012) failed, and I-012 was restored by the CONTESTED ruling MEC-R2b, with conditions: the process's documented exception;
  * MEC-05's failure (I-008's components) moved I-008's primary to z_spw by ruling MAT-R4;
  * MEC-16's serve-point clause concerns a serve-point height prior that was never built. I-023 is ace-only and passed its ace clause.
* **Consequence.** No further member drops, and no restored member re-enters.

**R-9 · Split-half means the raw correlation: stands.**
* It is the convention of the project's Stage 3 and shot-level code, and the structure analyst stated it with the gates.
* It is the stricter reading, it changes only I-009 for women (raw 0.270 against Spearman–Brown 0.43), and it is result-free.

**R-10 · Joint fits and added controls: accepted as built; nothing changes after the freeze.**
* **I-049.** It is fitted jointly with B6 through the linear Σlog1p(rest)·η and ΣFat·η, which its family row literally lists ("BOD-C2, I-054"). These span B6's R·η control. B6's addendum members are not added to I-049, while B6 does control for I-049's E·η. The asymmetry is accepted.
* **B-REPUTE and B-OVERREACT.** Both carry the M-set, which their rows do not list. Their members depend on η (I-055) or on prices (I-085, I-086), so the M-type rule applies, and extra controls only make the test conservative.

**R-11 · P3's alarm: its consequence is fixed now (F-7).**
* **If the alarm fires.** That is, more than one of the six known nulls passes the family's Bonferroni line as coded (p < 0.05/34 after the filter and replication). Then the family's claims and bundle eligibility are suspended, and checkpoint 2 investigates.
* **What may follow.** A recalibrated re-run is exploratory: no claim, no bundle and no opening of 2025–2026 follows from it. The one exception is a code error fixed without reference to any family result; the corrected batch then runs once more, with a ledger row.
* **Reported in any case.** The six known nulls' z_joint and KN-SDEV's W/k are reported descriptively, because the alarm alone has little power.

## 5. The harness verifier's fixes (spot-checked in the code)

| Fix | Where | Status |
|---|---|---|
| B1 | `screen.nuisance`: `if m.any() or s is None` | applied; `test_effect_sizes_with_a_season_missing_one_tour` |
| B2 | `screen.run`: `N_P2_EXT` = 20,000 fresh permutations when p ≤ 0.01; `p2_n`, `p2_sd` stored | applied |
| B3 | `history.long_table`: `ev_obs`, then the round order; `obs_mono`; `rest_days` | applied; test asserts rounds never reverse |
| B4 | `TABLE_COLS` holds `eta_mod_sha256` and `trait_cols`. `screen()` refuses on a module-hash or table-hash mismatch and on any swap failure | applied; regression test missing (F-9) |
| B5 | `screen_one` serves both the family and P3 | applied |
| B6 | the permuter re-runs `combine`, returns (x, controls) and permutes only players with a value | applied; tested |
| B7 | P2 compares the unwidened z | applied |
| B8 | the smallest W of three covariances against F(k, G − k); the scalar replication contrast | applied (`coef_test_multi`, `run_wald`) |
| B9 | Wald block with a fixed trait | replaced by the orchestrator's × 1.25 (`run_wald`'s trait branch); extended to B7 and B9a by R-6 |
| B10 | `build_all` drops `a_won`; `swap_sides` guards it | applied. The history table still carries every match's result (§2: no own-match read found) |
| B11, B12, B14 | the load check; NumPy keys in `strata`; base η in the permuter | applied |
| B13 | `built` keeps only `new`; the permuter works in place | applied in part (one panel copy per permuter, not a slim frame) |

* **The suite passes** (31 tests).
* **Code verified versus code now hashed.** The verifier's simulations ran on the code as of about 21:34–22:05. The fixes were applied afterwards: `history.py` at 22:00, `screen.py` and `screen_batch.py` at 22:20. I read the hashed versions in full; they implement the verifier's exact fixes and plan.md, apart from R-7.
* **Post-fix reruns missing.** The verifier asked for `verify/sizes_check.py` (with its nuisance patch removed) and `verify/planted_wald.py` to be rerun after the fixes. No output in `data/studies/feature_interactions/verify/` is later than 22:00, so this is F-10.

## 6. Freeze readiness and the plan after the screen

### 6.1 Ready once fixed

The screen's statistics, gates, multiplicity, placebos and frame are verified. The freeze mechanism holds: `--screen` refuses to run without matching table and module hashes, rebuilds every column and refuses after a swap failure.

What remains for the freeze is the list at the top: X-1, F-1 to F-8 and F-10. One fact affects the timing: other sessions are rebuilding shared tables. Without F-5, a changed upstream table would make the rebuilt hashes differ and the screen refuse to run, with no rule for what happens next.

### 6.2 The M2 choices that must be fixed now, with the table (X-1)

**Is the M2 procedure specified enough to pre-register without discretion? Not yet.**

* **What is specified.** The final test's skeleton is: one bundle arm against base, 16 seeds, disjoint-seed encompassing, a two-sided 95% interval on b as the primary reading, a frozen match list.
* **What is not.** Several G5 and bundle rules leave choices.
* **Why they must be fixed now.** G5 reads the same 2016–2024 results as the screen. If these choices are made after the screen's z's are known, the bundle can be steered. They belong in plan.md now:

1. **G5's window**: 2016–2024 or 2019–2024, one of them (plan M8 says "or").
2. **The G5 arm**: base plus the candidate's frozen `tabpfn` columns, seeds 0–2, both orientations, the decided per-tour calibration.
3. **Harm**: the arm's paired log-loss gain over the base, both tours pooled; the column is dropped when the point estimate is below −0.10 mLL. State whether the gain is calibrated. The walk-forward calibration from 2019 (`tabpfn_tests.calibrated`) exists only from 2020, so a calibrated harm can only be computed on 2020–2024, as `s2_row`'s effect size is; otherwise state the raw alternative.
4. **Capture**:
   * the OLS slope without intercept of (η_arm − η_base), on the same seeds, on b̂·x;
   * b̂ comes from the model-base joint 2014–2024 fit with the row's controls (the coefficient vector for a Wald row);
   * a slope ≥ 0.5 deploys the candidate as a column, otherwise as a nudge.
5. **Cap and ranking**:
   * at most six candidates and eight columns;
   * the ranking key: weighted p (p_joint/w) or z_joint, one of them;
   * how a multi-column candidate counts (B7 deploys five columns, B9a four, B-LEVER three);
   * what happens to **H-S2's 17 context columns**, which exceed the cap alone: exempt, deployable only as its own arm, or excluded.
6. **The nudge layer**:
   * the exact model: per-tour slope on η_B, the cubic or not, the x_k with or without the screen's controls;
   * fitted on B's out-of-sample forecasts from 2014 to the season before, pooled over tours;
   * raw or calibrated η.
7. **C3 (the hybrid arm)**: adopted by a rule (for example, a capture slope between two fixed values), or dropped. Not "if capture is mixed".
8. **Empty outcomes**: nothing eligible means 2025–2026 stays closed (critique). Fix also the case where every eligible candidate fails harm, and the case where only H-S2 is eligible.
9. **S9's shrinkage**: Tweedie's formula over the model base's z_joint of the 34 members. This fixes the expected gain the pre-registration will state.

### 6.3 What the final pre-registration (M2, before 2025–2026 is opened) must contain

1. **Population**: the frozen 2025–2026 match list (debut seasons out), its count and SHA-256, and the data version: the frozen pre-rebuild frame, or the live corrected Stage 0 through `id_map.csv`. Later matches are excluded.
2. **Tennis My Life faults** (rulings R2-measure, feasibility round 2 §4), as a procedure, not an intent:
   * women are unaffected;
   * the 476 of 573 men's TML rows that the official feeds replaced are used as replaced;
   * the rule for the 97 Roland Garros 2026 qualifying rows (excluded from histories, or their first/second split set missing);
   * the repair is programmatic, hashed, inspected by no one row by row, and logged;
   * the **base and every arm are refitted on the same repaired inputs**: the existing 16-seed 2025–2026 base forecasts are superseded if the inputs change, and the pre-registration says which set is used;
   * each test match's contaminated share is counted from source flags;
   * the secondary endpoint covers matches where both players' share is under 20%;
   * the exposed arms are flagged (B2, B3, B7's profile parts, I-008's z_C1 sensitivities);
   * no λ-attenuation.
3. **Arms**:
   * B and F, seeds 0–15, both orientations, recalibrated per tour walk-forward from 2019;
   * F composed by the rules of §6.2;
   * the history cut moved to 2026 only for building the test rows;
   * a check before any 2025–2026 result is read: the 2026 build must reproduce every frozen column exactly on its 2013–2024 rows. This proves that no constant moved, the blocks' member SDs of §2 included.
4. **Primary**:
   * logit P = a_tour·η_B[0–7] + c_tour·η_B[0–7]³ + b·(η_F[8–15] − η_B[8–15]). State raw or calibrated log-odds (raw is natural, since the free slopes calibrate), and per-tour or per tour × season slopes;
   * the union-clustered variance (the largest of three), t on G − 1 = 20 df;
   * **the two-sided 95% interval on b is the reading** (plan M9), with the one-sided p reported beside it.
5. **Effect size and expectations**:
   * F's paired log-loss gain over B across 16 seeds, with a four-week-block interval (positive = F better; a tie when it spans 0);
   * the MDEs (0.43 one-sided, 0.55 two-sided);
   * the expected gain (shrunk components × capture) and the power at it;
   * the statement that a tied gain is the likely reading even if the bundle is real.
6. **Secondary endpoints, descriptive**:
   * per tour and per season;
   * the TML-clean subset;
   * the Polymarket subset, F against B and each against the 24-hour price, and C4's move test;
   * each finalist alone (8 seeds);
   * **the bundle without the members already scored on 2025–2026** (math audit finding 7: I-006, I-020, I-030, I-035, I-037, I-048, I-049, I-063, I-071, I-080, I-085, I-086, I-087);
   * F_noodds against B_noodds, if kept.
7. **Columns that are stale or shift in the test years**, and their handling:
   * B-CLUTCH's Δb (Sackmann's Slam point files end in 2024);
   * I-082 (lower-level box scores double in 2025);
   * women's heights (39% in 2025–2026);
   * Pinnacle ends in January 2026 (C-1).
8. **The red team** (S3): it reports before the hash. A finalist that fails is dropped, and the bundle is recomposed by the same rules, with nothing else re-read.
9. **The final test's code.** `tabpfn_tests.py` has no `final_test` yet. It must be written, verified on synthetic outcomes by an agent who did not write it, and hashed with the pre-registration. It runs once, with a ledger row.
10. **Readings** (critique §7) and the claim limits: per-tour results are descriptive (MDE about 0.85), and features already seen on 2025–2026 cannot be confirmed there.

## 7. Not checked here

* I did not re-derive each member's formula against its master-list card beyond the signs and the cases named above. The red team (S3) re-implements the finalists at M2.
* I did not re-run the swap tests or the coverage figures. The table records them, and its hash reproduces.
* I did not audit the upstream tables (surface IOS, Elo pieces, Stage 3 and 4, Stage B) beyond the analysts' and verifier's checks of orientation and timing.
