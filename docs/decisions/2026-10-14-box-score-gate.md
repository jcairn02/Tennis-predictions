# A missing box score no longer blocks a bet; a men's fill from the ATP's own statistics; the evidence input in the pool

**Decided by the owner on 14 October 2026.** The [box-score gate review](../studies/box_score_gate_review/README.md)
([process log](../studies/box_score_gate_review/process_log.md)) found that the gate of 8 Oct, point 3 of
[the prediction-run decision](2026-10-08-prediction-run-box-scores.md), was designed by an agent: its 14 days, every
level, other events and blocking were never the owner's choices. It blocked mostly over gaps the training rows share.
The review ended with three recommendations, which the owner answered (verbatim):

> "Replace the gate with the rule above? Recommended.
> Build the men's fill? Recommended.
> Add an input to the candidate-feature list saying how much data stands behind each player's recent form? Recommended."
>
> Do all 3, but check if there are other processes that may contradict this work that are active and using this work.

Carried out by Claude the same day (the process log, Part 2). The check found no running process using the gate, the
fills or the feature pool. The only overlap was in files the pattern-adjustment session had edited the night before.

## Decision

1. **Point 3 of 8 Oct is replaced.** Points 1, 2 and 4 stand: refresh first, the sandboxed build, the live rows.
2. **What is checked is unchanged:** every completed earlier match of either player, at the same event or with a
   latest possible finish in the 14 days before the match, for a box score.
3. **A missing box score never blocks a bet.** What it does depends on its kind, by the training rows' own coverage
   (2013–2025, `src/eda/box_score_gate_review/coverage.py`):

   | Kind of the earlier match | Training rows with a box score (men / women) | A gap |
   |---|---|---|
   | Main tour | 100% / 96% (99–100% since 2016) | sets the edge bar |
   | Challenger / WTA 125 | 99.5% / 94% | sets the edge bar |
   | Qualifying above ITF level | 94.5% / 85% (99–100% each season since 2019) | sets the edge bar |
   | Team events | 48% / 54% | noted |
   | ITF, its qualifying included | 8% / 6% (none before 2025) | noted |

   * **The edge bar:** the match may be bet only if the forecast, moved 1 point against the side, is still worth
     betting at the bookmaker's odds (`gate.EDGE_BAR = 0.01`). One missing earlier round moved the forecast by a median
     of 0.35 points in the review's replay, and by 1.17 points or more in 1 case in 10.
   * **Noted:** shown on the bet sheet. It changes nothing: the model learned from thousands of rows with the same gaps.
   * **A kind not listed** (none exists in Stage 0 today) is treated as setting the bar.
4. **Still blocking:**
   * a player who entered through qualifying with no qualifying match in the data (results are missing, not only box
     scores);
   * a live match not in Stage 0;
   * an unknown indoor input (since 9 Oct).
5. **The men's fill.** At bet time, a men's box score Tennis My Life hasn't published is filled from the ATP's own match
   statistics. Like the WTA fill, it is live only and never enters the training history, and Tennis My Life's numbers
   replace it once published. The status line below says where it stands.
6. **The evidence input goes to the feature pool, not the model.** The pool already held it as U-126, "form evidence
   and shrinkage", built 7 Oct on the frozen population, for the points form only and without the level layer. It is
   refreshed with the model's own weights and its admission card re-filed. The selection rounds decide whether it
   enters the model.

## Evidence

* **The review** (14 Oct). All of these figures come from it.
  * **The old gate's cost:** it withheld 4.4% of men's and 13.7% of women's main-tour matches in 2024–2026 (20% of
    women's in 2026), on permanent gaps alone.
  * **What caused the blocks:** almost every block came from team events, ITF, partial events and qualifying.
  * **Its evidence:** a model without the market price, from which every same-event round had been removed at once.
* **The replay** of 13 Jul 2026 (23 matches; the active instance; box scores deleted on purpose):

  | Deleted | Median move | Largest move |
  |---|---|---|
  | One earlier round at the event | 0.35 pts | 1.41 pts |
  | Every box score in the two weeks | 0.42 pts | 1.84 pts |

  * **No direction:** the moves average out (+0.002 and −0.04 points).
  * **The bet decisions:** judged by the complete-data forecast, betting through one missing round cost 3.0 hundredths
    of a unit of expected profit, against 37.2 forgone by blocking.
  * **The 1-point bar beat a block** in 15 of 16 combinations of scenario, margin and edge size.
