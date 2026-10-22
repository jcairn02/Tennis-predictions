"""The lead's recount of Grand Slam box scores from Sackmann's Slam point-by-point archive (the Slams' own IBM and
Infosys point feeds, 2011-2024: Wimbledon and the US Open to 2024, the Australian Open and Roland Garros to 2021).

Reader lead_slam_pbp_recount (family slam_official, kind recount) in the box contract, written to
data/studies/source_reconciliation/box/readers/. Per singles match and player, from the points alone:
    svpt        points served (PointServer)
    first_in    points played on the first serve: ServeNumber 1 (2014 on), or the server's P1FirstSrvIn/P2FirstSrvIn
                flag (2011); first_won, second_won by who won them (a double fault is a second-serve point lost).
                Blank where a point of the match has no serve number (ServeNumber 0) and for 2012-2013, which carry
                none. ServeIndicator is the server's number (1 or 2), not the serve's
    ace, df     the server's ace and double-fault flags (P1Ace ...); blank where the match has none filled
    sv_gms      completed games served, tiebreaks not counted
    bp_faced    points of a non-tiebreak game that the receiver would win the game by winning, read from the game
                score BEFORE the point (the previous point's score in the same game; 0-0 at its start); bp_saved =
                those the server won. The archive's own break-point flags are not used (blank in some editions)
    set scores  games won per set from the game winners, tiebreak games included; complete = the recount's sets equal
                Stage 0's score and every game has a winner
Tiebreak games are recognised by their score values (counts, not 15/30/40). Linked to Stage 0 within the same Slam
edition by the two players' name keys (merge_feasibility's), main draw first.

Run: ./python.sh src/eda/source_reconciliation/lead_slam_pbp.py   (a few minutes)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.data_continuity import common as K  # noqa: E402
from src.eda.data_map import measure as M  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402
from src.eda.source_reconciliation import common as C  # noqa: E402

READERS = C.OUT / "box" / "readers"
BASE = C.DUMP / "points" / "sackmann_archive" / "slam_pointbypoint"
SLAM_NAME = {"ausopen": "australian", "frenchopen": "roland|french", "wimbledon": "wimbledon", "usopen": "us open"}
REGULAR = {"0", "15", "30", "40", "AD", "A", "GAME"}   # GAME: the AO/RG 2018-2021 files' game-won marker
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def flagcol(p: pd.DataFrame, c: str) -> pd.Series:
    if c not in p:
        return pd.Series(np.nan, index=p.index)
    return pd.to_numeric(p[c].astype("string").str.strip().replace("", pd.NA), errors="coerce")


def recount_match(p: pd.DataFrame) -> dict | None:
    """Both players' counts from one match's points (sorted). Keys p1_<field>, p2_<field>, sets, n_points, ok."""
    p = p.copy()
    p["srv"] = pd.to_numeric(p["PointServer"], errors="coerce")
    p["win"] = pd.to_numeric(p["PointWinner"], errors="coerce")
    p = p[p["srv"].isin([1, 2]) & p["win"].isin([1, 2])]
    if p.empty:
        return None
    p["set"] = pd.to_numeric(p["SetNo"], errors="coerce")
    p["game"] = pd.to_numeric(p["GameNo"], errors="coerce")
    p["gw"] = pd.to_numeric(p["GameWinner"], errors="coerce").fillna(0)
    s1 = p["P1Score"].astype("string").str.strip().str.upper().fillna("")
    s2 = p["P2Score"].astype("string").str.strip().str.upper().fillna("")
    key = p["set"].astype("Int64").astype(str) + "_" + p["game"].astype("Int64").astype(str)
    p["gkey"] = key
    # a tiebreak game: some score value in the game is not a regular game score
    irregular = ~(s1.isin(REGULAR) & s2.isin(REGULAR))
    tb_game = irregular.groupby(p["gkey"]).transform("any")
    # score before the point: the previous point's score within the same game, 0-0 at the game's start
    prev1 = s1.groupby(p["gkey"]).shift(1).fillna("0")
    prev2 = s2.groupby(p["gkey"]).shift(1).fillna("0")
    # a game-ending point resets the score to 0-0 in the archive; the next point of the SAME game cannot follow it,
    # so shift within the game is right
    srv = p["srv"].to_numpy()
    rec_score = np.where(srv == 1, prev2, prev1)
    srv_score = np.where(srv == 1, prev1, prev2)
    bp = (~tb_game.to_numpy()) & (((rec_score == "40") & np.isin(srv_score, ["0", "15", "30"])) |
                                  np.isin(rec_score, ["AD", "A"]))
    won_by_server = p["win"].to_numpy() == srv
    # the serve the point was played on: ServeNumber (1 or 2; 0 = not recorded) from 2014; the server's first-serve
    # flag (P1FirstSrvIn ...) in 2011; nothing in 2012-2013. ServeIndicator is the server's number, not the serve's.
    sn = pd.to_numeric(p.get("ServeNumber", pd.Series(np.nan, index=p.index)), errors="coerce").to_numpy()
    if np.isin(sn, [1, 2]).all():
        first = sn == 1
        has_sn = "ServeNumber"
    else:
        f1, f2 = flagcol(p, "P1FirstSrvIn"), flagcol(p, "P2FirstSrvIn")
        if f1.notna().all() and f2.notna().all():
            first = np.where(srv == 1, f1.to_numpy() > 0, f2.to_numpy() > 0)
            has_sn = "FirstSrvIn"
        else:
            first = None
            has_sn = ""
    out = {"n_points": int(len(p))}
    for k in (1, 2):
        mine = srv == k
        out[f"p{k}_svpt"] = float(mine.sum())
        out[f"p{k}_sv_won"] = float((mine & won_by_server).sum())
        if first is not None:
            out[f"p{k}_first_in"] = float((mine & first).sum())
            out[f"p{k}_first_won"] = float((mine & first & won_by_server).sum())
            out[f"p{k}_second_won"] = float((mine & ~first & won_by_server).sum())
        else:
            out[f"p{k}_first_in"] = out[f"p{k}_first_won"] = out[f"p{k}_second_won"] = np.nan
        for name, col in (("ace", f"P{k}Ace"), ("df", f"P{k}DoubleFault")):
            v = flagcol(p, col)
            out[f"p{k}_{name}"] = float((v.fillna(0).to_numpy() > 0)[mine].sum()) if v.notna().any() else np.nan
        out[f"p{k}_bp_faced"] = float((mine & bp).sum())
        out[f"p{k}_bp_saved"] = float((mine & bp & won_by_server).sum())
    # games: one row per game, its server, its winner, tiebreak or not. The winner is the archive's GameWinner where
    # filled, else the winner of the game's last point (the AO/RG 2018-2021 files leave GameWinner blank and write
    # GAME as the score); the comparison of set scores with Stage 0 (complete) catches a game cut short
    p["last_win"] = p.groupby("gkey", sort=False)["win"].transform("last")
    g = p.groupby("gkey", sort=False).agg(set=("set", "first"), srv=("srv", "first"), gw0=("gw", "max"),
                                          lw=("last_win", "last"),
                                          tb=("srv", lambda s: bool(tb_game.loc[s.index].any())))
    g["gw"] = np.where(g["gw0"].isin([1, 2]), g["gw0"], g["lw"])
    out["games_without_winner"] = int((g["gw"] == 0).sum())
    for k in (1, 2):
        out[f"p{k}_sv_gms"] = float(((g["srv"] == k) & (~g["tb"]) & (g["gw"] > 0)).sum())
    sets = []
    for st, gs in g.groupby("set", sort=True):
        sets.append((int((gs["gw"] == 1).sum()), int((gs["gw"] == 2).sum())))
    out["sets"] = sets
    out["serve_number_from"] = has_sn
    return out


def stage0_slams() -> tuple[pd.DataFrame, pd.DataFrame]:
    m, p = C.stage0(["match_id", "tour", "year", "map_level", "qualifying", "tournament_name", "score", "status"],
                    ["match_id", "player_id", "won", "player_name"])
    m = m[m["map_level"].isin(["GS", "GSQ"])].copy()
    p = p[p["match_id"].isin(m["match_id"])].copy()
    p["nk"] = K.norm_name(p["player_name"])
    return m, p


def set_scores_from_stage0(score: str) -> list[tuple[int, int]]:
    sets, _ = B.tokens_of(score or "")
    return [(a, b) for a, b, tb, br in sets]


def main() -> int:
    READERS.mkdir(parents=True, exist_ok=True)
    m, p = stage0_slams()
    log(f"Stage 0 Slam matches: {len(m):,}")
    rows, stats = [], {"files": 0, "matches_read": 0, "recounted": 0, "linked": 0, "unlinked": 0, "ambiguous": 0}
    for mpath in sorted(BASE.glob("*-matches.parquet")):
        year = int(mpath.name[:4])
        slam = mpath.name.split("-")[1]
        ppath = mpath.with_name(mpath.name.replace("-matches", "-points"))
        if slam not in SLAM_NAME or not ppath.exists():
            continue
        mm = pd.read_parquet(mpath)
        num = mm["match_num"].fillna("").astype(str)
        singles = num.str[:1].isin(["1", "2"]) | num.str[:2].isin(["MS", "WS"])
        mm = mm[singles].copy()
        if mm.empty:
            continue
        stats["files"] += 1
        mm["tour"] = np.where(num[singles].str[:1].isin(["1", "M"]), "atp", "wta")
        cols = [c for c in pq.read_schema(ppath).names if not c.startswith("_")]
        pts = pd.read_parquet(ppath, columns=cols)
        pts = pts[pts["match_id"].isin(mm["match_id"])].copy()
        pts["pn"] = pd.to_numeric(pts["PointNumber"], errors="coerce")
        pts = pts.sort_values(["match_id", "pn"], kind="stable")
        ev = m[(m["year"] == year) & m["tournament_name"].fillna("").str.lower().str.contains(SLAM_NAME[slam])]
        evp = p[p["match_id"].isin(ev["match_id"])]
        pairs = evp.groupby("match_id")["nk"].apply(lambda s: frozenset(s)).rename("pair").reset_index()
        pairs = pairs.merge(ev[["match_id", "tour", "qualifying", "score", "status"]], on="match_id")
        for r in mm.itertuples(index=False):
            stats["matches_read"] += 1
            pp = pts[pts["match_id"] == r.match_id]
            rc = recount_match(pp) if len(pp) else None
            if rc is None:
                continue
            stats["recounted"] += 1
            k1 = K.norm_name(pd.Series([r.player1])).iloc[0]
            k2 = K.norm_name(pd.Series([r.player2])).iloc[0]
            cand = pairs[(pairs["tour"] == r.tour) & pairs["pair"].map(lambda s: s == frozenset({k1, k2}))]
            method = "edition_name_pair"
            if len(cand) > 1:
                cand = cand[~cand["qualifying"].astype(bool)]
            if len(cand) == 0:
                # abbreviated names ('S. Tsitsipas', 'F Fognini'): the data map's loose test, both players, unique in
                # the edition's main draw
                pool = evp[evp["match_id"].isin(pairs.loc[(pairs["tour"] == r.tour) & ~pairs["qualifying"].astype(bool),
                                                          "match_id"])]
                hit1 = set(pool.loc[pool["player_name"].map(lambda n: M.surname_key(n) == M.surname_key(r.player1)
                                                            and M.same_player(n, r.player1)), "match_id"])
                hit2 = set(pool.loc[pool["player_name"].map(lambda n: M.surname_key(n) == M.surname_key(r.player2)
                                                            and M.same_player(n, r.player2)), "match_id"])
                both = hit1 & hit2
                cand = pairs[pairs["match_id"].isin(both)]
                method = "edition_surnames"
            if len(cand) != 1:
                stats["unlinked" if len(cand) == 0 else "ambiguous"] += 1
                continue
            stats["linked"] += 1
            mid = cand["match_id"].iloc[0]
            pl = evp[evp["match_id"] == mid].copy()
            if method == "edition_surnames":
                # key the two Stage 0 players by the archive's own name keys
                own = {}
                for nk, nm in ((k1, r.player1), (k2, r.player2)):
                    m1 = pl[pl["player_name"].map(lambda n: M.surname_key(n) == M.surname_key(nm))]
                    if len(m1) == 1:
                        own[m1.index[0]] = nk
                if len(own) != 2:
                    stats["linked"] -= 1
                    stats["ambiguous"] += 1
                    continue
                pl["nk"] = pl.index.map(own)
            pl = pl.set_index("nk")
            winner_nk = pl[pl["won"].astype(bool)].index[0] if pl["won"].astype(bool).any() else None
            s0_sets = set_scores_from_stage0(cand["score"].iloc[0])
            # the recount's sets from the Stage 0 winner's side
            w_is_p1 = (winner_nk == k1)
            rc_sets = [(a, b) if w_is_p1 else (b, a) for a, b in rc["sets"]]
            complete = (rc_sets == s0_sets) and rc["games_without_winner"] == 0 and \
                cand["status"].iloc[0] == "completed"
            for k, nk in ((1, k1), (2, k2)):
                if nk not in pl.index:
                    continue
                row = {"source_key": f"slam_pbp:{r.match_id}", "match_id": mid, "player_id": pl.loc[nk, "player_id"],
                       "complete": bool(complete), "link_method": method,
                       "x_serve_number_from": rc["serve_number_from"], "x_n_points": rc["n_points"],
                       "x_sets_agree": rc_sets == s0_sets}
                for f in C.COUNTS + ["sv_won"]:
                    row[f] = rc.get(f"p{k}_{f}", np.nan)
                rows.append(row)
        log(f"{mpath.name}: {stats}")
    out = pd.DataFrame(rows)
    out.insert(0, "kind", "recount")
    out.insert(0, "family", "slam_official")
    out.insert(0, "reader", "lead_slam_pbp_recount")
    for f in C.FIELDS:
        out[f] = out[f].astype("float64")
    out.to_parquet(READERS / "lead_slam_pbp_recount.parquet", index=False)
    stats["rows"] = int(len(out))
    stats["complete_rows"] = int(out["complete"].sum())
    C.write_json(READERS / "lead_slam_pbp_recount.json", stats)
    log(f"written {len(out):,} rows; {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
