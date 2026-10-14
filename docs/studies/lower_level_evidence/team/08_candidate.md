# Role 08: the candidate build: lower-level matches translated in the 17 one-step forms and `points_52w`

9 October 2026 · Team role 08 (candidate builder and tester) of the lower-level-evidence study · Research evidence, not a
decision. Accepting a candidate is the owner's call.

## In short

* **What was built** (Observed).
  * The remedy for the inputs that treat a lower-level match as equivalent: each lower-level match's contribution is
    translated by a per-statistic, per-tour, per-level offset before it enters the 17 one-step forms and `points_52w`.
  * The offsets were estimated on 2010–2018 only.
  * The candidate (FP) was built in a sandbox through the whole decided chain, with a two-line hook in each of two
    builders. Nothing else changed.
  * It was then scored against the frozen reference of 8 Oct with six control and channel arms, plus one control added
    before any score (R_S2).
* **The gates passed** (Observed).
  * The 40 untranslated inputs are identical to the reference's on all 67,226 matches.
  * At zero offsets, the build's code reproduces the reference's 18 translated inputs exactly. The translation is the
    build's only change.
  * Inputs no lower-level box score can reach did not move.
  * Every one of the 34 required input-tours moved towards the player with less lower-level evidence.
* **The primary is unresolved** (Observed). FP against the reference, both stages, both tours, 2020–2024:
  **+0.024 [−0.047, +0.096] mLL, P(better) 0.75** (+ = FP has the lower log loss).
  * Men: **+0.083 [+0.002, +0.164], better.**
  * Women: −0.040 [−0.154, +0.073], unresolved, P(better) 0.24.
* **The men's gain lives in `points_52w`, not in the forms** (Observed).
  * P (only `points_52w` translated): men +0.066 [+0.001, +0.131], better.
  * F (only the 17 forms translated): +0.005 [−0.060, +0.069], unresolved; both tours −0.003, P(better) 0.46.
* **It is not separable from the share signal** (Observed).
  * The gain sits where the two players' lower-level shares differ most: share gap ≥ 0.5, +0.165 [+0.004, +0.326],
    better.
  * The falsification stratum, whose inputs did not move, reads −0.033 [−0.155, +0.088], unresolved, as predicted.
  * But R_S2, the reference plus the two share differences as inputs, does as well as FP: FP against R_S2 is
    **−0.003 [−0.165, +0.160], unresolved, P(better) 0.49**.
  * Against its same-size placebo, FP is unresolved on both tours (+0.053 [−0.036, +0.142], P 0.88): better for men
    (+0.197 [+0.059, +0.335]), leaning worse for women (−0.106 [−0.231, +0.019], P 0.05).
* **The pre-registered verdict: unresolved, not suggested for adoption on mechanism.**
  * The primary is unresolved, which is the pre-registration's "tie" branch.
  * Of its three conditions, two hold: no secondary is worse, and every secondary was scored.
  * The third fails: the input check's operational test counts `points_52w` as an unexpected uneven input.
  * *Inferred:* that flag is a threshold artifact of a broad change (below), but the rule was fixed before the data and
    is applied as written.
* **My suggestion: do not adopt FP.** Keep the machinery for the ITF box scores; test any narrower version (`points_52w`
  alone, or the share inputs) as a new pre-registered candidate.

## The question

* **The owner's question** (9 Oct 2026, condensed). Lower-level data should *inform* the main-tour model, as the UFC
  pipeline skews a fighter's prior toward his record outside the UFC, without being treated as *equivalent* evidence.
* **What roles 01 and 03 found.** Eighteen of the 58 inputs treat a lower-level match nearly or fully as a main-tour
  match:
  * the 17 one-step forms (`adjperf_tpw_2w`, 12 `form_*`, 4 `formdef_*`) keep about 78% of the raw level shift. Each
    match is read against the opponent's own usual opponents, at whatever level he plays;
  * `points_52w` pools raw 52-week serve and return counts as if every level were the main tour.
* **The remedy tested here.** Before a lower-level match enters those 18 inputs, its contribution is translated by a
  per-statistic, per-tour, per-level offset: the same players' average gap between that level and the main tour in the
  same season. Nothing else in the model changes.

## Keys

* **Labels.** *Observed* = computed here (file cited) or read in code (`path:line`). *Inferred* = reasoning.
  *Suggestion* = a proposal.
* **Scores** are in mLL (milli-log-loss per match). **+ = the first-named model has the lower log loss (better).**
  * "Better" or "worse" when the 95% interval clears 0; otherwise **"unresolved"**, with P(better).
  * This follows the owner's decision of 9 Oct (`docs/decisions/2026-10-09-adoption-framework.md`). The
    pre-registration's "tie" reads as "unresolved"; its decision logic is unchanged.
  * Intervals combine four-week blocks with the seeds' variance, paired by seed (compare.py's `paired`).
