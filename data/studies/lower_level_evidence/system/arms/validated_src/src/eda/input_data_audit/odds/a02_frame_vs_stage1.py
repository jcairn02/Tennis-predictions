"""Tasks 1 and 4: the model frame's p_mkt against Stage 1 (30 Sep and 7 Oct), and the men's 2018 gap.

Outputs (out/):
    a02_frame_counts.csv          model-frame matches per tour x season x split
    a02_frame_vs_stage1.json      p_mkt == stage1 p_avg_a (30 Sep), in_odds_logit == logit(p_mkt), a_won agreement
    a02_old_vs_new.csv            every match whose p_avg_a differs between 30 Sep and 7 Oct (or exists in one only)
    a02_old_vs_new_summary.json   counts of the differences by tour x season x kind and by cause
    a02_atp2018_restore.json      what the 7 Oct Stage 1 would restore for the men's 2018 season
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from _common import MF, NEW, OLD, OUTD, ROOT, logit

mf = pd.read_parquet(MF)
o30 = pd.read_parquet(OLD / "stage1_odds.parquet")
o07 = pd.read_parquet(NEW / "stage1_odds.parquet")
mcols = ["match_id", "tour", "year", "level", "qualifying", "round", "tournament_id", "tournament_name", "tournament_date",
         "status", "score", "player_a_id", "player_b_id", "a_won", "source"]
s30 = pd.read_parquet(OLD / "stage0_matches.parquet", columns=mcols)
s07 = pd.read_parquet(NEW / "stage0_matches.parquet", columns=mcols)
idmap = pd.read_csv(ROOT / "data/studies/data_continuity/rebuilds/2026-10-07T0005Z/id_map.csv")
res = {}

# ---- model frame counts
cnt = mf.groupby(["tour", "season", "tabpfn_split"]).size().unstack(fill_value=0)
cnt.to_csv(OUTD / "a02_frame_counts.csv")
print(cnt.to_string())
res["frame_rows"] = int(len(mf))
res["frame_atp_2018_rows"] = int(((mf["tour"] == "atp") & (mf["season"] == 2018)).sum())
res["frame_dup_match_ids"] = int(mf["match_id"].duplicated().sum())

# ---- p_mkt vs stage1 (30 Sep)
j = mf[["match_id", "tour", "season", "a_won", "p_mkt", "in_odds_logit", "tabpfn_split"]].merge(
    o30[["match_id", "p_avg_a", "avg_a", "avg_b", "link", "status", "year"]], on="match_id", how="left", indicator=True)
res["frame_ids_in_stage1_30sep"] = int((j["_merge"] == "both").sum())
res["frame_ids_missing_from_stage1_30sep"] = int((j["_merge"] != "both").sum())
d = (j["p_mkt"] - j["p_avg_a"]).abs()
res["p_mkt_equals_stage1_30sep_exact"] = int((j["p_mkt"] == j["p_avg_a"]).sum())
res["p_mkt_max_abs_diff_vs_stage1_30sep"] = float(d.max())
res["p_mkt_diff_gt_1e-12"] = int((d > 1e-12).sum())
res["p_mkt_missing"] = int(j["p_mkt"].isna().sum())
res["year_equals_season"] = int((j["year"] == j["season"]).sum())
# a_won against Stage 0 (30 Sep)
k = mf[["match_id", "a_won"]].merge(s30[["match_id", "a_won", "status"]], on="match_id", how="left", suffixes=("", "_s0"))
res["a_won_equals_stage0_30sep"] = int((k["a_won"] == k["a_won_s0"]).sum())
res["frame_status_counts"] = k["status"].value_counts().to_dict()
# in_odds_logit
eps = 1e-9
lg = logit(np.clip(mf["p_mkt"].to_numpy(dtype=float), eps, 1 - eps))
dd = np.abs(lg - mf["in_odds_logit"].to_numpy(dtype=float))
res["in_odds_logit_max_abs_diff"] = float(np.nanmax(dd))
res["in_odds_logit_nonfinite"] = int((~np.isfinite(mf["in_odds_logit"].to_numpy(dtype=float))).sum())
# recompute p from the stored odds
p_re = (1 / j["avg_a"]) / (1 / j["avg_a"] + 1 / j["avg_b"])
res["p_mkt_vs_recomputed_from_avg_odds_max_abs"] = float((p_re - j["p_mkt"]).abs().max())
# market quality per split
y = mf["a_won"].astype(float).to_numpy()
p = mf["p_mkt"].to_numpy(dtype=float)
for sp in ("train", "test"):
    m = (mf["tabpfn_split"] == sp).to_numpy()
    ll = -(y[m] * np.log(p[m]) + (1 - y[m]) * np.log(1 - p[m])).mean()
    res[f"market_logloss_{sp}"] = round(float(ll), 5)
    res[f"mean_p_a_{sp}"] = round(float(p[m].mean()), 5)
    res[f"mean_a_won_{sp}"] = round(float(y[m].mean()), 5)
(OUTD / "a02_frame_vs_stage1.json").write_text(json.dumps(res, indent=1, default=str))
print(json.dumps(res, indent=1, default=str))

# ---- 30 Sep vs 7 Oct per match
ren = dict(zip(idmap["old_match_id"], idmap["new_match_id"]))
a = o30[["match_id", "tour", "year", "level", "round", "tournament_date", "status", "link", "td_file", "td_row", "td_winner",
         "td_loser", "avg_a", "avg_b", "p_avg_a"]].copy()
a["key"] = a["match_id"].map(lambda x: ren.get(x, x))
b = o07[["match_id", "tour", "year", "level", "round", "status", "link", "td_file", "td_row", "td_winner", "td_loser", "avg_a",
         "avg_b", "p_avg_a"]].rename(columns={"match_id": "key"})
c = a.merge(b, on="key", how="outer", suffixes=("_30", "_07"), indicator=True)
c["tour"] = c["tour_30"].fillna(c["tour_07"])
c["year"] = c["year_30"].fillna(c["year_07"])
has30, has07 = c["p_avg_a_30"].notna(), c["p_avg_a_07"].notna()
kind = np.select(
    [c["_merge"] == "left_only", c["_merge"] == "right_only", has30 & ~has07, ~has30 & has07,
     has30 & has07 & ((c["p_avg_a_30"] - c["p_avg_a_07"]).abs() > 1e-12), has30 & has07],
    ["match only 30 Sep", "match only 7 Oct", "odds lost", "odds gained", "p changed", "same"], "neither has odds")
c["kind"] = kind
c["flipped"] = has30 & has07 & ((c["p_avg_a_30"] - 0.5) * (c["p_avg_a_07"] - 0.5) < 0) & \
    ((c["p_avg_a_30"] + c["p_avg_a_07"] - 1).abs() < 1e-9)
diff = c[c["kind"] != "same"].copy()
diff = diff[diff["kind"] != "neither has odds"]
diff.to_csv(OUTD / "a02_old_vs_new.csv", index=False)
summ = {"by_kind": c["kind"].value_counts().to_dict(),
        "by_tour_year_kind": diff.groupby(["tour", "year", "kind"]).size().reset_index(name="n").to_dict("records"),
        "p_changed_and_exactly_mirrored": int(c["flipped"].sum())}
pc = c[c["kind"] == "p changed"]
summ["p_changed_abs_diff_quantiles"] = (pc["p_avg_a_30"] - pc["p_avg_a_07"]).abs().quantile([.5, .9, .99, 1]).round(4).to_dict()
summ["p_changed_by_td_file"] = pc.groupby("td_file_30").size().to_dict()
summ["p_changed_same_td_row"] = int((pc["td_row_30"] == pc["td_row_07"]).sum())
summ["p_changed_examples"] = pc.head(15)[["key", "td_file_30", "td_row_30", "td_row_07", "td_winner_30", "td_winner_07",
                                           "avg_a_30", "avg_b_30", "avg_a_07", "avg_b_07"]].to_dict("records")
lost = c[c["kind"] == "odds lost"]
summ["odds_lost_examples"] = lost.head(15)[["key", "tour", "year", "td_file_30", "td_row_30", "link_30", "link_07",
                                            "status_30", "status_07"]].to_dict("records")
summ["odds_lost_by_tour_year"] = lost.groupby(["tour", "year"]).size().reset_index(name="n").to_dict("records")
(OUTD / "a02_old_vs_new_summary.json").write_text(json.dumps(summ, indent=1, default=str))
print(json.dumps({k: v for k, v in summ.items() if k != "by_tour_year_kind"}, indent=1, default=str)[:6000])
print(pd.DataFrame(summ["by_tour_year_kind"]).pivot_table(index=["tour", "year"], columns="kind", values="n", fill_value=0).to_string())

# ---- the men's 2018 season
fr = pd.read_parquet(ROOT / "data/studies/tabpfn_thinking/frame.parquet",
                     columns=["match_id", "tour", "year", "group", "status", "split", "tabpfn_split", "format_supported"])
e18 = fr[(fr["tour"] == "atp") & (fr["year"] == 2018)]
r = {"thinking_frame_atp2018_rows": int(len(e18)), "eligible_split_train": int((e18["split"] == "train").sum()),
     "with_tabpfn_split": int((e18["tabpfn_split"] != "").sum())}
s18_30 = o30[(o30["tour"] == "atp") & (o30["year"] == 2018)]
r["stage1_30sep_atp2018_rows"] = int(len(s18_30))
r["stage1_30sep_atp2018_linked"] = int((s18_30["link"] != "none").sum())
s18 = o07[(o07["tour"] == "atp") & (o07["year"] == 2018)]
r["stage1_07oct_atp2018_rows"] = int(len(s18))
r["stage1_07oct_atp2018_linked"] = int((s18["link"] != "none").sum())
r["stage1_07oct_atp2018_with_p"] = int(s18["p_avg_a"].notna().sum())
elig = e18[e18["split"] == "train"].copy()
elig["key"] = elig["match_id"].map(lambda x: ren.get(x, x))
elig = elig.merge(o07[["match_id", "p_avg_a", "link", "avg_coherent"]].rename(columns={"match_id": "key"}), on="key", how="left")
r["eligible_with_7oct_p"] = int(elig["p_avg_a"].notna().sum())
r["eligible_without_7oct_p"] = int(elig["p_avg_a"].isna().sum())
r["eligible_without_p_by_link"] = elig[elig["p_avg_a"].isna()]["link"].fillna("not in stage1").value_counts().to_dict()
r["eligible_without_p_examples"] = elig[elig["p_avg_a"].isna()].head(10)[["match_id", "group", "status", "link"]].to_dict("records")
# the 2018 market's quality, from the 7 Oct links (stage0 a_won from the 7 Oct table)
s = s18.merge(s07[["match_id", "a_won"]], on="match_id")
s = s[s["p_avg_a"].notna() & s["status"].isin(["completed", "retired"])]
yy, pp = s["a_won"].astype(float).to_numpy(), s["p_avg_a"].to_numpy()
r["atp2018_market_logloss"] = round(float(-(yy * np.log(pp) + (1 - yy) * np.log(1 - pp)).mean()), 5)
r["atp2018_fav_win_rate"] = round(float(((pp > 0.5) == (yy == 1)).mean()), 4)
(OUTD / "a02_atp2018_restore.json").write_text(json.dumps(r, indent=1, default=str))
print(json.dumps(r, indent=1, default=str))
