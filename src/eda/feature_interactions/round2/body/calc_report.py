"""Round 2, body brainstormer: the result-free numbers quoted in docs/studies/feature_interactions/round2/rebuttal_body.md.

Novelty (R^2 by OLS on the 58 inputs, model rows 2014-2021), correlations between pre-match columns, coverage and
prevalence. `a_won` is never read; seasons <= 2024 only. Run: ./python.sh src/eda/feature_interactions/round2/body/calc_report.py
Writes data/studies/feature_interactions/round2/body/calc_report.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.eda.feature_interactions.round2.body import calc_core as K  # noqa: E402
from src.eda.predictability_diagnostic import stage4_country as SC  # noqa: E402
from src.eda.feature_interactions.round0.body.counts import CONTINENT  # noqa: E402

MF = ROOT / "data/studies/surface_rating_race/model/model_frame.parquet"
OUT = ROOT / "data/studies/feature_interactions/round2/body"
OFFSET = {"EU": 1, "AF": 1, "ME": 4, "AS": 8, "OC": 10, "NA": -6, "SA": -3}   # continent-level proxy (hours)
EXTRA = {**{c: "EU" for c in ["NOR", "DEN", "BLR", "ARM", "MNE", "ALB", "KOS", "CYP", "MLT", "ISL", "LIE", "IRL"]},
         **{c: "NA" for c in ["GUA", "CRC", "ESA", "JAM", "BAR", "TTO", "BAH", "HON", "NCA", "CUB"]},
         **{c: "SA" for c in ["VEN", "COL", "BOL"]}, **{c: "AF" for c in ["NGR", "KEN", "ZIM", "MRI", "ALG", "ZAM"]},
         **{c: "ME" for c in ["IRI", "LBN", "LIB", "JOR", "KUW", "OMA", "KGZ", "TJK"]},
         **{c: "AS" for c in ["INA", "SRI", "NEP", "BAN", "MGL", "MAC"]}, **{c: "OC" for c in ["GUM", "FIJ", "NCL", "TAH"]}}


def r2_on(X: np.ndarray, y: np.ndarray) -> float:
    ok = np.isfinite(y)
    A = np.column_stack([np.ones(ok.sum()), X[ok]])
    beta, *_ = np.linalg.lstsq(A, y[ok], rcond=None)
    res = y[ok] - A @ beta
    return float(1 - res.var() / y[ok].var())


def main() -> None:
    L = K.kernels(K.add_load(K.load_long()))
    tours = L.drop_duplicates("tournament_id")[["tour", "year", "tournament_id", "tournament_name"]]
    ctry = pd.Series(SC.event_country(tours).to_numpy(), index=tours["tournament_id"]).astype(object)
    itf = K.itf_country(tours["tournament_id"]); ctry = ctry.where(ctry.notna(), pd.Series(itf.to_numpy(), index=ctry.index))
    cmap = {**CONTINENT, **EXTRA}
    L["cont"] = L["tournament_id"].map(ctry).map(cmap)
    g = L.groupby("player_id", sort=False)
    new = L["tournament_id"] != g["tournament_id"].shift(1)
    L["prev_cont"] = g["cont"].shift(1); L["prev_surface"] = g["surface"].shift(1); L["prev_indoor"] = g["indoor"].shift(1)
    L["cont_change"] = np.where(new & L["cont"].notna() & L["prev_cont"].notna(), (L["cont"] != L["prev_cont"]).astype(float), np.nan)
    o1, o2 = L["cont"].map(OFFSET), L["prev_cont"].map(OFFSET)
    dz = (o1 - o2).abs(); L["zone5"] = np.where(L["cont_change"].notna(), (np.minimum(dz, 24 - dz) >= 5).astype(float), np.nan)
    L["surf_switch"] = (new & (L["surface"] != L["prev_surface"])).astype(float)
    # all events in the previous 42 days with a known continent (I-060)
    known = L["cont"].notna().to_numpy().astype(float); obs = L["obs"].to_numpy(); allk = np.full(len(L), np.nan)
    for idx in g.indices.values():
        c = np.concatenate([[0.0], np.cumsum(known[idx])]); lo = np.searchsorted(obs[idx], obs[idx] - 42); ar = np.arange(len(idx))
        allk[idx] = ((c[ar] - c[lo]) == (ar - lo)).astype(float)
    L["known42"] = allk
    cols58 = [c for c in pq.read_schema(str(MF)).names if c.startswith("in_")]
    mf = pq.read_table(str(MF), columns=["match_id", "tour", "season"] + cols58, filters=[("season", "<=", 2024)]).to_pandas()
    mf["match_id"] = mf["match_id"].astype(str)
    cols = ["fat", "off", "on_n", "rest", "prev_x", "pastfat", "cont_change", "zone5", "surf_switch", "known42", "age"]
    for s in ("A", "B"):
        sub = L.loc[L["side"] == s, ["match_id"] + cols].drop_duplicates("match_id").set_index("match_id")
        mf = mf.join(sub.add_suffix("_" + s.lower()), on="match_id")
    d = mf[(mf["season"] >= 2014) & (mf["season"] <= 2021)].copy()
    X = d[cols58].to_numpy(dtype=float); miss = ~np.isfinite(X); X = np.where(miss, 0.0, X)
    X = np.column_stack([X, miss[:, miss.any(axis=0)].astype(float)])
    z = d["in_odds_logit"].to_numpy()
    col = {f"d_{c}": (d[c + "_a"] - d[c + "_b"]).to_numpy() for c in ["fat", "off", "on_n", "prev_x", "pastfat"]}
    st = np.log1p(d["rest_a"]) + np.log1p(d["rest_b"]); col["stale_x_z"] = ((st - st.mean()) * z).to_numpy()
    E = (np.minimum(d["in_surf_season_a"], d["in_surf_season_b"]) < np.log(4)).astype(float)
    col["i049_z_x_E"] = (E * z).to_numpy()
    sa = (d["age_a"] - 28.5).abs() + (d["age_b"] - 28.5).abs(); col["agepair_x_z"] = ((sa - sa.mean()) * z).to_numpy()
    res = {"rows_2014_2021": int(len(d)), "r2_on_58": {k: round(r2_on(X, v), 3) for k, v in col.items()},
           "coverage_finite": {k: round(float(np.isfinite(v).mean()), 3) for k, v in col.items()}}
    cc = lambda a, b: round(float(pd.Series(np.asarray(a, float)).corr(pd.Series(np.asarray(b, float)))), 3)  # noqa: E731
    fat_ok = np.where(np.isfinite(col["d_fat"]), col["d_fat"], 0.0)
    res["r2_d_off_on_58_plus_d_fat"] = round(r2_on(np.column_stack([X, fat_ok]), col["d_off"]), 3)
    res["r2_d_fat_on_58_plus_d_off"] = round(r2_on(np.column_stack([X, np.where(np.isfinite(col["d_off"]), col["d_off"], 0.0)]), col["d_fat"]), 3)
    res["corr"] = {"d_on_vs_d_off": cc(col["d_on_n"], col["d_off"]), "d_fat_vs_sets14": cc(col["d_fat"], d["in_sets_14d"]),
                   "d_off_vs_sets14": cc(col["d_off"], d["in_sets_14d"]), "d_pastfat_vs_adjperf_tpw": cc(col["d_pastfat"], d["in_adjperf_tpw_2w"]),
                   "d_pastfat_vs_form_first_won": cc(col["d_pastfat"], d["in_form_first_won"]),
                   "d_pastfat_vs_d_fat": cc(col["d_pastfat"], col["d_fat"]), "stale_vs_i049": cc(col["stale_x_z"], col["i049_z_x_E"]),
                   "agepair_vs_stale": cc(col["agepair_x_z"], col["stale_x_z"]), "agepair_vs_i049": cc(col["agepair_x_z"], col["i049_z_x_E"]),
                   "d_prev_x_vs_d_fat": cc(col["d_prev_x"], col["d_fat"]), "d_prev_x_vs_d_off": cc(col["d_prev_x"], col["d_off"])}
    by = {}
    for tour, x in d.groupby("tour"):
        dp = (x["prev_x_a"] - x["prev_x_b"])
        by[tour] = {"n": int(len(x)), "prev_x_nonzero": round(float((dp.abs() > 0).mean()), 3),
                    "prev_x_missing": round(float(dp.isna().mean()), 3), "E_dprev_x_sq": round(float((dp ** 2).mean()), 4),
                    "first_match_cont_change_either": round(float(((x["cont_change_a"] == 1) | (x["cont_change_b"] == 1)).mean()), 4),
                    "zone5_either": round(float(((x["zone5_a"] == 1) | (x["zone5_b"] == 1)).mean()), 4),
                    "zone5_rest_le5_either": round(float((((x["zone5_a"] == 1) & (x["rest_a"] <= 5))
                                                          | ((x["zone5_b"] == 1) & (x["rest_b"] <= 5))).mean()), 4),
                    "cont_defined_both_when_first": round(float((x["cont_change_a"].notna() & x["cont_change_b"].notna()).sum()
                                                                / max(1, ((x["on_n_a"] == 0) & (x["on_n_b"] == 0)).sum())), 3),
                    "known42_both": round(float(((x["known42_a"] == 1) & (x["known42_b"] == 1)).mean()), 3),
                    "surf_switch_either": round(float(((x["surf_switch_a"] == 1) | (x["surf_switch_b"] == 1)).mean()), 4),
                    "rest_ge21_either": round(float(((x["rest_a"] >= 21) | (x["rest_b"] >= 21)).mean()), 4)}
    res["by_tour"] = by
    res["unmapped_country_share_of_rows"] = round(float(L["cont"].isna().mean()), 3)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "calc_report.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
