"""How much data goes to the model and how much to the meta-learner: the argument's inputs, measured on 2014-2021 only
(no 2022-2026 match is read), and the prequential check on 2019-2021. The argument itself is in
docs/studies/meta_stack/README.md ("How much data for the model, how much for the meta-learner").

Per tour, the meta-model S2 has weights b = (b_C, b_M) on the closing line's and the no-odds model's log-odds. With J
the per-match information matrix, K the per-match score covariance and n the matches it is fitted on, the expected
excess log loss on new matches, in nats per match, decomposes as

    estimation      tr(J^-1 K) / (2 n)                      (Takeuchi; k / (2 n) for a correct model, k = 2)
    drift           1/2 tr(J S_W)                           S_W: covariance of (the window's weights - the target
                                                            season's); iid season effects tau^2: S_W = tau^2 (1 + 1/W);
                                                            a random walk with step Q: S_W = Q (W + 1)(2W + 1) / (6W)
    the model's     Delta(W) = L*(model trained to Y-1-W) - L*(model trained to Y-1), the hold-out design only: the
    lost seasons    model that makes the target's forecast never saw the meta-learner's W seasons (first order in
                    the seasons withheld). Cross-fitting withholds nothing; its weights are learned on forecasts of
                    models trained on less data, which is part of the drift term (second order in the weights)

Measured here:
    per_season      b, its sandwich covariance and n for every out-of-sample season 2014-2021 (S2, four-seed means)
    constants       tr(J^-1 K) (iid; four-week clusters as a sensitivity), J, the mean season size, tau^2, Q, and a
                    trend of b_M on the size of the window that made the forecasts (the mismatch)
    lost seasons    Delta(W) for W = 1-3 on 2019-2021: S2 fitted in-sample on the target season (so estimation and
                    drift are absent and the in-sample optimism, the same for both, cancels) on the hold-out model's
                    forecasts against the walk-forward model's
    expected        the expected excess of each design, W = 1-12
    prequential     the designs run forward on 2019-2021: each target season scored by a meta-learner fitted only on
                    earlier seasons (cross-fit: last 1, 2, 3, 5 seasons, every season from 2014; hold-out: W = 1-3),
                    against cross-fit from 2014
Writes data/studies/meta_stack/design.json and design_prequential.csv.
Run: ./python.sh src/eda/meta_stack/design.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.meta_stack import common as C  # noqa: E402
from src.eda.meta_stack import meta as M  # noqa: E402
from src.eda.surface_ios import common as SC  # noqa: E402  (jdump)
from src.eda.tabpfn_thinking import common as T  # noqa: E402

DESIGN_YEARS = tuple(range(min(C.PRE), max(C.VAL) + 1))       # 2014-2021: everything this argument may read
WS = tuple(range(1, 13))
HOLD_WS = (1, 2, 3)
CROSS = ("last1", "last2", "last3", "last5", "from2014")
REF = "from2014"


def zs(d: pd.DataFrame, noodds: str = "p_noodds") -> M.Z:
    return {"mkt": C.zlogit(d["p_mkt"]), "noodds": C.zlogit(d[noodds]), "base": C.zlogit(d["p_base"])}


def psd(a: np.ndarray) -> np.ndarray:
    w, v = np.linalg.eigh((a + a.T) / 2)
    return (v * np.clip(w, 0, None)) @ v.T


def per_season(wf: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for tour in C.TOURS:
        for s in DESIGN_YEARS:
            g = wf[(wf["tour"] == tour) & (wf["year"] == s)]
            if g.empty:
                continue
            z, y = zs(g), g["a_won"].to_numpy(float)
            b, _ = M.fit("S2", z, y)
            sw = M.sandwich("S2", z, y, b)
            rows.append({"tour": tour, "season": s, "n": len(g), "b_C": b[0], "b_M": b[1],
                         "var_C": sw["cov"][0, 0], "var_M": sw["cov"][1, 1], "cov_CM": sw["cov"][0, 1],
                         "window_rows": int(wf.attrs["train_rows"][s]), "tr_JiK": sw["tr"]})
    return pd.DataFrame(rows)


def constants(wf: pd.DataFrame, ps: pd.DataFrame) -> dict:
    out = {}
    for tour in C.TOURS:
        g = wf[(wf["tour"] == tour) & wf["year"].isin(DESIGN_YEARS)]
        z, y = zs(g), g["a_won"].to_numpy(float)
        b, se = M.fit("S2", z, y)
        iid = M.sandwich("S2", z, y, b)
        clu = M.sandwich("S2", z, y, b, T.blocks(g["tournament_date"].to_numpy(), 28))
        p = ps[ps["tour"] == tour].sort_values("season")
        B = p[["b_C", "b_M"]].to_numpy()
        V = np.stack([[[r.var_C, r.cov_CM], [r.cov_CM, r.var_M]] for r in p.itertuples()])
        tau2_raw = np.cov(B.T, ddof=1) - V.mean(axis=0)
        steps = []
        for i in range(1, len(B)):                            # a random walk: Var(b_s - b_r) = (s - r) Q + V_s + V_r
            gap = p["season"].iloc[i] - p["season"].iloc[i - 1]
            d = (B[i] - B[i - 1])[:, None]
            steps.append((d @ d.T - V[i] - V[i - 1]) / gap)
        Q_raw = np.mean(steps, axis=0)
        dev = B - B.mean(axis=0)                              # persistence: lag-1 correlation of the deviations
        lag1 = [float(np.corrcoef(dev[1:, j], dev[:-1, j])[0, 1]) for j in range(2)]
        w = 1 / p["var_M"].to_numpy()                         # the mismatch: b_M against log(rows the model saw)
        X = np.column_stack([np.ones(len(p)), np.log(p["window_rows"].to_numpy(float))])
        coef = np.linalg.solve((X.T * w) @ X, (X.T * w) @ p["b_M"].to_numpy())
        cov = np.linalg.inv((X.T * w) @ X)
        resid = p["b_M"].to_numpy() - X @ coef
        out[tour] = {"pooled_b": b.tolist(), "pooled_se": se.tolist(), "J": iid["J"].tolist(), "tr_JiK_iid": iid["tr"],
                     "tr_JiK_cluster4w": clu["tr"], "k": 2, "mean_season_n": float(p["n"].mean()),
                     "tau2": psd(tau2_raw).tolist(), "tau2_raw": tau2_raw.tolist(), "Q": psd(Q_raw).tolist(),
                     "Q_raw": Q_raw.tolist(), "lag1_corr_bC_bM": lag1,
                     "trend_bM_per_log_rows": float(coef[1]), "trend_se": float(np.sqrt(cov[1, 1])),
                     "trend_chi2_per_df": float(np.sum(w * resid ** 2) / (len(p) - 2))}
    return out


def expected(cs: dict, delta: dict) -> pd.DataFrame:
    """Expected excess log loss (milli per match) of each design and window W, per tour and match-weighted."""
    rows = []
    for tour, c in cs.items():
        J = np.asarray(c["J"])
        for W in WS:
            est = 1000 * c["tr_JiK_iid"] / (2 * c["mean_season_n"] * W)
            iid = 1000 * 0.5 * np.trace(J @ np.asarray(c["tau2"])) * (1 + 1 / W)
            rw = 1000 * 0.5 * np.trace(J @ np.asarray(c["Q"])) * (W + 1) * (2 * W + 1) / (6 * W)
            d = delta.get((tour, W), {}).get("gain")
            rows.append({"tour": tour, "W": W, "estimation": est, "drift_iid": iid, "drift_rw": rw,
                         "cross_iid": est + iid, "cross_rw": est + rw, "lost_seasons": None if d is None else -d,
                         "holdout_iid": None if d is None else est + iid - d,
                         "holdout_rw": None if d is None else est + rw - d})
    out = pd.DataFrame(rows)
    n = {t: cs[t]["mean_season_n"] for t in cs}
    both = out.groupby("W").apply(lambda g: pd.Series({k: np.average(g[k].astype(float), weights=[n[t] for t in g["tour"]])
                                                       for k in out.columns if k not in ("tour", "W")}),
                                  include_groups=False).reset_index()
    both["tour"] = "both"
    return pd.concat([out, both], ignore_index=True)


def holdout_optimum(cs: dict, delta: dict) -> dict:
    """If a hold-out split is used anyway: with each withheld season costing the model about d (Delta(W) ~ d W, a
    least-squares line through the origin over W = 1-3) and one season of meta-data costing a = tr(J^-1 K) / (2 n),
    the split's cost a / W + d W is smallest at W* = sqrt(a / d), where it is 2 sqrt(a d) (milli per match)."""
    out = {}
    for tour, c in cs.items():
        a = 1000 * c["tr_JiK_iid"] / (2 * c["mean_season_n"])
        W = np.array(HOLD_WS, dtype=float)
        cost = np.array([-delta[(tour, w)]["gain"] for w in HOLD_WS])
        d = float(W @ cost / (W @ W))
        out[tour] = {"a_one_season": a, "d_per_season_withheld": d, "costs_W1_W3": cost.tolist(),
                     "W_star": float(np.sqrt(a / d)) if d > 0 else None,
                     "cost_at_W_star": float(2 * np.sqrt(a * d)) if d > 0 else None}
    return out


