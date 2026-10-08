"""Two more round-2 counts (result-free): INFO-1's blind-spot share in every season including 2025-2026 (schedule
fields only: match ids, player ids, the clock's es/lf, tournament dates and rounds), and INFO-2's coverage of the
qualifier's on-site qualifying box scores (2014-2024). Writes data/studies/feature_interactions/round2/feasibility/r2_extra.json.
Run: ./python.sh src/eda/feature_interactions/round2/feasibility/r2_extra.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from src.eda.feature_interactions.round1.feasibility import base as B  # noqa: E402

OUT = B.C.OUT / "round2" / "feasibility"
OLD = B.ROOT / "data" / "studies" / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" / "data" / "studies"


def main() -> int:
    m = pd.read_parquet(OLD / "predictability_diagnostic" / "stage0_matches.parquet",
                        columns=["match_id", "tournament_date", "round_order", "player_a_id", "player_b_id"])
    t = pd.read_parquet(OLD / "match_timing" / "timing.parquet", columns=["match_id", "es", "lf"])
    m = m.merge(t, on="match_id")
    long = pd.concat([m.assign(pid=m["player_a_id"], side="A"), m.assign(pid=m["player_b_id"], side="B")])
    long = long.sort_values(["pid", "es", "tournament_date", "round_order"], kind="stable")
    long["rest"] = long["es"] - long.groupby("pid")["lf"].shift(1)
    mf = pd.read_parquet(B.C.MODEL_FRAME, columns=["match_id", "season", "tour"])
    x = long[long["match_id"].isin(set(mf["match_id"]))].pivot_table(index="match_id", columns="side", values="rest")
    x = mf.merge(x, left_on="match_id", right_index=True, how="left")
    x["either"] = (x["A"] <= 0) | (x["B"] <= 0)
    res = {"info1_either_rest_le0_by_season": x.groupby(["tour", "season"])["either"].mean().round(4)
           .rename("share").reset_index().to_dict("records")}
    # INFO-2: the fresh qualifier's on-site qualifying matches with a box score (both qualifying rows of this week)
    P = pd.read_parquet(B.OUT / "_panel_aug.parquet").drop(columns=["a_won"])
    L = B.get_history()
    box = (L["svpt"].fillna(0) > 0) & L["qualifying"].astype(bool)
    onsite_box = box.astype(float).groupby([L["player_id"], L["tournament_id"]]).cumsum() - box.astype(float)
    a, b = B.at_model(L, onsite_box.to_numpy(float), P)
    first = (P["in_round"] == P.groupby("tournament_id")["in_round"].transform("min")).to_numpy()
    qa = P["entry_a"].isin(["Q", "LL"]).to_numpy() & (P["onsite_n_a"].to_numpy() >= 1)
    qb = P["entry_b"].isin(["Q", "LL"]).to_numpy() & (P["onsite_n_b"].to_numpy() >= 1)
    sub = first & (qa ^ qb)
    has = np.where(qa, a >= 1, b >= 1)
    out = {}
    for tag, (lo, hi) in (("2014_21", B.DISC), ("2022_24", B.REP)):
        for tour in ("atp", "wta"):
            mm = sub & (P["tour"].to_numpy() == tour) & P["season"].between(lo, hi).to_numpy()
            out[f"{tour}_{tag}"] = {"subgroup_rows": int(mm.sum()), "qualifier_has_onsite_box": round(float(has[mm].mean()), 4)}
    res["info2_qualifier_box"] = out
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "r2_extra.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res["info2_qualifier_box"], indent=1))
    s = pd.DataFrame(res["info1_either_rest_le0_by_season"]).pivot(index="season", columns="tour", values="share")
    print(s.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
