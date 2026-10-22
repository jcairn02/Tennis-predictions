# The data issues P6 found: subagent reports (verbatim)

Each subagent's final message, as received. Briefs: [briefs.md](briefs.md). What the lead re-checked is recorded in the process log.

## B. Tennis My Life's misdated editions (received 14 Oct 2026, about 08:28 local; its files are of 08:27)

> I found 67 misdated Tennis My Life (TML) editions in 2018-2026, all ATP Challengers. Stage 0 has a wrong date for only 33 matches. The leak-proof clock leaks for 31 of them, and the data map holds 1,575 matches twice. Nothing existing was modified.
>
> Method, in short: every TML row of 2018-2026 (102,035 rows, 3,660 editions) was linked to Sackmann's row, TennisLive's listing day, SofaScore's start and TDI's 2026 day. A link needs the same two players and identical set scores. 97,099 rows got a play day.
>
> ## 1. Misdated and lumped editions
> Lists: `misdated_editions.csv`; every edition: `editions.csv`.
>
> - **Misdated, dated in another week (observed): 67 editions, 2,093 matches.**
>   - By season: 2018: 4, 2020: 2, 2021: 21, 2022: 13, 2023: 10, 2024: 14, 2025: 3.
>   - 64 are dated early, by 7 to 309 days. TML gives a later edition an earlier edition's date and often its name. Examples:
>     - 2021-9466/9470/9496/9503/9498 "Biella 1", dated 14 Feb, are really Biella 3-7 (8 Mar to 31 May).
>     - 2018-444 "Poprad Tatry" is the Bratislava Challenger of 5 Nov 2018.
>   - 3 are dated late:
>     - Nottingham 2025-2907: +182 days, played 6-11 Jan 2025.
>     - Targu Mures 2025-3021: +8 days, played 8-14 Sep.
>     - Manama 2025-9635: +287 days, played 10-15 Feb 2025 (Sackmann's Manama CH).
>   - For 66 of the 67, the true start is Sackmann's date, which the play days confirm. For Tenerife 2024-2847 (really the third Tenerife Challenger of 2024) it comes from the play days alone, because Sackmann lacks that edition.
> - **Lumped:** 46 same-name-and-date groups contain a misdated member. Their 53 other members are dated within their own week.
> - **Name only:** 20 more pairs (40 editions) are consecutive editions under one name and date, both within their week.
> - **Rows dated apart:** the 2021 Australian Open qualifying (110 rows) was played 10-13 Jan in Doha and Dubai but is dated 8 Feb.
> - **Also found, a separate pattern:** 649 Challenger editions of 2018-2024 (21,151 matches) are dated 5-7 days late, by the final's day. None appear from 2025 on, and none reach Stage 0's dates.
> - **No problems found** in TML's WTA files, the ATP tour level, or any of the 104 Challenger editions since June 2026 that could be checked.
>
> ## 2. What Stage 0 holds
> - **Mostly the true date (observed).** Of the 3,991 matches in misdated, lumped and dated-apart editions, 3,954 are Sackmann's rows carrying his date. None is held twice.
> - **TML-only rows:** 37.
>   - Four take Sackmann's event date through Stage 0's event map.
>   - 33 carry TML's wrong date, more than 7 days off:
>     - 2024 Challenger: 31 (Tenerife 2024-2847; Stage 0 has 21 Jan 2024, the true start is 26 Feb). All 31 are evaluation matches.
>     - 2021 Slam qualifying: 2 (Australian Open walkovers; Stage 0 has 8 Feb, the true date is 10 Jan).
> - **No other wrong dates:** checking every one of Stage 0's 6,082 TML-only rows found none beyond these 33.
>
> ## 3. The leak-proof clock
> - **Only Tenerife leaks (observed).** Of 26,503 checked windows, 26,472 contain the play day.
> - **The 31 Tenerife matches:** their windows end 28-31 Jan 2024, 29-32 days before they were played (26 Feb to 3 Mar). Each result therefore counts about a month before it happened.
>   - Their windows also open 38-39 days early, so their own inputs are about five weeks stale. That is stale, not a leak.
>   - 136 later Stage 0 matches of the same players (93 of them evaluation matches), starting 29 Jan to 24 Feb 2024, read these results early (`clock_leak_readers.csv`).
>   - The clock has no exact day for these matches: the timing link files never offered one.
> - **The 2 Australian Open walkovers:** their window (8-15 Jan 2021, from a named rule) holds the qualifying week, so no leak.
> - **No other misses.** No window ends more than 7 days late. The 18 cases that differ by one day sit inside the evidence's ±1-day tolerance.
>
> ## 4. The data map
> - **1,575 matches held twice (observed):** a TML copy at the wrong date plus Sackmann's copy (1,548) or API-Tennis's (27). All are Challenger main draws:
>
> | Season | Held twice |
> |---|---:|
> | 2018 | 118 |
> | 2020 | 30 |
> | 2021 | 589 |
> | 2022 | 265 |
> | 2023 | 203 |
> | 2024 | 309 |
> | 2025 | 61 |
>
> - **Linked once despite the misdate:** editions misdated within the map's linking window (dated 7-16 days early, or Targu Mures's 8 days late).
> - **A separate cause:** 11 more doubles in 2026 two-week events, because TML dates each 2026 match by its day (already noted in the Stage 0 audit).
>
> ## 5. Proposed fixes (prepared, not applied)
> - **(a) The data map:** apply `tml_edition_date_corrections.csv` (the 67 editions plus the 2021 Australian Open qualifying) to TML rows in the map builder (`load_tml` in `measure.py`) before linking. Each misdated TML copy would then sit at its true start and pick up Sackmann's row, merging the 1,575 doubles. Dating 2026 TML rows by their edition's first main-draw date, as Stage 0's rule C05 does, would merge the other 11.
>   - Caveat (inference): the SofaScore and TennisLive gap adapters find frozen targets by name and map date. Re-dated TML copies would need their old date kept for that lookup, or the lists re-keyed.
> - **(b) Stage 0 and the clock:** `stage0_date_corrections.csv` gives the 33 matches with Stage 0 match id, current date, true date and evidence. Apply the edition table at Stage 0's C05 step, then rebuild the clock.
>   - This is lower-level history corrected from sources other than TML's own files, so under the project's rules it must go through the candidate test (`run_chain.py --setup --candidate`, then `compare.py`).
>   - It is a repair; its effect is far below what the comparison can resolve, so the comparison serves only as a harm check.
> - **(c) Prevention:** TML has been Stage 0's only Challenger source since June 2026, and the misdating recurred in 2025. Running this edition check weekly would catch a new case before it reaches Stage 0.
>
> ## Not determined
> - **Team events:** 771 editions, mostly Davis Cup ties, have no play-day evidence and were not judged.
> - **The current week:** its 5 events (12 Oct 2026) can't be checked yet. Maia Open 2026 is "unresolved" and United Cup 2025 is too thin to judge.
> - **TennisLive's day** is a listing day, read as ±1 day; its time zone is unknown.
> - **7 Stage 0 rows** of the late-dated (final's-day) editions were not located; these are misses in my linking, not in Stage 0.
> - **Missing first editions (inference from name matching):** TML seems to lack Biella 1 2021, Taipei 1 2024 and Lima 1 2024, with their dates passed to the next edition.
> - **Already-known duplicates:** Stage 0 holds 46 Davis Cup and Billie Jean King Cup matches twice (the audit's finding C1), unrelated to dates; listed in `stage0_duplicates.csv`.
>
> The inputs read were the map of 13 Oct 17:49, Stage 0 of 13 Oct 21:13 and the clock of 13 Oct 21:16. I did not edit the parent's process log; my brief, thresholds and results still need recording there.
>
> Files are in `C:\Users\zerom\Documents\Tennis-predictions\data\studies\p6_data_issues\tml_misdates\`:
> - `misdated_editions.csv`
> - `editions.csv`
> - `misdated_matches.csv.gz`
> - `stage0_date_corrections.csv`
> - `tml_edition_date_corrections.csv`
> - `clock_windows.csv`
> - `clock_leak_readers.csv`
> - `map_doubles.csv`
> - `stage0_tml_only_check.csv`
> - `stage0_duplicates.csv`
> - `round_offsets.csv`
> - `summary.json`
>
> Script: `C:\Users\zerom\Documents\Tennis-predictions\src\eda\p6_data_issues\tml_misdates.py` (runs in under a minute with `./python.sh`).

## A. The WTA website records' mislabelled matches (received 14 Oct 2026, about 08:33 local; its files are of 08:30)

> I found every match's real event. The problem is limited to the last ten editions in the WTA website copy (those starting 7–14 Sep 2026). There is no sign of it anywhere earlier in 2018–2026. The model's feed holds 44 wrong copies; Stage 0 holds none. I changed nothing outside my own output folders.
>
> ## 1. The 55 matches and their real events
> - **Scope (observed).** The copy files 339 singles listings under ten editions: Montreux, Antalya and Barranquilla (WTA 125), W50 Guiyang and W50 Evora (ITF), all on 7 Sep; Guadalajara on 13 Sep; Valencia, Caldas, Ljubljana and Sao Paulo on 14 Sep. That is 187 distinct matches (186 played, 1 walkover).
> - **Where they really belong (observed).** All 187 were played the week of 7 Sep, in five events: Guiyang 47, Evora 45, Antalya 35, Montreux 35, Barranquilla 25.
>   - The copy holds no real result of the 13–14 Sep events.
>   - Only 49 of the 339 listings sit in the right edition, about what random assignment would give.
>   - For 122 matches, the two players' listings went to two different editions.
> - **Evidence (observed).**
>   - The WTA API's player-match records (P2(b)) carry the WTA's own tournament number on every row; they place all 187.
>   - TennisLive's listings agree on event, players and score for 185.
>   - The WTA live-scoring match lists agree for 92 of the 95 WTA 125 matches.
>   - Every match has the WTA API plus at least one independent source agreeing, and the score matches the website's in 187 of 187.
> - **The 55 map rows (observed).** None is a WTA 125 match. All are ITF W50 matches: 28 at Evora (Portugal), 27 at Guiyang (China); 31 main draw, 24 qualifying; played 6–10 Sep.
>   - The 27 under 7-Sep titles (Montreux 14, Antalya 8, Barranquilla 5) are the map's only copy of their match.
>   - The 28 under 14-Sep titles (Valencia 10, Caldas 9, Ljubljana 9) are second copies: 24 duplicate a correct row already on the map under the W50 title, 4 duplicate another wrong copy.
>   - Your examples: Adkar d. Zhang was Guiyang qualifying round 2, 6-3 7-5. Johnson d. Gao was Evora R16, 6-2 6-2. Wang d. Astakhova was Guiyang R32, 7-6(5) 7-5. Dodin d. Johnson was Evora R32, 4-6 6-2 6-2.
> - **Beyond the 55 (observed).** The map has 31 more wrong rows from these editions: 16 under the Guadalajara and Sao Paulo titles, at main-tour level, and 15 Guiyang/Evora swaps.
>
> The 55-row table is `map_55_true_events.csv`.
>
> ## 2. How widespread
> - **Against the WTA API, all of 2026 (observed):** before 7 Sep, all 53,951 listings found sit in the same edition as the API's. From 7 Sep, 288 of 337 sit in another edition.
> - **Against TennisLive, 2018–Aug 2026 (observed).** I tested whether each edition's matches all belong to one TennisLive event, which avoids name matching. 270,246 of 270,262 matches, across 5,031 editions, do; the worst edition is 97%. The ten September editions score 22–36%, each spread over all five real events.
> - **Against Sackmann's files, to June 2026 (observed):** the same result, 99.99%. The only exceptions are 8 Fed Cup / Billie Jean King Cup zone events, because Sackmann files each tie separately.
> - **Against the WTA live-scoring lists, 2019–2026 (observed):** the September editions have 0–20% of their matches in their own list. Every other WTA 125 or tour edition has 86% or more; the Slams 73–94%, probably because the lists miss part of qualifying (inference).
> - **Within the copy (observed).** Before September there are 73 cases of one match under two editions.
>   - 58 are real rematches with the same score: TennisLive has both meetings.
>   - 13 are the W15 Luque (15 Jun 2026) edition, which the copy lists twice under two ids. That is a duplicate, not a mislabel.
>   - 2 cannot be checked: neither TennisLive nor Sackmann has the pair.
> - **Pattern (observed):** listings with the round index 1 went to the 7 and 13 Sep editions, index 2 to the 14 Sep editions. It is unrelated to the known "second pseudo id" duplication.
> - **Cause (inference):** the dataset creator's join failed for the newest, incomplete week.
>
> ## 3. What the model sees
> - **Feed snapshot 20261013c (observed):** it holds all 186 played matches.
>   - 145 are held once, correctly.
>   - 41 are held once, but only under a wrong event:
>     - 27 at WTA 125 level, under Montreux, Antalya or Barranquilla, though they were W50 matches.
>     - 14 Guiyang/Evora swaps.
>   - 3 are held twice: once under the real W50 and once under a WTA 125 (two matches), or under two wrong events (one match).
>   - 24 of the 44 wrong copies also carry clay instead of hard court.
>   - For the 53 matches behind your 55 map rows: 23 are held once correctly, 28 once under a wrong event (26 of them at WTA 125 level), 2 twice.
> - **Side effect (observed):** Darya Khamutsianskaya appears in the feed under two player ids, `wta:222944` and `wta:wtaid:330116`. I did not investigate this further.
> - **The feed's own check caught it (observed):** 24 of its 28 "player in two main draws in one week" flags are this week. That check does not block a snapshot.
> - **Risk (inference):** the feed read an earlier, smaller WTA API player-match file than today's. A new run could add the correct copies while keeping the wrong ones, which would double those 41. Today is a Wednesday, the feed's scheduled day.
> - **Stage 0 (observed):** none of the 186 matches; nothing in it comes from the website copy.
>
> ## 4. Proposed fix (not applied)
> All 179 wrong-edition matches are indisputable: two or more sources agree on event, players and score.
>
> The simplest repair: drop the website copy's rows for editions starting on or after 7 Sep 2026 in both loaders, the data map's and the feed's. The WTA API player-match records hold all 187 matches under their true events, so nothing is lost. For the feed that is a lower-level change, so it would go through a new snapshot and its checks.
>
> If you prefer to correct row by row:
>
> | Table | Re-attribute to true event and level | Drop as duplicate |
> |---|---|---|
> | Map | 42 | 44 |
> | Feed | 41 (target tournament ids listed) | 3 |
>
> I also suggest making the "two main draws in one week" check block a snapshot.
>
> ## Could not determine
> - The creator's join code is not public, and I cannot tell whether wtatennis.com itself showed these labels on 24 Sep.
> - I can't tell why the feed lacks the correct copies of the 41: the file it read is no longer on disk.
> - SofaScore holds none of the five events (only W35 Reus that week).
> - The ITF live API starts on 13 Sep, so it cannot confirm these matches.
>
> The script is `src\eda\p6_data_issues\wta_site_mislabels.py` (about 2 minutes). Three files from my first pass (`feed_rows.csv`, `map_rows_ten_editions.csv`, `stage0_rows.csv`) are superseded but not deleted, per the cleanup rule.
>
> Files are in `C:\Users\zerom\Documents\Tennis-predictions\data\studies\p6_data_issues\wta_site\`:
> - `map_55_true_events.csv`
> - `sep2026_matches.csv`
> - `map_copies.csv`
> - `feed_copies.csv`
> - `edition_purity_tennislive.csv`
> - `summary.json`

## C. The three reviewers of the Stage 0 date correction

### R1, recompute (received 14 Oct 2026, about 08:59 local)

> I vote yes on the Tenerife group (G1) and no on the Australian Open qualifying group (G2).
>
> **G1, Tenerife 2024: yes on both points. Fix: set the tournament date to 2024-02-26 for the 31 rows.**
> Every number in the claim checks out from the raw files. Stage 0 holds exactly 31 rows with id 2024-2847, dated 21 Jan 2024, taken from lines 280-310 of Tennis My Life's 2024 Challenger file. That file names all three 2024 Tenerife Challengers "Tenerife 1" and dates all three 21 Jan, but only this one reaches Stage 0 from that file. All 31 matches equal, one for one, the third Tenerife Challenger's main draw in both TennisLive and SofaScore: same players, winner, games and tiebreak points. They were played 26 Feb to 3 Mar 2024; the final was Kukushkin beating Gigante 6-2 2-0, retired. As controls, Sackmann's January edition and his 19 Feb edition each match their own event 31 of 31, and Sackmann has no copy of the third edition. The clock's windows close on 28-31 Jan, so each result counts 28 to 31 days before it was played, and none of the 31 windows holds its real day. I counted the later matches that read them early on my own definition before opening the study's table: 136 matches (93 of them used for evaluation), and the set is identical to the study's, row for row. Simulating the fix with the clock's own code moves every window onto its real day, 31 of 31. 26 Feb is the Monday of that week, which is how Stage 0 dates its Challengers (787 of 804 editions in 2022-25).
>
> **G2, Australian Open 2021 qualifying: no on both points. No rows confirmed.**
> The facts in the claim are right: the two rows are as described, and the qualifying was played 10-13 Jan 2021, with both walkovers scheduled for 12 Jan. But the date is not the fault, and the fix would cause harm:
> - **The rows are duplicates.** Stage 0 already holds both walkovers from Sackmann, under the qualifying draw's own id (2021-581): same players, round, walkover and winner. That is the real defect.
> - **8 Feb is the convention, not corruption.** Stage 0 dates Australian Open qualifying with the main draw's date in 2019, 2020, 2022 and 2023. The clock has a rule written for exactly these 2021 rows: their window is 8-15 Jan, which holds 12 Jan, and nothing reads them early today.
> - **Changing only the date would create a leak.** With the name "Australian Open" kept, the same rule would apply from 11 Jan instead, putting the window at 11-18 Dec 2020. The walkovers would then count 24 days before they happened, and 8 matches of the same draw would read them early. I checked this with the clock's own code.
>
> The fix the evidence supports is to drop the two Tennis My Life rows as duplicates. That needs its own proposal and three-reviewer round.
>
> I wrote only to my own folder, made no web requests and read no other reviewer's folder.
>
> Files are in `C:\Users\zerom\Documents\Tennis-predictions\data\studies\p6_data_issues\stage0_review\R1_recompute\`:
> - `votes.json`
> - `notes.md`

### R2, attack (received 14 Oct 2026, about 09:02 local)

> **G1 (Tenerife 2024, 31 rows): I confirm.** The rows are corrupt beyond doubt, and the fix is clear, unique and correct: set `tournament_date` from 2024-01-21 to 2024-02-26 on all 31, as the claim proposes.
>
> Tennis My Life's 2024 Challenger file names all three Tenerife draws of 2024 "Tenerife 1" and gives them all Tenerife 1's closing Sunday, 21 Jan. Stage 0 keeps the first two from Sackmann with their correct dates. The third (id 2847) exists only in Tennis My Life, so its wrong date got through. All 31 rows match TennisLive's "Tenerife 3 Challenger" one for one, with the same winners and the same set scores; SofaScore lists the same draw. That draw ran 26 Feb to 3 Mar 2024, and the final was Kukushkin d. Gigante, 6-2 2-0 retired.
>
> My attacks all failed:
> - **Duplicate?** None of the 31 pairings appear at Tenerife 1 or Tenerife 2.
> - **Two draws mixed together?** The bracket is one consistent 32-player draw.
> - **Could the current date be right?** No. That week Kukushkin lost a quarter-final at Tenerife 1, Gigante won in Thailand and Krueger won in California.
> - **Clash in the new week?** None of the 32 players has another Stage 0 match in the week of 26 Feb.
> - **Is 26 Feb the right day?** Yes. It is the first day of the main draw and the Monday of the week, which is the convention of Stage 0's own dating rule (C05), Sackmann and Stage 0's other Tennis-My-Life-only Challenger editions. The alternatives fail: Tennis My Life's usual Sunday (3 Mar) would put the clock's windows a week late, and 25 Feb is only the qualifying's first day.
>
> Changing the date creates no new links and drops no rows. The claimed consequence checks out exactly: the clock now closes these windows on 28-31 Jan, and 136 later matches of the same players read the results early. The rows' wrong name and blank surface are noted but not part of this fix.
>
> **G2 (AO 2021 qualifying, 2 walkovers): I reject the fix.** The rows are corrupt, but because they are duplicates, not because the date is wrong; the proposed fix is wrong.
>
> Stage 0 already holds both walkovers (Sweeny d. Kudla, Vilella Martinez d. Cerundolo) from Sackmann: same players, round and winner, filed under the qualifying's own id (2021-581, "Doha Aus Open Qualies") and dated 10 Jan. The study's note "no Sackmann row" missed them because Tennis My Life files the qualifying under the main draw's id instead. The two copies never linked because the linker accepts a 29-day date gap only when set scores match, and a walkover has none.
>
> The 8 Feb date is not the fault. It follows Stage 0's convention: every Sackmann Slam qualifying draw of 2015-2025 carries its main draw's date, except this AO 2021 one. The clock has a rule for exactly this case and already places these rows on 8-15 Jan, so there is no leak today. The proposed redate would create one. With the name left as "Australian Open", that same rule would move them to 11-18 Dec 2020, about three weeks before the qualifying, and they would still be duplicates. I worked that out from the clock's own arithmetic, which reproduces today's window exactly; I did not rerun the clock. My counter-proposal, for a vote of its own, is to drop the two rows as duplicates of the Sackmann ones.
>
> I did not read the other reviewers' folders. I sent no request to SofaScore, Flashscore, TennisLive, the ITF or the WTA, and read no model result. I wrote only inside my own folder; its parent, `stage0_review`, did not exist, so I created it.
>
> Files are in `C:\Users\zerom\Documents\Tennis-predictions\data\studies\p6_data_issues\stage0_review\R2_attack\`:
> - votes.json
> - notes.md

### R3, independent records and a simulated fix (received 14 Oct 2026, about 09:26 local)

> **G1 (Tenerife 2024): the rows are corrupt (yes), and the fix is clear, unique and correct (yes).** I confirm all 31 rows, set tournament_date to 2024-02-26.
>
> All 31 matches in Stage 0 are the third Tenerife Challenger, not the first. The ATP's own results page for event 2847 is titled "Tenerife 3, 26 Feb - 3 Mar 2024", and its 31 main-draw results match the 31 rows exactly: players, winners, every set score and both retirements. Wikipedia's draw agrees, and an ATP news story puts the final on Sunday 3 March. The January event, which Stage 0 already holds separately, has a different draw; for example, Landaluce lost his first match there to Nakashima. The cause is in Tennis My Life's raw file: it names all three 2024 Tenerife events "Tenerife 1" with the first one's date.
>
> With today's date the rows are physically impossible. Within the same January days, 48 other dated matches put the same players elsewhere: Gigante was playing the Nonthaburi final in Thailand on 21 Jan, and Kukushkin lost the January Tenerife quarter-final on 19 Jan.
>
> I simulated the fix on an in-memory copy, using the timeline code's own rules. That code first reproduced today's windows for all 31 matches. With the new date, every match's play day falls inside its new window (31 of 31; today none does). No player then has a clash with another match, and each player's run follows his previous event (mostly Tenerife 2) and comes before his next one. The 26 Feb date is also the only value that fits Stage 0's convention: 110 of 113 comparable Challenger events are dated on their starting Monday. My code independently gets the study's figure of 136 later matches that read these results too early.
>
> One point that does not block the fix: the name "Tenerife 1" stays wrong. The timeline does not use it, but I did not check whether anything else matches on tournament names.
>
> **G2 (Australian Open 2021 qualifying): the rows are corrupt (yes), but the fix is not clear, unique and correct (no).** The vote is on the two TML rows, operation set tournament_date to 2021-01-10.
>
> The qualifying was played in Doha on 10-13 Jan 2021: the ATP announced those dates, and Wikipedia confirms Doha and both second-round walkovers. But the two rows are not unique records. Stage 0 already holds the same two walkovers from Sackmann, with the same players, round and winners, dated 2021-01-10: `atp|2021-581|Q2|atp:106045|atp:208013` and `atp|2021-581|Q2|atp:106408|atp:202103`. So the real fault is two duplicates the link missed.
>
> The proposed re-dating fails two of the checks:
> - **Clash check:** each walkover would then sit in Stage 0 twice, on the same date and round.
> - **Window check:** the name stays "Australian Open", so the timeline keeps applying its special 2021 rule, which counts back from the main draw. From the new date, that rule moves the window to 11-18 Dec 2020, a month before the walkovers happened. Today's window (8-15 Jan) already holds the true day, 12 Jan, so the fix would create an early-counting problem where none exists now.
>
> Changing the name to Sackmann's as well would give a correct window (10-14 Jan), but the duplicates would remain. The clean fix is a different operation: drop the two Tennis My Life rows, or merge them into Sackmann's.
>
> **Limits.** The day of each individual Tenerife match comes from our saved TennisLive and SofaScore copies, which the study also used. On their own, the web pages only confirm the event's span and the final's day, though the window check holds on those facts alone. I did not check whether walkovers affect any inputs. Nothing outside my folder was modified.
>
> Files are in `C:\Users\zerom\Documents\Tennis-predictions\data\studies\p6_data_issues\stage0_review\R3_records\`:
> - votes.json
> - notes.md
> - simulate_fix.log

### The consensus (the lead, 14 Oct 2026)

The three vote files intersected (`data/studies/p6_data_issues/stage0_review/consensus.json`):
* **G1: confirmed unanimously.** The same 31 rows, operation (set the tournament date) and value (2024-02-26). Proposed table: `stage0_review/proposed_row_corrections.csv` (the 8 Oct format; its action `set_tourney_date` does not exist yet).
* **G2: the date fix rejected unanimously.** All three found the two rows to be duplicates of Sackmann's. Dropping them is a different operation, for its own round.
