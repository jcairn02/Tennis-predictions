# Serve-speed sources: evidence

Evidence for [docs/research/serve-speed-sources/](../../../docs/research/serve-speed-sources/README.md) (7 October 2026). The question: how much first-serve speed the project holds for the men's serve-speed-change feature of the [point-sequence study](../../../docs/studies/point_sequence/README.md), and where the rest could come from. Research only; nothing here is an approved source. No file here holds a match result, a raw third-party payload or a speed value: only counts.

## Local measurement

| File | What it is | Made by |
|---|---|---|
| [coverage_matches.csv](coverage_matches.csv) | Matches with both players' first serves timed, by tour × level × year: held (what the study used), with the files on disk the study did not read, and what each of those adds | `src/eda/serve_speed_sources/coverage.py` |
| [coverage_slam_editions.csv](coverage_slam_editions.csv) | The same for each Slam's main draw, by year | `coverage.py` |
| [coverage_feature.csv](coverage_feature.csv), [coverage_feature_by_year.csv](coverage_feature_by_year.csv) | The feature (both players timed in the previous 14 days) on the main-tour main draws, under six cumulative scenarios: held; + on disk; + ManTennisData (public GitHub, not held); + every ATP tour match of 2025–26 (ceiling for the encrypted files); + AO/RG 2025–26; + WTA tour 2025–26 | `coverage.py` |
| `coverage_feature_matches.parquet` (gitignored) | One row per frame match with each scenario's flag | `coverage.py` |
| [coverage_summary.json](coverage_summary.json) | Validation against `speed_build.py` (exact in all eight cells), the men's 2025–26 counts and power by scenario, the Polymarket window, Polymarket's volume by tier | `coverage.py` |
| [flashscore_crawl_events.csv](flashscore_crawl_events.csv) | Every event of 2024–26 in the Hugging Face handoff's Flashscore crawl: matches, with statistics, with "Average 1st serve speed" | `src/eda/serve_speed_sources/flashscore_crawl.py` |
| [flashscore_agreement.json](flashscore_agreement.json) | Flashscore's averages against the held official speeds (182 Slam matches; 14 Infosys) | `flashscore_crawl.py` |

Rerun (from the repository root):

```
./python.sh src/eda/serve_speed_sources/coverage.py --mantd DIR   # about 7 minutes
./python.sh src/eda/serve_speed_sources/flashscore_crawl.py       # about 4 minutes
./python.sh -m pytest test/serve_speed_sources -q
```

**About `--mantd DIR`.** `DIR` must hold `atp/matches_2021.csv` … `matches_2026.csv` and `tournaments.csv` of [`msolonskyi/ManTennisData`](https://github.com/msolonskyi/ManTennisData).
* The published figures used commit `4e2d39f99e` (4 Oct 2026), read from lane B's scratch copy.
* The project does not hold this dataset.
* Without the flag, the ManTennisData scenario equals the one before it.

**Placeholders.** Flashscore prints "0 km/h" where it has no reading, so every speed outside 40–270 km/h counts as missing.

Both scripts read Stage 0 (`predictability_diagnostic/stage0_matches.parquet`) without its result columns, the clock (`match_timing/timing.parquet`), the shot-level study's per-match speeds and link table, the Hugging Face handoff's raw Infosys and Flashscore files, the Australian Open match centre's statistics, the match-timing study's Flashscore links and Polymarket's event index. The walk-forward frame is read only to 2024, for the validation.

## Research lanes

Notes from the four lanes run on 7 October 2026, each with its own method, evidence labels, probe log and dead ends, are in [research_notes/](research_notes/):

| Lane | File | Main finding |
|---|---|---|
| A1: public sources for ATP and WTA tour-level events | [A1_tour_public.md](research_notes/A1_tour_public.md) | No official plain source outside the Slams; the ATP's rules time every court from 2025, the WTA's from 2026; Flashscore sporadic |
| A2: the Slam gaps (AO 2025, RG 2025–26) and ESPN | [A2_slams_and_espn.md](research_notes/A2_slams_and_espn.md) | Only the Slams' encrypted Infosys files hold AO 2025 and RG 2025–26; ESPN has no tennis statistics; Wimbledon's outside courts were never measured before 2025 |
| B: open datasets, repositories and archives | [B_open_datasets.md](research_notes/B_open_datasets.md) | `msolonskyi/ManTennisData`: the ATP Stats Centre's per-match speeds as weekly CSV, October 2021 onward |
| C: paid vendors and how to contact them | [C_paid_vendors.md](research_notes/C_paid_vendors.md) | No vendor sells a non-Slam archive publicly; holders TDI, SMT/IDS, Hawk-Eye, the WTA and Stats Perform; contact table and draft email |
