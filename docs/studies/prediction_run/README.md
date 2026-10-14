# The prediction run: box scores first, live inputs from the training code

9 October 2026 · Written for the owner · The build of a decision ([prediction runs](../../decisions/2026-10-08-prediction-run-box-scores.md), 8 Oct 2026) and its checks. Research code, not an approved production system.

**The owner's request.** "When we are working with live data on the prediction pipeline, we need a better pipeline. 'Make live inputs match what the model was trained on. Every prediction run should refresh box scores first: without the same event's earlier rounds, the 2-week profile loses a third to a half of its gain over Elo.'" The owner chose steps 1–4, fills for live use only, and the history-check change (the decision lists the options put to them).

## The answer in short

* **Every prediction run now refreshes box scores first, then builds the upcoming matches' inputs with the training code** (`src/eda/prediction_run/`):
  1. `run.py --refresh --matchups <csv>`:
     * downloads Tennis My Life (TML);
     * lists the matches with a result but no box score;
     * fills those after the freeze from the WTA API (live only);
     * writes the upcoming matches as live rows.
  2. `run.py --setup`, `run.py --build <folder>`: in a sandbox, Stage 0 takes each live row like any TML row, and the unchanged 58-input chain builds its inputs. About 2 hours.
  3. **The gate** marks a match "do not bet" when an earlier match of either player, at the event or in the last 14 days, lacks a box score.
* **The proof: replayed as live rows, past matches get exactly the inputs the model was trained on.** All 23 round-of-16 matches of 15 July 2026 (5 events, both tours) do:
  * 36 inputs are bitwise identical;
  * the 22 IOS inputs agree to within 1.6 × 10⁻¹⁵;
  * that includes the 10 matches whose placeholder result reversed the real one.
* **The one place live dating can differ is the window, and a day's error costs little.**
  * ATP matches dated a day early: only the IOS inputs moved, by a median 0.002 and at most 0.086 standard deviations.
  * The window now follows the last 60 days' dating: 0 days for both tours since July 2026.
