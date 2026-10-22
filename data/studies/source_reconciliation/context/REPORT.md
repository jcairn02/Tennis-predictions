# Results, context fields and birth dates (subagent 4's report)

16 Oct 2026 · Written by subagent 4 for the lead; saved here by the lead because the harness refused the subagent's own write of this file. The text below is the subagent's report as returned (its summary first, then its full report), unedited apart from this header. The lead's re-checks are in the study's process log and README.

## Summary

- **Coverage.** 2,040,019 result links from 14 sources cover 743,623 of Stage 0's 873,681 matches. 736,655 matches have at least one independent source, and 67,006 of the frame's 67,226 have two or more.
- **Winners.** Two or more independent families contradict Stage 0's winner in only 2 matches: Columbus 125 2021 F and W35 Timaru 2025 F. In both, Sackmann's row has winner and loser swapped, and the WTA's own records side with the other sources.
- **Scores and status.** Two or more independent families contradict 121 Stage 0 game scores and 137 statuses (11 and 12 in the frame). They are listed in `results_contradicted.csv`.
  - Most come from Sackmann's 2025–26 ITF files.
  - Of the 1,310 unmarked retirements that have a second source, 1,214 really are retirements with the RET marker missing.
  - 91 are completed matches whose score Sackmann cut short.
- **Indoor.** The model's rule is right on all 31 events where its two sources disagree (644 frame matches). On the evidence, the women's calendar-first order is the more accurate one.
- **Level.** On 61 main-tour events with a disagreement, Stage 0 is wrong on 15, covering 319 frame matches. Examples: Guadalajara 2023, Strasbourg 2024, Cleveland 2025, the 2017 and 2019 WTA 500s, and Valencia/Vienna 2014.
- **Surface.** In the frame, only WTA Paris 2013–14 is affected (54 matches). Stage 0 says Carpet; the WTA, tennis-data and Flashscore say Hard.
- **Dates.** Sources agree on match days almost everywhere.
  - After the timeline's own slack rules, 77 links that the clock counts still fall outside [es, lf]: 52 before es and 25 after lf.
  - Examples are rain-delayed Wimbledon 2023 first-round matches whose first point was on 3–4 July, against a window starting 5 July.
- **Seeds.** Where both sides give a seed, they differ on at most 0.24% of player rows.
- **Birth dates.** No frame row's age is 0.25 years or more off a decided majority. Outside the frame, 929 rows are off, mostly a young player filed under an older namesake's id.

**Bugs in other code or data, reported and not fixed:**
- `candidate_stage0.load_wta_site` keeps some WTA-site scores from the wrong side: 2,368 rows have a listed winner who lost more sets.
- `tml_vs_sackmann_pairs.parquet` is stale for TML's Challenger files: 28,145 pairs now point at other rows.
- 15 Stage 0 rows marked "completed" are retirements according to every source.

**Judgement calls you should re-check:**
- I chose the definitional classes after seeing the disagreement listings, never outcomes. Examples: match tiebreaks written differently, 7-6 for long advantage sets, and "awarded" read as a default. The raw classes are kept in the work tables, so the counts can be redone under other rules.
- Venue facts and men's level judgements come from my general knowledge, with no online check. They are labelled in `indoor_events.csv` (`venue_note`) and `level_main_tour_verdicts.csv` (`basis`).

---

# REPORT

16 Oct 2026. Prefix `ctx_`. Session f3930e64-e3c4-49f0-8e93-a4637aebdbcf. Numbers are **observed** (computed by the named script on the frozen snapshot) unless marked *inference* or *unknown*. Nothing was scored against results: only two sources' values for the same match were compared. No GPU or network was used, and nothing was written outside `src/eda/source_reconciliation/ctx_*.py` and the `context/` folder.

## 1. What was built

- **`ctx_common.py`** — shared helpers:
  - snapshot loaders and the model frame's match ids;
  - Stage 0 score parsing, which applies Stage 0's own `read_reversed` flag and reads a non-Slam last set of 10+ games as a match tiebreak;
  - set and status comparison classes;
  - orientation of each source's players to Stage 0's player A, by ids first, then names;
  - the independence families.
