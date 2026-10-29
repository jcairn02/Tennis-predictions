# Brief 03: the harness agent

You are the harness agent of the P9 point-details study, in the Tennis-predictions repository (`C:\Users\zerom\Documents\Tennis-predictions`). First read `docs/studies/p9_point_details/briefs/00_shared_context.md` (the request, the gate's findings, the plan, the rules), then this brief.

## Goal

Build the one piece of code that will read match results for this study. It scores a candidate feature on **men's matches of 2025-01-01 to 2026-10-18** against two benchmarks:
* **the market price**: the owner's first criterion, orthogonality to the market;
* **both stages of the live model**: the second criterion.

Calibrate it with placebo features and state its resolution. **You never see a rally statistic or a P9 table.** The lead will run the registered statistics through your harness once, after the pre-registration is frozen.

## The population

Men's Stage 0 matches (`data/studies/predictability_diagnostic/stage0_matches.parquet`) in the window:
* **tour level:** the Slams, the 250s to the Finals, main draws and qualifying;
* **Challengers:** main draws and qualifying.

Count completed matches and retirements separately. Follow the convention of the project's checks and say which one you use; the [unpriced-leads check](../../unpriced_leads/README.md) reported finished matches only as a sensitivity. Report counts by level group, draw and half-year.

## The prices (margin removed; say how)

* **Tour level:** the Pinnacle-first close.
  * Read `src/eda/current_best_model/odds_input.py` and the decision `docs/decisions/2026-10-09-pinnacle-first-odds-input.md` with its 21 Oct amendment.
  * The market benchmark uses the current default rule (`2026-10-21`). The live instance was built with its own rule: see its `odds_input.json` and README in `data/studies/current_best_model/template_2026-10-21b/`. For the model benchmark, use the instance's own inputs.
  * Find out whether tour-level qualifying has prices, and from where (`data/dump/odds/tennisexplorer/` may hold some). If not, say so.
* **Challengers and their qualifying:** TennisExplorer's lower-level tables, `data/dump/odds/tennisexplorer_lower/{matches,odds,moves,listed}/YYYY-MM.parquet`. Columns: `te_id`, `date`, `start_utc`, the players' names and slugs, `has_pinnacle`; per book, `k1_last`/`k2_last` and the opening prices.
  * Use Pinnacle's last pre-match price where it is shown, else a consensus of the other books' last prices. Say which.
  * CLAUDE.md records that the site's last Pinnacle price is a late pre-match price, not the close, with a median 3.6 hours before the start.
  * Link these matches to Stage 0's match ids. The lower-odds job, `src/ingest/tennisexplorer.py`, or the P11 report (`docs/studies/gap_downloads/README.md`, "Bookmaker odds below the 250s") may already have a linker. Report the link rate and never guess.

## The model's forecasts (tour level)

* **The live instance:** `data/studies/master_pipeline/selected_instance.json` → `template_2026-10-21b`.
* **What to use:** its out-of-sample forecasts for seasons 2025 and 2026, from the backtest fits (season Y trained on 2013..Y−1, the 16 seeds averaged in its `fits/`), then stage 2, the serve-speed adjustment, walk-forward as the project's comparisons apply it.
* **Code to reuse:** `src/eda/current_best_model/compare.py` (`seed_table`, `walk_forward`, `forecasts`, `close_forecast`, `paired`, `p_better`) and `src/eda/serve_speed_tabpfn/adaptive/adjust.py`. The [unpriced-leads check](../../unpriced_leads/README.md) built such forecasts for an earlier instance: `data/studies/unpriced_leads/check_now/forecasts.parquet` and `forecasts_facts.json`, with code in `src/eda/unpriced_leads/`.
* **Do not fit TabPFN, and use no GPU.** If the stored fits do not give out-of-sample 2025 and 2026 forecasts, report that and do the market part only.
* **Sanity check:** report the model's log loss against the close's on the same matches, and compare it with what the project's reports state for 2025–26.

## The scoring functions

Put them in `src/eda/p9_point_details/harness.py`, importable and with a command-line entry. Each takes a candidate column, an A − B difference on Stage 0's side A, for a set of matches.
1. **Orientation.** Check how Stage 0's `player_a` relates to the winner (`a_won`'s mean). Make the scoring symmetric: a swap of A and B flips the feature and the result, and must not change the score.
2. **z beyond the base.** A logistic model of the result on the base's log-odds plus the feature: base as an offset, and base with a free slope. Report z for the feature with standard errors clustered by calendar week, and a one-sided p in a declared direction.
3. **Cross-fitted mLL gain.** Fit on every 4-week block but one, predict the held-out block, for both the base-only model and the base-plus-feature model.
   * Gain = the base model's log loss minus the feature model's, × 1000. Positive means the feature is better.
   * A 95% interval and P(better) from a bootstrap over 4-week blocks.
   * Follow the project's reporting words: "better" or "worse" when the interval clears 0, otherwise "unresolved" with P(better).
4. **The new part.** At tour level, residualise the feature on the model's non-price inputs (the instance's `model_frame.parquet` columns other than the odds), as the unpriced-leads study did, and score that residual too. Below the tour, where the model's inputs are not built, say what is possible instead.
5. **Missing values.** A feature may exist for only part of the matches. Score on the subset where it exists, and also with a missing indicator. Report the coverage.
6. **Bases.** The price; the model, both stages (tour only); the model's stage 1 alone (as a diagnostic, never the headline).

## Calibration and resolution

* **Placebos.** Run 200 random standard-normal features, and a few nuisance features (a hash of the match id, a column of the opposite player's index), through every base and population. Their z should look like N(0, 1), and their mLL gains should centre slightly below 0. Report it.
* **A planted signal.** Draw synthetic results from the base plus γ × a random feature, at gains of 0.25, 0.5, 1 and 2 mLL, and report how often your pipeline detects each.
* **Resolution.** For each population and base, give the minimum detectable gain for a single standardised feature (80% power, two-sided 5%), in mLL and as a log-odds coefficient per standard deviation.

## Where you may write

* `src/eda/p9_point_details/harness*.py`;
* `data/studies/p9_point_details/harness/`;
* `docs/studies/p9_point_details/team/harness.md`;
* tests in `test/p9_point_details/`: symmetry, cross-fitting, the planted-signal recovery.

**Store the population** as `harness/population.parquet`. One row per match:
* `match_id`, `date`, the level group, `draw`, `a_won`, `finished`;
* `price_logit`, `price_source`;
* `model_logit_full` and `model_logit_s1` (tour only);
* the flags.

## What you may read

Match results, but only for the bases, placebos and planted signals. Do not open any table under `data/dump/points/infosys_atp_recent/` or `data/studies/p9_point_details/build/`, and do not score any real candidate feature. **Report only the bases' and the placebos' numbers.**

## Your final message

* the counts, by population;
* the bases' log losses, and the model against the price;
* the resolution table and the placebo calibration;
* how to call the harness on a feature column (one example command);
* the paths of everything you wrote.

Put your process notes (choices, failures, variants) in the memo.
