# Stage B: against Elo and the closing odds

**Status: built 2 Oct 2026.** A study stage, not a decision. The Brief is in the [README](README.md); the report section is Stage B in [report.html](report.html). Every number comes from `data/studies/rating_systems/summary_results.json`, which gathers `stageB_summary.json` and `stageB_ranking.csv`.

Labels: **observed** is measured on the data, **inferred** is a reading of measurements, **suggestion** is a proposal.

## In short

* **Observed. TrueSkill Through Time beats surface Elo by about 2.5–3 milli-log-loss, out of sample as in the tuning years.**
  * On every evaluation match of 2019–2026: +2.65 for the men (95% interval +1.89 to +3.40) and +3.00 for the women (+1.67 to +4.33).
  * In 2013–2026: +2.65 and +2.80.
  * It holds with the two-week events held back: +2.59 and +2.75 in 2019–2026.
* **Observed. The correlated-surface ratings are next.** Glicko's is +2.11 (men) and +2.68 (women) in 2019–2026. TrueSkill's is +1.75 and +3.29; for the women it edges TTT, within the noise.
* **Observed. Glicko-2 and TrueSkill as such barely beat Elo.**
  * Match-by-match Glicko-2: +0.90 (men, +0.27 to +1.54) and +1.01 (women, −0.31 to +2.32) in 2019–2026.
  * TrueSkill: +0.69 and +1.30.
  * Glicko-2 with weekly rating periods is worse: −1.42 and −0.32 (2019–2026), −3.30 and −1.10 (2013–2026).
* **Observed. On the main-tour matches with odds, TTT closes about a tenth of the gap between Elo and the closing prices.** In 2022–2026:
  * Men: +2.37 milli-log-loss (+0.62 to +4.12), 10.6% of the gap; from a coin to the market, 78.4% → 80.7%.
  * Women: +1.81 (−0.22 to +3.84), 9.6%; 81.7% → 83.5%.
* **Observed. Given the closing odds, no rating adds anything.** Through the shared harness, TTT adds +0.04 (men; −0.02 to +0.11) and −0.02 (women). The largest gain of any rating is the match-by-match Glicko-2's +0.08 for the men (+0.01 to +0.16).
* **Observed. TTT holds everything Elo has.** Through the harness, Elo given TTT scores −0.34 (men) and −0.57 (women): adding Elo to TTT makes the forecast worse. Elo still adds +0.44 and +0.16 to the correlated-surface Glicko.
* **Observed. The new ratings take over part of what the earlier leaders added to Elo.** TTT holds almost all of the games-weighted Elo's gain (1.82 → 0.04, men) and much of the serve-and-return ratings' (3.61 → 2.09). It leaves the men's statistics profile almost whole (3.97 → 3.78). [Stage C](stageC.md) measures the overlap properly.

## Against surface Elo, every evaluation match

Better than Elo (+) or worse (−), milli-log-loss, with the 95% interval clustered by four-week blocks (`summary_results.json`, `raw`):

