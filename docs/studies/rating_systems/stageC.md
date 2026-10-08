# Stage C: orthogonal to the promising features?

**Status: built 2 Oct 2026.** A study stage, not a decision. The Brief is in the [README](README.md); the report section is Stage C in [report.html](report.html). Every number comes from `data/studies/rating_systems/summary_results.json`, `stageC_ladder_results.csv`, `stageC_market_results.csv` and `stageC_repaired_results.csv`.

Labels: **observed** is measured on the data, **inferred** is a reading of measurements, **suggestion** is a proposal.

## In short

* **Observed. About three quarters of the best ratings' gain over Elo is information the promising features already carry.**
  * On the audit's ladder (men, scored 2022–2026), TTT alone beats calibrated Elo by +2.08 (95% interval +1.33 to +2.83), and the correlated-surface Glicko by +2.44 (+1.58 to +3.30).
  * In the audit's full feature model, swapping Elo for them gains only +0.48 (+0.03 to +0.93) and +0.56 (+0.13 to +0.99).
  * For the women: +2.17 and +1.61 alone; +0.19 and +0.66 in the full model.
* **Observed. The overlap is the serve-and-return ratings.** Given Elo they add +4.74 (men, 2022–2026); given TTT +3.10, given the correlated Glicko +3.00. The other steps add about as much given the new ratings as given Elo; the games-weighted Elo adds more.
* **Observed. Keeping both ratings is worth about a milli-log-loss in the full model.** Elo and TTT together beat the full model with Elo by +1.17 (men; +0.70 to +1.65) and +1.21 (women; +0.32 to +2.10). Elo and the correlated Glicko by +1.28 and +1.82.
* **Observed. No full model gets nearer the closing prices with a new rating.** With Elo as the base, the full model is 9.11 milli-log-loss worse than the raw closing average on the men's matches with odds (2022–2026). With TTT it is 9.22 worse; with the correlated Glicko 8.80.
* **Observed. Against the men's closing line, every rating adds about nothing.**
  * Given calibrated Pinnacle (2019–2026): TTT +0.08 (−0.01 to +0.16), the match-by-match Glicko-2 +0.12 (+0.01 to +0.23), surface Elo +0.02.
  * The 16-input statistics profile adds +0.79 (+0.17 to +1.42) there, and no rating changes that: profile plus TTT against the profile alone, +0.00 (−0.10 to +0.11).
* **Observed. The same on the audit's repaired cohort.**
  * TTT alone beats calibrated Elo by +2.07 (men) and +3.05 (women), 2019–2026. In the full model it adds +0.34 and +0.57, both ranges spanning zero. Both ratings together add +0.75 and +0.97.
  * Against calibrated Pinnacle TTT adds +0.09 (−0.01 to +0.19).
  * The profile's +0.35 (−0.25 to +0.96) reproduces the repairs' published figure (+0.355, −0.251 to +0.961) exactly.
* **Inferred. A better rating is only partly orthogonal to the promising features.**
  * Most of what TTT or the correlated-surface Glicko adds over Elo, the serve-and-return ratings already hold.
  * The rest, about half a milli-log-loss, or about one with both ratings, is new.
  * The statistics profile, the one lead against the odds, is orthogonal to every rating tried.

## The ladder, scored 2022–2026

milli-log-loss, with the 95% interval clustered by calendar week (`stageC_ladder_results.csv`; 63,336 men's and 23,379 women's matches):

| | Men: TTT | Men: correlated Glicko | Men: Glicko-2, match by match | Women: TTT | Women: correlated Glicko |
|---|---:|---:|---:|---:|---:|
| The base alone, against calibrated Elo | +2.08 (+1.33 to +2.83) | +2.44 (+1.58 to +3.30) | +1.15 (+0.41 to +1.90) | +2.17 (+0.79 to +3.55) | +1.61 (−0.01 to +3.22) |
| Plus the serve-and-return ratings, against the same with Elo | +0.44 (−0.09 to +0.97) | +0.70 (+0.09 to +1.31) | −0.29 (−0.80 to +0.23) | +0.88 (−0.19 to +1.95) | +0.48 (−0.76 to +1.72) |
| The full model, against the full model with Elo | +0.48 (+0.03 to +0.93) | +0.56 (+0.13 to +0.99) | +0.00 (−0.31 to +0.32) | +0.19 (−0.56 to +0.94) | +0.66 (−0.17 to +1.48) |
| Both ratings in the full model, against the full model with Elo | +1.17 (+0.70 to +1.65) | +1.28 (+0.83 to +1.73) | +0.61 (+0.27 to +0.95) | +1.21 (+0.32 to +2.10) | +1.82 (+0.87 to +2.77) |
| The full model against the raw closing average (matches with odds) | −9.22 | −8.80 | −9.47 | −7.12 | −6.92 |

