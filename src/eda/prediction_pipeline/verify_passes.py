"""Verify the Elo-type passes' saved state, and time the sequential passes (docs/studies/prediction_pipeline/).

On the build tree's Stage 0 (default: the sandbox of the current best model of 10 Oct 2026), with the level layer's
result weights as the build ran them, per tour:

    A  fidelity      the offset Elo pass (pieces.elo_pass_ext, mode "offset", the build's constants) through this
                     study's resumable copy, against the tree's pieces.parquet (R, N, S, NS, D for A and B)
    B  same table    the pass run to the first match of D0's week, its state pickled and loaded, then resumed: every
                     later match against the unbroken pass
    C  older table   the state made on an older table (matches of tournament weeks before T = D0 + 21 days only, so
                     different player codes), moved onto today's players and resumed: against the unbroken pass
    T  time          the whole pass, and the decided Stage 1 pass (the layer's opponent strength) and Stage 3 pass, per
                     tour: what recomputing them in full costs a daily update

Writes data/studies/prediction_pipeline/passes/verify.json. Reads only.
Run: ./python.sh src/eda/prediction_pipeline/verify_passes.py [--d0 2026-09-14]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pp_common as PC  # noqa: E402

OUT = PC.OUT / "passes"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--d0", default=None)
    ap.add_argument("--tree", default=str(PC.TREE))
    a = ap.parse_args()
    PC.use_tree(Path(a.tree))
    PC.set_layer(Path(a.tree))
    import elo_state as ES
    from src.eda.lower_level_evidence import level_layer as LLE
    from src.eda.predictability_diagnostic import stage1_baselines as B
    from src.eda.predictability_diagnostic import stage3_ratings as S3
    from src.eda.surface_elo_pieces import common as C
    from src.eda.surface_elo_pieces import pieces as PI

    OUT.mkdir(parents=True, exist_ok=True)
    rec = {"tree": a.tree, "layer_config": str(PC.layer_config(Path(a.tree)))}
    m = pd.read_parquet(C.STAGE0, columns=PI.STAGE0_COLS)
    pieces = pd.read_parquet(C.PIECES)
    if not np.array_equal(pieces["match_id"].to_numpy(), m["match_id"].to_numpy()):
        raise RuntimeError("pieces.parquet is not in Stage 0's order")
    meta = json.loads((C.OUT / "pieces_meta.json").read_text(encoding="utf-8"))
    chosen = {(c["tour"], c["rule"]): c for c in json.loads(C.STAGE1_SUMMARY.read_text())["chosen"]}
    week_all = m["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    last = int(week_all.max())
    d0 = int(np.datetime64(a.d0, "D").astype("int64")) if a.d0 else last - 21
    rec["d0"] = str(np.datetime64(d0, "D"))
    cols = ["R_a", "R_b", "N_a", "N_b", "S_a", "S_b", "NS_a", "NS_b", "D_a", "D_b"]
    for tour in C.TOURS:
        r = {}
        sel = m["tour"].eq(tour).to_numpy()
        t = m[sel].reset_index(drop=True)
        h = B.history_arrays(t)
        upd0 = t["status"].isin(B.UPDATES["ret"]).tolist()
        upd = LLE.elo_weights(t, upd0)
        k = {kk: float(chosen[(tour, "ret")][kk]) for kk in ("k0", "offset", "shape")}
        kd = meta["offset_constants"][tour]
        players = np.unique(np.concatenate([t["player_a_id"].to_numpy(), t["player_b_id"].to_numpy()]))
        args = (h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"], upd)

        t0 = time.time()
        full, _ = ES.elo_pass_ext_resumable(*args, ES.new_state(h["n_players"], "offset"), k["k0"], k["offset"],
                                            k["shape"], mode="offset", **kd)
        r["seconds_full_pass"] = round(time.time() - t0, 2)
        ref = pieces.loc[sel, cols].to_numpy(dtype="float64")
        mine = full[:, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]]
        r["A_fidelity"] = {c: PC.compare(mine[:, j], ref[:, j]) for j, c in enumerate(cols)}

        # B: checkpoint at the first match of D0's week (Stage 0's order follows tournament weeks)
        wk = np.asarray(h["week"])
        i0 = int(np.searchsorted(wk, d0, side="left"))
        if not (np.diff(wk) >= 0).all():
            raise RuntimeError("weeks are not ascending in Stage 0's order")
        part1 = tuple(np.asarray(x)[:i0].tolist() for x in args)
        part2 = tuple(np.asarray(x)[i0:].tolist() for x in args)
        _, st = ES.elo_pass_ext_resumable(*part1, ES.new_state(h["n_players"], "offset"), k["k0"], k["offset"],
                                          k["shape"], mode="offset", **kd)
        path = OUT / f"{tour}_offset_state.pkl"
        ES.save(path, st, players)
        st2, _ = ES.load(path)
        t1 = time.time()
        out2, _ = ES.elo_pass_ext_resumable(*part2, st2, k["k0"], k["offset"], k["shape"], mode="offset", **kd)
        r["B_same_table"] = {"checkpoint_match_index": i0, "matches_resumed": int(len(wk) - i0),
                             "state_bytes": int(path.stat().st_size), "seconds_resume": round(time.time() - t1, 3),
                             **{c: PC.compare(out2[:, j], full[i0:, j]) for j, c in enumerate(cols)}}

        # C: the state from an older table (weeks before T only: other player codes), moved onto today's players
        T = d0 + 21
        old = t[t["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64") < T].reset_index(drop=True)
        ho = B.history_arrays(old)
        upd_o = LLE.elo_weights(old, old["status"].isin(B.UPDATES["ret"]).tolist())
        players_o = np.unique(np.concatenate([old["player_a_id"].to_numpy(), old["player_b_id"].to_numpy()]))
        io = int(np.searchsorted(np.asarray(ho["week"]), d0, side="left"))
        args_o = (ho["week"], ho["event"], ho["rnd"], ho["a"], ho["b"], ho["a_won"], ho["surf"], upd_o)
        _, st_o = ES.elo_pass_ext_resumable(*(np.asarray(x)[:io].tolist() for x in args_o),
                                            ES.new_state(ho["n_players"], "offset"), k["k0"], k["offset"], k["shape"],
                                            mode="offset", **kd)
        st_c = ES.remap(st_o, list(players_o), players)
        out3, _ = ES.elo_pass_ext_resumable(*part2, st_c, k["k0"], k["offset"], k["shape"], mode="offset", **kd)
        r["C_older_table"] = {"table_weeks_before": str(np.datetime64(T, "D")), "matches_old": int(len(old)),
                              "players_old": int(len(players_o)), "players_new": int(len(players)),
                              **{c: PC.compare(out3[:, j], full[i0:, j]) for j, c in enumerate(cols)}}

        # T: the decided Stage 1 pass (plain: the layer's strength) and Stage 3's pass, whole history
        t2 = time.time()
        B.run_elo(h, t["status"], "ret", {**k}, surface=True)
        r["seconds_stage1_pass"] = round(time.time() - t2, 2)
        rec[tour] = r
        PC.log(f"{tour}: full pass {r['seconds_full_pass']} s; A {sum(v['bitwise_equal'] == v['rows'] for v in r['A_fidelity'].values())}/10 "
               f"bitwise; B {sum(v['bitwise_equal'] == v['rows'] for k_, v in r['B_same_table'].items() if isinstance(v, dict))}/10; "
               f"C {sum(v['bitwise_equal'] == v['rows'] for k_, v in r['C_older_table'].items() if isinstance(v, dict))}/10; "
               f"resume {r['B_same_table']['seconds_resume']} s; stage 1 pass {r['seconds_stage1_pass']} s")
    # Stage 3's pass (ratings_iid), its decided arrays with the layer's weights
    t3 = time.time()
    hist = S3.load_history()
    means = S3.surface_means(hist)
    mu = S3.mu_of(hist, means)
    rec["seconds_stage3_load"] = round(time.time() - t3, 1)
    summ = json.loads((S3.C.OUT / "stage3_ratings_summary.json").read_text(encoding="utf-8"))
    chosen3 = summ.get("chosen") or summ.get("constants")
    for tour in ("atp", "wta"):
        sel = hist["tour"].eq(tour).to_numpy()
        hh = S3.arrays(hist[sel].reset_index(drop=True), mu[sel])
        hh = LLE.ratings_arrays(hist[sel].reset_index(drop=True), hh)
        kk = chosen3[tour] if isinstance(chosen3, dict) else None
        if kk is None:
            rec[f"stage3_{tour}"] = "constants not found in the summary"
            continue
        t4 = time.time()
        S3.run(hh, kk)
        rec[f"seconds_stage3_pass_{tour}"] = round(time.time() - t4, 2)
    PC.write_json(OUT / "verify.json", rec)
    for f in OUT.glob("*_offset_state.pkl"):
        f.unlink(missing_ok=True)
    PC.log(json.dumps({k: v for k, v in rec.items() if k.startswith("seconds")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
