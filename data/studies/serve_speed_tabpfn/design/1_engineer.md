# R1 design proposal: the speed-data engineer (agent 1)

7 October 2026. Independent R1 proposal: no other agent's `1_*.md` was read. Labels: **observed** (computed here; scripts in §13), *inferred*, **suggestion**.
* No script read a match result. Stage 0 is always read with an explicit column list, and the model frame without `a_won` or `p_mkt`.
* The one statistic-target look (seasons ≤ 2023) is in §14.

## 0. Recommendation in five lines

1. **One row per Stage 0 player-match, from every held source.**
   * A gated point mean first. Else the ATP key statistic **− 0.5 km/h** (it is the *ceiling* of the point mean). Else the AO match centre **+ 0.5** (it is the floor).
   * The draft has 42,964 rows, all with `es`, `lf` and `obs`. Drop Flashscore: it adds one frame match.
2. **Centre with as-of edition offsets, not frozen ones.**
   * An edition is event × year × main/qualifying × basis. The offsets are refitted for each target day D = `es` on player-matches with `lf + 1 ≤ D`.
   * The test seasons hold measuring-system breaks no frozen constant can know. Same players, median change: W 2024→25 **+8.5 km/h**, USO 2025→26 **+9.7**, AO 2023→24 **+3.5**.
3. **Keep qualifying, Challengers and Davis Cup in the history, with draw-level offsets.**
   * Qualifying typically reads 1.3–3.7 km/h slower than the main draw for the same player-season.
   * Qualifying adds 9–12% of the men's matches where both sides have a 14-day value.
4. **Prefer points over key statistics, but carry both.**
   * When they disagree by more than 3 km/h, the point mean matches the player's other matches better 72% of the time.
   * 2025–26 tour data are almost all key statistics, so a key-statistic-first twin must be buildable.
5. **Imputation is needed for about half the men's test matches.**
   * Both sides have a 14-day value in **61 / 50 / 52%** of men's 2024 / 25 / 26 frame matches, and a 364-day value in 97–99%.
   * Women: 8–12% and 88–92%.

## 1. Definitions

For player-match *i* of player *p*:
* **Point mean:** y_i = (1/n_i) Σ v_k over his first serves in (serve 1, not a double fault) timed in (40, 270] km/h. n_i is the number of timed first serves in; f_i is all first serves in. Gate: n_i/f_i ≥ 0.5.
* **ATP key statistic:** y_i = KS_i − 0.5, with n_i = the box-score count of first serves in. **AO match centre:** y_i = MC_i + 0.5.
* **Edition** e(i) = (tour, `tournament_id` [year-specific], main | qualifying, points | key statistic). **Family** = the Slam or "tour", × draw.
* **As-of offsets** at day D, per tour:
  γ̂(D) = argmin Σ_{i: lf_i+1 ≤ D, obs_i ≥ D−364} w_i (y_i − α_p(i) − γ_e(i))² + K·w̄·Σ_e (γ_e − γ̄_fam(e))²
  * Weights: w_i = 1/(τ² + s²/n_i).
  * Reference: the men's tour main-draw editions average 0 (when they hold at least 200 rows), else the Slam main draws.
  * Prototype constants: τ² = 22 and s = 12.3 km/h (men) / 9.8 (women), from seasons ≤ 2023; K = 25 player-matches, a choice for the modeller to tune on ≤ 2023 targets.
* **Centred speed for target t:** c_i(t) = y_i − γ̂_e(i)(es_t). An edition with nothing released yet takes its family mean.
* **Windows,** as for `x_raw`: own earlier matches with obs_t − obs_i ≤ 14 or ≤ 364 days. S_W = Σ n_i·c_i(t) and N_W = Σ n_i. The registered change is S₁₄/N₁₄ − S₃₆₄/N₃₆₄; representations are the modeller's.

## 2. Data and harmonisation (Q1)

