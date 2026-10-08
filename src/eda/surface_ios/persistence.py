"""How persistent are opponent-adjusted surface deviations? (surface-IOS study, evidence for the representation)

The market-anchoring study (docs/studies/market_anchoring/README.md, section 6.3) measured raw, not opponent-adjusted,
deviations: a season's clay-minus-hard deviation correlates 0.1-0.3 with the next season's. Here the deviation is IOS's
own: one static solve of the surface model (no time decay; Stage B's tuned kappa and tau; kappa_s = kappa, a light
shrinkage) on each of two disjoint three-year periods before any test season, 2013-2015 and 2016-2018, every level of
the history included (so opponents are rated on all their matches). For players with enough matches on both surfaces in
both periods:

    deviation  = E_clay - E_hard (serve side) or F_clay - F_hard (return side)
    level      = O or D, the all-surface part

and, across the two periods, their correlation and covariance. The covariance is the part that persists; its square
root, the "stable SD", compared between deviation and level says how large the persistent surface specialisation is
next to the persistent differences between players (the earlier study's last column, now opponent-adjusted).
Grass against hard is reported too; grass has few matches per player.

Writes data/studies/surface_ios/persistence.csv and persistence.json.
Run: ./python.sh src/eda/surface_ios/persistence.py
"""
from __future__ import annotations

import os
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_ios import common as C  # noqa: E402
from src.eda.surface_ios import ios_surface as IS  # noqa: E402

PERIODS = {"2013-2015": ("2013-01-01", "2015-12-31"), "2016-2018": ("2016-01-01", "2018-12-31")}
MIN_UNITS = 4.0          # typical matches (tau weights) a player needs on each surface in each period
CONTRASTS = {"Clay - Hard": (2, 1), "Grass - Hard": (3, 1)}
WORKERS = int(os.environ.get("SURFACE_IOS_WORKERS", "8"))


def static_solve(td: dict, stat: str, lo: str, hi: str, kappa: float, kappa_s: float, tau: int, typ: float):
    """One solve over the statistic's observations played in [lo, hi] (best-estimate day), no decay."""
    st = td["stats"][stat]
    a, b = C.day_of(lo), C.day_of(hi)
    in_p = (td["obs"] >= a) & (td["obs"] <= b)
    td2 = dict(td)
    td2["stats"] = {stat: {**st, "ok": st["ok"] & in_p}}
    release = np.full(len(td["pid"]), float(a))         # every observation in the period released at once
    sysm = IS.SurfaceSystem(td2, stat, release, td["obs"].astype(float), typ)
    (_, O, D, E, F, P, Q, Ps, Qs, it, conv), = list(IS.snapshots(sysm, np.array([a]), np.inf, kappa, kappa_s, tau))

    def full(v):                                  # the solver's players back to the tour's player codes
        out = np.zeros((sysm.n_full,) + v.shape[1:])
        out[sysm.active] = v
        return out
    return {"O": full(O), "D": full(D), "E": full(E), "F": full(F), "Ps": full(Ps), "Qs": full(Qs),
            "converged": conv, "iterations": it}


def raw_means(td: dict, stat: str, lo: str, hi: str, tau: int, typ: float) -> dict:
    """Not opponent-adjusted: each player's weighted mean centred value per surface and over all surfaces, as server
    (their own rows' y) and as returner (minus the opponent's y), in [lo, hi]; weights (d/typical)^tau as in IOS."""
    st = td["stats"][stat]
    a, b = C.day_of(lo), C.day_of(hi)
    ok = st["ok"] & (td["obs"] >= a) & (td["obs"] <= b)
    w = np.where(ok, (st["d"] / typ) ** tau if tau else 1.0, 0.0)
    n = td["n_players"]
    pid, surf = td["pid"], td["surf"]
    opp = np.arange(len(pid)) ^ 1
    out = {}
    for side, who, val in (("serve", pid, st["y"]), ("return", pid[opp], -st["y"])):
        W = np.zeros((n, IS.S + 1))
        WY = np.zeros((n, IS.S + 1))
        np.add.at(W, (who, surf), w)
        np.add.at(WY, (who, surf), w * np.where(ok, val, 0.0))
        with np.errstate(invalid="ignore", divide="ignore"):
            per_surf = WY[:, 1:] / W[:, 1:]
            overall = WY.sum(axis=1) / W.sum(axis=1)
        out[side] = {"level": overall, "surf": per_surf, "w": W[:, 1:]}
    return out


