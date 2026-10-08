# R2 audit, rulings and R3 build spec (agent 4, auditor and red team)

7 October 2026. I read the brief, `team.md`, `CLAUDE.md`, the three R1 proposals, their scripts and outputs.

* **Labels.** **Observed** means recomputed or re-read on disk here; each carries its script. *Inferred* is reasoning. **Ruling** is binding under `team.md`; **suggestion** is not.
* **Scripts** are in `src/eda/serve_speed_tabpfn/design/auditor_*.py`; outputs `auditor_*.json` / `.log` sit in this folder.
  * `auditor_lib.py` is an independent, vectorised re-implementation of the panel choice, the as-of offsets and the modeller's filter.
  * It reproduces the modeller's f̂ to 3.4e-5 km/h on all 4,596 of his 2023 targets.
* **No match result was read.** Statistic targets were used on ≤ 2023 only; 2024–26 was looked at as values and counts only; no price was used (§(e)).
* **Score directions.** Every MSE difference "X − Y" is positive when Y is better. Every pp/SD coefficient is positive when a player serving faster than his norm serves better. "Tie" means the 95% interval spans 0.

## 0. The rulings in ten lines

1. **Centring (Q1): as-of edition offsets (the engineer).** The history is re-centred at each target's `es` and the filter is re-run per target over its last 364 days.
   * On a target that cannot reward carried edition artefacts (the within-match A − B speed difference), as-of beats frozen. Men 2023: +4.47 km/h² [+2.19, +6.75].
   * f̂'s own contribution ties between the two.
2. **Basis (Q2): key statistic first at tour level (the modeller).** Points are used at the Slams, with KS − 0.5 and AO match centre + 0.5. This keeps the history basis mix the same in training and test rows.
3. **Statistic (Q3): f̂ is the primary.** With the modeller's frozen constants, it carries the gate's information: in joint fits with edition fixed effects the registered window adds nothing. The modeller's R² and "oracle" evidence is biased, and his §5 calibration table omits a stratum.
4. **Missing values (Q4): 0, never NaN, and no reliability input.**
5. **Women (Q4): 0 in the primary arm A1. Their values go in A3,** which is A1 plus women's Slam values.
6. **Primary endpoint (Q5): P2 alone.** It is A1's calibrated paired mLL gain over the base, men 2024–26, with block and seed variance. The strategist's P1 becomes the key secondary S0, not a gate.
7. **Arms:** A1 `spd`, A2 `spd_raw` (registered x_raw, new panel), A3 `spd_all` (women included) and A1's no-odds twin.
   * Seeds and the fit count follow the strategist, plus 2 reproduction fits: **222 fits, about 2.1 h.**
   * Every comparison uses identical seed sets, and every calibration uses seeds 0–3.
8. **Two leak probes before any fit:** an order cut on own history and a day cut on the clock. Both have leaky controls (§(c) C7).
9. **Upstream defects** (QF→qualifying label, 88 women's 2026 id conflicts, no men's 2018, the AO 2026 hole) are handled in the build. No other study's file is edited (Q6).
10. **Contested:** centring (modeller), basis (engineer), women in A1 (engineer, modeller), the P1 → P2 sequence and the choice of A3 (strategist). The default is that these rulings stand.

## (a) Errors found

### Engineer (`1_engineer.md`)

| # | Claim or step | What is on disk (observed) | Severity |
|---|---|---|---|
| E1 | "14.7% of men's 2025–26 Slam A − B values move > 3 km/h" is offered as the effect of centring | It compares **raw (no offsets at all) with as-of** on the x_raw window (`engineer_asof.json`), not the choice in dispute. For the dispute (frozen-offset f̂ against as-of f̂, A − B): corr 0.961–0.986 in 2024–26; > 1 SD (2.22 km/h): 0.05–0.23% non-Slam, 0.3–1.4% Slam; > 0.5 SD: 3.8–5.6% / 6.0–9.5% (`auditor_centring.json` part3) | Framing; the number itself checks out |
| E2 | "The test seasons hold measuring-system breaks no frozen constant can know: … USO 2025→26 +9.7" | The model frame ends with events that started by **28 Jul 2026**, so USO 2026 reaches no test match. W 2024→25 +8.48 (52 men) and AO 2023→24 +3.49 (88) do (`engineer_misc.json`, verified). The brief's "2026 (to early Oct)" is also off | Factual |
| E3 | Id conflicts: "67 women's 2026 frame matches carry other player ids" | Also **21 frame matches with A and B flipped** in the rebuild (`engineer_clock.json`: `frame_sides_flipped_in_rebuilt` 21; I count 88 = 67 + 21). Orientation must come from the frame's own player ids | Omission |
| E4 | `engineer_asof.py` frozen-offset dict | Women's tour qualifying gets men's values (`wta|tour_Q|ks` = 5.669). No WTA tour speeds exist, so it is inconsequential | Scratch bug |
| E5 | Snapshot constant "s = 12.3 (men) / 9.8 (women)" | The code uses 12.4 for both | Trivial |
| E6 | Point-mean-first panel | Non-Slam sides' 28-day history is points-only 51/49/47% in 2022–24, then 28/17% in 2025–26. Key-statistic-only goes 4/3/3% → 35/55%. So training and test rows are built on different bases (`auditor_basis.json`) | Design (ruled against, Q2) |
| E7 | Family priors pool Challengers with tour events | Challengers read about +2 km/h relative to tour main draws (modeller offsets `ks_ch` +1.3 to +2.9). Until an edition is released, its prior is off by that much. Fix in C2 | Minor |

