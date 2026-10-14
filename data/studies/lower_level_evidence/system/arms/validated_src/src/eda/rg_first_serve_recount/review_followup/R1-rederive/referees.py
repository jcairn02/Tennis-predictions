"""R1-rederive (round 2): the independent referees, recounted myself, keyed to RG's documents.

  * Court Vision (the Hawk-Eye copy, data/dump/points/slam_ball_tracking/points/RG_<year>.parquet): one row per serve,
    RG's own match codes and player ids. Per server and point (set, game, point number): the point is a first-serve
    point when it has no second-serve row and its first serve is not a fault; a second-serve point when it has a
    second-serve row; "gap" when its only row is a faulted first serve. Aces and double faults from the rows' flags.
    Held 2019-2024; a referee for 2019, 2020 and 2022 only (its 2023-24 files lack many faulted first serves).
  * The Match Charting Project (hand-charted; data/dump/points/match_charting_project/): the Overview totals per player
    (serve points, first serves in, points won on each serve, aces, double faults), linked to RG's documents by year,
    tour, round and both players' names.

Writes work/referees.parquet: one row per (year, code, RG player id): cv_* and mcp_* counts.
Run: ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/referees.py
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
WORK = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive" / "work"
CV = ROOT / "data" / "dump" / "points" / "slam_ball_tracking" / "points"
MCP = ROOT / "data" / "dump" / "points" / "match_charting_project"


def toks(name) -> frozenset:
    s = unicodedata.normalize("NFKD", str(name or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    return frozenset(t for t in re.sub(r"[^a-z]+", " ", s).split() if t)


def sim(a, b) -> float:
    return len(a & b) / min(len(a), len(b)) if a and b else 0.0


def court_vision() -> pd.DataFrame:
    out = []
    for year in range(2019, 2025):
        f = CV / f"RG_{year}.parquet"
        if not f.exists():
            continue
        p = pd.read_parquet(f, columns=["match_id", "set_num", "game_num", "point_num", "serve_num", "server_id",
                                        "point_winner_id", "is_fault", "is_doublefault", "is_ace"])
        for c in ("set_num", "game_num", "point_num", "serve_num", "is_fault", "is_doublefault", "is_ace"):
            p[c] = pd.to_numeric(p[c], errors="coerce")
        # a faulted first serve's row often carries no ids ("NA"): the point's server is read off its other row
        sid = p["server_id"].astype(str)
        p["server_id"] = sid.where(sid.str.fullmatch(r"\d+"))
        p["point_winner_id"] = p["point_winner_id"].astype(str)
        key = ["match_id", "set_num", "game_num", "point_num"]
        g = p.groupby(key)
        pt = pd.DataFrame({
            "server": g["server_id"].first(),
            "has2": g["serve_num"].apply(lambda s: (s == 2).any()),
            "fault1": g.apply(lambda d: bool(((d["serve_num"] == 1) & (d["is_fault"] == 1)).any()), include_groups=False),
            "ace": g["is_ace"].sum(), "dfl": g["is_doublefault"].sum(),
            "winner": g.apply(lambda d: d.sort_values("serve_num")["point_winner_id"].iloc[-1], include_groups=False),
        }).reset_index()
        pt["won"] = pt["winner"].eq(pt["server"])
        pt["first_pt"] = ~pt["has2"] & ~pt["fault1"]
        pt["second_pt"] = pt["has2"]
        pt["gap"] = ~pt["has2"] & pt["fault1"]
        pt["fw"] = pt["won"] & pt["first_pt"]
        pt["sw"] = pt["won"] & pt["second_pt"]
        agg = pt.groupby(["match_id", "server"]).agg(
            cv_svpt=("server", "size"), cv_first_in=("first_pt", "sum"), cv_first_won=("fw", "sum"),
            cv_second_won=("sw", "sum"), cv_second_pts=("second_pt", "sum"), cv_gap=("gap", "sum"),
            cv_ace=("ace", "sum"), cv_df=("dfl", "sum")).reset_index()
        agg["year"] = year
        out.append(agg.rename(columns={"match_id": "code", "server": "player_id"}))
    return pd.concat(out, ignore_index=True)


def charting(api: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for g, tour in (("m", "atp"), ("w", "wta")):
        meta = pd.read_parquet(MCP / "metadata" / f"charting-{g}-matches.parquet")
        ov = pd.read_parquet(MCP / "stats" / f"charting-{g}-stats-Overview.parquet")
        ov = ov[ov["set"].astype(str).eq("Total")]
        meta = meta[meta["Tournament"].astype(str).str.contains("Roland Garros$", regex=True)
                    & ~meta["Tournament"].astype(str).str.contains("Junior")]
        meta = meta.assign(year=meta["Date"].astype(str).str[:4].astype(int), tour=tour)
        meta = meta[meta["year"].between(2019, 2026)]
        frames.append(ov.merge(meta[["match_id", "year", "tour", "Round", "Player 1", "Player 2"]], on="match_id"))
    mcp = pd.concat(frames, ignore_index=True)
    for c in ("serve_pts", "first_in", "first_won", "second_won", "aces", "dfs"):
        mcp[c] = pd.to_numeric(mcp[c], errors="coerce")
    a = api.copy()
    a["tour"] = np.where(a["family"].isin(["SM", "QM"]), "atp", "wta")
    a["tok"] = [toks(f"{f} {l}") for f, l in zip(a["first_name"], a["last_name"])]
    docs = a.pivot_table(index=["year", "code", "tour", "round"], columns="team", values=["tok", "player_id"],
                         aggfunc="first")
    docs.columns = [f"{x}_{t}" for x, t in docs.columns]
    docs = docs.reset_index()
    out = []
    for mid, ch in mcp.groupby("match_id"):
        r0 = ch.iloc[0]
        pa, pb = toks(r0["Player 1"]), toks(r0["Player 2"])
        cand = docs[docs["year"].eq(r0["year"]) & docs["tour"].eq(r0["tour"]) & docs["round"].eq(str(r0["Round"]))]
        best = None
        for d in cand.itertuples():
            s1 = sim(pa, d.tok_A) + sim(pb, d.tok_B)
            s2 = sim(pa, d.tok_B) + sim(pb, d.tok_A)
            s = max(s1, s2)
            if s >= 1.5 and (best is None or s > best[0]):
                best = (s, d, s1 >= s2)
        if best is None:
            continue
        _, d, a_is_1 = best
        for r in ch.itertuples():
            me = toks(r.player)
            team = "A" if sim(me, d.tok_A) >= sim(me, d.tok_B) else "B"
            out.append({"year": r0["year"], "code": d.code, "player_id": getattr(d, f"player_id_{team}"),
                        "mcp_match": mid, "mcp_svpt": r.serve_pts, "mcp_first_in": r.first_in,
                        "mcp_first_won": r.first_won, "mcp_second_won": r.second_won, "mcp_ace": r.aces,
                        "mcp_df": r.dfs})
    return pd.DataFrame(out)


def main() -> None:
    api = pd.read_parquet(WORK / "rg_api.parquet")
    cv = court_vision()
    mc = charting(api)
    ids = api[["year", "code", "player_id"]].drop_duplicates()
    ref = ids.merge(cv, on=["year", "code", "player_id"], how="left").merge(
        mc.drop_duplicates(["year", "code", "player_id"]), on=["year", "code", "player_id"], how="left")
    ref.to_parquet(WORK / "referees.parquet", index=False)
    print("Court Vision rows keyed to RG players:", int(ref["cv_svpt"].notna().sum()), "of", len(cv),
          "| by year", ref[ref["cv_svpt"].notna()].groupby("year").size().to_dict())
    print("charts keyed:", int(ref["mcp_svpt"].notna().sum()), "of", len(mc), "| by year",
          ref[ref["mcp_svpt"].notna()].groupby("year").size().to_dict())


if __name__ == "__main__":
    main()
