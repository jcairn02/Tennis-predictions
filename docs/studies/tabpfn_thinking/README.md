# One TabPFN-3.5-Thinking fit on the promising features

> **Update, 5 October 2026: 22 of this model's 53 inputs leaked, and fixing them leaves the result unchanged.**
>
> * **What leaked.** The IOS offence/defence profile (14 inputs), its matchup products (7) and the short-memory IOS points matchup were solved weekly by tournament start date. Results of events still running therefore reached other matches played before them ([match-timing study](../match_timing/README.md)).
> * **The refit.** They were rebuilt on the leak-proof clock and the model was refit once, on the same matches and configuration ([report](../tabpfn_leakproof/README.md)). Against the recalibrated price, for men:
>   * 2022–2026: +1.52 [+0.76, +2.27], against +1.57 here;
>   * 2026: +2.70 [−0.11, +5.51], against +2.70 here.
>
>   Refit against this fit: −0.06 [−0.13, +0.02], a tie. The forecasts correlate 0.9999.
> * **For new work,** build on the leak-proof inputs (`data/studies/tabpfn_leakproof/upload/`). The rule is in [CLAUDE.md](../../../CLAUDE.md), section "Feature timing".

**Status: built 2 October 2026; a study, not a decision.** One paid fit of Prior Labs' hosted TabPFN-3.5-Thinking on
the inputs that the [predictability diagnostic](../predictability_diagnostic/README.md), the
[UFC-ideas study](../ufc_ideas/README.md) and the [feature-alpha audit](../feature_alpha_audit/README.md) found
promising, scored against the closing odds and against linear, boosted and spline models fitted on exactly the same
matches. Labels: **observed** is measured, **inferred** is a reading, **suggestion** is a proposal. Gains are
milli-log-loss (+1 means the mean log loss is 0.001 lower), positive means the second-named forecast is better.
Brackets are paired 95% intervals clustered in four-week blocks of tournament dates, the corrected harness's method.
Every number below is read from `data/studies/tabpfn_thinking/`; the file is named with each table.

## In short

* **Observed. For the men, TabPFN-3.5-Thinking gains more on the closing odds than any forecast in the earlier
  studies.** Given the odds and 53 pre-match inputs, it gains +1.57 [+0.82, +2.32] over the odds recalibrated on the
  same training matches, and +2.08 [+1.07, +3.09] over the raw odds, on 12,352 men's main-tour matches of 2022–2026.
  The earlier best for 2022–2026 was +1.13, Stage D's two profiles with the points-won aggregates, in a walk-forward
  design rather than one fit. The gain is positive in every season (+0.72 to +2.70) and largest at the Grand Slams
  (+2.75). For the women it is +0.74 [−0.14, +1.63].
* **Observed. It is not an interaction effect.** About 60% of the men's gain is a *linear* reweighting of the inputs:
  TabPFN's adjustment to the price, reduced to its linear part, still gains +0.94; its additive part (a curve per
  input) +1.28; adding every interaction only reaches +1.35. Interactions explain about 2% of the adjustment's variance.
  The adjustment leans most on the long-memory offence/defence profile (IOS), then the two-week statistics profile and
  load, age and surface familiarity.
* **Observed. No free model reproduces it.** On the same inputs and matches, the men's gain over the odds is +0.09 for
  a linear fit, +0.19 for ridge, +0.21 for a spline GAM, +0.30 for boosting and +0.08 for TabICL v2, another tabular
  foundation model. TabPFN beats TabICL by +1.49 [+0.75, +2.22] on identical inputs.
* **Observed. The women's gain is mostly a curved calibration of the odds.** A cubic odds-only calibration leaves
  TabPFN +0.27 [−0.48, +1.03], and heavily shrunk ridge matches TabPFN exactly. For the men, +1.27 [+0.43, +2.11]
  remains beyond the most flexible odds-only calibration tried.
* **The big caveat. The inputs are the original features**, which the feature-alpha audit found the same afternoon to
  let some results from overlapping tournaments leak into features before they happened. On the audit's repaired
  features, in this study's own design and on identical matches, the linear men's profile falls from +0.83 to +0.25 over
  the odds. TabPFN was not refitted on repaired features (a second paid fit, quoted below), and TabICL cannot settle the
  question because it finds no gain on either feature set. **Inferred: a lead worth one more paid test, not an edge.**
