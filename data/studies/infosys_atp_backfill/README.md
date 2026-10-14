# The ATP Stats Centre backfill: evidence

Evidence for [docs/studies/infosys_atp_backfill/](../../../docs/studies/infosys_atp_backfill/README.md) (8 October 2026): the ATP's own Infosys files of 2018 to 17 Oct 2021, decrypted, checked, integrated and scored. Parquet files are gitignored and rebuilt by the scripts.

**Holdout warning.** `comparison_through_2026.*` and `compare_through_2026.log` contain results of 2025 and 2026 (to 28 Jul 2026): the exposed part of the [proposed clean holdout](../../../docs/studies/clean_holdout_rebuild/README.md). Keep them out of any clean-room material. Every other file reads results through 2024 at most, or none.

## Files

| File | What it is | Made by (`src/eda/infosys_atp_backfill/` unless stated) |
|---|---|---|
| `checks.json`, `check_mismatches.csv` | Checks A–H of the decrypted files against ManTennisData, the Hugging Face copy, Stage 0 and each other; every disagreeing value | `checks.py` (reads results on purpose: winners and box scores) |
| `history.json`, `history.log` | The live speed history with the backfill: reproduction check, rows added and changed, by year and event | `history.py` |
| `speed_columns_augmented.parquet`, `columns.json`, `columns.log` | The adjustment's columns (`spd_T_*`, `spd_L_*`, late flags, modes) on that history, for the 63,737 frame matches; how many moved, by season | `columns.py` |
| `coverage.json` | The share of men's frame matches whose players have a speed reading in the 28 days before, both histories, by season | `coverage.py` |
| `live_check.json` | The live panel and the 28-day form of 8 Oct 2026, built on both histories: no player's form moves | `live_check.py` |
| `vs_reference_2026-10-08/` | **The official comparison** with the frozen reference, both stages, 2020–2024 (inputs, scores, summary) | `src/eda/current_best_model/compare.py --candidate reference --speed speed_columns_augmented.parquet` |
| `comparison.json`, `comparison.csv`, `compare.log` | Both stages on each history, 2019–2024: gains, the coefficient path to 2025, the information test by season, heterogeneity across seasons and the next season's projection | `compare.py` |
| `comparison_through_2026.json`, `.csv`, `compare_through_2026.log` | The same through 28 Jul 2026 (**H-exposed**): coefficients to 2027 | `compare.py --through 2026` |
| `speeds_rerun.log` | The rerun of `serve_speed_acquisition/speeds.py` with the new source | `src/eda/serve_speed_acquisition/speeds.py` |
| `replaced/serve_speed_acquisition/` | `speeds.parquet`, `checks.json` and `links.json` as they were before that rerun (7 Oct 2026) | copied before the rerun |
| `speed_panel_augmented.parquet` | **Duplicate:** byte-identical to `serve_speed_tabpfn/live/speed_panel_backfilled.parquet`, written by the first run of `history.py` before the history moved to the live folder. Can be removed with the owner's OK | `history.py` (first run) |

## Outside this folder

| What | Where |
|---|---|
| The staged tables | `data/dump/points/infosys_atp/{matches,points,keystats,rally,court_vision}.parquet` (`src/ingest/point_sources/infosys_atp_stage.py`; summary `data/studies/serve_speed_acquisition/infosys_atp_stage_summary.json`) |
| The decrypted JSON and its audit | `data/dump/points/infosys_atp/decrypted/`; `data/studies/serve_speed_acquisition/infosys_atp_decryption/` |
| The per-player speed table | `data/studies/serve_speed_acquisition/speeds.parquet` (source `infosys_atp`), `links.json`, `checks.json` |
| The live speed history the model now reads | `data/studies/serve_speed_tabpfn/live/speed_panel_backfilled.parquet` + `.json`: its record holds the SHA-256 of the corrected copy it extends and of itself |

## Reruns

The order matters: each step reads the one before.

```
./python.sh -m src.ingest.point_sources.infosys_atp_stage
./python.sh src/eda/serve_speed_acquisition/speeds.py
./python.sh src/eda/infosys_atp_backfill/checks.py
./python.sh src/eda/infosys_atp_backfill/history.py
./python.sh src/eda/infosys_atp_backfill/columns.py
./python.sh src/eda/infosys_atp_backfill/coverage.py
./python.sh src/eda/infosys_atp_backfill/live_check.py
./python.sh src/eda/current_best_model/compare.py --candidate reference --speed data/studies/infosys_atp_backfill/speed_columns_augmented.parquet --out data/studies/infosys_atp_backfill/vs_reference_2026-10-08
./python.sh src/eda/infosys_atp_backfill/compare.py
./python.sh src/eda/infosys_atp_backfill/compare.py --through 2026      # reads 2025-2026 (H-exposed)
```
