# Audit A: Stage 0

**Status: an audit of Stage 0, run 30 Sep 2026. A review, not a decision.** Nothing in the study was changed: no Stage 0 code, table, evidence file or write-up. The audit's scripts are `src/eda/predictability_diagnostic/audit0_*.py`, and their evidence is in `data/studies/predictability_diagnostic/audit0/`. Every number below comes from those files, except the test count, which is pytest's own.

Labels, as in the study: **observed** is measured, **inferred** is a reading of measurements or of outside knowledge, **suggestion** is a proposal for the owner. Each finding is classed as a **confirmed problem**, a **possible problem** or **fine**.

## Findings

| # | Finding | Class | Checks | Size |
|---|---|---|---|---|
| C1 | 101 Tennis My Life rows repeat a match Sackmann already holds. They are the 2025 Billie Jean King Cup Finals (14), Davis Cup rubbers of 2010–2026 (83) and the 2025 Champaign Challenger (4). The Billie Jean King Cup copies also break the time order: the later copy's history includes its own result. | Confirmed | 2, 3 (seen in 1 and 8) | 4 evaluation matches; the rest team matches, used as history |
| C2 | Appended Tennis My Life rows credit matches to the wrong player, or split one player across two ids | Confirmed | 3 | 18 matches with another player's id (5 evaluation); 121 players under a second id (183 matches, 129 evaluation) |
| C3 | A match tiebreak written like a set ("4-6 6-4 10-7") is read as a set of 17 games | Confirmed | 5, 6 | 11,419 matches, none in evaluation; 190,459 phantom games in the history |
| P1 | Seven event-seasons sit at a level that follows the sources' codes but, by the tour calendars, is wrong | Possible (inferred) | 4 | 397 evaluation matches |
| P2 | Kept box scores whose break counts do not add up to the games in the score | Possible | 6 | 1,822 of 190,921 testable (1.0%); evaluation: 0.37% ATP, 1.67% WTA |
| P3 | The black-box leakage probe cannot see leaks from matches that are simultaneous under the Brief's rule | Possible | 9 | 2 of 6 deliberate leaks passed it in 200 cuts; the helper itself is correct |
| P4 | Sackmann draw errors that no Stage 0 rule removes: a player twice in one knockout round; a loser who plays on | Possible | 2, 8 | 182 matches in 58 events (49 evaluation matches involved), and more below |
| P5 | Appended rows moved 204–230 days into another edition of their event | Possible | 3 | 4 rows |
| F | Everything else | Fine | 1–9 | Counts against the data map explained exactly; 190,701 of 190,875 links verified; statuses, box-score checks, sides, round order and the as-of helper confirmed |

The study's 86 tests pass unchanged (run without writing any cache).

Terms used below, defined once:
- A **walkover** is a match not played; the opponent advances.
- A **retirement** is a match stopped part-way; the player who stops loses.
- A **match tiebreak** is a single tiebreak to 10 points played instead of a deciding set, common at ITF (entry-level) and team events.
- A **round robin** is a group stage in which each player meets several others. The Brief treats one stage's matches as simultaneous.
- **Qualifying** rounds (Q1–Q3) come before the main draw. A **lucky loser** is a qualifying loser who enters the main draw in a withdrawn player's place.
- A **box score** is a player's match statistics: serve points, aces, break points, service games. A **break** is a game won by the player receiving serve.
- The **Davis Cup** (men) and the **Billie Jean King Cup** (women) are team competitions between nations. Each tie is several singles **rubbers**.

## How the audit was run

- **Independence (observed).** The scripts read the Stage 0 tables and the staged source rows (`data/dump/matches`), joined through each match's `source_file` and `source_row`. All 872,704 matches find their staged row. The scripts parse names, scores and box scores with their own code and do not import `stage0_build.py`. For check 1 they run the data map's own code (`src/eda/data_map/measure.py`) read-only, carrying each staged row's provenance in memory.
- **Scripts and evidence.**

| Check | Script | Evidence in `audit0/` |
|---|---|---|
| Shared loaders and parsers | `audit0_common.py` | |
| 1 Counts against the data map | `audit0_counts.py` | `counts.json`, `counts_cells.csv`, `counts_reconciliation.csv` |
| 2 Duplicates | `audit0_duplicates.py` | `duplicates.json`, `duplicates.csv` |
| 3 Linking | `audit0_linking.py` | `linking.json`, `linking_sample_appended.csv`, `linking_sample_linked.csv` |
| 4 Levels | `audit0_levels.py` | `levels.json`, `levels_by_code.csv`, `levels_events_by_year.csv` |
| 5 Status | `audit0_status.py` | `status.json`, `status_crosstab.csv`, `status_disagreements.csv` |
| 6 Box scores | `audit0_box.py` | `box.json`, `box_crosstab.csv`, `box_disagreements.csv` |
| 7 Sides | `audit0_sides.py` | `sides.json`, `sides_by_cell.csv` |
| 8 Order | `audit0_order.py` | `order.json`, `order_sample_events.json`, `order_sample.csv` |
| 9 Leak test | `audit0_leak.py` | `leak.json` |

- **Re-running.** From the repository root, `./python.sh src/eda/predictability_diagnostic/audit0_<name>.py` for each. Run `audit0_linking.py` before `audit0_duplicates.py`, which reads its output. Each takes a few minutes at most, except `audit0_leak.py` at about 20 minutes. The random draws use seed 20260930.

## 1. Match counts against the data map

**Verdict: fine, apart from C1.** Every large difference is explained exactly. The main causes lie in how the data map links matches, and in those cells Stage 0's counts are the right ones.

**Observed.**
- `coverage_cells.csv` was rebuilt at 11:04 on 30 Sep, after Stage 0's checks ran at 10:31, but none of its 216 cells changed. Stage 0's comparison still stands.
- For 2018 on, with walkovers and blank scores left out as the map leaves them out:
  - Men: Stage 0 232,504; the map's matches first listed by Sackmann or Tennis My Life, 228,223; the map from every source, 237,607.
  - Women: Stage 0 237,611; the map 236,141; every source 239,853.
  - The women's figure is 6 above Stage 0's own check, because the audit applies the map's walkover rule to the score text.