**Sources.** Observed; timed and linked player-matches; a point mean must pass the gate.

| Source | Basis | Coverage | Player-matches |
|---|---|---|---:|
| `slam_pbp` | points | Slams 2011, 2014–24 | 13,248 |
| `slam_tracking` | points | AO/RG 2019–24, Hawk-Eye copy | 3,894 |
| `slamtracker` | points | W/USO 2019–26 | 6,438 |
| `infosys` | points | ATP tour and qualifying, 2021–24 | 9,709 |
| `sirgenkii` | points | ATP, Jan–Apr 2025 | 698 |
| `infosys_slams` | points | AO 2025, RG 2025–26, main draws and qualifying | 2,595 |
| ManTennisData | key statistic | ATP tour and some Challengers, 2021–26 | 19,810 |
| Handoff key statistics | key statistic | ATP 2018–24 | 12,023 |
| AO match centre | floored mean | AO 2026 and captures | 1,063 |

**Duplicates.** 43,019 player-matches are timed; 16,859 of them by 2 or more sources (7,371 by two, 9,472 by three, 16 by four).

**Agreement on the same player-match** (km/h, first source minus second; observed):
* **Copies agree:**
  * `slam_pbp` − `slamtracker`: 2,871 player-matches, median 0.00, sd 0.04;
  * `slam_pbp` − `slam_tracking`: 1,412, median 0.00, sd 0.42;
  * ManTennisData − handoff: 11,627, identical except 10;
  * `infosys` − `sirgenkii`: 16 of 16 identical.
* **Rounding:**
  * RG's key statistic is the rounded point mean (1,286 of 1,294).
  * The AO match centre sits 0.03–0.46 below the AO 2025 points in 10 of 10: a floor (*inferred*, n = 10).
* **Conflicts beyond the basis gap (§3) are mislinks:**
  * duplicated keys with conflicting values: ManTennisData 45 of 50, handoff 18 of 20;
  * 54 ManTennisData rows whose round differs from Stage 0's;
  * 2 Challenger rows linked to RG 2026 Q1, 12.9 km/h off.
  * **Upstream note for the lead:** `serve_speed_acquisition/speeds.py` labels ManTennisData quarterfinals as qualifying (`stadie_id.startswith("Q")`). The linker still placed 1,416 of 1,426 correctly.

**Choice rule** (*suggestion*; draft `engineer_panel0.py`, 31,981 men's and 10,983 women's rows):
1. A gated point mean. The source with the most timed serves wins; ties go infosys_slams > sirgenkii > infosys > slam_tracking > slamtracker > slam_pbp.
2. Else the key statistic − 0.5, unless one of these holds:
   * a held point table times under 80% of the box's first serves in (37 dropped);
   * it is a conflicting duplicate;
   * its round disagrees with Stage 0's.
3. Else the AO match centre + 0.5.

**Other columns:**
* **Second serve:** everywhere. Key statistic − points, median +0.50, so the same shift applies.
* **Maximum:** everywhere, but the key statistic is at least the point maximum in 92% of player-matches. *Inferred:* it includes faults, so keep the bases apart.
* **First-serve fault speed:** AO 2025 and RG 2025–26 only (2,593 rows). A diagnostic, not a window input.

## 3. Basis offset (Q2)

Observed: ManTennisData − held Infosys point mean on the same player-matches, 2021–24.
* **All 9,449:** median **+0.525** km/h (key statistic higher), mean +0.37, sd 5.19. 11.5% differ by more than 3 km/h.
* **Complete point tables** (every first serve in present and timed; 2,545): KS = ceil(point mean) in **81.5%**, median +0.516.
  * Seasons ≤ 2023 alone: 1,170 of 1,436, median +0.517.
