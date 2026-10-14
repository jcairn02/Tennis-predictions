"""The surface IOS (21 inputs, 14 solver runs) with a saved solver state (PLAN.md section 3.3, "ios/").

The solver and its state: the plan's prototype (prediction_pipeline/ios_state.py: Setup, Snap, run_days, outputs),
imported unchanged; it copies the decided loops' arithmetic in the same order. What this module adds:
    the solver's cache    build_cache.py's arrays (the same calls, the same order) plus each row's stable keys (match
                          id, side, player id): the cache's player codes are pd.factorize codes of one table, so a state
                          saved on one table can only be moved onto another by player id
    the checkpoint        after the last snapshot day on or before the checkpoint day: the running sums, the last
                          solution (warm start), the observations released so far; the in-flight rows' snapshot values
                          (rows queried by then, released after: the gap step reads them later), keyed by match and side;
                          the system's active players by id and its (server, returner, surface) triples by ids
    the move              onto today's system: players and triples matched by id, new ones at zero; an old player or
                          triple missing from today's system is allowed only where every saved sum and solution entry of
                          it is zero (nothing of it was released by the checkpoint day)
    the slice             every observation released by the checkpoint day (in the system's order: server and returner
                          ids, surface, value, units, the layer's weight and level code, best-estimate day, release day),
                          the snapshot days up to it, and every in-flight row's own data
Resumed on the table it was saved from, the run is the full run bit for bit (the prototype's check B). Moved onto
another day's system, the iterates drift at rounding level and each day's solve stops inside its tolerance: within
5.3e-8 in the prototype's check C; the owner's bar is 1e-6.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

from dp_hash import hash_arrays, hash_value

PROFILE = ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved")
RUNS = [(t, s) for t in ("atp", "wta") for s in PROFILE]


def _mods():
    from src.eda.lower_level_evidence import level_layer_ios as LLEIOS
    from src.eda.surface_ios import ios_surface as IS
    import ios_state as I                          # the prototype (prediction_pipeline), unchanged
    return LLEIOS, IS, I


# ------------------------------------------------------------------------------------------------
# The cache (build_cache.main's arrays, with keys)

def build_cache() -> tuple[dict, pd.DataFrame]:
    """{tour: td (as surface_ios/common.load_tour returns it) with keys}, and the pool (match id, tour, pos_a, pos_b),
    from the tree's tables, as surface_ios/build_cache.py builds them."""
    from src.eda.lower_level_evidence import level_layer_ios as _LLEIOS
    from src.eda.match_timing import common as MT
    from src.eda.match_timing import rebuild as RB
    from src.eda.predictability_diagnostic import common as PC
    from src.eda.surface_ios import common as C
    from src.eda.ufc_ideas import stageB_common as B
    rows, n_matches, _ = RB.load_full_rows()
    means = B.surface_means()
    sa = B.stat_arrays(rows, means, C.STATS)
    timing = pd.read_parquet(MT.TIMING, columns=["match_id", "es", "lf", "obs"]).set_index("match_id")
    mid = rows["match_id"].to_numpy()
    es = rows["match_id"].map(timing["es"]).to_numpy(dtype="float64")
    lf = rows["match_id"].map(timing["lf"]).to_numpy(dtype="float64")
    obs = rows["match_id"].map(timing["obs"]).to_numpy(dtype="float64")
    if not (np.isfinite(es).all() and np.isfinite(lf).all() and np.isfinite(obs).all()):
        raise ValueError("every match needs es, lf and obs in timing.parquet")
    if np.any(lf < es):
        raise ValueError("an inverted window in timing.parquet")
    surf = rows["surf"].to_numpy().astype("int64")
    pos = np.full(len(rows), -1, dtype=np.int64)
    out = {}
    for t in PC.TOURS:
        idx = np.flatnonzero(rows["tour"].to_numpy() == t)
        if len(idx) % 2 or not (mid[idx[0::2]] == mid[idx[1::2]]).all():
            raise ValueError("a tour's rows must come in A, B pairs")
        pos[idx] = np.arange(len(idx))
        pid = pd.factorize(rows["pcode"].to_numpy()[idx])[0].astype(np.int64)
        arrays = {"row": idx.astype(np.int64), "pid": pid, "n_players": np.int64(pid.max() + 1),
                  "day": rows["day"].to_numpy()[idx].astype(np.int64), "ev": rows["ev"].to_numpy()[idx].astype(np.int64),
                  "round_order": rows["round_order"].to_numpy()[idx].astype(np.int64), "surf": surf[idx],
                  "year": rows["year"].to_numpy()[idx].astype(np.int64),
                  "evaluation": rows["evaluation"].to_numpy()[idx].astype(bool),
                  "eval_level": rows["eval_level"].to_numpy()[idx].astype(bool),
                  "level_main": rows["level"].isin(["GS", "FIN", "T1000", "T500", "T250"]).to_numpy()[idx],
                  "es": es[idx], "lf": lf[idx], "obs": obs[idx]}
        for s in C.STATS:
            a = sa[s]
            arrays[f"{s}__ok"] = a["ok"][idx]
            arrays[f"{s}__x"] = a["x"][idx]
            arrays[f"{s}__d"] = a["d"][idx]
            arrays[f"{s}__y"] = a["c"][idx]
            arrays[f"{s}__mu"] = a["mu_scale"][idx]
        arrays = _LLEIOS.annotate_cache(arrays, rows, idx)
        # C.load_tour's shape of the arrays (np.savez / np.load leave the values as they are)
        d = dict(arrays)
        d["stats"] = {s: {"ok": d.pop(f"{s}__ok"), "x": d.pop(f"{s}__x"), "d": d.pop(f"{s}__d"), "y": d.pop(f"{s}__y"),
                          "mu": d.pop(f"{s}__mu")} for s in C.STATS}
        d["n_players"] = int(d["n_players"])
        d["tour"] = t
        d["key_match"] = np.asarray(mid[idx], dtype=str)
        d["key_side"] = np.asarray(rows["side"].to_numpy()[idx], dtype=str)
        d["key_player"] = np.asarray(rows["player_id"].to_numpy()[idx], dtype=str)
        d["key_event"] = np.asarray(rows["tournament_id"].astype(str).to_numpy()[idx] + "|"
                                    + rows["tournament_date"].astype(str).to_numpy()[idx], dtype=str)
        out[t] = d
    A, Bi = B.pool_rows(rows)
    pool = pd.DataFrame({"match_id": mid[A], "tour": rows["tour"].to_numpy()[A], "surf": surf[A],
                         "year": rows["year"].to_numpy()[A], "pos_a": pos[A], "pos_b": pos[Bi]})
    if (pool[["pos_a", "pos_b"]] < 0).any().any() or not (pool["pos_b"] == pool["pos_a"] + 1).all():
        raise ValueError("pool rows do not map onto the tour arrays")
    return out, pool


