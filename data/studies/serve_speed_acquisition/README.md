# Serve-speed acquisition: evidence

Evidence for [docs/studies/serve_speed_acquisition/](../../../docs/studies/serve_speed_acquisition/README.md) (7 October 2026). It covers two acquisitions under the [owner's decision of that day](../../../docs/decisions/2026-10-07-serve-speed-acquisition.md):
* ManTennisData, downloaded;
* the Australian Open's and Roland-Garros's Infosys match-centre files of AO 2025, RG 2025 and RG 2026, fetched and decrypted.

This is data collection, not a selection.

## Files

| File | What it is | Made by |
|---|---|---|
| [mantennisdata_summary.json](mantennisdata_summary.json) | ManTennisData's last run: commit, files planned and how each arrived, rows staged, and each season's rows with both players' first-serve average | `src/ingest/public_dump/mantennisdata.py` |
| [infosys_slams_summary.json](infosys_slams_summary.json), [runs.jsonl](runs.jsonl) | The Infosys adapter's last run, and one line per run: requests, every answer by edition and route, families given up, decryption failures, rows staged, and per edition and family the codes asked, the files, and the matches with points and with timed points | `src/ingest/point_sources/infosys_slams.py` |
| [checks.json](checks.json) | The five agreement checks (see the study, section 4) | `src/eda/serve_speed_acquisition/speeds.py` |
| [links.json](links.json) | Per source, event and year: the source matches, how many link to Stage 0 and are oriented, and the timed player-matches | `speeds.py` |
| [coverage_matches.csv](coverage_matches.csv) | Match level, by tour × group × year: matches with both players timed under each scenario | `src/eda/serve_speed_acquisition/coverage_after.py` |
| [coverage_feature.csv](coverage_feature.csv), [coverage_feature_by_year.csv](coverage_feature_by_year.csv) | The serve-speed-change feature on the main-tour main draws, by scenario | `coverage_after.py` |
| [coverage_summary.json](coverage_summary.json) | The men's and women's 2025–26 counts and power, and the Polymarket window | `coverage_after.py` |

## Raw data and staged tables (gitignored)

* `data/raw/public_dump/mantennisdata/` (32 MB): the repository's files at their own paths (`atp/matches_2021.csv` … `matches_2026.csv`, `tournaments.csv`, `players.csv`, `README.md`, `LICENSE`), `_tree_4e2d39f99e40.json` and `_receipts.jsonl`. Every file is checked against the tree's git blob hash.
* `data/dump/matches/mantennisdata/`: each CSV as string Parquet with provenance (78,453 match rows for 2021–26).
* `data/raw/point_sources/infosys_slams/<slam>/<year>/<route>/<MID>.json.gz` (175 MB, 1,891 files): every file as served, still encrypted, with `_receipts.jsonl`. **The only copy:** the hosts serve past editions only while they keep them.
* `data/dump/points/infosys_slams/` (22 MB):
  * `blocks.parquet`: 4,104 blocks decrypted, as JSON text;
  * `matches.parquet`: 1,434 match codes;
  * `points.parquet`: 235,725 points;
  * `keystats.parquet`: 67,391 statistics;
  * `rally.parquet`: 57,483 entries.
  No file is over 50 MB.
* `data/studies/serve_speed_acquisition/speeds.parquet`: one row per player and source match (2,834 Slam and 20,412 ManTennisData rows), linked to Stage 0 (`speeds.py`).

## Reruns

```
./python.sh -m src.ingest.public_dump.mantennisdata                    # skips what is held at the pinned commit
./python.sh -m src.ingest.public_dump.mantennisdata --commit latest    # the weekly refresh; replaced files kept under superseded/
./python.sh -m src.ingest.point_sources.infosys_slams                  # asks only for what is not held (nothing now)
./python.sh -m src.ingest.point_sources.infosys_slams --stage-only     # decrypt the raw files and rebuild the tables
./python.sh src/eda/serve_speed_acquisition/speeds.py                  # per-player speeds, links and checks
./python.sh src/eda/serve_speed_acquisition/coverage_after.py          # the feature's coverage
./python.sh -m pytest test/serve_speed_acquisition -q
```
