"""Round 2 (A2-skeptic): the extra box-score rows of data/studies/input_data_audit/fixes/round2_A_candidates.csv.

F2x  WTA API holds the exchanged box: per match, find the API record (tournament id, season, both players by shared
     name tokens), check its winner, count the 18 counts equal as recorded and exchanged, test the API's own box against
     the API's own score (games identity crediting tiebreaks, where the match was completed), test Stage 0's box both
     ways the same way, check who advanced, and look for a symmetric box (exchange changes nothing).
F1x  Doha 2015 SF and F: the Match Charting Project per player (svpt, svpt + df, first_in, first/second won, df,
     aces), Stage 0's definition test, the two-sided service-game bound, and the other Doha rows for contrast.
F2y  AO 2022 Paire-Monteiro: who served first and service games per player in the AO ball-tracking points
     (2022_MS146), SofaScore's counts, the identity with service games exchanged.
F4x  AO 2012 Li-Pervak against Wimbledon 2012: both raw rows, every held record of either match.
Writes data/studies/input_data_audit/fixes/A2-skeptic/round2_detail_*.csv
Run: ./python.sh src/eda/input_data_audit/review/A2-skeptic/round2.py
"""
from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd

import _common as K

SLAM_WTA = {"580": "901", "520": "903", "540": "904", "560": "905"}
NEXT = {"Q1": "Q2", "Q2": "Q3", "Q3": "Q4", "R128": "R64", "R64": "R32", "R32": "R16", "R16": "QF", "QF": "SF", "SF": "F"}


def toks(s) -> frozenset:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return frozenset(t for t in re.findall(r"[a-z]+", s) if len(t) >= 3)


def sets_of(score: str):
    """(games_a_first, games_b, tiebreak?) per set from a winner-first score string."""
    out = []
    for a, b, t in re.findall(r"(\d+)-(\d+)(?:\((\d+)\))?", str(score)):
        a, b = int(a), int(b)
        out.append((a, b, bool(t) or {a, b} == {6, 7}))
    return out


def identity(box_w: dict, box_l: dict, score: str, completed: bool):
    """Winner's games = own holds + loser's breaks + tiebreaks won (service games exclude tiebreak games), or the
    variant where tiebreak games count as service games (then tiebreaks are absorbed as holds/breaks: no TB term).
    Returns (holds_excl_tb, holds_incl_tb) booleans, None where untestable."""
    if not completed:
        return None, None
    s = sets_of(score)
    gw = sum(a for a, b, t in s)
    tbw = sum(1 for a, b, t in s if t and a > b)
    tbl = sum(1 for a, b, t in s if t and b > a)
    if any(pd.isna(box_w.get(c)) or pd.isna(box_l.get(c)) for c in ("sv_gms", "bp_faced", "bp_saved")):
        return None, None
    bw = box_w["bp_faced"] - box_w["bp_saved"]
    bl = box_l["bp_faced"] - box_l["bp_saved"]
    excl = box_w["sv_gms"] - bw + bl + tbw == gw
    incl = box_w["sv_gms"] - bw + bl == gw
    return bool(excl), bool(incl)


def points(box_w: dict, box_l: dict) -> tuple[float, float]:
    pw = box_w["first_won"] + box_w["second_won"] + box_l["svpt"] - box_l["first_won"] - box_l["second_won"]
    pl = box_l["first_won"] + box_l["second_won"] + box_w["svpt"] - box_w["first_won"] - box_w["second_won"]
    return pw, pl


