# Best practice: using lower-level evidence without treating it as equivalent

9 October 2026 · Team role 05 (best-practice researcher) of the lower-level-evidence study · Research evidence, not a decision.

**Note added by the lead (9 Oct 2026).** This report was written before the owner's [decision of 9 Oct](../../../decisions/2026-10-09-adoption-framework.md) that adopts the adoption framework as guiding principles and retires "tie". Read "tie" as "unresolved" (the 95% interval spans 0), and "the adoption framework" as adopted, not proposed.

**The question.** What do sports analytics, statistics and betting practice say about using lower-tier data to inform top-tier forecasts without treating it as equivalent? What does that imply for this project?

**Keys.**
* **Measured** = a source's own data, results or documented method. **Claimed** = a source's interpretation or opinion. **Inferred** = my reasoning. **Suggestion** = a proposal for the owner. **Not found** = searched for and not found.
* Sources are numbered [S1]–[S66]; the list at the end gives each URL and how much was read (full text, abstract only, secondary summary, citation only). **All were accessed on 9 October 2026.** "Web reader" means the page was read through a summarising fetch tool; load-bearing numbers and quotes were re-queried verbatim where the first reading was ambiguous.
* Project facts come from the [event-levels study](../../event_levels/README.md) (EL), the [lineage audit](01_lineage.md) (01) and the [UFC-analog report](06_ufc_analog.md) (06). This report extends EL §9's literature pass; it does not repeat it.
* mLL = milli-log-loss per match. Every in-project score is quoted with its direction in words; an interval spanning 0 is a tie.
* Tooling: PDFs the web reader could not parse were converted to text with the base Miniforge Python (`C:/Users/zerom/miniforge3/python.exe`, `pypdf`) in the session scratchpad. Nothing in the repository was run or changed. One local fact was read from the installed TabPFN package (the `tennis-tabpfn-local` environment).

## In short

* **Measured (each method), inferred (the common pattern). Every mature field uses the same recipe.** (1) Translate the lower-tier evidence onto the top-tier scale, statistic by statistic. (2) Count it as fewer observations than top-tier evidence. (3) Shrink toward the mean of comparable players, not the top-tier average. (4) Let top-tier data take over as it accumulates. Baseball projections, hockey and basketball prospect models, chess federations and the owner's UFC prior all do some version of this (§1).
* **Measured. US Chess is the cleanest written example** [S20]. A FIDE rating is converted by a formula (not 1:1). It counts as 5 or 10 games, at most 10 in total, when a domestic rating is "established" only after more than 25 games. Its weight decays with age, faster for weaker players. Foreign results then update the domestic rating only for players already established.
* **Measured. Tennis ratings (and FIDE) keep lower levels in one connected pool, with level-aware add-ons.** Tennis Abstract's Elo includes Challengers, women's ITF and qualifying, and starts newcomers at a level-dependent rating [S24]. Ultimate Tennis Statistics scales its K by level [S25]. Since March 2024 FIDE adds two hypothetical drawn games against 1800-rated opponents to every newcomer's first rating [S34].
* **Measured and claimed. FIDE's 2024 reform is the warning for this project.** Newcomers entered with biased first ratings (measured) and, Sonas argues, took points from the whole connected pool, reaching even the top players (claimed) [S22]. **Inferred:** the same channel as the project's finding #6, where ITF box scores moved the IOS zero point for main-tour players.
* **Measured (other sports), inferred (tennis). Process statistics translate; opponent-dependent outcomes translate poorly; "clutch" residuals do not persist at all.** A hitter's strikeout rate is half signal after 100 plate appearances, his BABIP only after about 1,100 balls in play [S66]. College block and steal rates carry over to the NBA (r = 0.74, 0.70), defensive rebounding less (0.29) [S14]; free-throw percentage "rarely changes much" [S13]. Tennis break-point performance beyond what return points predict has no year-to-year persistence (r² = 0.002) [S31]. The project's lineage audit already sees the serve-style forms barely move with the level (01).
* **Measured and claimed. Translation estimates are biased and drift.** Players promoted after hot streaks distort them [S3][S4]. Playing time depends on performance, so exposure is not a neutral weight [S3]. Direct comparisons beat chained ones [S2]. Factors must be re-estimated after structural change [S8]; the UFC's own transfer ratio jumped from about 0.02 to 0.71 between eras (06).
* **Measured. Statistics gives the machinery a name.** Credibility (Bühlmann), empirical Bayes (Efron–Morris: 3.5 times less squared error on batting averages [S37]), partial pooling (Gelman: cross-validated error 0.79 against 0.84 and 0.86 for complete and no pooling [S38]), power, commensurate and robust priors, and Kennedy–O'Hagan's "top = ρ·lower + δ". All formalise "informative, not equivalent" as **an offset plus extra uncertainty**.
* **Measured. The installed TabPFN takes no sample weights** (`fit(self, X, y)`, [S51]). A prior therefore enters through better-built inputs, a stacked prior column, a shrunk stage-2 term, context selection or fine-tuning. The project's evidence and the UFC lessons favour the first and the third.
* **Measured and claimed. Markets are weakest at lower tiers and for newcomers, but the edges are small, noisy and fade.** The favourite–longshot bias is stronger among lower-ranked players [S53]; promoted football teams are briefly under-priced [S16]; a celebrated tennis "buzz" profit vanished when one bet was removed [S55]. Integrity alerts concentrate at exactly these levels (EL §9).
* **Suggestion. Ranked recommendations (§5):** R1 give the 17 one-step forms and `points_52w` a level term before the ITF box scores land; R2 add per-statistic level offsets and a transfer weight below 1 inside the joint solves, anchored on main-tour players; R3 give newcomers proper priors; R4 treat statistics differently by type; R5 change inputs in place rather than add columns; R6 leave the "market under-rates climbers" effect to a small stage-2 term tested on fresh seasons; R7 stake less when the forecast is less certain; R8 clean lower-level results.
* **Suggestion. The protocol (§6):** pre-registered, translations fitted walk-forward, both stages against the frozen reference, results split by main-tour exposure, a "top players unchanged" falsification check, placebo twins, the leak probe, a selection penalty, the 2025–2026 holdout sealed.

## 1. The common recipe, field by field

