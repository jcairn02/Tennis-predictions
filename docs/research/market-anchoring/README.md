# Anchoring on the market: meta-labeling, odds inside the model, and surface ratings

**Status: research, not a decision.** Checked 5 October 2026; every source was accessed that day. Prompted by a professional bettor's remarks: "anchoring on odds and nudging with features"; surface Elo and surface stats matter; shot data is "all end of match stats", and Sackmann "privatized his repo". The project's data analysis is separate.

**Labels:** **Observed** (read in the source; read level in the table), **Author/provider claim** (not checkable), **Inferred** (our reasoning), **Unknown**, **Suggestion** (not a decision).

## In short

* **Observed.** Meta-labeling is a second model, trained on whether a first model's bets paid, that decides *whether and how much* to bet on the first model's side. No sports-betting application was found.
* **Inferred.** "Anchor and nudge" is most naturally a residual model, logit p = logit p_market + f(features): Benter's "second stage", and one-match Black–Litterman. Meta-labeling is a filter and sizer on top. With the same inputs it adds nothing without an "information advantage".
* **Observed.** In tennis, adding a model to sharp odds gained nothing (Clegg and Cartlidge: "The market itself encompasses our model"; Wilkens: no "significant improvement"). **Inferred:** the gains reported elsewhere came against weaker prices (a 1990s tote, soft bookmakers).
* **Observed.** Odds as an input raise accuracy but pull the model onto the bookmaker: correlation with it 0.95, against 0.87 without (NBA; Hubáček and Šír).
* **Observed.** Sackmann blends overall and surface Elo 50/50. **Unknown:** whether prices under-react to surface.
* **Observed.** Sackmann's results repositories have returned 404 since June 2026. Tennis Abstract and his charting repository are still updated. TML continues his ATP format.

## 1. Meta-labeling

* **Observed: López de Prado's *AFML* §3.6–3.8**, quoted verbatim by Singh and Joubert (the book is paywalled).
  * Given a model for the side, you "need to learn the size of that bet, which includes the possibility of no bet at all". The secondary model decides "whether to take the bet or pass"; its probability sets the size.
  * Aims: higher F1 by filtering a high-recall primary's false positives; an ML layer on a "white box" (fundamental) primary; less overfitting "because ML will not decide the side".
* **Observed: Singh and Joubert (Hudson & Thames).** Meta-model inputs are the primary's features plus its prediction; the target is whether the trade hit its profit barrier. On E-mini futures, out-of-sample precision went 0.17→0.20 and 0.48→0.54 (vendor report, one asset).
* **Unknown.** Chapter 10's sizing rule was not read. The form commonly reproduced, size = 2Φ(z) − 1 with z = (p − ½)/√(p(1−p)), is unverified.
* **Observed: abstracts only.** The journal is paywalled.
  * Joubert 2022 tests three components of meta-labeling in a controlled experiment.
  * Thumm, Barucca and Joubert name two of them, "information advantage" and "modeling for false positives". They find ensembles help with "multiple regimes" and nonlinear data.
  * Meyer, Barziy and Joubert: calibration improves "fixed position sizing methods", not sizing methods fitted on training data.
  * Meyer, Joubert and Alfeus: architectures, and "inverse meta-labeling" to improve the side forecasts.
* **Author/provider claim.** Layered on an end-to-end model, meta-labeling gave lower average Sharpe; the meta-model must "extract more information from the existing features than the main one" (Baldisserri). It "cannot create" an edge (Jesse documentation).

## 2. How the odds would enter

| Reading | First model (side) | Meta-model (act, size) | Precedent |
|---|---|---|---|
| Odds as the primary | Bets where a venue's price beats a sharp anchor's fair price | Features choose which to take | Kaunitz (no features) |
| Odds as a meta-feature | Feature model's disagreements with the market | Market probability and the gap as inputs | Benter (fit on all races) |
| Both | As the first row | As the second row | none found |