def holdout_frame(wf: pd.DataFrame, hold: pd.DataFrame, target: int, W: int) -> pd.DataFrame:
    """The hold-out design for one target: the no-odds model trained to target - 1 - W, its four-seed mean forecasts
    of the W meta seasons and the target (column p_hold)."""
    t = target - 1 - W
    h = hold[hold["train_to"] == t].groupby("match_id")["p"].mean().rename("p_hold")
    g = wf[wf["year"].between(target - W, target)].merge(h, left_on="match_id", right_index=True, how="left")
    if g["p_hold"].isna().any():
        raise RuntimeError(f"hold-out model trained to {t} lacks forecasts for {target - W}-{target}")
    return g


def lost_seasons(wf: pd.DataFrame, hold: pd.DataFrame) -> tuple[dict, list]:
    """Delta(W): S2 fitted in-sample on the target season (per tour), the hold-out model's forecasts against the
    walk-forward model's; positive gain = the hold-out model is better (expected negative)."""
    out, rows = {}, []
    for W in HOLD_WS:
        parts = []
        for target in C.VAL:
            g = holdout_frame(wf, hold, target, W)
            g = g[g["year"] == target].copy()
            for tour in C.TOURS:
                k = (g["tour"] == tour).to_numpy()
                y = g.loc[k, "a_won"].to_numpy(float)
                for col, name in (("p_noodds", "p_or_cross"), ("p_hold", "p_or_hold")):
                    z = zs(g[k], col)
                    b, _ = M.fit("S2", z, y)
                    g.loc[k, name] = M.predict("S2", z, b)
                    b1, _ = M.fit("mkt", z, y)
                    g.loc[k, "p_or_mkt"] = M.predict("mkt", z, b1)
            parts.append(g)
        g = pd.concat(parts, ignore_index=True)
        for tour in ("atp", "wta", "both"):
            h = g if tour == "both" else g[g["tour"] == tour]
            y, dts = h["a_won"].to_numpy(), h["tournament_date"].to_numpy()
            c = T.compare(T.ll(h["p_or_cross"].to_numpy(), y), T.ll(h["p_or_hold"].to_numpy(), y), dts)
            out[(tour, W)] = c
            c2 = T.compare(T.ll(h["p_or_mkt"].to_numpy(), y), T.ll(h["p_or_cross"].to_numpy(), y), dts)
            c3 = T.compare(T.ll(h["p_or_mkt"].to_numpy(), y), T.ll(h["p_or_hold"].to_numpy(), y), dts)
            c4 = T.compare(T.ll(h["p_noodds"].to_numpy(), y), T.ll(h["p_hold"].to_numpy(), y), dts)  # no close
            rows.append({"tour": tour, "W": W, "hold_vs_cross": c, "cross_info_over_mkt": c2,
                         "hold_info_over_mkt": c3, "standalone_hold_vs_cross": c4})
    return out, rows


