# Lane A: Slam Hawk-Eye copies and women's charts (29 Sep 2026)

**Compiled by the lead session.** Lane A's agent wrote its tables, then stalled; it was stopped at 12:40 local time without writing this report. It was stopped while revising how its replay records gaps set by set. These notes summarise its tables as they stood (written 10:51-11:10). The lead then added its own checks, marked **[lead]**: an independent replay of a sample, the Tennis Abstract pages, and the chart index.

**Gaps covered:** `slam_points_ao_rg` (AO and RG point by point, 2022-2026) and `women_shots` (shot data for women's matches at the Slams, Finals and WTA 1000/500/250, 2018-2026).

**Evidence labels:** **observed** (read in the files downloaded here), **inference**, **not determined**.

## Bottom line

* **`hawkilol/tennisSlamBallTracking` holds what the card says, for 2022-24 only.**
  * *Complete records:* 745 of the AO/RG gap's matches have a complete point record that replays to the official score, and 552 of those carry ball tracking. AO 2022-24 is nearly complete; RG 2022 is partial, and RG 2023-24 thin. There is nothing for 2025-26.
  * *Independent check [lead]:* separate code replays 40 of 40 sampled "complete" gap matches to the official score.
* **Women's tracking:** the same copy holds 621 women's AO and RG matches of the `women_shots` gap with ball tracking (2019-24).
* **Women's website-only Tennis Abstract charts:**
  * *In scope:* 2,282 are dated 2018-26, and 2,061 of them link to matches of the `women_shots` gap.
  * *In the Hugging Face copy:* 1,467 of the 2,061 (`ramizheman/TennisNLData`, commit `9a1fc64`); 594 are only on the website.
  * *Contents [lead]:* both the website pages and the Hugging Face files carry the full shot-by-shot point log.
* **`ryurko/hawkeye` adds nothing for 2022+.** It covers RG 2019-21 and AO 2020-21 only.

## A1. hawkilol/tennisSlamBallTracking

* **Source [observed].** https://github.com/hawkilol/tennisSlamBallTracking at commit `f97a9b31e64eab8485474398414dd26523871f64`, fetched 29 Sep 2026 17:29 UTC.
  * *Files:* 2,035 files (169.9 MB): the match catalogues and 2,027 processed per-point CSVs. Git blob hashes match the tree.
  * *Raw JSON:* the 3.3 GB of raw JSON was not downloaded.
  * *Where:* `data/raw/gap_sources/hawkilol/` (gitignored), with the receipt `_receipt_f97a9b3.json`. Script: `src/eda/gap_sources/fetch_hawkilol.py`.
* **Catalogue [observed].** 2,027 singles matches: AO 2020-24 (124-127 per draw per year) and RG 2019-24 (41-113 per draw). Status: 1,852 completed, 137 incomplete ("I"), 38 retired.
* **Replay [observed; `hawkilol_matches.py`].**
  * *How:* a point's final row (its highest serve number) gives the point; the rows are replayed into games and sets and compared with Sackmann's official score.
  * *Result:* 1,836 matches complete, 41 with the score right but gaps, 137 partial (the "I" matches), 10 with gaps and a different score, 2 with tie-break points differing, 1 mismatch.
  * *Tracking:* 1,656 matches have tracking on at least 90% of their points. At RG the share falls off by year: the median match of RG 2024 has tracking on 45% of its points.
* **Independent check [lead; `hawkilol_spotcheck.py`].** 40 matches were drawn (seed 20260929) from those labelled complete in the AO/RG gap of 2022-24. For each, separate code takes every game's winner from its last point row and compares each set's games with the official set: 40 of 40 agree. See [hawkilol_spotcheck.csv](../hawkilol_spotcheck.csv).
* **The AO/RG gap, 2022-24 [observed].** Complete point records, with tracking in brackets:

  | Year | AO men | AO women | RG men | RG women |
  |---|---|---|---|---|
  | 2022 | 83 of 89 (81) | 106 of 108 (104) | 79 of 96 (29) | 75 of 104 (24) |
  | 2023 | 58 of 60 (58) | 62 of 63 (62) | 30 of 90 (9) | 48 of 109 (20) |
  | 2024 | 71 of 75 (71) | 94 of 94 (94) | 15 of 82 (0) | 24 of 93 (0) |

  * *Totals:* 745 complete, 552 with tracking.
  * *Not covered:* AO 2025-26 and RG 2025-26 have nothing.
  * *Outside the gap:* 418 more matches of 2022-24 are in the copy but already have point or shot data on the map (charts, Wayback captures). For them the copy adds tracking.
* **Fields [observed; see the 24 Sep notes, `granular_data_leads/research_notes/D_open_datasets.md`, L1].** The per-point CSV has 64 columns, including:
  * server and point winner, serve number, serve speed and type;
  * rally length, point-end type (winner, forced or unforced error, ace, double fault), error type and last stroke;
  * serve, return and last-shot 3-D positions, and spin.

  The raw JSON adds a hit/peak/net/bounce position for every stroke.
* **Licence [observed]:** GPL-3.0 on the repository (code); no data licence.

## A2. ryurko/hawkeye

* **Source [observed].** https://github.com/ryurko/hawkeye at commit `981c812` (July 2021). Its README says "over 800 matches … from the 2019, 2020, 2021 Roland Garros and 2020, 2021 Australian Open". The tree has play-by-play and ball-trajectory files for 2019 (88), 2020 (351) and 2021 (366).
* **For these gaps:** nothing for 2022-26. For women's matches of 2019-21 it overlaps the hawkilol copy [inference from the event lists]. Only the README and the tree were read, not the data files.

## A3. Other AO/RG point data for 2022-26

* This lane's search was not reported before it stopped.
* **What the other checks found:**
  * Lane B's searches (Kaggle, GitHub, Hugging Face, Zenodo) found only the Kaggle SofaScore scrape `marcosjn2`. Of the AO/RG main-draw matches of 2022-25 it holds 1,793; 1,777 replay complete. By this lane's link rules, 1,216 of them are gap matches (`marcosjn2_ao_rg_summary.json`); by lane B's, 1,242.
  * The 24 Sep search (`D_open_datasets.md`) found no other copy either.
* **Status:** [not determined beyond those searches].

## A4. Women's shot-by-shot

* **The Hugging Face copy [observed].** `ramizheman/TennisNLData`, commit `9a1fc64da03bcc2abccd80d9d2d32389a4adcf81`: 9,256 JSON files (1.38 GB); only the file list and one sample file were downloaded.
  * *Contents:* 9,179 distinct chart ids, 4,216 of them women's.
  * *Website-only charts:* 3,053 are website-only charts, 1,945 of them women's.
  * *Unmapped:* two file names do not map to a chart id.
* **What a file holds [lead, observed on the sample `samples/2019_sample.json`, the 1990 Roland Garros women's final].**
  * *Match:* date, event, players, tour, URL and charter.
  * *Scraped page:* the point-log rows and the stat tables.
  * *Narrative:* a "transformed" text with every point: server, score, and every shot with its direction, depth and outcome (286 points).
* **The women's website-only charts of 2018-26 [observed; `women_charts.py`, `women_charts.csv`].**
  * *Totals:* 2,282 charts; 1,577 of them are in the Hugging Face copy.
  * *In the gap:* 2,061 link to a match of the `women_shots` gap (none of those matches was already at shot level on the map), and 1,467 of those are in the copy.
  * *By level (gap-linked):* GS 655, WTA 1000 497, 500 320, 250 498, Finals 91.

  | Year | Website-only | In the gap | Of which in the HF copy |
  |---|---:|---:|---:|
  | 2018 | 330 | 298 | 162 |
  | 2019 | 415 | 377 | 237 |
  | 2020 | 155 | 137 | 98 |
  | 2021 | 249 | 219 | 176 |
  | 2022 | 233 | 216 | 171 |
  | 2023 | 336 | 307 | 250 |
  | 2024 | 214 | 193 | 173 |
  | 2025 | 214 | 183 | 161 |
  | 2026 | 136 | 131 | 39 |

* **The website pages [lead; `ta_chart_pages.py`, 29 Sep 2026].** Three gap-linked women's charts that the Hugging Face copy lacks were fetched: Auckland 2019 final, Hobart 2023 semi-final and Brisbane 2026 semi-final. Each page's `pointlog` holds 170, 146 and 142 point rows, every shot spelled out ("1st serve wide; forehand return down the middle (very deep); backhand crosscourt …").
* **The chart index [lead].** It now lists 18,284 charts, against 18,262 on 23 Sep. That includes 5 more women's charts of 2018-26 (US Open 2026 and the 2026 BJK Cup Finals). The charting continues.

## A5. Women's tracking

* **hawkilol [observed].** The copy holds 621 women's AO and RG matches of the `women_shots` gap with ball tracking: 2019 18, 2020 122, 2021 154, 2022 146, 2023 84, 2024 97. 554 of them also have a complete point record.
* **No other public tracking of WTA matches** was found by the 24 Sep research, and none by this check [not determined beyond those searches].

## Files

* **Tables:** [hawkilol_matches.csv](../hawkilol_matches.csv), [hawkilol_summary.json](../hawkilol_summary.json), [women_charts.csv](../women_charts.csv), [women_charts_summary.json](../women_charts_summary.json), [marcosjn2_ao_rg_summary.json](../marcosjn2_ao_rg_summary.json).
* **The lead's checks:** [hawkilol_spotcheck.csv](../hawkilol_spotcheck.csv), [ta_chart_pages.json](../ta_chart_pages.json).
* **Scripts** (`src/eda/gap_sources/`): `fetch_hawkilol.py`, `hawkilol_matches.py`, `women_charts.py`, `marcosjn2_slams.py`; the lead's `hawkilol_spotcheck.py` and `ta_chart_pages.py`.
* **Raw** (gitignored): `data/raw/gap_sources/hawkilol/`, `ryurko/`, `ramizheman/` (API answers and one sample file), `tennisabstract/` (3 chart pages and the index, with receipts).
