"""Universe rows: long-memory profiles (surface IOS, pooled IOS, deviations, Stage 4 and other aggregates). Field order as
spec_market."""
FAMILY = "long-memory profile"
Z = "[z: + = declared direction]"
G = "[mLL: + = feature or arm better; tie = interval spans 0]"
E = "[onE/onM: mLL added to surface Elo / the average close, + = better]"
S7 = ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved")
S8 = ("spw",) + S7
FAULT = ("men's Slam first-serve recording fault in 2025-26 (TML): 264 frozen-frame test matches exposed, RG 2026 "
         "qualifying (97 rows) has no clean source")
HOLDF = "hold-based: possibly touched by the same fault; women's service games missing 2013-14 (64% in 2015)"
IOS_EV = (G + " surface-IOS profile kept 6 Oct: with odds +0.01 [-0.10, +0.13] tie, no odds M +0.83 [+0.39, +1.27] "
          "(surface_ios, 2022-26); TabPFN's reliance on the IOS group, shuffle share M 0.62, W 0.74 (tabpfn_thinking)")


def _cav(s):
    return FAULT if s in ("first_in", "first_won", "second_won") else HOLDF if s in ("hold", "bp_saved") else ""


ROWS = []
for s in S7:
    ROWS += [
        (f"surface IOS offence: {s}", "surface IOS", f"surface-effective offence O + E on {s} (ridge joint solve, "
         "read at the earliest start), A - B", "diff", f"surface_ios/surface_features: srf_O_eff_{s}_a/_b",
         f"m__iosO_{s}; pp__ios_srfO_{s}_a/_b", "IM", "PP", f"store:m__iosO_{s}", IOS_EV, "none", "yes", _cav(s),
         "high: incumbent long-memory profile"),
        (f"surface IOS defence: {s}", "surface IOS", f"surface-effective defence D + F on {s} (suppression of the "
         "server's rate), A - B", "diff", f"surface_features: srf_D_eff_{s}_a/_b", f"m__iosD_{s}; pp__ios_srfD_{s}_a/_b",
         "IM", "PP", f"store:m__iosD_{s}", IOS_EV, "none", "yes", _cav(s), "high: incumbent long-memory profile"),
        (f"surface IOS matchup product: {s}", "surface IOS", "O_A(-D_B) - O_B(-D_A) on the effective values", "diff",
         "surface_features (both factors)", f"m__prod_{s}", "IM", "PP", f"store:m__prod_{s}", IOS_EV, "none", "yes",
         _cav(s), "high: incumbent (the model's only cross-player products)"),
    ]
ROWS.append(
    ("surface IOS on serve points won (O and D)", "surface IOS", "surface-effective offence and defence on spw, per player",
     "pair", "surface_features: srf_O_eff_spw_*, srf_D_eff_spw_*", "pp__ios_srfO_spw_a/_b; pp__ios_srfD_spw_a/_b", "BN", "PP",
     "store:pp__ios_srfO_spw_ab", Z + " I-008 (spw composed through the iid model) joint +0.67 (z1 +1.07, z2 -0.41) "
     "(feature_interactions)", "D", "no", "the 58 have no spw IOS; immune to the first/second-serve fault",
     "medium: the serve-point profile the 58 lack"))
for s in S8:
    ROWS.append(
        (f"pooled IOS (all surfaces): {s}", "pooled IOS", f"leak-proof pooled offence, defence and product on {s}", "diff",
         f"surface_features: cur_O_{s}_*, cur_D_{s}_*", f"alt__iosO_cur_{s}; alt__iosD_cur_{s}; alt__prod_cur_{s}; "
         f"pp__ios_curO_{s}_a/_b; pp__ios_curD_{s}_a/_b", "BN", "PP", f"store:alt__iosO_cur_{s}",
         G + " replaced by the surface profile 6 Oct (R1 vs base +0.01 tie); IOS (21) linear with odds -0.16 tie (match_timing)",
         "none", "yes" if s != "spw" else "no", "superseded" + ("" if s != "spw" else "; never a model input"),
         "low: superseded"))
KN = {"spw": "kn__KN-SDEV__x0; kn__KN-SDEV__x1", "hold": "kn__KN-SDEV__x2; kn__KN-SDEV__x3",
      "first_won": "kn__KN-SDEV__x4; kn__KN-SDEV__x5", "ace": "kn__KN-SDEV__x6; kn__KN-SDEV__x7"}
