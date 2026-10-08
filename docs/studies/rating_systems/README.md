# Rating systems against Elo

> **Current standing (the owner, 3 Oct 2026): TrueSkill Through Time is the leading candidate for the model's base rating.** That is the slot surface Elo has filled so far. It is the present leader, not a final choice. The evidence, its limits and what stays open are in the [decision record](../../decisions/2026-10-03-leading-rating-candidate.md).

> **Update, 5 Oct 2026: `ttt_pass` leaked across overlapping events, and the leak-proof version keeps TTT's edge.**
>
> * **What leaked.** Its smoothing passed each start date's batch of matches, rounds still unplayed included, to every player.
> * **The fix.** `ttt_pass_timed` applies the match clock ([decision](../../decisions/2026-10-05-match-timing.md)).
> * **The result.** Against Elo in 2019–2026 it scores +2.66 [+1.90, +3.41] for men and +2.93 [+1.61, +4.25] for women, against +2.65 and +3.00 here ([match-timing study](../match_timing/README.md), section 8). Use `ttt_pass_timed` for new work.

**Status: study.** Built 2 Oct 2026 in one session, at the owner's request: try to improve on the base Elo with a Glicko-2 and/or a TrueSkill rating; research what has been published on rating systems in tennis; and find the most predictive rating that stays as orthogonal as Elo to the promising features. The summary is [summary.md](summary.md) and the top of [report.html](report.html). The literature is in [docs/research/rating-systems/](../../research/rating-systems/README.md). Beyond the owner's designation above, nothing here chooses a rating, features, models, markets or a roadmap.

## In short

* **Observed. Glicko-2 as Glickman specifies it (a week as the rating period) is worse than the tuned surface Elo.**
  * Run match by match it is about a milli-log-loss better, with Glicko-1 doing as well.
  * TrueSkill is about the same.
* **Observed. The best rating is TrueSkill Through Time, run causally:** +2.65 (men) and +3.00 (women) milli-log-loss better than surface Elo in 2019–2026, after the tuning years.
  * It has the lowest log loss on the tuning years, the rule that picks the leader, on both tours.
  * For the men it stays best in every window. For the women, after the tuning years it is level with TrueSkill with correlated surface skills: −0.29 (−1.29 to +0.71) head to head in 2019–2026.
  * Correlated surface skills are next. Both match the literature's ranking.
* **Observed. No rating adds to the closing odds:** a tenth of a milli-log-loss at most.
* **Observed. The better rating is partly orthogonal to the promising features.** In the audit's full feature model it adds about half a milli-log-loss in Elo's place, and about one beside Elo. The men's statistics profile is untouched by any rating.

## The question

The earlier studies ([predictability diagnostic](../predictability_diagnostic/README.md), [ideas borrowed from UFC-predictions](../ufc_ideas/README.md), the [feature alpha audit](../feature_alpha_audit/README.md)) all used Stage 1's surface Elo as the base rating. It is a FiveThirtyEight-style Elo whose K falls with a player's matches, with a per-surface rating blended in, tuned on 2013–2018 and frozen. Four questions:

1. **Does Glicko-2 or TrueSkill predict better than that Elo?** And does the rating the published evidence finds most predictive for tennis?
2. **Does any rating add to the bookmakers' closing prices?**
3. **Is a better rating as orthogonal as Elo to the promising features**, or does it carry what they carry? The features are the serve-and-return ratings, recent opponent-adjusted form, the context block, and the men's statistics profile against the odds.
4. **What does the published evidence say?**

## Stages

| Stage | What | Write-up |
|---|---|---|
| Literature | Two sweeps of published evidence: tennis studies, the algorithms' specifications, comparisons in other sports | [docs/research/rating-systems/](../../research/rating-systems/README.md) |
| A | Eight systems built for tennis under the time rule, tuned on 2013–2018 and frozen: Glicko-2 (weekly rating periods as Glickman specifies, and match by match), Glicko-1 (both ways), TrueSkill, correlated-surface Glicko and TrueSkill, TrueSkill Through Time run causally. Plus a sensitivity: TTT with two-week events held back. Built 2 Oct 2026 (80 minutes; 1,160 settings; every probe clean). In the tuning years TTT beats Elo by 2.65 (men) and 2.53 (women); the weekly Glicko-2 loses by 5.96 and 2.15 | [stageA.md](stageA.md) |
| B | Each against surface Elo and the closing odds, by window, level and era; calibration; where the gain comes from; the shared harness. Built 2 Oct 2026 (3 minutes). After the tuning years TTT beats Elo by 2.65 (men) and 3.00 (women) and closes about a tenth of the gap to the closing prices; given the odds no rating adds anything | [stageB.md](stageB.md) |
| C | The feature-alpha audit's ladder with each rating as the base; the men's statistics profile against the closing line with each rating as an input; both again on the audit's repaired cohort. Built 2 Oct 2026 (90 seconds). About three quarters of the gain over Elo is in the serve-and-return ratings already; both ratings together add about one milli-log-loss to the full model | [stageC.md](stageC.md) |
| Summary | What was found, what to do next, decisions | [summary.md](summary.md) · [report.html](report.html) |
| Decision | 3 Oct 2026: the owner names TrueSkill Through Time the leading candidate for the base rating. `summary_results.json` gains the `leader` block, which holds the tuning-year ranking and TTT head to head against every other system | [decision record](../../decisions/2026-10-03-leading-rating-candidate.md) |