* **Flat in n:** the medians run 0.43–0.54 across first-serve bins.
* **The spread grows as the point table's timed coverage falls:** sd 1.5 at 99% or more, 3.6 at 90–95%, 30 below 60%.
* **Which is right when they disagree by more than 3 km/h?** (2021–23, 524 player-matches; Look 1.) The point mean is closer to the player's same-season median in 72% of cases. Median absolute error: 3.5 km/h for the point mean, 7.5 for KS − 0.5.

**So:**
* A **constant −0.5 km/h** harmonises the basis (the ceiling).
* The per-match rules are about choice, not adjustment: points first, and no key statistic where the point table shows low coverage.
* *Inferred:* about 8% of key-statistic-only values are off by more than 3 km/h, so robust windows matter most in 2025–26.

## 4. Measuring systems (Q3)

**Decomposition** (observed): player × season fixed effects + edition effects, weighted, each season normalised to its Slam main draws.

**Men, seasons ≤ 2023** (20,822 rows, 368 editions): offsets from the Slam mean, positive = reads faster.

| Family | Offset (km/h) |
|---|---:|
| Tour main draws (points) | **+5.67** |
| Tour key statistic | +6.33 |
| Tour qualifying | +3.35 |
| W | +1.88 |
| AO | +0.74 |
| RG | −0.69 |
| USO | −1.46 |

* Women: W +1.96, AO +0.76, USO −0.96, RG −1.23.
* The study's raw-mean offsets (W +3.13, RG −2.49) mix player populations (*inferred:* big servers go deep at Wimbledon, clay players at RG).

**AO 2024 is visible.**
* Edition effect: men +3.26, women +1.87. AO 2023: −0.12 / +0.77; AO 2025: −1.13 / −0.77.
* Same players: AO 2023→24 +3.49 (88 men), +2.50 (78 women); 2024→25 −1.65.
* AO's own published averages agree with the Hawk-Eye copy at AO 2024 (27 player-matches, median difference +0.18). So the shift is in AO's system, not in the copy.

**Breaks in the test seasons** (same players, median change):
* W 2024→25: **+8.48** (52 men), +3.11 (56 women). 2025 is when every Wimbledon court was timed.
* USO 2025→26: **+9.66** (87 men), +7.54 (82 women).

**Tour events differ** (men, ≤ 2023, 75 main-draw editions with at least 20 rows):
* Edition sd 2.07 km/h, with a mean SE of 0.76. Net of noise: **persistent event sd 1.66**, **year-specific sd 0.95**.
* Indoor +2.3 km/h above outdoor; clay +3.6, hard +5.9, grass +6.3.
* Single events jump: Rome +6.5 → +1.9, Delray +0.9 → +4.1 (2022→23). Altitude: Madrid +6.7 against Monte-Carlo's +3.4 / +4.3.
* The radar vendor is not on disk.

**Qualifying − main draw, same event-year:**
* Tour: median −1.27 (111 event-years).
* Slams, men / women: AO −1.6 / −2.3, RG −3.0 / −3.6, W −1.7 / −3.7, USO +0.1 / −2.1.

**Applying the offsets leak-proof** (*suggestion:* as-of, §1). Prototype `engineer_asof.py`: 26 s for all 127,474 frame sides.
* **It learns a new edition in 1–3 days** (offsets relative to the tour reference):

  | Edition | Prior | Day 1 | Day 2 | Final |
  |---|---:|---:|---:|---:|
  | W 2025, men | −6.25 | +0.69 (56 released) | +2.35 (126) | +2.66 |
  | USO 2026, men | −7.19 | | −1.31 | −1.24 |
  | AO 2024, men | −5.46 | | | −1.85 (day 3: −2.47) |

* 1.1% of sides or fewer have a 14-day match whose edition has nothing released yet.

**What centring changes** (values only):

| | Side change, raw vs as-of | A − B feature, raw vs as-of |
|---|---|---|
| Men 2025–26, Slams | corr 0.74; 40% move more than 3 km/h (frozen ≤ 2023: 27%) | corr 0.92; **14.7%** move more than 3 km/h |
| Men 2025–26, non-Slam | corr 0.96; 18.5% | corr 0.98; 2.6% |

