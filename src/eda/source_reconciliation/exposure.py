"""How far a set of corrected matches reaches the model: the model-frame matches in which either player had a
corrected match in the 28 days before (the two-week form inputs) or the 365 days before (the long-memory inputs), as
the input-data audit's frame_fault_exposure table counted them (docs/studies/input_data_audit/README.md section 3.6).

The frame is the template instance's (data/studies/current_best_model/template_2026-10-14/model_frame.parquet: its
match ids, tours and seasons); dates and players are the frozen Stage 0's. Matches are counted by tournament date, so
"before" means an earlier tournament date; the same event's earlier rounds count from day 0 (tournament dates are equal
within an event). Training/test split: seasons up to 2024 are "train", 2025-2026 "test", as the audit's table split them.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402

FRAME = C.STUDIES / "current_best_model" / "template_2026-10-14" / "model_frame.parquet"


def exposure(corrected: set[str], windows=(28, 365)) -> dict:
    m, p = C.stage0(["match_id", "tournament_date", "round_order"], ["match_id", "player_id"])
    m["d"] = pd.to_datetime(m["tournament_date"])
    frame = pd.read_parquet(FRAME, columns=["match_id", "season"])
    fp = p[p["match_id"].isin(frame["match_id"])].merge(m[["match_id", "d", "round_order"]], on="match_id")
    fp = fp.merge(frame, on="match_id")
    cp = p[p["match_id"].isin(corrected)].merge(m[["match_id", "d", "round_order"]], on="match_id")
    out = {"corrected_matches": len(corrected), "corrected_player_rows": int(len(cp))}
    j = fp.merge(cp, on="player_id", suffixes=("", "_c"))
    # the corrected match must come before the frame match: an earlier date, or the same date (same event) and an
    # earlier round
    earlier = (j["d_c"] < j["d"]) | ((j["d_c"] == j["d"]) & (j["round_order_c"] < j["round_order"]))
    j = j[earlier & (j["match_id_c"] != j["match_id"])]
    lag = (j["d"] - j["d_c"]).dt.days
    for w in windows:
        hit = j[lag <= w]["match_id"].unique()
        seasons = frame.set_index("match_id").loc[hit, "season"]
        out[f"frame_matches_within_{w}d"] = {"train_to_2024": int((seasons <= 2024).sum()),
                                             "test_2025_26": int((seasons >= 2025).sum())}
    return out


if __name__ == "__main__":
    ids = set(pd.read_csv(sys.argv[1])["match_id"])
    print(exposure(ids))
