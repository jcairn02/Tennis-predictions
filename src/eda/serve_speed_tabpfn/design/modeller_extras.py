"""Design scratch (agent 2): two diagnostics for the state model, men, key-statistic-first panel, seasons <= 2023.
No match result is read.

A. The level prior of a CHANGE feature. The Kalman filter is run with (i) a diffuse level prior (the proposal), (ii) the
   population prior (tour mean, between-player variance 8.8^2), (iii) a height prior (tour mean + slope x height,
   residual variance). For targets whose player has at most two timed matches of history ("newcomers"), the share of
   f_hat explained by the player's level (corr with his career mean of centred speed, a speed statistic) shows whether
   the prior leaks the level into the change feature.

B. Edition centring (an oracle upper bound). Each edition's shared shift is estimated as the shrunk mean one-step
   residual of all its players (all of the edition's matches, so NOT leak-proof: an upper bound of what a leak-proof
   clock version could gain). History speeds are centred on it, the target is not; R2_oos of the 2023 targets'
   deviation and the match-level correlation are compared with the uncentred filter.

Run: ./python.sh src/eda/serve_speed_tabpfn/design/modeller_extras.py
Writes data/studies/serve_speed_tabpfn/design/modeller_extras.json
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
from src.eda.serve_speed_tabpfn.design import modeller_state as S  # noqa: E402

POLICY = "ks_first"


def kalman_prior(p: pd.DataFrame, targets: pd.DataFrame, prm: dict, L0: dict | float, P0: dict | float) -> pd.DataFrame:
    """modeller_state.kalman with a per-player level prior (mean L0, variance P0)."""
    lam = math.log(2) / prm["hl"]
    s2f, q, c = prm["s2f"], prm["q"], prm["c"]
    p = p.sort_values(["tour", "player_id", "tdate", "tournament_id", "round_order"], kind="mergesort")
    groups = {k: g for k, g in p.groupby("player_id", sort=False)}
    res = np.full((len(targets), 3), np.nan)
    tg = targets.reset_index(drop=True)

    def step(st, day):
        L, f, P11, P12, P22, d0 = st
        dt = max(day - d0, 0.0)
        ph = math.exp(-lam * dt)
        return [L, f * ph, P11 + q * dt, P12 * ph, P22 * ph * ph + s2f * (1 - ph * ph), day]

    def update(st, z, R):
        L, f, P11, P12, P22, d = st
        v = z - L - f
        S_ = P11 + 2 * P12 + P22 + R
        sd = math.sqrt(S_)
        if abs(v) > c * sd:
            v = math.copysign(c * sd, v)
        K1, K2 = (P11 + P12) / S_, (P12 + P22) / S_
        return [L + K1 * v, f + K2 * v, P11 - K1 * K1 * S_, P12 - K1 * K2 * S_, P22 - K2 * K2 * S_, d]

    for pid, t in tg.groupby("player_id", sort=False):
        g = groups.get(pid)
        tidx = t.index.to_numpy()
        l0 = L0[pid] if isinstance(L0, dict) else L0
        p0 = P0[pid] if isinstance(P0, dict) else P0
        if g is None:
            res[tidx] = (0.0, l0, 0)
            continue
        td, tid, ro = g["tdate"].to_numpy(), g["tournament_id"].to_numpy(), g["round_order"].to_numpy()
        ob, z, R = g["obs"].to_numpy(), g["z"].to_numpy(), g["R"].to_numpy()
        init = [l0, 0.0, p0, 0.0, s2f, ob[0]]
        states, st = [], list(init)
        for k in range(len(g)):
            st = update(step(st, ob[k]), z[k], R[k])
            states.append(st)
        for i, (ttd, ttid, tro, tob) in zip(tidx, t[["tdate", "tournament_id", "round_order", "obs"]].itertuples(index=False)):
            j = int(np.searchsorted(td, ttd, side="left")) - 1
            st = list(states[j]) if j >= 0 else list(init)
            same = np.flatnonzero((tid == ttid) & (ro < tro) & (td == ttd))
            for k in same:
                st = update(step(st, ob[k]), z[k], R[k])
            nh = j + 1 + len(same)
            st = step(st, max(tob, st[5]))
            res[i] = (st[1], st[0], nh)
    return pd.DataFrame(res, columns=["f_hat", "L_hat", "hist"], index=targets.index)


def main() -> None:
    st = json.loads((M.OUT / f"modeller_state_{POLICY}.json").read_text(encoding="utf-8"))["tours"]["atp"]
    prm, nu = st["kalman_tuned"]["params"], st["kalman_tuned"]["nu"]
    p = M.panel(POLICY)
    p = p[(p["tour"] == "atp") & (p["year"] <= 2023)].copy()
    off = S.offsets(p, 2022)
    p = S.centre(p, off, nu)
    tg = p[p["year"].between(2022, 2023)][["tour", "player_id", "tdate", "tournament_id", "round_order", "obs",
                                           "match_id", "side", "z", "year"]].copy()
    out = {"policy": POLICY, "kalman": prm, "nu": nu}

    # ---------------- A. level priors
    early = p[p["year"] <= 2022]
    mu = float(np.average(early["z"], weights=early["n"]))
    mp = pd.read_parquet(M.PD.MATCH_PLAYERS, columns=["player_id", "height"])
    h = mp[(mp["height"] >= 150) & (mp["height"] <= 215)].groupby("player_id")["height"].median()
    lv = early.groupby("player_id").apply(lambda x: np.average(x["z"], weights=x["n"]), include_groups=False)
    hh = pd.concat([lv.rename("lv"), h], axis=1, join="inner")
    slope, icpt = np.polyfit(hh["height"], hh["lv"], 1)
    resid_var = float(np.var(hh["lv"] - (icpt + slope * hh["height"])))
    tau2 = 8.8 ** 2
    players = tg["player_id"].unique()
    pri = {"diffuse": (0.0, 1e6), "population": (mu, tau2)}
    L0h = {pid: (icpt + slope * h[pid]) if pid in h.index else mu for pid in players}
    P0h = {pid: resid_var if pid in h.index else tau2 for pid in players}
    career = p.groupby("player_id").apply(lambda x: np.average(x["z"], weights=x["n"]), include_groups=False)
    resA = {"height_slope_kmh_per_cm": float(slope), "height_resid_sd": math.sqrt(resid_var),
            "population_mean": mu}
    for name, (l0, p0) in list(pri.items()) + [("height", (L0h, P0h))]:
        kf = kalman_prior(p, tg, prm, l0, p0)
        x = tg.join(kf)
        x["career"] = x["player_id"].map(career)
        new = x[(x["hist"] >= 1) & (x["hist"] <= 2)]
        rest = x[x["hist"] > 2]
        resA[name] = {"newcomer_rows": int(len(new)),
                      "newcomer_sd_f_hat": float(new["f_hat"].std()),
                      "newcomer_corr_f_hat_career_level": float(np.corrcoef(new["f_hat"], new["career"])[0, 1]),
                      "established_corr_f_hat_career_level": float(np.corrcoef(rest["f_hat"], rest["career"])[0, 1]),
                      "established_sd_f_hat": float(rest["f_hat"].std())}
        M.log(f"prior {name}: {resA[name]}")
    out["A_level_prior"] = resA

    # ---------------- B. edition centring (oracle upper bound)
    allt = p[["tour", "player_id", "tdate", "tournament_id", "round_order", "obs"]]
    kf = S.kalman(p, allt, prm)
    resid = p["z"] - kf["L_hat"] - kf["f_hat"]
    ed = pd.DataFrame({"tid": p["tournament_id"], "r": resid}).dropna().groupby("tid")["r"].agg(["mean", "size"])
    ed["e"] = ed["mean"] * ed["size"] / (ed["size"] + 10.0)
    out["B_edition"] = {"editions": int(len(ed)), "sd_shrunk_edition_shift": float(ed["e"].std()),
                        "sd_raw_edition_mean": float(ed["mean"].std())}
    pc = p.copy()
    pc["z"] = pc["z"] - pc["tournament_id"].map(ed["e"]).fillna(0.0)
    sw = M.OUT / f"modeller_state_rows_{POLICY}_atp.parquet"
    w = pd.read_parquet(sw)
    ev = (w["c52"].notna() & (w["d"].abs() <= 20) & (w["n"] >= 15) & (w["year"] >= 2023)).to_numpy()
    tune = (w["c52"].notna() & (w["d"].abs() <= 20) & (w["n"] >= 15) & (w["year"] <= 2022)).to_numpy()
    tgt = w[["tour", "player_id", "tdate", "tournament_id", "round_order", "obs"]]
    base = S.kalman(p, tgt, prm)["f_hat"].fillna(0).to_numpy()
    cent = S.kalman(pc, tgt, prm)["f_hat"].fillna(0).to_numpy()
    d = w["d"].to_numpy()
    for name, F in (("uncentred", base), ("edition_centred_oracle", cent)):
        r2, b, cr = S.r2_oos(F[tune], d[tune], F[ev], d[ev])
        mm = w.loc[ev, ["match_id", "side", "d"]].assign(F=F[ev])
        a, bb = mm[mm["side"] == "A"].set_index("match_id"), mm[mm["side"] == "B"].set_index("match_id")
        j = a.join(bb, lsuffix="_A", rsuffix="_B", how="inner")
        out["B_edition"][name] = {"r2_oos": r2, "slope": b, "corr": cr,
                                  "match_corr": float(np.corrcoef(j["F_A"] - j["F_B"], j["d_A"] - j["d_B"])[0, 1]),
                                  "matches": int(len(j))}
        M.log(f"edition {name}: {out['B_edition'][name]}")
    # ---------------- C. calibration across reliability strata (2023 targets; slope through the origin of the
    # target's deviation d on the feature, per stratum; a calibrated posterior mean has slope ~1 in every stratum)
    w["f_hat_k"] = S.kalman(p, tgt, prm)["f_hat"].to_numpy()
    e = w[ev].copy()
    e["x_raw0"] = e["x_raw"].fillna(0.0)
    strata = {"k2=0": e["k2"].eq(0), "k2=1": e["k2"].eq(1), "k2=2": e["k2"].eq(2), "k2>=3": e["k2"].ge(3)}
    cal = {}
    for lab, m in strata.items():
        g = e[m]
        row = {"rows": int(len(g))}
        for col in ("f_hat_k", "x_raw0"):
            F, d_ = g[col].to_numpy(), g["d"].to_numpy()
            if (F * F).sum() > 0:
                row[col] = {"slope": float((F * d_).sum() / (F * F).sum()), "sd": float(F.std())}
        cal[lab] = row
    out["C_calibration_by_k2"] = cal
    M.log(f"calibration: {cal}")
    (M.OUT / "modeller_extras.json").write_text(json.dumps(out, indent=1, default=float) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
