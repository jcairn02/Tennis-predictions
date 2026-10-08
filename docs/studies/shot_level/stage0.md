# Stage 0: what the shot-level data holds, and what it could detect

**Status: built 2 Oct 2026, waiting for the owner's review.** A study stage, not a decision. The Brief and the stage table are in the [README](README.md). Nothing in this stage was compared with who won: it counts fields, links and matches, and turns counts into the smallest gain a later test could detect.

Labels: **observed** is measured on the data, **inferred** is a reading of measurements, **suggestion** is a proposal for the owner. Every number comes from `data/studies/shot_level/stage0_summary.json` (written by `src/eda/shot_level/stage0_summary.py` from `stage0_sources.json`, `stage0_coverage.csv` and `stage0_coverage.json`). Numbers quoted from earlier studies name their write-up.

## In short

* **Observed. The statistics used so far are match totals, not point-by-point or shot-level.** Every feature in both earlier studies was built from nine box-score fields (aces, double faults, serve points, first serves in, first- and second-serve points won, service games, break points saved and faced) and the score. Three features read point-by-point sequences, all from the Grand Slam files: Stage 2's big-point analysis, Stage 4's big-point play on return, and the UFC study's late-match decline. None read a single shot-level field.
* **Observed. The shot-level data on disk is larger than a small slice.** Ten sources hold 82,100 matches of the earlier studies' match table, 2010–2026. Every one of them links at over 90% from 2010 except TDI (67%). The volunteer charts, the four Grand Slams' feeds and the ATP's 2021–2024 match-centre files are the bulk.
* **Observed. On the main tour, most matches with closing odds could carry a shot-level feature.** Require both players to have at least 3 earlier matches with the fields in the last 52 weeks. Then 79% of the men's and 75% of the women's matches with odds qualify (2013–2026), and 95% and 96% in 2022–2026. Rally length alone qualifies 63% and 52% (92% and 72% in 2022–2026); ball tracking 27% and 5%.
* **Observed. That is enough to detect a gain of about one milli-log-loss on the odds, not half of one.** Over 2013–2026, one shot-level statistic would need to improve on the closing odds by 0.75–1.22 milli-log-loss for the men and 0.77–1.67 for the women, depending on the family (ball tracking aside). At that size a test finds the gain 80% of the time. A profile of many statistics would need 1.35–2.18 and 1.39–2.99. In 2022–2026 alone, one statistic would need 1.61–2.03 and 1.70–3.17.
* **Observed. Under the feature-alpha audit's repaired rules the picture holds.** Those rules count only matches with a confirmed match day, as history and as targets, and they were finished on the same day as this stage. Under them, 78% (men) and 81% (women) of the matches with odds from 2019 on are scorable. The detectable gain there is 1.29–1.64 (men) and 1.34–2.50 (women) for one statistic of the broad families (rally length, endings, speed, net play). The box-score profile's lead, repaired, is 0.36 milli-log-loss beyond Pinnacle's line, with an interval from −0.25 to 0.96 ([repairs](../feature_alpha_audit/repairs.md)). That is well below what this data could detect.
* **Inferred. The constraint is the number of matches with odds, not the shot-level data.** More shot-level data cannot add many scorable matches on the main tour. At most it adds the 21% (men) and 25% (women) of matches with odds not yet covered. That would lower the detectable gain by the same shares. What more data would add is recency, the women's rally-level detail, ball tracking, and Challenger matches (which have no odds).
* **Suggestion. Test what is on disk before finding or buying more.** The [candidate list](candidates.md) proposes 14 statistics in two memories, tested as profiles against the closing odds and against the box-score profile on the same matches.

## Terms used here

