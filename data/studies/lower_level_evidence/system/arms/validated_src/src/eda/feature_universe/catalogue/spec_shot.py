"""Universe rows: shot- and point-level families. Field order as spec_market."""
FAMILY = "shot and point level"
G = "[mLL: + = feature or arm better; tie = interval spans 0]"
E = "[onE/onM: mLL added to surface Elo / the average close, + = better]"
SL = "shot_level/stage3_sides (A|<stat>|<side>|<form>, prior-filled: use |has); stage2_features (A - B)"
NOTHING = "against the closing odds 0 of 280 shot-level rows clear the line (shot_level stage 2)"
ROWS = [
    ("serve speed (first and second; level and change)", "serve", "spd1, spd2 histories (career, 2-week, 52-week; "
     "change dec2 - w52)", "pair", SL, "sl__*", "BN", "SC", "store:sl__spd1_w52_ab",
     G + " men's serve-speed profile onM 0.24 [0.07, 0.41] (2022-26, shot_level); men's 14-day speed change replication "
     "+0.090 [+0.017, +0.162] log-odds per SD given the model (+ = a rise wins more), discovery ties on 860 matches "
     "(point_sequence, 2025-26 untouched)", "none", "yes",
     "thin before 2022 (men 11-25% of matches); the earlier shot-level windows include 2025-26; the store keeps a "
     "value only where the source has real data (its |has flag), never the prior fill",
     "medium: the one replicated point-level signal (men)"),
    ("serve speed, new sources (2021-26)", "serve", "ATP first-serve averages (ManTennisData, Oct 2021 - Oct 2026) and "
     "decrypted AO/RG 2025-26 timed points", "pair", "serve_speed_acquisition (data/dump; see its README)", "", "BD", "SC",
     "=0 | M partial (tour level) | M partial", "not yet a feature (serve_speed_tabpfn in progress)", "none", "no",
     "men's tour level only; ATP non-Slam per-point speeds 2025-26 need an owner decision", "medium: needed for the speed lead"),
    ("rally length", "rally", "rally <= 5 and <= 9 shots, long-rally share, quick serve and return points", "pair", SL, "",
     "BN", "SC", "sl3:rally5|off|w52", G + " " + NOTHING, "none", "yes", "", "low"),
    ("net play", "net", "net approaches per point and net points won", "pair", SL, "", "BN", "SC", "sl3:net_rate|off|w52",
     G + " " + NOTHING, "none", "yes", "", "low"),
    ("how points end", "point endings", "winners, errors, unforced share, winner/UE ratio, backhand UE share, forehand "
     "winner share", "pair", SL, "", "BN", "SC", "sl3:winner_rate|off|w52",
     E + " W winners per point (adjusted) onE 0.37 [0.12, 0.63]; " + NOTHING + "; planted edges rule out 0.25-0.5 mLL (men)",
     "none", "yes", "", "low"),
    ("placement and return depth", "placement", "T and wide serve shares, deep returns, returns in play", "pair", SL, "",
     "BN", "SC", "sl3:t_share|off|w52", G + " W serves out wide 0.08 tie; " + NOTHING, "none", "yes", "", "low"),
    ("pressure and after-loss excess", "clutch", "pressure serve, first serves in under pressure, consolidations, breaks "
     "back, serving for sets, points after a lost point", "pair", SL, "", "BN", "SC", "sl3:pressure_srv|off|w52",
     E + " pressure excess onM M 0.02 tie; W holds after breaking onE 0.37 [0.13, 0.61]", "none", "yes", "", "low"),
    ("big-point return skill (Slam point files)", "clutch", "importance-weighted minus plain return points won at earlier "
     "Slams, A - B (stored as halves per player)", "diff", "stage4_features: bigpoint_return|single; stage2_pbp_players",
     "fp__f08_clutch__f08_bigpt_a/_b", "BN", "SC", "s4:bigpoint_return|single",
     E + " onE M 0.091 [0.002, 0.180], coefficient -0.043; onM ties; 'big-point play is not a trait' (point_sequence)",
     "none", "yes", "f08_bigpt holds +-half the A - B value, not a true per-player value", "low"),
    ("resilience excess", "clutch", "consolidations and breaks back beyond the player's own rates, released by the clock",
     "pair", "f08_clutch.resilience_state", "fp__f08_clutch__f08_res_a/_b; fp__f08_clutch__f08_resn_a/_b", "BN", "PP",
     "store:fp__f08_clutch__f08_res_ab", "I-027 dropped by its gate (carry-over -0.072 / -0.011 <= 0.1)", "none", "no",
     "", "exclude: not a trait"),
    ("tiebreaks, deciding sets, sets and games won", "clutch", "Stage 4 forms of tb_won, deciding, sets_won, games_won, "
     "win, bp_over", "diff", "stage4_features", "", "BN", "SC", "s4:deciding|52 weeks",
     E + " tb_won 'reads as luck'; deciding sets 52w W 0.829 onE but onM M -0.039 (worse); men's bp_over constant",
     "none", "yes", "", "low"),
    ("momentum and streaks", "point sequence", "hold after breaking, break back, point dependence, game dispersion, set "
     "swings", "pair", "point_sequence/sequences.parquet (19.17M points, 13 sources)", "", "BD", "SC", "ps:both_ge20",
     "all ten fail against pure-luck replays (point_sequence, discovery <= 2021, replication 2022-24)", "none", "no",
     "", "exclude: closed"),
    ("finishing form carried into the next match", "point sequence", "late-match point performance in the previous match",
     "pair", "point_sequence", "", "BD", "SC", "ps:both_ge20",
     "[log-odds per SD, + = carries] discovery ties; replication +0.0109 [+0.0003, +0.0216]: at most ~0.2 mLL",
     "none", "no", "", "low: inconclusive, at most ~0.2 mLL"),
    ("within-set serve clustering (men)", "point sequence", "game-to-game serve dispersion", "pair", "point_sequence", "",
     "BD", "SC", "ps:both_ge20", "[r, + = more trait-like than random order] +0.055 [-0.004, +0.116]: fails the exact "
     "shuffle; +0.163 [+0.086, +0.235] at 100+ matches", "none", "no", "", "low: a variance input for totals"),
    ("tempo and pressure pace (women)", "point sequence", "seconds between points; pace on pressure points", "pair",
     "point_sequence", "", "BD", "SC", "ps:both_ge20", "a reliable style that ties given the model and the close "
     "(point_sequence)", "none", "no", "", "exclude: closed"),
    ("point-sequence serve and return state at full depth", "point sequence", "per-player serve/return point records "
     "from the unified table (median 182 men / 77 women earlier matches)", "pair", "point_sequence/sequences.parquet",
     "", "BD", "SC", "ps:both_ge20", "pre-match tests against the close detect ~1.2 mLL (80% power); a trait needs "
     "4.5-8 mLL per tour to show (point_sequence)", "none", "no", "mid-build when mapped; women thin before 2016", "low: under-powered against the close"),
    ("ball tracking, SlamTracker, WTA API win probability", "tracking", "Hawk-Eye trajectories, likelihood-to-win, "
     "distance run", "pair", "not decoded / thin", "", "NN", "SC", "=0 | M partial | partial",
     "never tested ('too thin to test')", "none", "no", "", "exclude: too thin"),
    ("rally edge x long matches", "rally", "a built product (rally_edge|x_long|w52)", "diff", "shot_level/stage2_features",
     "", "BN", "SC", "sl2:rally_edge|x_long|w52", G + " " + NOTHING, "none", "yes", "", "low"),
    ("post-match match anatomy", "post-match", "luck, tiebreak and break-point over-performance of the finished match",
     "diff", "predictability_diagnostic/stage2_matches", "", "XL", "LK", "=history only | history only | history only",
     "in-match, not pre-match: 'most of what looks like clutch play is what pure luck produces' (PD stage 2)", "none",
     "yes", "describes the match itself: only as lagged history", "exclude: post-match"),
]
