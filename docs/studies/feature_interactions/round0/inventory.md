# Round 0: the data map (inventory)

6 October 2026 · Data cartographer (later the feasibility auditor) of the [feature-interactions study](../brief.md). Research evidence, not a decision.

**What this is.** Where every quantity an interaction idea could need lives, whether each player's own value exists or only the A − B difference, its timing class, and how much of the model population has it. Section 3 is the register of what earlier studies already tried.

**Labels.** *Observed* = measured here by a script in `src/eda/feature_interactions/inventory/` (outputs in `data/studies/feature_interactions/inventory/`). *Code* = read from the builder's source. *Doc* = taken from a study report, cited. *Inferred* = my reading. *Suggestion* = a proposal.

**Coverage notation.** Four shares, always in this order: **men 2013–21 / women 2013–21 / men 2022–24 / women 2022–24**, in percent of the model population's matches where the value exists (for per-player values: for **both** players). The population is the frozen model frame (`data/studies/surface_rating_race/model/model_frame.parquet`) restricted to seasons up to 2024: 19,331 / 20,587 / 7,958 / 7,268 matches (the men's 2018 season has no odds and is absent). **No 2025–2026 row was used for anything but counting.**

**Machine-readable companion.** [`data/studies/feature_interactions/inventory.csv`](../../../../data/studies/feature_interactions/inventory.csv): one row per feature or raw field (about 1,640 rows), with path, columns, per-player availability, kind, timing class, the four coverages (as shares 0–1; rows whose name says "share" hold a share of matches, not a coverage), in-model flag and notes. All coverages of all columns of every feature table are in `data/studies/feature_interactions/inventory/coverage_all.csv`.

## 0. The facts that matter most for designing interactions

1. **Side A is Stage 0's `player_a_id`, everywhere.** *Observed:* the model frame's A agrees with the pre-rebuild Stage 0 on the result, the market probability, age, Elo and all 21 surface-IOS inputs, value for value; every per-player table with `_a`/`_b` columns or `side` rows uses the same A (§5).
2. **Each player's own value is on disk, or now rebuilt, for 48 of the 51 player inputs** (the other 6 inputs are match context, plus the odds).
   * Stored per player: the long-memory surface IOS profile (`surface_ios/surface_features.parquet`, `srf_O_eff_<s>_a/_b`, `srf_D_eff_<s>_a/_b`), overall Elo and the surface offset (`surface_elo_pieces/pieces.parquet` `R_*`, `D_*`), the surface-switch pairs, the Stage 3 serve/return ratings behind `ratings_iid` (`stage3_ratings.parquet`), age.
   * **Rebuilt here and verified exact** (A − B reproduces the model input to < 1e-7): the whole two-week profile (12 `form_*`, 4 `formdef_*`, `adjperf_tpw_2w`) and `sets_14d`, per player, 2013–2024: [`perplayer_form_2013_2024.parquet`](../../../../data/studies/feature_interactions/inventory/perplayer_form_2013_2024.parquet), [`perplayer_load_2013_2024.parquet`](../../../../data/studies/feature_interactions/inventory/perplayer_load_2013_2024.parquet).
   * **Only the difference exists** for `elo_games`, `points_52w` and `ios_points_short`; each can be rebuilt per player from code paths named in §1.3 (minutes of compute).
