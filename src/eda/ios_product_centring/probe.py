"""Gate G3: the real-date leak probe for the centred products (the surface-IOS study's probe, src/eda/surface_ios/
probe.py, with reference.py's hook): no reference level and no centred product of a match moves when results that
surely happened after it are reversed.

On the match-timing probe's slice (every level, 2023-2024, history inside the slice) and at its four cut days D: every
match that surely started after D (earliest start > D) has its result reversed (match_timing.probe.flip), the decided
surface IOS is re-solved with the hook, and for every pool match that surely finished by D (latest finish <= D) its
surface-effective ratings, the reference level of its snapshot and surface, and its centred product are compared with the
unchanged solve (tolerance 1e-9, the surface-IOS probe's). Statistics: hold and first_won (the surface-IOS probe's own
model statistics) and ace (a serve-style one), at the decided constants. The main-tour flag is the cache's rule.

Writes data/studies/ios_product_centring/checks/g3_probe.json.
Run: ./python.sh src/eda/ios_product_centring/probe.py   (IOS_CENTRING_PROBE_WORKERS, default 5)
"""
from __future__ import annotations

import os
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.ios_product_centring import common as C  # noqa: E402
from src.eda.ios_product_centring import reference as R  # noqa: E402
from src.eda.surface_ios import common as SI  # noqa: E402
from src.eda.match_timing import common as MT  # noqa: E402
from src.eda.match_timing import probe as MP  # noqa: E402
from src.eda.match_timing import rebuild as RB  # noqa: E402
from src.eda.feature_alpha_audit.repair_data import repair_tables  # noqa: E402
from src.eda.predictability_diagnostic import common as PC  # noqa: E402
from src.eda.predictability_diagnostic import stage1_baselines as E  # noqa: E402
from src.eda.ufc_ideas import stageB_common as B  # noqa: E402

STATS = ("hold", "first_won", "ace")
MAIN_LEVELS = ["GS", "FIN", "T1000", "T500", "T250"]          # surface_ios/build_cache.py's level_main
ATOL = 1e-9
WORKERS = int(os.environ.get("IOS_CENTRING_PROBE_WORKERS", "5"))
KEYS = ("O_a", "O_b", "D_a", "D_b", "m_o", "m_d", "cprod")


def slice_tables():
    timing = pd.read_parquet(MT.TIMING, columns=["match_id", "es", "lf", "obs"])
    matches = PC.load_matches()
    matches = matches[matches["tournament_date"].between(pd.Timestamp(MP.SLICE[0]), pd.Timestamp(MP.SLICE[1]))]
    matches = matches.reset_index(drop=True)
    ids = set(matches["match_id"])
    players = pd.read_parquet(PC.MATCH_PLAYERS)
    players = players[players["match_id"].isin(ids)].reset_index(drop=True)
    odds = pd.read_parquet(E.ODDS)
    tm = timing[timing["match_id"].isin(ids)].reset_index(drop=True)
    return matches, players, odds, tm


def solve(matches, players, odds, timing) -> dict:
    """Every pool match's values on the slice: {(tour, stat): (n_pool, 7) array of KEYS}, plus the pool's match ids."""
    m, p, _ = repair_tables(matches, players)
    rows = RB.build_rows(m, p, odds)
    chosen, typ = SI.ios_constants()
    sa = B.stat_arrays(rows, B.surface_means(), STATS)
    tm = timing.set_index("match_id")
    A, Bi = B.pool_rows(rows)
    out = {"match_id": rows["match_id"].to_numpy()[A]}
    for t in PC.TOURS:
        idx = np.flatnonzero(rows["tour"].to_numpy() == t)
        pid = pd.factorize(rows["pcode"].to_numpy()[idx])[0].astype(np.int64)
        td = {"pid": pid, "n_players": int(pid.max()) + 1, "day": rows["day"].to_numpy()[idx].astype(np.int64),
              "ev": rows["ev"].to_numpy()[idx].astype(np.int64),
              "round_order": rows["round_order"].to_numpy()[idx].astype(np.int64),
              "surf": rows["surf"].to_numpy()[idx].astype(np.int64),
              "es": rows["match_id"].map(tm["es"]).to_numpy(dtype=float)[idx],
              "lf": rows["match_id"].map(tm["lf"]).to_numpy(dtype=float)[idx],
              "obs": rows["match_id"].map(tm["obs"]).to_numpy(dtype=float)[idx],
              "level_main": rows["level"].isin(MAIN_LEVELS).to_numpy()[idx],
              "stats": {s: {"ok": sa[s]["ok"][idx], "x": sa[s]["x"][idx], "d": sa[s]["d"][idx], "y": sa[s]["c"][idx],
                            "mu": sa[s]["mu_scale"][idx]} for s in STATS}}
        pos = np.full(len(rows), -1)
        pos[idx] = np.arange(len(idx))
        sel = rows["tour"].to_numpy()[A] == t
        pa, pb = pos[A[sel]], pos[Bi[sel]]
        q, surf = td["es"][pa], td["surf"][pa].astype(np.int64)
        for s in STATS:
            h, kappa, ks, tau, ty, _ = R.decided_constants(t, s)
            r, rec = R.solve_with_reference(td, s, h, kappa, ks, tau, ty)
            i = np.searchsorted(rec["days"], q)
            if not np.array_equal(rec["days"][i], q):
                raise RuntimeError("a pool match's start is not a snapshot day")
            mo, md = C.level(rec["m_o"][i, surf], rec["count"][i]), C.level(rec["m_d"][i, surf], rec["count"][i])
            Oa, Ob, Da, Db = r["O_eff"][pa], r["O_eff"][pb], r["D_eff"][pa], r["D_eff"][pb]
            vals = np.full((len(A), len(KEYS)), np.nan)
            vals[sel] = np.column_stack([Oa, Ob, Da, Db, mo, md, C.centred_product(Oa, Ob, Da, Db, mo, md)])
            out[(t, s)] = vals
    return out


