# The level layer in the current best model (men), and the men's 2026 Challenger data: process log

10 October 2026, 10:00–17:10 PDT · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code) · Session:
`d061329f-0568-4169-b891-1a461e96dc2d` · For a future reviewer · Report: [README.md](README.md) (written at the end)

## 1. The request

* **The owner's words, verbatim** (10 Oct 2026, about 17:00 UTC). The message was a pasted task brief, the study
  lead's `docs/studies/lower_level_evidence/system/IMPLEMENTATION_PROMPT.md` (sha256 `7f0ce83d…`, 187 lines, identical
  to the paste). Its first lines:
  > "# Task: make the level layer (the "final method") part of the official current best model, for men
  > [...] The owner wants the final method of the level-evidence study made part of the official current best model.
  > Implement it, verify it as specified below, record it, and report back."

  The brief's binding parts (quoted from the file): §1 the method (`SYS.json`); §2 "Before building, inspect `git
  status` and `git diff` read-only [...] Ask the owner whether it is part of the template"; §3 the integration ("Off by
  default", "One implementation"), the official config, the two gaps (a ceiling rule for seasons after the last fitted
  one; the opponent strength refreshed per build), the template build, prediction runs; §4 the checks (identity,
  fidelity, invariance, direction and leaks, strength, tests, harm check, replay); §5 the records; §6 maintenance; §7
  open points; §8 a report of at most 30 lines.
* **A second request, mid-turn** (10 Oct, about 17:05 UTC), verbatim:
  > "Also Wire in the 2026 challenger data we already have to the model, including the 2026 men's qualifying box
  > scores sitting on disk. That fills a live gap."
* **Questions put to the owner, and the answers** (AskUserQuestion, 10 Oct about 17:10 UTC):
  1. The uncommitted women's `indoor` fill in `tabpfn_thinking/build_frame.py`: "Include it (Recommended)" chosen. It
     is the owner's recorded request of 9 Oct (`docs/decisions/2026-10-09-indoor-input.md`), already in CLAUDE.md.
  2. Which 2026 data. My findings put to the owner: Stage 0 already holds men's 2026 Challenger main draws through
     5 Oct (6,194 of 6,215 with box scores) and men's tour qualifying (734 of 739 with box scores); it lacks men's
     Challenger qualifying after 1 June 2026; on disk those are 1,723 matches as results (TennisLive, SofaScore
     listings) with box scores for about 23; TDI holds 87 men's 2026 tour-qualifying rows Stage 0 lacks. Answer:
     "Men's 2026 CH + CHQ (Recommended)": role F's checked additions, 1,735 men's 2026 Challenger and
     Challenger-qualifying matches, entering through the level layer, built as a candidate on the layer template and
     adopted unless the harm check fails; ITF and women stay out.
* **How it was read.**
  * The layer: implemented as the brief says; the brief's open points (§7) are reported, not resolved.
  * The 2026 data: a candidate Stage 0 holding the frozen Stage 0 plus role F's men's 2026 CH and CHQ additions
    (from `system/stage0/C0_now/`), built with the layer, harm-checked against the layer template. Not: TDI's rows,
    2025's additions, ITF, women (the owner chose the first option).
  * Set aside: reading "the 2026 men's qualifying box scores" as tour qualifying (Stage 0 already holds them with box
    scores) or as Slam qualifying (432 of 448 already with box scores).
* **The target.** The harm checks are the owner's 9 Oct rule for a repair: men, both stages, seeds 0–3 paired;
  2020–2024 for the layer (fixed by the brief before any result); 2026 for the 2026 data (the additions are all in
  2026, so 2020–2024 cannot see them; fixed here, before any build). Primary: mLL per match at the frame's closing odds
  input (Pinnacle first), both stages. No edge credit for either.

## 2. Starting point

* **Code:** commit `677a63f` (8 Oct) plus many uncommitted changes by other sessions (git status: 296 entries). The
  layer modules on disk equal the frozen hashes (`level_layer.py` 26e21291…, `level_layer_ios.py` 3fa5f69e…). The
  repository's 11 builders plus the study's C1 and C2 patch texts equal the validated snapshot
  (`system/arms/validated_src/`) byte for byte (observed, 17:0x UTC). Other chain modules that differ from the snapshot:
  `tabpfn_thinking/build_frame.py` and `common.py` (the indoor fill), `stage0_build.py` and `corrections.py` (an added
  correction action no decided table uses), `run_chain.py` and `history.py` (the 9 Oct narrowing).
* **Data:** the repository's 72 live table files equal the frozen reference's hashes (`system_sandbox.check_tables()`,
  observed 17:0x UTC). So the template's tables today are the frozen reference's tables.
* **Earlier looks:** the level-evidence study read 2020–2024 and the 2025–2026 holdout for SYS and the NEW arms
  (`docs/studies/lower_level_evidence/system/README.md`). The 2026 season was read there (NEW_SYS_BOTH vs SYS_BOTH, men,
  holdout +0.031 [−0.035, +0.097]).
* **Environment:** `./python.sh` (tennis env) for builds; `./python_tabpfn_local.sh` for fits; 16 threads; one GPU
  (idle at 17:10 UTC); 240 GB free on C:.
* **The idea:** a structural change already tested (the layer: "repair" in the owner's 9 Oct terms) and more data of a
  kind already used (Challenger qualifying, already in the history to 1 June 2026).

## 3. Plan

1. **Code** (no build yet): the ceiling rule in `level_layer.py`; the C1 and C2 hooks put into the 11 builders with the
   same calls (a new comment tag); the study's patch tools made integration-aware without touching the study's evidence;
   a strength-and-config module for template builds; `run_chain.py` runs the IOS part before `leakproof_frame` when
   the layer needs it; prediction runs set the same layer; `relationship.py --freeze` writes into `--out`; tests.
2. **Official config:** `data/studies/current_best_model/level_layer/official.json`, SYS's settings, the frozen tables'
   hashes, `ios_points_short` off, the strength resolved per build.
3. **Builds on today's tables (= the frozen reference's):** B_off (layer unset) and B_on (official config), side by
   side. Checks: identity (B_off against the reference frame with the decided indoor fill and Pinnacle-first odds),
   fidelity (B_on's chain output against SYS's frame: every input bit for bit except `indoor`, which carries the
   decided fill, and `ios_points_short`, switched off; IOS columns within 1e-12), invariance, G2/G3/G5, the probes, the
   Stage B pin, the strength.
4. **Harm check (layer):** fits seeds 0–3, 2019–2024, both arms; men, both stages, 2020–2024, paired by
   `system_pairs.py`; adopt unless worse by more than 0.10 mLL with the whole interval below 0.
5. **The template instance:** B_on with fits seeds 0–15 and stage 2.
6. **The 2026 data:** candidate Stage 0 = frozen + role F's men's 2026 CH and CHQ additions; built with the layer
   (lane 0 first); gate: every input equal to B_on's on matches the additions cannot reach; harm check on men's 2026
   matches, both stages, seeds 0–3, against B_on; adopt unless harm.
7. **Replay:** `replay.py` with the layer on, against B_on's frame.
8. **Records:** decision record(s), the amendment, CLAUDE.md, this log and a short README.

## 4. Chronology

Local time PDT (UTC−7). "Results" means any outcome-based score.

| When | Step (command or action) | Why | Results seen by then | Output |
|---|---|---|---|---|
| 10:00–10:10 | Read CLAUDE.md, the study's README, C_layer.md, C_layer_ios.md, SYS.json, the layer modules, the patch specs and diffs, run_chain.py, system_sandbox.py, system_arms.py, the decisions | Brief §1–2 | The study's own readings (its README) only | — |
| 10:05 | `git status`, `git diff src/eda/tabpfn_thinking/build_frame.py` (read-only) | Brief §2 | none | the indoor fill change found |
| 10:06 | Repo builders + C1/C2 patches vs `validated_src/` | Can the hooks go in as tested? | none | 11 of 11 equal |
| 10:07 | `system_sandbox.check_tables()` | Are today's tables the reference's? | none | 72 of 72 equal |
| 10:08–10:10 | Inventory of men's 2026 lower levels in Stage 0, C0_now, SofaScore's staged events, TML's files | The owner's second request | none | the facts put to the owner (§1) |
| 10:10 | AskUserQuestion (two questions) | Brief §2; scope of the second request | none | answers in §1 |
| 10:15 | `level_layer.py`: `params_season_ceiling` ("last_fitted", per tour; recorded when it binds); `level_layer_ios.fingerprint` adds the key only when set, so the study's fingerprints are kept | Brief §3.3 (ceiling) | none | — |
| 10:20 | New tags: C1 `# level layer (LLE_LAYER)`, C2 `# level layer, joint solves (LLE_LAYER)`; `system_sandbox` and `level_layer_ios` patch tools made integration-aware (`integrated`, `unpatched_text`, `normalize`; no diff written when nothing is patched, so the study's diff evidence stays); `system_arms.restore_validated_code` compares integrated builders with the snapshot after `normalize` | The repository's builders will carry the hooks; the "(sandbox only)" tag would be false there | none | — |
| 10:25 | `integrate_hooks.py` (dry run, then `--write`): the 11 builders written | Brief §3.1 | none | 11 of 11: equal to the normalized validated snapshot, un-patch back to the decided builder, compile; `data/studies/level_layer_adoption/integration/hooks_written.json` |
| 10:30 | `src/eda/current_best_model/layer_config.py` (strength, check, option-(c) re-centring, resolve, guard); `official.json` written by `write_official.py` (sha256 `be66df29…`) | Brief §3.2–3.3 | none | — |
| 10:35 | `layer_config.py --check` on today's Stage 0 | Brief §4 "Strength" | none | **equal bit for bit on 873,437 of 873,437 matches**, no scale shift |
| 10:40 | `run_chain.py`: `--prepare-layer`, `--lane N --layer` (guard: resolved for this sandbox and this Stage 0), IOS part inserted before `leakproof_frame`, `--collect` copies the layer's records. `prediction_run/run.py`: the layer resolved after `stage0_checks`, every later step with LLE_LAYER, `--no-layer`. `replay.py --compare --template` | Brief §3.4–3.5 | none | — |
| 10:50 | Builds launched: B_off `tnr_lyr_off` → `data/studies/level_layer_adoption/template_off/` (LLE_LAYER unset); B_on `tnr_lyr_on` → `data/studies/current_best_model/level_layer_2026-10-10/` (official config); `build_template.sh`, 6 surface workers and 3 timed-solve workers each | Plan step 3 | none | running |
| *Correction (10:38)* | The times in the rows from 10:15 above were written from memory and run late. From the files: the builds started at 10:20 PDT (17:20 UTC); both reached lanes 1 and 2 at 17:26 UTC. B_on's `--prepare-layer` (in its sandbox) again found the strength equal bit for bit (`chain_layer.json`) | Rule 4 | none | — |
| 10:27–10:37 | `candidate_stage0.py` generalised (`derive(..., keep=)`, `--keep-tours/levels/years`, `--status-log`); C0_men26 derived from role F's C0_now (men, CH and CHQ, 2026), `--checks`, `--ready` | The owner's 2026 data | none | 875,172 matches (1,735 new: CHQ 1,723, CH 12; 19 with box scores; 1 completion kept, 1,643 undone); checks pass; history: lower-level new past 1,735, revised 1 |
| 10:40 | `expected_unevenness_men26.txt` written and hashed (594b8dcc…) | Expectations before any build on it | none | — |
| 10:41 | B_new launched: `tnr_lyr_new` → `data/studies/level_layer_adoption/candidate_men26/` (C0_men26, lane 0, then the layer resolved on it) | Plan step 6 | none | running |
| 10:42–10:48 | `pytest test/lower_level_evidence` on the integrated code | Brief §4 "Tests" | none | 262 pass, 6 xfail, **1 fail**: `test_patch_applies_once…` (its fake sandbox copied the repository's builders, now hooked) |
| 10:48–10:55 | Tests adapted, not weakened: the C2 patch test builds its sandbox from the decided builders (`unpatched_text`); the C1 Elo-pass tests compare the hooked passes with the decided originals recovered by `unpatched_text` (they had become hooked-vs-hooked); a test that the integrated builders equal the validated snapshot once the tags are mapped. New `test/current_best_model/test_level_layer_template.py` (hooks off, the ceiling, the strength, option (c), the build config and its guard, the lane plans) | Brief §4 "Tests" | none | 86 of 86 pass, among them option (c) reproduced bit for bit against the study's `NEW_C0_now_elo_optC.parquet` (after matching its float32 arithmetic: my first version computed the shift in float64) |
| 10:56 | `relationship.py`: `--freeze` writes `<out>/method_freeze.json`, refuses an existing one (so never the study's), hashes the `--strength` actually read; `--mechanical` reads its own `--out`'s record. Test added | Brief §6 | none | passes; the study's `method_freeze.json` unchanged |
| 10:58 | `src/eda/level_layer_adoption/verify.py` written (identity, fidelity, gates, candidate) | Brief §4 | none | — |
| 11:00–13:50 | `src/eda/current_best_model/additions.py` (accepted packages: package, merge, timeline pin, check against a candidate), `run_chain.py --additions`, lane 0 without its timeline when packages were merged, the prediction run's `additions` and `additions_window` steps, `history.py`'s "accepted" class, `build_template.sh accepted`; tests `test/current_best_model/test_additions.py` | So that the 2026 data, if adopted, reaches every template build and prediction run without touching the shared live tables | none | merge of a scratch package into the frozen Stage 0 equals C0_men26 exactly (matches, players, timeline by match); 5 tests pass after one fix (a string-key concatenation that failed on pandas' string dtype) |
| 13:22–13:41 | Builds finished: B_off (lanes done 20:21 UTC), B_on (20:32), B_new (20:41); all exit 0 | — | none | B_new's strength: plain Elo; 14,476 men's 2026 reference matches move after 5 Jan 2026; 2026 main-tour scale shift 0.06 Elo, under the 1-point threshold, so no re-centring |
| 14:07 | `post_build.sh` on the three folders (chain frame kept as `model_frame_chain.parquet`; `odds_input.py --apply`; `template_inputs.py --apply`) | Plan step 3 | none | 57 inputs each |
| 14:08 | Fits launched (GPU, seeds 0–3): B_off 2019–2024, B_on 2019–2026, B_new 2019–2026 | Harm checks | none | running |
| 14:09 | `verify.py --identity` | Brief §4 | none | **pass**: B_off's chain frame equals the reference's on 57 of 58 inputs on all 67,226 matches; `indoor` equal wherever the reference had a value, filled on 32,634 (127 men's US Open 2026, 32,507 women's); B_off's template frame equals the current template's inputs (`indoor_fill/arm/`) on 58 of 58 columns, prices and the 57-input list |
| 14:10 | `verify.py --fidelity` | Brief §4 | none | **pass, bit for bit**: B_on's chain frame equals SYS's on 56 of 56 inputs compared (no tolerance used, IOS columns included); `indoor` the decided fill; `ios_points_short` equals the reference's exactly (family off) |
| 14:12 | `verify.py --gates` | Brief §4 | none | **pass**: G2 149 of 149 checks bit-exact (women 32,507 matches every input; untouched inputs every match; `ios_points_short` every match; `points_52w` on 4,139 men's matches out of reach); G3 16 of 17 + `form_first_in` by the ENV rule (SYS's verdict); G5 0 protected matches moved, controls caught; Stage 1, offset, Stage 3 constants the reference's; Stage B's men's constants re-tuned differently under the layer and pinned to the reference's (as in SYS) |
| 14:13 | `verify.py --candidate` | Plan step 6 gate | none | **fails my own tolerance**: women exact; men's inputs before the first addition (counts from 6 Jan 2026) exact except 9 IOS columns, differing by up to 7.9e-9 (holds), 6.7e-12 (aces), 2e-13 (`ios_points_short`) |
| 14:15–14:25 | `solver_tolerance.py`, first version: men's pooled hold solve on both caches to 31 Dec 2025, PCG at 1e-8 and 1e-13 | Is it the solver's tolerance or information? | none | the two caches' rows before the first addition are identical; the pooled solve agrees to 7.4e-13 (decided) and 5.9e-12 (tight); each build's decided solve is 6–8e-7 from its tight one, identically in both. So the pooled solve is not where the 7.9e-9 comes from: the model's hold inputs come from the surface-model solve. The first run is kept (`solver_tolerance_first_run_current_only.json`) |
| 14:26 | `solver_tolerance.py` extended to the decided surface variant; re-run. `match_timing/probe.py` launched in B_on's sandbox with LLE_LAYER | — | none | running |
| 14:27 | Found in the Roland Garros decision: its adoption is applied to the live tables "after the level-layer work running in another session reports done". So the replay must finish before I report | Coordination | none | — |
| 14:28 | Found: Tennis My Life's download of 10 Oct 14:30 UTC revised past rows and was restaged into the dump; a prediction run rebuilds Stage 0 from the dump, so a replay today would differ from the frozen-table template for data reasons | Replay design | none | — |
| 14:35–14:45 | `freeze_dump.py`: the dump of Tennis My Life as at 8 Oct 18:53 UTC, from the receipts and the kept CSVs (28 of 104 staged files re-staged with their original provenance), into `C:/Users/zerom/tnr_dump_freeze/`; replay sandbox `tnr_lyr_rp` set up (`run.py --setup`) and its `data/dump` junction replaced by a folder of junctions (Tennis My Life → the freeze view) | So the replay tests the code path only | none | **Stage 0 built in the replay sandbox without live rows equals the frozen Stage 0 byte for byte** (both tables' sha256) |
| 14:24 | `match_timing/probe.py` with the layer on (B_on's sandbox) | Brief §4 "leaks" | none | **pass**: 0 earlier matches moved at the four cuts (13,758–31,163 checked; largest difference 6.0e-15); its week-clock control moved (as designed). The probe runs `rebuild.ios_features`, which carries the hooks |
| 14:26–14:28 | `replay.py --prepare` run inside the replay sandbox (reads its frozen Stage 0 and the freeze-time dump) | Brief §4 "replay" | none | 23 matches of 15 Jul 2026 (Bastad 4, Gstaad 3, Umag 8, Athens 4, Iasi 4); 10 with the placeholder reversing the result: the 9 Oct replay's set. Its build waits for the 2026 data's decision (the accepted package changes the template) |
| 14:28–14:33 | Test suites: `lower_level_evidence`, `current_best_model`, `prediction_run` | Brief §4 "tests" | none | 365 pass, 6 xfail (the study's own). Other folders of the edited builders: all pass but `predictability_diagnostic` (3 fail) and `ufc_ideas` (1 fail, 2 errors): they compare the repository's built Stage 1/3/4 tables (built 30 Sep – 1 Oct) with the Stage 0 of 8 Oct; stale outputs, not code (the layer is off in the repository) |
| 14:30 | `solver_tolerance.py` (both solve kinds) read | The candidate gate's IOS differences | none | **convergence tolerance, not information**: surface solve, men's holds, rows before 2026: ON against NEW 4.2e-8 at the decided PCG tolerance, 8.2e-12 at 1e-13; each build's decided solve 5.1e-7 from its tight one. Pooled solve: 7.4e-13 and 5.9e-12. So the gate's pre-addition IOS differences (≤ 7.9e-9) are solver noise; every other input before the additions is exact, women exact |
| **14:31** | **`harm.py --layer`: the first outcome read of this work** | Brief §4 harm check | — | **ON vs OFF, men, both stages, 2020–2024: −0.014 [−0.162, +0.134] mLL, unresolved, P(better) 0.42** (11,672 matches, 55 blocks); no harm under the rule, so adopt. Every other reading unresolved (both tours +0.022; women +0.062; men's strata −0.130 to +0.180; seasons −0.167 to +0.172) |
| 14:36 | `compare.py --candidate` on B_on (the confirming run against the frozen reference) | The study's README §1, item 3 | the layer reading above | both tours, both stages +0.029 [−0.313, +0.372], unresolved (carries the layer, Pinnacle-first odds and the indoor fill together). Input flags identical to SYS's own `compare.py` flags (points_52w 13 men's seasons; 3 forms; 6 products), plus women's `indoor` (the fill) |
| 14:37–14:40 | Records drafted: the layer's decision (with the verification table), the amendment of the current-best-model decision, the CLAUDE.md bullet, the decisions index row; the 2026 data's decision opened | Brief §5 | the layer reading | — |
| 14:40 | `verify.py --candidate` re-run with the joint solves judged at SOLVER_TOL = 1e-7 (**a tolerance set after the strict check failed**, on `solver_tolerance.json`'s evidence; the strict verdict is kept in the file and in `candidate_first_run_strict.json`) | Plan step 6 gate | no candidate outcome yet | pass: on 65,064 matches the additions cannot reach, every non-joint-solve input bit-exact and the joint solves within 1e-7; women exact |
| 14:41 | `additions.py --register`; a lane-0 test | Adoption is an explicit act | none | 20 tests pass |
| 14:42–14:52 | Records drafted while the candidate's fits ran (the 2026 data's decision opened; the layer instance's README; `LARGE_FILES.md`) | — | the layer reading | — |
| **14:53** | **`harm.py --candidate`: the second outcome read** | Plan step 6 | the layer reading | **NEW vs ON, men, both stages, season 2026: +0.058 [−0.048, +0.164] mLL, unresolved, P(better) 0.89** (2,190 matches, 11 blocks); women −0.0004 [−0.006, +0.005]. No harm, so adopted under the rule the owner chose |
| 14:54 | Package `men_2026_ch_chq` written into `data/studies/current_best_model/accepted_additions/` and registered; `--check-against C0_men26` | The adoption | both readings | the merge equals C0_men26 exactly; `history.py` on C0_men26: "accepted lower-level additions 1,736 (allowed) … the template may be built"; on the live tables unchanged |
| 14:55 | The instance `data/studies/current_best_model/template_2026-10-10/` = B_new's folder copied (frames, records, seeds 0–3 fits); seeds 4–15 for 2019–2026 launched (GPU); the replay build launched (`run.py --build`, sandbox `tnr_lyr_rp`, the layer on, the package merged) | Brief §3.4, §3.5 | both readings | running |
| 15:08–15:11 | Replay: Stage 0 (23 live rows, 75 later rows dropped), `additions` (1,735 added, 1 completion), checks, `lle_layer` (strength "plain"; differences only from the men's 2026 additions, from 5 Jan, and the replay's dropped rounds, from 20 Jul) | — | — | as designed |
| 15:16 | Replay's rebuilt timeline against the template's (C0_men26's) | Would the IOS inputs differ for timeline reasons? | — | **1,294 matches finishing before 15 Jul 2026 have other windows** (a day or two tighter: e.g. 2017 Futures, 2019 WTA qualifying): links from sources restaged after the freeze. The package's 1,735 rows equal the package's in every column after the pin |
| 15:17–15:18 | Build stopped (process tree 53996, 48792); the sandbox's timeline set to the template's on all 875,120 rows (the rebuilt one kept: `timing_rebuilt_by_the_run.parquet`, `timeline_held.json`); build resumed `--from timing_features` | Judgment call 7 | — | the layer's guard passed on resuming; running |
| 15:40 | Owner, verbatim: "Why is this process taking so long?" Answered: four 2.5–3 h builds, the GPU fits, the two replay detours; offered to report before the replay | — | — | — |
| 16:02 | Owner, verbatim: "Ohhh, I was under the impression we were just updating the model, but I realize I gave you many more instructions than that (I copy and pasted from another LLM giving you instructions) its all fine. Were you testing point ##7?" Answered: no; the variant (Elo results unweighted) is not built; the indoor question was asked and settled. Recommended not building the variant now (chosen from a report-only reading on seasons read many times; the comparison cannot resolve it; better at the P7 refit or on unseen seasons); the men's low-exposure stratum of the layer's harm check leans the same way, unresolved (−0.13 [−0.46, +0.20]) | Brief §7 | both readings | — |
| 16:04 | The instance's seeds 4–15 fits finished | Brief §3.4 | — | 128 fits (16 seeds × 2019–2026), no errors |
| 16:13 | Owner, verbatim: "What did you do the prompt session? list it bullet point. Why is it taking so much time just to build a model?" Answered (with the context summary): the steps of §3 as done; the cost is the inputs, not the fit (each build recomputes all 58 inputs from about 875,000 matches: lane 1 about 2–2.5 h, lane 2's surface solves about 1 h; four builds; 184 GPU fits of 30–55 s; the replay's two detours) | — | both readings | — |
| 16:13 | The conversation's context was summarised; this log re-read | Rule (after a summary) | — | — |
| 16:15 | The replay's prep step `timing_features` (`rebuild.py`, run after `lle_layer`) rebuilt the IOS part with the layer: its `ios_features_summary.json` carries the official config's fingerprint `4b2d4bc9…`, as B_on's does | Will `leakproof_frame`'s guard pass? | — | yes; the replay's own resolved config (`34e99972…`) differs from B_on's (`0dbc740d…`), as it must: another Stage 0 |
| 16:18–16:21 | The three test folders re-run on the final code (`checks/tests_final.txt`) | Code changed after the 14:28 run (the lane-0 test, `replay.py --frame`) | — | **366 pass, 6 xfail** (265 + 90 + 11) |
| 16:22 | `harm.py --holdback` added and run: the new instance (`template_2026-10-10`) against the holdback's control, the Pinnacle-first instance of 9 Oct; both tours, both stages, 2020–2024, seeds 0–3 paired. **Not in the brief:** CLAUDE.md asks for it "after each batch of adoptions" (errata E1). The rule fixed before the run: `adoption_read.py`'s holdback rule (keep unless harm, then bisect; plausible effect 0.10 mLL; blind when that is under the 95% half-width and the interval spans 0). The batch it sees on 2020–2024: the layer, the women's indoor fill and the 57-input list (the 2026 data is outside those seasons) | Framework § 10 | the layer and 2026-data readings | **+0.018 [−0.125, +0.161] mLL, unresolved, P(better) 0.60** (+ = the new instance better; 22,265 matches, 55 blocks): no harm; blind (half-width 0.143 against the plausible 0.10), so the control cannot see this batch. Men −0.010 [−0.186, +0.166]; women +0.048 [−0.151, +0.248]; seasons −0.139 to +0.209, all unresolved (`results/holdback.csv`, `.json`) |
| 16:27 | Three rows appended to `data/studies/adoption_framework/class_record.csv` (`level_layer_men`: repair, men, pooled; `men_2026_ch_chq`: expansion, 2026, not pooled (holdout season); `holdback_2026_10_10`: not pooled), then `class_record.py` re-run into `class_record.out` (it now also counts the RG row another session appended after the last run) | CLAUDE.md: "Pool readings by kind" | all three readings | repairs pooled over 5: +0.002 [−0.016, +0.021] |
| 16:27 | **A label made precise after the results:** the class record needs one kind for the 2026 data. In the framework's table it is an **expansion** (new sources, TennisLive and SofaScore, for a level already in the history), not an accretion (the reference's own feeds). At 10:10 I had called it "more data of a kind already used". Both kinds are adopted unless the harm check fails, so the label does not move the decision; the decision record now says so | Accuracy of the record | all three readings | — |
| 17:01 | The replay build finished (lanes 1–3 and the collect; every one of the resumed run's 25 steps exit 0). `build.json`: the layer on (its own resolved config `34e99972…`); the accepted package merged (1,736 rows: 1,735 added, 1 completed); indoor known for all 23 (men Stage 0's flag, women the WTA's calendar); the gate: 20 complete, 3 women's matches incomplete (players who entered through qualifying with no qualifying match in Stage 0: the gate's ordinary flag, untouched by the layer) | Brief §4 "Replay" | — | — |
| 17:02 | `replay.py --compare --template data/studies/current_best_model/template_2026-10-10 --frame model_frame_chain.parquet` | Brief §4 "Replay" | — | **pass: 23 of 23 matches equal the instance's frame on all 57 inputs, bit for bit (largest difference 0.0; tolerance 1e-9 not needed)**, the 10 whose placeholder reverses the real result included (`replay_compare.json`, `.csv`) |
| *Correction (17:03)* | The 15:08–15:11 row's "75 later rows dropped": the Stage 0 log reads "live rows: 23 added, 75 played rows dropped", i.e. the 23 targets' own played rows (replaced by the live rows) and the 52 later rows the morning had not seen (`replay.json` `left_out_later` 52; the history check: dropped 52, revised 23) | Rule 4 | — | — |
| 17:33 | Owner, verbatim: "Give me a summary HERE as if talking to a laymen businessman who has a little background in the pipeline, tennis and datascience but not much. Also explain why that took so long. How long do you expect it to take to refit a new model with more data?" Answered in chat. Time estimates given from this session's measured step times (a build alone about 2 h 05 min: the replay's resumed chain 1 h 44 min plus about 20 min of preparation; fits about 31–43 s each) | — | all readings | — |

## 5. Sources

None outside the repository: every table read is the project's own (the frozen reference, the level-evidence study's
evidence, role F's C0_now, the staged dumps and their receipts).

## 6. Judgment calls and deviations

1. **The hooks' comment tag.** Options: keep the study's `# lower_level_evidence C1 (sandbox only)` (the builders
   would then equal the validated snapshot byte for byte) or a truthful tag. Chose the truthful tag; equality with the
   snapshot is checked after mapping the tags (`system_sandbox.normalize`), in a test and in
   `system_arms.restore_validated_code`. Before any result.
2. **`families.ios_points_short` false** (the brief's default). The IOS part still runs, because the `ios` family's
   pooled solves feed lane 3's mapping check; the `spw` short solve then runs as decided. Fidelity therefore compares
   `ios_points_short` with the reference, not with SYS. Before any result.
3. **The strength: per build, with a resolved config.** The official config names the frozen strength (valid on the
   reference's matches only); each build writes its own strength and a resolved config, and the lanes refuse a config
   resolved on another Stage 0. Re-centring (option c) only past a scale shift of 1 Elo point in a tour-season's
   main-tour mean (my threshold; the study's case was 75–92 points). Before any result.
4. **The build's IOS part runs inside lane 1** (sequentially, before `leakproof_frame`), not in a thread beside it as
   `system_arms.build` did: simpler, about 5–10 minutes longer. No effect on values.
5. **The candidate's harm check reads 2026 only.** Its additions all fall in 2026, so 2020–2024 cannot see them.
   2026 was read once by the study's holdout; reading it again here is a harm check of a data addition, not a
   selection. Fixed before any build.
6. **The 2027 refit is documented, not implemented.** `relationship.py`'s mechanical step is hard-wired to the
   2025–2026 seasons; generalising it is a change to the study's estimator beyond the brief's freeze fix. The ceiling
   rule serves 2027 until the refit.
7. **The replay's data is held at the freeze's** (two deviations from a plain prediction run, both before any replay
   input was read): Tennis My Life's dump is the freeze's (`freeze_dump.py`; Stage 0 rebuilt on it equals the frozen
   Stage 0 byte for byte), and the historical timeline is the template's (the run rebuilt it from sources restaged after
   the freeze, which moved 1,294 earlier windows). Reason: the replay proves the code path (the layer and the package in
   a live build); data drift would blur that proof, and a live run on the day's data meets the same drift whether or
   not the layer is on. What is not re-tested: the live timeline rebuild itself, which the 9 Oct replay tested (its
   `--dating live` run). Alternative: replay on today's data and attribute the IOS differences; not done (a second
   two-hour build, and a weaker proof).
8. **The 2026 data's instance was copied, not rebuilt.** `template_2026-10-10/` is B_new's folder (built on C0_men26)
   with its seeds 0–3 fits; the merge route gives C0_men26's tables exactly (`--check-against`), so a fresh build by
   the decided route would give the same frame. Not rebuilt: about three hours.
9. **A holdback reading beyond the brief.** CLAUDE.md asks for the template against the holdback's control after each
   batch of adoptions; the brief does not. Run once the instance's fits existed (no new fit needed), with
   `adoption_read.py`'s holdback rule fixed before the run. It decides nothing here (blind) and is recorded as a harm
   check. The three readings were also appended to the class record, and its `.out` regenerated from the CSV.

## 7. Claims and their evidence

| Claim (README) | Evidence | Status |
|---|---|---|
| The builders carry the study's hooks, equal to the validated code comments aside | `integration/hooks_written.json`; `test_the_integrated_builders_equal_the_validated_snapshot_comments_aside` | observed |
| Identity with the layer off | `checks/identity.json` (`verify.py --identity`) | observed |
| Fidelity to SYS, bit for bit | `checks/fidelity.json` | observed |
| G2, G3, G5, constants, pin | `checks/gates.json`, `gates_G2.csv`, `gates_G3.csv` | observed |
| No leak with the layer on | `checks/probe_match_timing_ON.json` | observed |
| Strength equal to the frozen | `current_best_model/level_layer_2026-10-10/chain_layer.json`; `layer_config.py --check` | observed |
| Layer harm check −0.014 [−0.162, +0.134] | `results/layer.json`, `layer.csv` (`harm.py --layer`) | observed |
| The candidate's pre-addition differences are solver noise | `checks/solver_tolerance.json` (two kinds, two tolerances); `checks/candidate.json` (strict verdict kept: `candidate_first_run_strict.json`) | observed; the 1e-7 tolerance was set after the strict check failed |
| 2026 data harm check +0.058 [−0.048, +0.164] | `results/candidate.json`, `candidate.csv` | observed |
| The merge route equals the candidate | `additions.py --check-against` output (14:54) | observed |
| Tests: 366 pass, 6 xfail on the final code | `checks/tests_final.txt` | observed |
| Holdback +0.018 [−0.125, +0.161], no harm, blind | `results/holdback.csv`, `.json` (`harm.py --holdback`); `class_record.csv` rows | observed; not in the brief (CLAUDE.md) |
| The replay: 23 of 23 matches equal on all 57 inputs, bit for bit | `data/studies/prediction_run/replay_2026-10-10_layer/replay_compare.json`, `.csv`, `build.json` | observed (data held at the freeze: judgment call 7) |

## 8. Weak points

* **Power.** The layer's harm check resolves about ±0.15 mLL; the 2026 data's about ±0.11 on 2,190 matches. Both can
  see only large harms; both changes rest on their kind (a repair; more data of a kind already used), not on these
  readings. No edge credit is taken.
* **Repeated looks at 2026.** The 2026 season was read by the study's holdout and again here (a harm check). Nothing was
  selected on it.
* **The candidate gate's tolerance** (1e-7 for the joint solves) was fixed after the strict gate failed; it rests on the
  solver experiment, which isolates the solver's convergence on men's holds (the worst column). Other statistics' solves
  were not re-solved at the tight tolerance; their differences were smaller (≤ 6.7e-12).
* **The replay holds its data at the freeze** (Tennis My Life, the timeline), so it tests the code path, not the live
  timeline's rebuild on today's sources (judgment call 7).
* **The study's own tooling for later arms** (`system_arms.build_gate` quotes the frozen `level_layer.py` hash, which
  the ceiling rule changed) refuses the old gated arms: P7 needs its §10 changes in any case.
* **Where a flaw would hide.** In a builder path no check exercised with the layer on: `surface_ios/probe.py` (hooked,
  not run here; the study ran it) and the prediction run's `--dating live` path with the package (not replayed).
* **The holdback is blind** (half-width 0.14 against a plausible 0.10): it can only rule out a large harm of the batch.
* **What a re-design would do.**
  * Replay on the day's data (no freeze) with `--dating live`, attributing each IOS difference to its source: the live
    timeline's rebuild with the layer and the package, end to end.
  * Rebuild the instance by the decided route (`build_template.sh <sandbox> <out> 1 accepted`) instead of copying
    B_new; today the route is proven equal at the table level only (`additions.py --check-against`).
  * Run both builds' joint solves at a tight tolerance (1e-13) for the candidate gate, so it is bit-exact instead of
    judged at a tolerance chosen after the strict gate failed.
  * Aim the 2026 data's harm check at the men it reaches (players with a June–October 2026 Challenger-qualifying
    match), declared as the primary before the run.

## 9. Reviewer checklist

* [ ] `./python.sh src/eda/level_layer_adoption/verify.py --identity` (and `--fidelity`, `--gates`, `--candidate`):
  each `"pass": true`.
* [ ] `./python.sh src/eda/current_best_model/layer_config.py --check`: equal bit for bit.
* [ ] `./python.sh src/eda/level_layer_adoption/harm.py --layer` / `--candidate` / `--holdback`: the three readings
  above.
* [ ] `./python.sh src/eda/current_best_model/additions.py --check-against data/studies/level_layer_adoption/stage0/C0_men26`.
* [ ] `./python.sh -m pytest test/lower_level_evidence test/current_best_model test/prediction_run -q`.
* [ ] Confirm no 2025–2026 parameter value was printed or used for a choice (only the 2026 reading of the candidate's
  harm check, after its rule was fixed).
* [ ] Read `git diff` of the 11 builders: only the hook lines.

## 10. Reproduction

```
./python.sh data/studies/current_best_model/level_layer/write_official.py
bash data/studies/level_layer_adoption/build_template.sh C:/Users/zerom/tnr_lyr_off data/studies/level_layer_adoption/template_off 0
bash data/studies/level_layer_adoption/build_template.sh C:/Users/zerom/tnr_lyr_on data/studies/current_best_model/level_layer_2026-10-10 1
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_men26 --derive-from C0_now --keep-tours atp \
    --keep-levels CH,CHQ --keep-years 2026 --out data/studies/level_layer_adoption/stage0/C0_men26 \
    --status-log data/studies/level_layer_adoption/stage0/status.log   # then --checks, --ready with the same --out
bash data/studies/level_layer_adoption/build_template.sh C:/Users/zerom/tnr_lyr_new data/studies/level_layer_adoption/candidate_men26 1 data/studies/level_layer_adoption/stage0/C0_men26
bash data/studies/level_layer_adoption/post_build.sh <each folder> [<the candidate sandbox's stage1_odds.parquet>]
./python_tabpfn_local.sh src/eda/model_rebuild/fits.py --out <folder> --seeds 0-3 --seasons 2019-2024|2019-2026   # GPU, ~30-50 s a fit
./python.sh src/eda/level_layer_adoption/verify.py --identity | --fidelity | --gates | --candidate
./python.sh src/eda/level_layer_adoption/solver_tolerance.py
(cd C:/Users/zerom/tnr_lyr_on && LLE_LAYER=<its build_config.json> python src/eda/match_timing/probe.py)
./python.sh src/eda/level_layer_adoption/harm.py --layer ; ./python.sh src/eda/level_layer_adoption/harm.py --candidate
./python.sh src/eda/level_layer_adoption/harm.py --holdback          # after the instance's fits
./python.sh src/eda/adoption_framework/class_record.py > data/studies/adoption_framework/class_record.out
./python.sh src/eda/current_best_model/additions.py --package data/studies/level_layer_adoption/stage0/C0_men26 \
    --name men_2026_ch_chq --decision docs/decisions/2026-10-10-men-2026-challenger-data.md
./python.sh src/eda/current_best_model/additions.py --register men_2026_ch_chq
# the replay
./python.sh src/eda/level_layer_adoption/freeze_dump.py
PREDICTION_RUN_SANDBOX=C:/Users/zerom/tnr_lyr_rp ./python.sh src/eda/prediction_run/run.py --setup
#   then data/dump in the sandbox replaced by junctions, Tennis My Life -> C:/Users/zerom/tnr_dump_freeze (chronology 14:35)
(cd C:/Users/zerom/tnr_lyr_rp && python src/eda/prediction_run/replay.py --prepare --out <repo>/data/studies/prediction_run/replay_2026-10-10_layer --week 2026-07-13 --round R16 --winner A --dating training)
PREDICTION_RUN_SANDBOX=C:/Users/zerom/tnr_lyr_rp ./python.sh src/eda/prediction_run/run.py --build data/studies/prediction_run/replay_2026-10-10_layer
#   stopped after the timeline step; the timeline held at the template's (chronology 15:17); resumed --from timing_features
./python.sh src/eda/prediction_run/replay.py --compare --out data/studies/prediction_run/replay_2026-10-10_layer --template data/studies/current_best_model/template_2026-10-10 --frame model_frame_chain.parquet
```
(The replay prices its matches with Stage 1's books'-average close, as on 9 Oct, so it is compared with the instance's
chain frame, whose odds input is the books' average; every other input is the same in both of the instance's frames.)
Sandboxes kept (about 16–21 GB each; the owner decides their cleanup): `C:/Users/zerom/tnr_lyr_off`, `tnr_lyr_on`,
`tnr_lyr_new`, `tnr_lyr_rp`; and `C:/Users/zerom/tnr_dump_freeze` (15 MB).

## 11. Added 14 Oct 2026: `tnr_lyr_off` and `tnr_lyr_on` deleted

Session `d2d2331e-b87f-42fd-baa1-b5c3ddebe82c`, as part of the cleanup inventory
([its process log § 7](../cleanup_inventory/process_log.md); `tnr_lyr_rp` went on 11 Oct, § 6b there).
* **The owner, 14 Oct 2026:** "Do this and be mindful of anything that reads these files to properly change it" (the
  steps: copy what the checks read, point the code at the copies, delete the two sandboxes).
* **What read them, and the change:**
  * `verify.py --gates`: 5 summary JSONs of ON (G5's leak probes) and 2 of OFF (the constants check). `SANDBOX` OFF
    and ON now point at `data/studies/level_layer_adoption/sandbox_extracts/<sandbox>/`.
  * `solver_tolerance.py`: ON's lane-2 cache and its build config. `BOXES["ON"]` points at the extract; the
    extract's `build_config.json` is relocated (the strength table's path into the extract; `record_dir` null, since
    the hooks would otherwise re-create the deleted folder on a re-run). The original is kept beside it, byte for byte.
  * `src/eda/unpriced_leads/rebuild_pool.py` (another study, 13 Oct): reads OFF's `stageB_adj.parquet` through its own
    frozen extract, whose record matched. Unchanged.
* **Proved** (`data/studies/cleanup_inventory/lyr_2026-10-14.json`):
  * Both readers gave the same output from the sandboxes and from the extracts: `--gates` byte for byte (and equal
    to this study's 10 Oct `checks/gates*` byte for byte); the ON solve every array and field but its wall-clock
    seconds.
  * Again after the code edit, and again once the sandboxes were gone; neither sandbox re-created.
  * `verify.py --gates` run as a command afterwards rewrote `checks/gates.json`, `gates_G2.csv`, `gates_G3.csv` with
    identical bytes.
* **No longer reproducible as written in § 10:** the two `build_template.sh` lines for OFF and ON would build new
  sandboxes on today's tables, not the 8 Oct reference's tables they were built on. The match-timing leak probe run
  inside ON needs such a build. Its 10 Oct output stays in `checks/probe_match_timing_ON.json`.
* `tnr_lyr_new` (NEW) is unchanged. `solver_tolerance.py` (`BOXES["NEW"]`) and `unpriced_leads` read it; `verify.py`
  names it in `SANDBOX` but reads nothing from it. Deleting it later needs the same treatment.
