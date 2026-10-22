# Third-party box readers (subagent 3's report)

16 Oct 2026 · Written by subagent 3 for the lead; saved here by the lead because the harness refused the subagent's own write of this file. The text below is the subagent's report as returned, unedited apart from this header. The lead's re-checks are in the study's process log and README.

I built six of the brief's seven readers and the tables for Q1–Q3. The ITF one was not built. All six raw-document hand checks passed for each reader, and every contract check passed.

## What was built

| Reader | Family | Kind | Matches | Complete | Men / women |
|---|---|---|---:|---:|---|
| `tp_sofascore_box` (period ALL) | sofascore | box | 37,249 | 24,005 | 29,332 / 7,917 |
| `tp_sofascore_setbox` (sum of the per-set periods) | sofascore | box | 23,943 | 23,933 | 22,568 / 1,375 |
| `tp_sofascore_recount` | sofascore | recount | 48,167 | 40,936 | 41,391 / 6,776 |
| `tp_tennislive_stats` | tennislive | box | 38,612 | 38,576 | 34,934 / 3,678 |
| `tp_atp_scraped` | atp_official | box | 140,378 | 140,378 | men only |
| `tp_flashscore_stats` | flashscore | box | 36,960 | 34,141 | men only |
| `tp_mcp_recount` | mcp | recount | 9,128 | 8,058 | 5,417 / 3,711 |

- **Not built: `tp_itf_live`.** Stage 0's ITF rows end with tournament date 1 Jun 2026; the ITF capture starts 15 Sep 2026. A reader on Stage 0's ids would be empty.
- **I added `tp_sofascore_setbox`,** which the brief did not ask for. Q2 showed SofaScore's own per-set statistics are sound where its match totals are not.
- **Not a reader:** `box/readers/tp_sofascore_games.parquet` (one row per recounted game). Exclude it from any glob over the readers.

## Q2: SofaScore's box against its own recount (observed)

On complete recounts:

| Count | ALL box = recount | Set-sum box = recount |
|---|---:|---:|
| Serve points | 79.5% | 99.3% |
| Points won | 88.1% | 99.5% |
| Service games | 99.5% | 99.6% |
| Break points faced | 73.7% | 99.7% |
| Break points saved | 77.6% | 99.65% |

- **The recount** equals Stage 0 on serve points 99.0%, points won 99.2%, service games 99.8% and break points 99.4%. Its winner agrees with Stage 0 in 78,534 of 78,534 rows.
- **Break points "fewer from 2025" are a defect, not a definition.** In Dec 2024 – Aug 2025 and Feb – Jun 2026, SofaScore's ALL totals are not the sum of its own set periods. In those months the ALL conversions fall below the games actually broken in 24.7% and 41.6% of men's rows, which no definition allows. The set sums equal the recount in 99.7–99.8% of rows in every period. The cause is unknown.
- **First serves "+0.4–0.7" have two layers.**
  - (a) ALL differs from the set sums in about half the rows from 2025: +0.29 per player in 2025, but −0.3 to −0.9 in 2020–24.
  - (b) The set sums themselves exceed Stage 0: men's Slams +5.0, women's Slams +2.5, WTA 125 +3.5, men's Challengers only +0.10.
  - Where serve points agree, the surplus "first serves" are won at 52% (men) and 48% (women), second-serve rates. Inference: second serves booked as first. SofaScore's points carry no serve number, so this rests on the win-rate test.
- **Two quirks of SofaScore's points:**
  - **Last points not listed.** A non-tiebreak game's last point is never listed, so aces and double faults are given as lower and upper bounds only.
  - **Tiebreak server.** The `serving` field is not the tiebreak's first server; the normal serve rotation fits 6,463 of 6,479 aces.
- **Not reproduced:** the data-continuity finding of 6% self-contradicting 2025 records. On the current files it is 0.01%, cause unknown.

## Q3: Flashscore and the ATP-site scrape before 2019 (men's Slams and tour main draws)

- **Coverage, 2013–2018:** Stage 0 has 15,789 matches. The scrape covers 14,946 (94.7%), Flashscore 4,643 (29.4%, mostly 2017–18), both 4,267. Neither has women's statistics.
- **The scrape is not independent.** It equals Stage 0 in 99.9%+ of tour-level rows (100% in 2010–12): inference, the same atptour.com numbers Sackmann's files carry. Its differences sit at the Slams: service games 91.8% equal, first serves 94.8%.
- **Flashscore** agrees with Stage 0 in 98.3–99.4% per count once its defective pages are flagged. On 8,520 rows held by all three:
  - where Flashscore differs from Stage 0, the scrape sides with Stage 0 in 33–138 rows per count;
  - Flashscore and the scrape agree against Stage 0 on 2–8 rows per count, except service games: 61 rows (34 matches, 44 rows from the US Open 2017, all ±1). These are candidates for a Slam-feed referee.
- **Verdict:** neither referees Sackmann's 2013–2018 rows broadly. The scrape is a transcription check; Flashscore is a partial, weak second opinion.

## Q1 (by tour, level and season): `box/tp_coverage.csv`

## Defects found in shared code or sources (reported, not fixed)

1. **`data_continuity/sources.sofascore()`** reads period ALL, so its consumers inherit the defect above: `referees.py`, and `candidate_stage0.py`'s SofaScore loader. I did not check whether any accepted package took SofaScore box scores from the affected months. It also keeps the first collection listing an event, and so misses 457 events whose statistics exist only in the Slam collection.
2. **TennisLive's `winner_id`** names the retiring player at retirements (85 matches; all 170 disagreeing rows are retirements). `candidate_stage0`'s 45%-of-points swap rule reads it.
3. **Flashscore pages:**
   - 638 placeholder "0/0" blocks, blanked;
   - 3,111 rows from 2012–13 pages that file every serve point as a first serve: the split is blanked, raw values kept;
   - 639 pages whose games won contradict the score (70 are the two sides' statistics exchanged), marked not complete.
4. **Stage 0 holds no men's Challenger qualifying before 2016;** the scrape has about 3,900 such box scores a year in 2010–15.

## Checks

- **Hand checks:** six per reader against the raw documents, recorded in each JSON under `hand_check`; all 42 passed. One MCP chart was also recounted from the raw strings with independent minimal rules, with identical results.
- **MCP parser** equals MCP's own Overview totals in 99.6–99.99% of rows on complete charts.
- **Winner checks:** 0 disagreements on complete recounts.
- **Rule 3:** no helper read the live Stage 0. The live Stage 0 and all live link files still match the manifest; only `data_map/matches.parquet` changed, and I don't read it.

## Files

Paths are relative to `C:\Users\zerom\Documents\Tennis-predictions\`.

- **Readers:** `data\studies\source_reconciliation\box\readers\tp_*.parquet` and `.json`. The JSON holds inputs with SHA-256, link and drop counts, checks and the hand-check verdict.
- **Tables** (`data\studies\source_reconciliation\box\`): `tp_coverage.csv`, `tp_sofascore_q2_{counts,months,aces,first_serves,bp}.csv`, `tp_q3_{pre2019,agreement,second_opinion}.csv`, `tp_tables.json`.
- **Code** (`src\eda\source_reconciliation\`): `tp_common.py`, `tp_sofascore.py`, `tp_mcp.py`, `tp_atp_scraped.py`, `tp_flashscore.py`, `tp_tennislive.py`, `tp_tables.py`, `tp_handcheck.py`. The whole set runs in about 8 minutes.
