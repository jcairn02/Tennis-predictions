# Evidence dose and exposure: how much of the model's inputs comes from below the main tour

9 October 2026 · Role 02 of the lower-level evidence review · Research evidence, not a decision.

**The question.** How much of each model input's evidence comes from lower levels, for which players and matches? Where does lower-level evidence dominate? Where is the current best model weakest against the closing price?

**Ground rules kept.**
* Every count runs on the frozen reference of 8 Oct 2026 (Stage 0: 873,437 matches; the model frame: 67,226 matches).
* Parts 1–4 read no result. Part 5 reads results of seasons 2019–2024 only (2019 calibrates, 2020–2024 are scored). Season ≤ 2024 is checked to mean events before 30 Dec 2024 before any result is read (`composition.py:817`).
* Labels: **Observed** = computed here or read in a file (cited). **Inferred** = reasoning. **Suggestion** = for the lead and the owner.

**Direction keys used throughout.**
* **Lower-level share:** the part of a player's earlier matches played below the main tour's main draws (tour qualifying, Slam qualifying, Challenger and WTA 125 main draws and qualifying, ITF main draws and qualifying). Team events are counted in the total but not as lower-level. 0% = all main tour; 100% = all lower-level.
* **Gain over the close:** mLL = milli-log-loss per match. **+ = the model has the lower log loss (better).** "Better" or "worse" when the 95% interval clears 0; otherwise "unresolved" (what the shared brief calls a tie), with P(better) = Φ(estimate / SE).
* **Calibration slope:** the result regressed on a forecast's log-odds. 1 = right-sized; above 1 = the forecast is too timid (favourites win more than it says); below 1 = too extreme.

## The answer in short

* **About a quarter to a half of the evidence behind the inputs is lower-level, depending on the input's memory** (Observed, 2019–2024 model matches, pooled over sides):

  | Input family | Men | Women |
  |---|---|---|
  | Two-week form (`form_*`, `formdef_*`, `adjperf_tpw_2w`: 17 inputs) | 27% | 25% |
  | Short-memory IOS points matchup (`ios_points_short`) | 28% | 23% |
  | `points_52w` (raw rates, last 52 weeks) | 34% | 23% |
  | IOS profile (`iosO_*`, `iosD_*`, `prod_*`: 21 inputs) | 38% | 23% |
  | Serve and return ratings (`ratings_iid`) | 45% | 24% |
  | Elo family (career results) | 55% | 54% |

