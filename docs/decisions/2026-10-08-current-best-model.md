# The current best model is a template, built on the day's tables when it is needed

**Stated by the owner on 8 October 2026.** This came after the [comparison of the model rebuilt on the corrected tables](../studies/model_rebuild/README.md), where the rebuilt model tied the earlier one. The owner's words:

> "yes the current best model is the rebuilt model but I dont need it stored and trained on disk, its the template that matters so when I mention in a new prompt to use the current best model it knows what configuration im referring to. If it isnt built on disk, it would need to build it then, we dont need to do it now"

Recorded the same day.

**Amended by the owner on 8 October 2026,** on hearing that new ITF box scores would shift the scale of the IOS inputs (finding #6 of the [input-data audit](../studies/input_data_audit/README.md)):

> "I want to freeze the template of current model and its data locations as comparisons so the new data thats coming, if it harms results we will want to make some modifications, Either to ignore data, lower its weight, or find a way to mathematically change and integrate it so its useful. I dont want to lose sight of the current model"

* **The frozen reference.** The build of 8 Oct (`data/studies/model_rebuild/`) and the tables it was built on are copied, hashed and made read-only in [`data/studies/current_best_model/reference_2026-10-08/`](../../data/studies/current_best_model/reference_2026-10-08/README.md).
  * It holds the frame, its 32 fits, the speed column, Stage 0 and the odds, the code and the TabPFN checkpoint.
  * The previous model is frozen beside it.
  * Point 2 below still holds for live use. The reference is a yardstick, not the live model.
* **New data is compared with it before it changes the current best model.** That covers a new source wired into Stage 0 (the ITF downloads first), a new or changed input, and any rebuild.
  * The comparison is `src/eda/current_best_model/compare.py`.
  * First the inputs, with no result read. It flags any input that moves unevenly across seasons, as finding #6 did.
  * Then both stages against the reference, on 2020–2024.
* **If it harms,** the new data is ignored, down-weighted or transformed, and compared again. Accepting a candidate stays the owner's call.
* **The training data, clarified by the owner the same day:**

  > "I just want the same data as before for training + training updates from future dates frozen. But if we are downloading new LOWER LEVEL data, challenger +ITF it doesnt get auto included in the model. I want a way to test if this lower level skill data is harming our model (though the data is prior to the current date)."

  * **The model trains on the reference's matches plus the matches played since,** from the feeds that were feeding it (today Tennis My Life: the main tour, its qualifying, Challenger main draws, team events).
  * **Anything else that changes the history is a candidate,** never included by itself. That covers new Challenger or ITF matches or box scores of past dates, a new source, and a dropped or revised past match. *Narrowed on 9 Oct 2026 to lower-level data (the amendment below).*
  * **Enforced** by `src/eda/current_best_model/history.py`. It compares any Stage 0 with the reference's, match by match. `run_chain.py --setup` refuses a template build when the history differs. *Since 9 Oct 2026, only when the lower-level history differs.*
  * **Refined by the owner the same day** ([prediction-run decision](2026-10-08-prediction-run-box-scores.md)): a reference match possibly played from 5 Oct on, from the feeds that fed the reference, may be completed, corrected or dropped like a new match, so that box scores TML publishes late do not refuse every build.
  * **Testing new data:** a `--setup --candidate` build with the new data, compared with `compare.py`.
  * **Narrowed by the owner on 9 October 2026 (evening): the freeze is about lower-level data.** The owner's words:

    > "the oct 8 freeze I suggested was more about the data from the challenger series/ITF tour and I think the agent I was talking to read into it deeper than I was intending"

    Then, on Claude's recommendation: "Ok, do this".
    * **Lower-level data stays a tested candidate before it enters the model.** That covers new, revised or dropped past matches or box scores of qualifying (tour and Slam), Challengers and their qualifying, ITF and its qualifying, and any level the check does not know. Since 9 Oct it is judged as a harm check ([adoption by kind of change](2026-10-09-adoption-by-change-class.md)).
    * **Main-tour data is a repair, decided on the data evidence.** That covers corrections and new official sources for the main draws of the Slams, the Finals, the 1000s, 500s and 250s, and team events. `history.py` still lists every such difference, so nothing changes silently, but it no longer refuses a template build.
    * **The 8 Oct model stays saved as a comparison point** (the frozen reference).
    * **Qualifying is gated with the lower levels.** The owner named "challenger + ITF". Qualifying was kept under the gate on Claude's recommendation: its box scores inflate players' form numbers as Challengers' do (77–83% of the level boost kept; [lower-level evidence](../studies/lower_level_evidence/README.md) § 1.2). The owner may take it out.
    * **In the code:** `history.py` keeps its all-level counts (new past, dropped, revised) and splits each into `gated` (lower-level) and `allowed_main_tour`. `template_ok` reads only the gated part. Tests: `test/current_best_model/test_history.py`.
* **One gap, measured: no model input is affected.** A TDI refresh rewrote 18 timeline files in place an hour after the build had read them, and their build-time versions are lost.
  * **What the later versions add:** 268 TDI date links, for 206 Challenger and 62 ATP 500 matches (Beijing and Tokyo), all played 29 Sep – 8 Oct 2026. They change the days of 238 matches.
  * **Why the model cannot see it:** the frame's last matches (Chengdu and Hangzhou) finish by 29 Sep. Under the match clock a result counts only from the day after it finishes, so these days cannot reach a model input.
  * **Checked:** the one input taken straight from the leak-proof table (`ios_points_short`) is identical on all 67,226 frame matches.
* **The ATP Stats Centre backfill, accepted by the owner the same day (evening).** On the ATP's own files of 2018 to Oct 2021, decrypted at the owner's request, the owner said: "Integrate it as well into our pipeline like all the analogous data to this data unless there's a clear bug you identify." Recorded by the session that integrated them ([study](../studies/infosys_atp_backfill/README.md)).
  * **No bug was found.** The files equal the Hugging Face handoff's decrypted copy on every shared value, and name the same players and winners as ManTennisData.
  * **Compared with the reference first** (`compare.py`, only stage 2's speed column changed, 2020–2024; + = with the backfill better): both tours +0.014 [−0.073, +0.102], men +0.027 [−0.073, +0.128]: ties. No stage-1 input changed.
  * **So stage 2's speed history now holds them:** the corrected history plus 225 usable player-matches of 2018 and 2021 (`live/speed_panel_backfilled.parquet`, which `live_panel.frozen_panel()` reads while its record matches the corrected copy). No live speed form changes. The 2027 coefficient moves from b̃ 0.0432 to 0.0444.
  * **To undo:** without that file the history is the corrected copy again.
* **The odds input is "Pinnacle first", changed by the owner on 9 October 2026** ([decision](2026-10-09-pinnacle-first-odds-input.md), after the [odds-sources study](../studies/odds_sources/README.md)).
  * **In training:** Pinnacle's close, margin removed:
    * tennis-data's to July 2025, cross-checked against OddsTrader's timed copy;
    * then OddsTrader's, to 7 Sep 2025;
    * then BetOnline's closing line;
    * the books' average only where neither book prices a match.
  * **Live, at every venue and bet time:** Pinnacle's current line with the margin removed, BetOnline's while Pinnacle has none.
  * **Note: Pinnacle's closes are missing from August 2025. If they are obtained, the model is retrained on Pinnacle's closes throughout,** replacing the BetOnline stand-ins.
  * The frozen reference keeps the books' average: it stays the yardstick.
* **`ios_points_short` is dropped, by the owner on 9 October 2026: "Drop ios_points_short".** The model has 57 inputs.
  * **The evidence:** the [lean review](../studies/lean_review/README.md#results-9-oct-2026)'s T2. That is the Pinnacle-first instance with and without the input; 2020–2024; both stages; seeds 0–3 paired; + = without it better:
    * at Pinnacle's opening line: −0.03 [−0.11, +0.06], unresolved, P(better) 0.25;
    * at the close: −0.00 [−0.09, +0.08], P(better) 0.47.
    * Nothing measurable either way. The review's rule, fixed before any fit, proposed removing it at its threshold.
  * **Without it, the long-memory IOS profile stays per surface** (the review's T3): per surface against pooled reads +0.055 [−0.054, +0.163] at the opening line, P(better) 0.84.
  * **How it is done.**
    * The chain still builds all 58 columns, so its checks of each input against its source are unchanged.
    * `src/eda/current_best_model/template_inputs.py --apply <folder>` writes the 57-input list (§ "Building it").
    * The fit runner (`model_rebuild/fits.py`) accepts the chain's list or the template's, and records which.
    * A prediction run applies the template's list when it collects the live rows.
  * **Earlier builds keep their lists.** The frozen reference and the Pinnacle-first instance of 9 Oct are 58-input models, as built. The reference stays the yardstick.
  * **To undo:** skip the step, or remove the input from `DROPPED` in `template_inputs.py`.
* **The indoor input covers every match, at the owner's request on 9 October 2026** ([decision](2026-10-09-indoor-input.md), [study](../studies/indoor_fill/README.md)).
  * **What changes.** It was Stage 0's flag for the men only; every women's match, and the men's 2026 US Open, had none. It is now `src/eda/indoor_fill/status.py`'s rule, applied by `tabpfn_thinking/build_frame.py` in every build:
    * men: Stage 0's flag, as before; then tennis-data's Court;
    * women: the WTA's calendar, then tennis-data's Court.
  * **One choice is Claude's recommendation, for the owner to confirm:** the women's value comes from the WTA's calendar first. tennis-data's Court is wrong on 16 women's events where the WTA's calendar is right.
  * **The harm check** (2020–2024, both stages, + = the fill better): at Pinnacle's opening line +0.007 [−0.014, +0.029], unresolved, P(better) 0.75; at the close −0.002 [−0.016, +0.013]. No edge claimed.
  * **Live:** prediction runs fetch the WTA's calendar again, and the gate marks "do not bet" any live match whose indoor input is unknown.
  * **Earlier builds keep their input.** The frozen reference, the Pinnacle-first instance and the lean review's arms have women's `indoor` missing.
  * **To undo:** `build_frame.py --indoor-men-only`.
* **The recipe builds with the level layer for men, decided by the owner on 10 October 2026** ([decision](2026-10-10-level-evidence-layer.md), from the [level-evidence study](../studies/lower_level_evidence/system/README.md); [record](../studies/level_layer_adoption/README.md)).
  * **What changes.** For men, every lower-level observation (tour and Slam qualifying, Challenger main draw and qualifying) enters the inputs in main-tour terms: translated by the opponent's strength gap and a level offset, weighted by an exchange rate capped at 1. ITF and ITF-qualifying box scores are excluded until P7. Women, age, workload, context, odds and stage 2 are untouched.
  * **The config:** `data/studies/current_best_model/level_layer/official.json` (sha256 `be66df29…`): the study's SYS, every setting as tested, `ios_points_short` off, seasons after the last fitted one reading its parameters. Each build resolves it with the opponent strength on its own Stage 0 (`run_chain.py --prepare-layer`) and runs every lane with `--layer`; prediction runs do the same on their own Stage 0.
  * **Verified on the reference's tables** (today's equal them): with the layer off the builders reproduce the current template exactly; with it on they reproduce the study's SYS inputs bit for bit; women and the untouched inputs unchanged; no leak.
  * **The harm check:** men, both stages, 2020–2024: −0.014 [−0.162, +0.134] mLL, unresolved, P(better) 0.42 (+ = with the layer better). No harm under the owner's rule; no edge credit.
  * **The instance:** `data/studies/current_best_model/template_2026-10-10/`: the template with the layer and the accepted men's 2026 Challenger data (next bullet) on the tables of 8 Oct; fits for 2019–2026, seeds 0–15. The layer alone on the same tables, the harm check's arm: `level_layer_2026-10-10/` (seeds 0–3).
  * **Each season** the parameters are refitted walk-forward into a new folder (`relationship.py --method F4`), the config re-issued with the new path and hash, and the identity and strength checks re-run (the decision's "Maintenance").
  * **To undo:** build without `--layer` (and with `LLE_LAYER` unset); the builders then build the template of 9 Oct.
* **The men's 2026 Challenger and Challenger-qualifying matches enter the training history, at the owner's request of 10 October 2026** ([decision](2026-10-10-men-2026-challenger-data.md)): "Also Wire in the 2026 challenger data we already have to the model, including the 2026 men's qualifying box scores sitting on disk. That fills a live gap."
  * **What:** 1,735 men's matches of 2026 Stage 0 lacked (Challenger qualifying after 1 June, a few Challenger main-draw matches) and one box score, from role F's checked additions, entering through the level layer. Adopted under the owner's chosen rule, unless the harm check failed: men, both stages, 2026: +0.058 [−0.048, +0.164] mLL, unresolved, P(better) 0.89.
  * **How:** a package (`data/studies/current_best_model/accepted_additions/`, listed in `accepted.json`) that every build merges into its own tables: `run_chain.py --additions` after `--setup`, then lane 0, then the layer; prediction runs merge it after Stage 0. The repository's live tables are not changed; `history.py` counts the package as "accepted".
  * **Not a live feed:** Challenger qualifying after 5 Oct 2026 still has none.
* **Live fits grow within the season, decided by the owner on 9 October 2026** ([adoption by kind of change](2026-10-09-adoption-by-change-class.md), point 7: "I accept your adoptation logic, implement it").
  * **What changes.** Once the forecast step is built, a prediction run's fit for season Y trains on 2013 .. Y − 1, plus every season-Y match from the reference's feeds whose result counts by the run's cut-off under the match clock (lf + 1 ≤ the cut-off).
  * **Why.** It is accretion, more of the same data, decided once as a policy. The training-window study's learning curve puts the gain at about 0.001–0.01 mLL by late season. That is too small for any comparison to see, but its sign is known and it costs minutes of GPU.
  * **Unchanged:**
    * backtests and the frozen reference keep the annual protocol (the "Fit" bullet below);
    * live fills never become training rows (the [prediction-run decision](2026-10-08-prediction-run-box-scores.md)).
  * **The guard, before first live use:** a replay showing that the walk-forward calibration still fits the in-season fit's forecasts.
  * **Nothing is built yet:** the forecast step does not exist.

## Decision

1. **"The current best model" means the configuration below,** built on the tables of the day: the rebuilt model of 8 Oct 2026, as a recipe.
2. **It is not kept as a trained model.** A task that needs it uses an instance built on the current tables, if one is on disk, or builds one (§ "Building it").
3. **What it replaces.** The 7 Oct definition's frozen instance is now **the previous model**: `data/studies/surface_rating_race/model/model_frame.parquet`, built on the tables of 30 Sep, and its fits. It is kept as the evidence of the studies that used it. Its two stages and their settings carry over unchanged; only the data under them changes.

## The configuration

**Stage 1, the base forecast: the local, non-thinking TabPFN-3.5 on 57 inputs** (58 until `ios_points_short` was dropped on 9 Oct 2026; amendment above).
* **Data.** Stage 0 and Stage 1 as their builders write them by default, with the match timeline's leak-proof clock. That is:
  * Sackmann's files, then Tennis My Life;
  * the [Slam box-score overrides](2026-10-06-slam-box-scores.md);
  * the [corrections of 8 Oct](2026-10-08-corrupt-data-fixes.md): box scores, player ids, ages and odds rows.
* **Matches.** Main-tour matches with closing odds from 2013: Grand Slams, Tour Finals, 1000s, 500s and 250s; completed or retired; in a supported pre-match format. Side A is fixed by a hash of the match id.
* **Inputs.** 57, in the order of `model_inputs.json` once `template_inputs.py --apply` has run:
  * the closing odds' log-odds, **"Pinnacle first" since 9 Oct 2026** ([decision](2026-10-09-pinnacle-first-odds-input.md); `src/eda/current_best_model/odds_input.py`):
    * Pinnacle's close: tennis-data's to July 2025, cross-checked against OddsTrader's timed copy, then OddsTrader's to 7 Sep 2025;
    * then BetOnline's closing line;
    * the books' average only where neither book prices a match.

    Live: Pinnacle's current line, margin removed, at every venue. **If the missing Pinnacle closes (August 2025 on) are obtained, retrain on Pinnacle throughout;**
  * 29 of the leak-proof refit's 30 pre-match inputs:
    * two-week form (12);
    * two-week defence form (4);
    * opponent-adjusted points won over two weeks;
    * ~~IOS points~~ (`ios_points_short`, dropped on 9 Oct 2026; the chain still builds the column);
    * points over 52 weeks;
    * serve-and-return ratings;
    * games-weighted Elo;
    * sets in the last 14 days;
    * age and age squared;
    * the context: tour, surface, level, indoor, best of, round. Indoor covers both tours since 9 Oct 2026 (`src/eda/indoor_fill/status.py`; amendment above);
  * the [surface IOS profile](2026-10-06-surface-ios-profile.md)'s 21: 14 ratings and 7 matchup products;
  * the [offset Elo](2026-10-06-offset-elo.md)'s 6: overall Elo, the surface offset, and for each player the matches on the surface this season and the days since the last one.
  * **Since 10 Oct 2026, for men, the box-score and Elo inputs read lower-level matches through the [level layer](2026-10-10-level-evidence-layer.md)** (translated, weighted, ITF box scores out); `data/studies/current_best_model/level_layer/official.json`.
* **Fit.**
  * Season Y is trained on the frame's matches of 2013 .. Y − 1. Live fits will also take season Y's matches counted by the run's cut-off, once the forecast step is built (amendment of 9 Oct 2026 above).
  * 8 estimators, softmax temperature 0.9, pretraining limits ignored.
  * Each match is predicted as stored and with A and B swapped, and the two are symmetrised.
  * The forecast η averages seeds 0–15. The calibration and stage 2's fit use seeds 0–3.

**Stage 2, the walk-forward serve-speed adjustment** ([decision](2026-10-07-speed-nudge.md), as amended on 8 Oct): logit q = s_tour,Y · η + b̃_Y · `spd_L`.
* **`spd_L`** = clip((f̂₂₈,A − f̂₂₈,B) / 1.9496 km/h, −4, 4): the two men's 28-day first-serve-speed form. It is 0 for women.
* **The speeds** are the live speed feed's history plus its new daily rows. The history is the study's panel without the 130 impossible records (`data/studies/serve_speed_tabpfn/live/speed_panel_frozen_corrected.parquet`), plus the ATP's decrypted files of 2018 to Oct 2021 since the evening of 8 Oct (`…/live/speed_panel_backfilled.parquet`; amendment above). `live_panel.frozen_panel()` returns it.
* **The coefficients.**
  * s_atp, s_wta and b are fitted by maximum likelihood on 2019 .. Y − 1, from this model's own seeds 0–3 forecasts, with debut seasons left out.
  * b̃ = b · τ² / (τ² + SE²), with τ = 0.05.
  * They are refitted each season, on the speed history that matches the live feed: `spd_L_B` for the weekly feed, `spd_L_D` once the daily collector runs.
* **Every match is in mode L.** The code is `src/eda/serve_speed_tabpfn/adaptive/adjust.py`; the coefficient fit is `serve_speed_tabpfn/score.nudge_parameters`, reproduced in `src/eda/model_rebuild/compare.py` (`walk_forward`).

**Comparisons.** New features and studies are compared against both stages, never the TabPFN fit alone.

## Building it

1. **Bring Stage 0, Stage 1's odds and the timeline up to date** with `./python.sh src/eda/data_continuity/rebuild_stage0.py`. First ask the sessions that read those tables; the script keeps every file it replaces.
2. **Build the frame in a sandbox copy of the repository**, which leaves every study's folder as it is. Since 10 Oct 2026 with the level layer (`--prepare-layer`, then `--layer` on every lane; amendment above):

   Since 10 Oct 2026 the accepted lower-level packages are merged first (`--additions`, then lane 0, whose timeline step is skipped).

   ```
   ./python.sh src/eda/model_rebuild/run_chain.py --setup
   ./python.sh src/eda/model_rebuild/run_chain.py --additions --out data/studies/current_best_model/<date>
   ./python.sh src/eda/model_rebuild/run_chain.py --lane 0 --out data/studies/current_best_model/<date>
   ./python.sh src/eda/model_rebuild/run_chain.py --prepare-layer --out data/studies/current_best_model/<date>
   ./python.sh src/eda/model_rebuild/run_chain.py --lane 1 --layer --out data/studies/current_best_model/<date>   # about 1.5-2.5 h
   ./python.sh src/eda/model_rebuild/run_chain.py --lane 2 --layer --out data/studies/current_best_model/<date>   # beside lane 1
   ./python.sh src/eda/model_rebuild/run_chain.py --lane 3 --layer --out data/studies/current_best_model/<date>
   ./python.sh src/eda/model_rebuild/run_chain.py --collect --out data/studies/current_best_model/<date>
   ./python.sh src/eda/model_rebuild/run_chain.py --cleanup
   ```

   `data/studies/level_layer_adoption/build_template.sh <sandbox> <out> 1 accepted` runs the same steps.

   The model frame's own checks must pass. They tie every input to its source.
   * `--setup` first checks the training history against the frozen reference (the amendment's rule) and refuses if it differs.
   * A build that tests new data adds `--candidate`, writes to its own `--out`, and is compared with the reference before anything is accepted.

   **Then the odds input** (since 9 Oct 2026). The chain builds the books' average; this step replaces it with "Pinnacle first" and keeps a record:

   ```
   ./python.sh src/eda/odds_sources/table.py --link                 # OddsTrader's events for the frame's matches
   ./python.sh -m src.ingest.oddstrader --books-eids data/studies/odds_sources/oddstrader_eids.csv
   ./python.sh src/eda/current_best_model/odds_input.py --apply data/studies/current_best_model/<date>
   ```

   The adapter's monthly pull (`./python.sh -m src.ingest.oddstrader --from <YYYY-MM>`) must cover the new months first.

   **Then the input list** (since 9 Oct 2026). The chain lists all 58 inputs; this step drops `ios_points_short`:

   ```
   ./python.sh src/eda/current_best_model/template_inputs.py --apply data/studies/current_best_model/<date>
   ```
3. **Fit it** on the GPU. It takes turns with other runners on the card.

   ```
   ./python_tabpfn_local.sh src/eda/model_rebuild/fits.py --out data/studies/current_best_model/<date> --seeds 0-15 --seasons 2019-<Y>
   ```

   Seeds 0–3 of 2019–2026 take about 17 minutes. All 16 seeds take about an hour.
4. **Stage 2's coefficients and speed columns.**
   * Live: the live speed form (`src/eda/serve_speed_tabpfn/live/form.py`).
   * A backtest: the adjustment's column builder on the built frame. `src/eda/model_rebuild/speed_columns.py` does it for the previous frame's matches.
   * The coefficients: `walk_forward` on the instance's seeds 0–3.

A task needs only the parts it uses. A live forecast for season Y needs the frame, fits for season Y and the coefficients of Y.

## The Pinnacle-first instance of 9 Oct 2026

* **Where:** `data/studies/current_best_model/pinnacle_first_2026-10-09/`, built with `odds_input.py --from-reference` ([README](../../data/studies/current_best_model/pinnacle_first_2026-10-09/README.md)).
* **What it holds:**
  * the frozen reference's frame (8 Oct tables), with the Pinnacle-first odds input;
  * fits for 2019–2026, seeds 0–15.
* **Against the reference** (`compare.py`, 2020–2024, both stages, + = Pinnacle first better): +0.01 [−0.29, +0.31] mLL, unresolved; no input flagged.
* **The men's backtest by season:** [report](../studies/pinnacle_first/README.md).
* **It is a 58-input model,** built before `ios_points_short` was dropped.
  * The same frame without the input has fits for 2019–2024, seeds 0–3: the lean review's arm A2 (`data/studies/lean_review/arms/A2/fits/`).
  * A forecast with the decided 57 inputs needs fits for its season: build them when a task needs them, with § "Building it", step 3.
* **Note: if the missing Pinnacle closes (August 2025 on) are obtained, retrain on Pinnacle throughout.**

## The build of 8 Oct 2026 (for reference)

* **Where:** `data/studies/model_rebuild/`.
* **What it holds:**
  * the frame: 67,226 matches, on the tables of the rebuild of 8 Oct, `2026-10-08T1853Z`;
  * fits for 2019–2026, seeds 0–3 only.
* **Why it can't forecast as it stands.** It lacks seeds 4–15, and the tables move on.
* **Its 2026 coefficients** (seeds 0–3; the corrected speed history; the weekly feed): s_atp 0.8956, s_wta 0.9189, b̃ 0.0342.
* **Against the previous model, both stages, both tours 2022–2026:** +0.03 [−0.13, +0.20] milli-log-loss per match, a tie.
