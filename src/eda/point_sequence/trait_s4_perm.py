"""A1-T follow-up: men's S4 against a within-set permutation null with no rate model.

Pre-registration: data/studies/point_sequence/trait_s4_perm_prereg.md (frozen by trait_s4_perm_prereg.sha256).
Run after trait_build.py:  ./python.sh src/eda/point_sequence/trait_s4_perm.py

Pools are one server's serve points in the regular games of one set. Each pool's outcomes are put in a uniformly random
order, re-scored into games (deuce / advantage), and accepted only if the last point ends a game (rejection sampling,
at most 5,000 draws). S4 is computed with trait_common.point_stats on the permuted games; reliability with
trait_reliability.run_population. Writes trait_s4_perm.csv and trait_s4_perm_results.json.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import trait_common as TC  # noqa: E402
from src.eda.point_sequence import trait_reliability as TR  # noqa: E402

PREREG = TC.OUT / "trait_s4_perm_prereg.md"
HASH = TC.OUT / "trait_s4_perm_prereg.sha256"
PERMS = 3
SEED = 20261006
CAP = 5000
REL_SEED = 20261008


def pools_of(P: dict) -> dict:
    """Regular-game points grouped by pool (match x set x server), each pool in its real order."""
    reg = P["is_tb"] == 0
    m, st, sv = P["m"][reg], P["set_no"][reg].astype(np.int64), P["server"][reg].astype(np.int64)
    y = (P["winner"][reg] == P["server"][reg]).astype(np.int8)
    key = (m * 16 + st) * 2 + (sv - 1)
    o = np.argsort(key, kind="stable")
    key, m, st, sv, y = key[o], m[o], st[o], sv[o], y[o]
    first = np.r_[True, key[1:] != key[:-1]]
    starts = np.flatnonzero(first)
    lens = np.diff(np.r_[starts, len(key)])
    pool = np.cumsum(first) - 1
    return {"y": y, "m": m, "set_no": st, "server": sv, "starts": starts, "lens": lens, "pool": pool}


def scan(yp: np.ndarray, starts: np.ndarray, lens: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Re-score each pool's sequence into games. Returns the end-of-game flag per position (for the given pools'
    positions, as a dict-free global array) and whether each pool ends on a game end."""
    Pn = len(starts)
    order = np.argsort(-lens, kind="stable")
    sl = lens[order]
    s = np.zeros(Pn, np.int64)
    r = np.zeros(Pn, np.int64)
    ends = []
    for k in range(int(lens.max()) if Pn else 0):
        cnt = int(np.searchsorted(-sl, -k, side="left"))          # pools with length > k
        act = order[:cnt]
        pos = starts[act] + k
        v = yp[pos].astype(np.int64)
        s[act] += v
        r[act] += 1 - v
        e = ((s[act] >= 4) | (r[act] >= 4)) & (np.abs(s[act] - r[act]) >= 2)
        ends.append(pos[e])
        s[act[e]] = 0
        r[act[e]] = 0
    return (np.concatenate(ends) if ends else np.array([], np.int64)), (s == 0) & (r == 0)


def permute(pl: dict, rng: np.random.Generator | None) -> tuple[np.ndarray, dict]:
    """A position -> point index order: each pool permuted uniformly among orders that form complete games (None:
    the real order). Returns the order and acceptance diagnostics."""
    N = len(pl["y"])
    starts, lens, pool = pl["starts"], pl["lens"], pl["pool"]
    order = np.arange(N)
    draws = np.zeros(len(starts), np.int64)
    if rng is None:
        _, valid = scan(pl["y"], starts, lens)
        return order, {"real_order_valid_pools": int(valid.sum()), "pools": int(len(starts))}
    todo = np.arange(len(starts))
    yp = pl["y"].copy()
    rounds = 0
    while todo.size and rounds < CAP:
        rounds += 1
        mask = np.zeros(len(starts), bool)
        mask[todo] = True
        pos = np.flatnonzero(mask[pool])
        perm = np.lexsort((rng.random(pos.size), pool[pos]))
        order[pos] = order[pos][perm]
        yp[pos] = pl["y"][order[pos]]
        draws[todo] += 1
        _, valid = scan(yp, starts[todo], lens[todo])
        todo = todo[~valid]
    capped = int(todo.size)
    if capped:
        mask = np.zeros(len(starts), bool)
        mask[todo] = True
        pos = np.flatnonzero(mask[pool])
        order[pos] = pos
    return order, {"pools": int(len(starts)), "rounds": rounds, "pools_at_cap_kept_real_order": capped,
                   "mean_draws_per_pool": float(draws.mean()), "accepted_first_draw_pct": float(100 * (draws == 1).mean()),
                   "max_draws": int(draws.max())}


