# Lineage audit: how Challenger, qualifying and ITF matches reach the current best model today

9 October 2026 · Team role 01 (lineage auditor) of the lower-level-evidence study · Research evidence, not a decision.

**Note added by the lead (9 Oct 2026).** This report was written before the owner's [decision of 9 Oct](../../../decisions/2026-10-09-adoption-framework.md) that no comparison is called a "tie". Read "tie" here as "unresolved": the 95% interval spans 0. The [dossier](../README.md) gives P(better) where it quotes these readings. Its three code-level measurements (§2, §3) read the builds of 1–6 Oct: the same code, on the tables before the corrections of 8 Oct.

**The question.** For each of the 58 inputs and for stage 2's `spd_L`: does a match below the main tour enter as equivalent evidence, as opponent-adjusted evidence in a shared solve, as level-aware evidence, or not at all? And what happens to each input when the incoming lower-level data is wired into Stage 0?

**Keys.**
* *Observed* = read in the code (cited `path:line`) or computed here (cited file). *Inferred* = reasoning. *Suggestion* = a proposal.
* Buckets as in `src/eda/lower_level_evidence/common.py`: MAIN (main draws, 250 and up), TQ (tour qualifying), GSQ (Slam qualifying), CH (Challenger / WTA 125 main draws), CHQ, ITF, ITFQ, TEAM. "Lower" = TQ, GSQ, CH, CHQ, ITF, ITFQ.
* Level shifts are written as "lower level minus main tour, for the same player in the same season". **+ = the player looks better at the lower level.**
* Holdout: every value read from a result, a score or a box score is from events before 30 Dec 2024 (asserted in the code). 2025–2026 matches are only counted.

## In short

* **Observed. Every one of the 49 history-based inputs reads every level.** No builder filters by level, weights by level or adds a level term. The only level-aware pieces in the whole model are the `level` context input (the level of the match being forecast, never of the history) and stage 2's speed centring.
* **Observed. Lower levels are a large part of each input's evidence.** In main-tour matches of 2013–2024, lower-level matches make up, on average:
  * 52% of a player's Elo history (59% men, 63% women at the 250s);
  * 30% (men) / 24% (women) of the serve points behind `points_52w`;
  * 23% / 21% of the two-week form's weight, but 75% / 68% for qualifiers, whose own qualifying rounds feed their main-draw form;
  * 35% / 26% of the long-memory IOS weight.
* **Observed (new). The "opponent-adjusted" two-week form does not wash out the level.** Same player, same season, Challenger against main tour:
  * raw total points won is +3.6 points higher (men);
  * the one-step adjusted per-match value behind `adjperf_tpw_2w` keeps **78% of that shift** (+0.52 [+0.49, +0.54] in its own units, against +0.66 raw). Women: 77%. Qualifying: 79–83%.
  * So **17 inputs** (`adjperf_tpw_2w`, 12 `form_*`, 4 `formdef_*`) treat a lower-level match nearly as equivalent evidence. Thirteen carry a clear shift; the four serve-style ones (first serves in, double faults) barely move.
  * The reason is in the code: the opponent's "norm" is the plain average of what the opponent's own earlier opponents did against him, at whatever level he usually plays.
  * This corrects the event-levels study's statement that only `points_52w` is unadjusted.
* **Observed. The joint solves do wash it out, at Challenger and qualifying level.** Elo, the serve/return ratings (`ratings_iid`) and the IOS profile estimate every player together, so a weak opponent's weakness is measured.
  * Their residuals by level are within ±0.3 percentage points of serve points (Stage 3). For the IOS they are within ±0.08 SD of a match's value at every level, apart from an offset on break points saved that the main tour shares.
  * Whether this holds at ITF level cannot be checked: there is no ITF box score before 2025.
* **Contamination paths, by inputs touched:**
  * one-step forms: 17 inputs, measured;
  * raw `points_52w`: 1;
  * IOS products whose zero point is the pool's level (finding #6): 7;
  * one Elo K schedule for every level: 3, low harm;
  * missing lower-level matches after the June 2026 feed change: 5 directly, plus every box-score input's evidence for women.
* **Observed. The history's level mix already moves between seasons:**
  * men's Challenger-qualifying box scores are absent in 2010–2015 and thin in 2019;
  * women's 2015 has no lower-level box score at all;
  * ITF box scores exist only from January 2025 to May 2026;
  * after June 2026, Stage 0 holds no ITF match, no men's Challenger qualifying, and no women's qualifying or WTA 125. Women's live history is now almost main-tour-only, unlike every training season.
* **Forward risk, highest first:**
  1. ITF box scores (P7, P8, P1) reach 41 box-score inputs. They inflate the 17 forms and `points_52w` for ITF-active players, mostly women and qualifiers. They also move the IOS zero point in every season from 2018.
  2. Challenger speeds (P9, and the daily collector already enabled) enter the live `spd_L`. No history guard covers the speed panel.
  3. Results-only additions (P2, P4) mainly repair Elo and the workload counts.
  4. Point-by-point data (P5, P6) changes no current input.
  5. Odds below the 250s (P11) change no input.

## The master table

Verdicts: **EQUIVALENT** (a lower-level match counts like a main-tour one), **SHARED-ADJUSTED** (opponent-adjusted in a joint solve with no level term), **LEVEL-AWARE** (an explicit level weight or offset), **NOT-USED**.

