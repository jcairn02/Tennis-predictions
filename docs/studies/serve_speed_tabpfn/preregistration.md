# Serve-speed state in the best TabPFN model: pre-registration

**Drafted** by the integration strategist (R3) and amended after the red team ([4_redteam.md](../../../data/studies/serve_speed_tabpfn/design/4_redteam.md)) and the verifier ([4_verifier.md](../../../data/studies/serve_speed_tabpfn/design/4_verifier.md)). **Completed and frozen** by the lead on 7 October 2026. Its sources are the auditor's rulings ([2_audit.md](../../../data/studies/serve_speed_tabpfn/design/2_audit.md), C5–C7) and the [lead's notes](../../../data/studies/serve_speed_tabpfn/design/lead_notes.md).

**How it becomes binding.**
* The lead completes the items marked **[lead]** and fills the hash lines in §3 from `score.py --check`.
* The lead then runs `./python.sh src/eda/serve_speed_tabpfn/score.py --hash-prereg`. It writes this file's SHA-256, computed with CRLF normalised to LF, into `preregistration.sha256`. The lead also records the hash in the [look ledger](look_ledger.md).
* From then on nothing here changes, and `score.py --run` runs once. It refuses to run if this file, the code or any frozen input differs from what is recorded.

**Sign conventions.**
* Gains are in milli-log-loss (mLL). **Positive = the named arm has the lower log loss (better).**
* Coefficients are in **log-odds per unit of the column**:
  * for `spd_f`, one unit is one s_f = 2.224 km/h of the fast speed-state difference;
  * for `spd_raw`, one unit is 5.998 km/h of the registered x_raw, the published β's unit.
* A 95% interval that spans 0 is a **tie**.

## 1. The question and the estimands

**The owner's request** (7 Oct 2026): integrate the men's serve-speed change into the best local non-thinking TabPFN-3.5, "then perform a test to see if it improves prediction scores in 2024–2026 and by how much (expanding window tests)."

**Primary estimand.** The change in men's log loss when the speed-state column `spd_f` is added to the current best model, scored on 2024, 2025 and 2026. The current best is the 58-input model with the closing odds.

**The expanding window, explicitly.** For each test season Y in 2024, 2025 and 2026:
* every arm is fitted on the model frame's matches of **2013 to Y − 1** and predicts season Y;
* its calibration slope for Y is fitted on its own out-of-sample forecasts of 2019 to Y − 1;
* the nudge's coefficient for Y (S9) is fitted on 2019 to Y − 1.

Nothing from season Y or later enters any forecast of Y. Seasons 2019–2023 are fitted the same way only to calibrate.

## 2. What existed when this was hashed

* **The design:**
  * the brief and the team;
  * three independent R1 proposals;
  * the auditor's rulings, which stand in full (lead notes): as-of centring, ks-first basis, f̂ as the statistic, 0 rather than NaN, women 0 in A1, P2 alone primary, A3 = women.
* **The builds:**
  * the speed panel (C1–C2);
  * the speed features (C3), in `data/studies/serve_speed_tabpfn/features/speed.parquet`, with `speed_meta.json` recording Probe A (own history) and Probe B (clock) as passed;
  * the harness (C5–C6, `src/eda/serve_speed_tabpfn/`).
  * **Confirmed by the lead:** the feature file at the freeze is the R3 build on the R3 panel, not the stand-in. `speed_meta.json` records:
    * `standin_panel` false;
    * `probes_pass` true;
    * `features_parquet_sha256` `fcd8d241…`;
    * panel `f774eb50…`;
    * s_f = 2.2240 km/h.
  * **Accepted build deviations** (red team F4, with their measured effects in `design/4_redteam.md` §1):
    * the engineer's `mislink_level` rule;
    * the round check before the duplicate check;
    * `obs` floored to whole days;
    * the modeller's round-robin ordering by `obs`.
