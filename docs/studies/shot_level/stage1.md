# Stage 1: shot-level statistics, built from the points

**Status: built 2 Oct 2026, waiting for the owner's review.** A study stage, not a decision. The owner asked on 2 Oct 2026 for the features to be built and tested directly ("build more features from the shot by shot or point by point data ... trainable at a match level that we currently don't have"). That request replaced the approval step the [candidate list](candidates.md) had proposed; the statistics below take that list's ideas further. The Brief is in the [README](README.md); the features and their scores are in [Stage 2](stage2.md).

Labels: **observed** is measured on the data, **inferred** is a reading of measurements, **suggestion** is a proposal for the owner. The tables are generated from the stage's files (`data/studies/shot_level/stage1_tables.md`, by `src/eda/shot_level/stage2_tables.py`, from `stage1_points_census.csv`, `stage1_agreement.csv`, `stage1_stats_summary.json`, `stage1_reliability.csv` and `stage2_constants.json`).

## In short

* **Observed. One point table from eight sources.** It holds 38,293 matches and 6,178,876 points, every source mapped to one convention:
  * a point's rally length counts the serve and the shot that ended it;
  * a serve won without an ace is a forced error by the returner;
  * every winner and error belongs to the player who hit it.
* **Observed. The sources agree once the convention is shared.** Point by point, on matches two sources hold:
  * rally lengths match exactly on 81–100% of points, and fall on the same side of 5 and 9 shots on 95–100%;
  * winner or error matches on 96–100%, and who ended the point on 100%;
  * serve number and speed match on 99–100%;
  * forced or unforced matches on 76–100% of errors, and on 76–87% between independent scorers. That split is a judgement the sources make differently, so the statistics avoid it (below).
* **Observed. 25 statistics per player and match, for 30,044 matches of the earlier studies' table.** Up to 19,539 men's and 10,042 women's matches, in eight families: rally length, how points end, serve speed, net play, serve placement, return depth, the wing, and the point sequence.
* **Observed. Almost all are stable traits of a player.** A player's rate in half their matches predicts the other half:
  * the shot statistics at 0.38 to 0.99, the split-half correlation (net points won by the women lowest, serve speed highest);
  * returns put in play at 0.86–0.91;
  * holding after a break, breaking back and holding for the set at 0.31–0.52.

  Only the pressure statistics are weak or absent:
  * serving under pressure 0.17 for the men, chance for the women;
  * first serves in under pressure 0.22 and 0.30;
  * serving after a lost point indistinguishable from chance on both tours.

## Terms used here

* **Rally length.** The shots in a point, the serve counted as shot 1 and the shot that ended the point counted: an ace is 1, a double fault 0, a missed return 2, a return winner 2.
* **Rally point, or the return in play.** A point in which the return came back: 3 shots or more, or a return winner. Aces, double faults and missed returns are not rally points; the box scores already count them.
* **Winner, forced error, unforced error.** How a point ends when the ball is in play: a shot the opponent cannot reach; a miss the opponent's shot caused; a miss under no pressure. The last two are a scorer's judgement.
* **Excess.** For the three pressure statistics, the player's rate on the points in question minus the same player's rate in the same match: serve points won at 30-30, deuce or break point, minus all serve points won. Positive means better under pressure than usual.
* **Split-half correlation.** Each player's matches split alternately in two; the correlation, across players with 30 matches or more, of the two halves' rates. Near 1 a statistic is a trait; near 0 it is chance. The chance band comes from shuffling the halves across players.
* **K.** The shrinkage constant: a player's own rate counts half against the average when their history holds K units (points, serves or games). Estimated without reading a result: from the spread between player-seasons against binomial noise, or for the excesses from the split-half correlation (below).

## The sources and the shared convention

**Observed** (`stage1_points_census.csv`). The share of each source's points carrying each field:

| Source | Matches | Points | Rally length | Ending | Serve number | Serve speed | Net | Wing |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Volunteer charts | 9,406 | 1,437,120 | 100% | 100% | 100% | 0% | 100% | 87% |
| Sackmann's Slam files | 10,508 | 1,910,897 | 68% | 100% | 87% | 72% | 81% | 15% |
| Wimbledon / US Open feeds | 5,162 | 881,597 | 80% | 100% | 95% | 64% | 100% | 87% |
| AO / RG Hawk-Eye copy | 2,027 | 369,452 | 97% | 100% | 100% | 94% | 0% | 90% |
| Infosys (tour level) | 5,052 | 706,217 | 100% | 90% | 100% | 97% | 99% | 0% |
| SirGenkii | 908 | 133,560 | 100% | 100% | 100% | 37% | 4% | 0% |
| TDI | 4,698 | 665,479 | 98% | 98% | 94% | 0% | 99% | 60% |
| AO match centre | 532 | 74,554 | 11% | 100% | 0% | 0% | 0% | 89% |
| All | 38,293 | 6,178,876 | | | | | | |

