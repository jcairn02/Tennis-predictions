# Surface IOS: evidence and strategy (pre-registration)

6 October 2026 · Written before any TabPFN fit of a surface arm. Research evidence, not a production, model or betting decision.

The owner's request of 6 Oct 2026: explore and audit the idea of building the long-memory IOS profile separately for each surface; derive from our own evidence how to represent it; have it audited by an independent agent; lock a plan; then test it with TabPFN-3.5 in five expanding windows (one test season each, 2022–2026), with and without the change.

Labels: **observed** = computed here; **inferred** = reasoning; **proposal** = not yet decided. Statistic-forecast gains are milli-log-loss per unit of the statistic (per serve point, per service game, …): **higher is better**, positive = the surface model forecasts the statistic in the next match better than today's pooled IOS. Match gains are milli-log-loss per match, **positive = the second-named forecast is better**; a 95% interval spanning 0 is a tie.

## 1. The idea, and what our earlier evidence said

The pasted suggestion: "Build the long-memory IOS profile (each player's opponent-adjusted serve and return strengths, statistic by statistic) separately for each surface ... Surface deviations are real: for return stats on clay they're about two-thirds the size of the differences between players. But one season correlates only about 0.2 with the next, so it needs IOS's long memory, opponent adjustment, and shrinkage towards the player's all-surface value ... Prioritise return-side stats ... and surface matchups, such as A's clay return against B's clay serve. Serve stats barely deviate once surface averages are removed."

* **Where those numbers come from.** The [market-anchoring study](../market_anchoring/README.md), section 6.3 (`surface_persistence.csv`): raw box-score rates, not opponent-adjusted, one season per player, a two-year memory. It could not judge the idea, and said so.
* **What the model does with surface today** (observed, `src/eda/ufc_ideas/stageB_ios.py`, `src/eda/match_timing/ios_time.py`). Each observation is centred on the tour's average on the match's surface, so a clay ace rate is compared with clay norms. But each player has one offence and one defence rating per statistic, pooled over surfaces. The 22 IOS inputs (14 offence/defence, 7 matchup products, the short-memory points matchup) are the input group TabPFN leaned on most.

## 2. The surface IOS model

Per statistic and tour, on the leak-proof clock (a result enters the solve the day after its latest possible finish; a match reads the solve of its earliest possible start):

    y = O_server + E_server,surface − D_returner − F_returner,surface + noise

with Stage B's weights (time decay, units) and two ridge penalties: Stage B's tuned κ on the all-surface ratings O, D, and κ_surface on the surface deviations E (serve side) and F (return side). κ_surface shrinks a player's surface value towards their all-surface value — the Gaussian-prior reading of "a player's level on clay is their overall level plus a deviation that needs evidence". κ_surface = ∞ is today's pooled IOS.

* **Solver** (`src/eda/surface_ios/ios_surface.py`): conjugate gradients with an exact per-player block preconditioner (each player's O and their four E's form an arrowhead block); the player's own unreleased earlier matches are added by an exact block re-solve (Stage B's incremental step generalised).
* **Verified** (observed):
  * κ_surface = ∞ reproduces `ios_time.run_timed` to 3 × 10⁻¹⁶, and κ_surface = 10⁹ (the surface code path) to 2 × 10⁻⁸ (`verify_solver_wta_second_won.json`);
  * the pool's A − B differences reproduce the model's stored leak-proof inputs exactly;
  * 14 tests (`test/surface_ios/`): pooled equivalence, players without data, planted surface effects recovered, a leak test, separate serve/return penalties, the guard.

## 3. Evidence

### 3.1 Surface terms forecast every statistic better (observed; `tuning_summary.csv`)

Stage B's protocol: constants chosen on 2013–2018 only, frozen before any later season. For each tour and statistic the surface model ran with κ_surface at 1, 3, 10 and 30 times the statistic's tuned κ, plus pooled, and each forecast the statistic in every evaluation-level box-score match of 2013–2018 (main tour and Challengers, with qualifying). Gain over today's pooled IOS at the best penalty, milli-log-loss per unit (higher is better; paired 95% intervals over four-week blocks):

