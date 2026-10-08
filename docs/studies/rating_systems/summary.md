# Summary: rating systems against Elo

> **Current standing (the owner, 3 Oct 2026): TrueSkill Through Time is the leading candidate for the model's base rating,** the slot surface Elo has filled so far. It is the present leader, not a final choice. See the [decision record](../../decisions/2026-10-03-leading-rating-candidate.md).

**Status: written 2 Oct 2026 and reviewed by the owner on 3 Oct 2026. Apart from the designation above, a study, not a decision.** The same summary opens [report.html](report.html). Labels: **observed** is measured, **inferred** is our reading, **suggestion** is a proposal. Every number is read from `data/studies/rating_systems/summary_results.json`, written by `src/eda/rating_systems/summary_results.py`. The literature is in [docs/research/rating-systems/](../../research/rating-systems/README.md).

## The short version

You asked whether Glicko-2 or TrueSkill, or whatever the published evidence finds most predictive, improves on the surface Elo used as the base so far, and whether that helps against the closing line. Eight systems were built for tennis under the same time rule as Elo, tuned on the same seasons (2013–2018) and frozen. They were then scored on the same 155,130 men's and 60,321 women's matches of 2013–2026.

* **Observed. Glicko-2 as Glickman specifies it is worse than Elo,** with a tournament week as the rating period: by 1.42 (men) and 0.32 (women) milli-log-loss in 2019–2026.
  * Run match by match it is about one milli-log-loss better than Elo (+0.90 and +1.01).
  * Its volatility adds nothing: Glicko-1 does as well.
  * TrueSkill as such is about the same (+0.69, +1.30).
* **Observed. The best rating is TrueSkill Through Time, the smoothing system the literature ranks highest.**
  * It beats surface Elo by **2.65 (men) and 3.00 (women)** milli-log-loss after the tuning years (2019–2026), as much as in them.
  * It has the lowest log loss of the nine ratings on the tuning years, the rule that picks the leader, on both tours.
  * Head to head after the tuning years:
    * For the men, it beats the runner-up (correlated-surface Glicko) by +0.54 (−0.02 to +1.10) in 2019–2026 and +0.85 (+0.18 to +1.53) in 2022–2026.
    * For the women, it is level with TrueSkill with correlated surface skills: −0.29 (−1.29 to +0.71) and −0.68 (−1.99 to +0.62).
  * It holds when two-week events are held back (+2.59, +2.75).
  * A Bayesian surface model (correlated surface skills) is next: +2.11 and +2.68.
* **Observed. None of it reaches the bookmakers.** On the main-tour matches with odds, TTT closes about a tenth of the gap between Elo and the closing prices. Added to the closing prices it gains about nothing:
  * +0.04 (men) and −0.02 (women) through the shared test;
  * +0.08 against calibrated Pinnacle in the audit's own test.
* **Observed. The better rating is only partly orthogonal to the promising features.**
  * In the audit's full feature model, swapping Elo for TTT gains only +0.48 (men) and +0.19 (women): the serve-and-return ratings already carry most of TTT's edge.
  * Keeping both ratings gains about a milli-log-loss (+1.17, +1.21).
  * The men's statistics profile, the one lead against the odds, is untouched by any rating.
* **Inferred.** A better rating makes a better forecast, by a little, but adds nothing the bookmakers lack. That agrees with the published evidence and with your view that results-based ratings are priced in.

## How far each forecast gets

Main-tour matches with bookmaker odds, 2022–2026 (12,352 men's, 11,467 women's). On this scale a coin flip is 0% and the bookmakers' closing prices are 100%; each rating stands alone, with no features added:

| Forecast | Men | Women |
|---|---:|---:|
| Surface Elo (the base so far) | 78% | 82% |
| Glicko-2, match by match | 78% | 82% |
| TrueSkill | 78% | 83% |
| Glicko with correlated surfaces | 80% | 83% |
| TrueSkill Through Time | 81% | 83% |
| Bookmakers' closing prices | 100% | 100% |

## What each system did

Better (+) or worse (−) than surface Elo, milli-log-loss, every evaluation match of 2019–2026 (after the tuning years), with the 95% interval clustered by four-week calendar blocks:

| System | What it is | Men | Women |
|---|---|---:|---:|
| **TrueSkill Through Time** | Re-estimates every player's whole history as results arrive, so an old win is credited at what the opponent later proved to be worth | **+2.65** (+1.89 to +3.40) | **+3.00** (+1.67 to +4.33) |
| the same, two-week events held back | Grand Slam results join only after the event, the conservative check on smoothing | +2.59 | +2.75 |
| **Glicko with correlated surface skills** | A skill per surface, linked by a correlation (the Bayesian form of the surface blend) | +2.11 (+1.20 to +3.01) | +2.68 (+1.06 to +4.29) |
| TrueSkill with correlated surface skills | The same with TrueSkill's update | +1.75 | +3.29 |
| **Glicko-2, match by match** | Glicko-2 updated every round, the uncertainty growing with time away | +0.90 (+0.27 to +1.54) | +1.01 (−0.31 to +2.32) |
| **TrueSkill** | Microsoft's Gaussian rating, two players, no draws | +0.69 (+0.07 to +1.31) | +1.30 (−0.05 to +2.66) |
| **Glicko-2, weekly periods** | As Glickman specifies it: a week's games scored together | −1.42 (−2.23 to −0.62) | −0.32 (−2.07 to +1.44) |

