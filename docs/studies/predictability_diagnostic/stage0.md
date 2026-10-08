# Stage 0: the analysis table

> **Correction, 2 October 2026:** These are historical results. The audit found chronology, forecast-format and evaluation defects. The shared code and shortlisted features have been repaired; see the [repair report](../feature_alpha_audit/repairs.md). Original numerical results below have not been relabelled as corrected results.

> **Rebuilt, 6 October 2026** (7 Oct, 00:05 UTC), under the [Slam box-score decision](../../decisions/2026-10-06-slam-box-scores.md). The live tables now hold:
> * Tennis My Life's results to 5 October: 873,364 matches;
> * the repairs of 2 October;
> * the official feeds' box scores for Wimbledon and the US Open 2026.
>
> The numbers below describe the build of 30 September. Its tables are kept, with their SHA-256, in `data/studies/data_continuity/rebuilds/2026-10-07T0005Z/replaced/`.

**Status: built 30 Sep 2026, waiting for the owner's review.** A study stage, not a decision. The Brief and the stage table are in the [README](README.md); the report section is "Data used" in [report.html](report.html).

Labels: **observed** is measured on the data, **inferred** is a reading of measurements, **suggestion** is a proposal for the owner. Every number comes from `data/studies/predictability_diagnostic/` (the file is named where it is not `stage0_summary.json` or `stage0_checks.json`).

## In short

