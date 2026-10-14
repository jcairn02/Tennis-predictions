# Incoming lower-level data: what arrives, when, and how much of it reaches the model

9 October 2026, as of 15:15 UTC · Team role 04 (incoming-data scout) of the lower-level-evidence study · Research evidence, not a decision.

**The question.** Exactly what lower-level data is coming, when, in what grain, how much of it touches the players the current best model forecasts, what must happen before it can reach a model input, and what should trigger a re-review of this dossier.

**Keys.**
* *Observed* = computed here (file cited) or read in a file or the code (`path:line`). *Inferred* = reasoning. *Suggestion* = a proposal.
* Buckets as in `src/eda/lower_level_evidence/common.py`: MAIN (250 and up, main draws), TQ, GSQ, CH (Challenger and WTA 125 main draws), CHQ, ITF, ITFQ. Counts are matches unless they say "player rows".
* **"Relevant"** has three readings in this report:
  * **±365:** at least one of the two players also played a MAIN match within 365 days either side (the brief's definition);
  * **feeds 365:** at least one player plays a model-frame match in the 365 days after it (the long-memory inputs see it);
  * **feeds 28:** the same within 28 days (the two-week form sees it). The 28/365 windows are the input-data audit's (`docs/studies/input_data_audit/README.md:229`).
* **No outcome was read.** The script reads `has_box` (coverage) and dates only: no winner, score or box-score value. 2025–2026 matches (the proposed holdout) are counted, never scored. This report quotes no new score.
* Evidence: `data/studies/lower_level_evidence/incoming/`. Code: `src/eda/lower_level_evidence/incoming.py` (about 25 seconds; it reran unchanged five times; a brute-force recount of 300 sampled player rows agrees on every relevance flag, `summary.json`).

## In short

* **Status (observed).** P1, P3 and P4 are done; P1 now runs daily. Two collectors are running: P5 (TennisLive Challenger pages, started 15:10 UTC) and P6 (SofaScore, gap 1 of 7). P7 and P8 are queued. P2, P9, P10, P11 and P12 have not started.
* **Landing dates at the logged pace (inferred):**
  * P5 about the evening of 10 Oct;
  * P6 about 12–13 Oct;
  * P7's ITF 2025–26 about 17–18 Oct, and its ITF 2018–24 about 31 Oct – 2 Nov (about 22 Oct at the adapter's faster pace);
  * P8 after P7, in early to mid November.
* **None of it is in Stage 0 (observed).** Stage 0 reads only Sackmann's and Tennis My Life's files (`src/eda/predictability_diagnostic/stage0_build.py:91-103`). So no model input can see any new source until it is wired into a candidate Stage 0. The history gate refuses it in a template build.
* **The dose that matters is ITF box scores (P7, then P8), and it is mostly about women** (observed, `targets.csv`, `dose.csv`):
  * P7 targets 202,207 ITF matches of 2018–2024 that Stage 0 holds as results only. At the sampled 97.6% (95% CI 92–99%), that is about 197,000 new box scores.
  * Relevance (±365): 37% of the women's matches and 14% of the men's.
  * From the model's side, 2019–2024: in 69% of women's model matches (men 9%), at least one player's previous year holds such matches.
  * P7 would add on average 14–18% to a woman's previous-year box-score history (men 1–2%). In 20% of women's model matches it reaches the 28-day window of the two-week form.
* **P7 stops at 2018: a built-in step (observed + inferred).** In 72% of women's model matches of 2013–2017 (men 14%), a player has pre-2018 ITF matches that no package covers. Every training window (2013 to Y−1) would mix seasons with and without ITF box scores. That is the "uneven" shape the input check flags (finding #6, moved from 2025 back to 2018).
* **Point data (P5, P6) reaches no current input (observed; Stage 0 holds no point field, and 01_lineage.md's input table agrees).**
  * Points would come for 28,785 men's Challenger and Challenger-qualifying matches of 2018–2024. 75% of them are relevant (±365).
  * 77% of men's model matches of 2019–2024 have such a match in a player's previous year.
  * But no input of the 58 reads point-by-point data. These points reach the model only through a new feature.
* **Biggest by count, least relevant (observed).** Men's ITF qualifying from the P4 listings: 158,824 new results for 2018–2026. Only 920 of them (0.6%) involve a player with a main-tour match within ±365 days.
* **Some lower-level box scores are already on disk but not in Stage 0 (observed).** For 2025–26, the WTA API holds box scores for 1,943 women's matches that Stage 0 lacks: WTA 125 847, its qualifying 385, Slam qualifying 337, tour qualifying 374. About 1,730 of them are from 2026. They are the repair data for finding #7 (women's histories since June 2026).
* **Two gaps in the guardrails (inferred; verify before relying on them):**
  1. After P6/P7, `refresh.py --sources sofascore` rewrites the leak-proof timeline and IOS inputs. The history gate compares Stage 0 facts only (`src/eda/current_best_model/history.py:58`), so a timeline change passes it.
  2. The prediction-run gate checks only matches inside Stage 0. A player's recent ITF, Challenger-qualifying or women's-qualifying matches since June 2026 are not in Stage 0, so the gate cannot see that they are missing.

