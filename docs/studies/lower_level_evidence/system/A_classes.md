# Role A: which statistics depend on the opponent, and is the level effect an opponent effect?

9 October 2026 · Role A (classifier) of the level-evidence system run ([SPEC](SPEC.md) §4–§6) · Research evidence, not a
decision.

**The owner's question** (verbatim): "identify wheter a statistic is independent of its opponent or dependent to figure
out if it qualifies for an offset depending on level of skill. For example how many points given up on their break is
dependent of the opponent. Age is not dependent on the opponent. 1st Serve speed is not really dependent on the
opponents skill. Most stats will be dependent on the opponent I believe?"

**Keys.**
* *Observed* = computed here (file cited, all under `data/studies/lower_level_evidence/system/classes/`, written
  `classes/` below) or read in code (`path:line`). *Inferred* = reasoning. *Suggestion* = a proposal.
* **γ** = how far a statistic moves when the opponent is 100 Elo points stronger, same player, same season, on the main
  tour. Units: the logit of the rate per opportunity, the builders' scale (log for break points faced per service game).
  **γ < 0 = the statistic falls against stronger opponents.** For intuition: on a rate near 50%, 0.04 logit is 1 point
  per 100.
* **Level shifts** are "level L minus main tour, same player, same season". **+ = the statistic is higher at the lower
  level.** Whether higher is better depends on the statistic (not for double faults, break points faced, and the defence
  statistics' aces).
* Intervals are 95%, clustered by player.
* **Holdout:** no outcome of a 2025–2026 match was read. The analysis reads box scores of events before 30 Dec 2024
  (asserted, `classify.py`: `analysis_rows`, `player_rows`, `speed_checks`); `gamma()` refuses later outcomes unless
  called for the SPEC's mechanical fits. 2025–2026 appear only as counts.

## In short

* **Most statistics depend on the opponent; the "style" ones do not** (Observed, `gamma_main.csv`). Against an opponent
  100 Elo stronger, same player and season: total points won −0.056 logit (men) / −0.069 (women), about −1.4 / −1.7
  points per 100; holds −0.146 / −0.155; breaks −0.186 / −0.214; aces −0.075 / −0.054. **First serves in: +0.000 /
  −0.002, intervals spanning 0. Double faults: −0.012 / +0.001.** The owner's guess holds: 17 of 19 men's and 16 of 19
  women's box-score statistics are opponent-dependent (class OPP).
* **The class table** (rule fixed at 20:12:50 UTC, before any γ; `classes.csv`). OPP: every points, games and
  break-point statistic, aces, and the defence statistics. ENV (no material opponent dependence): first serves in and
  double faults on both tours, and women's first serves in faced. Three calls sit within 20% of the line: men's double
  faults (0.091 against 0.10), women's first serves in faced (0.095) and women's aces (0.117, OPP).
* **The level effect is an opponent effect** (Observed, `level_decomposition.csv`). γ × the opponents' Elo gap explains
  **100% of men's Challenger shift in total points won** (raw +0.117 logit; left over −0.000 [−0.006, +0.005]), 89% in
  tour qualifying and 80% in Slam qualifying. Women: 92% (tour qualifying), 85% (WTA 125), 77% (Slam qualifying). With
  Stage 3's one-scale opponent ratings in place of Elo: 78–95% (`level_decomposition_stage3.csv`).
* **What is left is a serve–return balance, not skill** (Observed). At Challengers men's serve statistics sit below
  what the weaker returners imply (serve points −0.043, holds −0.108, aces −0.118 logit) and return statistics above
  (return points +0.035, breaks +0.093). The two cancel in total points. This is role 03's "more return-friendly
  conditions", now measured after the opponent.
* **Elo is a good enough strength for the level translation, not the best per-match one** (Observed, `counter_skill.csv`).
  For points and games, Elo explains about as much of the per-match variation as the opponent's own running
  counter-statistic, and less than Stage 3's ratings (men's serve points: partial R² 0.079, 0.071, 0.151). For aces and
  the defence statistics the opponent's own statistic explains 3–20 times more (aces faced: 0.386 against 0.037).
* **Serve speed depends on the opponent a little** (Observed, `speed_checks.json`): +0.29 km/h per 100 Elo [+0.22,
  +0.35] (+0.30 with round and event level held fixed). That is 0.7 km/h at the typical lower-level gap: 0.075
  between-player SD, but 3.6 times stage 2's materiality line, so OPP by the fixed rule. **No level problem is shown:**
  the same player's centred Challenger speed minus his main-tour speed is +1.0 [−1.0, +3.0] km/h (69 player-seasons;
  unresolved, P(reads high) 0.84). **Verdict:** no translation and no level guard for speed, because stage 2's edition
  centring already removes each edition's average opponent. The open risk is the 2026 dose (940 Challenger rows, 15% of
  men's speed rows, against 89–167 a season in the fitting seasons), and that is a data question.