def save_cache(path: Path, cache: dict) -> None:
    """The tours' arrays in one npz (no pickles), for worker processes."""
    flat = {}
    for t, td in cache.items():
        for k, v in td.items():
            if k == "stats":
                for s, d in v.items():
                    for kk, vv in d.items():
                        flat[f"{t}::stats::{s}::{kk}"] = vv
            elif k == "tour":
                continue
            else:
                a = np.asarray(v)
                flat[f"{t}::{k}"] = a.astype(str) if a.dtype == object else a
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, **flat)


def load_cache(path: Path, tours=("atp", "wta")) -> dict:
    out = {t: {"stats": {}, "tour": t} for t in tours}
    with np.load(path, allow_pickle=False) as z:
        for key in z.files:
            parts = key.split("::")
            t = parts[0]
            if t not in out:
                continue
            if parts[1] == "stats":
                out[t]["stats"].setdefault(parts[2], {})[parts[3]] = z[key]
            else:
                out[t][parts[1]] = z[key]
    for t in out:
        out[t]["n_players"] = int(out[t]["n_players"])
    return out


def cache_equals_tree(td: dict, tour: str) -> dict:
    """This cache's arrays against the tree's own cache/{tour}.npz (built by build_cache.py): every array bitwise."""
    from src.eda.surface_ios import common as C
    ref = C.load_tour(tour)
    bad = []
    for k, v in ref.items():
        if k == "stats":
            for s, d in v.items():
                for kk, vv in d.items():
                    if not np.array_equal(np.asarray(vv), np.asarray(td["stats"][s][kk]), equal_nan=True):
                        bad.append(f"{s}.{kk}")
        elif isinstance(v, np.ndarray):
            if not np.array_equal(v, np.asarray(td[k]), equal_nan=(v.dtype.kind == "f")):
                bad.append(k)
        elif v != td[k]:
            bad.append(k)
    return {"tour": tour, "arrays_differing": bad}


