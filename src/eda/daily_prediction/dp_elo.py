"""The Elo-type passes with saved state (docs/studies/daily_prediction/; PLAN.md section 3.3, "elo/").

Three sequential passes reach the model's inputs:
    offset     the Elo pieces' pass (surface_elo_pieces/pieces.elo_pass_ext, mode "offset"): R and D give elo_overall and
               elo_surf_offset. Resumable loop: the plan's prototype (prediction_pipeline/elo_state.py), imported
    weighted   Stage 4's games- and points-weighted surface Elo (stage4_features.weighted_elo_pass, through
               elo_variants): elo_games. Resumable loop below, the decided body line for line
    stage3     Stage 3's serve and return ratings (stage3_ratings.rating_pass): ratings_iid reads each match's own
               values. Resumable loop below, the decided body line for line. Stage 4's loader reads the whole
               stage3_ratings.parquet, so a checkpoint also keeps the pass's outputs before its day, and the daily
               update writes the whole table back (the decided format, stage3_ratings.main)
Each pass runs per tour over Stage 0's order. Its state between two matches is every player's lists and the current
week's pending entries; resumed from a state saved at the first match of a tournament week, the arithmetic and its
order are the decided pass's, so the outputs equal one unbroken pass bit for bit. A state saved on an older table is
moved onto today's player codes by player id (codes are positions in the tour's sorted ids, so they shift when a
player sorting earlier appears).

The checkpoint of a tour and pass sits at i0, the first match of the checkpoint day's tournament week (weeks ascend in
Stage 0's order). Its slice: every array the pass read for the matches before i0, with match and player ids and event
keys in place of codes (dp_hash).
"""
from __future__ import annotations

import math
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from dp_hash import hash_arrays, hash_value

STAGE3_COLS = ["serve_a", "serve_b", "return_a", "return_b", "var_serve_a", "var_serve_b", "var_return_a",
               "var_return_b", "serve_pts_a", "serve_pts_b", "return_pts_a", "return_pts_b"]
OFFSET_COLS = ["R_a", "R_b", "N_a", "N_b", "S_a", "S_b", "NS_a", "NS_b", "D_a", "D_b"]
WEIGHTED_KINDS = ("games", "points")


def _mods():
    from src.eda.lower_level_evidence import level_layer as LLE
    from src.eda.predictability_diagnostic import stage1_baselines as B
    from src.eda.predictability_diagnostic import stage3_ratings as S3
    from src.eda.predictability_diagnostic import stage4_features as F
    return LLE, B, S3, F


# ------------------------------------------------------------------------------------------------
# The instance's constants (read from a tree's files; a checkpoint keeps them)

def constants(root: Path) -> dict:
    """Stage 1's chosen K (rule "ret": k0, offset, shape, w), the offset pass's K (pieces_meta.json) and Stage 3's chosen
    variances, from a tree's files."""
    import json
    pd_out = Path(root) / "data" / "studies" / "predictability_diagnostic"
    s1 = json.loads((pd_out / "stage1_baselines_summary.json").read_text(encoding="utf-8"))
    chosen = {c["tour"]: {k: float(c[k]) for k in ("k0", "offset", "shape", "w")} for c in s1["chosen"]
              if c["rule"] == "ret"}
    meta = json.loads((Path(root) / "data" / "studies" / "surface_elo_pieces" / "pieces_meta.json")
                      .read_text(encoding="utf-8"))
    s3 = json.loads((pd_out / "stage3_ratings_summary.json").read_text(encoding="utf-8"))
    return {"stage1": chosen, "offset": {t: {k: float(v) for k, v in d.items()} for t, d in meta["offset_constants"].items()},
            "stage3": {t: {k: float(v) for k, v in d.items()} for t, d in s3["chosen"].items()}}


def checkpoint_index(week, d0: int) -> int:
    w = np.asarray(week, dtype=np.int64)
    if len(w) and not (np.diff(w) >= 0).all():
        raise RuntimeError("tournament weeks do not ascend in the table's order")
    return int(np.searchsorted(w, int(d0), side="left"))


# ------------------------------------------------------------------------------------------------
# The resumable loops (the decided bodies; state in, state out)

def new_weighted_state(n: int) -> dict:
    _, B, _, _ = _mods()
    return {"R": [B.START] * n, "N": [0] * n, "RS": [[B.START] * n for _ in B.SURFACES],
            "NS": [[0] * n for _ in B.SURFACES], "lo": {}, "ls": {}, "cur": None}


