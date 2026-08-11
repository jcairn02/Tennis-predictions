# 01 — Academic Landscape: Tennis Match Prediction (2012–2026)

*Produced 2026-06-10 by a multi-agent research run (108 agents; 129 claims extracted from 26
sources; 25 survived 3-vote adversarial verification, 0 refuted). Every claim below carries its
verification vote and source. This is the most settled of the research pillars.*

## Headline conclusions

1. **Nobody beats the bookmaker head-on.** Across every credible benchmark from 2016 to 2026,
   bookmaker odds (Pinnacle or a vig-corrected multi-book consensus) are the most accurate
   tennis forecaster, and no published odds-free model beats them overall. Models that *match*
   the market all use the market's own odds as a training input.
2. **Every published profitable result is a selective-subset play** — find the slice of matches
   where the market has a structural blind spot, bet only there, pass on everything else. This is
   exactly the UFC pipeline's philosophy (calibrated model + expected-value gate), so the playbook
   transfers directly.
3. **The cheap baseline is excellent.** A specific, fully published Elo variant gets within ~2
   percentage points of bookmaker accuracy using nothing but win/loss history. It is implemented
   and tested in this repo already (`src/ratings/elo.py`).
4. **Predictability collapses outside the top tier — for the bookmakers too.** All models,
   including the market, lose 10–20 percentage points of accuracy on matches without a top-30
   player. The weakest-priced segment of the sport is also the one with integrity and limit
   issues (see doc 03).

## The benchmark hierarchy

