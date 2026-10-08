"""Run the surface IOS at the tuned constants on the full history and write its per-match inputs (surface-IOS study).

For every tour and statistic (spw and the model's seven) two leak-proof runs over all 872,704 matches:

    current   today's pooled IOS (Stage B's tuned h, kappa, tau; kappa_s = inf): reproduces the model's inputs
    surface   the tuned surface model (tuning_choice.json: half-life multiplier and kappa_s chosen on 2013-2018)

Out of sample (constants fixed on 2013-2018), each run forecasts the statistic in every evaluation-level box-score
match of 2019-2026 and 2022-2026; the surface model's gain over the current one is reported in milli-log-loss per unit,
positive = the surface model forecasts the statistic better, with paired 95% intervals over four-week blocks, overall,
by surface and on the main tour.

Writes data/studies/surface_ios/surface_features.parquet (one row per Stage 4 pool match: for each statistic, each
side's current O and D, the surface model's effective O_eff = O + E_s and D_eff = D + F_s on the match's surface, its
all-surface parts O and D, and its surface parts E_s and F_s), oos_scores.csv and build_features.json.

Run: ./python.sh src/eda/surface_ios/build_features.py   (SURFACE_IOS_WORKERS, default 14)
"""
from __future__ import annotations

import os
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_ios import common as C  # noqa: E402
from src.eda.surface_ios import ios_surface as IS  # noqa: E402
from src.eda.surface_ios.summarise_tuning import BLOCK_ORIGIN, ratio_gain  # noqa: E402

WORKERS = int(os.environ.get("SURFACE_IOS_WORKERS", "14"))
RUNS = C.OUT / "full_runs"
WINDOWS = {"2019-2026": range(2019, 2027), "2022-2026": range(2022, 2027)}
_TD: dict = {}


def _init() -> None:
    for t in ("atp", "wta"):
        _TD[t] = C.load_tour(t)


def task(args) -> dict:
    tour, stat, kind, hm, ksm = args
    chosen, typ = C.ios_constants()
    c = chosen[(tour, stat)]
    td = _TD[tour]
    h = c["h"] * hm
    if ksm is None:
        ks = np.inf
    elif isinstance(ksm, (tuple, list)):
        ks = tuple(c["kappa"] * (np.inf if v is None else v) for v in ksm)
    else:
        ks = c["kappa"] * ksm
    t0 = time.time()
    res = IS.run(td, stat, h, c["kappa"], ks, c["tau"], typ[(stat, tour)])
    ll, _ = IS.row_logloss(td, stat, res)
    keep = ("O_eff", "D_eff", "O", "D", "E", "F")
    np.savez_compressed(RUNS / f"{tour}_{stat}_{kind}.npz", ll=ll, **{k: res[k] for k in keep})
    consts = constants(tour, stat, hm, ksm)
    (RUNS / f"{tour}_{stat}_{kind}.json").write_text(json.dumps(consts), encoding="utf-8")
    return {"tour": tour, "stat": stat, "kind": kind, **consts, "solver": res["solver"],
            "seconds": round(time.time() - t0, 1)}


def constants(tour: str, stat: str, hm: float, ksm) -> dict:
    """The constants a run is made with (stored beside it; a saved run is re-used only if they match)."""
    chosen, _ = C.ios_constants()
    c = chosen[(tour, stat)]
    fin = lambda v: None if v is None or not np.isfinite(v) else float(v)  # noqa: E731
    if ksm is None:
        kE = kF = None
    elif isinstance(ksm, (tuple, list)):
        kE, kF = (None if v is None else c["kappa"] * v for v in ksm)
    else:
        kE = kF = c["kappa"] * ksm
    return {"h": fin(c["h"] * hm), "kappa": float(c["kappa"]), "kappa_E": fin(kE), "kappa_F": fin(kF),
            "tau": int(c["tau"])}


def saved_and_current(tour, stat, kind, hm, ksm) -> bool:
    npz, side = RUNS / f"{tour}_{stat}_{kind}.npz", RUNS / f"{tour}_{stat}_{kind}.json"
    if not npz.exists():
        return False
    if not side.exists() or json.loads(side.read_text(encoding="utf-8")) != constants(tour, stat, hm, ksm):
        raise RuntimeError(f"{npz.name} was made with other constants (or none recorded); delete it to rebuild")
    return True


