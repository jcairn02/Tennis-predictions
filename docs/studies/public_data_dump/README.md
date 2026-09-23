# Public data dump: acquisition run of 22 September 2026

**Seven public source families were downloaded byte-exact and staged by source into string-typed Parquet under `data/dump/`, with per-file provenance and a tracked manifest.** Scope is 2010 onward with the emphasis on 2022–2026; the freshest rows in the dump are Tennis My Life matches with tournament weeks up to 21 September 2026 and Polymarket contracts scheduled through 24 September 2026. No cleaning, merging or normalisation was done: every source column is kept verbatim, and the [structure plan](structure-plan.md) records how the next phase should combine them.

This is an acquisition and organisation record, not a source selection or a decision. Rights of every source are unchanged by copying it (see the last section).

| Item | Where |
|---|---|
| Pipeline code | `src/ingest/public_dump/` (one adapter per source, `run_all.py`, `polymarket_prices.py`, `polymarket_catalog.py`, `build_manifest.py`) |
| Byte-exact downloads and receipts | `data/raw/public_dump/<source>/` (gitignored; `_receipts.jsonl` per source) |
| Staged tables | `data/dump/{matches,players,rankings,points,odds}/<source>/` (gitignored) |
| Manifest, coverage tables, download log | [`data/studies/public_data_dump/`](../../../data/studies/public_data_dump/) (tracked): [manifest.json](../../../data/studies/public_data_dump/manifest.json), [coverage_tables.md](../../../data/studies/public_data_dump/coverage_tables.md), [download_log.json](../../../data/studies/public_data_dump/download_log.json) |
| Tests | `test/public_data_dump/` (offline; 28 tests) |
| Target structure proposal | [structure-plan.md](structure-plan.md) |

## Question, method, status

**Question.** From the source register's most recommended public families, how much recent, complete, statistics-rich tennis data can be accumulated in a tabular form, and how should it be organised before cleaning and merging?

**Method.** Each adapter plans files from the source's own listing (GitHub tree at a pinned commit, the Tennis My Life file manifest, the Zenodo record, the GitHub release, the tennis-data.co.uk index), downloads them with retries and validators (rejecting HTML error pages and non-workbook bytes), writes a receipt (URL, time, status, bytes, SHA-256, route), then stages each file to Parquet with all columns as strings plus provenance columns (`_source`, `_source_file`, `_row`, `_width_ok`, `_extra`, `_sha256`, `_retrieved_at`). Malformed rows are kept and flagged rather than dropped. Odds files are physically partitioned by the source's verbatim tournament-type label; Polymarket prices are partitioned by an inferred tournament-type bucket. `build_manifest.py` measures rows, date bounds and tournament-type counts from the staged files.

**Environment.** The project's `tennis` Conda environment did not exist; it was created from `environment.yml` (`mamba env create`) so `./python.sh` works as documented. Nothing else on the machine was changed.

**Status.** Acquisition complete for the planned sources except the gaps listed below. The 2010 lower bound was set mid-run on the owner's direction (the run had started at 2000); files fetched before that correction are kept and marked as out of scope rather than deleted. Re-running `./python.sh -m src.ingest.public_dump.run_all --sources all` refreshes changed Tennis My Life files, retries failed downloads and skips everything already staged.

## What was retrieved

Row counts are physical rows in the staged files (2010+ files unless stated). Dates are the source's own date field: tournament week for Sackmann and Tennis My Life (`tourney_date`), match day for tennis-data.co.uk and Open Tennis Data, scheduled UTC for the Live Tennis API and Polymarket.