| Inputs | Builder (main lines) | Levels entering | Lower-level treatment | Window / clock | Box score? | Verdict | Incoming-data risk |
|---|---|---|---|---|---|---|---|
| `odds_logit` (1) | `tabpfn_thinking/build_frame.py:111-112` | the match's own close (main tour only) | none | none | no | NOT-USED | none (P11 cannot reach it) |
| context: `tour`, `surface`, `level`, `indoor`, `best_of`, `round` (6) | `build_frame.py:113-125` | the match itself | `level` = this match's level only | none | no | NOT-USED | none |
| `age`, `age_sq` (2) | `stage4_features.py:1165-1170` | the match's own row | none | none | no | NOT-USED | none |
| `elo_overall`, `elo_surf_offset` (2) | `stage1_baselines.py:102-179`; `surface_elo_pieces/pieces.py:64-148, 305-346`; `arms.py:79-80` | all 8 buckets, 2010 on; completed + retired move it | one K(n) for all levels (`stage1_baselines.py:169-170`; offset `pieces.py:146-147`); K tuned on a pool 76% (men) / 42% (women) lower-level | whole history; tournament week + earlier rounds | no | SHARED-ADJUSTED (online, one K) | low: ITF qualifying and post-June-2026 results (P4, P2, P1) |
| `surf_season_a/b`, `surf_layoff_a/b` (4) | `pieces.py:210-236`; `arms.py:84-88` | all 8; played matches | plain counts and days | calendar season; last surface match (obs day), capped 3 years | no | EQUIVALENT | repaired by P2/P4/P1 (counts rise, layoffs fall) |
| `elo_games` (1) | `stage4_features.py:623-688, 706-750, 1124-1136` | all 8; completed + retired | Stage 1's K; each update × winner's games share ÷ the all-level 2010–18 mean (an ITF update weighs 5–8% more than a main-tour one on average) | whole history; tournament week | no (score) | SHARED-ADJUSTED (one K) | low |
| `sets_14d` (1) | `stage4_features.py:826-839, 1216-1222` | all 8; played | plain count of sets | events of the last 14 days + earlier rounds; tournament week | no (score) | EQUIVALENT | finding #7 now; P2/P4/P1 restore lost matches |
| `ratings_iid` (1) | `stage3_ratings.py:86-182, 204-218`; `stage4_features.py:1138-1153` | all 8 with a box score, completed only; ITF 2025–May 2026 only | online serve/return ratings vs each opponent's rating (from all levels); no level term | whole history with drift; tournament week | **yes** | SHARED-ADJUSTED | medium: ITF box scores 2018–24 (P7, P8) |
| `points_52w` (1) | `stage4_features.py:564-598 (574), 935-973 (959-962), 1055-1092` | all 8 with a box score (completed, standard format: `:184`) | **raw** serve and return points won, centred on the tour-surface average; no opponent term | last 364 days + earlier rounds; tournament week | **yes** | EQUIVALENT | **high**: ITF box scores inflate ITF-active players |
| `adjperf_tpw_2w` (1) | `ufc_ideas/stageB_adjperf.py:143-243, 374-430`; `stageB_common.py:153-263` | all 8 with a box score; ITF 2025–May 2026 | one-step adjustment: z vs the opponent's raw norm from his own (any-level) opponents; keeps 78% of the raw level shift | half-life 2 weeks; opponent norm 26 weeks to no decay; tournament week | **yes** | EQUIVALENT in effect | **high** |
| `form_*` (12), `formdef_*` (4) | as above; `stageD_profile.py:51-65` | as above | as above, per statistic: 13 of 17 keep a clear level shift | as above | **yes** | EQUIVALENT in effect | **high** |
| `ios_points_short` (1) | `match_timing/rebuild.py:179-221`; `ios_time.py:102-169`; `stageB_ios.py:435-442` | all 8 with a box score (`rebuild.py:87-113` admits ITF and team by their own score) | joint ridge solve O_server − D_returner, all players together; no level term | half-life 4 weeks (men) / 13 (women); leak-proof clock (in at lf + 1, read at es) | **yes** | SHARED-ADJUSTED | medium-low (shift-invariant matchup) |
| `iosO_*`, `iosD_*` (14) | `surface_ios/ios_surface.py`, `build_cache.py:33-36`, `build_features.py`, `arms.py`; `surface_rating_race/model_frame.py:47-61` | as above | joint ridge solve with player × surface deviations; no level term; ridge zero ≈ the pool's average player (*inferred*; finding #6 shows it moving) | per statistic, half-life 26 weeks to no decay; leak-proof clock | **yes** | SHARED-ADJUSTED | medium: more ITF evidence; ITF-level validity untested |
| `prod_*` (7) | `surface_ios/arms.py` (recipe); `rebuild.py:220` | as above | as above, but a product is not shift-invariant: the pool's level leaks in (finding #6) | as above | **yes** | SHARED-ADJUSTED with a level-dependent zero point | **high**: ITF box scores move the zero in every season from 2018 |
| stage 2 `spd_L` (men) | `serve_speed_tabpfn/panel.py:572-674`; `features.py:121-290`; `adaptive/columns.py:123-140`; `adaptive/adjust.py:89-120` | Slams (main + qualifying), tour (main + qualifying), Challengers (main + qualifying), a few team rows | each edition centred on its own offset, shrunk to its family (Slam / tour / ch / other × main / qualifying) | Kalman fast state, half-life 28 days; history 364 days; released rows only (lf + 1) | n/a (speeds) | LEVEL-AWARE (venue offsets) | **medium-high**: Challenger speeds from P9 and the live daily collector |

**Counting check.** 1 + 6 + 2 + 2 + 4 + 1 + 1 + 1 + 1 + 1 + 16 + 1 + 14 + 7 = 58.
* The 41 box-score inputs are the 41 that "read the same event's earlier rounds' box scores" in the prediction-run decision.
* Eight inputs read results only: the 2 offset-Elo inputs, `elo_games`, `sets_14d` and the 4 surface pairs.
* Nine read no history: `odds_logit`, the 6 context inputs, `age` and `age_sq`.