def weighted_pass(week, event, rnd, a, b, a_won, surf, upd, weight, state: dict, k0: float, offset: float,
                  shape: float) -> tuple[np.ndarray, dict]:
    """stage4_features.weighted_elo_pass from `state`; returns (out, state after the last match)."""
    R, N, RS, NS, lo, ls, cur = (state[k] for k in ("R", "N", "RS", "NS", "lo", "ls", "cur"))
    out = np.full((len(week), 8), np.nan)
    for i in range(len(week)):
        if week[i] != cur:
            for (p, _), st in lo.items():
                R[p] += st[0] + st[3]
                N[p] += st[1] + st[4]
            for (p, _, s), st in ls.items():
                RS[s][p] += st[0] + st[3]
                NS[s][p] += st[1] + st[4]
            lo.clear()
            ls.clear()
            cur = week[i]
        e, r, s, pa, pb = event[i], rnd[i], surf[i], a[i], b[i]
        xa = lo.get((pa, e))
        if xa is None:
            xa = lo[(pa, e)] = [0.0, 0, r, 0.0, 0]
        elif xa[2] < r:
            xa[0] += xa[3]; xa[1] += xa[4]; xa[2] = r; xa[3] = 0.0; xa[4] = 0
        xb = lo.get((pb, e))
        if xb is None:
            xb = lo[(pb, e)] = [0.0, 0, r, 0.0, 0]
        elif xb[2] < r:
            xb[0] += xb[3]; xb[1] += xb[4]; xb[2] = r; xb[3] = 0.0; xb[4] = 0
        ra, rb, na, nb = R[pa] + xa[0], R[pb] + xb[0], N[pa] + xa[1], N[pb] + xb[1]
        out[i, 0], out[i, 1], out[i, 2], out[i, 3] = ra, rb, na, nb
        do_s = s >= 0
        if do_s:
            ya = ls.get((pa, e, s))
            if ya is None:
                ya = ls[(pa, e, s)] = [0.0, 0, r, 0.0, 0]
            elif ya[2] < r:
                ya[0] += ya[3]; ya[1] += ya[4]; ya[2] = r; ya[3] = 0.0; ya[4] = 0
            yb = ls.get((pb, e, s))
            if yb is None:
                yb = ls[(pb, e, s)] = [0.0, 0, r, 0.0, 0]
            elif yb[2] < r:
                yb[0] += yb[3]; yb[1] += yb[4]; yb[2] = r; yb[3] = 0.0; yb[4] = 0
            sa, sb, nsa, nsb = RS[s][pa] + ya[0], RS[s][pb] + yb[0], NS[s][pa] + ya[1], NS[s][pb] + yb[1]
            out[i, 4], out[i, 5], out[i, 6], out[i, 7] = sa, sb, nsa, nsb
        if upd[i]:
            wgt = upd[i] * weight[i]
            res = 1.0 if a_won[i] else 0.0
            surprise = res - 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))
            xa[3] += wgt * k0 / (na + offset) ** shape * surprise
            xb[3] -= wgt * k0 / (nb + offset) ** shape * surprise
            xa[4] += upd[i]
            xb[4] += upd[i]
            if do_s:
                surprise = res - 1.0 / (1.0 + 10.0 ** ((sb - sa) / 400.0))
                ya[3] += wgt * k0 / (nsa + offset) ** shape * surprise
                yb[3] -= wgt * k0 / (nsb + offset) ** shape * surprise
                ya[4] += upd[i]
                yb[4] += upd[i]
    return out, {"R": R, "N": N, "RS": RS, "NS": NS, "lo": lo, "ls": ls, "cur": cur}


def new_stage3_state(n: int, k: dict) -> dict:
    _, _, S3, _ = _mods()
    return {"S": [float(k.get("start_serve", 0.0))] * n, "R": [float(k.get("start_return", S3.START_RETURN))] * n,
            "VS": [k["var_serve"]] * n, "VR": [k["var_return"]] * n, "NS": [0.0] * n, "NR": [0.0] * n,
            "LW": [None] * n, "lo": {}, "cur": None}