- 156 of 202 cells agree within 1%. 32 cells are off by more than 1% and 10 matches.

**How the differences were taken apart.** The map's own first two steps (Tennis My Life, then Sackmann) were run again with each staged row's provenance.
- The re-run reproduces the map's count in all 216 cells.
- 469,639 of Stage 0's 470,115 matches were followed into the map match their staged row became.
- A cell's difference is then the sum of four things:
  - matches the map **merges** into a match that already holds another Stage 0 match;
  - matches the map **drops**;
  - matches the two file in different cells;
  - matches only the map has.
- The sum closes exactly in all 216 cells.

Over all cells:

| | Men | Women |
|---|---:|---:|
| Stage 0 minus the map | +4,281 | +1,470 |
| The map merges it with another match: one shared surname only (the map's fallback passes) | 5,191 | 953 |
| … the same surname pair at another event within the map's −10 to +21 day window (two real matches made one) | 737 | 142 |
| … the same surname pair, same event, another round | 134 | 36 |
| … two matches of one event and round whose surname pairs coincide (brothers, common surnames) | 50 | 39 |
| … one match twice in Stage 0 (same surname pair, event and set scores) | 37 | 14 |
| The map drops it: both players share a surname key, so the pair is blank | 162 | 314 |
| Only the map has it: a second copy of a match Stage 0 holds once, in the same event on another date | −1,784 | −26 |
| Only the map has it: a Tennis My Life row Stage 0 does not keep | −246 | −2 |

Matches the two sources file in different cells cancel out over all cells, so they are not in this table.

The 32 large cells:

| Cell | Stage 0 | Map | Difference | Map merges | Map drops | Map files elsewhere | Map files here | Map only |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Men CH 2019 | 7,385 | 7,164 | +221 | 255 | 9 | 12 | 5 | 50 |
| Men CH 2021 | 4,539 | 4,906 | -367 | 309 | 1 | 0 | 102 | 575 |
| Men CH 2022 | 5,703 | 5,779 | -76 | 312 | 2 | 1 | 30 | 361 |
| Men CHQ 2018 | 3,646 | 3,601 | +45 | 24 | 3 | 18 | 0 | 0 |
| Men CHQ 2021 | 1,655 | 1,629 | +26 | 14 | 0 | 12 | 0 | 0 |
| Men CHQ 2022 | 2,975 | 2,939 | +36 | 16 | 1 | 19 | 0 | 0 |
| Men CHQ 2023 | 3,266 | 3,211 | +55 | 24 | 4 | 27 | 0 | 0 |
| Men CHQ 2024 | 3,466 | 3,428 | +38 | 21 | 1 | 16 | 0 | 0 |
| Men CHQ 2025 | 3,610 | 3,551 | +59 | 27 | 2 | 30 | 0 | 0 |
| Men CHQ 2026 | 1,802 | 1,750 | +52 | 16 | 3 | 33 | 0 | 0 |
| Men ITF 2018 | 16,917 | 16,308 | +609 | 544 | 19 | 46 | 0 | 0 |
| Men ITF 2019 | 16,532 | 16,275 | +257 | 235 | 10 | 12 | 0 | 0 |
| Men ITF 2020 | 4,561 | 4,381 | +180 | 172 | 0 | 8 | 0 | 0 |
| Men ITF 2021 | 11,786 | 11,368 | +418 | 314 | 10 | 94 | 0 | 0 |
| Men ITF 2022 | 16,253 | 15,682 | +571 | 535 | 16 | 20 | 0 | 0 |
| Men ITF 2023 | 17,563 | 16,902 | +661 | 612 | 15 | 34 | 0 | 0 |
| Men ITF 2024 | 18,342 | 17,564 | +778 | 708 | 16 | 54 | 0 | 0 |
| Men ITF 2025 | 17,870 | 17,396 | +474 | 426 | 23 | 25 | 0 | 0 |
| Men ITF 2026 | 6,879 | 6,677 | +202 | 185 | 6 | 11 | 0 | 0 |
| Men T1000 2025 | 769 | 674 | +95 | 3 | 0 | 95 | 2 | 1 |
| Men T1000 2026 | 620 | 568 | +52 | 7 | 0 | 55 | 0 | 10 |
| Men T250 2025 | 826 | 919 | -93 | 4 | 2 | 0 | 98 | 1 |
| Men T250 2026 | 642 | 697 | -55 | 7 | 0 | 0 | 55 | 7 |
| Men TEAM 2018 | 274 | 264 | +10 | 13 | 0 | 0 | 1 | 2 |
| Men TEAM 2025 | 300 | 284 | +16 | 16 | 0 | 0 | 0 | 0 |
| Women CH 2024 | 1,110 | 1,089 | +21 | 9 | 0 | 12 | 0 | 0 |
| Women ITF 2018 | 15,942 | 15,780 | +162 | 135 | 25 | 2 | 0 | 0 |
| Women ITF 2019 | 17,033 | 16,860 | +173 | 151 | 22 | 0 | 0 | 0 |
| Women ITF 2026 | 7,215 | 7,132 | +83 | 61 | 16 | 6 | 0 | 0 |
| Women TEAM 2025 | 131 | 117 | +14 | 14 | 0 | 0 | 0 | 0 |
| Women TQ 2021 | 835 | 825 | +10 | 5 | 1 | 4 | 0 | 0 |
| Women TQ 2024 | 936 | 925 | +11 | 3 | 0 | 8 | 0 | 0 |

What each group of cells shows (observed in `counts.json`, `large_differences`):
- **ITF, men 2018–2026 and women 2018, 2019, 2026.** The map merges these matches into others, almost all through its one-surname fallback. For example, it merges 612 of the men's 2023 surplus of 661. Its fallback lets an ITF match join a Tennis My Life match of the same week when one surname agrees, which is common for surnames such as Wang, Kim or Garcia. The map also drops matches between two players with the same surname key (women's 2018: 25). Stage 0 said the men's ITF difference was "only partly explained". It reproduced two of the map's link passes on its own matches; running the map's code shows the full mechanism. Stage 0's counts are right here.
- **Men's 1000s and 250s, 2025–2026.** The map files Shanghai 2025 (95 matches) and Monte Carlo 2026 (54, plus one Madrid match) as 250s, as Stage 0 said. In 2026 the map also keeps 10 second copies of 1000-level matches, 5 of them from Indian Wells. Inferred: Tennis My Life dates 2026 matches by the day played, which can fall outside the map's window.
- **Men's Challengers 2021 and 2022.** The map keeps 561 and 291 second copies of matches Stage 0 holds once. They are Tennis My Life's misdated later editions: Biella 1 alone gives 145 in 2021, and Forli 1 gives 90 in 2022. It also merges 309 and 312. Stage 0 labelled this inferred; it is now observed.
- **Men's Challenger qualifying.** The map merges 14–27 matches a season. It files 12–33 a season elsewhere: in Challenger main draws, or Grand Slam or tour qualifying. It joins each to a match of the same pair within its window.
- **Team events, 2025: here Stage 0's reading was wrong.**
  - Women's +14: all 14 are "one match twice in Stage 0". They are the Billie Jean King Cup Finals repeat (C1), not "Tennis My Life's 2025 Billie Jean King Cup finals and play-offs" added.
  - Men's +16: includes 8 identical-score Davis Cup repeats (C1).
  - Men's team events 2018 (+10): mostly the map merging two different rubbers whose surname pairs coincide (8).