* **Holdout.** 2025–2026 (events from 30 Dec 2024) is the proposed clean holdout. No 2025–2026 outcome was read:
  * fits cover seasons 2019–2024, scores 2020–2024;
  * G1 compared the result column through 2024 only (a filtered read);
  * `low_share_diff` was computed with the result column replaced by a constant.

  Inputs of 2025–2026 were built and counted only.
* **Files.** Outputs are under `data/studies/lower_level_evidence/candidates/` (written `candidates/` below).

## The pre-registration

* **Written and hashed** at 16:11 UTC on 9 Oct (`candidates/preregistration.md`; SHA-256 `bf1e6a33…` in
  `preregistration.sha256`).
  * It came before any offset was estimated (the rate offsets: 16:16 UTC), any frame was built or any score was read.
  * It fixes the arms, the offsets' rule, the gates, the readings and the decision rule (as given in the brief).
* **One dated addition** at 16:43 UTC, also before any candidate fit existed or any score was read: R_S2 and the
  "unresolved" wording, at the lead's request.
  * The original text keeps its hash; the file with the addition has its own (`preregistration_addition.sha256`).
  * The scorer (`candidate_pairs.py`) refuses to run unless both match.
* **Before the addition,** the scorer had been dry-run once, on a copy of the reference against itself: 0 exactly, and
  +1.374 against the calibrated close, as published. No candidate was involved.

## What was built

### The offsets (seasons 2010–2018 only)

* **The rule** (pre-registered; `src/eda/lower_level_evidence/translate_hooks.py`, `offsets_from_levels`):
  * a player-season qualifies for a level when it has at least 3 box scores at the main tour (MAIN) and at least 3 at
    that level;
  * the offset is the mean, over qualifying player-seasons, of (the player's mean at the level minus his mean at MAIN);
  * TQ, GSQ, CH and CHQ are estimated per tour. A cell under 100 player-seasons takes the both-tours estimate, then 0.
  * ITF and ITFQ take CH's and CHQ's values as a placeholder: they have box scores only in 2025–2026, the holdout.
    TEAM and MAIN: 0.
  * Intervals: 95%, clustered by player.
* **The forms.** Measured on the build's own Stage B per-match z (after the clip at ±4, before step 3), for the 17
  (statistic, channel) pairs that feed the 17 inputs.
  * They were estimated inside the build by the hook's first full-history call, which also wrote the untranslated z
    (`candidates/offsets/forms_z_untranslated.parquet`).
  * Re-derived from that record outside the build, they are equal (largest gap 2e-16,
    `checks/offsets_forms_rederived.json`).
* **`points_52w`.** Measured on the raw rates of serve and return points won, on the rows Stage 4 admits to its
  histories.
  * They were estimated before the build from the frozen Stage 0 (`offsets.py --rates`).
  * The build's Stage 4 re-estimated them from its own rows and found them equal (`verified` in
    `offsets/hook_calls.jsonl`).

