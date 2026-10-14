# Lane L2 report (scoring structure, luck and psychology), as returned by the subagent on 13 Oct 2026

Verbatim copy of the subagent's final message (brief: `subagent_briefs.md`, lane L2), joined from two deliveries: the first arrived truncated (it began inside candidate 3), so R1 asked for the part before that point and the subagent resent it unchanged (no new searches). Part A below is the resent part; part B is the tail of the first delivery. R1 has not re-verified every row; the rows R1 spot-checked are marked in the memo.

---

## Part A (resent)

# L2 lane report: scoring structure, luck and psychology

**Conventions.** All sources were accessed on 13 Oct 2026. "pp" means percentage points.
- **Read levels:** *full* means I read the whole text (PDF). *partial* means I read the article or page through a summarising fetch. *abstract* and *snippet* mean I saw only that.
- **"vs market"** uses the categories in the brief: none / rankings or Elo only / soft odds / average odds / sharp close / exchange / in-play.

## Summary

- **I found and read the Kovalchik & Ingram paper in full** (MIT Sloan 2016).
  - Pressure and score effects on serve points are real on average but small: facing a break point costs −0.76 pp (ATP); being a set down costs −1.9 pp; each point of lead within the set adds +0.3 pp.
  - Per-player "mentality" effects improved ATP log loss on the 2015 Slams from 0.517 to 0.509, with no gain for the WTA.
  - The baseline was a point model that treats points as independent (iid). There were about 500 test matches per tour, and nothing was tested against prices.
- **Clutch outcomes are mostly luck.**
  - Winning more tiebreaks than expected has a year-to-year correlation "almost exactly zero".
  - Deciding-set records regress hard: three-set win% ≈ 45% + 0.20 × straight-set win%.
  - Weighting break points won by their importance adds nothing, even within the match.
  - The usable statistic is therefore a **luck residual** that should mean-revert, not a clutch skill.
- **Weighting ratings by the scoreline beats win/loss Elo**, but nobody has shown it beats prices.
  - Weighted Elo (WElo) lost money at average odds (−3.5% ROI) and at Bet365 (−3.8%).
  - Its +3.6% ROI exists only at the best of 11 books, with thresholds picked on the test period. Random picks at best odds also showed positive ROI in a 2021 replication.
  - Sackmann reports never improving his Elo with margin of victory.
  - The untested angle is the gap between results and points won: about 4.5% of matches are won with fewer points.
- **Departures from independent points are mostly match-level "day form", not momentum.**
  - In 2014, 36% of ATP best-of-three matches went three sets, against 44% predicted.
  - 7-0 tiebreaks occur at about twice the equal-skill rate.
  - Even controlling for the average-odds win probability, the loser of set 1 is 20.5 pp less likely to win set 2.
  - Before a match, this points to **form volatility** as the candidate.
- **The cross-match "hot hand" is a ratings effect.**
  - +3.1–3.3 pp per win in the last ten matches holds only against rankings.
  - Title winners perform as expected the following week.
  - No tennis study tests how pre-match prices react to streaks.
- **Gender effects are all within-match**, so they matter in-play only (tour is already an input).
  - Men choke more on high-pressure games.
  - Women's second sets collapse more after losing the first set.
  - Match-level setbacks show no gender gap.
- **Serve versus return:** I found no study of which predicts future results better, or of whether markets over-value serving. The 200-search cap was hit during this topic.

## 1. Break points, tiebreaks, deciding sets, "clutch"

