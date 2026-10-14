# Task: make the level layer (the "final method") part of the official current best model, for men

You are working in the tennis-prediction repository at `C:\Users\zerom\Documents\Tennis-predictions` (Windows; Git
Bash or PowerShell). The owner wants the final method of the level-evidence study made part of the official current
best model. Implement it, verify it as specified below, record it, and report back.

**Ground rules.**
* Read `CLAUDE.md` first and follow it:
  * Python only through `./python.sh`; GPU fits through `./python_tabpfn_local.sh`.
  * No state-changing git; the owner commits.
  * Delete nothing.
* Do not modify the frozen reference (`data/studies/current_best_model/reference_2026-10-08/`) or the study's evidence
  (`data/studies/lower_level_evidence/system/`).
* If a step needs a choice this prompt does not settle, ask the owner. Do not guess.

## 1. What the final method is

**Read first:**
* `docs/studies/lower_level_evidence/system/README.md`: the system, the evidence, the proposal.
* `docs/studies/lower_level_evidence/system/SPEC.md` §3: the relationship.
* `C_layer.md` and `C_layer_ios.md`: the hooks and their insertion points.
* `B_relationship.md`: the parameters. `A_classes.md`: the statistic classes.
* `data/studies/lower_level_evidence/system/preregistration_addition_3.md`: the frozen internals, with hashes.

**The tested configuration** is `data/studies/lower_level_evidence/system/arms/configs/SYS.json`. Use it as the
specification of every setting.

**In short.** For men's matches only, each lower-level observation (tour and Slam qualifying, Challenger main draw and
Challenger qualifying) enters the history inputs in main-tour terms. Four rules:

1. **Translation.** Shift each observation by γ_s × (the opponent's pre-match Elo − the main-tour reference strength),
   plus δ_{s,L} where `classes.csv`'s `delta_levels` allows it. Statistics in the ENV class (first serves in, double
   faults) take δ only.
2. **Weight.** Count each observation at w_{s,L}: role B's fitted value, capped at 1 (Challenger about 0.6, qualifying
   about 1).
3. **Per input family:**
   * `points_52w`: rates translated and weighted.
   * One-step forms (`adjperf_tpw_2w`, `form_*`, `formdef_*`):
     * the opponents' norms are re-referenced row by row;
     * the match's own value takes δ only;
     * the weights apply in the decay-and-shrink;
     * Stage B's tuned constants are pinned to the reference's (the `pins` entry of `SYS.json`).
   * Joint solves (surface IOS O/D and the products): a level effect estimated inside each solve (form b) at the
     allowed levels, with row weight `w_joint`.
   * `ratings_iid`: weight `w_joint`, no level term.
   * Elo family: K × w_results, and the rated-match count advances by w_results. Men's ITF results are worth about
     0.25–0.5 and ITF-qualifying results 0, all capped at 1.
4. **Exclusions and scope.**
   * ITF and ITF-qualifying box scores are excluded (w = 0) until the P7 ITF data gives training-season parameters.
   * Women are untouched (`tours: ["atp"]`).
   * Parameters are chosen by the row's own season. Rows before 2013 use 2013's parameters (`params_season_floor`).

Age, workload counts, context, odds and the stage-2 serve-speed adjustment are untouched.

## 2. The official template today

**Read:**
* `docs/decisions/2026-10-08-current-best-model.md` and its amendments;
* the "current best model" section of `CLAUDE.md`;
* `docs/decisions/2026-10-09-pinnacle-first-odds-input.md`;
* `docs/decisions/2026-10-09-adoption-by-change-class.md`.

As of 10 Oct 2026 the template is:
* local TabPFN-3.5 on **57 inputs** (`ios_points_short` was dropped on 9 Oct);
* the **Pinnacle-first** odds input (`src/eda/current_best_model/odds_input.py --apply`);
* stage 2 as before.

The study verified the layer on the frozen reference: 58 inputs, books'-average odds. So it must be re-verified on the
current template.

**Before building,** inspect `git status` and `git diff` read-only. Another session left an uncommitted change in
`src/eda/tabpfn_thinking/build_frame.py`: it fills women's `indoor` input from the WTA calendar. Do not include it or
revert it silently. Ask the owner whether it is part of the template.

## 3. Implementation

**The recommended route: integrate the hooks permanently, switched by config.**

Today the layer reaches builders only through sandbox patches. `src/eda/lower_level_evidence/system_sandbox.py --patch`
applies C1's diffs (`data/studies/lower_level_evidence/system/arms/patches/*.diff`) and `level_layer_ios.py`'s
`apply_patch`.

1. **Put the same hook calls into the decided builders,** at the same insertion points. The hook maps are in
   `C_layer.md` and `C_layer_ios.md`:
   * `predictability_diagnostic/stage4_features.py`: `points_52w`, `elo_games`;
   * `ufc_ideas/stageB_adjperf.py` and `stageB_common.py`: the forms and the Stage B pin;
   * `predictability_diagnostic/stage3_ratings.py`: `ratings_iid`;
   * `predictability_diagnostic/stage1_baselines.py` and `surface_elo_pieces/pieces.py`: Elo;
   * `surface_ios/build_cache.py` and `build_features.py`, with the guards in `tabpfn_leakproof/build_frame.py` and
     `surface_ios/arms.py`;
   * `match_timing/rebuild.py`: the IOS part (`level_layer_ios.run_ios_part`), which runs before lane 1's
     `leakproof_frame` when the IOS families are on.

   Two constraints:
   * **Off by default.** Every hook must do nothing when `LLE_LAYER` is unset.
   * **One implementation.** Import `level_layer.py` and `level_layer_ios.py`; do not copy their logic.
