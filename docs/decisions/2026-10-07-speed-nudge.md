# The current best model includes the walk-forward serve-speed adjustment

**Stated by the owner on 7 October 2026,** after the [serve-speed TabPFN study](../studies/serve_speed_tabpfn/README.md). Recorded the same day. The owner's words:
* "Ok, the current best model will be the model + Speed as a walk-forward adjustment on the model's output (secondary)."
* "When I refer to the current best model, it will also imply the addition of this walk-forward adjustment."

**Amended by the owner on 8 October 2026:** "I confirm 28 day memory and id love to get the speed data daily :)"
* **The adjustment always uses the 28-day memory.** That is the column `spd_L` and its coefficient set L in `src/eda/serve_speed_tabpfn/adaptive/adjust.py`, with every match in mode L. The 14-day version below is superseded. The evidence: it beat the 14-day memory and the switch in every availability scenario ([adaptive follow-up](../studies/serve_speed_tabpfn/adaptive.md), exploratory).
  * `spd_L` = clip((f̂₂₈,A − f̂₂₈,B) / 1.9496 km/h, −4, 4). The study's filter, with a 28-day half-life instead of 14 and every other constant unchanged, runs on the speeds in hand at forecast time.
  * **The coefficients come from the history that matches the live speed feed.**
    * While only the weekly feed exists, they are fitted on the weekly feed's history. In force for 2026: s_atp 0.8996, s_wta 0.9168, b̃ 0.0376 per unit.
    * Once a daily feed runs, they are refitted on the daily feed's history (the latency study's scenario D).
* **Speed data are to be collected daily.** The collector is being built under the [scraping approval](2026-10-08-scraping-approved.md).

## Decision

**"The current best model" means two stages.**

1. **The base forecast:** the local, non-thinking TabPFN-3.5 with 58 inputs, as decided on 6 October ([offset Elo](2026-10-06-offset-elo.md), [surface IOS profile](2026-10-06-surface-ios-profile.md)).
   * The inputs are in `data/studies/surface_rating_race/model/model_frame.parquet`. Settings: 8 estimators, softmax temperature 0.9, pretraining limits ignored.
   * Season Y is predicted by fits trained on 2013 to Y − 1.
   * The forecast is symmetrised (stored and swapped) and averaged over seeds. η is its log-odds.
2. **The serve-speed adjustment** on that forecast: the study's S9, shrunk version:

   &nbsp;&nbsp;&nbsp;&nbsp;**logit q = s_tour,Y · η + b̃_Y · `spd_f`**

   * **`spd_f`** = clip((f̂_A − f̂_B) / 2.224 km/h, −4, 4): the two men's difference in current first-serve-speed form. It comes from the study's two-state filter on as-of edition-centred speeds (`src/eda/serve_speed_tabpfn/features.py`; constants frozen on speeds ≤ 2023).
     * It is 0 for women, and 0 for a man with no speed history. It is never missing.
   * **The three coefficients** (s_atp, s_wta, b̂_Y) are fitted jointly by maximum likelihood on the base's out-of-sample forecasts of 2019 to Y − 1 (seed 0–3 mean, debut seasons out).
   * **The shrinkage:** b̃_Y = b̂_Y · τ² / (τ² + SE²), with τ = 0.05. The slopes are not refitted after it.
   * **For women** the adjustment reduces to the decided calibration slope, because their `spd_f` is 0.
   * **Code:** `nudge_parameters` and `nudge` in `src/eda/serve_speed_tabpfn/score.py`.
   * **In force for 2026** (fitted on 2019–2025):

     | Coefficient | Value |
     |---|---|
     | s_atp | 0.9007 |
     | s_wta | 0.9168 |
     | b̂ | 0.0452 (SE 0.0201) |
     | **b̃** | **0.0389** per unit of `spd_f` |

     For 2027 they are refitted on 2019–2026, as each season is in turn.

* **What b̃ means.** In a 50–50 match, a man whose speed form is 2.2 km/h above his opponent's (relative to each player's own norm) gets about +1 point of win probability over the base forecast.
* **Superseded comparisons.** New work is compared against both stages, not against the TabPFN fit alone.

## The evidence

From the study's one pre-registered run (`data/studies/serve_speed_tabpfn/results.json`). Men 2024–26, 7,068 matches, expanding window. Gains in milli-log-loss per match, positive = the speed version better; a 95% interval spanning 0 is a tie.