| Source (register id) | Content staged | Years | Latest date in data | Files / rows | Version or route |
|---|---|---|---|---|---|
| Tennis My Life (PUB049) | ATP main tour, Challenger, ATP qualifying, WTA main tour season files; three ongoing-tournament files; ATP player database (12,903); ATP rankings of 2026-08-31 (2,298) | 2010–2026 (qualifying from 2007) | ATP main 2026-09-13, Challenger 2026-09-14, ATP qualifying 2026-08-28, WTA 2026-09-21, ongoing 2026-09-18 to 09-21 | 71 / 196,500 match rows (plus 33 pre-2010 files, 107,576 rows, fetched before the scope change) | live site manifest, fetched 2026-09-22 |
| Sackmann archival mirror (PUB003) | ATP main, qualifying+Challenger, Futures, doubles (to 2020); WTA main, qualifying+ITF; ATP/WTA player tables (66,912 / 70,571); weekly rankings; Grand Slam point-by-point | 2010–2026; rankings 2010–2026-06-08; slam points 2011–2024 | main tours 2026-05-25, ATP qualifying/Challenger and Futures 2026-06-01, WTA qualifying/ITF 2026-06-02, rankings 2026-06-08, slam points 2024 US Open | matches 96 / 882,094; rankings 6 / 2,537,744; points 166 / 2,328,041; players 2 / 137,483 | commit `8373358` (2026-06-25 snapshot) |
| Match Charting Project (PUB005) | chart metadata (men 7,566, women 4,264); shot-by-shot points 2010s and 2020s; 32 per-match aggregate stats files (all eras) | 2010–2026 (stats files include older matches) | women's charts 2026-09-09, men's 2026-05-21 | 38 / 4,537,499 (points 1,437,120; stats 3,088,549) | commit `1813a13` ("thru 18 sep 2026") |
| Live Tennis API public sample (PUB010) | match index (no winner/score), players (partial Sackmann crosswalk), June 2026 observed score states | 2023–2026 | index 2026-08-13; states 2026-06-01 to 07-01 | 3 / 1,157,313 (173,571 + 32,678 + 951,064) | Zenodo record 22048731 v1.0.0, MD5 verified |
| Open Tennis Data (PUB013) | completed results with exact dates, fixtures, players, tournaments, provenance, quarantine, coverage, health, catalog, sources | 2020–2026 | 2026-08-29 | 11 / 111,478 (completed 26,619) | release `data-v3-20260905T083014Z`, SHA-256 verified; derivative of tennis-data.co.uk and Sackmann |
| tennis-data.co.uk (PUB014, PUB015, tennis_data_odds) | ATP (2010–2026 except 2018) and WTA (2010–2026) results with set scores and closing odds, partitioned by `Series`/`Tier` | 2010–2026 | 2026-08-03 in both tours (2026 file captured that day: 1,786 ATP and 1,730 WTA rows, against 1,296 and 1,248 in the inherited June workbooks; one row mis-dated 2029) | 178 / 79,728 (plus 51 pre-2010 files, 27,268 rows, fetched before the scope change) | every file via Internet Archive captures (`route=wayback`, capture timestamp recorded per file); live site dead |
| Polymarket (poly_gamma, poly_clob_history) | event and market index (census of 2026-09-10 plus post-census extension of 2026-09-22); minute price history of the first outcome token of every moneyline | sporting dates 2025-09-10 to 2026-09-24 | catalog 2026-09-24 (scheduled); prices 2026-09-22 | index 2 / 34,197 + 3,483 events and 411,502 + 52,764 contracts; prices 84 / 62,218,248 minute rows for 36,270 markets (33,115 census and 3,155 extension moneylines; one market returned an empty history) | public Gamma and CLOB APIs; no account; 36,295 price requests, none failed |

Totals: 743 staged Parquet files, 74,838,119 rows, 426 MB staged, plus 1.75 GB of byte-exact downloads under `data/raw/public_dump/`. The full per-file table with date bounds, malformed-row counts and routes is in [coverage_tables.md](../../../data/studies/public_data_dump/coverage_tables.md).

### Recency, the owner's priority

