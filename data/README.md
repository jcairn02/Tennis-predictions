# Data

**Start with the [data map](data_map.html)**: open it in a browser. For every professional singles match since 2018 it shows how much detail `data/` holds, by tour, tournament level and year, from every shot of a rally down to just the result. It also shows where each dataset came from and how it was obtained, what is downloading now, what is missing, and, set against what is known to exist publicly but is not collected yet, how much more could be had. The page is built from **[data_map.yaml](data_map.yaml)**, the master list of every dataset in this folder: its level of detail, years, status, acquisition method, folders, the code that fetched it, its write-up, the decision behind it, its rights and its backups, plus the outside sources it is measured against. Per-source details belong there, not in this file.

Data is the current research priority. Measure coverage against actual markets, preserving unmatched events and ambiguous identities.

## How data moves through this folder

| Stage | Folder | What it holds | Made by | In git |
|---|---|---|---|---|
| 1. Raw | `raw/<group>/<source>/` | Every file exactly as downloaded, never edited, with `_receipts.jsonl` (URL, time, status, bytes, SHA-256). Where a refresh brings different bytes, tennis-data.co.uk and Tennis My Life keep the replaced file under `superseded/` | An adapter in `src/ingest/` | No |
| 2. Staged | `dump/<branch>/<source>/` | The raw files as tables: string-typed Parquet with provenance columns, in the branches `matches`, `players`, `rankings`, `points` and `odds` | The same adapter (`--stage-only` rebuilds from raw) | No |
| 3. Evidence | `studies/<study>/` | Manifests, run summaries, coverage tables and check results; the write-ups are in `docs/studies/`. Beside them, the studies' own outputs, which make up most of the size | `src/eda/<study>/` | The summaries; large outputs mostly not |
| 4. Merged | Not built | One cleaned database joining the sources, as proposed in the [structure plan](../docs/studies/public_data_dump/structure-plan.md) | | |
| 5. Bets | `betting_history/` | Reserved for actual bets and their settlement | | Yes |

The groups under `raw/`:

| Group | What | Fetched by |
|---|---|---|
| `raw/public_dump/` | Bulk downloads of public collections, described in [the public data dump report](../docs/studies/public_data_dump/README.md): Sackmann, Tennis My Life, the Match Charting Project, the Live Tennis API sample, Open Tennis Data, tennis-data.co.uk and Polymarket (with four days of tennis order books from the PMXT archive, for the [line-sharpening study](../docs/studies/line_sharpening/README.md): `pmxt_books`, receipts only). Also the [Hugging Face ATP pipeline dump](../docs/studies/atp_pipeline_handoff/README.md): Infosys point data, Court Vision tracking, Flashscore, api-tennis and Tennis Abstract chart pages; and the [SirGenkii/infotennis dumps](../docs/studies/gap_downloads/README.md): Infosys point data for January to April 2025; and the [Hawk-Eye Court Vision copy](../docs/studies/ao_rg_points/README.md) of the Australian Open and Roland Garros, 2019–2024 (`slam_ball_tracking`); and [ManTennisData](../docs/studies/serve_speed_acquisition/README.md), the ATP Stats Centre's match statistics with serve speeds from October 2021 (`mantennisdata`) | `src/ingest/public_dump/` |
| `raw/point_sources/` | Match-by-match collections of point feeds, reported in [official point feeds](../docs/studies/official_point_feeds/README.md) and [point- and shot-level sources](../docs/studies/point_shot_sources/README.md): Wimbledon, the US Open, the Australian Open, the WTA API, TDI, SofaScore and TennisLive, plus Wayback capture indexes; and SofaScore listed tournament by tournament for the map's gaps ([gap downloads](../docs/studies/gap_downloads/README.md), and the [Australian Open and Roland Garros gap](../docs/studies/ao_rg_points/README.md): `sofascore_tournaments`); and the Australian Open's and Roland-Garros's Infosys match-centre files of AO 2025, RG 2025 and RG 2026, kept as served and decrypted at staging ([serve-speed acquisition](../docs/studies/serve_speed_acquisition/README.md): `infosys_slams`); and the ATP Stats Centre's Infosys files of 2015 to October 2021, kept as served and **not decrypted**, on the owner's instruction (same study: `infosys_atp`) | `src/ingest/point_sources/` |
| `raw/point_shot_sources/` | Small research downloads: Sackmann's old point strings (2011 to January 2017) and the Tennis Abstract chart index | `src/eda/point_shot_sources/`, `src/eda/granular_data_leads/` |
| `raw/sackmann/`, `raw/tennis_data_couk/` | June 2026 snapshots from the inherited scaffold, superseded by the public dump and kept for a later diff; not an approved source selection | `src/ingest/download_*.py` |
| `raw/data_continuity/` | Tennis My Life files as republished after the project's copy, saved beside it to measure revisions ([data continuity](../docs/studies/data_continuity/README.md)) | `src/eda/data_continuity/tml_revisions.py` |
| `raw/_scheduled/` | Bookkeeping, not data: the run log, state and job output of the daily scheduled downloads ([download cadence](../docs/decisions/2026-10-06-download-cadence.md)). The downloads themselves land in their sources' folders | `src/ingest/scheduled.py` (Windows task "Tennis predictions - daily data downloads") |

