# Round 2 builds · analyst "body"

7 October 2026 · EDA analyst BODY · Research evidence, not a decision. Built to the final family ([hypothesis_family.md](../hypothesis_family.md), [rulings.md](../rulings.md)), which supersedes the round-1 cards where they differ, and to [builders.md](../../builders.md). Updated for the meta-auditor's [checkpoint 1](../../meta/checkpoint_1.md): INFO-1 is out of B-STATE (R-1, F-1); B9a gates on the slow-trait widening (R-6, F-2); B11's member decomposition and INFO-1's column are exposed as descriptive sensitivities (R-2, F-6).

**No result read.** The panel's `a_won` was dropped on load in every script of mine. Seasons stop at 2024: `history.long_table()` is cut before 20 December of the panel's last season, and tennis-data's Court field is read only for seasons up to it. The 2025–2026 row counts (4,394 men's, 4,199 women's) come from `round1/test_counts.json`; no 2025–2026 value was loaded. Prices enter only as a modulator (I-066's expected points) and through the batch's η. Gate and constant targets are box-score statistics, schedule facts or a simulator, on 2013–2018.

**History order.** Everything below was rebuilt after `history.py`'s 22:00 correction (events placed by their earliest day, rounds kept in order). The builders' clock is the running maximum of the best-estimate day (`obs_mono`), so every decay and window sees non-decreasing days.

## Summary (all rows pass `screen_batch.py --prepare`: swap test of x and controls)

Coverage is the share of model matches with x defined, men / women. R² is the batch's novelty R² of x on the 58 inputs (2014–2021). Block rows carry sign **+** on the sum of members already multiplied by their declared signs: that is the family's rule ("multiplied by its declared sign and summed … tested one-sided") and every block module's convention. The family table writes the members' common sign (B-LOAD, B-PREV, B10, B-INJ: −).

| hid | module | members (declared sign) | test | weight | trait | coverage 2014–21 · 2022–24 | R² |
|---|---|---|---|---|---|---|---|
| I-053 | f20_fatigue | Δ[Fat·(age − 26)+] (−) | single, − | 1 | slow | 100 / 100 · 100 / 100 | 0.766 |
| B-LOAD | f20_fatigue | ΔFat (−), ΔOff (−) | signed sum | 1 | none | 100 / 100 · 100 / 100 | 0.766 |
| B-PREV | f20_fatigue | ΔPrevX (−), Δ[PrevX·(1[rest ≤ 1] − 1[rest ≥ 2])] (−) | signed sum | 1 | none | 96.9 / 95.7 · 97.1 / 96.4 | 0.068 |
| B9a | f21_constitution | Δ[h·Fat] (−), Δ[h·(age − 28)+] (−), Δ[Trait·Fat] (+), I-061 (−) | signed sum | 0.5 | slow; height permutation as a diagnostic (R-6) | 100 / 100 · 100 / 100 | 0.238 |
| B9b | f22_demand | I-063 composed ΔFat (−), I-065 (+), I-066 (−) | signed sum, M-set | 0.5 | slow | 100 / 100 · 100 / 100 | 0.277 |
| B10 | f23_arrival | I-059, I-088, I-060, I-074 (all −) | signed sum | 0.5 | none | 100 / 100 · 100 / 100 | 0.227 |
| B11 | f24_onsite | I-051 On, I-075, I-076 (all +) | signed sum | 0.5 | none | 100 / 100 · 100 / 100 | 0.476 |
| B-SWITCH | f25_switch | I-046, I-047 style·sgn, I-047 age, I-050 | Wald 4 df | 0.5 | slow | 100 / 100 · 100 / 99.96 | 0.211, 0.010, 0.101, 0.248 |
| B-INJ | f26_impairment | I-043, I-044, I-045 (all −) | signed sum | 0.5 | none | 100 / 100 · 100 / 100 | 0.103 |
| B-HOME | f27_home | I-078, I-079 | Wald 2 df | 0.5 | fixed (country) | 100 / 100 · 100 / 100 | 0.045, 0.118 |
| B-STATE | f28_state | BOD-C1 ΔPastFat (+) alone; INFO-1 out (R-1) | single member | 0.5 | none | 81.6 / 79.0 · 83.9 / 80.2 | 0.669 |

