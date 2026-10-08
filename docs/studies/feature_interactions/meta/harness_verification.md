# Harness verification (M1)

6 October 2026, 20:55–22:05 (local). The harness verifier: a fresh agent that did not write the harness (plan.md, M6). Research evidence, not a decision. Every score below carries its direction; "tie" when an interval spans zero.

**Verified versions** (SHA-256, first 16 hex): `screen.py` 8ddd8330bb0faee6, `screen_batch.py` 0227595c8561e7ff, `panel.py` 56b4a6f5f495dd0b, `history.py` c26b51b4e2ae6b05, `arms.py` 0e407859cb9dff60, `local_fits.py` 89196190c04a2968, `common.py` 2e1e7e4b285f32d3, `tabpfn_tests.py` 9bc8a61061ffdbed (read, not simulated), `features/p3_known_null.py` 8135cd2b18a83058, `features/levels.py` bfec9e141dfc31e9; tests `test/feature_interactions/` (22 pass). `screen_batch.py` changed at 21:34 during the verification (now 975324c8ba015709: the `x_of_eta` path and `s2_row`, H-S2 as a family member); both additions were read (B14 below), the simulations do not depend on them, and B4, B5 and B13 still apply. Any later edit is not covered.

**What read results.** Only task 3 (the design effect): real 2014–2024 results with randomly generated features, ledger row 11. Every planted-effect, false-positive, P2, Wald, effect-size and timing run drew synthetic outcomes; the frame's `a_won` was overwritten before any fit.

**Scripts** `src/eda/feature_interactions/verify/` (`integrity.py`, `history_order.py`, `multiplicity_check.py`, `cols.py`, `simlib.py`, `planted.py`, `planted_wald.py`, `p2_check.py`, `sizes_check.py`, `design_effect.py`, `timing.py`, `summarise.py`, `report_tables.py`); outputs `data/studies/feature_interactions/verify/` (`*_smoke*`, `p2_UFIX_cal*` and `p2_UFIX_t010` are smoke tests and a superseded first P2 design with the trait held fixed across draws; not used below).

## Verdict: sign off with fixes

* **The statistical core holds.** The coefficient test, the union-clustered variance, the joint z, the filter and replication rules and weighted Holm and BH are right. Planted effects are found at the critique's rates, within ±10 points in 54 of 55 cells. The exception is one column's joint detection at Δ = 0.1, 12 points under, explained by the specified clipping. False positives are at or under nominal: 0.15% through the whole gate at the Holm-34 line, against 0.15% nominal. Side A and every join are consistent.
* **Against real results the design effect is covered.** A random fixed per-player trait has a true null variance 1.11 times the model-based one. The screen's variance is the largest of three estimators, 1.15 on average, so the ratio that decides calibration is 0.96 (the critique measured 1.23 against the predecessor).
* **Must fix before the screen runs:**
  * **B1**, a crash: no `run` with effect sizes completes on the real frame.
  * **B2**, P2's p-value floor: a fixed trait at weight 0.5 can never be claimed.
  * **B3**, the history's order: a few model matches read a later round as their previous match.
  * **B4**, the freeze does not cover the η-modulator controls, the module hashes or the swap failures.
  * **B8**, the Wald path: an 8-column block passes 9.7% of nulls at 5%, which can also raise a false P3 alarm.
