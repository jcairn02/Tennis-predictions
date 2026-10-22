# The current best model: which instance to use

**"The current best model"** is a template: the recipe in the [current-best-model decision](../../../docs/decisions/2026-10-08-current-best-model.md), with its odds input set by the [Pinnacle-first decision](../../../docs/decisions/2026-10-09-pinnacle-first-odds-input.md) (the owner's production rule, 9 Oct 2026).
* **Stage 1:** the local, non-thinking TabPFN-3.5 on 57 inputs (since 9 Oct 2026); for men, lower-level matches enter its inputs through the [level layer](../../../docs/decisions/2026-10-10-level-evidence-layer.md) (since 10 Oct 2026), and the training history holds the [lower-level feed](../../../docs/decisions/2026-10-13-lower-level-feed.md) (since 13 Oct 2026: the levels the history lost in 2026, kept current weekly; it replaced the [accepted men's 2026 Challenger data](../../../docs/decisions/2026-10-10-men-2026-challenger-data.md)).
* **Stage 2:** the walk-forward serve-speed offset, men only.

This file names the instance built from that recipe. **Update it whenever a newer instance is built.**

| Role | Folder | What it is |
|---|---|---|
| **The current instance** (since 21 Oct 2026, 16:39 PDT) | `template_2026-10-21b/` | **The first retrain with its odds input repaired** (the owner: "Yes, start now (Recommended)"; [README](template_2026-10-21b/README.md)): `template_2026-10-21`'s build, unrebuilt, finished with the odds step of 21 Oct afternoon (OddsTrader's tables brought up to date: 288 recent matches from the books' average to BetOnline; 3 mirrored OddsTrader prices left out). The same cut-off (67,531 rows); fits for 2019–2026 seeds 0–3, 2026 seeds 0–15 (2019–2025 seeds 4–15 resume at 03:00 on 22 Oct, evaluation only); harm check against `template_2026-10-21`: +0.018 [−0.074, +0.110] mLL, unresolved, no harm; replay passed. The rollback: `tp.use_instance("template_2026-10-21", tree="C:/Users/zerom/tnr_tpl1021")` |
| The previous instance (21 Oct 2026, 10:59–16:39 PDT) | `template_2026-10-21/` | **The first retrain the owner called** ([report](../../../docs/studies/in_season_retrain/README.md)): the template on the day's tables of 21 Oct (rebuilt 13:47 UTC; Tennis My Life's three reviewed files, the feed's snapshot 20261021). Its live fit trains on 2013 through the cut-off 21 Oct (`training_cutoff.json`: 67,531 rows, every one of its frame's 4,662 2026 matches, the newest finished 19 Oct); stage 2 grown with it; its own extended speed table. Fits for 2019–2026, seeds 0–15; build tree `C:/Users/zerom/tnr_tpl1021`; harm check against 16 Oct: no harm |
| The previous instance (16–21 Oct 2026) | `template_2026-10-16/` | The template on the day's tables of 14 Oct (rebuilt 21:19 UTC) with the men's lower-level fill and every package and feed accepted by then ([report](../../../docs/studies/men_lower_level_fill/README.md)); fits for 2019–2026, seeds 0–15; build tree `C:/Users/zerom/tnr_tpl1016`; its live fit followed the season rule. The rollback: `tp.use_instance("template_2026-10-16", tree="C:/Users/zerom/tnr_tpl1016")` |
| The previous instance (14–16 Oct 2026) | [`template_2026-10-14/`](template_2026-10-14/README.md) | The template **on the day's tables** of 13 Oct: **the Roland Garros repair** applied, **Tennis My Life's accepted corrections**, and **the lower-level feed's first snapshot** merged. Fits for 2019–2026 seeds 0–3 and 2026 seeds 0–15 (the other seasons' seeds 4–15 in progress). Its replays read Tennis My Life's dump frozen as it was built (`C:/Users/zerom/tnr_dump_freeze_1014`) |
| The bridge (13–14 Oct 2026) | [`template_2026-10-13/`](template_2026-10-13/README.md) | The template of 10 Oct with the lower-level feed's first snapshot in place of the men's 2026 package, on the tables of 8 Oct: the feed's harm-check arm (no harm against the 10 Oct instance), in use from 13 Oct 20:41 to 14 Oct 07:43 |
| The 10 Oct instance | [`template_2026-10-10/`](template_2026-10-10/README.md) | The template as decided on 10 Oct 2026: the Pinnacle-first odds input, 57 inputs, the indoor fill, **the level layer for men** and **the accepted men's 2026 Challenger data**. Built on the tables of 8 Oct 2026; fits for 2019–2026, seeds 0–15 |
| The layer alone | [`level_layer_2026-10-10/`](level_layer_2026-10-10/README.md) | The same without the 2026 data: the layer's harm-check arm (seeds 0–3); compared with the reference in `vs_reference_2026-10-08/` |
| An earlier instance | [`pinnacle_first_2026-10-09/`](pinnacle_first_2026-10-09/README.md) | The template with the Pinnacle-first odds input. Built on the tables of 8 Oct 2026 (the reference's frame); fits for 2019–2026, seeds 0–15; compared with the reference in `vs_reference_2026-10-08/` |
| The yardstick | [`reference_2026-10-08/`](reference_2026-10-08/README.md) | The frozen build of 8 Oct 2026: hashed, read-only, odds input the books' average. New data, inputs and rebuilds are compared with it (`src/eda/current_best_model/compare.py`) |

## Using the current instance

* **Forecasts, both stages.** `src/eda/pinnacle_first/backtest.py` (`load()`) is the worked example:
  * the forecast is the 16-seed mean;
  * the per-tour calibration slope and the speed offset's b are fitted walk-forward on 2019 .. Y − 1 from seeds 0–3 (`compare.walk_forward`, `compare.forecasts`);
  * the speed column is `../infosys_atp_backfill/speed_columns_augmented.parquet` (`spd_L_B`).
* **Training data:** one model trained on both tours (2013 .. Y − 1), with `tour` as an input. The calibration slope is per tour; the speed offset is men only.
* **Odds input:** in training, Pinnacle's close, then BetOnline's closing line from August 2025. Live, Pinnacle's current line with the margin removed, at every venue. **If the missing Pinnacle closes are obtained, retrain on Pinnacle throughout.**
  * **Changes at the next retrain** (owner, 21 Oct 2026, [decision amendment](../../../docs/decisions/2026-10-09-pinnacle-first-odds-input.md)). The odds step's default, rule `2026-10-21`, is:
    * TennisExplorer's time-stamped Pinnacle closes from 1 Nov 2025, in place of BetOnline's;
    * when OddsTrader and tennis-data are mirror images, OddsTrader wins.
  * The instances listed above keep the rule they were built with.
  * The owner deferred the test build comparing it with the current model: don't run it until the owner asks.
* **Don't** refit, overwrite or add to its fits for an experiment. Test a change as a candidate in its own folder, and compare it with `compare.py --candidate <folder>`.
* **Live forecasts** need the template built on the day's tables (the decision's "Building it") and Pinnacle's current line. The current instance holds history up to the tables of 13 Oct 2026 (rebuilt 21:12–21:48 PDT); the daily pipeline adds the matches played since on each bet day.