2. **Write the official config.** Copy `SYS.json` to a template location, for example
   `data/studies/current_best_model/level_layer/official.json`.
   * Keep every setting as in `SYS.json`:
     * `tours ["atp"]`, `translate true`, `weight "fitted"`, `weight_results "fitted"`, `itf_box "exclude"`;
     * `fitted_cap 1`, `fitted_cap_results 1`;
     * `solve_w "w_joint"`, `ios_level_term "fixed_effect"`, `ratings_level_term "none"`;
     * `params_season_floor 2013`, `prior "pool"`, `elo_count "weighted"`;
     * the same Stage B pin.
   * Point it at the frozen files, with their hashes:
     * `relationship/params.parquet`: 4c559abd…;
     * `classes/classes.csv`: 58e78622…;
     * `classes/strength_elo.parquet`: 4fa9a573….
   * Set `families.ios_points_short` to false, unless the chain's mapping check still needs the IOS part. In that case
     keep the part and verify (`C_layer_ios.md`).
3. **Two gaps the study did not need, and production does.**
   * **Seasons after the last fitted season.** `params.parquet` covers seasons used through 2026. Add a ceiling rule to
     `level_layer.py`: seasons after the last fitted one use the last fitted season's parameters until the next refit.
     That is leak-free, because those parameters were fitted on earlier data.
   * **Opponent strength for matches after the freeze.** `strength_elo.parquet` covers only the frozen reference's
     matches. Each template build must compute the plain pre-match Elo (the reference's K, without the w_results hook)
     on its own Stage 0 and use it as the strength.
     * Check that it equals `strength_elo.parquet` on the reference's matches, and explain any difference. Main-tour
       revisions are now allowed by `history.py`.
     * If the scale shifts, re-centre by tour and season, as addition 7 did for NEW_SYS_BOTH (option c).
4. **The template build.**
   * `run_chain.py --setup`, then every lane with `LLE_LAYER=<official config>` (the IOS part before lane 1's
     `leakproof_frame`), then `--collect`;
   * `odds_input.py --apply` (Pinnacle first);
   * `fits.py`, seeds 0–15;
   * stage 2 as today.
5. **Prediction runs.** `src/eda/prediction_run/run.py` builds live inputs through the same chain. It must set the same
   `LLE_LAYER`. `src/eda/prediction_run/replay.py` must still show live inputs equal to the template frame's.

## 4. Verification (all must pass)

| Check | Pass condition |
|---|---|
| **Identity** | With `LLE_LAYER` unset, the integrated builders reproduce the current template's inputs exactly, on every input and every match |
| **Fidelity** | On the frozen reference's tables, with the official config, the integrated builders reproduce the study's SYS inputs (`data/studies/lower_level_evidence/system/arms/SYS/model_frame.parquet`) bit for bit. Allow at most 1e-12 of documented solver rounding in IOS columns. This proves you built what was tested |
| **Invariance** | Women's inputs and every untouched input are unchanged |
| **Direction and leaks** | `src/eda/lower_level_evidence/system_gates.py` (G2, G3 with the ENV rule, G5); `src/eda/match_timing/probe.py` and the builders' own probes; the Stage B pin in effect |
| **Strength** | The plain Elo equals `strength_elo.parquet` on the reference's matches |
| **Tests** | Everything in `test/lower_level_evidence/` passes, plus new tests for the integration: the hooks are no-ops when off, the ceiling rule, the strength refresh |
| **Harm check** | The owner's 9 Oct rule for a repair (below) |
| **Replay** | `replay.py` passes |

**The harm check.** Build the current template with and without the layer, on the same tables. Score men, both stages,
2020–2024, seeds 0–3, paired: reuse the pairing in `src/eda/lower_level_evidence/system_pairs.py`.
* **Adopt unless it shows harm:** worse by more than 0.10 mLL, with the whole 95% interval below 0.
* **Expect "unresolved".** The study measured −0.008 [−0.162, +0.145] on the frozen reference.
* **No edge credit.**

## 5. Records

* **A decision record:** `docs/decisions/<date>-level-evidence-layer.md`. It holds:
  * the owner's instruction, verbatim;
  * what changes;
  * the evidence (link the study README);
  * the verification results;
  * the maintenance rules (§6).
* **A dated amendment** to `docs/decisions/2026-10-08-current-best-model.md`: the recipe now builds with the level layer
  for men.
* **One bullet in `CLAUDE.md`'s current-best-model section,** with the config path and the refit rule.

## 6. Maintenance rules (implement and document)

* **Yearly,** at the first build after a season ends, refit the parameters walk-forward with
  `./python.sh src/eda/lower_level_evidence/relationship.py --method F4 ...`.
  * The default method is F5. The frozen method is **F4**.
  * The output goes to a new folder. Make sure `--freeze` writes into `--out` and never overwrites the study's
    `method_freeze.json` (`P7_plan.md` §10 lists this change).
  * Update the official config's path and hash, re-run the identity and strength checks, and record the refit.
* **Classes:** keep A's frozen thresholds. Re-check yearly with `classify.py`.
* **New lower-level data,** for example P7's ITF box scores (about 22 Oct – 2 Nov 2026): follow
  `docs/studies/lower_level_evidence/system/P7_plan.md`. ITF stays excluded until then. Women stay untouched until then.

## 7. Open points: report them, do not resolve them silently

* **An optional variant the study's lead suggested:** the same layer with Elo results unweighted (`weight_results: 1`).
  * The Elo discount was the weakest part: worse on 2020–24 for matches involving players with little main-tour
    history (−0.18 [−0.31, −0.05]).
  * Build it and harm-check it only if the owner asks.
* **The women's `indoor` change** (§2).

## 8. Report back

At most 30 lines:
* the files changed;
* each check's result;
* the harm-check reading, with its interval;
* anything not done, and why.
