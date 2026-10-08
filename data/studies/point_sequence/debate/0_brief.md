# Brief: point-by-point momentum / streak / sequence statistics for the best tennis model

Repository: `C:\Users\zerom\Documents\Tennis-predictions` (read CLAUDE.md first; it is binding). Date: 6 Oct 2026.
Written by the main session from the repo's study reports; the auditor should spot-check it, it may contain errors.

## 1. The owner's frame (binding preferences)

* Edge thesis: beat the betting market with **point-by-point data** and **per-statistic offence/defence profiles**.
  Win/loss ratings, Elo refinements and points-won aggregates are treated as priced in: controls only, never headlined.
* Results are ranked by **gain over the closing odds** (and, because the owner bets before the close, over the
  Polymarket price ~24 h before the start), never by gain over Elo.
* A null against the close is never "unbeatable / priced in, route closed": name concrete process suspects and iterate
  (the owner knows someone who beats the tennis close with public data).
* Every score shown must state direction: "milli-log-loss (mLL), positive = second-named better", winner in words,
  and "tie" when the 95% interval spans 0. Label claims observed / inferred / suggestion.
* Owner floats an idea = build and score it, don't stop for approval (unless he asks for a gate).
* The owner's request today: where did we leave off on rebuilding point-by-point data to generate NEW statistics
  (momentum, streaks, summary statistics that don't exist as standalone stats in box-score data) for the current best
  model; explore creative possibilities; identify what is most promising, either to get more data for or to combine
  in novel ways with other statistics. He expects coverage gaps ("we may not have the data to be profitable if we are
  imputing a bunch of data, but we may have leads").

## 2. The current best model

* Local, non-thinking **TabPFN-3.5** (open checkpoint `tabpfn-v3.5-20260909`, RTX 5090, env `./python_tabpfn_local.sh`,
  helper `src/eda/tabpfn_local/runtime.py`). 8 estimators, softmax temperature 0.9, both orientations symmetrised.
* Inputs: closing odds' log-odds + 53 inputs (`src/eda/tabpfn_thinking/common.py`, `TABPFN_NAMES`):
  `elo_logit, ratings_iid, elo_games, adjperf_tpw_2w, ios_points_short, points_52w, sets_14d, surface_first, age, age_sq,`
  12 decayed box-score form stats `form_{ace,df,first_in,first_won,second_won,hold,bp_saved,bp_faced_pg,brk,bp_conv,rpw_first,rpw_second}`,
  4 `formdef_*`, 14 leak-proof IOS offence/defence `iosO_*/iosD_*` (ace, df, first_in, first_won, second_won, hold, bp_saved),
  7 `prod_*`, context `tour, surface, level, indoor, best_of, round`. **No point-sequence / momentum input exists.**
* Frame: `data/studies/surface_ios/base_frame.parquet` = every main-tour (Slam to 250) main-draw match with closing odds,
  2013–2026: 39,918 train (2013–2021) + 23,819 test (2022–2026). Harness for new inputs: `src/eda/surface_ios/`
  (frames, arms, run_local, score) and `src/eda/surface_rating_race/`: five expanding windows (one fit per test season
  2022..2026), one calibration slope per tour (fitted on 2019–2021 out-of-sample forecasts, or refitted each season).
* Standing: men +1.60 [+0.84, +2.36] mLL over the recalibrated close in 2022–2026 (positive = model better); both tours
  with per-season refit slopes +1.30 [+0.65, +1.94]. Women's gain is mostly calibration. Owner decision 6 Oct 2026: keep
  the per-surface IOS profile (men). Fed the Polymarket price 24 h out, the model beats that price by about +1.6–1.8
  (ties on few matches); fed the 30-minute price, ~0. The early price drifts toward the model's no-odds view
  (`docs/studies/surface_rating_race/README.md`, `docs/studies/line_sharpening/README.md`).

## 3. Point-level data on disk (what exists, and whether any feature uses it)

| Source | Where | Coverage | Per-point width | Used in a feature? |
|---|---|---|---|---|
| Kaggle `marcosjn2` SofaScore scrape | `data/raw/gap_sources/marcosjn2/{atp,wta}-matches.jsonl`; summary `data/studies/gap_sources/marcosjn2_summary.json`; replay code `src/eda/gap_sources/marcosjn2_links.py` | 48,479 ATP+WTA tour-level matches, Jun 2015 – Jun 2025 (men 25,185, women 23,294); main draw e.g. men 1000s 445–648/yr, 250s 622–915/yr (2016–2024); 99.6% replay complete; set scores = official in >99% | point winner + server, game/set structure. Drop the trailing extra point appended to 99.5% of tie-breaks | **No** |
| WTA official API | `data/dump/points/wta/` (`events/`, `points/`, `momentum/`, `advanced/`, `stats/` by year) | every WTA draw 2019 (from April) – 2026; ~33,300 matches 2020–2026 | umpire event log: point, ace, fault, let, challenge, overrule, suspension, violations, **medical and toilet breaks**, ms timestamps; point-by-point 2022–26 (gap Oct 2025–Mar 2026); per-point win probability and "momentum" 2025–26; advanced stats 2021–26 (winners/errors by wing, rally-length buckets, net approaches) | **No** |
| SofaScore by tournament | `data/dump/points/sofascore_editions/`, `sofascore_tournaments/`, `sofascore/` | ATP tour level 2025 – Jun 2026 (3,777 matches, every point); AO/RG 2022–26 gap (1,632); ten careers | score per point, server, ace/DF codes (beware: server may shift on game-ending points) | **No** |
| Infosys (ATP pipeline handoff) | `data/raw/public_dump/atp_pipeline_handoff/`, see `docs/studies/atp_pipeline_handoff/` | ~37,800 ATP tour + Challenger + qualifying matches 2021–2024, ~70% with every point | serve number, outcome, rally, speed | partly (shot-level study) |
| TDI Tennis Results | `data/dump/points/tdi/` | 6,096 ATP tour + Challenger matches (mostly Jun–Sep 2026; weekly forward capture) | UTC time per point, 1st/2nd serve, winner/FE/UE, rally, net | partly |
| Slam feeds | Sackmann Slam pbp 2011–2024 (`data/dump/points/sackmann_archive/`); Wimbledon 2019, 2021–26 and US Open 2022–26 SlamTracker (`wimbledon/`, `usopen/`: clock times, stroke sentence, IBM likelihood-to-win per point 2025–26); AO 2026 (`ausopen/`); AO/RG Hawk-Eye 2019–24 (`slam_ball_tracking/`) | all Slam main draws 2011–2026 | rich | partly |
| MCP charts | `data/dump/points/match_charting_project/` | 9,406 matches shot by shot | every shot | partly |
| Sackmann point strings | raw, see `data/data_map.yaml` id `sackmann_point_strings` | men 2011 – Jan 2017, T250/TQ/CH/ITF | winner + server | no |
| Polymarket | ticks to 5 Oct 2026 (incl. in-play), all trades with accounts 18 Sep 2025 – 21 Sep 2026, PMXT order books 4 days | singles match-winner markets | prices / fills with timestamps | pre-match only so far |

Data-map coverage of point-or-better detail (`data/studies/data_map/coverage_cells.csv`; **excludes marcosjn2**):
men main tour 2022–2026 86–100% (Slams ~100%), 2018–2021 non-Slam only 10–38%; women main tour 2020–2026 88–100%,
2019 50–57%, 2018 0–5%. marcosjn2 should fill most of 2016–2021 for both tours. 2013–2015 (in the training window)
stays thin outside Slams.

## 4. What was already tested near this topic (all pre-match unless noted)

1. **Clutch / big points** (`docs/studies/predictability_diagnostic/stage2.md`, Slam pbp + iid model): servers win slightly
   fewer big points than pure luck gives (men −0.27 per 100 importance-weighted serve points beyond luck); break points
   saved 0.7 fewer than luck. "Clutch records" (break points, tiebreaks, deciding sets) are luck: a good tiebreak
   record even predicts slightly worse results. **Open, never tested:** the women's points share decides matches less
   than iid luck predicts (log loss 0.118 vs 0.103), "streaks of form within a match are one candidate".
2. **Fatigue / late-match decline** (`docs/studies/ufc_ideas/stageC.md`): not a trait for men beyond luck (split-half
   ≤ 0.09), tentative for women; no gain given Elo or the odds. But real winners gain more late than the iid replay,
   even in the 3rd set alone (within-match dynamics exist; suggested for in-play). "Grinder" = margin, not stamina.
3. **Shot-level study** (`docs/studies/shot_level/`, 2 Oct): a point table from 8 annotated sources (38,293 matches;
   NOT WTA API, SofaScore, marcosjn2). Its "point sequence" family, per player-match: hold right after breaking
   (split-half r 0.43 men / 0.49 women), break back right after being broken (0.38 / 0.52), hold when serving for the
   set (0.33 / 0.31), serve points won at 30-30/deuce/BP minus all serve points (0.17 / chance), first serves in under
   pressure (0.22 / 0.30), serve points won after a lost point (chance / chance). As 141 pre-match features: nothing
   adds to the closing odds (best sequence rows ~0.0–0.05 mLL; the sequence profile with a ridge fit ~0). The one
   lead: men's recent change in serve speed, +0.24 [+0.07, +0.41] on the odds 2022–2026. Planted edges: in noisy
   statistics, edges of 1–2 mLL could hide.
4. The box-score profile (12 stats, 2-week memory) is the long-standing lead; it is in the model. Workload
   (`sets_14d`) adds +0.23 / +0.29 given the market.

## 5. Never done (as far as the main session can tell)

* No unified point-sequence (score-progression) table across all sources; marcosjn2, the WTA API and SofaScore's
  tour-level points have never fed a feature. Coverage of sequence features would rise from ~30k matches to most
  main-tour matches of 2016–2026.
* Momentum / streak measures proper were never built: point- and game-level serial dependence beyond iid, run
  lengths, reaction to being broken / breaking, comebacks from deficits, closing out leads, win-probability swing
  and leverage measures, first-set vs later-set level, slow starts.
* Event-log signals (WTA medical / toilet breaks, violations, suspensions; time between points from timestamps)
  never used.
* Previous-match "narrative" (saved match points, comeback, marathon, late finish) never tested against the close.
* In-play: point timestamps (WTA, Slam feeds, TDI) + Polymarket in-play ticks would allow testing how the market
  reacts to momentum swings; never done.

## 6. Rules

* `./python.sh` for the `tennis` env; `./python_tabpfn_local.sh` for local TabPFN. No state-changing git command.
  Do not delete files. Study code `src/eda/<study>/`, outputs `data/studies/<study>/`, reports `docs/studies/`.
  Agents in this session: write only to the scratchpad directory unless told otherwise.
* Feature timing (decided 5 Oct 2026, `docs/decisions/2026-10-05-match-timing.md`): own-history features in order are
  safe; anything combining different players' results must use the leak-proof clock
  `data/studies/match_timing/timing.parquet` (a result counts from the day after its latest possible finish; a match
  reads the state at its earliest possible start); test new cross-player features with `src/eda/match_timing/probe.py`.
* No paid API calls. Local GPU fits are free but shared with other sessions.

## 7. Corrections after the auditor's round 1 (verified by the main session, 6 Oct 2026)

* **The current model has 58 inputs**, not 54: owner decision 6 Oct (`docs/decisions/2026-10-06-offset-elo.md`) swapped
  `elo_logit` + `surface_first` for `elo_overall, elo_surf_offset, surf_season_a/b, surf_layoff_a/b`; IOS profile is
  per surface. Frame: `data/studies/surface_rating_race/model/model_frame.parquet` (same 63,737 matches; list in
  `model_inputs.json`). The 58-input model's own edge over the close has not been re-measured as a whole (each swap tied).
* The "+1.6–1.8 at the 24 h price" belongs to the offset-rating arms (ties, ±4 intervals); the then-base got +1.06
  [−3.02, +5.14], a tie. Betting the model at Polymarket's early market instead of the close: $0.00 per 100 matches.
* **Depth, not presence, was the binding constraint** for earlier sequence features: they already existed on ~95% of
  test matches, but on a median of 5–58 relevant games per player-year, so squared correlation with the true trait was
  0.15–0.35. New sources mainly add depth and training-window rows.
* WTA API: real win probabilities only 2026; full advanced stats only 2025–26; 2019 complete only from June; no Slams;
  some tie-breaks logged "0-0" (winners filled from the listing); correction "undo" runs not read (can fake streaks).
  Use the event log, not the point-by-point endpoint.
* Already tested (raw forms): serve after a lost point (chance), hold after break / break back / serve for set (ability
  in disguise; R² 0.22–0.25 with odds+Elo), pressure excesses, early vs late, importance-weighted big points (return
  side persisted beyond luck, 0.21/0.19, but failed pre-match with the wrong sign). NOT built: residualised (momentum
  only) versions, run lengths / overdispersion, comebacks and close-outs against win probability, set-to-set swings,
  slow starts; nothing in TabPFN, against the 24 h price, or in-play.
* `src/eda/point_sequence/` is THIS session's builder agent (started 17:38), not a prior build.
* A concurrent study, `docs/studies/feature_interactions/`, keeps **2025–2026 closed** until one final pre-registered
  test (discovery ≤ 2021, replication 2022–2024). This study adopts the same discipline: no design or tuning choice may
  read 2025–26 outcomes. The GPU is shared with it.
* Stage 0 was rebuilt at 17:07; 42 WTA 2026 match ids changed (`data/studies/data_continuity/rebuilds/2026-10-07T0005Z/id_map.csv`).
* In-play: ~5,270 main-tour Polymarket markets with in-play minute prices (Sep 2025 – Oct 2026); official per-point
  clocks for ~1,900 of 2026's (WTA 1,269, Slams 371, TDI 256) plus ~400–600 WTA late 2025: ~75% women. Trade costs
  ~3¢ per trade in play (5% × (1 − p) fee since July 2026 + spread). Point feeds are collected after events.
* WTA event-log incidence, singles 2022–25: physio call 16–17%, medical treatment 16%, toilet break 34–40%, time
  violation 5–6%, code violation 5%, suspension 8–12%.
* Power (auditor, 80% power, 2022–26): one-input feature vs close ≈ 1.6 mLL per tour (0.8 both tours); true-trait
  behind a noisy sequence stat ≈ 4.5–8 per tour. Best features ever found vs the close: 0.25–0.4.
