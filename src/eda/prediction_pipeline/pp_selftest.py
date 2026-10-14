"""Fast self-checks of the saved-state logic on a build tree (docs/studies/prediction_pipeline/), for the tests.

Each check runs in its own process (the tests call this file), because it imports the build tree's code:
    ios      the surface IOS on the 2025-2026 rows of one tour and statistic: the full run against a checkpoint saved to
             disk, loaded and resumed (bitwise); and a checkpoint made on an older slice (rows finished before D0 + 21)
             moved onto the full slice's system (within 1e-6)
    elo      the offset Elo pass on the 2024-2026 matches of one tour: unbroken against pickled and resumed (bitwise),
             and against a state from an older table with other player codes, remapped (bitwise)
    kahan    pandas' grouped cumulative sums are compensated (the reason Stages B and 4 recompute the day's players
             instead of resuming running totals)
Exit 0 when every assertion holds; prints one JSON line.
Run: ./python.sh src/eda/prediction_pipeline/pp_selftest.py ios|elo|kahan [--tree <build tree>]
"""
from __future__ import annotations

import os
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pp_common as PC  # noqa: E402


def check_kahan() -> dict:
    v = np.array([1e16, 1.0, 1.0, 1.0, 1.0, -1e16, 3.0])
    cs = pd.DataFrame({"v": v}).groupby(np.zeros(len(v), dtype=int)).cumsum()["v"].to_numpy()
    naive = np.add.accumulate(v)
    assert cs[-1] == 7.0 and naive[-1] == 3.0, (cs, naive)
    return {"groupby_cumsum_last": float(cs[-1]), "naive_last": float(naive[-1])}


def check_ios(tree: Path, tour: str = "wta", stat: str = "ace") -> dict:
    PC.use_tree(tree)
    PC.set_layer(tree)
    import ios_state as I
    import verify_ios_state as V
    from src.eda.surface_ios import common as SC
    td = V.subset(SC.load_tour(tour), SC.load_tour(tour)["year"] >= 2025)
    s = I.make_setup(td, stat, "surface")
    d0 = float(s.days[int(np.searchsorted(s.days, s.days[-1] - 21, side="right")) - 1])
    cps = {d0: None}
    out, rows, _ = I.full_run(s, checkpoints=cps)
    targets = np.flatnonzero(s.query > d0)
    with tempfile.TemporaryDirectory() as tmp:
        ck = Path(tmp) / "ck.npz"
        I.save_checkpoint(ck, s, cps[d0], rows)
        with np.load(ck) as zf:
            z = {k: zf[k] for k in zf.files}
    s2 = I.make_setup(td, stat, "surface")
    snap = I.Snap.from_state(s2, {k[3:]: v for k, v in z.items() if k.startswith("st_")})
    r2 = I.empty_rows(s2)
    for k in I.ROW_KEYS:
        r2[k][z["row_index"]] = z[f"row_{k}"]
    I.run_days(snap, r2)
    ob = I.outputs(s2, r2, targets)
    same = all(np.array_equal(ob[k], out[k][targets], equal_nan=True) for k in ("O_eff", "D_eff"))
    assert same, "resume differs from the full run"
    # an older slice's checkpoint moved onto the full slice's system
    keep = td["lf"] < d0 + 21 - 120                      # 120 days fewer: new players and triples appear later
    old = V.subset(td, keep)
    so = I.make_setup(old, stat, "surface")
    d1 = float(so.days[int(np.searchsorted(so.days, d0 - 120, side="right")) - 1])
    io = int(np.searchsorted(so.days, d1, side="left"))
    snap_o = I.Snap(so)
    rows_o = I.empty_rows(so)
    I.run_days(snap_o, rows_o, upto=io)
    st_o = snap_o.state()
    mapped = I.map_state(st_o, so.sysm.active, I.triple_keys(so), s2, so.n_fe)
    snap_c = I.Snap.from_state(s2, mapped)
    rows_c = I.empty_rows(s2)
    fl = I.inflight_rows(so, d1)
    for k in I.ROW_KEYS:
        rows_c[k][old["row_index"][fl]] = rows_o[k][fl]
    I.run_days(snap_c, rows_c)
    tg1 = np.flatnonzero(s2.query > d1)
    full1 = I.outputs(s2, rows, tg1)
    oc = I.outputs(s2, rows_c, tg1)
    cmp = {k: PC.compare(oc[k], full1[k]) for k in ("O_eff", "D_eff")}
    assert all(c["nan_pattern_equal"] for c in cmp.values()), "older table's checkpoint: missing values differ"
    gap = max(c["max_abs_diff"] for c in cmp.values())
    assert gap <= 1e-6, f"older table's checkpoint: {gap}"
    return {"tour": tour, "stat": stat, "resumed_rows": int(len(targets)), "bitwise": same,
            "older_table_rows": int(len(tg1)), "older_table_max_abs_diff": gap,
            "players_old_new": [int(so.sysm.n), int(s2.sysm.n)]}