**Inferred.**
* **The label ignores price.** "Profitable" just means the backed player won, so odds must enter at sizing (expected value = p × odds − 1; fractional Kelly). The 2Φ(z) − 1 rule assumes an even payoff.
* **Fewer rows.** Only candidate bets train it, selected by disagreement with the market.
* **A price-path label exists.** Polymarket positions can be sold before the match, so a closing-line-move label (AFML's triple-barrier analogue) is possible.
* **No new information.** A single model with the same inputs nests the meta-model; gains need new inputs or an act/pass step tuned to profit.

## 3. Does anchoring beat the market?

| Study | Market's role | Result as reported | Read |
|---|---|---|---|
| Benter 1994; racing, 2,313 races | Logit on the logs of the model and public probabilities | Pseudo-R²: public 0.1237, model 0.1016, combined 0.1327; tipsters add 0.0002. Years of profit: **author/provider claim** | full |
| Franck, Verbeek, Nüesch 2010; football, 5,478 games | Probit on the bookmaker probability plus the exchange/bookmaker ratio | Ratio significant everywhere; a gap-betting rule gave above-average, sometimes positive returns | full |
| Kaunitz et al. 2017; football, 479,440 games | Consensus minus 0.05 taken as truth; bet the outlying prices | +3.5% (56,435 closing bets); +9.9% (6,994, minute odds); +6.2% live and paper (672); accounts "severely" limited | full |
| Hubáček, Šír 2020; NBA, 9,093 games | Odds as an input or not; loss MSE − φ(t−m)² | Accuracy 68.80% with odds, 67.62% without (bookmaker about 69%). Without odds earned more at 5 of 6 φ under the Sharpe strategy (best 1.74 vs 1.49) | full |
| Wilkens 2021; ATP and WTA | Machine learning with market information | "most of the relevant information is embedded in the betting markets"; returns "mainly negative" | abstract |
| Candila, Palazzo 2020; ATP, 9,818 test matches | Bet365 Shin probability as an input | −1.63% ROI on favourites; positive only in subsets (+10.41% on 493 bets), at the best odds across books | full |
| Lisi, Zanella 2017; 501 Slam matches | Odds used only when the ranking favourite is priced above 2.0 | +15.9% (abstract) vs 16.3% (text) | full |
| Vaughan Williams et al. 2021; Slams | Odds, Elo and surface Elo averaged, weights fit in-sample | Brier-optimal weight on odds at Wimbledon: 86.1% ATP, 79.9% WTA | full |
| Clegg, Cartlidge 2026 (v2); test 2023–25 | Logit combination with recalibrated Pinnacle | Brier: model 0.214, Pinnacle 0.198; "no Brier-score improvement". v1's 3.26% ROI is gone from v2 | full |
| Ramirez et al. 2023, and correction; WTA | Wikipedia "buzz" signal | Claimed 17–29% ROI; replication: "the majority of reported profits disappear" | full / abstract |
| Goto et al. 2026; football, 90,014 matches | One-parameter favourite–longshot fit | Beats GLMs using odds "as raw input data" | full |

**Also read.** Spann and Skiera: combined forecasts were more accurate, but unprofitable after a 25% fee. Lyócsa and Výrost: 40 tennis betting rules lose their edge after data-snooping correction. Walsh and Joshi (one NBA season): selecting by calibration gave +34.69% ROI, by accuracy −35.17%.

**Inferred.** Gains come against weak prices; against a sharp tennis close, the one direct test shows none. Nothing here tests meta-labeling.

## 4. Odds as a feature, or decorrelation?

* **Observed: for odds as a feature.**
  * The market holds most of the information (Wilkens; Kovalchik 2016 in the [rating-systems note](../rating-systems/README.md)).
  * A model given odds learns their miscalibration (Goto et al.).
  * Its added value can be tested by encompassing (Franck et al.; Clegg and Cartlidge).
* **Observed: for decorrelation.** A copy of the market only pays the margin. Hubáček and Šír show decorrelation helps when the model is no better than the market, and "breaks down severely" when the market is the more biased.
* **Inferred.** An offset model is the middle path. Its f(x) is fit only to what the market leaves unexplained, so it cannot collapse onto the price.

## 5. Black–Litterman

* **Observed (PyPortfolioOpt).** The posterior is "a weighted average between the prior estimate of returns and the views", weighted by confidence (Ω) and τ. The 1992 and 1999 originals were not read.
* **Inferred.** For one match, prior = market logit and view = model logit, so the posterior is their precision-weighted average; Benter's α and β are those weights fitted by maximum likelihood. Fitted so far: 80–86% on the odds in-sample (Vaughan Williams et al.); in effect all of it against Pinnacle, where adding the model gained nothing (Clegg and Cartlidge).

## 6. How calibrated are tennis odds?

* **Author/provider claim (Pinnacle).** ATP closing prices 2007–2018 have a calibration slope of 0.994. No decile is profitable, and there is no favourite–longshot bias once the margin is allowed for.
* **Observed (Pinnacle article, tipster "Nishikori").** Margin removal on 33,270 ATP closing lines since 2010 leaves yields of −1.58% (equal split), −0.42% (proportional to odds) and −0.26% (odds ratio).
* **Observed: softer prices show a favourite–longshot bias.**
  * Forrest and McHale 2007: "throughout the range of odds".
  * Lahvička 2014: 44,871 Bet365 matches; outcome = −0.0293 + 1.0594 × implied probability; stronger for low-ranked players, later rounds and big events.
  * Abinzano et al. 2016: the same pattern on exchanges.
* **Author/provider claim (Pinnacle).** "Beat the closing line by 10% and you should expect to make a profit over turnover of 10%."

## 7. Surface

* **Observed (Sackmann 2019).** Four ratings: overall, hard (indoor included), clay, grass; a surface rating "threw away results on every other surface". Forecasts use "a 50/50 blend": "my testing showed that 50/50 worked for each surface". The Elo page (28 September 2026) labels the blends hElo, cElo, gElo.
* **Observed (Sackmann 2017).** About 50,000 ATP matches, 2000–17.

  | Brier score | Overall Elo | Surface-only Elo | 50/50 blend |
  |---|---|---|---|
  | Hard | 0.205 | 0.202 | 0.202 |
  | Clay | 0.211 | 0.213 | 0.207 |
  | Grass | 0.207 | 0.207 | 0.196 |

  * "differences between, say, 60/40 and 50/50 are extremely small on all surfaces".
  * For comparison, betting odds scored 0.189 in 2016.
  * **Inferred:** the blend was tuned on the same matches it was scored on.
* **Observed.**
  * Vaughan Williams et al.: the in-sample optimal surface share (ATP, grass) is 13% for accuracy, 43% for Brier, 100% for calibration.
  * Lisi and Zanella: a preferred-surface dummy was insignificant.
  * Ingram 2019 (ATP 2014): serve and return skills by surface reached 68.8% accuracy and 0.592 log loss, against 66.3% and 0.641 for earlier point-based models.
  * The [rating-systems note](../rating-systems/README.md): surface is the most consistent rating extension, but no rating beats the market.
* **Unknown: do prices reflect surface?**
  * No test by surface was found.
  * The favourite–longshot studies split by rank, round and event, not surface.
  * Blogs claiming slow pricing at surface switches show no data (**author/provider claim**).

## 8. Sackmann's data

* **Observed: what the stats are.** One row per match (surface, round, score, minutes, ranks) with each player's end-of-match `ace, df, svpt, 1stIn, 1stWon, 2ndWon, SvGms, bpSaved, bpFaced`. The Match Charting Project adds shot-by-shot charts of volunteer-chosen matches.
* **Observed: status.**
  * `tennis_atp`, `tennis_wta` and `tennis_slam_pointbypoint` return 404 (API and web). The one public repository left is `tennis_MatchChartingProject`, last commit 18 September 2026.
  * Wayback: `tennis_atp` live 14 March 2026, 404 on 22 June. Earlier project lanes date the removal to 8 May–16 June (Software Heritage).
  * Tennis Abstract's Elo tables are dated 28 September 2026.
* **Inferred.** GitHub returns 404 for private and deleted repositories alike, so "privatized" cannot be confirmed. "Isn't doing them anymore" fits the public CSVs, not his site or charting.
* **Unknown.** The reason; no statement was found. A third-party issue (20 September) only logs the 404s. The charting README's warning, "If violations continue, I may stop updating the repo entirely", dates from 2022 or earlier.
* **Observed: alternatives.**
  * TML's `2026.csv` has Sackmann's columns plus `indoor`: 2,419 rows to 29 September, 2,372 with serve statistics.
  * **Author/provider claim:** TML covers ATP from 1968, Challenger, qualifying, and WTA from 1990, without "the same 100% reliability" for the WTA.
  * Its licence is inconsistent: the site says MIT; the README says "non-commercial unless explicitly permitted".
  * `Aneeshers/tennis-sackmann-archive` is a frozen June 2026 mirror.
  * More sources are in the [source register](../tennis-data-audit/source-register.md).

## 9. Suggestions (not decisions)

1. **Suggestion: make the anchored model the baseline.** Recalibrate the market (logit p = a + b·logit p_market), fit features as a residual f(x), and score out-of-sample log loss against the recalibrated market with an encompassing or Diebold–Mariano test. Only then simulate bets at executable Polymarket prices.
2. **Suggestion: use meta-labeling only as a second stage.** Try it once a residual shows information beyond the market. Size bets by price, and compare win labels with closing-line-move labels.
3. **Suggestion: tune the surface blend walk-forward.** Then test whether surface ratings and surface serve and return statistics explain the market's residual, especially at surface switches.
4. **Suggestion: record the anchor.** Note whether it is a sharp bookmaker's price or Polymarket's own. The gap between them is itself a signal (Kaunitz).

## 10. Limits

Abstract only: the meta-labeling journal papers, Wilkens, Spann and Skiera, Lyócsa and Výrost, Forrest and McHale, Ingram, Hubáček et al. 2019. Not read: *AFML* itself, the Black–Litterman originals, Štrumbelj 2014. Most profit figures are backtests at best-of-many or soft prices. No source covers Polymarket tennis, and no tennis professional's published "start from the price" method was found (**Unknown**).

## Sources

All accessed 2026-10-05.

| Source | URL | Read |
|---|---|---|
| *AFML* §3.6–3.8, quoted by Singh & Joubert 2019 | hudsonthames.org/wp-content/uploads/2022/04/Does-Meta-Labeling-Add-to-Signal-Efficacy.pdf | full |
| Joubert 2022, *JFDS* | doi.org/10.3905/jfds.2022.1.098 | abstract |
| Meyer, Barziy, Joubert 2023, *JFDS* | doi.org/10.3905/jfds.2023.1.119 | abstract |
| Thumm, Barucca, Joubert 2023, *JFDS* | discovery.ucl.ac.uk/id/eprint/10169066 | abstract |
| Meyer, Joubert, Alfeus 2022, *JFDS* | doi.org/10.3905/jfds.2022.1.108 | abstract |
| Baldisserri (forum) | quantconnect.com/forum/discussion/14706 | full |
| Jesse documentation | docs.jesse.trade/docs/research/ml/meta-labeling | full |
| Benter 1994 | gwern.net/doc/statistics/decision/1994-benter.pdf | full |
| Spann & Skiera 2009 | doi.org/10.1002/for.1091 | abstract |
| Franck, Verbeek, Nüesch 2010 | unifr.ch/tim/en/assets/public/uploads/Publication%20list/2010/IJoF_Franck_Verbeek_Nuesch.pdf | full |
| Kaunitz, Zhong, Kreiner 2017 | arxiv.org/abs/1710.02824 | full |
| Hubáček, Šourek, Železný 2019, *IJF* | ideas.repec.org/a/eee/intfor/v35y2019i2p783-796.html | abstract |
| Hubáček & Šír 2020 | arxiv.org/abs/2010.12508 | full |
| Wilkens 2021 | doi.org/10.3233/JSA-200463 | abstract |
| Candila & Palazzo 2020 | doi.org/10.3390/risks8030068 | full |
| Lisi & Zanella 2017 | doi.org/10.1285/i20705948v10n3p790 | full |
| Vaughan Williams et al. 2021 | irep.ntu.ac.uk/id/eprint/42038 | full (accepted manuscript) |
| Clegg & Cartlidge 2026 | arxiv.org/abs/2510.20454 | full (v1, v2) |
| Ramirez, Reade, Singleton 2023 | carlsingletoneconomics.com/uploads/4/2/3/0/42306545/tennis_rrs.pdf | full |
| Clegg & Cartlidge, correction | arxiv.org/abs/2306.01740 | abstract |
| Lyócsa & Výrost 2017 | doi.org/10.1080/00036846.2017.1394973 | abstract |
| Goto, Takeishi, Yairi 2026 | arxiv.org/abs/2604.17194 | full |
| Walsh & Joshi 2024 | doi.org/10.1016/j.mlwa.2024.100539 | abstract |
| Forrest & McHale 2007 | doi.org/10.1080/13518470701705736 | abstract |
| Lahvička 2014 (working paper) | mpra.ub.uni-muenchen.de/47905 | full |
| Abinzano, Muga, Santamaría 2016 | doi.org/10.1080/13504851.2015.1093074 | abstract |
| Pinnacle: ATP market efficiency | pinnacle.com/betting-resources/en/Tennis/how-efficient-is-the-atp-tennis-betting-market/URU25K89X26GMH62 | full |
| Pinnacle: true odds in tennis | pinnacle.com/betting-resources/en/tennis/how-to-estimate-the-true-odds-in-tennis/q6e22qnbj3ltzjq7 | full |
| Pinnacle: closing line | pinnacle.com/betting-resources/en/betting-strategy/using-the-closing-line-to-test-your-skill-in-betting/7e6jwjm5ykejuwkq | full |
| PyPortfolioOpt, Black–Litterman | pyportfolioopt.readthedocs.io/en/latest/BlackLitterman.html | full |
| Black & Litterman 1992; He & Litterman 1999 | ssrn.com/abstract=334304 | not read |
| Sackmann 2019 | tennisabstract.com/blog/2019/12/03/an-introduction-to-tennis-elo/ | full |
| Sackmann 2017 | tennisabstract.com/blog/?p=2339 | full |
| Tennis Abstract Elo ratings | tennisabstract.com/reports/atp_elo_ratings.html | full |
| Ingram 2019, *JQAS* | doi.org/10.1515/jqas-2018-0008 | abstract |
| GitHub API, JeffSackmann | api.github.com/users/JeffSackmann/repos | checked |
| Wayback CDX, `tennis_atp` | web.archive.org/cdx/search/cdx?url=github.com/JeffSackmann/tennis_atp | checked |
| Match Charting Project README | github.com/JeffSackmann/tennis_MatchChartingProject | full |
| FirstData issue 238 | github.com/MLT-OSS/FirstData/issues/238 | full |
| TML database and README | stats.tennismylife.org/tennis-match-database; github.com/Tennismylife/TML-Database | full; 2026.csv checked |
