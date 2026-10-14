"""R2-skeptic (round 2, SVX): a test of the service games that does not use MatchBeats.

In every non-tie-break game exactly one player serves, and the receiver wins it only by converting a break point, so
for each player X, against Y:
    non-tie-break games X won  =  X's service games  -  X's service games lost  +  Y's service games lost
where a player's service games lost are his break points faced minus saved (the row's own box: RG's statistics in
2019-2021, Sackmann's AO rows in 2025, the two equal). Games won come from the row's score (a 7-6 set's tie-break is not
a game won on serve; a retirement's score holds finished games only). The difference between the two players' sides
flips sign when the two service-game counts are exchanged, so where they differ the identity holds for at most one of
the truth and its exchange: an independent arbiter of every swap, from the score and the break points alone.

Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/:
    svx_identity.csv, svx_identity.json
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/svx_identity.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"


def games_on_serve(score: str) -> tuple[int, int]:
    c = B.score_counts(str(score or ""), False)
    return c[2] - c[4], c[3] - c[5]           # games won minus tie-breaks won, winner and loser


def main() -> int:
    x = pd.read_csv(OUT / "svx_checked.csv")
    x = x[x["proven"] & x["status"].isin(["completed", "retired"]) & x["true_w"].notna()].copy()
    g = x["row_score"].map(games_on_serve)
    x["gw"], x["gl"] = g.str[0], g.str[1]

    def holds(sw, sl):
        return (x["gw"] == sw - x["w_bp_lost"] + x["l_bp_lost"]) & (x["gl"] == sl - x["l_bp_lost"] + x["w_bp_lost"])
    x["identity_truth"] = holds(x["true_w"], x["true_l"])
    x["identity_row"] = holds(x["raw_w"], x["raw_l"])
    x["identity_exchanged_truth"] = holds(x["true_l"], x["true_w"])
    x["bp_known"] = x["w_bp_lost"].notna() & x["l_bp_lost"].notna()
    keep = ["match_id", "event", "year", "status", "cls", "row_score", "raw_w", "raw_l", "true_w", "true_l",
            "w_bp_lost", "l_bp_lost", "gw", "gl", "identity_truth", "identity_row", "bp_known"]
    x[keep].to_csv(OUT / "svx_identity.csv", index=False)
    out = {}
    for name, d in (("all_proven", x), ("swapped", x[x["cls"].eq("swapped")]), ("equal", x[x["cls"].eq("equal")]),
                    ("other", x[x["cls"].eq("other")])):
        d = d[d["bp_known"]]
        out[name] = {"matches": int(len(d)), "identity_holds_for_truth": int(d["identity_truth"].sum()),
                     "identity_holds_for_row": int(d["identity_row"].sum()),
                     "truth_only": int((d["identity_truth"] & ~d["identity_row"]).sum()),
                     "row_only": int((~d["identity_truth"] & d["identity_row"]).sum()),
                     "neither": int((~d["identity_truth"] & ~d["identity_row"]).sum())}
    sw = x[x["cls"].eq("swapped") & x["bp_known"]]
    out["swapped_by_edition"] = sw.groupby(["event", "year"]).agg(
        matches=("match_id", "size"), truth_only=("identity_truth", lambda s: int((s & ~sw.loc[s.index,
                                                                                          "identity_row"]).sum())),
        row_holds=("identity_row", "sum")).reset_index().to_dict("records")
    out["swapped_where_the_identity_does_not_pick_the_truth"] = sw[~(sw["identity_truth"] & ~sw["identity_row"])][
        keep].to_dict("records")
    (OUT / "svx_identity.json").write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
