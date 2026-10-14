"""The evidence behind the representation, on the design seasons 2013-2021 only (tuning 2013-2018, checking 2019-2021).

    A. bias     how far each surface rating sits from the overall rating, by the player's surface-match count
    B. weights  Elo-only forecasts (no odds) of the surface variants: overall alone, Stage 1's fixed blend, a blend whose
                weight grows with each player's surface evidence (w_i = w_max n_i / (n_i + k)), the anchored surface
                rating, the surface offset. Constants tuned on 2013-2018 evaluation matches; scored on 2019-2021
    C. switches how often "first matches on this surface" (fewer than 3 this season) cancels as A - B because both
                players are new; by surface and by week of the surface season; layoffs since the last surface match
    D. odds     what the pieces add once the closing odds are in: forward-chained logistic fits (each season 2016-2021
                fitted on 2013 to the season before), main tour, no intercept (the forecast is antisymmetric)
    E. priced   do players new to a surface, or back on it after a long layoff, win less than overall Elo, the offset
                Elo and the recalibrated market expect? (main tour with odds, player rows, one population)
    F. no odds  what the pieces add to Elo without the odds, forward-chained as in D
    G. offset   added after the audit: each switch quantity and career counts beside the offset Elo, without and with
                the odds; the offset's gain over the blend by period; a surface-blind offset as a control; the offset's
                average for experienced players by surface

Writes data/studies/surface_elo_pieces/evidence.json and evidence_*.csv.
Run: ./python.sh src/eda/surface_elo_pieces/evidence.py
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_elo_pieces import common as C  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

W_STAGE1 = {"atp": 0.30, "wta": 0.25}
EVIDENCE_GRID = {"w_max": [round(x, 2) for x in np.arange(0.1, 1.0001, 0.05)],
                 "k": [0.0, 2.0, 5.0, 10.0, 20.0, 40.0, 80.0, 160.0]}
COUNT_BINS = [-1, 0, 2, 5, 10, 20, 40, 80, 160, 100_000]


def load() -> pd.DataFrame:
    p = pd.read_parquet(C.PIECES)
    m = pd.read_parquet(C.STAGE0, columns=["match_id", "level", "qualifying", "evaluation", "status", "surface",
                                           "tournament_date", "a_won", "tournament_id"])
    p = p.merge(m, on="match_id", how="left", validate="one_to_one")
    f = pd.read_parquet(C.FRAME, columns=["match_id", "split", "tabpfn_split", "odds_logit", "elo_logit",
                                          "surface_first", "group"])
    p = p.merge(f, on="match_id", how="left", validate="one_to_one")
    p["main"] = p["split"].isin(["train", "test"])                 # the best model's population (with or without odds)
    p["eval_ok"] = p["evaluation"] & p["status"].isin(["completed", "retired"]) & p["surface"].notna()
    return p


def elo_logit(ra, rb):
    return C.L10 * (np.asarray(ra, float) - np.asarray(rb, float))


def blend_logit(p: pd.DataFrame, w_a, w_b, sa="S_a", sb="S_b") -> np.ndarray:
    """log-odds from R + w (S - R) for each player (overall alone where the surface is unknown)."""
    s_a = np.where(np.isfinite(p[sa]), p[sa], p["R_a"])
    s_b = np.where(np.isfinite(p[sb]), p[sb], p["R_b"])
    return elo_logit(p["R_a"] + w_a * (s_a - p["R_a"]), p["R_b"] + w_b * (s_b - p["R_b"]))


def evidence_weights(p: pd.DataFrame, w_max: float, k: float) -> tuple[np.ndarray, np.ndarray]:
    na, nb = p["NS_a"].fillna(0).to_numpy(), p["NS_b"].fillna(0).to_numpy()
    return w_max * na / (na + k) if k > 0 else np.full(len(p), w_max), w_max * nb / (nb + k) if k > 0 else np.full(len(p), w_max)


# ------------------------------------------------------------------------------------------------
# A. bias

def bias_table(p: pd.DataFrame) -> pd.DataFrame:
    d = p[p["main"] & p["year"].between(*C.DESIGN_YEARS)]
    rows = pd.DataFrame({
        "tour": np.r_[d["tour"], d["tour"]], "surface": np.r_[d["surface"], d["surface"]],
        "n_surface": np.r_[d["NS_a"], d["NS_b"]],
        "stage1_minus_overall": np.r_[d["S_a"] - d["R_a"], d["S_b"] - d["R_b"]],
        "anchored_minus_overall": np.r_[d["XA_a"] - d["R_a"], d["XA_b"] - d["R_b"]],
        "offset": np.r_[d["D_a"], d["D_b"]]})
    rows["count_bin"] = pd.cut(rows["n_surface"], COUNT_BINS).astype(str)
    g = rows.groupby(["tour", "count_bin"], sort=False)
    out = g.agg(player_rows=("n_surface", "size"),
                **{f"{c}_{s}": (c, s) for c in ("stage1_minus_overall", "anchored_minus_overall", "offset")
                   for s in ("mean", "std")}).reset_index()
    out["order"] = out["count_bin"].map({str(pd.Interval(a, b, closed="right")): i
                                         for i, (a, b) in enumerate(zip(COUNT_BINS[:-1], COUNT_BINS[1:]))})
    share = rows.assign(low=rows["n_surface"] < 20).groupby(["tour", "surface"])["low"].mean().rename("share_below_20")
    return out.sort_values(["tour", "order"]).drop(columns="order"), share.reset_index()


# ------------------------------------------------------------------------------------------------
# B. Elo-only forecasts

def tune_evidence(p: pd.DataFrame, rows: np.ndarray, sa: str, sb: str) -> tuple[dict, pd.DataFrame]:
    y = p.loc[rows, "a_won"].to_numpy(bool)
    q = p[rows]
    grid = []
    for w_max, k in itertools.product(EVIDENCE_GRID["w_max"], EVIDENCE_GRID["k"]):
        wa, wb = evidence_weights(q, w_max, k)
        grid.append({"w_max": w_max, "k": k, "log_loss": C.mean_ll(expit(blend_logit(q, wa, wb, sa, sb)), y)})
    g = pd.DataFrame(grid)
    best = g.loc[g["log_loss"].idxmin()]
    return {"w_max": float(best["w_max"]), "k": float(best["k"])}, g


def elo_forecasts(p: pd.DataFrame) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """Every Elo-only log-odds for every match, with each variant's constants tuned per tour on 2013-2018."""
    out = pd.DataFrame(index=p.index)
    consts, grids = {}, []
    for tour in C.TOURS:
        t = (p["tour"] == tour).to_numpy()
        tune = t & p["eval_ok"].to_numpy() & p["year"].between(*C.TUNE_YEARS).to_numpy()
        q = p[t]
        out.loc[t, "overall"] = elo_logit(q["R_a"], q["R_b"])
        w = W_STAGE1[tour]
        out.loc[t, "stage1_blend"] = blend_logit(q, w, w)
        ev, g1 = tune_evidence(p, tune, "S_a", "S_b")
        wa, wb = evidence_weights(q, **ev)
        out.loc[t, "stage1_evidence"] = blend_logit(q, wa, wb)
        # anchored surface rating: a fixed weight tuned on the same matches, and the evidence-weighted form
        y = p.loc[tune, "a_won"].to_numpy(bool)
        fixed = [(w_, C.mean_ll(expit(blend_logit(p[tune], w_, w_, "XA_a", "XA_b")), y))
                 for w_ in EVIDENCE_GRID["w_max"] + [0.0]]
        w_anch = min(fixed, key=lambda x: x[1])[0]
        out.loc[t, "anchored_blend"] = blend_logit(q, w_anch, w_anch, "XA_a", "XA_b")
        ev_a, g2 = tune_evidence(p, tune, "XA_a", "XA_b")
        wa, wb = evidence_weights(q, **ev_a)
        out.loc[t, "anchored_evidence"] = blend_logit(q, wa, wb, "XA_a", "XA_b")
        d_a, d_b = q["D_a"].fillna(0).to_numpy(), q["D_b"].fillna(0).to_numpy()
        out.loc[t, "offset"] = elo_logit(q["R_a"] + d_a, q["R_b"] + d_b)
        consts[tour] = {"stage1_w": w, "stage1_evidence": ev, "anchored_w": w_anch, "anchored_evidence": ev_a}
        grids += [g1.assign(tour=tour, variant="stage1_evidence"), g2.assign(tour=tour, variant="anchored_evidence")]
    return out, consts, pd.concat(grids)


