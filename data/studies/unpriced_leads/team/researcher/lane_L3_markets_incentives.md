# Lane L3 report (markets, incentives and the draw), as returned by the subagent on 13 Oct 2026

Verbatim copy of the subagent's final message (brief: `subagent_briefs.md`, lane L3). R1 has not re-verified every row; the rows R1 spot-checked are marked in the memo. Kept as evidence for the lead and a reviewer.

---

# Lane L3 (markets, incentives and the draw): literature report

All sources were accessed on 13 Oct 2026. The session's shared web-search budget ran out partway through. After that I only fetched pages I had already found, so topic 5 and the injury-news part of topic 2 are thin.

## Summary

- **Nothing in this lane has been tested against a sharp close.** Every incentive, entry-type and home result I found is measured against rankings or Elo. The market studies use average, Bet365 or Betfair odds, mostly from before 2020. So every candidate below is untested against the Pinnacle/BetOnline close of 2025–26.
- **The firmest new finding is a settlement mismatch, not a statistic.**
  - Polymarket's rules resolve a mid-match retirement to the player who advances, and a walkover to 50-50.
  - Pinnacle voids moneyline bets if a player retires before one completed set. Older quotes of its rules say two sets. Check this against Pinnacle's own rules page; I could not load it.
  - So a Pinnacle-first odds input is a price that assumes the match goes on, and it cannot carry a player's risk of retiring early for a Polymarket bet.
- **The best-replicated incentive effect is the superstar "shadow".** ATP, 2004–19, controlled for ranking only:
  - top-20 players who are not superstars win 3.4 percentage points (pp) less often while a superstar is still in the draw;
  - the effect is larger when the superstar is the likely next-round opponent;
  - players ranked outside the top 50 win 4.1 pp more often.
- **How a player entered the draw matters at Slams.** First rounds, 1978–2023, controlled for ranking only:
  - qualifiers gain +0.40 to +0.67 log-odds and wild cards +0.40 to +0.57 over direct entrants;
  - men's lucky losers lose −0.31 to −0.40 log-odds.
  - Most of this is probably players whose ranking lags their level, which Elo and the close already absorb. The lucky-loser deficit is the less obvious part.
- **Market structure says where the close is noisier, rather than giving player statistics:**
  - bookmakers' margins are higher on WTA matches than ATP matches (51,881 matches);
  - on Betfair, the favourite–longshot bias grows with uncertainty and with how unevenly bettors' attention falls on the two players;
  - lower tiers produce most integrity alerts.
  - On Polymarket and Kalshi, sports prices are well calibrated within 48 hours of the event but too close to 50% a month or more out.
- **Smaller practitioner signals (Sackmann, Tennis Abstract):**
  - seeds win 61% against unseeded players at 250s held the week before a Slam, against 70% at other 250s (2009–12, raw win–loss);
  - no general letdown after a title;
  - players handed a walkover perform as predicted;
  - Davis Cup home singles run about 15% above Elo expectation.
- **The popularity, beauty and Google-search claims (theses of 2022–23) are weak.** They use average or Bet365 odds and are in-sample, and the closely related "buzz" result failed the correction study you already know. I would not spend inputs on them.

## 1. Market efficiency of tennis prices, 2018–2026

