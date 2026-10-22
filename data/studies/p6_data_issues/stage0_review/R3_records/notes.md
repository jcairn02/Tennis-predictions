# R3 review (independent records and a simulated fix): notes and process log

Reviewer R3 of three under the rule of 8 Oct 2026 (docs/decisions/2026-10-08-corrupt-data-fixes.md).
Written while working; corrected by adding, never by rewriting.

## The brief (verbatim, from the coordinating agent, 14 Oct 2026)

> You are an independent reviewer under the project's rule of 8 Oct 2026 (docs/decisions/2026-10-08-corrupt-data-fixes.md): a Stage 0 row is corrected only where three independent reviewers each confirm (a) it is corrupt beyond reasonable doubt and (b) the fix is clear, unique and correct, naming the same rows, operation and values. You are one of three; do not read the other reviewers' folders. Work read-only: write only your own folder, data/studies/p6_data_issues/stage0_review/R3_records/. Use ./python.sh (the project's tennis environment) from C:\Users\zerom\Documents\Tennis-predictions; scratch scripts go in your folder. Make no request to SofaScore, Flashscore, TennisLive, the ITF or the WTA (collectors are running on those hosts). Do not edit any existing file, run no state-changing git command, delete nothing, and read no model result.
>
> The claim to review (a study of 14 Oct 2026, docs/studies/p6_data_issues/):
>
> Group G1, Tenerife 2024. Stage 0 (data/studies/predictability_diagnostic/stage0_matches.parquet) holds 31 men's Challenger matches with tournament_id 2024-2847, tournament_name "Tenerife 1", tournament_date 2024-01-21, source "tml" (Tennis My Life's file data/raw/public_dump/tennis_my_life/2024_challenger.csv, rows 280-310 by Stage 0's source_row). The claim: these are the matches of the third Tenerife Challenger of 2024 (played 26 Feb - 3 Mar 2024; final Kukushkin d. Gigante 6-2 2-0 ret.), not of the first (Sackmann's "Tenerife CH", 2024-9623, week of 15 Jan, which Stage 0 also holds), so their date is corrupt. Proposed fix: tournament_date 2024-01-21 -> 2024-02-26 for exactly these 31 rows (match ids unchanged; the name left as it is). The consequence claimed: the leak-proof clock (data/studies/match_timing/timing.parquet; es and lf in days since 1970; a result counts from lf + 1) closes their windows on 28-31 Jan 2024, so each result counts about a month before it was played, and 136 later Stage 0 matches of the same players read them early.
>
> Group G2, Australian Open 2021 qualifying. Two Tennis-My-Life-only walkover rows, atp|2021-580|Q2|atp:106045|atp:208013 and atp|2021-580|Q2|atp:106408|atp:202103, dated 2021-02-08 (the main draw's date), from data/raw/public_dump/tennis_my_life/atp_quali/2021_atp_quali.csv rows 98 and 106. The claim: that qualifying was played 10-13 Jan 2021 in Doha; proposed fix: tournament_date -> 2021-01-10 (Sackmann's date for the same qualifying draw).
>
> Evidence the study used (use it if you like, but verify, never trust): TennisLive's listings, data/dump/points/tennislive/listed.parquet (event_name, start_utc, player names, score); SofaScore's events, data/dump/points/sofascore_editions/events.parquet and data/dump/points/sofascore/events.parquet; Sackmann's staged files, data/dump/matches/sackmann_archive/atp/; Tennis My Life's staged files, data/dump/matches/tennis_my_life/; the study's tables, data/studies/p6_data_issues/tml_misdates/ (stage0_date_corrections.csv, misdated_matches.csv.gz, clock_windows.csv, clock_leak_readers.csv).
>
> Your lens: R3, independent records and a simulated fix. Check against records independent of the study's linking: the web (Wikipedia and atptour.com only, with WebSearch and WebFetch: the dates, draws and results of the 2024 Tenerife Challengers I, II and III, and of the 2021 Australian Open men's qualifying). Then simulate the fix on a copy (never on the live tables): set the proposed dates and check that (i) no player then has two matches on overlapping days, (ii) the timeline's class window for a Challenger dated 2024-02-26 (the rules in src/eda/match_timing/timing.py) contains each match's play day, and (iii) in date order each of the 31 then follows the players' matches of the preceding weeks. The same for G2 where it applies.
>
> Deliver data/studies/p6_data_issues/stage0_review/R3_records/votes.json: a list with one object per group, {"group": "G1" or "G2", "corrupt_beyond_doubt": true/false, "fix_clear_unique_correct": true/false, "rows": [the Stage 0 match ids you confirm], "operation": "set tournament_date", "value": "YYYY-MM-DD", "objections": [...], "evidence": [...]}, and a short notes.md. Your final message: the two votes and a one-paragraph reason for each, in plain words. Keep to what your lens needs: about 15-20 minutes of work.