def check_elo(tree: Path, tour: str = "atp") -> dict:
    PC.use_tree(tree)
    PC.set_layer(tree)
    import elo_state as ES
    from src.eda.lower_level_evidence import level_layer as LLE
    from src.eda.predictability_diagnostic import stage1_baselines as B
    from src.eda.surface_elo_pieces import common as C
    from src.eda.surface_elo_pieces import pieces as PI
    m = pd.read_parquet(C.STAGE0, columns=PI.STAGE0_COLS)
    t = m[m["tour"].eq(tour) & m["year"].ge(2024)].reset_index(drop=True)
    meta = json.loads((C.OUT / "pieces_meta.json").read_text(encoding="utf-8"))
    chosen = {(c["tour"], c["rule"]): c for c in json.loads(C.STAGE1_SUMMARY.read_text())["chosen"]}
    k = {kk: float(chosen[(tour, "ret")][kk]) for kk in ("k0", "offset", "shape")}
    kd = meta["offset_constants"][tour]

    def args_of(frame):
        h = B.history_arrays(frame)
        upd = LLE.elo_weights(frame, frame["status"].isin(B.UPDATES["ret"]).tolist())
        players = np.unique(np.concatenate([frame["player_a_id"].to_numpy(), frame["player_b_id"].to_numpy()]))
        return h, (h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"], upd), list(players)
    h, args, players = args_of(t)
    full, _ = ES.elo_pass_ext_resumable(*args, ES.new_state(h["n_players"], "offset"), k["k0"], k["offset"], k["shape"],
                                        mode="offset", **kd)
    wk = np.asarray(h["week"])
    d0 = int(np.datetime64("2026-03-02", "D").astype("int64"))
    i0 = int(np.searchsorted(wk, d0, side="left"))
    p1 = tuple(np.asarray(x)[:i0].tolist() for x in args)
    p2 = tuple(np.asarray(x)[i0:].tolist() for x in args)
    _, st = ES.elo_pass_ext_resumable(*p1, ES.new_state(h["n_players"], "offset"), k["k0"], k["offset"], k["shape"],
                                      mode="offset", **kd)
    with tempfile.TemporaryDirectory() as tmp:
        ES.save(Path(tmp) / "s.pkl", st, players)
        st2, _ = ES.load(Path(tmp) / "s.pkl")
    out2, _ = ES.elo_pass_ext_resumable(*p2, st2, k["k0"], k["offset"], k["shape"], mode="offset", **kd)
    assert np.array_equal(out2, full[i0:], equal_nan=True), "resume differs"
    old = t[t["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64") < d0 + 21].reset_index(drop=True)
    ho, args_o, players_o = args_of(old)
    io = int(np.searchsorted(np.asarray(ho["week"]), d0, side="left"))
    _, st_o = ES.elo_pass_ext_resumable(*(np.asarray(x)[:io].tolist() for x in args_o),
                                        ES.new_state(ho["n_players"], "offset"), k["k0"], k["offset"], k["shape"],
                                        mode="offset", **kd)
    out3, _ = ES.elo_pass_ext_resumable(*p2, ES.remap(st_o, players_o, players), k["k0"], k["offset"], k["shape"],
                                        mode="offset", **kd)
    assert np.array_equal(out3, full[i0:], equal_nan=True), "remapped resume differs"
    return {"tour": tour, "matches_resumed": int(len(wk) - i0), "players_old_new": [len(players_o), len(players)],
            "bitwise": True}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("check", choices=("ios", "elo", "kahan"))
    ap.add_argument("--tree", default=str(PC.TREE))
    a = ap.parse_args()
    tree = Path(a.tree)
    res = {"ios": lambda: check_ios(tree), "elo": lambda: check_elo(tree), "kahan": check_kahan}[a.check]()
    print(json.dumps(res, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