- **Women's 125s 2024 and tour qualifying 2021, 2024.** Small merges, plus the map filing a few matches under a tour level.

One map-internal inconsistency, outside Stage 0: `coverage_cells.csv` gives women's Grand Slam qualifying 2026 as 448 matches, while the map's own match list has 331.

## 2. Duplicates: the same players, event and round twice

**Verdict: confirmed problem C1. A second copy survives wherever an id or a round label differs. Plus the possible Sackmann errors in P4.**

**Observed** (`duplicates.json`; the repeats of Tennis My Life rows are sized in check 3):
- **The match id itself never repeats (0).** It is tour, tournament, round and the two sorted player ids, so a repeat can only hide behind a difference in one of those parts.
- **Same tournament and round, same two names, different ids: 8 rows (4 pairs).** All are the 2025 Champaign Challenger. The Tennis My Life copy carries other players' ids (check 3).
- **Same two players in one event, different rounds, identical set scores: 18 pairs.**
  - 14 are the 2025 Billie Jean King Cup Finals. Tennis My Life labels them QF/SF/F and dates them 16 Sep; Sackmann labels them RR and dates them 19 Sep.
  - Three are Sackmann qualifying matches repeated in the main draw with the same score:
    - Santiago CH 2022, Q2 and R32: Juan Bautista Torres d. Daniel Dutra Da Silva 6-4 6-2.
    - W15 Los Angeles 2022, Q3 and R32: Megan McCray d. Micheline Aubuchon 6-2 6-3.
    - W15 Antalya 2022, Q3 and QF: Alexandra Shubladze d. Daria Lodikova 5-7 7-6 7-5.
  - One is real: Jannik Sinner beat Taylor Fritz 6-4 6-4 in both the round robin and the final of the 2024 ATP Finals.
- **Davis Cup repeats (83, check 3).** Found by name and score, not by id. Each shares its Sackmann twin's round and date.
  - In 75 the tournament id is also the same, but a player id differs: in 69 because that player is kept under a Tennis My Life code or a name, in 6 because the code resolved to another Sackmann id.
  - In 8 the tournament id differs as well.
  - Stage 0's rule D6 would catch a repeat like this, but it skips round robins, and Sackmann files all 4,094 of its Davis Cup rubbers as round robins.
- **The same pair in two different events within a fortnight, identical scores and winner: 233 pairs.** 181 of them are exactly one week apart. That is chance, not copying: identical scores and winner occur in 1.21% of the 14,923 pairs who met in different events 7 days apart, and in 0.86% of the 5,345 who met 14 days apart. ITF circuits hold consecutive events at one venue, so rematches a week apart are common.
- **Allowed rematches: 209 pairs in one event, qualifying then main draw, or round robin then final, with different scores.** A lucky loser meets their qualifying opponent again, or a Finals group rematch reaches the final.
- **Possible, from Sackmann (P4):**
  - 6 pairs meet in two knockout rounds of one draw, all ITF, which cannot happen.
  - In 182 matches across 58 events, a player appears twice in one knockout round; 49 evaluation matches are involved. Examples:
    - The 2018 WTA Elite Trophy (Zhuhai) round robin is labelled R16 (12 matches). That is harmless for the time order, since one round's matches never see each other.
    - The 2025 Targu Mures Challenger R32 holds blank-score placeholder rows.
    - The 2016 Columbus Challenger qualifying has one name standing in for two players.

**Effect of C1 on the time order (observed).** The Billie Jean King Cup repeat is the only event in the table with two tournament dates. The as-of helper treats an earlier date as an earlier event. So for both players of each of the 14 later (Sackmann) copies, the history includes the Tennis My Life copy of the same match. The 83 Davis Cup repeats share their twin's date, so they are simultaneous and leak nothing. Both copies still count in every later match's history. None of these repeats is an evaluation match.

## 3. Linking Tennis My Life to Sackmann

**Verdict: the links themselves are sound. The problems are in the rows appended after linking (C1, C2, P5).**