| | Result | Reading |
|---|---|---|
| **This adjustment** (S9, shrunk; a pre-registered *secondary*) against the calibrated base | **+0.41 [+0.04, +0.78]** | Better |
| The same, unshrunk | +0.45 [+0.002, +0.91] | Better |
| Speed as an extra TabPFN input column (P2, the primary) | +0.07 [−0.05, +0.18] | Tie: TabPFN used about 8% of the information |
| Speed information beyond the base (S0; log-odds per unit of `spd_f`; positive = the faster-trending man wins more than the base says) | +0.065 [+0.012, +0.118] | Present |
| The original 14-day statistic on blind 2025–26 (S12; per 5.998 km/h) | +0.103 [+0.029, +0.178] | Replicates the published +0.090 |
| For scale: the calibrated base against the calibrated close (S13) | +2.20 [+1.10, +3.30] | The adjustment is about 19% of this edge |

**Multiplicity.** Four of 30 secondary intervals exclude 0 (S0, both S9 versions, S12). Under the verifier's simulated null that has a probability of 1.7%.

## What it does not show

* **It is not a confirmatory result.** It is a pre-registered secondary, and its lower bound is +0.04 mLL.
* **It assumes speeds are known as soon as a match ends.** The backtest uses every speed from matches that surely finished before the next one could start. At bet time, the sources lag:
  * ManTennisData publishes about a week after the matches;
  * the AO and RG Infosys files and the other Slam feeds are collected after the event (the [download cadence](2026-10-06-download-cadence.md)).
  * **Observed** (values only): in men's 2024–26 test matches, 53% of players' latest speed reading was within 7 days of the match, and 31% within 1 day. Those are the readings the filter weights most, often the previous round of the same event.
  * *Inferred:* with today's sources, the live gain is smaller than +0.41 until speeds arrive faster.
  * **Measured on 8 Oct 2026** ([latency follow-up](../studies/serve_speed_tabpfn/latency.md); exploratory):
    * with today's sources, the adjustment keeps **+0.27 to +0.38 mLL (66–92%)**. The top of the range uses a 28-day memory for the speed form instead of 14 days;
    * a one-day delay keeps all of it;
    * filling late speeds from box scores does not help.
    * Using the 28-day memory live was decided by the owner on 8 Oct 2026 (amendment at the top).
  * **Measured on 8 Oct 2026** ([adaptive follow-up](../studies/serve_speed_tabpfn/adaptive.md); exploratory). The owner asked for a switch: 14-day memory when speeds are in hand, 28-day when they are late. It was built (`src/eda/serve_speed_tabpfn/adaptive/`) and audited.
    * **Always using the 28-day memory beat both the switch and the 14-day memory in every availability scenario, instant included:** +0.54 against +0.41 with instant speeds; +0.38 with today's sources.
    * **The owner chose the 28-day memory on 8 Oct 2026** (amendment at the top).
* **Early prices.** It was not tested against Polymarket's price 24 hours out. The speed column tied there.
* **No money.** A log-loss gain against an archived average close is not a betting return.
* **Women:** unchanged; no WTA tour-level speed exists.

## Before it is used

* **Keep the speeds current.** Refresh ManTennisData weekly (`./python.sh -m src.ingest.public_dump.mantennisdata --commit latest`). Then rebuild the panel and the features (`src/eda/serve_speed_tabpfn/panel.py`, then `features.py`).
  * Without new speed data, `spd_f` decays to 0 within about six weeks and the adjustment switches itself off.
  * Adding it to the scheduled downloads is the owner's call (the acquisition study's option 2).
* **Bring the base up to date.** The model frame ends with events starting by 28 Jul 2026 and is behind Stage 0. Its rebuild steps are in the [offset-Elo decision](2026-10-06-offset-elo.md).
* **Make it reusable.** No module yet writes "the current best model's" forecasts for every season or for new matches. The adjustment exists inside `score.py`'s S9 for 2024–26 only. A small module that applies it walk-forward to the base's forecasts is the next build.

## Not decided

* How and where to collect speeds fast enough for bet time.
  * **Permission settled on 8 Oct 2026:** the [scraping approval](2026-10-08-scraping-approved.md) covers the ATP's Stats Centre and every Slam feed, live included.
  * Building the collectors remains.
* A prospective confirmation on matches after 7 October 2026.
* **The project's status.** No model, dataset, market or roadmap is selected. This is a decision about what "the current best model" means.
