"""Writes docs/studies/unpriced_leads/team/point_structure_ideas.csv (B2's ideas list). No data is read.
Run: ./python.sh data/studies/unpriced_leads/team/point_structure/write_ideas_csv.py
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "docs" / "studies" / "unpriced_leads" / "team" / "point_structure_ideas.csv"
COLS = ["id", "name", "area", "definition", "encoding", "mechanism", "data_paths", "data_status", "coverage_note",
        "model_overlap", "pool_rows", "prior_evidence", "exposed_2025_26", "timing_class", "build_hours", "your_rank",
        "notes"]
S0 = ("data/studies/predictability_diagnostic/stage0_match_players.parquet (spw_n/d, tb_won_n/d, hold_n/d, brk_n/d, "
      "bp_saved_n/d, bp_conv_n/d, games_won_n/d, sets_won_n/d, tpw_n/d); stage0_matches.parquet (score, best_of, status, "
      "level, round)")
AGG = ("Decayed sum over the player's earlier completed box-score matches at every level, weight 2^(-days/91) "
       "(secondary 365 d and flat 52 weeks); expectation curves frozen on 2010-2012; A - B; registered sign negative")

rows = [
    dict(id="PS01", name="Tiebreak luck", area="conversion_luck",
         definition=("Per match: tiebreaks won minus sum over tiebreaks played of pi_TB(p_i, p_j, L), the iid tiebreak "
                     "win probability at the two players' own serve-point rates in that match (L = 10 for Slam deciding "
                     "tiebreaks under the rule, else 7; stage2_iid.tiebreak). " + AGG + "."),
         encoding="diff",
         mechanism=("Tiebreak outcomes are luck (season spread = pure iid spread, 2.28 tiebreaks for men 2013-24) but "
                    "enter scorelines (straight sets), round reached, rankings and results-based ratings as wins; "
                    "a 0.02-0.06 log-odds shift is below the margin, so sharps cannot bet it alone and the close keeps it"),
         data_paths=S0 + "; data/studies/predictability_diagnostic/stage2_matches.parquet (tb_exp_a, tb_over_a); src/eda/predictability_diagnostic/stage2_iid.py",
         data_status="on_disk",
         coverage_note=("Both tours, every level with box scores (men CH 99%, WTA125 94%, tour 88-99%, ITF ~10%); "
                        "stage2_matches has men 2010-26 and women 2019-26 already, women 2013-18 to compute from Stage 0; "
                        "main-tour box-score matches 2025: M 2,637 / W 2,485; 2026 to 28 Jul: M 1,620 / W 1,502; ~0.50 (M) / 0.25 (W) tiebreaks per match"),
         model_overlap="low (diluted inside elo_overall, elo_games, points_52w; no tiebreak input)",
         pool_rows="none as a residual (U-207 is Stage 4's raw record, not stored)",
         prior_evidence=("Stage 4 (predictability_diagnostic/stage4_results.csv, seasons 2013-2024 read): raw 52-week "
                         "tiebreak record beside the close has a negative walk-forward coefficient in 11/11 men's and "
                         "12/12 women's seasons, mean OOS gain W +0.09 / M -0.04 mLL; Stage 2: persistence 0.06 vs luck "
                         "(2010-26 pooled, in-match); pre-repair pipeline: pointers only"),
         exposed_2025_26=("partly (weak): Stage 4's text sentence on the tiebreak record given Elo pools 2013-2026; no "
                          "2025-26 reading against a price used"),
         timing_class="own_sequence", build_hours="4", your_rank="1",
         notes=("Expectation uses the match's own rates (includes tiebreak points: conservative bias toward 0); check "
                "calibration by p-bins on 2010-12. Gate: market loading c > 0 (memo section 4). Bundle with PS03, PS04, PS06.")),
    dict(id="PS02", name="Results-rating luck gap (Elo on results minus Elo on points-implied results)",
         area="conversion_luck",
         definition=("Run stage1_baselines' Elo twice over Stage 0: with the result y, and with Lambda_P substituted for "
                     "y where a box score exists (logit Lambda_P = beta_tour,bo * (T_i - T_j)/sqrt(T_i + T_j), T = total "
                     "points won, fitted once on 2010-12). Gap = R(y) - R(Lambda_P) pre-match, in log-odds; a third run "
                     "with Lambda_G (games-implied) splits it into set luck R(y)-R(Lambda_G) and game luck R(Lambda_G)-R(Lambda_P). "
                     "Companion decayed sums of y-Lambda_P, y-Lambda_G, Lambda_G-Lambda_P (h 91 d)."),
         encoding="diff",
         mechanism=("Measures the luck a results-based rating (the kind openers and the public use) carries now, with "
                    "Elo's own memory; the close over-rates the lucky if it leans on results"),
         data_paths=S0 + "; src/eda/predictability_diagnostic/stage1_baselines.py (Elo pass); src/eda/feature_interactions/features/f18_overreact.py (I-025 reference)",
         data_status="on_disk",
         coverage_note="As PS01; every main-tour match with a rated history",
         model_overlap="medium (elo_overall ~ R(y); ratings_iid points-based; the same-dynamics difference is not formable from them)",
         pool_rows="U-278 (I-025, 13-week match luck, inside B-OVERREACT U-277); U-015 (games-weighted Elo, not a substituted result)",
         prior_evidence=("B-OVERREACT block incl. I-025: z +2.13 beyond the model / +2.27 beyond the price, 2014-24, both "
                         "windows positive, never decomposed (feature_interactions/next_candidates.md); Stage 4: luck "
                         "corrects Elo downward (given Elo)"),
         exposed_2025_26=("partly: market_anchoring's men's decayed hold/break luck (uncalibrated iid) read on 2019-2025 "
                          "(-0.01 [-0.10,+0.09] mLL) and 2026 (+0.28 [-0.07,+0.62]); I-025 itself unseen"),
         timing_class="own_sequence", build_hours="8", your_rank="2",
         notes="I-025's beta*(t-1/2) form as a sensitivity. Expected R2 with the 56 inputs 0.2-0.4 (inferred)."),
    dict(id="PS03", name="Break-point luck in four pieces (saved, faced, converted, chances created)",
         area="conversion_luck",
         definition=("Per match: save luck S - F*sbar(p_i); faced luck F - G*phibar(p_i); conversion luck C - Ch*(1 - sbar(p_j)); "
                     "chance luck Ch - G_opp*phibar(p_j); sbar = weighted logistic of saves on logit p, phibar = iid "
                     "break points per service game (f08_clutch.bp_per_game) times a tour constant, both frozen on 2010-12. "
                     "Four decayed sums (h 91 d), A - B. Signs: save -, faced +, conversion -, chance -. Hold luck ~ save luck - (1 - sbar)*faced luck."),
         encoding="diff",
         mechanism=("The close credits holds; holding by saving break points (luck, persistence 0.07-0.11) is rated like "
                    "holding by not facing them (skill, reliability 0.71). Luck reading of the men's serving-over-rated / returning-under-rated lead"),
         data_paths=S0 + "; data/studies/predictability_diagnostic/stage2_matches.parquet (bp_save_over_a/_b, naive); src/eda/feature_interactions/features/f08_clutch.py",
         data_status="on_disk",
         coverage_note="Hold/break counts in 99.4% (M) / 97.9% (W) of evaluation matches; women's service-game counts 74% of 2013-21",
         model_overlap="medium-high (form_bp_saved, form_bp_faced_pg, form_bp_conv, form_brk, iosO/D_bp_saved are raw rates = skill + luck)",
         pool_rows="none stored (market_anchoring's hold/break luck lives in its own table)",
         prior_evidence=("edge_anatomy scan_inputs.csv, eras 2013-24: men's form_bp_saved z -1.35/-0.80/-0.86/-1.68 and "
                         "form_bp_faced_pg -1.37/-0.42/-1.73/-2.45 beside the close; Stage 4 raw 52-week bp_saved "
                         "coefficient negative in 11/11 men's seasons and 6/6 women's (2019-24); Stage 2 naive "
                         "expectation biased (+0.8 pp saves)"),
         exposed_2025_26=("partly: motivated in part by edge_anatomy's 2025-26 ledger (men's holds -4.4, bp saved -3.9, "
                          "two-week bp saved -2.8) and market_anchoring's 2019-2026 hold/break luck readings"),
         timing_class="own_sequence", build_hours="6", your_rank="3",
         notes=("Mechanism-separating discovery fit: residuals beside iosO_hold and iosO_bp_saved; luck explains the "
                "serving over-rating if residuals take the negative weight and the profile's serve terms go to 0. Highest re-encoding risk of the luck family.")),
    dict(id="PS04", name="Event-run luck and the flattering last scoreline", area="conversion_luck",
         definition=("Run luck R = sum over the player's earlier matches at this event (qualifying included) of "
                     "(y - Lambda_P); 0 with an indicator if none. Scoreline flattery F = logit(games share) - kappa*logit(points share) "
                     "of the previous match, kappa the 2010-12 population slope. A - B; signs negative."),
         encoding="diff",
         mechanism=("Within an event the recreational market prices how the last match looked (straight sets, bagels); "
                    "sharp models price points; a recreational close (BetOnline from Sep 2025) keeps more. Separates rhythm (+, U-138) from luck (-) in a deep run"),
         data_paths=S0,
         data_status="on_disk",
         coverage_note="Run luck exists for ~55-57% of main-tour matches (rounds after the first, more with qualifying); both tours, all seasons",
         model_overlap="low (sets_14d mixes progress and luck; round)",
         pool_rows="U-280 (I-086, price surprise of the last win: a different quantity), U-138 / U-307 (On)",
         prior_evidence="None direct; B-OVERREACT block (above) nearest; On z +3.29 (2014-24) is its counterpart",
         exposed_2025_26="no",
         timing_class="own_sequence", build_hours="4", your_rank="4",
         notes="Test beside U-138 and I-086; kill if On's coefficient is unchanged with and without it and run luck >= 0."),
    dict(id="PS05", name="Serve-speed state extensions (second serve, gap, fault speed, last-match fade)", area="point_state",
         definition=("Each a 14-day mean minus own 364-day mean, per SD, event-year centred: (a) second-serve speed; "
                     "(b) first-minus-second speed gap; (c) mean speed of first-serve faults minus first serves in; "
                     "(d) last match's first-serve speed, last third of service points minus first third, against own normal fade, controlled for points played. A - B."),
         encoding="diff",
         mechanism="Physical state (shoulder, fatigue, confidence) shows in the radar before results; unwatched data (M1); the base first-serve state replicated",
         data_paths=("data/dump/matches/mantennisdata/ (match averages incl. second serve, Oct 2021-); "
                     "data/studies/serve_speed_tabpfn/live/speed_panel_*.parquet (y, spd2, spd_max, fault1); "
                     "data/dump/points/infosys_slams/points.parquet (AO25, RG25-26, fault speeds 96-98%); "
                     "data/raw/public_dump/atp_pipeline_handoff/court_vision/ (2021-24 per serve incl. faults); "
                     "data/dump/points/slam_ball_tracking/ (AO/RG 2019-24); data/dump/points/{wimbledon,usopen}/"),
         data_status="partial",
         coverage_note=("Men only (no free WTA tour speed). (a),(b): tour level ~1,700 matches in 2025 via "
                        "ManTennisData. (c),(d): per-serve 2021-24 ATP CV (~4,450 linked) + Slams; ATP non-Slam 2025-26 "
                        "not on disk (package P9, ~10,800 matches, decryption approved)"),
         model_overlap="medium for (a),(b),(d) (spd_L stage 2 is first-serve 28-day form); low for (c)",
         pool_rows="U-198 (sl__spd2_*, thin before 2022), U-199, U-137 (box-score within-event decay)",
         prior_evidence=("Base first-serve speed change: replication +0.090 [+0.017,+0.162] log-odds/SD given the model, "
                         "2022-24 (point_sequence); extensions untested (scout #1)"),
         exposed_2025_26="partly: the family is motivated by the base signal's 2025-26 results (serve_speed_tabpfn, edge_anatomy)",
         timing_class="needs_clock", build_hours="12 (plus P9 collection for 2025-26 c,d)", your_rank="5",
         notes="Centring by event-year crosses players: clock + probe.py. Outcome-free gate first: predicts next-match first-serve points won beyond spd_L (<= 2024)."),
    dict(id="PS06", name="Close-set and deciding-set luck", area="conversion_luck",
         definition=("Close-set luck: over sets that reached 5-5 (7-5, 5-7, 7-6, 6-7, long advantage sets), sets won minus "
                     "sum of pi_55(p_i, p_j), the iid probability of winning a set from 5-5 averaged over both serving orders "
                     "(includes the tiebreak). Deciding-set luck: deciding sets won minus pi_set(p_i, p_j, rule). Decayed sums, A - B, negative."),
         encoding="diff",
         mechanism="Close and deciding sets are near coin flips under iid but read as toughness or fitness; results and rankings carry them",
         data_paths=S0 + "; src/eda/predictability_diagnostic/stage2_iid.py (set_win, tiebreak, deciding_set_rule)",
         data_status="on_disk",
         coverage_note="As PS01; set scores from the score string",
         model_overlap="low",
         pool_rows="U-207 (Stage 4 raw deciding-set record, not stored)",
         prior_evidence=("Stage 4 seasons 2013-2024: women's raw 52-week deciding-set record negative beside the close in "
                         "11/12 seasons; men's mixed; persistence of tiebreak over-performance 0.06 (Stage 2)"),
         exposed_2025_26="partly (weak): as PS01 (Stage 4 pooled given-Elo text)",
         timing_class="own_sequence", build_hours="5", your_rank="6",
         notes="Overlaps PS01 (tiebreaks are a subset of close sets): pre-register PS01 and the 7-5 remainder separately."),
    dict(id="PS07", name="Ranking-points luck", area="conversion_luck",
         definition=("Over the 52-week ranking window: sum of (y_k - Lambda_P,k) * dRP_k, dRP = ranking points for "
                     "reaching the next round at match k's level and year (official tables), divided by the player's "
                     "current ranking points; A - B; negative."),
         encoding="diff",
         mechanism="Rankings drive seeding, the public's anchor and rank-based openers; luck in big-event rounds inflates them more than Elo",
         data_paths=S0 + " (rank_points); ATP and WTA ranking-points tables by year (to transcribe)",
         data_status="partial",
         coverage_note="Both tours; needs the points tables (public, small, hand-made)",
         model_overlap="low (points_52w is the actual points, not their luck share)",
         pool_rows="U-171, U-172 (ranking, points)",
         prior_evidence="None direct; Stage 4: ranking one of few positives beyond the close for women (pre-repair)",
         exposed_2025_26="no",
         timing_class="own_sequence", build_hours="6", your_rank="7",
         notes="Visibility-weighted variant of PS02; also a level-weighted decayed sum as a cheaper proxy."),
    dict(id="PS08", name="Games-route minus points-route rating matchup, luck direction (I-009 re-framed)",
         area="conversion_luck",
         definition=("z_C2 - z_C1: match log-odds from the surface IOS hold ratings (via serve_rate_for_hold) minus from "
                     "the spw IOS, remainder after projection on the inputs (f08_clutch.x_i009); registered NEGATIVE (luck), not + (skill)."),
         encoding="diff",
         mechanism="Long-memory hold/break records beyond what points imply are mostly luck; the close credits holds",
         data_paths="src/eda/feature_interactions/features/f08_clutch.py (x_i009); feature_interactions panel; surface IOS (U-069 for spw)",
         data_status="on_disk",
         coverage_note="Model frame, both tours, 2013-26 (code exists)",
         model_overlap="medium (iosO/D_hold in model; spw IOS not)",
         pool_rows="U-327 (I-009, gate-dropped), U-069",
         prior_evidence="Dropped before screening by a skill reliability gate (split-half 0.16 M / 0.27 W, 2010-18); never screened",
         exposed_2025_26="no",
         timing_class="needs_clock", build_hours="2", your_rank="8",
         notes="Cheapest to test; uses the leak-proof IOS (probe already passed for the inputs)."),
    dict(id="PS09", name="Women's error state (WTA advanced statistics)", area="point_state",
         definition=("Unforced errors per point played in the last 14 days minus the player's own 52-week rate, "
                     "event-year centred, per SD; A - B; sign negative (rising errors = declining state)."),
         encoding="diff",
         mechanism="Confidence or physical decline shows in errors before results; no market watches this feed",
         data_paths="data/dump/points/wta/advanced/<year>.parquet (2022-24 totals; 2025-26 full detail)",
         data_status="partial",
         coverage_note="Women, WTA tour and 125 levels; UE totals 91-92% filled 2022-24 (~3.6-4.2k singles/yr), 97.5% in 2025; no Slams",
         model_overlap="low",
         pool_rows="U-202 (how points end, trait form: closed)",
         prior_evidence="Error rates closed as traits (shot_level); never built as a state (scout #9)",
         exposed_2025_26="no",
         timing_class="needs_clock", build_hours="8", your_rank="9",
         notes="Only three discovery seasons; error crediting by stats crews may shift by event-year."),
    dict(id="PS10", name="Return elasticity to server strength (non-additive matchup)", area="serve_return",
         definition=("Per returner, shrunk slope of match return-point residuals (logit rpw minus IOS-predicted from the "
                     "server's pre-match O and the returner's D) on the server's O; matchup term b_A*(O_B - Obar) - b_B*(O_A - Obar)."),
         encoding="diff",
         mechanism="Additive serve/return models (bookmakers' and ours) miss returners who hold up against big servers",
         data_paths=S0 + "; leak-proof surface IOS (src/eda/match_timing/ios_time.py run_timed)",
         data_status="on_disk",
         coverage_note="Both tours, all levels with box scores",
         model_overlap="medium (prod_* matchup products)",
         pool_rows="U-098 (opponent-strength splits, closed), U-324 (B4 style cells, gate-dropped)",
         prior_evidence="Related splits failed reliability gates; reliability gate first",
         exposed_2025_26="partly: motivated by edge_anatomy's 2025-26 men's serving/returning asymmetry",
         timing_class="needs_clock", build_hours="10", your_rank="10",
         notes="The structural alternative to PS03's luck reading of the serve/return lead."),
    dict(id="PS11", name="Visible luck count: points-dominant losses minus fewer-points wins, last 10 matches",
         area="conversion_luck",
         definition="Count of the last 10 matches lost while winning more total points, minus those won with fewer points; A - B; sign positive (unlucky = under-rated).",
         encoding="diff", mechanism="The market sees the W/L column; points say otherwise", data_paths=S0,
         data_status="on_disk", coverage_note="Both tours, all seasons", model_overlap="low",
         pool_rows="U-278 (I-025)", prior_evidence="4.36% (M) / 3.86% (W) of matches go to the player with fewer points (Stage 2)",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="2", your_rank="",
         notes="Short-memory, discrete form of PS02; likely dominated by it."),
    dict(id="PS12", name="Cheap-wins share", area="conversion_luck",
         definition="Share of the last 52 weeks' wins that came by opponent retirement or walkover (status); A - B; negative.",
         encoding="diff", mechanism="Rankings and results-based ratings count them fully",
         data_paths="data/studies/predictability_diagnostic/stage0_matches.parquet (status, status_detail)",
         data_status="on_disk", coverage_note="All levels", model_overlap="low",
         pool_rows="U-026 (Elo without retirements, dominated)", prior_evidence="none found",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="1", your_rank="",
         notes="Rare; mostly a check of whether the model's Elo counts retirements."),
    dict(id="PS13", name="Escapes: match points saved in recent matches", area="conversion_luck",
         definition="Match points saved (score replay) in matches won over the last 8 weeks, minus match points failed to convert in losses; A - B; negative.",
         encoding="diff", mechanism="A narrative of resilience the public pays for; under iid it is luck",
         data_paths="data/studies/point_sequence/sequences.parquet (set_no, game_no, pt_no, server, winner; score replays)",
         data_status="partial",
         coverage_note="Model-frame coverage 87-98% (men 66,300 usable matches 2013-24; 2025: M 4,293 / W 5,122); predates later sources",
         model_overlap="none", pool_rows="none", prior_evidence="Big-point traits closed (point_sequence); escapes as luck untested",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="6", your_rank="",
         notes="Rare event; fold into PS04 if built."),
    dict(id="PS14", name="Luck exposure as a price-slope modulator", area="conversion_luck",
         definition="Sum over both players' recent tiebreaks and close sets of pi(1 - pi) (outcome-free luck variance), times the close's log-odds; context modulator.",
         encoding="context", mechanism="Noisy records deserve more shrinkage; the close may not shrink enough",
         data_paths=S0, data_status="on_disk", coverage_note="All", model_overlap="low",
         pool_rows="U-256 / U-231 (pair-strength modulators, not confirmed)", prior_evidence="none found",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="3", your_rank="",
         notes="Price-slope rule: enters only beside odds_logit (feature_universe section 6, item 4)."),
    dict(id="PS15", name="Rally and return speed state from Hawk-Eye tracking", area="point_state",
         definition="Return speed (and spin) in the last 14 days minus own normal, event-year centred; A - B.",
         encoding="diff", mechanism="Physical state in the rally (point-shot-ideas section 1)",
         data_paths="data/dump/points/slam_ball_tracking/ (returnSpeed 33%, spin_rpm 56%); ATP court_vision 2021-24 (trajectories, no per-shot speed)",
         data_status="partial", coverage_note="AO/RG 2019-24 mostly; nothing tracked on disk for 2025-26",
         model_overlap="none", pool_rows="U-203, U-213", prior_evidence="Shot-style rates closed as traits; never a state",
         exposed_2025_26="no", timing_class="needs_clock", build_hours="16", your_rank="",
         notes="Too thin to test now."),
    dict(id="PS16", name="Distance-run state (Slam feeds)", area="rhythm_body",
         definition="Metres run per point in the previous match minus own normal; A - B.",
         encoding="diff", mechanism="Fatigue carried into the next round",
         data_paths="data/dump/points/wimbledon/, data/dump/points/usopen/ (P1/P2DistanceRun); Sackmann slam_pointbypoint from 2015",
         data_status="partial", coverage_note="Wimbledon and US Open only", model_overlap="low (sets_14d)",
         pool_rows="U-213", prior_evidence="none found", exposed_2025_26="no", timing_class="own_sequence",
         build_hours="6", your_rank="", notes="B1's lens; listed for completeness."),
    dict(id="PS17", name="Serve-mechanics collapse in the last match", area="point_state",
         definition="Last match's double faults per serve point and first serves in, each minus own 52-week rate in SDs (no decay); A - B.",
         encoding="diff", mechanism="A single bad serving day (yips, injury) before it shows in decayed form",
         data_paths=S0 + " (df, svpt, first_in)", data_status="on_disk", coverage_note="All levels with box scores",
         model_overlap="medium-high (form_df, form_first_in decayed)", pool_rows="U-137", prior_evidence="Women's within-match fade closed (point_sequence)",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="2", your_rank="",
         notes="Likely redundant with form_* inputs."),
    dict(id="PS18", name="Serve-return balance", area="serve_return",
         definition="Serve share of dominance: iosO_spw deviation / (iosO_spw deviation + iosD_rpw deviation), A - B.",
         encoding="diff", mechanism="If the close over-rates servers per se", data_paths="surface IOS (U-069)",
         data_status="on_disk", coverage_note="Model frame", model_overlap="high (linear contrast of iosO/iosD)",
         pool_rows="U-069", prior_evidence="edge_anatomy 2025-26 men's asymmetry", exposed_2025_26="partly: motivated by 2025-26",
         timing_class="needs_clock", build_hours="1", your_rank="", notes="Re-encoding; listed to say it is not new."),
    dict(id="PS19", name="Draw luck", area="conversion_luck",
         definition="Ranking points earned in 52 weeks minus the points expected from the player's pre-match win probabilities against the opponents actually drawn; A - B; negative.",
         encoding="diff", mechanism="Rankings ignore draw strength; the public anchors on rankings",
         data_paths=S0 + "; ranking-points tables", data_status="partial", coverage_note="Both tours",
         model_overlap="low", pool_rows="U-043 (strength of schedule, unsettled)", prior_evidence="none found",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="8", your_rank="",
         notes="Needs a pre-match probability for every past match (Elo); B3 overlap."),
    dict(id="PS20", name="Lower-level luck behind an arrival's ranking", area="conversion_luck",
         definition="PS02's decayed match luck restricted to qualifying, Challenger and WTA 125 matches in 52 weeks; A - B; negative.",
         encoding="diff", mechanism="Arrivals are under-rated on average (U-330); lucky Challenger runs inflate the ranking that partly corrects it",
         data_paths=S0, data_status="on_disk", coverage_note="Men CH 99% box scores, WTA125 94%; ITF ~10%",
         model_overlap="low", pool_rows="U-330", prior_evidence="U-330: share coefficient +0.18 [+0.09,+0.27] 2020-24 (event_levels)",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="2", your_rank="",
         notes="Interaction with U-330 and the men's level layer."),
]

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=COLS, quoting=csv.QUOTE_MINIMAL)
    w.writeheader()
    for r in rows:
        assert set(r) == set(COLS), r["id"]
        w.writerow(r)
print(OUT, len(rows))
