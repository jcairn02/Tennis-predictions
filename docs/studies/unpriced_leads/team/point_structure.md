# Point structure: where results drift away from the points (B2 memo, round 1)

13 Oct 2026 · Role B2, the point-structure analyst ([brief](../briefs/02_point_structure.md), [shared context](../briefs/00_shared_context.md)) · Claude Opus 5.5, a subagent of session `e1ffc84e-fa2d-42f9-9d17-7c936a046c45` · Ideas: [point_structure_ideas.csv](point_structure_ideas.csv) · Scratch: `data/studies/unpriced_leads/team/point_structure/`

* **Outcomes read: seasons ≤ 2024 only.** Two sources:
  * stored per-season rows of earlier studies, filtered in code before printing (`predictability_diagnostic/stage4_results.csv`; `edge_anatomy/scan_inputs.csv`);
  * my `descriptives.py` → `descriptives.json`: the spread of tiebreak and break-point residuals per player-season, against pure luck.

  Nothing was compared with a result or a price. 2025–26: outcome-free counts only (§ 8 discloses one over-count).
* **Labels:** *observed* (a repository file), *inferred*, *suggestion*. No web source was used.
* **Keys:** z and β "+ = the player higher on the statistic beats the price" unless stated. mLL "+ = the statistic better".

## Summary

1. **The lens.** The close is built on results: wins, scorelines, rankings, and openers rated on them. The scoring hierarchy (points → games → sets → match) injects luck at every level.
   * A statistic built to be pure luck cannot be "already priced" as skill.
   * If the close moves with it, the close is wrong.
2. **The luck is large and is luck** (observed; 2013–24 men, 2019–24 women; player-seasons with 40+ analysed matches):

   | Luck per season | Men | Pure-luck spread | Women | Pure-luck spread |
   |---|---:|---:|---:|---:|
   | Tiebreaks won above expectation (SD) | 2.28 | 2.28 | 1.66 | 1.72 |
   | Break points saved above expectation (SD) | 8.9 | 9.2 | 9.9 | 9.8 |

   * The two are uncorrelated (r 0.02 and 0.00).
   * A tiebreak swings a best-of-three match by 0.5 wins in sets one and two, and by 1.0 in the deciding set.
   * So tiebreak luck alone moves a man's season by about ±1.2 match wins of 54 (*inferred*).
3. **Earlier signs that the close over-credits it** (observed, ≤ 2024). In Stage 4's walk-forward fits beside the close:
   * the raw 52-week **tiebreak record** is negative in all 11 men's and 12 women's seasons;
   * the **break-points-saved record** is negative in all 11 men's and all 6 women's seasons;
   * the women's **deciding-set record** is negative in 11 of 12.

   The model's own two-week break-points-saved input reads negative for men beside the close in all four eras of 2013–24 (z −1.68 to −0.80; edge_anatomy). Each reading is small, and Stage 4's predate the repairs; all point the same way.
4. **New against the pool.** The pool already has I-025 (one 13-week number inside a four-member block, never decomposed) and market_anchoring's men's hold/break luck (unresolved on 2019–2026). New here:
   * separate components;
   * expectations calibrated and frozen on 2010–12;
   * a rating-dynamics version;
   * a within-event version;
   * a ranking-points version;
   * women, and every level with box scores.
5. **Top five:**
   1. **PS01** tiebreak luck;
   2. **PS02** the results-rating luck gap;
   3. **PS03** break-point luck in four pieces (the serve-against-return lead, made into luck);
   4. **PS04** event-run luck and the flattering last scoreline;
   5. **PS05** serve-speed state extensions (men, partial data).
6. **A cheap, precise gate** (§ 4): the close's own loading on a luck statistic, holding point-based skill fixed. It reads prices, not outcomes, and it predicts the outcome coefficient: β ≈ −c.
7. **Resolution** (inferred). At −0.03 to −0.05 log-odds per SD, discovery (2013–24) reads z ≈ 3–5, and Look A alone z ≈ 1.2–2.1. Expect "unresolved, P(better) high" until the sealed matches are added.

## 1. Three ways the scoring structure leaves information unpriced

