"""Verify the surface IOS's saved solver state against the template build's own runs (docs/studies/prediction_pipeline/).

For each (tour, statistic) asked, on the build tree's cache (default: the sandbox of the current best model of
10 Oct 2026), with the level layer as that build ran it:

    A  fidelity      this study's copy of the solver (ios_state.full_run) against the build's stored run
                     (surface_ios/full_runs/<layer folder>/<tour>_<stat>_surface.npz): O_eff and D_eff on every row
    B  same table    a checkpoint saved to disk after day D0, loaded into a fresh solver and resumed to the last day:
                     every row queried after D0 against the full run
    C  older table   the checkpoint made on an older table (only the matches finished before T = D0 + 21 days, as a
                     table downloaded on day T holds them), moved onto today's system and resumed: the rows queried
                     after D0 against the full run on today's table (a different system: the solver's tolerance)
    D  cold start    the last day solved from zero instead of the previous day's solution
    E  time          the resume over the days after D0 (the daily update's work for this run)

Writes data/studies/prediction_pipeline/ios_state/<tour>_<stat>.json (and the checkpoint files, then deleted unless
--keep). Reads only.
Run: ./python.sh src/eda/prediction_pipeline/verify_ios_state.py --runs atp:hold wta:ace [--d0 2026-09-14] [--workers 4]
"""
from __future__ import annotations

import os
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "1")          # as build_features.py runs its workers

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pp_common as PC  # noqa: E402

OUT = PC.OUT / "ios_state"


def day_of(text: str) -> int:
    return int(np.datetime64(text, "D").astype("int64"))


def subset(td: dict, keep: np.ndarray) -> dict:
    """The tour's cache restricted to some matches (both rows of each), keeping the player codes."""
    if not np.array_equal(keep[0::2], keep[1::2]):
        raise ValueError("a match must keep both rows")
    nr = len(td["pid"])
    out = {}
    for k, v in td.items():
        if k == "stats":
            out[k] = {s: {kk: vv[keep] for kk, vv in d.items()} for s, d in v.items()}
        elif isinstance(v, np.ndarray) and v.ndim >= 1 and len(v) == nr:
            out[k] = v[keep]
        else:
            out[k] = v
    out["row_index"] = np.flatnonzero(keep)
    return out


