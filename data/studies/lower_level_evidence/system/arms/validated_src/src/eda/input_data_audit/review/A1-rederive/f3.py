"""F3: WTA Adelaide 2 2022 (10 Jan 2022) against Adelaide 2021, and the WTA API.

1. Every Sackmann row of Adelaide 2 2022 (main and qualifying files): is its 18-count box (both players, either
   orientation) a verbatim copy of an Adelaide 2021 box (Sackmann, any match)? Match number alignment.
2. WTA API: Adelaide 2 2022 = event 2030 (year 2022); Adelaide 2021 = event 2014 (year 2021). Do Sackmann's 2021 boxes
   equal the API's 2021 boxes (genuine)? Do Sackmann's 2022 boxes equal the API's 2022 boxes?
3. F3b: per-count exact agreement of the WTA API with Sackmann on the clean WTA events of 2021-2022 (all linked events
   except Abu Dhabi 2021, Phillip Island 2021 and Adelaide 2 2022), and whether the API's 2022 counts pass B0-B9.
Writes f3_matches.csv, f3_api_agreement.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

pd.set_option("display.width", 260)
pd.set_option("display.max_colwidth", 60)
COUNTS = [f"{s}_{b}" for s in ("w", "l") for b in R.BOX]

s22 = pd.concat([R.sack("wta", "wta_matches_2022.parquet"), R.sack("wta", "wta_matches_qual_itf_2022.parquet")], ignore_index=True)
s21 = pd.concat([R.sack("wta", "wta_matches_2021.parquet"), R.sack("wta", "wta_matches_qual_itf_2021.parquet")], ignore_index=True)
a22 = s22[s22["tourney_name"].str.contains("Adelaide", na=False)]
print(a22.groupby(["tourney_id", "tourney_name", "tourney_date"]).size())
a21 = s21[s21["tourney_name"].str.contains("Adelaide", na=False)]
print(a21.groupby(["tourney_id", "tourney_name", "tourney_date"]).size())
ad2 = a22[a22["tourney_date"].eq("20220110")].copy()
ad2["box"] = R.has_box(ad2)


def key(r, swap=False):
    sides = ("l", "w") if swap else ("w", "l")
    return tuple(r[f"{s}_{b}"] for s in sides for b in R.BOX)


k21 = {}
for r in a21[R.has_box(a21)].to_dict("records"):
    k21.setdefault(key(r), []).append((r, False))
    k21.setdefault(key(r, swap=True), []).append((r, True))

# also: any 2021-2022 WTA row anywhere (not only Adelaide 2021)
allrows = pd.concat([s21, s22], ignore_index=True)
allrows = allrows[R.has_box(allrows)]
kall = {}
for r in allrows.to_dict("records"):
    kall.setdefault(key(r), []).append(r)

rows = []
for r in ad2.to_dict("records"):
    out = {"_source_file": r["_source_file"], "_row": r["_row"], "round": r["round"], "match_num": r["match_num"],
           "winner": r["winner_name"], "loser": r["loser_name"], "score": r["score"], "has_box": r["box"]}
    if r["box"]:
        hit = k21.get(key(r), [])
        out["copy_of_adelaide2021"] = len(hit) > 0
        if hit:
            h, sw = hit[0]
            out.update({"src_row": h["_row"], "src_round": h["round"], "src_match_num": h["match_num"],
                        "src_match": f"{h['winner_name']} d. {h['loser_name']} {h['score']}", "src_orientation_swapped": sw})
        others = [x for x in kall.get(key(r), []) if not (x["_source_file"] == r["_source_file"] and x["_row"] == r["_row"])]
        out["equal_box_elsewhere_2021_2022"] = "; ".join(f"{x['tourney_name']} {x['tourney_date']} {x['round']}" for x in others)
    rows.append(out)
f = pd.DataFrame(rows)

# ---------------- WTA API
L = pd.read_parquet(R.OUT / "wta_api_links_2019_2020_2021_2022_2023_2024_2025_2026.parquet")
api22 = R.wta_api(2022)
api21 = R.wta_api(2021)
ap2 = api22[api22["event"].eq("2030")]
print("WTA API Adelaide 2 2022 (event 2030) singles matches with stats:", len(ap2), ap2["draw"].value_counts().to_dict())
lk = L[L["_source_file"].str.contains("2022") & L["tourney_id"].str.endswith("-2030") & L["tdate"].astype(str).str.startswith("2022-01-10")]
lk = lk.set_index(["_source_file", "_row"])
f["api_linked"] = [(a, b) in lk.index for a, b in zip(f["_source_file"], f["_row"])]


def eq_rec(x):
    return all(x[f"s_{c}"] == x[f"a_{c}"] for c in COUNTS)


f["sack_equals_api"] = [eq_rec(lk.loc[(a, b)]) if (a, b) in lk.index else np.nan for a, b in zip(f["_source_file"], f["_row"])]


def b_checks(c):
    """Stage 0's B0-B4, B6-B8 on one player's counts (dict)."""
    bad = any(v < 0 for v in c.values())
    bad |= c["first_in"] > c["svpt"] or c["first_won"] > c["first_in"] or c["second_won"] > c["svpt"] - c["first_in"]
    bad |= c["bp_saved"] > c["bp_faced"] or c["df"] > c["svpt"] - c["first_in"] or c["ace"] > c["first_won"] + c["second_won"]
    bad |= (c["bp_faced"] - c["bp_saved"]) > c["sv_gms"]
    return not bad


api_ok = []
for a, b in zip(f["_source_file"], f["_row"]):
    if (a, b) not in lk.index:
        api_ok.append(np.nan)
        continue
    x = lk.loc[(a, b)]
    cw = {bb: x[f"a_w_{bb}"] for bb in R.BOX}
    cl = {bb: x[f"a_l_{bb}"] for bb in R.BOX}
    api_ok.append(b_checks(cw) and b_checks(cl))
f["api_counts_pass_checks"] = api_ok
f.to_csv(R.OUT / "f3_matches.csv", index=False)
print(f[["_row", "round", "winner", "loser", "score", "has_box", "copy_of_adelaide2021", "src_match", "api_linked",
         "sack_equals_api", "api_counts_pass_checks"]].to_string())
print("Adelaide 2 2022 rows:", len(f), " with box:", int(f["has_box"].sum()), " copies of an Adelaide 2021 box:",
      int(f["copy_of_adelaide2021"].fillna(False).sum()))

# Sackmann's Adelaide 2021 against the API's Adelaide 2021 (event 2014 in the API; Sackmann's tourney id?)
lk21 = L[L["_source_file"].str.contains("2021") & L["tourney_name"].str.contains("Adelaide")]
print("Sackmann Adelaide 2021 rows linked to the API:", len(lk21), " (Sackmann tourney ids:", lk21["tourney_id"].unique(), ")")
if len(lk21):
    print("  equal on all 18 counts:", int(sum(eq_rec(x) for _, x in lk21.iterrows())))
else:
    # Sackmann's id 2021-2030 is not the API's event (2014): link by names within the API's event 2014
    ap14 = api21[api21["event"].eq("2014")]
    n = eqn = 0
    for r in a21[R.has_box(a21)].to_dict("records"):
        wk, lk_ = R.nkey(r["winner_name"]), R.nkey(r["loser_name"])
        for x in ap14.to_dict("records"):
            for ws, ls in (("A", "B"), ("B", "A")):
                if wk.endswith(x[f"lk{ws}"]) and lk_.endswith(x[f"lk{ls}"]):
                    n += 1
                    eqn += all(r[f"w_{b}"] == x[f"{ws}_{b}"] and r[f"l_{b}"] == x[f"{ls}_{b}"] for b in R.BOX)
    print(f"  Sackmann Adelaide 2021 vs API event 2014 by names: linked {n}, equal on all 18: {eqn}")

# ---------------- F3b: agreement of the API with Sackmann on clean events 2021-2022
ag = pd.read_csv(R.OUT / "wta_api_agree_2021_2022_matches.csv")
bad_ev = ag["tourney_id"].isin(["2021-2028", "2021-2027"]) | (ag["tourney_id"].eq("2022-2030") & ag["tdate"].astype(str).str.startswith("2022-01-10"))
clean = ag[~bad_ev]
res = {"matches": len(clean), "events": clean["tourney_id"].nunique()}
for b in R.BOX:
    e = pd.concat([clean[f"s_w_{b}"].eq(clean[f"a_w_{b}"]), clean[f"s_l_{b}"].eq(clean[f"a_l_{b}"])])
    res[f"{b}_exact_per_player_row"] = round(float(e.mean()), 5)
allc = np.ones(len(clean), dtype=bool)
for c in COUNTS:
    allc &= clean[f"s_{c}"].eq(clean[f"a_{c}"]).to_numpy()
res["all_18_exact_per_match"] = round(float(allc.mean()), 5)
res["exchanged"] = int(clean["exchanged"].sum())
pd.Series(res).to_csv(R.OUT / "f3_api_agreement.csv")
print(pd.Series(res).to_string())
# rows of clean events that differ: how many counts
nd = clean.loc[~allc, "n_diff"]
print("clean matches differing:", int((~allc).sum()), " n_diff distribution:", nd.value_counts().sort_index().to_dict())