def stage3_pass(week, event, rnd, a, b, mu, upd, n_a, w_a, n_b, w_b, state: dict, var_serve: float,
                var_return: float, drift: float) -> tuple[np.ndarray, dict]:
    """stage3_ratings.rating_pass from `state` (new_stage3_state holds the start values); returns (out, state)."""
    _, _, S3, _ = _mods()
    VAR_FLOOR = S3.VAR_FLOOR
    S, R, VS, VR, NS, NR, LW, lo, cur = (state[k] for k in ("S", "R", "VS", "VR", "NS", "NR", "LW", "lo", "cur"))
    out = np.full((len(week), 12), np.nan)
    exp = math.exp
    for i in range(len(week)):
        wk = week[i]
        if wk != cur:
            for p, st in [(k[0], v) for k, v in lo.items()]:
                S[p] += st[0] + st[7]
                R[p] += st[1] + st[8]
                VS[p] = max(VS[p] + st[2] + st[9], VAR_FLOOR)
                VR[p] = max(VR[p] + st[3] + st[10], VAR_FLOOR)
                NS[p] += st[4] + st[11]
                NR[p] += st[5] + st[12]
            lo.clear()
            cur = wk
        e, r = event[i], rnd[i]
        sts = []
        for p in (a[i], b[i]):
            last = LW[p]
            if last != wk:
                if last is not None and drift > 0.0:
                    grow = drift * (wk - last) / 7.0
                    VS[p] = min(VS[p] + grow, var_serve)
                    VR[p] = min(VR[p] + grow, var_return)
                LW[p] = wk
            st = lo.get((p, e))
            if st is None:
                st = lo[(p, e)] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, r, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            elif st[6] < r:
                for j in range(6):
                    st[j] += st[7 + j]
                    st[7 + j] = 0.0
                st[6] = r
            sts.append(st)
        pa, pb = a[i], b[i]
        xa, xb = sts
        sa, ra = S[pa] + xa[0], R[pa] + xa[1]
        sb, rb = S[pb] + xb[0], R[pb] + xb[1]
        vsa, vra = max(VS[pa] + xa[2], VAR_FLOOR), max(VR[pa] + xa[3], VAR_FLOOR)
        vsb, vrb = max(VS[pb] + xb[2], VAR_FLOOR), max(VR[pb] + xb[3], VAR_FLOOR)
        o = out[i]
        o[0], o[1], o[2], o[3] = sa, sb, ra, rb
        o[4], o[5], o[6], o[7] = vsa, vsb, vra, vrb
        o[8], o[9], o[10], o[11] = NS[pa] + xa[4], NS[pb] + xb[4], NR[pa] + xa[5], NR[pb] + xb[5]
        if upd[i]:
            m = mu[i]
            for n, w, s_srv, v_srv, r_ret, v_ret, x_srv, x_ret in (
                    (n_a[i], w_a[i], sa, vsa, rb, vrb, xa, xb), (n_b[i], w_b[i], sb, vsb, ra, vra, xb, xa)):
                if n <= 0:
                    continue
                p = 1.0 / (1.0 + exp(-(m + s_srv - r_ret)))
                g = w - n * p
                h = n * p * (1.0 - p)
                den = 1.0 + (v_srv + v_ret) * h
                x_srv[7] += v_srv * g / den
                x_srv[9] -= v_srv * v_srv * h / den
                x_srv[11] += n
                x_ret[8] -= v_ret * g / den
                x_ret[10] -= v_ret * v_ret * h / den
                x_ret[12] += n
    return out, {"S": S, "R": R, "VS": VS, "VR": VR, "NS": NS, "NR": NR, "LW": LW, "lo": lo, "cur": cur}


# ------------------------------------------------------------------------------------------------
# Remapping a state onto today's player codes

def remap(state: dict, old_players, new_players, kind: str, k: dict | None = None) -> dict:
    """A state saved with an older player list (codes = positions in it) moved onto today's: new players start as the
    pass starts everyone; pending entries keep their insertion order with codes translated."""
    import elo_state as ES                                    # the prototype (prediction_pipeline), unchanged
    new_players = list(new_players)
    pos = {p: i for i, p in enumerate(new_players)}
    try:
        idx = [pos[p] for p in old_players]
    except KeyError as e:
        raise ValueError(f"a player of the saved state is not in today's table: {e}") from None
    n = len(new_players)
    if kind == "offset":
        return ES.remap(state, list(old_players), new_players)
    if kind == "weighted":
        fresh = new_weighted_state(n)
        for j, i in enumerate(idx):
            fresh["R"][i], fresh["N"][i] = state["R"][j], state["N"][j]
            for s in range(len(fresh["RS"])):
                fresh["RS"][s][i], fresh["NS"][s][i] = state["RS"][s][j], state["NS"][s][j]
        fresh["lo"] = {(idx[p], e): v for (p, e), v in state["lo"].items()}
        fresh["ls"] = {(idx[p], e, s): v for (p, e, s), v in state["ls"].items()}
        fresh["cur"] = state["cur"]
        return fresh
    if kind == "stage3":
        fresh = new_stage3_state(n, k)
        for j, i in enumerate(idx):
            for key in ("S", "R", "VS", "VR", "NS", "NR", "LW"):
                fresh[key][i] = state[key][j]
        fresh["lo"] = {(idx[p], e): v for (p, e), v in state["lo"].items()}
        fresh["cur"] = state["cur"]
        return fresh
    raise ValueError(kind)


