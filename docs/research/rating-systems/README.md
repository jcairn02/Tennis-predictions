# Rating systems for tennis: what the published evidence says about Glicko, TrueSkill and the alternatives to Elo

**Status: research, not a decision.** Literature checked on 2 October 2026; every source below was accessed that day. Two sweeps were run: one of tennis studies, one of the algorithms' primary specifications and of comparisons in other sports. Where only an abstract could be read, the table says so. The project's own test of these systems is the study [rating systems against Elo](../../studies/rating_systems/README.md). This page is what others report.

Labels: **reported** is what a source states, **inferred** is our reading, **unknown** is what no source settles, **suggestion** is a proposal.

## In short

* **Reported. No peer-reviewed tennis study compares Glicko-2 with Elo.** The only tennis comparison found is an undergraduate project, where Glicko-2 ties Elo and Glicko (S37).
* **Reported. Glicko-1 ties Elo in tennis.**
  * ATP 2018–2019: Glicko 63.5% accuracy and mean log-likelihood −0.633, against Elo 63.7% and −0.632 (Ingram 2021, abstract).
  * WTA 2022: Glicko 0.636, Elo 0.636 log loss (Duffield, Power and Rimella 2024).
  * ATP 2018: Glicko 0.635–0.637, Elo 0.638–0.639 (Ingram 2019 preprint).
  * Jeff Sackmann (Tennis Abstract): he "tinkered with Glicko… without much success" (blog).
* **Reported. TrueSkill ties or slightly beats a constant-K Elo.** Same ATP data (1991–2017, all levels, last 30% as the test):
  * Maystre et al. 2019: TrueSkill 0.563, Elo 0.563 log loss.
  * Landfried and Mocskos 2025: TrueSkill about 0.558.
* **Reported. The largest gains over Elo come from smoothing systems.** These re-estimate a player's whole history as later results arrive, crediting an old win at what the opponent later proved to be worth:
  * TrueSkill Through Time (TTT) about 0.552 and KickScore 0.552, against Elo 0.563 on the same test: about 0.011 nats per match better.
  * Measured only against a **constant-K** Elo without a surface model, and never against betting odds.
* **Reported. Surface is the most consistent extension.**
  * A surface-specific dynamic model beats the same model without surface: 0.578 against 0.584 log loss, ATP 2015–2017 (Gorgi, Koopman and Lit 2019).
  * Surface correlations implied by the data: 0.72–0.81 (Ingram 2019) and 0.90 (Leonelli 2026).
  * One dissent: Landfried and Mocskos find surface factors unneeded for the ATP as a whole.
* **Reported. No study shows any rating beating the betting market.**
  * Bookmakers lead in every study that measures them: Kovalchik 2016 (0.55 against Elo's 0.59), Gorgi et al. 2019, Clegg and Cartlidge (Pinnacle).
  * None tests whether a rating adds information to closing odds.
  * Reported betting profits rest on choosing the best of 11 bookmakers, thresholds set after the fact, or selected subsets.
* **Inferred. A well-tuned Elo is already near the published frontier for results-only ratings.**
  * The Bayesian filters (Glicko, TrueSkill, Kalman) are Elo with an uncertainty per player. An Elo whose K falls with matches played captures most of that: in chess, the games-played K recovers about 92% of Glicko's gain over a constant K (our arithmetic on Stephenson 2012's deviances: 90.131, 90.030, 90.021).
  * What a tuned Elo cannot imitate is smoothing, and that is untested against a tuned Elo.

## The systems, briefly

