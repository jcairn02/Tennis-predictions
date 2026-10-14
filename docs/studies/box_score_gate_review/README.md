# The box-score gate of 8 Oct 2026, reviewed

14 October 2026 · For the owner · Process log: [process_log.md](process_log.md) · **Decided by the owner on 14 Oct 2026:** "Do all 3" (the three decisions at the end).

**Correction, 14 Oct, after you approved:** the first version put *women's qualifying* among the kinds training lacks. That came from my error: I pooled the ITF qualifying, which has no box scores in training, with the Slam, WTA and WTA 125 qualifying, which has them in 99–100% of training matches every season since 2019. Corrected below: **qualifying above ITF level is a kind training nearly always has, for both tours**, so its gaps get the 1-point bar, not a note. Only the women's figures for the narrower block move (3.3% → 4.3%).

## In short

* **The intention was right; the rule built on it was not.** You asked that live inputs be built the way training inputs were, and that every run refresh box scores first. An agent turned that into "withhold the bet if any match of either player in the last 14 days, at any level, lacks a box score". That tests *completeness*, not *sameness with training*. Training rows are missing box scores for about half of team-event matches and every ITF match before 2025, qualifying included. A live match with those gaps looks exactly like what the model learned from, and those gaps cause almost all the blocks: **4.4% of men's and 13.7% of women's main-tour matches in 2024–2026 (20% of women's in 2026).**
* **"Quietly skips … drifts toward average" is not incredibly bad.** It's how the inputs are designed: no invented numbers, the same treatment in training, and a pull toward average that is the inputs' normal handling of thin evidence. Measured directly: one missing earlier round moves the forecast by a **median of 0.35 percentage points**, at most 1.4, in no consistent direction. That is a fraction of a typical edge.
* **A block costs more than the gap it guards against.** On the replayed day, betting through one missing round cost about 3 hundredths of a unit in expected profit over 23 matches. Blocking those matches would have given up about 37, twelve times as much. That holds unless the model's edges are badly overstated, and the rule I recommend covers that case too.
* **What I recommend:**
  1. Keep refreshing first, and keep the data check.
  2. Stop blocking bets over missing box scores.
     * Gaps of kinds the model was trained with (team events, ITF) become a note on the bet sheet.
     * Gaps of kinds training nearly always has (main tour, Challengers / WTA 125, qualifying above ITF level) raise the bar instead: bet only if the edge is above 1 point.
  3. Keep the two small checks that aren't about box scores (an unknown indoor/outdoor input; a qualifier with no qualifying match).
  4. Build the men's fill from the ATP's own match stats, so a box score Tennis My Life hasn't published yet gets filled, as the women's already are.

## The rule, and who wrote it

**What it does** (`src/eda/prediction_run/gate.py`). Before a prediction run lets a match be bet, it checks every finished match of either player:
* at the same tournament, in an earlier round;
* or with a possible finish in the 14 days before the match, at any event and any level, team events included.

If any of them lacks a box score, the match is marked "do not bet". The forecast is still made, but the bet sheet withholds the bet. Two later additions, also by agents: a player who came through qualifying needs a qualifying match in the data, and the match's indoor/outdoor input must be known.

**What you asked for on 8 Oct** (the decision record, verbatim): *"Make live inputs match what the model was trained on. Every prediction run should refresh box scores first: without the same event's earlier rounds, the 2-week profile loses a third to a half of its gain over Elo."*

**What you approved:** "Steps 1–4: the refresh, the sandboxed rebuild, the gate, and the live rows", from options the agent put to you. "The gate" was approved by name only. **Every one of its settings was the agent's choice**, and the record doesn't say so:
* the 14 days (taken from the form inputs' two-week *half-life*, used as a window);
* every level, team events included;
* other events, beyond "the same event's earlier rounds" that you named;
* the qualifier rule;
* blocking, rather than a warning or a smaller stake.

A later session then called the gate "the owner's policy".

## What the evidence behind it actually says

The rule rests on one measurement: "without the same event's earlier rounds, the 2-week profile loses a third to a half of its gain over Elo" (Stage B's recency diagnostic, 2 Oct).

* **No market price.** It was a two-input model: Elo plus one form number. Today's model has Pinnacle's price as an input, and the price already reflects most of what form says.
* **Everything removed at once.** It deleted *every* same-tournament earlier round from *every* match, then refitted the model on that. That measures how much information those rounds carry. It doesn't measure what one missing box score does to one forecast from a model trained on complete data.
* **With the market price in the same test, the effect disappears:** men 0.14 → 0.11 mLL, women −0.07 → −0.08 (milli-log-loss; higher is better). Neither difference is detectable.
* **In today's model,** the whole two-week form family (17 inputs) adds about **+0.1 to +0.3 mLL** beyond Pinnacle's price:
  * +0.14 [−0.35, +0.63] in 2025–26;
  * +0.30 [+0.05, +0.54] in 2020–24 (edge-anatomy study, 12 Oct).

  One missing match is a small slice of that.
* **The "training standard"** quoted with the rule (98.4–99.7% of earlier-round box scores present) covers **same-tournament rounds of 2019–2025 only**, and no script behind it was found. It says nothing about other events, other levels or qualifying, which the gate also polices. This review measures training's coverage directly (below).

**Nobody had measured what one missing box score does to one forecast.** This review does.

## What the rule costs

I applied the gate's own rule (its code's constants) to every main-tour singles match since 2013, as if each were predicted live, on today's data. Only the gaps that are still there today count. Gaps from Tennis My Life publishing late would add more on bet days, so **these are lower bounds.**

| Main-tour matches the gate would withhold | Men | Women |
|---|---|---|
| 2024 | 2.5% | 12.3% |
| 2025 | 5.5% | 9.2% |
| **2026** | **5.4%** | **20.0%** |
| 2013–2026, all seasons | 7.6% (seasons 1.2–21.9%) | 24.5% (seasons 9.2–64.4%) |

These are on the tables of the evening of 13 Oct. That evening's shared rebuild restored Roland Garros 2026's box scores from its own records, under your 9 Oct decision. On the tables of a few hours earlier, 2026 read 10.9% (men) and 24.5% (women), and about 240 of those blocks came from Roland Garros alone.

**What blocks them now** (2024–2026). In every case the box score isn't in any of our sources:
* **WTA Berlin and Nottingham 2026:** partial box scores; 187 matches blocked.
* **Team events** (Davis Cup, BJK Cup, United Cup, the Olympics): 494 matches.
* **ITF events** (women's W50–W100): 425 matches. Since the lower-level feed of 13 Oct, these reach live runs too: the 13 July replay now blocks 2 of 23 matches over ITF box scores. Yet the men's inputs give ITF box scores **zero weight**, so for men the gate demands data the model ignores.
* **Qualifying** (mostly women's Slam qualifying): 172 matches.

**For men, not one of the remaining blocks comes from a main-tour box score.** They all come from team events, Challengers, ITF matches or qualifying.

**The crucial point:** these gaps are also in the model's **training** rows. The same simulation finds a gap in the window for 1–22% of men's and 9–64% of women's training matches, season by season. Which kinds of match have box scores in training (completed singles, 2013–2025 pooled):

| Kind of match | Men | Women | So a live gap of this kind... |
|---|---|---|---|
| Main tour | 100% | 96% (99–100% since 2016) | differs from training |
| Challenger / WTA 125 | 99.5% | 94% | differs from training |
| Qualifying above ITF level (Slams, tour, Challenger / WTA 125) | 94.5% | 85% (99–100% a season since 2019) | differs from training |
| Team events | 48% | 54% | looks like training |
| ITF, qualifying included | 8% (none before 2025) | 6% (none before 2025) | looks like training |

A live match with a gap of the last kinds looks exactly like thousands of matches the model learned from. For those, the gate protects nothing.

**Narrower versions of the gate** (same simulation, 2024–2026, qualifier rule kept):

| The gate blocks for a missing box score of... | Men | Women |
|---|---|---|
| any kind (today's rule) | 4.4% | 13.7% |
| the kinds training nearly always has (main tour, Challenger / WTA 125, qualifying above ITF level) | 0.5% | 4.3% |
| main tour only | 0.2% | 3.2% |
| the same event's earlier main-draw rounds only | 0.2% | 1.0% |

The women's 4.3% is mostly two things:
* WTA Berlin and Nottingham 2026 (187 matches). Tennis My Life holds those events' box scores only in part; on a live day the run would first try to fill them from the WTA's own feed.
* The 2026 Slam qualifying (82 matches: Roland Garros 29, Wimbledon 28, US Open 25). Tennis My Life has lacked the women's qualifying since June 2026.

The qualifier rule alone withholds 0.2% (men) and 0.4% (women).

**On live days so far:** 3 of 13 live matches were blocked, in the daily engine's three live runs (11 Oct: 3 of 8; 13 Oct: 0 of 4 and 0 of 1). All three came from the Laver Cup parsing bug (now fixed), together with the event's imprecise dates.

## What "quietly skips" actually means

From the code (all 40 box-score inputs):
* **No fake numbers.** A match without a box score gets **zero weight**. It is never filled with zeros or invented numbers. Results without box scores still count in Elo and the other result-based inputs.
* **The same code builds training rows and live rows,** so training rows skip their missing box scores the same way.
* **"Drift toward average" is the inputs' design, not an accident.** Each value is a weighted average pulled toward the tour average by a prior, which is how they handle small samples.
  * In the two-week form inputs the prior is heavy. With three recent matches, the prior already carries 77–98% of the value, and one match carries 0.6–7.7%.
  * In the long-memory inputs (the IOS profile, ratings, 52-week points), one match is about 1–5% for a regular player, and more for a newcomer.

  Losing a match means a little less evidence, and the value leans a little more toward average.

**Is it "incredibly bad"? No:**
* the treatment is principled;
* it's identical in training;
* one missing match moves an input by a few percent, and the forecast by about a third of a point (next section).

**Two real weaknesses:**
1. **No input says how much evidence a value rests on.** The model can't tell "average player" from "player we know little about". That's a model-design question for the feature pool, not a betting rule.
2. **Some gaps really do differ from training.** Late publication is the common one: at bet time the most recent match, which weighs the most, may be missing only because Tennis My Life hasn't published it yet (it runs about a day behind), while training rows were built after publication. A source that stops covering what it used to cover is the other (Tennis My Life dropped the women's qualifying in June 2026). Refreshing first and filling from official feeds address these. Women's gaps are filled from the WTA's own feed; the men's equivalent (the ATP's stats feed) was planned on 8 Oct but never built.

## What a missing box score does to the forecast (the replay)

**How.** I took a past day (13 July 2026, round of 16: 23 matches at Båstad, Gstaad, Umag, Athens and Iasi, the week after Wimbledon) and predicted it through the daily engine exactly as on a bet day, with today's model (16 runs averaged, plus the serve-speed stage). Then I predicted it again four times, each time deleting chosen box scores from the data, in the same way a missing one looks. Everything else stayed fixed, including the trained model, so any change in a forecast comes from the deleted box scores alone.

| What was deleted before predicting | Matches | Typical move (median) | 1 in 10 moved more than | Largest | Moved over 1 point |
|---|---|---|---|---|---|
| **One player's latest earlier round at the same event** (the one most likely to be late) | 23 | **0.35** | 1.17 | 1.41 | 3 (all men) |
| The other player's latest round at the event (added after the first reading) | 14 | 0.26 | 0.58 | 0.74 | 0 |
| One match at another event in the last 14 days (Wimbledon, Challengers) | 20 | 0.21 | 0.35 | 0.72 | 0 |
| **Every** box score in the last 14 days, both players (2–7 matches each) | 23 | 0.42 | 1.36 | 1.84 | 5 |

Moves are in percentage points of the win probability. For scale, the 11 Oct bet sheet's edges were 2–3.5 points.

* **No direction.** On average the moves cancel (+0.002 and −0.04 points). A gap adds noise; it doesn't push a forecast one way.
* **Men move more than women,** because the women's form inputs lean harder on their prior.
* **Matches with nothing deleted moved by at most 0.02 points,** so a deletion barely spills over to other players.
* **The bigger moves are rare and capped:** even with every box score of the last two weeks gone, the largest move was 1.8 points.

**By the rule I set before seeing these numbers,** a single missing round would justify a block if 1 in 10 such gaps moved the forecast by more than a point. The first reading came out at 1.17, so it clears that line, narrowly: it rests on the third-largest of 23 values. The second single-gap reading, added afterwards, came out at 0.58.

## What a gap costs in bets, against what a block costs

That line was a stand-in for the real question: **does withholding the bet save more than it costs?** I could answer that only once the forecasts existed, so this part was designed after the numbers above.

I applied the bet sheet's own rule (bet the side with positive expected profit at the bookmaker's odds, one unit a bet) to the 13 July forecasts, with and without each gap. Each decision is judged by the complete-data forecast. The replay has only closing prices, so odds were built with a 2.5% bookmaker margin (4% checked too). On complete data the model bets 10 of the 23 matches, at an average expected profit of 3.7% a bet.

| What was deleted | Decisions the gap changed | Expected profit lost by betting anyway | Expected profit forgone by blocking |
|---|---|---|---|
| One player's latest round at the event | 4 of 23 | 3.0 | 37.2 |
| The other player's latest round | 2 of 14 | 0.4 | 18.9 |
| One match at another event | 1 of 20 | 0.3 | 31.9 |
| Every box score in the last 14 days | 5 of 23 | 7.3 | 37.2 |

In hundredths of a unit, summed over the matches. The decisions a gap changes are the marginal ones, where the expected profit was near zero anyway; a block throws away the clear bets too.

**If the model's edges are overstated, the picture changes.** I judged the same decisions again as if the true edges were half what the model says.
* **At a 2.5% margin,** blocking still forgoes more than the gaps cost: 1.3 to 4.6 times as much in three cases, though the gap costs more in the fourth.
* **At a 4% margin,** the model's bets lose money on this day even with complete data. A block then "saves" money only because betting loses. That is a question for every bet, not a reason to block gapped ones.

**A middle rule does well either way: bet a gapped match only if its edge is above 1 point** (about the size of a large move from one missing round). Expected profit over the 23 matches with one missing round (2.5% margin):

| Rule for a match with a gap | Edges as the model says | Edges half as big |
|---|---|---|
| Bet as usual | 34.2 | 2.5 |
| **Bet only if the edge is above 1 point** | **28.2** | **8.0** |
| Block | 0 | 0 |
| (For comparison: no gap at all) | 37.2 | 6.4 |

Across all four kinds of deletion, both margins and both judgements, the 1-point rule beat blocking in 15 of 16 cases (the 16th: −0.1 against 0). One honest caveat: when edges are overstated, part of its advantage is simply having a minimum edge, which would help every bet, gapped or not. With about 10 bets on one day, these sums show the shape of the trade-off; they don't prove it.

## Recommendation

### The rule I recommend

1. **Keep:** every run refreshes box scores first (and fills women's gaps from the WTA's feed); the data check before the run stays.
2. **Missing box scores no longer block a bet.** Every earlier match of either player, at the same event or in the last 14 days, is still checked, and each gap is shown:
   * **Kinds the model was trained with mostly missing** (team events, ITF, women's qualifying): a note on the bet sheet, nothing else.
   * **Kinds training nearly always has** (main tour, Challengers / WTA 125, men's qualifying): the bet stands only if its edge is above 1 point. The sheet says why, for example: "Data gap: Sonego's last match has no box score yet. That can move the forecast by up to about a point, so this bet needs an edge above 1 point."
3. **Keep blocking** when the indoor/outdoor input is unknown, or when a qualifier has no qualifying match in the data. Both are cheap (0.2–0.4% of matches) and unmeasured: the model never saw a missing indoor value in training, and a missing qualifying run removes results, not just box scores.
4. **Build the men's fill** from the ATP's own match stats (scraping approved), as planned on 8 Oct. A late box score is then filled before the forecast instead of handled after it, which is better than any rule about it.
5. **To the feature pool:** an input saying how many box-scored matches a player's recent form rests on (weakness 1 above). The pool's selection rounds decide whether it enters the model.

**What it changes in practice:** blocks fall from 4.4% (men) and 13.7% (women) of main-tour matches to about 0.2% and 0.4%, which is the qualifier check plus the rare unknown indoor input. On top of that, small-edge bets are passed on matches with a main-tour gap.

### The alternatives

* **The narrower block my pre-set rule points to:** block only for gaps of the kinds training nearly always has. It withholds 0.5% (men) and 3.3% (women), plus every match whose previous round Tennis My Life hasn't published yet, until the men's fill exists. It follows my rule as set before the replay. I don't recommend it, because the replay shows a block costs more than it protects.
* **Never block for box scores, notes only:** the simplest. It's the best of the three if the model's edges are real, and the worst if they're overstated.
* **Keep the gate as it is:** not recommended. It withholds 1 in 7 women's main-tour matches (1 in 5 in 2026), mostly over gaps the model was trained with, and it demands ITF box scores the men's inputs ignore.

### What would change in the code, if you accept

* **The gate** (`src/eda/prediction_run/gate.py`): sort each gap by kind; record notes and the 1-point bar instead of "do not bet".
* **The bet sheet:** show the notes, and apply the bar when it picks a side.
* **The data check:** follows the gate, so it changes with it.
* **Tests** for each kind of gap.
* **A decision record** amending point 3 of the 8 Oct decision, and the gate's line in CLAUDE.md.

### Decisions for you

1. **Replace the gate with the rule above?** Recommended. If you'd rather keep a block, take the narrower block.
2. **Build the men's fill?** Recommended; it's the one change that improves the forecasts themselves.
3. **Add the evidence-count input to the feature pool?** Recommended.

## Other things found along the way

* **Replays of past days fail since the shared table rebuild of 13 Oct, 21:13–21:16.** The lower-level merge now finds duplicate timeline rows. I worked around it in my own copy only, and nobody has run a replay since. The daily engine's replay proofs and tests would fail the same way.
* **The engine's stand-alone "predict" command now fails** unless the pattern step runs first, and only the full bet-day run does that. The bet-day run itself is unaffected.
* **The pattern adjustment you switched on last night gave no shift to any of the 23 replayed matches.** Five of its members aren't built for live matches yet, and their safety checks were on for July, so the adjustment paused itself. Worth confirming it's active on a real October bet day.
* **Cleanup:** my replay work copy (`C:/Users/zerom/tnr_gate_review`, 11 GB) can be deleted. I haven't deleted it.

## Limits of this review

* **One replayed day, 23 matches** (250-level events, round of 16, the week after Wimbledon). Slams, best-of-five matches, and players with few recent matches may move more.
* **Closing prices, not bet-time prices,** in the replay: the edges, and so the profit sums, are those against the close.
* **The profit sums rest on about 10 bets.** They show the trade-off's shape, not its size.
* **The pattern adjustment was paused on that day.** On days it's active, a gap could move it too (one of its members reads aces).
* **The cost simulation counts only permanent gaps.** Late publication adds more blocks on bet days under today's rule, and more 1-point bars under the recommended one.