**Samples (seed 20260930), each checked against the staged source rows** (`linking_sample_appended.csv`, `linking_sample_linked.csv`):
- **50 random appended Tennis My Life rows**, 44 of them from 25 May 2026 on:
  - Every staged row was found. Names, score and round are as staged; dates are as moved by rule C05.
  - None is a match Sackmann holds.
  - Of the 100 player ids: 91 carry the id that name has in Sackmann's rows; 2 carry the id under a spelling variant; 1 has no Sackmann id.
  - 5 are kept under a Tennis My Life code although the same name has a Sackmann id.
  - 1 is another player's id. Igor Andreev's win over Ryan Sweeting in the 2011 Rome Masters qualifying is filed under `atp:104268`, whose name in Sackmann's rows is Alejandro Falla.
- **50 random linked rows** (Sackmann matches a Tennis My Life row was linked to; 48 by the exact name pair, 2 by the one-player anchor): every staged Sackmann row was found and matches the table. Each has a Tennis My Life row agreeing on both players, the set scores, the winner and the round, dated within 45 days.

**The same checks over every row (`linking.json`).**

*Appended rows (5,413):*
- **Repeats (C1): 101 rows** repeat a Sackmann match (same players, identical set scores, same event or within a week):
  - 83 Davis Cup rubbers of 2010–2026;
  - the 14 Billie Jean King Cup Finals matches;
  - 4 Champaign Challenger matches of 2025. Tennis My Life's own file lists that event twice, with scrambled player codes: one player appears under several codes. One copy linked and the other was appended.
- **The other 5,312 rows** have no Sackmann row with the same players and scores in the same event or week.

*Player ids of appended rows (C2), 10,826 player rows:*
- 10,050 carry the Sackmann id of the same name, and 313 that of a spelling variant.
- 125 carry an id Sackmann's rows do not hold (inferred: players newer than its files), and 126 a code for a name Sackmann lacks.
- **189 player rows (121 players, 183 matches, 129 evaluation matches) are kept under a Tennis My Life code or a name id although their exact name has a Sackmann id.** Each such player's history is split across two ids; 125 of these rows are in 2026.
- **23 player rows in 18 matches carry another player's id:** 11 in the 2011 Rome Masters qualifying, 1 each in Umag 2011, Winston-Salem 2015 and a 2017 Davis Cup tie, and 4 at Champaign 2025. 5 of these are evaluation matches.
- **Inferred cause.** Tennis My Life's early qualifying files carry numeric player codes that look like Sackmann ids but are not: 24 distinct codes on 33 player rows. In only 4 of those rows is the code the Sackmann id of the same name. The rest end up under a code (a second id), or, where the crosswalk learned the code for someone else, under another player's id.

*Dates of appended rows:*
- 4,290 keep their staged date, and 1,119 moved 1–14 days to their event's main-draw date (rule C05).
- **4 moved 204–230 days (P5):** three rows from Tennis My Life's 2023 Challenger file now sit in the July 2022 Rome Challenger, and one Santiago 2 Challenger row of 2021 moved too. The event mapping placed each in another edition of its event. Neither source can say which edition is right.

