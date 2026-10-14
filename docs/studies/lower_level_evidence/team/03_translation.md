# What a lower-level match is worth as main-tour evidence: translation and exchange rate, per statistic

9 October 2026 · Team role 03 (level-translation statistician) of the lower-level-evidence study · Research evidence, not a decision.

**Note added by the lead (9 Oct 2026).** This report was written before the owner's [decision of 9 Oct](../../../decisions/2026-10-09-adoption-framework.md) that no comparison is called a "tie". Read "tie" here as "unresolved": the 95% interval spans 0. The [dossier](../README.md) gives P(better) where it quotes these readings. The red team's review ([07](07_red_team.md) S1, S4) adds two caveats:
* the tier prior over-corrects women's holds in 2013–2018;
* the credibility estimator's δ and w also absorb recency and each group's level, so they rank the arms rather than measure structural exchange rates.

**The question.** For each box-score statistic:
* **the translation (δ):** how far a player's rate at a lower level sits from his main-tour rate;
* **the exchange rate (λ):** how many lower-level units are worth one main-tour unit as evidence. I report it mostly as the weight **w = 1/λ** (1 = equivalent, 0 = useless);
* **the bias check:** does the project's opponent adjustment already remove the level gap, or does it leave a bias that grows with a player's lower-level share?

**Keys.**
* **Labels.** *Observed* = computed here (file cited) or read in code (`path:line`). *Inferred* = my reasoning. *Suggestion* = a proposal for the owner.
* **Gaps** are in points per 100 units of the statistic: serve points, return points, games, or break points.
  * **+ = the rate is higher at the lower level** (or higher than expected, for residuals).
  * Higher is better for the player on every statistic except double faults.
* **Predictive gains** are in **milli per unit**: thousandths of the binomial log loss per point (or game, or break point) of that statistic.
  * **+ = the named version predicts better.**
  * These are not match-winner mLL. The effect on the model needs a candidate build (section 7).
* **Intervals** are 95% unless marked 90%. An interval that spans 0 is a **tie**.
* **Levels** are those of `src/eda/lower_level_evidence/common.py`:
  * MAIN = 250-and-up main draws;
  * TQ = tour qualifying; GSQ = Slam qualifying;
  * CH = Challenger and WTA 125 main draws; CHQ = their qualifying.
  * **"Lower-based"** = most of the player's previous 365 days was below the main tour (home tier not MT); "main-tour-based" = the opposite.
* **Data.** The frozen reference of 8 Oct 2026: 787,039 matches of seasons up to 2024, events before 30 Dec 2024.
* **The holdout.** No 2025–2026 outcome is read.
  * The player rows of other matches are never loaded: a filtered read (`translation.py:203-212`), guarded by `common.assert_no_holdout_outcomes` (`:212`, `:1248`).
  * 2025–2026 appears only as box-score coverage counts (section 5).

## In short

* **Raw rates are not comparable across levels** (Observed).
  * The same players, in the same season, at a Challenger rather than the main tour:
    * men win +2.9 [+2.8, +3.0] more points per 100, hold +3.7 more games and break +8.4 more;
    * women +2.5, +4.0 and +7.7.
  * Qualifying looks the same: +2.8 to +3.4 points of total points won.
  * So every raw aggregate that pools levels treats the lower level as equivalent: `points_52w`, and nearly the 17 one-step forms, which keep 78% of the raw shift ([role 01](01_lineage.md)).
* **For raw aggregates, translation is what matters. After it, a lower-level unit is worth about half to all of a main-tour unit** (Observed; fitted 2013–2018, scored 2019–2024).
  * **Translated beats pooled-as-equivalent:**
    * breaks +1.98 milli per unit (men) and +1.17 (women);
    * holds +0.45 / +0.68; total points +0.22 / +0.19.
  * **For players with fewer than 10 main-tour matches in the past year, 2–5 times more:** breaks +5.2 / +3.6, holds +1.9 / +3.4.
  * **Untranslated,** the best weight for raw return statistics is 0: as they stand, they carry only bias.
  * **Translated,** the fitted weight w (90% bootstrap) is:
    * men's Challenger: 0.5–0.8 (total points 0.73 [0.58, 0.93]);
    * men's tour qualifying: about 1;
    * women, at WTA 125 and qualifying: about 1.
* **The opponent-adjusted joint solve (the IOS form) removes most of the gap and needs little more** (Observed).
  * Run prior-only, it removes 64–87% of the same players' total-points gap.
  * **The leftover level "condition" offsets are small:**
    * men's serve points won at Challengers −0.2 points in 2010–2018 and −0.6 in 2019–2024;
    * aces −0.5 to −1.2 points; holds −0.4 to −1.6.
  * **Correcting for them barely helps:** translating gains at most +0.06 milli per unit (aces).
  * **A 2× discount helps only men's statistics,** and only a little:
    * holds +0.20 [+0.15, +0.25];
    * break points saved +0.08 [+0.03, +0.13], or +0.12 [+0.07, +0.18] with translation;
    * second-serve points +0.03.
  * **The lower-level box scores carry real information.** Dropping them costs every statistic 0.2–1.3 milli per unit, about a tenth of what the IOS gains over the tour average. For low-exposure players it costs 0.5–4.9.
* **The joint solve's remaining level bias comes from its prior, not from equivalence** (Observed, with the mechanism Inferred).
  * **The bias.** At the main tour, the IOS form overrates lower-based players against main-tour-based ones, clearly for women (per 100, 2013–2024):
    * break points saved +1.02 [+0.75, +1.29];
    * holds +0.58 [+0.25, +0.92];
    * second-serve points +0.40 [+0.23, +0.58].
    * Men tie, apart from aces and break points saved.
  * **Where it sits:** on lower-based women whose box-score evidence is thin. As servers with under 5 typical matches of evidence, they save 3.0 ± 1.3 fewer break points per 100 than predicted; with 20+ matches, the gap is about zero.
  * **It is not caused by equivalence.** It is as large with no lower-level rows at all (+1.16 for break points saved). A ridge pull towards the single pool average made 5 times stronger multiplies it 2–4 times.
  * **The remedy is the UFC "informed prior".** A prior set by the player's home tier removes most of it for women's holds (+0.58 → −0.29) and second-serve points (+0.40 → +0.06), and scores better on 2019–2024:
    * holds +0.08 [+0.02, +0.13], break points saved +0.07 [+0.05, +0.09];
    * for low-exposure players, up to +0.22.
* **Results (Elo) need no discount** (Observed).
  * In a plain Elo over every level, Challenger and ITF updates at ×0.75 tie full weight; ×1.25 is worse.
  * Half weight or less is worse. At zero weight: men's Challengers cost 6.8 [5.2, 8.4] mLL, women's ITF results 6.4 [4.7, 8.1].
* **ITF:** no box-score translation can be estimated without reading the holdout (Observed).
  * ITF box scores exist only in 2025 (95%) and 2026 (99%).
  * `translation.py` reruns unchanged on a candidate Stage 0. With windows over the seasons the new data cover, it gives ITF and ITF qualifying their own δ, λ and tier prior (section 5).
