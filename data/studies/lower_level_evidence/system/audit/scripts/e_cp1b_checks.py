"""Role E (red team), CP1b: re-audit of F's candidate Stage 0s C0_now and C0_pre (questions 1, 3 and 4 of the lead).

Q1  ids crossing tours in new matches (by the id's tour prefix), and the frame players of the 00:12 build's cross-tour
    rows (audit/F_c0now/cross_tour_rows.csv.gz): do they still receive other-tour rows; do the old rows' names now
    resolve to ids of their match's tour?
Q3  the new matches' windows: finite and lf >= es; a day-dated row's window holds its day; rows that join a Stage 0
    event, against the frozen windows of the same event and round (disjoint, or ending before them); the rows whose
    source dates the event apart from Stage 0 (the union safeguard).
Q4  C0_pre against C0_now: the same frozen rows; C0_pre's new matches are C0_now's dated before 30 Dec 2024, with the
    same match rows, player rows and windows; what C0_now has beyond them is all dated from 30 Dec 2024.
Counts, ids and dates only: no outcome is read. Writes audit/cp1b/checks.json.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[6]
S0 = ROOT / "data/studies/lower_level_evidence/system/stage0"
REF = ROOT / "data/studies/current_best_model/reference_2026-10-08/frozen"
REF_S0 = REF / "tables/data/studies/predictability_diagnostic"
REF_T = REF / "tables_later/data/studies/match_timing/timing.parquet"
OUT = Path(__file__).resolve().parents[1] / "cp1b"
OUT.mkdir(exist_ok=True)
MCOLS = ["match_id", "tour", "year", "map_level", "round", "tournament_id", "tournament_date", "status",
         "player_a_id", "player_b_id", "has_box"]
res = {}


def load(label):
    d = S0 / label
    m = pd.read_parquet(d / "stage0_matches.parquet", columns=MCOLS)
    p = pd.read_parquet(d / "stage0_match_players.parquet", columns=["match_id", "player_id", "side"])
    t = pd.read_parquet(d / "timing.parquet", columns=["match_id", "es", "lf", "width_days", "exact"])
    a = pd.read_parquet(d / "additions.parquet")
    return m, p, t, a


ref_ids = set(pd.read_parquet(REF_S0 / "stage0_matches.parquet", columns=["match_id"])["match_id"])
mN, pN, tN, aN = load("C0_now")
newN = set(aN["match_id"])
# ---------------- Q1
pm = pN.merge(mN[["match_id", "tour"]], on="match_id")
pm["id_tour"] = pm["player_id"].str.split(":").str[0]
cross = pm[pm["id_tour"].isin(["atp", "wta"]) & (pm["id_tour"] != pm["tour"])]
res["q1_cross_tour_rows_all"] = int(len(cross))
res["q1_cross_tour_rows_new_matches"] = int(cross["match_id"].isin(newN).sum())
res["q1_id_namespaces"] = pm["id_tour"].value_counts().to_dict()
old = pd.read_csv(OUT.parent / "F_c0now/cross_tour_rows.csv.gz")
fp_old = sorted(set(old.loc[old["frame_player"].astype(bool), "player_id"]))
res["q1_old_frame_players"] = len(fp_old)
sub = pm[pm["player_id"].isin(fp_old) & pm["match_id"].isin(newN)]
res["q1_old_frame_players_new_rows_by_match_tour_vs_id"] = sub.assign(
    same=lambda x: x["tour"] == x["id_tour"]).groupby("same").size().to_dict()
# the old rows' names: where do they resolve now (by source name, tour and tournament date)
add_long = pd.concat([
    aN[["match_id", "tour", "p1", "x1"]].rename(columns={"p1": "name", "x1": "pre_id"}),
    aN[["match_id", "tour", "p2", "x2"]].rename(columns={"p2": "name", "x2": "pre_id"})])
add_long = add_long.merge(mN[["match_id", "tournament_date", "player_a_id", "player_b_id"]], on="match_id")
old_fp = old[old["frame_player"].astype(bool)].copy()
old_fp["tournament_date"] = pd.to_datetime(old_fp["tournament_date"])
add_long["tournament_date"] = pd.to_datetime(add_long["tournament_date"])
j = old_fp.merge(add_long, left_on=["player_name", "tour", "tournament_date"],
                 right_on=["name", "tour", "tournament_date"], how="left", suffixes=("_old", "_new"))
j["final_tour_ok"] = j.apply(lambda r: (str(r["pre_id"]).split(":")[0] == r["tour"]) if pd.notna(r["pre_id"])
                             else None, axis=1)
res["q1_old_frame_rows"] = int(len(old_fp))
res["q1_old_frame_rows_found_by_name_tour_date"] = int(j["pre_id"].notna().sum())
res["q1_old_frame_rows_now_same_tour_id"] = int((j["final_tour_ok"] == True).sum())  # noqa: E712
res["q1_old_frame_rows_now_still_frame_id"] = int(j["pre_id"].isin(fp_old).sum())
res["q1_examples"] = j[["player_id", "player_name", "tour", "tournament_date", "pre_id"]].drop_duplicates(
    "player_name").head(8).astype(str).to_dict("records")
# ---------------- Q3
tn = tN[tN["match_id"].isin(newN)].copy()
res["q3_new_windows"] = int(len(tn))
res["q3_nonfinite"] = int((~np.isfinite(tn["es"]) | ~np.isfinite(tn["lf"])).sum())
res["q3_lf_lt_es"] = int((tn["lf"] < tn["es"]).sum())
res["q3_width_quantiles"] = (tn["lf"] - tn["es"]).describe(percentiles=[.01, .5, .99]).round(2).to_dict()
a = aN.merge(tn, on="match_id").merge(mN[["match_id", "tournament_id", "round", "tournament_date"]], on="match_id")
dated = a[a["day"].notna()].copy()
dday = pd.to_datetime(dated["day"]).values.astype("datetime64[D]").astype("int64")
res["q3_dated_rows"] = int(len(dated))
res["q3_dated_day_outside_window"] = int(((dday < dated["es"]) | (dday > dated["lf"])).sum())
res["q3_dated_window_minus_day"] = {"es_minus_day": pd.Series(dated["es"].to_numpy() - dday).value_counts().sort_index().to_dict(),
                                    "lf_minus_day": pd.Series(dated["lf"].to_numpy() - dday).value_counts().sort_index().to_dict()}
# joined rows against the frozen windows of the same event and round
fm = pd.read_parquet(REF_S0 / "stage0_matches.parquet", columns=["match_id", "tournament_id", "round"])
ft = pd.read_parquet(REF_T, columns=["match_id", "es", "lf"])
fr = fm.merge(ft, on="match_id").groupby(["tournament_id", "round"]).agg(f_es_min=("es", "min"), f_es_max=("es", "max"),
                                                                         f_lf_min=("lf", "min"), f_lf_max=("lf", "max"),
                                                                         f_n=("es", "size")).reset_index()
jj = a[a["joins_stage0_event"].astype(bool)].merge(fr, on=["tournament_id", "round"], how="left")
has = jj["f_n"].notna()
res["q3_joined_rows"] = int(len(jj))
res["q3_joined_rows_with_frozen_same_round"] = int(has.sum())
k = jj[has]
res["q3_joined_disjoint_from_frozen_round"] = int(((k["lf"] < k["f_es_min"]) | (k["es"] > k["f_lf_max"])).sum())
res["q3_joined_lf_before_frozen_round_lf_min"] = int((k["lf"] < k["f_lf_min"]).sum())
res["q3_joined_es_after_frozen_round_es_max"] = int((k["es"] > k["f_es_max"]).sum())
res["q3_joined_window_contains_frozen_round_window"] = int(((k["es"] <= k["f_es_min"]) & (k["lf"] >= k["f_lf_max"])).sum())
gap = (pd.to_datetime(jj["ev_date"]) - pd.to_datetime(jj["event_date"])).dt.days
u = jj[(gap.abs() >= 5) & has]
ue = pd.to_datetime(u["ev_date"]).values.astype("datetime64[D]").astype("int64")
ud = pd.to_datetime(u["event_date"]).values.astype("datetime64[D]").astype("int64")
res["q3_union_rows"] = int(((gap.abs() >= 5)).sum())
res["q3_union_rows_with_frozen_round"] = int(len(u))
res["q3_union_window_covers_frozen_round"] = int(((u["es"] <= u["f_es_min"]) & (u["lf"] >= u["f_lf_max"])).sum())
# the source's own week: the frozen round window shifted by the date gap
sh = ue - ud
res["q3_union_window_covers_shifted_round"] = int(((u["es"] <= u["f_es_min"] + np.minimum(sh, 0)) &
                                                   (u["lf"] >= u["f_lf_max"] + np.maximum(sh, 0))).sum())
res["q3_union_examples"] = u.assign(gap=sh)[["match_id", "source", "ev_date", "event_date", "round", "es", "lf",
                                             "f_es_min", "f_lf_max", "gap"]].head(5).astype(str).to_dict("records")
# frozen rows' windows unchanged
ftt = pd.read_parquet(REF_T)
cand_ref = pd.read_parquet(S0 / "C0_now/timing.parquet")
cand_ref = cand_ref[cand_ref["match_id"].isin(ref_ids)].set_index("match_id").sort_index()
ftt = ftt.set_index("match_id").sort_index()
res["q3_frozen_timeline_rows_equal"] = bool(cand_ref.equals(ftt.loc[cand_ref.index]) and len(cand_ref) == len(ftt))
# ---------------- Q4
mP, pP, tP, aP = load("C0_pre")
newP = set(aP["match_id"])
res["q4_pre_matches"] = int(len(mP))
res["q4_pre_new"] = int(len(newP))
res["q4_pre_ref_ids_all_present"] = bool(ref_ids <= set(mP["match_id"]))
res["q4_pre_new_subset_of_now_new"] = bool(newP <= newN)
dN = mN.set_index("match_id")
only_now = sorted(newN - newP)
td_only = pd.to_datetime(dN.loc[only_now, "tournament_date"])
evd_only = pd.to_datetime(aN.set_index("match_id").loc[only_now, "ev_date"])
res["q4_now_only_new"] = len(only_now)
res["q4_now_only_tournament_date_min"] = str(td_only.min().date())
res["q4_now_only_dated_before_2024_12_30"] = int((td_only < pd.Timestamp("2024-12-30")).sum())
res["q4_now_only_event_date_before_2024_12_30"] = int((evd_only < pd.Timestamp("2024-12-30")).sum())
td_pre = pd.to_datetime(mP.set_index("match_id").loc[sorted(newP), "tournament_date"])
res["q4_pre_new_tournament_date_max"] = str(td_pre.max().date())
res["q4_pre_new_on_or_after_2024_12_30"] = int((td_pre >= pd.Timestamp("2024-12-30")).sum())
cols = [c for c in MCOLS if c != "match_id"]
common = sorted(set(mP["match_id"]))
A = mP.set_index("match_id").loc[common, cols]
B = dN.loc[common, cols]
diff = (A.astype(str) != B.astype(str))
res["q4_match_rows_differ_by_column"] = {c: int(v) for c, v in diff.sum().items() if v}
res["q4_match_rows_differ_any"] = int(diff.any(axis=1).sum())
dif_ids = diff.index[diff.any(axis=1)]
res["q4_match_rows_differ_ref_vs_new"] = {"ref": int(pd.Index(dif_ids).isin(list(ref_ids)).sum()),
                                          "new": int((~pd.Index(dif_ids).isin(list(ref_ids))).sum())}
TP = tP.set_index("match_id").sort_index()
TN = tN.set_index("match_id").loc[TP.index]
res["q4_timing_rows_equal_on_common"] = bool(TP[["es", "lf", "width_days", "exact"]].equals(
    TN[["es", "lf", "width_days", "exact"]]))
pPk = pP.set_index(["match_id", "side"]).sort_index()
pNk = pN.set_index(["match_id", "side"]).loc[pPk.index]
res["q4_player_ids_equal_on_common"] = bool((pPk["player_id"] == pNk["player_id"]).all())
# the box completions: C0_pre's revised reference matches = C0_now's dated before 30 Dec 2024?
refN = mN[mN["match_id"].isin(ref_ids)].set_index("match_id")
refP = mP[mP["match_id"].isin(ref_ids)].set_index("match_id").loc[refN.index]
hb = refN["has_box"].astype(str) != refP["has_box"].astype(str)
res["q4_ref_matches_box_differs_pre_vs_now"] = int(hb.sum())
res["q4_ref_box_differs_dates"] = pd.to_datetime(refN.loc[hb, "tournament_date"]).dt.year.value_counts().to_dict()
(OUT / "checks.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
print(json.dumps(res, indent=1, default=str)[:6000])
