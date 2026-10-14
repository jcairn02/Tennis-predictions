"""The reference level of every daily snapshot of the decided surface IOS, from a re-solve that also reproduces the
stored ratings (gate G1).

For each tour and each of the model's 7 statistics the surface IOS is solved again at the decided constants (Stage B's
h, kappa, tau with the surface-IOS tuning choice, exactly as surface_ios/build_features.py runs its "surface" kind) on
the same cached inputs, with a read-only hook on the snapshot generator (ios_surface.snapshots). At each snapshot day t
the hook records the reference players' unweighted mean O + E_s and D + F_s for every surface code (common.py's
definition: players in a main-tour observation of the statistic released by t, best-estimate day t - 364 or later).
The hook passes every snapshot through unchanged, and the re-solve's per-row ratings must equal the stored full-history
run (surface_ios/full_runs/<tour>_<stat>_surface.npz) to 1e-12 with identical missing values: the reference levels then
belong to exactly the ratings the model reads.

Writes data/studies/ios_product_centring/reference/<tour>_<stat>.npz (days, m_o, m_d, count: one row per snapshot,
columns surface codes 0..4) and checks/g1_reference.json.
Run: ./python.sh src/eda/ios_product_centring/reference.py   (IOS_CENTRING_WORKERS, default 14)
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

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.ios_product_centring import common as C  # noqa: E402
from src.eda.surface_ios import build_features as BF  # noqa: E402
from src.eda.surface_ios import common as SI  # noqa: E402
from src.eda.surface_ios import ios_surface as IS  # noqa: E402

WORKERS = int(os.environ.get("IOS_CENTRING_WORKERS", "14"))
S = IS.S
ORIG_SNAPSHOTS = IS.snapshots
_TD: dict = {}


def observation_order(td: dict, stat: str) -> np.ndarray:
    """The rows of the solver's observations in its order (ios_surface.SurfaceSystem.__init__, repeated)."""
    st = td["stats"][stat]
    lf, obs = td["lf"], td["obs"]
    release = np.where(np.isfinite(lf), lf + 1, np.nan)
    k = np.flatnonzero(st["ok"] & np.isfinite(release) & np.isfinite(obs))
    return k[np.argsort(release[k], kind="stable")]


def reference_hook(td: dict, stat: str, main: np.ndarray | None = None):
    """(wrapper, record): wrapper replaces ios_surface.snapshots for one solve, yields every snapshot unchanged and
    fills record with days, m_o, m_d (snapshots x surface codes 0..S) and count (reference players per snapshot).
    main: a per-row main-tour flag (default td["level_main"])."""
    k = observation_order(td, stat)
    main_k = np.asarray(td["level_main"] if main is None else main, dtype=bool)[k]
    rel_k = (td["lf"][k] + 1).astype(np.int64)
    rec: dict = {}

    def wrapper(sysm, days, h, kappa, kappa_s, tau):
        if len(k) != len(sysm.y) or not np.array_equal(sysm.release, rel_k) \
                or not np.array_equal(sysm.srv, sysm.cmap[td["pid"][k]]):
            raise RuntimeError("the hook's observation order differs from the solver's")
        n, nd = sysm.n, len(days)
        last = np.full(n, -np.inf)                       # each player's latest released main-tour observation day
        m_o, m_d = np.full((nd, S + 1), np.nan), np.full((nd, S + 1), np.nan)
        count = np.zeros(nd, dtype=np.int64)
        ptr = 0
        for item in ORIG_SNAPSHOTS(sysm, days, h, kappa, kappa_s, tau):
            i, O, D, E, F = item[:5]
            t = float(days[i])
            new = int(np.searchsorted(sysm.release, t, side="right"))    # the snapshot's own released observations
            if new > ptr:
                sel = ptr + np.flatnonzero(main_k[ptr:new])
                if len(sel):
                    np.maximum.at(last, sysm.srv[sel], sysm.obs[sel])
                    np.maximum.at(last, sysm.ret[sel], sysm.obs[sel])
                ptr = new
            mem = last >= t - C.WINDOW_DAYS
            count[i] = int(mem.sum())
            if count[i]:
                o, d = O[mem], D[mem]
                m_o[i, 0], m_d[i, 0] = o.mean(), d.mean()
                for s in range(1, S + 1):
                    m_o[i, s] = (o + E[mem, s - 1]).mean()
                    m_d[i, s] = (d + F[mem, s - 1]).mean()
            yield item
        rec.update(days=np.asarray(days, dtype="float64"), m_o=m_o, m_d=m_d, count=count)
    return wrapper, rec


