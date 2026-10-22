# WTA official box readers (subagent 1's report)

16 Oct 2026 · Written by subagent 1 for the lead; saved here by the lead because the harness refused the subagent's own write of this file. The text below is the subagent's report as returned, unedited apart from this header. The lead's re-checks are in the study's process log and README.

## Status
All five readers follow the contract and are on Stage 0's ids:

| Reader (`box/readers/`) | Rows / matches | Complete |
|---|---|---|
| `wta_api_box` (B3: tour, WTA 125, Finals) | 53,314 / 26,657 | 26,640 matches |
| `wta_api_slam_box` (B9) | 4,084 / 2,042 | 617 (only 2026 has data) |
| `wta_events_recount` (umpire event log, 2019–26) | 50,578 / 25,289 | 24,753 (97.9%) |
| `wta_pbp_recount` (B8 point-by-point, 2022–26) | 29,356 / 14,678 | 11,497 (78.3%) |
| `wta_events_tbfill_recount` (event-log recount, unwritten tiebreak winners filled from the point-by-point) | 50,578 / 25,289 | 2,634 filled |

The fill reader is not independent of either source. Rule 3: I used no live helper. At the end, the live Stage 0 files and the `wta_api` link file still match the manifest's SHA-256. The live data map has changed since the snapshot; none of my readers reads it.

## Answers

**Q1 coverage** (`wta_coverage.csv`, `wta_api_not_in_stage0.csv`)
- The box links 93–99% of Stage 0 women's tour, WTA 125 and qualifying matches in every season. The exception is the 2019 tour main draw at 68%: 15 editions have no match list.
- The event log covers 95–99% from 2020. In 2019 it covers 33–58%: logs are empty until April and bare (no server or score) until June.
- The point-by-point covers 47–99% in 2022–26.
- No WTA record covers a Slam except B9, and only its 2026 boxes hold data.
- The API also holds 1,951 played 2026 singles that Stage 0 lacks: 921 WTA 125 main draw, 324 WTA 125 qualifying, 367 tour qualifying, 338 Slam qualifying.

**Q2: does the event-log recount reproduce the box?** Nearly exactly. On 49,506 rows of complete recounts with a box:

| Count | Exact agreement |
|---|---|
| ace / df | 99.88% / 99.85% |
| svpt | 99.67% |
| first_in | 98.72% |
| first_won / second_won | 99.13% / 99.19% |
| sv_won | 99.68% |
| sv_gms | 99.83% |
| bp_faced / bp_saved | 99.74% / 99.73% |

Where they differ (`wta_three_way.csv`), the box and Stage 0 agree against the recount on first serves in 548 rows; the recount and Stage 0 agree against the box in 71. The first-serve differences cluster at 33 editions of 2021–26 (mostly 2022–24; worst is Ningbo 2023). Which record is right there is unknown. On the other counts the odd one out is balanced between the three sources.

The device's own first-serve flag is stale after corrections. Read with that flag, first serves agree with the box in only 88–95% of 2022–26 rows.

**Q3: the 2024–25 "short records" are the B9 Slam boxes.** All of 2024 (Roland Garros, US Open) and 2025 (all four Slams) are a match row of zeros with no set rows.
- Read as counts, they reproduce data continuity's figures: 89.1% and 82.9% equal serve points, mean −7.5 and −12.0, about −70 points where they differ.
- Without them the tour box agrees with Sackmann in 99.2% (2024) and 99.5% (2025).
- So neither record is short: the API's Slam box is empty, and the event log holds no Slam points at all.
- Separately, 33 tour matches of 2024 (65 player rows) have a garbled API match row where the event log and Stage 0 agree. That suggests (inference) Sackmann's women's counts don't come from these box documents (`wta_short_records.csv`).

**Q4: the service-game gap is a definition, and only at the Slams.**
- In the 2026 Slam boxes, `servgamesplayed` is service games *won*. It equals Stage 0's service games minus breaks in 1,234 of 1,234 rows.
- That explains the "9% of 2026 rows". Against tour boxes only, Sackmann-sourced 2026 rows agree in 99.90% and TML-sourced rows in 99.87%.
- At tour events the event log supports Sackmann's count: regular service games started, tiebreaks not counted, the game in progress at a retirement counted. The box equals that recount in 99.86% and Stage 0 in 99.91% of 49,014 rows.
- The box counts the in-progress game in 253/253 such retirement rows; Stage 0 in 227/253.
- Counting the tiebreak as a service game fits only 88%, so I rejected it (`wta_service_games.csv`).

