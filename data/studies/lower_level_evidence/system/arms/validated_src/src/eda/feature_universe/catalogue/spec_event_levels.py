"""Universe rows: the event-levels study (docs/studies/event_levels/), added 8 Oct 2026 at the owner's request. Kept as
its own family, after every other, so the earlier rows keep their ids (build_universe numbers rows in order). Field order
as spec_market."""
FAMILY = "event-levels study"
B = ("[beta: logistic coefficient beside a forecast's log-odds, slope fitted; + = the forecast under-rates the player "
     "with more lower-level history]")
G = "[mLL: + = feature or arm better; tie = interval spans 0]"
ROWS = [
    ("share of the last year's matches below the main tour", "history composition",
     "the player's share of their played matches in the 365 days before this one (earlier in Stage 0's order, tournament "
     "date within 365 days) that were below the main tour: tour or Slam qualifying, Challenger / WTA 125 (main draw or "
     "qualifying), ITF (main draw or qualifying); team events count in the total only; A - B, and A's and B's values; "
     "missing without a played match in the window",
     "diff", "event_levels/blend.history on the 30 Sep 2026 Stage 0, written by event_levels/universe_columns.py",
     "el__low_share_diff; el__low_share_a/_b", "BN", "SC", "store:el__low_share_diff",
     B + " the average close 2020-24 +0.18 [+0.09, +0.27] (where it was found), 2013-19 +0.09 [+0.02, +0.16] "
     "(replication), 2013-24 +0.13 [+0.07, +0.19]; Pinnacle +0.17 / +0.08 / +0.12; the current best (both stages) "
     "2020-24 +0.12 [+0.03, +0.21]; not match volume (log matches last year: -0.02, tie); beside last year's win share "
     "+0.18 [+0.11, +0.26] (win share -0.25 [-0.45, -0.05]); one SD (0.43) is about 1.4-1.9 points of win probability "
     "in an even match. " + G + " as a 59th TabPFN input against the current best (both stages), 2020-24: +0.06 "
     "[-0.10, +0.23] tie (C1); as a third walk-forward stage-2 term: +0.08 [-0.35, +0.50] tie (C2; 500s +0.94 "
     "[+0.19, +1.70], 1000s -0.76 [-1.58, +0.06]; its coefficient positive every season, 0.12-0.24) (event_levels)",
     "none", "no",
     "the lead was found on 2020-24 and C1/C2 were tested on the same seasons; the replication on 2013-19 is on the "
     "prices only (no model forecast before 2019); the prices' beta varies by level (500s +0.41, 1000s -0.02), by tour "
     "and era (women in 2013-19, men in 2020-24); ITF matches count here but carry no box score before 2025; at the "
     "Challengers Elo's version of the test points the other way; the window follows Stage 0's order (3 of 116,560 "
     "main-tour player rows of 2013-24 also count another event of the same week)",
     "medium: the close and Pinnacle under-rate it (replicated on 2013-19, unseen on 2025-26) but it tied as a TabPFN "
     "input and as a stage-2 term on 2020-24; test it beside last year's win share and as a stage-2 term"),
]
