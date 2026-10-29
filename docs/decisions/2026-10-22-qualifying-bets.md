# The qualifying of the 250s and above is bet, with the live model

**Decided by the owner on 22 October 2026**, after the qualifying-targets study ([report](../studies/qualifying_targets/README.md)). The owner's words:

> "We've done enough tests to conclude we should be betting the qualifying rounds of 250+ tournaments.
> Build the acceptance of this into A1-A5 so we can predict on them using the live model"

Carried out by Claude the same day ([master pipeline process log, Part 8](../studies/master_pipeline/process_log.md)).

## What is decided

* **The population.** Matches of the qualifying draws of the ATP and WTA 250s, 500s and 1000s and of the four Slams, both
  tours, are predicted and bet on bet days like main-draw matches.
  * In the project's tables these are Stage 0's levels T250, T500, T1000 and GS with `qualifying`; Stage 4 calls them TQ
    and GSQ.
  * It is the study's population.
  * The qualifying of Challengers, WTA 125s and ITF events stays out.
* **The model: the live model, unchanged.**
  * The active instance's fits are still trained on main draws only.
  * Stage 2's calibration slope and serve-speed term still come from main-draw matches.
  * The study's qualifying-calibrated stage 2 is not used (it existed only in the study's scoring code), and nothing is
    retrained.
* **A qualifying match's inputs are built as the study built them.** The model has never seen these codes in training,
  as in the study:
  * its level is coded TQ 6 / GSQ 7 (the model's own codes are GS 0 to T250 4);
  * its round order is Q1 1, Q2 2, Q3 3;
  * best of 3, or 5 where the data records 5 for a men's Slam qualifying match;
  * the indoor rule as for every match.

## The evidence

From the study's report, on 2020–2026 qualifying matches the model never saw:
* **Accuracy:** the model beat the calibrated closing price (+1.09 thousandths of log loss a match, 95% range +0.23 to
  +1.95).
* **Return at the closing prices:** the live model, with its own main-draw calibration, as A1–A5 runs it:

| Bets | BetOnline's close | Pinnacle's close |
|---|---|---|
| Every +EV side | +4.5% (5,572 bets) | +4.7% (2,857 bets) |
| The top 40% of edges | +8.3% | +9.8% |

* **What the backtest is not:** it priced bets at the close, not at the earlier prices bets are placed at.
* **What it did not test**, though both are part of the live model's daily run:
  * the five-pattern adjustment;
  * the TabPFN-3.5-Thinking ensemble.

  "Using the live model" applies both to qualifying as to the main draw. The bet sheet shows the chance without the
  patterns beside the one used, as it does for every match.
* **The five-pattern adjustment, tested later the same day** (the owner: "Test this"; the study's follow-up 2, process
  log Part 3): computed exactly as the daily run computes it (equal to the run's own on 16 replayed matches), on the
  same 15,834 matches. With it the live model was +0.28 thousandths better (range −0.07 to +0.63: unresolved). The harm
  check fixed beforehand did not fail, so **it stays on for qualifying**. Returns at the close were higher with it:
  BetOnline +5.8% on every +EV side (+4.5% without), Pinnacle +5.3% (+4.7%).

## How it is carried out (22 Oct 2026)

The bet-day cells A1–A5 run qualifying matches like main-draw ones ([how](../studies/master_pipeline/README.md#qualifying-of-the-250s-and-above-22-oct-2026); process log Part 8).
* **A2 places each match** (`src/pipeline/qualifying.py`). Pinnacle's listing gives neither the round nor, before round 1 is played, any event data:
  * the event comes from Tennis My Life's rows of the edition, else it is built from its previous edition;
  * the round comes from TennisLive's results of the event, checked against Tennis My Life's;
  * the main draw's start is estimated. Stage 0 dates an event by its main draw's first date, and before the main draw is played it would otherwise take the first qualifying day, which moved 19 of the 57 inputs.
* **The inputs** are the qualifying study's (`dp_context`), and a qualifying match is priced from the run's price alone (tennis-data prices no qualifying).
* **Blocked:** a round 2 or 3 whose player's round before is not in the data. A man's waits for Tennis My Life (hours); a woman's for the weekly lower-level feed, so women's rounds 2 and 3 cannot be bet on the day.
* **Checked:**
  * The engine's inputs for 956 past qualifying matches equal the study's bit for bit (both tours, Slams included).
  * A replay of 17 and 18 Oct's rounds 1 and 2 at Almaty and Brussels, built as live rows, reproduces all 57 inputs bit for bit (24 matches), given the main draw's start.
  * The start estimate is exact for 81% of 2025–26 qualifying matches, within a day for 97%, within 2 days for all.
  * A round 1's event built from its previous edition matches what Tennis My Life later published, on every field the model reads, for 99–100% of 778 matches.

## Stakes: the same as the main draw's

**Decided by the owner later on 22 October 2026**, to the recommendation of a smaller stake for a first stretch of
qualifying bets: "Stakes should be the same as main." A qualifying bet is staked by whatever rule the bet sheet applies
to a main-draw bet (today the owner's research rule of 8 Oct, `STAKE_RULE = "owner_8oct"`). That is what the sheet
already did; nothing in the code changed.

## Not decided here

* A staking rule as such: the research rule of 8 Oct stays labelled as research, for qualifying and main-draw bets alike.
* Betting only the top 40% of edges.
* Thinking on qualifying as a measured part: it earns no edge credit there until tested. The five-pattern adjustment
  was tested (above): no harm, its gain unresolved, so it earns none either.
