# Australian Open and Roland Garros point data, 2022–2026

**Status: data collection, not a selection.** On 29 September 2026 the owner asked for the data the [gap-sources research](../../research/gap-sources/README.md#the-proposed-list) proposed for the data map's gap "Roland Garros and Australian Open point by point, 2022–2026" (`slam_points_ao_rg`, 1,636 matches), put in the appropriate place in `data/` ([decision](../../decisions/2026-09-29-ao-rg-points.md)). The research's row: SofaScore first, then the Hawk-Eye copy for 2022–24.
* *The Hawk-Eye copy* was downloaded on 29 September.
* *SofaScore* was deferred that day while it blocked the plain client. It was collected on 30 September at the owner's request, through a Chrome window.

## Result

The gap's 1,636 rows, as frozen from the map of 25 September [observed; `sofascore_check.py`, `hawkeye.py`]:

| | Rows |
|---|---:|
| **With a complete point record from at least one source** | **1,606** |
| … from the Hawk-Eye copy (every point, replaying to the official score) | 745 |
| … … and every stroke of every rally tracked | 552 |
| … from SofaScore (every game of the score) | 1,596 |
| With a partial record only (SofaScore short, or a game filed in the wrong set) | 27 |
| Walkovers: nothing was played | 3 |

**By edition** (rows with a complete record, of the gap's):

| Year | AO men | AO women | RG men | RG women |
|---|---|---|---|---|
| 2022 | 89 of 90 | 110 of 111 | 96 of 96 | 104 of 104 |
| 2023 | 60 of 60 | 63 of 63 | 86 of 90 | 109 of 109 |
| 2024 | 74 of 75 | 94 of 94 | 74 of 82 | 87 of 93 |
| 2025 | 75 of 76 | 88 of 89 | 73 of 74 | 107 of 107 |
| 2026 | 3 of 3 | 0 of 1 | 113 of 114 | 97 of 100 |

The misses in 2022 and at the 2026 Australian Open are the walkovers. The gap also held five matches at the other two Slams (the women's US Open 2024, and the US Open and Wimbledon men's 2026); four of the five are complete.

**On the rebuilt map** (30 September), the gap card shows 8. None is a match to fill: three walkovers, and five 2026 men's matches listed twice (as Sackmann's row and as Tennis My Life's) whose other row has the points.

## The Hawk-Eye Court Vision copy

**What it is [observed].** The GitHub repository [`hawkilol/tennisSlamBallTracking`](https://github.com/hawkilol/tennisSlamBallTracking), commit `f97a9b3` (8 April 2025, still the latest on 29 September 2026): the two Slams' Court Vision files for 2,027 singles matches, the Australian Open 2020–2024 and Roland Garros 2019–2024, men and women. Its author scraped them from the Slams' match centres; the code is GPL-3.0 and the data carry no licence.

**What was taken.**
* The match catalogue and the 2,027 per-point CSVs (163 MB): one row per serve, 64 columns (server and point winner, serve number, speed and type, rally length, how the point ended, error type, the serve's, return's and last shot's positions, spin).
* For 2022–2024, the years of the gap, the Court Vision JSON of each of the 1,225 matches (2.08 GB; 104 MB gzipped). It is the only place with every stroke: each point's `trajectoryData` lists the ball's hit, peak, net and bounce positions for the whole rally. The JSON of 2019–2021 (802 matches, 1.16 GB) is outside the gap and was not fetched.
* The adapter, `src/ingest/public_dump/slam_ball_tracking.py`, checks every file against the repository tree's git blob hash. 2,035 files already fetched by the research session were copied from its copy instead of downloaded again, and 1,222 were downloaded; none failed.

**Where it is.**

| Stage | Path | Contents |
|---|---|---|
| Raw | `data/raw/public_dump/slam_ball_tracking/` | The repository's paths; JSON gzipped; `_receipts.jsonl` (268 MB) |
| Staged | `data/dump/points/slam_ball_tracking/matches.parquet` | The catalogue, 2,027 matches, with each match's files and counts |
| | `…/points/<slam>_<year>.parquet` | Every CSV row, 503,586 |
| | `…/json_matches.parquet`, `…/json_points/<slam>_<year>.parquet` | The JSON's match fields (1,225) and point records (307,734) |
| | `…/shots/<slam>_<year>.parquet` | Every trajectory position, 4,662,409 |
| Map | [data_map.yaml](../../../data/data_map.yaml), entry `slam_ball_tracking` | Measured as shot where 90% of a match's points are tracked, else point |

A match is identified by slam, tour, year and the catalogue's `match_id`. The Roland Garros ids repeat every year (`SM001` is every final).

**Checks [observed; `hawkeye.py`].**
* *Against the research session's own reading of the same commit* (`src/eda/gap_sources/hawkilol_matches.py`): all 2,027 matches agree on points and tracked share.
* *CSV against JSON* (2022–24): 307,734 records on each side, with the same point ids and the same tracked records in every match. The JSON holds 6,121 placeholder records (`pointId` "NA", no scorer), which the CSV carries as point id "NA".
* *Against the official score:* the research replayed every match. 745 gap matches are complete: every point present, and every set, tie-breaks included, equal to Sackmann's score. The research's independent spot check confirmed 40 of 40.
* *On the map:* 2,026 of the 2,027 matches are placed, all on Grand Slam main-draw matches.
  * *By names:* 2,010 are placed by both surnames, initials and round within the same Slam and year. The map's generic linker alone misread surnames the catalogue runs together (`P.CARRENOBUSTA`), confused sisters (Mirra and Erika Andreeva both played Sabalenka at Roland Garros 2024), and took two matches of the week before (the 2021 ATP Cup, Strasbourg 2024).
  * *By the generic linker:* the other 16, all married names (Riske Amritraj, Hrunčaková, Saville). Four of them land on the map's maiden-name duplicate rows.
  * *Unplaced:* Sorribes Tormo v Gavrilova (now Saville), Australian Open 2021.

**What it fills** (complete point records, with every stroke tracked in brackets):

| Year | AO men | AO women | RG men | RG women |
|---|---|---|---|---|
| 2022 | 83 of 90 (81) | 106 of 111 (104) | 79 of 96 (29) | 75 of 104 (24) |
| 2023 | 58 of 60 (58) | 62 of 63 (62) | 30 of 90 (9) | 48 of 109 (20) |
| 2024 | 71 of 75 (71) | 94 of 94 (94) | 15 of 82 (0) | 24 of 93 (0) |
| 2025–26 | none | none | none | none |

The Australian Open is nearly whole. Roland Garros is not: the copy holds 225 of its 254 singles matches in 2022, about half in 2023–24, and most Roland Garros points have no trajectory (no 2024 match is tracked on 90% of its points).

## SofaScore

**How it was collected [observed].**
* *The block:* SofaScore refused the plain client (HTTP 403 "challenge") from 17:54 UTC on 29 September, and still did at 04:15 UTC on 30 September, 10 hours 21 minutes later.
* *The browser mode:* on the owner's go-ahead, Claude opened Chrome with the documented command (a blank profile, debugging port 9222). The adapter made its requests as `fetch()` calls in that tab, 1.2 seconds apart plus up to 0.8 seconds. The site's check passed without a click at the start. The other session, which collects the ATP gap, held its own SofaScore run meanwhile, since the two share one address.
* *Seasons:* 20 of the gap's 23 seasons had been listed by the gap probe on 29 September and were copied byte for byte. The other three (women's Australian Open 2026, Roland Garros 2026, US Open 2024) were found from one WTA day listing each and listed, in 29 requests. All 1,636 gap rows then link to an event. SofaScore's winner agrees with the map's in all 1,633 rows but the three that do not list the winner first: the two maiden-name duplicates and the Osaka walkover.
* *Order:* first the 891 gap rows the Hawk-Eye copy does not record completely, newest first; then the 745 it does.
* *The first run:* 2,108 requests from 04:19 to 05:15 UTC gave 1,051 point-by-point records and 1,051 box scores, and three answers "absent", the walkovers. At 05:15 the hourly token's renewal wanted a click in the Chrome window. The run waited for it, and was stopped at 06:00. That left 543 matches not asked, every one with a complete Hawk-Eye record.
* *The second run,* at the owner's word, fetched those 543: 1,087 requests from 14:26 to 14:55 UTC. The site's check passed without a click, and no request was refused or retried.
* *Held in all:* the records of all 1,632 played gap matches (38 of them the probe's) and 1,629 full box scores.

**Where it is.** Raw answers in `data/raw/point_sources/sofascore_tournaments/` (18 MB gzipped, with `_receipts.jsonl`; the runs' logs in `_logs/`). Staged tables in `data/dump/points/sofascore_tournaments/`: `events.parquet` (the 5,555 events of the 23 seasons), `points.parquet` (250,664 point states) and `statistics.parquet` (140,973 rows). On the map as `sofascore_tournaments`.

**Checks [observed; `sofascore_check.py`].**
* *Completeness* (every set of the record has as many games as SofaScore's own score, the research's rule): 1,595 of the 1,632, 19 of them to a retirement. 8 stop short. 29 file one game in the neighbouring set (for example 9, 14, 7 and 9 games against a score of 9, 13, 8 and 9).
* *Against the official score:* SofaScore's set scores equal Tennis My Life's in all 1,631 gap matches that have one. Two retirements between sets are written as a last set of 0-0 on one side or the other. The three walkovers are walkovers in both, and the two maiden-name duplicates have no official row under that name.
* *Against the Hawk-Eye copy:* the same set scores in all 745 matches the copy records completely.
* *Box scores:* 1,629 have the full serve and return box (aces, double faults, first serves in and won, second serves won, break points saved).
* *On the map:* all 1,632 are placed; 1,626 by names and round within the same Slam, year and tour. The generic linker alone had made two kinds of mistake. It put four 2026 men's matches on the same pair's meeting at the week-before event (Eastbourne, Mallorca, Winston-Salem), because Tennis My Life dates its 2026 Slam rows by the day played. And it put Yafan Wang's match on Xiyu Wang's: Diane Parry played both at the 2024 US Open.

**Found while linking** (both also applied in the other session's adapter):
* **Li Tu:** his name words are two letters, which a three-letter rule never links. Names with no longer word keep their two-letter words.
* **Pouille and Rodionov met twice** at Roland Garros 2023: in qualifying on 25 May (an event SofaScore gives no round name) and in the first round on 28 May. Events on the main draw's days are preferred.

**Five of the 1,636 are not matches to fill** [observed]. They are rows the map took from the Australian Open's own files without a tournament name:
* three walkovers in SofaScore: Evans v Rinderknech and Parrizas Diaz v Zanevska (2022), and Osaka v Inglis (2026, Inglis through);
* two maiden-name duplicates of matches listed under married names: Kuzmova v Wang is Hrunčaková v Wang, and Storm Sanders v Sabalenka is Storm Hunter v Sabalenka (2022).

**Two adapters.** Two sessions wrote SofaScore by-tournament adapters on 29 September: `src/ingest/point_sources/sofascore_tournaments.py` (this study: a seasons file, an event list, the probe's answers imported) and `src/ingest/point_sources/sofascore_editions.py` (the [gap downloads](../gap_downloads/README.md) study: any gap, with `--gap <id>`). This one collected this gap; the other is for the ATP gap. Whether both stay is the owner's call.

## Running it

From the repository root, in Git Bash:

```
./python.sh -m src.ingest.public_dump.slam_ball_tracking          # the copy; skips what is held
./python.sh -m src.ingest.public_dump.slam_ball_tracking --json-years all   # adds the 2019-2021 tracking (1.16 GB)
./python.sh src/eda/ao_rg_points/hawkeye.py                       # the copy's checks and the gap's fill
./python.sh src/eda/ao_rg_points/link_sofascore.py                # gap row -> SofaScore event, and the fetch order
./python.sh -m src.ingest.point_sources.sofascore_tournaments --seasons-file data/studies/ao_rg_points/sofascore_seasons.csv --events-file data/studies/ao_rg_points/sofascore_fetch_order.csv --browser
./python.sh src/eda/ao_rg_points/sofascore_check.py               # SofaScore's checks
./python.sh src/eda/data_map/build.py                             # redraw the map
./python.sh -m pytest test/ao_rg_points -q
```

The SofaScore command asks only for what is not held; every gap match is held now, so a rerun asks nothing. `--browser` needs the Chrome window of [point- and shot-level sources](../point_shot_sources/README.md#rerunning) open first, and someone to click if the site shows its check, at the start or at the hourly renewal. Without `--browser` it uses the plain client, which SofaScore refused on 29–30 September (HTTP 403, "challenge", later "Forbidden"). Only one SofaScore download should run at a time: the project's sessions share one address.

Evidence files are listed in [data/studies/ao_rg_points/](../../../data/studies/ao_rg_points/README.md).

## Limits

* **Rights.** The copy's data are unlicensed and came from the Slams' feeds through a third party, like the Hugging Face dump the owner accepted on 25 September. SofaScore's terms forbid automated extraction; it was collected on the owner's decision of 23 September. Non-commercial research only; nothing here approves a dataset or model.
* **What "complete" means.** For the copy, the research's replay against Sackmann's score. For SofaScore, the games per set against its own score; its point states imply the game-winning point, and its ace and double-fault codes are inferred, not documented (see `src/ingest/point_sources/sofascore.py`). The copy's per-stroke positions were checked for being present, not for accuracy.
* **Roland Garros tracking is thin**, and missing strokes are not interpolated. A match counts as tracked when 90% of its points have a trajectory.
* **Names.** The copy's names are "initial.SURNAME" with compound surnames run together. One of its matches could not be placed on the map. Married and maiden names split a few matches into two rows on the map, and five 2026 matches appear twice there for other reasons.
