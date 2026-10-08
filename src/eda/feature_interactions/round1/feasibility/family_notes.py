"""The feasibility auditor's notes per family (round 1), written into each family file by assemble.py."""
FAMILY_NOTES = {
    "01": "Every column is built from held inputs (surface IOS for serve points, Stage 3, the odds) and passes the full "
          "swap test. Two are close to what TabPFN can already form from an input and a context column: I-006 (augmented "
          "R² 0.99, essentially `ratings_iid` × best of five) and I-001 (0.85). That is not a G2 failure. I-007 reads results: "
          "it may run only inside the frozen screen, and its gating of I-001, I-003, I-010 and I-011 must be declared at M1.",
    "02": "The composition family is almost linear in the 58 inputs: z_C1 0.980, the games route 0.964, the noise-integrated "
          "version 0.970 (in family 03, I-015 0.995; I-012 0.954). As raw columns these fail novelty. The remedy is the "
          "originator's own: declare the remainder after a projection on the 58 inputs fitted without outcomes (2013–2018) "
          "and report its SD. I-011 (0.87) and I-013's squares pass. I-010's variance V must be fixed before M1 without "
          "reading results.",
    "03": "The IOS products pass (I-014 0.61, I-016 0.72). I-017 is a rotation of inputs (R² 1.00), not a column. I-018 is a "
          "field statistic (the clock, then probe.py). 60% of matches have an earlier meeting for I-019. I-020's speed history "
          "covers 70% / 68% and 95% / 84% of matches, but the men's serve-speed signal was already scored on 2022–2026.",
    "04": "Men's heights are near complete. Women's (93% in 2014–21, 64% in 2022–24) would pass G2, but only 1,624 of 4,199 "
          "women's test matches have both, so the originators' men-only claim stands. I-021 needs a new IOS solve with "
          "hand terms on the clock, then the probe. I-024's height × age fails novelty (0.958); height × Fat passes.",
    "05": "I-025 uses past results as inputs, which is allowed, but its β_f must not be fitted on the discovery outcomes "
          "in-sample: fix it walk-forward by season or from the iid model (M6). I-026 reads Sackmann's Slam point files, "
          "which end in 2024; its values go stale in the test years unless the point-sequence table extends them.",
    "06": "Built from Stage B's per-match z (each player's own matches; opponents' norms from their earlier matches): coverage "
          "96% or more, R² about 0.06. Residuals against IOS would be cross-player and need the clock and the probe. I-028 "
          "needs set scores parsed from the score strings (all held).",
    "07": "I-031 and I-033 use the rebuilt per-player profile and pass. I-032 fails novelty as built here (0.953) only because "
          "its statistic and evidence source are undeclared. Δ1's scaling constants (I-034) are walk-forward fits on results "
          "and belong inside the screen.",
    "08": "Every quote is held for 2014–2024 (average, best, Pinnacle, Bet365: 99.4% or more). Pinnacle stops in January 2026, "
          "so I-039 has 5,054 of 8,593 test matches. The current best's walk-forward forecasts now exist for every 2014–2024 "
          "match (M1), so I-040 and I-041 can be built. **No opening odds exist on disk before 2025** (tennis-data.co.uk is "
          "closing only; Polymarket covers 2025–26; the BetOnline lines in docs/research cover 2024–26 and are not held): "
          "the critique's C5 discovery move test cannot run.",
    "09": "Own history (status, gaps, Elo) covers every match. I-044 is non-zero on 1% of rows, a power question for the "
          "mathematical auditor. The point-sequence study tested related questions on 2014–2024 outcomes today (E1: medical "
          "events and the next match; B1: carry-over of finishing form). That look sits outside this study's ledger and "
          "concerns I-042, I-044 and I-045.",
    "10": "All five are built and pass. I-048 reweights the surface deviations whose arm (sdev) the surface-IOS study scored "
          "as a tie on 2022–26. I-050 is men only: no women's indoor flag exists for their earlier matches.",
    "11": "Load kernels on the match clock: minutes cover 84% / 61% (2014–21) and 88% / 82% (2022–24); women lack minutes in "
          "2014–15. Games-based kernels cover 100%. I-052 is deferred only for its unstated tuning target (M5): declare a "
          "price-free target (for example next-match serve residuals, 2013–2018) or fix τ in advance; I-053, I-054, I-055, "
          "I-058, I-064 and I-065 inherit that τ. I-060 needs event countries at every level and a continent map. "
          "`sets_14d` already counts team ties that have set totals.",
    "12": "Data pass. I-063 is deferred for the same reason as I-052 (κ, η, λ). Pace (seconds per point) covers men fully "
          "and women 59–72% in 2014–21. I-067's weather is not held.",
    "13": "All four are built; R² 0.14–0.40.",
    "14": "I-072 and I-073 are cross-player: build on the clock, then probe.py; I-073 is men only. I-074, I-075 and I-077 wait "
          "for tables not on disk (time zones, elevations). Indoor flags exist only for men's main-tour matches (Challenger 0.2%, ITF 0%), so I-073's indoor term learns from main-tour history only. The cartographer's I-076 question is answered: 98% of qualifiers' "
          "qualifying matches share the main draw's tournament id.",
    "15": "All built. N-based secondaries need walk-forward fits on results inside the screen.",
    "16": "I-085 lacks no-odds forecasts before 2019 (coverage 38% men, 32% women). I-086 needs a missingness rule (coverage 43–45%). I-089's "
          "points-to-defend secondary needs a hand-made table. The others pass with small informative subsets (1.4–2.3% "
          "non-zero).",
}
