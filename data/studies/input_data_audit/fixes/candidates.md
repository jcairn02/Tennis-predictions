# Candidate fixes for review (8 Oct 2026)

The owner asked: "find all the corrupt data that is UNDOUBTABLY corrupt where the fix is CLEAR. Have review agents
confirm the logic so we have consensus that the problem is clear and the fix is unanimous. Execute it after."

A candidate is executed only if **every reviewer** votes that (a) the data is corrupt beyond reasonable doubt and
(b) the proposed fix is clear, unique and correct, **on the same rows**. A reviewer may narrow a candidate's scope;
then only the rows every reviewer confirms are executed. Anything short of that is left as it is.

Background: the audit report `docs/studies/input_data_audit/README.md` (read it first, sections 2–5) and its evidence in
`data/studies/input_data_audit/` (file names below). The audit code is `src/eda/input_data_audit/` (`common.py` has the
detectors). Treat the audit's numbers as claims to check, not facts.

## Where the data is

| What | Path |
|---|---|
| Live Stage 0 (7 Oct build; what a rebuild would correct) | `data/studies/predictability_diagnostic/stage0_matches.parquet`, `stage0_match_players.parquet` |
| How Stage 0 is built (merge, box checks B0–B9, overrides, repairs) | `src/eda/predictability_diagnostic/stage0_build.py`, `src/eda/feature_alpha_audit/repair_data.py` |
| Sackmann's raw rows as staged (columns `_source_file`, `_row`) | `data/dump/matches/sackmann_archive/{atp,wta}/*.parquet` |
| Tennis My Life raw rows | `data/dump/matches/tennis_my_life/` |
| Match Charting Project (hand-charted points) | `data/raw/public_dump/match_charting_project/` (CSV), `data/dump/points/match_charting_project/` |
| WTA's own match statistics (WTA API, 2019–2026) | `data/dump/points/wta/stats/<year>.parquet` (one row per match and set; `setnum` 0 = whole match). Read with `pyarrow.parquet.ParquetFile(path).read().to_pandas()` and drop duplicated columns: `pd.read_parquet` fails on a duplicated `year` field. Match list: `data/dump/points/wta/matches.parquet`; editions: `editions.parquet` (Abu Dhabi 2021 = 2028, Phillip Island 2021 = 2027, Adelaide 2 2022 = 2030). Match ids: `LS` main singles, `RS` qualifying singles |
| Roland Garros's own key statistics, 2025–26 (decrypted Infosys) | `data/dump/points/infosys_slams/keystats.parquet` (`set_key` set0 = whole match; "First Serve" = first serves in / serve points, etc.), `matches.parquet` (players), `points.parquet` (point by point, also AO) |
| Closing odds as linked (Stage 1) | `data/studies/predictability_diagnostic/stage1_odds.parquet`; raw tennis-data.co.uk: `data/dump/odds/tennis_data_couk/` |
| Odds agent's tables | `data/studies/input_data_audit/odds/` (a04_avg_gt_max, a06_placeholders, a06_winner_swapped, a07_avg_vs_books) |
| Serve-speed panel (stage 2) | `src/eda/serve_speed_tabpfn/panel.py` (header explains sources and precedence); `data/studies/serve_speed_tabpfn/speed_records.parquet`, `speed_panel.parquet` |
| Speed agent's tables | `data/studies/input_data_audit/speed/` (`o13_row_checks.txt`, `t_*.csv`) |

Box-score columns in Stage 0: `ace, df, svpt, first_in, first_won, second_won, sv_gms, bp_saved, bp_faced` per player
row. In Sackmann's raw rows they are `w_ace, w_df, w_svpt, w_1stIn, w_1stWon, w_2ndWon, w_SvGms, w_bpSaved, w_bpFaced`
and the `l_` equivalents. In Sackmann's convention serve points (`svpt`) **include** double faults.

## Candidates

### Box scores (Stage 0; they feed the two-week form, IOS profiles and points aggregates)

**F1. WTA 2015, serve points leave out double faults.**
* Claim: in 30 WTA tour events from Acapulco (23 Feb 2015) to New Haven (24 Aug 2015), Sackmann's `svpt` excludes
  double faults. Evidence: `box_wta2015_events.csv` (rows with `in_fault` True), `box_wta2015_vs_mcp.csv`,
  `box_svpt_df_editions_oct07.csv`; the definition test `second_won + df <= svpt - first_in` fails in 2.6% of WTA 2015
  rows and in no more than 0.04% of any other tour-season; MCP agreement 83% for `svpt + df` against 12% for `svpt`.
