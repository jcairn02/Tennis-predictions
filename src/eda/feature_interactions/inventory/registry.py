"""The hand-written part of the feature-interactions data map: the 58 model inputs and the raw fields, with their
definitions, per-player availability and timing class (round 0, 6 Oct 2026). build_inventory.py joins these to the
measured coverage (coverage.py) and writes data/studies/feature_interactions/inventory.csv.

Every per-player claim below was checked by reading data (orientation.py, perplayer_form.py, perplayer_load.py,
rebuild_diff.py; results in data/studies/feature_interactions/inventory/*.json) unless the note says "code" (read from
the builder's source) or "doc" (from a study report).
"""
from __future__ import annotations

SAFE = "safe by construction (each player's own matches in order)"
CLOCK = "solved together: needs the leak-proof clock (already built on it)"
MARKET = "market price (pre-match close)"
CONTEXT_T = "match context (known before the match)"
ATTR = "pre-match attribute of the player (known before the match)"
HIST = "post-match field: safe only as each player's history of earlier matches"
FORM_SRC = ("data/studies/ufc_ideas/stageD_profile_features.parquet `adjperf_{s}|decayed` (built by "
            "src/eda/ufc_ideas/stageB_adjperf.py)")
PERPLAYER_FORM = ("yes: data/studies/feature_interactions/inventory/perplayer_form_2013_2024.parquet `{n}_a`/`{n}_b` "
                  "(rebuilt here from ufc_ideas/stageB_adj.parquet z's; A - B reproduces the input to < 1e-7; 2013-2024 "
                  "only)")

