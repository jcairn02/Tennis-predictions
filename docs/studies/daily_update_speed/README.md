# A daily update in minutes, not hours

10 October 2026 · For the owner · Process log: [process_log.md](process_log.md). Working detail: [scoping.md](scoping.md).

**Status, 11 Oct 2026:** the daily path is built by the [daily prediction script](../daily_prediction/README.md)
(another session; about 5.5 minutes a day, replay-proven). This study's own lean build stopped on finding it; what it
had written, a live assembler (the 57 inputs from the five tables that compute them, equal to the chain's frame on all
67,226 matches, 11 seconds), duplicated that script and was deleted on the owner's word (12 Oct). Done here and still in
force: the scoping below, the bet-time pricing measurements, and the 2027 fix. **This study is closed;** predictions
run from the master notebook (`CLAUDE.md`, "Daily predictions: the master notebook").

The owner, 10 Oct 2026: a daily rebuild of about 2 hours "is unnaceptable. Anything even close to this is
unacceptable." The target taken: new results in, the day's 57 inputs out in a couple of minutes; pricing at bet time
immediate; the numbers identical to a full rebuild's (proven by the replay, as on 10 Oct).

## In short

1. **Most of the 2 hours computes nothing the model reads.** Of about 35 steps, 7 compute values that reach the 57
   inputs. The rest are checks and reports from the research builds, tuning grids that pick the same settings every
   time, and duplicate computations replaced later in the chain.
2. **Without changing any number, a lean daily build should take about 10 minutes** (estimate from the step times):
   skip what reaches no input, use the settings the grids always pick, compute only the needed columns.
3. **With saved state, about 2 minutes:** each rating and profile resumes from where the last full build left it, and
   only the days since are processed. What remains is downloading and rebuilding the match table and the timeline.
4. **Bet time is a lookup.** One model run prices each of the day's matches at every price (about 1 minute per seed;
   16 seeds about 15 minutes, before betting starts). Read back at a match's own price it is within 0.0008 of a direct
   prediction (`data/studies/daily_update_speed/bet_time_pricing_grid_plain.json`). The library's faster cached mode
   gives different numbers (up to 0.18) and is not used until explained.
5. **Found on the way, to fix whatever is decided:** from 1 January 2027 the chain gives no match any input (year
   ranges end in 2026). And the step that turns inputs into a probability (forecasting) has never been built.

## The 2027 fix (done 10 Oct 2026, at the owner's word)

**What would have happened.** From 1 January 2027 no match would have got any input: Stage 0's evaluation flag,
Stage 4's pool and the frame's split all stopped at 2026. Less visibly: the timeline had no era for 2027, the Australian
Open 2027's official times would have been dropped as implausible, Stage 1 would have skipped 2027's per-season fits,
and the serve-speed adjustment would have stopped fitting new seasons after 2027.

**What changed.** Each of those limits is now open-ended, written so that every season to 2026 is treated exactly as
before. 13 files; the two hooked builders' edits are listed (`system_sandbox.POST_VALIDATION`), so the level-evidence
study's check that the builders carry its validated code still holds.

**The proof.**
* A 2027 match passes every gate (`test/daily_update_speed/test_year_limits.py`: 5 tests).
* Nothing moved on today's data: each rule, old against new, on the repository's and the frozen reference's tables,
  including the 7,931 Grand Slam feed rows (`data/studies/daily_update_speed/year_fix_checks.json`: all equal).
* The chain's tests pass, except the failures that predate this work (tables built before 8 Oct).

**Added 12 Oct 2026, at the owner's word ("in 2027 I don't want to fall back to using average odds"):** a limit the
first pass missed, found by the master-notebook session. The odds-sources study's season lists
(`src/eda/odds_sources/common.py`) ended in 2026, so no 2027 tennis-data row would be linked to OddsTrader and every 2027
match's Pinnacle-first input would fall back to the books' average. They now take every season tennis-data.co.uk holds on
disk (`td_seasons`): today exactly the lists of before (2013–2026, 2018–2026), so nothing moves; a 2027 file is taken
once staged (a test). The rest of that path chooses its years from the date (the odds refresh, OddsTrader's months) or
has no season limit (the linker, the reconciliation, the rule). The notebook's rollover note was updated to match.

**Still to do.** An end-to-end run with a 2027-dated match, once the lean build makes that a few minutes. At the turn
of the season, as every year: the 2027 model's fits, the serve-speed coefficients, and the level layer's refit (until
then 2027 reads 2026's parameters, as decided).

## Decision for the owner

Rows of past matches change most days (Tennis My Life's corrections, late box scores, restaged sources). Option (a):
the daily update detects them and falls back to the lean full build (about 10 minutes) when they touch the history
before its saved state. Option (b): the history before a cut is held fixed between full rebuilds (weekly, overnight),
recent weeks recomputed daily; older corrections wait for the next weekly rebuild. **Recommended: (b)**, with the cut
three weeks back: late box scores arrive within days, so they are always included; a correction to a match weeks old
barely moves today's inputs, and the daily time stays predictable.
