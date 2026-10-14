"""R3-referee (follow-up), step 9: brought_back.csv and verdict.json, assembled from this folder's outputs.

brought_back.csv: every Stage 0 row of RG 2019-2026 / the Paris Olympics whose box Stage 0 does not hold in full
today (blank, failed check, partial, service games missing) and that the candidate (= my scope) holds in full, with
the checks it fails today; and the rows that stay dropped.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/verdict.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3f as F  # noqa: E402


def main() -> int:
    sim = pd.read_csv(F.OUT / "sim_scope_rows.csv", index_col=0)
    ov = pd.read_csv(F.OUT / "overrides_scope.csv", dtype=str)
    ex = pd.read_csv(F.OUT / "exchanges_scope.csv", dtype=str)
    sim["overridden"] = sim["stage0_match_id"].isin(set(ov["stage0_match_id"]))
    sim["exchanged"] = sim["stage0_match_id"].isin(set(ex["match_id"]))
    sim["group"] = np.where(sim["season"].eq(2026), "W26", np.where(sim["season"].between(2022, 2025), "W22", ""))
    back = sim[~sim["today_box_status"].eq("full") & sim["scope_box_status"].eq("full")].copy()
    stay = sim[~sim["scope_box_status"].isin(["full"])].copy()
    cols = ["stage0_match_id", "group", "tourney_name", "season", "round", "winner_name", "loser_name", "score", "source",
            "overridden", "today_box_status", "today_fails", "scope_box_status"]
    out = pd.concat([back.assign(outcome="brought back (full)"), stay.assign(outcome="not full after")])
    out[["outcome"] + cols].to_csv(F.OUT / "brought_back.csv", index=False)
    print(back.groupby(["group", "today_box_status"]).size())
    print(stay.groupby(["tourney_name", "overridden", "scope_box_status"]).size())
    return 0


if __name__ == "__main__":
    sys.exit(main())