# name -> family, definition, kind, upstream (table: column), per_player, timing, notes
MODEL_INPUTS: dict[str, dict] = {
    "odds_logit": dict(
        family="market", kind="diff", timing=MARKET,
        definition="log-odds that A wins from the average closing odds of tennis-data.co.uk, de-vigged by "
                   "normalising 1/odds to sum to one (pairs with overround outside 1.00-1.20 dropped)",
        upstream="predictability_diagnostic/stage1_odds.parquet: p_avg_a (= stage1_baselines p_market = model p_mkt)",
        per_player="yes (each side's price): stage1_odds avg_a/avg_b, ps_a/ps_b, max_a/max_b, b365_a/b365_b, "
                   "overround_avg/ps",
        notes="verified: in_odds_logit == logit(p_avg_a) exactly on 2013-2024"),
    "ratings_iid": dict(
        family="ratings", kind="diff", timing=SAFE,
        definition="log-odds of the iid point model's match-win probability from Stage 3's serve and return ratings: "
                   "p_serve_A = expit(mu + serve_A - return_B), p_serve_B likewise, combined under the scheduled "
                   "format and deciding-set rule",
        upstream="predictability_diagnostic/stage4_features.parquet: rating_matchup|single (via ufc_ideas/stageD)",
        per_player="yes: predictability_diagnostic/stage3_ratings.parquet serve_a/b, return_a/b, sd_serve_a/b, "
                   "sd_return_a/b, serve_pts_a/b, return_pts_a/b, mu_logit, p_serve_a/b",
        notes="verified: logit(iid(p_serve_a, p_serve_b, TB7@6)) equals the input on every non-Slam match; Slams "
              "differ only by their deciding-set rule (stage2_iid.deciding_set_rule)"),
    "elo_games": dict(
        family="ratings", kind="diff", timing=SAFE,
        definition="games-weighted Elo (each update times the winner's games share / a scale; Angelini et al. 2022), "
                   "overall and surface ratings blended like Stage 1's Elo, as log-odds",
        upstream="predictability_diagnostic/stage4_features.parquet: elo_games|single",
        per_player="no on disk; code: stage4_features.weighted_elo_pass returns each match's (R_A, R_B, N_A, N_B, "
                   "surface R_A, R_B, N) before the blend (a copy that keeps them gives per-player values)",
        notes="match_timing/perplayer_features (rebuild on repaired data) correlates 1.0000 but equals only 9% to 1e-6"),
    "adjperf_tpw_2w": dict(
        family="points aggregates", kind="diff", timing=SAFE,
        definition="opponent-adjusted total points won: decayed (half-life 2 weeks) mean of per-match z = (points "
                   "won - what the opponent usually allows) / opponent's MAD, shrunk with K3 = 10 (men) / 20 (women)",
        upstream="ufc_ideas/stageD_features.parquet: adjperf_tpw|decayed",
        per_player=PERPLAYER_FORM.format(n="adjperf_tpw_2w"), notes=""),
    "ios_points_short": dict(
        family="points aggregates", kind="diff", timing=CLOCK,
        definition="IOS serve-points-won offence/defence with a short memory (half-life 4 weeks men, 13 women), "
                   "the points matchup through the iid model, log-odds",
        upstream="match_timing/leakproof_features.parquet: ios_short (pre-rebuild copy)",
        per_player="no on disk; code: match_timing/rebuild.ios_features keeps O[('spw','short')], D[...] per row "
                   "before I.matchup_points; a rerun of ios_time.run_timed for spw (about 2-3 min per tour) gives them",
        notes="equals match_timing leakproof ios_short exactly (pre-rebuild copy)"),
    "points_52w": dict(
        family="points aggregates", kind="diff", timing=SAFE,
        definition="A's serve points won over the last 52 weeks (shrunk to the tour-surface mean with Stage 3's K) "
                   "against B's return points won, and the reverse, through the iid model with the scheduled format, "
                   "log-odds",
        upstream="predictability_diagnostic/stage4_features.parquet: mu_points|52 weeks",
        per_player="no on disk; code: match_timing/rebuild.points_52w holds val['spw'], val['rpw'] per row (on the "
                   "repaired rows; stage4_features' own version matches the model)",
        notes="rebuild version equals the input on 95% of rows (repairs); 52-week window counted from event dates"),
    "sets_14d": dict(
        family="load and age", kind="diff", timing=SAFE,
        definition="log(1 + sets played in matches of events starting in the 14 days before this event, plus "
                   "earlier rounds of this event), missing if a played match in the window lacks a set total",
        upstream="predictability_diagnostic/stage4_features.parquet: sets_14d|single",
        per_player="yes: data/studies/feature_interactions/inventory/perplayer_load_2013_2024.parquet sets_14d_a/b "
                   "(rebuilt here from pre-rebuild Stage 0; exact)",
        notes="time gaps counted from event start dates, not match days (decision 2026-10-05: imprecise, not leaking)"),
    "age": dict(
        family="load and age", kind="diff", timing=SAFE,
        definition="age_A - age_B in years (ages outside 14-50 missing)",
        upstream="predictability_diagnostic/stage4_features.parquet: age|single",
        per_player="yes: stage0_match_players.age (per side); perplayer_load_2013_2024.parquet age_a/b",
        notes="verified exact"),
    "age_sq": dict(
        family="load and age", kind="diff", timing=SAFE,
        definition="(age_A - 25)^2 - (age_B - 25)^2",
        upstream="predictability_diagnostic/stage4_features.parquet: age|single|2",
        per_player="yes (from age)", notes="verified exact"),
}
for _s in ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved", "bp_faced_pg", "brk", "bp_conv",
           "rpw_first", "rpw_second"):
    _ret = _s in ("brk", "bp_conv", "rpw_first", "rpw_second")
    MODEL_INPUTS[f"form_{_s}"] = dict(
        family="two-week profile", kind="diff", timing=SAFE,
        definition=f"adjperf of {_s}: decayed (half-life 2 weeks) mean of the player's per-match opponent-adjusted z "
                   f"(own value minus the opponent's usual allowed value, over the opponent's MAD, clipped +-4), "
                   f"shrunk toward 0 with K3 = " + ("160 (return-skill constants: very small values)" if _ret
                                                     else "10 men / 20 women"),
        upstream=FORM_SRC.format(s=_s), per_player=PERPLAYER_FORM.format(n=f"form_{_s}"),
        notes=("women's hold/brk/bp_faced_pg need service games: missing 2013-2014, partial 2015" if _s in
               ("hold", "brk", "bp_faced_pg") else ""))