# ------------------------------------------------------------------------------------------------
# One run's setup, its checkpoint day and slice

def setup(td: dict, stat: str):
    _, _, I = _mods()
    return I.make_setup(td, stat, "surface")


def day_index(s, d0: int) -> int:
    """The checkpoint's snapshot day: the last one BEFORE d0 (-1: none). The checkpoint covers everything before the
    checkpoint day, as the Elo passes' (tournament weeks before d0) and the forms' (box rows of weeks before d0): a row
    queried on d0 or later is resumed."""
    return int(np.searchsorted(s.days, float(d0), side="left")) - 1


def inflight(s, day: float) -> np.ndarray:
    _, _, I = _mods()
    return I.inflight_rows(s, float(day))


def slice_hash(s, d0: int) -> str:
    """The arrays the state at the last snapshot day <= d0 read, and the in-flight rows' own data."""
    i0 = day_index(s, d0)
    day = float(s.days[i0]) if i0 >= 0 else float("-inf")
    sysm, td = s.sysm, s.td
    n_rel = int(np.searchsorted(sysm.release, day, side="right"))
    rk = sysm.rows[:n_rel]
    kp = td["key_player"]
    named = {"srv": kp[rk], "ret": kp[rk ^ 1], "match": td["key_match"][rk], "side": td["key_side"][rk],
             "surf": sysm.surf[:n_rel], "y": sysm.y[:n_rel], "d": sysm.d[:n_rel], "m": sysm.m[:n_rel],
             "obs": sysm.obs[:n_rel], "release": sysm.release[:n_rel],
             "fe": (s.fe[:n_rel] if s.mode == "fe" else np.zeros(0, dtype=np.int64)),
             "days": s.days[:i0 + 1]}
    fl = inflight(s, day) if i0 >= 0 else np.zeros(0, dtype=np.int64)
    st = td["stats"][s.stat]
    named.update({"fl_match": td["key_match"][fl], "fl_side": td["key_side"][fl], "fl_player": kp[fl],
                  "fl_query": s.query[fl], "fl_release": s.release[fl], "fl_obs": td["obs"][fl],
                  "fl_day": td["day"][fl], "fl_event": td["key_event"][fl], "fl_round": td["round_order"][fl],
                  "fl_surf": td["surf"][fl], "fl_y": st["y"][fl], "fl_d": st["d"][fl], "fl_ok": st["ok"][fl],
                  "fl_mult": s.mult[fl], "fl_delta": s.delta[fl],
                  "fl_fe": (s.fe_code[fl] if s.fe_code is not None else np.zeros(0, dtype=np.int64)),
                  "fl_opp_match": td["key_match"][fl ^ 1], "fl_opp_player": kp[fl ^ 1]})
    consts = {"h": s.h, "kappa": s.kappa, "kappa_s": list(s.kappa_s) if isinstance(s.kappa_s, tuple) else s.kappa_s,
              "tau": s.tau, "typ": s.typ, "mode": s.mode, "n_fe": s.n_fe}
    named["constants"] = np.asarray([hash_value(consts)])
    return hash_arrays(named, tag=f"dp/ios/{s.tour}/{s.stat}/v1")