**The offsets in brief** (Observed; `candidates/offsets/offsets_summary.csv` has every cell with its interval and
count). z units for the forms (a match's z has an SD of about 1.2); points per point for the rates.

| Input (pair) | Men CH | Men TQ | Men GSQ | Men CHQ | Women CH | Women TQ | Women GSQ | Women CHQ* |
|---|---|---|---|---|---|---|---|---|
| `adjperf_tpw_2w` (adjperf tpw) | +0.55 | +0.62 | +0.65 | +0.83 | +0.48 | +0.49 | +0.65 | +0.84 |
| `form_hold` | +0.47 | +0.51 | +0.57 | +0.58 | +0.46 | +0.35 | +0.59* | +0.59 |
| `form_first_won` | +0.45 | +0.43 | +0.42 | +0.51 | +0.43 | +0.37 | +0.47 | +0.49 |
| `form_bp_faced_pg` (lower is better) | −0.44 | −0.50 | −0.53 | −0.53 | −0.41 | −0.32 | −0.54* | −0.55 |
| `form_ace` | +0.28 | +0.20 | +0.12 | +0.25 | +0.20 | +0.10 | +0.25 | +0.23 |
| `form_df` (lower is better) | −0.14 | −0.21 | −0.29 | −0.29 | −0.24 | −0.09 | −0.26 | −0.25 |
| `form_first_in` | +0.08 | +0.12 | +0.13 | +0.20 | +0.24 | +0.06 | +0.14 | +0.20 |
| `formdef_df` | +0.02 | −0.03 | +0.05 | +0.09 | +0.19 | −0.12 | −0.02 | +0.08 |
| `points_52w`: serve points won | +0.025 | +0.030 | +0.029 | +0.031 | +0.027 | +0.025 | +0.035 | +0.030 |
| `points_52w`: return points won | +0.045 | +0.046 | +0.053 | +0.071 | +0.031 | +0.034 | +0.046 | +0.072 |
| Player-seasons behind the total-points cell | 1,312 | 1,114 | 423 | 100 | 181 | 1,114 | 318 | 6 (→ 106) |

\* Both-tours value (the own tour has under 100 player-seasons): every women's CHQ cell, and women's GSQ for holds,
breaks and break points faced.

* **They agree with role 01's measure on 2013–2024.** Men's Challenger total points: +0.55 here against +0.52 there.
* **Every skill statistic looks better below the main tour; the style statistics barely move,** as role 01 found.

### The hook and the patch

* **The hook** (`src/eda/lower_level_evidence/translate_hooks.py`) is switched off unless the environment variable
  `LLE_TRANSLATE` names a JSON config (`candidates/hook_config_FP.json`). Unset, both functions return their input
  object unchanged. With it set:
  * `translate_forms`: z ← z − scale · δ_z[statistic, channel, tour, level of the match] for every box row of a
    lower-level match, in the 17 pairs. The clip is not re-applied; MAIN and TEAM rows are untouched.
  * `translate_counts`: x ← x − scale · d · δ_rate[statistic, tour, level] for serve and return points won, on the rows
    Stage 4 admits.
  * Every full-history call re-estimates the offsets from the data it receives, and refuses to run if they differ from
    the stored table. Every call is logged (`candidates/offsets/hook_calls.jsonl`).
* **The patch:** two lines in each of two sandbox copies (`candidates/sandbox_patch.diff`, applied by
  `src/eda/lower_level_evidence/sandbox_patch.py`, which refuses the repository itself):
  * `stageB_adjperf.build`, after the per-match z of every pair and before the decay-and-shrink step:
    `Z = _LLE.translate_forms(ctx.rows, ctx.box_idx, Z)`;
  * `stage4_features.history_sums`, before the sums: `x = _LLE.translate_counts(rows, s, x, d, ok)`.
* **What stays as it was.**
  * Stage B's tuning reads `Ctx.z` directly, so its constants are the reference build's.
  * The opponents' norms (their "allowed" averages) are not translated.
  * No other builder is touched, and no decided file in the repository was edited.
* **Tests:** `test/lower_level_evidence/test_translate_hooks.py`, 12 tests, all pass. They check:
  * a planted offset is recovered, and the estimate equals a brute-force mean of season differences;
  * the 3-box-score rule; seasons after 2018 never enter; the fallbacks and the placeholders; the rates pool counts
    within the season;
  * the hooks are off without the variable;
  * only lower-level rows move, by their own pair's offset; a missing z stays missing;
  * the hooks are linear in the scale;
  * a stored table the data does not reproduce is refused, and a slice never estimates.

### The build

* **The sandbox.** `MODEL_REBUILD_SANDBOX=C:/Users/zerom/tnr_lle`, `run_chain.py --setup --candidate`.
  * Before the build, the live tables were checked against the frozen reference's hashes: Stage 0, the odds and every
    timeline file were equal (the hashes in `frozen/files.csv.gz`).
  * No file in the chain's study folders had changed since the freeze (`frozen/inventory.csv.gz`, sizes and times).
  * The IOS constants were pinned to version `2026-10-08_reference` (`IOS_CONSTANTS_VERSION`).
* **The lanes.** Lanes 1 and 2 ran beside each other, then lane 3, then `--collect --out candidates/FP`. Every step
  exited 0.

### The arms

Each arm is a folder `candidates/<arm>/` with `model_frame.parquet`, `model_inputs.json` and its fits. Every frame other
than FP (and FP_L, which is FP's file plus one column) is the reference's file with columns replaced or added, through
pyarrow, so the result column passes through unread (`src/eda/lower_level_evidence/candidate_arms.py --build`, `--half`).

| Arm | Frame | Role | Fitted by |
|---|---|---|---|
| **FP** | the collected frame: the 17 forms and `points_52w` translated | **primary** | `model_rebuild/fits.py` |
| F | the reference with FP's 17 forms | channel: forms | `fits.py` |
| P | the reference with FP's `points_52w` | channel: `points_52w` | `fits.py` |
| FP_half | the reference plus half of FP's change: forms interpolated; `points_52w`'s exact value at half the offsets (G4) | dose | `fits.py` |
| FP_placebo | the reference plus FP's per-match change vector (all 18 inputs together), permuted across matches within tour × season (`default_rng(20261009)`) | placebo twin: the same size (the SDs of the changes agree to 0.2%), alignment destroyed (\|correlation\| with FP's change under 0.011) | `fits.py` |
| R_L | the reference plus `low_share_diff` (event-levels' C1 input: A's minus B's share of the previous 365 days' played matches below the main tour) | exposure-gap control | `candidate_fits.py` |
| FP_L | FP plus `low_share_diff` | exposure-gap control | `candidate_fits.py` |
| R_S2 | the reference plus A's minus B's lower-level share of box-score evidence, in the two-week window and over 365 days (two inputs) | the matching share control (the dated addition) | `candidate_fits.py` |

* **`low_share_diff`** was computed for all 67,226 frame matches with event-levels' own function
  (`event_levels/blend.history`) on the frozen Stage 0 (`checks/low_share_check.json`).
  * It equals event-levels' column on 63,407 of the 63,697 matches both hold.
  * All 290 differences come from the Stage 0 snapshot: 232 in 2026, 47 in 2016, 9 in 2015, 2 in 2021; 56 name a
    different player on side A (the 8 Oct corrections).
  * The same code on event-levels' own 30 Sep snapshot reproduces their column exactly, on 63,737 of 63,737 matches.
* **`candidate_fits.py`** is `model_rebuild/fits.py` line for line, except that it admits one registered set of extra
  inputs after the 58. `fits.py`, a decided file, refuses any frame without exactly 58.
* **The order.** The arms were fitted in the pre-registered order, then R_S2. FP_half was fitted last, because G4
  finished after the queue had started. The order changes no fit.

### The dated addition (R_S2)

* **The argument** (red team, items S2 and M1). With one constant offset per statistic, tour and level, the translation
  moves each form by about δ × the player's shrunk lower-level share in its two-week window, and `points_52w` by
  δ × its 364-day share. So FP is in effect the reference re-centred by two share variables. R_L's 365-day *results*
  share is not the share that drives 17 of the 18 changes.
* **The pre-registered reading.** FP against R_S2. If FP's gain over the reference survives against R_S2, the
  translation carries more than the share signal; if not, it is the share signal in disguise.

## The gates (all passed before any fit; `candidates/checks/`)

| Gate | What it checks | Result |
|---|---|---|
| G1 reproduction | FP's frame against the frozen frame: ids, order, identifiers, the result column through 2024, every input | **Pass** (`g1_reproduction.json`, `g1_inputs.csv`). All 67,226 matches in the same order. The 40 untranslated inputs are identical: largest difference 0, the same missing cells. The 18 translated inputs changed on 51,989–58,436 matches each, with the same missing cells. |
| G2 invariance | Inputs no lower-level box score can reach must not move | **Pass** (`g2_invariance.json`). (a) On the 612 matches where neither player has ever had a lower-level box score, all 17 forms are identical. (b) On the 8,329 matches with no lower-level box score for either player in 365 days, `points_52w` is identical on all 8,219 with a value (the rounding allowance was not needed). |
| G3 direction | The change against A's minus B's lower-level box-score share (two-week window for the forms, 365 days for `points_52w`) | **Pass**: 34 of 34 required input-tours have the expected sign (`g3_direction.csv`). The correlations run from −0.97 to −0.74, or from +0.43 to +0.90 where the offset is negative. Not required (offset under 0.05 z): men's `formdef_df`, women's `formdef_first_in`. |
| G4 linearity | The forms and `points_52w` recomputed by the sandbox's code at 0, 0.5 and 1 times the offsets | **Pass for the forms; `points_52w` not linear, as expected** (`g4_linearity.json`). Scale 0 reproduces the reference's 18 columns and scale 1 FP's, exactly, on all 67,226 matches. The forms are linear (largest departure from the midpoint 4e-16). `points_52w` departs by up to 0.066 (median 0.0004), because it passes through logit and the iid match model. So FP_half takes `points_52w`'s exact value at scale 0.5, as pre-registered. |
| G5 the fit runner | `candidate_fits.py` refits the reference's season 2019, seed 0, from the frozen frame | **Pass** (`g5_fit_runner.json`): the same ids and input fingerprint; largest difference of the forecasts 0.0. |

**Also observed in the build's own logs.**
* **The constants are the reference build's.** Stage B's tuning chose the same constants with the same in-sample gains,
  e.g. men's total points 2.693 (`FP/chain_logs/ufc_stageB_adjperf.log`).
* **The builders' own leak probes still pass with the hooks on.**
  * Stage 4: no protected match changed on any cut.
  * Stage B: none changed on 4 cuts, with the reference build's own counts of later changes (13,419 / 26,695 / 26,838 /
    39,818).
  * Stage B split: none changed.