| Population | Freshest public rows in the dump | What is missing after that |
|---|---|---|
| ATP/WTA main tour results with serve stats | Tennis My Life to the week of 2026-09-21 (WTA) and 2026-09-13 (ATP), ongoing files to 2026-09-21 | Sackmann stops 2026-05-25; nothing else public covers June–September besides TML |
| ATP Challenger | TML Challenger to 2026-09-14 | Sackmann stops 2026-06-01 |
| ATP qualifying | TML to 2026-08-28 | none public for September |
| WTA qualifying, WTA 125, ITF women | Sackmann to 2026-06-02 | **no public result source from June 2026 on**; the Live Tennis API index schedules them to 2026-08-13 without results; Polymarket settlements (`outcomePrices`) identify winners for markets that resolved |
| ATP Futures / ITF men | Sackmann to 2026-06-01 | same gap as above |
| Doubles | Sackmann to 2020; Slam doubles points to 2024 | no current public doubles results; Polymarket doubles markets exist (2,532 census moneylines) |
| Exact match dates | tennis-data.co.uk to 2026-08-03, Open Tennis Data to 2026-08-29 | September only from scheduled times (Live Tennis API index, Polymarket `gameStartTime`) |
| Closing bookmaker odds | tennis-data.co.uk to 2026-08-03 (archive capture of that day) | 4 August to September 2026; ATP 2018 entirely |
| Polymarket prices | minute history through 2026-09-22 | other contract types (set winners, totals, handicaps, exact score, completion) |
| Shot-level data | Match Charting Project women's charts to 2026-09-09 | men's file ends 2026-05-21 in this commit |

## What was not retrieved, and why

Nothing was purchased, no account was created, no site was scraped against its terms.

| Source | Reason | Consequence |
|---|---|---|
| tennis-data.co.uk live files | Every workbook path returned an IONOS/Sedo domain-parking page (HTTP 404) on 22 Sep 2026, while the index pages still listed the files | All 2010–2026 files came from Internet Archive captures instead; the capture date is recorded per file. ATP 2018 has only HTTP 503 captures and is missing; ATP 2002, 2004, 2006 also failed but are out of scope |
| tennis-data.co.uk inherited June 2026 workbooks (`data/raw/tennis_data_couk/`) | Older than the August archive captures; overlap | Not staged; left on disk for a later diff |
| Sackmann original repositories, `tennis_pointbypoint`, `tennis_slam_pointbypoint` | Still HTTP 404 on 22 Sep 2026 | Archive mirror used; the 2012–2015 point strings are unavailable and old anyway |
| Sackmann 2000–2009 files, TML amateur file, TML `backup_ll_audit_*` folder, MCP points before 2010 | Out of the 2010+ scope; backup folder is a duplicate of the season files | `--mcp-all-eras` and `--start-year` flags fetch them if ever wanted |
| TennisData.app | Download page behind a bot check; HTTP 403 | Unmeasured; would need a browser session |
| Live Tennis API full dataset / academic programme | Application-only, noncommercial | Only the public sample was taken |
| Betfair Historical Data, The Odds API, BettingIsCool, OpticOdds, TxODDS, OddsPapi, BetsAPI, PolymarketData, Telonex, Dome, PMXT, Poly Research & Robotics | Registration, payment or licence required | Not part of a public dump; documented in the source register |
| OddsPortal, BetExplorer, Tennis Explorer, CoreTennis, TennisLive, Tennis Abstract website, official ATP/WTA/ITF sites | Terms restrict automated extraction, or no bulk export exists | Not scraped |
| Kaggle, Hugging Face and GitHub re-uploads of Sackmann or tennis-data files, SCORE's MCP derivative, TennisDB, Ultimate Tennis Statistics | Derivatives of collections already downloaded | Skipped as overlap |
| Polymarket contract types other than moneyline (373,083 census contracts plus 49,282 in the extension), the second outcome token, trades and order books | Twelve times more requests; the complement token is nearly redundant; trades/books are different data layers | `polymarket_prices.py --market-types` extends the pull when wanted |

## Overlaps acknowledged (not downloaded twice)