def triple_positions(s) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Each triple of the system as (server's position, returner's position, surface): positions in the system's
    player order (active_ids)."""
    sysm = s.sysm
    srv = np.empty(sysm.n_triples, dtype=np.int64)
    ret = np.empty(sysm.n_triples, dtype=np.int64)
    sur = np.empty(sysm.n_triples, dtype=np.int64)
    srv[sysm.triple] = sysm.srv
    ret[sysm.triple] = sysm.ret
    sur[sysm.triple] = sysm.surf
    return srv, ret, sur


def active_ids(s) -> np.ndarray:
    """The system's players by id, in the system's order (sysm.active are cache codes)."""
    td = s.td
    first = np.full(int(td["n_players"]), -1, dtype=np.int64)
    first[td["pid"][::-1]] = np.arange(len(td["pid"]))[::-1]
    return td["key_player"][first[s.sysm.active]]


# ------------------------------------------------------------------------------------------------
# Checkpoint files

def save(path: Path, s, state: dict, rows: dict) -> dict:
    _, _, I = _mods()
    day = float(state["day"])
    fl = inflight(s, day)
    payload = {f"st_{k}": v for k, v in state.items()}
    payload.update({f"row_{k}": rows[k][fl] for k in I.ROW_KEYS})
    payload["row_match"] = s.td["key_match"][fl]
    payload["row_side"] = s.td["key_side"][fl]
    payload["active_ids"] = active_ids(s)
    srv, ret, sur = triple_positions(s)
    payload["triple_srv"], payload["triple_ret"] = srv.astype(np.int32), ret.astype(np.int32)
    payload["triple_surf"] = sur.astype(np.int8)
    payload["n_fe"] = np.int64(s.n_fe)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **payload)
    return {"inflight_rows": int(len(fl)), "bytes": int(os.path.getsize(path)), "day": day}


def load(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:            # closed at once (Windows keeps an open npz locked)
        return {k: z[k] for k in z.files}


def move(z: dict, s) -> dict:
    """A saved state moved onto today's system s (players and triples by id)."""
    _, IS, _ = _mods()
    S = IS.S
    sysm = s.sysm
    n_new = sysm.n
    old_ids = z["active_ids"]
    new_ids = active_ids(s)
    new_pos = pd.Index(new_ids)
    if new_pos.has_duplicates:
        raise ValueError("a player id appears twice in today's system")
    pos = new_pos.get_indexer(old_ids)
    st = {k[3:]: v for k, v in z.items() if k.startswith("st_")}
    n_old = len(old_ids)
    nfe_old = int(z["n_fe"])
    if s.mode == "fe" and s.n_fe != nfe_old:
        raise ValueError(f"the level effects differ: saved {nfe_old}, today {s.n_fe}")
    xo = st["x"]
    gone = pos < 0
    if gone.any():                                      # allowed only for players with nothing released yet
        cols = np.flatnonzero(gone)
        Eo = xo[2 * n_old:2 * n_old + n_old * S].reshape(S, n_old)
        Fo = xo[2 * n_old + n_old * S:2 * n_old + 2 * n_old * S].reshape(S, n_old)
        parts = [st[k][cols] for k in ("Pc", "Qc", "bOc", "bDc")]
        parts += [st[k][:, cols] for k in ("Psc", "Qsc", "bEc", "bFc")]
        parts += [xo[:n_old][cols], xo[n_old:2 * n_old][cols], Eo[:, cols], Fo[:, cols]]
        if s.mode == "fe":
            parts += [st["PLc"][cols], st["QLc"][cols], st["PsLc"][:, cols], st["QsLc"][:, cols]]
        zero = all(bool(np.all(p == 0)) for p in parts)
        if not zero:
            raise ValueError(f"{int(gone.sum())} saved players with released data are not in today's system")
    keep = ~gone
    p_new = pos[keep]
    out = {}
    for k in ("Pc", "Qc", "bOc", "bDc"):
        v = np.zeros(n_new)
        v[p_new] = st[k][keep]
        out[k] = v
    for k in ("Psc", "Qsc", "bEc", "bFc"):
        v = np.zeros((S + 1, n_new))
        v[:, p_new] = st[k][:, keep]
        out[k] = v
    # triples: the saved (server, returner, surface) positions -> ids -> today's positions -> today's triple index
    srv_n, ret_n, sur_n = triple_positions(s)
    key_new = (srv_n * n_new + ret_n) * (S + 1) + sur_n
    ps_o = pos[z["triple_srv"].astype(np.int64)]
    pr_o = pos[z["triple_ret"].astype(np.int64)]
    ok_t = (ps_o >= 0) & (pr_o >= 0)
    key_old = np.where(ok_t, (ps_o * n_new + pr_o) * (S + 1) + z["triple_surf"].astype(np.int64), -1)
    tpos = pd.Index(key_new).get_indexer(key_old)
    tpos[~ok_t] = -1
    tgone = tpos < 0
    if tgone.any() and np.any(st["TWc"][tgone] != 0):
        raise ValueError(f"{int((tgone & (st['TWc'] != 0)).sum())} saved triples with released weight are not in "
                         "today's system")
    v = np.zeros(sysm.n_triples)
    v[tpos[~tgone]] = st["TWc"][~tgone]
    out["TWc"] = v
    if s.mode == "fe":
        nL = s.n_fe
        for k in ("PLc", "QLc"):
            v = np.zeros((n_new, nL))
            v[p_new] = st[k][keep]
            out[k] = v
        for k in ("PsLc", "QsLc"):
            v = np.zeros((S + 1, n_new, nL))
            v[:, p_new] = st[k][:, keep]
            out[k] = v
        out["SLc"], out["bBc"] = st["SLc"].copy(), st["bBc"].copy()
    x = np.zeros(2 * n_new + 2 * n_new * S + (s.n_fe if s.mode == "fe" else 0))
    x[p_new] = xo[:n_old][keep]
    x[n_new + p_new] = xo[n_old:2 * n_old][keep]
    Eo = xo[2 * n_old:2 * n_old + n_old * S].reshape(S, n_old)
    Fo = xo[2 * n_old + n_old * S:2 * n_old + 2 * n_old * S].reshape(S, n_old)
    E = np.zeros((S, n_new))
    F = np.zeros((S, n_new))
    E[:, p_new], F[:, p_new] = Eo[:, keep], Fo[:, keep]
    x[2 * n_new:2 * n_new + n_new * S] = E.reshape(-1)
    x[2 * n_new + n_new * S:2 * n_new + 2 * n_new * S] = F.reshape(-1)
    if s.mode == "fe":
        x[2 * n_new + 2 * n_new * S:] = xo[2 * n_old + 2 * n_old * S:]
    out["x"] = x
    for k in ("ptr", "i", "day"):
        out[k] = st[k]
    return out


