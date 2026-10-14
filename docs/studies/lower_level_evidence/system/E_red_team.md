# E: the red team's audit of the level-evidence system

9 October 2026 · Role E (red team) of the level-evidence system · Research evidence, not a decision: the lead fixes
SYS's internals, the owner decides. Specification: [SPEC.md](SPEC.md). Evidence written by E is under
`data/studies/lower_level_evidence/system/audit/` (written `audit/` below); `system/` is
`data/studies/lower_level_evidence/system/`.

**Keys.** *Observed* = read in code (`path:line`) or computed by E (file cited). *Inferred* = E's reasoning.
*Suggestion* = a proposal for the lead. Scores follow the owner's rule: "better" or "worse" only when the 95% interval
clears 0, otherwise "unresolved" with P(better). E read no outcome of a 2025–2026 match: every computation of a
performance reads seasons ≤ 2024 (the re-derivations ≤ 2023 and ≤ 2018); 2025–2026 rows were only counted (matches,
ids, dates, statuses). The sealed 2025–2026 parameter rows were not read: E's probe loads `params.parquet` and drops
them before use, and no value of theirs was printed or used.

# Checkpoint 1 (CP1)

Audited 23:16–00:33 UTC. State: B frozen (23:02) and READY (23:14); C1's `level_layer.py` final at 23:19
(`0b99b046…`); C2's `level_layer_ios.py` final and READY at 00:29 (`077c760a…`); F rebuilding C0_now (attempt 8 from
00:23, after E's findings); C1's IDENTITY build still in lane 1; no arm of the SYS family built; no model score of this
run computed.

## In short

* **Verdict: CP1 passes with conditions.** No leak through time and no use of the 2025–2026 outcomes was found. Five
  things must be done before any SYS-family arm is built or any dev score is read (M1–M5); none needs a change to B's
  estimator.
* **B's estimator is right as code, and nothing leaks in E's probes** (Observed). E's own code, reading only seasons
  before the one fitted, reproduces B's men's Challenger serve-points fit for 2024 (w 0.575, δ −0.0812; all four
  levels' w within 0.001; the same 27,772 targets) and for 2019 (w 0.491). Every 2013–2024 parameter row uses results in
  at least 13 days before its season's cutoff. With B's real parameters and the final `level_layer.py`, reversing every
  result after a cut moves 0 earlier pool matches at four cuts (13,758–31,163 checked), while the layer itself moves
  33,331–34,764 (`audit/g5_realparams/`).
* **M1: C1's identity gate has not run on the final code.** G1 (all 58 inputs on 67,226 matches) is pending; the
  IDENTITY build is still in lane 1 and runs an earlier layer copy. M2: C2's final joint-solve module is READY (00:29
  UTC, its SYS-config gates and probes pass); it only needs recording.
* **M3: the results channel changes what the primary and the decomposition mean.** SYS discounts men's ITF results in
  Elo (×0.25–0.5) and drops ITF-qualifying results (×0) in every season, against SPEC §3's "ITF results stay in Elo
  as today". No arm separates this Elo change from the box-score relationship, so a SYS gain could be a priced-in Elo
  gain, and "SELECTED against REF_noITF = the Challenger and qualifying part" would be mislabelled.
* **M4–M5: the scorer predates addition 2 and is not frozen.** `system_pairs.py` was last written at 20:58 UTC, before
  addition 2 (21:06): it has no Holm correction, no default for the 2026 speed rule (and its "drop" sensitivity drops
  416 men's matches, not 909), and falls back silently to "REF" if the selected arm lacks a fit. The CP1 addition
  must freeze it, with the build code, after it implements addition 2.
* **Two estimates should not be read as B's report reads them** (Observed). w above 1 (men's break points forced at
  Challengers, up to 2.82; the free fit sits at its bound 3) is an artefact of the pool prior: with tier means it falls
  to 1.0–2.6. And δ is a forecasting term, two to three times the same-player level residual (2024: −0.081 against
  −0.039 [−0.049, −0.030]; 2019: −0.037 against −0.012).
* **F's C0_now must not be used as built** (Observed, S9). TennisLive ids were linked without their tour: 16,151
  player rows of new matches hold an id of the other tour in the build of 23:18 UTC, still 6,159 after the rebuild of
  00:12, 30 frame players among them (Alexandra Eala's id gets men's matches). A blocker for NEW_ASIS and NEW_SYS_BOTH
  only. C0_now adds mostly women's and ITF-qualifying results, and its 2026 part is largely the reference's
  publication lag, so the rule test can say little about men and mixes the rule with data completeness.
* **What the readings can show** (Inferred, from the first run's intervals): only differences of about 0.08 mLL (dev,
  men) or 0.12 mLL (holdout, men) and up. SYS against SYS_w100, SYS_w50 or SYS_NOCLASS will almost surely be
  unresolved; the model-level dose curve cannot say what a Challenger match is worth.

## MUST-FIX before any SYS arm is built (M1–M4) or any dev score is read (M5)

### M1. C1's identity gate has not passed on the final code

