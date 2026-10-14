"""Universe rows: market fields. Field order (every spec file): name, subfamily, definition, kind, source, store,
status, timing, coverage key, evidence, near-miss tier, seen 2025-26, caveats, priority. Codes in build_universe.py."""
FAMILY = "market"
Z = "[z: + = declared direction]"
G = "[mLL: + = feature or arm better; tie = interval spans 0]"
ROWS = [
    ("closing price, average of books (odds_logit)", "anchor",
     "log-odds that A wins from the average closing odds of tennis-data.co.uk, de-vigged by normalising 1/odds",
     "diff", "predictability_diagnostic/stage1_odds: p_avg_a (model frame in_odds_logit)", "m__odds_logit",
     "IM", "SC", "store:m__odds_logit",
     G + " current best (odds + 53 inputs) vs the close: M +1.57 [+0.82, +2.32], W +0.74 tie (tabpfn_thinking/leakproof, "
     "2022-26); a no-odds forecast stacked on the close loses -1.15 [-1.76, -0.55] (meta_stack): keep the price inside",
     "none", "yes", "a benchmark, not the betting venue (Polymarket); pairs with overround outside 1.00-1.20 dropped",
     "high: the anchor every from-scratch model needs"),
    ("Pinnacle minus average (C-1)", "book differences",
     "Pinnacle's de-vigged log-odds minus the average close's", "diff",
     "stage1_odds (pre-rebuild): ps_a, ps_b, avg_a, avg_b", "mk__ps_minus_avg", "MI", "SC", "store:mk__ps_minus_avg",
     Z + " C-1 descriptive beyond the current best: joint +2.98 model / +3.05 price (z1 +2.41, z2 +1.76) (feature_interactions); "
     + G + " the current best beats calibrated Pinnacle +1.06 [+0.27, +1.85] (2022-24), +0.21 tie (2014-21)",
     "A", "yes", "an artefact of the average close: helps a model benchmarked on the average, not one betting at Polymarket "
     "(as sharp as Pinnacle); venue comparisons with 2025-26 (sharp_benchmark, PD stage 1) already showed Pinnacle sharper; "
     "Pinnacle ends Jan 2026", "low: market-internal; at most an uncertainty input, never a direction"),
    ("Pinnacle close as the anchor", "anchor",
     "Pinnacle's de-vigged log-odds used instead of the average (= m__odds_logit + mk__ps_minus_avg exactly: the "
     "model's price is the proportionally de-vigged average close on all 63,737 rows)", "diff",
     "stage1_odds (pre-rebuild): p_ps_a", "m__odds_logit; mk__ps_minus_avg", "MI", "SC", "store:mk__ps_minus_avg",
     G + " average vs Pinnacle 0.7 [0.3, 1.1] worse (men, PD stage 1); recalibrated Pinnacle is the stronger benchmark (C-1)",
     "A", "yes", "a choice of anchor, not an added input; Pinnacle stops in Jan 2026 (later rows need the average)",
     "medium: decide the anchor before selecting inputs"),
    ("best price minus average", "book differences",
     "the best available price's de-vigged log-odds minus the average's (I-038's skew k)", "diff",
     "stage1_odds (pre-rebuild): max_a, max_b", "mk__max_minus_avg", "MI", "SC", "store:mk__max_minus_avg",
     Z + " inside B-ANCHOR (I-038): block joint -1.34 model / -1.39 price, against the declared direction",
     "C", "no", "whether OddsPortal's maximum includes exchanges is unknown", "low: market-internal"),
    ("Bet365 minus average", "book differences", "Bet365's de-vigged log-odds minus the average's", "diff",
     "stage1_odds (pre-rebuild): b365_a, b365_b", "mk__b365_minus_avg", "MI", "SC", "store:mk__b365_minus_avg",
     "no test found", "none", "no", "a soft book's deviation", "low: market-internal"),
    ("overround of the average close", "book differences", "1/avg_A + 1/avg_B - 1", "context",
     "stage1_odds (pre-rebuild): overround_avg", "mk__overround_avg", "MI", "SC", "store:mk__overround_avg",
     "no test found", "none", "no", "symmetric context; margins fell over the years", "low: market-internal"),
    ("cross-book dispersion", "book differences",
     "the best prices' implied sum minus the average's (more negative = books disagree more; I-037's a)", "context",
     "stage1_odds (pre-rebuild): max_a, max_b, avg_a, avg_b", "mk__dispersion", "MI", "SC", "store:mk__dispersion",
     Z + " inside B-ANCHOR (I-037 a x eta): block -1.34 model / -1.39 price, against the declared direction "
     "(feature_interactions); SEP's most-dispersed third +0.40 [+0.02, +0.78], post hoc", "C", "no",
     "symmetric: a model can use it as an uncertainty modulator of the price", "low: market-internal"),
    ("Expekt, Ladbrokes, Stan James closes", "other books", "the three books' closing odds",
     "diff", "tennis-data raw EXW/EXL, LBW/LBL, SJW/SJL (via stage1_odds td_file + td_row position)", "", "BD", "SC",
     "=M 0.67 / W 0.72 (EX) | 0 | 0", "not tested", "none", "no", "every book stops in 2018", "exclude: no data after 2018"),
    ("Betfair exchange close", "other books", "Betfair exchange odds (BFEW/BFEL)", "diff",
     "tennis-data raw BFEW/BFEL", "", "BD", "SC", "=0 | 0 | 2025-26 files only",
     G + " Betfair - Pinnacle -0.3 [-2.3, +1.6] tie (sharp_benchmark, 2025-26)", "none", "yes",
     "present only in the closed test seasons", "exclude: no training history"),
    ("opening or early prices, line movement", "price path",
     "price 24 h before or the move to the close", "diff",
     "Polymarket price paths 2025-26 (line_sharpening, sharp_benchmark); none in tennis-data", "", "NN", "SC",
     "=0 | 0 | partial (Polymarket)",
     G + " model fed the 24 h Polymarket price +0.332 [+0.091, +0.574] (flawed specification); price move toward the "
     "model beta +0.107 [+0.040, +0.174] (surface_rating_race); betting early vs close $0.00 per 100 (line_sharpening)",
     "none", "yes", "no history before 2025", "exclude: untrainable on 2013-24"),
    ("Polymarket price", "venue", "the venue's de-vigged pre-match price", "diff",
     "data/studies/public_data_dump polymarket_*; sharp_benchmark", "", "MI", "SC", "=0 | 0 | partial",
     G + " Polymarket - Pinnacle +0.3 [-4.9, +5.8] tie (sharp_benchmark)", "none", "yes",
     "the betting venue: benchmark and execution price, not a training input", "exclude: no history; use to bet"),
    ("Polymarket trade flow, order book, sharp positions", "venue", "flow and depth descriptors", "context",
     "polymarket_sharp_money (market descriptions only)", "", "NN", "SC", "=0 | 0 | partial",
     "measured only as market descriptions (polymarket_sharp_money)", "none", "yes", "2025-26 only",
     "exclude: no history"),
]
