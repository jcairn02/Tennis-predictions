# Serve-speed change in the best TabPFN model: the brief every agent reads

7 October 2026. Written by the lead (main session) before any agent ran. **Binding for every agent of this study.**

## 1. The owner's request (verbatim)

> We identified "Serve-speed change (men): first-serve speed over the last 14 days minus the last year +0.090 [+0.017, +0.162] in 2022–24 (log-odds per SD, positive = a player whose speed rose wins more than the model says); about the same against the close.
>
> However, when we came to this conclusion we were a bit data starved and didnt have proper era fill ins or completeness of this feature. Since that point we've developed a MUCH more robust data collection for this statistic. Check out which data we've recently downloaded.
>
> Work with multiple opus agents to brainstorm how you should potentially integrate this into our best performing tabpfn 3.5 local non thinking model (develop an agent collective that work together as an optimal organization team unit for completing this task. No more than 10 agents. As few as 3.).
>
> After you figure out how to implement it effectively (may or may not require imputing and baysian priors to handle players who we dont have much of this data on). Then perform a test to see if it improves prediction scores in 2024-2026 and by how much. (expanding window tests). Be clear when speaking about how it was done, what was done and what it predicts.

**What the study must deliver:**
1. A design for putting serve-speed information into the current best model, settled by the team (this brief, `team.md`).
2. A leak-proof, tested build of the chosen feature(s), including how players with little or no speed data are handled (imputation, shrinkage, priors, as the team decides).
3. One pre-registered **expanding-window test** on 2024, 2025 and 2026. For each test season Y, the model is trained on 2013 to Y − 1 and scored on Y, with and without the speed input(s). The test says how much the prediction scores change.
4. A report that says plainly how it was done, what was done, and what the feature predicts.

## 2. Binding rules

### 2.1 What may be looked at before the freeze

* **No match result before the freeze.** Before the pre-registration is hashed, no agent relates any speed feature to a match result (`a_won`, `won`, the winner, sets or games won), in any season. The point-sequence study's published numbers (section 5) are the only result-based knowledge allowed.
* **Statistic targets are allowed only on seasons ≤ 2023.** Examples: a player's next-match first-serve speed, next-match aces, first-serve points won or service points won. They may be used to tune constants, choose representations and pass gates. Each such look goes in the "Looks" section of your file: seasons, target, what was compared. The lead copies it into the [look ledger](look_ledger.md).
* **2024–2026: features and counts only.** You may compute feature values, coverage and distributions for 2024–2026, but you may not relate them to any outcome or statistic target of those seasons.
* **Prices.** You may relate a feature to the closing odds (`in_odds_logit`), for example R² or redundancy, on seasons ≤ 2023 only. Log the look.

### 2.2 Timing (project decision of 5 Oct 2026; CLAUDE.md)

A result may reach another match's features only if it surely finished before that match could start. A match's serve speeds are part of its result.
* **Own history in order is safe by construction.** This means the player's earlier events, plus earlier rounds of the same event, never other events of the same week. It is `predictability_diagnostic.common` order, as in `src/eda/point_sequence/speed_build.py`.
* **Anything that pools different players' speeds is a field statistic.** Examples: event or edition offsets, tour means, empirical-Bayes priors fitted across players, population variances. It must either be frozen on an earlier period (≤ 2021 or ≤ 2023, stated) or follow the leak-proof clock: a match counts from `lf + 1` and a target reads state as of `es` (`data/studies/match_timing/timing.parquet`). It must never use the tournament start date.
* **Every new feature is probed.** Speeds after a cut are replaced by noise, and nothing about a match before the cut may move (`speed_build.leak_probe` is the model to copy). For field statistics, also follow `src/eda/match_timing/probe.py`'s idea.

### 2.3 Working rules

* **Python:** `./python.sh` (the `tennis` env) for everything.
  * The GPU env `./python_tabpfn_local.sh` is used **only by the lead**. Agents do not run TabPFN fits.
  * A smoke test of a fit runner on synthetic labels needs the lead's go-ahead.
* **Files:**
  * code: `src/eda/serve_speed_tabpfn/`, with design-phase scratch in `src/eda/serve_speed_tabpfn/design/`;
  * tests: `test/serve_speed_tabpfn/`;
  * outputs: `data/studies/serve_speed_tabpfn/`, with design notes in `data/studies/serve_speed_tabpfn/design/`;
  * report: `docs/studies/serve_speed_tabpfn/`.
