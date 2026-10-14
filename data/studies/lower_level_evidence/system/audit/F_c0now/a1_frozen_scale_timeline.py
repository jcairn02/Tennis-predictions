"""Role E audit of C0_now, part 1: the frozen part (matches + timeline), the scale of the additions, statuses, and the
timeline of new matches. Read-only on every input; writes only into this folder.

No outcome of a 2025-2026 match is printed or used: frozen-vs-candidate comparisons are equality counts per column.
Run from the repository root: ./python.sh data/studies/lower_level_evidence/system/audit/F_c0now/a1_frozen_scale_timeline.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from src.eda.lower_level_evidence import common as LC  # noqa: E402

AUD = ROOT / "data/studies/lower_level_evidence/system/audit/F_c0now"
CAND = ROOT / "data/studies/lower_level_evidence/system/stage0/C0_now"
OUT: dict = {}


def eq(a: pd.Series, b: pd.Series) -> np.ndarray:
    """Element-wise equality with missing == missing (values never printed)."""
    a = a.reset_index(drop=True)
    b = b.reset_index(drop=True)
    na, nb = a.isna().to_numpy(), b.isna().to_numpy()
    try:
        same = (a.astype(object).to_numpy() == b.astype(object).to_numpy())
    except Exception:
        same = (a.astype(str).to_numpy() == b.astype(str).to_numpy())
    same = np.asarray(same, dtype=bool)
    return (same & ~na & ~nb) | (na & nb)


# ------------------------------------------------------------------ 1. the frozen part: matches
ref = pd.read_parquet(LC.STAGE0_DIR / "stage0_matches.parquet")
cm = pd.read_parquet(CAND / "stage0_matches.parquet")
OUT["matches_ref"], OUT["matches_cand"] = int(len(ref)), int(len(cm))
OUT["cand_ids_unique"] = bool(not cm["match_id"].duplicated().any())
ref_ids = pd.Index(ref["match_id"])
in_cand = ref_ids.isin(cm["match_id"])
OUT["ref_ids_missing_in_cand"] = int((~in_cand).sum())
OUT["dtypes_equal"] = {c: (str(ref[c].dtype) == str(cm[c].dtype)) for c in ref.columns}
OUT["columns_equal"] = list(ref.columns) == list(cm.columns)
c_al = cm.set_index("match_id").loc[ref["match_id"]].reset_index()
diff_cols = {}
changed = np.zeros(len(ref), dtype=bool)
for c in ref.columns:
    if c in ("match_id", "order"):
        continue
    e = eq(ref[c], c_al[c])
    diff_cols[c] = int((~e).sum())
    changed |= ~e
OUT["ref_matches_changed_any_column_except_order"] = int(changed.sum())
OUT["ref_mismatch_by_column"] = {k: v for k, v in diff_cols.items() if v}
ch = ref.loc[changed, ["match_id", "tour", "year", "map_level", "tournament_date", "has_box"]].copy()
ch["bucket"] = LC.bucket(ch["map_level"])
ch["holdout"] = LC.in_holdout(ch["tournament_date"])
OUT["ref_changed_by_bucket_holdout"] = ch.groupby(["tour", "bucket", "holdout"]).size().rename("n").reset_index() \
    .to_dict("records")
OUT["ref_changed_has_box_before"] = ch["has_box"].value_counts().to_dict()
# the box layer's applied reference matches
L = pd.read_parquet(CAND / "box_layers.parquet")
applied_ref = set(L.loc[L["applied"].astype(bool) & L["reference_match"].astype(bool), "match_id"])
OUT["box_layer_applied_reference_matches"] = len(applied_ref)
OUT["changed_equals_applied_set"] = bool(set(ch["match_id"]) == applied_ref)
OUT["changed_not_in_applied"] = int(len(set(ch["match_id"]) - applied_ref))
OUT["applied_not_changed"] = int(len(applied_ref - set(ch["match_id"])))
# facts unchanged on the changed matches (only box columns may move)
box_cols = {"has_box", "box_status", "sv_gms_incl_tb"}
OUT["changed_columns_outside_box_cols"] = {k: v for k, v in diff_cols.items() if v and k not in box_cols}
# relative order of the frozen matches
pos = c_al["order"].to_numpy()
ref_order = ref["order"].to_numpy()
o = np.argsort(pos, kind="stable")
OUT["frozen_relative_order_preserved"] = bool(np.all(np.diff(ref_order[o]) > 0))
OUT["ref_order_is_0_to_n"] = bool(np.array_equal(np.sort(ref_order), np.arange(len(ref))))
OUT["cand_order_is_0_to_n"] = bool(np.array_equal(np.sort(cm["order"].to_numpy()), np.arange(len(cm))))
OUT["cand_rows_sorted_by_order"] = bool(cm["order"].is_monotonic_increasing)
OUT["ref_rows_sorted_by_order"] = bool(ref["order"].is_monotonic_increasing)
# frame matches: present and unchanged (all columns but order)
fr = pd.read_parquet(LC.FRAME, columns=["match_id", "tour", "season"])
OUT["frame_matches"] = int(len(fr))
OUT["frame_matches_in_cand"] = int(fr["match_id"].isin(cm["match_id"]).sum())
OUT["frame_matches_changed"] = int(fr["match_id"].isin(set(ch["match_id"])).sum())

# ------------------------------------------------------------------ 2. the scale of the additions
new = cm[~cm["match_id"].isin(ref_ids)].copy()
new["bucket"] = LC.bucket(new["map_level"])
new["holdout"] = LC.in_holdout(new["tournament_date"])
new["period"] = np.select([new["year"] <= 2017, new["year"] <= 2024], ["2010-2017", "2018-2024"], "2025-2026")
OUT["new_matches"] = int(len(new))
OUT["new_by_bucket"] = new["bucket"].value_counts().to_dict()
OUT["new_in_MAIN_or_TEAM"] = int(new["bucket"].isin(["MAIN", "TEAM"]).sum())
OUT["new_year_vs_holdout_inconsistent"] = int(((new["year"] >= 2025) != new["holdout"]).sum())
OUT["new_year_min_max"] = [int(new["year"].min()), int(new["year"].max())]
OUT["new_tdate_max"] = str(new["tournament_date"].max())
adds = pd.read_parquet(CAND / "additions.parquet")
OUT["additions_rows"] = int(len(adds))
OUT["additions_ids_equal_new_ids"] = bool(set(adds["match_id"]) == set(new["match_id"]))
src = adds.set_index("match_id")["source"]
new["src"] = new["match_id"].map(src)
OUT["new_source_col_equals_additions_source"] = bool((new["source"] == new["src"]).all())
t1 = new.groupby(["tour", "year", "bucket", "src", "status"]).size().rename("n").reset_index()
t1.to_csv(AUD / "new_by_tour_year_bucket_source_status.csv", index=False)
t2 = new.groupby(["tour", "year", "bucket"]).agg(new=("match_id", "size"), new_with_box=("has_box", "sum")).reset_index()
refc = ref.assign(bucket=LC.bucket(ref["map_level"])).groupby(["tour", "year", "bucket"]).agg(
    ref=("match_id", "size"), ref_with_box=("has_box", "sum")).reset_index()
t2 = refc.merge(t2, on=["tour", "year", "bucket"], how="outer").fillna(0)
for c in ("ref", "ref_with_box", "new", "new_with_box"):
    t2[c] = t2[c].astype(int)
t2["new_share_of_total"] = (t2["new"] / (t2["ref"] + t2["new"]).replace(0, np.nan)).round(3)
t2.to_csv(AUD / "ref_vs_new_by_tour_year_bucket.csv", index=False)
t3 = new.groupby(["tour", "bucket", "period"]).agg(new=("match_id", "size"), new_with_box=("has_box", "sum")).reset_index()
t3.to_csv(AUD / "new_by_tour_bucket_period.csv", index=False)
OUT["new_by_tour_bucket_period"] = t3.to_dict("records")
OUT["new_with_box_by_source"] = new.groupby("src")["has_box"].agg(["size", "sum"]).astype(int).to_dict("index")
OUT["new_evaluation_flag_true"] = int(new["evaluation"].sum())

# ------------------------------------------------------------------ 5. statuses
OUT["new_status_by_source"] = new.groupby(["src", "status"]).size().rename("n").reset_index().to_dict("records")
OUT["new_status_detail_by_source"] = new.groupby(["src", "status_detail"]).size().rename("n").reset_index() \
    .to_dict("records")
OUT["new_score_flag_by_source"] = new[new["score_flag"].astype(str).ne("")].groupby(["src", "score_flag"]).size() \
    .rename("n").reset_index().to_dict("records")
OUT["new_walkover_status"] = int(new["status"].eq("walkover").sum())
OUT["ref_status_by_bucket"] = ref.assign(bucket=LC.bucket(ref["map_level"])).groupby(["bucket", "status"]).size() \
    .rename("n").reset_index().to_dict("records")
OUT["new_status_by_bucket"] = new.groupby(["bucket", "status"]).size().rename("n").reset_index().to_dict("records")
# the raw source status hints: retirements carried? (counts only)
OUT["new_score_has_RET_token"] = int(new["score"].astype(str).str.contains(r"\bRET\b").sum())
OUT["new_score_has_DEF_token"] = int(new["score"].astype(str).str.contains(r"\bDEF\b").sum())
OUT["new_score_has_WO_token"] = int(new["score"].astype(str).str.contains(r"W/O|w/o|walkover", regex=True).sum())

# ------------------------------------------------------------------ 6. the timeline
rt = pd.read_parquet(LC.TIMING)
ct = pd.read_parquet(CAND / "timing.parquet")
OUT["timing_rows_ref"], OUT["timing_rows_cand"] = int(len(rt)), int(len(ct))
OUT["timing_ids_unique"] = bool(not ct["match_id"].duplicated().any())
OUT["timing_ids_equal_match_ids"] = bool(set(ct["match_id"]) == set(cm["match_id"]))
OUT["ref_timing_ids_equal_ref_match_ids"] = bool(set(rt["match_id"]) == set(ref["match_id"]))
ct_al = ct.set_index("match_id").loc[rt["match_id"]].reset_index()
tdiff = {}
for c in rt.columns:
    if c == "match_id":
        continue
    tdiff[c] = int((~eq(rt[c], ct_al[c])).sum())
OUT["ref_timing_mismatch_by_column"] = {k: v for k, v in tdiff.items() if v}
OUT["ref_timing_dtypes_equal"] = {c: str(rt[c].dtype) == str(ct[c].dtype) for c in rt.columns if
                                  str(rt[c].dtype) != str(ct[c].dtype)}
nt = ct[ct["match_id"].isin(set(new["match_id"]))].copy()
nt = nt.merge(new[["match_id", "src", "bucket", "period"]], on="match_id")
OUT["new_timing_rows"] = int(len(nt))
OUT["new_lf_lt_es"] = int((nt["lf"] < nt["es"]).sum())
OUT["new_obs_outside"] = int(((nt["obs"] < nt["es"]) | (nt["obs"] > nt["lf"])).sum())
OUT["new_nonfinite"] = int((~np.isfinite(nt[["es", "lf", "obs"]].to_numpy(float))).any(axis=1).sum())
nt["w"] = nt["lf"] - nt["es"] + 1
nt["es_rel"] = nt["es"] - nt["start"]
nt["lf_rel"] = nt["lf"] - nt["start"]
OUT["new_width_matches_width_days"] = bool(np.allclose(nt["w"], nt["width_days"]))
OUT["new_window_basis_by_source"] = nt.groupby(["src", "window_basis"]).size().rename("n").reset_index() \
    .to_dict("records")
q = nt.groupby(["src", "exact"]).agg(n=("w", "size"), w_min=("w", "min"), w_med=("w", "median"), w_max=("w", "max"),
                                     es_rel_min=("es_rel", "min"), es_rel_med=("es_rel", "median"),
                                     lf_rel_med=("lf_rel", "median"), lf_rel_max=("lf_rel", "max")).reset_index()
q.to_csv(AUD / "new_timing_by_source_exact.csv", index=False)
OUT["new_timing_by_source_exact"] = q.to_dict("records")
OUT["new_rejected_links_by_source"] = nt.groupby("src")["rejected_links"].sum().astype(int).to_dict()
OUT["new_demoted_by_source"] = nt[nt["demoted"].astype(str).ne("")].groupby("src").size().to_dict()
# the frozen timeline's widths by class (tour, level, qualifying, round), exact and not
rt["w"] = rt["lf"] - rt["es"] + 1
cls = ["tour", "level", "qualifying", "round"]
fw = rt.groupby(cls + ["exact"])["w"].median().rename("ref_w_med").reset_index()
fw_any = rt.groupby(cls)["w"].median().rename("ref_w_med_any").reset_index()
fwn = rt[~rt["exact"].astype(bool)].groupby(cls)["w"].median().rename("ref_w_med_nonexact").reset_index()
nt2 = nt.merge(fw, on=cls + ["exact"], how="left").merge(fw_any, on=cls, how="left").merge(fwn, on=cls, how="left")
OUT["new_with_no_ref_class"] = int(nt2["ref_w_med_any"].isna().sum())
OUT["new_narrower_than_ref_class_same_exactness"] = int((nt2["w"] < nt2["ref_w_med"]).sum())
OUT["new_nonexact_narrower_than_ref_nonexact_median"] = int(((~nt2["exact"].astype(bool)) & (nt2["w"] < nt2["ref_w_med_nonexact"])).sum())
nar = nt2[(~nt2["exact"].astype(bool)) & (nt2["w"] < nt2["ref_w_med_nonexact"])]
OUT["new_nonexact_narrower_examples_by_class"] = nar.groupby(cls + ["src"]).agg(
    n=("w", "size"), new_w=("w", "median"), ref_w=("ref_w_med_nonexact", "first")).reset_index() \
    .sort_values("n", ascending=False).head(15).to_dict("records")
ex = nt2[nt2["exact"].astype(bool)]
OUT["new_exact_width_distribution"] = ex["w"].value_counts().sort_index().to_dict()
OUT["ref_exact_width_distribution"] = rt.loc[rt["exact"].astype(bool), "w"].value_counts().sort_index().head(10).to_dict()
OUT["ref_nonexact_width_quantiles"] = rt.loc[~rt["exact"].astype(bool), "w"].quantile([.05, .25, .5, .75, .95]).to_dict()
OUT["new_nonexact_width_quantiles"] = nt.loc[~nt["exact"].astype(bool), "w"].quantile([.05, .25, .5, .75, .95]).to_dict()
# a new match's window against its own event in the frozen timeline (events it joins)
jn = adds[adds["joins_stage0_event"].astype(bool)][["match_id", "event_tid", "event_date"]]
ev = rt.merge(ref[["match_id"]], on="match_id")[["match_id", "tournament_id", "tournament_date", "es", "lf"]]
span = ev.groupby(["tournament_id", "tournament_date"]).agg(ev_es=("es", "min"), ev_lf=("lf", "max")).reset_index()
span = span.rename(columns={"tournament_id": "ev_tid", "tournament_date": "ev_tdate"})
nj = nt.merge(jn, on="match_id").merge(span, left_on=["event_tid", "event_date"], right_on=["ev_tid", "ev_tdate"],
                                       how="left")
OUT["new_joining_events"] = int(len(nj))
OUT["new_joining_event_not_found_in_frozen_timeline"] = int(nj["ev_lf"].isna().sum())
OUT["new_joining_tournament_id_differs_from_event_tid"] = int((nj["tournament_id"].astype(str)
                                                              != nj["event_tid"].astype(str)).sum())
OUT["new_joining_tournament_date_differs_from_event_date"] = int(
    (pd.to_datetime(nj["tournament_date"]) != pd.to_datetime(nj["event_date"])).sum())
OUT["new_joining_lf_after_event_last_lf"] = int((nj["lf"] > nj["ev_lf"]).sum())
OUT["new_joining_lf_after_event_last_lf_by_7d"] = int((nj["lf"] > nj["ev_lf"] + 7).sum())
OUT["new_joining_es_before_event_first_es_by_7d"] = int((nj["es"] < nj["ev_es"] - 7).sum())
# source day vs the tournament date the match was given (wrong-week placement risk), sources with a day
ad = adds.copy()
ad["day_rel"] = (pd.to_datetime(ad["day"]) - pd.to_datetime(ad["event_date"])).dt.days
OUT["adds_day_rel_quantiles_by_source"] = ad.groupby("source")["day_rel"].describe(
    percentiles=[.001, .01, .5, .99, .999]).round(1).reset_index().to_dict("records")
OUT["adds_day_rel_outside_m10_p21_by_source"] = ad[(ad["day_rel"] < -10) | (ad["day_rel"] > 21)].groupby("source") \
    .size().to_dict()
OUT["adds_day_rel_ge7_joining_stage0_by_source"] = ad[(ad["day_rel"] >= 7) & ad["joins_stage0_event"].astype(bool)] \
    .groupby("source").size().to_dict()
OUT["adds_day_rel_ge7_not_joining_by_source"] = ad[(ad["day_rel"] >= 7) & ~ad["joins_stage0_event"].astype(bool)] \
    .groupby("source").size().to_dict()
OUT["adds_day_rel_le_m4_by_source"] = ad[(ad["day_rel"] <= -4)].groupby("source").size().to_dict()
# one tournament id with several dates among the new events
ne = new.groupby("tournament_id")["tournament_date"].nunique()
OUT["new_tournament_ids_with_several_dates"] = int((ne > 1).sum())
(AUD / "a1_results.json").write_text(json.dumps(OUT, indent=1, default=str), encoding="utf-8")
print(json.dumps(OUT, indent=1, default=str)[:20000])