def resume(z: dict, s, upto: int | None = None):
    """Today's snapshot loop resumed from a saved state (moved onto today's system), with the saved in-flight rows'
    snapshot values put on today's rows. Returns (snap, rows, record)."""
    _, _, I = _mods()
    st = move(z, s)
    snap = I.Snap.from_state(s, st)
    rows = I.empty_rows(s)
    keys = pd.MultiIndex.from_arrays([s.td["key_match"], s.td["key_side"]])
    want = pd.MultiIndex.from_arrays([z["row_match"].astype(str), z["row_side"].astype(str)])
    pos = keys.get_indexer(want)
    if (pos < 0).any():
        raise ValueError(f"{int((pos < 0).sum())} saved in-flight rows are not in today's table")
    for k in I.ROW_KEYS:
        rows[k][pos] = z[f"row_{k}"]
    fl_today = inflight(s, float(st["day"]))
    if not np.array_equal(np.sort(fl_today), np.sort(pos)):
        raise ValueError("today's in-flight rows at the checkpoint day differ from the saved ones")
    rec = I.run_days(snap, rows, upto=upto)
    return snap, rows, rec


def full(s, checkpoint_day: int | None = None, upto: int | None = None):
    """The run from day 0 (the decided arithmetic through the prototype's copy), optionally keeping the state after the
    last snapshot day <= checkpoint_day. Returns (snap, rows, record, state or None)."""
    _, _, I = _mods()
    snap = I.Snap(s)
    rows = I.empty_rows(s)
    state = None
    if checkpoint_day is not None:
        i0 = day_index(s, checkpoint_day)
        rec1 = I.run_days(snap, rows, upto=i0)
        state = snap.state()
        rec2 = I.run_days(snap, rows, upto=upto)
        rec = {"days": rec1["days"] + rec2["days"], "seconds": round(rec1["seconds"] + rec2["seconds"], 2),
               "not_converged": rec1["not_converged"] + rec2["not_converged"]}
    else:
        rec = I.run_days(snap, rows, upto=upto)
    return snap, rows, rec, state


