# Data map: measured coverage

The numbers behind the [data map](../../data_map.html). `src/eda/data_map/measure.py` writes them, and `src/eda/data_map/build.py` runs it and draws the page. The catalog it reads for dataset statuses is [data_map.yaml](../../data_map.yaml).

| File | What it holds | In git |
|---|---|---|
| `coverage_cells.csv` | One row per tour, tournament level and year, 2018 to the last complete week: matches, estimated missing matches, matches by best detail (shot, point, stats, result) counting everything and counting only data on disk, and matches by the status of their best detail | Yes |
| `coverage.json` | The same cells, plus each source's matches in each cell, how each source matched the list of matches, and the run's notes | Yes |
| `build_report.json` | The last build: catalog problems, unmapped folders, live progress of the downloads marked `downloading` | Yes |
| `matches.parquet` | Every match in the map with its level, best detail and the sources that hold it | No, rebuilt |
| `_cache/` | Summaries of the slow sources (Infosys records, WTA point-log states, the WTA website's records, the Kaggle SofaScore copy) | No, rebuilt with `--refresh` (needed after a loader changes: the caches key on the input files only) |

## Method in brief

1. **The list of matches.** Built from the result files in order: Tennis My Life, Sackmann, the WTA's match lists, the Slam draws, the WTA website's records, api-tennis and TDI's listings. Singles only; walkovers are left out.
2. **Matching the other files.** Every other file is matched to the list by tour, the pair of surnames and the date (a window of 10 days before to 21 after, allowing for tournament-start versus match-day dating; 40 days either way for Grand Slam qualifying, which the 2021 Australian Open played in Doha and Dubai four weeks early). Two fallbacks follow: one surname agrees and the other names share a word (names cut short or reordered), or one player and the round agree in the same week (a changed surname). Both need the two players' first names to agree, which keeps sisters and namesakes apart (Naomi and Mari Osaka; the many players named Liu at the ITF events of one week). Before that test, about 6,400 Sackmann rows had been merged into other players' matches (8 Oct 2026). Infosys joins on the ATP's own tournament and player ids first. A row that matches nothing joins the list as a new match.
3. **Best detail.** Each match takes the richest detail any file gives it, and records whether that detail is on disk, downloading or assumed.
4. **Missing matches.** Estimated three ways: Grand Slam draw sizes (127 main-draw and 112 qualifying singles matches per tour per Slam); the rest of the current season after a level's files stop, from the same weeks of the season before; and a whole season where no file holds a level at all.
5. **What exists (drawn by the page).** The catalog's `universe` lists outside sources with the share of each tour, level and year they are measured or inferred to hold at each detail, or counts (the women's website-only charts), or files counted on disk (the encrypted ATP Stats Centre files, by file name only). Per cell the page takes, for each detail, the most any single source reaches, or adds a `disjoint` source's matches to ours. Paid feeds are listed, not counted.

Known limits: a player who changed surname and is not matched by round can be counted twice, as can one whose first name is spelled differently in a fallback (Dasha / Daria). Flashscore and the ATP-site statistics are not read into the counts. Doubles, juniors and exhibitions are outside the map. Combining outside sources by the largest single one understates what several together would reach.
