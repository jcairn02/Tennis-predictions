# Stage 3: is it the method or the data?

**Status: built 2 Oct 2026, waiting for the owner's review.** A study stage, not a decision. It follows [Stage 2](stage2.md); the Brief is in the [README](README.md).

The owner's question after Stage 2: "how much of this is you dont know how to amalgamate the data in a predictive way vs theres simply no edge to be found there?"

Labels: **observed** is measured on the data, **inferred** is a reading of measurements, **suggestion** is a proposal for the owner. Gains are in milli-log-loss (thousandths of a nat per match, unless marked per serve point); positive is better. The tables are generated from the stage's files: `data/studies/shot_level/stage3_tables.md`, written by `src/eda/shot_level/stage3_tables.py` from `stage3_points.json`, `stage3_flexible.json`, `stage3_profiles.csv`, `stage3_planted.csv`, `stage3_planted_depth.csv` and `stage2_ranking.csv`.

## In short

* **Observed. The shot data say a little about the coming match beyond the box scores: for men, in recent seasons only.** The test scores serve points, about 145 outcomes per match instead of one result. The shot features then add 0.012 milli-log-loss per serve point (0.006 to 0.018) to the ratings and box-score form, for men in 2022–2026. That is about a third of what box-score form adds to the ratings (0.035). Before 2022 they make the men's forecast slightly worse, and for women they add nothing. Turned into match forecasts, they add nothing to the closing odds (−0.02).

  Split on 8 Oct 2026, most of the men's 0.012 is the serve's own speed and placement (0.010), not the rally. The rally inputs alone add 0.005 per serve point in 2022–2026 (0.001 to 0.009) and make the forecast worse over 2014–2026 (−0.006). Given the odds, their match forecast is a tie (2022–2026: −0.024, range −0.083 to 0.035).
* **Observed. Better learners do not find more.** On the TabPFN study's split (fitted 2013–2021, scored 2022–2026):
  * ridge logistic regression over the 102 shot differences picks the strongest penalty it is offered, so it uses none of them (−0.03 against the odds). The same ridge finds 1.01 (0.35 to 1.67) in the men's box-score inputs;
  * gradient boosting, which sees both players' values and can find matchups, adds 0.16 (men) and 0.54 (women) over boosting on the odds alone. Both ranges span zero;
  * adding the shot inputs to the box-score inputs makes every learner worse.
* **Observed. One weakness of the method was found. Fixing it found nothing.** The harness fits a multi-input profile without a penalty, and the early seasons have little data to fit on.
  * With no edge at all, a 10-input profile loses about half a milli-log-loss to the odds (0.49 men, 0.63 women, on synthetic results). A planted 1-milli edge in its statistics is never detected.
  * A ridge-penalised walk-forward fit removes that cost (0.04–0.07 with no edge). It recovers 0.40–0.41 of a planted edge instead of 0.23–0.24.
  * On the real results, every shot profile then lands at zero (−0.16 to 0.09 given the odds). The box-score control keeps its men's lead (0.53, range 0.13 to 0.93).
* **Observed. The data limit what can be seen, statistic by statistic.** A planted edge in a player's true career value reaches the pre-match feature at about the squared correlation of the two:
  * 0.15–0.34 of it for quick points, long rallies, net points and holds after breaking;
  * 0.42–0.64 for winners and errors per point;
  * 0.83–0.84 for first-serve speed.

  More data per player raises those shares. For men's quick points on serve, the squared correlation goes from 0.15 in the quarter of matches with the least data to 0.60 in the quarter with the most.