* **Cost: 162,211 tokens billed** (0.8% of the monthly quota; the server's quote was 648,845), 275 seconds end to end.

## The question

The earlier studies fitted logistic regressions, which add up their inputs in a straight line. The owner asked
whether a non-linear model given all the promising features at once finds something the linear fits miss, through
interactions between features or by weighting them differently: an edge on the closing line, or failing that, a better
model than Elo.

## Design, fixed before the paid call

| | |
|---|---|
| Matches | Main-tour singles (Grand Slams, Tour Finals, 1000s, 500s, 250s), completed or retired; men and women pooled with a tour column. The audit's events with no supported pre-match format are left out (Next Gen Finals; three Melbourne 2021 WTA events): 247 matches |
| Training | 2013–2021 matches with closing odds: 19,331 men's, 20,587 women's. The men's 2018 season has no odds file. The warm-up seasons 2010–2012, when every rating is still settling, are left out |
| Test | 2022–2026 matches with odds: 12,352 men's, 11,467 women's |
| Inputs (54) | The closing odds' log-odds; surface Elo; the serve/return ratings through the iid model; games-weighted Elo; two-week adjusted total points, the short-memory IOS points matchup and the 52-week points matchup; sets in the last 14 days, first matches on the surface this season, age and age squared; the 16-input two-week profile (adjperf on 12 statistics, adjdef on 4); the long-memory IOS offence and defence on 7 statistics and their 7 matchup products; and match context: tour, surface, indoor (men only), level, scheduled best of 3 or 5, round. Every player input is A − B |
| Left out | The families the audit deprioritised: Bradley–Terry, MESR, strength of schedule, revaluation, grinder |
| Model | `model_path` `v3.5_default` (served: `tabpfn-v3.5-20260909`), thinking on, effort high, metric log loss, 8 estimators, softmax temperature 0.9, seed 0: the UFC production settings. One fit, one prediction batch |
| Symmetry | Side A is random, so each test match was predicted in both orientations and the two averaged |
| Comparators | All free, fitted once on the same training matches: the odds recalibrated (one slope per tour), linear fits of the odds plus subsets of the inputs, boosting with and without interactions, spline GAMs, ridge, flexible odds-only calibrations, TabICL v2 |

**A change made before the paid call.** The first plan kept the odds out of the model and stacked its forecast with
the odds afterwards. Running the scorer on the free models first showed why that fails. Built from all the inputs
without the odds and stacked with them, the men's forecast gained +0.10. The same profile information fitted directly
beside the odds gained +0.79. A no-odds forecast is mostly strength the market already prices, and a two-coefficient
stack cannot separate out the small market-orthogonal part. So the paid fit was given the odds as an input
(`manifest.json`, `common.py`). The question "better than Elo?" is answered by the free models below.

## Results

### Against the closing odds (`results.json`)

| Forecast, against the odds recalibrated | Men | Women | Both |
|---|---:|---:|---:|
| **TabPFN-3.5-Thinking** (odds + 53 inputs) | **+1.57 [+0.82, +2.32]** | +0.74 [−0.14, +1.63] | **+1.17 [+0.54, +1.80]** |
| Linear: odds + the 16-input profile | +0.79 [−0.15, +1.74] | −0.31 [−0.95, +0.33] | +0.26 [−0.29, +0.81] |
| Linear: odds + everything (9) | +0.26 [−0.45, +0.98] | +0.73 [+0.08, +1.39] | +0.49 [+0.03, +0.96] |
| Linear: odds + everything + profile (25) | +0.52 [−0.65, +1.70] | +0.41 [−0.52, +1.34] | +0.47 [−0.23, +1.17] |
| Linear: odds + all 47 differences | +0.09 [−1.31, +1.49] | +0.68 [−0.58, +1.94] | +0.37 [−0.63, +1.38] |
| Boosting, no interactions: odds + 47 | −0.18 [−1.30, +0.93] | +0.04 [−1.08, +1.16] | −0.08 [−0.85, +0.70] |
| Boosting with interactions: odds + 53 | +0.30 [−0.80, +1.39] | −0.55 [−1.67, +0.56] | −0.11 [−0.87, +0.65] |

* Against the raw odds TabPFN gains +2.08 [+1.07, +3.09] (men) and +1.24 [+0.12, +2.35] (women). Recalibrating the
  odds alone is worth +0.51 and +0.49: the bookmakers' average line is slightly under-confident (a fitted slope of
  1.09–1.10 on its log-odds).
* Stacked with the odds and cross-fitted by season, TabPFN keeps +1.57 [+0.71, +2.43] for the men. Forward-only, each
  season 2023–2026 fitted on the earlier ones, it keeps +1.69 [+0.84, +2.53]. In the stack the men's odds get a
  coefficient of −0.19 beside TabPFN's 1.16: TabPFN's forecast replaces the price rather than nudging it.
