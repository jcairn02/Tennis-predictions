# Source reconciliation: the subagents' briefs, verbatim

16 Oct 2026 · Companion of the [process log](process_log.md). Each subagent received the common preamble followed by its own section, exactly as written here (the preamble is repeated in each prompt).

## Common preamble (given to every subagent)

```
You are a subagent working in the repository C:\Users\zerom\Documents\Tennis-predictions (a tennis-prediction research
project; Windows; run shell commands in Git Bash). You are part of the study "source reconciliation", led by the main
session. The study asks, for each raw field the project's current best model reads, which source on disk is the most
accurate, and whether a combination of sources, or a correction of corrupt rows, beats the source the model uses. You
build one part, described below, and report to the lead. The lead will re-check your findings before using them, so
make them checkable.

HARD RULES
1. Run Python only through `./python.sh` from the repository root in Git Bash (it activates the project's `tennis` Conda
   environment). Never fall back to another interpreter. Bash prints harmless "bind: warning" lines; ignore them.
2. Read-only on everything shared. Write ONLY: code as `src/eda/source_reconciliation/<your prefix>_*.py`; outputs under
   your part folder in `data/studies/source_reconciliation/`. Never write to data/dump/, data/raw/, any other folder of
   data/studies/, Stage 0/Stage 1, or any decided table. Never run a script whose job is to rebuild or rewrite shared
   tables (stage0_build.py, rebuild_stage0.py, match_timing/refresh.py, data_map/build.py or measure.py, any ingest
   adapter, any fits or compare script). No network access. No git command that changes state (status/log/diff are fine).
   Do not edit any existing file outside your own new files, even to fix a bug you find: report it instead.
3. Stage 0 = the frozen snapshot in data/studies/source_reconciliation/_snapshot/ (stage0_matches.parquet,
   stage0_match_players.parquet, stage0_summary.json, links/<source>.parquet, data_map_matches.parquet; manifest.json
   lists their SHA-256). Read it through src/eda/source_reconciliation/common.py (C.stage0(), C.links(name), C.SNAP).
   If you reuse a project helper that reads the live Stage 0 (data/studies/predictability_diagnostic/), check at the end
   that the live files' SHA-256 still equal the manifest's, and say so in your report.
4. No GPU: nothing in your part fits a model. Keep memory below about 20 GB (other jobs run on this machine); stream big
   files; prefer pyarrow column selection and filters.
5. `*.parquet` is git-ignored; CSV, JSON and MD under data/studies/ are tracked, and the repository is PUBLIC. Put
   per-match rows in parquet. Put only aggregates (counts, shares, means), ids and short examples in CSV/JSON/MD. Never
   write a bookmaker's price for a match to a tracked file.
6. Matches played from 29 Jul 2026 on are a proposed sealed holdout: never score anything against their results.
   Comparing two sources' values of the same field is not scoring and is allowed for every date; only the odds part
   scores against results, and only before 29 Jul 2026.
7. Label statements: observed (computed here, with the file), inference, unknown. Do not overstate. A source that counts
   differently by definition (e.g. service games including tiebreak games) is a definitional difference, not an error;
   say which it is and how you know.
8. Verify your own readers: for at least 5 random linked matches per reader, open the raw document (or the staged row)
   and check by hand that the counts and the player orientation are right. Record the keys you checked in your summary
   JSON.
9. When done, write REPORT file named below (for the lead, not the owner): what you built; every output file with its
   columns; the headline numbers with their files; what you checked and how; what you could not do and why; anything
   surprising. Then reply with a concise summary (under 600 words) pointing to the REPORT.

CONTEXT
- Stage 0 is the model's match table. Sackmann's files are its base; Tennis My Life (TML) rows are appended where no
  Sackmann row links (in practice every match from the week of 25 May 2026 on, and TML-only events before). On top: the
  decided Slam box overrides (Wimbledon and US Open 2026 from the IBM feeds; Roland Garros 2022-2026 from RG's own
  statistics; the AO/RG service-game swaps), and the corrupt-row corrections of 8 Oct 2026. Columns: matches: match_id,
  tour (atp/wta), year, level, qualifying, round, surface, indoor, best_of, draw_size, tournament_id, tournament_name,
  tournament_date, status, status_detail, score, minutes, has_box, box_status, sv_gms_incl_tb, player_a_id, player_b_id,
  a_won, source (sackmann/tml), source_file, source_row, map_level, ...; match players: match_id, player_id,
  opponent_id, side, won, player_name, rank, rank_points, seed, entry, age, height, hand, country, and the nine box
  counts ace, df, svpt, first_in, first_won, second_won, sv_gms, bp_saved, bp_faced (Sackmann's definitions; Stage 0
  blanks counts that fail its row checks).
- The match-timing link files (_snapshot/links/<source>.parquet: match_id, source, source_key, date_local, start_utc,
  date_basis, link_method, score_agrees, round_agrees) place many sources' records on Stage 0's match ids: wta_api, tdi,
  sofascore, infosys (the Hugging Face handoff), slam_feeds, match_charting, flashscore, tennis_data, api_tennis,
  open_tennis_data, live_tennis_api, pbp_copy, tml_days. Their builders are in src/eda/match_timing/ (srcb_*, srcc_*,
  link_flashscore.py): read them to learn each source_key's format.
- A general linker: src/eda/shot_level/common.py Stage0Linker (source rows with tour M/W, d (date), name1, name2
  [, round, level, draw] -> Stage 0 match_id and orientation a1). It reads the live Stage 0 (rule 3).
- Existing readers to reuse or copy (never edit them): src/eda/data_continuity/sources.py (SofaScore, WTA API box,
  TDI, the IBM Slam feeds mapped onto the nine-count contract, with comments on definitions, e.g. the WTA API records
  break points on the returner's side) and src/eda/data_continuity/common.py (the contract, the invariants,
  read_parquet_dedup); src/eda/shot_level/stage0_sources.py (readers of the Infosys handoff, SirGenkii, TDI, the Slam
  feeds, the Match Charting Project); src/eda/serve_speed_acquisition/speeds.py (Infosys key statistics and ManTennisData
  per player, linked); src/eda/rg_first_serve_recount/ (recounts of the nine counts from Infosys point files, service
  games from points, link code); src/eda/lower_level_evidence/candidate_stage0.py (links TennisLive, ITF live, SofaScore,
  TDI and WTA API box scores to Stage 0 for lower-level packages).
- Facts already established, to read before you start: docs/studies/data_continuity/README.md (section 3: TML against
  Sackmann; the referees; SofaScore's first serves in run 0.4-0.7 higher and its break points faced fewer from 2025;
  the WTA API's short records of 2024-25; its service games differ from Sackmann's in 9% of 2026 rows),
  docs/studies/input_data_audit/README.md (the accounting checks, swaps, copies), the decision
  docs/decisions/2026-10-08-corrupt-data-fixes.md, and docs/studies/rg_first_serve_recount/README.md (how the RG recount
  was done and validated).
- The data map's per-match list of sources for every singles match since 2018: _snapshot/data_map_matches.parquet
  (uid, tour M/W, level, draw, year, d, name1, name2, tname, creator, best, sources joined by ';'). The catalog
  data/data_map.yaml describes every dataset (paths, adapters, notes).
```

