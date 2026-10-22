# The men's lower-level matches are in: 4,345 results fill holes in Challenger and ITF seasons

16 October 2026 · For the owner · Status: **done and in use**: on bet days from 14:25, in the model's training from
17:58, when the daily runs switched to the rebuilt model (decision of 14 Oct 2026,
[record](../../decisions/2026-10-14-lower-level-gap-fills.md), section "The third package") · [Process log](process_log.md)

## What you asked

> "Add the men's 4,246 matches now"

The women's half of the same message has its own page: [the women's model to-do list](../womens_model/to_do.md).

## What was done

1. **Built fresh from today's downloads**, as I said it would be, rather than copied from the 10 October batch.
   * Men only.
   * **Results only.** Who played whom, when, at what level, and who won, with no serve or return statistics.
   * **Dated where the weekly feed does not reach.** The feed already brings men's Challengers from 1 January 2026
     and men's ITF from 1 June 2026, so this package stops just before those dates.
2. **It passed the entry tests** of your 14 October rule (below), so I registered it at 14:25 without a separate
   decision. Bet-day runs use it from now on.
3. **A rebuild is running, started at 14:28.** It retrains the model on today's tables with this package and everything
   accepted since 14 October.
   * Then the harm check compares the new instance with the one in use now. Its rule was fixed before the build: harm
     means worse by more than 0.10 mLL per match, with the whole 95% range below zero.
   * **No harm:** the daily runs switch to the new instance by themselves tonight. The switch is checked first: a
     past day is re-run through the daily pipeline, and its inputs must equal the new instance's.
   * **Harm:** nothing switches, and the decision is yours.
   * The result is in the section "Tonight's rebuild" below: no harm, and the switch was made at 17:58.

## What went in

| Level | Matches | Seasons |
|---|---:|---|
| ITF main draws | 3,372 | 2017–May 2026; 1,742 of them in 2025, 739 in 2018 |
| Challenger qualifying | 953 | 2018–2025 |
| Challenger main draws | 20 | 2019 and 2023 |
| **Total landing on today's tables** | **4,345** | |

The package holds 4,376. The other 31 are Challenger matches our tables already have, so the merge skips them.

**Why 4,345 and not the 4,246 I quoted this morning.** This morning's count treated two players meeting at the same
level within 10 days as one match. Today I checked those pairs one by one. They are real rematches a week apart, at ITF
venues that host the same event in back-to-back weeks (Tabarka, Monastir, Maanshan and the like). That rule had wrongly
dropped 124 of them. The two builds also differ by 25 matches the other way.

**How much it moves the model: very little, as I said before.**
* The ratings count these results as they count those levels already:
  * Challenger results count in full;
  * Challenger-qualifying results count at most in full;
  * ITF results count at a quarter.
* The "matches played recently" counts take every match.
* Only 749 of the 35,319 men's main-tour matches the model trains on have a player who gains a match in the year
  before. Only 41 gain one in the four weeks before.
* Women are untouched.
* Expect no measurable change in betting results. This is housekeeping, not an edge.

## How I know it's right

* **It fills holes, not new ground.** Your rule asks that each season it touches already holds at least as many matches
  as it adds, or be catching up with its neighbours. All 19 level-and-season groups pass the first test easily. The
  tightest is Challenger qualifying 2019, which holds 271 matches and gains 24. ITF 2025 gains the most: 1,742 on top
  of 17,870.
* **No double counting.** The merge already skips a match it holds under the same id, or the same two players in the
  same round within 3 days. I went further.
  * I listed every added match whose two players also meet in our tables within 14 days, at any round or level: 167.
  * Every one is exactly 7 or 14 days apart, and 166 have a different score.
  * The 3 with the same score are separate events: the players' other opponents that week differ at every round.
* **The right players.**
  * The matching rules passed: at most 5% of the sampled links were uncertain, against a limit of 25%.
  * I also checked by hand the 20 sampled cases where a new match was attached to a player we already had under a
    different spelling. All 20 are the same person, for example "Wei Qiang Zheng" and "Weiqiang Zheng". Two are likely
    but not certain: Junhyun and Junhyeon Lee of Korea, and Mohammed and Mhamed Affes of Tunisia, with one match each.
* **It reproduces exactly.** Merged onto the frozen 8 October tables, the package gives the checked build's tables, row
  for row.

## Tonight's rebuild

**Done: the daily runs use the new model (`template_2026-10-16`) from 17:58.** It is trained on today's tables, with
these matches and everything accepted since 14 October.