* On the ladder (a coin 0%, the raw odds 100%) TabPFN reaches 102.0% for the men and 101.2% for the women, against
  100.5% for the recalibrated odds.
* By level, against the odds (men; women): Grand Slams +2.75 [+0.49, +5.00]; +2.40 [+1.12, +3.68]. 1000s +1.34;
  +0.02. 500s +1.33; +1.64. 250s +1.30; −0.20. Tour Finals (60 and 75 matches, directional only) −4.07; −1.52.
* By season, men against the odds: 2022 +1.24, 2023 +0.72, 2024 +1.30, 2025 +2.28, 2026 +2.70.

### Where the gain comes from (`diagnostics.json`)

**The odds' own shape.** Flexible odds-only calibrations, fitted per tour on the training seasons, add little: +0.30
for the men and +0.45 for the women (a cubic in the log-odds plus separate slopes for the Slams and best of five).
Beyond them TabPFN still gains:

| TabPFN against | Men | Women | Both |
|---|---:|---:|---:|
| Odds, cubic calibration | +1.31 [+0.51, +2.11] | +0.27 [−0.48, +1.03] | +0.81 [+0.20, +1.42] |
| Odds, cubic + Slam + best-of-five calibration | +1.27 [+0.43, +2.11] | +0.29 [−0.46, +1.05] | +0.80 [+0.17, +1.44] |

At the Grand Slams, beyond the most flexible odds calibration: +1.94 [+0.18, +3.70] (men) and +1.94 [+0.41, +3.46]
(women).

**Interaction or weighting.** TabPFN's adjustment to the price is its log-odds minus the recalibrated odds' log-odds.
It averages 1.7 percentage points of probability and flips the favourite in 610 of 23,819 matches. Describing it with
models fitted on the other half of the tournaments (`results.json`, `adjustment`):

| Share of the adjustment's variance explained | Linear | Additive | + interactions | Interaction share |
|---|---:|---:|---:|---:|
| TabPFN, men | 0.65 | 0.96 | 0.98 | 0.02 |
| TabPFN, women | 0.66 | 0.95 | 0.97 | 0.02 |
| Boosting with odds, men (for comparison) | 0.31 | 0.47 | 0.76 | 0.30 |
| Linear with odds, men (a check: no interactions by construction) | 1.00 | 0.97 | 0.98 | 0.00 |

The value of each part, added to the recalibrated odds and scored like a forecast (`diagnostics.json`,
`surrogate_value`):

| Gain over the recalibrated odds | Men | Women |
|---|---:|---:|
| TabPFN's adjustment, linear part only | +0.94 [+0.06, +1.82] | +0.40 [−0.31, +1.10] |
| Additive part | +1.28 [+0.51, +2.06] | +0.91 [+0.09, +1.73] |
| Additive + interactions | +1.35 [+0.58, +2.13] | +0.88 [+0.05, +1.71] |
| TabPFN itself | +1.57 [+0.82, +2.32] | +0.74 [−0.14, +1.63] |

These parts are read off TabPFN's own test-match outputs. They describe the function it learned; they are not models
that could have been fitted before 2022.

**Which inputs** (share explained lost when a group is shuffled in that description; men, women): long-memory IOS
offence/defence and products 0.62, 0.74; load, age and surface familiarity 0.40, 0.49; two-week statistics profile
0.44, 0.24; the odds 0.31, 0.26; points-won aggregates 0.14, 0.10; Elo 0.12, 0.11; serve/return ratings and
games-weighted Elo 0.09, 0.07; match context 0.00, 0.00.

* **Inferred.** The edge is a *different weighting* of the inputs plus some curvature per input, not interactions. It
  leans on the long-memory IOS profile, the family that added nothing linearly in Stage D. The match context (surface,
  level, best of, round), the natural home of interactions, carries nothing.

### Can a free model do the same? (`gam.json`, `tabicl_check.json`)

Every model below was fitted on the training seasons only. Its penalty, where it has one, was chosen on 2020–2021
inside them.

