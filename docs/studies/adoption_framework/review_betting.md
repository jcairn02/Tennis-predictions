# Review: betting practice and model risk

9 October 2026 · An independent review by a subagent given [review_brief.md](review_brief.md), read-only access to the repository and web search · **Verbatim below.**
* **Checked by the main session:**
  * the edge against Pinnacle's close (`close_drift`, line 36);
  * the Pinnacle returns (`tabpfn_thinking58`, lines 35 and 41);
  * the bet-timing readings at 24 and 48 hours (`bet_timing`, line 25);
  * the matches needed for 80% power (`feature_provenance`, line 62).
* **Not re-checked:** the other repo figures it quotes, and its web sources.
* **Its finding 7** corrects the brief, which is kept as written.

---

**(1) Verdict**

The owner is right that a 95% interval is a publishing bar. Section 2's split, lenient on parts and strict on the number that sizes stakes, is the right instinct. But section 2 measures success at a price nobody bets (the books' average close) and ignores the repo's own money evidence. It also adopts on the sign of an effect (P ≥ 0.8), although its own logic says size against cost decides. It understates what leniency costs in betting: matching live inputs to training, fragile feeds, over-reaction that the bet rule stakes, and margin gearing. The first-order risk is whether the whole model has a bettable edge where the owner will bet; rules for parts are second-order.

**(2) Findings, ranked**

Tags: [Obs] repo number, [Src] source, [Inf] inference, [Sug] suggestion. mLL: + = model/candidate better unless stated.

1. **Wrong yardstick.**
   * [Obs] Edge 2020–24: +1.46 [+0.84, +2.08] over the books' average close; +1.16 [+0.52, +1.79] over Pinnacle (women +0.73, tie).
   * [Obs] Polymarket 2025–26: +0.10 (tie) at the 30-minute close; +2.11 (tie) fed the 24-hour price; +5.03 [+0.49, +9.56] at 48 h.
   * [Obs] Section 2 counts women's offset Elo at the close (−0.21 [−0.48, +0.07], + = offset better) as harm in an adopted change. It was adopted for the 24-hour price, where women read +1.11 [+0.04, +2.18].
   * [Inf] Caveat 3 (the prior "beyond the closing odds") holds only for betting at the close, the only place compare.py scores.

2. **Log loss is not money.**
   * [Inf] mLL over a margin-free price equals the log growth per match of full-Kelly betting at that price, with no margin and unlimited depth. +1.46 over 5,000 matches would be e^7.3 ≈ 1,500× a year. Margin, depth and staking decide the money.
   * [Obs] At Pinnacle (2022–Jan 2026, selection era) the bets claimed 2.9% and returned +1.50% [+0.38, +2.73] per unit staked. Women's returns are indistinguishable from 0.
   * [Inf] Net edge = gross − margin, so an overstated gross edge is multiplied by gross/net. Section 2's "twice the edge earns nothing" bites on the net edge, which is far easier to double. Gearing magnifies real small gains too.
   * [Obs] Challenger rows only leaned worse (−0.48 [−1.09, +0.14], + = with rows better), but realisation fell 0.91 → 0.63 (1 = right-sized, lower = over-reacting). [Inf] Such a model stakes most on its errors.

3. **No fast feedback at the close.**
   * [Obs] With the close as an input, bets at the close have closing-line value (CLV, the expected return if the close is true) of minus the costs: BetOnline −3.5%, Polymarket −1.8% per $1.
   * [Inf] Only outcomes can validate it: [Obs] ~7,700 matches for 80% power at +1.3; [Inf] ~13,000 at 1.0.
   * [Obs] Early bets get CLV: Polymarket +0.0% at 24 h, +1.3% at 48 h, fees in.
   * [Obs] The price's move toward the model tests a change without outcomes: +0.23 [+0.04, +0.43] for the offset-Elo swap (+ = toward the new model).
   * Section 2 uses neither.

