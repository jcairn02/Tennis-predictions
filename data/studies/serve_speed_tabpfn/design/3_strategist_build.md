# R3 build note: integration strategist (C5, C6, T-H1 to T-H7)

7 October 2026 · agent 3. Built to `2_audit.md` and `lead_notes.md`. No GPU fit was run, and `score.py --run` was never run. No speed feature was related to any result.

## What was built

| File | Content (audit section) |
|---|---|
| `src/eda/serve_speed_tabpfn/common.py` | `Paths` (every path overridable for tests), the seeds and configuration, logged fit times, `code_hash`, `race_names` |
| `arms.py` | The registry (`features/registry.json`, written: `spd_f`, `spd_raw`, `spd_f_all`, kind diff, family `speed`), the arms `spd`, `spd_raw`, `spd_all` and `*_noodds`, `load_frame` (one-to-one join; the never-NaN columns asserted; `a_won` only with `labels=True`), `flip`, `job_data`, `feature_status` (probe records), `base_columns_unchanged` (C5) |
| `local_fits.py` | The 223-job plan, `--plan`, `--fingerprint-check`, `--repro-check` and the GPU `--run` (C5) |
| `forecasts.py` | The fit loader. Base arms search this study's folder, then feature interactions', then the race's. Columns, training shape and ids are checked. Race fits are refused until both reuse checks pass (C6) |
| `score.py` | `--check`, `--synthetic` and `--run`. P2, S0–S14, the decision table and the multiplicity count (C6) |
| `test/serve_speed_tabpfn/test_ssp_harness.py` | 23 tests on a stand-in world in a temp folder: T-H1 to T-H7, plus checks of the interval convention, the decision table, recovery of a planted β, S13/S14 signs, and the refusals. **23 pass in 7 s** |
| `docs/studies/serve_speed_tabpfn/preregistration.md` | **Draft.** Hash lines and counts are marked **[lead]** |

**The runner's refusals:**
* a job outside the plan;
* `model` with the odds, except the 2 reproduction jobs;
* a `model_noodds` seed the race already holds;
* a feature file whose `speed_meta.json` lacks passing Probe A/B records, records another hash, says it read results, or has `standin_panel` true.

Every fit's metadata stores:
* the feature file's SHA-256 and registry entries;
* the model frame's SHA-256;
* the training seasons (2013..Y−1);
* the fingerprint.

**Added at the coordinator's request:**
* **S13:** the base against the recalibrated close, with P2 / S13 as a point value.
* **S14:** P2 on the Brier score.
* **The stale-fit guard:** a speed-arm fit whose stored `feature_sha256` is not the current file's is refused by the loader, listed by `--check`, and stops `--run`.

## Checks run (CPU, permitted)

* **`--plan`:** 223 jobs, 2.08 h at the logged speeds (3.13 h at 1.5×). Written to `data/studies/serve_speed_tabpfn/fit_plan.csv`.
  * A1: 68; A2, A3 and the no-odds twin: 44 each; new `model_noodds` seeds: 20; reproductions: 3.
  * A test pins that the scorer reads exactly these fits, plus the reused base seeds.
* **`--fingerprint-check`** (`checks/fingerprint_check.json`):
  * **107 of 107** feature-interactions `model` fingerprints for 2019–2026 equal this harness's `job_data`.
  * The race's 48 fits (`model` and `model_noodds`, seeds 0–2) match on columns, training shapes, query rows and ids.
* **Finding: the race names the 21 surface-profile inputs `sf_<name>`.**
  * This is its own convention (`surface_rating_race/arms.py`, "in the model they keep their names"); `model_frame.py` drops the prefix.
  * Without normalising it, every race fit fails the column check. `common.race_names` normalises it for race files only.
  * The values are the same: the frame build checks this, and feature interactions' 2019 duplicates are bit-identical. The reproduction fits will confirm it.

## Notes for the lead

1. **The feature file now at `features/speed.parquet` is a stand-in build** (`standin_panel: true`). `local_fits.py --run`, `score.py --run` and `feature_status` refuse it by design. Rebuild it on the R3 panel before fitting.
2. **The interfaces match the modeller's current file:**
   * `probes` A/B with `pass`;
   * `probes_pass`;
   * `features_parquet_sha256`;
   * the diagnostics `k28_a/b`, `last_age_a/b` and `id_conflict`.