## The box-score reader contract (given to the three box-reader subagents, after the preamble)

```
YOUR OUTPUT: THE READER CONTRACT
For each reader you build, write data/studies/source_reconciliation/box/readers/<reader>.parquet, one row per (match,
player), on Stage 0's ids, with these columns:
  reader (str); family (str, below); kind ("box" = totals the source publishes; "recount" = totals you derive from its
  point records); source_key (str, the source's own match key); match_id (str, Stage 0's); player_id (str, Stage 0's);
  the counts ace, df, svpt, first_in, first_won, second_won, sv_gms, bp_saved, bp_faced, sv_won (float64; NaN where the
  source does not give the count; sv_won = serve points won); complete (bool: for a recount, every point of the match is
  present and your recount's set scores equal Stage 0's score; for a box, the source marks the match played/complete);
  link_method (str); any extra columns you need, prefixed x_.
Definitions to map onto (Sackmann's): svpt = every point served, double faults included; first_in = first serves in;
first_won = points won when the first serve went in; second_won = points won on the second serve (a double fault is a
second-serve point lost); sv_gms = service games played, tiebreak games NOT counted (Stage 0's sv_gms_incl_tb marks
sources that count them); bp_faced = break points faced on one's own serve; bp_saved = of those, saved.
Orientation: each row's counts are THAT player's serve counts. Orient by names or ids, never by "who won" alone; then
check that your recount's winner equals Stage 0's `won` and report the share that does not.
Families (independence groups): "wta_official" (the WTA API's box, its umpire event log, its point-by-point);
"atp_official" (the Infosys key statistics in every copy, Infosys MatchBeats and rally analysis, ManTennisData, TDI,
the ATP-site scrape); "slam_official" (IBM SlamTracker, the AO/RG Infosys files, rolandgarros.com); "sofascore";
"tennislive"; "flashscore"; "mcp"; "itf_official".
Also write <reader>.json: records read; records linked to Stage 0 and how; dropped and why (counts per reason); recounts
complete; the hand-check keys (rule 8).
Do not build the cross-source comparison: the lead builds it on your tables. You may compute a quick per-count equality
with Stage 0 as a sanity check of your reader, and report it.
```