## Brief

**Scope.** Exactly the earlier studies':

* Singles only; ATP and WTA separately, side by side.
* Evaluation matches: Grand Slams, Tour Finals, 1000s, 500s, 250s, their qualifying, and Challenger / WTA 125 main draws and qualifying. Completed or retired; walkovers excluded.
* Evaluation years 2013–2026, with 2010–2012 as warm-up; headline window 2022–2026.
* Rating history: every singles match from 2010 at every level, 872,704 matches.
* No betting simulation.

**Rules.**

* Follow [CLAUDE.md](../../../CLAUDE.md): `./python.sh`, the filing table, no Git command that changes state.
* The earlier studies' code and tables are imported, never edited: `stage1_baselines`, the shared harness `ufc_ideas/common.py`, and the audit's `elo_retest.py` and `profile_retest.py`.
* **The time rule.** A match's rating may use earlier weeks and earlier rounds of its own event only: never the match itself, another match of its round (a round robin), or another event of its week. It is held as `stage1_baselines.elo_pass` holds it.
* **Probes.** Every system is probed by `stage1_baselines.probe_by_round`, cut by date, event and round. Tests check every pre-match value against a fresh pass over only what the rule lets it see.
* **Tuning.** Constants are tuned on the overall rating's log loss over the evaluation matches of 2013–2018, then the surface weight, then frozen. This is Stage 1's procedure for Elo. A best value on a grid edge widens the grid.
* **Scoring.** Log loss only. Differences are in milli-log-loss, with the word better or worse.
* **Intervals.** 95% intervals clustered by four-week calendar blocks (the shared harness as revised on 2 Oct 2026), or by calendar week (the audit's retests).
* **Numbers.** Every number is computed before it is stated.
* **Labels.** **Observed**, **inferred**, **suggestion**.
* **The shared code may change.** Other work revised the shared harness on 2 Oct 2026 at 16:48, while this study ran. Every stage's summary therefore records the SHA-256 of the shared code it ran with, and the size and date of its input tables (`shared_code`).

## Files

| What | Where |
|---|---|
| The systems: Glicko-2 and Glicko-1 (weekly and match by match), TrueSkill, correlated surface skills, TrueSkill Through Time, each under the time rule | `src/eda/rating_systems/ratings.py` |
| Shared helpers: the history arrays, paths, the shared-code hashes | `src/eda/rating_systems/common.py` |
| Stage A: grids, widening, surface weights, full passes, checks, probes | `src/eda/rating_systems/stageA_ratings.py` → `stageA_ratings.parquet`, `stageA_tuning.csv`, `stageA_surface_weights.csv`, `stageA_summary.json` |
| Stage A sensitivity: TrueSkill Through Time with two-week events held back | `src/eda/rating_systems/stageA_ttt_hold.py` → `stageA_ttt_hold.parquet`, `stageA_ttt_hold_summary.json` |
| Stage B: comparisons and the harness | `src/eda/rating_systems/stageB_compare.py` → `stageB_features.parquet`, `stageB_summary.json`, `stageB_ranking.csv`, `stageB_results.csv`, `stageB_null_copies.csv`, `stageB_results.json`, `stageB_catalog.json` |
| Stage C: the ladder, the closing line, the repaired cohort | `src/eda/rating_systems/stageC_orthogonality.py` → `stageC_ladder_results.csv`, `stageC_market_results.csv`, `stageC_repaired_results.csv`, `stageC_summary.json` |
| The summary's numbers; the report | `summary_results.py` → `summary_results.json`; `render_report.py`, `report_summary.py`, `report_stageA.py`, `report_stageB.py`, `report_stageC.py` → `docs/studies/rating_systems/report.html` |
| Tests | `test/rating_systems/test_ratings.py` (the formulas, the time rule, the probes), `test/rating_systems/test_stages.py` (the stage logic) |
| Outputs | `data/studies/rating_systems/` |

**Rebuild,** from the repository root, in this order:

1. `./python.sh src/eda/rating_systems/stageA_ratings.py`. Add `--reuse-grid` to read back settings already in `stageA_tuning.csv`; `--top-only` rewrites only the sanity list. Its grid passes took 16,785 CPU-seconds in all, about an hour on 5 workers, mostly TrueSkill Through Time's long-window passes. The surface weights, full passes and probes took 26 minutes more (`stageA_summary.json`, `timings`).
2. `stageA_ttt_hold.py` (about 20 minutes on 2 workers), then `stageB_compare.py`
3. `stageC_orthogonality.py`
4. `summary_results.py`
5. `render_report.py`

Tests: `./python.sh -m pytest test/rating_systems`.