def solve_with_reference(td: dict, stat: str, h: float, kappa: float, kappa_s, tau: int, typ: float,
                         main: np.ndarray | None = None, until_day: int | None = None) -> tuple[dict, dict]:
    """ios_surface.run with the hook: (the run's outputs, the reference record)."""
    wrapper, rec = reference_hook(td, stat, main)
    IS.snapshots = wrapper
    try:
        res = IS.run(td, stat, h, kappa, kappa_s, tau, typ, until_day=until_day)
    finally:
        IS.snapshots = ORIG_SNAPSHOTS
    if not rec:
        raise RuntimeError("the hook recorded nothing")
    return res, rec


def decided_constants(tour: str, stat: str) -> tuple[float, float, object, int, float, tuple]:
    """(h, kappa, kappa_s, tau, typ, (h_mult, ks_mult)) as build_features.py runs the "surface" kind."""
    choice = C.read_json(SI.OUT / "tuning_choice.json")[f"{tour}|{stat}"]
    chosen, typ = SI.ios_constants()
    c = chosen[(tour, stat)]
    if choice["variant"] == "shared":
        hm, ksm = choice["h_mult"], choice["ks_mult"]
        ks = c["kappa"] * ksm
    elif choice["variant"] == "return_only":
        hm, ksm = choice["h_mult"], (choice["kE_mult"], choice["kF_mult"])
        ks = tuple(c["kappa"] * (np.inf if v is None else v) for v in ksm)
    else:
        raise RuntimeError(f"{tour} {stat}: no surface run (variant {choice['variant']})")
    return c["h"] * hm, c["kappa"], ks, c["tau"], typ[(stat, tour)], (hm, ksm)


def _init() -> None:
    for t in C.TOURS:
        _TD[t] = SI.load_tour(t)


def task(args) -> dict:
    tour, stat = args
    t0 = time.time()
    td = _TD[tour]
    h, kappa, ks, tau, typ, (hm, ksm) = decided_constants(tour, stat)
    stored_consts = C.read_json(C.SI_RUNS / f"{tour}_{stat}_surface.json")
    if BF.constants(tour, stat, hm, ksm) != stored_consts:
        raise RuntimeError(f"{tour} {stat}: the decided constants differ from the stored run's")
    res, rec = solve_with_reference(td, stat, h, kappa, ks, tau, typ)
    with np.load(C.SI_RUNS / f"{tour}_{stat}_surface.npz") as z:
        gaps = {k: C.max_gap(res[k], z[k]) for k in ("O_eff", "D_eff", "O", "D", "E", "F")}
    C.REF.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(C.REF / f"{tour}_{stat}.npz", days=rec["days"], m_o=rec["m_o"], m_d=rec["m_d"],
                        count=rec["count"])
    from2013 = rec["days"] >= SI.day_of("2013-01-01")
    return {"tour": tour, "stat": stat, "constants": stored_consts,
            "max_abs_gap": {k: g for k, (g, _) in gaps.items()},
            "same_missing": {k: s for k, (_, s) in gaps.items()},
            "passed": all(g <= C.EXACT and s for g, s in gaps.values()),
            "snapshots": int(len(rec["days"])),
            "reference_players_from_2013": {"min": int(rec["count"][from2013].min()),
                                            "median": float(np.median(rec["count"][from2013])),
                                            "max": int(rec["count"][from2013].max())},
            "solver": res["solver"], "seconds": round(time.time() - t0, 1)}


def main() -> int:
    tasks = [(t, s) for t in C.TOURS for s in C.STATS]
    C.log(f"{len(tasks)} hooked re-solves, {WORKERS} workers")
    rows = []
    with ProcessPoolExecutor(max_workers=WORKERS, initializer=_init) as ex:
        futs = [ex.submit(task, a) for a in tasks]
        for f in as_completed(futs):
            r = f.result()
            rows.append(r)
            C.log(f"  {r['tour']} {r['stat']}: {r['seconds']}s, G1 {'pass' if r['passed'] else 'FAIL'} "
                  f"(largest gap {max(r['max_abs_gap'].values()):.1e}), reference players from 2013 "
                  f"{r['reference_players_from_2013']}")
    rows.sort(key=lambda r: (r["tour"], C.STATS.index(r["stat"])))
    out = {"what": "G1: the hooked re-solve reproduces the stored surface-IOS ratings of every row (1e-12, same "
                   "missing values); the reference levels of every snapshot",
           "tolerance": C.EXACT, "window_days": C.WINDOW_DAYS, "runs": rows,
           "passed": all(r["passed"] for r in rows) and len(rows) == len(tasks)}
    C.jdump(out, C.CHECKS / "g1_reference.json")
    C.log(f"G1 {'PASS' if out['passed'] else 'FAIL'}")
    return 0 if out["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