* **γ is stable for men and drifts for some women's statistics** (Observed, `gamma_robust.csv`, `gamma_by_season.csv`).
  The men's points statistics move by at most 0.007 between 2013–18 and 2019–24. Women's return and defence statistics
  move more (return points against the first serve −0.087 → −0.114). **2010 is unusable:** Elo's burn-in halves γ there,
  so `gamma()` starts in 2011.
* **Delivered:** `classify.gamma(through, ...)`, the walk-forward function role B calls. It takes 8.4 s on the first call
  and 1.8 s after. Its strength source is role A's checked copy of the reference's pre-match Elo. Also `classes.csv`
  with its sha256, and 12 tests (`test/lower_level_evidence/test_classify.py`).

## 1. The method

**Per base statistic s and tour** (`src/eda/lower_level_evidence/classify.py`, `fit_gamma`, `fe_wls`):
* **The value:** y = logit((x + ½)/(d + 1)) per box-score player-match. It is log for break points faced per service
  game. This is the builders' scale (`ufc_ideas/stageB_common.py`: `stat_arrays`, `to_scale`).
* **x and d:** the builders' definitions (`predictability_diagnostic/stage4_features.py:314-345`):
  * own rates `<s>_n / <s>_d` from Stage 0's player rows;
  * return points against each serve from the opponent's first- and second-serve counts;
  * **the defence statistics** (the `formdef_*` and `iosD_*` side: what servers do against this player) from the
    opponent's own row. Here the "opponent" in the regression is the server.
* **Rows:**
  * main-tour main draws (bucket MAIN), completed, standard format, with a box score and units > 0;
  * seasons 2013–2024, events before 30 Dec 2024;
  * 58,154 men's and 52,352 women's player-matches (holds, breaks and break points per game: 58,136 and 42,476;
    women's service-game counts start in 2015).
* **Strength:** the opponent's pre-match overall Elo (Stage 1, retirements counted), from every level's results. It is
  the frozen reference's `elo_overall`:
  * checked, ln10/400 × (R_A − R_B) equals the frame's `in_elo_overall` on all 67,226 matches (max difference 1.4e-6
    log-odds, float32 rounding; `strength_elo.json`);
  * copied into `classes/strength_elo.parquet`, so the system does not depend on the first run's sandbox.
* **The model:** y = γ · opponent Elo/100 + surface + a fixed effect per player × season, weighted by the units d.
  * Exact within transformation. CR1 sandwich clustered by player.
  * The partial R² is the share of the within-player-season variance that the opponent adds after the fixed effects
    and surface.
* **A check of the machinery on results** (Observed, `results_check.csv`). Inside the main tour, a player's chance of
  winning falls by 0.113 (men) / 0.122 (women) per 100 Elo of the opponent. Elo's own expectation, fitted the same way,
  falls by 0.109 / 0.113. So Elo's scale holds inside the main tour to within 4% (men) and 8% (women), and the
  fixed-effect regression recovers it.

## 2. The list: 58 inputs and `spd_L`, by base statistic, side and family