* **Shot by shot.** Every stroke of every point: the serve and where it went, each return and rally shot (forehand or backhand, direction, depth), and how the point ended. Volunteers chart it from video (the Match Charting Project), or Hawk-Eye cameras track the ball (Court Vision).
* **Annotated point by point.** Every point in order with who served and won, plus some of: how many shots it lasted (**rally length**), how it ended (**winner**: a shot the opponent did not reach; **unforced error**: a missed shot under no pressure; **forced error**: a miss caused by the opponent's shot), serve speed, where the serve landed (**placement**: wide, body or T, the centre line), whether a player came to the net, how deep the return landed.
* **Match totals.** Counts over a whole match, as in a box score. The WTA's advanced statistics are match totals of shot-level counts (winners, errors, net approaches).
* **Families.** The eight kinds of shot-level field a source can carry: rally length, how points end, serve speed, serve placement, net play, return depth, stroke mix (forehand, backhand, slice, volley), and ball tracking. A match **carries** a family when at least half its points have the field: 40% for endings, speed, placement, return depth and stroke, any net point for net play. Thresholds are in `stage0_sources.json`.
* **Linked.** Matched to a match of the predictability diagnostic's Stage 0 table, by the data map's linker: the same tour, the same pair of surnames and a date in the window, with fallbacks for married or shortened names. **Oriented**: which source player is which Stage 0 player; every linked match was oriented.
* **Scorable match, memory, k.** A pre-match feature exists for a match when both players have at least k earlier matches carrying the family within the memory: the whole career, the last 52 weeks, or the last 13 weeks. "Earlier" follows the earlier studies' time rule: earlier events and earlier rounds of the same event.
* **Matches with odds.** Evaluation matches with closing odds: tour-level main draws (Grand Slams to 250s), 2013–2026: 31,683 men's and 32,178 women's (12,352 and 11,467 in 2022–2026).
* **Log loss, milli-log-loss.** As in the earlier studies: minus the log of the probability given to the winner, averaged; a coin scores 0.693; one milli-log-loss is 0.001.
* **Detectable gain.** The smallest improvement on the closing odds, in milli-log-loss, that a test on the scorable matches would find 80% of the time at the usual 5% threshold (below).

## What the earlier studies used

**Observed** (from the code's constants; `stage0_summary.json`, `earlier_studies`).

* Stage 0 of the predictability diagnostic keeps nine box-score fields per player (`common.BOX`): `ace`, `df`, `svpt`, `first_in`, `first_won`, `second_won`, `sv_gms`, `bp_saved`, `bp_faced`. The per-match statistics of both studies are built from them and the score:
  * the 16 rates of `common.RATES`: serve, return and total points won, holds, breaks, aces, double faults, first serves in, first- and second-serve points won, break points saved, converted and faced per game, tiebreaks, sets and games won;
  * a few more from the same fields: return points won against the first and the second serve, break points won above expectation, deciding sets, head to head.
* The ratings, adjperf, adjdef, IOS, Bradley–Terry, strength of schedule and the profiles are all built from those rates or from results.
* Point-by-point sequences enter three places, all from Sackmann's Grand Slam files: Stage 2's big-point analysis, Stage 4's "big-point play on return", and the UFC study's Stage C "late-match decline".
* No feature in either study reads rally length, how a point ended, serve speed or placement, net play, return depth, stroke type or ball tracking.

## The sources

**Observed** (`stage0_summary.json`, `sources`). Linked counts by family are of matches linked to Stage 0 that carry the family.

| Source | Tours | Years linked | Matches read (from 2010) | Linked (share from 2010) | Points | Rally | Ending | Speed | Placement | Net | Return | Stroke | Tracking |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Match Charting Project (volunteer charts) | both | 2010–2026 | 9,429 | 9,336 (99.0%) | 1,438,299 | 9,306 | 9,306 | 0 | 9,306 | 9,291 | 8,421 | 9,305 | 0 |
| Grand Slam point-by-point (Sackmann's copies of the IBM and Infosys feeds) | both | 2011–2024 | 10,508 | 10,470 (99.6%) | 1,922,136 | 6,710 | 10,460 | 8,103 | 4,136 | 8,443 | 3,653 | 17 | 0 |
| Wimbledon and US Open feeds (IBM SlamTracker) | both | 2019–2026 | 5,162 | 4,938 (95.7%) | 881,597 | 3,839 | 4,920 | 3,226 | 3,553 | 4,920 | 3,535 | 5 | 0 |
| Australian Open and Roland Garros Court Vision (hawkilol copy) | both | 2019–2024 | 2,027 | 2,021 (99.7%) | 503,586 | 1,973 | 2,021 | 1,897 | 1,765 | 0 | 1,700 | 1,716 | 1,221 |
| Australian Open match centre | both | 2020–2026 | 532 | 532 (100%) | 74,567 | 0 | 532 | 0 | 0 | 0 | 0 | 532 | 0 |
| ATP Infosys match centre (Hugging Face handoff) | men | 2018–2025 | 37,908 | 36,876 (97.3%) | 4,437,046 | 4,936 | 6,312 | 6,028 | 0 | 6,311 | 0 | 6,308 | 0 |
| ATP Court Vision (Hugging Face handoff) | men | 2018–2024 | 4,570 | 4,463 (97.7%) | 903,596 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4,402 |
| SirGenkii infotennis (ATP, Jan–Apr 2025) | men | 2025 | 922 | 902 (97.8%) | 136,928 | 902 | 902 | 365 | 902 | 52 | 0 | 902 | 0 |
| TDI Tennis Results (ATP and Challenger) | men | 2025–2026 | 4,698 | 3,146 (67.0%) | 665,504 | 3,084 | 3,086 | 0 | 0 | 3,076 | 0 | 3,086 | 0 |
| WTA official API, advanced statistics (match totals) | women | 2021–2026 | 24,309 | 22,130 (91.0%) | totals | 0 | 19,018 | 0 | 0 | 6,215 | 0 | 6,372 | 0 |

**Observed, per source** (`stage0_sources.csv` gives every source by tour and year).

* **Infosys.** Its 4.4 million points annotate fully only at tour level, and only for 4,936 matches: 113 in 2021, then 1,207, 1,561 and 2,033 in 2022–2024, and 22 in 2025. Annotated means points grouped by the shot that ended them (serve, return, 3rd … 8th, "9+ odd", "10+ even"), how they ended, serve speed and net flags. At Challengers every point that is not an ace or a double fault sits in an unnamed group, with no rally length and no ending. The per-set key statistics add match totals of winners, unforced errors, net points won and serve speeds; with them, 6,312 matches carry endings.
* **Grand Slam files.** Rally counts are missing at all four Slams in 2012–2015 and partly in 2016. Serve placement is filled in 2011 and from 2016, return depth from 2016. Serve speed is filled on 8,103 of the 10,470 linked matches.
* **Grand Slam main draws, all sources together** (`grand_slam_main_draw_carrying_share`). From 2018, at least 98% of each Slam's main-draw matches carry a family, with these exceptions:
  * the Australian Open 2025: 39%, mostly volunteer charts (81 of its 254 main-draw matches), plus 14 in SirGenkii's files and 6 match-centre captures;
  * Roland Garros 2022–2026: 89%, 51%, 56%, 27% and 9%. The Court Vision copy covers 2022–2024 only, and only the charts cover 2025–2026;
  * the US Open 2018: 70%.

  In 2011–2017, coverage was 46–100%, depending on the Slam and year.
* **Wimbledon and US Open feeds.** These repeat Sackmann's Slam files for 2019 and 2021–2024 and add 2025–2026, where every field is filled. Forced errors are not flagged in these feeds, so endings are read from winners, unforced errors, aces and double faults.
* **WTA advanced statistics.** The files of 2021 are empty of shot counts. Winners and unforced and forced errors are filled from 2022, net approaches and the forehand–backhand split from 2025. The WTA's point-by-point batch, still downloading, carries only server, point winner and score, so it adds no shot-level field (one file checked).
* **TDI.** Its unlinked third is mostly Challenger qualifying after June 2026 and matches after 21 September 2026, neither in Stage 0.
* **Not read here.** The 2,147 men's Tennis Abstract charts that exist only on the website (point logs as prose, not parsed); Flashscore's per-set statistics (winners and unforced errors on 6–10% of matches; not linked); the 2019–2021 Court Vision files of the Slam copy (not downloaded).

## On how many matches could a shot-level feature be scored?

**Observed** (`stage0_summary.json`, `coverage`). Matches with odds where both players have at least 3 earlier matches carrying the family. Detectable gains in milli-log-loss, for one statistic and for a profile of many (next section).

| Tour | Family | 52 weeks, 2013–2026 | One statistic | Profile | 13 weeks, 2013–2026 | 52 weeks, 2022–2026 | One statistic | Profile | 13 weeks, 2022–2026 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Men | rally length | 19,990 of 31,683 (63%) | 0.94 | 1.68 | 10,870 (34%) | 11,337 of 12,352 (92%) | 1.65 | 2.96 | 7,544 (61%) |
| Men | how points end | 24,986 (79%) | 0.75 | 1.35 | 13,177 (42%) | 11,673 (94%) | 1.61 | 2.88 | 8,406 (68%) |
| Men | serve speed | 18,877 (60%) | 0.99 | 1.78 | 8,224 (26%) | 10,516 (85%) | 1.78 | 3.20 | 6,384 (52%) |
| Men | serve placement | 16,508 (52%) | 1.14 | 2.04 | 6,203 (20%) | 9,854 (80%) | 1.90 | 3.41 | 4,252 (34%) |
| Men | net play | 23,560 (74%) | 0.80 | 1.43 | 11,032 (35%) | 11,398 (92%) | 1.65 | 2.95 | 7,225 (58%) |
| Men | return depth | 15,438 (49%) | 1.22 | 2.18 | 4,551 (14%) | 9,228 (75%) | 2.03 | 3.64 | 2,802 (23%) |
| Men | stroke mix | 15,884 (50%) | 1.18 | 2.12 | 8,754 (28%) | 11,146 (90%) | 1.68 | 3.02 | 7,585 (61%) |
| Men | ball tracking | 8,511 (27%) | 2.20 | 3.95 | 4,581 (14%) | 8,422 (68%) | 2.23 | 3.99 | 4,497 (36%) |
| Men | any | 24,999 (79%) | 0.75 | 1.34 | 13,186 (42%) | 11,684 (95%) | 1.60 | 2.88 | 8,410 (68%) |
| Women | rally length | 16,876 of 32,178 (52%) | 1.11 | 1.99 | 4,871 (15%) | 8,272 of 11,467 (72%) | 2.27 | 4.06 | 2,192 (19%) |
| Women | how points end | 24,221 (75%) | 0.77 | 1.39 | 14,057 (44%) | 11,062 (96%) | 1.70 | 3.04 | 10,124 (88%) |
| Women | serve speed | 14,197 (44%) | 1.32 | 2.37 | 2,444 (8%) | 5,924 (52%) | 3.17 | 5.67 | 885 (8%) |
| Women | serve placement | 13,862 (43%) | 1.35 | 2.42 | 3,757 (12%) | 8,189 (71%) | 2.29 | 4.11 | 2,322 (20%) |
| Women | net play | 20,975 (65%) | 0.89 | 1.60 | 7,538 (23%) | 9,356 (82%) | 2.00 | 3.59 | 4,551 (40%) |
| Women | return depth | 13,680 (42%) | 1.37 | 2.46 | 3,660 (11%) | 8,142 (71%) | 2.30 | 4.13 | 2,259 (20%) |
| Women | stroke mix | 11,233 (35%) | 1.67 | 2.99 | 4,757 (15%) | 7,839 (68%) | 2.39 | 4.29 | 4,147 (36%) |
| Women | ball tracking | 1,644 (5%) | 11.41 | 20.45 | 258 (1%) | 1,644 (14%) | 11.41 | 20.45 | 258 (2%) |
| Women | any | 24,227 (75%) | 0.77 | 1.39 | 14,058 (44%) | 11,062 (96%) | 1.70 | 3.04 | 10,124 (88%) |

**Observed. Where it comes from** (`by_group_market_52w_k3`): the scorable matches of 2013–2026 with each group of sources alone.

| Tour | Family | All sources | Grand Slam feeds | ATP feeds (Infosys, Court Vision, SirGenkii, TDI) | Volunteer charts | WTA advanced statistics |
|---|---|---:|---:|---:|---:|---:|
| Men | rally length | 19,990 | 13,264 | 9,300 | 10,663 | – |
| Men | how points end | 24,986 | 21,070 | 9,829 | 10,663 | – |
| Men | serve speed | 18,877 | 15,024 | 9,257 | 0 | – |
| Men | ball tracking | 8,511 | 2,027 | 8,216 | 0 | – |
| Women | rally length | 16,876 | 12,972 | – | 7,368 | 0 |
| Women | how points end | 24,221 | 20,239 | – | 7,368 | 10,686 |
| Women | serve speed | 14,197 | 14,197 | – | 0 | 0 |
| Women | net play | 20,975 | 15,057 | – | 7,336 | 3,400 |

* **Observed.** The Grand Slam feeds carry the most: alone, they make 67% (men) and 63% (women) of the matches with odds scorable for some family (`group_shares_market_52w_k3`). Nearly every main-tour player plays the four Slams, and almost every Slam main-draw match since 2018 has an annotated record (above). The volunteer charts reach 34% (men) and 23% (women), because they concentrate on the leading players' matches. The ATP feeds reach 31% of the men's, almost all of it 2021–2024.
* **Inferred.** For many players the 52-week shot-level history is their last few Slams. Such a feature measures a style over months, not recent form. The 13-week columns show how much recent history exists: 34% (men) and 15% (women) of matches with odds for rally length.

**Observed. Under the audit's repaired rules** (`coverage`, the `repaired_*` cells). The audit's corrected rebuild ([repairs](../feature_alpha_audit/repairs.md)) changes two things:

* It accepts a match only with a provider match day it can confirm: 78,714 of Stage 0's 872,704 matches, nearly all main-tour main draws.
* It lets only accepted matches enter history, ordered by match day (earlier days, and earlier rounds of the same event on the same day).

Here the same count is run under those rules (`repaired_rows` in `stage0_coverage.py`). The audit scores its market comparisons from 2019 on.

| Tour | Family | 52 weeks, 2013–2026 | 52 weeks, 2019–2026 | One statistic | Profile | 13 weeks, 2019–2026 | 52 weeks, 2022–2026 |
|---|---|---:|---:|---:|---:|---:|---:|
| Men | rally length | 17,624 of 31,496 (56%) | 14,176 of 18,563 (76%) | 1.32 | 2.37 | 8,202 (44%) | 10,006 of 12,286 (81%) |
| Men | how points end | 22,601 (72%) | 14,500 (78%) | 1.29 | 2.32 | 8,884 (48%) | 10,327 (84%) |
| Men | serve speed | 17,145 (54%) | 11,422 (62%) | 1.64 | 2.94 | 5,965 (32%) | 9,371 (76%) |
| Men | net play | 20,542 (65%) | 12,446 (67%) | 1.51 | 2.70 | 6,953 (38%) | 9,774 (80%) |
| Men | ball tracking | 7,464 (24%) | 7,464 (40%) | 2.51 | 4.50 | 3,833 (21%) | 7,394 (60%) |
| Men | any | 22,601 (72%) | 14,500 (78%) | 1.29 | 2.32 | 8,884 (48%) | 10,327 (84%) |
| Women | rally length | 15,321 of 32,006 (48%) | 11,201 of 17,285 (65%) | 1.68 | 3.00 | 3,210 (19%) | 7,218 of 11,395 (63%) |
| Women | how points end | 22,569 (70%) | 13,967 (81%) | 1.34 | 2.41 | 9,258 (54%) | 9,984 (88%) |
| Women | serve speed | 13,382 (42%) | 7,490 (43%) | 2.50 | 4.49 | 1,225 (7%) | 5,294 (46%) |
| Women | net play | 18,570 (58%) | 10,393 (60%) | 1.80 | 3.23 | 4,101 (24%) | 7,638 (67%) |
| Women | ball tracking | 1,579 (5%) | 1,579 (9%) | 11.88 | 21.29 | 236 (1%) | 1,579 (14%) |
| Women | any | 22,573 (70%) | 13,967 (81%) | 1.34 | 2.41 | 9,258 (54%) | 9,984 (88%) |

**Observed.** The repaired rules lower the 2013–2026 shares by up to 9 percentage points (net play, men: 74% to 65%). History loses the qualifying and lower-level matches, and targets lose the matches without a confirmed day. The order of the families stays the same. The other families (placement, return depth, stroke mix) are in `stage0_summary.json`.

**Observed. By season** (`by_season_market_52w_k3`; the share of matches with odds, 52 weeks, k = 3).

| Season | 2013 | 2014 | 2015 | 2016 | 2017 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Men, rally length | 0.09 | 0.09 | 0.18 | 0.38 | 0.66 | 0.85 | 0.75 | 0.75 | 0.88 | 0.91 | 0.95 | 0.94 | 0.90 |
| Men, ball tracking | 0 | 0 | 0 | 0 | 0 | 0.00 | 0 | 0.03 | 0.76 | 0.83 | 0.87 | 0.72 | 0 |
| Women, rally length | 0.04 | 0.07 | 0.23 | 0.22 | 0.53 | 0.77 | 0.70 | 0.69 | 0.73 | 0.69 | 0.76 | 0.73 | 0.68 |
| Women, how points end | 0.48 | 0.54 | 0.69 | 0.65 | 0.56 | 0.77 | 0.70 | 0.69 | 0.95 | 0.97 | 0.98 | 0.97 | 0.95 |

(The men have no 2018 odds file; the women's 2018 rally share is 0.66.)

**Observed. By level** (`by_level_evaluation_52w_k3`; the share of all evaluation matches, any family, 52 weeks, k = 3). Men: Finals 0.95, 1000s 0.90, 500s 0.84, Grand Slams 0.79, 250s 0.70, tour qualifying 0.26, Slam qualifying 0.22, Challenger 0.13, Challenger qualifying 0.01. Women: Finals 1.00, 1000s 0.88, 500s 0.85, Grand Slams 0.79, WTA 125 0.66, 250s 0.60, tour qualifying 0.31, Slam qualifying 0.32, WTA 125 qualifying 0.29. **Inferred:** a shot-level study is a main-tour study. Below it the data is thin, and below it there are no odds.

## What gain could such a test detect?

**The formula (inferred from the arithmetic; checked by simulation in `test_stage0.py`).** Add a standardised feature with true coefficient β to a calibrated forecast p. The expected log loss improves by G = β² v / 2 nats per match, with v the average of p(1 − p). The per-match improvement has standard deviation |β| √v. So a test on n matches has z = |β| √(v n) / 2, and the gain it detects with 80% power at the two-sided 5% level is **G = 2 (1.96 + 0.84)² / n**, whatever v is. For 10,000 matches that is 1.57 milli-log-loss.

**The inflation (observed, `stage0_coverage.json`, `inflation`; rows in `stage0_inflation.csv`).** Real walk-forward fits are noisier than the formula. Compare the earlier rundowns' market intervals with the formula's standard error, on rows with a positive gain:

* single-input rows: 1.09 times wider (median of 49 rows);
* multi-input models: 1.46 times wider (median of 19 rows). Stage D's seven profile models with a positive gain alone: 2.36 (median), up to 3.01 (`inflation_by_source`);
* the audit's intervals clustered by calendar week: 1.06 times wider than the formula (median of 243 rows).

The detectable gain grows with the square of the inflation.

| Scorable matches | Formula alone | One statistic (× 1.09) | Profile (× 1.46) |
|---:|---:|---:|---:|
| 5,000 | 3.14 | 3.75 | 6.72 |
| 10,000 | 1.57 | 1.88 | 3.36 |
| 20,000 | 0.79 | 0.94 | 1.68 |
| 30,000 | 0.52 | 0.63 | 1.12 |

**Inferred, against what is known.**

* The men's box-score profile adds to the odds:
  * 0.51 milli-log-loss over all scored seasons and 0.92 in 2022–2026, as first measured ([Stage D](../ufc_ideas/stageD.md));
  * 0.86 to the calibrated average line and 0.79 to Pinnacle's on 16,776 matches from 2019 in the audit ([audit](../feature_alpha_audit/README.md));
  * 0.40 and 0.36 after its repairs, on 16,333 matches, both intervals reaching below zero ([repairs](../feature_alpha_audit/repairs.md)).

  A shot-level profile of that size would be detected less than half the time on the shot-level coverage.
* A shot-level statistic that adds **1 milli-log-loss or more** would be seen over 2013–2026 for rally length, endings, speed and net play (both tours), and **about 2 or more** in 2022–2026 alone.
* A family-wide line across about 40 rows (the multiple-comparisons guard, z = 3.23) multiplies every threshold by 2.11 (`family_wide_over_single`; `mde_family_wide` in `stage0_coverage.csv`). One statistic over 2013–2026 would then need 1.59–2.57 (men) and 1.64–3.53 (women).
* Ball tracking is too thin to test against the odds: 2.2 milli-log-loss for one men's statistic, 11.4 for the women's.
* Profiles cost more than single statistics. An unpenalised fit of k inputs on n training matches loses about k / (2n) nats per match out of sample: 16 inputs on 5,000 matches cost 1.6 milli-log-loss. This is the arithmetic of the maximum-likelihood fit (an inference). Profiles on the shot-level coverage need few inputs or a ridge penalty.

## What this means for finding or buying more data

* **Inferred. More shot-level data cannot add many matches with odds.** On the main tour, 79% (men) and 75% (women) of the matches with odds already qualify (2013–2026; 95% and 96% in 2022–2026). Covering every remaining match would raise n by 27% (men) and 33% (women), and lower the detectable gain by 21% and 25% (`headroom_any_52w_k3`). The binding limit is the closing odds, which exist only for main-tour main draws.
* **Inferred. What more data would add is quality, not quantity:**
  * **Recency.** Rally length has 13-week history in 34% (men) and 15% (women) of matches with odds. The men's lead is a two-week memory.
  * **The women's rally-level detail.** Only the Slam feeds and the volunteer charts carry it. The WTA's point-by-point batch does not.
  * **The men's tour-level gap** of April 2025 to June 2026, between SirGenkii's files and TDI's window.
  * **Ball tracking**, and **Challenger matches** (which have no odds, so they would help only a test against Elo).
* **Suggestion.** Run the candidate list on what is on disk first. Look for more data, or pay for it, only if Stage 2 finds a gain on the odds, and then target the gap it points to (recency, women's rallies, tracking).

## What was built

| File | What it holds |
|---|---|
| `stage0_source_matches.parquet` (3.8 MB) | One row per source match (102,466): source, key, names, date, round, points, the per-family point counts and carried flags, the Stage 0 match and orientation; Infosys's rally-length groups per match |
| `stage0_sources.csv`, `stage0_sources.json` | Per source, tour and year: matches read, linked, oriented, points, carrying each family, linked and carrying; the reading notes and thresholds |
| `stage0_coverage.csv` | Tour × family (and any) × source group × memory × k × subset (all evaluation matches, matches with odds, matches with odds 2022–2026), with seasons and level groups for some cells: eligible, scorable, share, detectable gains (formula, one statistic, profile, profile clustered, family-wide) |
| `stage0_inflation.csv` | The earlier rundowns' and the audit's market rows: observed standard error against the formula's |
| `stage0_coverage.json`, `stage0_summary.json` | The inflation summary, the headline counts, and every number quoted here; `inputs` records the earlier studies' tables and code read, with hashes |
| `stage0_tables.md` | This write-up's tables, generated from `stage0_summary.json` (`stage0_summary.py`, `write_tables`) |

Code in `src/eda/shot_level/`: `common.py` (the families, the source register, the link to Stage 0, the detectable-gain formula), `stage0_sources.py` (every source read and linked; under 2 minutes with 5 workers), `stage0_coverage.py` (about a minute), `stage0_summary.py` (seconds). Tests: `test/shot_level/test_stage0.py`, 14 tests, all passing. They cover the shot-string parser on hand-made charts, the orientation and the linker's window and married-name fallback, the time rule on a hand-made history, the formula against a simulation, and that the pool is read without its result column.

## Limitations

* **Carrying a family is not having enough of it.** An annotated Infosys match holds 142 points on average, 18.1 of them rallies of nine shots or more (12.7% of points; `infosys_long_rallies`). Three such matches give a noisy long-rally rate. Stage 1 would measure each statistic's reliability before any scoring.
* **The sources measure differently.** Rally length is the shot that ended the point in Infosys (capped at "9+" and "10+"), a rally count in the Slam feeds, and shots charted in the volunteer charts. Endings are fully classified in some sources and only winners and unforced errors in others. Placement uses different zones. A player's history mixes sources, so Stage 1 would check the sources against each other on matches two of them hold (the Slam files and feeds overlap in 2019–2024; the charts overlap every feed).
* **Linking by surname and date** misses same-surname pairs (sisters, or two players named Wang) and players whose surname changed between sources. The linker's misses are concentrated before 2010 (charts outside Stage 0's years), in juniors and team events (not in Stage 0), and in TDI's Challenger qualifying.
* **Two time rules.** The main tables use the earlier studies' rule (tournament start dates and rounds). The feature-alpha audit found that rule can let a fortnight-long event's late rounds into another event's history. Its repaired rule, finished on the same day, is counted separately above, and the candidate list proposes it for scoring. The repaired outputs were read as they stood at the time of this run; their hash is in `stage0_summary.json`, `inputs`.
* **The detectable gains assume a calibrated base and a fixed feature.** Selection among many rows, clustering of matches by week, and fitting many inputs raise them. The inflation factors capture part of that, and the family-wide column more.

## Decisions for the owner

**Overtaken on 2 Oct 2026.** The owner asked for the features to be built and tested directly. Stages [1](stage1.md) and [2](stage2.md) answer decisions 1 and 2: both tours were built, side by side. Decision 3 (ball tracking later) and decision 4 (no purchase) stand as suggestions, with Stage 2's results behind them. The decisions as first written:

1. **Go on to Stage 1, and on which list?** The [candidate list](candidates.md) proposes 14 statistics, two memories and the scoring protocol. Stage 1 builds the statistics and checks them without reading results; Stage 2 scores them against the odds.
2. **Both tours, or the men first?** The men have the denser data (the ATP feeds) and the box-score lead; the women have rally length only from the Slams and the charts. The suggestion is both, side by side, as in the earlier studies, with the women's thinner families flagged.
3. **Ball tracking now or later?** Decoding Court Vision's obfuscated fields is a few hours' work against the readable Slam copy, for a family whose detectable gain is 2.2 (men) and 11.4 (women). The suggestion is later, only if Stage 2 finds a gain.
4. **No data purchase or new download now.** That is the suggestion; Stage 2's result decides what, if anything, to look for.