def prequential(wf: pd.DataFrame, hold: pd.DataFrame) -> pd.DataFrame:
    """Each design run forward on 2019-2021; per match the forecast of every design that is defined there."""
    g = wf[wf["year"].isin(C.VAL)].copy()
    y, year, tour = wf["a_won"].to_numpy(float), wf["year"].to_numpy(), wf["tour"].to_numpy()
    z = zs(wf)
    for kind in CROSS:
        for spec in ("S2", "mkt", "best"):
            p, _ = M.walk_forward(spec, z, y, year, tour, C.VAL, lambda t, k=kind: M.window(k, t))
            g[f"{spec}|cross:{kind}"] = p[wf["year"].isin(C.VAL).to_numpy()]
    for W in HOLD_WS:
        col = np.full(len(g), np.nan)
        for target in C.VAL:
            h = holdout_frame(wf, hold, target, W)
            zh = zs(h, "p_hold")
            yh, yr, tr = h["a_won"].to_numpy(float), h["year"].to_numpy(), h["tour"].to_numpy()
            p, _ = M.walk_forward("S2", zh, yh, yr, tr, [target], lambda t: list(range(t - W, t)))
            got = pd.Series(p, index=h["match_id"]).dropna()
            m = g["match_id"].isin(got.index).to_numpy()
            col[m] = got.reindex(g.loc[m, "match_id"]).to_numpy()
        g[f"S2|holdout:{W}"] = col
    return g


