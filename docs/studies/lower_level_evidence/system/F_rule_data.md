# Role F: the data the rule of 8 October keeps out, wired into a candidate Stage 0 (C0_now)

9-10 October 2026 · Role F (data wiring) of the level-evidence system · Research evidence, not a decision.
Pre-registration addition 1 (`data/studies/lower_level_evidence/system/preregistration_addition_1.md`, hash checked)
asks for C0_now; this report says what it holds, how it was built and checked, and how the chain takes it.

Keys: *Observed* = computed here (file cited) or read in code (`path:line`); *Inferred* = reasoning; *Suggestion* = a
proposal. No outcome of a 2025-2026 match was read for any choice: set scores are compared only to confirm that two
records are one match, as the timeline's own linker does (`src/eda/match_timing/srcc_common.py:409`).

## In short

* **C0_now is READY** (`stage0/C0_now/READY.txt`, re-written 10 Oct 02:10 UTC after E's two windows were widened,
  manifest `91603b07…`; first READY 01:07; Observed, sections 1-2): the frozen Stage 0 of
  8 Oct, unchanged (873,437 matches), plus 298,008 new lower-level matches (men 173,185, women 124,823; 18,334 have a
  player with a main-tour match within 365 days) and 1,644 box scores for reference matches held as results only.
  16,581 different box scores for matches that have one (revisions) are counted, not applied.
* **Where it lands:** men's ITF qualifying 2018-2026 (159,191; the reference has none in any year), women's ITF
  qualifying 2010-2018 (80,332), and both tours' 2025-2026 lower levels (92,248), largely the reference's publication
  lag (its ITF tables end on 1 June 2026).
* **Left out:** 1.1% of the played rows Stage 0 lacks (3,285: ids linking to several Stage 0 players, unconfirmed
  same-pair rows, main-tour rows, unknown rounds), and walkovers. Not wired: api-tennis (3,306 rows; initials only),
  TDI (88), the ATP's Infosys files (60), the LTA sample (38), all point data; P7, the bulk of P5 and P8 were not staged.
* **Integrity checks pass:** new-match ids of the other tour 0 (E's blocker, fixed); `history.py` new past 298,008,
  revised 1,644, dropped 0, future 0; no pair twice in a tournament or within 3 days, no player twice in a round; the
  chain's identity repair is idempotent on it; the frozen timeline's rows identical.
* **Identity precision (hand check, section 5):** links 120 of 120 right; players resolved to Stage 0 ids 237 right,
  3 wrong, 8 unsure of 248, every error in TennisLive's fuller-or-shorter-name route (143 player rows; about 0.003% of
  resolved rows wrong when weighted by route); new ids: 4 of 62 are splits of a player Stage 0 holds; the identity
  repair's moves: 18 right, 2 unsure of 20.
* **Expected unevenness, written and hashed before any NEW arm** (section 7): men, nothing flagged in any season;
  women, the 2026 workload counts flagged ("uneven"), possibly the 2026 two-week forms and IOS products, perhaps
  2014; nothing above threshold in 2020-2024; C0_pre arms, no flag in 2025-2026.
* **C0_pre is READY** (`stage0/C0_pre/READY.txt`, 01:30 UTC; frozen Stage 0 plus the additions of events dated up to
  29 Dec 2024): 205,760 new matches and 1,619 completions, derived from C0_now with the same ids and windows; its
  checks pass; twin arms differ only through 2025-2026 data.
* **Hand-over** (section 8): lane 0 takes either folder as it is, without the timeline step; E re-audits before
  NEW_ASIS (the lead); the P7-day commands are in section 9.

## 1. What C0_now adds: new matches

Observed: `stage0/C0_now/inventory.csv` (source x kind x tour x level x year; the per-year detail is there). "Relevant"
= the match has a player with a main-tour match (250 and up, main draw) within 365 days either way, in C0_now.

New matches by tour, level and period (relevant in brackets):

| Tour | Level | 2010-2017 | 2018-2024 | 2025-2026 | All |
|---|---|---|---|---|---|
| Men | Challenger | | 51 (37) | 12 (7) | 63 (44) |
| Men | Challenger qualifying | | 820 (213) | 1,856 (304) | 2,676 (517) |
| Men | ITF | 3 (0) | 1,238 (167) | 10,014 (625) | 11,255 (792) |
| Men | ITF qualifying | | 118,725 (805) | 40,466 (163) | 159,191 (968) |
| Women | WTA 125 / Challenger | 92 (90) | 55 (51) | 859 (772) | 1,006 (913) |
| Women | its qualifying | 87 (69) | 229 (157) | 387 (199) | 703 (425) |
| Women | Slam qualifying | 106 (106) | 108 (107) | 336 (326) | 550 (539) |
| Women | ITF | 674 (196) | 815 (376) | 8,785 (2,299) | 10,274 (2,871) |
| Women | ITF qualifying | 66,382 (7,933) | 16,097 (1,139) | 29,168 (1,597) | 111,647 (10,669) |
| Women | Tour qualifying | 185 (169) | 93 (87) | 365 (340) | 643 (596) |
| **All** | | **67,529** | **138,231** | **92,248** | **298,008 (18,334)** |

