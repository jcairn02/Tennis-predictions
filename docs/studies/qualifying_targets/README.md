# Qualifying matches: the model beats the closing price there too

22 October 2026 · For the owner · How it was done, step by step: [process_log.md](process_log.md) · The test as fixed
before any result was read: [preregistration.md](preregistration.md) (frozen 07:50, before the first fit)

**Status: a study, not a decision.** Nothing in the live model, the bet-day notebook or the shared tables changed.
The one shared file that grew is OddsTrader's table of every book's lines, which gained the qualifying matches' lines.
I checked that this moved no price the live model uses.

**Decided the same day by the owner:** the qualifying of the 250s and above is bet, with the live model
([decision](../../decisions/2026-10-22-qualifying-bets.md)). It is built into the bet-day cells A1–A5
([how](../master_pipeline/README.md#qualifying-of-the-250s-and-above-22-oct-2026)); the study's own code and results are
unchanged.

## In short

* **Yes: on qualifying matches the model's forecasts beat the bookmakers' closing price.**
  * The test was fixed in advance and passed.
  * The sample: 15,834 qualifying matches of 2020–2026 the model had never seen.
  * The model was more accurate than the closing price by 0.97 thousandths of a log-loss point per match, with a 95%
    range of 0.10 to 1.83. Higher means the model is more accurate; the whole range is above zero.
  * The comparison is fair to the market. The closing price got the same calibration step the model gets.
* **It would have made money at BetOnline's closing odds.**
  * The bet: every side the model rated as worth backing at those odds, margin included, 1 unit each.
  * **+2.5% per unit staked** over 7,009 bets, with a 95% range of +0.5% to +4.7%.
  * At Pinnacle's closing odds it was +1.0% (range −1.5% to +3.5%), so not proven there. Pinnacle charges a much higher
    margin on qualifying (4.4%, against 2.7% on main draws).
* **Today's model does this as it is.**
  * Retraining it with qualifying matches added made qualifying forecasts no better, and left main-draw forecasts
    unchanged.
  * A model trained on qualifying matches alone gained nothing.
  * So the edge comes from what the model learned on the main tour.
* **The edge is the model's, not the price's.**
  * Without the model, betting wherever BetOnline's price beat Pinnacle's fair price lost money (−2.7%).
  * Correcting the closing price for its known lean also fell short of the model.
* **Follow-up (22 Oct, 10:30): betting only the top 40% of the model's edges** returned more at both books (details
  [below](#follow-up-22-oct-1030-betting-only-the-top-40-of-edges)):
  * with the live model exactly as the bet-day notebook would run it (its calibration learned from main-draw
    matches): +8.3% at BetOnline's close and +9.8% at Pinnacle's;
  * with the calibration re-learned from qualifying matches instead (a test-only variant, never used live): +5.4% and
    +2.3%.
* **My recommendation:** put qualifying into the bet-day notebook using today's model, then run a small-stake live
  trial.
  * The notebook needs three changes first (below), about a day of work.
  * The realistic first targets are this season's last qualifying events, and the Australian Open qualifying in
    January.

## What I did

1. **Pinnacle's qualifying prices.**
   * Our odds site, OddsTrader, had them, as you guessed it might.
   * I downloaded every book's closing line for the 21,462 qualifying matches I could match to our records: 302 paced
     requests, all receipts kept.
   * Pinnacle's close is now held for 17,647 qualifying matches from 2018 to September 2025, where the site's Pinnacle
     history ends. BetOnline's is held for 19,137, to this month.
   * The download changed none of the 39,507 main-draw prices the live model reads (checked cell by cell).
2. **The model's inputs for 22,790 qualifying matches** (Slam, 1000, 500 and 250 qualifying, men and women,
   2018–2026).
   * They were built with the live model's own code on the tables it was built on.
   * As a check, the same build reproduced the live model's own inputs exactly, every one of them on all 67,531 of its
     matches.
3. **Three versions of the model**, each tested season by season on qualifying matches it had not seen, with training
   only on earlier seasons:
   * **today's model**: trained on main-draw matches only, as now;
   * **the pooled model**: today's training matches plus earlier qualifying matches. This was the declared main test;
   * **a qualifying-only model**: trained on earlier qualifying matches only.
4. **Each was scored** with the project's usual arithmetic: four seeds, and intervals that allow for matches being
   grouped in time.
   * **One difference from the live model, which I did not spell out at first (clarified 22 Oct):** the final
     calibration step was re-learned from past qualifying matches, each season from earlier seasons only. That step
     decides how far to trust the model's confidence, and adds the serve-speed nudge.
   * The live model learns those same numbers from main-draw matches.
   * Every qualifying figure from here to the follow-up uses this test-only calibration. The follow-up also shows the
     live model's own calibration, the one the bet-day notebook uses, and it did at least as well.
   * The five-pattern adjustment was left out, as in every model comparison.

## Question 1: how good are the closing prices on qualifying?

Matches of 2019–2025 that have both books' closing prices: 14,592 qualifying and 28,361 main draw.

| | Qualifying | Main draw |
|---|---|---|
| BetOnline's accuracy minus Pinnacle's (thousandths of a log-loss point; above 0 = Pinnacle more accurate) | **+0.62** (range +0.14 to +1.10): Pinnacle is more accurate | −0.54 (range −2.33 to +1.24): unresolved |
| Pinnacle's margin | **4.4%** | 2.7% |
| BetOnline's margin | **3.8%** | 3.6% |
| Calibration of Pinnacle's closing price (1 = right; above 1 = favourites win more often than priced) | **1.11 men, 1.13 women**: favourites underpriced (BetOnline's: 1.09, 1.12) | 1.02 men, 1.04 women (BetOnline's: 1.05, 1.06) |

So on qualifying:
* **Pinnacle is a little sharper than BetOnline.** On main draws the two can't be told apart.
* **Both closing prices underrate favourites.**
* **BetOnline is the cheaper book,** because Pinnacle raises its margin sharply on qualifying.

## Question 2: does the model beat the closing price?

The gain in accuracy over the closing price, both stages, 2020–2026. Higher is better; above 0 means the model beats
the price. "Better" means the whole 95% range is above 0; otherwise "unresolved", with the chance it is truly better.

| Version | Gain over the closing price | Reading |
|---|---|---|
| **The pooled model (the declared test)** | **+0.97** (range +0.10 to +1.83) | **better** (P 0.99) |
| Today's model | +1.09 (range +0.23 to +1.95) | better |
| Qualifying-only model | −0.01 (range −0.88 to +0.86) | unresolved |

The pooled model in more detail (these slices are flags, not separate verdicts):

| Slice | Gain | Reading |
|---|---|---|
| Men | +1.18 (+0.10 to +2.26) | better |
| Women | +0.76 (−0.38 to +1.90) | unresolved (P 0.91) |
| Slam qualifying | +1.50 (+0.16 to +2.85) | better |
| Tour qualifying (1000, 500, 250) | +0.68 (−0.47 to +1.83) | unresolved (P 0.88) |
| 2020–2024 | +0.69 (−0.48 to +1.86) | unresolved (P 0.88) |
| 2025–2026 | +1.62 (+0.65 to +2.60) | better |

* **Season by season,** the gain is positive in 6 of 7 seasons. The exception is 2021, at −0.72 with a range wide
  enough to mean nothing.
* **Today's model against the pooled one:** −0.12 (range −0.44 to +0.20), unresolved. Retraining with qualifying
  matches added nothing on qualifying.
* **Is it just bending the price?** I checked this after the main test, as an extra not fixed in advance.
  * The closing price was given a flexible, curved correction instead of the single calibration slope. It was no more
    accurate than the simple one.
  * Against that curved price, the model's gain was +1.36.
  * So the edge comes from the model's other inputs (players' form and match statistics), not from correcting the
    price's lean.

## Betting: what it would have earned

Every side the model rated as worth backing at the closing odds, margin included; 1 unit each; matches of 2020–2026.
Return per unit staked, with its 95% range.

| | At BetOnline's close | At Pinnacle's close |
|---|---|---|
| **The pooled model** | **+2.5%** (+0.5% to +4.7%), 7,009 bets | +1.0% (−1.5% to +3.5%), 4,685 bets |
| Today's model | +4.0% (+1.8% to +6.1%), 6,726 bets | +1.7% (−0.5% to +4.1%), 4,325 bets |
| Qualifying-only model | +0.3% (−1.3% to +2.1%) | −2.4% (−5.1% to +0.2%) |
| *No model: the corrected closing price alone* (extra) | *+2.0% (−0.5% to +4.4%)* | *−4.3% (−7.2% to −1.7%)* |
| *No model: back whatever beats Pinnacle's fair price* (extra) | *−2.7% (−8.6% to +2.8%)* | — |

* **Bets only where the model sees at least a 2% edge:** the pooled model returned +4.5% at BetOnline (+1.5% to
  +7.6%, 3,641 bets) and +3.5% at Pinnacle (−1.2% to +8.3%).
* **Most bets are on favourites:** 4,799 of the pooled model's 7,009 at BetOnline. That fits the closing prices'
  underrating of favourites.
* **These are returns on matches no choice had seen,** but not yet shrunk. The project's rule is that the edge used to
  size bets is shrunk first.
* **The bottom row answers your 16 Oct question** about Bar Biryukov at +186. Backing price gaps alone, without the
  model, lost money on average, so skipping those was right.

## Question 3: do the main-draw predictions stay as good?

Yes. The pooled model against today's on 32,027 main-draw matches of 2020–2026 scored **+0.03** (range −0.09 to +0.14;
higher means the pooled model is better). That is unresolved, and nowhere near the harm line. The breakdowns by tour
and period are all within ±0.1.