* The raw side change carries a systematic **+1.8 km/h** at tour events (14-day windows heavy in tour matches, 364-day windows that include Slams); as-of, +0.25.
* The **frozen fallback** (family × draw × basis, ≤ 2023) cannot see the 2025–26 breaks.

## 5. Plausibility and noise (Q4)

Observed:
* **Drop:**
  * men under 120 km/h: 13 rows (11 ManTennisData);
  * n₁ < 10: 67 rows.
* **Keep:**
  * men 120–140: 26 rows;
  * women: none under 100, and the 30 at 100–120 km/h (women's 0.1% quantile is 116);
  * n₁ < 20: 529 rows (the weights handle them).
* **The half-timed gate barely binds:** it drops 37 of 9,746 Infosys rows, and 1–50 per Slam source. 82–98% of player-matches are at least 90% timed.
* **Own-history outliers** (|y − median of his previous ≤ 10| with at least 5): more than 15 km/h in 2.6% (key statistics 3.1%, points 1.9%), more than 20 in 0.9%.
  * Part of this is edition effects. **Suggestion:** compute it after centring and *flag*, not drop, at more than 20 km/h.
* **Noise (≤ 2023):** within-match sd s = 12.3 / 9.8 km/h (men / women); match-to-match sd beyond sampling τ ≈ 4.7.

## 6. Linking and clock (Q5)

Observed:
* **ManTennisData:** 20,412 rows, 20,248 of them with a first-serve average; 19,972 linked.
  * ManTennisData has no dates: each linked Stage 0 match takes `es`, `lf` and `obs` from `timing.parquet`.
  * **0** linked rows lack a clock. Exact days for 99.6%; median `lf − es` is 1 day.
  * Unlinked: 438 rows, of which 430 are 2026 Challenger qualifying that Stage 0 lacks.
* **Clock coverage:** every panel row (42,964) and every frame match (63,737) has `es`, `lf` and `obs`.
* **Pre-rebuild against rebuilt Stage 0:**
  * Men: match ids and player ids are identical.
  * Women 2026: 40 frame ids were re-keyed, and the id map resolves all 40.
  * **67 women's 2026 frame matches carry other player ids before the rebuild.** 101 of those 134 ids exist nowhere in the rebuild (*inferred:* wrong in the frame).
* **Suggestion:**
  * Key the panel on rebuilt ids.
  * Join the frame through the id map, with the frame's own player ids.
  * Leave those 67 matches missing, and refer them to the lead.

## 7. Which matches feed the windows (Q6)

Men's frame matches with both 14-day values, adding history levels cumulatively (observed):

| History used | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|
| Main-tour main draws | 1,025 | 1,175 | 1,449 | 1,177 | 821 |
| + tour qualifying | +80 | +102 | +171 | +94 | +78 |
| + Slam qualifying | +12 | +8 | +5 | +38 | +16 |
| + Challengers | +2 | +1 | +3 | +2 | +12 |
| + Davis Cup / ITF | +16 | 0 | 0 | 0 | 0 |
| **All** | **1,135** | **1,286** | **1,628** | **1,311** | **927** |

* Qualifying appears in 13–20% of the men's 14-day windows.
* 7–9% of sides have only non-main matches in their 14-day window.

## 8. Coverage on the model frame (Q7)

Observed, in matches. The Slam / non-Slam split is in `engineer_coverage_frame.csv`.
* 2013 has no speed history (the 2012–13 Slam files lack serve numbers).
* The frame holds no men's matches in 2018.

| Year | Men frame | Both 14d | ≥ 1 side 14d | Both 364d | Women frame | Both 14d | ≥ 1 side 14d | Both 364d |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2014–19, average per season | 2,599 | 121 | 299 | 1,752 | 2,473 | 117 | 282 | 1,630 |
| 2020 | 1,259 | 149 | 321 | 968 | 1,046 | 130 | 217 | 755 |
| 2021 | 2,466 | 378 | 613 | 1,938 | 2,289 | 266 | 440 | 1,688 |
| 2022 | 2,606 | 1,135 | 1,898 | 2,423 | 2,339 | 192 | 332 | 1,923 |
| 2023 | 2,676 | 1,286 | 2,010 | 2,578 | 2,464 | 176 | 348 | 2,018 |
| **2024** | 2,676 | **1,628** | 2,293 | 2,606 | 2,465 | **184** | 333 | 2,158 |
| **2025** | 2,620 | **1,311** | 1,956 | 2,586 | 2,485 | **281** | 452 | 2,282 |
| **2026** | 1,774 | **927** | 1,405 | 1,753 | 1,714 | **213** | 314 | 1,557 |

* **Training rows with both 14-day values:** 5,018 for the 2024 fit (men 3,552 + women 1,466), 6,830 for 2025, 8,422 for 2026.
* **Men's test seasons:** 55% of matches have both values and 80% at least one side.

## 9. Missing data, priors and entry to TabPFN (views)

* **The panel's role:** per target side it supplies N₁₄, N₃₆₄, match counts, days since the last timed match and the basis mix. Priors are the modeller's.
* **Where the gap is:** the 364-day level exists for 97–99% of men, so the gap is the recent state. That favours shrinking toward the player's own level over a population prior.
* **TabPFN (*suggestion*, deferring to the strategist):** one A − B column of the as-of-centred change, NaN where missing, plus a reliability input.
* **Women:** keep their Slam-only values. At Slam rounds 2 and later both players share the edition.

## 10. Result-free gates for the R3 build

1. **Shape and inputs:** one row per (match_id, side); assertions that no result column is read.
2. **The copies agree:** `slam_pbp` − `slamtracker` sd < 0.1; ManTennisData equals the handoff on at least 99.8% of shared rows.
3. **The ceiling rule holds** on at least 75% of complete tables ≤ 2023.
4. **Presence reproduces the acquisition's N2 counts** within 1% per cell. Observed now: within 0–5 matches in every tour × year × Slam cell.
5. **Leak probes:**
   * an order cut, as `speed_build.leak_probe`: no earlier window moves;
   * a day cut, `match_timing/probe.py`'s idea: noising the speeds of matches with `lf` ≥ the cut moves no γ̂(D) for D ≤ cut, and no target with `es` ≤ cut.
6. **Constants:** τ², s, K and the frozen fallback come from seasons ≤ 2023 (an assertion).

## 11. Leak argument

* **Each match's own records only:** the values, the choice and the drops. The ±0.5 shifts are rounding rules, checked on ≤ 2023.
* **Own history, safe by construction:** the windows hold the player's own earlier matches (an earlier tournament date, or an earlier round), never another event of the same week.
* **Pooled quantities follow the clock:** edition offsets, family means and the reference use `lf + 1 ≤ D`, and a target reads D = `es`. The tournament start date is never used.

## 12. Effect, cost, risks, schema

* **Effect.** The panel sets n, not β (§8). Centring lowers the sd of the men's A − B feature by 2–7% (Slams 2025–26: 6.17 → 5.73).
* **Cost.** CPU only, about 2 minutes in all. **No GPU.**
* **Risks:**
  1. **Basis shift between training and test:** men's tour values are about 80% points in 2022–24 and nearly all key statistics in 2025–26. The test feature has a heavier error tail, which attenuates the effect. Mitigation: robust windows, and a key-statistic-first twin compared on ≤ 2023 targets.
  2. **Schedule-driven missingness:** whole events are untimed (Barcelona, Munich, Houston; ten events in 2025), so presence follows surface and season. Pair the column with counts.
  3. **Mislinks:** about 0.5% of ManTennisData rows, and the quarterfinal label.
  4. **Stage 0 gaps:** the 67 women's frame matches with other ids; RG 2026 women's qualifying (224 rows) and 2026 Challenger qualifying (430) are not in Stage 0.
  5. **AO 2026's +0.5 floor** rests on 10 player-matches.
* **Schema (R3)** (*suggestion*): `data/studies/serve_speed_tabpfn/speed_panel.parquet`, built by `src/eda/serve_speed_tabpfn/panel.py`, tested in `test/serve_speed_tabpfn/test_panel.py`. One row per rebuilt (`match_id`, `side`); dropped rows stay with `use = False`.
  * Keys: `match_id`, `side`, `player_id`, `opp_id`, `tour`, `year`, `level`, `qualifying`, `lgroup`, `round`, `round_order`, `tournament_id`, `tournament_name`, `tournament_date`, `surface`, `indoor`, `slam`, `event`, `edition`, `family`.
  * Clock: `es`, `lf`, `obs`, `rel` (= `lf + 1`), `exact`.
  * Provenance: `source`, `basis`, `alt_sources`, `n_sources`, `max_alt_diff`.
  * Values: `spd1`, `spd1_raw`, `spd1_pts`, `spd1_ks`, `n1`, `f1`, `timed_share`, `spd1_sd_within`, `spd2`, `n2`, `spd_max`, `max_basis`, `fault1`, `nfault1`.
  * Flags: `use`, `drop_reason`, `flag_own_outlier`, `off_frozen23`.
  * The module also exposes `EditionOffsets.at(day, tour)` and `window_sums(targets, centring)`, and writes `speed_frame_keys.parquet`: frame id → rebuilt id, the frame's players, `es`/`obs`, an id-conflict flag.

## 13. Claims checked on disk

Scripts are in `src/eda/serve_speed_tabpfn/design/`; outputs in `data/studies/serve_speed_tabpfn/design/`.

| Script | What it checks | Output |
|---|---|---|
| `engineer_records.py` | The sources | `engineer_records.parquet` |
| `engineer_overlap.py` | Overlap, agreement, rounding, mislinks | `engineer_overlap.json` |
| `engineer_basis.py`, `engineer_misc.py` | The ceiling rule and the tail; same-player Slam changes (§4); the coverage totals (§8) | `engineer_basis.json`, `engineer_misc.json` |
| `engineer_basis_ref.py` | The 72% | `engineer_basis_ref.json` |
| `engineer_panel0.py` | The draft panel | `engineer_panel0.parquet`, `engineer_panel0.json` |
| `engineer_systems.py` | Offsets, AO 2024, event components | `engineer_systems.json`, `engineer_editions.csv` |
| `engineer_asof.py` | As-of learning, the centring comparison | `engineer_asof.json` |
| `engineer_noise.py` | §5 | `engineer_noise.json` |
| `engineer_clock.py` | §6 | `engineer_clock.json` |
| `engineer_coverage.py [--flashscore]` | §7, §8, N2 validation | `engineer_coverage*.json`, `engineer_coverage_frame*.csv`, `engineer_frame_sides.parquet` |


## 14. Looks

| # | Seasons | Look | Why |
|---|---|---|---|
| 1 | 2021–2023 | **Statistic target:** each player's same-season leave-one-out median first-serve speed, against KS − 0.5 and the point mean, on 524 player-matches where they disagree by more than 3 km/h (`engineer_basis_ref.py`) | The source choice |
| 2 | 2011–2026 | **Speed against speed only:** player × season / edition fits, same-player changes between editions, as-of learning curves, centring comparisons. 2024–26 are used as values and distributions; nothing is frozen from 2024 on | System offsets |
| 3 | 2013–2026 | **Counts only:** presence on the frame and on Stage 0 | Coverage |

No speed value was related to `a_won`, the winner, sets, games, closing odds or any price.
