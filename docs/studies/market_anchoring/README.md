# Anchor on the odds, nudge with features: a professional bettor's advice, tested

5 October 2026 · Research evidence, not a production, model or betting decision.

A professional tennis bettor told the owner where to look to improve the model:

> "Anchoring on odds and nudging w features. Elo by surface and surface stats in general very important."
> "Can't find good shot by shot data. Its all end of match stats. 'Sackman' stats but not his specifically since he isnt doing them anymore and privatized his repo."

This study infers what that means, checks the best 2026 model against it (how it treats surface and whether it uses the odds), compares market anchoring with López de Prado's meta-labeling, and runs the EDA behind a list of suggestions. Men's main tour throughout, because the best 2026 model is men-only. The literature is in [docs/research/market-anchoring/](../../research/market-anchoring/README.md).

Positive milli-log-loss (mll) means better: +1 mll lowers average log loss by 0.001. Brackets are paired 95% intervals clustered in four-week calendar blocks. Seasons 2019–2026 have been inspected by earlier studies, so nothing here is an untouched holdout. Closing prices are archived tennis-data.co.uk quotes, not timestamped executable prices. Any return quoted below is hypothetical.

## In short

* **Observed. The best 2026 model doesn't use the odds.** TabPFN 3.5 Thinking on 36 sporting inputs scores 0.6080 on 2026. The calibrated average closing price scores 0.5945, so the model is 13.5 [6.3, 20.7] mll worse.
* **Observed. Anchoring on the odds and nudging with the 16-statistic profile and context gives the lowest log loss of any forecast scored on the 2026 test matches.** It scores 0.5931 on 1,710 of the 1,712 (two lack a profile).
  * Against the calibrated closing price: +1.38 [+0.08, +2.67] better.
  * Against TabPFN: +14.9 [+6.9, +22.9] better.
  * Over 2019–2025 the same specification is +0.52 [−0.19, +1.24] better than the calibrated average and +0.44 [−0.24, +1.12] better than calibrated Pinnacle: the same sign, but the intervals include zero.
  * The nudges are small: a median shift of 1.0 percentage point. The favourite changes in 1.8% of matches.
* **Observed. Features nudge; a market-free model's probability does not.** Stacking the 36-input sporting forecast on the market scores −0.14 [−0.30, +0.02] mll. Its encompassing coefficient beside the market is −0.06 (SE 0.05).
* **Observed. Surface matters for predicting matches, and the closing price already has it.**
  * Surface Elo is worth about 3.6 mll inside a ratings-only model.
  * Surface-specific statistics add +0.8 to +1.1 mll to the market-free model.
  * Given the odds, surface Elo's specialisation term adds +0.03 [−0.07, +0.13], and surface statistics +0.02 [−0.19, +0.23].
