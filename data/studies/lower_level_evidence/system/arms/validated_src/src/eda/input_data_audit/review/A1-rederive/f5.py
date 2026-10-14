"""F5: Roland Garros 2025 (and 2026) box scores from RG's own key statistics against Stage 0 (Sackmann 2025, TML 2026)
and against RG's own point-by-point.

Nine counts per player from keystats set0:
  ace = Aces; df = Double Faults; svpt, first_in = 'First Serve' (in / served); first_won = 'Win On 1st Serve' numerator;
  second_won = 'Win On 2nd Serve' numerator; bp_faced, bp_saved = the opponent's 'Break Points Won' (denominator,
  denominator - numerator); sv_gms = the opponent's 'Break Points Converted Games' denominator (return games).
Consistency: 'Win On 2nd Serve' denominator = svpt - first_in; 'Receiving Points Won' denominator = opponent's svpt;
'Total Points Won' = serve points won + return points won.
Point-by-point (points.parquet): svpt, first_in (serve 1), first_won, second_won, aces (result A), dfs (result DF),
service games (distinct set/game served).
Writes f5_rg_keystats_boxes.csv, f5_rg_vs_stage0.csv (per player row) and prints agreement.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

pd.set_option("display.width", 260)
pd.set_option("display.max_rows", 200)
ks = pd.read_parquet(R.INFOSYS / "keystats.parquet")
ks = ks[(ks["slam"] == "RG") & (ks["set_key"] == "set0")]
im = pd.read_parquet(R.INFOSYS / "matches.parquet")
im = im[im["slam"] == "RG"]
FRAC = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")


def frac(v):
    m = FRAC.match(str(v))
    return (int(m.group(1)), int(m.group(2))) if m else (np.nan, np.nan)


def num(v):
    try:
        return float(str(v).strip())
    except ValueError:
        return np.nan


rows = []
for (yr, mid), g in ks.groupby(["year", "match_id"]):
    st = {r["name"]: (r["player1"], r["player2"]) for r in g.to_dict("records")}
    need = ["Aces", "Double Faults", "First Serve", "Win On 1st Serve", "Win On 2nd Serve", "Break Points Won",
            "Break Points Converted Games", "Receiving Points Won", "Total Points Won"]
    if not all(n in st for n in need):
        continue
    out = {"year": int(yr), "match_id": mid}
    for k, o, j in (("1", "2", 0), ("2", "1", 1)):
        fi, sv = frac(st["First Serve"][j])
        fw, fd = frac(st["Win On 1st Serve"][j])
        sw, sd = frac(st["Win On 2nd Serve"][j])
        bpw_o, bp_o = frac(st["Break Points Won"][1 - j])
        cg_o, rg_o = frac(st["Break Points Converted Games"][1 - j])
        rw, rd_ = frac(st["Receiving Points Won"][j])
        out.update({f"p{k}_ace": num(st["Aces"][j]), f"p{k}_df": num(st["Double Faults"][j]), f"p{k}_svpt": sv,
                    f"p{k}_first_in": fi, f"p{k}_first_won": fw, f"p{k}_second_won": sw, f"p{k}_sv_gms": rg_o,
                    f"p{k}_bp_faced": bp_o, f"p{k}_bp_saved": bp_o - bpw_o,
                    f"p{k}_chk_first_den": fd == fi, f"p{k}_chk_second_den": sd == sv - fi,
                    f"p{k}_ret_won": rw, f"p{k}_ret_den": rd_, f"p{k}_total": num(st["Total Points Won"][j])})
    for k, o in (("1", "2"), ("2", "1")):
        out[f"p{k}_chk_ret_den"] = out[f"p{k}_ret_den"] == out[f"p{o}_svpt"]
        out[f"p{k}_chk_total"] = out[f"p{k}_total"] == out[f"p{k}_first_won"] + out[f"p{k}_second_won"] + out[f"p{k}_ret_won"]
    rows.append(out)
K = pd.DataFrame(rows)
K = K.merge(im[["year", "match_id", "tour", "draw", "round_from_code", "p1_name", "p1_first_name", "p1_last_name",
                "p2_name", "p2_first_name", "p2_last_name", "match_winner", "match_status", "is_match_complete"]]
            .assign(year=lambda d: d["year"].astype(int)), on=["year", "match_id"], how="left")
chk = [c for c in K.columns if "_chk_" in c]
print("RG keystats matches:", K.groupby(["year", "tour", "draw"]).size().to_dict())
print("internal consistency (share true):", {c: round(float(K[c].mean()), 4) for c in chk})

# ---------------- point-by-point
pts = pd.read_parquet(R.INFOSYS / "points.parquet")
pts = pts[pts["slam"] == "RG"]
pb = []
for (yr, mid), g in pts.groupby(["year", "match_id"]):
    o = {"year": int(yr), "match_id": mid}
    for k in ("1", "2"):
        s = g[g["server"].astype(str) == k]
        o[f"b{k}_svpt"] = len(s)
        o[f"b{k}_first_in"] = int((s["serve"].astype(str) == "1").sum())
        o[f"b{k}_first_won"] = int(((s["serve"].astype(str) == "1") & (s["scorer"].astype(str) == k)).sum())
        o[f"b{k}_second_won"] = int(((s["serve"].astype(str) == "2") & (s["scorer"].astype(str) == k)).sum())
        o[f"b{k}_ace"] = int((s["result"] == "A").sum())
        o[f"b{k}_df"] = int((s["result"] == "DF").sum())
        o[f"b{k}_sv_gms"] = int(s.groupby(["set", "game"]).ngroups)
    pb.append(o)
PB = pd.DataFrame(pb)
KP = K.merge(PB, on=["year", "match_id"], how="inner")
print("\nkeystats vs RG point-by-point, exact per player row:")
for b in ("svpt", "first_in", "first_won", "second_won", "ace", "df", "sv_gms"):
    e = pd.concat([KP[f"p1_{b}"].eq(KP[f"b1_{b}"]), KP[f"p2_{b}"].eq(KP[f"b2_{b}"])])
    print(f"  {b}: {e.mean():.4f} (n={len(e)})")

K.to_csv(R.OUT / "f5_rg_keystats_boxes.csv", index=False)

# ---------------- link to Stage 0 (RG 2025: Sackmann; RG 2026: TML)
m, p = R.stage0()
rg = m[m["tournament_name"].str.contains("Roland Garros", na=False) & m["year"].isin([2025, 2026])]
print("\nStage 0 RG rows:", rg.groupby(["year", "tour", "qualifying", "source"]).size().to_dict())
pp = p[p["match_id"].isin(rg["match_id"])].merge(rg[["match_id", "year", "tour", "qualifying", "round", "source", "has_box"]],
                                                  on="match_id", suffixes=("", "_m"))
pp["last"] = pp["player_name"].map(lambda x: R.nkey(x).split()[-1] if R.nkey(x) else "")
pp["first"] = pp["player_name"].map(lambda x: R.nkey(x)[:1])
links = []
for r in K.to_dict("records"):
    tour = {"M": "atp", "W": "wta"}.get(r["tour"])
    q = r["draw"] == "qual"
    c = pp[(pp["year"].eq(r["year"])) & (pp["tour"].eq(tour)) & (pp["qualifying"].eq(q))]
    for k, o in (("1", "2"), ("2", "1")):
        ln = R.nkey(r[f"p{k}_last_name"])
        fn = R.nkey(r[f"p{k}_first_name"])[:1]
        olast = R.nkey(r[f"p{o}_last_name"])
        okn = np.array([R.nkey(x).endswith(" " + ln) or all(t in R.nkey(x).split() for t in ln.split())
                        for x in c["player_name"]], dtype=bool)
        hit = c[okn & c["first"].eq(fn).to_numpy(dtype=bool)]
        oko = np.array([all(t in R.nkey(x).split() for t in olast.split()) for x in c["player_name"]], dtype=bool)
        hit = hit[hit["opponent_id"].isin(c.loc[oko, "player_id"])]
        if len(hit) != 1:
            continue
        h = hit.iloc[0]
        row = {"year": r["year"], "tour": tour, "qualifying": q, "rg_match": r["match_id"], "round": r["round_from_code"],
               "match_id": h["match_id"], "player_id": h["player_id"], "player_name": h["player_name"],
               "source": h["source"], "s0_has_box": h["has_box"]}
        for b in R.BOX:
            row[f"rg_{b}"] = r[f"p{k}_{b}"]
            row[f"s0_{b}"] = h[b]
        links.append(row)
L = pd.DataFrame(links)
L.to_csv(R.OUT / "f5_rg_vs_stage0.csv", index=False)
print("linked player rows:", L.groupby(["year", "tour", "qualifying", "source"]).size().to_dict())
Lb = L[L["s0_has_box"].eq(True)]
res = []
for (yr, tour, q, src), d in Lb.groupby(["year", "tour", "qualifying", "source"]):
    o = {"year": yr, "tour": tour, "qualifying": q, "source": src, "rows": len(d)}
    for b in R.BOX:
        o[b] = round(float(d[f"rg_{b}"].eq(d[f"s0_{b}"]).mean()), 3)
    o["all9"] = round(float(np.all([d[f"rg_{b}"].eq(d[f"s0_{b}"]) for b in R.BOX], axis=0).mean()), 3)
    o["all8_no_svgms"] = round(float(np.all([d[f"rg_{b}"].eq(d[f"s0_{b}"]) for b in R.BOX if b != "sv_gms"], axis=0).mean()), 3)
    o["first_in_pct_rg"] = round(100 * d["rg_first_in"].sum() / d["rg_svpt"].sum(), 1)
    o["first_in_pct_s0"] = round(100 * d["s0_first_in"].sum() / d["s0_svpt"].sum(), 1)
    o["svpt_equal"] = round(float(d["rg_svpt"].eq(d["s0_svpt"]).mean()), 3)
    res.append(o)
A = pd.DataFrame(res)
A.to_csv(R.OUT / "f5_agreement.csv", index=False)
print(A.to_string())
print(L[L["player_name"].str.contains("Tu", na=False) & L["qualifying"]][["year", "round", "player_name"] +
       [f"{x}_{b}" for b in ("svpt", "first_in", "first_won", "second_won") for x in ("rg", "s0")]].to_string())