| Citation | Type | Read level | Data and seasons | Claim and effect size (unit) | vs market? | Candour |
|---|---|---|---|---|---|---|
| Barrutiabengoa, Corredor & Muga (2022), [Does the betting industry price gender?](https://ideas.repec.org/a/sae/jospec/v23y2022i7p881-906.html), *J. Sports Econ.* 23(7):881–906 | peer-reviewed | abstract only | ATP+WTA, 51,881 matches; seasons not seen | Books "quote higher prices for women's matches than for men's" (bookmaker margin), even controlling for surprise and media attention; media attention is the information-asymmetry channel. No size seen | soft books (two analysed separately) | A margin is not a bias in probabilities; it shows where prices are less informed |
| Abinzano, Muga & Santamaría (2019), [Hidden power of trading activity: the FLB in tennis betting exchanges](https://observatorio-investigacion.unavarra.es/documentos/5f8e909a2999527b46a0067a?lang=en), *JSE* 20(2):261–285 | peer-reviewed | abstract/summary ([summary](https://hedgefundalpha.com/strategies/tennis-betting-exchanges/)) | Betfair; seasons not seen | Mispricing rises with volume and falls with institutional bettors. The favourite–longshot bias rises with uncertainty and with relative attention to the favourite. Information enters faster in more-watched markets. No numbers seen | exchange | Old data; describes mechanisms, not predictors |
| Le (2026), [Decomposing crowd wisdom](https://arxiv.org/html/2602.19520v2), arXiv 2602.19520v2 | working paper | partial | Kalshi 2021–25, Polymarket 2023–25; 353m trades, 429k contracts; sports not split by sport | Sports calibration slope 0.90–1.10 at 0–48 h, 1.74 beyond one month (prices too close to 50%, so favourites are underpriced far out). Polymarket sports mean slope 1.06. No trade-size effect | prediction markets | No tennis breakdown |
| Independent Review of Integrity in Tennis (2018), per [SI/AP](https://www.si.com/tennis/2018/04/25/corruption-problems-lower-levels); [IBIA 2025 report](https://ibia.bet/media/documents/IBIA_REPORT2025_FINAL.pdf) | integrity bodies | press snippets | Q1 2018; 2024–25 | Q1 2018: 38 alerts, 23 from ITF Futures, 1 ATP, 1 WTA. IBIA: 58 tennis alerts (2024), 74 (2025), 29 of them outside the main tours | n/a | Alerts are not proven fixes; no split by level seen |
| Hatfield, Tawn & Kirkbride (2019), [Statistical methods for detecting match-fixing in tennis](https://eprints.lancs.ac.uk/id/eprint/141874/), PhD, Lancaster | thesis | skimmed | 274 matches 2013–16, Challenger to Slam, one exchange | Models the whole pre-match odds path, not just opening vs closing. Glicko ratings often disagree with opening odds. No population effect size | exchange | Tiny sample; a methods study |
| "Nishikori" (2019), [Do Pinnacle closing prices in tennis tell the full story?](https://www.sportstradingnetwork.com/article/do-pinnacle-closing-prices-in-tennis-tell-the-full-story-can-you-win-in-the-long-run-without-beating-them/) | tipster claim | full | 3,000 ATP bets at Pinnacle, 2016–19 | 8.9% ROI against −0.2% expected from closing-line value | Pinnacle close | One tipster, survivorship; an anecdote |
| Johansen (2020), [MSc thesis, CBS](https://research.cbs.dk/en/studentProjects/empirical-study-of-information-efficiency-in-betting-markets-evid/); anonymous [MSc thesis, Aalto](https://aaltodoc.aalto.fi/items/4fa370de-ab49-464b-95d8-1379357dbd44) | theses | abstract only / snippet only (403) | ATP 45,813 matches over 18 years; Betfair 7,555 ATP matches 2010–13 | CBS: betting the favourite–longshot bias gives a "statistically significant abnormal profit", no number given. Aalto: result not seen | multi-book; exchange | In-sample; probably best available odds |

## 2. Biases since 2019, retirements and settlement

| Citation | Type | Read level | Data and seasons | Claim and effect size (unit) | vs market? | Candour |
|---|---|---|---|---|---|---|
| Tijmensen (2022), [Sentiment bias … tennis betting and Google searches](https://thesis.eur.nl/pub/61914/Tijmensen_Sebastiaan-Final-version.pdf), MSc, Erasmus | thesis | skimmed | ATP 250/500/1000, 2017–19, ~6,056 matches | The Google-search gap shifts odds; the more-searched player wins more often than the odds imply. Average margin ~5%; no effect in pp | average, max, Bet365 | In-sample, 3 seasons, not sharp odds. Same direction as van Rheenen 2017 (known) |
| Ramirez (2023), [Essays on information & beliefs](https://reading-pure-test.eprints-hosting.org/119850/1/RAMIREZ%20_Thesis_Philip%20Ramirez.pdf), PhD, Reading, ch. 3 | thesis | partial | WTA main draws 2015–20, 20,206 matches | Errors in average odds depend on rank difference and on a CNN beauty-score gap (p = 0.027) and a skin-tone gap. A Kelly staking strategy is claimed profitable | average, best, Bet365 | Same data pipeline as the buzz paper that failed the Clegg & Cartlidge correction (known); no replication found |
| Settlement rules: Polymarket ([market rules via aggregator](https://polyguana.com/market/1662867)); Pinnacle ([soccerway guide](https://www.soccerway.com/betting/guide/tennis-retirement-rules/); [older forum quote](https://www.therx.com/threads/lets-all-be-aware-of-tennis-wagering-rules.284061/)) | provider claims | snippets | current | Polymarket: retirement or default after the start goes to the player who advances; a walkover resolves 50-50. Pinnacle: void unless one set is completed (guide), or two sets (older quote) | defines what each price means | Check primary sources. BetOnline's rule not found |
| Palau et al. (2024), [Retirements … second- and third-tier tournaments](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0304638), *PLoS ONE* 19(6):e0304638 | peer-reviewed | full (most) | Men's Challenger+ITF 1978–2019 (584,806 matches); women's WTA125+ITF 1994–2018 (267,380) | Retirements 3.30% (men) and 2.73% (women); 1.56 and 1.36 per 1,000 games. ITF vs Challenger rate ratio 1.23. Hard or clay vs grass ≈2.0 (men). +31% risk per 5 years of mean age | none | Descriptive epidemiology |
| Sackmann, [Masters of retirement (2012)](https://www.tennisabstract.com/blog/2012/11/05/janko-tipsarevic-and-the-masters-of-retirement/), [Prize money whack-a-mole (2019)](https://www.tennisabstract.com/blog/2019/12/30/grand-slam-prize-money-whack-a-mole/), [Withdrawal effects (2012)](https://www.tennisabstract.com/blog/2012/09/03/withdrawal-effects/) | practitioner | full | ATP | Retirement rates persist by player (Tipsarevic 3.9% of 434 matches vs a tour average ≈1.5%). ATP tour-level first-round retirements fell from 48 to 20 (4.4% to 1.6%) between 2015 and 2019 after the paid-withdrawal rule. Slam men's first-round retirements: 9 in 2010, 9 in 2019. Walkover beneficiaries won 48.2% of their next matches vs 48.9% predicted (n = 139) | none (Elo, Jrank) | Small samples, descriptive |

## 3. Incentives

| Citation | Type | Read level | Data and seasons | Claim and effect size (unit) | vs market? | Candour |
|---|---|---|---|---|---|---|
| Deutscher, Neuberg & Thiem (2023), [Who's afraid of the GOATs?](https://ideas.repec.org/a/eee/joepsy/v99y2023ics0167487023000648.html), *J. Econ. Psych.* 99:102663 | peer-reviewed | abstract (numbers taken from the replication below) | ATP 2004–19 | Superstars in the draw lower top-20 players' win probability, even in early rounds. The effect is stronger with several superstars, vanishes once they are out, and raises retirements of strong players who are not superstars | ranking difference + player-season fixed effects | Not tested against odds; Big Four era. It may be the "Deutscher et al. 2021" on your known list |
| Creutzburg (2024), [Superstar effect in tennis – within-match](http://www.hced.uni-hamburg.de/WorkingPapers/HCED-079.pdf), HCED working paper 079; [2026 journal version](https://journals.sagepub.com/doi/10.1177/15586235261456651) | working paper + journal | skimmed | 27,366 ATP main-draw matches, 936 events, 2004–19 (Slams, Indian Wells, Miami and superstar matches excluded) | **−3.4 pp** win probability for top-20 higher-ranked players while a superstar is in the draw; larger if he is the likely next opponent. **+4.1 pp** for higher-ranked players outside the top 50. Home ≈ +6 pp | rankings only | Your known "Creutzburg et al. 2024" seems to be his home-advantage paper, so this one may be new to you |
| Gilsdorf & Sukhatme (2008), [Testing Rosen's model](https://ideas.repec.org/a/sae/jospec/v9y2008i3p287-303.html), *JSE* 9(3):287–303 | peer-reviewed | abstract | ATP 2001, 2,632 matches, 68 events | A larger prize gap between rounds raises the stronger player's win probability (significant); no size in the abstract | rankings | One season |
| Lallemand, Plasman & Rycx (2008), [Women and competition in elimination tournaments](https://ideas.repec.org/p/dul/wpaper/05-19rs.html), *JSE* 9(1):3–19 | peer-reviewed | abstract | WTA | A larger prize spread raises effort. In uneven matches favourites win more games and underdogs perform worse | rankings | Old |
| Sunde (2009), *Applied Econ.* 41(25):3199–3208 ([IZA DP 947](https://docs.iza.org/dp947.pdf)) | peer-reviewed | working paper, partial | ATP Slam and Masters semis/finals, 1990–2002 (156 events) | Stage prizes raise games won; larger rank gaps lower total games (effort) | rankings | Old; semis and finals only |
| Babington, Goerg & Kitchens (2020), [Superstars …?](https://ideas.repec.org/a/sae/jospec/v21y2020i1p44-63.html), *JSE* 21(1):44–63 | peer-reviewed | abstract | golf, alpine skiing | Cannot reject "no superstar effect" | — | Not tennis; a counterweight |
| Barget, Llorca & Teste (2011), [HAL-04704556](https://ideas.repec.org/p/hal/journl/hal-04704556.html) | post-print | abstract | ATP top-30, 2007 | The prize gap between tournament levels raises performance; total prize money does not | none | Tiny |
| Sackmann (2013), [Warming up and losing out](https://www.tennisabstract.com/blog/?p=1067) | practitioner | full | ATP 250s, 2009–12 | Seeds beat unseeded players 61% of the time at 250s the week before a Slam vs 70% elsewhere. Top-4 seeds: 65% vs 74% | none (raw win–loss) | Not adjusted for opponent; old |
| Sackmann (2014), [Post-Masters blues](https://www.tennisabstract.com/blog/?p=1689) | practitioner | full | ATP 2000–14 | Finalists who play the next week lose 31% of first matches (~1 point worse than expected). Masters winners: 26.3% (slightly better). Masters winners outside the top 5: 40% vs ~20% expected (n = 17) | ranking model | No general letdown |
| Sackmann (2016), [Round robin](https://www.tennisabstract.com/blog/2016/10/31/how-to-keep-round-robin-matches-interesting/) | practitioner | snippet | Tour Finals format | 12.5% of final-day outcomes include a dead rubber, plus 12.5% "almost dead" | none | Too few matches to model |

## 4. Entry type: qualifiers, lucky losers, wild cards

| Citation | Type | Read level | Data and seasons | Claim and effect size (unit) | vs market? | Candour |
|---|---|---|---|---|---|---|
| Eckmann (2024), [Unlucky losers: entry channel effects](https://doi.org/10.7298/kr1a-s955), MS thesis, Cornell | thesis | skimmed, including the coefficient table | Slam first rounds: men 1978–2023 (20,392 player-matches), women 1984–2023 (18,836) | Log-odds vs direct entrants, controlling for rank difference: qualifiers +0.395 (men) / +0.556 (women), or +0.542 / +0.667 when opponent rank is added. Wild cards +0.396 / +0.414 (+0.559 / +0.566). Lucky losers, men −0.402 (SE 0.127) / −0.306 (0.128); women not significant. Effects shrink after the move to 32 seeds in 2001; not surface-specific | rankings only | Ranking lag explains much of it; first round only |
| Sackmann (2012), [Competitive wild cards](https://www.tennisabstract.com/blog/2012/10/26/which-tournaments-award-competitive-wild-cards/) | practitioner | full | ATP 1998–2012, 65 events | Raw wild-card win rates range from 20% (Shanghai) to over 50% (Newport); British wild cards at Wimbledon ≈20% | none | Raw rates |
| Sackmann (2023), [Better to be unseeded?](https://www.tennisabstract.com/blog/2023/07/02/is-it-ever-better-to-be-unseeded/) | practitioner | full | 2023 Wimbledon simulation | Seeds 25–32 reach the last 16 16.5% of the time vs 14.5% if unseeded | none | Value of the path, not a match-level effect |

## 5. Lower-level results

| Citation | Type | Read level | Data and seasons | Claim and effect size (unit) | vs market? | Candour |
|---|---|---|---|---|---|---|
| Sackmann (2018), [Translating ATP stats across tour and Challenger levels](https://www.tennisabstract.com/blog/2018/04/25/translating-atp-statistics-across-main-tour-and-challenger-levels/) | practitioner | full | ATP 2012–17, the 100 players with the most matches at both levels | League factor ≈1.095 on total points won (52.5% at Challengers ≈ 48.0% on tour); 1.086–1.103 by year. Player ratios vary, e.g. Ebden 0.982, F. Mayer 1.180 | none | Not shown to persist out of sample |
| Sackmann (2025), [Why my forecasts sometimes differ from betting markets](https://www.tennisabstract.com/blog/2025/11/28/why-do-my-forecasts-sometimes-sharply-differ-from-betting-markets/) | practitioner | full | case study | Large Elo–market gaps come mostly from thin data on low-ranked players whose results are at ITF level (his men's Elo leaves ITF out). Other causes: unreported injuries, indoor vs outdoor, returns from absence, juniors on new surfaces. The market was right in the case shown | market (unnamed) | Anecdotal; supports your level layer |

## 6. Home advantage and crowds

| Citation | Type | Read level | Data and seasons | Claim and effect size (unit) | vs market? | Candour |
|---|---|---|---|---|---|---|
| Sackmann (2016), [Argentina's road warriors](https://www.tennisabstract.com/blog/2016/11/29/how-argentinas-road-warriors-defied-the-davis-cup-home-court-odds/) | practitioner | summary of full post | Davis Cup World Group + play-offs, 2003–16, 322 ties | Hosts won 60.9% of ties vs 53.1% from Elo simulation. Singles ~15% better than expected, doubles ~6% | Elo only | The host picks the surface; format changed in 2019 |
| Creutzburg, Maennig & Mueller (2026), [From bias to bliss](https://ideas.repec.org/p/hce/wpaper/075.html), *Contemp. Econ. Policy* 44(2):380–393 | peer-reviewed | abstract | ATP 2001–20 | Splits home advantage into fans, referee bias, travel fatigue and familiarity; Black players gain more from fan support. No size seen | none seen | Probably the known "Creutzburg et al. 2024" |
| Sackmann, [Bubble (2020)](https://www.tennisabstract.com/blog/2020/08/27/how-sports-are-analytically-different-in-the-bubble/); [Post-Covid (2021)](http://www.tennisabstract.com/blog/2021/01/25/the-post-covid-tennis-world-is-unpredictable-the-match-results-are-not/) | practitioner | full | ATP/WTA restart, 2020 to early 2021 | Men's Elo Brier score 0.213 after the restart vs 0.212 in 2017 to early 2020: a months-long layoff barely mattered. Women mixed | Elo only | Bears on your rust result |
| Gucciardi & Ruberti (2025) | known | — | — | Already known; nothing new found against it. Home advantage persisted without crowds | — | — |

## Candidate statistics not in the model

**C1. Early-retirement risk, aware of the venue's rules.**
- **Definition:** for each player:
  - retirement and walkover rate over 24 months and over the career, shrunk toward the tour mean;
  - retired, withdrew or took a medical time-out (if that data exists) in the last 14 days, and days since;
  - a "paid to start" flag: Slam first round, or first-round loser money large relative to the player's 52-week earnings;
  - the same for the opponent.
- **Mechanism:** Pinnacle voids early retirements, so its close prices the win given at least one (or two) sets are played. Polymarket pays the advancing player after any start. The gap is about P(early retirement), which is concentrated on retirement-prone players, older players, hard and clay courts, and lower tiers.
- **Evidence:** Palau et al. 2024; Sackmann 2012 and 2019; the rules pages. None of it is tested against odds.
- **First check:** how Stage 0 labels retirements, and whether the gap moves the log-loss at Polymarket's resolution rule.

**C2. Superstar shadow in the draw.**
- **Definition:** for each match:
  - the number of "dominant" players still alive in the draw at match time, defined by an Elo gap (e.g. at least 100 points above the third-best entrant), not by name;
  - whether one of them is the player's likely next-round opponent;
  - interacted with the player's own rank band (top 20 vs outside the top 50).
- **Mechanism:** the value of advancing falls, so effort shifts and retirements rise. The close prices the match-up, probably not the draw beyond it. This applies to the Sinner/Alcaraz and Sabalenka/Świątek eras.
- **Evidence:** −3.4 pp and +4.1 pp, ATP 2004–19, controlled for ranking only (Deutscher et al. 2023; Creutzburg 2024). It failed in golf and skiing (Babington et al. 2020).

**C3. Entry-type flags** (qualifier, lucky loser, wild card, protected/special ranking, alternate).
- **Mechanism:**
  - a lucky loser enters late and with a "reference-point" handicap;
  - wild cards mix prospects and home picks;
  - protected-ranking players return with stale ratings.
- **Evidence:** Eckmann 2024 (log-odds above, controlled for ranking only).
- **Caveat:** mostly ranking lag that Elo and the close already absorb. Test the men's lucky-loser deficit specifically.

**C4. The week before and after a big event.**
- **Definition:** event in the week before a Slam (or a 1000) × player is entered in that event × favourite or top-4 seed. The mirror case: the first event after a Slam where the player reached at least the quarter-finals.
- **Mechanism:** top players save effort and withdraw late. The close may price only the famous cases.
- **Evidence:** Sackmann 2013 (61% vs 70%, raw, 2009–12). His 2014 post found no letdown after titles.
- **Caveat:** probably partly priced by now; only about 8–10 such weeks per tour per year.

**C5. What is at stake for this particular player.**
- **Definition:**
  - (prize for winning this round − prize for losing) ÷ the player's 52-week prize money;
  - ranking points at stake ÷ the gap to the nearest threshold at that date (Slam main-draw cut, top 100, top-32 seeding, the top 8 for the year-end Finals).
- **Mechanism:** tournament theory says the marginal payoff differs by player. The close prices level and round, not each player's marginal utility.
- **Evidence:** Gilsdorf & Sukhatme 2008; Lallemand et al. 2008; Sunde 2009. All old and controlled for ranking only.

**C6. Measures of how far to trust the close.**
- **Definition:**
  - Pinnacle's margin at the close;
  - the gap between Pinnacle's and BetOnline's prices with margins removed;
  - Pinnacle's move from open to close, and its direction relative to the model's non-market inputs;
  - the number of books pricing the match, and the level.
- **Mechanism:** margins widen where information is unequal (WTA, less-covered matches), the longshot bias grows with uncertainty, and lower tiers carry most integrity risk. A large move also signals news, such as an injury, that box-score inputs cannot see.
- **Evidence:** Barrutiabengoa et al. 2022; Abinzano et al. 2019; the integrity bodies; Le 2026.
- **Requirement:** live equivalents must exist at bet time, so that live inputs match training.

**C7. A player's own level-translation ratio** (men Challenger↔tour; women ITF/WTA 125↔tour).
- **Definition:** opponent-adjusted points-won ratio between levels over 24–36 months, shrunk toward ≈1.095.
- **Mechanism:** a single common discount, used by Elo, the market and probably your level layer, misjudges players who do much better at Challengers than on tour, and the reverse.
- **Evidence:** Sackmann 2018 only.
- **First check:** split-half persistence, and whether your level layer's weights already capture it.

**C8. Team-event home tie (low priority).** A host-nation flag for Davis Cup, BJK Cup and United Cup. Sackmann 2016 finds +15% in singles vs Elo. Only useful if those matches are in your training frame.

## Searches that found nothing useful

- Academic tests of letdown after a title or a Slam against odds (only Sackmann 2014 exists).
- ROI against betting odds by entry type; academic wild-card studies.
- Players returning on a protected ranking.
- First-round byes and match rhythm.
- Dead rubbers against odds. Csató's tanking work is about football tournament design; Sackmann's "Tanking: a model" (2020) is theory only.
- Patriotic or nationality bias in tennis betting (football only: Braun & Kvasnicka).
- Pre-match over-reaction to upsets or recent form (only in-play: Lobão & Rolla, known).
- How markets price fatigue.
- Rust after the COVID restart against odds (only Bundesliga and NBA studies).
- Tennis-specific Polymarket or Kalshi calibration.
- Effort around ranking points or the year-end Finals race.
- Injury news and withdrawal reactions in markets.
- Efficiency at Challenger or ITF level beyond Buchdahl (known): only integrity reports.
- Not searched before the budget ran out: mandatory-event effects, Kovalchik's blog, practitioner pricing notes on Challengers.
