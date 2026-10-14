"""Design scratch (agent 2): a three-state variant of the speed-state filter, men, seasons <= 2023, no result read.

Why: in the two-state filter (modeller_state.py) the 2023 calibration slope of the target's deviation on f_hat is 0.31
for players with no timed match in the last 14 days but 0.69-0.85 with recent matches (modeller_extras.json, C):
persistence within an event looks stronger than across events. The variant adds an event component g:

    z_m = L(t) + f(t) + g[player, event] + eps_m
    g ~ N(0, s2g), drawn afresh at each new event (tournament_id) and constant within it; L, f, eps as before.

Target features: dev3 = E[f + g] (the predicted deviation in this match from the level; g's posterior is non-zero only
for later rounds of the same event) and f3 = E[f] (the cross-event state). Tuned by one-step-ahead MSE of z_m on
seasons <= 2022 (hl, s2f, s2g, c; q and the noise as in the two-state filter); evaluated on 2023 as modeller_state.py
does (R2_oos with a slope fitted on the tuning seasons; calibration slope by k2; match-level correlation).

Run: ./python.sh src/eda/serve_speed_tabpfn/design/modeller_state3.py [ks_first|pm_first]
Writes data/studies/serve_speed_tabpfn/design/modeller_state3_<policy>.json
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


def kalman3(p: pd.DataFrame, targets: pd.DataFrame, prm: dict) -> pd.DataFrame:
    lam = math.log(2) / prm["hl"]
    s2f, s2g, q, c = prm["s2f"], prm["s2g"], prm["q"], prm["c"]
    big = 1e6
    p = p.sort_values(["tour", "player_id", "tdate", "tournament_id", "round_order"], kind="mergesort")
    groups = {k: g for k, g in p.groupby(["tour", "player_id"], sort=False)}
    res = np.full((len(targets), 4), np.nan)
    tg = targets.reset_index(drop=True)
    # state: [L, f, g, PLL, PLf, PLg, Pff, Pfg, Pgg, day, event]

    def step(st, day, event):
        L, f, g, PLL, PLf, PLg, Pff, Pfg, Pgg, d0, ev = st
        dt = max(day - d0, 0.0) if d0 is not None else 0.0
        ph = math.exp(-lam * dt)
        PLL, PLf, Pfg = PLL + q * dt, PLf * ph, Pfg * ph
        Pff = Pff * ph * ph + s2f * (1 - ph * ph)
        f = f * ph
        if event != ev:                      # a new event: the event component is drawn afresh
            g, PLg, Pfg, Pgg = 0.0, 0.0, 0.0, s2g
        return [L, f, g, PLL, PLf, PLg, Pff, Pfg, Pgg, day, event]

    def update(st, z, R):
        L, f, g, PLL, PLf, PLg, Pff, Pfg, Pgg, d, ev = st
        a1, a2, a3 = PLL + PLf + PLg, PLf + Pff + Pfg, PLg + Pfg + Pgg      # P H'
        S_ = a1 + a2 + a3 + R
        v = z - L - f - g
        sd = math.sqrt(S_)
        if abs(v) > c * sd:
            v = math.copysign(c * sd, v)
        k1, k2, k3 = a1 / S_, a2 / S_, a3 / S_
        return [L + k1 * v, f + k2 * v, g + k3 * v,
                PLL - k1 * k1 * S_, PLf - k1 * k2 * S_, PLg - k1 * k3 * S_,
                Pff - k2 * k2 * S_, Pfg - k2 * k3 * S_, Pgg - k3 * k3 * S_, d, ev]

    init = [0.0, 0.0, 0.0, big, 0.0, 0.0, s2f, 0.0, s2g, None, None]
    for key, t in tg.groupby(["tour", "player_id"], sort=False):
        gg = groups.get(key)
        tidx = t.index.to_numpy()
        if gg is None:
            res[tidx] = (0.0, 0.0, np.nan, 0)
            continue
        td, tid, ro = gg["tdate"].to_numpy(), gg["tournament_id"].to_numpy(), gg["round_order"].to_numpy()
        ob, z, R = gg["obs"].to_numpy(), gg["z"].to_numpy(), gg["R"].to_numpy()
        states, st = [], list(init)
        for k in range(len(gg)):
            st = update(step(st, ob[k], tid[k]), z[k], R[k])
            states.append(st)
        for i, (ttd, ttid, tro, tob) in zip(tidx, t[["tdate", "tournament_id", "round_order", "obs"]].itertuples(index=False)):
            j = int(np.searchsorted(td, ttd, side="left")) - 1
            st = list(states[j]) if j >= 0 else list(init)
            same = np.flatnonzero((tid == ttid) & (ro < tro) & (td == ttd))
            for k in same:
                st = update(step(st, ob[k], tid[k]), z[k], R[k])
            if st[9] is None:
                res[i] = (0.0, 0.0, np.nan, 0)
                continue
            st = step(st, tob, ttid)
            res[i] = (st[1] + st[2], st[1], st[0] if st[3] < big / 10 else np.nan, j + 1 + len(same))
    return pd.DataFrame(res, columns=["dev3", "f3", "L3", "hist3"], index=targets.index)


def main() -> None:
    policy = sys.argv[1] if len(sys.argv) > 1 else "ks_first"
    st = json.loads((M.OUT / f"modeller_state_{policy}.json").read_text(encoding="utf-8"))["tours"]["atp"]
    base, nu = st["kalman_tuned"]["params"], st["kalman_tuned"]["nu"]
    p = M.panel(policy)
    p = p[(p["tour"] == "atp") & (p["year"] <= 2023)].copy()
    p = S.centre(p, S.offsets(p, 2022), nu)
    w = pd.read_parquet(M.OUT / f"modeller_state_rows_{policy}_atp.parquet")
    clean = w["c52"].notna() & (w["d"].abs() <= 20) & (w["n"] >= 15)
    tune, ev = (clean & (w["year"] <= 2022)).to_numpy(), (clean & (w["year"] >= 2023)).to_numpy()
    tgt = w[["tour", "player_id", "tdate", "tournament_id", "round_order", "obs"]]
    z = w["z"].to_numpy()

    def score(prm):
        kf = kalman3(p, tgt, prm)
        pred = (kf["L3"] + kf["dev3"]).to_numpy()
        return -float(np.nanmean((z[tune] - pred[tune]) ** 2)), kf

    prm = {"hl": base["hl"], "s2f": base["s2f"], "s2g": 4.0, "q": base["q"], "c": base["c"]}
    cur, _ = score(prm)
    grids = {"s2g": [0.0, 2, 4, 8, 12, 18], "hl": [7, 10, 14, 20, 28, 40, 60], "s2f": [4, 8, 12, 18, 26],
             "c": [1.5, 2.0, 2.5, 3.0]}
    for sweep in range(3):
        before = cur
        for k, vals in grids.items():
            for v in vals:
                pr = dict(prm)
                pr[k] = v
                s, _ = score(pr)
                if s > cur + 1e-6:
                    cur, prm = s, pr
        M.log(f"sweep {sweep}: one-step MSE (tune) {-cur:.3f} {prm}")
        if cur <= before + 1e-6:
            break
    s2, _ = score(dict(prm, s2g=0.0))
    kf = kalman3(p, tgt, prm)
    w = w.join(kf)
    d = w["d"].to_numpy()
    out = {"policy": policy, "params": prm, "one_step_mse_tune": -cur, "one_step_mse_tune_two_state_equiv": -s2,
           "two_state_one_step_mse_tune": st["kalman_tuned"]["one_step_mse_tune"], "eval": {}}
    e = w[ev]
    out["eval"]["mse_level_forecast_3state"] = float(((e["z"] - e["L3"] - e["dev3"]) ** 2).mean())
    out["eval"]["mse_level_forecast_2state"] = float(((e["z"] - e["L_hat"] - e["f_hat"]) ** 2).mean())
    for name in ("dev3", "f3", "f_hat"):
        F = w[name].fillna(0).to_numpy()
        r2, b, cr = S.r2_oos(F[tune], d[tune], F[ev], d[ev])
        mm = w.loc[ev, ["match_id", "side", "d"]].assign(F=F[ev])
        a, bb = mm[mm["side"] == "A"].set_index("match_id"), mm[mm["side"] == "B"].set_index("match_id")
        j = a.join(bb, lsuffix="_A", rsuffix="_B", how="inner")
        cal = {}
        for lab, m in (("k2=0", e["k2"].eq(0)), ("k2=1", e["k2"].eq(1)), ("k2=2", e["k2"].eq(2)), ("k2>=3", e["k2"].ge(3))):
            Fm, dm = F[ev][m.to_numpy()], d[ev][m.to_numpy()]
            cal[lab] = float((Fm * dm).sum() / max((Fm * Fm).sum(), 1e-12))
        out["eval"][name] = {"r2_oos": r2, "slope_tune": b, "corr": cr,
                             "match_corr": float(np.corrcoef(j["F_A"] - j["F_B"], j["d_A"] - j["d_B"])[0, 1]),
                             "calibration_slope_by_k2_eval": cal}
        M.log(f"{name}: {out['eval'][name]}")
    (M.OUT / f"modeller_state3_{policy}.json").write_text(json.dumps(out, indent=1, default=float) + "\n",
                                                          encoding="utf-8")


if __name__ == "__main__":
    main()