| System | Men 2013–2026 | Men 2019–2026 | Men 2022–2026 | Women 2013–2026 | Women 2019–2026 | Women 2022–2026 |
|---|---:|---:|---:|---:|---:|---:|
| TrueSkill Through Time | +2.65 (+2.13 to +3.17) | +2.65 (+1.89 to +3.40) | +2.90 (+2.06 to +3.74) | +2.80 (+1.96 to +3.64) | +3.00 (+1.67 to +4.33) | +2.29 (+0.92 to +3.67) |
| the same, two-week events held | +2.56 (+2.03 to +3.08) | +2.59 (+1.83 to +3.35) | +2.78 (+1.92 to +3.63) | +2.66 (+1.80 to +3.51) | +2.75 (+1.41 to +4.10) | +1.91 (+0.52 to +3.29) |
| Glicko, correlated surfaces | +1.51 (+0.90 to +2.12) | +2.11 (+1.20 to +3.01) | +2.05 (+1.10 to +2.99) | +2.33 (+1.29 to +3.37) | +2.68 (+1.06 to +4.29) | +2.11 (+0.40 to +3.81) |
| TrueSkill, correlated surfaces | +0.64 (−0.07 to +1.36) | +1.75 (+0.72 to +2.78) | +1.42 (+0.37 to +2.48) | +2.54 (+1.43 to +3.66) | +3.29 (+1.56 to +5.02) | +2.97 (+1.00 to +4.94) |
| Glicko-2, match by match | +0.49 (+0.04 to +0.94) | +0.90 (+0.27 to +1.54) | +1.05 (+0.35 to +1.75) | +0.80 (−0.02 to +1.61) | +1.01 (−0.31 to +2.32) | +0.45 (−0.89 to +1.79) |
| Glicko-1, match by match | +0.55 (+0.11 to +0.99) | +1.01 (+0.39 to +1.63) | +1.15 (+0.48 to +1.83) | +0.80 (−0.01 to +1.60) | +1.01 (−0.29 to +2.30) | +0.43 (−0.90 to +1.77) |
| TrueSkill | −0.25 (−0.72 to +0.21) | +0.69 (+0.07 to +1.31) | +0.79 (+0.11 to +1.46) | +1.05 (+0.20 to +1.90) | +1.30 (−0.05 to +2.66) | +1.11 (−0.48 to +2.70) |
| Glicko-2, weekly periods | −3.30 (−4.08 to −2.52) | −1.42 (−2.23 to −0.62) | −1.49 (−2.43 to −0.55) | −1.10 (−2.17 to −0.02) | −0.32 (−2.07 to +1.44) | −0.48 (−2.45 to +1.49) |
| Glicko-1, weekly periods | −3.37 (−4.15 to −2.59) | −1.51 (−2.31 to −0.71) | −1.56 (−2.49 to −0.63) | −1.10 (−2.18 to −0.02) | −0.32 (−2.08 to +1.43) | −0.48 (−2.45 to +1.49) |

Matches: men 155,130, 90,922 and 64,887; women 60,321, 34,645 and 23,998. **Observed:** the gains after the tuning years are as large as in them, so tuning did not flatter the new systems.

## On the matches with odds

2022–2026, main-tour matches with closing odds (12,352 men's, 11,467 women's). Better than Elo with its 95% interval; the share of the Elo-to-market gap closed; and the distance from a coin to the market (0% a coin, 100% the closing prices):

| System | Men | Gap closed | Coin → market | Women | Gap closed | Coin → market |
|---|---:|---:|---:|---:|---:|---:|
| Surface Elo | – | – | 78.4% | – | – | 81.7% |
| TrueSkill Through Time | +2.37 (+0.62 to +4.12) | 10.6% | 80.7% | +1.81 (−0.22 to +3.84) | 9.6% | 83.5% |
| the same, two-week events held | +2.24 (+0.46 to +4.02) | 10.0% | 80.6% | +1.56 (−0.49 to +3.62) | 8.3% | 83.2% |
| Glicko, correlated surfaces | +1.21 (−1.12 to +3.53) | 5.4% | 79.6% | +1.14 (−1.46 to +3.73) | 6.0% | 82.8% |
| TrueSkill, correlated surfaces | +0.56 (−2.01 to +3.14) | 2.5% | 79.0% | +1.91 (−1.11 to +4.92) | 10.1% | 83.5% |
| Glicko-2, match by match | −0.27 (−1.89 to +1.34) | −1.2% | 78.2% | +0.66 (−1.43 to +2.75) | 3.5% | 82.3% |
| TrueSkill | +0.06 (−1.55 to +1.66) | 0.2% | 78.5% | +1.20 (−1.46 to +3.86) | 6.4% | 82.9% |

* **The room** (Elo minus the market) is 22.46 (men) and 18.78 (women) milli-log-loss.
* **2013–2026.** TTT closes 7.1% (men; +1.40, +0.41 to +2.39) and 15.8% (women; +2.64, +1.58 to +3.70); the correlated-surface Glicko 9.1% and 11.4%.
* **Observed. The new ratings gain less on the main-tour draws than off them.** For the men, TTT's gain on every evaluation match is +2.90 in 2022–2026; on the matches with odds, +2.37.

