# Summary: what we found

> **Correction, 2 October 2026:** These are historical results. The audit found chronology, forecast-format and evaluation defects. The shared code and shortlisted features have been repaired; see the [repair report](../feature_alpha_audit/repairs.md). Original numerical results below have not been relabelled as corrected results.

**Status: written 2 Oct 2026, waiting for your review. A study, not a decision.** The same summary opens [report.html](report.html), with charts; the five stages follow it there as reference. Labels: **observed** is measured, **inferred** is our reading, **suggestion** is a proposal.

## The short version

We tested 59 candidate features (325 versions in all) on 155,130 men's and 60,321 women's professional matches from 2013 to 2026. Each season was always predicted from earlier seasons only.

* **Observed. The bookmakers stay ahead.** No feature improves on their closing prices by more than 0.3% of the way from a coin flip to their prices: far too little to bet on.
* **Observed. A few things beat Elo, modestly.** Serve-and-return strength ratings do best: they close about 28% (men) and 29% (women) of the gap between Elo and the bookmakers. Recent form, recent workload and a new surface add less.
* **Inferred. Pre-match records look priced in.** If there is an edge, it is more likely in live (in-play) data, or in markets less sharp than the bookmakers' closing prices.

## How far each forecast gets

Forecasts are scored by how much probability they gave the player who actually won (log loss). On this scale a coin flip is 0% and the bookmakers' closing prices are 100%. Main-tour matches with bookmaker odds, 2022–2026:

| Forecast | Men | Women |
|---|---:|---:|
| Official ranking | 48% | 52% |
| Elo rating | 78% | 82% |
| Elo + the best new feature (the strength ratings) | 85% | 86% |
| Bookmakers' closing prices | 100% | 100% |

## What helps beyond Elo, and by how much

Each figure is the share of the gap between Elo and the bookmakers that the family's best version closes, on main-tour matches (Grand Slams down to 250s, where bookmakers price matches).

* Only versions that passed the study's strict test count: fitted on earlier seasons, tested on later ones, and better than chance across all 325 tests.
* The families overlap, so their shares do not add up.

