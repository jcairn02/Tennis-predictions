# ATP official box readers (subagent 2's report)

16 Oct 2026 · Written by subagent 2 for the lead; saved here by the lead because the harness refused the subagent's own write of this file. The text below is the subagent's report as returned (its summary, then its full report), unedited apart from this header. The lead's re-checks are in the study's process log and README.

## Summary

All 11 readers are built on the contract. Five are box readers: the ATP's key statistics in the Hugging Face handoff, the decrypted backfill, SirGenkii's copy and the daily collector's 2026 files, plus TDI's statistics and ManTennisData. Five are recounts from point records, for the handoff, the backfill, the Challengers, SirGenkii and TDI. I hand-checked 5 matches per reader (55 in all) against the raw files: every count and every player's orientation was right. The checked keys are in each reader's JSON.

- **Q1, coverage.** In 2018–2026 the ATP's box covers 95.6–97.2% of Stage 0's men's matches in each group (Slam, tour main draw, Challenger, qualifying), almost all through ManTennisData. Complete point-level recounts exist for 34,189 matches, but are dense only in 2022–2024 (Challengers 82%, tour main draw 70%, qualifying 68%). There are almost none for the Slams or for 2018–2021 and 2025.
- **Q2, recounts against their own system.** The handoff recount equals the handoff's key statistics on 99.90–100% of 55,186 player rows, per count. The other systems: Challengers 99.67–100% against ManTennisData, TDI 99.75–100%, SirGenkii 98.4–100%, backfill 97.8–98.6% (some of its key-statistics files stop part-way through the match).
  - Service games: the ATP counts neither tiebreaks nor the game in progress at a retirement, the same as Sackmann. Both are definitional differences, and the recount now follows them.
  - Break points: TDI's flag marks the state after the point, so I read break points from its scores. SirGenkii's flags don't say whose serve was under threat.
- **Q3.** ManTennisData equals the ATP's key statistics on 99.9% of 2022–2026 rows. The exceptions are a handful of events: the 2018–2019 ATP Finals (the ATP's two publications differ by ±1 first serve) and a few 2021 qualifying events whose key-statistics files are cut short. TDI's statistics equal TDI's own points.
- **Q4.** SirGenkii's copy is damaged:
  - It keeps key statistics for one player per match only (the other is −999 in all 929 matches), and as shares, which I turned back into counts.
  - Its AO 2025 rally files sit under other matches' codes.
  - Many of its rally files lack the final point.

  The handoff's own `pointsMissing` flag catches gaps my checks don't, so I now require it to be False for a recount to count as complete. Within the ATP system, the point record and the box differ by exactly one point in about 0.1–0.3% of rows. This can't be settled within the family, because ManTennisData and Stage 0 copy the same ATP box.
- **Rally recounts need a derived server**, because rally files don't say who served. My rule reproduces the explicit server in the ATP's point-by-point files on 99.99% of 477,034 points.
- **Results conflicts for your results part.** Three matches where the ATP's records and Stage 0 disagree on the result: Florianópolis CH 2024 Q2, L'Aquila CH 2018 Q2, Mallorca 2023 Q2 (ids in §7).
- **Rule 3.** The live Stage 0 and link files still match the manifest's SHA-256; nothing I used reads the live Stage 0. I wrote no tests, since the brief limits writes to my folder.

---

# REPORT_atp.md

16 Oct 2026 · Subagent 2 (session f3930e64-e3c4-49f0-8e93-a4637aebdbcf). Every input was read from the frozen snapshot (Stage 0, link files) or the staged and raw source files. Labels: **observed** (computed here, with its file), *inference*, **unknown**.

## 1. Code (`src/eda/source_reconciliation/`)