## Subagent 1: WTA official family (box readers)

```
YOUR PART: the WTA's own records of women's matches, 2019-2026. Prefix: wta_. Readers under box/readers/; your report
box/REPORT_wta.md; any aggregate tables box/wta_*.csv.
Readers:
1. wta_api_box: the WTA API's per-match statistics (batch B3: data/dump/points/wta/stats/<year>.parquet; setnum "0" =
   the whole match; the mapping in data_continuity/sources.py wta_api(): break points are recorded on the returner's
   side), linked by the wta_api link file (source_key "wta:<tournament_id>/<year>/<match_id>"). Every year 2019-2026 and
   every draw the API holds (tour, WTA 125, qualifying). The Slams' box scores of 2024-2026 (batch B9) put first serves
   in 2-3 points higher than Sackmann and the Slams' own feeds (data_continuity section 3.2): keep them apart as a
   separate reader wta_api_slam_box if you can tell them apart (by tournament id/level).
2. wta_events_recount: the nine counts recounted from the chair umpire's event log (batches B1/B2:
   data/dump/points/wta/events/<year>.parquet; columns include index, name, type, reason, player, first_serve, server,
   receiver, score, set, game, game_score, match_score, match_state, timestamp; read with
   src/eda/data_continuity/common.py read_parquet_dedup, because the files repeat the column "year"). Work out the event
   vocabulary from the data (point won/lost, ace, double fault, fault / first serve, let, corrections and undo events,
   game/set/match end, tiebreaks), and handle umpire corrections (an undone point must be removed). Derive per player:
   points served, first serves in, points won on first and on second serve, aces, double faults, service games completed
   (tiebreak games not counted), break points faced and saved (a point, in a non-tiebreak game, that the receiver would
   win the game by winning), and the set scores. complete = the log covers the whole match and your set scores equal
   Stage 0's score.
3. wta_pbp_recount (if time permits): the WTA's point-by-point (batch B8: data/dump/points/wta/points/<year>.parquet,
   from April 2022; server, point_winner, scores; no serve number): svpt, sv_won, sv_gms, bp_faced, bp_saved and the set
   scores. A second record from the same system, useful to check the event-log recount.
(The Match Charting Project and SofaScore are another subagent's; do not build them.)
Questions to answer in box/REPORT_wta.md, with observed numbers and their files:
Q1 how many Stage 0 women's matches each reader covers, by level group (Slam, tour main draw, WTA 125, qualifying) and
   season;
Q2 does the event-log recount reproduce the WTA API's box (per count, exact share)? Where not, why?
Q3 the 2024-2025 "short records" (data_continuity section 3.2: where the API's box differs from Sackmann's, it has 7-12
   fewer serve points per player): does the event log hold those points? Which record is short: the API's box,
   Sackmann's, or neither?
Q4 service games: the WTA API's own count differs from Sackmann's in about 9% of 2026 rows, and TML's agree with the
   API in 83.7%. Which count does the event log support, and is the difference definitional (tiebreaks, games not
   completed at a retirement) or an error?
Q5 anything else systematic (events or seasons where the API's box disagrees with its own event log).
```

## Subagent 2: ATP official family (box readers)

