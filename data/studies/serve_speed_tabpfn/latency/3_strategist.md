# Latency follow-up: the exploratory outcome scorer (integration strategist)

7 October 2026 · agent 3. Built to [plan.md](plan.md), reading 3.
* **Exploratory.** 2024–26 results were opened by the study's pre-registered test.
* **No real outcome was read.** `--run` was not run; `variants.parquet` does not exist yet.

## What was built

**`src/eda/serve_speed_tabpfn/latency/score_latency.py`** imports the study's machinery from `score.py`, unedited: `population`, `Bank`, `Scorer` (the decided calibration), `nudge`, `nudge_parameters`, `encompassing` and `labels`.

Each variant goes into the Scorer's `spd_f` slot, so the study's S9 code runs unchanged.

Per variant, on men's matches of 2024–26, debut seasons out (7,068):

| Output | Definition | Direction |
|---|---|---|
| S9 shrunk and unshrunk | The walk-forward nudge: s and b refitted per variant on 2019..Y−1 (base seeds 0–3), applied to the 16-seed base. Against the calibrated base, mLL, block-only interval; pooled and by season; s, b̂, SE and b̃ per season | positive = the nudge better |
| S0 | `encompassing`, in log-odds **per unit of the variant's own column** | positive = the higher speed state wins more than the base says |
| Share of A | The variant's S9 gain / A's (shrunk and unshrunk; A = `spd_f` as run). A point value | – |

* **By-season split.** It mirrors `score.nudge`'s formula, and the code refuses to report it unless its pooled value equals `score.nudge`'s to 1e-12.
* **Headline:** `spd_B_M0` and `spd_B_M2`, flagged in the output (plan.md).

**Modes:**
* **`--check`** (result-free) writes `check_latency.json`:
  * the variants;
  * per variant, values only for men 2024–26: non-zero count by season, SD, correlation with `spd_f`, and the largest difference from it;
  * whether the code, model frame, feature file and population equal the study's frozen ones;
  * whether the 128 base fits are present, and the reuse checks.
* **`--synthetic`** draws y ~ Bernoulli(expit(0.9·η_B + β·z_plant)), never selecting `a_won`. It reports, per variant:
  * S0's mean and how often it rejects;
  * S0's coverage of the planted β, for the planted column;
  * S9's mean and rejection rates.
* **`--run`**, once:
  1. It refuses unless:
     * no results exist yet;
     * the study's `results.json` is present;
     * the code hash equals the study's (observed now: `6bcfc06c…` on both), as do the model frame and the feature file (`fcd8d241…`);
     * the population hash equals the study's;
     * all 128 base fits are present and both reuse checks have passed.
  2. It then reads `labels()` and scores `spd_f`. If that does not reproduce the study's S9 shrunk (+0.410 [+0.045, +0.775]: estimate and both bounds) and S0 (+0.0650) to 1e-9, it stops without writing anything.
  3. Only then does it score the variants and write `results_latency.json` and `.csv`. Every row carries its unit, its direction and a verdict.

**The variants file is validated whole, against the whole model frame** (all 63,737 matches, every season):
* one row per frame match, and no unknown id;
* finite everywhere;
* 0 for every woman.

A broken build is refused even in seasons the scorer never reads. Only columns named like `^spd_[A-Z][A-Za-z0-9]*_M\d+$` (`spd_A_M0`, `spd_B_M2`, `spd_L7_M0`) are variants; anything else is ignored as a diagnostic. `spd_A_M0` should equal `spd_f`, and `--check` reports its largest difference.

## Tests: `test/serve_speed_tabpfn/test_ssp_latency_score.py` (7 pass; 56 in the study folder)

On the harness tests' stand-in world plus a fake variants file:
* validation refuses NaN, a woman ≠ 0, a missing row and a duplicate;
* `--check` reads no result;
* `spd_f` and an identical `spd_A_M0` reproduce `score.py`'s S9 (both versions), its parameters and S0 **exactly**;
* signs and shares;
* `--synthetic` never selects `a_won` and recovers a planted β;
* `--run` refuses a "study" it cannot reproduce, which `score.py` computed independently. It writes nothing then, reproduces exactly otherwise, and refuses a second run;
* `--run` refuses changed inputs before reading labels.

**A test artifact, fixed.** The fake variant generator shared the stand-in world's seed. Its first noise draw copied the base's log-odds, so a "proxy" was collinear with the base: S0 read 0.47 and its nudge lost. S0 equalled a plain logistic fit, so the scorer was right. The generator now has its own seed stream.

## Synthetic sanity (stand-in world, not real data)

| | Null, 100 replicates | Planted β 0.3 on `spd_B_M2`, 50 replicates |
|---|---|---|
| S0 two-sided rejection | 2–4% per variant | `spd_B_M2` 100% (b 0.307, covers β 94%); proxy `spd_B_M0` (corr 0.55) b 0.194 against ~0.18 expected; noise 6% |
| S9 shrunk, rejection positive | 0–1% | 94% (`spd_B_M2`), 50% (the proxy) |
| S9 shrunk, mean | −0.02 to −0.16 mLL (the cost of fitting a useless b) | +7.2 mLL (`spd_B_M2`), +2.6 (the proxy, about 36% of it) |

The verifier or the lead should repeat `--synthetic` on the real base forecasts once `variants.parquet` exists. It is result-free.

## For the lead

1. When the variants exist, run `./python.sh src/eda/serve_speed_tabpfn/latency/score_latency.py --check`. Confirm the variant list, `spd_A_M0`'s difference from `spd_f`, and that the inputs equal the study's.
2. Optional, result-free: `--synthetic --plant spd_A_M0 --beta 0.065 --reps 100`.
3. `--run` once; log it in the look ledger.
4. **Interface assumed from the modeller:** columns `spd_<scenario>_<method>`, never NaN, women 0, one row per frame match. A different naming leaves a variant unscored; `--check` shows which.

## Looks

None on real data. Read on disk:
* the study's published S9 and S0 numbers (from `results.json`) and its frozen hashes;
* the code and feature hashes, recomputed.

The stand-in and scratch worlds use synthetic data only.