**Gates (pre-declared, result-free, binding as declared on raw correlations):** I-058 passes (split-half r 0.086 on 797 players against pure-luck replays −0.037, −0.031, +0.036); I-065 passes (0.887 ≥ 0.3); I-045 passes as declared (0.0096 against replays 0.0003) but would fail a 2-SE margin (SE 0.005). No member dropped. Numbers in `data/studies/feature_interactions/round2/body/prechecks.json`.

**Probe-equivalent check: passed** (66 of 66 cut × mode × row checks; rerun after the checkpoint changes; details below).

**Descriptive sensitivities** (checkpoint 1, F-6 interface `SENSITIVITIES` / `SENSITIVITY_OF`; never gating, never in the bundle; each swap-tested antisymmetric, defined on 100% of rows): in f24, "B11 member On", "B11 member I-075", "B11 member I-076" (each member's standardised column, sign +1, B11's controls; non-zero 37%, 27%, 11% of 2014–21 rows); in f28, "B-STATE INFO-1 (descriptive)" (INFO-1's raw column, B-STATE's controls; non-zero 33%).

## Shared machinery (f20_fatigue)

* **History.** One row per (match, player), the player's own order. Rows dated from 20 December belong to the next season and are cut with it. A value at a row uses only the same player's strictly earlier rows.
* **Load L_j** (BOD-02). Minutes of earlier played match j if 1–700; else points played × minutes per point; else games × minutes per game; walkovers 0.
  * The two pace constants are field statistics, so they are walk-forward on the clock: for tournament year Y, the ratio over the three previous years' matches with lf + 1 ≤ T_Y (T_Y = 20 December of Y − 1, or the year's first es if earlier).
  * Cells: tour × surface, then tour, then surface, then all (≥ 300 matches each). The prior 0.625 min per point and 4.4 min per game (BOD-02's arithmetic) is used only by 2010 rows.
  * **Observed:** ITF matches have no minutes at all, and women have none before 2016. Either player's kernel is more than half imputed in 11.6% of men's and 34.2% of women's 2014–21 matches (6.6% and 10.8% in 2022–24).
* **Fat_X = log(1 + Σ_j L_j·e^(−Δ_j/3))**, τ = 3 days fixed in advance (math audit, finding 2). The imputed share of the kernel's load is the "minutes-imputed indicator". Its A − B difference is a control, and 1[either share > 0.5] × η is an eta-modulator control.
* **Missingness (S11).** A missing value is 0 in the screen. A block member that is missing counts 0 in the sum, and its missing indicators enter the controls (A − B, and the symmetric indicator through `eta_mod_controls`). Where x itself is missing, the batch adds 1[missing] × η, so no copy of it is passed.
* **Std: the nearest inputs.** For each row, the 1–3 diff inputs with the largest |r| on 2014–2021 rows (|r| ≥ 0.10 beyond the first; the price is never one; the row's own controls are excluded). They were computed on the final code and **fixed** in `f20.NEAREST`, because the fixed-trait permutations re-run the builders.
* **Blocks.** Each member is clipped at its 99th percentile of |m| and divided by its SD on 2014–2021 rows (the screen's own preprocessing), times its declared sign, then summed.

## The rows

R² is always the novelty R² on the 58 inputs (2014–2021, the batch's least squares). "Non-zero" is the share of 2014–21 model matches where the member is not 0, men / women.

### I-053 · age × recovery debt
* **Built:** x = Fat_A·a_A − Fat_B·a_B, a = (age − 26)+, Stage 0's pre-match age. Single coefficient, sign −, weight 1, slow.
* **Constants:** τ = 3 days and the knee at 26 (the originator's simpler form). None tuned.
* **Controls:** ΔFat, age, age_sq, sets_14d, the imputed-share difference; nearest iosO_bp_saved, iosO_second_won, iosO_hold. Eta-mod: ΣFat, Σa, 1[imputed].
* **Diagnostics:** R² 0.766 (age dominates the product: r 0.77 with `age`). Non-zero 87% / 69%.

### B-LOAD · I-052's kernel and I-051's off-site part
* **Built:** members ΔFat (−) and ΔOff (−). Off = log(1 + the decayed load of earlier matches not at this event), which is Fat minus its on-site part. This is the rebuttal's definition (BOD-R1, accepted).
* **Controls:** sets_14d, surf_layoff_a − surf_layoff_b, the imputed-share difference; nearest adjperf_tpw_2w, form_brk, form_hold. Eta-mod: 1[imputed].
* **Diagnostics:**
  * R²: ΔFat 0.806, ΔOff 0.541, block 0.766. These reproduce the rebuttal's 0.811 and 0.543.
  * corr(ΔFat, ΔOff) = 0.50.
* **Sensitivities (correlation with ΔFat at τ = 3):** τ 1.5 days 0.93; τ 5 days 0.96; Fit at 21 days 0.64; a games-only kernel 0.99. Fit, ACWR and team ties stay sensitivities (family).

### B-PREV · the previous match's extra sets, and I-056's rest contrast
* **Built (BOD-L1 as the rebuttal computed it):** PrevX = (sets of X's previous played match − the format's minimum) / (maximum − minimum), when that match was at this event and ≤ 3 days before; otherwise 0. It is missing when that match ended in a retirement or has no score.
* **Members:** ΔPrevX (−) and Δ[PrevX·(1[rest ≤ 1] − 1[rest ≥ 2])] (−), rest in best-estimate days since the previous played match.
* **Controls:** sets_14d, ΔFat, Δmin(rest, 7), the PrevX-missing difference; nearest elo_games, elo_overall, ratings_iid.
* **Diagnostics:**
  * R²: ΔPrevX 0.120 (rebuttal 0.121); contrast 0.009; block 0.068.
  * Non-zero: ΔPrevX 28.8% / 25.6%; the contrast 29.5% / 24.7%.
  * Missing: 3.1% (men) and 4.3% (women) of matches (a previous on-site retirement); S11 applies.
* **Note:** fractional best-estimate rests between 1 and 2 days give the contrast 0, as the family's indicators define it.

### B9a · constitution × own load (fixed trait: height)
* **Members:**
  * I-024, two columns: Δ[(h − h̄)·Fat] (−) and Δ[(h − h̄)·(age − 28)+] (−), with h̄ the tour's mean height on 2014–2021 rows. Centring changes no test: Δh, ΔFat and Δ(age − 28)+ are controls. It does keep each column's SD to its interaction part inside the composite.
  * I-058: Δ[Trait·Fat] (+).
  * I-061: 1[month ≥ 9]·Δ[Odo·(age − 27)+] (−).
* **I-058's trait:**
  * Built from every earlier match with a box score: the shrunk difference of the points-won residual between high-Fat matches (≥ the tour's 80th percentile) and low-Fat matches (≤ the median).
  * Expectations come from Stage 3's pre-match serve shares.
  * Shrinkage τ²/(τ² + σ²(1/n_h + 1/n_l)).
* **Constants (2013–2018, statistic targets):** Fat quantiles (median, 80th) 3.892 and 4.716 for men, 3.868 and 4.661 for women; τ² = 5.67e-5 (the split halves' covariance); σ² = 5.03e-3.
* **Gate (I-058, declared):** split-half reliability on 797 players is r = 0.086. The three binomial replays at Stage 3's expectations give −0.037, −0.031 and +0.036 (mean −0.011). **Passes.** On the pre-22:00 history order it was 0.035 against −0.017: also above as declared.
* **I-061's odometer:**
  * M = X's minutes-equivalent load earlier in the season.
  * E = the field's mean M for the same tour, week and ranking band (1–20, 21–50, 51–100, 101–250, other) in the three previous seasons, walk-forward on the clock.
  * Odo = log((M + 300)/(E + 300)).
* **Controls:** Δh, Δ(age − 28)+, ΔFat, ΔTrait, Δ[Odo·(age − 27)+] (unmodulated), ΔOdo, Δage, the height-missing and imputed differences; nearest iosO_ace, prod_first_won, prod_hold. Eta-mod: ΣFat, Σh, Σage, ΣTrait, 1[month ≥ 9], missing indicators.
* **Diagnostics:**
  * R²: h·Fat 0.460; h·(age − 28)+ 0.236 (the feasibility audit's 0.958 was the uncentred product, mostly (age − 28)+); Trait·Fat 0.075; I-061 0.045; block 0.238.
  * Non-zero: h·(age − 28)+ 73% / 43%; I-061 16% / 11%.
  * Women's heights fall to 64% non-zero in 2022–24.
* **Trait (checkpoint 1, R-6):** the block gates on the slow-trait widening (variance × 1.25). `trait_cols = ["height"]` lets the batch compute the height permutation as a diagnostic of the height members only, never folded into `p_joint`.

### B9b · match demand × fatigue (slow)
* **I-063.**
  * D = logit P_iid(p_A − δ_A + ηδ_B, p_B − δ_B + ηδ_A) − logit P_iid(p_A, p_B), with δ = κ·Fat, Stage 3's p_serve and standard tiebreak sets.
  * The member is −D/κ, so it is positive when A is the more tired (sign −).
  * **κ and η from the statistic target (2013–2018, 169,248 rows):** serve and return residuals regressed on own and opponent Fat, with on-site counts held.
    * κ̂ = −0.00274 (s.e. 0.00016): the recently loaded player out-performs Stage 3's expectation, the survival selection Stage 4 saw for load.
    * η̂ = 1.18.
    * The member uses |κ̂| with the declared direction, and η clipped to 1.
    * λ (growth within a match) is not identifiable from match-level box scores without selection (realised length is an outcome), so λ = 0.
  * After standardisation the member is the iid leverage × ΔFat. It is identified beyond the ΔFat and 1[bo5]·ΔFat controls.
* **I-065.**
  * R = X's opponent-adjusted pace: log(seconds per point ÷ the walk-forward norm), minus half the opponent's pre-match pace, averaged with a 52-week half-life and shrinkage K = 4.42 (σ²/τ² from split halves, 2013–2018).
  * **Gate:** split-half reliability 0.887 on 1,175 players, ≥ 0.3: **passes**.
  * Member R_A·Fat_B − R_B·Fat_A (+). R is 0 without timed history (women before 2016), with a missing indicator.
* **I-066.**
  * E_min = E_points(|logit q|, best of) × the pair's minutes per point.
  * E_points comes from Stage 2's simulator (20,000 matches per point of a 16-point grid). An even match gives 164 points in best of 3 and 270 in best of 5.
  * Member (E_min − mean)·ΔFat (−). `m_set` is on.
* **Controls:** ΔFat, 1[bo5]·ΔFat, ΔR, the pace-missing and imputed differences; nearest sets_14d, iosD_hold, iosD_second_won. Eta-mod: the leverage s, ΣR, ΣFat, E_min, 1[imputed].
* **Diagnostics:** R²: I-063 0.791; I-065 0.213; I-066 0.046; block 0.277. Member correlations are at most |0.10|.

### B10 · arrival debt (the region map is built)
* **Geography: static tables from public facts, in f23.** No result is involved.
  * **Event country.** Stage 4's event table gives 97–100% of main-tour and Challenger matches. A supplement of 61 blank names is read from the city in the name. ITF events take the IOC code in the tournament id (100%).
  * **Team events.** Olympics, ATP Cup, United Cup, Hopman Cup, Laver Cup and the Davis Cup and BJK Cup Finals are placed by name and year. Other ties name two nations: they get a region only when both share it.
  * **Regions and offsets (the family's BOD-R2, R3).** The brainstormer's 81-code map plus its extension: EU, ME, AS, OC, NA, SA, AF. Offsets +1, +4, +8, +10, −6, −3 hours (AF +1), with India +5.5 and Kazakhstan +6, as a circular difference.
  * **Venue-zone table (a sensitivity only).** Standard offsets with approximate DST rules, city keywords for multi-zone countries and US state codes. It correlates 0.885 with the proxy on ΔJL.
* **Members:**
  * **I-059:** W·e^(−gap/2)·(1 + 1[region change]), with W = played wins at the previous event. τ = 2 is the math audit's value; μ = 1 is fixed here.
  * **I-088:** 1[a won final whose lf is ≤ 9 days before es] × 1[first match here].
  * **I-060:** Wk·(1 + 0.05(age − 28)+) + 0.1·Away. Wk = consecutive played Monday weeks; Away = weeks since the last match in the home region, capped at 26.
  * **I-074:** JL = (1.5·ΔZ+ + 1.0·(−ΔZ)+)·(1 − T/|ΔZ|)+·(1 + 0.05(age − 28)+). a, b, c and ρ are fixed here.
* **Controls:**
  * Component differences: W, e^(−gap/2), travel, first, title, Wk, Away, age, Fat, Fit (21 days), |ΔZ|.
  * sets_14d, the travel, Away and ΔZ missing differences.
  * Nearest adjperf_tpw_2w, form_hold, form_brk.
  * Eta-mod: the symmetric missing indicators only. The family's row lists no Σ·η terms.
* **Diagnostics:**
  * The previous event's region is known for both players in 97.2% / 97.6% (2014–21) and 98.2% / 98.8% (2022–24) of matches.
  * Jet-lag trigger (|ΔZ| ≥ 5 h within 5 days, either player): 1.8% / 1.1% (2014–21), 1.4% / 0.65% (2022–24).
  * R²: I-059 0.163; I-088 0.060 (non-zero 2.7% / 1.8%); I-060 0.195; I-074 0.022 (non-zero 3.4% / 2.9%); block 0.227.
  * corr(I-059, I-088) = 0.42.
* **Open:** with ΔWk and ΔAway as controls (the round-1 card), I-060 is identified only through its age term.

### B11 · on-site rhythm
* **Members:**
  * ΔOn, with On = log(1 + played matches already at this event, qualifying included).
  * I-075: Δ[On·Nov], with Nov = 1[surface switch] + 1[indoor switch] + 1[region change] (the family's BOD-R4).
  * I-076: r_A·c_B − r_B·c_A, with c = first match here × (another surface or more than 10 days since the last match).
  * All declared +.
* **Indoor status:** Stage 0 for men's main tour, else tennis-data's Court field (both tours' main tour; matched rows, else the event's majority). Challenger and ITF statuses are unknown and count 0, with missing indicators.
* **Controls:** sets_14d, ΔNov, Δc, three missing differences; nearest elo_overall, elo_games, ratings_iid. Eta-mod: ΣOn, ΣNov, Σr, Σc.
* **Deliberate deviation from the literal union rule:** I-075's ΔOS **is** member ΔOn, and I-076's Δr is its linear twin, so neither is a control. Either would leave I-051's member unidentified. `STRICT_UNION = True` restores them; this is the orchestrator's call. **Ruled (checkpoint 1, R-2): keep `STRICT_UNION = False`.** B11 tests on-site rhythm as a whole, ΔOn's main effect included; a B11 result may be attributed to I-075 or I-076 only if the per-member decomposition (the sensitivities "B11 member …") supports it.
* **Diagnostics:**
  * R²: On 0.497; I-075 0.138; I-076 0.428; block 0.476.
  * Member correlations 0.39, 0.64, 0.31.

### B-SWITCH · own switch state × own style or age (Wald, 4 df, slow)
* **Columns:**
  * c1 = Δ[q·shape], with q = 1[surface matches this season < 3] and shape = cell-centred D^spw − O^spw.
  * c2 = sgn(surface)·Δ[New·Sty], with Sty = −shape, sgn +1 grass, −1 clay, 0 hard.
  * c3 = Δ[New·(age − 28)], with New = e^(−n/2)·log(1 + layoff/30); the layoff is capped at 1,095 days when missing.
  * c4 = Δ[In·Sty], with In = e^(−m/2) after an indoor/outdoor switch and m = matches since it. Both tours' status comes from Stage 0 or Court.
* **Constants:** ν = 2 and the threshold 3 are fixed by the math audit; ν_In = 2.
* **Controls:**
  * ΔO^spw, ΔD^spw, the surf_season and surf_layoff differences, Δq, ΔNew, Δ[New·Sty] (unsigned), Δage, ΔIn, In-missing.
  * Nearest prod_hold, prod_first_won, iosO_first_won.
  * Eta-mod: Σq, Σshape, ΣNew, Σage, ΣIn, sgn.
* **Diagnostics:** R² per column 0.211, 0.010, 0.101, 0.248. Defined for 100% of model matches; women's indoor status now comes from Court.

### B-INJ · hidden impairment
* **Return and gap.** A return is a match after a gap of 42 days or more that exceeds E. E = the field's mean of min(gap, 90) for the same tour, week and ranking band in the three previous seasons, walk-forward on the clock.
* **Members:**
  * **I-043:** U·e^(−n/2)·(1 + 0.05(age − 28)+ + 0.5·inj + 0.5·PR/SR), with U = log(1 + gap − E) and n = matches since the return.
  * **I-044:** inj44·1[gap ≥ 56]·1[n ≤ 2]·(Elo at the return − the tour mean), with inj44 = injury start or PR entry.
  * **I-045:** −(shrunk within-event slope of the serve z-residual). This is the decay, so the sign is − as the block declares: a decaying serve predicts losing, and the slope itself would carry +.
* **Constants:** ν = 2, ρ = 0.05, η = ψ = 0.5 and 42 / 56 days are fixed in advance (math audit: "fixed in advance, not tuned"). I-045's τ² = 0.0039 (2013–18).
* **Gate (I-045, declared):** across 39,555 player-windows, the first-in and first-won slopes correlate at r = 0.0096; the three binomial replays give 0.0099, −0.0087 and −0.0003 (mean 0.0003). **Passes as declared**, but not with a 2-SE margin (SE 0.005).
* **Controls:** ΔU, Δage, surf_layoff difference, I-044's term without e_pre, elo_overall (Δe_pre), form_first_won, form_first_in; nearest sets_14d, elo_games, ratings_iid.
* **Diagnostics:**
  * R²: I-043 0.240; I-044 0.014 (non-zero 1.4% / 1.1%); I-045 0.031; block 0.103.
  * Members are uncorrelated (|r| ≤ 0.02).

### B-HOME · home crowd and hype (Wald, 2 df; fixed trait: country)
* **Built:**
  * H = 1[the player's country, read through Stage 4's ISO-to-IOC aliases, equals the venue]. The venue comes from Stage 4's table, else the supplement, else the finals' host by year.
  * c1 = ΔH·1[250 or 500]; c2 = Δ(H·wc).
  * `trait: fixed`, `trait_cols: ["country"]`, `wald: True`. The batch permutes countries within tour and re-runs the builder; the nearest list is fixed for that reason.
* **Controls (the family's):** ΔH, Δwc, the home-missing difference; nearest elo_overall, elo_games, ratings_iid. Eta-mod: g only.
* **Diagnostics:**
  * Non-zero 17% / 14%. R² 0.045 and 0.118.
  * Monte Carlo is coded Monaco, though the club is in France: a limitation.

### B-STATE · fatigue-contaminated form (BOD-C1 alone after checkpoint 1, R-1)
* **INFO-1 (now a descriptive sensitivity only), built as the round-2 ruling formulates it:**
  * K = the player's own earlier matches with lf + 1 > es (looking back 8 rows).
  * Each completed pool match with a box score gets the ridge's exact one-step update of the player's own spw O and D.
  * The update uses the panel's surface-IOS states at that match's es and Stage B's constants: h = 52 weeks, κ = 1, τ = 1, typical units 73.7 / 70.6.
  * Opponents are held. Member (+).
* **BOD-C1, the row's only member:** PastFat = the mean pre-match Fat over the player's own played matches in the 14 days before; x = ΔPastFat (+), standardised.
* **Controls:** adjperf_tpw_2w, ios_points_short, ΔFat, sets_14d, the update-missing and PastFat-missing differences; nearest form_brk, form_hold, form_rpw_first (recomputed for BOD-C1 alone).
* **Diagnostics:**
  * R²: BOD-C1 0.669 (rebuttal 0.67), the row's x since R-1; INFO-1 0.056 (the two-member block was 0.278).
  * Either player has an uncounted own match in 34.6% / 37.2% of matches (2014–21) and 30.8% / 2.6% (2022–24): the clock-width collapse for women.
  * An update cannot be computed in 2.5% / 8.3% (2014–21).
* **INFO-1's premise fails (observed, result-free).**
  * **The check.** Where the player's previous match was uncounted (n = 22,696 player-matches), the panel's own IOS change from that match to this one (O_m − O_k, same surface) correlates **0.879** with this update, slope **1.10**. Where it was already counted (n = 68,979), the figures are 0.877 and 1.14.
  * **The cause.** The leak-proof IOS's incremental step already adds each player's uncounted own matches to his own block (`match_timing/ios_time.py` and `surface_ios/ios_surface.py`, docstrings).
  * **The consequence.** INFO-1 double-counts information the model already has. **Ruled out of the block (checkpoint 1, R-1, F-1):** `USE_INFO1 = False`; `bdst_info1` left the deployment columns; B-STATE = BOD-C1 alone (sign +, weight 0.5, the same controls, the update-missing flag included as ruled); nearest inputs recomputed by the module's rule: form_brk, form_hold, form_rpw_first (the same three, reordered), fixed in `NEAREST`. With one member, x is missing where PastFat is (no played match in the 14 days before): coverage 81.6% / 79.0% (2014–21), 83.9% / 80.2% (2022–24); S11 applies. R² 0.669. INFO-1's column remains as the descriptive sensitivity "B-STATE INFO-1 (descriptive)".

## The probe-equivalent check (`round2/body/probe_body.py`)

* **Design.** probe.py's logic, applied to these builders. For each cut day D, every match that could start after D is either reversed (winner flipped, the two box scores exchanged) or removed. All 11 rows are then rebuilt.
* **The comparison.** Every prepared per-player value, and every x, of each match with lf ≤ D is compared with the unchanged build (tolerance 1e-9).
* **The cuts.** Reversal at 2016-09-07, 2019-01-23, 2023-09-06 and 2024-08-14; removal at 2016-09-07 and 2023-09-06.
* **What is held fixed.** The blocks' 2014–2021 standardisation constants and the modulators' centring means are recorded and replayed: they rescale a column uniformly and carry no match's information. Upstream inputs keep their own probes: leak-proof IOS, Elo, Stage 3 and the surface-IOS states.
* **Result: passed, 66 of 66.** No early value moved. Later matches did move, so the check has teeth: for example, B9a changes 35,586 later rows under the 2016 reversal.
  * I-053 is unchanged under reversal by construction (loads and ages do not depend on who won), but changes 35,776 later rows under removal.
  * B-HOME depends on the panel only.
* **Two faults the probe found, both fixed before this run:**
  * Unfrozen standardisation moved block columns. This was a global rescale, now held.
  * A global prefix sum in I-045's window slope moved one early row by about 1e-9 through floating-point rounding. The prefix sums are now within-player, in f26 and in f28's PastFat.

## Open issues for the auditor and the orchestrator

1. **INFO-1:** resolved: out of B-STATE (checkpoint 1, R-1); a descriptive sensitivity only.
2. **B11's controls:** resolved: `STRICT_UNION = False` (R-2); the per-member decomposition is exposed for the batch (F-6).
3. **Block signs:** encoded + on the oriented sum, like every other block module. The family's "−" is the members' declared sign. Checkpoint 1 confirms the orientation (no signed-sum block reverses its test, §1.2).
4. **I-063:** kept as built (checkpoint 1, R-3): −D/κ ≈ s(1 + η)·ΔFat for either sign of κ; κ̂ < 0 is a result-free sign of survival selection and may not be cited at M2 for or against fatigue.
5. **I-045's gate:** kept as declared (checkpoint 1, R-4): 0.0096 against the replays' mean 0.0003; one replay (0.0099) exceeds it and the margin is under 2 SE, so the member is probably noise. I-058 passes both ways.
6. **B9a's trait:** resolved: slow-trait widening gates; the height permutation is a diagnostic (R-6, F-2).
7. **Coverage shifts for the final test:** women's minutes (imputed before 2016), women's INFO-1 prevalence (2.6% in 2022–24), and women's heights (64% non-zero in 2022–24). Read beside the replication.

## Files

* **Builders:** `src/eda/feature_interactions/features/f20_fatigue.py` (shared machinery, I-053, B-LOAD, B-PREV), `f21_constitution.py` (B9a), `f22_demand.py` (B9b), `f23_arrival.py` (B10, with the geography tables), `f24_onsite.py` (B11), `f25_switch.py` (B-SWITCH and the indoor status), `f26_impairment.py` (B-INJ), `f27_home.py` (B-HOME) and `f28_state.py` (B-STATE). f29 is unused.
* **Checks:** `src/eda/feature_interactions/round2/body/prechecks.py` (constants and gates), `diagnostics.py` (coverage, members, sensitivities, the INFO-1 premise check) and `probe_body.py`.
* **Outputs:** `data/studies/feature_interactions/round2/body/` (`prechecks.json`, `diagnostics.json`, `probe_body.json`). The partial table is `data/studies/feature_interactions/hypotheses/partial_f20_fatigue+…+f28_state.csv`.
