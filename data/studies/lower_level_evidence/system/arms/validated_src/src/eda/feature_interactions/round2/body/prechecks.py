"""Round 2, the body analyst's result-free prechecks and constants (docs/studies/feature_interactions/round2/builds/
body.md). Every target is a statistic of the players' own earlier box scores or a schedule fact, on 2013-2018 rows
(tournament year), never a match result flag, a price or the current best's forecast (builders.md, critique M5).

    i058   Fat quantiles per tour (median, 80th percentile; box-score rows), the recovery trait's split-half reliability
           against three pure-luck replays (binomial points at Stage 3's pre-match expectations), and its empirical-
           Bayes variances (tau2 = the halves' covariance, sigma2 = the per-match residual variance)
    i065   the opponent-adjusted pace's split-half reliability (gate >= 0.3) and its shrinkage K = sigma2 / tau2
    i063   kappa and eta: serve- and return-point residuals on own and opponent Fat (with on-site counts held), points-
           weighted least squares; lambda is not identifiable from match-level box scores (set 0)
    i045   the within-event serve-decay slope: correlation of the first-in slope with the first-won slope across player-
           windows, real against binomial replays
    i066   the iid model's expected points as a function of |logit P| for best of 3 and 5 (Stage 2's simulator)

Writes data/studies/feature_interactions/round2/body/prechecks.json.
Run: ./python.sh src/eda/feature_interactions/round2/body/prechecks.py [i058 i065 i063 i045 i066]
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions.features import f20_fatigue as F  # noqa: E402

OUT = C.OUT / "round2" / "body"
WINDOW = (2013, 2018)
SEED = 20261006


def load_history() -> pd.DataFrame:
    from src.eda.feature_interactions.history import long_table
    P0 = pd.DataFrame({"season": [C.REPLICATION[-1]]})          # only the season cut is read from it
    return F.history(P0, long_table())


def split_half(groups: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """A random half label (0/1) per row, balanced within each group."""
    order = rng.permutation(len(groups))
    g = pd.Series(groups[order])
    rank = g.groupby(g.to_numpy()).cumcount().to_numpy()
    half = np.empty(len(groups), int)
    half[order] = rank % 2
    return half


def corr(a, b) -> float:
    m = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[m], b[m])[0, 1]) if m.sum() > 10 else np.nan


# ------------------------------------------------------------------------------------------------

def i058(H: pd.DataFrame) -> dict:
    from src.eda.feature_interactions.features import f21_constitution as B
    r = B.residuals(H)
    f, _ = F.fat(H)
    win = (H["tyear"] >= WINDOW[0]).to_numpy() & (H["tyear"] <= WINDOW[1]).to_numpy()
    tour = H["tour"].astype(str).to_numpy()
    use = win & np.isfinite(r)
    q = {t: (float(np.quantile(f[use & (tour == t)], 0.5)), float(np.quantile(f[use & (tour == t)], 0.8)))
         for t in C.TOURS}
    cls = B.fat_class(H, q)
    out = {"Q_FAT": q, "rows": int(use.sum()),
           "share_high": {t: float(np.mean(cls[use & (tour == t)] == 1)) for t in C.TOURS},
           "share_low": {t: float(np.mean(cls[use & (tour == t)] == -1)) for t in C.TOURS}}
    sel = use & np.isin(cls, (1.0, -1.0))
    pid = H["pid"].to_numpy()[sel]
    c = cls[sel]
    sigma2 = float(np.nanmean([np.var(r[sel][c == k]) for k in (1.0, -1.0)]))
    td, sd, rd = (H[k].to_numpy(float)[sel] for k in ("tpw_d", "spw_d", "rpw_d"))
    ps, po = H["pw_ps_self"].to_numpy(float)[sel], H["pw_ps_opp"].to_numpy(float)[sel]
    rng = np.random.default_rng(SEED)

    def reliability(res: np.ndarray, min_n: int = 5) -> dict:
        half = split_half(pid * 2 + (c > 0), rng)
        d = []
        for h in (0, 1):
            m = half == h
            g = pd.DataFrame({"p": pid[m], "c": c[m], "r": res[m]}).groupby(["p", "c"])["r"].agg(["mean", "size"])
            g = g[g["size"] >= min_n]["mean"].unstack()
            d.append((g.get(1.0) - g.get(-1.0)).rename(h))
        D = pd.concat(d, axis=1).dropna()
        return {"players": int(len(D)), "r": corr(D[0].to_numpy(), D[1].to_numpy()),
                "cov": float(np.cov(D[0], D[1])[0, 1]) if len(D) > 10 else np.nan}

    real = reliability(r[sel])
    replays = []
    for _ in range(3):
        sim = (rng.binomial(sd.astype(int), np.clip(ps, 0, 1)) + rng.binomial(rd.astype(int), np.clip(1 - po, 0, 1))
               - (sd * ps + rd * (1 - po))) / td
        replays.append(reliability(sim))
    rep_r = np.array([x["r"] for x in replays])
    se = (1 - real["r"] ** 2) / np.sqrt(max(real["players"] - 3, 1))
    # the gate AS DECLARED (round-1 card, master list): the raw split-half correlation above the pure-luck replays'
    # (their mean); a 2-SE margin is reported beside it, not applied (coordinator, 6-7 Oct: gates bind as declared)
    out.update({"sigma2": sigma2, "tau2_cov": real["cov"], "real": real, "replays": replays,
                "replay_mean_r": float(rep_r.mean()), "gate_pass": bool(real["r"] > rep_r.mean()),
                "margin_2se_pass": bool(real["r"] - rep_r.mean() > 2 * se), "se_r": float(se)})
    return out


def _window(H):
    return (H["tyear"] >= WINDOW[0]).to_numpy() & (H["tyear"] <= WINDOW[1]).to_numpy()


def i065(H: pd.DataFrame) -> dict:
    from src.eda.feature_interactions.features import f22_demand as D
    win = _window(H)
    out = {}
    K = 10.0
    for it in range(2):                                     # K enters only through the opponent adjustment
        _, _, r1 = D.pace(H, K)
        sel = win & np.isfinite(r1)
        pid = H["pid"].to_numpy()[sel]
        rng = np.random.default_rng(SEED)
        half = split_half(pid, rng)
        g = pd.DataFrame({"p": pid, "h": half, "r": r1[sel]}).groupby(["p", "h"])["r"].agg(["mean", "size"])
        g = g[g["size"] >= 10]["mean"].unstack().dropna()
        tau2 = float(np.cov(g[0], g[1])[0, 1])
        within = pd.DataFrame({"p": pid, "r": r1[sel]}).groupby("p")["r"].var().mean()
        K = float(within / tau2) if tau2 > 0 else np.inf
        out[f"iter{it}"] = {"players": int(len(g)), "reliability": corr(g[0].to_numpy(), g[1].to_numpy()),
                            "tau2": tau2, "sigma2_within": float(within), "K": K}
    out["K_PACE"] = K
    out["gate_pass"] = bool(out["iter1"]["reliability"] >= 0.3)
    return out


def i063(H: pd.DataFrame) -> dict:
    from src.eda.feature_interactions.features import f21_constitution as B
    from src.eda.feature_interactions.features import f22_demand as D
    from src.eda.feature_interactions.features import f23_arrival as G
    B.residuals(H)
    G.arrival(H)
    win = _window(H)
    f, _ = F.fat(H)
    p = D.partner(H)
    fo = np.where(p >= 0, f[np.maximum(p, 0)], np.nan)
    on = np.log1p(H["on_n"].to_numpy(float))
    ono = np.where(p >= 0, on[np.maximum(p, 0)], np.nan)
    ps, po = H["pw_ps_self"].to_numpy(float), H["pw_ps_opp"].to_numpy(float)
    sn, sd, rn, rd = (H[k].to_numpy(float) for k in ("spw_n", "spw_d", "rpw_n", "rpw_d"))
    res = {}
    for name, y, w in (("serve", (sn - sd * ps) / sd, sd), ("return", (rn - rd * (1 - po)) / rd, rd)):
        m = win & H["played"].to_numpy(bool) & np.isfinite(y) & np.isfinite(fo) & np.isfinite(ono) & (w > 0)
        X = np.column_stack([np.ones(m.sum()), f[m], fo[m], on[m], ono[m]])
        sw = np.sqrt(w[m])
        beta, *_ = np.linalg.lstsq(X * sw[:, None], y[m] * sw, rcond=None)
        e = y[m] - X @ beta
        XtWX_inv = np.linalg.inv((X * w[m][:, None]).T @ X)
        meat = (X * (w[m] * e)[:, None]).T @ (X * (w[m] * e)[:, None])
        se = np.sqrt(np.diag(XtWX_inv @ meat @ XtWX_inv))
        res[name] = {"rows": int(m.sum()), "b_self": float(beta[1]), "b_opp": float(beta[2]),
                     "se_self": float(se[1]), "se_opp": float(se[2]), "b_on_self": float(beta[3]),
                     "b_on_opp": float(beta[4])}
    kappa = 0.5 * (-res["serve"]["b_self"] + res["return"]["b_opp"])
    eta = 0.5 * (res["serve"]["b_opp"] - res["return"]["b_self"]) / kappa if kappa != 0 else np.nan
    return {**res, "KAPPA": float(kappa), "ETA": float(eta), "LAMBDA": 0.0}


def i045(H: pd.DataFrame) -> dict:
    from src.eda.feature_interactions.features import f26_impairment as J
    zfi, zfw = J.serve_z(H)
    win = _window(H)
    tid = H["tournament_id"].astype(str).to_numpy()
    pid = H["pid"].to_numpy()
    last_of_seg = np.r_[(pid[1:] != pid[:-1]) | (tid[1:] != tid[:-1]), True]

    def slopes(a, b):
        sa, na = J.window_slope(H, a)
        sb, nb = J.window_slope(H, b)
        m = win & last_of_seg & (na >= 3) & np.isfinite(sa) & np.isfinite(sb)
        return sa[m], sb[m]

    sa, sb = slopes(zfi, zfw)
    real = {"windows": int(len(sa)), "r": corr(sa, sb), "cov": float(np.cov(sa, sb)[0, 1])}
    rng = np.random.default_rng(SEED)
    sv, fi = H["svpt"].to_numpy(float), H["first_in"].to_numpy(float)
    m1, m2 = H["_m1"].to_numpy(float), H["_m2"].to_numpy(float)
    ok = np.isfinite(zfi) & np.isfinite(zfw)
    reps = []
    for _ in range(3):
        fi_s = np.where(ok, rng.binomial(np.where(ok, sv, 0).astype(int), m1), np.nan)
        fw_s = np.where(ok, rng.binomial(np.where(ok, fi_s, 0).astype(int), m2), np.nan)
        z1 = np.where(ok, (fi_s - sv * m1) / np.sqrt(np.where(ok, sv, 1) * m1 * (1 - m1)), np.nan)
        z2 = np.where(ok & (fi_s > 0), (fw_s - fi_s * m2) / np.sqrt(np.maximum(fi_s, 1) * m2 * (1 - m2)), np.nan)
        a, b = slopes(z1, z2)
        reps.append({"windows": int(len(a)), "r": corr(a, b), "cov": float(np.cov(a, b)[0, 1])})
    rep_r = np.mean([x["r"] for x in reps])
    se = 1 / np.sqrt(max(real["windows"] - 3, 1))
    return {"real": real, "replays": reps, "TAU2_DEC": real["cov"], "replay_mean_r": float(rep_r),
            "gate_pass": bool(real["r"] > rep_r), "margin_2se_pass": bool(real["r"] - rep_r > 2 * se),
            "se_r": float(se)}


def i066() -> dict:
    from scipy.special import expit
    from src.eda.predictability_diagnostic import stage2_iid as M
    out = {}
    for bo in (3, 5):
        xs, ys = [], []
        for g in np.linspace(0.0, 0.30, 16):                 # serve-share gap around 0.64
            pa, pb = np.full(20000, 0.64 + g / 2), np.full(20000, 0.64 - g / 2)
            sim = M.simulate(pa, pb, bo, np.full(20000, "TB7@6"), seed=SEED)
            p = float(M.match_win(pa[:1], pb[:1], bo)[0])
            xs.append(float(abs(np.log(p / (1 - p)))))
            ys.append(float(np.mean(sim["served"].sum(axis=1)) if "served" in sim else np.nan))
        out[bo] = {"abs_logit": xs, "points": ys}
    return out


def main() -> int:
    warnings.simplefilter("ignore")
    which = sys.argv[1:] or ["i058", "i065", "i063", "i045", "i066"]
    path = OUT / "prechecks.json"
    res = json.loads(path.read_text()) if path.exists() else {}
    H = load_history() if set(which) - {"i066"} else None
    for w in which:
        C.log(f"precheck {w}")
        res[w] = globals()[w](H) if w != "i066" else i066()
        C.log(json.dumps(res[w], default=str)[:1500])
    OUT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
