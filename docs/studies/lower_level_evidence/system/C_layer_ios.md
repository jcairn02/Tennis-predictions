# The level layer in the joint solves: surface IOS, `ios_points_short` and the products (role C2)

9–10 October 2026 · Role C2 (joint-solve engineer) of the level-evidence system · Phases 1 and 2 (updated 10 Oct: the
lead's cap; the pooled form-(b) fix, §6) · Research evidence, not a decision.
Specification: [SPEC.md](SPEC.md) §3 (the "joint solves" row), §6.3, §9, §10.

**Keys.** *Observed* = read in code (cited `path:line`) or computed here (file cited). *Inferred* = reasoning.
*Suggestion* = a proposal for the lead. No 2025–2026 outcome was read: the gates compare inputs and solver outputs only.
Paths: `system/` = `data/studies/lower_level_evidence/system/`; the code is
`src/eda/lower_level_evidence/level_layer_ios.py` (written `L` below).

## In short

* **Observed. What the chain rebuilds.** Lane 2 rebuilds the surface IOS behind the 21 `iosO_*`, `iosD_*` and
  `prod_*` inputs. `ios_points_short`, and the pooled IOS that lane 3 checks lane 2 against, reach the model **stored**
  in `match_timing/leakproof_features.parquet`, which no lane of `run_chain.py` rebuilds. A hooked build now rebuilds it
  in the sandbox (`rebuild.py --part ios`, then `--part merge`) before lane 1's `leakproof_frame`; guards refuse a build
  that mixes configs.
* **Observed. The hooks.** The decided solvers with two per-row arrays: an exchange rate m (m = 0 drops the row exactly)
  and a supplied level term δ (form a). Form (b), a level effect estimated inside each snapshot's solve, is built too.
  16 anchored edits in 6 sandbox files, off unless `LLE_LAYER` is set.
* **Observed. Identity: bit for bit.** With the hooks on and the identity config, the 22 IOS-family inputs equal the
  reference's on all 67,226 matches (0 cells changed); the IOS part alone equals the stored table on 255,832 pool matches.
* **Observed. w = 0.** SEP_ALL and REF_noITF run, and the dropped rows leave the solves exactly: bit for bit against
  the decided solvers on the history without them, in the IOS part and in lane 2. Women stay bit for bit under SEP_ALL.
  Before each tour's first ITF box score, REF_noITF keeps `ios_points_short` bit for bit and the 21 surface inputs
  within 4·10⁻¹⁵, which is the decided surface solver's own rounding when ITF-only players leave its system.
* **Observed. No leak with the hooks on.** `match_timing/probe.py` (form b; SEP_ALL) and the surface probe (form b) move
  no earlier match at any of the four cut days.
* **Observed. Finding #6, from both sides.** In the reference the products' 2025–26 spread is 1.08–1.61 times 2024's;
  without ITF box scores (REF_noITF) it is 0.94–1.16, within the earlier seasons' range. SEP_ALL, the other way, shrinks
  five products to 0.37–0.74 of their SD while the A − B inputs keep theirs. *Inferred:* the products' scale is the
  ratings' zero point, which moves with the pool's level mix.
* **Observed. Phase 2, the lead's rulings.** The level term is form (b), a level effect estimated inside each
  snapshot's solve at role A's levels of the statistic. Each observation takes B's `w_joint` for its own season (floor
  2013). The prior is the pool's (B's method F4); form (a) is off. Level effects are small (men's holds −0.06 to −0.09
  logit at CH and CHQ, aces −0.12 to −0.20).
* **Observed. Phase 2 gates, on B's frozen parameters.** SYS_w0 equals SEP_ALL bit for bit. The leak probes pass with
  form (b) and fitted w on both tours. Form (b) moves the ratings in the direction its estimates imply in 26 of 26
  checks (correlation 0.91–0.97). Lane 3's mapping check failed on SYS: a gap of 2.4·10⁻¹² against its limit of
  10⁻¹². Lane 2's pooled runs split the rows by surface and the timed runs do not; with that split removed, the two
  runs are equal bit for bit, and a capped build of SYS_BOTH passes (1.3·10⁻¹⁵). The module is now `3fa5f69e…` (the
  CP1 freeze had recorded `077c760a…`). The lead's cap on fitted w reaches the solves through C1's `weights()`, with
  no change here.

## 1. What the chain rebuilds, and what it reads stored

*Observed* (the lanes: `src/eda/model_rebuild/run_chain.py:65-93`).

| Inputs | Built by | In the chain | Read from |
|---|---|---|---|
| `iosO_*`, `iosD_*` (14), `prod_*` (7) | `surface_ios/build_cache.py` (the rows, levels, timeline), `build_features.py` (32 full-history runs: "current" and "surface", 8 statistics, 2 tours) | **Rebuilt, lane 2** (`run_chain.py:88-89`). The sandbox copy leaves out `full_runs/` (`run_chain.py:142`), so no saved run is reused | lane 3: `surface_ios/arms.py` arm `sprof` (`plan.py:31-32`, recipe `arms.py:33-46`), then `surface_rating_race/model_frame.py:47-57` |
| `prod_*` (7) | the recipe `prod = O_A·(−D_B) − O_B·(−D_A)` on the surface-effective O and D (`surface_ios/arms.py:46`; pooled: `match_timing/rebuild.py:220`) | follow the IOS: no hook of their own | as above |
| `ios_points_short` (1) | `match_timing/rebuild.py:179-221` (`ios_time.run_timed` on spw with the short half-life, `stageB_ios.matchup_points`) | **Read stored**: `match_timing/leakproof_features.parquet`, column `ios_short` (`tabpfn_leakproof/common.py:39, 45`). Only `rebuild.py` writes it, in run_chain's lane 0 ("a candidate only … Not yet exercised", `run_chain.py:35-37, 66-68`) | lane 1's `leakproof_frame` (`tabpfn_leakproof/build_frame.py:67`) and `elo_frames` (`surface_elo_pieces/build_frames.py:54`), then the model frame |
| the pooled leak-proof IOS `ios_O/D_*|single`, `prod_*|single` (an intermediate) | `rebuild.py:214-220` | **Read stored**, as above | lane 3's `frames.py:42-45` (the base frame), whose values `arms.py:83-91` checks against lane 2's "current" runs to 10⁻¹² |