### Modeller (`1_modeller.md`)

| # | Claim | What is on disk | Severity |
|---|---|---|---|
| M1 | "Edition centring did not help, even as an oracle (R² 0.040 vs 0.051)" | Three flaws, so it is not evidence against centring (`modeller_extras.py`, lines 132–158). On a clean target (Q1) as-of centring wins | **Material** |
| M2 | §5: "calibration slopes stay flat across window strata for f̂" (1 / 2 / ≥ 3: 0.80 / 0.69 / 0.85) | The same output holds k2 = 0: **slope 0.31** over 1,149 rows (`modeller_extras.json` C; `modeller_state3_ks_first.json`). It was left out of the table that supports "no reliability input". It reappears as risk 4 | Selective reporting |
| M3 | Panel coverage | The modeller's panel has **no AO 2026 rows** (men 0, women 0; the engineer has 474 + 474), because the AO match centre is not read (`auditor_checks.json`). This is why his women's 2026 x_raw coverage is 138 against the engineer's 213 | Material for 2026 |
| M4 | Frozen system offsets | Unstable between ≤ 2022 and ≤ 2023 fits. Slam qualifying is put in the main draw's system (`auditor_checks.json`) | Design (Q1) |
| M5 | Women: "the men's h, s2f, q; ν_pm 14, ν_ks 10, c 4" | The women's c and ν were tuned jointly with h = 90. The mix was never re-tuned at h = 14. On T1 it is within 0.3 km/h² of the women's grid optimum, so it is acceptable for A3 | Minor |
| M6 | "A speed change … persists across events" (gate verdict) | Holds for men, with edition FE: first-serve points won from earlier events only +0.32 pp/SD [+0.09, +0.55]. **Not shown for women:** their earlier-events-only rows tie (+0.25 [−0.42, +0.91]); the women's signal is within one Slam | Over-reach for women |
| M7 | Tuning target | The one-step MSE of the next match's system-centred speed rewards carrying edition effects. The constants survive anyway (Q3) | Minor in effect |

The three flaws in M1's oracle:
1. **The target is left uncentred.** History is centred, but the target deviation d = z − c52 still holds the target edition's effect. The uncentred f̂ "predicts" that effect whenever the history holds earlier rounds of the same edition.
2. **The target's own residual is in the oracle.** The edition shift is the mean residual of *all* the edition's matches, the target's included.
3. **Editions are tournament ids,** which pool qualifying with the main draw.

The offset instability in M4, ≤ 2022 → ≤ 2023 fits (km/h):

| System | ≤ 2022 | ≤ 2023 |
|---|---:|---:|
| RG | −6.82 | −4.61 |
| W | −4.22 | −2.46 |
| AO | −4.64 | −5.39 |
| `ks_ch` | +2.90 | +1.31 |

### Strategist (`1_strategist.md`)

| # | Claim | What is on disk | Severity |
|---|---|---|---|
| S1 | P1 (information) gates P2 (gain) in a fixed sequence | The owner asked "by how much". P2 alone has at least the sequence's power: β 0.077, capture 0.5 gives 0.342 alone vs 0.334 in sequence (`strategist_power*.csv`). It needs no multiplicity cost, and the gate could demote a real gain. P1 is a diagnostic | Design (Q5) |
| S2 | "Reused base fits: their stored fingerprints are rechecked for seasons ≤ 2024" | **The race's fits (seeds 0–2) store no fingerprint;** `meta` has none (checked `model__2024__seed1`, `model__2025__seed0`, `model__2026__seed2`). Only the feature-interactions fits (seeds 3–15) have one. Determinism was shown only for 2019. Fix: reproduction fits (C5) | Material |
| S3 | P2's seed term in the power simulation is analytic, 2/K·p(1−p)·σ²/n | The project convention (`surface_ios/score.py` `seed_var`) is **empirical**: the spread of single-seed mean log losses. In simulation the analytic term double-counts i.i.d. seed noise that the block SE already holds (null 0.15% one-sided vs 2.5%), so the power figures are conservative | Minor |
| S4 | Capture = slope of η_A1 − η_B on 0.090·z | It mixes the published x_raw β (per SD of x_raw) with the new column's scale. Redefined in C6 (S10) | Minor |
| S5 | `spd_chg` NaN when neither side has a timed match within 14 days | Decayed states still carry information. On T1 (men 2023, as-of) the both-k14 = 0 stratum has slope 0.68 (261 matches, SD 0.83 km/h). NaN discards it (Q4) | Design |
| S6 | "player_a is unchanged by the rebuild on all 50,116 speed ids ≤ 2024" | True, but 21 women's 2026 frame matches are flipped (E3) | Omission |

**Also checked and correct:** GPU times (15–47 s per fit; 220 fits ≈ 2.05 h), seed noise (0.019 log-odds; 4- vs 16-seed slope 0.9992), the 2019 determinism, the 7,068 men's test matches (2 debut) and the early-price coverage (men 232 + 1,210).

## (b) Rulings

### Q1. Centring: **as-of edition offsets.**

**The test** (`auditor_centring.py` part 1). For a match with both players timed:
* the target is T = y_A − y_B. The target edition's offset cancels exactly, because both serve in the same match;
* the forecast is Δ(L̂ + f̂), built from each player's own rows in the 364 days before `es`;
* three centrings are compared, all on the same ks-first panel:
  * raw;
  * frozen: the modeller's offsets, ≤ 2022 for men and ≤ 2019 for women;
  * as-of: the engineer's model, re-implemented and refitted at each target's `es` on rows with lf + 1 ≤ es;
