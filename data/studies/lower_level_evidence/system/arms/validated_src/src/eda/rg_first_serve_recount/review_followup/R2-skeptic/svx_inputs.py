"""R2-skeptic (round 2, SVX): my own inputs for the swapped-service-games review, besides the RG tables I already hold.

    raw_ao.parquet       Stage 0's raw rows (the build's own loader and normaliser, read once, then freed) of the
                         Australian Open 2025 (tournament id 2025-580, or a name saying Australian Open, any source)
    ao_mb_points.parquet every point of the AO 2025 MatchBeats files (decrypted with the adapter's routine), as
                         parse.py reads RG's: set, game, tie-break flag, order, server, serve, scorer, result, scores
    ao_mb_meta.parquet   one row per AO 2025 file: players per slot, status, completeness
    mcp_first.parquet    the first charted point of every hand chart of Roland Garros 2019-2026 and the Australian
                         Open 2025: its server (by name), set, game, and the chart's players
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/svx_inputs.py
"""
from __future__ import annotations

import gc
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
RAW = ROOT / "data" / "raw" / "point_sources"
MCP = ROOT / "data" / "dump" / "points" / "match_charting_project"


def raw_ao() -> None:
    from src.eda.predictability_diagnostic import stage0_build as B
    raw = B.normalise(B.load_raw())
    ao = raw["tid"].str.fullmatch(r"2025-580") | (raw["tourney_name"].str.contains("australian", case=False)
                                                  & raw["tid"].str.startswith("2025"))
    keep = (["source", "group", "tour", "tid", "tourney_id", "tourney_name", "tourney_date", "round", "winner_name",
             "loser_name", "winner_id", "loser_id", "wkey", "lkey", "score", "minutes", "best_of", "_source_file",
             "_row", "rid"] + B.OVERRIDE_COUNTS)
    sub = raw.loc[ao, keep].copy()
    del raw
    gc.collect()
    for c in B.OVERRIDE_COUNTS:
        sub[c] = sub[c].astype(str)
    sub["_row"] = pd.to_numeric(sub["_row"], errors="coerce").astype("Int64")
    sub.to_parquet(OUT / "raw_ao.parquet", index=False)
    print("raw AO 2025:", sub.groupby(["source", "tour", "tid", "tourney_name"]).size().to_dict())


def ao_mb() -> None:
    from src.ingest.point_sources import common as P
    from src.ingest.point_sources import infosys_slams as I
    pts, meta = [], []
    for path in sorted((RAW / "infosys_slams" / "AO" / "2025" / "match-beats").glob("*.json.gz")):
        code = path.name.split(".")[0]
        rec = {"year": 2025, "code": code, "route": "match-beats"}
        try:
            blocks = I.blocks_of("match-beats", P.read_json(path))
            doc = I.decrypt(blocks["mbData"]) if "mbData" in blocks else None
        except Exception as err:   # noqa: BLE001 - recorded
            meta.append({**rec, "problem": f"{type(err).__name__}: {err}"})
            continue
        if not isinstance(doc, dict) or not doc.get("setData"):
            meta.append({**rec, "problem": "empty"})
            continue
        pdat = doc.get("playerData") or {}
        meta.append({**rec, "problem": None, "complete": doc.get("isMatchComplete"), "status": doc.get("matchStatus"),
                     "winner_slot": doc.get("matchWinner"), "sets_complete": doc.get("setsComplete"),
                     **{f"p{k}_{f}": pdat.get(f"tm{k}Ply1{F}") for k in (1, 2)
                        for f, F in (("first", "FirstName"), ("last", "LastName"), ("id", "Id"))}})
        i = 0
        for si, s in enumerate(doc.get("setData") or [], 1):
            for gi, g in enumerate(s.get("gameData") or [], 1):
                for p in g.get("pointData") or []:
                    i += 1
                    pts.append({"year": 2025, "code": code, "set": s.get("set", si), "set_i": si,
                                "game": g.get("game", gi), "game_i": gi, "tb": bool(g.get("isTieBreak")),
                                "game_complete": g.get("isGameComplete"), "game_winner": g.get("gameWinner"),
                                "idx": i, "pointId": p.get("pointId"), "server": str(p.get("server")),
                                "serve": str(p.get("serve")), "scorer": str(p.get("scorer")),
                                "result": p.get("result"), "tm1_score": p.get("tm1GameScore"),
                                "tm2_score": p.get("tm2GameScore")})
    pd.DataFrame(pts).to_parquet(OUT / "ao_mb_points.parquet", index=False)
    m = pd.DataFrame(meta)
    m.to_parquet(OUT / "ao_mb_meta.parquet", index=False)
    print("AO 2025 MatchBeats:", len(m), "files;", m["problem"].value_counts(dropna=False).to_dict(), len(pts), "points")


