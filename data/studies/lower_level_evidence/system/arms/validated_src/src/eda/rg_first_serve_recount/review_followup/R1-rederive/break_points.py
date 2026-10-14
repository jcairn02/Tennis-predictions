"""R1-rederive (round 2): break points faced and saved, recounted from RG's MatchBeats points, where they change.

For every player row of a proposed match whose break points faced or saved change (RG's statistics against the raw
row), recount from the MatchBeats file: a point the server played facing a break point (isBrkPt true on his serve),
and whether he won it. Only files holding every point of the match (MatchBeats' serve points equal RG's for both
players) are used. Prints how often the recount equals RG's value and the row's.
Run: ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/break_points.py
"""
from __future__ import annotations

import gzip
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.ingest.point_sources.infosys_slams import blocks_of, decrypt  # noqa: E402

HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive"
RAW = ROOT / "data" / "raw" / "point_sources" / "infosys_slams" / "RG"
ROUTE = {**{y: "match-beats" for y in range(2019, 2025)}, 2025: "match-centre", 2026: "match-beats-api"}


def recount(year: int, code: str) -> dict:
    path = RAW / str(year) / ROUTE[year] / f"{code}.json.gz"
    if not path.exists():
        return {}
    with gzip.open(path, "rb") as fh:
        mb = decrypt(blocks_of(ROUTE[year], json.loads(fh.read()))["mbData"])
    c = {t: Counter() for t in ("1", "2")}
    for st in mb.get("setData") or []:
        for g in st.get("gameData") or []:
            for p in g.get("pointData") or []:
                s = str(p.get("server"))
                if s in c and p.get("isBrkPt"):
                    c[s]["faced"] += 1
                    c[s]["saved"] += str(p.get("scorer")) == s
    pdx = mb.get("playerData") or {}
    return {str(pdx.get(f"tm{t}Ply1Id")): c[t] for t in ("1", "2")}


def main() -> None:
    d = pd.read_csv(HERE / "sides.csv", low_memory=False)
    m = pd.read_csv(HERE / "matches.csv", low_memory=False)
    d = d.merge(m[["rid", "cls", "group_id"]], on="rid")
    p = d[d["cls"].eq("proposed") & d["group_id"].isin(["W22", "W26"])].copy()
    full = p.groupby("rid")["mb_full"].transform(lambda s: s.astype(str).eq("True").all())
    ch = p[(p["raw_bp_faced"].ne(p["off_bp_faced"]) | p["raw_bp_saved"].ne(p["off_bp_saved"])) & full]
    rows = []
    for r in ch.itertuples():
        got = recount(int(r.year), r.code).get(str(r.rg_id))
        if got is None:
            continue
        rows.append({"year": r.year, "code": r.code, "side": r.side, "name": r.name, "group": r.group_id,
                     "raw_faced": r.raw_bp_faced, "raw_saved": r.raw_bp_saved, "rg_faced": r.off_bp_faced,
                     "rg_saved": r.off_bp_saved, "mb_faced": got["faced"], "mb_saved": got["saved"]})
    x = pd.DataFrame(rows)
    x["mb_eq_rg"] = x["mb_faced"].eq(x["rg_faced"]) & x["mb_saved"].eq(x["rg_saved"])
    x["mb_eq_row"] = x["mb_faced"].eq(x["raw_faced"]) & x["mb_saved"].eq(x["raw_saved"])
    x.to_csv(HERE / "break_points_check.csv", index=False)
    print("rows whose break points change, MatchBeats holding every point:", len(x))
    print(x.groupby("group")[["mb_eq_rg", "mb_eq_row"]].sum().to_string())
    print(x[~x["mb_eq_rg"]].to_string())


if __name__ == "__main__":
    main()
