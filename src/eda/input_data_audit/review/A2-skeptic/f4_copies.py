"""F4 review (A2-skeptic): box scores repeated on the same pair's other meeting, and ATP Dusseldorf 2012.

Every group of Sackmann raw rows that share one 16-count box (box_raw_copies.csv rows with same_players True, plus the
ATP Dusseldorf 2012 rows) is rebuilt from the raw files. For each match of a group the box is tested against that
match's own score:
  * Stage 0's B5 (service games within one of the games, tiebreaks counted or not) and B9 (>= 4.5 points a game);
  * the games identity (completed, no tiebreak), as recorded and exchanged;
  * points per game against the tour norm, and serve points per service game;
  * the winner's share of points (the winner wins more points in 96% of matches);
  * the Match Charting Project where it charted either match.
The copy is the match whose score the box does not fit; a group where the box fits both or neither is undecided.
Writes data/studies/input_data_audit/fixes/A2-skeptic/f4_groups.csv
Run: ./python.sh src/eda/input_data_audit/review/A2-skeptic/f4_copies.py
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

import _common as K

RAW16 = ["w_ace", "w_df", "w_svpt", "w_1stIn", "w_1stWon", "w_2ndWon", "w_bpSaved", "w_bpFaced",
         "l_ace", "l_df", "l_svpt", "l_1stIn", "l_1stWon", "l_2ndWon", "l_bpSaved", "l_bpFaced"]


def score_info(score: str):
    sets = re.findall(r"(\d+)-(\d+)(?:\((\d+)\))?", str(score))
    gw = sum(int(a) for a, b, _ in sets)
    gl = sum(int(b) for a, b, _ in sets)
    tb = sum(1 for a, b, t in sets if t or {int(a), int(b)} == {6, 7})
    done = not re.search(r"RET|W/O|DEF|ABD", str(score), re.I)
    return gw, gl, tb, done


def fit(r: pd.Series) -> dict:
    gw, gl, tb, done = score_info(r["score"])
    g = gw + gl
    w = {c: r[f"w_{K.RAW[c]}"] for c in K.BOX}
    l_ = {c: r[f"l_{K.RAW[c]}"] for c in K.BOX}
    out = {"games": g, "tiebreaks": tb, "completed": done}
    sv = w["sv_gms"] + l_["sv_gms"]
    out["B5_pass"] = bool(pd.isna(sv) or abs(sv - (g - tb)) <= 1 or abs(sv - g) <= 1)
    played = (g - tb) - (0 if done else 1)
    pts = w["svpt"] + l_["svpt"]
    out["B9_pass"] = bool(pts >= 4.5 * played)
    out["pts_per_game"] = round(pts / g, 2) if g else None
    out["svgms_sum"] = sv
    if done and tb == 0 and pd.notna(sv):
        bw, bl = w["bp_faced"] - w["bp_saved"], l_["bp_faced"] - l_["bp_saved"]
        out["identity"] = bool(w["sv_gms"] - bw + bl == gw)
        out["identity_exchanged"] = bool(l_["sv_gms"] - bl + bw == gw)
    else:
        out["identity"] = out["identity_exchanged"] = None
    pw = w["first_won"] + w["second_won"] + l_["svpt"] - l_["first_won"] - l_["second_won"]
    pl = l_["first_won"] + l_["second_won"] + w["svpt"] - w["first_won"] - w["second_won"]
    out["winner_pts"], out["loser_pts"] = pw, pl
    return out


def main() -> None:
    pd.set_option("display.width", 320)
    pd.set_option("display.max_colwidth", 70)
    rc = pd.read_csv(K.AUDIT / "box_raw_copies.csv")
    sel = rc[rc["same_players"] | (rc["tour"].eq("atp") & rc["copy_event"].eq("Dusseldorf"))]
    print("box_raw_copies rows:", len(sel), "(same players", int(rc["same_players"].sum()), ")")
    raws = []
    for tour in ("atp", "wta"):
        r = K.sackmann(tour)
        r["tour"] = tour
        raws.append(r)
    raw = pd.concat(raws, ignore_index=True)
    for c in RAW16:
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    raw = raw[raw["w_svpt"].fillna(0) >= 20].copy()
    raw["key"] = raw[RAW16].fillna(-1).astype(int).astype(str).agg("|".join, axis=1)

    # groups: every raw row whose key is the key of a selected pair's source or copy match
    def find(tour, event, date, match):
        m = re.match(r"(.+) d\. (.+?) (\S.*)$", match)
        cand = raw[(raw["tour"] == tour) & (raw["tourney_name"] == event) & (raw["tourney_date"].astype(str) == str(date))]
        cand = cand[cand.apply(lambda x: f"{x['winner_name']} d. {x['loser_name']} {x['score']}" == match, axis=1)]
        return cand

    keys = set()
    for _, p in sel.iterrows():
        c = find(p["tour"], p["copy_event"], p["copy_date"], p["copy_match"])
        keys |= set(c["key"])
    groups = raw[raw["key"].isin(keys)].copy()
    s0 = pd.read_parquet(K.S0 / "stage0_matches.parquet",
                         columns=["match_id", "source_file", "source_row", "has_box", "box_status", "status", "tournament_name",
                                  "year"])
    groups = groups.merge(s0, left_on=["_source_file", "_row"], right_on=["source_file", "source_row"], how="left")
    rows = []
    for _, r in groups.iterrows():
        f = fit(r)
        rows.append({"group": r["key"][:40], "tour": r["tour"], "event": r["tourney_name"], "date": r["tourney_date"],
                     "round": r["round"], "match": f"{r['winner_name']} d. {r['loser_name']} {r['score']}",
                     "source_file": r["_source_file"], "source_row": r["_row"], "match_id": r["match_id"],
                     "stage0_has_box": r["has_box"], "stage0_box_status": r["box_status"],
                     "w_svpt": r["w_svpt"], "l_svpt": r["l_svpt"], "w_SvGms": r["w_SvGms"], "l_SvGms": r["l_SvGms"], **f})
    t = pd.DataFrame(rows).sort_values(["group", "date"])
    t["group_id"] = t.groupby("group").ngroup()

    # MCP for any match of a group
    mc = pd.concat([K.mcp("m").assign(tour="atp"), K.mcp("w").assign(tour="wta")])
    notes = []
    for _, r in t.iterrows():
        m = re.match(r"(.+) d\. (.+?) (\d.*|W/O.*)$", r["match"])
        wk, lk = K.name_key(m.group(1)), K.name_key(m.group(2))
        d0 = pd.to_datetime(str(r["date"]), format="%Y%m%d")
        c = mc[(mc["tour"] == r["tour"]) & (mc["pk"] == wk) & (mc["ok"] == lk) & (mc["date"] - d0).dt.days.between(-10, 16)]
        if c.empty:
            notes.append(None)
            continue
        c = c.iloc[0]
        cl = mc[(mc["match_id"] == c["match_id"]) & (mc["pk"] == lk)].iloc[0]
        notes.append(f"MCP {c['match_id']}: W serve_pts {c['serve_pts']} (box {r['w_svpt']}), L {cl['serve_pts']} (box {r['l_svpt']})")
    t["mcp"] = notes

    # verdict per group: the copy is the match whose own score the box does not fit
    def fits_well(x):
        ok = x["B5_pass"] and x["B9_pass"]
        if x["identity"] is not None:
            ok = ok and bool(x["identity"])
        return ok

    t["box_fits_this_score"] = t.apply(fits_well, axis=1)
    out = []
    for gid, g in t.groupby("group_id"):
        fitting = g[g["box_fits_this_score"]]
        if len(fitting) == 1:
            genuine = fitting.index[0]
            for i, r in g.iterrows():
                out.append((i, "genuine" if i == genuine else "copy"))
        else:
            for i, r in g.iterrows():
                out.append((i, "undecided"))
    v = dict(out)
    t["role"] = [v[i] for i in t.index]
    t.to_csv(K.OUT / "f4_groups.csv", index=False)
    show = ["group_id", "tour", "event", "date", "round", "match", "stage0_has_box", "games", "tiebreaks", "svgms_sum",
            "B5_pass", "B9_pass", "pts_per_game", "identity", "identity_exchanged", "winner_pts", "loser_pts", "mcp", "role"]
    print(t[show].to_string())
    print(t.groupby("role").size().to_dict())


if __name__ == "__main__":
    main()