for _s in ("ace", "df", "first_in", "bp_faced_pg"):
    MODEL_INPUTS[f"formdef_{_s}"] = dict(
        family="two-week profile", kind="diff", timing=SAFE,
        definition=f"adjdef of {_s}: decayed (2 weeks) mean of how far the player held opponents' {_s} below the "
                   f"opponents' own norm (a return skill), shrunk with K3 = 160",
        upstream=FORM_SRC.format(s=_s).replace("adjperf_", "adjdef_"),
        per_player=PERPLAYER_FORM.format(n=f"formdef_{_s}"),
        notes="women's bp_faced_pg missing 2013-2014" if _s == "bp_faced_pg" else "")
for _s in ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved"):
    _sf = "data/studies/surface_ios/surface_features.parquet"
    MODEL_INPUTS[f"iosO_{_s}"] = dict(
        family="long-memory IOS profile (per surface)", kind="diff", timing=CLOCK,
        definition=f"surface IOS offence on {_s}: the server's effective rating on the match's surface, O + E_s, from "
                   f"a ridge-regularised joint solve of every player's offence/defence with surface deviations "
                   f"(surface-IOS study), as of the match's earliest possible start",
        upstream=f"surface_ios/arms/sprof.parquet in_iosO_{_s} = {_sf}: srf_O_eff_{_s}_a - srf_O_eff_{_s}_b",
        per_player=f"yes: {_sf} srf_O_eff_{_s}_a / _b (also cur_O_{_s}_*, srf_O_{_s}_*, srf_E_{_s}_*)",
        notes="verified exact; for df a higher offence means MORE double faults (bad for the server)" if _s == "df"
        else "verified exact")
    MODEL_INPUTS[f"iosD_{_s}"] = dict(
        family="long-memory IOS profile (per surface)", kind="diff", timing=CLOCK,
        definition=f"surface IOS defence on {_s}: how much the player suppresses the opponent's {_s} on serve, "
                   f"D + F_s on the match's surface",
        upstream=f"{_sf}: srf_D_eff_{_s}_a - srf_D_eff_{_s}_b",
        per_player=f"yes: {_sf} srf_D_eff_{_s}_a / _b (also cur_D_*, srf_D_*, srf_F_*)", notes="verified exact")
    MODEL_INPUTS[f"prod_{_s}"] = dict(
        family="long-memory IOS profile (per surface)", kind="diff", timing=CLOCK,
        definition=f"matchup product on {_s}: O_A x (-D_B) - O_B x (-D_A) with the surface-effective values",
        upstream=f"{_sf}: srf_O_eff/srf_D_eff _a/_b",
        per_player="yes (both factors per player in surface_features)",
        notes="the only cross-player products the model has; verified exact")
for _c, _d in (("tour", "0 men, 1 women (categorical)"), ("surface", "0 hard, 1 clay, 2 grass, 3 carpet (categorical)"),
               ("level", "0 Grand Slam, 1 Tour Finals, 2 1000, 3 500, 4 250 (categorical)"),
               ("indoor", "1 indoor / 0 outdoor from Stage 0; men only (every women's value missing)"),
               ("best_of", "scheduled best of 3 or 5 (men's Slam main draws 5)"),
               ("round", "Stage 0 round_order (Q1=1 .. RR=10, R128=11 .. F=17)")):
    MODEL_INPUTS[_c] = dict(family="context", kind="context", timing=CONTEXT_T, definition=_d,
                            upstream="tabpfn_thinking/frame.parquet x_<name> from stage0_matches",
                            per_player="n/a (match-level)",
                            notes=("women's indoor can be filled from tennis-data.co.uk Court (agrees with Stage 0 on "
                                   "99.2% of men's matches)" if _c == "indoor" else ""))
