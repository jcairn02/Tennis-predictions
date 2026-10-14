# Serve-speed acquisition: evidence

Evidence for [docs/studies/serve_speed_acquisition/](../../../docs/studies/serve_speed_acquisition/README.md) (7 October 2026). It covers two acquisitions under the [owner's decision of that day](../../../docs/decisions/2026-10-07-serve-speed-acquisition.md):
* ManTennisData, downloaded;
* the Australian Open's and Roland-Garros's Infosys match-centre files of AO 2025, RG 2025 and RG 2026, fetched and decrypted.

On 8 October a third was added: the ATP Stats Centre's own Infosys files of 2015 to October 2021, fetched and **not decrypted**, on the owner's instruction (the study's section 8).

This is data collection, not a selection.

## Files

| File | What it is | Made by |
|---|---|---|
| [mantennisdata_summary.json](mantennisdata_summary.json) | ManTennisData's last run: commit, files planned and how each arrived, rows staged, and each season's rows with both players' first-serve average | `src/ingest/public_dump/mantennisdata.py` |
| [infosys_slams_summary.json](infosys_slams_summary.json), [runs.jsonl](runs.jsonl) | The Infosys adapter's last run, and one line per run: requests, every answer by edition and route, families given up, decryption failures, rows staged, and per edition and family the codes asked, the files, and the matches with points and with timed points | `src/ingest/point_sources/infosys_slams.py` |
| [infosys_atp_summary.json](infosys_atp_summary.json) | The ATP files' last run (or inventory): requests, every answer by season and route, events by outcome, families given up, files held and bytes. Nothing in it comes from decryption | `src/ingest/point_sources/infosys_atp.py` |
| `infosys_atp_decryption/` (`summary.json`, `files.csv`) | The ATP files' decryption of 8 Oct 2026 (the owner's later instruction): every file opened, content checks, receipts and hashes, originals unchanged | `src/ingest/point_sources/infosys_atp_decrypt.py` |
| [infosys_atp_stage_summary.json](infosys_atp_stage_summary.json) | The staging of the decrypted ATP files: rows per table, matches with points, timed points and key-statistic speeds by season | `src/ingest/point_sources/infosys_atp_stage.py` |
| [infosys_atp_events.csv](infosys_atp_events.csv) | One row per planned event of 2015 to 17 Oct 2021: codes, rows without a code, outcome (files, empty, no codes), and files and absences per route | `infosys_atp.py` |
| [infosys_atp_files.csv](infosys_atp_files.csv) | One row per ATP file held: event, match code, route, bytes, SHA-256, and the envelope's plain `lastModified` and ciphertext length | `infosys_atp.py` |
| [checks.json](checks.json) | The five agreement checks (see the study, section 4) | `src/eda/serve_speed_acquisition/speeds.py` |
| [links.json](links.json) | Per source, event and year: the source matches, how many link to Stage 0 and are oriented, and the timed player-matches | `speeds.py` |
| [coverage_matches.csv](coverage_matches.csv) | Match level, by tour × group × year: matches with both players timed under each scenario | `src/eda/serve_speed_acquisition/coverage_after.py` |
| [coverage_feature.csv](coverage_feature.csv), [coverage_feature_by_year.csv](coverage_feature_by_year.csv) | The serve-speed-change feature on the main-tour main draws, by scenario | `coverage_after.py` |
| [coverage_summary.json](coverage_summary.json) | The men's and women's 2025–26 counts and power, and the Polymarket window | `coverage_after.py` |

## Raw data and staged tables (gitignored)

* `data/raw/public_dump/mantennisdata/` (32 MB): the repository's files at their own paths (`atp/matches_2021.csv` … `matches_2026.csv`, `tournaments.csv`, `players.csv`, `README.md`, `LICENSE`), `_tree_4e2d39f99e40.json` and `_receipts.jsonl`. Every file is checked against the tree's git blob hash.
* `data/dump/matches/mantennisdata/`: each CSV as string Parquet with provenance (78,453 match rows for 2021–26).
* `data/raw/point_sources/infosys_slams/<slam>/<year>/<route>/<MID>.json.gz` (175 MB, 1,891 files): every file as served, still encrypted, with `_receipts.jsonl`. **The only copy:** the hosts serve past editions only while they keep them.
* `data/raw/point_sources/infosys_atp/<season>/<event>/<route>/<MID>.json.gz` (177 MB, 4,906 files, four of them calibration files from 2022 and 2025): the ATP's files as served, still encrypted, with `_receipts.jsonl` (9,162 receipts). **The only copy:** the host rewrites its files. Decrypted on 8 Oct 2026 into `data/dump/points/infosys_atp/decrypted/` (plain JSON, every field) and staged into `data/dump/points/infosys_atp/{matches,points,keystats,rally,court_vision}.parquet` ([backfill study](../../../docs/studies/infosys_atp_backfill/README.md)).
* `data/dump/points/infosys_slams/` (22 MB):
  * `blocks.parquet`: 4,104 blocks decrypted, as JSON text;
  * `matches.parquet`: 1,434 match codes;
  * `points.parquet`: 235,725 points;
  * `keystats.parquet`: 67,391 statistics;
  * `rally.parquet`: 57,483 entries.
  No file is over 50 MB.
* `data/studies/serve_speed_acquisition/speeds.parquet`: one row per player and source match (2,834 Slam, 20,412 ManTennisData and, since 8 Oct, 4,140 ATP-file rows of which 368 are timed), linked to Stage 0 (`speeds.py`).

## Reruns

```
./python.sh -m src.ingest.public_dump.mantennisdata                    # skips what is held at the pinned commit
./python.sh -m src.ingest.public_dump.mantennisdata --commit latest    # the weekly refresh; replaced files kept under superseded/
./python.sh -m src.ingest.point_sources.infosys_slams                  # asks only for what is not held (nothing now)
./python.sh -m src.ingest.point_sources.infosys_slams --stage-only     # decrypt the raw files and rebuild the tables
./python.sh -m src.ingest.point_sources.infosys_atp                    # the ATP's 2015-21 files; asks only for what is not held
./python.sh -m src.ingest.point_sources.infosys_atp --inventory-only   # no request; rewrite the three infosys_atp files
./python.sh -m src.ingest.point_sources.infosys_atp_decrypt            # decrypt the ATP files offline (8 Oct, the owner's instruction)
./python.sh -m src.ingest.point_sources.infosys_atp_stage              # stage the decrypted ATP files
./python.sh src/eda/serve_speed_acquisition/speeds.py                  # per-player speeds, links and checks
./python.sh src/eda/serve_speed_acquisition/coverage_after.py          # the feature's coverage
./python.sh -m pytest test/serve_speed_acquisition -q
```