* **The first live run (9 Oct, WTA Beijing's quarter-finals) shows why the refresh comes first.**
  * In the frozen tables of 8 Oct, all four players' round-of-16 box scores were missing: their latest match, at full weight in the two-week profile.
  * The 05:28 UTC refresh brought them. The gate passes both matches, and their 58 inputs are built.
  * The price is a placeholder: forecasting is not built yet.
* **The WTA fill reproduces TML.** At WTA Beijing the WTA API's box scores equal TML's on all nine counts in 162 of 162 player rows.
* **The history check let the 6 box scores TML completed overnight through.** The old rule would have refused every template build.
* **Not yet** (below):
  * forecasting itself, which needs matchups and bet-time prices linked to the project's ids;
  * ATP and Slam fills;
  * the WTA qualifying and 125 matches TML lacks;
  * the days of the last few days' matches at prediction time.

## Why the box scores come first

* **The claim holds** (Stage B's recency diagnostic, [stageB.md](../ufc_ideas/stageB.md)). Leave out the same event's earlier rounds and the two-week profile's gain over Elo (milli-log-loss, higher is better) falls:
  * men: from 3.19 to 2.09;
  * women: from 3.32 to 1.83.
* **It reaches 41 of the 58 inputs.** All of them read the same event's earlier rounds:
  * the 17 two-week inputs;
  * the serve and return ratings;
  * IOS points;
  * points over 52 weeks;
  * the 21 surface IOS inputs.
* **A missing box score raises no error.** The match is skipped. The decayed average is divided by its weights plus a prior worth 10–20 matches, so it shrinks toward 0.
* **What training saw.** In the frame's seasons 2019–2025, 98.4–99.7% of the same event's earlier-round player-matches had a box score.
* **What a forecast would have read on 8 Oct.**
  * No code forecast an unplayed match.
  * TML (Tennis My Life) has ATP box scores minutes after a match, but the project downloads once a day and rebuilt Stage 0 by hand.
  * TML listed WTA Beijing's newest results without box scores for over 24 hours. By the 05:28 UTC download of 9 Oct they were all there: a lag of one to two days.

## How a run works

| Step | Command | What it does |
|---|---|---|
| Refresh | `./python.sh src/eda/prediction_run/run.py --refresh --matchups <csv> [--out <folder>]` | Downloads TML (the daily job's command). Builds Stage 0 from it into the run's folder. Lists every completed match of the last four weeks with a result but no box score (`gaps.csv`). Fills those the frozen reference does not hold from the WTA API (`fills.csv`, `overrides.csv`). Writes the upcoming matches' live rows (`live_rows.parquet`, `live_meta.parquet`) |
| Sandbox | `run.py --setup` | A copy of `src/`, `docs/` and `data/studies/` (16.5 GB) with links to `data/dump/` and `data/raw/`, at `PREDICTION_RUN_SANDBOX` (default `C:/Users/zerom/tnr_live`). Marked as the one place Stage 0 accepts live rows |
| Build | `run.py --build <folder>` | In the sandbox, in this order: Stage 0 with the decided overrides, the fills and the live rows; its checks; Stage 1's odds with the live prices; the match timeline with the live days and windows; the leak-proof features; then the model's chain (`run_chain.py`'s lanes, 1 and 2 side by side, then 3). It collects the live matches' frame rows (`live_frame.parquet`), the history check and the gate |
| Gate | (in the build; `run.py --gate <folder>` again) | `gate.csv`: each live match, the earlier matches checked, and "may be bet" or "do not bet: inputs incomplete", with what is missing (`gate_missing.csv`) |
| Clean up | `run.py --cleanup` | Removes the links first, then the sandbox |

* **A live row** is the row TML will publish once the match is played, less what only playing it gives.
  * The result is a placeholder: one fixed player wins 6-4 6-4.
  * There are no games beyond that, no minutes and no box score.
  * Everything else comes from TML: the event's columns, and each player's columns from her or his row at the event.
  * Stage 0 builds it like any TML row (`stage0_build.py --live-rows`), and every builder after it treats it as a played match. A match's own result never reaches its own inputs; the replay below checks that.
* **The price** goes into Stage 1 as tennis-data's margin-free average (`p_avg_a`, the frame's odds input). This is the [bet-timing study](../bet_timing/README.md)'s plug-in: the model is fed the price of the moment.
* **The day** is the UK calendar day of the start, as tennis-data dates a match. It enters as a tennis-data day link, carrying the same venue tag tennis-data's links carry. No other source can have dated a match not yet played, so their links for it are removed.
* **The window.** Dated by one link alone, a match would get a window wider than the frame's matches had. So a live match takes its tour's current window around its day: the median over the dated frame-level matches of the 60 days before it.
  * The dating changed in July 2026, when TDI's point logs began. ATP matches have been dated exactly since then (113 of 116 in September), a day wide before.
  * WTA matches are dated exactly throughout.
* **The gate** holds the training standard. Every completed match before the live one, at the same event or within 14 days, must have a box score. A player who entered through the qualifying must have qualifying matches. Retired matches and walkovers are not required, since no box-score input reads them.
* **Fills** are rebuilt at every run. A match TML has since completed takes TML's numbers, and fills never reach the repository's Stage 0 or a template build.
* **The history check** ([history.py](../../../src/eda/current_best_model/history.py)) lets a reference match possibly played from 5 Oct on, from the reference's feeds, be completed, corrected or dropped. That means its latest possible finish is on or after 5 Oct.

## Checks

### 1. Nothing changes for the builds that take no live rows

* **Stage 0.** Built without live rows into a scratch folder, the tables are byte-identical to the repository's (both SHA-256s equal). The option is refused outside a sandbox or an `--out-dir`.
* **Tests.** 155 tests pass:
  * Stage 0's builder;
  * the coordinated rebuild and the download schedule;
  * the data repairs;
  * the as-of ordering;
  * the history check (16, of which 6 are new);
  * the prediction run (11, offline).

### 2. The history check on the download of 9 Oct

* **The result.** On the Stage 0 the refresh built from TML's download of 05:28 UTC: future 17 and updated 6 (allowed); new past, dropped and revised 0. The template may be built.
* **The 6 updated matches** are WTA Beijing's round of 16 (4) and quarter-finals (2). The reference held them without box scores, and TML published the box scores overnight.
* **The old rule** placed a match by its earliest possible start and counted any change to a reference match as a revision, so it would have refused every template build. Undated matches carry wide windows: Shanghai's main draw opens its window on 3 Oct, so its next rounds would have been called old as well.

### 3. The WTA fill reproduces TML

`./python.sh -m src.eda.prediction_run.fills --events 2026-1020 --out data/studies/prediction_run/fill_check_2026-10-09`

* **What it does.** It runs the fill on matches TML has already scored: the edition's match list, linking by the players' name keys and every set's games, the box score, and the nine counts as Stage 0 reads them.
* **WTA Beijing 2026:**
  * 81 of 81 completed matches were linked and fetched.
  * All nine counts equal TML's in all 162 player rows (aces, double faults, serve points, first serves in, first- and second-serve points won, service games, break points saved and faced).
* *Inferred.* TML takes its WTA box scores from the WTA's own statistics. A fill gives the numbers TML publishes a day or two later, so it costs no parity there. The earlier measurement (95.5% of first serves in, 83.7% of service games) was over 2026 to May.

### 4. The live run of 9 Oct 2026: WTA Beijing's quarter-finals

`run.py --refresh --out data/studies/prediction_run/live_2026-10-09 --matchups .../matchups.csv`, then `--setup` and `--build`. The matchups are the two quarter-finals the WTA's own match list named for 9 Oct, with their start times: Qinwen Zheng v Elina Svitolina (07:00 UTC) and Elise Mertens v Iga Swiatek (11:00 UTC).

* **The refresh** (05:28 UTC).
  * TML brought 17 new matches and WTA Beijing's six missing box scores.
  * The gaps left are all matches the reference holds: 37 Davis Cup rubbers, one team match of the BJK Cup Finals, and one ATP 1000 and one ATP 500 match.
  * No WTA match after the freeze lacked a box score, so nothing was filled.
* **Stage 0** holds both live matches under the expected ids, and they replace nothing.
* **Price, day and window.**
  * Their price is a placeholder (0.5): no bet-time price source is linked yet. It sets only the odds input; the other 57 do not read it.
  * Their day link carries Beijing's "east" tag.
  * Their window is the current norm: 0 days before and after, from 385 ATP and 414 WTA dated matches of the last 60 days.
* **The gate:** both "may be bet". It checked 10 earlier matches for Zheng v Svitolina and 7 for Swiatek v Mertens; none lacks a box score.
* **Why the refresh mattered here.** In the frozen tables of 8 Oct (18:53 UTC), all four players' round-of-16 matches (6–7 Oct) had no box score. That is each player's latest match, at the same event, at full weight in the two-week profile. After the 05:28 download all four have one.

| Player | R64 | R32 | R16, 8 Oct tables | R16, 9 Oct refresh |
|---|---|---|---|---|
| Qinwen Zheng | box | box | **none** | box |
| Elina Svitolina | box | box | **none** | box |
| Elise Mertens | box | box | **none** | box |
| Iga Swiatek | box | box | **none** | box |

* **The build** (`--build`, about 2.7 hours beside the two replays) collected both matches' 58 inputs from the unchanged chain (`live_frame.parquet`).
  * The history check of the sandbox's Stage 0, live rows included, reads: future 19 (the 17 new matches and the 2 live rows) and updated 6 (allowed); nothing refused.
  * Each input is A's value minus B's. Stage 0 orients A by a hash of the match id: here Zheng and Swiatek.

| Input | Zheng v Svitolina | Swiatek v Mertens |
|---|---:|---:|
| `odds_logit` (placeholder price) | 0.000 | 0.000 |
| `elo_overall` | −0.347 | +1.227 |
| `ratings_iid` (serve and return ratings) | −0.559 | +1.684 |
| `ios_points_short` | −0.709 | +1.486 |
| `adjperf_tpw_2w` (two-week total points, opponent-adjusted) | −0.089 | +0.092 |
| `points_52w` | −0.425 | +0.859 |
| `sets_14d` | −0.069 | −0.318 |
| `age` (years) | −8.07 | −5.54 |

* `indoor` is empty, as it is in every WTA row of the frame since 2025 (2,485 rows in 2025, 2,167 in 2026). Stage 0 has Beijing as outdoor. The live row follows the frame; the gap is the frame's.

### 5. The replay: live rows get the training inputs

`replay.py --prepare --dating training`, built in a sandbox and compared with the template's frame of 8 Oct (`replay.py --compare`).

* **The design.** Played round-of-16 matches went in as live rows:
  * each match's own TML row with its outcome removed;
  * a placeholder won by Stage 0's player A (the real result in some matches, the reverse in others);
  * the price and day from the frame's own Stage 1 row;
  * the events' later rounds left out.
* **The first day replayed, 15 July 2026:** 23 matches at Bastad, Gstaad, Umag (ATP), Athens and Iasi (WTA). In 10 of them the placeholder reverses the real result.
  * **36 of the 58 inputs are bitwise identical in every match:** the price, Elo, the serve and return ratings, the two-week profile, the 52-week points, workload, age and context.
  * **The 22 IOS inputs agree to within 1.6 × 10⁻¹⁵** (relative 1.8 × 10⁻¹³): the iterative solver's rounding.
  * So the placeholder result, the missing box score and the placeholder score never reach a match's own inputs. The live row's price, day and venue tag are read as tennis-data's are.
* **Later days moved, and why** (the first build replayed two weeks; it is kept as evidence in `replay_2026-10-09/`).
  * 26 of the 27 matches on later days differ, by small amounts: the serve and return ratings by at most 0.011, the Elo inputs by at most 0.0022, the two-week profile by at most 0.010. The price, points over 52 weeks, workload, age, context and the surface-season pair are equal in all 50.
  * Matches that were never replayed differ the same way after 16 July (all 389 of 17 Jul – 7 Aug, all 688 from 8 Aug). Before 15 July none differs in ratings or form.
  * The causes are the replay's own changes spreading:
    * a match without its box score leaves the jointly solved IOS ratings of every later day;
    * a dropped match changes its players' ratings, which reach their later opponents;
    * the timeline's class windows pool every event's dated matches.
  * The replay now takes one day only (`--week`), whose matches nothing it changes can reach.
* **One data change found on the way.** SofaScore's editions were re-staged at 19:41 UTC on 8 Oct, 46 minutes after the template build had linked them.
  * Re-linked, they tag 7 historical matches (Madrid and Rome 2026, Hong Kong 2025) as finishing a day later (`last_point_day+1`), from SofaScore's later edit times.
  * That moves 37 IOS rows of ATP Madrid and Rome 2026 by a median 0.0002 and at most 0.028 standard deviations.
  * The next template build will read the same. It is a source change, not a live-path one.

### 6. The replay dated as live: what the window costs

The same matches, `--dating live`: every source's day link removed, as for a match not yet played, and the window set by the tour's norm. For this replay the norm was the year before 15 July's median, which was 1 day for ATP and 0 for WTA.

* **WTA (8 first-day matches).** The live window equals the frame's, and all 58 inputs are equal.
* **ATP (15 first-day matches).** The year's median started their windows a day before the frame's: once played, TDI's point logs dated them exactly.
  * Only the 22 IOS inputs moved, by a median 0.002 and at most 0.086 standard deviations.
  * The other 36 inputs are equal.
* **So the window is the one place where live dating can differ from training,** and a day's error costs little.
* **The rule now uses the last 60 days**, because the norm moved with what is collected. Since July 2026 both tours are dated exactly (ATP 113 of 116 matches in September). The live run of 9 Oct measured 0 days for both tours, on 385 ATP and 414 WTA matches.
* **A remaining risk.** A day's error comes back only if collection changes. For instance, if TDI stopped, ATP matches played from then on would be dated a day wide in training.

## Limits and next steps (suggestions, not decisions)

1. **Forecasting (step 5 of the decision) is not built.** It needs, per upcoming match, a matchup and a bet-time price linked to the project's player ids.
   * For matchups, the WTA's own match lists name upcoming matches with their start times, as used here. For ATP matches no draw source is held. Polymarket's open markets and OddsTrader's provisional lines name both.
   * Once those exist, the live rows are season-Y rows of the sandbox's frame. The template's fit for season Y (`model_rebuild/fits.py`) predicts them with the season, and stage 2 adds the live speed form (`serve_speed_tabpfn/live/form.py`).
   * **Since 9 Oct 2026, that fit also trains on season Y's matches.** It takes every match from the reference's feeds whose result counts by the run's cut-off under the match clock (lf + 1 ≤ the cut-off).
     * Fills stay live-only.
     * Before first use, a replay checks that the walk-forward calibration still fits ([current-best-model decision](../../decisions/2026-10-08-current-best-model.md), amendment of 9 Oct; [adoption by kind of change](../../decisions/2026-10-09-adoption-by-change-class.md), point 7).
2. **ATP fills.**
   * The ATP Stats Centre's keystats hold the full box score, but the daily speed job stages only speeds and first serves.
   * TML usually has ATP box scores within minutes. The ATP lag was the project's own (one download a day, Stage 0 rebuilt by hand), and a run now removes it.
3. **The Slams.** Their feeds have no live mode yet, which the download-cadence decision ties to the first Slam the project bets on. At the Slams, TML's men's first serves are wrong (decision of 6 Oct), so a live run there needs the feeds as the decided overrides do.
4. **WTA qualifying and WTA 125s are missing as whole matches.**
   * TML has lacked them since June 2026: these are matches missing, not box scores missing. The frame's 2026 WTA rows were built the same way, so live and training agree with each other, but not with the frame's earlier seasons.
   * The gate fails a player who came through qualifying with no qualifying match.
   * Filling them is new data: a candidate under the reference rule, the owner's call.
5. **Recent matches' days.**
   * At prediction time, some of the last days' matches are not yet dated by any source: tennis-data lags, and TDI runs on Mondays. The timeline gives them windows, so their results reach other players' IOS ratings later than they did in the frame. A player's own matches always count.
   * A replay "as known at the time" needs the data versions of the data-continuity study (section 4.7), which are not built.
6. **Run time.**
   * A build takes about 2 hours alone: about 14 minutes from Stage 0 to the leak-proof features, then the chain's lane 1, about 100 minutes, with lane 2 beside it. Three builds side by side took about 3 hours each.
   * Lane 1 runs steps no input reads (Stage A, Stage C and the rundowns). A live lane without them would save about 35 minutes, after checking that the frame builders do not read them.
   * The price can change without a rebuild: only the odds input moves, so a new price needs only a new fit.
7. **Disk.** A sandbox holds 16.5 GB. `run.py --cleanup` deletes it, links first.

## Files

| What | Where |
|---|---|
| The decision | [docs/decisions/2026-10-08-prediction-run-box-scores.md](../../decisions/2026-10-08-prediction-run-box-scores.md) |
| The run: refresh, build, gate, clean-up | `src/eda/prediction_run/run.py` |
| The sandbox | `src/eda/prediction_run/sandbox.py` |
| Live rows from matchups and from played matches | `src/eda/prediction_run/live_rows.py` |
| The steps between the builders (check, odds, remap, links, window) | `src/eda/prediction_run/inject.py` |
| Gaps, WTA fills and their agreement check (`-m src.eda.prediction_run.fills`) | `src/eda/prediction_run/fills.py` |
| The gate | `src/eda/prediction_run/gate.py` |
| The replay | `src/eda/prediction_run/replay.py` |
| Stage 0's live rows (`--live-rows`) | `src/eda/predictability_diagnostic/stage0_build.py` (`add_live_rows`, `drop_replaced`) |
| The history check's `updated` class | `src/eda/current_best_model/history.py` |
| Tests | `test/prediction_run/` (11 offline tests), `test/current_best_model/test_history.py` (16) |
| Records | `data/studies/prediction_run/`: `replay_2026-10-09/`, `replay_2026-10-09_live/`, `live_2026-10-09/`, `fill_check_2026-10-09/` |