```
YOUR PART: the ATP's own records (the Infosys Stats Centre in its copies, TDI, ManTennisData) of men's matches,
2018-2026. Prefix: atp_. Readers under box/readers/; your report box/REPORT_atp.md; aggregate tables box/atp_*.csv.
Readers:
1. atp_ks_handoff: the Infosys key statistics in the Hugging Face handoff
   (data/raw/public_dump/atp_pipeline_handoff/infosys_deep/ and infosys_full/, <year>_data.jsonl[.gz], 2018-2019 and
   2021-2024; the two folders overlap: keep one record per match, as src/eda/match_timing/srcb_sources.py load_infosys
   does). keystats.setStats.set0 = the whole match. Map the statistic names (Aces, Double Faults, 1st Serve, 1st Serve
   Points Won, 2nd Serve Points Won, Break Points Saved, Service Games Played, ... look at the exact strings; some values
   are "n/d (pct)") onto the contract. Link with the infosys link file (learn its source_key format from
   src/eda/match_timing/srcb_sources.py) or by ATP player ids.
2. atp_mb_handoff_recount: a recount from the handoff's rally_analysis points (each point filed under the shot that
   ended it and the side: t1err / t1win / t2err / t2win, with serve 1/2, pointEndType ACE / DOUBLE FAULT / WINNER /
   FORCED ERROR / UNFORCED ERROR, score, set, pointId, break-point flags; and a pointsMissing flag). Work out who served
   each point (e.g. the side that wins on an ACE, or loses on a DOUBLE FAULT, served that game; games alternate;
   tiebreak serve order) and who won it. If the server cannot be derived reliably, recount only what you can, and
   document the rule and its failure rate.
3. atp_ks_backfill and atp_backfill_recount: the decrypted ATP backfill, 2018 to Oct 2021
   (data/dump/points/infosys_atp/keystats.parquet and points.parquet: server, serve, scorer, result, ...). The
   Challengers in data/dump/points/infosys_challengers/ are a separate reader (4).
4. atp_ch_recount: Challengers 2021-2024 (data/dump/points/infosys_challengers/points.parquet). Challenger points mark
   only aces and double faults as endings: check whether the serve number is present.
5. atp_ks_sirgenkii and atp_sirgenkii_recount: SirGenkii's January-April 2025 Stats Centre copy
   (data/dump/points/sirgenkii_infotennis/atp_key_stats.parquet, by set; atp_rally_analysis.parquet, points). The
   sirgenkii link file is empty: link by ATP player ids and names (src/eda/gap_sources/sirgenkii_matches.py has a
   link_map).
6. atp_ks_daily: the daily collector's 2026 key statistics (data/studies/serve_speed_tabpfn/live/staging/
   atp_daily_<date>.parquet; read-only), if they hold the box counts.
7. atp_tdi_stats and atp_tdi_recount: TDI (data/dump/points/tdi/statistics.parquet, period "match"; points.parquet,
   with serve events: faults, lets, ace, winner, team_serving, ...), linked by the tdi link file. TDI's statistics give
   no first-serve split, but its points mark faults, so a recount gives first_in.
8. atp_mantennisdata: ManTennisData (data/dump/matches/mantennisdata/atp_matches_<year>.parquet; ATP tour level,
   Challengers and Slams, 2021-2026; box scores; no match date: link by names, tournament start date and round, as
   src/eda/serve_speed_acquisition/speeds.py mantd_players does).
Questions to answer in box/REPORT_atp.md, with observed numbers and their files:
Q1 how many Stage 0 men's matches each reader covers, by level group (Slam, tour main draw, Challenger, qualifying) and
   season;
Q2 do the recounts reproduce their own system's key statistics (per count, per source)? Which counts differ
   systematically, and why (definitions such as service games counting tiebreaks; break points)?
Q3 does ManTennisData equal the Infosys key statistics (the data map says it did on every match checked), and do TDI's
   statistics equal its own points?
Q4 anything else systematic (events or seasons where the official record disagrees with itself).
```

## Subagent 3: third-party families (box readers)