_PIECES = "data/studies/surface_elo_pieces/pieces.parquet"
MODEL_INPUTS.update({
    "elo_overall": dict(family="ratings", kind="diff", timing=SAFE,
                        definition="Stage 1's overall Elo (retirements counted) as log-odds: (R_A - R_B) ln10/400",
                        upstream=f"{_PIECES}: R_a, R_b", per_player=f"yes: {_PIECES} R_a/R_b, N_a/N_b; also "
                        "predictability_diagnostic/stage1_baselines.parquet elo_a_ret/elo_b_ret, n_a_ret/n_b_ret",
                        notes="verified exact"),
    "elo_surf_offset": dict(family="ratings", kind="diff", timing=SAFE,
                            definition="surface offset Elo: (D_A - D_B) ln10/400, D starts at 0 and moves only on this "
                                       "surface by the surprise of R + D (K tuned 2013-2018)",
                            upstream=f"{_PIECES}: D_a, D_b (missing read as 0)",
                            per_player=f"yes: {_PIECES} D_a/D_b, NS_a/NS_b (surface counts), S_a/S_b, XA_a/XA_b, DG_a/DG_b",
                            notes="verified exact"),
    "surf_season_a": dict(family="surface switching", kind="pair", timing=SAFE,
                          definition="log(1 + A's played matches on this surface earlier this calendar season)",
                          upstream=f"{_PIECES}: season_n_a", per_player="yes (it is per player)", notes="verified exact"),
    "surf_season_b": dict(family="surface switching", kind="pair", timing=SAFE,
                          definition="the same for B", upstream=f"{_PIECES}: season_n_b", per_player="yes", notes=""),
    "surf_layoff_a": dict(family="surface switching", kind="pair", timing=SAFE,
                          definition="log(1 + days since A's last played match on this surface), on the match clock's "
                                     "best-estimate days (obs), capped at 1,095 days (never: the cap)",
                          upstream=f"{_PIECES}: days_since_a", per_player="yes (it is per player)",
                          notes="uses timing.parquet obs of 5 Oct (pre-rebuild)"),
    "surf_layoff_b": dict(family="surface switching", kind="pair", timing=SAFE, definition="the same for B",
                          upstream=f"{_PIECES}: days_since_b", per_player="yes", notes=""),
})