**How the convention was set** (`src/eda/shot_level/points.py`; checked in `stage1_agreement.csv`). Each rule was read from the data on matches two sources hold, aligned point by point:

* **Counting shots.** The volunteer charts and Infosys count the shot that ended the point. The IBM feeds (Sackmann's Slam files, the Wimbledon and US Open feeds), Hawk-Eye's copy at the Slams and TDI count only shots that landed in, so 1 is added to points that end in an error. With the rule, the charts and the Wimbledon / US Open feeds agree on rally length on 95% of points (table below).
* **The Australian Open and Roland Garros files of 2018–2021** record an ace's rally as 0; it is set to 1.
* **Forced errors.** Sackmann's Slam files flag winners and unforced errors on every point but forced errors only in 2011. Every other point of a flagged match is a forced error by the player who lost it: against Hawk-Eye's own classification of the same points, winner or error then agrees on 99% and forced or unforced on 100%.
* **Serves won without an ace** are forced errors by the returner on shot 2 in every source, as the IBM feeds and Hawk-Eye classify them (the charts' '#' after a serve, Infosys's unclassified serve points, Hawk-Eye's 'winner' on shot 1).
* **The Wimbledon and US Open feeds** name forced errors and the wing only in a sentence ("A. Gray loses the point with a forehand forced error"), which is parsed.
* **Hawk-Eye's copy at the Slams** lists each first-serve fault as a row; those rows are dropped. Roland Garros match codes repeat every year, so the key is the Slam, the year and the code. This also corrected Stage 0's count for this source; its tables were regenerated.
* **SirGenkii's** results and points tables write player ids in different cases, and its calendar starts several events weeks early. Matches are dated by their event's last day.

**Observed. Agreement on matches two sources hold** (`stage1_agreement.csv`; pairs with 20 or more aligned matches; a match is aligned when the two sources agree on the server and the point winner of at least 98% of its points):

| Pair | Matches aligned | Points | Rally equal | Same side of 5 shots | Same side of 9 shots | Winner or error | Forced or unforced | Who ended it | Serve number | Speed within 2 km/h | Placement | Net | Return depth | Wing | Errors per point, ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Sackmann's Slam files / Wimbledon / US Open feeds | 2,021 | 370,793 | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 98% | 100% | 100% | 1.00 |
| Sackmann's Slam files / AO / RG Hawk-Eye copy | 728 | 126,817 | 94% | 95% | 98% | 99% | 100% | 100% | 100% | 99% | – | – | – | – | 0.99 |
| Sackmann's Slam files / Volunteer charts | 1,414 | 267,153 | 92% | 96% | 98% | 98% | 85% | 100% | 100% | – | 75% | 91% | 90% | 96% | 0.97 |
| Wimbledon / US Open feeds / Volunteer charts | 671 | 121,931 | 95% | 98% | 99% | 98% | 84% | 100% | 100% | – | 74% | 91% | 91% | 97% | 0.97 |
| AO / RG Hawk-Eye copy / Volunteer charts | 509 | 97,793 | 96% | 98% | 99% | 99% | 87% | 100% | 99% | – | 87% | – | – | 97% | 0.99 |
| Volunteer charts / Infosys (tour level) | 398 | 52,808 | 81% | 98% | 99% | 96% | 76% | 100% | 100% | – | – | 89% | – | – | 1.02 |
| Volunteer charts / SirGenkii | 110 | 16,070 | 91% | 100% | 100% | 98% | 85% | 100% | 100% | – | – | 85% | – | – | 1.00 |
| Volunteer charts / TDI | 23 | 3,129 | 99% | 100% | 100% | 98% | 86% | 100% | 100% | – | – | 91% | – | 98% | 1.00 |
| Infosys (tour level) / SirGenkii | 22 | 2,967 | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% | – | 94% | – | – | 1.00 |

* **Inferred.** Rally lengths, winners against errors, who ended a point, serve numbers and speeds are measured alike. Total errors per point differ by at most 3% between sources (the last column).
* **Inferred.** Forced against unforced is not measured alike: 76–87% between the volunteer charts and the feeds. Infosys's error labels are the least comparable (76%). Statistics that split errors are therefore within-match shares, where a source's lean cancels.
* **Inferred.** Placement agrees on 74–87%: the zones are drawn differently. Its two statistics are the least comparable across sources.

## The statistics

Per player and match, as a count over a count (`src/eda/shot_level/stats.py`). A match carries a family when it carries the family's field on most points: 90% for rally length, endings and net play, half for speed, placement, return depth and the wing. Where several sources hold a match, each statistic comes from the first of: the volunteer charts, Hawk-Eye's copy, the Wimbledon and US Open feeds, Sackmann's Slam files, Infosys, SirGenkii, TDI, the Australian Open's match centre.

* **Rally length:**
  * quick points won on serve and on return: rally points won within 4 shots, over the player's rally points on serve or on return;
  * rally points won: points of 5 shots or more won, over all such points;
  * long-rally points won: the same for 9 shots or more;
  * returns put in play: over the opponent's serves that were neither aces nor double faults;
  * the share of long points (5 shots or more): a style, the same for both players in a match.
* **How points end:**
  * winners per point (aces excluded);
  * errors per point, forced and unforced together (double faults excluded);
  * the player's share of the match's unforced errors: within the match, so a source's lean on forced against unforced cancels;
  * winners over winners plus errors.
* **Serve speed:** the average speed of first serves in, and of second serves in.
* **Net play:** net approaches per point, and net points won.
* **Serve placement:** the share of first serves in to the T, and out wide.
* **Return depth:** the share of returns in play that land deep.
* **The wing:** the backhand's share of the player's unforced errors, and the forehand's share of their winners.
* **The point sequence** (a match's points reconstructed into games and sets; a match whose sets do not add up is left out):
  * holds right after breaking serve;
  * breaks back right after being broken;
  * holds when winning the game wins the set;
  * the three pressure excesses: serve points won at 30-30, deuce or break point; first serves in on those points; serve points won right after losing one.

**Observed** (`stage1_stats_summary.json`, `stage1_reliability.csv`, `stage2_constants.json`). Matches carrying each statistic, its average, the split-half correlation, and K:

| Statistic | Family | Matches, men | Matches, women | Average | Split-half r, men | Split-half r, women | K, men | K, women |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Quick points won on serve | rally | 17,445 | 7,722 | 0.247 | 0.77 | 0.65 | 41 | 38 |
| Quick points won on return | rally | 17,445 | 7,722 | 0.234 | 0.72 | 0.76 | 44 | 41 |
| Rally points won (5+ shots) | rally | 16,437 | 6,797 | 0.500 | 0.68 | 0.56 | 158 | 224 |
| Long-rally points won (9+ shots) | rally | 16,402 | 6,773 | 0.500 | 0.55 | 0.45 | 152 | 192 |
| Returns put in play | rally | 17,445 | 7,722 | 0.776 | 0.86 | 0.91 | 88 | 65 |
| Share of long points (style) | rally | 17,446 | 7,722 | 0.375 | 0.85 | 0.81 | 21 | 20 |
| Winners per point | ending | 18,105 | 10,042 | 0.122 | 0.73 | 0.84 | 395 | 178 |
| Errors per point | ending | 18,105 | 10,042 | 0.324 | 0.85 | 0.89 | 302 | 157 |
| Share of the match's unforced errors | ending | 18,101 | 10,041 | 0.500 | 0.90 | 0.91 | 45 | 33 |
| Winners / (winners + errors) | ending | 18,104 | 10,042 | 0.275 | 0.70 | 0.79 | 225 | 129 |
| First-serve speed | speed | 10,211 | 4,669 | 178.6 km/h | 0.99 | 0.99 | 2 | 1 |
| Second-serve speed | speed | 10,179 | 4,634 | 148.0 km/h | 0.98 | 0.98 | 1 | 1 |
| Net approaches per point | net | 17,686 | 8,528 | 0.100 | 0.94 | 0.88 | 52 | 88 |
| Net points won | net | 17,666 | 8,509 | 0.660 | 0.55 | 0.38 | 104 | 155 |
| First serves to the T | placement | 8,430 | 6,444 | 0.379 | 0.91 | 0.94 | 70 | 34 |
| First serves out wide | placement | 8,430 | 6,444 | 0.397 | 0.86 | 0.88 | 47 | 27 |
| Deep returns | return | 6,932 | 5,501 | 0.327 | 0.79 | 0.77 | 52 | 67 |
| Backhand share of unforced errors | stroke | 11,692 | 6,734 | 0.431 | 0.60 | 0.73 | 131 | 88 |
| Forehand share of winners | stroke | 11,692 | 6,734 | 0.692 | 0.87 | 0.90 | 52 | 36 |
| Holds right after breaking | sequence | 19,193 | 9,890 | 0.761 | 0.43 | 0.49 | 24 | 29 |
| Breaks back right after being broken | sequence | 19,193 | 9,890 | 0.239 | 0.38 | 0.52 | 86 | 66 |
| Holds when serving for the set | sequence | 17,864 | 8,965 | 0.802 | 0.33 | 0.31 | 17 | 32 |
| Serve points won under pressure (excess) | sequence | 19,528 | 9,900 | +0.008 | 0.17 | 0.05 (chance) | 3,996 | 12,151 |
| First serves in under pressure (excess) | sequence | 19,230 | 9,625 | +0.007 | 0.22 | 0.30 | 2,943 | 1,458 |
| Serve points won after a lost point (excess) | sequence | 19,539 | 9,900 | +0.004 | 0.09 (chance) | -0.00 (chance) | 12,730 | ∞ |

* **Observed.** Every statistic but serving after a lost point (both tours) and serving under pressure (women) repeats beyond chance. "(chance)" marks a correlation inside the chance band.
* **Observed.** The pressure excesses spread less between player-seasons than binomial noise alone would, so the usual estimate gives no K. Their K comes from the split-half correlation instead: K = D (1 − r) / r, with D a half's mean count.
  * Fewer than 100 players had 30 such matches before 2019, so these three use all seasons. No result enters, but the constant is not confined to the years before scoring.
  * Serving after a lost point gets an infinite K for the women, so its feature is constant.
* **Inferred.** Serve speed, returns put in play and net approaches are near-perfect traits: they describe how a player plays. Whether they say who wins beyond Elo and the odds is Stage 2's question.

## What was built

| File | What it holds |
|---|---|
| `stage1_points_<source>.parquet` (eight files) | The common point table, one per source (schema in `points.py`) |
| `stage1_points_census.csv` | Per source and year: points, and the share carrying each field and each kind of ending |
| `stage1_agreement.csv`, `.json` | Per pair of sources: matches aligned, and agreement on every field |
| `stage1_match_stats.parquet` | One row per player-match (60,088 rows, 30,044 matches): every statistic's numerator, denominator and source |
| `stage1_stats_summary.json` | Per statistic: matches by tour and year, the average, the sources used |
| `stage1_reliability.csv` | Per statistic and tour: the split-half correlation and its chance band |
| `stage1_tables.md` | This write-up's tables |

Code in `src/eda/shot_level/`: `points.py` (the adapters), `stats.py` (the statistics), `stage1_points.py` (about 1½ minutes with 5 workers), `stage1_agreement.py`, `stage1_stats.py` and `stage1_reliability.py` (seconds each). Tests: `test/shot_level/test_stage1.py`, on hand-made points whose statistics were worked out by hand: the charts' shot strings, the feeds' sentences, Infosys's shot groups, every statistic of one match, and a two-set sequence's breaks, holds and pressure points.

## Limitations

* **Error labels are a judgement.** Statistics built on forced against unforced (the share of unforced errors, the backhand's share of them) are shares within a match or within the player's own errors, so a source's lean cancels; a scorer's lean within one match does not.
* **One source per statistic per match.** The order of preference is fixed (the volunteer charts first). A player's history can still mix sources from match to match; the agreement table bounds what that can do.
* **Gates drop matches.** A match carrying a field on fewer points than the gate contributes nothing to that family (Infosys's unclassified points, the half-filled rally counts at Wimbledon 2022–2024).
* **Return depth and placement** come from fewer sources, and placement's zones differ between them.
* **No ball tracking yet.** Court Vision's ATP files use obfuscated field names, and the Hawk-Eye copy's trajectories were not turned into statistics. Stage 0 found that family too thin to test against the odds.
