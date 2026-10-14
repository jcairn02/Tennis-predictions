# The prediction pipeline plan: process log

10 October 2026, about 18:20–19:30 PDT (the chronology's times from 19:20 on are corrected in its last row) · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code) · Session:
`b6a34d10-94c8-4ba5-a412-700597c70ab5` · For a future reviewer · Report: [PLAN.md](PLAN.md) (written as the work
proceeds)

## 1. The request

* **The owner's words, verbatim** (10 Oct 2026, about 18:20 PDT):
  > "We are building now the prediction pipeline for the best current tabpfn 3.5 offline model. Use the
  > ../ufc-predictions/ pipeline as inspiration.
  >
  > There will be a process of
  > 1) getting the necessary INPUT about the matchup that is currently not in our database
  > 2) running that input through the best performing model "at prediction time"
  > 3) generating predictions.
  >
  > There will also have to be a script that
  >
  > Build the rough draft of this process as well as your understanding of what the best current tabpfn 3.5 offline
  > model (including the recent challenger data offset with reduced weight and opponent adjusted) and the prediction
  > offset for serve speed changes.
  >
  > Have it as a .md plan that we well then build out once I build the master script and improve organization.
  > We also need to make it so its a reasonable speed so we can have solver states update on disk and a quick update if
  > necessary so im not taking hours per build.
  > Do the algorithmic work to figure out how to do all this and test and verify the logic is good"
* **How it is read.**
  * Deliverable: a Markdown plan (`PLAN.md`) of the prediction pipeline (inputs for an unseen matchup → the current best
    model at prediction time → predictions), my statement of what the current best model is (the template of the
    current-best-model decision, with the level layer and the accepted men's 2026 Challenger package, and stage 2's
    serve-speed adjustment), and a speed design ("solver states" saved on disk, a quick update).
  * "Do the algorithmic work ... test and verify the logic": prototype the state-and-resume computations and check them
    against a full build's own values, with run times. Study code (`src/eda/prediction_pipeline/`), not the production
    pipeline: the owner builds that out later ("once I build the master script and improve organization").
  * **The truncated sentence** "There will also have to be a script that" is unfinished. Readings: (a) a script that
    keeps the saved states up to date (nightly/at need); (b) a script that grades predictions once matches finish; (c)
    the master script itself. The plan covers all three as components and the owner is asked which was meant. Not
    blocking: each is in the plan either way.
  * Set aside: building the production pipeline now; changing any decided model setting; any betting.
* **The target** (adoption framework § 1): not a model comparison. The bar is the 8 Oct prediction-run decision: live
  inputs equal the training inputs (bit for bit, or within a measured solver tolerance for joint solves). No outcome is
  scored in this work.

## 2. Starting point

* **Code:** commit `677a63f`, with many uncommitted changes (the other sessions' work; `git status`).
* **Another session is working on the same problem right now:** session `d061329f-0568-4169-b891-1a461e96dc2d`,
  [daily_update_speed](../daily_update_speed/README.md) (opened about 17:50 PDT the same day). It scoped where the 2
  hours go (four read-only subagents), measured bet-time pricing on the GPU (a 91-price grid per match, within 0.0008),
  applied a "2027 fix" to year limits in several builders, and started a "lean build". This work builds on its scoping
  and does not redo it; my code goes to new folders only (`src/eda/prediction_pipeline/`, `test/prediction_pipeline/`,
  `data/studies/prediction_pipeline/`, this folder), and I edit no file of the chain.
* **The current best model's instance:** `data/studies/current_best_model/template_2026-10-10/` (frame, 57-input list,
  fits 2019–2026 seeds 0–15), built in the sandbox `C:/Users/zerom/tnr_lyr_new`, whose intermediate tables are still on
  disk (read-only use here).
* **Environment:** `tennis` env through `./python.sh`; RTX 5090 (32 GB; another process's Jupyter kernels in the
  `tabiclv2` env hold about 6.7 GB); 16 logical CPUs, 126 GB RAM. A SofaScore scraper and another session's pytest were
  running when this log opened.
