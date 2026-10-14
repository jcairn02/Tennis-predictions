"""F2 step 2: independent records for the F2 matches that the WTA API does not hold.

Sources (each gives, per player: serve points, serve points won, aces, double faults, first serves in where held):
  * Match Charting Project Overview totals (m/w);
  * Sackmann's Slam point-by-point (2011-2024): per point server / winner / ace / double fault / serve number;
  * Roland Garros & AO infosys point-by-point (2025-26): server, serve (1/2), scorer, result (A ace, DF);
  * ATP key statistics 2025 (sirgenkii infotennis) with atp_results names.
For each match the Stage 0 box under each player is compared with the source's counts, as recorded and exchanged.
Writes f2_external.csv.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

pd.set_option("display.width", 260)
pd.set_option("display.max_colwidth", 70)
d2 = pd.read_csv(R.OUT / "f2_internal.csv")
m, p = R.stage0()
mi = m.set_index("match_id")


def toks(name):
    return [t for t in R.nkey(name).split() if len(t) > 1]


def same_person(s0_name, src_name):
    a = R.nkey(s0_name).split()
    b = R.nkey(src_name).split()
    if not a or not b:
        return False
    full = [t for t in b if len(t) > 1]
    initials = [t for t in b if len(t) == 1]
    if not full:
        return False
    if not set(full) <= set(a):
        # surname-only containment (source gives only the surname or a different first name spelling)
        if b[-1] not in a:
            return False
    if initials and not a[0].startswith(initials[0]):
        return False
    return True


def compare(rec, src):
    """rec: {'W': box, 'L': box} from Stage 0; src: {'W': counts, 'L': counts} by player. Returns per-assignment
    (matches, compared) over the counts the source holds."""
    keys = [k for k in src["W"] if k in R.BOX + ["spw"] and pd.notna(src["W"][k]) and pd.notna(src["L"][k])]

    def val(box, k):
        return box["first_won"] + box["second_won"] if k == "spw" else box[k]
    n_rec = sum(val(rec["W"], k) == src["W"][k] for k in keys) + sum(val(rec["L"], k) == src["L"][k] for k in keys)
    n_exc = sum(val(rec["L"], k) == src["W"][k] for k in keys) + sum(val(rec["W"], k) == src["L"][k] for k in keys)
    detail = {k: (val(rec["W"], k), val(rec["L"], k), src["W"][k], src["L"][k]) for k in keys}
    return n_rec, n_exc, 2 * len(keys), detail


# ---------------- sources
mcp = pd.concat([R.mcp_overview("m").assign(g="m"), R.mcp_overview("w").assign(g="w")], ignore_index=True)


def from_mcp(row, Wn, Ln, date):
    c = mcp[(mcp["mdate"] - date).dt.days.between(-5, 30)]
    for mid, g in c.groupby("match_id"):
        names = g["player"].tolist()
        if len(names) != 2:
            continue
        a = [n for n in names if same_person(Wn, n)]
        b = [n for n in names if same_person(Ln, n)]
        if len(a) == 1 and len(b) == 1 and a[0] != b[0]:
            gw, gl = g[g["player"].eq(a[0])].iloc[0], g[g["player"].eq(b[0])].iloc[0]

            def cnt(x):
                return {"svpt": x["serve_pts"], "ace": x["aces"], "df": x["dfs"], "first_in": x["first_in"],
                        "first_won": x["first_won"], "second_won": x["second_won"], "bp_faced": x["bk_pts"],
                        "bp_saved": x["bp_saved"]}
            return f"MCP {mid}", {"W": cnt(gw), "L": cnt(gl)}
    return None


SLAM = {"Australian Open": "ausopen", "Roland Garros": "frenchopen", "Wimbledon": "wimbledon", "US Open": "usopen",
        "Us Open": "usopen"}


def from_slam_pbp(row, Wn, Ln, year, event):
    slam = SLAM.get(event)
    if not slam:
        return None
    base = R.DUMP / "points" / "sackmann_archive" / "slam_pointbypoint"
    mf, pf = base / f"{year}-{slam}-matches.parquet", base / f"{year}-{slam}-points.parquet"
    if not mf.exists():
        return None
    mt = pd.read_parquet(mf)
    hit = None
    for r in mt.to_dict("records"):
        if same_person(Wn, r["player1"]) and same_person(Ln, r["player2"]):
            hit = (r["match_id"], 1, 2)
        elif same_person(Wn, r["player2"]) and same_person(Ln, r["player1"]):
            hit = (r["match_id"], 2, 1)
        if hit:
            break
    if not hit:
        return None
    pt = pd.read_parquet(pf)
    pt = pt[pt["match_id"].eq(hit[0])].copy()
    for c in ["PointServer", "PointWinner", "P1Ace", "P2Ace", "P1DoubleFault", "P2DoubleFault", "ServeIndicator",
              "PointNumber"]:
        pt[c] = pd.to_numeric(pt[c], errors="coerce")
    pt = pt[pt["PointServer"].isin([1, 2])]
    if pt.empty:
        return None

    def cnt(k):
        s = pt[pt["PointServer"].eq(k)]
        out = {"svpt": len(s), "spw": int((s["PointWinner"] == k).sum()),
               "ace": int(s[f"P{k}Ace"].sum()), "df": int(s[f"P{k}DoubleFault"].sum())}
        if s["ServeIndicator"].notna().all() and s["ServeIndicator"].isin([1, 2]).all():
            out["first_in"] = int((s["ServeIndicator"] == 1).sum())
        return out
    return f"slam_pbp {hit[0]}", {"W": cnt(hit[1]), "L": cnt(hit[2])}


ipts = pd.read_parquet(R.INFOSYS / "points.parquet")
imat = pd.read_parquet(R.INFOSYS / "matches.parquet")


def from_infosys(row, Wn, Ln, year, event):
    slam = {"Australian Open": "AO", "Roland Garros": "RG"}.get(event)
    if not slam:
        return None
    x = imat[(imat["slam"].eq(slam)) & (imat["year"].astype(str).eq(str(year)))]
    hit = None
    for r in x.to_dict("records"):
        if not isinstance(r["p1_name"], str):
            continue
        if same_person(Wn, r["p1_name"]) and same_person(Ln, r["p2_name"]):
            hit = (r["match_id"], "1", "2")
        elif same_person(Wn, r["p2_name"]) and same_person(Ln, r["p1_name"]):
            hit = (r["match_id"], "2", "1")
        if hit:
            break
    if not hit:
        return None
    pt = ipts[(ipts["slam"].eq(slam)) & (ipts["year"].astype(str).eq(str(year))) & (ipts["match_id"].eq(hit[0]))]
    if pt.empty:
        return None

    def cnt(k):
        s = pt[pt["server"].astype(str).eq(k)]
        return {"svpt": len(s), "spw": int((s["scorer"].astype(str) == k).sum()),
                "ace": int((s["result"] == "A").sum()), "df": int((s["result"] == "DF").sum()),
                "first_in": int((s["serve"].astype(str) == "1").sum()),
                "first_won": int(((s["serve"].astype(str) == "1") & (s["scorer"].astype(str) == k)).sum())}
    return f"infosys {slam} {year} {hit[0]}", {"W": cnt(hit[1]), "L": cnt(hit[2])}


ks = pd.read_parquet(R.DUMP / "points" / "sirgenkii_infotennis" / "atp_key_stats.parquet")
kr = pd.read_parquet(R.DUMP / "points" / "sirgenkii_infotennis" / "atp_results.parquet")


def from_atp_keystats(row, Wn, Ln, year):
    x = kr[kr["year"].astype(str).eq(str(year))]
    hit = None
    for r in x.to_dict("records"):
        if same_person(Wn, str(r["player1_name"])) and same_person(Ln, str(r["player2_name"])):
            hit = (r, r["player1_id"], r["player2_id"])
        elif same_person(Wn, str(r["player2_name"])) and same_person(Ln, str(r["player1_name"])):
            hit = (r, r["player2_id"], r["player1_id"])
        if hit:
            break
    if not hit:
        return None
    r = hit[0]
    k = ks[(ks["year"].astype(str).eq(str(year))) & (ks["tournament_id"].astype(str).eq(str(r["tournament_id"])))
           & (ks["match_id"].astype(str).eq(str(r["match_id"]))) & (ks["set_n"].astype(str).eq("0"))]
    if k.empty:
        return None

    def cnt(pid):
        s = k[k["player_id"].astype(str).eq(str(pid))]
        if s.empty:
            return None
        s = s.iloc[0]
        out = {"ace": pd.to_numeric(s["aces"], errors="coerce"), "df": pd.to_numeric(s["double_faults"], errors="coerce")}
        for col, key in (("serve1", "first_in"),):
            out[key] = pd.to_numeric(str(s[col]).split("/")[0], errors="coerce") if col in s else np.nan
        if "serve1_pts_won" in s:
            out["first_won"] = pd.to_numeric(str(s["serve1_pts_won"]).split("/")[0], errors="coerce")
        if "serve2_pts_won" in s:
            out["second_won"] = pd.to_numeric(str(s["serve2_pts_won"]).split("/")[0], errors="coerce")
        return out
    a, b = cnt(hit[1]), cnt(hit[2])
    if a is None or b is None:
        return None
    return f"atp_keystats {r['tournament_id']} {r['match_id']}", {"W": a, "L": b}


rows = []
for r in d2.to_dict("records"):
    mid = r["match_id"]
    mr = mi.loc[mid]
    pr = p[p["match_id"].eq(mid)]
    W, L = pr[pr["won"]].iloc[0], pr[~pr["won"]].iloc[0]
    rec = {"W": {b: W[b] for b in R.BOX}, "L": {b: L[b] for b in R.BOX}}
    date, year, event = mr["tournament_date"], int(mr["year"]), mr["tournament_name"]
    found = []
    for fn in (lambda: from_mcp(r, W["player_name"], L["player_name"], date),
               lambda: from_slam_pbp(r, W["player_name"], L["player_name"], year, event),
               lambda: from_infosys(r, W["player_name"], L["player_name"], year, event),
               lambda: from_atp_keystats(r, W["player_name"], L["player_name"], year) if r["tour"] == "atp" else None):
        try:
            res = fn()
        except Exception as ex:  # noqa: BLE001
            res = None
            print("ERR", mid, ex)
        if res:
            found.append(res)
    for src, cnts in found:
        n_rec, n_exc, n, detail = compare(rec, cnts)
        rows.append({"match_id": mid, "api": r["api"], "source": src, "n_compared": n, "match_recorded": n_rec,
                     "match_exchanged": n_exc, "detail": json.dumps({k: [None if pd.isna(x) else float(x) for x in v]
                                                                     for k, v in detail.items()})})
    if not found:
        rows.append({"match_id": mid, "api": r["api"], "source": "none", "n_compared": 0, "match_recorded": 0,
                     "match_exchanged": 0, "detail": ""})
x = pd.DataFrame(rows)
x.to_csv(R.OUT / "f2_external.csv", index=False)
print(x[x["source"].ne("none")][["match_id", "api", "source", "n_compared", "match_recorded", "match_exchanged"]].to_string())
print("matches with an external record:", x.loc[x["source"].ne("none"), "match_id"].nunique(),
      " of which not WTA-API-linked:", x.loc[x["source"].ne("none") & x["api"].eq("no_link"), "match_id"].nunique())
print("no record and no API:", x.loc[x["source"].eq("none") & x["api"].eq("no_link"), "match_id"].tolist())
