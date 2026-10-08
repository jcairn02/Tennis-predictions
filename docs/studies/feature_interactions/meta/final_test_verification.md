# The final test's code: verification on synthetic outcomes

7 October 2026. This is checkpoint 1 §6.3 item 9: `final_test.py` verified by an agent who did not write it. It covers [plan.md](../plan.md) ("Fixed at M1" rule 7, "M2: what the rules gave") and [the pre-registration](../preregistration.md). The version verified is the one with the coordinator's `column_arm` secondary (added during this verification; nothing else in the file changed).

**No real outcome was used.** No real 2025–2026 result was read, and no 2014–2025 fit saw a real result. Every frame was built without `a_won` (`verify_final/harness.py`: `tabpfn_tests.frame` with `a_won` never loaded, NaN until a synthetic draw fills it), and every fit and score in this note ran on synthetic draws. The η forecasts and the B-INJ column x are real: they are forecasts and features, not results. I did not count missing values of the real `a_won`; that would read the result column (see fix 4).

## Verdict: sign off with fixes

The primary, the effect size, the nudge, the calibration, the population gate and the result-free `--check` all do what rule 7 and the pre-registration say:
* x is preprocessed exactly as in the screen;
* every walk-forward fit uses only seasons before its test season;
* the effect size is unbiased;
* b's interval covers its expected value.

Before the hash:
1. **Fix bug 1.** Every one-tour primary is NaN, so the pre-registered per-tour secondary would come out empty.
2. **Correct the pre-registration's power lines.** As coded, the primary is conservative: its two-sided size is 2.35%, not 5%. Its power is below the stated "MDE about 0.50 mLL, power about 25% at the expected gain" (§3.1):
   * 16% at 0.1 mLL, 34% at 0.2 and 72–76% at 0.5;
   * MDE about 0.57 mLL;
   * about 19% at the expected 0.12 mLL.

Fixes 3–5 make the one run safe and are strongly recommended. The rest are notes.

## 1. Bugs and fixes

**Bug 1 (must fix): the primary is NaN on any one-tour population.**
* `tabpfn_tests.encompassing` builds one cubic column per tour in `C.TOURS`. For a tour absent from the rows, `sd = np.std(e3[tour == t_]) or 1.0` is NaN: `np.std([])` is NaN, and NaN is truthy, so `or 1.0` keeps it.
* The column becomes 0/NaN, and b, se and the interval are all NaN.
* `run()` writes them silently: the "atp" and "wta" subsets give b = NaN (reproduced, `verify_final/tour_subset_bug.py`). Their effect sizes are unaffected.
* Exact fix, keeping `tabpfn_tests.py` (hashed in `hypotheses/prepare.json`) untouched. In `final_test.primary`, replace `return TT.encompassing(f, z0, lf - lb)` with:

```python
    tours, saved = tuple(t for t in C.TOURS if (f["tour"] == t).any()), C.TOURS
    C.TOURS = tours                      # encompassing builds one cubic column per tour present
    try:
        return TT.encompassing(f, z0, lf - lb)
    finally:
        C.TOURS = saved
```

* The pooled result stays bit-identical, and each tour gets a finite b (atp 0.80 [−0.98, +2.58], wta 1.34 [+0.04, +2.64] on one synthetic draw).
* The equivalent fix inside `encompassing` is `k = tour == t_; if not k.any(): continue` before the cubic column. It would change a hashed builder file, so it needs a ledger row.

**Fix 2 (must, pre-registration text): power.** Replace the "Power" bullet with this. The values come from this code on these 8,520 matches and 21 blocks (§3.1–3.2):

