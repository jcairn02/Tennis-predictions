# Lower-level evidence review: scenario_p7 against reference_2026-10-08

Generated 2026-10-09T16:45:18Z by `src/eda/lower_level_evidence/refresh.py`. Shares are in points (percentage points of the evidence that is lower-level); + = more lower-level evidence than in the base run.

**A construction, not new data:** the base run's own preview of the ITF box scores of 2018-2024 (`itf_p7_scenario.csv`, column `box_lower_share_p7`) fed in as a candidate's box-score shares. It shows what the flags will read when that data is wired in.

**4 flags.** Read MISSING, UNEVEN DOSE and NEW LEVEL first: they decide whether a candidate built on this Stage 0 needs the level-aware treatment before `compare.py`.

## UNEVEN DOSE (4)

| where | moved_seasons | unmoved_seasons | largest_change_points |
|---|---|---|---|
| wta\|365d | [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025] | [2013, 2014, 2015, 2016, 2017, 2026] | 13.7 |
| wta\|h13w | [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025] | [2013, 2014, 2015, 2016, 2017, 2026] | 12.1 |
| wta\|h2w | [2018, 2019, 2020, 2021, 2022, 2023, 2024] | [2013, 2014, 2015, 2016, 2017, 2025, 2026] | 6.2 |
| wta\|h52w | [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026] | [2013, 2014, 2015, 2016, 2017] | 15.5 |