def f2x(cand: pd.DataFrame, d: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    api = K.wta_api(range(2019, 2027))
    api["ta"], api["tb"] = api["name_a"].map(toks), api["name_b"].map(toks)
    seen = set(zip(d["tour"], d["tournament_id"], d["round"], d["player_id"]))
    main_ids = set(zip(d.loc[~d["qualifying"], "tour"], d.loc[~d["qualifying"], "tournament_id"], d.loc[~d["qualifying"], "player_id"]))
    held_rounds = set(zip(d["tour"], d["tournament_id"], d["round"]))
    rows = []
    for c in cand.itertuples():
        mm = m[m["match_id"].eq(c.match_id)]
        pr = d[d["match_id"].eq(c.match_id)]
        rec = {"match_id": c.match_id, "stage0_found": len(mm) == 1 and len(pr) == 2}
        if not rec["stage0_found"]:
            rows.append(rec)
            continue
        mm = mm.iloc[0]
        w = pr[pr["won"]].iloc[0]
        l_ = pr[~pr["won"]].iloc[0]
        bw = {k: w[k] for k in K.BOX}
        bl = {k: l_[k] for k in K.BOX}
        rec.update({"winner": w["player_name"], "loser": l_["player_name"], "score": mm["score"], "status": mm["status"],
                    "has_box": bool(mm["has_box"]), "box_status": mm["box_status"],
                    "source_ok": (mm["source_file"] == c.source_file) and (int(mm["source_row"]) == int(c.source_row))})
        # symmetric box?
        rec["counts_equal_between_players"] = int(sum(float(bw[k]) == float(bl[k]) for k in K.BOX if pd.notna(bw[k]) and pd.notna(bl[k])))
        # API record
        y = str(mm["year"])
        tid = str(mm["tournament_id"]).split("-")[-1]
        tid = SLAM_WTA.get(tid, tid)
        cc = api[api["year"].astype(str).eq(y) & api["tournament_id"].astype(str).eq(tid)]
        tw, tl = toks(w["player_name"]), toks(l_["player_name"])
        best, score_, wside = None, 0, None
        for _, h in cc.iterrows():
            for ws, a, b in (("a", h["ta"], h["tb"]), ("b", h["tb"], h["ta"])):
                s1, s2 = len(tw & a), len(tl & b)
                if s1 >= 1 and s2 >= 1 and s1 + s2 > score_:
                    best, score_, wside = h, s1 + s2, ws
        if best is None:
            rec["api_found"] = False
            rows.append(rec)
            continue
        h = best
        ls = "b" if wside == "a" else "a"
        aw = {k: h[f"{wside}_{k}"] for k in K.BOX}
        al = {k: h[f"{ls}_{k}"] for k in K.BOX}
        eq_rec = sum(float(bw[k]) == float(aw[k]) for k in K.BOX if pd.notna(bw[k]) and pd.notna(aw[k])) + \
            sum(float(bl[k]) == float(al[k]) for k in K.BOX if pd.notna(bl[k]) and pd.notna(al[k]))
        eq_exc = sum(float(bw[k]) == float(al[k]) for k in K.BOX if pd.notna(bw[k]) and pd.notna(al[k])) + \
            sum(float(bl[k]) == float(aw[k]) for k in K.BOX if pd.notna(bl[k]) and pd.notna(aw[k]))
        n = sum(pd.notna(bw[k]) and pd.notna(aw[k]) for k in K.BOX) + sum(pd.notna(bl[k]) and pd.notna(al[k]) for k in K.BOX)
        completed = mm["status"] == "completed"
        api_id = identity(aw, al, mm["score"], completed)
        s0_rec = identity(bw, bl, mm["score"], completed)
        s0_exc = identity(bl, bw, mm["score"], completed)
        pw, pl = points(bw, bl)
        apw, apl = points(aw, al)
        rec.update({"api_key": h["key"], "api_result": h["ResultString"], "api_winner_same": h["winner_side"] == wside,
                    "equal_as_recorded": int(eq_rec), "equal_exchanged": int(eq_exc), "fields": int(n),
                    "api_identity_excl_tb": api_id[0], "api_identity_incl_tb": api_id[1],
                    "stage0_identity_as_recorded": s0_rec[0], "stage0_identity_exchanged": s0_exc[0],
                    "stage0_identity_as_recorded_incl_tb": s0_rec[1], "stage0_identity_exchanged_incl_tb": s0_exc[1],
                    "winner_pts_as_recorded": pw, "loser_pts_as_recorded": pl, "api_winner_pts": apw, "api_loser_pts": apl})
        # progression
        nxt = NEXT.get(mm["round"])
        if nxt and (mm["tour"], mm["tournament_id"], nxt) in held_rounds:
            won_on = (mm["tour"], mm["tournament_id"], nxt, w["player_id"]) in seen
            lost_on = (mm["tour"], mm["tournament_id"], nxt, l_["player_id"]) in seen
            rec["progression"] = {(True, False): "winner advanced", (False, True): "LOSER advanced",
                                  (True, True): "both", (False, False): "neither"}[(won_on, lost_on)]
        elif mm["qualifying"]:
            rec["progression"] = ("winner in main draw" if (mm["tour"], mm["tournament_id"], w["player_id"]) in main_ids
                                  else "winner not in main draw") + ("; loser in main draw" if (mm["tour"], mm["tournament_id"], l_["player_id"]) in main_ids else "")
        else:
            rec["progression"] = "next round not held"
        rows.append(rec)
    return pd.DataFrame(rows)


def f1x(cand: pd.DataFrame, d: pd.DataFrame) -> pd.DataFrame:
    doha = d[d["tournament_id"].eq("2015-W-PR-QAT-1A-2015") & d["has_box"]].copy()
    mc = K.mcp("w")
    mc = mc[mc["date"].dt.year.eq(2015)]
    doha["pk"], doha["ok"] = doha["player_name"].map(K.name_key), doha["o_player_name"].map(K.name_key)
    j = doha.merge(mc, on=["pk", "ok"], how="left", suffixes=("", "_mcp"))
    j = j[j["match_id_mcp"].isna() | (j["date"] - j["tournament_date"]).dt.days.between(-1, 16)]
    j = j.drop_duplicates(["match_id", "player_id"])
    j["def_fail"] = (j["second_won"] + j["df"]) > (j["svpt"] - j["first_in"])
    B = j["bp_faced"] - j["bp_saved"]
    H = j["sv_gms"] - B
    spw = j["first_won"] + j["second_won"]
    for tag, sv in (("raw", j["svpt"]), ("cor", j["svpt"] + j["df"])):
        spl = sv - spw
        dif = spw - spl
        j[f"bound_ok_{tag}"] = (dif >= 2 * H - 4 * B) & (dif <= 4 * H - 2 * B) & (spl >= 4 * B) & (spw >= 4 * H)
        j[f"diff_{tag}"] = dif
    j["in_round2"] = j["match_id"].isin(cand["match_id"])
    keep = ["in_round2", "match_id", "round", "player_name", "svpt", "df", "first_in", "first_won", "second_won", "ace",
            "serve_pts", "dfs", "first_in_mcp", "first_won_mcp", "second_won_mcp", "aces", "match_id_mcp", "def_fail",
            "bound_ok_raw", "bound_ok_cor", "diff_raw", "diff_cor", "sv_gms", "bp_saved", "bp_faced", "status", "tb_won_d"]
    return j[keep].sort_values(["in_round2", "round"])


def f2y() -> dict:
    p = pd.read_parquet(K.ROOT / "data/dump/points/slam_ball_tracking/points/AO_2022.parquet")
    q = p[p["match_id"].astype(str).eq("2022_MS146")].copy()
    m = pd.read_parquet(K.ROOT / "data/dump/points/slam_ball_tracking/matches.parquet")
    mm = m[m["match_id"].astype(str).eq("2022_MS146") & m["year"].astype(str).eq("2022")].iloc[0]
    q["set_num"] = pd.to_numeric(q["set_num"], errors="coerce")
    q["game_num"] = pd.to_numeric(q["game_num"], errors="coerce")
    q["point_num"] = pd.to_numeric(q["point_num"], errors="coerce")
    q = q.sort_values(["set_num", "game_num", "point_num"])
    games = q.drop_duplicates(["set_num", "game_num"])[["set_num", "game_num", "server_id", "is_tiebreak"]]
    first_server = games.iloc[0]["server_id"]
    tb = games["is_tiebreak"].astype(str).str.upper().isin(["TRUE", "1"])
    per = games[~tb].groupby("server_id").size().to_dict()
    pts = q.drop_duplicates(["set_num", "game_num", "point_num"])
    svpt = pts.groupby("server_id").size().to_dict()
    dfc = q[q["is_doublefault"].astype(str).str.upper().isin(["TRUE", "1"])].drop_duplicates(["set_num", "game_num", "point_num"]).groupby("server_id").size().to_dict()
    ace = q[q["is_ace"].astype(str).str.upper().isin(["TRUE", "1"])].drop_duplicates(["set_num", "game_num", "point_num"]).groupby("server_id").size().to_dict()
    return {"player1": mm["player1"], "player1_id": mm["player1_id"], "player2": mm["player2"], "player2_id": mm["player2_id"],
            "first_server_id": first_server, "service_games_by_server": per, "games_listed": int(len(games)),
            "tiebreak_games": int(tb.sum()), "serve_points_by_server": svpt, "double_faults_by_server": dfc,
            "aces_by_server": ace, "points_listed": int(len(pts))}


def f4x(d: pd.DataFrame) -> pd.DataFrame:
    r = K.sackmann("wta", "201[12]")
    r = r[((r["winner_name"].str.contains("Li$|Na Li", regex=True) & r["loser_name"].str.contains("Pervak"))
           | (r["loser_name"].str.contains("Li$|Na Li", regex=True) & r["winner_name"].str.contains("Pervak")))]
    return r[["tourney_name", "tourney_date", "round", "winner_name", "loser_name", "score", "_source_file", "_row"]
             + [f"{s}_{K.RAW[c]}" for s in ("w", "l") for c in K.BOX]]


def main() -> None:
    pd.set_option("display.width", 320)
    pd.set_option("display.max_columns", 60)
    pd.set_option("display.max_colwidth", 60)
    cand = pd.read_csv(K.ROOT / "data/studies/input_data_audit/fixes/round2_A_candidates.csv")
    d = K.stage0()
    m = pd.read_parquet(K.S0 / "stage0_matches.parquet")

    x = f2x(cand[cand["cand"].eq("F2x")], d, m)
    x.to_csv(K.OUT / "round2_detail_f2x.csv", index=False)
    print(x.drop(columns=["api_result"], errors="ignore").to_string())

    y = f1x(cand[cand["cand"].eq("F1x")], d)
    y.to_csv(K.OUT / "round2_detail_f1x.csv", index=False)
    print(y.to_string())

    z = f2y()
    print("F2y ball tracking:", z)
    s = d[d["match_id"].eq("atp|2022-580|R128|atp:105332|atp:106329")][["player_name", "won"] + K.BOX]
    print(s.to_string())

    w = f4x(d)
    w.to_csv(K.OUT / "round2_detail_f4x_raw.csv", index=False)
    print(w.to_string())


if __name__ == "__main__":
    main()