| File | What it does |
|---|---|
| `atp_common.py` | Stage 0's men's matches from the snapshot, name keys, the event linker, the contract writer, the sanity and winner checks (details below) |
| `atp_crosswalk.py` | ATP player code → Stage 0 id, written to `box/atp_crosswalk.parquet` |
| `atp_recount.py` | The recount engine and the server derivation (`derive_servers`) |
| `atp_keystats.py` | Key statistics (`set0`) → contract |
| `atp_points.py` | Point-record plumbing shared by the recounts |
| `atp_handoff.py` | Readers 1–2 (the handoff); `--reuse` reruns from a saved intermediate |
| `atp_backfill.py` | Readers 3–4 (backfill and Challengers) and the server-rule validation |
| `atp_sirgenkii.py` | Reader 5 |
| `atp_ksdaily.py` | Reader 6 |
| `atp_tdi.py` | Reader 7 |
| `atp_mantd.py` | Reader 8 |
| `atp_analysis.py` | The aggregate CSVs |
| `atp_handcheck.py`, `atp_handcheck_record.py` | The rule-8 hand checks and their recording |

- **The Stage 0 frame.** Stage 0's tournament ids carry the ATP's event id, except Sackmann's combined-event ids `YYYY-M0nn` (2016–2020). Those are mapped through a table and checked against ManTennisData's tournament list; every 2018–2020 id is found.
- **The event linker.** A source row goes to the Stage 0 match of the same season and ATP event whose two players it matches, player by player: by Stage 0 id through the crosswalk, else full name, else abbreviated name.
  - The qualifying flag must agree; the round only breaks ties.
  - If two source rows claim one Stage 0 match, the stronger link keeps it; ties drop both.
  - Orientation comes from which Stage 0 side each player matched, never from who won.
- **The crosswalk.** Learned from ManTennisData rows where both players matched by full name: 4,423 codes, each kept only if it maps to one Stage 0 id at least 80% of the time. 8 fall below that and are left out.
- **Run order** (about 20 minutes): crosswalk → mantd → backfill → handoff (about 12 minutes; `--reuse` takes 1) → sirgenkii → ksdaily → tdi → analysis → handcheck → handcheck_record.

## 2. Outputs

**Every reader** writes `box/readers/<reader>.parquet` (one row per match and player) and `<reader>.json`.

- **Contract columns:** `reader, family (atp_official), kind, source_key, match_id, player_id`, the nine counts, `sv_won, complete, link_method`.
- **Common `x_` columns:** `x_player_no`, `x_code`, `x_season`, `x_won`.
- **Each JSON holds:** records read and linked by method, drops by reason, `sanity_vs_stage0`, `winner_vs_stage0`, `hand_checks`.

| Reader | Kind | Rows / matches (complete) | Source | Reader-specific `x_` columns |
|---|---|---|---|---|
| `atp_ks_handoff` | box | 74,662 / 37,331 | handoff `set0`; key `year_event_CODE` | `x_first_won_den, x_second_den, x_sv_won_den, x_spd1, x_status, x_folder, x_match_date, x_linkfile_match_id` |
| `atp_mb_handoff_recount` | recount | 63,166 / 31,583 (27,593) | handoff `rally_analysis` (the handoff holds no MatchBeats; the name follows the brief) | engine diagnostics, `x_points_missing_flag, x_complete_before_source_flag` |
| `atp_ks_backfill` | box | 1,146 / 573 | `infosys_atp/keystats.parquet` | as `atp_ks_handoff` |
| `atp_backfill_recount` | recount | 1,144 / 572 (508) | `infosys_atp/points.parquet` | engine diagnostics, `x_route` |
| `atp_ch_recount` | recount | 4,706 / 2,353 (2,150) | `infosys_challengers` MatchBeats (2,260 matches); 115 rally-only matches with derived servers | engine diagnostics, `x_route` |
| `atp_ks_sirgenkii` | box | 1,858 / 929 | key stats `set_n 0`, counts reconstructed | `x_from_return_side, x_recon_me/opp/pairs` |
| `atp_sirgenkii_recount` | recount | 1,844 / 922 (613) | rally analysis | engine diagnostics, `x_identity` |
| `atp_ks_daily` | box | 198 / 99 | collector's raw 2026 files, decrypted in memory by its own guarded routine | `x_sv_games_fit, x_file` |
| `atp_tdi_stats` | box | 7,578 / 3,789 | `tdi/statistics.parquet`, match period | `x_status, x_level` |
| `atp_tdi_recount` | recount | 7,576 / 3,788 (3,529) | `tdi/points.parquet` | engine diagnostics, `x_first_in_faults, x_label_faults_disagree, x_level` |
| `atp_mantennisdata` | box | 264,818 / 132,409 | staged files **2015–2026** (2015–2017 are outside the window; filter on `x_season`) | `x_atp_key, x_first_pts_total, x_second_pts_total, x_service_pts_total, x_spd1, x_status, x_score` |