With Elo as the base:

* the full model gains +11.10 (men) and +9.49 (women) on calibrated Elo;
* it stands −9.11 and −6.92 against the closing average.

**What each step adds, given each base** (men, 2022–2026):

| Step | Given Elo | Given TTT | Given correlated Glicko |
|---|---:|---:|---:|
| Serve and return ratings | +4.74 | +3.10 | +3.00 |
| Two-week adjusted points won | +1.03 | +1.03 | +1.12 |
| Short-memory IOS matchup | +0.13 | +0.11 | +0.06 |
| Games-weighted Elo | +0.31 | +0.55 | +0.60 |
| Sets over 14 days, first matches on a surface, age | +4.90 | +4.71 | +4.43 |

For the women: the serve-and-return step is +3.12 given Elo, +1.82 given TTT and +1.99 given the correlated Glicko. The others are about the same.

**Scored 2019–2026** (`summary_results.json`, `orthogonality`):

* Men, the full model against the one with Elo: TTT +0.46 (+0.04 to +0.88), correlated Glicko +0.69 (+0.30 to +1.08); with both ratings +1.15 and +1.44.
* Women: +0.63 (−0.05 to +1.31) and +0.94 (+0.21 to +1.68); with both ratings +1.57 and +1.97.

**Weaker ratings fall away in the full model:** the match-by-match Glicko-2 +0.02, TrueSkill −0.03, the weekly Glicko-2 −0.21 (men, 2019–2026).

## The men's closing line

Gain over the calibrated closing price, milli-log-loss, calendar-week intervals; the audit's shared rows (`stageC_market_results.csv`). 16,776 matches in 2019–2026 and 10,503 in 2022–2026:

| Added to the closing price | Pinnacle 2019–2026 | Pinnacle 2022–2026 | Average 2019–2026 |
|---|---:|---:|---:|
| Surface Elo | +0.02 (−0.01 to +0.05) | +0.04 (−0.00 to +0.08) | +0.02 (−0.01 to +0.04) |
| TrueSkill Through Time | +0.08 (−0.01 to +0.16) | +0.12 (+0.00 to +0.23) | +0.07 (−0.01 to +0.15) |
| Glicko, correlated surfaces | +0.02 (−0.03 to +0.08) | +0.08 (+0.00 to +0.16) | +0.05 (+0.00 to +0.09) |
| Glicko-2, match by match | +0.12 (+0.01 to +0.23) | +0.17 (+0.02 to +0.32) | +0.11 (+0.00 to +0.21) |
| TrueSkill | +0.10 (−0.01 to +0.20) | +0.15 (+0.01 to +0.29) | +0.09 (−0.00 to +0.19) |
| The 16-input statistics profile | +0.79 (+0.17 to +1.42) | +0.85 (+0.05 to +1.64) | +0.86 (+0.21 to +1.52) |
| The profile plus TTT, against the profile | +0.00 (−0.10 to +0.11) | +0.03 (−0.13 to +0.19) | −0.03 (−0.11 to +0.05) |
| The profile plus correlated Glicko, against the profile | −0.03 (−0.12 to +0.07) | −0.00 (−0.16 to +0.15) | −0.06 (−0.14 to +0.01) |

**Observed.** Every rating's gain on the closing line is under two tenths of a milli-log-loss. Even the largest, 0.17, is under 1% of the 22.46 milli-log-loss between Elo and the market. With the profile in the model, no rating adds anything.

## On the repaired cohort

