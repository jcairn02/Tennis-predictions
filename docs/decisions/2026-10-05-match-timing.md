# The match clock: a result reaches another match only after it surely finished

**Stated by the owner on 5 October 2026**, after the [match-timing study](../studies/match_timing/README.md) and its explanation of the cautious window rule:

> "ok implement IOS and any necessary functions going forward in this way, using the data we just covered to find the exact day/time of the match. When we scrape going forward we want to find that information out. If there's another function we use that requires this, modify that too. Once that is finished, rebuild the IOS for the best performing tabpfn3.5 thinking model and do a single fit on the same matches/windows and see if it meaningfully changes our predictive value"

Recorded on 5 October 2026.

## Decision

1. **The two-time rule is the project's clock.** It applies to every feature that lets one player's result reach another player's inputs: ratings solved for all players together (IOS), smoothed ratings (TrueSkill Through Time), batch fits, and statistics of a field.
   * Every match has an earliest possible start day and a latest possible finish day.
   * A result may enter another match's inputs only if its latest possible finish comes before that match's earliest possible start.
   * Features that follow each player's own matches in order (Elo, Glicko, TrueSkill, serve and return ratings, opponent-adjusted profiles, workload, age) keep that order. A player's order is known even without days, because nobody plays two events at once.
2. **Cautious, never guessed.**
   * **Unknown day.** When no source gives a match's day, its window covers every day it could have been played. Its result is withheld until the window closes, and its own inputs are read as of the window's start.
   * **Disagreeing sources.** No day is chosen by trusting one source over another. A day that three or more sources share against a single dissenter stands. Otherwise the window covers every source's day.
   * **Measured clock error.** Each source's measured clock error widens its own days.
3. **Days come from the data, and scrapers keep the clock.**
   * Days come from the 13 sources linked so far.
   * Every scraper keeps the time fields its source sends: the start, whether that start is only scheduled, the finish, and the court or venue.
4. **Live use.** A result enters when it is final. The windows exist only to rebuild history for training and backtests.
5. **One paid refit is authorised.** One TabPFN-3.5-Thinking fit of the best 2026 model, on the same matches and configuration, with its IOS inputs rebuilt on this clock.

## Where it is implemented

* **The timeline.** `src/eda/match_timing/timing.py` writes `data/studies/match_timing/timing.parquet`: one row per match with its earliest start, latest finish, best-estimate day, the window's basis and why.
  * **Exact days:** from the link files in `data/studies/match_timing/links/`.
  * **Calibration:** each source's clock error, measured against point-log days, is in `source_calibration.csv`.
  * **Windows:** from the same round's dated matches, the researched schedule rules (`schedule_rules.csv`), class windows, the event's own shift and the draw order.
  * **Check:** `timing_check.py` tests the windows out of sample.
* **IOS.** `src/eda/match_timing/ios_time.py`, function `run_timed`: one solve per day.
  * The inputs are built by `rebuild.py`, giving `leakproof_features.parquet`.
  * The superseded weekly solver, `src/eda/ufc_ideas/stageB_ios.py`, is marked as such.
* **TrueSkill Through Time.**
  * `ttt_pass_timed` in `src/eda/rating_systems/ratings.py` is the leak-proof pass. On the old weekly clock it reproduces `ttt_pass` exactly (tested).
  * `ttt_pass` is marked as leaking.
  * `src/eda/match_timing/ttt_timed.py` re-measures TTT against Elo.
* **Scrapers that now keep their source's time fields:**
  * `src/ingest/point_sources/wta.py`: whether the start is estimated, and the court.
  * `sofascore.py`, plus `_editions` and `_tournaments`, which inherit its columns: the last set's start, the last change (within a minute of the last point for a finished match), and the venue.
  * `ausopen.py`: the archived draws' actual start, duration, court and session.
  * `tennislive.py`: the page's start.
  * `src/ingest/public_dump/polymarket_prices.py`: the event index's start, event date and end.

  The linkers read the new fields where staged files have them. `srcc_wta.py` uses the estimated-start flag; `srcc_sofascore.py` tags a finish on a later day than the start.
* **Going forward.**
  * Results reach Stage 0 only from Tennis My Life (`tennis_my_life.py`, then `stage0_build.py`).
  * Their days come from the sources that keep updating: tennis-data.co.uk via `refresh_odds.py`, the WTA API, SofaScore, the Slam feeds and TDI.
  * After those adapters run, `./python.sh src/eda/match_timing/refresh.py` re-links them, rebuilds and checks the timeline, and rebuilds the IOS inputs.
* **Guardrails.**
  * `probe.py` flips every result after a cut day and recomputes the inputs of matches that surely finished before it; nothing may move.
  * The timeline builder refuses a window that ends before it starts, and so does the IOS solver.
  * The tests are in `test/match_timing/`, `test/rating_systems/test_ttt_timed.py` and `test/tabpfn_leakproof/`.

## What the audit found (5 October 2026)

| Function | Verdict | Status |
|---|---|---|
| IOS (Stage B weekly snapshots): 22 inputs of the best 2026 model | Leaks | Rebuilt leak-proof; the old solver marked superseded |
| TrueSkill Through Time (`ttt_pass`, the leading rating candidate of 3 Oct) | Leaks | Leak-proof pass written. Re-measured against Elo in 2019–2026: +2.66 [+1.90, +3.41] men and +2.93 [+1.61, +4.25] women, against +2.65 and +3.00 before the fix |
| Bradley–Terry and MESR (`ufc_ideas/stageA_ratings.py`), strength-of-schedule revaluation (`stageC_sos.py`) | Leaks | Not in use; marked, to be rebuilt before any use |
| Elo, Glicko, TrueSkill, correlated-surface ratings, Stage 3 serve/return ratings, opponent-adjusted profiles, 52-week points, workload, age | No leak | Kept. Their time gaps (decay, 14-day and 52-week spans) are counted from event start dates: imprecise, not leaking |
| Normalising constants (surface means, typical units, shrinkage) | No leak in the test years | Frozen on 2010–2018 |

## Not decided

* **Old ITF days.** Whether to acquire days for old ITF matches, women's ITF qualifying especially (70,124 matches, none dated). SofaScore holds women's ITF from 2014; Tennis Explorer needs Livesport's consent.
* **Time gaps of the per-player features.** Whether to measure them from match days instead of event start dates. This is an improvement, not a leak fix.
* **Earlier results.** Whether earlier studies' results are redone on this clock. They stand as recorded, with this caveat.
* **TrueSkill Through Time's standing.** Whether the 3 October decision stands on its re-measured evidence is the owner's call. The leak-proof re-measurement changes TTT's edge over Elo by +0.01 for men and −0.07 for women.
* **The project's status.** No production pipeline, model, dataset, market or roadmap is selected.