- **`ctx_readers.py`** — one reader per link-file source: tennis_data, api_tennis, open_tennis_data, flashscore, slam_feeds (AO match centre, Wayback and archived draws; Wimbledon/USO SlamTracker), wta_api, tdi, sofascore, live_tennis_api and infosys (cached in `work/infosys_records.parquet`).
- **`ctx_selflink.py`** — links TennisLive listings (walkovers kept), the WTA website records (Kaggle copy plus the 2026 API player results) and ITF live data to the snapshot. It uses `candidate_stage0`'s loaders and its linking with the event map and weekly-venue filter.
- **`ctx_tml.py`** — finds TML's own row for each Sackmann match. It uses the data-continuity pairs checked by name, and re-pairs stale pairs by exact name pair within 7 days.
- **`ctx_results.py`** (Part C) — two stages: `gather`, then `summarize` (votes, contradictions, verdicts).
- **`ctx_context.py`** (Part D) — `--part surface | indoor | level | rbd | dates | seeds`.
- **`ctx_dob.py`** — Part E.
- **`ctx_handcheck.py`** — rule-8 printouts.
- **`ctx_summary.py`** — `summary.json`, input SHA-256s and the live-Stage-0 check.

To reproduce, run in this order: selflink, tml, results `--stage all`, context `--part all`, dob, summary. The whole sequence takes about 20 minutes.

**Families.** A family groups sources that are copies of each other; dependent families never vote.
- Independent: tennis_data; api_tennis; flashscore; sofascore; slam_official; wta_official (WTA API + website); atp_official (Infosys + TDI); live_tennis_api; tennislive; itf_official.
- Dependent:
  - derived_otd (Open Tennis Data cites Sackmann and tennis-data);
  - sackmann_tml (TML's rows for Sackmann's matches, per the brief). Observed evidence of the dependence: TML repeats Sackmann's typos, and Stage 0's wrong levels follow TML's 250/500 codes.

## 2. Part C: results and scores

### Agreement by source (`results_by_source.csv`)

Each disagreement count is followed by its share of the matches that source could be compared on.

| Source | Links | Winner differs | Games against | Tiebreak pts differ | Status against |
|---|---:|---:|---:|---:|---:|
| tennis_data | 83,183 | 15 (0.018%) | 70 (0.085%) | n/a | 37 (0.044%) |
| api_tennis | 108,269 | 3 | 3,929 (3.69%)¹ | 30/32,629 | 15 |
| flashscore | 413,612 | 13 | 72 (0.018%) | n/a | 29 |
| sofascore | 160,314 | 34 (0.021%) | 253 (0.158%) | 173/36,298 (0.48%) | 163 (0.10%) |
| tennislive | 468,952 | 14 | 162 (0.035%) | 54/111,548 | 222 (0.047%) |
| slam_feeds | 7,682 | 0 | 1 | 1/3,304 | 3 |
| wta_api | 28,853 | 1 | 51 (0.18%) | 1/6,808 | 47 (0.16%)² |
| wta_site | 388,205 | 74 (0.019%) | 563 (0.145%) | n/a | 111 |
| tdi | 3,673 | 0 | 1 | 0/1,309 | 0 |
| infosys | 37,203 | 1 | no sets | n/a | 2 |
| live_tennis_api | 126,876 | no winner | n/a | n/a | 62 |
| open_tennis_data (dependent) | 26,581 | 7 | 18 | n/a | 33³ |
| tml (dependent) | 186,615 | 23 | 795 (0.43%) | 61/64,917 | 204 |
| itf_live | 1 | 0 | 0 | n/a | 0 |

¹ 3,117 of these are completed matches whose api-tennis score stops early.
² The WTA API's Slam batch codes retirements as plain wins.
³ Open Tennis Data calls retirements "completed".

Definitional classes are excluded from "games against": match tiebreaks written as 1-0 / 7-6 / other points (54 links), advantage sets written as 7-6 (9), and truncations where one side marks the match unfinished (666).

### Verdicts by class

Who is right is decided by an official record other than the source's own, else by the majority of the other independent families. Per-source detail is in `results_verdicts.csv`; one row per disagreeing link is in `work/results_disagreements.parquet`.

| Class (Stage 0 vs source) | Links | Stage 0 right | Source right | No other / other |
|---|---:|---:|---:|---:|
| Winner differs | 185 | 127 | 8 | 50 |
| Games: source stops early, both "completed" | 2,506 | 2,498 | 0 | 8 |
| Games: different set count | 1,808 | 1,741 | 12 | 55 |
| Games: same number of sets, games differ | 1,278 | 739 | 220 | 319 |
| Games: mirrored | 270 | 185 | 17 | 68 |
| Games: source has more sets, both "completed" | 53 | 36 | 15 | 2 |
| Status: Stage 0 retired, source completed | 412 | 157 | **225** | 30 |
| Status: Stage 0 completed, source retired | 205 | 122 | 70 | 13 |
| Status: Stage 0 unknown, source gives a value | 121 | 0 | 75 | 46 |
| Status: retired vs walkover | 66 | 49 | 4 | 13 |
| Status: walkover vs retired | 44 | 44 | 0 | 0 |
| Status: definitional (defaulted vs retired/awarded; default with no play) | 118 | 73 | 0 | 45 |

