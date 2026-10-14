# Pre-registration: five lead groups of new statistics against the 2025–26 closing line

**FROZEN on 13 Oct 2026 at 13:08 PDT** (§ 14). Any change from here on follows § 11 and is logged in the process log with old and new hashes.

13 Oct 2026 · Study: [unpriced leads](README.md) · Process log: [process_log.md](process_log.md) · Kept by Claude Opus 5.5 (`claude-opus-5-5`), session `e1ffc84e-fa2d-42f9-9d17-7c936a046c45` · Revised before the freeze on the [red team's findings](team/red_team.md)

This file fixes, before any 2025–26 result of these statistics exists, what will be tested, on which matches, with which code, and what each outcome means. It is binding on whoever runs the looks. **A look runs only on the owner's go.**

## 1. The question and the hypotheses

**The owner's question** (13 Oct 2026): which new statistics predict outcomes, are not priced into the 2025–26 closing line of BetOnline and Pinnacle, and are not directly in the current best TabPFN model?

**Registered hypotheses.** For each score below, the hypothesis is that its coefficient β beyond the close (§ 6) is **positive**, every member oriented to its registered direction:
* **H0, the primary:** the omnibus score, the five groups together.
* **H1–H5:** each group's score. They are tested only at a look where H0 is confirmed (gatekeeping, § 6).

## 2. What had been seen when this was written

* **Discovery read seasons 2013–2024 only.** About 100 newly built statistics (luck 44 with variants, rhythm 37, market 13, the lead's 4) and 340 feature-pool columns were screened against the close by era, each as built and as its orthogonal part (§ 4). The groups were chosen from those readings ([process log](process_log.md), "Synthesis 2"; revised on the red team's M4). Expect shrinkage: they are the best of many.
* **No outcome from season 2025 on, and no 2025+ line move, was read for any registered statistic by this study.**
  * The harness that reads outcomes filters seasons ≤ 2024 inside the read and asserts it.
  * The 2025–26 values of the statistics were computed (they use only earlier matches' facts); only their presence and the gate's input counts were read.
  * The red team checked every code path and values file.
* **Known before, related to these statistics:**
  * the edge-anatomy study's 2025–26 ledger of the model's own inputs (the schedule family unpriced; men's serving over-rated, returning under-rated);
  * the market-anchoring study's men's hold and break luck (365-day, uncalibrated), read on 2019–2025 (−0.01 mLL, unresolved) and on 2026 to 2 Aug 2026 (+0.28, unresolved). Those 2026 readings include **36 matches dated 29 Jul – 2 Aug 2026, inside Look B**. Its statistic correlates 0.39 with G1's score on Look A's men's matches (outcome-free);
  * the predictability diagnostic's Stage 4 sentence on the raw tiebreak record given Elo, pooled over 2013–2026; close-set luck correlates 0.83 with tiebreak luck;
  * earlier 2025–26 tests of rust after a break (feature interactions) and of pair strength.

  The registered scores are each statistic's part orthogonal to the model's inputs, re-projected inside each look's window (§ 4). So what was known about the model's own inputs cannot fix these readings linearly.
* **The 136 season-2025 matches dated late December 2024 belong to Look A** (1.6% of it). Their results were read in two places, never against a registered statistic:
  * inside the market builder's record-against-the-close statistic (not registered);
  * loaded but unused by the harness before its season filter was added.

  They stay in Look A.
* **The sealed matches** (from 29 Jul 2026): no outcome was read. Three agents printed outcome-free counts or summaries that included sealed rows (the point-structure analyst, the market builder, the pool rebuilder; all disclosed in the log).

## 3. The five groups

Every member is a difference between the two players (A − B) built from matches that surely finished before the match it describes. Signs: − means the player higher on the statistic is expected to do worse than the close.

**Columns of the tables:**
* **Discovery z:** the member's oriented score (its orthogonal part, signed so that + is the registered direction) beyond the close with the registered base, both tours, seasons 2013–2024; then the four eras (2013–16, 2017–19, 2020–22, 2023–24). Source: `data/studies/unpriced_leads/registration/discovery_registered.csv`.
* **Non-zero in Look A:** the share of Look A matches where the A − B value is not 0, men / women (`registration/member_coverage.csv`).
* **Gate:** the input series of the completeness gate (§ 5).

The values files and columns are in the registry, with their SHA-256.

### G1. Luck read as skill: break points, close sets and flattering scorelines

* **What it is:** each player's recent scoring luck, from his own box scores at every level: results beyond what his serve and return points imply. Each per-match residual is against an iid point model calibrated once on 2010–12 matches, summed over earlier matches with a 91-day half-life. Built by `src/eda/unpriced_leads/build_luck.py`.
* **Why the close would miss it:** results, scorelines, rankings and results-based ratings carry this luck as skill.
  * Given point-based skill, the close loads positively on it in 8 of 8 tour-eras (2013–24).
  * The luck does not persist (split-half correlation ≤ 0.09, against 0.6–0.7 for the serve-point rate).
* **Exposure to 2025–26:** partly.
  * The break-point idea was prompted by the edge-anatomy study's 2025–26 finding that men's break-point saving is over-rated.
  * A relative was read by the market-anchoring study (§ 2).
  * Retirements carry part of the discovery signal (3.85 → 3.34 without them): a completed-matches reading is registered (§ 7).

| Member | Column | Sign | Gate | Discovery z (eras) | Non-zero in Look A |
|---|---|---|---|---|---|
| Net break-point luck: saves and conversions beyond the serve and return point rates | `PS03_net` | − | box scores | +1.93 (+0.03, +1.63, +2.69, +0.06) | 1.00 / 1.00 |
| Close-set luck: sets from 5–5 won beyond expectation | `PS06_close` | − | box scores | +1.86 (+0.23, +2.91, +1.46, −0.09) | 1.00 / 1.00 |
| A flattering last scoreline: games share beyond points share | `PS04_flat` | − | box scores | +2.55 (+1.97, +1.05, +1.01, +0.84) | 0.98 / 0.97 |
| **The group's score** | | | | **+3.85** (+1.43, +3.04, +2.69, +0.52) | |

### G2. The post-Slam letdown

* **What it is:** the player reached a Grand Slam quarter-final or better at another event, finishing at most 21 days before this match could start. Pool feature U-284, rebuilt on the current tables by `src/eda/unpriced_leads/rebuild_pool.py` with the original builder (`f19_motiv`).
* **Why the close would miss it:** a deep Slam run leaves a player tired or flat in the following weeks, while prices credit the Slam form.
  * The model does not use it (beyond the instance's forecast, 2020–24, the group reads +2.19).
  * The line does not move toward it before the close.
* **Exposure to 2025–26:** none.

| Member | Column | Sign | Gate | Discovery z (eras) | Non-zero in Look A |
|---|---|---|---|---|---|
| Reached a Slam QF or better elsewhere within 21 days | `rb__fi__B-MOTIV__post_slam` | − | none | +3.61 (+2.52, +1.78, +1.89, +0.87) | 0.024 / 0.019 |

Women +3.36, men +1.35.

### G3. Fast courts amplify big servers

* **What it is:** the venue's pace, estimated without leakage from aces at its earlier editions and this edition's earlier days (a cross-player statistic on the match clock), times the gap between the two players' ace offence. Pool feature U-254, rebuilt by `rebuild_pool.py` with the original builder (`f09_venue`). The venue-pace cut check leaves every earlier match unchanged.
* **Why the close would miss it:** the close applies a damped serve-dominance scaling in general and learns a venue's pace slowly.
* **Exposure to 2025–26:** none.

| Member | Column | Sign | Gate | Discovery z (eras) | Non-zero in Look A |
|---|---|---|---|---|---|
| Venue pace × the ace-offence gap | `rb__fi__B-VENUE__f09_venue_pace_x_ace` | + | none | +3.46 (+2.35, +0.94, +2.39, +1.43) | 1.00 / 1.00 |

Women +4.24, men +1.15. The weather, altitude and court-pace extension is H6 (§ 12).

### G4. Status over-priced, low-visibility form under-priced

* **What it is:** pool features rebuilt by `rebuild_pool.py`:
  * the share of a player's last-year matches below the main tour (U-330);
  * having recent form earned in low-visibility matches (U-261, its indicator, which the level layer does not move);
  * being seeded (U-175);
  * fame (U-177).
* **Why the close would miss it:** prices lean on reputation and visible results; form earned at lower levels or out of view is under-weighted. BetOnline's line moves *away* from lower-level arrivals before the close (move z −2.3, 2018–24), so the crowd's bias survives to the close.
* **Exposure to 2025–26:** none for these members. Ranking points (U-172), which a study had related to 2025–26, are left out for that reason.
* **Women's lower-level history in Look A.** Stage 0 holds no women's ITF qualifying from 2025 (16,684 matches in 2024, 0 in 2025), and every lower level falls away from June 2026. The completeness gate (§ 5) therefore sets the two lower-level members to missing for 69% of Look A's women's matches and 11% of the men's. There, G4 is the mean of seeded and fame.

| Member | Column | Sign | Gate | Discovery z (eras) | Non-zero in Look A |
|---|---|---|---|---|---|
| Share of last year's matches below the main tour | `rb__el__low_share_diff` | + | lower levels | +2.63 (+1.02, +1.50, +0.89, +2.14) | 0.91 / 0.91 |
| Has recent form earned where nobody watches | `rb__fp__f12_salience__hasL_a-b` | + | lower levels | +3.08 (+0.45, +1.96, +2.66, +1.75) | 0.45 / 0.44 |
| Seeded | `rb__pp__seeded_a-b` | − | none | +3.33 (+0.61, +3.37, +1.73, +1.19) | 0.51 / 0.50 |
| Fame: titles and Slam quarter-finals since 2010 | `rb__fp__f14_anchor__fame_a-b` | − | none | +2.98 (+0.48, +2.53, +1.75, +1.13) | 0.81 / 0.82 |
| **The group's score** | | | | **+4.22** (+0.97, +3.06, +2.38, +2.25) | |

Fame's scale drifts upward over the seasons (it counts titles from 2010; the red team's m5). The window-internal scaling of § 4 keeps its weight in the group equal.

### G5. Rhythm the singles record misses

* **What it is:** match play and recovery that a singles record and a day count cannot see. Built by `src/eda/unpriced_leads/build_rhythm.py` (doubles, rest) and `rebuild_pool.py` (past fatigue, U-143).
* **Why the close would miss it:** prices count singles results and days.
  * Doubles results live in another feed and market; the line does not move toward that member, and its signal sits in fresh lines.
  * Sleep after a late finish is measured in hours.
* **Exposure to 2025–26:** partly. The lens was prompted by the edge-anatomy study's 2025–26 finding that the schedule family is unpriced. The members themselves were never read on 2025–26.
* **Dropped before the freeze** (the red team's M4): the bye seed's cold start (`rb14_cold28`). It read z 0.12 on 2020–24, the line learns it, it is 54% predictable from context and price, and it overlaps G4's `seeded`. It is reported as a member-level secondary only (discovery +2.58).

| Member | Column | Sign | Gate | Discovery z (eras) | Non-zero in Look A |
|---|---|---|---|---|---|
| Doubles played at other events in the previous 7 days (2018 on in discovery) | `rb01_d7_else` | + | doubles rows | +2.87 (—, +1.93, +2.38, +0.69) | 0.09 / 0.15 |
| Rest under 20 hours since the previous match ended | `rb03_lt20` | − | presence | +2.61 (+2.02, +1.04, +0.47, +1.40) | 0.04 / 0.05 |
| Past fatigue: recent match load over 14 days | `rb__fp__f28_state__bdst_pastfat_a-b` | + | presence | +1.84 (−0.29, +1.23, +0.34, +2.99) | 0.83 / 0.78 |
| **The group's score** | | | | **+3.99** (+1.29, +2.40, +1.92, +2.27) | |

### The omnibus score

The mean of the five group scores, each scaled to unit RMS:
* discovery z **+8.76** (eras +4.44, +5.18, +5.48, +2.81);
* β +0.086 log-odds per SD.

The group scores correlate at most 0.084 with each other in discovery and 0.12 on Look A (outcome-free; the red team). Fitted jointly, each keeps its z.

## 4. The scores

* **A member's value** is the registered column, built by the registered code.
  * For Look A, the values were built on the repository's 8 Oct Stage 0 and the 12 Oct match clock, with the instance's own surface IOS and Stage B for the pool members (frozen extracts, `candidates/pool_rebuilt/inputs/`).
  * For Look B, on the tables of the instance current then (§ 9).
* **The completeness gate** (§ 5) sets a member to missing for a tour and month where its inputs collapsed.
* **Its score (the primary):** the value re-projected on the look window's own matches is the value minus its least-squares projection on the model's 48 non-price, non-context inputs (A − B; missing inputs 0), by tour, without an intercept, fitted on the rows where the value is present.
  * This reads no outcome.
  * The re-projected value is scaled to unit RMS in the window by tour and signed; a missing value counts 0.
* **A group's score:** the mean of its members' scores over the members the gate leaves active for that match (0 if none).
* **The omnibus score:** the mean of the five groups' scores, each scaled to unit RMS in the window.
* **The frozen-projection score** (a secondary): the same with the projections and scales fitted on seasons ≤ 2024, frozen in the registry.
* **The 48 inputs** are those of the current best model's template of 13 Oct 2026 (`template_2026-10-10/model_inputs.json`), built by the decided chain on the look's tables. The code asserts their order.

## 5. The completeness gate

* **The rule** (outcome-free, before any fit): for each member, tour and calendar month of the window, compare the member's input count over the month and its two neighbours with the same three months a year earlier. Below 70%, the member is missing for that tour and month. A month whose year-earlier count is 0 passes.
* **The inputs:**
  * **lower levels:** Stage 0's qualifying, Challenger, WTA 125 and ITF matches;
  * **box scores:** Stage 0's matches with a box score, every level;
  * **doubles rows:** TennisLive's played doubles;
  * **presence:** the member's own presence among the frame's matches;
  * **none:** main-tour facts.
* **Calibrated outcome-free** on 2023–26 counts. Normal three-month variation stays at 0.76 or above. The women's ITF qualifying lost from 2025 (0.48–0.66) and the lower levels lost from June 2026 (0.0–0.56) fall below.
* **Its effect on Look A, computed now** (`registration/gate_lookA.json`):
  * G1's members are off in June–July 2026 (11% of matches);
  * G4's lower-level members are off for 11% of men's and 69% of women's matches;
  * nothing else is gated.

## 6. The test

* **Matches:** the frame of the look's instance (main tour, both tours, debut seasons out).
* **The price:** the frame's odds input `p_mkt`, margin-free: Pinnacle's close to 7 Sep 2025, BetOnline's closing line after, the books' average where neither prices a match. L = its log-odds.
* **The fit:** logistic, no intercept: logit P(A wins) = s_atp·L·1[men] + s_wta·L·1[women] + k_atp·L|L|·1[men] + k_wta·L|L|·1[women] + β·s. Every coefficient is fitted in the window. The curvature terms keep a score from borrowing the price's favourite–longshot shape.
* **Uncertainty:** cluster-robust over four-week blocks; one-sided p from t on G − 1 degrees of freedom.
* **The two looks** (Bonferroni across them: an overall error rate of 0.05 for H0–H5 together):
  * **Look A:** H0 is confirmed if its one-sided p ≤ 0.02. Only then are H1–H5 tested, with Holm at 0.02.
  * **The final, read with Look B** (only if H0 was not confirmed at Look A): the two looks' combined z,
    z_AB = (√I_A·z_A + √I_B·z_B) / √(I_A + I_B), with z = Φ⁻¹(1 − p) and I = the window's sum of p(1 − p) of the close.
    * It confirms H0 at one-sided 0.03.
    * Only then are H1–H5 tested on their combined z's, with Holm at 0.03.
  * **Look B alone** is reported without verdict words. If H0 was confirmed at Look A, Look B is a replication reading.
* **Readings reported for every score:**
  * β per SD of the score in the window, its z, the one-sided p (Holm-adjusted for H1–H5);
  * P(β > 0) under a flat prior;
  * the realisation ratio (β per SD in the window over β per SD on 2013–24) with its SE;
  * the in-window gain in mLL.

**Verdict words** (these alone; "tie" is never used):
* **confirmed:** the one-sided p (Holm-adjusted for H1–H5) is at or below the look's level;
* **contrary:** the one-sided p in the other direction, adjusted the same way, is at or below that level;
* **unresolved:** otherwise, with P(β > 0);
* **not tested:** H1–H5 at a look where H0 is not confirmed. Their readings are still reported.

## 7. Secondary readings (registered; no verdict words)

For the omnibus and each group:
* **beyond the close and the model's 48 inputs** (per tour, fitted in the window). A confirmation that vanishes under it is reported as "re-finding in-model information";
* the frozen-projection score;
* the raw score (values not orthogonalised);
* the base without curvature;
* beyond the current instance's both-stages forecast (where that forecast exists: Look A yes; Look B only if forecasts are built for its matches);
* each tour;
* the Pinnacle and BetOnline periods of the odds input;
* BetOnline's own close as the base, on all matches and split by a fresh last line (stamped within 60 minutes of the listed start, or after it) or a stale one;
* Pinnacle's own close as the base where it exists (to 7 Sep 2025; none in Look B unless bought);
* **completed matches only:** retirements out, the settlement reading;
* Look A before the 2026 lower-level data gap (women before 18 May 2026, men before 29 Jun 2026);
* BetOnline's open-to-close move on the score (outcome-free: does the market learn it before the close?);
* an empirical-Bayes P(β > 0) with a prior N(k·b, (k·b)²), k = 0.45 (the screened universe's realisation, from the red team's cross-era check), b the discovery β per SD;
* each member alone; the bye seed's cold start as a member-level secondary.

## 8. What the looks can see

* **Resolution** (outcome-free, `resolution.json`):
  * Look A's SE of a unit-RMS score's β is ≈ 0.026 log-odds;
  * Look B's, at about 5,100 matches, ≈ 0.033;
  * the two combined ≈ 0.021.
* **The realisation to expect.** Across the 380 screened orthogonal parts, a statistic's 2013–19 z predicts its 2020–24 z with a reliability of about 0.45 (the red team's m1). So the 2025–26 β is expected to be about 0.45 of the discovery β, before any market learning.

**Power of the registered design** (`registration/power.json`; t on 20 degrees of freedom at Look A):

| Score | Discovery β per SD (z) | Realisation 1: at A / by the final | 0.5 | 0.45 | 0.25 |
|---|---|---|---|---|---|
| **Omnibus (H0)** | 0.086 (+8.76) | 0.87 / 0.99 | 0.29 / 0.60 | **0.24 / 0.52** | 0.09 / 0.22 |
| G1 luck | 0.033 (+3.85) | 0.18 / 0.41 | 0.06 / 0.16 | 0.05 / 0.14 | 0.03 / 0.08 |
| G2 letdown | 0.036 (+3.61) | 0.21 / 0.47 | 0.07 / 0.17 | 0.06 / 0.15 | 0.03 / 0.08 |
| G3 fast courts × big servers | 0.035 (+3.46) | 0.19 / 0.44 | 0.06 / 0.16 | 0.06 / 0.15 | 0.03 / 0.08 |
| G4 status | 0.046 (+4.22) | 0.34 / 0.66 | 0.10 / 0.24 | 0.08 / 0.21 | 0.04 / 0.11 |
| G5 rhythm | 0.039 (+3.99) | 0.25 / 0.53 | 0.07 / 0.19 | 0.06 / 0.17 | 0.03 / 0.09 |

* The group figures ignore the gatekeeping (it can only lower them) and G4's gating of women (§ 5).
* **For comparison:**
  * a single confirmatory Look A at 0.05 would give the omnibus 0.41 at a realisation of 0.45;
  * the red team's boundaries (2.50 at A, 1.66 at the final) would give about 0.17 and 0.61.
* **The choice of 0.02 / 0.03** spends part of the error rate on an early answer, because the owner asked about 2025–26.
* **What to expect:** at the realisation the data predict, **Look A confirms H0 about a quarter of the time, and the final about half.** Single groups are unlikely to be confirmed on their own. Their readings (β, P(β > 0), the realisation ratio, the empirical-Bayes probability) are the evidence a later selection round weighs.
* **Dry runs** of this code on 2023–24 (a discovery window, in-sample) read the omnibus at z +2.75: even in-sample, a window of Look A's size is small for effects of this size.

## 9. The windows

* **Look A:** seasons 2025 and 2026 with tournament date before 29 Jul 2026: 8,591 matches (men 4,394, women 4,197), including the 136 dated late December 2024. On the owner's go, once.
* **Look B:** tournament date from 29 Jul 2026 to 31 Jul 2027, about 5,100 matches by the 2024–25 calendar. Read once after those results are in:
  * on the frame of the instance current then (`registry_lookB.json`, § 13);
  * with every member's values recomputed by the registered code on that instance's tables;
  * through the completeness gate.
* **Look B needs data the repository has stopped holding.** Restoring the 2026 lower-level history (WTA 125, women's qualifying, the ITF) enters only as a candidate the owner accepts under the freeze rules. Without it, the gate switches the affected members off. The start-time and doubles feeds must keep running to July 2027.
* A look that cannot run as written is reported as such; any repair follows § 11.

## 10. What each outcome means

Nothing here changes the model or a stake by itself. "Confirmed" belongs to the score tested, never to members it did not test (the red team's B2).
* **H0 confirmed:** the five areas *together* carry information the 2025–26 close lacks.
  * Each member enters the feature pool as a lead ([feature universe](../feature_universe/README.md) § 9) with its own member reading and its group's verdict attached.
  * A group reading contrary is not admitted on the omnibus's strength.
  * The next step, the owner's call, is a candidate build (as model inputs or as a walk-forward nudge like the serve-speed stage), compared on both stages with `compare.py`.
* **A group confirmed (Holm, after H0):** its members enter the pool as leads confirmed on 2025–26 *as a group*.
* **Unresolved:** the members stay leads; the final reads them again; their estimates go to the next selection round.
* **Contrary:** not admitted; recorded in the adoption framework's class record as evidence that the 2025–26 close prices it, or that the discovery reading was luck.
* **The realisation ratio** says how much of the 2013–24 effect per SD is left in 2025–26: near 1, unpriced and stable; near 0, learned by the market or never real.

## 11. Deviations

* **Frozen:** the groups, members, signs, gates, the scoring, the windows, the base, the tests, the two looks' levels and the verdict rules.
* **Allowed before a look, each logged in the process log with the old and new hashes:**
  * a data repair whose need is found by outcome-free checks (a recording fault, a broken link), applied to every season alike;
  * a fix to a bug in `look.py` or a builder that does not change the specification, shown by a dry run on seasons 2023–2024 that reproduces the frozen dry run (`looks/dry-run/result.json`, § 14);
  * for Look B: pointing the builders and `look.py` at the instance current then (paths and hashes only), shown by reproducing Look A's values on the 10 Oct instance bit for bit.
* **Not allowed:** adding or dropping a member or group, changing a sign, a gate, a window, the base, a level or a rule.
* A look that departs from this file is reported with the departure named, and its verdicts are given as departing.

## 12. Registered now, outside H0–H5

Each has its own one-sided 0.05 and does not enter the omnibus. **If nothing is real, the chance of at least one false "confirmed" across H0–H5 (0.05), H6, H7 and H8 is about 0.19.**

**H6, conditions at the scheduled hour** (G3's extension; needs data the project does not hold).
* **Data, on the owner's choice of source:**
  * hourly ERA5 reanalysis at the venue (from Copernicus, or Open-Meteo's archive of it, whose free tier is non-commercial): wind speed at 10 m (km/h), temperature, dew point, shortwave radiation;
  * a venue table (coordinates, altitude, IANA time zone, from GeoNames or Wikidata).
* **The hour:** the scheduled start hour (local) and the two following hours, averaged.
* **Heat:** WBGT by Liljegren et al. (2008), outdoor method; H = max(0, WBGT − 25 °C).
* **Members:**
  * (a) wind × the price's slope, registered − (the price should be flatter in wind);
  * (b) wind × the ace-offence gap, registered − (the bigger server's edge shrinks);
  * (c) 1[venue altitude > 500 m] × the ace-offence gap, registered +;
  * (d) heat × acclimatisation, registered +: H, times the gap in each player's exposure Σ max(0, WBGT_j − 22)·e^(−days_j/7) over his matches of the previous 14 days.
  * Indoor matches carry 0 for (a), (b) and (d). The same columns built from the outdoor weather on indoor matches are the placebo.
* **Entry rule:** build on seasons ≤ 2024 with this study's harness and timing probe. A member enters H6 if its orthogonal part reads z ≥ 2 in its registered direction, with at least 3 of 4 eras of that sign, and its indoor placebo reads |z| < 2. If none enters, H6 is void.
* **Test:** H6's score (the mean of the members that enter) is tested on Look A once built (Look A is still unread for these statistics), then on Look B, with this file's scoring and base, at 0.02 and 0.03.

**H7, rust after a break, on Look B only.** Rust is already related to 2025–26 (the feature-interactions study's B-INJ test there was unresolved), so Look A is not clean for it.
* **The statistic:** the rust state (pool U-135, `fp__f26_impairment__bdinj_rust0`, A − B), registered −, with the lower-levels gate.
* **Registered:** its values from the store (`registration/h7_rust_store.parquet`) with a frozen projection and scales. At Look B it is rebuilt by the original builder on that instance's tables and checked against the store on seasons ≤ 2024.
* **Discovery:** z +3.09 oriented (eras +1.91, +1.35, +1.56, +1.37).
* **Test:** its score on Look B, one-sided 0.05.

**H8, Polymarket's informed flow, prospective only.**
* **The statistic:** the net stake toward A from wallets that clearly beat Polymarket's close, placed 48–6 hours before the listed start, over all stake in that window. Wallets are classified walk-forward, from markets settled before the window opens, with the `polymarket_sharp_money` study's rule.
* **Data:** recorded with the existing trade adapter from the day the owner, or a session he directs, schedules it. No match before that day is used.
* **Test:** once 3,000 main-tour matches with a classified flow have been recorded, beyond BetOnline's close and beyond Pinnacle's recorded live price (where it exists), one-sided +. About 350–570 such matches a month carry a Polymarket market in 2026.

**Partial-information candidates** (named now so a later registration can cite them; no test is registered):
* serve-speed extensions: second-serve speed, fault speed, the fade within the previous match (needs the ATP Stats Centre per-point files of 2025–26, approved);
* women's unforced-error state from the WTA's advanced statistics (2021–26 on disk; three discovery seasons);
* an edition's court pace from Hawk-Eye bounces;
* each player's own lower-level-to-tour translation ratio (an extension of G4);
* a women's lower-level share without ITF qualifying in every season (stable across the 2025 loss).

## 13. Code and commands

**Code** (in `src/eda/unpriced_leads/`; SHA-256 in the registry's `code_sha256`):
* `screen.py`: the harness. It reads outcomes, seasons ≤ 2024 only, and provides the orthogonal part, the timing probe and the long table.
* `build_luck.py`, `build_rhythm.py`, `rebuild_pool.py`: the members' values for every frame match, with no result column.
* `register.py`: builds `registry.json` (members, gates, frozen projections and scales, the instance's paths and hashes, H7), the discovery readings and the power.
* `gate_lookA.py`: the gate's effect on Look A, outcome-free.
* `look.py`: the looks. It checks every hash before reading.

**Commands:**
```
./python.sh src/eda/unpriced_leads/look.py --registry docs/studies/unpriced_leads/registry.json --dry-run
./python.sh src/eda/unpriced_leads/look.py --registry docs/studies/unpriced_leads/registry.json --look A --owner-go "<the owner's words>"
```

**Look B:**
1. Build the instance current then.
2. Rebuild every member's values with the three builders on its tables, written beside the Look A files as `values_lookB.parquet`, after showing that the parameterised builders reproduce Look A's values on the 10 Oct instance.
3. Write `registry_lookB.json`: `registry.json` with only the instance's paths and hashes, the values paths and hashes, and `look_b_end` changed. A check confirms every other field is identical.
4. Run `look.py --registry docs/studies/unpriced_leads/registry_lookB.json --look B --owner-go "<the owner's words>" --look-a-result data/studies/unpriced_leads/looks/A/result.json`.

## 14. Freeze

**Frozen on 13 Oct 2026 at 13:08 PDT**, before any outcome of seasons 2025–2026 or later was read for any registered statistic. This file's own SHA-256 is recorded in the [process log](process_log.md) (a file cannot hold its own hash) and in the README, § 9.

| What | SHA-256 |
|---|---|
| `docs/studies/unpriced_leads/registry.json` (holds the hashes of the frame, book prices, input list, forecast table, every values file and the code below) | `9364008c9058384a50ba7f504554dfd12c35992d8403de2bc899c9922d384a8a` |
| Code, from the registry: `screen.py` | `659a599066c4ffc5c6ba97ac5795f01f1ea87916de041544a96fd44c389ed209` |
| `look.py` | `4923f9bae3dfe8f833e7c608b417655c5f3ae674aa6d0429e23cfe8b4ef830f5` |
| `register.py` | `9fa5eeeb74e452a10db485770662d07476fe2e9b7481cabcab87a0a714844f61` |
| `build_luck.py` | `1286a62e25ca5db0ca51be92ddbb4c80a2e751c42b63a6c9fc6b609da4e74fd7` |
| `build_rhythm.py` | `980d39d65edc2a45d8eb4e325df1bcbedad56db25c802b5feb485819a7eb0bfb` |
| `rebuild_pool.py` | `e43a74316e2ba044f7b314970de53fc602b18395167434a753426e2ab22a9b7d` |
| `gate_lookA.py` | `0aa6b2ba803694054d0b82d0603aaccd5611b93101492bab4e59f984038e16b6` |
| Values files, from the registry: `candidates/luck/values.parquet` | `092d423ccca35474…` (full hash in the registry) |
| `candidates/rhythm/values.parquet` | `95b8da80d7be47e8…` |
| `candidates/pool_rebuilt/values.parquet` | `037bb2a060e73637…` |
| `registration/h7_rust_store.parquet` | `03669242e42934d99267230eeda4f50232ddcfa82f1dc77570369880944751fa` |
| `registration/discovery_registered.csv` (the discovery readings above) | `b0c6c38dbba81439a18c7501cb6b2da0ddb648bbee7749622b911d51a39b5f22` |
| `registration/power.json` | `58f55e5b790275de6d6d4a18435c8c0c9b799f925428975ff77deff3d2ed326b` |
| `registration/gate_lookA.json` (the gate's effect on Look A, outcome-free) | `832db29fad4b8fc90375d0e45a10338f0c732165ee598ec1c304ab2ce2827a96` |
| `registration/member_coverage.csv` | `0e6fe43bba0353aeac4f317043ca66527b3de784dcb90973447a52a09d6a758a` |
| `looks/dry-run/result.json` (the frozen dry run, seasons 2023–2024; § 11's reproduction reference) | `4300cbac4254235042a9e69ca1df92d5f531e9f6712c0342a3d19fe24c342819` |
| `resolution.json` | `78cf103c673c091e756477b58d30faddeac2c891833ada09f59f38d0bb096682` |

The instance read by Look A: `data/studies/current_best_model/template_2026-10-10/`; frame SHA-256 `038cc68ed1e92100…`, book prices `ca8a3f9e007fda74…`, input list `21375ea90efe6933…`, forecast table (edge_anatomy's `analysis.parquet`) `69b67a6bee62f625…`, all in full in the registry.

The repository is not committed by Claude. **Committing these files is the owner's step that fixes them in the git history.** Until then, the hashes above are the record.
