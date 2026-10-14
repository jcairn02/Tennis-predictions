"""F5: Roland Garros 2025 against RG's own key statistics and point-by-point (decrypted Infosys), TML 2026, Sofascore, MCP.

Derivations (per player-match, whole match):
  key statistics  ace = Aces; df = Double Faults; first_in / svpt = First Serve a/b; first_won = Win On 1st Serve a;
                  second_won = Win On 2nd Serve a; bp_faced = opponent's Break Points Won b; bp_saved = that b - a;
                  sv_gms = opponent's 'Break Points Converted Games' b (the opponent's return games)
  point-by-point  svpt = points served; ace / df = result A / DF on own serve; first_in = serve 1; first_won /
                  second_won = serve 1 / 2 points won; sv_gms = distinct (set, game) served
Writes f5_rg_rows.csv (Stage 0 / TML rows joined to every referee) and f5_agreement.csv (per count, per source pair).
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


def keystats() -> pd.DataFrame:
    k = rc.rd(rc.PTS / "infosys_slams" / "keystats.parquet")
    k = k[k["set_key"].eq("set0")].drop_duplicates(["slam", "year", "match_id", "name"])
    m = rc.rd(rc.PTS / "infosys_slams" / "matches.parquet")
    out = []
    for no, other in (("1", "2"), ("2", "1")):
        w = k.pivot_table(index=["slam", "year", "match_id"], columns="name", values=f"player{no}", aggfunc="first")
        o = k.pivot_table(index=["slam", "year", "match_id"], columns="name", values=f"player{other}", aggfunc="first")
        d = pd.DataFrame(index=w.index)
        d["first_in"], d["svpt"] = refs.frac(w["First Serve"], 0), refs.frac(w["First Serve"], 1)
        d["first_won"] = refs.frac(w["Win On 1st Serve"], 0)
        d["second_won"] = refs.frac(w["Win On 2nd Serve"], 0)
        d["second_den"] = refs.frac(w["Win On 2nd Serve"], 1)
        d["ace"] = pd.to_numeric(w["Aces"], errors="coerce")
        d["df"] = pd.to_numeric(w["Double Faults"], errors="coerce")
        d["bp_faced"] = refs.frac(o["Break Points Won"], 1)
        d["bp_saved"] = refs.frac(o["Break Points Won"], 1) - refs.frac(o["Break Points Won"], 0)
        d["sv_gms"] = refs.frac(o["Break Points Converted Games"], 1)
        d["opp_ret_pts"] = refs.frac(o["Receiving Points Won"], 1)
        d = d.reset_index().merge(m[["slam", "year", "match_id", "draw", "tour", "round_from_code", "p1_first_name",
                                     "p1_last_name", "p2_first_name", "p2_last_name", "match_status"]],
                                  on=["slam", "year", "match_id"], how="left")
        d["name"] = d[f"p{no}_first_name"].fillna("") + " " + d[f"p{no}_last_name"].fillna("")
        d["oname"] = d[f"p{other}_first_name"].fillna("") + " " + d[f"p{other}_last_name"].fillna("")
        d["pno"] = no
        out.append(d)
    x = pd.concat(out, ignore_index=True)
    x["pk"], x["ok"] = rc.keys(x["name"]), rc.keys(x["oname"])
    x["year"] = x["year"].astype(int)
    return x


def pbp() -> pd.DataFrame:
    pt = rc.rd(rc.PTS / "infosys_slams" / "points.parquet")
    for c in ["server", "serve", "scorer", "set", "game"]:
        pt[c] = pd.to_numeric(pt[c], errors="coerce")
    out = []
    for k in (1, 2):
        s = pt[pt["server"] == k]
        g = s.groupby(["slam", "year", "match_id"])
        won = s["scorer"] == k
        d = pd.DataFrame({"p_svpt": g.size(), "p_ace": s[s["result"] == "A"].groupby(["slam", "year", "match_id"]).size(),
                          "p_df": s[s["result"] == "DF"].groupby(["slam", "year", "match_id"]).size(),
                          "p_first_in": s[s["serve"] == 1].groupby(["slam", "year", "match_id"]).size(),
                          "p_first_won": s[(s["serve"] == 1) & won].groupby(["slam", "year", "match_id"]).size(),
                          "p_second_won": s[(s["serve"] == 2) & won].groupby(["slam", "year", "match_id"]).size(),
                          "p_sv_gms": g[["set", "game"]].apply(lambda z: z.drop_duplicates().shape[0])}).fillna(0)
        d["pno"] = str(k)
        out.append(d.reset_index())
    x = pd.concat(out, ignore_index=True)
    x["year"] = x["year"].astype(int)
    return x


def main() -> int:
    K = keystats()
    Pp = pbp()
    KP = K.merge(Pp, on=["slam", "year", "match_id", "pno"], how="left")
    print("key-statistics player rows:", K.groupby(["slam", "year"]).size().to_dict())
    agr = []
    have = KP[KP["p_svpt"].notna()]
    for b in ["svpt", "ace", "df", "first_in", "first_won", "second_won", "sv_gms"]:
        agr.append({"pair": "RG keystats vs RG point-by-point", "count": b, "rows": len(have),
                    "exact": round(float((have[b] == have[f"p_{b}"]).mean()), 4)})
    # Stage 0 RG 2025 / 2026 rows
    m, p = rc.stage0()
    mm = m[m["tournament_name"].eq("Roland Garros") & m["year"].isin([2025, 2026])]
    W = rc.wide(mm, p[p["match_id"].isin(mm["match_id"])])
    rows = []
    for side, oth in (("w", "l"), ("l", "w")):
        d = W[["match_id", "tour", "year", "qualifying", "round", "score", "source", "has_box", "source_file",
               "source_row"]].copy()
        d["player_id"], d["name"], d["oname"] = W[f"{side}_player_id"], W[f"{side}_player_name"], W[f"{oth}_player_name"]
        for b in rc.BOX:
            d[b] = W[f"{side}_{b}"]
        rows.append(d)
    S = pd.concat(rows, ignore_index=True)
    S["pk"], S["ok"] = rc.keys(S["name"]), rc.keys(S["oname"])
    S["sn"] = S["name"].map(refs.surname)
    S["osn"] = S["oname"].map(refs.surname)
    K["sn"], K["osn"] = K["name"].map(refs.surname), K["oname"].map(refs.surname)
    j = S.merge(K, on=["year", "pk", "ok"], suffixes=("", "_rg"))
    rest = S[~S.set_index(["match_id", "player_id"]).index.isin(j.set_index(["match_id", "player_id"]).index)]
    j2 = rest.merge(K, on=["year", "sn", "osn"], suffixes=("", "_rg"))
    j = pd.concat([j, j2], ignore_index=True).drop_duplicates(["match_id", "player_id"])
    j = j.merge(Pp, on=["slam", "year", "match_id_rg" if "match_id_rg" in j else "match_id", "pno"], how="left") \
        if False else j
    print("Stage 0 RG 2025-26 player rows:", len(S), "with a box:", int(S["has_box"].sum()), "joined to keystats:", len(j))
    j["draw"] = np.where(j["qualifying"], "qualifying", "main")
    for (tour, year, draw, src), g in j[j["has_box"]].groupby(["tour", "year", "draw", "source"]):
        for b in rc.BOX:
            agr.append({"pair": f"Stage0 {src} vs RG keystats", "tour": tour, "year": year, "draw": draw, "count": b,
                        "rows": len(g), "exact": round(float((g[b] == g[f"{b}_rg"]).mean()), 4),
                        "mean_diff": round(float((g[b] - g[f"{b}_rg"]).mean()), 3)})
    A = pd.DataFrame(agr)
    A.to_csv(rc.OUT / "f5_agreement.csv", index=False)
    print(A[A["pair"].str.contains("point")].to_string(index=False))
    piv = A[A["pair"].str.startswith("Stage0")].pivot_table(index=["pair", "tour", "year", "draw"], columns="count",
                                                             values="exact")
    print(piv[rc.BOX].round(3).to_string())
    # distribution of first-in differences, 2025 Sackmann rows
    s25 = j[(j["year"] == 2025) & j["has_box"]].copy()
    s25["d_fi"] = s25["first_in"] - s25["first_in_rg"]
    s25["d_fw"] = s25["first_won"] - s25["first_won_rg"]
    s25["d_sw"] = s25["second_won"] - s25["second_won_rg"]
    s25["d_svpt"] = s25["svpt"] - s25["svpt_rg"]
    for (tour, draw), g in s25.groupby(["tour", "draw"]):
        print(f"\n{tour} {draw}: first_in difference (Sackmann - RG) distribution, rows {len(g)}")
        print(g["d_fi"].value_counts().sort_index().to_dict())
        print("  svpt diff:", g["d_svpt"].value_counts().sort_index().to_dict())
        moved = g[g["d_fi"] > 0]
        if len(moved):
            print(f"  rows with extra first serves: {len(moved)}; extra first serves {int(moved['d_fi'].sum())}; "
                  f"first_won gained {int(moved['d_fw'].sum())}, second_won lost {int(-moved['d_sw'].sum())} "
                  f"-> the moved points were won {moved['d_fw'].sum() / moved['d_fi'].sum():.3f}")
    j.to_csv(rc.OUT / "f5_rg_rows.csv", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