* **A correction to the event-levels study** (Observed).
  * Its break shifts (`blend/level_shift.csv`) summed break counts and return-game counts separately.
  * 18,138 box-score rows of 2013–2024 have the second without the first: mostly the WTA main tour and qualifying, and Slam qualifying.
  * With complete rows only:
    * men's qualifying shift is +7.1 points, not +8.5;
    * women's qualifying +7.3, not +9.1;
    * women's WTA 125 +7.7, not +6.8.
  * The men's Challenger figures reproduce to the fourth decimal; breaks to the third.

## The data

Box-score matches by level, seasons 2010–2024 (completed, standard format), the pool every solve here reads. `summary.json`, `data.box_rows_by_tour_bucket`, holds the same as player rows, two per match:

| | Main tour | Tour qualifying | Slam qualifying | Challenger / WTA 125 | Their qualifying | Team |
|---|---:|---:|---:|---:|---:|---:|
| Men | 36,711 | 14,406 | 4,610 | 71,931 | 21,240 | 1,794 |
| Women | 32,383 | 13,971 | 3,684 | 4,323 | 716 | 1,678 |

* **Men's box-score pool is three-quarters lower-level** (Observed). Women's is 40%.
* **Main-tour ratings lean on it.** In the IOS-form solve of section 2, lower levels give, on average, 32–48% of a main-tour man's serve or return evidence, and 26–31% of a woman's (`evidence_shares.csv`). Role 02 measures 38% / 23% for the decided IOS profile ([02_composition.md](02_composition.md)).
* **ITF** has 29 women's box-score matches before 2025 and no men's. TEAM is solved as its own level but not discussed here.

## 1. Raw same-player gaps (task 1)

**The measure.** Player-seasons with at least 3 box scores at both the main tour and level L. Each rate is pooled over the season's box scores at that level. Shown: the mean of (rate at L − rate at main tour), with player-clustered intervals, 2013–2024 (`raw_gaps.csv`; `translation.py:291-365`).

**Men** (points per 100; + = higher at the lower level):

| Statistic | Challenger | Tour qualifying | Slam qualifying | Challenger qualifying |
|---|---|---|---|---|
| Aces per serve point | +0.4 [+0.3, +0.5] | +0.6 [+0.4, +0.7] | +0.7 [+0.4, +0.9] | +0.4 [−0.0, +0.8] tie |
| Double faults (lower = better) | +0.1 [+0.1, +0.2] | −0.1 tie | −0.0 tie | −0.0 tie |
| First serves in | −0.2 [−0.4, −0.0] | +0.1 tie | +0.7 [+0.3, +1.1] | +0.7 [+0.1, +1.4] |
| First-serve points won | +1.9 [+1.7, +2.1] | +2.4 [+2.1, +2.6] | +2.4 [+2.0, +2.8] | +2.7 [+2.0, +3.5] |
| Second-serve points won | +2.0 [+1.8, +2.3] | +2.7 [+2.4, +2.9] | +2.8 [+2.3, +3.3] | +4.0 [+3.1, +4.9] |
| Serve points won | +1.9 [+1.7, +2.1] | +2.5 [+2.3, +2.7] | +2.6 [+2.3, +3.0] | +3.4 [+2.7, +4.0] |
| Return points won | +4.5 [+4.3, +4.6] | +3.9 [+3.7, +4.1] | +4.4 [+4.1, +4.8] | +6.6 [+5.9, +7.2] |
| **Total points won** | **+2.9 [+2.8, +3.0]** | **+3.0 [+2.8, +3.1]** | **+3.3 [+3.0, +3.5]** | **+4.6 [+4.2, +5.0]** |
| Service games held | +3.7 [+3.3, +4.0] | +4.8 [+4.4, +5.2] | +5.0 [+4.3, +5.8] | +6.3 [+5.0, +7.5] |
| Return games won (breaks) | +8.4 [+8.0, +8.8] | +7.4 [+7.0, +7.9] | +7.8 [+7.0, +8.6] | +12.3 [+11.0, +13.6] |
| Break points saved | +2.3 [+1.8, +2.7] | +2.3 [+1.8, +2.9] | +3.0 [+2.0, +4.0] | +3.0 [+1.3, +4.7] |
| Break points converted | +3.8 [+3.4, +4.2] | +4.3 [+3.7, +4.9] | +4.1 [+3.1, +5.0] | +6.5 [+4.8, +8.2] |
| Player-seasons | 1,685 | 1,443 | 640 | 237 |
| Matches won, main tour → level | 37% → 61% | 37% → 61% | 34% → 63% | 32% → 69% |

**Women:**

| Statistic | WTA 125 | Tour qualifying | Slam qualifying |
|---|---|---|---|
| Aces per serve point | +0.1 tie | +0.5 [+0.4, +0.5] | +0.5 [+0.4, +0.6] |
| Double faults (lower = better) | −0.1 tie | +0.1 [+0.0, +0.2] | −0.4 [−0.6, −0.3] |
| First serves in | +0.4 [+0.1, +0.7] | −0.3 [−0.5, −0.1] | +1.1 [+0.8, +1.5] |
| First-serve points won | +1.8 [+1.4, +2.2] | +2.8 [+2.6, +3.1] | +3.2 [+2.8, +3.6] |
| Second-serve points won | +1.9 [+1.4, +2.3] | +2.2 [+1.9, +2.5] | +2.9 [+2.4, +3.4] |
| Serve points won | +1.8 [+1.5, +2.2] | +2.5 [+2.3, +2.7] | +3.3 [+2.9, +3.6] |
| Return points won | +3.3 [+3.0, +3.6] | +3.3 [+3.1, +3.5] | +3.7 [+3.3, +4.0] |
| **Total points won** | **+2.5 [+2.3, +2.7]** | **+2.8 [+2.7, +3.0]** | **+3.4 [+3.1, +3.7]** |
| Service games held | +4.0 [+3.3, +4.8] | +5.8 [+5.2, +6.3] | +6.9 [+5.8, +7.9] |
| Return games won (breaks) | +7.7 [+6.9, +8.5] | +7.5 [+7.0, +8.0] | +6.8 [+5.7, +7.9] |
| Break points saved | +1.3 [+0.6, +2.1] | +2.4 [+2.0, +2.9] | +2.1 [+1.2, +3.0] |
| Break points converted | +3.3 [+2.5, +4.1] | +3.3 [+2.8, +3.8] | +4.0 [+3.2, +4.8] |
| Player-seasons | 740 | 1,564 | 656 |
| Matches won, main tour → level | 38% → 57% | 38% → 59% | 35% → 62% |