def save_state(path: Path, state: dict, players) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump({"state": state, "players": list(players)}, f, protocol=pickle.HIGHEST_PROTOCOL)
    return int(path.stat().st_size)


def load_state(path: Path) -> tuple[dict, list]:
    with open(path, "rb") as f:
        d = pickle.load(f)
    return d["state"], d["players"]


# ------------------------------------------------------------------------------------------------
# Each pass's inputs for one tour, and its slice

def offset_inputs(m: pd.DataFrame, tour: str, consts: dict) -> dict:
    """m: Stage 0's matches (pieces.STAGE0_COLS) in Stage 0's order. The pass's arrays as pieces.main makes them."""
    LLE, B, _, _ = _mods()
    sel = m["tour"].eq(tour).to_numpy()
    t = m[sel].reset_index(drop=True)
    h = B.history_arrays(t)
    upd = LLE.elo_weights(t, t["status"].isin(B.UPDATES["ret"]).tolist())
    players = np.unique(np.concatenate([t["player_a_id"].to_numpy(), t["player_b_id"].to_numpy()]))
    k, kd = consts["stage1"][tour], consts["offset"][tour]
    return {"kind": "offset", "tour": tour, "match_id": t["match_id"].astype(str).to_numpy(), "players": players,
            "args": (h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"], upd),
            "ids": (t["player_a_id"].to_numpy(), t["player_b_id"].to_numpy()),
            "event_key": (t["tournament_date"].astype(str) + "|" + t["tournament_id"].astype(str)).to_numpy(),
            "k": {"k0": k["k0"], "offset": k["offset"], "shape": k["shape"]}, "kd": kd, "n_players": h["n_players"]}


def weighted_inputs(rows: pd.DataFrame, tour: str, scales: dict, consts: dict) -> dict:
    """rows: Stage 4's player-match table (stage4_features.load_rows). elo_variants' arrays for one tour, both kinds."""
    LLE, B, _, F = _mods()
    shares = F.winner_shares(rows)
    a = rows.iloc[0::2].reset_index(drop=True)
    upd = a["status"].isin(B.UPDATES["ret"]).to_numpy()
    idx = np.flatnonzero(a["tour"].eq(tour).to_numpy())
    t = a.iloc[idx].reset_index(drop=True)
    h = F.elo_inputs(t)
    updw = LLE.elo_weights(t, upd[idx].tolist())
    wgt = {kind: np.where(np.isfinite(shares[kind][idx]), shares[kind][idx] / scales[(kind, tour)], 1.0)
           for kind in WEIGHTED_KINDS}
    players = np.unique(np.concatenate([t["player_id"].to_numpy(), t["opponent_id"].to_numpy()]))
    k = consts["stage1"][tour]
    return {"kind": "weighted", "tour": tour, "match_id": t["match_id"].astype(str).to_numpy(), "players": players,
            "base": (h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"], updw),
            "wgt": wgt, "ids": (t["player_id"].to_numpy(), t["opponent_id"].to_numpy()),
            "event_key": (t["tournament_date"].astype(str) + "|" + t["tournament_id"].astype(str)).to_numpy(),
            "k": {"k0": k["k0"], "offset": k["offset"], "shape": k["shape"]}, "w": k["w"],
            "scales": {f"{kd}|{tour}": float(scales[(kd, tour)]) for kd in WEIGHTED_KINDS}, "n_players": h["n_players"],
            "rows_a": idx}


def stage3_inputs(m: pd.DataFrame, mu: np.ndarray, tour: str, consts: dict) -> dict:
    """m: stage3_ratings.load_history(); mu: its mu_of. rating_pass's arrays for one tour, with the layer's
    ratings_arrays (as stage3_ratings.main)."""
    LLE, _, S3, _ = _mods()
    idx = np.flatnonzero(m["tour"].eq(tour).to_numpy())
    t = m.iloc[idx].reset_index(drop=True)
    h = LLE.ratings_arrays(t, S3.arrays(t, mu[idx]))
    return {"kind": "stage3", "tour": tour, "match_id": t["match_id"].astype(str).to_numpy(),
            "players": np.asarray(h["players"]), "rows": idx,
            "args": (h["week"], h["event"], h["rnd"], h["a"], h["b"], h["mu"], h["upd"], h["n_a"], h["w_a"],
                     h["n_b"], h["w_b"]),
            "ids": (t["player_a_id"].to_numpy(), t["player_b_id"].to_numpy()),
            "event_key": (t["tournament_date"].astype(str) + "|" + t["tournament_id"].astype(str)).to_numpy(),
            "k": consts["stage3"][tour], "n_players": h["n_players"]}


def week_of(inp: dict) -> np.ndarray:
    a = inp["args"] if "args" in inp else inp["base"]
    return np.asarray(a[0], dtype=np.int64)


def slice_hash(inp: dict, i0: int) -> str:
    """The arrays the pass read for the matches before i0 (ids and keys in place of codes) and its constants."""
    a = inp["args"] if "args" in inp else inp["base"]
    named = {"match_id": inp["match_id"][:i0], "week": np.asarray(a[0][:i0]), "event": inp["event_key"][:i0],
             "rnd": np.asarray(a[2][:i0]), "a": inp["ids"][0][:i0], "b": inp["ids"][1][:i0]}
    if inp["kind"] == "stage3":
        for j, name in enumerate(("mu", "upd", "n_a", "w_a", "n_b", "w_b"), start=5):
            named[name] = np.asarray(a[j][:i0], dtype="float64")
        consts = inp["k"]
    else:
        named["a_won"] = np.asarray(a[5][:i0])
        named["surf"] = np.asarray(a[6][:i0])
        named["upd"] = np.asarray(a[7][:i0], dtype="float64")
        consts = {"k": inp["k"], "kd": inp.get("kd")}
        if inp["kind"] == "weighted":
            for kd in WEIGHTED_KINDS:
                named[f"wgt_{kd}"] = np.asarray(inp["wgt"][kd][:i0])
            consts = {**consts, "w": inp["w"], "scales": inp["scales"]}
    named["constants"] = np.asarray([hash_value(consts)])
    return hash_arrays(named, tag=f"dp/elo/{inp['kind']}/v1")


# ------------------------------------------------------------------------------------------------
# Running a pass: whole, to a checkpoint, or from one

def run(inp: dict, start: int = 0, stop: int | None = None, state: dict | None = None, kind_w: str | None = None):
    """The pass over matches [start, stop) from `state` (a fresh one when None). kind_w: the weighted pass's kind."""
    stop = len(inp["match_id"]) if stop is None else stop
    import elo_state as ES
    if inp["kind"] == "offset":
        st = ES.new_state(inp["n_players"], "offset") if state is None else state
        args = tuple(list(x[start:stop]) for x in inp["args"])
        return ES.elo_pass_ext_resumable(*args, st, inp["k"]["k0"], inp["k"]["offset"], inp["k"]["shape"],
                                         mode="offset", **inp["kd"])
    if inp["kind"] == "weighted":
        st = new_weighted_state(inp["n_players"]) if state is None else state
        args = tuple(list(x[start:stop]) for x in inp["base"])
        return weighted_pass(*args, list(inp["wgt"][kind_w][start:stop]), st, inp["k"]["k0"], inp["k"]["offset"],
                             inp["k"]["shape"])
    if inp["kind"] == "stage3":
        k = inp["k"]
        st = new_stage3_state(inp["n_players"], k) if state is None else state
        args = tuple(list(x[start:stop]) for x in inp["args"])
        return stage3_pass(*args, st, k["var_serve"], k["var_return"], k["drift"])
    raise ValueError(inp["kind"])


def stage3_table(m: pd.DataFrame, mu: np.ndarray, block: np.ndarray) -> pd.DataFrame:
    """stage3_ratings.parquet as stage3_ratings.main writes it, from the whole block (rows of m)."""
    _, _, S3, _ = _mods()
    out = m[["match_id", "tour", "year", "updates"]].copy()
    for j, c in enumerate(STAGE3_COLS):
        if c.startswith("var_"):
            out[c.replace("var_", "sd_")] = np.sqrt(block[:, j]).astype("float32")
        else:
            out[c] = block[:, j].astype("float32")
    out["mu_logit"] = mu.astype("float32")
    pa, pb = S3.expected_serve(block, mu)
    out["p_serve_a"], out["p_serve_b"] = pa, pb
    return out