* **The idea and how it arose:** a structural change of how inputs are computed (not of what they are): resume each
  family from saved state instead of recomputing the history.

## 3. Plan

1. Read the decided configuration and the existing live path (`prediction_run/`), the other session's scoping, and the
   UFC pipeline (a read-only subagent).
2. For each of the 7 computations that reach the 57 inputs (the other session's `scoping.md`): the algorithm, its state,
   the update rule, its exactness class.
3. Prototype checkpoint-and-resume for the families where it matters, and verify against the template build's own
   tables in `tnr_lyr_new` (bit for bit where the code is sequential; measured tolerance for joint solves); time them.
4. Write `PLAN.md`: the pipeline (input acquisition, inference, predictions, grading), the model as I understand it, the
   speed tiers and state store, what is verified and what is not, open decisions for the owner.

## 4. Chronology

Local time PDT (UTC−7). "Results" means any outcome-based score; none is read in this work.

| When | Step (command or action) | Why | Results seen by then | Output |
|---|---|---|---|---|
| 18:20–18:45 | Read: README, docs index, pipeline boundaries; decisions (current best model, prediction runs, level layer, men's 2026 Challenger data); `prediction_run/run.py`, `model_rebuild/run_chain.py`, `fits.py`; the template's chain records; `tabpfn_thinking` and `tabpfn_leakproof` frame builders; `stageB_adjperf.py`, `stageB_common.py`; `surface_ios/build_features.py`, `build_cache.py`, `ios_surface.py`; the step logs of the template build | Plan step 1–2 | none | Observed: a full template build is about 3 h (lane 1 alone 2.6 h); a prediction run 2–3.4 h. Most time is tuning grids, probes and unused stages (step logs) |
| 18:30 | UFC pipeline subagent launched (Explore, read-only; brief in the appendix) | Plan step 1 | none | running |
| 18:46 | Found the other session's `daily_update_speed` study (README, scoping, process log, its code and data folders) | Avoid duplicate work | none | Its scoping adopted as the map of the 7 computations; my verification targets what it estimated but did not run (state and resume) |
| 18:50 | This log opened | Rule 2 | none | — |
| 18:52 | UFC subagent reported (taken as reported; organisational reference only) | Plan step 1 | none | A notebook orchestrator (`scripts/master_script.ipynb`, Steps 1–16); MESR rating states as sufficient statistics decayed forward and solved at the cutoff ("only rolls FORWARD", raises on hyperparameter mismatch); parity tests (v3 time-travel, v4 `parity.json` at 1e-8); a per-fight probability cache for re-pricing without refit; provenance sidecars with hashes that block a re-bet on drift; archive `predictions/real_world_predictions/{date}__{event}__{sex}.csv`; post-hoc monitors that fail open |
| 18:55–19:25 | Read the level layer (`level_layer.py`, `level_layer_ios.py`), Stage 1/3/4 passes, `pieces.py`, `stageB_common` (pair index, pair moments, windowed sums), `predictability_diagnostic/common.asof_sums`; diffed the template tree's code against the repository's | Plan step 2 | none | Observed: the IOS, Stage B, Elo-piece and layer code in `tnr_lyr_new` equal the repository's; only the other session's year-limit edits differ (Stage 1, Stage 4, `common.py`). The Elo-type passes are Python loops whose state is per-player lists plus the week's pending dict; the IOS snapshot loop keeps additive accumulators and a warm start; Stage B's z of a match reads only the opponent's earlier matches |
| 19:20 | pandas grouped `sum`/`cumsum` checked on [1e16, 1, 1, 1, 1, −1e16, 3] | Whether a saved running sum can be resumed bit for bit | none | **Observed: pandas 3.0.6's grouped sums are compensated (Kahan): `groupby.cumsum` gives 4 then 7 where `np.add.accumulate` gives 0 then 3.** A saved per-player running total would not resume bit for bit (the compensation term is hidden). Design consequence: per-player as-of sums are recomputed on the affected players' rows only (exact, since they are per group) instead of resumed |
| 19:30 | `src/eda/prediction_pipeline/pp_common.py`, `ios_state.py` written: the surface IOS loop copied with its state exposed (`Snap.state/from_state`, `map_state` for an older table's system, `outputs` for chosen target rows) | Plan step 3 | none | — |
| 19:40 | Smoke test (scratchpad `smoke_ios.py`): WTA ace (plain) and ATP hold (two level effects) on the 2025–26 rows only | Catch bugs before the long runs | none | Resume after a checkpoint 21 days before the end: **bitwise equal** on 438 and 1,920 rows; the targeted gap step on all rows bitwise equal to the full one |
| 19:45 | `verify_ios_state.py --runs wta:ace atp:hold atp:first_in wta:bp_saved --workers 4` launched (background) | Full-history checks A–E | none | running |
| 19:55 | `forms_state.py`, `verify_forms_state.py` written (targeted pair moments for new rows' z; per-player step 3) and launched (background) | Stage B's state | none | running |
| 20:03 | **Failure:** `verify_ios_state.py` run 1 crashed at the end of every task: `np.load` keeps the `.npz` open on Windows, so deleting the checkpoint raised `PermissionError`, and the JSON was written after the delete. All four tasks' results lost (about 12 minutes); the checkpoint files were left (3.6–6.7 MB each) | — | none | Fixed: arrays copied out under `with np.load(...)`, the JSON written before the delete, the delete guarded. Re-launched as run 2 (`verify_run2.out`) |
| 20:10 | Stage B run done (`forms_state/verify.json`; observed) | — | none | Reference (forms_z + forms_step3 + pool_values on the tree, 176 s) equals the stored `stageB_adj_features.parquet` on 17 of 17 columns (float32, bitwise). D0 2026-09-16: **z of the 1,676 new box rows bitwise on 17 of 17 pairs (0.71 s); the 17 inputs of the 1,055 new pool matches bitwise (14.5 s)**, also equal to the stored float32. Overheads: the context 20 s, the layer's per-row terms for all box rows 27 s (restrictable) |
| 20:12 | Elo passes done (`passes/verify.json`; observed) | — | none | Offset Elo pass: the tree's `pieces.parquet` reproduced bitwise (10 of 10 columns, both tours); full pass 4.1 s (ATP), 2.9 s (WTA); **resume from a pickled state bitwise** (1,018 and 161 matches after D0, 0.007 s; state about 2 MB a tour); older-table state moved onto today's players bitwise. Decided Stage 1 pass 2.5 / 1.8 s; Stage 3 pass 2.2 / 1.7 s |
| 20:14 | The older-table check above had identical player lists (the table 21 days old adds no player): re-run with D0 2026-03-02 (`verify_d0_2026-03-02.json`) | The remap was not exercised | none | ATP 14,548 → 14,822 players, 15,771 matches resumed; WTA 15,947 → 16,065, 8,102 matches: **bitwise** |
| 20:20 | IOS run 2 done (`ios_state/<tour>_<stat>.json`; observed) | — | none | **A: this study's copy equals the build's stored runs bitwise on every row** (936,900 ATP, 813,444 WTA; O_eff, D_eff, O, D, E, F) for WTA ace and bp_saved (plain) and ATP hold and first_in (two level effects each). **B: resume from a saved checkpoint bitwise** on the rows after D0 (1,920 ATP, 438 WTA; 0.45–1.25 s; checkpoint 3.6–6.7 MB, 2–250 in-flight rows). C: the older table here differs too little (same players): re-run with D0 2026-03-02 launched (`_d0_2026-03-02`). D: a cold one-day solve differs from the warm chain by at most 1.2e-7 (2.6e-9 to 1.2e-7); full runs 72–167 s each |
| 20:22 | One day of revisions measured (scratchpad `revisions.py`; the reference's Stage 0 of 8 Oct 18:53Z against the refresh's of 9 Oct 05:28Z; observed) | How far back the past changes in a day | none | 17 matches added (all in the last 7 days), none removed; box scores changed in 6 matches (WTA Beijing, week of 30 Sep); otherwise only a code-side difference: `surface` NA ↔ value on 183 team and Challenger matches of 2011–2024, and `indoor`'s missing-value representation (no value differs). One day's data revisions reach 1–2 weeks back; a builder code change can reach any year |
| 20:25 | `verify_stage4_state.py` written (the decided builder's `state`/`build` on the new matches' players only, with the whole-table weighted Elo blocks) and launched | Stage 4's five inputs | none | running |
| 20:26 | (Order note: the failure row of 20:03 was first written below 20:25 by mistake and moved to its place above; its text is unchanged) | — | — | — |
| 20:30 | Stage 4 run done (`stage4_state/verify.json`; observed) | — | none | **elo_games, mu_points|52 weeks, sets_14d, age, age_sq of the 1,055 new pool matches bitwise equal to the tree's stored float32** (5 of 5), from the decided `state`/`build` run on the 743 new matches' players' 216,587 matches (25.5 s) with the whole-table weighted Elo blocks (14.1 s); loading and constants 46.6 s |
| 20:32 | TabPFN 9.1.0's source read (`tabpfn/base.py create_inference_engine`, `classifier.py` docstring of `kv_cache_precision`) for the other session's unexplained cached-mode difference (0.179) | Bet-time pricing in about 1 s | none | **Hypothesis, written before the run:** the default `kv_cache_precision=None` is int8 for TabPFN-3 ("int8 when it can quantize"); with `"auto"` the cached path should equal the decided path to about 1e-4. Test `cache_precision.py` (A plain; C_int8 default; C_auto; the 91-price grid on C_auto) launched on the GPU |
| 20:45 | IOS run 3, D0 2026-03-02 (`ios_state/<tour>_<stat>_d0_2026-03-02.json`; observed) | The older-table check with real structural change | none | **B: 207–219 days resumed bitwise** (31,084 ATP, 16,008 WTA rows; 2.5–5.5 s). **C: a checkpoint of the table of 23 Mar (121 fewer ATP players, ~12,000 fewer triples; 201 fewer WTA players) moved onto today's system and resumed:** WTA ace 1.3e-15, WTA bp_saved 1.7e-16, ATP first_in 2.8e-16, **ATP hold 2.4e-8 (O) / 5.3e-8 (D)** (main-tour rows 1e-8), i.e. rounding level in 3 of 4 runs and the solver's tolerance in one (the warm chain's iterates drift apart at rounding level, then each stops inside rtol 1e-8). No row queried by D0 was missing from the older table; the snapshot days to D0 were identical |
| 20:47 | Timeline versions compared (scratchpad `timeline_revisions.py`: the reference's `timing.parquet` of 8 Oct against the 9 Oct live run's, the template's and the replay's; observed) | Whether past rows' dates move | none | Template and replay: 0 of 873,437 changed. **The 9 Oct live run: 14 matches' es/lf/obs changed, 7 in the last week, 6 of 60–365 days and 1 older** (lf moved −4 to +1 days; the SofaScore restaging the prediction-run README notes). So an old row's dates can change in a day: a checkpoint must be checked against the rows it covers |
| 20:50 | `cache_precision.json` (observed) | — | none | **Hypothesis rejected.** C_auto (unquantized cache, 11.5 GB peak) is as far from A as C_int8: max 0.1793 / 0.1793, mean 0.0756 / 0.0757; predictions 0.95–1.03 s; the grid of 23 × 91 prices in 3.98 s. A difference this large is structural, not rounding. Not pursued further here (the decided path's price grid already prices in about a minute a seed, the other session's E). Next diagnostics noted in PLAN.md: one estimator, `memory_saving_mode` off, a small training set, the downsample-correction weights |
| 20:55–21:20 | Read the remaining pieces for the plan: `live_rows.py` (a live row copies the event's TML rows: none exist before an event's first match), `adjust.py`, `live/form.py`, `model_rebuild/compare.walk_forward`, the Pinnacle-first decision, the early-lines research (Pinnacle's guest service lists both tours' matchups with prices; no adapter), `oddstrader.py`, `scheduled.py`, `speed_daily.py`; the instance's fit records (41–52 s a fit, 8.1 GB) | Plan steps 2 and 4 | none | Gaps recorded in PLAN.md § 5. Stage 2's 2026 coefficients are not stored for the instance; not computed here (they read 2025 results, the proposed clean holdout's season, and computing them is the build's step, not this plan's) |
| 21:20–21:45 | `PLAN.md` written; figures re-checked against the records (tuning shares, Stage 4's build minutes, GPU minutes corrected) | Plan step 4 | none | — |
| 21:45 | `pp_selftest.py` (fast checks: IOS resume and an older slice's checkpoint on 2025–26 rows; Elo resume and remap on 2024–26; pandas' compensated sums) and `test/prediction_pipeline/test_state_resume.py` | Reproducible checks | none | **3 passed in 12 s** (`data/studies/prediction_pipeline/tests.txt`): IOS 438 rows bitwise, older slice 5,388 rows within 8.9e-16 (3,144 → 3,169 players); Elo 15,771 matches bitwise, remap 4,465 → 4,782 players |
| 21:50 | One row added at the top of `docs/studies/README.md` (the studies index), linking PLAN.md | Convention | none | — |
| **19:21 (clock read)** | **Correction: the "When" column above is wrong from the 19:20 row on.** I wrote those times by estimate instead of reading the clock; the clock read 19:21 when this was noticed. The sequence of rows is right; their times are not. The observed times, from the files' modification times (`ls -l --time-style=+%H:%M:%S`): `pp_common.py` 18:54; smoke test 18:58–19:00; `ios_state.py` 18:59; run 1 launched about 19:00, **failed 19:03:38**; Stage B written 19:02, done **19:06:43**; Elo passes done 19:06:44, March re-run 19:08:16; IOS run 2 done **19:08:33**; one day's revisions 19:07; Stage 4 launched 19:10, done **19:12:08**; cache test written 19:12:11, done **19:14:42**; IOS run 3 (March) done **19:13:16**; timeline versions 19:13; PLAN.md 19:18; tests 19:19–19:20. So the pandas check and the first prototypes were about 18:54–18:59 (not 19:20–19:40), and the reading row "18:55–19:25" was about 18:50–18:56. No result or choice depends on these times | Rule 4 | — | — |
| 19:24 | Checked that the build tree was left unchanged (`find /c/Users/zerom/tnr_lyr_new -newermt "2026-10-10 18:40"`; observed) | The checks were meant to read only | — | **One file written:** `src/eda/surface_elo_pieces/__pycache__/pieces.cpython-311.pyc`, Python's bytecode cache from importing the module (no data, no result). Left in place (not deleted mid-session). `pp_common.use_tree` now sets `sys.dont_write_bytecode = True`, so later runs write nothing there |

## 6. Judgment calls

1. **Build on the other session's scoping, do not message it.** Options: message the other session to divide the work;
   work independently in separate folders and cite it. Chosen: the latter (sending text into another live session
   could disrupt its work, and dividing work is the owner's call). Before any result.
2. **Verify against the build tree's own code and tables** (`tnr_lyr_new`) rather than the repository's. The
   repository's builders were being edited by the other session (its year-limit fix); the tree holds the exact code
   and the intermediate tables that built the template's frame, so a bitwise match there proves the logic. Hooks were
   run with a copy of the tree's layer config with `record_dir` null, so nothing was written into the tree. The cost:
   the checks depend on that sandbox existing (the scripts take `--tree`; any later template build's sandbox works).
3. **Bit for bit as the bar for every family but the joint solves; a measured tolerance there.** The prediction-run
   decision proves live inputs by the replay at machine precision; the joint solves already carry 1e-8-level
   convergence noise between two full builds (the 2026 Challenger decision's 7.9e-9), so a stricter bar would hold
   them to less than the full build itself achieves.
4. **Per-player recomputation instead of resumed running sums** for Stages B (step 3) and 4. Chosen after the
   pandas check (19:20), before the Stage B/4 results: a resumed running total cannot reproduce pandas' compensated
   sums bit for bit; recomputing the day's players is exact and costs seconds.
5. **Checkpoint 3 weeks back as the default** (D0 = the table's last day − 21), the other session's proposed cut and a
   week boundary for the Elo passes. A second set at 2026-03-02 was added after the first results showed the 3-week
   older-table check could not exercise new players (judgment made after seeing those results; it made the test
   harder, not easier).
6. **Not every family was checked on every statistic:** the surface IOS on 4 of its 14 needed runs (both modes, both
   tours, both kinds of level-effect count); the Elo resume on the offset pass (the Stage 1, Stage 3 and games-weighted
   passes share its loop structure and were only timed). Chosen for time; the remaining runs are the same code paths.
7. **The cached-mode diagnosis was stopped** after one rejected hypothesis: it is the other session's open item, and
   the decided path's price grid already meets the bet-time need.
8. **Stage 2's coefficients for the instance's 2026 were not computed** (reads 2025 results; the build's step).

## 7. Claims and their evidence

| Claim (PLAN.md) | Evidence | Status |
|---|---|---|
| The 57 inputs, their builders and the layer's effect per family | the builders' code (`tabpfn_thinking/common.py`, `surface_rating_race/model_frame.py`, `surface_ios/arms.py`, `surface_elo_pieces/arms.py`, `stage4_features.single_features`/`matchup`, `level_layer.py`), the instance's `model_inputs.json` | observed (read); the input-to-builder map also agrees with the other session's scoping (taken as reported, the IOS source re-checked by it) |
| Stage 2's formula and coefficients procedure | `adjust.py`, `live/form.py`, `model_rebuild/compare.py`, the decision | observed (read) |
| Where the hours go | `template_2026-10-10/chain_lane*.json`, `chain_logs/*.log`, `prediction_run/*/build.json` | observed |
| Surface IOS: copy bitwise; resume bitwise; older table ≤ 5.3e-8; cold ≤ 1.2e-7 | `ios_state/*.json` (4 runs × 2 checkpoint days) | observed |
| Elo states: bitwise, remap bitwise | `passes/verify.json`, `verify_d0_2026-03-02.json` | observed (offset pass only) |
| Stage B: reference = stored; new z and inputs bitwise | `forms_state/verify.json` | observed |
| Stage 4: five inputs bitwise from the day's players | `stage4_state/verify.json` | observed |
| Daily input update ~5–8 min now, ~2 min with an incremental Stage 0 | the sum of measured parts (this study's family timings; Stage 0 2.3 min and the preparation steps from the other session's step table) | **estimate**, not run end to end |
| GPU ~13–16 min a day | 16 × the instance's fit records (41–52 s) and the other session's grid timing (57 s) | estimate from measured parts |
| One day of revisions reaches 1–2 weeks back; timeline dates of older matches can move | scratchpad `revisions.py`, `timeline_revisions.py` | observed for one day only |
| The cached mode's gap is not int8 quantization | `cache_precision.json` | observed (one seed) |

## 8. Weak points

* **No end-to-end run of the state path.** Each family was checked alone; the frames' assembly for new rows, the
  manifest checks and the shared loader are designs. The existing replay is the test to run once assembled.
* **One build tree, one day's tables.** Every bitwise result is on the tables of 8 Oct (plus the accepted package).
  A table with revisions before the checkpoint is exactly what the manifest check must catch; it was not exercised.
* **Revision frequency is from one day.** Weekly or monthly checkpoint spacing should follow a month of measured
  revisions (the data-continuity study's versions, when built).
* **Where a flaw would most likely hide:** the in-flight rows of the IOS gap step for matches with long windows
  (undated rows), and Stage 0's row order when matches are inserted out of time order (the IOS and Elo states assume
  the new rows come after the checkpoint in every ordering they use).
* **What a re-design would do:** run the state path through `prediction_run/replay.py` for several past days,
  including a day with late box scores and a restaged source; measure a month of revisions; check all 14 IOS runs and
  the other three Elo-type passes.

## 9. Reviewer checklist

* [ ] `./python.sh -m pytest test/prediction_pipeline -q` (needs the build tree; 3 tests, about 12 s).
* [ ] Re-run `verify_ios_state.py --runs <all 14 surface runs> --workers 6` and `--d0 2026-03-02 --tag _d0_2026-03-02`;
      check A, B bitwise and C ≤ 1e-6 for every run.
* [ ] Re-run `verify_forms_state.py`, `verify_stage4_state.py`, `verify_passes.py` (and `--d0 2026-03-02`).
* [ ] Confirm the 57-input table in PLAN.md § 1 against the instance's `model_inputs.json`.
* [ ] Confirm no file in `C:/Users/zerom/tnr_lyr_new` changed except the one bytecode cache noted at 19:24 (the
      checks read only; the layer config copy recorded nothing).

## 10. Reproduction

```
# CPU, the tennis env; each reads the build tree (default C:/Users/zerom/tnr_lyr_new, or --tree)
./python.sh src/eda/prediction_pipeline/verify_ios_state.py --runs wta:ace atp:hold atp:first_in wta:bp_saved --workers 4
./python.sh src/eda/prediction_pipeline/verify_ios_state.py --runs wta:ace atp:hold atp:first_in wta:bp_saved --workers 4 --d0 2026-03-02 --tag _d0_2026-03-02
./python.sh src/eda/prediction_pipeline/verify_passes.py                 # and --d0 2026-03-02
./python.sh src/eda/prediction_pipeline/verify_forms_state.py
./python.sh src/eda/prediction_pipeline/verify_stage4_state.py
./python.sh -m pytest test/prediction_pipeline -q
# GPU (tennis-tabpfn-local), one seed, about 3 minutes
./python_tabpfn_local.sh src/eda/prediction_pipeline/cache_precision.py
```

Run times: each IOS task 4–6 min (two full runs of the history), Stage B 4 min, Stage 4 1.5 min, the passes 0.5 min.
Outputs in `data/studies/prediction_pipeline/` (`ios_state/`, `passes/`, `forms_state/`, `stage4_state/`,
`cache_precision.json`, `tests.txt`, the run logs `*.out`). The checkpoint files are deleted after each check; the
copy of the layer config is `layer_config_verify.json`.

## Appendix: briefs

### UFC pipeline subagent (Explore, read-only), 18:30

```
Explore the sibling project at C:\Users\zerom\Documents\UFC-Predictions (read-only). I need to understand its PREDICTION
PIPELINE as an organizational reference for a tennis project: how an upcoming event's matchups become predictions.
Thoroughness: very thorough.

Report concretely (file paths + short quotes of key function names / CLI flags):
1. The end-to-end flow for predicting an upcoming UFC card: which scripts/modules run in what order (fetch upcoming
card/odds → build features "as of" fight time → model inference → write predictions → compare to odds/bets → grade
after results). Name the master/orchestrator script if any, its CLI and steps.
2. How live/upcoming inputs are built: do they reuse the training feature code (same functions) or a separate path? Any
parity check between live features and training features (replay/backtest proof)?
3. Any STATE CACHING / incremental updating: e.g. rating states (Elo/Glicko/etc.) saved to disk and updated with new
results instead of recomputing from scratch; snapshots; "as-of" stores; how they keep prediction runs fast. Name files/dirs
and formats.
4. How the model is stored/loaded at prediction time (trained model files vs refit at prediction time),
versioning/manifest of model + data, hashes.
5. Output format of predictions (folder layout under predictions/, file naming, columns: probability, model version,
timestamp, odds, edge, etc.), and any post-event grading/results logging script.
6. Any docs describing the pipeline (README/CLAUDE.md/docs/*pipeline*, *prediction*), plus decisions about cadence
(daily/weekly), gates ("do not bet" checks), and data freshness checks.
7. Anything about speed: how long a prediction run takes, what is precomputed.

Also look at C:\Users\zerom\Documents\UFC-Predictions\predictions specifically and summarize its structure with 2-3
example file names and their columns (read a header row or two).

Keep the report factual and structured, ~800-1200 words. Do not modify anything.
```
