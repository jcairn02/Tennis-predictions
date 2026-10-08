# Australian Open and Roland Garros point data, 2022–2026: evidence

Evidence for [docs/studies/ao_rg_points/](../../../docs/studies/ao_rg_points/README.md) (29–30 September 2026): the data map's gap `slam_points_ao_rg`, the Hawk-Eye Court Vision copy downloaded for it on 29 September, and SofaScore's records collected for it on 30 September ([decision](../../../docs/decisions/2026-09-29-ao-rg-points.md)). Data collection, not a selection.

## Files

**The gap:**

| File | What it is | Made by |
|---|---|---|
| [gap_matches.csv](gap_matches.csv) | The gap's 1,636 matches as the map had them on 25 Sep 2026, frozen: names, date, tournament, the map's uid of that build (later builds renumber), its best grain and sources. Five have no tournament name on the map and take their source's (`tname_from`) | `gap.py` |

**The Hawk-Eye Court Vision copy** (`hawkilol/tennisSlamBallTracking` @ `f97a9b3`):

| File | What it is | Made by |
|---|---|---|
| [slam_ball_tracking_summary.json](slam_ball_tracking_summary.json) | The adapter's last run: files planned, how each arrived (receipts), rows and bytes of every staged table | `src/ingest/public_dump/slam_ball_tracking.py` |
| [hawkeye_gap.csv](hawkeye_gap.csv) | One row per gap match: whether the copy holds it, its replay status against the official score, its tracking, and whether it fills the gap at point or shot grain | `hawkeye.py` |
| [hawkeye_summary.json](hawkeye_summary.json) | The checks of the staged tables (against the research lane's own reading; CSV against JSON) and the gap's fill by tournament, tour and year | `hawkeye.py` |

**SofaScore** (`src/ingest/point_sources/sofascore_tournaments.py`):

| File | What it is | Made by |
|---|---|---|
| [sofascore_seasons.csv](sofascore_seasons.csv) | One row per gap edition (23): its SofaScore season, found by the gap probe (20) or by the adapter from a day listing on 30 Sep (3), and what the adapter needs to find a season anew | `gap.py` |
| [sofascore_links.csv](sofascore_links.csv) | One row per gap match: the SofaScore event it links to (all 1,636), the round, status and winner check | `link_sofascore.py` |
| [sofascore_fetch_order.csv](sofascore_fetch_order.csv) | The linked events in the order fetched: the 891 the Hawk-Eye copy does not record completely first, newest first; then the 745 it does | `link_sofascore.py` |
| [sofascore_check.csv](sofascore_check.csv), [sofascore_check.json](sofascore_check.json) | One row per gap match: what SofaScore answered, the record's completeness, the box score, and the set scores against the official result (Tennis My Life) and the Hawk-Eye replay | `sofascore_check.py` |
| [sofascore_summary.json](sofascore_summary.json), [runs.jsonl](runs.jsonl) | The adapter's runs, one line each: the probe's answers imported (29 Sep), the three seasons found and listed (30 Sep, 29 requests), the stagings, and the second record fetch (14:26-14:55 UTC, 1,087 requests; the summary is its). The first record fetch (2,108 requests, 04:19-05:15 UTC) was stopped while it waited for a click, so it wrote no summary line; its receipts and its log record it | `sofascore_tournaments.py` |

## Raw data and staged tables (gitignored)

* `data/raw/public_dump/slam_ball_tracking/` (268 MB): the repository's files at their own paths, the tracking JSON of 2022–2024 gzipped, `_tree_f97a9b31e64e.json` and `_receipts.jsonl`. 2,035 files were copied byte for byte from the research copy in `data/raw/gap_sources/hawkilol/` (checked against the tree's git blob hashes); 1,222 were downloaded.
* `data/dump/points/slam_ball_tracking/` (113 MB): `matches.parquet` (2,027), `points/` (503,586 rows), `json_matches.parquet` (1,225), `json_points/` (307,734) and `shots/` (4,662,409 positions). No file is over 50 MB.
* `data/raw/point_sources/sofascore_tournaments/` (18 MB): SofaScore's answers gzipped, with `_receipts.jsonl`: day listings, the 23 seasons' listing pages, and the point-by-point and statistics of all 1,632 played gap matches (38 of them the gap probe's answers of 29 Sep, copied byte for byte). The runs' logs are in `_logs/`.
* `data/dump/points/sofascore_tournaments/` (3 MB): `events.parquet` (the 5,555 events of the 23 seasons, with the outcome of each document's fetch), `points.parquet` (250,664 point states) and `statistics.parquet` (140,973 rows).

## Reruns

```
./python.sh src/eda/ao_rg_points/gap.py                        # the frozen list (reads the map's matches.parquet: rerun only before a rebuild)
./python.sh -m src.ingest.public_dump.slam_ball_tracking       # the copy: skips what is held; --json-years all adds 2019-2021
./python.sh -m src.ingest.public_dump.slam_ball_tracking --stage-only
./python.sh src/eda/ao_rg_points/hawkeye.py                    # checks and the gap's fill
./python.sh src/eda/ao_rg_points/link_sofascore.py             # gap match -> SofaScore event, and the fetch order
./python.sh -m src.ingest.point_sources.sofascore_tournaments --seasons-file data/studies/ao_rg_points/sofascore_seasons.csv --events-file data/studies/ao_rg_points/sofascore_fetch_order.csv --browser   # asks only for what is not held (nothing now)
./python.sh -m src.ingest.point_sources.sofascore_tournaments --stage-only
./python.sh src/eda/ao_rg_points/sofascore_check.py            # SofaScore's checks
./python.sh -m pytest test/ao_rg_points -q
```

`gap.py` derives the list from the map's current `matches.parquet`, which later builds change as the gap fills; the committed `gap_matches.csv` is the list of 25 September.
