# Audit, round 3: final adjudication and build list

Auditor, 6 Oct 2026. Units: mLL; **positive = model (or the feature) better**; "tie" when the 95% interval spans 0.

## Evidence used (observed)

**I1 discovery, 2015–21** (`data/studies/point_sequence/diag_edge_split.csv`):
* Overall: +0.55 [+0.05, +1.05], model better.
* Every contrast is a tie; Holm p ≥ 0.70.
  * C1 first-at-event minus later round: −0.39.
  * C2 rest > 7 days minus ≤ 1 day: +0.07 [−1.69, +1.75].
  * C4 early rounds minus R16+: −0.74.
* The 2022–24 "cold-start" directions (C1 +0.92, C2 +1.95, C4 +0.61) **flip sign or vanish** in discovery.
* The one nominal 2022–24 contrast is C5, Slams minus others: +1.71 [+0.15, +3.18], Holm 0.22, discovery +0.24. A tie.
* **The edge is roughly uniform across previous-match states.**

**Unified table, first build** (`coverage_model.csv`):
* **Men:**
  * own-sequence coverage 0.73 (2016) to 0.98 (2025);
  * median earlier sequenced matches 83 (2013) to 260 (2019);
  * both players with ≥ 20 such matches: 0.87–0.99.
* **Women:**
  * coverage 0.15 / 0.20 / 0.38 (2013–15), 0.61–0.78 (2016–18), 0.87–0.99 (2019–24);
  * median earlier sequenced matches 9 (2013) to 227 (2026);
  * both players with ≥ 20: 0.08 (2013), 0.50 (2016), 0.80–0.95 (2019–26).

## Decisions on the three questions

**(a) I1b is not built.** Its premise was a later-round or short-rest gap in the model's edge (reading A, with a "ceiling ≈ +0.4 mLL"). That premise rested on 2022–24 subsets that discovery does not reproduce. With no subset pattern there is nothing for the A/B/C decomposition to explain, and its natural experiments (qualifier, bye) lose their purpose. What survives:

* **D1 / A05 composite** (conversion luck): an optional one-hour residual screen against `p_base` (discovery 2015–21, replication 2022–24), only if time remains. Its components all tie given the market.
* **E3-lite (rest hours):** parked. Discovery C2 removes its new motivation. Day-level rest already ties: recovery context −0.07 / −0.24.
* **The price-only step** ("what the market uses beyond the no-odds model"): parked. It is interesting but has no decision value now.

**(b) Yes: the A1 outcome-free trait audit replaces I1b, and goes first.**

* It answers the owner's question directly: are momentum and streaks real, stable traits?
* It runs at a depth one to two orders of magnitude above the shot-level study's (median 4–58 qualifying games against 2,000–6,000 games now).
* It reads no match-winner outcomes, and its null is decisive.

**(c) What I still reject or amend in the rebuttal.**

* **B2's logic: I concede the correction.** σ²_pt = 0 ⇒ Δ = 0 is valid; my "logically wrong" was too strong. The gate is still useless, as the brainstormer agrees: non-stationarity makes σ²_pt > 0 certain. **B2 stays parked behind B1.**
* **Rejected: the reading-A ceiling (+0.4) and any item justified by it.** That covers F4/E3 "where the model is weakest", N2 subset shrinkage and N3 qualifier form. They rest on 2022–24 subset gains that came from the predecessor and `elo_off` arms and do not replicate.
* **D1:** "the composite was never tested" is true, but it does not earn a slot (above). Note that discovery now leans the *opposite* way to 2022–24 (later rounds +1.03 against early +0.29, a tie). I1 neither supports nor contradicts reading A′.
* **E1, "dilution cannot create a false positive":** true for M1. It is not true for a market screen: treated players who continue are a selected group. **The toilet control and the propensity model are mandatory there too.**
* **E1, "use every logged pair at any next-match level":** accepted for M1 (results exist at any level). M2 needs the next match's serve points, so it is restricted to next matches with a box score or a sequence.

## Final build list (CPU; a GPU arm only after a gate *and* a residual screen pass, trained and scored on ≤ 2024 only)

### 1. A1-T: momentum and streak traits at full depth (outcome-free)

* **Exposures:** five statistics per player-match, from `sequences.parquet`. Complete replays agreeing with the official score; ≤ 2024; retirements excluded. Each is an *excess* within the match, so the player's level that day cancels:
  * **S1** hold after breaking, minus the hold rate in the player's other service games;
  * **S2** break back after being broken, minus the break rate in other return games;
  * **S3** serve-point serial dependence by score state: won after won, minus won after lost, within games, with score-state fixed effects;
  * **S4** overdispersion of serve points across service games (D − 1), plus a runs z-score per server block;
  * **S5** set-to-set swing: overdispersion of per-set serve-point rates.