```
YOUR PART: the box scores compiled outside the tours: SofaScore, TennisLive, Flashscore, the Match Charting Project,
the ATP-site scrape, and (if time) the ITF's live data, for both tours. Prefix: tp_. Readers under box/readers/; your
report box/REPORT_third.md; aggregate tables box/tp_*.csv.
Readers:
1. tp_sofascore_box and tp_sofascore_recount: SofaScore's three collections (data/dump/points/sofascore/,
   sofascore_editions/, sofascore_tournaments/: events.parquet, statistics.parquet (period ALL), points.parquet),
   linked by the sofascore link file (source_key "sofascore:<event_id>"). The box mapping: data_continuity/sources.py
   sofascore(). The recount from its points: the server (serving), the point's winner (scoring), the
   home/away_point_type codes (find the codes for ace and double fault), the game/set structure, the tiebreak flag:
   derive svpt, sv_won, ace, df, sv_gms, bp_faced, bp_saved and the set scores (SofaScore's points carry no serve
   number: leave first_in, first_won and second_won NaN). Both tours, every level.
2. tp_tennislive_stats: TennisLive's match statistics (data/dump/points/tennislive/statistics.parquet with
   matches.parquet and index.parquet; the ten careers, the P4 samples and the P5 gap pages): map what the 8 statistics
   allow (aces, double faults, first-serve share, points won on first and second serve, ...; TennisLive gives no
   service games). Link: the P5 per-target files data/studies/gap_downloads/tennislive_<gap>_matches.csv.gz tie pages to
   the data map's targets; src/eda/lower_level_evidence/candidate_stage0.py (source "tennislive_pages") links them to
   Stage 0: reuse its logic, or the Stage0Linker.
3. tp_atp_scraped: the ATP-site scrape with per-set statistics (data/raw/public_dump/atp_pipeline_handoff/
   atp_scraped_enriched/atp_matches_<year>.csv.gz and atp_scraped/; men, 1991-2024): the match totals of the nine counts
   where present. Link by names, dates and rounds (the Stage0Linker) or ATP ids. Family "atp_official" (atptour.com's own
   numbers), but you build it because it is a scrape.
4. tp_flashscore_stats: Flashscore's statistics in the handoff (start with
   data/raw/public_dump/atp_pipeline_handoff/flashscore_gql_stats/ (1.2 GB); flashscore_full/ is 14 GB: stream it, and
   only if gql_stats lacks the match statistics), match totals mapped onto the contract where possible, linked through
   the flashscore link file (learn its source_key from src/eda/match_timing/link_flashscore.py;
   links/flashscore_records.parquet describes the records). If a full read would take more than about 3 hours, read a
   stratified sample of seasons and say so.
5. tp_mcp_recount: the Match Charting Project, both tours (data/dump/points/match_charting_project/: metadata, points,
   stats; linked by the match_charting link file), recounting all nine counts from each point's first- and
   second-serve strings (see src/eda/shot_level/stage0_sources.py mcp_point() and the RG study's referee scripts,
   src/eda/rg_first_serve_recount/review/R3-referee/independent.py and review_followup/R3-referee/referees.py, for
   the conventions: aces, double faults, faults, lets).
6. tp_itf_live (if time permits): the ITF's own statistics and points (data/dump/points/itf_live/statistics.parquet,
   points.parquet; 2026 from 15 Sep) for ITF matches, linked as candidate_stage0.py does.
Questions to answer in box/REPORT_third.md, with observed numbers and their files:
Q1 how many Stage 0 matches each reader covers, by tour, level group and season;
Q2 does SofaScore's box equal its own point recount (per count)? Its definitional differences (data_continuity: first
   serves in +0.4-0.7, break points faced fewer from 2025): where do they come from?
Q3 Flashscore's and the ATP-site scrape's coverage of the main tour before 2019, where no official point log is held:
   are they a usable second opinion for Sackmann's 2013-2018 rows (the training seasons)?
```

## Subagent 4: results, scores, context fields and birth dates (Parts C, D, E)