## By level and era

Better than Elo, milli-log-loss, every evaluation match of 2013–2026 (`by_level`, `by_era`):

| Level | Men: TTT | Men: correlated Glicko | Women: TTT | Women: correlated Glicko |
|---|---:|---:|---:|---:|
| Grand Slams | +1.47 | +5.28 | +4.48 | +4.47 |
| Tour Finals* | +3.18 | −0.52 | +1.44 | −0.06 |
| 1000s | +1.16 | −0.43 | +1.94 | +0.40 |
| 500s | −0.48 | +1.45 | +4.57 | +2.96 |
| 250s | +2.59 | +1.41 | +1.23 | +1.21 |
| Grand Slam qualifying | +0.03 | +1.02 | −0.52 | +0.49 |
| Tour qualifying | +1.40 | +0.89 | +3.70 | +3.33 |
| Challenger / WTA 125 | +1.59 | +0.91 | +3.96 | +3.53 |
| Challenger / 125 qualifying | +8.03 | +3.21 | +3.33 | +0.75 |

\* Under 300 matches (315 men's, 285 women's): directional only. The women's Challenger / 125 qualifying cell has 1,343 matches.

* **By era.**
  * TTT: men +3.07, +1.22, +3.87 and +2.90 (2013–16, 2017–19, 2020–21, 2022–26); women +2.79, +2.27, +5.94 and +2.29.
  * Correlated Glicko: men +1.23, −0.31, +4.40 and +2.05; women +2.38, +1.43, +4.98 and +2.11.
* **Observed.** Positive in every era for TTT. Largest in 2020–21, the seasons cut short, when players returned after months away.

## Calibration, 2019–2026

The slope from refitting the result on each forecast's log-odds (1 is perfect; below 1, too confident):

| | Surface Elo | TTT | Correlated Glicko | Glicko-2, match by match | TrueSkill | Glicko-2, weekly |
|---|---:|---:|---:|---:|---:|---:|
| Men | 0.859 | 0.915 | 0.869 | 0.887 | 0.890 | 0.929 |
| Women | 1.035 | 1.000 | 0.943 | 0.984 | 0.959 | 1.061 |

**Observed.**

* **Men.** Every forecast is too confident (slopes 0.84 to 0.93): TTT less than Elo (0.915 against 0.859), the weekly Glicko least (0.929), TrueSkill with correlated surfaces most (0.841, `calibration_slope_2019_2026`).
* **Women.** TTT's slope is 1.000, against Elo's 1.035.

## Where the gain comes from

Better than Elo, milli-log-loss, every evaluation match of 2013–2026 (`diagnostics`):