* **The consequence** (*Observed*, by the code above). A layer that changes the joint solves must also rebuild
  `leakproof_features.parquet` in the sandbox, or `ios_points_short` keeps the reference's values and lane 3's mapping
  check fails (lane 2's hooked "current" runs against the stored pooled IOS).
* **What the sandbox now runs** (*Observed*, `L.run_ios_part`): `rebuild.py --part ios` (the 16 timed solves: 7
  statistics "tuned" and spw "short", both tours), then `rebuild.py --part merge` (the stored per-player part plus the
  new IOS part). It must finish before lane 1's `leakproof_frame`; a guard there refuses otherwise.
* **The stored tables are the reference's** (*Observed*). On 9 Oct the repository's `stage0_*`, `stage1_odds`,
  `timing.parquet`, `ios_features.parquet`, `leakproof_features.parquet` and `perplayer_features.parquet` hash as the
  frozen reference's `tables/` and `tables_later/` (`frozen/files.csv.gz`). The stored `ios_short` equals the
  reference frame's `in_ios_points_short` on all 67,226 matches. The repository's own `surface_features.parquet` is
  older (6 Oct) and does not: the 21 surface inputs exist only as lane 2 rebuilds them.

## 2. The hooks

**Switched off by default** (*Observed*, tested). `LLE_LAYER` names the layer config, read by C1's loader
(`level_layer.py`: `validate`, `config`, `weights`). Unset, every hook returns its input object and every solve is the
decided function's call. Set, a solve of a tour the config names, in a family it switches on, runs a solver variant:

* **The variants** (`L.solve_timed`, `L.solve_surface`): the decided `ios_time.run_timed` and `ios_surface.run`, line for
  line, with two per-row arrays.
  * **m_k, the exchange rate.** The row's weight is (d/d_typical)^τ · 2^(−age/h) · m_k, in the snapshots and in the
    incremental step. MAIN and TEAM rows: 1. m_k from C1's `weights()`: the arm's number; ITF and ITFQ rows 0 under
    `itf_box` "exclude" and untouched (1, as the reference has them) under "as_is" (C1's rule of 21:25 UTC: no training
    season holds their box scores before P7).
  * **A row with m_k = 0 is dropped:** it leaves the system, its pairs and the incremental step, exactly as a row without
    a box score. "w = 0" is a physical exclusion, not a near-zero weight.
  * **δ_k, form (a) of the level term:** y_k ← y_k − δ_k, in the solve's units (the centred logit of the statistic's
    rate). The solver takes it; the config path to role B's δ is Phase 2.
  * With every m_k = 1 and δ_k = 0 the variants perform the decided operations in the same order (x·1.0 and y − 0.0 are
    exact), so the identity config is the reference bit for bit.
* **Form (b), the level effect estimated in the solve** (`L.solve_fe`; config `translate` true with
  `ios_level_term` "fixed_effect"):
  * y_k = O_srv + E_srv,s − D_ret − F_ret,s + β_L(k) + noise, with β = 0 at MAIN and TEAM;
  * β_L is a few extra unknowns in each snapshot's ridge system (penalty κ), estimated from the released rows only, so it
    is walk-forward by construction;
  * the incremental step holds β at the gap match's own snapshot, as it holds the opponent's rating there;
  * the levels: every lower level when the config has no classes; otherwise the union of role A's allowed levels for the
    solve's two inputs (`iosO_s`, `iosD_s`; `ios_points_short` for spw), through C1's `gate()`. One observation feeds
    both inputs, so a solve has one level term per level; A's `prod_*` rows read the union too. ITF and ITFQ never get
    one, as C1's `translation()` never translates them.
* **The tables the hooks need:** each solver row's level (Stage 0's `map_level` → `common.bucket`) and season (Stage 0's
  year). `annotate_td` adds them in `rebuild.py`; `annotate_cache` writes them into lane 2's cache.
* **The sandbox patch** (`L.apply_patch`; 16 anchored edits in 6 sandbox files, each anchor found exactly once; the diff
  is `system/ios_layer/sandbox_patch_ios.diff`):

| Sandbox file | Edit |
|---|---|
| `match_timing/rebuild.py` | `_ios_task`: `L.run_timed(..., label=label)`; `ios_features`: `L.annotate_td(td, rows)`; `part_ios`: `L.stamp(meta)` into `ios_features_summary.json` |
| `surface_ios/build_cache.py` | `L.annotate_cache(arrays, rows, idx)` before each tour's npz |
| `surface_ios/build_features.py` | `RUNS = L.runs_dir(...)`; `task`: `L.run_surface(...)`; `L.stamp(...)` into `build_features.json` |
| `tabpfn_leakproof/build_frame.py` (lane 1) | `L.require_consistent(ROOT, "ios_part")` first |
| `surface_ios/arms.py` (lane 3) | `L.require_consistent(ROOT, "both")` first |
| `surface_ios/probe.py` | the probe's rows get their tour and levels; `L.run_surface` in place of `IS.run` |

