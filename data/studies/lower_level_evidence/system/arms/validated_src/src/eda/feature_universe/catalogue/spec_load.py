"""Universe rows: load, rest, layoffs, schedule and travel (own matches). Field order as spec_market."""
FAMILY = "load and schedule"
Z = "[z: + = declared direction]"
G = "[mLL: + = feature or arm better; tie = interval spans 0]"
E = "[onE/onM/onP: mLL added to surface Elo / the average close / calibrated Pinnacle, + = better]"
RUST = Z + " I-043 rust alone beyond the current best +4.05 model / +3.91 price (z1 +3.89, z2 +1.44); OOS gains +0.25 / +0.09 mLL, point estimates, + = lower log loss (feature_interactions)"
F20 = "f20_fatigue.prepare (the shared kernel; f10, f13, f16, f21, f22, f23, f28 hold copies)"
ROWS = [
    ("sets in the last 14 days", "load", "log(1 + sets in events started in the 14 days before, plus this event's rounds)",
     "diff", "stage4_features: sets_14d|single; per player perplayer_load_2013_2026", "m__sets_14d; pp__sets_14d_a/_b",
     "IM", "SC", "store:m__sets_14d", E + " onE M 1.63 [1.41, 1.84], W 1.87; onM 0.23 / 0.29 ties; onP M 0.19 tie (PD stage 4)",
     "none", "yes", "missing if a match in the window lacks a set total", "high: incumbent load"),
    ("surface matches this season (pair)", "surface switching", "log(1 + played matches on this surface earlier this "
     "season), A's and B's (2 of the 58)", "pair", "pieces: season_n_*",
     "m__surf_season_a; m__surf_season_b; pp__surf_season_n_a/_b", "IM", "SC", "store:m__surf_season_a",
     G + " season counts no odds M +2.11 [+0.99, +3.23], W +3.66; with odds ties (surface_elo_pieces)", "none", "yes", "",
     "high: incumbent"),
    ("days since the last match on this surface (pair)", "surface switching", "log(1 + days since the player's last match "
     "on this surface), capped 1,095 (2 of the 58)", "pair", "pieces: days_since_*",
     "m__surf_layoff_a; m__surf_layoff_b; pp__surf_days_since_a/_b", "IM", "SC", "store:m__surf_layoff_a",
     G + " layoff no odds +1.70 / +1.93; with odds ties (surface_elo_pieces)", "none", "yes", "", "high: incumbent"),
    ("first matches on the surface (surface_first, replaced)", "surface switching", "fewer than 3 matches on the surface "
     "this season, A - B", "diff", "surface_elo_pieces/frame.parquet", "alt__surface_first", "BN", "SC",
     "store:alt__surface_first", E + " onE M 1.45, W 1.30; onM ties; replaced 6 Oct by the switch pairs", "none", "yes",
     "superseded", "low: superseded"),
    ("days since the last match (any level)", "rest and layoffs", "best-estimate days since the player's previous played "
     "match", "pair", "history.long_table rest_days; " + F20,
     "pp__rest_days_a/_b; fp__f20_fatigue__bd_rest_a/_b; fp__f10_price_slopes__rest_a/_b; fp__f13_uncertainty__rest_a/_b; "
     "fp__f17_info__rest_a/_b", "BN", "SC", "store:pp__rest_days_ab",
     E + " Stage 4 days_since onE 0.809 / 0.900, onM ties (2013-26); the raw block of I-043: " + RUST, "A", "yes",
     "five copies of one quantity; Stage 4's days_since (A - B) was scored on windows with 2025-26",
     "high: raw block of the strongest near miss"),
    ("break length beyond the field's norm", "rest and layoffs", "U = log(1 + gap - E) at the latest return after a break "
     "of 6+ weeks; E = the field's walk-forward mean gap (tour, week, ranking band); and the break's raw length in days",
     "pair", "f26_impairment.prepare_inj; f26_impairment.layoffs (ret_gap)",
     "fp__f26_impairment__bdinj_U_a/_b; fp__f26_impairment__ret_gap_a/_b", "BN", "PP",
     "store:fp__f26_impairment__bdinj_U_ab", RUST, "A", "yes",
     "inside B-INJ, which was opened on 2025-26 (tie); off-season returns carry ~60% of the rust",
     "high: raw block of I-043"),
    ("matches since the return from a break", "rest and layoffs", "n = played matches since the latest 6-week return "
     "(0 at the return; missing if the player never returned from such a break)", "pair", "f26_impairment.layoffs (ret_n)",
     "fp__f26_impairment__ret_n_a/_b", "BN", "PP", "store:fp__f26_impairment__ret_n_ab", RUST, "A", "yes",
     "seen through I-043 (B-INJ was opened on 2025-26); the return is defined on the field's walk-forward norm (clock)",
     "high: raw block next_candidates names"),
    ("rust after a break (I-043's own-player state)", "rest and layoffs", "U exp(-n / 2): grows with the break, half "
     "weight after ~1.4 matches", "pair", "f26_impairment.prepare_inj", "fp__f26_impairment__bdinj_rust0_a/_b", "BN", "PP",
     "store:fp__f26_impairment__bdinj_rust0_ab", RUST + "; B-INJ on 2025-26: effect -0.27 [-0.64, +0.10] mLL tie (+ = better)",
     "A", "yes", "opened on 2025-26", "medium: prefer the raw blocks"),
    ("returning from injury flags", "rest and layoffs", "inj = retirement or walkover given just before the break; rinj = "
     "rust x inj; win = within 2 matches of a 56-day return", "pair", "f26_impairment.prepare_inj",
     "fp__f26_impairment__bdinj_inj_a/_b; fp__f26_impairment__bdinj_rinj_a/_b; fp__f26_impairment__bdinj_win_a/_b", "BN",
     "SC", "store:fp__f26_impairment__bdinj_inj_ab", Z + " I-044 +0.48 (exploratory member, non-zero in 1.2%)", "none",
     "yes", "rare", "low"),
    ("within-event serve decay", "rest and layoffs", "minus the shrunk slope of first-serve residuals over this event's "
     "and the previous event's matches", "pair", "f26_impairment.decay", "fp__f26_impairment__bdinj_dec_a/_b", "BN", "SC",
     "store:fp__f26_impairment__bdinj_dec_ab", Z + " I-045 +1.56 model / +1.60 price (exploratory member)", "C", "yes",
     "first-serve based: exposed to the 2025-26 TML fault", "low: test only on clean data"),
    ("matches already played at this event", "on-site", "on_n = played matches at this tournament id before this one "
     "(qualifying shares the id in 98%)", "pair", "f24_onsite.per_row_b11",
     "fp__f24_onsite__bd11_on_n_a/_b; fp__f17_info__bd11_on_n_a/_b", "BN", "SC", "store:fp__f24_onsite__bd11_on_n_ab",
     Z + " B11's On member (log1p on_n, A - B) +3.29 model / +3.03 price (z1 +2.63, z2 +1.99), descriptive", "A", "no",
     "sets_14d counts sets, not rounds here", "high: a main effect the 58 lack"),
    ("fatigue kernel (tau 3 days)", "load", "log(1 + decayed minutes of strictly earlier matches, every level); minutes "
     "imputed from points or games", "pair", F20,
     "fp__f20_fatigue__bd_fat_a/_b; fp__f10_price_slopes__bd_fat_a/_b; fp__f13_uncertainty__bd_fat_a/_b; "
     "fp__f16_repute__bd_fat_a/_b; fp__f21_constitution__bd9a_fat_a/_b; fp__f22_demand__bd9b_fat_a/_b; "
     "fp__f23_arrival__bd10_fat_a/_b; fp__f28_state__bdst_fat_a/_b", "BN", "PP", "store:fp__f20_fatigue__bd_fat_ab",
     Z + " B-LOAD (dFat, dOff) +0.63 (feature_interactions); " + E + " minutes_14d onE M 1.51, W 1.59", "none", "no",
     "eight copies; women's minutes imputed before 2016", "medium: minutes-based recency load"),
    ("imputed-load share", "load", "share of the kernel from imputed minutes (data-quality flag)", "pair", F20,
     "fp__f20_fatigue__bd_fatimp_a/_b; fp__f10_price_slopes__bd_fatimp_a/_b; fp__f13_uncertainty__bd_fatimp_a/_b; "
     "fp__f16_repute__bd_fatimp_a/_b; fp__f21_constitution__bd9a_imp_a/_b; fp__f22_demand__bd9b_imp_a/_b", "BN", "SC",
     "store:fp__f20_fatigue__bd_fatimp_ab", "a control, not a hypothesis", "none", "no", "", "low: missingness flag"),
    ("off-site load", "load", "the kernel minus its part at this event", "pair", F20,
     "fp__f20_fatigue__bd_off_a/_b; fp__f10_price_slopes__bd_off_a/_b; fp__f13_uncertainty__bd_off_a/_b; "
     "fp__f16_repute__bd_off_a/_b", "BN", "PP", "store:fp__f20_fatigue__bd_off_ab", Z + " B-LOAD member (block +0.63)",
     "none", "no", "", "low"),
    ("previous on-site match's extra sets", "load", "PrevX: (sets - minimum)/(maximum - minimum) of the previous match "
     "here within 3 days", "pair", F20, "fp__f20_fatigue__bd_prevx_a/_b", "BN", "SC",
     "store:fp__f20_fatigue__bd_prevx_ab", Z + " B-PREV -0.07", "none", "no", "missing after a retirement", "low: raw part of B-PREV, which tied"),
    ("past fatigue (14 days)", "load", "mean pre-match fatigue kernel over the player's own matches in the 14 days before",
     "pair", "f28_state", "fp__f28_state__bdst_pastfat_a/_b", "BN", "SC", "store:fp__f28_state__bdst_pastfat_ab",
     Z + " B-STATE +1.79 (z1 +0.87, z2 +1.93), failed the filter", "C", "no", "missing with no match in 14 days",
     "medium"),
    ("season odometer", "load", "log((season load + 300)/(the field's mean for tour, week, ranking band + 300)), "
     "walk-forward", "pair", "f21_constitution", "fp__f21_constitution__bd9a_odo_a/_b", "BN", "PP",
     "store:fp__f21_constitution__bd9a_odo_ab", Z + " I-061 inside B9a (block +1.48; z1 +0.10, z2 +2.52): 'the likeliest "
     "member'", "C", "no", "nothing in 2014-21; look for a change after 2021", "medium"),
    ("recovery trait", "load", "shrunk points-won residual in high- vs low-fatigue earlier matches", "pair",
     "f21_constitution", "fp__f21_constitution__bd9a_trait_a/_b", "BN", "SC",
     "store:fp__f21_constitution__bd9a_trait_ab", Z + " I-058 inside B9a (block +1.48)", "C", "no",
     "split-half reliability r 0.086", "low"),
    ("pace and minutes per point", "match demand", "opponent-adjusted seconds per point (R) and minutes per point", "pair",
     "f22_demand", "fp__f22_demand__bd9b_pace_a/_b; fp__f22_demand__bd9b_mpp_a/_b", "BN", "PP",
     "store:fp__f22_demand__bd9b_pace_ab", Z + " B9b -0.81; women's tempo 'a reliable style that adds nothing' "
     "(point_sequence)", "none", "no", "women have no minutes before 2016; bd9b_mpp is identical for A and B (a norm: context)", "low: raw part of B9b, which tied; women's tempo ties too"),
    ("deep run at the previous event", "arrival", "wins at the previous event, decayed by the gap (tau 2 days), and the "
     "run term", "pair", "f23_arrival.per_row_b10",
     "fp__f23_arrival__bd10_wprev_a/_b; fp__f23_arrival__bd10_decay_a/_b; fp__f23_arrival__bd10_run_a/_b", "BN", "SC",
     "store:fp__f23_arrival__bd10_run_ab", Z + " I-059 inside B10 (block +0.37)", "none", "no", "", "low"),
    ("travel between regions", "arrival", "1[the previous event's region differs]", "pair", "f23_arrival",
     "fp__f23_arrival__bd10_trav_a/_b", "BN", "SC", "store:fp__f23_arrival__bd10_trav_ab", Z + " inside B10 (+0.37)",
     "none", "no", "nation represented, not residence", "low"),
    ("title last week and first match here", "arrival", "won a final within 9 days; first match at this event; product",
     "pair", "f23_arrival", "fp__f23_arrival__bd10_title_a/_b; fp__f23_arrival__bd10_first_a/_b; "
     "fp__f23_arrival__bd10_t88_a/_b", "BN", "SC", "store:fp__f23_arrival__bd10_t88_ab", Z + " I-088 inside B10 (+0.37)",
     "none", "no", "", "low"),
    ("consecutive weeks played and weeks away", "arrival", "Wk = consecutive calendar weeks played; Away = weeks since "
     "the home region", "pair", "f23_arrival", "fp__f23_arrival__bd10_wk_a/_b; fp__f23_arrival__bd10_away_a/_b", "BN",
     "SC", "store:fp__f23_arrival__bd10_wk_ab", Z + " I-060 inside B10 (+0.37)", "none", "no", "", "low"),
    ("jet lag", "arrival", "continent-level time-zone shift since the last event, fading a day per zone", "pair",
     "f23_arrival", "fp__f23_arrival__bd10_jl0_a/_b; fp__f23_arrival__bd10_dzabs_a/_b", "BN", "SC",
     "store:fp__f23_arrival__bd10_jl0_ab", Z + " I-074 inside B10 (+0.37)", "none", "no", "a proxy offset table", "low"),
    ("fitness kernel (21 days)", "load", "the load kernel with tau 21 days (Fit)", "pair", "f23_arrival",
     "fp__f23_arrival__bd10_fit_a/_b", "BN", "PP", "store:fp__f23_arrival__bd10_fit_ab", "a control and sensitivity",
     "none", "no", "", "low"),
    ("novelty of conditions", "on-site", "surface switch + indoor switch + region change since the previous event",
     "pair", "f24_onsite", "fp__f24_onsite__bd11_nov_a/_b; fp__f24_onsite__bd11_sw_missing_a/_b; "
     "fp__f24_onsite__bd11_isw_missing_a/_b; fp__f24_onsite__bd11_cc_missing_a/_b; fp__f17_info__bd11_nov_a/_b; "
     "fp__f17_info__bd11_sw_missing_a/_b; fp__f17_info__bd11_isw_missing_a/_b; fp__f17_info__bd11_cc_missing_a/_b",
     "BN", "SC", "store:fp__f24_onsite__bd11_nov_ab", Z + " I-075 (On x novelty) +0.10, descriptive", "none", "no", "",
     "low: I-075 tied"),
    ("cold start", "on-site", "1[first match here] x 1[previous match on another surface or > 10 days before]", "pair",
     "f24_onsite", "fp__f24_onsite__bd11_cold_a/_b; fp__f17_info__bd11_cold_a/_b", "BN", "SC",
     "store:fp__f24_onsite__bd11_cold_ab", Z + " I-076 (rhythm vs cold start) +0.99, descriptive", "C", "no", "",
     "low: borderline"),
    ("indoor-switch state", "on-site", "exp(-m/2) after the player's indoor status switched", "pair", "f25_switch",
     "fp__f25_switch__bdsw_in_a/_b", "BN", "SC", "store:fp__f25_switch__bdsw_in_ab", "[Wald] inside B-SWITCH p 0.31",
     "none", "no", "unknown below the main tour", "low"),
    ("minutes and sets over 7 / 14 days", "load", "minutes_7d, minutes_14d, sets_7d (Stage 4, A - B)", "diff",
     "stage4_features: minutes_7d|single, minutes_14d|single, sets_7d|single", "", "BN", "SC", "s4:minutes_14d|single",
     E + " sets_7d onM M 0.30 [0.05, 0.54] (lag disputed: 0.03 vs 0.38); minutes_14d onE M 1.51", "none", "yes",
     "minutes-based 54-62% for women 2013-21", "low"),
    ("previous match length and early end", "load", "prev_minutes, prev_sets, last_early (own and opponent's early end)",
     "diff", "stage4_features: prev_minutes|single, prev_sets|single, last_early|single", "", "BN", "SC",
     "s4:last_early|single", E + " prev_sets M -0.030 (worse); last_early 0.225 / 0.321; onM ties", "none", "yes", "", "low"),
    ("matches played, 52 weeks and career", "load", "played_52w, played_career", "diff",
     "stage4_features: played_52w|single, played_career|single", "", "BN", "SC", "s4:played_52w|single",
     E + " 0.96 / 0.65; career -0.449 / -0.599: a warm-up artefact", "none", "yes", "", "low"),
    ("late decline and grinder", "load", "serve rate in sets 3+ minus sets 1-2; residual points share in long matches",
     "diff", "ufc_ideas/stageC_fatigue_part", "", "BN", "SC", "fat:grinder|52 weeks",
     E + " late_decline ties, onM W -0.19 [-0.35, -0.03]; grinder onM ties: 'Fatigue: no sign'", "none", "yes",
     "women 63% (grinder 52 weeks, 2013-21)", "exclude: closed"),
    ("recovery context (rest, retired losses)", "rest and layoffs", "pf_rest_diff, pf_retired_loss_*", "diff",
     "predictive_frontier/frontier_features", "", "BN", "SC", "pf:pf_rest_diff",
     G + " PF recovery context ties (both baselines)", "none", "yes", "", "low"),
    ("acute:chronic load ratio and team ties", "load", "ACWR (I-057) and team-tie load (I-062): f20 sensitivities", "pair",
     "f20_fatigue (sensitivities, not built as columns)", "", "BD", "SC", "store:fp__f20_fatigue__bd_fat_ab",
     "not screened", "none", "no", "", "low"),
    ("post-Slam letdown", "calendar", "reached a Slam quarter-final or better elsewhere, finishing at most 21 days before",
     "pair", "f19_motiv", "fp__f19_motiv__post_a/_b", "BN", "SC", "store:fp__f19_motiv__post_ab",
     Z + " I-090 inside B-MOTIV (+2.27; z1 +2.39, z2 +0.49)", "B", "no", "", "medium: test alone"),
]
