"""Writes docs/studies/unpriced_leads/team/market_practitioner_ideas.csv (the B3 memo's idea table).
Run: ./python.sh data/studies/unpriced_leads/team/market_practitioner/write_ideas_csv.py
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
DEST = ROOT / "docs/studies/unpriced_leads/team/market_practitioner_ideas.csv"
COLS = ["id", "name", "area", "definition", "encoding", "mechanism", "data_paths", "data_status", "coverage_note",
        "model_overlap", "pool_rows", "prior_evidence", "exposed_2025_26", "timing_class", "build_hours", "your_rank",
        "notes"]

BOL = "data/dump/odds/oddstrader/betonline_matches.parquet"
BT = "data/studies/bet_timing/frame.parquet"
OS = "data/studies/current_best_model/template_2026-10-10/odds_sources.parquet"
BP = "data/studies/current_best_model/template_2026-10-10/book_prices.parquet"
S0 = "data/studies/predictability_diagnostic/stage0_matches.parquet; stage0_match_players.parquet"
CLK = "data/studies/match_timing/timing.parquet"
PROBE = "data/studies/unpriced_leads/team/market_practitioner/probes/receipts.jsonl"

rows = [
    dict(id="MP-01", name="Totals-implied competitiveness (excess total)", area="market_info",
         definition="excess = BetOnline total-games line minus its expectation given the moneyline (|logit p|, logit p^2), "
                    "tour, best_of, surface, indoor, level and the pair's in-model serve levels (IOS hold and ace sums), "
                    "fitted outcome-free on 2019-2024; enters as z(excess) x logit p_close (+ excess = the totals market "
                    "expects a closer match than the moneyline). Members: excess at the open; total-implied minus "
                    "moneyline-implied favourite strength (diff, inverted fit); totals move net of the moneyline-implied move.",
         encoding="context",
         mechanism="Moneyline and totals are bet by different money and settle differently (totals void on any "
                   "retirement, moneyline has action after one set at Pinnacle and BetOnline); no arbitrage ties them, "
                   "so a moneyline tilted by favourite or injury money is not corrected by the totals market, and the "
                   "gap carries the market's own view of closeness and retirement risk.",
         data_paths=f"{BOL} (tg_open_line, tg_close_line, tg_*_uncertain, eid); eid link {OS}; {BT}; "
                    "data/studies/feature_universe/store.parquet level sums (U-217, U-222, U-229)",
         data_status="on_disk",
         coverage_note="BetOnline totals on 40% of 2019 frame matches, 90-97% of 2020-23, 83% of 2024, 84% of 2025 "
                       "(~4,300), 96% of 2026 (~4,200); both tours, main tour incl. Slams; Pinnacle totals not held "
                       "(live only)",
         model_overlap="medium (serve dominance known to IOS and ratings_iid; the net-of-IOS construction removes it; "
                       "check R2 with the 56 inputs)",
         pool_rows="none (U-010 nearest)",
         prior_evidence="Outcome-free, this memo (BetOnline 2019-2024, 22,086 matches): the total's residual given the "
                        "moneyline has SD 0.94 games at the open, 0.88 at the close (best of 3); the opening favourite "
                        "drifts when the total says closer (-0.013 |log-odds| per SD, z -1.8; best of 5 z -1.5); the "
                        "total follows the moneyline (z -17). Provider claim: books mis-set game totals when Slam "
                        "tiebreak rules changed, 2019-21 (Rose-Berman 2024). No outcome test anywhere.",
         exposed_2025_26="no (market structure and an outcome-free <=2024 check only)",
         timing_class="market_or_context", build_hours="8", your_rank="1",
         notes="Register two-sided. Bet time: Pinnacle's and BetOnline's live totals exist. Retirement wedge: also score "
               "with retirements before a completed set voided."),
    dict(id="MP-02", name="Line momentum: the close's reaction to its own move", area="market_info",
         definition="mv = logit p_close - logit p_open at one book (BetOnline: p_bol_open to p_bol_close; Pinnacle: "
                    "OddsTrader id 20 opening p_ot20o to its close), oriented to A, RMS-scaled; tested beyond that "
                    "book's own close, overall and by limit tier: tour, level (Slam/1000 vs 500/250), first match at "
                    "the event vs later round, |L|.",
         encoding="diff",
         mechanism="The close ends a constrained process: limits cap sharp money in low-limit segments (WTA, 250s, "
                   "early rounds), so moves can stop short (momentum survives); public match-day money can overshoot "
                   "(reversal). Neither is removed by the close itself.",
         data_paths=f"{BT} (p_bol_open, p_bol_close, h_bol_open, ok_*, known_bol_open); {OS} (p_ot20o, p_ot20, "
                    "after_ot20_min, p_ps)",
         data_status="on_disk",
         coverage_note="BetOnline open+close: 1,731 (2018), 3,971-4,881 a season 2019-2024 (2,149 in 2020), 4,909 "
                       "(2025), 3,251 (2026 to the frame's end); Pinnacle opening 2018 - 7 Sep 2025 (2,164-4,994 a "
                       "season; 4,142 in 2025)",
         model_overlap="low", pool_rows="U-010; U-279 (I-085 drifting favourite)",
         prior_evidence="Moskowitz 2021 (US sports: open-to-close momentum reversed by outcomes, below costs); "
                        "Buchdahl (Pinnacle tennis 2015-19, 68,361 matches, provider claim: openers 'do not fully "
                        "converge', gradient 0.825); bet_timing: BetOnline moves 2.5 points open to close but not "
                        "toward the model (2020-26). The move's own residual never tested.",
         exposed_2025_26="no (bet_timing's 2025-26 move readings concern the model, not this statistic)",
         timing_class="market_or_context", build_hours="4", your_rank="3",
         notes="Two-sided. Test each book's move against its own close (the lead's registered secondaries). Outcome-free "
               "check here: no differential move for US or top-10 players at BetOnline (<=2024)."),
    dict(id="MP-03", name="Late steam and the line path", area="market_info",
         definition="From OddsTrader lineHistory (BetOnline; Pinnacle to Sep 2025): move in the last 3 h before the "
                    "listed start, number of line changes, time of the last change; late_share = late move / total "
                    "move. Tested beyond the close and, outcome-free, as move-so-far predicting the remaining move.",
         encoding="diff",
         mechanism="Late moves carry warm-up, injury and highest-limit sharp money; whether the close over- or "
                   "under-shoots them is untested; move-so-far predicting the rest is the 'beat the move' business.",
         data_paths="OddsTrader lineHistory endpoint (documented in src/ingest/oddstrader.py, unused)",
         data_status="download_needed",
         coverage_note="2 requests per match: ~68,000 for every BetOnline match 2018-26; a 5,000-match sample ~10,000",
         model_overlap="low", pool_rows="U-010",
         prior_evidence="none in tennis; Moskowitz 2021 (overreaction)",
         exposed_2025_26="no", timing_class="market_or_context", build_hours="16", your_rank="10",
         notes="Refines MP-02; pacing and receipts per the scraping decision."),
    dict(id="MP-04", name="Wind at the scheduled start, indoor as negative control", area="conditions",
         definition="Mean wind speed and gusts (Open-Meteo archive, hourly) at the venue over [listed start, +2 h]; "
                    "context z(wind) x logit p_close (prediction: flatter) and diff z(wind) x serve-strength gap "
                    "(iosO_ace or iosO_first_won, A - B: the bigger server's edge shrinks). The same columns built for "
                    "indoor matches from the outside weather are the placebo.",
         encoding="context",
         mechanism="Books price players, not weather; wind compresses serve dominance and adds error variance; "
                   "BetOnline's last line is stamped over 60 min before the listed start in 30-43% of matches "
                   "(observed), so the day's conditions often come after it.",
         data_paths=f"Open-Meteo archive API (probe: {PROBE}); venue gazetteer (to build, ~150 main-tour venues); "
                    f"listed start hour: {BOL} dt_utc (2018-26), else session norms; in_indoor in the frame",
         data_status="download_needed",
         coverage_note="every outdoor frame match 2013-2026 (indoor 6-20% a season); ~4,600 outdoor matches in 2025, "
                       "~4,100 in 2026",
         model_overlap="low (indoor flag, surface)", pool_rows="U-196; U-195",
         prior_evidence="provider claims: winds above ~15 mph favour underdogs (tennismajors, tennisnerd; no data); "
                        "no project test",
         exposed_2025_26="no", timing_class="market_or_context", build_hours="16", your_rank="2",
         notes="Archive weather at the listed hour is a near-nowcast for a bet at the close; register a forecast-based "
               "variant for live use. Stratify by stale vs fresh close (MP-25)."),
    dict(id="MP-05", name="Heat stress x age and climate of origin", area="conditions",
         definition="Approximate WBGT from temperature, humidity and radiation (Open-Meteo) at the listed hour, "
                    "outdoor; diff z(heat) x (age_A - age_B) and z(heat) x (home-climate gap: mean summer temperature of "
                    "the player's country, A - B); indoor placebo.",
         encoding="diff",
         mechanism="Heat costs are physiological and player-specific; ratings and prices carry no heat term; the 2026 "
                   "ATP heat rule shows the issue is live.",
         data_paths="as MP-04, plus a country climate table (Open-Meteo climate API or a static table); age in Stage 0",
         data_status="download_needed",
         coverage_note="outdoor frame matches; hot sessions (WBGT >= 28 C) a minority, concentrated at the AO, Miami, "
                       "Cincinnati, Washington, US Open, Asian swing",
         model_overlap="low (age is an input; heat x age is not)", pool_rows="U-196",
         prior_evidence="Smith et al. 2018 (JSAMS; AO 2014-16, 360 matches each tour: higher WBGT, more doctor calls, "
                        "fewer winners, more double faults); edge_anatomy scout #11 (gate first)",
         exposed_2025_26="no", timing_class="market_or_context", build_hours="6", your_rank="6",
         notes="Shares the gazetteer and pull with MP-04."),
    dict(id="MP-06", name="Altitude x serve dominance and altitude experience", area="conditions",
         definition="Venue elevation (from the gazetteer's coordinates); diff 1[elevation > 500 m] x serve-strength gap "
                    "(A - B) and x (matches above 500 m in the last 365 days, A - B, own sequence).",
         encoding="diff",
         mechanism="Thin air speeds the ball and rewards big servers; adaptation takes days; books apply at most a "
                   "venue reputation (Madrid, Gstaad, Kitzbuehel, Bogota, Guadalajara).",
         data_paths="gazetteer + Open-Meteo elevation; Stage 0 for each player's venues",
         data_status="download_needed",
         coverage_note="few main-tour weeks (Madrid both tours; Gstaad, Kitzbuehel, Bogota, Guadalajara 2022-23)",
         model_overlap="low", pool_rows="U-196",
         prior_evidence="none tested; B-VENUE (venue pace x ace offence, +2.50 / +2.72, 2014-24) is the nearest",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="3", your_rank="14",
         notes="Small sample; fold into the conditions bundle."),
    dict(id="MP-07", name="Finals-race pressure", area="career",
         definition="For tour-level matches from August: each player's year-to-date race points (results x a per-year "
                    "points table, or downloaded race standings) and the gap to the last qualifying place (ATP and WTA "
                    "top 8) from results finished before es; states in_contention (gap <= points available in his "
                    "remaining events), clinched, eliminated; diffs of in_contention and clinched.",
         encoding="diff",
         mechanism="Incentives are discussed but not modelled: books' openers lean on ratings and rankings; a "
                   "qualified player conserves, a contender pushes, an eliminated one may be on holiday.",
         data_paths=f"{S0} (results, rounds, levels); {CLK}; points tables from the ATP/WTA rulebooks (to compile)",
         data_status="partial",
         coverage_note="August-November tour-level matches (~35% of a season); players in contention ~10-20 a tour",
         model_overlap="low (points_52w, sets_14d)", pool_rows="U-174; U-282 (B-MOTIV); U-296 (I-061 autumn odometer)",
         prior_evidence="B-MOTIV (pre-Slam top-20, post-Slam letdown) z1 +2.39, z2 +0.49 (2014-24, failed "
                        "replication); I-061 inside B9a z2 +2.52; race pressure never built",
         exposed_2025_26="no", timing_class="needs_clock", build_hours="14", your_rank="4",
         notes="The cut-off combines other players' results: clock + probe.py. Next Gen race (age <= 20) as a member."),
    dict(id="MP-08", name="Ranking cliffs: Slam seeding and direct entry", area="career",
         definition="For matches in the 4 weeks before a Slam's seeding ranking (seeds 1-32) or its entry-deadline "
                    "ranking (direct entry about top 104): 1[rank 28-40] and 1[rank 90-120] at the match, signed by "
                    "whether this round's points would cross the line; A - B.",
         encoding="diff",
         mechanism="A seed avoids top-8 opponents for two rounds and a direct entry saves qualifying; the money and "
                   "draw value are large, invisible to rating-based prices.",
         data_paths=f"{S0} (rank, rank_points at the match); Slam dates; deadlines from the rulebooks",
         data_status="on_disk",
         coverage_note="a few hundred matches a tour-season near each cliff",
         model_overlap="low (points_52w)", pool_rows="U-174",
         prior_evidence="none tested", exposed_2025_26="no", timing_class="own_sequence", build_hours="6",
         your_rank="8", notes="Published ranking is a pre-match fact."),
    dict(id="MP-09", name="Points to defend", area="career",
         definition="Points the player earned at the same tournament last year (round reached x points table) divided "
                    "by his ranking points, plus 1[defending champion]; A - B.",
         encoding="diff",
         mechanism="Rolling 52-week rankings make last year's result a live stake; books do not price stakes.",
         data_paths=f"{S0} (tournament_id, year, round); points tables",
         data_status="partial", coverage_note="every tour-level match with a prior edition",
         model_overlap="low", pool_rows="U-174",
         prior_evidence="never built (B-MOTIV's points-to-defend member deferred)",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="4", your_rank="13",
         notes="Sign open: motivation or pressure."),
    dict(id="MP-10", name="Player's beat-the-close record", area="other",
         definition="For each player, over his previous up to 60 priced main-tour matches (all with lf + 1 <= es), the "
                    "shrunk mean of (result - closing probability) = sum(y - p) / (n + 30); members by role (as "
                    "favourite, as underdog) and by surface; A - B. For Look A, a version frozen at 31 Dec 2024.",
         encoding="diff",
         mechanism="Books' and bettors' player models share blind spots (style, returning, reputation); a player the "
                   "close has kept mispricing may keep being mispriced. A catch-all for unnamed player traits.",
         data_paths="data/studies/current_best_model/template_2026-10-10/model_frame.parquet (p_mkt) with Stage 0 ids",
         data_status="on_disk", coverage_note="all frame matches from 2015 (needs two seasons of history)",
         model_overlap="medium (IOS profile and form may explain persistent residuals; check R2)", pool_rows="none",
         prior_evidence="none in tennis; first gate = split-half reliability of player residuals on <=2024",
         exposed_2025_26="partly (the mechanism leans on edge_anatomy's 2025-26 finding that men's returning strength "
                         "is under-rated)",
         timing_class="own_sequence", build_hours="4", your_rank="5",
         notes="Uses past outcomes as inputs, like Elo; the frozen variant keeps Look A blind."),
    dict(id="MP-11", name="Rest hours from the previous match", area="rhythm_body",
         definition="Hours between the previous match's estimated end (its listed start from OddsTrader dt_utc plus "
                    "its minutes from Stage 0, imputed from games where missing) and this match's listed start, capped "
                    "at 72; members 1[rest < 20 h] and 1[previous ended after 23:00 local and this starts before 15:00 "
                    "next day]; A - B.",
         encoding="diff",
         mechanism="Models and most bettors count days; tournament schedulers give stars the better slots; a late "
                   "finish is followed by an overnight line posted with thin money.",
         data_paths=f"{BOL} (dt_utc listed starts 2018-26: 290 distinct times, real hours); {S0} (minutes, score); "
                    "official feeds for Slams and the WTA API (MatchTimeStamp)",
         data_status="partial",
         coverage_note="2018-2026 main tour via OddsTrader listings; TennisLive start times are placeholders (09:00) "
                       "and the match clock is day-level",
         model_overlap="medium (sets_14d, surf_layoff)", pool_rows="U-195; U-291 (I-056); U-139",
         prior_evidence="days- and minutes-based load unresolved beyond the close (B-LOAD +0.63, B-PREV -0.07); hours "
                        "never built (scout #7, register C07)",
         exposed_2025_26="partly (edge_anatomy found the schedule family unpriced in 2025-26)",
         timing_class="own_sequence", build_hours="10", your_rank="7",
         notes="Overlaps B1's lens; my angle is the overnight line (MP-12)."),
    dict(id="MP-12", name="Formation window (line age) as a stratifier", area="market_info",
         definition="h_open = hours between BetOnline's first recorded line and the listed start (h_bol_open); "
                    "context 1[h_open < 12]; registered as a stratifier for late-information statistics (MP-04, "
                    "MP-11, MP-16): their coefficient expected larger where the line formed fast.",
         encoding="context",
         mechanism="Maturity takes time and money; later-round lines are posted after the previous round ends.",
         data_paths=f"{BT} (h_bol_open)", data_status="on_disk",
         coverage_note="2018-2026; median opener 31-38 h before start to 2024, 28.7 h in 2025, 24.6 h in 2026 (a drift)",
         model_overlap="low", pool_rows="none (round-0 MKT-17, never built)",
         prior_evidence="bet_timing: S - A tie at every opening time (the model inherits the opener's softness)",
         exposed_2025_26="no", timing_class="market_or_context", build_hours="1", your_rank="",
         notes="Not a direction; use it to stratify."),
    dict(id="MP-13", name="Polymarket informed flow (2025-26 only)", area="market_info",
         definition="Net stake toward A from wallets classified as clearly beating Polymarket's close using only "
                    "markets settled before the window opens (polymarket_sharp_money's rule, walk-forward), placed "
                    "48-6 h before the listed start, divided by all stake in that window; plus Polymarket's price move "
                    "over the window.",
         encoding="diff",
         mechanism="No sportsbook shows who bets; on Polymarket the accounts that beat the close are visible, and "
                    "their early money may hold information the books' close lacks (most of all for women, where "
                    "BetOnline's 2026 line lagged the exchanges).",
         data_paths="src/eda/polymarket_sharp_money/ (build_positions.py, prematch.py); data/dump/odds/polymarket/trades/",
         data_status="partial",
         coverage_note="Sep 2025 - 5 Oct 2026 on disk; main tour 2026 ~95% of matches listed; early books thin; needs "
                       "a live trade poller for a prospective window",
         model_overlap="low", pool_rows="U-012; U-011",
         prior_evidence="polymarket_sharp_money: 831 clear winners beat Polymarket's close by +1.26c per $1 on held-out "
                        "matches (2025-26)",
         exposed_2025_26="yes (Polymarket 2025-26 closes and settled results, through 21 Sep 2026, inside the sealed "
                         "window)",
         timing_class="market_or_context", build_hours="20", your_rank="9",
         notes="No history before Sep 2025: register a fixed definition now and read it once on matches after the "
               "registration date (Look B from 29 Jul 2026 was partly read in aggregate by that study)."),
    dict(id="MP-14", name="Edition pace learned this week", area="conditions",
         definition="Ace rate in this edition's matches completed before es (lf + 1 <= es) over the players' IOS "
                    "expectation (shrunk by service games), times the pair's ace-offence gap (A - B); context version "
                    "as a slope modifier.",
         encoding="diff",
         mechanism="This year's balls, resurfacing and weather differ from the venue's history (Paris 2025 moved "
                   "venue); bettors learn it from commentary; the price applies only part of serve-dominance scaling.",
         data_paths=f"{S0} box scores; {CLK}; IOS components (tabpfn_leakproof upload)",
         data_status="on_disk", coverage_note="all frame matches from the second round of each edition",
         model_overlap="medium (iosO_ace, prod_ace)", pool_rows="U-192; U-254 (B-VENUE)",
         prior_evidence="B-VENUE from earlier editions: +2.50 model / +2.72 price (2014-24, unseen on 2025-26)",
         exposed_2025_26="no", timing_class="needs_clock", build_hours="10", your_rank="11",
         notes="Cross-player: probe.py required."),
    dict(id="MP-15", name="Doubles tells", area="rhythm_body",
         definition="From TennisLive's listed doubles, name-linked to singles players: 1[gave a walkover or retired in "
                    "doubles at this event or in the last 14 days], doubles sets in the last 3 days, 1[entered doubles "
                    "here]; A - B.",
         encoding="diff",
         mechanism="Markets and singles models watch singles; a doubles withdrawal is a cheap health tell rarely "
                   "reported, and doubles load is invisible to singles histories.",
         data_paths="data/dump/points/tennislive/listed.parquet (discipline, player1_members, end_reason, start_utc)",
         data_status="partial",
         coverage_note="tour ~1,800-1,950 and Slam ~500 doubles matches a season 2018-25 (2020 ~830; 2026 partial); names, not ids",
         model_overlap="low", pool_rows="none",
         prior_evidence="none; edge_anatomy scout #12 (load only, 'likely unresolved')",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="12", your_rank="12",
         notes="Read end_reason only for <=2024 in discovery."),
    dict(id="MP-16", name="Lucky loser late replacement", area="other",
         definition="1[A is LL] - 1[B is LL] (Stage 0 entry) and its product with 1[BetOnline's first line < 8 h before "
                    "the start]; plus the LL's qualifying matches here.",
         encoding="diff",
         mechanism="The opponent prepared for someone else; the LL is warm; the line is posted late with low limits.",
         data_paths=f"{S0} (entry); {BT} (h_bol_open)", data_status="on_disk",
         coverage_note="an LL in 4-6% of frame matches 2018-2026", model_overlap="low",
         pool_rows="U-176; U-309 (I-076); U-138",
         prior_evidence="entry type alone ties given the close (U-176); I-076 rhythm vs cold start +0.99",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="2", your_rank="", notes=""),
    dict(id="MP-17", name="Pre-event injury withdrawals", area="rhythm_body",
         definition="1[withdrew from an event citing injury in the last 30 days] and days since, from Wikipedia "
                    "edition pages' Withdrawals sections (or ATP/WTA entry lists); A - B.",
         encoding="diff",
         mechanism="High-profile withdrawals are priced; mid-ranked players' withdrawals at 250s are not watched, and "
                   "no layoff measure sees a two-week gap with a stated injury.",
         data_paths="Wikipedia tournament edition pages (to scrape)", data_status="download_needed",
         coverage_note="~1,800 edition pages 2013-2026; reasons stated for most top-100 withdrawals",
         model_overlap="low (surf_layoff)", pool_rows="U-136",
         prior_evidence="I-044 returning from injury x reputation +0.48 (exploratory); I-043 rust uses breaks",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="18", your_rank="15", notes=""),
    dict(id="MP-18", name="Attention and liquidity context", area="market_info",
         definition="Context: OddsTrader books with a pre-start line (<= 30 min after the listed start), h_bol_open, "
                    "Polymarket pre-match stake (2025-26); modulators of other statistics.",
         encoding="context",
         mechanism="Thin markets price less information.",
         data_paths=f"{OS} (after_ot*_min); {BT}", data_status="on_disk",
         coverage_note="books per match (median) 30-34 in 2018-21, 24-25 in 2024-25, 12 in 2026: a structural break",
         model_overlap="low", pool_rows="U-194; U-273 (B-INFO)",
         prior_evidence="B-INFO block +0.30 (null) with rank-based attention", exposed_2025_26="no",
         timing_class="market_or_context", build_hours="2", your_rank="", notes="Avoid book counts after 2025."),
    dict(id="MP-19", name="Public attention (fame) premium", area="other",
         definition="Wikipedia pageviews of the player's article: 30-day mean before the match as a log residual on "
                    "his ranking, and the 7-day / 90-day surge; A - B.",
         encoding="diff",
         mechanism="Recreational money follows names; a recreational book may shade popular players.",
         data_paths=f"Wikimedia pageviews API (probe: {PROBE})", data_status="download_needed",
         coverage_note="from July 2015; ~2,000 player articles",
         model_overlap="low", pool_rows="U-177; U-270 (I-083); U-272 (LIT-2)",
         prior_evidence="Ramirez et al. 2023 (WTA buzz; gone after 2020 per Clegg & Cartlidge). Outcome-free gate here "
                        "(<=2024): BetOnline does not shade US players (+0.0008 log-odds, z 0.7) or top-10 players "
                        "relative to Pinnacle, and their prices do not move differently open to close",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="10", your_rank="",
         notes="The clientele mechanism failed its gate; only an all-book fame bias remains."),
    dict(id="MP-20", name="Night session x player's night record", area="conditions",
         definition="1[local listed start >= 18:00] x the player's own shrunk night-minus-day residual; A - B.",
         encoding="diff", mechanism="Cooler, heavier conditions under lights suit some games; not in ratings.",
         data_paths=f"{BOL} dt_utc + venue time zones (gazetteer)", data_status="partial",
         coverage_note="night sessions at Slams (AO, USO), IW, Miami, Cincinnati, Asian events",
         model_overlap="low", pool_rows="U-195", prior_evidence="none", exposed_2025_26="no",
         timing_class="own_sequence", build_hours="6", your_rank="", notes="Player-specific: noisy."),
    dict(id="MP-21", name="Exhibition and team-event load", area="rhythm_body",
         definition="1[played Laver Cup, United Cup, Davis Cup Finals or qualifiers, Six Kings Slam or UTS in the last "
                    "10 days] plus travel distance; A - B.",
         encoding="diff", mechanism="Off-tour matches and travel are invisible to tour histories.",
         data_paths="Wikipedia event pages; Stage 0 (if team ties are present)", data_status="download_needed",
         coverage_note="tens of players a season", model_overlap="low", pool_rows="none",
         prior_evidence="none", exposed_2025_26="no", timing_class="own_sequence", build_hours="8", your_rank="",
         notes=""),
    dict(id="MP-22", name="Slam first-round entrant with a health doubt", area="rhythm_body",
         definition="1[Slam first round] x 1[retired, gave a walkover or withdrew in the last 28 days]; A - B.",
         encoding="diff", mechanism="First-round prize money draws entrants who are not fit.",
         data_paths=f"{S0} (status for prior matches, <=2024 in discovery)", data_status="on_disk",
         coverage_note="a few dozen matches a season", model_overlap="low", pool_rows="U-136; U-178",
         prior_evidence="none; the 2018 Slam rule (half prize money for on-site withdrawal) weakened it",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="2", your_rank="", notes="Rare."),
    dict(id="MP-23", name="Overnight close", area="market_info",
         definition="Context: listed start when both US Eastern (00:00-08:00) and central Europe (00:00-07:00) are "
                    "asleep in the final hours; a modulator.",
         encoding="context", mechanism="Fewer bettors set the last price.",
         data_paths=f"{BOL} dt_utc", data_status="on_disk",
         coverage_note="AO, Asian events", model_overlap="low", pool_rows="none", prior_evidence="none",
         exposed_2025_26="no", timing_class="market_or_context", build_hours="1", your_rank="", notes=""),
    dict(id="MP-24", name="Settlement wedge (retirement risk), test design", area="market_info",
         definition="Score registered tests with retirements before a completed set treated as void (both books' "
                    "moneyline rule) and report retirements separately; shrunk retirement hazard per player as a "
                    "control.",
         encoding="diff",
         mechanism="The close prices the bet the book settles; the model's target counts every retirement as a loss.",
         data_paths=f"{S0} (status, score; <=2024 in discovery)", data_status="on_disk",
         coverage_note="retirements are rare at tour level (1.6% of matches in 1968-2010, event_levels section 9)", model_overlap="low", pool_rows="U-178; U-260 (I-042)",
         prior_evidence="I-042 retirement hazard x price -0.64 (null); Pinnacle rule text accessed 13 Oct 2026",
         exposed_2025_26="no", timing_class="own_sequence", build_hours="2", your_rank="",
         notes="Design, not a lead. Totals void on any retirement: matters for MP-01."),
    dict(id="MP-25", name="Stale benchmark close, test design", area="market_info",
         definition="Minutes between BetOnline's last recorded line and the listed start (bol_after_listed_min); "
                    "stratify every late-information statistic's test: fresh (<= 60 min) vs stale.",
         encoding="context",
         mechanism="From 7 Sep 2025 the model's price is BetOnline's last recorded line, which can precede the start by "
                   "hours, so late news looks 'unpriced'.",
         data_paths=BP, data_status="on_disk",
         coverage_note="BetOnline's last line > 60 min before the listed start: ATP 20-38%, WTA 26-43% a season "
                       "2018-26",
         model_overlap="low", pool_rows="none",
         prior_evidence="edge_anatomy: women's BetOnline line ~4.5 mLL behind the exchanges in 2026, partly timing",
         exposed_2025_26="partly (edge_anatomy's 2026 benchmark gap used 2026 results)",
         timing_class="market_or_context", build_hours="1", your_rank="", notes="Design, not a lead."),
    dict(id="MP-26", name="Outright-implied strength vs the match price", area="market_info",
         definition="Tournament-winner prices inverted into a strength (draw simulation), minus the match price's "
                    "implied strength; A - B.",
         encoding="diff", mechanism="Outrights are bet by other money and updated on other news.",
         data_paths="Polymarket tournament-winner markets (2025-26); archived outrights (OddsPortal) unknown",
         data_status="download_needed", coverage_note="2025-26 only unless archives exist",
         model_overlap="low", pool_rows="none", prior_evidence="none", exposed_2025_26="no",
         timing_class="market_or_context", build_hours="20", your_rank="", notes="Long shot."),
    dict(id="MP-27", name="Coaching change", area="career",
         definition="1[announced coaching change in the last 60 days]; A - B.",
         encoding="diff", mechanism="New-coach bounce or disruption; news-only.",
         data_paths="no systematic source", data_status="not_available", coverage_note="",
         model_overlap="low", pool_rows="none", prior_evidence="none", exposed_2025_26="no",
         timing_class="own_sequence", build_hours="", your_rank="", notes="Listed for completeness."),
    dict(id="MP-28", name="Ball brand switch between consecutive events", area="conditions",
         definition="1[this event's ball brand differs from the player's previous event's]; A - B.",
         encoding="diff", mechanism="Players complain about ball changes; books ignore them.",
         data_paths="event fact sheets (manual)", data_status="download_needed",
         coverage_note="completeness unknown", model_overlap="low", pool_rows="U-196",
         prior_evidence="provider claims only (AP 2024)", exposed_2025_26="no", timing_class="own_sequence",
         build_hours="12", your_rank="", notes=""),
]

with DEST.open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=COLS, quoting=csv.QUOTE_MINIMAL)
    w.writeheader()
    for r in rows:
        assert set(r) == set(COLS), (r["id"], set(COLS) ^ set(r))
        w.writerow(r)
print(f"wrote {len(rows)} rows to {DEST}")
