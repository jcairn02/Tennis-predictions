# Filling the data map's gaps: downloads

**Status: data collection, not a selection.** Started 29 September 2026 with the ATP tour-level gap. The [gap-sources research](../../research/gap-sources/README.md) proposed a source list for each of the [data map](../../../data/data_map.html)'s eight gaps; this study downloads them, one gap at a time, in the order proposed. Nothing here approves a dataset, model or venue.

## ATP tour-level point by point, 2025 to June 2026

The gap (`atp_points_2025` in [data_map.yaml](../../../data/data_map.yaml)) is 3,778 ATP tour-level singles matches of 2025 to June 2026 (Finals, 1000s, 500s, 250s and their qualifying) held only as box scores on 25 September 2026. The research proposed two sources:

| Order | Source | What the research measured | Status on 30 Sep 2026 |
|---|---|---|---|
| 1 | **SofaScore**, listed tournament by tournament | Complete points for 34 of 36 sampled matches, box scores for 34; about 3,570 of the gap | Downloaded: every point for 3,777 of the 3,778 matches (3,753 complete), box scores for 3,777 |
| 2 | **SirGenkii/infotennis**, a GitHub fork's MySQL dumps of decrypted ATP Stats Centre files | Point outcomes (winner, forced or unforced error) for 715 gap matches of December 2024 to April 2025 | Downloaded, hash-checked and staged; fills the 715 |

**The gap on the map fell from 3,778 to 3** (build of 30 September, 18:04 UTC). One is a match SofaScore has no record of, Kitzbühel 2025, Rinderknech v Hanfmann. The other two are a match the map holds twice under two spellings of a name, whose other row has the points.

### SirGenkii/infotennis (done)

`src/ingest/public_dump/sirgenkii_infotennis.py` downloads the repository at its head commit `ec1b188` (11 April 2025; the dumps date from `1bb7527`, 7 April 2025) and stages each dump as a table.

* **Downloaded [observed]:** 13 files, 34.5 MB, in 13 seconds: the six dumps plus the README, licence, config, player table and the three API notes. Every file matches the pinned git tree's blob SHA-1, and each dump is byte-identical to the research copy in `data/raw/gap_sources/sirgenkii/`.
* **Staged [observed]:** 239,526 rows, every value kept as dumped text.

  | Table | Rows | Columns | What a row is |
  |---|---:|---:|---|
  | `atp_results` | 1,343 | 18 | A match: event, round, players with ATP ids, score |
  | `atp_rally_analysis` | 136,928 | 29 | A point: server, serve 1 or 2, how it ended, serve speed and direction, rally-length bucket, score |
  | `atp_stroke_analysis` | 87,976 | 15 | A player's winners and errors by stroke, per set |
  | `atp_court_vision` | 6,992 | 47 | A tracked stroke: hit, net, bounce and peak positions (8 matches) |
  | `atp_key_stats` | 6,264 | 44 | A player's box score per set, with winners and unforced errors |
  | `atp_calendars` | 23 | 13 | An event: dates, category, surface |

* **Checked [observed]:** the research session's own parser (`src/eda/gap_sources/sirgenkii_matches.py`) reads the same row counts from its copy, and the same values in every cell. The only differences are 2,071 Court Vision coordinates dumped as `-0`, which it reads as 0.
* **In the map [observed, measured 29 Sep 2026]:** the results table's 1,343 rows are 1,286 played singles matches once the United Cup doubles rubbers and the unplayed matches (no score) are left out. 922 carry points.
  * *Placement:* 1,284 of the 1,285 in the map's window land on known matches, 1,280 of them by ATP tournament and player ids, as the Infosys copy is joined. The one left over, Tseng v Holmgren in the 2025 Australian Open qualifying, joins as a new match.
  * *The gap:* 715 of its 3,778 matches get every point with its outcome, as the research counted. That leaves 3,063 for SofaScore.
  * *On the page:* the map built at 22:08 UTC shows the gap at 3,063. The build at 21:46 UTC had shown 3,070, because it predated the fix that leaves 7 unplayed matches out.

### SofaScore (done)

`src/ingest/point_sources/sofascore_editions.py` is the by-tournament mode that the research found missing from the SofaScore adapter ("needs a by-tournament listing mode"). The player adapter lists one career at a time; this one works from the gap itself:

