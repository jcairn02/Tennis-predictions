"""Write data/studies/feature_interactions/inventory.csv: one row per feature or raw field of the data map (round 0).

Rows:
  * the 58 model inputs (registry.MODEL_INPUTS), coverage from coverage_all.csv (table model_frame);
  * the raw fields (registry.RAW_FIELDS), coverage from coverage_all.csv;
  * every column of the built feature tables (coverage.FEATURE_TABLES), with family, per-player availability, kind and
    timing class from the table rules below (TABLE_RULES; column overrides in COLUMN_RULES);
  * the shot-level per-player statistics with real-data coverage (coverage_shot_sides.csv).
Coverage = share of the model population's matches with the value (both players for per-player fields), 2013-2021 and
2022-2024, per tour. Run coverage.py and shot_sides.py first.
Run: ./python.sh src/eda/feature_interactions/inventory/build_inventory.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions.inventory import registry as R  # noqa: E402

INV = ROOT / "data" / "studies" / "feature_interactions" / "inventory"
OUT = ROOT / "data" / "studies" / "feature_interactions" / "inventory.csv"
COLS = ["name", "family", "path", "columns", "per_player_available", "kind", "timing_class",
        "coverage_2013_2021_atp", "coverage_2013_2021_wta", "coverage_2022_2024_atp", "coverage_2022_2024_wta",
        "in_model", "notes"]
LEAK = "LEAKING per CLAUDE.md (do not use as is)"
OWN = R.SAFE
CLOCK_OK = "solved together: built on the leak-proof clock"
POST = "post-match (describes the match itself: history only, never a pre-match input of the same match)"
FIELD = "field statistic (combines other players' results) on a strictly-earlier-day clock, not timing.parquet: unprobed"
SOS_UNVERIFIED = ("own-sequence by the code (opponents' pre-match ratings), but built by stageC_sos.py, which the "
                  "2026-10-05 decision marks as leaking: run match_timing/probe.py before use")

# table label (coverage.py) -> (family, path, per_player, kind, timing, notes)
TABLE_RULES = {
    "stage4_features": ("Stage 4 history aggregates", "data/studies/predictability_diagnostic/stage4_features.parquet",
                        "no: A - B (or logit P(A)) only; per row in stage4_features.form_value() val (A rows even, B "
                        "odd) and single_features() locals", "diff", OWN,
                        "1 Oct 2026, pre-repair Stage 0 and code; <stat>|<form>: career, 52 weeks, decayed (52-week "
                        "half-life), surface, adjusted (opponent's Stage 3 rating); constants frozen 2010-2018"),
    "stage1_baselines": ("Stage 1 Elo and baselines", "data/studies/predictability_diagnostic/stage1_baselines.parquet",
                         "yes for elo_*_a/_b, elo_surf_*_a/_b and the counts", "per player / probability", OWN,
                         "elo_surf_* is surface-ONLY Elo (starts at 1500); p_elo_surf_ret is the old 70/30 blend"),
    "stage3_ratings": ("Stage 3 serve/return ratings", "data/studies/predictability_diagnostic/stage3_ratings.parquet",
                       "yes (_a/_b columns)", "per player", OWN,
                       "ingredients of ratings_iid; p_serve_a/b are matchup rates, not levels; `updates` is post-match"),
    "audit4_lag_features": ("audit diagnostics (built vs lagged)",
                            "data/studies/predictability_diagnostic/audit4/lag_features.parquet",
                            "no: A - B only", "diff", OWN, "audit copies (#built / #lag) of Stage 4 inputs"),
    "ufc_stageA_bt": ("Bradley-Terry", "data/studies/ufc_ideas/stageA_bt.parquet", "yes (_a/_b)", "per player", LEAK,
                      "batch fits: leak (decision 2026-10-05); rebuild on the clock before any use"),
    "ufc_stageA_mesr": ("MESR (market-implied ratings)", "data/studies/ufc_ideas/stageA_mesr.parquet", "yes (_a/_b)",
                        "per player", LEAK, "batch fits on odds: leak (decision 2026-10-05)"),
    "ufc_stageA_features": ("UFC-ideas stage A inputs", "data/studies/ufc_ideas/stageA_features.parquet",
                            "no: A - B only", "diff", OWN, "bt/mesr columns leak; the rest are Stage 4 copies"),
    "ufc_stageB_adj_features": ("adjperf/adjdef profiles (52 weeks, decayed, career)",
                                "data/studies/ufc_ideas/stageB_adj_features.parquet",
                                "no on disk; rebuildable per player from stageB_adj.parquet z's (see perplayer_form.py)",
                                "diff", OWN, "decayed forms = the model's form_*; 52 weeks and career forms not in model"),
    "ufc_stageB_ios": ("IOS weekly (per player)", "data/studies/ufc_ideas/stageB_ios.parquet", "yes (_a/_b)",
                       "per player", LEAK, "weekly solver superseded by match_timing/ios_time.run_timed; leak-proof "
                       "per-player equivalents: surface_ios/surface_features cur_O_<s>_a/_b, cur_D_<s>_a/_b"),
    "ufc_stageB_ios_features": ("IOS weekly (differences)", "data/studies/ufc_ideas/stageB_ios_features.parquet",
                                "no: A - B only (per player in stageB_ios.parquet)", "diff", LEAK, "weekly solver"),
    "ufc_stageB_split_features": ("splits by opponent strength", "data/studies/ufc_ideas/stageB_split_features.parquet",
                                  "no: A - B only; per player in stageB_split.split_features() res['a'], res['b']",
                                  "diff", OWN, "strong = opponent's pre-match surface-only Elo above the 2010-18 "
                                  "main-tour median; strong_gap_x_strong_opp is a cross-player product"),
    "ufc_stageB_features": ("UFC-ideas stage B inputs (union)", "data/studies/ufc_ideas/stageB_features.parquet",
                            "no: A - B only", "diff", OWN, "its ios_* columns are the weekly (leaking) IOS"),
    "ufc_stageC_features": ("UFC-ideas stage C inputs (union)", "data/studies/ufc_ideas/stageC_features.parquet",
                            "no: A - B only", "diff", OWN,
                            "revalue* leak; sos_*/over_elo* see their own rows; elo_surface|single here is the BLEND"),
    "ufc_stageC_fatigue_part": ("fatigue and grinder (already interactions)",
                                "data/studies/ufc_ideas/stageC_fatigue_part.parquet",
                                "no: A - B only; per player in stageC_fatigue.build() locals (trait, sets14, min14, v)",
                                "diff", OWN, "late_decline from Slam point-by-point (sets 3+ vs 1-2); grinder from "
                                "minutes per set; *_x_bo5 men only; minutes holes (women 2013-15)"),
    "ufc_stageC_sos_part": ("strength of schedule and revaluation", "data/studies/ufc_ideas/stageC_sos_part.parquet",
                            "no: A - B only; per row in stageC_sos.sos_value()/revalue_value()", "diff", SOS_UNVERIFIED,
                            "mean of opponents' pre-match Elo over 52 weeks, shrunk; revalue* columns leak"),
    "ufc_stageD_features": ("UFC-ideas stage D shortlist", "data/studies/ufc_ideas/stageD_features.parquet",
                            "no: A - B only", "diff", OWN, "contains bt/mesr/revalue/sos (leaking) and weekly IOS"),
    "ufc_stageD_profile_features": ("UFC-ideas stage D profile", "data/studies/ufc_ideas/stageD_profile_features.parquet",
                                    "no: A - B only", "diff", OWN,
                                    "source of the model's form_*/formdef_*; its ios_*/prod_* are the weekly IOS"),
    "rating_systems_stageA_ratings": ("Glicko, TrueSkill, TTT (rating systems study)",
                                      "data/studies/rating_systems/stageA_ratings.parquet",
                                      "yes for glicko2m/trueskill/glicko_cs mu/u/vol _a/_b; else probability",
                                      "probability / per player", OWN, "p_ttt / p_ttt_overall: ttt_pass LEAKS"),
    "rating_systems_stageA_ttt_hold": ("TTT variant (hold)", "data/studies/rating_systems/stageA_ttt_hold.parquet",
                                       "no: probability only", "probability", LEAK, "TTT smoothed on the weekly clock"),
    "rating_systems_stageB_features": ("rating systems study frame", "data/studies/rating_systems/stageB_features.parquet",
                                       "no: A - B only (n_a/n_b, glicko2m_u_a/_b per player)", "diff", OWN,
                                       "p_ttt/ttt|single/p_ttt_hold leak"),
    "match_timing_ttt_timed(pre-rebuild)": ("TTT leak-proof", "data/studies/match_timing/ttt_timed.parquet",
                                            "no: probability only (per-player state in ttt_offset.parquet)",
                                            "probability", CLOCK_OK, "rebuilt 17:35 6 Oct; pre-rebuild copy used here"),
    "match_timing_leakproof_features(pre-rebuild)": ("leak-proof copies of the model inputs",
                                                     "data/studies/match_timing/leakproof_features.parquet",
                                                     "no: A - B only", "diff", OWN,
                                                     "IOS columns on the clock; per-player part rebuilt on repaired data"),
    "surface_rating_race_ttt_offset": ("TTT offset (per player)", "data/studies/surface_rating_race/ttt_offset.parquet",
                                       "yes (_a/_b)", "per player", CLOCK_OK, "mu, s2, off, so2, n, ns"),
    "surface_elo_pieces_pieces": ("Elo pieces and surface switching", "data/studies/surface_elo_pieces/pieces.parquet",
                                  "yes (_a/_b)", "per player", OWN, "R, N, S, NS, XA, D, DG, season_n, days_since, prev_n, prev_res"),
    "surface_ios_surface_features": ("surface IOS (per player)", "data/studies/surface_ios/surface_features.parquet",
                                     "yes (_a/_b)", "per player", CLOCK_OK,
                                     "cur_* pooled IOS; srf_O/D (all-surface), srf_E/F (surface deviation), srf_*_eff"),
    "surface_ios_subgroups": ("surface IOS subgroups", "data/studies/surface_ios/subgroups.parquet", "yes (_a/_b)",
                              "per player", OWN, ""),
    "market_anchoring_surface_stat_features": ("surface statistic levels and deviations",
                                               "data/studies/market_anchoring/surface_stat_features.parquet",
                                               "no: A - B only; per player in surface_stats.features() level/surf/dev "
                                               "arrays (A rows 0::2, B rows 1::2)", "diff", OWN,
                                               "no opponent adjustment; history = repaired dated main-tour main draws "
                                               "only (no qualifying/Challenger/ITF; ATP 2018 mostly missing)"),
    "predictive_frontier_frontier_features": ("predictive frontier", "data/studies/predictive_frontier/frontier_features.parquet",
                                              "no: A - B only; per player inside features.build_features() arrays",
                                              "diff", OWN, "several are symmetric x signed products (pf_*_elo, "
                                              "pf_uncertainty_sr, pf_event_*): already interactions"),
    "shot_level_stage2_features": ("shot level (differences)", "data/studies/shot_level/stage2_features.parquet",
                                   "no: A - B only (per player in stage3_sides.parquet)", "diff", OWN,
                                   "off/def/adj x career/dec2 (2-week)/w52; empirical-Bayes K per tour"),
    "shot_level_stage3_sides": ("shot level (per player)", "data/studies/shot_level/stage3_sides.parquet",
                                "yes (A|... / B|... columns; |has flags real data)", "per player", OWN,
                                "values are filled with a prior where a player has no data: use the |has flags"),
    "stage2_matches(post-match)": ("Stage 2 match anatomy", "data/studies/predictability_diagnostic/stage2_matches.parquet",
                                   "some _a/_b", "post-match", POST, "luck, tiebreaks over expectation, etc. of the match"),
}
COLUMN_RULES = [  # (table regex, column regex, overrides), applied in order
    (r"rating_systems_stageA_ratings|rating_systems_stageB_features", r"ttt", {"timing_class": LEAK}),
    (r"rating_systems_stageB_features", r"^ios_short", {"timing_class": LEAK, "notes": "weekly IOS"}),
    (r"ufc_stageA_features|ufc_stageD_features", r"^(bt|p_bt|mesr|p_mesr|mesr_minus)", {"timing_class": LEAK}),
    (r"ufc_stage[BD]", r"^(ios_|prod_)", {"timing_class": LEAK, "notes": "weekly IOS (superseded)"}),
    (r"ufc_stageC_features|ufc_stageD_features|ufc_stageC_sos_part", r"^revalue", {"timing_class": LEAK}),
    (r"ufc_stageC_features|ufc_stageD_features", r"^(sos_|over_elo)", {"timing_class": SOS_UNVERIFIED}),
    (r".*", r"^(p_elo|p_mkt)$", {"family": "copies of Elo / market probability", "kind": "probability"}),
    (r"match_timing_leakproof_features", r"^(ios_|prod_)", {"timing_class": CLOCK_OK}),
    (r"predictive_frontier", r"^pf_event_", {"timing_class": FIELD}),
    (r"stage4_features", r"^best_of_five", {"kind": "context x baseline", "timing_class":
                                            "reads the match's own score (post-match dependency); men only"}),
    (r"stage4_features", r"^entry_", {"notes": "existence mask uses the whole season's entry records"}),
    (r"stage4_features", r"^rank\|single", {"notes": "log rank B - log rank A: positive = A better ranked"}),
    (r"stage4_features", r"^bp_over", {"notes": "men: identically 0 in every form (K infinite)"}),
    (r"stage4_features", r"^tb_won", {"notes": "near-constant (no history reaches K): a negative control"}),
    (r"stage3_ratings", r"^updates$", {"timing_class": POST, "kind": "post-match"}),
    (r"shot_level_stage3_sides", r"^[AB]_spw_[nd]$", {"timing_class": POST, "kind": "post-match"}),
]


def raw_timing(table: str, column: str) -> str:
    """Timing class of a raw measurement row of coverage.py that the registry does not describe."""
    c = column.lower()
    if table.startswith("stage1_odds") or (table.startswith("tennis_data") and re.search(r"(b365|ps|max|avg|ex|lb|sj|bfe)w", c)):
        return R.MARKET
    if table.startswith("tennis_data"):
        if re.search(r"court|location|tournament", c):
            return R.CONTEXT_T
        if re.search(r"rank|pts", c):
            return R.ATTR
        return POST
    if table.startswith("match_timing"):
        if c.startswith("rest"):
            return OWN
        if c.startswith("start_utc"):
            return R.CONTEXT_T
        return "the clock itself"
    if table.startswith("stage0_matches"):
        return R.CONTEXT_T if re.search(r"indoor|draw_size|best_of", c) else POST
    if table.startswith("stage0_match_players"):
        return R.ATTR if re.search(r"rank|age|height|hand|country|seed|entry|lefty|same_country", c) else POST
    return POST                                                     # point- and shot-level match records


def cov_lookup(cov: pd.DataFrame, table: str, column: str) -> dict:
    r = cov[(cov["table"] == table) & (cov["column"] == column)]
    if r.empty:
        return {k: None for k in COLS[7:11]}
    r = r.iloc[0]
    return {"coverage_2013_2021_atp": r["cov_atp_d"], "coverage_2013_2021_wta": r["cov_wta_d"],
            "coverage_2022_2024_atp": r["cov_atp_r"], "coverage_2022_2024_wta": r["cov_wta_r"]}


def main() -> int:
    cov = pd.read_csv(INV / "coverage_all.csv")
    rows = []
    for name, d in R.MODEL_INPUTS.items():
        c = cov_lookup(cov, "model_frame", name)
        rows.append({"name": name, "family": d["family"], "path": "data/studies/surface_rating_race/model/model_frame.parquet",
                     "columns": f"in_{name}  <- {d['upstream']}", "per_player_available": d["per_player"],
                     "kind": d["kind"], "timing_class": d["timing"], **c, "in_model": "yes",
                     "notes": (d["definition"] + (" | " + d["notes"] if d["notes"] else ""))})
    for d in R.RAW_FIELDS:
        if d["cov"]:
            c = cov_lookup(cov, *d["cov"])
        else:      # measured elsewhere (cov_values: men d, women d, men r, women r) or not measured
            c = dict(zip(COLS[7:11], d.get("cov_values", (None,) * 4)))
        rows.append({"name": d["name"], "family": d["family"], "path": d["path"], "columns": d["columns"],
                     "per_player_available": d["per_player"], "kind": d["kind"], "timing_class": d["timing"], **c,
                     "in_model": "no", "notes": d["notes"]})
    # extra raw measurements of coverage.py not in the registry
    known = {tuple(d["cov"]) for d in R.RAW_FIELDS if d["cov"]}
    raw_tables = {"stage0_matches(pre-rebuild)", "stage0_match_players(pre-rebuild)", "match_timing_timing(pre-rebuild)",
                  "stage1_odds(pre-rebuild)", "tennis_data_couk_raw(via stage1_odds td_file/td_row)",
                  "shot_level_stage0_source_matches", "shot_level_stage1_match_stats(per player-match)"}
    for _, r in cov[cov["table"].isin(raw_tables)].iterrows():
        if (r["table"], r["column"]) in known:
            continue
        rows.append({"name": r["column"], "family": "raw: " + r["table"], "path": r["table"], "columns": r["column"],
                     "per_player_available": "per player-match" if "per player" in r["table"] or "(both" in r["column"]
                     else "match-level", "kind": "raw", "timing_class": raw_timing(r["table"], r["column"]),
                     **cov_lookup(cov, r["table"], r["column"]),
                     "in_model": "no", "notes": "share, not coverage" if "share" in r["column"] else ""})
    # built feature tables
    for table, (fam, path, pp, kind, timing, notes) in TABLE_RULES.items():
        if table == "shot_level_stage3_sides":
            continue                                   # replaced by the real-data coverage below
        for _, r in cov[cov["table"] == table].iterrows():
            row = {"name": r["column"], "family": fam, "path": path, "columns": r["column"], "per_player_available": pp,
                   "kind": kind, "timing_class": timing, **cov_lookup(cov, table, r["column"]), "in_model": "no",
                   "notes": notes}
            for treg, creg, over in COLUMN_RULES:
                if re.search(treg, table) and re.search(creg, r["column"]):
                    row.update(over)
            rows.append(row)
    ss = pd.read_csv(INV / "coverage_shot_sides.csv")
    for _, r in ss.iterrows():
        rows.append({"name": r["feature"], "family": "shot level (per player)",
                     "path": "data/studies/shot_level/stage3_sides.parquet",
                     "columns": f"A|{r['feature']} / B|{r['feature']} (+ |has)", "per_player_available": "yes",
                     "kind": "per player", "timing_class": OWN, "coverage_2013_2021_atp": r["cov_atp_d"],
                     "coverage_2013_2021_wta": r["cov_wta_d"], "coverage_2022_2024_atp": r["cov_atp_r"],
                     "coverage_2022_2024_wta": r["cov_wta_r"], "in_model": "no",
                     "notes": "coverage = both players have real data (|has); plain values are prior-filled"})
    out = pd.DataFrame(rows, columns=COLS)
    out.to_csv(OUT, index=False)
    print(f"inventory.csv: {len(out):,} rows; by family:\n{out['family'].value_counts().to_string()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