```
YOUR PART: Parts C, D and E of the study: results and scores, the context fields, and birth dates. Prefix: ctx_. Part
folder: data/studies/source_reconciliation/context/. Report: context/REPORT.md.
Each item: (a) the sources that hold the field for the same matches or players, and which one the model reads; (b) how
often they disagree; (c) for each class of disagreement, which source is right, by the official record where held, else
by a majority of independent sources (count dependent copies once: Open Tennis Data is built from tennis-data and
Sackmann; TML's pre-2026 rows largely continue Sackmann's format); (d) the Stage 0 rows contradicted by two or more
independent sources, listed (ids and the competing values only).
C. Results and scores. For every Stage 0 match linked to another source that holds a result: the link files
   tennis_data, api_tennis, open_tennis_data, flashscore, slam_feeds, wta_api, tdi, sofascore, live_tennis_api; and,
   linking them yourself, TennisLive's event listings (data/dump/points/tennislive/listed.parquet) and the WTA site
   records (data/dump/points/wta/player_matches/, player_results/), and the ITF live data. Compare the winner, the set
   scores (with tiebreak points where both give them) and the status (completed / retired / walkover / default: they
   change how Stage 0 treats a match). The link files carry score_agrees: use it, and recompute where you need finer
   classes. Write context/results_contradicted.csv.
D. Context fields.
   - surface: Stage 0's (Sackmann's, blanks filled from TML) against tennis-data's Surface (the tennis_data link file
     and data/dump/odds/tennis_data_couk/), the WTA API's editions and events (data/dump/points/wta/editions.parquet,
     events.parquet), TML's own surface where it differs from Sackmann's on linked matches, Flashscore's records,
     Open Tennis Data. Carpet against indoor hard. Per event, list the disagreements and who is right (where the venue
     makes it plain).
   - indoor: the model's indoor input (src/eda/indoor_fill/status.py: men, Stage 0's flag, then tennis-data's Court;
     women, the WTA's calendar, then tennis-data's Court; read docs/decisions/2026-10-09-indoor-input.md and
     docs/studies/indoor_fill/README.md first). On matches where two sources exist: men, Stage 0's flag against
     tennis-data's Court; women, the WTA calendar against tennis-data's Court. List every disagreeing event and resolve
     each where the venue makes it plain (Rotterdam, Paris Bercy, Linz, Stuttgart's Porsche Arena are indoor; Indian
     Wells is outdoor). The 9 Oct decision put the WTA calendar first for women as Claude's recommendation, awaiting the
     owner's confirmation: say which order is the more accurate on the evidence.
   - level: Stage 0's level against tennis-data's Series/Tier, the WTA editions' tier, TennisLive's event categories,
     TML's; list the disagreements (e.g. TML filing Winston-Salem 2026 as a Masters).
   - round, best_of, draw size: Stage 0 against tennis-data and the official feeds (a quick check).
   - dates: Stage 0's tournament_date (the event's start, Sackmann's convention) against the actual match dates of the
     timing sources (the link files' date_local / start_utc): how often does each source's match date disagree with
     the others' by more than a day; is the leak-proof clock (data/studies/match_timing/timing.parquet: es, lf per
     match; read src/eda/match_timing/timing.py for its definition) consistent with every source (no source's match
     date outside [es, lf])?
   - seeds (Stage 0 players' seed, read by the five-pattern stage): Stage 0 against the WTA API's SeedA/SeedB, the
     Slam feeds, TDI, the Infosys handoff's player1_seed/player2_seed: the disagreement rate.
E. Birth dates and ages. Stage 0's age (Sackmann's convention: years at the tournament date, one decimal; see the
   corrections F8b and F9 of 8 Oct) against Sackmann's player files (data/dump/players/sackmann_archive/), TML's player
   table (data/dump/players/tennis_my_life/), the WTA API's player data where held (data/raw/point_sources/wta/players/,
   data/dump/points/wta/player_*), the ATP profiles in the handoff (data/raw/public_dump/atp_pipeline_handoff/
   atp_player_scrape/), Tennis Abstract's bios (handoff tennis_abstract/), the Live Tennis API's players
   (data/dump/players/live_tennis_api_zenodo/). Per player: the birth date in each source; disagreements beyond a day;
   the majority; which players of the model's frame (main-tour main-draw matches from 2013) carry an age that disagrees
   with the majority by 0.25 years or more. Write context/dob_disagreements.csv (player id, name, the dates by source).
```

## Subagent 5: odds where Pinnacle is missing (Part F)