## Follow-up (22 Oct, 10:30): betting only the top 40% of edges

Your request: "how we'd do at pinnacle close and betonline close if we only bet on the best top 40% predicted edges for
the qualifying matches with the current best model (and offset)".

**What was tested.**
* **The model:** today's model with its serve-speed offset, calibrated two ways:
  * **the live model:** calibration and speed weight learned from main-draw matches, exactly as A1–A5 runs it;
  * **calibrated on qualifying (test only):** the same numbers re-learned from past qualifying matches, as in the main
    test above. Not used anywhere live.
* **The bets:** of the bets the model would make at each book's closing odds, the 40% with the highest expected profit.
* **The matches:** the same as above, 2020–2026.

Return per unit staked, with its 95% range:

| | BetOnline's close | Pinnacle's close |
|---|---|---|
| **Live model, top 40%** | **+8.3%** (+3.1% to +13.5%), 2,229 bets | **+9.8%** (+3.7% to +16.1%), 1,143 bets |
| Live model, top 40% with the cut fixed from earlier seasons (2021–2026) | +8.6% (+3.0% to +13.9%) | +10.9% (+4.6% to +17.8%) |
| Live model, all edges | +4.5% (+1.1% to +7.7%) | +4.7% (+0.7% to +8.7%) |
| Live model, the other 60% | +1.9% | +1.4% |
| **Calibrated on qualifying (test only), top 40%** | **+5.4%** (+1.7% to +8.8%), 2,691 bets | **+2.3%** (−1.6% to +6.2%), 1,730 bets: not proven |
| Calibrated on qualifying, top 40% with the cut fixed from earlier seasons (2021–2026) | +6.7% (+3.0% to +10.4%) | +2.2% (−1.8% to +6.4%) |
| Calibrated on qualifying, all edges | +4.0% (+1.8% to +6.1%) | +1.7% (−0.5% to +4.1%) |