def main() -> int:
    RUNS.mkdir(parents=True, exist_ok=True)
    choice = json.loads((C.OUT / "tuning_choice.json").read_text(encoding="utf-8"))
    tasks = []
    for t in ("atp", "wta"):
        for s in C.STATS:
            ch = choice[f"{t}|{s}"]
            tasks.append((t, s, "current", 1.0, None))
            if ch["variant"] == "shared":
                tasks.append((t, s, "surface", ch["h_mult"], ch["ks_mult"]))
            elif ch["variant"] == "return_only":
                tasks.append((t, s, "surface", ch["h_mult"], (ch["kE_mult"], ch["kF_mult"])))
            # "pooled": no surface variant beat today's IOS for this statistic; the surface arm keeps today's values
    tasks = [a for a in tasks if not saved_and_current(*a)]
    if "--current-only" in sys.argv:                 # today's pooled runs do not depend on the tuning choice
        tasks = [a for a in tasks if a[2] == "current"]
    tasks.sort(key=lambda a: (a[0] != "atp", a[2] != "surface"))
    meta = []
    C.log(f"{len(tasks)} full-history runs, {WORKERS} workers")
    with ProcessPoolExecutor(max_workers=WORKERS, initializer=_init) as ex:
        futs = [ex.submit(task, a) for a in tasks]
        for f in as_completed(futs):
            r = f.result()
            meta.append(r)
            C.log(f"  {r['tour']} {r['stat']} {r['kind']}: {r['seconds']}s, PCG {r['solver']['iterations_mean']:.1f}, "
                  f"not converged {r['solver']['not_converged']}")
            if r["solver"]["not_converged"]:
                raise RuntimeError(f"not converged: {r}")
    if "--current-only" in sys.argv:
        return 0

    # out-of-sample statistic forecasts and the per-match inputs
    pool = pd.read_parquet(C.CACHE / "pool.parquet")
    feats = {"match_id": pool["match_id"].to_numpy()}
    oos = []
    for t in ("atp", "wta"):
        td = C.load_tour(t)
        sel_pool = (pool["tour"] == t).to_numpy()
        a, b = pool.loc[sel_pool, "pos_a"].to_numpy(), pool.loc[sel_pool, "pos_b"].to_numpy()
        block = (td["day"] - BLOCK_ORIGIN) // 28
        for s in C.STATS:
            cur = np.load(RUNS / f"{t}_{s}_current.npz")
            srf_path = RUNS / f"{t}_{s}_surface.npz"
            srf = np.load(srf_path) if srf_path.exists() else cur
            for side, idx in (("a", a), ("b", b)):
                for k in ("O_eff", "D_eff"):
                    feats.setdefault(f"cur_{k[0]}_{s}_{side}", np.full(len(pool), np.nan))[sel_pool] = cur[k][idx]
                for k in ("O_eff", "D_eff", "O", "D", "E", "F"):
                    feats.setdefault(f"srf_{k}_{s}_{side}", np.full(len(pool), np.nan))[sel_pool] = srf[k][idx]
            units = td["stats"][s]["d"]
            for w, yrs in WINDOWS.items():
                base_sel = np.isfinite(cur["ll"]) & np.isfinite(srf["ll"]) & td["evaluation"] & np.isin(td["year"], list(yrs))
                for scope, extra in (("all levels", None), ("main tour", td["level_main"])):
                    for sname, code in (("all", None), ("hard", 1), ("clay", 2), ("grass", 3)):
                        m = base_sel.copy()
                        if extra is not None:
                            m &= extra
                        if code is not None:
                            m &= td["surf"] == code
                        if m.sum() < 50:
                            continue
                        g = ratio_gain(cur["ll"][m], srf["ll"][m], units[m], block[m])
                        oos.append({"tour": t, "stat": s, "window": w, "scope": scope, "surface": sname,
                                    "rows": int(m.sum()), **g})
    F = pd.DataFrame(feats)
    F.to_parquet(C.OUT / "surface_features.parquet", index=False)
    O = pd.DataFrame(oos)
    O.to_csv(C.OUT / "oos_scores.csv", index=False)
    C.jdump({"choice": choice, "runs": meta}, C.OUT / "build_features.json")
    with pd.option_context("display.width", 250, "display.max_rows", 500):
        print(O[(O["scope"] == "all levels")].round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