* **What is wrong** (Observed). SPEC §10 makes CP1 conditional on "the C1 and C2 identity gates pass". C2's gate passed
  for the 22 joint-solve inputs (`system/ios_layer/gates/identity_IDENTITY_m1.json`). C1's has not run:
  * `system/arms/IDENTITY/` holds no `model_frame.parquet` and no `gates/` (23:33 UTC); the build's last finished step
    is `ufc_stageB_adjperf` at 23:15 UTC (`arms/IDENTITY/chain_lane1r.json`);
  * `C_layer.md` §"In short" still reads "G1 identity: RESULTS_G1";
  * the IDENTITY build runs an earlier copy of the layer (`C_layer.md`, "What it does not show": the copy of 20:31 UTC;
    `tnr_sys1`'s copy hashes `932789fd…`). The final `level_layer.py` (`0b99b046…`, 23:19 UTC) changed `weights()`,
    the validity masks, `missing_params` and the ratings hook since; it was checked only on a 2024–2026 slice and by
    unit tests.
* **Why it matters** (Inferred). "Inert at the identity settings" is an inference about code paths. G1 exists to make it
  an observation: every later reading is "arm minus reference", and an identity leak would be read as an effect.
* **Fix** (Suggestion). Build IDENTITY_ALL (C1's and C2's patches, the final copies of both modules, which
  `system_arms.arm_config` already defines) and pass G1: the 58 inputs bit for bit on all 67,226 matches, the tuned
  constants the reference's, and C2's end-to-end check (the 22 IOS columns equal `ios_layer/inputs/IDENTITY.parquet`).
  Record the result and the module hashes in the CP1 addition.

### M2. The joint solves' final hooks: ready at 00:29 UTC; what remains is the record

* **Status** (Observed, status 00:29 UTC; `arms/READY_ios_hooks.txt` of 00:29). C2's final module `077c760a…` is in
  READY, tested against `level_layer.py` `0b99b046…`. Its gates on B's frozen parameters passed, inputs only: SYS_w0's
  22 IOS inputs equal SEP_ALL's bit for bit on 67,226 matches; `match_timing/probe.py` and `surface_ios/probe.py` with
  SYS_BOTH's settings (form b, fitted w_joint) move 0 earlier matches at four cuts; the mapping check for SYS_w0 holds
  (2.2e-15). SYS's own lane-3 mapping check was still running. Before 00:29 (when E audited the code) the module was
  changing (`d4c3d29f…` at 23:23, `077c760a…` at 23:35), and READY named `d49a2511…`.
* **What remains** (Observed):
  * SYS's config does not name the joint-solve level term: `system_arms.py:271-275` sets `translate`, `weight
    "fitted"`, `solve_w "w_joint"` but no `ios_level_term`, so SYS gets whatever `LEVEL_TERM_DEFAULT` is
    (`level_layer_ios.py:139`, now "fixed_effect").
  * Form (b) now uses A's `delta_levels` of the solve's serve-side statistic only (`level_layer_ios.py:291-302`), where
    C2's report (§2) described the union of the two inputs' levels (men's holds: CH, CHQ, against `iosD_hold`'s TQ, GSQ,
    CH). The docstring calls it the lead's ruling; it is not yet written anywhere dated.
  * SYS's lane-3 mapping check, and C2's end-to-end check on C1's built SYS (its 22 IOS columns equal
    `ios_layer/inputs/SYS.parquet`), are still to come.
* **Fix** (Suggestion). The CP1 addition records `077c760a…`, the level rule (the serve-side statistic's δ levels) and
  that SYS relies on the default `ios_level_term` (or SYS's config names it); C1's gates on SYS include the end-to-end
  check. This item no longer blocks the build once it is recorded.

### M3. Decide and label the results channel: ITF results in Elo

* **What is wrong** (Observed).
  * SPEC §3: "ITF results stay in Elo as today". The pre-registration: SYS has "w_results fitted", with no exception.
    C1 implemented the lead's ruling: B's fitted w_results at every lower level, ITF and ITFQ included
    (`system_arms.py:268-272`, `level_layer.py:19-20`).
  * B's walk-forward choices (`relationship/elo_w_results.csv`, seasons 2013–2024): men's ITF 0.25–0.5 and ITF
    qualifying **0 in every season**; women's ITF 0.5–0.75. So SYS changes `elo_overall`, `elo_surf_offset` and
    `elo_games` for every season since 2010, not only the box-score inputs.
  * It is the largest single gain B measured on Elo's own log loss: men's ITF at 0.25, +1.05 [+0.47, +1.63] mLL
    (`relationship/elo_grid.csv`).
  * No arm separates it. SYS_w0, SYS_w50 and SYS_w100 vary the box-score w only (`system_arms.py:276-277`);
    SYS_NOCLASS keeps the fitted w_results; SEP_ALL sets every w_results to 0.
* **Which governs** (Inferred). The pre-registration says "w_results fitted" and says nothing about ITF results; SPEC
  §3 says they stay as today, and SPEC §1 makes the SPEC binding until the lead changes it in §12. Read together, ITF
  results stay at 1 and the other levels are fitted. The ruling in C1's code departs from that and is not in §12.
* **Why it matters** (Inferred).
  * The pre-registered decomposition reads "SELECTED against REF_noITF: the Challenger and qualifying part". Under the
    ruling it also holds the ITF results' Elo discount.
  * A SYS gain could come from Elo, which the owner's thesis treats as a priced-in control, rather than from the
    per-statistic relationship the study is about. The readings could not tell which.
* **Fix** (Suggestion), in the CP1 addition, before SYS is built. Either:
  * (a) ITF and ITFQ w_results = 1 in every SYS-family arm, as SPEC §3 says (C1's `weights()` takes the value from B's
    rows; a config key or a params view with those rows at 1 is needed); or
  * (b) keep the ruling, amend SPEC §3 in §12, relabel the decomposition, and add one separating arm read as a
    pre-registered secondary: SYS_RES1 (SYS with every w_results = 1), or the cheaper RES_ONLY (the reference with SYS's
    w_results and nothing else). Then "SYS against SYS_RES1" is the results channel and "SYS_RES1 against REF" the
    box-score relationship.

### M4. Freeze what decides the readings, not only what builds SYS

* **What is wrong** (Observed). Addition 2 §5 says the CP1 addition will hash `classes.csv`, `params.parquet`,
  `relationship.py`, `level_layer.py` and `level_layer_ios.py`. D's dev guard checks only the first two
  (`D_verification.md`, "The modes"). Not covered:
  * the scorer: `system_pairs.py` (the selection, the Holm reading, the recommendation, the speed rule, the strata) and
    the parts of `compare.py` and `candidate_pairs.py` it calls;
  * the fit queue's copy rules (`system_fits.py`);
  * how SYS's config is written and which builder lines are hooked: `system_arms.py` (`phase2_config`: the floor,
    `missing_params`, `solve_w`, `ratings_level_term`, `itf_box`), `system_sandbox.py` and the patch diffs;
  * `params_noclass.parquet` (SYS_NOCLASS's parameters; it has its own `.sha256` but is not in the list);
  * for addition 1's arms: `candidate_stage0.py` and C0_now's tables.
* **Why it matters** (Inferred). The scorer can change after the dev scores are read and leave no trace. That is the
  one route by which a choice could follow the scores.
* **Fix** (Suggestion). List these files' SHA-256 in the CP1 addition; `system_pairs.py` refuses `--dev` and `--holdout`
  when its own hash (and compare.py's) differs from the addition's, as it already does for the classes and parameters.
  Record each built arm's layer copy (SEP_ALL and REF_noITF were built with earlier copies; see S5).

### M5. The scorer does not implement addition 2 (fix it, then freeze it in M4)

The scorer's audit was delegated to a sub-agent of E and its load-bearing items re-checked by E (Observed, line numbers
in `src/eda/lower_level_evidence/system_pairs.py`; synthetic probes in `audit/D_scorer/probe_scorer.py`; no 2025–2026
outcome read). The file was last written at 20:58:32 UTC; addition 2 is from 21:06:25 UTC.

* **"No secondary is worse" is still D's literal reading, with no Holm correction** (`:793-798`, `recommend` `:816-830`;
  no "holm" anywhere in the file). Every holdout and pooled row of every arm, tour, stratum and season counts at its raw
  label. Addition 2 §3 restricts it to eight men's readings of SELECTED against REF, Holm-corrected at 5%. In the
  probe, two synthetic cases give "unresolved" where addition 2 recommends SELECTED (a women's SYS_w0 row reading worse;
  one of the eight raw-worse at z = −2.3 but not worse after Holm).
* **Holm's p-value is not defined anywhere.** With z = −2.75 and 22 blocks, a two-sided normal p (0.0060) passes Holm's
  first step (0.00625) and a two-sided t(21) p (0.0120) does not. That choice would otherwise be made after the
  readings. *Suggestion:* two-sided, on the t distribution with blocks − 1 degrees of freedom (the one the 95%
  intervals use), so a Holm-worse reading is always raw-worse; the lead pins it in the CP1 addition.
* **The 2026 speed rule is a free CLI choice** (`--speed-missing` has no default, `:917-919`; the holdout refuses
  without it, `:314-316`). Addition 2 §1 fixes "zero" for the primary and every reading. The "drop" path removes men's
  matches only (`speed_gaps`, `:255-266`: 416, not the 909 addition 2 names; 493 are women's), and both paths write the
  same files, so the sensitivity run would overwrite the primary. *Fix:* force "zero"; compute the 909-match drop
  sensitivity in the same run under separate keys.
* **A selected arm with a missing fit is dropped silently** (`:775`); the primary becomes None (`:789`) and
  `recommend()` returns "REF (no change) … REF was selected on dev" (`:822-823`). *Fix:* the holdout refuses unless
  SELECTED, REF and REF_noITF hold all 32 checked fits.

## SHOULD-FIX

### S1. Fitted w above 1 is an artefact of the pool prior: cap it

* **Observed** (`relationship/params_dev.parquet`, seasons 2013–2024). 26 of 1,369 fitted lower-level cells exceed
  1.5; 18 are men's `def_bp_faced_pg` (break points forced per return game). At Challengers its w is 2.47, 2.79, 2.82,
  2.80, 2.70, 2.30, 2.19, 2.28, 1.90, 1.58, 1.46, 1.35 (2013–2024), and the unshrunk w sits at the bound 3.0 in
  2013–2021. Its serve-side mirror, `bp_faced_pg` (the same break points seen from the server), reads 0.51–0.75 at
  Challengers.
* **Observed** (B's own `relationship/dev_fits.parquet`, men, 52 weeks). With a prior mean per home tier (F5ml) instead
  of one pool mean, `def_bp_faced_pg`'s free w at Challengers falls from 3.0 to 1.69–2.63 (2013–2021), from 2.35 to 1.46
  (2022), from 1.78 to 1.14 (2023) and from 1.61 to 1.03 (2024). The fitted main-tour tier's mean lies 0.25–0.81 log
  units above the Challenger tier's (2013–2024).
* **Observed** (`audit/shrinkage_target_atp_CH.csv`, `audit/scripts/e_shrinkage_target.py`; E's recomputation of B's
  DerSimonian–Laird step equals B's `w_level_mean` in all 12 seasons). The boundary cell also lifts every statistic's
  shrinkage target at men's Challengers: the level mean is 0.61–0.82 with it and 0.58–0.72 without it (2024: 0.619
  against 0.584; 2013: 0.812 against 0.713), and τ² falls by a fifth to a half without it. So B's headline "a
  Challenger point is worth 0.63 [0.54, 0.79]" is pulled up a little by the same artefact.
* **Inferred.** w does two jobs in the credibility average: the exchange rate, and the shrinkage of Challenger-based
  players toward a pool mean that does not fit them. A large w lets their own evidence escape the prior. Transplanted
  into the builders, it makes a Challenger match weigh 1.4–2.8 main-tour matches in `formdef_bp_faced_pg` (step 3)
  and in `form_bp_faced_pg`'s opponents' norms (the adjperf norms read `def_bp_faced_pg`, `level_layer.py:127-144`).
  That is not an exchange rate.
* **Fix** (Suggestion), pre-score and cheap. Cap fitted w at 1.5 (SPEC 6.3's numeric range) in the layer, by a ruling
  in the CP1 addition, or state why B's cap of 3 stands. B's own dose curve says a uniform 1.25 is worse than 1 for men
  (−0.006 [−0.009, −0.002]), and fitted w adds +0.006 over w = 1 (unresolved, P 0.97), so the cost of a cap is
  negligible. The lifted target (+0.025 to +0.067 in 2019–2024) would need B's refit to remove; it is small enough to
  record rather than refit, and the final document should quote B's per-level w with it.

### S2. δ is the predictor's forecasting term, not "the level's conditions"

* **Observed** (`audit/rederive_spw_atp_2024.json`, `audit/rederive_spw_atp_2019.json`; men, serve points won,
  Challengers). The same player's d-weighted Challenger mean minus his main-tour mean in the same season, after γ × gap
  and the surface, on each season's fit window:

  | Season's parameters (fit window) | Same-player residual (E) | B's δ | E's re-fit of B's model: δ, w_free (B's w_free) |
  |---|---|---|---|
  | 2019 (2013–2018) | −0.012 [−0.021, −0.002], 933 player-seasons | −0.037 [−0.058, −0.017] | −0.036, 0.491 (0.491) |
  | 2024 (2018–2023) | −0.039 [−0.049, −0.030], 887 player-seasons | −0.081 [−0.102, −0.064] | −0.081, 0.575 (0.575) |

* **Inferred.** B's δ is two to three times the level residual in both windows, so half or more of it is not the
  level's conditions: it also absorbs selection (players arrive on the main tour after good runs) and the interplay
  with k, w and the half-life. Both quantities drift between the windows, so B's walk-forward refit is warranted.
  B_relationship.md §4 ("δ is the level's conditions after the opponent gap … Challengers are more return-friendly
  and slower") over-claims.
* **Fix** (Suggestion). In B's report and the final document, call δ "the predictor's level term" and do not cite it as
  conditions evidence. No code change: the arms test whether this δ helps inside the builders.

### S3. The selection rule switches on noise about a third of the time; write the reading down now

* **Observed** (E's simulation, `audit/power_cp1.json`, `audit/scripts/e_power.py`). With seven challengers and no true
  difference from SYS, the chance that at least one reaches P(better than SYS) ≥ 0.90 is 0.52 (independent readings),
  0.34 (correlation 0.5), 0.19 (0.9).
* **Observed.** R_S2's and FP's dev readings are already published (first run: R_S2 against the reference, men,
  +0.152 [−0.052, +0.357], P(better) 0.93), so the dev comparison against R_S2 is not blind, and changing the
  threshold now would not be either.
* **Suggestion.** Keep the frozen rule. State before the dev readings that a switch away from SYS is weak evidence,
  that the selected arm's dev reading is biased upward (it was the best of eight), and that only the holdout primary
  is free of the selection.

### S4. The newcomer prior was rejected in one form only

* **Observed** (`B_relationship.md` §5; `relationship.py:827-844`, `:912-916`). F5 takes each target's prior from the
  newcomer mean of its home tier; main-tour and qualifying tiers fall back to the pooled newcomer mean, so every
  established main-tour player is shrunk toward the newcomers' mean (men's serve points 2022: +0.381 against +0.167).
* **Inferred.** "Worse overall" was close to built in; the rule (fixed at 21:17 UTC, before any score) was applied
  correctly, but it tested this form, not the owner's idea. SYS therefore has two of SPEC §3's three components.
* **Suggestion.** The final document says "this form of the newcomer prior was worse", never "the newcomer prior does
  not help", and carries B's own post-hoc form (newcomer means for lower-tier players only) to P7 as a pre-registered
  candidate.

### S5. Arms built with earlier copies of the layer

* **Observed** (status 23:19 UTC; E hashed the sandboxes' copies at 23:53 UTC). The three sandboxes hold three
  different copies of `level_layer.py`, none of them the final `0b99b046…`: `tnr_sys1` (IDENTITY) `932789fd…`,
  `tnr_sys2` (SEP_ALL) `e091a8e8…`, `tnr_sys3` (REF_noITF) `b443a37f…`. C1 calls the differences inert for these
  configs.
* **Suggestion.** Show it: G2 on each arm with the final code, or a one-family rebuild compared bit for bit; record each
  arm's copy hash in the CP1 addition.

### S6. Departures from SPEC §3 that the CP1 addition should state

* **Observed.** `ratings_iid`: SPEC §3 says "a level offset, and K × w"; built: w_joint and no level term
  (`level_layer.py:858-866`, config `ratings_level_term "none"`). The joint solves: one weight per observation, w_joint,
  the mean of the two sides' w (`relationship.py:1794-1806`). The forms: the norms' γ is the allowed view's (A's
  `def_<s>` or the mirror statistic), which SPEC §3 leaves open.
* **Suggestion.** Record each as a ruling; none is wrong.

### S7. B's planted-recovery tests check the mechanics, not the estimand

* **Observed** (`test/lower_level_evidence/test_relationship.py:109-142`). The planted targets are drawn from the
  predictor's own formula; the histories come from a world in which a Challenger row carries the same information as a
  main-tour row. The test shows the optimiser returns its own parameters. It cannot show that w measures information,
  and it cannot catch S1 or S2.
* **Suggestion.** Before the final document says "a Challenger point is worth 0.63 of a main-tour point", add a world
  with noisier Challenger evidence, tier-specific means and selection, and show what w and δ recover.

### S8. The scorer's other gaps (D)

Observed (line numbers in `system_pairs.py` unless named; E's sub-agent, probes in `audit/D_scorer/`):
* **The dev guard checks two files** (`:107`, `:217-232`): not `relationship.py`, `level_layer.py`,
  `level_layer_ios.py` (addition 2 §5), not `params_noclass.parquet` (SYS_NOCLASS's), and not each SYS-family arm's
  `layer_config.json` and `cp1_addition` record (`system_arms.py:271-275`). Part of M4.
* **Fit provenance is not checked at scoring** (`complete()` `:249-250` checks existence only;
  `serve_speed_tabpfn/forecasts.py:117` skips the frame hash for "model"; `system_fits.check_fits` lists fits from
  another frame and still passes, `:614-619`). A fit left over from before a rebuild would be scored.
* **"Opened once" is not enforced:** dev can rewrite `selection.json` after the unlock (`:742`); the unlock does not
  hold `selection.json`'s hash (`:185-214`); the holdout can be re-run over its outputs. *Fix:* the unlock records
  `selection.json` and `dev/pairs.csv`; the holdout refuses if `readings.json` exists; dev refuses after the unlock.
* **No rule for a challenger that cannot be built.** `select()` returns "incomplete" (`:525-527`) but dev still computes
  and prints every partial reading (`:726-761`). *Fix:* pre-register the missing-arm rule; dev prints nothing until SYS
  and the seven challengers are complete and checked.
* **The C0_now arms can never pass the frame check** (`system_fits.py:334`: `same_ids_in_order` is None for them, and
  `system_fits.py:401` requires it to be true); NEW_ASIS and NEW_SYS_BOTH would never be fitted, and addition 1's three
  C0_now pairs would read "not scored" (`system_pairs.py:692`).
* **Addition 2 §2 is not implemented:** dev never reads SYS_BOTH against SYS_BOTH_ITFASIS (`:103`, `:723`), though
  women's inputs may differ from 2022.
* Smaller: a tie in gain goes to the first challenger in list order (`:519`); the Φ/t disagreement is flagged at the
  selection but not at the recommendation's 0.80 (`:828`); the zero speed fill applies to each model's own column
  (`:326-328`) rather than to the same 909 ids; the holdout's compare.py cross-check cannot run (`:806-812`);
  `sides.parquet` (the strata) is not hashed between dev and the holdout.

Checked and correct (Observed): the seven challengers and nothing else enter the selection (`:110`; SYS_w25/75 and
SYS_PLACEBO never do); signs; gain = −(SYS against C), P = Φ(gain/se) ≥ 0.90, the largest gain, REF if P < 0.50
(`:509-526`); Φ decides and the t value is kept; dev reads no 2025–2026 result, fit or label (`:282-283`, `:322`,
compare.py `:103-108`, `:219`); the lock lists the additions on disk at run time (`:141-145`, `:202-212`); addition 1's
pairs and thresholds (`:101-105`, `:639-661`); the strata are pre-match counts (`composition.py:26-36`, `:309`); the
pooled reading is one population with four-week blocks across both periods (`:782`); SYS_PLACEBO and SYS_S2 as
pre-registered (`system_fits.py:637-655`, `:687-714`); fits are copied only when inputs to 2024 are identical or an
exact refit matches (`system_fits.py:291-315`, `:720-840`).

### S9. F's candidate Stage 0 (C0_now): two blockers for phase 3, and what the rule test can measure

Audited on the build of 23:18 UTC (297,932 new matches; `stage0_matches` sha256 `c3aa6afb…`; results archived in
`audit/F_c0now/build_231847Z/`) and re-checked on F's rebuild of 00:12 UTC (297,817 new matches, `6c7370c4…`; results
in `audit/F_c0now/`). F then fixed the crosswalk and other items E reported and started attempt 8 at 00:23 UTC, not
yet audited. Work by a sub-agent of E; the cross-tour count was repeated by E on both builds. No 2025–2026 outcome was
read for any performance purpose.

**Blockers before NEW_ASIS or NEW_SYS_BOTH is built** (`system_arms.py:236-238` refuses them today):
* **Players get ids of the other tour** (Observed). TennisLive numbers players separately per tour, and 1,948 of its
  ids are used on both (100093 is Daniel Fennis on the ATP pages and Kennedy Hutto on the WTA pages); the crosswalk
  and `resolve_ids` matched the bare id.
  * Build of 23:18: 16,151 player rows of new matches hold an id of the other tour (E's count: 15,715 `wta:` ids in
    men's matches, 375 `atp:` ids in women's); 72 are frame players, with 1,035 rows; e.g. `wta:201696` (Laura
    Siegemund) receives 49 men's matches as "Michael Shabaz" (`build_231847Z/a7_results.json`).
  * Rebuild of 00:12: still 6,159 such rows by E's count (6,235 with the other id namespaces), 30 frame players with
    140 rows, reaching 50 women's frame matches in 2026; e.g. `wta:223253` (Alexandra Eala) receives men's matches as
    "Lukas Brandl" (`a7_results.json`).
  * In NEW_ASIS these rows would enter women's Elo, workload and forms, and leave the men's histories they belong to.
  * *Fix:* match on (tour, source id) in `crosswalk`, `resolve_ids` and `Names`, rebuild, and add a build check that
    every player row's id tour equals its match's tour. F confirmed it at 00:17 UTC (ids keyed `<tour>|<id>`, a test,
    a build that refuses a cross-tour id) and was rebuilding (attempt 8, from 00:23). The blocker stands until the
    rebuilt C0_now is re-audited.
* **The expected unevenness is not written** (Observed). Addition 1 requires it from F before these arms are scored;
  `F_rule_data.md` is a stub and no status line holds it. The figures exist (`frame_reach_by_tour_season.csv`).

**SHOULD-FIX: what NEW_ASIS against REF would measure** (Inferred from counts, rebuild):
* **Mostly ITF-qualifying results, and mostly women.** New matches, with box scores in brackets: men's ITFQ 118,628
  (107) in 2018–2024 and 40,352 (355) in 2025–2026; men's ITF 9,976 (1,446) in 2025–2026; women's ITFQ 66,388 (0) in
  2010–2017, 16,151 (2) and 29,149 (480) after. A new match within 365 days reaches 1.4–5.9% of men's frame matches in
  2018–2024 (5.1% in 2025, 6.6% in 2026) against 25–53% of women's in 2013–2016 and 59% in 2026. NEW_ASIS against
  REF, men, will be unresolved by construction; and since SYS's Elo rule sets men's ITFQ results to 0 in every season,
  NEW_SYS_BOTH against SYS_BOTH, men, is close to a null comparison.
* **2026 is mostly the reference's publication lag, not the rule.** Men's ITF in 2026: 6,894 in the frozen data,
  8,246 added; women's ITF qualifying in 2025–2026: 0 frozen, about 29,150 added. A holdout reading there measures data
  completeness.
* **The periods are not separable.** One arm holds every addition, so the holdout reading mixes the 2010–2024
  additions (through training inputs and ratings) with the 2025–2026 ones. *Suggestion:* a C0_pre (additions dated
  before 30 Dec 2024): NEW(C0_pre) against REF on dev and the holdout, NEW(C0_now) against NEW(C0_pre) on the holdout;
  2026 per tour with and without the lag-filling rows. A new arm needs its own dated addition before any NEW score.
* **Box scores selected by player.** 1,450 frozen men's ITF matches of 2016–2024 gain box scores from SofaScore's
  career pages, almost all from about ten careers (Sanchez Izquierdo 232, Onclin 223, Choinski 192 with 23 frame
  matches, Adam Walton 79 with 74 frame matches); no other men's ITF box score exists before 2025. List them in the
  unevenness note; run NEW_ASIS with and without them.
* **Elo is re-tuned on C0_now** (`stage1_baselines.py:27,72,229`), while SPEC §3 keeps the builders' tuned constants
  the reference's. Decide which NEW_ASIS uses (the template would re-tune; the SPEC pins) and record both K sets.

**SHOULD-FIX: data integrity** (Observed):
* **WTA-site 2026 records file one match under several events** (64 groups, 129 matches, in the 23:18 build, all
  women's holdout; two groups remain after F's rebuild, with an arbitrary copy kept); 163 rows sat a week before the
  site's own date. *Suggestion:* leave out WTA-site events from 31 Aug 2026 (the snapshot is of 24 Sep) and widen the
  window to both weeks where the site's week differs from the mapped event.
* **The identity repair moves 12,189 new-match rows between two frozen ids,** in both right and wrong directions
  ("Tatjana Malek" rows leave Tatjana Maria's id for a one-match id; "Klaudia Gawlik" rows leave Cristina Madalina
  Stancu's, a correction). Hand-check those moves (`a4_results.json`).
* **Some crosswalk names are wrong** (e.g. TennisLive "Jake Van Emburgh" to "Toby D Boyer", 75 links; "Rayan
  Ghedjemis" to "Rayane Roumane", 98 of 112). One id in two main draws in one week: 0.26% of player-weeks with new
  matches (outside the bad weeks), against 0.009% frozen. 1,039 new ids share an exact name with a frozen player.
* **Boundary week:** 105 new matches of events from 30 Dec 2024 carry year 2024, while the frozen data labels that
  week 2025. Label them 2025 or split dev and holdout by date.
* NEW_SYS_BOTH needs a ruling on the strength of new matches, which have no reference pre-match Elo (C1, §9 Q7;
  `system_arms.py:106-124`); D's frame check cannot pass a C0_now arm (S8). Walkovers: the additions drop all of them,
  the frozen data keeps 4,102 (they move no rating).

**Checked and correct** (Observed, both builds): all 873,437 frozen ids present with the same columns and types; only
1,644 frozen matches differ, exactly those the box-score layer filled, in their box columns only; all 67,226 frame
matches unchanged; no new main-tour or team match; the odds link reaches main draws only (`stage1_odds.py:71,161`);
the frozen timeline identical in all 28 columns; every new window finite, ending after it starts, 3 days wide (wider
than the 1–2 days the frozen timeline gives the same sources), none rejected; `history.py` (read-only; it only
prints, `history.py:167-175`): future 0, updated 0, new past 297,932, dropped 0, revised 1,644, template refused, as
it should be for a candidate; pairs a week apart (918 new against frozen, 2,548 new against new) repeat a score
before the holdout in 1.5% and 1.8% of cases, the same as frozen pairs (1.5%), so they are rematches, not copies;
retirements kept as retired, at near-frozen shares (ITFQ 2.8% against 2.3%); volumes plausible (men's ITFQ 12.8–23.4
thousand a year in 2018–2025).

## NOTES

* **N1. The classes look ahead within dev** (Observed, `A_classes.md` §1: seasons 2013–2024). OPP/ENV and the δ levels
  are fixed from data that include the dev seasons. Holdout readings are clean of it; dev readings of SYS against
  SYS_NOCLASS are not. B measured the classes' value at −0.000 (P 0.44), so the effect should be small.
* **N2. B's method choices used 2019–2024 statistic-level outcomes** (Observed: the newcomer-prior rule reads 2019–2024
  contrasts). The dev model readings are not independent of the method; only the holdout is.
* **N3. Unfitted levels get w = 0 for good** (Observed, `params_dev.parquet` `fitted`). With each row on its own season's
  parameters, men's Challenger-qualifying box scores of 2016–2017 never enter SYS (fitted from 2018); women's WTA 125
  of 2013–2016 and women's Challenger qualifying in every season never enter SYS_BOTH.
* **N4. w per unit in per-match sums** (Inferred). B's w is per point or game; the forms' step 3 and the IOS rows weigh a
  match by units^τ. Where τ = 0, a Challenger match gets w where `w_per_match` would apply (men's serve points: 0.563
  against 0.497).
* **N5. Grid edges** (Observed). The half-life is 26 weeks, the shortest tried, in 11 of 12 seasons; w_results sits at
  the grid's top, 1.25, for men's TQ, GSQ and CHQ in most seasons (`elo_w_results.csv`). The optima may lie beyond.
* **N6. Precision is not information** (Inferred). The predictor weighs a row by its units d, ignoring r(1 − r) (or λ
  for the per-game counts). Part of w's distance from 1 at low-rate statistics is precision.
* **N7. The builders' main-tour rows are not opponent-adjusted** (Observed, `level_layer.py:45-54`: MAIN rows T = 0),
  while B's predictor adjusts them (`relationship.py:554-576`). w and δ were fitted in that context.
* **N8. SYS against SYS_PLACEBO "better" does not mean SYS helps** (Observed, first run,
  `candidates/results/pairs.csv`). FP_placebo against the reference, men: −0.114 [−0.233, +0.005], P(better) 0.03; FP
  against FP_placebo: +0.197 [+0.059, +0.335] while FP against the reference read +0.083. A random change of that size
  costs about 0.1 mLL, so beating the placebo is easy.
* **N9. Men-only arms move women's forecasts** (Inferred). The fit is joint over both tours (`tour` is an input), so
  women's readings of men-only arms carry the fit's spillover (first run: FP, women, −0.040 [−0.154, +0.073]).
* **N10. 27–29 Dec 2024** (Observed). Season-2025 events start then; they are holdout by season but not by
  `common.in_holdout` (date ≥ 30 Dec 2024). Every module E read filters by season too; C1's G5 slice flipped them
  mechanically (no performance read). E's probe excluded them.
* **N11. The layer's records pool every season** (Observed, `level_layer.py:556-562`, `:615-623`). Once SYS is built,
  `layer_calls.jsonl` holds w means, T means and "fitted w above 1.5" warnings over all rows, the sealed 2025–2026
  parameters included. Pooled, they say little; nobody should break them down by season before the unlock.

## Checked and found correct

* **The pre-registration** (Observed). The three hashes match their `.sha256` files; written 20:01:24, 20:51:42 and
  21:06:25 UTC, each before any score it governs (the first score of this run, B's statistic-level `dev_fits.parquet`,
  was written at 21:27 UTC; no model score exists). Addition 1's text says "about 20:45": its file is from 20:51:42,
  and nothing was scored in between (status log).
* **B's rule timing** (Observed). Fixed at 21:17 UTC; the dev run's first output with scores (`dev_fits.parquet`) is
  from 21:27; pass 1 (`dev_pass1.parquet`, 21:12) holds fits only (`relationship.py:956-986`), and nothing is logged
  with a score before (`relationship.py:1248-1290`).
* **B's comparisons measure what they claim, at the statistic level** (Observed, `relationship.py:849-866`,
  `:1019-1113`, `:1139-1177`). Every formulation is fitted and scored in one predictor on the same targets,
  walk-forward, player-clustered; F3 against F2b isolates the per-match gap term (men +0.038 [+0.025, +0.051]); the
  newcomer-prior rule of 21:17 UTC was applied as written (men: low exposure better, overall worse; women: unresolved,
  worse), so dropping it follows from B's evidence (S4 is about the form tested, not the rule). They forecast main-tour
  box-score statistics, not match results.
* **B's walk-forward** (Observed). Fit targets, E_ref, the level counts and role 08's offsets all use lf + 1 ≤ the
  season's first es (`relationship.py:385-497`); histories are each player's earlier rows; the mechanical mode loads
  seasons ≤ 2025 for 2026 only and refuses changed code (`:1899-1953`). `fit_through` + 1 ≤ cutoff for all 3,108
  statistic rows (largest −13 days). The independent re-derivation reads seasons ≤ 2023 (≤ 2018) and reproduces the
  2024 (2019) fit, so those fits used nothing later.
* **The parameters' seasons** (Observed). No match labelled Y + 1 starts before the last main-tour match of Y
  (2010–2025, both tours), so the own-season convention never hands a match parameters fitted after it starts; the
  2013 floor serves 2010–2012 rows, read only by frame matches from 2013 (frame 2013–2026).
* **A's γ and season_cutoff** (Observed). Main-tour rows with lf + 1 ≤ through (`classify.py:322-344`); B's cutoffs equal
  A's for 2013–2026 (`dev_checks.json`).
* **The layer's cross-player changes, with real parameters** (Observed; E's probe,
  `audit/scripts/e_g5_realparams.py`, results in `audit/g5_realparams/`). C1's G5 design (`system_g5.py`: the
  2023–2024 slice, four cut days, every match with es > D reversed and its box-score counts exchanged, Stage 1's Elo
  recomputed on the flipped history) run with three changes: B's `params.parquet` rows of 2024 and earlier (a copy,
  hashed); the repository's final `level_layer.py` (`0b99b046…`) injected in place of the sandbox's copy; the slice
  ends on 26 Dec 2024, so no season-2025 match is read. Config: SYS's settings for `points_52w` and the forms
  (translate, fitted w, A's classes), both tours. **0 protected pool matches moved at every cut** (13,758 / 19,744 /
  29,141 / 31,163); later matches moved 22,156 / 16,482 / 7,382 / 5,378; with the layer on, 33,331–34,764 pool matches'
  inputs differ from the layer off, so the path was exercised. 541 s. Parameters are fixed tables, so a flip probe
  cannot see a look-ahead in their seasons; that is covered by the fit_through and season-label checks above.
* **C2's form (b)** (Observed, `level_layer_ios.py:816-1067`). β is solved in each snapshot from released rows only;
  the incremental step nets a gap row's y with β at that row's own snapshot.
* **The ITF exclusion** (Observed). `weights()` gives ITF and ITFQ box rows w = 0 under "exclude" in every box-score
  family (`level_layer.py:530-566`): points_52w multiplies the counts, the forms' norms and step 3 the weights,
  `ratings_iid` the counts, the IOS drops m = 0 rows; ITF rows are never translated (`:585`).
* **`missing_params` "untouched"** is set for SYS_BOTH and SYS_BOTH_ITFASIS only (`system_arms.py:280-282`); SYS has
  every men's key (`params_dev.parquet`: all levels, every season), so it runs with "error".

## What the readings will and will not be able to show (written before any reading)

*Inferred* from the first run's intervals (`candidates/results/pairs.csv`, men, 2020–2024, both stages, seeds 0–3) and
the frame's counts.

| Reading | Typical SE (mLL) | Smallest difference it can call |
|---|---|---|
| An arm that changes inputs, against REF, men, dev (FP, FP_half, F, P: 0.029–0.041) | 0.03–0.04 | 0.06–0.08 |
| An arm that adds inputs (R_S2, R_L, FP_L, against REF: 0.10–0.11) | 0.10 | 0.20 |
| The holdout primary, men (4,810 matches against 11,672) | about 0.063 | about 0.124 |
| 2020–2026 pooled, men (16,482 matches) | about 0.034 | about 0.067 |

* **The primary.** If SYS is as good as the first run's FP (+0.083 on dev), the holdout reads "better" about 26% of the
  time and P(better) ≥ 0.80 about 68% of the time; the pooled 2020–2026 reading is "better" about 68% of the time. An
  unresolved holdout will not rule out a gain of that size.
* **Will not resolve:** SYS against SYS_w100 and SYS_w50 (B: fitted w adds +0.006 milli per unit over w = 1); SYS
  against SYS_NOCLASS (B: −0.000); probably SYS against R_S2 and SYS_S2 against SYS (SE about 0.10). The model-level
  dose curve applies one w to TQ, GSQ, CH and CHQ together, so it cannot answer "is a Challenger match worth 0.5–0.7".
  That answer is B's statistic-level per-level w, with S1, S2 and S7 attached.
* **The strata** (fewer than 10 main-tour results; share gap ≥ 0.5; falsification) hold a sixth to a quarter of the
  matches each (first run, both tours, dev: 5,913, 5,619 and 3,652 of 22,265; SEs 0.096, 0.080, 0.061). Scaled to the
  men's holdout, their SEs are about 0.13–0.20 mLL: Holm's eight readings (addition 2 §3) can flag only a large harm.
* **The decomposition** (Inferred). For men, ITF box scores exist only in 2025–2026, so "REF_noITF against REF" on the
  men's holdout is the as-is ITF box scores' effect, with the primary's SE. "SELECTED against REF_noITF" is the
  Challenger and qualifying part only if M3 is fixed.
* **Can show:** whether the frozen SYS improves on the reference by about 0.1 mLL or more for men, and whether that
  holds on 2020–2026 pooled; with M3 fixed, whether the gain is the results channel or the box-score relationship.

## Verdict

**CP1: pass with conditions.** Build no SYS-family arm until M1–M4 are done and written into the dated CP1 addition;
read no dev score until M5 is done and the fixed scorer's hash is in that addition (D's dev guard already waits for the
addition). S1 is a one-line, pre-score choice worth making in the same addition. The arms that need no parameters
(SEP_ALL, REF_noITF) may continue; their scores stay unread until the addition exists. Phase 3 (NEW_ASIS,
NEW_SYS_BOTH) waits, in addition, for the cross-tour identity fix and a clean re-audit of C0_now, F's written
expected unevenness, D's frame check for C0_now arms, rulings on the new matches' strength and on Elo's K (pinned or
re-tuned), and, if the lead wants the rule test to separate the periods and the publication lag, a dated addition
with a C0_pre arm (S8, S9).

What the CP1 addition should record, in one place: the full SHA-256 of `classes.csv`, `params.parquet`,
`params_noclass.parquet`, `relationship.py`, `level_layer.py`, `level_layer_ios.py`, `system_arms.py`,
`system_sandbox.py` and its patch diffs, `system_fits.py`, `system_pairs.py` (after M5) and `compare.py`; each built
arm's layer copy; the rulings (the 2013 floor; `missing_params`; the w cap; w_results at ITF and ITFQ; the joint
solves' w_joint and form (b) at the serve-side statistic's δ levels; no level term in `ratings_iid`); Holm's p-value;
the missing-arm rule; and the separating arm of M3 if chosen.

## What it does not show

* **No model-level reading exists,** so nothing here says whether the system helps.
* **The leak probes cover a slice** (2023–2024, four cut days). E's own covers points_52w and the forms with real
  parameters; the joint solves rest on C2's probes (with SYS_BOTH's settings since 00:29) and on E's code reading; Elo
  and `ratings_iid` rest on their being per-player passes with fixed per-season parameters, and on C1's checks.
* **The re-derivation covers one cell in two seasons** (men, serve points won, Challengers, 2019 and 2024). The w > 1
  finding rests on B's own fits (F4free against F5ml), not on an independent fit of `def_bp_faced_pg`.
* **F's C0_now was rebuilt during and after the audit** (attempt 8 from 00:23 UTC, with F's fixes for E's findings);
  S9's findings apply to the builds of 23:18 and 00:12 and to phase 3 (NEW_ASIS, NEW_SYS_BOTH), not to the SYS family.
* **The power figures are approximations** from the first run's arms; this run's arms may be noisier or quieter.

# Checkpoint 1b (CP1b): C0_now and C0_pre

Audited 01:32–01:47 UTC on 10 Oct, at the lead's request, before C1 builds any NEW arm. Builds audited: C0_now READY
01:07 UTC (the build of 00:23–00:50, 1,171,445 matches, 298,008 new) and C0_pre READY 01:30 UTC (1,079,197 matches,
205,760 new). E's scripts: `audit/scripts/e_cp1b_checks.py` (questions 1, 3, 4) and `e_cp1b_residuals.py` (question 2);
results in `audit/cp1b/`. Ids, names, dates and windows only: no outcome was read.

## In short

* **Verdict: the NEW arms may be built** on C0_now and C0_pre once a few small items are done or written down (§5): the
  two conflicting windows, the lead's ruling on Elo's K, the strength of new matches, and D's frame check.
* **The blocker is fixed** (Observed). No player row of any match carries an id of the other tour (0 of 2,342,890). The
  30 frame players hit before now receive only their own tour's rows (1,002 new rows, all same-tour), and the old wrong
  rows resolve to men's ids (e.g. "Lukas Brandl" to `atp:tl:67792`), none to a frame player.
* **The residuals barely touch the frame** (Observed; 1,879 frame players, 67,226 frame matches). At most 13 frame
  matches have an affected new row in the 365 days before them: 9 through minor-id splits (6 players, among them
  Coleman Wong, Allie Kiick, Tatjana Maria and Margarita Gasparyan), 3 through repair merges onto a frame player's id,
  1 through a possible reused source id (Rayane Roumane, 1 frame match). The wrong-given-name rows touch no frame
  player. Small enough for a fair test; fix the given-name rule and the minor-id repair in the next build.
* **The windows are leak-safe to the reference's own standard** (Observed), with 2 rows to widen. Every window is
  finite with lf ≥ es; every dated row's window holds its day (day − 1 to day + 1); all 159 undated rows dated a week
  apart get 14–15-day windows spanning both weeks; the frozen timeline is unchanged.
* **C0_pre is a clean cut** (Observed): every reference match; exactly C0_now's additions dated up to 23 Dec 2024 (the
  other 92,248 all from 30 Dec 2024); the same match rows, player ids and windows on every common match; it lacks only
  the 25 box completions of 2025–2026 reference matches.
* **The expected unevenness was fixed before any NEW arm** (Observed): `expected_unevenness.txt` hashes to `edcab8a7…`,
  file time 00:36:52 UTC (its text says "about 00:45"; harmless). It is based on the 23:17 build's dose and says so.

## 1. The blocker: ids crossing tours

*Observed* (`audit/cp1b/checks.json`).
* Player rows whose id's tour differs from the match's: **0** in C0_now (namespaces: `atp` 1,279,542 rows, `wta`
  1,063,090, `atpcode` 258, all reference rows).
* The 30 frame players of the 00:12 build's cross-tour rows (`audit/F_c0now/cross_tour_rows.csv.gz`): their 1,002 new
  rows in C0_now are all in their own tour's matches. The old wrong rows, found again by name, tour and event date
  (209 slots), now hold ids of their match's tour, and none a frame player's.

## 2. The residuals against the frame

*Observed* (`audit/cp1b/residuals.json`, `residual_slots.csv`). Per new-match player slot (596,016). "Frame matches
hit" = frame matches with an affected new row in the 365 days before them.

| Class (how found) | Slots | On frame players | Frame players | Rows within 365 days of a frame match | Frame matches hit |
|---|---:|---:|---:|---:|---:|
| Wrong player: a fuller or shorter name with another given name (route `name_subset`; F: about 19 wrong, 39 unsure) | 69 | 0 | 0 | 0 | 0 |
| Minor-id split: the repair moved the slot from the linked id to an id with fewer frozen matches | 2,224 | 96 | 6 | 38 | 9 |
| Repair merge onto a frame player's id (F's sample: 18 of 20 right, 2 unsure) | 122 | 122 | 11 | 46 | 3 |
| Possible relative or reused source id (same surname with unrelated given names, or men's entries sharing no name word: 36 crosswalk entries, mostly transliterations) | 1,113 | 41 | 2 | 19 | 1 |

* **The splits** (Coleman Wong 32 slots, James Trotter 26, Sherazad Reix 19, Allie Kiick 15, Tatjana Maria 3,
  Margarita Gasparyan 1) take new rows out of the frame player's history and give them to a minor id. They dilute the
  treatment (that player's history stays as in REF) and put nobody else's matches into it (Inferred).
* **The suspect crosswalk entries** include clear errors (TennisLive "Bogdan Seleznev" to Marc Saura Moragrega, 20
  links; "Rayan Ghedjemis" to Rayane Roumane, 98), but only Rayane Roumane (1 frame match) and Mingge Xu (1 slot) are
  frame players.
* **The physical-impossibility check** (an id in two main-draw events of one week, frame players): 62 of 4,777
  player-weeks with a new row (1.3%), against 0.97% of frozen-only player-weeks by the same broad rule (team events and
  overlapping weeks included). No strong excess of wrong joins on frame players.
* **Reading it** (Inferred). At most 13 of 67,226 frame matches (0.02%) see an affected row in the prior year, none
  through a wrong player. That cannot move a reading whose SE is 0.03–0.06 mLL. NEW_ASIS against REF is a fair test of
  the data as wired; the fixes belong to the next build, not before this one.

## 3. The windows

*Observed* (`audit/cp1b/checks.json`; F's union rule, status 00:22 UTC).
* All 298,008 new windows are finite with lf ≥ es; width (lf − es) 2 days at the median, at most 15.
* The 183,603 rows dated by the source: window = day − 1 to day + 1 (6 rows to day + 3); none excludes its day. F's
  calibration against the frozen timeline's exact days (TennisLive 99.0% the same day) is not re-derived here.
* **The union safeguard holds:** all 159 undated rows (WTA website) whose event the source dates a week apart from Stage
  0's get windows of 14–15 days, from 1–5 days before the earlier Monday to 3–6 days after the later one.
* Against the frozen windows of the same event and round (2,232 comparable rows): 1,674 contain the frozen round
  window; 246 end before the round's earliest frozen finish, by 1 day (74), 2 (156), 3 (15) or 5 (1), and 241 of those
  246 are against rounds the frozen timeline holds only with class windows, which the source's own day narrows, as it
  should.
* **Two rows conflict** with the frozen round. `atp|2026-9552|SF|…`: TennisLive day 20 Sep 2026, Stage 0's SF windows
  on 26 Sep; its result would count from 22 Sep, possibly four days early. `wta|2025-W-ITF-USA-2025-21|R16|…`: dated
  31 May, the round's frozen windows end 29 May; it reads the state up to two days late. *Fix:* give both the union
  with the frozen round's window. Both are lower-level holdout matches.
* The frozen timeline's rows are identical in C0_now.

## 4. C0_pre against C0_now

*Observed* (`audit/cp1b/checks.json`).
* All 873,437 reference matches are in C0_pre; its 205,760 new matches are a subset of C0_now's, the latest dated
  23 Dec 2024; C0_now's other 92,248 additions all date from 30 Dec 2024 (by tournament and by the source's event date).
* On every match the two hold: the same match rows except `has_box` on 25 reference matches (the box completions of
  2025 (16) and 2026 (9), absent from C0_pre), the same player ids, and the same windows (es, lf, width, exactness).
* So a C0_now arm and its C0_pre twin differ only through data dated from 30 Dec 2024. C0_pre's identity is C0_now's
  (a cut, not a rebuild), as F says.

## 5. Verdict and what remains

**The NEW arms may be built** (NEW_ASIS, NEW_SYS_BOTH, and C0_pre twins if registered), after:
* the two conflicting windows are widened (or written down as accepted);
* the lead rules on Elo's K for NEW_ASIS (the template re-tunes Stage 1 on C0_now; SPEC §3 pins the builders'
  constants) and on the new matches' strength for NEW_SYS_BOTH (C1, §9 Q7);
* D's frame check can pass a C0 arm (S8: `system_fits.py:334`, `:401`), and any C0_pre arm is registered in a dated
  addition before a NEW score is read (addition 1 names only NEW_ASIS and NEW_SYS_BOTH).

**Not blocking** (fix in the next build): the given-name rule of the `name_subset` route (69 slots, no frame player);
the minor-id repair (96 slots of 6 frame players, 9 frame matches); the suspect crosswalk entries (41 slots of 2 frame
players).

**What it does not show.** The hand-check precision is F's; E did not re-check links by hand. The calibration of
dated windows rests on F's measurement. The residual classes are found by rules: the "relative" rule is a heuristic
superset, and a wrong join that fits no rule shows only through the two-events-one-week check. Nothing here says
whether the new data helps the model.

# Checkpoint 2 (CP2): the dev readings and the selection

Audited 08:29–08:36 UTC on 10 Oct, on D's first dev run (08:09–08:28 UTC; `selection.json` `b5fbec82…`). E's scripts:
`audit/scripts/e_cp2_rederive.py`; results in `audit/cp2/`. E read results of seasons up to 2024 only.

## In short

* **Verdict: pass with conditions.** The lead may write the unlock once C1–C3 below are done (C2 is half done:
  addition 5 is hashed). None of them changes a rule or a reading.
* **The decision layer was applied exactly** (Observed). Re-derived from `results/dev/pairs.csv`: none of the five
  challengers reads "better" than SYS, and SYS against REF, men, −0.008 [−0.162, +0.145], is not harm, so SYS is
  selected, as `selection.json` says.
* **No 2025–2026 result was read** (Observed): no unlock, no holdout folder, every `summary.json` reads results through
  2024, every dev row is 2020–2024, and the code paths refuse later seasons without the unlock.
* **Timing is clean, and the switch must be reported** (Observed). The owner's file, its erratum and additions 4, 4b
  and 4c were hashed between 02:55 and 03:57 UTC; the first score came at 08:09. The registered rules would have
  selected SYS_S2 (P 0.95). Addition 4's own seven-challenger rule already gives SYS, so the erratum did not decide it;
  the threshold did. That threshold was set knowing R_S2's published first-run dev reading (+0.152, P 0.93).
  Registered step 2 would also have turned SYS itself (P 0.46) into REF.
* **The numbers re-derive exactly** from the fits with compare.py's functions: SYS against REF, men, −0.0083
  [−0.1617, +0.1451]; SYS_w100 against SYS +0.0419 [−0.0718, +0.1557].
* **The width is real, not mis-specified** (Observed). The block term carries it: block SE 0.075 against a seed term
  of 0.013, the same seed term as the first run's FP. SYS moves the forecasts about twice as much as FP did (per-match
  SD of the loss difference 8.5 against 4.8 mLL).
* **What the width means for the holdout** (Inferred). The holdout SE will be about 0.12 mLL, so harm needs an
  estimate below −0.25. The check flags a true −0.10 harm 11% of the time and −0.20 35%, where the owner's rates
  (holdout SE 0.063) said 31% and 86%.
* **No input flag is harm** (Observed). SYS's flags are broad (`points_52w`, 13 of 14 men's seasons) or remove the
  reference's 2025–26 widening of the products. REF_noITF's flags sit in 2025–26 only, as written down before it
  existed.

## 1. The decision layer, re-derived

*Observed* (`results/dev/pairs.csv`; rules: owner's file §1–3, erratum 1 §1, additions 4/4c; `system_decide.py`
`829560436…` = addition 4c's hash; harm in code: `estimate < −0.10 and hi < 0`, `system_decide.py:92-96`).

| Challenger (men, dev, both stages) | SYS against it | Reads better than SYS? |
|---|---|---|
| SYS_w0 | +0.578 [+0.137, +1.019] | no (SYS better) |
| SYS_w50 | +0.118 [−0.022, +0.258] | no |
| SYS_w100 | −0.042 [−0.156, +0.072] | no (unresolved, P(SYS_w100 better) 0.77) |
| SEP_ALL | +0.584 [+0.011, +1.156] | no (SYS better) |
| SYS_NOCLASS | +0.015 [−0.066, +0.096] | no |

* Step 1: no challenger qualifies, so SYS. Step 2: SYS against REF, men, −0.008 [−0.162, +0.145]; harm needs
  estimate < −0.10 with hi < 0; not met, so SYS stays. `selection.json`: SYS, status final, the five challengers,
  R_S2 and SYS_S2 labelled pool-lead evidence, the registered outcome beside it.
* The winner's-luck figure is reported as gain − 1.35 × SE for each challenger, as the owner's file asks.
* Report-only (Observed): SYS_S2 against SYS +0.167 [−0.035, +0.369]; R_S2 against SYS +0.161 [−0.086, +0.407]. Neither
  clears 0, so they would not have been selected under addition 4's seven challengers either.

## 2. No 2025–2026 result read

*Observed.* `system/holdout_unlock.json` and `results/holdout/` do not exist. All nine arms' `summary.json` say
`results_read_through: 2024` (`results/compare_runs.log`: each run "through 2024"); `results/dev/pairs.csv` holds the
period "dev 2020-2024" only, and no `scores.csv` holds a 2025 or 2026 population. Code: compare.py's `outcomes` filters
seasons ≤ 2024 before the column is read; `system_pairs.py --dev` loads fits of 2019–2024 only and refuses after the
unlock; `--holdout` and `system_decide.py --holdout` need the unlock; `system_supplementary.py` (`5dcefc1e…`, not yet
hashed in an addition) needs it for holdout seasons. The 2025–2026 fits exist (training labels through 2025, compared by
hash only), as registered.

## 3. Timing, and the switch from SYS_S2 to SYS

*Observed* (file times, UTC; hashes equal their `.sha256` files and the additions' quotes):

| File | Written | SHA-256 |
|---|---|---|
| `docs/decisions/2026-10-09-adoption-by-change-class.md` | 02:58:15 | `e72e9ae2…` (quoted in addition 4) |
| `owner_decision_2026-10-09.md` | 02:55:12 | `7e7f35da…` |
| addition 4 | 02:59:56 | `754e055c…` |
| addition 4b (`system_pairs.py` `a486aed9…` of 03:03, `system_decide.py` `34ac7071…`) | 03:08:26 | `f4e2e405…` |
| `owner_decision_2026-10-09_erratum_1.md` | 03:54:08 | `edb9b377…` |
| addition 4c (`system_decide.py` `82956043…` of 03:55) | 03:57:12 | `7c7ff69a…` |
| first dev score (status log) | 08:09:20 | |

* **All before the first score; the code in force equals 4c's hashes** (`system_decide.py` `82956043…`,
  `system_pairs.py` `a486aed9…`, `system_fits.py` `e8831b1f…`).
* **What decided the switch** (Observed, `selection_registered.json`): the registered rule (P(better than SYS) ≥ 0.90)
  qualifies SYS_S2 (0.951) and R_S2 (0.904) and selects SYS_S2 (P(better than REF) 0.901). The amended rule needs a 95%
  interval clearing 0, which neither has. Addition 4's seven-challenger version gives SYS too, so erratum 1's removal of
  the share arms changed nothing here.
* **Registered step 2 would have rejected SYS itself:** P(SYS better than REF) = 0.457 < 0.50. Under the original
  pre-registration, SYS could only have reached the holdout as a selected challenger's alternative. It does now because
  the owner's §3 keeps the proposal unless it shows harm.
* **What is not blind** (Inferred). The rule change came before any score of this run, but its authors could know the
  first run's published dev readings on the same seasons: R_S2 against the reference, men, +0.152 [−0.052, +0.357],
  P 0.93; FP +0.083. CP1 (S3) advised keeping the registered threshold for that reason. The owner's reasons (the power
  note's false-switch rate; a new feature belongs to the pool) are general and stand on their own. **Not improper by the
  project's rules** (the owner decides, before scores, in hashed files); **it must be reported:** the final document
  states the registered outcome (SYS_S2, +0.167 [−0.035, +0.369] over SYS) beside the amended one, and that SYS goes to
  the holdout on its statistic-level evidence with no model-level support on dev (P(better than REF) 0.46).

## 4. The numbers, re-derived

*Observed* (`audit/cp2/rederive.json`): E's own driver over compare.py's functions (`inputs_frame`, `scoring_info`,
`seed_table`, `walk_forward`, `forecasts`, `serve_speed_tabpfn.score.paired_stats` with seeds paired), results of
seasons ≤ 2024, men, 11,672 matches, 55 blocks:

| Reading | E | D (`pairs.csv`) |
|---|---|---|
| SYS against REF, both stages | −0.0083 [−0.1617, +0.1451], SE 0.0765 | −0.008314 [−0.161727, +0.145099], SE 0.076520 |
| SYS against REF, stage 1 | −0.0122 [−0.1663, +0.1419] | (stage 1 row) |
| SYS_w100 against SYS, both stages | +0.0419 [−0.0718, +0.1557], SE 0.0567 | SYS vs SYS_w100 −0.041917, SE 0.056728 |
| FP against REF (first run, the yardstick) | +0.0830 [+0.0017, +0.1643], SE 0.0406 | first run +0.083 [+0.002, +0.164] |

## 5. The input flags

*Observed* (`results/dev/decision.json`; each arm's `vs_reference_2026-10-08/`; F's `expected_unevenness.txt`; D's
`expected_changes.json`, written before the arms).
* **SYS (44 men's inputs moved; women identical).**
  * `points_52w` is flagged in 13 of 14 men's seasons (all but 2021): a broad change, as D's expectation said ("move in
    every season"). Its size does not track the evidence mix (Spearman 0.04), and SYS's own scale is smooth across
    seasons (SD ratio to 2013–21 from 1.0 in 2015–18 to 0.87–0.95 in 2022–26, levels within 0.07 SD).
  * Five products are flagged in some of 2016–2021 and in 2025–26. SYS's own 2025–26 product scale sits with its
    dev seasons (e.g. `prod_hold` 0.82 and 0.77 against 0.71–0.81 in 2021–24), where the reference widens (0.87, 0.94).
    These flags are SYS removing finding #6 (ITF box scores out), plus its CH/CHQ reweighting earlier.
  * Single-season flags: `form_first_in` 2023, `form_bp_conv` and `form_rpw_second` 2022.
  * **Not harm** (owner's file §1): each is explained by the dose or the written expectation, and none is a 2025–26-only
    jump in a direction the training seasons lack.
* **REF_noITF:** flags only in 2025–2026 (four products, both tours) and women's 2026 (`ratings_iid`,
  `prod_bp_saved`): ITF box scores leave, as written before it existed (C2 20:44 UTC; D's amended expectation). Not
  harm.
* F's expected unevenness concerns the C0 arms, none scored yet.

## 6. The width

*Observed* (`audit/cp2/rederive.json`): SE² = block SE² + seed term.

| Reading | SE | Block SE | Seed term (SD of the mean) | Per-match SD of the loss difference (mLL) | Mean change in the forecast |
|---|---|---|---|---|---|
| SYS against REF | 0.0765 | 0.0753 | 0.0134 | 8.46 | 0.0030 |
| FP against REF (first run) | 0.0406 | 0.0382 | 0.0136 | 4.83 | 0.0016 |
| SYS_w100 against SYS | 0.0567 | 0.0555 | 0.0118 | 5.92 | 0.0020 |

* **Not mis-specified, and not seeds** (Inferred). The four seeds agree (SYS's per-seed gains −0.021, +0.009, −0.049,
  +0.005); the seed term equals FP's. The interval is wide because SYS changes 44 inputs and moves each forecast about
  twice as much as FP's 18 inputs did, so the per-match differences, and the block SE, double. The power note's 0.08
  came from FP-sized changes.
* **The holdout** (Inferred, `audit/cp2/harm_rates.json`). Scaled to 4,810 men's matches, SE about 0.12 mLL; with
  t(22), harm needs an estimate below −0.247. The primary flags a true harm of −0.10 with probability 0.11, −0.20 0.35,
  −0.30 0.67 (a false flag at 0: 0.02). The owner's §6 table used SE 0.063 (0.31, 0.86, 0.996). The holdout primary
  can show only a large harm; an unresolved reading is the expected outcome whatever SYS is worth within ±0.25.

## 7. Before the holdout is opened

* **C1. Restate the rates with the observed SE, in writing, before the unlock.** The owner's file §6 and the final
  document quote rates for SE 0.063; for SYS the SE is about 0.12 (§6 above). The rule itself does not change (the
  tolerance may not be loosened, and tightening it after dev scores would be a choice made on them).
* **C2. The supplementary scorer.** Done (Observed): addition 5 (`f9d12ac4…`, 08:33 UTC, before any unlock) holds
  `system_supplementary.py` `5dcefc1e…` (equal on disk). From the code: it refuses the six selection arms, never reads or
  writes `selection.json`, writes only under `results/supplementary/`, and needs the unlock for holdout seasons; RES_ONLY's
  dev reading (the M3 separation) runs there. **Still to add:** its holdout readings can be re-run ("a re-run of the same
  target rewrites its own files"), and NEW_SYS_BOTH's holdout reading decides the 2025–26 additions (owner's §5). A
  written rule is enough: each target's first holdout reading, with its fits' hashes, is the reading of record; any
  re-run is reported beside it.
* **C3. The unlock holds, besides every pre-registration file and `selection.json`** (`b5fbec82…`), the hashes of the
  owner's file (`7e7f35da…`), its erratum (`edb9b377…`), the decision (`e72e9ae2…`) and `system_decide.py`
  (`82956043…`). They govern the decision layer, and `verify_unlock` checks only files named `preregistration*` or
  `*addition*` (`system_pairs.py:240-268`).
* **Build and gate code since addition 3** (recorded in addition 5, not re-verified by E): `system_gates.py`
  (`f4cb45c6…`; the identity file's fingerprint, the lead's G3 rule for ENV inputs) and `system_arms.py` (`64457222…`;
  every build restores the validated code snapshot, MANIFEST `1e95dbfe…`). The snapshot answers an incident: another
  session's uncommitted change to `tabpfn_thinking/build_frame.py` (01:14 UTC) reached `tnr_sys5`, and G2 caught it on
  SYS_w100 (`indoor`), which was rebuilt. The record says the arms built earlier ran code equal to the snapshot.
* **Already in place** (Observed, `system_pairs.py`): Holm on addition 2's eight readings with the lead's two-sided normal
  p (`:476`, `:687-714`); the 2026 speed rule "zero" with the 909-match drop as a sensitivity, both tours (`:391-440`);
  the holdout refusing a missing fit and running once (`:28-31`, `:351-369`).

## Notes

* **The dose curve against REF, men, dev** (Observed): SYS_w0 −0.586 [−1.055, −0.118] (harm by §1), SYS_w50 −0.126
  [−0.315, +0.062], SYS −0.008, SYS_w100 +0.034 [−0.085, +0.152]; SEP_ALL −0.592 [−1.187, +0.002]. Removing lower-level
  box scores costs about 0.6 mLL. Above w = 0.5 the readings cannot separate the weights.
* **SYS_PLACEBO against REF, men:** −0.161 [−0.354, +0.031] (P(better) 0.05), as in the first run (N8): SYS against
  SYS_PLACEBO, +0.153 (P 0.94), says SYS's change hurts less than a random one, not that it helps.
* **The amended rules' guard against a challenger** (owner's §2) is the same 95% interval as the holdout's. On dev it
  could not separate SYS from SYS_w100, SYS_w50 or SYS_NOCLASS, as CP1 expected.

## What it does not show

* Nothing here reads the holdout.
* The re-derivation covers three readings, not all 546 rows. D's own check against compare.py covers 54.
* The holdout rates are scaled from the dev SE by match counts. Its blocks and seasons may differ.

# Checkpoint 3 (CP3): the holdout readings and the final document

Audited 08:41–08:47 UTC on 10 Oct, after the unlock (`holdout_unlock.json` `56864fed…`, 08:36:26 UTC) and D's main
holdout run (08:37–08:40 UTC). E's script: `audit/scripts/e_cp3_rederive.py`; results in `audit/cp3/`. E's readings
are reproductions, not readings of record (addition 6 §2).

## In short

* **Verdict: the results stand. The document stands after the fixes R1–R6** (§5); none changes a number or the
  recommendation.
* **The lock held** (Observed). Unlock 08:36:26; D's run started 08:37:15 with `readings.json` absent and wrote it
  once (08:38:23, `8f7805eb…`, the hash `decision.json` records). Nothing of 2025–26 was read before. No supplementary
  reading exists yet.
* **The headline numbers re-derive exactly** from the fits: primary SYS against REF, men, 2025–26, +0.0107 [−0.4254,
  +0.4468]; SYS_w0 against REF, men, pooled 2020–26, −0.5016 [−0.8717, −0.1314]; the placebo, both tours, +0.2145
  [+0.0306, +0.3984].
* **The placebo's "better" is the holdout period, not seeds and not regularisation** (Observed). Its four seeds agree;
  it does not shrink forecasts; REF is not overconfident on 2025–26. Its men's gain by season runs −0.18, −0.42, 0.00,
  −0.24, 0.00 on dev and +0.36, +0.34 on the holdout; pooled 2020–26 it is −0.012. The interval is right for "this
  frame on these matches". It is not the uncertainty of "a random change of this size".
* **The SE of 0.21 is plausible** (Observed): block term 0.210, seed term 0.009. On the holdout SYS's per-match
  difference from REF is larger (SD 11.7 against 8.5 mLL on dev), as the 2025–26 ITF exclusion adds to it, and there
  are 23 blocks instead of 55. E's CP2 projection of 0.12 scaled by match count only and missed this.
* **The recommendation is valid as the owner's rules state it** (SYS for men: no harm, no Holm reading worse), with
  four qualifications (§4). The harm check flags a true −0.20 only 13% of the time. No model-level reading supports
  SYS (dev −0.008, holdout +0.011, pooled −0.003). RES_ONLY reads +0.055 and SYS against RES_ONLY −0.045. The registered
  rules recommend nothing.
* **The document has two factual errors** (R1, R2: what the registered rules would have selected and recommended) and
  one description that does not match the build (R3: `ratings_iid` has no level term). Three more statements over-reach
  (R4–R6).

## 1. The lock

*Observed* (`status.log`; file times; `results/holdout/`).
* `holdout_unlock.json` was written at 08:36:15 and rewritten at 08:36:26 (`56864fed…`), after addition 6's stated time
  was corrected (`70d686e8…` superseded by `20255b89…`). It holds the hashes of the nine pre-registration files, of
  `selection.json` (`b5fbec82…`) and of the decision layer's four sources (CP2's C3), equal to the files on disk.
* D's main run: started 08:37:15, after the unlock; `readings.json` was absent at the start (status line); written
  08:38:23, once; `decision.json` (08:38:41) records its hash, `8f7805eb…`, equal to the file now. The frozen scorer
  refuses a second run while `readings.json` exists (`system_pairs.py:28-31`).
* Nothing of 2025–26 was read before the unlock: CP2 checked to 08:35; between 08:35 and 08:36:26 only addition 6 (text)
  and the unlock were written. No `results/supplementary/` exists, so every supplementary reading still to come will be
  its arm's first, as addition 6 §2 requires.

## 2. The re-derivation

*Observed* (`audit/cp3/rederive.json`): E's driver over compare.py's functions, results through 2026 (after the
unlock), the 2026 speed rule "zero" (gap matches get no stage-2 nudge), seeds paired.

| Reading | E | D (`results/holdout/`) |
|---|---|---|
| Primary: SYS against REF, men, 2025–26 | +0.0107 [−0.4254, +0.4468], SE 0.2103, 23 blocks | +0.011 [−0.425, +0.447], SE 0.2103, P 0.52 |
| SYS against REF, men, pooled 2020–26 | −0.0028 [−0.1643, +0.1588] | −0.003 [−0.164, +0.159] |
| SYS_w0 against REF, men, pooled 2020–26 | −0.5016 [−0.8717, −0.1314] | −0.502 [−0.872, −0.131], worse |
| SYS_PLACEBO against REF, both tours, 2025–26 | +0.2145 [+0.0306, +0.3984] | +0.215 [+0.031, +0.398], better |
| SYS_PLACEBO against REF, men, 2025–26 | +0.3497 [−0.0337, +0.7331] | +0.350, P 0.97 |

## 3. The placebo, and what it says about the other readings

*Observed* (`audit/cp3/rederive.json`):

| Placebo against REF | SE | Block | Seed term | Per-seed gains | By season (men) |
|---|---|---|---|---|---|
| men, 2025–26 | 0.185 | 0.184 | 0.016 | +0.326, +0.380, +0.318, +0.377 | 2025 +0.361, 2026 +0.336 |
| both tours, 2025–26 | 0.089 | 0.087 | 0.018 | +0.171, +0.254, +0.199, +0.234 | |
| men, dev 2020–24 | 0.096 | 0.093 | 0.024 | −0.092, −0.204, −0.173, −0.168 | −0.178, −0.416, +0.004, −0.243, +0.002 |
| men, pooled 2020–26 | 0.091 | 0.090 | 0.015 | | −0.012 overall |

* **Not the seed term.** The four seeds agree within ±0.04; the paired seed term is small and is the right one.
* **Not regularisation** (Observed). On men's 2025–26 matches the placebo does not shrink REF's forecasts (mean |logit|
  0.849 against 0.850; slope of the placebo's logit on REF's 0.999). REF is barely overconfident (calibration slope
  0.970; the placebo's 0.973), so there is no overconfidence for added noise to cure.
* **The period** (Inferred). The block interval holds the two frames' forecasts fixed and samples outcomes in four-week
  blocks within one period. A permuted frame's fit against a given period's outcomes has a period component the
  interval does not carry. Season by season the placebo swings from −0.42 to +0.36, and both holdout seasons land at
  the top. With dozens of holdout readings, one "better" from a null arm is not surprising. Pooled 2020–26 it reads
  −0.012 [−0.193, +0.169].
* **What it changes** (Inferred).
  * SYS's readings (dev −0.008, holdout +0.011, pooled −0.003) sit well inside the placebo's swing. Single-period
    model-level readings of changes this size cannot separate SYS from a random rearrangement of its own changes. SYS
    against SYS_PLACEBO on the holdout, men, −0.339 [−0.958, +0.280] (P 0.13), says the same.
  * The SYS_w0 harm stands. It is negative in all seven seasons (−1.32, −0.73, −0.27, −0.35, −0.65, −0.31, −0.27) and
    all four seeds (pooled −0.41 to −0.58), unlike the placebo. But the holdout alone gives −0.296 [−0.911, +0.319]
    (P 0.16): the pooled "worse" leans on the dev seasons where it was first seen.
* **The SE of 0.21.** Block term 0.210, seed term 0.009. Against dev: per-match SD of SYS's loss difference 11.65 against
  8.46 mLL (on 2025–26, SYS also removes the men's ITF box scores, which exist only from 2025), and 23 blocks against
  55. Scaling by matches and by that SD gives 0.16; the rest is stronger block-level clustering. Plausible.

## 4. The recommendation

*Observed* (`results/holdout/decision.json`): under addition 4 §4, SELECTED (SYS) unless the primary shows harm
(+0.011: no) or one of the eight Holm readings is worse (none, raw or adjusted). **SYS for men is the rule's correct
output.** Qualifications the document must carry (Inferred unless marked):
* **The harm check was weak.** At SE 0.21, harm needs an estimate below −0.436. It would flag a true −0.10 harm with
  probability 0.06, −0.20 0.13, −0.30 0.26 (`audit/cp3/`). Addition 6 stated 0.11 and 0.35 for SE 0.12. "No harm"
  excludes only harms larger than about 0.43 mLL.
* **There is no model-level support** (Observed): dev −0.008 (P 0.46), holdout +0.011 (P 0.52), pooled −0.003 (P 0.49).
  The recommendation rests on the statistic-level evidence alone, as addition 6 §1 says. The holdout cannot tell SYS
  from its placebo (§3).
* **What SYS bundles** (Observed): RES_ONLY (the results channel alone, ITF results discounted and ITF qualifying
  dropped) against REF, men, +0.055 [−0.076, +0.187] (P 0.81); SYS against RES_ONLY −0.045 (P 0.40); SYS against
  REF_noITF +0.083 (P 0.71). None resolved. The box-score relationship has no model-level reading in its favour.
* **The registered rules** (Observed): their selection, SYS_S2, reads +0.099 [−0.490, +0.688] (P 0.64 < 0.80) on the
  holdout, so they recommend nothing ("unresolved: report P(better)"). D's record computes
  them for SYS (P 0.52), with the same answer.

## 5. The final document (`README.md`, the lead's draft of 08:41 UTC)

Every number was checked against `results/dev/`, `results/holdout/`, `selection*.json`, B's and A's tables, F's report
and the additions. All match except where listed. The two placeholders ([RULE …], the wired test) wait for the
supplementary NEW arms, as stated.

**Must fix** (errors, or a description that does not match the build):
* **R1. §3.2:** "The registered rules would have picked SYS_S2 (P 0.95), and then preferred REF to it (P 0.46 < 0.50)."
  SYS_S2's P(better than REF) on dev is 0.90, so the registered rules keep SYS_S2 (`selection_registered.json`,
  `step1_p_better_than_REF` 0.9006). The 0.46 is SYS's: had SYS been the step-1 arm, step 2 would have preferred REF.
  Addition 6 §4 carries the same ambiguity.
* **R2. "In short" 5 and §3.3:** "Under the original rules: none (P 0.52 < 0.80)." The registered recommendation applies
  to the registered selection, SYS_S2: holdout +0.099 [−0.490, +0.688], P 0.64 < 0.80, so none. Give that, with SYS's
  0.52 as D's record.
* **R3. §1, `ratings_iid`:** "Level offset, and K × w" does not match the build. Built: one weight per observation (B's
  `w_joint`, capped at 1) and no level term (`ratings_level_term "none"`; B's δ is not in the solve's units; C_layer.md;
  E's CP1 S6).
* **R4. "In short" 4:** "Dropping the lower-level evidence is again clearly worse (pooled −0.50)." On the holdout alone
  it is −0.296 [−0.911, +0.319], unresolved (P 0.16). The pooled reading includes the dev seasons where it was found.
  Say "consistent in all seven seasons and all four seeds; pooled 2020–26 −0.50, worse".
* **R5. §3.1:** "with the layer switched off, the build reproduces all 58 inputs exactly." G1 (IDENTITY_ALL) ran with
  every family's layer on at the identity settings, a stronger check than "off".
* **R6. §1, Elo:** add that men's ITF-qualifying results are dropped (w_results 0 in every season), and that RES_ONLY
  separates this channel (holdout +0.055 against REF; SYS against RES_ONLY −0.045).

**Should fix** (over- or under-claims):
* "In short" 2, "the relationship is clearly right": say "clearly better than pooling as equivalent, in one predictor
  (B)". The planted tests check mechanics (CP1 S7).
* "In short" 3, "TabPFN already copes with equivalent pooling about as well as with translated inputs": an inference
  beyond the evidence. Say "the model-level test cannot tell them apart (±0.15 on dev, ±0.43 on the holdout)".
* "Model-level readings at this scale are noise": say "single-period readings cannot resolve changes of this size; a
  shuffled placebo of SYS's size moved the holdout by +0.35 (men)".
* §2.2 and §2.3, the newcomer prior: "in the form tested" (CP1 S4). The UFC idea itself is untested.
* §3.3 and §3.4: SE 0.21 (0.2103), not 0.22. Add the harm check's rate at that SE: a true −0.20 is flagged 13% of the
  time.
* §1, "Fitted values above 1 came from the estimator's prior": the largest ones (up to 2.8, men's break points forced).
  Qualifying's 1.03 is not shown to be an artefact.
* "In short" 1, "a Challenger match is worth about 0.6": B gives 0.63 per point and about 0.55 per match. The level
  mean is lifted by about 0.035 by the same artefact (CP1 S1).
* §2.2's statistic-level gains are for B's estimator with w up to 3; the system caps w at 1 (addition 3). B's dose
  curve says the difference is small (+0.006). One clause is enough.
* "What it does not show": "The system was fitted for women too (SYS_BOTH)": B fitted women's parameters, but SYS_BOTH
  was not built when the holdout was read (waived; supplementary).
* **The owner's decisions:** state in §3.1 who wrote what. The owner said "I accept your adoptation logic, implement
  it"; session `tennis-predictions-cc` wrote the application (02:55 UTC) and its erratum (03:54 UTC), and the lead
  adopted them (additions 4–4c), all before any score. §7.3 already says the 0.10 tolerance is Claude's choice.

**Consistent with the role reports** (Observed): A's classes and γ, B's tables (w, δ, contrasts, dose, Elo grid), C1's
and C2's builds as gated, D's dev and holdout readings, F's counts (298,008 new; 1,644 completions; 18,334 near a
main-tour player; identity 120/120 and 237/248), and G's plan. The exception is `ratings_iid` (R3).

## 6. Verdict

**The results stand.** The lock held, the readings re-derive exactly, and the recommendation is what the owner's rules
give. **The document stands after R1–R6.** The should-fix items make its claims match the evidence. Its central message
is right and should stay prominent: no model-level evidence for or against SYS, a harm check that can see only large
harms, and adoption resting on the statistic-level evidence, with no edge credit.

## What it does not show

* The re-derivation covers five readings. D's own cross-check with compare.py covers the rest.
* The placebo's period component is inferred from one permutation's seven seasons. A second permutation would test it.
* Nothing here reads the supplementary arms (RES_ONLY's dev, SYS_BOTH, the ITFASIS pair, the NEW arms), still to come.
