# Hugging Face ATP pipeline dump: download record

This folder is the tracked record of downloading the Hugging Face dataset [`atlas-polybot/atp-pipeline-handoff`](https://huggingface.co/datasets/atlas-polybot/atp-pipeline-handoff), under the owner's [decision of 25 September 2026](../../../docs/decisions/2026-09-25-atp-pipeline-handoff.md). The files themselves are in `data/raw/public_dump/atp_pipeline_handoff/` (gitignored). The comparison with our data that led to the download is in the [study write-up](../../../docs/studies/atp_pipeline_handoff/README.md).

**Where things stand:** the download is complete. All 5,707 planned files (150.53 GB) were downloaded on 25 September 2026, 14:24–15:23 UTC, and every one matched its hash. They take 16.79 GB on disk. [status.md](status.md) shows the state by chunk and by source folder.

**Backup:** a zip of the whole raw folder is in cold storage at `gs://tennis-predictions-archive/public_dump/tennis_atp_pipeline_handoff_raw_2026-09-25.zip`: Coldline, uploaded 25 Sep 2026, 16.7 GB, SHA-256 `bc7d1b49977d4c58f3f3cfe5f49f0f166370d64e2077e3b6593e7b9eb30e6c9f`. Restoring it is described in [LARGE_FILES.md](../../LARGE_FILES.md#5-the-hugging-face-atp-pipeline-dump) and in `README.txt` beside the zip. It is rewritten every minute while a download runs and at the end of each run. [runs.jsonl](runs.jsonl) has one line per run.

## The source

* **Where from.** A public Hugging Face dataset by `atlas-polybot`, created 1 June 2026 and last changed 19 June 2026. It holds the raw inputs of another team's ATP data pipeline: their scrapers' outputs for men's tennis, 1990–2024, with some 2025–26.
  * It has no licence and no dataset card.
  * Its own notes are `RAW_DATA_SOURCES.md`, downloaded to `_repo_root/`. They are wrong in places: Tennis Abstract's `match_date` is the tournament start date, and the `itf_*` folders hold Davis Cup only.
* **Version.** Pinned to commit `ea3d94d79f5d9e9b4bead031e2c6262f91a86c35`, the dataset's last change. That version has 5,764 files and 151.6 GB.
* **What each folder is.**

| Folder in the dataset (`data/tennis/`) | What it is | Chunk |
|---|---|---:|
| `infosys_deep/` | ATP Infosys Stats Centre files: point-by-point rally analysis, per-set key statistics, stroke summaries and season-to-date stats for about 37,300 tour, Challenger and qualifying matches, 2021–24 | 1 |
| `court_vision/` | Hawk-Eye Court Vision ball tracking, one file per match: 4,570 tour-level matches (2018 and 2021–24) | 1 |
| `atp_scraped_enriched/` | ATP-site results with per-set statistics, return statistics and rating, both players' season-to-date stats, prize money and draw sizes (main tour 1991–2024; qualifying and Challenger 2009–24) | 1 |
| `mcp/charts/` | Tennis Abstract chart pages, men only: stat tables and the full point log for 8,914 charts, 1959–2024 | 1 |
| `api_tennis/` | api-tennis.com fixtures: exact date, start time and status for men's ATP, Challenger and ITF matches, 2021–24 | 1 |
| `tennis_abstract/` | Tennis Abstract player pages: every match per player with rank, opponent details and serve stats, plus player bios | 1 |
| `atp_player_scrape/`, `atp_scraped/`, `itf_full/`, `itf_scraped/` | ATP profiles (height, weight, backhand, turned pro); basic ATP-site results; ITF Davis Cup rows | 1 |
| `tennis_atp/` | Jeff Sackmann's ATP files, 1968–2024. Only files we don't hold are downloaded (pre-2010 and `atp_players.csv`) | 1 |
| `flashscore_daily/`, `flashscore_data/`, `flashscore_bruteforce/`, and the `flashscore_full/` progress files | Small Flashscore side scrapes and progress records | 1 |
| `infosys_full/` | The Infosys files again, with Court Vision embedded in each match | 2 |
| `flashscore_gql_stats/` | Flashscore match statistics including winners, unforced errors and net points (ATP 1990–2025, Challenger 2011–25) | 3 |
| `flashscore_full/` year files from 2010 | Flashscore match pages: real start and end times, set durations, per-set stats, umpire and head-to-head feeds (ATP 2010–2024 with early 2025, Challenger 2010–11) | 4 |
| `flashscore_full/` year files before 2010 | The same for 1990–2009 (with Challenger 2008–09) | 5 |
| `flashscore_full/` head-to-head passes | Matches found by crawling head-to-head links, including WTA, ITF and juniors | 6 |

## How it is segmented

Every file is assigned to one chunk. Chunks run in order, most predictive first. Inside a chunk, files run by source priority and then the most recent year first.

| Chunk | Files | GB to download |
|---:|---:|---:|
| 1 | 5,552 | 6.25 |
| 2 | 7 | 7.01 |
| 3 | 46 | 11.22 |
| 4 | 21 | 24.84 |
| 5 | 23 | 18.51 |
| 6 | 58 | 82.69 |
| Total | 5,707 | 150.53 |

**Not downloaded** (57 files; the reason for each is in [plan.csv](plan.csv)):
* **56 `tennis_atp/` files:** identical to our `data/raw/public_dump/sackmann_archive/atp/` apart from their line endings, which the plan confirms file by file from the hashes.
* **`flashscore_full/flashscore_full_shard0.jsonl`:** the same bytes as `flashscore_full_2009_2009_challenger.jsonl`.

## Files here

| File | What it holds |
|---|---|
| [plan.csv](plan.csv) | One row per file in the dataset. Columns: chunk; rank (the order inside the chunk); source folder; path; size; how the Hub stores it and its hash; action (`fetch`, `skip-held`, `skip-duplicate`) with the reason; where it is stored under the raw folder; whether it is gzipped |
| [status.md](status.md), [status.json](status.json) | Done, part-way, failed and left, by chunk and by source folder |
| [runs.jsonl](runs.jsonl) | A `started` line when a run begins and an `ended` line when it finishes. The ended line gives what the run was asked for, files done or failed, GB received, requests, and why it stopped. A `started` line with no `ended` line means the run was interrupted (runs before 25 Sep 14:30 UTC wrote only the end line) |
| [checks.json](checks.json) | Checks on the downloaded chunk 1 by `src/eda/atp_pipeline_handoff/verify_chunk1.py`: record counts against the uploader's claims, Infosys point depth by year, and the join of Infosys matches to Tennis My Life |
| [checks_chunks_2_6.json](checks_chunks_2_6.json) | Checks on chunks 2–6 by `src/eda/atp_pipeline_handoff/verify_chunks_2_6.py`. Per Flashscore file: records against the uploader's claims, date range, categories, and the share with start times, statistics, and winners and unforced errors. Also distinct Flashscore matches by year, 2025–26 matches by tournament-name class, and how `infosys_full` and `infosys_deep` overlap |

## How a download works

* **Ranges.** Each file is streamed from the pinned commit in 256 MB byte ranges.
* **Compression.** Files over 1 MB are gzipped as they arrive, one gzip member per range. `gzip.open()` returns the original bytes. Files under 1 MB, and files already gzip (`court_vision/`), are stored as served.
* **Checks.** A file counts as done only when it matches the Hub's own hash: SHA-256 for large files, the git blob SHA-1 for small ones. Proof for each file is in `data/raw/public_dump/atp_pipeline_handoff/_receipts.jsonl`.
* **Resuming.** After each range, `_progress.jsonl` records how far a large file has got. An interrupted file resumes from its last complete range. A file that fails its hash is kept as `*.bad-<run>` and downloaded again.
* **Pace.** At most 5 requests a second to huggingface.co, 4 files at a time, no account.
* **Stops.** A run stops on HTTP 403, on a 404 (it means the dataset changed), or on three 429s in a row.

## Resume after an interruption

From the repository root, in Git Bash:

```
./python.sh -m src.ingest.public_dump.atp_pipeline_handoff status   # rewrite status.md from the receipts
./python.sh -m src.ingest.public_dump.atp_pipeline_handoff fetch    # continue: all chunks in order
```

* Rerunning is always safe. Finished files are skipped, part-way files continue, and failed files are retried.
* `--chunks 1 2` limits a run to chosen chunks. `--max-gb` and `--max-files` cap one run.
* `plan` rebuilds `plan.csv` from the pinned commit. It is only needed if this folder is lost.
* If a run stopped on a 404, the dataset has changed or been removed. Check its page before going on.

The raw folder's layout mirrors the dataset's `data/tennis/<source>/…` paths; its root files are in `_repo_root/`. The raw folder has its own short `README.md`.