* Scope: every player row (both players) of the 30 events with `in_fault` True: 2,382 rows. Doha 2015 is excluded.
* Fix: `svpt := svpt + df` on each of those player rows; every other count unchanged.
* Points to settle: does the 12% "svpt alone equals MCP" come only from rows with `df = 0`? Is any row in the window
  already inclusive (adding `df` would then break it)? Is the event list right at both ends (Doha out, Kuala Lumpur at
  49.9% in)? Are qualifying rows, Fed Cup rows or the 2015 Slams affected?

**F2. Box scores exchanged between winner and loser.**
* Claim: 88 matches fit their score (games = own holds + opponent's breaks conceded) only with the two box scores
  exchanged; 74 of them also have the recorded winner winning fewer points. Clusters: WTA Abu Dhabi 2021 (22 main +
  6 qualifying), Phillip Island 2021 (14 + 4); the rest are scattered singletons. Evidence: `box_swapped_oct07.csv`,
  `box_identity_editions_oct07.csv`; detector `identity_flags` in `common.py`.
* Scope: the 88 matches. Reviewers are expected to narrow it. About 1,700 matches fail the games identity for other
  reasons (counting conventions, tiebreaks counted as service games), so some exchanged fits may be coincidences.
* Fix: exchange all nine counts between the two players of the match.
* Points to settle: per match, is the exchange confirmed by an independent record (the WTA API for the 2021 events and
  Saint-Malo 2025; MCP; an official Slam feed), or by internal evidence strong enough on its own (exchange makes the
  winner win more points, service games alternate, B0–B9 still pass)? Could the score or the winner be wrong
  instead of the box (check that the recorded winner advanced)?

**F3. WTA Adelaide 2 2022 carries Adelaide 2021's box scores.**
* Claim: the box scores of WTA Adelaide 2 (10 Jan 2022) are verbatim copies of Adelaide 2021's (22 Feb 2021), on
  other players. Evidence: `box_raw_copies.csv` (rows with `copy_event` "Adelaide 2", `same_players` False).
* Scope: every Adelaide 2 2022 match whose box equals an Adelaide 2021 box (about 19 matches, 38 player rows). Check
  whether any Adelaide 2 2022 match with a box score is not a copy.
* Fix, two variants (vote on each): **F3a** blank the box score (missing, as Stage 0 treats any failed box);
  **F3b** replace it with the WTA API's box where the WTA API holds the match and its counts pass Stage 0's checks,
  else blank. F3b is clear only if the WTA API is shown to measure what Sackmann measures: check its agreement with
  Sackmann on the clean WTA events of 2021–2022 (exact equality per count, per player row).

**F4. Box scores copied from the same pair's earlier meeting, and the Dusseldorf 2012 copies.**
* Claim: in `box_raw_copies.csv` rows with `same_players` True, the later match carries the box of the same two
  players' earlier match (different score). Also ATP Dusseldorf 2012 (World Team Cup): one box appears on other
  matches of the event.
* Scope: the copy in each pair (deduplicate the file: it lists some pairs twice).
* Fix: blank the copy's box. Which of the two is the copy must be decided per pair (the box fits one match's score and
  not the other's; or an independent record says which is genuine). If it cannot be decided, the pair is not clear.

**F5. Roland Garros 2025 (qualifying and main draw, both tours): Sackmann's counts against RG's own statistics.**
* Claim: Stage 0's RG 2025 qualifying reads 68.5% first serves in (men) and 67.9% (women) against RG's key statistics
  63.1% and 63.2%; exact first-in agreement 35–39% of rows (main draw about 76%). Example: Li Tu's 2025 Q1, 82 first
  serves in against RG's 57. Evidence: `box_rg2025_vs_keystats.csv`; the data-continuity study flagged the men's
  qualifying fault and the Slam box-score decision (`docs/decisions/2026-10-06-slam-box-scores.md`) explicitly left
  "Sackmann's Roland Garros men's qualifying of 2022–2025" unchanged "until a study measures its effect".
* Scope: the RG 2025 rows that differ from RG's key statistics.
* Fix: replace the whole box (nine counts, both players, one source per match, as the Wimbledon 2026 decision did)
  with the counts derived from RG's key statistics (and/or point-by-point). Points to settle: do the key statistics
  give all nine counts unambiguously (service games, break points saved)? How often do RG's statistics equal TML's
  or the point-by-point data where no fault is suspected (2026 men's qualifying agrees on first serves in only 66% of
  rows with identical pooled rates, which suggests convention differences)? Does the earlier decision's "left
  unchanged until a study measures its effect" bar this fix?

**F6. Roland Garros 2022–2024 (qualifying and main draw) and the Paris Olympics 2024.** Proposed **exclusion**: the
fault is shown at the edition level (pooled first serves in; MCP on a sample), there is no independent record for
each match, and the fix (blank the first/second split, or the box) is a choice. Confirm or contest.

### Identities and ages (Stage 0)

**F7. Players split across two ids.**
* Claim: 13 players still carry a second id in the 7 Oct tables (9 women, 4 men). Evidence:
  `frame_split_ids_oct07.csv` (name key, established id, new id, dates). `repair_data.repair_tables` merges such ids
  only when no "demographic conflict" exists; see F8 for why these 9 women fail it.
* Fix: map the new id to the established id (alias), on every row of the new id.
* Points to settle, per pair: the name key is held by exactly one established player of that tour; countries and
  birth years agree where known; the two ids never play in the same week at different events; no second person of that
  name exists (for example "cuong quoc tran", with one established match).

**F8. Garbage ages on Tennis My Life's 2026 WTA rows.**
* Claim: 12 player rows (Cristian, Kasatkina, Kudermetova, Boisson, Tomljanovic, Yastremska, Eala; 8 June 2026) have
  ages of 2,143–3,387. Evidence: `box_ages_oct07.csv` (kind "impossible", source tml).
* Fix: blank the age (missing). Variant **F8b**: compute it from the player's established birth date (Sackmann's
  player file, or the established id's own ages) once F7 resolves the id. Vote on each.

**F9. ATP Challengers of August 2020: ages about 5 months behind.**
* Claim: 182 rows, e.g. Alcaraz 16.8 at 17 Aug 2020 (born 5 May 2003: 17.3). Evidence: `box_ages_oct07.csv` (kind
  "inconsistent", column `off_days`). These rows are not in the model frame.
* Fix: recompute the age from the player's birth date. Settle: is the age wrong, or the date?

**F10. Other "impossible" ages** (11–12 and 61–76, Sackmann ITF/125 rows). Proposed **exclusion**: some are real
(Gail Falkenberg, born 1947, played ITF qualifying in her seventies; Yue Yuan's ages fit her birth year). Confirm or
contest per player.

### Closing odds (Stage 1)

**F11. Average odds reversed against the individual books.**
* Claim: Wimbledon 2016 final (Murray d. Raonic): the average puts 1.26 on Raonic while Bet365 4.33, Pinnacle 4.36 and
  two more books make Murray the favourite; Chennai 2013 semi-final (Bedene d. Tipsarevic): the average is reversed
  against 5 books. Evidence: `odds/a07_avg_vs_books.csv` (flag "reversed").
* Fix: exchange the two players' average (and, if equally reversed, maximum) prices.
* Settle: is the reversal certain (several books agree, ranks agree)? Are other rows flagged "reversed" equally
  certain? Rows where only one reference book disagrees are not: in Berlin 2023 R32 the average agrees with the
  ranks and the single book is the one reversed.

**F12. Nottingham 2017 women's final: names swapped in tennis-data.**
* Claim: Vekic won 2-6 7-6(3) 7-5; tennis-data lists Konta as the winner, so the winner's price (4.98, Vekic's) is
  linked to Konta (ranked 8th against 70th). Evidence: `odds/a06_winner_swapped.csv`.
* Fix: exchange the two players' prices on that row.

**F13. Other odds flags** (average above the maximum: `odds/a04_avg_gt_max.csv`; "placeholder" Washington 2026 finals:
`odds/a06_placeholders.csv`; single-book reversals). Proposed **exclusion** unless a row is shown corrupt with one
clear fix.

### Serve-speed panel (stage 2, `spd_L`)

**F14. A first-serve average at or above the fastest serve of the match.**
* Claim: 108 records (handoff key statistics and ManTennisData) have a first-serve mean ≥ the match's fastest serve
  minus 1 km/h; an average cannot exceed the maximum it averages. Evidence: `speed/o13_row_checks.txt` section 4;
  record table `data/studies/serve_speed_tabpfn/speed_records.parquet`.
* Fix: the record is not a candidate (like the panel's existing mislink rules), so the player-match takes its next
  valid record, if any. Settle the exact rule: strictly above the maximum, or at/above, or within 1 km/h; which
  maximum (the player's own, or the match's); minimum n.

**F15. Physically impossible first-serve averages.** Men's records averaging ≥ 240 km/h (14 rows, up to 267; the
fastest servers average about 210–220). Fix: as F14. Check how many are already caught by F14.

**F16. Copied speed blocks.** The same player with identical (mean, n, second-serve mean, max) on two different
matches (5 pairs), and matches whose two sides carry identical values (12). Fix: drop both records of each pair
(the original cannot be told), or only the later one. Vote; settle whether the original can be identified.

**F17. Court and edition offsets, the filter's diffuse start, the 120 km/h floor, "second-serve mean ≥ first".**
Proposed **exclusion**: measurement offsets and design choices, not single corrupt records with one clear fix.

### Already handled or not data corruption (for the record; confirm)

* The IOS products' scale (#6): a design issue. Workload after the splice (#7): a coverage gap (missing matches).
* Men's 2018 odds (#9): restored in the 7 Oct Stage 1. Wimbledon 2026 (#10): replaced on 7 Oct by decision.
