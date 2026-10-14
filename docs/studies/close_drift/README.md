# Does the closing line drift, and does the model's trust in it go stale?

8 October 2026 · Written for the owner · Research evidence, not a decision.

**The owner's question.** The model takes the closing line as an input, so it learns from its training seasons how far to move away from the close on the strength of its other features. If the close was softer in some seasons and sharper in others, two things could follow:
* features orthogonal to the close might be weaker in some eras;
* the learned trade-off might be stale.

**The data.** Seasons ≤ 2024 only; nothing from 2025–2026 is read, so the proposed holdout stays untouched. These are the current model's stored stage-1 forecasts (seeds 0–2), against the books' average close and against Pinnacle. Both prices are margin-free, and the model and each price are recalibrated walk-forward on 2014..Y−1. Debut seasons are left out. Units are mLL; **+ = the model (or the first-named) is better**, and an interval spanning 0 is a tie.

**Code and outputs.** `src/eda/close_drift/drift.py` writes `data/studies/close_drift/drift_by_season.csv` and `drift_by_era.csv`.

## The answer in short

* **Against a softer close, orthogonal features are worth more, not less.** A feature's power to predict the winner does not depend on the market. Its value on top of the close is what the close leaves out, and a softer close leaves more out.
* **The real risk is the trade-off the model learns.** If the value of moving away from the close changes between eras, the model moves too far in a sharper era, or too little in a softer one. The **realisation coefficient** measures this: how much of the model's disagreement with the close actually came true. 1 means right-sized; below 1, the model over-reacts; above 1, it under-reacts.
* **2015–2019: the model over-reacted.**
  * The realisation coefficient was 0.60 (SE 0.16), mostly in 2015–2016 (0.34 and 0.19), when the model trained on only 10,000–15,000 matches.
  * By 2017–2019 it was 0.8–1.2.
* **2020–2024: it under-reacts against the average close** (1.29, SE 0.16) **and is right-sized against Pinnacle** (1.02, SE 0.14). So in the recent era the drift runs in the safe direction: the model is not over-trusting its features.
* **The close itself was stable:** its calibration slope (1.09 → 1.11, a little timid in both eras), its margin (5.7% → 5.5%) and its lead over a sporting model that never sees odds (9.6 → 8.4). What changed is that the books' average became softer than Pinnacle after 2019.
* **About a fifth of the recent edge is that softness.** In 2020–2024 the edge is +1.46 against the average close and +1.16 against Pinnacle. For women it is +1.20 against the average and a tie against Pinnacle (+0.73 [−0.11, +1.57]).

## The measurements

Both tours (`drift_by_era.csv`):

| | 2015–2019 | 2020–2024 |
|---|---|---|
| Average close against Pinnacle, log loss gap (+ = the average is softer) | +0.37 [−0.09, +0.82], tie | **+0.82 [+0.47, +1.16]** |
| Close's own calibration slope (1 = calibrated; above 1 = too timid) | 1.09 (SE 0.02) | 1.11 (SE 0.02) |
| Books' average margin | 5.7% | 5.5% |
| Close's lead over the no-odds model (+ = close better) | 9.6 [7.5, 11.8] | 8.4 [5.7, 11.1] |
| In-season trust: close a / no-odds model b | 0.97 / 0.10 (SE 0.04) | 0.97 / 0.12 (SE 0.04) |
| Model against the average close | +0.18 [−0.28, +0.64], tie | **+1.46 [+0.84, +2.08]** |
| Model against Pinnacle | +0.29 [−0.28, +0.86], tie | **+1.16 [+0.52, +1.79]** |
| Realisation of the model's disagreement, against the average | 0.60 (SE 0.16) | 1.29 (SE 0.16) |
| … against Pinnacle | 0.63 (SE 0.14) | 1.02 (SE 0.14) |
| Spread of the disagreement (log-odds) | 0.107 | 0.122 |

**Realisation by season,** against the average:

| Season | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|---|
| Realisation | 0.34 | 0.19 | 0.78 | 1.19 | 1.11 | 1.73 | 1.56 | 0.91 | 1.25 | 1.30 |

Each season's SE is 0.3–0.5.

* **The in-season trust columns.** The result is regressed on the close's log-odds (a) and on the no-odds model's (b), within each season, in-sample.
  * **b barely moved:** 0.10 → 0.12, and 0.00–0.20 by season.
  * **What the linear blend can add:** its in-sample gain over the recalibrated close is only 0.13 → 0.19.
  * So the edge does not come from blending a sporting forecast with the price. It comes from giving TabPFN the price and the features together, as the meta-stack study found.
* **2020 stands out.**
  * The close's lead over Elo almost doubled (32.6 against 12–22 in other seasons; Elo goes stale over a five-month stop).
  * The linear room is 0.
  * The model's realisation was 1.73, on only 2,305 matches.

## What it means

* **For betting.** The edge to expect depends on the price you bet against. Against Pinnacle-sharp prices, expect about 0.3 less than against the books' average. For women, the edge against Pinnacle is a tie. The benchmark should be the venue the bets go to.
* **For the failure mode to watch.** If the market re-sharpens, or absorbs what these features measure, a model trained on 2020-era seasons would start over-reacting. The realisation coefficient would fall below 1 before the edge visibly went. Tracking it walk-forward each season is the early warning.
* **For the rebuild** (added to the protocol as open questions Q28–Q29):
  1. the training window becomes an axis chosen on D: expanding, the last N seasons, or recency-weighted;
  2. a two-part recalibration also becomes an axis: one slope for the close and a separate scale for the model's disagreement, both fitted walk-forward. A walk-forward scale above 1 would have used more of the 2020–2024 information. It is a bet that the recent regime continues, so it must win on D's confirmation season.
* **What it cannot settle.** These are 2015–2024 seasons, and the early ones are confounded with small training sets and shallow player histories. The 2025–2026 holdout and the sealed matches will show whether the regime held.