for s in S8:
    ROWS.append(
        (f"surface deviations: {s}", "surface IOS deviations", f"the player's serve (E) and return (F) deviation on this "
         f"surface for {s}, A - B", "diff", f"surface_features: srf_E_{s}_*, srf_F_{s}_*",
         f"alt__sdevO_{s}; alt__sdevD_{s}; pp__ios_srfE_{s}_a/_b; pp__ios_srfF_{s}_a/_b" + (f"; {KN[s]}" if s in KN else ""),
         "BN", "PP", f"store:alt__sdevO_{s}", "[Wald, two-sided] KN-SDEV (8 df) p 0.55, known null (feature_interactions); "
         + G + " R2 sdev vs base -0.06 tie (surface_ios)", "none", "yes", "already inside the surface-effective IOS",
         "low: a known null"))
ROWS += [
    ("surface IOS net shift (dnet_spw)", "surface IOS deviations", "the surface IOS study's P1 net shift on spw", "diff",
     "surface_ios/arms/snet1", "kn__KN-SNET", "BN", "PP", "store:kn__KN-SNET",
     "[z, two-sided] KN-SNET known null +0.49 (feature_interactions); " + G + " P1 vs its placebo -0.00 tie (surface_ios)",
     "none", "yes", "", "exclude: equal to its placebo"),
    ("short-memory IOS points matchup", "points matchup", "IOS on spw, half-life 4 weeks men / 13 women, through the iid "
     "model", "diff", "match_timing/leakproof_features: ios_short", "m__ios_points_short", "IM", "PP",
     "store:m__ios_points_short", E + " onE M 3.72, W 5.02; onM 0.13 / 0.01 (UFC stage B, leaking original)", "none",
     "yes", "", "high: incumbent"),
    ("52-week points matchup", "points matchup", "52-week serve vs return points won through the iid model", "diff",
     "stage4_features: mu_points|52 weeks", "m__points_52w", "IM", "SC", "store:m__points_52w",
     E + " onE M 1.55, W 1.59; onM ties; given TTT 1.13 / 0.71 (PD stage 4; rating_systems)", "none", "yes", "",
     "medium: incumbent, close to ios_points_short"),
]
for form, ev in (("career", "spw career onE M -0.189 [-0.373, -0.006] (worse): 'career averages do not help'"),
                 ("52 weeks", "tpw 52w onE M 1.334, W 1.39; onM ties"), ("decayed", "52-week half-life; onM ties"),
                 ("surface", "this surface only; several cells constant"),
                 ("adjusted", "'opponent-adjusted' career form onE -0.15 to 0.29")):
    ROWS.append(
        (f"Stage 4 box-score aggregates: {form}", "Stage 4 aggregates", f"21 statistics (spw ... bp_over), form '{form}', "
         "shrunk logit share, A - B", "diff", f"stage4_features: <stat>|{form}", "", "BN", "SC",
         f"s4:spw|{form}" if form != "decayed" else "s4:spw|decayed", E + " " + ev + " (PD stage 4)", "none", "yes",
         "duplicates the IOS and two-week profiles; men's bp_over is constant", "low: duplicates incumbents"))
