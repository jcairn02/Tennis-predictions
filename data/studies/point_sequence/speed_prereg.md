# Item C: serve-speed change, residual screen — pre-registration

* **Who and when:** written 6 Oct 2026 by TESTER-3, for item C of the scoped audit (section 2, the coordinator's binding spec).
* **What existed before this file was hashed:** only the feature build (`speed_build.py`), its coverage counts and a leak probe.
  * No match result was read.
  * No β, log loss or recalibrated benchmark was computed.
* **Locking:** this file's SHA-256 is stored in `speed_prereg.sha256`, and `speed_screen.py` refuses to run if the hash differs.
  * Anything decided after estimation goes into `speed_results.json` under `deviations_after_estimation`. This file is never edited again.

## 1. Question

Does a recent change in a player's first-serve speed against his own norm predict the match result beyond the 54-input model? The market is a secondary benchmark.

The change is the mean over the last 2 weeks minus the mean over the last 52 weeks, of first serves in.

## 2. Feature (primary: x_raw)

* **Per player P before match m, own history in order.** P's earlier events count, plus earlier rounds of the same event. Other events of the same week never count.
  * This is safe by construction under the 5 Oct 2026 timing decision.
  * Leak probe: speeds at and after 8 random cuts were replaced by noise and the feature rebuilt for 4,000 targets. Nothing before or at a cut changed.
* **The two means:**
  * **m2** is the mean speed (km/h) of P's timed first serves in, over P's earlier matches whose best-estimate day (`timing.parquet` `obs`) is at most 14 days before m's;
  * **m52** is the same over at most 364 days.
  * **xP = m2 − m52**, missing when P has no timed first serve in the 2-week window.
* **Match feature:** x = xA − xB, missing when either side is missing.
* **Speeds.** `shot_level/stage1_match_stats.parquet` gives `spd1_n` and `spd1_d` per match side. These are aggregated from the shot-level point tables' `speed` column, one source per match, and a match counts only if at least half of its first serves in are timed.
  * Sources: Infosys (ATP tour and qualifying; 91 tour matches in 2021, dense from 2022), the AO/RG Hawk-Eye copy, SlamTracker, and Sackmann's Slam point-by-point.
  * Women: Slams only.
* **Scale:** x_std = x / s, with s fixed per tour before any result was read. s is the SD of x_raw over the tour's analysable matches in both windows: **men 5.998 km/h, women 4.942 km/h**.
* **Clipping:** x_std is clipped to [−4, +4]. This affects 12 men's matches and 0 women's (speed glitches).

## 3. Benchmarks and frame

* **Frame:** `meta_stack/walkforward.parquet` (main-tour main draws with closing odds), read with year ≤ 2024 only. The 2025–26 closed holdout is never loaded.
* **Model benchmark:** `p_base`, the 54-input model's walk-forward forecast, seeds averaged.
* **Market benchmark:** `p_mkt`, the de-vigged average close.
* **Recalibration:** both are recalibrated prequentially with `diag_edge_split.prequential`: one slope per tour on logit, no intercept, fitted on every earlier season.
  * 2014 has no earlier season, so analysis starts in 2015.
  * The men's 2018 season has no odds in the frame.

## 4. Subsets and observed coverage (feature only)

| subset | frame matches | x_raw present | by year |
|---|---|---|---|
| **Men, discovery** (primary): Slams 2015–2020, plus every level in 2021 | 4,868 | **860** | 2015: 126, 2016: 111, 2017: 125, 2019: 93, 2020: 117, 2021: 288 |
| **Men, replication** (primary): every level, 2022–2024 | 7,958 | **3,534** | 2022: 967, 2023: 1,138, 2024: 1,429 |
| Women, discovery (secondary, no gate): Slams 2015–2021 | 3,416 | 840 | |
| Women, replication (secondary, no gate): Slams 2022–2024 | 1,515 | 503 | |

* **Men's replication by level:** Slams 776 of 1,515 (51%); non-Slam 2,758 of 6,443 (43%).
* **Why coverage is low:** the 2-week window needs a timed match in the previous two weeks. Before 2021 that means an earlier round of the same Slam, so Slam first rounds are mostly missing.

## 5. Statistic and inference

* **Model:** logit P(A wins) = logit(benchmark) + β · x_std, with no intercept (side A is a random hash of the match id).
* **Direction:** **positive β = the player whose recent first-serve speed rose more against his own norm (or fell less) than his opponent's wins more often than the benchmark says.**
* **Fit:** Newton maximum likelihood with a Wald 95% interval from the observed information.
* **Check:** a four-week-block bootstrap (blocks of 28 days of tournament dates, 2,000 resamples), percentile interval.
* **Implied gain** (walk-forward, in mLL):
  * For each season s from 2016 to 2024, β_s is fitted with the same model and benchmark on every earlier season's analysable matches of the same tour, from 2015, using the subset rules of §4. A season is scored only if at least 300 earlier matches exist.
  * Gain per match = LL(benchmark) − LL(expit(logit benchmark + β_s · x_std)). Positive = the feature better.
  * It is reported per window as the mean over the scored analysable matches with a four-week-block interval (`tabpfn_thinking.common.compare`).
  * It is also reported diluted over all frame matches of the window's subset, counting a gain of 0 where the feature is missing.

## 6. Pass rule (binding: men, against the model)

**PASS** if both hold:

1. β (replication 2022–24) > 0 with its Wald 95% interval above 0;
2. β (discovery) > 0.

Otherwise **FAIL**.

* If the rule passes but the block-bootstrap replication interval spans 0, the result is "pass, fragile".
* The market benchmark and the women are reported and do not gate.
* If C passes, no further model or market test is run here. The main session decides the next step.

## 7. Secondaries (descriptive; none gates)

1. **The market benchmark** for every subset. Label: not blind for 2022–24. The shot-level study saw its own speed-change feature against the close in 2022–26: +0.14 [−0.00, +0.28] mLL, week-clustered.
2. **x_evt:** the same windows on event-family-centred speeds.
   * Each match's speeds have its family's offset from the tour mean removed. Families are AO, RG, W, USO, and "tour" (Infosys).
   * Offsets are frozen on matches to 2021. Men, in km/h: tour +5.34, W +3.13, AO +0.37, USO −1.21, RG −2.49.
   * Reason: the tracking systems read at different levels, so a Slam 2-week window against an Infosys-heavy 52-week window shows an artificial drop.
   * Scale: its own pooled SD (men 5.904, women 4.884); clipping as primary.
3. **x_shot, the shot-level study's own feature, reused as it is:** `stage2_features.parquet` `spd1_change|off|dec2-w52`, which is a two-week half-life minus 52 weeks, shrunk toward the tour mean, surface-centred and leak-probed.
   * Scale: its own pooled SD (men 6.247, women 8.832); clipping as primary.
4. **x_raw unclipped.**
5. **β per season** (descriptive) and the men's replication split into Slams and non-Slams.

## 8. Power (inferred, before reading any result)

* **Replication standard error.** SE(β) ≈ 1/√(n · p(1−p) · var x_std) ≈ 1/√(3,534 · 0.19 · 1.06) ≈ 0.038 per SD.
* **Minimum detectable effect** (80% power): β ≈ 0.11 per SD. That is an implied gain of about 1.1 mLL on the analysable matches, about 0.5 mLL diluted over the window.
* **Discovery standard error:** n = 860, so SE ≈ 0.076.
* **The lead's size is below what this test can see.** The shot-level lead (+0.14 mLL against the close, on about 95% of matches) corresponds to β ≈ 0.04 per SD, about a third of the minimum detectable effect.
  * So the screen cannot confirm an effect of the lead's size. A pass needs an effect about three times larger in β (about nine times in mLL).
  * A tie bounds the effect; it does not close the lead.

## 9. Choices fixed before estimation (deviations from the spec's wording)

* **D1. The shot-level feature is not reused as the primary.** The spec says to reuse `stage2_features.parquet`'s feature if it holds the 2-week-minus-52-week change. It holds `spd1_change|off|dec2-w52`, which is leak-safe but a different statistic. Its 2-week part is a half-life over all history, shrunk toward the tour mean (shrinkage constant K = 2.3 serves for men).
  * Without recent timed matches, it therefore turns into minus the player's speed level.
  * Observed, feature only: at men's Slam first rounds in 2015–20 it correlates 0.88 with the negative 52-week level (0.41 in later Slam rounds, 0.24 in 2022–24).
  * The primary is therefore the spec's literal windowed mean. The reused feature is secondary 3.
  * x_raw correlates 0.90 with x_shot where both exist, and 0.97 with x_evt.
* **D2. Clock.** The windows use the clock's best-estimate day `obs`. timing.parquet's `start` is the tournament start date.
* **D3. Analysis starts in 2015**, because the prequential recalibration needs an earlier season and the frame starts in 2014.
* **D4. Clipping at ±4 SD** (see §2).

## Files

* Code:
  * `src/eda/point_sequence/speed_build.py` (features, coverage, leak probe);
  * `src/eda/point_sequence/speed_screen.py` (this test; it checks the hash).
* Outputs in `data/studies/point_sequence/`:
  * `speed_features.parquet` and `speed_build_summary.json`;
  * `speed_results.json` and `speed_estimates.csv`.
