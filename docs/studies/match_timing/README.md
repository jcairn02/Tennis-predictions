# Match timing: a leak-proof clock for every match

5 October 2026 · Research evidence, not a production, model or betting decision.

The IOS inputs (ratings solved for all players together) leaked results across overlapping events; [section 1](#1-the-leak-and-the-rule) explains how. The owner asked how to fix this without discarding most of the history, as the [repair](../feature_alpha_audit/repairs.md) had done, and approved this build:

* give each of the 872,704 matches an earliest possible start day and a latest possible finish day;
* re-solve the IOS ratings day by day on that clock;
* test the result against real dates;
* score three versions of the inputs on identical matches.

No new data, no paid calls. Next the owner asked for three things: research online to narrow the windows, a list of every match without a known day, and a proposal for the corner cases. The research is in [docs/research/match-timing/](../../research/match-timing/README.md).

Later the same day the owner made this clock the project's rule ([decision](../../decisions/2026-10-05-match-timing.md)):

* IOS and every other function that needs it are rebuilt on it;
* every scraper keeps its source's match times;
* one TabPFN-3.5-Thinking refit of the best 2026 model is authorised. It ran that evening ([report](../tabpfn_leakproof/README.md)), and its edge over the closing price is unchanged.

Positive milli-log-loss (mLL) means better: +1 lowers average log loss by 0.001. Brackets are paired 95% intervals clustered in four-week calendar blocks; a range that spans zero is a tie. **Observed** means computed here, **inferred** means reasoning, **proposal** means a suggestion not yet decided.

## In short

* **Observed. The original IOS clock leaked; the new one does not.** The test flips every result after a cut day and recomputes the inputs of the matches that surely finished before it.
  * The original week clock moved 238, 140 and 236 of those matches at three of the four cuts in 2023–2024. At the fourth cut, no event straddled the cut day.
  * The leak-proof clock moved none at any cut. It checked 13,758 to 31,163 matches per cut, up to 1.46 million values; the largest difference was 6 × 10⁻¹⁵.
* **Observed. The leak did not move the scores.** On identical 2022–2026 test matches, the leak-proof inputs tie the original ones in every model:
  * men's Elo: −0.02 [−0.05, +0.01];
  * the nine-input combination: −0.03 [−0.11, +0.04];
  * the odds plus all 47 inputs: +0.01 [−0.04, +0.06].
* **Observed. Keeping the whole history matters far more.** The leak-proof build keeps all 872,704 matches; the repaired build kept only the 78,714 main-tour matches with a provider date. Without the odds, leak-proof beats repaired:
  * men: Elo +19.3 [+15.5, +23.1]; nine inputs +14.3 [+10.7, +17.8];
  * women: Elo +19.9 [+15.8, +24.1]; nine inputs +10.8 [+7.8, +13.8].

  With the odds, the three versions tie.
* **Observed. 479,784 matches (55.0%) have a trusted day** from 13 sources; **392,920 do not.** All are listed in `undated_matches.csv.gz`. 61% of them sit in 8,370 events where no match is dated, almost all ITF events and team ties.
* **Observed. Every source's own clock error is measured and carried.**
  * Against the days of point logs, the sources put 94–99.98% of matches on the first point's day. Their misses are mostly a day or two late.
  * Each dated match's own window carries its sources' measured error (median 2 days wide).
  * Each source's days then hold 99.8% or more of the point-log days (`source_calibration.csv`).
* **Observed. The windows hold out of sample.**
  * On dated matches held out by event, the class/rule windows miss 0.046% of true days, by 1–6 days.
  * Windows built from the same round's other dated matches miss 0.019%.
  * In events run off their usual calendar, the event-shift rule cuts misses from 1.27% to 0%.
* **Observed. Four defects were found in this study's first timeline and fixed the same day**, each now covered by a test:
  * where sources disagreed, the code trusted one of them;
  * a draw-order step spread one misdated day through a quarter of a draw, which let 54 matches see their own result;
  * the 2021 Australian Open qualifying was read as the US Open;
  * events run off their usual calendar got windows that were too narrow.
* **Observed. The same leak reaches beyond IOS** ([section 8](#8-the-same-leak-elsewhere)).
  * **TrueSkill Through Time**, the leading rating candidate of 3 October, leaks. Rebuilt on this clock, it keeps its edge: against Elo in 2019–2026 it scores +2.66 [+1.90, +3.41] for men (+2.65 before the fix) and +2.93 [+1.61, +4.25] for women (+3.00 before).
  * **Bradley–Terry, MESR and the strength-of-schedule revaluation** also leak. None is in use; each is marked.
* **Observed. The best 2026 model keeps its edge with leak-proof IOS.** One TabPFN-3.5-Thinking refit used the same matches and configuration, with only the 22 IOS inputs rebuilt. Against the recalibrated closing price, for men:
  * 2022–2026: +1.52 [+0.76, +2.27], against +1.57 for the original fit;
  * 2026: +2.70 [−0.11, +5.51], against +2.70.

  Refit against original: −0.06 [−0.13, +0.02], a tie. The two fits' forecasts correlate 0.9999.
* **Implemented. Going forward, every scraper keeps the match's time**, and one command refreshes the timeline and the IOS inputs ([section 9](#9-going-forward)).
* **Proposal.** The handling of each corner case is in [section 6](#6-corner-cases-and-proposed-handling). The weakest remaining case is women's ITF qualifying: 70,124 matches, none with a source date.

## 1. The leak and the rule

**What leaked** (observed in `src/eda/ufc_ideas/stageB_ios.py`, line 224):

* IOS solves all players' serve and return ratings together, one solve per tournament start date.
* Each solve held every result whose *event* began before that date.
* The late rounds of a two-week event (the Slams, Indian Wells, Miami, the 12-day Masters) are played during the next week. So are the later rounds of any event dated earlier than another (Tokyo on a Wednesday and Beijing on a Thursday, for example). Those results entered the ratings for the other event's earlier matches before they were played.
* Because the solve is joint, one leaked result moves every player's ratings a little.

**How many matches were exposed.** A count of two-week overlaps alone found 3.9% of the men's 2022–2026 test matches exposed. The audit later counted every exposed event. Up to 2,306 of the 12,797 men's and 1,260 of the 11,911 women's main-tour test matches sit in exposed events; this is an upper bound, since not every match of an exposed event saw a leaked result.

**What did not leak.** Elo, the serve/return ratings, the opponent-adjusted profile, the 52-week points matchup, workload and age use only each player's own earlier matches. Nobody plays two events at once, so a player's own order is known even without days. Rebuilt here, these inputs correlate 0.997–1.000 with the originals.

**The two-time rule.** Every match gets an earliest possible start day (ES) and a latest possible finish day (LF). A result may enter another match's inputs only if it surely finished before that match could start, that is, if its LF comes before the other match's ES. For IOS (`ios_time.py`):

* there is one solve per day S, holding the results with LF + 1 ≤ S;
* a match reads the solve of its ES day;
* each player's own earlier matches that are not yet released are then added in order, as Stage B already did within an event;
* the time decay uses a best-estimate day inside [ES, LF].

A window that ended before it began would let a match's own result into its own ratings. The solver refuses to run on such a window, and the timeline builder refuses to write one.

**What the rule costs** (inferred). Only delay:

* a result reaches other players' inputs at LF + 1, not on the day after it was played;
* a match reads its ratings as of its ES.

Nothing leaks as long as every window holds its true day. In live betting every result in the database is already in the past, so the rule only recreates that condition for backtests.

## 2. Where the match days come from

Thirteen sources were linked to the project's match table, Stage 0 of the [predictability diagnostic](../predictability_diagnostic/README.md). Each link matches both players' names within a date window and is confirmed by identical set scores. The code is in `src/eda/match_timing/link_*.py`. A match can have several links.

| Source | Links | Clock of the date | Dates |
|---|---|---|---|
| Flashscore export (on disk) | 413,616 | local 408,055; UTC 5,561 | 2010 – Apr 2026 |
| Live Tennis API (Zenodo copy) | 126,876 | local 66,265; UTC 60,611 | 2023 – Aug 2026 |
| api-tennis fixtures | 108,269 | local 46,898; UTC 61,371 | 2021 – 2024 |
| tennis-data.co.uk | 79,669 | UK day, tagged by venue direction | 2010 – Aug 2026 |
| Sackmann's point-by-point copy | 52,234 | unstated, so treated as UTC | Oct 2010 – Feb 2017 |
| ATP Infosys | 37,203 | local | Nov 2018 – 2024 |
| WTA API | 28,689 | local 27,853; UTC 836 | Dec 2018 – Sep 2026 |
| Open tennis data | 26,581 | local 15,457; UTC 11,124 | 2020 – Aug 2026 |
| SofaScore | 13,923 | local 13,843; UTC 80 | 2013 – Sep 2026 |
| Match Charting Project | 9,164 | local | 2010 – Sep 2026 |
| Slam feeds | 7,682 | local | 2019 – Sep 2026 |
| TDI | 3,132 | local | May 2025 – Sep 2026 |
| TML match days | 2,448 | local 1,393; UTC 1,055 | Nov 2021 – Sep 2026 |

**How the days are read** (`timing.py`):

* A local day counts as itself. A UTC day could be the local day before, on or after, so it counts as that three-day interval.
* tennis-data dates matches by the UK clock. The local day can be one later at venues east of London and one earlier at venues to the west.
* A match suspended overnight ends on its last point's day, up to three days later.
* A link more than 10 days before or 21 days after the tournament's start is dropped, as are the tennis-data rows that Stage 1 had re-dated.
* Three sources are often a day off where several sources date a match. Before this rule, ATP Infosys was outvoted 380 times, Match Charting 348 and TML days 105, almost always by one day. Their days now count as ± 1, like a UTC day.
* When sources still disagree:
  * a day shared by three or more sources against a single dissenter stands (281 matches);
  * otherwise the interval covering every source's day is used, which holds the true day whichever source is right;
  * if the sources lie more than a week apart (7 matches), the match is not counted as dated.

  A day is never chosen by trusting one source over another.

**Each source's clock error, measured.** The days read off a point log are the reference: a WTA event log's or a Slam feed's first point, and TDI's points. For each class of link (source, clock, and the WTA list's or tennis-data's tag), `calibrate()` measures how many extra days before and after its interval would bring 99.9% of those reference days inside. Classes with fewer than 200 overlaps are measured instead against days where Flashscore and tennis-data agree; classes with neither take one day each side. A dated match's own window is its claimed days widened by its sources' error. The windows of section 3 and the checks use the claimed days.

| Source and clock | Overlaps with point logs | Extra days before / after | Inside before → after |
|---|---|---|---|
| Flashscore, local | 24,423 | 1 / 0 | 98.7% → 99.93% |
| Live Tennis API, local | 19,755 | 1 / 0 | 98.4% → 99.92% |
| tennis-data, untagged | 7,415 | 2 / 1 | 97.0% → 99.99% |
| tennis-data, venues to the east | 3,340 | 1 / 0 | 99.6% → 100% |
| tennis-data, venues to the west | 5,009 | 0 / 0 | 99.98% |
| open tennis data, local | 7,042 | 2 / 1 | 97.4% → 99.99% |
| open tennis data, UTC | 5,304 | 0 / 0 | 99.98% |
| Match Charting | 2,348 | 1 / 0 (on top of ± 1) | 99.7% → 99.8% |
| SofaScore, local | 1,524 | 1 / 0 | 98.5% → 100% |
| api-tennis, local | 1,459 | 2 / 0 | 95.8% → 100% |
| WTA list, scheduled start | 1,072 | 1 / 0 | 99.7% → 99.9% |
| TML days, local / UTC | 495 / 495 | 4 / 1 and 3 / 4 | 97.8% and 94.1% → 100% |
| Infosys; point-by-point copy (against Flashscore and tennis-data agreeing) | 3,635; 5,919 | 0 / 0 | 99.9%; 100% |

Most sources miss on the late side: their day falls a day or two after the first point, through a late start dated by the next day or a time zone read wrongly. A late day risks a same-day leak: the match's own ratings would include other results of the day it was really played. The widened windows remove that risk.

**How well the sources agree.** Of the 256,365 matches with several sources, 96.5% get the same day from all of them and 99.93% get days at most one apart.

## 3. Windows where no source has the day

The online research established each level's schedule and how far it slipped in 2010–2026. Its rules are in `schedule_rules.csv`, 455 rows, each with a source. A match without a trusted day gets its window as follows:

1. **From its round's dated matches** in the same event: the first to the last dated day, ± 1 day, or ± 2 with fewer than three dated matches. This applies when those days lie within 4 days of each other.
2. **Otherwise from a named edition's researched rule.** Named rules cover the Slams' qualifying, the January 2021 events, the 2021 Australian Open qualifying in Doha and Dubai, the Olympics, team competitions, the Laver Cup and a few others.
3. **Otherwise from the union of two windows:**
   * the class window: the spread of dated days for the same tour, level, phase (qualifying or main draw), round and era, trimmed of 0.2% at each end and widened by a day each side;
   * the level's research rule, widened by two days each side.

   A class with fewer than 200 dated matches takes the level's default window.
4. **The event shift.** If the event's own dated matches sit 2 or more days off their classes' typical days, the window is joined with the same window moved by that much.
5. **The draw.**
   * A player's match cannot start before their previous round could start, nor finish after their next round finished.
   * If applying this would ever make a window end before it begins, some dated day in that event is wrong. Every match of that event then takes the union of its claimed day, its round's window and its class window.
6. **When a dated day is not trusted on its own.** This applies when its sources lie more than a week apart, it falls after the event's dated final, or it lies outside its round's other dated days. Such a match takes the union of its claimed day and its window.

**Validation** (observed, `timing_check.py`). The dated matches are split by event into two halves. Windows are built from one half and tested on the other, then the halves swap.

| Window | Tested | True day outside the window | Notes |
|---|---|---|---|
| Class/rule (steps 2–3) | 473,366 | 0.046% (after it 0.010%, before it 0.036%) | missed by 1 day: 109; 2: 34; 3: 34; 4: 29; 5–6: 12 |
| With the event shift (step 4), using only the event's other rounds | 10,834 in shifted events | 0% (1.27% without the shift) | median 2 days wider |
| Same round (step 1), leaving each match out | 461,959 | 0.019% | median width 4 days |

**Class/rule misses by class:**

* 0.006% of men's and 0% of women's ITF main-draw matches;
* 0.029% of men's Challenger main draws;
* 0–0.03% of Slam, Challenger and 250 qualifying;
* 0.16% (men) and 0.32% (women) of team ties.

**Where the remaining class misses fall:**

* special editions whose matches are in fact all dated: the 12-day Masters of 2025–26 and the 2021 Abu Dhabi events;
* a few team ties: the 2017 Fed Cup zonal weeks, missed by 1–2 days.

## 4. Defects found and fixed

All four were in this study's own first timeline. The first two were found by checking that every window ends on or after its start; the last two by listing which events the out-of-sample misses came from. All are fixed, with tests in `test/match_timing/` (63 pass).

1. **When sources disagreed by more than a week, the code kept the top-ranked source's day.**
   * That was wrong for Haas–Fognini at Stuttgart and at Hamburg 2013, a quarter-final at both. tennis-data, ranked first, gives the two matches each other's days; Flashscore and the point-by-point copy agree with each other and not with it.
   * It happened to be right in 2026. There, open tennis data alone gives Osaka–Muchova at Bad Homburg and Wimbledon each other's days, and puts Zverev–Fritz's Wimbledon quarter-final 18 days early.

   Fixed by the majority and covering-interval rules (section 2). Seven matches remain with sources more than a week apart, none in 2026.
2. **The draw rule spread a misdated day.** The Hamburg quarter-final, dated three days before the main draw began, pulled the latest-finish day of every match in its quarter of the draw back to that date. 54 windows ended before they began, which let those matches' own results into their own ratings. Fixed by the guard in step 5 and the check in step 6. The solver now also refuses an inverted window.
3. **The 2021 Australian Open qualifying was read as the US Open.** The events are named "Doha / Dubai Aus Open Qualies", and "aus open" contains "us open". The second- and third-round windows (96 matches) ended on 11 January, but those rounds were played on 12 and 13 January. Fixed: names are matched as whole phrases, and three researched rule rows give those rounds' days.
4. **Some events ran off their usual calendar.** 219 of 16,820 dated events sit 2 or more days from their classes' typical days, mostly women's ITF events at Antalya, Cancún and Kuršumlijska Banja. Fixed with the event-shift rule, which widened 624 windows.

The source calibration of section 2 was added later the same day, after the same checks showed that some "exact" days are themselves a day or two late.

From the first timeline to the final one, 434,911 windows changed:

* 433,966 widened at one end or both, mostly by the calibration's day;
* 945 narrowed at one end, mostly by a day, where a disagreement was resolved:
  * 805 are dated matches whose sources had disagreed and now agree, either because a loose-clock source counts as ± 1 or because three sources outvote a fourth;
  * 140 are undated matches whose round's dated days narrowed in the same way.

Test scores moved by at most 0.06 mLL.

## 5. Every match without a trusted day

**Files:**

* `data/studies/match_timing/undated_matches.parquet` and `undated_matches.csv.gz`: 392,920 rows. Each gives the match, tournament, round, its earliest and latest dates, the window's width and basis, and why it has no trusted day.
* `undated_summary.csv`: the same counts by tour, level, phase and year.

**Why there is no trusted day:**

* no source holds the day: 392,836;
* the event's dated days contradict the draw order: 45, in 2 events;
* the dated day lies outside its round's other dated days: 32;
* the sources lie more than a week apart: 7.

| Matches | Without a day | Share | Median window (days) |
|---|---|---|---|
| Women's ITF main draw | 156,912 | 60.6% | 9 |
| Men's ITF main draw | 136,806 | 49.5% | 9 |
| Women's ITF qualifying | 70,124 | 100% | 7 |
| Men's Challenger qualifying | 10,669 | 38.5% | 7 |
| Tour-level qualifying | 7,449 | 15.3% | 3 |
| Men's Challenger main draw | 5,925 | 6.7% | 4 |
| Team ties | 3,125 | 33.7% | 8 |
| Men's ITF qualifying | 982 | 97.2% | 7 |
| WTA 125 | 813 | 9.4% | 5 |
| Tour-level main draws | 115 | 0.1% | 4 |

**Where they sit:**

* 240,921 (61%) are in 8,370 events where no match is dated, almost all ITF events and team ties.
* 93,880 (24%) are in events with dated matches but none in their round. Most are women's ITF qualifying in events whose main draw is dated.
* 58,119 (15%) take their window from dated matches of the same round.

## 6. Corner cases and proposed handling

| Case | Matches | What the build does | Remaining risk | Proposal |
|---|---|---|---|---|
| Whole events with no dated match (ITF, team ties) | 240,921 in 8,370 events | Class/rule window, then the draw; median 9 days | Out-of-sample misses: men's ITF main 0.006%, women's 0% | Keep. A cheap check: widen every window by one day, re-score, and confirm that nothing moves |
| Women's ITF qualifying (and men's) | 70,124 (982) | Rule/default window, about 7 days; draw order for players who qualify | Weakest validation: only 14 (28) dated matches to test on | (a) Add a rule: qualifying ends before the event's first dated main-draw day. (b) Acquire days: SofaScore has women's ITF from 2014 (covered by the owner's decisions of 23–25 Sep, per the research; this use to be confirmed); Tennis Explorer needs Livesport's consent. (c) Fallback: release qualifying results only after the main draw starts |
| Events partly dated | 93,880 | Class/rule window plus the event shift, then the draw | Out of sample, 0% in shifted events | Keep |
| Sources disagree | 553 (281 settled by majority; 7 more than a week apart) | Majority of 3+ against 1; else an interval covering every day; more than a week apart, not dated | None found | Keep; never trust one source by rank |
| A source's day a day or two off | Every source class | Each class's measured clock error widens its days | Beyond 99.9% of each class's errors; classes never compared take ± 1 more | Keep. Re-measure when a source changes |
| A wrong day that agrees with its round and the draw | Unknown | Cannot be detected; the calibration covers each source's measured error | Rare and short | Accept |
| Special editions (COVID calendar, relocated qualifying, 12-day Masters, season finals, Challenger Finals) | Nearly all dated | Named rule, else the round's dated days, else the event shift; fully undated special editions get the level's default | Named-rule labels can mismatch names (defect 3) | Keep. A test that every named rule matches its events' real names |
| Dated days contradict the draw | 142 in 2 events | Union windows for the whole event, then the draw again | None found | Keep |
| Rain delays, overnight suspensions, post-midnight finishes | Not counted | Class windows include them; a suspended match's last-point day, and from now on SofaScore's last change, extends its finish | Finals slipped at most one day in 2010–26, earlier rounds two (research) | Keep |
| Same-day results | All | Never released to another match the same day; a player's own earlier round that day is added through the own-sequence step | None: delay only | Keep |
| Round robins (season finals, team events) | 9,271 (3,089 without a day) | No order between round-robin matches; windows from the round's dated matches or rules | Fed Cup zonal 2017: 1–2 days before the window | Widen team-tie windows by one day before their start |
| Live use (bets) | Future | Results enter when final | Nothing to reconstruct | The as-of rule; the windows are for history only |

## 7. Rebuild, probe and scores

### Rebuild (observed, `rebuild.py`)

* **History:** all 872,704 matches, with the repair's data corrections: 305 identity rows, 7,650 historical tiebreak scores, 137 implausible durations and 1 negative box score masked. Formats come from the schedule, not from the scores.
* **Per-player inputs (24):** rebuilt; they correlate 0.997–1.000 with the originals.
* **IOS inputs (22):** seven statistics, each as offence, defence and their product, on the tuned constants, plus the short-memory points matchup. One solve per day; every solve converged.
* **Output:** `leakproof_features.parquet`, 255,123 pool matches, 46 inputs.

### Probe (observed, `probe.py`, 2023–2024 slice)

At each cut day, every result that could have started after the cut is flipped: winner and loser swap, and so do their statistics. Then every input is recomputed for the matches that surely finished by the cut.

| Cut | Matches checked | Leak-proof: matches moved | Week clock: matches moved (largest change) |
|---|---|---|---|
| 6 Sep 2023 | 13,758 | 0 | 238 (0.061) |
| 24 Jan 2024 | 19,744 | 0 | 140 (0.043) |
| 10 Jul 2024 | 29,141 | 0 | 236 (0.092) |
| 14 Aug 2024 | 31,163 | 0 | 0 (no event straddled the cut) |

All 47 inputs were checked: Elo and the 46 rebuilt ones. Under the week clock only the IOS inputs moved, and all 22 of them did. The probe cannot see a match's own result leaking into its own ratings. That case is ruled out separately: the timeline never writes a window that ends before it starts, and the solver refuses one.

### Scores (observed, `score.py`)

The models are logistic regressions without an intercept, fitted per tour on 2013–2021 and scored on 2022–2026, following the [TabPFN-Thinking study](../tabpfn_thinking/README.md)'s design. Every compared version uses the same training and test matches. The repaired build has no IOS or 52-week points inputs, so models that need them compare two versions only.

**Leak-proof against the other versions**, same model, same matches (positive = leak-proof better):

| Tour | Model | Window | Matches | Against original | Against repaired |
|---|---|---|---|---|---|
| Men | Elo | 2022–26 | 12,299 | −0.02 [−0.05, +0.01] tie | +19.30 [+15.48, +23.11] |
| Men | 9 inputs | 2022–26 | 12,042 | −0.03 [−0.11, +0.04] tie | +14.26 [+10.74, +17.79] |
| Men | odds + profile (16) | 2022–26 | 12,019 | +0.00 [−0.01, +0.02] tie | +0.65 [−0.02, +1.33] tie |
| Men | odds + 9 + profile (25) | 2026 | 1,710 | +0.04 [−0.19, +0.26] tie | −0.03 [−2.48, +2.41] tie |
| Men | odds + all 47 | 2022–26 | 12,327 | +0.01 [−0.04, +0.06] tie | n/a |
| Women | Elo | 2022–26 | 11,413 | +0.64 [−0.24, +1.52] tie | +19.93 [+15.80, +24.06] |
| Women | 9 inputs | 2022–26 | 11,024 | −0.04 [−0.44, +0.35] tie | +10.81 [+7.84, +13.78] |
| Women | odds + all 47 | 2022–26 | 11,256 | −0.01 [−0.26, +0.23] tie | n/a |

**Each version with the odds, against the recalibrated closing price** (positive = better than the price):

| Tour | Inputs with the odds | Window | Original | Leak-proof | Repaired |
|---|---|---|---|---|---|
| Men | profile (16) | 2022–26 | +0.93 [−0.00, +1.86] tie | +0.93 [+0.00, +1.86] borderline | +0.28 [−0.49, +1.05] tie |
| Men | profile (16) | 2026 | +1.38 [−1.24, +4.00] tie | +1.43 [−1.20, +4.07] tie | +1.24 [−0.15, +2.63] tie |
| Men | 9 + profile (25) | 2026 | +2.27 [−1.36, +5.90] tie | +2.30 [−1.34, +5.95] tie | +2.34 [+0.42, +4.25] better |
| Men | IOS (21) | 2022–26 | −0.16 [−0.83, +0.52] tie | −0.15 [−0.82, +0.53] tie | n/a |
| Men | all 47 | 2026 | +0.93 [−3.80, +5.66] tie | +1.01 [−3.61, +5.63] tie | n/a |
| Women | all 47 | 2022–26 | +0.73 [−0.53, +1.98] tie | +0.71 [−0.56, +1.98] tie | n/a |

## 8. The same leak elsewhere

An audit of every rating and feature function looked for the same pattern: results of different players combined in buckets keyed on the event's start date (`docs/decisions/2026-10-05-match-timing.md` has the full table).

* **Leak, now rebuilt: TrueSkill Through Time.** This is `ratings.ttt_pass`, the owner's leading rating candidate of 3 October.
  * **How it leaks.** It adds each start date's matches as one batch once the date changes, and its smoothing passes a batch's results to every player. A Slam's second week, or any event still running under an earlier date, therefore reaches other players' matches played before it. The study's hold variant withholds only events with a round of 128.
  * **The fix.** `ratings.ttt_pass_timed` applies the two-time rule: a result joins the model on its release day, and a match reads it as of its earliest start. On the old weekly clock it reproduces `ttt_pass` exactly, quiet weeks included; on real days it passes the isolation test that `ttt_pass` fails (`test/rating_systems/test_ttt_timed.py`).
  * **Re-measuring.** `ttt_timed.py` re-runs it at the study's frozen constants (not retuned). The smoothing span is the days the original window of start-date batches covered: 2,337 days for men, 602 for women. It is scored against Elo as the study did; the original's numbers are reproduced exactly.

    | Tour | Window | Original TTT vs Elo | Leak-proof TTT vs Elo | Leak-proof vs original |
    |---|---|---|---|---|
    | Men | 2019–2026 | +2.65 [+1.89, +3.40] | +2.66 [+1.90, +3.41] | +0.01 [−0.03, +0.05] tie |
    | Men | 2022–2026 | +2.90 [+2.06, +3.74] | +2.92 [+2.08, +3.76] | +0.02 [−0.03, +0.07] tie |
    | Women | 2019–2026 | +3.00 [+1.67, +4.33] | +2.93 [+1.61, +4.25] | −0.07 [−0.14, −0.00] worse |
    | Women | 2022–2026 | +2.29 [+0.92, +3.67] | +2.21 [+0.82, +3.61] | −0.08 [−0.16, +0.01] tie |

    TTT's edge over Elo survives the fix. For men the leak was worth nothing; for women, about 0.07 milli-log-loss, a twentieth of the edge. On the tuning years (2013–2018) the leak-proof version is 0.04 (men) and 0.02 (women) below the original, so the constants chosen there would not change. The 3 October designation therefore rests on leak-free evidence: the leak-proof TTT beats Elo by +2.66 (men) and +2.93 (women) in 2019–2026.

    *Rebuilt on 6 Oct 2026, with the coordinated Stage 0 rebuild* ([Slam box-score decision](../../decisions/2026-10-06-slam-box-scores.md)). The table's own evaluation matches are unchanged.
    * **Against Elo** (positive = TTT better):

      | Tour | 2019–2026 | 2022–2026 |
      |---|---|---|
      | Men | +2.67 [+1.90, +3.44] | +2.94 [+2.08, +3.81] |
      | Women | +3.22 [+1.85, +4.59] | +2.63 [+1.14, +4.12] |
    * **What moved.** The Elo it is scored against is the frozen one of the table above, so any change is TTT's own. Its women's log loss fell by 0.29 milli-log-loss (lower is better); the men's barely moved.
      * *Inferred:* the gain comes from the identity repairs, which put 305 player rows back on their players' histories. TTT reads results only, so the box-score changes cannot move it, and on the two-time rule later results cannot reach earlier matches.
    * **The comparison with the original TTT** now mixes the leak fix with those data corrections. The table above keeps the clean comparison.
    * The outputs of 5 Oct are kept in `data/studies/data_continuity/rebuilds/2026-10-07T0005Z/replaced/`.
* **Leak, not in use, marked:** Bradley–Terry and MESR (`ufc_ideas/stageA_ratings.py`), and the strength-of-schedule revaluation (`stageC_sos.py`). Each docstring now says to rebuild it on this clock before any use.
* **No leak:** Elo, Glicko, TrueSkill, the correlated-surface ratings, Stage 3's serve/return ratings, the opponent-adjusted profiles, the 52-week points, workload and age. Their time gaps (decay; the 14-day and 52-week spans) are counted from event start dates. That is imprecise, but not a leak.
* **Normalising constants** (surface means, typical units, shrinkage) are frozen on 2010–2018 and never touch the test years.

## 9. Going forward

* **Scrapers keep the clock.** Each adapter keeps the time fields its source sends:
  * the WTA API (`point_sources/wta.py`): whether a listed start is only an estimate, which it is for most Slam rows, and the court;
  * SofaScore (`sofascore.py`, with its `_editions` and `_tournaments` adapters, which inherit the columns): the last set's start, the last change (within a minute of the last point for a finished match) and the venue;
  * the Australian Open's archived draws (`ausopen.py`): the actual start, duration, court and session;
  * TennisLive (`tennislive.py`): the page's start;
  * Polymarket (`public_dump/polymarket_prices.py`): the event index's start, event date and end.

  The linkers read these fields where the staged files have them. The WTA linker uses the estimated-start flag in place of guessing from the tier. The SofaScore linker tags a finish that falls on a later day than the start.
* **The order to refresh.**
  1. New results reach Stage 0 only from Tennis My Life (`public_dump/tennis_my_life.py`, then `predictability_diagnostic/stage0_build.py`).
  2. Their days come from the sources that keep updating: tennis-data.co.uk (`refresh_odds.py`, then `stage1_odds.py`), the WTA API, SofaScore, the Slam feeds and TDI.
  3. After those run, `./python.sh src/eda/match_timing/refresh.py` re-links the updating sources, rebuilds and checks the timeline, and rebuilds the IOS inputs. Frozen sources keep their link files.
     * A match's id can change at a Stage 0 rebuild when a player's id is corrected: 42 June-2026 WTA matches did at the rebuild of 6 Oct 2026.
     * `src/eda/data_continuity/rebuild_stage0.py` runs the whole sequence. It pairs each changed id with its new one (same event, round and players) and rewrites it in the frozen link files.
* **Not yet re-staged.** Files staged before 5 October lack the new fields until each adapter's staging is rerun from its raw files (`--stage-only`), which the owner has not asked for.

## 10. What this means for the 2026 closing-line result

The best 2026 result is the [TabPFN-Thinking fit](../tabpfn_thinking/README.md) on the closing odds plus 53 original inputs. Against the recalibrated price it scored, for men, +2.70 [+0.01, +5.38] on 2026 and +1.57 [+0.82, +2.32] on 2022–2026.

* **Observed.** On the 96% of men's test matches outside the two-week overlaps, that fit scored +1.59 [+0.80, +2.37]. In linear models, the leak-proof inputs carry the same information as the original ones. The leak-proof IOS inputs correlate 0.993–0.9995 with the originals on the fit's test rows, and 0.996–1.000 on its training rows.
* **Observed: the direct test.** The [authorised refit](../tabpfn_leakproof/README.md) used the same matches and configuration with the 22 IOS inputs rebuilt. For men it scores +1.52 [+0.76, +2.27] on 2022–2026 and +2.70 [−0.11, +5.51] on 2026 against the recalibrated price. Against the original fit it is −0.06 [−0.13, +0.02], a tie. The overlap leak did not create the result.

## 11. Files and how to reproduce

Code is in `src/eda/match_timing/`, tests in `test/match_timing/`, outputs in `data/studies/match_timing/`. Run with `./python.sh`:

1. `link_pbp_copy.py`, `link_flashscore.py`, `link_sources_b.py`, `link_sources_c.py`: write `links/<source>.parquet`, one file per source.
2. `timing.py`: writes `timing.parquet`, one row per match:
   * `es`, `lf`, `obs`: earliest start, latest finish and best-estimate day;
   * `exact`, `window_basis`, `demoted`, `contradictory_event`: whether the day is trusted, and how the window was built;
   * sources, conflicts and outvoted sources.

   It also writes `source_calibration.csv`, `timing_classes.csv`, `timing_summary.json`, `undated_matches.*` and `undated_summary.csv`.
3. `timing_check.py`: writes `timing_check.json`, `timing_check_classes.csv` and `timing_check_siblings.csv`.
4. `rebuild.py`: writes `perplayer_features.parquet`, `ios_features.parquet` and `leakproof_features.parquet`, about 15 minutes. After a timeline change, only `rebuild.py --part ios` (about 10 minutes with four workers; set `MATCH_TIMING_WORKERS`) and `--part merge` need rerunning.
5. `score.py`: writes `score_results.csv`, `score_gains.csv`, `score_summary.json` and `score_predictions.parquet`.
6. `probe.py`: writes `probe.json` and `probe_details.csv`, about 10 minutes.
7. `ttt_timed.py`: TrueSkill Through Time on this clock against Elo. Writes `ttt_timed.parquet`, `ttt_timed_results.csv` and `ttt_timed_summary.json`.
8. `refresh.py`: steps 1–4 for the sources that keep updating.

## 12. Limits

* **ITF and team ties.** Windows for events with no dated match rest on the class pattern. A misrecorded tournament week there cannot be detected without another source.
* **Women's ITF qualifying.** Its windows are validated on only 14 dated matches.
* **Calibration coverage.** The calibration measures each source against point logs, which exist only from 2019 and mostly at tour level. Classes without that overlap are measured against Flashscore and tennis-data agreeing, or take a default.
* **The scores.** They come from linear models and one TabPFN refit. The 2019–2026 seasons have been inspected by earlier studies, so nothing here is an untouched holdout. Closing prices are archived tennis-data quotes, not timestamped executable prices.