1. **Targets.** The gap's 3,778 matches, frozen at the first run in [sofascore_atp_points_2025_matches.csv](../../../data/studies/gap_downloads/sofascore_atp_points_2025_matches.csv). Once the map is rebuilt with what the run collects, the gap shrinks, so the list is not derived again unless asked (`--refresh-targets`).
2. **Editions.** The targets fall in 112 tournament editions (tour, tournament, year, ISO week).
3. **Locate.** SofaScore's day listing of the ATP category on a few days of the edition's week. The tournament season whose events name the most of the edition's known matches is taken. This is the method of the research probe, which located 9 of 9 sampled editions.
4. **List and link.** Every event of that season, qualifying included. Each target links to the singles event whose players both share a name word with it, 10 days before to 21 after the tournament start. Two refinements came from the session linking the Australian Open and Roland Garros gap:
   * A name with no word of three letters or more (Li Tu) uses its two-letter words.
   * When a pair met twice at one event, in the qualifying and again in the main draw, the event in the target's own draw is taken.
5. **Fetch.** The point-by-point record of every linked event, newest first, then every box score. If SofaScore blocks part-way, the points are what the run has.

**The first run was refused [observed].** At 21:40 UTC on 29 September, SofaScore answered HTTP 403 "challenge" to the first request and to its retry a minute later. That was nearly four hours after it had blocked the research probe (17:54 UTC). The run stopped as the collection rules require, after 2 requests, and froze the targets. The plain client was still refused on 30 September at 14:56 UTC (HTTP 403, now "Forbidden").

**The download [observed].** 30 September, 15:10 to 18:01 UTC, in browser mode, through the Chrome window the owner had opened for the Australian Open and Roland Garros session. The two sessions took turns, never running at once.
* *Requests:* 7,867: 313 to locate and list the 112 editions, then 3,777 point records and 3,777 box scores. There were 2 retries, no challenge and no token renewal.
* *Listing:* all 112 editions located; all 3,778 targets linked, to 3,776 events. The two events linked twice are the map's duplicates (next list).
* *Records:*

  | Point record | Targets |
  |---|---:|
  | Complete: every set has the score's games | 3,679 |
  | Complete to a retirement (the game in progress also listed) | 74 |
  | Short: games missing | 12 |
  | Other: the games fall differently from the score | 9 |
  | No score to compare with (SofaScore lists none) | 3 |
  | No record (HTTP 404) | 1 |

  "Other" is judged against SofaScore's own score, which can be wrong. At Båstad 2025 (Ugo Carabelli v van de Zandschulp) the listing says 7-6 5-4, but the record's 34 games are those of the official 7-6 5-7 6-3.
* *Box scores:* 3,777 of 3,778; 3,760 with the full serve and return set.
* *Staged:* 4,995 events (every event of the 112 tournaments), 464,721 point states and 226,347 statistics rows.
* *No record at all:* Kitzbühel 2025, Rinderknech v Hanfmann (neither points nor box score).

**The links, checked against the official result [observed].** `src/eda/gap_downloads/verify_links.py` rebuilds the links offline and compares each event with Tennis My Life's row for the same match, qualifying and main draw kept apart:

| Verdict | Targets |
|---|---:|
| Same winner and the same games in every set | 3,768 |
| Same winner; SofaScore lists no score (retirements early in the match) | 3 |
| Same winner; the score differs (Båstad, above) | 1 |
| No official row: the map's six matches taken from Sackmann | 6 |
| A different winner | 0 |

Two of the six Sackmann rows repeat a Tennis My Life match under another spelling:
* Humbert v Oconnell (Rotterdam 2026);
* Bu Yunchaokete v Albert Ramos (Monte-Carlo qualifying 2025).

Each links to its twin's event, and the map credits the Tennis My Life row. Two pairs met twice at Basel 2025, in the qualifying and again in the main draw: Opelka v van de Zandschulp, and Cilic v Goffin. Each of their four matches links to its own event.

## Running it

From the repository root, in Git Bash:

```
./python.sh -m src.ingest.public_dump.sirgenkii_infotennis              # done; reruns skip what is on disk
./python.sh -m src.ingest.point_sources.sofascore_editions               # plain client, once SofaScore's block has lifted
./python.sh -m src.ingest.point_sources.sofascore_editions --limit 3 --max-requests 60   # a trial on the 3 newest editions
./python.sh -m src.ingest.point_sources.sofascore_editions --stage-only  # no HTTP: rebuild the tables and evidence
./python.sh src/eda/data_map/build.py                                    # then redraw the data map
```

**Browser mode**, when SofaScore challenges the plain client. First open a Chrome window with a blank profile and a debugging port, in PowerShell:

```
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:LOCALAPPDATA\sofascore-cdp" --no-first-run --no-default-browser-check https://www.sofascore.com/tennis
```