| Against the recalibrated odds | Men | Women |
|---|---:|---:|
| Ridge, odds + 47 differences | +0.19 [−1.16, +1.54] | +0.75 [+0.17, +1.34] |
| Ridge, odds + everything + profile (25) | +0.65 [−0.44, +1.73] | +0.50 [+0.02, +0.99] |
| Ridge with recency weights (half-life chosen: 4 and 2 years) | −0.37 [−1.79, +1.05] | +0.50 [−0.19, +1.19] |
| Ridge on outlier-proof (quantile) inputs | +0.16 [−1.16, +1.49] | +0.69 [+0.09, +1.30] |
| Spline GAM, odds + 47 differences | +0.21 [−1.09, +1.52] | +0.33 [−1.14, +1.79] |
| Spline GAM, odds + the IOS profile only | +0.03 [−0.64, +0.70] | +0.33 [−0.81, +1.46] |
| Spline GAM, odds + load, age, surface familiarity | +0.37 [−0.25, +0.99] | +1.00 [+0.22, +1.79] |
| TabICL v2 (free foundation model), the identical 54 inputs | +0.08 [−0.99, +1.16] | −0.37 [−1.44, +0.70] |
| **TabPFN-3.5-Thinking** | **+1.57 [+0.82, +2.32]** | +0.74 [−0.14, +1.63] |

* **Observed.** For the women, shrunk ridge equals TabPFN (TabPFN − ridge −0.01 [−0.71, +0.69]). For the men, TabPFN
  beats ridge by +1.38 [+0.31, +2.45], the spline GAM by +1.36 [+0.32, +2.39] and TabICL by +1.49 [+0.75, +2.22].
* **Inferred.** What TabPFN-3.5-Thinking does for the men is specific to it. It is not curvature a spline finds, not
  shrinkage, not recency weighting and not something TabICL also learns. Either its prior estimates these noisy,
  correlated inputs genuinely better, or it exploits something no simpler model picks up, including any leak (below).
  One fit cannot tell these apart.

### Without the odds: better than Elo? (free models only; every test match; `results.json`)

| Against Elo recalibrated | Men | Women |
|---|---:|---:|
| Linear: Elo + everything (9) | +12.40 [+9.36, +15.43] | +10.34 [+8.02, +12.66] |
| Linear: Elo + all 47 differences | +12.14 [+8.73, +15.55] | +11.39 [+8.63, +14.16] |
| Boosting, no interactions (47) | +11.54 [+8.58, +14.49] | +9.17 [+7.09, +11.26] |
| Boosting with interactions (53) | +11.30 [+8.42, +14.18] | +8.97 [+6.71, +11.24] |

Without the odds the features move a model far past Elo, from 78.9% to 90.7% of the way from a coin to the odds (men;
the women from 81.6% to 92.5%), but non-linearity costs: boosting is −0.84 (men) and −2.42 (women) against the linear model on the
same inputs, and interactions add −0.24 and −0.20 to boosting without them.

### Does it survive the repaired features? (`repaired_check.json`, `tabicl_check.json`)

The audit's repair (`docs/studies/feature_alpha_audit/repairs.md`, written at 17:02 on 2 October, about seven minutes
before this study's paid call at 17:09)
rebuilt the shortlisted features in provider match-day order. That cuts the history to the 78,706 dated main-tour
matches, dropping the lower levels and the men's 2018 season. On the 25 differences both versions share, this study's
design and identical test matches (23,681 with odds):

| Against the recalibrated odds | Men, original | Men, repaired | Women, original | Women, repaired |
|---|---:|---:|---:|---:|
| Linear: odds + profile (16) | +0.83 [−0.10, +1.76] | +0.25 [−0.50, +1.00] | −0.29 [−0.94, +0.35] | −0.45 [−1.02, +0.13] |
| Linear: odds + everything + profile (25) | +0.56 [−0.58, +1.70] | +0.37 [−0.52, +1.26] | +0.34 [−0.59, +1.27] | −0.06 [−0.87, +0.75] |
| Boosting with odds | +0.25 [−0.83, +1.33] | +0.00 [−0.96, +0.96] | −0.30 [−1.37, +0.77] | −0.17 [−1.06, +0.73] |
| TabICL v2 with odds (32 inputs) | −0.12 [−1.26, +1.02] | −0.11 [−1.14, +0.93] | −0.54 [−1.55, +0.47] | −0.26 [−1.12, +0.60] |

* **Observed.** The repair takes most of the men's linear profile gain away in this design too. The cause is a mix of
  removing the leak and thinning the history; the audit cannot separate them and neither can this check.
* **Inferred.** TabPFN's +1.57 sits on features of the same vintage and is best read as an upper bound. The repaired
  set also lacks the long-memory IOS profile, TabPFN's most-used group, so a like-for-like repaired test needs that
  profile rebuilt on the dated history first.

## What it cost and how it ran (`thinking_run.json`, `quotes.json`, `thinking/`)

* One thinking fit and one prediction batch, dispatched through a once-only guard: an async submit, the fit id saved
  the moment the server returned it, the fitted model saved before predicting, and no automatic retries. The guard is
  adapted from the UFC project's TabPFN 3.0-vs-3.5 study.
