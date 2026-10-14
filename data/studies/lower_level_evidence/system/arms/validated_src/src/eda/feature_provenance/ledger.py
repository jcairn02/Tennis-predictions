"""The provenance ledger of the current best model's 58 inputs and its stage-2 adjustment (feature-provenance study).

One row per input: what it is, where the idea came from, its fitted constants and the seasons whose outcomes chose
them, how it entered the model and which results were in view, whether pre-2022 evidence alone gives the same choice,
and two labels:

    constants  mechanism       set by a rule, an owner-approved convention or a normaliser fitted without outcomes
               fitted-clean    tuned on outcomes of 2013-2018 (or 2010-2018 norms) only
               fitted-exposed  a constant chosen after reading results of windows that contain 2022-2026
    choice     selected-exposed  the decision to include or represent it read 2022-2026 results (every input)

and an exposure group for the choice:

    A  pre-2022 evidence alone (or standard practice) gives the same choice
    B  a candidate on pre-2022 evidence, but its claimed role (the closing-line lead) rests on 2020+ seasons
    C  no pre-2022 case; entered on the owner's thesis and was kept on 2022-2026 by a criterion declared after the
       pre-registered test tied
    D  weak or absent before 2020; its value comes from 2020+ seasons

The records are compiled from the study reports and code cited in docs/studies/feature_provenance/README.md; nothing
is measured here. The script checks that the rows cover exactly the 58 names of the model's input list.

Writes data/studies/feature_provenance/provenance_58.csv and provenance_stage2.csv.
Run: ./python.sh src/eda/feature_provenance/ledger.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "studies" / "feature_provenance"
INPUTS = ROOT / "data" / "studies" / "surface_rating_race" / "model" / "model_inputs.json"

PROFILE = ["ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved", "bp_faced_pg", "brk", "bp_conv",
           "rpw_first", "rpw_second"]
FORMDEF = ["ace", "df", "first_in", "bp_faced_pg"]
IOS = ["ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved"]
CONSTANT_LABELS = {"mechanism", "fitted-clean", "fitted-exposed"}
GROUPS = {"A", "B", "C", "D"}

GROUP_RECORDS = [
    {"inputs": ["odds_logit"], "family": "market",
     "definition": "log-odds that A wins from the average of the books' closing odds, margin removed",
     "idea_origin": "the market anchor; fed as an input (not stacked) by the TabPFN-Thinking design of 2 Oct",
     "constants": "margin removal (rule)", "constants_outcomes": "none", "constants_label": "mechanism",
     "inclusion": "2 Oct TabPFN-Thinking design; input rather than stacking chosen from the free models' 2022-2026 "
                  "scores (+0.79 direct against +0.10 stacked)",
     "pre2022_same_choice": "yes (standard practice; no pre-2022 comparison reported)", "group": "A"},
    {"inputs": ["elo_overall", "elo_surf_offset"], "family": "ratings",
     "definition": "overall Elo's log-odds; the two players' surface offsets (own K, moving only on the surface)",
     "idea_origin": "owner's items 5-6 (6 Oct), motivated by a 2019-2026 market-anchoring reading; the offset "
                    "structure is the analyst's, built on 2010-2021 design years",
     "constants": "K men 600/(n+2)^0.6, women 600/(n+1)^0.6; offset K men 80/(n+10)^0.6, women 80/(n+20)^0.6",
     "constants_outcomes": "2013-2018", "constants_label": "fitted-clean",
     "inclusion": "owner, 6 Oct, on 2022-2026 without a price (+1.01 [+0.18, +1.84]) and the 2025-2026 24-hour "
                  "price (+0.78 [+0.03, +1.54]; clean event openers +0.88 [-0.38, +2.13], tie); close a tie",
     "pre2022_same_choice": "yes: Elo-only 2019-2021 men +4.50 [+2.06, +6.94]; linear 2016-2021 men +2.16, women "
                            "+1.44; TabPFN-Plus pilot 2019-2021 men +0.60 [+0.08, +1.12]. The 'useful before the "
                            "close' premise cannot be tested before 2025", "group": "A"},
    {"inputs": ["surf_season_a", "surf_season_b", "surf_layoff_a", "surf_layoff_b"], "family": "load and schedule",
     "definition": "log(1 + matches on this surface this season); log(1 + days since the last match on it), "
                   "capped at 3 years; each player",
     "idea_origin": "owner's item 6 (6 Oct)", "constants": "log1p, cap 1,095 days (rules)",
     "constants_outcomes": "none", "constants_label": "mechanism",
     "inclusion": "the offset-Elo swap of 6 Oct (as above)",
     "pre2022_same_choice": "yes: linear 2016-2021 without odds, season counts men +2.11, women +3.66; layoff "
                            "+1.70 / +1.93", "group": "A"},
    {"inputs": ["elo_games"], "family": "ratings", "definition": "games-weighted Elo difference",
     "idea_origin": "inherited legacy plan (Angelini and Candila's weighted Elo); Stage 4 starting list",
     "constants": "Stage 1 K and blend weight; scale = mean winner's games share", "constants_outcomes": "2013-2018 "
     "(K, weight); 2010-2018 values, no outcome fit (scale)", "constants_label": "fitted-clean",
     "inclusion": "Stage 4 top ten over 2013-2026 (men +1.82, women +2.38 over Elo) -> UFC Stage D -> the 53",
     "pre2022_same_choice": "yes: 2013-16 +2.34 / +3.31, 2017-19 +2.39 / +2.08, 2020-21 +1.16 / +1.06 (tie)",
     "group": "A"},
    {"inputs": ["ratings_iid"], "family": "ratings",
     "definition": "serve and return strength ratings turned into a win probability by the iid point model",
     "idea_origin": "Stage 3's suggestion; legacy plan's serve/return aggregates",
     "constants": "rating variances, drift, newcomer starts; serve-point mean", "constants_outcomes": "2013-2018 "
     "(per-serve-point log loss); 2010-2018 means", "constants_label": "fitted-clean",
     "inclusion": "Stage 4 (+3.61 / +4.58 over Elo) -> summary's carry-forward -> the 53",
     "pre2022_same_choice": "yes: better than Elo in every era", "group": "A"},
    {"inputs": ["adjperf_tpw_2w"], "family": "two-week profile",
     "definition": "total points won relative to what each opponent usually allows, two-week half-life",
     "idea_origin": "UFC adjperf, at the owner's request of 2 Oct",
     "constants": "h1/K1/tau/h3/K3 men 104/2/0/2 weeks/10, women inf/20/0/2 weeks/20 (grid extended twice)",
     "constants_outcomes": "2013-2018 (in-sample gain over Elo)", "constants_label": "fitted-clean",
     "inclusion": "Stage B's best adjperf row (+3.19 / +3.32 over Elo) -> Stage D -> the 53",
     "pre2022_same_choice": "yes: +2.98 / +4.37 over Elo before 2022", "group": "A"},
    {"inputs": ["ios_points_short"], "family": "long-memory profile",
     "definition": "IOS points matchup with a short memory, 4 weeks men and 13 weeks women",
     "idea_origin": "UFC IOS, at the owner's request of 2 Oct; short memories added as diagnostics",
     "constants": "kappa, tau (2013-2018); memory picked from three diagnostics added after the first all-season "
                  "rundown was read (stageB.md:340)",
     "constants_outcomes": "all seasons 2013-2026 for the memory (42% of men's, 69% of women's matches in 2022-2026)",
     "constants_label": "fitted-exposed",
     "inclusion": "Stage D 'everything' model -> feature-alpha audit ladder -> the 53",
     "pre2022_same_choice": "yes, the same memories (men 4 weeks +3.16 against 13 weeks +2.60; women 13 weeks +6.38 "
                            "against 4 weeks +6.01)", "group": "A"},
    {"inputs": ["points_52w"], "family": "long-memory profile", "definition": "points-won matchup over 52 weeks",
     "idea_origin": "Stage 4 starting list ('A's serve against B's return')",
     "constants": "52-week window (convention); shrinkage from Stage 3's statistic reliability",
     "constants_outcomes": "none (window); 2010-2018 statistics, no outcomes (shrinkage)",
     "constants_label": "mechanism",
     "inclusion": "Stage 4 top ten (+1.55 / +1.59 over Elo) -> summary -> Stage D -> the 53",
     "pre2022_same_choice": "yes: +1.04 / +2.48 over Elo before 2022", "group": "A"},
    {"inputs": [f"form_{s}" for s in PROFILE] + [f"formdef_{s}" for s in FORMDEF], "family": "two-week profile",
     "definition": "two-week opponent-adjusted form on twelve statistics (form_) and the defensive mirror on four "
                   "(formdef_)",
     "idea_origin": "owner's request of 2 Oct for offensive/defensive ratings of individual statistics; UFC "
                    "adjperf/adjdef; statistics from the Stage 4 list",
     "constants": "each statistic borrows serve- or return-points constants (h3 = 2 weeks; K3 10-160)",
     "constants_outcomes": "2013-2018 (in-sample gain over Elo)", "constants_label": "fitted-clean",
     "inclusion": "UFC Stage D's 'one lead against the odds': +0.51 [-0.05, +1.07] over 2013-2026, 0.92 in "
                  "2022-2026, 'positive in every season from 2020 on (and absent before)'; audit's 'main "
                  "closing-line lead'",
     "pre2022_same_choice": "as a candidate yes; as the closing-line lead no: pooled 2013-2021 about +0.25 over the "
                            "odds (tie); eras -0.07, -0.01, 2020-21 +1.49", "group": "B"},
    {"inputs": [f"ios{side}_{s}" for s in IOS for side in ("O", "D")] + [f"prod_{s}" for s in IOS],
     "family": "long-memory profile",
     "definition": "long-memory surface IOS offence and defence per statistic, and the matchup products",
     "idea_origin": "UFC IOS and products (owner's thesis, 2 Oct); the surface version from a pasted suggestion and "
                    "a bettor's advice, its premise read off TabPFN's 2022-2026 outputs",
     "constants": "memory/kappa/tau per statistic; surface penalty 10x or 30x kappa (30x at the grid edge for 5 of "
                  "16 cells)", "constants_outcomes": "2013-2018 (next-match statistic)",
     "constants_label": "fitted-clean",
     "inclusion": "into the 53 against a null linear result (Stage D -0.06, with products -0.21, ties), no rationale "
                  "recorded; into the 58 by the owner on 6 Oct: with the odds a tie (+0.01 [-0.10, +0.13]), a "
                  "no-odds criterion declared after that result (men +0.83 [+0.39, +1.27])",
     "pre2022_same_choice": "no linear case before 2022 (-0.25; with products -0.41; ties); 2019-2021 without odds "
                            "men +0.98 [+0.42, +1.54], run after the 2022-2026 result was seen", "group": "C"},
    {"inputs": ["sets_14d"], "family": "load and schedule", "definition": "sets played in the last 14 days",
     "idea_origin": "Stage 4 starting list (expected 'weak'); legacy plan",
     "constants": "14-day window (owner-approved plan, 1 Oct)", "constants_outcomes": "none",
     "constants_label": "mechanism", "inclusion": "Stage 4, third (+1.63 / +1.87 over Elo) -> the 53",
     "pre2022_same_choice": "yes: +1.54 / +1.72 over Elo before 2022", "group": "A"},
    {"inputs": ["age", "age_sq"], "family": "player background",
     "definition": "age and squared age around 25, A - B", "idea_origin": "Stage 4 starting list",
     "constants": "centred at 25 (rule)", "constants_outcomes": "none", "constants_label": "mechanism",
     "inclusion": "Stage 4: men +1.42 over Elo ('finding'), women +0.56 ('possible'); pooled into the 53",
     "pre2022_same_choice": "weak for men (+0.37; 2013-16 -1.10, worse than Elo alone), absent for women (+0.02, "
                            "tie); its value comes from 2020-21 (+4.19) and 2022-26 (+2.88)", "group": "D"},
    {"inputs": ["tour", "surface", "level", "indoor", "best_of", "round"], "family": "context",
     "definition": "match context (indoor is men only; best of from the pre-match rule)",
     "idea_origin": "TabPFN-Thinking design, 2 Oct", "constants": "codes (rules)", "constants_outcomes": "none",
     "constants_label": "mechanism", "inclusion": "the 2 Oct design",
     "pre2022_same_choice": "yes (descriptive context; TabPFN's reliance on it measured at 0.00)", "group": "A"},
]

STAGE2 = [
    {"component": "spd_L", "what": "men's 28-day first-serve-speed form difference / 1.9496 km/h, clipped at +-4",
     "constants": "filter tuned on speeds <= 2022 (next-match speed), checked on 2023; 28 days = the arg-max of a "
                  "result-free within-match target; normaliser from 2022-23 values; clip pre-registered",
     "constants_label": "mechanism",
     "choice": "the 28-day memory adopted on 8 Oct after two outcome runs on men's 2024-2026 (exploratory)",
     "choice_label": "selected-exposed"},
    {"component": "b-tilde", "what": "shrunk speed coefficient, b-hat * tau^2 / (tau^2 + SE^2), tau = 0.05",
     "constants": "tau pre-registered from point_sequence's published evidence; b-hat refitted each season on "
                  "2019..Y-1", "constants_label": "fitted-clean",
     "choice": "a pre-registered secondary adopted on 7 Oct when the primary (speed as a TabPFN column) tied; men "
               "2024-2026 +0.41 [+0.04, +0.78]", "choice_label": "selected-exposed"},
    {"component": "s_atp, s_wta", "what": "one calibration slope per tour on the base's log-odds",
     "constants": "refitted each season on 2019..Y-1 out-of-sample forecasts", "constants_label": "fitted-clean",
     "choice": "need found on 2022-2026 (surface-IOS audit); walk-forward refit added after the women's drift was "
               "seen on 2022-2026", "choice_label": "selected-exposed"},
    {"component": "TabPFN settings", "what": "8 estimators, softmax temperature 0.9, training 2013..Y-1",
     "constants": "the UFC project's production settings (tabpfn-client defaults); never varied in tennis",
     "constants_label": "mechanism", "choice": "fixed in the 2 Oct design", "choice_label": "mechanism"},
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    names = [i["name"] for i in json.loads(INPUTS.read_text())["inputs"]]
    rows = []
    for g in GROUP_RECORDS:
        assert g["constants_label"] in CONSTANT_LABELS and g["group"] in GROUPS, g["inputs"]
        for name in g["inputs"]:
            rows.append({"input": name, "family": g["family"], "group_size": len(g["inputs"]),
                         **{k: v for k, v in g.items() if k not in ("inputs", "family")},
                         "choice_label": "selected-exposed", "seen_2025_2026": "yes"})
    ledger = pd.DataFrame(rows)
    assert len(ledger) == len(names) == 58 and set(ledger["input"]) == set(names), "the ledger must cover the 58"
    ledger = ledger.set_index("input").loc[names].reset_index()
    ledger.to_csv(OUT / "provenance_58.csv", index=False)
    pd.DataFrame(STAGE2).to_csv(OUT / "provenance_stage2.csv", index=False)
    print(ledger.groupby(["group", "constants_label"]).size().to_string())
    print("inputs per exposure group:", ledger["group"].value_counts().sort_index().to_dict())
    return 0


if __name__ == "__main__":
    sys.exit(main())