## The measurements behind the verdicts

All from `src/eda/lower_level_evidence/lineage_checks.py`; tables in `data/studies/lower_level_evidence/lineage/`.

### 1. How much of each input's evidence is lower-level

*Observed* (`evidence_shares.csv`):
* **What was measured.** Every player row of a frame match of 2013–2024 (115,528 rows of 57,764 matches). For each row, the share of the player's earlier evidence that is lower-level.
* **The weight per match.** Each input family's own weight, as listed in the table below.
* **The time rule.** The builders': earlier tournament weeks, plus earlier rounds of the same event.

| Input family (weight per earlier match) | Men: mean lower share | Men, at the 250s | Women | Women, at the 250s | Rows over half lower (men / women) |
|---|---:|---:|---:|---:|---|
| Elo, whole history (played match = 1) | 51% | 59% | 52% | 63% | 55% / 55% |
| Elo, last 364 days | 32% | 41% | 33% | 48% | 31% / 31% |
| `points_52w` (serve points, 364 days) | 30% | 39% | 24% | 35% | 29% / 19% |
| two-week form (box-score match, half-life 2 weeks) | 23% | 31% | 21% | 30% | 22% / 20% |
| long IOS (serve points, half-life 52 weeks) | 35% | 44% | 26% | 36% | 32% / 19% |
| `ios_points_short` (serve points, half-life 4 / 13 weeks) | 24% | 32% | 23% | 34% | 22% / 18% |
| `sets_14d` (played matches, 14 days) | 22% | 29% | 25% | 34% | 21% / 24% |

* **Where it comes from.** For men's box-score inputs the lower-level part is mostly Challengers: 21 of the 30 points of `points_52w`. For women it is mostly qualifying: 19 of 24.
* **ITF box scores.** The ITF part of every box-score input is 0 here: none exists before 2025.
* **ITF in the Elo history.** ITF makes up 15% (men) and 37% (women) of the whole Elo history.
* **The two-week form is bimodal.** The median player row has almost no lower-level form evidence, but a fifth of rows are mostly lower-level.
* **Qualifiers.** 13% of the frame's player rows are qualifiers or lucky losers, and a quarter of frame matches have one.
  * Their two-week form evidence is 75% (men) / 68% (women) lower-level, against 16% / 14% for direct entrants.
  * Qualifying shares the main draw's tournament id and date (checked on the 2019 ATP 250s), so the qualifying rounds count as "earlier rounds of the same event" for every per-player input and for the IOS's incremental step (`ios_time.py:129-164`).
  * **No input marks a player as a qualifier.**

### 2. The one-step opponent adjustment keeps most of the level shift

*Observed* (`adj_level_shift.csv`):
* **Source.** Stage B's per-match z (`data/studies/ufc_ideas/stageB_adj.parquet`, the 2 Oct build on the 30 Sep tables; the same code as the reference's chain), seasons 2013–2024.
* **The sample.** Player-seasons with at least three box scores at each of the two levels.

| Same player, same season | Player-seasons | Raw total points won | Raw, in z units | One-step z of total points (`adjperf_tpw_2w`) | Raw shift left |
|---|---:|---:|---:|---:|---:|
| Men: Challenger − main tour | 2,139 | +3.6 points | +0.66 | **+0.52 [+0.49, +0.54]** | **78%** |
| Women: WTA 125 − main tour | 740 | +3.1 | +0.53 | **+0.41 [+0.36, +0.45]** | **77%** |
| Men: tour qualifying − main | 1,840 | +3.8 | +0.70 | +0.55 [+0.52, +0.58] | 79% |
| Women: tour qualifying − main | 1,936 | +3.6 | +0.62 | +0.49 [+0.46, +0.52] | 79% |
| Men: Slam qualifying − main | 850 | +3.9 | +0.71 | +0.59 [+0.54, +0.64] | 83% |
| Women: Slam qualifying − main | 811 | +4.2 | +0.71 | +0.56 [+0.51, +0.61] | 79% |
| Men: Challenger qualifying − main | 237 | +5.5 | +1.01 | +0.77 [+0.68, +0.86] | 77% |

* **How big.** A match's z has an SD of about 1.2 on the main tour, so +0.5 is about 0.4 SD per match.
* **By statistic, men at Challengers.** Every skill statistic looks better at the lower level:
  * first-serve points won +0.41, holds +0.42, breaks +0.41, return points against the first serve +0.39;
  * second-serve points won +0.31, return points against the second serve +0.31, aces +0.25;
  * break points saved +0.17, converted +0.17;
  * break points faced per game −0.39 (fewer: better);
  * the defence mirrors: aces held down +0.26, opponents' break points per game −0.33 (more pressure: better).
