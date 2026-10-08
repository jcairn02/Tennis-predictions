# Literature scout: interactions, matchups and what beats the close

6 October 2026, round 0 of the [feature-interactions study](../brief.md). Research evidence, not a decision. Written blind to the other round-0 files.

**Scope.** What other modellers have published (seminal works, then mainly 2018–2026, academic and practitioner) on interactions and matchups between features in tennis match prediction, and on what beats bookmakers' closing prices. It extends the project's earlier notes rather than repeating them: [market anchoring](../../../research/market-anchoring/README.md) (5 Oct), [rating systems](../../../research/rating-systems/README.md) (2 Oct), and the [predictive-frontier register](../../predictive_frontier/research.md) (2 Oct). Sources those notes already read are cited as **project note** and not re-read.

**Labels.**

* **Reported**: what a source measured and published.
* **Claim**: a statement the source makes without data shown, or that cannot be checked here (practitioner posts, abstract-only conclusions).
* **Computed here**: my own arithmetic.
* **Inferred**: my reasoning.
* **Unknown**: what no source settles.
* **Suggestion**: a proposal, not a decision.

**Read level.** Each reference states one: *full* (whole text read), *partial*, *abstract*, *secondary* (described by another source), or *project note*.

**Access.** Every URL was accessed on 6 October 2026, except project-note items, which those notes accessed on 2 or 5 October 2026.

