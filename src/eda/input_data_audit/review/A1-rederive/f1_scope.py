"""F1 step 3: the scope rows (raw Sackmann rows of the 30 events, both players) mapped to Stage 0, plus a calibrated
per-match test of the serve-point convention.

Per-match test: under "inclusive" (svpt includes double faults) the second serves in are X = svpt - first_in - df;
under "exclusive" they are X = svpt - first_in. second_won ~ Binomial(X, p) with p the pooled share of WTA 2014 and
2016 (inclusive, clean); the log-likelihood ratio (exclusive minus inclusive) is summed over both players. A row whose
second_won exceeds the inclusive X is impossible under inclusive (the definition test). Validated on Doha 2015, where
the MCP shows R32/R16 inclusive and SF/F exclusive.
Writes f1_scope_rows.csv (player rows), f1_match_llr.csv, f1_round_llr.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binom

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

EVENTS30 = ["Acapulco", "Kuala Lumpur", "Monterrey", "Indian Wells", "Miami", "Charleston", "Katowice", "Bogota",
            "Stuttgart", "Marrakech", "Prague", "Madrid", "Rome", "Nuremberg", "Strasbourg", "'s Hertogenbosch",
            "Nottingham", "Birmingham", "Eastbourne", "Bastad", "Bucharest", "Bad Gastein", "Istanbul", "Baku",
            "Florianopolis", "Stanford", "Washington", "Toronto", "Cincinnati", "New Haven"]

s15 = R.sack("wta", "wta_matches_2015.parquet")
s15["box"] = R.has_box(s15)
win = s15["tdate"].between("2015-02-23", "2015-08-24") & ~s15["tourney_level"].isin(["G", "D"])
print("tour events (non-Slam, non-Fed Cup) dated 23 Feb - 24 Aug 2015, with any box:",
      sorted(s15[win & s15["box"]]["tourney_name"].unique()))
ev = s15[win & s15["tourney_name"].isin(EVENTS30)]
assert ev["tourney_name"].nunique() == 30, ev["tourney_name"].nunique()
print("matches in the 30 events:", len(ev), " with a box (both svpt > 0):", int(ev["box"].sum()))
# partial boxes: one side only, or some counts blank
part = ev[~ev["box"] & (ev["w_svpt"].notna() | ev["l_svpt"].notna())]
print("rows with a partial box:", len(part))

# ---------------- Stage 0 mapping
m, p = R.stage0()
m15 = m[m["source_file"].str.endswith("wta_matches_2015.csv")]
key = m15.set_index("source_row")
rows = []
for r in ev[ev["box"]].to_dict("records"):
    mid = key.loc[r["_row"], "match_id"] if r["_row"] in key.index else None
    for side, pid in (("w", r["winner_id"]), ("l", r["loser_id"])):
        rows.append({"match_id": mid, "player_id": f"wta:{pid}", "_source_file": r["_source_file"], "_row": r["_row"],
                     "raw_side": side, "tourney_name": r["tourney_name"], "tourney_date": r["tdate"].date(),
                     "round": r["round"], "player_name": r["winner_name"] if side == "w" else r["loser_name"],
                     **{f"raw_{b}": r[f"{side}_{b}"] for b in R.BOX}})
sc = pd.DataFrame(rows)
pp = p.set_index(["match_id", "player_id"])
idx = pd.MultiIndex.from_frame(sc[["match_id", "player_id"]])
found = idx.isin(pp.index)
print("scope player rows:", len(sc), " found in Stage 0:", int(found.sum()))
s0 = pp.reindex(idx)
sc["s0_has_box"] = s0["has_box"].to_numpy()
for b in R.BOX:
    sc[f"s0_{b}"] = s0[b].to_numpy()
same = np.ones(len(sc), dtype=bool)
for b in ("ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_saved", "bp_faced"):
    same &= (sc[f"s0_{b}"].to_numpy() == sc[f"raw_{b}"].to_numpy())
sc["s0_equals_raw"] = same
sc["new_svpt"] = sc["raw_svpt"] + sc["raw_df"]
print("Stage 0 has_box:", sc["s0_has_box"].value_counts(dropna=False).to_dict(),
      " Stage 0 counts equal raw (where has_box):", int(sc.loc[sc["s0_has_box"].eq(True), "s0_equals_raw"].sum()))
print("source of the Stage 0 matches:", m.set_index("match_id").loc[sc["match_id"].dropna().unique(), "source"].value_counts().to_dict())
nb = sc[sc["s0_has_box"].ne(True)]
print("scope rows without a Stage 0 box:\n", nb[["match_id", "player_name", "tourney_name", "round", "raw_svpt", "raw_df",
                                                 "raw_first_in", "raw_second_won"]].to_string())
sc["def_fail"] = sc["raw_second_won"] + sc["raw_df"] > sc["raw_svpt"] - sc["raw_first_in"]
sc["df0"] = sc["raw_df"].eq(0)
# after the fix: B1-B9-like checks on the corrected counts
x = sc.assign(svpt=sc["new_svpt"])
sc["fixed_fails_b3"] = x["raw_second_won"] > x["svpt"] - x["raw_first_in"]
sc["fixed_fails_b6"] = x["raw_df"] > x["svpt"] - x["raw_first_in"]
sc["fixed_fails_def"] = x["raw_second_won"] + x["raw_df"] > x["svpt"] - x["raw_first_in"]
print("after the fix, rows failing B3/B6/definition:", int(sc["fixed_fails_b3"].sum()), int(sc["fixed_fails_b6"].sum()),
      int(sc["fixed_fails_def"].sum()))
print("per event rows:", sc.groupby("tourney_name").size().to_dict())
print("rows with Stage 0 box:", int(sc["s0_has_box"].eq(True).sum()), " df = 0 rows:", int(sc["df0"].sum()))
sc.to_csv(R.OUT / "f1_scope_rows.csv", index=False)

# ---------------- calibrated per-match LLR
clean = pd.concat([R.sack("wta", f"wta_matches_{y}.parquet") for y in (2014, 2016)], ignore_index=True)
clean = clean[R.has_box(clean) & ~clean["tourney_level"].isin(["D"])]
X, SW = [], []
for side in ("w", "l"):
    X.append(clean[f"{side}_svpt"] - clean[f"{side}_first_in"] - clean[f"{side}_df"])
    SW.append(clean[f"{side}_second_won"])
X, SW = pd.concat(X), pd.concat(SW)
ok = X > 0
p2 = SW[ok].sum() / X[ok].sum()
print(f"pooled second-serve-in won share, WTA 2014+2016 (inclusive): {p2:.4f}")


def llr_rows(svpt, df, fi, sw):
    xi = svpt - fi - df
    xe = svpt - fi
    li = np.where(sw <= xi, binom.logpmf(sw, np.maximum(xi, 0), p2), -np.inf)
    le = binom.logpmf(sw, xe, p2)
    return le - li


def match_llr(d):
    out = []
    for r in d.itertuples(index=False):
        a = llr_rows(r.w_svpt, r.w_df, r.w_first_in, r.w_second_won)
        b = llr_rows(r.l_svpt, r.l_df, r.l_first_in, r.l_second_won)
        out.append(a + b)
    return np.array(out, dtype=float)


allw = s15[s15["box"] & s15["tdate"].between("2015-01-01", "2015-12-31")].copy()
allw["llr"] = match_llr(allw)
allw["grp"] = np.where(allw["tourney_name"].isin(EVENTS30) & win.loc[allw.index], "window30",
                       np.where(allw["tourney_level"].eq("G"), "slam", "other_2015"))
q = allw.groupby(["grp"])["llr"].describe(percentiles=[.05, .25, .5, .75, .95])
print(q.to_string())
# share of matches with LLR < -2.3 (favouring inclusive by 10:1) and > +2.3
for g, d in allw.groupby("grp"):
    print(g, "n", len(d), " LLR<-2.3:", int((d["llr"] < -2.3).sum()), " LLR>2.3:", int((d["llr"] > 2.3).sum()),
          " inf:", int(np.isinf(d["llr"]).sum()), " sum(finite):", round(d.loc[np.isfinite(d['llr']), 'llr'].sum(), 1))
rnd = allw[allw["tourney_name"].isin(["Doha", "Acapulco", "Kuala Lumpur", "Monterrey", "Dubai", "Rio de Janeiro", "New Haven"])]
rl = rnd.groupby(["tourney_name", "round"]).agg(n=("llr", "size"), llr_sum=("llr", lambda v: v[np.isfinite(v)].sum()),
                                                  n_inf=("llr", lambda v: int(np.isinf(v).sum())),
                                                  n_neg=("llr", lambda v: int((v < -2.3).sum())))
print(rl.to_string(float_format=lambda x: f"{x:.1f}"))
rl.to_csv(R.OUT / "f1_round_llr.csv")
allw[["_source_file", "_row", "tourney_name", "tdate", "round", "winner_name", "loser_name", "grp", "llr"]].to_csv(
    R.OUT / "f1_match_llr.csv", index=False)
print("window matches favouring inclusive by >= 10:1:")
print(allw[(allw["grp"] == "window30") & (allw["llr"] < -2.3)][["tourney_name", "round", "winner_name", "loser_name", "llr",
                                                                 "w_svpt", "w_df", "w_first_in", "w_second_won", "l_svpt", "l_df",
                                                                 "l_first_in", "l_second_won"]].to_string())
