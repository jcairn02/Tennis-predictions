"""Universe rows: level sums (A + B) as symmetric context: H-S2's 17, pair strength and pair serve dominance. Field
order as spec_market."""
FAMILY = "level sums"
Z = "[z: + = declared direction]"
S2 = (Z + " H-S2, the 17 sums together as TabPFN context: +1.73 (z1 +1.37, z2 +1.05; widened x 1.25), q 0.23 "
      "(feature_interactions)")
ROWS = [
    ("H-S2 levels arm (all 17 sums)", "H-S2", "both players' sums of 14 surface-IOS offence/defence inputs, overall Elo, "
     "age and sets in 14 days, as context beside the differences", "context",
     "src/eda/feature_interactions/features/levels.py", "lv__*", "BN", "PP", "store:lv__elo", S2, "C", "no",
     "the most direct 'built from scratch' test; spans the spw sums (98%)",
     "medium: repeat with fewer, chosen sums (spw sums, Elo)"),
]
for k, label in (("iosO", "offence"), ("iosD", "defence")):
    for s in ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved"):
        ROWS.append((f"level sum: surface IOS {label} of {s}", "H-S2", f"surface-IOS {label} of {s}, A + B (the model has "
                     "A - B)", "context", "levels.py (from the panel's per-player IOS)", f"lv__{k}_{s}", "BN", "PP",
                     f"store:lv__{k}_{s}", "inside the H-S2 arm; " + S2, "C", "no",
                     "first-serve sums exposed to the 2025-26 TML fault" if s in ("first_in", "first_won", "second_won")
                     else "", "low: one of 17; choose a few"))
ROWS += [
    ("pair strength: overall Elo sum", "pair strength", "R_A + R_B (A + B overall Elo); I-084's modulator is this "
     "standardised", "context", "levels.py; f10_price_slopes.prominence", "lv__elo", "BN", "SC", "store:lv__elo",
     Z + " I-084 (pair prominence x price) -2.98 model / -3.12 price, reversed (z1 -2.38, z2 -1.82); inside H-S2; "
     "[mLL: + = the arm with the Elo sum better; tie = interval spans 0] TabPFN 58 + Elo sum vs the current best "
     "2020-24 +0.17 [+0.07, +0.27]; one-shot 2025-26 -0.07 [-0.29, +0.16] tie leaning worse (pair_strength)",
     "A", "yes", "the favourite-longshot bias of weak pairs, carried by the price (pair_strength, 2014-24); its "
     "development gain sat in the weakest fifth of pairs, where 2025-26 lost (exploratory); 2025-26 is used",
     "low: tested on 2025-26 and not confirmed (pair_strength)"),
    ("pair age sum", "pair strength", "age_A + age_B", "context", "levels.py", "lv__age", "BN", "SC", "store:lv__age",
     "inside the H-S2 arm; " + S2, "C", "no", "", "low"),
    ("pair load sum", "pair strength", "sets in 14 days, A + B", "context", "levels.py", "lv__sets14", "BN", "SC",
     "store:lv__sets14", "inside the H-S2 arm; " + S2, "C", "no", "", "low"),
    ("pair serve dominance (spw sums)", "pair serve dominance", "m_pair = mu_spw + (O_A + O_B - D_A - D_B)/2 on spw: how "
     "serve-dominated the match is; kappa_pair is its leverage form", "context",
     "f02_leverage (kappa_pair); build from pp__ios_srfO_spw / pp__ios_srfD_spw", "fi__B-LEVER__f02_kappa_pair",
     "BN", "PP", "store:fi__B-LEVER__f02_kappa_pair", "[Wald] B-LEVER p 0.21 model / 0.24 price; S2's IOS sums span "
     "m_pair", "none", "no", "the stored column is kappa_pair (the leverage ratio), not the raw sum",
     "medium: the serve-dominance level the 58 lack"),
]