**Tools.** Text was pulled from downloaded PDFs with `pypdf` in the miniforge base Python 3.11 (a self-contained research utility, not the project's `tennis` environment). The iid point-model numbers in §2.1 were run with `./python.sh` from throwaway scripts in the session scratchpad. Their logic is reproduced in Appendix A, so nothing outside this study folder is needed to recompute them.

**Direction of scores.** Log loss and Brier: lower is better. Accuracy, ROI, mLL gains: higher is better. Few sources report intervals; where none is given, the size is a point estimate and cannot be called a win or a tie. "Points" means percentage points unless a count is stated.

## In short

* **Reported.** No peer-reviewed paper or preprint found shows a statistic-based feature or interaction beating a sharp closing price out of sample.
  * The nearest claims all fail on design or were withdrawn:
    * Clegg and Cartlidge: +3.26% ROI at Pinnacle on "high-intransitivity" matchups in v1; v2 (June 2026) drops the betting claim [R44].
    * Sipko: a positive ROI at Pinnacle from a model whose test log loss is far above the market's [R40].
    * Buhamra: profit from a spline on average odds, under look-ahead cross-validation [R47].
    * Candila and Palazzo: profit only in subsets, at the best of many prices (project note).
  * Wilkens, the largest ML study, concludes the market holds most of the information [R41].
* **Computed here: the structural literature implies one interaction the A − B frame cannot see.**
  * The point → game → set → match recursion turns a serve-point edge into match odds more weakly when both players serve dominantly. The match-win log-odds per 0.01 of serve-point difference is 0.213 at a serve level of 0.55 and 0.175 at 0.75 (best of three).
  * Best of five multiplies the log-odds by 1.25 at every level.
  * The sum of both players' serve orientation is a symmetric quantity. The difference-only inputs never carry it.
  * Ignoring it costs a 70% favourite 0.15–0.6 mLL per match when the pair's serve level is 0.04–0.08 above the reference. A 90% favourite in an extreme pairing loses up to 2.3 mLL (Appendix A). The average over all matches is probably a few tenths of a mLL (**Inferred**).
* **Reported: one empirical hint for the serve-level effect.** Matches between two aggressive, big-serving players produce more upsets than surface Elo expects; matches between two counterpunchers produce the fewest (Sackmann 2019, about 11,000 ATP matches [R60]). A Bet365 thesis found positive returns on grass underdogs, 2010–2012 (weak [R35]).
* **Reported: the best-measured market errors are about the price's shape by context, not about player statistics.** On Bet365 (44,871 matches) the favourite–longshot bias is near zero in ordinary matches. It is much stronger when both players are outside the top 50, in later rounds and at Slams [R28].
  * In matches between two players outside the top 50, a 20% longshot wins about 3.6 points less than the base fit, and an 80% favourite about 2.0 points more (**Computed here** from the reported coefficients).
  * Exchanges show the same pattern [R29]. Pinnacle says its own close is nearly calibrated (project note).
* **Reported: well-measured context effects that no study tests against odds.**
  * Previous-match load (sets, minutes) [R14, R61].
  * Home advantage, larger for inexperienced players [R17].
  * Event speed [R5, R65].
  * Heat and altitude [R21, R22].
  * Height and handedness [R23–R26, R63b].
  * Volatility (match-to-match variance) [R4].
* **Reported: clutch, momentum and head-to-head are weak.**
  * Clutch is contested. Persistent "critical ability" in US Open data [R49] against no persistence in break-point and tiebreak over-performance [R67, R68].
  * Momentum is causal but small, and found for men only [R50, R52].
  * Head-to-head adds almost nothing to rankings [R62].
* **Observed in this repository (not literature).** Two literature-motivated families were already tested against a strong market model, and both tied:
  * event speed × style: men +0.073 [−0.149, +0.295] mLL;
  * reliability/variability: +0.232 [−0.038, +0.502] mLL ([predictive frontier](../../predictive_frontier/README.md); gains, higher is better).
* **Process lesson (Reported).** Leakage and look-ahead are common in this literature. Examples:
  * Above 80% "pre-match" accuracy built from same-match serve statistics with a random split [R42].
  * Leave-one-tournament-out cross-validation [R47].
  * Selection of interaction features on a validation set that did not carry over to the test set [R40].

## 1. Ranked interaction and matchup ideas from the literature

**How ranked (Inferred).** Each idea is scored on three things:

1. The strength and size of the published evidence.
2. Whether there is any reason or evidence that the price misses it.
3. Whether the current 58-input frame genuinely cannot express it.

Type codes follow the [brief's template](../brief.md):

* **S**: symmetric match character × a difference.
* **W**: within-player nonlinear, f(A) − f(B).
* **X**: cross-player matchup.
* **C**: composition through the point → match model.
* **U**: uncertainty or reliability.
* **M**: market state.

Evidence strength grades:

* **A**: theory, or causal/quasi-experimental and replicated.
* **B**: large-sample observational, or one strong study.
* **C**: small sample, simulation or in-sample only.
* **D**: claim without data.

| # | Idea (type) | Mechanism | Main evidence | Strength | Reported direction and size | Against the market? | What the 58-input frame lacks |
|---|---|---|---|---|---|---|---|
| 1 | **Serve-dominance level × strength difference** (S, via C) | When both players hold easily, sets go to tiebreaks and a given point edge buys fewer match wins | Newton & Keller [R2]; O'Malley [R3]; Klaassen & Magnus 2003 fix the sum per tournament [R7, R9]; Ingram reports sum and difference separately [R5]; Sackmann styles and upsets [R60]; computed here | A (theory), C/B (empirical) | Log-odds slope 0.213 → 0.175 per 0.01 serve difference as the serve level goes 0.55 → 0.75. A 70% favourite at level 0.64 is 68.4% at 0.72. Aggressive pairs show the most upsets against Elo | None tested; thesis hint of grass underdogs [R35] | The level (both players' serve orientation summed) is invisible to A − B inputs; only surface, tour and indoor stand in for it |
| 2 | **Price shape by context**: the favourite–longshot bias by rank tier, round and event level; nonlinear in the odds (M) | Bookmakers shade longshots where information is asymmetric or attention is high | Lahvička 44,871 Bet365 matches [R28]; Abinzano exchange [R29]; Forrest & McHale [R27]; Whelan 56,004 matches [R30]; Buchdahl, Pinnacle 2015–19 [R31]; Buhamra spline on odds [R47] | B | Both players outside the top 50: about −3.6 points at 20% implied, +2.0 at 80%. Slams and tour finals: −2.2 / +2.0. Later rounds: −1.6 / +0.5. 10% Pinnacle longshots won 6% (claim) | Yes, as a pricing bias at soft or average odds. Pinnacle claims a close slope of 0.994 (project note) | One logistic slope per tour. TabPFN could form context × `odds_logit` but reportedly learned no context effect (brief) |
| 3 | **Volatility and evidence reliability pull toward 50%** (U) | Variance in a player's point rates hurts the favourite and helps the underdog; thin or stale evidence should shrink edges | Newton & Aslam simulation [R4]; Glicko/TrueSkill (project note); Sipko's uncertainty filter [R40]; Kovalchik on consistency [R59] | C (and a project tie) | The favourite (serve 0.71 against 0.68) loses 0.83 points of match-win probability per 0.01 of its serve-rate SD. The project's reliability family tied against the market model | None outside the project | No per-player dispersion or exposure input. "Both players erratic" × difference cannot be formed |
| 4 | **Previous-match load relative to the opponent, × sex and format (age)** (W; S by tour) | Hangover from extra sets or long time on court | Goossens et al. 20,320 Slam matches [R14]; Sackmann time on court [R61]; marathon fifth sets [R61b]; WTA marathon third sets [R61c]; O'Donoghue [R15] | B; conflicting for women | Women, one set more than the opponent: logit −0.286 (about −4.5 points). Men: +1 set no effect; +2 sets −0.184 (about −4.9 points). Next-round win ratio against surface Elo: 1.07 after a 1:00–1:29 match, 0.76 after 4:30+. Rest-day difference: no effect | None tested; practitioners claim it is "usually" priced. The project's recovery family tied (men −0.07 [−0.22, +0.08] mLL) | Only `sets_14d`. No last-match minutes or sets relative to the opponent; no age × load |
| 5 | **Home advantage × experience; × opponent's travel** (W; X) | Familiar environment and the travelling opponent's fatigue | Gucciardi & Ruberti, 59,067 ATP matches [R17]; Koning [R16]; Creutzburg et al. [R18]; home bets lost less, Bet365 thesis [R35] | B | +4.3 points (s.e. 0.6) with rank, points, age, height and fixed effects. Larger for inexperienced players. Home × opponent travel positive (10% level). Survived closed-door COVID matches. Men only in Koning | Thesis hint only | No home or country input |
| 6 | **Event conditions (court speed, altitude, heat) × serve/return style** (S) | Fast or thin-air events reward serving; heat changes risk-taking | Ingram tournament intercepts [R5]; Sackmann speed ratings [R63–R65]; Federer–Nadal speed model [R66]; altitude [R22]; heat [R21, R21b] | B (events differ), C (× style) | Ace rate 53–145% of average, yet serve points within ±3% for 53 of 67 events. Intercepts ±0.15 logit (about ±3.5 points of serve). Heat, Elo-adjusted: aces +5% and net approaches −7.6% per WBGT zone | None; the project's event speed × style tied | No event-speed input |
| 7 | **Intransitivity and multi-dimensional style matchups** (X) | Rock–paper–scissors patterns that a single rating cannot hold | Clegg & Cartlidge v1/v2 [R44]; Chen & Joachims [R45]; Sackmann styles [R60] | B against Elo; nothing against the close | v1: +3.26% Kelly ROI on 1,903 Pinnacle bets in a subset. v2: no unconditional accuracy gain; combined with WElo it beats WElo; no Brier gain over Pinnacle | Tested: no gain against Pinnacle | `prod_<s>` gives one bilinear form per statistic; no latent style vectors |
| 8 | **Popularity / sentiment × price** (M) | Fans' money distorts prices on stars | Ramirez et al. and its replication (project note); van Rheenen [R33]; Scheibehenne & Bröder [R34] | C, conflicting | WTA "buzz" profits mostly disappear on replication. Men's Slams: popular players' odds too long in finals and Big Four matches, but not exploitable | Tested at soft prices: no durable edge | No popularity input |
| 9 | **Age × strength; age × load** (W) | Ratings mean more near peak age; older players recover more slowly | Buhamra & Groll [R46]; Sackmann aging curves [R75] | C | Random-forest dependence plots: Elo matters more near ages 28–32 (Grand Slams, no odds). Aging curves: ATP peak about 25 (flat 24–27), WTA 23–24 | None | Age and load enter separately as differences |
| 10 | **Best of five × difference** (S) | More sets make an edge more decisive | Theory (computed); Kovalchik 2015 [R59]; Pollard et al. set dependence [R13]; Gorgi (project note); Sackmann "better at best of five" [R13b] | A (main effect) | Log-odds × 1.25. Kovalchik: 7–10 points in theory, 9 expected from 2010–14 set-win rates; the men–women gap in favourites' advantage at Slams was 8 points. Favourite's set-win probability +0.035 after trailing, +0.110 after losing two sets | Surely priced (Inferred) | Has `best_of`; a player-specific best-of-five ability is unproven |
| 11 | **Opening-to-closing move as information** (M) | The close may over- or under-react to steam | Buchdahl, Pinnacle 68,361 matches [R31]; Kaunitz (football; project note) | D/C | Opening-price yields against the yields implied by the open/close ratio have a gradient of 0.825, not 1 (claim) | Claim only | No opening price in the inputs |
| 12 | **Handedness matchups** (X; lefty–lefty S) | Unfamiliar spin and court-side asymmetry; a frequency-dependent edge | Sackmann 2011 and 2021 [R25, R26]; Loffing et al. [R23]; Breznik [R24] | B (rank-level), C (match-level) | Right-handers win 64.0/62.1% of serve points to the deuce/ad court, left-handers 59.3/62.8%. About +2 points for lefties at 30–40 and 40–AD. Elite advantage gone among men by 2011; smaller for better players and matches | None | No hand input. Needs A's hand × B's hand |
| 13 | **Height × surface** (W/S) | Taller players serve better and return worse | Sackmann 2017 [R63b]; Söğüt [R19]; Ma et al. [R20] | B (descriptive) | Serve points about 60% → about 70% from the shortest to the tallest bins. Return points fall with height (r² 0.74 on bins). Benefit fades above 186–190 cm | None | Height absent, but mostly carried by the serve and return profiles (Inferred) |
| 14 | **Clutch skill (break points, tiebreaks)** (W) | Some players raise their game on big points | González-Díaz et al. [R49]; Klaassen & Magnus 2001 [R1]; VU mental profiles [R59b] against Sackmann [R67, R68] | Conflicting | Big-point effects are small; at 5–5, 30–40 in a deciding set the server loses 4.6 points; weaker players deviate more. Over-performance does not persist (Sackmann) | None | `bp_saved` and `bp_conv` are already in the profiles; no tiebreak record |
| 15 | **Momentum carried across matches; letdowns** (W) | Winner/loser effects, post-title letdowns | Page & Coates [R52]; Gauriot & Page [R50]; Meier et al. [R51]; Kovalchik 2015 letdowns [R59]; Wang & Drekic (project note) | A within a match, C across matches | Men: about 60/40 in the next set after a long first-set tiebreak; none for women. Letdowns more common for women at Slams. Momentum additions failed in Wang & Drekic | In-play: the market lags the post-break dip [R36] | No "close tiebreak or comeback last match" or "title last week" inputs |
| 16 | **Head-to-head beyond ratings** (X) | Matchup-specific history | Sackmann 2014 [R62]; Sipko [R40]; Wang & Drekic (project note) | B (negative) | Head-to-head right 66.0% of the time against rank's 68.5%. Only long unbeaten records help (81.9% against 80%) | None | Not needed (low) |
| 17 | **Low-level serve decomposition through the point model** (C) | Composing first/second-serve, ace and double-fault rates into match odds | Spanias & Knottenbelt [R11]; Barnett & Clarke [R8]; Gollub 2017 [R39]; Ingram [R5] | B | Point models trail Elo. Log loss 0.649 (Barnett–Clarke) and 0.616 (James–Stein) against Elo 0.586, ATP 2014 [R39]. Ingram 0.592 against Elo 0.586 [R5] | Not against odds | Useful as the way to implement idea 1, weak alone |
| 18 | **Travel and time zones** (W) | Jet lag, arrival timing | Gucciardi & Ruberti (opponent travel) [R17]; Maynard et al. (project note) | C | Sleep changes but no performance link (WTA). Home × opponent travel positive at the 10% level | None | No travel inputs |

### Evidence notes for the top ideas

**1. Serve-dominance level × difference (S, via C).**

* **Reported.**
  * Klaassen and Magnus's 2003 forecaster, as described by Gollub [R39], sets the sum of the two serve-point probabilities to a tournament constant and solves for the difference that matches a ranking-based forecast. The sum is a separate input in the structural tradition.
  * Ingram scores the sum and the difference of serve-winning probabilities separately: RMSE 0.0904 against 0.0993 for the sum, 0.125 against 0.130 for the difference (lower is better) [R5].
  * His tournament intercepts run from +0.15 (Halle, Wimbledon) to −0.14 (Monte Carlo) on the logit scale [R5].
  * Sackmann 2019: the most predictable matches (fewest upsets against surface Elo) are between the two most conservative players. The least predictable are between two aggressive players. Against counterpunchers, aggressive players are not unpredictable [R60]. The post's tables did not render in the fetch, so the ratios are not quoted.
* **Computed here (Appendix A).** The log-odds slope falls as the serve level rises; the best-of-five multiplier stays 1.25. Excess log loss from ignoring the level, for a correctly signed difference:

  | Favourite priced at level 0.64 | True at level 0.72 | True at level 0.56 |
  |---|---|---|
  | 70% | 68.4% (0.63 mLL per match) | 71.1% (0.31) |
  | 80% | 77.9% (1.39) | 81.4% (0.66) |
  | 90% | 87.9% (2.31) | 91.3% (1.02) |

  At a women's level of about 0.57 the effects are roughly halved.
* **Inferred.**
  * Under a logit-additive serve/return model, the difference p_A − p_B tracks total strength, (serve + return)_A − (serve + return)_B.
  * The sum p_A + p_B tracks a match level plus both players' serve-minus-return orientation. That is exactly the symmetric "level" the brief says the model cannot see.
  * Sackmann's ["decline of specialization"](https://www.tennisabstract.com/blog/2025/12/01/the-decline-of-specialization-or-the-rising-floor/) (hold and break ranks increasingly correlated, ATP top 50, 1991–2025) suggests the spread of orientation, and so the effect, has shrunk in recent years.
* **Unknown.** Whether prices already apply it. No study tests it.

**2. Price shape by context (M).**

* **Reported (Lahvička working paper, full [R28]).** Bet365 latest odds; men 2002–2013, women 2007–2013; proportional de-vig.
  * Overall linear-probability fit: result = −0.0293 + 1.0594 × implied.
  * With interactions, the base slope is 1.0051 (no bias). The added slopes are +0.0918 for LowerRank (both outside the top 50, n = 12,878), +0.0358 for LaterRound (n = 24,189) and +0.0704 for HighProfile (Slams and finals, n = 8,962).
  * Interpreted as bookmakers protecting against informed insiders and the public reacting to news.
* **Reported (other sources).**
  * Exchanges: mispricing rises with trading volume, falls with institutional bettors, and rises with relative attention to the favourite [R29].
  * Whelan: loss rates rise steadily toward extreme longshots, ATP+WTA 2011 to June 2022 [R30].
  * Buhamra: a P-spline on average odds alone made +113.7 units on 1,170 bets, against −128.8 on 2,696 for the linear version and −311.4 for the odds benchmark. The design was leave-one-tournament-out, so it looks ahead [R47].
* **Inferred.** Part of this "bias" is created by proportional de-vigging. The Pinnacle note in the project shows yields of −1.58% (equal split), −0.42% (proportional) and −0.26% (odds ratio). Whether a context-dependent bias survives the project's de-vig of average closing odds is **Unknown**. It is cheap to test: calibration slopes by rank tier, round and level on 2013–2021.

**3. Volatility and reliability (U).**

* **Reported.**
  * Newton and Aslam: a player's serve and return point rates vary from match to match roughly normally; the 2007 ATP field SD of serve points was 0.095. With the favourite at 0.71 and the underdog at 0.68 (SD 0), simulated match-win probability = 0.677 − 0.826 × SD_A. For the weaker server, more variance raises the win chance [R4].
  * Sipko: discarding the most uncertain matches (few common opponents) improved validation log loss and ROI [R40].
* **Inferred.** This is the symmetric "both players erratic" × difference term. A reliability-weighted shrinkage of `odds_logit`-independent inputs is the U-type version.
* **Observed in this repository.** The frontier's reliability family improved the Elo combination: men +2.0 [+1.1, +3.0] mLL. Against the market model it tied: men +0.23 [−0.04, +0.50] mLL.

**4. Previous-match load (W).**

* **Reported (Goossens et al., full [R14]).**
  * Slams 1992–2011, 20,320 matches, controlling only for the log₂ world-rank difference (no odds).
  * Women with one set more in the previous match than the opponent: logit −0.286 (s.e. 0.052).
  * Men: +1 set −0.076 (s.e. 0.051, not significant); +2 sets −0.184 (s.e. 0.039).
  * For women, a rank-30 opponent who played one set fewer is equivalent to a rank-20 opponent.
  * Rest-day differences: no effect (|difference| ≤ 1 day in 98% of matches). No difference by surface or tournament.
* **Reported (Sackmann).**
  * Men's Slams since 2001, against surface Elo: the next-round win ratio falls steadily with the previous match's length, from 1.07 (1:00–1:29) to 0.76 (4:30+) [R61].
  * Marathon fifth sets reaching 6–6: next round 43–103 (29.5%) against 43.4% expected [R61b].
  * In women's Slams, marathon third sets (8–6 or longer) show little hangover: 42.2% against 44.0% expected [R61c]. This conflicts with Goossens et al.'s women's result. The measures differ (one set more against a long final set).
* **Inferred.** Strength confounds both directions: a long win can signal weaker form, and a short one a weak opponent. The market control is missing in every study.

**5. Home advantage (W).**

* **Reported (Gucciardi and Ruberti, full [R17]).**
  * ATP 2000–2022 (Sackmann data), 59,067 matches. Linear probability model with player and tournament-date fixed effects, controlling for rank, points, age and height differences.
  * Home: +0.043 (s.e. 0.006). Stronger for less experienced players; individualist cultures stronger.
  * Survived closed-door COVID matches (crowd not the main channel). Opponent's travel fatigue amplified it at the 10% level; facility familiarity did not.
* **Reported (Koning).** Significant for men, none for women [R16].
* **Claim (thesis).** Bet365 ATP 2010–2012: home-country bets lost about one third as much as the whole sample [R35].

## 2. Key quantitative facts

### 2.1 Point → match structure (Computed here unless cited)

Match-win log-odds per 0.01 of serve-point difference (p_A − p_B) near zero difference, by the average serve level p̄ = (p_A + p_B)/2:

| p̄ | 0.55 | 0.60 | 0.62 | 0.64 | 0.66 | 0.68 | 0.70 | 0.75 |
|---|---|---|---|---|---|---|---|---|
| Best of 3 | 0.213 | 0.207 | 0.203 | 0.199 | 0.195 | 0.191 | 0.186 | 0.175 |
| Best of 5 | 0.266 | 0.258 | 0.254 | 0.249 | 0.244 | 0.238 | 0.233 | 0.219 |

* At a fixed difference of 0.04, best of three gives 69.7% at p̄ = 0.60 and 68.0% at 0.70; best of five gives 74.1% and 72.0%. The same fractional shift appears in both formats.
* **Reported context for p̄.**
  * Men's average players win 65% of service points, women's 56% (Wimbledon 1992–95 [R1]).
  * Ingram's median for equal players at an average event is 62.3% [R5].
  * Tournament speed moves serve points by only ±3% for 53 of 67 events, while aces range 53–145% of average [R63].
  * Height bins span about 60% to 70% serve points [R63b].
* **Reported.** P(set) and P(match) under iid do not depend on who serves first [R2].

### 2.2 Player and context effects (Reported)

| Effect | Size | Source |
|---|---|---|
| Points are not iid | Previous point won +0.3 (women +0.5) points; lost −0.5 (−0.7). At 5–5, 30–40 in the deciding set the server loses 4.6 (4.8) points. Weaker players deviate more; iid "a good approximation" | Klaassen & Magnus 2001 [R1], Wimbledon 1992–95, about 86,000 points |
| Set outcomes not independent (men's Slams 1995–2004, 4,883 matches) | Better player's set-win probability +0.035 after trailing or after a set win; +0.110 after losing two sets. Constant-probability model χ² 38.7 against 1.83 | Pollard, Cross & Meyer 2006 [R13] |
| Momentum (causal, Hawk-Eye close calls) | Winning a point raises the next for men only | Gauriot & Page 2019 [R50] |
| Winner effect | Equal men after a long first-set tiebreak: about 60/40 in set two; none for women | Page & Coates 2017 [R52] |
| Converted break point, game-level | Game-win probability rises after a break; interruptions blunt it (psychological) | Meier et al. 2020 [R51], 141 Slam matches |
| Serving first in a tiebreak | No effect (1,701 men's and 920 women's tiebreaks, 2012–15) | Cohen-Zada et al. 2018 [R53] |
| Best of five | 7–10 points theoretical edge for the higher-ranked player; 9 points expected from 2010–14 set-win rates. Higher-ranked players' "win advantage" at 2010–14 Slams: men 50%, women 42%. Women's extra inconsistency appears only at Slams (format) | Kovalchik 2015 [R59] |
| Fatigue | See idea 4 | [R14, R61] |
| Home | +4.3 points (ATP); men only (Koning) | [R17, R16] |
| Heat (men's AO 2014–16, 360 matches) | Doctor calls +47% per WBGT zone. Unadjusted: return points won +1.75 (±0.46) per zone, winners −2.5%, net approaches −7.1%. Adjusted for opponent Elo: aces +5%, net approaches −7.6%. Duration unchanged. "Few matchplay characteristics were noticeably affected" | Smith et al. 2018 [R21] |
| Altitude (122 ATP 250 matches) | More aces and first- and second-serve points won at altitude | Sánchez Pay et al. 2019 [R22] |
| Height (156 age-25 seasons, 1998–2017) | Serve r² 0.81, return r² 0.74 (negative), win% r² 0.38 on height bins. No world No. 1 above 193 cm | Sackmann 2017 [R63b] |
| Left-handers | Over-represented in the ATP top 100 (15; about 4% chance at a 10% base rate); under in the WTA top 200. Elite men's advantage gone by 2011 | [R26, R23] |
| Head-to-head | 66.0% against rank's 68.5% (ATP since 1996) | Sackmann 2014 [R62] |
| Consistency | Favourite −0.83 points of match-win probability per 0.01 SD of serve rate (simulation) | Newton & Aslam 2009 [R4] |

### 2.3 Market biases (Reported; prices as stated)

| Finding | Size | Source |
|---|---|---|
| Favourite–longshot bias, Bet365, 44,871 matches | Slope 1.0594, intercept −0.0293. Concentrated in lower-ranked, later-round and Slam matches (§1, note 2) | Lahvička [R28] |
| Exchange favourite–longshot bias | Grows with volume and attention to favourites; shrinks with institutional bettors | Abinzano et al. 2016 [R29] |
| Loss rate by implied probability (tennis-data, 56,004 matches 2011–22) | Rises toward longshots, steeply at the extremes | Whelan 2023 [R30] |
| Pinnacle opening and closing odds, all tiers, 2015–19 (68,361 matches) | Implied 90% won 89%; implied 10% won 6%. Open/close gradient 0.825. A tipster beat the close by about 3% (claim) | Buchdahl [R31] |
| Pinnacle ATP close 2007–18 | Calibration slope 0.994; no favourite–longshot bias after the margin (Pinnacle's claim) | Pinnacle (project note) |
| Grass underdogs, Bet365 ATP 2010–12 | Positive return on grass; the bias as usual elsewhere | van 't Leven (thesis) [R35] |
| WTA against ATP margins | WTA overround higher (adverse selection) | Barrutiabengoa (thesis) [R37] |
| Reversed sentiment, men's Slams 2000–16 | Popular players under-priced in finals and Big Four matches; not exploitable | van Rheenen (thesis) [R33] |
| In-play | Odds track the iid model closely and anticipate breaks up to four points ahead. The post-break dip in point-winning is not priced at once | Easton & Uylangco 2010 [R36] |
| In-play exchange | Conservatism, anchoring and representativeness biases; profitable rules claimed | Lobão & Rolla 2015 [R38] |
| Forecast accuracy | Bookmakers' log loss 0.55 against Elo 0.59 (ATP 2014); 0.557 against best model 0.578. Pinnacle Brier 0.198 against a graph network's 0.214 | Kovalchik; Gorgi et al.; Clegg & Cartlidge (project notes) |

## 3. Negative results worth knowing

* **Interaction features overfit (Reported, Sipko [R40]).**
  * The pairwise within-player products (A_i·B_i, then the difference; RETIRED excluded) joined the 20 original features, 173 in all, in a logistic model; backward elimination kept 57.
  * Validation log loss 0.5727 against 0.5761 for the basic model (3.4 mLL better).
  * Test (2013–14, 6,315 ATP matches): 0.6122 against 0.6129 (0.7 mLL; no interval).
  * The author attributes the drop to feature selection on the validation set.
  * Sipko's "serve advantage" feature, (WSP₁ − WRP₂) − (WSP₂ − WRP₁), is algebraically linear in differences, so it is not a true matchup term (**Inferred**).
* **Intransitivity does not beat Pinnacle (Reported, Clegg & Cartlidge [R44]).** Version 2 reframes the paper away from market inefficiency. The model is complementary to Weighted Elo only.
* **ML does not beat odds (Claim, abstract-level; Wilkens [R41]).** Accuracy is capped near 70%; no model beats odds-implied forecasts; returns mainly negative.
* **Point models trail Elo (Reported).**
  * Gollub [R39], ATP 2014: Barnett–Clarke 0.649, Elo 0.586.
  * Kovalchik 2016 found the same ordering (project note).
  * Ingram [R5]: 0.592 against Elo 0.586.
  * Splitting point statistics by surface hurts through lost sample (Gollub: 0.707 against 0.649).
* **Momentum, stamina decay and player-specific additions failed (Reported, project note).** Wang and Drekic's ensembling; head-to-head variants suffer data scarcity.
* **Clutch and tiebreak over-performance do not persist (Reported, Sackmann [R67, R68]).** Season tiebreak records "resemble a spreadsheet full of random numbers"; break-point over-performance does not carry year to year. González-Díaz et al. [R49] disagree.
* **Rest-day differences at Slams: no effect (Reported, [R14]).**
* **Serving first in a tiebreak: no effect (Reported, [R53]).**
* **Head-to-head is weaker than rank (Reported, [R62]).**
* **The left-hander edge has faded among elite men (Reported, [R23]).**
* **Travel disrupts sleep but not WTA results (Reported, Maynard et al., project note).**
* **Profits in the literature vanish on correction (Reported, project notes).** Lyócsa and Výrost: 40 tennis rules after data-snooping correction. Ramirez et al.: buzz profits on replication. Hubáček and Šír: decorrelation fails when the market is the less biased side.
* **Leakage and look-ahead examples (Reported / Inferred).**
  * Gao and Kowalczyk claim above 80% accuracy, "much greater than betting odds". The design uses a random train/test split, and serve features without the "past 12 months" window given for other features, so very likely same-match statistics [R42].
  * Buhamra's profits come from leave-one-tournament-out cross-validation [R47].
  * Several 2024–25 arXiv papers model in-match "momentum" with time-series, transformer and state-space models (for example 2404.13300, 2408.01544, 2409.10176, 2505.21882). They predict point or game outcomes within matches, mostly Wimbledon 2023. They are not pre-match forecasts (titles and abstracts from search results; not read).

## 4. What practitioners actually use

* **Tennis Abstract (Sackmann).**
  * Ratings: surface Elo blended 50/50 with overall Elo (project note).
  * Analyses compare results against surface-Elo expectations, never against odds. Topics: style and upsets, fatigue, height, handedness, surface speed, clutch persistence [R60–R68].
  * One betting post is a match-fixing anecdote ([Westerhof v Van Der Duim, 11 Aug 2014](https://www.tennisabstract.com/blog/2014/08/11/westerhof-van-der-duim-and-a-strong-whiff-of-match-fixing/)).
* **Betfair Data Scientists, 2019 Australian Open datathon.** Inputs are differences in serve-win ratio, return-win ratio, games won, break points per game and rank; scored by log loss [R71]. No interactions.
* **GitHub and Kaggle-style repositories.**
  * Logistic or SGD models on Elo, PCA serve/return indices, head-to-head and age difference; random 70/30 splits; about 66% accuracy; no comparison with odds [R72].
  * Ultimate Tennis Statistics' "Tennis Crystal Ball": a neural network of about 60 neurons on past results (claim [R73]).
* **Pinnacle and Sports Trading Network (Buchdahl).** Calibration of closing lines and the closing-line-value logic [R31; project note].
* **Blogs, Substack, Medium, Reddit.** The sweep found tutorials and tipping services that cite closing-line value but publish no evaluated closing-line results. Example: a surface-Elo tutorial whose single worked match "proves nothing" by its own statement [R74]. Reddit threads were not reachable through the search tool (**Unknown**).
* **Kovalchik's *On the T* blog.** Returned 403 and could not be read. Her published work is cited through [R59], [R59b] and project notes.

## 5. Unknowns that no source settles

* **Whether prices apply the serve-level (sum) effect** of idea 1. No test exists, apart from one thesis's grass-underdog returns.
* **Whether serve and return combine additively.** Barnett–Clarke is additive on the probability scale; Ingram and Kovalchik use the logit scale. No paper tests a point-level server × returner interaction. The Server Quality Score authors say explicitly they do not model it [R48]. **Inferred:** the choice of scale is itself an interaction choice. A logit-additive truth looks like an interaction on the probability scale, and vice versa.
* **Whether the context-dependent favourite–longshot bias survives** sharp or average closing odds with a margin-aware de-vig. No split by sex was reported.
* **Pre-match overreaction to recent results** (big wins, titles, upsets). Only in-play evidence exists [R36, R38]. Practitioner "recency bias" claims carry no data.
* **Fatigue, home, heat, altitude, height and handedness measured against odds.** Every study controls for rank or Elo only.
* **Player-specific best-of-five ability, clutch ability, and "focus".** Persistence is disputed or untested [R13b, R49, R67, R68].

## 6. Limits of this review

* **Not read in full** (paywalled, blocked or unreachable on 6 Oct 2026):
  * Klaassen & Magnus 2003 (Tilburg returned 403; described through Gollub [R39]).
  * Barnett & Clarke 2005 (Victoria University repository unreachable; formula quoted by Gollub and Sipko).
  * Kovalchik 2016 full text (same repository; project note).
  * Wilkens 2021 and Gao & Kowalczyk 2021 journal versions (Sage 403; preprint read for the latter).
  * Buhamra et al. 2024 (JSA 403; dissertation summary read).
  * Forrest & McHale 2007 (ResearchGate 403).
  * Abinzano et al. 2016 and the Navarra theses (repository unreachable).
  * The 2026 MDPI *Analytics* tennis benchmark (403).
  * Kovalchik & Ingram's MIT Sloan paper on mental skills (not located).
* **Summaries via the fetch tool.** Some numbers come from page summaries rather than my own extraction: Pollard et al., Sackmann's posts, Loffing et al. and Buchdahl. PDFs were extracted directly where possible.
* **No quantitative source is a closing-line test** of the ideas in §1 except those marked. Profit figures are backtests at soft, best-of-many or average prices.

## References

Accessed 6 October 2026 unless marked **project note**. Columns:

* **Type**: PR peer-reviewed, PP preprint or working paper, TH thesis, PR-C conference abstract, BL blog or practitioner, PN press or news.
* **OOS?**: evaluated out of sample.
* **Close?**: evaluated against closing odds.

### Structural and point models

| # | Citation | Type | Data | OOS? | Close? | Key finding | Read |
|---|---|---|---|---|---|---|---|
| R1 | Klaassen, F. & Magnus, J. (2001). Are points in tennis independent and identically distributed? *JASA* 96(454):500–509. [PDF](https://www.janmagnus.nl/papers/JRM057.pdf) | PR | Wimbledon 1992–95, 481 matches, 86,298 points | n/a | n/a | Effects in §2.2; weaker players deviate more | full |
| R2 | Newton, P. & Keller, J. (2005). Probability of winning at tennis I. *Stud. Appl. Math.* 114:241–269. [PDF](https://sites.usc.edu/newtonlab/files/2020/06/SAM2005.pdf) | PR | 2002 US Open and Wimbledon | n/a | n/a | iid recursions; set and match probability independent of first server | full |
| R3 | O'Malley, A.J. (2008). Probability formulas and statistical analysis in tennis. *JQAS* 4(2). doi:10.2202/1559-0410.1100. [record](https://hcp.hms.harvard.edu/publication/probability-formulas-and-statistical-analysis-tennis) | PR | 2007 Wimbledon | n/a | n/a | Closed-form game, tiebreak, set and match formulas | abstract |
| R4 | Newton, P. & Aslam, K. (2009). Monte Carlo tennis: a stochastic Markov chain model. *JQAS* 5(3) art. 7. doi:10.2202/1559-0410.1169. [PDF](https://sites.usc.edu/newtonlab/files/2020/04/JQA2009.pdf) | PR | 2007 ATP | simulation | no | P(A) = 0.677 − 0.826·SD_A (favourite); variance helps the underdog | full |
| R5 | Ingram, M. (2019). A point-based Bayesian hierarchical model to predict the outcome of tennis matches. *JQAS* 15(4):313–325. doi:10.1515/jqas-2018-0008. [PDF](https://martiningram.github.io/papers/bayes_point_based.pdf) | PR | ATP to 2014; test 2014 | yes | no | 68.8% / log loss 0.592 against Barnett–Clarke 0.641 and Elo 0.586. Additive logit, no server × returner term. Tournament intercepts ±0.15 | full |
| R6 | Toevank, F. & Wolters, M. (c. 1997). De geringe praktische toepasbaarheid van de beschrijving van een tenniswedstrijd als een stochastisch proces: een reactie (Dutch; reply to Magnus & Klaassen). [PDF](https://www.vvsor.nl/wp-content/uploads/2020/06/KM1997054007.pdf) | commentary | simulation | n/a | n/a | Match probability very sensitive to p₁, p₂, which are hard to estimate precisely | full |
| R7 | Klaassen, F. & Magnus, J. (2003). Forecasting the winner of a tennis match. *EJOR* 148(2):257–267. [record](https://repository.tilburguniversity.edu/items/80a54108-ed3f-4bb7-ac82-1fd090604e4a) | PR | Wimbledon | in-match | no | Sum of serve probabilities fixed per tournament, difference from rankings (via R39) | secondary |
| R8 | Barnett, T. & Clarke, S. (2005). Combining player statistics to predict outcomes of tennis matches. *IMA J. Manag. Math.* 16(2):113–120. [record](https://vuir.vu.edu.au/8502/) | PR | one match illustrated | no | no | f_ij = f_t + (f_i − f_av) − (g_j − g_av): additive serve/return combination | secondary |
| R9 | Klaassen, F. & Magnus, J. (2014). *Analyzing Wimbledon*. OUP. [listing](https://www.shakes.cz/ebook/978-0-19-935597-6) | book | Wimbledon | – | – | Forecasting chapter has sections "Effect of smaller p̄" and "Effect of larger p̄" | table of contents |
| R10 | Knottenbelt, W., Spanias, D. & Madurska, A. (2012). A common-opponent stochastic model. *Comput. Math. Appl.* 64(12):3820–3827. [link](https://www.sciencedirect.com/science/article/pii/S0898122112002106) | PR | ATP 2011, 2,173 matches | yes | yes (soft) | +3.8% ROI claim (2011); in Sipko's 2013–14 re-test, positive ROI but log loss 0.6228, loss-making in 2014 | secondary (R40) |
| R11 | Spanias, D. & Knottenbelt, W. (2013). Predicting the outcomes of tennis matches using a low-level point model. *IMA J. Manag. Math.* 24(3):311–320 | PR | – | – | – | Ace, double-fault and serve-phase point model | citation only |
| R12 | Madurska, A. (2012). Set-by-set model, Imperial MEng | TH | 2011 WTA Slams | yes | yes (soft) | +19.6% ROI claim on a small sample (via R40) | secondary |

### Hierarchical, ML and recent models

| # | Citation | Type | Data | OOS? | Close? | Key finding | Read |
|---|---|---|---|---|---|---|---|
| R39 | Gollub, J. (2017). Producing win probabilities for professional tennis matches from any score. Harvard BA thesis. [PDF](https://dash.harvard.edu/server/api/core/bitstreams/dc501d43-9be0-4c8a-8066-480bd5ff5be5/content) | TH | ATP 2011–14; test 2014 (2,409 matches) | yes | no | Log loss: Barnett–Clarke 0.649; James–Stein 0.616; Elo 0.586; Elo + surface Elo 0.577. Klaassen–Magnus inversion with a fixed sum | full |
| R40 | Sipko, M. (2015). Machine learning for the prediction of professional tennis matches. Imperial MEng. [PDF](https://www.doc.ic.ac.uk/teaching/distinguished-projects/2015/m.sipko.pdf) | TH | OnCourt ATP 2004–14; test 2013–14, 6,315 matches | yes | Pinnacle ROI only | Test log loss 0.6129 (LR), 0.6122 (LR + interactions), 0.6111 (ANN). Kelly ROI 4.17 / 4.08 / 4.35%. Interactions overfit validation | full |
| R41 | Wilkens, S. (2021). Sports prediction and betting models in the machine learning age: the case of tennis. *JSA* 7(2):99–117. [doi](https://journals.sagepub.com/doi/10.3233/JSA-200463) | PR | ATP+WTA | yes | yes | Accuracy capped at about 70%; cannot beat odds-implied forecasts; returns mainly negative | abstract |
| R42 | Gao, Z. & Kowalczyk, A. (2021). Random forest model identifies serve strength as a key predictor of tennis match outcome. *JSA* 7(4):255–262; [arXiv:1910.03203](https://arxiv.org/abs/1910.03203) | PR/PP | ATP 2000–16 | random split | claims beats odds | Above 80% accuracy; likely leakage (§3) | full (preprint) |
| R43 | Penn, Michael & Bhatt (2025). Dynamic graph-based forecasts of bookmakers' odds in professional tennis. arXiv:2508.15956; journal version doi:10.1098/rsos.252512 | PP/PR | Slams 2024–25 | yes | parity | Forecasts the odds (project note) | project note |
| R44 | Clegg, L. & Cartlidge, J. (2025/2026). Capturing intransitive dominance in tennis forecasting: a graph neural network approach. [arXiv:2510.20454](https://arxiv.org/abs/2510.20454) v1 23 Oct 2025, v2 18 Jun 2026 | PP | ATP+WTA, test 2023–25 | yes | yes (Pinnacle) | 65.7% / Brier 0.214. v1 subset ROI +3.26% removed in v2. Complements WElo; no gain over Pinnacle | abstract v2; v1/v2 project note |
| R45 | Chen, S. & Joachims, T. (2016). Modeling intransitivity in matchup and comparison data. WSDM. [record](https://aminer.org/pub/5736975f6e3b12023e647c0b) | PR-C | games and sports | yes | no | Blade–chest vectors capture intransitivity | abstract |
| R46 | Buhamra, N. & Groll, A. (2025). Statistical enhanced learning for modeling and prediction tennis matches at Grand Slam tournaments. [arXiv:2502.01613](https://arxiv.org/abs/2502.01613) | PP | men's Slams 2011–22, 5,013 matches | expanding window | no | RF classification rate 0.820, Brier 0.151; splines Brier 0.149. Age.30 × Elo interaction in dependence plots | full (HTML) |
| R47 | Buhamra, N. (2025). Classic statistical and modern machine learning methods for modeling and prediction of major tennis tournaments. PhD, TU Dortmund. [text](https://eldorado.tu-dortmund.de/server/api/core/bitstreams/1c6a69df-ca85-4747-b3e1-704334f1e247/content); article: Buhamra et al. (2024) *JSA*, doi:10.3233/JSA-240670 | TH/PR | as R46, with OddsPortal average odds | leave-one-tournament-out + 2022 | average odds | Spline on odds: +113.7 units on 1,170 bets; odds benchmark −311.4 | partial |
| R48 | Li, A., Balajee, A., Wieand, H. & Pipping-Gamón, J. (2026). A unified server quality metric for tennis. [arXiv:2602.08083](https://arxiv.org/abs/2602.08083) | PP | Wimbledon and US Open point-by-point | – | no | Mixed model, server and returner intercepts; explicitly no server × returner interaction | abstract + search excerpt |
| R48b | Schwaderer, J. et al. (2026). Topological data analysis and graph-theoretic approaches for tennis match prediction. [arXiv:2607.23509](https://arxiv.org/abs/2607.23509) | PP | ATP 2000–25, about 66,000 matches | unclear | no | RF 66.2%, AUC 0.719 | abstract |
| R48c | Xie, C. & Muppidi, A. (2026). Forecasting the winner of a live tennis match. [arXiv:2609.07617](https://arxiv.org/abs/2609.07617) | PP | Slams 2011–24 point-by-point, 8,222 matches | chronological | no | In-play hybrid; peripheral | partial |
| R48d | Jäger, B. et al. (2026). TabPFN-3.5 technical report. [arXiv:2609.17895](https://arxiv.org/abs/2609.17895) | PP | – | – | – | Says nothing on interactions in the abstract; no sports application of tabular foundation models found | abstract |

### Context effects

| # | Citation | Type | Data | OOS? | Close? | Key finding | Read |
|---|---|---|---|---|---|---|---|
| R13 | Pollard, G., Cross, R. & Meyer, D. (2006). An analysis of ten years of the four Grand Slam men's singles data for lack of independence of set outcomes. *JSSM* 5(4):561–566. [link](https://www.jssm.org/jssm-05-561.xml-Fulltext) | PR | men's Slams 1995–2004, 4,883 matches | no | no | +0.035 / +0.110 set dependence | full (fetch) |
| R13b | Sackmann, J. (16 Jan 2014). Better at best-of-five. [post](https://www.tennisabstract.com/blog/2014/01/16/better-at-best-of-five/) | BL | ATP Slams and non-Slams | no | no | Tsonga 1.19, Berdych 1.12, Safin +14% / −10%; no persistence test | full |
| R14 | Goossens, D., Kempeneers, J., Koning, R. & Spieksma, F. (2015). Winning in straight sets helps in Grand Slam tennis. *IJPAS* 15(3):1007–1021. [PDF](https://fspieksma.win.tue.nl/papers/IJPAS2015paper.pdf) | PR | Slams 1992–2011, 20,320 matches | no | no (rank only) | Idea 4 | full |
| R15 | O'Donoghue, P. (2006). The advantage of playing less sets than the opponent in the previous two rounds of Grand Slam tennis tournaments. *J. Sports Sci.* 24(4):344. [record](https://lida.sport-iat.de/ta/Record/3039576?lng=en) | PR-C | 2002 Slams, 243 matches | no | no | Women affected, men not | abstract |
| R16 | Koning, R. (2011). Home advantage in professional tennis. *J. Sports Sci.* [record](https://lida.sport-iat.de/twm/Record/4022195?lng=en) | PR | ATP and WTA | no | no | Men significant, women none | abstract/secondary |
| R17 | Gucciardi, G. & Ruberti, M. (2025). Individual performance and environment: home advantage in ATP tennis. *JEBO* 238:107236. doi:10.1016/j.jebo.2025.107236. [PDF](https://iris.uniupo.it/bitstream/11579/215763/1/GR_JEBO_2025.pdf) | PR | ATP 2000–22, 59,067 matches | no | no | Idea 5 | full |
| R18 | Creutzburg, C., Maennig, W. & Mueller, S. (2024). From bias to bliss: racial preferences and worker productivity in tennis. Hamburg WP 75. [record](https://econpapers.repec.org/paper/hcewpaper/075.htm) | PP | men 2001–20 | no | no | Black players benefit more from fan support | abstract |
| R19 | Söğüt, M. (2019). Height- and surface-related variations in match-play outcomes and rankings in professional men's tennis. *Ger. J. Exerc. Sport Res.* doi:10.1007/s12662-019-00612-2. [record](https://avesis.metu.edu.tr/yayin/9defd904-f37a-4fcb-bbaf-7f3cfb2f7bed/height-and-surface-related-variations-in-match-play-outcomes-and-rankings-in-professional-mens-tennis) | PR | ATP top 100, 3 height groups | no | no | Tallest: more aces and first-serve points on all surfaces. Shortest: better second-serve return on clay | abstract |
| R20 | Ma, S.-M., Liu, C.-C., Tan, Y. & Ma, S.-C. (2013). Winning matches in Grand Slam men's singles. *J. Sports Sci.* 31(11):1147–1155. [record](https://lida.sport-iat.de/ta/Record/4029823) | PR | men's Slams 1991–2008 | no (in-match statistics) | no | Benefit of stature diminishes above 186 cm | abstract |
| R21 | Smith, M., Reid, M., Kovalchik, S., Woods, T. & Duffield, R. (2018). Heat stress incident prevalence and tennis matchplay performance at the Australian Open. *JSAMS*. doi:10.1016/j.jsams.2017.08.019. [AM PDF](https://opus.lib.uts.edu.au/bitstream/10453/129211/4/Smith%20et%20al%20JSMAS%202018.pdf) | PR | men's AO 2014–16, 360 matches | no | no | §2.2 | full |
| R21b | Kahraman, G., Turp, M.T. & An, N. (2026). EGU26-16816. [abstract](https://meetingorganizer.copernicus.org/EGU26/EGU26-16816.html) | PR-C | AO, ERA5 heat index | no | no | Heat: more errors and longer matches; lower seeds take more risk | abstract |
| R22 | Sánchez Pay, A., Otálora Murcia, F.J. & Sánchez-Alcaraz Martínez, B.J. (2019). Influence of high altitude on competition demands of professional tennis on hard and clay surface. *Cultura, Ciencia y Deporte* 14(42). [record](https://repositorio.ucam.edu/handle/10952/5980) | PR | 122 ATP 250 matches | no | no | Altitude raises aces and serve points | abstract |
| R23 | Loffing, F., Hagemann, N. & Strauss, B. (2012). Left-handedness in professional and amateur tennis. *PLoS ONE* 7(11):e49325. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3492260) | PR | rankings 1973/75–2011; Slams 1968–2011 | no | no | Elite advantage declined and is gone for men; persists at amateur level | full (fetch) |
| R24 | Breznik, K. (2013). On the gender effects of handedness in professional tennis. *JSSM* 12:346–353. [abstract](https://www.jssm.org/jssm-12-346.xml-abst) | PR | 438,937 men's and 415,346 women's matches, 1968–2011 | no | no | Lefty advantage larger for men; inversely related to player and match quality | abstract |
| R25 | Sackmann, J. (10 Nov 2011). Win probability tables for righties and lefties. [post](https://tennisabstract.com/blog/?p=562) | BL | 2011 Slams | no | no | Deuce/ad asymmetry; about +2 points for lefties at 30–40 and 40–AD | full (fetch) |
| R26 | Sackmann, J. (6 Feb 2021). Everybody's a tricky lefty. [post](https://www.tennisabstract.com/blog/2021/02/06/everybodys-a-tricky-lefty/) | BL | ATP and WTA rankings | no | no | 15 lefties in ATP top 100 (about 4% chance); WTA under-represented | full (fetch) |

### Markets

| # | Citation | Type | Data | OOS? | Close? | Key finding | Read |
|---|---|---|---|---|---|---|---|
| R27 | Forrest, D. & McHale, I. (2007). Anyone for tennis (betting)? *Eur. J. Finance* 13(8):751–768. [record](https://ideas.repec.org/a/taf/eurjfi/v13y2007i8p751-768.html) | PR | men's matches | no | soft odds | Positive (favourite) bias throughout the odds range | abstract |
| R28 | Lahvička, J. (2014). What causes the favourite-longshot bias? Further evidence from tennis. *Appl. Econ. Lett.* 21(2):90–92; WP: [MPRA 47905](https://mpra.ub.uni-muenchen.de/47905/1/MPRA_paper_47905.pdf) | PR/PP | Bet365 latest odds; men 2002–13, women 2007–13; 44,871 matches | no | Bet365 latest | Coefficients in §1, note 2 | full (WP) |
| R29 | Abinzano, I., Muga, L. & Santamaria, R. (2016). Game, set and match: the favourite-long shot bias in tennis betting exchanges. *Appl. Econ. Lett.* 23(8):605–608. doi:10.1080/13504851.2015.1093074. [record](https://observatorio-investigacion.unavarra.es/documentos/5f8e8f5d2999527b469ff7ae) | PR | exchange | no | exchange | Bias rises with volume and attention; stronger for lower-ranked players, later rounds, high-profile events | abstract |
| R30 | Whelan, K. (2023). Risk aversion and favorite-longshot bias in a competitive fixed-odds betting market. [MPRA 116923](https://mpra.ub.uni-muenchen.de/116923/1/MPRA_paper_116923.pdf) | PP | tennis-data, ATP+WTA 2011–Jun 2022, 56,004 matches | no | average odds | Loss rate rises toward longshots | partial |
| R31 | Buchdahl, J. (undated). How efficient is the tennis betting market? Sports Trading Network. [article](https://www.sportstradingnetwork.com/article/how-efficient-is-the-tennis-betting-market/) | BL | Pinnacle opening and closing, ATP/WTA/Challenger/ITF, 12 May 2015–19 Jul 2019, 68,361 matches | – | yes | 10% implied won 6%; open/close gradient 0.825; tipster beats the close by about 3% | full (fetch); claims |
| R32 | Candila, V. & Scognamillo, A. (2018). Estimating the implied probabilities in the tennis betting market: a new normalization procedure. *Int. J. Sport Finance* 13:225–242. [record](https://ideas.repec.org/p/sep/wpaper/3_236.html) | PR | over 27,000 men's matches | yes | one bookmaker | CASCO normalisation forecasts better than other de-vig methods | abstract |
| R32b | Clarke, S., Kovalchik, S. & Ingram, M. (2017). Adjusting bookmaker's odds to allow for overround. *Am. J. Sports Sci.* 5(6):45–49. [link](https://www.sciencepublishinggroup.com/article/10.11648/j.ajss.20170506.12) | PR | tennis | – | – | Power method; flaws of additive, normalisation and Shin methods | abstract |
| R33 | van Rheenen, S. (2017). The sentiment bias in the market for tennis betting. MSc thesis, Erasmus. [PDF](https://thesis.eur.nl/pub/38118/Rheenen-S-van-347986-MA-thesis.pdf) | TH | men's Slams 2000–16 + Google Trends | no | soft odds | Reversed sentiment bias in finals and Big Four matches; not exploitable | partial |
| R34 | Scheibehenne, B. & Bröder, A. (2007). Predicting Wimbledon 2005 tennis results by mere player name recognition. *IJF* 23(3):415–426. [record](https://ideas.repec.org/a/eee/intfor/v23y2007i3p415-426.html) | PR | Wimbledon 2005 | yes | odds | Recognition 70% ≈ rankings; odds more accurate | abstract |
| R35 | van 't Leven, L. (2013). The favorite longshot bias in tennis tournaments. Thesis, Erasmus. [record](https://thesis.eur.nl/pub/13970/) | TH | Bet365 ATP 2010–12 | no | Bet365 | Grass underdogs positive; home bets lose a third as much | abstract |
| R36 | Easton, S. & Uylangco, K. (2010). Forecasting outcomes in tennis matches using within-match betting markets. *IJF* 26(3):564–575. [record](https://ideas.repec.org/a/eee/intfor/v26yi3p564-575.html) | PR | in-play | – | in-play | Efficient; post-break dip not priced at once | abstract |
| R37 | Barrutiabengoa Ortubai, J.M. (2019). Behaviour of the over-round in tennis betting markets. BA thesis, UPNA. [record](https://academica-e.unavarra.es/xmlui/handle/2454/34197) | TH | ATP and WTA | no | – | WTA overround higher | abstract (via search) |
| R38 | Lobão, J. & Rolla, N.M. (2015). Another look at the efficiency of markets: the case of the tennis betting exchanges. *RAE* 55(4). [record](https://ideas.repec.org/a/fgv/eaerae/v55y2015i4a52958.html) | PR | Betfair in-play | – | exchange | Behavioural biases; profitable rules claimed | abstract |

### Clutch, momentum, consistency, structure of upsets

| # | Citation | Type | Data | OOS? | Close? | Key finding | Read |
|---|---|---|---|---|---|---|---|
| R49 | González-Díaz, J., Gossner, O. & Rogers, B. (2012). Performing best when it matters most: evidence from professional tennis. *JEBO* 84(3):767–781. doi:10.1016/j.jebo.2012.09.021. [record](https://ideas.repec.org/a/eee/jeborg/v84y2012i3p767-781.html) | PR | US Open, 12 years of point data | persistence | no | Player-specific "critical ability" persists and tracks career success | abstract |
| R50 | Gauriot, R. & Page, L. (2019). Does success breed success? *Econ. J.* 129(624):3107–3136. [record](https://ideas.repec.org/a/oup/econjl/v129y2019i624p3107-3136..html) | PR | Hawk-Eye close calls | causal | no | Point momentum for men, not women | abstract |
| R51 | Meier, P., Flepp, R., Ruedisser, M. & Franck, E. (2020). Separating psychological momentum from strategic momentum. *J. Econ. Psychol.* 78. [record](https://ideas.repec.org/a/eee/joepsy/v78y2020ics016748702030026x.html) | PR | 141 men's Slam matches, 4,930 games | quasi-experiment | no | Momentum after a converted break point, blunted by interruptions | abstract |
| R52 | Page, L. & Coates, J. (2017). Winner and loser effects in human competitions. *Evol. Hum. Behav.* 38:530–535. [summary](https://www.daedalustrust.com/winner-and-loser-effects-in-human-competitions-evidence-from-equally-matched-tennis-players-2017/) | PR | equally matched pros | quasi-experiment | no | About 60/40 in the next set (men only) | abstract |
| R53 | Cohen-Zada, D., Krumer, A. & Shapir, O.M. (2018). Testing the effect of serve order in tennis tiebreak. *JEBO* 146:106–115. [record](https://cris.bgu.ac.il/en/publications/testing-the-effect-of-serve-order-in-tennis-tiebreak-2/) | PR | 2,621 tiebreaks, 2012–15 | – | no | No first-server effect | abstract |
| R59 | Kovalchik, S. (9 Aug 2015). Are women professional tennis players really less consistent than male players? JSM 2015 press Q&A. [PDF](https://www.amstat.org/asa/files/pdfs/pressreleases/JSM2015-QA-TennisPerformance.pdf) | PN | ATP and WTA 2010–14 | no | no | Upsets 31.5% (WTA) against 29.6% (ATP); format explains the Slam gap; best of five worth 7–10 points | full |
| R59b | Victoria University (23 Nov 2017). Measuring mental skills of tennis. [news](https://www.vu.edu.au/news-events/news/measuring-mental-skills-of-tennis) | PN | 3 million points, about 20,000 matches, 858 players, 2011–15 | – | no | Mental profiles (Kovalchik) | full |
| R60 | Sackmann, J. (14 Jan 2019). What I should've known about playing styles and upsets. [post](https://www.tennisabstract.com/blog/2019/01/14/what-i-shouldve-known-about-playing-styles-and-upsets/) | BL | about 11,000 ATP matches, 106 charted players since 2010 | no | no (Elo) | Aggressive × aggressive matches least predictable; conservative pairs most | full (tables not rendered) |
| R61 | Sackmann, J. (2 Jun 2017). The negative impact of time of court [sic]. [post](https://www.tennisabstract.com/blog/2017/06/02/the-negative-impact-of-time-of-court/) | BL | over 7,200 men's Slam matches since 2001 | no | no (surface Elo) | Ratio 1.07 → 0.76 | full (fetch) |
| R61b | Sackmann, J. (9 Aug 2012). The hangover effect of a marathon fifth set. [post](https://www.tennisabstract.com/blog/2012/08/09/the-hangover-effect-of-a-marathon-fifth-set/) | BL | 146 Slam fifth sets reaching 6–6 | no | no | 29.5% against 43.4% expected | full (fetch) |
| R61c | Sackmann, J. (30 May 2017). Bouncing back from a marathon third set. [post](https://www.tennisabstract.com/blog/2017/05/30/bouncing-back-from-a-marathon-third-set/) | BL | 185 WTA Slam marathon third sets | no | no | 42.2% against 44.0% expected (little effect) | full (fetch) |
| R62 | Sackmann, J. (19 Jan 2014). The limited value of head-to-head records. [post](https://www.tennisabstract.com/blog/2014/01/19/the-limited-value-of-head-to-head-records/) | BL | ATP since 1996 | no | no | 66.0% against 68.5% | full (fetch) |
| R63 | Sackmann, J. (13 Sep 2011). The speed of every surface. [post](https://tennisabstract.com/blog/?p=528) | BL | ATP 2011 | – | no | Aces 53–145%; serve points within ±3% for 53 of 67 events | full (fetch) |
| R63b | Sackmann, J. (4 Sep 2017). How much does height matter in men's tennis? [post](https://www.tennisabstract.com/blog/2017/09/04/how-much-does-height-matter-in-mens-tennis/) | BL | 156 player-seasons, 1998–2017 | no | no | §2.2 | full (fetch) |
| R64 | Sackmann, J. (27 Nov 2019). The speed of every surface, 2019 edition. [post](https://www.tennisabstract.com/blog/2019/11/27/the-speed-of-every-surface-2019-edition) | BL | ATP 2019 | – | no | Chengdu 1.57 … Monte Carlo 0.50; Tour Finals 0.89 → 1.31 | full (fetch) |
| R65 | Sackmann, J. (10 Dec 2025). Surface speed convergence, one more time. [post](https://www.tennisabstract.com/blog/2025/12/10/surface-speed-convergence-one-more-time/) | BL | ATP 1991–2025 | – | no | No convergence: Wimbledon 1.13 → 1.14, Monte Carlo 0.58 → 0.57 | full (fetch) |
| R66 | Sackmann, J. (11 Jul 2019). Slow conditions might just flip the outcome of Federer–Nadal XL. [post](https://www.tennisabstract.com/blog/2019/07/11/slow-conditions-might-just-flip-the-outcome-of-federer-nadal-xl/) | BL | 39 matches | in-sample | no | Speed rating × matchup; 49.3% → 59.5% from speed 1.0 to 1.5 | full (fetch) |
| R67 | Sackmann, J. (2 Jan 2019). The effect of tiebreak luck. [post](https://www.tennisabstract.com/blog/2019/01/02/the-effect-of-tiebreak-luck/) | BL | ATP | year to year | no | Tiebreak over-performance does not persist | full (fetch) |
| R68 | Sackmann, J. (8 Sep 2015). Break point persistence: why Venus is better than her ranking. [post](https://www.tennisabstract.com/blog/2015/09/08/break-point-persistence-why-venus-is-better-than-her-ranking/) | BL | WTA | year to year | no | Break-point over-performance does not persist | full (fetch) |
| R69 | Sackmann, J. (1 Dec 2025). The decline of specialization (or, the rising floor). [post](https://www.tennisabstract.com/blog/2025/12/01/the-decline-of-specialization-or-the-rising-floor/) | BL | ATP top 50, 1991–2025 | – | no | Hold and break ranks increasingly correlated | full (fetch) |
| R70 | Sackmann, J. (3 Sep 2018). Two servebots and zero tiebreaks. [post](https://www.tennisabstract.com/blog/2018/09/03/two-servebots-and-zero-tiebreaks/) | BL | one match | – | no | Isner–Raonic holds 96.0% and 91.7% | full (fetch) |

### Practitioner code and tutorials

| # | Citation | Type | Key point | Read |
|---|---|---|---|---|
| R71 | Betfair Data Scientists. aus-open-datathon (2019). [GitHub](https://github.com/betfair-datascientists/aus-open-datathon) | BL/code | Difference features; log-loss scoring | full (fetch) |
| R72 | BrandoPolistirolo. Tennis-Betting-ML. [GitHub](https://github.com/BrandoPolistirolo/Tennis-Betting-ML) | code | Elo, EMA, PCA serve/return, head-to-head; random 70/30 split; 66% | full (fetch) |
| R73 | Ultimate Tennis Statistics. About / Tennis Crystal Ball. [site](https://ultimatetennisstatistics.com/about) | BL | Neural network of about 60 neurons on past results (claim) | search snippet |
| R74 | OddsPapi. Tennis ELO model in Python: beat the closing line with free historical odds. [blog](https://oddspapi.io/blog/tennis-elo-model-python/) | BL | Tutorial, no evaluated results | full (fetch) |
| R75 | Sackmann, J. Aging-curve posts: "Forecasting Future Felix with ATP aging patterns" ([post](https://www.tennisabstract.com/blog/?p=3494)) and "WTA aging patterns and Bianca Andreescu's future" (30 Mar 2019, [post](https://www.tennisabstract.com/blog/2019/03/30/wta-aging-patterns-and-bianca-andreescus-future/)) | BL | Over 700 ATP players born 1960–89: peak about 25, small differences 24–27; WTA peak 23–24 (Elo-based) | search snippet |

### Project notes relied on (not re-read)

Their sources are listed in those notes.

* [Market anchoring](../../../research/market-anchoring/README.md): Benter; Kaunitz; Hubáček & Šír; Candila & Palazzo 2020; Vaughan Williams et al. 2021; Clegg & Cartlidge v1/v2; Ramirez et al. 2023 and its correction; Goto et al. 2026; Lyócsa & Výrost 2018; Pinnacle articles; Lisi & Zanella 2017.
* [Rating systems](../../../research/rating-systems/README.md): Kovalchik 2016; Gorgi, Koopman & Lit 2019; Ingram 2019 and 2021; Angelini et al. 2022; Bunker et al. 2024; Duffield et al. 2024; Bozóki et al. 2016.
* [Predictive frontier register](../../predictive_frontier/research.md): Gollub 2021; Wang & Drekic 2026; Kovalchik & Albert 2022; Maynard et al. 2025; Picchio & van Ours 2024; Penn et al. 2025.

## Appendix A: the iid computation (Computed here)

Standard Newton–Keller / O'Malley recursions.

* **Game.** The server holds with p⁴(1 + 4q + 10q²) + 20p³q³ · p²/(p² + q²), where q = 1 − p.
* **Tiebreak.** First to 7, win by 2, serve order ABBA…. From 6–6 each pair of points is one A serve and one B serve, so P = p_A(1 − p_B) / [p_A(1 − p_B) + (1 − p_A)p_B].
* **Set.** First to 6 games, 7–5, or a tiebreak at 6–6, with A serving first (the set probability does not depend on the first server).
* **Match.** First to 2 or 3 sets.
* **Slopes.** Central differences of the match log-odds at p_A = p̄ ± 0.005.
* **Bound.** Solve for the difference d that gives P₀ at the reference p̄, then re-evaluate at other p̄ with the same d. Excess expected log loss = KL(P_true ‖ P₀) = P ln(P/P₀) + (1 − P) ln[(1 − P)/(1 − P₀)].

```python
def p_game(p):
    q = 1 - p
    return p**4 * (1 + 4*q + 10*q*q) + 20 * (p*q)**3 * p*p / (p*p + q*q)

def p_tiebreak(pa, pb):                         # A serves point 1, then B, B, A, A, ...
    from functools import lru_cache
    @lru_cache(None)
    def tb(a, b):
        if a >= 7 and a - b >= 2: return 1.0
        if b >= 7 and b - a >= 2: return 0.0
        if a >= 6 and a == b:
            w, l = pa*(1-pb), (1-pa)*pb
            return w / (w + l)
        n = a + b
        pt = pa if n % 4 in (0, 3) else 1 - pb
        return pt*tb(a+1, b) + (1-pt)*tb(a, b+1)
    return tb(0, 0)

def p_set(pa, pb):
    from functools import lru_cache
    ga, gb, t = p_game(pa), p_game(pb), p_tiebreak(pa, pb)
    @lru_cache(None)
    def s(a, b):
        if (a == 6 and b <= 4) or a == 7: return 1.0
        if (b == 6 and a <= 4) or b == 7: return 0.0
        if a == 6 and b == 6: return t
        pg = ga if (a + b) % 2 == 0 else 1 - gb
        return pg*s(a+1, b) + (1-pg)*s(a, b+1)
    return s(0, 0)

def p_match(pa, pb, best_of=3):
    from functools import lru_cache
    st, need = p_set(pa, pb), best_of // 2 + 1
    @lru_cache(None)
    def m(a, b):
        if a == need: return 1.0
        if b == need: return 0.0
        return st*m(a+1, b) + (1-st)*m(a, b+1)
    return m(0, 0)
```

**Checks.** p_match(p, p) = 0.5 for every p. The best-of-five to best-of-three log-odds ratio is constant at 1.25 across p̄. Results match §2.1 and the table in idea 1.
