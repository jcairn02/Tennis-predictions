# The current best model: which instance to use

**"The current best model"** is a template: the recipe in the [current-best-model decision](../../../docs/decisions/2026-10-08-current-best-model.md), with its odds input set by the [Pinnacle-first decision](../../../docs/decisions/2026-10-09-pinnacle-first-odds-input.md) (the owner's production rule, 9 Oct 2026).
* **Stage 1:** the local, non-thinking TabPFN-3.5 on 57 inputs (since 9 Oct 2026); for men, lower-level matches enter its inputs through the [level layer](../../../docs/decisions/2026-10-10-level-evidence-layer.md) (since 10 Oct 2026), and the training history holds the [lower-level feed](../../../docs/decisions/2026-10-13-lower-level-feed.md) (since 13 Oct 2026: the levels the history lost in 2026, kept current weekly; it replaced the [accepted men's 2026 Challenger data](../../../docs/decisions/2026-10-10-men-2026-challenger-data.md)).
* **Stage 2:** the walk-forward serve-speed offset, men only.

This file names the instance built from that recipe. **Update it whenever a newer instance is built.**

| Role | Folder | What it is |
|---|---|---|
| **The current instance** (since 13 Oct 2026) | [`template_2026-10-13/`](template_2026-10-13/README.md) | The template of 10 Oct with **the lower-level feed's first snapshot** (`lower_level_feed/20261013c`, 48,572 matches) in place of the men's 2026 package. Built on the tables of 8 Oct 2026; fits for 2019–2026 seeds 0–3, and 2026 seeds 0–15. Its harm check against the 10 Oct instance: no harm |
| The previous instance | [`template_2026-10-10/`](template_2026-10-10/README.md) | The template as decided on 10 Oct 2026: the Pinnacle-first odds input, 57 inputs, the indoor fill, **the level layer for men** and **the accepted men's 2026 Challenger data**. Built on the tables of 8 Oct 2026; fits for 2019–2026, seeds 0–15 |
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
* **Don't** refit, overwrite or add to its fits for an experiment. Test a change as a candidate in its own folder, and compare it with `compare.py --candidate <folder>`.
* **Live forecasts** need the template built on the day's tables (the decision's "Building it") and Pinnacle's current line. The instance holds history up to the 8 Oct tables.
