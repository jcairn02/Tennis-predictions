# R1 proposal: the speed state model (agent 2, Bayesian state modeller)

7 October 2026. Written without reading the other R1 files.

**Labels.** *Observed* means computed here (§11 names the script and output). *Inferred* and *suggestion* are marked as such.

**Rules followed.** No match result was read. Statistic targets and prices were used on seasons ≤ 2023 only. For 2024–26 only values, counts and distributions were computed. Scripts are `src/eda/serve_speed_tabpfn/design/modeller_*.py`; outputs are `modeller_*` in this folder.

## 0. Recommendation in five lines

1. Replace the 14-day window with the posterior mean of a robust two-state Kalman filter on each player's own timed matches. The level is a random walk; the fast state f is mean-reverting with a 14-day half-life. The primary column is **`spd_f` = f̂_A − f̂_B** (diff, km/h).
2. Each match's noise is ν_basis + σ²_serve/n, with innovations clipped at 2 SD. The level prior is diffuse. When nothing is known, f̂ = 0 (the prior mean), never NaN. Constants are frozen on speeds ≤ 2023.
3. On 2023, out of sample, it predicts the next match's speed deviation with R² **0.051** [0.030, 0.074] against x_raw's **0.019** [−0.002, 0.052]. The difference is +0.032 [+0.009, +0.052], filter better.
4. The mechanism gate passes. +1 SD of f̂ goes with **+0.34 pp first-serve points won** [+0.22, +0.46] and **+0.17 pp serve points won** [+0.08, +0.25] in the match, beyond box-score form. It holds across events.
5. Ranked columns: `spd_f`; the registered `x_raw` (the comparator); the posterior-SD pair (secondary). Women get the same column, with the men's dynamics.

## 1. Definitions

For player i, each timed match j has a centred speed z_j = y_j − o_sys(j) and n_j timed first serves in.

```
z_j    = L(t_j) + f(t_j) + e_j,          e_j ~ N(0, nu_b(j) + s2_serve / n_j)
L(t+D) = L(t) + eta,                     eta ~ N(0, q D)              prior L ~ N(0, 1e6)  (diffuse)
f(t+D) = phi f(t) + w,  phi = 2^(-D/h),  w ~ N(0, s2f (1 - phi^2))    prior f ~ N(0, s2f)
update: v = z - L^ - f^,  S = 1'P1 + R,  v <- sign(v) min(|v|, c sqrt(S)),  K = P1 / S
```

* **Side value before match m:** f̂_m = E[f(es_m) | own history], and σ̂_m is its posterior SD.
  * Own history means timed matches of earlier events, plus earlier rounds of the same event.
  * It never includes the same round or other events of the same week.
* **Columns:**
  * `spd_f` = f̂_A − f̂_B (diff);
  * `spd_sd_a`, `spd_sd_b` = σ̂ (pair);
  * `x_raw` as registered (diff, NaN when missing).
* **Constants, men.** Tuned by one-step-ahead MSE of the next match's centred speed on ≤ 2022:
  * h = 14 d, s2f = 12 km/h², q = 4 km/h²/yr, c = 2.0;
  * ν_pm = 7 and ν_ks = 8 km/h²; σ_serve = 13.5 km/h.
  * Every optimum is interior to the grid, and both panels gave the same values.
* **Constants, women:** the men's h, s2f and q; ν_pm = 14, ν_ks = 10, c = 4, σ_serve = 10.7 (§4).
* **Offsets o_sys.** Least squares on pairs of the same player's blocks (one edition each) in different systems within ±60 days, on ≤ 2023.
  * Men, against the ManTennisData tour level: AO −5.4, RG −4.6, USO −7.6, W −2.5, Challengers +1.3.
  * Women, against AO: RG −1.7, USO −1.8, W +1.3.

## 2. Data and harmonisation

* **Sources.**
  * Held point means, whose `spd1_sq` gives the per-serve variance.
  * ManTennisData's key statistic, with n = `ks_first_in`.
  * The AO and RG 2025–26 point means.
  * The plausible range is 40–270 km/h. Men's values below 120 km/h count as missing (suggestion).