def mcp_first() -> None:
    """Per hand chart: the first charted point (and whether it opens the match: sets 0-0, games 0-0, points 0-0), its
    server by name, and the first server implied by every non-tie-break game (a game numbered k in the match, Gm#, is
    served by the first server when k is odd), with how many games dissent."""
    rows = []
    for g in ("m", "w"):
        meta = pd.read_parquet(MCP / "metadata" / f"charting-{g}-matches.parquet")
        yr = pd.to_numeric(meta["Date"].astype(str).str[:4], errors="coerce")
        sel = meta[meta["Tournament"].astype(str).str.contains("Roland Garros|Australian Open", case=False)
                   & yr.between(2019, 2026)]
        ids = set(sel["match_id"])
        for f in sorted((MCP / "points").glob(f"charting-{g}-points-*.parquet")):
            pt = pd.read_parquet(f, columns=["match_id", "Pt", "Set1", "Set2", "Gm1", "Gm2", "Pts", "Gm#", "Svr"])
            pt = pt[pt["match_id"].isin(ids)].copy()
            if pt.empty:
                continue
            for c in ("Pt", "Set1", "Set2", "Gm1", "Gm2", "Gm#", "Svr"):
                pt[c] = pd.to_numeric(pt[c], errors="coerce")
            pt = pt.sort_values(["match_id", "Pt"])
            for mid, q in pt.groupby("match_id", sort=False):
                mm = sel[sel["match_id"].eq(mid)].iloc[0]
                f0 = q.iloc[0]
                opens = (f0["Set1"] == 0 and f0["Set2"] == 0 and f0["Gm1"] == 0 and f0["Gm2"] == 0
                         and str(f0["Pts"]).strip() in ("0-0", "0 - 0"))
                tb = (q["Gm1"].eq(6) & q["Gm2"].eq(6))
                games = q[~tb].groupby("Gm#")["Svr"].agg(lambda s: s.mode().iloc[0] if len(s.mode()) else None)
                votes = [int(s) if k % 2 == 1 else (3 - int(s)) for k, s in games.items()
                         if pd.notna(k) and s in (1, 2)]
                top = max(set(votes), key=votes.count) if votes else None
                name = {1: mm["Player 1"], 2: mm["Player 2"]}
                rows.append({"mcp_id": mid, "tour": "M" if g == "m" else "W", "date": mm["Date"],
                             "tournament": mm["Tournament"], "round": mm["Round"], "p1": mm["Player 1"],
                             "p2": mm["Player 2"], "first_pt": f0["Pt"], "opens_match": bool(opens),
                             "first_point_server": name.get(int(f0["Svr"])) if pd.notna(f0["Svr"]) else None,
                             "parity_first_server": name.get(top), "parity_games": len(votes),
                             "parity_dissent": sum(v != top for v in votes), "n_points": len(q)})
    out = pd.DataFrame(rows)
    out.to_parquet(OUT / "mcp_first.parquet", index=False)
    print("hand charts:", len(out), "opening at 0-0:", int(out["opens_match"].sum()),
          "parity dissent > 0:", int(out["parity_dissent"].gt(0).sum()))


def main() -> int:
    raw_ao()
    ao_mb()
    mcp_first()
    return 0


if __name__ == "__main__":
    sys.exit(main())