## Interpretation acted on

* This notes.md doubles as the process log (the brief asks for a short notes.md; the project's process-log rule says scale it to the work).
* "Independent records" = Wikipedia and atptour.com pages, read with WebSearch/WebFetch. Not the study's linking tables. The study's tables are read only to check what they say, never as the evidence for a vote.
* "Simulate the fix on a copy" = load Stage 0 into memory (or a scratch copy in this folder), change the dates in memory, and recompute the class windows with timing.py's own rules (imported or re-implemented, read-only). Nothing is written to timing.parquet or Stage 0.
* Readings set aside: I do not re-run the study's linker or judge its other groups; I do not check the "136 readers" number beyond what the simulation needs (it is a consequence, not part of the vote).
* I do not open stage0_review/R2_attack/ or any other reviewer's folder.

## Plan

1. Web: Tenerife Challengers I, II, III 2024 (dates, finals, draws) and AO 2021 men's qualifying (place, dates, the two walkover pairs).
2. Stage 0: pull the 31 G1 rows and the 2 G2 rows; compare names/results to the web draws.
3. timing.py: read the class-window rules; compute the window for a Challenger dated 2024-02-26 (and for AO qualifying dated 2021-01-10).
4. Simulate: (i) overlap of the same player's matches by day windows, (ii) window contains play day (from the web), (iii) order versus the players' surrounding matches.
5. votes.json + finish this log.

## Log

Session: Claude Code subagent (R3), 14 Oct 2026. No context summary so far.

### 1. Web records (accessed 14 Oct 2026; WebSearch + WebFetch, Wikipedia and atptour.com only)

* Wikipedia "2024 Tenerife Challenger" (https://en.wikipedia.org/wiki/2024_Tenerife_Challenger): 15-21 Jan 2024, hard; Nakashima d. P. Martinez 6-3 6-4.
* Wikipedia "2024 Tenerife Challenger II" (https://en.wikipedia.org/wiki/2024_Tenerife_Challenger_II): 19-25 Feb 2024; Gigante d. Travaglia 6-2 6-4.
* Wikipedia "2024 Tenerife Challenger III" (https://en.wikipedia.org/wiki/2024_Tenerife_Challenger_III): 26 Feb - 3 Mar 2024, hard; Kukushkin d. Gigante 6-2 2-0 ret. Page flagged "relies on a single source".
* Wikipedia singles draws (wikitext via action=raw, extracted by WebFetch as tables):
  * III (https://en.wikipedia.org/wiki/2024_Tenerife_Challenger_III_%E2%80%93_Singles): 31 main-draw matches; R32 includes Brancaccio d. Piros 1-6 6-2 6-3, Landaluce d. Llamas Ruiz 7-6 1-0 ret, Kukushkin d. Agamenone 7-6 6-3, ...; F Kukushkin d. Gigante.
  * I (https://en.wikipedia.org/wiki/2024_Tenerife_Challenger_%E2%80%93_Singles): R32 is a different draw (Fognini d. Martineau, Nakashima d. Landaluce, Barranco Cosano d. Brancaccio 7-6 3-1 ret, Kukushkin d. Damm, Llamas Ruiz d. Kachmazov, Berankis d. Agamenone, Meligeni Alves d. Kuzmanov, Maestrelli d. Rincon, Moro Canas d. Martin Tiffon, ...).
  * II (https://en.wikipedia.org/wiki/2024_Tenerife_Challenger_II_%E2%80%93_Singles): again a different draw (Marie d. Piros, Kuzmanov d. Misolic, ..., F Gigante d. Travaglia).
* atptour.com results archives:
  * https://www.atptour.com/en/scores/archive/tenerife/2847/2024/results : header "Tenerife 3", "26 Feb - 3 Mar, 2024"; 31 main-draw matches listed with scores (all under one header "Mon, 26 February, 2024": the archive gives no per-match day).
  * https://www.atptour.com/en/scores/archive/tenerife/9623/2024/results : "Tenerife 1", 15-21 Jan 2024; F Nakashima d. Martinez.
  * https://www.atptour.com/en/scores/archive/tenerife/2839/2024/results : "Tenerife 2", 19-25 Feb 2024; F Gigante d. Travaglia.
  * So the ATP's own tournament id 2847 is Tenerife 3; 9623 is Tenerife 1; 2839 is Tenerife 2.
* atptour.com news (https://www.atptour.com/en/news/kukushkin-gigante-tenerife-challenger-2024-final), published 4 Mar 2024: the final was on Sunday (= 3 Mar 2024); Kukushkin came through qualifying; his previous title was Manama about two weeks earlier.
* AO 2021 qualifying:
  * atptour.com news of 17 Dec 2020 (https://www.atptour.com/en/news/atp-announces-updated-start-to-2021-calendar): "Australian Open men's qualifying will take place from 10-13 January in Doha".
  * Wikipedia (https://en.wikipedia.org/wiki/2021_Australian_Open_%E2%80%93_Men%27s_singles_qualifying, wikitext): held at the Khalifa International Tennis and Squash Complex, Doha; RD2 Sweeny d. Kudla w/o; RD2 Vilella Martinez d. Cerundolo w/o. (The wikitext itself gives no calendar dates.)
  * atptour.com AO 2021 results archive (https://www.atptour.com/en/scores/archive/australian-open/580/2021/results): files the qualifying under the main draw's id 580 and header "8-21 February 2021"; Q1 Kudla d. Benchetrit, Cerundolo d. Garcia-Lopez; Q2 Sweeny / Kudla and Vilella Martinez / Cerundolo with no score (00:00); Q3 Stakhovsky d. Sweeny, Vilella Martinez d. Wu. This is the likely origin of TML's 2021-02-08 date (the ATP lists the qualifying under the main draw's week).

### 2. Stage 0 rows (look_rows.py, read-only)

* G1: the 31 rows of 2024-2847 ("Tenerife 1", 2024-01-21, tml, source_row 280-310). Every one of the 31 (players, round, winner, set scores, retirements) equals the Wikipedia/atptour.com Tenerife 3 draw. None matches the Tenerife 1 draw (e.g. Landaluce lost the Tenerife 1 R32 to Nakashima, but here wins an R32 over Llamas Ruiz).
* Stage 0 also holds 2024-9623 "Tenerife CH" 2024-01-15 (sackmann, 31 + 16 qual) and 2024-2839 "Tenerife 2 CH" 2024-02-19 (sackmann, 31 + 17 qual). No other 2024 Tenerife event, so no Sackmann copy of Tenerife 3 exists that the fix would duplicate.
* Timing now: no source links at all for the 31 (sources empty, rejected_links 0); windows from the class/rule (empirical+rule) on anchor 2024-01-22: R32 19-28 Jan, R16 21-29 Jan, QF 23-30 Jan, SF 23-31 Jan, F 24-31 Jan.
* G2: the two TML rows (2021-580 "Australian Open" 2021-02-08, Q2, walkover, tml_link tml_only) have exact twins from Sackmann in Stage 0: atp|2021-581|Q2|atp:106045|atp:208013 and atp|2021-581|Q2|atp:106408|atp:202103 ("Doha Aus Open Qualies", 2021-01-10, walkover, source rows 2438 and 2451). Same players, same round, same walkover. So the TML rows are duplicates the Sackmann link missed, not unique records.
* G2 timing now: named rule "Australian Open" 2021 Q2 (schedule_rules.csv row 87: offsets -29..-26 from the main draw's anchor, +-2 margin) puts both windows at 8-15 Jan 2021, which already holds the true day (12 Jan). The proposed fix changes the date but not the name, so the same named rule would be applied from the new anchor (Mon 11 Jan 2021): 11-18 Dec 2020, a month BEFORE the play day. To be confirmed by simulation (step 3).

### 3. Link files and TML's raw file (read-only)

* data/studies/match_timing/links/: infosys.parquet holds 30 of the 31 G1 ids (linked inside ATP event 2847 by ATP ids or names; no day in them). flashscore_unlinked.parquet (a helper table timing.py never reads) lists all 31 G1 rows and both G2 rows as "player pair in Flashscore, but not in the date window" (or one player only): the pipeline's own sign that the date window is wrong. No usable dated link exists for any of the 33 rows, which is why the simulation below needs no link logic.
* data/raw/public_dump/tennis_my_life/2024_challenger.csv: all three Tenerife events (2839, 2847, 9623) are labelled "Tenerife 1" with tourney_date 20240121. The first event's label was copied onto the other two. Stage 0 took 2839 and 9623 from Sackmann (right dates) and 2847 only from TML. TML's own date convention in that file is mixed (130 Sundays, 32 Mondays, 28 Saturdays, mostly the final's day), but Stage 0's TML-sourced Challenger events are on its start-Monday convention: 110 of 113 since 2023 on a Monday, 2 Tuesday, and only 2024-2847 on a Sunday. So 2024-02-26 is the convention's value; 2024-03-03 (TML's end-day style) or 2024-02-25 would not be.

### 4. Simulation (simulate_fix.py -> simulate_fix.log, sim_*.csv)

* Method: timing.py's own anchor_day, rule_windows (schedule_rules.csv), the stored class windows (timing_classes.csv), the build() combination rule and draw_narrowing, applied to an in-memory copy of the rows. timing.build() is never called and nothing outside this folder is written. Validation: on the current dates the code reproduces timing.parquet's es/lf for 31/31 G1 rows and 2/2 G2 rows.
* G1, with tournament_date 2024-02-26: windows R32 23 Feb-3 Mar, R16 25 Feb-4 Mar, QF 27 Feb-5 Mar, SF 27 Feb-6 Mar, F 28 Feb-6 Mar (rule label unchanged, "ATP Challenger (all categories)"; the name "Tenerife 1" does not enter it).
  * (ii) Play days come from the local copies of TennisLive (31/31) and SofaScore (24/31; they agree wherever both exist). R32 26-27 Feb, R16 28-29 Feb, QF 1 Mar, SF 2 Mar, F 3 Mar (the ATP news confirms the final on Sunday 3 Mar). 31/31 fall inside the new windows, 0/31 inside the current ones. Web-only check: every new window meets 26 Feb-3 Mar, and the final's holds 3 Mar.
  * (i) After the fix, none of the 32 players has another match with an exact day inside his Tenerife 3 span, nor a window touching any of his Tenerife 3 play days. Before the fix, 48 exact-dated matches of these players lie inside the misdated windows (19-31 Jan). Examples: Gigante played the Nonthaburi 3 QF to final 19-21 Jan; Kukushkin lost the Tenerife 1 QF on 19 Jan; Landaluce and Demin were at M15 Manacor.
  * (iii) After the fix, each player's Tenerife 3 matches are contiguous in Stage 0's chrono order. They follow the previous event (23 of 32 players from Tenerife 2, the rest from Manama, Pune, M15 Villena, M25 Vila Real or AO qualifying) and precede the next, with days in order for all 32.
  * The leak now: 136 distinct matches of these players start (es) after a misdated result counts (old lf + 1) and before that match was played. My code is independent of the study's and reproduces its 136. A further 171 matches dated 22 Jan-25 Feb sit after the misdated rows in Stage 0's order.
* G2, with tournament_date 2021-01-10 and the name kept as "Australian Open": the window becomes 2020-12-11..2020-12-18 and the Q2 day (12 Jan 2021) falls outside it (today: 2021-01-08..2021-01-15, inside). As a variant, the same date with Sackmann's name ("Doha Aus Open Qualies", label AO21_QUALIFYING) gives 2021-01-10..2021-01-14, inside. (i) fails either way, because the Sackmann twins stay: each player would hold the same Q2 walkover twice on the same date and round.

### 5. Votes (make_votes.py -> votes.json)

* G1: corrupt yes; fix (set tournament_date 2024-02-26 on the 31 rows) clear, unique, correct: yes. No blocking objection. A remark that does not block: the name stays "Tenerife 1" although the event is Tenerife 3. The timeline does not read it (checked), but any name-based join elsewhere would still see the wrong name. I did not check other consumers of tournament_name.
* G2: corrupt yes (the rows are second copies of Sackmann's two walkovers and sit four weeks late in Stage 0's order); fix as proposed: no. It fails checks (i) and (ii), and the clear fix is a different operation: drop or merge the two TML rows into the Sackmann twins atp|2021-581|Q2|atp:106045|atp:208013 and atp|2021-581|Q2|atp:106408|atp:202103.
* Results were seen before the votes were set; the votes were not changed after seeing any other reviewer's work (none was read).

## Claims and their evidence

| Claim | Evidence |
|---|---|
| The 31 G1 rows are Tenerife 3, not Tenerife 1 | atptour.com archive 2847 (31/31 results equal); Wikipedia III draw; I draw disjoint |
| Their true dates are 26 Feb-3 Mar 2024 | atptour.com header; Wikipedia; ATP news (final Sun); local TennisLive/SofaScore days 31/31 |
| 2024-02-26 is the unique value | ATP start Monday; Stage 0's TML Challenger events on start Mondays (110/113) |
| The fix is safe for the clock | simulate_fix.log: new windows hold 31/31 play days; (i) and (iii) clean |
| G2 rows are duplicates | Stage 0 Sackmann rows 2438/2451 of 2021-581 with the same players, round and winner (W/O) |
| G2 fix as proposed breaks the clock | simulate_fix.log: 11-18 Dec 2020 window, without 12 Jan; today's 8-15 Jan holds it |

## Threats to validity

* The per-match play days come from local copies of TennisLive and SofaScore, which the study also used. They are not independent of the study. The web pages fix only the event's span and the final's day. The G1 window check still holds on web facts alone, because each round's window covers every day of the event that round could be played on.
* The WebFetch answers are a model's extraction of the pages, not raw text. The G1 draw was extracted twice, from Wikipedia and from atptour.com, and the two agree with each other and with Stage 0. Spellings were normalized by eye.
* The simulation does not re-run the linkers. After a real fix, Flashscore and others may attach exact days to the 31 rows, which can only narrow their windows towards the true days.
* I did not check how walkovers enter the features (whether the G2 duplicates do harm). That does not change the G2 vote, which rests on the fix being wrong.

## A re-design would

* Fetch per-match days from an official order of play (the ATP's daily schedules) rather than the listing copies, if available for 2024 Challengers.
* Re-run timing.build() end to end on a sandbox copy with the fix and the linkers, and diff timing.parquet.

## Reviewer checklist and reproduction

* `./python.sh data/studies/p6_data_issues/stage0_review/R3_records/look_rows.py g1` (and `g2`): the rows.
* `./python.sh data/studies/p6_data_issues/stage0_review/R3_records/simulate_fix.py`: the validation line must read True (31/31) and True; check the (ii), (i) and (iii) lines.
* `./python.sh data/studies/p6_data_issues/stage0_review/R3_records/make_votes.py`: rebuilds votes.json, asserting the row ids, source rows 280-310 and the check results.
* Web sources: listed in section 1, all accessed 14 Oct 2026.

