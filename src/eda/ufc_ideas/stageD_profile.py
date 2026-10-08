"""Stage D, part 2: the individual-statistic ratings together, against the closing odds.

Stage B built, as the UFC pipeline does, opponent-adjusted statistics (adjperf / adjdef) for 15 individual box-score
statistics and IOS offence / defence ratings for 8, and scored each ONE AT A TIME. The owner's question is whether the
profile of individual statistics (aces, double faults, first serves in, first- and second-serve points won, holds,
break points: the parts of a match that are not simply points won) carries information the closing odds do not price.
That is a joint test: every rating of the profile in one model, given the market, with the null band and the
family-wide line of the shared harness guarding against a many-input fit. The points-won aggregates (total and serve
points won, the IOS points matchup) are left out of the profiles and added back in a last model, to see what each side
adds to the other.

Models (per tour): see MODELS below. The "products" are the UFC weapon-times-liability interactions: A's offence on a
statistic times B's lack of defence on it, minus the same for B against A, from the per-player IOS ratings of
stageB_ios.parquet (a linear model of A - B differences cannot see them).

Scores: alone, given Elo, given the market, given the serve-and-return ratings through the iid model (p_ratings).
Writes stageD_profile_features.parquet, stageD_profile_ranking.csv / _results.csv / _null_copies.csv / _results.json,
stageD_profile_catalog.json, stageD_profile_summary.json.
Run: ./python.sh src/eda/ufc_ideas/stageD_profile.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.ufc_ideas import common as U  # noqa: E402

FEATURES = U.OUT / "stageD_profile_features.parquet"
CATALOG = U.OUT / "stageD_profile_catalog.json"
SUMMARY = U.OUT / "stageD_profile_summary.json"
STYLE = ["ace", "df", "first_in"]                                       # serve style: rarely decides a match
SKILL = ["first_won", "second_won", "hold", "bp_saved"]                  # serve skill statistics short of points won
IOS_STATS = STYLE + SKILL
ADJ_STATS = ["ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved", "bp_faced_pg", "brk", "bp_conv",
             "rpw_first", "rpw_second"]                                   # the individual statistics with an adjperf
NO_MIRROR = ["ace", "df", "first_in", "bp_faced_pg"]                      # adjdef differs from adjperf only here
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def assemble() -> pd.DataFrame:
    pool = U.load_pool(["rating_matchup|single", "mu_components|52 weeks"])
    b = pd.read_parquet(U.OUT / "stageB_features.parquet")
    assert (b["match_id"].to_numpy() == pool["match_id"].to_numpy()).all()
    want = ([f"ios_O_{s}|single" for s in IOS_STATS] + [f"ios_D_{s}|single" for s in IOS_STATS]
            + [f"adjperf_{s}|decayed" for s in ADJ_STATS] + [f"adjperf_{s}|52 weeks" for s in ADJ_STATS]
            + [f"adjdef_{s}|decayed" for s in NO_MIRROR] + ["adjperf_tpw|decayed", "ios_matchup_points|single",
                                                              "ios_matchup_points|diagnostic: h 4 weeks",
                                                              "ios_matchup_points|diagnostic: h 13 weeks", "p_ratings"])
    missing = [c for c in want if c not in b.columns]
    for c in want:
        if c in b.columns:
            pool[c] = b[c].to_numpy(dtype="float64")
    # the weapon-times-liability products from the per-player IOS ratings
    ios = pd.read_parquet(U.OUT / "stageB_ios.parquet").set_index("match_id").reindex(pool["match_id"])
    for s in IOS_STATS:
        oa, da = ios[f"O_{s}_a"].to_numpy(dtype="float64"), ios[f"D_{s}_a"].to_numpy(dtype="float64")
        ob, db = ios[f"O_{s}_b"].to_numpy(dtype="float64"), ios[f"D_{s}_b"].to_numpy(dtype="float64")
        pool[f"prod_{s}|single"] = oa * (-db) - ob * (-da)
    return pool, missing


MODELS = {
    "style_ios": ("Serve style: IOS offence and defence", "aces, double faults and first serves in: each player's IOS offence and defence (6 inputs)",
                  [f"ios_{k}_{s}|single" for s in STYLE for k in ("O", "D")]),
    "skill_ios": ("Serve skill short of points: IOS", "first- and second-serve points won, holds and break points saved: IOS offence and defence (8 inputs)",
                  [f"ios_{k}_{s}|single" for s in SKILL for k in ("O", "D")]),
    "profile_ios": ("The IOS profile", "IOS offence and defence on all seven individual statistics (14 inputs)",
                    [f"ios_{k}_{s}|single" for s in IOS_STATS for k in ("O", "D")]),
    "profile_ios_products": ("The IOS profile with matchup products", "the 14 IOS inputs plus seven weapon-times-liability products, one per statistic (21 inputs)",
                             [f"ios_{k}_{s}|single" for s in IOS_STATS for k in ("O", "D")] + [f"prod_{s}|single" for s in IOS_STATS]),
    "profile_adjperf": ("The adjperf profile, decayed", "adjperf (2-week half-life) on twelve individual statistics, and adjdef on the four with no mirror (16 inputs)",
                        [f"adjperf_{s}|decayed" for s in ADJ_STATS] + [f"adjdef_{s}|decayed" for s in NO_MIRROR]),
    "profile_adjperf_52w": ("The adjperf profile, 52 weeks", "adjperf over the last 52 weeks on twelve individual statistics (12 inputs)",
                            [f"adjperf_{s}|52 weeks" for s in ADJ_STATS]),
    "profile_both": ("Both profiles", "the IOS profile and the decayed adjperf profile together (30 inputs)",
                     [f"ios_{k}_{s}|single" for s in IOS_STATS for k in ("O", "D")] + [f"adjperf_{s}|decayed" for s in ADJ_STATS]
                     + [f"adjdef_{s}|decayed" for s in NO_MIRROR]),
    "profile_both_products": ("Both profiles with products", "both profiles and the seven products (37 inputs)",
                              [f"ios_{k}_{s}|single" for s in IOS_STATS for k in ("O", "D")] + [f"prod_{s}|single" for s in IOS_STATS]
                              + [f"adjperf_{s}|decayed" for s in ADJ_STATS] + [f"adjdef_{s}|decayed" for s in NO_MIRROR]),
    "profile_plus_points": ("Both profiles plus the points-won aggregates", "both profiles, the 2-week adjperf of total points won and the IOS points matchup (32 inputs)",
                            [f"ios_{k}_{s}|single" for s in IOS_STATS for k in ("O", "D")] + [f"adjperf_{s}|decayed" for s in ADJ_STATS]
                            + [f"adjdef_{s}|decayed" for s in NO_MIRROR] + ["adjperf_tpw|decayed", "ios_matchup_points|single"]),
    "points_only": ("The points-won aggregates alone", "the 2-week adjperf of total points won and the IOS points matchup (2 inputs), for comparison",
                    ["adjperf_tpw|decayed", "ios_matchup_points|single"]),
}


def main() -> int:
    f, missing = assemble()
    log(f"frame: {len(f):,} matches, {f.shape[1]} columns; missing: {missing}")
    f.to_parquet(FEATURES)
    tasks, catalog = [], []
    for mid, (name, desc, cols) in MODELS.items():
        cols = [c for c in cols if c in f.columns]
        for t in C.TOURS:
            tasks.append(U.task(t, mid, "profile", name, "profile", cols, scores=("alone", "elo", "market", "ratings"),
                                wta_box_from_2019=True, bases={"ratings": "p_ratings"}))
        catalog.append({"id": mid, "form": "profile", "name": name, "family": "statistics profile", "description": desc,
                        "inputs": cols, "tuned": "nothing: every input at Stage B's frozen constants"})
    log(f"{len(tasks)} tasks")
    res = U.rundown(FEATURES, tasks, U.OUT / "stageD_profile", workers=5)
    CATALOG.write_text(json.dumps(catalog, indent=1), encoding="utf-8")
    rank = res["ranking"]
    keep = [k for k in ("alone_imp", "elo_imp", "elo_lo", "elo_hi", "elo_2022-2026", "elo_clears_line", "market_imp", "market_lo", "market_hi",
                        "market_2022-2026", "market_clears_line", "market_above_band", "market_band_max", "ratings_imp", "ratings_lo",
                        "ratings_hi", "ratings_clears_line", "reading", "market_coverage", "eras_positive", "inputs") if k in rank.columns]
    head = {f"{r['tour']}|{r['id']}": {k: (None if pd.isna(r[k]) else (bool(r[k]) if isinstance(r[k], (bool, np.bool_)) else
                                                                      float(r[k]) if isinstance(r[k], (int, float, np.floating, np.integer)) else r[k]))
                                      for k in keep} for _, r in rank.iterrows()}
    SUMMARY.write_text(json.dumps({"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "models": catalog,
                                   "missing_columns": missing, "headline": head, "lines": res["lines"],
                                   "seconds": round(time.time() - T0, 1)}, indent=1, default=float), encoding="utf-8")
    cols = ["tour", "id", "inputs", "elo_imp", "market_imp", "market_lo", "market_hi", "market_clears_line", "ratings_imp", "reading"]
    print(rank[[c for c in cols if c in rank.columns]].to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
