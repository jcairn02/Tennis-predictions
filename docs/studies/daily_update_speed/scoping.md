# Scoping: what a daily update must compute

10 Oct 2026 · Working document of [the daily-update study](README.md) · From four read-only subagent reports (briefs
verbatim: [subagent_briefs.md](subagent_briefs.md)), taken as reported unless marked **re-checked**. Step minutes:
the stand-alone replay build of 10 Oct (`data/studies/prediction_run/replay_2026-10-10_layer/build.out`,
`build_resumed.out`; observed).

## Where the 57 inputs come from

Subagent D's chain of custody, grouped. **Re-checked:** the 21 IOS inputs enter the model from the surface-IOS arm
(`surface_rating_race/arms.py`: `ARMS["model"]` uses `sf_<name>` for the 21; `model_frame.py` only checks the other
inputs against the leak-proof upload).

| Inputs | Value computed by | Path into the model frame |
|---|---|---|
| `odds_logit` | the price (live: `inject.py`), logit of Stage 4's `p_mkt` | thinking frame |
| `ratings_iid` | `stage3_ratings` (a Glicko-like pass per tour) and Stage 4's `rating_matchup` | Stage 4 → Stage D → thinking frame |
| `elo_games`, `points_52w`, `sets_14d`, `age`, `age_sq` | `stage4_features` (5 of its 165 columns) | Stage 4 → Stage D → thinking frame |
| `adjperf_tpw_2w`, `form_*` (12), `formdef_*` (4) | `ufc_ideas/stageB_adjperf` (17 statistic-channel pairs) | Stage B frame → Stage D → thinking frame |
| `iosO_*`, `iosD_*`, `prod_*` (21) | `surface_ios/build_features` (14 of its 32 runs: the 7 statistics' "surface" runs, both tours) | `sprof` arm → model frame |
| `elo_overall`, `elo_surf_offset`, `surf_season_a/b`, `surf_layoff_a/b` | `surface_elo_pieces/pieces` | Elo-pieces frame → model frame |
| `tour`, `surface`, `level`, `indoor`, `best_of`, `round` | Stage 0 and the indoor rule | thinking frame |

The frames between them copy values (float32 → float64 where the source stores float32), take differences A − B, and
form the products `O_A·(−D_B) − O_B·(−D_A)`.

## Each step

| Step | Min (alone) | Reaches | Live mode |
|---|---:|---|---|
| `stage0` (with the live rows) | 2.3 | everything (the history, the context inputs) | keep: rebuilt from the day's dump; about 75% of it is per-row Python (vectorise, byte-equal) |
| `additions`, `inject` (check, odds, remap, links, pin), `additions_window` | about 0.8 | the price, the timeline | keep |
| `stage0_checks` | 0.3 | none (reports) | skip |
| `lle_layer` (resolve) | 0.2 | the layer (strength for the forms and `points_52w`) | keep |
| `stage1_odds` | 0.1 | `odds_logit`; tennis-data days for the timeline | keep |
| `link_sources_c` | 0.4 | the timeline | keep (a global crosswalk) |
| `timing` | 0.8 | the timeline: the 21 IOS inputs, `surf_layoff` | keep (pooled statistics) |
| `timing_check` | 3.1 | none (reports) | skip |
| `timing_features` (`match_timing/rebuild.py`) | 8.0 | none (only checks read it) | skip; also recomputes the 17 forms for nothing |
| `stage1_baselines` | 19.1 | none through its tables (its constants only) | skip, or one final pass with pinned constants if a reader needs the table |
| `stage3_ratings` | 2.2 | `ratings_iid` | pinned constants; one pass per tour (7–15 s); later resume from state |
| `stage4_features` | 9.4 | 5 inputs, the pool | the needed columns only, no probe; later state |
| `ufc_stageA_ratings`, `stageA_features` | 14.3 | none | skip |
| `ufc_stageC_fatigue`, `stageC_sos`, `stageC_rundown` | 4.5 | none | skip |
| `ufc_stageB_adjperf` | 17.6 | 17 inputs | no tuning (the layer's pin discards it), no probe, the 17 pairs only: about 5 min (estimate); later state: seconds |
| `ufc_stageB_ios` | 7.3 | none (superseded) | skip (several asserts expect its file) |
| `ios_constants_check` | 0.0 | none | skip |
| `ufc_stageB_split` | 2.0 | none | skip |
| `ufc_stageB_rundown` | 7.2 | copies 17 inputs | frame only (its frame is written in about 8 s) |
| `ufc_stageD_profile` | 3.8 | copies 16 | frame only |
| `ufc_stageD_rundown` | 0.9 | copies 7 | frame only |
| `thinking_frame` | 0.2 | assembles 30 | live rows only |
| `leakproof_frame` | 0.0 | none | skip |
| `elo_pieces` | 7.0 | 6 inputs | pinned constants, one pass per tour (about 3 s); later state |
| `elo_frames` | 0.2 | copies 36 | live rows only |
| `surface_ios_cache` | 1.2 | the 21 IOS inputs | keep; later rows after the checkpoint |
| `surface_ios_features` | 15.4 | the 21 IOS inputs | the 14 needed runs only (42% of its CPU saved; about 5 min wall); later checkpoint and resume: seconds |
| `surface_ios_frames` | 0.0 | none | skip |
| `surface_ios_arms` | 0.1 | the 21 formulas | `sprof` only, live rows |
| `model_frame` | 0.0 | assembles the 57 | live rows only |

Critical path today about 112 min. Sum of what reaches an input, as estimated by the subagents: preparation about
4.3 min with the skips alone; Stage 3/4 and the Elo pieces about 1–2 min; Stage B about 5 min; the surface IOS about
5 min wall, beside them.

## What exactness needs

* **The tuning grids' winners are constants** while Stage 0's rows up to 2018 are unchanged: identical in every build
  since 8 Oct (Stage 1, Stage 3, the offset Elo; Stage B pinned under the layer). A live mode pins them and checks that
  slice's hash.
* **float32 storage** (Stage 3, Stage 4, Stage B) turns any last-bit difference into about 6e-8: the original summation
  order must be kept.
* **Joint solves** (surface IOS) depend on the warm-start chain and the player order: bit-equal only with the same
  history and signature; a cold one-day solve agrees only to the solver tolerance (1e-8), looser than `replay.py`'s
  1e-9 (to be measured).
* **Past rows move every day** (Tennis My Life revisions, restaged sources, events in progress, the live rows' own day
  links in the timeline's pooled statistics). A state saved at a cut date is valid only while the rows before it are
  unchanged.
* **The layer config** (a seasonal refit) and the 2010–2018 tables invalidate every state.

## Found on the way

* **The calendar cliff** (**re-checked**): `EVAL_YEARS = range(2013, 2027)` caps the pool at 2026
  (`predictability_diagnostic/common.py`, `stage4_features.pool_mask`), and `tabpfn_thinking/common.py`
  `TEST_YEARS = (2022, 2026)` sets the split. From 1 Jan 2027 no match gets inputs, in a full build or a live run.
* `match_timing/rebuild.py`'s per-player part recomputes the 17 forms (704 s on 9 Oct) that no reader takes.
* `model_frame.py` reads `ttt_timed.parquet`, which prediction runs do not rebuild (not an input).
* The surface-IOS `full_runs` reuse is checked by constants, not data: safe only because sandboxes exclude the folder.
* The library's cached mode (`fit_mode="fit_with_cache"`) prices in about 1 s but differs from the decided path by up to
  0.18 in probability (`bet_time_pricing.json`): unexplained.