* **Endpoint (no match outcomes):** split-half reliability across players (50 random splits) at ≥ 20 and ≥ 50 matches per half; ρ² of the shrunk 52-week value against the career truth (≤ 2024) by depth quartile; correlation with the player's hold or break rate.
* **Data and windows:** the unified table, ≤ 2024. Men from 2013; women from 2016 (dense from 2019). K by empirical Bayes on ≤ 2018.
* **Benchmark and placebo:** the identical pipeline on 3 iid replays per match at de-noised day rates (priors frozen ≤ 2018). This fixes the finite-sequence streak bias and the stopping rule. The placebo statistic is "hold after holding", which must sit on the replay.
* **Pass** (per statistic × tour; Holm over 10): real r − replay r ≥ 0.10, with a player-bootstrap interval excluding 0, at ≥ 20 matches per half; and |r with hold or break rate| < 0.3.
* **If it passes:** a residual screen against `p_base` (discovery 2015–21, replication 2022–24). Then, only if that passes, a planted-edge check and one TabPFN arm on the 58-input frame, ≤ 2024.
* **A null closes** momentum, streak and pressure-reaction as stable player traits, at full depth: within-match dynamics may exist (Stage C), but players do not differ in them measurably. With it go B3, B5 and C1–C3 as pre-match traits. What remains is the in-play question (G2) and state carry-over (item 3).

### 2. E1 mechanism gate, with the women's fade markers (the brainstormer's F2, amended)

* **Exposure:** TREATED (MedicalTreatment, treatment in progress, or a physio call not cancelled) in the player's previous logged match within 21 days. INJURY (Injury, Illness or Heat) nested in it. Three states; unlogged pairs excluded.
* **Endpoints:**
  * **M1**, next-match retirement or walkover-out, at any level;
  * **M2**, next-match serve-point residual (binomial against `stage3_ratings` p_serve), where a box score or sequence exists.
* **Data and windows:** WTA event log; discovery 4 Jun 2019 – 2021; replication 2022–24. 2025–26 counts only.
* **Adjustment:**
  * the previous match's minutes decile, its result and the days since;
  * surface and age;
  * a propensity score fitted ≤ 2021.
* **Pass** (Holm over {TREATED, INJURY} × {M1, M2}): risk ratio ≥ 1.5, or M2 ≤ −0.5 pp, significant in discovery with the same sign in replication, **and the toilet-break control null on both**.
* **Placebo:** TREATED permuted within season × previous result × minutes decile; the opponent's flag as a mirror.
* **Secondary family** (k = 3, its own Holm): first-serve-in, double-fault and tempo fade slopes, against M2, as a difference in differences against the match before.
* **A null closes** medical and distress events as a pre-match signal, together with E1's market and G1 tests. G3 is downgraded, and the women's fade markers are closed as state signals.

### 3. B1: finishing-form carry-over, difference in differences on triples

* **Exposure:** in match t, the LATE minus EARLY serve-point residual, against pre-match p_serve:
  * LATE = set 2 in best of three, set 3 in best of five;
  * EARLY = set 1.
* **Endpoint:** serve points won in t+1, binomial, with offset at its own p_serve, plus box-score form and the day gap. Reverse: the same for t−1, on the **same triples**.
* **Statistic:** Δ = [β_LATE − β_EARLY] forward − [same] reverse, clustered by player.
* **Data and windows:**
  * triples of consecutive completed matches of one player at one event, each gap ≤ 3 days;
  * discovery ≤ 2021 from the unified table: Sackmann strings (men 2013 – Jan 2017), marcosjn2, the Slam point sequences and the WTA log from June 2019;
  * replication 2022–24.
* **Placebos:**
  1. the pipeline on iid replays of match t, where Δ's null must centre on 0;
  2. EARLY and LATE swapped at random.
* **Secondary:** fade by gap length (1 against 3 days).
* **Pass:** Δ > 0 with the interval excluding 0 in discovery, the replay placebo inside its null, and the same sign in replication.
* **A null closes** carry-over of finishing form across matches (B1, and B2 with it) as a pre-match state signal. Momentum is then an in-play question only.

### 4. I2: the women's points-share anomaly (sharing item 1's replays)

* **Exposure and endpoint:** the cross-validated log loss of the winner on the points share (and on the iid plug-in chance), real minus replay.
* **Data:**
  * women: WTA log, non-Slam, June 2019 – 2024;
  * men's control: the unified table ≤ 2024.
* **Replay variants:** true variance × 0.5, 1 and 1.5; per player-season rates.
* **Pass:** the women's gap (Stage 2: 0.118 against 0.103) excludes 0 under every variant, while the men's covers 0.
* **Negative control:** men.
* **A null closes** the anomaly as evidence of streakiness (it came from box-score error or replay misspecification), and parks B3 for women. A pass, read together with item 1's S5, says whether within-match swings are real and whether they are player traits.

## Not this session

* D1 / A05 (an optional one-hour screen).
* E3, E2-men, I1b, N2–N4.
* B2–B7, C1–C4 beyond item 1's statistics.
* G1: only for a feature that passes a gate.
* **The G2 price-only pilot is the first item next session.**
* Acquisition leads unchanged from round 2. First among them: recording Polymarket order books, and the PMXT archive for in-play costs.
