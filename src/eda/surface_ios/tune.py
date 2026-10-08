"""Tune the surface penalty (kappa_s) of the surface IOS on 2013-2018, Stage B's tuning window, before any test season.

For every tour and statistic (spw and the model's seven), the leak-proof solver (ios_surface.run) is run on the history
up to 31 Dec 2018 with Stage B's tuned (h, kappa, tau) and

    kappa_s = kappa x {1, 3, 10, 30}, and kappa_s = inf (the pooled IOS, today's inputs)
    at the tuned half-life h and at 2h (surface traits may need a longer memory than a player's level)

and scored like Stage B: the binomial log loss per unit of the statistic in each evaluation-level box-score match of
2013-2018, at expit(mu + O_eff,server - D_eff,returner), against the tour's surface average. Results by surface and on
the main tour alone are kept as well, and each run's per-row log losses (for paired intervals in summarise_tuning.py).

Writes data/studies/surface_ios/tuning/runs.jsonl (one line per run, appended as runs finish; a rerun skips finished
runs) and tuning/ll_<tour>_<stat>_<h>_<kappa_s>.npz.

Run: ./python.sh src/eda/surface_ios/tune.py   (about 45 minutes with 14 workers; SURFACE_IOS_WORKERS to change)
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

from src.eda.surface_ios import common as C  # noqa: E402
from src.eda.surface_ios import ios_surface as IS  # noqa: E402

TUNE = C.OUT / "tuning"
WORKERS = int(os.environ.get("SURFACE_IOS_WORKERS", "14"))
KS_MULT = (1.0, 3.0, 10.0, 30.0, np.inf)
H_MULT = (1.0, 2.0)
# the second grid (--grid return), added after the first grid and the persistence check showed serve-side deviations
# small and barely persistent next to return-side ones: no serve deviation, the return deviation at these multiples
RETURN_ONLY = ((np.inf, 3.0), (np.inf, 10.0), (np.inf, 30.0))
YEARS = range(2013, 2019)

_TD: dict = {}


def _m(v) -> str:
    return "inf" if not np.isfinite(v) else f"{v:g}"


def tag(tour, stat, hm, km) -> str:
    if isinstance(km, tuple):
        return f"{tour}_{stat}_h{hm:g}_kE{_m(km[0])}_kF{_m(km[1])}"
    return f"{tour}_{stat}_h{hm:g}_ks{_m(km)}"


def _init() -> None:
    for t in ("atp", "wta"):
        _TD[t] = C.load_tour(t)


def task(args) -> dict:
    tour, stat, hm, km = args
    chosen, typ = C.ios_constants()
    c = chosen[(tour, stat)]
    td = _TD[tour]
    h = c["h"] * hm
    ks = (c["kappa"] * km[0], c["kappa"] * km[1]) if isinstance(km, tuple) else c["kappa"] * km
    t0 = time.time()
    res = IS.run(td, stat, h, c["kappa"], ks, c["tau"], typ[(stat, tour)], until_day=C.day_of(C.TUNE_TO))
    ll, ll0 = IS.row_logloss(td, stat, res)
    sel = np.isfinite(ll) & td["evaluation"] & np.isin(td["year"], list(YEARS))
    rows = np.flatnonzero(sel)
    np.savez_compressed(TUNE / f"ll_{tag(tour, stat, hm, km)}.npz", rows=rows, ll=ll[rows], ll0=ll0[rows])
    sc = IS.score(td, stat, res, YEARS)
    main = IS.score(td, stat, res, YEARS, sel_extra=td["level_main"], by_surface=False)["all"]
    opp = np.arange(len(td["pid"])) ^ 1
    box = td["stats"][stat]["ok"] & td["level_main"] & np.isin(td["year"], list(YEARS)) & np.isfinite(res["O_eff"])
    spread = {}
    for s in range(1, C.N_SURF + 1):
        m = box & (td["surf"] == s)
        spread[C.SURF_NAMES[s]] = {"sd_O": float(np.std(res["O"][m])) if m.any() else None,
                                   "sd_E": float(np.std(res["E"][m])) if m.any() else None,
                                   "sd_D": float(np.std(res["D"][opp][m])) if m.any() else None,
                                   "sd_F": float(np.std(res["F"][opp][m])) if m.any() else None}
    fin = lambda v: None if not np.isfinite(v) else float(v)  # noqa: E731
    pair = isinstance(km, tuple)
    return {"tour": tour, "stat": stat, "h_mult": hm, "variant": "return_only" if pair else "shared",
            "ks_mult": None if pair else fin(km), "kE_mult": fin(km[0]) if pair else fin(km),
            "kF_mult": fin(km[1]) if pair else fin(km),
            "h": None if not np.isfinite(h) else h, "kappa": c["kappa"],
            "kappa_s": None if pair else fin(ks), "kappa_E": fin(ks[0]) if pair else fin(ks),
            "kappa_F": fin(ks[1]) if pair else fin(ks),
            "tau": c["tau"], "score": sc, "main_tour": main, "spread_main_tour": spread, "solver": res["solver"],
            "seconds": round(time.time() - t0, 1), "tag": tag(tour, stat, hm, km)}


def main() -> int:
    TUNE.mkdir(parents=True, exist_ok=True)
    out = TUNE / "runs.jsonl"
    done = set()
    if out.exists():
        done = {json.loads(line)["tag"] for line in out.read_text(encoding="utf-8").splitlines() if line.strip()}
    if "--grid" in sys.argv and sys.argv[sys.argv.index("--grid") + 1] == "return":
        tasks = [(t, s, 1.0, km) for t in ("atp", "wta") for s in C.STATS for km in RETURN_ONLY]
    else:
        tasks = [(t, s, hm, km) for t in ("atp", "wta") for s in C.STATS for hm in H_MULT for km in KS_MULT]
    tasks = [a for a in tasks if tag(*a) not in done]
    # the long runs first: men before women, surface runs before pooled ones
    tasks.sort(key=lambda a: (a[0] != "atp", not isinstance(a[3], tuple) and not np.isfinite(a[3])))
    C.log(f"{len(tasks)} runs to do ({len(done)} done), {WORKERS} workers")
    with ProcessPoolExecutor(max_workers=WORKERS, initializer=_init) as ex:
        futs = {ex.submit(task, a): a for a in tasks}
        for f in as_completed(futs):
            r = f.result()
            with out.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(r, default=lambda o: None if isinstance(o, float) and not np.isfinite(o)
                                    else (o.item() if hasattr(o, "item") else str(o))) + "\n")
            C.log(f"  {r['tag']}: {r['score']['all']['better_milli_per_unit']:.3f} milli/unit "
                  f"(clay {r['score']['Clay']['better_milli_per_unit']:.3f}, grass "
                  f"{r['score']['Grass']['better_milli_per_unit']:.3f}); {r['seconds']}s, "
                  f"PCG {r['solver']['iterations_mean']:.1f}, not converged {r['solver']['not_converged']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
