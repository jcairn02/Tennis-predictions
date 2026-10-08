# Download status: `atlas-polybot/atp-pipeline-handoff`

Generated 2026-09-25T17:13:01+00:00 by `./python.sh -m src.ingest.public_dump.atp_pipeline_handoff status` (also rewritten every minute while a fetch runs). Pinned commit `ea3d94d79f5d9e9b4bead031e2c6262f91a86c35`. What the chunks are and how to resume: [README.md](README.md).

**5,707 of 5,707 files done (150.53 of 150.53 GB); 0 files and 0.00 GB left.** Done files take 16.79 GB on disk. 0 file(s) part-way, 0 with an error in their latest attempt.

| Chunk | Content | Files done / planned | GB done / planned | GB left | State |
|---:|---|---:|---:|---:|---|
| 1 | Everything outside the large Flashscore and infosys_full files: Infosys point data 2021-24, Court Vision tracking, ATP per-set and season-to-date statistics, Tennis Abstract chart and player pages, api-tennis fixtures, ATP profiles, Davis Cup, pre-2010 Sackmann files, the dump's progress files | 5,552 / 5,552 | 6.25 / 6.25 | 0.00 | done |
| 2 | infosys_full: Infosys match files with Court Vision embedded, 2021-24 | 7 / 7 | 7.01 / 7.01 | 0.00 | done |
| 3 | flashscore_gql_stats: Flashscore statistics with winners, unforced errors and net points | 46 / 46 | 11.22 / 11.22 | 0.00 | done |
| 4 | flashscore_full match files 2010-2024 (with Challenger 2010-11 and early 2025) | 21 / 21 | 24.84 / 24.84 | 0.00 | done |
| 5 | flashscore_full match files 1990-2009 (with Challenger 2008-09) | 23 / 23 | 18.51 / 18.51 | 0.00 | done |
| 6 | flashscore_full head-to-head crawl passes | 58 / 58 | 82.69 / 82.69 | 0.00 | done |

| Source folder | Files done / planned | GB done / planned | GB on disk |
|---|---:|---:|---:|
| `_repo_root` | 2 / 2 | 0.00 / 0.00 | 0.00 |
| `api_tennis` | 5 / 5 | 0.05 / 0.05 | 0.01 |
| `atp_player_scrape` | 20 / 20 | 0.00 / 0.00 | 0.00 |
| `atp_scraped` | 104 / 104 | 0.04 / 0.04 | 0.04 |
| `atp_scraped_enriched` | 50 / 50 | 0.83 / 0.83 | 0.05 |
| `court_vision` | 4,570 / 4,570 | 0.34 / 0.34 | 0.34 |
| `flashscore_bruteforce` | 10 / 10 | 0.04 / 0.04 | 0.00 |
| `flashscore_daily` | 7 / 7 | 0.02 / 0.02 | 0.00 |
| `flashscore_data` | 28 / 28 | 0.03 / 0.03 | 0.01 |
| `flashscore_full` | 261 / 261 | 126.05 / 126.05 | 14.23 |
| `flashscore_gql_stats` | 46 / 46 | 11.22 / 11.22 | 1.23 |
| `infosys_deep` | 15 / 15 | 3.11 / 3.11 | 0.14 |
| `infosys_full` | 7 / 7 | 7.01 / 7.01 | 0.50 |
| `itf_full` | 136 / 136 | 0.02 / 0.02 | 0.02 |
| `itf_scraped` | 136 / 136 | 0.02 / 0.02 | 0.02 |
| `mcp` | 59 / 59 | 0.93 / 0.93 | 0.09 |
| `tennis_abstract` | 146 / 146 | 0.71 / 0.71 | 0.06 |
| `tennis_atp` | 105 / 105 | 0.10 / 0.10 | 0.05 |

Not planned for download: 1 skip-duplicate, 56 skip-held (reasons per file in [plan.csv](plan.csv)).

Last run `20260925T142547Z` ended 2026-09-25T15:22:58+00:00: 5700 files done, 0 failed, 149.47 GB received; stopped because: it finished its list.

Resume (skips finished files, continues part-way ones from their last complete range):

```
./python.sh -m src.ingest.public_dump.atp_pipeline_handoff fetch
```