Reading this table:
- In general, when one source disagrees with Stage 0, Stage 0 is right.
- There are three exceptions:
  - Stage 0's inferred retirements for short scores, where the sources are right more often (Sackmann's truncated 2025 ITF scores and his "6-6" typos);
  - TennisLive's game-score disagreements (102 TennisLive right vs 50 Stage 0 right);
  - Stage 0's "unknown" statuses, which other sources fill.

### Contradicted rows (`results_contradicted.csv`, 260 rows)

Columns: match_id, field, stage0_value, competing_values, competitors_agree_on_one_value, families_against, families_agreeing, families_definitional, agreeing_values, official_relation, official_against, official_for_stage0, in_model_frame, tour, year, map_level, tournament_name, tournament_date, round, name_a, name_b, stage0_score, status_detail, stage0_source.

| Field | Rows | In frame | Official record against Stage 0 | Against outnumber for |
|---|---:|---:|---:|---:|
| Winner | 2 | 0 | 2 | 2 |
| Games | 121 | 11 | 61 | 119 |
| Status | 137 | 12 | 69 | 133 |

**The 121 game scores by pattern** (frame counts in brackets):
- unmarked retirement whose score Sackmann cut short: 69 (3);
- one set differs: 25 (1);
- a retirement's partial set differs: 15 (5);
- several sets differ: 6 (0);
- Stage 0 is missing a set: 3 (2) — e.g. Abu Dhabi 2021, "7-5 3-6" where the full score is 7-5 3-6 2-6;
- Stage 0 has an extra set: 3 (0).

**The 137 statuses:**
- Stage 0 "retired", mostly unmarked: 87.
- Stage 0 "unknown": 33.
- Stage 0 "completed": 15 (8 in the frame). Stage 0 itself flags 8 of them "inconsistent" and 5 "short_of_best_of"; 2 are unflagged. Every source, the WTA's own records included, calls them retirements (e.g. Guadalajara 2022 SF, Madrid and Berlin 2023).
- Stage 0 "abandoned": 2.
- By level: ITF 106, ITF qualifying 7, main tour 13, Challenger 7, Slam main draw or qualifying 4.

### Other observations

- Read the right way round, Stage 0's 63 `read_reversed` rows (49 of them in 2025–26) equal every other source. *Inference:* a downstream consumer that ignores the flag would read those scores backwards. I did not check consumers.
- In 2,368 WTA-site rows, the score is written from the side opposite the listed winner. I turned those rows' sets to the listed winner before comparing.

## 3. Part D: context fields

### Surface (`surface_by_source.csv`, `surface_events.csv`)

Share of matches where the source's surface equals Stage 0's (men / women):

| Source | Men | Women | Note |
|---|---:|---:|---|
| TML (dependent) | 99.8% | 99.96% | |
| WTA editions | — | 99.85% | |
| TennisLive | 99.65% | 99.96% | |
| tennis-data | 99.7% | 98.5% | |
| Flashscore | 98.5% | 97.9% | has no carpet category |
| SofaScore | 97.2% | 98.8% | |
| WTA website | — | 98.1% | |
| Live Tennis API | **80.1%** | **92.0%** | left out of the majority |

- Stage 0 differs from the independent majority on 222 events: Carpet/Hard 103, Hard/Clay 104. These are men's Challenger 43 and ITF 78, women's ITF 90, Paris 2010–14 (5 events) and 6 team events. The WTA's own record is against Stage 0 on 100 of them.
- In the frame, only WTA Paris 2013–14 is affected: Stage 0 says Carpet, while the WTA, tennis-data and Flashscore say Hard (54 frame matches).

### Indoor (`indoor_events.csv`, `indoor_summary.json`)

- I ran `indoor_fill.status.rule()` on the snapshot rows, with tennis-data's Court column read from its link file. It reproduces the frame's `in_indoor` on 67,226 of 67,226 matches.
- Events with both sources: men 1,055, women 905. Disagreeing: men 10 events (274 matches), women 21 (476).
- **Men: Stage 0's flag (from TML) is right on all 10.**
  - São Paulo 2016–17 (Pinheiros, outdoor) and Santiago 2020–26 (outdoor clay), by venue.
  - Antalya 2021 (outdoor), by SofaScore and TennisLive.