* **Points won, games and break points all shift by 2–12 points** (Observed). The return side shifts most: weaker opponents serve worse.
* **Statistics a player controls alone barely move** (Observed): first serves in, double faults, and (less so) aces.
* **The reproduction check passes.** Re-run with the event-levels study's rule (completed and retired matches, any format), the men's Challenger shifts equal `blend/level_shift.csv` to the fourth decimal (Observed, `raw_gaps_blend_rule.csv`). Breaks are the exception (the correction above). Women's figures differ by up to 0.05 points: the 8 Oct WTA corrections.
* **Caution (Inferred).** A season with matches at both levels is partly chosen by that season's results: players drop after losing and climb after winning. That pushes these gaps up (section 6). The forecasting fits of section 3 do not have this problem.

## 2. Does the opponent adjustment remove the gap? (task 2)

### 2.1 The model, mirrored

**The form.** Per tour and serve statistic, as the IOS ([`ios_time.py`](../../../../src/eda/match_timing/ios_time.py)):
* **Value:** y = logit((x + ½)/(d + 1)) − logit(μ), where μ is the tour's average on the surface.
* **Model:** y ≈ O_server − D_returner.
* **Weights:** (d / typical units)^τ × 2^(−age/h).
* **Ridge:** κ, pulling every rating towards 0.

**The constants.** h, κ, τ and the typical units come from the IOS constants registry, version `2026-10-08_reference` (`translation.py:368-374`). Stage 3's surface averages are recomputed from the frozen Stage 0 (`:377-396`). They equal `stage4_constants.csv` for men. Women's differ by at most 0.0033 (`summary.json`, `surface_means_check`), because the stored file predates the 8 Oct WTA corrections.

**The timeline is leak-proof** (`weekly_solve`, `:513-591`):
* a result enters on the day after its latest possible finish;
* a match reads the last weekly solve on or before its earliest possible start (`:529-540`).

**Simplifications against the decided IOS.** Each one treats every level alike:
* the pooled IOS (no surface deviations);
* weekly snapshots instead of daily ones;
* no incremental step, so a match reads ratings up to a week older.

**The statistics.**
* Eight serve systems per tour: serve points, aces, double faults, first serves in, first- and second-serve points won, holds, break points saved.
* The return measures (return points, breaks, break points converted) are the returner's side of the same rows.
* Total points won combines both sides.

### 2.2 How much of the gap the joint solve removes

**The measure.** The same pairing as section 1, on residuals of the prior-only solve. A residual is actual minus expected, per 100 units (`residual_gaps.csv`).

| Statistic | Men: Challenger | Men: tour qualifying | Men: Slam qualifying | Women: WTA 125 | Women: tour qualifying | Women: Slam qualifying |
|---|---|---|---|---|---|---|
| **Total points won** | +2.9 → **+0.37** [+0.24, +0.50] | +3.0 → **+0.78** [+0.65, +0.92] | +3.3 → **+1.19** [+0.91, +1.47] | +2.5 → **+0.56** [+0.33, +0.80] | +2.8 → **+0.84** [+0.69, +1.00] | +3.4 → **+1.08** [+0.81, +1.36] |
| Serve points won | +1.9 → +0.16 tie | +2.5 → +0.70 | +2.6 → +0.67 | +1.8 → +0.52 | +2.5 → +0.73 | +3.3 → +1.03 |
| Return points won | +4.5 → +0.58 | +3.9 → +0.89 | +4.4 → +1.74 | +3.3 → +0.61 | +3.3 → +0.97 | +3.7 → +1.16 |
| Holds | +3.7 → +0.47 | +4.8 → +1.57 | +5.0 → +1.82 | +4.0 → +1.34 | +5.8 → +2.17 | +6.9 → +2.99 |
| Breaks | +8.4 → +1.44 | +7.4 → +2.11 | +7.8 → +3.84 | +7.7 → +2.18 | +7.5 → +2.84 | +6.8 → +3.62 |
| Break points saved | +2.3 → +1.37 | +2.3 → +1.54 | +3.0 → +1.57 | +1.3 → +0.85 | +2.4 → +1.74 | +2.1 → +1.19 |
| Aces | +0.4 → +0.11 | +0.6 → +0.03 tie | +0.7 → −0.05 tie | +0.1 → +0.10 tie | +0.5 → +0.16 | +0.5 → +0.16 |

* **The joint solve removes most of the gap** (Observed). Of the total-points gap it removes:
  * men: 87% (Challenger), 74% (tour qualifying), 64% (Slam qualifying), 82% (Challenger qualifying);
  * women: 78%, 70%, 68%.
* **What is left mixes selection with a real bias for women** (Observed, with the reading Inferred).
  * The same players do worse than expected at the main tour (men's total points −0.29 [−0.39, −0.19]; women's −0.34 [−0.48, −0.20], WTA 125 pairs) and better at the lower level.
  * Their membership depends on in-season results (section 6), which pushes both numbers away from zero.
  * The measures of section 2.4 use prior information only. They find little bias for men and a clear one for women on some statistics.

### 2.3 The level ("condition") effects, δ_L

**The model** (`effects_for_system`, `:681-750`; `batch_fe`, `:594-646`):
* every player-season gets its own serve and return rating;
* each lower level gets an unpenalised fixed effect (main tour = 0);
* the IOS's weights and κ apply;
* intervals cluster by event.

**What δ means.** How much better servers do at level L than the same players' season ratings predict against those returners. It is the level's serve-return balance: conditions, balls, courts, the data source. It cancels in total points won.

Points per 100; + = servers do better at the lower level than the ratings predict (`level_effects.csv`):

| Statistic | Men CH 2010–18 | Men CH 2019–24 | Men CHQ 2019–24 | Men TQ 2019–24 | Men GSQ 2019–24 | Women CH 2019–24 | Women TQ 2019–24 |
|---|---|---|---|---|---|---|---|
| Serve points won | −0.19 [−0.35, −0.03] | −0.60 [−0.81, −0.39] | −0.81 [−1.03, −0.59] | −0.25 [−0.48, −0.03] | −0.76 [−1.14, −0.38] | −0.43 [−0.70, −0.17] | +0.03 tie |
| Aces | −0.52 [−0.63, −0.42] | −0.73 [−0.87, −0.60] | −0.98 [−1.12, −0.83] | −0.51 [−0.66, −0.36] | −1.02 [−1.35, −0.68] | −0.16 [−0.26, −0.06] | −0.10 [−0.19, −0.01] |
| First-serve points won | +0.00 tie | −0.52 [−0.76, −0.28] | −0.73 [−0.99, −0.47] | −0.16 tie | −0.97 [−1.39, −0.54] | −0.59 [−0.89, −0.28] | −0.04 tie |
| Second-serve points won | −0.46 [−0.60, −0.33] | −0.55 [−0.71, −0.39] | −0.74 [−0.93, −0.56] | −0.20 tie | −0.47 [−0.88, −0.07] | −0.26 tie | −0.01 tie |
| Holds | −0.42 [−0.75, −0.09] | −1.10 [−1.50, −0.69] | −1.35 [−1.80, −0.91] | −0.53 [−0.99, −0.08] | −1.24 [−2.10, −0.38] | −1.36 [−1.98, −0.74] | −0.20 tie |
| Break points saved | −0.25 [−0.42, −0.09] | −0.12 tie | −0.93 [−1.21, −0.65] | −0.18 tie | −0.07 tie | −0.34 tie | −0.22 tie |

