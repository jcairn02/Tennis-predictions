# Files over 50 MB: how to get them back

These files and folders are gitignored because they are over 50 MB, or hold files that are. GitHub warns above 50 MiB and rejects files above 100 MiB. A fresh clone does not have them. The rebuild and re-download results quoted below were tested on 23 September 2026 against the originals from 10 and 22 September 2026.

| File | Size | What it is | Way back | Exact copy? |
|---|---:|---|---|---|
| `data/studies/tennis_data_audit/polymarket/markets.jsonl.gz` | 116.6 MB | Polymarket tennis contract inventory: the census of 10 Sep 2026, 411,502 contract rows | A backup, or an offline rebuild from a backup of its page cache. Otherwise a live re-run makes a new snapshot | Only from a backup |
| `data/dump/odds/polymarket/market_index.parquet` | 106.5 MB | Staged index of 464,266 Polymarket contracts with an inferred tournament-type bucket | Offline rebuild, about 15 seconds | Same rows; a later rebuild updates some flags |
| `data/raw/public_dump/polymarket_prices/bodies/itf.jsonl.gz` | 72.2 MB | Raw minute price-history responses for 17,930 ITF moneylines | Re-download, about an hour together with the next file | No; the responses matched in a spot check |
| `data/raw/public_dump/polymarket_prices/bodies/challenger_125_inferred.jsonl.gz` | 50.5 MB | The same for 7,021 Challenger / WTA 125 moneylines | Same command as the ITF file | No; the responses matched in a spot check |
| `data/raw/public_dump/match_charting_project/charting-m-points-2020s.csv` | 56.6 MB | Match Charting Project men's shot-by-shot points, 2020s | Re-download from a pinned commit | Yes |
| `data/raw/public_dump/atp_pipeline_handoff/` (a folder; dozens of its files are over 50 MB even gzipped) | 16.8 GB (150.5 GB uncompressed) | The Hugging Face dataset `atlas-polybot/atp-pipeline-handoff`: Infosys, Court Vision, Flashscore, ATP-site and Tennis Abstract files ([section 5](#5-the-hugging-face-atp-pipeline-dump)) | Restore the zip in cold storage, or re-download from a pinned commit (1–2 hours) | Yes |
| `data/raw/public_dump/polymarket_trades/` (a folder; eight bucket files over 50 MB) | 1.91 GB | Raw Data API trade responses for 35,756 tennis moneylines, both parties of every fill, with receipts ([section 6](#6-polymarket-trade-fills)) | Re-download, about 55 minutes | No; settled markets' fills should match |
| `data/dump/odds/polymarket/trades/` (a folder; seven files over 50 MB) | 877 MB | The same fills staged to Parquet, 36,037,873 rows | Offline rebuild from the raw folder, about 10 minutes | Same rows |
| `data/studies/polymarket_sharp_money/wallet_markets.parquet`, `scored_positions.parquet`, `prematch_positions.parquet`, `prematch_positions_buffer30.parquet` | 1.34 GB, 1.07 GB, 123 MB, 103 MB | Sharp-money study tables: one row per account and market (all money, with tiers; and bets before the match, with closing-price groups) | Offline rebuild from the staged fills and price history, about 10 minutes | Same rows |
| `data/studies/predictability_diagnostic/stage0_match_players.parquet` | 62.3 MB | Predictability diagnostic, Stage 0: two rows per singles match, 2010 to September 2026 (players, box scores and rates) | Offline rebuild from the staged Sackmann and Tennis My Life files with `./python.sh src/eda/predictability_diagnostic/stage0_build.py`, about a minute | Same rows |
| `data/studies/predictability_diagnostic/stage1_baselines.parquet` | 74.6 MB | Predictability diagnostic, Stage 1: one row per singles match, every baseline's pre-match probability and each player's pre-match Elo ratings | Offline rebuild after Stage 0: `./python.sh src/eda/predictability_diagnostic/stage1_odds.py`, then `stage1_baselines.py`, about 5½ minutes | Same rows |
| `data/studies/predictability_diagnostic/stage4_features.parquet` | 197.0 MB | Predictability diagnostic, Stage 4: one row per evaluation-level match of 2010–2026 (completed or retired), every candidate's features (165 columns) beside the result and surface Elo's and the market's probabilities | Offline rebuild after Stages 0–3: `./python.sh src/eda/predictability_diagnostic/stage4_features.py`, about 9 minutes | Same rows; a rebuild on 1 Oct 2026 gave identical values |
| `data/studies/ufc_ideas/stageB_adj.parquet`, `stageB_adj_features.parquet`, `stageB_ios.parquet`, `stageB_split_features.parquet`, `stageB_features.parquet` | 84.3, 129.4, 95.6, 54.2 and 232.0 MB | UFC-ideas study, Stage B: the per-match adjperf/adjdef z per statistic; the adjperf/adjdef features per pool match; each player's pre-match IOS offence and defence per statistic for every match; the opponent-strength split features; the scored frame (the pool, the earlier study's re-scored columns, every Stage B feature) | Offline rebuild after the predictability diagnostic's Stages 0–4: `./python.sh src/eda/ufc_ideas/stageB_adjperf.py`, `stageB_ios.py`, `stageB_split.py`, `stageB_rundown.py` (about 23, 16, 6 and 9 minutes) | Same rows (deterministic; the frozen constants are in `stageB_summary.json`) |
| `data/studies/ufc_ideas/stageD_profile_features.parquet` | 110.5 MB | UFC-ideas study, Stage D: the pool with the individual-statistic adjperf / adjdef / IOS columns of Stage B and the seven matchup products, the inputs of the profile models | Offline rebuild after Stage B: `./python.sh src/eda/ufc_ideas/stageD_profile.py` (about 4 minutes) | Same rows |
| `data/studies/shot_level/stage2_frame.parquet`, `stage2_features.parquet` | 134.5 and 103.5 MB | Shot-level study, Stage 2: the scored frame (the Stage 4 pool, every shot-level feature, the Stage D box-score profile and the two walk-forward bases built from it); the pool with the shot-level features alone | Offline rebuild after Stage 0 and the predictability diagnostic's Stages 0–4 and the UFC-ideas Stage D: `./python.sh src/eda/shot_level/stage1_points.py`, `stage1_stats.py`, `stage2_features.py`, `stage2_rundown.py` (about 1½, ½, 6 and 4 minutes) | Same rows (deterministic) |
| `data/studies/shot_level/stage3_sides.parquet` | 193.2 MB | Shot-level study, Stage 3: per pool match, each player's own Stage 2 feature values (A and B), box-score serve and return form in the same memories, the serve-point counts and the ratings' serve forecasts | Offline rebuild after Stage 2 and the predictability diagnostic's Stage 3 ratings: `./python.sh src/eda/shot_level/stage3_sides.py` (a few minutes) | Same rows (deterministic) |
| `data/studies/rating_systems/stageA_ratings.parquet`, `stageB_features.parquet` | 132.1 and 99.3 MB | Rating-systems study: one row per singles match (872,704) with every system's pre-match probability and the main systems' ratings; the scored frame (the Stage 4 pool, the new ratings, the earlier leaders) | Offline rebuild after the predictability diagnostic's Stages 0–4 and the UFC-ideas Stage B: `./python.sh src/eda/rating_systems/stageA_ratings.py`, then `stageA_ttt_hold.py` and `stageB_compare.py` (the grids about an hour on 5 workers, `--reuse-grid` reads back `stageA_tuning.csv`; the rest about half an hour) | Same rows (deterministic; the frozen constants are in `stageA_summary.json`) |
| `data/studies/line_sharpening/prices.parquet`, `takers.parquet` | 101.7 and 179.1 MB | Line-sharpening study: the pre-match minute price path of every 2026 singles moneyline (42.3 million points) and its pre-match taker orders (2.1 million) | Offline rebuild from the staged price history and fills: `./python.sh src/eda/line_sharpening/build.py` (about 15 minutes) | Same rows (deterministic) |
| `data/studies/data_continuity/rebuilds/<stamp>/replaced/` (a folder; it holds copies of files over 50 MB) | 366 MB (the rebuild of 6 Oct 2026, `2026-10-07T0005Z`) | What a coordinated Stage 0 rebuild replaced, under the same relative paths with a SHA-256 manifest: Stage 0's tables and evidence, Stage 1's odds links, and the match-timing links, timeline, feature tables and TrueSkill table | None by rebuilding: Stage 0's code changed on 2 Oct 2026, so the tables of 30 Sep cannot be built again. Copy them back from here | Only from this copy, or a backup of it |
| `data/studies/point_sequence/sequences.parquet` | 94.0 MB | Point-sequence study: the unified point-by-point table, one row per point (19.17 million) for 130,751 Stage 0 matches from 13 sources, with the `usable` flag | Offline rebuild from the staged point sources and Stage 0: `./python.sh src/eda/point_sequence/build.py` (about 2 minutes; `--refresh all` re-reads every source) | Same rows (deterministic) |
| `data/studies/point_sequence/trait_player_matches_variants.parquet` | 61.6 MB | Point-sequence study: the momentum and streak statistics per player-match on the pure-luck replays, every variant | Offline rebuild after `build.py`: `./python.sh src/eda/point_sequence/trait_build.py` (fixed seeds) | Same rows (fixed seeds) |
| `data/studies/match_timing/leakproof_features.parquet` | 97.1 MB | Match-timing study: the Stage 4 pool (255,123 matches) with the 46 sporting inputs rebuilt on the leak-proof timeline (per-player inputs and daily-solved IOS) | Offline rebuild after the predictability diagnostic's Stages 0–4, the feature-alpha repair and the match-timing links: `./python.sh src/eda/match_timing/timing.py`, then `rebuild.py` (about 1 and 15 minutes; after a timeline change only `rebuild.py --part ios` and `--part merge` need rerunning) | Same rows (deterministic) |
| `data/studies/match_timing/undated_matches.csv` | 109.8 MB | Match-timing study: an older, uncompressed list of the undated matches, written 5 Oct 2026, with the first 12 columns of today's list (no `why`). Nothing in the code writes or reads it now | None by rebuilding: no script writes it any more. `./python.sh src/eda/match_timing/timing.py` writes the current list, `undated_matches.csv.gz` (4.2 MB) and `undated_matches.parquet` | Only from a backup |
| `data/studies/feature_interactions/round1/_panel_aug.parquet` | 112.5 MB | Feature-interactions study, round 1: the augmented 2014–2024 player panel of the feasibility audit (history quantities, venue, shot-level sides, the current best's forecast), read by the round-1 audit and round-2 checks | `./python.sh src/eda/feature_interactions/round1/feasibility/augment.py` writes it again, but not the same values: its history quantities have changed since 6 Oct (see the next row) | No |
| `data/studies/feature_interactions/round1/_history_feats_2010_2024.parquet` | 74.4 MB | Feature-interactions study, round 1: per-player history quantities of 2010–2024, the values the feasibility audit saw | None. No script writes or reads it. A rebuild with today's code on 8 Oct 2026 (`history_feats.build`) differs in 35 of its 37 columns, because the history table changed after 6 Oct | Only from a backup |
| `data/studies/feature_universe/store.parquet` | 317.5 MB | Feature-universe store: 63,737 model-frame matches × 776 candidate features: the 58 inputs, alternatives, per-player pairs, other rating systems, opponent-adjusted profiles, serve speed, market-internal, interaction and module columns, levels, known-null placebos and context. Described column by column in the tracked `store_registry.csv`; the selection pool is `menu.csv` | Offline rebuild after the feature-interactions study's inputs and the rating-systems, UFC-ideas and shot-level tables: `./python.sh src/eda/feature_universe/perplayer_2026.py`, then `build_store.py` (about 1 and 8 minutes) | Same rows (deterministic) |

Sizes are decimal megabytes. `challenger_125_inferred.jsonl.gz` is 48.1 MiB, under GitHub's warning threshold, but it is over 50 MB, so it is listed.

## Before you start

* Create the environment with `conda env create -f environment.yml` and run the commands below from the repository root in Git Bash.
* `./python.sh` calls the `tennis` environment at the owner's install path. On another machine, activate `tennis` and use `python` in place of `./python.sh`.
* The Polymarket files depend on each other, so restore them in this order. The Match Charting file is independent.

```
polymarket_census.py   -> markets.jsonl.gz, events.jsonl        snapshot of 10 Sep 2026
polymarket_catalog.py  -> catalog extension (optional)          events created after the census
polymarket_prices.py   -> market_index.parquet                  offline, from the two above
                       -> bodies/itf.jsonl.gz,                  live download
                          bodies/challenger_125_inferred.jsonl.gz
match_charting.py      -> charting-m-points-2020s.csv           independent
```

## 1. `markets.jsonl.gz`: the Polymarket census

[`polymarket_census.py`](../src/eda/tennis_data_audit/polymarket_census.py) took a snapshot of Polymarket's public Gamma API on 10 September 2026 (348 requests, 21:30 to 21:35 UTC). Polymarket keeps revising its records, so **that snapshot cannot be downloaded again**. There are three ways back, best first.

1. **Restore a backup** of `markets.jsonl.gz` and `events.jsonl` (45 MB, same folder, also ignored) into `data/studies/tennis_data_audit/polymarket/`. Check them against the [checksums](#checksums).
2. **Rebuild from a backup of the page cache**, `data/studies/tennis_data_audit/polymarket/raw/` (696 files, 181 MB, ignored). Put it back in place and run:
   ```
   ./python.sh src/eda/tennis_data_audit/polymarket_census.py
   ```
   With a complete cache this takes under a minute and makes no network requests; each cached page is checked against the URL and SHA-256 in its `.meta.json`. Tested on 23 Sep 2026, the decompressed content, `events.jsonl`, `summary.json` and `request-manifest.json` all came out identical. The `.gz` file's own SHA-256 changes, because gzip records when it was written.
3. **Re-run against the live API.** Without the cache, the same command fetches everything again, in about 5 minutes, with no account. The result is a new census, not the 10 September one:
   * It includes contracts added since then, and volumes, prices and closed flags are current.
   * The in-window flag still uses the window fixed in the script, 10 Sep 2025 to 11 Sep 2026. Later matches are flagged out of window, and the price download in section 3 skips them.
   * It rewrites the tracked `summary.json` and `request-manifest.json`, which describe the snapshot that [the census report](../docs/research/tennis-data-audit/polymarket-census.md) cites. Don't commit the rewritten versions unless you mean to replace that evidence. Pass `--out <folder>` to write the new census somewhere else instead.

## 2. `market_index.parquet`: the staged contract index

[`polymarket_prices.py`](../src/ingest/public_dump/polymarket_prices.py) builds this from local files only. It needs the census from section 1 and, if present, the catalog extension in `data/raw/public_dump/polymarket_catalog/` (`events_extension.jsonl` and `markets_extension.jsonl.gz`, both ignored). This rebuilds the event and market index tables without downloading anything:

```
./python.sh -m src.ingest.public_dump.polymarket_prices --no-fetch --no-rebuild
```

* Expect 464,266 rows: 411,502 from the census and 52,764 from the extension, as recorded in [manifest.json](studies/public_data_dump/manifest.json). Without the extension files you get the 411,502 census rows only.
* The rebuild is deterministic. Pinned to the original build time (22 Sep 2026, about 22:23 UTC), the rebuild on 23 Sep was byte-identical. A normal run uses the current time, so extension contracts whose sporting date has passed become in-window and receive a bucket. A day later 4,667 rows differed, and the number grows with time.
* If the extension files are missing, recreate them first with `./python.sh -m src.ingest.public_dump.polymarket_catalog`. That fetches every tennis event newer than the census up to the day you run it, not just to 22 September, so the index gains rows.
* The command appends a line to the tracked `data/studies/public_data_dump/polymarket_runs.jsonl`.

## 3. `itf.jsonl.gz` and `challenger_125_inferred.jsonl.gz`: raw price histories

These are raw responses from Polymarket's public price-history endpoint, `https://clob.polymarket.com/prices-history`, which needs no account. They hold minute prices for the first outcome token of every moneyline, stored in one file per inferred tournament-type bucket. The market list comes from the census and the extension, so do sections 1 and 2 first. The `lower` group is exactly these two buckets:

```
./python.sh -m src.ingest.public_dump.polymarket_prices --buckets lower --workers 10 --rps 8
```

* The original run made 17,946 ITF and 7,024 Challenger requests with no errors. These counts are under `sources.polymarket_prices` in the tracked [download_log.json](studies/public_data_dump/download_log.json). At 8 requests per second that takes just under an hour.
* The run is resumable. If it is interrupted, run it again and it requests only the windows that have no stored response.
* The same command also rebuilds the index tables from section 2 and the price Parquet in `data/dump/odds/polymarket/price_history/`. The original staged 20,593,357 ITF and 14,630,051 Challenger price rows ([coverage_tables.md](studies/public_data_dump/coverage_tables.md)). The command also appends a line to `polymarket_runs.jsonl`.
* `--buckets all` re-downloads every bucket, which took 36,295 requests originally.

The new files will not match the old bytes, because every stored response carries its retrieval time. The responses themselves can match. On 23 Sep 2026, four stored windows (two per bucket) were requested again and came back byte-identical. How long Polymarket keeps serving minute histories for old markets is unknown. A later run also covers more than the original:

* It picks up markets whose sporting date has passed since 22 Sep 2026.
* It extends the windows of markets that were still open then.

## 4. `charting-m-points-2020s.csv`: Match Charting Project

This file comes from [JeffSackmann/tennis_MatchChartingProject](https://github.com/JeffSackmann/tennis_MatchChartingProject) at commit `1813a1309b7ed7ebf1c7e884b32bf675d00e4edf` ("thru 18 sep 2026"). It is licensed CC BY-NC-SA 4.0. [`match_charting.py`](../src/ingest/public_dump/match_charting.py) downloads the planned files from that commit that are not already present, about 430 MB for the full set. It records receipts and stages the files to Parquet:

```
./python.sh -m src.ingest.public_dump.match_charting
```

To fetch only this file:

```
curl -L -o data/raw/public_dump/match_charting_project/charting-m-points-2020s.csv \
  https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/1813a1309b7ed7ebf1c7e884b32bf675d00e4edf/charting-m-points-2020s.csv
```

A file fetched with `curl` has no receipt, so the adapter downloads it again the next time it runs. The re-download on 23 Sep 2026 was byte-identical, and its SHA-256 matches the one recorded in [download_log.json](studies/public_data_dump/download_log.json). This only works while the repository stays online. Several of Sackmann's other repositories already returned HTTP 404 on 22 Sep 2026 (see [the public data dump report](../docs/studies/public_data_dump/README.md)).

Run the adapter directly rather than `run_all --sources mcp`, because `run_all` also rewrites the tracked manifest, coverage tables and download log.

## 5. The Hugging Face ATP pipeline dump

[`atp_pipeline_handoff.py`](../src/ingest/public_dump/atp_pipeline_handoff.py) downloads the dataset [`atlas-polybot/atp-pipeline-handoff`](https://huggingface.co/datasets/atlas-polybot/atp-pipeline-handoff) at commit `ea3d94d79f5d9e9b4bead031e2c6262f91a86c35`. The download needs no account. The tracked [plan.csv](studies/atp_pipeline_handoff/plan.csv) lists every file with its hash, and the adapter checks each file against it. From the repository root:

```
./python.sh -m src.ingest.public_dump.atp_pipeline_handoff plan    # only if data/studies/atp_pipeline_handoff/plan.csv is missing
./python.sh -m src.ingest.public_dump.atp_pipeline_handoff fetch
```

* **Resuming.** The fetch resumes: finished files are skipped and part-way files continue from their last complete 256 MB range. [status.md](studies/atp_pipeline_handoff/status.md) shows what is done and what is left.
* **Exact copies.** Files over 1 MB are stored gzipped. The `.gz` bytes differ from run to run, but `gzip -dc` returns the original file, whose hash the adapter has checked.
* **Availability.** The dataset has no licence and could be withdrawn, so this re-download works only while it stays online.
* **Backup.** A zip of the whole folder is in cold storage at `gs://tennis-predictions-archive/public_dump/tennis_atp_pipeline_handoff_raw_2026-09-25.zip`: Coldline, uploaded 25 Sep 2026, 16,666,419,985 bytes, SHA-256 `bc7d1b49977d4c58f3f3cfe5f49f0f166370d64e2077e3b6593e7b9eb30e6c9f`. To restore:

  ```
  gcloud storage cp gs://tennis-predictions-archive/public_dump/tennis_atp_pipeline_handoff_raw_2026-09-25.zip .
  tar -x -f tennis_atp_pipeline_handoff_raw_2026-09-25.zip -C data\raw
  ```

  This recreates `data/raw/public_dump/atp_pipeline_handoff/`. The restore was tested with Windows `tar` before upload. `README.txt` in the same bucket folder describes both of the bucket's zips.

## 6. Polymarket trade fills

[`polymarket_trades.py`](../src/ingest/public_dump/polymarket_trades.py) downloads every fill of every tennis moneyline in the index from section 2 whose match was on or before the cutoff (default 21 Sep 2026). It uses Polymarket's public trades endpoint, `https://data-api.polymarket.com/trades?market=<condition id>&takerOnly=false`, which needs no account. The original run on 25 Sep 2026 made 36,028 requests for 35,756 markets with no errors:

```
./python.sh -m src.ingest.public_dump.polymarket_trades --buckets all --workers 8 --rps 14
```

* The run is resumable: a market counts as done when its receipt says so and all its pages are stored.
* The same command rebuilds `data/dump/odds/polymarket/trades/`. To rebuild only that from existing raw files: `./python.sh -m src.ingest.public_dump.polymarket_trades --no-fetch`. It also appends a line to `polymarket_runs.jsonl`.
* Each stored response carries its retrieval time, so the bytes will differ. Fills of settled markets should not change.

The study tables in `data/studies/polymarket_sharp_money/` rebuild offline from the staged fills with `build_positions.py`, `classify.py` and `prematch.py` (see the [study README](../docs/studies/polymarket_sharp_money/README.md#reproduce)).

## Checksums

These are the SHA-256 values of the originals on 23 September 2026. Use them to check a restored backup with `sha256sum <file>`.

| File | Bytes | SHA-256 |
|---|---:|---|
| `markets.jsonl.gz` | 116,560,662 | `cf994e5233da550d7fb7d750805397ae44433d3b7bb07a817f60c5c687319cc5` |
| `markets.jsonl.gz` decompressed (`gzip -dc`) | 928,489,681 | `c9638f66fc7c01114b0fade5246fa45d50742e870d45c7b6be677789845a9a2d` |
| `events.jsonl` (under 50 MB; restored with the census) | 45,028,131 | `8788240b915c5b9ae1a35ba725a3b978e9a76117b0c3ad5861297dd0666f37dd` |
| `market_index.parquet` | 106,526,218 | `248965c65fca1ac34b7775a49307ee40aad1b2a70ec88836b298658c6050e7fe` |
| `itf.jsonl.gz` | 72,161,992 | `987f213059af60790a751572f5c470b08022f427c542972ede9dc263a982d7bb` |
| `challenger_125_inferred.jsonl.gz` | 50,464,333 | `71a0b0176362ec9892c6e9a7d95b481367a96fc7c2bbac20b51f4e7212e8ba34` |
| `charting-m-points-2020s.csv` | 56,590,483 | `2cd43f73e0530a47ea4c02b99dae40177ca6d58a8ccf9189358eb05dffb4be9a` |

The `markets.jsonl.gz` and `events.jsonl` hashes also appear in [manifest.json](studies/public_data_dump/manifest.json), as the source hashes of the two index tables.

## Keeping this list current

`.gitignore` matches paths, not sizes. Three kinds of rule keep large files out of git:
* **Folders:** `data/raw/` and `data/dump/` as whole folders.
* **File types:** every `.parquet` file, and archives (`.zip`, `.7z`, `.tar`, `.tar.gz`, `.tgz`) anywhere in `data/`, plus `data/backups/`.
* **Names:** a list of every file over 50 MB by name.

A large file anywhere else, for example a new output in `data/studies/`, would still be committed. So before committing, run these from the repository root in Git Bash.

**Check.** This prints every file over 50 MB that git would pick up. On 25 Sep 2026 it printed nothing: 94 files were over 50 MB, all ignored.

```
find . -path ./.git -prune -o -type f -size +50000000c -print | git check-ignore --no-index --stdin -n -v | grep '^::' | cut -f2
```

**Fix.** This appends each of those files to the end of `.gitignore`:

```
find . -path ./.git -prune -o -type f -size +50000000c -print | git check-ignore --no-index --stdin -n -v | grep '^::' | cut -f2 | sed 's|^\./||' >> .gitignore
```

Then move each new line into the named list in `.gitignore` and describe the file on this page.

**Already tracked.** An ignore rule does not remove a file git already tracks. This lists tracked files over 50 MB; on 25 Sep 2026 there were none:

```
git ls-files -z | xargs -0 -r ls -l | awk '$5 > 50000000 {print $5, $NF}'
```

Take any it lists out of the index with `git rm --cached <file>`. The file stays on disk.