| Citation | Type | Read | Data, seasons | Claim and effect size (unit) | vs market | Candour |
|---|---|---|---|---|---|---|
| [Kovalchik & Ingram (2016), "Hot heads, cool heads, and tacticians: Measuring the mental game in tennis", MIT Sloan SAC paper 1464](https://martiningram.github.io/papers/hot-heads-cool-heads.pdf) | conference paper | full | Tennis Abstract point-by-point data, 2011–15. ATP 250+ and Slams: 1.61M points, 10,101 matches. WTA International+: 1.37M points, 9,668 matches. Test set: 2015 Slams | Change in serve-point win, pp per unit, ATP/WTA: break point −0.76 [−1.08, −0.44] / −0.63; set down −1.94 / −2.01; set up +1.43 / +1.71; lead within the set +0.30 / +0.31 per point (≈1.4 pp per SD); won previous point +0.63 / +0.51; tiebreak −0.06 (ns) / −0.61 (ns). 2015 Slam log loss, iid → average effects → per-player effects: ATP 0.529 → 0.517 → 0.509; WTA 0.598 → 0.580 → 0.583 | none | One season and about 500 test matches per tour, so the 0.008 gap is likely unresolved. The "momentum" terms are confounded with day form (ability is held static). No persistence test. Disputes the "practically insignificant" conclusion of Klaassen & Magnus 2001 (known) |
| [Kovalchik & Reid, "Measuring clutch performance in professional tennis", *Statistica Applicata* 30(2):255–268 (2018; online 2020)](https://www.sa-ijas.org/ojs/index.php/sa-ijas/article/view/30-11) | peer-reviewed | full | 2011 Slams: 305 ATP and 296 WTA matches | Importance-weighted averages separate winners from losers better. First-set clutch differentials improve accuracy in calling the same match's winner by up to 1–6 pp. ATP odds ratio for break points created: 3.8 [1.8–8.6]. Break points won: "negligible effect" | none | Explains the same match; not pre-match prediction. Small sample. No player persistence test |
| [Sackmann (2012), "The Luck of the Tiebreak"](https://tennisabstract.com/blog/?p=922) | practitioner | partial | ATP players with ≥15 tiebreaks in consecutive years, 1991–2012 | Tiebreak wins above expectation: "year-to-year correlation … almost exactly zero". The number of tiebreaks played predicts a little over-performance; big serving does not | none | Old; ATP only. Agrees with the known 2019 post (two extra tiebreak wins ≈ one extra match win) |
| [Sackmann (2024), "Hubi's Three-Set Magic"](https://www.tennisabstract.com/blog/?p=6950); [Sackmann (2014), "A Quick Look at the Odds of Three-Setters"](https://www.tennisabstract.com/blog/page/95/?cat=-1) | practitioner | partial | ATP regulars (50+ matches a year); 2014 ATP and Challenger matches | "Three-set win% = 45% + (20% × two-set win%)". In 2014, 36% of ATP best-of-three matches (32% at Challengers) went three sets, against 44% predicted by a rankings model | none | The fit of the formula is not shown. The shortfall of three-setters is evidence of overdispersion (§3) |
| [Sackmann (2014), "Do Players Get Broken More Often After Failing to Convert Break Point?"](https://www.tennisabstract.com/blog/category/hot-hand/) | practitioner | partial | About 3,000 tour and qualifying matches, 2013 | Break rate 21.7% overall vs 21.2% in the next service game after missed break points; 571 holds observed vs 570 expected | none | One season. Agrees with Kovalchik & Ingram's non-significant "missed break" terms |

Known and consistent with these: Sackmann's 2015 post on break-point persistence and his 2019 post on tiebreak luck. Kovalchik & Ingram is the only out-of-sample support for clutch as a skill, and it holds for the ATP only.

## 2. Conversion luck and margin of victory

| Citation | Type | Read | Data, seasons | Claim and effect size (unit) | vs market | Candour |
|---|---|---|---|---|---|---|
| [Angelini, Candila & De Angelis (2022), "Weighted Elo rating for tennis match predictions", *EJOR* 297(1):120–132 (postprint)](https://cris.unibo.it/handle/11585/821483) | peer-reviewed | full | tennis-data.co.uk, ATP 250+ and Slams, 2005–20: 33,976 matches. Test: ATP 2012–20 (19,123), WTA 2013–20 (15,684) | The Elo update is scaled by the games share of the last match. Test accuracy 78.23% vs 77.91% for Elo. Diebold–Mariano statistic vs Elo: −6.92 (Brier), −7.75 (log loss); WTA −5.48 / −6.39. ATP ROI: +3.56% at the best of 11 books (3,189 bets) vs Elo +1.31%; −3.53% at average odds; −3.76% at Bet365. Negative even at best odds in 2018 and 2020 | Elo; soft, average and best-of-11 odds (Pinnacle among them) | Profit exists only at best-of-books odds, which are biased upward, with thresholds picked on the test grid. 78% accuracy is unusually high, because cleaning keeps only matches with complete covariates. The baseline is plain Elo |
| [Candila (2023), "welo: an R package for weighted and standard Elo rates", *Statistica Applicata* 35(1)](https://sa-ijas.org/ojs_files_online_first/35_005_193.pdf) | peer-reviewed (software) | full | ATP 2021: 1,771 matches, in-sample, no burn-in | WElo log loss 0.6451 vs Elo 0.6581. At best odds: WElo +10.0% ROI on 1,002 bets; **random picks under the same filter +2.6%** | soft odds and best odds | Demonstration only. It shows that selecting at best odds inflates ROI |
| [Kovalchik (2020), "Extension of the Elo rating system to margin of victory", *IJF* 36(4):1329–1341](https://ideas.repec.org/a/eee/intfor/v36y2020i4p1329-1341.html) | peer-reviewed | abstract | men's tennis | All margin-of-victory variants using within-set statistics beat standard Elo; only the "joint additive" variant gave unbiased ratings with stable variance. No numbers seen | Elo only | Paywalled |
| [Sackmann (2019), "Rethinking Match Results as Probabilities"](https://www.tennisabstract.com/blog/?p=3815) | practitioner | partial | — | Converts a match's points won into the probability that the winner was the better player. "Have not found any way to consistently improve the predictiveness of the ratings" with margin of victory | none | Contradicts the two papers above; no data shown |
| Wright, Rodenberg & Sackmann (2013), "Incentives in best of N contests: quasi-Simpson's paradox in tennis", *IJPAS* 13(3):790–802 ([link](https://www.ingentaconnect.com/content/uwic/ujpa/2013/00000013/00000003/art00019)) | peer-reviewed | snippet | More than 61,000 matches, 1990–2011 | About 4.5% of matches were won by the player who won fewer points | none | Descriptive |
| Lisi, Grigoletto & Canesso (2019), "Winning tennis matches with fewer points or games than the opponent", *JSA* 5(4):313–324 ([link](https://content.iospress.com/articles/journal-of-sports-analytics/jsa190328)) | peer-reviewed | snippet | Men and women, 2012–17 | The same paradox for points and games, with significance tests and Monte Carlo simulation | none | No numbers seen |
| [Yoshizawa, Kawamoto & Takeshita (2026), "Rules create unequal rewards: elite tennis players allocate resources efficiently", arXiv 2601.15327](https://arxiv.org/abs/2601.15327) | working paper | abstract | not stated | Top players sit nearer the frontier of game-win probability vs points spent; they ease off when far behind in a game (0-2, 0-3), especially on return | none | Implies part of the games-vs-points gap is **skill** for elite players, which complicates the luck reading |
| Moskowitz, SSAC talks: ["Skill, Luck, and the Battle of the Sexes"](https://www.sloansportsconference.com/event/skill-luck-and-the-battle-of-the-sexes) (2025); ["Identifying Multiple Dimensions of Luck versus Skill"](https://www.sloansportsconference.com/event/luck-v-skill-in-tennis-outcomes-need-title) (2026) | conference talk | abstract | Point-by-point data, structural model | Three kinds of luck: match, path and draw. Match luck hurts more-skilled players; best-of-three carries more luck than best-of-five. The model "matches data and betting odds" | fit to odds (unspecified) | No paper or numbers found |
| [Zappalá et al. (2023), "The paradox of talent", *Chaos, Solitons & Fractals* 176](https://arxiv.org/abs/2311.06268) | peer-reviewed | abstract | ATP 2010–19 | An agent-based model fits best when the weight on talent is 0.20–0.30 ("chance" 70–80%) | none | Luck is defined by the model; not predictive |

## 3. Departures from independent, identically distributed points

| Citation | Type | Read | Data, seasons | Claim and effect size (unit) | vs market | Candour |
|---|---|---|---|---|---|---|
| Jackson & Mosurski (1997), "Heavy defeats in tennis: psychological momentum or random effect?", *Chance* 10(2):27–34 | peer-reviewed | snippet | Wimbledon and US Open | More heavy (straight-set) defeats than an independent-set model predicts; evidence of momentum concentrated in heavy defeats | none | Not opened. Momentum vs a match-level random effect is the day-form question |
| [Sackmann (2011), "Point Outcomes by Game Score"](https://www.tennisabstract.com/blog/2011/11/03/point-outcomes-by-game-score/) | practitioner | partial | 2011 Slam men: 66,309 points | Server point win: 63.4% at 0-0, 67.1% at 40-0, 54.8% at 0-40, 61.6% at deuce, 57.8% on break point | none | Selection bias (strong servers reach 40-0 more often), acknowledged |
| [Sackmann (2013), tiebreak shutouts; (2012), influence of a first-set tiebreak](https://www.tennisabstract.com/blog/category/hot-hand/) | practitioner | partial | 30,259 tiebreaks since 1991 | 7-0 tiebreaks: 1.7% observed vs ≈0.93% expected for equal players. First-set tiebreak winners lose the match 22.3% of the time vs 18.0% for all first-set winners; "at least 80%" of the effect is skill, not momentum | none | The equal-skill benchmark exaggerates the excess |
| De Paola & Scoppa (2017), "Gender differences in reaction to psychological pressure: evidence from tennis players", *EJWOP* 26(3):444–456 ([IZA DP 9315](https://www.iza.org/publications/dp/9315)) | peer-reviewed | full (discussion paper) | 35,441 best-of-three ATP and WTA matches, 2007–14 | Controlling for the average-odds win probability (Bet365, Bwin, Ladbrokes, Expekt), ranking, rest, and player or tournament fixed effects. Losing set 1: P(win set 2) −0.205 (linear probability model); −1.24 games in set 2 (men), −1.78 (women). Losing set 2: −0.30 games and −0.053 P(win set 3) | average odds (as a control) | Not causal. It shows a large match-specific form component that pre-match prices leave out |
| [Depken, Gandar & Shapiro (2022), *JSE* 23(5):598–623](https://ideas.repec.org/a/sae/jospec/v23y2022i5p598-623.html); [(2023), *AEL* 30(6):735–739](https://ideas.repec.org/a/taf/apeclt/v30y2023i6p735-739.html) | peer-reviewed | abstract | About 66,000 best-of-three matches, 2002–20; 8,193 ATP best-of-five matches | A rational contest model fits set 1. After that, a "psychological reversal": the winner of the previous set underperforms the model in every later set | not verified | No effect sizes seen; how skill was measured not checked |
| Malueg & Yates (2010), "Testing contest theory", *REStat* 92(3):689–692 ([link](https://ideas.repec.org/a/tpr/restat/v92y2010i3p689-692.html)) | peer-reviewed | snippet | Pairs judged equal by betting odds | Effort is adjusted strategically: more matches end in two sets; reaching a third set makes the players even | soft odds (to select matches) | Old; no numbers seen |
| [Kovalchik & Reid (2019), *IJF* 35(2):756–766](https://ideas.repec.org/a/eee/intfor/v35y2019i2p756-766.html) | peer-reviewed | abstract | Tested on the 2017 season | In-play updating vs constant ability: "28% reduction in the error of in-match serve predictions", and +4 pp in win accuracy | none | Evidence of strong match-specific form |
| [Goyal & Simonoff (2020), arXiv 2009.05830](https://arxiv.org/abs/2009.05830) | working paper | abstract | Slams 2014–19, mixed models | Carry-over at set, game and point level; losing a game predicts winning the next one | none | Withdrawn |
| [Meier, Rüdisser, Flepp & Franck (2019), U. Zurich WP 383](https://ideas.repec.org/p/zrh/wpaper/383.html) | working paper | abstract | Wimbledon and Roland Garros 2009–14, N = 29,934 | A converted break predicts winning the next game only when there is no rest break; stronger for less skilled players and late in matches | none | Within-match; companion to the known Meier et al. 2020 |

## 4. Hot hand and momentum across matches, and market reaction

| Citation | Type | Read | Data, seasons | Claim and effect size (unit) | vs market | Candour |
|---|---|---|---|---|---|---|
| Jetter & Walker (2015), "Game, set, and match", *JEBO* 119:96–108 ([IZA DP 8934](https://www.iza.org/publications/dp/8934)) | peer-reviewed | full (discussion paper) | 107,566 main-tour matches (ATP 1997–2014, WTA 1989–2014) of players ranked on 21 Sep 2014 | Logit marginal effects with rank, opponent rank, head-to-head, surface and round controls. Per win in the last 10: +3.1 pp (men), +3.3 (women). Per win in the last 5: +4.0 / +4.5. Win streak +1.7 per match; losing streak −1.6 / −2.0. Clutch: top-4 player at a Slam +10.8 pp (men), +7.8 (women); top-4 in Slam tiebreaks +8.3 pp (men, p < 0.1); deciding sets ns | rankings only | Rankings are weak controls (Elo absorbs recent form). Survivor sample: the reference player wins 53–54% of matches. Rows are duplicated when both players are ranked |
| [Sackmann (2014), "Jo-Wilfried Tsonga and the (Extremely Specific) Post-Masters Blues"](https://tennisabstract.com/blog/?p=1689) | practitioner | partial | ATP since 2000 | 531 title winners who played the next week: 2.0 wins in the next event, lost their first match 26.3% of the time (≈ expected). 1,055 finalists who played the next week: lost their first match 31% (≈1 pp worse than expected). 17 Masters winners outside the top 5: more than 40% first-match losses | rankings model | No letdown on average; the n = 17 subgroup is noise |
| [Ötting, Deutscher, Singleton & De Angelis (2025), "Betting on momentum in contests", *Economic Inquiry* 63(4)](https://ideas.repec.org/a/bla/ecinqu/v63y2025i4p1066-1089.html) | peer-reviewed | abstract | **Football**: 612 Bundesliga matches, in-play odds and stakes second by second | Stakes on a team that has just equalised rise about 40%. No momentum in outcomes, and prices are unbiased | in-play | Not tennis. Prices do not follow bettors' belief in momentum |

Known and consistent: Easton & Uylangco 2010 (Betfair in-play did not instantly price the tendency to lose points after being broken); Gauriot & Page 2019; Meier et al. 2020.

## 5. Gender differences under pressure

| Citation | Type | Read | Data, seasons | Claim and effect size (unit) | vs market | Candour |
|---|---|---|---|---|---|---|
| Cohen-Zada, Krumer, Rosenboim & Shapir (2017), "Choking under pressure and gender: evidence from professional tennis", [IZA DP 10587](https://docs.iza.org/dp10587.pdf) (journal version not checked) | working paper | full | 2010 Slams, first sets only: 4,153 men's and 4,127 women's games | One SD more pressure (the game's importance to the match) raises the chance the server is broken by +4.9 pp for men (≈25% of their 0.20 mean) and +2.8 pp for women. With the server held fixed within the match: +9.0 vs +4.6 pp. In tied games women do not choke | none (within-match) | One year, first sets only. The pressure index is built from rankings on the same data (an instrumental-variable check is reported) |
| [Paserman (2023), *JEBO* 212:590–609](https://ideas.repec.org/a/eee/jeborg/v212y2023icp590-609.html) | peer-reviewed | abstract and snippet | Slams 2005–07; stroke-by-stroke data for 2006–07 | Both sexes play less aggressively on important points (fewer winners and fewer unforced errors), which the paper reads as deterioration. Keeping aggression could raise P(win) from 0.5 to 0.75–0.80. An earlier version: women's serves ≈3.5 mph slower on the most important points | none | Versions disagree on the gender gap. The counterfactual comes from a structural model |
| De Paola & Scoppa (2017), see §3 | peer-reviewed | full | as in §3 | Women lose 0.54 more games than men in set 2 after losing set 1 (odds-controlled; t ≈ −7.4 with player fixed effects). In finals: women −2.77 games, men −0.47. No gender gap in set 3 | average odds (as a control) | Within-match |
| [Banko, Leeds & Leeds (2016), *SSQ* 97(2):161–176](https://ideas.repec.org/a/bla/socsci/v97y2016i2p161-176.html) | peer-reviewed | abstract | ATP and WTA best-of-three | Women who lose the first set are no more likely than men to lose the match, but lose straight-set defeats by wider margins | not stated | Abstract only |

## 6. Serving versus returning

| Citation | Type | Read | Data, seasons | Claim and effect size (unit) | vs market | Candour |
|---|---|---|---|---|---|---|
| [Sackmann (2017), "Measuring the Impact of the Serve in Men's Tennis"](https://tennisabstract.com/blog/?p=2429) | practitioner | partial | About 1,200 Match Charting Project matches since 2000 | 53.6% of service points won are attributable to the serve (grass 61.5%, hard 54.4%, clay 47.8%). Range: Karlovic 73.3%, Schwartzman 35.0% | none | Descriptive |
| Kovalchik & Ingram (2016), see §1 | — | full | 2015 Slams | Isner, Raonic and Karlovic were the most predictable on serve and on return. Federer, Djokovic and Nadal were predictable on serve but unpredictable on return (Serena Williams and Sharapova similarly) | none | One season; outliers flagged at \|z\| ≥ 2 |
| Reid, McMurtrie & Crespo (2010), "The relationship between match statistics and top 100 ranking in professional men's tennis", *IJPAS* 10(2) (authors and venue from memory) | peer-reviewed | snippet | Top-100 men | Second-serve points won plus second-serve return points won explain 52% of the variance in ranking | none | Cross-sectional; ranking, not future results |
| [Wieand, Chen, Zhou & Lin (2025), "Quantifying the drivers of serve effectiveness in men's tennis"](https://wsb.wharton.upenn.edu/wp-content/uploads/2025/12/WIEAND-serve_performance.pdf) | student paper | full | US Open men, 2018–19 and 2021–24 | Effect per SD on the share of first-serve points won within three shots: speed +0.063, first-serve-in% +0.023, entropy of serve location +0.013. Out-of-sample r = 0.39 | none | High-school project; one event |
| [Gauriot, Page & Wooders (2023), "Expertise, gender, and equilibrium play", *QE* 14(3):981–1020](https://www.econometricsociety.org/doi/10.3982/QE1563) | peer-reviewed | snippet | About 0.5M Hawk-Eye serves, more than 3,000 matches | Men's win rates by serve direction match game-theory equilibrium; women and lower-ranked players deviate more | none | Little exploitable serve-direction pattern at the top |

A snippet also claimed that "first-serve return win% correlates 0.637 with match win%". The source page returned HTTP 500, so treat that number as unverified.

## Candidate statistics not in the model

1. **Tiebreak and deciding-set luck residuals.**
   - *Definition:* per player, over the trailing 52 weeks and shrunk by count:
     - tiebreaks won minus Σ P(win tiebreak), where each P comes from both players' serve-point rates under independent points;
     - deciding sets won minus their expected count from the pre-match points-based model;
     - optionally, break points saved or converted minus the number expected from that player's serve and return point rates.
   - *Mechanism:* these events move win/loss records (two tiebreaks ≈ one match) but show no year-to-year persistence. Win/loss Elo, ranking points and record-reading bettors take them on board and then regress. The model's form window is only two weeks and uses raw break-point counts.
   - *Evidence:* Sackmann 2012, 2019 and 2024; Kovalchik & Reid 2018; Kovalchik & Ingram's near-zero ATP tiebreak effect.
   - *What differs from the project's earlier big-point tests:* those treated clutch as a persistent skill. This is a stock of luck expected to reverse, with a negative expected sign.
2. **Results beyond points.**
   - *Definition:* over 52 weeks and over 3 months, Σ match wins minus Σ P(win | share of total points, match length), following Sackmann's 2019 binomial method. Also games won minus the number expected from serve and return points won. Alternatively, WElo minus win/loss Elo.
   - *Mechanism:* the market and the model's Elo anchor on wins and losses.
   - *Evidence:* WElo beats Elo but not average odds; 4.5% of matches are won with fewer points.
   - *Caveat:* Yoshizawa 2026 implies the gap is partly a persistent skill for elite players, so the sign is an empirical question. That makes it a good candidate for the feature pool.
3. **Day-form volatility.**
   - *Definition:* the time-decayed SD, over the last 20–30 matches, of the match residual: share of points won minus the share expected from the pre-match profile. Computed separately for serve and return, plus the frequency of blow-out losses.
   - *Mechanism:* outcomes are over-dispersed and a favourite's win probability depends on how much its form varies. Ratings and the closing price carry means; the model's inputs are all means.
   - *Evidence:* the three-setter and 7-0 tiebreak excesses; De Paola & Scoppa (−0.205 after odds); Kovalchik & Reid 2019 (−28% error); Kovalchik & Ingram's differences in predictability.
   - *Known neighbour:* Kovalchik's 2015 consistency Q&A, which was descriptive and never tested before a match.

## Part B (the tail of the first delivery, from candidate 4 on)

4. **Score-state "resilience" profile.**
   - *Definition:* from point-by-point data (Slams, Tennis Abstract), per-player effects of being a set down, the lead or deficit within the set, and facing a break point, on serve-point win. Use Kovalchik & Ingram's model with partial pooling over a rolling 2–3 seasons, and interact with best-of-five.
   - *Mechanism:* this is invisible in box scores; the market prices only reputation.
   - *Evidence:* ATP log loss 0.517 → 0.509 with per-player effects, with no WTA gain. Against it: Sackmann's break-point non-persistence, and the project's own finding that leverage traits are priced or unresolved.
   - *What differs:* it measures response to being ahead or behind, not response to point importance.
   - *Prior:* low; coverage is limited to matches with point-by-point data.
5. **Matchup luck exposure.**
   - *Definition:* from the two players' predicted serve-point probabilities (already in the profile), apply the point-by-point Markov model to get P(at least one tiebreak), expected tiebreaks, P(deciding set) for the format, and the iid match-win probability. Add them as inputs, and their products with the rating edge.
   - *Mechanism:* when both players hold serve often, results hinge on tiebreaks that behave like coin flips, so skill edges shrink. Moskowitz finds match luck hurts the more skilled player. Isner went to three sets in 47.4% of matches in 2014, against 36% for the tour. The learner may not build this transform from raw rates, and the closing price may shrink favourites too little or too much in serve-dominated matchups.
   - *Evidence:* Sackmann 2012 and 2014; Moskowitz (abstract only). The formulas are known (Barnett & Clarke, O'Malley); this use of them is new.
   - *Prior:* low to modest; no new data needed.
6. **In-play only: tour asymmetries after set 1 and under pressure.**
   - Applies only if the project bets live.
   - WTA set-1 losers lose 0.54 more games in set 2 than ATP set-1 losers, after controlling for odds.
   - Men's break probability rises 9.0 pp per SD of game pressure, against 4.6 pp for women.
   - The known Easton & Uylangco 2010 found Betfair lagging after breaks of serve.
   - Out of scope for pre-match betting.
7. **Not recommended: serve-direction entropy** from the Slam ball-tracking data.
   - The evidence is a student paper (+0.013 per SD), and top men play close to equilibrium.
   - It overlaps the shot-level style rates the project already found priced or unresolved.

## Searches that found nothing useful

- **Persistence of break-point or tiebreak over-performance:** no academic year-to-year test beyond Sackmann's posts. Kovalchik & Reid 2018 is within-match only; Fitzpatrick et al.'s Wimbledon papers are descriptive.
- **"Pythagorean" or dominance-ratio luck predicting the next season in tennis:** only generic baseball and NBA material.
- **Pre-match price reaction to streaks, titles or comeback wins in tennis:** nothing tennis-specific. Only football (Ötting et al.) and a Czech thesis on hot-hand bias, which I did not open.
- **The "ATP 250 winner's curse":** an April 2026 tennisnerd opinion piece with no data.
- **Serve vs return:** nothing on which is more persistent or more predictive, and nothing on whether markets over-value big servers, before the cap was hit.
- **Effect of saving match points on the next match:** nothing.
- **Du, Zhang & Zhou (2025), arXiv 2509.01243:** momentum built from in-match features of 31 matches at Wimbledon 2023. Not usable.
- **Sources I could not open, so reported at abstract or snippet level:**
  - Kovalchik 2020 full text (paywall)
  - Semantic Scholar (HTTP 403 and 429)
  - the Newcastle repository (DNS failure)
  - the Harvard Sports Analysis 2010 post (HTTP 500)
  - IOS Press (HTTP 403)

## Process notes

- **Search budget:** the 200-call WebSearch cap, shared across agents, ran out during topic 6. These planned look-ups were not done:
  - Pinnacle's articles on serve and return
  - how Depken et al. measured the skill gap
  - Kovalchik 2020's numbers
  - more work on whether serve or return predicts better

  A follow-up turn could finish them.
- **Files:** I wrote no repository files and ran no git commands. WebFetch cached seven fetched PDFs in the session's `tool-results` folder (`C:\Users\zerom\.claude\projects\c--Users-zerom-Documents-Tennis-predictions\e1ffc84e-fa2d-42f9-9d17-7c936a046c45\tool-results\`); the tool does this itself.