* **Sackmann family**: original repositories, the Aneeshers GitHub mirror, its Hugging Face mirror (same commit, checked via the Hub API) and the inherited copies in `data/raw/sackmann/` are one dataset. Only the GitHub mirror was downloaded.
* **Tennis My Life**: season files, ongoing files and the publisher's backup folder overlap; season and ongoing files were taken (a match can migrate from an ongoing file to a season file; both are kept as retrieved), the backup folder was not.
* **Sackmann vs Tennis My Life**: the same ATP/WTA matches with different ids, corrections and date coverage. Both were downloaded on purpose, because the owner asked to consider all sources with in-match statistics; the merge phase reconciles them.
* **tennis-data.co.uk vs Open Tennis Data**: every Open Tennis Data completed row cites tennis-data.co.uk (most also Sackmann). Open Tennis Data adds exact dates and provenance but no odds; it is staged as a derivative and flagged as such in its sidecars.
* **Odds branch overlap**: tennis-data.co.uk's `MaxW/MaxL/AvgW/AvgL` columns are OddsPortal aggregates (per the provider's notes), so OddsPortal/BetExplorer were not scraped; Kaggle "ATP with odds" datasets are re-uploads of the same workbooks and were not downloaded; the inherited June workbooks were not re-staged.
* **Match Charting Project**: the raw points and the per-match stats files are two views of the same charts (stats are derived from points). Both were downloaded because the stats files save re-implementing the chart parser; they are stored under one source so they cannot be counted twice. Tennis Abstract's website charts and SCORE's teaching subset were not fetched.
* **Polymarket**: the Gamma census (metadata) and the CLOB price history (prices) are different layers of one venue, both under `odds/polymarket/`. The post-census extension is merged with a `catalog` column, never re-fetching census events.
* **Live Tennis API**: the public Zenodo sample overlaps the vendor's commercial and academic products, which were not requested.

## How the dump is organised

```
data/raw/public_dump/<source>/                 byte-exact files as downloaded, _receipts.jsonl, docs/
data/dump/
  matches/{sackmann_archive/{atp,wta}, tennis_my_life/{atp_main,atp_challenger,atp_qualifying,wta_main,ongoing},
           live_tennis_api_zenodo, open_tennis_data}/
  players/{sackmann_archive,tennis_my_life,live_tennis_api_zenodo,open_tennis_data}/
  rankings/{sackmann_archive,tennis_my_life}/
  points/{sackmann_archive/slam_pointbypoint, match_charting_project/{metadata,points,stats}, live_tennis_api_zenodo}/
  odds/tennis_data_couk/<atp|wta>/<series or tier label>/<year>.parquet
  odds/polymarket/{event_index,market_index}.parquet
  odds/polymarket/price_history/<bucket>/<YYYY-MM>.parquet
```

* One Parquet per source file, named after it; a `.meta.json` sidecar next to each carries URL, hash, retrieval time, route, commit/release, row and column counts.
* All source columns are strings in source order. Duplicate header names get `__2`; source names starting with `_` are prefixed `src`. Short rows are padded (`_width_ok = short`), long rows keep the surplus in `_extra` (`_width_ok = long`). Example: every Sackmann doubles row has 20 trailing empty fields beyond its 65-column header; they are kept as an all-separator `_extra` value.
* Odds by tournament type: tennis-data.co.uk uses its own labels verbatim (`Grand Slam`, `Masters 1000`, `ATP500`, `ATP250`, `Masters Cup`; WTA `WTA1000/500/250`, earlier `Premier`, `International`, `Tour Championships`). Polymarket uses fourteen inferred buckets from the tier-terrain study's classifier (`slam_main`, `slam_qualifying`, `tour_1000`, `tour_500`, `tour_250`, `tour_finals`, `tour_qualifying`, `challenger_125_inferred`, `itf`, `doubles`, `slam_juniors`, `outrights`, `team_exhibition`, `other`), with the provider's own `series`/`league` fields kept in the index for re-derivation.
* Polymarket price rows: `event_id, event_slug, market_id, condition_id, token_id, outcome, bucket, sport_date, t (Unix seconds), p (price), window_start, window_end, _source, _retrieved_at, _sha256`; raw response bodies are kept gzip-appended per bucket under the raw folder, and the Parquet is rebuilt from them.

