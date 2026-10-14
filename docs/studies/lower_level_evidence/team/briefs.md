# The team's briefs (for re-running the review)

9 October 2026 · For the session that re-runs this review when new lower-level data lands · The verbatim briefs of the first run, condensed only where they repeat.

**How to re-run.** Launch the same roles with these briefs. Change three things:
* the date;
* the Stage 0 they read: `--stage0-dir <candidate Stage 0>` instead of the frozen reference;
* the label of their outputs, so the first run's evidence stays beside the new one.

Then compare the new snapshot with the first one (`src/eda/lower_level_evidence/refresh.py`; see the [dossier](../README.md#re-running-it)). The [re-review triggers](../README.md#when-to-re-review) say when.

## The organisation

| Role | Focus | Reads | Writes | Depends on |
|---|---|---|---|---|
| 01 Lineage auditor | How each of the 58 inputs and stage 2 takes in lower-level matches today, in the code | builders of the chain, decisions | `team/01_lineage.md` | nothing |
| 02 Evidence-dose and exposure analyst | How much of each input's evidence is lower-level, for whom; where the model is weak against the close | frozen Stage 0, frame, fits | `team/02_composition.md`, `composition.py`, `data/…/composition/` | nothing (runs beside 01) |
| 03 Level-translation statistician | Per statistic: the level offset, whether opponent adjustment removes it, and the exchange rate of a lower-level match | frozen Stage 0 (outcomes to 2024) | `team/03_translation.md`, `translation.py`, `data/…/translation/` | nothing |
| 04 Incoming-data scout | What lower-level data is coming, when, how much reaches the model's players, the re-review triggers | collection plan, data map, run logs | `team/04_incoming.md`, `data/…/incoming/` | nothing |
| 05 Best-practice researcher | Sports statistics and betting practice for cross-tier evidence | the web | `team/05_best_practice.md` | nothing |
| 06 UFC-analog analyst | How the UFC pipeline's non-UFC prior works, and its lessons | the UFC repository (read-only) | `team/06_ufc_analog.md` | nothing |
| Lead | Synthesis, the proposal, the dossier, the one-command refresh | all of the above | `README.md`, `refresh.py` | 01–06 |
| 07 Red team | Verifies the dossier's claims and attacks the proposal | the dossier, the code, the data | `team/07_red_team.md` | the draft dossier |
| 08 Candidate builder | Builds and scores the first remedy (the 18 aggregate inputs translated) against the frozen reference | the chain in a sandbox, the GPU | `team/08_candidate.md`, `translate_hooks.py`, `data/…/candidates/` | 01, 03 |

Six specialists work in parallel because their questions are independent: the code (01), the data's composition (02), the statistics of translation (03), the pipeline of incoming data (04), outside practice (05) and the owner's own precedent (06). The lead merges them, then two roles check the result: one attacks the dossier (07), one tests the main remedy on the model itself (08).

## The shared brief (every specialist received it)

* **The owner's question,** verbatim (see the [dossier](../README.md)).
* **The model:** the current best model's two stages, its 58 inputs and the chain that builds them (`src/eda/model_rebuild/run_chain.py`).
* **Already known:** the event-levels study (training rows are main tour only; Challenger rows lean harmful; the same players gain +2.9 points of total points won at Challengers; `points_52w` is the one raw-rate input; Elo has one K schedule; the market under-rates players arriving from lower levels); the input-data audit's findings #6 and #7; the product-centring study; the adoption framework.
* **The guardrail:** the frozen reference and its candidate comparison (`compare.py`).
* **Ground rules:**
  1. Read CLAUDE.md first; Python only through `./python.sh`.
  2. Read-only except their own outputs; no state-changing git; delete nothing; no downloads, scrapers, GPU fits or rebuilds.
  3. Use the frozen reference's tables (`src/eda/lower_level_evidence/common.py`).
  4. Read no outcome of a 2025–2026 match (the proposed holdout); counting them is allowed.
  5. Label claims observed, inferred or suggestion; cite path:line.
  6. Never a bare signed score: direction, winner, and "tie" when the interval spans 0.
  7. Respect the owner's thesis: per-statistic profiles first; Elo and win-rate aggregates are priced-in controls.
  8. Write plainly.

## 01 Lineage auditor

For each input group and for stage 2's `spd_L`, trace the code from Stage 0 to the model frame and record:
1. the builder and function (path:line);
2. which Stage 0 matches enter (buckets, tours, qualifying, statuses, years, box score required), with the filter's line;
3. how a lower-level match is treated against a main-tour one: identical weight; level-specific K or weight; a level covariate; opponent adjustment in a joint solve with no level term; raw rates; counts;
4. memory, window, decay and clock;
5. whether norms, pool means, constants or K values are computed over pools that include lower levels;
6. box-score dependence;
7. a verdict: EQUIVALENT, SHARED-ADJUSTED, LEVEL-AWARE or NOT-USED.

Then: the serve-speed stage's sources and levels; each contamination path confirmed or refuted (`points_52w`, the products' drift, Elo's single K, `sets_14d` after the splice, others); and the forward risk of each incoming dataset (collection plan P1–P11) per input group.

## 02 Evidence-dose and exposure analyst

1. `composition.py` (CLI `--stage0-dir`, `--frame`, `--label`, `--out`; reruns unchanged on a candidate Stage 0): for each model-frame match and side, the player's earlier matches by bucket in 14, 28, 91 and 365 days and the career, for results and for box scores, with the leak-proof clock where practical.
2. The lower-level share per channel and window, by tour, season, target level and rank band.
3. The ITF box-score regime of 2025–26, and a preview of what ITF box scores for 2018–2024 would add.
4. Exposure: main-tour matches in 365 days and the career; where the less-exposed side has fewer than 10.
5. Where the current model is weak against the close, 2019–2024 only: the gain over the recalibrated close by exposure and by lower-level dose, with intervals; the close's calibration slope by bucket.
6. Tests of the window counting.

## 03 Level-translation statistician

Outcomes of 2013–2024 only; men and women apart; ace and double-fault rates, first serves in, first- and second-serve points won, serve, return and total points won, holds, breaks, break points saved and converted.
1. Raw same-player gaps between MAIN and TQ, GSQ, CH, CHQ.
2. **The key diagnostic:** an opponent-adjusted model solved over all levels with no level term, as the IOS is; do the same players' residuals differ by level? Estimate level effects δ_L, and whether they depend on tour, surface and home tier; check the opponent side.
3. **The exchange rate:** θ̂ = (k·μ + n_M·x̄_M + (n_L/λ_L)·(x̄_L − δ_L)) / (k + n_M + n_L/λ_L); fit δ, λ, k on 2013–2018, validate on 2019–2024; arms MAIN only, pooled as equivalent, translated, translated and discounted; gains overall and for low-exposure players.
4. Results channel, briefly: a coarse K multiplier for Challenger and ITF results in a plain Elo.
5. ITF: what results alone allow; `translation.py` reruns unchanged once ITF box scores of 2018–2024 are wired in.
6. Selection biases: boundary players, regression after promotion, survivorship, eras.
7. Tests that recover a planted δ and λ.

## 04 Incoming-data scout

1. Read the collection plan, the gap-downloads report, the data map, the run logs, the scheduler and the collection decisions; list the running collectors (read-only).
2. A table of P1–P12: status with evidence, levels, years, grain, volume, landing date, wiring needed.
3. The input families each package would touch once wired, and the dose: lower-level matches of 2018–2024 that are results-only today and would gain a box score or points, split by tour and by whether the player also plays the main tour.
4. What the new data enables that is impossible today.
5. Data-quality and integrity risks that would bias a player's lower-level profile.
6. Re-review triggers and the re-run order.

## 05 Best-practice researcher

1. Cross-tier translation in sports: baseball's minor-league equivalencies and projection systems, hockey's NHLe, college-to-NBA, football league strength and promoted-team priors; tennis (Tennis Abstract, Ultimate Tennis Statistics, Kovalchik, Ingram, Gorgi–Koopman–Lit, TrueSkill Through Time, Glickman). Typical factors, discounts and regression after translation; which statistics translate well.
2. Statistics: credibility theory, empirical Bayes, hierarchical models, partial pooling, multi-fidelity modelling, data fusion, measurement error, transfer learning; how to put a prior into TabPFN, which takes no sample weights.
3. Betting practice: where markets are weak; favourite–longshot bias by tier; closing-line value; integrity risk and robust results data; staking for low-information players; how sharp bettors treat new players.
4. Ranked recommendations for this project, each with its evidence strength, and the evaluation protocol best practice demands.

## 06 UFC-analog analyst

Read-only on the UFC repository and its memory folder.
1. The mechanism of the UFC informed prior: the data, the model, the shrinkage, how its weight falls with UFC fights, the channels that consume it, the experience gates.
2. What worked and what failed there, and why.
3. What maps to tennis and what does not.
4. Lessons for the tennis design and its tests.

## 07 Red team (after the draft)

Re-derives the dossier's load-bearing numbers and code claims from the files, and attacks the proposal: leaks under the match clock, holdout use, whether the market already prices it, whether TabPFN can use it, and its cost against the adoption framework's bar. Lists what must change.

## 08 Candidate builder (after 01 and 03)

* **The build.** Translate each lower-level match by a per-statistic, per-tour, per-level offset (estimated on 2010–2018 same-player-season contrasts) before it enters the 17 one-step forms and `points_52w`. Patch only a sandbox copy of the chain (`run_chain.py --setup --candidate`, `MODEL_REBUILD_SANDBOX`), through `src/eda/lower_level_evidence/translate_hooks.py`.
* **The gates, before any fit:**
  * reproduction: every other input equals the reference's;
  * invariance: no lower-level evidence, no change;
  * direction;
  * linearity, for the half dose.
* **The arms:** both changes; each channel alone; half the dose; a placebo twin; the reference and the candidate each with `low_share_diff` (the exposure-gap control).
* **Fits and scores:** seeds 0–3 on 2019–2024; `compare.py` on 2020–2024, both stages; paired readings by stratum.
* **Pre-registration** and its hash come before any score.
* **For P7:** the same brief, with the ITF box scores wired into the candidate Stage 0.
  * **The ITF offsets are fitted walk-forward on the match clock:** a match of season Y uses ITF box scores of 2018 .. Y − 1 only, never 2025–2026. A fixed set fitted on 2018–2021 would leak into a candidate scored on 2020–2024; if one is used, score only the seasons after its window.
  * **Three arms:** ITF as it stands, ITF through the layer, and the reference.
  * **The first run's result** (§7 of the dossier): unresolved at the close, no more than the share signal (R_S2). Keep R_S2 as a control in every later run.
