# A daily update in minutes, not hours: process log

10–11 October 2026 (PDT) · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code) · Session:
`d061329f-0568-4169-b891-1a461e96dc2d` (the session that integrated the level layer: `docs/studies/level_layer_adoption/`)
· For a future reviewer · Report: README.md (written at the end)

## 1. The request

* **The owner's words, verbatim** (10 Oct 2026, about 17:40–17:50 PDT, after the level-layer report):
  > "How the hell is this acceptable and no model missed this ? [the pasted "Why it took about 7 hours" section of my
  > summary] We are betting this thing daily, I cant run 7 hours of fits on my computer everytime I make a bet??? or
  > every day?"

  Then, after I answered that a morning run of about 2 hours would rebuild the inputs and that the bet-time step should
  take seconds:
  > ""Each morning: rebuild the player profiles from yesterday's results. Today that takes about 2 hours of unattended
  > computer time, and one run covers the whole day's matches." This is unnaceptable. Anything even close to this is
  > unacceptable."
* **How it is read.**
  * The daily update (new results in, the day's matches' 57 inputs out) must take minutes at most; my working target is
    a couple of minutes. Pricing at bet time must be immediate.
  * The correctness bar does not move: live inputs must equal the inputs a full rebuild gives (the 8 Oct prediction-run
    decision; proven by `prediction_run/replay.py`, bit for bit on 10 Oct).
  * Set aside: running the 2-hour rebuild overnight (the owner rejected anything close to it); constant-factor speed-ups
    of the full rebuild alone (they cannot reach minutes from 2 hours without changing what is recomputed).
  * Open, for the owner: an exact time budget; whether the forecast step (not built: `predictions/README.md`) comes
    first or together. The owner says bets are placed daily; this repository holds no forecast and no recorded bet, so
    what feeds those bets is unknown to me (asked).

## 2. Starting point

* The live path (`src/eda/prediction_run/run.py --build`) rebuilds Stage 0 and the whole input chain from scratch in a
  sandbox: about 2 h 05 min alone (the 10 Oct replay: preparation about 20 min, chain 1 h 44 min), 2.5–3.2 h when
  several builds share the machine. Observed: `data/studies/prediction_run/replay_2026-10-10_layer/build_resumed.out`,
  `data/studies/current_best_model/level_layer_2026-10-10/chain_lane*.json`.
* Only one of the 57 inputs reads the price (`odds_logit`); the other 56 depend on results before the match.
* The model (TabPFN 9.1.0, local) is not retrained within a season (season Y on 2013..Y−1); `fit_mode` caching exists
  in the library.

## 3. Plan

1. **Where the time goes:** each step's minutes, and whether its output reaches any of the 57 inputs.
2. **What each input-producing step needs to update a day:** per-player state carried forward (Elo, forms, workload),
   a joint solve for one more day (IOS), a tuning grid whose answer is pinned anyway, data loading.
