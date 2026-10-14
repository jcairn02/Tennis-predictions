# The IOS constants registry

**What it is.** One record of every constant the IOS inputs are built with, kept in versions, and a pointer to the version in use. A version is hashed and never edited. A change is a new version, and reverting it means activating the old one. The code is [`src/eda/ios_constants/registry.py`](../../../src/eda/ios_constants/registry.py).

**Why (8 Oct 2026).** The constants lived in two study outputs and a line of code:

| Constants | Where they were | What could change them |
|---|---|---|
| Stage B's half-life h, ridge κ and units weight τ, and the typical units | `data/studies/ufc_ideas/stageB_ios_summary.json` | Any run of `stageB_ios.py`, including lane 1 of the template's build chain while lane 2 read the file |
| The surface IOS's penalties | `data/studies/surface_ios/tuning_choice.json` | A run of `summarise_tuning.py` |
| The short memory: 4 weeks (men), 13 (women) | Hard-coded in `src/eda/match_timing/rebuild.py`, and again in `feature_alpha_audit/repair_features.py` | An edit |

* **The risk.** Re-running a tuning study could change the model's inputs without anyone deciding it, and no build recorded which constants it used.
* **On 8 Oct it did not bite, by timing.** The build chain re-tuned Stage B on the corrected tables at 14:11–14:20 (local time). It chose the same 16 settings, and the surface IOS had already read the old file at 13:07–13:25.

## Where everything is

* `versions/<id>.json`: one file per version.
* `active.json`: the version in use, its hash, and every activation with its reason.

Each version holds four blocks, keyed `tour|stat` over both tours and the eight statistics (spw and the profile's seven):

| Block | What it holds |
|---|---|
| `base` | Stage B's tuning on 2013–2018: h in weeks (`"inf"` = no decay), κ in typical matches, τ (0 or 1). The pooled and the surface IOS both use them |
| `typical_units` | The mean units of a box-score match, 2010–2018: the reference for the units weights |
| `short_memory_h` | Per tour, the half-life of the short-memory IOS points matchup (`ios_points_short`). It uses spw's κ and τ |
| `surface` | The surface IOS's variant (`shared`, `return_only` or `pooled`), the half-life multiplier, and the surface penalties as multiples of κ: kE on the serve side, kF on the return side (`"inf"` = no surface term) |

It also holds:
* `sources`: the file each block came from, with its SHA-256 at the time;
* the fingerprint of the surface averages the IOS is centred on;
* `sha256`: the hash of the four blocks. Every load recomputes it and refuses a mismatch. The pointer holds it too, so a version edited after its activation is refused even if its own hash was redone.

**The surface averages are recorded, not served.** They are Stage 3's, and every feature family shares them, so the builders still read them from `stage4_constants.csv`. `--check` reports if they change.

## The version in use: `2026-10-08_reference`

* **It is the constants the [frozen reference](../current_best_model/reference_2026-10-08/README.md) was built with,** checked three ways:
  1. Its two source files hash to the reference inventory's SHA-256.
  2. Its short memory is the `SHORT_H` line of the reference's frozen code.
  3. Every reader returns exactly what it returned before the registry: Stage B's 16 settings and typical units, the surface choice, and the 32 saved surface runs' constants. Types are kept, so τ stays an integer and infinity stays infinity.
* **A full rebuild of the leak-proof IOS from the registry** reproduces `match_timing/ios_features.parquet` exactly, on the same timeline.

## Using it

```
./python.sh src/eda/ios_constants/registry.py --show            # the constants in effect
./python.sh src/eda/ios_constants/registry.py --list            # every version; * marks the active one
./python.sh src/eda/ios_constants/registry.py --verify          # every hash and the pointer; exit 1 on a mismatch
./python.sh src/eda/ios_constants/registry.py --check           # what the tuning outputs on disk would change
./python.sh -m pytest test/ios_constants -q
```

**A new version** is the active one (or `--from ID`) with the blocks you give replaced. It is not activated.

```
./python.sh src/eda/ios_constants/registry.py --add <id> --note "<what and why>" \
    [--base-from data/studies/ufc_ideas/stageB_ios_summary.json] \
    [--surface-from data/studies/surface_ios/tuning_choice.json] \
    [--short-h atp=4 wta=13]
./python.sh src/eda/ios_constants/registry.py --activate <id> --reason "<why>"
```

**Reverting** is `--activate <earlier id> --reason "..."`. The history in `active.json` keeps both moves.

## Who reads it

* **`match_timing/rebuild.py`**: the leak-proof IOS profile and the short-memory points matchup. It records the version in `ios_features_summary.json`, and so in `leakproof_features_summary.json`.
* **The surface IOS**: `surface_ios/common.ios_constants` and `build_features.py`. It records the version in `build_features.json`.
* **Pinning.** Both builders pin the version at their start with `IOS_CONSTANTS_VERSION`, so every worker reads the same one whatever the pointer does meanwhile.
* **The build chain** runs `--check` in lane 1 right after Stage B's re-tune. Its log (`chain_logs/ios_constants_check.log`) says whether a re-tune on the day's tables would change anything. It never fails the lane.
* **Closed studies keep their own copies** as the record of what they ran: `ufc_ideas/stageB_rundown.py`, `feature_alpha_audit/repair_features.py` and `feature_interactions/features/f28_state.py`.

## Changing the current best model's constants

* **Activating another version changes the current best model's inputs.** Like any rebuild, it is tested as a candidate first and compared with the reference. Accepting it is the owner's call.
* **A candidate build tries a version without moving the live pointer.** Either set `IOS_CONSTANTS_VERSION=<id>` for the chain, or activate the version inside the sandbox's own copy of the registry.
* **Which lanes to run:**
  * A change to `base`, `typical_units` or `short_memory_h` moves the leak-proof IOS. Run lane 0's `timing_features` step (`--lane 0 --from timing_features`) before lanes 1–3.
  * A change to `surface` alone needs lanes 2 and 3.