* **Luck read as skill.**
  * *Observed* (`predictability_diagnostic/stage2.md`). Given the points share:
    * tiebreaks explain 40.9 mLL of the result (men) and 24.9 (women); pure-luck replays give 46.6 and 29.9;
    * break points explain 2.9 and 0.2;
    * 4.36% of men's matches go to the player with fewer points;
    * over-performance on tiebreaks and break points persists between random halves of a career at −0.02 to 0.12, against 0.89 for serve points won.
  * *Inferred.* Rankings, Elo-like openers and the public's "he wins the tight ones" carry this luck as skill.
  * The model's point-based inputs ignore luck. Its win/loss inputs (`elo_overall`, `elo_games`, `points_52w`) hold luck diluted inside skill, so it cannot be isolated. edge_anatomy found the model loses nothing without them.
* **Mispricings below the margin survive** (*inferred*).
  * Each component moves a fair price by about 0.02–0.06 log-odds (0.5–1.5 points at evens), less than a bookmaker's margin.
  * No sharp can bet one alone, so the close need not remove it; only a bettor adding many nudges can.
  * Recreational money (BetOnline's close since Sep 2025) reacts to scorelines, which keep the luck.
* **States against the player's own normal.** The serve-speed change is the one point-level state that replicated (`point_sequence` § 5.6).
* **What is closed stays closed.** Clutch *as a skill* is dead: leverage ties exact shuffles, and B-CLUTCH did not replicate. Everything here runs the other way: lucky results make the close over-rate. The predicted sign is negative for the lucky player, and persistence near zero is the premise, not a flaw.
  * So I-009 (games route minus points route), dropped by a *skill* reliability gate (split-half 0.16 men, 0.27 women; `f08_clutch.py`) and never screened, deserves the luck test.

## 2. The long list (definitions in the CSV)

| Id | Statistic (A − B) | Rank |
|---|---|---|
| PS01 | Tiebreak luck: won minus iid expectation at the match's own serve rates | 1 |
| PS02 | Results-rating luck gap: Elo on results minus Elo on points-implied results; game and set parts | 2 |
| PS03 | Break-point luck: saved, faced, converted, chances, against calibrated expectations | 3 |
| PS04 | Event-run luck (escapes in this event's rounds) and the flattering last scoreline | 4 |
| PS05 | Serve-speed states: second serve, speed gap, fault speed, last-match fade (men) | 5 |
| PS06 | Close-set (from 5–5) and deciding-set luck | 6 |
| PS07 | Ranking-points luck: the share of 52-week points owed to luck | 7 |
| PS08 | I-009 re-framed: games-route minus points-route matchup, luck sign | 8 |
| PS09 | Women's unforced-error state (WTA advanced statistics) | 9 |
| PS10 | Return elasticity to server strength (non-additive matchup) | 10 |
| PS11 | Points-dominant losses minus fewer-points wins, last 10 matches | – |
| PS12 | Cheap-wins share (opponent retired or walked over) | – |
| PS13 | Escapes: match points saved recently (point sequences) | – |
| PS14 | Luck exposure, Σπ(1 − π), as a price-slope modulator | – |
| PS15 | Return and rally speed state (Hawk-Eye) | – |
| PS16 | Distance-run state (two Slams) | – |
| PS17 | Serving collapse in the last match (double faults, first serves in) | – |
| PS18 | Serve–return balance (a re-encoding: not new) | – |
| PS19 | Draw luck: ranking points per unit of opponent strength | – |
| PS20 | Lower-level luck behind an arrival's ranking | – |

## 3. Top ideas in depth

### Building blocks shared by every residual

* **Per match k (player i against j)** from `stage0_match_players.parquet`:
  * serve-point rate p = `spw_n`/`spw_d`;
  * holds `hold_n` of service games `hold_d` = G;
  * breaks `brk_n`;
  * break points saved S of faced F (`bp_saved_n`/`_d`);
  * converted C of chances Ch (`bp_conv_n`/`_d`);
  * tiebreaks `tb_won_n`/`_d`, games and sets won;
  * total points T (`tpw_n`).
* **From `stage0_matches.parquet`:** `best_of`, `score`, `status` (completed only; non-standard formats out).
* **Rules and the iid model:** the deciding-set rule `stage2_iid.deciding_set_rule`, and the iid functions `stage2_iid.game`, `tiebreak`, `set_win`, `match_win_by`.
* **Calibration, frozen:** every expectation curve is fitted once on completed 2010–12 box-score matches at all levels, by tour (and best-of where needed), then applied unchanged. Those matches all finished before 2013, so no discovery or test result enters a curve.
* **Aggregation** (own matches in order: safe by construction):
  * S^x_i = Σ_k 2^(−Δdays/h)·e^x_ik over earlier box-score matches at every level, with h = 91 days; secondaries h = 365 and a flat 52 weeks.
  * A sum, not a shrunk mean: each lucky win moves a results-based rating by about the same amount.
  * Companions: the decayed count, and a no-history flag (value 0).
* **Encoding** A − B; **registered sign** negative unless stated.

### 3.1 PS01 — tiebreak luck (rank 1)

* **Definition.** e^TB = `tb_won_n` − Σ over tiebreaks played of π_TB(p_i, p_j, L), where π_TB = `stage2_iid.tiebreak` and L = 10 for Slam deciding tiebreaks under the rule, else 7.
  * `stage2_matches.parquet` already holds `tb_exp_a` and `tb_over_a` (men 2010–26 at every evaluation level; women 2019–26). Women 2013–18 come from Stage 0.
  * The match rates include the tiebreak points, which biases π toward the winner and pulls e^TB toward 0: conservative. Check by p-bins on 2010–12.
* **Mechanism.**
  * A tiebreak settles a set on a dozen points, and its spread is exactly pure luck (Summary 2).
  * Yet it enters "won in straight sets", the round reached, ranking points and Elo as skill.
  * The close inherits it through results-based anchors and recreational money (inferred).
* **Data, coverage and timing.**
  * On disk.
  * Main-tour box-score matches in 2025: 2,637 men's and 2,485 women's.
  * Tiebreaks per match are stable at about 0.50 (men) and 0.25 (women), 2013–26.
  * Live once the previous rounds' box scores are fetched (the refresh already does this).
* **Overlap.** No model input carries tiebreaks; only the `elo_*` and `points_52w` ratings hold it, diluted. Pool: none (U-207 is Stage 4's raw record, unstored). Expected R² with the 56 inputs below 0.15 (inferred).
* **Earlier evidence** (≤ 2024).
  * Stage 4's raw 52-week record (season reliability 0.06) has a coefficient beside the close below 0 in every season: men −0.003 to −0.024, women −0.021 to −0.043. Its out-of-sample gain is +0.09 mLL (women) and −0.04 (men).
  * A residual removes the record's skill part, so its coefficient should be larger (inferred).
  * Stage 4 predates the feature-alpha repairs: pointers only.
* **2025–26 exposure: partly, weakly.** Stage 4's sentence on the tiebreak record *given Elo* pools 2013–2026. No 2025–26 reading against a price.
* **Test.** The harness's per-era fit beside the close and beyond the 2020–24 forecast, then § 4's gates, then one-sided inside the bundle (§ 7). Likely resolution: discovery resolves at ≤ −0.03 per SD; confirmation alone does not.
* **Kill.** A pooled coefficient ≥ 0, or eras decaying to 0 by 2023–24; a market loading c ≤ 0; R² > 0.5.

### 3.2 PS02 — the results-rating luck gap (rank 2)

* **Definition.** Expectations fitted once on 2010–12 by tour × best-of (symmetric, no intercept):
  * points-implied, logit Λ_P = β(T_i − T_j)/√(T_i + T_j);
  * games-implied, logit Λ_G = γ(games_i − games_j)/√(games played).
  * Then e^match = y − Λ_P = e^set + e^game, with e^set = y − Λ_G and e^game = Λ_G − Λ_P.
  * I-025's β(t − ½) form is the sensitivity.
* **The new part: same-dynamics ratings.**
  * Run `stage1_baselines.py`'s Elo twice: once on y, once with Λ_P substituted for y wherever a box score exists.
  * Gap = R(y) − R(Λ_P), pre-match, in log-odds.
  * A third run on Λ_G splits the gap into set luck, R(y) − R(Λ_G), and game luck, R(Λ_G) − R(Λ_P).
  * It measures the luck a results-based rating carries now, with Elo's memory (counted in matches, larger for new players).
* **Overlap.** `elo_overall` (≈ R(y)) and `ratings_iid` are inputs, but their difference mixes memories and adjustments; the same-dynamics gap is not formable from them. Expected R² 0.2–0.4. Pool: U-278 (I-025), U-015 (`elo_games` *weights* updates; it does not substitute results).
* **Earlier evidence.**
  * B-OVERREACT (I-025 inside): z +2.13 beyond the model and +2.27 beyond the price, 2014–24, both windows positive.
  * Stage 4: luck corrects Elo downward.
* **2025–26 exposure: partly.** market_anchoring's men's hold/break luck (uncalibrated iid, `src/eda/market_anchoring/luck.py`) read −0.01 [−0.10, +0.09] mLL on 2019–25 and +0.28 [−0.07, +0.62] in 2026. I-025 is unseen.
* **Kill.** As PS01; if only the set part carries signal, PS01/PS06 are the efficient form.

### 3.3 PS03 — break-point luck in four pieces (rank 3)

* **Definition.** s̄(p) is a weighted logistic of saves on logit p; φ̄(p) is the iid break points per service game (`f08_clutch.bp_per_game`) times a tour constant. Both are frozen on 2010–12.
  * save luck: S − F·s̄(p_i), sign −;
  * faced luck: F − G·φ̄(p_i), sign +;
  * conversion luck: C − Ch·(1 − s̄(p_j)), sign −;
  * chance luck: Ch − G_opp·φ̄(p_j), sign −.
  * Hold luck ≈ save luck − (1 − s̄)·faced luck (verify numerically).
* **Why calibrate.**
  * Against the match's own rate, men "save" 59.25% where 58.41% is expected (Stage 2), an artefact that varies with serve strength.
  * market_anchoring's naive G(p) leaked that into its residual (inferred).
* **Mechanism.**
  * The close credits holds. Holding by saving break points (persistence 0.07–0.11) is luck; not facing them is skill (break points faced per game has a season reliability of 0.71).
  * This is the luck reading of edge_anatomy's "men's serving over-rated". It also separates mechanisms: put the four residuals beside `iosO_hold` and `iosO_bp_saved`. If the residuals take the negative weight and the profile's serve terms go to 0, luck is the mechanism; otherwise it is a mis-weighted genuine serve skill.
* **Data.** On disk (`stage2_matches.parquet` holds the naive `bp_save_over_a/_b`). Hold and break counts exist for 99.4% (men) and 97.9% (women) of matches; women's service-game counts cover 74% of 2013–21.
* **Overlap: medium-high**, the largest re-encoding risk here. `form_bp_saved`, `form_bp_faced_pg`, `form_bp_conv`, `form_brk` and `iosO/D_bp_saved` are raw rates; the residuals are their luck part, orthogonal to p.
* **Earlier evidence** (≤ 2024).
  * Men's `form_bp_saved` reads negative in all four eras (z −1.35, −0.80, −0.86, −1.68), and so does `form_bp_faced_pg` (−1.37, −0.42, −1.73, −2.45). Given holds, facing many and saving many is over-rated.
  * Stage 4's raw break-points-saved record is negative in all 11 men's seasons.
  * Men's break-point play carries about 20% signal on 100 matches (Stage 2), so expect a small skill offset on the save piece.
* **2025–26 exposure: partly.** It is motivated in part by edge_anatomy's 2025–26 ledger (men's holds −4.4, saved −3.9, two-week saved −2.8) and by market_anchoring's 2019–26 reading.
* **Kill.** All pieces ≥ 0; R² > 0.5; or the profile's serve terms keep their weight with the residuals at 0.

### 3.4 PS04 — event-run luck and the flattering last scoreline (rank 4)

* **Definition.**
  * **Run luck:** Σ (y_k − Λ_P,k) over the earlier matches at this event, qualifying included. For a player still in the draw this is mostly Σ(1 − Λ_P,k): how much of his run he did not earn on points. Missing: 0, with a flag.
  * **Flattery:** for the previous match, logit(games share) − κ·logit(points share), with κ the 2010–12 slope.
  * Signs negative.
* **Mechanism.**
  * The recreational market prices how the last match *looked*; sharp models price points, and a recreational close keeps the gap (inferred).
  * It separates rhythm (+: matches played here, U-138, a tier-A near miss at z +3.29) from luck (−) inside one deep run; `sets_14d` mixes them.
* **New against I-086 (U-280).** I-086 is the last win's *price* surprise. A dominant underdog win is information; a favourite's escape is luck.
* **Data.** On disk. About 55–57% of main-tour matches have an earlier match at the event. Live as soon as the previous round's box score is.
* **Exposure:** no.
* **Kill.** Run luck ≥ 0, or it only re-sizes U-138.

### 3.5 PS05 — serve-speed state extensions (rank 5; men)

* **Definitions.** Each is a 14-day minus own 364-day mean, per SD, centred by event-year (a cross-player step: clock and `probe.py`):
  * (a) second-serve speed;
  * (b) the first-to-second speed gap (a shrinking gap means more risk);
  * (c) fault speed minus in-serve speed;
  * (d) the previous match's first-serve speed, last third of service points minus first third, against the player's own normal fade, controlled for length.
* **Mechanism.** A physical or confidence state shows in the radar before the results do, and no market watches it. The base first-serve state replicated (+0.090 [+0.017, +0.162] per SD, 2022–24).
* **Overlap.** `spd_L` is first-serve form, so (a), (b) and (d) are other channels and (c) is new. Pool: U-198, U-137. The scout's #1 listed them as untested.
* **Exposure: partly** (the base signal's 2025–26 results).
* **Data:** § 6.
* **Kill.** Split-half below 0.3; or, on ≤ 2024, no prediction of next-match first-serve points won beyond `spd_L`.

## 4. A gate for any "luck read as skill" statistic: the close's own loading

* **The regression:** L_close = Z·b + c·x + ε, per tour and era, clustered by four-week block.
  * Z holds point-based skill only: the IOS inputs, `form_*`, `formdef_*`, `adjperf_tpw_2w`, `ratings_iid`, context, schedule and body; *not* `elo_*` or `points_52w`.
* **Why it is precise.** It reads prices, so its noise is the price's small disagreement with Z, not a coin flip (inferred).
* **What it predicts.**
  * For pure luck (PS01), β beside the close ≈ −c.
  * c > 0 with β ≈ −c confirms the mechanism.
  * c ≈ 0 kills the over-rating story whatever β shows.
* **When.** Run it on ≤ 2024. On 2025–26 it is a registered secondary under the lead's rule.
* **Companion:** BetOnline's open-to-close move on x, 2018–24 (`bet_timing/frame.parquet`).
  * A move *against* luck means it is learned by the close (an early-bet edge).
  * No move with β < 0 means it is never priced.

## 5. Serving against returning

* **Not new.**
  * Return points won "against the server's norm" is the IOS defence side.
  * Serve share of dominance (PS18) is a contrast of `iosO_*` and `iosD_*`.
* **New.** PS03 splits holds and breaks into luck and skill, with § 3.3's mechanism-separating fit. edge_anatomy's own hypothesis ("serving dominance and clutch break-point saving are visible and memorable … but partly luck") becomes directly testable.
* **The structural alternative:** PS10, return elasticity.
  * Per returner, a shrunk slope of match return residuals (logit rpw minus the leak-proof IOS prediction) on the server's O.
  * Matchup term: b_A(O_B − Ō) − b_B(O_A − Ō).
  * It needs the clock and `probe.py`, and a reliability gate first, which similar splits (U-098, B4) failed.
* **Exposure: partly** for all of § 5 (edge_anatomy's 2025–26 men's ledger).

## 6. Partial point and tracking data

From a read-only Explore catalogue (13 Oct; row and fill counts only).

| Need | Discovery (≤ 2024) | 2025–26 | Gap, route |
|---|---|---|---|
| PS05 (a, b) | ManTennisData match averages incl. second serve (`data/dump/matches/mantennisdata/`, Oct 2021–); ATP Stats Centre per point 2018–Oct 2021 (`data/dump/points/infosys_atp/`); Slams; panels' `spd2` (`serve_speed_tabpfn/live/speed_panel_*.parquet`) | ManTennisData, about 1,700 tour matches in 2025; Slams | none for men; women only at Slams (`serve_speed_acquisition` § 5) |
| PS05 (c) | per-serve records with faults: ATP Court Vision 2021–24 (`data/raw/public_dump/atp_pipeline_handoff/court_vision/`, about 4,450 matches linked, 93% of faults timed); AO/RG Hawk-Eye 2019–24 (`data/dump/points/slam_ball_tracking/`, 2,027) | AO 2025, RG 2025–26 (`data/dump/points/infosys_slams/`, fault speeds 96–98%); **ATP non-Slam not on disk** | collection package P9 (`gap_downloads/collection-plan.md`: about 10,800 matches, 60–90k requests; decryption approved 8 Oct) |
| PS05 (d) | the same, plus Wimbledon and US Open SlamTracker (speed of the serve that started each point; fill 47–56% / 91–95%) and Sackmann's Slam archive | AO/RG; Wimbledon (95%); US Open | ATP non-Slam needs P9 |
| PS09 | WTA advanced statistics 2022–24, unforced-error totals (91–92% filled; about 3.6–4.2k singles a year; `data/dump/points/wta/advanced/`) | 2025: 97.5% filled | three discovery seasons; crediting may shift by event: centre by event-year (clock) |
| PS13 | `point_sequence/sequences.parquet` score replays (usable: men 66,300, women 30,636, 2013–24) | 2025: men 4,293, women 5,122 | model-frame coverage 87–98% |
| PS15 | AO/RG `returnSpeed` (33%), trajectories; Court Vision has no per-shot speed | nothing tracked | too thin |
| PS16 | Wimbledon and US Open distance run (Sackmann from 2015) | the same Slams | B1's lens |

*Inferred.* The luck family (PS01–04, PS06–08, PS11–12) needs only Stage 0 box scores and scores, at every level that has them:
* men's Challengers 99% and WTA 125 94% (observed, 2013–26);
* tour levels 88–99%;
* ITF about 10%.

The data-hungry states are one-tour and have at most three discovery seasons, hence their lower ranks.

## 7. Suggested lead group: "conversion luck read as skill"

* **Members** (A − B, h = 91 days):
  * PS01;
  * PS06;
  * PS03's four pieces, faced luck sign-flipped;
  * PS04's run luck.

  PS02's gap is the one-number alternative, registered as a secondary.
* **Bundle score:** each member divided by its 2013–24 RMS, oriented by its registered sign, and summed.
  * Equal weights by default; inverse-variance weights from discovery as the alternative.
  * The weighting is chosen before any confirmation.
* **Frozen test:** one-sided beside the close (primary) and beside both stages (secondary), clustered, on Look A and then Look B. Expected z ≈ 1.2–2.1 on Look A for a true −0.03 to −0.05 per SD.
* **Gates before registration** (≤ 2024):
  * bundle discovery z ≤ −2;
  * market loading c > 0;
  * R² with the 56 inputs < 0.5.
* **Diversity:** pure point structure, with no schedule, body or market inputs.

## 8. Process notes

* **Read:**
  * CLAUDE.md, this study's process log and briefs;
  * edge_anatomy's README and its scout memo;
  * `feature_universe` (README; `universe.csv` rows U-069, U-095–U-098, U-125–U-127, U-137, U-143–U-145, U-198–U-259, U-277–U-281, U-322–U-329);
  * `next_candidates.md`;
  * the code of `f18_overreact.py`, `f08_clutch.py` and `market_anchoring/luck.py`, with market_anchoring § 6.6–7;
  * `predictability_diagnostic` Stage 2, Stage 4 §§ 2–3 and `candidates.md` § 3.1;
  * the `point_sequence`, `shot_level` and `point-shot-ideas` READMEs.
* **Computed:** the Stage 4 given-market rows (tiebreak, break-point, deciding-set, sets and games records; seasons ≤ 2024); edge_anatomy's scan, eras 2013–24; `descriptives.py`.
* **Deviations, disclosed:**
  * My first `descriptives.py` run counted 2026 main-tour box scores and tiebreaks played *including* matches after 28 Jul 2026. These are symmetric counts that reveal no winner. The script now drops those matches by the clock's latest finish before reading, and the file was replaced.
  * The Explore catalogue's 2026 row counts may also include the sealed period. Only its 2025 counts are quoted here.
* **Threats to validity:**
  * Stage 4 predates the repairs.
  * The 2010–12 curves may drift with format changes (Slam rules are handled).
  * Luck sums correlate weakly with load (lucky players stay in draws), so test them beside `sets_14d` and U-138.
  * PS03 is collinear with in-model rates.
