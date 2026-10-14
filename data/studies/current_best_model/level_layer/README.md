# The level layer's official config (the current best model, men)

**What it is.** The config with which the current best model's chain builds its inputs, since the owner's decision of
10 October 2026 ([decision](../../../../docs/decisions/2026-10-10-level-evidence-layer.md)). For men, every
lower-level observation (tour and Slam qualifying, Challenger main draw and qualifying) enters the inputs in main-tour
terms: translated by the opponent's strength gap and a level offset, and weighted by an exchange rate. ITF and ITF
qualifying box scores are left out until the P7 test; women are untouched.

| File | What |
|---|---|
| `official.json` (sha256 in `official.sha256`) | The config: the level-evidence study's tested SYS config, every setting as tested, and the changes listed in its `changed_from_sys` |
| `write_official.py` | Writes `official.json` from SYS.json once; refuses to change an existing one |
| `this_build/` (inside a build's sandbox only) | What `src/eda/current_best_model/layer_config.py --resolve` writes for each build: the opponent strength on that build's Stage 0, its check against the frozen strength, and the resolved config every step reads as `LLE_LAYER` |

**The tables it names** (hash-checked by the layer at every read):

| Table | sha256 | Owner |
|---|---|---|
| `data/studies/lower_level_evidence/system/relationship/params.parquet` | `4c559abd…` | role B (method F4, seasons 2013–2026) |
| `data/studies/lower_level_evidence/system/classes/classes.csv` | `58e78622…` | role A |
| `data/studies/lower_level_evidence/system/classes/strength_elo.parquet` | `4fa9a573…` | role A (the frozen strength; each build's own must equal it on the reference's matches) |
| `data/studies/lower_level_evidence/system/arms/constants/stageB_adj_summary_reference.json` | `43429744…` | Stage B's tuned constants, pinned |

**How a build uses it.**
```
./python.sh src/eda/model_rebuild/run_chain.py --setup
./python.sh src/eda/model_rebuild/run_chain.py --prepare-layer --out <folder>
./python.sh src/eda/model_rebuild/run_chain.py --lane 1 --layer --out <folder>     # beside lane 2
./python.sh src/eda/model_rebuild/run_chain.py --lane 2 --layer --out <folder>
./python.sh src/eda/model_rebuild/run_chain.py --lane 3 --layer --out <folder>
./python.sh src/eda/model_rebuild/run_chain.py --collect --out <folder>
```
Without `--layer` (and with `LLE_LAYER` unset) the same builders build the template without the layer.

**Keeping it current** (the decision's maintenance rules).
* **Each season,** at the first build after it ends: refit B's parameters walk-forward with
  `src/eda/lower_level_evidence/relationship.py --method F4` into a new folder (`--freeze` writes there and never
  over the study's record), write a new official config with the new path and hash (a new decision), and re-run the
  identity and strength checks. Until then, a season after the last fitted one reads the last fitted season's
  parameters (`params_season_ceiling: "last_fitted"`).
* **Classes:** A's frozen thresholds; re-checked yearly with `classify.py`.
* **New lower-level data:** `docs/studies/lower_level_evidence/system/P7_plan.md`.