* **Two safeguards** (*Observed*, tested).
  * **A runs folder per config.** `build_features.py` reuses a saved run whenever its IOS constants match
    (`build_features.py:95-101`), and the constants know nothing of the layer. With the layer on, the runs go to
    `full_runs/lle_<name>_<fingerprint>/`, so a sandbox reused for several arms never reads another config's runs.
  * **The guards.** Each hooked step records the config's fingerprint (a hash of everything the IOS outputs depend on).
    Lane 1's `leakproof_frame` and lane 3's `arms.py` refuse to run when the IOS part, the merge or lane 2 was built with
    another config, or not rebuilt at all while the layer touches the family. A config that leaves the joint solves
    alone has the fingerprint "off" and is served by the stored (decided) tables.

## 3. The gates

All in the dev sandbox `C:/Users/zerom/tnr_sys_ios` (`run_chain.py --setup --candidate`; history check: 0 new past,
0 dropped, 0 revised), `IOS_CONSTANTS_VERSION=2026-10-08_reference`. Results in `system/ios_layer/gates/`.

| Gate | What is compared | Result |
|---|---|---|
| **Identity, the IOS part** | the hooked `rebuild.py --part ios` (identity config, both tours; all 16 timed solves through the variant, each recording the layer) against the stored `ios_features.parquet` (= the frozen reference's `tables_later` copy) | **Equal bit for bit**: 255,832 pool matches × 22 columns (14 pooled O/D, 7 products, `ios_short`) |
| **Identity, the model's inputs** | the 22 IOS-family inputs rebuilt from the hooked IOS part and lane 2 (32 runs, all through the variant) by the chain's own recipes, against the frozen reference frame (`identity_IDENTITY_m1.json`) | **Pass: equal bit for bit on all 67,226 matches**, the same cells missing; 0 cells changed |
| **SEP_ALL: the rows drop out** | the decided `rebuild.ios_features`, with the men's lower-level box scores removed (ok false), against the hooked IOS part (`drop_timed_SEP_ALL.json`) | **Pass: equal bit for bit** on all 22 columns × 255,832 pool matches |
| **SEP_ALL: everything else equal** | the 22 inputs against the reference (`equal_SEP_ALL.json`) | **Pass**: women's 32,507 matches unchanged bit for bit. Men's 34,719 all change (below) |
| **SEP_ALL: lane 3's mapping check** | lane 2's hooked "current" runs against the IOS part's hooked pooled IOS on the frame's matches, as `surface_ios/arms.py:83-91` does (to 10⁻¹²) | **Pass**: largest gap 2.2·10⁻¹⁵; both records carry SEP_ALL's fingerprint |
| **SEP_ALL: the rows drop out, lane 2** | for each of the 8 men's statistics, the hooked system against the decided one built on the cache with those rows' ok false (rows, values, units, surfaces, release days, pattern); then the full men's holds solve ("surface") against the saved lane-2 run (`drop_surface_SEP_ALL.json`) | **Pass**: the 8 systems identical; the solve equal bit for bit (307,849 rows dropped) |
| **REF_noITF: the rows drop out** | as for SEP_ALL, with the ITF and ITFQ box scores of both tours: the timed part (`drop_timed_REF_noITF.json`), and lane 2 (16 systems; full holds solves, men and women: `drop_surface_REF_noITF.json`) | **Pass: bit for bit**, timed (22 columns × 255,832 pool matches) and lane 2 (45,044 and 46,252 ITF rows dropped) |
| **REF_noITF: everything else equal** | every match whose earliest start precedes the tour's first ITF/ITFQ box score (men 29 Dec 2024, 29,910 matches; women 2 May 2022, 21,445), against the reference (`equal_REF_noITF.json`) | **Pass**: `ios_points_short` bit for bit; the 21 surface-solver inputs within 4.0·10⁻¹⁵ (men) and 1.8·10⁻¹⁵ (women), the same cells missing (below) |
| **The decided surface solver's own rounding** | the decided `ios_surface.run` on the full history against itself on the history without ITF rows, single-threaded as lane 2 runs it; women's holds before 2 May 2022 (`decided_active_set_wta_hold.json`) | 105,711 of 537,000 rows differ, by at most 1.6·10⁻¹⁵; its system holds 4,002 players with ITF rows, 1,893 without |
| **REF_noITF: lane 3's mapping check** | as for SEP_ALL (`mapping_REF_noITF.json`) | **Pass**: largest gap 4.7·10⁻¹⁵ |
| **Leaks: `match_timing/probe.py`, hooks on** | the sandbox's probe (2023–2024 slice, 4 cut days, every later result reversed) with PROBE_FE (form b, both tours) and SEP_ALL (`probe_match_timing_*.json`) | **Pass, both**: 0 earlier matches moved at every cut (13,758–31,163 checked; largest difference 6·10⁻¹⁵ against the probe's 10⁻⁹) |
| **Leaks: `surface_ios/probe.py`, hooks on** | the sandbox's patched surface probe (spw, hold, first_won; two surface penalties; the same slice and cuts) with PROBE_FE: the fixed-effect surface solver (`probe_surface_PROBE_FE.json`) | **Pass**: 0 earlier matches moved at every cut (13,758–31,163 checked; largest difference exactly 0) |
| **The probes ran the layer** | the sandbox's patched `rebuild.ios_features` on Jan–Jun 2023 with PROBE_FE, against the decided code (`hooked_path_PROBE_FE.json`) | **Yes**: all 16 solves record the layer (men's holds: level effects at TQ, GSQ, CH, CHQ); the 22 values differ on about 8,960 pool matches; the decided run records none |
| Tests | `test/lower_level_evidence/test_level_layer_ios.py` | **45 pass**: off-by-default; both variants equal the decided solvers bit for bit (several κ_s, τ, h, `until_day`); w = 0 equals the box score removed, bit for bit; δ equals y − δ, bit for bit; weights equal a dense weighted ridge; form (b): no levels equals the plain solver bit for bit, planted effects recovered (within 0.02), the dense augmented system matched (10⁻⁶); no leak (both variants and form b); the config's forms, switches and refusals; the patch (fake sandbox, idempotent, checked, refused on the repository); the guards |

