"""Role E (red team), CP1: an independent re-derivation of one men's Challenger w and delta.

Cell: men (atp), serve points won (spw), season_used 2024 (fit targets: main-tour main draws of 2018-2023 surely
finished before season 2024's first match could start). Role B's numbers (params_dev.parquet): h = 26 weeks,
w_free CH 0.575, w (shrunk) CH 0.563 [0.41, 0.80], delta CH -0.081 [-0.102, -0.064].

Written from scratch (no import of relationship.py): reads the frozen Stage 0, the frozen timeline and role A's strength
copy, rebuilds the targets and their histories with an explicit per-target loop (not cumulative sums), and fits:
  (1) B's estimand with my own code: the credibility predictor, all lower levels free (k, mu, delta_CH, delta_CHQ,
      w_TQ, w_GSQ, w_CH, w_CHQ), gamma fixed at role A's 2024 value, h = 26 weeks;
  (2) a simpler delta: same player, same season, d-weighted mean of (y - s - gamma*gap) at CH minus at the main tour,
      averaged over player-seasons with >= 3 box scores at each (2018-2023, results in by the cutoff);
  (3) a simpler w: a profile over a w grid with delta fixed at (2), k and mu refitted at each w.
  (4) the w > 1 question: the same fit with tier-specific prior means (home tier by the previous 365 days' matches).
Reads no outcome of a 2025-2026 match (years <= 2023 only, asserted).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT))
from src.eda.lower_level_evidence import common as C  # noqa: E402  (paths and bucket() only)

OUT = Path(__file__).resolve().parents[1]
STRENGTH = ROOT / "data/studies/lower_level_evidence/system/classes/strength_elo.parquet"
TOUR, STAT, SEASON = "atp", "spw", 2019
H_DAYS = 26 * 7.0
WINDOW = 730
GAMMA = -0.060454 / 100.0          # role A gamma for (2019, atp, spw), dev_gamma_used.csv
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:6.1f}s] {m}", flush=True)


def main():
    m = C.load_matches(C.STAGE0_DIR, columns=["tour", "year", "map_level", "surface", "status", "format", "has_box",
                                               "tournament_date", "order", "player_a_id", "player_b_id"])
    t = pd.read_parquet(C.TIMING, columns=["match_id", "es", "lf", "obs"])
    m = m.merge(t, on="match_id", how="left")
    for c in ("es", "lf", "obs"):
        if np.issubdtype(m[c].dtype, np.datetime64):
            m[c] = m[c].values.astype("datetime64[D]").astype("int64").astype(float)
    cutoff = float(m.loc[m["bucket"].eq("MAIN") & m["year"].eq(SEASON), "es"].min())
    log(f"cutoff(2024) = {cutoff} (B/A: 19721)")
    m = m[m["tour"].eq(TOUR) & (m["year"] <= SEASON - 1)].copy()
    assert (pd.to_datetime(m["tournament_date"]) < pd.Timestamp("2024-12-30")).all()
    ids = m["match_id"].tolist()
    p = pd.read_parquet(C.STAGE0_DIR / "stage0_match_players.parquet",
                        columns=["match_id", "player_id", "side", "spw_n", "spw_d"],
                        filters=[("match_id", "in", ids)])
    p = p.merge(m, on="match_id", how="inner")
    e = pd.read_parquet(STRENGTH, filters=[("match_id", "in", ids)]).set_index("match_id")
    p["elo_opp"] = np.where(p["side"].eq("A"), p["match_id"].map(e["elo_b_ret"]), p["match_id"].map(e["elo_a_ret"]))
    p["level"] = p["bucket"].replace({"TEAM": "MAIN"})
    p["is_target_bucket"] = p["bucket"].eq("MAIN")
    p["box"] = p["status"].eq("completed") & p["format"].eq("standard") & p["has_box"].fillna(False).astype(bool)
    p["played"] = p["status"].isin(["completed", "retired"])
    p["day"] = pd.to_datetime(p["tournament_date"]).values.astype("datetime64[D]").astype("int64")
    p["surf"] = p["surface"].where(p["surface"].isin(["Hard", "Clay", "Grass", "Carpet"]), "other")
    # home tier from all played matches of the previous 365 days (for check 4), computed before the box filter
    tier_of = {"MAIN": "MT", "TEAM": "MT", "TQ": "Q", "GSQ": "Q", "CH": "CH", "CHQ": "CH", "ITF": "ITF", "ITFQ": "ITF"}
    p["tier_row"] = p["bucket"].map(tier_of)
    p = p.sort_values(["player_id", "order"], kind="mergesort").reset_index(drop=True)
    home = np.empty(len(p), dtype=object)
    for pid, g in p.groupby("player_id", sort=False):
        idx = g.index.to_numpy()
        dd = g["day"].to_numpy()
        tr = g["tier_row"].to_numpy()
        pl = g["played"].to_numpy()
        lo = np.searchsorted(dd, dd - 365, side="left")
        for j in range(len(idx)):
            sel = slice(lo[j], j)
            cnt = {k: int(((tr[sel] == k) & pl[sel]).sum()) for k in ("MT", "Q", "CH", "ITF")}
            tot = sum(cnt.values())
            home[idx[j]] = "none" if tot == 0 else max(("MT", "Q", "CH", "ITF"), key=lambda k: (cnt[k], -("MT", "Q", "CH", "ITF").index(k)))
    p["home"] = home
    n, d = p["spw_n"].to_numpy(float), p["spw_d"].to_numpy(float)
    ok = p["box"].to_numpy() & np.isfinite(n) & np.isfinite(d) & (d > 0) & (n >= 0) & (n <= d) & \
        np.isfinite(p["elo_opp"].to_numpy(float))
    q = p[ok].reset_index(drop=True)
    q["y"] = np.log((q["spw_n"] + 0.5) / (q["spw_d"] + 1.0)) - np.log1p(-(q["spw_n"] + 0.5) / (q["spw_d"] + 1.0))
    log(f"valid {STAT} rows (atp, years <= 2023): {len(q):,}; by level {q['level'].value_counts().to_dict()}")

    # fit targets
    tgt = q["is_target_bucket"] & q["year"].between(SEASON - 6, SEASON - 1) & (q["lf"] + 1.0 <= cutoff)
    T = np.flatnonzero(tgt.to_numpy())
    log(f"fit targets: {len(T):,} (B: 27,772)")
    # E_ref: mean opponent Elo of main-tour box rows with lf + 1 <= cutoff and es >= cutoff - 365 (B's definition)
    mm = q["is_target_bucket"] & (q["lf"] + 1.0 <= cutoff) & (q["es"] >= cutoff - 365)
    eref = float(q.loc[mm, "elo_opp"].mean())
    log(f"E_ref = {eref:.3f} (B: 2212.941)")
    # surface offsets from the fit targets
    xs, ds, sf = q.loc[T, "spw_n"].to_numpy(), q.loc[T, "spw_d"].to_numpy(), q.loc[T, "surf"].to_numpy()
    lg = lambda r: np.log(r) - np.log1p(-r)  # noqa: E731
    base = lg(xs.sum() / ds.sum())
    soff = {s: (lg(xs[sf == s].sum() / ds[sf == s].sum()) - base if (sf == s).sum() >= 300 else 0.0)
            for s in ("Hard", "Clay", "Grass", "Carpet", "other")}
    log(f"surface offsets {soff}")
    q["s"] = q["surf"].map(soff)
    q["g"] = q["elo_opp"] - eref
    q["a"] = q["y"] - q["s"] - GAMMA * q["g"]            # opponent-adjusted, surface-centred observation

    # per-target window sums by an explicit loop over each player's earlier rows (independent of B's cumsums)
    levels = ["MAIN", "TQ", "GSQ", "CH", "CHQ"]
    V = np.zeros((len(T), len(levels)))
    A = np.zeros((len(T), len(levels)))
    lev_code = q["level"].map({L: i for i, L in enumerate(levels)}).fillna(-1).astype(int).to_numpy()
    pid = q["player_id"].to_numpy()
    order = q["order"].to_numpy()
    day = q["day"].to_numpy()
    obs = q["obs"].to_numpy(float)
    dd_ = q["spw_d"].to_numpy(float)
    aa = q["a"].to_numpy(float)
    starts = {}
    # rows are sorted by (player, order); index each player's block
    change = np.r_[0, np.flatnonzero(pid[1:] != pid[:-1]) + 1, len(q)]
    for i0, i1 in zip(change[:-1], change[1:]):
        starts[pid[i0]] = (i0, i1)
    for k, ti in enumerate(T):
        i0, _ = starts[pid[ti]]
        j = np.arange(i0, ti)
        j = j[(order[j] < order[ti]) & (day[j] >= day[ti] - WINDOW)]
        if not len(j):
            continue
        v = dd_[j] * np.exp2(-(obs[ti] - obs[j]) / H_DAYS)
        lc = lev_code[j]
        for li in range(len(levels)):
            mk = lc == li
            if mk.any():
                V[k, li] = v[mk].sum()
                A[k, li] = (v[mk] * aa[j][mk]).sum()
    log("window sums done")
    xt, dt = q.loc[T, "spw_n"].to_numpy(float), q.loc[T, "spw_d"].to_numpy(float)
    off_t = q.loc[T, "s"].to_numpy(float) + GAMMA * q.loc[T, "g"].to_numpy(float)
    home_t = q.loc[T, "home"].to_numpy()
    tiers = ["MT", "Q", "CH", "ITF", "none"]
    tier_ix = np.array([tiers.index(h) for h in home_t])

    def predict(th, delta_fixed=None, w_fixed=None, tier=False):
        i = 0
        k = np.exp(th[i]); i += 1
        if tier:
            mu = th[i:i + 5][tier_ix]; i += 5
        else:
            mu = th[i]; i += 1
        if delta_fixed is None:
            dCH, dCHQ = th[i], th[i + 1]; i += 2
        else:
            dCH, dCHQ = delta_fixed
        if w_fixed is None:
            w = th[i:i + 4]; i += 4
        else:
            w = np.asarray(w_fixed, float)
        num = k * mu + A[:, 0] + w[0] * A[:, 1] + w[1] * A[:, 2] + w[2] * (A[:, 3] - dCH * V[:, 3]) + \
            w[3] * (A[:, 4] - dCHQ * V[:, 4])
        den = k + V[:, 0] + w[0] * V[:, 1] + w[1] * V[:, 2] + w[2] * V[:, 3] + w[3] * V[:, 4]
        return off_t + num / den

    def nll(th, **kw):
        eta = predict(th, **kw)
        return -float(np.sum(xt * eta - dt * np.logaddexp(0.0, eta))) / dt.sum() * 1e4

    rate = xt.sum() / dt.sum()
    mu0 = lg(rate)
    res = {}
    # (1) B's estimand, all lower levels free (B's "w_free" analogue; no penalty)
    th0 = np.r_[np.log(10 * np.median(dt)), mu0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0]
    bnds = [(-3, 13), (-8, 8), (-1.5, 1.5), (-1.5, 1.5)] + [(0, 3)] * 4
    best = None
    for start_k in (np.log(10 * np.median(dt)), np.log(np.median(dt))):
        th0[0] = start_k
        r = minimize(nll, th0, method="L-BFGS-B", bounds=bnds, options={"ftol": 1e-13, "gtol": 1e-8, "maxiter": 5000})
        if best is None or r.fun < best.fun:
            best = r
    th = best.x
    res["free_fit"] = {"k": float(np.exp(th[0])), "mu": float(th[1]), "delta_CH": float(th[2]),
                       "delta_CHQ": float(th[3]), "w_TQ": float(th[4]), "w_GSQ": float(th[5]), "w_CH": float(th[6]),
                       "w_CHQ": float(th[7]), "nll_per_unit_x1e4": float(best.fun), "converged": bool(best.success)}
    log(f"(1) free fit: {res['free_fit']}")
    # profile in w_CH (others refitted) for the curvature: a likelihood-ratio 95% interval
    prof = []
    for wc in np.round(np.arange(0.2, 1.61, 0.05), 3):
        def nll_w(tt):
            full = np.r_[tt[:6], wc, tt[6]]
            return nll(full)
        t0 = np.r_[th[:6], th[7]]
        b2 = bnds[:6] + [bnds[7]]
        r = minimize(nll_w, t0, method="L-BFGS-B", bounds=b2, options={"ftol": 1e-13, "gtol": 1e-8, "maxiter": 5000})
        prof.append({"w_CH": float(wc), "dev_total": float(2 * (r.fun - best.fun) * dt.sum() / 1e4)})
    res["profile_w_CH"] = prof
    ok_ = [r["w_CH"] for r in prof if r["dev_total"] <= 3.84]
    res["profile_w_CH_LR95"] = [min(ok_), max(ok_)] if ok_ else None
    log(f"profile LR 95% for w_CH (iid targets, not player-clustered): {res['profile_w_CH_LR95']}")

    # (2) simpler delta: same player-season, CH minus MAIN, d-weighted means of the adjusted observation
    win = q["year"].between(SEASON - 6, SEASON - 1) & (q["lf"] + 1.0 <= cutoff)
    z = q[win & q["level"].isin(["MAIN", "CH"])].copy()
    z["dz"] = z["spw_d"] * z["a"]
    g = z.groupby(["player_id", "year", "level"]).agg(dz=("dz", "sum"), d=("spw_d", "sum"), nn=("a", "size"))
    g["mean"] = g["dz"] / g["d"]
    g = g.reset_index().pivot_table(index=["player_id", "year"], columns="level", values=["mean", "nn"])
    g = g.dropna()
    g = g[(g[("nn", "MAIN")] >= 3) & (g[("nn", "CH")] >= 3)]
    diff = (g[("mean", "CH")] - g[("mean", "MAIN")]).to_numpy()
    se = diff.std(ddof=1) / np.sqrt(len(diff))
    res["simple_delta_CH"] = {"player_seasons": int(len(diff)), "delta": float(diff.mean()), "se": float(se),
                              "lo": float(diff.mean() - 1.96 * se), "hi": float(diff.mean() + 1.96 * se)}
    log(f"(2) simple delta CH: {res['simple_delta_CH']}")

    # (3) simpler w: profile over a w grid (one w for CH; others at 1; CHQ excluded i.e. w=0 rows? no: at 1)
    grid = []
    for wv in (0.0, 0.25, 0.4, 0.5, 0.6, 0.75, 1.0, 1.25):
        def nll_g(tt):
            full = np.r_[tt[0], tt[1]]
            return nll(full, delta_fixed=(res["simple_delta_CH"]["delta"], 0.0), w_fixed=(1.0, 1.0, wv, 1.0))
        r = minimize(nll_g, th[:2], method="L-BFGS-B", bounds=bnds[:2], options={"ftol": 1e-13, "gtol": 1e-8})
        grid.append({"w_CH": wv, "nll_per_unit_x1e4": float(r.fun), "k": float(np.exp(r.x[0]))})
    bestg = min(grid, key=lambda r: r["nll_per_unit_x1e4"])
    for r in grid:
        r["dev_total_vs_best"] = float(2 * (r["nll_per_unit_x1e4"] - bestg["nll_per_unit_x1e4"]) * dt.sum() / 1e4)
    res["simple_w_grid"] = grid
    log(f"(3) simple w grid best: {bestg}")

    # (4) the same free fit with prior means per home tier
    th0t = np.r_[th[0], [th[1]] * 5, th[2:]]
    bndt = [(-3, 13)] + [(-8, 8)] * 5 + bnds[2:]
    r = minimize(lambda tt: nll(tt, tier=True), th0t, method="L-BFGS-B", bounds=bndt,
                 options={"ftol": 1e-13, "gtol": 1e-8, "maxiter": 5000})
    tt = r.x
    res["tier_prior_fit"] = {"k": float(np.exp(tt[0])), "mu_by_tier": dict(zip(tiers, map(float, tt[1:6]))),
                             "delta_CH": float(tt[6]), "delta_CHQ": float(tt[7]), "w_TQ": float(tt[8]),
                             "w_GSQ": float(tt[9]), "w_CH": float(tt[10]), "w_CHQ": float(tt[11]),
                             "tier_counts": pd.Series(home_t).value_counts().to_dict()}
    log(f"(4) tier-prior fit: {res['tier_prior_fit']}")
    res["inputs"] = {"cutoff": cutoff, "E_ref": eref, "surface_offsets": soff, "fit_targets": int(len(T)),
                     "gamma_per_100": GAMMA * 100, "h_weeks": 26, "years_read": "<= 2023"}
    res["B"] = {"w_free_CH": 0.5753, "w_CH": 0.5635, "w_CH_95": [0.412, 0.800], "delta_CH": -0.0812,
                "delta_CH_95": [-0.1016, -0.0636], "w_free_TQ": 1.125, "w_free_GSQ": 1.012, "w_free_CHQ": 0.833,
                "delta_CHQ": -0.0321, "k": 78.18, "mu": 0.1614, "E_ref": 2212.941, "fit_targets": 27772}
    (OUT / "rederive_spw_atp_2019.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    log(f"wrote {OUT / 'rederive_spw_atp_2019.json'}")


if __name__ == "__main__":
    main()
