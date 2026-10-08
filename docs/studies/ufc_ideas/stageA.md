# Stage A: a Bradley–Terry rating and a market rating

> **Correction, 2 October 2026:** These are historical results. The audit found chronology, forecast-format and evaluation defects. The shared code and shortlisted features have been repaired; see the [repair report](../feature_alpha_audit/repairs.md). Original numerical results below have not been relabelled as corrected results.

**Status: built 2 Oct 2026, waiting for the owner's review.** A study stage, not a decision. The Brief and the stage table are in the [README](README.md). The report section is `src/eda/ufc_ideas/report_stageA.py` (it joins the study's page when Stage D builds it).

Labels: **observed** is measured on the data, **inferred** is a reading of measurements, **suggestion** is a proposal for the owner. Every number comes from `data/studies/ufc_ideas/`: from `stageA_summary.json` (the comparisons outside the harness, and a copy of the ratings' constants, checks and probes) unless another file is named. The other sources are `stageA_bt_summary.json`, `stageA_features_summary.json`, `stageA_bt_tuning.csv`, `stageA_mesr_tuning.csv` and the harness's `stageA_ranking.csv` / `stageA_results.json`. The harness's own `stageA_results.json` is left as it writes it; the comparisons are in `stageA_summary.json` instead.

## In short

* **Observed. A tuned Bradley–Terry rating (BT) is not a better base rating than Elo in tennis.**
  * Built from wins and losses and tuned on the same matches as Stage 1's surface Elo, it is worse over 2013–2026: by 1.60 milli-log-loss for the men (95% range 0.76 to 2.44) and 4.45 for the women (3.21 to 5.69).
  * On the matches with closing odds of 2022–2026, it closes −8% (men) and −32% (women) of the gap between Elo and the bookmakers: it sits further from the market than Elo does.
  * The surface version matches surface Elo for the men (0.58 better over 2013–2026, range −0.22 to 1.38) but not for the women (2.20 worse).
* **Observed. BT and Elo each add something to the other, Elo more.** Through the shared harness, BT adds 1.77 milli-log-loss to Elo for the men (a finding) and 0.70 for the women (possible). Elo adds 4.18 and 3.62 to BT.
* **Observed. BT absorbs one earlier leader, not the rest.**
  * Given BT, the points matchup over 52 weeks falls from 1.55 to 0.32 (men) and from 1.59 to 0.30 (women), and age falls from 1.42 to 0.87 and from 0.56 to 0.27.
  * Recent workload, the first matches on a surface, the games-weighted Elo and the ratings through the iid model all add as much or more given BT as given Elo: the games-weighted Elo 1.82 → 5.22 (men) and 2.38 → 5.12 (women).
* **Observed. MESR adds nothing to the closing line.**
  * MESR is a rating solved from earlier closing odds. Given the market it scores −0.03 (men) and −0.02 (women).
  * The gap between the market's view and the results' view (MESR − BT) scores −0.01 and −0.06 given the market.
  * Given Elo, MESR adds nothing for the men (−0.31) and 0.78 for the women. As a forecast on the matches with odds of 2022–2026, it is level with Elo.
* **Observed. The tuned constants are far from the UFC project's.** BT wants a half-life of 0.5 years on both tours, a weak ridge (λ 0.1) and a low newcomer anchor (−2 men, −1.5 women). MESR wants a half-life of 0.09 years (about a month) and almost no ridge. Both lay beyond the Brief's grids, which were widened.
* **Inferred. Why BT trails Elo here.** Tennis players have dense histories.
  * Elo's per-player K gives fast updates to newcomers and a long memory to veterans.
  * BT's one half-life must choose between the two, and it chose a short memory.
  * BT loses most where a long memory helps: experienced players, Grand Slam qualifying, players back from long layoffs.
  * It also loses where its newcomer anchor meets established players under a new id (2026, a known Stage 0 problem).
* **Observed. Probes.** Cut by date, event and round, 0 of 2,489,504 protected pre-match values moved. A deliberately leaky BT moved 412.
* **For the owner.** Six decisions, [at the end](#decisions-for-the-owner).

## What was built

| File | What it holds |
|---|---|
| `stageA_bt.parquet` (45.15 MB) | One row per match of Stage 0's table (872,704): pre-match `bt_a`, `bt_b`, `p_bt_a`; each player's edges in the snapshot (`n_a`, `n_b`) and earlier rounds of this event (`nev_a`, `nev_b`); the variants' ratings (`bt_games_*`, `bt_nodecay_*`, `bt_surface_*`) |
| `stageA_mesr.parquet` (15.81 MB) | One row per match: pre-match `mesr_a`, `mesr_b` (missing for a player with no odds history), `p_mesr_a`, odds-edge counts, the snapshot-only values `mesr_snap_*` |
| `stageA_features.parquet` (27.44 MB) | The Stage 4 pool (255,123 matches) with the leaders' columns, `p_bt`, `p_mesr` and the eight Stage A features |
| `stageA_bt_tuning.csv`, `stageA_mesr_tuning.csv` | Every setting tried (BT 316 and the surface grid's 6; MESR 200), labelled by grid, with log loss 2013–2018, MESR's out-of-sample gap to the closing log-odds, run times and solver counts |
| `stageA_bt_summary.json` | The chosen constants, the grids' flatness, which constants sit on an edge of what was tried, the checks, the probes, timings, the ten highest-rated players per tour at the end of the table |
| `stageA_features_summary.json` | Coverage of every feature, correlations, the check of `elo|single` against Stage 1's ratings |
| `stageA_ranking.csv`, `stageA_results.csv`, `stageA_null_copies.csv`, `stageA_results.json` | The harness's rundown (30 rows) |
| `stageA_summary.json` | The comparisons outside the harness, the diagnostics, Stage 1's and Stage 4's numbers reproduced, file sizes |
| `stageA_catalog.json` | One entry per scored row id (15 ids) |

Code in `src/eda/ufc_ideas/`:

* **`stageA_ratings.py`**: the BT and MESR passes, the grids, the probes.
  * The grids ran in four invocations as they were widened. Their passes took 12,744.7 seconds in all (`stageA_bt_summary.json`, timings), on 5 worker processes.
  * The `--reuse-grid` run (surface grid, full passes, checks, probes, outputs) took 1,285.4 seconds.
  * Both ran on a machine shared with Stages B and C. Each invocation fits the 45-minute plan; a single run from scratch would not.
* **`stageA_features.py`**: the feature frame, 1.4 seconds.
* **`stageA_rundown.py`**: the harness and the comparisons, 54.8 seconds; the harness took 51.3 of them on 5 workers.
* **`report_stageA.py`**: the report section.

Tests: `test/ufc_ideas/test_stageA.py`, 21 tests, all passing.

## Terms used here

* **Log loss, milli-log-loss.** Minus the natural log of the probability given to the winner, averaged over matches. A coin scores 0.693; lower is better. One milli-log-loss is 0.001. Differences are written "better" or "worse".
* **Evaluation matches.** The earlier study's: singles 2013–2026, completed or retired. The levels are the Grand Slams (the four majors), the Tour Finals, the 1000s, 500s and 250s (the main tour, by ranking points on offer) and the second tier (Challengers for men, WTA 125s for women). Main draws and their qualifying (the rounds that decide a draw's last places) both count.
* **Matches with odds.** Evaluation matches with a closing-odds probability: tour-level main draws only, no men's 2018 (Stage 1).
* **Retirement, walkover.** A player stops during the match (it counts; the opponent wins), or does not start (no match).
* **Round robin.** A group stage in which each player meets every other; its matches share one round.
* **Best of five.** The men's Grand Slam main draws: the first to win three sets.
* **Elo.** Stage 1's surface Elo: a rating moved after every match by the surprise of its result. A separate rating per surface is blended in (30% for the men, 25% for the women). Its constants were tuned on 2013–2018 and frozen.
* **Bradley–Terry rating (BT).** P(A beats B) = sigmoid(s_A − s_B). At each snapshot every earlier result is re-solved at once, as a ridge-penalised logistic regression. A win is credited at what the opponent turned out to be worth over the whole history, not at what they were worth that day. This is the UFC project's "retrospective" strength of schedule, built in.
* **Snapshot.** One solve of BT or MESR from every result before a date. **Edge**: one result in a snapshot.
* **Half-life.** The age at which an old result counts half as much as a new one: weights 2^(−age / half-life).
* **Ridge (λ) and anchor.** The penalty λ/2 × (s_i − m_i)² pulls each rating toward a prior mean m_i. For an established player m_i is 0; for a newcomer it is a lower **anchor** (the UFC project's "newbie" anchoring), here fading over a player's first six matches.
* **Retirement weight.** How much a retirement counts as a result. The UFC project's analogue is its decisiveness weights (a split decision counts less); the owner asked for win or loss only.
* **MESR (market-embedded skill rating).** The same kind of rating solved from closing odds: each match's de-vigged log-odds is a measurement of s_A − s_B, fitted by weighted least squares with a half-life and a ridge. It is the market's opinion of each player, carried forward.
* **Given Elo, given BT, given MESR, given the market.** The shared harness's scores. The row is added to that base's log-odds in a logistic regression without an intercept, refitted season by season on earlier seasons only, and compared with the base alone on the same matches (milli-log-loss; positive is better). **Alone** is the row against a coin.
* **Null band, family-wide line, reading.**
  * Each score has 20 copies of the feature, shuffled within each season, beside it; the band is their range.
  * The line is the largest standardised score any shuffled copy reaches across all of this stage's rows, per tour and base. A row above it beats chance for the whole family.
  * Readings: a **finding** clears the line given Elo and gains in at least three eras; **possible** is above its own band only; **no sign** is inside it; **worse** is below it.
  * Sizes given a base: small (under 1 milli-log-loss) or clear (1 or more).
* **Eras.** 2013–16, 2017–19, 2020–21, 2022–26. Groups under 300 matches are directional only.

## The BT design and its time rule

**The model** (the UFC project's `add_bt_rating` and `_solve_bt_irls_warm`, adapted):

* **Objective.** At a snapshot, the ratings minimise Σ_k w_k [log(1 + e^{η_k}) − y_k η_k] + (λ/2) Σ_i (s_i − m_i)², with η_k = s_A − s_B and y_k = 1 if A won.
* **Edges.** One per match whose result moves ratings: completed or retired, as the owner decided for Elo. Walkovers never. Every singles level from 2010 (ITF and team events included), per tour, from Stage 0's table.
* **Weights.** w_k = 2^(−age_k / half-life) × the result weight, with age measured from the snapshot's date. Edges whose decay weight falls below 1e-4 are dropped: with the chosen half-life of 0.5 years, results more than 6.64 years old.
* **Anchor.** m_i = anchor × max(0, 1 − n_i / 6), n_i the player's edges in the snapshot: the UFC v4 "informed" form, chosen once and kept fixed. Tennis newcomers arrive in large numbers at the ITF level and play many matches quickly, so the pull fades over their first six matches rather than stopping after one, as in the UFC BT's rule. A player with no edge is rated at the anchor.
* **Solver.** Damped Newton on the sparse Hessian with a preconditioned conjugate gradient. Each snapshot is warm-started from the previous one plus each player's in-event steps. Newton stops when the largest step is below 1e-3; quadratic convergence leaves the ratings within 2.4e-7 of a tight solve (checked below).

**The time rule** (the Brief's, as `stage1_baselines.elo_pass` implements it for Elo):

* **Snapshots.** One is solved at every distinct tournament date of the tour, almost always a Monday (the date is `elo_pass`'s "week"), from the edges of earlier dates only.
* **Earlier rounds of the same event.** A player's rating for a match is the snapshot plus what their earlier rounds of the event added, each through a one-step local Newton update with the opponent's rating held fixed: step = w (y − p) / (w p (1 − p) + λ + I_i + J_i).
  * p comes from the two pre-match ratings.
  * I_i is the player's information at the snapshot: Σ w p (1 − p) over their edges, at the solution.
  * J_i is the information their earlier rounds of this event added.
* **Held back.** A round's steps wait for the next round of the event, so a round robin's matches never see each other. They never reach another event, so two events of one date never see each other. The next snapshot re-solves everything.

**Variants**, each its own column:

* **Games-weighted BT.** Each result's weight is multiplied by the winner's share of the games over its 2010–2018 mean (Stage 4's scale, read from `stage4_constants.csv`; 1 where the score has no games).
* **BT without decay.** The best grid setting without decay.
* **Surface BT.** s_i + u_{i,surface}, with its own ridge λ_u on the deviations; the other constants are the primary's. Its in-event step uses the combined rating's information from the 2 × 2 block of (s_i, u_{i,surface}). A player who plays on one surface makes s and u nearly collinear, so the solver preconditions each player's block exactly.

**MESR** (the UFC project's `add_mesr` and v4 `mesr.py`, adapted):

* **Edges.** Matches with a coherent closing-odds probability (Stage 1's `p_avg_a`), completed or retired, from 2010. The 2010–2012 odds warm MESR up, as 2010–2012 results warm up Elo and BT. d_k = logit(p_avg_a), the de-vigged log-odds that A wins.
* **Snapshot.** Minimise Σ w_k (d_k − (s_A − s_B))² + λ Σ (s_i − m_i)², with w_k = 2^(−age / half-life). m_i is the anchor for a player with at most one odds edge and 0 otherwise (the UFC rule, as the Brief sets it). A linear sparse solve; no edge is dropped.
* **Within an event.** MESR uses the same time rule as BT. It adds the same event's earlier rounds through the exact one-player least-squares step w (d − Δ) / (w + λ + I_i + J_i).
  * This departs from the Brief's "edges of earlier weeks only". The README's general rule allows it for any batch rating if leak-free, and it is probed below.
  * Without it, a Grand Slam's fourth round would carry the market's view from before the event, and MESR − BT would partly measure the rounds BT has seen and MESR has not.
  * The snapshot-only values are kept (`mesr_snap_*`) and scored raw beside it.
* **Missing.** A player with no odds edge visible under the rule has no MESR, so the feature is missing for that match.

## Tuning

**The Brief's grid put the best at its corner.**

* **The grid.** Per tour, half-life {0.75, 1.5, 3, 6, none} years × λ {0.1, 0.35, 1, 3} × anchor {0, −0.5, −1} × retirement weight {1, 0.5}, scored by the log loss of P(A wins) on the evaluation matches of 2013–2018. Every snapshot was weekly; nothing was coarsened.
* **Where the best lay.** The shortest half-life and the smallest λ on both tours, and for the men the lowest anchor too. The surface was steep there: in the Brief's grid the best setting with a 1.5-year half-life is 4.24 milli-log-loss worse for the men and 5.34 for the women. With λ 0.35 instead of 0.1 it is 2.75 and 4.36 worse.
* **Widened.** As Stage 1 widened Elo's grid, the grid was extended past that corner in two rounds: half-life {0.25, 0.35, 0.5, 0.75} × λ {0.01, 0.03, 0.1} × anchor {−0.5, −1, −1.5}, then anchors −2 and −2.5. The retirement weight was kept at 1, the better value in the Brief's grid.
* **Size.** 158 settings per tour in all.

**Chosen and frozen** (`stageA_bt_summary.json`, which also records which values sit at an edge of what was tried). BT's half-life, λ and anchor lie inside the range tried. The retirement weight is at its natural maximum, 1. The women's λ_u (10) is the largest tried but ties with 3. MESR's λ is the smallest tried.

| | Men | Women |
|---|---|---|
| BT | half-life 0.5 years, λ 0.1, anchor −2, retirement weight 1 | half-life 0.5 years, λ 0.1, anchor −1.5, retirement weight 1 |
| Log loss 2013–2018 | 0.58840 | 0.60189 |
| Settings within 1 milli-log-loss of the best | 13 of 158 | 16 of 158 |
| BT without decay | λ 1, anchor −1, retirement weight 1 | λ 1, anchor −1, retirement weight 1 |
| Surface BT | λ_u 3 | λ_u 10 |
| MESR | half-life 0.09 years, λ 0.0003, anchor −1 | half-life 0.09 years, λ 0.0003, anchor −1 |

**How flat the surface is** (`stageA_bt_summary.json`, flatness; milli-log-loss above the best, the other constants free):

* **Half-life.** Sharply curved.
  * Men: 0.25 years +9.56, 0.35 +3.12, 0.75 +0.004, 1.5 +4.36, none +19.79.
  * Women: 0.35 +2.69, 0.75 +0.44, none +20.85.
* **λ.** Sharply curved.
  * Men: 0.01 +17.72, 0.03 +4.87, 0.35 +2.87.
  * Women: 0.03 +0.63, 0.35 +4.80.
* **Anchor.** Flat: between −1 and −2.5 every value is within 0.14 for the men and 0.04 for the women.
* **Retirement weight.** Weighting retirements by a half costs 0.28 (men) and 0.52 (women): **observed**, retirements count fully, as Stage 1 found for Elo.
* **The surface BT's λ_u.** Men: 1 is 2.64 worse than 3, and 10 is 0.29 worse. Women: 3 and 10 tie to the third decimal of a milli-log-loss, so the optimum lies between them.
* **MESR.**
  * The Brief's grid also put the best at its corner (half-life 0.5, λ 0.3, anchor −1, the shortest, smallest and lowest). It was widened in three rounds to 100 settings per tour.
  * The half-life ends inside the range: 0.06 years is 1.62 (men) and 1.36 (women) worse, 0.125 years 0.19 and 0.36 worse.
  * λ ends at the smallest value tried, 0.0003. The gain is shrinking toward the no-ridge limit: 0.001 is 0.19 and 0.28 worse.

**Inferred.** The UFC BT's defaults (`elo_utils.add_bt_rating`) remember results for years and shrink harder. Tennis wants half a year and a weak ridge. A tennis player plays dozens of rated matches a year, so half a year of results already pins a rating, and older results mostly add drift. The market's opinion goes stale faster still: MESR does best remembering about a month of prices, with no shrinkage.

## BT against Elo

### Log loss, every evaluation match

Raw log loss of P(A wins), lower is better. "Elo − BT" is Elo's log loss minus BT's in milli-log-loss, with its 95% range from the per-match differences; positive means BT is better.

| Tour | Window | Matches | BT | Surface BT | Elo | Elo − BT | Elo − surface BT |
|---|---|---:|---:|---:|---:|---:|---:|
| Men | 2013–2026 | 155,130 | 0.6062 | 0.6040 | 0.6046 | −1.60 (−2.44 to −0.76) | +0.58 (−0.22 to 1.38) |
| Men | 2013–2018 (tuning) | 64,208 | 0.5884 | 0.5861 | 0.5869 | −1.53 (−2.68 to −0.39) | +0.77 (−0.30 to 1.83) |
| Men | 2019–2026 | 90,922 | 0.6187 | 0.6166 | 0.6171 | −1.65 (−2.83 to −0.47) | +0.45 (−0.69 to 1.59) |
| Men | 2022–2026 | 64,887 | 0.6167 | 0.6152 | 0.6152 | −1.46 (−2.84 to −0.07) | +0.05 (−1.30 to 1.39) |
| Women | 2013–2026 | 60,321 | 0.6047 | 0.6025 | 0.6003 | −4.45 (−5.69 to −3.21) | −2.20 (−3.37 to −1.03) |
| Women | 2013–2018 (tuning) | 25,676 | 0.6019 | 0.5997 | 0.5991 | −2.77 (−4.20 to −1.34) | −0.63 (−1.91 to 0.66) |
| Women | 2019–2026 | 34,645 | 0.6069 | 0.6045 | 0.6012 | −5.69 (−7.57 to −3.82) | −3.37 (−5.17 to −1.57) |
| Women | 2022–2026 | 23,998 | 0.6081 | 0.6058 | 0.6014 | −6.66 (−8.90 to −4.42) | −4.38 (−6.53 to −2.23) |

**Observed.**

* **Elo stays ahead, even in the tuning years.** On the very matches both were tuned on (2013–2018), BT is 1.53 (men) and 2.77 (women) worse than surface Elo.
* **The games-weighted BT.** Level with Elo for the men over 2013–2026 (0.11 better, range −0.73 to 0.95) and 2.16 worse for the women (−3.41 to −0.90).
* **The BT without decay** is far worse: 29.47 (men) and 32.28 (women).
* **By era** (Elo − BT):
  * men −1.35, −2.79, +0.01 and −1.46 (2013–16 to 2022–26);
  * women −2.31, −3.66, −3.39 and −6.66;
  * BT is never clearly better.

### On the matches with odds, and the share of the gap to the market

| Tour | Window | Matches | BT | Surface BT | Elo | Market | Elo − BT | Gap closed: BT | games BT | surface BT |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Men | 2013–2026 | 31,683 | 0.6025 | 0.5986 | 0.5989 | 0.5791 | −3.63 (−5.26 to −2.00) | −18% | −13% | +1% |
| Men | 2022–2026 | 12,352 | 0.6131 | 0.6101 | 0.6114 | 0.5890 | −1.72 (−4.48 to 1.05) | −8% | −3% | +6% |
| Women | 2013–2026 | 32,178 | 0.6114 | 0.6093 | 0.6086 | 0.5920 | −2.77 (−4.39 to −1.15) | −17% | −6% | −4% |
| Women | 2022–2026 | 11,467 | 0.6154 | 0.6135 | 0.6093 | 0.5906 | −6.03 (−9.38 to −2.68) | −32% | −21% | −22% |

**The gap closed** is (Elo − BT) / (Elo − market). A negative share means BT is further from the market than Elo.

**Observed.**

* **The gap.** Elo trails the market by 22.46 (men) and 18.78 (women) milli-log-loss in 2022–2026, as in Stage 1. The primary BT closes −7.6% and −32.1% of it.
* **The surface BT** closes 5.7% for the men: 1.28 better than Elo, range −1.32 to 3.88, so not distinguishable from zero. For the women it closes −22.0%.
* **Stage 1 reproduced.** Its log losses for Elo and the market reappear here to the last digit: 40 numbers, largest difference 4.48e-11 (`stage1_reproduced`).

### Calibration, 2019–2026

Ten equal bins of the forecast that A wins, evaluation matches (`calibration_2019_2026`, which also holds every bin). The **calibration slope** comes from refitting the result on the forecast's log-odds: 1 is perfect, below 1 the forecast is too confident.

| Tour | BT slope | Elo slope | Largest bin gap (≥ 300 matches), BT | Elo |
|---|---:|---:|---:|---:|
| Men | 0.967 (0.948 to 0.986) | 0.859 (0.842 to 0.875) | 3.23 points | 4.06 points |
| Women | 1.052 (1.021 to 1.083) | 1.035 (1.005 to 1.064) | 3.62 points | 2.07 points |

**Observed.**

* For the men, BT is better calibrated than Elo: Elo is too confident, as Stage 1 found at best of three.
* **Inferred.** BT's deficit is therefore not calibration. It separates likely winners from likely losers less well.
* **Observed.** Within each level, recalibrating both forecasts by their own slope (in-sample, a reading only) leaves BT worse at the Grand Slam qualifying by 13.62 (men) and 15.68 (women) (`diagnostics`, `level_after_recalibration`).

### By level, 2013–2026

Elo − BT, milli-log-loss (positive: BT better), every evaluation match (`by_level`):

| Level | Men | Matches | Women | Matches |
|---|---:|---:|---:|---:|
| Grand Slams | −8.47 (−12.05 to −4.90) | 6,951 | −4.18 (−7.59 to −0.77) | 6,965 |
| Tour Finals | +0.40 (−10.46 to 11.27) | 315 | −2.96 (−11.38 to 5.46)* | 285 |
| 1000s | −1.84 (−4.87 to 1.19) | 7,883 | −1.27 (−3.90 to 1.37) | 8,048 |
| 500s | −0.97 (−4.48 to 2.53) | 5,625 | −0.91 (−4.92 to 3.10) | 5,444 |
| 250s | −2.08 (−4.70 to 0.53) | 14,060 | −4.23 (−7.20 to −1.27) | 12,106 |
| Grand Slam qualifying | −13.57 (−18.36 to −8.77) | 6,041 | −14.92 (−20.12 to −9.72) | 5,025 |
| Tour qualifying | −2.24 (−5.06 to 0.57) | 12,953 | −5.39 (−8.19 to −2.60) | 13,886 |
| Challenger / WTA 125 | −1.28 (−2.38 to −0.19) | 73,768 | −1.92 (−4.92 to 1.09) | 7,219 |
| Challenger / 125 qualifying | +2.38 (−0.26 to 5.02) | 27,534 | −6.16 (−14.57 to 2.24) | 1,343 |

\* Under 300 matches: directional only.

### Where BT loses

`diagnostics` (Elo − BT, milli-log-loss; positive: BT better):

| Cut | Men | Matches | Women | Matches |
|---|---:|---:|---:|---:|
| A player has no edge in the snapshot (rated at the anchor) | +70.45 | 830 | −313.60* | 167 |
| The less experienced player has 1–5 edges | −34.43 | 2,316 | −32.75* | 269 |
| Both have over 100 edges | −2.05 | 126,981 | −3.59 | 54,306 |
| The longer layoff of the two is over 365 days | −44.60 | 1,059 | −8.42* | 292 |
| Grand Slam qualifying, first round (Q1) | −19.90 | 3,456 | −17.84 | 2,870 |
| Grand Slam qualifying, last round (Q3) | −1.48 | 861 | −3.40 | 719 |
| 2026, a player with no edge in the snapshot | −507.25* | 90 | −382.59* | 87 |

\* Under 300 matches: directional only.

**Observed.**

* **Most of the deficit is on experienced players**: those with over 100 edges, who play most matches.
* **Newcomers.** The newcomer anchor helps when a man has no history at all. Players with one to five edges cost BT on both tours, and the anchor hurts in 2026 on both tours.
* **Long layoffs** (over a year) cost BT a lot, on few matches.
* **Grand Slam qualifying.** The deficit is largest in its first round, where no in-event step applies, so it lies in the snapshot itself.
* **Seasons.** The women's BT is worse than Elo in every season, 0.16 to 10.83. The men's is better in 2016, 2021, 2023 and 2025, and worst in 2026 (−8.09) (`diagnostics`, season).

**Inferred.**

* **One half-life.** Elo's K shrinks with a player's matches: newcomers move fast, veterans slowly, so Elo remembers a veteran's level over years. BT has one half-life for everyone, and tuning chose a short one (0.5 years) because form matters. A longer one loses more than it gains: 1.5 years is 4.36 worse for the men in the tuning years.
* **Where that costs BT.** It forgets the long-run level of experienced players, of players back from long layoffs, and of the journeymen of Grand Slam qualifying, where Elo's long memory orders players better. The cause at Grand Slam qualifying is not established here. The in-event steps do not explain it, since it is largest in the first round.
* **2026.** The matches with a player BT has never seen pile up there (90 men's, 87 women's). Stage 1 found established players under a second Tennis My Life id in the weeks from 25 May 2026. BT rates such a player at the newcomer anchor (−2 or −1.5, a heavy underdog), where Elo starts them at its average rating. That is consistent with the 2026 losses, though they were not separated here.

### BT and Elo through the harness

Milli-log-loss better than the base alone, all scored seasons, with the 95% range (`stageA_ranking.csv`):

| Row | Men, given Elo | Women, given Elo | Men, given BT | Women, given BT |
|---|---:|---:|---:|---:|
| BT (primary) | +1.77 (1.36 to 2.18), finding | +0.70 (−0.05 to 1.45), possible | – | – |
| Surface Elo | – | – | +4.18 (3.81 to 4.54) | +3.62 (3.18 to 4.07) |
| Games-weighted BT | +2.65 (2.19 to 3.11) | +1.69 (0.82 to 2.56) | +3.35 (2.92 to 3.78) | +3.72 (2.98 to 4.46) |
| Surface BT | +2.47 (2.01 to 2.92) | +1.42 (0.61 to 2.24) | +2.43 (2.09 to 2.77) | +2.60 (2.08 to 3.13) |
| BT without decay | −2.80 (−3.26 to −2.35), worse | −3.26 (−4.02 to −2.49), worse | −0.08 (−0.46 to 0.29) | +0.62 (0.11 to 1.13) |
| BT + the ratings through the iid model (two inputs) | +4.55 (3.92 to 5.18) | +3.89 (2.59 to 5.19) | – | – |

**Observed.**

* **BT given Elo.** It adds 1.42 for the men in 2022–2026; for the women, −0.19.
* **Elo given BT.** It adds 4.44 and 5.60 in 2022–2026.
* **The ratings through the iid model with BT** add 4.55 given Elo for the men, against 3.61 for those ratings alone. For the women they add 3.89, against 4.58 alone.
* **The family-wide line.** Given Elo, 3.71 (men) and 3.90 (women) standard deviations of the shuffled copies; given BT, 4.90 and 3.57.

**Inferred.** The two ratings hold different information: BT a short-memory form, Elo a long-memory level. Each adds to the other, Elo more. The games-weighted and surface BTs add more given Elo than the primary because they carry the margin and the surface, which plain Elo does not.

## What BT absorbs: the earlier leaders

Each of the earlier study's leaders given Elo (the reference, reproduced: the largest difference from `stage4_ranking.csv` is 2.22e-16) and given BT, on the same pool and seasons. Milli-log-loss, with the 95% range. ★ marks a score that clears the family-wide line; the null bands are in the second table. Women's box-score rows (the iid-model ratings, the points matchup) are scored from 2019.

| Leader | Men, given Elo | given BT | Women, given Elo | given BT |
|---|---:|---:|---:|---:|
| Ratings through the iid model | 3.61 (3.04 to 4.18) ★ | 4.98 (4.43 to 5.53) ★ | 4.58 (3.64 to 5.52) ★ | 5.83 (4.89 to 6.77) ★ |
| Games-weighted Elo | 1.82 (1.55 to 2.08) ★ | 5.22 (4.79 to 5.65) ★ | 2.38 (1.96 to 2.79) ★ | 5.12 (4.56 to 5.68) ★ |
| Sets over the last 14 days | 1.63 (1.41 to 1.84) ★ | 1.52 (1.28 to 1.75) ★ | 1.87 (1.49 to 2.25) ★ | 1.90 (1.44 to 2.36) ★ |
| Points matchup, 52 weeks | 1.55 (1.26 to 1.85) ★ | 0.32 (0.11 to 0.53) ★ | 1.59 (1.05 to 2.12) ★ | 0.30 (−0.03 to 0.62) ★ |
| Age (and age squared) | 1.42 (1.18 to 1.65) ★ | 0.87 (0.70 to 1.03) ★ | 0.56 (0.28 to 0.84) ★ | 0.27 (0.07 to 0.47) ★ |
| First matches on the surface | 1.45 (1.23 to 1.67) ★ | 2.02 (1.73 to 2.31) ★ | 1.30 (1.01 to 1.58) ★ | 1.75 (1.35 to 2.14) ★ |

The null bands, the range of the 20 shuffled copies' scores in milli-log-loss (`stageA_ranking.csv`):

| Leader | Men, given Elo | given BT | Women, given Elo | given BT |
|---|---:|---:|---:|---:|
| Ratings through the iid model | −0.02 to 0.01 | −0.02 to 0.01 | −0.10 to 0.03 | −0.10 to 0.02 |
| Games-weighted Elo | −0.02 to 0.01 | −0.01 to 0.01 | −0.02 to 0.02 | −0.02 to 0.02 |
| Sets over the last 14 days | −0.03 to 0.00 | −0.03 to 0.00 | −0.04 to −0.01 | −0.04 to −0.01 |
| Points matchup, 52 weeks | −0.02 to 0.00 | −0.02 to 0.00 | −0.08 to 0.03 | −0.09 to 0.03 |
| Age (and age squared) | −0.03 to 0.00 | −0.03 to 0.00 | −0.21 to 0.02 | −0.21 to 0.03 |
| First matches on the surface | −0.02 to 0.00 | −0.02 to 0.01 | −0.08 to 0.01 | −0.08 to 0.01 |

**Observed.**

* **Absorbed.** BT takes most of the points matchup over 52 weeks (1.55 to 0.32 for the men, 1.59 to 0.30 for the women) and part of age.
* **Unchanged.** Recent workload (sets over 14 days) is unchanged.
* **Larger given BT.** The first matches on a surface (BT has no surface term), the iid-model ratings and, most of all, the games-weighted Elo.
* **Every leader** still clears the line given BT.

**Inferred.**

* **The points matchup.** It and the short-memory BT both summarise the last year, so one stands in for the other.
* **Age.** Part of what it adds to Elo is recent decline, which a short-memory rating already follows.
* **The games-weighted Elo** gains given BT because it brings back Elo's long memory, along with the margin.
* **For later stages.** BT is not a base that makes the earlier leaders redundant.

## MESR

**Constants** (tuned on 2013–2018 matches with odds against the result): half-life 0.09 years, λ 0.0003 (the smallest tried) and anchor −1 on both tours. Out of sample (2019–2026), its rating difference misses the closing log-odds by a root-mean-square 0.463 for the men (18,291 matches) and 0.415 for the women (16,996) (`mesr_rms_gap_chosen`).

**Coverage** (`mesr_coverage`, a player needs an odds history):

| Tour | 2022–2026, evaluation matches with an MESR | Matches with odds with an MESR |
|---|---:|---:|
| Men | 32,674 of 64,887 (50%) | 12,112 of 12,352 (98%) |
| Women | 20,619 of 23,998 (86%) | 11,190 of 11,467 (98%) |

**As a forecast** (raw log loss; matches with odds where both MESR forms exist):

| Tour | Window | Matches | MESR | Snapshot-only MESR | BT | Elo | Market | Gap closed by MESR |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Men | 2022–2026 | 12,041 | 0.6143 | 0.6181 | 0.6162 | 0.6149 | 0.5918 | +2% |
| Women | 2022–2026 | 11,072 | 0.6122 | 0.6141 | 0.6138 | 0.6105 | 0.5934 | −10% |

* **Observed. Level with Elo.** MESR is level with Elo there: 0.57 better for the men (range −2.89 to 4.03) and 1.69 worse for the women (−4.99 to 1.60). The same-event update helps: the snapshot-only MESR is 3.16 (men) and 3.58 (women) worse than Elo.
* **Observed. Weak off the main tour.** On every match where MESR exists, Challengers and qualifying included, it is far weaker than Elo: 29.74 (men) and 15.53 (women) worse over 2013–2026. There a player's odds history is old or thin. That is why every row adds a lot "given MESR" in the harness, and why Elo adds 26.11 and 15.76 given MESR.

**Through the harness:**

| Row | Men: alone | given Elo | given BT | given the market | Women: alone | given Elo | given BT | given the market |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MESR | 38.55 | −0.31 (−0.79 to 0.18) | +0.63 (0.25 to 1.01) | −0.03 (−0.11 to 0.05) | 63.65 | +0.78 (0.06 to 1.50) | +1.86 (1.27 to 2.45) | −0.02 (−0.09 to 0.05) |
| MESR − BT | 3.92 | −0.41 (−0.71 to −0.11) | +0.63 (0.25 to 1.01) | −0.01 (−0.10 to 0.08) | 1.90 | −0.31 (−0.75 to 0.13) | +1.86 (1.27 to 2.45) | −0.06 (−0.14 to 0.02) |
| MESR − Elo | 9.05 | −0.31 (−0.79 to 0.18) | −0.01 (−0.05 to 0.03) | +0.02 (−0.03 to 0.07) | 5.81 | +0.78 (0.06 to 1.50) | −0.06 (−0.15 to 0.03) | −0.04 (−0.11 to 0.03) |

**Observed.**

* **No gain given the market.** Neither MESR nor the market-versus-results gap adds anything there: all six values lie inside their ranges around zero, none above the family-wide line (6.51 men, 5.51 women).
* **Given Elo.** MESR is worse than its null band for the men ("worse"). For the women it is a finding (+0.78).
* **Given BT.** MESR and MESR − BT add the same (+0.63 and +1.86): with BT as the base, subtracting BT changes nothing.

**Inferred.**

* The market's past opinion of a player, carried forward, is in its current closing price: nothing is left over.
* As a pre-match rating it does as well as Elo where the market prices matches, and no better.
* The gap between the market's view and the results' view carries no information the closing line lacks.

## Given the market

**Observed.** No Stage A row gains given the closing odds. The values for BT, its variants, MESR and the gaps run from −0.06 to +0.03 milli-log-loss, all with ranges around zero. None clears the family-wide line given the market (6.51 men, 5.51 women). The surface BT for the men (+0.03) is the only one above its own band.

The earlier leaders reproduce Stage 4's given-the-market scores exactly. Recent workload (sets over 14 days) clears the line on both tours (+0.23 men, +0.29 women) and the women's first matches on a surface does too (+0.20), as before.

## Probes and leak checks

**Observed.**

* **The probe cut by date, event and round** (`stageA_bt_summary.json`, probes; `stage1_baselines.probe_by_round`'s design).
  * On the matches from 2024 (83,305 men's and 75,896 women's, history inside the slice), 6 random cuts per tour.
  * At each cut, every input the rule does not let the cut see was redrawn: the results (BT), also the games shares (games-weighted BT), or the closing log-odds (MESR). The pass was then re-run.
  * In 48 cuts over BT, the games-weighted BT, the surface BT and MESR, 0 of 2,489,504 protected pre-match values changed.
  * A deliberately leaky BT, whose snapshots include their own date, changed 151 (men) and 261 (women).
  * Later matches changed by the hundred thousand for BT (172,534 men's values, for instance), so the probe was live.
* **Tests** (21): the solver against a dense Newton solve, plain and surface; the sparse Hessian against a dense one across layout rebuilds; the block preconditioner against a dense inverse; MESR's solve against a dense least squares.
  * The time rule on a hand-made history: a round robin's matches never see each other, two events of one week never see each other, a later round sees an earlier one.
  * Every pre-match value of random histories against a row-by-row reading, for BT (with and without decay, surface) and MESR. Each date is solved densely from earlier dates only, then each event's rounds are applied in order in plain Python. The pass agrees with it; a leaky pass and a pass without in-event updates differ.
  * With no decay and a huge λ, every rating stays at its anchor; the probe catches a leaky pass; the comparison helpers.
* **Checks.**
  * The tuning pass equals the frozen full pass's first years (largest difference 6.22e-15).
  * A solve with tight tolerances moves no rating by more than 1.13e-7 (men) and 2.40e-7 (women).
  * `elo|single` equals Stage 1's blended ratings on the log-odds scale to 1.31e-6, the float32 rounding of the stored ratings (`stageA_features_summary.json`).
  * The ten highest-rated players at the end of the table (as of 2026-09-28) read as expected. Men: Jannik Sinner, Carlos Alcaraz, Alexander Zverev, Arthur Fils, Novak Djokovic, Taylor Fritz, Ben Shelton, Rafael Jodar, Tommy Paul, Felix Auger-Aliassime. Women: Aryna Sabalenka, Elena Rybakina, Coco Gauff, Iga Swiatek, Jessica Pegula, Karolina Muchova, Elina Svitolina, Marta Kostyuk, Mirra Andreeva, Naomi Osaka.

## Problems found in earlier work (reported, not fixed)

1. **The time rule reads a "week" as a tournament date** (`stage1_baselines.elo_pass`; BT follows it here for comparability). A match dated later in a calendar week than another event of that week sees that event in full (`date_convention`).
   * **How many.** 9,338 men's and 3,702 women's evaluation matches are so dated. In 2,019 and 543 of them a player played at an earlier date of the same week.
   * **Sunday-dated (1,997 and 482).** Events such as Monte Carlo or Roland Garros begin after the earlier week's events end, so no result is seen early.
   * **Dated Tuesday to Saturday (22 and 61).** Events such as Indian Wells or Madrid overlap the earlier-dated event, so a result can be seen before it happened.
   * **Effect.** For Elo this matters only for those few matches. For BT, the global re-solve spreads an early-seen result to every rating slightly.
2. **The 2026 split identities (Stage 1's problem 1) cost a BT-type rating more than Elo.** In 2026, BT is worse than Elo by 507.25 (men, 90 matches) and 382.59 (women, 87) on matches with a player BT has never seen, consistent with established players under a new id (above). Merging the ids (Stage 1's open decision 1) matters more for any rating with a newcomer prior.
3. **This study's shared harness:** `common.rundown()` defaults to `min(6, cores − 2)` worker processes, one more than the Brief's limit of 5 per stage. This stage passes 5 explicitly; a stage relying on the default would exceed it.
4. **The README** describes Stage A's MESR as built from "edges of earlier weeks only" while its general rule allows a leak-free same-event update. This stage uses the update for MESR (probed) and keeps the snapshot-only values for comparison: decision 3.

## Limitations

* **Ranges treat matches as independent**, as in the earlier study, so they are somewhat too narrow; the shuffled copies are the sturdier guard.
* **The tuning years are 2013–2018 for both ratings.** Elo was tuned on Stage 1's widened grid; BT on 158 settings per tour here, after two widenings. Both searches went past their first grid's corner, so neither is favoured by search effort.
* **One snapshot per date.** Two events of a week can sit on different dates (problem 1).
* **The in-event step is a one-step approximation.** The opponent is held fixed, and the next snapshot corrects everything. For MESR it is exact for one player at a time.
* **MESR's λ is at the edge of what was tried.** The trend flattens toward no ridge at all.
* **The surface BT's in-event information** uses the player's 2 × 2 block (overall and this surface), ignoring the other surfaces' coupling.
* **Stage 0's known problems** feed every history here unchanged: the 2026 split identities (problem 2), repeated rows, match tiebreaks read as sets.
* **The harness trains from 2010**, while the ratings warm up. For rows that stand in for strength this understates the early seasons (Stage 4, section 6); 2022–2026 is quoted beside the full period.
* **The variants' ratings are stored as float32** in `stageA_bt.parquet` to keep it under 50 MB, so their features carry float32 rounding; the primary BT is stored in full.

## Decisions for the owner

1. **The base rating for later stages.**
   * BT does not beat surface Elo, and its surface version only matches it for the men.
   * **Suggestion:** keep surface Elo as the base. Treat BT's short-memory rating as a feature (it adds 1.77 given Elo for the men), not a replacement.
2. **The widened grids.**
   * Both ratings' best settings lay outside the Brief's grids, which were extended (BT twice, MESR three times; listed in `stageA_bt_summary.json`).
   * MESR's λ is still at the smallest value tried.
   * Approve the extensions, or ask for a further step?
3. **MESR's same-event update.** The Brief's MESR uses earlier weeks only; this stage adds the same event's earlier rounds (leak-free, probed) and keeps the snapshot-only values. Keep it, or revert to snapshots only?
4. **The newcomer anchor.** The informed form (fading over six matches) was chosen and kept fixed. It helps the men's newcomers but punishes re-identified players (2026). Test the UFC rule (anchor for at most one edge) as well, or settle Stage 0's split identities first?
5. **The time rule's date convention** (problem 1). Keep tournament dates as "weeks" (as Stage 1 did), or switch later stages to calendar weeks? It touches 22 men's and 61 women's evaluation matches in practice.
6. **What to carry to Stage D.** MESR and MESR − BT add nothing given the market. **Suggestion:** drop them from the market question and keep BT as an optional form feature beside the earlier leaders.

## Suggestions (not computed)

* **A two-timescale BT.** Use a long-half-life BT (or Elo) as each player's ridge target m_i for the short-half-life BT. Form could then move fast while the long-run level stays remembered, the trade-off a single half-life cannot make.
* **Per-player memory.** A half-life that grows with a player's matches, the BT analogue of Elo's shrinking K.
* **BT with the margin and the surface together.** The games-weighted and surface variants each add on their own given Elo (2.65 and 2.47 for the men); one rating with both is untried.
* **Grand Slam qualifying.** The largest deficit to Elo, unexplained. Comparing the players' recent levels (ITF, Challenger, tour) in those draws would tell whether BT misplaces players moving between levels.