## Coverage overview

Detailed tables: [coverage_tables.md](../../../data/studies/public_data_dump/coverage_tables.md). Highlights:

* **Match rows 2010+ with serve statistics available**: Sackmann main tours (90,888 rows to May 2026), Sackmann qualifying/Challenger (137,088) and Futures (277,637) with statistics that become sparse below Challenger level and before 2025; WTA qualifying/ITF (363,168 rows) largely without statistics before 2025; Tennis My Life ATP main (47,875), Challenger (79,326), qualifying (24,564) and WTA (44,547) rows with serve totals to September 2026.
* **Point and shot level**: 2.33 million Grand Slam point rows 2011–2024 (Wimbledon and US Open to 2024, Australian Open and Roland Garros to 2021, doubles and mixed for 2018–2024 where published); 1.44 million Match Charting Project shot rows 2010–2026 plus 3.09 million aggregate stat rows; 951,064 timestamped score states for June 2026.
* **Rankings**: 2.54 million weekly ranking rows 2010 to 8 June 2026 (ATP and WTA) plus one ATP snapshot of 31 August 2026.
* **Closing odds**: 79,728 match rows 2010–2026 across ATP and WTA main-tour tiers, partitioned by tournament type; no lower-tier odds exist in any public file.
* **Polymarket**: minute price histories for every moneyline in the catalog, by inferred bucket (markets / price rows / first–last price time): ITF 17,929 / 20.35M / 2026-05-13 to 2026-09-22; Challenger-WTA 125 (inferred) 7,021 / 14.55M / 2025-10-11 to 2026-09-22; doubles 2,786 / 8.12M / 2026-05-13 to 2026-09-22; Masters-WTA 1000 1,660 / 4.05M / 2025-09-23 to 2026-08-23; Grand Slam main draws 1,007 / 3.92M / 2026-01-18 to 2026-09-13; 250s 1,538 / 3.61M; 500s 1,017 / 2.41M; tour qualifying 1,699 / 2.00M; Slam juniors 692 / 1.54M; Slam qualifying 832 / 1.38M; Tour Finals 51 / 0.22M; team events 38 / 0.06M. ITF and doubles markets only appear in the catalog from May 2026, so their price history is short by construction, not by omission. Each market contributes one series (its first outcome token), typically one observation per minute while the market is open, from about three days before a Slam match to a day before a lower-tier match.

Known defects surfaced by verbatim staging (for the cleaning phase; also listed in the structure plan): the WTA 2021 workbook labels 26 rows `WTA251`…`WTA276` (an Excel fill-down of `WTA250`); the WTA 2026 file dates the Iasi Open Sherif–Badosa match `2029-07-20`; 2 men's and 9 women's Match Charting metadata rows are short and shift values into the wrong columns; Tennis My Life ATP files repeat `(tourney_id, match_num)` keys; Sackmann doubles rows carry trailing empty fields; the Live Tennis API index has no winners.

## Ambiguities and how they were navigated