def task(args) -> dict:
    tour, stat, d0_text, tree, keep_files, tag = args
    PC.use_tree(Path(tree))
    PC.set_layer(Path(tree))
    import ios_state as I
    from src.eda.surface_ios import common as SC
    from src.eda.lower_level_evidence import level_layer_ios as LLEIOS

    rec = {"tour": tour, "stat": stat, "tree": tree, "layer_config": os.environ["LLE_LAYER"]}
    t0 = time.time()
    td = SC.load_tour(tour)
    s = I.make_setup(td, stat, "surface")
    rec["setup"] = s.info
    days = s.days
    d0 = float(day_of(d0_text)) if d0_text else float(days[-1] - 21)
    i0 = int(np.searchsorted(days, d0, side="right")) - 1          # the last snapshot day on or before D0
    d0 = float(days[i0])
    rec["d0"] = str(np.datetime64(int(d0), "D"))
    rec["last_day"] = str(np.datetime64(int(days[-1]), "D"))
    rec["days_after_d0"] = int(len(days) - 1 - i0)

    # A: the full run through this study's copy, checkpointed at D0 (and the day before the last, for D), against the
    # build's stored run
    last = len(days) - 1
    cps = {d0: None, float(days[last - 1]): None}
    t1 = time.time()
    out_full, rows_full, rfull = I.full_run(s, checkpoints=cps)
    rec["full_run"] = {**rfull, "seconds_total": round(time.time() - t1, 1)}
    runs = LLEIOS.runs_dir(SC.OUT / "full_runs")
    with np.load(runs / f"{tour}_{stat}_surface.npz") as zf:
        stored = {k: zf[k] for k in ("O_eff", "D_eff", "O", "D", "E", "F")}
    rec["A_fidelity"] = {k: PC.compare(out_full[k], stored[k]) for k in ("O_eff", "D_eff", "O", "D", "E", "F")}
    rec["A_fidelity"]["stored_file"] = str(runs / f"{tour}_{stat}_surface.npz")

    # B: save, load into a fresh solver, resume
    OUT.mkdir(parents=True, exist_ok=True)
    ck = OUT / f"{tour}_{stat}{tag}_checkpoint.npz"
    rec["B_checkpoint"] = I.save_checkpoint(ck, s, cps[d0], rows_full)
    t2 = time.time()
    with np.load(ck) as zf:                     # closed at once (Windows keeps an open npz locked)
        z = {k: zf[k] for k in zf.files}
    st = {k[3:]: v for k, v in z.items() if k.startswith("st_")}
    s2 = I.make_setup(td, stat, "surface")
    snap = I.Snap.from_state(s2, st)
    rows = I.empty_rows(s2)
    fl = z["row_index"]
    for k in I.ROW_KEYS:
        rows[k][fl] = z[f"row_{k}"]
    r_days = I.run_days(snap, rows)
    targets = np.flatnonzero(s2.query > d0)
    out_b = I.outputs(s2, rows, targets)
    rec["B_same_table"] = {"seconds_resume": round(time.time() - t2, 2), "resume": r_days, "target_rows": int(len(targets)),
                           **{k: PC.compare(out_b[k], out_full[k][targets]) for k in ("O_eff", "D_eff")}}

    # C: the checkpoint made on an older table (matches finished before T = D0 + 21), moved onto today's system
    T = d0 + 21
    keep = td["lf"] < T
    old = subset(td, keep)
    so = I.make_setup(old, stat, "surface")
    rec["C_older_table"] = {"table_day_T": str(np.datetime64(int(T), "D")), "rows_old": int(keep.sum()),
                            "rows_new": int(len(keep)), "setup_old": so.info}
    io = int(np.searchsorted(so.days, d0, side="right")) - 1
    rec["C_older_table"]["old_days_on_or_before_d0"] = int(io + 1)
    rec["C_older_table"]["new_days_on_or_before_d0"] = int(i0 + 1)
    same_days = bool(np.array_equal(so.days[:io + 1], days[:i0 + 1]))
    rec["C_older_table"]["same_snapshot_days_to_d0"] = same_days
    snap_o = I.Snap(so)
    rows_o = I.empty_rows(so)
    t3 = time.time()
    I.run_days(snap_o, rows_o, upto=io)
    rec["C_older_table"]["seconds_old_run_to_d0"] = round(time.time() - t3, 1)
    st_o = snap_o.state()
    st_o["day"] = np.float64(d0)
    mapped = I.map_state(st_o, so.sysm.active, I.triple_keys(so), s2, so.n_fe)
    snap_c = I.Snap.from_state(s2, mapped)
    rows_c = I.empty_rows(s2)
    fl_o = I.inflight_rows(so, d0)
    orig = old["row_index"][fl_o]
    for k in I.ROW_KEYS:
        rows_c[k][orig] = rows_o[k][fl_o]
    # rows of today's table queried by D0 that the older table did not hold cannot be served by the checkpoint
    missing = np.flatnonzero((s2.query <= d0) & ~keep)
    rec["C_older_table"]["rows_queried_by_d0_missing_from_old_table"] = int(len(missing))
    t4 = time.time()
    I.run_days(snap_c, rows_c)
    out_c = I.outputs(s2, rows_c, targets)
    rec["C_older_table"]["seconds_resume"] = round(time.time() - t4, 2)
    rec["C_older_table"].update({k: PC.compare(out_c[k], out_full[k][targets]) for k in ("O_eff", "D_eff")})
    # the same rows' inputs on the model's scale: the main-tour pool rows only (the frame's matches)
    main = td["level_main"][targets]
    rec["C_older_table"]["main_tour_rows"] = {k: PC.compare(out_c[k][main], out_full[k][targets][main])
                                              for k in ("O_eff", "D_eff")}

    # D: the last day solved cold (x = 0) against the warm chain
    st_prev = cps[float(days[last - 1])]
    warm = I.Snap.from_state(s2, st_prev)
    yw = warm.step(last)
    cold = I.Snap.from_state(s2, st_prev)
    cold.x = np.zeros_like(cold.x)
    yc = cold.step(last)
    rec["D_cold_start"] = {"day": str(np.datetime64(int(days[last]), "D")), "iterations_warm": int(yw[-2]),
                           "iterations_cold": int(yc[-2]),
                           "O": PC.compare(yc[1], yw[1]), "D": PC.compare(yc[2], yw[2]),
                           "E": PC.compare(yc[3], yw[3]), "F": PC.compare(yc[4], yw[4])}
    rec["seconds_task"] = round(time.time() - t0, 1)
    PC.write_json(OUT / f"{tour}_{stat}{tag}.json", rec)
    if not keep_files:
        try:
            ck.unlink(missing_ok=True)
        except OSError as e:                    # never lose the record over a scratch file
            rec["checkpoint_not_deleted"] = str(e)
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="+", default=["wta:ace", "atp:hold"], help="tour:stat ...")
    ap.add_argument("--d0", default=None, help="checkpoint day (default: 21 days before the last snapshot day)")
    ap.add_argument("--tree", default=str(PC.TREE))
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--keep", action="store_true", help="keep the checkpoint files")
    ap.add_argument("--tag", default="", help="suffix of the output files (e.g. _d0_2026-03-02)")
    a = ap.parse_args()
    jobs = [(r.split(":")[0], r.split(":")[1], a.d0, a.tree, a.keep, a.tag) for r in a.runs]
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(task, j): j for j in jobs}
        for f in as_completed(futs):
            r = f.result()
            PC.log(f"{r['tour']} {r['stat']}: A {json.dumps({k: (v['bitwise_equal'], v['rows'], v['max_abs_diff']) for k, v in r['A_fidelity'].items() if isinstance(v, dict)})}")
            PC.log(f"   B same table: {r['B_same_table']['O_eff']} {r['B_same_table']['seconds_resume']} s")
            PC.log(f"   C older table: {r['C_older_table']['O_eff']} / D {r['C_older_table']['D_eff']}")
            PC.log(f"   D cold: {r['D_cold_start']['O']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
