# Feature provenance: how much of the current best model was fit to the seasons it was tested on

8 October 2026 · Written for the owner and for the sessions that rebuild the model · A research audit and a proposed plan, not a decision.

The owner's questions (8 Oct 2026), before the actual model is built:
1. Which 58 inputs were selected, and by what process (reverse-engineered from the studies)?
2. How much of it was fitted to the current era and then tested on that same era? How overfitted are the features?
3. If the feature selection is rebuilt with a proper holdout, and these features stay in the pool it chooses from, how much leakage does their design carry?
4. A plan to estimate all this.

**How this was done.** Four independent read-only audits covered every study report, the decision records, the code that sets each constant, the look ledgers and the data on disk. Their findings were checked against the cited files. One new computation was made: the per-season edge of the current best model's stage 1 against the closing price, from the forecasts the earlier studies stored. It reads seasons up to 2024 only. No model was fitted and no result after 2024 was read.

**Labels.** *Observed* means read in a file or measured; *inferred* is a reading; *suggestion* is a proposal. Scores are in **mLL** (milli-log-loss per match). In every table **positive = the model, or the named input or arm, is better**, and a 95% interval that spans 0 is a **tie**.

The detailed estimation plan is in [plan.md](plan.md).

## In short

* **Observed. The 58 inputs** are listed in section 1: the closing odds, overall and surface-offset Elo with the surface switch pairs, games-weighted Elo, the serve/return ratings, three points-won aggregates, the 16-input two-week statistics profile, the 21-input long-memory surface IOS profile, load, age and six context columns. On top sits the walk-forward serve-speed adjustment, men only.

* **Observed. Numbers and choices differ in where they were fitted.**

  | Layer | What was fitted on the test seasons |
  |---|---|
  | **Numbers** (constants inside features) | Almost nothing. 57 of 58 inputs have every tuned constant fitted on 2013–2018 outcomes (2010–2018 for norms) or set by rule. The one exception is the short IOS memory (4 weeks men, 13 women). It was picked after reading results over all seasons, 2022–2026 included, although pre-2022 data pick the same memories. Stage 2's constants were set without results, and its coefficients are refitted walk-forward. |
  | **Choices** (which inputs, which representation, which memory, the calibration, stage 2) | All of it. Every one of the 58 inputs, and every one of the six changes since 2 Oct, was decided with 2022–2026 results in view, 2025–2026 included. About 20 study runs read those seasons in seven days. |
  | **Tests** | Every headline edge was measured on 2022–2026, or on 2024–2026 for stage 2. These are the seasons that informed the choices. |

* **Observed. For 19 of the 58 inputs, pre-2022 evidence alone would have made the same choice.** The other 39 owe their place, or the role claimed for them, to 2020+ results or to the owner's thesis:
  * **16 inputs** (the two-week profile) were candidates on early evidence, but "the closing-line lead" was positive only from 2020.
  * **21 inputs** (the surface IOS profile) had no pre-2022 linear case. They entered on the owner's per-statistic thesis and were kept on a no-odds criterion declared after the pre-registered test with the odds had tied.
  * **2 inputs** (age, age²) draw their value from 2020+.

* **Observed (new). The edge exists only from 2020, the seasons in which the selection found its market leads and read its tests.** These are the stored forecasts of the 58-input stage 1, with both the model and the close recalibrated walk-forward:

  | Seasons | Matches | Model vs recalibrated close (+ = model better) |
  |---|---:|---|
  | 2015–2019 | 22,802 | **+0.18 [−0.28, +0.64], a tie** |
  | 2020–2024 | 22,265 | **+1.46 [+0.84, +2.08], model better** |

  * Seasons 2015 to 2019 run −0.64 to +0.96.
  * The profile's market value appeared in 2020, and the features were selected with 2020+ results in view.
  * Three explanations fit, and the data so far cannot separate them:
    * the early models trained on fewer matches (10k in 2015, 50k in 2024);
    * a real change in the market or the data around 2020;
    * inputs chosen because they worked from 2020.

