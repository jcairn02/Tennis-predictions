# R4 red team: the speed build against the spec (agent 4, auditor)

7 October 2026. This round audits the R3 build against `2_audit.md` C1–C4 and C7:
* `panel.py` → `speed_panel.parquet`, `frame_keys.parquet`;
* `features.py` → `features/speed.parquet` (SHA-256 `fcd8d241…`), with s_f = 2.2240;
* the harness's feature guards.

**Labels.** All numbers are **observed**. Scripts are in `src/eda/serve_speed_tabpfn/design/auditor_r4_*.py`; outputs `auditor_r4_*.json` / `.log` are in this folder.

**Rules followed.**
* No match result, no statistic target, no box score and no price was read; feature and speed values only.
* No GPU.
* No builder's file was edited. Refusal tests ran on copies in my scratchpad.

## Verdict: **sign off with fixes; the fits may proceed.**

* **The build reproduces exactly.** My independent rebuild reproduces all three columns on all 63,737 frame matches, to 2e-14 s_f. Every gap to my earlier library traces to a documented spec reading, not a bug.
* **Both of my probes pass.** I ran them on the built code, with my own cuts and perturbations and two leaky controls per cut; both controls fired at every cut.
* **The code matches C1–C4,** and the 43 builder tests pass.
* **Two small fixes are due before the freeze** (F1, F2); neither touches the feature values. Two items should be written into the pre-registration (F3, and F4's deviations).

## 1. Independent rebuild (`auditor_r4_rebuild.py`)

**Independence.** Nothing imports `panel.py` or `features.py`. I wrote my own:
* C1 choice rule and drops;
* families (C1: Slam / tour / ch / other × M/Q);
* as-of snapshots (C2) and frame join (C4, through `id_map` to the rebuilt timing);
* histories and the registered x_raw.

The inputs and the filter come from earlier rounds:
* **Records:** the R1 extraction (`engineer_records.parquet`).
* **Filter:** `auditor_lib.kalman_batch`.
* **Extraction cross-check:** the R3 panel's 19,077 chosen point means equal the shot-level study's own `stage1_match_stats` exactly, values and counts alike.

**Agreement** (A − B in units of s_f = 2.2240). The criterion is corr ≥ 0.995 and ≥ 99% within 0.05:

| Column, rows | Matches | corr | Within 0.05 s_f | Max \|difference\| |
|---|---:|---:|---:|---:|
| `spd_f`, all frame matches | 63,737 | 1.000000 | **100%** | 2.2e-14 |
| `spd_f`, men | 31,683 | 1.000000 | **100%** | 2.2e-14 (every season 2014–26) |
| `spd_f_all`, women | 32,054 | 1.000000 | 100% | 1.2e-14 |
| `spd_raw` (both present) | 7,435 | 1.000000 | 100% | 0.0 |

* Presence of `spd_raw` agrees on every match.
* My s_f is 2.223995373606193, identical to the build's.

**Where the earlier shortfall came from.** The modeller measured 98.1% for men, fully independent. Each of my readings is switched alone below:

| Variant (one switch from the spec reading) | Men within 0.05 | Max \|diff\| (s_f) | Whose reading | Kind |
|---|---:|---:|---|---|
| R2 library's families (Challengers inside `tour`) | 98.25% (modeller's run iii) | — | mine (R2) | Superseded by the C1 families (E7) |
| Round check per (match, side) key, not per record | 99.84% (52 matches out) | 1.66 | mine: the R1 records hold no round label | **The build is right.** C1 drops a *row* whose round disagrees; dropping the whole key voids the match's own correct record |
| Duplicate check before the round check | 99.84% | 1.66 | spec silent | **The build is right** (engineer's deviation 3), for the same reason |
| No `mislink_level` rule | 99.88% | 0.29 | engineer's addition (deviation 2) | Accept: a Slam feed on a non-Slam match is a mislink |
| γ not re-referenced before the "else 0" fallback | 99.997% (1 match) | 0.050 | spec ambiguity (mine, C2) | The build's convention (0 = the snapshot's reference level) is adopted (F3) |
| `obs` not floored | 100% | 0.006 (women's `spd_f_all` 0.09) | engineer's deviation 4 | Negligible |

* With all of the engineer's documented choices, the two builds are identical.
* None of the gaps is a bug in the build. The two that mattered (key-level round check, check order) were my R2 library's readings, and C1's wording favours the build.

## 2. My probes on the built code (`auditor_r4_probes.py`)

Both probes call the production functions (`features.histories`, `snapshot_gammas` and `side_values`; `panel.EditionOffsets`) on perturbed panels I build myself. Probe A does **not** use `features.py`'s `y_override` hook, and Probe B builds its leak into the data, not through the module's `release` option.

### Probe A: own history, cut by Stage 0 order

* **Setup:** 20,000 frame sides (8,000 in 2024–26) and 30 cuts (12 in 2024–26).
* **Perturbation:** every panel row with order ≥ cut gets +30 km/h. Snapshots stay at the clean build (C7).

| Check | Result |
|---|---|
| Sides before the cut (1,483–19,374 per cut) or at it that moved (tolerance 1e-12) | **0** at every cut |
| Power: sides after the cut that moved | 378–16,666 per cut |
| Leaky L1: the target's own row added to its history (tried ±30, because the robust clip hides a +30 shift on an already-clipped high outlier) | Fired at **30/30** cuts |
| Leaky L2: the player's next own row added to its history | Fired at **30/30** cuts (32–98 sides each) |

### Probe B: the clock, cut by day

* **Setup:** 30 cut days, all inside events (17 in 2024–26):
  * the second-week Wednesday of every Slam main draw of 2021–26 in the frame;
  * the Thursday of the two biggest tour events of each of 2023–26.
* **Perturbation:** every row with es > D is perturbed in **both** the filter and the snapshot inputs, and `EditionOffsets` is refitted. On 25 days the perturbation is +30 km/h; on 5 days it is U(100, 250) noise.

| Check | Result |
|---|---|
| Frame sides with lf ≤ D that moved, on f̂, σ̂, L̂, x_raw and the γ used (71,376–126,716 checked per day) | **0** on every day |
| γ̂ at D, D − 1, D − 3, D − 7, every edition | Identical to 6e-14. This is floating-point summation order: the clean snapshots come from `panel.py`'s disk cache, fitted in file row order |
| Power: sides with es > D that moved | 72–97% of the sample |
| Leaky L1: rows released at their tournament date (lf := tdate − 1, in the data) | Fired on **30/30** days (46–491 sides) |
| Leaky L2: the next own row added to the history | Fired on **30/30** days (250–419 sides) |

## 3. Code review against C1–C4

| Spec item | Finding |
|---|---|
| **History rule** (C3) | `td < td_m` or (same `tournament_id` and `round_order` < the target's) never admits another event of the same week. Qualifying rounds (round_order 1–4) precede main-draw rounds (10–17), so a qualifier's own qualifying rows count. Round-robin peers share round_order 10, so earlier round-robin matches of the same event are left out: conservative, and it touches finals events only |
| **Truncation and centring** | History rows need obs ≥ es − 364. Each target is centred with one snapshot at its own `es` (`snapshot_gammas`, grouped by target day) |
| **Filter and projection** | Equations as C3: φ = 2^(−Δ/h), Q = qΔ, the OU variance, S = P11 + 2P12 + P22 + R, K and the Joseph-free update, the innovation clipped at c√S. The first row skips the prediction step. Projection to `es`; no history gives f̂ = 0 and σ̂ = √s2f. Equality with an independent filter: 0.0 (T-F1) and 2e-14 (§1) |
| **Constants** | Men: h 14, s2f 12, q 4/365, c 2, ν 7/8, σ 13.49. Women (A3): c 4, ν 14/10, σ 10.72. C2: τ² 22, s 12.4, K 25, 364-day window, ≥ 50 rows. All as frozen |
| **s_f** | SD (ddof 1) of unclipped A − B, men's frame matches 2022–23 only: 2.2240, reproduced exactly |
| **Clipping, women, `spd_raw`** | ±4 s_f (1–11 matches per tour × season × Slam cell). Women: `spd_f` = 0 everywhere, `spd_f_all` carries their values. `spd_raw` is the registered statistic (raw y, n-weighted, obs windows ≤ 14 / ≤ 364, both sides present, ÷ 5.998); my implementation agrees to 0.0 |
| **Orientation** (C4) | Sides follow the frame's pre-rebuild ids, and the clock comes through `id_map`. 88 `id_conflict` (all women's 2026), 21 of them `flipped`; my rebuild with the same rule agrees exactly. 20 of the 67 other conflicts carry a frame id that has rebuilt history; only A3 is touched |
| **flip and registry** | All three columns have registry kind `diff`. `arms.flip` negates each and keeps NaN; flip is an involution; the 58 base columns hash-equal the frame's. The frame was loaded without `a_won` |
| **Runner guards** | Each fit stores the feature SHA-256 and registry entries. `forecasts.py` refuses a speed-arm fit whose stored hash differs from the current file. On copies, `feature_status` refused: no probe records, a failed probe B, `probes_pass` false, a stand-in panel, `reads_results` true, and a changed file. It **accepted a meta with no recorded hash** (F1) |
| **Hashes on disk** | `speed.parquet`, `speed_panel.parquet` and `features.py` all equal the hashes in `speed_meta.json`. `feature_status` is ok. The 43 builder tests pass, and the outputs were unchanged afterwards |

## 4. Values-only sanity (`auditor_r4_values.py`; no outcome read)

**Men, `spd_f`:**

| Statistic | 2024–26 | 2022–23 (reference) |
|---|---|---|
| Mean | −0.03 to +0.01 (side A is random) | |
| SD | 1.01–1.19 | 0.95–1.02 |
| Kolmogorov–Smirnov distance to 2022–23, per season × Slam | 0.027–0.070 | |
| Exact zeros | ≤ 0.09% | |
| \|value\| < 0.05 | 5–9% | |
| Clipped at ±4 | 1–11 per cell | |

**Men, `spd_raw`:** present on 704–1,324 non-Slam and 226–325 Slam matches per season, SD 0.97–1.27, correlation with `spd_f` 0.71–0.89.

**Women:**
* `spd_f` is 0 on every match.
* `spd_f_all` has SD 0.17–0.25 at non-Slam matches, where it holds decayed remnants of a past Slam, and 0.64–0.93 at Slams; 2 values are clipped (2025 Slams).

**Extremes.** Men's side f̂ beyond ±8 km/h on 0.06–0.25% of sides (minimum −12.3, maximum +10.4). I traced two of them through the panel rows:
* a qualifier's run to the Madrid 2026 semi-final at 201–211 km/h against a level of about 192 (f̂ +9.0);
* a top player's Madrid 2026 at 188–197 km/h against about 201 (f̂ −6.9).

A broken key statistic (154.5 km/h in Monte Carlo 2026 qualifying) was clipped by the robust update. These are runs in the data, not code defects.

## 5. Issues and fixes

| # | Severity | Owner | Issue | Fix |
|---|---|---|---|---|
| F1 | Low (before the freeze) | Strategist | `arms.feature_status` accepts a `speed_meta.json` with no `features_parquet_sha256`, so probe records could belong to another file. The current meta records the hash, and it matches | Refuse when the hash is absent. Also refuse when `panel_sha256` ≠ the current `speed_panel.parquet`, or `features_py_sha256` ≠ the current `features.py` |
| F2 | Low | Strategist | `3_strategist_build.md` note 1 ("the feature file is a stand-in") is stale. The file on disk is the R3 build (`standin_panel` false, SHA `fcd8d241…`) | Correct the note. Pre-registration §3 records `fcd8d241…`, the panel `f774eb50…` and s_f 2.2240 |
| F3 | Info (spec text) | Lead | C2's "else 0" fallback did not say which level 0 means | Record it: 0 is the snapshot's reference level (men's tour main draws when they hold ≥ 200 rows, else the Slam main draws). Effect: ≤ 0.05 s_f on one men's match |
| F4 | Info | Engineer | Deviations 2–4 (`mislink_level`, round check before duplicate check, `obs` floored) | Accepted, with their measured effects in §1. List them in the pre-registration |
| F5 | Info | Engineer | Disk-cached snapshots are fitted in the panel file's row order and features.py's in-memory refits in its own, so they agree to 6e-14, not bit for bit | None needed. Reproducibility is exact through the cache |
| F6 | Info | — | The modeller's R4 attribution (families, plus the reference) misses the round-check granularity, which caused the 1.66 s_f maximum | None. My R2 library is superseded by this rebuild for R5 checks |

## 6. Looks (for the ledger)

| # | Seasons | What was related to what | Script → output |
|---|---|---|---|
| R4-1 | 2013–2026 | Feature values only: my rebuilt `spd_f`, `spd_f_all` and `spd_raw` against the build's (agreement); panel speed values and source choices against the R3 panel; point means against `stage1_match_stats` (speeds only) | `auditor_r4_rebuild.py` → `.json`; `auditor_r4_residual.py` → `.json` |
| R4-2 | 2014–2026 | Probes: perturbed speeds against unperturbed feature values. No target, no outcome | `auditor_r4_probes.py` → `.json` |
| R4-3 | 2022–2026 | Values and distributions of the built columns; two players' 2026 panel speed values (the extremes) | `auditor_r4_values.py` → `.json` |
| R4-4 | – | The runner's feature guards on modified copies of `speed_meta.json` (metadata only, in the scratchpad) | inline, §3 |

No speed value or feature was related to a match result, a statistic target, a box score or a price.