* **Observed. What the real results rule out.** Here, a planted edge of 1 milli-log-loss means the true win probability differs from the closing price by about 2.1 percentage points, root mean square.
  * For men's serve speed, errors and winners, an edge of 0.25–0.5 or more in the true career value would have shown in Stage 2, and did not.
  * For women, the same holds from 0.5–2.
  * For the five noisy statistics, the cut-off is mostly 1–2 (men's holds after breaking: 0.5). For men's quick points on return and women's long rallies, nothing up to 2 is ruled out.
* **Inferred. The reading:**
  * Mostly no edge. For men, the well-measured statistics rule out edges of 0.25–0.5, at or below the size of the project's best lead (0.36–0.9). For women the bounds are looser (0.5–2). On serve points, the shot data carry little beyond the box scores.
  * Partly data too thin. Up to about 1–2 milli-log-loss could hide in the noisy statistics.
  * Little is method. Four different ways of using the data agree, and they find the box-score signal on the same matches. The one flaw found, in how profiles were fitted, hid nothing.

## How the question was split

A real edge could have been missed in three ways. Each has a test:

1. **The data were summarised badly.** Score something closer to the data than the match winner: how many serve points each player wins (part A).
2. **The model was too simple, or badly fitted.** Let flexible learners try the same inputs (part B). Refit the profiles with a penalty (part D).
3. **The data are too thin to show an edge that exists.** Plant edges of known size in the players' true values and see how much the pipeline recovers (part C).

Terms used below:

* **Serve point:** a point on the player's serve.
* **Ridge:** logistic regression with a penalty on the size of the coefficients, which shrinks inputs that do not earn their place.
* **Oracle:** a forecaster that knows the planted truth.
* **Recovery:** the share of the oracle's gain that the real pre-match feature achieves.

## A. Points: is there information at all?

**How** (`stage3_points.py`). For every pool match with a box score there are two rows, one per server. The target is the serve points won out of serve points played. It is a binomial regression (counts, not one bit per match), fitted walk-forward by season, with four models:

* **M1:** the earlier study's serve/return-rating forecast, recalibrated;
* **M2:** M1 plus box-score form: the server's serve points won and the returner's return points won, in three memories;
* **M3:** M1 plus the shot features: the server's serve-side traits, the returner's return-side traits, and both players' rally and ending traits;
* **M4:** M2 plus the shot features.

The forecasts are then turned into match forecasts by the earlier study's iid model. That model treats each point as an independent coin flip with the forecast's probability.

**Observed:**

| Tour | Comparison | 2014–2026 | 2019–2026 | 2022–2026 | Serve points, 2014–2026 |
|---|---|---:|---:|---:|---:|
| Men | Box-score form over the ratings | 0.032 (0.025 to 0.039) | 0.031 (0.024 to 0.039) | 0.035 (0.026 to 0.044) | 20,951,082 |
| Men | Shot features over the ratings | -0.002 (-0.006 to 0.003) | 0.005 (-0.001 to 0.010) | 0.012 (0.007 to 0.018) | 20,951,082 |
| Men | Shot features over the ratings and box-score form | -0.002 (-0.007 to 0.002) | 0.005 (-0.000 to 0.010) | 0.012 (0.006 to 0.018) | 20,951,082 |
| Women | Box-score form over the ratings | 0.031 (0.020 to 0.041) | 0.032 (0.021 to 0.044) | 0.031 (0.018 to 0.044) | 7,374,556 |
| Women | Shot features over the ratings | -0.011 (-0.020 to -0.001) | -0.004 (-0.016 to 0.007) | 0.001 (-0.010 to 0.012) | 7,374,556 |
| Women | Shot features over the ratings and box-score form | -0.009 (-0.019 to 0.001) | -0.005 (-0.016 to 0.006) | -0.001 (-0.012 to 0.011) | 7,374,556 |

(Milli-log-loss per serve point, 95% range clustered by calendar week.)

**From points to matches:**

| Tour | Shot-informed over box-score point model, all matches | The same, matches with odds | Shot information as a feature given the odds | Given Elo |
|---|---:|---:|---:|---:|
| Men | -0.07 (-0.35 to 0.21) on 143,321 | -1.44 (-2.27 to -0.61) on 28,933 | -0.02 (-0.08 to 0.04) on 26,361 | -0.02 (-0.04 to 0.01) on 134,469 |
| Women | -0.89 (-1.56 to -0.21) on 52,194 | -1.78 (-2.80 to -0.76) on 28,679 | -0.02 (-0.14 to 0.10) on 26,461 | -0.02 (-0.09 to 0.05) on 48,435 |

* **Observed.** The shot features move the serve forecast very little: the standard deviation of M4 − M2 is 0.015 log-odds for men and 0.021 for women.
* **Observed. Season by season** (`stage3_points_seasons.csv`, shot features over the ratings and box-score form, men): negative in every season from 2014 to 2021 except 2020 (0.009), together −0.014. Then 0.012, 0.011, 0.017, 0.009 and 0.012 in 2022–2026. The women's seasons scatter around zero.
**Observed. The serve's own attributes against the rally's** (added 8 Oct 2026, `stage3_points_split.py`). The owner separated point-by-point data about the serve from shot-by-shot data about the rally, so the shot inputs were refitted in two halves. "Over the ratings and box-score form" is per serve point; "given the odds" is per match, with each model's iid match forecast scored as a feature. Higher is better; a range spanning zero is a tie.

| Tour | Inputs added | Serve points, 2014–2026 | Serve points, 2022–2026 | Matches given the odds, 2014–2026 | Matches given the odds, 2022–2026 |
|---|---|---:|---:|---:|---:|
| Men | Both (56 inputs) | -0.0022 (-0.0068 to 0.0024) | 0.0122 (0.0063 to 0.0180) | -0.017 (-0.077 to 0.043) | -0.032 (-0.073 to 0.009) |
| Men | Rally only (48: rally length, returns in play, how points end, net play, return depth) | -0.0062 (-0.0103 to -0.0021) | 0.0048 (0.0010 to 0.0086) | -0.005 (-0.055 to 0.045) | -0.024 (-0.083 to 0.035) |
| Men | Serve only (8: first- and second-serve speed, placement) | 0.0050 (0.0020 to 0.0081) | 0.0101 (0.0048 to 0.0153) | -0.004 (-0.028 to 0.019) | 0.006 (-0.033 to 0.046) |
| Women | Both (56 inputs) | -0.0087 (-0.0189 to 0.0015) | -0.0006 (-0.0121 to 0.0109) | -0.017 (-0.136 to 0.102) | 0.044 (-0.095 to 0.183) |
| Women | Rally only (48: rally length, returns in play, how points end, net play, return depth) | -0.0127 (-0.0213 to -0.0042) | -0.0024 (-0.0116 to 0.0067) | -0.059 (-0.169 to 0.051) | 0.032 (-0.074 to 0.138) |
| Women | Serve only (8: first- and second-serve speed, placement) | 0.0044 (-0.0025 to 0.0112) | 0.0014 (-0.0067 to 0.0095) | -0.057 (-0.163 to 0.050) | -0.012 (-0.104 to 0.080) |

* **Observed.** Men, rally inputs only, per serve point by season: negative in every season from 2015 to 2021 (−0.004 to −0.027), then 0.001, 0.003, 0.006, 0.006 and 0.009 in 2022–2026.
* **Inferred.** The men's recent signal on serve points is mostly the serve. The rally's part turned from harmful to slightly helpful as the shot data became dense in 2022 (Stage 0). It is the only sign in this study that rally data gains value with depth. It does not reach match results given the odds.
* **Inferred.** This is the most sensitive test of the four, since a match holds about 145 serve points. The men's 2022–2026 signal is real but small, and it arrives with the dense speed and tracking data of those seasons (Stage 0). The match forecast amplifies the noise in the point forecast more than the signal, so the shot-informed match forecast is worse than the box-score one.

## B. Flexible learners: would a better model find more?

**How** (`stage3_flexible.py`). The TabPFN study's design is used:

* main-tour matches with closing odds, fitted on 2013–2021 and scored on 2022–2026;
* each test match forecast from both players' sides, and the two averaged;
* the gain measured over the odds recalibrated on the training matches;
* 95% ranges from four-week blocks of dates.

Three learners get the odds plus each input set:

* **ridge** gets A − B differences, with its penalty chosen on 2021;
* **gradient boosting** gets both players' values separately, so it can find matchups and curves;
* **gradient boosting rising with the odds** is the same, constrained so the forecast always rises with the odds.

The input sets are the shot features (102 a side), the box score (the 16-input Stage D profile and each player's box-score serve and return points won), and both.

**Observed. Over the recalibrated closing odds, 2022–2026:**

| Tour | Learner | Learner on the odds alone | Shot | Box score | Box score + shot | Box score + shot, over box score |
|---|---|---:|---:|---:|---:|---:|
| Men | Ridge logistic, A − B differences | – | -0.03 (-0.14 to 0.08) | 1.01 (0.35 to 1.67) | 0.13 (0.01 to 0.24) | -0.88 (-1.51 to -0.25) |
| Men | Gradient boosting, both players' values | -0.83 (-1.72 to 0.06) | -0.67 (-1.76 to 0.42) | 0.07 (-0.97 to 1.11) | -0.15 (-1.38 to 1.09) | -0.22 (-1.02 to 0.59) |
| Men | Gradient boosting, rising with the odds | -0.25 (-1.00 to 0.50) | -0.39 (-1.37 to 0.60) | 0.23 (-0.75 to 1.22) | 0.04 (-0.97 to 1.05) | -0.19 (-0.93 to 0.55) |
| Women | Ridge logistic, A − B differences | – | 0.09 (-0.06 to 0.24) | 0.16 (-0.24 to 0.56) | 0.12 (-0.03 to 0.27) | -0.04 (-0.42 to 0.34) |
| Women | Gradient boosting, both players' values | -1.83 (-3.35 to -0.31) | -1.30 (-2.42 to -0.17) | -0.64 (-2.05 to 0.77) | -0.96 (-2.12 to 0.20) | -0.32 (-1.34 to 0.70) |
| Women | Gradient boosting, rising with the odds | -0.40 (-1.47 to 0.66) | -1.04 (-2.18 to 0.09) | -0.51 (-1.68 to 0.66) | -1.08 (-2.24 to 0.08) | -0.57 (-1.33 to 0.19) |

**Observed. Boosting over the same learner on the odds alone** (what the inputs add inside one learner):

| Tour | Learner | Shot | Box score | Box score + shot |
|---|---|---:|---:|---:|
| Men | Gradient boosting, both players' values | 0.16 (-0.73 to 1.05) | 0.90 (0.26 to 1.54) | 0.68 (-0.18 to 1.54) |
| Men | Gradient boosting, rising with the odds | -0.13 (-0.78 to 0.52) | 0.49 (-0.22 to 1.19) | 0.30 (-0.32 to 0.91) |
| Women | Gradient boosting, both players' values | 0.54 (-0.82 to 1.90) | 1.19 (-0.09 to 2.47) | 0.87 (-0.44 to 2.18) |
| Women | Gradient boosting, rising with the odds | -0.64 (-1.58 to 0.30) | -0.11 (-0.88 to 0.66) | -0.68 (-1.62 to 0.27) |

* **Observed.** Ridge penalties chosen on 2021 (C; smaller is stronger; grid 1e-05 to 10):
  * men: shot 1e-05, box score 0.001, both 1e-05;
  * women: shot 1e-05, box score 0.0003, both 1e-05.

  For the shot inputs, the strongest penalty means they are left out. With one penalty for all inputs, adding the shot inputs to the box score drags the box score down with them.
* **Observed.** Test matches: 12,344 men's and 11,405 women's. By Stage 0's formula, this test detects 1.27 (men) and 1.38 (women) with 80% power, or 2.71 and 2.93 with Stage 0's inflation for models with many inputs.
* **Inferred.** Alone, this test is too small to rule out much. Its value is the comparison: on the same matches, the same learners find the box-score signal and not the shot signal.

## C. Planted edges: could the data show an edge that exists?

**How** (`stage3_planted.py`). For ten single features and the 10-input core profile:

1. **The truth.** Each player's true value of the statistic is their rate over the whole career, or over the same calendar season. It includes future matches, so no forecaster could know it before the match. It is shrunk with Stage 2's K and taken as A − B. The part the closing odds already price is removed, and the result is standardised.
2. **The planted edge.** Synthetic results are drawn on the harness's matches with odds: A wins with probability expit(logit(closing price) + β × truth). β is set so that knowing the truth is worth G milli-log-loss over the odds, with G = 0 (no edge), 0.25, 0.5, 1 and 2, and 10 draws each.
3. **The scoring.** The harness's walk-forward fit scores the oracle (the truth itself) and the real Stage 2 feature on the same synthetic results. Detection means a 95% range above zero. Stage 2's own bar, the shuffled-copy line, is higher.

The real results are never read here. The features are rebuilt with Stage 2's code and checked against the stored ones.

**Observed. What a planted gain means:** the root-mean-square gap between the true probability and the closing price.

| Tour | G = 0.25 | G = 0.5 | G = 1 | G = 2 |
|---|---:|---:|---:|---:|
| Men | 1.0 pp | 1.5 pp | 2.1 pp | 2.9 pp |
| Women | 1.0 pp | 1.5 pp | 2.1 pp | 3.0 pp |

For scale: the project's one lead, the men's box-score profile, measures 0.5–0.9 on the earlier studies' frame. The feature-alpha audit puts it at 0.36 under its repaired rules.

**Observed. Planted in the career value.** The table gives:

* the squared partial correlation of feature and truth, given the odds;
* recovery at G = 2;
* the gain when nothing is planted;
* how often the feature, and in brackets the oracle, is detected in 10 draws.

| Tour | Statistic | Memory | Fit | Matches | Corr² | Recovery at G = 2 | Gain with no edge | Detected, G = 0.5 | G = 1 | G = 2 |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Men | Quick points won on serve | 52 weeks | harness | 25,020 | 0.27 | 0.24 | -0.08 | 10% (70%) | 50% (80%) | 70% (100%) |
| Men | Quick points won on return | 52 weeks | harness | 25,020 | 0.20 | 0.15 | -0.04 | 10% (50%) | 40% (100%) | 50% (100%) |
| Men | Long-rally points won (9+ shots) | 52 weeks | harness | 24,470 | 0.33 | 0.27 | -0.07 | 0% (80%) | 20% (90%) | 80% (100%) |
| Men | Winners per point | 52 weeks | harness | 28,897 | 0.46 | 0.42 | -0.03 | 30% (80%) | 70% (90%) | 100% (100%) |
| Men | Errors per point | 52 weeks | harness | 28,897 | 0.64 | 0.64 | -0.05 | 70% (70%) | 100% (100%) | 100% (100%) |
| Men | First-serve speed | 52 weeks | harness | 23,369 | 0.83 | 0.84 | -0.03 | 20% (50%) | 90% (100%) | 100% (100%) |
| Men | Net points won | 52 weeks | harness | 28,655 | 0.37 | 0.34 | -0.05 | 0% (90%) | 30% (90%) | 90% (100%) |
| Men | Holds right after breaking | 52 weeks | harness | 28,296 | 0.23 | 0.18 | -0.04 | 0% (50%) | 10% (90%) | 40% (100%) |
| Men | Winners per point | 2-week half-life | harness | 29,978 | 0.13 | 0.07 | -0.07 | 10% (60%) | 10% (100%) | 10% (100%) |
| Men | First-serve speed | 2-week half-life | harness | 27,355 | 0.49 | 0.51 | -0.04 | 40% (90%) | 50% (100%) | 100% (100%) |
| Men | core profile | 52 weeks | harness | 24,109 | 0.51 | 0.24 | -0.49 | 0% (70%) | 0% (80%) | 30% (100%) |
| Men | core profile | 52 weeks | ridge | 24,109 | 0.51 | 0.40 | -0.07 | 0% (70%) | 30% (80%) | 70% (100%) |
| Women | Quick points won on serve | 52 weeks | harness | 23,401 | 0.24 | 0.20 | -0.10 | 0% (70%) | 20% (100%) | 40% (100%) |
| Women | Quick points won on return | 52 weeks | harness | 23,401 | 0.32 | 0.29 | -0.07 | 10% (80%) | 20% (90%) | 50% (100%) |
| Women | Long-rally points won (9+ shots) | 52 weeks | harness | 22,459 | 0.24 | 0.21 | -0.06 | 0% (50%) | 20% (70%) | 40% (100%) |
| Women | Winners per point | 52 weeks | harness | 28,023 | 0.48 | 0.49 | -0.05 | 30% (90%) | 70% (100%) | 100% (100%) |
| Women | Errors per point | 52 weeks | harness | 28,023 | 0.64 | 0.58 | -0.05 | 40% (50%) | 80% (90%) | 100% (100%) |
| Women | First-serve speed | 52 weeks | harness | 21,953 | 0.81 | 0.83 | -0.05 | 20% (60%) | 80% (90%) | 100% (100%) |
| Women | Net points won | 52 weeks | harness | 27,282 | 0.24 | 0.19 | -0.05 | 20% (70%) | 10% (100%) | 80% (100%) |
| Women | Holds right after breaking | 52 weeks | harness | 27,489 | 0.22 | 0.24 | -0.06 | 10% (90%) | 10% (100%) | 80% (100%) |
| Women | Winners per point | 2-week half-life | harness | 29,555 | 0.11 | 0.07 | -0.06 | 0% (100%) | 10% (100%) | 10% (100%) |
| Women | First-serve speed | 2-week half-life | harness | 26,397 | 0.37 | 0.37 | -0.07 | 10% (50%) | 30% (100%) | 90% (100%) |
| Women | core profile | 52 weeks | harness | 21,978 | 0.57 | 0.23 | -0.63 | 0% (40%) | 0% (80%) | 30% (100%) |
| Women | core profile | 52 weeks | ridge | 21,978 | 0.57 | 0.41 | -0.04 | 10% (40%) | 20% (80%) | 90% (100%) |

The same with the true value taken over the same season is in `stage3_tables.md`. The squared correlations there are higher, 0.22–0.86, since a season is closer to the match than a career.

* **Observed. Single features recover about their squared correlation with the truth,** as theory says they should. The fitting cost of one input is small: −0.03 to −0.10 with no edge planted.
* **Observed. The two-week memory carries little of a player's long-run value.** For winners per point it recovers 0.07, against 0.42–0.49 for the 52-week memory.
* **Observed. The harness's profile fit is the weak point.** With no edge, it costs 0.49 (men) and 0.63 (women). That matches Stage 2's shuffled copies (0.44–0.66). A planted edge of 1 milli-log-loss in all ten statistics at once is never detected, though the oracle sees it 80% of the time. The ridge walk (part D) costs 0.04–0.07, recovers 0.40–0.41 rather than 0.23–0.24, and detects that edge 20–30% of the time.
* **Observed. Even the oracle misses small edges on this many matches.** It detects a 0.5 edge in 40–100% of draws, and a 0.25 edge in 0–70% (`stage3_planted.csv`). Below about 0.5, no pipeline on these matches could show an edge reliably.

**Observed. What the real results rule out (career value).** The real Stage 2 gain is set against the gains the same pipeline produced with a planted edge. An edge counts as ruled out when its feature gains lie 1.645 standard deviations or more above the real gain, at that size and every larger one. The standard deviations come from 10 draws, so the cut-offs are approximate.

| Tour | Statistic | Memory | Fit | Real gain on the odds | Planted G = 0.5: feature gain (sd) | G = 1 | G = 2 | Smallest planted G ruled out |
|---|---|---|---|---:|---:|---:|---:|---:|
| Men | Quick points won on serve | 52 weeks | harness | -0.08 | +0.07 (0.11) | +0.25 (0.17) | +0.41 (0.20) | 1 |
| Men | Quick points won on return | 52 weeks | harness | -0.14 | +0.05 (0.10) | +0.17 (0.16) | +0.29 (0.27) | none up to 2 |
| Men | Long-rally points won (9+ shots) | 52 weeks | harness | -0.04 | +0.08 (0.10) | +0.16 (0.20) | +0.60 (0.33) | 2 |
| Men | Winners per point | 52 weeks | harness | -0.03 | +0.21 (0.11) | +0.44 (0.23) | +0.77 (0.13) | 0.5 |
| Men | Errors per point | 52 weeks | harness | -0.02 | +0.29 (0.11) | +0.67 (0.24) | +1.31 (0.22) | 0.25 |
| Men | First-serve speed | 52 weeks | harness | -0.01 | +0.31 (0.18) | +0.79 (0.30) | +1.82 (0.38) | 0.25 |
| Men | Net points won | 52 weeks | harness | -0.02 | +0.10 (0.08) | +0.27 (0.14) | +0.68 (0.17) | 1 |
| Men | Holds right after breaking | 52 weeks | harness | -0.14 | +0.02 (0.06) | +0.22 (0.17) | +0.32 (0.21) | 0.5 |
| Men | Winners per point | 2-week half-life | harness | -0.05 | +0.02 (0.10) | +0.11 (0.12) | +0.14 (0.14) | none up to 2 |
| Men | First-serve speed | 2-week half-life | harness | -0.03 | +0.24 (0.15) | +0.46 (0.20) | +0.94 (0.19) | 0.5 |
| Men | core profile | 52 weeks | harness | -0.36 | -0.27 (0.17) | -0.04 (0.20) | +0.40 (0.33) | 2 |
| Men | core profile | 52 weeks | ridge | -0.01 | +0.07 (0.09) | +0.29 (0.13) | +0.66 (0.26) | 1 |
| Women | Quick points won on serve | 52 weeks | harness | -0.07 | -0.01 (0.11) | +0.27 (0.28) | +0.35 (0.26) | 2 |
| Women | Quick points won on return | 52 weeks | harness | -0.07 | +0.13 (0.16) | +0.14 (0.20) | +0.51 (0.20) | 2 |
| Women | Long-rally points won (9+ shots) | 52 weeks | harness | +0.04 | -0.04 (0.07) | +0.16 (0.22) | +0.38 (0.28) | none up to 2 |
| Women | Winners per point | 52 weeks | harness | +0.01 | +0.22 (0.16) | +0.42 (0.26) | +0.95 (0.28) | 2 |
| Women | Errors per point | 52 weeks | harness | -0.02 | +0.23 (0.11) | +0.57 (0.21) | +1.10 (0.28) | 0.5 |
| Women | First-serve speed | 52 weeks | harness | -0.12 | +0.24 (0.22) | +0.84 (0.31) | +1.76 (0.36) | 1 |
| Women | Net points won | 52 weeks | harness | -0.08 | +0.10 (0.11) | +0.08 (0.12) | +0.37 (0.15) | 2 |
| Women | Holds right after breaking | 52 weeks | harness | +0.02 | +0.09 (0.12) | +0.14 (0.08) | +0.45 (0.14) | 2 |
| Women | Winners per point | 2-week half-life | harness | -0.02 | -0.02 (0.09) | +0.09 (0.12) | +0.14 (0.13) | none up to 2 |
| Women | First-serve speed | 2-week half-life | harness | -0.10 | +0.08 (0.16) | +0.23 (0.10) | +0.71 (0.22) | 1 |
| Women | core profile | 52 weeks | harness | -0.25 | -0.35 (0.31) | -0.05 (0.28) | +0.42 (0.39) | 2 |
| Women | core profile | 52 weeks | ridge | -0.01 | +0.02 (0.20) | +0.37 (0.22) | +0.75 (0.25) | 1 |

**Observed. What more data per player buys.** This uses the career value and the 52-week memory. The matches are split into quarters by the smaller of the two players' amounts of data in the memory. Each cell gives the median amount, then the squared correlation.

| Tour | Statistic | Depth unit | Quarter 1 | Quarter 2 | Quarter 3 | Quarter 4 |
|---|---|---|---:|---:|---:|---:|
| Men | Quick points won on serve | serve points in play | 83: 0.15 | 311: 0.25 | 678: 0.34 | 1,455: 0.60 |
| Men | Quick points won on return | return points in play | 76: 0.10 | 305: 0.18 | 667: 0.29 | 1,466: 0.50 |
| Men | Long-rally points won (9+ shots) | points of 9+ shots | 24: 0.17 | 90: 0.31 | 223: 0.42 | 549: 0.51 |
| Men | Winners per point | classified points | 400: 0.32 | 1,032: 0.45 | 1,886: 0.50 | 3,707: 0.61 |
| Men | Errors per point | classified points | 400: 0.43 | 1,032: 0.61 | 1,886: 0.72 | 3,707: 0.83 |
| Men | First-serve speed | first serves in, timed | 76: 0.74 | 203: 0.82 | 440: 0.88 | 1,093: 0.92 |
| Men | Net points won | net points | 29: 0.23 | 81: 0.29 | 167: 0.42 | 402: 0.55 |
| Men | Holds right after breaking | games right after breaking | 5: 0.18 | 13: 0.20 | 26: 0.23 | 58: 0.33 |
| Women | Quick points won on serve | serve points in play | 60: 0.13 | 165: 0.21 | 300: 0.30 | 547: 0.48 |
| Women | Quick points won on return | return points in play | 56: 0.17 | 157: 0.29 | 298: 0.38 | 542: 0.58 |
| Women | Long-rally points won (9+ shots) | points of 9+ shots | 15: 0.14 | 44: 0.20 | 88: 0.26 | 174: 0.36 |
| Women | Winners per point | classified points | 236: 0.32 | 577: 0.48 | 945: 0.53 | 1,633: 0.64 |
| Women | Errors per point | classified points | 236: 0.45 | 577: 0.63 | 945: 0.71 | 1,633: 0.79 |
| Women | First-serve speed | first serves in, timed | 42: 0.75 | 92: 0.82 | 158: 0.84 | 287: 0.84 |
| Women | Net points won | net points | 12: 0.15 | 30: 0.21 | 53: 0.24 | 101: 0.33 |
| Women | Holds right after breaking | games right after breaking | 4: 0.15 | 11: 0.20 | 19: 0.23 | 37: 0.28 |

* **Inferred.** The deepest quarter is mostly the best players, who are charted most. So the quarters also differ in who plays. Even so, the gradient says the noisy statistics are limited by data, not by their nature. In the men's deepest quarter, quick points and net points reach 0.50–0.60. That is about where winners and errors stand over all matches (0.46–0.64).

## D. The profiles without the fitting cost

**How** (`stage3_profiles.py`). Every Stage 2 profile is refitted with a ridge-penalised walk-forward fit (`ridge_walk`):

* the base's log-odds are unpenalised;
* the inputs are standardised on the training seasons and penalised;
* season Y uses the penalty whose earlier forecasts had the smallest log loss. Each of those forecasts came from fits on the seasons before it, so nothing about season Y is used.

The harness's own fit is recomputed beside it, on the same rows; it reproduces Stage 2's numbers. "Given the odds + box score" uses the ridge fit of the odds and the box-score profile as its base. The Stage D box-score profile is scored the same way, as the control.

**Observed. Men** (95% ranges clustered by week; 2013–2026 unless marked):

| Profile | Memory | Inputs | Shuffled copies' average, given the odds (Stage 2) | Given the odds, harness's fit | Given the odds, ridge | Given the odds, ridge, 2022–2026 | Given the odds + box score, ridge | Given Elo, ridge |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Box-score profile (Stage D, the control) | 2-week | 16 | – | 0.51 (-0.11 to 1.13) | 0.53 (0.13 to 0.93) | 0.90 (0.29 to 1.51) | – | 3.94 (3.53 to 4.35) |
| Core, own | 2-week half-life | 10 | -0.48 | -0.66 (-1.13 to -0.20) | -0.07 (-0.15 to 0.01) | 0.00 (-0.02 to 0.02) | -0.03 (-0.06 to 0.00) | 0.12 (-0.01 to 0.26) |
| Core, own | 52 weeks | 10 | -0.51 | -0.36 (-0.72 to -0.00) | -0.01 (-0.06 to 0.04) | -0.02 (-0.05 to 0.01) | -0.01 (-0.01 to 0.00) | 0.15 (-0.00 to 0.30) |
| Core, opponent-adjusted | 2-week half-life | 10 | -0.52 | -0.68 (-1.11 to -0.24) | -0.03 (-0.11 to 0.04) | -0.01 (-0.02 to 0.01) | -0.04 (-0.12 to 0.05) | 0.16 (0.04 to 0.28) |
| Core, opponent-adjusted | 52 weeks | 10 | -0.53 | -0.37 (-0.77 to 0.02) | -0.04 (-0.14 to 0.05) | -0.02 (-0.05 to 0.01) | -0.02 (-0.06 to 0.02) | 0.25 (0.05 to 0.46) |
| Core, conceded | 52 weeks | 8 | -0.44 | -0.28 (-0.54 to -0.02) | -0.00 (-0.02 to 0.01) | -0.00 (-0.02 to 0.01) | -0.00 (-0.01 to 0.00) | 0.54 (0.30 to 0.77) |
| Serve speed | 52 weeks | 3 | -0.15 | 0.07 (-0.07 to 0.20) | 0.06 (-0.00 to 0.12) | 0.12 (0.00 to 0.24) | 0.06 (-0.03 to 0.15) | 0.59 (0.33 to 0.85) |
| Point sequence | 52 weeks | 6 | -0.32 | -0.60 (-0.96 to -0.24) | -0.02 (-0.05 to 0.01) | -0.03 (-0.09 to 0.03) | -0.02 (-0.04 to -0.00) | 0.14 (-0.01 to 0.30) |
| Style | 52 weeks | 6 | -0.51 | -0.38 (-0.87 to 0.11) | -0.06 (-0.22 to 0.11) | -0.15 (-0.28 to -0.03) | -0.06 (-0.20 to 0.07) | -0.04 (-0.07 to 0.00) |
| Everything, own | 52 weeks | 25 | -3.52 | -3.24 (-4.50 to -1.97) | -0.05 (-0.24 to 0.14) | -0.10 (-0.21 to 0.01) | -0.05 (-0.20 to 0.09) | 0.50 (0.13 to 0.88) |

**Observed. Women:**

| Profile | Memory | Inputs | Shuffled copies' average, given the odds (Stage 2) | Given the odds, harness's fit | Given the odds, ridge | Given the odds, ridge, 2022–2026 | Given the odds + box score, ridge | Given Elo, ridge |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Box-score profile (Stage D, the control) | 2-week | 16 | – | -0.60 (-1.17 to -0.04) | 0.03 (-0.08 to 0.15) | 0.09 (-0.15 to 0.33) | – | 3.07 (2.29 to 3.84) |
| Core, own | 2-week half-life | 10 | -0.62 | -0.75 (-1.23 to -0.26) | -0.15 (-0.37 to 0.07) | 0.01 (-0.02 to 0.03) | -0.02 (-0.06 to 0.03) | 0.02 (-0.18 to 0.22) |
| Core, own | 52 weeks | 10 | -0.66 | -0.25 (-0.79 to 0.28) | -0.01 (-0.13 to 0.12) | 0.02 (-0.16 to 0.20) | -0.11 (-0.43 to 0.21) | 0.16 (-0.12 to 0.43) |
| Core, opponent-adjusted | 2-week half-life | 10 | -0.65 | -0.68 (-1.07 to -0.29) | -0.16 (-0.32 to 0.00) | 0.01 (-0.02 to 0.03) | -0.05 (-0.14 to 0.04) | 0.04 (-0.15 to 0.22) |
| Core, opponent-adjusted | 52 weeks | 10 | -0.65 | -0.06 (-0.62 to 0.51) | 0.09 (-0.08 to 0.27) | 0.24 (-0.06 to 0.55) | 0.17 (-0.33 to 0.68) | 0.31 (-0.01 to 0.63) |
| Core, conceded | 52 weeks | 8 | -0.50 | -0.44 (-0.87 to -0.01) | -0.05 (-0.11 to 0.02) | -0.04 (-0.13 to 0.05) | -0.08 (-0.17 to 0.01) | 0.01 (-0.12 to 0.13) |
| Serve speed | 52 weeks | 3 | -0.21 | -0.19 (-0.37 to -0.02) | -0.02 (-0.03 to 0.00) | -0.01 (-0.01 to 0.00) | -0.01 (-0.02 to 0.00) | 0.11 (-0.14 to 0.36) |
| Point sequence | 52 weeks | 5 | -0.35 | -0.23 (-0.54 to 0.08) | -0.01 (-0.05 to 0.03) | -0.01 (-0.09 to 0.06) | -0.09 (-0.25 to 0.07) | -0.00 (-0.01 to 0.01) |
| Style | 52 weeks | 6 | -0.73 | -0.97 (-1.51 to -0.43) | -0.05 (-0.15 to 0.05) | -0.01 (-0.02 to 0.01) | -0.07 (-0.23 to 0.10) | -0.12 (-0.28 to 0.04) |
| Everything, own | 52 weeks | 24 | -5.33 | -5.59 (-7.46 to -3.72) | -0.02 (-0.06 to 0.02) | -0.00 (-0.03 to 0.02) | -0.10 (-0.24 to 0.04) | -0.03 (-0.36 to 0.30) |

* **Observed.** Given the odds, the ridge walk chooses its strongest penalty (100,000) in most seasons for most shot profiles (`stage3_profiles.json`, `chosen`). That means it drops the inputs. For the box-score control it chooses 1,000 for men.
* **Observed.** The clearest exception is the men's speed profile. Its chosen penalty falls season by season from 2022 (100,000, 10,000, 3,000, 1,000, 300), and it gives 0.12 (0.00 to 0.24) in 2022–2026. That is the same recent signal Stage 2 flagged (0.24 there), and weaker under the penalty. The women's opponent-adjusted core profile also takes lighter penalties in recent seasons (3,000 in 2021–2024, 1,000 in 2025–2026). It gives 0.24 (−0.06 to 0.55) in 2022–2026.
* **Observed, a side result on the box-score lead.** On the earlier studies' frame, the ridge fit gives the men's box-score profile 0.53 (0.13 to 0.93) over 2013–2026, a range clear of zero where the harness's was not (−0.11 to 1.13). In 2022–2026 it gives 0.90 (0.29 to 1.51). This is not the feature-alpha audit's repaired frame.
* **Inferred.** Stage 2's profile losses were the fitting cost, not harm from the statistics. Without that cost, the profiles are worth nothing given the odds, and a little given Elo: −0.04 to 0.59 for men, beside the box score's 3.94.

## Method or data: the reading

**Inferred.**

1. **The method accounts for little of the null result.** The shot data were used in four different ways:
   * as linear features of each statistic, memory and kind (Stage 2);
   * as both players' raw values in learners that can find matchups and curves (B);
   * against serve points instead of match results (A);
   * as profiles with and without a penalty (D).

   All four agree. On the same matches, the same machinery finds the box-score signal. The one real flaw, the unpenalised profile fit, cost about half a milli-log-loss per 10 inputs. Removed, it revealed nothing.
2. **The data account for part of it, in the noisy statistics.** Quick points on serve and on return, long rallies, net points and holds after breaking pass only 15–34% of a player's true value into the pre-match feature. The real results cannot rule out an edge of up to about 1–2 milli-log-loss in those true values. That is 2–3 percentage points of win probability, root mean square, and larger than the project's best lead (0.36–0.9). More charted points per player would sharpen those statistics (the depth table). It would not create an edge that the well-measured statistics say is absent from the traits they measure.
3. **Most of it is that there is no edge of a useful size here.** For serve speed, errors and winners, the features are close to the truth (0.42–0.84 of it passes through). The real results rule out edges of 0.25–0.5 milli-log-loss for men and 0.5–2 for women in the true career values. On serve points, the shot data's information beyond the box scores is small and recent.

## Not tested

* **In-play use.** The shot data's natural use is within the match: momentum, a drop in serve speed during the match, and fatigue. All the tests here are pre-match.
* **Other markets.** Style statistics (rally length, aces, serve speed) could predict the number of games, tiebreaks or aces better than the winner. Whether Polymarket lists such markets for tennis, and with what depth, is not checked here.
* **Other summaries.** Not tried:
  * matchups at a finer grain than boosting can build from 102 inputs a side (serve direction against the returner's weaker wing);
  * sequence models on the raw stream of shots;
  * statistics outside Stage 1's 25.

  Part A measures what these features say about serve points. It does not bound what other summaries of the same data could say.
* **TabPFN.** The paid fit was not run; it needs the owner's approval. Part B's learners stand in for it.
* **The audit's repaired time rule.** These are the earlier studies' rules, kept so the rows stay comparable with Stage 2 and the list. With nothing found, the repaired rules are unlikely to change the reading. The men's speed signal and the box-score side result should be rechecked under them.
* **The planted truths are a model.** An edge was planted as a straight-line effect of one statistic's true value, or of the ten core statistics together. An edge shaped otherwise, such as a threshold, a matchup, or a signal only in recent seasons, would be recovered differently.

The ideas these gaps leave open, starting with physical condition measured from the rally, are kept in the [list of point-by-point and shot-by-shot ideas](../../research/point-shot-ideas/README.md) (8 Oct 2026).

## Suggestions for the owner

1. **Close the shot-level style statistics as pre-match features for match-winner markets.** This adds the method question to Stage 2's suggestion: it is answered, and the answer does not reopen them.
2. **No purchase of shot-level data for pre-match match-winner markets.** If the noisy statistics need to be settled, a cheaper step comes first: one pre-registered test of the five noisy statistics on the deepest quarter of matches. There, for men, the features already carry 0.33–0.60 of the truth (squared correlation).
3. **Score multi-input profiles with a penalty in future studies,** or compare them with their shuffled copies. The unpenalised walk understates a 10-input profile by about half a milli-log-loss, and a 25-input one by 3.5–5.3 (Stage 2's shuffled copies). Earlier profile results (the UFC study's Stage D, Stage 2 here) should be read that way.
4. **Recheck the men's box-score lead with the ridge fit under the audit's repaired rules.** On the earlier frame, its range is clear of zero with the penalty.

## What was built

| File | What it holds |
|---|---|
| `stage3_sides.parquet` (193.2 MB) | Per pool match, each player's own Stage 2 feature values (A and B), box-score serve and return form in the same memories, the serve-point counts and the ratings' serve forecasts |
| `stage3_points.json`, `stage3_points_seasons.csv` | Part A: the gains per serve point by window and season, and the match-level translation |
| `stage3_points_split.json` | Part A split (8 Oct 2026): rally inputs and serve inputs separately, per serve point and as match forecasts given the odds |
| `stage3_flexible.json` | Part B: every learner and input set, with ranges and chosen capacities |
| `stage3_planted.csv`, `stage3_planted_depth.csv`, `stage3_planted.json` | Part C: one row per statistic, truth, fit, planted gain and tour; the depth quarters |
| `stage3_profiles.csv`, `stage3_profiles.json` | Part D: every profile and the control, per base and fit, with ranges and the penalties chosen per season |
| `stage3_tables.md` | The write-up's tables |

Code in `src/eda/shot_level/`, all with `./python.sh`:

* `stage3_sides.py` (a few minutes);
* `stage3_points.py` (under half a minute), and `stage3_points_split.py` (about 20 seconds);
* `stage3_flexible.py` (about 2½ minutes);
* `stage3_profiles.py` (under a minute);
* `stage3_planted.py` (about 4 minutes);
* `stage3_tables.py` (seconds).

Tests are in `test/shot_level/test_stage3.py` (12). They cover:

* the binomial fit against the expanded 0/1 fit;
* the server rows' orientation;
* the learners' symmetry;
* the planted-gain formula;
* the partial correlation and the truths' shrinkage;
* the ridge walk: no penalty equals the harness's fit, noise inputs cost less, a real signal is found, and a season's own results are never used.
