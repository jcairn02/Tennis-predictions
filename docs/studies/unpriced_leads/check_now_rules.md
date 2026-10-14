# Rules for the check: written before looking

**Status:** frozen 13 Oct 2026, before any result from 2025 on was read for these patterns. The SHA-256 of this file and of the code are in the [process log](process_log.md). A change before the check runs re-freezes the rules with new hashes. After the check runs, nothing here changes.

The owner adopted this single check on 13 Oct 2026 in place of the two-look plan in the [pre-registration](preregistration.md), which would most likely have given a firm answer only in August 2027. The five patterns themselves are unchanged.

## In plain words

1. **What we test.** The five patterns combined into one score, exactly as registered on 13 October: the same statistics, the same directions, equal weights.
2. **Which matches.** Every match in the model's data from the 2025 season on: 9,457 matches, the last on 23 September 2026.
3. **The question.** Do the patterns predict winners beyond our full current model (TabPFN plus the serve-speed adjustment)? That is where the adjustment would sit.
4. **The pass mark.** The result must lean the right way by at least one standard error.
   * If the patterns are as real as we expect, this passes about 7 times in 10.
   * If they are dead, it passes by luck about 1 time in 6.
   * Pass: we use the adjustment. Fail: we don't.
5. **The size.** Start from 45% of the strength found in 2013–24. Update it with the 2025–26 result, each weighted by how precise it is. The size is never below zero.
6. **The limit.** The combined score is capped at 3.5 times its typical size.
   * In 2013–24 the cap touched about 8 matches in 1,000, mostly post-Slam-slump matches.
   * It doesn't weaken the pattern's reading.
   * At the expected size, no single match moves by more than about 3½ percentage points at even odds.
7. **Missing data.** A pattern whose data is missing for a match adds nothing. A pattern whose data supply has collapsed in a month is switched off for that month (the registered rule: below 70% of the same months a year earlier).
8. **The monthly re-check.** Once a month, the size is recalculated the same way on all matches since the start of 2025. It can grow, shrink or go to zero. Nothing else changes without a new decision.
9. **If the check fails.** The adjustment stays off. Any later attempt, such as a fresh search on 2013–22, counts as a second attempt and needs a stricter pass mark, decided before it runs.
10. **Reported alongside, without changing the decision:**
    * the result against the closing odds alone (your original question);
    * how much of the old strength survived;
    * the months with Pinnacle odds and the months with only BetOnline odds;
    * each pattern on its own;
    * finished matches only;
    * whether it also meets the usual scientific standard (5%).

## For a reviewer: the exact specification

**Code:** [check_now.py](../../../src/eda/unpriced_leads/check_now.py) (the check), [build_forecasts.py](../../../src/eda/unpriced_leads/build_forecasts.py) (the base). The registered [look.py](../../../src/eda/unpriced_leads/look.py) and [registry.json](registry.json) are used unchanged, with the registry's hash checks.

| Part | Specification |
|---|---|
| Window | The instance's frame (`template_2026-10-10/model_frame.parquet`, hash-checked), seasons ≥ 2025, all tournament dates, debut seasons out: 9,457 matches (atp 4,810, wta 4,647). The 136 matches of season 2025 dated December 2024 are in, as in the registered Look A |
| Score | `s = look.omnibus_score(groups, frame, "window", gates)`: the registered members, signs, completeness gate, in-window projection on the 48 inputs and RMS scaling. `z = clip(s / RMS(s), −3.5, 3.5)` |
| Base | The current best model's both-stages forecast for every window match. It is rebuilt by `build_forecasts.py` with the recipe of `edge_anatomy/data.py`, and equals the stored `analysis.parquet` exactly (max \|diff\| 0) on the 30,839 matches both hold. The one departure: 909 matches of 2026 have no value in the speed column (it ends 28 Jul 2026), and their speed term is 0. Only 416 men's matches of 29 Jul – 23 Sep 2026 are affected, because women's speed term is always 0. The term is small: 2026 b = 0.037 per unit, and the column's SD is about 0.76 |
| Decision reading | `look.fit(frame, z, base="L_full")`: logistic, no intercept, per-tour slope and per-tour curvature (L\|L\|) on the base's log-odds, β on z per RMS; cluster-robust over four-week blocks |
| Pass mark | β / se ≥ 1.0. Pass rates (normal approximation, Look A's standard error scaled to 9,457 matches): 0.72 at a realisation of 0.45, 0.16 at 0 |
| Prior | N(m₀, m₀²), m₀ = 0.45 × 0.0859 = 0.0386: the registered discovery β per SD (`look.fit` on seasons ≤ 2024, beyond the close, uncapped), as in the registered empirical-Bayes secondary |
| Size | On a pass, b = max(0, posterior mean) per SD of z, divided by z's RMS in the fit to give b per unit of z. On a fail, b = 0 |
| Live adjustment | logit q = s_tour·η + b̃·spd_L + b·z_live, applied after the serve-speed step in the daily engine. η, s_tour, b̃ and spd_L are unchanged |
| z_live | `check_now.score_from_params` with the window's frozen parameters (`params.json`): each member's projection coefficients and RMS scale by tour, each group's RMS, the combined score's RMS, the limit. On the window it reproduces `look.omnibus_score` exactly; this is asserted on every run |
| Live gate | A member with a registered gate is switched off for a live match of month M when its count over the three complete months M−3..M−1 is below 70% of the same months a year earlier. This is the registered gate's trailing form, because a live match has no complete next month. The check itself uses the registered centred gate |
| Monthly re-check | The same computation on the newest instance: all matches from season 2025 to the latest, z's parameters refitted on that window, b recomputed. The members, signs, weights, gates, limit, prior and sizing are unchanged. Running it on a new instance needs the instance paths made arguments: a mechanical change, to be made in Stage 4 and recorded in the process log |
| Second attempts | A new pass mark, stricter than 1.0, is fixed before any second attempt is run |
| Reported, no decision | The registered primary (beyond the close, uncapped) with the realisation ratio; beyond the close, capped; beyond stage 1 alone; uncapped beyond the model; the Pinnacle months; the BetOnline months; matches with a speed value only; completed matches only; each group beyond the model; the share of matches at the limit; whether the one-sided p (t on G − 1) is ≤ 0.05 |
| Guard | The check reads results from 2025 on only with `--owner-go "<the owner's words>"` |
| Dry run | Seasons 2023–2024, already read by the registered dry run. β/se +2.68 beyond the model; +2.75 beyond the close, matching the registered dry run; reproduction max \|diff\| 0; the rebuilt base equals the registered one. 2023–24 lies inside the discovery seasons, so this checks the code and says nothing about the patterns |

**What was seen before this was written:** only discovery readings (seasons ≤ 2024) and outcome-free counts of 2025–26: matches by season and tour, odds sources, forecast and member-value coverage by month. No 2025–26 result was read for these patterns. While counting forecast coverage, one count script loaded the whole forecasts table, including its result column; it printed only column names and counts. The process log records this.