* **The harm check passed.** The new model against the one it replaces, on 31,722 matches of 2020–2026: **+0.007 mLL
  per match** (95% range −0.025 to +0.039; positive means the new one is better). That's unresolved, with P(better)
  0.66, and far from the harm line (worse by more than 0.10 with the whole range below zero).
  * **Other readings, which don't decide:**
    * men +0.034 (P(better) 0.91);
    * women −0.023 (P 0.14);
    * 2025–26 +0.035 (P 0.86).
  * **One slice reads worse:** women's 2024, −0.125, with its range clear of zero. It is one of 21 season slices, and
    about one in twenty lands outside its range by chance. Noted for the women's list.
* **The input check: one new warning out of 58 inputs, explained.**
  * The men's surface offset is the input saying how much better or worse a player is on this surface than overall.
  * Each rebuild re-tunes how fast it moves, on 2013–2018. With about 950 extra men's 2018 matches in that history,
    the tuning picked a different setting.
  * That shifts the input slightly in every men's season, and narrows its spread a little more in later seasons.
  * The men's main Elo inputs barely moved.
* **The switch check passed.** A past day (the round of 16 of 13 July) was re-run through the daily pipeline. Every one
  of its 23 matches got the same inputs as the model was trained on, to within 0.000005, the same as on 14 October.
  * My script first undid the switch: a bug in its own safety check pointed it at a file path Windows can't read.
  * I confirmed the check had passed and completed the switch by hand.
* **Everything finished at 18:37.** The new model's bet-day checkpoint was ready at 18:10. The extra fits for
  16-seed evaluations ended at 18:37, so the graphics card is free and prediction runs are fine.
* **The script's path bug is fixed**, and the fixed check passes on tonight's replay.

**Earlier in the evening:**

* **It stopped once, at 15:21, and was resumed at 15:28.**
  * The model builder includes a test that the inputs never use future results. It replaces later results with
    random numbers, drawing "points won" and "points played" separately, so it can make impossible matches such as
    400 points won out of 3.
  * One such match gave a rating a weight in the hundreds, and the Elo formula overflowed. The earlier builds passed
    only because their random draws missed that case.
  * **The fix:** the formula's exponent is capped. Real ratings never come near the cap: it sits at a 120,000-point
    gap, and real inputs stay within about 7 on its scale of 300. So every real input is unchanged, to the last bit.
    A new test reproduces the old failure.

## Things I found on the way (not caused by this package)

* **Replays of past days currently fail.** A replay is the end-to-end check that re-runs a past day through the daily
  pipeline. Another session's replay failed this afternoon.
  * The cause: since 14 October, Tennis My Life has published 43 matches that the weekly feed had already added under
    the same ids. A replay rebuilds the history from Tennis My Life's 8 October files, which lack them, while it copies
    the newer timeline, which has them. They end up counted twice, and the run stops.
  * Bet-day runs don't use the old files, so they are fine.
  * Tonight's switch check uses a copy of Tennis My Life's files as of 14 October, which matches the tables.
  * The notebook's own replay check still used the 8 October files. I told the session that ran into it.
* **Replays against the instance in use since 14 October couldn't be exact anyway.** 2,110 of the feed's current matches
  arrived after that instance was built, and an exact replay requires the instance to know every match. This happens
  each time accepted data grows after a build; tonight's rebuild resets it.
* *Update, 15:06: both are now fixed by that session (at your request).* Replays use each model instance's own copy
  of Tennis My Life's files and its own list of accepted packages. Its proof run passed.
* **One project test fails, and it is unrelated.** It checks that every event name in the tables has a country in the
  model builder's country list. A recently added event name is missing from that list, so the list needs that name
  added.

## Files

* **The package:** `data/studies/current_best_model/accepted_additions/men_lower_level_fill/` (listed in
  `accepted.json`).
* **The evidence:** `data/studies/men_lower_level_fill/`.
  * `package/c2_new_matches.csv` and `.json`: the entry test per level and season.
  * `package/near_pairs.csv`: the 167 nearby same-pair meetings.
  * `check_against.log`; `screen_MLF20261016.log`: the matching rules.
  * The build, derive and check logs.
* **The builds:** `C:/Users/zerom/tnr_mlf/candidates/` (`MLF20261016`, the whole download; `MLF20261016_pkg`, the men's
  part). They sit outside the repository, as the feed's do.
* **The rebuild:** `data/studies/current_best_model/template_2026-10-16/` (sandbox `C:/Users/zerom/tnr_tpl1016`); the
  harm check in `data/studies/men_lower_level_fill/harm/`.
* **Code:** `src/eda/men_lower_level_fill/` (the entry test for added matches with the duplicate listing, the harm
  check); tests in `test/men_lower_level_fill/`; the scripts `build_candidate.sh`, `package_steps.sh`,
  `build_template.sh` and `resume_build.sh` in the evidence folder.
* **The builder fix:** `src/eda/predictability_diagnostic/stage4_features.py` (`EXP_CAP` in `weighted_elo_pass`); its
  test in `test/predictability_diagnostic/test_stage4.py`.
