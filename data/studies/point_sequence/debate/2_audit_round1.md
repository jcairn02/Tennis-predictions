# Audit, round 1: framework for point-sequence / momentum / streak ideas

Auditor (independent of the brainstormer). 6 Oct 2026. Read-only checks with `./python.sh`; nothing written outside the scratchpad.

Conventions used throughout:

* Gains are milli-log-loss (mLL) per match. Each one says who is better, and "tie" when the 95% interval spans 0.
* Labels: **observed** = read or computed from repo files today; **inferred** = my reasoning; **suggestion** = proposal.

---

## A. Verification of the brief

### A.1 Load-bearing errors (fix before ideas are judged)

1. **The model the brief describes is no longer the current model.** *Observed.*
   * The owner's decision of 6 Oct (`docs/decisions/2026-10-06-offset-elo.md`) replaced `elo_logit` and `surface_first` with six inputs: `elo_overall`, `elo_surf_offset`, `surf_season_a/b` and `surf_layoff_a/b`.
   * Together with the surface-IOS decision, the model now has **58 inputs**: odds + 31 unchanged + 21 per-surface IOS + these 6.
   * Its frame is `data/studies/surface_rating_race/model/model_frame.parquet`: 63,737 rows, 58 `in_` columns, list in `model_inputs.json`.
   * The brief's "closing odds + 53 inputs", its input list, and `surface_ios/base_frame.parquet` as "the frame" all describe the 54-input predecessor. The other session's `docs/studies/feature_interactions/brief.md` already uses the 58-input model.
   * The match set is the same (39,918 train + 23,819 test), so links by `match_id` still work. Any new arm must be built on the 58-input frame.
2. **The current model's own standing is unmeasured.** *Observed.*
   * The brief's "+1.60 [+0.84, +2.36]" (men) and "+1.30 [+0.65, +1.94]" (both tours) are for the 54-input predecessor. Positive = model better than the recalibrated tennis-data close; the women's figure, +1.00 [−0.01, +2.00], is a tie.
   * Each 6 Oct swap was tested separately and tied at the close:
     * surface profile R1 against base: +0.01 [−0.10, +0.13], positive = surface arm better, a tie;
     * offset Elo against base: −0.05 [−0.24, +0.14], positive = offset arm better, a tie.
   * No fit of the combined 58-input model is reported. Its edge has to be re-established before it serves as "base".
3. **The 24-hour Polymarket claim is attributed to the wrong model, and the money test is omitted.** *Observed.* Source: `surface_rating_race/README.md` §4. Positive = arm better than the 24-hour price; 2,648 matches.
   * The "+1.6 to +1.8" belongs to the offset arms: `elo_off` +1.84 [−1.84, +5.53] and `ttt_off` +1.59 [−2.43, +5.61], both ties.
   * The then-current base got +1.06 [−3.02, +5.14], a tie.
   * The intervals are about ±4 on 2,648 matches. That is not "few matches"; a test against a price is simply that wide.
   * Omitted: the line-sharpening study bet the current best model at Polymarket's early market instead of the close, on 2,933 matches of 2026.
     * The difference was **$0.00 per 100 matches** realized (−0.86 to +0.91), a tie.
     * The market moved only 7% of the way toward the model.
     * Against Polymarket's close in 2026 the model ties: +0.21 [−2.58, +2.83] mLL, positive = model better.
   * "The early price drifts toward the model" is true (slope +0.107 [+0.040, +0.174] on event openers), but it has not been shown to be worth money.
4. **The "coverage" framing is wrong.** *Observed* from `shot_level/stage2.md` and `stage1.md`.
   * The brief says coverage "would rise from ~30k matches to most main-tour matches". But the shot-level study's pre-match sequence features already **existed** on 27,489–30,018 of about 31–32k matches with odds per tour (2013–2026), because a feature only needs each player to have one earlier carrying match.
   * The ~30k (30,044) is the pool of per-match statistics. The sequence family covers about 19.5k men's and 9.9k women's matches, mostly Slams, charts, ATP tour 2021–24 and TDI.
   * The binding constraint was **depth per player**, not existence:
     * "Holds right after breaking" rested on a median of 5–58 qualifying games per player per 52 weeks.
     * Its squared correlation with the player's true value was 0.18–0.33 (stage3 depth table).
   * The new sources add depth: WTA API non-Slam 2020–26; marcosjn2 2016–21; the 2021–24 Infosys Challenger and qualifying points (only 5,052 tour-level Infosys matches were in the stage-1 table, out of 37,355 handoff matches). They also add **training-window** density.