```
YOUR PART: Part F, the odds input where Pinnacle's close is missing. Prefix: odds_. Part folder:
data/studies/source_reconciliation/odds/. Report: odds/REPORT.md.
Background (read fully first): docs/studies/odds_sources/README.md, docs/decisions/2026-10-09-pinnacle-first-odds-input.md,
docs/studies/pinnacle_first/README.md. The model's odds input, "Pinnacle first" (src/eda/current_best_model/
odds_input.py), is Pinnacle's close (tennis-data's to July 2025, cross-checked against OddsTrader's timed copy, then
OddsTrader's to 7 Sep 2025), then BetOnline's closing line, then the books' average. Live, the model is fed Pinnacle's
current line. So the training rows from August 2025 on carry BetOnline's line as a stand-in for a Pinnacle close that
was never recorded. odds_sources section 4 found, in 2026 without Pinnacle (3,814 matches): BetOnline + Betfair better
than BetOnline alone by 0.63 mLL [0.15, 1.11]; BetOnline + Polymarket (30 minutes before the start) better by
2.00 [0.66, 3.34].
The question: for the stand-in rows (Pinnacle's faithful close missing: August 2025 to 28 Jul 2026), which available
price or combination is the most accurate against results, i.e. the best stand-in for Pinnacle? Candidates: BetOnline's
last line (today's stand-in); the Betfair exchange (tennis-data's BFE columns); Polymarket's price near the start (the
sharp benchmark's table: src/eda/sharp_benchmark/, data/studies/sharp_benchmark/); tennis-data's PSW/PSL after July
2025 (no longer Pinnacle's close: what are they?); Bet365 (tennis-data); the books' average and maximum; OddsTrader's
other books (the median, with lines stamped over 30 minutes after the start dropped); equal and walk-forward-weighted
logit averages of two to four of these; and a "Pinnacle proxy": a combination fitted where Pinnacle IS known (2018 to
July 2025) to predict Pinnacle's own margin-free log-odds from the other books, applied to the gap, and scored both
against results (in the gap) and against Pinnacle itself (out of sample, where Pinnacle is known).
Rules: remove the margin as the model's input does (check odds_input.py); compare candidates paired on the same matches;
intervals over four-week blocks, as odds_sources does (reuse src/eda/odds_sources/ code: table.py, quality.py,
pools.py, and their parquet outputs in data/studies/odds_sources/); read results only for matches before 29 Jul 2026;
fit walk-forward weights only on earlier data, never on the scored window; per-match prices only in parquet. Report in
mLL with 95% intervals and P(better), saying in each table which sign is better.
Also report each candidate's coverage of the gap rows (by tour and month: a stand-in must exist for most rows), and how
many rows of the template's frame (data/studies/current_best_model/template_2026-10-14/odds_sources.parquet and
odds_input.json) carry BetOnline as their odds input, and how many carry neither Pinnacle nor BetOnline.
```

## Subagent 6: serve speed (Part G)

```
YOUR PART: Part G, serve speed. Prefix: spd_. Part folder: data/studies/source_reconciliation/speed/. Report:
speed/REPORT.md.
Background (read first): docs/studies/input_data_audit/README.md section 2 (all of it), docs/studies/
serve_speed_acquisition/README.md, docs/studies/serve_speed_tabpfn/README.md (the panel and the live feed), and
docs/decisions/2026-10-07-speed-nudge.md. The model's stage 2 reads each men's player's first-serve average speed per
match from a panel (src/eda/serve_speed_tabpfn/panel.py; live: src/eda/serve_speed_tabpfn/live/live_panel.py,
frozen_panel(): data/studies/serve_speed_tabpfn/live/speed_panel_frozen_corrected.parquet plus
speed_panel_backfilled.parquet), which takes one source per player-match by an order. The audit found the handoff's key
statistics 26% more than 10 km/h off the player's norm, broken ManTennisData rows and court offsets, and suggested:
prefer the point mean where a key statistic differs from it by more than 5 km/h; drop rows whose average is at or above
the maximum, or whose second-serve average is at or above the first; bands of 150-235 km/h (men) and 125-205 (women).
Only the 130 impossible records were excluded (8 Oct).
The question: per player-match, which source of first-serve average speed is the most accurate, taking as referee the
mean of the same match's timed first serves in point records (Infosys MatchBeats and rally analysis, the Slam feeds'
points, Sackmann's Slam point-by-point speeds, the Hawk-Eye copy) where one exists; and does a consensus rule (e.g. the
median of the available sources; the point mean first; a key statistic only when within X km/h of another source) beat
the panel's current choice? Measure: (1) each source's agreement with the point mean (bias, SD, share within 1, 3 and 5
km/h), by source and season, men and women; (2) how many panel rows (by season) differ from the point mean by more than
3, 5 and 10 km/h, and from the consensus; (3) how far the consensus would move spd_L: recompute the 28-day speed form on
the corrected history with the project's own code (src/eda/serve_speed_tabpfn/features.py, adaptive/adjust.py), at the
data level only (do NOT score against results), and count the matches moved by at least 0.25, 0.5 and 1 unit, as the
audit's propagation table did. Never modify the frozen or live panels; build your alternatives under your folder.
```
