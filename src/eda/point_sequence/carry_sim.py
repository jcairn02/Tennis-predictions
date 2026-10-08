"""B1 replay null: match t replayed point by point as iid draws at de-noised day rates, format preserved.

``simulate`` plays many matches at once (numpy, one point per step for every unfinished match) under the scoring rules of
replay.py (Rules: best of, deciding-set rule tb / tb10 / adv / tb12 / mtb10, six-game sets, tie-break at 6-6, ad
scoring) with the servers of replay.rule_servers: the serve alternates by game over the match, a tie-break counts as
one game, and inside a tie-break the first server serves one point and then the serve changes every two points. Each
point is won by its server with that player's day rate. It returns, per match, the serve points each player played and
won in every set (sets 1-5) and the winner. ``record=True`` also returns every match's point winners and servers, which
the tests replay with replay.py to check the simulator against the reference rules.

``denoise`` draws a "true" day rate for each player from what the measured rate allows (empirical Bayes, as
predictability_diagnostic.stage2_anatomy.denoised_rates does), but with the prior frozen on 2013-2018 Stage 0 box
scores (``frozen_prior``): per tour and surface, the mean of measured serve-point shares and their variance less the
average binomial noise; surfaces with under 400 player-matches use the tour's.

``replay_triples`` replays every triple's match t conditional on its real winner: rates and points are redrawn
together until the replay's winner is the real one (at most MAX_TRIES rounds; a match never matched keeps its last
draw and is counted). The first server and the format are the real match's.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as PD  # noqa: E402

FINAL_CODE = {"tb": 0, "tb10": 1, "adv": 2, "tb12": 3, "mtb10": 4}
PRIOR_YEARS = (2013, 2018)
MAX_TRIES = 200
MAX_SETS = 5


def simulate(pa, pb, best_of, final, s0, rng: np.random.Generator, record: bool = False) -> dict:
    """Play len(pa) matches. pa, pb: each side's probability of winning a point on its own serve; best_of 3/5; final:
    a FINAL_CODE per match; s0: the first server (1 or 2). Six-game sets, tie-break at 6-6, ad scoring."""
    pa = np.asarray(pa, float)
    pb = np.asarray(pb, float)
    K = len(pa)
    need = (np.asarray(best_of, int) // 2 + 1)
    final = np.asarray(final, int)
    s0 = np.asarray(s0, int)
    s1 = np.zeros(K, int); s2 = np.zeros(K, int)
    g1 = np.zeros(K, int); g2 = np.zeros(K, int)
    p1 = np.zeros(K, int); p2 = np.zeros(K, int)
    gi = np.zeros(K, int)
    kind = np.zeros(K, int); target = np.full(K, 4)
    setno = np.zeros(K, int)
    done = np.zeros(K, bool)
    winner = np.zeros(K, int)
    served = np.zeros((K, MAX_SETS, 2), int)
    won = np.zeros((K, MAX_SETS, 2), int)
    rec_w: list[list[int]] | None = [[] for _ in range(K)] if record else None
    rec_s: list[list[int]] | None = [[] for _ in range(K)] if record else None
    idx = np.arange(K)
    while idx.size:
        # a new game: its kind and target
        start = (p1[idx] == 0) & (p2[idx] == 0)
        if start.any():
            j = idx[start]
            deciding = (s1[j] == need[j] - 1) & (s2[j] == need[j] - 1)
            fj = final[j]
            mtb = deciding & (fj == FINAL_CODE["mtb10"])
            at6 = (g1[j] == 6) & (g2[j] == 6) & ~(deciding & ((fj == FINAL_CODE["adv"]) | (fj == FINAL_CODE["tb12"])))
            at12 = deciding & (fj == FINAL_CODE["tb12"]) & (g1[j] == 12) & (g2[j] == 12)
            k = np.where(mtb, 2, np.where(at6 | at12, 1, 0))
            t = np.where(mtb, 10, np.where(at6, np.where(deciding & (fj == FINAL_CODE["tb10"]), 10, 7),
                                           np.where(at12, 7, 4)))
            kind[j] = k
            target[j] = t
        first = np.where(gi[idx] % 2 == 0, s0[idx], 3 - s0[idx])
        played = p1[idx] + p2[idx]
        flip = (kind[idx] > 0) & (((played + 1) // 2) % 2 == 1)
        server = np.where(flip, 3 - first, first)
        prob = np.where(server == 1, pa[idx], pb[idx])
        srv_won = rng.random(idx.size) < prob
        pw = np.where(srv_won, server, 3 - server)
        sn = setno[idx]
        np.add.at(served, (idx, sn, server - 1), 1)
        np.add.at(won, (idx, sn, server - 1), srv_won.astype(int))
        if record:
            for a, b, c in zip(idx.tolist(), pw.tolist(), server.tolist()):
                rec_w[a].append(b)
                rec_s[a].append(c)
        p1[idx] += pw == 1
        p2[idx] += pw == 2
        q1, q2, kd, tg = p1[idx], p2[idx], kind[idx], target[idx]
        lead = np.abs(q1 - q2) >= 2
        game_over = np.where(kd > 0, ((q1 >= tg) | (q2 >= tg)) & lead, ((q1 >= 4) | (q2 >= 4)) & lead)
        if game_over.any():
            j = idx[game_over]
            gw = np.where(p1[j] > p2[j], 1, 2)
            kj = kind[j]
            p1[j] = 0
            p2[j] = 0
            gi[j] += 1
            g1[j] += (gw == 1) & (kj != 2)
            g2[j] += (gw == 2) & (kj != 2)
            set_over = (kj == 2) | (kj == 1) | (((g1[j] >= 6) | (g2[j] >= 6)) & (np.abs(g1[j] - g2[j]) >= 2))
            if set_over.any():
                js, gws = j[set_over], gw[set_over]
                g1[js] = 0
                g2[js] = 0
                setno[js] = np.minimum(setno[js] + 1, MAX_SETS - 1)
                s1[js] += gws == 1
                s2[js] += gws == 2
                fin = (s1[js] == need[js]) | (s2[js] == need[js])
                done[js[fin]] = True
                winner[js[fin]] = gws[fin]
            idx = idx[~done[idx]]
    out = {"served": served, "won": won, "winner": winner, "sets": s1 + s2}
    if record:
        out["point_winners"] = rec_w
        out["point_servers"] = rec_s
    return out


# ------------------------------------------------------------------------------------------------
# De-noised day rates

def frozen_prior() -> pd.DataFrame:
    """Per tour x surface: mean measured serve-point share, its variance, the mean binomial noise and the implied true
    variance, from Stage 0 box scores of completed standard-format matches, 2013-2018 (frozen)."""
    m = pd.read_parquet(PD.MATCHES, columns=["match_id", "tour", "year", "surface", "status", "format", "has_box"],
                        filters=[("year", ">=", PRIOR_YEARS[0]), ("year", "<=", PRIOR_YEARS[1])])
    m = m[m["status"].eq("completed") & m["format"].eq("standard") & m["has_box"]]
    mp = pd.read_parquet(PD.MATCH_PLAYERS, columns=["match_id", "spw_n", "spw_d"])
    x = mp.merge(m[["match_id", "tour", "surface"]], on="match_id")
    x = x[x["spw_d"] > 0]
    x["P"] = x["spw_n"] / x["spw_d"]
    x["noise"] = x["P"] * (1 - x["P"]) / x["spw_d"]
    x["surface"] = x["surface"].fillna("unknown")
    rows = []
    for tour, g in x.groupby("tour"):
        whole = (float(g["P"].mean()), float(g["P"].var()), float(g["noise"].mean()), int(len(g)))
        for sf, h in g.groupby("surface"):
            own = len(h) >= 400
            mu, var, nz, n = ((float(h["P"].mean()), float(h["P"].var()), float(h["noise"].mean()), int(len(h)))
                              if own else whole)
            rows.append({"tour": tour, "surface": sf, "player_matches": int(len(h)), "own_prior": own, "mu": mu,
                         "measured_var": var, "noise_mean": nz, "true_var": max(var - nz, 1e-6)})
        rows.append({"tour": tour, "surface": "_tour", "player_matches": whole[3], "own_prior": True, "mu": whole[0],
                     "measured_var": whole[1], "noise_mean": whole[2], "true_var": max(whole[1] - whole[2], 1e-6)})
    return pd.DataFrame(rows)


def denoise(P, N, tour, surface, prior: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    """A true-rate draw per player-match: normal posterior around the measured share shrunk to the tour x surface prior
    (the tour's for a surface the prior lacks), clipped to [0.02, 0.98]."""
    P = np.asarray(P, float)
    N = np.asarray(N, float)
    table = {(r.tour, r.surface): (r.mu, r.true_var) for r in prior.itertuples(index=False)}
    got = [table.get((t, s), table[(t, "_tour")]) for t, s in zip(np.asarray(tour, str), np.asarray(surface, object))]
    mu = np.fromiter((g[0] for g in got), float, len(got))
    vt = np.fromiter((g[1] for g in got), float, len(got))
    noise = np.clip(P * (1 - P), 1e-4, None) / N
    shrink = vt / (vt + noise)
    draw = rng.normal(mu + shrink * (P - mu), np.sqrt(shrink * noise))
    return np.clip(draw, 0.02, 0.98)


def frozen_deviation_prior() -> pd.DataFrame:
    """Secondary replay variant (player-centred): per tour, the variance of the day's serve share around the
    player's own pre-match expectation (stage3 p_serve), less the average binomial noise, from Stage 0 box scores of
    completed standard-format matches, 2013-2018 (frozen)."""
    m = pd.read_parquet(PD.MATCHES, columns=["match_id", "tour", "year", "status", "format", "has_box"],
                        filters=[("year", ">=", PRIOR_YEARS[0]), ("year", "<=", PRIOR_YEARS[1])])
    m = m[m["status"].eq("completed") & m["format"].eq("standard") & m["has_box"]]
    mp = pd.read_parquet(PD.MATCH_PLAYERS, columns=["match_id", "side", "spw_n", "spw_d"])
    r = pd.read_parquet(PD.OUT / "stage3_ratings.parquet", columns=["match_id", "p_serve_a", "p_serve_b"],
                        filters=[("year", ">=", PRIOR_YEARS[0]), ("year", "<=", PRIOR_YEARS[1])])
    x = mp.merge(m[["match_id", "tour"]], on="match_id").merge(r, on="match_id")
    x = x[x["spw_d"] > 0]
    x["ps"] = np.where(x["side"].eq("A"), x["p_serve_a"], x["p_serve_b"])
    x["P"] = x["spw_n"] / x["spw_d"]
    x["dev"] = x["P"] - x["ps"]
    x["noise"] = x["P"] * (1 - x["P"]) / x["spw_d"]
    rows = []
    for tour, g in x.groupby("tour"):
        rows.append({"tour": tour, "player_matches": int(len(g)), "dev_mean": float(g["dev"].mean()),
                     "dev_var": float(g["dev"].var()), "noise_mean": float(g["noise"].mean()),
                     "true_var": max(float(g["dev"].var() - g["noise"].mean()), 1e-6)})
    return pd.DataFrame(rows)


def denoise_player(P, N, ps, tour, dev_prior: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    """Player-centred true-rate draw: normal posterior of the day's deviation from the player's own expectation ps,
    shrunk toward 0 by the tour's frozen true variance of day deviations; clipped to [0.02, 0.98]."""
    P = np.asarray(P, float)
    N = np.asarray(N, float)
    ps = np.asarray(ps, float)
    vt_map = dict(zip(dev_prior["tour"], dev_prior["true_var"]))
    vt = np.array([vt_map[t] for t in np.asarray(tour, str)])
    noise = np.clip(P * (1 - P), 1e-4, None) / N
    shrink = vt / (vt + noise)
    draw = rng.normal(ps + shrink * (P - ps), np.sqrt(shrink * noise))
    return np.clip(draw, 0.02, 0.98)


def replay_triples(tri: pd.DataFrame, prior: pd.DataFrame, seed: int, mode: str = "tour_mean",
                   dev_prior: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """One conditional replay of every triple's match t. Returns the replayed set-1 and late-set serve counts of the
    triple's player (n1, w1, nL, wL) and the opponent's (on1, ow1, onL, owL), indexed like ``tri``.

    mode "tour_mean" (primary, as specified): de-noised toward the frozen tour x surface prior; "player" (secondary):
    de-noised toward each player's own pre-match p_serve with the frozen tour variance of day deviations."""
    rng = np.random.default_rng(seed)
    side = tri["side_t"].to_numpy(int)
    # measured whole-match rates of side A and side B in match t
    nA = np.where(side == 1, tri["n_tot"], tri["on_tot"]).astype(float)
    wA = np.where(side == 1, tri["w_tot"], tri["ow_tot"]).astype(float)
    nB = np.where(side == 1, tri["on_tot"], tri["n_tot"]).astype(float)
    wB = np.where(side == 1, tri["ow_tot"], tri["w_tot"]).astype(float)
    tour = tri["tour"].to_numpy(str)
    surf = tri["surface"].fillna("unknown").to_numpy(object)
    bo = tri["bo"].to_numpy(int)
    fin = tri["final"].map(FINAL_CODE).to_numpy(int)
    s0 = tri["s0"].to_numpy(int)
    target = tri["winner_t"].to_numpy(int)
    K = len(tri)
    served = np.zeros((K, MAX_SETS, 2), int)
    won = np.zeros((K, MAX_SETS, 2), int)
    todo = np.arange(K)
    tries = 0
    psA = np.where(side == 1, tri["ps_t"], tri["pso_t"]).astype(float) if mode == "player" else None
    psB = np.where(side == 1, tri["pso_t"], tri["ps_t"]).astype(float) if mode == "player" else None
    while todo.size and tries < MAX_TRIES:
        tries += 1
        if mode == "player":
            pa = denoise_player(wA[todo] / nA[todo], nA[todo], psA[todo], tour[todo], dev_prior, rng)
            pb = denoise_player(wB[todo] / nB[todo], nB[todo], psB[todo], tour[todo], dev_prior, rng)
        else:
            pa = denoise(wA[todo] / nA[todo], nA[todo], tour[todo], surf[todo], prior, rng)
            pb = denoise(wB[todo] / nB[todo], nB[todo], tour[todo], surf[todo], prior, rng)
        sim = simulate(pa, pb, bo[todo], fin[todo], s0[todo], rng)
        ok = sim["winner"] == target[todo]
        last = tries == MAX_TRIES
        take = ok | last
        served[todo[take]] = sim["served"][take]
        won[todo[take]] = sim["won"][take]
        todo = todo[~ok]
    late = np.where(bo == 5, 2, 1)                      # 0-based index of the late set
    me = side - 1
    op = 2 - side
    ar = np.arange(K)
    out = pd.DataFrame({
        "n1": served[ar, 0, me], "w1": won[ar, 0, me], "nL": served[ar, late, me], "wL": won[ar, late, me],
        "on1": served[ar, 0, op], "ow1": won[ar, 0, op], "onL": served[ar, late, op], "owL": won[ar, late, op],
    }, index=tri.index)
    return out, {"rounds": tries, "never_matched": int(todo.size)}