def pseudo_points(pl: dict, order: np.ndarray) -> dict:
    """The permuted pools as point arrays for point_stats: each pool's points in permuted order, cut into games."""
    yp = pl["y"][order]
    ends, valid = scan(yp, pl["starts"], pl["lens"])
    end = np.zeros(len(yp), bool)
    end[ends] = True
    start_game = np.r_[True, end[:-1]] | np.r_[True, pl["pool"][1:] != pl["pool"][:-1]]
    gid = np.cumsum(start_game) - 1
    gfirst = np.flatnonzero(start_game)
    pt_no = np.arange(len(yp)) - gfirst[gid] + 1
    srv = pl["server"].astype(np.int8)
    win = np.where(yp == 1, srv, 3 - srv).astype(np.int8)
    return {"m": pl["m"], "set_no": pl["set_no"].astype(np.int16), "game_no": np.ones(len(yp), np.int16),
            "game_idx": gid.astype(np.int64), "pt_no": pt_no.astype(np.int16), "is_tb": np.zeros(len(yp), np.int8),
            "server": srv, "winner": win, "_valid": valid, "_games": int(gid[-1] + 1)}


def s4_rows(Pp: dict, n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """X_S4, D_S4, service games, holds in (mcode, side) order (rows 2*mcode + side - 1)."""
    pm, _ = TC.point_stats({k: v for k, v in Pp.items() if not k.startswith("_")}, n)
    pm = pm.sort_values(["mcode", "side"], kind="mergesort")
    return (pm["X_S4"].to_numpy("float64"), pm["D_S4"].to_numpy("float64"), pm["svc_games"].to_numpy("float64"),
            pm["holds"].to_numpy("float64"))


def main() -> int:
    t0 = time.time()
    digest = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    recorded = HASH.read_text(encoding="utf-8").split()[0]
    assert digest == recorded, "pre-registration changed after its hash was recorded"
    info: dict = {"prereg_sha256": digest, "deviations": []}
    pop = pd.read_parquet(TC.OUT / "trait_population.parquet")
    n = len(pop)
    P = TC.real_points(pop)
    pl = pools_of(P)
    TC.log(f"{len(pl['starts']):,} pools, {len(pl['y']):,} regular-game serve points")
    # identity: the real order re-scored must reproduce the stored real S4
    order, diag = permute(pl, None)
    assert diag["real_order_valid_pools"] == diag["pools"], diag
    Pp = pseudo_points(pl, order)
    X0, D0, G0, H0 = s4_rows(Pp, n)
    stored = pd.read_parquet(TC.OUT / "trait_player_matches.parquet",
                             columns=["world", "mcode", "side", "X_S4", "D_S4", "svc_games", "holds"])
    st = stored[stored["world"] == "real"].sort_values(["mcode", "side"])
    info["identity_check"] = {"max_abs_diff_X": float(np.max(np.abs(st["X_S4"].to_numpy("float64") - X0))),
                              "max_abs_diff_D": float(np.max(np.abs(st["D_S4"].to_numpy("float64") - D0))),
                              "svc_games_equal": bool((st["svc_games"].to_numpy() == G0).all()),
                              "holds_equal": bool((st["holds"].to_numpy() == H0).all()), "games": Pp["_games"]}
    assert info["identity_check"]["max_abs_diff_X"] < 1e-2 and info["identity_check"]["svc_games_equal"], info
    TC.log(f"identity check passed: {info['identity_check']}")
    worlds = {"real": (X0, D0, G0, H0)}
    info["acceptance"] = {}
    for j in range(PERMS):
        rng = np.random.default_rng([SEED, 77, j])
        order, diag = permute(pl, rng)
        Pp = pseudo_points(pl, order)
        assert Pp["_valid"].sum() >= len(pl["starts"]) - diag["pools_at_cap_kept_real_order"]
        worlds[f"perm_{j}"] = s4_rows(Pp, n)
        diag["games"] = Pp["_games"]
        info["acceptance"][f"perm_{j}"] = diag
        TC.log(f"perm_{j}: {diag}")
    _, rows, _, tot = TR.load()
    assert (rows["mcode"].to_numpy() == np.repeat(np.arange(n), 2)).all()
    wl = list(worlds)
    XD = {"X": {w: worlds[w][0][:, None] for w in wl}, "D": {w: worlds[w][1][:, None] for w in wl}}
    rng = np.random.default_rng(REL_SEED)
    out = []
    for tour in ("atp", "wta"):
        tmask = rows["tour"].to_numpy() == tour
        for label, hm in (("ge20", 20), ("ge50", 50)):
            res = TR.run_population(label, tour, tmask, rows, XD, wl, hm, rng)
            rel = res["rel"][:, 0]
            boot = res["boot"][:, :, 0]
            d = rel[0] - rel[1:].mean()
            bd = boot[:, 0] - boot[:, 1:].mean(axis=1)
            bd = bd[np.isfinite(bd)]
            row = {"tour": tour, "population": label, "players": res["players"], "player_matches": res["player_matches"],
                   "matches_per_player_median": res["matches_per_player_median"], "real_r": float(rel[0]),
                   "permuted_r": float(rel[1:].mean()), "permuted_r_each": [float(x) for x in rel[1:]],
                   "delta": float(d), "delta_lo": float(np.percentile(bd, 2.5)), "delta_hi": float(np.percentile(bd, 97.5))}
            if label == "ge20":
                sub, pc, Pn = res["sub"], res["pcode"], res["players"]
                T = tot["real"][sub]
                s4 = np.bincount(pc, weights=X0[sub], minlength=Pn) / np.bincount(pc, weights=D0[sub], minlength=Pn)
                hold = np.bincount(pc, weights=T[:, 1], minlength=Pn) / np.bincount(pc, weights=T[:, 0], minlength=Pn)
                brk = np.bincount(pc, weights=T[:, 3], minlength=Pn) / np.bincount(pc, weights=T[:, 2], minlength=Pn)
                ok = np.isfinite(s4)
                row["r_hold"] = float(np.corrcoef(s4[ok], hold[ok])[0, 1])
                row["r_break"] = float(np.corrcoef(s4[ok], brk[ok])[0, 1])
                row["ability_max_abs_r"] = max(abs(row["r_hold"]), abs(row["r_break"]))
                row["pass"] = bool(d >= 0.10 and row["delta_lo"] > 0 and row["ability_max_abs_r"] < 0.3)
            out.append(row)
            TC.log(f"{tour} {label}: real {rel[0]:.4f} permuted {rel[1:].mean():.4f} delta {d:+.4f} "
                   f"[{row['delta_lo']:+.4f}, {row['delta_hi']:+.4f}]")
        # population level: pooled S4, real - permuted, player-cluster bootstrap
        sub = np.flatnonzero(tmask)
        pc, uq = pd.factorize(rows["player"].to_numpy()[sub])
        Pn = len(uq)
        W = np.stack([np.bincount(rng.integers(0, Pn, Pn), minlength=Pn) for _ in range(1000)]).astype("float64")
        sums = {w: (np.bincount(pc, weights=worlds[w][0][sub], minlength=Pn),
                    np.bincount(pc, weights=worlds[w][1][sub], minlength=Pn)) for w in wl}
        real = sums["real"][0].sum() / sums["real"][1].sum()
        perm = np.mean([sums[w][0].sum() / sums[w][1].sum() for w in wl[1:]])
        b = (W @ sums["real"][0]) / (W @ sums["real"][1]) - np.mean(
            [(W @ sums[w][0]) / (W @ sums[w][1]) for w in wl[1:]], axis=0)
        G = {w: worlds[w][2][sub].sum() for w in wl}
        H = {w: worlds[w][3][sub].sum() for w in wl}
        info.setdefault("population_level", {})[tour] = {
            "player_matches": int(len(sub)), "real_S4": float(real), "permuted_S4": float(perm),
            "real_minus_permuted": float(real - perm), "lo": float(np.percentile(b, 2.5)), "hi": float(np.percentile(b, 97.5)),
            "service_games_real": float(G["real"]), "service_games_permuted_mean": float(np.mean([G[w] for w in wl[1:]])),
            "hold_rate_real": float(H["real"] / G["real"]),
            "hold_rate_permuted_mean": float(np.mean([H[w] / G[w] for w in wl[1:]]))}
        TC.log(f"{tour} population: {info['population_level'][tour]}")
    res_df = pd.DataFrame(out)
    res_df.to_csv(TC.OUT / "trait_s4_perm.csv", index=False)
    info["reliability"] = json.loads(res_df.to_json(orient="records"))
    info["seconds"] = round(time.time() - t0, 1)
    (TC.OUT / "trait_s4_perm_results.json").write_text(json.dumps(info, indent=1, default=float) + "\n", encoding="utf-8")
    TC.log("wrote trait_s4_perm.csv and trait_s4_perm_results.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