**Engine diagnostics on every recount row:**
- Per player: `x_tb_first, x_bp_faced_seq, x_sets_won, x_sv_gms_unfinished`.
- Per match: `x_points, x_point_gaps, x_game_gaps, x_games_not_ending_at_last_point, x_sets_recount, x_sets_stage0, x_sets_equal, x_tb_played, x_s0_status, x_games_two_servers`.
- From the server derivation: `x_games_without_evidence, x_games_evidence_against_alternation, x_sets_without_assignment, x_aces_against_assigned_server, x_double_faults_against_assigned_server, x_set_first_server_against_previous_set, x_tiebreak_evidence_against, x_score_steps_inconsistent`.

**What `complete` means.**
- For a box: the source's own finished flag (key statistics: `matchCompleted`; ManTennisData: no RET/W/O mark; TDI: a player won two sets). SirGenkii keeps no flag, so there `complete` means only that statistics are held.
- For a recount: no point or game gaps; every game ends at its last point (the game in progress at a retirement excepted); every point has a server; the set games equal Stage 0's score. For the handoff, the source's `pointsMissing` must also be False.

**Other files in `box/`.** Parquet files are untracked; everything else is tracked and holds only aggregates, ids and event names. No prices anywhere.

| File | Content |
|---|---|
| `atp_crosswalk.parquet` / `.json` | `code, pid, votes, total, share`; the JSON has counts and conflict examples |
| `atp_handoff_records.parquet` | Per-record intermediate of the handoff, for `--reuse` and the hand checks |
| `atp_handoff_copies.csv` | Matches held in both handoff folders, and how many are identical |
| `atp_server_rule_validation.csv` | Derived server against MatchBeats' own server |
| `atp_coverage.csv` | `reader, year, level_group, qual_level, stage0_matches, stage0_with_box, covered, covered_complete, shares`; also `any_atp_official` and `any_atp_recount` unions |
| `atp_recount_vs_box.csv` | `recount, box, joined_on, scope, year, count, n, equal, mean_diff, within_1` |
| `atp_recount_vs_box_diffs.csv` | `recount, box, count, diff, rows` |
| `atp_svgms_tiebreaks.csv` | Service-game differences explained by tiebreaks or not |
| `atp_mantd_vs_keystats.csv` | ManTennisData against each key-statistics copy, per count and season |
| `atp_events_disagree.csv` | `comparison, season_event, tournament_name, level_group, player_rows (≥20), share_any_count_differs, overall share, worst_count, worst share` |
| `atp_vs_stage0.csv` | Sanity check only: Stage 0 isn't a referee, and ManTennisData and Sackmann both come from the ATP's box |

## 3. Reader notes (observed)

**Handoff.**
- 75,190 records (deep folder 37,355, full folder 37,835) hold 37,908 matches, every one with key statistics; 32,101 have rally points.
- The two folders' key statistics are identical in all 37,282 matches held twice.
- 37,331 matches link: 36,054 by both ATP codes, 30 only through the match-timing link file (oriented inside the match).
- The link file agrees on all 37,170 matches both of us place.
- The key statistics' internal fractions are 100% consistent.

**Backfill.** 2,070 match codes, 2,045 linked (24 of the 25 unlinked are empty Indian Wells qualifying files). Key statistics for 575 matches; points for 573.

**Challengers.**
- The serve number is present on every point (38% second serves).
- Points are classified only as aces and double faults, which the recount doesn't need.
- 2,353 matches linked, 2,150 complete.

