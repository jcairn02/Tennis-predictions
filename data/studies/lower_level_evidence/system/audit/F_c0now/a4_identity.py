"""Role E audit of C0_now, part 4: identity. Routes, new ids, possible splits and merges, the crosswalks, an error-rate
proxy (one id in two main draws in one week), and what the chain's own identity repair (repair_data.repair_tables, run
by rebuild.py and Stage 4) would do to the candidate (its alias step replicated, read-only).
Names, ids, dates and counts only; no outcome. Run: ./python.sh data/studies/lower_level_evidence/system/audit/F_c0now/a4_identity.py
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
from src.eda.match_timing import srcc_common as K  # noqa: E402
from src.eda.feature_alpha_audit.repair_data import name_key  # noqa: E402

AUD = ROOT / "data/studies/lower_level_evidence/system/audit/F_c0now"
CAND = ROOT / "data/studies/lower_level_evidence/system/stage0/C0_now"
OUT: dict = {}
adds = pd.read_parquet(CAND / "additions.parquet")
m = pd.read_parquet(CAND / "stage0_matches.parquet", columns=["match_id", "tour", "tournament_id", "tournament_date",
                                                               "round", "qualifying", "map_level", "source"])
ref_ids = set(pd.read_parquet(LC.STAGE0_DIR / "stage0_matches.parquet", columns=["match_id"])["match_id"])
m["new"] = ~m["match_id"].isin(ref_ids)
mp = pd.read_parquet(CAND / "stage0_match_players.parquet", columns=["match_id", "player_id", "player_name", "country",
                                                                      "age"])
ref_mp = mp[mp["match_id"].isin(ref_ids)]
ref_players = set(ref_mp["player_id"])

# ---------------------------------------------------------------- 1. routes and new ids
r = pd.concat([adds[["match_id", "source", "tour", "x1", "route1", "p1", "c1"]].set_axis(
    ["match_id", "source", "tour", "x", "route", "name", "c"], axis=1),
    adds[["match_id", "source", "tour", "x2", "route2", "p2", "c2"]].set_axis(
    ["match_id", "source", "tour", "x", "route", "name", "c"], axis=1)], ignore_index=True)
OUT["player_rows_by_source_route"] = r.groupby(["source", "route"]).size().rename("n").reset_index().to_dict("records")
r["in_ref"] = r["x"].isin(ref_players)
OUT["route_vs_in_ref"] = r.groupby(["route", "in_ref"]).size().rename("n").reset_index().to_dict("records")
newids = r[~r["in_ref"]].drop_duplicates("x").copy()
newids["key"] = newids["name"].map(name_key)
OUT["distinct_new_ids"] = int(len(newids))
OUT["distinct_new_ids_by_source_tour"] = newids.groupby(["source", "tour"]).size().rename("n").reset_index().to_dict(
    "records")
OUT["new_ids_namespace_tags"] = newids["x"].str.extract(r"^(\w+:\w+):")[0].value_counts().to_dict()
# possible splits: a new id whose exact name key a frozen player of the tour holds; or another new id holds
refkeys = ref_mp.merge(m[["match_id", "tour"]], on="match_id").assign(key=lambda d: d["player_name"].map(name_key))
refkeys = refkeys.drop_duplicates(["tour", "key", "player_id"])
nref = refkeys.groupby(["tour", "key"])["player_id"].nunique()
newids["ref_same_name"] = pd.MultiIndex.from_frame(newids[["tour", "key"]]).map(lambda k: int(nref.get(k, 0)))
OUT["new_ids_with_a_frozen_namesake"] = int((newids["ref_same_name"] > 0).sum())
OUT["new_ids_with_a_frozen_namesake_by_source"] = newids[newids["ref_same_name"] > 0].groupby("source").size().to_dict()
nk = newids.groupby(["tour", "key"])["x"].nunique()
newids["other_new_same_name"] = pd.MultiIndex.from_frame(newids[["tour", "key"]]).map(lambda k: int(nk.get(k, 1)) - 1)
dupn = newids[newids["other_new_same_name"] > 0]
OUT["new_ids_sharing_exact_name_with_another_new_id"] = int(len(dupn))
srcs = dupn.groupby(["tour", "key"])["source"].agg(lambda s: ",".join(sorted(set(s))))
OUT["new_name_groups_by_sources"] = srcs.value_counts().head(10).to_dict()
OUT["examples_new_id_name_groups_cross_source"] = dupn[dupn.set_index(["tour", "key"]).index.map(
    lambda k: "," in srcs.get(k, ""))].sort_values(["tour", "key"]).head(12)[["x", "name", "c", "source"]].to_dict(
    "records")

# ---------------------------------------------------------------- 2. crosswalks
xw_res = {}
for f in sorted((CAND / "evidence").glob("crosswalk_*.csv")):
    src = f.stem[len("crosswalk_"):]
    x = pd.read_csv(f, dtype={"src": str, "s0": str})
    x["grade"] = [K.name_grade(a, b) for a, b in zip(x["src_name"], x["s0_name"])]
    x["share"] = x["n"] / x["tot"]
    res = {"rows": int(len(x)), "grade_counts": x["grade"].value_counts().sort_index().to_dict(),
           "claims": x["claim"].value_counts().to_dict(),
           "s0_claimed_by_several_src": int((x.groupby("s0")["src"].nunique() > 1).sum()),
           "src_name_to_several_s0": 0}
    x["skey"], x["s0key"] = x["src_name"].map(name_key), x["s0_name"].map(name_key)
    g = x.groupby("skey").agg(s0n=("s0", "nunique"), s0keys=("s0key", "nunique"))
    res["src_name_to_several_s0"] = int((g["s0n"] > 1).sum())
    res["src_name_to_several_s0_with_different_s0_names"] = int(((g["s0n"] > 1) & (g["s0keys"] > 1)).sum())
    low = x[x["grade"] <= 1].sort_values("n", ascending=False)
    res["grade_le1_rows"] = int(len(low))
    res["grade_le1_with_n_ge_3"] = int((low["n"] >= 3).sum())
    res["grade_le1_examples"] = low.head(8)[["src", "src_name", "s0", "s0_name", "n", "tot", "claim"]].astype(str) \
        .to_dict("records")
    sh = x[x["claim"].str.contains("shared")].sort_values("s0")
    res["shared_examples"] = sh.head(6)[["src", "src_name", "s0", "s0_name", "n", "claim"]].astype(str).to_dict(
        "records")
    xw_res[src] = res
OUT["crosswalks"] = xw_res
# the same Stage 0 id reached from two different source ids of one source in the new rows (name route included)
lp = r[r["in_ref"]].copy()
OUT["new_rows_on_frozen_ids_by_route"] = lp["route"].value_counts().to_dict()
lp["key"] = lp["name"].map(name_key)
s0name = refkeys.drop_duplicates("player_id").set_index("player_id")["player_name"]
sub = lp.drop_duplicates(["x", "key"]).copy()
sub["s0_name"] = sub["x"].map(s0name)
sub["grade"] = [K.name_grade(a, b) for a, b in zip(sub["name"], sub["s0_name"])]
OUT["frozen_id_new_rows_name_grade_by_route"] = sub.groupby(["route", "grade"]).size().rename("n").reset_index() \
    .to_dict("records")
OUT["frozen_id_new_rows_grade_le1_examples"] = sub[sub["grade"] <= 1].head(15)[
    ["route", "source", "x", "name", "s0_name", "c"]].astype(str).to_dict("records")

# ---------------------------------------------------------------- 3. error proxy: one id, two main draws, one week
md = pd.concat([m[["match_id", "tournament_id", "tournament_date", "round", "qualifying", "new"]].assign(pid=a)
                for a in (pd.read_parquet(CAND / "stage0_matches.parquet", columns=["player_a_id"])["player_a_id"],
                          pd.read_parquet(CAND / "stage0_matches.parquet", columns=["player_b_id"])["player_b_id"])],
               ignore_index=True)
md = md[~md["qualifying"].astype(bool) & md["round"].ne("RR")]
wk = md.groupby(["pid", "tournament_date"]).agg(ev=("tournament_id", "nunique"), anynew=("new", "any"),
                                                allnew=("new", "all")).reset_index()
OUT["player_weeks_main_draw_frozen_only"] = int((~wk["anynew"]).sum())
OUT["conflicts_two_main_draws_one_week_frozen_only"] = int(((wk["ev"] > 1) & ~wk["anynew"]).sum())
OUT["player_weeks_main_draw_with_new"] = int(wk["anynew"].sum())
OUT["conflicts_two_main_draws_one_week_with_new"] = int(((wk["ev"] > 1) & wk["anynew"]).sum())
# by the route the id came through in its new match(es) that week
rr = r[["match_id", "x", "route", "source"]].merge(m[["match_id", "tournament_date"]], on="match_id")
cw = wk[(wk["ev"] > 1) & wk["anynew"]].merge(rr, left_on=["pid", "tournament_date"],
                                             right_on=["x", "tournament_date"], how="left")
OUT["conflicts_with_new_by_route_source"] = cw.drop_duplicates(["pid", "tournament_date", "route", "source"]).groupby(
    ["route", "source"]).size().rename("n").reset_index().to_dict("records")
rw = rr.merge(wk[["pid", "tournament_date"]], left_on=["x", "tournament_date"], right_on=["pid", "tournament_date"])
OUT["main_draw_player_weeks_with_new_by_route"] = rw.drop_duplicates(["x", "tournament_date", "route"]).groupby(
    "route").size().to_dict()
cw.drop_duplicates(["pid", "tournament_date"]).to_csv(AUD / "identity_two_main_draws_one_week.csv", index=False)

# ---------------------------------------------------------------- 4. the chain's identity repair (alias step, replicated)
q = mp.merge(m[["match_id", "tour", "source", "tournament_date"]], on="match_id")
q["name_key"] = q["player_name"].map(name_key)
q["country"] = q["country"].astype("string").str.upper().str.strip().replace({"": pd.NA})
q["by"] = pd.to_datetime(q["tournament_date"]).dt.year - pd.to_numeric(q["age"], errors="coerce")
trusted = q[q["source"].eq("sackmann") & q["name_key"].ne("")]
tg = trusted.groupby(["tour", "name_key"])
ids = tg["player_id"].agg(lambda s: tuple(sorted(set(s))))
years = tg["by"].median()
ctry = tg["country"].agg(lambda s: set(s.dropna().astype(str)))


def aliases(rows: pd.DataFrame) -> pd.DataFrame:
    """repair_tables' alias rule on the non-sackmann rows: (tour, player_id, name_key) -> the one sackmann id with that
    exact name, unless the age or country contradicts."""
    g = rows.groupby(["tour", "player_id", "name_key"], sort=False)
    a = g.agg(n=("match_id", "size"), oc=("country", lambda s: set(s.dropna().astype(str))),
              ymin=("by", "min"), ymax=("by", "max")).reset_index()
    a = a[a["name_key"].ne("")]
    k = list(zip(a["tour"], a["name_key"]))
    a["cands"] = pd.Series([ids.get(t, ()) for t in k], index=a.index, dtype=object)
    a["one"] = a["cands"].map(len).eq(1)
    a["target"] = a["cands"].map(lambda c: c[0] if len(c) == 1 else None)
    y0 = pd.Series([years.get(t, np.nan) for t in k], index=a.index).astype(float)
    a["bad_age"] = np.isfinite(y0) & (((a["ymin"] - y0).abs() > 1.5) | ((a["ymax"] - y0).abs() > 1.5))
    kc = pd.Series([ctry.get(t, set()) for t in k], index=a.index, dtype=object)
    a["bad_country"] = [bool(o and kk and not (set(o) & set(kk))) for o, kk in zip(a["oc"], kc)]
    a["alias"] = a["one"] & a["target"].ne(a["player_id"]) & ~a["bad_age"] & ~a["bad_country"]
    a["several"] = a["cands"].map(len) > 1
    return a


ns = q[q["source"].ne("sackmann")]
al_c = aliases(ns)
al_r = aliases(ns[ns["match_id"].isin(ref_ids)])
newrows = set(adds["match_id"])
# rows of new matches the repair would remap
ns_new = ns[ns["match_id"].isin(newrows)]
key_cols = ["tour", "player_id", "name_key"]
remap = ns_new.merge(al_c.loc[al_c["alias"], key_cols + ["target"]], on=key_cols)
OUT["repair_new_match_player_rows"] = int(len(ns_new))
OUT["repair_new_match_player_rows_remapped"] = int(len(remap))
OUT["repair_distinct_ids_remapped_in_new_rows"] = int(remap[["player_id", "target"]].drop_duplicates().shape[0])
rm = remap.merge(r[["match_id", "x", "route", "source"]].rename(columns={"source": "src"}),
                 left_on=["match_id", "player_id"], right_on=["match_id", "x"], how="left")
OUT["repair_remapped_new_rows_by_F_route"] = rm.groupby(["route"]).size().to_dict()
OUT["repair_remapped_new_rows_from_frozen_id_to_other_frozen_id"] = int(rm["player_id"].isin(ref_players).sum())
OUT["repair_remapped_examples_from_frozen_id"] = rm[rm["player_id"].isin(ref_players)].drop_duplicates(
    ["player_id", "target"]).head(10)[["player_id", "target", "name_key", "route", "src"]].astype(str).to_dict("records")
OUT["repair_remapped_examples_new_id"] = rm[~rm["player_id"].isin(ref_players)].drop_duplicates(
    ["player_id", "target"]).head(10)[["player_id", "target", "name_key", "route", "src"]].astype(str).to_dict("records")
# frozen rows: does the alias decision of a (tour, id, name) group that holds frozen rows change?
cmp_ = al_r[key_cols + ["alias", "target"]].merge(al_c[key_cols + ["alias", "target"]], on=key_cols,
                                                   suffixes=("_ref", "_cand"))
chg = cmp_[(cmp_["alias_ref"] != cmp_["alias_cand"]) | (cmp_["alias_ref"] & (cmp_["target_ref"] != cmp_["target_cand"]))]
OUT["repair_groups_with_frozen_rows"] = int(len(cmp_))
OUT["repair_frozen_groups_decision_changed"] = int(len(chg))
fz = ns[ns["match_id"].isin(ref_ids)].merge(chg[key_cols], on=key_cols)
OUT["repair_frozen_player_rows_decision_changed"] = int(len(fz))
OUT["repair_frozen_rows_changed_in_frame_matches"] = int(fz["match_id"].isin(
    set(pd.read_parquet(LC.FRAME, columns=["match_id"])["match_id"])).sum())
OUT["repair_frozen_decision_changed_examples"] = chg.head(10).astype(str).to_dict("records")
(AUD / "a4_results.json").write_text(json.dumps(OUT, indent=1, default=str), encoding="utf-8")
print(json.dumps(OUT, indent=1, default=str)[:30000])