3. **Synthetic sanity on a stand-in world (not real data).**
   * Null, 200 replicates: P2 rejects positively in 0.5% (block-only 3%); its interval covers the exact expected gain 98% of the time; S0 rejects 2%, two-sided.
   * Planted β 0.15: S0 recovers 0.148; P2 averages 1.58 mLL against an expected 1.62; the capture is 0.083, as constructed.
   * The verifier's runs on the real forecasts are what count.
4. **The run order** is in the pre-registration, §11:
   * fingerprint check;
   * 3 reproduction fits, then `--repro-check`;
   * 220 fits;
   * `--check`, fill §3, hash;
   * `--run` once.
   * `--run` checks six recorded hashes and the file's own SHA-256 (`preregistration.sha256`).

## Choices where the spec left room (stated in the pre-registration)

* **223 jobs**, not C5's 222: the coordinator added the `model_noodds` 2025 seed 1 reproduction.
* **Calibration fits leave debut seasons out**, and fewer than 1,000 rows per tour raises an error.
* **S3:** a side is recent if `k28` > 0, falling back to `last_age` ≤ 28.
* **S6's move:** M is regressed on [η_B,early − logit p(24 h), η_A1,early − η_B,early], four-week clusters; the second slope is read. The race's no-odds version is reported beside it.
* **S9** is compared with the calibrated base on a block-only interval (the same base forecasts, so no seed term).
* **S11's week interval** includes the seed term.

## Disagreement recorded (no ruling changed)

The empirical seed term double-counts independent seed noise that the block SE already holds (my R1 S3). In simulation, P2's null rejection is 0.15–0.5% against 2.5%. I accept the convention for comparability. S11 reports the block-only interval beside it.

## Looks (for the ledger)

| # | Seasons | What | Why |
|---|---|---|---|
| R3-1 | 2013–2025 labels; 2019–2026 forecasts | `--fingerprint-check`. Training labels are **hashed** into the fingerprints with X_train and X_query, and compared with the stored metadata. Nothing is related to anything | Reuse of the base fits (permitted by the lead) |
| R3-2 | 2024–2026 | Counts only (no `a_won`): men 7,068, women 6,586 and 33 blocks; men with a 24-hour price 1,442, of which 582 are clean openers; the last tournament date, 28 Jul 2026 | Pre-registration counts |
| R3-3 | – | `speed_meta.json` and the feature file's schema (metadata) | Interface |
| R3-4 | – | Synthetic outcomes on stand-in worlds (pytest temp; the scratchpad) | Harness tests, sanity |

## Correction, 7 October 2026 (after R4, red team F1–F2)

* **F2: note 1 above is stale.** The feature file now on disk is the **R3 build, not a stand-in**:
  * `standin_panel` false;
  * `features_parquet_sha256` `fcd8d241…`;
  * panel `f774eb50…`;
  * s_f 2.2240.
  
  `feature_status` is ok for it.
* **F1: fixed.** `arms.feature_status`, and so the runner and `--run`, now refuses a `speed_meta.json` that records:
  * no feature-file hash;
  * no `panel_sha256` or `features_py_sha256`;
  * either of those differing from the current `speed_panel.parquet` and `features.py`.

  The tests cover each case, and a panel or builder changed on disk after the meta. 23 tests pass.

## Addendum, 7 October 2026 (after the verifier, `4_verifier.md`)

**Code changes, each with tests** (29 harness tests; 49 in the study folder; all pass):
* **V1:** S6(b)'s odds move is regressed on [η_B^{0–7} − logit p24, η_B^{0–7}, η_A1^{0–15} − η_B^{8–15}], and the last slope is read. The no-odds version is unchanged.
* **V2:** `--run` refuses any missing needed fit before `labels()`.
* **V5:** `synthetic(arms="real")` runs only after the hash.
* **V6:** coefficients are labelled per unit of the column.
* **V7:** `--run` checks a recorded `FORECASTS_SHA256`.
* **V8:** the pre-registration hash is computed with CRLF normalised to LF; `--hash-prereg` writes it.
* **V9:** S10 also reports a_cal = Σ s_Y·dev·z / Σ z² and a_cal / b_S0.
* **V13:** `eta` refuses NaN.
* **S13** is context and is not counted in the multiplicity.
* **Errors in S6, S9 and S12:** a linear-algebra error now marks that secondary unavailable instead of crashing.

**Pre-registration text:** V3, V4, V6, V10, V11, V12 (left as [lead] placeholders), V14, §5 and §11 were updated as the lead decided.