> **Power** (measured on synthetic outcomes with the final test's code, meta/final_test_verification.md). Under independence the two-sided reading's size is 2.4%: the largest-of-three variance is conservative. Its power is 16% at 0.1 mLL, 34% at 0.2 and 72–76% at 0.5; the MDE (80%) is about 0.57 mLL. **The power at the expected gain (0.12 mLL) is about 19%.** **A tie is the likely reading even if B-INJ is real**; a tie does not refute the 2014–2024 evidence (z_joint 3.99, both windows in the declared direction).

**Fix 3 (strongly recommended): write the reading before the secondaries.**
* `run()` writes nothing until every secondary has finished.
* `T.compare` returns no `lo`/`hi` when no row is scorable, so `polymarket()` and `column_arm()` raise `KeyError` on an empty comparison. One failing descriptive secondary would therefore lose the once-only primary.
* Today every row is covered:
  * the 2,648 and 1,067 Polymarket rows all have early forecasts;
  * `binj` covers every 2019–2026 match;
  * no forecast or x is missing.

  The crash cannot happen with today's files.
* Exact change in `run()`: move the subset loop into a local `def subsets(): ...; return sub`, then replace everything from `sub = []` to `res["column_arm"] = column_arm(f)` with:

```python
    C.write_json(OUT / "final_results.json", res)          # the reading is on disk before any secondary runs
    for key, fn in (("subsets", subsets), ("polymarket", lambda: polymarket(f, xs, params)),
                    ("column_arm", lambda: column_arm(f))):
        try:
            res[key] = fn()
        except Exception as e:                              # a descriptive secondary never costs the reading
            res[key] = {"error": repr(e)}
        C.write_json(OUT / "final_results.json", res)
```

**Fix 4 (recommended): refuse missing outcomes loudly.**
* A NaN `a_won` among the 2025 rows (the 2026 nudge's history) or the test rows makes the parameters or the primary NaN without an error.
* Add, after the hash check in `run()`: `if f["a_won"].isna().any(): raise SystemExit("missing results in the population")`.
* Add the same check in `history_frame` before returning. `column_arm`'s calibration frames (2019..Y−1) need it too: a NaN there gives NaN slopes and the `KeyError` of fix 3.
* If a check fires, the population changes, and that is a pre-registration amendment made before any result is computed.

**Fix 5 (recommended): hash every input of the run.**
* `run()` checks only the population hash.
* Today these all equal `prepare.json` (`verify_final/input_hashes.json`): all 155 base forecast files for 2014–2026, the model frame and the pre-rebuild Stage 0.
* Not hashed anywhere:
  * `final/binj_x.parquet` (`d64593c3…` in `check.json`);
  * `surface_elo_pieces/early_price_frame.parquet`;
  * the `binj` 2025–2026 forecast files (seeds 0–7);
  * the code (`final_test.py`, `tabpfn_tests.py`, `screen.py`, `common.py`).
* Add `SHA256 <path>: <hash>` lines to the pre-registration's Hashes section, and have `run()` compare them before `population()`.

## 2. Code review against rule 7, the pre-registration and §6.3

| Item | What the code does | Finding |
|---|---|---|
| x preprocessing | `x_scaled`: on the screen's discovery rows (2014–2021, debut seasons out), clip at the 99th percentile of \|x\|, divide by the SD of the clipped values; missing → 0 | **Equal to `screen.prepare`**: max \|difference\| 0.0 on all 2014–2024 screen rows (clip 6.024, SD 1.478). No x is missing in 2014–2026. B-INJ has no η form, so nothing is evaluated at η |
| Nudge | `fit_nudge`: maximum likelihood, columns [η·atp, η·wta, x], no intercept, no cubic, b pooled; history = seasons 2014..Y−1, η = seed mean of the seeds held (0–2 / 0–5 / 0–15) | As specified. 2025 is fitted on 2014–2024 (50,087 matches), 2026 on 2014–2025 (55,192). **No 2026 row reaches any fit.** On synthetic data the fitted b is unbiased (§3) |
| B's calibration | `fit_calibration`: one slope per tour, no intercept, seasons 2019..Y−1 | As decided |
| Deployed arms | B = cal_tour·η; F = s_tour·η + b·x, per test season | As specified |
| Primary | z0 = seeds 0–7, z8 = seeds 8–15. `encompassing(f, z0, logit P_F[z8] − logit P_B[z8])`: slopes per tour × season, cubic per tour, the largest of three clustered variances (four-week block, shared player, union) × G/(G−1), t on G − 1 | As pre-registered: 21 blocks, 20 df. One-tour subsets give NaN (**bug 1**) |
| Effect size | 16-seed means, both arms deployed, paired log loss, four-week blocks, t on G − 1 | As specified; unbiased (§3) |
| Subsets | atp, wta, 2025, 2026, TML-clean | atp/wta primary NaN (bug 1). Seasons: 12 and 9 blocks (df 11 and 8). TML-clean: 8,145 matches. The flag reproduces the 573 men's Slam rows (RG 2026 97, Wimbledon 238, US Open 238), exposing 375 test matches |
| Polymarket | early block = the base with `odds_logit` replaced by the 24-hour price (`local_fits.queries`); `p_close_a` = the 30-minute price; move regression OLS without intercept, four-week clusters | As pre-registered. All 2,648 / 1,067 rows have early forecasts (398 in 2025, 2,294 in 2026, every seed) |
| Column arm (new) | `binj` vs B, seeds 0–7 each, each calibrated on its own forecasts from 2019..Y−1 | As the coordinator describes. Coverage is 100% (binj: seeds 0–2 in 2019–2024, 0–7 in 2025–2026). Unbiased at zero difference (§3) |
| Population gate | `run()` refuses unless the sorted-id SHA-256 equals the `POPULATION_SHA256:` line | Correct (§4) |
| Leakage | — | `--check` output depends on no result (§4). Parameters for season Y use seasons < Y only. x's constants come from 2014–2021. The column arm's calibration uses 2019..Y−1. All 155 base forecast files and the model frame equal the frozen manifest |

**Notes (no change needed).**
* *The effect size carries a calibration-window term.* F's slopes come from 2014, B's from 2019. With constant true slopes (the synthetic null), the longer window alone gives F +0.006 mLL. In real data the sign depends on drift. The primary is insulated:
  * under the null the deviation is mostly (s − cal)·z8 (in one null draw its SD was 0.005, against 0.0003 for b·x; across draws the fitted b has SD 0.010);
  * the offset's per-tour × season slopes absorb that term, leaving b to read x (b* median 0.005 at β = 0). F against B recalibrated from 2014 would isolate x in the effect size, as an optional descriptive.
* *`check()` holds `a_won` in memory without using it.* `tabpfn_tests.frame` lists `a_won`, and `screen.load` reads the whole model frame before cutting it at 2024. Dropping the column in check mode would be tidier.
* *The gate needs the line at column 0.* An indented `POPULATION_SHA256:` line refuses, which is safe.
* *TML exposure reads the event's tournament date.* It counts every row of the player's own event, later rounds and the match itself included: conservative for a clean subset. The pre-registration's rule (any exposure) is stricter than §6.3's "share under 20%" and counts no shares. That is a stated departure for checkpoint 2.
* *Seed counts.* The column arm's calibration histories (binj: 3 seeds; B: 16) and its 8-seed test forecasts differ in seed count. This is immaterial: SD(z0 − z8) = 0.008 in log-odds.

## 3. Synthetic checks

**Design** (`verify_final/harness.py`, `synth_power.py`).
* **The data-generating process (DGP).** The real η_B for 2014–2026 (the seed means of the seeds held; 16 seeds from 2019) and the real scaled x feed y ~ Bernoulli(σ(a_tour·η_B + β·x)), with a = 0.89 (men) and 0.91 (women).
* **One draw serves both sides.** Each replicate draws every season from 2014 to 2026. The same draw feeds the walk-forward fits (2014–2025) and the test (2025–2026), so the 2026 nudge sees the 2025 outcomes the test scores.
* **The code itself runs:** `final_test.parameters`, `primary` and `effect`.
* **β is set** so that the population gain on the 8,520 test matches (the oracle F over the best-calibrated B without x) is 0, 0.1, 0.2 or 0.5 mLL: β = 0, 0.0304, 0.0430 and 0.0680 per SD. The screen's b̂ was 0.042.
* **Expected values per replicate.**
  * b* is the encompassing regression refitted with the true probabilities in place of y, on the same deviation and nudge.
  * gain* is the expected paired gain of the two deployed forecasts under the true probabilities.
* **Replicates:** 2,000 at β = 0 and 1,000 per other setting. The Monte Carlo SE of a rate is about 0.3 points at the null and 1.2–1.6 points elsewhere.

### 3.1 The primary (b's two-sided 95% interval; positive = the bundle adds information)

| Population gain (mLL) | β per SD | Interval above 0 | Interval below 0 | Two-sided rejection | One-sided p < 0.05 | Median b* | b's interval covers b* | Fitted nudge b, 2025 (mean, SD) |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 0.9% | 1.45% | **2.35%** | 2.5% | 0.005 | 97.6% | 0.0004, 0.0100 |
| 0.1 | 0.0304 | **16.4%** | 0.1% | 16.5% | 27.3% | 1.01 | 97.3% | 0.0303, 0.0098 |
| 0.2 | 0.0430 | **33.5%** | 0 | 33.5% | 50.0% | 0.99 | 97.0% | 0.0436, 0.0101 |
| 0.5 | 0.0680 | **72.2%** | 0 | 72.2% | 84.6% | 1.00 | 97.8% | 0.0681, 0.0105 |

* **Size: 2.35%** two-sided (MC SE 0.34%). That is conservative, against the ≈ 5% expected.
* **b reads the nudge:**
  * Its expected value is 1 when x is real (median b* 0.99–1.01).
  * Its interval covers b* in 97–98% of replicates, consistent with the conservative size.
  * The fitted nudge b is unbiased for β.
* **Power against the critique's simulation** (two-sided):
  * 0.2 mLL: critique 0.33, here 33.5%.
  * 0.5 mLL: critique 0.77, here 72.2%. The breakdown run's independent draws give 75.5%, so 73.9% pooled over 2,000.
* **The MDE and the expected-gain power.** A fit of power(g) = Φ(k√g − c) through the 0.2 point and the pooled 0.5 point gives k = 4.10, c = 2.26; at 0.1 it predicts 16.8%, against the 16.4% observed.
  * **MDE (80%): about 0.57 mLL** (critique 0.55; pre-registration 0.50).
  * **Power at the expected 0.12 mLL: about 19%** (pre-registration 25%).
  * The pre-registration's noncentrality is right: its z of 1.41 at 0.116 mLL gives k = 4.13. The gap is the critical value: 2.086 (nominal t, 20 df) against about 2.26 for the code's variance.

### 3.2 Why it is conservative (`variance_breakdown.py`, 1,000 replicates per setting, the same coefficient, t with 20 df)

| Variance | Rejection, 0 mLL | Rejection, 0.5 mLL | SD of t at 0 |
|---|---|---|---|
| four-week block | 5.4% | 80.6% | 1.05 |
| shared player (dyadic) | 3.3% | 79.4% | 0.95 |
| union | 6.8% | 81.3% | 1.14 |
| **largest of the three (the code)** | **2.7%** | **75.5%** | 0.90 |
| model-based (inverse Hessian) | 3.2% | 79.6% | 0.95 |

* The largest variance is the player one in 57% of replicates. The median ratio of the largest to the model-based variance is 1.12.
* The synthetic outcomes are independent given η and x. So the table shows the rule's price under independence: it halves the size and costs about 5 points of power at 0.5 mLL.
* The model-based row is what an exact variance gives against t's 2.086 under independence (3.7% expected).
* *Inferred:* under the player dependence the rule guards against, which the critique found in the residuals, the size would sit nearer 5%.
* **No change to the rule is recommended; only the stated power must match it (fix 2).**

### 3.3 The effect size (F over B, mLL, positive = F better)

| Population gain | Mean gain | Mean gain* | Bias (MC SE) | Interval covers gain* | Interval above 0 | SD of the gain |
|---|---|---|---|---|---|---|
| 0 | +0.008 | +0.006 | +0.002 (0.002) | 95.5% | 3.75% | 0.079 |
| 0.1 | +0.107 | +0.106 | +0.001 (0.005) | 96.3% | 8.7% | 0.166 |
| 0.2 | +0.207 | +0.205 | +0.001 (0.007) | 94.8% | 14.8% | 0.233 |
| 0.5 | +0.497 | +0.505 | −0.008 (0.011) | 95.8% | 27.2% | 0.346 |

* The effect size is unbiased, and its interval has nominal coverage.
* gain* at the null (+0.006) is the calibration-window term (§2, notes).
* A tie stays the likely reading even at 0.5 mLL (27% above 0), as the pre-registration says.

### 3.4 Subsets at β = 0 (1,000 replicates), and per tour with bug 1's fix (`tour_fixed_size.py`)

| Subset | Blocks (df) | Two-sided rejection at 0 | Power at 0.5 mLL |
|---|---|---|---|
| atp or wta, as coded | 21 (20) | — (b is NaN in every replicate: bug 1) | — |
| atp, with the fix | 21 (20) | 3.2% | 42.7% |
| wta, with the fix | 21 (20) | 3.3% | 43.8% |
| 2025 | 12 (11) | 1.05% | — |
| 2026 | 9 (8) | 0.6% | — |
| TML-clean | 21 (20) | 1.0% | — |

The descriptive subsets are more conservative still: with fewer blocks, the largest of three is noisier.

### 3.5 The column arm at zero difference (`colarm_synth.py`, 1,000 replicates)

The DGP is y ~ Bernoulli(σ(a_tour·(η_binj + η_B)/2)) in every season from 2019 to 2026, so neither arm is the truth. The harness's frame hands `column_arm`'s calibration histories the same draw.

| Tour | Matches | Mean gain* | Mean gain | Bias (MC SE) | Interval covers gain* | Interval excludes 0 |
|---|---|---|---|---|---|---|
| both | 8,520 | +0.002 | −0.001 | −0.003 (0.004) | 96.3% | 3.7% |
| atp | 4,394 | +0.002 | +0.004 | +0.002 (0.005) | 95.2% | 4.7% |
| wta | 4,126 | +0.001 | −0.006 | −0.007 (0.006) | 95.4% | 4.8% |

The column arm is unbiased at zero difference, with nominal coverage.

## 4. The two modes

| Check | Result |
|---|---|
| `--check` with `a_won` never loaded (NaN) | `check.json` identical to the study's (computed with the real frame) |
| `--check` with `a_won` replaced by noise | identical again. Its output depends on no result. `build_x` was trapped and not called (the x file exists). Output written outside `final/` |
| `--run`, no `POPULATION_SHA256:` line | refused ("the population differs from the pre-registered one") |
| `--run`, wrong hash / indented line | refused |
| `--run`, no pre-registration file | refused (`FileNotFoundError`) |
| `--run`, the real pre-registration | passes the gate and reaches the first fit (trapped there; synthetic population) |
| `run()` end to end on synthetic outcomes (β for 0.2 mLL) | every branch completes and writes the JSON (primary, effect, five subsets, Polymarket, column arm). The atp/wta primaries are NaN (bug 1) |

## 5. Not checked here

* **Whether the real 2025–2026 `a_won` has gaps.** Counting them would read the result column; fix 4 makes the run refuse instead.
* **The TabPFN fits' training windows.** The base's files equal the frozen manifest. The `binj` 2025–2026 files (fitted today) are in no manifest (fix 5).
* **B-INJ's construction on the 2025–2026 rows** (the clock, the walk-forward field table): the red team's remit. Here only `build_x`'s reproduction of the frozen 2013–2024 column was relied on, as recorded in `check.json`, not re-run.
* **The real dependence structure.** The synthetic outcomes are independent; §3.2 says what that implies.

## Files

Scripts, all under `src/eda/feature_interactions/verify_final/` and run with `./python.sh`:

| Script | What it does |
|---|---|
| `harness.py` | result-free frames, the DGP |
| `inventory.py`, `early_keys.py` | forecast-file inventory |
| `sanity.py` | frame equality, x preprocessing, timing |
| `synth_power.py` | §3.1, §3.3, §3.4 |
| `variance_breakdown.py` | §3.2 |
| `tour_subset_bug.py`, `tour_fixed_size.py` | bug 1 |
| `colarm_synth.py` | §3.5 |
| `binj_coverage.py` | column-arm coverage |
| `modes.py` | §4 |
| `input_hashes.py` | fix 5 |

Outputs are in `data/studies/feature_interactions/verify_final/`: `*.json`, `synth_replicates.csv`, `colarm_replicates.csv`.
* `SYNTHETIC_end_to_end/final_results.json` holds a synthetic run, **not** the final test.
* `check_result_free/check.json` is `--check`'s output with no result loaded.
* The study's `final/` folder was not written to.
* The pre-registration variants for the gate test were written to the session scratchpad, not the study folders.

## Addendum, 7 October 2026 (round 2): checkpoint 2's changes (R-A, R-B, R-C)

This round verified `final_test.py` as of 10:07 (code hash `239b91896b370a19…`, the value in `check.json`), with `tabpfn_tests.py` as of 09:34. Bug 1 was fixed inside `encompassing`, which skips absent tours. That is the alternative fix of §1: it changes a file hashed in `hypotheses/prepare.json`, so it needs its ledger row. The code hash now covers the file. **The same rules held: synthetic outcomes only, and no real result of any season was loaded.** The scripts are `verify_final/b14_synth.py` and `verify_final/gate_round2.py`, with `modes.check_mode` re-run.

**Verdict, round 2: sign off.** One small robustness fix is recommended (R2-1 below); it does not touch the primary.

### A. B₁₄ and the three gains (R-A)

**Design.** The DGP, β settings, seeds and draw order are those of §3, so replicate k is round 1's replicate k: 2,000 at β = 0 and 1,000 per other setting. gain* is each comparison's expected paired gain under the true probabilities (mLL, positive = the second-named arm better).

| Population gain | Comparison | Mean gain | Mean gain* | Bias (MC SE) | Interval covers gain* | Above 0 | Below 0 |
|---|---|---|---|---|---|---|---|
| 0 | **F vs B₁₄** | −0.010 | −0.011 | +0.001 (0.001) | **95.1%** | 1.3% | 3.8% |
| 0 | B₁₄ vs B | +0.018 | +0.017 | +0.001 (0.001) | 94.9% | 6.0% | 1.3% |
| 0 | F vs B | +0.008 | +0.006 | +0.002 (0.002) | 95.5% | 3.8% | 1.8% |
| 0.1 | **F vs B₁₄** | +0.092 | +0.090 | +0.002 (0.005) | 95.6% | 6.7% | 0.3% |
| 0.1 | B₁₄ vs B | +0.015 | +0.016 | −0.001 (0.002) | 96.1% | 4.8% | 0.9% |
| 0.2 | **F vs B₁₄** | +0.190 | +0.190 | +0.000 (0.007) | 94.7% | 14.2% | 0.2% |
| 0.2 | B₁₄ vs B | +0.017 | +0.016 | +0.001 (0.002) | 95.0% | 4.7% | 1.7% |
| 0.5 | **F vs B₁₄** | +0.482 | +0.489 | −0.007 (0.011) | 96.4% | 26.8% | 0 |
| 0.5 | B₁₄ vs B | +0.015 | +0.016 | −0.000 (0.002) | 95.3% | 4.8% | 1.7% |

* **F vs B₁₄ (the effect size read) at β = 0.**
  * It is about 0: −0.010 mLL, which is the price of fitting the nudge's b on noise.
  * It is unbiased: +0.001, MC SE 0.001.
  * Its interval covers gain* in 95.1% of replicates.
* **At β > 0 it recovers the planted gain.** Its gain* is 0.090, 0.190 and 0.489 against 0.1, 0.2 and 0.5. The shortfall of about 0.01 is the same estimation price, and the realized means agree within MC error.
* **B₁₄ vs B isolates the calibration window.** It is +0.015 to +0.018 at every β, so it carries none of B-INJ's gain. With constant true slopes, the 2014 window is the more precise one.
* **The three gains add exactly.** F vs B − (F vs B₁₄ + B₁₄ vs B) ≤ 5e-16 mLL in all 5,000 replicates, on identical rows (equal n in every one). Their intervals do not add, as expected.
* **Comparisons with round 1.** F vs B is round 1's effect size, and B₁₄'s 2025 slope is within 0.002 of the nudge's.

### B. The primary is unchanged

* **Same draws, same answer.** The 5,000 replicates of the round-1 seeds give the same b, lo and hi as round 1 to CSV round-trip precision: a relative error near 1e-16, absolutely ≤ 6e-14 at β = 0, where b is in units of a tiny deviation. F vs B equals round 1's effect size to ≤ 1e-16 mLL.
* **End to end.** The synthetic run gives the same result as round 1 on the same draw: b 0.311 [−1.033, +1.655], F vs B −0.019.
* **Code.** `primary()` and the `(lb, lf)` of `deployed()` are textually unchanged.
* **Bug 1 is fixed.** The per-tour primaries are now finite (atp −0.08, wta 0.66 on that draw, 20 df each). The pooled result is unaffected.
* **B₁₄'s fit.** `fit_slopes` is `fit_nudge` without x: same rows, same η and the same maximum likelihood. Both agree with an independent BFGS fit to 6 decimals.

### C. The gate (R-B, R-C): every input checked before any result is loaded

| Case (`population()` trapped) | Outcome |
|---|---|
| Positive control: the pre-registration with today's code hash filled in (scratch copy) | passes every file check; stops at `population()` |
| One file's hash changed: model frame; Stage 0 matches; x file; early frame | refused, naming the file; `population()` never reached |
| One code file changed (each of the 10 in `code_hash`, the two external ones included) | refused ("the final test's code differs") |
| One forecast file changed (`model` in both folders, `binj`) | refused ("the forecast files differ") |
| Real modified copies (one byte appended): x file, early frame; a copied source tree with `screen.py` changed | refused. The unchanged copied tree passes, so the copy is faithful |
| Each of the six file-hash lines removed | refused |
| After the gate: population minus one match / one NaN `a_won` | refused (population hash / "missing results") before any fit |
| End to end (synthetic) | `final_primary.json` is written first. It holds `preregistration_sha256` (equal to the text's own SHA-256), the primary, the three gains and the B₁₄ parameters. `final_results.json` follows, with every subset carrying the three gains |
| A failing `polymarket()` | recorded as `{"error": …}`; the run completes |

**State today.** The pre-registration's `FINAL_TEST_CODE_SHA256:` line is still the placeholder "(filled after the B₁₄ check)", so `--run` refuses until it is filled. Every other hash line matches today's files: model frame, Stage 0 matches, x file, early frame, forecasts and population.

**`--check`.**
* It is still result-free: the output is identical with `a_won` NaN or noise.
* That output equals the study's `check.json`, new hash fields included.
* `a_won` is dropped after `population()` loads it (memory only).

**R2-1 (recommended, minor): `tml_exposed()` runs outside the subsets' `try`.**
* The subset tuple is built before the loop, so an exception in `tml_exposed()` escapes `run()` after `final_primary.json` is written. It then loses `final_results.json`: every subset, Polymarket and the column arm (shown by a trapped failure).
* It reads only a hashed file and never failed here.
* Exact fix: in `run()`, replace `("TML-clean", ~tml_exposed(f["match_id"]))` with `("TML-clean", None)`, and replace the loop body's first line with:

```python
        try:
            g = f[~tml_exposed(f["match_id"]) if mask is None else mask].reset_index(drop=True)
```

* Then move the existing `sub.append(...)` into that `try`.

**Notes.**
* The module docstring's line 17 still reads "Effect size: F against B deployed" (`effect()`'s own docstring is right).
* `deployed()` computes B₁₄'s log-odds even when `b14=False`, so every `params` must hold `"b14"` (`parameters()` always provides it).
* `run()` hashes `preregistration.md` again at the end instead of hashing the bytes it read; the two differ only if the file changes during the run.
