# R3 build: the state modeller (agent 2)

7 October 2026. C3 and tests T-F1 to T-F6 of `2_audit.md`, built on the engineer's real panel. All numbers are **observed**. No match result, statistic target or price was read; 2024–26 appears only as values and counts. No new look; no GPU.

## What was built

* **Code:** `src/eda/serve_speed_tabpfn/features.py`. It takes 7 s, or 2.8 min with both probes.
  * It follows C3: each side's own rows in [es − 364, es), one snapshot γ̂(es) per target via `panel.EditionOffsets.gamma`, and my own vectorised filter with the frozen constants, projected to `es`.
* **`features/speed.parquet`** (63,737 rows; SHA-256 `fcd8d241…`):
  * the columns `spd_f`, `spd_f_all`, `spd_raw`;
  * per side: f̂, σ̂, L̂, `hist`, `k14`, `k28`, `last_age`, `ks28` / `pts28` (the 28-day basis mix), `x_raw`;
  * `id_conflict` and `flipped`.
* **`features/speed_meta.json`:**
  * constants, and the C2 constants read from `panel.py`;
  * **s_f = 2.2240 km/h** (men 2022–23, ddof 1);
  * SHA-256 of the panel (`f774eb50…`) and of `features.py`;
  * both probe records with pass flags (`probes_pass: true`);
  * coverage by tour × season.
* **`design/modeller_panel_standin.py`** was used only before the panel landed; the meta records `standin_panel: false`.

## Coverage (values and counts only)

| Men | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|
| Both sides timed within 28 days | 64% | 67% | 79% | 74% | 78% |
| At least one side | 91% | 89% | 95% | 90% | 93% |
| `spd_raw` present | 1,141 | 1,289 | 1,632 | 1,312 | 930 |
| SD of f̂_A − f̂_B (km/h) | 2.15 | 2.29 | 2.55 | 2.28 | 2.69 |

* The SD is 0.6–1.1 km/h in 2019–21, when only Slams are timed.
* `spd_raw` counts equal the engineer's both-sides-14-day counts exactly.
* 7–13 matches per season are clipped at ±4.
* Women: `spd_f` is 0; `spd_f_all` has an SD of 0.30–0.48.

## Tests and probes

`./python.sh -m pytest test/serve_speed_tabpfn/test_ssp_features.py -q`: **10 passed.**

| Test | Result |
|---|---|
| T-F1 | Against `auditor_lib.kalman_batch` on 2,000 random targets, same centred rows: max difference **0.0**. Against my R1 scalar filter (200 targets): ≤ 1e-9 |
| T-F2 (Probe A) | 5,000 sides, 26 order cuts (12 in 2024–26). **0 values moved before or at a cut** (f̂, σ̂, L̂, x_raw; tolerance 1e-12). Leaky control moved at **24/26** cuts. **PASS** |
| T-F3 (Probe B) | 26 days: the timing probe's 4, 9 more Slam second Wednesdays of 2024–26, and 13 random. **Every** frame side with lf ≤ D was checked (2.47 million checks) on f̂, σ̂, L̂, x_raw and the γ̂ used: **0 moved**. Leaky control (`release="tdate"`) moved 5,272 sides. **PASS** |
| T-F4 | The constants, C2 constants and s_f (recomputed from ≤ 2023 values) equal the frozen ones |
| T-F5 | Flipping A and B on 600 matches negates all three columns exactly; NaN stays NaN |
| T-F6 | The coverage table matches the parquet |

Also tested:
* one row per frame match;
* no NaN in `spd_f` or `spd_f_all`;
* the women's values follow the rules (`spd_f` 0, `spd_raw` NaN);
* everything is within ±4.

## Agreement check (`design/modeller_agree.py` → `features/agreement_auditor_lib.json`; s_f units)

| Comparison | corr | Within 0.05, men | Within 0.05, all matches | Men 2024–26 |
|---|---:|---:|---:|---:|
| (i) Fully independent (auditor panel, snapshots, filter) | 0.99932 | 98.06% | **99.04%** | 93.3% |
| (ii) auditor_lib on the engineer's panel | **0.99992** | **99.62%** | 99.81% | 98.9% |
| (iii) As (ii), with the auditor's old families | 0.99952 | 98.25% | 99.13% | 93.9% |

* **The criterion holds** on all frame matches in (i), and on men alone in (ii).
* **The men-only shortfall in (i) is E7.** (iii) shows it comes from the Challenger family, which was ruled in. The two panels otherwise differ on only 26 rows and 1,097 half-day `obs`.
* **For R4:** run auditor_lib with C1's families.

**What remains in (ii) is a reference effect, not a leak.**
* `panel.py` re-references γ to the men's tour main draws; auditor_lib does not.
* On fitted editions the two differ by an exact constant (to 1e-15 on 12 checked days), which the diffuse level absorbs.
* The "else 0" fallback, for an edition whose family has nothing in the window, is not shifted. That leaves a small relative offset (fallback SD 0.08–0.51 km/h).
* Under `panel.py`, 0 means the tour main-draw level, so I treat this as a spec clarification for R4.

## Deviations

1. Rows tied on (tdate, tournament_id, round_order), which are round robins, are ordered by `obs`, then `match_id`.
2. `last_age` can be −1 day (20 sides per side) because of clock windows. The projection uses max(·, 0), as specified.
3. Probe A's cut targets have a timed own match, so the leaky control can fire.
4. `spd_raw` uses the panel's floored `obs`.

## Disagreements

None that would change a ruling. I accept M1 (my biased oracle) and M2 (the omitted stratum).