* **Why the weekly Glicko-2 loses.** Glickman designed it for 10–15 games per player per period; tennis players play one to five a week. Scoring them together overshoots for uncertain players. The deficit sits almost entirely in matches with a player who has 20 or fewer prior matches: about 70 to 120 milli-log-loss worse for the men, within ±1.6 among veterans ([Stage B](stageB.md)).
* **Where TTT gains.** Mostly on experienced players, where most matches are (+2.11 for the men when both have over 100 matches). Its largest gains per match are after long layoffs (+13.36 after 6–12 months out) and on newcomers. Elo's K never grows with time away.

## Against the bookmakers

* **Observed. Added to the closing prices, no rating adds more than a fifth of a milli-log-loss.**
  * Through the shared test (2013–2026), every rating scores between −0.03 and +0.08.
  * In the audit's own market test (men, Pinnacle, 2019–2026), TTT adds +0.08 (−0.01 to +0.16) and the match-by-match Glicko-2 +0.12 (+0.01 to +0.23).
  * The same on the audit's repaired data: TTT +0.09.
* **Inferred.** At most about 1% of the gap between Elo and the market, and only at the edge of significance. Not an edge.

## Beside the promising features

* **Observed. The audit's feature ladder** (men, 2022–2026):
  * TTT alone beats calibrated Elo by +2.08, and the correlated Glicko by +2.44.
  * With the full feature set, swapping Elo for them gains +0.48 and +0.56; keeping both ratings gains +1.17 and +1.28.
  * The serve-and-return ratings add 4.74 given Elo but 3.10 given TTT: they are the overlap.
  * TTT also absorbs the games-weighted Elo almost completely (1.82 → 0.04 through the shared test).
* **Observed. The context features keep or grow their gain given TTT:** recent load, a new surface, age (age 1.42 → 2.79 for the men).
* **Observed. The men's 16-input statistics profile is orthogonal to every rating.** It adds 3.97 given Elo and 3.78 given TTT. Against Pinnacle, adding TTT to it changes nothing (+0.00).
* **Observed. The audit's repaired data agree.** On main-tour matches with trusted dates and rebuilt features:
  * TTT alone beats calibrated Elo by +2.07 (men) and +3.05 (women);
  * in the full model it adds +0.34 and +0.57;
  * beside Elo, +0.75 and +0.97.

## What the published evidence says

From [docs/research/rating-systems/](../../research/rating-systems/README.md), two literature sweeps on 2 Oct 2026:

* **Reported.** No peer-reviewed tennis study compares Glicko-2 with Elo. Glicko-1 ties Elo in the two peer-reviewed tennis tests (ATP 2018–19; WTA 2022), and TrueSkill ties or slightly beats a constant-K Elo.
* **Reported.** The largest published gain over Elo comes from smoothing (TrueSkill Through Time, KickScore): about 0.011 nats per match, but against a constant-K Elo without a surface model, and never against odds.
* **Reported.** A surface model is the most consistent extension. No study shows any rating beating the bookmakers.
* **Inferred.** This study reproduces that ranking against a much stronger Elo. The smoothing gain shrinks from 11 to about 2.7 milli-log-loss once Elo's K falls with experience and a surface blend is added. The surface model helps. Glicko-2 and TrueSkill as such tie.

## What we suggest next

* **Suggestion. If the project wants a better base rating, use TrueSkill Through Time, or keep Elo and add it.**
  * It beats surface Elo out of sample on both tours, in every window and era. It is the best rating found in every window for the men. For the women, it is best on the tuning years and level with the correlated-surface TrueSkill after them.
  * Beside Elo in the audit's full model it adds about a milli-log-loss.
  * The cost is speed: the men's full pass takes about 19 minutes against Elo's second.
* **Suggestion. Spend nothing more on ratings for the closing line.** Every rating is priced in, and the one lead against the odds, the men's statistics profile, is orthogonal to all of them. Point-by-point and per-statistic work stays the place to look.
* **Suggestion. If a rating is kept, rerun it after the identity fixes.** The audit's repairs canonicalised the 2026 split identities in their own pipeline. This study's history still has them.

## Decisions for you

1. **The base rating** for later studies. **Answered 3 Oct 2026:** TrueSkill Through Time is the current leading candidate ([decision record](../../decisions/2026-10-03-leading-rating-candidate.md)).
   * Still open: whether surface Elo is carried beside it. The study suggests both, since they add to each other.
   * It changes the prediction baseline, not the market question.
2. **Whether to keep TTT and the correlated-surface rating** (`src/eda/rating_systems/ratings.py`) as maintained code, with their tests.

## Problems found (reported, not fixed)

* **The shared harness changed while this study ran.** Other work revised `stage4_rundown.py` and `ufc_ideas/common.py` on 2 Oct 2026 at 16:48 to four-week cluster intervals and a stricter "finding".
  * The earlier leaders' point estimates still reproduce exactly through it; their ranges no longer do.
  * Every stage here records the hash of the shared code it ran with.
* **The event-start time rule and two-week events.** The audit flagged that a Grand Slam's second week counts as known before it is played. Filtering ratings cannot pass that between players; TTT's smoothing can.
  * Holding those events back costs TTT 0.06–0.25 milli-log-loss in 2019–2026, so the overlap is not its source.
  * Every other system is unaffected.
* **TTT's smoothing window for the men reached the largest value tried** (416 weeks). The last doubling gained 0.12, so little is left.
* **The 2026 split identities** (Stage 1's problem) remain in this study's history.

## Files

The stages' code, tests, outputs and write-ups are listed in the [README](README.md). This summary's numbers are in `summary_results.json`; the page is built by `render_report.py`.