| What we tried | Men | Women | Beyond the bookmakers? |
|---|---:|---:|---|
| **Serve and return strength ratings**: how well each player serves and returns, rated point by point against each opponent. They see every point, not just who won | 28% | 29% | no |
| **Points won**: share of serve, return and total points won. The last 12 months help; career averages do not | 9% | 13% | no |
| **Margin of recent wins**: an Elo that counts how decisively matches were won. Mostly the margin of the latest match | 4% | 13% | no |
| **Match length**: best of five sets (men's Grand Slams). Already inside the strength ratings | 10% | – | no |
| **Age**: older men do worse than Elo expects | 9% | no | no |
| **Recent workload**: sets and minutes played in the last one or two weeks. It means a player is still winning: form, not fatigue | 7% | 9% | barely (0.3%) |
| **New surface**: a player's first few matches on a surface this season | 6% | 6% | barely (0.2%, women only) |
| **"Clutch" records**: break points, tiebreaks, deciding sets, big points. Luck: a good tiebreak record even predicts slightly worse results | 0.6% | 3% | no |
| **Win-loss records**: share of matches, sets and games won. Elo is already made of wins and losses | no | 3% | no |
| **Serving style**: aces, double faults, first serves in. Habits, not match-winners | 0.6% | 2% | no |
| **Player background**: height, handedness, home country, wild card, qualifier | 2% | no | no |
| **Rankings**: official ranking and points; Elo's recent trend. A flaw in the test's early seasons hides them; since 2022 they add a little | no | no | barely (0.3%, women only) |
| **Head to head**: earlier meetings between the two players | no | no | no |

## Which match statistics are skill, and which are luck

The report's chart places each statistic by how consistent a player's figure is from season to season (across) and how much it decides the match it was measured in (up).

* **Observed. Skill, top right:** serve points won, return points won, total points won, holds and breaks are both consistent and decisive. Useful features come from here.
* **Observed. Luck, left:** break points, tiebreaks, even a season's sets won swing with chance.
* **Observed. Habit, bottom right:** aces, double faults and first serves in are consistent but rarely decide a match.

## How much of a match can anyone predict?

* **Observed (Stage 2's estimate).** Replaying every match point by point (main-tour matches with odds, 2022–2026), a coin flip's doubt about the winner splits into three parts:
  * 16% is known before the match (what the bookmakers price);
  * 23% (men) and 24% (women) is how the players play that day;
  * 61% is scoring luck.

  Its method still awaits your approval.
* **Correction.** This decomposition depends on the iid point replay and its denoising assumptions. It does not establish a ceiling for perfect pre-match information or prove that day-level performance is unknowable before play.

## What we suggest next

* **Suggestion. Test the best features together.** The [repaired feature comparison](../feature_alpha_audit/repairs.md) supersedes the original results. Failure of these features would not close the pre-match research route.
* **Suggestion. Try live (in-play) data.** Point observations may help update day-level performance estimates. Testing this needs time-stamped point data and live prices, which this study did not have.
* **Suggestion. Test against the market you would actually bet on.** Polymarket's tennis prices may be less sharp than the bookmakers' closing prices.
* **Suggestion. Fix the known data problems first.** Some players appear under two ids in 2026, and some lower-level scores are misread. The effects here are small, but any rebuild inherits them.

## Decisions for you

1. **Which features to carry forward.** Our suggestion: the strength ratings, recent points won and recent workload.
2. **What to do next:** the combined test, live data, or the Polymarket comparison.
3. **The open technical choices from the earlier stages** (below). None was changed here.

**Open technical choices from the earlier stages**, each set out in its stage's write-up:

* **[Stage 0](stage0.md):** its seven data-cleaning choices, and its [audit's](audit_stage0.md) suggestions.
* **[Stage 1](stage1.md):**
  * merging the women's split identities;
  * the odds-linking rules;
  * keeping the Next Gen ATP Finals;
  * relabelling four WTA 125 events filed as 250s.
* **[Stage 2](stage2.md):**
  * retirements;
  * the luck estimate quoted above;
  * two Grand Slam deciding-set rules;
  * best of five at Wimbledon's last qualifying round;
  * one unreadable box score;
  * whether to study the women's momentum.
* **[Stage 3](stage3.md):** the line for "consistent" that the skill-or-luck chart uses, and freezing the strength ratings' settings.
* **[Stage 4](stage4.md):**
  * the training window (the "flaw in the early seasons" above);
  * the minimum training rule;
  * reading match length from the score;
  * the opponent adjustment's slope;
  * break points above expectation for the men;
  * the women's protected ranking;
  * two cities in the country table;
  * how to read the results;
  * what to carry forward (decision 1 above).

  Also its [audit's](audit_stage4.md) suggestions.
* **This summary:**
  * the two lines that divide the skill-or-luck chart into corners;
  * whether to keep the number check, below, as the standing check after every rebuild.

## How the numbers were checked

* **What was read.** A script ([summary_number_check.py](../../../src/eda/predictability_diagnostic/summary_number_check.py)) read every number on the report page as a browser shows it. That covers every state of every button and menu (183) and every tooltip (9,530 readings): 38,752 numbers, 33,127 of them results. The rest are years, axis labels and the like.
* **How each number was checked.** Each result was tied to its source:
  * 6,679 by a tag naming the exact data-file entry it was printed from;
  * 19,037 by the exact value the page's scripts formatted;
  * 7,405, mostly counts, by value alone.

  Each had to match its source, and its source had to be of the tour, season and level the page says. The 24,226 numbers the page's charts draw from all equal the data files.
* **Observed. Result: none was wrong**, so nothing in the report needed fixing.
* **Self-test.** The script was rerun with deliberate errors planted (the men's and women's figures swapped in four places, two time windows swapped in one). It caught every one, and it flags nothing on the page as built.
* **Limit.** The 7,405 numbers checked by value alone get a weak check: only 16% of one-digit errors among them would be caught. The script also cannot tell a right number from a wrong one of the same tour and season.

## Problems found in earlier work (reported, not fixed)

* stage4.md quotes 3.05 for one gain of the strength ratings (the men's 2013–16 seasons); the data file says 3.04, as the report shows.
* Opened on a phone, Stage 4's menu of rows is wider than the screen.
* The studies index (`docs/studies/README.md`) still describes only Stages 0–1.

## Files

* **Summary figures:** `data/studies/predictability_diagnostic/summary_results.json` (written by `src/eda/predictability_diagnostic/summary_results.py`).
* **Number check:** `summary_number_check.csv`, `.json` and `_selftest.json`.
* **Report section:** `report_summary.py`.
* **Tests:** `test/predictability_diagnostic/test_summary.py`.