4. **Parts are the smallest lever.** [Obs] Part increments at the close are mostly ±0.1 mLL. Larger levers:
   * the yardstick: 0.3 (Pinnacle vs average);
   * Polymarket timing: S − A ≈ +2 at 24–48 h (+ = betting early gains; one season);
   * an odds input built like training: +0.34 to +0.42 (+ = fed the books' average rather than BetOnline's line);
   * margins: Pinnacle 2.79%, BetOnline 3.75%, the better of the two 2.19%;
   * Polymarket's taker fee: 2.5¢ per $1 at evens; makers get rebates;
   * depth: ~$350 within 1¢ at 1000s 24–48 h out; $70 at 250s 12–24 h out.

   The whole edge is unproven outside its era. 2015–19 read +0.18 [−0.28, +0.64] against +1.46 in 2020–24, and the inputs were chosen with 2020+ in view. The 2025–26 reading is forecast to overstate the edge by ≈0.35.

5. **The rule contradicts its own logic.**
   * [Inf] Under its flat prior, a pure null clears P > 0.8 one time in five.
   * Its "fishing" scenario admits 3.2 nulls among 4.4 adoptions, and the survivors' sizes are inflated ([Src] Gelman & Carlin).
   * The simulation assumes effects add up. [Obs] Yet with offset Elo in, the surface profile added nothing detectable.
   * It guesses the cost of a dud, which shuffled twins could measure.
   * It treats tests on reused 2020–24 seasons as independent ([Src] Dwork et al.), and it ignores live costs.
   * [Src] Harvey & Liu: haircut marginal results heavily and strong ones lightly.
   * [Obs] The repo already has the tool: stage 2's b̃ = b·τ²/(τ²+SE²).