Let the page load (click the check if one shows). Then run:

```
./python.sh -m src.ingest.point_sources.sofascore_editions --browser
```

The adapter makes each request as a `fetch()` inside that tab, at its own pace. It reloads the tab when the site's hourly token expires. Keep the window open; if a check appears in it, click it.

**Every run:**
* **Resumes.** Every answer is kept with a receipt, and nothing is asked twice. An HTTP 404 means the record does not exist and is not asked again.
* **Stops on a block.** HTTP 403, 429 or a challenge, after one retry a minute later.
* **Is budgeted.** `--max-requests`, 10,000 by default.
* **Rebuilds its evidence**, from everything on disk, even when it stops early.

`--skip statistics` fetches points only (about half the requests). `--gap <id>` points the adapter at another gap of the map, but only `atp_points_2025` has been run.

## Files

| File | What it is | Made by |
|---|---|---|
| [sirgenkii_summary.json](../../../data/studies/gap_downloads/sirgenkii_summary.json) | The SirGenkii download: every file's bytes, SHA-256 and git blob SHA-1, and each staged table's rows | `sirgenkii_infotennis.py` |
| [sofascore_atp_points_2025_matches.csv](../../../data/studies/gap_downloads/sofascore_atp_points_2025_matches.csv) | One row per target: the match as the map had it, the SofaScore event it links to, and what was fetched (status, points, completeness against the score, box score) | `sofascore_editions.py` |
| [sofascore_atp_points_2025_editions.csv](../../../data/studies/gap_downloads/sofascore_atp_points_2025_editions.csv) | One row per edition: the SofaScore season found, the listings tried, events listed and targets linked | `sofascore_editions.py` |
| [sofascore_atp_points_2025_summary.json](../../../data/studies/gap_downloads/sofascore_atp_points_2025_summary.json), [runs.jsonl](../../../data/studies/gap_downloads/runs.jsonl) | The last run's counts by year and level, and one line per run | `sofascore_editions.py` |
| [sofascore_atp_points_2025_link_check.csv](../../../data/studies/gap_downloads/sofascore_atp_points_2025_link_check.csv), [.json](../../../data/studies/gap_downloads/sofascore_atp_points_2025_link_check.json) | Each target's event against Tennis My Life's winner and score, and the counts | `src/eda/gap_downloads/verify_links.py` |

Raw files, gitignored:
* `data/raw/public_dump/sirgenkii_infotennis/`: the repository's files at their own paths, with `_receipts.jsonl`.
* `data/raw/point_sources/sofascore_editions/`: SofaScore's answers, gzipped verbatim, with `_receipts.jsonl`, and the runs' logs in `_logs/`.

Staged tables, gitignored:
* `data/dump/points/sirgenkii_infotennis/`: one Parquet file per dump.
* `data/dump/points/sofascore_editions/`: `events`, `points` and `statistics`, in the columns of the SofaScore player adapter.

Tests: `./python.sh -m pytest test/gap_downloads test/data_map -q`. They cover the dump reader, name linking and completeness, a whole run against a fake SofaScore (a block included), the link check's verdicts, and the map's placement of the records.

## Limits

* **Linking by names.** Name forms differ between the map and SofaScore, so a match could go unlinked or be paired wrongly. For this gap all 3,778 linked, and the check found no link with a different winner. It cannot vouch for the 6 matches that have no official row.
* **SofaScore's own records.** 21 records are short or uneven against the score, and SofaScore's listed score is itself wrong at least once (Båstad). Where another source holds the same match, the records can be compared once the sources are merged.
* **Placement on the map.** The map dates 2026 matches by the day played, so its generic link can put a record on the same pair's meeting a few days earlier at another event. The map therefore places SofaScore's records on the matches the adapter linked them to, by tournament, and uses the generic link only for the rest (`sofascore_edition_uids` in `src/eda/data_map/measure.py`). The other session found this trap in the Slam data.
* **The frozen list.** It keeps the map's match ids (`uid`) of the build of 25 September 2026. A later build renumbers matches, so the list is joined by its names and dates, not by `uid`.
* **Rights.** SofaScore's terms forbid automated extraction; it is collected on the owner's decision of 23 September 2026 ([point- and shot-level sources](../point_shot_sources/README.md#direct-download-24-september-2026)). The SirGenkii data has no licence and is a third party's decryption of ATP files, the kind the owner accepted for the Hugging Face copy on 25 September ([decision](../../decisions/2026-09-25-atp-pipeline-handoff.md)). The project decrypts nothing.
