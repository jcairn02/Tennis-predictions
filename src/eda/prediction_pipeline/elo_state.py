"""The offset Elo pass (src/eda/surface_elo_pieces/pieces.py, elo_pass_ext) with its state saved and resumed.

The pass is a loop over the tour's matches in Stage 0's order. Between two matches its whole state is: each player's
overall rating R and count N, per surface the rating RS, count NS and offset X (and INIT for the anchored mode), the
current week's pending entries (lo, ls, lx: what an event's earlier rounds added, held back until the next round or
the week's end) and the current week. elo_pass_ext_resumable is the decided loop, line for line, taking that state in
and handing it back; resumed from a state saved anywhere (any match), the outputs equal one unbroken pass bit for
bit, because the arithmetic and its order are the same.
"""
from __future__ import annotations

import pickle

import numpy as np


def _C():
    from src.eda.surface_elo_pieces import common as C
    return C


def new_state(n_players: int, mode: str) -> dict:
    C = _C()
    from src.eda.surface_elo_pieces.pieces import START
    return {"R": [START] * n_players, "N": [0] * n_players,
            "RS": [[START] * n_players for _ in C.SURFACES], "NS": [[0] * n_players for _ in C.SURFACES],
            "X": [[0.0 if mode == "offset" else START] * n_players for _ in C.SURFACES],
            "INIT": [[False] * n_players for _ in C.SURFACES], "lo": {}, "ls": {}, "lx": {}, "cur": None}


def elo_pass_ext_resumable(week, event, rnd, a, b, a_won, surf, upd, state: dict, k0: float, offset: float,
                           shape: float, mode: str = "stage1", kd0: float = 0.0, kd_off: float = 1.0,
                           kd_shape: float = 0.5) -> tuple[np.ndarray, dict]:
    """pieces.elo_pass_ext over the given matches, starting from `state` (new_state() for the first match); returns
    (out, state after the last match). The body is the decided loop's."""
    R, N, RS, NS, X, INIT = state["R"], state["N"], state["RS"], state["NS"], state["X"], state["INIT"]
    lo, ls, lx, cur = state["lo"], state["ls"], state["lx"], state["cur"]
    out = np.full((len(week), 10), np.nan)

    def entry(d, key, r):
        x = d.get(key)
        if x is None:
            x = d[key] = [0.0, 0, r, 0.0, 0]
        elif x[2] < r:
            x[0] += x[3]; x[1] += x[4]; x[2] = r; x[3] = 0.0; x[4] = 0
        return x

    for i in range(len(week)):
        if week[i] != cur:
            for (p, _), st in lo.items():
                R[p] += st[0] + st[3]
                N[p] += st[1] + st[4]
            for (p, _, s), st in ls.items():
                RS[s][p] += st[0] + st[3]
                NS[s][p] += st[1] + st[4]
            for (p, _, s), st in lx.items():
                X[s][p] += st[0] + st[3]
            lo.clear(); ls.clear(); lx.clear()
            cur = week[i]
        e, r, s, pa, pb = event[i], rnd[i], surf[i], a[i], b[i]
        xa, xb = entry(lo, (pa, e), r), entry(lo, (pb, e), r)
        ra, rb, na, nb = R[pa] + xa[0], R[pb] + xb[0], N[pa] + xa[1], N[pb] + xb[1]
        out[i, 0], out[i, 1], out[i, 2], out[i, 3] = ra, rb, na, nb
        do_s = s >= 0
        if do_s:
            ya, yb = entry(ls, (pa, e, s), r), entry(ls, (pb, e, s), r)
            sa, sb, nsa, nsb = RS[s][pa] + ya[0], RS[s][pb] + yb[0], NS[s][pa] + ya[1], NS[s][pb] + yb[1]
            out[i, 4], out[i, 5], out[i, 6], out[i, 7] = sa, sb, nsa, nsb
            if mode == "anchored":
                for p, rr in ((pa, ra), (pb, rb)):
                    if not INIT[s][p]:
                        X[s][p] = rr
                        INIT[s][p] = True
            za, zb = entry(lx, (pa, e, s), r), entry(lx, (pb, e, s), r)
            xa_s, xb_s = X[s][pa] + za[0], X[s][pb] + zb[0]
            out[i, 8], out[i, 9] = (sa, sb) if mode == "stage1" else (xa_s, xb_s)
        if upd[i]:
            res = 1.0 if a_won[i] else 0.0
            surprise = res - 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))
            xa[3] += upd[i] * k0 / (na + offset) ** shape * surprise
            xb[3] -= upd[i] * k0 / (nb + offset) ** shape * surprise
            xa[4] += upd[i]
            xb[4] += upd[i]
            if do_s:
                surprise_s = res - 1.0 / (1.0 + 10.0 ** ((sb - sa) / 400.0))
                ya[3] += upd[i] * k0 / (nsa + offset) ** shape * surprise_s
                yb[3] -= upd[i] * k0 / (nsb + offset) ** shape * surprise_s
                ya[4] += upd[i]
                yb[4] += upd[i]
                if mode == "anchored":
                    surprise_x = res - 1.0 / (1.0 + 10.0 ** ((xb_s - xa_s) / 400.0))
                    za[3] += upd[i] * k0 / (nsa + offset) ** shape * surprise_x
                    zb[3] -= upd[i] * k0 / (nsb + offset) ** shape * surprise_x
                elif mode == "offset":
                    surprise_c = res - 1.0 / (1.0 + 10.0 ** (((rb + xb_s) - (ra + xa_s)) / 400.0))
                    za[3] += upd[i] * kd0 / (nsa + kd_off) ** kd_shape * surprise_c
                    zb[3] -= upd[i] * kd0 / (nsb + kd_off) ** kd_shape * surprise_c
    state = {"R": R, "N": N, "RS": RS, "NS": NS, "X": X, "INIT": INIT, "lo": lo, "ls": ls, "lx": lx, "cur": cur}
    return out, state