3. **A design** that updates from saved state, with the replay as the proof (inputs equal to a full rebuild's).
4. **Report to the owner** with a time estimate before building, then build.

## 4. Chronology

Local time PDT (UTC−7). "Results" means any outcome-based score; none is read in this work. Times from 17:5x are
approximate (written as the steps ended).

| When | Step (command or action) | Why | Results seen by then | Output |
|---|---|---|---|---|
| 17:5x | Log opened | Rule 2 | none (this work reads no scores) | — |
| 18:00 | Owner, verbatim, mid-turn: ""A lower-level result is adjusted for how strong the opponent was and for the level." Also how do we do this? How do we measure a low tour fights "strength" compared to the 250+ tour players". Answered in chat from the level-evidence study's role B report (`docs/studies/lower_level_evidence/system/B_relationship.md`) and `level_layer.py`'s docstring: one Elo pool over all levels; γ per 100 Elo against E_ref; δ per level; w; walk-forward fits | — | — | — |
| 18:05 | Four read-only scoping subagents launched in parallel (general-purpose; briefs verbatim in [subagent_briefs.md](subagent_briefs.md)): A the preparation path, B Elo and Stages 1–4 and the Elo pieces, C the UFC-ideas stages, D the frames, the surface IOS and the 57-input chain of custody | Plan steps 1–2 | — | running |
| 18:10 | Step times of the stand-alone replay build (`build.out`, `build_resumed.out`; observed) | Plan step 1 | — | **Preparation 7.8 min** (Stage 0 2.3, timing check 3.1, timeline 0.8, the rest ≤ 0.4 each), `timing_features` (`rebuild.py`) 8.0. **Lane 1, 95.7 min in sequence:** `stage1_baselines` 19.1, `ufc_stageB_adjperf` 17.6, `ufc_stageA_ratings` 14.3, `stage4_features` 9.4, `ufc_stageB_ios` 7.3, `ufc_stageB_rundown` 7.2, `elo_pieces` 7.0, `ufc_stageD_profile` 3.8, `stage3_ratings` 2.2, `ufc_stageC_sos` 2.1, `ufc_stageB_split` 2.0, `ufc_stageC_rundown` 1.3, `ufc_stageC_fatigue` 1.1, `ufc_stageD_rundown` 0.9, frames ≤ 0.2. **Lane 2 beside it:** surface IOS 16.6 (cache 1.2, features 15.4). Lane 3 0.1. Critical path about 112 min. (`stage1_baselines` from the timestamps: its exit line interleaves with lane 2's) |
| 18:20 | `src/eda/daily_update_speed/bet_time_pricing.py` written and launched (GPU, `./python_tabpfn_local.sh`): season 2026's model, seed 0, on the 23 replay matches: (A) today's fit-then-predict, timed; (B) against the stored forecast; (C) `fit_mode="fit_with_cache"`, predictions timed; (D) a 91-price grid per match in one call, read back at the match's own price. No outcome scored (the fit reads the training labels, as every fit does) | The bet-time half of the target | — | running |
| 18:27 | Its result (`data/studies/daily_update_speed/bet_time_pricing.json`; observed) | — | — | **(A)** `fit` 0.75 s (preprocessing only); `predict_proba` 41.3 s for 23 matches, 41.2 s again (identical): the cost is the 62,869 training rows, paid at every prediction. **(B)** predicting the 23 alone vs inside the season's batch: ≤ 3.7e-5. **(C)** the cache: fit 42.5 s, then 1.03 s per call (23 matches or 1), 8.2 GB, **but its probabilities differ from (A) by up to 0.179**: not the decided model's numbers; not usable until explained. **(D)** grid on the cached model: 4,186 rows in 4.2 s; inherits (C)'s difference; 121 of 2,070 steps fall (largest 0.0067) |
| 18:28 | The `.out` of the first run, written by mistake to `data/studies/daily_update_speed_bet_time.out`, moved into the study folder (`bet_time_pricing.out`). `--grid-plain` added and launched: the price grid on a plain fit (the decided inference path) | (C) is not the decided model | (A)–(D) | running |
| 18:31 | Its result (`bet_time_pricing_grid_plain.json`; observed) | — | — | **(E)** 23 matches × 91 prices (4,186 rows with the flips) in **57.4 s** on one seed; read back at each match's own price by linear interpolation in log-odds: **within 0.0008 of the direct prediction**; 12 of 2,070 steps fall (largest 0.003): the curve is nearly monotone. So the decided path can price a day's matches at every price in about a minute per seed (16 seeds: about 15 min), and bet time becomes a lookup |
| 18:40 | Subagent A (preparation path) reported; taken as reported, its claims to be re-checked before any code relies on them | Plan steps 1–2 | — | Preparation about 16 min (464 s + `rebuild.py` 481 s). **`rebuild.py` reaches none of the 57** (its 22 columns are replaced by lane 2's surface IOS; only checks read it) → skip, with live-row exemptions in two checks. **`timing_check` (3.1 min) and `stage0_checks` report-only** → skip. The cheap global steps (additions, inject, layer resolve, odds, links, timeline: about 2–3 min) must run in full: their pooled statistics make an incremental version unequal. Stage 0 (135 s) must be rebuilt from the day's dump; about 75% of it is per-row Python. **Past rows move every day** (TML revisions, restaged sources, events in progress, the live rows' own day links): an exact incremental mode must diff and resume from the earliest changed day, or the owner chooses to hold past history fixed between full rebuilds |
| 18:45 | Subagent C (the UFC-ideas stages) reported; taken as reported, to be re-checked | Plan steps 1–2 | — | **Only `stageB_adjperf` computes values that reach the 57** (the 17 forms); `stageD_rundown` copies 6 more from Stage 4. **Stage A, Stage C, `stageB_ios`, the registry check and `stageB_split` reach none** (28–60 min a build): skip, with two assert bypasses (`stageD_rundown.py:76`, `stageB_rundown.py:211`) and the replaced IOS columns filled from the leak-proof table. The three rundowns: frame-only exits (12–23 min saved; the frames are column copies). `stageB_adjperf` without its tuning (discarded by the pin under the layer) and its probe: about 5 min (estimate); with float64 state saved at a cut before every running event: seconds; float32 storage makes the summation order matter. Also found: the prep's `rebuild.py` recomputes the same 17 forms (704 s on 9 Oct) for nothing; **live rows of 2027 would fall out of the pool** (`predictability_diagnostic/common.py:54`) unless the year ranges are extended |
| 18:50 | Subagent B (Elo, Stages 1–4, Elo pieces) reported; taken as reported, to be re-checked | Plan steps 1–2 | — | **`stage1_baselines` reaches no input through its tables** (only its constants, identical in every build since 8 Oct; the layer config pins the same K): skip. About 23 min a build is tuning grids whose winners cannot move while data to 2018 is unchanged (Stage 1, Stage 3, pieces); about 13 min is leak probes; Stage 4 builds 165 columns of which 6 reach inputs. What remains: one Elo-type pass per tour (about 3 s), one Stage 3 pass per tour (7–15 s), per-player window sums: **about 1–2 min on full history, seconds with snapshots at tournament-date boundaries** (estimate). Float32 casts must be copied exactly. **Calendar cliff, confirmed by a second agent: `pool_mask` caps years at 2026 (`C.EVAL_YEARS`) and the base frame's `TEST_YEARS` ends in 2026: from 1 Jan 2027 no match gets inputs, in a full build or a live one** |
| 18:52 | The calendar cliff re-checked by me (observed): `predictability_diagnostic/common.py` `EVAL_YEARS = range(2013, 2027)`; `stage4_features.pool_mask` keeps years `FIRST_YEAR .. EVAL_YEARS[-1]` (line 1483); `tabpfn_thinking/common.py` `TEST_YEARS = (2022, 2026)`, used by `build_frame.py` lines 156–157 to set the split | A claim from two agents that would stop the model on 1 Jan 2027 | — | **confirmed** |
| 19:05 | Subagent D (frames, surface IOS, the 57-input chain of custody) reported; taken as reported except the line below | Plan steps 1–2 | — | The 57 inputs come from 7 computations (`scoping.md`). The whole leak-proof IOS family (`rebuild.py`, `leakproof_frame`, `frames.py`, the 16 "current" runs) feeds only cross-checks. Only 14 of the 32 surface-IOS runs reach inputs (42% of lane 2's CPU saved). All frames are row-wise: a live mode can assemble the live rows only. Surface IOS checkpoint and resume: bit-equal on the same tables; a cold one-day solve only to 1e-8 (to be measured). Also: `model_frame.py` reads a stale `ttt_timed.parquet` in prediction runs (not an input) |
| 19:08 | Re-checked by me (observed): `surface_rating_race/arms.py` `ARMS["model"]` takes the 21 IOS inputs as `sf_<name>` from the `sprof` arm; `model_frame.py` checks only the other inputs against the leak-proof upload | The claim that decides most skips | — | **confirmed** |
| 19:10 | Synthesis written (`scoping.md`, `README.md`) | Plan step 3 | — | Lean build about 10 min (no state, same numbers); about 2 min with saved state; pricing by a morning price grid (about 15 min for 16 seeds), bet time a lookup. Estimates from step times and the subagents' extrapolations, not measured end to end |
| 19:25 | Owner, verbatim: "Im not betting yet, I plan to be betting. Thats a future very soon step. "then step 1 together with the forecast step, so in about a week you could bet off this model daily on about 25 minutes of unattended computer time; then step 2 and the pricing speed-up." explain this more and clearly". Answered in chat after checking which live feeds exist (observed: `src/ingest/scheduled.py` runs Tennis My Life daily, a serve-speed job and the ITF API; `speed_daily.py` says its ATP collector is off until enabled; `oddstrader.py` reads BetOnline's and other books' current lines; `refresh_odds.py` lists Polymarket's events). The forecast step's scope corrected upward: the daily matchups must be fetched and matched to the project's player ids | — | — | — |
| 19:35 | Owner, verbatim: "2-3 days of work with high powered llms is completly insane? what are you recommending to me???" Answered: my estimates were a human team's; the coding is hours, the time goes to builds and their proofs. Revised: the lean build a few hours (today), the forecast step a few more, saved state and fast pricing about a day. Recommended starting now in that order; the 2027 fix after (not needed before January). Started the lean build | — | — | — |
| 19:40 | Owner, verbatim, mid-turn: "Execute this "The 2027 fix (about an hour). Remove the year limits that would stop the pipeline on 1 January."" The lean build paused; the 2027 fix started | — | — | — |
| 19:40–19:55 | Inventory: every year literal in the chain's modules (prep, lanes 1–3, frames, fits, stage 2, prediction runs, the timeline's sources, the downloaders), each read in context | Which limits gate a match's inputs | — | **Gating (fixed):** Stage 0's evaluation flag and Stage 4's pool (`EVAL_YEARS` to 2026); the frame split (`TEST_YEARS` to 2026); the timeline's eras (2027 had none: its own empty class); the Grand Slam feeds' timestamp bound (before 2027-01-01: AO 2027's times would be dropped); Stage 1's per-season loop (2027 rows without `p_rank`); Stage 2's next season (2027 only: a 2028 cliff); `fits.py`'s default seasons. **Not gating (left):** tuning and report windows; the downloaders' manual default end year (`public_dump/common.py` 2026; the scheduled TML job and `refresh_odds` choose years from the date); the level layer (seasons after the last fitted one read its parameters, decided); the strength re-centring (extrapolates the nearest season) |
| 19:55–20:10 | Edits (each leaves every season to 2026 as it was): `predictability_diagnostic/common.py` (`EVAL_FROM`, `in_evaluation`, `era_of` open-ended); `stage0_build.py`; `lower_level_evidence/candidate_stage0.py`; `stage4_features.pool_mask`; `stage1_baselines.py` (the seasons held); `tabpfn_thinking/build_frame.py` (`split_of`); `match_timing/timing.era_of`; `match_timing/srcc_slams.py` (`epoch_hi`: the old bound for seasons to 2026, the next 1 January for later ones); `serve_speed_tabpfn/adaptive/adjust.py` (every fittable later season); `model_rebuild/fits.py` (default to the frame's last season). Two of these are hooked builders: `system_sandbox.POST_VALIDATION` lists their edits and `validated_now` applies them, so the study's snapshot check and `system_arms.restore_validated_code` still prove the integrated code is the validated code plus exactly these edits | The fix | — | all compile; line endings kept |
| 20:10 | `test/daily_update_speed/test_year_limits.py` (5 tests: a 2027 match passes each gate; seasons to 2026 unchanged) | Proof for 2027 | — | 5 pass |
| 20:15 | `src/eda/daily_update_speed/year_fix_checks.py`: each changed rule, old against new, on today's data | Proof nothing moved | — | **all equal** (`year_fix_checks.json`): the evaluation flag on the repository's and the frozen reference's Stage 0 (873,437 matches each); Stage 1's seasons; both era helpers; the pool; the split; the Grand Slam feed tables (2,195 + 3,346 + 2,390 rows, identical); stage 2 does not fit 2027 today (2026 incomplete), as before |
| 20:20–20:40 | The chain's test folders (`tests_year_fix.txt`) | Brief proof | — | daily_update_speed 5, lower_level_evidence 265 (+6 xfail), current_best_model 90, prediction_run 11, match_timing 65, tabpfn_thinking 18, surface_ios 14, surface_elo_pieces 11: all pass. predictability_diagnostic 3 fail and ufc_ideas 1 fail + 2 errors: the same stale-table failures as on 10 Oct before this work. **serve_speed_tabpfn 6 fail, 3 of them mine:** my `adjust.py` loop dropped `ok` and `why`, which the written record still used (`NameError`) |
| 20:45 | `adjust.write_coefficients` fixed: `ok, why` kept for the first season not yet fittable; each later season fitted is recorded as "fitted" (today the record is as before: `season_2027: not yet fittable`) | The bug above | — | serve_speed_tabpfn: 137 pass, 3 fail. The 3 (`test_ssp_latency_availability`, `test_ssp_lat_flip_negates`, `test_tp4_presence_reproduces_n2`) reference no changed function or constant; they compare tables built on 7–8 Oct (`latency/availability.parquet`: 1,746,728 rows) with today's Stage 0 (873,437 matches, 1,746,874 player rows): stale tables, not this fix |
| 20:50 | The 2027 fix reported to the owner; "next is the lean daily build" | — | — | — |
| *11 Oct, about 17:50* | Woken by a background task's notice (a leftover waiter of the test run; no owner message since 19:40 of 10 Oct). Resumed the lean build as announced | — | — | — |
| 17:50–17:58 | `src/eda/prediction_run/assemble.py` written: the 57 inputs straight from Stage 4, Stage B's features, the Elo pieces and the surface IOS features, with the chain's own functions. The replay sandbox `tnr_lyr_rp` was gone (not deleted by this session). In `C:/Users/zerom/tnr_lyr_new` (the current instance's build tree; its chain frame equals `template_2026-10-10/model_frame_chain.parquet` on all 67,226 rows): **the repository's `src` copied in (robocopy)**, then the assembler run against the chain frame | Prove the assembler before making the builders lean | — | after one fix (the IOS names were looked up in Stage B's table): **all 67,226 matches × 57 inputs equal bit for bit, in 11 s** (one column-selection bug fixed first) |
| 17:58–18:05 | Found while reading readers of Stage 1's summary: **`src/eda/daily_prediction/`**, another session's daily prediction script (session `d2d2331e…`; files from 10 Oct 20:28 to 11 Oct 17:56; report `docs/studies/daily_prediction/README.md`: "A day is now about 5.5 minutes with a warm disk cache", replay-proven, with saved states, the price grid, the fit and the forecasts). Its log quotes the owner's instruction not to edit "the builders the daily_update_speed session is changing". **The lean build stopped here**: it duplicates that work | Avoid duplicate and conflicting work | — | — |
| 18:05 | Effect of the robocopy on that work checked (observed): the daily script takes `tnr_lyr_new` as its default base tree (`dp_common.BASE_TREE`) and imports the decided builders from a tree when it makes a checkpoint; its checkpoint (`data/studies/daily_prediction/state/template_2026-10-10/`, 11 Oct 11:13) records only its own scripts' hashes. The builder files the copy replaced in the tree differ from the instance's build code only by edits shown not to move a value: that session's Stage 0 speed-up (byte-identical, its own proof) and this session's 2027 fix (`year_fix_checks.json`); also yesterday's level-layer tooling (`additions.py`, `history.py`, `layer_config.py`, `run_chain.py`). The existing checkpoint is untouched; a new checkpoint made from that tree would import the new code. My 2027 edits are all still in the repository's files (checked after that session's edits to `stage0_build.py`). The daily script's own modules hold no 2026 limit except test defaults | Report to the owner and that session | — | Which listed session is `d2d2331e…` could not be told from the session list: put to the owner |
| *12 Oct, 09:00* | Owner, verbatim: "So do we have two redundant prediction pipelines now? [a quoted line] What is the state of our prediction pipeline that is fed into the master script ipynb? If I query an LLM about the pipeline could it potentially confuse how do to so because of two branches that are similar?" Read: `scripts/master_pipeline.ipynb` (calls `src/pipeline/`, whose `predict_day` runs `daily_prediction/dp.py run_day`), the master-pipeline and daily-prediction reports, `CLAUDE.md` and `docs/pipeline.md` (neither named the notebook or the engine; `CLAUDE.md`'s "Prediction runs" described the 2-hour path), `odds_sources/common.py` (`FRAME_SEASONS`, `OT_SEASONS` end in 2026: a limit the 2027 fix missed, flagged by the notebook session). Answered: one working pipeline; the duplicate was this session's unused assembler; the confusion risk is real, mostly from the instructions | — | — | — |
| 09:10 | Owner, verbatim: "My recommendation: 1. Add a short section to CLAUDE.md: daily predictions run only from the notebook, plus a few lines of the map above saying what each folder is. 2. Put the same pointer in docs/pipeline.md. 3. Delete my unused assemble.py. Fix this. Execute as you suggested". Done: `CLAUDE.md` gains "Daily predictions: the master notebook (since 11 Oct 2026)" (the pointer, the six-row map, "do not build a second prediction path") and a lead line in "Prediction runs" (the rules hold; the commands are the reference path); `docs/pipeline.md` gains "Daily predictions (since 11 Oct 2026)" with the same map, and its "reserved homes" sentence now excepts the notebook; `src/eda/prediction_run/assemble.py` deleted, with the identical copy this session had put in `C:/Users/zerom/tnr_lyr_new/src/` (no import of it anywhere; no bytecode left). The odds-source limit not changed (not in the owner's list) | The owner's instruction | — | — |
| 09:20 | Owner, verbatim: "Yes in 2027 I don't want to fall back to using average odds [quoting my offer] Fix it" | — | — | — |
| 09:20–09:35 | The odds input's path read (observed): `odds_input.py --apply` builds `odds_sources/table.py`'s per-source table on the instance's own frame and Stage 1, then takes Pinnacle's close, BetOnline's close (OddsTrader book 8), else the average. BetOnline's line reaches a match only through `table.link()`, which loads tennis-data for `OT_SEASONS` (2018–2026); the extra books load `FRAME_SEASONS` (2013–2026). No season limit in `sharp_benchmark.build.link`, `pools.reconciled`, `quality.drop_late`, `construct`; the notebook's finishing step runs `--link`, the every-book pull and `--apply`; the odds refresh takes tennis-data's years and OddsTrader's months from the date | Find every limit on the path | — | the two lists are the only limits |
| 09:35 | `odds_sources/common.py`: `TD` (the loader's root, checked equal to `sharp_benchmark.build.TD`) and `td_seasons(first)`: the seasons staged on disk from `first` on; `FRAME_SEASONS = td_seasons(2013)`, `OT_SEASONS = td_seasons(2018)`; docstrings of `common.py` and `table.py` say "on" instead of "-2026". A test (`test_the_odds_sources_take_every_staged_season_with_no_last_one`): the lists today equal the old ones; a staged 2027 file is taken; a non-season file is not | The fix | — | today's lists: (2013 … 2026) and (2018 … 2026), **equal to the old tuples**, so the loader, the link and the table are unchanged; tests: daily_update_speed 6, odds_sources 9, `test_odds_input.py` and `test/master_pipeline` 32, all pass |
| 09:40 | `scripts/master_pipeline.ipynb`, cell 29 (the season-rollover note): the sentence saying the odds sources stop at 2026 replaced by what holds now (one exact string replacement; the notebook still loads, 32 cells) | The note would mislead | — | — |

## 5. Sources

None outside the repository: the project's code, its build logs and records, and the current instance's fits.

## 6. Judgment calls

1. **Scope the code before promising a time.** The four subagents read code only (no builder run), in parallel, with
   identical common briefs; the two claims that decide the most (the IOS inputs' source; the calendar cliff) were
   re-checked by me.
2. **The correctness bar is kept** (the 8 Oct decision: live inputs equal the training inputs). Faster paths are judged
   by the replay, bit for bit, or at a measured solver tolerance for joint solves.
3. **The cached pricing mode is set aside** until its 0.18 difference is explained; the price grid uses the decided
   inference path.
4. **The owner's decision on past revisions** (README) is put with a recommendation, not taken: it changes what "equal
   to a full rebuild" means for the daily path.

## 7. Claims and their evidence (this phase)

| Claim | Evidence | Status |
|---|---|---|
| Step minutes | `replay_2026-10-10_layer/build.out`, `build_resumed.out` | observed |
| 7 computations reach the 57 inputs; the rest reach none | subagent reports (`scoping.md`) | taken as reported; the IOS source re-checked |
| Lean build about 10 min; about 2 min with state | step times plus the subagents' extrapolations | estimate, not measured |
| Pricing: about 41 s per seed per call, any number of matches; the grid in 57 s; within 0.0008 | `bet_time_pricing.json`, `bet_time_pricing_grid_plain.json` | observed (one seed) |
| The cached mode differs by up to 0.179 | `bet_time_pricing.json` | observed; cause unknown |
| The 2027 cliff | the code lines cited at 18:52 | observed |

## 8. Weak points

* The subagents' reading is not a run: a step judged "reaches none" could still feed an input through a path they
  missed. The lean build's replay comparison will catch it (an input would differ).
* The time estimates for the lean steps (Stage B about 5 min, the surface IOS about 5 min wall) are extrapolations.
* The frequency of past-row revisions (which sets the cost of option (a)) is unknown.
* **What a re-design would do:** profile one lean build end to end before estimating; measure the cold one-day IOS
  solve against the warm chain; count a month of daily revisions before choosing (a) or (b).

## 9. Reviewer checklist

* [ ] Each "skip" in `scoping.md` against the code paths it cites.
* [ ] `bet_time_pricing.py` and `--grid-plain` re-run: the timings and differences above.

## 10. Reproduction

```
./python_tabpfn_local.sh src/eda/daily_update_speed/bet_time_pricing.py
./python_tabpfn_local.sh src/eda/daily_update_speed/bet_time_pricing.py --grid-plain
```