* **Experience** (the less experienced player's rated matches before the match).
  * Men, TTT: no history +91.65 (727 matches); 1–5 matches +23.73 (2,256); 6–20 +6.71; 21–50 +1.80; 51–100 −1.25; over 100 +2.11 (127,801).
  * Women, TTT: over 100 +2.83 (54,663).
* **Layoffs** (the longer of the two, days since the previous date played).
  * Men, TTT: up to 14 days +1.75 (97,121); 15–35 +2.92; 36–90 +5.14; 91–180 +7.56; 181–365 +13.36; over 365 +4.49 (1,059).
  * Women, TTT: 91–180 +7.41 (1,523).
* **The correlated-surface Glicko** loses badly where a player has no history: −66.12 (men, 727 matches). It also loses after layoffs of over a year: −11.52.

**Observed.** Most of TTT's gain is on experienced players (over 100 matches each), who play most matches. Its largest gains per match come where Elo is weakest: newcomers and players back from a long absence. Elo's K never grows with time away.

**Inferred.** TTT's smoothing re-scores a newcomer's early results once their opponents are better known. Its drift widens a returning player's uncertainty. Elo does neither.

## Why Glicko-2 with weekly rating periods loses

The weekly Glicko-2's log loss minus the match-by-match one (positive: weekly worse), by how many rated matches the players had already played that week, every evaluation match of 2013–2026 (`weekly_overshoot`):

| Earlier matches that week (the larger of the two) | Men: every match | Men: less experienced player 20 or fewer prior | Men: both over 100 prior |
|---|---:|---:|---:|
| none (the first match of the week for both) | +6.90 (67,276) | +71.25 (5,468) | +1.59 (50,656) |
| 1 | +2.42 (40,993) | +72.10 (1,065) | +0.74 (34,867) |
| 2 | +1.00 (25,837) | +118.27 (300) | −0.18 (22,992) |
| 3 or more | −0.04 (21,024) | +121.75 (74) | −0.58 (19,286) |

**Observed.**

* **Where the deficit sits.** It is in matches with an inexperienced player, worse the more matches that player has already played that week. Among players with over 100 matches it is within ±1.6.
* **It already shows in a week's first match,** carried over from the previous week's update.
* **Women.** The same holds for the first match of the week: +43.63 with an inexperienced player (842 matches), +2.57 among veterans. Later rounds have too few inexperienced players to read.

**Inferred.** A week's games scored together around the pre-week rating overshoot when the rating is uncertain. A newcomer winning several rounds is credited for each win as if it were their first. Glickman's guidance asks for 10–15 games per player per period; tennis gives one to five.

## Through the shared harness

milli-log-loss added to the base, walk-forward 2013–2026, with the four-week cluster interval (`stageB_ranking.csv`):

| Row | Men, given Elo | Men, given the market | Women, given Elo | Women, given the market |
|---|---:|---:|---:|---:|
| TrueSkill Through Time | +2.44 (+1.69 to +3.19) | +0.04 (−0.02 to +0.11) | +4.91 (+3.61 to +6.20) | −0.02 (−0.08 to +0.04) |
| the same, two-week events held | +2.41 (+1.67 to +3.15) | +0.04 (−0.02 to +0.10) | +4.74 (+3.42 to +6.05) | −0.02 (−0.08 to +0.04) |
| Glicko, correlated surfaces | +2.52 (+2.04 to +3.01) | +0.01 (−0.03 to +0.05) | +4.28 (+3.40 to +5.16) | −0.02 (−0.08 to +0.04) |
| TrueSkill, correlated surfaces | +2.52 (+2.00 to +3.04) | +0.01 (−0.04 to +0.06) | +4.99 (+3.98 to +5.99) | −0.03 (−0.12 to +0.06) |
| Glicko-2, match by match | +1.17 (+0.79 to +1.55) | +0.08 (+0.01 to +0.16) | +2.41 (+1.69 to +3.13) | +0.00 (−0.04 to +0.05) |
| TrueSkill | +0.82 (+0.46 to +1.17) | +0.07 (−0.01 to +0.14) | +2.94 (+2.13 to +3.76) | −0.01 (−0.06 to +0.04) |
| Glicko-2, weekly periods | +0.30 (+0.02 to +0.57) | +0.05 (−0.01 to +0.12) | +2.61 (+1.91 to +3.32) | −0.01 (−0.07 to +0.05) |

**Surface Elo given each new rating.** TTT: −0.34 (men) and −0.57 (women). Correlated Glicko: +0.44 and +0.16. Match-by-match Glicko-2: +0.43 and +0.14. TrueSkill: +0.78 and −0.00.

**Observed.**

* **Through the harness, the new ratings gain more on Elo than in the raw comparison,** especially for the women (TTT +4.91 against +2.80 raw). The harness refits a weight on each, season by season.
* **TTT makes Elo redundant;** adding Elo to it makes the forecast worse out of sample.
* **Given the market, every rating's gain is between −0.03 and +0.08.** Even the two ratings together with Elo stay in that range (`pair_ttt`: +0.04 men, −0.05 women).

## The earlier leaders, given Elo and given each new rating

milli-log-loss each feature adds to the base (`stageB_ranking.csv`). A feature that adds less given a new rating than given Elo shares information with that rating:

| Feature | Men: given Elo | given TTT | given correlated Glicko | Women: given Elo | given TTT | given correlated Glicko |
|---|---:|---:|---:|---:|---:|---:|
| The men's statistics profile (16 inputs) | +3.97 | +3.78 | +3.61 | +3.53 | +2.17 | +2.48 |
| Serve and return ratings (iid model) | +3.61 | +2.09 | +2.13 | +4.58 | +1.85 | +2.17 |
| Short-memory IOS points matchup | +3.72 | +3.15 | +2.69 | +5.02 | +2.23 | +2.44 |
| Two-week adjusted total points won | +3.19 | +2.98 | +2.80 | +3.32 | +2.20 | +2.46 |
| Games-weighted Elo | +1.82 | +0.04 | +1.12 | +2.38 | −0.16 | +0.98 |
| Points matchup, 52 weeks | +1.55 | +1.13 | +0.93 | +1.59 | +0.71 | +0.82 |
| Sets over 14 days | +1.63 | +1.61 | +1.90 | +1.87 | +1.75 | +2.06 |
| First matches on a surface | +1.45 | +1.27 | +1.86 | +1.30 | +1.01 | +1.62 |
| Age and age squared | +1.42 | +2.79 | +1.54 | +0.56 | +0.99 | +0.64 |

**Observed.**

* **Overlap with TTT.** TTT absorbs almost all of the games-weighted Elo, about two fifths of the men's serve-and-return ratings, and much of the women's point-based features.
* **No overlap.** The context features (recent load, a new surface, age) add as much or more given TTT.
* **The men's statistics profile is almost untouched** (3.97 → 3.78).

**Inferred.**

* **The games-weighted Elo.** It carried a margin of victory and a faster reading of recent form. TTT's smoothing captures the same thing from wins and losses alone.
* **The women's features.** Given TTT they lose more than the men's.

## Problems found in earlier work (reported, not fixed)

* **The shared harness changed while this stage ran** (other work, 2 Oct 2026, 16:48). `stage4_rundown.summarize` and `ufc_ideas/common.py` now give four-week cluster intervals, raw-baseline comparisons and a stricter "finding".
  * The earlier leaders' point estimates, bands and counts still reproduce the predictability diagnostic's ranking exactly.
  * Their ranges do not (largest difference 0.148, all in `lo` / `hi`).
  * `stageB_summary.json` records the hash of the harness this stage ran with.


* **The matches.** The earlier studies' pool: every evaluation-level singles match of 2010–2026 (completed or retired), side A random. It is scored on the evaluation matches of 2013–2026 (155,130 men's, 60,321 women's).
* **Raw comparisons.** Each system's frozen forecast against Stage 1's surface Elo on the same matches, neither refitted. "Better than Elo" is Elo's log loss minus the system's, in milli-log-loss.
* **Intervals.** The 95% interval is clustered by four-week calendar blocks, as the shared harness now computes them. The per-match and calendar-week intervals are in `stageB_summary.json`.
* **The market.** On the matches with odds (tour-level main draws) the market is the closing prices' average, normalised; Pinnacle is a check where it exists. The share of the gap closed is (Elo − system) / (Elo − market).
* **Through the shared harness** (`src/eda/ufc_ideas/common.py`, as revised on 2 Oct 2026):
  * Walk-forward by season; each row added to a base (surface Elo, the market, or a new rating) in a logistic regression without an intercept, refitted on earlier seasons only.
  * 20 shuffled copies as a descriptive band; four-week cluster intervals.
  * The reading: an exploratory "finding" needs a positive clustered lower bound, the heuristic line cleared and three positive eras.
  * The harness's point estimates for the earlier leaders reproduce the predictability diagnostic's ranking. Its ranges do not, because the revision replaced the per-match intervals with clustered ones (`stage4_reference_reproduced`).
