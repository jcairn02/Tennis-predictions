# C1: the level layer in the lane-1 families, and the arms pipeline

9 October 2026 · Role C1 (layer engineer, lead engineer) of the lower-level-evidence system · Research evidence, not a
decision. The binding specification is [SPEC.md](SPEC.md); the joint solves are C2's ([C_layer_ios.md](C_layer_ios.md)).

## In short

* **What is built** (Observed). One layer, `src/eda/lower_level_evidence/level_layer.py`, applies SPEC §3's relationship
  inside every lane-1 family: `points_52w`, the 17 one-step forms, `ratings_iid` and the three Elo inputs. It is off unless
  `LLE_LAYER` names a config; then each hook returns its input object unchanged.
* **The patches** (Observed). 21 anchored edits in 5 builders, applied only in sandbox copies by `system_sandbox.py`, which
  refuses the repository and the first run's sandbox (diffs: `system/arms/patches/`).
* **The pipeline** (Observed). `system_arms.py` writes each arm's config, builds it through the decided chain with C2's IOS
  part (or, on a candidate Stage 0, lane 0) inserted where the chain needs it, and collects it into `system/arms/<ARM>/`;
  `system_gates.py` runs the gates; `system_new_arms.py` and `level_pins.py` build the NEW arms on role F's Stage 0s.
* **G1 identity** (Observed). IDENTITY_ALL, with C1's and C2's patches and the frozen modules (`level_layer.py`
  26e21291…, `level_layer_ios.py` 3fa5f69e…), reproduces the reference's 58 inputs exactly on all 67,226 matches, with
  the reference's tuned constants and 0 protected matches moved by any builder's probe (04:06 UTC, 10 Oct). IDENTITY
  (C1's patches alone, an earlier layer copy) had passed the same check.
* **READY for D** (Observed; times UTC, 10 Oct): SEP_ALL 01:59, REF_noITF 02:20, SYS 05:12, SYS_w0 05:19, SYS_w50 07:09,
  SYS_NOCLASS 07:24, SYS_w100 07:36, RES_ONLY 08:04, SYS_ITFASIS 10:03, NEW_ASIS 12:50, NEW_ASIS_PRE 13:03. G4 (the
  dose) passes on all 41 box-score inputs.
* **Ruled by the lead** (addition 7): SYS_BOTH and SYS_BOTH_ITFASIS READY with one weak women's G3 cell (`formdef_df`)
  recorded as an exception; NEW_SYS_BOTH rebuilt with option (c), because the plain Elo on C0_now moves the rating scale
  (+75 to +92 for women in every season), which B's parameters do not expect; READY at 15:34 UTC.
* **At checkpoint 1** (the lead): fitted w, w_joint and w_results capped at 1 in the layer; RES_ONLY added; every arm's
  config frozen in `system/arms/configs/` (MANIFEST.json 5bb50f1a…); gated arms built only under addition 3.
* **Two problems were caught by the gates and fixed in the open** (Observed). G2's "before the first reached row" set used
  event dates, which is not conservative for late rounds (REF_noITF); it now uses the match clock too. SYS_w100's first
  build carried a change another session made to the repository's frame builder (the women's indoor flag); every build
  now restores the chain's code to the copy IDENTITY_ALL validated (`system/arms/validated_src/`).

## 1. Keys and sources

* *Observed* = read in code (`path:line`, repository lines before the patch) or computed here (file cited). *Inferred* =
  reasoning. *Suggestion* = a proposal.
* Levels as `src/eda/lower_level_evidence/common.py`: MAIN, TQ, GSQ, CH, CHQ, ITF, ITFQ, TEAM. "Lower" = TQ, GSQ, CH,
  CHQ, ITF, ITFQ. TEAM rows are treated like MAIN (T = 0, w = 1).
* Data: the frozen reference's tables. Before each sandbox, `system_sandbox.check_tables()` re-hashed the 72 table
  files against `frozen/files.csv.gz`: 72 of 72 equal (Observed, 9 Oct 20:20 UTC). The history gate found 0 new, 0
  dropped, 0 revised matches (`system/arms/sandbox_logs/setup_tnr_sys1.log`).
* No 2025–2026 outcome is read: G1 reads the result column through 2024 only (a filtered read), and no gate reads
  results.

## 2. The hook map (Observed)