* **The lower levels are slightly more return-friendly than the main tour, for the same players** (Observed).
  * For points and holds the effects are a tenth to a third of the raw gaps, with the opposite sign: serve points −0.2 to −0.8, holds −0.4 to −1.4.
  * Aces are the exception: −0.5 to −1.2, as large as the raw gap (+0.4 to +0.7).
* **They drift.** Men's Challenger effect by era (`level_effects.csv`, eras):

  | | 2010–12 | 2013–15 | 2016–18 | 2019–21 | 2022–24 |
  |---|---|---|---|---|---|
  | Serve points won | +0.15 tie | −0.21 tie | −0.48 [−0.76, −0.19] | −0.41 [−0.72, −0.10] | −0.73 [−1.00, −0.45] |
  | Holds | +0.24 tie | −0.54 tie | −0.93 [−1.52, −0.34] | −0.69 [−1.31, −0.07] | −1.37 [−1.91, −0.83] |
  | Aces | −0.32 [−0.50, −0.14] | −0.51 [−0.68, −0.34] | −0.73 [−0.93, −0.53] | −0.62 [−0.85, −0.40] | −0.81 [−0.98, −0.63] |

  * It is the "uneven" shape the owner's input check warns about (Inferred): a translation fitted once goes stale, so it must be refitted walk-forward.
* **Grass carries the largest effects** (Observed). Men's aces on grass at Challengers −2.0 and in tour qualifying −2.4; tour-qualifying holds on grass −2.9. Women's WTA 125 effects sit on clay: serve points −0.9, holds −2.7.

### 2.4 Mixed matches: ratings built from lower-level evidence against main-tour ones

**In the batch fit, at the lower level itself** (`level_effects.csv`, variant "level x home tiers", 2010–2024, points per 100):

| | both lower-based | main-tour-based server, lower-based returner | lower-based server, main-tour-based returner |
|---|---|---|---|
| Men, Challenger, serve points | −0.43 [−0.56, −0.31] | **+0.42 [+0.19, +0.64]** | **−0.92 [−1.15, −0.70]** |
| Men, Challenger, holds | −0.80 [−1.05, −0.54] | +0.64 [+0.19, +1.09] | −1.79 [−2.26, −1.31] |
| Men, Challenger, break points saved | −0.30 [−0.43, −0.17] | +3.49 [+3.00, +3.99] | −2.31 [−2.75, −1.88] |
| Women, tour qualifying, holds | −0.74 [−1.15, −0.33] | **+4.11 [+3.32, +4.91]** | **−4.68 [−5.50, −3.86]** |
| Women, tour qualifying, second-serve points | −0.54 [−0.69, −0.38] | +2.49 [+2.13, +2.85] | −2.51 [−2.85, −2.17] |

* **When the two kinds of player meet, the main-tour-based one beats the ratings and the lower-based one falls short** (Observed).
  * Inferred: in the joint fit, the two groups' ratings are not on one scale.

**At the main tour, which is what the model forecasts.** The prior-only solve; positive = lower-based players overrated against main-tour-based ones (`ios_arm_bias.csv`, arm "ios", 2013–2024, per 100):

| Statistic | Men | Women |
|---|---|---|
| Serve points won | +0.04 [−0.07, +0.16] tie | −0.08 [−0.20, +0.05] tie |
| Aces | +0.10 [+0.04, +0.17] | +0.06 [+0.01, +0.11] |
| First-serve points won | +0.06 tie | +0.22 [+0.08, +0.37] |
| Second-serve points won | +0.11 tie | **+0.40 [+0.23, +0.58]** |
| Holds | +0.15 tie | **+0.58 [+0.25, +0.92]** |
| Break points saved | +0.36 [+0.08, +0.64] | **+1.02 [+0.75, +1.29]** |

* **Men: little bias at the main tour** (Observed). Only aces (+0.10) and break points saved (+0.36) clear zero.
* **Women: lower-based players are overrated** on holds, second- and first-serve points and break points saved (Observed). The 2019–2024 half shows the same.

**Where the bias sits:** by the amount of evidence in the rating. Main-tour rows, residual per 100 (`residual_by_evidence.csv`); negative = the group is overrated:

| Women, lower-based | Under 5 typical matches of evidence | 5–20 | 20 or more |
|---|---|---|---|
| Break points saved (serving) | **−2.99 ± 1.25** (760 rows) | −0.20 ± 0.76 | −0.23 ± 0.33 |
| Break points saved (returning) | −1.83 ± 1.29 | −1.27 ± 0.78 | −0.85 ± 0.35 |
| Holds (serving) | **−2.56 ± 1.02** (1,427 rows) | −0.08 ± 0.75 | −0.63 ± 0.46 |
| Second-serve points (serving) | **−1.84 ± 0.73** (889 rows) | −0.17 ± 0.41 | −0.05 ± 0.22 |

* **The bias sits on thin evidence** (Observed). Main-tour-based players almost always have 20+ matches of evidence, and their residuals are near zero.
* **For men,** thin-evidence lower-based players are rare at the main tour: 119–311 rows per statistic under 5 matches of evidence.

**Against the lower-level share of the rating's evidence.** Weighted slope of the main-tour residual, per 100 per unit of share (`residual_share_slopes.csv`):
* **Men:** ties or positive. Holds +0.56 [+0.05, +1.08]: servers whose rating leans on lower levels do slightly *better* than predicted. So there is no contamination that grows with the share.
* **Women:** it grows for break points saved and second-serve points.
  * Break points saved: server's share −2.16 [−2.83, −1.48], returner's share +2.21 [+1.57, +2.86].
  * Second-serve points: −0.54 [−0.96, −0.13] and +0.92 [+0.52, +1.32].