* **The tests:**
  * T-P1 to T-P8;
  * T-F1 to T-F6;
  * T-H1 to T-H7 (`test/serve_speed_tabpfn/test_ssp_harness.py`).
  * **All 49 tests in `test/serve_speed_tabpfn/` pass** (lead, 7 Oct, about 15:05).
* **R4:**
  * **The auditor's red team** (`design/4_redteam.md`):
    * an independent rebuild that imports neither `panel.py` nor `features.py`;
    * `spd_f` equals the build on all 63,737 frame matches: corr 1.000000, 100% within 0.05 s_f, largest difference 2.2e-14. `spd_f_all` and `spd_raw` are equal too;
    * its own Probe A (30 order cuts) and Probe B (30 cut days) moved nothing before a cut, and both leaky controls fired at every cut;
    * verdict: sign off, with fixes F1–F2 made.
  * **The verifier** (`design/4_verifier.md`, including its 15:00 re-verification), on synthetic outcomes only:
    * P2 is unbiased for the exact expected gain, and its interval covers it in 94–96% of replicates;
    * it rejects a true null in 0.35–0.75%;
    * S0 is unbiased and covers β in 95–97%;
    * all 33 endpoint rows read with their registered signs;
    * calibration and the nudge read seasons < Y only;
    * `--run`'s refusals all fire before any label is read;
    * verdict: sign off, with fixes V1–V14 made.
* **Reuse checks of the base fits:**
  * `checks/fingerprint_check.json` (observed 7 Oct): all 107 feature-interactions fingerprints of `model` for 2019–2026 equal this harness's. The rating race's 48 `model` and `model_noodds` fits match on columns, training shapes, query rows and ids.
    * The race names the 21 surface-profile inputs `sf_<name>`; that renaming is documented in `common.race_names`.
  * `checks/repro_check.json`: **passed.** The three reproduction fits equal the race's stored forecasts with a **maximum difference of 0.0** in every block (`td`; `early` and `late` for 2026).
* **Fits.** All 223 fits exist at the freeze, and `FORECASTS_SHA256` in §3 pins them: `--run` recomputes it and refuses on any difference. No forecast of any speed arm has been scored, and none has been related to `spd_f`.
* **Looks.** No speed feature was related to any match result, in any season, before this hash: look ledger rows 1–31. The GPU fits trained on the results of 2013..Y−1, as the expanding window requires, and nothing was scored.
* **Not blind:**
  * 2024 was in the published 2022–24 replication of x_raw;
  * 2025–26 was opened for the old, sparse speed coverage via `x_shot` against the close;
  * the base's 2025–26 forecasts were scored by the feature-interactions final test.

## 3. Frozen inputs

Fill each line from `score.py --check` (`check.json` → `hashes`, `forecasts`). Leave nothing on these lines but the 64-character hex.
* `--run` verifies the first six lines against the current files and code.
* If the `FORECASTS_SHA256` line holds a hex, `--run` also recomputes it from the fit files and refuses on any difference.

Expected values seen on 7 Oct, for orientation only:
* the model frame `6113966f…ab06b`;
* the early-price frame `22809fa7…9a5c`.
  * Both equal the feature-interactions freeze.
* the R3 feature file `fcd8d241…`, with panel `f774eb50…` and s_f 2.2240 (red team, 4_redteam.md).

```
SCORER_CODE_SHA256: 6bcfc06c2aff73b2bf40fd4bac17050629fc019c84a9af94fb38f39300c04ba8
MODEL_FRAME_SHA256: 6113966fd8286cb41738eb7b52e0d6d9e2d7631c980c3aec7be6e4bbbaaab06b
FEATURE_SHA256: fcd8d24124e0d9987bd42c0557af27770dbd0c7fa314ddaa1ae7927f1328e0e3
REGISTRY_SHA256: 217100ecf7ab2799b0ccb924c8d459cf9aa1161350e6a80ab6ba963ce4bab389
EARLY_SHA256: 22809fa7a9422a22f28953292cca0d5db894470f3218bc23d45d3cdce9729a5c
POPULATION_SHA256: e4ab0787b531526708fa7d97ffdd97a2878b02a1b113eda62c26b59d5296ef27
FEATURES_PY_SHA256: fc3c0cf58ce66521fff6a24feee79b4fa0cc759cb8040a6be1ba33644c0dabc5
PANEL_SHA256: f774eb50a0874469cb5a30101549b576c03c48a073de32d7966d5eadcdcaff39
FORECASTS_SHA256: 198015082c60d4344960cc0cdc782ce3db71edd2c85747884c6fd25c3cac6e56
```

