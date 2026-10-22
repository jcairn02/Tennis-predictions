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
    # re-filed 14 Oct 2026 at the owner's request ("Add an input to the candidate-feature list saying how much data stands
    # behind each player's recent form"): the fe__ columns, the model's own weights, are the current build; the fp__
    # columns are the 7 Oct builds, kept for B6 and B7. The admission card is in the README, section 9
    ("form evidence and shrinkage", "form level", "how much box-score evidence stands behind each player's two-week "
     "form, as the current best model weighs it (fe__, 14 Oct 2026): sw = the decayed count of the player's earlier "
     "box-score matches, Stage B's step-3 weight sum for total points won (half-life 2 weeks, Stage B's time rule; the "
     "level layer's weights for men, ITF box scores 0; 0 without one); r = sw/(sw + K3), the share of the raw two-week "
     "mean the form keeps (K3 10 men, 20 women); r_diff = r_a - r_b. The 7 Oct builds: s0 (the same count without the "
     "layer, on the 30 Sep tables), shr (f13's own W/(W + K3)), K3 and the rebuilt form used to check them", "pair",
     "feature_universe/form_evidence.py: stageB_adjperf step 3 through level_layer.forms_step3 on template_2026-10-13's "
     "build tree (form_evidence/store_columns.parquet; the instance's own 67,226 matches in "
     "form_evidence/template_2026-10-13.parquet); 7 Oct builds: f13_uncertainty; f07_evidence_age",
     "fe__sw_a/_b; fe__r_a/_b; fe__r_diff; fp__f13_uncertainty__shr_a/_b; fp__f07_evidence_age__f07_s0_a/_b; "
     "fp__f07_evidence_age__f07_k3_a/_b; fp__f07_evidence_age__f07_form_rebuilt_a/_b", "BN", "SC", "store:fe__sw_ab",
     Z + " the 7 Oct builds inside B7 and B6 (blocks +0.76 and +1.13 oriented, 2014-24, as parts of I-031 and I-033, "
     "never as an input); fe__: no result read (14 Oct 2026)", "D", "no",
     "fe__ is the current build (14 Oct 2026): with sw it rebuilds the model's adjperf_tpw_2w bit for bit on all 67,226 "
     "frame matches; select it, not the fp__ 7 Oct builds (corr 0.98: no layer, older tables); store values missing for "
     "111 WTA 2026 matches that today's tables hold with other player ids (71) or no longer hold (40); sw's level moves "
     "with box-score "
     "coverage: women's 2015 lacks lower-level box scores (mean 2.05, other seasons 2.7-3.5), women's ITF box scores "
     "are 3.8% (2025) and 2.7% (2026) of sw, about 0 before (the layer leaves women untouched), men's lower-level box "
     "scores weigh 0.49-0.90 on average (ITF 0); the other 16 "
     "forms' sw differ: men's corr 0.98-1.00 with tpw's (the layer weighs each statistic), women's service-game forms "
     "(hold, break points faced, return games) 0.70 in 2013-21, missing on 24% of the player-rows where tpw's exists; "
     "at bet time the daily engine computes sw in step 3 but does not output it; f07_form_rebuilt is a check copy of "
     "adjperf_tpw_2w; f07_k3 is the tour constant (identical for A and B)",
     "medium: admitted (14 Oct 2026, no result read); the evidence beside the short form lets a model weigh it, as "
     "U-125's level lets it form the gap"),
    ("fatigue-adjusted two-week form", "form level", "the two-week form read through recent fatigue (BOD-C1's mechanism), "
     "as a replacement of the raw form inputs", "diff", "build from f28_state (PastFat) and the form inputs", "", "BD", "SC",
     "store:fp__f28_state__bdst_pastfat_ab", Z + " B-STATE past fatigue +1.79 (z1 +0.87, z2 +1.93), failed the filter",
     "C", "no", "next_candidates' suggestion: replace, not add", "medium: a re-expression of incumbents"),
]
