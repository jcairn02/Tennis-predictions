# R3 build: the speed-data engineer (agent 1)

7 October 2026. Built C1 (the panel), C2 (as-of offsets) and C4 (the frame join) of `2_audit.md`, with the fixed API, plus tests T-P1 to T-P8. All numbers are **observed**. No result column is read, 2024–26 is looked at only as values and counts, and there is no new statistic-target look and no GPU use.

## What was built

* **Code:** `src/eda/serve_speed_tabpfn/panel.py`.
  * `./python.sh src/eda/serve_speed_tabpfn/panel.py` takes 27 s, plus 50 s on the first run to parse the handoff.
  * It implements the API as specified.
* **Outputs** in `data/studies/serve_speed_tabpfn/`:
  * `speed_panel.parquet`: 43,089 player-matches, 42,900 with `use`;
  * `speed_records.parquet`: 70,805 timed source records, each with its validity;
  * `frame_keys.parquet`: 63,737 matches;
  * `offsets_snapshots.parquet` and `.json`: the frame's `es` days, men 3,458 and women 3,650;
  * `panel_summary.json`.
* **Choice** (ruling Q2). Use rows by chosen source:
  * Men: ManTennisData 19,707, handoff 370, Infosys points 15, SirGenkii 21, Slam point feeds 11,362, AO match centre 474.
  * Women: Slam point feeds 10,473, AO match centre 478.
  * The non-Slam basis is the key statistic every season (ks / points): 2022 3,095 / 3; 2025 3,420 / 21; 2026 4,230 / 0.
* **Drops** (`use = False`), 189 rows:

  | Reason | Rows |
  |---|---:|
  | gate | 70 |
  | low_n | 57 |
  | implausible | 30 (27 ManTennisData values of 54–119 km/h) |
  | mislink_level | 14 |
  | mislink_round | 12 |
  | ks_duplicate | 4 |
  | mc_duplicate | 2 |

  * Records rejected as candidates: `mislink_round` 54 (the 10 QF among them), `ks_duplicate` 56.
  * 425 rows flagged `flag_own_outlier` (flag only).
* **Families:** `ch|M` 1,238 and `ch|Q` 156, which is the E7 fix.

**Use rows by tour, year, Slam / non-Slam:**

| Year | Men non-Slam | Men Slam | Women Slam |
|---|---:|---:|---:|
| 2011, 2014–20 (per year) | 0 (17 in 2018) | 490–692 | 499–688 |
| 2021 | 603 | 838 | 826 |
| 2022 | 3,098 | 879 | 871 |
| 2023 | 3,765 | 827 | 813 |
| 2024 | 4,959 | 852 | 842 |
| 2025 | 3,441 | 1,735 | 1,757 |
| 2026 | 4,230 | 1,893 | 1,235 |

* Women have no non-Slam rows.

**Frame matches with both sides holding a 14-day row:**

| | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|
| Men | 1,141 | 1,289 | 1,632 | 1,312 | 930 |
| Women | 192 | 176 | 184 | 281 | 213 |

## Tests

`./python.sh -m pytest test/serve_speed_tabpfn/test_ssp_panel.py -q`: **10 passed** (13 s).

| Test | Result |
|---|---|
| T-P1 | One row per (match_id, side). No column list or output names a result |
| T-P2 | slam_pbp − slamtracker: sd 0.041 (2,871). ManTennisData = handoff on 99.98% of 11,601 |
| T-P3 | KS = ceil(point mean) on 81.5% of 1,439 complete tables ≤ 2023 |
| T-P4 | All 48 cells within tolerance of N2; largest difference 3 |
| T-P5 | All 10 QF → non-QF records are `mislink_round`; no use row carries one. `draw` is never read |
| T-P6 | AO 2026: 474 men, 474 women |
| T-P7 | 25 cut days inside timed events: γ̂ at C, C−1, C−7 and C−100 is identical after noising every row with es > C. Leaky control (rows admitted by tournament start) moved 25 of 25 cuts, median 1.86 km/h |
| T-P8 | 63,737 matches, one to one. 21 `flipped`, 67 other conflicts, 88 `id_conflict` (all women's 2026). Sides follow the pre-rebuild ids; 40 re-keyed ids resolved |
| API | Integer clock with es ≤ obs ≤ lf; the tier rule; exact shifts. `at()` covers every edition, with family-mean or 0 fallbacks; the cache equals a fresh fit to 1e-12 |

## Deviations, with reasons

1. **Records rejected for a link problem** (a mislink, a conflicting duplicate) are not candidates, so the player-match takes its next valid record.
   * 55 use rows: their own ManTennisData record 38, the handoff copy 16, RG points 2.
   * None falls from a key statistic to points outside the Slams.
   * Value drops (implausible, n < 10, no clock) never fall back, as the basis ruling requires.
2. **An added `mislink_level` check:** a Slam feed on a non-Slam match or an ATP-tour feed on a Slam (14 records, e.g. SlamTracker on a WTA São Paulo 2026 match). It applies the same in every season.
3. **The round check precedes the duplicate check,** so a mislink no longer voids the match's own record. ManTennisData's conflicting duplicates fall from 45 keys to 10.
4. **`obs` is floored to integer days** (the API asks for integers): 1,100 panel rows and 3,889 frame matches held half-days. Floor keeps es ≤ obs ≤ lf; `obs_raw` keeps the original.
5. **Gate-only rows** stay with `use = False` (`gate`, 70).
6. **`id_conflict` marks all 88** (Q6), and `flipped` marks the 21.
7. **Optional keywords on `EditionOffsets`:**
   * `cache`: read only when the tour's use rows match the stored fingerprint, so a probe always refits;
   * `release`: default lf + 1; `"tdate"` exists only for the leaky control.
8. **Extra columns:** `source_key`, `kind`, `y_raw`, `spd1_pts` / `spd1_ks`, `alt_sources`, `max_alt_diff`, `spd2`, `spd_max`, `fault1`, `lgroup`, `event`.

## Disagreements (recorded, not contested)

* **Basis.** Point means remain the better measurement where both exist. The audit's own +5.86 km/h² [+0.25, +14.47] (points better) shows it.
  * Under ks-first, 27 broken ManTennisData values are dropped rather than replaced.
  * The 4–7.5% key-statistic tail stays in training and test alike. I accept the consistency argument; the robust filter must carry it.
* **The AO 2026 +0.5 floor** rests on 10 player-matches. AO 2026's own as-of offset absorbs any constant error.