## 1. What is running now

Observed from the process list (`Get-CimInstance Win32_Process`, 15:14 UTC) and the receipts:

| PID | Collector | Package | State |
|---|---|---|---|
| 40696 | `sofascore_editions --gap challenger_points_2025 --browser` (2 s + up to 1 s) | P6, gap 1 of 7 | Since 19:42 UTC on 8 Oct. At 15:14 UTC: point records for all 14,576 linked events (11 absent); about 10,560 box scores; **about 4,000 left** (`progress.json`). Pace over the last 2 hours: about 1,130 requests an hour (a challenge at 13:49 UTC cleared by itself at 14:15) |
| 29064 | `tennislive_gaps --max-requests 40000` | P5 | Started 15:10 UTC: 36,737 pages to fetch, about 1,460 an hour (`_logs/gaps_20261009T1510Z.log`). Its trial (14:57 UTC) is in §5 |
| 5548 | `oddstrader --books-eids …` | (not in the plan) | ATP and WTA leagues only (`src/ingest/oddstrader.py:18`): main tour and its qualifying, no Challenger or ITF |
| 34864 | `lower_level_evidence/composition.py` | (team role 02) | Analysis |

The daily ITF job (P1) ran at 14:31 UTC (`official_point_feeds/runs.jsonl`: 137 requests). The brief's `tennislive_gaps --link-only` runs ended at 14:52 UTC.

## 2. The packages, P1–P12

The full table, with evidence for each status, is in `packages_2026-10-09.csv`. Plan: `docs/studies/gap_downloads/collection-plan.md`.

| Pkg | What | Status (9 Oct, 15:15 UTC) | Levels, tours, years | Grain | Volume | Landing (inferred, logged pace) |
|---|---|---|---|---|---|---|
| P1 | ITF live-data API | **Done; daily job on** | ITF, ITFQ; M, W; 15 Sep 2026 onward | results, ITF statistics (34–40 types), points (server, ace / double fault / other), start and end times | 4,906 played singles to 9 Oct; stats + points on 3,531 (main draw 99.2%, qualifying 40%); ~1,500 singles a week | Landed; grows daily |
| P2 | WTA API catch-up + women's ITF after early Sep | **Not started** (no `wta` run since 3 Oct; no `--player-matches` mode) | (a) WTA tour, WTA 125, qualifying; (b) ITF, ITFQ; W; Sep–Nov 2026 | (a) point log, box; (b) results | ~10,000 requests | ~8 h once started |
| P3 | TDI, Match Charting, Live Tennis API, Hawk-Eye | **Done 8 Oct** | TDI: ATP tour and Challengers, Jun–Oct 2026 | points, times | 6,084 TDI matches | Weekly TDI job proposed |
| P4 | TennisLive event listings | **Done 9 Oct** | every level; M, W; 2018 – 4 Oct 2026 | results, start times | 696,217 played singles; 178,506 new on the map | Landed |
| P5 | TennisLive pages: Challengers 2018–24, TQ/GSQ 2018–26, WTA 2018 | **Running** (since 15:10 UTC) | CH, CHQ (M); TQ, GSQ (M, W); WTA 2018 | points without the set-closing games; 8-statistic box | 36,737 pages | ~25 h + pauses: **evening of 10 Oct** |
| P6 | SofaScore, 7 gaps | **Running gap 1 of 7** | CH, CHQ (M) 2018–26; WTA 125 2018–26; tour residual; ATP 2018–20; WTA 2018 | complete points (server, ace and double-fault codes), full box, times | 51,687 targets; 37,012 after gap 1; ~110,000 requests | Gap 1 ~18:00–18:30 UTC today; all seven **~12–13 Oct** |
| P7 | SofaScore, ITF 2025–26 then 2018–24 | **Queued** (after P6: one session per site) | ITF main draws; M, W | full box, complete points, times | 63,259 + 207,045 targets (map of 9 Oct 03:56 UTC); ~590,000 requests | 2025–26 **~17–18 Oct**; 2018–24 **~31 Oct – 2 Nov** (≈22 Oct at the faster pace) |
| P8 | TennisLive pages for the ITF that SofaScore lacks | **Queued** (after P5, P7) | ITF 2019–26 (+ final qualifying round, optional) | 8-statistic box, partial points | ~19,000 pages | ~13 h after P7: **early–mid Nov** |
| P9 | ATP Stats Centre 2025–26, decrypted | **Not started.** Host free since 23:09 UTC on 8 Oct; the daily speed collector uses it in the mornings | tour, TQ, CH, CHQ; M | points with serve speed (tour level); Challenger speed content unmeasured | 60,000–90,000 requests | 2–3 days once started |
| P10 | Tennis Abstract charts | Not started | women's tour level; men 2025–26 | shots | ~2,500 requests | ~1 h |
| P11 | Odds below the 250s | **Not started** (probe ≤ 500 first) | CH, WTA 125, ITF; 2018–26 | opening and closing prices | unmeasured | unknown |
| P12 | ITF official statistics 2025–26 (probe) | Not started | ITF, ITFQ | umpire-device box, points | probe ≤ 150 | unknown |