**Which module ran which gate** (*Observed*). The identity build (20:28–21:10 UTC) ran the module's first version, which
read the config with its own loader. The final version reads it with C1's (`level_layer.config`, `weights`); its solver
code is the same. On the sandbox's real rows it gives m = 1 and δ = 0 for every row of both tours under the identity
config (checked for spw and hold, both families), so it performs the identity build's arithmetic. SEP_ALL, REF_noITF and
the probes ran the final version.

**Why REF_noITF is not bit for bit everywhere before 2025** (*Observed*, then *Inferred*).
* *Observed:* the timed solver's input (`ios_points_short`) is bit for bit. The 21 surface-solver inputs differ in the
  last bits on most matches before each tour's first ITF box score, by at most 4.0·10⁻¹⁵.
* *Observed:* the decided surface solver does the same by itself. Given the same history without the ITF rows, it moves
  women's holds before May 2022 by up to 1.6·10⁻¹⁵, and the hooked solver equals that decided run bit for bit (the drop
  gate).
* *Inferred:* the surface solver's system holds only the players with a box score somewhere in the history
  (`ios_surface.py:116-121`). ITF-only players leave it when their rows go, the CG vectors get shorter, and the BLAS
  reductions round differently from the first snapshot on. The timed solver holds every player of the tour
  (`ios_time.py:43`), so its values are bit for bit.
* So the criterion here is the one lane 3 itself applies between the two IOS solvers: 10⁻¹² (`surface_ios/arms.py:90`).
  An untouched tour runs the decided code and is bit for bit.
* **The harness's own false alarm.** The first runs of both lane-2 drop gates failed: the gate's worker processes used
  multi-threaded BLAS, while lane 2's runs are made single-threaded (`build_features.py:26-27`). The CLI now pins one
  thread for its workers (only in the CLI, so an importing process keeps its own setting), and both gates pass bit for
  bit.

**What REF_noITF does to the products** (*Observed*, `gates/products_spread_REF_noITF.csv`; inputs only, no outcome
read; the expectation was written in the status log at 20:44 UTC, before REF_noITF existed). SD of each product by
season, as a ratio to its 2024 SD:

| Product | Reference 2025 / 2026, men | REF_noITF, men | Reference, women | REF_noITF, women |
|---|---|---|---|---|
| `prod_hold` | 1.28 / 1.39 | 1.15 / 1.10 | 1.20 / 1.53 | 0.97 / 1.01 |
| `prod_first_won` | 1.29 / 1.44 | 1.11 / 1.09 | 1.26 / 1.61 | 1.00 / 1.04 |
| `prod_second_won` | 1.27 / 1.30 | 1.16 / 1.06 | 1.08 / 1.26 | 0.96 / 0.94 |
| `prod_ace` | 1.25 / 1.38 | 1.11 / 1.12 | 1.11 / 1.35 | 0.94 / 1.00 |
| `prod_bp_saved` | 1.18 / 1.22 | 1.15 / 1.13 | 1.10 / 1.31 | 1.04 / 1.10 |

* Without ITF box scores the 2025–26 widening of the products (finding #6) mostly goes: the ratios fall within the
  seasons' own spread before it (men's `prod_hold`: 1.20 in 2022, 1.02 in 2023). `prod_df` and `prod_first_in` did not
  widen and do not move.
* The 14 A − B ratings and `ios_points_short` change too, from each tour's first ITF box score on (men 2025–26; women
  slightly from May 2022: D counts 31 women's ITF box-score matches in 2022); D's input check reads them against the
  tour-season's evidence mix.

**What SEP_ALL does to the men's inputs** (*Observed*, `equal_SEP_ALL.csv`; inputs only, no outcome read).
* It drops 309,692 of the 396,240 men's box-score rows (78%): Challengers 168,536, their qualifying 52,912, ITF 45,452
  (2025–26), tour qualifying 31,850, Slam qualifying 10,942.
* The 14 A − B ratings keep their scale (SD ratio to the reference 0.92–1.29 by season) and level (within ±0.03 SD).
  `ios_points_short` too (0.96–1.09).
* **Five of the seven products shrink to 0.37–0.74 of their SD** (`prod_df` and `prod_first_in`: 0.86–1.43).
  *Inferred:* with only main-tour rows, the ridge's zero is the main-tour average, so main-tour players' O and D sit near
  zero and their products shrink. It is finding #6's zero-point mechanism, seen from the other side.
* *Inferred:* SEP_ALL changes the products' meaning, not only their evidence. D's input check will flag them; that is
  expected for this arm.

## 4. Timings

*Observed* (`system/ios_layer/builds/<config>/chain_lane_ios.json`, `chain_lane2.json`; the reference's own records in
`frozen/instance/chain_lane2.json` and `ios_features_summary.json`). The machine was shared with other roles' builds and
mostly at 100% CPU, so the loaded figures are upper bounds.