The canonical model comparison is **Kovalchik (2016), "Searching for the GOAT of tennis win
prediction"** (Journal of Quantitative Analysis in Sports): 11 published models on 2,395 ATP
2014 singles matches, walkovers and retirements excluded. Verified 3-0 against the published
text: a Shin-corrected 7-bookmaker consensus hit **72% accuracy / 0.55 log loss** — top or
tied-top on every metric ("no model was able to beat the bookmakers").
[Source](https://vuir.vu.edu.au/34652/1/jqas-2015-0059.pdf)

| Model family | Accuracy (ATP 2014) | Log loss | Verdict |
|---|---|---|---|
| Bookmaker consensus (Shin-corrected) | 72% | 0.55 | Unbeaten |
| FiveThirtyEight-style career Elo | 70% | 0.59 | Best odds-free model |
| Bayesian hierarchical point-based (Ingram 2019) | 68.8% | 0.592 | Best point-based |
| Regression on rankings/points | ~68% | 0.61–0.64 | Mid |
| Classic point-based Markov (Barnett–Clarke lineage) | 66–67% | up to 0.68 | Lags (see below) |

Modern replications agree. **Bunker et al. (2024)** (~34,000 ATP matches, expanding-window
2007–2020, verified 3-0): best ML models ADTree 69.8% and logistic regression 69.5% vs Elo and
Weighted Elo both at 67.5%, with odds-derived predictions at 70.4% — ML *matched* the odds but
didn't beat them, and the ML feature set itself included odds. Only 2 of 5 ML algorithms even
beat Elo (neural nets, SVM, and random forest did not).
[Source](https://journals.sagepub.com/doi/10.1177/17543371231212235)

Freshest evidence (2024–25 Grand Slams, 1,684 matches, verified 3-0): a dynamic graph model
trained on bookmaker odds reached statistical parity — bookmakers 74.1% correct, model 73.5%
(p = 0.40), official rankings 69.7%. Note the circularity: it's trained on odds, so this shows
odds-replication, not independent skill. Published in Royal Society Open Science (May 2026).
[Source](https://arxiv.org/html/2508.15956v1)

### The exact Elo spec to use (verified at p.130 of Kovalchik 2016)

- Rating update: standard Elo with **K = 250 / (career matches + 5)^0.4** — new players move
  fast, veterans stabilize.
- **Grand Slam matches: K × 1.1.**
- Start rating 1500.
- This scored 70% / 0.59 log loss — "performed better than all other approaches" among
  non-bookmaker models. Later work (Angelini & Candila's Weighted Elo, which scales updates by
  margin of victory; surface-specific blends) extends rather than contradicts it.

`src/ratings/elo.py` implements this spec (including the per-match K multiplier and a
surface-blended variant: effective rating = weighted average of overall and surface-specific
ratings). Smoke-tested on real ATP 2023–2025 data: walk-forward log loss 0.638, accuracy 62.9%
post burn-in — sane for a 2-year warmup window; the published 70% figures use full career history
(the roadmap's first milestone is backfilling to ~1990 and reproducing ~0.59).

## Why odds-aware training is the gap-closer

Verified 3-0 (merged claims): in the 2025 graph paper's survey table, the only model to edge
bookmaker accuracy (+0.14% ratio) was **Wilkens (2021)** — gradient boosting *with bookmaker odds
as a feature*; pure Elo sat at −2.78% and point-based models at −6.94%. Wilkens himself called
his result parity, not outperformance ("not able to outperform simple betting odds-implied
forecasts"). The graph-paper authors state the efficiency argument plainly: any published
market-beating model would simply be adopted by the bookmakers.
[Sources](https://arxiv.org/html/2508.15956v1), (https://journals.sagepub.com/doi/10.1177/17543371231212235)

**Implication for this project:** train *with* market features so the model's probabilities are
anchored to a near-efficient prior, then hunt the residual — the same structure as the UFC v2.5
model, which carries the market's logit-odds as a feature and earns its money on the residual
slices. The alternative (pure fundamentals model "discovering" the market is right 98% of the
time) wastes capacity re-deriving the consensus.

## The point-based (Markov) family — weaker for pre-match, but the only road to in-play

Tennis's scoring structure (point → game → set → match) lets you turn one number — probability
the server wins a service point — into a full match-win probability via closed-form recursions
(O'Malley equations). The literature on this family, all verified:

- **Knottenbelt, Spanias & Madurska (2012)** — the "common-opponent" model: estimate each
  player's serve-point win probability *restricted to opponents both players have faced*
  (removes opposition-quality bias), then propagate to match probability. Reported **3.8% ROI
  over 2,173 ATP matches in 2011** — but this is an early-era backtest; Kovalchik and Wilkens
  both find this model class underperforms regression on 2014+ data, and a careful
  re-implementation (Sipko) earned only 2.40% on 2013–14.
  [Source](https://www.sciencedirect.com/science/article/pii/S0898122112002106)
- **Ingram (2019, JQAS)** — the fix is Bayesian estimation, not a new structure: serve-point win
  probability modeled on the logit scale as server skill − returner skill + surface effect +
  tournament intercept, with skills evolving as Gaussian random walks (fit in Stan with NUTS).
  **68.8% / 0.592** — nearly closes the gap to Elo while keeping point-level interpretability,
  which is what enables in-play pricing and match-duration predictions later.
  [Source](https://martiningram.github.io/papers/bayes_point_based.pdf)
- **Wang & Drekic (2026, Journal of Sports Analytics)** — ensembling Markov methods with a
  head-to-head variant and point-specific modifications reaches ~70% accuracy, "on par with
  machine learning models" (accuracy only; no log-loss/ROI evidence).
  [Source](https://journals.sagepub.com/doi/10.1177/22150218251412670)
- The family's documented weakness (verified 2-1, corroborated by Kovalchik): classic plug-in
  estimation of serve percentages, not the Markov structure itself.

## Published profitability — all selective

| Result | Subset condition | Source |
|---|---|---|
| 3.8% ROI, 2,173 matches (2011) | none (era-specific; decayed since) | Knottenbelt 2012 |
| 4.35–4.4% ROI ANN at Pinnacle odds (2013–14) | **least-uncertain 50% of matches only**; best of 3 staking schemes; 3,183 bets | Sipko 2015 (Imperial thesis) |
| **+3.26% Kelly ROI, 1,903 Pinnacle bets, Jan 2023 – Jun 2025** | **high-intransitivity matchups only** (A beats B beats C beats A patterns); same model betting everything: **−5.49%** | Clegg & Cartlidge, arXiv 2510.20454 (Oct 2025) |

The MagNet graph-network result (verified 3-0 against the full PDF; medium confidence — preprint,
Sharpe 0.61, simulated against closing odds) is the most instructive: Pinnacle remained the
better forecaster overall (69.0% accuracy / 0.196 Brier vs the model's 65.7% / 0.215), yet the
model still made money *on the slice where its structural insight (intransitivity) was relevant*.
Markets are hardest to beat on average and easiest to beat where they're structurally blind.
[Source](https://arxiv.org/pdf/2510.20454)

**Sipko (2015)** is the most-cited applied template (22 engineered features — common-opponent
averaging, surface weighting, time discounting, fatigue proxies — logistic regression + ANN,
OnCourt database): its honest details matter — the ROI is on the *least-uncertain half* of
matches, staking-scheme-dependent (the other two schemes gave 0.70%/2.07%), with log-loss edge
over the Markov benchmark modest (0.611 vs 0.623). Uncertainty-filtered betting is literally the
UFC pipeline's sigma-rubric idea.
[Source](https://www.doc.ic.ac.uk/teaching/distinguished-projects/2015/m.sipko.pdf)

## In-play and momentum: real but small

**Klaassen & Magnus (2001, JASA)** — ~90,000 Wimbledon points 1992–95, dynamic binary panel
model, verified 3-0 across three merged claims: points are *not* independent and identically
distributed — winning the previous point helps win the next (corroborated later at ~7%
next-point boost, ~15% at 30-30/deuce), and servers underperform on high-pressure "important"
points — **but the deviations are small**, so iid-based Markov in-play engines remain a good
approximation. Do not cite momentum as a large exploitable in-play edge; 1990s grass-court data,
and heterogeneity across players exists.
[Source](https://www.researchgate.net/publication/4744107_Are_Points_in_Tennis_Independent_and_Identically_Distributed_Evidence_From_a_Dynamic_Binary_Panel_Data_Model)

## Literature hygiene: the retrospective-accuracy trap

Verified 3-0: **Li et al. (2025, Journal of Big Data)** report "97.5% accuracy" for a Random
Forest + CatBoost ensemble on Grand Slam matches — using point-by-point statistics from 100% of
the completed match. That's classification with hindsight, not forecasting; with only 25% of the
match played it falls to ~71–75%. **Any tennis "prediction" accuracy above ~75% pre-match is
almost certainly leaking in-match or post-match information** — the same lesson as temporal
validity in the UFC pipeline. Treat GitHub repos claiming 90%+ the same way.
[Source](https://journalofbigdata.springeropen.com/articles/10.1186/s40537-025-01216-4)

## Structural soft spots the literature hands us

1. **Sub-top-30 matches** (verified 3-0): bookmaker consensus drops from 76% (top-30 involved)
   to 67%; FiveThirtyEight Elo from 75% to 59–64%. Lower tiers are priced worst — but see doc
   03 for the liquidity/integrity caveats before acting.
2. **Retirements are invisible to academia** (verified, embedded in the Kovalchik finding): the
   canonical benchmarks *exclude* retired matches entirely, and no academic model prices
   retirement risk — while real books settle retirements under different rules. A modeling +
   rules-arbitrage niche nobody publishes on.
3. **Uncertainty-gated betting works in print** (Sipko, MagNet): both profitable results filter
   to the subset where the model knows it knows. The UFC sigma-rubric concept has direct
   published precedent in tennis.

## Caveats on all of the above

All ROI figures are simulated backtests against historical (mostly closing) odds with no
modeling of limits, bet rejection, or the line moving against you. The two headline profitable
results are a master's thesis and an arXiv preprint — deeply verified here, but not
peer-reviewed. Era sensitivity is real: 2011–2014 results live in a softer market than 2026.
The freshest profitable window tested is January 2023 – June 2025 (MagNet).
