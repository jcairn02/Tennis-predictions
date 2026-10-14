# The level layer in the current best model, and the men's 2026 Challenger data

10 October 2026 · For the owner · The record of carrying out two of the owner's requests of 10 Oct 2026. Process log:
[process_log.md](process_log.md). Decisions: [the level layer](../../decisions/2026-10-10-level-evidence-layer.md);
[the men's 2026 Challenger data](../../decisions/2026-10-10-men-2026-challenger-data.md).

**Keys.** mLL = milli-log-loss per match; + = the first-named model better. Intervals 95%. "Unresolved" when the
interval spans 0, with P(better). Both stages: TabPFN, then the serve-speed adjustment. Seeds 0–3, paired.

## In short

1. **The level layer is in the template, for men.** The study's SYS method, every setting as tested: lower-level
   observations translated by the opponent's strength gap and a level offset, weighted by an exchange rate capped at 1;
   ITF box scores excluded; women untouched. The hooks are in the decided builders, off unless `LLE_LAYER` names a
   config; the official config is `data/studies/current_best_model/level_layer/official.json`.
2. **It is what was tested, bit for bit.** On the reference's tables (today's equal them), the integrated builders
   reproduce SYS's inputs exactly on every input the decision keeps; with the layer off they reproduce today's
   template exactly.
3. **No harm.** Men, both stages, 2020–2024: −0.014 [−0.162, +0.134] mLL, unresolved, P(better) 0.42 (the study:
   −0.008). No edge credit: the case is the study's statistic-level evidence.
4. **The men's 2026 Challenger data is in, through the layer.** 1,735 men's 2026 matches Stage 0 lacked (Challenger
   qualifying after 1 June, a few Challenger main-draw matches), as a package every build merges into its own tables.
   No harm: men, both stages, 2026, +0.058 [−0.048, +0.164] mLL, unresolved, P(better) 0.89.
5. **Prediction runs** build with the same layer and package, resolved on their own Stage 0. The replay passes, bit
   for bit: 15 Jul 2026's 23 round-of-16 matches, rebuilt as live rows, get exactly the instance's 57 inputs.
6. **The current instance** is `data/studies/current_best_model/template_2026-10-10/` (the layer and the 2026 data;
   seeds 0–15).

## 1. What changed