| Statistic (unit) | Men: gain | Men: clay / grass / hard | Women: gain | Women: clay / grass / hard |
|---|---|---|---|---|
| Holds (service game) | +0.45 [+0.35, +0.55] | +0.78 / +0.78 / +0.18 | +0.22 [+0.10, +0.35] | +0.36 / +0.57 / +0.12 |
| First-serve points won (first serve in) | +0.12 [+0.09, +0.14] | +0.17 / +0.33 / +0.06 | +0.07 [+0.05, +0.10] | +0.10 / +0.11 / +0.05 |
| Aces (serve point) | +0.10 [+0.07, +0.13] | +0.15 / +0.20 / +0.05 | +0.06 [+0.04, +0.09] | +0.11 / +0.24 / +0.02 |
| Serve points won (serve point) | +0.10 [+0.07, +0.12] | +0.17 / +0.26 / +0.03 | +0.05 [+0.04, +0.07] | +0.10 / +0.08 / +0.03 |
| First serves in (serve point) | +0.08 [+0.06, +0.09] | +0.08 / +0.16 / +0.06 | +0.06 [+0.04, +0.08] | +0.07 / +0.23 / +0.03 |
| Second-serve points won | +0.05 [+0.03, +0.06] | +0.08 / +0.09 / +0.02 | +0.02 [+0.01, +0.04] | +0.03 / +0.08 / +0.01 |
| Double faults (serve point) | +0.04 [+0.03, +0.05] | +0.04 / +0.10 / +0.02 | +0.03 [+0.01, +0.05] | +0.00 / +0.14 / +0.03 |
| Break points saved (break point) | +0.03 [+0.01, +0.05] | +0.05 / −0.01 / +0.01 | +0.02 [−0.00, +0.03] | +0.01 / +0.07 / +0.01 |

* **Every statistic on both tours forecasts better with surface terms**, by 1–3% of IOS's own skill over the surface average (men's holds: 14.46 → 14.91 milli per game). All intervals exclude zero except the women's break points saved (borderline).
* **The gain sits mostly on clay and grass**, the largest per unit on grass. Hard courts gain too (about a quarter of the men's holds gain in the tuning years): a clay specialist's all-surface level is no longer pulled up on hard courts. Hard is the majority surface, so today's pooled values are closest to hard-court values.
* **Heavy shrinkage is right.** The best penalty is 10–30 times the all-surface one for every statistic; the lightest (1×) is worse than pooled for most. A player's surface value needs several seasons on that surface before it moves far from their all-surface value. (κ was tuned together with the time decay, so the ratio is not a ratio of true variances; section 3.3 measures those directly.)
* **The women's gains are about half the men's**, consistent with the shorter WTA box-score history (sparse before 2015).

### 3.2 A longer memory does not help (observed)

The same grid at twice each statistic's tuned half-life. Doubling the memory raises the surface gain by at most 0.015 milli per unit (men's aces +0.100 → +0.115; holds +0.449 → +0.457) but costs the all-surface part up to 0.18 (men's holds), so the net is worse for 15 of the 16 tour × statistic pairs (the exception: women's break points saved, +0.023 against +0.016).