* **The style statistics barely move:** first serves in +0.05, double faults −0.09, and their defence mirrors 0.00 and +0.03. Women show the same pattern, slightly smaller.
* **Why, in the code** (`stageB_adjperf.py:144-145, 195-207`):
  * z = (the player's value − E_o) / MAD_o.
  * E_o is the opponent's average "allowed" value, over the opponent's own earlier box-score matches at any level (memory h1 of 26 weeks to no decay; `stageB_adj_summary.json`).
  * So z measures the player against **the opponent's usual opponents**. A Challenger regular's usual opponents are Challenger players.
  * *Inferred:* the reference field drops with the level, which is why most of the raw shift survives.

### 3. The joint solves are level-consistent at Challenger and qualifying level

*Observed:* residuals of each server's observed value against the rating model's prediction, by the level of the match, 2013–2024.
* **Stage 3** (`stage3_residuals.csv`, from `stage3_ratings.parquet` of 1 Oct): serve points won minus expected, in percentage points.
* **Surface IOS** (`ios_residuals.csv`, from `surface_features.parquet` of 6 Oct): the centred log-odds value minus O_server − D_returner, in SDs of a match's value.

| | MAIN | TQ | GSQ | CH | CHQ |
|---|---:|---:|---:|---:|---:|
| Stage 3, men (points per 100 serve points) | +0.04 | +0.25 | −0.24 | +0.11 | +0.32 |
| Stage 3, women | −0.08 | +0.16 | +0.16 | −0.10 | +0.22 |
| IOS serve points, men (SD) | +0.05 | +0.02 | +0.00 | +0.03 | +0.00 |
| IOS serve points, women | +0.01 | +0.01 | +0.02 | −0.00 | −0.03 |
| IOS holds, men | +0.01 | −0.02 | −0.02 | −0.00 | −0.03 |
| IOS holds, women | +0.01 | −0.01 | −0.00 | −0.02 | −0.05 |

* **Across the other profile statistics** (aces, double faults, first serves in, first- and second-serve points won, holds): every level's mean residual is within ±0.08 SD.
* **Break points saved** are about −0.10 to −0.14 SD at every level, the main tour included. *Inferred:* a common offset of the small-sample transform, not a level effect.
* **Stage 3's extremes behave alike across levels:** over-predicted strong servers and under-predicted weak ones, slightly stronger at Challengers (men's extreme bins +2.55 / −0.79 points at Challengers against +1.70 / −0.56 on the main tour).
* *Inferred.* When the opponent's strength is estimated jointly from the whole connected history, a Challenger or qualifying match is informative but not inflating, on average. This is the "informative, not equivalent" behaviour the owner asks for.
* **Not testable on the allowed seasons:** the ITF level (no ITF box score before 2025), and individual players whose game transfers worse than average between levels.

### 4. What the inherited constants were tuned on

*Observed* (`tuning_pools.csv`; populations as named in the code):