**Q5: other systematic findings**
1. The 58 logs that record no serve numbers are mostly Brisbane, Canberra 125 and Auckland, first week of 2024 (53); the box still has plausible first serves for them (`wta_serve_number_missing.csv`).
2. From 2022, about 91% of tiebreak points are written "0-0". The log alone therefore gives no serve points won in 4,241 matches; the fill restores 2,634.
3. In 2019–21, second-serve foot faults are logged as `Foot`, and the box counts them as double faults (97/97 player rows).
4. 442 logs are missing point records. The 8 Melbourne Feb-2021 matches used a match tiebreak, which the engine doesn't replay.
5. Possible Stage 0 errors to pass on:
   - 2054/2021/LS001 (Columbus 125 final): the API listing and a log that reproduces its score both have Párrizas Díaz winning; Stage 0 has Xin Yu Wang. Winner and loser look swapped.
   - 1109/2024/LS011: Stage 0 has "6-3 6-2 RET", but the match was completed.
   - 18 identity splits in Stage 0, some named "DUPE …".

## Choices made after seeing results
- **First-serve rule:** a point counts as a second-serve point only if a first-serve fault record stands before it, with no Correction since. I chose this on 2024 after seeing that the device's flag gave 91.9% agreement with the box and this rule 97.8%. So first_in, first_won and second_won are calibrated to the box and are not a blind referee of it; the flag reading is kept as `x_first_in_flag` / `x_first_won_flag`.
- **sv_gms** now includes the game in progress at a retirement, because both the box and Stage 0 count it.
- **Corrections:** each correction edit is resolved as a whole, from the Correction to its closing InProgress record. I built this logic by tracing matches that failed. 10,170 of 10,239 edits resolved this way; 69 fell back to record-by-record. 2021 completeness rose from 48% to 98% once I read 2021's different match-score format.

## Checks
- **Hand checks** (seed 20261016, keys in every reader JSON and `wta_handcheck.json`): 31 matches, raw `.json.gz` documents opened and compared by eye with the reader rows. All counts and orientations matched, including the tricky Xinyu Wang / Xiyu Wang pairing, a Brisbane log with no serve numbers, a corrected point removed, and point-by-point totals.
- **Self-test:** 7 cases pass.
- **Orientation:** by names, with 410 links oriented on one name (married names) and 1 dropped. An id crosswalk agrees in 28,753 of 28,771 checkable links; the API's winner disagrees with Stage 0's in 1 link.

## Not done
- No Slam recount: the WTA API serves no Slam point data.
- 513 bare 2019 logs can't be recounted.
- 536 linked recounts are incomplete; their counts are in the files with `complete` False.
- The 1,951 non-Stage-0 matches aren't output, since the contract is on Stage 0's ids.

## Bugs in others' code (reported, not edited)
1. `data_continuity/sources.wta_api()` reads the B9 zero rows and the 2026 Slam "games won" field as counts. That is the source of the data-continuity README's §3.2 "short records" and its 2026 service-game claim.
2. `official_point_feeds/verify_wta.scoring_records()` misses the 190 second-serve `Foot` double faults in 2019–21 singles logs.
3. The official_point_feeds README says all B9 boxes "have data", but 2,850 of the 4,084 linked Slam rows are zeros.

Files are in `C:\Users\zerom\Documents\Tennis-predictions\`:
- code, `src\eda\source_reconciliation\`: wta_common.py, wta_api_box.py, wta_eventlog.py, wta_events_recount.py, wta_pbp_recount.py, wta_handcheck.py, wta_questions.py
- tables, `data\studies\source_reconciliation\box\`: wta_coverage.csv, wta_api_not_in_stage0.csv, wta_recount_vs_box.csv, wta_three_way.csv, wta_short_records.csv, wta_service_games.csv, wta_event_disagreement.csv, wta_serve_number_missing.csv, wta_questions.json, wta_handcheck.json
- readers, `data\studies\source_reconciliation\box\readers\`: the five `wta_*.parquet` files above, each with a `.json`