* **Betting only the biggest edges pays more, with both calibrations at both books.** The top 40% earned more than the
  other 60% every time, so the model's bigger predicted edges are really bigger.
* **The cut works when fixed in advance.** Set from earlier seasons only, as it would have to be live, the top 40% did as
  well. In practice the cut is an expected profit of about **3% at BetOnline's odds** and **2% at Pinnacle's**.
* **The two calibrations forecast equally well:** the live model's accuracy minus the qualifying calibration's is +0.13
  (range −0.32 to +0.59).
* **Why the live model returns more:** its calibration pulls forecasts a little more toward 50/50.
  * That skips 2,100–2,300 marginal favourite bets, which only broke even.
  * It adds 650–1,150 underdog bets, whose results are very uncertain (+8.8% at Pinnacle, −2.2% at BetOnline).
  * So part of its lead may be luck.
* **The most recent seasons are weaker for betting.** In 2025–2026 the live model's top 40% returned +4.3% at
  BetOnline (−6.8% to +14.8%) and +9.8% at Pinnacle (−8.2% to +31.5%): both unresolved, on 490 and 207 bets.
* **This was not a fresh test.** It ran on the seasons the main test had already scored, with a rule chosen after that
  test. The live trial is what confirms it.

**My recommendation for the trial:**
* Use the live model exactly as A1–A5 runs it, with its own calibration: nothing new to maintain.
* Bet only the top 40% of edges: about 3% expected profit or more at BetOnline's odds.
* Plan on returns nearer the lower readings (about +5%) than +8%. The project's rule is to size stakes on an edge that
  has been shrunk.

