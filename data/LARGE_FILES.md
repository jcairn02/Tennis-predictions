# Files over 50 MB: how to get them back

These five files are gitignored because each is over 50 MB. GitHub warns above 50 MiB and rejects files above 100 MiB. A fresh clone does not have them. The rebuild and re-download results quoted below were tested on 23 September 2026 against the originals from 10 and 22 September 2026.

| File | Size | What it is | Way back | Exact copy? |
|---|---:|---|---|---|
| `data/studies/tennis_data_audit/polymarket/markets.jsonl.gz` | 116.6 MB | Polymarket tennis contract inventory: the census of 10 Sep 2026, 411,502 contract rows | A backup, or an offline rebuild from a backup of its page cache. Otherwise a live re-run makes a new snapshot | Only from a backup |
| `data/dump/odds/polymarket/market_index.parquet` | 106.5 MB | Staged index of 464,266 Polymarket contracts with an inferred tournament-type bucket | Offline rebuild, about 15 seconds | Same rows; a later rebuild updates some flags |
| `data/raw/public_dump/polymarket_prices/bodies/itf.jsonl.gz` | 72.2 MB | Raw minute price-history responses for 17,930 ITF moneylines | Re-download, about an hour together with the next file | No; the responses matched in a spot check |
| `data/raw/public_dump/polymarket_prices/bodies/challenger_125_inferred.jsonl.gz` | 50.5 MB | The same for 7,021 Challenger / WTA 125 moneylines | Same command as the ITF file | No; the responses matched in a spot check |
| `data/raw/public_dump/match_charting_project/charting-m-points-2020s.csv` | 56.6 MB | Match Charting Project men's shot-by-shot points, 2020s | Re-download from a pinned commit | Yes |

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

`.gitignore` matches paths, not sizes. Before pushing, this lists every file over 50 MB and says whether git ignores it:

```
find . -path ./.git -prune -o -type f -size +50000000c -print | while read -r f; do
  git check-ignore -q "$f" && echo "ignored:     $f" || echo "NOT IGNORED: $f"
done
```

Add any `NOT IGNORED` file to the list in `.gitignore` and to this page.