* **Observed. Players' surface deviations are real but slow to measure.** On clay, the stable part of a player's return-statistic deviation is about two-thirds the size of the stable differences between players. A single season's deviation still correlates only 0.17–0.27 with the next season's.
* **Observed. Meta-labeling with the market as the primary model is the anchored model.** It gives the same log loss, provided the market term is never shrunk. With the market-free model as the primary, meta-labeling is worse than the market itself, at 0.5902 against 0.5900, and its hypothetical bets lose.
* **Inferred.** The bettor most likely meant a market-prior model: take the price as the estimate and let shrunk features move it a little. Meta-labeling is a sizing and filtering layer on top of a probability, not a better probability model.
* **Suggestions.** Ranked in [section 7](#7-suggestions). The first is to evaluate and build the best model as "market plus nudges", scoring every feature by its gain on top of the odds.

## 1. What the advice most likely means

**"Anchoring on odds and nudging with features."** *Inferred.* Start from the market's probability, because it already aggregates ratings, form, injuries and surface. Model only the departures from it: features may move the price a little, by an amount shrunk towards zero, and bets come from the few matches where they move it far enough to clear the margin. Statistically this is the price as an offset or a free-slope input, with penalised feature terms:

* offset: logit *p* = logit *p*<sub>market</sub> + Σ γ*x*
* free slope: logit *p* = *b* logit *p*<sub>market</sub> + Σ γ*x*, where *b* > 1 corrects the favourite–longshot bias

Equivalent framings are a Bayesian prior and finance's Black–Litterman model, which starts from market equilibrium and tilts by "views" in proportion to confidence. "Nudge" implies small adjustments. In this repository's data the anchored model moves the closing price by a median of 1.0 point (90th percentile 3.1, 99th 5.8).

**Could he mean a meta-model in López de Prado's sense?** Meta-labeling (Advances in Financial Machine Learning, ch. 3) works in two steps:

1. A primary model picks the side.
2. A secondary model, trained on whether the primary's past calls paid off, decides whether to act and how much to stake.

There are two readings for betting:

* **The market is the primary.** The side is always the favourite, and the secondary model asks whether the favourite wins given the features. That is exactly the anchored model written with the favourite as the reference side. Section 6.5 confirms it gives the same log loss.
* **Our model is the primary.** The side is our value pick, and the meta-model, with the price as an input, filters it. That is López de Prado's original use. It is tested in section 6.5 and does not beat the anchored model.

"Nudging" fits the first reading better than a filter does. Either way the information is the same: what the features say beyond the price.

**"Elo by surface and surface stats very important."** *Inferred.* Surface-specific ratings, such as Tennis Abstract-style surface Elo blended with overall Elo, and surface-specific serve and return statistics: hold, break and points won by surface.

**"It's all end of match stats. 'Sackman' stats."** *Inferred.* He works from box scores in Jeff Sackmann's match-file format, not shot-by-shot data:

* aces and double faults
* serve points, first serves in, first- and second-serve points won
* service games
* break points saved and faced

He now gets them from another source. *Observed in the repository.* The repaired match rows carry Sackmann-format box scores to 7 June 2026 for the ATP and 6 June 2026 for the WTA, and Tennismylife (TML) rows from there to 2 August 2026. The project's own [shot-level study](../shot_level/README.md) found that shot-level statistics add nothing to the closing odds, which agrees with his practice.

*Observed in the [research note](../../research/market-anchoring/README.md).* Sackmann's results repositories have returned 404 since June 2026, which fits the repository's rows stopping on 7 June. Whether they were made private or deleted cannot be told from outside. His charting repository and Tennis Abstract are still updated.

## 2. How the best 2026 model works

*Observed in [the 2026 TabPFN study](../predictive_frontier_tabpfn/README.md) and its code.* It makes one hosted TabPFN 3.5 Thinking fit on 13,952 men's matches from 2020–2025 and tests it on 1,712 matches from 4 January to 2 August 2026.

* **Inputs.** The established nine plus the 27 frontier features. No prices, dates, identities or test outcomes are inputs.
* **Symmetry.** Predictions are averaged over both player orders.
* **Comparator.** A logistic twin on the same inputs and rows scores 0.6099, against TabPFN's 0.6078.
* **Benchmark.** The study compares both against the average closing price, 0.5948, but never combines them with it.

The 36 inputs:

| Group | Inputs | What they measure |
|---|---|---|
| Established nine | surface Elo logit; serve/return matchup logit; recent opponent-adjusted total points won; short-memory serve-points (IOS) matchup; games-weighted Elo; 14-day sets load; surface familiarity; age; age² | Strength, form, workload, surface-season rust, age |
| Own-expected form (8) | serve and return point residuals against both players' pre-match strengths, half-lives 28 and 182 days, short minus long, coverage controls | Form beyond strength |
| Surface correction (4) | 182-day surface residual minus global residual, shrunk with 400 points; surface evidence; unknown-surface × Elo | Recent surface-specific over- or under-performance |
| Reliability (5) | point exposure, uncertainty × Elo and × serve/return strength, excess dispersion | How trustworthy the strength estimate is |
| Recovery (6) | rest, absence × Elo, recent retirement losses, coverage | Rest and fitness proxies |
| Event speed × style (4) | this edition's earlier-day serve residuals × serve-versus-return style, × Elo | Court-speed proxy |

## 3. How much it separates statistics and ratings by surface

*Observed from the code* (`stage1_baselines.py`, `repair_history.py`, `repair_features.py`, `predictive_frontier/features.py`, `ufc_ideas/stageB_common.py`).

| Input | Surface treatment |
|---|---|
| Surface Elo (and games-weighted Elo) | Rating = 0.7 × overall + 0.3 × surface rating (ATP; WTA 0.75 / 0.25). Each surface rating is moved only by matches on that surface, starting from 1500. This is the only full player-by-surface state with all-history memory. |
| Serve/return matchup | The player's serve and return ratings are pooled across surfaces. Surface enters only as the tour's average serve-point rate on that surface: p = expit(μ<sub>surface</sub> + serve<sub>A</sub> − return<sub>B</sub>). |
| Recent points form, IOS, the 16-statistic profile (market route) | Each match's statistic is centred on the tour's average on its surface, so an ace rate on grass is compared with grass norms. The player's level is pooled across surfaces: no player-by-surface statistics. |
| Frontier surface correction (4 of 27) | Player-by-surface, but only for serve and return points won, with a 182-day half-life and 400-point shrinkage. A grass match sees last year's grass season at about a quarter weight. |
| Surface familiarity | 1 if fewer than three observed matches on the surface this season, as A minus B. |
| Everything else (load, age, reliability, recovery) | No surface. Event speed is keyed by edition and surface. |

So "Elo by surface" is in the model at a fixed 30% weight, which tuning found best. On 2013–2018 it improves the ratings-only log loss by 3.57 mll for men (0.5904 → 0.5869) and 2.79 for women; TrueSkill Through Time tunes to 0.35 / 0.30 and gains 3.74 / 3.41 ([rating systems](../rating_systems/README.md)). "Surface stats" are barely in it: surface enters the statistics as a baseline, not as a player trait, except for the short-memory serve/return correction.

## 4. Does it anchor on the odds and nudge with features?

**The best 2026 model does not.** It is a sporting model, built to be orthogonal to the price and compared with it afterwards.

**The repository does have the anchored form, in its "market route".** The [feature audit's](../feature_alpha_audit/repairs.md) Pinnacle-plus-profile model is logit(Pinnacle) with an unpenalised slope, plus ridge-penalised features with no intercept. It also tests the price as a fixed offset ("profile with raw line as fixed offset"). The [predictive frontier](../predictive_frontier/README.md) and the [TabPFN Thinking](../tabpfn_thinking/README.md) study, which uses closing odds plus 53 unrepaired inputs, did the same.

These models were used to ask whether a feature "adds beyond the market", never as the candidate model.

* **The market route** needs both prices, and Pinnacle ends on 13 January 2026, so it has no 2026 season.
* **The TabPFN Thinking study** is the most direct earlier anchored model: one fit on the closing odds plus 53 inputs, trained on 2013–2021. It reported +1.57 [+0.82, +2.32] over the recalibrated odds for men on 2022–2026, including +2.70 in its 2026 portion. Its inputs were the original features, which leak results from overlapping tournaments. On the repaired features the linear profile in that design falls from +0.83 to +0.25, so its number is an upper bound.

Section 6.2 is the first full-2026 test of an anchored model on repaired features, using the average closing price.

## 5. Meta-models and the odds: what the literature says

Summarised from the [research note](../../research/market-anchoring/README.md); see it for sources, how much of each was read, and the evidence label of each claim.

**Meta-labeling.** *AFML* §3.6–3.8 is quoted verbatim by Hudson & Thames; the book itself was not read.

* A secondary model, trained on whether the primary's bets paid off, decides "whether to take the bet or pass", and its probability sets the size.
* The aim is precision: filtering the false positives of a high-recall primary.
* It suits a white-box or discretionary primary, "because ML will not decide the side".
* The follow-up papers (abstracts only) stress that the secondary needs an "information advantage".
* No sports-betting application was found.

**Anchor and nudge has a long precedent.** Benter's (1994) racing model is a logit of his model's and the public's probabilities, his "second stage".

| Probabilities used | Pseudo-R² |
|---|---|
| The public's | 0.1237 |
| His model's | 0.1016 |
| Both combined | 0.1327 |

Black–Litterman is the same idea: a confidence-weighted average of the market's view and one's own.

**Against sharp tennis prices, combining has not helped.**

* Clegg and Cartlidge (2026) find no Brier improvement over recalibrated Pinnacle: "the market itself encompasses our model".
* Wilkens (2021) finds most of the information is already in the market.
* In-sample, Vaughan Williams et al. (2021) put 80–86% of the weight on the odds at Wimbledon.
* Reported profits come against soft or best-of-many prices: Kaunitz et al.'s football bookmakers, Benter's racing pools.

**Odds as an input pull a model onto the bookmaker.** In the NBA (Hubáček and Šír 2020), forecasts correlate 0.95 with the odds when the odds are an input and 0.87 when they aren't. That is the argument for decorrelating from the market. An offset model avoids the collapse, because its features are fitted only to what the price leaves unexplained.

**Calibration.**

* Soft tennis prices carry a favourite–longshot bias: Forrest and McHale 2007; Lahvička 2014, where outcome = −0.029 + 1.059 × implied probability at Bet365.
* Pinnacle reports a slope of 0.994 for ATP closing prices, 2007–2018 (provider claim).
* This study's proportionally de-vigged slopes, 1.09 on the average and 1.03 on Pinnacle, fit that pattern.

**Surface.**

* Sackmann's Elo blends overall and surface ratings 50/50, tested on the same matches it was scored on: "differences between, say, 60/40 and 50/50 are extremely small".
* This repository tuned 0.30.
* No published test of whether prices under-react to surface was found.

**Sackmann's data.**

* `tennis_atp`, `tennis_wta` and `tennis_slam_pointbypoint` have returned 404 since June 2026. Wayback shows `tennis_atp` live on 14 March and gone on 22 June.
* From outside, "private" and "deleted" look the same.
* The Match Charting Project repository is still public (last commit 18 September 2026), and Tennis Abstract's Elo tables are still updated.
* TML continues the format: its `2026.csv` runs to 29 September. Its licence is inconsistent: MIT on the site, "non-commercial unless explicitly permitted" in the README.

*Inferred.* The literature and this study agree on two points. Anchor-and-nudge is Benter's second stage. Meta-labeling is a sizing layer that needs information the anchored model does not already use.

## 6. EDA results

Code is in `src/eda/market_anchoring/` and outputs in `data/studies/market_anchoring/`.

The harness for every model in this section:

* annual expanding logistic fits from 2013
* ridge on the nudges, chosen on the prior two seasons
* the market term never penalised
* no intercept, so swapping the two players gives the complementary forecast

### 6.1 Ways of putting the odds in

Gain over the calibrated closing price, with a free market slope unless noted:

| Nudge | Average, 2019–2025 (16,422–16,445) | Pinnacle, 2019–2025 (16,270–16,292) | Average, 2026 (1,710–1,712) |
|---|---|---|---|
| 16-statistic profile | +0.33 [−0.26, +0.92] | +0.30 [−0.29, +0.88] | +0.91 [+0.08, +1.73] |
| Profile + serve/return rating + context | +0.52 [−0.19, +1.24] | +0.44 [−0.24, +1.12] | +1.38 [+0.08, +2.67] |
| 36 sporting inputs | +0.29 [−0.24, +0.82] | +0.02 [−0.50, +0.55] | +0.60 [−1.51, +2.71] |
| 36 inputs + profile | +0.31 [−0.45, +1.07] | +0.24 [−0.50, +0.99] | +1.35 [−0.08, +2.77] |
| Established nine | +0.26 [−0.16, +0.68] | +0.24 [−0.15, +0.64] | +0.89 [−0.91, +2.69] |
| Surface Elo (blend) | +0.12 [+0.01, +0.23] | +0.12 [+0.02, +0.22] | +0.43 [−0.28, +1.14] |
| Surface Elo's specialisation term (surface minus overall) | +0.03 [−0.07, +0.13] | +0.02 [−0.06, +0.11] | −0.35 [−1.04, +0.34] |
| Frontier surface correction (4) | +0.01 [−0.15, +0.16] | −0.03 [−0.18, +0.12] | −0.46 [−1.17, +0.24] |
| Stack: market + 36-input forecast (from 2020) | −0.14 [−0.30, +0.02] | −0.09 [−0.21, +0.02] | −0.10 [−0.50, +0.30] |

* **Free slope beats a fixed offset on the average price.** The de-vigged average is under-confident, with a calibration slope of 1.09 (SE 0.015) on 2013–2025, against Pinnacle's 1.03. Fixed at slope 1, the profile + context nudge gains +0.41 rather than +0.52, and Elo loses 0.46 rather than gaining 0.12. On Pinnacle the two forms are level (+0.45 against +0.44).
* **Encompassing regressions** (y on logit market and logit sporting forecast, 2019–2025):
  * The 36-input forecast's coefficient beside the average price is −0.06 (SE 0.05), and −0.06 (0.05) beside Pinnacle. The market leaves it nothing to add.
  * In 2026 TabPFN's coefficient beside the average price is +0.15 (SE 0.075, z = 2.0) in-sample. Cross-fitted by four-week blocks inside 2026, that stack scores −1.34 [−2.76, +0.08] mll against the calibrated price. With weights learned on 2019–2025 it scores −0.26 [−0.55, +0.03].

### 6.2 2026, head to head (1,710 men's matches, 4 January – 2 August)

| Forecast | Log loss | Against the calibrated average |
|---|---|---|
| TabPFN, 36 sporting inputs, no odds | 0.607965 | −13.48 [−20.66, −6.31] |
| Logistic, 36 sporting inputs | 0.610416 | −15.93 [−25.53, −6.34] |
| Average closing price, de-vigged | 0.594820 | −0.34 [−2.95, +2.27] |
| Calibrated average closing price | 0.594482 | 0 |
| Anchor + established nine | 0.593617 | +0.86 [−0.92, +2.64] |
| Anchor + 16-statistic profile | 0.593577 | +0.91 [+0.08, +1.73] |
| **Anchor + profile + context** | **0.593106** | **+1.38 [+0.08, +2.67]** |
| Anchor + 36 inputs + profile | 0.593134 | +1.35 [−0.08, +2.77] |

*Inferred.* Anchoring is the single largest improvement available to the best model. Most of it is the market itself. The part that is the nudges is about one milli-log-loss: positive in 2026 and in 2019–2025, but only clearly separated from zero in 2026, after about ten specifications were tried.

For women the same specification, on the audit's repaired frame, points the same way but less (`anchor_tours_check.csv`):

* +0.26 [−0.22, +0.74] over the calibrated average price, 2019–2025
* +0.25 [−0.24, +0.74] over calibrated Pinnacle, 2019–2025
* +0.53 [−1.33, +2.38] in 2026, on 1,560 matches

### 6.3 Surface: real, but priced

**Surface Elo.** Given the closing price, the specialisation term's coefficient is −0.025 (SE 0.019) on 2013–2025. It is −0.047 (0.038) in early-clay-season matches and −0.044 (0.038) in early-grass-season ones. The market gives surface form at least as much weight as Elo does; if anything slightly more.

**Surface statistics** (`surface_stats.py`). For each of 12 box-score statistics, each player has:

* a level, with a 365-day half-life
* a surface-specific level shrunk to it, with a 730-day half-life
* their difference, the surface deviation

The three are built from strictly earlier days, centred on surface averages, and not opponent-adjusted. Constants were fixed before scoring.

| Nudge | Average, 2019–2025 | Pinnacle, 2019–2025 | Average, 2026 |
|---|---|---|---|
| 12 surface deviations | −0.08 [−0.37, +0.20] | −0.09 [−0.38, +0.21] | +0.22 [−0.43, +0.87] |
| 12 surface-specific levels | +0.02 [−0.19, +0.23] | +0.01 [−0.20, +0.22] | +0.72 [+0.00, +1.44] |
| Surface levels beyond profile + context | +0.04 [−0.30, +0.38] | +0.09 [−0.24, +0.41] | +0.34 [−0.37, +1.04] |
| *No market:* surface levels added to the established nine | +0.83 [+0.17, +1.49] | — | +3.66 [−0.15, +7.48] |

**How stable are surface deviations?** This is per player and season, with at least four match-units on each surface (`surface_persistence.csv`, men, clay minus hard, 965 consecutive-season pairs):

| Statistic | Deviation, season-to-season r | All-surface level, r | Stable SD of deviation ÷ stable SD of level |
|---|---|---|---|
| Aces | 0.16 | 0.89 | 0.25 |
| First serves in | 0.20 | 0.78 | 0.44 |
| Serve points won | 0.22 | 0.76 | 0.48 |
| Hold | 0.19 | 0.73 | 0.49 |
| Return points won | 0.27 | 0.73 | 0.66 |
| Break | 0.21 | 0.68 | 0.66 |
| Return v second serve | 0.17 | 0.61 | 0.67 |

The same pattern holds on grass and for women: return statistics have the largest stable surface deviations. For men on grass the ratio is 0.57 for return points won, 0.62 for breaks and 0.73 for return points against the first serve. *Inferred.* Surface specialisation is mostly a return-game trait, but a season gives so few matches per surface that it takes several seasons to estimate. This study's two-year memory does not get there, and the market seems to.

### 6.4 The market by surface and by point in the surface season

"Early" means either player has fewer than three observed matches on the surface this calendar year (`market_by_surface.csv`).

| Subset | Matches, 2019–2026 | Average slope, 2013–2025 | Pinnacle slope, 2013–2025 | 36-input forecast against the average |
|---|---|---|---|---|
| Hard, early | 3,170 | 1.15 (0.03) | 1.09 (0.03) | −34.0 mll |
| Hard, rest | 7,091 | 1.06 (0.02) | 1.00 (0.02) | −9.8 |
| Clay, early | 2,697 | 1.07 (0.04) | 1.02 (0.04) | −31.2 |
| Clay, rest | 3,082 | 1.09 (0.04) | 1.03 (0.04) | −21.4 |
| Grass, early | 1,547 | 1.13 (0.05) | 1.07 (0.05) | −18.4 |
| Grass, rest | 570 | 1.03 (0.08) | 0.98 (0.08) | −2.0 |

*Inferred.* The market-free model is furthest behind at the start of each surface season. There the price knows things the model doesn't (off-season news, fitness, practice), and favourites also win more than the price says. Letting the market slope vary with early season, best of five, surface and level adds only +0.12 [−0.08, +0.32] (2019–2025; +0.62 in 2026). On top of profile + context it adds +0.31 [+0.003, +0.62] (2019–2026).

### 6.5 Meta-labeling, tested

The test (`meta_label.py`) covers 2020–2026:

* A primary model picks a side.
* A logistic meta-model, trained on earlier seasons' picks, predicts whether that side wins. At fixed odds a winning pick is a profitable pick.
* Meta inputs: the market's log-odds (never shrunk), the primary's edge, surface, level, best of five, early season, and edge interactions.

Log loss of each forecast of the picked side winning, on the same picks:

| Primary | Picks | Market | Calibrated | Anchored model | Meta-model | Primary itself |
|---|---|---|---|---|---|---|
| 36-input value side, all | 15,648 | 0.59000 | 0.58958 | **0.58909** | 0.59024 | 0.60959 |
| 36-input, edge > 0.4 logit | 4,347 | 0.56097 | **0.55994** | 0.56002 | 0.56108 | 0.62039 |
| Anchored model's value side | 15,626 | 0.59021 | 0.58980 | **0.58909** | 0.59003 | 0.58909 |
| Market favourite (meta = market + nudges) | 15,626 | 0.59021 | 0.58980 | 0.58909 | **0.58895** | 0.59021 |

* **The market as primary reproduces the anchored model** (0.58895–0.58900 against 0.58909). The equivalence holds only if the market term is not shrunk. With it penalised at ridge 0.01 the favourite-oriented model lost 1.3 mll, and at 0.1 it lost 10.9.
* **Meta-labeling cannot rescue a market-free primary.** Its meta-model is worse than the plain market at every threshold.
* **Hypothetical flat bets at Pinnacle's closing odds** (2020–2025; not executable):

| Model | Bets | Return per bet |
|---|---|---|
| The 36-input model's value picks | 13,796 | −5.0% [−7.2, −2.8] |
| The same picks, meta-filtered | 4,818 | −6.4% [−9.3, −3.4] |
| Market favourite, meta-filtered | 3,913 | +0.2% [−1.9, +2.3] |
| The anchored model, backing either side when its expected value is positive | 7,389 | +1.6% [−1.3, +4.5] |
| The calibrated average price alone | 3,301 | −4.6% [−9.8, +0.7] |

  At the average price, with its larger margin, the anchored model is +0.4% [−4.0, +4.7] on 2,382 bets. At the best price across bookmakers it is +3.8% [+1.4, +6.2], but even the plain calibrated price shows +1.0% there. Best-price returns are an artefact of stale and outlying quotes, not an edge.

*Inferred.* Meta-labeling adds no information. It is the right tool for sizing and filtering: deciding how much to stake on a calibrated probability, or using a non-probabilistic primary such as a tipster or a rule. It does not replace the anchored probability. López de Prado's own condition, that the secondary model must see information the primary lacks, is the binding one: here that information is the features, and the anchored model already uses them.

### 6.6 What the nudges are made of

One unpenalised fit of the market plus profile plus context, 2013–2025, 29,081 matches (`anchor_nudge_coefficients.csv`). Coefficients are per training-RMS unit, with cluster-robust z:

* **market log-odds:** 1.058 (z = 37)
* **age difference:** −0.072 (z = −3.7). Given the price, the older player does worse than priced.
* **hold rate:** −0.177 (z = −3.1)
* **break points faced per service game:** −0.111 (z = −2.5)
* **return-side ace suppression:** +0.037 (z = 2.7)
* **return-side double-fault statistic:** +0.040 (z = 2.6)
* Everything else has |z| < 1.7.

The negative hold coefficient suggested the market over-credits converting points into games. A direct test says no (`luck.py`). Each player's decayed holds and breaks above the iid expectation from their points won add −0.01 [−0.10, +0.09] to the calibrated average (2019–2025), +0.28 [−0.07, +0.62] in 2026, and −0.11 [−0.24, +0.02] beyond profile + context. *Inferred.* The hold sign is collinearity among the profile's overlapping statistics, not a mispriced-luck effect.

## 7. Suggestions

Ranked by evidence and expected value. These are suggestions, not decisions.

1. **Make "market + nudges" the frame for the best model.** Logit *p* = *b* logit(price) + Σ γ*x*: the market slope never penalised, the nudges ridge-penalised, no intercept. Score every feature by its gain over the calibrated price, not over Elo. In 2026 this beats TabPFN by 14.9 mll and the calibrated price by 1.4 [0.1, 2.7]. The market-free TabPFN track can continue, but as a source of nudges, not as the production candidate.
2. **Feed the market individual features, not a sporting model's probability.**
   * Stacking the 36-input forecast's probability on the price: −0.14 [−0.30, +0.02].
   * Entering the same 36 inputs one by one: +0.29 [−0.24, +0.82] on the average price, +0.02 on Pinnacle.
   * Profile + context entered the same way: +0.52 on the average price, +0.44 on Pinnacle.

   A sporting probability is mostly strength the price already has. Each feature, given the price and shrunk on its own, can keep only the part the price lacks.
3. **Anchor on the price you can actually bet, and measure closing-line value.** Every test here anchors on the closing price, which a bettor only has at the close. Rebuild pre-match price paths from the 36.0 million Polymarket fills (September 2025 – September 2026, adapter `src/ingest/public_dump/polymarket_trades.py`, market start times in `polymarket_sharp_money/markets.parquet`). Anchor on the price 24 hours and 1 hour before the start, and test whether the nudges predict the result *and* the move to the close. This is where the bettor's surface information could still pay: the close has it, an early price may not.
4. **Grow the per-statistic nudge set** (the owner's thesis, and the bettor's "end of match stats"). The 16-statistic profile is the strongest single family against the price: +0.33 on the average price and +0.30 on Pinnacle over 2019–2025, and +0.91 in 2026. Candidates:
   * a hierarchical player × surface model per statistic, pooled across seasons and opponent-adjusted; the persistence table says single seasons are too noisy, and a two-year memory is too short for the return statistics
   * age and trajectory terms (age is the strongest single nudge, z = −3.7)
   * return-side ace suppression

   Already tested and dropped: conversion luck (holds and breaks above the point-based expectation).
5. **Keep surface Elo where it helps: building a price, not beating one.** It is worth 3–4 mll to a ratings-only model, but its specialisation term adds nothing given the close. If TrueSkill Through Time replaces Elo, keep its tuned surface weight (0.35 men, 0.30 women). Don't spend effort tuning surface Elo for edge.
6. **Test surface and statistic nudges where the market is thinner.** These are Challenger, WTA 125 and ITF matches, where the [Polymarket study](../polymarket_sharp_money/README.md) found the largest share of accounts beating the close. The repaired cohort has no Challengers (undated), so this needs dated lower-tier history: SofaScore box scores and TML.
7. **If a paid TabPFN fit is approved, give it the market.** Use the repaired features plus the price's log-odds, train on 2020–2025 and test on 2026. The unrepaired version reported +1.57 mll over recalibrated odds for men. 2026's in-sample encompassing coefficient for the market-free TabPFN is +0.15 (z = 2.0), so there may be a little to extract; cross-fitting says it is small. This needs the owner's approval: the current guard forbids another fit.
8. **Use meta-labeling only as a sizing and filtering layer on the anchored probability.** Possible uses: Kelly fractions, minimum edge by context, or labels defined by closing-line value instead of the result. Do not use it as a substitute for the probability model.
9. **Improve the anchor itself.** The price is most under-confident early in the hard-court season (slope 1.15 on the average, 1.09 on Pinnacle). Letting the slope vary by context gains a little (+0.1 to +0.3 mll) and is cheap. Removing the margin by the odds-ratio, power or Shin method rather than proportionally may do part of the same job; the research note cites Pinnacle's comparison of margin-removal methods.
10. **Secure Sackmann-format box scores going forward.** The profile needs a box score for every match, published before the next one.
    * Sackmann's results repositories have been gone since June 2026, and the repository's Sackmann-format rows end on 7 June.
    * TML continues the format: its `2026.csv` runs to 29 September, while the repository's TML rows stop on 2 August. Its licence is inconsistent (MIT on the site, non-commercial in the README), so check it before relying on it.
    * The WTA API (box scores to 2026) and SofaScore are the other continuing sources. Compare all three on coverage, field definitions and publication delay.
11. **Score the frozen anchored model on matches it hasn't seen.** Before any of the above changes it, freeze the anchored specification and score it on matches after 2 August 2026 as they arrive, against the price and Polymarket. 2019–2026 have been looked at too often to settle a one-mll effect.

## 8. Limits

* **Population and prices.** Men's main tour (the best model is men-only), plus one women's check of the anchored model, on the repaired dated cohort without Challengers or qualifying. Archived closing prices are not executable quotes and carry no timestamps. Pinnacle ends on 13 January 2026, so 2026 uses the average price.
* **Selection.** 2026 is seven months (1,712 matches). About ten nudge sets × two forms were scored, and nothing is adjusted for that multiplicity. The 2026 interval for the best anchored model excludes zero narrowly.
* **Construction.** The surface statistics are not opponent-adjusted and use only main-tour history, so they may understate what a full model could do.
* **Betting.** Returns are hypothetical flat stakes at archived prices: no limits, no slippage, no fees, and they are not a betting test.

## Files and rebuild

| What | Where |
|---|---|
| Shared loading, the walk-forward harness, cluster-robust fits | `src/eda/market_anchoring/common.py` |
| Anchor forms, nudge sets, stacks, encompassing, the 2026 TabPFN stack | `anchor.py` → `anchor_results.csv`, `anchor_encompassing.csv`, `anchor_tabpfn2026.csv`, `anchor_predictions.parquet`, `anchor_summary.json` |
| Context slopes, nudge coefficients, the women's check | `anchor_detail.py` → `anchor_context_slopes.csv`, `anchor_nudge_coefficients.csv`, `anchor_tours_check.csv` |
| Surface statistics: persistence, features, nudges | `surface_stats.py` → `surface_persistence.csv`, `surface_stat_features.parquet`, `surface_stat_results.csv`, `surface_stat_predictions.parquet`, `surface_stat_summary.json` |
| The market by surface and season timing | `market_surface.py` → `market_by_surface.csv`, `surface_residual_tests.csv` |
| Meta-labeling | `meta_label.py` → `meta_probabilities.csv`, `meta_bets.csv`, `meta_reference_bets.csv` |
| Conversion luck | `luck.py` → `luck_results.csv`, `luck_summary.json` |
| Tests: time rule, chronology, symmetry, the unshrunk anchor | `test/market_anchoring/test_market_anchoring.py` → `tests.xml` (6 passed) |

Run from the repository root through Git Bash, with `C:/Users/zerom/miniforge3/envs/tennis/Library/bin` on PATH:

```bash
./python.sh src/eda/market_anchoring/anchor.py
./python.sh src/eda/market_anchoring/anchor_detail.py
./python.sh src/eda/market_anchoring/surface_stats.py
./python.sh src/eda/market_anchoring/market_surface.py
./python.sh src/eda/market_anchoring/meta_label.py
./python.sh src/eda/market_anchoring/luck.py
./python.sh -m pytest test/market_anchoring -p no:cacheprovider --basetemp=data/studies/market_anchoring/pytest_tmp --junitxml=data/studies/market_anchoring/tests.xml
```

Inputs are read, never written: the 2026 TabPFN frame and predictions, the repaired rows, matches and features, the predictive frontier's out-of-sample forecasts, and Stage 1's odds table. No paid call, new package or download was used.