**Daily (2026).**
- 105 raw files, all Shanghai 2026; 99 linked.
- The `matchCompleted` flag reads False on 12 finished matches whose service games fit the score.
- The staged daily tables hold only speeds and first serves in, hence the raw route.

**SirGenkii.**
- Its key statistics are given as shares, so I recovered counts as the integers that reproduce the shares, within a plausible range of points per service game and matching total points won. The absent player's counts come from the present player's return shares.
  - The result is unique for 722 of 929 present players and 720 of 929 absent ones; the rest are left NaN.
  - The absent player's aces, double faults and break points can't be recovered.
- Against Stage 0: aces and double faults 100%, break points 99.8–99.9%, serve-point counts 99.5–100%.
- In the recount, rally matches are identified by their own players because of the AO 2025 mix-up; 613 of 922 are complete.

**TDI.**
- 5,347 singles: 3,670 linked through the link file and 119 by my event linker.
- The 1,558 unlinked are mostly Challenger qualifying from June 2026 on (which Stage 0 lacks) and October 2026 matches.
- The serve number comes from the label, the break points from the scores before each point; game 13 is the tiebreak.

**ManTennisData.**
- 145,243 rows; 132,409 linked.
- No box is held for 4,810 of 4,811 retirements or for any of the 753 walkovers.
- Internally consistent on 100% of rows.

## 4. Q1: coverage (observed, `atp_coverage.csv`)

Stage 0 men's matches covered, 2018–2026 (covered / complete, where they differ):

| Source | Slam (4,445) | Tour main (17,698) | Challenger (50,412) | Qualifying (32,230) |
|---|---:|---:|---:|---:|
| Any ATP source | 4,253 | 17,196 | 48,201 | 30,804 |
| ManTennisData | 4,253 | 17,080 | 47,842 | 30,665 |
| Handoff key statistics (2021–24) | 0 | 6,689 | 18,282 | 12,360 |
| Handoff recount | 0 | 5,571 / 4,745 | 15,563 / 13,946 | 10,449 / 8,902 |
| TDI recount | 0 | 729 / 686 | 2,681 / 2,489 | 378 / 354 |
| Challenger recount | 0 | 0 | 1,576 / 1,445 | 777 / 705 |
| Backfill recount | 0 | 436 / 403 | 0 | 130 / 103 |
| SirGenkii recount | 14 | 637 / 426 | 0 | 271 / 173 |
| **Any recount, complete** | 14 | 6,188 | 17,793 | 10,194 |

Complete recounts per season (Challenger / qualifying / tour main):

| Season | Challenger | Qualifying | Tour main |
|---|---:|---:|---:|
| 2018–19 | 0 | 0 | 43 |
| 2020 | 0 | 34 | 113 |
| 2021 | 427 | 275 | 311 |
| 2022 | 4,961 | 3,185 | 1,597 |
| 2023 | 5,128 | 3,213 | 1,529 |
| 2024 | 4,779 | 2,945 | 1,480 |
| 2025 | 113 | 285 | 451 |
| 2026 | 2,385 | 257 | 664 |

*Inference:* by box, the family can referee almost every men's non-Slam match. By an independent point record, it can do so densely only in 2022–2024, plus TDI's mid-2025–2026.

## 5. Q2: recounts against their own system's key statistics

**The server rule.**
- Rally files don't say who served, so I derive it. Evidence per game:
  - an ace is won by the server;
  - a double fault is lost by the server;
  - a side holding a break point is the receiver;
  - consecutive scores, written server first, show which side won each point.
- Games alternate within a set; tiebreaks follow the A-B-B-A pattern.
- Validation against the explicit server in MatchBeats (observed): 83,017 of 83,025 backfill points and 393,956 of 394,009 Challenger points agree. The 61 misses sit in 10 matches where the two files number points differently (*inference:* misalignment, not the rule).
- In the handoff: 66 of 681,852 games contradict the alternation, 22 sets get no assignment (those matches are incomplete), and 67 aces and 26 double faults contradict the assigned server.

