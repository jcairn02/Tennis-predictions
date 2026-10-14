"""F5: who is right where Sackmann's RG 2025 differs from RG's key statistics? MCP and Sofascore as third records;
and the key-statistics box simulated through Stage 0's checks and the games identity.

Reads f5_rg_rows.csv (x50_f5.py). Writes f5_third_records.csv and f5_keystats_box_checks.csv; prints agreement.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc  # noqa: E402
import refs  # noqa: E402

pd.set_option("display.width", 260)
pd.set_option("display.max_rows", 200)
j = pd.read_csv(rc.OUT / "f5_rg_rows.csv")
j = j[j["year"].eq(2025) & j["has_box"]].copy()
j["draw"] = np.where(j["qualifying"], "qualifying", "main")

mc = refs.ref_mcp()
sf = refs.ref_sofascore()
out = []
for name, R in (("mcp", mc), ("sofascore", sf)):
    R = R[R["year"].eq(2025)].copy()
    if name == "mcp":
        R = R[R["event"].astype(str).str.contains("Roland|French", case=False)]
    else:
        R = R[R["event"].astype(str).str.contains("French Open|Roland", case=False)]
    x = j.merge(R[["pk", "ok"] + rc.BOX], on=["pk", "ok"], suffixes=("", "_ref"))
    x = x.drop_duplicates(["match_id", "player_id"])
    for (tour, draw), g in x.groupby(["tour", "draw"]):
        for b in ["ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_faced", "bp_saved", "sv_gms"]:
            if g[f"{b}_ref"].notna().sum() == 0:
                continue
            out.append({"third": name, "tour": tour, "draw": draw, "count": b, "rows": int(g[f"{b}_ref"].notna().sum()),
                        "third_eq_keystats": round(float((g[f"{b}_ref"] == g[f"{b}_rg"]).mean()), 3),
                        "third_eq_sackmann": round(float((g[f"{b}_ref"] == g[b]).mean()), 3)})
    # rows where Sackmann and keystats differ on first_in: which one does the third record back?
    d = x[x["first_in"] != x["first_in_rg"]]
    if len(d):
        out.append({"third": name, "tour": "all", "draw": "rows where Sackmann != keystats on first_in",
                    "count": "first_in", "rows": len(d),
                    "third_eq_keystats": round(float((d["first_in_ref"] == d["first_in_rg"]).mean()), 3),
                    "third_eq_sackmann": round(float((d["first_in_ref"] == d["first_in"]).mean()), 3)})
    d = x[x["svpt"] != x["svpt_rg"]]
    if len(d):
        out.append({"third": name, "tour": "all", "draw": "rows where Sackmann != keystats on svpt",
                    "count": "svpt", "rows": len(d),
                    "third_eq_keystats": round(float((d["svpt_ref"] == d["svpt_rg"]).mean()), 3),
                    "third_eq_sackmann": round(float((d["svpt_ref"] == d["svpt"]).mean()), 3)})
T = pd.DataFrame(out)
T.to_csv(rc.OUT / "f5_third_records.csv", index=False)
print(T.to_string(index=False))

# key-statistics box through Stage 0's checks, per match (both players)
m, p = rc.stage0()
both = j.groupby("match_id").filter(lambda g: len(g) == 2)
res = []
for mid, g in both.groupby("match_id"):
    s0 = m[m["match_id"] == mid].iloc[0]
    pw = p[(p["match_id"] == mid) & p["won"]].iloc[0]
    pl = p[(p["match_id"] == mid) & ~p["won"]].iloc[0]
    gw_ = g[g["player_id"] == pw["player_id"]]
    gl_ = g[g["player_id"] == pl["player_id"]]
    if len(gw_) != 1 or len(gl_) != 1:
        continue
    wb = pd.DataFrame([{b: gw_.iloc[0][f"{b}_rg"] for b in rc.BOX}])
    lb = pd.DataFrame([{b: gl_.iloc[0][f"{b}_rg"] for b in rc.BOX}])
    c = rc.box_checks(wb, lb, pd.Series([s0["score"]]), pd.Series([s0["status"]]), pd.Series([s0["status_detail"]]))
    ident = rc.games_identity(pd.Series([pw["games_won_n"]]), pd.Series([pl["games_won_n"]]), wb, lb,
                              pd.Series([pw["tb_won_n"] if pd.notna(pw["tb_won_n"]) else 0]),
                              pd.Series([pl["tb_won_n"] if pd.notna(pl["tb_won_n"]) else 0]))
    defn = bool(((wb["second_won"] + wb["df"]) > (wb["svpt"] - wb["first_in"])).iloc[0]
                or ((lb["second_won"] + lb["df"]) > (lb["svpt"] - lb["first_in"])).iloc[0])
    differs = any((gw_.iloc[0][b] != gw_.iloc[0][f"{b}_rg"]) or (gl_.iloc[0][b] != gl_.iloc[0][f"{b}_rg"]) for b in rc.BOX)
    res.append({"match_id": mid, "tour": s0["tour"], "qualifying": bool(s0["qualifying"]), "status": s0["status"],
                "differs_from_sackmann": differs, "keystats_passes_B0_B9": bool(c["has_box"][0]),
                "failed": ",".join(k for k in ["B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9"] if c[k][0]),
                "identity_both": bool(ident["both_fit"][0]) if pd.notna(pw["games_won_n"]) else None,
                "definition_test_fails": defn})
Rz = pd.DataFrame(res)
Rz.to_csv(rc.OUT / "f5_keystats_box_checks.csv", index=False)
print("\nRG 2025 matches with both rows joined:", len(Rz))
print(Rz.groupby(["tour", "qualifying"]).agg(matches=("match_id", "size"), differs=("differs_from_sackmann", "sum"),
                                             passes=("keystats_passes_B0_B9", "sum"),
                                             identity=("identity_both", lambda s: int(s.fillna(False).sum())),
                                             deffail=("definition_test_fails", "sum")).to_string())
print(Rz[~Rz["keystats_passes_B0_B9"]].head(20).to_string())