* **Inferred. How overfitted.**
  * **The fit itself is not the problem.** TabPFN learns nothing across seasons, the windows are walk-forward, and the constants predate 2019.
  * **The stage-1 refinements since 2 Oct cannot have inflated the closing-line edge much.** The surface IOS, the offset Elo and the calibration rule each tie at the close. A worst-case bound puts their combined effect at about 0.2 mLL, against a reported +1.2 to +1.3 (section 5).
  * **Stage 2 is the most exposed component relative to its size.** Its choices could account for up to about 0.3 of its +0.41 to +0.54. The underlying speed signal did replicate blind.
  * **The open question is the era.** The whole edge sits in 2020+, where the selection found its market leads and read its tests. That cannot be resolved from inside those seasons.

* **Inferred. The rebuild's leakage depends on where its holdout sits, not on the features alone.**
  * **Holdout no design ever saw** (matches after the frame, or men's 2005–2012): the design leak is zero by construction, even with all 58 in the pool. Any fit to the 2020–2026 era then shows up honestly as a smaller edge.
  * **Holdout inside 2013–Jul 2026, such as 2025–2026:** it inherits the whole selection bias of every choice made on a window that contains it, not a diluted share (section 6).

* **Observed. Untouched data is scarce** (section 7).
  * Of the 1,014 main-tour matches after the model frame (29 Jul – 30 Sep 2026), 787 were scored by earlier studies, though only without odds and never against the market. 227 are untouched, 82 of them with tennis-data odds.
  * Men's 2018 (2,639 matches) never entered a market test.
  * A men's backcast of 2005–2012 is feasible from disk once three odds files are downloaded.
  * New main-tour matches arrive at about 5,000 a year. Detecting a +1.3 edge with 80% power needs about 7,700.

* **Suggestion.**
  * **Seal the post-frame matches now.**
  * **Treat 2025–2026 as development, not as a holdout.**
  * **Run the plan's cheap diagnostics first:**
    * training size against era;
    * the decision bootstrap;
    * the hindsight replay at 2022.
  * **Let the sealed future, and optionally the backcast, decide.** Details and costs are in [plan.md](plan.md); the decisions for the owner are in section 9.

## 1. The 58 inputs

Every input is a difference A − B (negated when the players swap), except the two pairs (exchanged) and the context (unchanged). The list is `data/studies/surface_rating_race/model/model_inputs.json`; the frame is `model_frame.parquet` (63,737 matches, 2013 to 28 Jul 2026). The per-input ledger, with sources, is `data/studies/feature_provenance/provenance_58.csv`.

| Inputs | n | What it is | Constants fitted on | Same choice on pre-2022 evidence? | Group |
|---|---:|---|---|---|---|
| `odds_logit` | 1 | log-odds from the average of the books' closing odds, margin removed | rule | yes (standard practice) | A |
| `elo_overall`, `elo_surf_offset` | 2 | overall Elo; each player's surface offset, moving only on its surface with its own K | 2013–18 | yes. Elo-only 2019–21 men +4.50 [+2.06, +6.94]. The "useful before the close" premise cannot be tested before 2025 | A |
| `surf_season_a/_b`, `surf_layoff_a/_b` | 4 | log(1 + surface matches this season); log(1 + days since the last match on the surface), capped at 3 years | rules | yes. Linear 2016–21 without odds: season counts men +2.11, women +3.66 | A |
| `elo_games` | 1 | games-weighted Elo | 2013–18 | yes. Better than Elo in 2013–16, 2017–19 and 2020–21 | A |
| `ratings_iid` | 1 | serve/return ratings through the iid point model | 2013–18 | yes. Better than Elo in every era | A |
| `adjperf_tpw_2w` | 1 | opponent-adjusted total points won, 2-week half-life | 2013–18 | yes. +2.98 / +4.37 over Elo before 2022 | A |
| `ios_points_short` | 1 | IOS points matchup, 4-week (men) or 13-week (women) memory | κ, τ 2013–18. **The memory was picked on all seasons** | yes, the same memories | A |
| `points_52w` | 1 | 52-week points-won matchup | rule; 2010–18 reliability | yes. +1.04 / +2.48 over Elo | A |
| `sets_14d` | 1 | sets played in the last 14 days | rule | yes. +1.54 / +1.72 over Elo | A |
| `tour`, `surface`, `level`, `indoor`, `best_of`, `round` | 6 | match context; indoor is men only | rules | yes | A |
| `form_<12>`, `formdef_<4>` | 16 | two-week opponent-adjusted form on twelve statistics, and its defensive mirror on four | 2013–18 | **As a candidate, yes. As "the closing-line lead", no:** pooled 2013–21 about +0.25 over the odds (tie); by era −0.07, −0.01, then 2020–21 +1.49 | B |
| `iosO_/iosD_<7>`, `prod_<7>` | 21 | long-memory surface IOS offence and defence per statistic, and the matchup products | 2013–18 | **No linear case** (2013–21 −0.25; with products −0.41; ties). Kept on a no-odds criterion declared after the test with the odds tied | C |
| `age`, `age_sq` | 2 | age and squared age around 25 | rule | **Weak or absent.** Men +0.37 over Elo (2013–16 −1.10, worse); women +0.02 (tie). The value comes from 2020–21 (+4.19) and 2022–26 (+2.88) | D |

* **Gains in the "same choice" column** are against surface Elo refitted each season (+ = with the input better), except where "over the odds" is stated.
* **Stage 4/B/D intervals** assume independent matches and are too narrow. The pre-2022 pooled figures are match-weighted averages of each study's era rows.
* **Stage 2** (`provenance_stage2.csv`) is logit q = s_tour·η + b̃·`spd_L`:
  * **`spd_L`, the men's 28-day first-serve-speed form difference.** The filter constants were tuned on speeds of 2022 and earlier, against next-match speed rather than results. The value 28 was the arg-max of a result-free target. Its adoption followed two outcome runs on men's 2024–2026.
  * **b̃, the shrunk coefficient.** τ = 0.05 was pre-registered, and b̂ is refitted on 2019..Y−1.
  * **The slopes s_atp and s_wta** are refitted on 2019..Y−1. The need for them was found on 2022–2026.
  * **The TabPFN settings** (8 estimators, temperature 0.9) are the UFC project's settings and were never varied here.

## 2. How the set was built

| Date | Step | Results in view | Arms |
|---|---|---|---|
| 30 Sep | Stage 1 Elo: K and blend tuned on 2013–18. The owner picked surface Elo after seeing every window, 2022–26 included | 2013–26 | 4 |
| 1–2 Oct | Predictability diagnostic, Stage 4. 59 candidates planned **before any result**: 52 from a starting list, 7 from Stages 1–3's structural findings. Scored walk-forward over 2013–26, headline window 2022–26 | 2013–26 | 325 versions |
| 2 Oct | UFC ideas, Stages A–D, at the owner's request. adjperf, adjdef and IOS constants tuned in-sample on 2013–18, grids extended after hitting their edges. Short-IOS diagnostics added after reading all seasons. Stage D's profile became "the one lead against the odds": 0.92 in 2022–26, "positive in every season from 2020 on (and absent before)" | 2013–26 | 290 versions + 17 models |
| 2 Oct | Feature-alpha audit: the profile is the "main closing-line lead", and "the search was not fully held out". The repairs cut the profile to +0.355 [−0.251, +0.961], a tie | 2019–26 | ~20 specifications |
| 2 Oct | TabPFN-Thinking on 53 inputs: "the earlier studies' winners, chosen after their 2022–2026 results were seen". The deprioritised families were dropped; the IOS profile was kept despite a null linear result. Feeding the odds as an input was chosen from the free models' test-window scores | 2022–26 | ~30 forecasts |
| 5 Oct | Leak-proof IOS refit (a rule-driven fix; unchanged). The owner adopted "the best performing" model | 2022–26 | 1 |
| 6 Oct | Surface IOS kept by the owner (no-odds criterion, early betting) | 2019–21, 2022–26 | 5 arms ± odds |
| 6 Oct | Calibration: the need was found on 2022–26; slopes fitted on 2019–21; the walk-forward refit was added after the women's drift showed on 2022–26 | 2022–26 | 2–3 forms |
| 6 Oct | Offset Elo swapped in by the owner (no price 2022–26; 24 hours 2025–26). **The 58 inputs** | 2022–26, 2025–26 | 8 representations, 240 fits |
| 7 Oct | Serve-speed adjustment: a pre-registered secondary, adopted when the primary (a TabPFN column) tied | men 2024–26 | primary + 30 secondaries |
| 8 Oct | 28-day memory, adopted after two more outcome runs | men 2024–26 | 3 rules × 4 scenarios |

* **Forking paths, counted by the audits.**
  * **Rating and surface slot:** about 45 variants were scored on windows containing 2022–2026 before the swap. Eight representations competed inside TabPFN, under up to four price conditions.
  * **Profile, points and player slots:** they touch 218 of the predictability diagnostic's 325 rows and 282 of the UFC study's 324.
  * **Tuning-only runs saw only 2013–2018:** 21,600 adjperf fits, 1,152 IOS fits and 208 surface-IOS runs.
* **Men's 2024–2026 was read four times in about 24 hours for stage 2.** The base model's 2025–2026 forecasts were scored before the "one-shot" 2025–2026 tests, so those tests were one-shot for the candidates only.

## 3. What was fitted to the current era

* **Numbers: clean, with one exception (observed).**
  * Every tuned constant of 57 inputs used 2013–2018 outcomes, or 2010–2018 statistics, and no later outcome.
  * The grid extensions after edge hits also stayed on 2013–2018.
  * The exception is the short IOS memory, chosen on all-season results; 42% of the men's matches in that pool, and 69% of the women's, were from 2022–2026.
  * Git cannot date any of this. The repo has three commits, the last on 23 Sep 2026, before every feature study. Dates here come from the reports.
* **Choices: fully exposed (observed).**
  * The six changes that make today's model each read 2025–2026 results:
    * the 53 inputs, with the odds as an input;
    * the surface profile;
    * the calibration;
    * the offset Elo;
    * stage 2;
    * the 28-day memory.
  * The catalogue already flags all 58 incumbents as "seen on 2025–2026" (`feature_universe/universe.csv`).
* **Tests: fully on the same seasons (observed).**
  * The headlines:
    * +1.57 [+0.82, +2.32], men (Thinking, 53 inputs);
    * +1.18 [+0.54, +1.82] both tours and +1.66 [+0.92, +2.41] men (the 58-input stage 1, 16 seeds, 2022–26);
    * +2.20 [+1.10, +3.30], men 2024–26 (stage 1, in the speed study);
    * +0.41 [+0.04, +0.78] and +0.54 for stage 2 (men 2024–26).
  * All are on 2022–2026 or 2024–2026, against the recalibrated close (+ = model better).
* **Which decisions leaned on 2020+ (inferred):**
  * the profile's lead status;
  * age;
  * keeping the long-memory IOS profile, whose premise ("the group TabPFN leaned on most") was read off TabPFN's 2022–2026 outputs;
  * the "useful before the close" rationale of 6 Oct, which only 2025–2026 Polymarket prices can test. The decisive 24-hour figure (+0.78 [+0.03, +1.54]) used all 2,648 matches. On the 1,067 clean event openers that an earlier plan preferred, it ties: +0.88 [−0.38, +2.13].

## 4. The edge by season

Stage 1 of the current best model (local TabPFN-3.5, 58 inputs, trained on 2013..Y−1), seeds 0–2, debut seasons left out. Both the model and the close are recalibrated with one slope per tour, fitted on 2014..Y−1. Intervals are over four-week blocks. **+ = model better than the recalibrated close.** The source is `data/studies/feature_provenance/edge_by_season.csv`.

| Season | Training matches | Matches | Edge | Reading |
|---|---:|---:|---|---|
| 2015 | 10,051 | 5,113 | −0.37 [−1.96, +1.22] | tie |
| 2016 | 15,165 | 5,100 | −0.64 [−1.24, −0.03] | close better |
| 2017 | 20,266 | 5,096 | +0.43 [−0.52, +1.38] | tie |
| 2018 (women only) | 25,363 | 2,450 | +0.96 [−0.33, +2.24] | tie |
| 2019 | 27,813 | 5,043 | +0.92 [+0.02, +1.81] | model better |
| 2020 | 32,858 | 2,305 | +1.93 [−0.30, +4.16] | tie |
| 2021 | 35,163 | 4,753 | +1.87 [+0.04, +3.69] | model better |
| 2022 | 39,918 | 4,938 | +0.82 [−0.58, +2.22] | tie |
| 2023 | 44,863 | 5,135 | +1.39 [+0.29, +2.49] | model better |
| 2024 | 50,003 | 5,134 | +1.56 [+0.01, +3.11] | model better |

| Window | Both tours | Men | Women |
|---|---|---|---|
| 2015–2019 | +0.18 [−0.28, +0.64] tie | +0.12 [−0.80, +1.04] tie | +0.23 [−0.49, +0.94] tie |
| 2020–2021 | +1.89 [+0.59, +3.19] | +2.70 [+1.24, +4.15] | +0.98 [−0.66, +2.63] tie |
| 2022–2024 | +1.26 [+0.55, +1.97] | +1.23 [+0.37, +2.09] | +1.29 [+0.33, +2.26] |
| 2020–2024 | +1.46 [+0.84, +2.08] | +1.70 [+0.96, +2.44] | +1.20 [+0.39, +2.01] |

* **The other calibrations agree.** Averaging every stored seed (3 to 16 per season) gives +0.17 and +1.44. The decided rule (slopes on 2019..Y−1) gives +1.44 in 2020–2024. Uncalibrated, it is +0.00 against +1.65.
* **The reproduction check passes:** with slopes fitted on each window itself (`inwindow_s02`), the script gives +0.33 [−0.21, +0.88] on 2014–2021 and +1.30 [+0.58, +2.03] on 2022–2024, exactly the feature-interactions ledger's row 2.
* **Copied from the studies that computed them:**
  * 2025 and 2026, with the 2019–21 slope and three seeds: +1.19 and +2.35 for both tours; men +2.36 and +3.05.
  * Against calibrated Pinnacle: 2014–21 +0.21 [−0.37, +0.78] (a tie) and 2022–24 +1.06 [+0.27, +1.85].
* **Inferred. The edge appears around 2019–2020 and stays.** The candidate explanations, with what would test each, are:
  1. **Training size.** The context grew from 10k to 50k matches over the same years. The 2019 → 2020 step is small (28k → 33k), but the per-season intervals are wide. *Test: fixed-size refits (plan, phase 2).*
  2. **A change in the market or the data around 2020:** COVID-era schedules and layoffs, changes in the books' average, changes in box-score sources. The same step against Pinnacle argues against a quirk of the average. *Test: prospective seasons and the backcast (phases 5–6).*
  3. **Selection on the era.** The profile's market value, age's value and the long-memory IOS premise were all read on 2020+ seasons. *Test: the hindsight replay at 2022 (phase 4) and prospective seasons.*

  None of this is a verdict that the pre-2020 market was unbeatable. It is a process question with named suspects.

## 5. How overfitted

**What is not overfitted (inferred).**
* TabPFN-3.5 fits nothing across seasons.
* Each season is forecast from earlier seasons only.
* The constants predate the test seasons.

So the forecasts are honest out-of-sample forecasts *given the inputs*. The exposure is in which inputs and representations were chosen, and in which seasons the result was then read.

**Why a holdout inside the decision window carries the full bias (inferred, standard algebra).**
* Suppose a choice picks the best of k arms on window W, and its estimated advantage is inflated by β, the selection bias.
* For any holdout H whose matches all lie inside W, the expected inflation of H's reading is the whole β. It is not diluted by W being larger. In general it is (matches of H inside W) / (matches of H) × β.
* When the choice is made on one metric (no odds, or the 24-hour price) and read on another (the closing-line edge), the inflation carries over in proportion to how the two metrics' noise is correlated.
* The working is in [plan.md](plan.md), section 1.

**Order-of-magnitude bounds for the choices made since 2 Oct (inferred, worst case).**
* The assumptions: the deciding metric's noise fully correlated with the close's, and all arms truly equal.
* The bound is the expected maximum of k standard normals times the standard error of the arms' difference at the close, read from each study's reported interval.
* Phase 3 of the plan replaces these with bootstrap measurements.

| Choice | Window | Arms | SE at the close | Bound on the inflation of the close edge (mLL) |
|---|---|---:|---:|---:|
| Surface IOS kept | 2022–26 | 2 | 0.06 | ≈ 0.03 |
| Offset Elo swapped in | 2022–26, 2025–26 | ≈ 8 | 0.10 | ≈ 0.14 |
| Walk-forward calibration | 2022–26 | 2 | ≈ 0.03 (assumed: two near-identical forecasts; not reported) | ≈ 0.02 |
| **Stage 1 total** | | | | **≈ 0.2**, against a reported +1.2 to +1.3 |
| Stage 2 adopted (adjustment against the column) | men 2024–26 | ≈ 3 | 0.19 | ≈ 0.16 |
| 28-day memory | men 2024–26 | 3 | ≤ 0.19 | ≤ 0.16 |
| **Stage 2 total** | | | | **≲ 0.3**, against +0.41 to +0.54 |

* **Not bounded here:**
  * **the 2 Oct family choice:** 53 inputs from about 600 scored versions, chosen mostly on gains over Elo, with the profile's role chosen on its 2020+ market gains;
  * **the reliance on the 2020+ era** (section 4).
* Choices made on gains over Elo carry little selection pressure on the closing-line metric. Most inputs tie with the odds, and TabPFN's edge was a surprise rather than a target. Choices made on the market metric carry more. The data inside 2020–2026 cannot separate selection on the era from a real change of era.

**What happened to selected results in this project when they were re-tested (observed).** All in mLL or log-odds, + = the named arm or effect better:

| Result | Where it was selected | On new or repaired data | Reading |
|---|---|---|---|
| Pair strength, Elo-sum input | +0.17 [+0.07, +0.27], 2020–24 | −0.07 [−0.29, +0.16], 2025–26 | gone |
| Rust after a break (feature interactions) | joint z +3.99, 2014–24 (+ = the declared direction) | 2025–26: coefficient b −0.21 [−1.35, +0.93] (+ = the declared direction); as an input −0.27 [−0.64, +0.10] mLL; power 19–26% | not confirmed |
| Profile beyond calibrated Pinnacle | +0.79 [+0.13, +1.46], original | +0.355 [−0.251, +0.961], repaired (a leak fix and a thinner history, not pure selection) | halved; tie |
| Short IOS after adjusted points | +0.13 [+0.05, +0.20], 2022+ | −0.013 [−0.091, +0.066], repaired | gone |
| Men's serve-speed change, log-odds per SD | +0.090 [+0.017, +0.162], 2022–24 | +0.103 [+0.029, +0.178], blind 2025–26 | held |

The sibling UFC project's rebuild records that a headline from a chain of about 80 constructions realised about half its size when re-measured. That is a reference from another sport, not tennis evidence.

## 6. The rebuild question: how much leakage do these features bring?

It depends on the holdout:

| Holdout of the rebuild | Design leak from keeping the 58 in the pool | What remains |
|---|---|---|
| **Matches after the frame**, sealed now (from 29 Jul 2026) | **none by construction.** No choice read them against the market: 227 are untouched; 787 were scored only without odds, where they made up about 0.2% (Stage 4's rundown) to about 3% (the Thinking study's free models) of the scored matches | The selection on development data can still overfit 2020–2026. The holdout measures that honestly, as a smaller edge |
| **Men's 2005–2012 backcast** | **none.** No choice or constant saw it | Era differences (wider margins, other books, no speed data) confound absolute edges. Comparisons between designs inside the era are cleaner |
| **Men's 2018** (never in a market test) | **none for the choices.** It sits inside the constants' 2013–18 tuning | Small: 2,620 matches, SE about 0.9 |
| **2025–Jul 2026, or any window inside 2013–2026** | **The full bias of every choice whose window contains it.** For the post-2 Oct refinements, about 0.2 (stage 1) and ≲ 0.3 (stage 2, men), by the bounds above | **The era reliance and the 2 Oct family choice cannot be bounded from inside.** 2025–2026 was read about 20 times; every incumbent is seen there |

* **The question as asked has two answers (inferred):**
  * With a sealed future (or the backcast) as the holdout, keeping these features in the pool costs nothing in leakage, and the holdout tells how much of their 2020+ value survives.
  * With 2025–2026 as the holdout, the refinements leak a few tenths of a mLL, but the bigger risk is the era, and only fresh data can measure it.
* **The pool itself is exposed (observed).** 367 of the 603 usable menu columns were related to 2025–2026 results by earlier studies (`feature_universe/menu.csv`). As in the UFC v4 rebuild, the remedy for a historical holdout is symmetry and disclosure. The remedy for leakage itself is a holdout no choice has seen.

## 7. Untouched data on disk

Counts from `data/studies/feature_provenance/counts/` (no result column read for any match after 28 Jul 2026). They describe the tables of the 7 Oct rebuild, counted on 8 Oct. The coordinated Stage 0 rebuild planned for 8 Oct (the [corrupt-data decision](../../decisions/2026-10-08-corrupt-data-fixes.md), about 73 new Tennis My Life matches, 36 re-keyed Shanghai qualifying ids) will move some of them slightly. A rerun of the scripts after it gives the new counts.

**After the frame: main-tour main draws, completed or retired, tournament dates 29 Jul – 30 Sep 2026.**

| | ATP | WTA | Total |
|---|---:|---:|---:|
| Matches | 477 | 537 | 1,014 |
| In the 30 Sep build, scored without odds (Stage 4; TabPFN-Thinking's free models) | 362 | 425 | 787 |
| New at the 7 Oct rebuild, untouched | 115 | 112 | 227 |
| … of which with a tennis-data average close | 54 | 28 | 82 |
| With a tennis-data average close (all) | 416 | 453 | 869 |
| Pinnacle | 0 | 0 | 0 (Pinnacle on file ends 13–14 Jan 2026) |
| BetOnline clean close | 464 | 512 | 976 |
| Polymarket close (24 h before) | 459 (330) | 528 (427) | 987 |
| Serve speed for both players | 428 | 128 (US Open only) | 556 |

* **Betfair Exchange** (tennis-data BFE columns) is on 949 of the 950 tennis-data rows after 28 Jul, a sharp second benchmark.
* **The frame is not built for these matches yet.** The rebuild steps are in the [offset-Elo decision](../../decisions/2026-10-06-offset-elo.md). The frame's checks against the frozen 5 Oct upload will need re-basing.

**Never in a market test.**
* **Men's 2018:** 2,639 main-tour matches, 2,620 with the average close and 2,604 with Pinnacle.
* **Lower tiers:** prices only from 2024–2026; mostly Polymarket, 2026.
* **Seasons before 2013:**
  * **Men:** Sackmann's tour-level files 2000–2009, with box scores on about 88% of matches; tennis-data ATP odds with Pinnacle in 2005, 2007, 2008 and 2010–2012. Three files are missing (ATP 2002, 2004, 2006: failed Wayback captures, never retried). The books' average starts in mid-2010.
  * **Women:** no box scores before 2010 on disk.
  * **2010–2012** served only as rating warm-up and training rows, and was never scored.

## 8. The estimation plan (summary)

The full plan is in [plan.md](plan.md), with the estimands, the methods, the data, what each outcome would mean, costs and guardrails.

**Follow-up, 8 Oct 2026.** The owner asked for the alternative: keep 2025–2026 as the holdout and make it as clean as possible. That protocol, with its forecast of the remaining optimism, is in [clean_holdout_rebuild](../clean_holdout_rebuild/README.md).

| Phase | What it estimates | Data | Cost |
|---|---|---|---|
| 0. Seal | protects the only clean data; freezes today's model as the comparator | none read | none |
| 1. Ledger | done (this report) | — | — |
| 2. Training size against era | how much of the 2015–19 tie is a smaller training set; one look at men's 2018 | seen data + men's 2018 | ~120 local fits |
| 3. Decision bootstrap | the selection bias of each exposed choice, on the closing-line metric, replacing section 5's bounds | stored per-arm forecasts | CPU |
| 4. Hindsight replay at 2022 (and 2020) | how much of the 2022–26 edge an honest 2021 process would have found | seen data | a few hundred local fits |
| 5. Backcast, men 2005–2012 | whether the design choices hold in an era none of them saw | three downloads + rebuild | days |
| 6. Prospective | the true forward edge; the design leak (exposed against clean, compared across seasons) | sealed matches from 29 Jul 2026 | waits for data: ~7,700 matches for +1.3 at 80% power |
| 7. Rebuild protocol | selection with no incumbent in any rule; exposed choices re-enter as alternatives | development data ≤ 28 Jul 2026 | the rebuild itself |

## 9. Decisions for the owner

1. **Seal the post-frame matches as the holdout now?**
   * Recommended: yes, all events starting from 29 Jul 2026, with the 787 no-odds-scored matches included and disclosed. No study reads their results until a pre-registered look.
2. **2025–2026: development, not holdout?**
   * Recommended: yes for any claim about the edge.
   * It may still serve as a pseudo-holdout rehearsal for the selection process.
3. **Order of the cheap diagnostics.** Recommended: phase 2, then 3, then 4. They need no new data and could run before the rebuild's selection.
4. **The backcast.** Downloading three tennis-data files and extending Stage 0 to 2000 for men buys about 20,000 untouched matches. Fund it now, after phase 4, or not at all?
5. **The rebuild's pool.** Should exposed choices enter as axes of alternatives rather than at their chosen values? Recommended: yes, as in the UFC v4 rebuild. Examples:
   * profile memories of 1–8 weeks;
   * pooled or surface IOS;
   * blend, offset or overall Elo;
   * speed memories of 14 or 28 days.
6. **Per-tour choices.** Several inputs entered both tours on the men's evidence, among them the surface profile (the analyst recommended men only) and the offset Elo (women all ties). Should the rebuild select per tour?
7. **Provenance going forward.** The modelling work since 23 Sep is uncommitted. A commit, or a hashed manifest, before the rebuild would give its decisions a date. Whether and when to commit is the owner's call.

## 10. Limits of this audit

* **What it rests on.** It reads documents and code. Where they disagreed, the code was taken: for example, `stage4_features.py:727` says "full history" where the code filters to 2010–2018.
* **The 59 candidates' list is unrecorded.** The starting list behind 52 of them is not in the repo. The plan's hash proves it did not change after 02:19 UTC on 2 Oct, not what was approved.
* **The pre-2022 pooled figures** in section 1 are match-weighted averages of the studies' era rows, with approximate intervals.
* **Section 5's bounds are back-of-envelope.** They assume worst-case correlation and equal true arms.
* **The per-season edge reads seasons up to 2024 only.** The 2025–2026 figures are copied from earlier studies, with their own calibration choices.
* **Who drafted some inputs is not recorded:** the owner's items 5–6 of 6 Oct and the Stage 4 starting list.

## 11. Files

| What | Where |
|---|---|
| Per-season and pooled edge, 2014–2024; seeds and training sizes | `src/eda/feature_provenance/edge_by_season.py` → `data/studies/feature_provenance/edge_by_season.csv`, `edge_pooled.csv`, `edge_meta.json` |
| The ledger of the 58 inputs and of stage 2 | `src/eda/feature_provenance/ledger.py` → `provenance_58.csv`, `provenance_stage2.csv` |
| Counts of untouched data (post-frame, pre-2013, lower tiers, which tables hold which rows) | `src/eda/feature_provenance/counts/*.py` → `data/studies/feature_provenance/counts/*.txt` (plus the link and post-frame parquet files they write) |
| The estimation plan | [plan.md](plan.md) |
| Tests | `test/feature_provenance/` (5) |

Run from the repo root: `./python.sh src/eda/feature_provenance/edge_by_season.py`, `./python.sh src/eda/feature_provenance/ledger.py`, then each script in `counts/` (`postframe.py` before `postframe_misc.py`). Tests: `./python.sh -m pytest test/feature_provenance -q`.
