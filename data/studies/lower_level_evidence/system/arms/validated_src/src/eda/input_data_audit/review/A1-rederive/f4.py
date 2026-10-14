"""F4: verbatim box repeats in Sackmann's raw files and, for each repeat, which row is the copy.

1. Every raw row with a box (both players' svpt > 0), all Sackmann files (ATP main / qual-chall / futures, WTA main /
   qual-ITF), 2010-2026. Key: the 16 counts other than service games (w then l); a repeat is another row with the same key in either orientation.
2. For each group: same two players or not; for each row: does the box fit that row's own score?
     games identity (holds + breaks of the opponent = games, tiebreak sets added when service games exclude them; or
     service games = all games when they include them), B5 (service games within one of the games), and points per
     game (B9: at least 4.5 serve points per game played).
3. Independent records: MCP (per player serve points, aces, double faults, first serves in) and Sackmann's Slam
   point-by-point (serve points, aces, double faults, points won on serve) for each row of a group.
Decision per group of a same-pair repeat: the copy is the row whose score the box does not fit while it fits the
other's (or the row an independent record contradicts while it confirms the other). Otherwise undecided.
Writes f4_groups.csv (every row of every repeat group) and prints the decisions.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

pd.set_option("display.width", 280)
pd.set_option("display.max_colwidth", 60)
pd.set_option("display.max_rows", 300)

frames = []
for tour, pats in (("atp", ["atp_matches_[0-9]*.parquet", "atp_matches_qual_chall_*.parquet", "atp_matches_futures_*.parquet"]),
                   ("wta", ["wta_matches_[0-9]*.parquet", "wta_matches_qual_itf_*.parquet"])):
    for pat in pats:
        d = R.sack(tour, pat)
        d["tour"] = tour
        frames.append(d)
s = pd.concat(frames, ignore_index=True)
s = s[R.has_box(s) & s["tdate"].dt.year.ge(2009)].copy()
B16 = [b for b in R.BOX if b != "sv_gms"]
cols = [f"{side}_{b}" for side in ("w", "l") for b in B16]
s = s.dropna(subset=cols)
k1 = s[cols].astype(int).astype(str).agg("|".join, axis=1)
k2 = s[[f"{side}_{b}" for side in ("l", "w") for b in B16]].astype(int).astype(str).agg("|".join, axis=1)
s["k"] = np.where(k1 <= k2, k1, k2)
s["flip"] = k1 > k2
dup = s[s["k"].duplicated(keep=False)].copy()
print("rows with a box:", len(s), " rows in repeat groups:", len(dup), " groups:", dup["k"].nunique())


def fits(r):
    gw, gl, tw, tl, ntb, ret = R.games_of(r["score"])
    if pd.isna(r["w_sv_gms"]) or pd.isna(r["l_sv_gms"]):
        played = gw + gl - ntb - (1 if ret else 0)
        b9 = (r["w_svpt"] + r["l_svpt"]) >= 4.5 * played
        # without service games: serve points per game of the score (a box from a shorter match reads low)
        return None, False, None, bool(b9), "", f"{gw}-{gl}"
    hw = r["w_sv_gms"] - (r["w_bp_faced"] - r["w_bp_saved"])
    hl = r["l_sv_gms"] - (r["l_bp_faced"] - r["l_bp_saved"])
    bw = hw + (r["l_bp_faced"] - r["l_bp_saved"])
    bl = hl + (r["w_bp_faced"] - r["w_bp_saved"])
    excl = bw == gw - tw and bl == gl - tl
    incl = (r["w_sv_gms"] + r["l_sv_gms"] == gw + gl) and (gw - tw <= bw <= gw) and (gl - tl <= bl <= gl)
    tol = abs(bw - (gw - tw)) <= 1 and abs(bl - (gl - tl)) <= 1 if ret else False
    sv = r["w_sv_gms"] + r["l_sv_gms"]
    b5 = abs(sv - (gw + gl - ntb)) <= 1 or abs(sv - (gw + gl)) <= 1
    played = gw + gl - ntb - (1 if ret else 0)
    b9 = (r["w_svpt"] + r["l_svpt"]) >= 4.5 * played
    return bool(excl or incl), bool(tol), bool(b5), bool(b9), f"{int(bw)}-{int(bl)}", f"{gw}-{gl}"


rows = []
for k, g in dup.groupby("k"):
    pairs = {frozenset((R.nkey(a), R.nkey(b))) for a, b in zip(g["winner_name"], g["loser_name"])}
    for r in g.to_dict("records"):
        fi, tol, b5, b9, bg, sg = fits(r)
        rows.append({"group": k, "n_in_group": len(g), "same_players": len(pairs) == 1, "tour": r["tour"],
                     "_source_file": r["_source_file"], "_row": r["_row"], "event": r["tourney_name"],
                     "date": r["tdate"].date(), "level": r["tourney_level"], "round": r["round"],
                     "match": f"{r['winner_name']} d. {r['loser_name']}", "score": r["score"],
                     "fits_score": fi, "fits_if_retired_tol1": tol, "b5_ok": b5, "b9_ok": b9, "box_games": bg,
                     "score_games": sg, "svpt_total": r["w_svpt"] + r["l_svpt"]})
G = pd.DataFrame(rows).sort_values(["group", "date", "_row"])

# ---------------- independent records per row (MCP, Slam PBP)
mcp = pd.concat([R.mcp_overview("m").assign(g="m"), R.mcp_overview("w").assign(g="w")], ignore_index=True)
mcp_by_pair = {}
for mid, g in mcp.groupby("match_id"):
    if len(g) == 2:
        mcp_by_pair.setdefault(frozenset(g["pkey"]), []).append((mid, g))
SLAM = {"Australian Open": "ausopen", "Roland Garros": "frenchopen", "Wimbledon": "wimbledon", "US Open": "usopen"}
pbp_cache = {}


def pbp(year, slam):
    key = (year, slam)
    if key not in pbp_cache:
        base = R.DUMP / "points" / "sackmann_archive" / "slam_pointbypoint"
        mf, pf = base / f"{year}-{slam}-matches.parquet", base / f"{year}-{slam}-points.parquet"
        pbp_cache[key] = (pd.read_parquet(mf), pd.read_parquet(pf)) if mf.exists() else (None, None)
    return pbp_cache[key]


s_idx = s.set_index(["_source_file", "_row"])
ind = []
for r in G.to_dict("records"):
    raw = s_idx.loc[(r["_source_file"], r["_row"])]
    wn, ln = raw["winner_name"], raw["loser_name"]
    box = {"w": {b: raw[f"w_{b}"] for b in R.BOX}, "l": {b: raw[f"l_{b}"] for b in R.BOX}}
    verdicts = []
    # MCP
    for mid, g in mcp_by_pair.get(frozenset((R.nkey(wn), R.nkey(ln))), []):
        md = g["mdate"].iloc[0]
        if pd.isna(md) or not (-5 <= (md - raw["tdate"]).days <= 30):
            continue
        gw_, gl_ = g[g["pkey"].eq(R.nkey(wn))].iloc[0], g[g["pkey"].eq(R.nkey(ln))].iloc[0]
        comp = [(box["w"]["svpt"], gw_["serve_pts"]), (box["l"]["svpt"], gl_["serve_pts"]), (box["w"]["ace"], gw_["aces"]),
                (box["l"]["ace"], gl_["aces"]), (box["w"]["df"], gw_["dfs"]), (box["l"]["df"], gl_["dfs"]),
                (box["w"]["first_in"], gw_["first_in"]), (box["l"]["first_in"], gl_["first_in"])]
        close = sum(abs(a - b) <= 2 for a, b in comp)
        verdicts.append(f"MCP {mid}: {close}/8 within 2 (svpt {int(box['w']['svpt'])}/{int(box['l']['svpt'])} vs "
                        f"{int(gw_['serve_pts'])}/{int(gl_['serve_pts'])})")
    # Slam PBP
    slam = SLAM.get(raw["tourney_name"])
    if slam:
        mt, pt = pbp(raw["tdate"].year, slam)
        if mt is not None:
            hit = None
            for x in mt.to_dict("records"):
                if R.nkey(x["player1"]) == R.nkey(wn) and R.nkey(x["player2"]) == R.nkey(ln):
                    hit = (x["match_id"], 1, 2)
                elif R.nkey(x["player2"]) == R.nkey(wn) and R.nkey(x["player1"]) == R.nkey(ln):
                    hit = (x["match_id"], 2, 1)
                if hit:
                    break
            if hit:
                q = pt[pt["match_id"].eq(hit[0])].copy()
                for c in ("PointServer", "PointWinner"):
                    q[c] = pd.to_numeric(q[c], errors="coerce")
                q = q[q["PointServer"].isin([1, 2])]
                if len(q):
                    sw = int((q["PointServer"] == hit[1]).sum())
                    sl = int((q["PointServer"] == hit[2]).sum())
                    ww = int(((q["PointServer"] == hit[1]) & (q["PointWinner"] == hit[1])).sum())
                    wl = int(((q["PointServer"] == hit[2]) & (q["PointWinner"] == hit[2])).sum())
                    bw_ = box["w"]["first_won"] + box["w"]["second_won"]
                    bl_ = box["l"]["first_won"] + box["l"]["second_won"]
                    ok = abs(sw - box["w"]["svpt"]) <= 2 and abs(sl - box["l"]["svpt"]) <= 2 and abs(ww - bw_) <= 2 and abs(wl - bl_) <= 2
                    verdicts.append(f"SlamPBP {hit[0]}: {'AGREES' if ok else 'DIFFERS'} (svpt {sw}/{sl}, won {ww}/{wl} vs box "
                                    f"{int(box['w']['svpt'])}/{int(box['l']['svpt'])}, {int(bw_)}/{int(bl_)})")
    ind.append("; ".join(verdicts))
G["independent"] = ind
G.to_csv(R.OUT / "f4_groups.csv", index=False)

# ---------------- decisions for same-player groups (and listing of other-player groups)
dec = []
for k, g in G.groupby("group"):
    g = g.sort_values(["date", "_row"])
    fit = g["fits_score"] | g["fits_if_retired_tol1"]
    agrees = g["independent"].str.contains("AGREES") | g["independent"].str.contains(r"MCP [^;]*: [78]/8", regex=True)
    differs = g["independent"].str.contains("DIFFERS") | g["independent"].str.contains(r"MCP [^;]*: [0-4]/8", regex=True)
    copy_rows, reason = [], ""
    if len(g) == 2:
        a, b = g.iloc[0], g.iloc[1]
        fa, fb = bool(fit.iloc[0]), bool(fit.iloc[1])
        ia, ib = (bool(agrees.iloc[0]), bool(differs.iloc[0])), (bool(agrees.iloc[1]), bool(differs.iloc[1]))
        if fa and not fb and not ib[0]:
            copy_rows, reason = [1], "box fits the earlier row's score only"
        elif fb and not fa and not ia[0]:
            copy_rows, reason = [0], "box fits the later row's score only"
        elif ia[0] and ib[1]:
            copy_rows, reason = [1], "independent record agrees with the earlier row and contradicts the later"
        elif ib[0] and ia[1]:
            copy_rows, reason = [0], "independent record agrees with the later row and contradicts the earlier"
        else:
            reason = f"undecided (fits: earlier {fa}, later {fb})"
        # strengthen / contradict with records
        if copy_rows:
            c = copy_rows[0]
            gen = 1 - c
            if (differs.iloc[gen]) or (agrees.iloc[c]):
                reason += " BUT the independent record contradicts this"
                copy_rows = []
    else:
        reason = f"group of {len(g)}"
    for i, r in enumerate(g.to_dict("records")):
        dec.append({**r, "role": ("copy" if i in copy_rows else ("genuine" if copy_rows else "undecided")), "reason": reason})
D = pd.DataFrame(dec)
D.to_csv(R.OUT / "f4_decisions.csv", index=False)
show = ["tour", "event", "date", "round", "match", "score", "box_games", "score_games", "fits_score", "b5_ok", "b9_ok",
        "role", "reason", "independent"]
print(D[D["same_players"]][show].to_string())
print(D[~D["same_players"]][["tour", "event", "date", "round", "match", "score", "fits_score", "n_in_group"]].to_string())
print("same-player groups:", D.loc[D["same_players"], "group"].nunique(),
      " decided:", D.loc[D["same_players"] & D["role"].eq("copy"), "group"].nunique())