*Inferred, and only partly tested* (the audit's point): doubling the memory lengthens the level's memory too, so this does not test a long memory for the deviations alone. A two-timescale model (today's memory for the level, a longer one for the deviations) was not built. Its likely value is small, since the surface gain grew by only 2–15% when the memory doubled, but the audit notes a tension: at the chosen penalties the estimated deviations are about a sixth to a fifth of the level's spread (men's holds on clay), while section 3.3 puts the persistent deviation at two-thirds or more of it. A longer-memory deviation could pass more of a stable trait. It is listed as a follow-up (section 7).

### 3.3 Surface specialisation is durable, and opponent adjustment sharpens it (observed; `persistence.csv`)

One static solve of the surface model on each of two disjoint periods, 2013–2015 and 2016–2018 (all levels, no time decay, light shrinkage κ_surface = κ), and the same players' raw (not opponent-adjusted) per-surface averages for comparison. Players with at least four typical matches on both surfaces in both periods (about 310 men for clay, 136 for grass). "Persists" is the correlation of a player's clay-minus-hard deviation between the periods; "stable size" is the square root of that covariance divided by the same for the player's all-surface level (the earlier study's last column).

| Men, clay − hard | Side | Persists (r) | Raw r | Stable size ÷ player level | Raw |
|---|---|---|---|---|---|
| Return points won | return | 0.49 | 0.44 | 0.91 | 1.12 |
| Breaks | return | 0.45 | 0.41 | 0.93 | 1.12 |
| Return against the first serve | return | 0.40 | 0.36 | 0.90 | 1.16 |
| Return against the second serve | return | 0.36 | 0.26 | 0.88 | 0.90 |
| Ace suppression | return | 0.25 | 0.32 | 0.64 | 0.71 |
| Serve points won | serve | 0.45 | 0.36 | 0.67 | 0.74 |
| Holds | serve | 0.41 | 0.33 | 0.67 | 0.75 |
| First-serve points won | serve | 0.29 | 0.24 | 0.51 | 0.48 |
| Aces | serve | 0.24 | 0.21 | 0.38 | 0.32 |

* **The suggestion's core claim holds, more strongly than it said.** Over three-year periods a man's clay return deviation correlates 0.40–0.49 with the next period's, and its stable part is about as large as the stable differences between players' return levels.
* **Opponent adjustment does not shrink it.** The adjusted deviations persist about as well as the raw ones (return points won 0.49 against 0.44; ace suppression 0.25 against 0.32). The comparison is not clean enough to say that adjustment sharpens them (the audit's point): the adjusted values are ridge-shrunk, the raw ones are plain averages, and shrinkage changes correlations.
* **"Serve stats barely deviate" is only half right.** Aces and first serves in deviate little, but serve points won and holds deviate on clay at two-thirds of the player spread, and persist as well as the return side.
* **Grass is too thin to judge** (r −0.04 to 0.28 on about 136 men); the women's tables are noisier (about 150 women qualify) and point the same way on clay for the return side (return points won r 0.28, ratio 0.77).

### 3.4 Both sides carry surface signal (observed; `tuning_summary.csv`, variant `return_only`)

Added after 3.1 and 3.3: the same tuning with the serve-side deviations switched off (E held at zero) and the return side at 3, 10 or 30 times κ. How much of the shared model's gain the return side alone keeps, at its best penalty:

| Statistic | Men: shared → return only | Kept | Women: shared → return only | Kept |
|---|---|---|---|---|
| Holds / breaks | +0.45 → +0.27 | 60% | +0.22 → +0.10 | 46% |
| Serve / return points won | +0.10 → +0.06 | 56% | +0.05 → +0.03 | 62% |
| Second-serve points won | +0.05 → +0.03 | 58% | +0.02 → +0.01 | 40% |
| First-serve points won | +0.12 → +0.06 | 48% | +0.07 → +0.05 | 68% |
| Aces | +0.10 → +0.04 | 40% | +0.06 → +0.03 | 47% |
| Break points saved | +0.03 → +0.01 | 35% | +0.02 → +0.01 | 42% |
| Double faults | +0.04 → +0.01 | 21% | +0.03 → +0.01 | 15% |
| First serves in | +0.08 → +0.01 | 10% | +0.06 → −0.00 | 0% |

* **The return side carries about half of the surface signal in the two-sided statistics** (points, games, return against each serve, aces) and almost none in the serve-only ones (first serves in, double faults). The shared penalty wins for all 16 tour × statistic pairs, so the chosen settings keep both sides.
* *Inferred.* "Prioritise the return side" is right in relative terms (section 3.3: the return deviations are the larger relative to the spread between players) but wrong as an exclusion: dropping the serve side gives up 40–60% of the forecastable surface signal even in points won and holds.

### 3.5 The chosen settings (`tuning_choice.json`)

Today's half-life for every statistic; one penalty shared by the serve and return deviations, at 10× κ (men: aces, double faults, first serves in, serve points won, break points saved; women: all but aces and serve points won) or 30× κ (men: first-serve and second-serve points won, holds; women: aces, serve points won). No statistic falls back to today's pooled values.

### 3.6 Out of sample, the gains hold (observed; `oos_scores.csv`)

The chosen settings run over the whole history; each forecasts the statistic in every evaluation-level box-score match after the tuning years. Gain over today's IOS, milli-log-loss per unit (higher is better), 2019–2026, all levels; the main tour alone in brackets:

| Statistic | Men | Men: grass | Women | Women: grass |
|---|---|---|---|---|
| Holds | +0.40 [+0.34, +0.46] (main tour +0.60) | +0.88 | +0.39 [+0.28, +0.51] (+0.31) | +0.47 |
| First-serve points won | +0.11 [+0.09, +0.13] (+0.15) | +0.29 | +0.08 [+0.06, +0.11] (+0.07) | +0.18 |
| Aces | +0.12 [+0.09, +0.15] (+0.14) | +0.43 | +0.07 [+0.05, +0.09] (+0.07) | +0.22 |
| First serves in | +0.09 [+0.08, +0.11] (+0.09) | +0.24 | +0.09 [+0.07, +0.11] (+0.08) | +0.24 |
| Serve points won | +0.08 [+0.06, +0.10] (+0.14) | +0.23 | +0.07 [+0.06, +0.09] (+0.07) | +0.16 |
| Second-serve points won | +0.05 [+0.04, +0.06] (+0.09) | +0.07 | +0.03 [+0.02, +0.05] (+0.03) | +0.07 |
| Double faults | +0.03 [+0.02, +0.05] (+0.02) | +0.18 | +0.04 [+0.01, +0.06] (+0.03) | +0.18 |
| Break points saved | +0.03 [+0.01, +0.05] (+0.05) | −0.02 | +0.03 [+0.02, +0.05] (+0.03) | +0.05 |

The 2022–2026 seasons alone give the same picture (`oos_scores.csv`). These are statistics, not results: no match outcome of 2019–2026 enters the choice of anything here.

### 3.7 How much the inputs move, and whether the price already has them (observed; `diagnostics_*.csv`)

**Movement.** On the model's rows (main tour with odds), the surface-specific versions of the 21 IOS inputs correlate 0.87–0.99 with today's on men's clay and grass (lowest for the return side of double faults, 0.87–0.89, and first serves in, 0.93–0.94), and 0.95–0.998 on hard courts. The change is 14–60% of the input's own SD on men's clay and grass (10–33% on hard). For comparison, the leak-proof rebuild moved the same inputs by 0.2–0.3% of an SD.

**Priced? (linear, 2013–2018 only; 2019–2021 kept untouched for the validation phase.)** Logistic fits of the result on the closing price's log-odds plus a block of surface inputs, per tour, fitted on 2013–2016 and scored on 2017–2018 (the men's 2018 season has no odds, so the men's score is 2017 alone). Gain over the price alone, positive = the block helps:

| Block | Men | Women |
|---|---|---|
| 4 return deviations | +0.01 [−0.37, +0.39] tie | −0.31 [−0.79, +0.16] tie |
| 16 deviations | −0.01 [−1.75, +1.73] tie | −0.55 [−1.49, +0.40] tie |
| The 21 inputs' change | −0.84 [−2.33, +0.66] tie | −2.53 [−3.99, −1.06] worse |

The in-sample fits (in `diagnostics_priced.csv`) are not evidence: their gains, +0.62 to +0.87 for the 16- and 21-input blocks, equal what that many free coefficients buy by chance (the audit computes 0.54–0.81), and their largest z's (3.7, 3.1) come in opposite-signed pairs of correlated deviations. The women's −2.53 is partly a data gap: women's hold box scores are absent before 2015, so the hold inputs are about zero in 2013–2014 and the fitted weights do not carry over. The audit's own check with annual expanding refits (outcomes 2015–2018 only; closing price plus the net surface shift in serve points won and holds) gives +0.03 [−0.25, +0.32] (men) and +0.07 [−0.66, +0.79] (women), ties, and slightly negative with today's 21 IOS inputs as controls.

*Inferred.* Linearly, the closing price already has the surface information. This repeats the market-anchoring study's finding for raw surface statistics. Whether TabPFN extracts something non-linear (for instance early in a surface season, where the market is weakest) is what the test is for; the prior is a small effect.

### 3.8 Leak and mapping checks (observed)

* **Real-data leak probe** (`probe.json`): the match-timing study's probe on the surface IOS (2023–2024 slice, every level, its four cut days where events overlap; spw, hold and first-serve points won at a strong and a weak surface penalty). Every match that surely started after the cut had its result reversed. **PASS:** no effective rating or surface deviation of any of the 13,758–31,163 matches that surely finished by the cut moved (largest difference 0).
* **Mapping** (`arms/checks.json`): today's 21 IOS inputs rebuilt from this study's pooled runs equal the base frame's to within 5 × 10⁻¹⁵ (summation order).
* **The base frame** reproduces the leak-proof refit's upload exactly; the local pipeline reproduces another session's local fit on the same rows to 6 × 10⁻⁸.

## 4. Strategy: how to give it to the model (proposal, for the audit)

What the evidence says the representation must respect:

1. **Shrunk surface values, not raw surface-only ratings** (3.1: the lightest penalty is worse than pooling).
2. **Today's memory** (3.2).
3. **Both sides** (3.4), with the return side the larger relative to the spread between players (3.3).
4. **Clay and grass are where it matters** (3.1); TabPFN already sees the surface, the level and surface familiarity (`surface_first`) as context, so it can learn where the surface values matter.

Two candidate representations, each a single change to the best model's inputs:

| Arm | Inputs | What it tests |
|---|---|---|
| `base` | Today's 54 inputs (odds + 53; the leak-proof IOS) | The reference |
| `sprof` (R1, surface profile) | The same 54 columns; the 21 IOS profile inputs (iosO, iosD, prod on seven statistics) computed from each player's surface-specific ratings on the match's surface, O + E_s and D + F_s, at the chosen settings. The matchup products become surface matchups (A's clay serve against B's clay return and the reverse). The short-memory points matchup is unchanged | The suggestion taken literally: the profile TabPFN leans on most, built per surface. No extra columns |
| `sdev` (R2, surface deviations) | Today's 54 inputs unchanged, plus 8 columns: A − B of the serve-side (E) and return-side (F) deviations on the match's surface for the four statistics the suggestion prioritised: return points won (spw), breaks (hold), return against the first serve (first_won), aces | The surface signal kept separate, so TabPFN can weigh it on its own (with surface familiarity, level, surface); and return points won, absent from today's profile, enters through spw |

Not proposed, and why:

* **Surface-only ratings with no pooling**: worse than pooled for every statistic (3.1, the 1× penalty and below).
* **A longer memory or a two-timescale model**: at most +0.01 milli per unit (3.2).
* **Return-only deviations**: lose 40–60% of the signal in the two-sided statistics (3.4).
* **All 16 deviation columns**: the serve-only statistics' deviations are small; 16 weak columns risk diluting TabPFN's attention; R1 already carries all of them.
* **Surface Elo's specialisation term**: tested before; priced by the market (market-anchoring study, 6.1).

## 5. Test protocol (proposal, locked after the audit)

* **Model.** Local TabPFN-3.5 (open checkpoint `tabpfn-v3.5-20260909`, the same date stamp as the API's 3.5) on this machine's GPU, with the paid fits' settings except thinking: 8 estimators, softmax temperature 0.9, pretraining limits ignored, no categorical hints. **Not the API's "3.5 Plus".** On 6 Oct 2026 another session relayed the owner's concern about API costs, and that the free offline model could be used instead. No rule was recorded; this study left paid calls for the owner to approve and made none. Whether the local open model equals the hosted Plus model is unknown. *(Wording corrected after the study: an earlier version called the relay an instruction to avoid paid calls, which overstated it.)*
* **Rows.** Main-tour singles with closing odds, both tours pooled with a tour column (the best model's population). Each window trains on every season from 2013 to the one before the test season (the men's 2018 season has no odds) and tests on one season, each match queried in both orientations and averaged.
* **Seeds.** Four per arm and window (0–3); an arm's forecast is the mean of its four seeds' probabilities.
* **Phases.**
  1. *Validation, 2019–2021* (three windows), to choose the primary arm before any 2022–2026 result of a surface arm is seen: the primary is the arm with the larger pooled gain over `base` (both tours); if neither is ahead, R1.
  2. *Test, 2022–2026* (the owner's five windows): every arm, four seeds.
* **Primary endpoint.** Both tours, pooled over 2022–2026: log loss of `base` minus log loss of the primary arm, milli-log-loss per match (positive = the surface arm is better), with a paired 95% interval clustered in four-week blocks. **Better** if the interval is above zero, **worse** if below, otherwise a **tie**.
* **Secondary, reported in full.** Each tour; each season; the other arm; each arm against the closing price recalibrated on its window's training matches; pre-declared subgroups (`subgroups.py`): surface (hard, clay, grass) and early in the surface season (either player has fewer than three earlier matches on the surface that year).
* **Noise yardstick.** The base arm's seed-against-seed differences (already measured: single seeds differ by about 0.1 milli-log-loss pooled over 2022–2026, at most ±0.15); four-seed averages halve that.
* **Power.** Near-identical forecasts give paired intervals about ±0.2–0.4 milli-log-loss wide pooled over 2022–2026; an effect smaller than that will read as a tie. A tie would mean the surface terms add less than that through TabPFN given the closing odds, not that surface information is useless (3.1 shows it forecasts the statistics) or that the market cannot be beaten.

## 6. Validation phase, 2019–2021 (observed; run after section 5 was written, before the audit's verdict; `primary.json`, `results.csv`)

Local TabPFN-3.5, four seeds per arm and window. Gain over `base`, milli-log-loss per match (positive = the surface arm has the lower log loss):

| Arm | Both tours | Men | Women | 2019 / 2020 / 2021, both tours |
|---|---|---|---|---|
| R1 `sprof` | **+0.21 [+0.00, +0.41]** | +0.26 [−0.08, +0.61] tie | +0.15 [−0.04, +0.33] tie | +0.32 / +0.16 / +0.11 |
| R2 `sdev` | +0.11 [−0.11, +0.33] tie | +0.15 [−0.18, +0.49] tie | +0.05 [−0.24, +0.34] tie | +0.30 / −0.19 / +0.05 |

* **By the rule of section 5 the primary arm is R1 (`sprof`).** It is ahead of `base` in every validation season and its pooled interval just clears zero; R2 is a tie.
* Pre-declared subgroups, both tours, R1: early in the surface season +0.50 [+0.07, +0.92] against +0.11 [−0.06, +0.28] later; grass +0.82 [−0.17, +1.80], clay −0.07 [−0.40, +0.27], hard +0.24 [+0.02, +0.45]. R2 on grass +0.80 [+0.25, +1.34]. Several subgroups were looked at, so these are directions, not findings.
* Against the closing price recalibrated per window (positive = better than the price), both tours: `base` +0.71 [−0.51, +1.93], R1 +0.92 [−0.27, +2.10], R2 +0.82 [−0.35, +1.98]; all ties.
* Run-to-run noise: one seed against another moves an arm's pooled 2019–2021 result by −0.17 to +0.18; four-seed averages halve that.

These are the raw (not recalibrated) comparisons of section 5's first protocol; section 7 replaces them as the basis of the choice.

## 7. The audit, and the plan as locked

An independent agent (Claude Opus 5.5, read-only, blind to every validation result of a surface arm) audited sections 1–5 and the code; its review is kept verbatim in [audit.md](audit.md). Its verdict: the construction is correct and leak-proof (no bug in the solver, the incremental step or the arms' mapping), the statistic-forecast evidence is solid, but the match-level test was not ready.

### 7.1 What it found, and what I decided

| Audit item | Verified? | Decision |
|---|---|---|
| **The local reference model is over-confident.** One slope per tour on its log-odds (men 0.886, women 0.964), fitted on its 2019–2021 forecasts, lifts it on 2022–2026 from +0.53 [−0.35, +1.42] to +1.20 [+0.51, +1.89] over the recalibrated closing price (both tours), level with the paid thinking fit. An arm whose change moves with the favourite could gain or lose through calibration, not information | **Yes**, reproduced exactly (men +0.85 → +1.60 [+0.84, +2.36]) | **Accepted.** Every forecast is recalibrated per tour on its own 2019–2021 forecasts (cross-fitted by season inside 2019–2021); the recalibrated comparison is primary, the raw one secondary |
| **The interval leaves out the seeds' variance** (a single seed's pooled log loss varies with SD 0.068 milli over 2022–2026; a systematic shift a block interval cannot see) | **Yes** (0.068) | **Accepted.** Arm-against-arm intervals add (s²_arm + s²_base)/4 to the block variance; the verdict uses the wider interval |
| **Power must be stated before the test** | — | **Accepted** (7.3) |
| **The choice rule was undefined if neither arm was ahead** | — | **Accepted**: largest recalibrated, cross-fitted gain; R1 if none is ahead |
| **The run cache did not record its constants** | Yes | **Fixed**: each run's constants are stored beside it and checked before re-use |
| **Only out-of-sample "priced" rows are evidence**; women's 2013–2014 hold gap | Yes | **Fixed** in 3.7 |
| **R2 mixes two models** (deviations from the surface model's own level beside today's levels; misses the level correction) | Yes (the deviations explain 71–90% of the change) | **Kept** as a secondary arm, its flaw noted |
| **P1: one column, the net surface shift** in A's serve-and-return point advantage, with a **placebo** (the same column permuted within tour × surface × season) | — | **Accepted** as a third candidate (`snet1`) and a control arm (`snet1_perm`) |
| **A linear residual check** (recalibrated base plus the net shift, fitted on 2019–2021) | — | **Accepted** as secondary (`residual_check.json`) |
| **A split 2022–2024 / 2025–2026** (lower-level box scores more than double in 2025) | Yes | **Accepted** as secondary |
| **Wording**: 3.2 overstated, 3.3's adjustment claim, "clay and grass" | Yes | **Fixed** |
| Tuning extensions on 2013–2018: a 100× penalty (30× is best for 5 of 16), a penalty per surface, serve-only deviations for double faults and first serves in, a long-memory deviation | Partly | **Deferred to follow-ups** (7.4). Each would move the statistic forecasts by a few hundredths of a milli per unit; through TabPFN that is far below what this test can detect (7.3), so they cannot change its verdict |
| Indoor hard as a surface; the men's 2018 odds; eight seeds | — | Deferred |

### 7.2 Validation under the locked protocol (observed; `results.csv`, `primary.json`)

Recalibrated forecasts, cross-fitted by season; gain over `base`, pooled 2019–2021, both tours; 95% intervals with the seeds' variance:

| Arm | Gain | Interval | Verdict |
|---|---|---|---|
| R1 `sprof` | +0.15 | [−0.08, +0.38] | tie |
| P1 `snet1` | +0.10 | [−0.05, +0.25] | tie |
| P1's placebo `snet1_perm` | +0.06 | [−0.09, +0.21] | tie |
| R2 `sdev` | +0.03 | [−0.21, +0.27] | tie |

* **The primary arm is R1 (`sprof`)**, by the rule (the largest gain).
* P1 is barely ahead of its own placebo (+0.04): most of its gain is what adding any column does.
* All four are ties in validation; recalibration removed about 30% of R1's raw gain (+0.21 raw → +0.15).

### 7.3 Power (pre-registered; `primary.json`)

R1 moves forecasts little: on 2019–2021 its recalibrated log-odds differ from the base's by SD 0.022, 0.34 percentage points of probability on average. Scaled to the 23,819 test matches, the paired SE is 0.066 from the matches and 0.064 from the seeds, 0.092 in all. **The test detects an effect of about +0.26 milli-log-loss with 80% power.** The validation estimate (+0.15) is below that, so **a tie is the expected outcome**; it would mean R1 adds less than about a quarter of a milli-log-loss through local TabPFN-3.5 given the closing odds. It would not mean that surface information is useless (3.1, 3.6), that the paid model would agree, or that the market cannot be beaten.

### 7.4 The locked plan

* **Arms** (`plan.py`): `base`; R1 `sprof` (primary); R2 `sdev`, P1 `snet1` and the placebo `snet1_perm` (secondary). Four seeds each, test seasons 2022–2026, expanding windows from 2013.
* **Primary endpoint**: R1 against `base`, both tours pooled over 2022–2026, recalibrated forecasts (each arm's slope per tour fitted on its 2019–2021 forecasts), 95% interval with the seeds' variance. Better / worse / tie by the interval.
* **Secondary, all reported**: men and women; each season; 2022–2024 and 2025–2026; raw forecasts; each arm against the recalibrated closing price; the other arms against `base`; the pre-declared subgroups (surface; early in the surface season); the linear residual check.
* **If the primary is a tie**, the pre-registered next steps are, in order:
  1. the early-season subgroup as the lead (the market is weakest there, and validation pointed that way);
  2. a stronger surface signal: a long-memory deviation (the audit's tension), a penalty per surface and serve-only deviations for the serve-only statistics, all tuned on 2013–2018;
  3. a price the bettor can actually take: Polymarket's price hours before the start rather than the close (the market-anchoring study's suggestion 3);
  4. one paid TabPFN-3.5-Thinking fit of R1, only if the owner approves it.

Locked on 6 Oct 2026 before any 2022–2026 result of a surface arm was scored (`plan.py` hash recorded in `uploads/manifest.json`).

**Outcome** (added after the test; [README.md](README.md)): the primary comparison is a tie, +0.01 [−0.10, +0.13] milli-log-loss (R1 against base, both tours, 2022–2026), and every secondary arm and subgroup ties as well.

## 8. Without the odds (pre-declared 6 Oct 2026, after the test above, before any of these fits ran)

The owner's question after the result: if the odds were not in the model, would the surface profile add to it?

* **Arms.**
  * `base_noodds`: today's 53 sporting inputs, without the closing odds' column.
  * `sprof_noodds`: the same 53 inputs, with the 21 IOS profile inputs per surface (R1, the representation chosen before the test).
* **Design.** Everything else as in 7.4:
  * the same matches and expanding windows, four seeds;
  * each arm recalibrated per tour on its own 2019–2021 forecasts, cross-fitted by season inside 2019–2021;
  * intervals with the seeds' variance.
* **Primary.** `sprof_noodds` against `base_noodds`, both tours, 2022–2026; better, worse or tie by the interval.
* **Secondary.** Each tour, each season, 2019–2021, raw forecasts, and each arm against the recalibrated closing price, which shows how far below the market a model without odds sits.

**Outcome** ([README.md](README.md)):

* The primary comparison is a **tie**: +0.27 [−0.03, +0.58], both tours, 2022–2026.
* That tie pools a clear gain for men, **+0.83 [+0.39, +1.27]** (also +0.98 [+0.42, +1.54] in 2019–2021), with nothing for women, −0.33 [−0.84, +0.18].

## 9. One model or one per court type? (pre-declared 6 Oct 2026, after the owner's decision, before any of these fits ran)

The owner's question: does the model need to be split by court type, or does one model distinguish surfaces properly?

* **Arms.**
  * `sprof`: the decided model, R1 with the odds; one model for all surfaces, with surface as an input.
  * `sprof_bysurf`: the same inputs as three models: hard with the 54 carpet matches, clay, and grass. Each is trained only on its surface's matches and predicts only that surface's matches.
* **Data per surface.** Before 2022 the model's rows hold 24,061 hard (plus 54 carpet), 11,380 clay and 4,423 grass matches.
* **Design.** As in 7.4: expanding windows, four seeds, recalibration per tour on 2019–2021, intervals with the seeds' variance.
* **Primary.** `sprof_bysurf` against `sprof`, both tours, 2022–2026. **Secondary**: each surface, especially grass, and each tour.

**Outcome** ([README.md](README.md)):

* The primary comparison is a **tie leaning worse**: −0.28 [−0.77, +0.21] (positive = separate models better).
* Separate models are worse in women's grass matches (−3.58 [−7.02, −0.14]) and nearly worse early in the surface season (−1.26 [−2.53, +0.01]).
* They are also about twice as noisy from seed to seed.
* One pooled model with surface as an input distinguishes court types at least as well as separate models.