def weight_by_evidence(p: pd.DataFrame) -> pd.DataFrame:
    """The best single surface weight (and its slope) where the smaller of the two surface counts falls in a bin, main
    tour 2013-2021, against the weight Stage 1 tuned: does the right weight grow with evidence?"""
    d = p[p["main"] & p["year"].between(*C.DESIGN_YEARS) & p["surface"].notna()].copy()
    d["bin"] = pd.cut(np.minimum(d["NS_a"], d["NS_b"]), [-1, 2, 5, 10, 20, 40, 80, 1e9]).astype(str)
    rows = []
    for (tour, b), g in d.groupby(["tour", "bin"], sort=False):
        y = g["a_won"].to_numpy(bool)
        fits = []
        for w in np.round(np.arange(0, 1.0001, 0.05), 2):
            x = blend_logit(g, w, w)
            s = scale_fit(x, y)
            fits.append((w, C.mean_ll(expit(s * x), y)))
        best = min(fits, key=lambda t: t[1])
        at_stage1 = [v for w, v in fits if abs(w - W_STAGE1[tour]) < 1e-9][0]
        rows.append({"tour": tour, "min_surface_count": b, "matches": len(g), "best_w": float(best[0]),
                     "gain_best_vs_stage1_w": 1000 * (at_stage1 - best[1])})
    return pd.DataFrame(rows)


