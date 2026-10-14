"""R1 researcher: write docs/studies/unpriced_leads/team/researcher_ideas.csv with the brief's exact columns.

Kept as code so the quoting is right and the rows can be re-generated. Reads no data.
Run: ./python.sh data/studies/unpriced_leads/team/researcher/scripts/write_ideas_csv.py
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
OUT = ROOT / "docs/studies/unpriced_leads/team/researcher_ideas.csv"
COLS = ["id", "name", "area", "definition", "encoding", "mechanism", "data_paths", "data_status", "coverage_note",
        "model_overlap", "pool_rows", "prior_evidence", "exposed_2025_26", "timing_class", "build_hours",
        "your_rank", "notes"]

S0M = "data/studies/predictability_diagnostic/stage0_matches.parquet"
S0P = "data/studies/predictability_diagnostic/stage0_match_players.parquet"
CLK = "data/studies/match_timing/timing.parquet"
BOX = ("Box scores: ATP tour and Challenger >=99% every season 2010-26; WTA tour 84-88% in 2013-15 then >=96%; "
       "WTA 125 >=99% from 2016; ITF none before 2025 (R1 coverage_box_end.json, outcome-free)")

ROWS = [
    dict(id="RS01", name="Clutch-luck stock: break points and tiebreaks beyond the match's own point rates",
         area="conversion_luck",
         definition=("Per player, over completed matches with a box score in the 365 days before this one, sum with a "
                     "13-week half-life (no shrinkage) three residuals against that match's own serve-point rates "
                     "p_s (player) and p_o (opponent) under iid points: BP saved - faced*p_s; BP converted - "
                     "chances*(1-p_o); tiebreaks won - played*q with q = p_s(1-p_o)/[p_s(1-p_o)+(1-p_s)p_o]. "
                     "Composite = mean of the three standardised stocks; A - B; expected sign negative."),
         encoding="diff",
         mechanism=("Break-point and tiebreak over-performance does not persist (luck), yet it moves W/L records, "
                    "rankings, Elo and the 'clutch' narrative; the model's raw BP rates mix this luck with serving "
                    "skill; the close over-rates men's BP saving in every era (edge_anatomy), consistent with luck "
                    "read as skill."),
         data_paths=f"{S0P} (bp_saved_n/d, bp_conv_n/d, tb_won_n/d, spw_n/d); {S0M} (dates, level, status)",
         data_status="on_disk",
         coverage_note=BOX + "; tiebreak counts present ~99% where a box score exists (<=2024)",
         model_overlap="medium (form_bp_saved, form_bp_conv, iosO_bp_saved, form_first_won, form_second_won); the orthogonal-part step decides",
         pool_rows="U-207 (bp_over: men constant, shrinkage K infinite), U-278, U-094, U-253",
         prior_evidence=("Sackmann 2012 'The Luck of the Tiebreak': year-to-year correlation 'almost exactly zero' "
                         "(ATP 1991-2012, >=15 TBs; R1 checked); Sackmann 2015 BP non-persistence (WTA; repo note); "
                         "Kovalchik & Ingram 2016 (ATP 2011-15: tiebreak effect on serve points -0.06 pp n.s.); "
                         "Kovalchik & Reid 2018 (BP won 'negligible'); repo: pool's men's bp_over K infinite (no "
                         "persistent variance; src/eda/feature_interactions/inventory/build_inventory.py); "
                         "edge_anatomy 2013-24 men BP saved vs price z -1.6 (long memory), -2.3 (two-week)"),
         exposed_2025_26="partly: motivated by edge_anatomy's 2025-26 ledger of the in-model BP-saved rates (men z -3.9, -2.8), read by the lead and R1; the residual itself never read",
         timing_class="own_sequence", build_hours="4", your_rank="1",
         notes=("Same family as B2's PS01/PS03 (S2b building). Kill: split-half persistence of the residual > 0.3 "
                "(skill, not luck), or the close's own loading on it with no residual beta; likely unresolved alone "
                "on Look A (MDE ~0.064 per RMS unit), so register inside a group.")),
    dict(id="RS02", name="Break-point luck piece", area="conversion_luck",
         definition=("RS01's first two residuals only (BP saved - faced*p_s; BP converted - chances*(1-p_o)), per "
                     "100 break-point opportunities, 13-week half-life, unshrunk; A - B."),
         encoding="diff", mechanism="As RS01; the part most directly tied to the close's over-rating of men's BP saving.",
         data_paths=f"{S0P} (bp_saved_n/d, bp_conv_n/d, spw_n/d)", data_status="on_disk", coverage_note=BOX,
         model_overlap="medium (form_bp_saved, form_bp_conv, iosO_bp_saved)", pool_rows="U-207, U-114, U-117",
         prior_evidence="As RS01 (Sackmann 2015; Kovalchik & Reid 2018; pool K infinite; edge_anatomy 2013-24)",
         exposed_2025_26="partly: as RS01", timing_class="own_sequence", build_hours="2", your_rank="",
         notes="Member of RS01."),
    dict(id="RS03", name="Tiebreak luck piece", area="conversion_luck",
         definition=("Tiebreaks won minus sum over tiebreaks played of q(p_s, p_o) from each match's own serve-point "
                     "rates, last 52 weeks (13-week half-life), plus tiebreaks played per match as exposure; A - B."),
         encoding="diff",
         mechanism="Tiebreak wins are near coin flips but count fully in records, rankings and Elo; the model has no tiebreak input.",
         data_paths=f"{S0P} (tb_won_n/d, spw_n/d)", data_status="on_disk",
         coverage_note="tiebreak counts present ~99% where a box score exists (<=2024)",
         model_overlap="low (no tiebreak input in the model)", pool_rows="U-207",
         prior_evidence="Sackmann 2012 (r ~0, R1 checked) and 2019 (two extra tiebreak wins ~ one match win); Kovalchik & Ingram 2016",
         exposed_2025_26="partly: raw tiebreak rates (U-207) were scored on 2025-26 by the predictability diagnostic; this residual not",
         timing_class="own_sequence", build_hours="2", your_rank="", notes="Member of RS01; B2's PS01."),
    dict(id="RS04", name="Deciding-set luck piece", area="conversion_luck",
         definition=("Deciding sets won minus sum of the iid probability of winning a set at that match's own serve-"
                     "point rates, over deciding sets played in the last 52 weeks; A - B."),
         encoding="diff", mechanism="Deciding-set records regress strongly toward 45% + 0.2 x straight-set record; bettors read them as nerve.",
         data_paths=f"{S0M} (score); {S0P} (sets_won_n/d, spw_n/d)", data_status="on_disk", coverage_note=BOX,
         model_overlap="low", pool_rows="U-207 (deciding)",
         prior_evidence="Sackmann 2014/2024 ('three-set win% = 45% + 20% x two-set win%'; 36% three-setters vs 44% predicted, ATP 2014)",
         exposed_2025_26="partly: U-207's deciding-set form was scored on 2025-26 by the predictability diagnostic (onM men -0.039, worse)",
         timing_class="own_sequence", build_hours="2", your_rank="", notes="Weakest member of the luck family."),
    dict(id="RS05", name="Load spike against the player's own normal (acute:chronic ratio)", area="rhythm_body",
         definition=("log(G14 / max(Gch, floor)): G14 = games played (singles at every level, doubles where held) in "
                     "the 14 days before this match's earliest start es; Gch = mean 14-day games over days 15-70 before; "
                     "floor = tour median 14-day games of active players; plus a flag for ratio >= 1.5; A - B."),
         encoding="diff",
         mechanism=("The close and the model see absolute recent load (sets_14d), not load relative to the player's own "
                    "normal; spikes cause injury and flat play before any news shows; the 12-day Masters (2023, 2025) "
                    "raised spikes; record retirements in 2025."),
         data_paths=f"{S0M} (minutes, score, status, level); {S0P} (games_won_d); {CLK} (es, lf)",
         data_status="on_disk", coverage_note="Every level 2010-26 (lower-level dates are windows); minutes partial below tour level",
         model_overlap="medium (sets_14d, surf_season_a/b, surf_layoff_a/b)",
         pool_rows="U-161 (ACWR, never screened), U-139, U-141, U-156",
         prior_evidence=("Kovalchik 2020 PLoS One: cumulative load raises competition time-loss, HR 1.05 [1.01, 1.10] "
                         "per 1,000 games, magnified with age (389 ATP players, 55,773 weeks; R1 checked); Amor-Salamanca "
                         "et al. 2025 review: acute:chronic ratio >= 1.3-1.5 strongest external injury predictor; "
                         "repo: B9a odometer x age z2 +2.52 (2022-24)"),
         exposed_2025_26="partly: the schedule-and-body family's 2025-26 strength (edge_anatomy) shaped the choice; the ratio never read",
         timing_class="own_sequence", build_hours="4", your_rank="2",
         notes="Kill: orthogonal part near zero, or no within-player effect of spikes on next-match points won vs own norm (gate on <=2024)."),
    dict(id="RS06", name="Season load x age", area="rhythm_body",
         definition=("Games played in the last 52 weeks relative to the field's walk-forward norm (tour, week, ranking "
                     "band), times max(0, age - 27), with an autumn (Sep-Nov) indicator; A - B."),
         encoding="diff", mechanism="Older players recover more slowly from accumulated load; the close prices age uniformly.",
         data_paths=f"{S0M}; {S0P} (age, games_won_d)", data_status="on_disk", coverage_note="Every level 2010-26",
         model_overlap="medium (age, age_sq, sets_14d)", pool_rows="U-144, U-296, U-292",
         prior_evidence=("Kovalchik 2020 (load effect magnified with age); Palau et al. 2024 (lower tiers: +31% retirement "
                         "risk per 5 years of mean age); retirement rate doubles every 5 years after 27 (Baiget/Casals "
                         "group, university news); repo B9a z1 +0.10, z2 +2.52"),
         exposed_2025_26="partly: age's 2025-26 reading (edge_anatomy) seen", timing_class="own_sequence",
         build_hours="2", your_rank="9", notes="Member of RS05's group (scout #6)."),
    dict(id="RS07", name="Turnaround in hours, late finish, doubles since the last singles match", area="rhythm_body",
         definition=("H = hours from the end of the player's previous match (singles or doubles) to this match's "
                     "scheduled start (end = Flashscore end_utc where present, else start_utc + Stage 0 minutes; doubles "
                     "have start times only, so start + a typical duration); features min(H, 48) A - B, flag H < 20, "
                     "previous finish after 23:00 local time, doubles matches since the last singles match."),
         encoding="diff",
         mechanism="Books and models count days and sets, not clock hours; late finishes and same-day doubles are invisible in day counts.",
         data_paths=("data/studies/match_timing/links/*.parquet (start_utc); data/studies/match_timing/links/"
                     f"flashscore_records.parquet (end_utc); {S0M} (minutes); data/dump/points/tennislive/listed.parquet "
                     "(doubles start_utc, discipline); venue time zones from the gazetteer (to build)"),
         data_status="partial",
         coverage_note=("start_utc: ATP main draw >=98.6% every season 2010-26; WTA 65-72% 2010-17, >=93% 2018-26. "
                        "Flashscore end: ATP 90-99% to 2024, 16% (2025), 11% (2026); WTA 65-86% to 2024, 99% (2025), "
                        "37% (2026). Stage 0 minutes: ATP ~99% (2015: 52%), WTA >=93% from 2016 (none before). "
                        "TennisLive finished_at is a '0' placeholder on 99.98% of listings: not a source (R1 "
                        "coverage_clock.json, coverage_box_end.json, coverage_finish_fields.json)"),
         model_overlap="low (sets_14d)", pool_rows="U-195 (never tested), U-157, U-265, U-291",
         prior_evidence=("Turner et al. 2022 (lab, 12 players: max serve 10.5 km/h lower at 20:00 than 14:00); Ashman "
                         "et al. 2010 (NBA back-to-backs vs spreads); Smith et al. 2013 (NFL circadian vs Las Vegas "
                         "spread); Goossens et al. 2015 (Slams: previous-match sets); ATP 2025 late-finish rules "
                         "(post-midnight finishes 50 -> 39)"),
         exposed_2025_26="no", timing_class="own_sequence", build_hours="5", your_rank="5",
         notes=("Same as B1's RB03/RB04 (S2a building). Scheduled start is published the evening before (WTA order of "
                "play released ~19:00). Kill: no within-player effect of H < 20 h on next-match points won vs own norm (<=2024).")),
    dict(id="RS08", name="Doubles load at the same event", area="rhythm_body",
         definition=("Doubles matches and sets the player played at this event, and in the 3 days before this singles "
                     "match's scheduled start; A - B."),
         encoding="diff", mechanism="Singles histories, ratings and most bettors ignore doubles minutes.",
         data_paths=("data/raw/public_dump/sackmann_archive/atp/atp_matches_doubles_2010-2020.csv (event-level dates); "
                     "data/dump/points/tennislive/listed.parquet (2018-26, start times only; finish field empty)"),
         data_status="partial",
         coverage_note="Men 2010-26 (event-level only to 2017); women 2018-26; TennisLive doubles: tour ~1,600-1,950 a year, Slams 504, Challengers 2,150-3,200; no doubles finish times (use start + typical duration, or count only doubles started >= 3 h before the singles start)",
         model_overlap="low", pool_rows="none",
         prior_evidence="No published study found (lane L1); B1 measured one player with doubles in the prior 7 days in 30-38% of frame matches 2018-24",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="4", your_rank="7",
         notes="Same as B1's RB01 (S2a building); name linking needed (TennisLive 'A / B' members)."),
    dict(id="RS09", name="Draw shadow: a dominant player still alive, and the next-round shadow", area="other",
         definition=("Dominant = as-of overall Elo >= 100 points above the field's 3rd-best entrant at the event's "
                     "start; S = 1[another dominant player is still alive at es] x 1[player in Elo top 20, not "
                     "dominant]; N = 1[a dominant player is the projected next-round opponent]; reverse term for "
                     "players outside the top 50; each A - B."),
         encoding="diff",
         mechanism=("Effort and psychology in elimination draws respond to the draw beyond the current match; prices "
                    "are set match-up by match-up; dominance concentrated again in 2024-26 (men)."),
         data_paths=f"{S0M} (round, match_num, draw_size, player ids); {CLK} (es, lf); Elo history (the model's Elo builder)",
         data_status="on_disk", coverage_note="Both tours 2013-26 (main tour)",
         model_overlap="low", pool_rows="none",
         prior_evidence=("Creutzburg 2024 (HCED WP 79; journal 2026): top-20 non-superstar players -3.4 pp win "
                         "probability while a superstar is in the draw, more if he is the likely next opponent; players "
                         "outside the top 50 +4.1 pp (n.s. with more events); ATP 2004-19, 27,366 matches, rank-"
                         "difference, round, tournament and player-season FEs, no odds (R1 checked); Deutscher, Neuberg "
                         "& Thiem 2023 JEP (stronger with several superstars, vanishes once they are out); Babington et "
                         "al. 2020 (no effect in golf, skiing)"),
         exposed_2025_26="no", timing_class="needs_clock", build_hours="6", your_rank="3",
         notes=("Papers name the superstars (Federer, Nadal, Djokovic, Murray); the Elo definition is R1's so women and "
                "2020-26 can be tested. Brown & Minor 2014 (Mgmt Sci) cited by Creutzburg, not read. Kill: no effect in "
                "2013-19 with Elo (not rankings) as the control.")),
    dict(id="RS10", name="Player's own translation ratio from lower levels to the tour", area="career",
         definition=("Men: opponent-adjusted total points won at Challenger level / at tour level over the last 36 "
                     "months, shrunk toward the walk-forward global factor (~1.095) by matches at the scarcer level; "
                     "women: WTA 125 vs tour; feature (ratio - global) x U-330's lower-level share; A - B."),
         encoding="diff",
         mechanism=("Rankings, Elo and a global level translation discount every player alike; the close under-rates "
                    "arrivals from lower levels (growing by era); players whose lower-level form translates unusually "
                    "are misjudged."),
         data_paths=(f"{S0M}; {S0P} (tpw_n/d, level); data/studies/event_levels/history.parquet; "
                     "data/studies/current_best_model/level_layer/official.json"),
         data_status="on_disk",
         coverage_note="Men's Challenger box scores >=99% 2010-26; WTA 125 >=99% from 2016; women's ITF box only 2025-26",
         model_overlap="medium (the men's level layer; IOS profiles)", pool_rows="U-330",
         prior_evidence=("Sackmann 2018: Challenger-to-tour factor 1.086-1.103 by year (2012-17); player ratios 0.982 "
                         "(Ebden) to 1.180 (F. Mayer); persistence not tested (R1 checked); Sackmann 2025: Elo-market "
                         "gaps mostly from thin lower-level data; repo U-330 beta beside the average close +0.13 [+0.07, "
                         "+0.19] 2013-24 (500s +0.41, 1000s -0.02); current best leaves +0.12 [+0.03, +0.21] 2020-24"),
         exposed_2025_26="no", timing_class="own_sequence", build_hours="5", your_rank="4",
         notes="Published support is thin; the project's U-330 carries it. Kill: split-half persistence of the ratio < 0.2, or no gain beside U-330."),
    dict(id="RS11", name="Ranking stakes: points to defend and distance to a threshold", area="career",
         definition=("(a) Ranking points the player earned at this event last year (Stage 0 + the tours' points "
                     "tables) / current points; (b) signed distance in places to the nearest live threshold at the "
                     "match date (top 100/104 Slam entry, top 32 Slam seeding, Finals-race top 8 in Sep-Nov); (c) "
                     "points for winning this round / points gap to that threshold; A - B."),
         encoding="diff",
         mechanism=("Tournament theory: effort follows each player's marginal stake; prices reflect level and round, "
                    "not individual stakes; 2026 rules (18 counting results, fewer mandatory 500s) shift stakes."),
         data_paths=(f"{S0P} (rank, rank_points); {S0M} (round, level); Sackmann weekly rankings (to 8 Jun 2026); "
                     "TML ATP rankings (31 Aug 2026); Wikipedia edition pages (seeds' points before/dropped/after)"),
         data_status="partial", coverage_note="Men's weekly rankings to Aug 2026; women's 2025-26 weekly rankings need the WTA API or Wikipedia",
         model_overlap="low (points_52w)", pool_rows="U-174 (never built), U-283, U-284, U-191",
         prior_evidence=("Gilsdorf & Sukhatme 2008 (ATP 2001: larger prize gaps raise the stronger player's win "
                         "probability); Lallemand, Plasman & Rycx 2008 (WTA); Sunde 2009 (ATP semis/finals); Sackmann "
                         "2013 (seeds 61% vs 70% at 250s the week before a Slam, raw); repo B-MOTIV z1 +2.39, z2 +0.49"),
         exposed_2025_26="no", timing_class="own_sequence", build_hours="6", your_rank="6",
         notes="Overlaps B3's MP-07-09 (S2c building MP-08/09). Wikipedia probe: receipts/wikipedia/."),
    dict(id="RS12", name="Heat stress: heat-weighted recent load, and heat x age", area="conditions",
         definition=("Outdoor WBGT at the venue and scheduled hour from hourly temperature, humidity, wind and "
                     "radiation (Liljegren; Open-Meteo); (i) sum of minutes x max(0, WBGT - 25 C) over the last 3 days, "
                     "A - B; (ii) WBGT at this match x (age_A - age_B); (iii) a 2026+ ATP heat-rule indicator."),
         encoding="diff",
         mechanism=("Simple lagged heat is priced (Burke); the interactions (heat x own minutes, heat x age) and the "
                    "2026 cooling-break rule are untested and may not be priced."),
         data_paths=("Open-Meteo archive (download); venue gazetteer (to build with Open-Meteo geocoding); "
                     f"{S0M} (minutes); the model's indoor input; data/dump/points/wta/events (heat suspensions 2019-26)"),
         data_status="download_needed",
         coverage_note="Outdoor main-tour matches 2013-26; ERA5 0.25 deg (~25 km) from 1940, ERA5-Land 0.1 deg; archived day-ahead forecasts (previous-runs API) for live-like inputs",
         model_overlap="low (age, sets_14d, indoor)", pool_rows="U-196 (needs new data)",
         prior_evidence=("Burke et al. 2023 NBER (177,868 matches 2002-17: hotter previous match ~-0.1% win per C; "
                         "'most tennis betting markets appear to accurately price climate risk', incl. Pinnacle; R1 "
                         "checked); Smith et al. 2018 (AO: doctor calls +47% per WBGT zone); Simani et al. 2026 MSSE "
                         "(men's Slams 2000-25: older players relatively better in heat); ATP heat rule 2026"),
         exposed_2025_26="no", timing_class="market_or_context", build_hours="12", your_rank="8",
         notes="Overlaps B1's RB07 and B3's MP-05; Burke lowers the prior; free tier is non-commercial (owner's call)."),
    dict(id="RS13", name="Edition court pace from Hawk-Eye bounces", area="conditions",
         definition=("Per venue-edition, the ball's horizontal speed retained and vertical restitution at the bounce "
                     "from Court Vision tracking of earlier days' matches (released by the clock), giving a pace-rating "
                     "analogue; feature = this edition's index - the venue's previous edition, x (A's serve dominance - B's)."),
         encoding="diff",
         mechanism="Court changes shift serve dominance (Paris, Shanghai 2025 per media); ace-based pace lags; a physical measure is new information.",
         data_paths=("data/raw/public_dump/atp_pipeline_handoff/court_vision/ (ATP 2021-24); "
                     "data/dump/points/slam_ball_tracking/ (AO 2020-24, RG 2019-24); ATP Stats Centre 2025-26 (decryptable; Court Vision unverified)"),
         data_status="partial", coverage_note="ATP tour 2021-24 (4,570 matches), AO/RG 2019-24; none for WTA tour; 2025-26 unknown",
         model_overlap="low", pool_rows="U-192, U-254, U-106",
         prior_evidence=("ITF (Capel-Davies & Spurr 2019): ~2 pace-rating points per km/h of post-bounce speed, return "
                         "rate -1% per km/h (snippet); media court pace index Paris 46.6 -> 35.1, social-media sourced "
                         "(SI 2025, R1 checked); B-VENUE z +2.50/+2.72 (ace-based)"),
         exposed_2025_26="no", timing_class="needs_clock", build_hours="16", your_rank="",
         notes="Formula of the ITF rating to verify at source (search cap)."),
    dict(id="RS14", name="Decline from own peak (men): serve speed and serve points", area="career",
         definition=("Own 52-week mean first-serve speed minus own highest 52-week mean to date (system offsets as in "
                     "the speed panel), and own 52-week opponent-adjusted serve points won minus own 3-year peak; A - B."),
         encoding="diff",
         mechanism="The close over-rates older men; chronological age proxies a physical decline that varies by player.",
         data_paths="data/studies/serve_speed_tabpfn/live/speed_panel_backfilled.parquet; " + S0P,
         data_status="partial", coverage_note="Men tour level 2018/2021-26 (~49% of 2025-26 men's matches with ManTennisData), Slams 2015-26; women none",
         model_overlap="medium (age, age_sq, spd_L, iosO_*)", pool_rows="U-045, U-198",
         prior_evidence=("Sutter et al. 2018 (serve speed peaks ~26, accuracy ~28, similar declines both sexes); "
                         "Kovalchik 2014 (top players older, to 27.9 in 2012); repo: men's age vs price z -3.3 (2013-24)"),
         exposed_2025_26="partly: age's 2025-26 reading seen", timing_class="own_sequence", build_hours="6",
         your_rank="10", notes="Thin before 2022."),
    dict(id="RS15", name="Day-form volatility (pair steepness modulator)", area="point_state",
         definition=("Per player, time-decayed SD of match-level serve and return point residuals (observed minus "
                     "expected from pre-match profiles) over the last 25 matches; pair term (sd_A^2 + sd_B^2) x the "
                     "close's log-odds."),
         encoding="pair", mechanism="Match outcomes are over-dispersed; prices and inputs carry means only.",
         data_paths=f"{S0P}; data/studies/feature_universe/store.parquet (profiles)", data_status="on_disk",
         coverage_note="As box scores", model_overlap="low", pool_rows="U-103, U-104, U-328, U-262, U-263",
         prior_evidence=("Sackmann 2014 (36% three-setters vs 44% predicted); De Paola & Scoppa 2017 (set-1 loser "
                         "-20.5 pp in set 2 given average odds); Kovalchik & Reid 2019; repo: reliability family +0.232 "
                         "[-0.038, +0.502] mLL beyond Pinnacle + profile (men, predictive_frontier); I-028 dropped "
                         "(split-half 0.051)"),
         exposed_2025_26="partly: predictive_frontier scored the reliability family through 2025", timing_class="own_sequence",
         build_hours="4", your_rank="", notes="Killed as a trait by I-028's split-half 0.051; listed to close it."),
    dict(id="RS16", name="Early-retirement risk under each venue's settlement rule", area="market_info",
         definition=("Shrunk 24-month retirement + walkover rate, a flag for a retirement or walkover in the last 30 "
                     "days, WTA physio events in the previous match, and age; A - B."),
         encoding="diff",
         mechanism=("Pinnacle voids early retirements (rule to verify), Polymarket pays the advancing player: a venue-"
                    "specific gap, not an outcome edge against the close."),
         data_paths=f"{S0M} (status); data/dump/points/wta/events (PhysioCalled, MedicalTreatment)", data_status="on_disk",
         coverage_note="Stage 0 every level; WTA physio events 2019-26", model_overlap="low", pool_rows="U-178, U-179, U-260",
         prior_evidence=("Palau et al. 2024 (lower tiers: retirements 3.30% men, 2.73% women; +31% per 5 years of age); "
                         "Sackmann 2012 (retirement rates persist by player); record 4.8% ATP 2025 (news); repo U-178 "
                         "null vs the close"),
         exposed_2025_26="no", timing_class="own_sequence", build_hours="3", your_rank="",
         notes="For Polymarket accounting (B3), not for beating the close."),
    dict(id="RS17", name="Recent withdrawal with an injury reason", area="rhythm_body",
         definition=("Flag for a withdrawal from, retirement in or walkover at an event in the last 28 days, split by "
                     "stated reason (injury or illness vs schedule); A - B."),
         encoding="diff",
         mechanism=("The close has the news, the model does not: a defensive input that keeps the model from "
                    "fighting a news-moved line, not an edge against the close."),
         data_paths=f"Wikipedia edition singles pages (withdrawn players with reason; withdrawals list) (download); {S0M} (status)",
         data_status="download_needed", coverage_note="Main tour 2013-26, ~4,000 pages; reasons mostly given for would-be seeds",
         model_overlap="low", pool_rows="U-136",
         prior_evidence=("Casals et al. 2025 (ATP walkovers: injury 28.7% of causes, unknown 61%); Sackmann 2025 "
                         "(unreported injuries behind Elo-market gaps); George et al. 2019 (returns after surgery)"),
         exposed_2025_26="no", timing_class="own_sequence", build_hours="8", your_rank="",
         notes="Wikipedia probe receipts in receipts/wikipedia/."),
    dict(id="RS18", name="Lucky-loser entry", area="career",
         definition="1[entered as lucky loser] (and qualifier), A - B.", encoding="diff",
         mechanism="Late entry and a reference-point loss; possibly a ranking lag the close already absorbs.",
         data_paths=f"{S0P} (entry)", data_status="on_disk", coverage_note="Every level",
         model_overlap="low", pool_rows="U-176 (priced: onM ties)",
         prior_evidence="Eckmann 2024 (Slam R1 1978-2023, rank-controlled: men's LL -0.40 log-odds, SE 0.13; qualifiers +0.40 to +0.67)",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="1", your_rank="", notes="B1's RB13 overlaps."),
    dict(id="RS19", name="Pre-Slam effort and post-Slam letdown", area="career",
         definition="U-283 and U-284's definitions (top-20 at a 250/500 within 8 days of a Slam; a Slam QF+ within 21 days), A - B.",
         encoding="diff", mechanism="Effort saving before a Slam; fatigue or relief after a deep run.",
         data_paths=S0M, data_status="on_disk", coverage_note="Main tour 2013-26", model_overlap="low",
         pool_rows="U-283, U-284, U-191",
         prior_evidence="Sackmann 2013 (61% vs 70%, raw); Sackmann 2014 (no general letdown; finalists ~1 pp worse); repo B-MOTIV z1 +2.39, z2 +0.49",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="1", your_rank="", notes="Failed replication in the pool."),
    dict(id="RS20", name="Exposure to tiebreaks in the matchup (serve-dominance level)", area="point_state",
         definition=("From the two players' predicted serve-point rates (profiles), P(at least one tiebreak) and "
                     "expected tiebreaks under iid for the format, times the close's log-odds."),
         encoding="pair", mechanism="When both hold easily, a skill edge converts less; the price may scale it imperfectly.",
         data_paths="data/studies/feature_universe/store.parquet; " + S0P, data_status="on_disk", coverage_note="As profiles",
         model_overlap="low (prod_*)", pool_rows="none (H-S2 levels arm related)",
         prior_evidence="Newton & Keller 2005; O'Malley 2008; repo round-0 computed slopes 0.213 -> 0.175; Sackmann 2019 (aggressive pairs least predictable); Moskowitz SSAC 2025/26 (abstracts)",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="4", your_rank="",
         notes="feature_interactions measured the close close to the iid scaling (43% vs ~39%)."),
    dict(id="RS21", name="Night session and local start hour", area="conditions",
         definition="Local start hour (start_utc + venue time zone), 1[>= 18:00 local], and a day-to-night switch flag versus the player's previous match.",
         encoding="context", mechanism="Circadian effects on serving; night conditions (cooler, slower).",
         data_paths="data/studies/match_timing/links/*.parquet (start_utc); gazetteer (to build)", data_status="partial",
         coverage_note="As RS07 start times", model_overlap="none", pool_rows="U-195",
         prior_evidence="Turner et al. 2022 and 2023 (lab; evening: more unforced errors, fewer winners)",
         exposed_2025_26="no", timing_class="market_or_context", build_hours="4", your_rank="", notes="Thin evidence."),
    dict(id="RS22", name="Eastward travel and jet lag (not recommended)", area="rhythm_body",
         definition="Time zones crossed eastward since the previous event x days since arrival proxy; A - B.",
         encoding="diff", mechanism="Circadian disruption.", data_paths="Gazetteer (to build); " + S0M,
         data_status="partial", coverage_note="All levels", model_overlap="low", pool_rows="U-151, U-305, U-148",
         prior_evidence="Maynard et al. 2025/26 (WTA: less sleep, no link to results); Song et al. 2017 (MLB, disputed); Leota et al. 2022 (NBA)",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="3", your_rank="", notes="Listed to close it."),
    dict(id="RS23", name="Altitude and acclimatisation", area="conditions",
         definition="Venue elevation (Open-Meteo elevation/geocoding) and its change since the player's previous event, x serve profile.",
         encoding="context", mechanism="Thin air favours servers; arrivals from sea level may lag.",
         data_paths="Open-Meteo geocoding and elevation APIs (download)", data_status="download_needed",
         coverage_note="Probed: Bogota 2,582 m, Kitzbuhel 751-759 m", model_overlap="low", pool_rows="U-192, U-196",
         prior_evidence="Sanchez Pay et al. 2019 (122 ATP 250 matches: more aces at altitude); Sackmann 2013 (Sao Paulo ace factor 1.58)",
         exposed_2025_26="no", timing_class="market_or_context", build_hours="4", your_rank="", notes="Venue pace already absorbs most."),
    dict(id="RS24", name="Wind at the scheduled hour", area="conditions",
         definition="10 m wind speed and gusts at the venue and hour (outdoor), x both players' first-serve reliance, and as a pair steepness term.",
         encoding="pair", mechanism="Wind adds variance and penalises serve-reliant players.",
         data_paths="Open-Meteo archive (download)", data_status="download_needed", coverage_note="Outdoor matches; reanalysis grid not stadium-level",
         model_overlap="none", pool_rows="U-196", prior_evidence="No study of match results found (lab side-wind serve study only)",
         exposed_2025_26="no", timing_class="market_or_context", build_hours="6", your_rank="", notes="B3's MP-04."),
    dict(id="RS25", name="Ball switch between consecutive events (not recommended)", area="conditions",
         definition="1[the ball model differs from the player's previous event]; count of ball types in the last 4 weeks.",
         encoding="diff", mechanism="Adaptation to ball changes.", data_paths="No compiled table", data_status="not_available",
         coverage_note="ATP centralises balls by swing 2025-27", model_overlap="none", pool_rows="U-196",
         prior_evidence="ATP ball centralisation (2025, R1 checked: no per-event list); AP 2024 (10 brands, 19 types on WTA 2023)",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="20", your_rank="", notes="No evidence; variation removed by 2027."),
    dict(id="RS26", name="Coaching change", area="career",
         definition="1[a dated coach start or split in the last 90 days]; A - B.", encoding="diff",
         mechanism="A change in level before ratings adjust.", data_paths="No structured dated source", data_status="not_available",
         coverage_note="-", model_overlap="none", pool_rows="none", prior_evidence="None found (not searched: cap)",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="30", your_rank="", notes="Low."),
    dict(id="RS27", name="Women's serve-speed state", area="serve_return",
         definition="As men's spd_L: 28-day minus long-run first-serve speed, A - B.", encoding="diff",
         mechanism="State signal the men's model already uses.", data_paths="None public", data_status="not_available",
         coverage_note="WTA API advanced statistics 2021-26 (434 fields) hold no speed (R1 wta_fields.json); all courts tracked from 2026 (documented)",
         model_overlap="none (women)", pool_rows="U-198", prior_evidence="Men's speed nudge (serve_speed_tabpfn)",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="-", your_rank="", notes="Blocked by data; ask SMT, WTA or Stats Perform."),
    dict(id="RS28", name="Physical state from the rally (Hawk-Eye)", area="point_state",
         definition="Groundstroke speed, rally length and distance between hits against the player's own normal over the last 28 days; A - B.",
         encoding="diff", mechanism="A physical state that box scores do not show.",
         data_paths="Court Vision (ATP 2021-24); slam_ball_tracking (AO/RG 2019-24); TDI rally length (2025-26 window)",
         data_status="partial", coverage_note="Thin per player; 2025-26 ATP needs decryption (Court Vision unverified)",
         model_overlap="low", pool_rows="U-213",
         prior_evidence="Burke 2023 (heat shortens rallies, less distance run); Turner 2022 (evening: less distance run)",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="20", your_rank="", notes="point-shot-ideas #1."),
    dict(id="RS29", name="Score-state resilience", area="point_state",
         definition="Per-player effects of being a set down or up and of the within-set lead on serve points (Kovalchik-Ingram model), pooled over 2-3 seasons; A - B.",
         encoding="diff", mechanism="Response to the scoreboard is invisible in box scores.",
         data_paths="data/studies/point_sequence/sequences.parquet", data_status="partial", coverage_note="Point-by-point matches only",
         model_overlap="low", pool_rows="U-206 (dropped)",
         prior_evidence="Kovalchik & Ingram 2016 (2015 Slams: ATP log loss 0.517 -> 0.509 with per-player effects; WTA none)",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="12", your_rank="", notes="Low prior."),
    dict(id="RS30", name="Trust in the close (market-internal)", area="market_info",
         definition="Pinnacle's margin at the close; Pinnacle minus BetOnline de-vigged gap; books pricing; stale-close flag.",
         encoding="context", mechanism="Margins widen where information is unequal; a stale close carries less news.",
         data_paths="data/studies/current_best_model/template_2026-10-10/odds_sources.parquet; data/studies/bet_timing/frame.parquet",
         data_status="partial", coverage_note="Pinnacle closes end Sep 2025", model_overlap="low", pool_rows="U-002, U-007",
         prior_evidence="Barrutiabengoa et al. 2022 (higher margins on WTA, 51,881 matches); Abinzano et al. 2019",
         exposed_2025_26="no", timing_class="market_or_context", build_hours="3", your_rank="",
         notes="Project policy: market-internal inputs only as uncertainty, never as direction."),
]


def main() -> None:
    for r in ROWS:
        assert set(r) == set(COLS), (r["id"], set(COLS) ^ set(r))
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in ROWS:
            w.writerow(r)
    print(f"wrote {len(ROWS)} rows to {OUT}")


if __name__ == "__main__":
    main()