**Agreement per count**, complete rows (% equal; `atp_recount_vs_box.csv`):

| Recount vs box | Rows | ace | df | svpt | first_in | first_won | second_won | sv_gms | bp_faced | bp_saved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Handoff rally vs handoff key statistics | 55,186 | 99.98 | 99.99 | 99.90 | 99.90 | 99.94 | 99.97 | 100 | 99.94 | 99.96 |
| Challenger MatchBeats vs ManTennisData | 4,278 | 100 | 99.98 | 99.67 | 99.77 | 99.91 | 99.93 | 100 | 99.86 | 99.88 |
| Challenger MatchBeats vs handoff key statistics | 4,298 | 99.93 | 99.84 | 99.54 | 99.63 | 99.77 | 99.81 | 99.86 | 99.72 | 99.81 |
| Backfill MatchBeats vs backfill key statistics | 1,008 | 98.41 | 98.21 | 97.82 | 97.82 | 97.92 | 98.02 | 98.02 | 98.31 | 98.61 |
| SirGenkii rally vs SirGenkii key statistics | 592–1,184 | 99.32 | 100 | 100 | 98.39 | 98.39 | 98.39 | 100 | 99.83 | 100 |
| TDI points vs TDI statistics | 6,774 | 99.97 | 99.76 | 99.75 | — | — | — | 100 | 99.88 | 100 |

**Why counts differ.**

*Service games.* Three definitional differences, each settled by the data and each matching Stage 0, whose service games equal the complete handoff recounts 100%:
- **No tiebreaks.** All 15,792 handoff rows with a tiebreak equal a recount that leaves tiebreaks out (likewise SirGenkii, TDI and the Challengers).
- **No unfinished game at a retirement.** Before I adopted this, 290 handoff rows were off by one; all were retirements, and Stage 0 sided with the key statistics in 286.
- **One server per game.** 23 TDI matches had a point inside a game naming the other server, which pushed totals above the score; such a game now counts for the player who served most of its points.

*Key-statistics files that stop early.* 13 handoff rows are 10–45 serve points short; ManTennisData and Stage 0 side with the recount in 12. *Inference:* the handoff fetched those files mid-match.

*Off by exactly one point.* About 0.1% of complete handoff rows differ by one serve point. ManTennisData and Stage 0 equal the key statistics there, but all three are copies of the same ATP box. The Challenger recount, which uses explicit servers, shows the same rate, so the derivation isn't the cause. **Unknown** which side is right.