def scale_fit(x: np.ndarray, y: np.ndarray) -> float:
    """One slope on the log-odds, fitted (no intercept): every variant is recalibrated the same way on 2013-2018."""
    r = minimize(lambda b: np.mean(T.ll(expit(b[0] * x), y)), x0=[1.0], method="Nelder-Mead")
    return float(r.x[0])


def score_elo(p: pd.DataFrame, fc: pd.DataFrame) -> pd.DataFrame:
    """Log loss on 2019-2021 (lower is better) and the gain over Stage 1's blend (milli-log-loss, positive = the
    variant is better), each variant recalibrated by one slope fitted on 2013-2018; by tour and population/subset."""
    rows = []
    for tour in C.TOURS:
        t = (p["tour"] == tour).to_numpy() & p["eval_ok"].to_numpy()
        tune = t & p["year"].between(*C.TUNE_YEARS).to_numpy()
        chk = t & p["year"].between(*C.CHECK_YEARS).to_numpy()
        y_t = p.loc[tune, "a_won"].to_numpy(bool)
        cal = {v: scale_fit(fc.loc[tune, v].to_numpy(), y_t) for v in fc.columns}
        q = p[chk]
        y = q["a_won"].to_numpy(bool)
        early = (q["season_n_a"] < 3) | (q["season_n_b"] < 3)
        subsets = {"all evaluation": np.ones(len(q), bool), "main tour": q["main"].to_numpy(),
                   "grass": (q["surface"] == "Grass").to_numpy(),
                   "low evidence (either < 20 surface matches)": ((q["NS_a"] < 20) | (q["NS_b"] < 20)).to_numpy(),
                   "early surface season (either < 3 this season)": early.to_numpy()}
        base = T.ll(expit(cal["stage1_blend"] * fc.loc[chk, "stage1_blend"].to_numpy()), y)
        for name, s in subsets.items():
            for v in fc.columns:
                lv = T.ll(expit(cal[v] * fc.loc[chk, v].to_numpy()), y)
                c = T.compare(base[s], lv[s], q.loc[s, "tournament_date"].to_numpy())
                rows.append({"tour": tour, "subset": name, "variant": v, "matches": int(s.sum()),
                             "log_loss": float(lv[s].mean()), "slope_2013_2018": cal[v],
                             "gain_vs_stage1_blend": c["gain"], "lo": c["lo"], "hi": c["hi"]})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# C. surface switches