*Linked Sackmann rows (190,875):*
- 190,701 are verified against a Tennis My Life row:
  - 188,269 agree on players, scores, winner and round within 45 days.
  - 2,066 agree but are dated 46–400 days apart. These are Tennis My Life's misdated editions; for instance, it swaps the tournament ids of the two 2021 Istanbul Challengers and dates both 24 January.
  - 275 agree through the same tournament id, round and one player, the other name spelled differently.
  - 91 are the same except for the round label (Stage 0's pass 4).
- 169 have the same winner but other set scores. 60 of those differ in walkover, default or retirement notation. The rest are the same match with a different score in one source: a typo, a blank score, or a match tiebreak written with or without brackets.
- 4 have the other winner:
  - Two are genuine conflicts between the sources. One is Elias Ymer v Yoshihito Nishioka, 2017 qualifying. The other is a 2025 Davis Cup rubber whose Sackmann score gives the match tiebreak as [8-10] where Tennis My Life has [10-8].
  - Two also show different scores: Alexandra Eala v Sorana Cirstea and Tereza Valentova v Yulia Putintseva, WTA 2026.
- 1 has no Tennis My Life row for the pair under these rules: a link made through resolved ids.

## 4. The level mapping: every source code and what it became

**Verdict: the mapping works as documented (fine). Seven event-seasons follow wrong source codes (P1, inferred).**

**Observed.** Every staged row the build reads (2010 on) was followed to the table: 872,704 as matches, and 155,788 Tennis My Life rows through the Sackmann match they were linked to (same tournament id, round and names). 36,789 could not be followed that way. They are rows dropped by cleaning rules, and Tennis My Life's WTA rows, whose tournament ids use another format ("2015-609" where Sackmann has "2015-W-PM-USA-01A-2015"). Check 3 verifies those by name. No row fell through the rules (L4 = 0).

| Source | Code | Staged rows | Followed to the table | Became | Seasons |
|---|---:|---:|---:|---:|---:|
| Sackmann ATP | 15 | 58,502 | 58,502 | ITF 58502 | 2020-2026 |
| Sackmann ATP | 25 | 35,072 | 35,072 | ITF 35072 | 2020-2026 |
| Sackmann ATP | A | 38,033 | 38,023 | T250 27981, T500 9377, TEAM 620, FIN 45 | 2010-2026 |
| Sackmann ATP | C | 113,218 | 113,211 | CH 113211 | 2010-2026 |
| Sackmann ATP | D | 4,096 | 4,094 | TEAM 4094 | 2010-2026 |
| Sackmann ATP | F | 317 | 317 | FIN 317 | 2010-2025 |
| Sackmann ATP | G | 15,311 | 15,311 | GS 15311 | 2010-2026 |
| Sackmann ATP | M | 13,013 | 13,013 | T1000 13013 | 2010-2026 |
| Sackmann ATP | O | 64 | 64 | TEAM 64 | 2024-2024 |
| Sackmann ATP | S | 184,063 | 184,063 | ITF 184063 | 2010-2019 |
| Sackmann WTA | 10 | 69,663 | 69,632 | ITF 69632 | 2010-2016 |
| Sackmann WTA | 100 | 9,506 | 9,506 | ITF 9506 | 2010-2026 |
| Sackmann WTA | 15 | 108,219 | 108,169 | ITF 108169 | 2012-2026 |
| Sackmann WTA | 25 | 79,902 | 79,866 | ITF 79866 | 2010-2023 |
| Sackmann WTA | 35 | 17,438 | 17,438 | ITF 17438 | 2024-2026 |
| Sackmann WTA | 35+H | 31 | 31 | ITF 31 | 2025-2025 |
| Sackmann WTA | 40 | 2,741 | 2,741 | ITF 2741 | 2023-2023 |
| Sackmann WTA | 50 | 15,148 | 15,148 | ITF 15148 | 2010-2026 |
| Sackmann WTA | 50+H | 184 | 184 | ITF 184 | 2025-2025 |
| Sackmann WTA | 60 | 15,129 | 15,129 | ITF 15129 | 2017-2023 |
| Sackmann WTA | 75 | 8,222 | 8,222 | ITF 8222 | 2010-2026 |
| Sackmann WTA | 80 | 3,098 | 3,098 | ITF 3098 | 2017-2023 |
| Sackmann WTA | C | 10,002 | 8,648 | CH 8648 | 2012-2026 |
| Sackmann WTA | D | 3,790 | 3,790 | TEAM 3790 | 2010-2026 |
| Sackmann WTA | F | 344 | 344 | FIN 344 | 2010-2025 |
| Sackmann WTA | G | 14,381 | 14,381 | GS 14381 | 2010-2026 |
| Sackmann WTA | I | 24,100 | 24,100 | T250 23816, TEAM 123, T500 82, T1000 79 | 2010-2026 |
| Sackmann WTA | O | 256 | 256 | TEAM 256 | 2012-2024 |
| Sackmann WTA | P | 17,148 | 17,148 | T500 10708, T1000 6440 | 2010-2026 |
| Sackmann WTA | PM | 7,354 | 7,354 | T1000 7354 | 2010-2026 |
| Sackmann WTA | W | 436 | 436 | T250 302, T500 88, CH 31, FIN 15 | 2015-2024 |
| TML ATP | (blank) | 374 | 360 | T250 179, GS 110, T500 50, T1000 21 | 2010-2018 |
| TML ATP | 250 | 28,179 | 25,896 | T250 25896 | 2010-2026 |
| TML ATP | 500 | 9,460 | 8,497 | T500 8497 | 2010-2026 |
| TML ATP | A | 619 | 515 | TEAM 339, FIN 102, T250 74 | 2010-2026 |
| TML ATP | C | 79,386 | 74,599 | CH 74599 | 2010-2026 |
| TML ATP | D | 4,240 | 3,641 | TEAM 3641 | 2010-2026 |
| TML ATP | F | 256 | 255 | FIN 255 | 2010-2025 |
| TML ATP | G | 15,789 | 15,328 | GS 15328 | 2010-2026 |
| TML ATP | M | 13,366 | 10,952 | T1000 10893, T250 59 | 2010-2026 |
| TML ATP | O | 256 | 191 | TEAM 191 | 2012-2024 |
| TML WTA | 1000 | 3,865 | 3,806 | T1000 3806 | 2021-2026 |
| TML WTA | 250 | 4,697 | 4,299 | T250 4299 | 2021-2026 |
| TML WTA | 500 | 2,798 | 2,646 | T500 2646 | 2021-2026 |
| TML WTA | A | 56 | 27 | T250 27 | 2025-2025 |
| TML WTA | D | 3,832 | 3,805 | TEAM 3805 | 2010-2026 |
| TML WTA | F | 344 | 210 | FIN 210 | 2010-2025 |
| TML WTA | G | 8,509 | 254 | GS 254 | 2010-2026 |
| TML WTA | I | 10,396 | 3,980 | T250 3980 | 2010-2020 |
| TML WTA | O | 256 | 64 | TEAM 64 | 2012-2024 |
| TML WTA | P | 3,762 | 1,130 | T500 1130 | 2010-2020 |
| TML WTA | P5 | 2,896 | 715 | T1000 715 | 2010-2020 |
| TML WTA | PM | 3,118 | 0 |  | 2010-2019 |
| TML WTA | W | 46 | 31 | T250 31 | 2015-2021 |

The table's main draws give these counts of events per season (`levels.json`); the inferred readings follow.

*ATP:*
- **1000s:** 9 each season 2010–2019, 3 in 2020, 8 in 2021 and 2022, 9 in 2023–2025, 7 so far in 2026.
- **500s:** 11 in 2010–2014, 13 in 2015–2019, 7 in 2020, 9 in 2021, 13 in 2022–2024, 16 in 2025.
- **Inferred:** these match the ATP calendar, including its changes. The COVID seasons, Shanghai's absence in 2021–2022, Astana as a 500 in 2022, and Dallas, Doha and Munich rising to 500 in 2025 are all there. Memphis falls to 250 in 2014, and Halle and Queen's rise to 500 in 2015. Vienna is in P1.

*WTA:*
- **1000s:** 9 each season 2010–2019, 3 in 2020, 7 in 2021, 8 in 2022 and 2023, 10 in 2024 and 2025.
- **Inferred:** these fit the calendar. Doha and Dubai alternate as the Premier 5 exactly as the calendar did from 2015. Birmingham is a 500 from 2014 to 2019; Eastbourne is a 250 from 2025.
- **500s:** 12 or 13 each season from 2012 to 2018, except 2017 with 9; 2019 has 10. Those two dips are P1.
- An event name at two levels in one season (Tokyo 2015 and 2017, Moscow 2018) is, inferred, two different events in the same city: fine.

**P1, possible (inferred from the tours' calendars, not measured; to confirm against the ATP's and WTA's own records).** Seven event-seasons sit at a level the calendar contradicts, and each follows its source codes:

| Event | Season | Sackmann code | TML code | In the table | Calendar (inferred) | Evaluation matches |
|---|---|---|---|---|---|---:|
| Vienna (ATP) | 2014 | A | 500 | T500 | 250 (a 500 from 2015) | 55 |
| Valencia (ATP) | 2014 | A | 250 | T250 | 500 (a 250 from 2015) | 41 |
| Brisbane (WTA) | 2017 | I | I | T250 | Premier (500) | 57 |
| Sydney (WTA) | 2017 | I | I | T250 | Premier (500) | 56 |
| Moscow, Kremlin Cup (WTA) | 2017 | I | I | T250 | Premier (500) | 55 |
| Moscow, Kremlin Cup (WTA) | 2019 | I | I | T250 | Premier (500) | 55 |
| Guadalajara (WTA) | 2023 | P | 500 | T500 | WTA 1000 | 78 |

Tennis My Life seems to swap Vienna and Valencia one season early. Rule L1 then takes Tennis My Life's level wherever Sackmann's code A is ambiguous.

*Smaller points:*
- Rule L2 keeps the code's default for 43 matches of one 2017 WTA event that Tennis My Life lacks. The 2017 WTA tour events it lacks are 's-Hertogenbosch, Nurnberg and Zhengzhou.
- The note on rule 7 in `stage0_level_rules.csv` says it catches the 2020 ATP Finals. The 15 matches it catches are the 2023 Tour Finals. This is cosmetic.

## 5. Status: retirements and walkovers against the score strings

**Verdict: the statuses are right (fine). The same scores hide C3.**

**Observed** (`status.json`):
- Every match's score equals its staged score (872,704 of 872,704).
- The audit's own reading of each score agrees with Stage 0's status for 865,042 matches. It agrees on status detail and score flag together for 865,041.
- The statuses are as stage0.md gives them:

| | Completed | Retired | Walkover | Other |
|---|---:|---:|---:|---:|
| ATP | 446,411 | 17,530 | 1,959 | 215 |
| WTA | 391,467 | 12,685 | 2,140 | 297 |

- **Retirements.** 28,895 carry a retirement marker. 1,316 are "completed" scores with an unfinished last set (rule C18: 691 ATP, 625 WTA), and 4 are walkover markers after games were played.
  - 25 retirements (18 ATP, 7 WTA) have a score in which the winner had already finished the match. Examples: "6-0 6-0 RET" at a 2014 men's ITF event, and 2016 Davis Cup rubbers filed as best of 3 with five-set scores. They are kept as retirements, as the sources say.
- **Walkovers.** 4,092 carry a walkover marker, and 7 read "BYE" (treated as walkovers). None is evaluated.
- **The evaluation flag** matches the status in every match. Left out inside the evaluation levels and seasons: 790 ATP and 320 WTA walkovers, and 55 ATP and 137 WTA of status "other".
- **Scores read from the loser's side (rule C17, 63).** In 46 the recorded winner plays the next round, so the draw supports the reading. The other 17 have no next round to check: 15 men's team-event rubbers, 1 ITF match and 1 WTA 500 match. One of these, the 2025 Davis Cup rubber in check 3, conflicts with Tennis My Life about who won.
- **The disagreements (7,662).** 7,659 are completed matches that end in a match tiebreak written like a set. Stage 0's status "completed" is right for them; what goes wrong is below. The other 3 are scores written like "5-7 6-3 [7-6](5)", which Stage 0 reads as retirements. These cannot be settled.

**C3, confirmed.** A deciding match tiebreak written without brackets ("4-6 6-4 10-7") is read by Stage 0 as a set of 17 games.
- **How the audit identifies them.** A real set that reaches 10 games is a long set: it ends two games apart (12-10) or at 13-12. So a final "set" of 10 or more games after level sets that ends with any other margin, such as 10-7, can only be a match tiebreak; the audit counts those as certain (7,651). It also counts those that end two apart (10-8, 11-9) at ITF events, which play no long final sets.
- **Where they are.** 11,419 matches: 11,127 women's ITF, 285 men's ITF and 7 Davis Cup rubbers. The women's ones run from 2,247 to 2,813 a season in 2021–2024.
- **What Stage 0 does with them:**
  - flags 11,418 of them as format "standard", not "match tiebreak";
  - counts 190,459 games that were never played, a median of 16 per match, into `games_won`;
  - does not count the match tiebreak as a tiebreak in `tb_won`. Its tiebreak test takes 7-6, 13-12 or a bracketed score, not 10-7.
- **Scope.** None is an evaluation match, but all enter the history that ratings and features are built from. Grand Slam and Davis Cup long sets such as 16-14 are read correctly.

## 6. Box scores: the consistency checks re-run independently

**Verdict: Stage 0's checks are reproduced exactly (fine). They let through the source inconsistencies in P2, and C3 costs 35 box scores.**

**Observed** (`box.json`):
- **The re-run from the staged rows agrees with Stage 0's box status and `has_box` for every match (872,704).** It uses the audit's own parsing and its own reading of each score's games.
- Failures per check are identical: 0 first serves in above serve points, 1 first-serve points won above first serves in, 7 second-serve points won above second serves, 12 break points saved above faced, 1,758 service games that fit the score neither way, 5 double faults above second serves, 0 aces above serve points won, 30 breaks above service games, and 1,078 below 4.5 serve points per game.
- **Kept values.** For all 296,843 kept box scores, the eight point and break counts equal the staged values, with the 17 swaps of rule D5 accounted for. Evaluation coverage is 98.1% (ATP) and 92.2% (WTA), as stage0.md says.
- **The cost of C3.** 45 matches with a plain-written match tiebreak have a usable box score. Read as Stage 0 reads the score, all 45 fail the service-games check and 37 fail the points-per-game floor. With the tiebreak taken out, 2 fail each. So 35 box scores and 43 service-game counts are dropped only because the tiebreak was counted as games.

**Added by the audit, P2, possible.** Three checks Stage 0 does not make, run on the box scores it keeps:
- **The games identity.** In a completed match with no tiebreak, each player's games won must equal their service games held plus the opponent's breaks. Breaks conceded are break points faced minus saved.
  - Of 190,921 kept box scores where this can be tested, 1,822 (1.0%) miss by a game or more, and 157 by more than one.
  - The commonest pattern, in 1,127, is winner +1 and loser −1 with the total unchanged: one break credited to the wrong player.
  - They come mostly from Sackmann (1,805; Tennis My Life 17). The levels are Grand Slams (906), team events (337) and ITF (448).
  - Among evaluation matches: 365 of 98,660 ATP (0.37%) and 593 of 35,531 WTA (1.67%).
- **The split of service games.** In 89 kept box scores the two players' service games differ by more than one plus the number of tiebreaks.
- **Four points per service game.** No kept box score has a player with fewer than four serve points per service game, allowing for one unfinished game and the tiebreaks.

The effect is on hold, break and break-point rates for those matches.

## 7. Sides A and B

**Verdict: fine. Being A carries no information.**

**Observed** (`sides.json`):
- **Structure.** Every match has two player rows, one A and one B, with one winner. The A row is `player_a_id` and its `won` equals `a_won`. Recomputing the side from the match id with the stated rule (one bit of SHA-256 decides whether the lower-sorted id is A) gives the stored side for all 872,704.
- **Winning.**
  - A won 50.013% of all matches (95% range 49.909–50.118).
  - Among evaluation matches: 50.02% (ATP, 155,130) and 49.94% (WTA, 60,321).
  - In the 2022–2026 headline window: 50.11% and 50.24%.
  - 8 of 267 tour × level × season cells fall outside their own 95% range. A chi-square test that every cell is one half gives 248.1 on 267 cells (p ≈ 0.79).
- **Rank.**
  - Where both players are ranked (674,311 matches), A is the better-ranked player in 50.04% (49.93–50.16). The figure is 50.01% for ATP and 50.13% for WTA evaluation matches.
  - The better-ranked player wins 65.19% when on side A and 65.10% when on side B.
  - When only one player is ranked, it is A in 49.77%.
- **Name and other traits.**
  - A's name sorts first alphabetically in 49.93% (49.83–50.04).
  - A has the lower id in 49.96%, is older in 49.94%, and is the seeded player (when one is) in 50.01%.
  - The alphabetically-first player wins slightly more often (50.17% when A sorts first). That is a property of the players, not of the sides: side is unrelated to name order.

## 8. Order: do the rounds come in the right order?

**Verdict: fine for all 20 random events and for the whole table. The one exception is C1's Billie Jean King Cup repeat.**

**Observed** (`order_sample_events.json`, `order.json`). Twenty events were drawn at random, every event equally likely. For each, all its matches were read in the table's order:
- all 20 are in the order the draw is played;
- each round forms one block;
- qualifying comes first, in the 8 events that have it;
- each event keeps one date;
- no loser plays on.

Because events were drawn uniformly, the sample is mostly ITF.

| Event | Level | Matches | Rounds in the table's order | In order |
|---|---:|---:|---:|---:|
| Busan CH (ATP, 2023) | CH | 49 | Q1×12 → Q2×6 → R32×16 → R16×8 → QF×4 → SF×2 → F×1 | yes |
| Egypt F30 (ATP, 2018) | ITF | 31 | R32×16 → R16×8 → QF×4 → SF×2 → F×1 | yes |
| Perugia CH (ATP, 2015) | CH | 31 | R32×16 → R16×8 → QF×4 → SF×2 → F×1 | yes |
| W75 Kursumlijska Banja (WTA, 2024) | ITF | 71 | Q1×16 → Q2×8 → R64×16 → R32×16 → R16×8 → QF×4 → SF×2 → F×1 | yes |
| W15 Kayseri (WTA, 2025) | ITF | 31 | R32×16 → R16×8 → QF×4 → SF×2 → F×1 | yes |
| Davis Cup QLS R1: GER vs BLR (ATP, 2020) | TEAM | 4 | RR×4 | yes |
| W35 Seville (WTA, 2024) | ITF | 52 | Q1×14 → Q2×7 → R32×16 → R16×8 → QF×4 → SF×2 → F×1 | yes |
| M25 Kutaisi (ATP, 2026) | ITF | 31 | R32×16 → R16×8 → QF×4 → SF×2 → F×1 | yes |
| W15 Heraklion (WTA, 2021) | ITF | 66 | Q1×11 → Q2×16 → Q3×8 → R32×16 → R16×8 → QF×4 → SF×2 → F×1 | yes |
| Luxembourg (WTA, 2019) | T250 | 59 | Q1×16 → Q2×8 → Q3×4 → R32×16 → R16×8 → QF×4 → SF×2 → F×1 | yes |
| W15 Sharm El Sheikh (WTA, 2020) | ITF | 47 | Q1×10 → Q2×6 → R32×16 → R16×8 → QF×4 → SF×2 → F×1 | yes |
| M15 Concepcion (ATP, 2023) | ITF | 31 | R32×16 → R16×8 → QF×4 → SF×2 → F×1 | yes |
| W15 Heraklion (WTA, 2022) | ITF | 70 | Q1×15 → Q2×16 → Q3×8 → R32×16 → R16×8 → QF×4 → SF×2 → F×1 | yes |
| Melbourne 15K (WTA, 2014) | ITF | 31 | R32×16 → R16×8 → QF×4 → SF×2 → F×1 | yes |
| Peru F3 (ATP, 2013) | ITF | 31 | R32×16 → R16×8 → QF×4 → SF×2 → F×1 | yes |
| Davis Cup WG1 R1: BRA vs SUI (ATP, 2026) | TEAM | 3 | RR×3 | yes |
| W60 Toronto (WTA, 2023) | ITF | 55 | Q1×16 → Q2×8 → R32×16 → R16×8 → QF×4 → SF×2 → F×1 | yes |
| M15 Monastir (ATP, 2024) | ITF | 31 | R32×16 → R16×8 → QF×4 → SF×2 → F×1 | yes |
| M25 Jakarta (ATP, 2023) | ITF | 31 | R32×16 → R16×8 → QF×4 → SF×2 → F×1 | yes |
| Davis Cup G1 R1: CHN vs KOR (ATP, 2019) | TEAM | 3 | RR×3 | yes |

Within the sample:
- One winner at W35 Seville 2024 does not appear in the next round, probably a withdrawal.
- Players who enter after the first round are, inferred, byes or direct entries into a later qualifying round, e.g. Q2×16 after Q1×11 at W15 Heraklion.

**The whole table, 25,194 events:**
- Only one event has a round out of played order, and only one has more than one date. Both are the 2025 Billie Jean King Cup Finals (C1): Tennis My Life's QF/SF/F on 16 Sep come before Sackmann's round robin on 19 Sep.
- Stage 0's own test checks the order within each tournament date. It could not see this, because the two copies have different dates.
- **Possible Sackmann errors (P4), kept as recorded:**
  - 44 appearances in 16 events of a main-draw loser in a later main-draw round (the kind of case Stage 0 counts as "both play on" and leaves as recorded);
  - 26 appearances of a qualifying loser in a later qualifying round.
- 7,712 qualifying losers reappear in the main draw. These are lucky losers, so that is fine.

## 9. The leak test: a leak introduced on purpose

**Verdict: the as-of helper is correct, and the study's tests fail for every leak introduced (fine). The black-box probe alone misses two kinds of leak (P3).**

**Observed** (`leak.json`).
- **The real helper against the rule.** The rule was read row by row on 4,782 real player rows of 2024: every round-robin row (886), every row of a player with two events in one week (896), and 3,000 others at random. The helper gives the same value on all of them.
- **Six leaky versions of the helper**, each put in place of the real one in memory:
  1. It includes the match itself and its round.
  2. It adds the other matches of the same round, as in a round robin.
  3. It adds other events of the same week.
  4. It keeps a running total over the table's order, the match itself left out.
  5. It adds the player's next match.
  6. It uses the whole period's total.
- **How each version was tested.** The probe ran as `stage0_checks.py` runs it (2024, 20 cut points) and again with 200 cut points. The study's `test_order_asof.py` also ran against each version, with pytest in the same process.

| Helper | Rows changed (2024) | Probe, 20 cuts (before / at) | Probe, 200 cuts (before / at) | Tests failing (of 11) |
|---|---:|---:|---:|---:|
| real helper | 0 | 0 / 0 | 0 / 0 | 0 |
| includes the match itself and its round | 74,224 | 0 / 40 | 0 / 400 | 5 |
| other matches of the same round (round robins) | 290 | 0 / 0 | 0 / 0 | 4 |
| other events of the same week | 371 | 108 / 1 | 962 / 0 | 3 |
| running total over the order (simultaneous matches earlier in the order) | 328 | 0 / 0 | 0 / 0 | 2 |
| the player's next match | 71,206 | 75,538 / 37 | 771,782 / 372 | 5 |
| the whole period's total | 132,822 | 1,399,858 / 40 | 13,857,828 / 400 | 5 |

**Results:**
- Every leak makes at least two of the study's tests fail. Test `test_asof_counts_only_earlier_events_and_earlier_rounds`, on the hand-made history, fails for all six.
- Leak 1 is the kind Stage 0 tested, a total that includes the match itself. Like Stage 0's, it moves 40 rows at the cut in 20 cuts: both players of each cut match.
- Leak 3 is caught by the probe only because it also uses other events later in the order.

**P3, possible.** The probe replaces the match at a cut point, and everything after it, with noise. It then asks whether anything earlier moved. Its idea of "earlier" is the table's order, which is finer than the Brief's rule: matches of one round, and events of one week, are simultaneous under the rule but still stand one after another in the order.
- **Leak 4 is invisible to the probe.** It uses only matches earlier in the order. Nothing it uses is ever perturbed, so it passes at any number of cuts, though it breaks the rule for 328 rows of 2024.
- **Leak 2 is seen only by luck.** A cut must fall between two matches one player has in one round: a round-robin stage, or a draw error of P4. That happened in the built-table test's 8 cuts on the first half of 2023, and in none of 200 cuts on 2024.
- stage0.md presents the probe as something later stages "can point at any feature". Point it at a feature built on the order, and it will pass leaks that the synthetic tests catch.

## Suggestions for the owner (not applied)

1. **C1.** Drop or link the 101 repeated Tennis My Life rows. For example, match appended rows against Sackmann by names, event and set scores, and let rule D6 cover round robins at team events.
2. **C2.**
   - Resolve a Tennis My Life player code by its exact name when the code crosswalk lacks it (121 players).
   - Distrust numeric codes in Tennis My Life's early qualifying files, and flag the 18 matches credited to another player.
3. **C3.** Read a deciding "set" of 10 or more games after level sets as a match tiebreak outside Grand Slams and Davis Cup, where long sets exist. Then recount games, tiebreaks, formats and the two box checks.
4. **P1.** Confirm the seven event-seasons against the ATP's and WTA's calendars, and add named rules where they are confirmed.
5. **P2.** Consider the games identity as a flag, or a check, on hold and break rates.
6. **P3.** In later stages, test each feature against the hand-made and brute-force tests, not the probe alone. Or define the probe's cut by tournament date and round rather than by the order.

## Limits of this audit

- **Name matching.** Names are matched across sources by the audit's own rules: every word in either order, else shared distinctive words. Spelling variants beyond that are sized separately in check 3 (through tournament id, round and one player). The rules were tightened after false candidates showed up.
- **P1 rests on calendar knowledge.** No official calendar was consulted.
- **Sample composition.** The 50 + 50 linking samples and the 20 events are random. Every finding they show was then sized over the whole table. The 20 events were drawn uniformly over events, so they are mostly ITF; the full-table sweep covers the rest.
- **Check 1 runs the data map's code as it stands today.** If `measure.py` changes, re-run `audit0_counts.py`, which checks the reproduction cell by cell.
