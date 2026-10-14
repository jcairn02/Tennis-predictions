# Pre-registration: centre the IOS ratings before forming the 7 matchup products

8 October 2026. Written before any centred product was built or any forecast scored. The owner asked for this change to be executed ("Centre the IOS ratings before forming the 7 prod_* products … Its cost in log loss has never been measured").

## The problem (observed before this study)

* **The products.** Each of the model's 7 IOS matchup products is `prod_s = O_A·(−D_B) − O_B·(−D_A)`, formed from the surface-effective ratings `O + E_s` and `D + F_s` ([surface-IOS arms](../../../src/eda/surface_ios/arms.py)).
* **Why it drifts.** A common shift of every rating (o₀, d₀) adds `d₀(O_B − O_A) + o₀(D_A − D_B)` to a product, but leaves the A − B inputs unchanged.
* **The shift happened.** The ITF box scores exist only from January 2025 to May 2026. While they were in the pool, the level of the model's players rose (women's holds: mean defence 0.41 in 2024, 0.54 in 2025, 0.73 in 2026), and the products' spread grew 25–56% ([input-data audit, #6](../input_data_audit/README.md)).

## The change

For each tour and each of the 7 statistics, at every daily snapshot of the decided surface IOS (the same solve as the model's, unchanged constants):

* **Reference players at snapshot day t:** every player who served or returned in a main-tour observation of that statistic that is released by t (`lf + 1 ≤ t`) with a best-estimate day of t − 364 or later (the last 52 weeks). Main tour is the model's level set: Grand Slams, Tour Finals, 1000s, 500s, 250s.
* **Reference level:** the unweighted mean over the reference players of `O + E_s` (offence) and `D + F_s` (defence) on each surface s; for an unknown surface, of `O` and `D`.
* **Centred product:** `prod_c = −(O_A − m_O)(D_B − m_D) + (O_B − m_O)(D_A − m_D)`, with m read from the match's own snapshot (its earliest possible start) and surface.
* **What does not change.** The 14 offence and defence differences, the other 37 inputs, the solve, its constants, TabPFN's settings and stage 2's rule.

## The comparison

* **Arms.** `model` (the current best model) against `cprod` (the same 58 inputs with the 7 products centred).
* **Stage 1.** Local TabPFN-3.5, the decided settings, trained on 2013 .. Y − 1 for season Y, symmetrised, seeds 0–3 on both sides. The base's fits are the stored ones, reused after one reproduction fit.
* **Both stages.** `logit q = s_tour,Y · η + b̃_Y · spd_L`. η is the arm's seeds 0–3 mean log-odds. s and b are fitted walk-forward on 2019 .. Y − 1 from the arm's own seeds 0–3 mean, debut seasons out, with the L_weekly history column (spd_B_M1). b is shrunk with τ = 0.05. Women get their tour slope only.
  * This is the decided stage 2, except that both arms are applied with their seeds 0–3 mean rather than the base's 16-seed mean, so that the seed sets are identical.
* **Score.** Log loss, in mLL. **Positive = the centred arm has the lower log loss (better).** The 95% interval combines the four-week-block standard error with both arms' seed variance (`serve_speed_tabpfn.score.paired_stats`), with t on G − 1 degrees of freedom. An interval that spans 0 is a **tie**.

| Id | Comparison | Population |
|---|---|---|
| **P (primary)** | both stages, cprod against model | both tours, 2025 – 28 Jul 2026 |
| S1 | the same | both tours, 2022–2024 (harm check: no ITF regime) |
| S2 | the same | both tours, 2022–2026 |
| S3 | the same, by season | both tours, 2022, …, 2026 |
| S4 | the same, by tour | men and women, 2025–2026 and 2022–2026 |
| S5 | stage 1 only (calibrated, no speed term) | both tours, 2025–2026 |
| S6 | both fed Polymarket's price 24 hours before the start, calibrated and nudged with their close-fitted s and b | both tours, 2025–2026 matches with a price |
| S7 (context) | each arm against the closing price recalibrated the decided way (block-only interval) | both tours, 2025–2026 and 2022–2026 |

**Outcome-free diagnostics, made before scoring.** The spread of each product as built and centred by tour and season, and the reference levels by season.

**Power.** On 2025–2026 a paired standard error near 0.10 mLL is expected, so a true effect below about 0.28 mLL will usually read as a tie.

## Gates (all must pass before any result is read)

1. **G1.** The hooked re-solve reproduces the stored surface-IOS ratings of every row (O_eff, D_eff, O, D, E, F) to 1e-12, for all 14 runs.
2. **G2.** With m = 0, the rebuilt products equal the model frame's 7 `prod_*` inputs to 1e-12, with identical missing values.
3. **G3.** The real-date leak probe (the surface-IOS probe's slice and four cut days, results after each cut reversed): no centred product or reference level of a match that surely finished by the cut moves (tolerance 1e-9).
4. **G4.** This study's fit runner reproduces a stored base fit (model, 2025, seed 0) to 1e-6 in every query block.
5. **G5.** The stage-2 fit reproduces the published L_weekly coefficients of 2024–2026 for the base to 1e-12.
6. **G6.** The centred products are antisymmetric (swapping A and B negates them), and the flip is an involution.

## Reading

* **Primary better:** the drift was costing log loss; the analyst recommends centring.
* **Primary a tie, and S1 not worse:** no measurable cost either way. Centring would be recommended on mechanism alone (it removes a drift that follows data coverage, not tennis), stating that no log-loss gain was shown.
* **Primary or S1 worse:** do not adopt; investigate.

The owner decides adoption. This study changes no decided file.

## What is read

* **Results read, once, for this comparison:** 2019 – 28 Jul 2026 (the model frame).
  * 2025 – 28 Jul 2026 is the "H-exposed" part of the clean-holdout proposal. It has been read about 20 times by earlier studies, and this read is disclosed here.
* **Not read:** no match after 28 Jul 2026 (the proposal's sealed matches).