* **The opponent side** (the brief's check: a return rating built mostly from lower-level matches) is the returner's share.
  * A positive slope means servers do better than predicted against such a returner, so his return rating is too high.
  * Women: yes, for break points saved and second-serve points (above).
  * Men: ties on every statistic except aces (+0.26 [+0.12, +0.40]).

### 2.5 The mechanism

* **Observed. The bias does not need the lower-level rows.** With every lower-level row removed ("main_only"), the women's main-tour bias is as large: break points saved +1.16, second-serve points +0.43, holds +0.49.
* **Observed. It grows with the pull towards the single average.** With the ridge pull towards the pool's zero five times stronger, it multiplies: women's holds +2.33, men's serve points +0.59.
* **Observed. The zero sits far below the main-tour players.** The average rating of player-seasons with enough evidence, by home tier, 2010–2018 batch fit (`tier_prior_means.csv`). On men's serve points won (log-odds; O = serve rating, D = return rating), O / D:
  * main-tour-based +0.38 / +0.32;
  * qualifying-based +0.21 / +0.16;
  * Challenger-based +0.20 / +0.19;
  * ITF-based +0.09 / +0.09.
  * Women's holds show the same shape: +0.43 / +0.34 main tour, +0.13 / +0.11 ITF.
* **Inferred. A prior problem, not an equivalence problem.**
  * The ridge pulls every player with thin box-score evidence towards one pool-wide zero. That zero is nobody's peer group.
  * Thin evidence is common for women arriving from the ITF, results-only before 2025 (role 02: 26 ITF results without a box score per low-exposure woman per year).
  * Such players then meet well-evidenced main-tour players, and the joint solve misplaces them.
  * The lower-level box scores are part of the cure: more evidence moves a player off the prior. They are not the cause.
  * The same zero point moves when the pool's mix moves. That is the [input audit's finding #6](../../input_data_audit/README.md): the ITF box scores of 2025 shifted the IOS level.

## 3. The exchange rate (task 3)

### 3.1 Inside the joint solve (opponent-adjusted)

**The arms.** The prior-only solve of section 2 with only the treatment of lower-level rows changed (`arms`, `:756-780`):
* **main_only:** lower-level rows left out;
* **translated:** each lower-level row shifted by its level's δ from the 2010–2018 batch fit;
* **lam2, lam4:** each lower-level row's weight halved or quartered;
* **tr_lam2:** both, translated and halved;
* **tier_prior:** the ridge pulls each player towards his home tier's mean (from the 2010–2018 fit) instead of 0. His tier is known from his own earlier matches, every level's results included (`:578-580`);
* **tp_tr_lam2:** the tier prior plus translation and the 2× discount.

**The score.** Main-tour rows of 2019–2024. Gain over the IOS as built, milli per unit, + = the arm predicts better; intervals from 28-day blocks (`ios_arms.csv`).

| Statistic | IOS over the tour average | main_only | translated | lam2 | tr_lam2 | tier_prior | tp_tr_lam2 |
|---|---|---|---|---|---|---|---|
| Men, serve points won | 3.29 | −0.30 [−0.36, −0.24] | +0.01 [+0.00, +0.01] | +0.02 [+0.01, +0.03] | +0.03 [+0.01, +0.04] | −0.00 tie | +0.02 [+0.01, +0.04] |
| Men, aces | 10.65 | −0.55 [−0.64, −0.46] | **+0.06 [+0.01, +0.11]** | +0.01 tie | +0.06 [+0.02, +0.10] | +0.01 [+0.00, +0.02] | +0.07 [+0.03, +0.12] |
| Men, first-serve points won | 5.17 | −0.49 [−0.59, −0.39] | +0.00 tie | +0.02 [+0.00, +0.04] | +0.02 [+0.01, +0.04] | −0.00 tie | +0.02 tie |
| Men, second-serve points won | 2.15 | −0.30 [−0.37, −0.23] | +0.01 [+0.00, +0.02] | +0.03 [+0.02, +0.05] | +0.04 [+0.02, +0.06] | −0.00 tie | +0.04 [+0.02, +0.06] |
| Men, holds | 13.63 | −1.27 [−1.56, −0.98] | +0.02 tie | **+0.20 [+0.15, +0.25]** | +0.21 [+0.15, +0.27] | −0.01 tie | +0.20 [+0.14, +0.27] |
| Men, break points saved | 2.01 | −0.20 [−0.38, −0.02] | +0.05 [+0.03, +0.08] | +0.08 [+0.03, +0.13] | +0.12 [+0.07, +0.18] | +0.04 [+0.03, +0.05] | **+0.17 [+0.11, +0.23]** |
| Women, serve points won | 2.58 | −0.29 [−0.35, −0.23] | +0.00 tie | +0.00 tie | +0.00 tie | +0.01 tie | +0.01 tie |
| Women, aces | 7.44 | −0.40 [−0.47, −0.33] | −0.00 tie | −0.02 [−0.04, −0.01] | −0.02 [−0.04, −0.01] | +0.01 [+0.00, +0.01] | −0.01 tie |
| Women, first serves in | 4.04 | −0.43 [−0.51, −0.35] | −0.01 tie | −0.04 [−0.06, −0.02] | −0.05 [−0.07, −0.02] | −0.00 tie | −0.05 [−0.07, −0.03] |
| Women, first-serve points won | 4.75 | −0.34 [−0.41, −0.27] | −0.00 tie | −0.01 tie | −0.01 tie | +0.02 [+0.01, +0.04] | +0.02 tie |
| Women, second-serve points won | 1.71 | −0.19 [−0.25, −0.13] | +0.00 tie | −0.01 tie | −0.01 tie | +0.03 [+0.02, +0.05] | +0.03 [+0.01, +0.06] |
| Women, holds | 13.62 | −1.16 [−1.48, −0.85] | −0.02 tie | +0.02 tie | +0.01 tie | **+0.08 [+0.02, +0.13]** | +0.11 [+0.01, +0.21] |
| Women, break points saved | 1.91 | −0.26 [−0.35, −0.17] | +0.01 tie | −0.03 tie | −0.03 tie | **+0.07 [+0.05, +0.09]** | +0.05 [+0.00, +0.10] |

* **Lower-level box scores are informative** (Observed). Leaving them out costs every statistic 0.2–1.3 milli per unit: 5–14% of what the IOS gains over the tour average.
  * For low-exposure players it costs 0.5–4.9. Men's holds −4.88 [−5.74, −4.03], women's holds −3.44 [−4.28, −2.60].
* **Translating by the condition offsets gains little** (Observed). The only clear case is men's aces (+0.06).
* **The best discount is mild, and only for men** (Observed).
  * Men: λ = 2 helps holds (+0.20), break points saved (+0.08) and second-serve points (+0.03). λ = 4 adds nothing for holds (+0.21) and costs elsewhere (double faults −0.03).
  * Women: λ = 1 is best. λ = 2 costs a little (first serves in −0.04, aces −0.02); λ = 4 costs on every statistic (holds −0.19).
* **The tier prior helps women** (Observed). Holds +0.08, break points saved +0.07, second-serve points +0.03, first-serve points +0.02.
  * Low-exposure women: holds +0.22 [+0.06, +0.38], break points saved +0.15 [+0.10, +0.21].
  * Men: break points saved +0.04, otherwise ties.
* **Stronger pull, to either target, hurts** (Observed). The ridge five times stronger, towards 0 or towards the tier's mean, costs most statistics (e.g. women's holds −0.77 and −0.15). The decided κ with a tier mean is the right strength.
* **The tune seasons, 2013–2018, agree** (Observed). The one exception is women's holds under the tier prior, which gained more there (+0.24 [+0.03, +0.45]).
* **Scale.** These are small next to the IOS's own gain over the average: men's holds λ = 2 is +0.20 of 13.63. In match terms they are untested (section 7).

### 3.2 On raw rates: the credibility estimator

**The estimator.** For a player's next main-tour match (`credibility`, `:1149-1218`; `cred_theta`, `:1062-1074`):

