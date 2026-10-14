"""R2-skeptic (round 2): break points recounted from RG's point record, against RG's statistics and the row.

A break point faced by the server is a point of a non-tie-break game played when the receiver would win the game by
winning it (receiver at 40 or advantage, ahead of the server: 0-40, 15-40, 30-40, 40-AD); it is saved when the server
wins it. Recounted from MatchBeats' scorers (replayed per game), for every RG match of 2019-2026 with a file.

Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/:
    bp_rows.csv    one row per Stage 0 player row: MatchBeats' break points faced/saved, RG's statistics', the row's
    bp_summary.json  agreement by period: MatchBeats = RG's statistics; the row = RG's
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/break_points.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"


def recount(pts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (y, c), g in pts.groupby(["year", "code"], sort=False):
        faced = {"1": 0, "2": 0}
        saved = {"1": 0, "2": 0}
        for _, game in g.sort_values("idx").groupby(["set_i", "game_i"], sort=True):
            if bool(game["tb"].iloc[0]):
                continue
            sp = rp = 0
            for p in game.itertuples(index=False):
                srv = p.server
                if rp >= 3 and rp > sp:
                    faced[srv] = faced.get(srv, 0) + 1
                    if p.scorer == srv:
                        saved[srv] = saved.get(srv, 0) + 1
                if p.scorer == srv:
                    sp += 1
                elif p.scorer in ("1", "2"):
                    rp += 1
        for k in ("1", "2"):
            rows.append({"year": y, "code": c, "slot": int(k), "mbbp_faced": faced[k], "mbbp_saved": saved[k]})
    return pd.DataFrame(rows)


def main() -> int:
    pts = pd.read_parquet(OUT / "mb_points.parquet")
    bp = recount(pts)
    s = pd.read_parquet(OUT / "players.parquet")
    s = s.merge(bp.rename(columns={"code": "code", "slot": "mb_slot"}), on=["year", "code", "mb_slot"], how="left")
    s["period"] = np.select([s["year"].le(2021), s["year"].le(2025)], ["2019-2021", "2022-2025"], "2026")
    s["mb_eq_rg"] = s["mbbp_faced"].eq(s["my_bpFaced"]) & s["mbbp_saved"].eq(s["my_bpSaved"])
    s["raw_eq_rg"] = s["raw_bpFaced"].eq(s["my_bpFaced"]) & s["raw_bpSaved"].eq(s["my_bpSaved"])
    s["raw_eq_mb"] = s["raw_bpFaced"].eq(s["mbbp_faced"]) & s["raw_bpSaved"].eq(s["mbbp_saved"])
    keep = ["match_id", "year", "tour", "draw", "round", "side", "player", "code", "status", "mb_complete_match",
            "raw_bpFaced", "raw_bpSaved", "my_bpFaced", "my_bpSaved", "mbbp_faced", "mbbp_saved", "mb_eq_rg",
            "raw_eq_rg", "raw_eq_mb"]
    s[keep].to_csv(OUT / "bp_rows.csv", index=False)
    summ = {}
    for per, g in s.groupby("period"):
        c = g[g["mb_complete_match"] & g["my_bpFaced"].notna()]
        r = c[c["raw_bpFaced"].notna()]
        summ[per] = {"rows_mb_complete": int(len(c)), "mb_equals_rg": int(c["mb_eq_rg"].sum()),
                     "rows_with_raw": int(len(r)), "raw_equals_rg": int(r["raw_eq_rg"].sum()),
                     "raw_differs_and_mb_equals_rg": int((~r["raw_eq_rg"] & r["mb_eq_rg"]).sum()),
                     "raw_differs_and_mb_equals_raw": int((~r["raw_eq_rg"] & r["raw_eq_mb"]).sum()),
                     "mb_differs_from_rg_examples": c[~c["mb_eq_rg"]][["match_id", "side", "status", "my_bpFaced",
                                                                       "my_bpSaved", "mbbp_faced", "mbbp_saved"]]
                     .head(15).to_dict("records")}
    (OUT / "bp_summary.json").write_text(json.dumps(summ, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summ, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