* **Should fix:** B5–B7 and B9–B14 (low; B5 low–medium).
* **After the fixes:** rerun `pytest test/feature_interactions`, plus regression tests for B1 (a held-out season without one tour), B3 (`round_order` never decreases within a player's event) and B4 (a changed η-modulator changes the table hash). Then rerun `verify/sizes_check.py` with the nuisance patch removed and `verify/planted_wald.py`. No other re-verification is needed.
* **Ledger.** Two rows are numbered 11 (this verifier's design-effect row, and the feasibility auditor's row written after it). The meta-auditor should renumber.

## Bugs and exact fixes

| ID | Severity | Where | What is wrong (observed) | Exact fix |
|---|---|---|---|---|
| B1 | **High** (crash; the batch cannot run) | `screen.nuisance`, used by `effect_sizes` | With one slope per tour (`per_season=False`) a tour column is dropped when the rows hold no match of that tour. The held-out 2018 season has no men's matches (no odds file), so its prediction design has 6 columns against the fit's 7: `ValueError: matmul … size 7 is different from 6`. Every `run(..., sizes=True)` (the default, used by the batch for the family and for P3) crashes on the real frame. The unit tests miss it because their synthetic frame has both tours in every season | In `nuisance`, replace `if m.any():` by `if m.any() or s is None:` (both tour columns always kept when there is one slope per tour). Verified: with this patched in (`verify/simlib.nuisance_fixed`), effect sizes run and recover planted gains (planted-effects section) |
| B2 | **Medium-high** (fixed traits nearly unclaimable) | `screen.run`, P2 | The permutation p-value has a floor of 1/(n_p2 + 1) = 0.000999 at n_p2 = 1,000. Holm's first-step line among 34 hypotheses (weights of mean 1) is 0.05·w/34 = 0.00147·w. A fixed trait at weight 0.5 can **never** be claimed; at weight 1 it needs zero exceedances in 1,000 (z beyond the permutation maximum, about 3.2 null SDs). Computed detection at Δ = 0.1 / 0.2 / 0.3 mLL: weight 0.5 → 0 / 0 / 0 (0.41 / 0.84 / 0.97 without the floor); weight 1 → 0.38 / 0.80 / 0.96 (against 0.48 / 0.87 / 0.98) | Keep the exact count p-value but let the number of permutations follow the evidence: run 1,000; if `(1 + k) / 1001 <= 0.01`, draw a **fresh** set of `n_p2_ext = 20_000` permutations and report their `(1 + k') / 20001` as `p2_perm` (floor 5·10⁻⁵, under every Holm line; still a valid p-value, because the fresh set does not depend on the decision to extend); store the count used and `p2_sd = np.std(null, ddof=1)`. Only candidates near a claim pay the extra (about 2–7 hours each at today's speed, under 2 with B13's fix). The cheaper normal approximation `p_value(z_raw / max(1, p2_sd), sign)` is **not** recommended: with 49 permutations per draw it did not restore the nominal rate (9.0% against 5.0% for the count p-value; P2 section) |
| B3 | **Medium** (a leak by construction, small) | `history.long_table` | Each player's matches are sorted by the clock's best-estimate day `obs` first. For undated matches `obs` is an estimate and puts a later round of the same event before an earlier one in 3,476 places (mostly Challenger Q3 before Q2; also R32, R16, QF, SF). At 7 model-match rows `prior(…, 1)` is a **later** round (a match not yet played); 751 model-match player-rows read a different previous match and 491 a different `rest_days` once fixed. The test `test_history_order_and_rest` cannot see it (it checks only that `obs` never decreases) | Replace the sort and the two rest lines by: `L["ev_obs"] = L.groupby(["player_id", "tournament_id", "tday"])["obs"].transform("min")`; `L = L.sort_values(["player_id", "ev_obs", "tday", "tournament_id", "round_order", "match_num"], kind="stable")`; then `k` as now; `L["obs_mono"] = g["obs"].cummax()`; `L["rest_days"] = L["obs_mono"] - g["obs_mono"].shift(1)`. Verified (`verify/history_order.py`): 0 reversals, 0 negative rest days. Add a test that `round_order` never decreases within a player's event |
| B4 | **Medium** (the freeze can be bypassed) | `screen_batch.table_hash`, `screen()` | The frozen hash covers x and the controls but not the values of `eta_mod_controls` (only their count), nor `trait_cols`; `screen()` never compares the module hashes recorded in `prepare.json`, and it runs even when a swap test failed | Add `"eta_mod_sha256": sha_array(Em)` (or `""`) and `"trait_cols": json.dumps(spec.get("trait_cols", []))` to each row and to `table_hash`'s column list; in `screen()`, `raise SystemExit` if `(~(T["swap_x"] & T["swap_controls"])).any()`, and if `module_hashes()` differs from the frozen `prepare.json` (or hash the module hashes into the frozen line) |
| B5 | Low–medium | `screen_batch.screen()`, P3 | The known-null set runs as `S.Hypothesis(hid, xf, None, [], sign)`: no controls, no miss × η, no `x_times_eta` / `eta_mod_controls` / `m_set` handling, so it does not go "through the whole pipeline" (critique 6.10). The six current P3 columns have none of these and full coverage, so today's set is unaffected; a future P3 builder with controls would be screened differently from the family | Move the family loop's body (per_base, miss × η, `S.run` / `S.run_wald`) into one function and call it for both the family and P3 |
| B6 | Low | `screen_batch._trait_permuter`, `screen.run` P2 loop | The permuted x is rebuilt through `combine`, but the controls are the real trait's (the builder's trait-derived controls and the batch's miss × η). Missing trait values also travel with the permuted players while the miss × η control stays put | Let the permuter return `(x, controls)` from the re-run `combine` plus a recomputed miss × η, and pass both to `Hypothesis` in the P2 loop; or permute only among players with an observed value (`table = table[np.isfinite(table["v"])]` before the shuffle), which keeps the missingness pattern |
| B7 | Low (conservative) | `screen.run`, P2 | The observed statistic compared with the permutation null is the P1-widened `zj`, the null is unwidened: double conservative when P1 widens | Compare the unwidened `z_raw = joint_z(r1["z"], r2["z"], r1["n"], r2["n"])` with the null, then take the max with the widened normal p as now |
| B8 | **Medium** (the Wald path over-rejects for wide blocks) | `screen.coef_test_multi`, `run_wald` | The covariance is the one with the largest **trace**, and W is referred to χ²_k. With G = 92 / 128 four-week blocks the clustered k × k covariance is noisy, so b'V̂⁻¹b is inflated (the Hotelling effect), and the largest trace is not the most conservative W. Synthetic nulls, 300 draws each: the 8-column P3 block KN-SDEV gives a joint false-positive rate of **9.7% at nominal 5%** and 3.3% at 1% (mean W/k 1.07; under the union covariance alone 1.25); the 2-column block S2 is conservative (3.3%). The replication rule along the discovery direction passes 29% of null 8-column blocks (nominal 25%) | In `coef_test_multi`: `Ws = {n: float(b @ np.linalg.solve(m, b)) for n, m in covs.items()}`; `name = min(Ws, key=Ws.get)`; `V, W = covs[name], Ws[name]`; `G = len(np.unique(f["block"].to_numpy()[rows]))`; `p = scipy.stats.f.sf(W / k * (G - k) / (G - 1), k, G - k)`; return `G`. In `run_wald` compute `p1` and `p_joint` with the same F reference (W divided by `widen` first). Replication: a scalar contrast, `z_rep = (d @ r2["b"]) / np.sqrt(d @ r2["V"] @ d)`. Simulated with min-W and F: 3.7% at 5%, 1.3% at 1% for k = 8; 3.0% / 1.3% for k = 2 |
| B9 | Low | `screen.run_wald`, batch | A Wald block that is a fixed player trait gets no permutation (M4) | `assert not (spec.get("wald") and spec["trait"] == "fixed")` in `build_all`, or add the permutation to `run_wald` |
| B10 | Low | `panel.panel`, `screen_batch.build_all` | Every builder receives the panel with the model frame's `a_won` (the match's result); nothing stops a builder from using it | In `build_all`, build on `P.drop(columns=["a_won"])`; in `swap_sides`, guard the flip with `if "a_won" in P.columns:` |
| B11 | Low | `screen.load` | The side-A check `a_won == a_won_s0` passes a match missing from Stage 0, because `NaN.astype(bool)` is True (observed: 0 missing today) | `if f["a_won_s0"].isna().any() or not (...).all(): raise` |
| B12 | Low | `screen.strata` | A RangeIndex series is grouped by `f["tour"]`, `f["season"]` (index-aligned): wrong deciles if a caller passes a frame without a 0…n−1 index (the harness's frames are reset, so not triggered) | `groupby([f["tour"].to_numpy(), f["season"].to_numpy()])` |
| B13 | Low (memory, time) | `screen_batch.build_all`, `_trait_permuter` | `P.assign(**new)` keeps a full panel copy (126 MB) per hypothesis with a `prepare` inside `built` (up to about 4 GB for 34); the permuter copies the whole panel at every one of its 1,000 permutations | Keep only `new` in `built` and rebuild `Q` when needed; in the permuter assign the permuted trait columns onto a frame holding only the columns `combine` reads |
| B14 | Low | `screen_batch._trait_permuter` (new `x_of_eta` path) | For a hypothesis whose x is a function of the base's η (`x_of_eta`), the permuter still takes `combine(R)["x"]` and applies η only for `x_times_eta`, so a fixed trait of that kind would be permuted on the wrong column. `s2_row` (H-S2 through the disjoint-seed encompassing t, 2016–2021 and 2022–2024, joined like the rest, weight 1) reads as specified in plan.md | In `permute`, `r = spec["combine"](R)`; `xp = r["x_of_eta"](e_base, pos) if r.get("x_of_eta") is not None else np.asarray(r["x"], float)[pos]` (pass the base's η to `_trait_permuter` whenever `x_of_eta` or `x_times_eta`), or assert that no fixed trait uses `x_of_eta` |

Not bugs, recorded for the reader:

* **The variance is the largest of block, dyadic and union** (the code's docstring; the critique asks for the union). This is conservative: with independent synthetic outcomes the harness's SE is 4–6% above the model-based one, which with the clipping costs 1–5 points of detection (tables below). Against real results it is what keeps fixed traits nominal (design effect).
* **Two-sided weights.** The batch passes the table's weight unchanged; the 0.5 for an undeclared sign (critique 6.7) must therefore be written into the hypothesis row (the math audit does so for I-006). An `assert` that `sign == "two"` implies `weight <= 0.5` unless the row says otherwise would catch an omission.
* **The z₁–z₂ correlation** that shared players could create (the joint z treats the windows as independent) is not visible against real results: correlation −0.11 to +0.05 for the five random feature types, joint-z SD 0.92–1.00.
* **`swap_sides`** handles every `_a`/`_b` pair, the model's diff inputs, `eta_model`, the two probabilities, the player ids and `a_won`; `mu_logit` is context (mean 0.37, correlation with the odds −0.004), correctly left unchanged.

## Code review: what was checked and holds (observed)

* **Rows and orientation** (`verify/integrity.py`). The screen's frame has 50,087 matches (34,880 in 2014–2021, 15,207 in 2022–2024; the men's 2018 season absent), 92 and 36 four-week blocks, no missing player id, no match with the same player on both sides, every match in the pre-rebuild Stage 0. Side A is Stage 0's `player_a_id` everywhere: the panel's `player_a_id` equals the frame's on all rows, Stage 0's player table has side A = `player_a_id` on all 872,704 matches, and every per-player source reproduces the model's own A − B inputs (surface IOS, Elo, sets in 14 days, age, the two-week profile: correlation 1.000, sign agreement 1.000; de-vigged average odds equal `in_odds_logit` to 4·10⁻¹⁵). The P3 TTT log-odds is oriented the same way (correlation 0.93 with the odds) and comes from the leak-proof `ttt_pass_timed`.
* **The coefficient test.** No intercept; one slope on η per tour × season and an odd cubic per tour (scaled on discovery rows); the controls; b. Newton with a negligible ridge; the influence terms u_i = (y_i − p_i)·(H⁻¹z_i)_b are the right sandwich pieces; the model-based variance is (H⁻¹)_bb.
* **Clustered variances.** Block: Σ_blocks (Σu)². Dyadic: Σ_players (Σu)² − Σ_pairs (Σu)², which counts each pair of matches sharing at least one player once (a rematch shares two). Union: block + dyadic − (both), the intersection computed the same way within blocks. All three agree with brute force (the existing test). The small-sample factor G/(G − 1) with G = blocks is applied to all three; the dyadic and union terms have thousands of player clusters, so this is the larger, conservative factor. The k × k version is the same algebra.
* **Preprocessing** is fixed on discovery rows without results: |x| clipped at its 99th percentile (for an antisymmetric x, the same as winsorising at 0.5% and 99.5%, and it keeps the swap sign), x and the controls divided by their discovery SD and never centred, missing values set to 0, the cube's scale per tour.
* **Joint z, gates and multiplicity.** z_joint = (√n₁z₁ + √n₂z₂)/√(n₁ + n₂); one-sided p in the declared direction, two-sided 2·Φ(−|z|); filter z₁ > 1 (|z₁| > 1 two-sided); replication z₂ > 0.67 in the same direction; filtered or non-replicating hypotheses enter Holm and BH with p = 1. Weighted Holm and weighted BH agree with brute-force rejection rules in 40,000 random families of 2–60 hypotheses with weights 0.5 / 1 / 2 at α = 0.05 and 0.10 (`verify/multiplicity_check.py`: 0 disagreements).
* **Wald path.** Per-column preprocessing, the k × k clustered covariance, W = b'V⁻¹b on 2014–2021 (filter p < 0.3173), on the pooled 2014–2024 fit (joint p), and replication as d'V₂⁻¹b₂/√(d'V₂⁻¹d) with d the discovery coefficients, which is N(0, 1) under the null; P1 permutes the block's rows jointly and widens by the mean null W/k when above 1.21.
* **P1** shuffles the standardised x within tour × season × surface × η-decile (deciles within tour × season) and widens the SE by the null SD when above 1.10. **P2** permutes each player's trait once, within tour, through the builder's own `combine`; the p-value (1 + #exceed)/(1 + B) is right; the harness's P2 p-value equals an independent re-implementation exactly on the same seed (`verify/p2_check.py`).
* **Batch.** Builds x per hypothesis on the panel, maps to the frame through unique match ids, forms s·η for `x_times_eta`, s_j·η for `eta_mod_controls`, η·|η| per tour for the M-set and miss × η for any column with missing values, per base; swap tests use `swap_sides` on the panel with the builder's new per-player columns.
* **Effect sizes** (after B1's fix): leave-one-season-out on 2014–2021 and forward on 2022–2024 with one slope per tour, the cubic and the controls, paired with four-week-block intervals; the direction is "positive = the hypothesis lowers the log loss".
* **TabPFN side** (read only): `local_fits` saves each orientation and the ids; `oos_model_forecast` and `tabpfn_tests.forecasts` symmetrise the same way and differ only in which folder they try first for 2019–2024 (identical fits, plan M1).

## Timing (observed, this PC, synthetic outcomes, 50,087 matches)

| Call | Seconds |
|---|---|
| one `coef_test` (2014–2021) | 0.10 |
| `screen.run`, n_p1 = 0, no effect sizes | 0.14 |
| `screen.run`, n_p1 = 0, with effect sizes (B1 patched) | 0.40 |
| **`screen.run`, n_p1 = 200, with effect sizes (B1 patched)** | **22.0** |
| `screen.run_wald`, k = 4, n_p1 = 200 | 26.6 |
| one P2 permutation (permute, prepare, two fits) on a slim frame-sized table / a slim panel-sized one (measured under load) | about 0.3 / about 1 |

A batch of 34 single-coefficient hypotheses against both bases takes about 13 minutes, plus about 5–17 minutes per fixed trait for P2 at 1,000 permutations per base. The batch's permuter also copies the full 126 MB panel at each permutation (not timed; B13).

## Design effect against the current best (task 3; ledger row 11)

Real 2014–2024 results through `screen.run` (per tour × season slopes, cubic, no controls) on the current best's out-of-sample log-odds, plus one **random** feature; 300 draws per type. Each cell is a variance relative to the model-based variance (sampling error of a ratio about ±0.08); "harness" is the mean of the variance the screen actually uses, the largest of block, dyadic and union. The last two columns are the ones that decide calibration: true ÷ harness above 1 means the screen's z is too large.

| Random feature, window | True null variance | Block | Dyadic | Union | Harness (max of 3) | True ÷ harness | SD of z |
|---|---|---|---|---|---|---|---|
| independent per match, 2014–2021 | 1.07 (critique 1.05) | 0.98 (0.99) | 1.01 (0.98) | 0.98 | 1.09 | 0.98 | 1.01 |
| independent per match, 2022–2024 | 1.04 | 1.00 | 1.01 | 0.98 | 1.13 | 0.92 | 0.96 |
| **fixed per player, u_A − u_B, 2014–2021** | **1.11 (critique 1.23)** | 0.99 (0.98) | 1.07 (1.06) | 1.06 | 1.15 | **0.96** | 1.00 |
| fixed per player, 2022–2024 | 0.82 | 0.99 | 0.82 | 0.80 | 1.04 | 0.79 | 0.90 |
| per player and season, 2014–2021 | 0.91 (1.02) | 0.99 (1.01) | 1.00 (0.99) | 0.99 | 1.09 | 0.83 | 0.93 |
| per player and season, 2022–2024 | 1.04 | 1.02 | 0.95 | 0.96 | 1.12 | 0.93 | 0.97 |
| per tournament edition × η, 2014–2021 | 1.17 (1.07) | 1.00 (0.94) | 0.95 (0.93) | 0.97 | 1.09 | 1.08 | 1.05 |
| per tournament edition × η, 2022–2024 | 0.93 | 0.88 | 0.98 | 0.88 | 1.06 | 0.88 | 0.95 |
| per four-week block × η, 2014–2021 | 0.99 (0.86) | 0.82 (0.85) | 0.95 (0.92) | 0.78 | 0.98 | 1.01 | 1.01 |
| per four-week block × η, 2022–2024 | 0.74 | 0.71 | 1.00 | 0.70 | 1.04 | 0.72 | 0.88 |

The joint z, which is what the gates read: SD 0.94 (independent), 0.97 (fixed per player), 0.92 (player-season), 1.00 (tournament × η), 0.99 (block × η); correlation of z₁ and z₂ −0.11 to +0.05; two-sided 5% false-positive rate 4.3–5.7% (300 draws each, ±1.3 points).

* **Observed.** Against the current best, a fixed per-player trait's true null variance is 1.11 times the model-based one (the critique measured 1.23 against the 54-input predecessor; the two differ by about 1.5 sampling errors). The harness's variance, the largest of the three estimators, is 1.15, so the ratio that matters is 0.96: the screen's normal z for a fixed trait is not inflated against real results.
* **Observed.** The one type above 1 is the tournament-edition modulation of η in 2014–2021 (1.08, SD of z 1.05), within sampling error of 1; four-week blocks contain whole tournaments, so no further clustering is suggested.
* **Inferred.** The M4 factor for slow traits (variance × 1.25) is conservative against the current best; P2 remains as insurance for fixed traits: its count p-value is exact, and with B2's fix it can also reach the Holm lines.
* **Plan M1's ledger row:** design effect re-measured; fixed-trait ratio (true ÷ harness) 0.96, all types 0.83–1.08 in discovery.

## Planted effects against the critique (task 2; synthetic outcomes)

y ~ Bernoulli(σ(a_tour·η + β·x)), η the current best's real out-of-sample log-odds, a = 0.89 men and 0.91 women, x a real column standardised on 2014–2021 rows, β set so that the population-averaged gain over the screen's own null design (per tour × season slopes, cubic, the column's controls) is Δ, pooled over 2014–2024. Through `screen.run` (n_p1 = 0, no effect sizes), 200 draws per cell (rate SE about 3.5 points at 0.5, 2 at 0.9). The columns: the five single-column known nulls built by `screen_batch.build_all(P, L, pattern="p3_*.py")` (the sixth, KN-SDEV, is in the Wald section), three S-type products of the levels columns with a model input (the input as control: S-IOS hold offence sum × `in_iosD_hold`, S-AGE age sum × `in_sets_14d`, S-ELO Elo sum × `in_elo_overall`), the height difference (missing 8%, so miss × η is a control), the model's own `in_form_df`, and independent noise. "Power" is z₁ > 1.96 on 2014–2021 (critique table 1.4: **0.78** at Δ = 0.1, **0.96** at 0.2); "joint" is the full one-sided gate at the Holm-34 line: z₁ > 1, z₂ > 0.67 and z_joint > 2.97 (critique table 1.5, Holm over 40: **0.53 / 0.90 / 0.99**). In brackets, the normal theory at this column's n and gains with design effect 1.

| Column | Δ = 0.1: power z₁ > 1.96 | Δ = 0.1: joint Holm-34 | Δ = 0.2: power | Δ = 0.2: joint | Δ = 0.3: joint | mean z₁ ÷ theory (Δ = 0.2) |
|---|---|---|---|---|---|---|
| RAND | 0.74 (0.75) | 0.51 (0.55) | 0.96 (0.96) | 0.89 (0.91) | 0.98 (0.99) | 0.95 |
| KN-TTTOFF | 0.69 (0.73) | 0.48 (0.55) | 0.94 (0.95) | 0.93 (0.92) | 0.98 (0.99) | 0.98 |
| KN-SNET | 0.71 (0.73) | 0.52 (0.55) | 0.95 (0.96) | 0.88 (0.92) | 0.98 (0.99) | 0.93 |
| KN-ELOSURF | 0.71 (0.75) | 0.48 (0.55) | 0.94 (0.96) | 0.92 (0.91) | 0.98 (0.99) | 0.95 |
| KN-TTTLOGIT | 0.72 (0.75) | 0.47 (0.55) | 0.94 (0.96) | 0.90 (0.91) | 0.98 (0.99) | 0.99 |
| KN-SURFCAREER | 0.70 (0.69) | 0.51 (0.55) | 0.91 (0.94) | 0.87 (0.92) | 0.98 (0.99) | 0.94 |
| S-IOS | 0.79 (0.83) | 0.46 (0.48) | 0.98 (0.98) | 0.81 (0.82) | 0.92 (0.93) | 0.93 |
| S-AGE | 0.76 (0.76) | 0.54 (0.54) | 0.96 (0.97) | 0.84 (0.91) | 0.96 (0.98) | 0.95 |
| S-ELO | 0.73 (0.79) | 0.41 (0.53) | 0.94 (0.97) | 0.84 (0.89) | 0.96 (0.97) | 0.92 |
| HEIGHT | 0.72 (0.79) | 0.52 (0.53) | 0.98 (0.97) | 0.82 (0.89) | 0.97 (0.98) | 0.95 |
| IN-FORMDF | 0.73 (0.72) | 0.53 (0.55) | 0.94 (0.95) | 0.92 (0.92) | 0.99 (0.99) | 0.93 |
| **mean, Δ = 0.1** | power 0.73 (0.75) | joint 0.49 (0.54); Holm-40 0.47 | | | | |
| **mean, Δ = 0.2** | power 0.95 (0.96) | joint 0.87 (0.90); Holm-40 0.87 | | | | |
| **mean, Δ = 0.3** | power 0.99 (1.00) | joint 0.97 (0.98); Holm-40 0.97 | | | | |

* **Observed.** Averaged over the eleven columns, detection is 0.49 / 0.87 / 0.97 at Δ = 0.1 / 0.2 / 0.3 mLL against the critique's 0.53 / 0.90 / 0.99, and discovery power 0.73 / 0.95 against 0.78 / 0.96: **within ±10 points** everywhere except one cell, S-ELO at Δ = 0.1 (0.41, 12 points under the critique's 0.53, 3.4 sampling errors under its own theory 0.53).
* **Why the harness sits 1–5 points under the theory.** The variance used is the largest of three estimators, on average 4–6% above the model-based one with independent outcomes (column `se_ratio` in `summary_planted.csv`), and |x| is clipped at its 99th percentile, which attenuates b̂ by up to 7% for a heavy-tailed product (b̂/β = 0.93 for S-ELO, 0.95 for S-IOS, 0.97–1.03 for the others). Mean z₁ is 0.92–0.99 of the theoretical √(2nΔ). Both are choices of the specification, not code errors.
* **Effect sizes** (B1 patched; 30 draws at Δ = 0.3, mLL, positive = the planted term lowers the log loss): independent noise, leave-one-season-out 0.25 (true 0.30) and forward 0.31 (true 0.30); S-IOS 0.32 (true 0.36) and 0.13 (true 0.15). Draw-to-draw SD 0.13–0.16; mean 95% half-widths about 0.25 (leave-one-season-out) and 0.30–0.40 (forward): unbiased within noise, and as the critique says too noisy to gate.
* **P1** (200 shuffles, 6 draws each): the null SD of z is 0.91–1.00 at β = 0 and 0.89–1.09 at Δ = 0.2, never above the 1.10 widening line.

## False positives at β = 0 (synthetic outcomes)

The same eleven columns, 500 null draws each (rate SE about 1 point at 5%, 0.4 at 1%). One-sided rates are in the declared "+" direction.

| Column | Draws | SD z₁ | SD z_joint | z_joint > 1.645 (5%) | abs(z_joint) > 1.96 (5%) | z_joint > 2.326 (1%) | filter + replication + z_joint > 1.645 | full gate at Holm-34 |
|---|---|---|---|---|---|---|---|---|
| RAND | 500 | 0.98 | 0.96 | 0.036 | 0.038 | 0.012 | 0.020 | 0.002 |
| KN-TTTOFF | 500 | 0.99 | 0.94 | 0.046 | 0.042 | 0.008 | 0.030 | 0.002 |
| KN-SNET | 500 | 0.97 | 0.97 | 0.050 | 0.052 | 0.010 | 0.028 | 0.002 |
| KN-ELOSURF | 500 | 0.94 | 0.94 | 0.048 | 0.038 | 0.012 | 0.018 | 0.000 |
| KN-TTTLOGIT | 500 | 0.95 | 0.93 | 0.040 | 0.042 | 0.008 | 0.016 | 0.000 |
| KN-SURFCAREER | 500 | 0.96 | 0.98 | 0.050 | 0.040 | 0.012 | 0.034 | 0.002 |
| S-IOS | 500 | 0.95 | 0.98 | 0.046 | 0.050 | 0.004 | 0.026 | 0.004 |
| S-AGE | 500 | 0.94 | 0.95 | 0.028 | 0.038 | 0.004 | 0.018 | 0.000 |
| S-ELO | 500 | 0.97 | 1.04 | 0.060 | 0.054 | 0.014 | 0.042 | 0.004 |
| HEIGHT | 500 | 0.94 | 0.89 | 0.026 | 0.028 | 0.004 | 0.012 | 0.000 |
| IN-FORMDF | 500 | 0.93 | 0.91 | 0.028 | 0.026 | 0.002 | 0.014 | 0.000 |
| **all (5500 draws)** | | | 0.95 | 0.042 | 0.041 | 0.008 | 0.023 | 0.0015 |

* **Observed.** The single-coefficient screen is at or under nominal: z_joint SD 0.95 overall (0.89–1.04 by column), 4.2% one-sided and 4.1% two-sided at 5%, 0.8% at 1%, and 8 of 5,500 draws (0.15%) through the whole gate at the Holm-34 line, where the nominal rate is 0.15%. S-ELO is the one column with SD above 1 (1.04 ± 0.03).

## The Wald path (synthetic outcomes)

Two real blocks through `screen.run_wald` (n_p1 = 0): the P3 block KN-SDEV (8 surface-deviation columns, no controls, as the batch runs it) and S2 = [S-IOS, S-AGE] with their two controls and miss × η. The planted direction is the equal-weight sum of the standardised columns. 300 null draws and 150 per Δ. Detection is the joint p below the Holm-34 line 0.05/34 (theory: the non-central χ²_k with λ = 2nΔ); the null row gives the joint test's rate at nominal 5%.

| Block | k | Statistic as coded (largest-trace V, χ²) | min of the three W, χ² | **min of the three W, F(k, G − k)** (proposed) | block V, F(k, G − k) | theory |
|---|---|---|---|---|---|---|
| KN-SDEV, β = 0, rate at 5% | 8 | **0.097** | 0.063 | 0.037 | 0.047 | 0.05 |
| KN-SDEV, Δ = 0.1 / 0.2 / 0.3 | 8 | 0.23 / 0.63 / 0.91 | 0.16 / 0.53 / 0.88 | 0.09 / 0.33 / 0.79 | 0.13 / 0.45 / 0.85 | 0.17 / 0.58 / 0.87 |
| S2, β = 0, rate at 5% | 2 | 0.033 | 0.030 | 0.030 | 0.030 | 0.05 |
| S2, Δ = 0.1 / 0.2 / 0.3 | 2 | 0.34 / 0.78 / 0.96 | 0.33 / 0.77 / 0.96 | 0.29 / 0.74 / 0.96 | 0.34 / 0.78 / 0.96 | 0.38 / 0.84 / 0.98 |

* **Observed.** As coded, the 8-column block's null rate is 9.7% at 5% (3.3% at 1%), and 3 of its 300 null draws (S2: 2 of 300) pass the whole gate at the Holm-34 line, where 0.44 is expected; its "power" above the theory is the same inflation. Under each covariance the mean null W/k on 2014–2024 is: model-based 0.99, block 1.07, dyadic 1.11, union 1.25 (k = 8); 0.99, 1.03, 1.12, 1.20 (k = 2). The trace rule picked block 143, dyadic 110, union 47 times of 300 (k = 8). The union covariance was positive definite in every draw.
* **Proposed (B8).** The minimum W over the three covariances (the analogue of the single path's largest variance) referred to F(k, G − k) after the factor (G − k)/(k(G − 1)), G the blocks in the fitted rows: under nominal for both widths (3.7%, 3.0%), and 1 of 300 null draws through the Holm-34 gate for each block. Its cost falls on wide blocks (KN-SDEV at Δ = 0.2: 0.33 against a theory of 0.58); for two columns it is 4 points (0.74 against 0.78). If wide family blocks matter, the block covariance alone with the same F reference is closest to nominal (4.7%) at 0.45, but it ignores shared players, so pair it with B9.
* **Replication along the discovery direction** passes 29% (k = 8) and 27% (k = 2) of null blocks against a nominal 25%: the inverse of the replication window's k × k covariance (36 blocks) is noisy; B8's scalar contrast avoids the inverse.

## Fixed player traits, with and without P2 (synthetic outcomes with career-long player effects)

To test P2 the outcomes need what real results have and independent synthetic draws lack: a player the forecast misjudges stays misjudged. y ~ Bernoulli(σ(a_tour·η + v_A − v_B)), v ~ N(0, 0.1²) per player, redrawn each draw. That is stronger than in the real data (against real results a random fixed trait's z_joint has SD 0.97; here 1.09), so it is a stress test. The permutation is the batch's own `_trait_permuter`; the P2 loop is mirrored call for call so that the permutation null's spread can be kept, and on the first draw of each run the harness's own `p2_perm` equals the mirror exactly.

| Trait | Draws | True null SD of z_joint | Mean permutation SD | Normal test, one-sided 5% | max(normal, P2 count p), 5% | max(normal, SD-calibrated normal), 5% |
|---|---|---|---|---|---|---|
| UFIX, u_A − u_B, a new u ~ N(0, 1) per player each draw (P2's exact null) | 500 without P2, 100 with P2 (49 permutations each) | 1.086 | 1.036 (draw-to-draw SD 0.12) | **0.082** (two-sided 0.078; 0.090 in the 100 draws with P2) | **0.050** | 0.090 |
| HEIGHT, the real height difference (8% missing; miss × η control) | 60 (49 permutations each) | 1.063 | 1.024 | 0.033 | 0.017 | 0.033 |

* **Observed.** Without P2, a null fixed trait under strong player effects passes a one-sided 5% test 8.2% of the time; P2's count p-value restores 5.0% (100 draws, ±2.2 points), and its p-values average 0.47 (uniform: 0.50). P2 does what M4 asks, and the harness implements it as specified.
* **Observed.** The permutation SD (1.04) sits within 1.4 sampling errors of the true null SD (1.09). Gating on the normal tail divided by that SD did not restore the nominal rate (9.0%), so B2's fix keeps the exact count p-value and adds permutations instead.
* **Computed** (B2): with 1,000 permutations the count p-value cannot go below 0.000999. At the Holm-34 line this caps fixed-trait detection at Δ = 0.1 / 0.2 / 0.3 mLL at 0 / 0 / 0 for weight 0.5 (0.41 / 0.84 / 0.97 without the cap), 0.38 / 0.80 / 0.96 for weight 1 (0.48 / 0.87 / 0.98) and 0.48 / 0.87 / 0.97 for weight 2 (0.56 / 0.90 / 0.98): normal theory with the harness's 0.95 efficiency and a permutation null of SD 1 (as against real results), the filter and replication included.
* **Against real results** (design effect, above), the fixed-trait ratio true ÷ harness is 0.96. P2 should rarely bind; its job is insurance.