* Server time: fit 231 s (queue 1 s), prediction 11 s; 275 s end to end.
* Tokens: the account's monthly counter moved from 172,980 to 335,191, **162,211 billed** against a quote of 648,845
  (fit 463,704, prediction 185,141). The UFC study also saw bills well below quotes.
* The server echoed the requested configuration (8 estimators) in its returned `tabpfn_config` but reported
  `n_estimators: 2` at the top level of its metadata; what the thinking search ran internally is not documented.
* No column was treated as categorical by the server (`categorical_features_indices: []`); the context codes went in as
  numbers.
* TabPFN's forecast is nearly antisymmetric before averaging the two orientations (mean |P(A) − (1 − P(A swapped))|
  0.010, 95th percentile 0.025).

## Limitations

* **Original features.** The chronology defect the audit found is in the training and the test inputs alike. A flexible
  model could exploit such a leak more than a linear one; nothing here rules that out.
* **One fit, one seed, one split.** The intervals cover sampling of the test matches, not the variation between thinking
  fits. The UFC study saw about 1 milli-log-loss between TabPFN versions on the same inputs.
* **Selection.** The inputs are the earlier studies' winners, chosen after their 2022–2026 results were seen, so the
  test seasons are not an untouched holdout.
* **The bookmakers' average line, not Pinnacle**, and archived pre-play snapshots, not executable prices. A log-loss
  gain is not a betting return.
* `time_col` (thinking mode's time-ordered validation) was not used, to keep the inputs identical to the comparators'.

## Suggestions and decisions for the owner

1. **Suggestion: one more paid fit, on repaired features, before building on this.** Rebuild the long-memory IOS
   profile and products on the audit's dated history (free compute; the audit's machinery rebuilds IOS on those rows),
   then refit TabPFN-3.5-Thinking with the same design. A quote for the 32-column repaired set without the IOS profile
   is 582,705 tokens; at today's ratio the bill would be roughly a quarter of that. If the men's gain survives, it is
   the first lead in either study worth a betting-grade validation. If it collapses, the leak explains it.
2. **Suggestion: if it survives, check that it is the model and not the draw.** Refit with another seed or the
   `v3_default` model, and with `time_col`, on the same split. Whether to spend those fits is the owner's call.
3. **Decision: keep the isolated env and the guard as the pattern for paid TabPFN calls?** `environment-tabpfn.yml`,
   `python_tabpfn.sh`, `src/eda/tabpfn_thinking/guard.py`.
4. **Observed, for the free route:** for the women the same gain comes free, from a shrunk linear model plus a curved
   odds calibration, and load, age and surface familiarity through splines add +1.00 over the odds.

## Files

| What | Where |
|---|---|
| Shared definitions: inputs, symmetry, interval, fingerprint | `src/eda/tabpfn_thinking/common.py` |
| Frame and the exact upload | `src/eda/tabpfn_thinking/build_frame.py` → `data/studies/tabpfn_thinking/frame.parquet`, `upload/`, `manifest.json` |
| Free comparators | `baselines.py` → `baselines.parquet`, `baselines_meta.json` |
| The paid call (env `tennis-tabpfn`) and its guard | `dispatch.py`, `guard.py` → `preflight.json`, `quotes.json`, `thinking/`, `thinking_run.json`, `thinking_run.log` |
| Scoring (written and run on the free models before the paid call) | `score.py` → `results.json`, `results.csv`, `test_predictions.parquet` |
| Diagnostics, GAM and ridge, repaired features, TabICL | `diagnostics.py`, `gam.py`, `repaired_check.py`, `tabicl_check.py` → `diagnostics.json`, `gam.json`, `repaired_check.json`/`.csv`, `tabicl/`, `tabicl_check.json` |
| Tables in this write-up | `tables.py` (prints markdown from `results.json`) |
| Tests | `test/tabpfn_thinking/` (18 in `tennis`, 11 in `tennis-tabpfn`) |

Run order: `build_frame.py`, `baselines.py`, `dispatch.py --dry-run`, `dispatch.py --run --spend-tokens` (re-running it
re-uses the saved predictions and spends nothing), `score.py`, `diagnostics.py`, `gam.py`, `repaired_check.py`,
`tabicl_check.py --prepare` / `--run` (with `C:/Users/zerom/miniforge3/envs/tabiclv2/python.exe`, the UFC project's
env, used read-only) / `--score`. Every script except `dispatch.py` and `tabicl_check.py --run` runs through
`./python.sh`; `dispatch.py` runs through `./python_tabpfn.sh`.
