# Candidate list: shot-level statistics to build and test

**Status: superseded on 2 Oct 2026.** The owner asked the same day for the features to be built and tested directly, without this approval step. What was built is in [Stage 1](stage1.md) (25 statistics, including these 14 ideas) and [Stage 2](stage2.md) (141 features scored with the earlier studies' harness). This page is kept as the record of the proposal. It was written before anything was compared with who won; the only numbers behind it are Stage 0's coverage counts ([stage0.md](stage0.md); `data/studies/shot_level/stage0_summary.json`).

Labels as in the [README](README.md): **observed**, **inferred**, **suggestion**.

## In short

* **14 statistics in four families:** rally length (5), how points end (3), serve speed (3) and net play (2), plus one weakness measure. Each is built per player and match as a count over a count, so it can be shrunk and opponent-adjusted like the box-score statistics.
* **Each in two memories, opponent-adjusted:** a two-week half-life (the memory of the men's box-score lead) and the last 52 weeks. Six statistics also get their defensive mirror: what opponents manage against the player, against the opponents' own norm. Offence and defence, as in the UFC study's adjperf and adjdef.
* **Two primary tests, fixed now:**
  * the two-week offence profile against the closing odds;
  * the same profile against the closing odds plus the box-score profile, on the same matches.

  The second says whether shot-level data adds anything the box scores do not, which is the question behind buying more of it.
* **Scored with the feature-alpha audit's repaired protocol:**
  * only matches with a confirmed match day, from 2019;
  * the calibrated average line and Pinnacle's;
  * clustered intervals;
  * profiles with a ridge penalty chosen on earlier seasons;
  * every definition frozen before Stage 2 reads a result.
* **Deferred:** serve placement, return depth, the stroke mix beyond one weakness measure, and ball tracking. They are thinner (Stage 0), or need decoding first.

## Why these

* **Inferred from Stage 0.** On the matches with odds, the families with the most scorable matches are:
  * how points end: 79% (men) and 75% (women);
  * net play: 74% and 65%;
  * rally length: 63% and 52%;
  * serve speed: 60% and 44%.

  These can detect a gain of about 0.75–1.3 milli-log-loss each over 2013–2026. Placement, return depth and the stroke mix reach 35–52%; ball tracking 27% and 5%.
* **The owner's thesis (30 Sep and 2 Oct 2026):** offensive and defensive ratings of individual statistics within a match, tested jointly against the odds, never points-won or win-rate aggregates. Every statistic here is one way of winning or losing points that a box score cannot see:
  * how quickly, for rally length;
  * by whose shot, for endings;
  * with how much pace, for serve speed;
  * from where on the court, for net play.
* **What the box scores already hold** is left out: aces, double faults, first serves in, first- and second-serve points won, and break points. A shot-level statistic that only restates them (an ace is a one-shot point) would add nothing new, so each statistic below excludes them where they overlap.

## The statistics

Per player and match, as numerator / denominator. A point's **length** counts the serve as shot 1. A **rally point** is one in which the return was in play: it lasted 3 shots or more, or ended on shot 2 with a return winner. Aces, unreturned serves, double faults and return errors, which the box score already holds or which end before a rally exists, are left out of every rate below. **Mirror**: the same statistic for the player's opponents in their matches against the player, scored against those opponents' own norm (the defence side).

| # | Statistic | Numerator / denominator | Mirror | Family | Why the odds might miss it | Expected sign |
|---|---|---|---|---|---|---|
| 1 | Quick points won on serve | the player's serve rally points that ended within 4 shots in the server's favour / the player's serve rally points | yes: how often opponents' serve-plus-one beats the player | rally length | The serve's follow-up once the return comes back, invisible in a box score, which counts only aces and serve points won | + |
| 2 | Quick points won on return | the player's return rally points that ended within 4 shots in the returner's favour / the player's return rally points | yes | rally length | Return pressure that ends points at once. The box score's return points won mixes it with aces and long rallies | + |
| 3 | Rally points won | points of 5 or more shots won / points of 5 or more shots | – (the opponent's is its complement) | rally length | The baseline game, apart from serve and return | + |
| 4 | Long-rally points won | points of 9 or more shots won / points of 9 or more shots | – | rally length | Endurance and consistency under length; 12.7% of points (Stage 0) | + |
| 5 | Long-rally edge where long rallies are likely | (A's long-rally points won − B's, both shrunk) × the expected share of 9+ shot points in this match, from both players' rally lengths | – | rally length | An interaction: the edge counts only when the match will be played from the back. A sum of ratings cannot see it | + |
| 6 | Winners | winners, excluding aces and unreturned serves / rally points played | yes: winners conceded | endings | Aggression that wins points, apart from the serve | + |
| 7 | Unforced errors | unforced errors / rally points played | yes: unforced errors drawn from opponents | endings | Consistency; how much a player gives away | − |
| 8 | Forced errors drawn | the opponent's forced errors / rally points played | yes: forced errors made | endings | Pressure that wins points without winners | + |
| 9 | First-serve speed | mean speed of first serves in (km/h) | – | speed | Pace as such; box scores see only its results | + |
| 10 | Second-serve speed | mean speed of second serves in | – | speed | The risk taken on the second serve | + |
| 11 | Serve-speed change | mean first-serve speed over the last two weeks minus the player's own over the 52 weeks before | – | speed | A state signal: a drop can mean fatigue or an injury the odds may price late. Exists only with recent speed data (13-week coverage: 26% men, 8% women) | + |
| 12 | Net approaches | points at which the player came to the net / rally points played | – | net | Style; whether a player can shorten points | ? |
| 13 | Net points won | net points won / net points played | yes: how opponents fare at the net against the player (passing shots) | net | Finishing at the net, apart from approaching | + |
| 14 | Backhand share of unforced errors | backhand unforced errors / unforced errors with the wing known | – | stroke | Where a player breaks down; narrow (stroke mix scorable in 50% men, 35% women) | − |

**Sources and what they can give** (Stage 0's families, from `stage0_sources.json`):

* **Rally length (statistics 1–5):** the volunteer charts (shot counts), the Grand Slam files and feeds (rally counts), Infosys (the shot that ended the point, grouped "9+ odd" and "10+ even", which is enough for "9 or more"), the Court Vision Slam copy, SirGenkii, TDI.
* **Endings (6–8):** every source with endings. Totals from the WTA's advanced statistics (from 2022) and Infosys's key statistics. Forced errors are not flagged in the Wimbledon and US Open feeds or in Infosys's key statistics, so statistic 8 is thinner there. Stage 1 checks whether "neither winner nor unforced error" can stand in for them on matches charted twice.
* **Speed (9–11):** the Slam files and feeds, Infosys, the Court Vision Slam copy, SirGenkii (some events).
* **Net (12–13):** the charts, the Slam files and feeds, TDI, Infosys's key statistics (net points won only), the WTA's advanced statistics (from 2025).
* **Backhand errors (14):** the charts, Infosys's stroke summaries, TDI, the Australian Open match centre, the WTA's advanced statistics (from 2025).

## Forms

* **Opponent-adjusted (adjperf), two memories.** Each match's rate is restated against what that opponent usually allows, as in the UFC study's Stage B. It is then summed with weights:
  * exponentially decayed with a **two-week half-life**, the men's lead;
  * over the **last 52 weeks**.

  It is shrunk toward the tour's mean with a constant estimated by the predictability diagnostic's Stage 3 method on history before 2019.
* **Speed** is a level, not a share. It is shrunk with a normal–normal constant estimated the same way, and adjusted for the event's surface average.
* **Serve-speed change** has its own definition (above): one memory.
* **Existence:** a statistic exists for a player when at least one earlier match carries its family in the form's memory. A match is scored when both players have it, as in the earlier studies. Stage 0's coverage with k = 3 is the realistic count.
* **Sides:** every input enters as A − B; no intercept.

## The rows to score

* **Single rows (reading only, not for selection):** 14 statistics × 2 memories + 6 mirrors × 2 memories = 40 rows per tour (the serve-speed change has one memory, so 39 in fact). The family-wide line is built over these, as in the earlier studies.
* **Profiles:**

| Model | Inputs | Role |
|---|---|---|
| P1: offence profile, two-week memory | statistics 1–14 (13 inputs; the speed change is a separate model) | **primary test 1**, given the odds |
| P1 given the box-score profile | P1, on top of the closing odds plus the men's 16-input box-score adjperf profile (Stage D; the women's equivalent) | **primary test 2**: does shot-level data add to box scores? |
| P2: offence profile, 52 weeks | statistics 1–14 | secondary |
| P3: offence and defence, two-week | P1 + 6 mirrors | secondary |
| P4–P7: one family at a time | rally (1–5), endings (6–8), speed (9–11), net (12–13) | secondary: which family carries any gain |

## Scoring protocol (Stage 2)

1. **The pool, time rule and scorer: the feature-alpha audit's repaired ones** ([repairs](../feature_alpha_audit/repairs.md)), unless the owner rules otherwise:
   * only matches with a confirmed match day, as targets and as history;
   * history ordered by match day;
   * pre-match match format from the scheduled-format rules;
   * its paired scorer.

   Under these rules Stage 0 counts 14,500 men's and 13,967 women's scorable matches with odds from 2019 on (any family, 52 weeks, k = 3).
2. **Bases:**
   * the closing odds: the calibrated average line, and Pinnacle's, raw and calibrated, on the matches with both (the headline);
   * surface Elo, reported but not headlined.
3. **The comparator for primary test 2:** the audit's repaired box-score profile (its rebuilt 16 adjperf and adjdef inputs, `repair_features.parquet`). The women's equivalent is built the same way.
4. **Intervals** clustered by calendar blocks, as the audit's repaired scorer does, beside the harness's independent-match intervals.
5. **Profiles** fitted with a ridge penalty chosen only from earlier seasons; scaling from training data only.
6. **Seasons:**
   * statistics' constants from history before 2019, frozen;
   * scored from 2019 on, as the audit's market comparisons are, with 2022–2026 as a second window;
   * the women's endings from the WTA's statistics exist from 2022.
7. **Reading:**
   * a **lead** is a primary test whose gain on the odds is positive with its clustered interval above zero, from 2019 and in 2022–2026;
   * everything else is descriptive;
   * results are ranked by the gain on the odds; gains on Elo are reported, never headlined.
8. **Frozen before scoring:** this list, the memories, the constants and the protocol. Any change after Stage 2 reads a result is reported as a change.

## Stage 1: what gets built and checked first (no results read)

1. **The statistics, per player and match, from every source,** in one table with the source kept.
2. **Agreement between sources on the matches two of them hold:**
   * the Slam files and the Wimbledon and US Open feeds, 2019–2024;
   * the charts against the feeds, Infosys, SirGenkii and the Court Vision copy;
   * TDI against the charts.

   Systematic gaps get a per-source correction or an exclusion, decided before Stage 2.
3. **Reliability:** each statistic's split-half correlation within player-seasons, against a pure-luck replay where one exists (the predictability diagnostic's Stage 3 method). A statistic that does not repeat cannot predict.
4. **Redundancy with what the market already holds, in feature space:** how much of each pre-match statistic (A − B) the odds' log-odds, surface Elo and the box-score profile explain together (R²). These are all pre-match quantities, so no result is read. A statistic the odds already hold cannot add to them; an independent one may or may not.
5. **The leak probes** of the earlier studies (cut by date, event and round) on every new feature family.

## Optional, for the owner: a point-share screen

* **Suggestion.** A second, more sensitive test beside the match-winner log loss: does a statistic predict the share of points a player wins, beyond what the closing odds imply for it? The odds can be turned into an expected share of points through the earlier study's iid model.
* **Inferred, from the arithmetic, not measured.** It would carry about 1.7 times the information per match of the result. It strips out how the points fell into games and sets, but not the luck of each point.
* **The cost** is a model step (odds to expected share) that could itself be wrong. The suggestion is to use it only to screen the single rows, never as a result.

## Decisions for the owner

1. **The 14 statistics.** Add, drop or change any; the deferred families can be brought in.
2. **The memories:** two-week half-life and 52 weeks.
3. **The two primary tests**, and that everything else is descriptive.
4. **The feature-alpha audit's repaired rules and scorer** for Stage 2. That is the proposal. Its cost is the matches without a confirmed match day: Stage 0 shows scorable matches falling from 95% to 84% of the men's matches with odds in 2022–2026.
5. **The point-share screen:** yes or no.