1. **"Highest recommended sources."** Read as the register's five public families plus the two public sources it names as next candidates with recency (Match Charting Project, Open Tennis Data). Commercial and application-only sources were excluded because the step is a *public* dump.
2. **Year range.** The run started with a 2000 lower bound (the earlier note said 1990–2005 was low priority); the owner corrected this mid-run to 2010+ with emphasis on 2022–2026. The default was changed to 2010, the run restarted, and the pre-2010 files already fetched (33 Tennis My Life and 51 tennis-data.co.uk files) were left in place and marked out of scope rather than deleted.
3. **"Don't download overlapping data."** Applied strictly to the odds branch (one copy of each odds source, derivatives skipped). For match sources the owner also said "consider using all", so overlapping-by-derivation sources with extra value (Open Tennis Data's exact dates, MCP's aggregate stats) were downloaded and flagged as derivatives.
4. **"Organise by tournament type."** Done with verbatim source labels for tennis-data.co.uk and inferred buckets for Polymarket. A normalised tier taxonomy across sources is cleaning work and was not attempted.
5. **"Tabular format."** Parquet with every column as a string, plus provenance. Typing dates, numbers and scores was deliberately left to the cleaning phase so nothing is altered by parsing.
6. **tennis-data.co.uk being dead.** The adapter tries live, then Internet Archive captures, then the inherited local workbooks, and records the route. Archive captures were preferred over the local June files because they are newer (2026 captured 3 August).
7. **"As much odds data as reasonable" for Polymarket.** Minute prices of the first outcome token for every moneyline in the catalog (36,271 markets whose sporting date had passed), fetched at a capped 8 requests per second with per-market windows split into 13-day chunks because the endpoint returns nothing for windows longer than about 14 days. Other contract types were deferred. One earlier pull was force-stopped to raise its worker count, which left a damaged gzip member in the Slam bucket's raw store; the reader skips damaged members and the lost requests were re-fetched, which is why the store has 36,295 receipts for 36,270 markets.
8. **Recency for Polymarket.** The audited census ends 10 September; a catalog extension adapter pages newer events from Gamma (keyset pagination, because the offset endpoint rejects offsets above 2,000) and merges them with a `catalog` flag. It found 3,483 events for 11–24 September.
9. **Player A/B ordering.** Not applied here; the [structure plan](structure-plan.md) proposes higher-ranked player first, then first server where point data exists, then a deterministic hash, with swap augmentation in training.
10. **Interpreter.** The documented `tennis` environment was created instead of reusing another project's environment, because this is project code rather than a one-off research utility.

## Rerunning and updating

```
./python.sh -m src.ingest.public_dump.run_all --sources all          # static sources; skips what is staged, retries failures
./python.sh -m src.ingest.public_dump.polymarket_catalog             # new Polymarket tennis events since the last known id
./python.sh -m src.ingest.public_dump.polymarket_prices --buckets all --workers 10 --rps 8   # prices for markets without a stored body
./python.sh -m src.ingest.public_dump.build_manifest                 # manifest, coverage tables, download log
./python.sh -m pytest test/public_data_dump -q                       # offline tests
```

Tennis My Life season files are re-fetched only when the publisher's manifest changes; its ongoing files are always re-fetched. Sackmann and Match Charting Project are pinned to commits and only change when `--sackmann-commit` / `--mcp-commit` are pointed at a newer commit. The Polymarket price store is append-only and resumable; a request is repeated only if its body is not stored (a run stopped by force can leave a damaged gzip member, which the reader skips).

## Limitations

* Row counts are physical rows; completeness against the real tournament calendar was not measured.
* Date bounds are lexicographic min/max of verbatim strings and inherit source semantics (tournament week vs match day vs scheduled time).
* The Polymarket tier buckets are name-based inference; `challenger_125_inferred` is a residual bucket.
* A Wayback capture reflects the file on the capture date, not necessarily the last state of the provider's file.
* Rights: Sackmann and MCP CC BY-NC-SA 4.0; Live Tennis API sample CC BY-NC 4.0; Tennis My Life MIT on the website but noncommercial in its repository; tennis-data.co.uk without an explicit licence; Polymarket under its API terms. Copying data into this dump grants nothing beyond those terms.

## Cleanup candidates (not deleted)

`data/raw/public_dump/polymarket_catalog/pages/20260922T211935Z/` (21 pages from the aborted offset-paginated attempt), the pre-2010 Tennis My Life and tennis-data.co.uk files, the inherited `data/raw/sackmann/` and `data/raw/tennis_data_couk/` June snapshots, and the 5 smoke-test Polymarket receipts are all retained. Removing them is a separate decision.