def outputs(s, rows: dict, targets: np.ndarray) -> dict:
    _, _, I = _mods()
    return I.outputs(s, rows, np.asarray(targets, dtype=np.int64))


def last_day_index(s, targets: np.ndarray) -> int:
    """The last snapshot day the targets' gap steps need (their own query days; predecessors' are earlier)."""
    q = s.query[np.asarray(targets, dtype=np.int64)]
    return int(np.searchsorted(s.days, q.max(), side="left")) if len(q) else -1


def worker(args: dict) -> dict:
    """One run in a worker process (sys.path and LLE_LAYER inherited; BLAS single-threaded, as build_features.py runs
    its workers). mode "checkpoint": from day 0 to the checkpoint, saved to args["out"]; "resume": from the saved state
    args["ck"] if today's slice equals args["expect"] (else marked invalid); "full": from day 0. Then the outputs of the
    target rows (positions in the tour's arrays)."""
    import time
    tour, stat, mode, d0 = args["tour"], args["stat"], args["mode"], int(args["d0"])
    td = load_cache(Path(args["cache"]), (tour,))[tour]
    s = setup(td, stat)
    targets = np.asarray(args.get("targets", []), dtype=np.int64)
    res = {"tour": tour, "stat": stat, "mode": mode, "slice": slice_hash(s, d0), "setup": s.info}
    t0 = time.time()
    if mode == "checkpoint":
        _, rows, rec, state = full(s, checkpoint_day=d0, upto=day_index(s, d0))
        res["checkpoint"] = save(Path(args["out"]), s, state, rows)
    elif mode == "resume":
        if args.get("expect") != res["slice"]:
            res["invalid"] = True
            return res
        _, rows, rec = resume(load(Path(args["ck"])), s, upto=last_day_index(s, targets))
    elif mode == "full":
        _, rows, rec, _ = full(s, upto=last_day_index(s, targets))
    else:
        raise ValueError(mode)
    res["record"] = rec
    if len(targets) and mode != "checkpoint":
        out = outputs(s, rows, targets)
        res["out"] = {k: out[k] for k in ("rows", "O_eff", "D_eff", "O", "D", "E", "F")}
    res["seconds"] = round(time.time() - t0, 2)
    return res


def run_workers(jobs: list[dict], workers: int) -> list[dict]:
    """The jobs in worker processes with single-threaded BLAS (the parent's own BLAS is left as it is)."""
    from concurrent.futures import ProcessPoolExecutor
    keep = {v: os.environ.get(v) for v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS")}
    for v in keep:
        os.environ[v] = "1"
    try:
        with ProcessPoolExecutor(max_workers=max(1, min(workers, len(jobs)))) as ex:
            return list(ex.map(worker, jobs))
    finally:
        for v, old in keep.items():
            if old is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = old


def match_inputs(td: dict, out: dict, rows_a: np.ndarray, stat: str) -> dict:
    """The three model inputs of a statistic for pool matches whose A rows (positions in the tour's arrays) are rows_a;
    `out` holds O_eff / D_eff for target rows covering rows_a and rows_a + 1 (surface_ios/arms.recipe)."""
    pos = pd.Index(out["rows"])
    ia, ib = pos.get_indexer(rows_a), pos.get_indexer(np.asarray(rows_a) + 1)
    if (ia < 0).any() or (ib < 0).any():
        raise ValueError("a pool match's row is not among the targets")
    oa, ob = out["O_eff"][ia], out["O_eff"][ib]
    da, db = out["D_eff"][ia], out["D_eff"][ib]
    return {f"iosO_{stat}": oa - ob, f"iosD_{stat}": da - db, f"prod_{stat}": oa * (-db) - ob * (-da)}