* **Other studies' files are read-only.** Import shared modules; never edit them.
* **No git command that changes state.** Do not delete files.
* **Scores carry a direction.** Every log loss, mLL gain or "A − B" figure says which direction is better, who wins, and "tie" when its 95% interval spans 0.
* **Labels.** Separate *observed* (computed here, with the file), *inferred* and *suggestion*. Check claims on disk before relying on them; this repo's notes have been wrong before.

### 2.4 The owner's standing views (from earlier sessions)

* **The thesis.** The edge on the market comes from point-level, per-statistic information, not from win/loss ratings. Rank results by the gain against the odds, never against Elo.
* **Betting may happen before the close.** The owner kept two inputs that tie at the close but help without odds or at Polymarket's price 24 hours out. So no-odds and 24-hour-price results matter alongside the close.
* **A null against the close is a process flaw to hunt, never a verdict** that the market is unbeatable. Name concrete process suspects.
* **Build and score in-session.** Do not stop for approval except where the owner asked for a gate.

## 3. The model to improve

The current best is the **local, non-thinking TabPFN-3.5 with 58 inputs**, after the owner's decisions of 6 Oct 2026 ([offset Elo](../../decisions/2026-10-06-offset-elo.md), [surface IOS profile](../../decisions/2026-10-06-surface-ios-profile.md)).

* **Frame.** `data/studies/surface_rating_race/model/model_frame.parquet`: 63,737 main-tour matches with closing odds, 2013–2026, both tours pooled. It has a `tour` context input and side A is random. The columns are `match_id, tour, season, tournament_date, a_won, p_mkt, debut_season, in_<input>`.
  * Inputs are listed in `model_inputs.json`, with kinds: `diff` (A − B, negated on flip), `pair` (exchanged on flip), `context`.
  * There are 45 diff inputs, 4 pair inputs (surface season and layoff) and 6 context inputs (tour, surface, level, indoor, best_of, round), plus odds_logit, Elo and the IOS and form profiles.
  * The model already carries **box-score serve form and IOS serve profiles** (aces, first in, first-/second-serve points won, holds).
* **Season counts.**

  | Tour | 2024 | 2025 | 2026 (to early Oct) |
  |---|---|---|---|
  | Men | 2,676 | 2,620 | 1,774 |
  | Women | 2,465 | 2,485 | 1,714 |

* **The harness** (`src/eda/feature_interactions/`):
  * `arms.py`: the arms, `load_frame`, `job_data` (train 2013..Y−1, test Y) and `flip`. New inputs are registered in a `features/registry.json` with a kind.
  * `local_fits.py`: one fit per (arm, season, seed). Settings: 8 estimators, softmax temperature 0.9, `ignore_pretraining_limits`, through `src/eda/tabpfn_local/runtime.py`.
    * Each fit predicts the season's matches as stored and flipped (`td`).
    * For 2025–2026 it also predicts with `odds_logit` replaced by Polymarket's price 24 hours (`early`) and 30 minutes (`late`) before the start (`data/studies/surface_elo_pieces/early_price_frame.parquet`).
  * `tabpfn_tests.py`: the scoring.
    * Forecasts are symmetrised and averaged over seeds.
    * **Decided calibration:** one slope per tour on the log-odds, refitted each season on all earlier out-of-sample seasons from 2019. So a new arm needs its own out-of-sample fits for 2019–2023 to calibrate 2024.
    * `paired_gain`: mLL with four-week-block intervals.
  * This study gets its **own copies** under `src/eda/serve_speed_tabpfn/`, with output to `data/studies/serve_speed_tabpfn/local/`. It never writes into another study's folders.
* **Existing base fits (read-only).**
  * Arm `model` (58 inputs): seeds 0–2 in `data/studies/surface_rating_race/local/`, seeds 3–15 in `data/studies/feature_interactions/local/`, seasons 2019–2026.
  * `model_noodds` (57, no odds): seeds 0–2 in the race folder.
  * One fit takes about 1–1.5 minutes on the RTX 5090.
  * **GPU budget for this study: about 4 hours** of fits in total.
* **Stage 0 versions.**
  * The model frame is built on the 30 September Stage 0, kept as `screen.PRE_REBUILD_STAGE0`.
  * `data/studies/predictability_diagnostic/stage0_matches.parquet` is the rebuilt one, and the new speed links point at it.
  * 40 women's 2026 model ids are absent from the rebuild. Men's ids agree. Join with care.

## 4. The speed data (what was "recently downloaded")

All paths are relative to the repo. **Observed**, from the [acquisition report](../serve_speed_acquisition/README.md) and this session's checks.