The audit's repairs (`stageC_repaired_results.csv`): main-tour matches with trusted match dates, every feature rebuilt in match-day order. Intervals are clustered by four-week blocks. Scored 2019–2026 on 18,174 men's and 16,675 women's matches; the market part on 16,333 men's matches with both prices.

| | Men | Women |
|---|---:|---:|
| The repairs' own Elo (dated history only), against calibrated Stage 1 Elo | −18.26 (−21.56 to −14.97) | −16.25 (−19.10 to −13.40) |
| TTT alone, against calibrated Elo | +2.07 (+0.66 to +3.48) | +3.05 (+1.27 to +4.83) |
| TTT: the full model against the full model with Elo | +0.34 (−0.58 to +1.25) | +0.57 (−0.74 to +1.88) |
| TTT and Elo together in the full model | +0.75 (+0.21 to +1.30) | +0.97 (+0.06 to +1.88) |
| Correlated Glicko alone, against calibrated Elo | +3.30 (+1.24 to +5.36) | +2.17 (+0.15 to +4.20) |
| Correlated Glicko: the full model against the full model with Elo | +0.31 (−1.05 to +1.67) | −0.08 (−1.62 to +1.46) |
| Correlated Glicko and Elo together in the full model | +1.15 (+0.26 to +2.05) | +0.91 (−0.03 to +1.84) |
| Glicko-2 match by match: the full model against the one with Elo | −1.60 (−2.43 to −0.77) | −0.57 (−1.76 to +0.61) |

**The men's closing line on the repaired cohort, 2019–2026.** Given calibrated Pinnacle:

* the profile +0.35 (−0.25 to +0.96);
* surface Elo −0.00, TTT +0.09 (−0.01 to +0.19), the match-by-match Glicko-2 +0.11 (+0.00 to +0.23);
* the profile plus TTT against the profile alone, +0.08 (−0.03 to +0.19).

**Observed.**

* **A history of dated main-tour matches alone cripples a rating.** The repairs' own Elo is 18 milli-log-loss worse than Stage 1's, so the full-history ratings are the fair comparators here.
* **The same pattern as on the full cohort.** The best ratings beat calibrated Elo alone, add little once the features are in, and add about a milli-log-loss when kept beside Elo.

A new rating could beat Elo in two ways:

* **By carrying what the promising features carry.** Then the features add less given it, and a model holding the features gains nothing from the swap.
* **By carrying something they lack.** Then the features add as much given it, and the model keeps the rating's gain.

The owner asked for the most predictive rating that is "similarly orthogonal" to the promising features, so both readings are measured. The audit's own machinery is imported unchanged:

1. **The ladder** (`src/eda/feature_alpha_audit/elo_retest.py`). On the audit's common complete cases (every ladder input present; evaluation-level matches from 2013), annual expanding logistic fits from 2013 are scored from 2019, with training-RMS scaling, no intercept, and intervals clustered by calendar week.
   * Each base rating R goes through the audit's steps: R alone (its slope refitted each season); + the serve-and-return ratings through the iid model; + the two-week opponent-adjusted total points won; + the short-memory IOS points matchup; + the games-weighted Elo; + sets over 14 days, the first matches on a surface, age and age squared (the full model).
   * Also Elo and R together as the base.
2. **The closing line, men** (`src/eda/feature_alpha_audit/profile_retest.py`). On the audit's shared rows (both the average and Pinnacle, and the 16-input profile present), the market's log-odds are an unpenalised input, with a ridge on the others chosen from the two preceding seasons. Models: R given the market; the 16-input profile; the profile with R as one more input.
3. **The repaired cohort** (`src/eda/feature_alpha_audit/repair_score.py`). The audit's repairs of 2 Oct 2026 rebuilt the shortlist on main-tour matches with trusted match dates (78,706 matches), every feature in match-day order. Parts 1 and 2 are run again there.
   * The repairs' own Elo, built from that dated history only, is shown for reference. The fair comparator for this study's ratings is Stage 1's Elo: both use the full 2010–2026 history under the event-start time rule.
   * For a filtering rating (Elo, Glicko, TrueSkill, the correlated-surface ratings), that rule cannot carry an overlapping event's later rounds into another player's rating, because a rating moves only with the player's own matches. TrueSkill Through Time's smoothing can, which is what the [hold sensitivity](stageA.md) addresses.