* **Observed.** The table holds 872,704 singles matches, ATP 466,115 and WTA 406,589, from the week of 28 Dec 2009 (the first week of the 2010 season) to the week of 21 Sep 2026, with two player rows each (1,745,408). 14,807 men and 16,128 women play in them.
* **Observed.** 215,451 are evaluation matches: ATP 155,130 and WTA 60,321, of which 64,887 and 23,998 fall in the 2022–2026 headline window. After the checks, 98.1% of ATP and 92.2% of WTA evaluation matches carry a box score.
* **Observed.** Side A (set by a hash of the match id) won 50.01% of all matches (95% range 49.91–50.12%). The as-of helper passes a black-box leakage probe on real data; a deliberately leaky feature fails it. 86 tests pass.
* **Observed.** Stage 0 found and corrected, in its own code, flaws in the linking it was told to reuse (`src/eda/merge_feasibility/scan.py`), and found problems in the data map's counts and in both sources. They are listed under [Problems found in earlier work](#problems-found-in-earlier-work-reported-not-fixed); nothing outside this study was changed.
* **For the owner.** Seven decisions, [at the end](#decisions-for-the-owner). The first is the Brief's own rule: cleaning rules that remove more than 1% of a tour × level × year cell.

## What was built

| File | What it holds |
|---|---|
| `stage0_matches.parquet` (26.4 MB) | One row per match: `match_id` (tour, tournament, round and the two sorted player ids), tour, season, era, level, qualifying flag, evaluation flag, round and round order, match number, surface, indoor, best of, draw size, tournament id, name and date, status and its detail, score and a score flag, minutes, format and a non-standard-format flag, box-score status, the service-games convention flag, players A and B, whether A won, source, how TML linked to it, source file and row, the data map's level code, and `order` (the position in the one chronological order) |
| `stage0_match_players.parquet` (62.3 MB) | Two rows per match: match id, player id, opponent id, side (A or B), won, name, rank, ranking points, seed, entry route, age, height, hand, country, the nine box-score counts, `has_box`, and 16 rates stored as `<rate>_n` and `<rate>_d` |
| `stage0_level_rules.csv` | The hand-made level mapping: source, tour, level code and tournament-name pattern to level; checked in order |
| `stage0_level_applied.csv` | How each source code became a level, with counts, years and example tournaments |
| `stage0_cleaning_log.csv` | Every cleaning rule with its count in every tour × level × qualifying × season cell, the cell's size, the share, and whether it passes 1% |
| `stage0_cells.csv` | Per tour × level × qualifying × season: matches, evaluation matches, box scores before and after the checks, retirements, walkovers, A's wins, TML rows |
| `stage0_summary.json` | Everything above in figures: sources, linking, identity, levels, statuses, formats, box scores, holes |
| `stage0_checks.json`, `stage0_check_counts.csv`, `stage0_check_box.csv` | The three checks below and the leakage probe |

Code: `src/eda/predictability_diagnostic/common.py` (scope, loaders, the order, the as-of helper, the leakage probe), `stage0_build.py`, `stage0_checks.py`; report: `render_report.py`, `report_shell.html`, `report_stage0.py`. Tests: `test/predictability_diagnostic/`. The build takes about a minute, the checks 12 seconds and the report under a second. `stage0_match_players.parquet` is over 50 MB and is listed in [data/LARGE_FILES.md](../../../data/LARGE_FILES.md).

## Sources and how they were merged

**Observed.** Jeff Sackmann's files are the base: 461,670 ATP and 405,621 WTA matches in the table (2,544 of them from the weeks from 25 May 2026, where his main-tour files stop; his lower-level files run to 1–2 June). Tennis My Life (TML) adds 4,445 ATP and 968 WTA matches Sackmann lacks: 3,951 and 912 from 25 May 2026 on, and 494 and 56 older ones.

Every TML row was compared with Sackmann before it could be added, identity first, as `scan.py` does:

| TML rows | ATP | WTA |
|---|---:|---:|
| Pass 1: the same two names (normalised), tour and round (scan.py's candidates) | 140,600 | 43,326 |
| Pass 2: one identical player in the same tournament and round (scan.py's anchor) | 6,074 | 211 |
| Pass 3 (new): the two resolved player ids in the same tour and round | 499 | 54 |
| Pass 4 (new): the same event and players under another round label | 112 | 1 |
| Left unlinked, so added | 4,472 | 983 |

Two later rules then removed TML-only rows that repeat a Sackmann match (D4: 1; D6: 41, see below), leaving 5,413.

**Player ids.** Sackmann's ids are used as they are (`atp:104925`). TML's WTA files use the same numbers (they equal Sackmann's in 99.9% of 87,069 linked player pairs). TML's ATP files use ATP website codes (`S0AG`); 4,350 codes were learned from the linked matches by majority (197 codes point at two or more Sackmann ids, 320 Sackmann ids have two or more codes). 307 matches involve a player with no Sackmann id, kept under the code (`atpcode:...`), and 81 matches had a blank id in the source, filled from the same name elsewhere.

**What Stage 0 changed in scan.py's method, and why (observed).** The method is reused through `scan.py`'s own functions (`keys_for`, `pair_of`, `link`, `anchor_links`, `resolve`, `statuses`, all tested in `test_stage0_build.py`), with these changes. The numbers are an audit of scan.py's own choices on the same rows (`merge.scan_py_audit`):

1. **The same event before the nearest week.** scan.py keeps, for each TML row, the Sackmann match of the nearest tournament week. A pair who met in the same round at events in consecutive weeks is then read as one match; TML dates some Challengers by their closing Sunday, so the nearest week can be the wrong event. Of scan.py's 181,039 pass-1 links, 251 point at a different Sackmann match than Stage 0 chose, and 482 share a Sackmann match with another TML row. Stage 0 ranks candidates by the same event (tournament id, else a shared word in the tournament name), then identical set scores, then the nearest week, and gives each Sackmann match to at most one TML row.
2. **Misdated editions.** TML gives a season's later editions of a Challenger the first edition's name and date, sometimes its id too (every Forlì Challenger of 2022 reads "Forli 1" with the first one's date). Stage 0 also accepts a candidate with identical set scores within a month, or within the season in the same event. 2,239 exact-name links are more than a month apart with identical set scores and the same tournament id.
3. **The anchor.** scan.py's anchor assumes one match per player per round, which fails in round robins, and it never compares dates. Run as scan.py runs it, it makes 9,321 links: 295 in round robins, and 2,361 more than a month apart, of which 9 have different set scores (different matches; the rest are misdated copies of the same match). Stage 0 skips round robins in this pass and judges anchor candidates by the rule in point 2.
4. **TML's events.** TML reuses one tournament id for two events of a season (Adelaide 1 and 2 of 2022; the February and October Guadalajara events): an event is its id and name together, and 43 TML-only rows got the date added to their id. TML also dates some qualifying rows apart from the main draw, and in 2026 each match of a two-week event by its day; 5,985 TML rows took their event's main-draw date (rule C05).

**Inferred.** merge_feasibility read its 9,331 anchor links as "the same matches under another spelling". By this audit most are the same matches, but many under the same spelling: pass 1 missed them because TML's date was more than 10 days off. Its counts stand; that reading does not.

## Levels

**Observed.** One taxonomy for both sources and every season: Grand Slams (GS), Tour Finals (FIN), 1000s (T1000), 500s (T500), 250s (T250), team events (TEAM), Challenger / WTA 125 (CH), ITF; qualifying is a separate flag. The hand-made rules are `stage0_level_rules.csv`. Two things are taken from TML where Sackmann cannot say:

* Sackmann's ATP code `A` covers both 250 and 500 events, and its WTA codes blur 500 and 1000 (Premier 5 has no code of its own). For those events the level is the one TML gives the same matches (rule L1: 16,144 matches relabelled; L2: 43 matches in events TML lacks keep the code's default).
* Team events and finales are named in the rules whatever their code (Sackmann files the ATP Cup, United Cup and 2012–2021 Olympics under `A`).

`stage0_level_applied.csv` lists every source code, the rule that fired, the level and example tournaments.

## Results, scores and formats

**Observed.** Statuses, from the score:

| | Completed | Retired | Walkover | Other |
|---|---:|---:|---:|---:|
| ATP | 446,411 | 17,530 | 1,959 | 215 |
| WTA | 391,467 | 12,685 | 2,140 | 297 |

"Retired" includes 691 ATP and 625 WTA matches listed as completed whose last set is unfinished and whose winner is short of the sets needed ("6-2 0-0", rule C18), almost all ITF matches of 2025–2026; 1 ATP and 3 WTA scores carry a walkover marker after games were played. "Other" is defaulted (disqualified), abandoned, or a blank or unreadable score. Evaluation counts completed and retired matches only; inside the evaluation levels and seasons that leaves out 790 ATP and 320 WTA walkovers, and 55 ATP and 137 WTA matches of status other.

* **The player who advanced won (rule D5).** For every match whose event holds a next round (team events aside), the recorded winner should play it and the loser should not. 797,522 matches pass; in 32 the recorded loser plays on and the winner does not, and those were exchanged (21 are ITF matches of 2025 written with the loser first); in 44 both play on and in 1,146 neither does (left as recorded).
* **Scores written from the loser's side (C17, 63 matches):** read the other way they are a complete win for the recorded winner; they are read reversed. 22 are TML's WTA events at Berlin and Nottingham in 2026, where the draw confirms the winners.
* **Short sets and match tiebreaks.** The Next Gen ATP Finals play sets to four games (122 matches, 121 of them evaluation matches under Tour Finals). A match tiebreak (first to 10 points) replaces the deciding set in 6,261 matches: the Laver Cup, some Davis Cup ties, some women's ITF events of 2019, and 29 WTA 500 evaluation matches. Both are flagged (`format`, `nonstandard_format`), not removed.

## Box scores

**Observed.** A box score is kept only when both players have one and it passes every check; blank or all-zero counts are missing, not zero. The checks the Brief asks for, then those added:

| Check | Box scores failing |
|---|---:|
| First serves in exceed serve points | 0 |
| First-serve points won exceed first serves in | 1 |
| Second-serve points won exceed second serves | 7 |
| Break points saved exceed break points faced | 12 |
| Service games disagree with the games in the score by more than one (either convention) | 1,758 (service games dropped, the other counts kept) |
| Added: double faults exceed second serves | 5 |
| Added: aces exceed serve points won | 0 |
| Added: breaks conceded exceed service games | 30 |
| Added: fewer than 4.5 serve points per game in the score | 1,078 |

* **Service games are counted two ways.** In most files they exclude the tiebreak game; at some Grand Slams (Wimbledon and the US Open of 2018–2023, the Australian Open of 2015 and 2016, and TML's men's Wimbledon of 2026) they include it. Both pass; `sv_gms_incl_tb` flags the matches where a tiebreak shows the difference, and a hold rate there counts the tiebreak as a service game.
* **Service games missing, points kept.** 17,939 box scores have every count but service games (all but 324 of them in the WTA's files of 2010–2014) and 1,855 record service games as 0; both keep their point counts, and hold and break rates are missing there.
* **Partial box scores.** The added points-per-game check catches box scores that cover part of a match; most are ITF matches of 2025 (395 men's, 528 women's). A game has at least four points; among the 286,788 completed matches whose box score is kept, the lowest 0.1% have 4.83 serve points per game and the median 6.45 (`points_per_game_in_kept_box_scores` in `stage0_checks.json`), so a floor of 4.5 sits below nearly every complete box score.

## Per-player rates

Stored per player row as numerator `<rate>_n` and denominator `<rate>_d` (`common.rate()` divides them), so later stages can sum numerators and denominators over a player's history rather than average rates:

| Rate | Numerator / denominator |
|---|---|
| `spw` serve points won | first- plus second-serve points won / serve points |
| `rpw` return points won | the opponent's serve points minus the points they won / the opponent's serve points |
| `tpw` total points won | serve plus return points won / both players' serve points |
| `hold` | service games minus breaks conceded / service games |
| `brk` break rate | the opponent's breaks conceded / the opponent's service games |
| `ace`, `df` | aces, double faults / serve points |
| `first_in` | first serves in / serve points |
| `first_won`, `second_won` | points won on the first serve / first serves in; on the second serve / second serves |
| `bp_saved`, `bp_conv`, `bp_faced_pg` | break points saved / faced; converted / the opponent's faced; faced / service games |
| `tb_won`, `sets_won`, `games_won` (from the score) | tiebreaks won / played; sets won / completed sets; games won / games played |

## The order and the as-of helper

**The order.** Dates are tournament Mondays, so one chronological order is built from the tournament date, then the round (qualifying Q1–Q4 before the main draw; a round robin before the knockout rounds; a bronze-medal match level with the final), then the match number; tournament and match id break ties. `order` numbers it.

**The as-of rule** (`common.asof_sums`). A feature for a match sums the same player's matches of events with an earlier tournament date, plus earlier rounds of the same event. It never sees the match itself, another event of the same week, or another match of the same round, so the matches of one round-robin stage never see each other. It is one vectorised pass (group sums and exclusive cumulative sums), not a per-row look-back.

**The proof** (tests in `test/predictability_diagnostic/test_order_asof.py`; figures in `stage0_checks.json`):

* On a hand-made history, the helper counts exactly the matches the rule allows (qualifying before the main draw, other events of the same week excluded, round robins blind to each other).
* On random histories, the helper equals a row-by-row computation of the rule.
* The leakage probe (`common.leak_probe`) scrambles the match at a random cut point and everything after it, and checks that no feature up to the cut moved. On the 148,206 player rows of 2024, with 20 cut points, the helper moved at no row; a deliberately leaky running total that includes the match itself moved at 40 cut rows (both players of each cut match). The tests also catch a leaky whole-period total.
* In the built table, every event's earlier rounds come first and its qualifying precedes its main draw.

## Checks

**1. Match counts against the data map** (`data/studies/data_map/coverage_cells.csv`, 2018 on, walkovers left out on both sides). The map counts every source, so the like-for-like figure is its matches first listed by Sackmann or TML (`stage0_check_counts.csv`).

| | Stage 0 | Data map, same two sources | Data map, every source |
|---|---:|---:|---:|
| Men | 232,504 | 228,223 | 237,607 |
| Women | 237,605 | 236,141 | 239,853 |

156 of 202 tour × level × season cells agree within 1%. The larger differences, measured:

* **Levels (observed).** The map files Shanghai 2025 (95 matches) and Monte Carlo 2026 (55) as 250s: its rule looks for "Masters" in the name, and TML names those two events without it. They account for the men's 1000 and 250 differences of 2025 (+95 and −93) and 2026 (+52 and −55) to within a few matches.
* **ITF (observed).** The map's linking folds some ITF matches into a match it had listed from TML: the same surname pair within −10 to +21 days, or one shared surname in the same round within three days. Measured on Stage 0's own matches, that folds 452, 431, 126, 277, 359, 301, 433, 453 and 194 men's ITF matches in 2018–2026, against differences of 609, 257, 180, 418, 571, 661, 778, 474 and 202; and 146, 168, 35, 70, 90, 143, 146, 133 and 69 women's against 162, 173, 34, 77, 110, 171, 158, 153 and 83. For the women that is nearly the whole difference; for the men it is the same size in most seasons but not in all (2019: 431 against 257; 2023: 301 against 661), so the men's ITF difference is only partly explained.
* **Challengers of 2021 and 2022 (inferred).** The map holds 367 and 76 more than Stage 0, concentrated in a few weeks (2021-02-08: 186, 2022-01-03: 186). Those are the weeks TML gives its misdated later editions; the map, linking by date, keeps them as extra matches.
* Smaller cells: team events (Stage 0 adds TML's 2025 Billie Jean King Cup finals and play-offs and some Davis Cup rubbers) and Challenger qualifying (9 to 59 more a season).

**2. Box-score coverage against merge_feasibility** (`serve_stats_available_pct`, on that study's grouping and years; `stage0_check_box.csv`). 119 of 130 cells agree within one percentage point; of the other 11, 10 are team events, which here also include the Olympics and the ATP and United Cups.

**3. The share of matches A won.** 50.01% of 872,704 (95% range 49.91–50.12%); among evaluation matches 50.02% for the ATP (155,130) and 49.94% for the WTA (60,321). 11 of 267 tour × level × season cells fall outside their own 95% range, about the 5% that chance gives.

## Problems found in earlier work (reported, not fixed)

* **`src/eda/merge_feasibility/scan.py`** (scaffold code): the nearest-week choice, the anchor in round robins and without a date check, as measured above. Stage 0 corrects them in its own code; `scan.py` and the merge_feasibility results are unchanged.
* **The data map** (`src/eda/data_map/measure.py`, `coverage_cells.csv`): Shanghai 2025 and Monte Carlo 2026 filed as 250s; ITF matches folded into Challenger and tour matches by surname; Challenger counts of 2021–2022 raised by TML's misdated editions (inferred).
* **Tennis My Life:** 124 Nouméa matches dated 2007–2008 sit in the 2024 Challenger file (rule C01); one tournament id for two events (Adelaide 1 and 2, the two Guadalajara events of 2022); later editions of a Challenger with the first edition's name and date; ATP Cup group matches labelled R128 (2021–2022) and knockout matches RR (2020); the WTA's Berlin and Nottingham 2026 scores written from the loser's side; Grand Slam 2025 matches repeated with a misidentified opponent (rule D6: 41 rows in all); service games of the 2026 women's Wimbledon matches that cannot fit their scores.
* **Sackmann:** every WTA 125 qualifying match listed twice, 2014–2026 (rule D1: 1,360 rows in all); 114 matches copied into a second ITF event of the same week (D3); five pairs of repeats with different winners (D2, 10 rows); ITF matches of 2025 with winner and loser exchanged (fixed by D5 through the draw); ITF box scores of 2025 that cover part of the match.

## Known holes

* **Observed.** After Sackmann's last weeks (25 May – 2 June 2026) the table has no WTA 125 events, no qualifying on the WTA side or at Challengers, and no ITF matches: TML lists none of them. From 25 May 2026 it holds 93 WTA 125 matches (682 in the same weeks of 2025), 18 WTA qualifying matches (773), 186 Challenger qualifying matches (1,396) and 1,652 ITF matches (16,221), all from those last weeks.
* **Observed.** Men's Challenger qualifying is absent before 2015 and thin in 2015 (43 matches, against 3,443 in 2016).
* **Observed.** Box scores are under 90% in the WTA's 1000, 500 and 250 main draws of 2010–2015, in Grand Slam qualifying in 2011–2018 (men) and 2010–2013 and 2015–2018 (women), and in every ITF season before 2025 (see the report's coverage chart).
* **Observed.** Indoor or outdoor comes only from TML: known for 100.0% of ATP 250 matches, 15.2% of Challengers and 0.3% of WTA 250 matches. Minutes are known for 94.8% of ATP 250, 58.0% of WTA 250 and 8.9% of men's ITF matches. 98.2% of ATP and 99.1% of WTA players in evaluation matches carry a ranking.
* **Inferred.** A TML-only match may sit in the wrong week where TML misdates an edition that Sackmann does not hold.

## Decisions for the owner

1. **Rules that remove more than 1% of a cell** (the Brief's rule; `cells_over_1pct` in the summary, and the report's list). Each is applied now and can be reversed from the log. Approve, or say which to change:
   * D1 (Sackmann): one copy of each WTA 125 qualifying match listed twice: 50% of every WTA 125 qualifying cell 2014–2026, because every match is listed twice.
   * C35: service games dropped where they fit the score neither way, point counts kept: 24.6% of the WTA's 2026 Grand Slam cell (TML's Wimbledon), 3.4% and 4.1% of the 2025 ITF cells, 1–4% of ten other cells.
   * C39: box scores with fewer than 4.5 serve points per game dropped: 2.2% and 2.9% of the 2025 ITF cells, 1–2% of three others.
   * C38, C34: impossible break-point counts: 6.7% of the WTA Finals of 2013 (2 matches), 2.7% of 2026 men's Grand Slam qualifying, 1.1–1.4% of two women's team-event cells.
   * C01 (124 matches dated 2007–2008 in TML's 2024 Challenger file), D1 for TML (5 Davis Cup rubbers of 2017 listed twice), D6 (12 of TML's women's Grand Slam matches of 2025 repeated with a misidentified opponent).
2. **Non-standard formats in evaluation.** 121 Next Gen ATP Finals matches (sets to four games, players under 21) sit under Tour Finals, and 29 WTA 500 matches were played with a match tiebreak for the deciding set. Keep them in evaluation (flagged), or leave them out?
3. **Box-score evaluation windows.** The Brief evaluates WTA box-score features from 2019. The ATP has holes too: its Grand Slam qualifying has usable box scores for none of its matches in 2016–2017, about three-quarters in 2011–2014 and half in 2015 and 2018 (99–100% from 2019). Evaluate ATP Grand Slam qualifying box-score features from 2019 as well?
4. **Box scores from TML.** For 1,988 ATP and 174 WTA evaluation matches, Sackmann has no usable box score and the linked TML row has one. Stage 0 keeps Sackmann's data only (the Brief names it the base). Fill these from TML (suggestion: yes, flagged by source)?
5. **Status "other".** 55 ATP and 137 WTA matches in the evaluation levels and seasons are defaulted or have a blank or unreadable score; they are left out, like walkovers. Agree?
6. **Service games that count tiebreaks.** Leave the two conventions as recorded and flagged, or drop `hold`, `brk` and `bp_faced_pg` where the tiebreak convention shows?
7. **The last weeks.** Later stages can use the table to 21 Sep 2026 for the main tours and Challenger main draws, but not for WTA 125, qualifying below the tour, or ITF after early June 2026. Accept, or ask for another source first (the data map lists the WTA API batches and SofaScore as candidates)?

## Limitations

* Linking is by exact normalised names and ids; a match both sources hold under names that differ beyond one player and whose round labels also differ is counted twice. Rule D6 and the draw check catch the ones that collide within an event.
* Where Sackmann's level code is ambiguous the level follows TML, so an event TML files at the wrong level is wrong here too (the two sources disagree on Cleveland and Strasbourg 2025: Sackmann's code says 250, TML says 500).
* The data map comparison reproduces two of the map's linking passes, not all of them; the unexplained part of the men's ITF difference is left open.
* Rights: Sackmann's files are CC BY-NC-SA 4.0 and Tennis My Life's notices conflict (MIT on the site, noncommercial in its repository); the table keeps the source of every row.