| Field | 1. Translate | 2. Discount | 3. Shrink toward | 4. Hand over | Source |
|---|---|---|---|---|---|
| Baseball projections | Per component. AA→MLB: home runs ×0.56, strikeouts ×1.27, walks ×0.92; AAA: ×0.74, ×1.23, ×0.85. Overall production about −26 to −28% (AAA) and −32 to −37% (AA) | Davenport: AA/AAA translations predicted next year about as well as an MLB season (148 players) | A mean weighted by the chance of reaching the majors, which depends on age relative to level | Recent seasons weighted more (5/4/3) | [S3][S1][S8][S7] |
| Baseball, Marcel | None: minor leagues ignored | — | League average: rookies project at league average; 1,200 PA of league average added to everyone | 5/4/3 | [S7] |
| Hockey (NHLe) | One factor per league from players who moved: AHL 0.53, KHL 0.71, SHL 0.54 (points per game); chained through intermediate leagues | Used as one predictor (with age, height, weight) in logistic models, not as NHL data | — | — | [S11][S12] |
| Basketball (Pelton) | 14 statistics translated one by one, adjusted for schedule strength | Seasons weighted | Positional averages of NBA rookies | — | [S13] |
| Chess (US Chess) | Piecewise formula: US = −1073 + 1.5667·FIDE (FIDE ≤ 2000); 20 + 1.02·FIDE (above) | 5 games (FIDE ≤ 2000) or 10 (above); staleness decay; total capped at 10 | Age-based rating when nothing else exists | K = 800/(N′+m): the prior's games fade as real ones accrue | [S20] |
| Chess (FIDE, 2024) | — | Two hypothetical draws against 1800 added to a newcomer's first games | First rating capped at 2200 | K = 40 until 30 games, then lower | [S34][S22] |
| Football (GAP ratings) | — | Own lower-league record ignored | A promoted team gets the average rating of last season's relegated teams | Normal updates | [S15] |
| Tennis (Tennis Abstract) | Total points won ×1.086–1.103 at Challengers (opponent-adjusted, 2012–2017) | Elo: no level weighting reported; extra weight for "important" matches did not help | Newcomers start "in the low 1200s", by level and gender | Surface rating blended 50/50 with the overall one | [S23][S24] |
| Tennis (UTS Elo) | — | K: Slam 100%, Finals 90%, Masters 85%, 500 75%, others 70% | Historical players start at the average Elo of their ranking | — | [S25] |
| Tennis (Gorgi–Koopman–Lit) | — | Main tour only | A new player's starting strength = α × log(ATP ranking points) | Score-driven updates | [S27] |
| UFC (the owner's) | Ridge from nine counts of the pre-UFC record | 0.9 × the ridge residual | A flat anchor | Fades to zero over six effective UFC fights | 06 |

**Inferred. What the table says for tennis.**
* The owner's instinct ("an average newcomer, skewed toward his lower-level record") is the standard credibility blend. The literature adds four details: translate per statistic first; give the lower-level record a pseudo-count, not a full count; let its weight decay with age; and shrink toward players *like him* (age, level, ranking), not toward the main-tour average.
* The usual discounts are modest. A converted foreign chess rating is worth at most 10 games, when a domestic one is "established" only after more than 25 and its effective count reaches 50 [S20]. The UFC prior is worth about six fights (06). Davenport's claim that AA/AAA translations are as good as a major-league season [S1] is the generous end, from 148 players.
* **The project already has an in-house template.** Stage 2's speed panel centres each edition on its own offset and shrinks it toward its family (Slam / tour / Challenger × main / qualifying) (01). That is "translate, then shrink toward the family", the same recipe.

## 2. Cross-tier translation, sport by sport

### 2.1 Baseball: minor-league equivalencies and projection systems

* **Measured.** Davenport (1998) [S1]: 148 hitters with 200+ AA/AAA at-bats in 1994–96 and 150+ MLB at-bats the next year. "The DTs were more 'right' than the MLEs by an 88-59 margin." He cites David Grabiner that MLEs "do not handle walks (and strikeouts ...) particularly well".
  * **Claimed:** "There is nothing here to make anyone believe that this year's minor league DT is any worse of a predictor for next year's major league DT than this year's major league DT."
* **Measured.** Cartwright (2009) [S2]: comparing each level directly with the majors beat chaining (A → AA → AAA → MLB). For 368 test players whose MLB line (Marcel) was .270/.327/.427, their High-A lines projected .267/.323/.419 with direct factors, against .242/.295/.368 chained through MLB players and .229/.279/.338 chained through all players. Chaining compounds error.
* **Claimed (forum estimates).** The 2003–04 MLE thread [S3]:
  * production falls 25.7–28% from AAA and 32–37.4% from AA (MGL; Rally Monkey 26.5% and 37%);
  * the components fall very differently (MGL): home runs ×0.56 (AA) and ×0.74 (AAA); strikeouts ×1.27 and ×1.23; walks ×0.92 and ×0.85;
  * Tangotiger: "The PAs of a player is dependent on how well he plays. It should not simply be used as a weight as if it was independent of his performance."
  * MGL's two-step: translate first, then regress the translated line like any other sample.
* **Claimed.** Allen & Tenenbaum (2014) [S4] list six problems: promoted players were over-performing; age is ignored; players with the same line respond differently to a level change (skill profile); no error estimates; chaining against direct; and experience at a level inflates the line. They recommend regressing toward level means, age-adjusting and bootstrapped errors.
* **Measured.** KATOH (Mitchell 2014) [S5], probit models from minor-league lines since 1990: "a one percent change in strikeout rate affects a player's projection by about 1.5 times as much as a one percent change in walk rate"; "Walk rate doesn't matter very much at the lower levels of the minors. In fact, it's not predictive at all for players in rookie ball or Low-A."
* **Measured.** Carty (2011) [S66], the sample at which a hitter's statistic is half signal (r = 0.50): strikeout rate 100 PA, unintentional walk rate 168, home runs 143, singles 959, BABIP 1,126 balls in play. **Inferred:** fast-stabilising statistics carry more information per match at any level, so they are the ones worth carrying across levels.
* **Measured (documented).** FanGraphs [S6] builds translations "around the basic statistics" because leagues reward skills differently: Japan's league devalues power, so "we should trust NPB batting averages and on-base-percentages more than ... slugging, or home runs". **Claimed:** "Translating ... is not the same thing as projecting future performance."
* **Measured (documented).** Rosenblum (2024) [S8] translates with 2021–2023 transitions "to capture the new minor league landscape" and regresses each player "toward a mean weighted by their probability of making the major leagues", a function of age relative to level. Pitcher List (2019) [S10]: "Age (relative to level), K%, and Iso are the most predictive minor league statistics."
* **Measured (documented).** Marcel [S7] ignores the minors: a rookie projects at league average. ZiPS treats the KBO as roughly Double-A [S9]. Steamer's exact formula is not public [S9].
* **Not found:** a published per-statistic reliability table for translated minor-league lines in PECOTA, Steamer or THE BAT.

### 2.2 Hockey: NHL equivalency

* **Measured (documented).** NHLe factors come from players who moved between leagues: points per game in league B ÷ in league A [S11][S12]. Current values (Chatel 2023): AHL 0.53, KHL 0.71, SHL 0.543 for points [S11].
* **Measured (documented).** The network version chains through intermediate leagues where direct links are few. Bacon's tuned version uses the top 11 paths per league and at least 8 transitioning players, chosen by 5-fold cross-validation (mean absolute error 0.33) [S12].
* **Measured (documented).** NHLe feeds prospect models as **one predictor** in logistic regressions with age, height and weight [S12]. It is not treated as NHL data.
* **Claimed.** Classic NHLe bakes a year of player development into the factor, and dominant players hit a ceiling: today's McDavid "would probably struggle to manage an NHLe of even 40 if he were banished" to junior [S12].
* **Inferred for tennis.** A prodigy winning Challengers 6-2 6-2 hits the same ceiling. His lower-level statistics understate him, which is one reason age must sit beside them.

### 2.3 Basketball: college to NBA

* **Measured (documented).** Pelton [S13] translates 14 statistics one by one, adjusts college players for strength of schedule, weights seasons, and regresses to the positional averages of NBA rookies (internationals: to replacement level). "Free throw percentage rarely changes much, but players shoot much worse percentages from the field."
* **Measured.** Kram (2018) [S14], 44 lottery-pick big men (2004–2018): final-college-season block rate correlates 0.74 with the NBA career, steal rate 0.70, defensive rebounding 0.29.

### 2.4 Football (soccer): league strength and promoted teams

* **Measured (documented).** GAP ratings [S15]: a team keeps its ratings within a league. "Teams that are promoted are assigned the average ratings of those teams that were relegated in the previous season." The class mean is used and the team's own lower-league record is dropped.
* **Measured and claimed.** Deutscher, Frick & Ötting (2018) [S16], Bundesliga 2002/03–2015/16: backing newly promoted teams early in the season returned a temporary profit, mostly away. They read it as bookmakers under-estimating how fast promoted teams adapt; the inefficiency is short-lived (abstract only).
* **Measured (documented).** Shelopugin & Sirotkin (2023) [S17]: a Glicko-2 variant across first and second tiers of European and South American leagues, with a term for teams becoming "stronger or weaker following their league transitions" (abstract only).
* **Measured (documented).** Macrì-Demartino, Egidi & Torelli (2025) [S18]: football ratings that borrow from earlier periods through commensurate priors, borrowing when past and current agree and adjusting fast when they do not (abstract only).
* **Observed.** ClubElo's ratings page lists first and second divisions in one pool [S19]; its method text could not be read.

### 2.5 Chess: converted priors and a contaminated pool

* **Measured (documented).** The US Chess rating system (Glickman & Doan, 6 Apr 2026) [S20]:
  * an unrated player's first rating is a weighted average of his other ratings (FIDE, Canadian, other US formats), "the weights ... expressed in terms of the number of 'games' worth of information the rating provides";
  * FIDE ≤ 2000 counts as 5 games, FIDE > 2000 as 10; the total is capped at 10;
  * a staleness factor cuts each weight with age, and "the weight depreciates faster with staleness for lower rated players";
  * a rating is "established" if it is based on more than 25 games; the effective game count N′ reaches 50;
  * FIDE events update a US rating only for players with an established US rating, through converted opponent ratings; youth events use their own conversion;
  * the formats (regular, quick, blitz, online) are separate systems: "Other than the use of imputing initial ratings for unrated players, there is no formal connection among these systems."
* **Measured.** Sonas's report to FIDE (11 Jan 2024) [S22]:
  * 2010–2013: players whose first rating was 1100–1199 gained 22 points on average in their next 15 games; those first rated 2000+ lost points. "The very low initial ratings were probably (on average) too low, and the very high initial ratings were probably (on average) too high."
  * Newcomers rated low were far more numerous after 2015.
* **Claimed.** Sonas: newly rated, under-rated players take points "away from established players"; the effect "propagates throughout the entire rating pool" because "all the players are part of the same connected network of opponents", reaching the 2600s; "a 'deflation engine'".
* **Measured (documented).** FIDE's fix, in force from 1 March 2024 [S21][S34]:
  * a one-time compression: ratings below 2000 rose by 0.40 × (2000 − rating) [S21];
  * a newcomer's first rating averages his rated opponents "plus two hypothetical opponents rated 1800", with "the result against these two hypothetical opponents ... considered as a draw" [S34]; Sonas chose 1800 because it "seemed to behave the best" in simulations [S22];
  * first ratings capped at 2200; 1400 the minimum for publication; K = 40 until a newcomer has 30 games [S34].
* **Inferred for tennis.** The ITF flood is FIDE's situation: thousands of players with few matches entering a pool solved jointly with the main tour. The IOS solve pulls them toward the pool's zero and the zero moves (finding #6). Chess answers with priors for newcomers, caps and an anchor.

### 2.6 Tennis: what extends EL §9

* **Measured.** Tennis Abstract (2018) [S23]: the ratio of Challenger to tour total points won (opponent-adjusted; players who played both levels, weighted by the smaller match count) was 1.100 (2012), 1.100 (2013), 1.103 (2014), 1.098 (2015), 1.086 (2016), 1.086 (2017).
  * The middle 60% of players sat between 1.07 and 1.13, so the player-to-player spread of the factor is narrow.
  * Fewer than 50 paired matches is too few to read one player.
  * Only total points won was translated. The post's "10% ace rate at Challengers ≈ 8% on tour" is an illustration, not a measurement.
  * The ratio drifted down by about 0.015 over six years (**inferred**: the gap is not constant).
* **Measured (documented).** Tennis Abstract's Elo (2019) [S24] covers "Challengers (and the women's ITF equivalent) and tour-level qualifying". New players start "in the low 1200s (it depends a bit on tournament level and gender)". Surface ratings are a 50/50 blend of the surface and overall ratings. **Claimed:** no extra weight for "important" matches has consistently improved its forecasts.
* **Measured (documented).** Ultimate Tennis Statistics [S25] multiplies K by level (above), by round (final 100% down to 75% for the first rounds) and by format (best of three 90%). Historical players start at "average Elo rating for the current rank". No validation is published on the page.
* **Measured.** Ingram's point-based hierarchical model (NESSIS 2017 slides) [S26]:
  * logit(serve point) = server skill − returner skill + surface skills + **a tournament intercept δ_t with a hierarchical prior N(0, σ_δ²)** + intercept;
  * serve and return skills follow Gaussian random walks (the slides: "Took some inspiration from Glicko");
  * trained from 2011 to predict ATP 2014: log loss 0.60 against FiveThirtyEight's Elo 0.59 and Barnett–Clarke 0.63.
  * The tournament intercept is the closest published tennis precedent for a level intercept per statistic.
* **Measured.** Gorgi, Koopman & Lit (2019) [S27]:
  * main tour only (tennis-data.co.uk, Jan 2000 – Feb 2017);
  * they removed retirements, irregular results and players with nine matches or fewer (561 players, 43,175 matches); **claimed:** keeping them gave "roughly the same" results;
  * a new player's starting strength is α × log(ATP ranking points): the ranking, which embeds lower-level results, is the prior;
  * a Grand Slam scaling γ amplifies strength differences;
  * the bookmakers beat every statistical model out of sample: average log score −0.557 against −0.577 for the best model.
* **Measured (documented).** TrueSkill Through Time's ATP example [S28] (447,000 games, 1915–2020; levels not stated) models a player on a surface as a team of two: "a generic player, who is included in all the games, and another player representing the ability of the player on a particular surface". **Inferred:** the same device gives "generic + level" skills, a direct way to partially pool across levels. TTT itself smooths the whole history in one network [S28][S29].
* **Measured (documented).** McHale & Morton (2011) [S30] weight past matches by time and surface in a Bradley–Terry likelihood: other surfaces' matches count, but less. It is the closest tennis precedent for weighting evidence by relevance (abstract only).
* **Measured.** Tennis Abstract (2019) [S31], 700 pairs of consecutive player-seasons 2009–2018: break-point performance beyond overall return skill correlates r² = 0.002 from one year to the next. **Claimed:** "indistinguishable from chance".
* **Citation only.** Kovalchik (2020) extends Elo to margin of victory [S33]; Glickman (1999) is the Glicko model with per-player rating uncertainty [S32].
* **Not found.** A published tennis study that translates individual box-score statistics across levels (beyond total points won), or that tests level-discounted histories against the market.

### 2.7 Which statistics translate

| Kind of statistic | Other sports | Tennis analog (inferred) | Suggested treatment |
|---|---|---|---|
| Player-controlled process | Strikeout rate (half signal at 100 PA [S66]; weighs most in KATOH [S5]); free-throw % [S13]; block and steal rates [S14] | First serves in, double faults, serve speed. 01 observes the serve-style forms barely move with the level | Small offset, transfer weight near 1 |
| Outcome that depends on the opponent | BABIP half signal only after ~1,100 balls in play [S66]; field-goal % falls [S13]; defensive rebounding 0.29 [S14]; power devalued in some leagues [S6] | Return points won, breaks, second-serve points won, total points won (the same men at Challengers: breaks +8.3 points, holds +3.6, EL §3) | Offset per statistic and a clear discount |
| Partly opponent-dependent "free points" | Home runs fall most (×0.56–0.74) [S3] | Aces depend on the returner, so likely fall at higher levels; size unknown | Measure (role 03) |
| Clutch residual | Tennis break points beyond expectation: r² = 0.002 [S31] | Break points saved or converted beyond what points won predict | Do not carry across levels; shrink to the points-won expectation |
| Volume and opportunity | Hockey points depend on role and ice time [S12] | Match counts, sets played (workload) | Count as workload, not skill |

## 3. Statistics: the machinery behind "informative, not equivalent"

### 3.1 Credibility and empirical Bayes

* **Standard result.** Bühlmann credibility [S35]: estimate = Z·(own mean) + (1 − Z)·(complement), with Z = n/(n + k) and k = (variance within a player) ÷ (variance of true means between players). Bühlmann–Straub weights each observation by its exposure (matches, points).
* **Measured (documented, secondary summary).** Actuarial practice [S36] asks six things of a "complement of credibility": accurate, unbiased, independent of the base statistic, available, easy to compute, and logically related. Harwayne's method first adjusts the related data to the target's mix, then uses it: **translate before you blend**.
* **Measured.** Efron & Morris (1975) [S37], 18 batters after 45 at-bats: the shrunk averages predicted the rest of the season with total squared error 5.01 against 17.56 for the raw averages, 3.5 times smaller, and were closer for 15 of the 18.
  * Their "limited translation" estimators cap how far shrinkage moves any one player. It cut the worst single-player risk from 4.60 to 1.52 while keeping 80% of the savings.
  * **Inferred:** this is the guard for a genuine prodigy, the "Clemente" of a Challenger field.

### 3.2 Hierarchical models and partial pooling

* **Measured.** Gelman (2006) [S38], radon in 85 Minnesota counties, cross-validated error: 0.84 complete pooling, 0.86 no pooling, 0.79 multilevel; by county, 0.50 complete pooling against 0.40 multilevel. No pooling overfits small groups; complete pooling ignores real differences.
* **Inferred, mapped to this project.**
  * Main-tour-only histories = no pooling: they would discard 44–50% of a 250 player's year (EL).
  * Today's all-level histories = complete pooling: a Challenger match counts like a main-tour one.
  * Translated and discounted histories = partial pooling.
  * EL's experiment A is the row-level version of the same lesson: own-level-only training was worse at the 250s.
* **Measured (documented).** Group offsets with a shared prior are the standard device: Ingram's tournament intercepts [S26].

### 3.3 Two parts: an offset and extra uncertainty

* **Measured (documented, abstract only).** Kennedy & O'Hagan (2000) [S39] combine a cheap approximate code with an expensive accurate one through an autoregressive model: top(x) = ρ·cheap(x) + δ(x). The cheap source is informative through ρ; δ is learned where top-level data exist.
* **Measured (documented, abstract only).** Turner et al. (2009) [S43] separate a source's **internal bias** (lack of rigour) from its **external bias** (lack of relevance to the target), each with a mean and a variance.
* **Measured (documented, abstract only).** Borrowing from historical data in trials:
  * the power prior raises the old data's likelihood to a power a₀ between 0 and 1 [S40];
  * commensurate priors let the agreement between old and new data set how much is borrowed [S41];
  * robust meta-analytic-predictive priors add a vague component so the analysis reacts fast when old and new conflict [S42].
* **Inferred.** Lower-level evidence is a biased (offset δ, per statistic) and less relevant (extra variance, so a discount) measure of main-tour skill. External bias: a different population. Possible internal bias: weaker data capture at ITF level. The discount should be learned from how well the two levels agree, statistic by statistic, and a robust component should stop a fast-improving player from being anchored to his past.

### 3.4 Measurement error

* **Standard method** [S44]: regression calibration replaces a noisy measurement by its expected true value given the measurement. Uncorrected noise attenuates a predictor's effect. **Inferred:** a translated, shrunk lower-level profile is exactly the regression-calibrated value.

### 3.5 Transfer learning and domain adaptation

* **Measured (documented, citation only).** Under covariate shift, weighting the log-likelihood by p_target(x)/p_source(x) corrects the fit [S45]. **Inferred:** the method needs sample weights, and the project's training rows are all main tour anyway; the contamination sits in the inputs, not the rows.
* **Measured (documented, metadata page).** Feature augmentation (Daumé III 2007) [S46] gives the learner a shared copy and a domain-specific copy of each feature. **Inferred:** in tennis, a main-tour-only and an all-level version of a profile. It doubles the columns, which the UFC experience and the adoption framework argue against (06; R5).
* **Measured (abstract only).** Drift-Resilient TabPFN [S50] learns temporal shifts from a prior of drifting causal models (accuracy 0.688 → 0.744 across 18 datasets, the authors' figures). **Inferred:** relevant to the ITF regime's drift, but not a drop-in replacement for the decided model.

### 3.6 Putting a prior into TabPFN

**Measured.** The installed TabPFN (package 9.1.0) has `fit(self, X, y)` with no sample weights (`tabpfn/classifier.py:949`); the package ships a fine-tuning module (`tabpfn/finetuning/`) [S51].

| Route | How | Evidence | Status here | Pitfalls |
|---|---|---|---|---|
| **In place: better-built inputs** | Translate and shrink inside the feature builders; the column count stays 58 | Credibility, partial pooling (§3.1–3.2); stage 2's speed panel already does it (01) | Recommended (R1–R4) | Fit the translations walk-forward; re-tune constants tuned on all-level pools (06) |
| Prior as a feature | A column holding the prior (e.g. a translated lower-level profile) | NHLe and KATOH-style models feed translated statistics as predictors [S12][S5] | EL's C1 (history share as a 59th input): the model took up about a third of the market's bias; tie | More columns, weak signals; added exposure columns died in the UFC work (06) |
| Stacking | Another model's output as a column (the close already is one) | Standard | The close, `odds_logit` | A second stack on top of the close likely adds little at the close (inferred) |
| **Offset on the log-odds (stage 2)** | logit q = s·η + b̃·x, with b̃ shrunk and refitted each season | The decided speed adjustment; EL's C2 absorbed the climber effect fully, positive coefficient in every season, overall a tie | Recommended only for the climber effect (R6) | Small effect; regimes change (06) |
| Context selection | The nearest rows as TabPFN's context (LoCalPFN) [S48] | Helps on large datasets (authors) | Not tried; own-level-only training hurt (EL) | Fewer rows |
| Weights by duplication | Copy rows to up-weight | — | Not tried (EL) | The rows are all main tour; does not address the inputs |
| Fine-tuning | Adapt the network or a learned context [S49] | Authors report gains | Package supports it | Large change to a decided model |

**Inferred.** TabPFN approximates Bayesian prediction over its pre-training prior [S47]. With effects at the close of about 0.01 mLL or less (adoption framework), it is unlikely to discover "trust this profile less when the player's main-tour record is thin" from the 50,000–60,000 rows a season's fit trains on (EL §1). Encoding that known structure in the inputs relieves it.

## 4. Betting practice

### 4.1 Where markets are weak

* **Measured.** Forrest & McHale (2007) [S52]: men's tennis shows positive longshot bias across the range of odds (abstract only).
* **Measured.** Abinzano, Muga & Santamaria (2016) [S53], betting exchange: the bias is stronger in matches between lower-ranked players, in later rounds and at high-profile tournaments (abstract via a search index; the repository was unreachable).
* **Measured, then corrected.** Ramirez, Reade & Singleton (2023) [S54]: pre-match Wikipedia "buzz" predicted bookmaker mispricing and a profitable strategy. Clegg & Cartlidge (2025) [S55]: a single outlier bet drove most of the profit; corrected, only one marginal strategy remained, and none after 2020.
* **Measured.** Deutscher et al. (2018) [S16]: promoted Bundesliga teams were briefly under-priced (§2.4).
* **Measured.** On the main tour the bookmakers beat every statistical model (Gorgi et al. [S27]); in golf, Pinnacle's close matched realised returns about 1:1 and other books' closes added little (Data Golf 2020) [S59].
* **In project (EL §8).** The close under-rates players arriving from lower levels: about 1.4–1.9 points of win probability per standard deviation of history-share difference, about 0.1 mLL a match; as an input or a stage-2 term it ties.
* **In the owner's UFC work (06).** The pre-UFC prior carried nothing beyond the debut line; the market had priced the record.
* **Not found** (as in EL §9): any published measurement of Challenger or ITF price efficiency.
* **Inferred.** Where the market is weakest (lower-ranked players, newcomers), models are weakest too (Kovalchik 2016, EL §9). Edges there are larger and noisier, and they fade as information arrives.

### 4.2 Closing-line value as the yardstick, and its limits

* **Measured and claimed.** Whelan (12 Aug 2026) [S58]: across 3,670 NBA games (2022–2025), only the top tenth of moneyline bets turned closing-line value into meaningful profit (+11.4%); three of five deciles with positive closing-line value still lost. In college basketball, early bets on big underdogs earned closing-line value but not enough to beat the margin. **Claimed:** closing-line value must exceed the margin to matter.
* **Measured and claimed.** Wunderlich & Memmert (2020) [S56]: positive betting returns can occur without better accuracy; judge accuracy and profitability separately.
* **Measured and claimed.** Hubáček & Šír (2023) [S57]: a model decorrelated from the market can profit while predicting worse. **Inferred:** lower-level information that the market under-uses may matter more for bets than for log loss against the close.

### 4.3 Integrity and robust results

* **Measured (documented).** Gorgi et al. dropped retirements and irregular results [S27]. US Chess caps rating changes from head-to-head match play (50 points a match, 100 per 180 days, 200 per three years) and does not rate games in which a player makes no move [S20]. FIDE caps first ratings at 2200 [S34].
* **Measured (documented), abstract only.** Forrest & McHale (2019) [S63]: integrity screens compare in-play model odds with market odds and flag divergence; the results have been accepted as evidence at the Court of Arbitration for Sport.
* **Inferred.** Lower-level results carry three extra noise sources: retirements (3.59% of Futures matches against 1.61% at tour level, EL §9), integrity (alerts concentrate at Challenger 50/75 and ITF, EL §9), and weaker data capture. A rating should not move far on one such match.

### 4.4 Staking under uncertainty

* **Measured and claimed.** Baker & McHale (2013) [S60], with tennis betting data: Kelly ignores the uncertainty of the estimated probability, and "the size of the bet should be shrunk in the presence of this parameter uncertainty"; shrunk Kelly beat raw Kelly.
* **Claimed.** Fractional Kelly gives up some growth for much less risk (MacLean, Thorp & Ziemba 2010, citation only) [S61]; across horse racing, basketball and football, "an adaptive variant of the popular 'fractional Kelly' method is a very suitable choice" (Uhrín et al. 2021) [S62].
* **Inferred.** A low-exposure player's forecast is less certain, so the stake should be smaller even at the same edge.

### 4.5 How sharp bettors treat newcomers

* **Not found:** academic evidence for tennis qualifiers or Challenger climbers beyond EL §8. Practitioner claims that qualifiers are mispriced were not verified.
* **Inferred.** The evidence (promoted teams, climbers, the UFC record) points the same way: the market leans on reputation and ranking, the error is small, and it fades as information arrives.

## 5. What it implies for this project: ranked recommendations

All are **suggestions**. The order weighs evidence strength, how much contamination each removes before the ITF box scores land, and cost. Gains at the close are expected to be small; the project's screens put true effects of a new input at the close at about 0.01 mLL or less (adoption framework). The first aim is no harm.

| Rank | What | Evidence strength | Expected gain at the close | Main pitfalls |
|---|---|---|---|---|
| R1 | A level ("league strength") term in the 17 one-step forms and `points_52w` | **Strong** in principle (every translation field); in-project shift measured (01) | Small; mainly prevents harm when ITF box scores arrive | Selection bias and drift in the offsets; ITF offsets need ITF box scores of 2018–2024 |
| R2 | Per-statistic level offsets and a transfer weight τ < 1 inside the joint solves; anchor the zero on main-tour players | **Moderate–strong** (credibility, partial pooling, chess, TTT); untested in tennis | Small; protects the IOS profile and products | More parameters; re-tune the solves' constants; τ may change by era |
| R3 | Proper priors for newcomers entering the pools | **Strong** in chess (measured bias, reform); moderate in tennis | Small; mostly no-harm | Leaks if priors use later data |
| R4 | Treat statistics by type (process near 1:1; outcomes discounted; clutch residuals dropped) | **Moderate** (cross-sport; consistent with 01) | Small | Must be measured per statistic (role 03) |
| R5 | Change inputs in place; add no exposure columns | **Moderate** (UFC lessons; adoption framework; C1) | — (a design rule) | — |
| R6 | The climber effect only as a shrunk stage-2 term, adopted only on fresh seasons | **Weak–moderate** (C2 ties; promoted-team effects fade) | ≈0.1 mLL at best | Regime change; it leaned worse at the 1000s |
| R7 | Stake less when the forecast is less certain | **Strong** (theory and tennis data) | None in log loss; protects the bankroll | Needs per-stratum calibration |
| R8 | Clean lower-level results (walkovers, retirements, bounded updates, integrity-risk events) | **Moderate** | Small | Thins lower-level evidence further |

### R1. Give the one-step forms and `points_52w` a level term

* **Why.** 01 found that the "opponent-adjusted" two-week form keeps 78% of the raw level shift (77% for women), because the opponent's norm is what his own opponents did against him "at whatever level he usually plays". Opponent adjustment *inside* a pool cannot see that the whole pool is weaker. That is the league-strength problem every other field solves with links across leagues: players who move (MLEs, NHLe), matches across leagues (club ratings), schedule strength (Pelton).
* **How (options, cheapest first).**
  1. Take the opponent's norm from the joint-solve ratings, which are level-consistent at Challenger and qualifying level (01).
  2. Or subtract a per-statistic level offset δ_s,L, fitted walk-forward on players who played both levels in the same window.
  3. Then discount lower-level matches in the two-week average by a transfer weight (R2).
  4. For `points_52w`, use the opponent-adjusted version Stage 4 already builds (EL §3), or the same offset.
* **Why now.** 01 ranks ITF box scores (P7, P8, P1) as the highest forward risk: they would inflate the 17 forms and `points_52w` for ITF-active players, mostly women and qualifiers.
* **Pitfalls.** The offset is biased by who moves between levels and why (§2.1). Estimate it on dual-level players in the same window, not across promotions. Refit it each season (its tennis value drifted [S23]). The ITF offset needs ITF box scores of 2018–2024; do not estimate it on 2025–2026, which would read holdout outcomes. A norm taken from joint-solve ratings combines players' results, so it must use the leak-proof clock and pass the leak probe.

### R2. Partial pooling inside the joint solves

* **What.** In the serve/return ratings and the IOS profile (and, at low priority, Elo):
  * a level intercept per statistic, in the way Ingram gives tournaments intercepts [S26];
  * a transfer weight τ_s,L < 1 on lower-level observations (a weighted ridge), so one lower-level point counts as τ main-tour points;
  * the reference level taken from main-tour players, as the product-centring study did (a tie in log loss, recommended there on mechanism).
* **Equivalent form.** Role 03's exchange-rate estimator, θ̂ = (k·μ + n_M·x̄_M + (n_L/λ_L)·(x̄_L − δ_L)) / (k + n_M + n_L/λ_L), is this recipe written out: δ the translation, λ the discount (τ = 1/λ), k the Bühlmann constant, μ the complement.
* **Why.** Partial pooling beats both extremes when group sizes vary (§3.2). Top players have little lower-level evidence, so they are untouched automatically. Players who mostly play Challengers are carried by their translated record, and their own main-tour matches take over as they accumulate. This is 06's "copy the method; adapt the mechanism" proposal, and the literature backs it.
* **Optional, richer.** "Generic + level" skills in the TrueSkill Through Time pass, using the surface device of [S28].
* **Expectations and pitfalls.**
  * Tennis Abstract found no consistent gain from extra weight on important matches in a results-only Elo [S24]; EL found Elo about right across levels. **Elo is the lowest priority**; the owner's thesis treats it as a priced-in control.
  * The offset and weight must be fitted per statistic and walk-forward. The UFC transfer ratio moved from about 0.02 to 0.71 between eras (06).
  * Constants tuned on all-level histories (the offset Elo's K, the surface-IOS constants) must be re-tuned for a level-aware arm, or it is judged against an optimum it never had (06).

### R3. Proper priors for newcomers

* **What.**
  * Shrink a newcomer toward the mean of comparable newcomers (by level, tour, age), not toward the pool's overall zero, so a flood of ITF players does not move main-tour players' ratings.
  * Add a small number of pseudo-matches against a typical opponent of his level (FIDE's two hypothetical draws), with the number chosen by walk-forward simulation, as FIDE chose 1800.
  * Cap a first estimate and limit how far shrinkage can move an exceptional player (Efron–Morris's limited translation).
* **Why.** FIDE measured the bias of first ratings and saw it spread through the connected pool [S22]. The project saw the same channel in finding #6.

### R4. Treat statistics by type

* Serve-style statistics (first serves in, double faults, serve speed): small offset, transfer weight near 1. 01 sees these forms barely move with the level.
* Return points, breaks, second-serve points, total points won: per-statistic offset and a clear discount.
* Break points saved or converted beyond what points won predict: do not carry across levels; shrink to the points-won expectation [S31].
* Aces: measure (role 03); they depend on the returner.
* This follows the owner's thesis: per-statistic profiles first.

### R5. In place, not new columns

* Keep the 58 columns and change how they are built. TabPFN cannot weight rows [S51], and it took up only a third of the climber effect as a new column (EL C1).
* The UFC work found added experience and uncertainty columns died, and in-place changes won (06).
* If a prior column is tried at all, one blended column per statistic family, never a main / lower / exposure triplet.

### R6. The climber effect: a shrunk stage-2 term, tested on fresh seasons only

* EL's C2 absorbed the market's under-rating of climbers fully, with a positive coefficient in every season, but tied overall: better at the 500s, leaning worse at the 1000s.
* Promoted-team effects fade [S16]; the UFC transfer ratio changed by era (06).
* Adopt only if it holds on seasons not used to find it, and refit and shrink it each season, as the speed term is.

### R7. Stake by uncertainty

* Shrink the Kelly stake by the forecast's uncertainty [S60], and use a fractional, adaptive Kelly [S62].
* Measure calibration by exposure stratum (role 02 has the strata) and size bets on low-exposure players down where calibration is worse.

### R8. Clean lower-level results

* Drop walkovers.
* For a retirement, use the points played but not the result, or a reduced weight.
* Bound any single match's move in a rating. Chess bounds similar risks: US Chess caps rating changes from head-to-head match play [S20] and FIDE caps first ratings [S34].
* Give a lower transfer weight to event types where integrity alerts cluster (Challenger 50/75, ITF; EL §9).

### What not to do

| Don't | Why |
|---|---|
| Add lower-level matches as training rows | No help, leans harmful with the price in (EL §6) |
| Train each main-tour level on its own rows only | Worse in direction at every level, significantly at the 250s (EL §4) |
| Fit a discount once on old seasons and freeze it | Regimes change: the UFC transfer ratio (06); MiLB's 2021 reorganisation [S8]; Tennis Abstract's ratio drifting [S23] |
| Chain ITF → Challenger → tour without carrying the error | Chaining compounds error [S2][S12] |
| Compare raw lower-level rates with main-tour rates | Every translation method adjusts first; the same players win 61% against 37% (EL §3) |
| Add "exposure" columns as stand-alone inputs | Died in the UFC work (06); C1 tied (EL) |
| Treat ITF like Challengers | ITF is results only before 2025; its offsets are unmeasured |

## 6. The evaluation protocol best practice would demand

1. **Pre-register each arm** (plan, primary comparison, strata, reading rules) and hash it, as the project already does. Pre-registration separates predictions from postdictions [S64].
2. **Walk-forward everything.** Translations, offsets, transfer weights and newcomer priors for season Y are fitted on seasons before Y. Arms that change a solve re-tune its constants on 2013–2018. Score 2019–2024 (compare.py's 2020–2024). Keep 2025–2026 sealed, and do not estimate ITF offsets on it. Leakage of this kind turned "superior" ML models into ordinary ones in other fields [S65].
3. **Both stages against the frozen reference** (`compare.py`), with the input check first: no input flagged "uneven". Run the leak probe on any change that combines different players' results.
4. **Primary:** log loss with the close as an input, both tours. **Secondary:** against Pinnacle; by tour; by level.
5. **Declared strata.**
   * The less-exposed player's main-tour matches in the previous 365 days (for example under 10, 10–29, 30 or more; role 02 uses "fewer than 10").
   * The lower-level dose; qualifiers against direct entrants.
6. **A falsification check.** Matches where both players have long main-tour records should barely move (only through their opponents' ratings). A change that "helps" top-against-top matches is suspect.
7. **Touched against untouched rows, and placebo twins.** Shuffle lower-level histories across players within tour × season × exposure band, or permute the level labels. The candidate must beat the placebo spread, not zero (06's UFC method).
8. **Shrink and penalise.** Read the gain through the adoption framework: shrink toward 0 with B = τ²/(τ² + s²), and subtract the winner's-luck term when the best of several variants is picked.
9. **Betting yardsticks, separately.** The gain over the recalibrated close and Pinnacle. Closing-line value against the 24-hour Polymarket price only inside the holdout's own protocol. Realised returns only as a secondary readout [S56], with event-block bootstrap and a check that no single bet carries the result [S55].
10. **Report the translation itself.** Per statistic and level: δ and τ with intervals, their drift by season, who is touched, and what happened to top players' inputs (they should be about unchanged).
11. **Re-run when data lands** (`refresh.py`, role 08) and track δ and τ over time against role 04's re-review triggers.

## 7. What this report does not show

* **No new measurement.** Everything about tennis translation factors here is from the literature or the project's earlier studies. Role 03 measures them on the project's data.
* **Thin reading of some sources.** Several statistics and betting papers were read as abstracts only (marked in the list). The baseball component factors come from a 2003–04 forum thread [S3], not a peer-reviewed study.
* **Cross-sport analogies are inferences.** Baseball, basketball, hockey and chess have different structures: fewer and slower movements between tiers, and no market-price input in the model.
* **No source tests these ideas against tennis prices.** The project's own C1/C2 ties are the closest evidence, and they say the market-facing effect is small.
* **Pages not readable:** ClubElo's method, FiveThirtyEight's (now offline) soccer methodology, Kovalchik 2016's full text, Baker & McHale's shrinkage formula.

## Sources (all accessed 9 October 2026)

| # | Source | What it supports here | Read | URL |
|---|---|---|---|---|
| S1 | Davenport, C. (30 Jan 1998). DTs vs. MLEs – A Validation Study. Baseball Prospectus | Translated minor-league lines as predictive as an MLB season; DTs beat MLEs 88–59 | Full text (web reader; quotes re-queried) | https://baseballprospectus.com/?p=49 |
| S2 | Cartwright, B. (17 May 2009). Prospectus Idol entry (MLE methods). Baseball Prospectus | Direct comparison beats chaining | Full text (web reader) | https://baseballprospectus.com/?p=8887 |
| S3 | Tango on Baseball archives: MLE thread (MGL, Tangotiger, Rally Monkey; Dec 2003 – Jan 2004) | Component factors; production drops; PA weighting depends on performance | Full text (web reader) | https://tangotiger.net/archives/stud0262.shtml |
| S4 | Allen, D. & Tenenbaum, K. (26 Nov 2014). A Theoretical Blueprint for Improving MLEs. The Hardball Times | Six problems with MLEs | Full text (web reader) | https://tht.fangraphs.com/a-theoretical-blueprint-for-improving-mles/ |
| S5 | Mitchell, C. (30 Dec 2014). KATOH. The Hardball Times | Which minor-league statistics predict | Full text (web reader) | https://tht.fangraphs.com/katoh-forecasting-a-hitters-major-league-performance-with-minor-league-stats/ |
| S6 | FanGraphs Library. League Equivalencies | Translations per basic statistic; NPB power devalued | Full text (web reader) | https://library.fangraphs.com/principles/league-equivalencies/ |
| S7 | Tango, T. Marcel the Monkey Forecasting System | 5/4/3 weights; 1,200 PA regression; rookies at league average | Full text (web reader) | https://www.tangotiger.net/archives/stud0346.shtml |
| S8 | Rosenblum, J. (8 Apr 2024). The Top 30 Projected Hitting Prospects Entering 2024. FanGraphs | 2021–23 translations; regression weighted by the chance of reaching MLB | Full text (web reader) | https://fantasy.fangraphs.com/the-top-30-projected-hitting-prospects-entering-2024 |
| S9 | Cockcroft, T. H. (20 Feb 2015). How fantasy baseball projections are calculated. ESPN | ZiPS: KBO ≈ AA; Oliver direct MLEs; Steamer formula not public | Full text (web reader) | https://africa.espn.com/flb/story/_/page/mlbdk2k15_projectionstalk/how-fantasy-baseball-projections-calculated-how-best-use-them |
| S10 | Isherwood, A. (27 Jul 2019). Projecting Minor League Hitters Using Statistics. Pitcher List | Age relative to level, K%, ISO most predictive | Full text (web reader) | https://pitcherlist.com/projecting-minor-league-hitters-using-statistics/ |
| S11 | Chatel, T. (8 Jun 2023, updated 17 Jul 2023). Rethinking NHLe | NHLe method and factors | Full text (web reader) | https://thibaudchatel.substack.com/p/rethinking-nhle |
| S12 | Bacon, P. (2021). NHL Equivalency and prospect projection models. HockeyStats | Network NHLe tuning; NHLe as a predictor; ceiling effect | Full text (web reader) | https://hockeystats.com/methodology/nhle |
| S13 | Pelton, K. Explaining Kevin Pelton's NBA draft projection system. ESPN (page dated 19 Jun 2025) | Per-statistic translation; schedule adjustment; regression to rookie averages | Full text (web reader) | https://africa.espn.com/nba/story/_/id/16235135/explaining-kevin-pelton-nba-draft-projection-system |
| S14 | Kram, Z. (13 Jun 2018). The Ringer | Block 0.74, steal 0.70, defensive rebounding 0.29 | Full text (web reader) | https://www.theringer.com/2018/06/13/nba/deandre-ayton-defense-nba-draft |
| S15 | Wheatcroft, E. (2020). Forecasting football matches by predicting match statistics. arXiv:2001.09097 | Promoted teams take relegated teams' average rating | Full text (pypdf) | https://arxiv.org/abs/2001.09097 |
| S16 | Deutscher, C., Frick, B. & Ötting, M. (2018). Betting market inefficiencies are short-lived in German professional football. Applied Economics 50(30), 3240–3246 | Promoted teams briefly under-priced | Abstract only | https://ideas.repec.org/a/taf/applec/v50y2018i30p3240-3246.html |
| S17 | Shelopugin, A. & Sirotkin, A. (2023). Ratings of European and South American football leagues based on Glicko-2 with modifications. arXiv:2310.11459 | Cross-tier ratings with a transition term | Abstract only | https://arxiv.org/abs/2310.11459 |
| S18 | Macrì-Demartino, R., Egidi, L. & Torelli, N. (2025). Bayesian weighted discrete-time dynamic models for association football prediction. arXiv:2508.05891 | Commensurate priors in football ratings | Abstract only | https://arxiv.org/abs/2508.05891 |
| S19 | ClubElo ratings page | One pool across first and second divisions | Page read; method text not found | http://clubelo.com/System |
| S20 | Glickman, M. E. & Doan, T. (6 Apr 2026). The US Chess Rating system | Converted priors worth 5–10 games; staleness; caps; FIDE events | Full text (pypdf) | https://www.glicko.net/ratings/rating.system.pdf |
| S21 | FIDE (2 Jan 2024). New FIDE Rating and Title Regulations come into effect | Compression 0.40 × (2000 − rating) | Full text (web reader) | https://www.fide.com/new-fide-rating-and-title-regulations-come-into-effect/ |
| S22 | Sonas, J. (11 Jan 2024). Final report to FIDE | Biased first ratings; deflation through the network; two hypothetical draws vs 1800; caps | Full text (pypdf), pp. 10–14 read closely | https://qc.fide.com/wp-content/uploads/2024/03/Sonas-Final-Report-as-of-11-JAN-2024.pdf |
| S23 | Sackmann, J. (25 Apr 2018). Translating ATP statistics across main tour and Challenger levels. Tennis Abstract | TPW factors by year; spread among players | Full text (web reader) | https://www.tennisabstract.com/blog/2018/04/25/translating-atp-statistics-across-main-tour-and-challenger-levels/ |
| S24 | Sackmann, J. (3 Dec 2019). An Introduction to Tennis Elo. Tennis Abstract | Levels included; level-dependent start; 50/50 surface blend; important-match weights no gain | Full text (web reader) | https://www.tennisabstract.com/blog/2019/12/03/an-introduction-to-tennis-elo/ |
| S25 | Ultimate Tennis Statistics. Elo ratings | K multipliers by level, round and format | Full text (web reader) | https://ultimatetennisstatistics.com/eloRatings |
| S26 | Ingram, M. (2017). A point-based Bayesian hierarchical model to predict the outcome of tennis matches. NESSIS slides. Published as J. Quant. Anal. Sports (2019), doi:10.1515/jqas-2018-0008 (not read) | Tournament intercepts with a hierarchical prior; log losses | Slides full text (pypdf) | https://www.nessis.org/nessis17/Ingram.pdf |
| S27 | Gorgi, P., Koopman, S. J. & Lit, R. (2019). The analysis and forecasting of tennis matches by using a high dimensional dynamic model. JRSS A 182(4), 1393–1409 | Main-tour data; cleaning; ranking-points prior; bookmakers best | Full text (pypdf) | https://pure.au.dk/ws/files/191853062/rssa.12464.pdf |
| S28 | Landfried, G. & Mocskos, E. (2025). TrueSkill Through Time. J. Statistical Software 112(6); and the package's examples page | Generic + surface skills; ATP example | JSS abstract; examples page full | https://www.jstatsoft.org/article/view/v112i06 ; https://trueskillthroughtime.readthedocs.io/en/latest/man/examples.html |
| S29 | Dangauthier, P., Herbrich, R., Minka, T. & Graepel, T. (2007). TrueSkill Through Time: Revisiting the History of Chess. NeurIPS 20 | Smoothing skills through time | Abstract only | https://proceedings.neurips.cc/paper/2007/hash/9f53d83ec0691550f7d2507d57f4f5a2-Abstract.html |
| S30 | McHale, I. & Morton, A. (2011). A Bradley-Terry type model for forecasting tennis match results. Int. J. Forecasting 27(2), 619–630 | Weighted likelihood by time and surface | Abstract only | https://www.iaorifors.com/paper/71431 |
| S31 | Sackmann, J. (4 Jan 2019). Measuring the Impact of Break Points. Tennis Abstract | Break-point residual r² = 0.002 | Full text (web reader) | https://www.tennisabstract.com/blog/2019/01/04/measuring-the-impact-of-break-points/ |
| S32 | Glickman, M. E. (1999). Parameter estimation in large dynamic paired comparison experiments. JRSS C 48(3), 377–394 | Glicko: per-player rating uncertainty | Citation only | https://ideas.repec.org/r/bla/jorssc/v48y1999i3p377-394.html |
| S33 | Kovalchik, S. (2020). Extension of the Elo rating system to margin of victory. Int. J. Forecasting 36(4), 1329–1341 | Elo variants in tennis | Citation only | https://doi.org/10.1016/j.ijforecast.2020.01.006 |
| S34 | FIDE Rating Regulations (approved by the FIDE Council 15 Dec 2023, effective 1 Mar 2024), FIDE Handbook B.02 | Two hypothetical drawn games vs 1800 in first ratings; 2200 cap; 1400 minimum; K = 40 for newcomers | Full text (web reader) | https://handbook.fide.com/chapter/B022024 |
| S35 | Bühlmann, H. (1967). Experience rating and credibility. ASTIN Bulletin 4(3), 199–207 | Credibility | Abstract only | https://www.cambridge.org/core/journals/astin-bulletin-journal-of-the-iaa/article/experience-rating-and-credibility/B9A879CE4A73397C653963B474A7F954 |
| S36 | Werner, G. & Modlin, C. Basic Ratemaking (CAS), ch. 12, via a study summary | Complement of credibility; Harwayne's method | Secondary summary | https://battleacts.pro.wiki/wiki/Werner12.Credibility |
| S37 | Efron, B. & Morris, C. (1975). Data analysis using Stein's estimator and its generalizations. JASA 70(350), 311–319 | 17.56 vs 5.01; limited translation | Full text (pypdf) | https://faculty.ucmerced.edu/jvevea/classes/290_21/readings/week%204/Efron%20and%20Morris.pdf |
| S38 | Gelman, A. (2006). Multilevel (hierarchical) modeling: what it can and cannot do. Technometrics 48(3), 432–435 | Partial pooling cross-validation | Full text (pypdf) | https://sites.stat.columbia.edu/gelman/research/published/multi2.pdf |
| S39 | Kennedy, M. C. & O'Hagan, A. (2000). Predicting the output from a complex computer code when fast approximations are available. Biometrika 87(1), 1–13 | Autoregressive multi-fidelity model | Abstract only | https://tonyohagan.co.uk/academic/abs/techrep9.html |
| S40 | Chen, M.-H. & Ibrahim, J. G. (2000). Power prior distributions for regression models. Statistical Science 15(1) | Power prior | Abstract only | https://projecteuclid.org/journals/statistical-science/volume-15/issue-1/Power-prior-distributions-for-regression-models/10.1214/ss/1009212673.full |
| S41 | Hobbs, B. P., Carlin, B. P., Mandrekar, S. J. & Sargent, D. J. (2011). Hierarchical commensurate and power prior models. Biometrics 67(3), 1047–1056 | Commensurate priors | Abstract only | https://ideas.repec.org/a/bla/biomet/v67y2011i3p1047-1056.html |
| S42 | Schmidli, H. et al. (2014). Robust meta-analytic-predictive priors in clinical trials with historical control information. Biometrics 70(4), 1023–1032 | Robust MAP priors | Abstract only | https://ideas.repec.org/a/bla/biomet/v70y2014i4p1023-1032.html |
| S43 | Turner, R. M., Spiegelhalter, D. J., Smith, G. C. S. & Thompson, S. G. (2009). Bias modelling in evidence synthesis. JRSS A 172(1), 21–47 | Internal against external bias | Abstract only | https://pmc.ncbi.nlm.nih.gov/articles/PMC2667303/ |
| S44 | Carroll, R. J., Ruppert, D., Stefanski, L. A. & Crainiceanu, C. M. (2006). Measurement Error in Nonlinear Models, 2nd ed. | Regression calibration | Publisher page only | https://www.routledge.com/Measurement-Error-in-Nonlinear-Models-A-Modern-Perspective-Second-Edition/Carroll-Ruppert-Stefanski-Crainiceanu/p/book/9781584886334 |
| S45 | Shimodaira, H. (2000). Improving predictive inference under covariate shift by weighting the log-likelihood function. J. Statistical Planning and Inference 90, 227–244 | Importance weighting | Citation only | https://doi.org/10.1016/S0378-3758(00)00115-4 |
| S46 | Daumé III, H. (2007). Frustratingly Easy Domain Adaptation. ACL | Feature augmentation | Metadata page | https://aclanthology.org/P07-1033/ |
| S47 | Hollmann, N. et al. (2025). Accurate predictions on small data with a tabular foundation model. Nature 637 | TabPFN | Abstract only | https://pubmed.ncbi.nlm.nih.gov/39780007/ |
| S48 | Thomas, V. et al. (2024). Retrieval & Fine-Tuning for In-Context Tabular Models (LoCalPFN). NeurIPS 37 | Context selection | Abstract only | https://arxiv.org/abs/2406.05207 |
| S49 | Feuer, B. et al. (2024). TuneTables. NeurIPS 37 | Learned context / fine-tuning | Abstract only | https://arxiv.org/abs/2402.11137 |
| S50 | Helli, K. et al. (2024). Drift-Resilient TabPFN. NeurIPS 37 | Temporal shift | Abstract only | https://arxiv.org/abs/2411.10634 |
| S51 | The installed TabPFN package, version 9.1.0, environment `tennis-tabpfn-local` (`tabpfn/classifier.py:949`, `tabpfn/finetuning/`) | No sample weights; fine-tuning module present | Read locally | `C:/Users/zerom/miniforge3/envs/tennis-tabpfn-local/Lib/site-packages/tabpfn/` |
| S52 | Forrest, D. & McHale, I. (2007). Anyone for tennis (betting)? European J. Finance 13(8), 751–768 | Longshot bias in men's tennis | Abstract only | https://ideas.repec.org/a/taf/eurjfi/v13y2007i8p751-768.html |
| S53 | Abinzano, I., Muga, L. & Santamaria, R. (2016). Game, set and match: the favourite-long shot bias in tennis betting exchanges. Applied Economics Letters 23(8), 605–608 | Stronger bias among lower-ranked players | Abstract via a search index; repository unreachable | https://hdl.handle.net/2454/18748 |
| S54 | Ramirez, P., Reade, J. J. & Singleton, C. (2023). Betting on a buzz. Int. J. Forecasting 39(3) | Attention predicts mispricing | Abstract only | https://stir.ac.uk/research/hub/publication/1969448 |
| S55 | Clegg, L. & Cartlidge, J. (2025). Not feeling the buzz: correction study. Int. J. Forecasting 41(2), 798–802 | One outlier bet carried the profit | Abstract only | https://arxiv.org/abs/2306.01740 |
| S56 | Wunderlich, F. & Memmert, D. (2020). Are betting returns a useful measure of accuracy in (sports) forecasting? Int. J. Forecasting 36(2), 713–722 | Returns ≠ accuracy | Abstract only | https://ideas.repec.org/a/eee/intfor/v36y2020i2p713-722.html |
| S57 | Hubáček, O. & Šír, G. (2023). Beating the market with a bad predictive model. Int. J. Forecasting 39(2), 691–719 | Decorrelation from the market | Abstract only | https://ideas.repec.org/a/eee/intfor/v39y2023i2p691-719.html |
| S58 | Whelan, K. (12 Aug 2026). The Truth about Closing Line Value | Limits of closing-line value | Full text (web reader) | https://www.karlwhelan.com/?p=2595 |
| S59 | Data Golf (18 Dec 2020). Analyzing betting odds | Pinnacle's close ≈ realised returns (golf) | Full text (web reader) | https://datagolf.com/analyzing-betting-odds |
| S60 | Baker, R. D. & McHale, I. G. (2013). Optimal betting under parameter uncertainty: improving the Kelly criterion. Decision Analysis 10(3), 189–199 | Shrunk Kelly, tennis data | Abstract only | https://ideas.repec.org/a/inm/ordeca/v10y2013i3p189-199.html |
| S61 | MacLean, L. C., Thorp, E. O. & Ziemba, W. T. (2010). Long-term capital growth: the good and bad properties of the Kelly and fractional Kelly criteria. Quantitative Finance 10(7) | Fractional Kelly | Citation only (search summary) | https://www.stat.berkeley.edu/~aldous/157/Papers/Good_Bad_Kelly.pdf |
| S62 | Uhrín, M., Šourek, G., Hubáček, O. & Železný, F. (2021). Optimal sports betting strategies in practice: an experimental review. IMA J. Management Mathematics | Adaptive fractional Kelly | Abstract only | https://arxiv.org/abs/2107.08827 |
| S63 | Forrest, D. & McHale, I. G. (2019). Using statistics to detect match fixing in sport. IMA J. Management Mathematics 30(4), 431–449 | Model-vs-market integrity screens | Abstract via a search index | https://livrepository.liverpool.ac.uk/id/eprint/3063428 |
| S64 | Nosek, B. A., Ebersole, C. R., DeHaven, A. C. & Mellor, D. T. (2018). The preregistration revolution. PNAS 115, 2600–2606 | Pre-registration | Abstract only | https://pmc.ncbi.nlm.nih.gov/articles/PMC6233068 |
| S65 | Kapoor, S. & Narayanan, A. (2023). Leakage and the reproducibility crisis in machine-learning-based science. Patterns | Leakage taxonomy | Abstract only | https://pmc.ncbi.nlm.nih.gov/articles/PMC10499856 |
| S66 | Carty, D. (13 Jun 2011). Resident Fantasy Genius: When Hitters' Stats Stabilize. Baseball Prospectus | Samples at which statistics are half signal | Full text (web reader) | https://www.baseballprospectus.com/?p=14215 |

**In-project sources:** [event-levels study](../../event_levels/README.md) (EL); [lineage audit](01_lineage.md) (01); [UFC-analog report](06_ufc_analog.md) (06); [input-data audit, finding #6](../../input_data_audit/README.md); [product-centring study](../../ios_product_centring/README.md); [adoption framework](../../adoption_framework/README.md); [current best model](../../../decisions/2026-10-08-current-best-model.md).