By source (package): TennisLive listings (P4) 179,793 (men 172,439, women 7,354); WTA website records 114,404;
WTA API 2,218; ITF live (P1) 1,530; SofaScore 63 (men's Challenger and qualifying). Men 173,185 (2,321 relevant),
women 124,823 (16,013 relevant). 5,998 new matches carry a box score (men 1,958, women 4,040; 5,506 of them in
2025-2026): the WTA API's 2,195, ITF live's own 1,004, TennisLive's results completed by ITF live, SofaScore or
TennisLive pages 2,716, and 83 others.

**Where it lands** (Observed): men's additions are ITF qualifying from 2018 (none before: TennisLive's listing starts in
2018; the frozen Stage 0 holds no men's ITF qualifying in any year) and the 2025-2026 lower levels; women's are ITF
qualifying of 2010-2018 and the 2025-2026 lower levels. 2025-2026 is in large part the reference's publication lag:
in the frozen Stage 0 the ITF and Challenger-qualifying tables end on 1 June 2026, women's tour qualifying on 18 May
2026 and women's ITF qualifying on 16 December 2024 (E S9 makes the same point; section 7).

## 2. What C0_now adds: box scores for reference matches

Observed (`inventory.csv`, `box_layers.parquet`): one source per match, only box scores that pass Stage 0's checks.

| Source | Completions applied (results-only reference matches) | Revisions counted, not applied | Identical |
|---|---|---|---|
| SofaScore (ten careers' pages + P6) | 1,468: men's ITF 2016-2024 (1,450), a few Challenger and qualifying | 13,855: men 13,764, mostly Challenger, its qualifying and tour qualifying; 13,683 in 2025-2026 | 3,128 |
| WTA API | 117: WTA 125 2021-2025 (102) and qualifying | 856 (669 of them the API's all-zero box scores) | 13,099 |
| TennisLive pages | 59: men's ITF 28, women's ITF qualifying 27 (no service-game count: Stage 0's 'no_svgms') | 1,869 | 11 |
| ITF live | 0 | 1 | 0 |
| **All** | **1,644** (= `history.py`'s "revised") | 16,581 | |

Completions of *new* matches (TennisLive results completed by another source) are counted with the new matches above:
ITF live 2,458, SofaScore 122, TennisLive pages 216. The men's reference completions come almost entirely from about
ten SofaScore careers (E S9): box scores selected by player, listed in the expected unevenness (section 7).

## 3. How C0_now is built

Code: `src/eda/lower_level_evidence/candidate_stage0.py`. Tests: `test/lower_level_evidence/test_candidate_stage0.py`
(24 pass). Output: `data/studies/lower_level_evidence/system/stage0/C0_now/`. C0_now was built (00:23-00:50 UTC) by
the builder with SHA-256 `3ac7bf72…`; the manifests record each later hash (`ae1d4b51…` at C0_now's first READY and
C0_pre's derivation, `7b39afd6…` at C0_pre's READY; the round union's in `build_record.json`, `patches`). The changes
after the build are the derivation mode, the precision summary, the coded repair-move sample (it reproduces the sample
checked by hand), the round union (section 5; for later builds it runs in the build) and docstrings.

**The base** (Observed, checked in section 5). The frozen Stage 0 of 8 Oct
(`reference_2026-10-08/frozen/tables/data/studies/predictability_diagnostic/`), never changed: every reference match
keeps its facts, its players and its timeline row; only the box columns of matches a completion reaches change.

**The sources, in wiring order.** Each is linked against Stage 0 plus everything earlier sources added, so a match two
sources hold enters once, from the first.

| Order | Source (package) | Read from | Can add |
|---|---|---|---|
| 1 | WTA API (batches B1-B9, finished 2-3 Oct; not P2) | `data/dump/points/wta/{matches,stats}/<year>.parquet`, `editions.parquet` | women's TQ, GSQ, CH, CHQ 2019-2026, with box scores |
| 2 | WTA website records (Kaggle v29, 24 Sep) | `data/raw/gap_sources/bwandowando/{matches,tournaments}.csv` | women's results at every level since December 2009 |
| 3 | TennisLive listings (P4) | `data/dump/points/tennislive/{listed,events}.parquet` | every level, both tours, 2018 - 4 Oct 2026 (results) |
| 4 | ITF live-data API (P1) | `data/dump/points/itf_live/{matches,events,statistics}.parquet` | ITF and ITFQ from 15 Sep 2026, with box scores |
| 5 | SofaScore (P6 so far; P7 once staged) | `data/dump/points/{sofascore,sofascore_editions,sofascore_tournaments}/` | box scores; a few matches |
| 6 | TennisLive match pages (P5, P8 once staged) | `data/dump/points/tennislive/{matches,statistics}.parquet` | box scores only (8 of the 9 counts) |

ITF live comes after TennisLive so that its players are identified through the matches both list (15 Sep - 4 Oct), by
TennisLive ids the reference's own matches validate, rather than by name alone. Every input file's SHA-256 is in
`build_record.json`.

**Linking** (Observed, code): the timeline's identity linker (`srcc_common.link`): both players' names in a window of
-10 .. +21 days around Stage 0's tournament date, confirmed by identical set scores or by the same round on a plausible
day, then a pass by the source's own player ids; run per tour and season.

**The rules added for the candidate** (each with a test):
* *Event map:* a source event joins the Stage 0 tournament holding 60% or more of its confirmed links, with 3 links at
  least, and of the tier the source gives (ITF, Challenger / WTA 125, main tour, team).
* *Weekly venues:* a link into another tournament than the row's mapped event stands only with identical set scores.
  Monastir and Antalya hold real rematches a week apart; duplicates are found by tournament identity, never by the pair
  alone. Rematches a week apart are kept (counted in section 5).
* *Player ids:* a source id, keyed by its tour, maps to the Stage 0 id that 80% of its links agree on (srcc_common's
  rule, over every season). Where two source ids claim one Stage 0 id, srcc_common drops both; here a claim stands when
  its name agrees with the Stage 0 player's (the WTA API lists Serena Williams under 18254 and 230234), and is refused
  otherwise. Where a source id's links split between Stage 0 ids that all carry its name, the majority id. Otherwise the
  one Stage 0 player of the tour with the same exact name key and no contradicting country, unless another id of the
  same source already maps to that player (then a namesake; the WTA API's Slam-qualifying ids excepted when the country
  agrees, and a row with no id at all excepted); then a fuller or shorter spelling with the same country; otherwise a new
  id `<tour>:<tag>:<source id>` (tags `wtaid`, `itf`, `tl`, `sofa`), a namespace no Stage 0 id uses. A source id whose
  links disagree across different names is a conflict: its rows are left out.
* *New match:* not linked; no Stage 0 (or earlier added) match of the same pair in the same tournament (or, for an event
  Stage 0 lacks, within 3 days); a player never twice in one round of one tournament; a lower level (TQ, GSQ, CH, CHQ,
  ITF, ITFQ); a round Stage 0 can order. Main-tour and team matches are left out: the rule concerns lower-level data,
  and a new main-tour row could enter the model frame itself.
* *Retirements* keep their marker (" RET"); *walkovers and byes* are left out when read.
* *Stage 0 rows* go through `stage0_build`'s own functions: normalise, the score's status and format, the counts read
  from the score, the box checks B0-B9 (`box_scores`), the player rows and rates.
* *Season:* Stage 0's convention (an event starting in the last week of December opens the next season); a row joining a
  Stage 0 tournament takes that tournament's season.
* *Identity repair:* `repair_tables` (`src/eda/feature_alpha_audit/repair_data.py:60`), which `stage0_build` applies to
  every Stage 0, is applied to the candidate too, so that every builder sees the same ids (rebuild.py repairs again,
  Stage 1 does not). It changed no reference row. New matches it made duplicates are then left out: the same pair twice
  in one tournament, the same pair in two tournaments of one week, the same pair, round and score within ten days (one
  match filed under two weekly events), a player twice in one round.

**Box layers.** For every lower-level match the candidate holds, a source's box score is a *completion* when the match
is held as a result only, a *revision* when it holds another box score, *identical* otherwise. One source per match
(WTA API, ITF live, SofaScore, TennisLive pages, in that order); only box scores that pass Stage 0's checks are used.
Completions are applied: they change no fact of the match. Revisions are counted and applied only with `--revisions`
(off for C0_now).

**The clock.** `timing.parquet` holds the frozen timeline's row for every reference match, unchanged, and a row for
every new match:
* the source's own day where it gives one and it is plausible (-10 .. +21 days from the Stage 0 tournament date or from
  the source's own event date), widened by the source's clock error measured against the frozen timeline's exact days
  (timing.py's calibration rule: 99.9% coverage, mislinks beyond 7 days dropped);
* otherwise the frozen timeline's class window (tour, level, phase, round, era; pooled over eras, else timing.py's
  default) joined with the researched schedule rules, from the anchor Monday; for a row that joined a Stage 0
  tournament the source dates otherwise (a weekly venue's event a week apart in the two records), the union of both
  dates' windows, so the true days lie inside whichever record is right;
* no draw narrowing (it only narrows; leaving it out is the cautious side). A result counts from `lf + 1` and a match
  reads the state at `es`, as `src/eda/match_timing/timing.py` defines them.

## 4. What is left out, and why

**When the sources are read** (Observed, `build_record.json`, `per_source.*.read`): walkovers, byes and unplayed or
unfinished matches (WTA API 217; WTA website 38,185; TennisLive 5,732; ITF live 204; SofaScore 2,211 incl. doubles);
WTA website rows whose ids and names fit neither order (12,809; their winner cannot be read safely; 37,841 second copies
were merged, not lost); TennisLive pages whose winner took under 45% of the points (3; the page's two players'
statistics are swapped).

**When they are wired** (Observed, `left_out.csv.gz`, one row per source row, with why):

| Why | WTA API | WTA website | TennisLive | ITF live | SofaScore | TL pages | All |
|---|---|---|---|---|---|---|---|
| A player's source id links to several Stage 0 players (conflict) | 16 | 554 | 1,127 | 0 | 1 | 0 | 1,698 |
| The same pair already in Stage 0 at this event, not confirmed as one match | 6 | 192 | 144 | 0 | 22 | 456 | 820 |
| Main tour or team (not lower-level data) | 6 | 40 | 7 | 0 | 5 | 3 | 61 |
| A player twice in one round (in the source) or already in that round | 0 | 54 | 114 | 0 | 0 | 0 | 168 |
| Ambiguous (equally good Stage 0 matches) | 0 | 9 | 52 | 1 | 0 | 0 | 62 |
| Round or level unknown (cannot be ordered) | 0 | 3 | 2 | 0 | 77 | 267 | 349 |
| **Left out at wiring** | 28 | 852 | 1,446 | 1 | 105 | 726 | **3,158** |

After the identity repair, 127 new matches it made duplicates were dropped (`build_record.json`, `repair`): the same
pair twice in a tournament 7, in two tournaments of one week 56, the same pair, round and score within ten days 54, a
player twice in a round 10. They are counted there, not in `left_out.csv.gz`. In all, 1.1% of the played rows not already
in Stage 0 are left out (3,285 of 301,293).

**Box scores not used** (Observed, `box_layers.parquet`): one source per match, so a lower-priority source's box score
of a match another source completed is not processed (TennisLive pages: 1,212 on reference matches, 119 on new ones);
box scores failing Stage 0's checks (completions: ITF live 35, SofaScore 15, TennisLive pages 9, WTA API 9, the
WTA API's six all-zero ones included); and every *revision* (a
different box score for a match Stage 0 already holds with one: SofaScore 13,855, TennisLive pages 1,869, WTA API 856
of which 669 are the API's all-zero box scores, ITF live 1). Revisions are counted, not applied (`--revisions` applies
them in a separate build).

**Not wired at all** (Observed: the data map's rows the reference lacks, by source, `incoming/newresults.csv`; the
reasons are F's):
* *api-tennis* (3,306 rows: men's ITF 2,253, Challenger 526, Challenger qualifying 516, 2021-2024): its names are
  abbreviated to an initial ("J. Vanneste"), so a player with no linked match cannot be told from a namesake. Whether
  TennisLive's listing already holds these matches was not checked.
* *TDI* (P3; 88 men's rows of 2026, 87 of them tour qualifying): its box scores lack the first-serve split; not wired as
  results either (not checked against the other sources).
* *The ATP's Infosys files* (60 men's Challenger and Challenger-qualifying rows, 2021-2024), *the LTA sample* (38,
  2026), Marcos Jn's and three single rows: small; not wired in this build.
* *Point data* (P3, P5, P6, P7 point records): out of scope; no current input reads points.
* *Packages not staged when C0_now was built:* P7 (SofaScore's ITF events), the bulk of P5 and P8 (TennisLive match
  pages; only the pages staged by 9 Oct 08:10 local time are read). Section 9 has the commands for the day they land.

## 5. The checks

All Observed, `stage0/C0_now/checks.json` (run 01:01 UTC on the build of 00:50 UTC) unless stated.

**Structure: pass.** 1,171,445 matches (873,437 reference, 298,008 new); every reference match present with its facts
unchanged; `has_box` changed only where a completion was applied; the reference's player rows identical outside the
box columns; one A and one B row per match, ids consistent with the sides, `won` with `a_won`; chronological order;
new matches at the lower levels only; 15,669 new player ids, all in the new namespaces; **new-match player ids of the
other tour: 0** (6,159-16,151 in the builds E audited); **new matches whose season and holdout date disagree: 0**
(105 before); one timeline row per match, every window finite and `lf >= es`; the frozen timeline's rows identical.
Side A won 50.1% of new matches (49.9-50.3%).

**`history.py` against the reference of 8 Oct:** future 0, updated 0, **new past 298,008, dropped 0, revised 1,644**
(exactly the applied completions); a template build is refused, as it must be for a candidate.

**Stage 0's own rules on the additions** (`stage0_rules`): status completed 289,413, retired 8,552 (kept with their
marker; 104 retirements the source did not mark), other 43; box checks: full 5,467, no service-game count 531, failed
41, all zero 2; 250 WTA website scores read reversed by Stage 0's parser, as it does for its own rows.

**Duplicates where a new match is involved:** the same pair twice in one tournament 0 (10 before the fixes); the same
pair within 3 days in two tournaments 0 (41 before); a player twice in one round 0. The same pair a week apart in two
tournaments: 3,430, kept (weekly venues; E found these repeat a score at the frozen rate, so they are rematches). A
player in two main draws of one week: 67 of 24,414 player-weeks with a new match (0.27%; reference 65 of 737,209).
Read by hand (Observed, the tables): events Stage 0 holds in part (M15 Casablanca 2025: only the final) whose
TennisLive copy got its own tournament id (fewer than 3 links), or two events the sources date to the same week (M15
Toulouse, March 2020: Stage 0's has a final, TennisLive's stops at the last 16, the week COVID-19 stopped play). No
match is held twice; `chrono_sort` orders by round across both, so a player's own order is kept (Inferred).

**The identity repair** (`repair_tables`, applied in the build): it moved 3,158 player slots of new matches (0.53%;
2,636 from a crosswalk id to another Stage 0 id with the source's exact name, 522 from a new id). Run again on
C0_now it moves 0 rows, so rebuild.py's repair changes nothing. A hand check of 20 moves (weighted by rows; 1,037
slots; `identity_sample_repair_moves.csv`): 18 right (the two Stage 0 ids are one player under two spellings, e.g.
Petr / Pedro Iamachkine, or a fuller name), 2 unsure (Michael Quintero 2010-2017 against Michael Quintero Aguilar
2019-2022; Ricardo Villacorta Alonso 2011-2017 against Ricardo Villacorta 2022-2023), none wrong.

**Identity precision** (hand check of samples drawn with a fixed seed, `identity_sample_*.csv`; verdicts in
`identity_verdicts.csv`; rates and exact 95% upper bounds in `identity_precision.csv`):

| Sample | Checked | Wrong | Unsure | What a wrong one is |
|---|---|---|---|---|
| Links (a source row read as a reference match), 20 per source | 120 | 0 | 0 | another match; upper bound 3.0% pooled, 16.8% per source |
| Players resolved to a Stage 0 id, 20 per source and route | 248 | 3 | 8 | another player |
|   by crosswalk (520,487 slots) | 105 | 0 | 0 | upper bound 3.5% |
|   by exact name (7,831 slots) | 83 | 0 | 2 | (exact name, matches years apart) |
|   by a fuller or shorter name (280 slots) | 60 | 3 | 6 | all in TennisLive's 143 slots |
| New ids, 15 per source | 62 | 4 | 1 | a split: Stage 0 holds the player under another id |

Weighted by route, about 0.003% of resolved player rows are wrong (0.04% counting the unsure as wrong); the bound that
matters is the crosswalk's (0 of 105 and 0 of 120 links). The three wrong rows are TennisLive names resolved to a
Stage 0 player whose name is contained in theirs but whose given name differs ("Juan Pablo Barriga Martinez" to "Pablo
Martinez"; "Camilo Andres Gonzalez Torres" to "Andres Torres"). In the whole build that class holds 69 player rows
under 8 names (`additions.parquet`, route `name_subset`): by hand about 19 rows probably another player, 39 unsure
(35 of them "Daniel Damian" to "Mihaita Daniel Damian"), 3 right. *Suggestion:* for the next build, require the same
given name in that route (a one-line change in `Names`).

Splits (new ids for players Stage 0 holds) are the price of the namesake rule: 4 of 62 sampled new ids (Aruzhan
Sagandykova, "M. Di Prima", Meixu Wu, Alevtina Ibragimova, each with 1-4 new matches); 208 of 15,669 new ids (1.3%)
share an exact name with a reference player of the tour. A split leaves the new matches out of that player's history;
it never puts another player's matches into it.

**Crosswalk names** (Observed, `evidence/crosswalk_*.csv`): 268 of 44,045 crosswalk entries carry names that share no
surname word, or only the surname. By hand nearly all are married names and transliterations (Tatjana Malek and
Tatjana Maria, 776 of 777 links; Kateryna Kozlova and Kateryna Baindl; Daria Gavrilova and Daria Saville;
Sobolieva/Soboleva). E's "Jake Van Emburgh to Toby D Boyer" came from the builds before the tour fix and is gone
(Toby D. Boyer now has his own entry, names agreeing). A few may be relatives or one source id reused (e.g. "Rayan
Ghedjemis" to Rayane Roumane, 98 of 112 links; Kuang Chen Lin to Ping Chen Lin; Ana to Jocelijn Cavero Roeper): about
eight entries holding about 280 new-match player rows (0.05%).

**The clock** (Observed, `timing.parquet`, `build_record.json`): 183,603 new matches carry the source's own day (window
3 days, 5 for ITF live's local day); the 114,404 WTA website rows, which give no day, take the frozen timeline's class
windows (median 9 days, at most 16); one TennisLive row too (7 days). Sources' clocks against the frozen timeline's
exact days: TennisLive 99.0% the same day over 308,543 matches, SofaScore 96.6% (32,512), WTA API 94.3% (28,617), all
inside the window at the calibrated slack. No new event's matches start a week or more after its date (the order
could otherwise put a later result first).

**The round union** (E's CP1b; the lead, 10 Oct): a new row that joins a Stage 0 tournament may not have a window
disjoint from the frozen windows of the same round. Two rows of C0_now had one, both holdout matches: TennisLive's
semifinal of `2026-9552` dated 20 Sep (window 19-21 Sep) against Stage 0's semifinals on 26 Sep, so its result could
count four days early; and the R16 of `2025-W-ITF-USA-2025-21` dated 31 May (30 May - 1 Jun) against Stage 0's R16
windows of 28-29 May, so it read the state up to two days late. Both now take the union (19-26 Sep; 28 May - 1 Jun),
no longer exact; the ids and every other row are unchanged (`round_union`, applied by `--round-union` and, for later
builds, in the build; recorded in `build_record.json`, `patches`). The structure check now counts such rows:
`new_windows_disjoint_from_the_frozen_round` 0. C0_pre holds neither row and is unchanged.

## 6. Errors found and fixed before READY

The checks and role E's audit (`E_red_team.md` S9; `audit/F_c0now/`) found these in earlier builds (none of which was
marked READY). Each fix has a test.

| Found by | Error | Fix |
|---|---|---|
| F's crosswalk check | The WTA website records list a match's ids in the listing player's order and, in later seasons, its names in draw order: 14% of rows had the names the other way round, and the winner code follows the ids. The first loader read the names' order, so those rows had the wrong winner (identical set scores confirmed 1% of their links, 98% of the others) | Each WTA id's own name (the name in 90% or more of its rows); names aligned to ids; the winner read in the ids' order (checked against Stage 0 on hand-picked matches); rows whose ids and names fit neither order left out |
| F's left-out counts | 7% of WTA website rows are a match's second copy, one copy lacking a player's id: 29,000 rows were left out as a player twice in one round | Copies deduplicated by tournament, draw and the pair of names |
| F | Qualifying rounds inferred from the round names misnumber a tournament listed without its first round | The records' own round index (`tourn_round`) |
| F's development run | ~300 reference match ids are stable handles that keep an id the identity repairs later changed; rebuilding a box score by id failed | Rebuilt rows mapped back by position |
| **E (S9)** | **TennisLive numbers its ATP and WTA players separately; F's crosswalk keyed a source id without its tour, so 6,159-16,151 player rows of new men's matches carried women's ids (Laura Siegemund as "Michael Shabaz")** | Source ids keyed by tour; the build refuses a new match with a player id of the other tour; a structure check |
| F's check of the repair | The chain's identity repair would merge 1,489 new-match ids into Sackmann ids by exact name (the WTA website's id-less opponents, blocked by F's namesake rule) | A row with no source id is not a namesake; the repair applied in the build, then the duplicates it creates left out |
| E (S9) | 105 new matches whose season and holdout date disagreed | Stage 0's season convention; a row joining a Stage 0 tournament takes its season |
| E (S9) | One match filed under two weekly events (same pair, round and score) | Left out after the repair (counted) |
| E (S9, a5) | 163 new rows joined a Stage 0 tournament the source dates a week apart (WTA website's "Antalya 14" of 23 Apr 2018 into Stage 0's "Antalya $15K" of 16 Apr): a window from one date only could let a result count before it was played | The union of both dates' windows |
| E (CP1b), after READY | 2 new rows' windows disjoint from Stage 0's windows for the same round (a semifinal that could count four days early; an R16 reading the state two days late) | The union with the frozen round's window; READY withdrawn, checks re-run, READY re-written (section 5) |

## 7. The dose, and the unevenness expected before any NEW arm exists

**Written before any NEW arm was built or scored** (the lead's request): the expectation is the hashed file
`stage0/C0_now/expected_unevenness.txt` (SHA-256 `edcab8a7c6f0174fa5f02700c8248a373ad9fceb0c73a960f813bc5ea18634c6` in
`expected_unevenness.sha256`; status line 2026-10-10T00:36:57Z; C0_pre's folder holds the same file). Its first line
says "about 00:45 UTC"; it was written at 00:36 UTC (the file's time and the status line). It is not revised once any
arm exists; this section repeats it.

*The test* (compare.py, part 1): a tour-season is flagged when its scale ratio is off 1 by more than 10% or its level
moves by more than 0.10 SD; an input is "uneven" when some tour-seasons are flagged and others not.

*The basis* (Observed, counts and dates only): the dose, i.e. per tour and season the model-frame matches with a player
whose previous 365 (28) days gain new matches or new box scores. The expectation was written from the dose of an
earlier build (attempt 4, 23:17 UTC); the READY build's `dose.csv` is below.

The READY build's dose (Observed, `stage0/C0_now/dose.csv`; frame = the reference's model frame, 67,226 matches):

| Tour | Season | Frame matches | New match within 365 / 28 days | Share of previous-year matches | New box score within 365 / 28 days | Share of box history |
|---|---|---|---|---|---|---|
| Men | 2013 | 2,611 | 0.0% / 0.0% | 0.00% | 0.0% / 0.0% | 0.00% |
| Men | 2014 | 2,574 | 0.0% / 0.0% | 0.00% | 0.0% / 0.0% | 0.00% |
| Men | 2015 | 2,619 | 0.0% / 0.0% | 0.00% | 0.3% / 0.0% | 0.00% |
| Men | 2016 | 2,603 | 0.0% / 0.0% | 0.00% | 0.8% / 0.1% | 0.03% |
| Men | 2017 | 2,612 | 0.0% / 0.0% | 0.00% | 0.8% / 0.0% | 0.02% |
| Men | 2018 | 2,620 | 1.4% / 0.3% | 0.03% | 0.9% / 0.0% | 0.03% |
| Men | 2019 | 2,587 | 2.7% / 0.1% | 0.12% | 0.4% / 0.1% | 0.02% |
| Men | 2020 | 1,259 | 2.1% / 0.5% | 0.06% | 1.4% / 0.0% | 0.08% |
| Men | 2021 | 2,466 | 5.5% / 0.3% | 0.33% | 1.1% / 0.0% | 0.05% |
| Men | 2022 | 2,606 | 4.9% / 0.1% | 0.09% | 1.8% / 0.0% | 0.06% |
| Men | 2023 | 2,676 | 4.6% / 0.2% | 0.11% | 1.8% / 0.1% | 0.11% |
| Men | 2024 | 2,676 | 5.9% / 0.5% | 0.14% | 1.3% / 0.1% | 0.06% |
| Men | 2025 | 2,620 | 5.1% / 0.5% | 0.16% | 1.8% / 0.0% | 0.03% |
| Men | 2026 | 2,190 | 6.6% / 2.2% | 0.35% | 0.7% / 0.0% | 0.01% |
| Women | 2013 | 2,417 | 24.8% / 2.5% | 1.15% | 0.0% / 0.0% | 0.00% |
| Women | 2014 | 2,449 | 44.5% / 12.8% | 1.95% | 0.0% / 0.0% | 0.00% |
| Women | 2015 | 2,495 | 52.7% / 2.4% | 2.09% | 0.0% / 0.0% | 0.00% |
| Women | 2016 | 2,498 | 39.4% / 2.6% | 2.15% | 0.0% / 0.0% | 0.00% |
| Women | 2017 | 2,485 | 20.2% / 3.1% | 1.19% | 0.0% / 0.0% | 0.00% |
| Women | 2018 | 2,450 | 25.1% / 4.5% | 1.27% | 0.0% / 0.0% | 0.00% |
| Women | 2019 | 2,458 | 29.2% / 0.8% | 1.15% | 3.6% / 0.3% | 0.07% |
| Women | 2020 | 1,046 | 6.7% / 1.4% | 0.15% | 3.3% / 1.2% | 0.06% |
| Women | 2021 | 2,289 | 38.1% / 6.0% | 1.40% | 9.4% / 2.5% | 0.34% |
| Women | 2022 | 2,339 | 20.6% / 1.1% | 0.30% | 25.7% / 2.0% | 0.65% |
| Women | 2023 | 2,464 | 19.9% / 4.9% | 0.32% | 27.0% / 7.2% | 1.28% |
| Women | 2024 | 2,465 | 32.5% / 2.6% | 0.53% | 40.4% / 2.7% | 1.37% |
| Women | 2025 | 2,485 | 38.1% / 4.9% | 1.42% | 26.1% / 2.2% | 0.52% |
| Women | 2026 | 2,167 | 56.9% / 27.4% | 4.24% | 46.8% / 24.2% | 2.48% |

Against the basis the expectation was written from (attempt 4, which still had the cross-tour ids), the shape is the
same; men's exposure is lower, not higher as the file guessed (2026: 6.6% / 2.2% against 9% / 3%), and women's 2020 is
6.7% (the basis range for 2019-2024 was 14-38%). Neither changes the expectation, which stands as written.

*The expectation* (Inferred, from the dose and from what each input family reads):

| Arm against its reference | Men | Women |
|---|---|---|
| NEW_ASIS against REF | Nothing flagged in any season. Results family (Elo family, `sets_14d`, `surf_season`, `surf_layoff`): the additions are mostly ITF qualifying from 2018 (none before), far from the frame's players; Elo changes spread through opponents, so many rows from 2018 move, each by very little (level under 0.02 SD, scale within 2%). Box family: about 1,500 completions (ten SofaScore careers' ITF 2015-2024; ITF live from 15 Sep 2026); under 1% of rows change per season. A reading near 0. | **2026 flagged, so "uneven"**: the workload counts (`sets_14d` scale about 1.05-1.20; `surf_season` level 0.05-0.20 SD; `surf_layoff`), because 27% of 2026 frame matches gain a match in the previous 28 days (the same event's tour and Slam qualifying). Possibly also in 2026: the two-week forms (level up to about 0.10 SD) and the IOS products (scale off 5-15%; the pool gains about 1,700 lower-level box scores, the mechanism of the input audit's finding #6). Perhaps 2014's workload counts (2014 qualifying added). Elo family: under 0.05 SD, not flagged. Nothing above threshold in the development seasons 2020-2024. |
| NEW_SYS_BOTH against SYS_BOTH | Smaller still: B's fitted w_results for ITF qualifying is 0, so most men's additions drop out of Elo by construction. | The same additions scaled by w_results at ITF and ITFQ. |
| C0_pre arms | As C0_now's for 2013-2024. | As C0_now's for 2013-2024 (perhaps 2014's workload counts); **no flag in 2025 or 2026** (only the carry-over of 2024 additions into early 2025). |

*The caveat* (Inferred): the template recipe re-tunes Stage 1's Elo constants and the offset Elo's K on 2013-2018, and
C0_now changes 2018 (men's ITF qualifying) and 2010-2018 (women's). If a re-tune picks another constant, every season's
Elo inputs move from 2013 ("every season", not "uneven"), still by little. C1 records the constants used.

So differences between a C0_now arm and its C0_pre twin sit in 2025-2026, the holdout, by construction.

## 8. Hand-over: how the chain takes C0_now

**The folder** (`data/studies/lower_level_evidence/system/stage0/C0_now/`): `READY.txt`; `stage0_matches.parquet`,
`stage0_match_players.parquet` (Stage 0's schema and chronological order); `timing.parquet` (match_timing's schema);
`manifest.json` (SHA-256 of every file and every input, counts); `additions.parquet` (each new match: source, source key,
how each player was resolved, the ids before and after the identity repair); `box_layers.parquet`; `left_out.csv.gz`;
`evidence/` (links and crosswalks per source); `build_record.json` (inputs' SHA-256, per-source counts, clocks, the
repair); `checks.json`, `history.json`, `inventory.csv`, `dose.csv`; `expected_unevenness.txt` and its `.sha256`; the
identity samples (`identity_sample_{links,players,new_ids,repair_moves}.csv`), `identity_verdicts.csv` (the hand
check) and `identity_precision.csv`.

**What lane 0 needs** (Observed in the code; Suggestion for C1):
* C1's tooling already installs a candidate: `system_sandbox.py --patch --sandbox D --stage0 <C0_now folder>` copies the
  three tables over the sandbox's (it refuses without `READY.txt`), and `system_arms.lane_plan` then runs lane 0 without
  its timeline step, because the candidate brings `timing.parquet`. That is right.
* **Do not run the timeline step** (`refresh.py`). It re-links TDI, SofaScore and the WTA API from the live raw folders
  (the sandbox's `data/raw` is a junction to the repository's), where P6 has added SofaScore events since the freeze, so
  reference matches' days could move.
* **`stage1_odds` should reproduce the frozen odds exactly** (Inferred): its candidates are main draws of the Slams,
  Finals, 1000s, 500s, 250s and team events only (`stage1_odds.py:71`), C0_now adds none, and its inputs (the
  tennis-data files, last written 5 Oct; `odds_corrections.csv`, 8 Oct 18:46 UTC) predate the freeze. *Gate:* compare
  the sandbox's `stage1_odds.parquet` with the frozen one, every column, before lane 1.
* **`timing_features` is `rebuild.py` with no `--part`**: the per-player features, the IOS solve and the merge, on the
  whole candidate history (34% more matches than the reference), so `ios_points_short` and the pooled IOS see the new
  data. Expect it to take about a third longer.
* **The frame:** C0_now adds no main-tour match, so the model frame's 67,226 match ids must come out unchanged (a gate;
  D's frame check can compare ids, E S8). The Stage 4 pool grows, because new women's WTA 125 and qualifying rows are
  evaluation-level: any gate comparing the pool with the reference's differs by design.
* **Constants:** the template recipe re-tunes Stage 1's Elo constants and the offset Elo's K on 2013-2018 every build.
  C0_now changes those seasons (women's ITF qualifying 2010-2018; men's ITF qualifying from 2018), so a re-tune may pick
  other constants than the reference's. That is the template recipe, so it is NEW_ASIS's (what happens without the
  rule); NEW_SYS_BOTH follows SPEC section 3 (the reference's constants). Record which was used.
* **New matches' strength** (for NEW_SYS_BOTH's translation, E S9): they have no row in A's `strength_elo.parquet`
  (the reference build's pre-match Elo). The arm's own Stage 1 gives a pre-match Elo for every C0_now match; the ruling
  is the lead's.
* **The identity repair is already applied** to C0_now; rebuild.py's own repair should therefore change nothing
  (checked: section 5).

**C0_pre** (`stage0/C0_pre/`, the lead's request of 10 Oct): the frozen Stage 0 plus only C0_now's additions of events
dated up to 29 December 2024, the day before the holdout's first events. It is derived from C0_now, not rebuilt: the
same ids, windows and box scores; new matches of later events dropped; completions of later reference matches undone
(the reference's box columns put back); every later addition counted in `left_out.csv.gz` as "dated after 2024-12-29".
So it separates the historical backfill from the fill of the reference's 2026 publication lag, and a C0_now arm and
its C0_pre twin differ only through 2025-2026 data. Its identity check is C0_now's (same ids; the samples and verdicts
are copied). The chain takes it as C0_now: `--patch --sandbox D --stage0 data/studies/lower_level_evidence/system/stage0/C0_pre`.

Observed (`stage0/C0_pre/checks.json`): 1,079,197 matches, 205,760 new (92,248 later additions left out), 11,260 new
player ids; structure pass (other-tour ids 0, season/holdout disagreements 0, the frozen timeline's rows identical);
`history.py` new past 205,760, revised 1,619 (25 later completions undone), dropped 0, future 0; the same pair twice in
a tournament or within 3 days 0, a player twice in a round 0; 15 of 3,384 main-draw player-weeks with a new match in
two main draws.

## 9. The commands, and the P7 day

C0_now and C0_pre, as built (one heavy process at a time):

```
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_now            # about 35 min on the shared machine
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_now --checks   # about 25 min
#   hand check of the identity samples -> stage0/C0_now/identity_verdicts.csv
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_now --ready
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_pre --derive-from C0_now --until 2024-12-29
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_pre --checks
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_pre --ready
```

When P7's session has staged SofaScore's ITF events into `data/dump/points/sofascore_editions/` (its `verify_links.py`
and staging done, no collector writing those files), the same builder makes C0_P7, and a same-day control without P7's
ITF box scores, so that the comparison isolates P7 from everything else that has landed since:

```
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_P7
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_P7 --checks
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_P7ctl --sofascore-skip "ITF Men,ITF Women"
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_P7ctl --checks
#   hand check: identity_sample_links.csv (the SofaScore rows are P7's ITF links), identity_sample_players.csv,
#   identity_sample_new_ids.csv and identity_sample_repair_moves.csv -> identity_verdicts.csv in each folder
#   (columns kind, source, route, row, verdict right / wrong / unsure, note); write and hash expected_unevenness.txt
#   before any arm is built on them
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_P7 --ready
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_P7ctl --ready
./python.sh -m pytest test/lower_level_evidence/test_candidate_stage0.py -q
#   then C1, per arm: system_sandbox.py --setup; --patch --sandbox D --stage0 data/studies/lower_level_evidence/system/stage0/C0_P7
#   (or C0_P7ctl); system_arms.py --build <ARM> --sandbox D
```

* Each build takes about 25-40 minutes on the shared machine, its checks 20-30 (P7 adds about 270,000 SofaScore events
  to link). Run one at a time.
* P7's ITF box scores reach reference matches as completions: `history.py` will call them revised (about 197,000 for
  2018-2024), as designed for a candidate.
* P5 and P8 (TennisLive pages) and the rest of P6 enter the same way; nothing to change in the code.
* Expect the 2018 step: no package covers ITF box scores before 2018 (role 04, section 3.2).

## 10. What it does not show

* **Whether the rule helps or harms.** C0_now is the data; the readings are the NEW arms' (C1 builds, D scores).
* **Identity beyond the samples.** Precision is measured on hand-checked samples (section 5); errors at a rate under
  the samples' resolution can remain (the crosswalk's 95% bound is 3.5%), and splits (one player under two ids) are
  likelier than merges by design (the namesake rule prefers a new id to a guess). Known residuals, not fixed in this
  build: about 19 player rows resolved by a shorter name with another given name, about 280 rows under crosswalk
  entries that may join relatives or a reused source id, and the repair's two unsure moves.
* **That the identity repair's choice of id is the better one.** Where Stage 0 holds one player under two ids, the
  repair moves new matches to the id carrying the source's exact name, sometimes a minor id (Coleman Wong's 32 new
  matches go to the one-match "Chak Lam Coleman Wong"); the chain's own repair would do the same in rebuild.py.
* **C0_pre as a separate data cut.** It is C0_now restricted by date, not a build from the sources as they stood at the
  end of 2024: the identities were resolved with 2025-2026 rows present (no result was read), so a 2024 addition can
  carry an id that only later rows made resolvable.
* **Exact box-score agreement.** Completions pass Stage 0's checks; no second source checks their counts. SofaScore's ITF
  statistics probably come from the same umpire feed as the ITF's (role 04, section 5), so agreement would not validate
  them anyway.
* **Results against an official record for the new matches.** Winners come from one source each (the WTA's own records,
  TennisLive, the ITF's API, SofaScore); a few source errors (TennisLive's set-closing games, misfiled events) can remain.
* **The relevance of new players.** "Touches the model's players" counts ids with a main-tour match within 365 days; a
  new id that is really a known player under a second id is counted as not touching.
* **Point data.** No current input reads points (role 04); P3, P5, P6 and P7's point records are not wired.
* **Live use.** C0_now is a history candidate for the rule test; a prediction run's gate (`run.py`) is unchanged.