6. **"Cheap and reversible" is mostly "cheap and unobservable".**
   * [Obs] Inputs must be reproduced exactly live.
   * [Obs] Publication lag is not the finish clock: the speed adjustment keeps 66–92% of its gain at today's latency.
   * [Obs] Feeds vanish (Sackmann's repositories now return 404), and Polymarket's fee changed three times in 2026.
   * [Inf] Leaks look like gains, and each choice made on the same seasons inflates the edge that sizes stakes.
   * [Inf] Leniency suits only parts that need no new feed, fall back to the reference, pass the gates, add no over-reaction and earn no edge credit.

7. **A misstatement in the brief.** [Obs] "$0.00 per 100 matches" was early minus close. Both moments returned ~+4% per $1 in 2026, against an expected −1.5% with Polymarket's close as the truth, and log loss tied (+0.21). That is probable luck.

Evidence, under C:\Users\zerom\Documents\Tennis-predictions\docs: studies\{close_drift,bet_timing,tabpfn_thinking58,feature_provenance,event_levels,line_sharpening,polymarket_sharp_money,betonline_lines}\README.md; decisions\2026-10-06-offset-elo.md.

**(3) The provenance-and-cost hypothesis**

The hypothesis is right in shape. Provenance works through four channels, not through how plausible an idea sounds:
1. **The prior of an effect beyond the price you bet into.** Domain ideas predict outcomes, and the close usually holds them already; thin early books may not.
2. **Search breadth.** An idea found in the 2020–24 outcomes cannot be confirmed on them. It needs data outside its discovery, or a selection-corrected estimate ([Src] deflated Sharpe, PBO).
3. **Mechanism and counterparty: who is on the other side?**
   * Thin early Polymarket books absorbing public information late is a credible story ([Obs] the price moves 29–45% toward the model).
   * [Inf] Beating the Pinnacle close needs information the syndicates lack.
   * [Obs] The competition: 4.4% of Polymarket accounts beat the close, by 1.3¢ per $1 before fees.
4. **Bet-time existence:** will the input exist before the bet, in the same form?

Bars by class [Sug]:
* **A data fix, or more of the same data:** adopt if harmless and the live pipeline matches; claim no edge.
* **A feature with a mechanism:** adopt if its shrunk gain beats its cost at the target.
* **Mined, or the best of many:** only on data outside its discovery.

Cost: rank errors by reversibility and observability.
* **Cheap and reversible:** a part that needs no new feed and falls back to the reference.
* **Cheap but never detected:** a dud.
* **Expensive and irreversible:**
  * over-staking on an inflated net edge;
  * spent sealed matches;
  * soft-book limits ([Src] Kaunitz et al. were restricted during five months of real-money betting);
  * a feed that vanishes;
  * a leak's phantom edge.
* **Missing a real edge:** cheap and recoverable if it is small; a large one is detectable.

**(4) Framework elements [Sug]**

1. **Name the target first:** venue, hour, price fed, population bet and depth. Also score at the Pinnacle close. If the target is Polymarket early, its only history is 2025–26, already read, so sealed and live matches are the clean evidence.
2. **Report, with directions labelled:**
   * mLL at the target;
   * Δ realisation;
   * return and CLV on the bets, after the venue's margin;
   * the move toward the model (early hours);
   * dollars a year at achievable depth;
   * new dependencies and their lag.
3. **Decide on shrunk gain against cost:** gain × τ²/(τ²+SE²), with τ set by provenance class and small at the close. The outcomes are adopt, adopt on a logged lean, shadow, or reject. Ties that cost nothing go to the simpler member, spending no looks.
4. **Hard gates, whatever P says:** the leak probe, the shuffled twin, publication lag, matching live inputs, a fallback to the reference, and no added over-reaction (realisation).
5. **Keep parts apart from sizing.** Stakes come from a whole-model edge measured on untouched or live matches, shrunk ([Src] Baker & McHale), at fractional Kelly.
6. **The ladder:**
   * backtest;
   * selection-corrected estimate;
   * sealed matches, one look;
   * paper bets at the venue (price, depth, close, result);
   * small real stakes, to learn fills, fees, slippage, limits and the adverse selection of posted orders;
   * scale with evidence.

   CLV gates early bets ([Src] Buchdahl); bets at the close wait on outcomes.
7. **Shop practice, scaled to one person [Inf]:** run a challenger in shadow on the same live matches and promote it on paired evidence. Ramp stakes with capacity, and set kill switches in advance. Splitting real stakes between versions teaches little except about execution.
8. **Triggers:**
   * a stale or out-of-range input means no bet;
   * drift in the model's disagreement with the market, or in the bet count;
   * rolling CLV below 0;
   * walk-forward realisation below ~0.8;
   * a drawdown beyond what the shrunk edge allows.
9. **Budget the looks,** and log every read of sealed data.

**(5) Sources (accessed 2026-10-09)**

1. Bailey, Borwein, López de Prado & Zhu, Probability of Backtest Overfitting, https://papers.ssrn.com/abstract=2326253: the chance that the in-sample best underperforms out of sample.
2. Bailey & López de Prado, Deflated Sharpe Ratio, https://papers.ssrn.com/abstract=2460551: deflates a best-of-N result for the number of trials and non-normality.
3. Harvey & Liu, Backtesting (2015), https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF: haircuts are nonlinear, heaviest on marginal results.
4. Baker & McHale (2013), https://ideas.repec.org/a/inm/ordeca/v10y2013i3p189-199.html: shrink Kelly stakes when the probability is estimated; tested on tennis data.
5. Buchdahl (Pinnacle, 2019), https://www.pinnacle.com/betting-resources/en/betting-strategy/using-the-closing-line-to-test-your-skill-in-betting/7e6jwjm5ykejuwkq: beating an efficient close by x% implies ~x% long-run return. Read from a search extract; the page itself did not load.
6. Kaunitz, Zhong & Kreiner (2017), https://arxiv.org/abs/1710.02824: a backtest, a simulation and five real-money months, then discrimination against the winners.
7. Gelman & Carlin (2014), https://sites.stat.columbia.edu/gelman/research/published/PPS551642_REV2.pdf: at low power, results that pass a bar exaggerate the effect and can have the wrong sign.
8. Dwork et al., Reusable Holdout (2015), https://cis.upenn.edu/~aaroth/reusable.html: reusing a holdout adaptively invalidates it.