def stable(d1, d2) -> tuple[float, float]:
    cov = float(np.cov(d1, d2)[0, 1])
    return float(np.corrcoef(d1, d2)[0, 1]), float(np.sqrt(max(cov, 0.0)))


def one(args) -> list[dict]:
    tour, stat = args
    chosen, typ = C.ios_constants()
    c = chosen[(tour, stat)]
    td = C.load_tour(tour)
    ty = typ[(stat, tour)]
    res = {p: static_solve(td, stat, lo, hi, c["kappa"], c["kappa"], c["tau"], ty) for p, (lo, hi) in PERIODS.items()}
    raw = {p: raw_means(td, stat, lo, hi, c["tau"], ty) for p, (lo, hi) in PERIODS.items()}
    (p1, r1), (p2, r2) = res.items()
    w1, w2 = raw[p1], raw[p2]
    out = []
    for side, lvl, dev, wkey in (("serve", "O", "E", "Ps"), ("return", "D", "F", "Qs")):
        for label, (s1, s0) in CONTRASTS.items():
            enough = np.ones(td["n_players"], dtype=bool)
            for r in (r1, r2):
                enough &= (r[wkey][:, s1 - 1] >= MIN_UNITS) & (r[wkey][:, s0 - 1] >= MIN_UNITS)
            m = enough
            if m.sum() < 30:
                continue
            d1 = r1[dev][:, s1 - 1] - r1[dev][:, s0 - 1]
            d2 = r2[dev][:, s1 - 1] - r2[dev][:, s0 - 1]
            dev_r, dev_sd = stable(d1[m], d2[m])
            lvl_r, lvl_sd = stable(r1[lvl][m], r2[lvl][m])
            # the same players, not opponent-adjusted (the market-anchoring study's kind of measure, static)
            q1, q2 = w1[side], w2[side]
            rd1 = q1["surf"][:, s1 - 1] - q1["surf"][:, s0 - 1]
            rd2 = q2["surf"][:, s1 - 1] - q2["surf"][:, s0 - 1]
            mm = m & np.isfinite(rd1) & np.isfinite(rd2) & np.isfinite(q1["level"]) & np.isfinite(q2["level"])
            raw_dev_r, raw_dev_sd = stable(rd1[mm], rd2[mm])
            raw_lvl_r, raw_lvl_sd = stable(q1["level"][mm], q2["level"][mm])
            out.append({"tour": tour, "stat": stat, "side": side, "contrast": label, "players": int(m.sum()),
                        "deviation_r": dev_r, "level_r": lvl_r,
                        "stable_sd_deviation": dev_sd, "stable_sd_level": lvl_sd,
                        "ratio": dev_sd / lvl_sd if lvl_sd > 0 else np.nan,
                        "raw_deviation_r": raw_dev_r, "raw_level_r": raw_lvl_r,
                        "raw_stable_sd_deviation": raw_dev_sd, "raw_stable_sd_level": raw_lvl_sd,
                        "raw_ratio": raw_dev_sd / raw_lvl_sd if raw_lvl_sd > 0 else np.nan,
                        "mean_deviation": float(np.mean(np.r_[d1[m], d2[m]])),
                        "converged": bool(r1["converged"] and r2["converged"])})
    C.log(f"  {tour} {stat}: {len(out)} rows")
    return out


def main() -> int:
    tasks = [(t, s) for t in ("atp", "wta") for s in C.STATS]
    rows = []
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        for r in ex.map(one, tasks):
            rows.extend(r)
    R = pd.DataFrame(rows)
    R.to_csv(C.OUT / "persistence.csv", index=False)
    C.jdump({"periods": PERIODS, "min_units": MIN_UNITS, "rows": rows}, C.OUT / "persistence.json")
    with pd.option_context("display.width", 200, "display.max_rows", 200):
        print(R.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