| Step | Idle machine (the reference's builds) | Here, loaded |
|---|---:|---:|
| IOS part: `rebuild.py --part ios` (16 timed solves, 4 workers) | 291 s | 739 s (IDENTITY), 328 s (SEP_ALL), 1,677 s (REF_noITF) |
| merge: `rebuild.py --part merge` | — | 113 s, 17 s, 78 s |
| lane 2: cache | 70 s | 370 s, 108 s, 239 s |
| lane 2: 32 full-history runs (14 workers idle; 10 here) | 1,066 s | 1,294 s, 551 s, 1,780 s |
| the guards | — | under a second |
| form (b), one solve (women's holds, surface model, to 2024) | — | 21 s against 16 s without the level term (95 s against 60 s in a first run under heavier load) |
| leak probes | 760 s (match_timing, decided) | 981 s (PROBE_FE), 435 s (SEP_ALL); surface probe 1,337 s (PROBE_FE) |

* **What an arm adds** (*Inferred*): the IOS part and the merge, about 5–6 minutes on an idle machine, before lane 1
  reaches `leakproof_frame`. Lane 1 takes about 90 minutes to get there, so run beside lanes 1 and 2 it costs no wall
  time; run first, about 5 minutes.

## 5. The level term: the two forms, and a recommendation

**Form (a), a supplied δ** (B's estimate, subtracted from lower-level rows).
* Cheap: built (`δ_k` in the variants), bit-for-bit tested.
* **The units do not match** (*Observed* in role A's report, *Inferred* for B). A's and B's δ is the residual after the
  Elo-based opponent term γ·(Elo gap) ([A_classes.md](A_classes.md) §8–9: "My δ is the residual after Elo's γ, not after
  the solve's own opponent adjustment … Its size must be fitted in the solve's units"). In the joint solve the opponent is
  the solve's own D_returner. A δ fitted against Elo is a different object.
* **One term per observation.** The "hold" solve's observation is also the returner's break. A classes `iosO_hold` and
  `iosD_hold` (base `brk`) separately, with different allowed levels (men: CH, CHQ against TQ, GSQ, CH). A supplied δ must
  be one number per (statistic, tour, level, season), consistent across the two sides (δ_brk = −δ_hold in logit units).
* **Season.** C1's rows use the parameters of the row's own season (`level_layer.py` docstring). In a long-memory solve a
  row keeps its season's δ for as long as it weighs; that is the same rule.

**Form (b), the level effect estimated inside the solve.**
* Built and tested (`L.solve_fe`): it recovers planted level effects to within 0.02 logit, equals the dense solution of
  the augmented normal equations to 10⁻⁶, and moves no earlier value when later results are reversed.
* **In the solve's own units, by construction.** β_L is role 03's δ_L (the level's serve–return balance for the same
  players against the same opponents), estimated with the solve's own decay and opponent adjustment.
* **Walk-forward by construction.** Each snapshot estimates β from the rows released by then; nothing is fitted
  offline, so there is no parameter for a season to read before it starts.
* **No unit conversion, no per-side conflict.** One β per solve and level; A's classes decide only where it is allowed.
* **On real data** (*Observed*, `system/ios_layer/fe_demo/wta_hold.json`; women's holds, the surface model at the
  reference's constants, every lower level except ITF, history released by 29 Dec 2024 only):
  * the level effects at the last 2024 snapshot are small and negative (servers hold a little less than the ratings
    predict): TQ −0.015, GSQ −0.007, CH −0.036, CHQ −0.059 logit. At a 65% hold rate, CH's is about −0.8 points per 100:
    the sign and order of size of role 03's batch estimate (−1.36 [−1.98, −0.74], 2019–2024), from a decayed solve
    rather than player-season ratings;
  * main-tour ratings of 2019–2024 move by a median 0.0035 (O and D), against SDs of 0.30 and 0.23: about 1% of an SD;
  * the cost: 21 s against 16 s for the same solve without the term, 10.7 PCG iterations a snapshot against 9.1
    (`fe_demo/wta_hold.json`; a first run under heavier load took 95 s against 60 s).
* **What it does not do.** It is a level offset only. It is not the newcomer prior (the ridge target) and it does not
  change w.

**What the first run predicts for either form** (*Observed* there, *Inferred* here). Role 03 found the joint solve
already removes 64–87% of the same players' level gap; the residual level offsets are small (men's serve points won
−0.2 to −0.8 points per 100 at Challengers), and translating by them gained at most +0.06 milli per unit
([03_translation.md](../team/03_translation.md) §2.3, §3.1). A says the men's Challenger level effect on total points is
about 100% opponent (status log, CP0). So the level term should move the joint-solve inputs little; w (λ = 2 helped men's
holds and break points saved) and the newcomer prior (women) matter more there.

**My recommendation** (*Suggestion*). Use **form (b)** for the joint solves, gated by A's classes (the union rule above),
with B supplying w (and the prior, if B keeps it). Form (a) would need B to refit δ inside an IOS-form model per season,
which form (b) does exactly and walk-forward. Keep form (a) in the code for a test: B's in-solve δ against (b)'s, at the
statistic level, on dev seasons.

## 6. Phase 2: what was built, and its gates

**The lead's rulings** (9 Oct 2026, after CP0 and B's freeze of method F4), and how the module applies them
(*Observed*, `level_layer_ios.py`: `stat_key`, `fe_levels`, `level_arrays`, `fe_plan`, `row_plan`):
* **The level term: form (b)**, the default `ios_level_term`, at role A's `delta_levels` of the solve's statistic
  (classes.csv, kind "stat"; class OPP or ENV; "none": no term). Every lower level but ITF/ITFQ when the classes are null
  (SYS_NOCLASS). Form (a) stays in the solvers and is refused in the config path.
* **One weight per observation: role B's `w_joint`** (the mean of the serve statistic's and its receiving side's w),
  through C1's `weights(..., column=solve_w)`: the solve's serve-side statistic (spw for `ios_points_short`), the row's
  level and its own season, floor 2013, as fitted (B's bound 3), then capped at 1 by C1's `weights()` since 10 Oct (the
  lead's CP1 ruling, `fitted_cap`; see below). `missing_params` "untouched" leaves a cell without a
  parameter at w 1. ITF and ITFQ rows: 0 under "exclude", untouched under "as_is". A parameter is read only for rows
  that enter the solve.
* **No newcomer prior.** B's F4 keeps the pool prior; the prior setting stays refused. The tier-means option was not
  built: with no home tier in use it would be untested code in a file the CP1 addition freezes.
* **What the plans are on real rows** (*Observed*, the sandbox's cache, C1's configs):
  * SYS (men): level effects for spw, ace, first_won and hold at CH and CHQ, df and second_won at CH, first_in at GSQ and
    CHQ, none for bp_saved; mean kept w 0.51 (first_in) to 0.83 (second_won). 57,802 rows drop: ITF (45,452) and the
    men's CHQ of 2016–2017, which B did not fit (w_joint 0 before season 2018).
  * SYS_BOTH (women): GSQ for six statistics, none for ace and bp_saved; 48,676 women's rows drop (ITF and the WTA 125
    seasons B did not fit).
  * SYS_w0: no level effect and the same 309,692 dropped rows as SEP_ALL; SYS_ITFASIS keeps the ITF rows at w 1.
* **A bug found and fixed before the freeze** (*Observed*, test `test_sys_hooks_run_form_b_with_w_joint_and_w0_is_sep_all`).
  Rows without a box score keep m = 1 (they never enter a solve), and the first version let them create a level effect.
  Under SYS_w0 that sent the solve to the fixed-effect solver with an empty level. Now a level needs a kept observation
  (box score present, m > 0), and a solve with none runs the plain variant.
* **A record fixed before the freeze.** The fixed-effect solve's level estimates went into the build records at the last
  snapshot, which in a full build holds 2025–2026 box scores. The records now carry the last snapshot of 2024 only.

**The gates** (results in `system/ios_layer/gates/`; inputs and solver outputs only, nothing of 2025–2026 read as
evidence):

| Gate | Config | Result |
|---|---|---|
| **w = 0 equivalence** | SYS_w0 (translate on, w 0) built through the IOS part and lane 2, against SEP_ALL's inputs (`equivalence_SYS_w0_SEP_ALL.json`) | **Pass: equal bit for bit**, 22 inputs × 67,226 matches. No level effect is left, so the plain variants run, on SEP_ALL's rows |
| **Lane 3's mapping check** | SYS_w0's hooked outputs (`mapping_SYS_w0.json`) | **Pass**, 2.2·10⁻¹⁵ |
| **Lane 3's mapping check, form (b)** | SYS, module `077c760a`, C1's `level_layer.py` before the cap (`mapping_SYS.json`) | **Fail**: 2.36·10⁻¹² (prod_hold), 1.37·10⁻¹² (ios_O/D_hold), 1.02·10⁻¹² (prod_ace) against arms.py's 10⁻¹²; the other columns at 6.7·10⁻¹³ or less (first serve points won), most below 1.4·10⁻¹⁴. Lane 3 would have stopped SYS, and likely every arm with level effects on holds or aces |
| **The diagnosis** | Men's holds and aces of the same build, lane 2's pooled run repeated with the rows' surfaces zeroed (`fe_surfzero_atp_hold.json`, `fe_surfzero_atp_ace.json`) | **Equal bit for bit** to the IOS part's inputs on all 183,031 men's pool matches; the stored (split) runs differ by up to 2.6·10⁻¹² and 3.3·10⁻¹² |
| **Lane 3's mapping check after the fix** | SYS_BOTH_cap: SYS_BOTH's config under a new name (same fingerprint), module `3fa5f69e`, C1's capped `26e21291`, both tours (`mapping_SYS_BOTH_cap.json`) | **Pass**: largest gap 1.3·10⁻¹⁵. 15 of 21 columns are exactly 0, every statistic with a level effect on both tours among them. The rest is the plain solvers' rounding (bp_saved; women's ace has no level effect) |
| **The cap reaches m** | B's parameters, dev seasons 2013–2024, through `level_arrays` with C1's `26e21291` | **Yes**: all 756 cells of the solves' keys give m = min(`w_joint`, 1) (96 were above 1, largest 1.476); with `fitted_cap` null, m = `w_joint` |
| **Leaks: `match_timing/probe.py`, hooks on** | SYS_BOTH: form (b) at A's levels and B's fitted `w_joint`, both tours (`probe_match_timing_SYS_BOTH.json`) | **Pass**: 0 earlier matches moved at the four cuts (13,758–31,163 checked) |
| **Leaks: `surface_ios/probe.py`, hooks on** | SYS_BOTH (`probe_surface_SYS_BOTH.json`) | **Pass**: 0 earlier matches moved at the four cuts (13,758–31,163 checked; largest difference exactly 0) |
| **The probe ran the layer** | SYS_BOTH on Jan–Jun 2023 against the decided code (`hooked_path_SYS_BOTH.json`) | **Yes**: all 16 timed solves record the layer with A's levels (men's hold CH, CHQ; women's GSQ; none for bp_saved and women's ace); the 22 values differ on 8,216–9,011 of 9,316 pool matches |
| **Direction of form (b)** | SYS (men) and SYS_BOTH (women), each statistic with a level effect, history released by 29 Dec 2024, main-tour rows 2013–2024 (`direction_form_b.json`) | **Pass: 26 of 26** (13 solves × serve and return side). The ratings' change from adding the level term correlates +0.91 to +0.97 with its first-order prediction (−β × the player's serve share at each level; +β × his return share), slopes 0.46–0.64 |
| Tests | `test_level_layer_ios.py` | **47 pass** against C1's capped `level_layer.py` `26e21291` (the Phase 2 additions: `w_joint` by key, level and own season with the floor; both `missing_params` modes; A's levels per statistic; form (a) refused; SYS's hooks against `solve_fe`; SYS_w0 equal to SEP_ALL bit for bit; the pre-holdout record; since the fix, the timed and pooled form-(b) runs equal bit for bit, and the old arrangement not) |

* **The level effects themselves** (*Observed*, `direction_form_b.json`, the last snapshot of 2024; before the cap,
  which changes w at 96 of the 756 dev cells, mostly men's TQ and GSQ). Men: aces CH −0.12,
  CHQ −0.20 logit (fewer aces at the lower levels than the ratings predict, as role 03 found); holds −0.06 / −0.09;
  serve points −0.027 / −0.040; first serve points won −0.024 / −0.040; double faults CH +0.018. Women at GSQ: double
  faults −0.062, first serves in +0.055, the rest within ±0.014.
* **Why the slope is about a half** (*Inferred*). The prediction assumes a player's rating rests on his own rows only.
  The ridge pulls a rating toward 0 and the opponents' ratings shift too, so part of each shift is absorbed; the sign
  and the ranking hold (correlation above 0.9).

### The cap and the pooled form-(b) fix (10 October 2026)

* **The cap** (*Observed*). The lead's CP1 ruling sets a fitted w above 1 to 1. This module reads `w_joint` only through
  C1's `weights(..., column=solve_w)` (`level_layer_ios.py:319-320`), where C1 applies `fitted_cap`
  (`level_layer.py:551-596`, version `26e21291`), so the cap needed no change here.
* **Why lane 3's check failed** (*Observed*, the build records of SYS). Lane 3 compares lane 2's pooled ("current") runs
  with the IOS part's pooled IOS to 10⁻¹² (`surface_ios/arms.py:83-91`). Under form (b) both are `solve_fe`, with the
  same snapshots, players, observations and PCG iterations (men's holds: mean 17.9, max 24, in both). They differ in
  one way. The timed hook zeroes the rows' surfaces, so each server–returner pair is one term (234,264 for men's holds).
  Lane 2 kept the surfaces, so each pair is split by surface (262,802), and the sums are taken in another order.
  *Inferred:* the level effects couple every player at a level, which grows that rounding difference up to about
  1,000-fold, depending on the statistic. Men's holds reach 1.4·10⁻¹² on the ratings and 2.4·10⁻¹² on the products;
  aces 1.0·10⁻¹²; the other statistics with a level effect run from 6.7·10⁻¹³ (first serve points won) down to
  4·10⁻¹⁶ (first serves in). Plain solves stay near 2·10⁻¹⁵ (SYS_w0).
* **The fix** (*Observed*, `level_layer_ios.py` `run_surface`; module `3fa5f69e`). When a solve estimates a level effect
  in the pooled model (κ_s infinite), the surfaces are zeroed before `solve_fe`, as the timed hook does. The pooled model
  has no surface term, so only the order of the sums changes. Repeated that way on men's holds and aces, lane 2's runs
  equal the IOS part's inputs bit for bit (the diagnosis row above). A full capped build of SYS_BOTH passes lane 3's check,
  with every statistic that has a level effect exactly equal. Nothing else moves: the plain solves (so IDENTITY,
  SEP_ALL, REF_noITF and SYS_w0), the surface model (finite κ_s, also the surface probe's only path:
  `surface_ios/probe.py:42,76`) and the timed solves (`match_timing/probe.py`'s path) are unchanged.
* **A caution for the arm builds** (*Observed*, `surface_ios/build_features.py:95-119`). Lane 2 reuses a saved run whose
  constants match, in `full_runs/lle_<name>_<fingerprint>`. The fingerprint holds neither `level_layer.py`'s version
  nor the cap. A sandbox that built a fitted-w arm before the cap would reuse its runs for the capped arm of the same
  name. The IOS part is always rebuilt, so lane 3's check would then fail wherever the cap binds (*Inferred*). Each
  arm is therefore built in a sandbox that has not built that name before. Adding the two to the fingerprint is a
  one-line change, left to the lead.

## 7. Files and commands

| What | Where |
|---|---|
| The hooks, the solver variants, the patch, the gates (CLI) | `src/eda/lower_level_evidence/level_layer_ios.py` |
| The extra checks: lane 3's mapping check, the products' spread, the decided solver's rounding, the probes' hooked path, the form (b) demo, the zeroed-surface diagnosis (`--fe-surfzero`) | `src/eda/lower_level_evidence/level_layer_ios_checks.py` (first run as scratch scripts; moved here unchanged, and re-run to the same outputs; `--fe-surfzero` was first run as a scratch copy of the same code, whose outputs are the two `fe_surfzero_*` files) |
| Tests | `test/lower_level_evidence/test_level_layer_ios.py` |
| Configs (IDENTITY, SEP_ALL, REF_noITF; the probe's PROBE_W50, PROBE_FE; C2's copies of C1's SYS family; SYS_BOTH_cap) | `system/ios_layer/configs/` |
| The patch's diff | `system/ios_layer/sandbox_patch_ios.diff` |
| Build records (each config's IOS part and lane 2) | `system/ios_layer/builds/<config>/chain_lane_ios.json`, `chain_lane2.json` |
| Each config's 22 IOS-family inputs on the reference frame's matches, with the builders' records | `system/ios_layer/inputs/<config>.parquet`, `.json` |
| Gate results: `identity_*`, `drop_timed_*`, `drop_surface_*`, `equal_*` (json and csv), `mapping_*`, `probe_match_timing_*`, `probe_surface_*`, `hooked_path_*`, `decided_active_set_*`, `products_spread_*`, `equivalence_*`, `direction_form_b`, `fe_surfzero_*` | `system/ios_layer/gates/` |
| The form (b) demo | `system/ios_layer/fe_demo/wta_hold.json` |
| The hand-off to C1 | `system/arms/READY_ios_hooks.txt` |
| The dev sandbox (not deleted) | `C:/Users/zerom/tnr_sys_ios` |

```
# from the repository root
./python.sh src/eda/lower_level_evidence/level_layer_ios.py --write-configs
MODEL_REBUILD_SANDBOX=C:/Users/zerom/tnr_sys_ios ./python.sh src/eda/model_rebuild/run_chain.py --setup --candidate
./python.sh src/eda/lower_level_evidence/level_layer_ios.py --sandbox C:/Users/zerom/tnr_sys_ios --apply-patch
./python.sh src/eda/lower_level_evidence/level_layer_ios.py --sandbox C:/Users/zerom/tnr_sys_ios --check-patch
export MODEL_REBUILD_SANDBOX=C:/Users/zerom/tnr_sys_ios IOS_CONSTANTS_VERSION=2026-10-08_reference
export LLE_LAYER=$PWD/data/studies/lower_level_evidence/system/ios_layer/configs/<CONFIG>.json
./python.sh src/eda/lower_level_evidence/level_layer_ios.py --sandbox $MODEL_REBUILD_SANDBOX --run-ios-part \
    --out data/studies/lower_level_evidence/system/ios_layer/builds/<CONFIG>
./python.sh src/eda/model_rebuild/run_chain.py --lane 2 --out data/studies/lower_level_evidence/system/ios_layer/builds/<CONFIG>
./python.sh src/eda/lower_level_evidence/level_layer_ios.py --sandbox $MODEL_REBUILD_SANDBOX --collect-inputs <CONFIG>
./python.sh src/eda/lower_level_evidence/level_layer_ios.py --sandbox $MODEL_REBUILD_SANDBOX --gate-drop-timed <CONFIG>
./python.sh src/eda/lower_level_evidence/level_layer_ios.py --gate-identity IDENTITY | --gate-equal <CONFIG> <CONFIG>
./python.sh src/eda/lower_level_evidence/level_layer_ios.py --sandbox $MODEL_REBUILD_SANDBOX --gate-drop-surface <CONFIG> \
    --stats hold --kinds surface
./python.sh src/eda/lower_level_evidence/level_layer_ios_checks.py --mapping $MODEL_REBUILD_SANDBOX <CONFIG>
./python.sh src/eda/lower_level_evidence/level_layer_ios_checks.py --products REF_noITF
./python.sh src/eda/lower_level_evidence/level_layer_ios_checks.py --decided-active-set $MODEL_REBUILD_SANDBOX wta hold
./python.sh src/eda/lower_level_evidence/level_layer_ios_checks.py --fe-demo $MODEL_REBUILD_SANDBOX wta hold
# the probes, with the hooks on (from the sandbox; LLE_LAYER = PROBE_FE, then SEP_ALL)
(cd $MODEL_REBUILD_SANDBOX && python src/eda/match_timing/probe.py && python src/eda/surface_ios/probe.py)
(cd $MODEL_REBUILD_SANDBOX && python <repo>/src/eda/lower_level_evidence/level_layer_ios_checks.py --hooked-path .)
./python.sh -m pytest test/lower_level_evidence/test_level_layer_ios.py -q
```

## What it does not show

* **No model-level reading.** No fit was run; D scores the arms. The gates show that the hooks do what the config says,
  not that any config helps the model.
* **The level term's value.** Form (b) is built and tested on synthetic histories and timed on one real solve (women's
  holds to 2024); it has not been through the chain or scored. Form (a)'s config path waits for B's δ in the solve's
  units.
* **Whether `w_joint` suits a ridge solve.** B fitted w in a credibility average on raw rates, not in a joint solve
  (B's own caveat, `B_relationship.md` §9), and role 03's arms found a solve's best discount milder (λ = 2 helped men's
  holds and break points saved only). The SYS arms may over-discount in this family; the dose arms (SYS_w50, SYS_w100)
  bracket it at the model level, not separately for the joint solves.
* **The level effects' value.** Form (b) is shown to be leak-free, exact where it should be, and to move the ratings
  the way its estimates imply. Whether it helps the model is D's reading; on real data it moves ratings by about 1% of
  an SD.
* **The probes' slice.** The Phase 2 probes ran SYS_BOTH on 2023–2024 and four cut days; the direction gate reads
  history released by 29 Dec 2024. Nothing about 2025–2026 is checked beyond the code being the same.
* **The level effects after the cap.** The values in §6 were estimated before the cap, which changes w at 96 of the 756
  dev cells (mostly men's TQ and GSQ); they were not re-measured.
* **The probes after the cap and the fix.** Neither probe was re-run. The surface probe runs only the surface model
  (finite κ_s), which the fix leaves unchanged; the timed probe's solves are unchanged too. Lane 2's pooled runs with a
  level effect now do the timed runs' arithmetic exactly (the SYS_BOTH_cap check), so the timed probe covers them. The
  cap changes the value of m, not which results a match can see (*Inferred*: no new leak is possible).
* **The newcomer prior** is not built (B's method F4 dropped it); no tier means are in the solve.
* **ITF.** REF_noITF only removes ITF and ITFQ box scores. Whether ITF rows would help the joint solves at some w, or need
  a level term, cannot be estimated without box scores of non-holdout seasons (P7).
* **Bit-for-bit claims hold for this machine and these library versions.** The reference was built the same way here; a
  different BLAS could change the last bits of the reference and the hooked code alike.
* **The end-to-end chain** (lanes 1 and 3 with this patch, all 58 inputs) was not run here. In this dev sandbox the
  gates read the IOS family's outputs directly (the IOS part, lane 2) and replicate lane 3's mapping check, because a
  full lane 1 under the shared machine's load would have doubled the time to the hand-off. C1's arm builds run it (SEP_ALL
  started at 22:12 UTC with this patch); their 22 IOS columns should equal `system/ios_layer/inputs/<arm>.parquet` bit for
  bit, which is not yet checked.
* **The leak probes' slice.** Both probes cover 2023–2024 and four cut days, with the hooks on (form b; SEP_ALL). They
  do not cover the REF_noITF configuration (ITF box scores exist only from 2022 for women, 2025 for men), and form (b)
  was probed without A's classes (every lower level but ITF carries an effect).
