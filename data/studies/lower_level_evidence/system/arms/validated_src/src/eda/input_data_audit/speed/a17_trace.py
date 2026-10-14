"""Audit step 17: step-by-step trace of the 28-day filter for single targets (the project's history, snapshot gammas and
filter equations; scenario A), to show how one broken row moves f_hat. Read-only."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 200)
from src.eda.serve_speed_tabpfn import features as F  # noqa: E402
from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402
from src.eda.serve_speed_tabpfn.latency import features_latency as FL  # noqa: E402

p = FL.load_panel()
keys = P.load_frame_keys()
t = F.side_targets(keys)
S = FL.Scenario("A", p, None, None)
PRM = dict(FL.MEN, hl=28.0)


def trace(match_id: str, side: str):
    tg = t[(t["match_id"] == match_id) & (t["side"] == side)].reset_index(drop=True)
    hist = FL.histories_rel(p, tg, None)
    idx = hist["idx"][0]
    idx = idx[idx >= 0]
    G = F.snapshot_gammas(p, tg, hist["idx"], S.offsets)[0][: len(idx)]
    rows = p.iloc[idx]
    y, n, obs = rows["y"].to_numpy(float), rows["n"].to_numpy(float), rows["obs"].to_numpy(float)
    ks = rows["basis"].astype(str).eq("ks").to_numpy()
    R = np.where(ks, PRM["nu_ks"], PRM["nu_pts"]) + PRM["sigma"] ** 2 / n
    z = y - G
    lam = math.log(2.0) / PRM["hl"]
    s2f, q, c = PRM["s2f"], PRM["q"], PRM["c"]
    L = f = 0.0
    P11, P12, P22 = F.BIG, 0.0, s2f
    last = None
    out = []
    for k in range(len(idx)):
        dt_ = 0.0 if last is None else max(obs[k] - last, 0.0)
        phi = math.exp(-lam * dt_)
        fp = f * phi
        P11p, P12p, P22p = P11 + q * dt_, P12 * phi, P22 * phi * phi + s2f * (1 - phi * phi)
        v = z[k] - L - fp
        Sk = P11p + 2 * P12p + P22p + R[k]
        cs = c * math.sqrt(Sk)
        vc = min(max(v, -cs), cs)
        K1, K2 = (P11p + P12p) / Sk, (P12p + P22p) / Sk
        L, f = L + K1 * vc, fp + K2 * vc
        P11, P12, P22 = P11p - K1 * K1 * Sk, P12p - K1 * K2 * Sk, P22p - K2 * K2 * Sk
        last = obs[k]
        out.append({"date": str(pd.Timestamp(obs[k], unit="D").date()), "event": rows["tournament_name"].iloc[k],
                    "rnd": rows["round"].iloc[k], "src": rows["source"].iloc[k], "y": y[k], "n": int(n[k]),
                    "gamma": G[k], "z": z[k], "innov": v, "clip": cs, "L": L, "f": f})
    d = tg["es"].iloc[0] - last
    fh = f * math.exp(-lam * d)
    res = pd.DataFrame(out)
    print(f"\n=== {match_id} side {side} (player {tg['player_id'].iloc[0]}), es {pd.Timestamp(tg['es'].iloc[0], unit='D').date()}"
          f": f_hat {fh:.2f} km/h")
    print(res.round(2).to_string(index=False))


trace("atp|2025-540|R64|atp:208103|atp:208233", "B")
trace("atp|2024-496|R32|atp:126409|atp:200624", "B")
trace("atp|2025-580|R64|atp:126846|atp:200624", "A")