| Constant | Population | Lower-level share, men / women |
|---|---|---|
| Elo K and surface weight (also the offset's kd) | evaluation matches 2013–2018 (`stage1_baselines.py:229`; `pieces.py:162`) | 76% / 42% (men: Challengers 45%) |
| Elo updates | every played match (`stage1_baselines.py:69, 204`) | 90% / 89% |
| games-Elo scale | played matches 2010–2018 (`stage4_features.py:706-722`) | 90% / 87% |
| Stage 3 surface mu | box-score matches 2010–2018, any level (`stage3_ratings.py:224`) | 73% / 35% |
| Stage 3 constants | evaluation levels 2013–2018 (`stage3_ratings.py:277`) | 75% / 36% |
| surface averages and shrinkage K of every box-score input | evaluation levels, completed, standard, 2010–2018 (`stage3_traits.py:765-767`) | 73% / 36% |
| Stage B form constants | evaluation pool 2013–2018 (`stageB_adjperf.py:262`) | 75% / 36% |
| Stage B population MAD, typical units (also the IOS's) | box-score rows 2010–2018, any level (`stageB_adjperf.py:149-171`; `stageB_common.py:175-186`) | 73% / 35% |
| IOS h, kappa, tau | evaluation-level matches 2013–2018 (`stageB_ios.py` docstring) | 75% / 36% |

*Inferred.*
* The men's constants are tuned mostly on Challenger and qualifying matches. They are optimal for that mix, not for main-tour forecasts. That is a fit question, not a bias.
* The surface averages are constant offsets: they cancel in A − B, except through the shrinkage of players with little evidence.
* The ITF regime does not touch any tuned constant (no ITF box scores before 2025), but it would if the constants were re-tuned after P7.

### 5. The history's level mix by season

*Observed* (`pool_composition.csv`, counts only; 2025–2026 included):
* **The box-score pool** (completed, standard format, with a box score) is lower-level in:
  * men: 69–79% of matches every season of 2010–2024, then 91.5% in 2025 (ITF 54%) and 87.5% in 2026 (ITF 37%);
  * women: 35–51%, then 89% in 2025 (ITF 74.5%) and 80.5% in 2026 (ITF 66%).
* **Gaps inside the training seasons:**
  * men's Challenger-qualifying box scores: none in 2010–2015, then 2,880–3,509 a season in 2016–2018, 260 in 2019, 368 in 2020;
  * men's Slam-qualifying box scores: none in 2016–2017;
  * women's 2015: main-tour box scores only.
* **The result pool** (Elo's) is 84–94% lower-level every season to 2025, and 86% (men) / 79% (women) in 2026.
* **The feed change of June 2026** (Stage 0 by month): Sackmann's files end on 25 May (main tour) and 1–2 June (lower tiers); Tennis My Life continues. From July 2026 Stage 0 holds:
  * ITF: none, either tour (393 men's and 427 women's matches in June);
  * men's Challenger qualifying: none (102 in June);
  * WTA 125: none (93 in June); WTA 125 qualifying: none after June;
  * women's tour qualifying: none from June;
  * women's Slam qualifying: none after the Australian Open.
* *Inferred.* Since July 2026 women's inputs are built on a history with almost no lower-level match, the opposite of every training season. Men keep Challenger main draws and tour and Slam qualifying.

## Each input group in detail

Items: (1) builder, (2) matches entering, (3) treatment, (4) memory and clock, (5) norms and tuning, (6) box-score dependence, (7) verdict.

**Offset Elo: `elo_overall`, `elo_surf_offset`.**
1. Stage 1's pass (`stage1_baselines.py:102-179`), reproduced and extended by `surface_elo_pieces/pieces.py:64-148` (offset mode `:144-147`), inputs `arms.py:79-80`: (R_A − R_B) and (D_A − D_B) in log-odds.
2. Every Stage 0 match of the tour, all 8 buckets, 2010–2026 (`pieces.py:292, 305-309`). Completed and retired matches move ratings; walkovers and "other" never do (`stage1_baselines.py:69`; `pieces.py:309`).
3. The same K(n) = k0 / (n + offset)^shape at every level, n = rated matches at any level (`stage1_baselines.py:169-170`). The surface offset has its own level-free K on the surface count (`pieces.py:146-147`). Opponent-adjusted through the expected score; the opponent's rating comes from all levels.
4. Whole history, no decay. Tournament week plus earlier rounds of the same event (`stage1_baselines.py:112-116`). Not the leak-proof clock (safe by construction under the timing decision).
5. K grid per tour on evaluation matches 2013–2018 (`stage1_baselines.py:226-246`): 76% (men) / 42% (women) lower-level. kd the same way (`pieces.py:157-180`).
6. No box score.
7. **SHARED-ADJUSTED** (online, one K). The event-levels study found it about calibrated across levels.

**Surface switches: `surf_season_a/b`, `surf_layoff_a/b`.**
1. `pieces.py:210-236`; `arms.py:84-88`.
2. All buckets; played matches (`pieces.py:198`).
3. Plain counts and days.
4. Calendar season (`pieces.py:217-221`); days since the last played match on the surface, on the timeline's best-estimate day (`:222-226`), capped at 3 years (`arms.py:33`).
5. Rules, no tuning.
6. No box score.
7. **EQUIVALENT.**

**`elo_games`.**
1. `stage4_features.py:725-750` (variants), `623-688` (pass), `1124-1136`.
2. All buckets; completed and retired.
3. Stage 1's constants (one K). Each update is multiplied by the winner's games share over the mean share of rated matches of 2010–2018 at every level (`:706-722, 744`).
   * *Observed:* the update weight averages 0.94 (men) / 0.96 (women) on the main tour, 0.97 / 0.96 at Challengers, 1.01 / 1.00 at ITF, 1.02 / 1.04 in ITF qualifying.
   * So an ITF update weighs 5–8% more than a main-tour one, because ITF matches are more lopsided.
4. Whole history; tournament week.
5. Scale on a 90% / 87% lower-level pool.
6. Score only.
7. **SHARED-ADJUSTED** (one K, mild up-weighting of lower levels).

**`sets_14d`.**
1. `stage4_features.py:826-839` (sums), `1216-1222`.
2. All buckets; played matches.
3. A plain count of sets. The input is missing if any played match in the window lacks a set count.
4. Events whose tournament Monday is within 14 days, plus earlier rounds of this event; tournament week.
5. None.
6. Score only.
7. **EQUIVALENT.**
* **The feed change (finding #7, confirmed in the counts).** Matches absent from Stage 0 since June 2026 do not count as missing; they make the player look rested.

**`ratings_iid`.**
1. `stage3_ratings.py:86-182` (pass), `204-218` (history), then `stage4_features.py:1138-1153` (the iid model's log-odds).
2. Every match gets values. Only completed matches with serve points for both players move ratings (`stage3_ratings.py:215`): retirements never do, and ITF only from January 2025.
3. Online Gaussian serve and return ratings: P(serve point) = expit(mu + S_server − R_returner), the returner's rating estimated from all levels. One variance and drift for everyone; no level term.
4. Whole history, with a rating's variance growing again with time away (`:141-145`); tournament week.
5. mu per tour and surface from box scores of 2010–2018 at any level (`:224`). Constants on evaluation levels 2013–2018 (`:277`).
6. **Yes.**
7. **SHARED-ADJUSTED**, level-consistent on average (measurement 3).

**`points_52w`.**
1. Stage 4's `mu_points|52 weeks`.
   * History sums of x − d·mu (`stage4_features.py:574`): raw counts against the tour's surface average.
   * The 52-week window (`:959-962`).
   * Each player's spw against the other's rpw combined around the average and passed through the iid model (`:1055-1092`, `:1079-1080`).
2. All buckets with a box score: completed, standard format (`:184`).
3. **Raw rates, shrunk toward the tour's surface average. No opponent term.**
4. Events starting up to 364 days before, plus earlier rounds; tournament week.
5. Surface averages and K from Stage 3 on the evaluation-level pool of 2010–2018 (`stage3_traits.py:187-200, 765-767`).
6. **Yes.**
7. **EQUIVALENT.**
* Its 52-week serve points are 30% (men) / 24% (women) lower-level, 39% / 35% at the 250s.
* A Challenger match adds about +3.6 points of total points won for the same player (measurement 2).

**`adjperf_tpw_2w`, `form_*` (12), `formdef_*` (4).**
1. `stageB_adjperf.py:143-209` (z), `374-430` (features); `stageB_common.py:153-172` (values), `197-263` (time rule); assembled in `stageD_profile.py:51-65`; names in `tabpfn_thinking/common.py:84-85, 101-106`.
2. All buckets with a box score (completed, standard, units > 0); ITF only January 2025 to May 2026.
3. One-step adjustment (measurement 2): about 78% of the raw level shift survives.
   * `formdef_*` is the same machinery seen from the opponent: how far the player held the opponent below the opponent's own norm (`:205-207`).
4. The player's z decayed with a half-life of 2 weeks and shrunk with K3 = 10–160 matches. The opponent's norm uses h1 = 26 weeks to no decay (frozen constants, `stageB_adj_summary.json`). Tournament week plus earlier rounds.
5. Surface averages as above. Population MAD on box rows of 2010–2018 at any level (`:149-171`). Constants tuned on the evaluation pool of 2013–2018 (`:262`).
6. **Yes.**
7. **EQUIVALENT in effect.** It is "opponent-adjusted" in name, but the reference field moves with the level.
* For a woman whose recent matches were results-only ITF matches (before 2025), the form shrinks toward 0, not toward her ITF level.

**`ios_points_short`.**
1. `match_timing/rebuild.py:179-221` (spw with the short half-life, `:199, 221`); `ios_time.py:102-169`; `stageB_ios.py:435-442`.
2. All buckets with a box score (completed). The leak-proof history rule admits ITF and team matches whose own score is standard (`rebuild.py:87-113`).
3. Joint ridge solve of y = O_server − D_returner over every player of the tour; shrinkage toward 0 (*inferred:* about the pool's average player); no level term.
4. Half-life 4 weeks (men), 13 (women) (registry `short_memory_h`). A result enters at lf + 1 and a match reads the solve at es (`ios_time.py:109-110`). For ITF matches the median window is 4 days and 55% have no exact day (`timing.parquet`), so their results enter the solve late.
5. kappa and tau of spw, tuned on evaluation-level 2013–2018. The memory was chosen on all seasons (feature-provenance study).
6. **Yes.**
7. **SHARED-ADJUSTED.**
* A common shift of all O and D cancels in O_A − D_B (`stageB_ios.py:440-441`).

**`iosO_*`, `iosD_*` (14).**
1. `surface_ios/ios_surface.py` (model, docstring lines 4-11), `build_cache.py:33-36` (the leak-proof rows), `build_features.py`, `arms.py`; frame `surface_rating_race/model_frame.py:47-61`.
2. As `ios_points_short`.
3. Joint ridge solve with each player's surface deviations shrunk to his all-surface value; no level term. Residuals level-consistent (measurement 3).
4. Per statistic half-life 26 weeks to no decay (registry version `2026-10-08_reference`); leak-proof clock.
5. Centred on Stage 3's surface averages; typical units of 2010–2018 at any level; Stage B's tuning on evaluation-level 2013–2018; surface penalties tuned 2013–2018.
6. **Yes.**
7. **SHARED-ADJUSTED.**
* The A − B differences cancel a common shift of the ratings.
* The ridge still shrinks a sparse player toward the pool's average player. For men, that is mostly a Challenger-level player.

**`prod_*` (7).**
1. `surface_ios/arms.py` recipe: prod = O_A·(−D_B) − O_B·(−D_A).
2–6. As the IOS ratings.
7. **SHARED-ADJUSTED with a level-dependent zero point.**
* A common shift (o₀, d₀) adds o₀(D_A − D_B) − d₀(O_A − O_B).
* When ITF players filled the pool in 2025 the level rose, and the products' spread grew 25–56% (input-data audit #6).
* Centring them removed the drift and tied in log loss (`docs/studies/ios_product_centring/README.md`).

## A. The serve-speed stage

* **Sources** (`panel.py` docstring lines 1-46; `live/live_panel.py:43-70`):
  * Slam point tables (slam_pbp, slam_tracking, slamtracker, infosys_slams, the AO match centre);
  * ManTennisData and the handoff's key statistics for ATP tour level and Challengers;
  * the ATP Stats Centre backfill of 2018 to Oct 2021 (225 usable rows);
  * since 8 Oct, the daily collector (`infosys_atp_daily`).
* **Levels in the frozen, corrected panel**, usable men's rows (`frozen/speed/speed_panel_frozen_corrected.parquet`): Slam main draws 9,988, Slam qualifying 1,848, tour main draws 13,834, tour qualifying 4,781, Challengers 1,231, Challenger qualifying 151, other 88 (ATP Cup 84; 4 rows of one ITF event). Women: Slams only, and `spd_L` is 0 for every woman (`adaptive/columns.py:135`; `adjust.py:120`).
* **Challenger speeds are already in, and jumped in 2026.** Usable Challenger rows: 167 (2022), 92, 94, 89 (2025), then 940 in 2026, all from ManTennisData and almost all from May 2026 on (86 in May, 266 June, 181 July, 233 August, 172 September). Counts only.
* **How levels are treated.**
  * **Edition centring is level-aware.** Each speed is y = α_player + γ_edition. Each edition's γ is shrunk to its family's mean with a prior worth 25 player-matches; the families are Slam, tour, `ch`, other, each split into main draw and qualifying. Zero is the tour main draws' average (`panel.py:621-653`; families `live_panel.py:83-85`).
  * So a Challenger venue's radar or court offset is removed, within a 364-day window of released rows (`panel.py:624`).
  * The player effect α is one number across levels.
* **The 28-day form.** A two-state filter: a slow level L and a fast state f with a 28-day half-life (`features.py:199-243`; `adaptive/columns.py:47`).
  * A Challenger speed is one observation like any other. Its noise depends on the basis (key statistic or point mean) and the serve count, not on the level.
  * spd_L = clip((f̂_A − f̂_B) / 1.9496, −4, 4).
* **The coefficients.** Fitted on main-tour frame matches 2019 .. Y−1 against the weekly feed's history (`adjust.py` docstring).
* **Verdict: LEVEL-AWARE** for venue offsets; otherwise each speed is one observation in the player's own series.
* **What P9 (ATP Stats Centre 2025–26, tour and Challengers) would change.** *Inferred.*
  * At non-Slam levels a key statistic outranks a point mean (`panel.py` docstring), so matches ManTennisData already holds keep their value.
  * New rows would be mostly Challenger and qualifying matches of 2025 to April 2026, which ManTennisData barely covers.
  * Effect: men active at Challengers get more readings in their 28-day window, so f̂ is less shrunk toward 0 and |spd_L| grows for them in 2025–26 only. That is an uneven change in the seasons that are both the holdout and the live period.
  * Edition offsets gain connections; main-tour γ moves slightly.
* **A gap in the guard.** *Observed.*
  * The daily collector is enabled (`live/collector.json`) and plans tour-level and Challenger matches (`live/atp_daily.py:132-145`: everything but Slams and team events). New daily rows enter `live/speed_panel_live.parquet` with no level filter (`live_panel.py:88-155`).
  * `current_best_model/history.py` checks Stage 0 only.
  * So new Challenger speeds reach the live `spd_L` without a candidate comparison. So far: 72 daily rows, 2 of them Challengers.

## B. Contamination paths

| Path | Status | Inputs touched | Evidence |
|---|---|---|---|
| B1. `points_52w` uses raw 52-week rates | **Confirmed** | 1 | `stage4_features.py:574, 959-962`; +3.6 points per Challenger match for the same player |
| B2. IOS products drift with the pool's level (ITF box scores) | **Confirmed** | 7 (second-order: `ios_points_short`) | algebra in `arms.py`; finding #6; centring ties |
| B3. One K schedule across levels in Elo | **Confirmed in code; low harm** | 3 (`elo_overall`, `elo_surf_offset`, `elo_games`) | `stage1_baselines.py:169-170`; event-levels calibration; games-Elo weighs an ITF update 5–8% above a main-tour one |
| B4. Workload after the feed change (finding #7) | **Confirmed**, wider than women's qualifying | `sets_14d` and the 4 surface pairs directly; Elo and every box-score input lose those matches | Stage 0 by month: no ITF from July 2026, no men's Challenger qualifying, no WTA 125 or women's qualifying |
| B5. The "opponent-adjusted" two-week form keeps the level shift (**new**) | **Confirmed, measured** | 17 | 78% of the raw shift left (measurement 2) |
| B6. Main-tour players' IOS ratings estimated mostly against lower-level opponents | **True for many players; no bias found at Challenger / qualifying level; open at ITF level** | 22 (14 + 7 + 1) | 44% of men's long-IOS weight at the 250s is lower-level; residuals ±0.08 SD |
| B7. Norms and pool means include lower levels | **Confirmed; mostly harmless** | the 41 box-score inputs, weakly | norms on pools 73% (men) / 36% (women) lower-level; constant offsets cancel in A − B, except through shrinkage of sparse players and the products' zero |
| B8. The form's opponent baseline is computed from all levels | **Confirmed**: the mechanism of B5 | 17 | `stageB_adjperf.py:144-145, 197` |
| B9. Constants tuned on all-level data | **Confirmed** | every tuned input | tuning pools 75% (men) / 36–42% (women) lower-level |
| B10. Qualifiers' qualifying rounds feed their main-draw inputs; no input marks a qualifier (**new**) | **Confirmed** | 17 forms most; every per-player input | 13% of frame player rows; their form evidence 75% / 68% lower-level |
| B11. The level mix moves between training seasons (**new**) | **Confirmed** | the 41 box-score inputs' composition | men's Challenger qualifying 0 / ~3,000 / 260 a season; women's 2015 main only; ITF only 2025–May 2026 |
| B12. Women's ITF is results-only before 2025: Elo sees it, the box-score inputs do not (**new**) | **Confirmed** | 41 vs 8 | 37% of women's Elo history is ITF; 0% of their box-score evidence |
| B13. Challenger speeds enter the live stage 2 unguarded (**new**) | **Confirmed** | `spd_L` | 940 Challenger rows in 2026; daily collector scope; `history.py` covers Stage 0 only |

## C. Forward risk when each incoming dataset is wired into Stage 0

None is wired in yet (`docs/studies/gap_downloads/collection-plan.md`, last section). Each would be "new past" under `history.py`, so a candidate, except the speed rows (B13).

| Dataset | What changes | Mechanism | Inputs that move | Direction for a main-tour player who also plays below (*inferred*) | Risk |
|---|---|---|---|---|---|
| **ITF box scores and points 2018–2026** (P7 SofaScore, P8 TennisLive, P1 ITF live API) | Box scores for ~200,000 ITF matches that are results-only today; ITF results after June 2026 | New box scores for results-only matches; thousands of weak players enter the IOS and Stage 3 pools; the pool's level moves in every season from 2018, not in 2013–2017 | All 41 box-score inputs; P1 also the 8 results inputs (post-June matches) | **Forms and `points_52w` rise** for ITF-active players (the ITF field effect, probably above the Challenger +0.5 z), mostly women ranked 100–300 and qualifiers. Their IOS O and D gain evidence; unbiased only if the additive model holds at ITF level (untested). **Products jump in scale from 2018**, uneven against 2013–17 | **High** |
| **Challenger point-by-point 2018–2026** (P5 TennisLive, P6 SofaScore, P9 Stats Centre) | Point logs; box scores only where Stage 0 lacks one (men's Challenger qualifying 2019–20, WTA 125 gaps, tour qualifying 2018–21) | No current input reads point-by-point; filled box scores act as above, at Challenger and qualifying level; a revised box score is a revision | Few of the 41, where box scores are filled | Small; forms and `points_52w` rise a little for players with newly filled matches. TennisLive's records usually lack the set-closing game: box scores built from them would undercount holds and break points | **Low** for the 58; their value is for new per-point inputs |
| **ITF qualifying results** (P4 listings) | Men's ITF qualifying for every season (today only ~200–270 a season in 2010–13); ITF after June 2026 | New results for players mostly below the main tour; Elo's match counts grow | Elo inputs, `elo_games`, surface pairs, `sets_14d`, for players who appear in main-tour matches years later | Earlier, slightly better-settled ratings for ITF graduates; K smaller by the time they reach the main tour | **Low** |
| **Women's ITF results after Sep 2026** (P2(b)); WTA editions since the batches (P2(a)) | Women's ITF results (Kaggle v29 to early September is on disk, not in Stage 0); WTA 125 and qualifying matches with statistics | Repairs the June 2026 feed change: results return to Elo and the counts; P2(a) returns WTA 125 and qualifying box scores | Women's results inputs (8); with P2(a), the 41 box-score inputs | Workload stops reading "rested", the surface counts rise, layoffs fall, and Elo gains a little from ITF wins. P2(a) restores some of the lower-level form evidence (and its inflation, B5) | **Medium**: it moves women's 2026 inputs back toward the training regime. It is also a policy question: should restoring a lost feed be a candidate? |
| **Challenger serve speeds 2025–26** (P9; the daily collector) | Many `ch` speed rows 2025–26 | More readings per 28-day window; new edition offsets | `spd_L` (men) | Larger \|spd_L\| for Challenger-active men in 2025–26 only; b̃ was fitted when Challenger speeds were rare (89 a season) | **Medium-high**, and unguarded |
| **Odds below the 250s** (P11) | Closing prices for Challenger, WTA 125 and ITF matches | No input reads another match's price. The frame keeps main-tour groups only (`tabpfn_thinking/build_frame.py:92, 132`) | none of the 58 | none, unless training rows are redefined (the event-levels study tested Challenger rows only without prices) | **None** for the inputs |

## Questions the code could not answer

1. **Does the additive rating model hold at ITF level?** There is no ITF box score before 2025, and 2025–2026 is the holdout. B6 and the first row of section C hinge on it.
2. **How large is the ITF field effect in the one-step forms?** Inferred larger than the Challenger +0.52 z. It is measurable only on 2025 box scores (holdout) or after P7 on 2018–2024.
3. **Does TabPFN undo the form inflation?** It sees `level`, `round` and `best_of` of the match being forecast, but nothing about the history's composition or the player's entry status. The share of lower-level matches exists in the feature universe (U-330), not in the model.
4. **Are Challenger radar speeds comparable?** Edition offsets remove a constant per edition, not a noisier or partly missing radar.
5. **Would TennisLive's partial point logs become box scores?** If so, holds and break points would be undercounted (set-closing games missing).
6. **Should restoring a feed lost in June 2026** (women's ITF, WTA 125, qualifying) be a candidate like a new source? The history rule treats it so.
7. **Would `compare.py`'s input check see player-specific contamination?** It flags tour-seasons whose SD or mean moves. Inflation confined to ITF-active players may move neither by 10%.

## What this means for the proposal (suggestions)

* **Start with the 18 inputs where a lower-level match acts as equivalent evidence:** the 17 one-step forms and `points_52w`. The joint solves already behave as "informative, not equivalent" at Challenger and qualifying level.
* **Ways to make the forms level-aware**, each to be compared as a candidate:
  * read each match against the joint solve's prediction (y − (O_server − D_returner)), not against the opponent's raw norm;
  * or add a per-level offset estimated from same-player-season contrasts like measurement 2, in the UFC spirit of "skew toward their record elsewhere, at a discount".
* **Decide once whether ITF box scores enter the IOS**, and centre the products on a fixed main-tour reference before they do (input-data audit #6).
* **Give the model the composition it cannot see:** a qualifier flag, or U-330's lower-level share. Then re-measure B5.
* **Extend the history guard to the speed panel**, or filter `spd_L` to the levels its coefficients were fitted on, before the daily collector brings Challenger speeds in bulk.
* **Add a player-stratified input check to `compare.py`:** the shift of each input for players whose evidence is mostly lower-level, beside the tour-season check.

## Files

| What | Where |
|---|---|
| Spot-check code | `src/eda/lower_level_evidence/lineage_checks.py` (`./python.sh src/eda/lower_level_evidence/lineage_checks.py [--stage0-dir …] [--only …]`) |
| Pool composition by tour, season, bucket (counts) | `data/studies/lower_level_evidence/lineage/pool_composition.csv` |
| Tuning populations | `…/lineage/tuning_pools.csv` |
| Evidence shares (summary; per player row) | `…/lineage/evidence_shares.csv`, `…/lineage/evidence_shares_rows.parquet` |
| One-step adjustment level shift | `…/lineage/adj_level_shift.csv` |
| Stage 3 residuals by level and predicted edge | `…/lineage/stage3_residuals.csv` |
| Surface IOS residuals by level | `…/lineage/ios_residuals.csv` |
| Run record | `…/lineage/lineage_checks.json` |

**Inputs read.**
* **Frozen** (`data/studies/current_best_model/reference_2026-10-08/frozen/`): Stage 0, the model frame, the timeline (`tables_later`), the speed panel.
* **Not frozen,** from the builds the previous model used, the same code as the reference's chain:
  * `data/studies/ufc_ideas/stageB_adj.parquet` and `stageB_adj_summary.json` (2 Oct);
  * `data/studies/predictability_diagnostic/stage3_ratings.parquet` (1 Oct) and `stage4_constants.csv` (1 Oct);
  * `data/studies/surface_ios/surface_features.parquet` (6 Oct).
* All are read only, and no outcome of 2025–2026 is read.
