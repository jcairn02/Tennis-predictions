"""Universe rows: the two-week opponent-adjusted profile and its long-memory level. Field order as spec_market."""
FAMILY = "two-week profile"
Z = "[z: + = declared direction]"
G = "[mLL: + = feature or arm better; tie = interval spans 0]"
FORM_EV = (G + " adjperf_tpw 2-week onE M 3.19 [2.85, 3.54], W 3.32; onM 0.14 / -0.07 (UFC stage B); profile16 vs the "
           "close M 0.51 tie, repaired +0.355 tie (FAA): 'the market already prices recent form'")
FAULT = "men's Slam first-serve recording fault in 2025-26 (TML): 264 frozen-frame test matches exposed"
SVG = "women's value missing where service games are (74% of 2013-21 matches)"
FORM = {"ace": "aces", "df": "double faults", "first_in": "first serves in", "first_won": "first-serve points won",
        "second_won": "second-serve points won", "hold": "service games held", "bp_saved": "break points saved",
        "bp_faced_pg": "break points faced per service game", "brk": "return games won (K3 160)",
        "bp_conv": "break points converted (K3 160)", "rpw_first": "return points won on the first serve (K3 160)",
        "rpw_second": "return points won on the second serve (K3 160)"}
CAV = {"first_in": FAULT, "first_won": FAULT, "second_won": FAULT, "rpw_first": FAULT + " (opponents' counts)",
       "rpw_second": FAULT + " (opponents' counts)", "hold": SVG, "bp_faced_pg": SVG, "brk": SVG}
DEF = {"ace": "aces conceded below the opponent's norm", "df": "double faults induced", "first_in": "first serves in "
       "induced", "bp_faced_pg": "break points forced per game"}
ROWS = []
for s, label in FORM.items():
    ROWS.append((f"two-week form: {label}", "adjperf", f"decayed (half-life 2 weeks) mean of per-match opponent-adjusted "
                 f"z on {s}, shrunk (K3 10 men / 20 women unless noted), A - B", "diff",
                 f"ufc_ideas/stageD_profile_features: adjperf_{s}|decayed; per player rebuilt (perplayer_form_2013_2026)",
                 f"m__form_{s}; pp__form_{s}_a/_b", "IM", "SC", f"store:m__form_{s}", FORM_EV, "none", "yes",
                 CAV.get(s, ""), "high: incumbent short-memory profile"))
for s, label in DEF.items():
    ROWS.append((f"two-week defence: {label}", "adjdef", f"decayed (2 weeks) mean of how far the player held opponents "
                 f"below their norm on {s} (K3 160), A - B", "diff", f"stageD_profile_features: adjdef_{s}|decayed",
                 f"m__formdef_{s}; pp__formdef_{s}_a/_b", "IM", "SC", f"store:m__formdef_{s}", FORM_EV, "none", "yes",
                 FAULT if s == "first_in" else SVG if s == "bp_faced_pg" else "", "high: incumbent short-memory profile"))
ROWS += [
    ("two-week total points won (adjperf_tpw_2w)", "adjperf", "opponent-adjusted total points won, decayed 2 weeks, "
     "shrunk (K3 10 / 20)", "diff", "stageD_features: adjperf_tpw|decayed", "m__adjperf_tpw_2w; pp__adjperf_tpw_2w_a/_b",
     "IM", "SC", "store:m__adjperf_tpw_2w", FORM_EV, "none", "yes", "", "high: incumbent current form"),
    ("52-week level of the points form", "form level", "l52 = sum z / (n + K3) over the last 364 days of box-score "
     "matches (I-033's level; I-031's l is released by the clock)", "pair",
     "f13_uncertainty.prepare_b6; f07_evidence_age (I-031)",
     "fp__f13_uncertainty__l52_a/_b; fp__f07_evidence_age__f07_ell_a/_b", "BN", "SC",
     "store:fp__f13_uncertainty__l52_ab", Z + " used by I-033 flux (in B6, oriented +1.13) and I-031 re-anchoring (in B7, "
     "+0.76; z1 -0.97, z2 +2.85)", "C", "no", "two builds of one idea (f07's on the clock)",
     "medium: the long level beside the short form lets a model form the gap itself"),
    ("form evidence and shrinkage", "form level", "s0 = decayed count of recent box-score matches, K3, r = s0/(s0 + K3) "
     "the form's shrinkage, and the rebuilt form used to check it", "pair", "f13_uncertainty; f07_evidence_age",
     "fp__f13_uncertainty__shr_a/_b; fp__f07_evidence_age__f07_s0_a/_b; fp__f07_evidence_age__f07_k3_a/_b; "
     "fp__f07_evidence_age__f07_form_rebuilt_a/_b", "BN", "SC", "store:fp__f13_uncertainty__shr_ab",
     Z + " inside B7 and B6 (blocks +0.76 and +1.13 oriented)", "D", "no",
     "f07_form_rebuilt is a check copy of adjperf_tpw_2w; f07_k3 is the tour constant (identical for A and B)", "low: reliability input"),
    ("fatigue-adjusted two-week form", "form level", "the two-week form read through recent fatigue (BOD-C1's mechanism), "
     "as a replacement of the raw form inputs", "diff", "build from f28_state (PastFat) and the form inputs", "", "BD", "SC",
     "store:fp__f28_state__bdst_pastfat_ab", Z + " B-STATE past fatigue +1.79 (z1 +0.87, z2 +1.93), failed the filter",
     "C", "no", "next_candidates' suggestion: replace, not add", "medium: a re-expression of incumbents"),
]