**How the landing dates were reached (inferred).**
* **P6.** About 4,000 box scores were left in gap 1 at 15:14 UTC; at 1,130–1,450 an hour that is 3–3.5 hours. The other six gaps need about 74,000 record requests (two per target), plus about 3,850 listing requests (gap 1 needed 1.34 per edition; 2,876 editions are left). At about 1,300 an hour that is 55–60 hours of running. Each gap also needs a session to start it (trial, run, link check, map rebuild). So about 12–13 Oct; the data map says "12 Oct at the earliest".
* **P7.** At about 31,000 requests a day it takes about 19 days; at the adapter's 1.0 s + 0.6 s (~67,000 a day), about 9. It goes newest first: 2025–26 (holdout seasons) lands first, then 2024 back to 2018.
* **Every date slips** if the PC sleeps or a site blocks. SofaScore challenged after 24,505 requests (it recovered in 26 minutes). TennisLive went silent for 35 minutes after about 12,200 requests.

### What wiring each package needs before an input can read it

Observed: no new source is read by Stage 0 (`stage0_build.py:91-103`: Sackmann's five file groups and TML's seven). The leak-proof clock reads SofaScore, the WTA API, TDI, the Slam feeds and tennis-data.co.uk (`src/eda/match_timing/refresh.py:4-12`), but not TennisLive, the ITF API, the 2025–26 Infosys files or Tennis Abstract (`collection-plan.md:72`).