*The `pointsMissing` flag.* 1,392 handoff matches carry the flag yet pass every gap and score check. Their serve points agree with the key statistics only 93.75%, against 99.90% without the flag, so I mark them incomplete (`x_complete_before_source_flag` keeps my engine's verdict).

*Break points.*
- The Infosys flags mark the receiver's chance before the point. Flag-based and score-based counts agree 99.86% in the handoff; 97.4% in the backfill, which includes the no-ad Next Gen Finals.
- TDI's flag is set on exactly the 49,665 points after which the receiver holds a break point, but on only 10,063 of the 49,636 points actually played at one; break points therefore come from TDI's scores.
- SirGenkii's p1 and p2 flags are each set about half the time whoever serves, so a flagged point is charged to the derived server.

*First serves.*
- TDI's serve label and its fault counter disagree on 518 points. Against ManTennisData, the label agrees 97.1% and the faults 92.9%, so the label is used.
- At Miami 2025, SirGenkii's rally files move 1–3 points between first and second serve in 12 of 27 matches, against its own key statistics.

## 6. Q3: ManTennisData against the key statistics (observed)

Joined on the ATP's own match key and player code, so no Stage 0 link is involved:

| Copy | Equal per count |
|---|---|
| Handoff, 2022–24 | 99.90–100% |
| Handoff, 2021 | 98.1–98.9% |
| Handoff, 2018–19 Finals | first serves in 70–87% |
| Backfill | 95.6–98.3% |
| SirGenkii | 100% |
| Daily (118 rows) | 100% |

- The exceptions are events (`atp_events_disagree.csv`):
  - the 2018–2019 ATP Finals: ±1 first serve, the ATP's two publications differing;
  - Nur-Sultan 2021 qualifying (60% of rows), Metz 2021 qualifying (50%), Washington 2021 qualifying (8%): key statistics cut short;
  - Columbus CH 2021 qualifying: double faults, 27% of rows.
- TDI's statistics equal TDI's own points (§5).

## 7. Q4: other systematic findings

1. **SirGenkii's copy:** key statistics for one player per match (all 929), as shares; AO 2025 rally files under other matches' codes (14 of 14); break-point flags with no side; final points often missing. *Inference:* the third party's scraper, not the ATP, since the other copies show none of this.
2. **Key-statistics files cut short** in the handoff (2021) and the backfill (2021 qualifying), still marked completed.
3. **The daily file's `matchCompleted` reads False** on 12 of 99 finished matches.
4. **Box against points within one system:** single-point differences in about 0.1–0.3% of rows. The worst events are Brisbane 2024 qualifying (12.5%), Madrid 2023 qualifying (10.7%), Canberra CH 2024 qualifying (9.1%) and Auckland 2024 (8.3%).
5. **Results contradicting Stage 0**, for your results part:
   - `atp|2024-9651|Q2|atp:131951|atp:207815`: Stage 0 has Cukierman d. Justo 6-4 2-0 RET; the ATP (handoff QS019 and ManTennisData) has Justo d. Cukierman 6-1 6-0.
   - `atp|2018-3627|Q2|atp:121816|atp:200325`: Stage 0 has a walkover; ManTennisData has Ruusuvuori d. Di Nicola 6-0 6-1 with a box.
   - `atp|2023-8994|Q2|atp:144750|atp:210506`: the handoff's winner flag (status 'D') names Michelsen, against ManTennisData and Stage 0 (Harris). The handoff is the odd one.
6. **Known Stage 0 facts reappear in the sanity table** (not findings of this part): 2026 qualifying first serves from TML differ from the ATP's (Shanghai qualifying 36% equal, main draw 100%); Slam rows come from other systems.

## 8. Checks

- **Hand checks:** 55 matches, 5 per reader, against the raw handoff JSON, the decrypted daily files or the staged rows, plus direct tallies for the recounts. All counts and orientations were right.
  - The printout was re-run on the final outputs: identical, except the handoff recount's sample, which changed with the `pointsMissing` rule and was read again.
- **The linker agrees with the match-timing link file** on all 37,170 shared matches.
- **Winner checks:** at most 0.005% of rows differ from Stage 0; these are the 3 matches in §7.
- **Rule 3:** the live Stage 0 files and the infosys and tdi link files still equal the manifest's SHA-256.
- **Rule 2:** writes were limited to `atp_*` code and `box/`; no network, GPU or git changes.

## 9. Limits

- **No independent referee within the family** for the one-point differences; your cross-family comparison can settle them.
- **SirGenkii:** about 22% of reconstructions are ambiguous and left NaN; a set-by-set reconstruction might resolve more and wasn't attempted.
- **Thin handoff years:** 2018–2019 hold only the Finals, 2021 about 1,500 records, and 2020 nothing.
- **The daily files** hold only Shanghai 2026.
- **ManTennisData** has no box for retirements.
- **No tests** were written.
- **The ATP-site scrape** belongs to subagent 3 (`tp_atp_scraped`) and isn't duplicated here.

## 10. Surprises worth re-checking

1. SirGenkii's key statistics hold one player per match, as shares.
2. The handoff's `pointsMissing` flag carries information the point numbers don't.
3. TDI's break-point flag marks the state after the point, and its fault counter overstates first serves.
4. In the rally files, the receiver's win on the opponent's double fault is often filed as `t1win`: about half of player 2's double faults in the handoff, almost all in the Challenger files. A reader that takes `t1win` to mean player 1 served would be wrong on those points.
5. Some key-statistics files are mid-match snapshots still marked completed.