| System | What it is | Key reference |
|---|---|---|
| **Elo** | One rating per player, moved after each match by K × (result − expected). FiveThirtyEight's tennis form lets K fall with matches played: K = k0 / (n + offset)^shape | Elo 1978; FiveThirtyEight; Kovalchik 2016 |
| **Glicko (Glicko-1)** | Elo with a rating deviation (RD) per player. RD shrinks with games and grows with time out; results against uncertain opponents count less; forecasts are pulled toward 50% when either player is uncertain. Results are processed in rating periods | Glickman 1999 (S40); glicko.pdf |
| **Glicko-2** | Glicko plus a volatility per player that learns how erratic a player is; τ controls how fast it moves. Glickman advises periods with at least 10–15 games per player on average | Glickman 2001; glicko2.pdf (2022 revision) |
| **TrueSkill** | Gaussian skill (mean, variance) with a probit link: the winner had the higher performance, performance = skill + noise. Exact moment matching for two players; dynamics add variance before each game | Herbrich, Minka and Graepel 2007 |
| **TrueSkill Through Time (TTT)** | The TrueSkill model over the whole history at once: a Gaussian random walk per player, solved by expectation propagation forward and backward in time | Dangauthier et al. 2008; Landfried and Mocskos 2025 |
| **KickScore, Whole-History Rating** | Other smoothing models: Gaussian-process (KickScore) and Wiener-process Bradley–Terry (WHR) dynamics | Maystre et al. 2019; Coulom 2008 |
| **Kalman-filter view** | Elo is the steady state of a Kalman filter on skills; Glicko and TrueSkill are its approximations with per-player variance | Ingram 2021; Szczecinski and Tihon 2023 |
| **Margin-of-victory Elo** | Updates scaled by games or sets won (WElo, Kovalchik's MOV Elo) | Angelini et al. 2022; Kovalchik 2020 |

## Direct evidence in tennis

| Study | Data and test | Systems | Result (as reported) | Read |
|---|---|---|---|---|
| Kovalchik 2016, *JQAS* (S2) | ATP 2014, 2,395 matches | 11 models incl. FiveThirtyEight Elo, Bradley–Terry; bookmaker consensus | Log loss: bookmakers 0.55, Elo (career) 0.59, Bradley–Terry 0.65–0.67. States Glicko and TrueSkill "have yet to be applied in tennis" | full |
| Ingram 2021, *JQAS* (S5) | Men, test 2018–2019 | Elo, Glicko, Bayesian extensions (margin, correlated surfaces, level) | Best extension 65.8%, mean log-likelihood −0.615; Elo 63.7%, −0.632; Glicko 63.5%, −0.633 | abstract |
| Ingram 2019, arXiv (S11) | ATP tour level 2018, 2,623 matches | Elo, Glicko, Gaussian-process models | Log loss: GP with surface 0.631, GP 0.634, Glicko 0.635–0.637, Elo 0.638–0.639; surface correlations 72–81% | full |
| Duffield, Power and Rimella 2024, *JRSS C* (S15) | WTA tour level, test 2022 | Elo, Glicko, extended Kalman, HMM, SMC, TrueSkill2-type | Elo 0.636, Glicko 0.636, Kalman 0.635, HMM 0.636, SMC 0.639, TrueSkill2 0.668: "all models broadly perform quite similarly" | full |
| Maystre, Kristof and Grossglauser 2019, KDD (S10) | ATP 1991–2017, 618,934 matches (all levels), last 30% as test | Constant, Elo, TrueSkill, KickScore | Log loss 0.581 / 0.563 / 0.563 / 0.552; accuracy 68.9 / 70.5 / 70.5 / 71.4% | full |
| Landfried and Mocskos 2025, *J. Stat. Software* (S9) | The same, 186,361 test matches | TrueSkill, TTT (Elo and KickScore copied from S10) | Geometric mean of probabilities 0.5722 (TrueSkill) and 0.5760 (TTT), i.e. log loss about 0.558 and 0.552; surface factors vanish at the evidence's maximum for the ATP as a whole | full |
| Hua, Chang, Lin and Weng 2024, *IJF* (S14) | ATP 2018–2019, 5,100 matches | Elo with and without variance updates, surface models | Accuracy: constant-variance Elo 63.4%, variance-updated 63.8–63.9%; surface model 64.5%, with variance updates 64.9% (not significant once surface is modelled). Test log loss not reported | arXiv v1 |
| Yue et al. 2022, *PLoS ONE* (S13) | Grand Slams 2000–2019 | Glicko as features in a logistic regression | ATP accuracy: ranking 72.4%, Glicko 73.4%, Glicko by court 73.8%; no Elo | full |
| Gorgi, Koopman and Lit 2019, *JRSS A* (S6) | ATP tour level, test 2015–Feb 2017 | Dynamic Bradley–Terry (score-driven), surface and age versions; bookmakers | Log loss: bookmakers 0.557; Elo-like model 0.584; surface 0.578; ATP points 0.603; McHale–Morton Bradley–Terry 0.610. Bookmakers significantly better | full |
| Arcagni, Candila and Grassi 2023, *Ann. Oper. Res.* (S16) | 1000s and Slams only, 2016–2020 | Eigenvector centrality ("B-score"), Elo, MOV Elo, Bradley–Terry | Men 0.573 (B-score) against Elo 0.601; but Elo was fed top-tier matches only | full |
| Angelini, Candila and De Angelis 2022, *EJOR* (S3) | ATP 2012–2020, WTA 2013–2020 | WElo (games-weighted), Elo, others | WElo 78.2% against Elo 77.9% accuracy; profits only at the best of 11 bookmakers. **Contested** (below) | full |
| Clegg and Cartlidge, arXiv 2025/26 (S29) | ATP and WTA tour level, 2022–Oct 2025, 12,052 matches | Graph network, WElo, Elo, Bradley–Terry; Pinnacle | Brier: Pinnacle 0.198, network 0.214, WElo 0.217, Elo 0.217, Bradley–Terry 0.219 | partial |
| Undergraduate project, Imperial College (S37, grey) | ATP 2017, random cross-validation | Elo, Glicko, Glicko-2 | Fold log-likelihood −241.22, −241.34, −241.35 (not walk-forward) | key sections |

## Which system is most predictive, and how strong the evidence is

* **Reported.** Each study names a different winner: bookmakers then FiveThirtyEight Elo (Kovalchik), an extended Bayesian Elo (Ingram), a surface state-space model (Gorgi), TTT and KickScore (Landfried; Maystre), a tie (Duffield), WElo (Angelini), an eigenvector score on a restricted sample (Arcagni).
* **Inferred.** No study ranks the candidates on common data. The tests are mostly ATP tour level, one or two seasons, with a different Elo in every paper and few significance tests. Taken together:
  * The uncertainty machinery of Glicko and TrueSkill adds little once Elo's K falls with matches played.
  * Smoothing (TTT, KickScore, WHR) is the one mechanism with a clear published gain, about 0.011 nats over a constant-K Elo. Its gain over a tuned, surface-blended Elo is **unknown** and probably smaller.
  * A surface model helps in most tennis studies.
* **Inferred.** The best published results-only forecasts close about 72% (Kovalchik 2016) to 85% (Gorgi et al. 2019) of the distance from a coin to the bookmakers, by our arithmetic on their log losses. The project's surface Elo closes 78–82% on its matches with odds, so it already sits inside that range.

## Extensions that help in tennis

| Extension | Evidence | Size and caveats |
|---|---|---|
| **Surface** (separate, blended or correlated ratings) | Gorgi 2019 (0.584 → 0.578); Ingram 2019 (0.634 → 0.631); Hua 2024 (+1.1 points accuracy); Leonelli 2026 (correlation 0.90); Tennis Abstract blog (Brier better on grass and hard) | Most consistent. Against: Landfried and Mocskos (unneeded overall), Vaughan Williams et al. 2021 (plain Elo best for women) |
| **Margin of victory** | Kovalchik 2020 (every within-set margin improved Elo; size not seen); Ingram 2021 (part of the combined gain) | Small or absent in re-tests: Arcagni 2023 (0.001–0.004), Bunker et al. 2024 and Clegg and Cartlidge (WElo ≈ Elo). Uses scores, so it overlaps with point-based features |
| **Uncertainty or a K that falls with matches** | Kovalchik 2016 (more history helps); Hua 2024 (variance updates help without surface) | No tennis test of a falling K against a constant K; Glicko ≈ Elo. Chess: the falling K recovers about 92% of Glicko's gain (our arithmetic on Stephenson 2012) |
| **Inactivity** | Tennis Abstract blog 2018: pre-layoff Elo overrates returning players by about 25%; a penalty improves Brier on about 500 first matches back | Grey literature, in-sample |
| **Best of five** | Gorgi 2019: a set-based likelihood gains 0.001; no extra Grand Slam effect once the format is modelled | — |

## Other sports

| Study | Sport | Result (as reported) |
|---|---|---|
| Stephenson 2012 (FIDE/Deloitte data) | Chess, about 1.8M games | Scaled deviance on a 2007 holdout: Glicko 90.021, Elo with K by games played 90.030, Elo with a constant K 90.131 |
| Coulom 2008, Whole-History Rating | Go (KGS), 2.3M test games | Accuracy: Elo 55.121%, Glicko 55.522%, TrueSkill 55.536%, Bayeselo 55.671%, WHR 55.793% |
| Glickman, Hennessy and Bent 2018 | Beach volleyball, 12,241 matches | Log loss ×10⁴: Elo 2652.55, Glicko 2623.03, Glicko-2 2622.08 (tuned and tested on the same window) |
| Szczecinski and Tihon 2023, *JQAS* | NHL, Premier League, NFL | A Kalman filter equals Elo to 0.001–0.002 log-score |
| Maystre et al. 2019 | NBA, football, chess | Elo / TrueSkill / KickScore log loss: NBA 0.634 / 0.634 / 0.630; football 0.950 / 0.937 / 0.926; chess 1.035 / 1.030 / 1.026 |
| Weng and Lin 2011, *JMLR* | Halo 2 head-to-head | Error: Bradley–Terry 32.53%, Thurstone–Mosteller 32.41%, TrueSkill 32.44%, Glicko 33.88% |

**Inferred.** Across sports, a well-tuned Elo, Glicko, Glicko-2 and TrueSkill sit within a few thousandths of log loss of each other. Glicko-2's volatility adds almost nothing over Glicko (volleyball: 2622.08 against 2623.03). Smoothing and richer models give the larger gains.

## What this implies for the project (suggestions)

* **Suggestion. Test, don't assume.** The published Elo baselines are weaker than the project's tuned surface Elo, so the published gains cannot be transferred. The [study](../../studies/rating_systems/README.md) tunes Glicko-2, Glicko-1, TrueSkill, correlated-surface ratings and a causal TTT exactly as Elo was tuned, and scores them with the same walk-forward test.
* **Suggestion. Run Glicko-2 match by match.** A tennis player plays one to five matches a week, far below Glickman's 10–15 games per period. Leonelli (2026) notes the same problem with Glicko's single update step.
* **Suggestion. Don't expect any rating to add to the closing odds.** No published study shows it; the study tests it.

## Conflicts and unverified points

1. **WElo's accuracy** (Angelini et al. 2022): Elo and WElo near 78–82% would beat the market by about 9 points, which is implausible.
   * Bunker et al. 2024, with the same data and R package, find 63–71%.
   * Our reading: the package drops players with fewer than 10 matches across the whole dataset, which is a look-ahead filter. Not verified.
2. **TrueSkill on the same ATP data:** 0.563 in Maystre et al., about 0.558 in Landfried and Mocskos. Unexplained.
3. **Surface:** Landfried and Mocskos (unneeded overall) conflict with Gorgi, Ingram, Hua, Leonelli and the Tennis Abstract blog.
4. **Read at abstract level only:**
   * Ingram 2021 (no equations seen)
   * Kovalchik 2020
   * McHale and Morton 2011
   * Baker and McHale 2014, 2017
   * Wilkens 2021
   * Boulier and Stekler 1999; del Corral and Prieto-Rodríguez 2010; Clarke and Dyte 2000; Irons et al. 2014
5. **Different versions:** Hua et al. read as arXiv v1 (test accuracy only); Szczecinski and Tihon as arXiv v1.
6. **Grey literature:** student projects, blogs and commercial sites are labelled as such and are not evidence of a measured gain.
7. **Odds sources differ** across papers (best of 11 books, average, Bet365, Oddschecker, Pinnacle with opening or closing unstated). None is a closing-line test of a rating.

## Sources

All accessed 2 October 2026. "Full" means the full text was read; "abstract" means only the abstract.

| # | Source | Link | Type | Read |
|---|---|---|---|---|
| S1 | Vaughan Williams, Liu, Dixon and Gerrard (2021), How well do Elo-based ratings predict professional tennis matches? *JQAS* 17(2):91–105 | doi:10.1515/jqas-2019-0110; accepted manuscript irep.ntu.ac.uk/id/eprint/42038 | journal | full (AM) |
| S2 | Kovalchik (2016), Searching for the GOAT of tennis win prediction, *JQAS* 12(3):127–138 | doi:10.1515/jqas-2015-0059 | journal | full |
| S3 | Angelini, Candila and De Angelis (2022), Weighted Elo rating for tennis match predictions, *EJOR* 297(1):120–132 | doi:10.1016/j.ejor.2021.04.011; hdl.handle.net/11585/821483 | journal | full (AM) |
| S4 | Kovalchik (2020), Extension of the Elo rating system to margin of victory, *IJF* 36(4):1329–1341 | doi:10.1016/j.ijforecast.2020.01.006 | journal | abstract |
| S5 | Ingram (2021), How to extend Elo: a Bayesian perspective, *JQAS* 17(3):203–219 | doi:10.1515/jqas-2020-0066; code github.com/martiningram/jax_elo | journal | abstract |
| S6 | Gorgi, Koopman and Lit (2019), The analysis and forecasting of tennis matches by using a high dimensional dynamic model, *JRSS A* 182(4):1393–1409 | doi:10.1111/rssa.12464 | journal | full |
| S7 | McHale and Morton (2011), A Bradley–Terry type model for forecasting tennis match results, *IJF* 27(2):619–630 | doi:10.1016/j.ijforecast.2010.04.004 | journal | abstract |
| S8 | Baker and McHale (2014) *EJOR* 236(2):677–684; (2017) *EJOR* 258(1):328–333 | doi:10.1016/j.ejor.2013.12.028; doi:10.1016/j.ejor.2016.08.043 | journal | abstract |
| S9 | Landfried and Mocskos (2025), TrueSkill Through Time, *J. Stat. Software* 112(6) | doi:10.18637/jss.v112.i06 | journal | full |
| S10 | Maystre, Kristof and Grossglauser (2019), Pairwise comparisons with flexible time-dynamics (KickScore), KDD '19, 1236–1246 | doi:10.1145/3292500.3330831; arXiv:1903.07746 | conference | full |
| S11 | Ingram (2019), Gaussian process priors for dynamic paired comparison modelling | arXiv:1902.07378 | preprint | full |
| S12 | Ingram (2019), A point-based Bayesian hierarchical model to predict the outcome of tennis matches, *JQAS* 15(4):313–325 | doi:10.1515/jqas-2018-0008 | journal | full |
| S13 | Yue, Chou, Hsieh and Hsiao (2022), *PLoS ONE* 17(4):e0266838 | doi:10.1371/journal.pone.0266838 | journal | full |
| S14 | Hua, Chang, Lin and Weng (2024), *IJF* 40(3):1152–1165 | doi:10.1016/j.ijforecast.2023.10.004; arXiv:2310.10386 | journal | arXiv v1 |
| S15 | Duffield, Power and Rimella (2024), *JRSS C* 73(5):1262–1282 | doi:10.1093/jrsssc/qlae035; arXiv:2308.02414 | journal | full (arXiv v3) |
| S16 | Arcagni, Candila and Grassi (2023), *Ann. Oper. Res.* 325(1):615–632 | doi:10.1007/s10479-022-04594-7 | journal | full |
| S17 | Radicchi (2011), Who is the best player ever? *PLoS ONE* 6(2):e17249 | doi:10.1371/journal.pone.0017249 | journal | full (summary) |
| S18 | Dingle, Knottenbelt and Spanias (2012), On the (Page)Ranking of professional tennis players | eprints.maths.manchester.ac.uk/1845 | workshop | full |
| S19 | Bozóki, Csató and Temesi (2016), *EJOR* 248(1):211–218 | doi:10.1016/j.ejor.2015.06.069 | journal | abstract |
| S20 | Motegi and Masuda (2012), *Sci. Rep.* 2:904 | doi:10.1038/srep00904 | journal | partial |
| S21–S24 | Boulier and Stekler (1999) *IJF* 15(1); del Corral and Prieto-Rodríguez (2010) *IJF* 26(3); Clarke and Dyte (2000) *ITOR* 7(6); Irons, Buckley and Paulden (2014) *JQAS* 10(2) | doi:10.1016/S0169-2070(98)00067-3; doi:10.1016/j.ijforecast.2009.12.006; doi:10.1111/j.1475-3995.2000.tb00218.x; doi:10.1515/jqas-2013-0101 | journal | abstract |
| S25 | Wilkens (2021), Sports prediction and betting models in the machine learning age: the case of tennis, *J. Sports Analytics* 7(2):99–117 | doi:10.3233/JSA-200463 | journal | abstract |
| S28 | Bunker, Yeung, Susnjak, Espie and Fujii (2024), *Proc. IMechE P* 238(4):305–316 | doi:10.1177/17543371231212235 | journal | full (AM) |
| S29 | Clegg and Cartlidge, graph neural networks for tennis prediction | arXiv:2510.20454v2 | preprint | partial |
| S30 | Leonelli (2026), How exceptional was the Big Three era? | arXiv:2608.27362 | preprint | partial |
| S36 | Sackmann (2018), Handling injuries and absences with tennis Elo | tennisabstract.com/blog/2018/05/15/handling-injuries-and-absences-with-tennis-elo/ | blog | full |
| S37 | Paired comparison models (Imperial College year-2 project) | matsagad.com/files/papers/Paired_Comparison_Models.pdf | student report (grey) | key sections |
| S40 | Glickman (1999), Parameter estimation in large dynamic paired comparison experiments, *Appl. Statist.* 48(3):377–394 (a tennis example: ATP 1986–95, 33,359 matches) | doi:10.1111/1467-9876.00159; glicko.net/research/glicko.pdf | journal | full |
| S41 | Glickman, The Glicko system; Example of the Glicko-2 system (revised 22 March 2022) | glicko.net/glicko/glicko.pdf; glicko.net/glicko/glicko2.pdf | specification | full |
| S42 | Glickman (2001), Dynamic paired comparison models with stochastic variances, *J. Appl. Stat.* 28(6):673–689 | doi:10.1080/02664760120059219 | journal | full |
| S43 | Herbrich, Minka and Graepel (2007), TrueSkill: a Bayesian skill rating system, NIPS 19 | proceedings.neurips.cc (2006 paper f44ee263952e65b3610b8ba51229d1f9) | conference | full |
| S44 | Dangauthier, Herbrich, Minka and Graepel (2008), TrueSkill Through Time, NIPS 20 | microsoft.com/en-us/research/wp-content/uploads/2008/01/NIPS2007_0931.pdf | conference | full |
| S45 | Coulom (2008), Whole-History Rating, Computers and Games, LNCS 5131 | doi:10.1007/978-3-540-87608-3_11; remi-coulom.fr/WHR/WHR.pdf | conference | full (draft) |
| S46 | Weng and Lin (2011), A Bayesian approximation method for online ranking, *JMLR* 12:267–300 | jmlr.org/papers/volume12/weng11a/weng11a.pdf | journal | full |
| S47 | Szczecinski and Tihon (2023), Simplified Kalman filter for online rating, *JQAS* 19(4):295–315 | doi:10.1515/jqas-2021-0061; arXiv:2104.14012 | journal | arXiv v1 |
| S48 | Stephenson (2012), the FIDE/Deloitte chess-rating challenge entry | englishchess.org.uk (PDF) | competition write-up | full |
| S49 | Glickman, Hennessy and Bent (2018), *Statistica Applicata* (beach volleyball) | — | journal | full |

S26, S27 and S31–S35 (machine learning against bookmakers, market biases, a commercial site) were read for context and do not bear on the choice of rating system; S38–S39 (theses' abstract pages, commercial sites) were not usable as evidence.
