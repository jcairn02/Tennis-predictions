# What "model what the closing line is not pricing" means in practice, and a residual shop for this model

12 Oct 2026 · Edge-anatomy team, round 1 · Role: the betting-market practitioner (a syndicate's head of modelling) · A Claude Opus 5.5 subagent of session `6483c720-30a3-46ff-9519-287690b6f9d8` · Read-only; **no match outcome was read** (§ 7) · Input to the lead's synthesis, not a decision.

**Labels.** [Obs] observed in the repository; [PR] peer-reviewed; [WP] working paper or preprint; [Prov] a provider's, practitioner's or blogger's claim; [Inf] my inference; [Sug] suggestion. mLL = milli-log-loss per match (lower log loss is better); each figure says what + means. "Unresolved" = the 95% interval spans 0 (P(better) given where computed).

## In short

* **Two businesses hide in the advice.** *Beat the close*: statistics the sharp close never prices, scored slowly by results. *Beat the move*: statistics the close will price but the current line has not, bet early and scored fast by closing-line value (CLV). The current model is a beat-the-close model; [Inf] most professional money is made beating the move.
* **Both readings of "the most recent closing line" point to process, not to a new model form.** (a) Score against the sharpest close available, and model its residual. (b) Treat every signal as perishable: watch it migrate from "missed by the close" to "learned between open and close".
* **The current model already is Benter's "market + adjustments", done non-linearly,** and no alternative tested beat it (§ 1.3). Missing: a sharpest-close yardstick, a per-signal ledger, decay monitors, a price tape, a bet ledger.
* **The 2026 headline is scored against a soft stand-in.** [Obs] 1,679 of the 1,774 men's matches of 2026 are scored against BetOnline's line, which a BetOnline + Polymarket average beats by 2.00 mLL. [Inf] Against the sharpest 2026 price, the men's +3.57 is probably +1.5 to +3. 2025 (81% Pinnacle) is the cleaner reading.
* **A recent window cannot resolve one statistic.** [Inf] 80% power needs about 3,900 / G matches by a coefficient test with the close as offset, and 16,000 / G by out-of-sample log loss (G in mLL). Single signals here are worth 0.1–0.4 mLL. The open→close move is about 15 times less noisy per match than the result: it is the fast probe of what the market learns.
* **Learning is mixed** [Obs]. Gone in 2025–26: the weak-pair favourite–longshot pattern, part of BetOnline's opening softness. Held or grown: the serve-speed signal, the under-rating of players from lower levels.
* **Missing for a CLV programme** [Obs]: a scheduled recorder (Pinnacle's has made 3 pulls), any bet log, BetOnline's line history, Pinnacle's closes from August 2025.
* **Eight ranked suggestions** in § 6, led by the sharpest-close re-score, the price tape and CLV ledger, and the move scan.

## 1. What the advice most likely means

### 1.1 Two businesses

| | Beat the close (residual alpha) | Beat the move (timing alpha) |
|---|---|---|
| The statistic predicts | the result, *given the sharp close* | *where the close will go* |
| Example here [Obs] | Men's serve-speed change: R² 0.003 on the closing odds, replicated blind in 2025–26 (`serve_speed_tabpfn`) | Polymarket 24–48 h out: the price moves 29–45% toward the model by the close (`bet_timing`) |
| The close is | the anchor (an input) | the referee |
| Bet | near the close, at the cheapest venue with depth | early, at the venue that lags |
| Scored by | results against the sharpest close: slow | CLV, then results: fast |
| Decay looks like | the residual coefficient falls to 0 | the move comes earlier, then the opener absorbs it |

[Inf] Read literally, the advice is the first column. With the close as an input, a bet at the close has a CLV of minus the margin by construction (`adoption_framework/review_betting.md`, finding 3). So the current model is scored only by results and cannot see which signals are being learned.

### 1.2 How professionals operationalise it

* **The sharpest price: a residual model.** Benter's second-stage logit: pseudo-R² 0.1237 for the public, 0.1016 for his model, 0.1327 combined [WP/Prov]. [Inf] A model fed a soft line "beats" it partly by knowing what sharper books know: book lag, not an unpriced statistic.
* **Today's market: perishable signals.**
  * Bookmakers were slow to price the Bundesliga's vanished home advantage [PR, Deutscher et al. 2021].
  * The WTA "buzz" mispricing earned nothing after 2020 [WP, Clegg & Cartlidge 2024].
  * Published equity predictors return 58% less after publication [PR, McLean & Pontiff 2016].
  * Pros detect decay by CLV per bet type over time, by lines moving before they bet, and by limits [Prov]. "Beating the closing number" is "the most important thing" (Spanky Kyrollos) [Prov].
* **Models of the move.**
  * Open→close moves carry momentum and value that results reverse, too small to beat costs [PR, Moskowitz 2021]. CLV must exceed the margin: three of five positive-CLV deciles still lost (NBA) [Prov, Whelan 2026].
  * [Obs] BetOnline's line moves 2.5 points open→close, but not toward the model (slope +0.01 [−0.02, +0.04]); Polymarket's does, 24–48 h out.
  * [Inf] Tennis lines move on earlier rounds' toll (often after the opener), withdrawals, injuries, conditions and syndicate money.
* [Inf] **The cleanest decay signature:** a signal being learned migrates from the residual (result − close) into the move (close − open), then into the opener.

### 1.3 Is the close inside a non-linear model trained over a decade wrong?

* [Obs] **No alternative tested beats it.**
  * A stack of a no-odds TabPFN and the close loses by 1.15 mLL [0.55, 1.76] (`meta_stack`).
  * Linear, ridge, GAM and boosted residuals gain +0.09 to +0.30 over the odds for men, against TabPFN's +1.57 (`tabpfn_thinking`, inputs of 2 Oct; + = better than the recalibrated odds).
  * Recent-only windows add nothing and over-react (`training_window`).
* [Inf] **Two process gaps remain.**
  * *Era-averaged trust:* TabPFN has no time input, so a signal the market learned in 2024 keeps its older weight until later rows dominate. `training_window` read seasons ≤ 2024 only.
  * *Opacity:* the edge is not attributed, so decay shows only in the aggregate, about 9,000 men's matches per verdict.

## 2. Blueprint: a tennis residual shop on this repository

### 2.1 The stations

0. **Anchor.** Pinnacle's current margin-free line (decided), else BetOnline's; record Polymarket and Betfair beside it. Calibrated per tour and venue, walk-forward.
1. **Discovery.** The scout's ideas, the feature universe, what the market learns late (S3), where the close is wrong (level, round, surface-season start, climbers), new feeds. Mechanism, sign and size are written before any outcome is read.
2. **Screen.** A score test with the close as offset (and the current model as a second offset), four-week clusters, by era (2013–16, 2017–19, 2020–22, 2023–24, 2025 – Jul 26). Empirical-Bayes shrinkage across candidates; then the move test (§ 2.2).
3. **Admit.** Into the pool with a verdict and its class; [Sug] a fast offset lane (S5).
4. **Monitor.**
   * Per family: walk-forward realisation, a CUSUM of score contributions, the residual-to-move migration.
   * The whole model: CLV by venue and horizon, realisation against Pinnacle by quarter, predicted against realised ROI by edge band, with `review_betting.md`'s gates and triggers.
5. **Execute.**
   * Never-priced signals near the close at the cheapest venue with depth; learned signals early at the lagging venue, posting at Polymarket.
   * Fractional Kelly on a shrunk edge (Baker & McHale), only above the venue's cost: the 0–1% predicted-ROI band breaks even (`pinnacle_first` § 8).
   * Settle by each venue's rules (S8).

### 2.2 The map of every statistic

| | Move coefficient ≈ 0 | Move coefficient > 0 |
|---|---|---|
| **Residual coefficient ≈ 0** | Priced at the open: builds a price, not a bet | Learned by the close: bet early, score by CLV |
| **Residual coefficient > 0** | Never priced: bet late at the sharpest venue, score by results | Partly learned: both; watch the migration |

### 2.3 What "recent" can resolve

[Inf] For a standardised signal with true residual coefficient β, the gain is G = ½·E[p(1−p)]·β². A score test then needs n ≈ 3.92 / G matches for 80% power (5%, two-sided). An out-of-sample log-loss comparison has half the z, so it needs four times as many. E[p(1−p)] of the close (0.195–0.209 by season [Obs]) cancels.

| Window | Matches | Smallest G at 80% power: coefficient test | … log-loss comparison |
|---|---:|---:|---:|
| One men's season | ~2,600 | 1.5 mLL | 6.0 mLL |
| One season, both tours | ~5,100 | 0.8 | 3.1 |
| 2025 – 28 Jul 2026, both tours [Obs] | 8,591 | 0.46 | 1.8 |
| … men only [Obs] | 4,394 | 0.9 | 3.6 |
| 2020–2024, both tours | 22,265 | 0.18 | 0.7 |

* **Cross-check** [Obs]: the men's whole model (G ≈ 1.7) needs about 9,000 matches by log loss, so a men's season resolves it about a third of the time. The backtest resolved 3 of 7 men's seasons (`pinnacle_first`).
* **Single signals are smaller** [Obs]: the 16-statistic profile +0.33, surface Elo +0.12 (`market_anchoring`), climbers about 0.1 (`event_levels`), speed +0.41 (men).
* **CLV is the fast scorekeeper** [Obs]: its intervals here are about 4 times narrower than realised profit's (`bet_timing` § 4: +0.47 [+0.22, +0.71] against −0.27 [−1.20, +0.66] per 100 matches), so about 15 times fewer matches are needed.
* **The move is the fast probe** [Inf]: in log-odds, the result's noise per match is about 2.2 and the open→close move's about 0.15, so a move coefficient needs about 1/200 of the matches.
* **So "recent" means** [Sug]: estimate on every comparable season; test decay on rolling 24 months; read moves on 6–12 months; read CLV on rolling 500 bets.

### 2.4 Against the current design

* **Keep:** TabPFN with the close inside as the engine; its non-linear reweighting is the best forecaster tested (§ 1.3).
* **Change the yardstick:** the sharpest close per match, not its own recalibrated input (BetOnline's line in 2026).
* **Add what it lacks:** per-signal attribution (residual and move coefficients, realisation, CLV), monitored or recency-weighted trust instead of trust averaged over 2013..Y−1, an offset lane for new signals instead of partial uptake as TabPFN columns, weekly CLV instead of a verdict every ~9,000 men's matches, and bet timing by signal class instead of one plug-in.

## 3. Literature and public evidence on tennis closing lines

| Soft spot | Evidence | Type | Decayed? |
|---|---|---|---|
| Favourite–longshot bias | At soft books (Forrest & McHale 2007); larger when both players are outside the top 50, and at Slams (Lahvička 2014); on exchanges, for lower-ranked players and big events (Abinzano et al. 2016); widened against clear underdogs (Candila & Scognamillo 2019); test method matters (Hegarty & Whelan 2024). Pinnacle claims an ATP slope of 0.994 | PR; WP; Prov | [Obs] The weak-pair pattern was in the close in 2014–24 and absent in 2025–26 (`pair_strength`) |
| Women's tour | WTA "buzz" mispricing (Ramirez et al. 2023), mostly one outlier bet, none after 2020 (Clegg & Cartlidge 2024) | PR; WP | Yes. [Obs] The women's edge is mostly a curved calibration of the odds (`tabpfn_thinking`) |
| Lower tiers | Integrity alerts concentrate at Challenger 50/75 and ITF (ITIA 2025). No published efficiency study. [Obs] Polymarket's clear winners earn +1.75¢ per $1 at Challengers, among the highest of any level | official; Obs | Not measurable before Sep 2025 |
| Retirements | Retirement risk read from Betfair markets with different rules (Cutmore & Knottenbelt 2013). [Obs] Polymarket pays the player who advances; guides say Pinnacle voids before two completed sets | conference; Obs; Prov | — |
| Early season, returners, conditions | Blog claims only. [Obs] The close is least calibrated early in the hard-court season (slope 1.15 average, 1.09 Pinnacle, `market_anchoring`) | Prov; Obs | — |
| Models against the sharp close | The market is best (Kovalchik 2016: log loss 0.55 against Elo's 0.59; Gorgi et al. 2019; Wilkens 2021). 40 rules' profits vanish after a data-snooping correction (Lyócsa & Výrost 2018). A claimed Pinnacle weakness is gone from v2 (Clegg & Cartlidge 2025/26) | PR; WP | — |
| Open→close moves | Reversed by results, below costs (Moskowitz 2021); negatively autocorrelated (Simon 2025); Pinnacle moved 26–30% toward DataGolf's model | PR; Prov | — |

**Sources,** accessed 12 Oct 2026 († from the repository's notes, accessed 5–9 Oct). "Abs." = read at abstract level.
* Hegarty & Whelan 2024, WP, abs.: https://mpra.ub.uni-muenchen.de/121382/
* Lyócsa & Výrost 2018, PR, abs.: https://ideas.repec.org/a/taf/applec/v50y2018i20p2251-2272.html
* Lobão & Rolla 2015, PR, abs. (Betfair bettors show conservatism and anchoring): https://periodicos.fgv.br/rae/article/view/52958
* Candila & Scognamillo 2019, WP, abs.: https://ideas.repec.org/p/sep/wpaper/3_236.html
* Clegg & Cartlidge, WP, abs.: https://arxiv.org/abs/2306.01740 (v4, 2024) and https://arxiv.org/abs/2510.20454 (v2, 18 Jun 2026)
* Moskowitz 2021, PR, abs.: https://academicnewsletter.sufe.edu.cn/info/359180
* Simon 2025, PR, abs.: https://academicnewsletter.sufe.edu.cn/info/386234
* Deutscher et al. 2021, PR, abs.: https://arxiv.org/abs/2008.05417
* McLean & Pontiff 2016, PR, abs.: https://www.gwern.net/doc/economics/2016-mclean.pdf
* Cutmore & Knottenbelt 2013, conference, via search summaries: https://www.doc.ic.ac.uk/~wjk/publications/cutmore-knottenbelt-mis-2013.pdf
* DataGolf 2020, Prov: https://datagolf.com/analyzing-betting-odds
* Covers 2019 (Spanky Kyrollos), Prov: https://www.covers.com/industry/whats-the-difference-between-you-and-a-sharp-step-inside-the-mind-of-a-professional-bettor
* Whelan 2026, Prov: https://www.karlwhelan.com/?p=2595
* PFF 2021, Prov (NFL closes picked the winner 65.9% of the time, openers 63.5%): https://www.pff.com/news/bet-why-betting-early-critical-beating-nfl-markets
* Retirement rules, Prov: https://www.flashscore.co.uk/betting/guide/tennis-retirement-rules/; Pinnacle's from a snippet of https://www.soccerway.com/betting/guide/tennis-retirement-rules/
* Conditions, Prov, snippet: https://www.tennismajors.com/others-news/how-weather-and-court-conditions-impact-tennis-betting-821520.html
* † Benter 1994, Forrest & McHale 2007, Lahvička 2014, Abinzano et al. 2016, Ramirez et al. 2023, Wilkens 2021, Pinnacle: `docs/research/market-anchoring/`. Kovalchik 2016: `docs/research/rating-systems/`. Gorgi et al. 2019, Baker & McHale 2013: `lower_level_evidence/team/05_best_practice.md`. ITIA 2025: `event_levels` § 9.

## 4. What the repository has and lacks [Obs]

| Need | Held | Missing |
|---|---|---|
| Timed sharp close | Pinnacle: tennis-data to Jul 2025 (untimed), OddsTrader to 7 Sep 2025 (timed); `template_2026-10-10/odds_sources.parquet` (`p_ps`, `p_ot20`) | No Pinnacle close from Aug 2025: training uses BetOnline stand-ins, and 2026 is scored against BetOnline |
| Openers | BetOnline open and last line, timed, 2018–2026, ~34,000 matches, with inputs-known flags (`bet_timing/frame.parquet`). Pinnacle's opener to Sep 2025 (`p_ot20o`, a median 35.5 h out) | An opener is the first line OddsTrader saw |
| Price paths | Polymarket minute mids (69.3M) and every fill with its wallet (38.1M), Sep 2025 – Oct 2026 | BetOnline's line history (~68,000 requests); Betfair ticks need an account; order books: 4 days |
| Exchange closes | Betfair (`p_bfe`) and Polymarket's 30-min mid (`p_pm_m30`), ~4,150 matches of 2026 each | Betfair's is untimed |
| Lower tiers | Polymarket Challenger from Sep 2025, ITF from May 2026 | No earlier Challenger price |
| Live recording | Pinnacle recorder `src/ingest/pinnacle.py`: 3 pulls on 11 Oct | Not in `src/ingest/scheduled.py`; no scheduled BetOnline or Polymarket snapshots |
| Prediction log | Live forecasts with price source, time, market probability and q (`predictions/2026-10-12/`) | No grading yet (step 8 of `prediction_pipeline/PLAN.md`) |
| Bet log | — | `data/betting_history/` is empty |
| News | Daily match clock; official first points (main tour) | No withdrawal, injury or medical-time-out timestamps |

## 5. A practitioner's reading of 2025–26 (priors written before reading this study's results)

* **The benchmark** [Inf]. On the same matches, edge(against X) − edge(against Y) = LL(Y) − LL(X), with calibration fixed.
  * On 2026 matches, Betfair's close is +0.70 mLL sharper than BetOnline's line ([−0.13, +1.54], unresolved, P(Betfair sharper) 0.95); the BetOnline + Polymarket average +2.00 [+0.66, +3.34] (`odds_sources` § 4, both tours).
  * Against Polymarket's 30-min close the model's edge is unresolved: +0.10 to +0.80 mLL, ±3–4 (`bet_timing`; + = model better; P(better) ≈ 0.5–0.7).
  * The 2026 recalibration slope was fitted while the input was Pinnacle.
  * Hence my +1.5 to +3 for the men's 2026 edge over the sharpest price.
* **The market got earlier and dearer** [Obs]. BetOnline's opener's extra log loss over its last line fell from 3.05 mLL (2020–24) to 1.73 (2025–26), and opening bets' CLV advantage from +0.71 to −0.14 per 100 matches (`bet_timing`). Margins rose, BetOnline 3.3% → 4.0% and Pinnacle 2.5% → 2.85% (2018 → 2026). Polymarket's taker fee is about 2.5¢ per $1 at evens since July 2026.
* **Family priors** [Inf].
  * Ratings and context: nothing beside the close.
  * The close's calibration (favourite–longshot shape, venue shading): the most perishable share, and the likeliest home of the women's edge.
  * Short-memory box-score form: the likeliest to be learned (box scores are public within hours).
  * Long-memory IOS profile and speed: the likeliest to persist (costly to compute or obtain).
  * Climbers: persistent but tiny.
* **The tell** [Inf]: a family whose residual coefficient falls across 2020–22 → 2023–24 → 2025–26 while its move coefficient rises is being learned. Bet it earlier, or write it down.

## 6. Ranked suggestions

**1. Re-score the 2025 – Jul 2026 edge against the sharpest close.**
* *Build:* per match, Pinnacle to 7 Sep 2025, then Betfair's close, Polymarket's 30-min mid and their average. Add BetOnline's line recalibrated on its own 2019–2025 history.
* *Data:* `template_2026-10-10/odds_sources.parquet`, the instance's fits.
* *Test:* the template (both stages, 16 seeds) against each benchmark on the same matches; primary: men 2026 against the Betfair + Polymarket average. ±2.5–3 mLL on the edge, ±0.5–1.3 on the benchmark gaps.
* *Cost:* hours of CPU.
* *A pro would:* always. A soft yardstick flatters, and soft-book lag is a separate business.

**2. Start the price tape and the CLV ledger.**
* *Build:* schedule `src/ingest/pinnacle.py` on tournament days (paced, per the scraping decision); add BetOnline and Polymarket snapshots. Log every bet in `data/betting_history/` (venue, time, price, stake, fill, fee, rule). Grade every prediction against the venue's and Pinnacle's last pre-start price.
* *Test:* weekly CLV by venue × horizon × edge band, with a "rolling CLV below 0" trigger; about ±0.3–0.6% after 500 bets.
* *Cost:* a day or two.
* *A pro would:* first. It also restores Pinnacle's closes for training from October 2026.

**3. The move scan.**
* *Build:* regress the move (logit close − logit open) on each non-price input, each family score, `spd_L_B` and U-330, controlling for the open, clustered by four-week blocks, on matches where the input was known at the open (`known_*` flags). Moves: BetOnline 2018–2026, Pinnacle 2018 – Sep 2025, Polymarket 48 and 24 h → 30 min. Join the lead's residual scan to fill § 2.2's map by era.
* *Test (pre-registered):* does any family with a residual coefficient above 0 in 2020–24 show its move coefficient rising in 2023–26? SE about 0.001 log-odds per SD on ~30,000 pairs; the move half reads no outcome.
* *Cost:* one or two days.
* *A pro would:* yes: it shows what to bet early and warns of decay without outcomes. *Caveats:* openers are first sightings; moves carry news and over-reaction.

**4. A per-family realisation monitor, with an optional brake.**
* *Build:* split the template's disagreement with the sharp close into families with an out-of-fold additive surrogate (95–96% of TabPFN's adjustment, `tabpfn_thinking`). Each quarter, fit result ~ offset(close) + Σ ρ_f·d_f walk-forward with a two-season half-life. Alarm when a family's ρ_f is below 0.5 with 90% confidence for two windows; the brake scales d_f by the shrunk ρ_f. Start from the lead's C2 code.
* *Test:* pre-registered walk-forward 2016–2024, then 2025 – Jul 2026, then sealed matches; ±0.3 mLL. Accuracy will likely be unresolved; the value is the warning.
* *Cost:* two or three days.
* *A pro would:* build the monitor, not yet the brake: one global re-sizing read −0.07, unresolved, and recent-only scales lost in 2022–23 (`training_window`).

**5. A recency-weighted offset lane for new signals** (a structural option for the owner).
* *Build:* logit q = s·η + Σ b̃_j·x_j, each b̃_j shrunk as decided (b·τ²/(τ² + SE²)) and refitted each season with older seasons down-weighted; each signal carries its class and a CUSUM.
* *Why offsets* [Obs]: as TabPFN columns, speed was applied at about 8% and the climber signal at about a third. As an offset, the climber signal was absorbed in full (`event_levels` C2); the speed offset earned +0.41.
* *Candidates:* U-330 (its stage-2 coefficient was positive in every season of 2020–24, 1.6–3.3 SE) and the scout's.
* *Test:* `compare.py` per candidate (±0.3–0.4); the pool and selection rounds still decide adoption.
* *Cost:* days per candidate.
* *A pro would:* for control and speed. No visible accuracy gain is expected.

**6. Polymarket sharp-flow timing.**
* *Build:* rebuild positions (`polymarket_sharp_money/build_positions.py`, `prematch.py`); classify wallets only on matches settled before t; take each market's net "clear winner" stake 48–6 h out.
* *Test:* does it predict Polymarket's move to its close, and BetOnline's and Pinnacle's later moves? (Beyond the close it should not.) Then the CLV of posting with the flow, after fees and depth; SEs of about 0.1¢ per $1 on ~8,500 markets.
* *Cost:* two to four days, plus a live trade-tape poller.
* *A pro would:* yes; no sportsbook shows wallets. *Against:* winners earn +1.26¢ per $1 before fees, followers less, and taking costs about 2.5¢. Post instead.

**7. Challengers at Polymarket.**
* *Build:* `event_levels`' pooled no-price model, extended to 2025–26 Challengers and combined with Polymarket's price, cross-fitted within Sep 2025 – Jul 2026.
* *Test:* a time split, then sealed matches; ~5,000–6,500 matches give ±2–2.5 mLL by log loss, about 0.6–0.8 by coefficient.
* *Cost:* a few GPU fits.
* *A pro would:* yes, the softest liquid tennis market, with box scores since 2010. *Against:* thin early books ($9–66 within 1–2¢ at 12–24 h), integrity risk, one season of prices.

**8. Settlement-aware pricing and accounting.**
* *Build:* a table of venues' retirement and walkover rules (check BetOnline's and Pinnacle's own pages). At Polymarket a retirement pays the player who advances (rule text in `data/raw/public_dump/polymarket_catalog/events_extension.jsonl`), yet `bet_timing` voided retirements in its Polymarket returns. Add a retirement-risk model.
* *Test:* the Polymarket close's error against predicted retirement risk. Low power: retirements are rare at tour level (1.6% of matches in 1968–2010, `event_levels` § 9).
* *Cost:* a day.
* *A pro would:* fix the accounting at once; the edge is small on the main tour.

## 7. How this memo was made

* **Read:** CLAUDE.md, the brief, §§ 1–3 of the lead's process log; the reports of bet_timing, line_sharpening, odds_sources, market_anchoring, event_levels, polymarket_sharp_money, pinnacle_first, close_drift, training_window, meta_stack, feature_provenance, sharp_benchmark, betonline_lines and pair_strength; parts of tabpfn_thinking, serve_speed_tabpfn, feature_universe, `review_betting.md` and `05_best_practice.md`; the early-lines and market-anchoring notes.
* **Inspected, outcome-free:** the instance's `odds_input.json` and `odds_sources_counts.json`, the odds tables' columns, Polymarket's rule text, the first live forecast's header, `scheduled.py` and `pinnacle.py`.
* **Computed:** E[p(1−p)] of the close by season, from `in_odds_logit`. One command loaded the instance frame in full only to list its columns; no outcome value was printed or used. **Seasons whose outcomes were read: none.**
* **Not read:** the lead's new outputs in `data/studies/edge_anatomy/` and the other team memos, to stay independent.
* **Weak points:** the power rules assume a correctly sized linear signal and independent matches; § 5 applies both-tour benchmark gaps to a men's edge; several sources were read only at abstract level or through search summaries; practitioner claims are not evidence.