def job(cut: str | None) -> dict:
    """The unchanged solve (cut None) or the solve with every result after the cut reversed."""
    matches, players, odds, tm = slice_tables()
    if cut is not None:
        D = float(MT.to_day([cut])[0])
        later = set(tm.loc[tm["es"] > D, "match_id"])
        matches, players = MP.flip(matches, players, later)
    return {"cut": cut, "values": solve(matches, players, odds, tm)}


def main() -> int:
    t0 = time.time()
    _, _, _, tm = slice_tables()
    C.log(f"slice {MP.SLICE}: {tm['match_id'].nunique():,} matches; cuts {MP.CUTS}; {WORKERS} workers")
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        res = {r["cut"]: r["values"] for r in ex.map(job, [None, *MP.CUTS])}
    base = res[None]
    tmi = tm.set_index("match_id")
    lf_pool = pd.Series(base["match_id"]).map(tmi["lf"]).to_numpy()
    results = []
    for cut in MP.CUTS:
        got = res[cut]
        if not np.array_equal(got["match_id"], base["match_id"]):
            raise RuntimeError("the pool changed")
        D = float(MT.to_day([cut])[0])
        earlier = lf_pool <= D
        rec = {"cut": cut, "changed_matches": int((tm["es"] > D).sum()), "checked_matches": int(earlier.sum()),
               "by_input": {}}
        moved_any = np.zeros(len(earlier), dtype=bool)
        biggest = 0.0
        for key in (k for k in base if k != "match_id"):
            x, y = base[key], got[key]
            mv = ~np.isclose(x, y, rtol=0, atol=ATOL, equal_nan=True)
            for c, name in enumerate(KEYS):
                rec["by_input"][f"{key[0]}|{key[1]}|{name}"] = {"earlier_moved": int(mv[earlier, c].sum()),
                                                                "later_moved": int(mv[~earlier, c].sum())}
            moved_any |= mv.any(axis=1) & earlier
            gap = np.where(np.isfinite(x) & np.isfinite(y), np.abs(x - y), 0.0)
            biggest = max(biggest, float(gap[earlier].max()) if earlier.any() else 0.0)
        rec["earlier_moved_matches"] = int(moved_any.sum())
        rec["largest_earlier_difference"] = biggest
        rec["later_cprod_moved"] = int(sum(v["later_moved"] for k, v in rec["by_input"].items() if k.endswith("cprod")))
        results.append(rec)
        C.log(f"cut {cut}: {rec['earlier_moved_matches']} of {rec['checked_matches']:,} earlier matches moved "
              f"(largest difference {biggest:.2e}); later centred products moved {rec['later_cprod_moved']:,}")
    passed = all(r["earlier_moved_matches"] == 0 for r in results) and all(r["later_cprod_moved"] > 0 for r in results)
    out = {"what": "G3: reversing every result after a cut day moves no surface-effective rating, reference level or "
                   "centred product of a match that surely finished by the cut; later ones respond",
           "slice": MP.SLICE, "cuts": results, "tolerance": ATOL, "stats": STATS, "passed": passed,
           "seconds": round(time.time() - t0, 1)}
    C.jdump(out, C.CHECKS / "g3_probe.json")
    C.log(f"G3 {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
