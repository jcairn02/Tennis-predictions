# Summary: ideas borrowed from UFC-predictions

**Status: written 2 Oct 2026, waiting for your review. A study, not a decision.** The same summary opens [report.html](report.html), with the earlier study's summary folded below it for reference. Labels: **observed** is measured, **inferred** is our reading, **suggestion** is a proposal. Every number is read from the stages' output files (`data/studies/ufc_ideas/`); each stage's write-up names its file.

## The short version

The UFC pipeline's tools were rebuilt for tennis and tried on the same 155,130 men's and 60,321 women's matches of 2013–2026 as the predictability diagnostic, with the same walk-forward test, so every number sits on that study's scale: 82 new features in 290 versions, plus 17 models that put them together (99 scored ids, 324 rows, counted by `summary_results.py`).

* **Observed. A Bradley–Terry rating does not replace Elo in tennis.** Tuned on the same seasons, it is worse than surface Elo by 1.60 (men) and 4.45 (women) milli-log-loss, and further from the bookmakers than Elo is. A rating solved from closing odds (MESR) adds nothing to the odds.
* **Observed. Opponent-adjusted statistics beat Elo as much as the serve-and-return ratings did, and the bookmakers not at all.** The best new rows given Elo are Stage B's short-memory IOS points matchup (3.72 men, 5.02 women) and the two-week adjperf of total points won (3.19, 3.32), beside the earlier ratings' 3.61 and 4.58. Everything together adds 9.35 and 9.86 to Elo and 0.31 and 0.32 to the odds.
* **Observed. One lead against the odds: the men's profile of individual statistics.** Twelve opponent-adjusted statistics with a two-week memory (aces, double faults, first serves in, first- and second-serve points won, holds, break points, breaks, returns), almost useless alone, add 0.51 milli-log-loss to the closing odds (−0.05 to 1.07; 0.92 in 2022–2026): the largest gain on the odds in either study, positive in every season from 2020 on (and absent before) and strongest at the 1000s (+1.56). The women's profile adds nothing. The same statistics over 52 weeks, and the long-memory IOS traits, add nothing.
* **Inferred. What the line misses, if anything, is recent form statistic by statistic, not a stable trait.**

## How far each forecast gets

Main-tour matches with bookmaker odds, 2022–2026; a coin flip is 0%, the bookmakers' closing prices 100%:

| Forecast | Men | Women |
|---|---:|---:|
| Official ranking | 48% | 52% |
| Bradley–Terry rating (Stage A) | 77% | 76% |
| Elo rating | 78% | 82% |
| Elo + the earlier best feature | 85% | 86% |
| Elo + everything (Stage D) | 90% | 92% |
| Bookmakers' closing prices | 100% | 100% |

## What each idea did

Each figure is the share of the gap between Elo and the bookmakers that the family's best finding closes, on main-tour matches, as the earlier summary measured it; the report's table unfolds every version.

| Borrowed from UFC-predictions | Men | Women | Beyond the bookmakers? |
|---|---:|---:|---|
| **IOS offence/defence ratings per statistic** (Stage B); the short-memory points matchup leads | 30% | 33% | no |
| **adjperf**: statistics against what each opponent allows, two-week memory (Stage B) | 21% | 23% | barely, single rows (0.27 men, 0.23 women) |
| **The individual-statistic profiles together** (Stage D); the family's best finding is the version that adds back the points-won aggregates | 30% | 31% | **the men's lead: the adjperf profile alone adds 0.51, 0.92 in 2022–26**; women no |
| **Everything together** (Stage D): Bradley–Terry, the ratings, the games-weighted Elo, adjperf, IOS, load, surface, age, credit, with MESR | 54% | 60% | 0.42 (men) and 0.37 (women), ranges reaching zero |
| **Performance split by opponent strength** (Stage B) | 6% | 10% | no; a player's strong-versus-weak gap is chance |
| **adjdef** (Stage B): the mirror of adjperf except on four statistics | 5% | 7% | no |
| **Bradley–Terry rating** (Stage A): as a feature given Elo | small (1.77 men, 0.70 women) | | no; worse than Elo as the base |
| **MESR** from closing odds (Stage A) | no (men) | 17% (MESR minus Elo: what the market thought that Elo did not) | no (−0.03, −0.02) |
| **Strength of schedule** (Stage C) | no | no on the main tour; a finding over every level (quality of wins 0.95) | no |
| **Retrospective credit for old opponents** (Stage C) | no on the main tour (0.16 over every level) | 3% | no |
| **Fatigue** (Stage C): late-match decline, long-match "grinder" | 2% (the grinder, which reads as recent dominance) | 4% | no; the late decline is not a trait |

## What we suggest next

* **Suggestion. Tighten the men's lead before building on it:** a ridge-penalised fit instead of the plain logistic regression, Pinnacle's line in place of the average line, the gain by level and by season, which statistics carry it. Half a milli-log-loss is about half a percent of the way from a coin flip to the odds: a lead, not an edge.
* **Suggestion. Then build the same recent-form profile from point-by-point data**, where the finer individual statistics live (serve direction, rally length, pressure points).
* **Suggestion. Keep surface Elo as the base rating.** Bradley–Terry, MESR, strength of schedule and the retrospective credit do not improve on it: tennis histories are dense and frequent, and a per-player K beats a batch rating with one memory.
* **Suggestion. Close fatigue as a pre-match family.** What fatigue there is shows within a match, not before it.

## Decisions for you

1. Whether to pursue the men's individual-statistic profile, and which tightening comes first.
2. Which inputs to carry forward as the pre-match baseline: our suggestion is surface Elo, the ratings through the iid model and the two-week adjperf profile.
3. The stages' open technical choices, each set out in its write-up:
   * [Stage A](stageA.md): the widened grids; MESR's same-event update; the UFC newcomer anchor against the 2026 split identities; tournament dates as "weeks".
   * [Stage B](stageB.md): the extended adjperf and IOS grids; the diagnostic IOS rows added after the first rundown; adjdef kept for the four unmirrored statistics only; re-tuning IOS on the winner; closing the opponent split; the impossible box score; the time rule by tournament date.
   * [Stage C](stageC.md): the credit for opponents lost to; normalising Stage 0's dates to Mondays; closing fatigue; the grinder's constant; the K grid; a rerun with Stage A's rating.
   * [Stage D](stageD.md): the order of the tightening; the baseline; closing the long-memory IOS ratings and the products as market features.

## Problems found in the earlier study's data (reported, not fixed)

* Tournament dates that are not Mondays (26,019 of 872,704 matches; 287 evaluation-level events), which the time rule treats as weeks of their own; in a few matches a mid-week event can see a same-week result.
* One women's box score with impossible break-point counts (W15 Malta 2025), which breaks a batch solve of break points saved until it is left out.
* Implausible minutes in 123 matches.
* The 2026 split identities hurt any rating with a newcomer prior far more than Elo.

## Files

* The stages' code, tests, outputs and write-ups are listed in the [README](README.md).
* The summary's numbers: `data/studies/ufc_ideas/summary_results.json` (`src/eda/ufc_ideas/summary_results.py`); the page: `src/eda/ufc_ideas/render_report.py`.