* **Panel (suggestion to the engineer).** Use the key statistic first at tour level, which gives one basis from October 2021 to 2026, as in the test years. Use point means at the Slams. A point-mean-first panel scores slightly better on 2023 (f̂ R² 0.077), but it would switch basis between training and test.
* **Key statistic against point mean** (observed, 5,508 ATP matches ≤ 2023):
  * The median gap is +0.52 km/h, with a robust SD of 0.62. In 58% of matches the key statistic is the point mean rounded up.
  * But in 12.3% they differ by more than 3 km/h.
  * Where they disagree, the key statistic is farther from the player's other matches in 71% of cases. Hence the basis-specific noise and the clipped update.
* **System offsets drift by edition** (observed, within-player pairs within ±60 days against Infosys tour level):
  * AO −4.7, RG −3.9, W −1.5, USO −7.4 km/h.
  * RG 2022 is −5.7 but RG 2023 is −1.9.
  * The point-sequence offsets imply RG −7.8, about 4 km/h further (inferred: composition).
  * Edition shifts have an SD of 1.4 km/h. Centring history on them did not help, even as an oracle (R² 0.040 against 0.051), so it is not proposed.
* **Reproduction check.** On point means, my windows reproduce the registered x_raw exactly: 2,891 of 2,891 men's 2022–23 values.

## 3. Variance decomposition (≤ 2023; km/h², net of serve sampling)

| Component | Men | Women |
|---|---|---|
| Per-serve SD (km/h); players' 10–90% range | 13.5 (10.3–16.8) | 10.7 (7.7–13.6) |
| Sampling variance of one match mean (n ≈ 43) | 4.2 | 2.7 |
| Match-day variance ν (robust nugget) | 6.4 point mean / 9.7 key statistic | ≈ 9–10 |
| Fast state: variance / half-life | 11.7 / 11.5 d (point mean); 17 / 10 d (key statistic) | not identifiable |
| Slow drift, per year | 1.1–1.7 | – |
| Edition-shift SD within a system (km/h) | 1.3–2.0 | 1.4–1.9 |
| Between-player level SD (km/h) | 8.8 | 8.5 |
| Year-on-year level change, SD (km/h) | 3.2 | 3.7 |
| Correlation of the two players' residuals in a match | 0.19 | 0.13 |
| Level against height | r = 0.63 (0.76 km/h per cm) | r = 0.55 |

* **The state is fast** (inferred). Its correlation is about 0.73 at 11 days, 0.5 at 3 weeks and about 0 from 6 weeks.
* **One match is half noise.** Its mean carries noise ν + σ²/n ≈ 11, against a state variance of ≈ 12.
* **How much of x_raw is signal** (observed, men):
  * Its SD is 4.9 km/h.
  * The target match's own deviation has a slope of 0.53 on it, with a correlation of 0.41. So about half of x_raw is persistent signal.
  * On centred speeds the slope is 0.39, 0.48 and 0.60 with one, two and three or more matches in the window.
  * Raw x_raw is biased by +2.1 km/h at tour-level targets, because the Slams in its 364-day window read slow.

## 4. Missing and thin data; priors

* **No timed match lately.** f̂ decays with the 14-day half-life. Its mean absolute value (observed, 2023):
  * 1.79 km/h within 3 days of a timed match;
  * 0.74 at 14–28 days and 0.30 at 28–56 days;
  * 0.02 beyond 56 days.

  Meanwhile σ̂ rises from 2.6 to √12 = 3.46.
* **None in a year, or ever:** f̂ = 0 and σ̂ = 3.46. This is the prior, not a guess.
* **The level prior must be diffuse.** For players with 1–2 timed matches (n = 409), the correlation of f̂ with the career level is:
  * 0.51 with a population prior;
  * 0.44 with a height prior;
  * 0.14 with a diffuse prior.

  An informative prior leaks the level into the change, which is D1's critique of `x_shot`. So no population prior: height would only matter for a level column, which I do not propose.
* **Women.** Slam-only data cannot separate a slow state from the level: their own tuning drifts to a 90-day half-life. Borrowing the men's dynamics raises the women's gate from +0.28 to +0.37 pp/SD of first-serve points won (§6).

## 5. How it enters TabPFN

* **`spd_f` is one diff column, with 0 when nothing is known, never NaN.**
  * The reason: if the outcome is linear in the true state, the data act only through f̂. So 0 is the Bayes value, and no reliability input is needed.
  * The evidence (2023): the calibration slopes of the next match's deviation stay flat across window strata for f̂, but not for x_raw.

    | Matches in the 14-day window | 1 | 2 | ≥ 3 |
    |---|---|---|---|
    | f̂ | 0.80 | 0.69 | 0.85 |
    | x_raw | 0.15 | 0.22 | 0.33 |

    x_raw would need a learned reliability interaction.
  * TabPFN's NaN handling (inferred) is a constant plus a flag, which would throw away decayed states.