| Input family | Inputs | Builder lines patched (repository lines) | What the hook does |
|---|---|---|---|
| Raw rates | `points_52w` | `predictability_diagnostic/stage4_features.py:570-572` (`history_sums`) | `points_counts`: spw and rpw counts of each lower-level row translated, x ← x + d·(expit(logit r − T) − r), r = (x + ½)/(d + 1); then x, d ← w·x, w·d |
| One-step forms | `adjperf_tpw_2w`, `form_*` (12), `formdef_*` (4) | `ufc_ideas/stageB_adjperf.py:396-398` (after the per-match z), `:404` (step 3), `:525` (the pin) | `forms_z`: the 17 pairs' z recomputed with every opponent's norm re-referenced (each norm row translated and weighted) and the match's own value shifted by δ; `forms_step3`: each row's weight × w, a w = 0 row does not make the form exist; `pin`: Stage B's tuned constants replaced by the reference build's |
| Online point ratings | `ratings_iid` | `predictability_diagnostic/stage3_ratings.py:336` (the final pass) | `ratings_arrays`: each lower-level match's serve points and points won × w (a tempered likelihood), the pass's intercept + δ in the solve's units; the stored `mu_logit` untouched |
| Results ratings | `elo_overall`, `elo_surf_offset` | `stage1_baselines.py:169-178` (the pass), `:248` (the final pass), `:390` (the probe); `surface_elo_pieces/pieces.py:130-147` (the pass), `:309`, `:324`, `:333` | `elo_weights`: a played lower-level match updates with K × w_results and counts w_results; the tuning reads the unweighted flags, so K, the surface weight and kd are the reference's |
| Results ratings | `elo_games` | `stage4_features.py:674-686` (the weighted pass), `:747` (`elo_variants`) | as above, on top of the games weight |
| ITF exclusion | every box-score family | the hooks above (and C2's) | ITF and ITFQ box rows get w = 0 under `itf_box: "exclude"`; ITF results stay in Elo |

* Every patch is anchored on text found exactly once; `check_patch` requires each sandbox file to equal the repository's
  file plus exactly these edits (`system_sandbox.py`, `PATCH_SPECS`).
* With booleans the patched Elo passes perform the original operations (`upd[i] * k0` with `upd[i]` True is k0; `+=
  upd[i]` adds 1). With every w = 1.0 and T = 0 every hook's arithmetic is exact (x·1.0, y − 0.0). Tests below.

## 3. The relationship as the layer applies it

**Per observation** of statistic s, tour g, level L, season Y (lower levels, the arm's tours only):
* T = γ_{s,g} · (the opponent's reference pre-match Elo − strength_ref)/100 + δ_{s,g,L}; translated value = value − T.
  * Units: the logit of (x + ½)/(d + 1); the log for break points faced per service game (A's and the builders').
  * **The strength** (Observed): role A's `classes/strength_elo.parquet`, the reference build's Stage 1 ratings
    (retirements counted). My copy (`system/arms/strength/reference_elo.parquet`) is identical on all 873,437 matches
    (largest difference 0.0) and reproduces the frozen frame's `elo_overall` to 1.4e-6 log-odds.
  * **Gating by A's classes** (Observed, `classes.csv`): the input's class switches the γ term (OPP) or not (ENV);
    INTR, WORK, RES and CTX inputs are untouched; δ is used only at the levels A's `delta_levels` lists for the
    statistic the observation is (raw rates, forms) or for the input (the joint solves' single level term). Classes
    null (SYS_NOCLASS): γ and δ everywhere.
* **w**: an observation's weight in its aggregation is w times a main-tour observation's.
* **ITF and ITFQ box rows** are never translated: no training season has an ITF box score, so no parameter exists (P7).
  * Under `itf_box: "exclude"` they get w = 0.
  * Under `"as_is"` they are left as the reference has them (w = 1, T = 0): the SYS_ITFASIS arms of pre-registration
    addition 1, "as the reference treats them (equivalent)".
  * ITF results stay in Elo; they take the arm's w_results like every lower level.
* **Elo** (Observed, `stage1_baselines.py:169-178` patched): a lower-level result moves the ratings by K × w_results and
  the rated-match count by w_results, so w_results = 0 removes the match entirely (SEP_ALL's complete separation) and 1
  is the reference.
  * Role B's estimator uses the same rule (`relationship.py:46-47`: "counts advance by w_results").
  * The first run's role 03 counted every match (`translation.py:1268-1269`).
* **Parameters by season** (Suggestion, a call for CP1): each observation uses the parameters of its own season (Stage 0's
  `year`), fitted before that season. Every input of a season-Y match therefore reads observations translated with
  parameters fitted before their own seasons, all before Y. No season borrows another's parameters unless the config
  names a `params_season_floor`.

**The one-step forms in detail** (Inferred from `stageB_adjperf.py:144-209`; Observed in `level_layer.form_views`).
Stage B's z compares a player's value with the opponent o's norm, built from o's earlier rows. Each norm row is an
observation about o, so it is translated as one: by the strength of o's opponent at that row, with the γ and δ of the
statistic the row is.

| Part | adjperf channel (`form_s`, `adjperf_tpw_2w`) | adjdef channel (`formdef_s`) |
|---|---|---|
| a row of o's norm | what o allowed: A's `def_<s>` for ace, df, first_in, bp_faced_pg; otherwise minus o's mirror statistic (q's first-serve points won against o = 1 − o's return points won against the first serve) | what o produced: s |
| the match's own value | δ only (the re-referenced norm already accounts for who was across the net) | δ only, on o's value |
| the player's own form (step 3) | weight w of s | weight w of `def_<s>` |

* *Why not γ on the own value:* z = value − E'_o. If E'_o is what a main-tour reference player would get against o in
  main-tour conditions, then value − δ − E'_o is already main-tour-referenced. Shifting the value by γ too would count
  the opponent twice (Inferred).
* *Why A's `def_<s>` and the mirrors* (Observed, A_classes.md §3): the producer's dependence is not minus the
  opponent's. For men's aces, γ is −0.075 (aces against a stronger returner) and `def_ace` is +0.101 (aces conceded to a
  stronger server). The SPEC's "the strength gap of the player who produced it" is the same strength (o's opponent at
  that row); the table supplies the γ.

## 4. The config (SPEC §6.3 and the extensions)

`level_layer.validate` enforces SPEC §6.3. It refuses:
* `fitted` without params;
* translate without params or strength;
* params without their sha256;
* the newcomer prior until B's home-tier rule is in the config;
* any `elo_count` but `weighted`.

Every table read is hash-checked, by the config or by the sibling `.sha256` file.

The extensions have defaults:
* `strength`, `gamma_scale` (100);
* `forms_norm_weight` (true: w also weights the norms), `forms_own_delta` (true);
* `elo_count` (`weighted`);
* `solve_stat` (spw), `solve_w` (`w_joint`), `ratings_level_term` (`none`): the serve and return ratings;
* `params_season_floor` (null; SYS 2013), `missing_params` (`error`; SYS_BOTH `untouched`);
* `fitted_cap` and `fitted_cap_results` (1: the lead's ruling at CP1; null leaves B's values as fitted);
* `pins`, `record_dir`, `stage0_matches`.

* **Fitted w is capped at 1** (the lead, CP1 message of 10 Oct, after E's S1; Observed, `level_layer.weights`). B's value
  is first checked against B's own bound of 3, then any value above `fitted_cap` is set to it, whichever column is read:
  `w` for `points_52w` and the forms, `w_joint` for `ratings_iid` and C2's joint solves (C2 reads m through
  `level_layer.weights`, `level_layer_ios.py:319`). The literal ruling also caps B's `w_results` (the `results` rows of
  B's `w` column) through `fitted_cap_results`. Numeric weights (the dose arms' 0, 0.5, 1) are never capped.
  * Dev seasons 2013–2024 of SYS's parameters (Observed, `arms/configs/capped_cells_SYS.csv`): 199 men's box-score cells
    with w above 1, 208 with w_joint above 1, and 25 men's `results` cells (1.25 at TQ, GSQ and CHQ in most seasons).
  * Each arm's capped cells of the dev seasons are listed beside its config; the hooks record the rows they cap.
* **Records describe dev seasons only** (E's N11). The layer's records give w and T summaries for rows of seasons before
  2025; of the sealed seasons they give row counts, never a parameter's value or anything derived from one. The 2026
  parameters were fitted on 2025 results.
* **Only rows whose observation exists** are translated and weighted, and only they need parameters. For example,
  women's box scores have no service-game counts before 2015 (main tour) and 2016 (lower levels).
* **The final layer:** `level_layer.py` sha256 26e21291…, posted at 00:42 UTC on 10 Oct. It replaces 0b99b046… (23:19
  UTC), which had no cap.

## 5. The pipeline

**The sandbox** (`system_sandbox.py`):
* `--setup`: `MODEL_REBUILD_SANDBOX=C:/Users/zerom/tnr_sys<k> run_chain.py --setup --candidate`, after `check_tables()`.
* `--patch`:
  * copies the layer in and applies C1's patches;
  * applies C2's `apply_patch` once `system/arms/READY_ios_hooks.txt` exists;
  * pins `IOS_CONSTANTS_VERSION=2026-10-08_reference` (the version file must exist);
  * records everything with hashes in `<sandbox>/LLE_SYSTEM.json`.
* `--patch --stage0 F` (phase 3) copies role F's candidate Stage 0 and its own timeline over the sandbox's tables first.

**The build** (`system_arms.py --build ARM --sandbox D`):
* **Lane 0**, a candidate Stage 0 only: Stage 1's odds link and the full leak-proof rebuild. The timeline step runs only
  when F brings no `timing.parquet`. Lane 0 is "not yet exercised" (`run_chain.py:35-37`).
* **Lane 2** beside lane 1.
* **Lane 1**, split before `leakproof_frame` when an IOS family is on and C2's patch is in. C2's
  `run_ios_part(sandbox, out)` runs in the gap (`rebuild.py --part ios`, then `--part merge`).
* **Then** lane 3 and `--collect` into `system/arms/<ARM>/`, with `build.json`, the lane records and `chain_logs/`.
* **The environment of every step:** `MODEL_REBUILD_SANDBOX`, `LLE_LAYER` (the arm's `layer_config.json`) and
  `IOS_CONSTANTS_VERSION`.

**Which steps a family needs** (Observed, the chain's reads; run_chain.py:65-93):

| Family | Lane-1 steps that carry its change to the frame |
|---|---|
| `points_52w` | `stage4_features` → `ufc_stageD_rundown` (stageD_features) → `thinking_frame` → `leakproof_frame` → lane 3 `model_frame` |
| the 17 forms | `ufc_stageB_adjperf` → `ufc_stageB_split` (reads the z; no input), `ufc_stageB_rundown` (merges) → `ufc_stageD_profile` → `thinking_frame` → `leakproof_frame` → `model_frame` |
| `ratings_iid` | `stage3_ratings` → `stage4_features` (`rating_matchup`) and `ufc_stageB_ios` (C2) → Stage D → the frames |
| Elo | `stage1_baselines` → `stage4_features` (`elo_games`, `p_elo`), Stage B's tuning (pinned), Stages A and C (no input) → `elo_pieces` → `elo_frames` → `model_frame` |
| the joint solves (C2) | C2's IOS part (`rebuild.py --part ios`, `--part merge`), lane 2, lane 3 |

* **Stages A and C feed no input** (`run_chain.py:15-17`: Stage D's rundown needs their files on the same matches).
  Every arm takes their outputs from the reference-equivalent build on the frozen tables. That is the first run's
  sandbox, read only: its Stage 1, A and C and offset-Elo steps ran the decided builders unpatched.
* **Stage 1 and `elo_pieces`** are reused only when the arm leaves Elo alone (REF_noITF).
* **An arm that changes Elo only (RES_ONLY)** also takes Stage 3 and Stage B's adjperf and IOS steps from IDENTITY_ALL's
  sandbox, once IDENTITY_ALL has passed G1 (`system_arms.REUSABLE_IDENTITY`). Stage 3 reads no Elo. Stage B's adjperf
  and IOS read Elo only to tune (`stageB_adjperf.py:254-300`), and their constants are pinned or the registry's. The
  files each step writes were read off their modification times in the identity build. Stage 4, Stage B's split and
  rundown, Stage D, the frames and the offset Elo read Elo for more than tuning, so they run: lane 1 is 11 steps instead
  of 14.
* **Never on a candidate Stage 0.** Each reused file is copied with its hash (`build.json`, `reused`).
* **Everything else runs in full.** A family's change reaches the shared intermediates (Stage 4's pool frame, Stage D,
  the frames), so no smaller unit of the chain can be rebuilt alone.

**The gated arms and the frozen configs** (Observed, `system_arms.py`, after the lead's CP1 message):
* `--write-configs` writes every arm's config into `system/arms/configs/` once: the arms already built keep theirs byte
  for byte. It lists each file's sha256 in `MANIFEST.json`, and for each arm reading fitted weights it writes the dev
  seasons' capped cells.
* A gated arm (the SYS family, addition 1's ITFASIS arms, RES_ONLY) is built only under the lead's dated CP1 addition,
  named by `LLE_CP1_ADDITION` and checked against its `.sha256`. The addition must quote, in full, the current sha256 of
  `level_layer.py`, `system_sandbox.py`, `system_gates.py`, `system_arms.py` and `MANIFEST.json`
  (`system_arms.build_gate`). The arm's `layer_config.json` is then the frozen file, byte for byte.
* The configs no longer name the addition: the addition freezes them, so they cannot name it.
* **Lane timings** (first run, `candidates/FP/chain_lane1.json`): lane 1 98.5 min (Stage 1 21, Stage A 15, Stage B
  adjperf 15, Stage B IOS 9, Stage 4 9, `elo_pieces` 8), lane 2 19.7 min, lane 3 0.2 min.

## 6. B's parameters as the layer reads them

B delivered `relationship/params.parquet` (Observed, `READY_params.txt`, 23:15 UTC):
* sha256 4c559abd…;
* 3,808 rows, seasons 2013–2026, the 2025–2026 rows sealed;
* `params_noclass.parquet` (4018747d…) is SYS_NOCLASS's view.

The `stat` keys are exactly the layer's:

| Keys | Read by |
|---|---|
| `spw`, `rpw` | `points_52w`; `ratings_iid` (`w_joint`, one weight per observation) |
| `tpw`, `ace`, `df`, `first_in`, `first_won`, `second_won`, `hold`, `bp_saved`, `bp_faced_pg`, `brk`, `bp_conv`, `rpw_first`, `rpw_second` | the forms' own values and adjdef norms; the mirrors of the adjperf norms |
| `def_ace`, `def_df`, `def_first_in`, `def_bp_faced_pg` | the adjperf norms of the four statistics without a mirror; `formdef_*`'s step-3 weight |
| `results` | w_results (Elo), every lower level, ITF and ITFQ included |

* **Checked through the layer** (Observed, 23:20 UTC; inputs only, no score): every statistic and season of 2010–2024
  on 30,000 Stage 0 matches. Units agree: γ per 100 Elo, `gamma_scale` 100.
  * At Challengers the translation averages +0.16 (spw) and +0.24 (rpw) logit: weaker opponents, so rates come down.
  * ITF and ITFQ box rows get w = 0.
* **The lead's rulings**, written into the SYS configs (`system_arms.phase2_config`):
  * `params_season_floor: 2013` for the rows of 2010–2012 (9 Oct);
  * `missing_params: "untouched"` for SYS_BOTH's women's service-game cells of 2013–2015, which B cannot fit (9 Oct);
  * B's fitted w_results at every lower level, ITF and ITFQ included (9 Oct);
  * fitted w capped at 1 (CP1 message, 10 Oct; §4). It replaced the ruling of 9 Oct, "as fitted, up to B's cap of 3".
    B's w reaches 2.82 (men's `def_bp_faced_pg` at CH), which E traced to the pool prior (`E_red_team.md` S1).
* **Men's CHQ rows of 2016–2017 get w = 0** (B: the level is not fitted until season 2018, `fitted` false). Under the
  own-season convention every men's Challenger-qualifying box row of those two seasons drops out of the box-score
  families. The input check may flag the seasons this reaches (Inferred).
* A missing key is an error, never a fallback, unless the config says `missing_params: "untouched"`.

## 7. The gates

| Gate | What it checks | Code |
|---|---|---|
| G1 identity | IDENTITY's frame against the frozen frame: ids and order, identifiers, the result column through 2024 (filtered read), all 58 inputs exactly; the tuned constants the reference's | `system_gates.g1`, `constants_gate` |
| G2 invariance | exact on what the arm cannot reach: other tours (all 58), the untouched inputs (odds, context, age, sets, surface pairs), the inputs of the families the arm switches off (every match), every input before the tour's first reached row, `points_52w` without a reached box row in 364 days, the forms without a reached row of their own or in an opponent's norm | `system_gates.g2`, `reach_sets` |
| G3 direction | the changed box-score inputs against the reached share gap (two-week window for the forms, 365 days for `points_52w`), signs from the first run's offsets; required where the weighted shift is 0.05 or more; an ENV-class input's failed cell in a translating arm judged per season against B's δ (the lead's ruling, §12) | `system_gates.g3`, `env_rule` |
| G4 dose | phase 2, once SYS_w0, SYS_w50, SYS and SYS_w100 exist; not yet coded (§9) | — |
| G5 leaks | the builders' own probes in each arm's build with the hooks on; the real-date probe below | `system_gates.g5`, `system_g5.py` |
| G6 level | phase 2 (B's residual target); not yet coded (§9) | — |
| C2 end to end | an arm's 22 IOS inputs equal C2's own build of the same IOS fingerprint (`system/ios_layer/inputs/<ARM>.parquet`; the identity arms against C2's `IDENTITY_m1`), exactly | `system_gates.c2_end_to_end` |

* **G2's one tolerance** (fixed before any G2 ran with it, 10 Oct 00:35 UTC). The 21 surface-solver inputs are compared
  within 1e-12; every other input exactly. C2 showed that the decided surface solver moves by rounding alone when
  players with no row before a day leave its system: women's holds by 1.6e-15, decided against decided
  (`system/ios_layer/gates/decided_active_set_wta_hold.json`); REF_noITF's hooked solve by 4.0e-15 (men) and 1.8e-15
  (women) before the first ITF box score. G2 still reports each check's bit-exact result.
* **The families-off set** (added 10 Oct 00:45 UTC, before any G2 ran) makes RES_ONLY's check strict: every input but
  the three Elo ones must equal the reference's on every match. For REF_noITF it covers the Elo inputs.

**G5, the real-date probe of the layer's cross-player changes** (Observed, `system/arms/g5/real_date_probe.json`).
* **Design:** match_timing/probe.py's slice (2023–2024, history inside the slice) and its four cut days. Every match
  that surely started after the cut has its result reversed and the two players' counts exchanged.
* **Strength:** Stage 1's pass is re-run on the flipped history, so the translation reads the flipped world's pre-match
  Elo.
* **Rebuilt:** `points_52w` and the 17 forms, with the layer on.
* **Configs:** DROP (men, w = 0), REWEIGHT (both tours, w = 0.5, ITF out) and TRANSLATE (both tours, A's classes,
  synthetic parameters in SPEC 6.2's schema with γ from A's table, δ 0.1, w 0.7).

| Config | Protected pool matches moved (of 13,758 / 19,744 / 29,141 / 31,163 at the four cuts) | Later matches moved |
|---|---|---|
| DROP | 0 / 0 / 0 / 0 | 13,020 / 10,103 / 4,256 / 2,989 |
| REWEIGHT | 0 / 0 / 0 / 0 | 22,602 / 16,921 / 7,787 / 5,787 |
| TRANSLATE | 0 / 0 / 0 / 0 | 22,602 / 16,921 / 7,787 / 5,787 |
| Control: TRANSLATE with each player's end-of-slice rating (a leak by construction) | **28,958** at the last cut: caught | |

* **The intermediate identity checks** (Observed). The identity build's outputs were compared with the first run's
  sandbox, which ran the decided builders on the frozen tables:
  * Stage 1's `stage1_baselines.parquet`: every column, all 873,437 matches, 0 differences; the chosen K and surface
    weights the reference's; its probe 0 protected matches moved;
  * Stage 3's ratings: every column, 0 differences; the reference's constants; its probe 0 moved;
  * Stage 4's features: all 150 columns that FP's translation did not touch, 0 differences (FP translated the serve and
    return points in the first run).

**The Phase 1 arms' gates** (Observed; `system/arms/<ARM>/gates/`):

| Arm | G1 / G2 | G3 | Constants | Builder probes (G5) | C2 end to end | Matches changed | READY |
|---|---|---|---|---|---|---|---|
| IDENTITY | G1 pass: 58 of 58 inputs exact on 67,226 matches; identifiers and results to 2024 equal | — | reference's | 0 moved; controls caught | 22 of 22 exact | 0 | identity arm (none) |
| IDENTITY_ALL (both patches, the frozen modules) | G1 pass: the same, 58 of 58 exact | — | reference's, Stage B's own tuning included | 0 moved; controls caught | 22 of 22 exact | 0 | identity arm (none); 04:06 UTC |
| SEP_ALL | G2 pass: women's 32,507 matches, every input exact; the untouched inputs on all 67,226; `points_52w` on the 4,139 men's matches without a reached row in 364 days | 17 of 17 required cells as expected | reference's (Stage B's own men's tuning differed; the pin replaced it) | 0 moved; controls caught | 22 of 22 exact | 34,719 (every men's match, from 2013) | 01:59 UTC |
| REF_noITF | G2 pass (second run, below): 151 checks, 130 bit for bit, 21 within the rounding tolerance | none required (w = 1) | reference's | 0 moved; controls caught | 22 of 22 exact | men from 2025, women from 2 May 2022 (beyond rounding) | 02:20 UTC |

* **REF_noITF's G2 failed on its first run, on the gate's own definition** (Observed, then corrected). Seven women's
  matches (QF, SF and F of WTA event 2022-1038, event date 28 Apr 2022) moved by up to 0.008 in `ios_points_short` and
  0.0017 in the surface inputs. They were played after the first ITF box rows of 2 May 2022, which count on the match
  clock, so the layer reached them legitimately. The set "before the first reached row" had used event dates only,
  which is not conservative for late rounds. It now also requires es before the first reached row's lf + 1
  (`system_gates.reach_sets`, 10 Oct 02:25 UTC). The rerun passed; SEP_ALL's set was empty under both rules.
* **REF_noITF before its first ITF row** (Observed, `arms/REF_noITF/gates/season_profile_beyond_rounding.csv`): on every
  men's match of 2013–2024 the 37 non-surface inputs are bit for bit and the 21 surface-solver inputs differ by at most
  4e-15. Changes beyond rounding: men 2,584 matches of 2025 and all of 2026; women 1,473 of 2022's 2,339 matches, then
  every match.

**The arms built with earlier copies of the layer** (E's S5). Each sandbox keeps the copy its build ran, hashed in
`build.json` and in `<sandbox>/LLE_SYSTEM.json`:

| Arm | Sandbox | `level_layer.py` copy | C2's `level_layer_ios.py` copy |
|---|---|---|---|
| IDENTITY | `tnr_sys1` | 932789fd… (9 Oct 20:31 UTC) | none (C1's patches only) |
| SEP_ALL | `tnr_sys2` | e091a8e8… | 0886da75… |
| REF_noITF | `tnr_sys3` | b443a37f… | d49a2511… |
| IDENTITY_ALL | `tnr_sys4` | 26e21291… (final, with the cap) | 077c760a… (final) |

Why the differences cannot reach SEP_ALL's and REF_noITF's inputs (Inferred, from the diffs of each copy against the
final file; no rebuild was run to show it):
* **Translation is off in both arms,** and `translation()` returns zeros before any changed line when it is
  (`level_layer.py`, `translation`, identical in the three copies).
* **Their weights are numbers,** so nothing that reads B's parameters runs: the `column` argument, the cap,
  `missing_params` and the season floor act only on fitted weights.
* **`ratings_level_term`** (b443a37f… and earlier added the supplied δ): with translate off that δ was zeros, so the
  intercept is the same `mu + 0.0`.
* **The validity masks** (added after e091a8e8…, SEP_ALL's copy) give w = 1 instead of 0 to rows whose observation is
  missing. Each hook ignores those rows whatever their weight:
  * `points_counts` keeps x and d where `ok` is false (`np.where(okb, …, xf)`, the same in both copies);
  * the forms' moments and step 3 multiply by `valid`/`ok` before the weight;
  * Stage 3's pass reads a match's counts only where it updates (`stage3_ratings.py:166`, `if upd[i]`).
* **The records** changed (dev seasons only); they feed no input.
* G2, run on each arm's frame, checks the consequence: nothing the arm cannot reach moved.

## 8. Tests

`test/lower_level_evidence/test_level_layer.py`: 23 tests, all pass (Observed, 10 Oct 00:53 UTC; C2's 47 tests also pass
against the final layer). They check:
* off: every hook returns its input object; a family switched off does too;
* the config's refusals, and the hash checks of the parameters and the classes;
* w: SEP_ALL's and REF_noITF's rules, ITF as_is untouched, fitted w read from its own season, a missing key refused;
* the cap: fitted w, w_joint and w_results above 1 set to 1, numeric weights untouched, B's bound of 3 still refused,
  the records and `capped_cells` describing dev seasons only;
* G4 on synthetic dose arms: a change that grows with w passes, one that shrinks fails;
* T: the formula, its sign (weaker opponents, T > 0), the complement's sign, A's class and `delta_levels` gating, ENV
  δ-only, INTR untouched, the joint solve's input-level δ;
* the statistic views of the forms;
* exactness at the identity settings: `points_counts` and `ratings_arrays` bit for bit;
* the patched Elo passes: the same with booleans and with 1.0 (Stage 1, the three `pieces` modes, Stage 4's weighted
  pass); w = 0 equals "does not move" exactly; w = 0.5 moves by half and counts 0.5;
* the weighted step-1 moments equal Stage B's at w = 1 and drop w = 0 rows;
* every patch anchor is found once and the patched files compile;
* the build plan (lane 1 split around C2's IOS part; lane 0 for a candidate); a candidate without READY refused; the
  Stage B pin.

On a real slice (2024-06 to 2026, 180,290 box rows), the patched Stage B build at the identity config reproduced the
builder's 30 pairs' z and 90 features exactly. That was a scratch smoke test, run twice: with the layer copy of 20:31
and with the final one.

## 9. Open questions for the lead (Suggestion)

Each is a config switch or a line of the layer. The CP1 addition should fix them before SYS is built.
* **Settled** since: the 2013 floor, `missing_params` and w_results at ITF (the lead's rulings of 9 Oct, §6); the cap
  at 1 and RES_ONLY (the CP1 message of 10 Oct).
* **B agrees** (`B_relationship.md` "For the engineers"): the Elo count (1), the norm views (2) and the own-season
  convention (3).
* **Open at CP1:**
  * **Does the cap apply to B's w_results?** The literal ruling ("fitted w above 1 is set to 1") reaches the `results`
    rows of B's `w` column, which are 1.25 at men's TQ, GSQ and CHQ in most dev seasons (25 men's cells). The configs
    carry `fitted_cap_results: 1`; null would leave B's values. SYS and RES_ONLY take the same value either way, so SYS
    against RES_ONLY still isolates the results channel.
  * **G4 and G6 are diagnostics, not READY conditions** (my reading). G4 compares four arms, so it cannot hold one
    arm's READY without delaying D. It is coded (`system_gates.py --dose`). G6 (the same-player gap after translation)
    is not coded: B publishes no residual target, and E's S2 already measured it for one cell. If the lead wants it, it
    would be a separate diagnostic module, so the frozen `system_gates.py` would not change.
  * **Disk for Phase 2** (status line, 00:58 UTC): 11 gated arms in fresh sandboxes need about 230 GB of the 284 GB
    free. Proposal: build in the Phase 1 sandboxes once their arms' gates and READY are written.

1. **Elo's experience count** (`elo_count`). Implemented: the count moves by w_results, as role B's estimator does. The
   alternative, every played match counts in full (role 03's `translation.py:1268-1269`), would keep w_results = 0 from
   being a complete separation.
2. **The forms' norm views** (§3). Implemented:
   * the adjperf norms read A's `def_<s>` or the mirror statistic;
   * the adjdef norms read s;
   * the match's own value takes δ only;
   * w weights the norms as well as step 3 (`forms_norm_weight`).

   The SPEC's sentence ("shifted by the strength gap of the player who produced it") fixes the strength and leaves the γ
   open; A's table supplies it.
3. **The season of the parameters.** Each observation uses its own season's parameters. The alternative, re-translating
   all history with the target season's parameters, would rerun every online pass once per season.
4. **`ratings_iid`'s level term.** The δ "in the solve's own units" is not role B's residual after Elo's γ (A_classes.md
   §5, B_relationship.md "For the engineers"), and Stage 3 is an online pass, where C2's form (b) has no counterpart.
   * Implemented: weights only, one per observation (`w_joint`), no level term (`ratings_level_term: "none"`).
   * Role 01 measured Stage 3's residuals within ±0.3 points per 100 serve points at every level (`team/01_lineage.md`,
     measurement 3), so the omitted term is small (Inferred).
   * `"supplied"` would add B's spw δ to the pass's intercept.
5. **The newcomer prior is not kept** (Observed, `status.log`, B at 21:32 UTC): B's rule chose F4, the pool prior, on
   both tours. SYS therefore runs with `prior: "pool"`, and the builders' own shrinkage targets stay. The config still
   refuses `prior: "newcomer"`; wiring it would need B's tier mean in each builder's units (Stage 4's surface mean,
   Stage B's 0 in z units, the IOS ridge).
6. **ITF results in Elo under SYS.** The layer applies w_results to every lower level, ITF included (the lead's ruling of
   9 Oct). E's M3 found that this departs from SPEC §3 and that no arm separated it. The lead's answer at CP1 is
   RES_ONLY: the reference plus B's Elo weighting (translate false, weight 1, w_results fitted, ITF box scores as they
   are, Elo only; men, as SYS), built after SYS, SYS_w0 and SYS_w100.
7. **Phase 3** (role F's C0_now). The strength table covers only the frozen Stage 0's matches. A new match has no
   reference pre-match Elo, so NEW_SYS_BOTH needs a strength rebuilt on C0_now with the reference's Stage 1 constants.
   That is a decision about which Elo "the reference's" means there.

## 10. Commands (from the repository root, in the order run)

```
./python.sh src/eda/lower_level_evidence/system_arms.py --prepare                  # strength copy, Stage B pin, constants
./python.sh src/eda/lower_level_evidence/system_sandbox.py --setup --n 1           # also --n 2, --n 3 (tables re-hashed first)
./python.sh src/eda/lower_level_evidence/system_sandbox.py --patch --sandbox C:/Users/zerom/tnr_sys1
./python.sh src/eda/lower_level_evidence/system_arms.py --config IDENTITY | SEP_ALL | REF_noITF
./python.sh src/eda/lower_level_evidence/system_arms.py --build IDENTITY --sandbox C:/Users/zerom/tnr_sys1
./python.sh src/eda/lower_level_evidence/system_gates.py --arm IDENTITY --sandbox C:/Users/zerom/tnr_sys1
./python.sh src/eda/lower_level_evidence/system_g5.py --tree C:/Users/zerom/tnr_sys2      # the real-date probe
./python.sh src/eda/lower_level_evidence/system_arms.py --build SEP_ALL --sandbox C:/Users/zerom/tnr_sys2
./python.sh src/eda/lower_level_evidence/system_arms.py --build REF_noITF --sandbox C:/Users/zerom/tnr_sys3
./python.sh src/eda/lower_level_evidence/system_gates.py --arm <ARM> --sandbox <D>; ... --arm <ARM> --ready
./python.sh -m pytest test/lower_level_evidence/test_level_layer.py -q
```

At checkpoint 1 (10 Oct):

```
./python.sh src/eda/lower_level_evidence/system_sandbox.py --setup --n 4
./python.sh src/eda/lower_level_evidence/system_sandbox.py --patch --sandbox C:/Users/zerom/tnr_sys4    # final layer + C2's
./python.sh src/eda/lower_level_evidence/system_arms.py --build IDENTITY_ALL --sandbox C:/Users/zerom/tnr_sys4
./python.sh src/eda/lower_level_evidence/system_gates.py --arm IDENTITY_ALL --sandbox C:/Users/zerom/tnr_sys4
./python.sh src/eda/lower_level_evidence/system_arms.py --write-configs                # arms/configs/, once
./python.sh src/eda/lower_level_evidence/system_arms.py --freeze-hashes                # what the CP1 addition quotes
```

Phase 2 (after the lead's go): `LLE_CP1_ADDITION=<the lead's addition> ./python.sh src/eda/lower_level_evidence/
system_arms.py --build SYS --sandbox <D>`, in the lead's order: SYS, SYS_w0, SYS_w100, then RES_ONLY, SYS_w50,
SYS_NOCLASS, SYS_BOTH, SYS_ITFASIS, SYS_BOTH_ITFASIS; G4 with `system_gates.py --dose` once the four dose arms exist.

## 11. Files

| What | Where |
|---|---|
| The layer; the sandbox patcher; the arms; the gates; the real-date probe | `src/eda/lower_level_evidence/level_layer.py`, `system_sandbox.py`, `system_arms.py`, `system_gates.py`, `system_g5.py` |
| Tests | `test/lower_level_evidence/test_level_layer.py` |
| The patches' diffs | `system/arms/patches/` (`c1_all.diff` and one per builder) |
| The reference inputs (strength copy, Stage B pin, reference constants) | `system/arms/strength/`, `system/arms/constants/`, `system/arms/reference_inputs.json` |
| Each arm: config, frame, inputs, lane records, logs, layer calls, gates, READY | `system/arms/<ARM>/` |
| Every arm's frozen config, the dev seasons' capped cells, MANIFEST.json | `system/arms/configs/` (written at the freeze) |
| G4 across the dose arms | `system/arms/g4/` (phase 2) |
| The real-date probe | `system/arms/g5/real_date_probe.json` (and its synthetic parameters) |
| Sandbox setup and build logs, gate logs | `system/arms/sandbox_logs/` |
| Sandboxes (not deleted) | `C:/Users/zerom/tnr_sys1` … `tnr_sys4` (about 21 GB each once built; `run_chain.py --cleanup` with `MODEL_REBUILD_SANDBOX` set removes one, if the owner agrees) |

## 12. Phase 2: the SYS family, RES_ONLY and the NEW arms

**Under addition 3** (the lead, 10 Oct 01:49 UTC; sha256 f2063433…). It quotes `level_layer.py` 26e21291…,
`level_layer_ios.py` 3fa5f69e… (C2's pooled form-(b) fix), `system_sandbox.py` ebf4520a…, and the build code as it was
at 01:49 (`system_arms.py` 3e3b9b6b…, `system_gates.py` 0adbf1a5…).
* **The configs** were written by that frozen `system_arms.py` into `system/arms/configs/` at 02:00 UTC, before any edit
  (MANIFEST.json 5bb50f1a…). Each gated arm's `layer_config.json` is the frozen file, byte for byte.
* **Build code changed since, inputs not** (posted in `status.log` for a later addition, as addition 3 §1 allows):
  * `build_gate` checks that the addition quotes the two layers and the patches as on disk;
  * a gated build refuses a lane-2 runs folder that already exists, and records the folder;
  * a resumed build with an IOS family on rebuilds C2's IOS part first;
  * no gated arm is READY before IDENTITY_ALL passes G1 (addition 3 §5);
  * G2's set "before the first reached row" also uses the match clock (§7);
  * the NEW arms (below).

**The queue** (the lead's order of 02:08 UTC; at most 3 builds, the next arm starting when a slot frees, after the gates
of the arm before it in that sandbox):

| Slot | Sandbox: arms in order |
|---|---|
| A | `tnr_sys4` IDENTITY_ALL → `tnr_sys5` SYS_w100 (only on IDENTITY_ALL's G1 pass) → `tnr_sys1` RES_ONLY → SYS_BOTH_ITFASIS → NEW_ASIS_PRE (C0_pre) |
| B | `tnr_sys2` SYS → SYS_w50 → SYS_BOTH → `tnr_sys4` NEW_ASIS (C0_now) |
| C | `tnr_sys3` SYS_w0 → SYS_NOCLASS → SYS_ITFASIS → `tnr_sys5` NEW_SYS_BOTH (C0_now) |

* **C2's cautions** (C_layer_ios.md §6): every arm name is new in its sandbox, so no lane-2 runs folder is reused; every
  IOS arm rebuilds the IOS part fresh.
* **RES_ONLY in `tnr_sys1`:** an arm with the IOS families off reads the stored IOS tables, and only `tnr_sys1` never had
  them rewritten (IDENTITY ran C1's patches alone). C2's guard would refuse a table stamped by another arm.

**The NEW arms** (addition 3 §4; new files only, so no SYS-family input can move):
* **The pins** (`level_pins.py`). Stage 1's K and surface weight, the offset Elo's kd (both kinds) and Stage 3's
  constants are replaced by the reference build's (`arms/constants/reference_constants.json`) on the line where each
  builder has chosen them, when the config names `pin_constants`. Each pin records the build's own tuned value. Pieces
  and Stage 4 read Stage 1's constants from its summary, so they follow. Stage B is pinned by the layer's own pin, the
  IOS constants by `IOS_CONSTANTS_VERSION`.
* **The install** (`system_new_arms.py --patch --stage0 F`): role F's Stage 0 and timeline over the sandbox's tables
  (`system_sandbox.patch`), C1's and C2's patches, then the pins as three anchored edits on top of C1's, in NEW-arm
  sandboxes only. A NEW sandbox is refused for any other arm, and the other way round.
* **Lane 0** runs Stage 1's odds link and the full leak-proof rebuild (F brings its timeline). Then **F's lane-0 check**,
  before lane 1: Stage 1's odds table against the frozen file, and the 67,226 frame matches unchanged in every column.
  Stage 0's global `order` column is compared by relative order, since the new matches shift its values. Tested on a
  scratch copy with C0_now installed: odds bytes equal; 67,226 frame matches, 35 columns equal, relative order equal.
* **NEW_SYS_BOTH's strength** (the lead, 02:08 UTC): the plain Elo on C0_now under the reference K, with no w_results
  hook, which is exactly NEW_ASIS's Stage 1. `system_new_arms.py --strength` writes it from NEW_ASIS's sandbox in
  `strength_elo.parquet`'s columns, hashed. It must equal the reference strength on every match before C0_now's first
  new match.
* **Their gates:** the same frame matches, identifiers and results through 2024; the nine inputs no Stage 0 row feeds
  (odds, tour, surface, level, indoor, best of, round, age, age²) exact; the constants the reference's; F's lane-0
  check; the builders' probes. G2 and G3 read the frozen Stage 0's reach, so they do not apply.

**The Phase 2 arms** (Observed; `system/arms/<ARM>/gates/`, `build.json`; times UTC on 10 Oct):

| Arm | Sandbox, lane-2 folder | Built | G2 | G3 | Constants, probes | C2 end to end | READY |
|---|---|---|---|---|---|---|---|
| SYS | `tnr_sys2`, `lle_SYS_24795056aa30` | 02:00–04:55 (175 min) | pass | 16 of 17 + `form_first_in` by the lead's ruling | pass | not comparable (C2's SYS file predates the cap and the fix) | 05:12 |
| SYS_w0 | `tnr_sys3`, `lle_SYS_w0_dc8c136d1a63` | 02:21–05:18 (177 min) | pass | 17 of 17 | pass | 22 of 22 exact | 05:19 |
| SYS_w50 | `tnr_sys2` | 04:56–07:09 (134 min) | pass | 17 of 17 | pass | no C2 file | 07:09 |
| SYS_NOCLASS | `tnr_sys3` | 05:19–07:24 (125 min) | pass | 17 of 17 | pass | no C2 file | 07:24 |
| RES_ONLY | `tnr_sys1` (Stage 3, Stage B's adjperf and IOS from IDENTITY_ALL's sandbox) | 06:43–08:04 (81 min) | pass: every one of the 55 non-Elo inputs bit for bit on all 67,226 matches; only `elo_overall`, `elo_surf_offset` and `elo_games` move, on the 34,719 men's matches | none required (w = 1) | pass | no C2 file | 08:04 |
| SYS_w100 | `tnr_sys5` | 04:06–06:42 (157 min), then resumed from `thinking_frame` 07:09–07:36 | first run failed (`indoor`, below); pass after the fix | 15 of 17 + `form_df` (not required) and `form_first_in` (follows B's δ) by the ENV rule | pass | no C2 file | 07:36 |
| SYS_ITFASIS | `tnr_sys3` (validated code restored: 51 files) | 07:24–10:02 (158 min) | pass | 16 of 17 + `form_first_in` by the ENV rule (as SYS) | pass | no C2 file | 10:03 |
| SYS_BOTH | `tnr_sys2` | 07:37–10:08 (151 min) | pass | 32 of 34; `form_first_in` (men) by the ENV rule; women's `formdef_df` (OPP) the ruled exception (addition 7) | pass | 22 of 22 exact against C2's `SYS_BOTH_cap` | 14:00 |
| SYS_BOTH_ITFASIS | `tnr_sys1` | 08:05–10:29 (144 min) | pass | the same two cells as SYS_BOTH | pass | no C2 file | 14:00 |
| NEW_ASIS | `tnr_sys4` (C0_now, the pins) | 08:53–12:49 (235 min: lane 0 and Stages A and C included) | NEW-arm gates: identifiers, the nine fixed inputs, F's lane-0 check, constants: pass (`debut_season` changes on 10 matches, reported) | — | pass | — | 12:50 |
| NEW_ASIS_PRE | `tnr_sys2` (C0_pre, the pins) | 10:08–13:03 (175 min) | NEW-arm gates: pass | — | pass | — | 13:03 |
| NEW_SYS_BOTH | `tnr_sys5` (C0_now, the pins, option (c)'s strength) | lane 0 to Stage 3 10:03–10:50; from Stage 4 14:01–15:34 with option (c) (addition 7) | NEW-arm gates: pass (`debut_season` on 10 matches, waived) | — | pass | — | 15:34 |

* **The NEW arms' constants** (Observed, the pins' records). On C0_now and C0_pre the builders' own tuning chose the
  reference's Stage 1 K and surface weights and Stage 3 constants; Stage B's tuning differed for men's spw and women's
  tpw, which the pin replaced. Stage 1's odds table is byte-identical to the frozen one in every NEW sandbox.
* **NEW_SYS_BOTH's strength** (Observed, `arms/strength/NEW_C0_now_elo.json`; the question is the lead's). The file is
  written as ruled at 02:08: NEW_ASIS's plain Elo on C0_now, sha256 cfa48f2f…, covering all 1,171,445 matches. C0_now's
  added matches move the Elo scale as well as the ratings: new entrants start at the default rating and lose points to
  established players. On the reference's matches of 2010–2024 the new pre-match rating minus the reference's averages
  +75 to +92 for women in every season and at every level (MAIN +77); for men it is 0 through 2017, then +13 (2018) rising
  to +85 (2024) at the lower levels (MAIN +7 overall). B's `strength_ref` is on the reference's scale, so the γ term would
  move by γ × 0.75–0.92 for women's lower-level rows. Offered: (a) as ruled; (b) re-centred per tour and season on the
  main-tour mean (still +33 for men's reference matches, −11 for women's: the lower levels gained relative to the main
  tour); (c) the reference strength for the 873,437 matches it covers and the re-centred new Elo for the 298,008 new ones,
  which leaves every reference match's translation exactly as SYS_BOTH's. I suggested (c). With no ruling by 12:00 UTC the
  build resumed with (a), its READY held. **The lead ruled (c)** (addition 7, 8e302da0…, 13:59 UTC): the strength file is
  `arms/strength/NEW_C0_now_elo_optC.parquet` (sha256 1a9c211a…; the reference's `strength_elo`, identical, on its
  873,437 matches; the re-centred plain Elo on the 298,008 new ones). NEW_SYS_BOTH was rebuilt from Stage 4 under its
  name; its lane 0, Stage 1, Stage 3 and lane 2 read no strength and were reused. The option-(a) build is kept as
  `arms/NEW_SYS_BOTH_optA_unread/`, never scored.

* **SYS_BOTH's and SYS_BOTH_ITFASIS's held cell** (Observed): women's `formdef_df`, A's class OPP, so outside the ENV
  rule. The correlation is −0.0015 (−0.022 in SYS_BOTH_ITFASIS) where the first run's offset (−0.055, just past the
  0.05 threshold) expects a positive sign. The arm moves this input by 0.0009 on average against an SD of 0.016, and the
  by-season correlations swing both ways (−0.17 to +0.21). In the adjdef channel the match's value and the opponent's
  norm rows are both df, so their δ terms cancel and the change is mostly the weights. The lead ruled it an exception
  (addition 7): both arms READY at 14:00 UTC, the cell recorded in `gates/waivers.json`.

**G4, the dose** (Observed, `system/arms/g4/`, 07:38 UTC): all 41 box-score inputs change less at w = 0.5 than at w = 1
from SYS_w0, in the same direction (correlation 0.97–1.00). SYS's change is 0.72–0.97 of w = 1's: its fitted weights,
capped at 1, sit between. The forms on the return side and the adjdef forms move about 0.005 against 0.04–0.08 for the
others, but their spread is ten times smaller too (men's SD 0.016–0.023 against 0.19–0.32): about 0.3 SD in both.

* **SYS_w100's first build failed G2, on a cause outside the layer** (Observed). Every women's match and 127 men's 2026
  matches had `indoor` filled where the reference has it missing. `tnr_sys5` was the only sandbox set up after the
  repository's src changed outside this team: `tabpfn_thinking/build_frame.py` fills the women's indoor flag from the
  WTA calendar since 10 Oct 01:14 UTC (`src/eda/indoor_fill/`, uncommitted). Every other input of the women's matches
  was exact. Its G3 had passed (15 of 17, `form_df` and `form_first_in` by the ENV rule: not required, and follows B's δ).
* **The fix, build code only.** `system/arms/validated_src/` holds the chain's code exactly as IDENTITY_ALL ran it and
  G1 validated it (`tnr_sys4`'s src at 00:30 UTC: 1,070 files; MANIFEST.sha256 1e95dbfe…). Every build and resume now
  restores a sandbox's code to it first, and refuses if a patched builder differs (`system_arms.restore_validated_code`).
  * The arms built in `tnr_sys1`–`tnr_sys3` ran chain code equal to the snapshot. Their 51–54 differing files lie
    outside the 64 modules that lanes 1–3 import.
  * In `tnr_sys5` the chain's differences were `build_frame.py` and two additive changes (a description string; a
    correction action no decided table uses).
  * SYS_w100 was resumed from `thinking_frame` with the snapshot's code (C2's IOS part rebuilt first) in slot B, before
    SYS_BOTH. To keep three builds at most, chain B was held by marking `tnr_sys2`'s already-run Stage 3 builder, which
    makes the next patch refuse that sandbox; the hold is lifted by writing C1's patched text back.

* **SYS's G3 cell, and the lead's ruling** (status 05:1x UTC). `form_first_in` (men) correlated +0.038 with the
  reached-share gap where the first run's offset (+0.105) expected a negative sign; SEP_ALL's cell was −0.060. By season
  the cell is −0.11, −0.06, −0.06 in 2013–15, about 0 in 2016–20, and +0.04, +0.05, +0.12, +0.18 in 2021–24. It
  follows B's fitted δ for first_in at GSQ, positive through 2020 and negative from 2021, while the opponents' norm rows
  (A's ENV class: δ only, of def_first_in) take a positive δ at TQ, CH and CHQ. The lead ruled that G3 follows B's
  walk-forward parameters, not the first run's static offsets, and marked SYS READY.
* **The standing rule, as coded** (`system_gates.env_rule`). A failed cell of an ENV-class input in a translating arm
  is re-scored per dev season (2013–2024; the sealed parameters are not read). D_Y is the frame's two-week box
  evidence at the reached levels, weighting B's season-Y δ of the own statistic minus the signed δ of the opponents'
  norm view, each only at A's `delta_levels`. Where |D_Y| ≥ 0.05 the season's correlation must have the sign −D_Y. The
  verdict is recorded and never holds the arm; any other failed cell holds it.
  * For SYS's `form_first_in`, D_Y reaches 0.05 in 2013, 2017, 2018 and 2023. The cell follows B's δ in three of them
    and not in 2018 (D −0.058, correlation −0.06). 2018 is CHQ's first fitted season: δ of first_in −0.19 and of
    def_first_in +0.41 there. Recorded as "not required under the lead's rule".

## What it does not show

* **No model-level reading here.** Role D fits and scores the arms; this report shows only that the inputs were built as
  specified and checked.
* **The gates check the inputs' mechanics, not their value.** G2 shows what must not move did not; G3 and G4 show the
  changes point and scale as the parameters imply; none says whether an arm forecasts better.
* **G3's expectations are partly the first run's offsets** (2010–2018), not this run's parameters. The lead's ENV rule
  re-scores ENV-class cells against B's δ per season; the other cells still use the offsets, and two weak cells (SYS's
  `form_first_in`, SYS_BOTH's women's `formdef_df`) are recorded or held rather than explained in full.
* **SEP_ALL's and REF_noITF's layer copies are argued, not rebuilt** (§7). G2 on their frames supports the argument.
* **The validated-code snapshot is IDENTITY_ALL's sandbox at 00:30 UTC on 10 Oct**, not the frozen reference's own code
  copy. 42 of the reference's listed source files differ from it; 15 of them are modules lanes 1–3 import: the 10
  patched builders (the snapshot holds their patched text) and 5 changed after the freeze (`corrections.py` and
  `stage0_build.py` with an added correction action no decided table uses; `surface_ios/common.py`,
  `surface_ios/summarise_tuning.py`, `ufc_ideas/stageB_ios.py`). G1 shows the 58 inputs unchanged by them; their
  intermediate outputs were not compared.
* **The NEW arms' gates cannot separate data from method.** Every frame match's inputs change on C0_now (new history
  reaches everyone through Elo and workload), so only the fixed inputs, the identifiers and the constants are checked
  exactly.
* **NEW_SYS_BOTH's strength is unresolved** (§12): built with the strength as first ruled, held for the lead.
* **Some of IDENTITY's layer records are smoke tests**, and the layer's records pool every arm's calls by arm folder only;
  the records describe dev seasons only (sealed seasons give counts).
