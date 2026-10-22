# Prediction runs refresh box scores first, and build live inputs with the training code

**Amended by the owner on 14 October 2026:** point 3 (the gate) is replaced. A missing box score no longer blocks a
bet: of a kind the training rows nearly always hold it asks a 1-point edge, of a kind they mostly lack it is noted; only
the qualifier and indoor checks still block ([decision](2026-10-14-box-score-gate.md)). The rest of this record stands.

**Asked by the owner on 8 October 2026:**

> "When we are working with live data on the prediction pipeline, we need a better pipeline. 'Make live inputs match what the model was trained on. Every prediction run should refresh box scores first: without the same event's earlier rounds, the 2-week profile loses a third to a half of its gain over Elo.'"

**Three choices made by the owner the same day**, from options Claude put to them after measuring the gap (below). Recorded on 8 October 2026.

| Question | The owner's choice |
|---|---|
| How far to build now | **Steps 1–4:** the refresh, the sandboxed rebuild, the gate, and the live rows built by the existing chain, proven by a replay. Forecasting (step 5) follows once upcoming matchups and prices are linked to the project's player ids |
| When Tennis My Life (TML) has a result but no box score | **Fill, live only:** "Only matches played after the 8 Oct freeze are filled. TML's own numbers replace a fill once TML publishes, and fills never enter the training history. This accepts the measured differences (first serves in 95.5% exact, service games 83.7%)." |
| A box score arriving after the freeze for a match the reference holds without one | **Recent matches update:** "Matches played from 5 Oct on (the freeze minus its 3 grace days), from the feeds that fed the reference, may change like new matches do. Everything older stays frozen exactly as now." |

## Why: the measurements put to the owner

* **The claim holds.** In Stage B's recency diagnostic ([stageB.md](../studies/ufc_ideas/stageB.md)), leaving out the same event's earlier rounds cuts the two-week profile's gain over Elo (milli-log-loss, higher is better) from 3.19 to 2.09 for men and from 3.32 to 1.83 for women.
* **It covers more than the two-week profile.** 41 of the model's 58 inputs are built from box scores, and all 41 read the same event's earlier rounds:
  * the 17 two-week inputs;
  * the serve and return ratings;
  * IOS points;
  * points over 52 weeks;
  * the 21 surface IOS inputs.
* **A missing box score is silent.** The match is skipped, and the decayed two-week average shrinks toward 0 (it divides by its weights plus a prior worth 10–20 matches).
* **The training standard.** In 2019–2025, 98.4–99.7% of the same event's earlier-round player-matches of the frame had a box score.
* **What a forecast would have read on 8 Oct.**
  * *No code forecast an unplayed match.* Every scoring path needed a played match in the model frame.
  * *ATP:* TML often has a box score minutes after the match. But the project downloads once a day (14:30 UTC) and rebuilt Stage 0 only by hand.
  * *WTA:* TML listed WTA Beijing's newest results without box scores for over 24 hours: three round-of-16 matches from 7 Oct, then one more and both quarter-finals on 8 Oct.
  * *Permanent gaps:* TML has no box scores for Roland Garros 2026 (254 main-draw matches) or WTA Berlin and Nottingham (58).
  * *The WTA's own API* served a Beijing box score 75 minutes after the match (one measurement). On 2026 WTA tour rows it agrees exactly with TML on 99.9% of aces, double faults and break points, 99.3% of serve points, 95.5% of first serves in and 83.7% of service games ([data continuity](../studies/data_continuity/README.md), section 3.2).
* **The frozen-reference check would have refused the first refresh.** The reference holds 50 recent matches without box scores, WTA Beijing's six among them, and counted any change to them as a revision.

## Decision

1. **Every prediction run refreshes box scores before anything else.**
   * It downloads TML.
   * It lists the main-tour matches of the last 14 days that have a result but no box score.
   * It fills those the frozen reference does not hold from the official feed that serves them: the WTA API now; the ATP Stats Centre and the Slam feeds would follow.
   * **Fills are live only.** They are rebuilt at every run, so a match TML has since completed takes TML's numbers. They go only into the run's own sandbox, never into the shared Stage 0 or a template build's training history.
   * **Checked on 9 Oct 2026:** on the 81 WTA Beijing matches TML had scored, the WTA API's box scores, read as a fill reads them, equal TML's on all nine counts in every player row (162 of 162). At that event a fill costs nothing. The earlier differences (95.5%, 83.7%) were measured over 2026 to May.
2. **The run rebuilds in its own sandbox,** never in `data/studies/`: Stage 0 with the decided overrides, the corrections and the fills, then the odds, the timeline and the leak-proof features.
3. **A gate holds the training standard.** For each upcoming match, every finished match of either player at the event and in the last 14 days must have a box score. A match that fails is recorded with what is missing and marked not to bet.
4. **Live inputs come from the training code.**
   * Each upcoming match enters the sandbox as a row with a placeholder result and no box score, priced and dated the way the frame's matches are.
   * The unchanged chain builds its 58 inputs.
   * **The proof:** a replay of past rounds as live rows must reproduce the frame's inputs exactly, and flipping the placeholder results must change nothing.
5. **The history check** (`src/eda/current_best_model/history.py`).
   * A reference match the feed was still publishing at the freeze may change (box score completed, score corrected, row dropped) like a new match. That means a match possibly played from 5 Oct on (its latest possible finish on or after it), from a source, tour and level that fed the reference.
   * New matches are placed the same way. Undated matches carry wide windows: Shanghai 2026's first round opens its window on 3 Oct, so testing the earliest start would have called the next rounds old.
   * A reference match is placed by the reference's own timeline, so a revision cannot move it into the window.
   * 194 reference matches qualify, all from events in progress at the freeze: Shanghai's main draw and qualifying, WTA Beijing, the BJK Cup Finals, ATP Beijing and Tokyo, and four Challengers.

## Where it is implemented

The [prediction-run study](../studies/prediction_run/README.md) holds the commands, the checks and the first live run.

* **The history check:** `src/eda/current_best_model/history.py` (the `updated` class), tested in `test/current_best_model/test_history.py`.
  * On the download of 9 Oct (05:28 UTC) it reads: future 17 and updated 6 (allowed), nothing refused.
  * The 6 are WTA Beijing's late rounds, whose box scores TML had just published. The old rule would have refused every template build.
* **The prediction run:** `src/eda/prediction_run/`.
  * `run.py --refresh`: the download, the gaps and the WTA fills.
  * `--setup`, `--build`: the sandbox and the chain.
  * `gate.py`: the gate.
  * `replay.py`: the proof.
* **Live rows in Stage 0:** `stage0_build.py --live-rows`. Without it, the build's tables are byte-identical to before.
* **The window rule.** A live match takes its tour's window of the 60 days before it. Decided by Claude while building, because the dating changed in July 2026 (TDI's point logs date ATP matches exactly since then). See the study.

## Not decided

* **Forecasting (step 5).** It needs a source of upcoming matchups and bet-time prices linked to the project's player ids (Polymarket's open markets, OddsTrader's lines), and the choice of price ([bet-timing study](../studies/bet_timing/README.md)).
* **Fills for matches the reference holds.** They wait for TML, as decided. WTA Beijing's six had box scores in TML's download of 9 Oct (05:28 UTC).
* **Roland Garros 2026, WTA Berlin and Nottingham.** They are permanent gaps in TML. They are in the training history, before the freeze, so filling them would be a candidate.