* **Coverage** (men's matches, 2024 / 25 / 26):
  * both players timed within 28 days: 78 / 73 / 69%;
  * at least one: 95 / 89 / 87%;
  * x_raw present: 61 / 50 / 48%.
* **Spread.** SD(`spd_f`) is 2.1–2.7 km/h in 2022–26, against 0.7–1.2 before 2021.
* **New information** (2022–23, price look). `spd_f` has R² 0.12 on the 58 inputs and 0.003 on the close.

## 6. Result-free tuning targets and gates (≤ 2023)

**Next-match speed.** The target is the 2023 match's deviation from its 364-day mean (men, key-statistic panel). Constants and slopes are from ≤ 2022, with 4,262 player-matches; "Match corr" is the A − B correlation over 2,013 matches.

| Candidate | R²_oos [95% block CI] | Match corr |
|---|---|---|
| (a) x_raw as registered | 0.019 [−0.002, 0.052] | 0.155 |
| (a′) the same on centred speeds | −0.011 [−0.052, 0.044] | 0.161 |
| (b) Empirical-Bayes-shrunk 14-day deviation | −0.005 [−0.043, 0.048] | 0.162 |
| (c) 10-day half-life mean − 364-day mean | 0.015 [−0.021, 0.058] | 0.179 |
| **(d) f̂ (Kalman)** | **0.051 [0.030, 0.074]** | **0.191** |
| (d′) L̂ + f̂ − 364-day mean | 0.070 [0.024, 0.114] | 0.259* |

\* (d′) shares the 364-day mean with the target, so part of its edge is mechanical. In the gate below, f̂ beats it.

* **Paired gains** (positive = the filter better):
  * f̂ − x_raw: +0.032 [+0.009, +0.052], and +0.038 [+0.017, +0.055] on the point-mean panel.
  * Level forecast, MSE(364-day mean + b·x_raw) − MSE(L̂ + f̂): +1.75 km/h² [+0.45, +2.83]. On the point-mean panel it is +1.28 [−0.26, +2.60], a tie.
* **Rejected variants:** an event component per tournament (tuned to variance 0) and edition centring.

**Mechanism gate.** Men, 2022–23, 32,720 player-matches.
* Model: weighted least squares on the player's own 364-day and two-week box-score rate, his speed level, the opponent's conceded rate, surface and level.
* Effects are pp per SD, with 28-day-block intervals. Positive = speed above his norm serves better than his form says.

| Target | f̂, all | x_raw, all | f̂, history from earlier events only (8,762) | Two-week box form (scale) |
|---|---|---|---|---|
| Aces per serve point | +0.14 [+0.09, +0.20] | +0.12 [+0.07, +0.19] | +0.18 [+0.09, +0.28] | +1.13 |
| First-serve points won | **+0.34 [+0.22, +0.46]** | +0.18 [+0.05, +0.30] | +0.39 [+0.21, +0.60] | +0.64 |
| Serve points won | **+0.17 [+0.08, +0.25]** | +0.14 [+0.04, +0.24] | +0.27 [+0.07, +0.45] | +0.49 |

* **Same event.** With an earlier round of the same event in the history, first-serve points won rise to +0.81 [+0.54, +1.11].
* **Drift** (L̂ − 364-day mean) adds only aces: +0.075 [+0.036, +0.108].
* **Point-mean panel:** serve points won +0.20 [+0.12, +0.28].
* **Women** (Slams 2016–23, men's dynamics): first-serve points won +0.37 [+0.23, +0.49]; serve points won +0.16 [+0.03, +0.29]; aces tie.
* **Verdict:** a speed change is a real serve-form state that persists across events, beyond box-score form.

## 7. Leak argument

* **Own history is safe by construction,** under speed_build's rule. Decay runs to the target's `es`; against `obs`, the correlation is 0.9998.
* **Pooled constants are frozen on speeds ≤ 2023.** That covers the six filter constants and the offsets. None follows the clock or reads 2024–26.
  * The 2019–23 calibration fits will use constants that saw those seasons' speeds, never their results. The brief allows this.
* **Probe** (observed). For 8 cuts and 3,000 frame player-matches of 2021–26, every speed from the cut on was replaced with noise.
  * **0 values changed before the cut, and 0 at it.**
  * A leaky control did change at the cut.
  * The offsets were unchanged with every post-2023 speed randomised.
* **R4 suggestion:** ≥ 25 cuts with 2024–26 targets, plus an independent re-implementation of the update.

## 8. Expected effect and power (inferred)

* **Serve channel only.**
  * Serve points won rise 0.153 pp per km/h of f̂ [0.070, 0.230].
  * A Markov match model gives 0.199 log-odds per pp of serve points won at best of three (0.249 at best of five).
  * Together: 0.030 log-odds per km/h of `spd_f` [0.014, 0.046]. That is **β ≈ 0.067 per SD**, or about 0.43 mLL per men's match if unpriced.
* **The published effect** is 0.090 per SD of x_raw. f̂'s higher match-level correlation (0.191 against 0.155) suggests about 1.2 times the per-SD effect. It also covers 87–95% of men's matches against 48–61%.
* **Power.** A logistic-offset test on the 7,070 men's 2024–26 matches has SE ≈ 0.027. Power is 0.69 at β = 0.067 and 0.38 at 0.045. TabPFN learns less than such a test; the strategist owns arm power.
* **Caveat.** "Beyond box-score form" is not "beyond the full model or the close".

## 9. Cost

CPU only: the frame build takes about 15 s and the probe 30 s. The column adds no GPU fits by itself.

## 10. Risks

1. **Key-statistic tails** (12% of matches off by more than 3 km/h). The clipping absorbs them. A panel that mixes bases within a player needs the +0.5 km/h basis offset.
2. **Edition shifts** (AO 2024 about +3; RG 3.8 km/h apart between 2022 and 2023). The fast state absorbs most of this, and within an edition it cancels in A − B.
3. **Era shift.** Men's values before 2022 are mostly 0 outside the Slams.
4. **Gaps are overweighted.** With an empty 14-day window the 2023 slope is 0.31, though f̂ is small there (SD 0.64). R3 could tune h on first-round targets.
5. **Women's dynamics are borrowed** from the men.
6. **The gate's controls** are box-score form only.

## 11. Claims checked on disk

Every script runs as `./python.sh src/eda/serve_speed_tabpfn/design/<script>` and writes its output to this folder.

| Script | Output | What it backs |
|---|---|---|
| `modeller_variance.py` | `.json`, `_variogram_tour.csv` | §3 and the offsets by edition |
| `modeller_basis.py` | `.json` | Key statistic against point mean |
| `modeller_state.py ks_first`, `pm_first` | `modeller_state_*.json` | Candidates, tuning, level forecasts |
| `modeller_state3.py` | `.json` | The event component |
| `modeller_extras.py` | `.json` | Priors, edition oracle, calibration by stratum |
| `modeller_gate.py <panel> <tour> [mendyn]` | `modeller_gate_*_atp.json`, `_wta*.json` | The gate (`modeller_gate_ks_first.json` is superseded) |
| `modeller_features.py ks_first` | `.parquet`, `.json` | Columns, coverage, probe |
| `modeller_redundancy.py`, `modeller_esobs.py`, `modeller_power.py` | `.json` each | New information, `es` against `obs`, β and power |
| `modeller_repro.py` | `.json` | The exact x_raw reproduction (2,891 of 2,891; none extra, none missing) |

## 12. Looks (no match result in any)

| # | Seasons | What was related to what | Script |
|---|---|---|---|
| 1 | ≤ 2023 | Speeds against speeds: variogram, offsets; x_raw against the target match's own speed | `modeller_variance.py`, `modeller_basis.py` |
| 2 | Tune men ≤ 2022 and women ≤ 2019; evaluate men 2023 and women 2021–23 | Candidates against next-match first-serve speed | `modeller_state.py`, `modeller_state3.py` |
| 3 | 2022–23 | f̂ under three priors against career speed level; edition-centred f̂ and calibration against next-match speed | `modeller_extras.py` |
| 4 | Men 2022–23; women Slams 2016–23 | f̂, drift, L̂ + f̂ − c52 and x_raw against next-match aces per serve point, first-serve points won and serve points won | `modeller_gate.py` |
| 5 | 2022–23 | `spd_f`, `spd_dev` and x_raw against the 58 inputs, including `in_odds_logit` (**price look**) | `modeller_redundancy.py` |
| 6 | 2013–26 | Values, coverage and SDs only for 2024–26; correlations with x_raw on ≤ 2023 | `modeller_features.py`, `modeller_esobs.py` |
