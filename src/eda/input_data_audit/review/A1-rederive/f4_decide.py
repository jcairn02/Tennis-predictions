"""F4 step 2: decide, per cross-match repeat of a box between the same two players (and the Dusseldorf 2012 group),
which row carries a box that is not its own.

Per row (all from the raw Sackmann row):
  * break-margin test (needs no service games): with bc = breaks conceded (bp_faced - bp_saved), a genuine box gives
    |(gw - gl) - 2 (bc_l - bc_w)| <= 1 over the non-tiebreak games (each player serves half the games, +-1);
  * points per game: total serve points / non-tiebreak games played (WTA norm about 6.2; a box from a shorter match
    reads high, from a longer match low);
  * games identity where service games are present (f4.py fits_score);
  * independent records: Sackmann's Slam point-by-point and the MCP, the MCP linked only when its tournament name
    matches the event and its date lies within 21 days after the tournament date.
Decision (pair): a record that agrees with one row and/or contradicts the other decides. Otherwise the internal tests
decide only if the box passes every test on one row and fails the break-margin test on the other and its points per
game lie outside 4.8-8.0 there. Else undecided.
Writes f4_pairs.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

pd.set_option("display.width", 300)
pd.set_option("display.max_colwidth", 70)
pd.set_option("display.max_rows", 300)
X = pd.read_csv(R.OUT / "f4_cross_groups.csv")
same = X[X["same_players"]].copy()
dus = X[X["event"].eq("Dusseldorf")].copy()

frames = []
for tour, pats in (("atp", ["atp_matches_[0-9]*.parquet", "atp_matches_qual_chall_*.parquet"]),
                   ("wta", ["wta_matches_[0-9]*.parquet", "wta_matches_qual_itf_*.parquet"])):
    for pat in pats:
        frames.append(R.sack(tour, pat))
S = pd.concat(frames, ignore_index=True).set_index(["_source_file", "_row"])

mcp = pd.concat([R.mcp_overview("m"), R.mcp_overview("w")], ignore_index=True)
SLAM = {"Australian Open": "ausopen", "Roland Garros": "frenchopen", "Wimbledon": "wimbledon", "US Open": "usopen"}


def tourn_key(x):
    return R.nkey(str(x)).replace(" ", "")


def mcp_check(raw):
    wk, lk = R.nkey(raw["winner_name"]), R.nkey(raw["loser_name"])
    c = mcp[mcp["pkey"].isin([wk, lk])]
    out = []
    for mid, g in c.groupby("match_id"):
        if set(g["pkey"]) != {wk, lk}:
            continue
        if tourn_key(g["tournament"].iloc[0])[:6] != tourn_key(raw["tourney_name"])[:6]:
            continue
        d = (g["mdate"].iloc[0] - raw["tdate"]).days
        if not (-2 <= d <= 21):
            continue
        a, b = g[g["pkey"].eq(wk)].iloc[0], g[g["pkey"].eq(lk)].iloc[0]
        comp = [(raw["w_svpt"], a["serve_pts"]), (raw["l_svpt"], b["serve_pts"]), (raw["w_ace"], a["aces"]),
                (raw["l_ace"], b["aces"]), (raw["w_df"], a["dfs"]), (raw["l_df"], b["dfs"]),
                (raw["w_first_in"], a["first_in"]), (raw["l_first_in"], b["first_in"])]
        close = sum(abs(x - y) <= 2 for x, y in comp)
        out.append(("agrees" if close >= 7 else ("differs" if close <= 4 else "unclear"),
                    f"MCP {mid}: {close}/8 within 2 (svpt {int(raw['w_svpt'])}/{int(raw['l_svpt'])} vs "
                    f"{int(a['serve_pts'])}/{int(b['serve_pts'])})"))
    return out


def pbp_check(raw):
    slam = SLAM.get(raw["tourney_name"])
    if not slam:
        return []
    base = R.DUMP / "points" / "sackmann_archive" / "slam_pointbypoint"
    mf, pf = base / f"{raw['tdate'].year}-{slam}-matches.parquet", base / f"{raw['tdate'].year}-{slam}-points.parquet"
    if not mf.exists():
        return []
    mt = pd.read_parquet(mf)
    wk, lk = R.nkey(raw["winner_name"]), R.nkey(raw["loser_name"])
    hit = None
    for x in mt.to_dict("records"):
        a, b = R.nkey(x["player1"]), R.nkey(x["player2"])

        def same(u, v):
            return u == v or (u.split()[-1:] == v.split()[-1:] and u[:1] == v[:1])
        if same(a, wk) and same(b, lk):
            hit = (x["match_id"], 1, 2)
        elif same(b, wk) and same(a, lk):
            hit = (x["match_id"], 2, 1)
        if hit:
            break
    if not hit:
        return []
    q = pd.read_parquet(pf)
    q = q[q["match_id"].eq(hit[0])].copy()
    for c in ("PointServer", "PointWinner"):
        q[c] = pd.to_numeric(q[c], errors="coerce")
    q = q[q["PointServer"].isin([1, 2])]
    if q.empty:
        return []
    sw, sl = int((q["PointServer"] == hit[1]).sum()), int((q["PointServer"] == hit[2]).sum())
    ww = int(((q["PointServer"] == hit[1]) & (q["PointWinner"] == hit[1])).sum())
    wl = int(((q["PointServer"] == hit[2]) & (q["PointWinner"] == hit[2])).sum())
    bw, bl = raw["w_first_won"] + raw["w_second_won"], raw["l_first_won"] + raw["l_second_won"]
    ok = abs(sw - raw["w_svpt"]) <= 2 and abs(sl - raw["l_svpt"]) <= 2 and abs(ww - bw) <= 2 and abs(wl - bl) <= 2
    far = abs(sw - raw["w_svpt"]) + abs(sl - raw["l_svpt"]) > 8
    return [("agrees" if ok else ("differs" if far else "unclear"),
             f"SlamPBP {hit[0]}: svpt {sw}/{sl} won {ww}/{wl} vs box {int(raw['w_svpt'])}/{int(raw['l_svpt'])} "
             f"{int(bw)}/{int(bl)}")]


def internal(raw):
    gw, gl, tw, tl, ntb, ret = R.games_of(raw["score"])
    bcw, bcl = raw["w_bp_faced"] - raw["w_bp_saved"], raw["l_bp_faced"] - raw["l_bp_saved"]
    margin = (gw - tw) - (gl - tl)
    bm = abs(margin - 2 * (bcl - bcw)) <= (2 if ret else 1)
    games = gw + gl - ntb - (1 if ret else 0)
    tbp = 0
    for tok in str(raw["score"]).split():
        mm = __import__("re").match(r"^(\d+)-(\d+)\((\d+)\)$", tok)
        if mm:
            n = int(mm.group(3))
            tbp += n + max(7, n + 2)
    ppg = (raw["w_svpt"] + raw["l_svpt"] - tbp) / games if games > 0 else np.nan
    return bm, ppg


rows = []
for grp, g in pd.concat([same, dus]).groupby("group"):
    g = g.sort_values(["date", "_row"])
    recs = []
    for r in g.to_dict("records"):
        raw = S.loc[(r["_source_file"], r["_row"])]
        ind = mcp_check(raw) + pbp_check(raw)
        bm, ppg = internal(raw)
        st = [x[0] for x in ind]
        recs.append({**{k: r[k] for k in ("group", "tour", "_source_file", "_row", "event", "date", "round", "match",
                                           "score", "fits_score", "same_players")},
                     "break_margin_ok": bm, "pts_per_game": round(ppg, 2),
                     "record": "agrees" if "agrees" in st else ("differs" if "differs" in st else ("unclear" if st else "none")),
                     "record_detail": "; ".join(x[1] for x in ind)})
    # decision
    agree = [i for i, x in enumerate(recs) if x["record"] == "agrees"]
    differ = [i for i, x in enumerate(recs) if x["record"] == "differs"]
    normal = [i for i, x in enumerate(recs) if x["break_margin_ok"] and 4.8 <= x["pts_per_game"] <= 8.5
              and x["fits_score"] is not False and not (isinstance(x["fits_score"], float) and False)]
    impossible = [i for i, x in enumerate(recs) if x["pts_per_game"] < 4.0 or x["pts_per_game"] > 10.5]
    fit_t = [i for i, x in enumerate(recs) if x["fits_score"] is True or x["fits_score"] == 1.0]
    fit_f = [i for i, x in enumerate(recs) if x["fits_score"] is False or x["fits_score"] == 0.0]
    double = [i for i, x in enumerate(recs) if not x["break_margin_ok"] and not (4.8 <= x["pts_per_game"] <= 8.5)]
    copy, reason = set(), ""
    if len(agree) == 1 and not any(recs[i]["record"] == "agrees" for i in range(len(recs)) if i != agree[0]):
        copy = set(range(len(recs))) - set(agree)
        reason = "R1 independent record agrees with " + recs[agree[0]]["event"] + " " + str(recs[agree[0]]["date"])
    elif len(agree) > 1:
        reason = "records agree with two rows: undecided"
    elif differ and len(recs) == 2 and len(differ) == 1 and (1 - differ[0]) in normal:
        copy = set(differ)
        reason = "R1 independent record contradicts " + recs[differ[0]]["event"] + "; the box fits the other row"
    elif len(recs) == 2 and len(fit_t) == 1 and len(fit_f) == 1 and not differ[:0]:
        copy = set(fit_f)
        reason = "R2 exact games identity fits " + recs[fit_t[0]]["event"] + " only"
    elif len(recs) == 2 and len(impossible) == 1 and (1 - impossible[0]) in normal:
        copy = set(impossible)
        reason = ("R3 impossible serve points per game on " + recs[impossible[0]]["event"]
                  + f" ({recs[impossible[0]]['pts_per_game']}); normal on the other")
    elif len(recs) == 2 and len(double) == 1 and (1 - double[0]) in normal:
        copy = set(double)
        reason = ("R4 the box fails the break-margin test and has implausible points per game ("
                  + f"{recs[double[0]]['pts_per_game']}) on " + recs[double[0]]["event"] + "; normal on the other")
    elif len(recs) == 3 and len(fit_t) == 1 and len(fit_f) == 2:
        copy = set(fit_f)
        reason = "R2 exact games identity fits " + recs[fit_t[0]]["event"] + " " + recs[fit_t[0]]["match"] + " only"
    else:
        reason = "undecided: no independent record and the internal tests do not separate the rows"
        if len(impossible) == len(recs):
            reason = "undecided: the box is implausible for every row (fits none)"
    for i, x in enumerate(recs):
        rows.append({**x, "role": "copy" if i in copy else ("genuine" if copy else "undecided"), "reason": reason})
P = pd.DataFrame(rows)
P.to_csv(R.OUT / "f4_pairs.csv", index=False)
print(P[["event", "date", "round", "match", "score", "fits_score", "break_margin_ok", "pts_per_game", "record", "role",
         "record_detail"]].to_string())
d = P[P["same_players"]]
print("same-pair groups:", d["group"].nunique(), " decided:", d.loc[d["role"].eq("copy"), "group"].nunique(),
      " copies:", int(d["role"].eq("copy").sum()))
print("decided by record:", d.loc[d["role"].eq("copy") & d["reason"].str.startswith("independent"), "group"].nunique(),
      " by internal tests:", d.loc[d["role"].eq("copy") & d["reason"].str.startswith("internal"), "group"].nunique())