*Observed* (builders from [01](../team/01_lineage.md)'s master table; the mapping is `classify.INPUTS`):

| Inputs | Base statistic(s) | Side | Family |
|---|---|---|---|
| `points_52w` | serve points won + return points won (raw 52-week rates) | serve + return | raw rates |
| `adjperf_tpw_2w` | total points won | none | one-step forms |
| `form_ace`, `form_df`, `form_first_in`, `form_first_won`, `form_second_won`, `form_hold`, `form_bp_saved`, `form_bp_faced_pg` | the statistic of the same name | serve | one-step forms |
| `form_brk`, `form_bp_conv`, `form_rpw_first`, `form_rpw_second` | breaks, break points converted, return points against the first and the second serve | return | one-step forms |
| `formdef_ace`, `formdef_df`, `formdef_first_in`, `formdef_bp_faced_pg` | `def_*`: the opponents' aces, double faults, first serves in and break points faced per game, against the player | defence | one-step forms |
| `iosO_<s>` (7) | s: ace, df, first_in, first_won, second_won, hold, bp_saved | serve | joint solves |
| `iosD_ace`, `iosD_df`, `iosD_first_in` | `def_ace`, `def_df`, `def_first_in` | defence | joint solves |
| `iosD_first_won`, `iosD_second_won`, `iosD_hold`, `iosD_bp_saved` | their return mirrors: rpw_first, rpw_second, brk, bp_conv | return | joint solves |
| `prod_<s>` (7) | s and its defence/return mirror | serve + defence/return | joint solves |
| `ios_points_short`, `ratings_iid` | serve points won + return points won | serve + return | joint solve; online point ratings |
| `elo_overall`, `elo_surf_offset`, `elo_games` | results | none | results ratings (RES) |
| `sets_14d`, `surf_season_a/b`, `surf_layoff_a/b` | workload | none | workload (WORK) |
| `age`, `age_sq` | age | none | intrinsic (INTR) |
| `odds_logit`, `tour`, `surface`, `level`, `indoor`, `best_of`, `round` | none | none | market, context (CTX) |
| `spd_L` (stage 2) | first-serve speed | serve | stage 2 |

Counting: 1 + 1 + 8 + 4 + 4 + 7 + 3 + 4 + 7 + 2 + 3 + 5 + 2 + 7 = 58, plus `spd_L`.

## 3. Opponent dependence inside the main tour (γ)

*Observed* (`gamma_main.csv`). γ per 100 Elo [95%]; "per SD" = γ in SDs of the per-match statistic; R² = the
within-player-season share of per-match variance the opponent explains.

| Statistic | Men γ [95%] | per SD | R² | Women γ [95%] | per SD | R² |
|---|---|---:|---:|---|---:|---:|
| Aces | −0.075 [−0.080, −0.070] | −0.08 | 0.030 | −0.054 [−0.060, −0.048] | −0.06 | 0.009 |
| Double faults | −0.012 [−0.016, −0.008] | −0.02 | 0.001 | +0.001 [−0.004, +0.006] | 0.00 | 0.000 |
| **First serves in** | **+0.000 [−0.002, +0.002]** | 0.00 | 0.000 | **−0.002 [−0.004, +0.000]** | −0.01 | 0.000 |
| First-serve points won | −0.071 [−0.073, −0.068] | −0.14 | 0.065 | −0.071 [−0.074, −0.068] | −0.14 | 0.057 |
| Second-serve points won | −0.054 [−0.056, −0.051] | −0.11 | 0.039 | −0.056 [−0.060, −0.053] | −0.11 | 0.032 |
| Serve points won | −0.060 [−0.062, −0.058] | −0.15 | 0.079 | −0.063 [−0.065, −0.060] | −0.16 | 0.071 |
| Holds | −0.146 [−0.151, −0.141] | −0.15 | 0.066 | −0.155 [−0.163, −0.148] | −0.16 | 0.059 |
| Break points saved | −0.055 [−0.059, −0.050] | −0.06 | 0.012 | −0.061 [−0.066, −0.056] | −0.07 | 0.013 |
| Break points faced per game (log) | +0.100 [+0.096, +0.105] | +0.13 | 0.048 | +0.080 [+0.076, +0.085] | +0.13 | 0.037 |
| Return points won | −0.076 [−0.078, −0.074] | −0.19 | 0.119 | −0.082 [−0.084, −0.079] | −0.21 | 0.113 |
| Return points against the first serve | −0.087 [−0.090, −0.084] | −0.17 | 0.086 | −0.099 [−0.102, −0.096] | −0.20 | 0.097 |
| Return points against the second serve | −0.060 [−0.062, −0.057] | −0.13 | 0.047 | −0.062 [−0.065, −0.059] | −0.12 | 0.037 |
| Breaks | −0.186 [−0.192, −0.181] | −0.19 | 0.103 | −0.214 [−0.220, −0.207] | −0.22 | 0.106 |
| Break points converted | −0.072 [−0.076, −0.067] | −0.08 | 0.018 | −0.079 [−0.084, −0.075] | −0.09 | 0.022 |
| **Total points won** | **−0.056 [−0.057, −0.055]** | −0.22 | **0.159** | **−0.069 [−0.071, −0.067]** | −0.23 | **0.144** |
| Aces faced (`def_ace`) | +0.101 [+0.095, +0.107] | +0.11 | 0.037 | +0.154 [+0.147, +0.161] | +0.16 | 0.055 |
| Double faults faced (`def_df`) | −0.038 [−0.043, −0.033] | −0.05 | 0.006 | −0.025 [−0.030, −0.020] | −0.03 | 0.002 |
| First serves in faced (`def_first_in`) | +0.020 [+0.018, +0.022] | +0.06 | 0.009 | +0.005 [+0.002, +0.008] | +0.01 | 0.000 |
| Break points per game forced (`def_bp_faced_pg`, log) | −0.128 [−0.133, −0.123] | −0.17 | 0.077 | −0.107 [−0.111, −0.102] | −0.17 | 0.064 |

* **The owner's example holds** (Observed). How many break points a server gives up depends on the opponent: break
  points faced per game +0.100 log per 100 Elo (+10%), break points saved −0.055.
* **Per match, the opponent explains a modest share; across levels it explains a lot** (Inferred).
  * Per match, R² is at most 16% (total points): most per-match variation is the player's day and coin-flip noise.
  * But the lower levels shift the opponent's strength by about 200 Elo for every match. A per-match effect of 0.06
    logit becomes a systematic 0.12 logit, about 1 to 2 between-player SDs (§5).

**Robustness** (Observed, `gamma_robust.csv`, `gamma_by_season.csv`):
* **Round and event level held fixed:** γ shrinks by 5–10% (men's total points −0.053, serve points −0.057, holds
  −0.138). It is an opponent effect, not a late-round or big-event effect.
* **Fitted inside the Challengers** (men, 117,454 rows): within 10% of the main tour's γ for the points statistics
  (total points −0.062, serve points −0.066, holds −0.156, breaks −0.188). It is smaller for aces (−0.051 against
  −0.075). So the main tour's γ transports to Challenger matches for the points statistics.
* **Eras (2013–18 against 2019–24):**
  * men's points statistics move by at most 0.007 (total points −0.056 / −0.056, serve points −0.060 / −0.059); aces
    faced +0.093 → +0.113; double faults faced −0.049 → −0.023;
  * **women move more:** return points against the first serve −0.087 → −0.114 (difference −0.027, SE 0.003); breaks
    −0.199 → −0.224; aces faced +0.123 → +0.191; first serves in faced +0.019 → −0.013, a sign change. *Inferred:*
    partly the 2019+ data sources; either way γ must be refitted walk-forward, which `gamma()` does.
* **Each season:** men's total points −0.052 to −0.061 in every season 2011–2024, but **−0.031 in 2010**. Stage 1's
  Elo starts everyone at 1500 in January 2010, and the noisy early ratings attenuate γ. `gamma()` therefore starts in
  2011 (method version .2, logged 20:29:53 UTC; early fits had read about 13% low).

**Elo against a statistic-specific counter-skill** (Observed, `counter_skill.csv`).
* **What was compared.** The partial R² inside the player-season of three strengths:
  * the opponent's Elo;
  * his own counter-statistic: his leak-free shrunk rate over the previous 365 days, every level, read on the match
    clock (rows with lf + 1 ≤ es; tested in `test_counter_skill_running_rate_respects_the_clock`);
  * for the points statistics, his Stage 3 serve and return ratings (pre-match, one scale, every level).

| Men (women similar) | Elo | Counter-statistic | Both | Stage 3 | Elo + Stage 3 |
|---|---:|---:|---:|---:|---:|
| Serve points won (counter: his return points won) | 0.079 | 0.071 | 0.134 | 0.151 | 0.152 |
| Return points won (counter: his serve points won) | 0.120 | 0.164 | 0.186 | 0.197 | 0.198 |
| Total points won | 0.159 | 0.088 | 0.162 | 0.168 | 0.170 |
| Holds / breaks | 0.066 / 0.103 | 0.056 / 0.139 | 0.110 / 0.159 | 0.125 / 0.169 | 0.126 / 0.171 |
| Aces (counter: aces he concedes) | 0.030 | 0.073 | 0.109 | | |
| Aces faced (counter: his own aces) | 0.037 | 0.386 | 0.390 | | |
| First serves in faced / double faults faced | 0.009 / 0.006 | 0.200 / 0.136 | 0.200 / 0.136 | | |

* **For points and games, Elo is about as good as the counter-statistic, and Stage 3 is better than both** (Observed).
  Elo adds at most 0.004 beyond Stage 3.
* **For aces and the defence statistics, the opponent's own statistic dominates** (Observed). Aces faced depend on the
  server's aces (0.386), not on his results (0.037). The same holds for women (0.325 against 0.055).
* **For the level translation, Elo does the job** (Inferred). What the translation needs is the level part, and Elo
  explains it as well as Stage 3's one-scale ratings (§4). A raw counter-statistic cannot replace it: it is itself
  level-contaminated (a Challenger regular's "aces conceded" are measured against Challenger servers).
* **Suggestion.** For the defence forms and aces, a one-scale statistic-specific strength (the opponent's IOS rating
  for that statistic, which is level-consistent per role 01) would make the per-match translation sharper. That is the
  red team's "one-scale form" (07, S3). It is a refinement for B and C1 to weigh, not needed for the level part.

## 4. Is the level effect an opponent effect?

**The opponents' gap** (Observed, `level_opponent_gaps.csv`). Same player-season (≥ 3 box scores at both), the mean
opponent Elo at level L minus at the main tour, in Elo points:

| | Tour qualifying | Slam qualifying | Challenger / WTA 125 | Challenger qualifying |
|---|---:|---:|---:|---:|
| Men | −195 (1,443 player-seasons) | −188 (640) | −214 (1,685) | −366 (237) |
| Women | −161 (1,564) | −157 (656) | −131 (740) | −301 (14: not identified) |

* **The decomposition** (`level_decomposition.csv`, `classify.py`: `table_levels`).
  * The raw same-player shift R comes from d-weighted per-match means, averaged over player-seasons.
  * The opponent part is γ × the stat's own gap.
  * The residual is δ = R − γ·gap. Its interval adds γ's uncertainty.
* **Selected statistics, logit** (Observed):

| | Men CH: raw → residual | Men TQ | Men GSQ | Women TQ | Women CH |
|---|---|---|---|---|---|
| **Total points won** | +0.117 → **−0.000 [−0.006, +0.005]** (100% explained) | +0.119 → +0.014 (89%) | +0.131 → +0.026 (80%) | +0.115 → +0.009 (92%) | +0.101 → +0.015 (85%) |
| Serve points won | +0.083 → −0.043 [−0.052, −0.035] (152%) | +0.110 → −0.002 | +0.115 → +0.003 | +0.105 → +0.009 | +0.075 → −0.004 |
| Return points won | +0.194 → +0.035 [+0.025, +0.044] (82%) | +0.170 → +0.027 | +0.194 → +0.053 | +0.135 → +0.010 | +0.135 → +0.033 |
| Holds | +0.199 → −0.108 [−0.130, −0.086] | +0.268 → −0.008 | +0.310 → +0.034 | +0.258 → +0.020 | +0.171 → −0.022 |
| Breaks | +0.487 → +0.093 [+0.069, +0.118] | +0.435 → +0.081 | +0.502 → +0.148 | +0.340 → +0.013 | +0.350 → +0.085 |
| Aces | +0.039 → −0.118 [−0.140, −0.097] | +0.094 → −0.047 | +0.096 → −0.044 | +0.125 → +0.043 | +0.006 → −0.062 |
| Aces faced | −0.342 → −0.130 | −0.254 → −0.064 | −0.299 → −0.111 | −0.182 → +0.054 | −0.245 → −0.052 |
| First serves in (ENV) | −0.008 (raw) | +0.006 | +0.035 | −0.012 | +0.017 |

* **For total points won, the level effect is almost wholly an opponent effect** (Observed). Men's Challengers: 100%;
  qualifying: 80–89%. Women: 77–92%.
* **The same holds with a statistic-specific strength on one scale** (Observed, `level_decomposition_stage3.csv`). With
  Stage 3's opponent ratings instead of Elo, total points won is explained 95% (men, CH), 84% (TQ), 78% (GSQ), and
  78–83% for women.
* **What is left is a serve–return balance** (Observed, men's Challengers):
  * serve statistics sit below what the weaker returners imply (serve points −0.043, holds −0.108, aces −0.118);
  * return statistics sit above (return points +0.035, breaks +0.093);
  * they cancel in total points.
  * *Inferred:* conditions (slower courts and balls, fewer aces) and role 03's level effects in the joint solve (serve
    points −0.6 per 100 at Challengers in 2019–24) are the same thing seen two ways.
* **Slam qualifying keeps a positive residual on both sides** (men's total points +0.026, breaks +0.148; women's holds
  +0.106) (Observed). *Inferred:* selection. A Slam-qualifying run is the best-of-season moment of players who do not
  usually reach main draws, and the same-season design rewards it (role 03, §6).
* **Challenger qualifying** (men, 237 player-seasons): the opponents are 366 Elo weaker; total points +0.185 → −0.014.
  Women's (14 player-seasons) is not identified.

## 5. The thresholds and the classes

**Fixed before any γ was computed** (`classes/thresholds.json`, sha256 `d8eb62d2…`; status log 20:12:50 UTC; the file's
time field was corrected to the logged time at 20:12:58, before any computation, and its content did not change):
* **Yardstick: SD_signal,** the between-player-season SD of the statistic's true value on the main tour (the variance
  of player-season means minus their sampling variance; ≥ 5 box scores).
  * Why not the per-match SD: it is dominated by coin-flip noise for low-count statistics (about 5 break points a
    match), so a per-match threshold would call a large systematic bias immaterial for exactly the noisiest statistics.
  * The inputs aggregate many matches, so a bias that does not average out is judged against the spread of players'
    true values. Per-match SD units are reported beside (§3).
* **The reference gap** per tour: the box-score-volume-weighted mean |gap| over TQ, GSQ, CH and CHQ (men 245 Elo,
  women 159). It is computed from Elo only.
* **OPP:** γ's interval excludes 0 AND |γ| × reference gap ≥ 0.10 SD_signal. Otherwise ENV.
  * Why 0.10: a player whose evidence is wholly lower-level moves about 4 percentile points at the median.
  * The average main-tour player row (23–35% lower-level evidence, role 01) moves 0.03 SD; a qualifier's (about 75%)
    0.075 SD. That is the scale at which role 08's translated inputs moved the model measurably but little.
* **δ "real" at level L:** at least 100 qualifying player-seasons, AND the shift left after the class's translation
  clears 0, AND it reaches 0.10 SD_signal. The shift left is the residual for OPP and the raw shift for ENV.
* **Speed:** the scale is stage 2's own: 0.10 × `spd_L`'s standardiser = 0.195 km/h.

**The base statistics** (Observed, `stat_classes_detail.csv`; "opp. part" = |γ| × reference gap in SD_signal; δ levels =
where the residual is real):

| Statistic | Men: class (opp. part); δ levels | Women: class (opp. part); δ levels |
|---|---|---|
| Aces | OPP (0.33); CH, CHQ | OPP (0.12, borderline); none |
| Double faults | ENV (0.09, borderline); CH | ENV (0.00); GSQ |
| First serves in | ENV (0.00); GSQ, CHQ | ENV (0.01); GSQ |
| First-serve points won | OPP (0.81); CH, CHQ | OPP (0.60); GSQ |
| Second-serve points won | OPP (1.27); CH | OPP (0.82); GSQ |
| Serve points won | OPP (1.04); CH, CHQ | OPP (0.81); GSQ |
| Holds | OPP (1.00); CH, CHQ | OPP (0.79); GSQ |
| Break points saved | OPP (0.95); none | OPP (0.74); none |
| Break points faced per game | OPP (1.14); CH, CHQ | OPP (0.90); GSQ |
| Return points won | OPP (1.57); TQ, GSQ, CH | OPP (1.31); GSQ, CH |
| Return points v first serve | OPP (1.49); TQ, GSQ, CH, CHQ | OPP (1.22); GSQ, CH |
| Return points v second serve | OPP (1.33); TQ, GSQ, CH | OPP (1.08); TQ, GSQ, CH |
| Breaks | OPP (1.51); TQ, GSQ, CH | OPP (1.39); CH |
| Break points converted | OPP (1.66); TQ, GSQ | OPP (1.36); GSQ, CH |
| Total points won | OPP (2.09); TQ, GSQ | OPP (1.44); TQ, GSQ, CH |
| Aces faced | OPP (0.76); all four | OPP (0.61); TQ, GSQ, CH |
| Double faults faced | OPP (0.59); none | OPP (0.28); TQ, GSQ, CH |
| First serves in faced | OPP (0.65); all four | ENV (0.095, borderline); TQ, GSQ, CH |
| Break points per game forced | OPP (1.56); GSQ, CH | OPP (1.24); CH |
| Results (Elo) | RES | RES |
| Age | INTR | INTR |
| Workload | WORK | WORK |
| First-serve speed | OPP by the speed rule, untouched (§6) | not used (no women's speeds in stage 2) |

**The rule each input gets** (Observed, `classes.csv`, column `rule`):
* **Translate with γ (and δ at the real levels), weight w.**
  * Men, 16 inputs: `points_52w`, `adjperf_tpw_2w`, `form_ace`, `form_first_won`, `form_second_won`, `form_hold`,
    `form_bp_saved`, `form_bp_faced_pg`, `form_brk`, `form_bp_conv`, `form_rpw_first`, `form_rpw_second`, and the four
    `formdef_*`.
  * Women, 15: the same without `formdef_first_in`.
* **δ only, weight w:** `form_df` (men CH; women GSQ), `form_first_in` (men GSQ, CHQ; women GSQ), and women's
  `formdef_first_in` (TQ, GSQ, CH).
* **Joint solves** (14 `ios*`, 7 `prod_*`, `ios_points_short`, `ratings_iid`): the solve handles the opponent, so there
  is no γ term. A level term is allowed only at the levels where δ is real for the input's statistics; weights w.
  * The δ measured here is a residual after Elo, not after the solve. B and C2 fit the solve's own level term. The class
    says only where it is allowed.
  * No level term at all for `iosO_bp_saved` (both tours), men's `iosD_df` and women's `iosO_ace`.
* **RES** (`elo_overall`, `elo_surf_offset`, `elo_games`): w_results only.
* **Untouched:** INTR (`age`, `age_sq`), WORK (`sets_14d`, the four surface pairs), CTX (`odds_logit` and the six
  context inputs), and `spd_L`.
* **Multi-statistic inputs** are OPP if any of their statistics is. `side` reads "serve+return" or "serve+defence",
  beyond the SPEC's four values.

## 6. Serve speed (stage 2)

*Observed* (`speed_checks.json`; men; `live_panel.frozen_panel()`; rows of events before 30 Dec 2024 only;
`panel.EditionOffsets` with its frozen constants):
* **The gradient on the opponent inside the main tour** (16,500 player-matches of 2013–2024, player × season fixed
  effects, surface and basis held fixed):

  | Speed | γ (km/h per 100 Elo) [95%] | Partial R² |
  |---|---|---:|
  | Raw | +0.34 [+0.27, +0.41] | 0.009 |
  | Edition-centred (stage 2's offsets at each season's end) | +0.29 [+0.22, +0.35] | 0.007 |
  | Centred, with event level and round also held fixed | +0.30 [+0.23, +0.38] | 0.005 |

  * Players serve slightly faster against stronger opponents. At the men's reference gap (245 Elo) that is 0.70 km/h.
  * That is 0.075 of the between-player-season SD (9.4 km/h), below the box-score line.
  * But it is 3.6 times the speed line fixed for stage 2 (0.195 km/h), so the class is **OPP by the fixed rule**.
  * The owner's "not really dependent" is right in size, not in sign.
* **The same player at Challengers and on the main tour** (same season):

  | | Player-seasons | Raw CH − main | Centred CH − main | Opponents' Elo gap |
  |---|---:|---|---|---|
  | ≥ 1 row at each | 69 (61 players) | +1.3 [−0.9, +3.4] km/h | **+1.0 [−1.0, +3.0], P(reads high) 0.84** | −216 |
  | ≥ 2 rows at each | 34 | −0.1 [−3.4, +3.3] | −0.8 [−3.8, +2.2] | −235 |

  * Only 353 usable Challenger speed rows exist before the holdout: 167 (2022), 92, 94.
  * Challenger editions' offsets average −1.9 km/h, main-tour editions' −1.1 km/h.
* **Reading it** (Inferred).
  * Stage 2 centres every speed on its edition (y = α_player + γ_edition, shrunk to the edition's family: `panel.py`,
    `EditionOffsets.fit`). An edition's offset therefore absorbs the average strength of its opponents, which is exactly
    the part that differs by level.
  * Translating speed by γ on top would count it twice. So: **no γ on speed.**
  * Whether anything is left after the centring is unresolved. The point estimate leans toward the lead's hypothesis
    (centred Challenger speeds read high, P 0.84). But the test cannot see a shift under about 2 km/h, which is a
    whole `spd_L` unit.
* **Verdict: stage 2 needs no level guard on this evidence** (the fixed rule: no shift with an interval clearing 0).
* **Suggestion.** The open risk is the dose, not the level.
  * My count of usable Challenger rows: 940 in 2026 (15% of the men's rows), against 167, 92, 94 and 89 in 2022–2025
    (2–4%), the seasons b̃ was fitted on. The red team counts 945 on its own filter.
  * If centred Challenger speeds do read 1 km/h high, a Challenger-active man's `spd_L` moves by up to half a unit, in
    2026 only.
  * The red team's guard (07, S8) stays the prudent option: hold Challenger rows to the fitting seasons' dose, or put
    the speed panel behind the history check.
  * It changes only 2025–26 rows, so it is a data-fix call for the owner, not something a 2020–24 score can judge.

## 7. `classify.gamma` for role B

* **The signature:**
  `gamma(through, tours=("atp","wta"), stats=None, start="2011-01-01", stage0_dir, timing, strength_path,
  allow_holdout=False)`.
  * It uses the rows with lf + 1 ≤ through (the match clock), from `start`.
  * It returns per (tour, stat): γ, se, interval, unit, counts, partial R², `last_result_day` and the method version.
  * `season_cutoff(Y)` gives the earliest possible start of season Y's first main-tour match.
* **Details:** `classes/READY_gamma.txt`.
* **The holdout guard.** It refuses any 2025–26 outcome unless `allow_holdout=True` (the SPEC's mechanical fits).
  * `through=2024-12-30` is already refused: 9 main-draw matches of season-2025 events were played on 29 Dec 2024.
  * `season_cutoff(2025)` = 29 Dec 2024 reads none (tested on the frozen Stage 0).
* **For the earliest histories** (Inferred). Lower-level observations of 2010–2011, in the histories of 2013 inputs,
  have no walk-forward γ. The first clean fit (through 2012) is the natural fallback; that is B's call.

## 8. Tests

`./python.sh -m pytest test/lower_level_evidence/test_classify.py -q`: **12 passed** (10 s). They check:
* **a planted γ** (−0.06 per 100 Elo, on a synthetic Stage 0 with assortative pairing) is recovered through the whole
  `gamma()` path, and a planted zero reads zero;
* **the fixed effects** equal an explicit dummy regression (the coefficient to 1e-10, the clustered SE to 1e-6). They
  are per player × season, and a pooled regression is biased where the within one is not;
* **the holdout:**
  * `gamma()` refuses 2025 outcomes without the flag;
  * the filtered read never requests a holdout match (spied);
  * `player_rows` asserts;
  * on the frozen Stage 0, the 2025 cutoff reads no holdout row and the 2026 cutoff is refused;
* **the clock:**
  * reversing every outcome not in by the cut leaves γ unchanged to 1e-12, and reversing earlier ones moves it (the
    leaky control);
  * the counter-skill's running rates pass the same cut-and-reverse probe and equal a brute-force sum;
  * `season_cutoff` is the first earliest start;
* **the class rule** applies `thresholds.json` as written.

`gamma()` is a batch fit across players. Its clock behaviour is tested by the cut-and-reverse probe above, in the spirit
of `match_timing/probe.py`, which is built for the IOS inputs.

## 9. For the lead and the other roles

1. **Joint solves (C2, B).** My δ is the residual after Elo's γ, not after the solve's own opponent adjustment. The
   class only says where a solve's level term is allowed. Its size must be fitted in the solve's units.
2. **The aces.** γ inside the Challengers is two-thirds of the main tour's (−0.051 against −0.075). The main-tour γ
   over-explains the aces' level shift, and δ_CH (−0.118) absorbs the difference. B should fit δ with γ fixed, or the
   two will trade off.
3. **Women's γ drifts** (return and defence statistics). Walk-forward γ per season is required, not a pooled value.
4. **Borderline calls** (within 20% of the line): men's double faults (ENV), women's first serves in faced (ENV) and
   women's aces (OPP). SYS_NOCLASS already tests the classes as a whole.
5. **Speed's guard** is a data-fix decision for the owner (§6), outside the SPEC's arms.
6. **`side`** takes "serve+return" and "serve+defence" for multi-statistic inputs, beyond the SPEC's four values.

## Files

| What | Where |
|---|---|
| Code (CLI `--strength`, `--demo`, `--analysis`; about 100 s) | `src/eda/lower_level_evidence/classify.py` |
| Tests (12) | `test/lower_level_evidence/test_classify.py` |
| The thresholds, fixed first; their hash | `classes/thresholds.json`, `classes/thresholds.sha256` |
| The class table; its hash | `classes/classes.csv`, `classes/classes.sha256` |
| Per-statistic detail (γ, SD_signal, opponent part, residuals with intervals, δ flags) | `classes/stat_classes_detail.csv` |
| γ table; robustness; each season; results check | `classes/gamma_main.csv`, `gamma_robust.csv`, `gamma_by_season.csv`, `results_check.csv` |
| Counter-skill comparison | `classes/counter_skill.csv` |
| Level decomposition (Elo; Stage 3); opponents' gaps | `classes/level_decomposition.csv`, `level_decomposition_stage3.csv`, `level_opponent_gaps.csv` |
| Speed checks and verdict | `classes/speed_checks.json` |
| Strength copy and its check | `classes/strength_elo.parquet`, `classes/strength_elo.json` |
| Hand-offs | `classes/READY_gamma.txt`, `classes/READY_classes.txt` |
| Run record (sources' hashes, counts, timings) | `classes/run.json` |

**Inputs read:**
* the frozen Stage 0 and timeline (`common.py`);
* the frozen frame (the Elo check only);
* the first run's sandbox `C:/Users/zerom/tnr_lle/data/studies/predictability_diagnostic/stage1_baselines.parquet` and
  `stage3_ratings.parquet`, read only (hashes in `run.json`);
* the live speed panel through `live_panel.frozen_panel()`.

## What it does not show

* **No model-level effect.** These are statistic-level measurements. Whether the classes help the model is D's
  SYS-against-SYS_NOCLASS reading.
* **Causality inside the main tour.** γ is a within-player-season association with the opponent's Elo. Round, event
  level and surface are held fixed (γ moves 5–10%), but tactics or scheduling tied to the opponent are in it. For
  translation that is what is wanted: the expected statistic given the opponent's Elo.
* **The level residuals carry selection.** The same-season design compares seasons in which a player played both
  levels, which results partly decide (role 03, §6). Slam qualifying's positive residuals are the likeliest case. The
  forecasting fits are B's.
* **ITF.** There are no ITF box scores before 2025, so nothing here classifies or decomposes the ITF levels.
* **Speed's level question is underpowered.** 69 player-seasons cannot see a shift under about 2 km/h.
* **The variance shares are per match.** R² ignores how much of the per-match variance is coin-flip noise. A
  noise-corrected share was computed and dropped: its delta-method noise is unreliable for low-count statistics (it
  read 0.99 for men's holds).
* **Women's Challenger qualifying** (14 player-seasons) is not identified. Every women's CHQ cell is "not identified",
  and δ is not allowed there.