| Source | Where | What | Years, tours |
|---|---|---|---|
| Held point means | `data/studies/shot_level/stage1_match_stats.parquet` (`spd1_n` = sum of speeds of timed first serves in, `spd1_d` = their count, `spd1_src`; also `spd2_*`, `spd1_sq_*`) | Built from point tables `stage1_points_<source>.parquet` (`speed`, `serve_no`, `set_no`, `game_key`); one source per match; a match counts if ≥ 50% of first serves in are timed | `infosys` (ATP tour + qualifying): 224 / 2,380 / 3,111 / 3,978 player-matches in 2021–24, 16 in 2025. `sirgenkii` (decrypted ATP, Jan–Apr 2025): 682. `slam_pbp` (Sackmann Slams) ≤ 2021. `slam_tracking` (AO/RG Hawk-Eye copy) 2019–24. `slamtracker` 2019–2026 (≈ 470/yr per tour, 949 men 2026). Women: Slams only |
| **New: ManTennisData** | `data/studies/serve_speed_acquisition/speeds.parquet` rows `source == "mantennisdata"` (`ks_spd1` first-serve average, `ks_spd2`, `ks_max`, `ks_first_in`, `ks_first_total`; `match_id`, `side` linked to the rebuilt Stage 0) | The ATP Stats Centre's per-match **key statistic** (not point means), ATP tour level + some Challengers; no Slams; no match dates (placed by tournament start + round) | Men only: 490 / 3,108 / 3,742 / 4,930 / 3,458 / 4,684 player rows in 2021–26 |
| **New: AO and RG Infosys files** | same table, `source == "infosys_slams"` (`spd1_mean`, `spd1_n`, `spd2_*`, `fault1_*`, `spd_max`; RG `ks_*`); points in `data/dump/points/infosys_slams/points.parquet` (`serveSpeed`, `serve`, `set`, `game`, `currentMatchDuration`) | Point means from decrypted MatchBeats, main draw + qualifying | AO 2025, RG 2025, RG 2026; men 932 + 478, women 946 + 478 player rows (RG 2026 women's qualifying not linked) |

**Known measurement problems (observed unless marked):**
* **Two kinds of average.** ManTennisData's key statistic runs a median 0.5–0.6 km/h above the point mean on ATP points, with a long tail. RG's key statistic equals the rounded point mean.
  * On 2021–24, ManTennisData equals the decrypted ATP key statistics on all 5,847 matches checked. So, over the held Infosys point means, it adds only the key-statistic basis and the 2025–26 coverage.
* **Measuring systems differ by event family.** Men's offsets from the tour mean, frozen on matches to 2021: tour (Infosys) +5.34 km/h, Wimbledon +3.13, AO +0.37, USO −1.21, RG −2.49.
  * A 14-day window at a Slam against an Infosys-heavy 364-day window shows a false drop.
* **AO 2024**, in the held Hawk-Eye copy, reads about 3 km/h fast for the same players.
* **Untimed events.** Barcelona, Munich and Houston every year. Halle, Hamburg, Rotterdam, Dubai, Doha, Acapulco and Brisbane in 2025. WTA tour level has no speeds at all.
* **Implausible values.** Values outside 40–270 km/h count as missing. Men's values of 40–120 km/h are almost certainly errors.
* **Challengers 2021–24 are holed** in the held Infosys points (points without a shot group were dropped).
* **Disclosure: 2025–2026 is not fully blind for speed.** The shot-level study once scored its own speed-change feature (`x_shot`) against the close over 2022–26: +0.14 [−0.00, +0.28] mLL, positive = the feature better. That used the old, sparse 2025–26 coverage.
  * The feature-interactions study opened 2025–2026 once (7 Oct) for a different feature, B-INJ.
  * No study has related the new 2025–26 speed coverage to any result.

**The feature's coverage** (the point-sequence definition: both players have a timed match in the previous 14 days). Stage 0's main-tour main draws, men, after the acquisition (`data/studies/serve_speed_acquisition/coverage_feature_by_year.csv`, scenario N2):

| Men | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| Non-Slam | 196 / 1,996 | 875 / 2,139 | 1,057 / 2,210 | 1,345 / 2,210 | 995 / 2,151 | 941 / 1,758 |
| Slam | 190 / 508 | 286 / 508 | 253 / 508 | 311 / 508 | 329 / 508 | 325 / 508 |

Before 2021, men's coverage is Slams only (85–128 of 508 per year). Women's coverage is Slams only: about 12% of 2025–26 matches.

## 5. Prior evidence (published; do not re-derive it from results)

From the [point-sequence study](../point_sequence/README.md), section 5.6, and `data/studies/point_sequence/speed_prereg.md`:
* **Statistic** (`x_raw`). Per player, the mean first-serve speed (km/h) of timed first serves in over his matches with `obs` within the last 14 days, minus the same over 364 days. Match feature: A − B, standardised by a fixed SD (men 5.998), clipped at ±4 SD.
* **Results.** β is in log-odds per SD, given the 54-input model's walk-forward forecast or the close as an offset. Positive = the player whose speed rose more wins more often than the benchmark says.

  | Men | Matches | Given the model | Given the close |
  |---|---|---|---|
  | Discovery (Slams 2015–20, all of 2021) | 860 | −0.018 [−0.209, +0.174], tie | −0.026, tie |
  | Replication 2022–24 | 3,534 | **+0.090 [+0.017, +0.162]** | **+0.097 [+0.024, +0.170]** |

  * By season: 2022 +0.09, 2023 +0.13, 2024 +0.05.
  * Implied gain where the feature exists: +0.36 [−0.88, +1.59] mLL, a tie.
  * Women tie in both windows.
  * The event-family-centred variant (`x_evt`) correlates 0.97 with `x_raw`, and the shot-level variant (`x_shot`) 0.90.
* **Inferred there.**
  * It is a *state* (a recent change), not a trait. Speed level is a near-perfect trait (split-half 0.99).
  * Every other point-derived trait (momentum, leverage, tempo, style) failed.
  * The suggested next step was the "speed family" together: the 14-day change, the within-match speed fade, and box-score serve form.
* **Power** of a test of β = 0.09 (probably inflated) on the men's 2025–26 matches with the feature: about 54% after the acquisition.

## 6. The questions the team must settle

1. **Which statistic(s)?** The 14-day minus 364-day first-serve change as registered. Other representations: half-lives, posterior deviations, second-serve or maximum speed, the fault-serve speed, within-match fade, level. Which are worth a column, and which are only a gate?
2. **Harmonising sources and measuring systems.** Key statistic against point mean; event families; edition effects such as AO 2024; per-source offsets. All leak-proof.
3. **Players with little or no data.** Imputation, shrinkage, hierarchical or state-space priors, reliability inputs. Pick the defaults when nothing is known, and tune the constants on result-free targets ≤ 2023.
4. **How the information enters TabPFN.**
   * One diff column or several; pair columns; NaN against imputed values plus an indicator.
   * Women's Slam-only values in or out.
   * Whether TabPFN can learn a weak effect from about 4–6 thousand training rows that carry it, or whether a walk-forward logistic "nudge" (as feature-interactions' B-INJ) should be a secondary.
5. **The test.** Arms (at most 3 new arms with odds, plus their no-odds twins if the budget allows), seeds, calibration, the primary endpoint, secondaries, power, multiplicity and the decision rule. Fixed in a hashed pre-registration before any 2024–2026 result is read.

## 7. Process (rounds)

| Round | Who | Output |
|---|---|---|
| R1 design proposals (independent, parallel) | the speed-data engineer, the Bayesian state modeller, the integration strategist | `data/studies/serve_speed_tabpfn/design/1_<role>.md` |
| R2 audit and ruling | the auditor | `design/2_audit.md`: errors found, a ruling per question, the build spec |
| R2b rebuttal (only on contested points) | the proposers, through the lead | `design/2b_rebuttal_<role>.md`; the auditor's final ruling `design/2c_ruling.md` |
| R3 build | the engineer (panel), the modeller (features, tuning), the strategist (arms, fit runner, scorer) | code, tests, outputs |
| R4 verification | the auditor (red team: independent re-implementation, leak probe) and the test verifier (scorer on synthetic outcomes) | `design/4_redteam.md`, `design/4_verifier.md` |
| Freeze | the lead | `preregistration.md` + SHA-256 |
| R5 run and read | the lead runs the fits and the scorer once; the auditor checks the report against the outputs | `README.md` |

**A design proposal (R1) holds:**
* the recommendation in five lines;
* the definitions, written as formulas;
* the data and harmonisation;
* missing data and priors;
* how the feature enters TabPFN;
* the result-free gates and tuning targets;
* the leak argument;
* the expected effect and power;
* the GPU cost;
* the risks;
* the claims checked on disk, with the numbers and the script that computed them;
* a "Looks" section.

Keep it under about 2,500 words. Scripts go in `src/eda/serve_speed_tabpfn/design/`.
