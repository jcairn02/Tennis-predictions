"""F3a / F3b scope: the 38 copied Adelaide 2 2022 boxes, their Stage 0 rows, and the WTA API's counts for each match
(event 2030, 2022; Storm Hunter is 'Storm Sanders' in the API's 2022 files), with Stage 0's checks B0-B9 run on the
API counts against the score. Also TML's copy of the event. Writes f3_scope.csv (one row per player row)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

pd.set_option("display.width", 260)
f = pd.read_csv(R.OUT / "f3_matches.csv")
cp = f[f["copy_of_adelaide2021"].eq(True)].copy()
api = R.wta_api(2022)
api = api[api["event"].eq("2030")].copy()
for c in ("kA", "kB", "lkA", "lkB"):
    api[c] = api[c].str.replace("sanders", "hunter", regex=False)
s22 = pd.concat([R.sack("wta", "wta_matches_2022.parquet"), R.sack("wta", "wta_matches_qual_itf_2022.parquet")], ignore_index=True)
s22 = s22.set_index(["_source_file", "_row"])
m, p = R.stage0()
mk = m.assign(k=m["source_file"] + "#" + m["source_row"].astype(str)).set_index("k")


def last_in(sack_name, api_last):
    t = set(R.nkey(sack_name).split())
    return bool(api_last) and all(x in t for x in api_last.split())


def checks(c, o, games, std_tb, completed):
    """B0-B4, B6-B8 per player; B5 / B9 on the pair."""
    bad = []
    for x in (c, o):
        if any(v < 0 for v in x.values()):
            bad.append("B0")
        if x["first_in"] > x["svpt"]:
            bad.append("B1")
        if x["first_won"] > x["first_in"]:
            bad.append("B2")
        if x["second_won"] > x["svpt"] - x["first_in"]:
            bad.append("B3")
        if x["bp_saved"] > x["bp_faced"]:
            bad.append("B4")
        if x["df"] > x["svpt"] - x["first_in"]:
            bad.append("B6")
        if x["ace"] > x["first_won"] + x["second_won"]:
            bad.append("B7")
        if x["bp_faced"] - x["bp_saved"] > x["sv_gms"]:
            bad.append("B8")
    sv = c["sv_gms"] + o["sv_gms"]
    if not (abs(sv - (games - std_tb)) <= 1 or abs(sv - games) <= 1):
        bad.append("B5(service games only)")
    played = games - std_tb - (0 if completed else 1)
    if c["svpt"] + o["svpt"] < 4.5 * played:
        bad.append("B9")
    return bad


rows = []
for r in cp.to_dict("records"):
    raw = s22.loc[(r["_source_file"], r["_row"])]
    mid = mk.loc[f"{r['_source_file']}#{r['_row']}", "match_id"] if f"{r['_source_file']}#{r['_row']}" in mk.index else None
    hits = []
    for x in api[api["draw"].eq("Q" if pd.Series([str(r["round"])]).str.match(r"^Q\d").iloc[0] else "M")].to_dict("records"):
        if last_in(raw["winner_name"], x["lkA"]) and last_in(raw["loser_name"], x["lkB"]):
            hits.append((x, "A", "B"))
        elif last_in(raw["winner_name"], x["lkB"]) and last_in(raw["loser_name"], x["lkA"]):
            hits.append((x, "B", "A"))
    gw, gl, tw, tl, ntb, ret = R.games_of(raw["score"])
    completed = not ret and "w/o" not in str(raw["score"]).lower()
    api_counts, verdict_b, bad = None, "blank", []
    if str(raw["score"]).strip().upper() in ("W/O", "WO"):
        verdict_b = "blank (walkover: no point played)"
    elif len(hits) == 1:
        x, ws, ls = hits[0]
        cw = {b: x[f"{ws}_{b}"] for b in R.BOX}
        cl = {b: x[f"{ls}_{b}"] for b in R.BOX}
        bad = checks(cw, cl, gw + gl, ntb, completed)
        api_counts = (cw, cl)
        verdict_b = "replace from WTA API" if not [b for b in bad if not b.startswith("B5")] else "blank (API counts fail " + ",".join(bad) + ")"
    else:
        verdict_b = f"blank (WTA API: {len(hits)} matches)"
    for side, name, pid in (("w", raw["winner_name"], raw["winner_id"]), ("l", raw["loser_name"], raw["loser_id"])):
        pr = p[(p["match_id"].eq(mid)) & (p["player_id"].eq(f"wta:{pid}"))] if mid else pd.DataFrame()
        row = {"match_id": mid, "player_id": f"wta:{pid}", "_source_file": r["_source_file"], "_row": r["_row"],
               "raw_side": side, "round": r["round"], "player_name": name, "score": raw["score"],
               "copied_from_2021": r["src_match"], "s0_has_box": bool(pr["has_box"].iloc[0]) if len(pr) else None,
               "f3b_action": verdict_b, "api_wmid": hits[0][0]["wmid"] if len(hits) == 1 else "",
               "api_checks_failed": ",".join(bad)}
        for b in R.BOX:
            row[f"copied_{b}"] = raw[f"{side}_{b}"]
            row[f"api_{b}"] = (api_counts[0] if side == "w" else api_counts[1])[b] if api_counts else np.nan
        rows.append(row)
sc = pd.DataFrame(rows)
sc.to_csv(R.OUT / "f3_scope.csv", index=False)
print(sc.groupby("f3b_action").size().to_string())
print("matches:", sc["_row"].nunique(), " player rows:", len(sc), " in Stage 0:", int(sc["match_id"].notna().sum()),
      " with a Stage 0 box:", int(sc["s0_has_box"].eq(True).sum()))
print(sc[sc["s0_has_box"].ne(True)][["match_id", "player_name", "round", "score", "s0_has_box"]].to_string())
print(sc[sc["api_checks_failed"].ne("")][["_row", "player_name", "score", "api_checks_failed"]].to_string())
# Stage 0 status of the 4 genuine and 7 boxless rows
others = f[~f["copy_of_adelaide2021"].eq(True)]
for r in others.to_dict("records"):
    k = f"{r['_source_file']}#{r['_row']}"
    print("non-copy:", r["_row"], r["round"], r["winner"], "-", r["loser"], r["score"], "box:", r["has_box"],
          "| Stage 0:", mk.loc[k, "match_id"] if k in mk.index else None, mk.loc[k, "box_status"] if k in mk.index else None)

# TML's Adelaide 2 2022
t = pd.read_parquet(R.TML / "wta_main" / "2022_wta.parquet")
t = t[t["tourney_name"].astype(str).str.contains("Adelaide", na=False)]
print("TML Adelaide 2022 events:", t.groupby(["tourney_id", "tourney_name", "tourney_date"]).size().to_dict())
t2 = t[t["tourney_date"].astype(str).eq("20220110")]
same = 0
n = 0
for r in t2.to_dict("records"):
    k = [x for x in cp.to_dict("records") if R.nkey(x["winner"]) == R.nkey(r["winner_name"]) and R.nkey(x["loser"]) == R.nkey(r["loser_name"])]
    if not k:
        continue
    raw = s22.loc[(k[0]["_source_file"], k[0]["_row"])]
    n += 1
    same += all(str(r[f"{s}_{c}"]).replace(".0", "") == str(raw[f"{s}_{c}"]).replace(".0", "")
                for s in ("w", "l") for c in ("ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced"))
print(f"TML rows matching a copied Sackmann row by names: {n}; identical box text: {same}")
