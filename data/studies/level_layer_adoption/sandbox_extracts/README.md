# The two 10 Oct builds' files that code still reads

`C:/Users/zerom/tnr_lyr_off` and `C:/Users/zerom/tnr_lyr_on` were this study's two full builds of 10 Oct 2026: the
template with the level layer off (B_off) and on (B_on, the instance in
`data/studies/current_best_model/level_layer_2026-10-10/`). They took 47 GB and were deleted on 14 Oct 2026 at the
owner's word ([cleanup inventory](../../../../docs/studies/cleanup_inventory/README.md), process log § 7).

Before the deletion, every file that code reads from them was copied here, byte for byte, in each build's own folder
layout. The code now reads the copies.

| Reader | What it reads here |
|---|---|
| `src/eda/level_layer_adoption/verify.py --gates` | G5's leak-probe summaries from `tnr_lyr_on/` (5 JSONs); the constants check's `stage3_ratings_summary.json` and `stageB_adj_summary.json` from both |
| `src/eda/level_layer_adoption/solver_tolerance.py` | `tnr_lyr_on/`: the men's lane-2 cache (`surface_ios/cache/atp.npz`) and the build config, with the strength table it names |

* **`tnr_lyr_on/…/this_build/build_config.json` is relocated, not the original.** Two fields differ from
  `build_config.original.json` (kept byte for byte, with its `.sha256`):
  * `strength.path` points at the copy of `strength_elo.parquet` here (same SHA-256, which the config pins);
  * `record_dir` is null. The layer's hooks append to that folder and create it, so the original value would
    re-create the deleted sandbox on a re-run. No computed value depends on it.
  * The config's `relocated` field records both changes.
* **Proved equal before the deletion:** `verify.py --gates` and `solver_tolerance.py`'s ON solve gave the same
  output, byte for byte, from the sandboxes and from these copies. They were run again after the code change and
  again once the sandboxes were gone (`data/studies/cleanup_inventory/lyr_2026-10-14.json`).
* **Not kept, and why:**
  * The rest of each build (Stage 0, the frames, every other study output): the frames are stored in `template_off/`
    and `current_best_model/level_layer_2026-10-10/`.
  * The match-timing leak probe re-run inside B_on (`docs/studies/level_layer_adoption/process_log.md`, reproduction
    list) needs a whole build. Its output stays in `checks/probe_match_timing_ON.json`. Repeating it now means
    rebuilding with `build_template.sh`, on today's tables.
* **Another reader, unchanged:** `src/eda/unpriced_leads/rebuild_pool.py` reads B_off's `stageB_adj.parquet` through
  its own frozen extract (`unpriced_leads/candidates/pool_rebuilt/inputs/layer_off_stageB_z.parquet`). Its record
  matched on 14 Oct, so it no longer needs the sandbox.
* `manifest.json`: every file, its source path, size and SHA-256.