| Where | What |
|---|---|
| 11 decided builders (`stage1_baselines`, `pieces`, `stage4_features`, `stage3_ratings`, `stageB_adjperf`; `rebuild`, `build_cache`, `build_features`, `surface_ios/arms`, `surface_ios/probe`, `tabpfn_leakproof/build_frame`) | The study's hook calls, as patched in its sandboxes, under a truthful tag. Off unless `LLE_LAYER` is set. Each equals the validated code, comments aside |
| `lower_level_evidence/level_layer.py` | `params_season_ceiling: "last_fitted"`: seasons after the last fitted one read its parameters |
| `lower_level_evidence/level_layer_ios.py`, `system_sandbox.py`, `system_arms.py` | The patch tools recognise the integrated builders and never overwrite the study's diffs; the fingerprint adds the ceiling only when set (the study's fingerprints unchanged) |
| `lower_level_evidence/relationship.py` | `--freeze` writes into `--out` and refuses an existing record (the study's never overwritten); `--mechanical` reads its own folder's record |
| `lower_level_evidence/candidate_stage0.py` | `--derive-from` with `--keep-tours/levels/years`; `--status-log` |
| `current_best_model/layer_config.py` (new) | The per-build config: the strength on the build's Stage 0, its check, the guard |
| `current_best_model/additions.py` (new) | Accepted lower-level packages, merged into a build's tables in its sandbox |
| `current_best_model/history.py` | An "accepted" class for those packages |
| `model_rebuild/run_chain.py` | `--prepare-layer`, `--lane N --layer` (the IOS part before `leakproof_frame`), `--additions`, the layer's records collected |
| `prediction_run/run.py`, `replay.py` | The layer resolved after Stage 0 and used by every later step (`--no-layer` for the old template); the accepted packages merged and their timeline pinned; `replay.py --compare --template` |
| `data/studies/current_best_model/level_layer/` | `official.json` (`be66df29…`), its writer, a README |

## 2. The checks

The live tables equal the frozen reference's (72 of 72 files), so every check is on the reference's tables. Builds:
B_off (the template, `LLE_LAYER` unset), B_on (the official config), B_new (B_on's recipe with the 2026 data). Files:
`data/studies/level_layer_adoption/checks/`, `results/`.

| Check | Result |
|---|---|
| Identity | **Pass.** B_off's chain frame equals the reference's on 57 of 58 inputs on all 67,226 matches; `indoor` differs only by the decided fill. With the odds input and list applied, B_off equals the current template's inputs (`indoor_fill/arm/`) on all 58 columns |
| Fidelity | **Pass, bit for bit.** B_on equals SYS on all 56 inputs compared (no tolerance used); `ios_points_short`, off, equals the reference's |
| Invariance (G2) | **Pass:** 149 of 149 checks bit for bit (women's every input; the untouched inputs; `ios_points_short`) |
| Direction (G3) | **Pass:** 16 of 17 cells; `form_first_in` under the ENV rule, SYS's verdict |
| Leaks | **Pass:** the builders' probes moved nothing protected; `match_timing/probe.py` with the layer on: 0 earlier matches moved at four cut days |
| Stage B pin | **In effect:** the men's constants re-tuned differently under the layer and were pinned to the reference's |
| Strength | **Pass:** the plain Elo on today's Stage 0 equals `strength_elo.parquet` on all 873,437 matches, bit for bit |
| Tests | **Pass:** 366, 6 expected failures (the final code). Unrelated failures elsewhere (3 + 3) compare the repository's own stale Stage 1/3/4 tables (built 30 Sep – 1 Oct) with the Stage 0 of 8 Oct |
| Harm check, layer | **No harm:** men, both stages, 2020–2024, −0.014 [−0.162, +0.134] mLL, P(better) 0.42 (11,672 matches). Both tours +0.022; women +0.062; every reading unresolved |
| Against the reference | `compare.py`: both tours +0.029 [−0.313, +0.372], unresolved; input flags identical to SYS's (the layer's dose), plus the indoor fill |
| Holdback | The new instance against the Pinnacle-first instance of 9 Oct (CLAUDE.md's control), both tours, both stages, 2020–2024: +0.018 [−0.125, +0.161], unresolved, P(better) 0.60. No harm; too small a batch for this control to see |
| Replay | **Pass, bit for bit.** A prediction run with the layer and the package replayed 15 Jul 2026's 23 round-of-16 matches as live rows (10 with the placeholder reversing the real result): all 57 inputs equal the instance's frame on all 23. Its data was held at the freeze (Tennis My Life's dump of 8 Oct, the template's timeline), so it proves the code path, not a live timeline rebuild on today's sources (`data/studies/prediction_run/replay_2026-10-10_layer/`) |

## 3. The men's 2026 Challenger data

* **What was on disk.** Stage 0 already held men's 2026 Challenger main draws (6,194 of 6,215 with box scores) and
  tour qualifying (734 of 739). It lacked Challenger qualifying after 1 June 2026. On disk those were results
  (TennisLive, SofaScore) with about 20 box scores. The owner chose role F's checked additions, men, 2026, CH and CHQ.
* **The candidate** C0_men26: F's C0_now cut to them (`candidate_stage0.py --derive-from C0_now --keep-*`): 1,735
  matches, 19 box scores, one completion; F's checks pass. Built with the layer (lane 0 first).
* **Its gate.** Women's inputs exact; on the 65,064 matches the additions cannot reach, every input exact except the
  joint solves, which differ by at most 7.9e-9. That is the solver's convergence: re-solving men's holds to 2025 at a
  1e-13 tolerance, the two builds agree to 8e-12 (`checks/solver_tolerance.json`).
* **The harm check** (men, both stages, 2026, the only season it reaches): **+0.058 [−0.048, +0.164] mLL, unresolved,
  P(better) 0.89** (2,190 matches); women −0.0004. Adopted under the owner's rule.
* **In production:** a package (`accepted_additions/men_2026_ch_chq/`) every build merges into its own tables; merging
  it into the frozen tables gives C0_men26's exactly. The repository's live tables are untouched.

## 4. What this does not show

* **A model-level gain.** Neither change resolves at the model level; both rest on their kind's evidence (a repair; more
  data of a kind already used).
* **The 2027 refit** is documented, not built: the study's estimator produces 2025–2026 rows only. Until it is, 2027
  rows read 2026's parameters.
* **Live data for future weeks.** The accepted 2026 data fills June–October 2026; Challenger qualifying after it still
  has no feed.
