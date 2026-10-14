"""Round 2, MECHANICS, part E: do courts change within an event? Per venue edition (2013-2021, model-frame matches; no
result read), the IOS-adjusted residual of aces and of serve points won, both players pooled, in the late rounds (QF, SF,
F) minus the earlier rounds; its mean by surface, and its persistence between consecutive editions of a venue.

Run: ./python.sh src/eda/feature_interactions/round2/mechanics/part_e.py
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from common import OUT, ROOT, load, logit, pr

OLD = ROOT / "data/studies/data_continuity/rebuilds/2026-10-07T0005Z/replaced/data/studies/predictability_diagnostic"


def main():
    f, _ = load()
    m0 = pd.read_parquet(OLD / "stage0_matches.parquet", columns=["match_id", "tournament_id", "round"],
                         filters=[("year", "<=", 2021)])
    p = pd.read_parquet(OLD / "stage0_match_players.parquet", columns=["match_id", "side", "ace", "svpt", "first_won",
                                                                        "second_won"])
    p = p[p["match_id"].isin(f["match_id"])].copy()
    p["spw"] = p["first_won"] + p["second_won"]
    wa = p[p["side"].eq("A")].set_index("match_id")[["ace", "svpt", "spw"]].add_suffix("_a")
    wb = p[p["side"].eq("B")].set_index("match_id")[["ace", "svpt", "spw"]].add_suffix("_b")
    d = f.merge(m0, on="match_id", how="left").join(wa, on="match_id").join(wb, on="match_id")
    d = d.dropna(subset=["ace_a", "ace_b", "svpt_a", "svpt_b", "spw_a", "spw_b", "tournament_id"])
    d = d[(d["svpt_a"] > 0) & (d["svpt_b"] > 0) & ~d["round"].eq("RR")].copy()
    d["late"] = d["round"].isin(["QF", "SF", "F"])
    d["venue"] = d["tournament_id"].astype(str).str.split("-", n=1).str[1]
    d["obs"], d["pts"], d["sobs"] = d["ace_a"] + d["ace_b"], d["svpt_a"] + d["svpt_b"], d["spw_a"] + d["spw_b"]
    d["exp"] = pr(d, "ace", "a", "b") * d["svpt_a"] + pr(d, "ace", "b", "a") * d["svpt_b"]
    d["sexp"] = pr(d, "spw", "a", "b") * d["svpt_a"] + pr(d, "spw", "b", "a") * d["svpt_b"]
    g = d.groupby(["tour", "surface", "venue", "season", "late"])[["obs", "exp", "sobs", "sexp", "pts"]].sum()
    g["ace"] = logit(g["obs"] / g["pts"]) - logit(g["exp"] / g["pts"])
    g["spw"] = logit(g["sobs"] / g["pts"]) - logit(g["sexp"] / g["pts"])
    w = g[["ace", "spw", "pts"]].unstack("late").dropna()
    D = pd.DataFrame({"ace": w[("ace", True)] - w[("ace", False)], "spw": w[("spw", True)] - w[("spw", False)],
                      "pts_late": w[("pts", True)]}).reset_index()
    out = {}
    for (t, s), h in D.groupby(["tour", "surface"]):
        h = h.sort_values(["venue", "season"]).copy()
        res = {"editions": int(len(h))}
        for k in ("ace", "spw"):
            res[f"{k}_late_minus_early_mean"] = round(float(h[k].mean()), 4)
            res[f"{k}_se"] = round(float(h[k].std() / np.sqrt(len(h))), 4)
            h["prev"] = h.groupby("venue")[k].shift(1)
            q = h.dropna(subset=["prev"])
            res[f"{k}_corr_prev_edition"] = round(float(np.corrcoef(q[k], q["prev"])[0, 1]), 3) if len(q) > 10 else None
        res["pairs"] = int(len(q))
        out[f"{t} {s}"] = res
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "part_e.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
