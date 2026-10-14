"""Verify Stage B's 17 forms from saved z against the decided computation (docs/studies/prediction_pipeline/).

On the build tree's tables (default: the sandbox of the current best model of 10 Oct 2026), with the level layer as the
build ran it:

    R  reference     the decided computation of the 17 inputs: level_layer.forms_z (the 17 pairs' z for every box row)
                     and, per pair and tour, level_layer.forms_step3 and Ctx.pool_values, exactly as stageB_adjperf.build
                     makes them (the other 13 pairs it also builds reach no input); checked against the tree's stored
                     stageB_adj_features.parquet (float32)
    Z  new matches   the z of every box row after D0 from this study's targeted pair moments (forms_state.z_for),
                     against R's z
    F  the inputs    the 17 inputs of every pool match after D0 from the saved z (R's up to D0, Z's after) and as-of
                     sums over those matches' players only (forms_state.step3_for), against R
    T  time          Z and F's seconds (a daily update's Stage B work)

Writes data/studies/prediction_pipeline/forms_state/verify.json. Reads only.
Run: ./python.sh src/eda/prediction_pipeline/verify_forms_state.py [--d0 2026-09-14]
"""
from __future__ import annotations

import os
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "4")

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pp_common as PC  # noqa: E402

OUT = PC.OUT / "forms_state"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--d0", default=None)
    ap.add_argument("--tree", default=str(PC.TREE))
    a = ap.parse_args()
    PC.use_tree(Path(a.tree))
    PC.set_layer(Path(a.tree))
    import forms_state as FS
    from src.eda.lower_level_evidence import level_layer as LL
    from src.eda.ufc_ideas import stageB_adjperf as AP

    rec = {"tree": a.tree, "layer_config": os.environ["LLE_LAYER"]}
    t0 = time.time()
    ctx = FS.context()
    chosen = FS.pinned_constants()
    rec["seconds_context"] = round(time.time() - t0, 1)
    PC.log(f"context: {len(ctx.box_idx):,} box rows, {ctx.P.n_pairs:,} pairs, {len(ctx.A):,} pool matches")

    # R: the decided computation of the 17 inputs
    t1 = time.time()
    dummy = {k: np.full(len(ctx.box_idx), np.nan) for k in LL.FORM_SPECS}
    Zr = LL.forms_z(ctx, chosen, dummy)
    feats_r = {}
    tour_pool = ctx.rows["tour"].to_numpy()[ctx.A]
    for s, ch in LL.FORM_SPECS:
        units, ok = ctx.step3_units(s, ch)
        col = f"{ch}_{s}|decayed"
        feats_r[col] = np.full(len(ctx.A), np.nan)
        for t in ("atp", "wta"):
            c = AP.constants_for(chosen, s, ch, t)
            sums = LL.forms_step3(ctx, s, ch, [Zr[(s, ch)]], units, ok & (ctx.tour_box == t), c["tau"], (c["h3"],))
            kref = ctx.pool_kref(s, c["K3"], c["tau"])
            v, _ = ctx.pool_values(sums, AP.form_key("decayed", c["h3"]), 0, kref, exists_key="career")
            mt = tour_pool == t
            feats_r[col][mt] = v[mt]
    rec["seconds_reference"] = round(time.time() - t1, 1)
    stored = pd.read_parquet(AP.ADJ_FEATURES, columns=["match_id"] + list(feats_r))
    if not np.array_equal(stored["match_id"].to_numpy(), ctx.rows["match_id"].to_numpy()[ctx.A]):
        raise RuntimeError("the stored features are not in the pool's order")
    rec["R_vs_stored_float32"] = {col: PC.compare(np.asarray(v, dtype="float32"), stored[col].to_numpy())
                                  for col, v in feats_r.items()}
    PC.log(f"reference in {rec['seconds_reference']} s; vs stored: "
           f"{sum(r['bitwise_equal'] == r['rows'] for r in rec['R_vs_stored_float32'].values())} of 17 columns bitwise")

    # the checkpoint
    day_box = ctx.rows["day"].to_numpy()[ctx.box_idx]
    last = int(day_box.max())
    d0 = int(np.datetime64(a.d0, "D").astype("int64")) if a.d0 else last - 21
    rec["d0"] = str(np.datetime64(d0, "D"))
    rec["last_tournament_day"] = str(np.datetime64(last, "D"))
    new_box = np.flatnonzero(day_box > d0)
    pool_day = ctx.rows["day"].to_numpy()[ctx.A]
    new_pool = np.flatnonzero(pool_day > d0)
    rec["new_box_rows"] = int(len(new_box))
    rec["new_pool_matches"] = int(len(new_pool))

    # Z: the new rows' z from targeted pair moments
    t2 = time.time()
    specs = FS.layer_specs(ctx, chosen)
    rec["seconds_layer_specs"] = round(time.time() - t2, 1)
    t3 = time.time()
    zn = FS.z_for(ctx, specs, new_box)
    rec["seconds_z_new"] = round(time.time() - t3, 2)
    rec["Z_new_vs_reference"] = {f"{ch}_{s}": PC.compare(zn[(s, ch)], Zr[(s, ch)][new_box]) for s, ch in LL.FORM_SPECS}

    # F: the inputs of the new pool matches from the saved z
    Zs = {}
    for k in LL.FORM_SPECS:
        z = np.array(Zr[k], copy=True)
        z[new_box] = np.nan                                  # the state holds z up to D0 only
        z[new_box] = zn[k]
        Zs[k] = z
    t4 = time.time()
    fn = FS.step3_for(ctx, specs, chosen, Zs, new_pool)
    rec["seconds_step3_new"] = round(time.time() - t4, 2)
    rec["F_new_vs_reference"] = {col: PC.compare(fn[col], feats_r[col][new_pool]) for col in feats_r}
    rec["F_new_vs_stored_float32"] = {col: PC.compare(np.asarray(fn[col], dtype="float32"),
                                                      stored[col].to_numpy()[new_pool]) for col in feats_r}
    rec["seconds_total"] = round(time.time() - t0, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    PC.write_json(OUT / "verify.json", rec)
    bz = sum(r["bitwise_equal"] == r["rows"] for r in rec["Z_new_vs_reference"].values())
    bf = sum(r["bitwise_equal"] == r["rows"] for r in rec["F_new_vs_reference"].values())
    PC.log(f"Z: {bz} of 17 pairs bitwise on {len(new_box):,} new box rows ({rec['seconds_z_new']} s); "
           f"F: {bf} of 17 inputs bitwise on {len(new_pool):,} pool matches ({rec['seconds_step3_new']} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