* **Stage B's "mirror" diagnostic now differs.** Adjdef of total points against adjperf of total points correlates
  0.979, not 1.000, because only the adjperf side is one of the 17. No input reads the mirror.
* **How far the inputs moved** (G3's medians, in the reference's SD per tour):
  * the serve-side forms and `adjperf_tpw_2w`: 0.02–0.14 (men), 0.01–0.07 (women);
  * the return-side and defence forms: at most 0.09. Their two-week forms shrink hard (K3 = 160 typical matches for the
    return-skill constants), so the same offset moves them less;
  * `points_52w`: 0.45 (men) and 0.26 (women), by far the largest change.

## The input check (compare.py part 1, read before any score)

*Observed* (`FP/vs_reference_2026-10-08/inputs.csv`, `inputs_by_season.csv`):
* **The 17 forms: no flag.** Scale ratios 0.93–1.02; level shifts within ±0.03 SD in every tour-season.
* **`points_52w`: flagged "uneven", in 27 of the 28 tour-seasons.**
  * Its spread **widens in every tour-season**: SD ratio 1.15–1.36 (men), 1.09–1.28 (women). Its level does not move
    (within ±0.05 SD).
  * The one unflagged cell is women's 2015 (ratio 1.094), just under the 10% line. Women's 2015 is the season with no
    lower-level box scores (role 01).