* **The player's ranking decides it.** Share of the two-week form's and `points_52w`'s evidence that is lower-level: top 20, under 2%; ranked 51–100, 30–46%; ranked 101–200, 58–75%; ranked 201+, 63–87% (Observed).
* **In half of all model matches (50%), at least one player's last year is mostly lower-level** (more than half of his or her results). At the 250s: 64% of men's and 73% of women's matches (Observed, 2019–2024).
* **Low exposure is common and comes with plenty of lower-level evidence.** In 24% of model matches the less-exposed player has fewer than 10 main-tour results in the last 365 days. Those players are mostly ranked 101–200 or worse, and for 84–88% of them three quarters or more of their year is lower-level. On average they have 4 main-tour box scores in the year against 43 lower-level ones (men), or against 12 lower-level box scores plus 26 ITF results without one (women) (Observed).
* **Women's box-score inputs already shift with data coverage, not with the players.** The lower-level share of women's box-score evidence (365 days) was 15% in 2013–18, 23% in 2019–24 and 32% in 2025–26, while their results stayed at 32–36% lower-level. Causes: ITF box scores exist only from January 2025; WTA 125 box scores are missing in 2013 and 2015; Slam qualifying has none in 2015–2017; WTA 2015 has no lower-level box score at all. Men's is steady at 31–35% (Observed).
* **ITF box scores of 2025–26 already reach 42% of women's model matches** (one side or both, 365-day window). They are 8–13% of women's box-score evidence from mid-2025 on (Observed). Men: 7% of matches, at most 1.6% of the evidence.
* **ITF box scores of 2018–2024 (collection plan P7) would change women's inputs a lot, and only in some seasons.** Recounted exactly with those box scores in place: women's lower-level share of box-score evidence (365 days) rises by +11 to +14 points in every season 2019–2024, +6 in 2018 and 2025, and not at all in 2013–2017 or 2026. That is the "uneven" shape the input check warns about (finding #6). Men move by about 1 point or less (Observed).
* **The model's edge over the close does not depend detectably on exposure or lower-level dose.** Its gain is positive in every both-tours stratum (+0.8 to +4.1 mLL point estimates), but no family of strata shows a difference between its strata (Wald tests, p = 0.12–0.92). Small strata are unresolved (Observed, 2020–2024).
* **What the close gets wrong, and the model only half fixes:** the close under-rates the player with more lower-level evidence when the two players' lower-level shares differ by half or more (a quarter of matches). It is short by +0.18 log-odds (SE 0.04) on the box-score share, about 4–5 points of win probability in an even match. The model leaves +0.09 to +0.12 (SE 0.04) of it (Observed). This replicates the event-levels study's finding, and locates it.

## How the counting works

**What is counted** (`src/eda/lower_level_evidence/composition.py:200-305`). For each of the 67,226 model matches and each side, the player's earlier matches in Stage 0, by bucket (`common.bucket`), in two channels:
* **results:** every completed or retired match (walkovers and "other" out);
* **box score:** the same, with a box score (Stage 0's `has_box`).

**Windows**, in days between tournament dates (how the per-player inputs measure time):

| Window | Mirrors (inferred from the builders' descriptions; role 01 traces the code) |
|---|---|
| 14 days | `sets_14d` (Stage 4's window: `stage4_features.py:838-839`) |
| 28 and 91 days | the short-memory IOS (4 weeks men, 13 women) in hard form |
| 365 days | `points_52w` (Stage 4 uses 364 days) |
| career (Stage 0 starts in 2010) | the Elo family; `ratings_iid` (Glicko-style steps; only completed box-score matches move it: `stage3_ratings.py:13-15`) |
| half-life 2 weeks | the two-week form, 17 inputs (`tabpfn_thinking/common.py:84-106`; Stage B's chosen h3 = 2 weeks, `data/studies/ufc_ideas/stageB_adj_summary.json`) |
| half-life 4 / 13 weeks | `ios_points_short`, men / women (the IOS constants registry) |
| half-life 52 weeks | the IOS profile's long memory (its half-lives run 26–208 weeks or none, by statistic) |

Half-life windows count each earlier match with weight 2^(−age / h), as Stage 3's `lookback_sums` does (`stage3_traits.py:556-564`).

**"Earlier" means the player's own earlier matches** (`composition.py:230-303`): events with an earlier tournament date, plus the same event's earlier rounds. Other events of the same week and other matches of the same round (round robin) never count.
* **Why this and not the strict match clock.** It is Stage 0's as-of rule (`predictability_diagnostic/common.py:161-181`), which every per-player input and the leak-proof IOS's own-match step follow (`match_timing/ios_time.py:14-18`). A player's own earlier matches surely finished before, because nobody plays two matches at once (the [match-clock decision](../../../decisions/2026-10-05-match-timing.md), point 1). The strict clock (a result counts from its latest finish + 1, read at the earliest start) is the rule for other players' results.
* **Its error, measured pair by pair** (Observed, `clock_check.csv`; 7,668,824 counted pairs in the 365-day windows):
  * **0 contradictions:** no counted match is shown by the clock to have started after the target surely finished.
  * **0.40% cannot be placed first by the clock** (30,417), 96% of them the same event's earlier rounds whose day windows overlap the target's. The inputs do count those. The strict clock would drop 6.6% of the 14-day evidence (main draw 7.4%, tour qualifying 7.8%), 1.5% of the 91-day and 0.4% of the 365-day.
  * **Same-week other events left out:** 6 pairs, 2 of which the clock shows finished first. Negligible.

**Shares are pooled** (the sum of lower-level matches over the sum of all matches) unless a table says "mean of sides". Pooled shares weight busy players more.

## 1. How much of each input's evidence is lower-level

Lower-level share of the evidence in each input family's mirrored window, pooled over model sides (`inputs_dose.csv`; Observed):

| Input family | Channel, window | Men 2013–18 | Men 2019–24 | Men 2025–26 | Women 2013–18 | Women 2019–24 | Women 2025–26 |
|---|---|---|---|---|---|---|---|
| Two-week form (17) | box, half-life 2 weeks | 23% | 27% | 30% | 18% | 25% | 26% |
| `ios_points_short` | box, half-life 4 weeks (men) / 13 (women) | 25% | 28% | 31% | 15% | 23% | 31% |
| `points_52w` | box, 365 days | 31% | 34% | 35% | 15% | 23% | 32% |
| IOS profile (21) | box, half-life 52 weeks | 33% | 38% | 38% | 16% | 23% | 31% |
| `ratings_iid` | box, career | 37% | 45% | 46% | 18% | 24% | 29% |
| Elo family (7) | results, career | 43% | 55% | 55% | 44% | 54% | 55% |
| `sets_14d` | results, 14 days | 26% | 27% | 30% | 27% | 29% | 25% |

* **Which levels.** Men's lower-level box-score evidence (365 days, 2019–24) is mostly Challenger main draws (22 of the 34 points) and tour qualifying (8). Women's is tour qualifying (12 of 23), WTA 125 (7.5) and Slam qualifying (3.4); ITF adds 0.1 (no box scores before 2025).
* **Career windows grow with the season** (Stage 0 starts in 2010), so the Elo family's and `ratings_iid`'s rise from 2013–18 to 2019–24 is partly the window filling in: a 2019–24 player's early ITF and Challenger years are in Stage 0, a 2013 player's are not (Inferred).
* **Even top-20 players' Elo is a third lower-level** (31% men, 35% women): their early careers (Observed, band table below).

## 2. For whom: rank band and level

Lower-level share by the player's ranking at the match, 2019–24 (`inputs_dose.csv`, grouping "tour x era x band"; Observed):

| Input family | Tour | 1–20 | 21–50 | 51–100 | 101–200 | 201+ |
|---|---|---|---|---|---|---|
| Two-week form | men | 0.2% | 5% | 32% | 69% | 76% |
| | women | 0.3% | 7% | 30% | 60% | 64% |
| `points_52w` | men | 1% | 17% | 46% | 75% | 87% |
| | women | 2% | 12% | 34% | 58% | 63% |
| IOS profile | men | 7% | 27% | 50% | 72% | 77% |
| | women | 4% | 15% | 34% | 53% | 50% |
| Elo family | men | 31% | 52% | 65% | 73% | 66% |
| | women | 35% | 47% | 62% | 73% | 69% |

* **Evidence volume falls with ranking for women's box scores.** A woman ranked 201+ has 10 box-score matches in 365 days behind `points_52w` (a top-20 woman: 55); a man ranked 201+ has 30. The rest of the low-ranked women's year is ITF results without box scores.

By match level, 2019–24 (Observed): the 250s carry the most lower-level evidence (two-week form: men 37%, women 34%; IOS profile: men 47%, women 34%). The 1000s carry the least (form 17% both tours). The Tour Finals: 0–5%.

## 3. Where lower-level evidence dominates

Share of model matches in which at least one side has more than half of its last 365 days' evidence below the main tour (Observed; computed from `sides.parquet` with `composition.per_match`):

| | Results channel | Box-score channel |
|---|---|---|
| Men, 2013–18 / 2019–24 / 2025–26 | 51% / 50% / 51% | 50% / 50% / 52% |
| Women, 2013–18 / 2019–24 / 2025–26 | 49% / 51% / 51% | 24% / 39% / 49% |
| 250s, 2019–24 (men / women) | 64% / 73% | 64% / 60% |
| 1000s, 2019–24 (men / women) | 32% / 29% | 32% / 19% |

* **The two-week form of players ranked 101–200 is two-thirds lower-level** (men 69%, women 60%). About a quarter of it is the qualifying rounds of the very event the match belongs to (men 23%, women 27%; all qualifying, 39% and 50%): the freshest evidence the model has about them (Observed, 2019–24; recounted with the script's index in a one-off check, not written to the outputs).
* **Most of the players the model ever sees are mostly lower-level players.** Of 936 men and 943 women with a model match in 2013–2026, 738 and 739 have a median 365-day lower-level share above one half across their model matches (Observed). They play few model matches each; the top players play many.

## 4. The box-score channel already moves with data coverage

Share of completed and retired matches with a box score in Stage 0 (Observed, the frozen Stage 0):

| | WTA 125 (men: Challenger) | Slam qualifying | Tour qualifying | Main tour | ITF |
|---|---|---|---|---|---|
| Women 2013 | 0% | 59% | 87% | 88% | 0% |
| Women 2015 | 0% | 0% | 0% | 77% | 0% |
| Women 2016–17 | 99–100% | 0% | 100% | 100% | 0% |
| Women 2018 | 99% | 54% | 100% | 100% | 0% |
| Women 2019–24 | 90–100% | 99–100% | 99–100% | 99–100% | 0% (31 matches in 2022) |
| Women 2025–26 | | | | | 94–99% |
| Men 2015–17 | 97–100% | 0–50% | 53% (2015), 100% | 100% | 0% |

What the women's box-score inputs therefore see (lower-level share, pooled; Observed, `itf_p7_scenario.csv` "today" columns):

| Women | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019–24 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|
| Two-week form (half-life 2 weeks) | 20% | 21% | **0.1%** | 20% | 19% | 21% | 22–27% | 29% | 23% |
| `points_52w` (365 days) | 16% | 17% | 11% | 12% | 17% | 18% | 19–26% | 28% | 37% |

* **Inferred:** the box-score inputs of a woman ranked 150 in 2015 rest on her main-tour matches only; in 2023 on main tour, qualifying and WTA 125; in 2026 also on ITF. The model trains on all these seasons pooled. The same kind of player reaches it through different evidence by season, which is a level shift the opponent adjustment can only partly absorb (role 03 measures how much).
* Men's box-score lower-level share is steady: 31% / 34% / 35% (365 days, the three eras).

## 5. The ITF box-score regime of 2025–26

ITF's share of the box-score evidence in model matches' windows (`itf_regime.csv`; Observed):

| Women | Before 2025 | 2025 Q1 | Q2 | Q3 | Q4 | 2026 Q1 | Q2 | Q3 |
|---|---|---|---|---|---|---|---|---|
| ITF share, 365 days | 0–0.3% | 0.7% | 2.7% | 8.4% | 11.5% | 10.3% | 9.7% | 12.6% |
| ITF share, 91 days | 0% | 3.2% | 5.9% | 8.5% | 7.5% | 7.7% | 7.5% | 4.6% |
| Sides with any ITF box score in 365 days | 0–6% | 7% | 17% | 31% | 35% | 33% | 28% | 37% |

* **Men:** at most 1.6% of the 365-day box-score evidence (2026 Q3), 0.3–1% of the 91-day; 6% of sides by 2026 Q3.
* **Players and matches with any ITF box score in the 365-day window, 2025–26** (`itf_any.csv`): women 297 of 413 players and 1,931 of 4,652 matches (42%); men 120 of 360 players and 317 of 4,810 matches (7%). By ranking, women 101–200: 802 of 1,316 matches; 51–100: 766 of 2,451; top 20: 29 of 1,668.
* **The 91-day share falls in 2026 Q3** because Stage 0's ITF box scores stop at the end of May 2026, as the input-data audit's finding #6 records (Inferred from the dates).

## 6. What ITF box scores of 2018–2024 would add (collection plan P7)

**The dose** (`itf_preview.csv`, `itf_preview_unique.csv`; Observed). ITF main-draw results without a box score inside the 365-day windows of 2019–2024 model matches:

| | Men | Women |
|---|---|---|
| Incidences (matches counted once per model side) | 21,366 | 209,284 |
| Per model side | 0.75 | 8.0 |
| Sides with at least one | 4.6% | 46.5% |
| Distinct ITF matches in at least one window | 9,286 of 101,903 (9%) | 28,048 of 102,283 (27%) |
| Women's ITF qualifying, distinct (P7's trial decides whether it is collected) | – | 3,764 of 69,067 |

The plan expects box scores for about 98% of P7's matches (a plan claim from 84 sampled matches, not observed here).

By ranking (women, 2019–24): ranked 101–200, 19 per side and 87% of sides; 201+, 22 per side; 51–100, 8; 21–50, 2; top 20, 0.4.

**The effect on the box-score evidence**, recounted exactly with every ITF main-draw result of 2018–2024 given a box score (`composition.py:652`, `itf_p7_scenario.csv`; Observed). Lower-level share of box-score evidence, today → with P7 (change in points):

| Women | 2013–17 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|
| 365 days (`points_52w`) | +0 | 18% → 24% (+6) | 21% → 33% (+12) | +13 | +11 | +12 | 26% → 40% (+14) | +12 | +6 | +0 |
| Half-life 13 weeks (`ios_points_short`) | +0 | +8 | +11 | +11 | +10 | +11 | +12 | +10 | +4 | +0.4 |
| Half-life 2 weeks (two-week form) | +0 | +6 | +5 | +5 | +5 | +5 | +6 | +4 | +0.3 | +0 |
| Half-life 52 weeks (IOS profile) | +0 | +4 | +10 | +12 | +14 | +15 | +16 | +15 | +11 | +7 |

* **Men:** +0.4 to +1.0 points (365 days) and up to +2.5 (52-week half-life) in 2018–2025.
* **By ranking (women, 2019–24, 365 days):** 51–100: 34% → 45%; 101–200: 58% → 75%; 201+: 63% → 88%. At the women's 250s: 35% → 51%.
* **Inferred: wired in by itself, P7 would make the women's box-score inputs "uneven"** (the input check's flag: a level or scale move in some seasons only). It moves 2018–2025 and leaves 2013–2017 untouched, the same shape as finding #6 (ITF box scores in 2025–26 only). It also more than doubles the box-score evidence of exactly the low-exposure women of section 7.

## 7. Exposure: main-tour matches in the last 365 days

The less-exposed side of each model match (fewer main-tour results in 365 days; ties broken on the career) (`exposure.csv`, `exposure_cross.csv`; Observed):

| Less-exposed side's main-tour results, 365 days | 0 | 1–4 | 5–9 | 10–19 | 20+ |
|---|---|---|---|---|---|
| Men 2013–18 | 3.4% | 9.3% | 9.1% | 14.9% | 63.3% |
| Men 2019–24 | 3.7% | 10.3% | 10.0% | 18.1% | 58.0% |
| Women 2013–18 | 3.3% | 10.0% | 9.6% | 16.5% | 60.5% |
| Women 2019–24 | 4.1% | 11.6% | 12.1% | 20.5% | 51.7% |

* **Fewer than 10 main-tour results: 24% of all model matches** (men 22–24%, women 23–28% by era; 2019–24 is higher partly because 2020's season was short). Median of the less-exposed side: 20–28 main-tour results.
* **Who they are** (2019–24): ranked 101–200 (men 52–63%, women 50–67% of the 1–9 buckets) or 201+ (43–73% of the 0 and 1–4 buckets). They play the 250s most (men's 1–4 bucket: 819 of 1,464 matches).
* **They are lower-level players:** 75–100% of their year is lower-level for 88% (men) and 84% (women) of these matches. So about 21% of men's and 23% of women's model matches have one side that is a lower-level player by any measure.
* **They have plenty of lower-level evidence.** 2019–24 sides with under 10 main-tour results: men 4.0 main-tour box scores in 365 days against 42.5 lower-level ones (30.7 Challenger, 8.4 qualifying); women 4.2 against 12.4, plus 26.4 ITF results without a box score.
* **Career exposure is rarely low:** 89–91% of sides (both tours, every era) have 20+ main-tour results in their career since 2010 (but see the 2010 floor).

## 8. Where the current model is weak against the close (2020–2024)

**The test** (`composition.py:760-929`). The reference's forecasts (seeds 0–3), both stages and stage 1 alone, refitted walk-forward as decided, against its frame's average close recalibrated with one slope per tour, by compare.py's own loaders and recipe (`current_best_model/compare.py:76-110, 228-292`). Debut seasons out. Intervals: 4-week blocks plus the seeds' variance (`serve_speed_tabpfn/score.py:396-412`). The strata were fixed in the code (`composition.py:119-124`, and `strata_of` at `:760`) before any score was computed. **Descriptive: many strata, no model choice rests on them.**

**Harness check (Observed):** all 22,265 matches give +1.374 [+0.668, +2.081], better, exactly the reference's published figure (`comparisons/reference/scores.csv`).

### 8a. The gain over the close by stratum

Both stages against the recalibrated close, both tours (`scores.csv`; **+ = the model better**):

| Stratum | Matches | Gain, mLL [95%] | Reading (P(better)) |
|---|---|---|---|
| **Less-exposed side's main-tour results, 365 days** | | | |
| 0 | 899 | +0.78 [−2.84, +4.41] | unresolved (0.67) |
| 1–4 | 2,514 | +1.57 [−0.27, +3.41] | unresolved (0.96) |
| 5–9 | 2,500 | +1.84 [−0.22, +3.89] | unresolved (0.96) |
| 10–19 | 4,493 | +2.09 [+0.76, +3.41] | better |
| 20+ | 11,859 | +1.01 [+0.13, +1.89] | better |
| **The larger side's 365-day box-score lower-level share** | | | |
| 0–25% | 7,328 | +0.99 [−0.08, +2.05] | unresolved (0.97) |
| 25–50% | 4,459 | +1.56 [+0.14, +2.98] | better |
| 50–75% | 5,235 | +1.87 [+0.72, +3.02] | better |
| 75–100% | 5,242 | +1.25 [−0.19, +2.69] | unresolved (0.96) |
| **Exposure crossed with dose** | | | |
| Both sides 10+, larger box share under 50% | 11,196 | +1.05 [+0.14, +1.97] | better |
| Both sides 10+, larger box share 50%+ | 5,156 | +1.85 [+0.67, +3.03] | better |
| A side under 10, larger box share under 50% | 592 | +4.14 [+0.04, +8.24] | better |
| A side under 10, larger box share 50%+ | 5,321 | +1.28 [−0.20, +2.76] | unresolved (0.96) |

* **No family's strata differ from each other** (`scores_heterogeneity.csv`): exposure in 365 days p = 0.64, career exposure 0.92, box-share dose 0.71, its A−B difference 0.73, results-share dose 0.79, exposure × dose 0.40; by tour p = 0.12–0.92. The model is not detectably weaker for low-exposure or lower-level-heavy matches.
* **By tour, the weakest point estimates** (all unresolved, Observed):
  * women with both players established: less-exposed side 20+ main-tour results, +0.23 [−1.08, +1.54] (P 0.64); larger box share 0–25%, +0.19 [−1.40, +1.79] (P 0.60);
  * men whose less-exposed side has no main-tour result in the year: −0.50 [−5.48, +4.49] (450 matches, P 0.42);
  * men whose larger box share is 75–100%: +0.67 [−1.00, +2.34] (P 0.79).
* **Women's edge sits with the lower-level-heavy matches:** larger box share 50–75%, +1.93 [+0.32, +3.55]; 75–100%, +2.48 [+0.18, +4.79], both better. Men's edge sits with the established matches: 0–25%, +1.79 [+0.58, +3.01], better. The heterogeneity test does not separate them (women p = 0.31, men 0.63).
* **Stage 1 alone** reads the same way (`scores.csv`, `stage1_*` columns).

### 8b. Is the market less sharp for low-exposure players?

Calibration slope by stratum (1 = right-sized; above 1 = too timid). The raw de-vigged close is too timid overall (1.11, SE 0.015); the decided per-tour recalibration brings it to 1.00. Within strata, the recalibrated close (`scores.csv`; Observed):

Slope (SE):

| Stratum | Matches | Recalibrated close | The model |
|---|---|---|---|
| All matches | 22,265 | 1.002 (0.014) | 0.994 (0.015) |
| Less-exposed side 0 main-tour results, both tours | 899 | **1.148 (0.073)** | 1.099 (0.075) |
| Same, men | 450 | **1.331 (0.127)** | 1.298 (0.128) |
| Less-exposed side 5–9 | 2,500 | 1.080 (0.050) | 1.075 (0.052) |
| No main-tour result in the career, both tours | 425 | **1.204 (0.100)** | 1.165 (0.102) |
| A side under 10 and larger box share 50%+ | 5,321 | **1.061 (0.030)** | 1.046 (0.032) |
| Women, larger box share 0–25% | 3,701 | **0.900 (0.038)** | 0.881 (0.038) |
| Women, less-exposed side 20+ | 5,278 | **0.929 (0.029)** | 0.915 (0.030) |

* **The close is too timid when one player has little or no main-tour record**: favourites win more often than it says. **It is too extreme in women's matches between established players.**
* **The model inherits both:** its slopes track the close's in every stratum.
* These are descriptive: about 2 standard errors each, among many strata.

### 8c. The player with more lower-level evidence is under-rated

Matches oriented so that the "focal" player has the larger 365-day lower-level share; the result regressed on the forecast's log-odds with an intercept. **+ = the forecast under-rates the focal player** (`scores.csv`, `intercept_*` columns; Observed, both tours):

Intercept in log-odds (SE); strata by the box-score share's difference (the results-share strata are built the same way on the results channel and hold slightly different matches):

| Difference of the two shares | Matches (box) | Close, box-score share | Model, box-score share | Close, results share | Model, results share |
|---|---|---|---|---|---|
| 0–0.10 | 6,457 | −0.010 (0.030) | −0.015 (0.030) | −0.007 (0.028) | −0.011 (0.028) |
| 0.10–0.25 | 4,820 | +0.094 (0.034) | +0.075 (0.033) | +0.083 (0.040) | +0.066 (0.039) |
| 0.25–0.50 | 5,265 | +0.091 (0.042) | +0.060 (0.041) | +0.060 (0.040) | +0.031 (0.040) |
| **0.50–1** | 5,619 | **+0.178 (0.043)** | **+0.093 (0.042)** | **+0.204 (0.044)** | **+0.119 (0.042)** |

* **Size:** +0.18 log-odds is about 4.5 points of win probability in an even match; the model's remaining +0.09 to +0.12 is about 2–3 points.
* **By tour (box-score share, 0.50–1):** men close +0.18 (0.05), model +0.10 (0.05); women close +0.16 (0.10), model +0.08 (0.10).
* **Inferred:** this is the event-levels study's finding (section 8, β ≈ +0.13 on the share difference), located: it sits in the quarter of matches where the two players' histories differ most. The model takes up about a third to a half of it (the event-levels study found about a third: +0.12 of +0.18). Event-levels' experiment C (the share as an input or a stage-2 term) was unresolved at about 0.1 mLL overall (as a 59th input: +0.06 [−0.10, +0.23], P(better) 0.76).

## 9. What this means for the design (suggestions)

**Suggestion 1: treat lower-level evidence as its own channel for the players who need it, not as more of the same.** The quantity is large exactly where main-tour evidence is thin: a quarter of model matches have a side with under 10 main-tour results in a year, and those players bring 10 times more lower-level box scores than main-tour ones (men). Today those matches enter the same pooled inputs as main-tour matches. A design that keeps them apart (a main-tour profile, a lower-level profile translated to main-tour terms, and how much of each the player has) would let the model weigh them; the UFC prior is this shape. The sides table (`sides.parquet`) already holds the per-player doses such a design would use as weights. Role 03 sets the exchange rate.

**Suggestion 2: before wiring P7, decide how the 2018–2024 ITF box scores enter.** Wired in by itself, P7 moves the lower-level share of women's box-score evidence by +11 to +14 points (365 days) and up to +16 (52-week half-life) in 2019–2024, and not at all in 2013–2017: the input check will likely flag it as uneven, as it flagged finding #6 (Inferred: the check reads input values, and this measures their evidence). Three ways, each to be scored as a candidate: keep ITF box scores out of the box-score inputs and give them their own channel; translate and discount them (role 03); or collect women's ITF of 2014–2017 too (SofaScore holds women's ITF from 2014, per the [match-clock decision](../../../decisions/2026-10-05-match-timing.md)'s open points) so that every training season has them. Rerun this script on the candidate Stage 0 first: it shows the dose by season in under two minutes.

**Suggestion 3: the women's coverage gaps of 2013 and 2015 are already an uneven dose.** WTA 2015 has no lower-level box score at all (two-week form 0.1% lower-level, against 20% in neighbouring seasons). A candidate that drops or down-weights the lower-level box scores in every season, or that fills 2015, would show whether this matters. Cheap to test as a candidate; nothing here says it helps.

**Suggestion 4: the target for an informative-prior design is narrow, and the evaluation should say so.** The model's edge is not detectably smaller for low-exposure matches, so a better lower-level channel must earn its keep where the close is wrong: (a) the under-rating of the lower-level-heavy player (+0.18 at the close, +0.09–0.12 left in the model, in a quarter of matches), and (b) the close's timidity when a player has no main-tour record (slope 1.15–1.33). Score candidates on those strata as secondary readings, pre-registered, with the overall gain over the reference as primary.

## What it does not show

* **Matches, not points.** The inputs weigh matches by their points or service games (the IOS's τ = 1) and shrink toward priors with K constants (the form: K3 = 10–160 typical matches). A share of matches is a proxy for a share of influence on each input, not the influence itself.
* **The player's own matches only.** Lower-level matches also reach a player's inputs through his opponents: their ratings, norms and the IOS's joint solve. That cross-player path is not counted here (role 01 traces it).
* **The mirrored windows are approximations** of the inputs' memories; the exact memory of each input is role 01's.
* **The career floor.** Stage 0 starts in 2010; career windows of early seasons are short.
* **Part 5 is descriptive.** 8 families × 3 tour splits × 4–5 strata. No stratum differs significantly from the others. The slopes and intercepts are about 2–4 standard errors each, with no correction for the number of looks.
* **Closing prices only,** 2020–2024. Nothing about an early price or a bet.
* **The holdout.** 2025–26 matches are counted (sections 1–7), never scored.
* **P7's yield** (98%) is the plan's claim; the scenario assumes 100%.

## Checks

* **Brute force:** 300 random model sides recounted from the rule written out directly, every channel, window and bucket: 43,200 values, 0 wrong (`summary.json`, `spot_check`).
* **Agreement with the event-levels study:** the pooled 365-day mix of 2013–2024 model matches reproduces its published table to the point, though on a later snapshot and a different match set: men's 250s 54% main tour / 12% qualifying / 29% Challenger / 3% ITF, women's 48 / 18 / 5 / 26; men's 1000s 75 / 7 / 14 / 1.
* **Harness:** the reference's gain over its calibrated close, +1.374456 [+0.667727, +2.081186], is reproduced exactly.
* **Tests:** 17 pass (`./python.sh -m pytest test/lower_level_evidence/test_composition.py -q`): window boundaries (inclusive at W days, excluded at W + 1), the same event's earlier rounds counted and later rounds never, round robin and same-week other events left out, channels and statuses, both sides and tours apart, half-life weights, the brute force on a random history, a cut probe (nothing after a cut changes any count before it), the bins, the heterogeneity test, the holdout guard, the clock check's classes, the P7 scenario, and a whole run on a synthetic Stage 0 folder (the renewable path).
  * The whole folder (`./python.sh -m pytest test/lower_level_evidence -q`, with role 03's `test_translation.py`) passed at the last run: 32 tests.
* **Inputs pinned** (`summary.json`): SHA-256 of the frozen Stage 0 tables and the frame. Runtime 45–105 seconds.

## Code, outputs and re-running it

| What | Where |
|---|---|
| The script | `src/eda/lower_level_evidence/composition.py` |
| Tests | `test/lower_level_evidence/test_composition.py` |
| Outputs (label `reference_2026-10-08`) | `data/studies/lower_level_evidence/composition/reference_2026-10-08/` |
| Per side, every count (gitignored parquet, rebuilt by the script) | `sides.parquet` |
| Shares: full cross (tour × season × level × rank band) / margins / per input family | `shares_full.csv.gz`, `shares.csv`, `inputs_dose.csv` |
| ITF regime, preview, distinct matches, the exact P7 scenario | `itf_regime.csv`, `itf_any.csv`, `itf_preview.csv`, `itf_preview_unique.csv`, `itf_p7_scenario.csv` |
| Exposure | `exposure.csv`, `exposure_cross.csv` |
| Part 5 | `scores.csv`, `scores_heterogeneity.csv` |
| The clock check, headline numbers, hashes | `clock_check.csv`, `summary.json` |

```
./python.sh src/eda/lower_level_evidence/composition.py                       # the frozen reference
./python.sh src/eda/lower_level_evidence/composition.py --stage0-dir <candidate Stage 0 folder> --label <name>
./python.sh src/eda/lower_level_evidence/composition.py --stage0-dir <...> --label <name> --model <built folder>
./python.sh -m pytest test/lower_level_evidence/test_composition.py -q
```

* **On a candidate Stage 0** the counts, shares, ITF tables and exposure are recomputed from it; the frame still names the model's matches. Part 5 uses the reference's forecasts unless `--model` names a candidate's built folder (compare.py's layout). A new `map_level` stops the run (`common.bucket`) until the bucket list is extended.
* **What to compare between runs:** `itf_p7_scenario.csv`'s "today" columns by season (an uneven dose shows as a jump in some seasons only), `inputs_dose.csv` by era, and `exposure_cross.csv`.