3. **Sums, levels and own-player products are therefore buildable without new data**: A's serve against B's return separately from the reverse, the sum of both players' serve strength, one player's age × the same player's load, reliability of each player's estimate (Stage 3 `sd_*`, `serve_pts_*`; TTT `s2`; Glicko `u`; Elo counts `N`, `NS`).
4. **Raw data not yet used** with good coverage before 2022: hand (98–100%), height (men 100%, women 94% then 64% in 2022–24), country (100%), **one- or two-handed backhand for men** (TML, joined here: 95% of men's matches), rank and points (99.5%+), seed and entry type, score strings (tiebreaks, deciding sets, comebacks, retirements: 100%), draw size, **indoor for women from tennis-data.co.uk's `Court` (100%)**, city (`Location`), Pinnacle / best price / Bet365 closes (99.5%+), the match clock (rest before a match: 100%), start times (men 99%, women 75% then 100%). Point-by-point data with shot detail is thin before 2022 (men 26%, women 23%) and only men's is rich after (90%); serve speed 12–15% before 2022. **A point-sequence table being built today by another session** (server and winner of every point, `data/studies/point_sequence/`) reports far higher coverage (men 88%, women 61% in 2013–21; 95% and 99% in 2022–24): the key resource for point → game → set composition ideas, still mid-build (§4.6).
5. **Data holes that shape interaction tests**: women's service-game counts (hold, breaks, break points per game) are missing in 2013–14 and partly 2015 (the model's women's `form_hold/brk/bp_faced_pg` cover 74%); women's minutes are missing 2013–15; men's 2015 minutes 52%; Betfair exchange odds exist only in 2025–26 (closed); per-book quotes other than Pinnacle, Bet365, Max and Avg stop in 2018.
6. **Leaking tables must not feed new features as they are**: weekly IOS (`ufc_ideas/stageB_ios*`), `ttt_pass` (TTT in `rating_systems/stageA_ratings`), Bradley–Terry and MESR (`ufc_ideas/stageA_*`), the SOS revaluation (`ufc_ideas/stageC_sos_part`). Their leak-proof replacements are named in §2.
7. **Shared tables were rebuilt today.** The Stage 0 rebuild (17:05–17:35, `ok: true`) changed nothing on the 2013–2024 model matches except 7 minute values, but changed 38 history matches' player ids and the tiebreak/game counts of 7,597 player rows; it re-keyed 40 women's 2026 model matches and flipped side A in 21 of them. **For consistency with the frozen model frame, read the pre-rebuild copies** (§5.4).

## 1. (a) The 58 model inputs

Kinds: **diff** = A − B, negated when A and B swap; **pair** = an (A, B) couple, exchanged when they swap; **context** = unchanged. Timing: **safe** = follows each player's own matches in order (safe by construction); **clock** = solved together, built on the leak-proof clock. Upstream tables are under `data/studies/`.

### 1.1 The inputs, their sources and where A and B live

| Input(s) | Definition | Kind | Upstream (table: column) | A's and B's values separately | Timing | Coverage % |
|---|---|---|---|---|---|---|
| `odds_logit` | log-odds that A wins, average closing odds of tennis-data.co.uk de-vigged by normalising 1/odds (pairs with overround outside 1.00–1.20 dropped) | diff | `predictability_diagnostic/stage1_odds.parquet: p_avg_a` (= frame `p_mkt`, = `stage1_baselines.p_market`) | each side's price: `avg_a/avg_b`, also `ps_*` (Pinnacle), `max_*`, `b365_*`, `overround_*` | market | 100 / 100 / 100 / 100 |
| `ratings_iid` | log-odds of the iid point model's match probability from Stage 3's serve and return ratings: p_serve_A = expit(mu + serve_A − return_B), p_serve_B alike, combined under the scheduled format and deciding-set rule | diff | `predictability_diagnostic/stage4_features.parquet: rating_matchup\|single` (via `ufc_ideas/stageD_features`) | **yes**: `stage3_ratings.parquet` `serve_a/b`, `return_a/b`, `sd_serve_*`, `sd_return_*`, `serve_pts_*`, `return_pts_*`, `mu_logit`, `p_serve_a/b` | safe | 100 / 100 / 100 / 100 |
| `elo_games` | games-weighted Elo (each update × the winner's games share / a scale; Angelini et al. 2022), overall and surface blended as Stage 1, log-odds | diff | `stage4_features.parquet: elo_games\|single` | **no** (code: `stage4_features.weighted_elo_pass` returns each match's R_A, R_B, N_A, N_B and the surface ones before the blend) | safe | 100 / 100 / 100 / 100 |
| `adjperf_tpw_2w` | opponent-adjusted total points won: decayed (half-life 2 weeks) mean of per-match z, shrunk with K3 = 10 men / 20 women | diff | `ufc_ideas/stageD_features.parquet: adjperf_tpw\|decayed` | **yes, rebuilt here** (`perplayer_form_2013_2024.parquet`) | safe | 99.9 / 98.9 / 99.9 / 99.8 |
| `ios_points_short` | IOS on serve points won with a short memory (half-life 4 weeks men, 13 women), the points matchup through the iid model, log-odds | diff | `match_timing/leakproof_features.parquet: ios_short` (pre-rebuild copy; equal value for value) | **no** (code: `match_timing/rebuild.ios_features` keeps `O[('spw','short')]`, `D[...]` per player row before `matchup_points`) | clock | 100 / 100 / 100 / 100 |
| `points_52w` | A's serve points won over 52 weeks (shrunk to the tour-surface mean with Stage 3's K) against B's return points won, and the reverse, through the iid model, log-odds | diff | `stage4_features.parquet: mu_points\|52 weeks` | **no** (code: `match_timing/rebuild.points_52w` holds `val['spw']`, `val['rpw']` per row; it runs on repaired rows and equals the input on 95% of matches) | safe | 99.7 / 98.2 / 99.8 / 99.3 |
| `sets_14d` | log(1 + sets played in matches of events that started in the 14 days before this event, plus this event's earlier rounds); missing if a played match in the window has no set total | diff | `stage4_features.parquet: sets_14d\|single` | **yes, rebuilt here** (`perplayer_load_2013_2024.parquet`) | safe | 100 / 100 / 100 / 99.5 |
| `age`, `age_sq` | age_A − age_B; (age_A − 25)² − (age_B − 25)² (ages outside 14–50 missing) | diff | `stage4_features.parquet: age\|single`, `age\|single\|2` | **yes**: `stage0_match_players.age` | safe | 100 / 100 / 100 / 100 |
| `form_<s>` for ace, df, first_in, first_won, second_won, bp_saved | adjperf of s: decayed (2 weeks) mean of the player's per-match z = (own value − what the opponent usually allows) / opponent's MAD, clipped ±4, shrunk toward 0 with K3 = 10 men / 20 women | diff | `ufc_ideas/stageD_profile_features.parquet: adjperf_<s>\|decayed` (built by `ufc_ideas/stageB_adjperf.py`) | **yes, rebuilt here** | safe | 99.9 / 98.9 / 99.9 / 99.8 |
| `form_hold`, `form_bp_faced_pg` | the same, on service games held and break points faced per service game | diff | as above | **yes, rebuilt here** | safe | 99.9 / **74.1** / 99.9 / 99.8 |
| `form_brk` | the same, on return games won (return skill: K3 = 160, values ~10× smaller) | diff | as above | **yes, rebuilt here** | safe | 99.9 / **74.1** / 99.9 / 99.8 |
| `form_bp_conv`, `form_rpw_first`, `form_rpw_second` | the same, return side (K3 = 160) | diff | as above | **yes, rebuilt here** | safe | 99.9 / 98.9 / 99.9 / 99.8 |
| `formdef_<s>` for ace, df, first_in | adjdef of s: decayed (2 weeks) mean of how far the player held opponents below their own norm on s (a return skill; K3 = 160) | diff | `stageD_profile_features.parquet: adjdef_<s>\|decayed` | **yes, rebuilt here** | safe | 99.9 / 98.9 / 99.9 / 99.8 |
| `formdef_bp_faced_pg` | the same on break points faced per game | diff | as above | **yes, rebuilt here** | safe | 99.9 / **74.1** / 99.9 / 99.8 |
| `iosO_<s>` (7 stats: ace, df, first_in, first_won, second_won, hold, bp_saved) | surface IOS offence on s, effective on the match's surface: O + E_surface from a ridge-regularised joint solve of all players' offence/defence with surface deviations, read at the match's earliest possible start | diff | `surface_ios/arms/sprof.parquet in_iosO_<s>` = `surface_ios/surface_features.parquet: srf_O_eff_<s>_a − srf_O_eff_<s>_b` | **yes**: `srf_O_eff_<s>_a/_b`; also the pooled `cur_O_<s>_*`, all-surface `srf_O_<s>_*`, surface deviation `srf_E_<s>_*` | clock | 100 / 100 / 100 / 100 |
| `iosD_<s>` (7) | surface IOS defence on s: how much the player suppresses the server's s, D + F_surface | diff | `surface_features.parquet: srf_D_eff_<s>_a − srf_D_eff_<s>_b` | **yes**: `srf_D_eff_<s>_a/_b`, `cur_D_*`, `srf_D_*`, `srf_F_*` | clock | 100 / 100 / 100 / 100 |
| `prod_<s>` (7) | O_A × (−D_B) − O_B × (−D_A) on the surface-effective values: the only cross-player products the model has | diff | from the same per-player columns | **yes** (both factors) | clock | 100 / 100 / 100 / 100 |
| `tour`, `surface`, `level`, `best_of`, `round` | 0 men / 1 women; 0 hard, 1 clay, 2 grass, 3 carpet; 0 Slam, 1 Finals, 2 1000, 3 500, 4 250; scheduled best of (men's Slam main draws 5); Stage 0 `round_order` (Q1 = 1 … RR = 10, R128 = 11 … F = 17) | context | `tabpfn_thinking/frame.parquet x_<name>` from `stage0_matches` | n/a | context | 100 / 100 / 100 / 100 |
| `indoor` | 1 indoor / 0 outdoor from Stage 0 | context | as above | n/a | context | 100 / **0** / 100 / **0** (men only) |
| `elo_overall` | Stage 1's overall Elo (retirements counted), (R_A − R_B) ln10/400 | diff | `surface_elo_pieces/pieces.parquet: R_a, R_b` | **yes**: `R_*`, counts `N_*`; also `stage1_baselines.parquet elo_a_ret/elo_b_ret` | safe | 100 / 100 / 100 / 100 |
| `elo_surf_offset` | surface offset: (D_A − D_B) ln10/400; D starts at 0 and moves only on this surface by the surprise of R + D (K tuned 2013–18) | diff | `pieces.parquet: D_a, D_b` (missing read as 0) | **yes**: `D_*`, surface counts `NS_*`, surface-only `S_*`, anchored `XA_*`, surface-blind control `DG_*` | safe | 100 / 100 / 100 / 100 |
| `surf_season_a`, `surf_season_b` | log(1 + the player's played matches on this surface earlier this calendar season) | pair | `pieces.parquet: season_n_a/_b` | per player by construction | safe | 100 / 100 / 100 / 100 |
| `surf_layoff_a`, `surf_layoff_b` | log(1 + days since the player's last match on this surface) on the clock's best-estimate days (`obs`), capped at 1,095 | pair | `pieces.parquet: days_since_a/_b` | per player by construction | safe | 100 / 100 / 100 / 100 |

*Code/doc sources:* `src/eda/tabpfn_thinking/common.py` (FEATURES), `src/eda/tabpfn_leakproof/common.py` (REPLACED), `src/eda/surface_elo_pieces/arms.py`, `src/eda/surface_rating_race/arms.py` and `model_frame.py`, `src/eda/surface_ios/arms.py` (recipe), `src/eda/ufc_ideas/stageB_adjperf.py` (constants in `data/studies/ufc_ideas/stageB_adj_summary.json`, key `used`).

### 1.2 What was verified, and how (observed)

| Check (2013–2024 model rows) | Result | Script / output |
|---|---|---|
| model `a_won`, `p_mkt`, `in_odds_logit` against pre-rebuild Stage 0 / Stage 1 odds | identical on all 55,144 | `orientation.py` / `orientation.json` |
| `in_age`, `in_age_sq` against Stage 0's per-player ages (side A minus side B) | equal to float precision, same missing pattern | same |
| `in_elo_overall`, `in_elo_surf_offset`, `in_surf_season_a` against `pieces.parquet` | identical | same |
| all 21 `in_iosO/iosD/prod_*` against `surface_features.parquet` `_a/_b` | identical | same |
| `in_ratings_iid` against the iid model (`stage2_iid.match_win_by`, deciding set TB7@6) on `stage3_ratings` `p_serve_a/_b` | identical to 1e-5 on 99.96–100% of non-Slam matches; Slams differ by their deciding-set rule | ad hoc check (recorded here) |
| 17 two-week profile inputs rebuilt per player from `ufc_ideas/stageB_adj.parquet` | max gap 7e-8, missing pattern identical | `perplayer_form.py` / `perplayer_form_check.json` |
| `sets_14d` and `age` rebuilt per player from pre-rebuild Stage 0 | max gap 1e-7 / 8e-7, missing pattern identical | `perplayer_load.py` / `perplayer_load_check.json` |
| the model's inherited inputs against the pre-rebuild `match_timing/perplayer_features.parquet` and `leakproof_features.parquet` (rebuilds on repaired data) | identical for `sets_14d`, `age` and `ios_points_short`; correlation ≥ 0.9991 but not identical for the profile, `ratings_iid`, `elo_games`, `points_52w` | ad hoc check |

The last row matters: **`match_timing/perplayer_features.parquet` is not the model's source** for the profile and ratings (it was rebuilt from the repaired history), and despite its name it holds **A − B differences**, not per-player values.

### 1.3 Getting per-player values for the three difference-only inputs (code)

* **`elo_games`.** Copy `stage4_features.weighted_elo_pass` and keep its output columns 0–7 (overall R_A, R_B, N_A, N_B; surface R_A, R_B, N_A, N_B) instead of blending them. Constants: `predictability_diagnostic/stage4_constants.csv` (kind "weighted Elo scale") and `feature_alpha_audit/repair_history.frozen_constants`. One pass per tour.
* **`points_52w`.** Copy Stage 4's `mu_points|52 weeks` (`stage4_features.py`), or `match_timing/rebuild.points_52w` run on the pre-rebuild Stage 0 without `repair_tables`, and keep `val['spw']` and `val['rpw']` for the A and B rows: each player's shrunk 52-week serve and return points won.
* **`ios_points_short`.** Rerun `match_timing/ios_time.run_timed` for `spw` with h = 4 weeks (men) or 13 weeks (women) and Stage B's kappa and tau, on the pre-rebuild timeline, and keep O and D per player row. The day-by-day solve took 138 s (men) and 51 s (women) in the 5 Oct rebuild (`ios_features_summary.json`). The same machinery gives per-player leak-proof IOS on any statistic.

### 1.4 Reliability of each player's value (for uncertainty-weighted ideas)

Per-player evidence and uncertainty already on disk: Stage 3 `sd_serve_*`, `sd_return_*` (posterior SD; median 0.056) and `serve_pts_*`, `return_pts_*` (points of evidence; median 17,820 serve points); Elo counts `N_*`, surface counts `NS_*` (`pieces.parquet`); TTT `s2_*`, `so2_*` and counts `n_*`, `ns_*` (`surface_rating_race/ttt_offset.parquet`); Glicko-2 `glicko2m_u_*`, `glicko2m_vol_*`, TrueSkill `trueskill_u_*`, correlated-surface `glicko_cs_u_*` (`rating_systems/stageA_ratings.parquet`). *Caveat:* IOS and the profile exist for everyone (a player without evidence sits at the shrinkage prior, 0), so "100% coverage" is not 100% information.

## 2. (b) Features already built but not in the model

*Sources:* the builders' code, read for this map (a survey of every table; code), and the measured coverage (observed, `coverage_feature_tables.csv`; every column is a row of `inventory.csv`). "A − B" means only the difference (or A's log-odds) is stored; "per row in `f()`" names the function that holds each player's value before differencing, so that a copy returning both is a small change. Paths are under `data/studies/` (tables) and `src/eda/` (code). Coverage % is men 13–21 / women 13–21 / men 22–24 / women 22–24.

**Common caveats.** Data versions differ by table:
* Stage 4 (1 Oct), UFC ideas, rating systems and shot level (2 Oct): the pre-rebuild Stage 0 with the code as it was before the 2 October repairs. Their box-score histories only take matches Stage 0's `format` called standard, a label set per event from all its scores.
* Market anchoring and predictive frontier: the repaired, dated main-tour rows only (78,706–78,714 matches).
* Elo pieces, TTT offset and surface IOS (5–6 Oct): the pre-rebuild Stage 0; surface IOS with the repairs applied on the fly, on the pre-rebuild clock.

Constants were frozen on 2010–2018, so 2013–2018 is in-sample for them.

### 2.1 Ratings

| Family (columns) | Table; builder | Definition | A and B separately | Timing | Coverage % |
|---|---|---|---|---|---|
| Surface-**only** Elo (`elo_surf_a/b_ret`, `S_a/b`), its counts (`n_surf_*`, `NS_*`); no-retirement variants (`*_noret`) | `predictability_diagnostic/stage1_baselines`; `surface_elo_pieces/pieces` | moved only by matches on the surface, starts at 1500 | **yes** | safe | 100 all |
| Anchored surface Elo `XA_*`; surface-blind offset control `DG_*` | `surface_elo_pieces/pieces`; `pieces.elo_pass_ext` | surface rating starting from the overall rating; the offset with one surface code | **yes** | safe | 100 all |
| Elo change over 26 / 52 weeks; rank-Elo gap; points-weighted Elo | `stage4_features` `elo_change_26w\|single`, `elo_change_52w\|single`, `rank_elo_gap\|single`, `elo_points\|single` | Elo now − Elo then; Elo minus a per-season line on log rank; Elo with updates × points share | A − B; per row in `single_features`, `elo_variants` | safe | 99.8–100 |
| Glicko-2 (match by match), TrueSkill, correlated-surface Glicko/TrueSkill | `rating_systems/stageA_ratings`: `glicko2m_mu/u/vol_*`, `trueskill_mu/u_*`, `glicko_cs_mu/u_*`, plus `p_<system>` | filters over each player's matches; per-player columns are the **overall** components only | **yes** (overall components) | safe | 100 all |
| TrueSkill Through Time, leak-proof | `match_timing/ttt_timed` `p_ttt_timed`, `p_ttt_timed_overall`; `ttt_timed.job` → `ratings.ttt_pass_timed` | smoothed overall + surface chains, blended (0.35 men / 0.30 women) | P(A) only; per player in `job()`'s `res` | clock | 100 all |
| TTT with a surface offset | `surface_rating_race/ttt_offset`: `mu_*`, `s2_*`, `off_*`, `so2_*`, `n_*`, `ns_*` | overall skill and variance, surface offset and variance; Φ((μA + oA − μB − oB)/√(2 + Σ var)) | **yes** | clock (probe passed) | 100 all |
| **Leaking**: weekly TTT (`p_ttt*`, `ttt\|single`, `p_ttt_hold*`), Bradley–Terry (`bt_*`, incl. games, no-decay and surface variants), MESR (`mesr_*`, a rating solved from closing odds) | `rating_systems/stageA_ratings`, `stageA_ttt_hold`; `ufc_ideas/stageA_bt`, `stageA_mesr`, `stageA_features` | batch or smoothed fits on the weekly clock | yes for BT and MESR | **LEAK** | 99–100 |
| Stage 3 serve and return as separate inputs | `stage4_features` `rating_serve\|single`, `rating_return\|single` | A − B of each rating | A − B; **per player in `stage3_ratings`** | safe | 100 all |
| Rank and points as inputs | `stage4_features` `rank\|single` (log rank **B − A**: positive = A better ranked), `rank_points\|single`; `stage1_baselines` `p_rank`, `p_points` | filled rank for the unranked | A − B; raw per player in Stage 0 | safe | 100 all |

### 2.2 Box-score history aggregates (Stage 4)

| Family (columns) | Table; builder | Definition | A and B separately | Timing | Coverage % |
|---|---|---|---|---|---|
| 21 statistics × 5 forms: `<s>\|career`, `\|52 weeks`, `\|decayed`, `\|surface`, `\|adjusted` for spw, rpw, tpw, hold, brk, ace, df, first_in, first_won, second_won, bp_saved, bp_conv, bp_faced_pg, rpw_first, rpw_second, tb_won, sets_won, games_won, win, deciding, bp_over | `stage4_features`; `stage4_features.history_sums`, `form_value` | each earlier match centred on its tour × surface mean, shrunk with a per-statistic K; **decayed = 52-week half-life** (not 2 weeks); surface = earlier matches on this surface only; adjusted = career form re-stated against a typical opponent through the opponent's Stage 3 rating | A − B (logit of the shrunk share); per row in `form_value()` (`val`, A rows even, B rows odd) | safe | 98–100; women's hold, brk, bp_faced_pg 72–74 in 2013–21 |
| Points / games / break-point / components matchups (`mu_points`, `mu_games`, `mu_bp`, `mu_components` × 5 forms) | same; `matchup` | A's serve form against B's return form and the reverse, through the iid model | logit P(A); each side's rate in `matchup()` (`pa`, `pb`) | safe | ~99.7; women's `mu_games` 74 |
| Head to head (`h2h\|<form>`) | same; `h2h_sums`, `h2h_feature` | A's shrunk share of earlier meetings; `adjusted` = Σ(won − iid expectation)/(n + K) | pair-level only (meeting count in `S["h2h"]`) | safe | career 60.7 / 57.3 / 58.8 / 57.1; 52 weeks 29.5 / 26.3 / 29.8 / 25.7 |

Traps (code): men's `bp_over` is identically 0 in every form (K infinite); `tb_won` is near-constant (no history reaches K); several `|surface` forms are constant (women's bp_saved on grass, men's bp_conv on grass, tb_won in several cells).

### 2.3 Opponent-adjusted profiles beyond the model's, and splits by opponent strength

| Family (columns) | Table; builder | Definition | A and B separately | Timing | Coverage % |
|---|---|---|---|---|---|
| adjperf / adjdef in the 52-week and career forms (15 statistics), and the decayed forms the model does not use (adjperf_spw, adjperf_rpw, the other adjdef) | `ufc_ideas/stageB_adj_features` (90 columns); `stageB_adjperf.build` | as the model's profile (§1.1), other windows: 52 weeks and career unweighted | A − B; **rebuildable per player from `stageB_adj.parquet`** as `perplayer_form.py` does (change h3 / window) | safe | 98–100; women's hold, brk, bp_faced_pg 74 |
| Splits by opponent strength: `vs_strong_<s>`, `vs_weak_<s>`, `strong_minus_weak_<s>` (tpw, spw, rpw), thirds, `slope_tpw`, `wins_over_strong/weak`, **`strong_gap_x_strong_opp`** (a cross-player product), "earlier weeks" variants; 52 weeks and career | `ufc_ideas/stageB_split_features`; `stageB_split.split_features` | mean adjperf z against opponents whose pre-match surface-only Elo is above or below the 2010–18 main-tour median, shrunk; slope of z on opponent Elo | A − B; per player in `split_features()` `res["a"]`, `res["b"]` | safe | 98–100 |

### 2.4 Strength of schedule and revaluation

| Family (columns) | Table; builder | Definition | A and B separately | Timing | Coverage % |
|---|---|---|---|---|---|
| `sos_elo` (52 weeks, decayed), `sos_rating`, `sos_won_elo`, `sos_lost_elo`, `over_elo`, `over_elo_strong` | `ufc_ideas/stageC_sos_part`; `stageC_sos.sos_value` | mean of opponents' **pre-match** Elo (or Stage 3 rating) over 52 weeks, shrunk; results above Elo's expectation | A − B; per row in `sos_value()` | **unsettled**: own-sequence by the code, but `stageC_sos.py` is the script the 5 Oct decision marks as leaking: run `probe.py` before any use | 99.9 all |
| `revalue`, `revalue_won`, `revalue_lost` and `_later` versions | same; `revalue_pairs`, `revalue_value` | opponents' Elo now minus at the meeting | A − B | **LEAK** ("now" can be a later Slam row) | 99.9 all |

### 2.5 Load, rest and fatigue beyond `sets_14d`

| Family (columns) | Table; builder | Definition | A and B separately | Timing | Coverage % |
|---|---|---|---|---|---|
| `minutes_7d`, `minutes_14d`, `sets_7d`, `prev_minutes`, `prev_sets`, `days_since`, `played_career`, `played_52w`, `last_early` (own and opponent's early end last time), `recent_level` | `stage4_features` (`\|single`); `state`, `single_features` | event-start-date windows; log1p totals; missing if a match in the window lacks the count | A − B; per row in `single_features()` (`win`, `gap`, `v`) | safe | sets/days/played 100; minutes-based 84–89 / **54–62** / 87–94 / 81–90 |
| `late_decline\|career` and **its products** `late_decline_x_bo5`, `late_decline_x_long`; `grinder\|career`, `grinder\|52 weeks`, **`grinder_x_bo5`**; **`sets_14d_x_decline`**, **`minutes_14d_x_decline`** | `ufc_ideas/stageC_fatigue_part`; `stageC_fatigue.build` | serve-point rate in sets 3+ minus sets 1–2 at earlier Slams (from point-by-point), relative to opponents, shrunk; residual points share in long vs short matches (minutes per set); products with best of five (men), expected closeness, 14-day load | A − B / products; per player in `build()` locals | safe | late_decline 88.5 / 71.0 / 86.0 / 70.3; grinder 52 weeks 99.7 / **63.4** / 99.8 / 99.3 |

### 2.6 Surface

| Family (columns) | Table; builder | Definition | A and B separately | Timing | Coverage % |
|---|---|---|---|---|---|
| Pooled leak-proof IOS `cur_O_<s>`, `cur_D_<s>` (spw + the 7 statistics); the surface model's all-surface parts `srf_O_<s>`, `srf_D_<s>` and surface deviations `srf_E_<s>`, `srf_F_<s>`; the spw versions of the effective ratings | `surface_ios/surface_features`; `build_features.py`, `ios_surface.py` | see §1.1; E/F are the player's serve/return deviation on the match's surface | **yes** | clock (probe passed) | 100 all |
| Surface-IOS arms not kept: `sdev` (E_A − E_B, F_A − F_B), `snet1` (`dnet_spw`), placebo `snet1_perm`, `sprof_bysurf` | `surface_ios/arms/*.parquet`; `arms.recipe` | differences of the per-player columns | via `surface_features` | clock | 100 |
| Last season's surface form `prev_res`/`prev_n` (`surf_form_prev`), career surface matches `NS` (`surf_career`) | `surface_elo_pieces/pieces`, `surface_elo_pieces/frame.parquet` `x_surf_*_a/b` | wins above overall Elo's expectation on the surface last season / (n + 5); log1p career surface count | **yes** | safe | 100 all |
| Surface statistic levels and deviations `ss_level_<s>`, `ss_surf_<s>`, `ss_dev_<s>` (12 statistics), `ss_surface_evidence` | `market_anchoring/surface_stat_features`; `surface_stats.features` | decayed level (365-day half-life), surface level (730 days) and their difference; no opponent adjustment | A − B; per player in `features()` (`level`, `surf`, `dev`, A rows `0::2`) | safe (strictly earlier match days) | 99.4–99.6; history = repaired dated main-tour main draws only |
| `surface_first\|single` (was in the 54-input model, replaced 6 Oct) | `stage4_features` | fewer than 3 matches on the surface this season | A − B | safe | 100 |

### 2.7 Player background and context built in Stage 4

| Family (columns) | Definition | A and B separately | Timing | Coverage % |
|---|---|---|---|---|
| `height\|single`, `lefty\|single`, `vs_hand\|single` | height A − B; left-hander indicator A − B; record against the opponent's hand relative to overall | A − B; raw per player in Stage 0 | safe | height 99.7 / 93.8 / 99.9 / **64.4**; hand 98–100 |
| `home\|single` | player's country = event's country (hand-made `stage4_event_country.csv`) | A − B (−1, 0, 1) | safe | 100 |
| `entry_q`, `entry_ll`, `entry_wc`, `entry_pr` | entry code indicators, A − B | A − B | safe; the existence mask uses the whole season's records | Q/LL/WC 91–99; PR 57.7 / 16.0 / 80.4 / 65.0 |
| `best_of_five\|single` | men only, baseline log-odds × indicator | match-level | **reads the match's own score** (post-match dependency in the stored column; on 2013–2024 model rows recorded and scheduled best-of agree everywhere, observed) | men 100 |
| `bigpoint_return\|single` | importance-weighted minus plain return points won at earlier Slams (Sackmann's point files) | A − B | safe | 88.5 / 84.2 / 86.0 / 84.7 |

### 2.8 Predictive frontier

| Family (columns) | Definition | A and B separately | Timing | Coverage % |
|---|---|---|---|---|
| `pf_serve_28/182`, `pf_return_28/182`, `pf_*_momentum` | decayed points won above the repaired ratings' expectation (half-life 28 or 182 days); momentum = 28 − 182 | A − B; per player in `predictive_frontier/features.build_features` arrays | safe (strictly earlier days) | 99.4–99.6 |
| `pf_box_seen_diff`, `pf_evidence_diff`, `pf_instability_diff`, `pf_rest_diff`, `pf_history_seen_diff`, `pf_retired_loss_*`, `pf_surface_*` | evidence, residual dispersion, rest (capped 365 days), retirement losses, surface form | A − B | safe | 99.4–99.6 |
| **Products**: `pf_box_unknown_elo`, `pf_uncertainty_elo`, `pf_uncertainty_sr`, `pf_instability_elo`, `pf_inactivity_elo`, `pf_history_unknown_elo`, `pf_surface_unknown_elo` | a symmetric reliability term × the Elo (or serve + return) difference: already **S/U-type interactions** | symmetric × signed | safe | 99.4–99.6 |
| `pf_event_speed_style`, `pf_event_speed_elo`, `pf_event_evidence_style`, `pf_event_unknown_elo` | this edition's earlier serve residuals (a court-speed estimate) × style (serve − return rating difference) or × Elo | match-level product | **field statistic on a strictly-earlier-day clock, not `timing.parquet`; never probed** | 99.4–99.6 |

History for every `pf_*` and `ss_*` column is the 78,706 repaired dated main-tour matches only.

### 2.9 Shot level

| Family (columns) | Table; builder | Definition | A and B separately | Timing | Coverage % |
|---|---|---|---|---|---|
| 25 per-match statistics (`srv_quick`, `ret_quick`, `rally5`, `rally9`, `ret_inplay`, `long_share`, `winner_rate`, `error_rate`, `ue_share`, `w_ratio`, `spd1`, `spd2`, `net_rate`, `net_won`, `t_share`, `wide_share`, `deep_ret`, `bh_ue_share`, `fh_win_share`, `consolidate`, `break_back`, `serve_set`, `pressure_srv`, `first_in_pressure`, `after_loss`) | `shot_level/stage1_match_stats` (`_n`, `_d`, `_src`); `stats.py` | numerators and denominators per player-match; pressure and after-loss are excesses over the player's own rate | per player-match | post-match (history only) | see §4.6 |
| Histories: `<s>\|off\|{career, dec2, w52}`, `<s>\|def\|…`, `<s>\|adj\|{dec2, w52}`, `spd1_change\|off\|dec2-w52`, **`rally_edge\|x_long\|w52`** (a product) | `shot_level/stage2_features` (A − B); `shot_level/stage3_sides` (`A\|…`, `B\|…`, `\|has`) | empirical-Bayes shrunk rates; dec2 = 2-week half-life; def = what opponents did against the player; adj = centred on each opponent's norm | **yes in `stage3_sides`** (prior-filled; use `\|has`) | safe | real data for both players, 52-week forms: men 58–87, women 47–84 (2013–21); men 85–98, women 83–93 (2022–24) |

`stage3_sides` also holds this match's own serve points (`A_spw_n/d`, `B_spw_n/d`): targets, not inputs.

### 2.10 Clutch from point-by-point, and match anatomy (history only)

| Family (columns) | Table | Definition | Note |
|---|---|---|---|
| `clutch_serve`, `clutch_return`, `clutch`, `points_share`, weighted serve/return points per player-match | `predictability_diagnostic/stage2_pbp_players.parquet` (19,896 rows) | importance-weighted minus plain points won, Slam point-by-point files (2011–) | keyed by the Slam files' own match ids (`2011-ausopen-1103`), not Stage 0's; Stage 4's `bigpoint_return` draws on the same Slam point files |
| `luck`, `p_floor`, `tb_over_a`, `bp_save_over_a/b`, `bp_net_a`, component split of the points edge, a pure-luck twin | `predictability_diagnostic/stage2_matches.parquet` | describe the finished match | **post-match**: targets or lagged history only |

### 2.11 Diagnostic copies (not new features)

* `predictability_diagnostic/audit4/lag_features.parquet`: 23 Stage 4 columns rebuilt (`#built`, equal to 9.5e-7) and with one more match of lag (`#lag`): a leak check.
* `feature_alpha_audit/chronology_calendar_week_features.parquet`: the 16-input profile with every tournament date moved to its calendar Monday.
* `match_timing/leakproof_features.parquet`, `perplayer_features.parquet`, `ios_features.parquet`: A − B copies of the model's 53 inputs on the repaired history (the profile, ratings and points versions differ slightly from the model's, §1.2).

### 2.12 Interaction terms already built (so not new as such)

`late_decline_x_bo5`, `late_decline_x_long`, `grinder_x_bo5`, `sets_14d_x_decline`, `minutes_14d_x_decline` (UFC ideas, stage C); `strong_gap_x_strong_opp` (stage B splits); `rally_edge|x_long|w52` (shot level); `best_of_five` (Elo × best of five, Stage 4); the weekly `prod_<s>` (leaking) and the model's own surface `prod_<s>`; `pf_*_elo`, `pf_uncertainty_sr`, `pf_*_style` (predictive frontier). Their results are in §3.2.

## 3. (c) Tried before: what earlier studies found

*Source:* a register survey of every `docs/studies/*/README.md`, their sub-reports and `docs/decisions/` (doc). Numbers are copied as reported, never recomputed. Ten of them were spot-checked against their files (Stage 4's best-of-five row, the surface-IOS no-odds gain, the repaired profile, the grinder, the short-memory IOS, tiebreak over-performance, the Elo-pieces arms, leak-proof TTT): all matched.

**How to read.**
* **Units.** Gains in milli-log-loss (mLL), **positive = the named feature or arm is better** (lower log loss) unless a cell says otherwise. Intervals are 95%; **tie** = the interval spans 0; "no CI" = none reported. M men, W women, B both tours pooled.
* **Tests.**
  * **onE**: added to Stage 1 surface Elo in the predictability-diagnostic harness (a refitted logistic regression, walk-forward by season).
  * **onM**: the same, added to the de-vigged average close.
  * **onP**: added to the calibrated Pinnacle close.
  * **pm**: per-match intervals (the early harness); **4wk** / **wk**: clustered in four-week or calendar-week blocks; **+seed**: seed variance added.
* **Flags.**
  * **25‑26**: the window includes 2025 and/or 2026, the seasons this study keeps closed; **✗**: it includes neither.
  * **LEAK**: built on a clock CLAUDE.md lists as leaking (before 5 Oct).
  * **HIST**: the report's banner calls it historical (the 2 Oct audit found chronology, format and evaluation defects; the repairs re-ran only the shortlisted features, so weak families' old scores are not corrected negative evidence).
  * **SUP→x**: superseded by x. **FMT**: format read from the match's own score (bounded at ≤ 0.015 mLL). **IS**: in-sample (tuning years). **PH**: post hoc. **CSV**: read from a results CSV/JSON, rounded to 3 decimals.
* **Source codes** (all under `docs/studies/` unless noted):
  * study folders: PD `predictability_diagnostic/`, UFC `ufc_ideas/`, FAA `feature_alpha_audit/`, RS `rating_systems/`, PF `predictive_frontier/`, PFT `predictive_frontier_tabpfn/`, TT `tabpfn_thinking/`, TL `tabpfn_leakproof/`, MT `match_timing/`, SI `surface_ios/`, SEP `surface_elo_pieces/`, SRR `surface_rating_race/`, MA `market_anchoring/`, MS `meta_stack/`, LS `line_sharpening/`, SB `sharp_benchmark/`, PSM `polymarket_sharp_money/`, SL `shot_level/`;
  * DEC `docs/decisions/`; D `data/studies/`;
  * a bare `stage4_ranking.csv` is under `data/studies/predictability_diagnostic/`, a bare `stageB_ranking.csv` under `data/studies/ufc_ideas/`.

**Caution for the auditors (inference).** Almost every result here was read on windows that include 2025–26. Using these numbers to choose or kill an idea is a forking path through the closed seasons; the ✗ rows (design years only) are the clean ones.

### 3.1 Results by family

#### Elo variants

| Feature/arm | Test (baseline, model) | Window, tour | Result | Verdict | Flags | Source |
|---|---|---|---|---|---|---|
| Surface Elo (blend 0.30 M / 0.25 W) vs overall Elo | raw log loss | 2013–26, M/W | M +3.8, W +3.0 (no CI); "2.8–4.0 better than overall Elo in every window" | "surface Elo as the rating" (owner, 30 Sep) | 25‑26; HIST | PD/stage1.md §3 Headline; §Decisions |
| Blend weight tuned; K tuned vs FiveThirtyEight | IS | 2013–18 | blend +3.6 M / +2.8 W; K +2.1 both (no CI) | constants frozen | ✗; IS; HIST | PD/stage1.md §Tuning |
| Retirements counted vs skipped (+ = counting better) | raw | 2022–26 | M Elo +1.9 [1.4, 2.3], surface Elo +1.6 [1.2, 2.1]; W +1.8 [1.2, 2.4] both | "Counted is the default kept" | 25‑26; HIST | PD/stage1.md §Retirements |
| Surface Elo vs market ("room"; + = market better) | raw, matches with odds | 2022–26 | M 22.5 [19.1, 25.8]; W 18.8 [15.5, 22.1] | benchmark | 25‑26; HIST | PD/stage1.md §In short |
| Elo by format (men) | favourite win rate minus forecast, percentage points | 2013–26 M | best of 5 +2.9 pp; best of 3 −1.9 pp; room 25.1 [20.4, 29.9] vs 18.4 [16.2, 20.6] | "Elo does not know how long a match is" | 25‑26; HIST | PD/stage1.md §Best of five |
| Overall Elo alone vs blend | Elo-only, recalibrated | 2019–21 | M main −4.84 [−7.24, −2.44]; W −2.74 [−4.60, −0.88] | worse | ✗ | SEP/strategy.md §4 |
| Evidence-weighted blend w·n/(n+k); best weight by evidence bin | IS | 2013–18 | tunes to k = 0; k > 0 worse by 0.6–1.8 M / 0.4–1.0 W; bin gains 0–0.8 (upper bounds) | "Direction right, no gain" | ✗; IS | SEP/README §2; strategy §3 |
| Re-anchored blend | Elo-only | 2019–21 | M main −0.00 (tie); M all levels −0.51 [−0.82, −0.20]; W main −0.55 [−1.08, −0.02]; the audit's evidence-weighted anchored variant +0.35 [−0.15, +0.85] (tie) | loses | ✗ | SEP/strategy §4; audit.md S5.3 |
| **Surface-offset Elo** vs blend (no odds) | Elo-only, recalibrated | 2019–21; forward-chained 2016–21 | M main +4.50 [+2.06, +6.94]; W main +1.81 [−0.99, +4.61] (tie); forward-chained M +2.16 [+0.58, +3.73], W +1.44 [+0.10, +2.77]; 2016–18 only M +0.54 (tie) | "beats the fixed blend" | ✗ | SEP/README §3 |
| Offset vs surface-blind offset control | Elo-only | README window not stated; audit 2019–21 | README M +6.44 [+3.99, +8.89], W +4.61 [+3.21, +6.01]; audit M all +5.97, main +9.16; W +5.00 / +4.66 | "the gain is surface structure" | ✗ | SEP/README §3; audit.md §3 |
| Offset Elo / blend / literal pieces given odds | linear, recalibrated odds, forward-chained | 2016–21 | offset pieces M −0.09 [−0.25, +0.08], W +0.06 (ties); README "−0.03 (men), +0.01 (women)"; blend M −0.06, W −0.04 (ties); literal M −0.27 [−0.46, −0.08] worse | "Given the odds it adds nothing" | ✗ | SEP/strategy §4; README §3 |
| Overall + 1500-start surface rating (± career counts), no odds | linear, forward-chained | 2016–21 M | +0.10 [−0.23, +0.42] (tie); + counts −0.83 [−1.76, +0.11] (tie) | "Not in a linear model" | ✗ | SEP/strategy §3 |
| primary / literal / elo_only / switch_only vs base (with odds) | TabPFN-3.5-Plus API, 3 seeds, 4wk | 2022–26 B | primary −0.01 [−0.24, +0.21] (M +0.14, W −0.18); literal −0.08; elo_only +0.03 (M +0.20 [−0.08, +0.48]); switch_only +0.01; all ties (MDE 0.40) | "neither improves nor hurts" | 25‑26 | SEP/README §5.1 |
| Same arms, recalibrated | slopes from 2019–21 | 2022–26 | primary −0.05 [−0.26, +0.16]; literal W −0.27 [−0.50, −0.05] worse | tie | 25‑26; PH | SEP/README §5.4 |
| primary vs base, no odds | Plus, 1 seed | 2022–26 | B +1.36 [+0.43, +2.29]; M +2.74 [+1.23, +4.25] (5 of 5 seasons); W −0.14 (tie) | "real and priced" | 25‑26 | SEP/README §5.5 |
| primary vs base, subsets / price dispersion | Plus | 2022–26 | early surface season −0.23 (tie); both players new +0.42 (tie); grass −0.17 (tie); most-dispersed third +0.40 [+0.02, +0.78] (~60 cells) | "a hint… not evidence" | 25‑26; PH | SEP/README §5.3, §5.7 |
| **base → elo_off** (offset Elo + switch pairs) | local TabPFN, calibrated, 3 seeds | 2022–26; Polymarket 24 h 2025–26 | close −0.05 [−0.24, +0.14] (tie); no price +1.01 [+0.18, +1.84] (M +2.24 [+0.99, +3.50]); 24 h +0.78 [+0.03, +1.54]; W at close −0.25 [−0.55, +0.05] (tie) | **adopted** 6 Oct ("Swap the old Elo blend…") | 25‑26 | SRR/README §3–4; DEC/2026-10-06-offset-elo.md |
| Offset Elo rating alone, rescaled | slope from 2013–18 | 2019–26 | vs Stage 1 Elo M +0.94 [+0.43, +1.46], W +0.89 [+0.12, +1.66]; raw M −1.58 [−2.22, −0.94] | over-confident raw | 25‑26; PH | SRR/README §2 |
| Elo from dated history only (repairs) vs Stage 1 Elo | calibrated | 2019–26 | M −18.26 [−21.56, −14.97]; W −16.25 | "cripples a rating" | 25‑26 | RS/stageC.md §repaired |
| Games-weighted Elo | onE, pm | 2013–26 | M 1.82 [1.55, 2.08]; W 2.38 [1.96, 2.79]; onM −0.03 / −0.03 (ties); one match later 0.33 / 0.57 | "margin of the most recent results" | 25‑26; HIST | PD/stage4.md §2, §3, §7 |
| Games-weighted Elo in ladders | logistic ladder, wk / 4wk | 2022+; 2019+ repaired | M 0.31 [−0.01, 0.62] (tie); W 0.93 [0.41, 1.45]; repaired M +0.278 (tie), W +0.540 [+0.149, +0.931]; given TTT 0.04 / −0.16; given BT 5.22 / 5.12 | "more convincing for women" | 25‑26 | FAA/elo_notes.md; repairs.md; RS/stageB.md; UFC/stageA.md |
| Points-weighted Elo; Elo change over 6 and 12 months | onE / onM, pm | 2013–26 | points-weighted M 0.267 [0.187, 0.348], W 0.693 [0.386, 1.000]; onM ties; change 6m/12m M −0.256 / −0.300 (worse), W ties | finding / worse | 25‑26; HIST; CSV | stage4_ranking.csv |

#### Glicko, TrueSkill, TrueSkill Through Time (TTT), correlated surfaces

| Feature/arm | Test | Window | Result | Verdict | Flags | Source |
|---|---|---|---|---|---|---|
| Each system vs surface Elo | raw, 4wk | 2019–26 M/W | TTT +2.65 [+1.89, +3.40] / +3.00 [+1.67, +4.33]; TTT with two-week events held back +2.59 / +2.75; Glicko corr. surfaces +2.11 / +2.68; TrueSkill corr. surfaces +1.75 / +3.29; Glicko-2 match by match +0.90 [+0.27, +1.54] / +1.01 (W tie); TrueSkill +0.69 / +1.30 (W tie); Glicko-2 weekly −1.42 [−2.23, −0.62] / −0.32 (W tie) | TTT "leading candidate" (DEC 3 Oct) | 25‑26; LEAK (TTT); SUP→MT §8 | RS/stageB.md; DEC/2026-10-03-leading-rating-candidate.md |
| Same, tuning years | IS | 2013–18 | TTT +2.65 / +2.53; Glicko-2 weekly −5.96 / −2.15 (no CI) | volatility "adds nothing" | ✗; IS | RS/stageA.md |
| Ratings given odds (harness) | onM | 2013–26 | TTT +0.04 [−0.02, +0.11] / −0.02 (ties); Glicko-2 match by match M +0.08 [+0.01, +0.16]; range −0.03 to +0.08 | "no rating adds anything" | 25‑26; LEAK | RS/stageB.md |
| Ratings given Elo; Elo given TTT | harness | 2013–26 | TTT +2.44 / +4.91; Elo given TTT −0.34 / −0.57 | "TTT makes Elo redundant" | 25‑26; LEAK | RS/stageB.md |
| TTT vs runner-up | 4wk | 2019–26 | M vs Glicko corr. +0.54 [−0.02, +1.10] (tie); W vs TrueSkill corr. −0.29 [−1.29, +0.71] (tie) | – | 25‑26 | RS/summary.md |
| Feature ladder (swap or add a rating) | FAA ladder, wk | 2022–26 M | TTT alone +2.08 [+1.33, +2.83]; swap +0.48 [+0.03, +0.93]; both ratings +1.17 [+0.70, +1.65]; W swap +0.19 (tie), both +1.21 | "only partly orthogonal" | 25‑26; LEAK | RS/stageC.md |
| Ratings given calibrated Pinnacle | wk | 2019–26 M | surface Elo +0.02 [−0.01, +0.05]; TTT +0.08 [−0.01, +0.16]; Glicko-2 match by match +0.12 [+0.01, +0.23]; profile + TTT vs profile +0.00 | "under two tenths" | 25‑26 | RS/stageC.md |
| Repaired cohort | 4wk | 2019–26 | TTT alone +2.07 / +3.05; in the full model +0.34 / +0.57 (ties); onP +0.09 [−0.01, +0.19] | – | 25‑26 | RS/stageC.md |
| Leak-proof TTT (`ttt_pass_timed`) | raw vs Elo | 2019–26 | M +2.66 [+1.90, +3.41]; W +2.93 [+1.61, +4.25]; vs original M +0.01 (tie), W −0.07 [−0.14, −0.00] | "edge … survives the fix" | 25‑26 | MT/README §8 |
| TTT offset (surface-offset TrueSkill team), rating alone | rescaled | 2019–26 | vs offset Elo +3.61 [+2.79, +4.43] / +2.46 [+1.06, +3.87]; vs decided TTT +1.91 [+1.40, +2.42] / +0.50 (tie) | "best of the four" | 25‑26; PH | SRR/README §2 |
| ttt_off vs elo_off: 24 h price / no price / close / price move | local TabPFN | 2022–26; 2025–26 for 24 h | −0.25 [−0.73, +0.22]; −0.02; −0.01; move slope +0.17 [−0.12, +0.46]; all ties | "tie, everywhere" → offset Elo is the default | 25‑26 | SRR/README |
| Decided TTT (blend) in the model | local TabPFN | as above | at 24 h −0.65 [−0.95, −0.36] worse; ttt_blend → ttt_off at 24 h +1.19 [+0.59, +1.78], no price +1.19 [+0.48, +1.91]; W at close −0.25 [−0.46, −0.05] worse | "never the decided blend" | 25‑26 | SRR/README §3–4 |

#### Bradley–Terry and MESR (all LEAK, HIST)

| Feature/arm | Test | Window | Result | Verdict | Flags | Source |
|---|---|---|---|---|---|---|
| BT vs surface Elo | raw, pm | 2013–26 / 2022–26 | M −1.60 [−2.44, −0.76]; W −4.45; 2022–26 −1.46 / −6.66; surface BT M +0.58 (tie), W −2.20; games-weighted BT M +0.11 (tie); no-decay BT −29.47 | "not a better base rating" | 25‑26 | UFC/stageA.md |
| BT given Elo (harness) | onE | 2013–26 | M +1.77 [1.36, 2.18]; W +0.70 [−0.05, 1.45] (tie); BT + ratings +4.55 / +3.89; Elo given BT +4.18 / +3.62 | "a feature, not a replacement" | 25‑26 | UFC/stageA.md |
| All stage A rows given odds | onM | 2013–26 | −0.06 to +0.03 (ties) | – | 25‑26 | UFC/stageA.md §Given the market |
| MESR (rating solved from closing odds) | onM / onE / as a forecast | 2013–26; 2022–26 | onM −0.03 / −0.02; onE M −0.31 (tie), W +0.78 [0.06, 1.50]; as a forecast vs Elo M +0.57 [−2.89, 4.03] (tie) | "Close this branch" (FAA) | 25‑26 | UFC/stageA.md; FAA/method_notes.md |
| MESR − BT; MESR − Elo | onM | 2013–26 | −0.01 / −0.06; +0.02 / −0.04 (ties) | "no information the closing line lacks" | 25‑26 | UFC/stageA.md |

#### Serve/return ratings, points aggregates, short-memory IOS

| Feature/arm | Test | Window | Result | Verdict | Flags | Source |
|---|---|---|---|---|---|---|
| Stage 3 serve/return ratings, next-match serve points | mLL per serve point vs surface average | 2019–26 | M 2.65 [2.59, 2.71] vs history alone 1.13; W 2.43 vs 1.10 | "most repeatable measure" | 25‑26; HIST | PD/stage3.md §4b |
| rating_matchup (ratings through the iid model) | onE / onM, pm | 2013–26 | onE M 3.61 [3.04, 4.18], W 4.58 [3.64, 5.52]; Grand Slams M 14.40; onM M −0.056 [−0.322, 0.210], W −0.010 (ties); lag 71% / 74% kept | closes "28% (men) and 29% (women)" of the Elo-to-market gap; "no" beyond the bookmakers | 25‑26; HIST; FMT | PD/stage4.md; summary.md |
| Serve rating / return rating separately | onE, pm | 2013–26 | M 1.151 / 0.658; W 1.872 / 0.836; onM ties | finding | 25‑26; HIST; CSV | stage4_ranking.csv |
| Serve/return matchup in ladders | FAA ladder | 2022+; repaired 2019+ | 4.74 [4.01, 5.48] / 3.12 [2.21, 4.02]; repaired +12.329 / +11.733; given TTT step +3.10 / +1.82 | "Keep serve/return strength" | 25‑26 | FAA/elo_notes.md; repairs.md; RS/stageC.md |
| mu_points 52w (points matchup) | onE / onM | 2013–26 | onE M 1.55 [1.26, 1.85], W 1.59; onM M 0.093 [−0.105, 0.291], W 0.025 (ties); given BT 0.32 / 0.30; given TTT 1.13 / 0.71 | absorbed by BT | 25‑26; HIST; FMT | PD/stage4.md; UFC/stageA.md; RS/stageB.md |
| mu_components / mu_games / mu_bp 52w | onE / onM | 2013–26 | components M 1.526; games W 1.337 with onM −0.094 [−0.169, −0.019]; mu_bp M 0.056 (tie), W 0.275 [0.067, 0.483] | finding / possible | 25‑26; HIST; CSV | stage4_ranking.csv |
| tpw / spw / rpw (forms) | onE / onM | 2013–26 | tpw 52w M 1.334, W 1.39; onM ties; spw career M −0.189 [−0.373, −0.006] | "12 months help; career averages do not" | 25‑26; HIST; CSV | PD/summary.md; stage4_ranking.csv |
| Short-memory IOS points matchup (h 4 / 13 weeks) | onE / onM, pm | 2013–26 | M h4 3.72 [3.30, 4.13], onM 0.13; W h13 5.02 [4.16, 5.88], onM 0.01; tuned IOS M 1.08 / W 2.21; beyond Elo + ratings M 0.50, W 0.64; tuned IOS there −0.74 / −0.28 | "winner … wants a short [memory]" | 25‑26; LEAK; HIST; PH; FMT | UFC/stageB.md |
| Short IOS in the FAA ladder | wk | 2022+ | after adjusted points 0.13 [0.05, 0.20] / 0.25 [0.13, 0.36]; repaired −0.013 / −0.052 (ties) | "much less incremental value" | 25‑26; LEAK (original) | FAA/elo_notes.md; repairs.md |

#### IOS offence/defence profile, products, surface IOS

| Feature/arm | Test | Window | Result | Verdict | Flags | Source |
|---|---|---|---|---|---|---|
| IOS single ratings | onE | 2013–26 | M −0.69 to 0.58; W −0.26 to 0.83 | "add little" | 25‑26; LEAK; HIST | UFC/stageB.md |
| IOS profile (14 inputs); style (6); skill (8) | onM, pm, unpenalised | 2013–26 | M −0.06 [−0.48, 0.36], W −0.17; style −0.03 / 0.02; skill −0.11 / −0.13 (all ties); given ratings M 3.00 | "add nothing" | 25‑26; LEAK; HIST | UFC/stageD.md Part 2 |
| IOS (21) linear with odds, original vs leak-proof inputs | logistic, fit 2013–21 | 2022–26 M | −0.16 [−0.83, +0.52] / −0.15 [−0.82, +0.53] (ties) | – | 25‑26 | MT/README §7 |
| TabPFN's reliance on the IOS profile + products | share of the adjustment's variance lost when the group is shuffled | 2022–26 | M 0.62, W 0.74 (largest group); GAM on odds + IOS only M +0.03 (tie) | "family that added nothing linearly" | 25‑26; LEAK → SUP by TL | TT §Where the gain comes from |
| Leak-proof IOS refit vs original Thinking fit | TabPFN-Thinking | 2022–26 | M −0.06 [−0.13, +0.02]; B 0.00 (ties) | "leak did not create the result" | 25‑26 | TL/README |
| Surface IOS statistic forecasts | mLL per unit of statistic (higher = better) | out of sample 2019–26 | M holds +0.40 [+0.34, +0.46] (grass +0.88); W +0.39 [+0.28, +0.51]; all 16 pairs positive | real | 25‑26 | SI/strategy §3.6 |
| Surface deviations given odds (linear) | fit 2013–16, scored 2017–18 | 2013–18 | 4 return deviations M +0.01 (tie); 21-input change W −2.53 [−3.99, −1.06]; audit net shift 2015–18 ties | "already has the surface information" | ✗ | SI/strategy §3.7; audit.md |
| R1 sprof / R2 sdev / P1 snet1 / placebo, validation | local TabPFN, recalibrated, +seed | 2019–21 | R1 +0.15 [−0.08, +0.38]; P1 +0.10; placebo +0.06; R2 +0.03 (all ties) | R1 chosen | ✗ | SI/strategy §7.2 |
| R1 vs base (primary), with odds | same | 2022–26 B | +0.01 [−0.10, +0.13] (M +0.07, W −0.05); R2 −0.06; P1 vs placebo −0.00 (all ties); early-season lead "did not replicate" | **kept** (DEC 6 Oct; women open) | 25‑26 | SI/README; DEC/2026-10-06-surface-ios-profile.md |
| R1, no odds | same | 2022–26 | M +0.83 [+0.39, +1.27]; W −0.33 (tie); B +0.27 [−0.03, +0.58] (tie); 2019–21 M +0.98 | "information is real; the price already has it" | 25‑26 | SI/README |
| One model vs a model per surface | same | 2022–26 | −0.28 [−0.77, +0.21] (tie); W grass −3.58 [−7.02, −0.14] | one model at least as good | 25‑26 | SI/README |

#### Opponent-adjusted profiles (adjperf / adjdef, profile16)

| Feature/arm | Test | Window | Result | Verdict | Flags | Source |
|---|---|---|---|---|---|---|
| adjperf_tpw, 2-week decay | onE / onM, pm | 2013–26 | onE M 3.19 [2.85, 3.54], W 3.32 [2.51, 4.12]; onM 0.14 / −0.07 | "current form" | 25‑26; HIST | UFC/stageB.md |
| adjperf by statistic, best channel | onE | 2013–26 | spw 2.78 / 2.97; hold 1.82 / 2.48; bp faced per game 1.94 / 1.63; first-serve points 1.75 / 1.90; df 0.18 / 0.25; first in 0.02 / 0.16 | adjperf wins 10 of 15 statistics | 25‑26; HIST | UFC/stageB.md |
| adjperf given odds | onM | 2013–26 | spw M 0.20 [−0.13, 0.53] (tie); W aces 0.23 [0.02, 0.44] (clears the line); W second-serve 0.13 (tie) | "market already prices recent form" | 25‑26; HIST | UFC/stageB.md |
| adjperf memories / earlier weeks only / career | onE | 2013–26 | tpw 52w 1.78 / 1.91; earlier weeks only 2.09 / 1.83; career −0.14 / −0.08 | same-event rounds carry part of it | 25‑26; HIST | UFC/stageB.md |
| adjperf beyond Elo + ratings (joint refit) | onE + ratings | 2013–26 | tpw 0.70 [0.57, 0.82] / 1.48 [0.99, 1.98]; spw 0.83 / 1.43 | adds | 25‑26; HIST | UFC/stageB.md |
| Stage 4 "opponent-adjusted" form (career sums) | onE | 2013–26 | −0.15 to 0.29 | "recent form beats opponent adjustment" (disputed, §3.4) | 25‑26; HIST | PD/stage4.md; FAA/elo_notes.md |
| Adjusted recent points in ladders | ladder | 2022+; repaired 2019+ | 1.03 [0.59, 1.47] / 1.26 [0.37, 2.15]; repaired +0.777 / +1.142 | "worth keeping" | 25‑26 | FAA/elo_notes.md; repairs.md |
| **Profile16 vs odds** (UFC stage D) | onM, pm, unpenalised | 2013–26 | M 0.51 [−0.05, 1.07] (tie), 2022–26 era +0.92 [0.09, 1.75], 1000s +1.56; W 0.02 (tie); 52-week version −0.09 / −0.33 (ties) | "a lead, not an edge" | 25‑26; HIST; SUP | UFC/stageD.md |
| Profile16, FAA original audit | ridge, 4wk | 2019–26 M | onP +0.794 [0.126, 1.462]; beyond ratings + load +0.57 [+0.04, +1.09]; + age/surface +0.51 [−0.08, +1.10] (tie); profile + context +1.05 [+0.28, +1.82] | "main closing-line lead" | 25‑26; SUP → repairs | FAA/README.md; profile_notes.md |
| Profile16, ablations / levels | ridge onP | 2019–26 | serve style 0.308 [−0.040, 0.656]; games/bp 0.149; extra adjdef 0.219 (ties); Masters +1.780 [0.390, 3.169] | "no defensible 'winning statistic'" | 25‑26; SUP | FAA/profile_notes.md |
| **Profile16, repaired** | ridge, 4wk, dated cohort | 2019 to 13 Jan 2026 | onP +0.355 [−0.251, +0.961]; average +0.396 (tie); beyond line + context +0.364 (tie); 2022+ +0.273 (tie) | "interval includes zero" | 25‑26 | FAA/repairs.md |
| Profile16 vs ratings | onP | 2019–26 | +0.79 [+0.17, +1.42]; + TTT +0.00 | "orthogonal to every rating" | 25‑26 | RS/stageC.md |
| Profile16 linear (TT design) and across clocks (MT) | fit 2013–21 | 2022–26 M | TT +0.79 [−0.15, +1.74]; repaired 0.83 → 0.25; MT original +0.93 [−0.00, +1.86], leak-proof +0.93 [+0.00, +1.86], repaired +0.28 (tie) | – | 25‑26 | TT §Results; MT §7 |
| Profile16 anchored (MA) | ridge, market slope free | 2019–25 / 2026 | average +0.33 (tie); 2026 +0.91 [+0.08, +1.73]; profile + serve/return + context 2026 +1.38 [+0.08, +2.67]; W 2019–25 +0.26 (tie) | suggestion: a "market + nudges" frame | 25‑26 | MA/README §6.1–6.2 |
| Profile16 ridge refit (control) | ridge | 2013–26 M | 0.53 [0.13, 0.93]; 2022–26 0.90 [0.29, 1.51] | recheck on the repaired frame | 25‑26; HIST frame | SL/stage3.md §D |

#### Strength of schedule, revaluation, opponent-strength splits (HIST)

| Feature/arm | Test | Window | Result | Verdict | Flags | Source |
|---|---|---|---|---|---|---|
| sos_* (quality of wins, opponents' Elo/ratings, results above expectation) | onE, pm | 2013–26 | M −0.43 to −2.55 (worse); W quality of wins +0.95 [0.21, 1.69]; onM none clears the line | "does not help the men" | 25‑26 | UFC/stageC.md §1, §5 |
| revalue_* (credit for old opponents) | onE | 2013–26 | lost to M 0.16 [0.01, 0.30], W 0.41 [0.22, 0.60]; later-only 0.14 / 0.47; beaten −0.02 / −0.11; onM ≤ 0.11 | "insufficient reason" (FAA) | 25‑26; **LEAK** | UFC/stageC.md §2 |
| Split by opponent strength (vs weak, bottom third, contrasts, slope) | onE / onM | 2013–26 | vs bottom third M 1.18, onM 0.27 [0.09, 0.44]; contrasts −0.46 to 0.13; slope_tpw 52w M −0.083 [−0.129, −0.036] | "gap is chance"; "Do not reopen" | 25‑26; CSV for slope | UFC/stageB.md; stageB_ranking.csv |
| wins_over_strong / wins_over_weak | onE | 2013–26 | strong 52w M 0.022 (tie); weak 52w M −0.338 [−0.519, −0.157] | worse | 25‑26; CSV | stageB_ranking.csv |

#### Fatigue and workload (pm, HIST unless noted)

| Feature/arm | Test | Window | Result | Verdict | Flags | Source |
|---|---|---|---|---|---|---|
| sets_14d | onE / onM / onP | 2013–26 | onE M 1.63 [1.41, 1.84], W 1.87; onM 0.23 [−0.01, 0.48] / 0.29 (ties); onP M 0.19 (tie, above the Pinnacle line) | "form, not fatigue" | 25‑26 | PD/stage4.md; audit_stage4.md §8 |
| sets_7d | onM | 2013–26 | M 0.30 [0.05, 0.54]; lag: Stage 4 0.03 vs audit 0.38 [0.16, 0.60]; onP 0.25 (tie) | "vanish" disputed | 25‑26 | PD/stage4.md §7; audit P1 |
| minutes_14d / minutes_7d | onE / onM | 2013–26 | 14d M 1.51, W 1.59; 7d onM M 0.18 (tie) | W 2013–16 dropped by a post hoc minimum | 25‑26; CSV | stage4.md; audit P2 |
| prev_minutes / prev_sets / last_early / days_since | onE / onM | 2013–26 | prev_sets M −0.030 (worse); last_early 0.225 / 0.321; days_since 0.809 / 0.900; onM all ties | small | 25‑26; CSV | stage4_ranking.csv |
| played_52w / played_career | onE | 2013–26 | 0.96 / 0.65; career −0.449 / −0.599 | warm-up artefact | 25‑26 | UFC/stageC.md; CSV |
| Context block (sets 14d, surface first, age) | ladder | 2022+; repaired 2019+ | after everything else +4.90 [4.16, 5.64] / +3.93; repaired +4.618 / +3.914; given Pinnacle (original) +0.54 [+0.10, +0.97]; repaired +0.214 (tie) | "materially useful beyond Elo" | 25‑26 | FAA/elo_notes.md; README; repairs.md |
| Load, age and surface familiarity with odds (GAM) | spline GAM | 2022–26 | M +0.37 (tie); W +1.00 [+0.22, +1.79] | a free route for women | 25‑26 | TT §free model |
| late_decline (career) | onE / onM, pm | 2013–26 (W 2019–26) | onE M −0.03 [−0.10, 0.04], W −0.10 [−0.42, 0.22] (ties); onM W −0.19 [−0.35, −0.03] | "Fatigue: no sign"; "Close fatigue as a pre-match family" (suggestion) | 25‑26; HIST | UFC/stageC.md §3.1 |
| grinder (52 weeks / career) | onE / onM | 2013–26 | 52w M 0.52 [0.34, 0.71], W 0.51 [0.22, 0.79]; onM −0.09 / −0.10 (ties); career M −0.19 [−0.39, 0.00], W −0.11 [−0.21, −0.01] | "recent dominance … not stamina" | 25‑26; HIST | UFC/stageC.md §3.2 |
| PF recovery context (rest, absence × Elo, retirement losses) | ridge, 4wk, dated cohort | 2019+ | vs the strong Elo combination M +0.240 [−0.069, +0.548], W +0.143 (ties); vs Pinnacle + profile M −0.069, W −0.240 [−0.487, +0.006] (ties); vs average W −0.252 [−0.501, −0.003] | "no clear individual gain" | 25‑26; CSV for the average route | PF/README; D/predictive_frontier/results.csv |

#### Surface switching and surface statistics

| Feature/arm | Test | Window | Result | Verdict | Flags | Source |
|---|---|---|---|---|---|---|
| surface_first (A − B flag: fewer than 3 matches on the surface this season) | onE / onM / onP, pm | 2013–26 | onE M 1.45 [1.23, 1.67], W 1.30 [1.01, 1.58]; onM M 0.034 (tie), W 0.20 [−0.01, 0.41] (tie); onP W 0.12 (tie) | replaced 6 Oct by the switch pairs | 25‑26; HIST | PD/stage4.md; audit_stage4.md §8 |
| surf_season / surf_layoff / surf_career / surf_form_prev, beside offset Elo, no odds | linear, forward-chained | 2016–21 | season counts M +2.11 [+0.99, +3.23], W +3.66; layoff +1.70 / +1.93; form +0.17 [+0.00, +0.34] / −0.06; career counts M −0.75 [−1.41, −0.08] | "season counts and layoff inform; career counts and form do not" | ✗ | SEP/audit.md S1; README §2 |
| Same pieces with odds | linear | 2016–21 | career counts M −0.13 [−0.23, −0.04]; season counts W +0.41 [−0.01, +0.82] (tie); switch differences M −0.05, W +0.40 (ties) | "every piece ties" | ✗ | SEP/audit.md S1; strategy §4 |
| Inexperience / long layoff priced? (actual minus expected wins, percentage points) | vs Elo and vs market | 2013–21 | M ≤ 5 surface matches: −5.8 vs Elo, +1.5 (SE 2.5) vs recalibrated market; layoff > 400 days −14.1 vs Elo, −4.5 (SE 2.7) vs market | "the market prices it" | ✗ | SEP/audit.md S1, §3 |
| PF surface correction (4 inputs) | ridge, 4wk | 2019+ | vs the strong Elo combination M +1.119 [+0.451, +1.787], W +0.714 [+0.200, +1.228]; vs Pinnacle + profile M −0.134, W −0.055 (ties); anchored (MA) 2026 −0.46 (tie) | priced | 25‑26 | PF/README; MA §6.1 |
| Surface Elo blend; specialisation term (surface minus overall), given odds | MA harness, free market slope | 2019–25 / 2026 | blend +0.12 [+0.01, +0.23] (average), +0.12 [+0.02, +0.22] (Pinnacle); slope fixed at 1 "loses 0.46"; specialisation +0.03 [−0.07, +0.13] (tie) | "adds nothing given the close" | 25‑26 | MA/README §6.1, §6.3 |
| ss_dev12 / ss_surf12 / ss_level12 (12 surface deviations / surface levels / all-surface levels) | anchored | 2019–25 / 2026 | dev −0.08 (tie); surf +0.02 (tie), 2026 +0.72 [+0.00, +1.44]; level +0.020 (tie, CSV); surf beyond profile + context +0.04 (tie); no market, added to the nine inputs: surf +0.83 [+0.17, +1.49], dev +0.800 [−0.024, 1.623] (CSV) | "helps the market-free model … nothing given the close" | 25‑26 | MA §6.3; D/market_anchoring/surface_stat_results.csv |

#### Player background, rankings, head to head, format (pm; 25‑26; HIST)

| Feature/arm | Test | Window | Result | Verdict | Source |
|---|---|---|---|---|---|
| Age + age² | onE / onM; ladders | 2013–26 | onE M 1.42 [1.18, 1.65] (2022–26: 2.88), W 0.559 (CSV); onM M 0.128 [−0.077, 0.333] (tie); given BT 0.87; given TTT 2.79; FAA ladder 3.11 [2.56, 3.66] / 1.11; MA in-sample coefficient −0.072 (z −3.7) | "older men do worse than Elo expects"; given the price, "the older player does worse than priced" | PD/stage4.md; FAA/elo_notes.md; RS/stageB.md; MA §6.6 |
| rank / rank_points / rank_elo_gap / recent_level | onE / onM / onP | 2013–26; 2022–26 | onE rank M −1.67, gap −2.26, recent_level −2.48 (2022–26: rank +0.24, gap +0.15); onM W rank 0.32 [0.01, 0.62], onP 0.30 [0.02, 0.57]; W gap 0.27 [−0.01, 0.55] (tie) | "a flaw in the test's early seasons hides them" | PD/stage4.md §3, §6; audit_stage4.md §8 |
| Height / lefty / vs_hand | onE / onM | 2013–26 | height M 0.104 [−0.030, 0.237] (tie); lefty M −0.013 [−0.023, −0.003]; vs_hand M −0.022 [−0.044, −0.000]; W all ties; onM ties | background "2% / no" | CSV; PD/summary.md |
| Home country | onE / onM | 2013–26 | M 0.235 [0.152, 0.318]; W −0.325 [−0.470, −0.180] (worse); onM M −0.118 (tie) | – | CSV |
| Entry types (qualifier, lucky loser, wild card, protected ranking) | onE / onM | 2013–26 | Q M 0.402 [0.175, 0.628], W 0.351; WC M −0.061 [−0.093, −0.030]; PR M 0.079 [0.016, 0.143]; LL ties; W PR not scored; onM all ties | small | CSV |
| Head to head (5 forms) | onE / onM | 2013–26 | onE all ties; onM M surface −0.587 [−1.058, −0.116], adjusted −0.383 [−0.752, −0.013], career −0.224 [−0.423, −0.026] | "no / no"; FAA "stop" | CSV; PD/stage4.md §3 |
| best_of_five (Elo log-odds × best-of-5 flag) | onE / onM | 2013–26 M | onE 0.298 [0.182, 0.414]; onM 0.114 [−0.084, 0.312] (tie); scheduled best-of in TabPFN context: shuffle share 0.00 | "already inside the strength ratings" | CSV; PD/stage4.md §7; TT |

#### Clutch and pressure

| Feature/arm | Test | Window | Result | Verdict | Flags | Source |
|---|---|---|---|---|---|---|
| tb_won 52w (tiebreak record) | onE / onM | 2013–26 | M +0.14 (CSV 0.137 [−0.064, 0.337], tie), coefficient −0.045; W 0.231 (tie); onM ties; season reliability 0.06 | "reads as luck, not a trait" | 25‑26; HIST; CSV | PD/stage4.md §2; stage3.md |
| Deciding sets won | onE / onM | 2013–26 | 52w M 0.347 [0.039, 0.656], W 0.829 [0.383, 1.275]; onM M −0.039 [−0.076, −0.001] | possible / finding | 25‑26; HIST; CSV | stage4_ranking.csv |
| bp_over / bp_saved / bp_conv | onE / onM | 2013–26 | bp_over M constant (no spread), W ties; bp_saved 52w W 0.356 [0.122, 0.590]; bp_conv ≤ 0.072 | "mostly chance" | 25‑26; HIST; CSV | stage4.md; stage4_ranking.csv |
| bigpoint_return (Slam point-by-point files) | onE | 2013–26 | M 0.091 [0.002, 0.180], coefficient −0.043; W −0.008 (tie); onM ties | negative-sign luck correction | 25‑26; HIST; CSV | stage4.md §2 |
| In-match, NOT pre-match: tiebreak / break-point over-performance given the points share | 5-fold cross-validated logistic | analysed matches | tiebreaks +40.9 [39.6, 42.3] M (pure-luck replay 46.6); break points +2.9 (luck 3.0); persistence ≈ luck except M break points 0.11 and return big points 0.21 / 0.19 | "most of what looks like clutch play is what pure luck produces" | HIST | PD/stage2.md §2, §4, §7 |
| Shot-level pressure excess / holds after breaking / breaks back | onM / onE | 2013–26 | pressure excess onM M 0.02 (tie); W holds after breaking (opponent-adjusted) onE 0.37 [0.13, 0.61]; breaks back 0.35 [0.11, 0.60] | onM nothing | 25‑26 | SL/stage2.md |
| Conversion luck (holds and breaks above iid expectation) | anchored | 2019–25 / 2026 | −0.01 [−0.10, +0.09]; 2026 +0.28 (tie); beyond profile + context −0.11 (tie) | "Already tested and dropped" | 25‑26 | MA §6.6 |

#### Shot-level statistics (2013 or 2019–2026; 25‑26; the earlier studies' clock)

| Feature/arm | Test | Result | Verdict | Source |
|---|---|---|---|---|
| 141 features (own / conceded / opponent-adjusted × 3 memories) | harness onM | best: M first-serve speed change 0.06 [−0.02, 0.15]; W serves out wide 0.08 (ties); 0 of 280 rows clear the line | "Against the closing odds, nothing" | SL/stage2.md |
| Same, onE | harness | M first-serve speed 52w 0.36 [0.05, 0.67]; W winners per point (adjusted) 0.37 [0.12, 0.63]; all < 1 | "a little" | SL/stage2.md |
| Profiles (3–25 inputs) | unpenalised / ridge onM | unpenalised −0.06 to −0.75; beyond odds + box profile −0.32 to −1.30; ridge −0.16 to 0.09 | "losses were the fitting cost" | SL/stage2.md; stage3.md §D |
| Men's serve-speed profile | onM, wk | 2022–26 0.24 [0.07, 0.41]; ridge 0.12 [0.00, 0.24]; whole period 0.07 (tie) | "one direction to watch" | SL/stage2.md; stage3.md |
| Serve-point test (binomial, per serve point) | over ratings + box-score form | M 2022–26 0.012 [0.006, 0.018]; to match level onM −0.02 (tie) | small and recent | SL/stage3.md §A |
| Flexible learners (ridge, boosting on both players' values) | TT split | ridge shot inputs −0.03 (tie) vs box 1.01 [0.35, 1.67]; boosting shot +0.16 / +0.54 (ties) | "Little is method" | SL/stage3.md §B |
| Planted edges | synthetic | rules out 0.25–0.5 (M) for speed, errors and winners; 1–2 could hide in the noisy statistics | "no edge of a useful size" | SL/stage3.md §C |

#### Predictive-frontier families (dated cohort, ridge, 4wk, 2019+; 25‑26)

| Family | vs the strong 9-input Elo combination (M / W) | vs Pinnacle + profile + context (M / W) | Source |
|---|---|---|---|
| Own-expected form (pf_serve/return 28/182, momentum) | +1.549 [+0.824, +2.274] / +0.415 (tie) | −0.036 / −0.131 (ties) | PF/README |
| Reliability (evidence, uncertainty × Elo, instability) | +2.022 [+1.077, +2.968] / +0.476 (tie) | +0.232 [−0.038, +0.502] / +0.077 (ties); vs raw Pinnacle +0.864 [+0.048, +1.679] (secondary, selected) | PF/README |
| Event speed × style | +0.062 / +0.096 (ties) | +0.073 / −0.046 (ties) | PF/README |
| All five families; past-only selector | +3.679 [+2.414, +4.944] / +1.180 [+0.296, +2.065]; selector +3.432 / +0.951 | +0.011 / −0.212; +0.130 / −0.053 (ties); "None … excludes zero" | PF/README |
| 36 inputs in TabPFN-Thinking vs logistic (PFT, 2026 M) | +2.028 [−1.110, +5.166] (tie); both trail the close (0.594790) | – | PFT/README |

#### Stacking, calibration, early prices, venues (25‑26)

| Test | Result | Verdict | Source |
|---|---|---|---|
| Meta-model S2 (no-odds TabPFN + close) vs the current best | −1.15 [−1.76, −0.55] (current best better); S2 vs close +0.14 (tie); the difference as a third input: S3p +0.01, S3q −0.03 (ties) | "Keep the closing line inside the model" | MS/README |
| Current best + no-odds forecast (E1) / close given its own weight (E2) | −0.03 / −0.02 (ties) | – | MS/README |
| Stacking a market-free forecast on the price (MA; TT dry run) | −0.14 [−0.30, +0.02]; TT dry run +0.10 vs +0.79 entered directly | features, not probabilities | MA §6.1; TT §Design |
| Meta-labelling (36-input primary) | log loss 0.59024 vs market 0.59000 (worse) | "a sizing layer" | MA §6.5 |
| Recalibration slope per tour (local TabPFN) | vs close +0.53 → +1.20 [+0.51, +1.89]; walk-forward slope +1.30 [+0.65, +1.94]; Plus raw → recalibrated +0.65 [+0.18, +1.11] | "worth more than any input tested" | SI/README; SEP §5.4 |
| Odds-only calibration (cubic + Slam + best-of-5 slopes) | +0.30 M / +0.45 W over recalibrated odds | small | TT §diagnostics |
| Model fed the 24 h Polymarket price (SEP test 1, price move) | pre-registered +0.332 [+0.091, +0.574] (flawed specification); price-free +0.139 [+0.028, +0.251]; vs recalibrated 24 h price +2.85 [+0.14, +5.57]; vs raw price +2.12 (tie) | "not proven" | SEP §5.8 |
| Price move toward the model (SRR, LS) | β +0.107 [+0.040, +0.174]; LS slope +0.066 [+0.028, +0.102]; betting early vs close $0.00 per 100 matches (−0.86 to +0.91) | "same performance" | SRR §4; LS |
| Venues (de-vigged) | Betfair − Pinnacle −0.3 [−2.3, +1.6]; Polymarket − Pinnacle +0.3 [−4.9, +5.8]; average vs Pinnacle 0.7 [0.3, 1.1] worse (M) | ties | SB; PD/stage1.md |
| Whole model: TabPFN-Thinking, odds + 53 inputs | M +1.57 [+0.82, +2.32] (leak-proof refit +1.52 [+0.76, +2.27]); W +0.74 (tie); free models M +0.09 to +0.30 (ties) | "not interactions" | TT; TL |
| UFC "everything" (10 inputs) | onE 9.35 / 9.86; onM 0.31 / 0.32 (ties); + MESR 0.42 / 0.37 (ties) | – (LEAK) | UFC/stageD.md |
| Full history vs dated-only history, no odds | Elo +19.3 [+15.5, +23.1] (M); nine inputs +14.3; with odds all versions tie | "Keeping the whole history matters" | MT §7 |

### 3.2 Interaction terms already tested

* **Elo log-odds × best of five** (PD stage 4, men, 2013–26): onE 0.298 [0.182, 0.414]; onM 0.114 [−0.084, 0.312] (tie). Source: stage4_ranking.csv.
* **late_decline × best of five** (men): onE 0.02 [−0.17, 0.21]; onM −0.01 (tie). **late_decline × expected length** (`late_decline_x_long`): onE −0.03 (M) and −0.10 (W), both ties; onM W −0.23 [−0.41, −0.06]. Source: UFC/stageC.md §5.
* **grinder × best of five**: −0.01 (tie). **Load × fatigue trait** (`sets_14d_x_decline`, `minutes_14d_x_decline`): onE −0.02 to −0.06, onM −0.04 to −0.16, all ties. Source: UFC/stageC.md.
* **strong_gap_x_strong_opp** (the player's strong-minus-weak gap × whether today's opponent is strong): 52w M 0.017 [−0.062, 0.097] (tie), W 0.022 (tie); career M 0.173 [0.064, 0.282], W 0.251 [0.058, 0.445]; onM all ties, W 52w −0.046 [−0.091, −0.001]. Source: UFC/stageB.md; stageB_ranking.csv.
* **Within-player slope of performance on opponent Elo** (`slope_tpw`): M −0.083 [−0.129, −0.036] and career −0.201, worse. Source: stageB_ranking.csv.
* **IOS offence × defence products (`prod_*`)**: profile + 7 products onM M −0.21 (tie) vs −0.06 without products. Per-surface products (R1, sprof) tie with odds and help men without odds (+0.83). FAA: "Do not expand … merely because interactions are available". Source: UFC/stageD.md; SI.
* **TabPFN's learned interactions**: 2% of its adjustment's variance. Surrogate gains: additive +1.28, with interactions +1.35, linear part alone +0.94 (men). Boosting with interactions (odds + 53) M +0.30, W −0.55 (ties); without odds, interactions add −0.24 / −0.20. Match context (surface, level, best of, round) carries 0.00. Source: TT.
* **Boosting on both players' values (matchups)**, shot level: +0.16 / +0.54 (ties). Source: SL/stage3.md §B.
* **Long-rally edge where long rallies are likely** (`rally_edge|x_long|w52`): onE M −0.063 [−0.208, 0.082] (tie), W −0.320 [−0.487, −0.154]; onM M −0.095 [−0.181, −0.008], W −0.082 (tie): worse. Source: CSV, `data/studies/shot_level/stage2_ranking.csv`.
* **Predictive-frontier terms × Elo or serve/return strength**: `pf_uncertainty_elo`, `pf_uncertainty_sr`, `pf_instability_elo` belong to the reliability family, the best of the five (table above); the other `*_elo` and `pf_event_speed_style` terms (recovery, event speed, surface, innovations): no clear gain beyond the market model. Source: PF; frontier_features_summary.json.
* **Odds × context** (MA): odds × early season / best of 5 / surface / level slopes +0.12 [−0.08, +0.32] (2019–25; +0.62 in 2026); on top of profile + context +0.31 [+0.003, +0.62] (2019–26). **Odds × both players new to the surface** (SEP): −0.03 (M) and −0.03 (W), ties.
* **Disagreement-size term** (meta-stack S3q): −0.03 [−0.09, +0.02] (tie). **A separate model per surface** (a full surface interaction): −0.28 [−0.77, +0.21] (tie).
* **Lefty vs right-hander; record against the opponent's hand**: M −0.013 and −0.022, both just below zero. **Age²**: tested only inside the age pair.

### 3.3 Families held in the data with no test result found

* WTA API win probability and momentum (2025–26).
* IBM SlamTracker likelihood-to-win, pre-match likelihood, key moments, distance run, limb tracking, TennisViz.
* Court Vision / Hawk-Eye ball tracking and trajectories (shot level: "not decoded"; "too thin to test").
* Flashscore per-set statistics; ATP per-set and season-to-date statistics; the 2,147 website-only charts.
* Polymarket trade flow, sharp-account positions and order-book depth as features (measured only as market descriptions).
* Betfair tick data (not on disk).
* Indoor vs outdoor hard as its own surface (deferred; only an unscored context column).
* Actual match times, real rest hours, weather, altitude, ball changes, travel (PF register entries C01–C07).
* Untested PF register ideas: A12, the S_A·R_B − S_B·R_A cross term; A13, uncertainty integrated through the iid model; A14, completion risk; A16, market surprise vs point surprise; B01, B02 and B05: unreturned serves, serve direction × return weakness, serve-plus-one.
* Any feature test on Challenger, ITF or other lower-tier markets: every market test covers the main tour only.
* *Added by this map (observed, §4):* the one-handed backhand (TML, men), comebacks and set-by-set momentum from score strings, rank trajectories and points to defend, start time of day, dispersion between books (Max vs Avg vs Pinnacle), women's indoor from tennis-data.co.uk.

### 3.4 Contradictions and tensions between reports

1. **Load features one match later.** Stage 4 says the load features' small gains over the market "vanish" (men's sets over 7 days 0.30 → 0.03; PD/stage4.md §7). The Stage 4 audit's alternative lag keeps them (0.30 → 0.38; PD/audit_stage4.md P1).
2. **"Recent form beats opponent adjustment."** PD/stage4.md §2 claims it. FAA/elo_notes.md item 2 says the comparison is confounded, because the adjusted form used career sums. UFC stage B's two-week adjperf beats both.
3. **"Best 2026 model" means two things.** In MA/README it is the 36-input model without odds; in TT, TL and MT it is the Thinking fit on odds + 53 inputs.
4. **The odds-based rating is called untested but was tested.** DEC/2026-10-03 lists "a rating built from players' past closing prices" as untested; UFC/stageA.md tested MESR, which is that rating.
5. **Surface Elo given the close.** MA §6.1: +0.12 [+0.01, +0.23] (repaired frame, free market slope). RS/stageC.md: +0.02 [−0.01, +0.05]; SEP/strategy.md: −0.06 (ties).
6. **Offset Elo given odds, and the surface-blind control.** SEP/README §3 gives "−0.03 / +0.01" for the former where strategy.md §4 gives −0.09 / +0.06; for the control the README gives +6.44 / +4.61 and audit.md +5.97 / +9.16 / +5.00 / +4.66. Neither pair is reconciled in the text.
7. **Profile16's linear gain on the men's 2022–26 test.** TT +0.79, its repaired check +0.83, MT +0.93: three different matched sets.
8. **Thinking fit against the close.** TL B +1.18, SEP +1.22, SI +1.19; SI attributes the gap to per-window recalibration.
9. **SEP's +2.85 at the 24-hour price** is against the recalibrated price; SRR §4: against the raw price +1.84 (tie), "Recalibrating the price makes the baseline weaker".
10. **Unpenalised profile results are understated.** SL/stage3.md shows the unpenalised fit costs about 0.5 mLL per 10 inputs; UFC stage D and SL stage 2 profile numbers should be read with that in mind.
11. **"Finding" labels on rows whose interval spans 0** in PD/UFC (e.g. men's tb_won 52w, height). The repairs relabelled the shuffled-copy threshold "descriptive heuristics"; interval types changed on 2 Oct, 16:48, from per-match to four-week blocks (RS/stageB.md).
12. **The men's profile verdict was reversed.** FAA/README: "the main closing-line lead" (+0.79 [+0.13, +1.46]); FAA/repairs.md: +0.355 [−0.251, +0.961]; UFC: "positive in every season from 2020 on"; FAA/profile_notes.md: −7.234 on the 71 Pinnacle-priced matches of 2026.
13. **Stage 4's 3.05 is 3.04 in its data file** (PD/summary.md).
14. **Unfilled placeholder**: DEC/2026-10-06-offset-elo.md still contains "[COMPOSITION]".

## 4. (d) Raw data not yet turned into features

Every row: path, columns, coverage on the model population (men 13–21 / women 13–21 / men 22–24 / women 22–24, %), caveats. Stage 0 paths are the pre-rebuild copies (`data/studies/data_continuity/rebuilds/2026-10-07T0005Z/replaced/data/studies/...`); the live tables are identical on these matches except where §5.3 says otherwise.

### 4.1 Per-player biography, rank and entry

| Field | Path: columns | Coverage % (both players) | Caveats |
|---|---|---|---|
| hand | `predictability_diagnostic/stage0_match_players.parquet: hand` (R, L, U) | 99.9 / 99.4 / 100 / 97.9 | a left-hander plays in 26% of men's and 16–18% of women's matches; used once as Stage 4 `lefty\|single`, `vs_hand\|single` |
| height | same: `height` (cm) | 99.7 / 93.8 / 99.9 / **64.4** | women's heights thin after 2021 |
| country | same: `country` (IOC) | 100 / 100 / 100 / 100 | same-country matches 5–7%; event country table `predictability_diagnostic/stage4_event_country.csv` (837 rows; 54 of 63,941 tennis-data-linked matches disagree; one unresolved "Kingston") feeds Stage 4's `home\|single` |
| age at match / birth date | same: `age`; birth dates in `data/dump/players/sackmann_archive/{atp,wta}/*_players.parquet: dob`, TML `ATP_Database.parquet: birthdate` | 100 / 100 / 100 / 100 | |
| backhand (1H/2H), weight, turned pro (**men only**) | `data/dump/players/tennis_my_life/ATP_Database.parquet: backhand, weight, turnedpro` | *observed* (joined here by normalised name + birth date to Sackmann's players, 79% of TML rows): backhand 95.5 / – / 94.3 / –; weight 96.1 / – / 94.6 / –; turned pro 94.4 / – / 88.7 / – | TML's `id` is mostly an ATP code, not Sackmann's id (1.9% match); one-handed backhands in 16% of men's player-rows (8,817 of 54,578); static, current values (weight is not at match time); no women's equivalent held (`backhand.py`, `backhand_join.json`) |
| rank, rank points | `stage0_match_players: rank, rank_points` | 99.7 / 99.6 / 99.8 / 99.5 | weekly rankings 2010 – 8 Jun 2026: `data/dump/rankings/sackmann_archive/{atp,wta}/*.parquet` (WTA adds `tours`, events counted); one TML snapshot of 31 Aug 2026. Rank trajectories and points to defend are not built |
| seed | `stage0_match_players: seed` | at least one seed: 62.3 / 60.9 / 61.4 / 60.6 | missing = unseeded |
| entry | `stage0_match_players: entry` | at least one non-direct entrant: 34.7 / 34.0 / 37.9 / 37.8 | player-rows (2013–24 model matches): Q 12,244, WC 6,583, LL 2,049, PR 483, SE 190, SR 79, ALT 63. Stage 4 built `entry_q/ll/wc/pr\|single` |

### 4.2 Match facts (history only: they describe a finished match)

| Field | Path: columns | Coverage % | Caveats |
|---|---|---|---|
| minutes | `stage0_matches: minutes` | 93.3 / 63.8 / 96.9 / 96.1 | women 2013–15 ≈ 0; men 2015 52%; 2022 and 2024 ~95% |
| score string | `stage0_matches: score`, `score_flag`, `status`, `status_detail` | 100 / 100 / 100 / 100 | gives set-by-set games, tiebreak scores, deciding sets, comebacks (lost the first set and won), bagels; **comebacks and set-level momentum are not built** |
| tiebreaks, sets, games per player | `stage0_match_players: tb_won_n/d, sets_won_n/d, games_won_n/d` | 100 / 99.99 / 100 / 99.9 | a tiebreak in 38.8 / 21.8 / 40.1 / 23.5% of matches; Stage 4 built `tb_won`, `deciding`, `sets_won`, `games_won` forms; the live rebuild changed tb/games counts of 7,597 history rows (match-tiebreak repair) |
| retirements | `stage0_matches: status` | share retired: 3.0 / 2.9 / 2.6 / 3.3 | the model population includes retired matches |
| box score counts | `stage0_match_players: ace, df, svpt, first_in, first_won, second_won, sv_gms, bp_saved, bp_faced` (+ `_n/_d` rate pairs) | any box: 99.9 / 94.4 / 100 / 99.5; service games: 99.9 / **69.9** / 99.9 / 99.2 | women's `sv_gms` missing 2013–14, 64% in 2015, 85% in 2017 |

### 4.3 Event metadata

| Field | Path: columns | Coverage % | Caveats |
|---|---|---|---|
| draw size | `stage0_matches: draw_size` | 100 all | |
| **indoor, both tours** | tennis-data.co.uk raw rows: `Court` (Indoor/Outdoor); join `stage1_odds.td_file` + `td_row` = the row's **position** in the file (not `_row`) | 100 all | *observed:* agrees with Stage 0's men's indoor on 99.2% of 27,289 matches; indoor share 18.2 / 9.4 / 16.2 / 5.9%. Fills the women's gap in the model's `indoor` |
| city | tennis-data `Location` | 100 all | home advantage needs player country × event country (the Stage 4 table above); **altitude, climate, ball brand and court speed are not held** (altitude would need an external gazetteer; court speed from field statistics needs the leak-proof clock) |
| tournament id and name, level, surface, round, best of | `stage0_matches` | 100 all | |

### 4.4 The match clock (`match_timing/timing.parquet`, pre-rebuild copy)

| Field | Columns | Coverage % | Caveats |
|---|---|---|---|
| earliest start, latest finish | `es`, `lf` (days since 1970), `obs` (best estimate), `width_days`, `exact`, `window_basis`, `n_sources`, `conflict` | 100 all | windows of 1 day: 8.5 / 20.5 / 16.6 / 86.3%; most others 2 days (UTC-dated sources). A result counts from `lf + 1`; a match reads the state at `es` |
| rest before the match (derived here) | `es` (this match) − `lf` (the player's previous match, any level, Stage 0's order) | 100 all | minimum rest per player-match: median 2 days, 5% at 0, 95% at 23; previous and current matches both exact: 97.8 / 88.1 / 99.9 / 98.5% |
| start time of day | `start_utc` in `match_timing/links/{flashscore, api_tennis, live_tennis_api, sofascore, slam_feeds, wta_api, tdi, match_charting}.parquet` | 99.4 / 75.4 / 100 / 100 | UTC; some are scheduled rather than actual starts; local time needs the venue's time zone (`src/eda/match_timing/srcc_tz.py`, `flashscore_tz.py`) |

### 4.5 Odds beyond the average close

| Field | Path: columns | Coverage % | Caveats |
|---|---|---|---|
| Pinnacle close | `stage1_odds: ps_a, ps_b, p_ps_a, overround_ps` | 99.6 / 99.5 / 99.7 / 99.5 | |
| best price across books | `stage1_odds: max_a, max_b` | 100 all | dispersion between books = Max against Avg (or Pinnacle) implied probability |
| Bet365 close | `stage1_odds: b365_a, b365_b` | 99.7 / 99.7 / 99.9 / 99.7 | |
| Expekt, Ladbrokes, Stan James | raw `EXW/EXL`, `LBW/LBL`, `SJW/SJL` | EX 67.1 / 71.5, LB 65.6 / 69.0, SJ 26.1 / 23.0 (2013–21); **0 in 2022–24** | stop in 2018 |
| **Betfair exchange** | raw `BFEW/BFEL` | **0 / 0 / 0 / 0** | only in the 2025 and 2026 files: the closed test years. Unusable for discovery |
| opening or early prices | not in tennis-data.co.uk | – | Polymarket price paths exist for 2025–26 only (`line_sharpening`, `sharp_benchmark`): closed years |

### 4.6 Point-by-point and shot-level data

| Field | Path | Coverage % | Caveats |
|---|---|---|---|
| any point-by-point record | `shot_level/stage0_source_matches.parquet` (`n_points > 0`) | 25.6 / 22.8 / **90.2** / 27.3 | men 2022–24 from ATP Infosys (66%) and Court Vision (38%); before 2022 mostly Slam point files (18%) and the Match Charting Project (9% / 7%) |
| **point sequences (server and winner of every point), new study in progress** | `data/studies/point_sequence/sequences.parquet` (`match_id` in the model frame's pre-rebuild ids, `tier`, `usable`, `set_no`, `game_no`, `pt_no`, `is_tb`, …); builder `src/eda/point_sequence/build.py` (another session, files rewritten 17:47–18:09 on 6 Oct, no report yet) | *its own `coverage_model.csv`, read at 18:09, not verified here:* own sequence 88.4 / 60.7 / 95.4 / 98.9; both players with ≥ 20 earlier sequenced matches 96.4 / 53.0 / 90.4 / 92.8 | adds the WTA umpire logs, SofaScore, Sackmann's point-by-point and other sources to the shot-level study's eight; women's coverage rises from 15% (2013) to 87% (2019) and 99% (2020–24). No shot detail. **Mid-build: read only, re-check before use** |
| rally length | same, `has_rally` | 18.9 / 17.2 / 64.0 / 24.4 | |
| how points end | `has_ending` | 25.6 / 22.8 / 74.5 / 96.3 | women 2021–24 add the WTA's match totals (`wta_advanced`, 74–78% of women's matches; no points) |
| serve speed | `shot_level/stage1_match_stats.parquet: spd1_n/d, spd2_n/d` (both players) | 12.1 / 11.7 / 57.8 / 15.6 | by season, men: 11–25% to 2021, 57%, 63%, 77% in 2022–24 |
| net play, placement, return depth, strokes | `has_net`, `has_placement`, `has_return`, `has_stroke` | net 22.3 / 18.6 / 69.6 / 21.2; placement 14.9 / 12.8 / 32.7 / 26.0 | |
| ball tracking | `has_tracking` | 1.0 / 0 / 45.5 / 8.3 | |
| per-player shot statistics with history | `shot_level/stage3_sides.parquet` (`A\|<stat>\|<side>\|<form>`, `\|has`) | 52-week forms, both players with real data: serve speed 60.5 / 59.6 / 95.3 / 84.1; rally ≤ 5 shots 64.6 / 60.1 / 96.3 / 87.2; winner rate 87.2 / 83.9 / 96.7 / 93.3 | plain values are **prior-filled** for players without data: use the `\|has` flags (`coverage_shot_sides.csv`) |

Per season (all model matches, %; `coverage_by_season.csv`):

| Tour | Season | Box score (both) | Service games (both) | Minutes | 1-day clock window | Point-by-point | Serve speed |
|---|---|---|---|---|---|---|---|
| men | 2013 | 100 | 100 | 100 | 7 | 16 | 13 |
| men | 2015 | 100 | 100 | **52** | 6 | 24 | 13 |
| men | 2017 | 100 | 100 | 99 | 8 | 24 | 13 |
| men | 2019 | 100 | 100 | 100 | 12 | 35 | 11 |
| men | 2021 | 100 | 100 | 100 | 13 | 36 | 25 |
| men | 2022 | 100 | 100 | 95 | 18 | 92 | 57 |
| men | 2024 | 100 | 100 | 95 | 15 | 91 | 77 |
| women | 2013 | 88 | **0** | **0** | 4 | 15 | 13 |
| women | 2014 | 91 | **0** | **0** | 4 | 21 | 14 |
| women | 2015 | 77 | **64** | **0** | 3 | 23 | 14 |
| women | 2016 | 100 | 100 | 100 | 3 | 14 | 10 |
| women | 2017 | 100 | 85 | 99 | 4 | 19 | 13 |
| women | 2019 | 100 | 100 | 100 | 45 | 32 | 12 |
| women | 2021 | 99 | 98 | 98 | 81 | 29 | 18 |
| women | 2022 | 99 | 98 | 95 | 85 | 30 | 16 |
| women | 2024 | 100 | 100 | 94 | 87 | 27 | 15 |

## 5. (e) Joining per-player values to model-frame rows

### 5.1 The A/B convention (observed)

* Stage 0 sets side A by a hash: the lower-sorted player id is A when one bit of SHA-256(match_id) is 0 (`predictability_diagnostic/common.side_is_low`). Reproduced on a 20,000-match sample: 100%.
* The model frame's A is Stage 0's `player_a_id` (pre-rebuild): `a_won` identical on all 55,144 matches of 2013–2024, and the market probability, age, Elo and surface-IOS inputs match value for value (§1.2).
* Tables with `_a`/`_b` columns keyed by `match_id` use the same A:
  * checked exactly for `surface_elo_pieces/pieces`, `surface_ios/surface_features`, `stage1_baselines` (to float32), `stage1_odds`, and `shot_level/stage3_sides` (its `p_serve_a` equals `stage3_ratings`' value for value); `stage2_matches.player_id_a` is `player_a_id` in 100% of rows;
  * by strong positive correlation for the rest: with `in_elo_overall`, `surface_rating_race/ttt_offset` (0.976), `rating_systems/stageA_ratings` Glicko-2 (0.986) and `ufc_ideas/stageA_bt` (0.970); with `in_iosO_ace`, the weekly `ufc_ideas/stageB_ios` (0.995); with `in_odds_logit`, `ufc_ideas/stageA_mesr` (0.903).
* Tables with one row per player-match carry `side`: `side == "A"` is `player_a_id` in 100% of rows of `stage0_match_players`, `ufc_ideas/stageB_adj`, `shot_level/stage1_match_stats`.

### 5.2 The match ids after the rebuild (observed)

* The Stage 0 rebuild of 6 Oct (started 17:05 local, finished 17:35, `rebuilds/2026-10-07T0005Z/rebuild.json`, `ok: true`) re-keyed **42 matches**, all in 2026 (41 women's, 1 men's qualifying), listed in `id_map.csv`. 40 are model-frame matches (women's 2026). None is in 2013–2025.
* Because side A depends on the match id, **side A changed player in 21 of those 40** (example: `wta|2026-2017|R16|...` had Iga Swiatek as A, the new id has Emma Navarro as A).
* The live `timing.parquet`, `leakproof_features`, `perplayer_features` and `ios_features` (rebuilt 17:09–17:19) lack those 40 old ids; the pre-rebuild copies have all of them.

### 5.3 What else the rebuild changed (observed, `rebuild_diff.py`)

* On the 2013–2024 model matches: no id, side, result, score, rank, bio or box-score change; **7 `minutes` values** differ.
* On the whole history to 2024 (787,039 matches, every level): **38 matches with new player ids** (identity repairs, 76 player rows), 75 minutes values, and the tiebreak and game counts of 7,597 player rows (15,194 `tb_won_d`/`games_won_d` values; the match-tiebreak repair). A per-player feature rebuilt from the live tables can therefore differ slightly from the model's.
* 660 matches were added (2026).

### 5.4 The safest join path for a study tied to the frozen model frame (suggestion)

1. **Key on the model frame's `match_id`**, never on names. Restrict to `season <= 2024` for every exploration step.
2. **Per-player values:** prefer, in this order, (a) the per-player tables built from the same Stage 0 version as the model (`surface_ios/surface_features`, `surface_elo_pieces/pieces`, `stage3_ratings`, `stage1_baselines`, `surface_rating_race/ttt_offset`, this study's `perplayer_form_2013_2024` and `perplayer_load_2013_2024`); (b) per player-match rows via `side` (`"A"` = model A).
3. **Anything rebuilt from Stage 0 or the clock:** read the pre-rebuild copies in `data/studies/data_continuity/rebuilds/2026-10-07T0005Z/replaced/data/studies/` (SHA-256 in its `manifest.json`), and record their hashes in the harness. Rebuild any cross-player feature on the pre-rebuild `timing.parquet` and run `src/eda/match_timing/probe.py` on it.
4. **New inputs must be registered with the model's flip**: differences in `ANTISYMMETRIC` (negated), pairs in `SWAP` (`src/eda/surface_rating_race/arms.py`, `src/eda/surface_elo_pieces/arms.py`), symmetric terms (sums, products of two differences, context) left unchanged.
5. **For the final 2025–26 test only:** either keep the pre-rebuild tables throughout, or map the 40 re-keyed ids with `id_map.csv` and flip the 21 whose side A changed (negate differences, swap pairs) before joining live tables.

### 5.5 The current model's own out-of-sample forecasts (observed: files only, not read for outcomes)

The screen the team plans ("beyond the best model's own forecast") needs the 58-input model's walk-forward forecasts. They exist as `data/studies/surface_rating_race/local/model__<season>__seed<k>.npz` (written 17:17–17:28 on 6 Oct; also `model_noodds__*`, `sprof__*`, and the race's other arms) for **seasons 2019–2026 only**, seeds 0–2, each with `ids_td` (the season's match ids) and `p_td` (raw, uncalibrated forecasts for the matches as stored, then with A and B swapped; 2 × 5,045 values in 2019). The race produced **no forecast for 2013–2018**; with those alone, a screen inside the discovery window covers 2019–2021 only (12,105 matches: men 6,312, women 5,793). *Observed at 18:10:* this study's own earlier folds are being written to `data/studies/feature_interactions/local/model__<season>__seed<k>.npz` (2014–2017 present; log `local_fits_model_2014_2019.log`). 2013 has no earlier training season. The per-tour calibration slope and the symmetrisation are applied by `src/eda/surface_rating_race/score.py`.

A minimal join (2013–2024):

```python
OLD = "data/studies/data_continuity/rebuilds/2026-10-07T0005Z/replaced/data/studies/"
mf = pd.read_parquet("data/studies/surface_rating_race/model/model_frame.parquet")
mf = mf[mf["season"] <= 2024]
sf = pd.read_parquet("data/studies/surface_ios/surface_features.parquet")          # per player: _a / _b
fp = pd.read_parquet("data/studies/feature_interactions/inventory/perplayer_form_2013_2024.parquet")
p = pd.read_parquet(OLD + "predictability_diagnostic/stage0_match_players.parquet")  # per player-match: side
x = (mf.merge(sf, on="match_id", how="left", validate="one_to_one")
       .merge(fp, on="match_id", how="left", validate="one_to_one")
       .merge(p[p["side"] == "A"].add_suffix("_A").rename(columns={"match_id_A": "match_id"}), on="match_id", how="left")
       .merge(p[p["side"] == "B"].add_suffix("_B").rename(columns={"match_id_B": "match_id"}), on="match_id", how="left"))
```

## 6. (f) Pitfalls

**Data defects** (doc: [data continuity](../../data_continuity/README.md) §"In short", unless marked observed)

* **Women's aces and double faults from Tennis My Life, December 2024 – February 2026, are wrong** (in 2025 only 57% of ace and 18% of double-fault counts agree with Sackmann; the official records side with Sackmann). Stage 0 prefers Sackmann where both exist; *observed:* every 2013–2024 model match is Sackmann-sourced. The exposure is the closed 2025–26 seasons and, through the histories, the profiles of early 2026.
* **Men's Slam first serves from TML have been wrong since about August 2025** (second serves recorded as first: US Open 2025 62.2% vs 58.8%; AO 2026; Wimbledon 2026). The 6 Oct rebuild replaced Wimbledon and US Open 2026 counts with the official feeds (731 rows). **Sackmann's own Roland Garros men's qualifying 2022–2025 has the same fault** (65.2–68.6% first serves in) and is in the training history, flagged not changed; Roland Garros 2022 men's main draw reads ~66% in both sources, unverified.
* **Women's service-game counts** missing 2013–14, 64% in 2015, 85% in 2017 (observed): every hold, break, break-points-per-game feature for women is thin before 2016. Model inputs affected: `form_hold`, `form_brk`, `form_bp_faced_pg`, `formdef_bp_faced_pg` (women 74% in 2013–21).
* **Minutes**: women 2013–15 ≈ 0%, men 2015 52% (observed). Minutes-based fatigue features (Stage 4 `minutes_7d/14d`, `prev_minutes`; UFC-ideas `grinder`, `late_decline`) inherit the holes.
* **The men's 2018 season has no odds file**: not in the model population; men's walk-forward folds skip it.
* **Indoor is missing for every women's match** in Stage 0, so the model's `indoor` is a men-only input; tennis-data.co.uk's `Court` covers both tours (observed, §4.3).
* **Height** for women 2022–24 only 64% (observed).
* **Betfair exchange odds only in 2025–26; Expekt/Ladbrokes/Stan James only to 2018** (observed).
* **The 2026 women's players re-appearing under new ids from June 2026** have no history (73 test matches; the `debut_season` flag removes them from scoring; doc: `surface_elo_pieces/build_frames.py`). The splice also split 86 men's identities (doc).

**Rebuilds in progress today**

* The Stage 0 rebuild and its chain (Stage 1 odds, the clock, the per-player and IOS inputs, TTT) **finished at 17:35** with `ok: true`; `ttt_timed.parquet` was rewritten at 17:35 on the new ids (873,364 rows). The GPU job `src/eda/surface_rating_race/local_fits.py --arms model,sprof,model_noodds,sprof_noodds` (started 17:16) had also finished by 18:05. The frozen model frame (written 17:17) was built from pre-rebuild sources only.
* **Still moving at 18:09:** another session's new `point_sequence` study (`src/eda/point_sequence/`, `data/studies/point_sequence/`) was rewriting its tables (`sequences.parquet`, `coverage_model.csv`). It expresses its links in the pre-rebuild ids and flips the 21 re-keyed matches itself (its `build.py` docstring). Treat its numbers as provisional until it publishes a report.

**Leaking features** (CLAUDE.md; decision 2026-10-05; column-level reading from the code survey)

* Weekly IOS, `src/eda/ufc_ideas/stageB_ios.py`: the tables `stageB_ios*`, the `ios_*`/`prod_*` columns of `stageB_features` and `stageD_*`, and `ios_short|single` in `rating_systems/stageB_features`.
* `ttt_pass`: `p_ttt*` and `ttt|single` in `rating_systems/stageA_ratings` and `stageB_features`, and `stageA_ttt_hold`.
* Bradley–Terry and MESR: `ufc_ideas/stageA_*` and the `bt*`/`mesr*` columns of `stageD_features`.
* The SOS revaluation: the `revalue*` columns (`ufc_ideas/stageC_sos_part`, `stageC_features`, `stageD_features`).
* **Unsettled.** `sos_*` and `over_elo*` come from the same script, but the code reads only opponents' pre-match ratings; probe them before use. The predictive frontier's `pf_event_*` court-speed terms are a field statistic on their own strictly-earlier-day clock, never run through `probe.py`.

**Provenance traps** (observed or code)

* **The frozen model frame mixes data versions.** Its 31 inherited inputs come from Stage 4 and UFC-ideas tables (pre-rebuild Stage 0, pre-repair code). The 21 surface-IOS inputs and `ios_points_short` come from rows with the repairs applied, on the pre-rebuild clock. The Elo pieces come from the pre-rebuild Stage 0. A new per-player feature should state which version it reads.
* **Stage 4's matchup inputs** (`ratings_iid`, `points_52w`, the `mu_*` family) took best of five from the match's own score in the pre-repair code. On the 2013–2024 model rows, recorded and scheduled best-of agree everywhere (observed), so the model's values are unaffected there; `best_of_five|single` itself reads the score.

**Scale and meaning traps** (observed or code)

* **Polarity.** For `df` and `bp_faced_pg`, a higher *offence* (or `form_`) value means more double faults / more break points faced: bad for the player. `D`/`formdef` are defences: higher = better at suppressing the opponent.
* **Shrinkage.** Return-skill profile values (`form_brk`, `form_bp_conv`, `form_rpw_*`, all `formdef_*`) are shrunk with K3 = 160 and have standard deviations of 0.015–0.02, against 0.16–0.26 for the serve-side ones; products with them are tiny unless rescaled.
* **Prior-filled values.** IOS and the profile give every player a value (the prior, 0, without evidence); `shot_level/stage3_sides` fills a prior and flags real data with `|has`.
* **Clock imprecision, not leak.** The per-player features' windows and decays (14 days, 2-week half-life, 52 weeks) count from event start dates; a same-event earlier round has age 0. The clock's windows are mostly 2 days wide for men (UTC-dated sources), so rest computed from it is a bound.
* **`match_timing/perplayer_features.parquet` holds differences**, not per-player values, and differs slightly from the model's inputs (§1.2).
* **Results that used the closed seasons.** Most earlier studies headline 2022–2026. Their numbers (§3) already include the 2025–26 seasons this study keeps closed; using them to pick ideas is a forking path for the meta-auditor to weigh. Where a study reports design-year (2013–2021 or 2019–2021) results, §3 gives them.

## 7. Files of this round

Scripts (read-only on shared data), `src/eda/feature_interactions/inventory/`:

| Script | Writes (`data/studies/feature_interactions/inventory/`) |
|---|---|
| `schemas.py` | `schemas.json`: every study table's rows and columns |
| `orientation.py` | `orientation.json`: the A/B checks and the rebuild's id changes |
| `coverage.py` | `coverage_all.csv`, `coverage_model_and_raw.csv`, `coverage_feature_tables.csv`, `coverage_by_season.csv`, `raw_values.json` |
| `perplayer_form.py` | `perplayer_form_check.json`, `perplayer_form_2013_2024.parquet` |
| `perplayer_load.py` | `perplayer_load_check.json`, `perplayer_load_2013_2024.parquet` |
| `rebuild_diff.py` | `rebuild_diff.json` |
| `shot_sides.py` | `coverage_shot_sides.csv` |
| `backhand.py` | `backhand_join.json`: TML's ATP database joined to Stage 0's men by name and birth date |
| `registry.py`, `build_inventory.py` | `data/studies/feature_interactions/inventory.csv` |
| `md_check.py` | (lints this file's tables) |

All scripts read the frozen model frame and, for Stage 0 and the clock, the pre-rebuild copies. 2025–26 rows are used only for row counts and, in `orientation.py`, for the id and side-A check of the 40 re-keyed 2026 matches (identities only: no result, odds or feature value).