| Step | Needed for | What exists | What is missing (inferred) |
|---|---|---|---|
| 1. A Stage 0 reader for new **matches** | P1, P2(b), P4 (men's ITFQ, post-June ITF), P7's 4,415 ITF matches the files lack | TML's pattern: its ATP codes are mapped to Sackmann ids from linked matches (`stage0_build.py:17-18`) | Identity crosswalks for TennisLive slugs, SofaScore team ids, ITF player codes and WTA ids. Dedupe rules that keep real rematches at weekly venues (Monastir, Antalya). Retirements: the ITF API lists them as "Complete" |
| 2. **Box scores** for matches Stage 0 holds | P7, P8 (~202,000 ITF matches), P5/P6 (~160 Challenger matches without one), the WTA API's 1,943 women's 2025–26 matches | The Slam override table (`stage0_build.py:24-29`, `apply_box_overrides` at `:163-180`) replaces named rows' box scores | An override table keyed to Stage 0 ids. A mapping to Sackmann's nine serve counts (SofaScore: 18 fields; TennisLive: 8; ITF: 34–40 types). Stage 0's box checks (`box_status`); service games may be missing |
| 3. A **point** table | P1, P3, P5, P6, P7, P8, P9 | Staged per source under `data/dump/points/` | A common schema and a completeness rule. Only a new feature would read it |
| 4. The **clock** | P1, P4, P5, P8, P9 | `refresh.py --sources sofascore` wires P6/P7 days | Adapters in `link_sources_c.py` for TennisLive's and the ITF API's start times |
| 5. A **candidate build** | all | `run_chain.py --setup --candidate`, lanes 0–3, `compare.py` | Lane 0 is "not yet exercised" (`run_chain.py:35-37`): the first lower-level candidate is its first real run |

**The owner's rule decides the route (observed).** `history.py` sorts any difference from the reference:
* box scores added to existing matches are **revised**;
* matches the reference lacks are **new past**;
* only matches from feeds that fed the reference in its last 60 days can be **future** (`history.py:13-25`).

Sackmann's lower tiers ended on 1–2 June 2026, so no ITF, Challenger-qualifying, WTA 125 or women's-qualifying feed qualifies. Even a match of next week from P1 is "new past" until a candidate is accepted. Template builds therefore cannot carry any of the incoming lower-level data.

## 3. The dose: how much of it touches the model's players

### 3.1 Stage 0's lower levels, 2018–2024: what is results-only, and what would gain detail

Observed (`census.csv`, `targets.csv`). "Would gain" uses the frozen target lists (P5, P6) and the P7 gap derived from the map's match table with the plan's select (P7 has not frozen its own list yet).

| Tour | Level | Matches | Results only today | Would gain | Package | Relevant ±365 | Feeds 365 | Feeds 28 |
|---|---|---:|---:|---|---|---:|---:|---:|
| Men | ITF | 102,358 | 102,358 (100%) | **box + points**: 100,311 targets (~97,900 box at 97.6%) | P7, then P8 | 14,363 (14.0%) | 11,046 | 691 |
| Women | ITF | 102,784 | 102,753 (100%) | **box + points**: 101,896 targets (~99,450 box) | P7, then P8 | 38,457 (37.4%) | 31,856 | 5,810 |
| Women | ITFQ | 69,889 | 69,889 (100%) | **nothing at scale.** P7 skips qualifying; P8 fetches qualifying pages only if most carry points (P4 sample: 70 of 200; final round 43 of 62) | (P8 option) | 5,617 (8.0%) | 4,112 | 428 |
| Men | ITFQ | 0 in Stage 0 | – | results only (P4: 118,593 new) | P4 | see §3.3 | | |
| Men | CH | 37,346 | 336 | **points** on 21,429 (box already) | P5, P6 | 32,336 (86.6%) | 28,863 | 8,697 |
| Men | CHQ | 15,768 | 140 | **points** on 7,356 | P5, P6 | 6,539 (41.5%) | 4,938 | 713 |
| Women | CH | 4,132 | 136 | points on 479 | P6 | 4,045 (97.9%) | 3,935 | 2,091 |
| Women | CHQ | 611 | 17 | points on 159 | P6 | 474 (77.6%) | 397 | 101 |

Relevant counts are of all matches in the row. For the results-only matches they are 287 / 52 / 133 / 16 (±365) in the four Challenger rows, and as shown in the ITF rows.

**The targets themselves** (Stage 0 matches each gap reaches, 2018–2024, observed):

| Gap (package) | Stage 0 matches | With a box already | Relevant ±365 | Feeds 365 | Feeds 28 |
|---|---:|---:|---:|---:|---:|
| `itf_detail` (P7), men | 100,311 | 5 | 13,915 (13.9%) | 10,660 | 664 |
| `itf_detail` (P7), women | 101,896 | 5 | 38,019 (37.3%) | 31,480 | 5,709 |
| Challenger points 2018–21 (P5 and P6, the same matches) | 23,595 | 23,504 | 17,722 (75%) | 15,372 | 4,273 |
| Challenger points 2022–24 (P5 and P6) | 5,190 | 5,135 | 3,828 (74%) | 3,328 | 959 |
| WTA 125 2018–24 (P6: `wta_2018_points` CH/CHQ, `wta125_points`) | 638 | 629 | 590 | 548 | 232 |
| TQ/GSQ qualifying 2018–24 (P5) | 6,188 | 5,832 | 6,082 (98%) | 5,930 | 4,845 |

* The qualifying row's 356 matches without a box score are mostly 2018 Slam qualifying (Stage 0's GSQ box share is 49–54% in 2018, `census.csv`). TennisLive's statistics block could fill them.
* **Holdout seasons, counted only:**
  * P6's running gap (`challenger_points_2025`) reaches 14,302 Stage 0 matches of 2025–26 (8,542 relevant ±365).
  * P7's first gap (`itf_points_2025_2026`) reaches 49,180 Stage 0 matches, 96% of which already have Sackmann's box scores, plus 13,862 matches Stage 0 lacks (mostly after June 2026).

### 3.2 From the model's side: how many model matches would see their inputs move

Observed (`dose.csv`). For every model-frame match, each player's earlier Stage 0 matches in the 365 (and 28) days before it. "P7 targets" = ITF matches of 2018–2024 without a box score.

| Seasons 2019–2024 | Model matches | A player has P7 targets in the previous 365 days | … in the previous 28 days | Mean share P7 adds to a player's previous-year box-score history | A player has a Challenger point-gap match in the previous 365 days |
|---|---:|---:|---:|---:|---:|
| Men | 14,270 | 1,266 (8.9%; 7.3–10.2% by season) | 169 (1.2%) | 1.1–1.7% | 11,003 (77.1%) |
| Women | 13,061 | **8,977 (68.7%; 64–74%)** | **2,638 (20.2%)** | **14.0–18.0%** | 2,606 (20.0%) |

