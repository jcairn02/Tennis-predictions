"""Task 3: the atoms. One row per (Stage 0 match, player) of every match in the point table (rally_points.parquet):
the raw counts that features of later matches are summed from. Reads no match result: point winners inside a match
are counted, never who won the match.

Per player:
    srv_pts, srv_won          serve points with a known rally length (double faults included) and how many the player
                              won; srv_b0..srv_b4 and srv_w_b0..srv_w_b4 by band (0 double fault, 1 = 1-2 shots,
                              2 = 3-4, 3 = 5-8, 4 = 9+)
    ret_pts, ret_won, ret_b*, ret_w_b*   the same on the opponent's serve
    srv_rally_n, srv_rally_sum   serve points other than double faults, and the sum of their rally lengths capped at
                              9 / 10 (rally_c, the same for every source): the mean rally length on serve is the ratio
    ret_rally_n, ret_rally_sum   the same on return
    shots_srv, shots_ret, shots   shots the player hit (capped rally lengths): the server hits shots 1, 3, 5 ...,
                              the returner 2, 4, ...; a double fault 0
    net_cov                   1 when the match's source records net points, 0 when not
    net_pts, net_app, net_won points with net flags, points at which the player came to the net, and of those how many
                              the player won (0 where net_cov is 0)
    pts_known                 every point of the match with a known rally length, double faults excluded (both players
                              share it): the count task 4 sums
Context from Stage 0: opponent_id, side, tournament_date, tournament_id, year, round, round_order, level, qualifying,
draw, surface, best_of; and the source of the match's points.

Run:  ./python.sh src/eda/p9_point_details/build_atoms.py      (after build_points.py; under a minute)
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


def atoms(pts: pd.DataFrame, s0: pd.DataFrame) -> pd.DataFrame:
    p = pts.merge(s0[["match_id", "player_a_id", "player_b_id"]], on="match_id", how="inner")
    p["returner_id"] = np.where(p["server_id"].eq(p["player_a_id"]), p["player_b_id"], p["player_a_id"])
    srv_won = p["winner_id"].eq(p["server_id"]).to_numpy()
    rc = p["rally_c"].to_numpy().astype("int64")
    nondf = p["band"].to_numpy() > 0
    shots_s = np.where(rc >= 1, (rc + 1) // 2, 0)
    shots_r = np.where(rc >= 1, rc // 2, 0)
    band = p["band"].to_numpy()
    rows = {}
    for role, who, won in (("srv", "server_id", srv_won), ("ret", "returner_id", ~srv_won)):
        d = pd.DataFrame({"match_id": p["match_id"].to_numpy(), "player_id": p[who].to_numpy()})
        d[f"{role}_pts"] = 1
        d[f"{role}_won"] = won.astype("int64")
        for b in range(5):
            d[f"{role}_b{b}"] = (band == b).astype("int64")
            d[f"{role}_w_b{b}"] = ((band == b) & won).astype("int64")
        d[f"{role}_rally_n"] = nondf.astype("int64")
        d[f"{role}_rally_sum"] = np.where(nondf, rc, 0)
        d[f"shots_{role}"] = shots_s if role == "srv" else shots_r
        # net: the player's own flag on these points (as server: net_server; as returner: net_returner)
        flag = p["net_server"].to_numpy() if role == "srv" else p["net_returner"].to_numpy()
        d[f"net_pts_{role}"] = (flag >= 0).astype("int64")
        d[f"net_app_{role}"] = (flag == 1).astype("int64")
        d[f"net_won_{role}"] = ((flag == 1) & won).astype("int64")
        rows[role] = d.groupby(["match_id", "player_id"], sort=False).sum()
    a = rows["srv"].join(rows["ret"], how="outer").fillna(0).astype("int64").reset_index()
    a["shots"] = a["shots_srv"] + a["shots_ret"]
    a["net_pts"] = a["net_pts_srv"] + a["net_pts_ret"]
    a["net_app"] = a["net_app_srv"] + a["net_app_ret"]
    a["net_won"] = a["net_won_srv"] + a["net_won_ret"]
    a = a.drop(columns=[c for c in a.columns if c.startswith(("net_pts_", "net_app_", "net_won_"))])
    cov = p.groupby("match_id")["net_server"].max().ge(0)
    a["net_cov"] = a["match_id"].map(cov).fillna(False).astype("int8")
    known = p[nondf].groupby("match_id").size()
    a["pts_known"] = a["match_id"].map(known).fillna(0).astype("int64")
    src = p.groupby("match_id")["source"].first()
    a["source"] = a["match_id"].map(src)
    ctx = s0.set_index("match_id")
    a["opponent_id"] = np.where(a["player_id"].eq(a["match_id"].map(ctx["player_a_id"])),
                                a["match_id"].map(ctx["player_b_id"]), a["match_id"].map(ctx["player_a_id"]))
    a["side"] = np.where(a["player_id"].eq(a["match_id"].map(ctx["player_a_id"])), "A", "B")
    for c in ("tournament_date", "tournament_id", "year", "round", "round_order", "level", "qualifying", "surface",
              "best_of"):
        a[c] = a["match_id"].map(ctx[c])
    a["draw"] = np.where(a["qualifying"].astype(bool), "qual", "main")
    front = ["match_id", "player_id", "opponent_id", "side", "source", "tournament_date", "tournament_id", "year",
             "round", "round_order", "level", "qualifying", "draw", "surface", "best_of", "pts_known"]
    return a[front + [c for c in a.columns if c not in front]].sort_values(
        ["tournament_date", "round_order", "match_id", "side"]).reset_index(drop=True)


def main() -> int:
    pts = pd.read_parquet(B.OUT / "rally_points.parquet")
    s0 = B.stage0_men(["player_a_id", "player_b_id", "tournament_date", "tournament_id", "round", "round_order",
                       "level", "qualifying", "surface", "best_of"], 2018)
    a = atoms(pts, s0)
    # checks: every point counted once on serve and once on return
    assert int(a["srv_pts"].sum()) == len(pts) and int(a["ret_pts"].sum()) == len(pts)
    assert int(a["srv_won"].sum() + a["ret_won"].sum()) == len(pts)
    a.to_parquet(B.OUT / "atoms.parquet", index=False)
    summary = {"rows": int(len(a)), "matches": int(a["match_id"].nunique()),
               "by_source_year": a.groupby(["source", "year"]).size().rename("rows").reset_index()
               .to_dict(orient="records"),
               "net_cov_matches": int(a.loc[a["net_cov"].eq(1), "match_id"].nunique())}
    B.write_json(B.OUT / "atoms_summary.json", summary)
    B.log(f"atoms: {len(a):,} rows, {a['match_id'].nunique():,} matches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