def compare_designs(g: pd.DataFrame) -> pd.DataFrame:
    ref = f"S2|cross:{REF}"
    rows = []
    cols = [c for c in g.columns if c.startswith(("S2|", "mkt|", "best|"))]
    for tour in ("atp", "wta", "both"):
        h0 = g if tour == "both" else g[g["tour"] == tour]
        for c in cols:
            h = h0[h0[[c, ref]].notna().all(axis=1)]
            y = h["a_won"].to_numpy()
            r = T.compare(T.ll(h[ref].to_numpy(), y), T.ll(h[c].to_numpy(), y), h["tournament_date"].to_numpy())
            rows.append({"tour": tour, "design": c, "vs": ref, "matches": r["n"], "gain": r["gain"], "lo": r["lo"],
                         "hi": r["hi"], "log_loss": float(T.ll(h[c].to_numpy(), y).mean())})
    return pd.DataFrame(rows)


def main() -> int:
    wf_all = pd.read_parquet(C.OUT / "walkforward.parquet")
    years = pd.read_parquet(C.SIOS / "base_frame.parquet", columns=["year"])["year"]
    wf = wf_all[wf_all["year"].isin(DESIGN_YEARS)].reset_index(drop=True)          # never a 2022-2026 match
    wf.attrs["train_rows"] = {s: int((years < s).sum()) for s in DESIGN_YEARS}
    hold = pd.read_parquet(C.OUT / "holdout.parquet")
    hold = hold[hold["year"].isin(DESIGN_YEARS)]
    ps = per_season(wf)
    cs = constants(wf, ps)
    delta, delta_rows = lost_seasons(wf, hold)
    ex = expected(cs, delta)
    hopt = holdout_optimum(cs, delta)
    pre = prequential(wf, hold)
    cmp_ = compare_designs(pre)
    cmp_.to_csv(C.OUT / "design_prequential.csv", index=False)
    SC.jdump({"key": "milli-log-loss per match. expected: expected excess over the best weights for the target season "
                     "(lower = better). prequential and lost_seasons: gain of the named design over the reference, "
                     "positive = the named design has the lower log loss (better); a 95% interval spanning 0 is a tie",
              "per_season": ps.to_dict("records"), "constants": cs,
              "lost_seasons": [{**r, "hold_vs_cross": r["hold_vs_cross"]} for r in delta_rows],
              "expected": ex.to_dict("records"), "holdout_optimum": hopt, "prequential": cmp_.to_dict("records")},
             C.OUT / "design.json")
    with pd.option_context("display.width", 220, "display.max_rows", 200):
        print(ps.round(4).to_string(index=False))
        for t, c in cs.items():
            print(t, {k: (np.round(v, 5).tolist() if isinstance(v, list) else round(v, 5) if isinstance(v, float) else v)
                      for k, v in c.items()})
        for r in delta_rows:
            print(r["tour"], r["W"], {k: round(v, 3) if isinstance(v, float) else v
                                      for k, v in r["hold_vs_cross"].items() if k in ("n", "gain", "lo", "hi")},
                  "info cross", round(r["cross_info_over_mkt"]["gain"], 3), "info hold",
                  round(r["hold_info_over_mkt"]["gain"], 3), "standalone",
                  {k: round(v, 3) for k, v in r["standalone_hold_vs_cross"].items() if k in ("gain", "lo", "hi")})
        print(ex[ex["tour"] == "both"].round(4).to_string(index=False))
        print("hold-out optimum:", hopt)
        print(cmp_[cmp_["tour"] == "both"].round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