- **Women: the WTA calendar is right on all 21, by venue.**
  - Stuttgart 2010–17: Porsche Arena, indoor clay.
  - Outdoor: Zhuhai 2015–19, Dubai 2016, Guadalajara 2021, WTA Championships 2010 (Doha), Tournament of Champions 2011 (Bali).
  - Indoor: Taipei 2017–18, Tallinn 2022, Tokyo 2018.
- Venue facts are general knowledge, not checked online. They agree with the indoor-fill study's web-checked venues where the two overlap.
- Third sources over all matches where both sides have a value: TennisLive agrees with the WTA calendar on 12,671 of 12,686 women's matches, and with Court on 12,539. SofaScore agrees with each about 96% of the time.
- **The women's calendar-first order is the more accurate one.**

### Level (`level_by_source.csv`, `level_events.csv`, `level_main_tour_verdicts.csv`)

- Share of matches where the source's level differs from Stage 0's:
  - tennis-data 0.85% for men and 2.53% for women. Its WTA "Premier" label cannot separate 500 from 1000 events. Its Tier column also holds 26 one-off values "WTA251"…"WTA276"; *inference:* a spreadsheet fill-down artefact.
  - WTA API 0.87%, WTA website 0.16%, TML 0.39% (men) / 0.26% (women).
- 593 ATP team events (Laver Cup, United Cup, Davis Cup) are filed under the tour by api-tennis and Flashscore, and under "A" by TML. This is definitional, not an error.
- **Main-tour verdicts.** Women's events are judged by the WTA's own record; men's by general knowledge, with a confidence given in the file. Of 61 events: Stage 0 wrong 15 (319 frame matches), right 38, definitional 8.
  - Stage 0 wrong: Valencia 2014 (an ATP 500); Vienna 2014 (a 250); Zhuhai 2015 (Elite Trophy, a season finale); Bol 2016–17, Zhengzhou 2017 and Limoges 2019 (WTA 125s); Brisbane, Moscow and Sydney 2017, Moscow and Osaka 2019 (WTA 500s); Guadalajara 2023 (a 1000); Strasbourg 2024 (a 500); Cleveland 2025 (a 250).
  - Of the 38 where Stage 0 is right, the disagreeing source is tennis-data in 37 and TML in 1 (WTA Finals 2015). Five of tennis-data's 37 are the Tournament of Champions, which it files as an International event.
- TML's "Winston-Salem 2026 as a Masters" is already corrected by Stage 0's level rule 12. Stage 0's own TML rows are not compared with TML, so it does not show here.

### Round, best-of, draw size

- **Round** (`round_by_source.csv`): disagreement is 0.015–0.30% for tennis-data, the WTA's records and TennisLive; 0.59% for SofaScore; 0.81% for api-tennis; 1.04% for Open Tennis Data; 3.6% for Flashscore (its round labels).
- **Best-of** (`bestof_by_source.csv`, `bestof_disagreements.csv`): Stage 0 is right.
  - The Live Tennis API marks men's Slam qualifying as best-of-5.
  - Open Tennis Data marks the men's 2026 Wimbledon and Roland Garros main draws as best-of-3.
- **Draw size** (`draw_by_source.csv`, `draw_events.csv`): TML agrees on 95.7% of events, the WTA editions on 77.4%. The differences are Sackmann's convention of rounding the draw up to its bracket (64 for 48 or 56): definitional.

### Dates (`dates_*.csv`, `dates_summary.json`, `work/dates_links.parquet`)

- 1,059,975 dated links cover 493,681 matches; 299,971 matches have two or more dates.
- **Do sources agree?** A source's date counts as off when it is more than a day from the median of the other sources (two days for UTC-based dates). Shares off:
  - at most 0.06% for most sources;
  - Slam feeds 0.12%, TDI 0.33%, Match Charting 0.87%, TML days 0.86–1.8%.
- **Are source dates inside the clock's window?** The leak-proof clock (es, lf) is stored as days since 1970.
  - 9,854 links lie strictly outside [es, lf]. Nearly all are definitional: tennis-data's UK calendar day (tagged as such in its link file), UTC-based dates, and the clock's own loose sources.
  - With the clock's own slack rules applied, 271 remain. 194 of those are dates the clock itself outvoted.
  - 77 counted links remain outside: 52 before es (SofaScore 28, Slam feeds 7, WTA API 6, Match Charting 5, TDI 3, three other sources 1 each) and 25 after lf (Flashscore 9, SofaScore 6, Match Charting 5, Live Tennis API 3, api-tennis 1, tennis-data 1).
  - Example: Wimbledon 2023 first-round matches whose first point was on 3–4 July, against a window starting 5 July.
