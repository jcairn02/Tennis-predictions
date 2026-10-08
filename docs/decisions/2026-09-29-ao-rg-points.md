# Obtain the Australian Open and Roland Garros point data of 2022–2026

**Asked for by the owner on 29 September 2026.** SofaScore's part was deferred by the owner the same day and resumed at the owner's request on 30 September. Recorded on 29 September; updated on 30 September.

## Decision

Obtain the data the [gap-sources research](../research/gap-sources/README.md#the-proposed-list) proposes for the data map's gap "Roland Garros and Australian Open point by point, 2022–2026" (`slam_points_ao_rg`, 1,636 matches), and put it in the appropriate place in `data/`. The owner quoted the research's row: SofaScore first, then the Hawk-Eye copy (2022–24); "SofaScore lists 1,529 of 1,530 checked; the Hawk-Eye copy adds 745 complete records, 552 with ball tracking".

| Order | Source | Status |
|---|---|---|
| 1 | SofaScore | **Deferred on 29 September, collected on 30 September.** See below |
| 2 | Hawk-Eye Court Vision copy [`hawkilol/tennisSlamBallTracking`](https://github.com/hawkilol/tennisSlamBallTracking), commit `f97a9b3` | **Downloaded and staged on 29 September** |

**SofaScore, 29 September: deferred.** SofaScore refused the plain client (HTTP 403 "challenge") from 17:54 UTC, and again at 21:32 UTC. Claude offered three routes: the adapter's browser mode (a Chrome window with a debugging port, as on 24 September), a wait for the block to lift, or a skip. The owner chose "Skip SofaScore for now". That option said the adapter, links and commands would be left ready to run.

**SofaScore, 30 September: collected.**
* *The request:* the owner said "lets do the sofa score half now".
* *The route:* the plain client was still refused at 04:15 UTC, so the requests ran in the adapter's browser mode. Claude opened the Chrome window with the documented command (a blank profile, debugging port 9222), the route of 24 September. The other Claude session, which collects the ATP gap from the same address, held its SofaScore run meanwhile.
* *The first run:* it gave 1,089 of the gap's matches SofaScore's record, every played match among them that the Hawk-Eye copy does not record completely. At 05:15 UTC the hourly token's renewal showed a check that wanted a click. It was left for a person to click, as the collection rules require; nothing solves a check by program. The run was stopped at 06:00 with 543 matches not asked, every one with a complete Hawk-Eye record.
* *The second run:* offered the choice between finishing these 543 and the other session's ATP-gap run, the owner said "do yours". It fetched the 543 from 14:26 to 14:55 UTC, and the site's check passed without a click. SofaScore now holds all 1,632 played matches of the gap.

**Scope taken for the Hawk-Eye copy (Claude's reading, not the owner's words).** The whole repository's catalogue and per-point CSVs (2,027 matches, 2019–2024; 163 MB), and the per-stroke tracking JSON of the years the row names, 2022–2024 (1,225 matches; 2.08 GB, 104 MB gzipped). The per-point CSVs keep only the serve, return and last shot's positions; the stroke-by-stroke tracking is in the JSON alone. The JSON of 2019–2021 (802 matches, 1.16 GB, outside the gap's years) was not fetched; `--json-years all` fetches it.

**Basis.**
* *The Hawk-Eye copy:* a public GitHub repository. Its code is GPL-3.0 and its data carry no licence; its author scraped the files from the two Slams' Court Vision feeds. The owner accepted third-party copies of that kind of data for the Hugging Face dump on [25 September](2026-09-25-atp-pipeline-handoff.md). The project decrypts nothing.
* *SofaScore:* the owner's decision of 23 September 2026 to collect regardless of its terms, for non-commercial research ([point- and shot-level sources](../studies/point_shot_sources/README.md#direct-download-24-september-2026)).

## Where the collection lives

The study `ao_rg_points`:
* Hawk-Eye adapter `src/ingest/public_dump/slam_ball_tracking.py`: raw files in `data/raw/public_dump/slam_ball_tracking/`, staged tables in `data/dump/points/slam_ball_tracking/`.
* SofaScore adapter `src/ingest/point_sources/sofascore_tournaments.py`: raw files in `data/raw/point_sources/sofascore_tournaments/`, staged tables in `data/dump/points/sofascore_tournaments/`.
* The gap's frozen match list, the links, the checks and the run summaries: `data/studies/ao_rg_points/`; scripts in `src/eda/ao_rg_points/`; tests in `test/ao_rg_points/`.
* The write-up: [docs/studies/ao_rg_points/README.md](../studies/ao_rg_points/README.md).

Two SofaScore by-tournament adapters exist, written on 29 September by two sessions: `sofascore_tournaments.py` (this study, which collected this gap) and `sofascore_editions.py` (the [gap downloads](../studies/gap_downloads/README.md) study, `--gap <id>`, for the ATP gap). Whether both stay is left to the owner.

## Not changed by this decision

* **The sources' terms and rights.** SofaScore's terms are unchanged; the Hawk-Eye copy's data remain unlicensed.
* **The project's status.** No dataset, model or venue is selected.