* The scorer's code hash covers `common.py`, `arms.py`, `forecasts.py`, `score.py`, `local_fits.py` and `src/eda/tabpfn_thinking/common.py`.
* `POPULATION_SHA256` is the SHA-256 of the sorted match ids of the primary population (§6).

## 4. Arms and seeds (223 jobs)

All arms are local TabPFN-3.5 with 8 estimators, softmax temperature 0.9 and pretraining limits ignored (feature interactions' runner).
* Each fit predicts the season's matches as stored and flipped.
* Arms with the odds also predict, in 2025–26, with `odds_logit` replaced by Polymarket's price 24 hours (`early`) and 30 minutes (`late`) before the listed start.

| Arm | Inputs | 2019–23 seeds | 2024–26 seeds | Fits |
|---|---|---|---|---|
| `spd` (A1) | 58 + `spd_f` | 0–3 | 0–15 | 68 |
| `spd_raw` (A2) | 58 + `spd_raw` | 0–3 | 0–7 | 44 |
| `spd_all` (A3) | 58 + `spd_f_all` | 0–3 | 0–7 | 44 |
| `spd_noodds` | 57 + `spd_f` | 0–3 | 0–7 | 44 |
| `model_noodds`, new seeds | 57 | 3 | 3–7 | 20 |
| Reproductions | `model` 2024 seed 0; `model` 2026 seed 2; `model_noodds` 2025 seed 1 | | | 3 |
| **Total** | | | | **223** (about 2.1 h logged; 3.1 h at 1.5×) |

**The columns** (registry `features/registry.json`; all of kind diff, A − B, negated when A and B swap):
* `spd_f` = clip((f̂_A − f̂_B)/s_f, −4, 4): the posterior fast first-serve-speed state. It is 0 for every woman and never NaN.
* `spd_f_all`: the same, with women's Slam values. Never NaN.
* `spd_raw`: the registered x_raw on the new panel / 5.998, clipped. NaN unless both men were timed within 14 days.

**The as-of offsets' fallback.** In C2, an edition with no in-window family editions falls back to "else 0". That 0 means **the snapshot's reference level**, the tour main draws. The red team measured that this fallback moves one men's match, by at most 0.05 s_f.

**Reused base fits (read-only):**
* `model` seeds 0–2 (the race) and 3–15 (feature interactions);
* `model_noodds` seeds 0–2 (the race).

## 5. Forecasts and calibration

* **Forecasts.** Each is symmetrised: the mean of P(A | x) and 1 − P(A | x swapped). They are averaged over the stated seeds, and η is the logit of the seed mean.
* **Calibration (decided).** One slope per tour on η, with no intercept.
  * It is fitted for season Y on the arm's own seasons 2019 to Y − 1 (debut seasons out), from the **seeds 0–3 mean**.
  * It is applied to the season-Y seed mean.
  * The same holds for every arm, the base included.
  * A calibration fit needs at least 1,000 rows per tour (else an error).
* **Seed sets.** Every comparison uses one seed set on both sides: 0–15 for A1 against the base, 0–7 for everything else. `score.py` asserts it.

## 6. Population and subsets

* **Primary:** men's model-frame matches, 2024–2026, debut seasons out.
  * **7,068** matches: 2,674 in 2024, 2,620 in 2025 and 1,774 in 2026.
  * 2026 ends with events that started by 28 July 2026, so it runs to early August.
  * 33 four-week blocks.
* **Women:** 6,586 matches (2,460, 2,485 and 1,641). **Both tours:** 13,654.
* **Recency (S3):** men with both / one / neither side holding a timed row within 28 days, from the feature file's `k28_a` and `k28_b`: **5,420 / 1,130 / 518** (verifier, counts only).
* **Polymarket (S6):** men 2025–26 with a 24-hour price: **1,442** (232 + 1,210). Of these, **582** are clean event openers (117 + 465).
* **`id_conflict`:** women's matches whose players differ between Stage 0 versions.
  * **21** are in the scored population, all in 2026 and all flipped sides.
  * 67 of the frame's 88 are debut-season matches, which are not scored.
* **`POPULATION_SHA256`** is filled at the freeze from `--check` (§3).

## 7. The primary endpoint, P2, and the decision table

**P2** = 1000 · mean over the primary population of [LL(q_base) − LL(q_A1)], with base and A1 seeds 0–15, both calibrated as in §5. **Positive = A1 is better.**

**Its interval:**
* SE² = SE²_block + v_A1 + v_base.
  * **SE_block** is the four-week-block cluster SE (the `tabpfn_thinking.common.paired_interval` formula).
  * **v_arm** is the variance over seeds k of the mean log loss of seed k's forecast, divided by K. This is the surface-IOS `seed_var` formula, with the arm's seed-mean calibration slope.
* The interval is G ± t(0.975, G − 1)·SE, two-sided 95%, with 33 blocks.
* **The registered interval is conservative near 0.** It rejects a true null in 0.35–0.75% of the verifier's worlds, against a nominal 5%. S11's block-only interval is reported beside it.

**Decision table:**

| P2 (men 2024–26) | S0 | Reading |
|---|---|---|
| lo > 0 | any | "Adding the speed state improves the men's log loss by G [lo, hi] mLL" |
| hi < 0 | any | Harm: "it worsens by \|G\|"; do not deploy |
| tie | lo_b > 0 | "S0 detects information beyond the base; P2 ties. P2 has less power than S0 at small effects and loses power as capture rises, so the tie does not show the column fails; S10 (capture) and S9 (nudge) say whether it delivers" |
| tie | tie | "No detectable speed information beyond the model in 2024–26"; S0 bounds β and P2 bounds the gain |
| tie | hi_b < 0 | A reversal of the published direction, reported as such |

## 8. Secondaries (descriptive)

Each row is reported with its interval and its direction. Paired gains use P2's interval convention unless stated.

| # | What | Direction (positive = …) |
|---|---|---|
| S0 | The information test. Regression: logit P = Σ_season a_s·η_B + c·η_B³ + b·`spd_f`, men 2024–26, η_B the base's raw 16-seed log-odds. b in log-odds per unit of `spd_f` (one s_f = 2.224 km/h); union-clustered variance (blocks, shared players; the largest of three), t on G − 1 | the man whose speed state is higher wins more often than the base says |
| S1 | P2 by season | A1 better |
| S2 | P2 on 2025–26 (blind for the new coverage) | A1 better |
| S3 | P2 by recency (both / one / neither within 28 days); "neither" is a harm check, expected about 0 | A1 better |
| S4 | A1 against the base on women and on both tours (seeds 0–15); A3 against the base on women, with and without the `id_conflict` matches (seeds 0–7) | the arm better |
| S5 | `spd_noodds` against `model_noodds` (seeds 0–7), men 2024–26, each calibrated on its own 2019..Y−1 | the no-odds A1 better |
| S6 | Two parts, on the early-price populations (all; clean openers): | |
| | (a) A1 against the base, both fed the 24-hour price and calibrated with their close slopes | A1 better |
| | (b) The 24 h → 30 min price move, M = logit p(30 min) − logit p(24 h), regressed without intercept, four-week clusters. Both versions are reported: | the price moved toward A1's view |
| | • **With the odds** (verifier V1): M on [η_B^{0–7},early − logit p(24 h), η_B^{0–7},early, η_A1^{0–15},early − η_B^{8–15},early]; the **last** slope is read. The base's seeds are disjoint between the controls and the deviation, and η_B is a control. The first version, without these, rejected a true null in 24–43% of the verifier's replicates; this one in 5.8–7.2% | |
| | • **Without the odds:** M on [η_Bno, η_Ano − η_Bno] (seeds 0–7, the race's convention); the second slope is read | |
| S7 | P2 on raw (uncalibrated) forecasts | A1 better |
| S8 | A2 against the base; A3 against the base; A1 against A2; A3 against A1 on men (dilution); all seeds 0–7 | the first-named arm better (A2 / A3 / A1 / A3) |
| S9 | The walk-forward nudge: logit q = s_tour·η_B + b̃_Y·`spd_f`. b̂_Y is maximum likelihood on 2019..Y−1 (η_B the seeds 0–3 mean), applied to the 16-seed η_B. Two versions: shrunk (b̃ = b̂·τ²/(τ² + SE²), τ = 0.05) and unshrunk. Each is compared with the calibrated base, block interval | the nudge better |
| S10 | Capture: a = Σ dev·z / Σ z², dev = η_A1 − η_base (raw 16-seed means), z = `spd_f`, men 2024–26, in log-odds per unit of `spd_f`. Also, because S0's b is on the calibrated scale (verifier V9): a_cal = Σ s_Y·dev·z / Σ z², where each season's deviation is multiplied by s_Y, A1's men's calibration slope for that season (pooled over the three seasons by z² weights; each s_Y reported). When S0's interval excludes 0, both a / b_S0 and a_cal / b_S0 are reported | a > 0: TabPFN moved toward the higher speed state |
| S11 | P2 with a block-only interval and with a calendar-week interval | A1 better |
| S12 | The registered statistic's replication: S0 with z = `spd_raw` (NaN → 0), men 2025–26. b in log-odds per unit of `spd_raw` (5.998 km/h of x_raw, the published β's unit) | the man whose registered speed change is higher wins more often |
| S13 | **Context, not a test of the speed column; not counted in §9.** "By how much", on P2's population. The calibrated base (seeds 0–15) against the closing price `p_mkt`, recalibrated the decided way: one slope per tour on logit p_mkt, no intercept, fitted for Y on 2019..Y−1, debut seasons out. mLL, block-only interval (the price has no seeds). Also **P2 / S13**, the speed gain as a share of the base's edge over the close: a descriptive point value, with no interval | the calibrated base has the lower log loss (better) than the calibrated close |
| S14 | P2 on the Brier score: 1000 × mean[Brier_base − Brier_A1], men 2024–26, seeds 0–15, calibrated. P2's interval convention: block SE plus the empirical seed variance on Brier | A1 has the lower Brier score (better) |

## 9. Multiplicity

* There is one confirmatory test, P2.
* The report gives the count of the S0–S14 intervals that exclude 0 (`results.json` → `multiplicity`).
  * **Not counted:** S13, which is context (the base against the close), not a test of the speed column; S10 (the capture) and the P2 / S13 ratio, which are point values.
* **The null reference for the count** is the verifier's null re-run after V1 (600 null replicates, `design/4_verifier.md`, re-verification), not 5% × K.
  * There are **K = 30** counted intervals.
  * Under the null the count's mean is **0.62**, and **P(count ≥ 3) = 5.0%**, P(≥ 4) = 1.7%, P(≥ 5) = 0.7%.
  * The count is overdispersed, not binomial at 5%.
  * **Reading rule:** 3 or more counted intervals excluding 0 is unusual under the null (about the 5% level). Fewer is what chance alone gives.
* No secondary can turn a P2 tie into a claim of improvement.

## 10. Expected effect, power and detectable effects

All of this is inferred, from simulations on synthetic outcomes. Two tables use two different units.

**Power per unit of `spd_f`** (the verifier's table 3; the real base forecasts and the real `spd_f`, which is non-zero on 7,066 of 7,068 men's matches):

| | β 0.05 | β 0.09 | β 0.15 |
|---|---|---|---|
| P2, capture 0.5 | 31–33% | 74–76% | 99% |
| P2, capture 1.0 | 16–21% | 43–46% | 84–87% |
| S0 | 43–46% | 93% | 100% |

* P2 is unbiased for the exact expected gain, and its interval covers it in 94–96% of replicates.
* P2's power falls as capture rises (V4).

**Power per SD of x_raw** (the strategist's earlier simulation of an x_raw-like column with partial coverage, `design/strategist_power*.py`):
* **The planning effect.**
  * Pooling the published discovery and replication gives β 0.077 ± 0.035 per SD of x_raw.
  * A sceptical prior for selection shrinks it to about 0.05.
  * The replication's own estimate is 0.09.
  * f̂'s β per unit of `spd_f` is unknown: no result was read. The audit's statistic-target gate shows f̂ carries at least the window's information.
* **Power at β 0.05 / 0.077 / 0.09 per SD of x_raw:**
  * P2: 11–15% / 34–36% / 45–51% (capture 0.25–0.5);
  * S0: 29–31% / 58–60% / 73%.
  * These used an analytic seed term, which is conservative (audit S3).
* **80% detectable effects, per SD of x_raw:** S0 at β ≈ 0.10; P2 at β ≈ 0.13, a gain of about 0.5–0.8 mLL.

The two tables differ in the column's unit and coverage, so they do not contradict each other. **A tie in P2 remains a likely reading at small effects** even if the effect is real.
* **Process suspects for a null:**
  1. capture;
  2. the key-statistic error tail;
  3. measuring breaks, only partly removed (AO 2024 under as-of);
  4. 2025 coverage (about 50% of men's matches have both sides within 14 days);
  5. seed count.

## 11. Run order

1. The panel, feature and harness tests pass. The auditor's R4 rebuild and probes agree. The verifier's synthetic runs pass.
2. `./python.sh src/eda/serve_speed_tabpfn/local_fits.py --fingerprint-check` (CPU) gives `all_ok`.
3. The lead, on the GPU: `./python_tabpfn_local.sh src/eda/serve_speed_tabpfn/local_fits.py --run --jobs repro` (3 fits), then `./python.sh src/eda/serve_speed_tabpfn/local_fits.py --repro-check` gives passed.
4. The lead, on the GPU: `local_fits.py --run --jobs all` (the remaining 220 fits). The runner refuses a feature file without passing probe records, or one built on a stand-in panel.
5. `./python.sh src/eda/serve_speed_tabpfn/score.py --check`: result-free. Fill §3 and §6.
   * Then `./python.sh src/eda/serve_speed_tabpfn/score.py --hash-prereg` writes `preregistration.sha256`. The hash is computed with CRLF normalised to LF, so a checkout under `core.autocrlf` still verifies.
   * Record the hash in the look ledger.
6. `./python.sh src/eda/serve_speed_tabpfn/score.py --run`, **once**. It writes `data/studies/serve_speed_tabpfn/results.json` and `results.csv`, and refuses to overwrite them.
   * **Before reading any result**, it refuses if:
     * the pre-registration's hash or any recorded hash differs;
     * the feature file fails its checks;
     * a reuse check has not passed;
     * any speed-arm fit (`spd`, `spd_raw`, `spd_all`, `spd_noodds`) stores a `feature_sha256` other than the current feature file's, which must itself equal `FEATURE_SHA256`;
     * **any fit in `needed_fits()` is missing**;
     * `FORECASTS_SHA256` is recorded and the fits differ from it.
   * `--check` lists the stale and the missing fits beforehand. If the features are rebuilt after fits start, the stale fits must be refitted.
   * `score.py --synthetic --arms real` relates the real A1 forecasts to `spd_f`, so it also runs only after the hash.
7. The auditor checks the report against the outputs.

## 12. Deviations

* After the hash, the code and the inputs are fixed; `--run` refuses any difference.
* A change the lead decides is necessary needs a new version of this file and a new hash.
* The reason goes in the look ledger and the report, labelled as a deviation with the time it was made relative to any result. A deviation after reading `results.json` is reported as post hoc.