- *Inference:* a source date before es means the match may have started before the day its inputs are read; a date after lf means its result may count before the match ended.
- Only 1 link lies outside −10…+21 days of Stage 0's tournament date.

### Seeds (`seeds_by_source.csv`, `seeds_differ_events.csv`)

- Where both sides give a seed: the WTA API, Slam feeds, TDI and Open Tennis Data never differ; Infosys 0.11%, TML 0.17%, SofaScore 0.19–0.24%, TennisLive at most 0.02%.
- TennisLive holds 57,471 ITF seeds that Stage 0 lacks.
- In the frame: 26 player rows differ, and on 233 a source gives a seed Stage 0 lacks.

## 4. Part E: birth dates and ages

### Sources and how many Stage 0 players each covers

- Sackmann: 25,274.
- TML: 4,183, via 4,289 ATP codes learned from TML rows linked to Stage 0.
- Live Tennis API: 3,961.
- WTA API 2026 player pages: 3,095, via 13,591 WTA ids learned from the WTA's linked records.
- Tennis Abstract: 1,249. Only bios whose full name matches are kept, because the scrape files one bio under several ids (Paire under three).
- Open Tennis Data: 1,209 (a copy of Sackmann).
- The handoff's ATP profiles hold no birth date in any of 3,150 records, so no official ATP date is available.

### Disagreements with Sackmann beyond a day

- TML 34 of 4,085 (0.8%).
- WTA API 37 of 1,961 (1.9%); 13 differ by more than a year, which are identity collisions.
- Live Tennis API 92 of 3,250 (2.8%).
- Tennis Abstract 1 of 1,247; Open Tennis Data 0 of 1,209.

### Majority and frame check

- The majority is the WTA's own date where held, else the date most families give. 66 cases are ties between two families.
- 26,763 players have a date, 7,448 from two or more families. 180 players' dates disagree beyond a day (16 in the frame); Sackmann differs from the majority on 39.
- **Frame (134,452 player rows):**
  - 0 rows are 0.25 years or more off the majority;
  - 0 rows are off Sackmann's file;
  - 186 rows have no age.
- Unresolved frame players with a gap of 0.25 years or more:
  - Yue Yuan (115 frame matches): Sackmann 1998-09-25 vs the Live Tennis API's 1998-02-18;
  - Alina Korneeva (28): Sackmann 2007-06-23 vs the Live Tennis API's 2009-03-11;
  - Mate Delic (9): Sackmann 1993-09-29 vs TML's 1993-04-29.
  - *Inference:* Sackmann's dates are right for Yuan and Korneeva; Delic is unknown.
- **Outside the frame:** 929 player rows (35 players; 897 of them ITF) carry an age 0.25 years or more off the majority. The large gaps are identity collisions, where Stage 0's id carries an older player's birth date but the matches belong to a younger namesake:

  | Player | Rows | Years off |
  |---|---:|---:|
  | Ekaterina Kuznetsova | 114 | 21 |
  | Yuka Matsumoto | 25 | 18 |
  | Su Jin Kim | 10 | 18 |
  | Kamila Kashaeva | 45 | 7 |
  | Iva Jankovic | 22 | 6 |

## 5. Checks

- **Hand checks (`handcheck.json`).** For all 13 result readers and 6 birth-date readers, five links each: the raw staged row printed beside my reader's values and Stage 0's row, judged by eye; 95 of 95 right. Eight contradicted rows were also opened in the raw files, and every contradiction is real:
  - two are 2-vs-2 splits decided by the WTA's record;
  - in one the two contradicting sources disagree with each other too.
- **Bugs in my own code, fixed before the final run.** I had seen only disagreement listings when fixing these, never outcomes.
  - Parquet turned missing tiebreak points into NaN, producing false "tiebreak differs" on 63,950 WTA-site rows.
  - Stage 0's `read_reversed` flag was not applied, producing false "mirrored" scores.
  - AO captures taken mid-match were used as results; the 49 are now `no_record`.
  - The clock's es/lf were read as dates instead of day numbers.
  - The hand-check printer split TennisLive keys wrongly.
