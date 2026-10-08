# Keep the surface IOS profile in the model

**Stated by the owner on 6 October 2026,** after the [surface-IOS study](../studies/surface_ios/README.md)'s test with and without the closing odds: "If its neutral with the odds in the model and + with the feature out of the model, then I vote to keep the feature in. Especially since we may bet early before the close." Recorded on 6 October 2026.

## Decision

**The best model's 21 IOS profile inputs are built per surface.** These are the offence, defence and matchup product (`iosO_<s>`, `iosD_<s>`, `prod_<s>`) of the seven statistics: aces, double faults, first serves in, first- and second-serve points won, holds, and break points saved.

* **What replaces them.** Each player's surface-specific rating on the match's surface: O + E_s and D + F_s from the surface IOS, at the constants tuned on 2013–2018 (`data/studies/surface_ios/tuning_choice.json`).
* **Unchanged.** The other 33 inputs, including the closing odds and the short-memory points matchup.
* **In the study** this is arm R1, `sprof`.

## The evidence

All gains are milli-log-loss per match on 2022–2026, local TabPFN-3.5, four seeds, recalibrated per tour on 2019–2021. **Positive = the surface profile is better**; intervals include the seeds' variance; a range spanning 0 is a tie. The source is `data/studies/surface_ios/results.csv`.

| | Men | Women | Both tours |
|---|---|---|---|
| With the closing odds (the locked primary test) | +0.07 [−0.11, +0.26] tie | −0.05 [−0.21, +0.11] tie | +0.01 [−0.10, +0.13] tie |
| Without the odds | **+0.83 [+0.39, +1.27] better** | −0.33 [−0.84, +0.18] tie | +0.27 [−0.03, +0.58] tie |
| Without the odds, validation seasons 2019–2021 | **+0.98 [+0.42, +1.54] better** | −0.09 [−0.63, +0.46] tie | **+0.47 [+0.05, +0.89] better** |

* **The statistics themselves.** Out of sample, the surface profile forecasts every serve and return statistic better on both tours. For example, men's holds gain +0.40 [+0.34, +0.46] milli per service game in 2019–2026.
* **Leak checks.** The construction is leak-proof: the match-timing study's probe passed at all four cut days.
* **An independent audit** found no bug ([audit](../studies/surface_ios/audit.md)).

## The owner's reasons

* **No cost with the odds.** With the closing odds in the model the change is neutral.
* **A gain without them.** Without the odds it adds, clearly for men.
* **Bets may be placed before the close,** when the price may not yet carry what the surface profile knows.

## What it does not show

* **No edge on the closing price.** Given the close, the profile adds nothing detectable: at most about +0.13.
* **Nothing yet about early prices.** That the profile helps against an early price is the reason for keeping it, and it is untested. The check is the same inputs against Polymarket's price hours before the start. That is the market-anchoring study's suggestion 3; the surface-Elo study built a 24-hours-out frame of 1,067 clean matches.
* **No benefit for women** in any match-level test. Without the odds it is a tie overall, and worse in 2022 and 2024 (−1.12 and −0.96). See the open points.

## Before it is used

* **Recalibrate.** Fit one slope per tour on the model's log-odds, refitted each season on all earlier out-of-sample seasons. For the local TabPFN-3.5 that is worth more than any input tested in the study: +1.30 against +0.53 over the close, both tours, 2022–2026.
* **Keep it fresh.** The surface IOS is not yet part of `src/eda/match_timing/refresh.py`. After that refresh, run in order:
  1. `./python.sh src/eda/surface_ios/build_cache.py`
  2. `build_features.py`, after deleting `data/studies/surface_ios/full_runs/` so that every run is rebuilt
  3. `frames.py` and `arms.py`

  The full-history surface runs take about 30 minutes on 14 cores.
* **Its cost.** Under the same load the surface IOS takes about 1.7 times today's pooled IOS: about 17 against 10 minutes per men's statistic, with 14 runs in parallel.

## Not decided

* **Men only, or both tours?** The owner's statement covers the model as a whole. The evidence supports the men's model only.
  * Without the odds, the women's surface profile ties overall and was worse in 2022–2024 (−0.73 [−1.14, −0.32]).
  * The likely cause is a shorter women's box-score history: hold box scores begin in 2015.
  * The analyst's recommendation is the surface profile for men and today's pooled profile for women, until a women's test shows a benefit. The model pools both tours, so the switch can be made per tour.
* **The other representations** in the study: eight surface deviations, or one net-shift column. Both tied with and without the odds and are not adopted.
* **The project's status.** No model, dataset, market or roadmap is selected. This is a decision about which inputs a candidate model carries.