def season_week(p: pd.DataFrame) -> np.ndarray:
    """Weeks since the first main-tour event of that tour, surface and calendar season (0 = the opening week)."""
    d = pd.to_datetime(p["tournament_date"])
    key = p["tour"] + "|" + p["surface"].fillna("?") + "|" + p["year"].astype(str)
    first = d.where(p["main"]).groupby(key).transform("min")
    return ((d - first).dt.days // 7).to_numpy()


def switch_tables(p: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    d = p[p["main"] & p["year"].between(*C.DESIGN_YEARS) & p["surface"].notna()].copy()
    new_a, new_b = d["season_n_a"] < 3, d["season_n_b"] < 3
    d["config"] = np.select([new_a & new_b, new_a ^ new_b], ["both new", "one new"], "neither new")
    flag = new_a.astype(int) - new_b.astype(int)
    stored = d["surface_first"].to_numpy()
    agree = float(np.mean((flag.to_numpy() == stored)[np.isfinite(stored)]))   # season_n reproduces surface_first
    d["week"] = season_week(d)
    by_surface = d.groupby(["tour", "surface", "config"]).size().unstack(fill_value=0)
    by_surface["share_both_new"] = by_surface.get("both new", 0) / by_surface.sum(axis=1)
    by_surface["share_flag_zero"] = (by_surface.get("both new", 0) + by_surface.get("neither new", 0)) / \
        by_surface[["both new", "one new", "neither new"]].sum(axis=1)
    wk = d[d["week"] <= 5].groupby(["tour", "surface", "week", "config"]).size().unstack(fill_value=0)
    wk["share_both_new"] = wk.get("both new", 0) / wk[["both new", "one new", "neither new"]].sum(axis=1)
    lay = pd.DataFrame({"config": np.r_[d["config"], d["config"]], "surface": np.r_[d["surface"], d["surface"]],
                        "days_since": np.r_[d["days_since_a"], d["days_since_b"]]})
    lay_q = lay.groupby(["surface", "config"])["days_since"].quantile([0.1, 0.5, 0.9]).unstack()
    lay_q.columns = [f"days_since_p{int(100 * c)}" for c in lay_q.columns]
    return by_surface.reset_index(), wk.reset_index(), {"stored_flag_reproduced_share": agree,
                                                        "layoff_quantiles": lay_q.reset_index().to_dict("records")}


# ------------------------------------------------------------------------------------------------
# D. with the odds: forward-chained logistic fits (main tour, seasons 2016-2021)

def design_matrix(q: pd.DataFrame, spec: str) -> np.ndarray:
    o = q["odds_logit"].to_numpy()
    new_a, new_b = (q["season_n_a"] < 3).to_numpy(), (q["season_n_b"] < 3).to_numpy()
    both_new = (new_a & new_b).astype(float)
    lsa, lsb = np.log1p(q["season_n_a"].to_numpy()), np.log1p(q["season_n_b"].to_numpy())
    cap = 1095.0
    dsa = np.log1p(np.minimum(q["days_since_a"].fillna(cap).to_numpy(), cap))
    dsb = np.log1p(np.minimum(q["days_since_b"].fillna(cap).to_numpy(), cap))
    nsa, nsb = np.log1p(q["NS_a"].fillna(0).to_numpy()), np.log1p(q["NS_b"].fillna(0).to_numpy())
    d_over = elo_logit(q["R_a"], q["R_b"])
    s_a = np.where(np.isfinite(q["S_a"]), q["S_a"], q["R_a"])
    s_b = np.where(np.isfinite(q["S_b"]), q["S_b"], q["R_b"])
    d_surf = elo_logit(s_a, s_b)
    d_off = C.L10 * (q["D_a"].fillna(0).to_numpy() - q["D_b"].fillna(0).to_numpy())
    prev = (q["prev_res_a"].fillna(0).to_numpy() / (q["prev_n_a"].fillna(0).to_numpy() + 5)
            - q["prev_res_b"].fillna(0).to_numpy() / (q["prev_n_b"].fillna(0).to_numpy() + 5))
    cols = {"odds": [o],
            "odds+elo_blend": [o, q["elo_logit"].to_numpy()],
            "odds+surface_first": [o, q["surface_first"].fillna(0).to_numpy()],
            "odds+pieces_literal": [o, d_over, d_surf, nsa - nsb, d_surf * np.minimum(nsa, nsb)],
            "odds+pieces_offset": [o, d_over, d_off],
            "odds x both_new": [o, o * both_new],
            "odds x season counts": [o, o * np.minimum(lsa, lsb), o * np.maximum(dsa, dsb)],
            "odds+switch diffs": [o, lsa - lsb, dsa - dsb, prev],
            "odds+switch all": [o, lsa - lsb, dsa - dsb, prev, o * both_new, o * np.minimum(lsa, lsb),
                                o * np.maximum(dsa, dsb)]}
    X = np.column_stack(cols[spec])
    return np.where(np.isfinite(X), X, 0.0)


SPECS = ["odds", "odds+elo_blend", "odds+surface_first", "odds+pieces_literal", "odds+pieces_offset",
         "odds x both_new", "odds x season counts", "odds+switch diffs", "odds+switch all"]


def with_odds(p: pd.DataFrame) -> pd.DataFrame:
    d = p[(p["tabpfn_split"] != "") & p["tabpfn_split"].notna() & p["year"].between(*C.DESIGN_YEARS)].copy()
    rows = []
    preds = {s: np.full(len(d), np.nan) for s in SPECS}
    years = d["year"].to_numpy()
    for tour in C.TOURS:
        for season in range(2016, 2022):
            tr = (d["tour"] == tour).to_numpy() & (years < season)
            te = (d["tour"] == tour).to_numpy() & (years == season)
            if not te.any():
                continue
            for s in SPECS:
                beta, _ = T.fit_logistic(design_matrix(d[tr], s), d.loc[tr, "a_won"].to_numpy(float))
                preds[s][te] = expit(design_matrix(d[te], s) @ beta)
    y = d["a_won"].to_numpy(bool)
    early = ((d["season_n_a"] < 3) | (d["season_n_b"] < 3)).to_numpy()
    for tour in C.TOURS + ("both",):
        t = np.ones(len(d), bool) if tour == "both" else (d["tour"] == tour).to_numpy()
        for sub, s_ in (("all", t), ("early surface season", t & early), ("grass", t & (d["surface"] == "Grass").to_numpy())):
            ok = s_ & np.isfinite(preds["odds"])
            base = T.ll(preds["odds"][ok], y[ok])
            for s in SPECS[1:]:
                c = T.compare(base, T.ll(preds[s][ok], y[ok]), d.loc[ok, "tournament_date"].to_numpy())
                rows.append({"tour": tour, "subset": sub, "spec": s, "matches": c["n"], "gain_vs_recalibrated_odds": c["gain"],
                             "lo": c["lo"], "hi": c["hi"]})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# E. is the inexperience and layoff penalty priced?

def priced(p: pd.DataFrame) -> pd.DataFrame:
    """One population (main-tour design-year matches with odds; the audit's S5.7: the first version compared Elo on
    all rows with the raw market on the rows with odds). Expectations: overall Elo, the surface-offset Elo and the
    market recalibrated per tour by one slope fitted on the same design years (descriptive, in-sample). Standard errors
    are cluster-robust over four-week blocks, each match's two player rows in the same block."""
    d = p[p["main"] & p["year"].between(*C.DESIGN_YEARS) & p["surface"].notna() & np.isfinite(p["odds_logit"])].copy()
    slope = {t: scale_fit(d.loc[d["tour"] == t, "odds_logit"].to_numpy(), d.loc[d["tour"] == t, "a_won"].to_numpy(bool))
             for t in C.TOURS}
    p_over = expit(elo_logit(d["R_a"], d["R_b"]))
    p_off = expit(elo_logit(d["R_a"] + d["D_a"].fillna(0), d["R_b"] + d["D_b"].fillna(0)))
    p_mkt = expit(d["odds_logit"].to_numpy() * d["tour"].map(slope).to_numpy())
    blk = T.blocks(d["tournament_date"].to_numpy(), 28)
    parts = []
    for side in ("a", "b"):
        own = side == "a"
        parts.append(pd.DataFrame({
            "tour": d["tour"].to_numpy(), "career_n": d[f"NS_{side}"].to_numpy(),
            "days": d[f"days_since_{side}"].to_numpy(), "block": blk,
            "won": np.where(own, d["a_won"].to_numpy(float), 1 - d["a_won"].to_numpy(float)),
            "p_elo": np.where(own, p_over, 1 - p_over), "p_off": np.where(own, p_off, 1 - p_off),
            "p_mkt": np.where(own, p_mkt, 1 - p_mkt)}))
    r = pd.concat(parts, ignore_index=True)
    r["career_bin"] = pd.cut(r["career_n"], [-1, 5, 10, 20, 40, 80, 1e9]).astype(str)
    r["layoff_bin"] = pd.cut(r["days"].fillna(1e6), [-1, 3, 10, 30, 90, 200, 400, 1e9]).astype(str)

    def mean_se(v, cl):
        v = np.asarray(v, float)
        labels, ix = np.unique(cl, return_inverse=True)
        infl = np.bincount(ix, weights=v - v.mean())
        g = len(labels)
        return float(v.mean()), float(np.sqrt(g / (g - 1) * infl @ infl) / len(v)) if g > 1 else np.nan

    out = []
    for by in ("career_bin", "layoff_bin"):
        for (tour, b), q in r.groupby(["tour", by], sort=False):
            row = {"tour": tour, "by": by, "bin": b, "player_rows": len(q)}
            for name, col in (("overall_elo", "p_elo"), ("offset_elo", "p_off"), ("market", "p_mkt")):
                m_, s_ = mean_se(q["won"] - q[col], q["block"])
                row[f"wins_minus_{name}"], row[f"se_{name}"] = m_, s_
            out.append(row)
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------
# G. beside the offset Elo (the audit's S1): career counts, last season's form, season counts and layoff, without and
#    with the odds; and the offset's gain by period (S5.6) and against a surface-blind offset (the audit's control)

def beside_offset(p: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = p[p["main"] & p["year"].between(*C.DESIGN_YEARS) & p["surface"].notna()].copy()
    cap = 1095.0
    x = {"off": elo_logit(d["R_a"] + d["D_a"].fillna(0), d["R_b"] + d["D_b"].fillna(0)),
         "gen": elo_logit(d["R_a"] + d["DG_a"].fillna(0), d["R_b"] + d["DG_b"].fillna(0)),
         "blend": d["elo_logit"].to_numpy(),
         "career": (np.log1p(d["NS_a"].fillna(0)) - np.log1p(d["NS_b"].fillna(0))).to_numpy(),
         "career20": (np.log1p(np.minimum(d["NS_a"].fillna(0), 20))
                      - np.log1p(np.minimum(d["NS_b"].fillna(0), 20))).to_numpy(),
         "season": (np.log1p(d["season_n_a"]) - np.log1p(d["season_n_b"])).to_numpy(),
         "layoff": (np.log1p(np.minimum(d["days_since_a"].fillna(cap), cap))
                    - np.log1p(np.minimum(d["days_since_b"].fillna(cap), cap))).to_numpy(),
         "form": (d["prev_res_a"].fillna(0) / (d["prev_n_a"].fillna(0) + 5)
                  - d["prev_res_b"].fillna(0) / (d["prev_n_b"].fillna(0) + 5)).to_numpy()}
    specs = {"offset": ["off"], "offset+career counts": ["off", "career"],
             "offset+career counts capped at 20": ["off", "career20"], "offset+last season's form": ["off", "form"],
             "offset+season counts": ["off", "season"], "offset+layoff": ["off", "layoff"],
             "offset+season counts+layoff": ["off", "season", "layoff"],
             "offset+all four": ["off", "season", "layoff", "career", "form"],
             "blend": ["blend"], "surface-blind offset": ["gen"]}
    odds = d["odds_logit"].to_numpy()
    y = d["a_won"].to_numpy(float)
    years = d["year"].to_numpy()
    rows = []
    for with_odds in (False, True):
        ok = np.isfinite(odds) if with_odds else np.ones(len(d), bool)
        pred = {k: np.full(len(d), np.nan) for k in specs}
        for tour in C.TOURS:
            for season in range(2016, 2022):
                tr = ok & (d["tour"] == tour).to_numpy() & (years < season)
                te = ok & (d["tour"] == tour).to_numpy() & (years == season)
                for k, cols in specs.items():
                    X = np.column_stack(([odds] if with_odds else []) + [x[c] for c in cols])
                    b, _ = T.fit_logistic(X[tr], y[tr])
                    pred[k][te] = expit(X[te] @ b)
        for tour in C.TOURS:
            t = (d["tour"] == tour).to_numpy() & np.isfinite(pred["offset"])
            for period, (lo_, hi_) in (("2016-2021", (2016, 2021)), ("2016-2018", (2016, 2018)),
                                       ("2019-2021", (2019, 2021))):
                tp = t & (years >= lo_) & (years <= hi_)
                for base, model in ([("offset", k) for k in specs if k.startswith("offset+")]
                                    + [("blend", "offset"), ("surface-blind offset", "offset")]):
                    if period != "2016-2021" and base != "blend":
                        continue
                    c = T.compare(T.ll(pred[base][tp], y[tp].astype(bool)), T.ll(pred[model][tp], y[tp].astype(bool)),
                                  d.loc[tp, "tournament_date"].to_numpy())
                    rows.append({"odds": with_odds, "tour": tour, "period": period, "base": base, "model": model,
                                 "matches": c["n"], "gain": c["gain"], "lo": c["lo"], "hi": c["hi"]})
    shift = pd.DataFrame({"tour": np.r_[d["tour"], d["tour"]], "surface": np.r_[d["surface"], d["surface"]],
                          "n": np.r_[d["NS_a"], d["NS_b"]], "offset": np.r_[d["D_a"], d["D_b"]]})
    shift = shift[shift["n"] > 160].groupby(["tour", "surface"])["offset"].agg(["mean", "std", "size"]).reset_index()
    return pd.DataFrame(rows), shift


# ------------------------------------------------------------------------------------------------
# F. without the odds: what the pieces add to Elo (forward-chained, main tour, 2016-2021)

def no_odds(p: pd.DataFrame) -> pd.DataFrame:
    d = p[p["main"] & p["year"].between(*C.DESIGN_YEARS) & p["surface"].notna()].copy()
    cap = 1095.0
    s_a = np.where(np.isfinite(d["S_a"]), d["S_a"], d["R_a"])
    s_b = np.where(np.isfinite(d["S_b"]), d["S_b"], d["R_b"])
    la = np.log1p(np.minimum(d["days_since_a"].fillna(cap), cap))
    lb = np.log1p(np.minimum(d["days_since_b"].fillna(cap), cap))
    f = {"blend": d["elo_logit"].to_numpy(), "overall": elo_logit(d["R_a"], d["R_b"]),
         "offset": elo_logit(d["R_a"] + d["D_a"].fillna(0), d["R_b"] + d["D_b"].fillna(0)),
         "surface1500": elo_logit(s_a, s_b),
         "ns_diff": (np.log1p(d["NS_a"].fillna(0)) - np.log1p(d["NS_b"].fillna(0))).to_numpy(),
         "season_diff": (np.log1p(d["season_n_a"]) - np.log1p(d["season_n_b"])).to_numpy(),
         "layoff_diff": (la - lb).to_numpy(),
         "prev_form": (d["prev_res_a"].fillna(0) / (d["prev_n_a"].fillna(0) + 5)
                       - d["prev_res_b"].fillna(0) / (d["prev_n_b"].fillna(0) + 5)).to_numpy(),
         "surface_first": d["surface_first"].fillna(0).to_numpy()}
    specs = {"offset": ["offset"], "overall+surface1500 (the pieces, linear)": ["overall", "surface1500"],
             "overall+surface1500+career counts": ["overall", "surface1500", "ns_diff"],
             "offset+career counts": ["offset", "ns_diff"], "blend+surface_first": ["blend", "surface_first"],
             "offset+season counts": ["offset", "season_diff"], "offset+layoff": ["offset", "layoff_diff"],
             "offset+last season's form": ["offset", "prev_form"],
             "offset+counts+season+layoff+form": ["offset", "ns_diff", "season_diff", "layoff_diff", "prev_form"],
             "blend+surface_first+counts+season+layoff+form": ["blend", "surface_first", "ns_diff", "season_diff",
                                                               "layoff_diff", "prev_form"]}
    y = d["a_won"].to_numpy(float)
    years = d["year"].to_numpy()
    pred = {k: np.full(len(d), np.nan) for k in ["blend"] + list(specs)}
    for tour in C.TOURS:
        for season in range(2016, 2022):
            tr = (d["tour"] == tour).to_numpy() & (years < season)
            te = (d["tour"] == tour).to_numpy() & (years == season)
            for k, cols in [("blend", ["blend"])] + list(specs.items()):
                X = np.column_stack([f[c] for c in cols])
                b, _ = T.fit_logistic(X[tr], y[tr])
                pred[k][te] = expit(X[te] @ b)
    rows = []
    for tour in C.TOURS:
        t = (d["tour"] == tour).to_numpy() & np.isfinite(pred["blend"])
        base = T.ll(pred["blend"][t], y[t].astype(bool))
        for k in specs:
            c = T.compare(base, T.ll(pred[k][t], y[t].astype(bool)), d.loc[t, "tournament_date"].to_numpy())
            rows.append({"tour": tour, "spec": k, "matches": c["n"], "gain_vs_blend": c["gain"], "lo": c["lo"],
                         "hi": c["hi"]})
    return pd.DataFrame(rows)


def main() -> int:
    p = load()
    C.log(f"pieces: {len(p):,} matches; main tour design rows {int((p['main'] & p['year'].between(*C.DESIGN_YEARS)).sum()):,}")
    bias, share = bias_table(p)
    bias.to_csv(C.OUT / "evidence_bias.csv", index=False)
    share.to_csv(C.OUT / "evidence_low_evidence_share.csv", index=False)
    fc, consts, grids = elo_forecasts(p)
    grids.to_csv(C.OUT / "evidence_weight_grid.csv", index=False)
    wb = weight_by_evidence(p)
    wb.to_csv(C.OUT / "evidence_weight_by_bin.csv", index=False)
    k_cost = (grids.groupby(["tour", "variant", "k"])["log_loss"].min()
              - grids.groupby(["tour", "variant"])["log_loss"].min()).mul(1000).rename("mll_worse_than_best").reset_index()
    k_cost.to_csv(C.OUT / "evidence_k_cost.csv", index=False)
    elo = score_elo(p, fc)
    elo.to_csv(C.OUT / "evidence_elo_only.csv", index=False)
    sw_surface, sw_week, sw_meta = switch_tables(p)
    sw_surface.to_csv(C.OUT / "evidence_switch_by_surface.csv", index=False)
    sw_week.to_csv(C.OUT / "evidence_switch_by_week.csv", index=False)
    od = with_odds(p)
    od.to_csv(C.OUT / "evidence_with_odds.csv", index=False)
    pr = priced(p)
    pr.to_csv(C.OUT / "evidence_priced.csv", index=False)
    no = no_odds(p)
    no.to_csv(C.OUT / "evidence_no_odds.csv", index=False)
    bo, shift = beside_offset(p)
    bo.to_csv(C.OUT / "evidence_beside_offset.csv", index=False)
    shift.to_csv(C.OUT / "evidence_offset_shift.csv", index=False)
    C.write_json(C.OUT / "evidence.json", {"constants": consts, "switch": sw_meta,
                                          "key": "log loss: lower is better; gains in milli-log-loss, positive = "
                                                 "the variant is better than the named base; a 95% interval spanning "
                                                 "0 is a tie"})
    with pd.option_context("display.width", 250, "display.max_rows", 400, "display.max_columns", 30):
        print(bias.round(1).to_string(index=False))
        print(share.round(3).to_string(index=False))
        print(consts)
        print(wb.round(3).to_string(index=False))
        print(k_cost.round(3).to_string(index=False))
        print(elo.round(3).to_string(index=False))
        print(sw_surface.round(3).to_string(index=False))
        print(sw_week.round(3).to_string(index=False))
        print(sw_meta)
        print(od.round(3).to_string(index=False))
        print(pr.round(4).to_string(index=False))
        print(no.round(2).to_string(index=False))
        print(bo.round(2).to_string(index=False))
        print(shift.round(1).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
