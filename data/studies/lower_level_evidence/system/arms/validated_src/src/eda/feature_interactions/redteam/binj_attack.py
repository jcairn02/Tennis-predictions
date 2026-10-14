"""Red team (S3): result-free attacks on B-INJ (no a_won is ever loaded; model rows 2013-2024, plus feature-only
coverage of 2025-2026 from the registered deployment columns and Stage 0's pre-match age).

Parts (each prints a compact summary and writes data/studies/feature_interactions/redteam/attack_<part>.json):
    orient    side labels vs Stage 0 player_a_id; the model frame's A vs Stage 0's A; exact negation under a swap
    timing    E's walk-forward boundary: max lf + 1 of the source rows <= T_Y <= min es of the target year
    proxy     |r| of x with the 58 inputs and the model's eta; R2 on the 58 inputs; x by season, band, entry, level, tour;
              player concentration
    covid     returns and E around the 2020 break; share of x's mass owed to returns of Mar-Dec 2020
    artefact  return definition, walkovers/retirements before a break, E's binding, gaps, coverage of 2026
Run: ./python.sh src/eda/feature_interactions/redteam/binj_attack.py
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions.history import long_table  # noqa: E402
from src.eda.feature_interactions.panel import SOURCES  # noqa: E402
from src.eda.feature_interactions.redteam import binj_redo as R  # noqa: E402
from src.eda.feature_interactions.redteam import redo_run as RR  # noqa: E402

OUT = C.OUT / "redteam"
DAY0 = pd.Timestamp("1970-01-01")


def dump(name: str, obj: dict) -> None:
    C.write_json(OUT / f"attack_{name}.json", obj)
    print(name, json.dumps(obj, default=float)[:1800])


def setup():
    L = long_table()
    H = R.base(L)
    R.layoff_state(H)
    M = RR.model_frame()
    ra, rb = R.model_rows(H, M["match_id"].to_numpy(), M["player_a_id"].to_numpy(), M["player_b_id"].to_numpy())
    X = pd.read_parquet(OUT / "redo_binj_2024.parquet")
    assert (X["match_id"].to_numpy() == M["match_id"].to_numpy()).all()
    return L, H, M, ra, rb, X


def orient(H, M, ra, rb, X) -> None:
    side = H["side"].astype(str).to_numpy()
    out = {"history_side_A_is_player_a": bool((side[ra] == "A").all()), "history_side_B_is_player_b":
           bool((side[rb] == "B").all())}
    f = pd.read_parquet(C.MODEL_FRAME, columns=["match_id", "season", "in_elo_overall", "in_age"])
    f = f[f["season"] <= 2024].reset_index(drop=True)
    d = f["in_elo_overall"].to_numpy(float) - (M["elo_R_a"] - M["elo_R_b"]).to_numpy(float)
    out["in_elo_overall_minus_pieces_RaRb_maxabs"] = float(np.nanmax(np.abs(d)))
    p = pd.read_parquet(SOURCES["stage0_players"], columns=["match_id", "player_id", "age"])
    p["match_id"] = p["match_id"].astype(str)
    age = p.set_index(p["match_id"] + "#" + p["player_id"].astype(str))["age"]
    aa = age.reindex(M["match_id"] + "#" + M["player_a_id"].astype(str)).to_numpy(float)
    ab = age.reindex(M["match_id"] + "#" + M["player_b_id"].astype(str)).to_numpy(float)
    ia = f["in_age"].to_numpy(float)
    ok = np.isfinite(ia) & np.isfinite(aa - ab)
    out["corr_in_age_vs_stage0_ageA_minus_ageB"] = float(np.corrcoef(ia[ok], (aa - ab)[ok])[0, 1])
    disc = M["season"].between(2014, 2021).to_numpy()
    Z = np.column_stack([R.standardise(-X[c].to_numpy(float), disc) for c in ("d43", "d44", "d45")])
    xs = -np.nansum(Z, axis=1)
    out["swap_x_equals_minus_x_maxabs"] = float(np.nanmax(np.abs(xs + X["x"].to_numpy(float))))
    dump("orient", out)


def timing(H) -> None:
    T = R.T_of_year(H)
    lf, ty, es = H["lf"].to_numpy(float), H["tyear"].to_numpy(), H["es"].to_numpy(float)
    ok = np.isfinite(H["gap"].to_numpy(float))
    rows = []
    for y in sorted(T):
        src = ok & (lf + 1 <= T[y]) & (ty >= y - 3) & (ty <= y - 1)
        tgt = ty == y
        if not tgt.any() or not src.any():
            continue
        rows.append({"y": y, "max_src_lf_plus1": float(np.nanmax(lf[src]) + 1), "T_Y": T[y],
                     "min_target_es": float(np.nanmin(es[tgt])), "target_es_nan": int(np.isnan(es[tgt]).sum()),
                     "excluded_late_rows_prev_year": int((ok & (ty == y - 1) & ~(lf + 1 <= T[y])).sum())})
    R_ = pd.DataFrame(rows)
    out = {"all_ok": bool((R_["max_src_lf_plus1"] <= R_["T_Y"]).all() & (R_["T_Y"] <= R_["min_target_es"]).all()),
           "target_es_nan_total": int(R_["target_es_nan"].sum()),
           "excluded_prev_year_rows_median": float(R_["excluded_late_rows_prev_year"].median()),
           "rows": R_.tail(4).to_dict("records")}
    dump("timing", out)


def side_vals(H, col, ra, rb):
    v = H[col].to_numpy()
    return v[ra], v[rb]


def proxy(H, M, ra, rb, X) -> None:
    from src.eda.feature_interactions.screen import oos_model_forecast
    import pyarrow.parquet as pq
    cols = [c for c in pq.read_schema(C.MODEL_FRAME).names if c.startswith("in_") or c in ("match_id", "season")]
    assert "a_won" not in cols
    f = pd.read_parquet(C.MODEL_FRAME, columns=cols, filters=[("season", "<=", 2024)])
    f = f[f["season"].between(2013, 2024)].reset_index(drop=True)
    lv = pd.read_parquet(SOURCES["stage0_matches"], columns=["match_id", "level"])
    lv["match_id"] = lv["match_id"].astype(str)
    f["level"] = f[["match_id"]].astype(str).merge(lv, on="match_id", how="left")["level"].astype(str).to_numpy()
    assert (f["match_id"].astype(str).to_numpy() == M["match_id"].to_numpy()).all()
    ins = [c for c in f.columns if c.startswith("in_")]
    s = M["season"].to_numpy()
    yrs = (s >= 2014) & (s <= 2024)
    x = X["x"].to_numpy(float)
    eta = C.lg(M["match_id"].map(oos_model_forecast()).to_numpy(float))
    r = {}
    for c in ins:
        v = pd.to_numeric(f[c], errors="coerce").to_numpy(float)
        ok = yrs & np.isfinite(v) & np.isfinite(x)
        if np.std(v[ok]) > 0:
            r[c] = float(np.corrcoef(x[ok], v[ok])[0, 1])
    top = sorted(r, key=lambda k: -abs(r[k]))[:8]
    out = {"n_inputs": len(ins), "top_abs_r": {k: round(r[k], 3) for k in top}}
    Z58 = np.nan_to_num(np.column_stack([pd.to_numeric(f[c], errors="coerce").to_numpy(float) for c in ins]))
    for tag, m in (("2014_2021", (s >= 2014) & (s <= 2021)), ("2022_2024", (s >= 2022) & (s <= 2024))):
        for nm, v in (("x", x), ("z43", X["z43"].to_numpy(float))):
            mm = m & np.isfinite(v)
            A = np.column_stack([np.ones(mm.sum()), Z58[mm]])
            b, *_ = np.linalg.lstsq(A, v[mm], rcond=None)
            out[f"R2_{nm}_on_58_{tag}"] = round(float(1 - np.var(v[mm] - A @ b) / np.var(v[mm])), 3)
    adj = eta - f["in_odds_logit"].to_numpy(float)
    ok = yrs & np.isfinite(eta)
    out["r_x_eta_model"] = round(float(np.corrcoef(x[ok], eta[ok])[0, 1]), 3)
    out["r_x_odds_logit"] = round(float(np.corrcoef(x[ok], f["in_odds_logit"].to_numpy(float)[ok])[0, 1]), 3)
    out["r_x_model_adjustment"] = round(float(np.corrcoef(x[ok], adj[ok])[0, 1]), 3)
    na, nb = X["n_since_a"].to_numpy(float), X["n_since_b"].to_numpy(float)
    near = (na <= 2) | (nb <= 2)
    by = []
    for y in range(2014, 2025):
        m = s == y
        by.append({"y": y, "sd_x": round(float(np.std(x[m])), 3), "share_abs_gt2": round(float((np.abs(x[m]) > 2).mean()), 4),
                   "share_near_return": round(float(near[m].mean()), 4),
                   "x2_mass_near_return": round(float((x[m] ** 2 * near[m]).sum() / (x[m] ** 2).sum()), 3),
                   "z43_sd": round(float(np.std(X["z43"].to_numpy(float)[m])), 3)})
    out["by_season"] = by
    # per player: rust at model rows by band, entry, level, tour; concentration
    rust = np.r_[X["rust_a"].to_numpy(float), X["rust_b"].to_numpy(float)]
    pid = np.r_[M["player_a_id"].astype(str).to_numpy(), M["player_b_id"].astype(str).to_numpy()]
    band = np.r_[side_vals(H, "band", ra, rb)]
    ent = pd.Series(np.r_[side_vals(H, "entry", ra, rb)]).astype(str).str.upper().to_numpy()
    lev = np.r_[f["level"].to_numpy(), f["level"].to_numpy()]
    yy = np.r_[s, s]
    ok = (yy >= 2014) & (yy <= 2024) & np.isfinite(rust)
    def summ(keys):
        d = pd.DataFrame({"k": keys[ok], "rust": rust[ok]})
        return {str(k): {"n": int(len(g)), "mean": round(float(g["rust"].mean()), 3),
                         "share_gt1": round(float((g["rust"] > 1).mean()), 4)} for k, g in d.groupby("k")}
    out["rust_by_band"] = summ(band)
    out["rust_by_entry"] = summ(np.where(np.isin(ent, ["PR", "SR"]), "PR/SR", np.where(ent == "NAN", "none", "other")))
    out["rust_by_tour"] = summ(np.r_[M["tour"].to_numpy(), M["tour"].to_numpy()])
    out["rust_by_level"] = summ(lev)
    out["abs_x_by_level"] = {str(k): round(float(np.mean(np.abs(x[yrs & (f["level"].to_numpy() == k)]))), 3)
                             for k in np.unique(f["level"].to_numpy())}
    tot = pd.Series(rust[ok], index=pid[ok]).groupby(level=0).sum().sort_values(ascending=False)
    out["players_with_rust"] = int((tot > 0).sum())
    out["share_rust_top10_players"] = round(float(tot.iloc[:10].sum() / tot.sum()), 3)
    out["share_rust_top50_players"] = round(float(tot.iloc[:50].sum() / tot.sum()), 3)
    dump("proxy", out)


def covid(H, M, ra, rb, X) -> None:
    t = H["t"].to_numpy(float)
    ret = H["is_ret"].to_numpy(bool)
    d = pd.to_datetime(t, unit="D")
    m20 = ret & (d >= "2020-03-01") & (d < "2021-01-01")
    out = {"history_returns_by_year": pd.Series(d[ret].year).value_counts().sort_index().to_dict(),
           "history_returns_mar_dec_2020": int(m20.sum())}
    # E by week around the restart (weeks 30-38) against the rest of the year, by tyear, for the ATP's and WTA's
    E, wk, ty = H["E"].to_numpy(float), H["week"].to_numpy(), H["tyear"].to_numpy()
    tour = H["tour"].astype(str).to_numpy()
    tab = []
    for y in range(2017, 2025):
        for tr in ("atp", "wta"):
            m = (ty == y) & (tour == tr) & np.isfinite(E)
            a = (wk >= 31) & (wk <= 37)
            tab.append({"y": y, "tour": tr, "E_w31_37": round(float(np.mean(E[m & a])), 1),
                        "E_other": round(float(np.mean(E[m & ~a])), 1)})
    out["E_restart_weeks"] = tab
    # model rows whose either player's latest return fell in Mar-Dec 2020
    r_all = H["r"].to_numpy()
    rt = lambda rows: np.where(rows >= 0, t[np.maximum(r_all[np.maximum(rows, 0)], 0)], np.nan)
    has = lambda rows: (rows >= 0) & (r_all[np.maximum(rows, 0)] >= 0)
    ta, tb = rt(ra), rt(rb)
    ca = has(ra) & (ta >= (pd.Timestamp("2020-03-01") - DAY0).days) & (ta < (pd.Timestamp("2021-01-01") - DAY0).days)
    cb = has(rb) & (tb >= (pd.Timestamp("2020-03-01") - DAY0).days) & (tb < (pd.Timestamp("2021-01-01") - DAY0).days)
    cov = ca | cb
    s, x = M["season"].to_numpy(), X["x"].to_numpy(float)
    na, nb = X["n_since_a"].to_numpy(float), X["n_since_b"].to_numpy(float)
    for y in (2020, 2021, 2022):
        m = s == y
        out[f"{y}_share_rows_covid_return"] = round(float(cov[m].mean()), 3)
        out[f"{y}_x2_mass_covid_return"] = round(float((x[m] ** 2 * cov[m]).sum() / (x[m] ** 2).sum()), 3)
        out[f"{y}_both_within2_of_return"] = round(float(((na <= 2) & (nb <= 2))[m].mean()), 3)
    m = (s >= 2014) & (s <= 2024)
    out["x2_mass_2020_2021_of_2014_2024"] = round(float((x[m & ((s == 2020) | (s == 2021))] ** 2).sum() / (x[m] ** 2).sum()), 3)
    out["rows_2020_2021_of_2014_2024"] = round(float(((s == 2020) | (s == 2021))[m].mean()), 3)
    dump("covid", out)


def artefact(H, M, ra, rb, X) -> None:
    yr = H["tyear"].to_numpy()
    win = (yr >= 2013) & (yr <= 2024)
    gap, E = H["gap"].to_numpy(float), H["E"].to_numpy(float)
    ret = H["is_ret"].to_numpy(bool) & win
    played = H["played"].to_numpy(bool)
    st, won = H["status"].astype(str).to_numpy(), H["won"].to_numpy(bool)
    start = H["start"].to_numpy()
    i = np.flatnonzero(ret)
    prev = i - 1
    ok = prev >= start[i]
    pst, pwon = st[np.maximum(prev, 0)], won[np.maximum(prev, 0)]
    out = {"returns_2013_2024": int(len(i)), "returns_that_are_walkover_rows": int((~played[i]).sum()),
           "blocked_by_E_gap42_but_le_E": int(((gap >= 42) & np.isfinite(E) & (gap <= E) & win).sum()),
           "gap42_E_nan": int(((gap >= 42) & ~np.isfinite(E) & win).sum()),
           "inj_retired_before": int((ok & (pst == "retired") & ~pwon).sum()),
           "inj_walkover_given_before": int((ok & (pst == "walkover") & ~pwon).sum()),
           "row_before_is_walkover_received": int((ok & (pst == "walkover") & pwon).sum()),
           "return_gap_quantiles": {q: float(np.quantile(gap[i], q)) for q in (0.25, 0.5, 0.75, 0.9, 0.99)},
           "share_return_gap_gt365": round(float((gap[i] > 365).mean()), 3)}
    E_m = E[win & np.isfinite(E)]
    out["E_quantiles"] = {q: round(float(np.quantile(E_m, q)), 1) for q in (0.01, 0.5, 0.99)}
    out["E_mean_by_band"] = {b: round(float(np.nanmean(E[win & (H["band"].to_numpy() == b)])), 1)
                             for b in ("20", "50", "100", "250", "other")}
    wk = H["week"].to_numpy()
    out["E_mean_week0_1"] = round(float(np.nanmean(E[win & (wk <= 1)])), 1)
    rank = pd.to_numeric(H["rank"], errors="coerce").to_numpy(float)
    pp = H["prevp"].to_numpy()
    rk0, rk1 = rank[np.maximum(pp[i], 0)], rank[i]
    okr = np.isfinite(rk0) & np.isfinite(rk1) & (pp[i] >= 0)
    out["returns_rank_improved_10pct_during_gap"] = round(float((rk1[okr] < 0.9 * rk0[okr]).mean()), 3)
    out["returns_rank_missing_at_return"] = round(float(~np.isfinite(rk1).mean()), 3) if False else round(
        float((~np.isfinite(rk1)).mean()), 3)
    # latest return of a model row being a walkover row; return match itself a model match
    r_all = H["r"].to_numpy()
    for side, rows in (("a", ra), ("b", rb)):
        rr = r_all[rows]
        out[f"model_{side}_latest_return_is_walkover"] = int(((rr >= 0) & ~played[np.maximum(rr, 0)]).sum())
        out[f"model_{side}_n0"] = int((X[f"n_since_{side}"].to_numpy(float) == 0).sum())
    nanr = ~np.isfinite(X["d43"].to_numpy(float))
    agea, ageb = side_vals(H, "age", ra, rb)
    out["d43_nan_rows_2013_2024"] = int(nanr.sum())
    out["d43_nan_rows_with_age_nan"] = int((nanr & (~np.isfinite(pd.to_numeric(pd.Series(agea)).to_numpy(float)) |
                                                    ~np.isfinite(pd.to_numeric(pd.Series(ageb)).to_numpy(float)))).sum())
    dump("artefact", out)


def coverage_test_years() -> None:
    """Feature-only: why the registered I-043 column is NaN on some 2025-2026 rows (no result column is read)."""
    f = pd.read_parquet(C.MODEL_FRAME, columns=["match_id", "season", "tour"])
    f["match_id"] = f["match_id"].astype(str)
    b = pd.read_parquet(C.OUT / "features" / "binj.parquet")
    f = f.merge(b, on="match_id", how="left")
    m = pd.read_parquet(SOURCES["stage0_matches"], columns=["match_id", "player_a_id", "player_b_id"])
    m["match_id"] = m["match_id"].astype(str)
    f = f.merge(m, on="match_id", how="left")
    p = pd.read_parquet(SOURCES["stage0_players"], columns=["match_id", "player_id", "age"])
    p["match_id"] = p["match_id"].astype(str)
    age = p.set_index(p["match_id"] + "#" + p["player_id"].astype(str))["age"]
    out = {}
    for y in (2024, 2025, 2026):
        g = f[f["season"] == y]
        aa = age.reindex(g["match_id"] + "#" + g["player_a_id"].astype(str)).to_numpy(float)
        ab = age.reindex(g["match_id"] + "#" + g["player_b_id"].astype(str)).to_numpy(float)
        agenan = ~np.isfinite(aa) | ~np.isfinite(ab)
        nan43 = ~np.isfinite(g["bdinj_I043"].to_numpy(float))
        out[str(y)] = {"rows": int(len(g)), "I043_nan": int(nan43.sum()), "age_nan_either": int(agenan.sum()),
                       "I043_nan_and_age_nan": int((nan43 & agenan).sum()),
                       "I043_nan_by_tour": g.loc[nan43, "tour"].value_counts().to_dict()}
    dump("coverage", out)


def main() -> int:
    warnings.simplefilter("ignore")
    part = sys.argv[1] if len(sys.argv) > 1 else "all"
    if part in ("coverage", "all"):
        coverage_test_years()
    if part == "coverage":
        return 0
    L, H, M, ra, rb, X = setup()
    for fn in (orient, proxy, covid, artefact):
        if part in (fn.__name__, "all"):
            fn(H, M, ra, rb, X) if fn is not orient else fn(H, M, ra, rb, X)
    if part in ("timing", "all"):
        timing(H)
    return 0


if __name__ == "__main__":
    sys.exit(main())


def classes(H, M, ra, rb, X) -> None:
    """Which kind of break carries the column: each model player-row's latest return classed as covid (previous played
    match before 15 Mar 2020, return Jun-Dec 2020), off-season (previous played match Sep-Dec, return Dec-Feb, gap
    <= 120 days), long (gap > 180), other; shares of the rust mass and of x^2 (2014-2024)."""
    t, gap, r_all = H["t"].to_numpy(float), H["gap"].to_numpy(float), H["r"].to_numpy()
    pp = H["prevp"].to_numpy()
    def cls(rows):
        rr = r_all[rows]
        has = rr >= 0
        r0 = np.maximum(rr, 0)
        dr = pd.to_datetime(t[r0], unit="D")
        dp = pd.to_datetime(t[np.maximum(pp[r0], 0)], unit="D")
        g = gap[r0]
        c = np.full(len(rows), "none", dtype=object)
        cov = has & (dp < "2020-03-15") & (dr >= "2020-06-01") & (dr < "2021-01-01")
        off = has & ~cov & np.isin(dp.month, [9, 10, 11, 12]) & np.isin(dr.month, [12, 1, 2]) & (g <= 120)
        lng = has & ~cov & ~off & (g > 180)
        c[has] = "other"; c[lng] = "long"; c[off] = "offseason"; c[cov] = "covid"
        return c
    ca, cb = cls(ra), cls(rb)
    s = M["season"].to_numpy()
    m = (s >= 2014) & (s <= 2024)
    rust = np.r_[X["rust_a"].to_numpy(float)[m], X["rust_b"].to_numpy(float)[m]]
    cc = np.r_[ca[m], cb[m]]
    ok = np.isfinite(rust)
    tot = rust[ok].sum()
    out = {"rust_mass_share": {k: round(float(rust[ok & (cc == k)].sum() / tot), 3) for k in ("covid", "offseason",
                                                                                            "long", "other")},
           "player_rows_share": {k: round(float((cc == k).mean()), 3) for k in ("none", "covid", "offseason", "long",
                                                                                "other")}}
    # x^2 attributed to the side with the larger |rust| contribution
    x = X["x"].to_numpy(float)[m]
    big = np.where(np.abs(X["rust_a"].to_numpy(float)[m]) >= np.abs(X["rust_b"].to_numpy(float)[m]), ca[m], cb[m])
    out["x2_share_by_dominant_side_class"] = {k: round(float((x[big == k] ** 2).sum() / (x ** 2).sum()), 3)
                                              for k in ("none", "covid", "offseason", "long", "other")}
    out["x2_share_offseason_by_season"] = {int(y): round(float((x[(big == "offseason") & (s[m] == y)] ** 2).sum() /
                                                               (x[s[m] == y] ** 2).sum()), 3) for y in range(2014, 2025)}
    dump("classes", out)