## What it means, and what I recommend

* **Bet qualifying: yes, through a small-stake live trial first.**
  * Both conditions fixed in advance are met: the model beats the closing price, and the return at BetOnline's close
    is above zero.
  * A trial with small stakes is the honest next step. The return above is a backtest at closing prices. Live bets
    are placed earlier, at different prices.
* **Use today's model for it, unchanged.**
  * Adding qualifying matches to training bought nothing on qualifying, and changed nothing on the main draw.
  * So there is no reason to change the model you bet the main draw with.
  * The declared test was the pooled model. Picking today's model instead means the trial itself becomes its
    confirmation on new matches, which the plan required for such a switch.
* **Bet at BetOnline rather than Pinnacle.** Its margin on qualifying is lower, and that is where the backtest made
  money.
* **The bet-day notebook needs three changes before it can price qualifying:**
  1. **Let qualifying through.** Today it leaves qualifying out on purpose. The model needs qualifying matches entered
     as this study entered them (their own level and round codes).
  2. **Find the event and round.**
     * Round 1 of qualifying is an event's first match, and the notebook needs a played match before it can place
       an event. That, as well as the qualifying filter, is why Almaty's eight matches on 16 Oct could not run.
     * Pinnacle's listing says only "Qualifiers", not which round.
     * The notebook has to take the event from the listing or the calendar, and work out the round.
  3. **Box scores in time.**
     * Men's qualifying results reach us daily through Tennis My Life.
     * Tennis My Life has had no women's qualifying since June, so it reaches us through the weekly feed. A women's
       round 2 will then often miss round 1's match statistics, and the 1-point edge rule would apply.
* **I can make these changes next** (about a day), then run the trial on the first qualifying weekend after that.
  * Staking: the project has no decided staking rule. For the trial I'd suggest small fixed stakes and a review after
    a few hundred bets.

## Limits

* **Closing prices only.** Live bets are placed earlier, at whatever the price is then. Earlier qualifying prices are
  known to be less settled (the Polymarket studies), which could cut either way.
* **Women's 2026 qualifying** comes from the weekly feed, and only about half of it has match statistics.
* **Four seeds per fit,** as model comparisons always use; the live model averages sixteen.
* **The local model only.** The Thinking model, half of the live blend since 20 Oct, was not tested on qualifying.
* **The size of the edge is known only roughly.** About +1 thousandth of a log-loss point per match, with a range of
  about ±0.9.
* **Slices are not verdicts.** The stronger readings on men, Slam qualifying and recent seasons are flags, not proven
  differences.

## Files

| What | Where |
|---|---|
| The code (link, prices, inputs, speed, fits, scores, the two extra checks) | `src/eda/qualifying_targets/` |
| Tests | `test/qualifying_targets/` (6 offline tests) |
| Outputs | `data/studies/qualifying_targets/` (`scores.csv`, `betting.csv`, `market.json`, `harm.json`, `forecasts.parquet`; the fits in `local/`, not committed) |
| The follow-up (top 40% of edges) | `src/eda/qualifying_targets/top_edges.py` → `top_edges.csv`, `top_edges.json`; the two speed-stage versions compared: `explore_stage2_variants.py` → `exploratory_stage2_variants.json` |
| OddsTrader's raw responses and receipts | `data/raw/oddstrader/books/`, `data/raw/oddstrader/_receipts.jsonl` |
