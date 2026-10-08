# Hugging Face ATP pipeline dump: what it adds, and its download

**Status: downloaded in full on 25 September 2026, under the owner's [decision of that day](../../decisions/2026-09-25-atp-pipeline-handoff.md).** All 5,707 planned files (150.53 GB) matched their hashes. They take 16.79 GB on disk. The final state by chunk and source is in [status.md](../../../data/studies/atp_pipeline_handoff/status.md). How the files are organised, and how to resume, is in [the evidence folder](../../../data/studies/atp_pipeline_handoff/README.md). Nothing is staged or merged yet, and this is not a source selection for modelling.

## Question

How much of the Hugging Face dataset [`atlas-polybot/atp-pipeline-handoff`](https://huggingface.co/datasets/atlas-polybot/atp-pipeline-handoff) does the project already hold, and what does it add?

## The source (observed 25 Sep 2026)

* **Publication.** Public, with no licence and no dataset card. Created 1 June 2026, last changed 19 June 2026 (commit `ea3d94d79f5d9e9b4bead031e2c6262f91a86c35`). 5,764 files, 151.6 GB.
* **Its own notes** (`RAW_DATA_SOURCES.md`) describe it as the raw input of another team's "unified dataset" builder, which is not included. They cover 1990–2024, and say 2025–26 "live in the owner's main repo" and are not published. The same notes cite `HANDOFF_README.md`, `DATA_COLUMN_GUIDE.md` and an `atp_rankings/` folder, none of which were uploaded. The author has no other public dataset.
* **Earlier research.** The [granular data leads](../../research/granular-data-leads/access-routes-tdi-and-open-data.md) of 24 Sep found it, but looked only at its Infosys and Court Vision folders.

## Method

* **Listing.** The Hub API gave every file's size and hash.
* **Samples.** Small files were downloaded whole. Large files were read by byte range (head, middle and tail), and their record structures were summarised.
* **Exact comparisons.**
  * The 57 Sackmann ATP files it shares with our copy were compared row by row after normalising line endings. The download plan later confirmed the matches from the hashes alone.
  * All 8,914 chart IDs in `mcp/charts/` were streamed and matched to [tennis_abstract_chart_gap.csv](../../../data/studies/granular_data_leads/tennis_abstract_chart_gap.csv).
  * The Tennis Abstract player pages were checked against our Sackmann rows for one player: Djokovic's full career, 1,504 rows.
* **Counts taken on trust.** Match counts for Flashscore and Infosys are the uploader's own progress files, marked [claim] below. They were not recounted.

## What the project already held

* **Byte-identical:** only the Sackmann ATP files for 2010–2024 (56 files, 494,464 rows), which differ from ours only in their line endings. Our `atp_players.csv` is newer than theirs: 940 rows are only in ours and 17 only in theirs.
* **The same data in another form, about 1.25 GB:**
  * The Tennis Abstract player pages. They draw on Sackmann's database, which we have: 1,073 Djokovic rows from 2010 in theirs, 1,077 in ours.
  * The basic ATP-site scrape.
  * 4,786 of the 8,914 charts.
* **Overall:** 0.9% of the dump's bytes.

## What it adds

| Folder | Size | New to the project |
|---|---:|---|
| `infosys_deep`, `infosys_full` | 3.1 + 7.0 GB | ATP Stats Centre point data for 2021–24: 37,355 tour, Challenger and qualifying matches, the uploader's counts exactly ([checks](#checks-on-chunk-1)). 25,934 of them (69%) have point rows, 3.63 million points in all. Tour-level points carry the outcome (winner, forced or unforced error, ace, double fault), serve speed, direction and shot type; 4,214 matches have those full outcomes. Challenger points classify only aces and double faults. Also per-set key statistics, stroke summaries and season-to-date statistics. `infosys_full` has the same layout, with Court Vision embedded in tour-level matches |
| `court_vision` | 0.34 GB | Hawk-Eye tracking for 4,570 tour-level matches: 14 from 2018, 298 from 2021, 1,348 from 2022, 791 from 2023 and 2,119 from 2024. Ball positions at hit, bounce and net, speeds, net clearance, serve type and outcome, per point. We hold nothing like it for ATP events |
| `flashscore_full`, `flashscore_gql_stats` | 127 + 11.2 GB | 566,853 distinct Flashscore matches ([checks](#checks-on-chunks-26)), each with its real start time, except 27,521 "recovered" rows. Also set durations, per-set statistics, the umpire, Flashscore IDs and raw head-to-head feeds.<br>• **Year files:** 162,594 matches, ATP and Challenger singles from 1990 to April 2025.<br>• **Statistics files:** add winners, unforced errors and net points.<br>• **Head-to-head crawl:** 403,900 matches found nowhere else, running to 17 April 2026 across ITF, WTA, Challenger and junior events. About 70,000 of them are dated 2025–26, inside the Polymarket period.<br>• **Statistics are sparse:** 22% of year-file records carry the statistics block, and 6% carry winners and unforced errors |
| `atp_scraped_enriched` | 0.83 GB | ATP per-set statistics, return rating, both players' season-to-date statistics at match time, prize money, draw sizes and tournament end dates. Main tour 1991–2024; qualifying and Challenger 2009–24 |
| `mcp/charts` | 0.93 GB | Chart pages scraped from Tennis Abstract, not the Match Charting export: stat tables plus the full point log, men only. 2,147 of them are website-only charts, missing from the export (1,788 from 2010–24). That is 2,147 of the 2,224 men's website-only charts up to 2024. A further 1,981 are export charts whose points our dump skipped, all but 28 of them before 2010 |
| `api_tennis` | 0.05 GB | Exact date, start time and status (walkover, retired, cancelled) for men's ATP, Challenger and ITF singles and doubles, 2021–24. Our exact-date sources cover the main tour only |
| `tennis_atp` (pre-2010), `tennis_abstract` | 0.1 + 0.71 GB | 1968–2009 history; backhand and opponent attributes; links from matches to charts |
| Minor | small | 3,150 ATP profiles: weight, turned pro and backhand, but empty birth dates and a broken coach field. Davis Cup rows from the ITF: IDs only, no scores or statistics. Flashscore daily boards for April–June 2026, with few fields |

## What the project holds that it lacks

* All WTA data.
* 2025–2026, the whole Polymarket period.
* Odds of any kind.
* Rankings.
* Grand Slam point-by-point.
* Women's charts, and charts from 2025–26.
* Tennis My Life.
* The official point feeds.

## Quality notes (observed)

* **Its notes are wrong in places:**
  * Tennis Abstract's `match_date` is the tournament start date: every Australian Open 2026 round is dated 2026-01-19.
  * The `itf_*` folders hold Davis Cup only, with no Futures.
  * One 961 MB file is a duplicate.
* **Head-to-head rows are rough.** Rows found by the crawling have country names in their score fields, and start and end timestamps that are equal.
* **Joining.** Infosys and Court Vision use ATP player codes and tournament IDs, as Tennis My Life does. Only the formats were checked, not a join.

## The download

* **Chunks.** Six, most predictive first. They are defined file by file in [plan.csv](../../../data/studies/atp_pipeline_handoff/plan.csv): 5,707 files and 150.53 GB, skipping the 56 identical Sackmann files and the duplicate.
* **How files are fetched.** Byte ranges from the pinned commit, gzipped as they arrive (one member per 256 MB range), each file checked against the Hub's hash, with resume from the last complete range. At most 5 requests a second to huggingface.co, and no account.
* **Tests.**
  * Seven offline tests in `test/atp_pipeline_handoff/` cover planning, hashing, rollback of a broken range, resume across runs, the kept-aside hash failure, stop on 404, and status.
  * A live smoke test downloaded five small files of each kind.
  * In a live crash test, the process was killed after 302 MB of the 941 MB `infosys_deep/2022_data.jsonl`. The rerun resumed at byte 301,989,888, fetched only the remaining 0.64 GB, and matched the Hub's SHA-256. The file is stored as 41.7 MB.
* **The run.** One run, `20260925T142547Z`, fetched the remaining 5,700 files from 14:25 to 15:23 UTC: 149.47 GB with 6,600 requests to huggingface.co.
  * There were no failures, no retries and no 429s.
  * The run averaged about 44 MB/s. The first 20 minutes were held to the request pace by Court Vision's 4,570 small files; after that it ran at about 55 MB/s.
* **Storage.** 150.53 GB takes 16.79 GB on disk, about 9 times smaller. Infosys shrinks about 22 times; Flashscore (126 GB to 14.2 GB) and the chart pages about 9–10 times. Court Vision was already gzip.
* **Standard tools read the files.** `gzip -t` passes, `gzip -dc | sha256sum` reproduces the Hub's hash, and pandas reads the `.gz` JSONL and CSV directly.
* **Backup.** The raw folder was zipped: 5,717 entries, with every entry's CRC checked. The zip was uploaded to cold storage on 25 Sep 2026 at `gs://tennis-predictions-archive/public_dump/tennis_atp_pipeline_handoff_raw_2026-09-25.zip` (Coldline, 16.7 GB, SHA-256 `bc7d1b49977d4c58f3f3cfe5f49f0f166370d64e2077e3b6593e7b9eb30e6c9f`).
  * The uploaded object's size and MD5 match the local zip.
  * Before upload, Windows `tar` listed all entries and restored a sample file whose hash matched the Hub's.

## Checks on chunk 1

Chunk 1 finished on 25 Sep 2026 with every file matching its hash. [`verify_chunk1.py`](../../../src/eda/atp_pipeline_handoff/verify_chunk1.py) then read the downloaded files ([checks.json](../../../data/studies/atp_pipeline_handoff/checks.json)).

**Infosys (`infosys_deep`).** Records equal the uploader's claimed totals in every year.

| Year | Matches | With point rows | With full outcomes | Points | Court Vision files |
|---|---:|---:|---:|---:|---:|
| 2018 | 10 | 0 | 0 | 0 | 14 |
| 2019 | 15 | 0 | 0 | 0 | 0 |
| 2021 | 1,549 | 813 (52%) | 148 | 117,692 | 298 |
| 2022 | 11,262 | 7,978 (71%) | 989 | 1,115,306 | 1,348 |
| 2023 | 12,017 | 8,447 (70%) | 1,312 | 1,182,596 | 791 |
| 2024 | 12,502 | 8,696 (70%) | 1,765 | 1,210,529 | 2,119 |
| Total | 37,355 | 25,934 (69%) | 4,214 | 3,626,123 | 4,570 |

* **Full outcomes** means at least one point labelled winner, forced error or unforced error. Other points are ace, double fault or unclassified.
* **Court Vision counts disagree slightly.** The Court Vision flag in the Infosys records (291, 1,452, 824 and 2,273 for 2021–24) differs a little from both the files present and the uploader's claims.

**Joining to Tennis My Life** on year, ATP tournament ID and the pair of ATP player codes:
* **Main draws:** 22,232 of the 23,466 main-draw matches of 2022–24 link (95%).
* **Qualifying:** only 2,430 of 12,273 link (20%), because Tennis My Life's qualifying files cover tour-level events only. About 9,800 Challenger qualifying matches of 2022–24 have Infosys data but no Tennis My Life row. Whether Sackmann's files hold them was not checked.

**Other folders:**

| Folder | Result |
|---|---|
| `court_vision` | 4,570 files (14 from 2018, 298 from 2021, 1,348 from 2022, 791 from 2023, 2,119 from 2024) |
| `mcp/charts` | 8,914 chart records |
| `api_tennis` | 136,946 fixture rows: 19,458 in 2021, 39,514 in 2022, 37,758 in 2023, 40,216 in 2024 |
| `tennis_abstract` | 553,359 player-match rows, 19,363 more than the uploader's progress files claim; 15,002 bios, as claimed |

## Checks on chunks 2–6

[`verify_chunks_2_6.py`](../../../src/eda/atp_pipeline_handoff/verify_chunks_2_6.py) read every Flashscore and Infosys file after the download ([checks_chunks_2_6.json](../../../data/studies/atp_pipeline_handoff/checks_chunks_2_6.json)).

**Flashscore: what the files hold.** 690,372 records in 148 files (102 in `flashscore_full`, 46 in `flashscore_gql_stats`), 566,853 distinct match IDs.

| Files | Records | Distinct matches | Start time | Statistics block | Winners and unforced errors |
|---|---:|---:|---:|---:|---:|
| Year files (ATP singles 122,848 records, Challenger singles 60,652; 1990 to 13 Apr 2025) | 183,500 | 162,594 | 100% | 22% | 6% |
| "Layer 3 recovered" files (2017–23, mostly Challenger; counted with the year files above) | 27,521 | | 0% | 0% | 0% |
| Statistics files (1990 to Dec 2024) | 47,401 | 45,950 (359 not in the year files) | 100% | 25% | 10% |
| Head-to-head passes (11 Dec 1989 to 17 Apr 2026) | 431,950 | 427,262 (403,900 found nowhere else) | 100% | 17% | 4% |

The uploader's progress files do not describe the Flashscore files reliably:
* **Year files.** Nine of them differ from their claimed counts, by −4,629 to +3,685 records.
* **Head-to-head files.** These hold slightly fewer records than claimed. Their counts are round hundreds, which suggests they were written in batches of 100 and the last batch of a pass was lost. Files with a claim hold 615,450 records against 620,229 claimed.

**Distinct Flashscore matches by year:**

| Year | All files | In the year files | Only in the head-to-head crawl |
|---|---:|---:|---:|
| Before 2010 | 122,297 | | |
| 2010 | 10,818 | 7,173 | 3,645 |
| 2011 | 17,834 | 8,175 | 9,659 |
| 2012 | 32,596 | 7,850 | 24,746 |
| 2013 | 23,236 | 7,932 | 15,304 |
| 2014 | 16,713 | 7,727 | 8,986 |
| 2015 | 17,319 | 7,552 | 9,767 |
| 2016 | 17,581 | 7,853 | 9,728 |
| 2017 | 16,234 | 3,554 | 12,649 |
| 2018 | 15,843 | 3,112 | 12,403 |
| 2019 | 17,443 | 3,375 | 14,068 |
| 2020 | 24,368 | 3,667 | 20,701 |
| 2021 | 29,920 | 7,973 | 21,947 |
| 2022 | 38,434 | 4,002 | 34,432 |
| 2023 | 45,059 | 8,910 | 36,149 |
| 2024 | 51,147 | 6,796 | 44,351 |
| 2025 | 55,279 | 49 | 55,230 |
| 2026 (to 17 Apr) | 14,732 | 0 | 14,732 |

**2025 to 17 April 2026, the part inside the Polymarket period.** The head-to-head records carry no tour label, so the classes below come from tournament names. The ITF classes are exact name prefixes (M15, W35 and so on); the rest are grouped roughly.

| Class | 2025 matches | With statistics | 2026 matches | With statistics |
|---|---:|---:|---:|---:|
| ITF men (M15, M25 …) | 19,167 | 13 | 4,278 | 1 |
| ITF women (W15, W35 …) | 19,465 | 24 | 4,055 | 10 |
| Grand Slams (either tour) | 2,151 | 1,511 | 551 | 393 |
| Other named events: ATP, WTA, Challenger, WTA 125, Billie Jean King Cup | 14,402 | 13,688 | 5,848 | 5,601 |
| Juniors | 94 | 0 | 0 | 0 |

**Infosys.**
* **The two folders overlap but differ.** `infosys_full` holds 37,835 matches and `infosys_deep` holds 37,355. 37,282 are in both, 553 only in `infosys_full`, and 73 only in `infosys_deep`. Both folders are therefore kept.
* **Court Vision** is embedded in 4,444 `infosys_full` records (1,197 in 2022, 867 in 2023 and 2,380 in 2024), against 4,570 per-match files in `court_vision/`.
* **An odd file.** `infosys_full/1970_data.jsonl` holds 14 records, presumably matches without a date.

## Not determined

* Completeness against the real tournament calendars.
* Which tour each head-to-head match belongs to, beyond the tournament-name classes above.
* Whether Sackmann's files hold the Challenger qualifying matches that Tennis My Life lacks.