* tune on men 2019–22 (2,870 matches) and women Slams 2016–20 (1,152); evaluate on men 2023 (2,129) and women 2021–23 (1,035);
* intervals are four-week-block bootstraps.

**The results.** Gains are in km/h², with the modeller's constants. "Change part" means MSE(level only) − MSE(level + f̂): how much f̂ adds within its own centring.

| | Men 2023 | Women 2021–23 |
|---|---|---|
| frozen − as-of, full forecast | **+4.47 [+2.19, +6.75]**: as-of better | +1.06 [−0.04, +2.11]: tie |
| raw − frozen | −0.30 [−2.58, +1.89]: tie | +1.03 [+0.24, +1.98]: frozen better |
| Change part, frozen | +5.02 [+1.04, +8.79] | +1.46 [+0.62, +2.41] |
| Change part, as-of | +4.93 [+1.27, +8.38] | +0.92 [+0.17, +1.79] |
| frozen − as-of, Huber (k 10) / trimmed MSE | +1.06 [+0.49, +1.57] / +2.45 [+0.92, +3.83]: as-of better | |

* The men's gain holds in every situation:
  * both players' history includes the target event: +3.42 [+1.49, +5.74];
  * neither does: +5.53 [+1.19, +10.39];
  * exactly one does: +4.60 [+2.31, +6.31].

**Reasons for the ruling.**
1. **On the clean target, as-of is better or tied, never worse.** Its gain sits mostly in the level. f̂'s own contribution is the same under both centrings (men +5.0 vs +4.9). The modeller's opposite result comes from the biased target (M1).
2. **Frozen offsets are unstable and blind to breaks.**
   * They move by 1.7–2.2 km/h between ≤ 2022 and ≤ 2023 fits (M4), and they cannot see a break such as W 2025 (+8.5 km/h, same men).
   * In 2024–26 values, sides whose latest row is at a Slam with a break carry a relative artefact at the next tour events. Mean f̂, those sides minus the rest (part 3):

     | Slam (sides) | Frozen | As-of |
     |---|---:|---:|
     | W 2024 (38) | −1.42 | −0.42 |
     | USO 2025 | −1.09 | −0.19 |
     | W 2025 | +0.50 | −0.24 |
     | AO 2024 | −0.35 | −0.58 (the one case as-of is worse) |

   * Frozen offsets also give Slam qualifying the main draw's offset (M4).
3. **It is leak-proof by construction.**
   * γ̂(D) uses only rows with lf + 1 ≤ D and obs ≥ D − 364, and a target reads D = `es`. Its own match has lf ≥ es, so it is excluded.
   * Probe B in C7 tests this with a leaky control.
4. **It is cheap.** My vectorised version builds every 2014–26 frame side in seconds.

**The values-only stakes are modest.** Frozen and as-of A − B f̂ correlate 0.96–0.99 in 2024–26 (E1). So the ruling buys robustness rather than a large change in the test column.

**How it interacts with the Kalman filter** (binding, C3):
* **History is re-centred per target, not per row.** Each target's history is centred with the single snapshot γ̂(es_t), and the filter is re-run for that target. No sequential state is shared across targets.
  * A shift common to all history rows is absorbed by the diffuse level, so f̂ does not depend on the snapshot's reference rule.
* **History is truncated to [es_t − 364, es_t).** Every history edition then sits inside the snapshot window. This removes the engineer's family-mean fallback for old editions, which a family with a break would misplace.
  * The cost is small: the level's effective memory is about 100 days. My T1 run uses this truncation.
* **A player's own rows enter his editions' γ̂.** About 1/12 of a 28-draw event's rows can be one player's, which attenuates his f̂ slightly.
  * The gate shows no loss: first-serve points won with edition FE, frozen +0.34 [+0.20, +0.47] vs as-of +0.33 [+0.20, +0.46].
* **Calibration by recency stratum is about the same** under both centrings (T1 men, slopes 0.87 / 0.97 / 0.68 as-of against 0.89 / 0.78 / 0.78 frozen).

### Q2. Basis: **key statistic first at tour level; point means at the Slams.**

TabPFN learns the feature's relation from training rows (2013..Y−1) and is scored on Y. What matters is that the column means the same thing in both.

**Under ks-first the basis mix is stable.** Key-statistic-only histories for non-Slam sides:

| Policy | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|
| ks-first | 55% | 60% | 69% | 52% | 55% |
| pm-first | 4% | 3% | 3% | 35% | 55% |

Under pm-first the training rows are point-based and the 2025–26 test rows mostly key-statistic-based. Only 2024 would be a consistent pm-first test season.

**The engineer's case is real but does not decide it.**
* Point histories forecast a point-mean target better: +5.86 km/h² [+0.25, +14.47] over 1,136 matches in 2021–23 (`auditor_basis.json`).
* On the basis-neutral gate target the information is about equal: the modeller's first-serve points won is +0.34 (ks-first) against +0.36 (pm-first).
* The two give A − B values that correlate 0.91–0.96 in 2022–24 and ≥ 0.98 in 2025–26.

