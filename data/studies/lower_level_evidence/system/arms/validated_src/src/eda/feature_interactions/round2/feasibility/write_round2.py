"""Write data/studies/feature_interactions/round2/feasibility_round2.csv: the feasibility auditor's round-2 rulings on
the rebuttals of G2 verdicts and on the new ideas. Coverage (shares, men / women, 2014-2021 and 2022-2024) is from
r2_checks.json, r2_geo.json, r2_extra.json, r2_resid.json and round 1's metrics; test counts are 2025-2026 model rows.
Run: ./python.sh src/eda/feature_interactions/round2/feasibility/write_round2.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "feature_interactions" / "round2"
ALL, MEN = 8593, 4394
SAFE, BUILT, NEWX = "safe by construction", "inputs already on the leak-proof clock", "cross-player: leak-proof clock + probe.py"
MKT, WF = "market quotes (pre-match)", "walk-forward fits on strictly earlier seasons"
C100 = (1.0, 1.0, 1.0, 1.0)
# id, kind, ruling, tables, coverage (atp d, wta d, atp r, wta r), n_test, timing, probe, hours, verdict, reason
ROWS = [
    ("I-008", "rebuttal", "ACCEPT", "surface_features fi/fw/sw (or spw: R4) remainder on the 58", C100, ALL, BUILT, "no", 2, "pass",
     "remainder after a 2014-18 projection: SD 0.205 men, 0.086 women out of fit (z_spw 0.24 / 0.20)"),
    ("I-009", "rebuttal (finding 3)", "ACCEPT", "as I-008 (hold route)", C100, ALL, BUILT, "no", 2, "pass", "same remainder rule; R2 0.964 raw"),
    ("I-012", "rebuttal", "ACCEPT", "surface_features ace, spw; Stage 4 cell means", C100, ALL, BUILT, "no", 3, "pass",
     "declared g: R2 0.922 men, 0.929 women (mechanics part A); joint-fit gate is a statistic-level look"),
    ("I-015", "rebuttal (finding 3)", "ACCEPT", "as I-008", C100, ALL, BUILT, "no", 1, "pass", "remainder rule as I-008"),
    ("I-060", "rebuttal", "ACCEPT", "stage4 event country + ITF id codes; continent map (round0/body/counts)", (0.791, 0.821, 0.746, 0.881),
     ALL, SAFE, "no", 2, "pass", "all events of both players' last 42 days mapped: 79/82% (2014-21), 75/88% (2022-24); 1.8% of rows unmapped"),
    ("I-074", "rebuttal", "ACCEPT", "continent-level UTC offsets from the same map; the clock", (0.928, 0.946, 0.913, 0.950), ALL, SAFE, "no", 2,
     "pass", "defined for both at first-match rows 93/95% and 91/95%; trigger on 1.9%/1.3% (men/women, 2014-21) of rows"),
    ("I-075", "rebuttal", "ACCEPT", "surface switch; continent change; indoor switch (Stage 0 men, tennis-data Court)", (0.714, 0.570, 0.717, 0.570),
     ALL, SAFE, "no", 3, "pass", "every part defined for both at first-match rows: indoor is the binding part, men 71%, women 57% (priced matches only)"),
    ("I-085", "rebuttal", "ACCEPT", "F = c(elo_overall + elo_surf_offset), c from price SDs 2014-18", C100, ALL, SAFE, "no", 1, "pass",
     "fit-free: 100% from 2014"),
    ("I-086", "rebuttal", "ACCEPT", "previous match's own price; S11 rule", C100, ALL, MKT, "no", 1, "pass",
     "QF-on rows (15-17%) have both previous prices in 99.6-99.9%; zero elsewhere"),
    ("I-020", "auditor's correction", "REVISE pass -> kill (c)", "shot_level stage1 speeds in the last 3 matches", (0.097, 0.095, 0.584, 0.133),
     7608, SAFE, "no", 2, "kill", "round 1 measured any speed history; a recent change needs recent speeds: 10%/10% in 2014-21"),
    ("I-051 Off", "rebuttal (data only)", "ACCEPT", "off-site load kernel; minutes or games x median", C100, ALL, SAFE, "no", 2, "pass",
     "games-imputed load covers 100%; the column's status is the mathematical auditor's"),
    ("MEC-L1", "new", "", "surface_features spw O, D", C100, ALL, BUILT, "no", 1, "pass", "as a control or sensitivity only: R2 0.986 / 0.961 as a column"),
    ("MEC-K1", "new", "", "Stage 0 results (own order); lambda from surface_features at earlier pool matches (1 elsewhere)", C100, ALL,
     SAFE + "; weights from clock-built IOS", "recommended", 4, "pass", "updates follow each player's matches; probe the finished rating once"),
    ("MEC-K2", "new", "", "box scores of earlier meetings; surface_features at each meeting", C100, ALL, SAFE, "no", 3, "pass",
     "an earlier meeting in 61/58% (2014-21) and 59/57% (2022-24); 0 elsewhere"),
    ("MAT-L1", "new", "", "model frame in_round; odds", C100, ALL, MKT, "no", 0.5, "pass", "near-duplicate of LIT-1's L x eta"),
    ("MAT-K1", "new", "", "surface_features spw (an arm)", C100, ALL, BUILT, "no", 1, "pass", "a TabPFN arm, no new column"),
    ("MAT-K2", "new", "", "58 inputs only (boosting R2 for S columns)", C100, ALL, "result-free (features only)", "no", 2, "pass", "a novelty rule"),
    ("MAT-R1", "new", "", "Stage 0 box scores by event (all levels with boxes)", C100, ALL, NEWX, "yes", 8, "pass",
     "an event-level field statistic: usable from the event's lf + 1, the venue prior for later rounds"),
    ("MAT-R2", "new", "", "Stage 0 source, tml_link (counts)", C100, ALL, "counts only", "no", 2, "pass",
     "women 0 exposed test matches; men 264 (frozen frame), 144 after the rebuild"),
    ("LIT-1", "new", "", "model frame in_round, level; Stage 0 draws", C100, ALL, MKT, "no", 0.5, "pass", "L on 53%, HP on 22% of rows"),
    ("LIT-2", "new", "", "fame (titles, Slam QF) built in round 1; eta", C100, ALL, SAFE, "no", 0.5, "pass", ""),
    ("C-1", "new", "", "stage1_odds ps_a/b", (0.996, 0.994, 0.997, 0.995), 5054, MKT, "no", 0.5, "pass",
     "test only 5,054 of 8,593 (Pinnacle ends Jan 2026); Betfair exists only in 2025-26"),
    ("C-2", "new", "", "Stage 0 rank; F as I-085", (0.997, 0.997, 0.998, 0.995), ALL, SAFE, "no", 1, "pass", ""),
    ("INFO-1", "new", "", "rest_min (clock); previous match box score; IOS at its es", C100, ALL, SAFE, "recommended", 4, "pass",
     "u buildable for 95/83% (2014-21) of blind-spot players; prevalence shifts: women 46% (2014-18) to 1% (2025)"),
    ("INFO-2", "new", "", "Stage 0 entry, qualifying box scores; onsite_n, rest", C100, ALL, SAFE, "no", 3, "pass",
     "subgroup 12.6/12.6% (2014-21); the qualifier's on-site box score in 87/85% (2014-21), 100% (2022-24)"),
    ("BOD-L1", "new", "", "Stage 0 previous on-site match (sets, best_of, status); clock", C100, ALL, SAFE, "no", 1, "pass",
     "non-zero where a previous on-site match within 3 days exists (either player 67-69%)"),
    ("BOD-L2", "new", "", "Stage 0 age; eta", C100, ALL, SAFE, "no", 0.5, "pass", ""),
    ("BOD-C1", "new", "", "own Fat kernel (games-imputed minutes) over the last 14 days", (0.817, 0.790, 0.841, 0.804), ALL, SAFE, "no", 2,
     "pass", "both played in the last 14 days 79-84%"),
    ("BOD-C2", "new", "", "rest days (own sequence); eta", C100, ALL, SAFE, "no", 0.5, "pass", ""),
]


def main() -> int:
    cols = ["id", "kind", "ruling", "tables_columns", "cov_disc_atp", "cov_disc_wta", "cov_rep_atp", "cov_rep_wta",
            "n_test_2025_2026", "timing_class", "probe_needed", "build_hours", "verdict", "reason"]
    rows = [(i, k, r, t, *c, n, tm, pr, h, v, why) for i, k, r, t, c, n, tm, pr, h, v, why in ROWS]
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=cols).to_csv(OUT / "feasibility_round2.csv", index=False)
    print(f"{len(rows)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