def save(path, state: dict, players) -> None:
    """The state with the tour's player ids (codes are positions in `players`), pickled (dict order kept)."""
    with open(path, "wb") as f:
        pickle.dump({"state": state, "players": list(players)}, f, protocol=pickle.HIGHEST_PROTOCOL)


def load(path) -> tuple[dict, list]:
    with open(path, "rb") as f:
        d = pickle.load(f)
    return d["state"], d["players"]


def remap(state: dict, old_players: list, new_players) -> dict:
    """A state saved with an older player list moved onto today's (new players start fresh, as the pass starts
    everyone). Pending entries keep their keys with player codes translated."""
    C = _C()
    from src.eda.surface_elo_pieces.pieces import START
    new_players = list(new_players)
    pos = {p: i for i, p in enumerate(new_players)}
    idx = [pos[p] for p in old_players]
    n = len(new_players)
    mode_offset = True
    fresh = new_state(n, "offset" if mode_offset else "stage1")
    out = {k: fresh[k] for k in ("R", "N", "RS", "NS", "X", "INIT")}
    for j, i in enumerate(idx):
        out["R"][i] = state["R"][j]
        out["N"][i] = state["N"][j]
        for s in range(len(C.SURFACES)):
            out["RS"][s][i] = state["RS"][s][j]
            out["NS"][s][i] = state["NS"][s][j]
            out["X"][s][i] = state["X"][s][j]
            out["INIT"][s][i] = state["INIT"][s][j]
    out["lo"] = {(idx[p], e): v for (p, e), v in state["lo"].items()}
    out["ls"] = {(idx[p], e, s): v for (p, e, s), v in state["ls"].items()}
    out["lx"] = {(idx[p], e, s): v for (p, e, s), v in state["lx"].items()}
    out["cur"] = state["cur"]
    _ = START
    return out