# Raw fields: coverage rows of coverage.py (table, column) -> description
OLD = "data/studies/data_continuity/rebuilds/2026-10-07T0005Z/replaced/data/studies/"
RAW_FIELDS: list[dict] = [
    # bio
    dict(name="hand", family="raw: player bio", cov=("stage0_match_players(pre-rebuild)", "hand_known(both, L or R)"),
         path=OLD + "predictability_diagnostic/stage0_match_players.parquet", columns="hand (R/L/U)",
         per_player="yes", kind="per player", timing=ATTR,
         notes="lefty in 26% (men) / 16-18% (women) of model matches; used once as Stage 4 lefty|single, vs_hand|single"),
    dict(name="height", family="raw: player bio", cov=("stage0_match_players(pre-rebuild)", "height(both)"),
         path=OLD + "predictability_diagnostic/stage0_match_players.parquet", columns="height (cm)",
         per_player="yes", kind="per player", timing=ATTR,
         notes="women 2022-2024 only 64% of matches have both heights"),
    dict(name="country", family="raw: player bio", cov=("stage0_match_players(pre-rebuild)", "country(both)"),
         path=OLD + "predictability_diagnostic/stage0_match_players.parquet", columns="country (IOC)",
         per_player="yes", kind="per player", timing=ATTR,
         notes="same-country matches 5-7%; event country in predictability_diagnostic/stage4_event_country.csv (home|single)"),
    dict(name="age_at_match", family="raw: player bio", cov=("stage0_match_players(pre-rebuild)", "age(both)"),
         path=OLD + "predictability_diagnostic/stage0_match_players.parquet", columns="age (years, decimal)",
         per_player="yes", kind="per player", timing=ATTR,
         notes="birth dates: data/dump/players/sackmann_archive/{atp,wta}/*_players.parquet dob; TML ATP_Database birthdate"),
    dict(name="backhand_weight_turnedpro(ATP only)", family="raw: player bio", cov=None,
         cov_values=(0.9553, None, 0.9430, None),
         path="data/dump/players/tennis_my_life/ATP_Database.parquet",
         columns="backhand (1H/2H/Unknown/blank), weight, height, turnedpro, birthplace, coaches",
         per_player="yes after a join by normalised name + birth date to Sackmann's players (backhand.py)",
         kind="per player", timing=ATTR,
         notes="men only; coverage = both players' backhand known (weight 96%/95%, turned pro 94%/89%); one-handed in "
               "16% of men's player-rows; TML ids are mostly ATP codes; static current values"),
    # rank, seed, entry
    dict(name="rank", family="raw: rank and entry", cov=("stage0_match_players(pre-rebuild)", "rank(both)"),
         path=OLD + "predictability_diagnostic/stage0_match_players.parquet", columns="rank", per_player="yes",
         kind="per player", timing=ATTR, notes="weekly rankings 2010-2026-06 in data/dump/rankings/sackmann_archive/"),
    dict(name="rank_points", family="raw: rank and entry", cov=("stage0_match_players(pre-rebuild)", "rank_points(both)"),
         path=OLD + "predictability_diagnostic/stage0_match_players.parquet", columns="rank_points", per_player="yes",
         kind="per player", timing=ATTR, notes="WTA weekly files also give 'tours' (events counted)"),
    dict(name="seed", family="raw: rank and entry", cov=("stage0_match_players(pre-rebuild)", "seed(either; missing=unseeded)"),
         path=OLD + "predictability_diagnostic/stage0_match_players.parquet", columns="seed", per_player="yes",
         kind="per player", timing=ATTR, notes="missing = unseeded; share = matches with at least one seed"),
    dict(name="entry", family="raw: rank and entry", cov=("stage0_match_players(pre-rebuild)", "entry(either; missing=direct)"),
         path=OLD + "predictability_diagnostic/stage0_match_players.parquet", columns="entry (Q, WC, LL, PR, SE, SR, ALT)",
         per_player="yes", kind="per player", timing=ATTR,
         notes="player-rows on 2013-2024 model matches: Q 12,244, WC 6,583, LL 2,049, PR 483, SE 190, SR 79, ALT 63"),
    # match facts
    dict(name="minutes", family="raw: match facts (post-match; usable only as history)",
         cov=("stage0_matches(pre-rebuild)", "minutes"), path=OLD + "predictability_diagnostic/stage0_matches.parquet",
         columns="minutes", per_player="match-level", kind="history only", timing=HIST,
         notes="women 2013-2015 ~0%; men 2015 52%; else 93-100%"),
    dict(name="score/sets/tiebreaks", family="raw: match facts (post-match; usable only as history)",
         cov=("stage0_match_players(pre-rebuild)", "tb_won_d(both)"),
         path=OLD + "predictability_diagnostic/stage0_match_players.parquet",
         columns="score (match table); tb_won_n/d, sets_won_n/d, games_won_n/d per player", per_player="yes",
         kind="history only", timing=HIST,
         notes="a tiebreak in 39-40% of men's and 22-24% of women's model matches; retirements 2.6-3.3%; the live "
               "Stage 0 changed tb/games counts of 7,597 player-rows to 2024 (match-tiebreak repair)"),
    dict(name="box score counts", family="raw: match facts (post-match; usable only as history)",
         cov=("stage0_match_players(pre-rebuild)", "has_box(both)"),
         path=OLD + "predictability_diagnostic/stage0_match_players.parquet",
         columns="ace, df, svpt, first_in, first_won, second_won, sv_gms, bp_saved, bp_faced (+ rate _n/_d pairs)",
         per_player="yes", kind="history only", timing=HIST,
         notes="women's sv_gms (hold, breaks) missing 2013-2014 and 36% of 2015"),
    dict(name="status (retired)", family="raw: match facts (post-match; usable only as history)",
         cov=("stage0_matches(pre-rebuild)", "status_retired(share, not coverage)"),
         path=OLD + "predictability_diagnostic/stage0_matches.parquet", columns="status, status_detail",
         per_player="match-level", kind="history only", timing=HIST, notes="share of model matches ending in retirement"),
    # event metadata
    dict(name="draw_size", family="raw: event metadata", cov=("stage0_matches(pre-rebuild)", "draw_size"),
         path=OLD + "predictability_diagnostic/stage0_matches.parquet", columns="draw_size", per_player="n/a",
         kind="context", timing=CONTEXT_T, notes=""),
    dict(name="td_Court (indoor, both tours)", family="raw: event metadata",
         cov=("tennis_data_couk_raw(via stage1_odds td_file/td_row)", "td_Court"),
         path="data/dump/odds/tennis_data_couk/<tour>/<series>/<year>.parquet (row = stage1_odds td_row position)",
         columns="Court (Indoor/Outdoor)", per_player="n/a", kind="context", timing=CONTEXT_T,
         notes="fills the women's indoor gap; indoor share 18%/16% men, 9%/6% women"),
    dict(name="td_Location (city)", family="raw: event metadata",
         cov=("tennis_data_couk_raw(via stage1_odds td_file/td_row)", "td_Location"),
         path="data/dump/odds/tennis_data_couk/... (as above)", columns="Location", per_player="n/a", kind="context",
         timing=CONTEXT_T, notes="city; event country table stage4_event_country.csv; altitude/climate not held"),
    # match clock
    dict(name="match clock es/lf", family="raw: match clock", cov=("match_timing_timing(pre-rebuild)", "es_lf(both finite)"),
         path=OLD + "match_timing/timing.parquet", columns="es, lf, obs, width_days, exact, window_basis, n_sources",
         per_player="match-level", kind="context", timing="the clock itself",
         notes="days since 1970; window width 1 day 24%, 2 days 69%, 3-4 days 6% of model matches"),
    dict(name="rest before the match", family="raw: match clock",
         cov=("match_timing_timing(pre-rebuild)", "rest_min_days(both players have a previous match)"),
         path=OLD + "match_timing/timing.parquet + stage0_matches (player order)",
         columns="es(this) - lf(previous own match)", per_player="yes (derived here)", kind="per player", timing=SAFE,
         notes="median minimum rest 2 days (5% at 0); both previous and this match exact: 98%/100% men, 88%/99% women"),
    dict(name="start time of day", family="raw: match clock",
         cov=("match_timing_timing(pre-rebuild)", "start_utc_any_link_source(time of day)"),
         path=OLD + "match_timing/links/{flashscore,api_tennis,live_tennis_api,sofascore,slam_feeds,wta_api,tdi}.parquet",
         columns="start_utc", per_player="match-level", kind="context", timing=CONTEXT_T,
         notes="UTC timestamps, some scheduled not actual; venue time zone needed for local time"),
    # odds beyond the average
    dict(name="Pinnacle close", family="raw: odds", cov=("stage1_odds(pre-rebuild)", "p_ps_a"),
         path=OLD + "predictability_diagnostic/stage1_odds.parquet", columns="ps_a, ps_b, p_ps_a, overround_ps",
         per_player="each side's price", kind="market", timing=MARKET, notes=""),
    dict(name="best price across books (Max)", family="raw: odds", cov=("stage1_odds(pre-rebuild)", "max_a"),
         path=OLD + "predictability_diagnostic/stage1_odds.parquet", columns="max_a, max_b",
         per_player="each side's price", kind="market", timing=MARKET,
         notes="dispersion between books = Max vs Avg implied probability; per-book quotes in the raw files"),
    dict(name="Bet365 close", family="raw: odds", cov=("stage1_odds(pre-rebuild)", "b365_a"),
         path=OLD + "predictability_diagnostic/stage1_odds.parquet", columns="b365_a, b365_b",
         per_player="each side's price", kind="market", timing=MARKET, notes=""),
    dict(name="Expekt/Ladbrokes/StanJames closes", family="raw: odds",
         cov=("tennis_data_couk_raw(via stage1_odds td_file/td_row)", "td_EXW"),
         path="data/dump/odds/tennis_data_couk/... (EXW/EXL, LBW/LBL, SJW/SJL)", columns="EX*, LB*, SJ*",
         per_player="each side's price", kind="market", timing=MARKET,
         notes="only to 2018: EX/LB ~66-71% of 2013-2021 matches, SJ ~23-26%; none 2019-2024"),
    dict(name="Betfair exchange close (BFE)", family="raw: odds",
         cov=("tennis_data_couk_raw(via stage1_odds td_file/td_row)", "td_BFEW"),
         path="data/dump/odds/tennis_data_couk/.../2025.parquet, 2026.parquet", columns="BFEW, BFEL",
         per_player="each side's price", kind="market", timing=MARKET,
         notes="ONLY in the 2025 and 2026 files: none before the closed test years, so unusable for discovery"),
    # point-level
    dict(name="point-by-point (any source)", family="raw: point and shot level",
         cov=("shot_level_stage0_source_matches", "point_by_point(any source, n_points>0)"),
         path="data/studies/shot_level/stage0_source_matches.parquet + stage1_points_<source>.parquet",
         columns="source, n_points, has_* flags", per_player="via stage1_match_stats per player-match",
         kind="history only", timing=HIST, notes="men 2022-2024 90% (Infosys, Court Vision); women 23-27%"),
    dict(name="serve speed", family="raw: point and shot level",
         cov=("shot_level_stage1_match_stats(per player-match)", "spd1(both, d>0)"),
         path="data/studies/shot_level/stage1_match_stats.parquet", columns="spd1_n/d, spd2_n/d, spd1_sq_n/d",
         per_player="yes (per player-match)", kind="history only", timing=HIST,
         notes="men 12% (2013-2021) and 58% (2022-2024); women 12% and 16%"),
    dict(name="ball tracking", family="raw: point and shot level",
         cov=("shot_level_stage0_source_matches", "pbp_has_tracking"),
         path="data/studies/shot_level/stage1_points_slam_tracking.parquet, court_vision", columns="tracking fields",
         per_player="via points", kind="history only", timing=HIST, notes="men 1% / 45%, women 0% / 8%"),
    dict(name="point sequences (server and winner per point; study in progress)", family="raw: point and shot level",
         cov=None, cov_values=(0.884, 0.607, 0.954, 0.989),
         path="data/studies/point_sequence/sequences.parquet (builder src/eda/point_sequence/build.py, another session)",
         columns="match_id (pre-rebuild ids), source, tier, usable, seq, set_no, game_no, game_idx, pt_no, is_tb, ...",
         per_player="via the point's server and winner", kind="history only", timing=HIST,
         notes="coverage from that study's own coverage_model.csv read at 18:09 on 6 Oct, mid-build, not verified here; "
               "both players with >= 20 earlier sequenced matches 96/53/90/93%; women 15% (2013) -> 99% (2020-24)"),
    dict(name="WTA advanced match totals", family="raw: point and shot level", cov=None,
         path="data/studies/shot_level/stage0_source_matches.parquet (source wta_advanced)",
         columns="point endings, net, stroke totals (no points)", per_player="per match", kind="history only",
         timing=HIST, notes="women 2021-2024: 74-78% of model matches; endings in 86% of its rows"),
]
