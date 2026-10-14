"""Design scratch (agent 2): the speed-state candidates, tuned and compared on result-free targets, seasons <= 2023.

Every target is a timed player-match m; its features use only the player's own earlier history (earlier events, plus
earlier rounds of the same event; never other events of the same week nor the same round), with clock days `obs`.
The target statistic is m's own first-serve speed (the "next match" after the history). No match result is read.

Speeds are centred on frozen within-player system offsets: z = y - o[system] (Slam families and the key-statistic
basis against the tour system; `offsets()` estimates them on the tuning seasons only).

Candidates (side level; the match feature is A - B):
  (a) x_raw   14-day mean minus 364-day mean (registered), raw speeds;  x_cen the same on centred speeds
  (b) x_eb    x_cen shrunk by its precision: x_cen * tau2 / (tau2 + nu_b / k2 + s2 / N2)
  (c) x_ew    sum_j w_j (z_j - c52) / (sum_j w_j + K), w_j = 2^(-age_j / h) * n_j / (n_j + n0), j within 364 days
  (d) f_hat   posterior mean of the fast state f of a two-state Kalman filter on irregular match days:
                 z_m = L(t) + f(t) + eps_m,  eps ~ N(0, nu_b + s2 / n_m)          (b = basis: point mean / key stat)
                 L: random walk, variance q per day (diffuse prior: a change feature must not learn the level)
                 f: Ornstein-Uhlenbeck, stationary variance s2f, half-life hl days
              robust (Huber) update: the innovation is clipped at c predictive SDs; projected to the target day.

Scores (targets with a 364-day history): d_m = z_m - c52_m, the target's centred deviation from its 364-day mean.
  R2_oos  1 - sum (d - b F)^2 / sum d^2 on the evaluation seasons, slope b fitted on the tuning seasons (F = 0 where
          the feature is missing, i.e. "no change"); corr; and the match-level version (A - B of both).
  Kalman also scored as a level forecast: MSE of z_m against the 364-day mean and against L_hat + f_hat.

Run: ./python.sh src/eda/serve_speed_tabpfn/design/modeller_state.py [pm_first|ks_first]
Writes data/studies/serve_speed_tabpfn/design/modeller_state_<policy>.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.design import modeller_common as M  # noqa: E402

LAST = 2023
HALF_LIVES = (3.5, 7.0, 10.0, 14.0, 21.0, 28.0, 42.0, 70.0)
SLAMS = ("AO", "RG", "W", "USO")
S2 = {"atp": 13.49 ** 2, "wta": 10.72 ** 2}     # pooled per-serve variance (modeller_variance.json, <= 2023)
SPLIT = {"atp": (2022, 2023), "wta": (2019, 2021)}  # tune on seasons <= first; evaluate on seasons >= second


# ------------------------------------------------------------------------------------------------ offsets
def offsets(p: pd.DataFrame, last_year: int, window: int = 60) -> dict:
    """Frozen within-player offsets per (tour, system), from seasons <= last_year only (a field statistic frozen on an
    earlier period). Blocks = one player's matches at one edition (n-weighted mean); every pair of a player's blocks in
    different systems within +-window days (men) or 130 days (women, Slams only) gives one difference
    o[s1] - o[s2] + noise; the offsets are the least-squares solution with the tour's reference system at 0 (men: the
    busier tour-level system; women: AO). Systems with fewer than 20 pairs stay at 0."""
    out = {}
    q = p[p["year"] <= last_year]
    for t, g in q.groupby("tour"):
        if t == "atp":
            ref = "ks_tour" if (g["system"] == "ks_tour").sum() > (g["system"] == "pm_tour").sum() else "pm_tour"
            win = window
        else:
            ref, win = "AO", 130
        b = g.groupby(["player_id", "system", "tournament_id"]).apply(
            lambda x: pd.Series({"m": np.average(x["y"], weights=x["n"]), "day": x["obs"].mean()}),
            include_groups=False).reset_index()
        x = b.merge(b, on="player_id", suffixes=("_i", "_j"))
        x = x[(x["system_i"] < x["system_j"]) & ((x["day_i"] - x["day_j"]).abs() <= win)]
        systems = sorted(set(g["system"]))
        cnt = pd.concat([x["system_i"], x["system_j"]]).value_counts()
        keep = [s for s in systems if s == ref or cnt.get(s, 0) >= 20]
        x = x[x["system_i"].isin(keep) & x["system_j"].isin(keep)]
        free = [s for s in keep if s != ref]
        res = {s: 0.0 for s in systems}
        if free and len(x):
            A = np.zeros((len(x), len(free)))
            col = {s: k for k, s in enumerate(free)}
            for r, (si, sj) in enumerate(zip(x["system_i"], x["system_j"])):
                if si in col:
                    A[r, col[si]] += 1
                if sj in col:
                    A[r, col[sj]] -= 1
            sol, *_ = np.linalg.lstsq(A, (x["m_i"] - x["m_j"]).to_numpy(), rcond=None)
            res.update({s: float(sol[col[s]]) for s in free})
        res["_pairs"] = {s: int(cnt.get(s, 0)) for s in systems}
        out[t] = res
    return out


def centre(p: pd.DataFrame, off: dict, nu: dict) -> pd.DataFrame:
    p = p.copy()
    o = np.array([off.get(t, {}).get(s, 0.0) for t, s in zip(p["tour"], p["system"])])
    p["z"] = p["y"] - o
    s2 = p["tour"].map(S2).to_numpy()
    p["R"] = np.where(p["basis"].eq("ks"), nu["ks"], nu["pm"]) + s2 / p["n"].to_numpy()
    return p


# ------------------------------------------------------------------------------------------------ windows
def window_stats(p: pd.DataFrame, n0: float) -> pd.DataFrame:
    """Per timed row (as a target): 364-day and 14-day means (raw and centred), k2, N2, and exponentially weighted
    deviation sums for each half-life."""
    p = p.sort_values(["tour", "player_id", "tdate", "tournament_id", "round_order"], kind="mergesort")
    cols = ["m52", "c52", "n52", "k52", "m2", "c2", "k2", "N2", "last_age"] + \
           [f"ewn_{h}" for h in HALF_LIVES] + [f"ewd_{h}" for h in HALF_LIVES]
    out = np.full((len(p), len(cols)), np.nan)
    pos = 0
    idx_all = p.index.to_numpy()
    for _, g in p.groupby(["tour", "player_id"], sort=False):
        td, tid, ro, ob = (g["tdate"].to_numpy(), g["tournament_id"].to_numpy(), g["round_order"].to_numpy(),
                           g["obs"].to_numpy())
        y, z, n = g["y"].to_numpy(), g["z"].to_numpy(), g["n"].to_numpy()
        pw = n / (n + n0)
        for k in range(len(g)):
            earlier = (td < td[k]) | ((tid == tid[k]) & (ro < ro[k]))
            age = ob[k] - ob
            w52 = earlier & (age <= 364)
            row = out[pos + k]
            if not w52.any():
                continue
            n52 = n[w52].sum()
            row[0] = (y[w52] * n[w52]).sum() / n52
            row[1] = c52 = (z[w52] * n[w52]).sum() / n52
            row[2], row[3] = n52, w52.sum()
            row[8] = age[w52].min()
            w2 = earlier & (age <= 14)
            if w2.any():
                N2 = n[w2].sum()
                row[4] = (y[w2] * n[w2]).sum() / N2
                row[5] = (z[w2] * n[w2]).sum() / N2
                row[6], row[7] = w2.sum(), N2
            else:
                row[6], row[7] = 0, 0.0
            a, dz, ww = age[w52], z[w52] - c52, pw[w52]
            for j, h in enumerate(HALF_LIVES):
                w = ww * np.exp2(-np.maximum(a, 0) / h)
                row[9 + j] = (w * dz).sum()
                row[9 + len(HALF_LIVES) + j] = w.sum()
        pos += len(g)
    res = pd.DataFrame(out, columns=cols, index=idx_all)
    return p.join(res)


# ------------------------------------------------------------------------------------------------ Kalman
def kalman(p: pd.DataFrame, targets: pd.DataFrame, prm: dict) -> pd.DataFrame:
    """Two-state robust Kalman filter per player over the timed rows of p (centred z, noise R); for each target row
    (player_id, tdate, tournament_id, round_order, obs), the state from the allowed history projected to the target
    day: f_hat, f_sd, L_hat, L_sd, hist (number of timed history rows)."""
    lam = math.log(2) / prm["hl"]
    s2f, q, c = prm["s2f"], prm["q"], prm["c"]
    big = 1e6
    p = p.sort_values(["tour", "player_id", "tdate", "tournament_id", "round_order"], kind="mergesort")
    groups = {k: g for k, g in p.groupby(["tour", "player_id"], sort=False)}
    res = np.full((len(targets), 5), np.nan)
    tg = targets.reset_index(drop=True)

    def step(st, day):
        L, f, P11, P12, P22, d0 = st
        dt = max(day - d0, 0.0) if d0 is not None else 0.0
        ph = math.exp(-lam * dt)
        return [L, f * ph, P11 + q * dt, P12 * ph, P22 * ph * ph + s2f * (1 - ph * ph), day]

    def update(st, z, R):
        L, f, P11, P12, P22, d = st
        v = z - L - f
        S = P11 + 2 * P12 + P22 + R
        sd = math.sqrt(S)
        if abs(v) > c * sd:
            v = math.copysign(c * sd, v)
        K1, K2 = (P11 + P12) / S, (P12 + P22) / S
        return [L + K1 * v, f + K2 * v, P11 - K1 * K1 * S, P12 - K1 * K2 * S, P22 - K2 * K2 * S, d]

    init = [0.0, 0.0, big, 0.0, s2f, None]
    for key, t in tg.groupby(["tour", "player_id"], sort=False):
        g = groups.get(key)
        tidx = t.index.to_numpy()
        if g is None:
            res[tidx, 0], res[tidx, 1], res[tidx, 4] = 0.0, math.sqrt(s2f), 0
            continue
        td, tid, ro = g["tdate"].to_numpy(), g["tournament_id"].to_numpy(), g["round_order"].to_numpy()
        ob, z, R = g["obs"].to_numpy(), g["z"].to_numpy(), g["R"].to_numpy()
        # sequential pass: state after each row
        states, st = [], list(init)
        for k in range(len(g)):
            st = update(step(st, ob[k]) if st[5] is not None else [st[0], st[1], st[2], st[3], st[4], ob[k]], z[k], R[k])
            states.append(st)
        for i, (ttd, ttid, tro, tob) in zip(tidx, t[["tdate", "tournament_id", "round_order", "obs"]].itertuples(index=False)):
            j = int(np.searchsorted(td, ttd, side="left")) - 1        # last row with tdate < target's
            st = list(states[j]) if j >= 0 else list(init)
            same = np.flatnonzero((tid == ttid) & (ro < tro) & (td == ttd))
            nh = j + 1 + len(same)
            for k in same:
                st = update(step(st, ob[k]) if st[5] is not None else [st[0], st[1], st[2], st[3], st[4], ob[k]], z[k], R[k])
            if st[5] is None:
                res[i] = (0.0, math.sqrt(s2f), np.nan, np.nan, 0)
                continue
            st = step(st, tob)
            res[i] = (st[1], math.sqrt(max(st[4], 0.0)), st[0] if st[2] < big / 10 else np.nan,
                      math.sqrt(max(st[2], 0.0)), nh)
    return pd.DataFrame(res, columns=["f_hat", "f_sd", "L_hat", "L_sd", "hist"], index=targets.index)


# ------------------------------------------------------------------------------------------------ scoring
def r2_oos(F_tune, d_tune, F_eval, d_eval) -> tuple[float, float, float]:
    b = float((F_tune * d_tune).sum() / max((F_tune * F_tune).sum(), 1e-12))
    sse = ((d_eval - b * F_eval) ** 2).sum()
    return 1 - sse / (d_eval ** 2).sum(), b, float(np.corrcoef(F_eval, d_eval)[0, 1]) if F_eval.std() > 0 else 0.0


def block_ci(F, d, b, blocks, n_boot=400, seed=0) -> tuple[float, float]:
    """95% block-bootstrap interval of R2_oos at a fixed slope (blocks: 28-day blocks of the target day)."""
    rng = np.random.default_rng(seed)
    ub = np.unique(blocks)
    ix = {u: np.flatnonzero(blocks == u) for u in ub}
    vals = []
    for _ in range(n_boot):
        s = np.concatenate([ix[u] for u in rng.choice(ub, len(ub))])
        vals.append(1 - ((d[s] - b * F[s]) ** 2).sum() / (d[s] ** 2).sum())
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def diff_ci(Fa, Fb, d, ba, bb, blocks, n_boot=400, seed=1) -> tuple[float, float, float]:
    """R2_oos(a) - R2_oos(b) with a 95% block-bootstrap interval (positive = a better)."""
    rng = np.random.default_rng(seed)
    ub = np.unique(blocks)
    ix = {u: np.flatnonzero(blocks == u) for u in ub}

    def r2(F, b, s):
        return 1 - ((d[s] - b * F[s]) ** 2).sum() / (d[s] ** 2).sum()

    alls = np.arange(len(d))
    est = r2(Fa, ba, alls) - r2(Fb, bb, alls)
    vals = []
    for _ in range(n_boot):
        s = np.concatenate([ix[u] for u in rng.choice(ub, len(ub))])
        vals.append(r2(Fa, ba, s) - r2(Fb, bb, s))
    return float(est), float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def main() -> None:
    policy = sys.argv[1] if len(sys.argv) > 1 else "ks_first"
    M.log(f"panel {policy}, seasons <= {LAST}")
    p0 = M.panel(policy)
    p0 = p0[p0["year"] <= LAST].copy()
    results = {"policy": policy, "seasons": f"<= {LAST}", "split": SPLIT, "tours": {}}
    for tour in ("atp", "wta"):
        tune_last, eval_first = SPLIT[tour]
        pt = p0[p0["tour"] == tour].copy()
        off = offsets(pt, tune_last)
        nu = {"pm": 7.0, "ks": 10.0}
        p = centre(pt, off, nu)
        n0 = S2[tour] / nu["pm"]
        M.log(f"{tour}: {len(p)} timed rows; offsets (<= {tune_last}) "
              f"{ {k: (round(v, 2) if isinstance(v, float) else v) for k, v in off[tour].items()} }")
        w = window_stats(p, n0)
        w["d"] = w["z"] - w["c52"]
        w["x_raw"] = w["m2"] - w["m52"]
        w["x_cen"] = w["c2"] - w["c52"]
        w["block"] = (w["obs"] // 28).astype(int)
        has = w["c52"].notna()
        clean = has & (w["d"].abs() <= 20) & (w["n"] >= 15)
        tune = clean & (w["year"] <= tune_last)
        ev = clean & (w["year"] >= eval_first)
        R = {"offsets": off[tour], "targets_tune": int(tune.sum()), "targets_eval": int(ev.sum()), "candidates": {}}
        d_t, d_e = w.loc[tune, "d"].to_numpy(), w.loc[ev, "d"].to_numpy()
        bl = w.loc[ev, "block"].to_numpy()
        feats = {}

        def add(name, F):
            F = np.nan_to_num(np.asarray(F, dtype=float), nan=0.0)
            feats[name] = F
            r2, b, cr = r2_oos(F[tune.to_numpy()], d_t, F[ev.to_numpy()], d_e)
            lo, hi = block_ci(F[ev.to_numpy()], d_e, b, bl)
            R["candidates"][name] = {"r2_oos": r2, "ci": [lo, hi], "slope": b, "corr": cr,
                                     "coverage_eval": float((F[ev.to_numpy()] != 0).mean())}
            M.log(f"  {name:28s} R2_oos {r2:+.4f} [{lo:+.4f}, {hi:+.4f}] slope {b:.3f} corr {cr:.3f}")

        add("a_x_raw", w["x_raw"])
        add("a_x_cen", w["x_cen"])
        # (b) EB shrinkage by precision: grid on tau2 and nu
        best = None
        for tau2 in (2, 4, 6, 8, 12, 16, 24):
            for nub in (4, 8, 12, 16):
                V = nub / w["k2"].clip(lower=1) + S2[tour] / w["N2"].clip(lower=1)
                F = (w["x_cen"] * tau2 / (tau2 + V)).fillna(0).to_numpy()
                r2, b, _ = r2_oos(F[tune.to_numpy()], d_t, F[tune.to_numpy()], d_t)
                if best is None or r2 > best[0]:
                    best = (r2, tau2, nub)
        R["eb_tuned"] = {"tau2": best[1], "nu": best[2], "r2_tune": best[0]}
        V = best[2] / w["k2"].clip(lower=1) + S2[tour] / w["N2"].clip(lower=1)
        add("b_x_eb", w["x_cen"] * best[1] / (best[1] + V))
        # (c) exponentially weighted, shrunk: grid on half-life and K
        best = None
        for h in HALF_LIVES:
            for K in (0.0, 0.25, 0.5, 1.0, 2.0, 4.0):
                F = (w[f"ewn_{h}"] / (w[f"ewd_{h}"] + K)).fillna(0).to_numpy()
                r2, b, _ = r2_oos(F[tune.to_numpy()], d_t, F[tune.to_numpy()], d_t)
                if best is None or r2 > best[0]:
                    best = (r2, h, K)
        R["ew_tuned"] = {"half_life_days": best[1], "K": best[2], "r2_tune": best[0]}
        add("c_x_ew", w[f"ewn_{best[1]}"] / (w[f"ewd_{best[1]}"] + best[2]))
        # (d) Kalman: coordinate search on the tuning seasons, criterion = one-step-ahead MSE of the target match's
        # centred speed z_m by L_hat + f_hat (the brief's "next-match first-serve speed")
        tgt = w[["tour", "player_id", "tdate", "tournament_id", "round_order", "obs"]]
        prm = {"hl": 10.0, "s2f": 8.0, "q": 2.0 / 365, "c": 2.5}
        nu_k = dict(nu)
        tn = tune.to_numpy()
        z_t = w.loc[tune, "z"].to_numpy()

        def score(prm_, nu_):
            pp = centre(pt, off, nu_)
            kf = kalman(pp, tgt, prm_)
            pred = (kf["L_hat"] + kf["f_hat"]).to_numpy()[tn]
            return -float(np.nanmean((z_t - pred) ** 2)), kf

        cur, kf = score(prm, nu_k)
        grids = {"hl": [3, 5, 7, 10, 14, 20, 28, 40, 60, 90, 120], "s2f": [1, 2, 4, 8, 12, 18, 26, 36],
                 "q": [0.0, 1 / 365, 2 / 365, 4 / 365, 8 / 365, 16 / 365, 32 / 365],
                 "c": [1.5, 2.0, 2.5, 3.0, 4.0, 10.0], "nu_pm": [2, 3, 5, 7, 10, 14, 20, 28],
                 "nu_ks": [3, 5, 8, 10, 14, 20]}
        for sweep in range(3):
            before = cur
            for k, vals in grids.items():
                for v in vals:
                    pr, nv = dict(prm), dict(nu_k)
                    if k == "nu_pm":
                        nv["pm"] = v
                    elif k == "nu_ks":
                        nv["ks"] = v
                    else:
                        pr[k] = v
                    s, _ = score(pr, nv)
                    if s > cur + 1e-6:
                        cur, prm, nu_k = s, pr, nv
            M.log(f"  kalman sweep {sweep}: one-step MSE (tune) {-cur:.3f} prm {prm} nu {nu_k}")
            if cur <= before + 1e-6:
                break
        R["kalman_tuned"] = {"params": prm, "nu": nu_k, "one_step_mse_tune": -cur, "q_per_year": prm["q"] * 365,
                             "half_life_days": prm["hl"]}
        pp = centre(pt, off, nu_k)
        kf = kalman(pp, tgt, prm)
        w = w.join(kf)
        add("d_f_hat", w["f_hat"])
        add("d_dev_hat", (w["L_hat"] + w["f_hat"] - w["c52"]))
        # level forecasts (Kalman's own long-run level vs the 364-day mean) on the evaluation seasons
        e = w[ev]
        R["level_forecast_eval"] = {
            "mse_m52": float(((e["z"] - e["c52"]) ** 2).mean()),
            "mse_L_hat": float(((e["z"] - e["L_hat"]) ** 2).mean()),
            "mse_L_plus_f": float(((e["z"] - e["L_hat"] - e["f_hat"]) ** 2).mean()),
            "mse_m52_plus_b_xraw": float(((e["d"] - R["candidates"]["a_x_raw"]["slope"] * e["x_raw"].fillna(0)) ** 2).mean()),
            "mse_m52_plus_b_xew": float(((e["d"] - feats["c_x_ew"][ev.to_numpy()] * R["candidates"]["c_x_ew"]["slope"]) ** 2).mean())}
        # paired difference with a 28-day-block interval: MSE(364-day mean + b x_raw) - MSE(L_hat + f_hat);
        # positive = the Kalman forecast better
        se_x = (e["d"] - R["candidates"]["a_x_raw"]["slope"] * e["x_raw"].fillna(0)).to_numpy() ** 2
        se_k = (e["z"] - e["L_hat"] - e["f_hat"]).to_numpy() ** 2
        okk = ~np.isnan(se_k)
        rng = np.random.default_rng(3)
        blk = e["block"].to_numpy()[okk]
        ub = np.unique(blk)
        ix = {u: np.flatnonzero(blk == u) for u in ub}
        dd_ = (se_x - se_k)[okk]
        bs = [dd_[np.concatenate([ix[u] for u in rng.choice(ub, len(ub))])].mean() for _ in range(400)]
        R["level_forecast_eval"]["xraw_minus_kalman"] = {"mse_diff": float(dd_.mean()),
                                                         "ci": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                                                         "rows": int(okk.sum())}
        # pairwise differences against the registered statistic (positive = the candidate better)
        R["vs_x_raw"] = {}
        ev_ = ev.to_numpy()
        for name in ("a_x_cen", "b_x_eb", "c_x_ew", "d_f_hat", "d_dev_hat"):
            est, lo, hi = diff_ci(feats[name][ev_], feats["a_x_raw"][ev_], d_e, R["candidates"][name]["slope"],
                                  R["candidates"]["a_x_raw"]["slope"], bl)
            R["vs_x_raw"][name] = {"r2_diff": est, "ci": [lo, hi]}
        # by history situation: where x_raw exists (k2 >= 1) and where it does not
        sub = {}
        for lab, m in (("x_raw_present", ev & w["k2"].ge(1)), ("x_raw_missing", ev & w["k2"].eq(0))):
            mm = m.to_numpy()
            sub[lab] = {"rows": int(mm.sum())}
            for name in ("a_x_raw", "b_x_eb", "c_x_ew", "d_f_hat", "d_dev_hat"):
                F, d = feats[name][mm], w.loc[m, "d"].to_numpy()
                b = R["candidates"][name]["slope"]
                sub[lab][name] = {"r2_oos": float(1 - ((d - b * F) ** 2).sum() / (d ** 2).sum()),
                                  "corr": float(np.corrcoef(F, d)[0, 1]) if F.std() > 0 else 0.0}
        R["by_situation"] = sub
        # match level: both players timed in the target match, both with a 364-day history
        mm = w[ev][["match_id", "side", "d"]].assign(**{k: feats[k][ev_] for k in feats})
        a, b_ = mm[mm["side"] == "A"].set_index("match_id"), mm[mm["side"] == "B"].set_index("match_id")
        j = a.join(b_, lsuffix="_A", rsuffix="_B", how="inner")
        R["match_level"] = {"matches": int(len(j))}
        dd = (j["d_A"] - j["d_B"]).to_numpy()
        for name in feats:
            F = (j[f"{name}_A"] - j[f"{name}_B"]).to_numpy()
            R["match_level"][name] = {"corr": float(np.corrcoef(F, dd)[0, 1]) if F.std() > 0 else 0.0}
        # correlations among candidates on the evaluation rows where x_raw exists (feature-only)
        pres = ev_ & w["k2"].ge(1).to_numpy()
        R["corr_with_x_raw_where_present"] = {k: float(np.corrcoef(feats[k][pres], feats["a_x_raw"][pres])[0, 1])
                                              for k in feats}
        # posterior SD summary and the decay of f_hat with the gap since the last timed match (feature-only)
        e = w[ev]
        gap = pd.cut(e["last_age"], [-1, 3, 7, 14, 28, 56, 364])
        R["f_sd_by_gap"] = e.groupby(gap, observed=True)["f_sd"].median().round(3).astype(float).to_dict()
        R["f_abs_by_gap"] = e.groupby(gap, observed=True)["f_hat"].apply(lambda s: s.abs().mean()).round(3).astype(float).to_dict()
        R["f_sd_by_gap"] = {str(k): v for k, v in R["f_sd_by_gap"].items()}
        R["f_abs_by_gap"] = {str(k): v for k, v in R["f_abs_by_gap"].items()}
        results["tours"][tour] = R
        w.to_parquet(M.OUT / f"modeller_state_rows_{policy}_{tour}.parquet")
    (M.OUT / f"modeller_state_{policy}.json").write_text(json.dumps(results, indent=1, default=float) + "\n",
                                                         encoding="utf-8")
    M.log("done")


if __name__ == "__main__":
    main()
