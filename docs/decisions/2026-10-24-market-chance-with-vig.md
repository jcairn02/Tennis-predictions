# The bet sheet's market chance is the posted price's, its margin included

**Decided by the owner on 24 October 2026**, after Claude explained a row of the 21:47 sheet: Griekspoor at −121,
model 55.1%, market 53.2%, edge +1.9 points, expected profit +0.7%. The 53.2% was Pinnacle's price with its 2.8%
margin removed, the model's own input; the break-even at −121 is 54.75%. The owner's words, verbatim:

> what? 53.2% is what the model implies? thats the market chance no?

> This is a mistake . I dont care what the fair value is with vig removed, I just care about the price that the
> bookmaker posts. Market chance should be market chance INCLUDING VIG ON THE SIDE WE ARE TRYING TO BET

## Decision

* **"Market chance" on the bet sheet is 1 ÷ the decimal odds Pinnacle posts for the player shown** (the owner's
  words): the chance that player must win for a bet at that price to break even. −121 gives 54.75%.
* **The rest follows from it; these are Claude's choices, to keep the sheet consistent:**
  * **"Edge (pts)" is the model's chance minus that market chance.** A positive edge is then a positive expected
    profit, since expected profit = edge × the payout per unit staked. The 1-point data-gap bar reads off the column:
    a bet with a gap needs an edge above 1 point.
  * **The Matches tab shows both players' posted chances** (they add up to 100% plus the margin) and the same edge.
  * **"Edge gone if the market reaches" becomes "Zero edge if Pinnacle moves to":** the price Pinnacle would have to
    post for the model's side for its expected profit to be zero. The model's chance moves with Pinnacle's line, so it
    is re-read off the run's curve at each price, with Pinnacle's margin assumed to stay as it is. The old figure was a
    margin-free price, with margin-free odds Pinnacle never posts.
  * Notes and the "How to read" tab say it the same way.

The margin-free market chance was an agent's choice when the sheet was built on 13 Oct ([master pipeline process
log](../studies/master_pipeline/process_log.md), Part 2), not the owner's.

## What does not change

* **The model's odds input** stays Pinnacle's current line with the margin removed, as in training (the owner's rule
  of 9 Oct 2026, [decision](2026-10-09-pinnacle-first-odds-input.md)).
* **Every decision, expected profit, stake and block.** The record keeps its 69 columns, the margin-free price
  (`p_market_a`) and its edge (`edge_a`) among them, and gains four (`zero_ev_implied_a`/`_b` and the nearest of
  each).

## Checks

* **The 21:47 sheet of 24 Oct rebuilt from its run**, as of its own time, before and after the change (process log
  Part 15):
  * the rebuilt record before equals the saved one, every cell of 19 rows × 69 columns;
  * after, those 69 columns are unchanged;
  * on the sheet, decision, player, stake, US odds, lowest odds, the model's chances and the expected profit are
    unchanged on all 19 rows (10 BET, 9 PASS);
  * every market chance is 1 ÷ the odds, and every edge times the payout equals the expected profit to the record's
    rounding (6 × 10⁻⁵);
  * every BET has a positive edge and every PASS a zero or negative one.
* **The zero-edge prices** checked against each match's curve: at every reported price the expected profit, re-read
  off the curve, is within 0.01% of zero, and a search on a 20,001-point grid finds the same crossings (1 per match,
  3 for Fernandez).
* `test/master_pipeline/test_master_pipeline.py`: the three asserts that held the old meaning, rewritten; new ones for
  the zero-EV prices and their wording, and for the edge bar read off the sheet's edge.
* No replay proof: no input of the model changes.