θ̂ = (k·μ + X_main + Σ_L w_L·(X_L − δ_L·N_L)) / (k + N_main + Σ_L w_L·N_L)

* X and N are the player's own successes and units at each level over the previous 365 days, strictly earlier matches only.
* μ is the main tour's surface average.
* w_L = 1/λ_L and δ_L are per statistic and level; k is the prior strength in units.
* **Fit:** maximum binomial likelihood on 2013–2018 targets, analytic gradient (`cred_fit`, `:1094-1146`).
* **Score:** 2019–2024 targets.
* **Arms:**
  * **main-only:** w = 0;
  * **pooled:** w = 1, δ = 0. This is how `points_52w` treats the levels;
  * **translated:** δ fitted, w = 1;
  * **discounted:** w fitted, δ = 0;
  * **translated + discounted:** both fitted.

**The fitted exchange rates.** Translated + discounted arm; 90% intervals from 30 player-bootstrap draws (`credibility_params.csv`). Each cell: w, then δ in points, then the implied "one match at this level ≈ x main-tour matches" (w × units per match at the level ÷ units per main-tour match; men's main-tour matches are longer because of best-of-five Slams, `units_per_match.csv`).

| Men | Challenger | Tour qualifying | Slam qualifying | Prior k (units) |
|---|---|---|---|---|
| Serve points won | 0.58 [0.49, 0.80]; +3.5 [+2.9, +4.0]; **0.52** | 1.04 [0.85, 1.49]; +2.4; 0.91 | 1.19 [0.43, 1.75]; +4.7; 1.10 | 860 points |
| Return points won | 0.66 [0.41, 0.89]; +5.9 [+5.5, +6.9]; **0.58** | 0.95 [0.68, 1.21]; +4.7; 0.83 | 0.92 [0.27, 1.66]; +12.7; 0.85 | 1,624 |
| Total points won | 0.73 [0.58, 0.93]; +3.9 [+3.5, +4.2]; **0.64** | 1.10 [0.84, 1.35]; +2.9; 0.96 | 0.97 [0.19, 1.65]; +6.7; 0.90 | 1,231 |
| Holds | 0.78 [0.64, 0.98]; +6.8 [+5.9, +8.0]; **0.68** | 1.06 [0.63, 1.32]; +3.1; 0.92 | 2.67 [1.67, 3.00]; +6.8; (thin) | 141 games |
| Breaks | 0.56 [0.45, 0.79]; +11.7 [+10.4, +13.5]; **0.49** | 0.63 [0.44, 1.07]; +9.0; 0.54 | 1.19 [0.68, 2.01]; +19.6; 1.09 | 276 |
| First-serve points won | 0.73 [0.57, 1.09]; +3.1; 0.64 | 1.33 [0.97, 1.82]; +2.2; 1.15 | 2.02 [0.98, 3.00]; +4.7; (thin) | 508 |
| Second-serve points won | 0.63 [0.44, 0.87]; +3.7; 0.57 | 0.70 [0.32, 1.04]; +3.8; 0.62 | 0.82 [0.11, 1.61]; +4.4; 0.75 | 634 |
| Aces | 0.49 [0.38, 0.64]; +0.8; 0.43 | 1.20 [0.98, 1.59]; +0.9; 1.04 | 0.97 [0.52, 1.52]; +0.8; 0.90 | 593 |

| Women | WTA 125 | Tour qualifying | Slam qualifying | Prior k (units) |
|---|---|---|---|---|
| Serve points won | 1.09 [0.55, 1.72]; +1.9; 1.08 | 1.16 [1.05, 1.44]; +3.8 [+3.3, +4.5]; 1.14 | 1.23 [0.67, 1.99]; +1.9; 1.24 | 791 points |
| Return points won | 1.11 [0.16, 1.81]; +4.5; 1.10 | 1.40 [1.02, 1.77]; +4.9; 1.36 | 1.46 [0.80, 2.20]; +7.4; 1.47 | 1,799 |
| Total points won | 0.92 [0.41, 1.47]; +3.0 [+1.6, +4.7]; 0.91 | 1.42 [1.21, 1.70]; +3.9 [+3.5, +4.2]; 1.39 | 1.14 [0.81, 1.50]; +4.3; 1.14 | 1,894 |
| Holds | 0.98 [0.65, 2.03]; −0.9 (wide); 0.96 | 0.95 [0.74, 1.25]; +9.6 [+8.3, +12.3]; 0.93 | (not identified) | 95 games |
| Breaks | 0.83 [0.50, 1.73]; +2.4 (wide); 0.81 | 1.46 [1.03, 2.04]; +11.5 [+9.6, +14.0]; 1.42 | (not identified) | 246 |
| First-serve points won | 1.06 [0.46, 1.76]; +2.9; 1.07 | 1.01 [0.84, 1.34]; +3.7; 0.99 | 1.31 [0.94, 1.93]; +1.3; 1.35 | 307 |
| Second-serve points won | 1.24 [0.41, 2.27]; +0.2 (wide); 1.19 | 1.11 [0.81, 1.41]; +4.3; 1.09 | 0.84 [0.24, 1.71]; +2.2; 0.82 | 703 |
| Aces | 1.06 [0.90, 1.74]; +0.9; 1.05 | 1.00 [0.81, 1.17]; +0.5; 0.98 | 0.83 [0.48, 1.18]; +0.0; 0.83 | 188 |

* **Translation comes first** (Observed). Fitted to predict the next main-tour match, δ is as large as or larger than section 1's same-season gaps. Men's Challenger total points: +3.9 against +2.9.
  * Inferred: the forecasting fit also absorbs whom these players meet in their next main-tour match and how they came to play it. The raw estimator does not model either.
* **After translation, men's Challenger evidence is worth about two-thirds of main-tour evidence** (Observed).
  * w = 0.5–0.8 per unit, so one Challenger match ≈ 0.5–0.7 main-tour matches.
  * Tour qualifying and Slam qualifying ≈ 1.
* **Women's lower levels are worth about one-for-one** (Observed). Tour qualifying is slightly above 1. WTA 125 intervals are wide (4,323 matches).
* **Challenger qualifying** is fitted but thin, especially for women (716 matches): `credibility_params.csv` only.
* **Thin cells hit their bounds** (Observed): w = 3 or δ = ±30 points. These are marked "not identified" or "(thin)".

**Gains, 2019–2024.** Milli per unit, + = the named arm better (`credibility_scores.csv`):

| Statistic | Translated + discounted vs pooled | vs main-only | Low exposure: vs pooled | Low exposure: vs main-only |
|---|---|---|---|---|
| Men, total points won | +0.22 [+0.18, +0.27] | +0.07 [+0.05, +0.09] | +0.68 [+0.52, +0.84] | +0.40 [+0.29, +0.51] |
| Men, return points won | +0.43 [+0.31, +0.54] | +0.11 [+0.07, +0.15] | +1.15 [+0.80, +1.51] | +0.40 [+0.17, +0.63] |
| Men, holds | +0.45 [+0.21, +0.69] | +0.74 [+0.50, +0.98] | +1.94 [+0.83, +3.05] | +4.68 [+3.30, +6.07] |
| Men, breaks | +1.98 [+1.47, +2.49] | +0.55 [+0.36, +0.73] | +5.22 [+3.55, +6.90] | +1.80 [+0.66, +2.93] |
| Men, aces | +0.06 [+0.03, +0.09] | +0.44 [+0.35, +0.54] | +0.16 [+0.02, +0.30] | +2.44 [+2.00, +2.87] |
| Men, break points saved | −0.02 tie | +0.12 tie | +0.21 tie | +0.65 tie |
| Women, total points won | +0.19 [+0.15, +0.23] | +0.10 [+0.07, +0.12] | +0.70 [+0.57, +0.83] | +0.49 [+0.39, +0.60] |
| Women, return points won | +0.23 [+0.17, +0.29] | +0.12 [+0.08, +0.16] | +0.68 [+0.47, +0.89] | +0.46 [+0.29, +0.64] |
| Women, holds | +0.68 [+0.39, +0.97] | +0.79 [+0.50, +1.08] | +3.44 [+2.33, +4.56] | +4.53 [+3.37, +5.69] |
| Women, breaks | +1.17 [+0.89, +1.44] | +0.59 [+0.40, +0.79] | +3.60 [+2.71, +4.50] | +2.42 [+1.68, +3.17] |
| Women, break points saved | +0.05 tie | +0.14 [+0.06, +0.23] | +0.33 [+0.13, +0.52] | +0.55 [+0.32, +0.78] |

* **Pooling raw lower-level rates as equivalent is worse than ignoring them for the return statistics** (Observed). Against main-only: men's breaks −1.43, return points −0.32, total points −0.15, break points converted −0.10; women's breaks −0.58, return points −0.11, total points −0.10. So treat them as informative, never as equivalent.
* **Translated and weighted, they beat main-only on every statistic** (Observed). The two ties are men's break points saved and women's break points converted.
* **Discounting adds little once translated** (Observed): at most +0.04 over translation alone (+0.06 for low-exposure players). Discounting without translation pushes the return-statistic weights to 0. The translation carries the gain.

### 3.3 "One Challenger match ≈ x main-tour matches"

| Context | Men | Women |
|---|---|---|
| Raw rates, after translation (section 3.2) | 0.5–0.7 Challenger; ≈ 1 qualifying | ≈ 1 (WTA 125 and qualifying) |
| Inside the joint solve (section 3.1) | 0.45–0.9 (λ 1–2; 2 for holds and break points saved) | ≈ 1 (λ = 1) |
| Results, Elo (section 4) | 0.75–1 | 0.75–1 |
| Raw rates, untranslated | 0 for return statistics (as they stand they mislead) | 0 for return statistics |

## 4. The results channel (task 4, brief)

* **From the event-levels study** ([README §3, §8](../../event_levels/README.md)).
  * Elo runs over every level with one K schedule. It rates players arriving from lower levels about right: β +0.11 men, +0.09 women (a tie).
  * The market under-rates them: β ≈ +0.13 on the close, worth about 0.1 mLL as a model input (a tie).
* **This test.** A plain Elo (K = 250 / (n + 5)^0.4, every played match in order) with Challenger-tier and ITF-tier updates multiplied by m. Main-tour matches 2013–2024, mLL against m = 1, + = better (`elo_k.csv`; `:1276-1326`).

| Challenger ×, ITF × | Men | Women |
|---|---|---|
| 0, 1 | −6.77 [−8.38, −5.17] | −0.53 tie |
| 0.5, 1 | −0.58 [−1.10, −0.06] | −0.04 tie |
| 0.75, 1 | +0.01 tie | +0.03 tie |
| 1.25, 1 | −0.41 [−0.63, −0.20] | −0.12 tie |
| 1, 0 | −0.79 tie | **−6.39 [−8.13, −4.65]** |
| 1, 0.5 | +0.16 tie | −0.39 tie |
| 1, 0.75 | +0.13 tie | +0.06 tie |
| 0.75, 0.75 | +0.17 tie | +0.09 tie |
| 1.25, 1.25 | −0.58 [−0.82, −0.35] | −0.52 [−0.78, −0.25] |

* **Results need no discount** (Observed). 0.75 ties full weight; 1.25 is worse. With a slope fitted on 2013–2018 and applied to 2019–2024, every multiplier from 0.75 to 1.25 ties full weight. The one exception is both at 1.25 for women: −0.34 [−0.68, −0.00].
* **Men need their Challenger results and women their ITF results.** Dropping them costs 6–7 mLL. Elo is a priced-in control (the owner's thesis), so this stays a check, not a lead.

## 5. ITF (task 5)

**Coverage** (counts only; `coverage_by_level_year.csv`):
* ITF and ITF-qualifying box scores: 0% in 2010–2024.
* 2025: 95% of 17,906 men's and 94% of 18,189 women's ITF matches.
* 2026: 99% of 6,894 / 7,224.
* All of this lies inside the holdout.

**What results alone show:**
* **ITF results deserve full weight in Elo.** Women's ITF results at zero weight cost 6.4 mLL.
* **ITF-based players' place in the box-score scale** can be estimated from those who also play qualifying and Challengers. The tier prior's ITF means rest on about 2,200–2,600 men's and 500–1,300 women's player-seasons per statistic (`tier_prior_means.csv`).
* **Their history share:** role 02's measure.

**What cannot be estimated:** ITF's box-score δ and λ. They need ITF box scores of non-holdout seasons: plan P7, SofaScore 2018–2024.

**How to rerun on a candidate.** `translation.py` reads any Stage 0 (`--stage0-dir`):
* every level with at least 200 box-score rows gets its own δ (batch fit), weights in the arms, tier mean and credibility δ and w (`present_levels`, `:1342-1344`; test `test_a_level_with_box_scores_gets_its_own_offset_and_weight`);
* with ITF box scores only from 2018, the windows must move so that ITF has fitting and scoring seasons;
* pass the candidate's own timeline with `--timing`. Matches the timeline lacks get a cautious window (earliest start = tournament date − 7, latest finish + 21; counted in `summary.json`, `timing_fallback_rows`).

```
./python.sh src/eda/lower_level_evidence/translation.py --stage0-dir <candidate>/data/studies/predictability_diagnostic \
    --timing <candidate>/data/studies/match_timing/timing.parquet --fit-window 2018-2021 --tune 2019-2021 \
    --validate 2022-2024 --label candidate_itf_p7
```

**Inferred. Expect the tier prior to matter most here.** ITF-based women are the thin-evidence group of section 2.4. Role 02 finds that P7 would raise women's lower-level share of box-score evidence by 11–14 points, in 2019–2024 only.

## 6. Selection biases (task 6)

* **Boundary players** (Inferred).
  * Who plays both levels in a season depends on that season's results. A player who loses on the main tour drops to Challengers; one who wins at Challengers climbs.
  * Both push the same-season gaps of sections 1 and 2.2 up. They make the both-level players' main-tour residuals negative (−0.29 points of total points, men).
  * **Control:** the conclusions rest on prior-only designs:
    * the weekly arms (every match scored with ratings from earlier results);
    * the credibility estimator (the previous 365 days only);
    * the home-tier, evidence and share analyses (groups defined from earlier matches only).
  * There the men's main-tour bias is near zero.
* **Regression to the mean, and moving up after a good run** (Inferred). The forecasting fits target the next main-tour match, so a lucky run that earned a promotion is discounted automatically: it is part of the fitted δ and w.
* **Survivorship** (Inferred). The tier means average player-seasons with at least 5 typical matches of evidence. Those players are better than true newcomers, so the tier prior is still generous to newcomers. That fits what the tier prior leaves behind (women's break points saved +0.70).
* **Era trends** (Observed). The condition offsets drift (section 2.3). The arms use δ from 2010–2018 on 2019–2024, a conservative test of translation. A live version must refit walk-forward.
* **Strictly prior-only.**
  * The weekly solve passes a leak probe (test `test_weekly_solve_never_reads_a_result_that_could_not_precede_the_match`).
  * Histories and credibility sums use strictly earlier matches by Stage 0's order (`player_sequence`, `:245-257`).
  * Home tiers come from the player's own earlier matches only.
* **What is in-sample.** The batch effects by era, surface and home tier are descriptive. In the tune seasons (2013–2018), the δ and tier means the arms use come from the overlapping 2010–2018 fit. The 2019–2024 validation is clean.

## 7. What it means for the model (Suggestions)

1. **Raw and one-step aggregates:** `points_52w`, and the 17 one-step forms that role 01 found keep 78% of the level shift.
   * Translate lower-level rates per statistic and level before pooling, with δ refitted walk-forward on earlier seasons.
   * Then weight a men's Challenger unit at about 0.6–0.8 and everything else at about 1.
   * This is this report's clearest gain at the statistic level: +0.2 (total points) to +2.0 (breaks) milli per unit over equivalence, and 2–5 times that for low-exposure players.
2. **Joint solves:** the IOS profile and `ios_points_short` (22 inputs); probably `ratings_iid` as well, which is not tested here.
   * Keep the lower-level rows at about equal weight. Consider half weight for men's holds and break points saved.
   * Add the condition offset where it is clear (aces), refitted walk-forward.
   * **Replace the single pool-wide prior by a home-tier prior.** This is the owner's UFC idea in this setting: an unknown player starts at the average of his peers, not at the average of the whole pool. It removes most of the women's bias and scores better.
3. **Elo:** keep full weight for Challenger and ITF results.
4. **Test it as a candidate, as the guardrail requires.** These are likelihood gains on the statistics, not on the match.
   * Build each change with `run_chain.py --setup --candidate`, then run `compare.py` (input check first).
   * Expect small match-level effects. The event-levels study found the lower-level share worth about 0.1 mLL. The IOS centring study found the products' drift cost nothing measurable.
   * The order to try (Inferred, by the size of the statistic-level gain): `points_52w` translated; the forms translated; the IOS home-tier prior.
5. **ITF.** When P7's box scores arrive, rerun this analysis with moved windows (section 5) before they enter any input. Fit the tier prior first: ITF-based players are the thin-evidence group.

## What it does not show

* **No match-level (TabPFN) effect.** No GPU fit was run, by the ground rules.
* **A simplified mirror.** The IOS form here is pooled and weekly, with no incremental step and no surface deviations. Its score is the statistic's likelihood, not the model's.
* **The one-step forms are not modelled directly.** The raw credibility estimator is their nearest stand-in. Role 01 measured that they keep 78% of the raw shift.
* **`ratings_iid`** (Stage 3's online ratings) is not mirrored.
* **A coarse search.** The discount grid is coarse (1, 2, 4, none). The tier prior was tried at the IOS's κ and at 5×, with means fixed from 2010–2018, not walk-forward.
* **Thin cells.** Women's Challenger qualifying, women's Slam-qualifying holds and breaks, and several bootstrap parameters sit at their bounds: not identified.
* **ITF** box-score translation: impossible before a non-holdout ITF box-score history exists.

## Checks and tests

* **Tests:** 19 in `test/lower_level_evidence/test_translation.py`, all pass.
  * The batch fit recovers planted level effects (+0.25 and −0.15 to ±0.02) and equals a dense direct solve to 1e-6.
  * The weekly solve equals the batch ridge at the end of the timeline (no decay), and a leak probe shows no later result moving an earlier match.
  * The tier prior gives a player without evidence exactly his tier's mean.
  * The credibility fit recovers a planted δ (0.03) and λ (2.5). Its arms rank as planted. Its analytic gradient equals finite differences.
  * The history window equals a brute-force count.
  * A planted raw shift is recovered.
  * Elo with zero weight freezes the ratings.
  * The holdout guard: a filtered read that drops a 6 Jan 2025 match even with `--through 2026`; the CLI refuses holdout seasons and overlapping windows.
  * A level with box scores (ITF in a candidate) gets its own offset and weight.
* **Reproduction:** `blend/level_shift.csv`, as section 1 says.
* **Surface averages:** against `stage4_constants.csv`, as section 2.1 says.
* **Solvers:** every weekly and batch solve converged (`summary.json`, `solver`).

## Code and outputs

| What | Where |
|---|---|
| Code (CLI: `--stage0-dir`, `--timing`, `--through`, `--label`, `--out`, `--steps`, `--workers`, `--boot`, `--fit-window`, `--tune`, `--validate`) | `src/eda/lower_level_evidence/translation.py` |
| Tests | `test/lower_level_evidence/test_translation.py` |
| Raw gaps; the event-levels rule's reproduction | `data/studies/lower_level_evidence/translation/reference_2026-10-08/raw_gaps.csv`, `raw_gaps_blend_rule.csv` |
| Level effects (windows, eras, surface, home tiers) and tier means | `level_effects.csv`, `tier_prior_means.csv` |
| Weekly arms: scores and main-tour bias per arm | `ios_arms.csv`, `ios_arm_bias.csv` |
| Residual diagnostics (the IOS as built) | `residual_gaps.csv`, `residual_by_evidence.csv`, `residual_by_share.csv`, `residual_share_slopes.csv`, `evidence_shares.csv` |
| Credibility estimator: parameters with bootstrap draws, scores, units per match | `credibility_params.csv`, `credibility_scores.csv`, `units_per_match.csv` |
| Elo multipliers; box-score coverage by level and year | `elo_k.csv`, `coverage_by_level_year.csv` |
| Run record (data counts, constants, windows, solver statistics, the δ used) | `summary.json` |

Run, from the repository root (about 8 minutes on 8 workers):

```
./python.sh src/eda/lower_level_evidence/translation.py --boot 30
./python.sh -m pytest test/lower_level_evidence/test_translation.py -q
```