* **No input outside the 18 is flagged.**
* *Inferred.* Translating lower-level-heavy players' rates down separates them from main-tour players: their pooled
  Challenger and qualifying rates had made them look closer. This is a broad, every-season change, not finding #6's
  shape (a change confined to some seasons).
  * In its own season profile, the translated `points_52w` is, if anything, *more* even across eras than the
    reference's. Women 2019–2024: SD ratio to 2013–2021 of 0.93–1.02, against the reference's 0.89–0.94.
* **The pre-registered operational test applied as written.** It counts a flagged tour-season as unexpected when its
  mean share gap is below the tour's median. That holds for 13 of the 27 flagged cells (men 2013, 2015, 2016, 2019–2022;
  women 2013, 2014, 2016–2018, 2021). So `points_52w` counts as "an unexpected uneven input".
  * *Inferred:* the definition did not anticipate a change broad enough to flag almost every tour-season.

## The readings (2020–2024, both stages unless stated)

*Observed* (`candidates/results/pairs.csv`, `results.json`; each arm's `vs_reference_2026-10-08/scores.csv`). 22,265
matches (men 11,672, women 10,593), debut seasons out. **+ = the first-named model better.** The harness check holds:
the scorer's FP-vs-reference primary equals compare.py's to 1e-15.

| Comparison | Both tours | Men | Women |
|---|---|---|---|
| **FP vs reference (primary)** | **+0.024 [−0.047, +0.096], unresolved, P 0.75** | +0.083 [+0.002, +0.164], **better** | −0.040 [−0.154, +0.073], unresolved, P 0.24 |
| FP vs reference, stage 1 alone | +0.023 [−0.048, +0.095], unresolved, P 0.74 | +0.081 [−0.001, +0.162], unresolved, P 0.97 | −0.040 [−0.154, +0.073], unresolved |
| F vs reference (forms only) | −0.003 [−0.060, +0.054], unresolved, P 0.46 | +0.005 [−0.060, +0.069], unresolved | −0.010 [−0.104, +0.083], unresolved |
| P vs reference (`points_52w` only) | +0.029 [−0.019, +0.077], unresolved, P 0.88 | +0.066 [+0.001, +0.131], **better** | −0.012 [−0.086, +0.062], unresolved |
| FP_half vs reference | −0.009 [−0.064, +0.047], unresolved, P 0.38 | +0.027 [−0.031, +0.085], unresolved, P 0.82 | −0.048 [−0.129, +0.033], unresolved, P 0.12 |
| FP_placebo vs reference | −0.029 [−0.107, +0.050], unresolved, P 0.23 | −0.114 [−0.233, +0.005], unresolved, P 0.03 | +0.066 [−0.026, +0.157], unresolved, P 0.92 |
| **FP vs FP_placebo** | +0.053 [−0.036, +0.142], unresolved, P 0.88 | +0.197 [+0.059, +0.335], **better** | −0.106 [−0.231, +0.019], unresolved, P 0.05 |
| R_L vs reference | +0.039 [−0.128, +0.206], unresolved, P 0.68 | +0.096 [−0.105, +0.296], unresolved | −0.024 [−0.301, +0.254], unresolved |
| FP_L vs reference | +0.114 [−0.056, +0.284], unresolved, P 0.91 | +0.210 [−0.012, +0.433], unresolved, P 0.97 | +0.007 [−0.241, +0.255], unresolved |
| **FP_L vs R_L** | +0.075 [−0.007, +0.157], unresolved, P 0.96 | +0.115 [+0.001, +0.228], **better** | +0.031 [−0.099, +0.161], unresolved |
| R_S2 vs reference | +0.027 [−0.128, +0.182], unresolved, P 0.64 | +0.152 [−0.052, +0.357], unresolved, P 0.93 | −0.111 [−0.321, +0.098], unresolved, P 0.15 |
| **FP vs R_S2** (the addition) | −0.003 [−0.165, +0.160], unresolved, P 0.49 | −0.069 [−0.265, +0.126], unresolved, P 0.24 | +0.071 [−0.162, +0.304], unresolved, P 0.73 |

**FP against the reference within the pre-registered strata** (counts from `sides.parquet`; inputs moved = the median
absolute change of the 18 inputs in the reference's SD, averaged; `results/stratum_inputs.csv`):

| Stratum | Matches | Inputs moved | mLL [95%] | Reading |
|---|---:|---:|---|---|
| Less-exposed side under 10 main-tour results in 365 days | 5,913 | 0.18 | +0.040 [−0.152, +0.232] | unresolved, P 0.66 |
| 10 or more | 16,352 | 0.04 | +0.019 [−0.068, +0.106] | unresolved, P 0.66 |
| Share gap (365-day box scores) 0.5 or more | 5,619 | 0.24 | **+0.165 [+0.004, +0.326]** | **better**, P 0.98 |
| Share gap under 0.5 | 16,542 | 0.04 | −0.017 [−0.090, +0.055] | unresolved, P 0.32 |
| Falsification: both 20+ main-tour results, both shares under 0.10 | 3,652 | 0.00 | −0.033 [−0.155, +0.088] | unresolved, P 0.29 (read without a decision rule) |

104 matches where a side had no box score in 365 days are left out of the share-gap strata, as pre-registered.

**Reported without a decision rule.**
* **Each season** (FP against the reference):
  * 2020: −0.042 [−0.260, +0.176];
  * 2021: −0.070 [−0.244, +0.103];
  * 2022: −0.021 [−0.158, +0.116];
  * 2023: +0.026 [−0.120, +0.173];
  * all four unresolved;
  * 2024: **+0.183 [+0.020, +0.346], better.**
* **Each level** (compare.py), all unresolved:
  * Slams −0.040;
  * 1000s +0.104 [−0.022, +0.230], P 0.95;
  * 500s −0.069;
  * 250s +0.055;
  * Tour Finals −0.137 (150 matches).
* **Each model against its own calibrated close.** All are better than the close:
  * the reference: +1.374 [+0.668, +2.081];
  * FP: +1.399 [+0.683, +2.114];
  * F +1.372, P +1.403, FP_half +1.366, FP_placebo +1.346, R_L +1.413, FP_L +1.488, R_S2 +1.401.
* **Stage 2 barely notices.** The 2024 coefficients agree within 0.005 across every arm: s_atp 0.894–0.898, s_wta
  0.931–0.935, b̃ 0.027–0.028.

## The pre-registered verdict

* **The primary is unresolved:** +0.024 [−0.047, +0.096], P(better) 0.75. That is the pre-registration's "tie" branch,
  which recommends adopting on mechanism only if three conditions hold.
  * **No pre-registered secondary is worse:** holds. F, P, men, women, the four strata and FP_L against R_L are all
    "better" or "unresolved".
  * **Every secondary was scored:** holds.
  * **No unexpected uneven input:** **fails.** The operational test counts `points_52w` as unexpected (above).
* **So, by the rule as written: unresolved, and not suggested for adoption on mechanism.**
* **The conditions of the "better" branch** do not apply. For the record: FP does not beat its placebo on both tours
  (unresolved, P 0.88), and FP_L is not worse than R_L (unresolved, P 0.96).
* **The addition's reading:** FP's gain does **not** survive against R_S2 (−0.003 [−0.165, +0.160], P 0.49). Whatever
  the translation adds is, in this test, the share signal in disguise.

## Reading it (Inferred)

* **What is real.**
  * The equivalence problem is real, and the translation fixes it at the input level: G3, and the offsets' size.
  * The men's model gains a little from it: about +0.08 mLL. The gain lives in `points_52w`, and in the matches where
    one player's evidence is mostly lower-level and the other's is not.
  * That is where the mechanism says it should be. The falsification stratum, where nothing moved, shows nothing.
* **Why this is not enough to adopt.**
  * **The share variables carry the same information.** R_S2 matches FP overall (FP − R_S2: −0.003), and for men R_S2's
    estimate (+0.152) is higher than FP's.
    * TabPFN can already learn "this player's numbers come from Challengers" when it is given the share.
    * The translation spends 18 inputs' worth of change to deliver what two share columns deliver. *Inferred:* the
      translation's offsets are constants, so FP is close to a fixed linear re-weighting of the shares, as the red team
      argued.
  * **No dose-response.** Half the offsets (FP_half) reads −0.009, below both the reference and FP: in the noise.
  * **Women lean the other way:**
    * FP −0.040 (P 0.24);
    * FP against its placebo −0.106 (P 0.05);
    * R_S2 −0.111 (P 0.15).

    Role 03 found women's lower-level evidence worth about one-for-one after translation, and the women's bias in the
    IOS coming from the prior, not from equivalence. Consistent with that, there is little here for women.
  * **The size.** At best, a tenth of an mLL for men, against the model's +1.37 over the close. The primary's interval
    half-width is about 0.07 mLL with 4 seeds.
* **The `points_52w` flag.** I read it as a threshold artifact (above). If the owner sets it aside, the "recommend on
  mechanism" branch would pass its other conditions. Even then, the R_S2 reading says the mechanism argument is not
  specific to the translation.

## Suggestions

* **Do not adopt FP** on this evidence (Suggestion; the owner's call).
* **Keep the machinery for the ITF box scores** (role 01's highest forward risk): the hook, the offsets, the gates and
  the arms.
  * With ITF box scores of 2018–2024 (collection plan P7) wired into a candidate Stage 0, re-run this build. Move the
    offsets' window so that ITF and ITFQ get their own offsets instead of the Challenger placeholders.
  * Equivalence would then inflate ITF-active players by more than the Challenger +0.5 z, and the test would have more
    to find.
* **If a narrower version is wanted, pre-register it as a new candidate.** For example, `points_52w` translated alone
  (the only channel with a resolved men's gain), or the two share inputs of R_S2 in place of any translation.
  * Score it against both the reference and R_S2. Read on fresh seasons if the owner opens the holdout.
  * These ideas came from reading F, P and R_S2 here, so they are hypotheses, not findings.
* **Fix the input check's "unexpected" definition before the next candidate.** Read a flag against the tour-season's
  own change in evidence mix (for example the dose, mean share gap × offset), not against a median split.

## What it does not show

* **Small effects.** The primary's standard error is about 0.036 mLL; a true effect under about 0.1 mLL would usually
  read unresolved. Only seeds 0–3 were fitted; the decided application averages 16.
* **Fixed, same-season offsets.**
  * They come from player-seasons with matches at both levels, which selection pushes up (role 03, § 6). Role 03's
    forecasting fits found the predictive offsets as large or larger.
  * The level effects drift by era (role 03, § 2.3); a live version would refit them walk-forward. Only scale 1 and 0.5
    were tried: nothing was tuned.
* **What the translation leaves alone.** The opponents' norms are not translated: a main-tour match against a Challenger
  regular still reads his inflated "allowed" average. Stage B's decay and shrinkage constants were not re-tuned for the
  translated z.
* **ITF.** The ITF and ITFQ offsets are placeholders (Challenger's), and touch the 2025–2026 inputs only; nothing here
  tests them.
* **The joint solves** (IOS, serve and return ratings, Elo) are untouched; this role did not test them.
* **One placebo draw.** The placebo is one permutation. Its spread across tours (men −0.114, women +0.066) is itself a
  picture of how much a same-size, mechanism-free change moves the scores.
* **Not fresh data.** 2020–2024 has been read by many earlier studies; it is not an untouched holdout.

## Compute time

| Step | Time |
|---|---|
| Rate offsets (`offsets.py --rates`) | 16 s |
| Sandbox setup (18.1 GB copied) | 5 min |
| Lane 1 (19 steps, all exit 0) | 98.5 min (16:19–17:58 UTC) |
| Lane 2 (beside lane 1) | 19.7 min |
| Lane 3 and collect | 12 s |
| Gates G1–G3, `low_share_diff`, the arms | about 2 min |
| G4 (CPU, beside the fits) | 11.5 min |
| G5 (one fit, after waiting 200 s for another session's process) | 30 s |
| Fits: 8 arms × 24 (seasons 2019–2024, seeds 0–3), 16–17 s a fit, one at a time | 82 min (17:58–19:21 UTC) |
| compare.py (8 arms) and the scorer | about 5 min |
| Wall clock, pre-registration to the last score | 3 h 10 min (16:11–19:21 UTC) |

## Commands (from the repository root; the order run)

```
./python.sh src/eda/lower_level_evidence/offsets.py --rates
MODEL_REBUILD_SANDBOX=C:/Users/zerom/tnr_lle ./python.sh src/eda/model_rebuild/run_chain.py --setup --candidate
./python.sh src/eda/lower_level_evidence/sandbox_patch.py --sandbox C:/Users/zerom/tnr_lle
export MODEL_REBUILD_SANDBOX=C:/Users/zerom/tnr_lle IOS_CONSTANTS_VERSION=2026-10-08_reference \
       LLE_TRANSLATE=C:/Users/zerom/Documents/Tennis-predictions/data/studies/lower_level_evidence/candidates/hook_config_FP.json
./python.sh src/eda/model_rebuild/run_chain.py --lane 1 --out data/studies/lower_level_evidence/candidates/FP
./python.sh src/eda/model_rebuild/run_chain.py --lane 2 --out data/studies/lower_level_evidence/candidates/FP   # beside lane 1
./python.sh src/eda/model_rebuild/run_chain.py --lane 3 --out data/studies/lower_level_evidence/candidates/FP
./python.sh src/eda/model_rebuild/run_chain.py --collect --out data/studies/lower_level_evidence/candidates/FP
./python.sh src/eda/lower_level_evidence/offsets.py --check-forms
./python.sh src/eda/lower_level_evidence/offsets.py --summary
./python.sh src/eda/lower_level_evidence/candidate_arms.py --low-share
./python.sh src/eda/lower_level_evidence/candidate_arms.py --gates
./python.sh src/eda/lower_level_evidence/candidate_arms.py --build
./python.sh src/eda/lower_level_evidence/g4_linearity.py --sandbox C:/Users/zerom/tnr_lle
./python.sh src/eda/lower_level_evidence/candidate_arms.py --half
./python_tabpfn_local.sh src/eda/lower_level_evidence/candidate_fits.py --repro
./python_tabpfn_local.sh src/eda/model_rebuild/fits.py --out data/studies/lower_level_evidence/candidates/<FP|FP_placebo|F|P|FP_half> --seeds 0-3 --seasons 2019-2024
./python_tabpfn_local.sh src/eda/lower_level_evidence/candidate_fits.py --out data/studies/lower_level_evidence/candidates/<R_L|FP_L|R_S2> --seeds 0-3 --seasons 2019-2024
./python.sh src/eda/current_best_model/compare.py --candidate data/studies/lower_level_evidence/candidates/<arm>
./python.sh src/eda/lower_level_evidence/candidate_pairs.py
./python.sh -m pytest test/lower_level_evidence/test_translate_hooks.py -q
```

* **The fits' waiting rule.** Another session added a `--wait-memory-only` option to `model_rebuild/fits.py` at 16:28
  UTC (it changes only how a fit waits for the card). These fits used the default waiting. `candidate_fits.py` mirrors
  the option.

## The sandbox (not deleted)

* **Where:** `C:/Users/zerom/tnr_lle`.
* **How big:** 18.9 GB of its own files (`src/`, `docs/`, the `data/studies` copy with the chain's outputs, `logs/`).
* **The links:** two junctions, `data/dump` and `data/raw`, point to the repository's folders. They are links only,
  holding no data of their own.
* **Not cleaned up,** as the brief and CLAUDE.md require mid-session.
* **To remove it,** if the owner agrees:
  `MODEL_REBUILD_SANDBOX=C:/Users/zerom/tnr_lle ./python.sh src/eda/model_rebuild/run_chain.py --cleanup`. It removes
  the links first and checks that none is left before deleting.

## Files

| What | Where |
|---|---|
| Pre-registration, its hashes, the dated addition | `candidates/preregistration.md`, `preregistration.sha256`, `preregistration_addition.sha256` |
| The hook; the offsets; the patcher | `src/eda/lower_level_evidence/translate_hooks.py`, `offsets.py`, `sandbox_patch.py` |
| Arms and gates; G4; the 59/60-input fit runner; the scorer | `src/eda/lower_level_evidence/candidate_arms.py`, `g4_linearity.py`, `candidate_fits.py`, `candidate_pairs.py` |
| Tests | `test/lower_level_evidence/test_translate_hooks.py` (12) |
| Offsets (with counts and intervals), the untranslated z, the hook's call log | `candidates/offsets/` (`forms_offsets.csv`, `rate_offsets.csv`, `offsets_summary.csv`, `forms_z_untranslated.parquet`, `hook_calls.jsonl`) |
| The patch; the hook's config | `candidates/sandbox_patch.diff`, `candidates/hook_config_FP.json` |
| Gates and checks | `candidates/checks/` (`g1_*`, `g2_*`, `g3_*`, `g4_*`, `g5_fit_runner.json`, `arms_check.json`, `low_share_check.json`, `offsets_forms_rederived.json`) |
| The arms (frame, inputs, fits, compare.py's output) | `candidates/<arm>/` (about 46 MB each; 452 MB in all) |
| The readings and the verdict | `candidates/results/pairs.csv`, `results.json`, `stratum_inputs.csv` |
| The build's records and logs | `candidates/FP/chain_lane*.json`, `candidates/FP/chain_logs/`, `candidates/fits_queue.log` |