* **A departure, stated as the adoption framework asks.** The rule set before the replay pointed to keeping a narrower
  block: the 90th-percentile move cleared 1 point, narrowly. The recommendation, accepted here, replaced the block
  with the bar, because the profit comparison answers directly the question that rule stood in for.
* **Classified before any result:** a betting rule, not a model change. Its nearest kind is a repair: the owner's own
  words named training parity, and the rest was unmeasured design.
* **A correction made before implementing.** The recommendation as the owner read it listed the women's qualifying as
  a kind training lacks. That came from pooling the ITF qualifying (0% box scores) with the tour and WTA 125 qualifying
  (99–100% since 2019). Corrected here: qualifying above ITF level sets the bar, for both tours. The principle the
  owner approved is unchanged.

## What it changes

* **Blocks:** from 4.4% (men) and 13.7% (women) of main-tour matches to about 0.2% and 0.4%. That remainder is the
  qualifier check, plus a rare unknown indoor input.
* **The edge bar:** matches whose gaps set it were 0.5% (men) and 4.3% (women) of main-tour matches in 2024–2026, on
  permanent gaps. Bet days add late publications, which the fills cover where they can.
* **Files:**
  * `gate.csv` gains `edge_bar`, `bar_gaps` and `noted_gaps`; its `bet` column reads "may be bet", "may be bet if its
    edge clears 1 point" or "do not bet: inputs incomplete".
  * `gate_missing.csv` gains each gap's `kind` and `effect`.
  * `predictions.csv` gains `gate_edge_bar`.
  * The bet sheet's record gains `gate_edge_bar`, `passed_by_bar` and `gate_notes`.
  * The data check's verdicts are "ready", "ready once filled", "needs a 1-point edge" and "will be blocked".
* **Runs made before 14 Oct keep their own gate,** and a sheet remade from them says what that gate said.

## Status

* **The gate:** in force from 14 Oct 2026 (`src/eda/prediction_run/gate.py`, `src/pipeline/diagnostics.py`,
  `bet_sheet.py`, `readiness.py`, `dp_predict.py`).
  * Tests: `test/prediction_run` and `test/master_pipeline`, 54 passed.
  * Not yet seen on a live bet day.
* **The men's fill:** in force from 14 Oct 2026 (`src/eda/prediction_run/fills.py`, `fill_atp` and `fill_all`, called
  by the refresh step).
  * **Scope:** men's tour-level main-draw matches. The Slams are not the ATP's, and Challenger statistics are
    unprobed.
  * **Not the qualifying:** there the ATP's first serves differ from Tennis My Life's. On 13 Shanghai qualifying
    matches, first serves in were equal on 9 of 26 player rows (the ATP 0.7 lower on average), while aces, service
    games and break points were equal on all 26. A fill there would not be the numbers the training rows hold, so a
    qualifying gap waits for Tennis My Life, under the 1-point bar meanwhile.
  * **How it links:** by the ATP event id, the round's match codes and both players' ATP codes.
  * **What it accepts:** a file whose service games add up to the score. The ATP's own "completed" flag reads False on
    9 of 82 finished Shanghai matches, so it is not relied on.
  * **Checked against Tennis My Life** on Shanghai 2026's main draw: all nine counts equal on 164 of 164 player rows
    (82 matches). The request path was tested live: 110 requests, about 2.5 s apart, each with a receipt and a raw
    copy. They brought 20 files (14 new), and each budget stop was clean.
  * **Expect it to be needed rarely:** in 2025–2026, men's matches of the kinds that set the bar lack a box score
    permanently in 7 of about 25,000 cases, and Tennis My Life usually publishes men's box scores within minutes.
* **The evidence input:** in the pool since 14 Oct 2026. U-126 was re-filed, verdict admitted.
  * **Code and columns:** `src/eda/feature_universe/form_evidence.py`; `fe__sw_a/_b` (the decayed count of earlier
    box-scored matches) and `fe__r_a/_b`, `fe__r_diff` (the share of the form still the prior).
  * **How it was built:** with the model's own form code, on template_2026-10-13's tree.
  * **Checks:**
    * it reproduces `adjperf_tpw_2w` bit for bit on all 67,226 frame matches;
    * the timing probe is clean;
    * its largest correlation with another input is 0.71 (sets in 14 days).
  * **Not in the model:** a selection round decides.
  * **Live use** would need the daily engine to output the weight sum. It computes it (`forms_state.step3_for`) but
    does not keep it.

## Revisit when

* the training rows' coverage of a kind changes: re-run `coverage.py` at each template build;
* bet days show the bar often taking bets away, or rarely mattering;
* the evidence input enters the model: the model could then price a gap itself, and the bar could go.
