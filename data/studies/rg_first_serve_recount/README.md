# Roland Garros 2022–2025 and the Paris Olympics, the first-serve recount: evidence

Evidence for [docs/studies/rg_first_serve_recount/](../../../docs/studies/rg_first_serve_recount/README.md) (9 October 2026): item 6 of the adoption checklist, steps 1–2 (the recount and the reviewers' check). No model result is read here.

## Files

**The collection** (`collection/`):

| File | What it is | Made by |
|---|---|---|
| `collection/rolandgarros_summary.json`, `runs.jsonl`, `rolandgarros_2019_2025.log` | RG's own statistics, 2019–2025: requests, answers, staged rows | `src/ingest/point_sources/rolandgarros.py` |
| `collection/infosys_slams_summary.json`, `infosys_rg2019_2024.log` | RG's MatchBeats files, 2019–2024 (raw only) | `src/ingest/point_sources/infosys_slams.py` |
| `collection/olympics_summary.json` | The Paris 2024 results files (Wayback captures) | `src/ingest/point_sources/olympics.py` |

**Step 1, the recount** (`src/eda/rg_first_serve_recount/recount.py`):

| File | What it is |
|---|---|
| `rows.parquet` | One row per Stage 0 player row of RG 2019–2026 and the Olympics 2024: Sackmann's row as read (`raw_*`), Stage 0 (`s0_*`), RG's statistics (`api_*`), RG's MatchBeats recount (`mb_*`), RG's key statistics (`ks_*`), Court Vision (`cv_*`), the Olympic results and play-by-play (`ol_*`, `olp_*`), the Match Charting Project (`mcp_*`) |
| `links.json` | What each source holds and how much of it was placed on Stage 0 |
| `agree_<a>_vs_<b>.csv` | Exact agreement per count by event, year, tour and draw; `first_in_given_svpt` is first serves in where the two agree on serve points |
| `editions.csv` | Pooled first serves in and points won on each serve, by edition and source |
| `ao_check.csv`, `ao_rows.csv` | The same point sources at the Australian Open against Stage 0's AO rows; `*_given_complete` where the point file holds every point |
| `disputed_referees.csv` | Rows where the official record and Sackmann's disagree on first serves in, with Court Vision and the hand charts |
| `recount_run.log` | The run's printout |

**Step 2, the proposal** (`propose.py`) **and the review**:

| File | What it is |
|---|---|
| `proposed_rows.csv` | Every Sackmann player row in scope (RG 2022–2025, the Olympics 2024) with its class (equal, split = A, split_other = B, points, other, no_record), the sign of the difference, the second record's verdict and every source's counts |
| `proposed_corrections.csv` | The proposed corrections, one row per raw Sackmann row, in `row_corrections.csv`'s columns (action `replace_split`; fix ids `RGFSA`, `RGFSB`, `OGFSA`, `OGFSB`) |
| `proposal_editions.csv`, `proposal_summary.json` | Counts by edition and class, pooled first serves in before and after, the dry run |
| `control_2019_2021.csv` | The same classes for RG 2019–2021, before the fault: a check of the rule, never proposed |
| `review/brief.md` | What the three reviewers were given |
| `review/<reviewer>/verdict.json`, `scope.csv` | Each reviewer's votes and the sides they confirm, with their own values; their scripts are in `src/eda/rg_first_serve_recount/review/<reviewer>/` |
| `confirmed/confirmed_corrections.csv` | **The corrections all three reviewers confirmed** (`consensus.py`) |
| `confirmed/consensus.json` | The votes, what was confirmed and dropped, the dry run of the confirmed table, the hashes of the decided tables |
| `confirmed/candidate_corrections/` | A corrections folder for a candidate Stage 0 build (`stage0_build.py --corrections-dir`): the decided tables of 8 Oct with the confirmed rows appended |

**The follow-ups of 9 Oct** (`followup/`; report § 8). These cover RG's whole box for 2022–2026 under the Slam rule of 6 Oct, and the four RG 2021 exchanged boxes. Code: `whole_box.py`, `consensus_followup.py`.

| File | What it is |
|---|---|
| `followup/collection/rolandgarros_summary.json`, `runs.jsonl`, `rolandgarros_2026_run.log` | RG's own statistics for 2026: 478 requests, every match answered, no error or refusal |
| `followup/whole_box_rows.csv` | One row per Stage 0 player row of RG 2022–2026, with the columns below |
| `followup/proposed_overrides.csv` | One override row per proposed match, in the Slam override table's columns plus `source` (sackmann or tml) |
| `followup/exchange_rows.csv`, `proposed_exchanges.csv` | The four RG 2021 exchanged boxes: the evidence, and their `exchange_box` rows (fix `RGX`) |
| `followup/proposal_summary.json`, `whole_box_run.log` | Classes by edition, the counts that change, what the referees say, pooled rates before and after, and the dry run of the whole candidate |
| `followup/*_v1.*` | The proposal as the reviewers first checked it, before the amendments on service games (report § 8.3) |
| `followup/review/brief.md`, `review/<reviewer>/verdict.json`, `overrides_scope.csv`, `exchanges_scope.csv` | Round 2 of the review: the brief, each reviewer's votes (with an `addendum` entry), and the matches and exchanges each confirms, with its own values. Scripts are in `src/eda/rg_first_serve_recount/review_followup/<reviewer>/` |
| `followup/review/addendum_matches.csv` | The 12 matches the amendments changed and the 32 they added, with the v1 and v2 values (`followup_delta.py`) |
| `followup/confirmed/confirmed_overrides.csv`, `confirmed_exchanges.csv`, `consensus.json`, `confirmed_run.log` | **What all three reviewers confirmed**: 1,304 overrides and 4 exchanges, with the votes, what was dropped, and the dry run |
| `followup/confirmed/not_unanimous_overrides.csv` | The 237 proposed matches short of unanimity, with each reviewer's word. They are part of no candidate |
| `followup/confirmed/editions_after.csv` | Pooled first serves in, aces and double faults by edition and draw: the rows as read, after the candidate, and RG's own |
| `followup/confirmed/candidate/` | The inputs of the candidate Stage 0 build (below) |
| `followup/service_game_swaps.csv`, `service_game_swaps_run.log` | Sackmann's service games at RG 2019–2026 and AO 2025 against the score's alternation from the Slam's own first server: equal, swapped, other (`service_game_swaps.py`; report § 8.6) |

**Executed at the owner's word, 9 Oct** (report § 9; [decision](../../../docs/decisions/2026-10-09-roland-garros-box-scores.md)):

| File | What it is |
|---|---|
| `followup/collection/infosys_probe_old_editions.log`, `infosys_slams_summary.json` | The probe of each final of AO 2013–2024 and 2026, and RG 2013–2018. Point files are served from AO 2018 and RG 2013 |
| `followup/collection/infosys_ao_2018_2026/`, `infosys_rg_2013_2018/` | The two fetches of those editions' MatchBeats files, raw only, each with its summary and log |
| `followup/service_games/matches.csv` | One row per player row of a Stage 0 AO or RG match with a MatchBeats file: the first server and its proof, the row's and the true service games, the class (equal, swapped, other, incomplete, unproven), and the exclusions |
| `followup/service_games/proposed_swaps.csv`, `summary.json` | The proposed `exchange_svgms` rows (fix SVX), and classes by Slam and year (`service_games.py`) |
| `followup/service_games_round1/` | The same for the first review round (RG 2019–2026 and AO 2025 only) |
| `followup/review/brief_service_games.md`, `addendum_swaps.csv`, `review/<reviewer>/swaps_scope.csv` | The swap review: the brief, the swaps added by the older editions, and each reviewer's confirmed swaps |
| `followup/confirmed/confirmed_swaps.csv` | **The swaps all three reviewers confirmed**, in the candidate's corrections |

`whole_box_rows.csv` holds, per player row:
* the row as read (`raw_*`) and RG's record (`off_*`);
* the match's class (`cls`) and what changes;
* the referee flag, and where `off_sv_gms` comes from;
* MatchBeats, key statistics, Court Vision and hand-chart counts.

The candidate folder `followup/confirmed/candidate/` holds:
* `slam_box_overrides.csv`: the decided table of 6 Oct with the confirmed RG rows appended;
* `corrections/`: the decided tables of 8 Oct, with step 2's confirmed split rows of the matches that take no override, and the confirmed exchanges.

Build with `stage0_build.py --box-overrides data/studies/rg_first_serve_recount/followup/confirmed/candidate/slam_box_overrides.csv --corrections-dir data/studies/rg_first_serve_recount/followup/confirmed/candidate/corrections`.

**The candidate build and its harm check** (steps 3–4 of checklist item 6; report § 10.3) keep their records in [`data/studies/current_best_model/2026-10-09_rg_box_scores/`](../current_best_model/2026-10-09_rg_box_scores/):

| File | What it is |
|---|---|
| `setup.log`, `chain_lane*.json`, `lane*.log`, `chain_logs/`, `chain_outputs/` | The sandbox build: each step's exit code, seconds and log (`chain_lane1i.json`: the frame steps rebuilt with the men-only indoor input) |
| `candidate_trim.json` | The trim of the sandbox Stage 0 to the live tables plus the 2,964 matches the candidate's tables name (`candidate_trim.py`) |
| `model_frame.parquet`, `model_inputs.json` | The frame fitted (SHA-256 `8549316e…`), on the reference's 58-input list |
| `first_collect_indoor_filled/` | The first collection, before the rebuild: its frame (`af51f912…`) also carried the indoor fill decided on 9 Oct |
| `input_dose/` | The input flags read against the dose (`input_dose.py`; reads no result): service-game coverage by tour and year, where it changed, and when the flagged inputs move |
| `fits_wait.log`, `fits.log`, `fits/` | The GPU wait and the fits (seeds 0–3, seasons 2019–2024) |
| `vs_reference_2026-10-08/` | `compare.py`'s reading against the frozen reference (seasons ≤ 2024), `adoption_read.json`, and `reading_split.csv` (the levels, each seed, the seed term's share; `reading_split.py`) |
| `verify_applied/` | Was the candidate applied as confirmed? (`verify_applied.py`; reads no result): V1 the values, V2 the orientation, V3 the timing (with the light cone and the clock), V4 the direction, V5 Stage 0's rule counts |
