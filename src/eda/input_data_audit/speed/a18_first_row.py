"""Audit step 18: the filter's diffuse start. The first row of each target's 364-day window sets the level with no
clipping (P11 = 1e6), so a broken first row poisons L and pushes f for as long as it stays in the window. Count the men's
2024-26 frame sides whose first in-window row is far from the rest of their window, and compare f_hat with a run that
starts the level at the median of the first five centred rows (an in-memory variant of the project's filter; scenario A
and B). Read-only; writes scratch/t_first_row.csv."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
SCR = Path.cwd() / "data" / "studies" / "input_data_audit" / "speed"   # run from the repo root
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 200)
from src.eda.serve_speed_tabpfn import features as F  # noqa: E402
from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402
from src.eda.serve_speed_tabpfn.latency import features_latency as FL  # noqa: E402

SD_L = float(json.loads(FL.META.read_text(encoding="utf-8"))["standardisation_sd_km_h"]["B_M1"])
PRM = dict(FL.MEN, hl=28.0)
p = FL.load_panel()
rd = FL.release_days(p)
keys = P.load_frame_keys()
t = F.side_targets(keys)
sel = t["tour"].eq("atp") & t["season"].between(2024, 2026)
A = t[sel & t["side"].eq("A")]
Bs = t[sel & t["side"].eq("B")]
tm = pd.concat([A, Bs], ignore_index=True)
nm = len(A)


def kalman_robust_start(Z, R, DAY, tday, prm, k0=5):
    """features.kalman, except the level starts at the median of the first k0 centred rows (diffuse variance kept for
    the update of row 1 is replaced by a start at that median with the variance of one observation)."""
    nt, H = Z.shape
    lam = math.log(2.0) / prm["hl"]
    s2f, q, c = prm["s2f"], prm["q"], prm["c"]
    med = np.nanmedian(np.where(np.arange(H)[None, :] < k0, Z, np.nan), axis=1)
    has0 = np.isfinite(Z[:, 0])
    L = np.where(has0, med, 0.0)
    f = np.zeros(nt)
    P11 = np.where(has0, R[:, 0] if R.shape[1] else 1.0, F.BIG)
    P11 = np.where(np.isfinite(P11), P11, F.BIG)
    P12 = np.zeros(nt); P22 = np.full(nt, s2f)
    last = np.full(nt, np.nan)
    for k in range(H):
        act = np.isfinite(Z[:, k])
        if not act.any():
            break
        dt_ = np.where(act & np.isfinite(last), np.maximum(DAY[:, k] - np.nan_to_num(last), 0.0), 0.0)
        phi = np.exp(-lam * dt_)
        fp = f * phi
        P11p = P11 + q * dt_; P12p = P12 * phi; P22p = P22 * phi * phi + s2f * (1.0 - phi * phi)
        z = np.where(act, Z[:, k], 0.0); Rk = np.where(act, R[:, k], 1.0)
        v = z - L - fp
        S = P11p + 2.0 * P12p + P22p + Rk
        cs = c * np.sqrt(S)
        v = np.minimum(np.maximum(v, -cs), cs)
        K1 = (P11p + P12p) / S; K2 = (P12p + P22p) / S
        L = np.where(act, L + K1 * v, L); f = np.where(act, fp + K2 * v, f)
        P11 = np.where(act, P11p - K1 * K1 * S, P11); P12 = np.where(act, P12p - K1 * K2 * S, P12)
        P22 = np.where(act, P22p - K2 * K2 * S, P22)
        last = np.where(act, DAY[:, k], last)
    has = np.isfinite(last)
    d = np.where(has, np.maximum(tday - np.nan_to_num(last), 0.0), 0.0)
    return np.where(has, f * np.exp(-lam * d), 0.0)


res = {}
for scen in ("A", "B"):
    rel = None if scen == "A" else rd["B"].to_numpy(np.int64)
    S = FL.Scenario(scen, p, rel, None if scen == "A" else rd["box"].to_numpy(np.int64))
    hist = FL.histories_rel(p, tm, rel)
    idx = hist["idx"]
    ok = idx >= 0
    safe = np.maximum(idx, 0)
    G = F.snapshot_gammas(p, tm, idx, S.offsets)
    Z = np.where(ok, p["y"].to_numpy(float)[safe] - G, np.nan)
    DAY = np.where(ok, p["obs"].to_numpy(float)[safe], np.nan)
    nb = p["basis"].astype(str).eq("ks").to_numpy()
    r_row = np.where(nb, PRM["nu_ks"], PRM["nu_pts"]) + PRM["sigma"] ** 2 / p["n"].to_numpy(float)
    R = np.where(ok, r_row[safe], np.nan)
    tday = tm["es"].to_numpy(float)
    f0 = F.kalman(Z, R, DAY, tday, PRM)["f_hat"]
    f1 = kalman_robust_start(Z, R, DAY, tday, PRM)
    k = ok.sum(1)
    rest_med = np.nanmedian(np.where(np.arange(Z.shape[1])[None, :] >= 1, Z, np.nan), axis=1)
    dev1 = Z[:, 0] - rest_med
    side = pd.DataFrame({"match_id": tm["match_id"], "side": tm["side"], "player_id": tm["player_id"], "rows": k,
                         "first_src": np.where(ok[:, 0], p["source"].to_numpy()[safe[:, 0]], ""),
                         "first_date": pd.to_datetime(np.where(ok[:, 0], DAY[:, 0], np.nan), unit="D"),
                         "dev_first": dev1, "f_hat": f0, "f_hat_robust_start": f1})
    side["d_f"] = side["f_hat"] - side["f_hat_robust_start"]
    res[scen] = side
    big = side[(side["rows"] >= 4) & (side["dev_first"].abs() > 15)]
    print(f"\n=== scenario {scen}: men's 2024-26 sides {len(side)}; with >= 4 rows {int((k >= 4).sum())}; first row "
          f"> 15 km/h from the median of the rest: {len(big)} sides, {big['player_id'].nunique()} players")
    print(big.groupby("first_src").agg(sides=("d_f", "size"), players=("player_id", "nunique"),
                                       mean_abs_df=("d_f", lambda s: s.abs().mean()),
                                       max_abs_df=("d_f", lambda s: s.abs().max())).round(2).to_string())
    # match level: spd_L with the robust start vs the build
    fA0, fB0 = f0[:nm], f0[nm:]
    fA1, fB1 = f1[:nm], f1[nm:]
    dL = np.clip((fA0 - fB0) / SD_L, -4, 4) - np.clip((fA1 - fB1) / SD_L, -4, 4)
    print(f"spd_L, build minus robust start: matches moved >= 0.25 / 0.5 / 1 / 2 units: "
          f"{int((np.abs(dL) >= .25).sum())} / {int((np.abs(dL) >= .5).sum())} / {int((np.abs(dL) >= 1).sum())} / "
          f"{int((np.abs(dL) >= 2).sum())} of {nm}; max {np.abs(dL).max():.2f}")
    print("sides with |f_hat - robust-start f_hat| >= 2 km/h:", int((side["d_f"].abs() >= 2).sum()),
          "| >= 5:", int((side["d_f"].abs() >= 5).sum()))
    print(side.loc[side["d_f"].abs().sort_values(ascending=False).index[:15],
                   ["match_id", "side", "player_id", "rows", "first_src", "first_date", "dev_first", "f_hat",
                    "f_hat_robust_start"]].round(2).to_string(index=False))
    side.to_csv(SCR / f"t_first_row_{scen}.csv", index=False)