**The key-statistic tail is real and it is not side swaps.**
* In 2023, 7.5% of men's tour matches have both key statistics more than 10 km/h from the Infosys points in either orientation (4.0–4.2% in 2022 and 2024). About 1% look like swaps (`auditor_ks_tail.json`).
* T1 residuals over 25 km/h: 4.6% in 2023 key-statistic matches, against 1.8% in 2021–22 key-statistic matches and 0.3–1.0% for points.
* The robust filter (clip c = 2) treats this tail the same way in every season, which is the point of consistency.

**No cleaning rule that needs a point table** (the engineer's 80% timed-coverage drop) is applied to key statistics. It would clean training rows and not test rows.

### Q3. The statistic: **f̂ is the right primary, with the modeller's frozen constants.**

* **Its tuning holds up.** The grid optimum is interior (h 14 of 3–120, s2f 12 of 1–36, q 4/yr, c 2.0, ν 7/8). Tuning was on ≤ 2022 and evaluation on 2023, as claimed.
  * On the clean T1 target the optimum moves to (h 21, s2f 18), with s2f on the grid's edge. The objective is flat: as-of eval MSE is 167.34 at the modeller's constants and 167.49 at the T1 optimum, and the A − B values correlate 0.99.
  * **Ruling: freeze the modeller's men's constants.** No re-tuning in R3.
* **f̂ against the registered window, like for like** (`auditor_gate2.py`; men 2022–23, as-of, target-edition FE). In pp per SD:

  | Target | f̂ | Window | x_raw | Joint fit: f̂ / window |
  |---|---|---|---|---|
  | First-serve points won | +0.33 [+0.20, +0.46] | +0.15 [+0.01, +0.29] | +0.19 [+0.04, +0.34] | +0.45 [+0.30, +0.59] / −0.17 [−0.32, −0.01] |
  | Serve points won | +0.11 [+0.02, +0.20] | +0.06 [−0.04, +0.15], tie | | +0.14 [+0.01, +0.26] / −0.04, tie |

  * Where a 14-day window exists, the joint fit is f̂ +0.79 [+0.55, +1.03] and the window −0.27, a tie.
  * Women: f̂ ≈ window (+0.36 vs +0.35).
  * **f̂ carries what the window carries, and more.**
  * On T1's full forecast the window's total (c52 + b·Δx) ties with L̂ + f̂: −2.12 [−6.24, +1.92] km/h², window slightly better. That difference comes from the level estimate, which is not the column.
* **The mechanism gate is sound, and it survives edition fixed effects for men** (`auditor_centring.py` part 2).
  * I checked the code: f̂, L̂ and all controls come from earlier matches; surface and level are pre-match context. I found no channel from the target match into f̂ or the controls.
  * Men, first-serve points won, edition FE: frozen +0.34 [+0.20, +0.47], as-of +0.33 [+0.20, +0.46]. Without FE: +0.35 and +0.32.
  * Earlier events only, FE: +0.32 [+0.09, +0.55], against serve points won +0.15 [−0.02, +0.32], a tie.
  * Women: within-Slam only (M6).
* **"0 when unknown is the Bayes value, so no reliability input is needed": accepted for men, with M2 noted.**
  * On T1, the slopes of (T − ΔL̂) on Δf̂ by recency stratum are 0.87 / 0.97 / 0.68 (both / one / neither side within 14 days), all close to 1.
  * For women the off-event strata are erratic (slopes −0.23 and 2.6 on SDs of 0.2–1.3 km/h). Women's values are within-Slam information only.
* **The modeller's probe** (8 order cuts, 0 changes) is fine for frozen offsets. It does not exercise a clock-based field statistic, so C7 requires both probes.

### Q4. Missing data and women

**Ruling.**
* **Men.** The column is the posterior-mean difference: decayed states are kept, a player with no history counts 0, and the column is **never NaN**. No reliability or precision input in A1.
* **Women.** **0 in A1** (no indicator; NaN would add a redundant "woman or no data" flag). **Their own values in A3.**

**Reasons.**
* T1 calibration for men is near 1 in every recency stratum, so NaN for "neither side within 14 days" would discard real, if attenuated, content (S5).
* For women the speed information is within-Slam only, and both published windows tie. The primary endpoint is men's, and women's rows with a different mechanism could dilute the slope TabPFN learns for men.
* A3 measures both questions directly:
  * do women's Slam values help women (S4);
  * do they dilute men (A3 against A1 on men's matches).

### Q5. Arms, seeds and the test

**Primary: P2 alone.** It is A1's calibrated paired mLL gain over the base on men's 2024–26 matches, debut seasons out (7,068). The interval is the four-week-block t interval with the **empirical** seed variance added. It answers "does it improve, and by how much".

**P1 becomes S0,** the key pre-registered secondary that reads a tie. No fixed sequence. With one confirmatory test, no correction is needed. The report states how many secondary intervals exclude 0, against chance.

**A3 = `spd_all`,** A1 plus women's Slam values.
* I chose it over a placebo because adding a column moves forecasts by about reseeding noise (0.013 against 0.014 RMS, `strategist_noise.json`), and P2's interval already carries seed variance.
* The women question (Q4) is open and decision-relevant; the placebo's answer is close to known.

**Seeds** follow the strategist:
* A1: 0–15 for 2024–26 and 0–3 for 2019–23;
* A2, A3 and the no-odds twin: 0–7 and 0–3;
* new `model_noodds` seeds: 3 for 2019–23 and 3–7 for 2024–26.

**Equal seed counts are guaranteed only if the scorer asserts them.**
* Each comparison uses the same seed set on both sides.
* Every calibration slope uses seeds 0–3 for every arm, the base included, though the base has 16.
* The race's base fits carry no fingerprint (S2), so two reproduction fits must match the stored forecasts exactly before any reuse.

**Blindness.** 2024 was in the published replication, so it is not blind; S2 reads 2025–26 alone. The decision table is in C6.

### Q6. Upstream defects and how the build handles them

No other study's file is edited.

| Defect (observed) | Handling in the build |
|---|---|
| `serve_speed_acquisition/speeds.py`, line 227, labels every ManTennisData "QF" row as qualifying (1,426 rows). The linker placed 1,416 on Stage 0 QFs; **8 went to qualifying matches and 2 to R32** | The panel never reads `speeds.parquet`'s `draw`: the draw comes from the linked Stage 0 match's `qualifying`. ManTennisData rows whose round label differs from the linked Stage 0 round are dropped, which catches all 10 (test T-P5). The lead should report the bug to the acquisition study's owner |
| Women's 2026: 40 frame ids re-keyed; 88 frame matches whose players differ between the pre-rebuild and rebuilt Stage 0 (67 other ids, 21 flipped sides) | The feature is computed per frame side from the **frame's own player ids** (`screen.PRE_REBUILD_STAGE0`), with histories keyed by player id from the rebuilt panel. The clock comes through `id_map.csv`. The flag `id_conflict` marks the 88. S4 reports women with and without them. A1 is unaffected (women 0) |
| The frame has no men's 2018 (frame counts: 2017 2,612, then 2019 2,587) | Inherited equally by every arm; nothing to fix. The speed history comes from Stage 0, which has 2018 Slam rows, so men's 2019 features are complete. Stated in the report |
| The modeller's design panel has no AO 2026 | The build uses the engineer's panel, which carries the AO match centre (+0.5) |
| The frame ends with events that started by 28 Jul 2026 | Report wording: "2026 to early August". USO 2026 is outside the test |
| Mislinked and broken key statistics (4–7.5% of matches more than 10 km/h from points; about 1% swaps) | The robust filter, the same in every season. No point-dependent cleaning (Q2) |

## (c) R3 build spec

Every path is under `src/eda/serve_speed_tabpfn/` (code), `test/serve_speed_tabpfn/` (tests) or `data/studies/serve_speed_tabpfn/` (outputs). Python is `./python.sh` only.

### C1. Panel (engineer) → `speed_panel.parquet`, built by `panel.py`

1. **Inputs.**
   * The engineer's per-source records, rebuilt in `panel.py` from the same sources as `engineer_records.py`: point tables of `slam_pbp`, `slam_tracking`, `slamtracker`, `infosys`, `sirgenkii` and `infosys_slams`; ManTennisData and the handoff key statistics; the AO match centre. Drop Flashscore.
   * Stage 0 is the rebuilt `stage0_matches.parquet`, read with an explicit column list that never names a result. The clock (`es`, `lf`, `obs`) comes from `timing.parquet`.
2. **The value per (match_id, side).**

   | Tier | Point mean | Key statistic | AO match centre |
   |---|---|---|---|
   | Slams | 1st | 2nd | 3rd |
   | Other levels (tour, qualifying, Challengers, team, ITF) | 2nd | **1st** | 3rd |

   * **Point mean:** first serves in (serve 1, not a double fault) timed in (40, 270], n = timed count. Gate: n / first serves in ≥ 0.5. The source with the largest n wins; ties go infosys_slams > sirgenkii > infosys > slam_tracking > slamtracker > slam_pbp.
   * **Key statistic:** ManTennisData, else the handoff copy; y = KS − 0.5, n = `ks_first_in`.
   * **AO match centre:** y = MC + 0.5, n = first serves in.
3. **Drops** (`use = False`, kept with `drop_reason`):
   * a key-statistic duplicate within a source with values more than 0.5 km/h apart;
   * a ManTennisData row whose round label differs from the linked Stage 0 round;
   * an AO match-centre duplicate in conflict;
   * men's y < 120 or women's y < 100;
   * n < 10;
   * no clock.
   * **Not** the point-coverage drop for key statistics. The own-history outlier is flagged, not dropped.
4. **Columns.** The engineer's schema (proposal §12), plus:
   * `basis` (`ks` | `pts`; the match centre counts as `pts`);
   * `edition` = `tournament_id | M/Q | basis`;
   * `family`: a Slam name, `tour` (T250, T500, T1000, FIN), `ch`, or `other` (TEAM, ITF), × M/Q. The `ch` family is the fix for E7.

### C2. As-of edition offsets (engineer) → `EditionOffsets.at(day, tour)` in `panel.py`

**Fit on day D, per tour.** The rows are those with `use`, lf + 1 ≤ D and obs ≥ D − 364. Model y_i = α_player + γ_edition + ε by weighted alternating least squares:

* weights w_i = 1 / (22 + 12.4² / n_i);
* each γ_e is shrunk to its family's weighted mean residual: a prior worth K = 25 player-matches, with weight 25·mean(w);
* at most 60 iterations, stopping at max |Δγ| < 1e-6;
* the snapshot needs at least 50 rows, else all γ = 0;
* the reference is any fixed rule; the engineer's is fine. A common shift cancels in f̂ under C3.

**An edition with no released row in the window** takes the unweighted mean γ of its family's in-window editions at D, else 0.

The constants τ² = 22, s = 12.4, K = 25 and the 364-day window are frozen; they come from ≤ 2023. Cache by day.

### C3. The state feature (modeller) → `features.py` → `features/speed.parquet` + `speed_meta.json`

**History of side P before match m** (P's id from C4):
* P's `use` rows with tdate < tdate_m, or the same `tournament_id` with round_order < round_order_m;
* and obs ≥ es_m − 364;
* in own order (tdate, tournament_id, round_order).

**Centred value:** z_h = y_h − γ̂_{e(h)}(es_m), from C2 at the target's own `es`.

**Noise:** R_h = ν_{b(h)} + σ² / n_h.

**Filter.** States L (level) and f (fast). At the first history row, L = 0 with P11 = 1e6, f = 0 with P22 = s2f, P12 = 0, and the first row skips the prediction step.

```
predict over Δ = max(obs_h − obs_prev, 0):  φ = 2^(−Δ/h)
    f ← φ f;   P11 ← P11 + qΔ;   P12 ← φ P12;   P22 ← φ² P22 + s2f (1 − φ²)
update:  v = z − L − f;   S = P11 + 2 P12 + P22 + R;   v ← sign(v) · min(|v|, c √S)
    K1 = (P11 + P12) / S;   K2 = (P12 + P22) / S
    L ← L + K1 v;   f ← f + K2 v
    P11 ← P11 − K1² S;   P12 ← P12 − K1 K2 S;   P22 ← P22 − K2² S
project to es_m:  Δ = max(es_m − obs_last, 0);   f̂ = 2^(−Δ/h) f;   σ̂² = φ² P22 + s2f (1 − φ²)
no history:  f̂ = 0,  σ̂ = √s2f,  L̂ = NaN
```

**Frozen constants:**

| | h | s2f | q | c | ν_pm | ν_ks | σ |
|---|---|---|---|---|---|---|---|
| Men | 14 d | 12 km/h² | 4/365 km/h² per day | 2.0 | 7 | 8 | 13.49 km/h |
| Women (A3 only) | 14 d | 12 | 4/365 | 4.0 | 14 | 10 | 10.72 |

**Columns** (one row per frame match, all 63,737, 2013–26):

| Column | Definition | Women | Missing |
|---|---|---|---|
| `spd_f` (A1) | clip((f̂_A − f̂_B) / s_f, −4, 4) | 0 | never NaN |
| `spd_f_all` (A3) | the same, with women's values from women's constants and the same s_f | own values | never NaN |
| `spd_raw` (A2) | clip(x_raw / 5.998, −4, 4), the registered statistic on this panel: raw y (no offsets), n-weighted means over own earlier rows with obs_m − obs_h ≤ 14 and ≤ 364, A − B; men with both sides holding a 14-day row | NaN | NaN otherwise |

* **s_f** = the SD of (f̂_A − f̂_B) over men's frame matches of 2022–23, all matches, unclipped. Expect about 2.2 km/h. It is computed from ≤ 2023 values only and written to the metadata.
* **Diagnostics** (not inputs): f̂, σ̂, L̂, the history count, k14, k28 and last_age per side; the basis mix of each side's 28-day history; `id_conflict`.

### C4. Frame join and orientation (engineer)

* **Keys and orientation.** Key on the frame's `match_id`. Side A = `player_a_id` of the **pre-rebuild** Stage 0 (`screen.PRE_REBUILD_STAGE0`).
* **Clock.** Take `es`, `tdate`, `tournament_id` and `round_order` through `id_map.csv` to the rebuilt timing.
* **Speeds.** Speed histories are looked up by player id in the rebuilt panel. A frame player id absent from the rebuild has no history (0).
* **Join.** One-to-one; every frame match gets a row.

### C5. Arms, registry and fit plan (strategist)

**Registry** (`data/studies/serve_speed_tabpfn/features/registry.json`): `spd_f`, `spd_raw` and `spd_f_all`, kind **diff**, family `speed`.

**Arms** (this study's `arms.py`): `spd` = 58 + `spd_f`; `spd_raw` = 58 + `spd_raw`; `spd_all` = 58 + `spd_f_all`; `spd_noodds` = 57 + `spd_f`.

Fits go to `data/studies/serve_speed_tabpfn/local/` only. Settings: 8 estimators, temperature 0.9, `ignore_pretraining_limits`. Each fit predicts `td`; arms with odds also predict `early` and `late` in 2025–26. The SHA-256 of the feature file goes in each fit's metadata.

| Job | 2019–2023 seeds | 2024–2026 seeds | Fits |
|---|---|---|---|
| `spd` (A1) | 0–3 | 0–15 | 68 |
| `spd_raw` (A2) | 0–3 | 0–7 | 44 |
| `spd_all` (A3) | 0–3 | 0–7 | 44 |
| `spd_noodds` | 0–3 | 0–7 | 44 |
| `model_noodds`, new seeds | 3 | 3–7 | 20 |
| **Reproduction:** `model` 2024 seed 0 and `model` 2026 seed 2 (race files) | | | 2 |
| **Total** | | | **222**, about 2.1 h at 15–47 s per fit |

Before any reuse of base fits:
1. The two reproduction fits must equal the stored `p_td` (and `p_early` / `p_late` for 2026) within 1e-6.
2. CPU check: this study's `job_data` fingerprints for `model` must equal the stored fingerprints of every feature-interactions fit (seeds 3–15, 2019–26).

The base folders stay read-only.

### C6. The scorer (strategist) → `score.py --check | --run | --synthetic`

**Forecasts.**
* Symmetrised (`td`: stored and flipped), averaged over the stated seeds.
* η = logit of the seed mean.
* Base `model` seeds load from this study's folder, then feature interactions', then the race's, with column, shape and id checks.

**Calibration (decided).**
* One slope per tour on η, with no intercept.
* It is fitted for season Y on the arm's own seasons 2019..Y−1, from the **seeds 0–3 mean**, and applied to the season-Y seed mean.
* The same for every arm and the base.

**P2 (primary).**
* G = 1000 · mean[LL(q_base) − LL(q_A1)] over men's frame matches 2024–26, debut seasons out (7,068). **Positive = A1 better.**
* SE = √(SE_block² + v_A1 + v_base).
  * SE_block is `T.paired_interval` on four-week blocks (`T.blocks(tournament_date, 28)`).
  * v_arm = var over seeds k of the mean log loss of seed k's forecast, calibrated with the arm's seed-mean slope, divided by K. This is the `surface_ios/score.seed_var` convention.
* t on G − 1 degrees of freedom; 95% two-sided.

**Secondaries** (descriptive; each with its direction; seed sets as in C5):

| # | What |
|---|---|
| S0 | The information test: `tabpfn_tests.encompassing` with dev replaced by z = `spd_f`, given the base's raw 16-seed η (slopes per tour × season, the cubic, union-clustered variance), men 2024–26. b in log-odds per SD; positive = the man whose speed state is higher wins more than the base says |
| S1 | P2 by season |
| S2 | P2 on 2025–26 alone (blind for the new coverage) |
| S3 | P2 by recency: both sides / one side / neither with a timed row within 28 days (the last is a harm check, expected about 0) |
| S4 | A1 against the base on women and on both tours; A3 against the base on women, with and without the 88 `id_conflict` matches |
| S5 | `spd_noodds` against `model_noodds` (seeds 0–7), men 2024–26, each calibrated on its own 2019..Y−1 |
| S6 | Polymarket 24 hours out: A1 against the base, both fed the `early` price and calibrated with their close slopes (men 2025–26: 1,442 matches). Also the 24 h → 30 min price move regressed on η_A1 − η_B |
| S7 | P2 on raw (uncalibrated) forecasts |
| S8 | A2 and A3 against the base (seeds 0–7); A1 against A2 (0–7); A3 against A1 on men (0–7, dilution) |
| S9 | The walk-forward nudge: q = s·η_base + b̃_Y·z, b̂_Y fitted on 2019..Y−1; shrunk (τ = 0.05) and unshrunk |
| S10 | Capture: the applied slope a = Σ dev·z / Σ z², dev = η_A1 − η_base (seed means 0–15), in log-odds per SD. Report a / b_S0 when S0's interval excludes 0 |
| S11 | P2 with a block-only interval and with a calendar-week interval |
| S12 | The registered statistic's replication: `encompassing` with z = `spd_raw` (NaN → 0), given the base, men 2025–26 (out of the published 2022–24 window) |

**Decision table** (fixed before the hash):

| P2 (men 2024–26) | S0 | Reading |
|---|---|---|
| lo > 0 | any | "Adding the speed state improves the men's log loss by G [lo, hi] mLL" |
| hi < 0 | any | Harm: "it worsens by \|G\|"; do not deploy |
| tie | lo_b > 0 | Information is present beyond the base and the column does not deliver it. Name the suspects: capture (S10), seeds, representation (S8). Next step: a prospective nudge (S9) |
| tie | tie | "No detectable speed information beyond the model in 2024–26"; S0 bounds β and P2 bounds the gain |
| tie | hi_b < 0 | A reversal of the published direction, reported as such |

**Multiplicity:** one confirmatory test (P2). The report gives the count of the S0–S12 intervals that exclude 0, against chance's 5%.

**Power, stated up front** (strategist's simulation; verified on disk; conservative, S3):
* at a planning β of 0.05 / 0.077 / 0.09 per SD, P2 has 11–15% / 34–36% / 45–51% power, and S0 29–31% / 58–60% / 73%;
* **a tie in P2 is the expected reading.**

**Process suspects pre-named for a null:**
1. capture;
2. the key-statistic error tail (Q2);
3. measuring breaks (only partly removed: AO 2024 under as-of);
4. 2025 coverage (50% of men's matches have both sides within 14 days);
5. seed count.

### C7. Probes and tests (each builder; all must pass before any fit; the runner refuses a feature file without the probe record)

**Engineer (`test_panel.py`):**
* **T-P1:** one row per (match_id, side); the column lists name no result.
* **T-P2:** `slam_pbp` − `slamtracker` SD < 0.1; ManTennisData equals the handoff on ≥ 99.8% of shared rows.
* **T-P3:** KS = ceil(point mean) on ≥ 75% of complete tables ≤ 2023.
* **T-P4:** presence reproduces the acquisition's N2 counts within 1% or 5 matches per tour × year × Slam cell.
* **T-P5:** every QF-labelled ManTennisData row linked to a non-QF Stage 0 match is dropped (10); `draw` is never read.
* **T-P6:** AO 2026 holds ≥ 470 rows per tour.
* **T-P7:** γ̂(D) is unchanged for every D ≤ C when speeds of rows with es > C are noised (25 days C).
* **T-P8:** the frame join is one-to-one with all 63,737 matches; 21 flips and 67 conflicts are flagged; orientation follows the frame's ids.

**Modeller (`test_features.py`):**
* **T-F1:** the filter equals an independent reference on 2,000 random targets within 1e-9. The reference can be `modeller_state.kalman` fed the same centred rows, or `auditor_lib.kalman_batch`.
* **T-F2, Probe A (own history):**
  * ≥ 25 cuts in Stage 0 `order`, ≥ 10 of them in 2024–26; 5,000 frame sides.
  * Noise U(100, 250) replaces y for rows with order ≥ cut, **in the filter input only**; the snapshots are held at the clean build.
  * No side value of a target with order ≤ cut may change (tolerance 1e-12).
  * Leaky control: with each target's own row added to its history, targets at the cut change in ≥ 80% of cuts.
* **T-F3, Probe B (clock):**
  * ≥ 25 cut days: the four in `match_timing/probe.py`, each Slam's second Wednesday in 2024–26 within the frame, and random days.
  * Rows with es > D get noise in **both** the filter and the snapshot inputs.
  * No value of any frame side with lf ≤ D may change, f̂ and the γ̂ it used alike.
  * Leaky control: snapshots that admit rows by tournament_date ≤ D must move some such target.
* **T-F4:** the constants, s_f (from ≤ 2023 values) and the C2 constants equal the frozen values.
* **T-F5:** flipping A and B negates all three columns exactly.
* **T-F6:** the coverage table per tour × season (counts only for 2024–26).

**Strategist (`test_harness.py`):**
* **T-H1:** flip is an involution with NaN; the 58 base columns hash-equal the frame's; the feature join is one-to-one.
* **T-H2:** the job list equals C5's 222 jobs.
* **T-H3:** the reproduction and fingerprint checks of C5 pass.
* **T-H4:** calibration and nudge read seasons < Y only.
* **T-H5:** every comparison's two seed sets are equal, and calibration uses 0–3.
* **T-H6:** `--synthetic` never selects `a_won`.
* **T-H7:** `--check` writes the population hash and counts without outcomes.

**R4 (auditor):** an independent rebuild of `spd_f` with `auditor_lib`. The A − B correlation must be ≥ 0.995 and the absolute difference ≤ 0.05 s_f on ≥ 99% of frame matches. Plus my own runs of Probes A and B.

**R4 (verifier):** P2 and S0 on synthetic outcomes: the null rejection rate and the recovery of a planted β.

## (d) Contested points (a rebuttal can change a ruling only as stated)

1. **Centring (modeller).** It changes only if:
   * a probe shows a leak the as-of build cannot avoid; or
   * a ≤ 2023 result-free target that does not reward carried edition effects shows as-of degrading f̂'s change part beyond its interval.
2. **Basis (engineer).** This is the closest call. It changes only with ≤ 2023 evidence that ks-first loses f̂'s change information (not the level) on a basis-neutral target (the FE gate), beyond its interval.
3. **Women in A1 (engineer, modeller).** It changes only if the lead makes the primary population both tours.
4. **P1 → P2 sequence and A3 = women rather than a placebo (strategist).** The lead's call under `team.md`. The primary must still answer "by how much".

## (e) Looks (for the ledger)

| # | Seasons | What was related to what | Script → output |
|---|---|---|---|
| A1 | 2011–2026 | Counts only: panel rows by tour × year × Slam × draw; ManTennisData round labels against linked Stage 0 rounds; frame ids against both Stage 0 versions. Speeds against speeds ≤ 2023: the modeller's offsets fitted ≤ 2022 and ≤ 2023 | `auditor_checks.py` → `auditor_checks.json` |
| A2 | 2023 | Feature values only: my f̂ against the modeller's stored f̂ (re-implementation) | `auditor_centring.py` part 0 |
| A3 | Men 2019–2023 (tune ≤ 2022, evaluate 2023); women Slams 2016–2023 (tune ≤ 2020, evaluate 2021–23) | **Statistic target:** the within-match A − B first-serve speed difference (T1) against forecasts under raw, frozen and as-of centring; filter constants on a grid; window forecasts | `auditor_centring.py` part 1 |
| A4 | Men 2022–2023; women Slams 2016–2023 | **Statistic targets (one player's rate, never A − B):** aces per serve point, first-serve points won per first serve in, serve points won per serve point, against f̂ (frozen and as-of), with and without target-edition fixed effects | `auditor_centring.py` part 2 |
| A5 | 2022–2026 frame matches | Feature values only: A − B f̂ under three centrings (SDs, correlations, shares moved); mean f̂ by group (Slam qualifiers at R1; sides after a Slam with a break) | `auditor_centring.py` part 3 |
| A6 | ≤ 2023 targets; 2022–2026 values | **Statistic target (T1):** residual tails by basis; robust frozen-against-as-of on 2023; point-mean target 2021–23 with ks-first against pm-first histories. 2022–26: A − B f̂ from the two panels and the history basis mix (values only) | `auditor_basis.py` → `auditor_basis.json` |
| A7 | 2021–2026 | Speed records only: ManTennisData key statistics against Infosys point means and counts (side swaps, disagreements); no target | `auditor_ks_tail.py` → `auditor_ks_tail.json` |
| A8 | Men 2022–2023; women Slams 2016–2023 | **Statistic targets as A4,** against f̂, the as-of window and raw x_raw, singly and jointly, with edition fixed effects | `auditor_gate2.py` → `auditor_gate2.json` |

No speed value or feature was related to `a_won`, a winner, sets, games, any price or an A − B difference of serve points won, in any season.