* **Women.** In 2019, 1,312 of 4,916 women's player rows (27%) would have a quarter or more of their previous-year box-score history new. On average, a women's model player has 8–10 ITF matches in the previous year that would gain box scores (5–7 in the short 2020–21 seasons), beside 42–46 that have one (28–33 in 2020–21).
* **The 2018 step.** 2013–2017 gain nothing: in those seasons 8,920 of 12,344 women's model matches (72%) and 1,881 of 13,019 men's (14%) have a player with pre-2018 ITF matches that stay results-only. 2025 is half-covered already (Sackmann's ITF box scores from January 2025). 2026 has no ITF box score after May.
* **Inferred consequence.** A candidate with P7 changes the women's box-score inputs in 2018–2025 and not in 2013–2017, for the same kind of player. `compare.py` will call several inputs "uneven" by construction. That is the signature of the input audit's finding #6. The IOS products are the most exposed: 01_lineage.md finds they move with the pool's level.
* **Suggestions.**
  * Either extend P7 back to 2013 (2010 for the features' warm-up), if SofaScore serves those ITF seasons (unmeasured);
  * or let ITF box scores reach the model only through a level-aware layer that keeps the shared pool's level fixed (the owner's "informative, not equivalent" design; see 03 and 06);
  * and run the candidate comparison once with the training window starting in 2019, as a control for the step.

### 3.3 Results the map holds that Stage 0 lacks

Observed (`newresults.csv`). A lower-level match is "in Stage 0" when its data-map record names Sackmann or Tennis My Life among its sources. Stage 0 is built from those two only, and the map links them by its own linker. Relevance uses players whose full name maps to exactly one Stage 0 id: ≥ 93% of ITF and ITFQ rows. The WTA lists carry surnames only, so women's WTA 125 relevance is undercounted.

| Tour | Level | New, 2018–2024 | Relevant ±365 | New, 2025–2026 | Relevant ±365 | Main source |
|---|---|---:|---:|---:|---:|---|
| Men | ITFQ | 118,593 | 760 (0.6%) | 40,231 | 160 | TennisLive listings (P4) |
| Women | ITFQ | 16,763 | 1,042 (6.2%) | 29,076 | 1,488 | WTA website records (2018 and 2025–26) |
| Men | ITF | 3,422 | 113 | 9,681 | 585 | API-Tennis; TennisLive after June 2026 |
| Women | ITF | 1,101 | 371 | 8,436 | **2,135** | TennisLive and WTA site after June 2026 |
| Men | CHQ | 880 | 55 | 1,793 | 269 | API-Tennis; TennisLive (2026) |
| Men | CH | 568 | 22 | 1 | 0 | API-Tennis |
| Women | CH / CHQ | 374 | 11 | 1,320 | 49 (undercount) | WTA API lists (box scores on disk) |

* **Results only.** These touch Elo, `elo_games`, `sets_14d` and the surface counts, not the box-score inputs. The exception is the women's WTA 125 and qualifying rows, whose WTA API box scores are on disk (1,943 in 2025–26 with tour and Slam qualifying).
* **2026 matters for the live model (inferred from observed counts).** In 2026 alone, mostly after June, 1,593 women's and 362 men's ITF matches involving a main-tour player (±365) are missing from Stage 0, and the rule in §2 keeps them out. So are 252 men's Challenger-qualifying matches. Those players' Elo, workload and form are stale in live runs. The women's side is finding #7.

### 3.4 Which input families each package touches once wired

Mapped from 01_lineage.md's master table (observed there, with code lines). Summary here:

| Package | Results: Elo (3), surface counts (4), `sets_14d` | Box scores: 17 two-week forms, `points_52w`, `ratings_iid`, `ios_points_short`, 14 IOS ratings, 7 products | Points | Stage 2 `spd_L` | Odds |
|---|---|---|---|---|---|
| P1 ITF API | yes (2026 on) | yes (2026 on, main draws 99%) | new feature only | – | – |
| P2 WTA | yes | WTA 125 and qualifying (finding #7) | – | – | – |
| P4 listings | **yes** (the largest result volume) | – | – | – | – |
| P5 TennisLive pages | – | ~160 Challenger + ~350 GSQ 2018 matches | new feature only (partial) | – | – |
| P6 SofaScore | – | ~160 Challenger matches; clock days | new feature only | – | – |
| **P7 SofaScore ITF** | 4,415 new matches | **~200,000 matches, 2018–2024** | new feature only | – | – |
| P8 TennisLive ITF | – | the ~7% P7 misses | new feature only (partial) | – | – |
| P9 Stats Centre | – | – | new feature only | **if Challenger files carry speeds** | – |
| P11 odds | – | – | – | – | lower-level rows only: no main-tour input |

## 4. What the new data makes possible that is impossible today

1. **ITF translation factors on development seasons.** Today every ITF box score is in 2025–26, the proposed holdout. Any ITF-to-tour translation estimated now would read holdout outcomes. After P7, the same-player, same-season anchors of 2018–2024 (three or more matches at each level; `translation_sample.csv`, observed) are:

   | Anchors, 2018–2024 | Today | After P7 |
   |---|---:|---:|
   | Men: ITF and Challenger | 0 | 2,109 |
   | Men: ITF and main tour | 0 | 104 |
   | Men: Challenger and main tour | 996 | 996 |
   | Women: ITF and main tour | 6 | 851 |
   | Women: ITF and WTA 125 | 6 | 851 |
   | Women: WTA 125 and main tour | 635 | 635 |

   *Inferred:* men's ITF evidence has to be translated through the Challengers (ITF→CH→MAIN), because few men play ITF and the main tour in one season. Women's can be translated directly.
2. **Point-level profiles at the Challengers.**
   * Today, on the map, Challenger point data covers 1–2% of 2018–2020 matches, 10% of 2021, and about 80% of 2022–24 (`cells.csv`); the 2022–24 points (the Infosys copy) mark only aces and double faults.
   * After P5 and P6: 28,785 matches of 2018–24, 75% of them relevant.
   * Stage 0 holds no points at any level, so any point-level profile is new code (the owner's per-statistic thesis).
3. **A lower-level price history (P11).** No Challenger or ITF price before September 2025 is held. Polymarket's begin in the holdout. P11 would allow three things on 2018–2024:
   * testing a Challenger model against its market;
   * testing whether Challenger markets under-rate players arriving from ITF (the event-levels study's §8 test, one rung down);
   * using a price move as an integrity signal.
4. **Challenger serve speeds for stage 2.** The frozen speed panel has 1,394 Challenger player rows (2022–26, 945 of them in 2026; observed). P9 could add 2025–26 Challenger MatchBeats: 3 of 4 sampled Challenger finals had a file (`data/studies/gap_sources/atp_statscentre_probe.csv`). Whether those files carry speeds is unmeasured.
5. **A tighter clock for the lower levels.** In the frozen timeline, 2018–2024 (`clock.csv`, observed), exact days cover:

   | Level | Exact days |
   |---|---:|
   | Main tour | 100% |
   | Men's Challengers | 89.5% |
   | Men's ITF | 69.8% |
   | Women's ITF | 56.4% |
   | Women's ITF qualifying | 0% (median window 7 days) |

   P7's SofaScore start times reach the clock through `refresh.py`. TennisLive's start times would need an adapter.
6. **Live histories repaired since June 2026:** P1, P2, P4 and the WTA API box scores already on disk (§3.3).

## 5. Data-quality and integrity risks, and how each would bias a player's lower-level profile

| Risk | Evidence | Which profile it biases, and how (inferred unless marked) | Mitigation (suggestion) |
|---|---|---|---|
| **TennisLive drops the game that closed each set** (P5, P8) | Observed. P5 trial (173 pages, Challengers): points on 163; complete 11; only set-closing games missing 134; median 89.5% of games. P4 ITF samples: complete 18 of 200 | The closing game is always won by the set winner. Dropping it removes about a tenth of the points, at a winning share of ~62–67% for the set winner. That lowers a set winner's points-won share by about 1 point. **Players who dominate a level (the "mostly Challenger" players) look weaker**, by about a third of the measured Challenger–tour shift (+2.9) | Use the match-total statistics block for totals. Reconstruct the closing game's server and winner from the score. Weight records by completeness. Never mix complete and partial records unflagged |
| **TennisLive swaps the two players' statistics** | Observed: 2 of 36 tour matches (gap research); **0 of 151 Challenger box scores in the P5 trial, all fields equal** | A swap gives the winner the loser's numbers, compressing both players toward each other. ITF pages (P8) have no official box score to check against | Check against the score (games, breaks against break points converted). Prefer SofaScore where both exist |
| **SofaScore coverage gaps** (P6, P7) | Observed (research): ITF box 82 of 84, complete points 78 of 84; 2018 weakest (Hungary F1 2018 lists 23 of 31). Challenger points ~74% in 2019–21, 33% in 2012–18 (ten careers) | If missing matches are early rounds or outside courts, the profile rests on later rounds against stronger opponents: raw rates too low, adjusted ones fine. **The coverage differs by year: a step the input check reads as uneven** | Measure missingness by round, grade and year after P7. Keep a coverage flag per match |
| **ITF umpire-device data** (P1, P12; likely SofaScore's ITF source too) | Observed: statistics and points on 99.2% of main draws, 40% of qualifying (final round 99.8%, earlier rounds 16.6%; M15/M25/W15 ~30%, W50–W100 100%). Point logs end early on 3%; 2% list no winner; retirements show as "Complete" | **Survivorship in qualifying:** a qualifier's box scores exist mostly when they reached the final round. Players who often lose in round 1 look better than they are. Untagged retirements bring partial matches in as full ones | Use qualifying box scores only with round-aware weights. Detect retirements from the score. *Inferred:* SofaScore's ITF statistics probably come from the same umpire feed, so agreement between the two does not validate the counting |
| **Disagreements between sources** | Observed: TennisLive listings against TML/Sackmann, 445,411 of 446,056 identical; 147 winners differ (12 are TML's Rouen 2026 rows). SofaScore against TML, ATP 2025: 0 of 3,772 winners differ | Mixing sources by event (P8 fills only what SofaScore lacks) puts a source effect on particular events, the smaller ones and 2018. **By design no ITF match will have two sources** | Fetch a seeded few hundred TennisLive pages of ITF matches SofaScore covers, to measure the disagreement |
| **The same match twice** | Observed: P5 and P6 fetch the same 28,785 Challenger matches. TML misdates some events (Irving 2018 under Dallas's date; Biella 2–7 under Biella 1): 172–174 targets per Challenger list link only at 11–45 days. The WTA-site file repeats 12% of its ITF rows. The map's loose test flags ≤ 100 of 178,506 added matches | Double counting doubles a match's weight in Elo, form, workload and the IOS. **Weekly venues** (Monastir, Antalya) hold real rematches a week apart, so a "same pair within 7 days" rule would delete real matches of exactly the ITF grinders | One merge rule per grain (SofaScore complete, then TennisLive partial; never both). Dedupe on event identity, not on the pair |
| **Integrity alerts concentrate at Challenger 50/75 and ITF** | Observed (event_levels §9): alerts per bettable match in 2013–17 were 0.70% at Challengers and 0.31% at men's ITF. ITIA 2025: 22 of 28 Challenger alerts at CH 50/75; men's ITF 28 | A manipulated match's statistics do not measure ability. Few matches, but they sit where "mostly lower-level" players earn their evidence | Winsorise per-match statistics. Give CH 50/75 and M15/W15 lower weight. Apply ITIA's sanction list. *Not held:* the Challenger tier (50–175) is not a Stage 0 field |
| **The 2018 start** (P5, P6, P7) | Observed (§3.2) | Point data and ITF box scores begin in 2018. Training seasons from 2013 lack them: a time-varying input distribution | See §3.2 |

## 6. Re-review triggers and the re-run order

**Triggers, in the order they are likely to occur:**

| # | Event | What it changes | Re-run |
|---|---|---|---|
| T1 | P6 gap 1 done, link check and map rebuild (today) | Challenger points 2025–26 (holdout seasons); no current input | `incoming.py` |
| T2 | P5 done (about 10 Oct) | Challenger and qualifying points 2018–26 (partial); ~500 box scores | `incoming.py`. Check `box_swapped` and completeness in `tennislive_gaps_summary.json` |
| T3 | P6 all gaps done, then **`refresh.py --sources sofascore`** (about 12–13 Oct) | The live timeline and leak-proof IOS inputs change, **with no Stage 0 change, so the history gate does not see it** | `incoming.py` (clock), then a template build run **as a candidate** and `compare.py`, input check first |
| T4 | P7 freezes its gap lists (its first run) | The real targets replace this report's map-derived ones | `incoming.py` |
| T5 | P7's ITF 2025–26 done (about 17–18 Oct) | ITF points for 2025–26; box scores after June 2026. Holdout seasons: live features only | `incoming.py`; the prediction-run gate's view of ITF players |
| T6 | **P7's ITF 2018–24 done (about 1 Nov; earlier at the faster pace), wired into a candidate Stage 0** | The main event: ~200,000 box scores, the 2018 step | See the run order below |
| T7 | P8 done (November) | Remaining ITF; the source mix | as T6, with the source mix checked by event |
| T8 | P9 started, with Challenger speeds | Stage 2's `spd_L`; no history guard covers the speed panel (01_lineage.md) | Stage 2 coefficients refitted as a candidate; `compare.py` (both stages) |
| T9 | P11 probe positive, odds collected | Lower-level edge tests become possible on 2018–24 | A lower-level model study; the §8 test at the Challengers |
| T10 | P1, P2, P4 or the WTA API box scores wired into a **live** candidate | Finding #7; the prediction gate's blind spot | Prediction-run replay (`src/eda/prediction_run/replay.py`) |
| T11 | A new frozen reference, or any Stage 0 rebuild | Everything | All scripts with `--stage0-dir` |
| T12 | A collector stops (block, sleep, budget) | Landing dates | `incoming.py` (its `progress.json` re-reads the receipts) |

**Run order for this dossier after a trigger.** No collector or rebuild is started by these scripts.
1. The owning session runs the collector's checks: `verify_links.py --gap <gap>` (SofaScore); `tennislive_gaps` writes its own (`record_verdict`, `box_swapped`). Then the map rebuild: `./python.sh src/eda/data_map/build.py`.
2. `./python.sh src/eda/lower_level_evidence/incoming.py` (about 25 seconds; reads no outcome). It refreshes the counts, targets, cells, new results, dose, clock and progress.
3. Once a candidate Stage 0 exists:
   * `./python.sh src/eda/lower_level_evidence/composition.py --stage0-dir <candidate> --label <name>`;
   * `./python.sh src/eda/lower_level_evidence/translation.py --stage0-dir <candidate> --label <name>` (`--through 2024` is the default);
   * `incoming.py --stage0-dir <candidate> --out <folder>`.
4. The lead's `refresh.py`, which regenerates the dossier's tables.
5. The candidate model:
   * `run_chain.py --setup --candidate --out <folder>`;
   * lane 0 (its first real use), lanes 1–3, `--collect`;
   * `fits.py --out <folder> --seeds 0-3 --seasons 2019-2024`;
   * `./python.sh src/eda/current_best_model/compare.py --candidate <folder>`. Read the input check (uneven inputs) before the scores.

## 7. What could not be determined

* **P7's yield on 2025–26.** Unmeasured: the block stopped that count in the research. The plan stops the run if its trial links fewer than 80% of targets.
* **Whether SofaScore serves ITF before 2018.** This decides whether the 2018 step can be removed.
* **Whether Challenger MatchBeats files carry serve speeds** (P9).
* **Lower-level odds coverage** at any site (P11 is unprobed).
* **The timeline gap is inferred from the code, not measured.** That a SofaScore refresh moves historical model inputs has not been tested. The reference's own TDI refresh moved none, because its changed days all fell after the frame's last matches.
* **Relevance gaps.**
  * 885 + 136 + 356 Challenger targets created from TML rows are in Stage 0 by the map's sources, but my surname join did not place them (`unlinked_but_in_stage0` in `targets.csv`). Their relevance flags are missing: a 3–4% undercount for those gaps.
  * Women's WTA 125 relevance in §3.3 is undercounted (surname-only names).
* **The dates are estimates.** They assume continuous running at the logged pace. Every gap after P6's first needs a session to start it. P7 needs the Chrome window for one to three weeks.

## Files

| File | What it holds |
|---|---|
| `data/studies/lower_level_evidence/incoming/census.csv` | Stage 0 by tour × bucket × year (2018–26): matches, box scores, results-only, the three relevance counts (matches and player rows) |
| `targets.csv` | Each gap × source × tour × level × year: targets, links to Stage 0 (by name and date, and by the map's sources), box scores held, relevance |
| `cells.csv` | The data map's coverage cells against Stage 0, on (tour, level, year), 2018–26 |
| `newresults.csv` | The map's lower-level matches Stage 0 lacks, by creator: relevance, near-duplicates, WTA API box scores on disk |
| `dose.csv` | Model-frame matches by tour and season: exposure to P7 targets (365 and 28 days), the share P7 adds, pre-2018 ITF, Challenger point gaps |
| `translation_sample.csv` | Same-player, same-season anchors by level pair, today and after P7 |
| `clock.csv` | The frozen timeline's exact-day share and window widths by level, 2018–24 |
| `packages_2026-10-09.csv` | The P1–P12 snapshot with the evidence for each status (written by hand, dated) |
| `progress.json`, `summary.json` | The collectors' state from their receipts; the key counts, input hashes and the relevance check |
| `src/eda/lower_level_evidence/incoming.py` | The code (`--stage0-dir`, `--out`, `--skip-progress`) |