ROWS += [
    ("Stage 4 matchups (points, games, break points, components)", "Stage 4 aggregates",
     "A's serve form vs B's return form through the iid model, 5 forms", "diff", "stage4_features: mu_*|<form>", "",
     "BN", "SC", "s4:mu_games|52 weeks", E + " mu_games W 1.337 with onM -0.094 [-0.169, -0.019] (worse); mu_bp W 0.275",
     "none", "yes", "", "low"),
    ("adjperf / adjdef, 52 weeks", "opponent-adjusted profiles", "the model's adjperf/adjdef over 52 weeks unweighted",
     "diff", "ufc_ideas/stageB_adj_features: adj*|52 weeks", "ad__*_52w", "BN", "SC", "store:ad__adjperf_tpw_52w",
     E + " tpw 52w onE 1.78 / 1.91; given odds spw M 0.20 tie (UFC stage B)", "none", "yes",
     "30 columns (15 statistics x adjperf/adjdef), A - B; each opponent-side mirror (adjdef_rpw = adjperf_spw, ...) "
     "is a copy, leaving 17 distinct; rebuildable per player (stageB_adj.parquet)", "low"),
    ("adjperf / adjdef, career", "opponent-adjusted profiles", "the same over the career", "diff",
     "stageB_adj_features: adj*|career", "", "BN", "SC", "adj:adjperf_tpw|career", E + " career onE -0.14 / -0.08",
     "none", "yes", "", "exclude: dominated"),
    ("adjperf decayed forms not in the model", "opponent-adjusted profiles",
     "two-week adjperf_spw, adjperf_rpw and the other adjdef statistics", "diff",
     "stageB_adj_features / stageD_profile_features: adj*|decayed", "ad__*_decayed", "BN", "SC",
     "store:ad__adjperf_spw_decayed",
     E + " adjperf by statistic onE spw 2.78 / 2.97, hold 1.82 / 2.48; W aces given odds 0.23 [0.02, 0.44]", "none", "yes",
     "30 columns, A - B; observed: 28 are exactly the model's own two-week form inputs or their opponent-side "
     "mirrors (adjperf_ace_decayed = m__form_ace, adjdef_first_won_decayed = m__form_rpw_first, ...); only the "
     "serve-points-won pair (adjperf_spw, adjdef_spw) is new",
     "medium: the two-week serve-points-won form, the one decayed form the model lacks"),
    ("splits by opponent strength", "opponent-adjusted profiles", "vs strong / weak, thirds, slope, wins over strong",
     "diff", "ufc_ideas/stageB_split_features", "", "BN", "SC", "split:vs_strong_tpw|52 weeks",
     E + " vs bottom third onM 0.27 [0.09, 0.44]; contrasts -0.46 to 0.13: 'gap is chance; do not reopen' (UFC)",
     "none", "yes", "", "exclude: closed"),
    ("surface statistic levels (ss_level)", "surface statistics", "decayed level of 12 statistics (365-day half-life)",
     "diff", "market_anchoring/surface_stat_features: ss_level_*", "", "BN", "SC", "ss:ss_level_ace",
     G + " level +0.020 tie anchored (market_anchoring)", "none", "yes", "repaired dated main-tour history only", "low"),
    ("surface statistic levels on this surface (ss_surf)", "surface statistics", "730-day surface level", "diff",
     "surface_stat_features: ss_surf_*", "", "BN", "SC", "ss:ss_surf_ace",
     G + " +0.02 tie anchored; no market +0.83 [+0.17, +1.49] (market_anchoring)", "none", "yes", "", "low"),
    ("surface statistic deviations (ss_dev)", "surface statistics", "surface level minus overall level", "diff",
     "surface_stat_features: ss_dev_*", "", "BN", "SC", "ss:ss_dev_ace", G + " -0.08 tie anchored (market_anchoring)",
     "none", "yes", "", "low"),
    ("own-expected form (pf_serve/return 28/182, momentum)", "predictive frontier", "decayed points won above the ratings' "
     "expectation", "diff", "predictive_frontier/frontier_features: pf_serve_*, pf_return_*", "", "BN", "SC",
     "pf:pf_serve_28", G + " vs the Elo combination M +1.549 [+0.824, +2.274]; vs Pinnacle + profile ties (predictive_frontier)",
     "none", "yes", "", "low"),
    ("reliability (evidence, history seen, instability)", "predictive frontier",
     "pf_box_seen_diff, pf_evidence_diff, pf_history_seen_diff, pf_instability_diff", "diff", "frontier_features", "",
     "BN", "SC", "pf:pf_evidence_diff", G + " vs Pinnacle + profile M +0.232 [-0.038, +0.502] tie; vs raw Pinnacle +0.864 "
     "[+0.048, +1.679] (secondary)", "none", "yes", "", "low"),
    ("reliability x strength products", "predictive frontier", "pf_*_unknown_elo, pf_uncertainty_elo/_sr, "
     "pf_instability_elo, pf_inactivity_elo", "diff", "frontier_features", "", "BN", "SC", "pf:pf_uncertainty_elo",
     "in the reliability family above", "none", "yes", "already interactions", "low"),
    ("surface correction (pf_surface_*)", "predictive frontier", "surface serve/return form and evidence", "diff",
     "frontier_features", "", "BN", "SC", "pf:pf_surface_serve", G + " vs Pinnacle + profile ties; anchored 2026 -0.46 tie",
     "none", "yes", "", "low"),
    ("this edition's speed x style (pf_event_*)", "predictive frontier", "this edition's earlier serve residuals x style "
     "or Elo", "context", "frontier_features: pf_event_*", "", "BN", "PN", "pf:pf_event_speed_style",
     G + " +0.062 / +0.096 ties (predictive_frontier)", "none", "yes",
     "a field statistic on a strictly-earlier-day clock, never probed; venue pace (I-072) is the leak-proof analogue",
     "exclude: unprobed; use venue pace"),
    ("last season's surface form", "surface switching", "wins above Elo's expectation on the surface last season, "
     "and its count", "pair", "pieces: prev_res_*, prev_n_*", "pp__surf_prev_res_a/_b; pp__surf_prev_n_a/_b", "BN", "SC",
     "store:pp__surf_prev_res_ab", G + " +0.17 [+0.00, +0.34] / -0.06 no odds: 'form does not inform' (SEP)", "none",
     "yes", "", "low"),
]