- **Classification choices made after seeing the listings.** They change the contradicted counts; the raw classes are kept in the work tables.
  - match tiebreaks written as 1-0, 7-6 or other points, and advantage sets written 7-6, count as definitional;
  - a non-Slam last set of 10+ games is a match tiebreak;
  - "awarded" means a default;
  - defaulted vs retired is vocabulary;
  - a truncation is definitional only where one side marks the match unfinished;
  - the Live Tennis API is left out of the surface majority.
- **Rule 3.** The live Stage 0 hashes still equal the manifest. No ctx_ module reads the live Stage 0. Hashes of every other input are in `summary.json`.

## 6. Found in other code or data (reported, not changed)

1. **`candidate_stage0.load_wta_site`** aligns names to ids and the winner, but keeps the score from the listing's side. In 2,368 linked rows the listed winner lost more sets.
2. **`data/studies/data_continuity/tml_vs_sackmann_pairs.parquet`** is stale for TML's Challenger files: 28,145 of 190,866 pairs point at other rows. I re-paired 23,947 by exact names; 4,374 are left out.
3. **Stage 0:**
   - the 15 "completed" rows that are retirements;
   - the 2 swapped winners;
   - Paris WTA 2010–14 surface;
   - the 15 levels in §3;
   - Sackmann's truncated 2025 ITF scores (about 70) and missing RET markers (about 1,200, which Stage 0 correctly infers);
   - the identity collisions in §4.
4. **Source faults to know before any blend:**
   - api-tennis cuts scores short on 3,117 completed matches.
   - The Live Tennis API's surfaces are unreliable, and it gives men's Slam qualifying as best-of-5.
   - Open Tennis Data's statuses, and its 2026 Slam best-of.
   - tennis-data's Tier fill-down and its 37 level disagreements.
   - tennis-data and Flashscore write long advantage final sets as 7-6.
   - The WTA API's Slam batch codes retirements as wins.
   - TennisLive cannot tell a 250 from a 500.
5. **The timeline:** 77 counted source days fall outside [es, lf], 52 of them before es.

## 7. Could not do

- No online venue or calendar checks, because no network was allowed. These judgements are flagged in `venue_note` and `basis`.
- No official ATP birth dates or levels on disk.
- ITF live data overlaps Stage 0 in one match only (it starts 15 Sep 2026; Stage 0's ITF data ends in June).
- Infosys has no set scores, and the Live Tennis API has no winner or score.
- The brief's "WTA events" table is the umpire event log, which has no surface or tier, so I used the WTA editions and the WTA website instead.
- The WTA-site source includes the Kaggle copy (1975 to Sep 2026), wider than the brief named.
- Lower-level and team level disagreements are listed, not judged.
- No blend was built. For discrete result fields, the evidence supports correction candidates decided official-record-first, not averaging.

## 8. Output files (`data/studies/source_reconciliation/context/`)

Tracked files hold aggregates, ids and short values only; no prices.

| Area | Files |
|---|---|
| Results | `results_by_source.csv`, `results_status_pairs.csv`, `results_set_classes.csv`, `results_verdicts.csv`, `results_contradicted.csv`, `results_coverage.csv`, `results_summary.json` |
| Linking | `selflink_summary.json`, `tml_rows_summary.json` |
| Surface | `surface_by_source.csv`, `surface_events.csv` |
| Indoor | `indoor_events.csv`, `indoor_summary.json` |
| Level | `level_by_source.csv`, `level_events.csv`, `level_main_tour_verdicts.csv` |
| Round, best-of, draw | `round_by_source.csv`, `bestof_by_source.csv`, `bestof_disagreements.csv`, `draw_by_source.csv`, `draw_events.csv` |
| Dates | `dates_by_source.csv`, `dates_pairwise.csv`, `dates_clock.csv`, `dates_outside_clock.csv`, `dates_summary.json` |
| Seeds | `seeds_by_source.csv`, `seeds_differ_events.csv` |
| Birth dates | `dob_disagreements.csv`, `dob_frame_age_off.csv` (empty), `dob_frame_unresolved.csv`, `dob_all_rows_age_off.csv`, `dob_summary.json` |
| Checks | `handcheck.json`, `summary.json` |

The columns of the key tables are listed in §2 and §3. Per-row tables are git-ignored, in `work/`:
- `results_<source>.parquet`, `results_votes.parquet`, `results_disagreements.parquet`;
- `selflink_*.parquet`, `selfrows_*.parquet`, `tml_rows.parquet`, `infosys_records.parquet`;
- `dates_links.parquet`, `dob_players.parquet`.
