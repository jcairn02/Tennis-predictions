"""The real-date leak probe for the surface IOS (the match-timing study's probe, src/eda/match_timing/probe.py, applied
to the surface solver): no surface-IOS input of a match moves when results that surely happened after it are changed.

On the match-timing probe's slice (every level, 2023-2024, history inside the slice) and at its four cut days D (where
events overlap: a Grand Slam's second Wednesday, Cincinnati's third day): every match that surely started after D
(earliest start > D) has its result reversed (the winner and the two players' statistics exchanged, match_timing.probe.flip),
the surface IOS is re-solved, and every effective rating (O + E_s, D + F_s) and every surface deviation of every pool
match that surely finished by D (latest finish <= D) is compared with the unchanged solve. Statistics probed: spw and
hold (the probe's own) and first_won, each with a strong surface penalty and a weak one.

Writes data/studies/surface_ios/probe.json.
Run: ./python.sh src/eda/surface_ios/probe.py
"""
from __future__ import annotations

import os
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_ios import common as C  # noqa: E402
from src.eda.surface_ios import ios_surface as IS  # noqa: E402
from src.eda.match_timing import common as MT  # noqa: E402
from src.eda.match_timing import probe as MP  # noqa: E402
from src.eda.match_timing import rebuild as RB  # noqa: E402
from src.eda.feature_alpha_audit.repair_data import repair_tables  # noqa: E402
from src.eda.predictability_diagnostic import common as PC  # noqa: E402
from src.eda.predictability_diagnostic import stage1_baselines as E  # noqa: E402
from src.eda.ufc_ideas import stageB_common as B  # noqa: E402
from src.eda.lower_level_evidence import level_layer_ios as _LLEIOS  # noqa: E402   # level layer, joint solves (LLE_LAYER)

STATS = ("spw", "hold", "first_won")
KS_MULT = (1.0, 10.0)
ATOL = 1e-9


def solve(matches, players, odds, timing) -> dict:
    """Every pool match's surface-IOS values on the slice: {(tour, stat, ks): (O_eff_a, O_eff_b, D_eff_a, D_eff_b,
    E_a, E_b, F_a, F_b)}, plus the pool's match ids."""
    m, p, _ = repair_tables(matches, players)
    rows = RB.build_rows(m, p, odds)
    chosen, typ = C.ios_constants()
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
              "stats": {s: {"ok": sa[s]["ok"][idx], "x": sa[s]["x"][idx], "d": sa[s]["d"][idx], "y": sa[s]["c"][idx],
                            "mu": sa[s]["mu_scale"][idx]} for s in STATS}}
        td = _LLEIOS.annotate_td(td, rows, idx=idx, tour=t)  # level layer, joint solves (LLE_LAYER)
        pos = np.full(len(rows), -1)
        pos[idx] = np.arange(len(idx))
        sel = rows["tour"].to_numpy()[A] == t
        pa, pb = pos[A[sel]], pos[Bi[sel]]
        for s in STATS:
            c = chosen[(t, s)]
            for km in KS_MULT:
                r = _LLEIOS.run_surface(td, s, c["h"], c["kappa"], c["kappa"] * km, c["tau"], typ[(s, t)])  # level layer, joint solves (LLE_LAYER)
                vals = np.full((len(A), 8), np.nan)
                vals[sel] = np.column_stack([r["O_eff"][pa], r["O_eff"][pb], r["D_eff"][pa], r["D_eff"][pb],
                                             r["E"][pa], r["E"][pb], r["F"][pa], r["F"][pb]])
                out[(t, s, km)] = vals
    return out


def main() -> int:
    t0 = time.time()
    timing = pd.read_parquet(MT.TIMING, columns=["match_id", "es", "lf", "obs"])
    matches = PC.load_matches()
    matches = matches[matches["tournament_date"].between(pd.Timestamp(MP.SLICE[0]), pd.Timestamp(MP.SLICE[1]))]
    matches = matches.reset_index(drop=True)
    ids = set(matches["match_id"])
    players = pd.read_parquet(PC.MATCH_PLAYERS)
    players = players[players["match_id"].isin(ids)].reset_index(drop=True)
    odds = pd.read_parquet(E.ODDS)
    tm = timing[timing["match_id"].isin(ids)].reset_index(drop=True)
    C.log(f"slice {MP.SLICE}: {len(matches):,} matches")
    base = solve(matches, players, odds, tm)
    tmi = tm.set_index("match_id")
    lf_pool = pd.Series(base["match_id"]).map(tmi["lf"]).to_numpy()
    results = []
    for cut in MP.CUTS:
        D = float(MT.to_day([cut])[0])
        later = set(tm.loc[tm["es"] > D, "match_id"])
        earlier = lf_pool <= D
        m2, p2 = MP.flip(matches, players, later)
        got = solve(m2, p2, odds, tm)
        if not np.array_equal(got["match_id"], base["match_id"]):
            raise RuntimeError("the pool changed")
        rec = {"cut": cut, "changed_matches": len(later), "checked_matches": int(earlier.sum()), "by_input": {}}
        moved_any = np.zeros(len(earlier), dtype=bool)
        biggest = 0.0
        for key in (k for k in base if k != "match_id"):
            x, y = base[key], got[key]
            mv = ~np.isclose(x, y, rtol=0, atol=ATOL, equal_nan=True)
            rec["by_input"]["|".join(map(str, key))] = {"earlier_moved": int(mv[earlier].any(axis=1).sum()),
                                                        "later_moved": int(mv[~earlier].any(axis=1).sum())}
            moved_any |= mv.any(axis=1) & earlier
            gap = np.where(np.isfinite(x) & np.isfinite(y), np.abs(x - y), 0.0)
            biggest = max(biggest, float(gap[earlier].max()) if earlier.any() else 0.0)
        rec["earlier_moved_matches"] = int(moved_any.sum())
        rec["largest_earlier_difference"] = biggest
        results.append(rec)
        C.log(f"cut {cut}: {rec['earlier_moved_matches']} of {rec['checked_matches']:,} earlier matches moved "
              f"(largest difference {biggest:.2e}); {len(later):,} later results reversed")
    out = {"slice": MP.SLICE, "cuts": results, "tolerance": ATOL, "stats": STATS, "ks_mult": KS_MULT,
           "verdict": ("PASS: no surface-IOS value of a match that surely finished by the cut moved"
                       if all(r["earlier_moved_matches"] == 0 for r in results) else "FAIL"),
           "seconds": round(time.time() - t0, 1)}
    C.jdump(out, C.OUT / "probe.json")
    C.log(out["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