5. **The WTA API row overstates three things.** *Observed* in `official_point_feeds/README.md` §WTA.
   * **Win probability** has real values in **2026 only**. 2025 documents carry momentum only; their probability is 0 on every point but the last.
   * **Full advanced statistics** (by wing, rally-length buckets, net approaches) exist for **2025–26 only**. 2021 is all zeros; 2022–24 have winner and unforced-error totals only.
   * **2019:**
     * the log is empty until March;
     * it is "bare" (no winner, server or score) from 1 April to May;
     * it is complete only from 4 June (1,644 matches);
     * 15 of 64 editions are unlisted.
   * **Never covered:** Slams (empty logs) and the United Cup.
   * **Reliability:**
     * The event log replays 98.5% (34,578 of 35,119). But 10,674 of those needed game winners filled from the listing: no-ad doubles, and tie-breaks written "0-0" in some 2022 and 2026 logs. Tie-break point sequences are therefore missing in part of the WTA data.
     * Multi-point correction "undo" runs are not read, so undone points stay in. That can fake streaks.
     * Use the event log, not the point-by-point endpoint, which replays 83.5% and has `pointWinner` wrong on 85,763 points.
6. **"Momentum / streak measures proper were never built" is partly wrong.** *Observed.* Already built and tested:
   * **Point-level serial dependence on serve:** "serve points won right after losing one, excess" (shot-level stage 1). Split-half correlation at chance on both tours; K = 12,730 points (men), infinite (women).
   * **Game-level reactions as raw rates:** holds right after breaking, breaks back right after being broken, holds when serving for the set.
   * **Pressure excesses:** serve points won at 30-30, deuce or break point, minus all serve points; first serves in under pressure.
   * **Early against late level (Stage C):** first two sets against the third set onward; first 150 points against the rest.
   * **Importance-weighted big-point play** against the iid replay (predictability diagnostic stage 2).

   **Not built:** residualised versions of the game-level reactions (the excess over the player's own expected hold or break rate), run-length and overdispersion measures, comebacks and close-outs measured against win probability, set-to-set form variance, slow starts, and anything from the WTA API, SofaScore or marcosjn2. **Nothing near-topic was ever run through TabPFN**, against the 24-hour price, or in-play.
7. **A point-sequence build has already started, and the brief does not mention it.** *Observed.*
   * `src/eda/point_sequence/common.py` and `replay.py` were created 6 Oct 17:38. They hold:
     * a source-priority list over 13 sources: the 8 shot-level ones plus `wta`, `wta_pbp`, `sofascore`, `marcosjn2` and `sackmann_pbp`;
     * a rules-aware replay with the Slam deciding-set rules and tie-break serve rotation.
   * No adapters, outputs or docs exist yet. This is probably "where we left off".
   * Minor: it points at `surface_ios/base_frame.parquet`. The rows are the same as the 58-input frame, so this is harmless for linking.

### A.2 Overstatements and imprecisions

* **Surface-IOS decision "(men)".**
  * The decision applies to the model as a whole. "Men only or both tours" is explicitly *not decided*; the analyst recommends men only.
  * The same holds for the offset-Elo decision.
* **marcosjn2.**
  * Correct: 48,479 records; 99.6% of replays complete; 99.5% of tie-breaks carry a trailing point.
  * The tier ranges "1000s 445–648/yr, 250s 622–915/yr (2016–2024)" omit 2020 (146 and 341).
  * Score agreement ">99%" was checked only on 2018+ records linked to Sackmann (99.45% exact).
  * **No link to Stage 0 or the model frame exists before 2018.** "Should fill most of 2016–2021" is an inference.
  * My rough upper bound (marcosjn2 main-draw counts divided by model-frame matches per tour and year):
    * men: 64–67% (2016), 71% (2017), 76–77% (2019), 76–98% (2020–21);
    * women: 45–59% (2016), 57–70% (2017), 63–76% (2018), 64–75% (2019), 73–100% (2020–21);
    * 2015: only 14–25% (from June);
    * Slam main draws: 53–65% (men) and 60–81% (women) in 2016–2019.
  * Coverage is **non-uniform by tier and year**.
  * The data carry no per-point times, no aces or double faults, no serve number; men's 2025 runs Jan–Jun only; there is no 2026.
* **SofaScore.**
  * There are **no per-point timestamps**: only the event start and set durations (`time_set1..5`).
  * Outside tie-breaks the game-winning point is implied, not listed.
  * The server is given once per game.
  * I could not find documentation for "server may shift on game-ending points". The measured TDI–SofaScore agreement is 99.22% on game servers and 99.93% on game winners (125 matches).
* **TDI.**
  * Of its 6,096 matches, only about 540 are main-tour main-draw singles (458 in the window, 81 Wayback, plus some of the 29 Sep capture). The rest are Challenger, qualifying or doubles.
  * Challenger point detail exists from Feb 2026.
  * TDI's terms forbid use for statistical models or betting; the data were collected under the owner's research decision.
  * Each point carries a provider "streak" flag.
* **"Sackmann Slam pbp 2011–2024."**
  * The Australian Open and Roland Garros run only to 2021 in Sackmann's files. Their 2022–26 points come from the Hawk-Eye copy (2019–24) and the SofaScore gap fill.
* **"Clutch records are luck."**
  * Mostly right, but the men's break-point record persists weakly beyond luck: 0.11 split-half at 50+ matches per half, about 20% signal on a 100-match record.
  * The one clutch trait that persisted beyond luck, **big-point play on return** (0.21 men / 0.19 women against about 0 for luck, Slams, 10+ matches per half), was then tested pre-match in Stage 4. It came out "possible" at +0.09 given Elo (positive = feature better), **with the wrong (negative) sign**, on 32% (men) and 60% (women) coverage. The brief omits this.
* **Stage C "split-half ≤ 0.09".**
  * The men's third-set-alone variant reached 0.126 at 12 matches per half (133 players) against 0.009 under luck.
  * The women's late decline was *worse* given the market: −0.19 [−0.35, −0.03], positive = feature better.
* **"The one lead: men's recent change in serve speed, +0.24 [+0.07, +0.41]."**
  * That figure is the 3-input **speed profile**, 52 weeks, 2022–26, week-clustered.
  * The change alone gives +0.14 [−0.00, +0.28], a tie; with a ridge fit +0.12 [0.00, +0.24]; positive = feature better than the odds alone.
  * It was one row among about 300.
* **"Workload adds +0.23 / +0.29 given the market."**
  * Both intervals span 0: men +0.23 [−0.01, +0.48], women +0.29 [−0.06, +0.64], positive = feature better. They are ties by interval, though above the old harness's shuffled-copy line.
* **Every near-topic result is "historical".**
  * Predictability-diagnostic stages 2 and 4, UFC-ideas Stage C and the shot-level study used the pre-repair logistic harness and the tournament-date clock.
  * The repair also **withdrew the claim that the iid "on the day" floor is a demonstrated ceiling** (`feature_alpha_audit/repairs.md`).
  * The timing decision lets these results "stand as recorded, with this caveat".
* **"Women's points share decides less than iid luck (0.118 vs 0.103)."**
  * Correct. But the women's replay also mismatches real tie-breaks per match (0.274 replay against 0.241 real) and wins with fewer points (3.71% against 3.86%).
  * Part of the gap may be replay or de-noising misspecification, not momentum.
* **The frame's 2026** runs to tournament dates of 28 Jul 2026 only: 1,774 men's and 1,714 women's matches.
* **CLAUDE.md** still calls the best model "TabPFN-3.5-Thinking, closing odds + 53 inputs". The brief is right to use local non-thinking TabPFN with a slope; CLAUDE.md is stale on model identity, not on timing rules.

### A.3 Verified as stated (observed)

* The 53-input list of the predecessor: 10 + 12 + 4 + 14 + 7 + 6.
* 8 estimators, softmax temperature 0.9, symmetrised orientations.
* 39,918 / 23,819 rows; men 12,352 and women 11,467 in the test window; no men's 2018 odds.
* Data-map coverage. Men 2022–26: 86–100%. Men 2018–21 non-Slam: 9–38%, excluding Finals. Women 2020–26: 88–100%. Women 2019: 50–57%. Women 2018: 1–5%. marcosjn2 is absent from the data map (0 mentions).
* Infosys: 37,355 matches, 69% with point rows.
* Stage-1 split-half values for the sequence family.
* Clutch figures: −0.27 per 100 importance-weighted serve points beyond luck; 0.7 points fewer break points saved than luck.
* Polymarket in-play prices exist. Measured today: main-tour markets with at least 30 in-play minute prices number 994 (Slam), 1,667 (1000s), 1,048 (500s) and 1,560 (250s), about 5,270 in all, with a median of about 230 in-play minutes each.

### A.4 Not verifiable today

* The SofaScore server-shift caveat (above).
* That marcosjn2's missing matches are missing at random. Its scrape selection is unknown.
* Whether Sackmann's point strings include 500s and 1000s. The catalog lists T250, TQ, CH and ITF; men only, 2011 to Jan 2017; CC BY-NC-SA; not staged.

---

## B. Lessons from what was tried

### B.1 The table

Gains are milli-log-loss per match; positive = the feature (or arm) is better. "Given X" means the feature was added to X.

| Measure (where) | Data | How built and scored | Given Elo | Given the odds | Why it failed | Could it have hidden a real effect? |
|---|---|---|---|---|---|---|
| Break-point record above expectation (PD stage 2; Stage 4) | Box scores: 146,971 men's and 33,205 women's matches | Saves and conversions above the serve rate; split-half; Stage 4 pre-match feature | Men: no spread, K infinite; women: noise | – | **Luck + biased baseline.** A server facing many break points had an unlucky day, which drags the expectation down. Only the iid replay is a fair benchmark. Persistence: men 0.11 at 50+ matches per half, women indistinguishable from luck | Little. Huge samples; luck-dominated by construction |
| Tiebreak record (PD stage 2; Stage 4) | Box scores | Tiebreaks above the iid chance; 52-week record | +0.14 / +0.23 men / women, **negative coefficient** | – | **Luck, used as a correction to Elo:** a good recent tiebreak record predicts *worse* results | No |
| Big-point play, importance-weighted (PD stage 2; Stage 4) | Sackmann Slam pbp 2011–2018/2024, main draws only | Weighted share minus plain share; replay benchmark; Stage 4 pre-match | On return: "possible" +0.09 (men), **wrong sign** | – | On serve: luck. On return: persists beyond luck (0.21 / 0.19, on 131 / 134 players) but fails pre-match | **Yes, partly.** Slam-only, 32% / 60% coverage, a few hundred players. Never rebuilt on WTA API, marcosjn2 or SofaScore depth, never in TabPFN |
| Pressure excess on serve (shot-level) | 8-source point table, about 29k matches | Serve points won at 30-30, deuce or break point minus all, same match; shrunk with K 3,996 (men) / 12,151 (women) | about 0 | +0.02 [−0.05, +0.10] (men, 2-week memory), a tie | **Barely a trait:** split-half 0.17 (men), chance (women). The spread is below binomial noise | Little for men. Women thin: Slams and charts only |
| First serves in under pressure (shot-level) | same | Excess, same match | – | about +0.01, a tie | Weak trait (0.22 / 0.30) | Possibly; never residualised against the player's first-serve rate |
| Serve points won after a lost point: point-level serial dependence (shot-level) | same | Excess, same match | – | about 0, a tie | **No trait** (chance on both tours). Not conditioned on score state; finite-sequence streak bias not addressed | Not as a player trait. As a *match-level* in-play dynamic it was never tested |
| Hold after breaking; break back after being broken; serving for the set (shot-level) | same; men 19,193, women 9,890 matches | **Raw rates**, three memories, opponent-adjusted variants | Women +0.37 [+0.13, +0.61] (hold after breaking, opp-adjusted, 2-week) | about +0.03 [−0.14, +0.20], a tie | **Confounded with hold and break ability**: R² with odds and Elo 0.22–0.25, the most market-like. Thin depth (median 4–58 games per 52 weeks; corr² with truth 0.15–0.33). Planted edges: men rule out ≥ 0.5 in the true career value, women only ≥ 2 | **Yes.** The momentum part (the excess over the player's own expected hold or break) was never isolated. Women's histories had no WTA API |
| Sequence profile, 6 inputs (men) / 5 (women) (shot-level) | same | Unpenalised logistic, then a ridge walk | +0.14 [−0.01, +0.30] (men, ridge), a tie | Unpenalised −0.60 [−0.96, −0.24] (men, worse); ridge −0.02 (men), −0.01 (women), ties | Unpenalised fitting cost about 0.5 mLL per 10 inputs; the ridge chose its maximum penalty, i.e. no signal | Method was fixed in stage 3, and found nothing |
| Late-match decline (Stage C) | Slam pbp 2011–24, 9,948 matches; AO/RG to 2021 | (Late − early serve rate) − the opponent's; replay benchmark | −0.03 / −0.10 (men / women), ties | Men −0.05, a tie; **women −0.19 [−0.35, −0.03], worse** | **Truncation:** the winner's late edge is mostly selection (men 0.024 of 0.040). Not a trait for men (≤ 0.09, about luck); women 0.17–0.19 on ≤ 118 players | As a pre-match trait, little. **The leftover within-match dynamic** (the winner improves late beyond luck; men's third set alone 0.014 against 0.001) was never tested in-play |
| "Grinder", long against short matches (Stage C) | Box scores and minutes | Residual points over the iid expectation in long minus short matches | +0.52 / +0.51 (52 weeks) | −0.09 / −0.10, ties | **Selection:** a favourite's long matches are its under-performances. It measures margin, not stamina | No |
| Workload `sets_14d` (Stage 4) | Results | Sets in the last 14 days | +1.63 / +1.87 | +0.23 [−0.01, +0.48] / +0.29 [−0.06, +0.64], ties; above the old harness line | Not a failure: in the model | – |
| Serve-speed profile and its change (shot-level) | Infosys and Slam speeds, 2022+ | 3-input profile; 2 weeks minus 52 weeks | +0.63 (profile) | Profile +0.24 [+0.07, +0.41] in 2022–26 (better); change alone +0.14 [−0.00, +0.28], a tie | One of about 300 rows; data dense only from 2022 | An open lead (fatigue or injury); never pre-registered |
| Shot features scored on serve points (shot-level stage 3) | 21M serve points | Binomial point model | Men +0.012 per serve point in 2022–26 | As a match feature −0.02, a tie | **Point-level gains do not survive conversion to match forecasts**: the match model amplifies point-forecast noise more than signal | Lesson for any sequence-derived point model |
| Women's points share decides less than iid (PD stage 2) | Box scores | Observation only | – | – | Never tested | Candidate within-match form swings; possibly replay misspecification |

### B.2 Why they failed, by mechanism

1. **Luck masquerading as a trait.** Every clutch, pressure or late-match measure loses its persistence once benchmarked against the iid replay. Persistence then sits at 0.0–0.11, with two tentative exceptions on a few hundred Slam players. *Inferred:* player-level momentum traits are, at best, small.
2. **Selection and truncation.** The match ends when someone wins. The winner therefore "finishes strong", "wins the tiebreaks" and "wins the big points" by construction. Measured against the match's own rates, break-point saves are biased upward; the replay shows it.
3. **Ability confounding.** The measures that did persist (hold after break, break back) persisted because they are hold and break ability, which the close prices.
4. **Coverage and depth.** All of these were built on Slams, volunteer charts and ATP 2021–24, usually 4–60 relevant events per player per year. Women had no non-Slam point data.
5. **Method.**
   * Unpenalised multi-input profiles cost about 0.5 mLL per 10 inputs (fixed in stage 3).
   * The old logistic harness was linear and additive; TabPFN was never used for these features.
   * The tournament-date clock was used.
   * Nothing was tested against the 24-hour price or in-play.
6. **Benchmark.** Only the close was used. The one measured "pre-close" pattern (the price drifts toward the model's no-odds view, slope about 0.1) has so far been worth $0.00 per 100 matches at the early market.

### B.3 Tests that could have hidden a real effect (under-powered or mis-specified)

* **Women's sequence features:** Slams and charts only, 9.9k matches. The WTA API's 33k event logs were unused.
* **Momentum as a residual** (hold after break minus the expected hold): never built.
* **Big points on return:** Slam-only, at 32% / 60% coverage.
* **The within-match late-surge dynamic, and the women's points-share anomaly:** never tested in-play.
* **Any sequence feature through TabPFN with the 58 inputs:** never done.
* **Any sequence feature against the 24-hour price:** never done.

---

## C. Power

### C.1 Formulas (from `src/eda/shot_level/common.py::mde_milli` and `stage0.md`)

* **Full capture.** A feature whose information, fully used, improves the forecast by G nats per match is detected with 80% power at two-sided 5% when **G = 2(1.96 + 0.84)²/n = 15.68/n** nats.
* **Inflation.** Multiply by 1.09² for one input and 1.46² for multi-input fits (walk-forward noise; the repo's measured medians). A family-wide guard over about 40 rows multiplies by 2.11; Bonferroni over 5 arms by about 1.49.
* **Scale.** v = E[p(1−p)] = 0.208 on the test frame (observed). G = 1 mLL needs a *correct* RMS log-odds move of 0.098, about 2.0 pp of win probability; G = 0.25 needs 0.049 (about 1.0 pp).
* **Realized-gain MDE in an arm-against-base test** (the surface-IOS method). SE ≈ √(v·E[δ²]/n), plus seed noise and block inflation, where δ is the arm's log-odds move.
  * RMS δ = 0.022 gave SE about 0.09 and MDE about 0.26 (as pre-registered there).
  * RMS δ = 0.05 gives SE about 0.16 and MDE about 0.45 mLL, both tours.
  * Such a test can show a small *realized* gain, but a tight tie only bounds what *that arm* captured, not the information's value.
* **Measurement noise.** A noisy statistic passes about ρ² (its squared correlation with the true trait) of the true edge to the feature: 0.15–0.35 for the sequence family at current depth (stage 3). So **true-trait MDE ≈ feature MDE / ρ²**.

### C.2 Pre-match, 2022–2026 test frame, all sources unified

*Inferred.* Scorable share assumed at 96% (men) and 98% (women): n ≈ 11,900 men, 11,250 women, 23,150 both. The pre-unification share was already 95% / 96% at k ≥ 3 in 52 weeks (stage 0).

| Smallest detectable gain over the close, mLL (positive = feature better) | Both tours | Men | Women |
|---|---:|---:|---:|
| Full capture, formula | 0.68 | 1.32 | 1.39 |
| One input (× 1.19) | 0.80 | 1.57 | 1.66 |
| Multi-input profile (× 2.13) | 1.44 | 2.81 | 2.97 |
| One input with Bonferroni over 5 pre-registered arms | 1.19 | 2.34 | 2.47 |
| Realized gain, arm moving forecasts by RMS 0.03–0.05 (4 seeds) | ≈ 0.30–0.45 | ≈ 0.45–0.65 | ≈ 0.45–0.65 |
| **True trait** behind a noisy sequence statistic (one input ÷ ρ², ρ² = 0.2–0.35) | **≈ 2.3–4.0** | **≈ 4.5–8** | **≈ 4.7–8.3** |

For scale, the best features this project has found against the close are much smaller:

* box-score profile: +0.36 [−0.25, +0.96] beyond Pinnacle after repair, a tie;
* serve-speed profile: +0.24;
* workload: +0.23 / +0.29, ties;
* surface information with the odds in the model: about 0.

*Inferred:* a pre-match momentum-trait test is under-powered by about 3–10× for any plausible effect. **A tie is the expected outcome and says little**, unless unification raises ρ² substantially.

**Unification does not change n much.** The test set is already about 95% scorable. It changes the **training rows** that carry the feature and **ρ² through depth**. Depth is the real lever.

**Subset effects are diluted.** A narrative or event feature active in a share s of matches has a within-subset MDE of about 15.68 × 1.19 / (s·23,150) nats:

* s = 5% (about 1,160 matches): about 16 mLL inside the subset, an RMS move of about 8 pp, contributing at most 0.8 overall;
* s = 20%: about 4 mLL inside the subset.

WTA event-log signals are common, so these subsets are not tiny. *Observed:* singles matches 2022–25 have a physio call in 16–17%, a medical treatment in 16%, a toilet break in 34–40%, a time violation in 5–6%, a code violation in 5% and a suspension in 8–12%.

### C.3 Against the 24-hour Polymarket price (2025–26, 2,648 matches)

* **Full-capture MDE:** 15.68/2,648 = 5.9 mLL; about 7 with inflation; per tour about 12–14.
* **Arm against arm** at that price showed half-widths of about 0.5. Only arms that move forecasts a lot, in the right direction, can register there.
* **The move test is cheaper.** H4 asks whether the price moves toward the arm's no-odds view between 24 hours and 30 minutes; it carries more information per match. Money is the binding check: the line-sharpening study measured $0.00 per 100 matches.

### C.4 In-play, 2025–26 Polymarket

*Observed* (computed today):

* About 5,270 main-tour markets carry in-play minute midpoints (Sep 2025 – Oct 2026; median about 230 in-play minutes).
* Official per-point clocks exist for about **1,896 of 2026's markets**: WTA API 1,269, Slam feeds 371, TDI 256 (`line_sharpening/starts_check.json`).
* Add an estimated 400–600 WTA matches from Sep–Dec 2025: **about 2,300–2,500 matches, about 75% women; men about 450–550.**
* Men's non-Slam 2025 to Jun 2026 has SofaScore points but **no per-point times**, only set durations.

| In-play design | Detectable effect |
|---|---|
| Log loss of the in-play price at one fixed checkpoint per match, with a momentum adjustment (full capture) | Both about 6.5 mLL; women about 8.7; men about 31. Extra checkpoints help little, because they share one outcome |
| Martingale drift test: does the price move after momentum events (overreaction or underreaction)? | Observed per-game (about 5-minute) price move: SD 7.4¢ (1000s; 3.6¢ per minute, 11.9¢ per 15 minutes; median move 0–1.5¢, fat-tailed). About 20 game increments per match gives about 48k increments; with 20% flagged, **MDE ≈ 0.25–0.35¢ per game** |

**The economic threshold is about 3¢ per trade.** The taker fee has been 5% × (1 − p) of the stake since July 2026, about 2.5¢ at even money, plus at least 0.5¢ of half-spread; in-play spreads are not yet measured.

*Inferred:* in-play, statistical power is **not** the constraint. Costs, latency and live data access are:

* Minute midpoints cannot resolve the seconds after a point; trades have second stamps up to 21 Sep 2026.
* Point feeds are collected *after* events under a "non-commercial research" basis. Collection during events awaits a betting-pipeline decision (decision of 6 Oct).

---

## D. Failure-mode checklist for momentum, streak and sequence features

Each item gives a required control. "Must" items are hard requirements for the first test.

1. **Truncation and selection** (winners look clutch, strong finishers or comeback kings).
   * Must: compute every within-match statistic on iid replays as well: de-noised day rates, and a second replay at *pre-match* expected rates. Report real minus replay.
   * For a pre-match feature, also run the full feature pipeline on replay-generated histories. It must show **zero** predictive gain there.
2. **Finite-sequence streak bias.** Under iid, P(win | k previous wins) estimated within short sequences is biased downward, and the mirror bias applies after losses.
   * Must: benchmark against the replay or a permutation within server-blocks. Never against 0.5 or the match average.
3. **Score-state, server and structure confounding.** After a lost point the server is more often at 30-30, deuce or break point, where servers win slightly less. Serve alternates by game and every two points in tie-breaks. New balls, changeovers and set breaks interrupt runs.
   * Must: condition on score state and server; use game-level iid expectations from both players' hold probabilities.
4. **Ability confounding.** Raw rates (hold after break, close-out percentage) mostly measure ability.
   * Must: residualise against the player's own pre-match expected rate, from leak-proof ratings at that date. Report R² with the 58 inputs (aim below 0.1).
   * Must: screen against the current best model's own out-of-sample forecast, as the feature-interactions study does and meta-stack's E1 did.
5. **Reliability threshold and shrinkage.**
   * Split-half real r minus replay r ≥ 0.10, with real r ≥ 0.20 at the depth a typical test-window player has.
   * K by empirical Bayes on ≤ 2018 seasons only (frozen).
   * Report ρ² against the career truth by depth quartile.
   * Below threshold: reject before any model fit.
6. **Leakage** under the 5 Oct clock (`docs/decisions/2026-10-05-match-timing.md`).
   * Own-history features in order are safe. Opponent-adjusted residuals, field or tour means and pooled iid baselines are **cross-player** and must use `timing.parquet` (a result counts from lf + 1; a match reads at es) and pass `src/eda/match_timing/probe.py`.
   * Normalising constants are frozen on ≤ 2018.
   * The **format** (best of, deciding-set rule) of the target match comes from schedule rules, never from its score (repair finding). `point_sequence/replay.py` picks rules by which one completes the replay. That is fine for *past* matches; it must never decide the *target* match's format.
   * **Previous-match narrative** features (late finish, marathon, rest hours) need the previous match's *finish* before the current match's *earliest start*. Watch overnight suspensions and Wimbledon's spurious day jumps (28 matches).
   * Same-day ordering: rain-delayed doubles and two singles in one day happen.
   * **Point stamps are entry times:**
     * AO 2026: 0.4% out of order, up to 25.6 h;
     * Wimbledon: `EpochTimeStart` keyed late; use `EpochTimeEnd`;
     * TDI: 869 step-backs in 15 matches;
     * WTA log: in order in 99.6% of logs.
   * Provider win-probability and momentum series (WTA 2025–26, IBM 2025–26) embed the provider's model. Fine as summaries of past matches; never read in-match values with a lag.
7. **Missingness as a proxy.** Availability differs by source × tier × year × court. marcosjn2 runs at about 45–98% depending on tier and year; SofaScore may skip outer courts and qualifying; the WTA log covers every draw. TabPFN models NaNs natively; the harness passes them through untouched (`src/eda/*/run_local.py`).
   * Must: model "feature present" on odds, rank, level, round, surface and year. If AUC > 0.6, missingness carries tier information.
   * Must run three placebo arms:
     1. a missingness indicator only;
     2. values shuffled within tour × season × source with the NaN mask kept;
     3. a complete-case comparison on identical rows.
   * Note that today's 58 inputs are almost fully observed. The exceptions are women's `indoor` (100% NaN) and women's hold and break form in 2013–15 (72% NaN). A feature with era- and tier-dependent gaps is new territory for this model.
8. **Source heterogeneity.**
   * marcosjn2 adds a trailing tie-break point (99.5%).
   * SofaScore implies the game-winning point.
   * WTA logs write "0-0" tie-breaks (2022, 2026), leave unread correction undos, and have no-ad doubles.
   * TDI stops early in a game in 6.3% of matches.
   * The AO feed has superseded duplicate entries; Wimbledon repeats rows (19 matches).
   * `point_sequence`'s PRIORITY takes one source per match, so a player's history mixes sources by era and tier.
   * Must: compute each per-match statistic on matches held by two sources (WTA log against marcosjn2 or SofaScore for 2020–25; marcosjn2 against the Slam files, 5,392 matches; TDI against SofaScore, 125) and require between-source ICC ≥ 0.95. Check the feature's per-source means on the same matches.
9. **Train/test coverage shift.**
   * 2013–15 is thin: Slams, charts, and unstaged Sackmann strings for men.
   * 2016–21 depends on partial marcosjn2.
   * 2022–26 is nearly complete.
   * TabPFN learns the feature from the rows that carry it, and can learn "era" through NaN patterns.
   * Must: report per-season NaN rate, mean and SD by tour; test 2016–21 against 2022–26 distributions; compare arm and base on identical rows and windows.
   * Consider building features only from fields every source has (point winner and server), the lowest common denominator.
10. **Benchmark choice.**
    * Primary: arm against base (the 58-input model) at the recalibrated close, with walk-forward slopes, seed variance and four-week blocks.
    * Secondary: the same arms fed the 24-hour Polymarket price (raw and recalibrated; recalibrating that price costs about 1 mLL, so do not weaken the baseline), plus the H4 move test.
    * Money: the line-sharpening betting simulation.
    * Always report the RMS log-odds move of the arm against base.
11. **Multiple comparisons and holdouts.**
    * Pre-register ≤ 5 arms. Choose them on 2019–21 validation (or on discovery 2013–21 and replication 2022–24, as `feature_interactions` does). Score the test window once, with Holm across arms; everything else is labelled exploratory.
    * **Coordinate with the concurrent `feature_interactions` study, which keeps 2025–26 closed** until its final test. Momentum EDA must not burn that holdout.
    * In-play data are 2025–26 only: split them in time (explore Sep 2025 – Mar 2026, confirm Apr – Oct 2026) and pre-register.
12. **Retirements, walkovers, dead rubbers, team events.**
    * Drop the retirement segment from momentum statistics; it is injury, and it is in the target as a retirement. Exclude Finals dead rubbers and team events.
13. **Format rules.**
    * Ten-point deciding tie-breaks: AO from 2019, every Slam from 2022. Wimbledon played 12-12 in 2019 and 2021; RG qualifying used 7-point tie-breaks 2017–21; AO qualifying 2018 had a tie-break.
    * Best of 5 against 3; Next Gen.
    * Sequences and iid baselines must use the right rule (`replay.py`'s fallbacks handle most cases).
14. **Rare-event power.**
    * State the subset share and within-subset MDE before building (C.2). Reject designs whose plausible effect is below it.
15. **In-play specifics.**
    * Use the price strictly before the point's earliest possible start.
    * The listed start is within 5 minutes of the first point in only 52% of matches; use the validated start.
    * Measure in-play spread and depth from PMXT books (31 Jul – 3 Aug 2026 on disk).
    * Courtsiders and latency; fee schedule changes (none before 29 Mar 2026, then 6% × (1 − p) in shares, 3% × (1 − p), and 5% × (1 − p) from July).
    * Live-data rights and collection timing (feeds are collected after events today).
16. **Planted-edge calibration inside TabPFN.**
    * Before reading a null, plant a known edge (synthetic outcomes, as in shot-level stage 3) through the actual TabPFN harness, to measure recovery for a feature with this missingness and noise.

---

## E. Scoring rubric for the brainstormer's ideas (100 points + hard gates)

### Hard gates (any failure: reject or redesign before scoring)

* **G1** Design, EDA or constant-tuning that reads 2022–26 outcomes (or the coordinated 2025–26 holdout).
* **G2** A cross-player feature without the 5 Oct clock and the probe.
* **G3** The target match's state or format read from its own realized score or points (pre-match), or prices taken after the point they are meant to precede (in-play).
* **G4** Needs data not on disk, a paid API call, or live collection the owner has not approved, *without* a stated acquisition step and cost.
* **G5** A within-match measure with no iid replay or permutation benchmark.

### Weighted criteria

| # | Criterion | Weight | Scoring guide |
|---|---|---:|---|
| 1 | **Mechanism, and why the price lacks it.** A concrete tennis or market mechanism, plus a reason the close (or the 24-hour price) does not already hold it. Not a re-expression of ability, Elo, points won or hold rates | 15 | 0 = ability in disguise; 8 = plausible but the market sees the same box score; 15 = derived from sequence or timing information not in box scores, with a reason bettors underweight it |
| 2 | **Trait or dynamic evidence beyond luck.** Prior repo evidence or a cheap outcome-free pre-test: split-half real minus replay; for in-play, a within-match dynamic beyond the replay | 15 | 0 = already shown to be luck; 8 = untested but testable outcome-free; 15 = existing beyond-replay evidence (e.g. late surge, return big points) |
| 3 | **Data coverage and quality** after unification: test-window share, *training-window* share (2013–21), depth per player, source agreement, clock quality | 15 | 0 = one source or a short window; 8 = test window covered, training thin; 15 = both windows covered by agreeing sources |
| 4 | **Power realism**: plausible effect against the MDE in C (full capture ÷ ρ², subset dilution, per tour) | 10 | 0 = plausible effect < MDE/3; 5 = within 2×; 10 = plausible effect ≥ MDE |
| 5 | **Leakage and selection risk** (scored in reverse): truncation, streak bias, score-state confounding, timing, format-from-score, missingness proxy; are the controls in D specified? | 15 | 0 = several unaddressed; 8 = risks named, controls vague; 15 = controls concrete and cheap |
| 6 | **Testability in the existing harness**: one clear arm on the 58-input frame, with placebo, residual screen against the best model's forecast, and pre-registration; or a clean in-play design with a pre-specified checkpoint or drift test; a cheap first gate | 10 | 0 = needs a new model class or many arms; 10 = one gate in hours, then one arm |
| 7 | **Economic path**: bettable where and when (24-hour or early price, in-play, tier), size against costs (about 3¢ per trade in-play; about 1¢ spread plus fee pre-match), liquidity, data rights for live use | 10 | 0 = no executable path; 5 = path exists but the costs dominate the plausible edge; 10 = plausible edge above costs at available liquidity |
| 8 | **Value even if null**: reusable infrastructure (unified point table, cross-source checks, replay library) or closing a route the owner keeps reopening; fits the owner's point-by-point and per-statistic thesis | 10 | 0 = one-off; 10 = infrastructure every later idea needs, or a decisive, well-powered closure |

### Bands

* **≥ 75: build now.**
* **55–74: build after the cheap gate** (outcome-free reliability against the replay, then the residual screen).
* **40–54: park.**
* **< 40: reject.**

Ties are broken by criterion 2, then criterion 3.

### The staging I will require of any idea scoring 55 or more (suggestion)

1. **Gate 0, no outcomes:** build the feature, then check cross-source ICC, real-against-replay persistence, the missingness model and the coverage table.
2. **Gate 1:** residual screen against the 58-input model's out-of-sample forecast, discovery 2013–21 and replication 2022–24, with the missingness-preserving placebo.
3. **Gate 2:** one TabPFN arm chosen on 2019–21 validation and pre-registered with a power statement, then the test window. Plant a known edge first to measure recovery.
4. **Gate 3:** the 24-hour price, the H4 move test, and the line-sharpening money simulation.
5. **In-play ideas** run a separate track with a time split, a drift test and a cost model.