## Adding or changing data

1. Fetch into `raw/<group>/<source>/` with receipts, stage to `dump/` if the data is tabular, and record the run under `studies/<study>/`.
2. Add an entry to [data_map.yaml](data_map.yaml), or change an entry's `status` when a download starts, finishes or is approved. The statuses are `on_disk`, `downloading` (a Claude Code session is running it now) and `assumed` (counted as held on the owner's instruction, not downloaded). Give it a `how` from the catalog's `methods`. When research measures a source that is not collected yet, add it to the catalog's `universe`, which sets out what exists outside `data/`.
3. Rebuild the map: `./python.sh src/eda/data_map/build.py` (about a minute; `--no-measure` only redraws the page). The build lists any folder under `raw/` or `dump/` that no entry claims, and any catalog link that points nowhere. The measured numbers go to `studies/data_map/`.
4. List every file over 50 MB in [LARGE_FILES.md](LARGE_FILES.md) and `.gitignore`. That file explains how to regenerate or re-download each one.

## Before using the data

* Sackmann's and Tennis My Life's `tourney_date` is the tournament's first day, not the day of the match. Other sources date matches by the day played or the scheduled time, so carry a date-precision flag.
* Result rows are winner first. Schedule changes, retirements, walkovers and source identities need explicit handling.
* Being on disk is not a selection. No dataset here is approved for modelling. Several were collected against their sites' terms, under the owner's decisions in [docs/decisions/](../docs/decisions/README.md), for non-commercial research. The map lists each dataset's rights.
* Several raw folders are the only copy of their data: the Slam feeds, the WTA API and the Hugging Face dump. The map's "Where it is" notes which ones need a backup outside the working tree. [preservation_register.csv](studies/data_continuity/preservation_register.csv) lists every raw folder with its size, receipts, catalog entry and any copy outside this PC (`./python.sh src/eda/data_continuity/inventory.py`).
* After Sackmann's end, Stage 0 takes results only from Tennis My Life. Its measured defects, the draws it does not publish and the official feeds that can check it are in the [data continuity study](../docs/studies/data_continuity/README.md).
* Tennis My Life is downloaded every day by a scheduled task. Stage 0 is rebuilt only on request, coordinated with the studies that read it, by `./python.sh src/eda/data_continuity/rebuild_stage0.py`. That command keeps the replaced tables, re-links the odds, carries changed match ids into the frozen link files, and refreshes the timeline and the features built on it.
* [Old data notes](../docs/research/legacy-one-shot/data/README.md), including odds-column and coverage claims, are archived. Use fresh source evidence and measured audits before relying on them.
