"""Task 2: the point table. One row per point with a known rally length, men's matches 2018-2026, every source, one
source per linked Stage 0 match (P9 first where sources overlap).

Sources (build_common.ATP_SOURCES and SHOT_LEVEL_SOURCES):
    * the ATP's MatchBeats-format files, read and put in the shot-level convention here (build_common.mb_convention):
      P9, infosys_atp (2018-22), infosys_challengers (2021-24), infosys_slams (AO, RG 2025-26);
    * the shot-level study's common point tables (data/studies/shot_level/stage1_points_<source>.parquet), already in
      that convention: infosys (the Hugging Face copy), sirgenkii, slamtracker, slam_pbp, slam_tracking, mcp; TDI is
      read from today's dump with the same adapter (src/eda/shot_level/points.py, tdi), since its dump was refreshed
      after the shot-level study's table.
A match's points enter only when the match carries rally length: at least build_common.GATE of its points other
than aces and double faults have one (aces and double faults are known from the ending in every source, measured or
not). Where several sources carry a Stage 0 match, the first in build_common.PREFERENCE gives its points.

Columns of rally_points.parquet:
    match_id            Stage 0's match id
    source, src_key     the source and its own match key (links.parquet)
    seq                 the point's order in the match (0-based); set_no; game_seq (the game's order in the match,
                        0-based); point_in_game (0-based)
    server_id, winner_id   Stage 0 player ids
    rally               shots, the serve 1 and the shot that ended the point counted (ace 1, double fault 0, return
                        error 2, serve won without an ace 2); Infosys's groups (infosys, sirgenkii) give 9 for "9+ odd"
                        and 10 for "10+ even"
    rally_c             rally capped as those groups are (9 or 10 for 9+ shots), the same for every source
    band                0 double fault, 1 = 1-2 shots, 2 = 3-4, 3 = 5-8, 4 = 9+
    end                 0 unknown, 1 ace, 2 double fault, 3 winner, 4 forced error, 5 unforced error
    ender_is_server     1 the server hit the point's last shot, 0 the returner, -1 unknown
    net_server, net_returner   1 came to the net, 0 did not, -1 the match records no net points
    how                 for the MatchBeats files, where the rally length came from (build_common.mb_convention)
Also match_sources.parquet: one row per (Stage 0 match, source) linked, with the gate's numbers, the known points and
which source each arm of task 4 takes (chosen_all: every source; chosen_without_p9: every source but P9).

Run:  ./python.sh src/eda/p9_point_details/build_points.py      (after build_link.py; a few minutes)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.p9_point_details import build_common as B  # noqa: E402

COLS = ["source", "key", "seq", "set_no", "game_seq", "point_in_game", "server", "winner", "rally", "end", "ender",
        "net1", "net2", "how"]


def atp_points(source: str) -> pd.DataFrame:
    p = B.read_atp_points(source)
    c = B.mb_convention(p)
    c = c[c["server"].isin([1, 2]) & c["scorer"].isin([1, 2])].copy()
    c["seq"] = c.groupby("key").cumcount().astype("int32")
    lab = c["set_no"].astype(str) + "|" + c["game_no"].astype(str)
    new = (lab != lab.shift()) | (c["key"] != c["key"].shift())
    c["game_seq"] = (new.astype("int32").groupby(c["key"]).cumsum() - 1).astype("int16")
    c["point_in_game"] = c.groupby(["key", "game_seq"]).cumcount().astype("int16")
    c["source"] = source
    c["winner"] = c["scorer"]
    c["raw_known"] = c["tracked"] & c["old"].between(0, B.MAX_COUNT) & ~c["result"].eq("DF")
    return c[COLS + ["raw_known"]]


def shot_level_points(source: str, keys: set) -> pd.DataFrame:
    if source == "tdi":
        from src.eda.shot_level import points as SP
        p = SP.tdi()
    else:
        p = pd.read_parquet(B.SHOT_LEVEL / f"stage1_points_{source}.parquet",
                            columns=["source", "key", "seq", "set_no", "game_key", "server", "winner", "rally", "end",
                                     "ender", "net1", "net2"])
    p = p[p["key"].isin(keys)].copy()
    p["source"] = source
    p = p.rename(columns={"game_key": "game_seq"})
    p = p.sort_values(["key", "seq"], kind="mergesort")
    p["point_in_game"] = p.groupby(["key", "game_seq"]).cumcount().astype("int16")
    p["how"] = "shot_level"
    p["raw_known"] = (p["rally"] >= 1)
    return p[COLS + ["raw_known"]]


def orient(p: pd.DataFrame, lk: pd.DataFrame, s0: pd.DataFrame) -> pd.DataFrame:
    """Source sides 1/2 to Stage 0 player ids (a1: the source's player 1 is Stage 0's side A)."""
    p = p.merge(lk[["source", "key", "match_id_s0", "a1"]], on=["source", "key"], how="inner")
    p = p.merge(s0, left_on="match_id_s0", right_on="match_id", how="inner").drop(columns=["match_id_s0"])
    a1 = p["a1"].astype(bool).to_numpy()
    id1 = np.where(a1, p["player_a_id"], p["player_b_id"])
    id2 = np.where(a1, p["player_b_id"], p["player_a_id"])
    p["server_id"] = np.where(p["server"] == 1, id1, id2)
    p["winner_id"] = np.where(p["winner"] == 1, id1, id2)
    p["ender_is_server"] = np.select([p["ender"].eq(p["server"]), p["ender"].isin([1, 2])], [1, 0], -1).astype("int8")
    n1, n2 = p["net1"].to_numpy(), p["net2"].to_numpy()
    srv1 = p["server"].to_numpy() == 1
    p["net_server"] = np.where(srv1, n1, n2).astype("int8")
    p["net_returner"] = np.where(srv1, n2, n1).astype("int8")
    return p


def main() -> int:
    links = pd.read_parquet(B.OUT / "links.parquet")
    links = links[links["match_id_s0"].notna()].copy()
    s0 = B.stage0_men(["player_a_id", "player_b_id", "tournament_date"], 2017)
    s0 = s0[s0["year"] >= 2018][["match_id", "player_a_id", "player_b_id"]]
    parts, gates = [], []
    for source in B.PREFERENCE:
        keys = set(links.loc[links["source"].eq(source), "key"])
        if not keys:
            B.log(f"{source}: no linked match")
            continue
        p = atp_points(source) if source in B.ATP_SOURCES else shot_level_points(source, keys)
        p = p[p["key"].isin(keys)]
        g = B.match_gate(p["key"], p["rally"], p["end"])
        known = p[(p["rally"] >= 1)].groupby("key").size().rename("known_nondf")
        known_all = p[(p["rally"] >= 0)].groupby("key").size().rename("known_all")
        raw = p[p["raw_known"]].groupby("key").size().rename("raw_known")
        g = g.join(known, on="key").join(known_all, on="key").join(raw, on="key")
        g[["known_nondf", "known_all", "raw_known"]] = g[["known_nondf", "known_all", "raw_known"]].fillna(0).astype(
            "int64")
        g["source"] = source
        gates.append(g)
        keep = set(g.loc[g["carries"], "key"])
        o = orient(p[p["key"].isin(keep) & (p["rally"] >= 0)], links, s0)
        parts.append(o)
        B.log(f"{source}: {len(g):,} linked matches with points, {len(keep):,} carry rally length; "
              f"{len(o):,} points kept")
    gates = pd.concat(gates, ignore_index=True)
    ms = gates.merge(links[["source", "key", "match_id_s0", "a1", "method"]], on=["source", "key"], how="inner")
    ms = ms.rename(columns={"match_id_s0": "match_id", "key": "src_key"})
    ms["pref"] = ms["source"].map({s: i for i, s in enumerate(B.PREFERENCE)})
    car = ms[ms["carries"]].sort_values(["match_id", "pref"])
    first_all = car.drop_duplicates("match_id")
    first_wo = car[car["source"].ne("p9")].drop_duplicates("match_id")
    ms["chosen_all"] = ms.index.isin(first_all.index)
    ms["chosen_without_p9"] = ms.index.isin(first_wo.index)
    ms.drop(columns=["pref"]).to_parquet(B.OUT / "match_sources.parquet", index=False)
    pts = pd.concat(parts, ignore_index=True)
    chosen = first_all[["match_id", "source", "src_key"]]
    pts = pts.merge(chosen, left_on=["match_id", "source", "key"], right_on=["match_id", "source", "src_key"],
                    how="inner")
    pts["rally"] = pts["rally"].astype("int16")
    pts["rally_c"] = B.capped(pts["rally"]).astype("int16")
    pts["band"] = B.band_of(pts["rally"])
    out = pts[["match_id", "source", "src_key", "seq", "set_no", "game_seq", "point_in_game", "server_id",
               "winner_id", "rally", "rally_c", "band", "end", "ender_is_server", "net_server", "net_returner", "how"]]
    out = out.sort_values(["match_id", "seq"], kind="mergesort").reset_index(drop=True)
    for c in ("set_no", "end"):
        out[c] = out[c].astype("int8")
    out["seq"] = out["seq"].astype("int32")
    out.to_parquet(B.OUT / "rally_points.parquet", index=False)
    summary = {
        "points": int(len(out)), "matches": int(out["match_id"].nunique()),
        "by_source": out.groupby("source").agg(points=("seq", "size"), matches=("match_id", "nunique"))
        .reset_index().to_dict(orient="records"),
        "how": out["how"].value_counts().to_dict(),
        "band_shares": (out["band"].value_counts(normalize=True).sort_index()).to_dict(),
        "match_sources": ms.groupby(["source", "carries"]).size().rename("n").reset_index().to_dict(orient="records"),
        "overlaps": {"matches_with_two_or_more_carrying_sources": int(car["match_id"].duplicated().sum()),
                     "pairs": car.groupby("match_id")["source"].apply(lambda s: "+".join(sorted(s)))
                     .loc[lambda s: s.str.contains(r"\+")].value_counts().head(20).to_dict()},
    }
    B.write_json(B.OUT / "rally_points_summary.json", summary)
    B.log(f"rally_points: {len(out):,} points, {out['match_id'].nunique():,} Stage 0 matches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
