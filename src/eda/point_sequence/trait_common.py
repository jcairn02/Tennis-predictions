"""A1-T and I2 (point sequence study, tester 1): shared population, statistics and the point-level iid replayer.

The pre-registration is data/studies/point_sequence/trait_prereg.md (written before any reliability was computed). This
module holds what every step shares:

    population()        the analysed matches (item 1's filters) with players, format, first server, obs day, source
    real_points()       their point sequences from sequences.parquet, in the replayer's array schema
    point_stats()       the per player-match statistics S1-S5, S4r and the placebo P0 (numerator X, denominator D), plus
                        serve / return / game / set totals; one function for real and replayed points
    replay_points()     a vectorised point-by-point iid replay of many matches, each under its own best-of and
                        deciding-set rule, emitting the same arrays as real_points()
    fit_priors(), draw_rates()   the de-noised day rates, with priors fitted on seasons <= 2018 only (V05/V1/V15 and
                        the per-player-season variant VPS)

Imports the builder's replay rules (replay.py) and Stage 3's empirical-Bayes helper read-only; edits nothing.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "point_sequence"
S0 = ROOT / "data" / "studies" / "predictability_diagnostic"
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
RATINGS = S0 / "stage3_ratings.parquet"
T0 = time.time()

FIRST_YEAR = {"atp": 2013, "wta": 2016}
LAST_YEAR = 2024
PRIOR_LAST_YEAR = 2018
FINALS = {"tb": 0, "tb10": 1, "adv": 2, "tb12": 3}
FINAL_NAMES = {v: k for k, v in FINALS.items()}
STAGE2_RULE = {"tb": "TB7@6", "tb10": "TB10@6", "adv": "ADV", "tb12": "TB7@12"}
STATS = ["S1", "S2", "S3", "S4", "S5", "S4r", "P0"]
PRIMARY = ["S1", "S2", "S3", "S4", "S5"]
STAT_WORDS = {
    "S1": "hold after breaking, minus the hold rate in the player's other service games (per after-break game)",
    "S2": "break back after being broken, minus the break rate in the player's other return games (per such game)",
    "S3": "serve point won after a won point minus after a lost point, same game, match x score-state cells",
    "S4": "game-level overdispersion of serve points won (dispersion index - 1)",
    "S5": "set-to-set overdispersion of serve points won (dispersion index - 1)",
    "S4r": "fewer runs of serve-point outcomes within service games than exchangeable (E - R, per unit variance)",
    "P0": "placebo: hold after holding, minus the hold rate in the player's other service games",
}
VARIANTS = {"V1": 1.0, "V05": 0.5, "V15": 1.5, "VPS": None}
REPLAYS = 3
SEED = 20261006


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# Population

def population() -> tuple[pd.DataFrame, dict]:
    """Item 1's matches: chosen usable sequence, tier 0-1, complete replay, Stage 0 completed and standard format, a
    standard rule, men 2013-2024 / women 2016-2024. One row per match with an integer code ``mcode`` (row order)."""
    sm = pd.read_parquet(OUT / "seq_matches.parquet",
                         columns=["match_id", "source", "chosen", "usable", "tier", "status", "replay", "rule",
                                  "strict", "n_points"])
    ch = sm[sm["chosen"] & sm["usable"]].drop(columns=["chosen", "usable"])
    m = pd.read_parquet(S0 / "stage0_matches.parquet",
                        columns=["match_id", "tour", "year", "level", "map_level", "qualifying", "status", "format",
                                 "best_of", "surface", "player_a_id", "player_b_id", "a_won", "tournament_id",
                                 "tournament_date", "round", "round_order"])
    j = ch.merge(m, on="match_id", how="inner", suffixes=("_seq", ""))
    steps = [("chosen usable sequence linked to Stage 0", j)]
    j = j[j["year"].le(LAST_YEAR) & ((j["tour"].eq("atp") & j["year"].ge(FIRST_YEAR["atp"])) |
                                     (j["tour"].eq("wta") & j["year"].ge(FIRST_YEAR["wta"])))]
    steps.append(("men 2013-2024, women 2016-2024", j))
    j = j[j["tier"].isin([0, 1]) & j["status_seq"].eq("complete") & j["replay"].eq("complete")]
    steps.append(("tier 0-1, complete replay agreeing with the official score", j))
    j = j[j["status"].eq("completed")]
    steps.append(("Stage 0 completed (retirements and the rest out)", j))
    j = j[j["format"].eq("standard")]
    steps.append(("standard format", j))
    bo = j["rule"].str.extract(r"^bo(\d)/([a-z0-9]+)$")
    j = j.assign(bo=pd.to_numeric(bo[0], errors="coerce"), final=bo[1])
    j = j[j["bo"].isin([3, 5]) & j["final"].isin(list(FINALS))]
    steps.append(("rule bo3/bo5 x {tb, tb10, adv, tb12}", j))
    t = pd.read_parquet(TIMING, columns=["match_id", "obs"])
    j = j.merge(t, on="match_id", how="left", validate="one_to_one")
    j["surface"] = j["surface"].fillna("unknown")
    j = j.sort_values(["tour", "obs", "tournament_date", "round_order", "match_id"], kind="mergesort").reset_index(drop=True)
    j["mcode"] = np.arange(len(j), dtype=np.int64)
    j["bo"] = j["bo"].astype(np.int64)
    j["final_code"] = j["final"].map(FINALS).astype(np.int64)
    counts = [{"step": s, **{tr: int((f["tour"] == tr).sum()) for tr in ("atp", "wta")}} for s, f in steps]
    return j, {"steps": counts, "obs_missing": int(j["obs"].isna().sum())}


def real_points(pop: pd.DataFrame) -> dict:
    """The population's points as arrays sorted by (mcode, seq): m, set_no, game_idx, pt_no, is_tb, server, winner
    (1 = side A, 2 = side B)."""
    s = pd.read_parquet(OUT / "sequences.parquet",
                        columns=["match_id", "usable", "seq", "set_no", "game_no", "game_idx", "pt_no", "is_tb",
                                 "server", "winner"])
    s = s[s["usable"]]
    code = pd.Series(pop["mcode"].to_numpy(), index=pop["match_id"].to_numpy())
    mid = s["match_id"].astype(str)
    keep = mid.isin(code.index).to_numpy()
    s = s[keep]
    m = code.reindex(mid[keep].to_numpy()).to_numpy()
    order = np.lexsort((s["seq"].to_numpy(), m))
    return {"m": m[order].astype(np.int64),
            "set_no": s["set_no"].to_numpy()[order].astype(np.int16),
            "game_no": s["game_no"].to_numpy()[order].astype(np.int16),
            "game_idx": s["game_idx"].to_numpy()[order].astype(np.int32),
            "pt_no": s["pt_no"].to_numpy()[order].astype(np.int16),
            "is_tb": s["is_tb"].to_numpy()[order].astype(np.int8),
            "server": s["server"].to_numpy()[order].astype(np.int8),
            "winner": s["winner"].to_numpy()[order].astype(np.int8)}


# ------------------------------------------------------------------------------------------------
# Statistics

def _bc(idx, w, n):
    return np.bincount(idx, weights=np.asarray(w, dtype="float64"), minlength=n)


def point_stats(P: dict, n: int, late_set: np.ndarray | None = None) -> pd.DataFrame:
    """Per player-match statistics from points sorted by (m, point order). Returns 2n rows: side 1 (A) for every match
    code 0..n-1, then side 2 (B). Columns X_<stat>, D_<stat> for STATS, and totals. ``late_set``: per match, the set
    number of the late set for the between-set diagnostic (2 in best of three, 3 in best of five)."""
    m = P["m"]
    set_no = P["set_no"].astype(np.int64)
    gidx = P["game_idx"].astype(np.int64)
    pt_no = P["pt_no"].astype(np.int64)
    tb = P["is_tb"].astype(bool)
    srv = P["server"].astype(np.int64)
    win = P["winner"].astype(np.int64)
    npt = len(m)
    # ---- games
    start = np.ones(npt, dtype=bool)
    start[1:] = (m[1:] != m[:-1]) | (gidx[1:] != gidx[:-1])
    gid = np.cumsum(start) - 1
    G = int(gid[-1]) + 1
    first = np.flatnonzero(start)
    last = np.r_[first[1:] - 1, npt - 1]
    gm, gset, gtb = m[first], set_no[first], tb[first]
    gsrv, gwin = srv[first], win[last]
    gn = np.bincount(gid, minlength=G).astype("float64")
    swon = (win == srv)
    gsw = _bc(gid, swon, G)
    prev_same = np.zeros(G, dtype=bool)
    prev_same[1:] = (gm[1:] == gm[:-1]) & (gset[1:] == gset[:-1]) & ~gtb[:-1]
    prev_srv = np.r_[0, gsrv[:-1]]
    prev_win = np.r_[0, gwin[:-1]]
    prev2_same = np.zeros(G, dtype=bool)
    prev2_same[2:] = (gm[2:] == gm[:-2]) & (gset[2:] == gset[:-2]) & ~gtb[:-2]
    prev2_srv = np.r_[0, 0, gsrv[:-2]]
    prev2_win = np.r_[0, 0, gwin[:-2]]
    # ---- point level: score state before the point (regular games), previous point in the same game
    reg = ~tb
    cs = np.cumsum(swon.astype(np.int64))
    cs_before_game = (cs - swon)[first][gid]               # server points won before this game started
    s_before = (cs - swon) - cs_before_game                # server points won earlier in this game
    r_before = (pt_no - 1) - s_before
    deuce = (s_before >= 3) & (r_before >= 3)
    state = np.where(deuce, 16 + np.clip(s_before - r_before, -1, 1), np.clip(s_before, 0, 3) * 4 + np.clip(r_before, 0, 3))
    prev_won = np.r_[False, swon[:-1]]
    has_prev = reg & (pt_no >= 2)
    # runs within regular games: a change of outcome between consecutive points of the same game
    change = np.zeros(npt, dtype=bool)
    change[1:] = (gid[1:] == gid[:-1]) & (swon[1:] != swon[:-1])
    gchanges = _bc(gid, change, G)
    # per (match, set) serve points of each side
    out = {}
    for side in (1, 2):
        opp = 3 - side
        o = {}
        mine_g = (gsrv == side) & ~gtb
        theirs_g = (gsrv == opp) & ~gtb
        held = gwin == side
        # S1
        ab = mine_g & prev_same & (prev_srv == opp) & (prev_win == side)
        n1, h1 = _bc(gm, ab, n), _bc(gm, ab & held, n)
        ns, hs = _bc(gm, mine_g, n), _bc(gm, mine_g & held, n)
        n0, h0 = ns - n1, hs - h1
        okk = n0 > 0
        o["X_S1"] = np.where(okk, h1 - n1 * h0 / np.where(okk, n0, 1), 0.0)
        o["D_S1"] = np.where(okk, n1, 0.0)
        # S2
        bb = theirs_g & prev_same & (prev_srv == side) & (prev_win == opp)
        n1, b1 = _bc(gm, bb, n), _bc(gm, bb & held, n)
        nr, br = _bc(gm, theirs_g, n), _bc(gm, theirs_g & held, n)
        n0, b0 = nr - n1, br - b1
        okk = n0 > 0
        o["X_S2"] = np.where(okk, b1 - n1 * b0 / np.where(okk, n0, 1), 0.0)
        o["D_S2"] = np.where(okk, n1, 0.0)
        # P0
        ah = mine_g & prev2_same & (prev2_srv == side) & (prev2_win == side)
        n1, h1 = _bc(gm, ah, n), _bc(gm, ah & held, n)
        n0, h0 = ns - n1, hs - h1
        okk = n0 > 0
        o["X_P0"] = np.where(okk, h1 - n1 * h0 / np.where(okk, n0, 1), 0.0)
        o["D_P0"] = np.where(okk, n1, 0.0)
        # S4: game-level dispersion of serve points won in the player's regular service games
        w_g, n_g = np.where(mine_g, gsw, 0.0), np.where(mine_g, gn, 0.0)
        N, W = _bc(gm, n_g, n), _bc(gm, w_g, n)
        Sww, Swn, Snn = _bc(gm, w_g * w_g, n), _bc(gm, w_g * n_g, n), _bc(gm, n_g * n_g, n)
        ph = np.divide(W, N, out=np.zeros(n), where=N > 0)
        var = N * ph * (1 - ph)
        o["X_S4"] = np.where(var > 0, Sww - 2 * ph * Swn + ph * ph * Snn - var, 0.0)
        o["D_S4"] = var
        # S4r: runs within service games
        a, b = w_g, n_g - w_g
        both = mine_g & (a > 0) & (b > 0)
        nn = np.where(both, n_g, 2.0)
        E = 1 + 2 * a * b / nn
        V = 2 * a * b * (2 * a * b - nn) / (nn * nn * (nn - 1))
        R = 1 + gchanges
        o["X_S4r"] = _bc(gm, np.where(both, E - R, 0.0), n)
        o["D_S4r"] = _bc(gm, np.where(both, V, 0.0), n)
        o["svc_games"], o["holds"] = ns, hs
        o["ret_games"], o["breaks"] = nr, br
        # serve points (all, tie-breaks included), per set and in total
        sp = srv == side
        key = m * 8 + np.clip(set_no, 0, 7)
        nk = _bc(key[sp], np.ones(int(sp.sum())), n * 8).reshape(n, 8)
        wk = _bc(key[sp], swon[sp], n * 8).reshape(n, 8)
        Nt, Wt = nk.sum(1), wk.sum(1)
        ph = np.divide(Wt, Nt, out=np.zeros(n), where=Nt > 0)
        var = Nt * ph * (1 - ph)
        o["X_S5"] = np.where(var > 0, (wk * wk).sum(1) - 2 * ph * (wk * nk).sum(1) + ph * ph * (nk * nk).sum(1) - var, 0.0)
        o["D_S5"] = var
        o["svpt"], o["svpt_won"] = Nt, Wt
        o["set1_n"], o["set1_w"] = nk[:, 1], wk[:, 1]
        if late_set is not None:
            ls = np.clip(late_set.astype(np.int64), 0, 7)
            o["late_n"], o["late_w"] = nk[np.arange(n), ls], wk[np.arange(n), ls]
        # S3: within (match, side, state) cells, regular-game serve points with a previous point in the game
        sel = has_prev & sp
        ck = (m[sel] * 2 + (side - 1)) * 18 + state[sel]
        cu, cinv = np.unique(ck, return_inverse=True)
        x = prev_won[sel].astype("float64")
        y = swon[sel].astype("float64")
        xbar = np.bincount(cinv, weights=x) / np.bincount(cinv)
        dx = x - xbar[cinv]
        o["X_S3"] = _bc(m[sel], dx * y, n)
        o["D_S3"] = _bc(m[sel], dx * dx, n)
        out[side] = o
    # match-level totals for I2 (A's view)
    tot = {"pts": np.bincount(m, minlength=n).astype("float64"),
           "a_pts": _bc(m, win == 1, n),
           "tiebreaks": _bc(gm, gtb, n),
           "sets": np.zeros(n), "a_won": np.zeros(n)}
    lastpt = np.r_[np.flatnonzero(m[1:] != m[:-1]), npt - 1]
    tot["sets"][m[lastpt]] = set_no[lastpt]
    tot["a_won"][m[lastpt]] = (win[lastpt] == 1)
    rows = []
    for side in (1, 2):
        d = pd.DataFrame(out[side])
        d.insert(0, "side", side)
        d.insert(0, "mcode", np.arange(n, dtype=np.int64))
        rows.append(d)
    pm = pd.concat(rows, ignore_index=True)
    return pm, pd.DataFrame(tot)


# ------------------------------------------------------------------------------------------------
# The point-level iid replayer

def replay_points(pa: np.ndarray, pb: np.ndarray, bo: np.ndarray, final_code: np.ndarray, s0: np.ndarray,
                  rng: np.random.Generator, max_points: int = 20000) -> dict:
    """Play every match point by point, the server winning each point with their fixed probability. ``s0``: the first
    server (1 = A, 2 = B). Every set but the deciding one has a 7-point tie-break at 6-6; the deciding set follows
    final_code (FINALS: 0 tb, 1 a 10-point tie-break at 6-6, 2 advantage, 3 a 7-point tie-break at 12-12). The serve
    alternates by game over the match (a tie-break counts as one game); in a tie-break its first server serves one
    point, then two each. Returns the arrays of real_points(), sorted by (m, point order)."""
    n = len(pa)
    p_srv = np.stack([np.asarray(pa, "float64"), np.asarray(pb, "float64")], axis=1)
    need = (np.asarray(bo, np.int64) + 1) // 2
    fc = np.asarray(final_code, np.int64)
    first = np.asarray(s0, np.int64) - 1
    sets = np.zeros((n, 2), np.int64)
    games = np.zeros((n, 2), np.int64)
    pts = np.zeros((n, 2), np.int64)
    gi = np.zeros(n, np.int64)
    set_no = np.ones(n, np.int64)
    in_tb = np.zeros(n, bool)
    target = np.full(n, 4, np.int64)
    done = np.zeros(n, bool)
    rec = {k: [] for k in ("m", "set_no", "game_no", "game_idx", "pt_no", "is_tb", "server", "winner")}
    active = np.arange(n)
    for _ in range(max_points):
        if active.size == 0:
            break
        idx = active
        k = pts[idx, 0] + pts[idx, 1]
        gsrv = np.where(gi[idx] % 2 == 0, first[idx], 1 - first[idx])
        flip = in_tb[idx] & ((((k + 1) // 2) % 2) == 1)
        sv = np.where(flip, 1 - gsrv, gsrv)
        won = rng.random(idx.size) < p_srv[idx, sv]
        pw = np.where(won, sv, 1 - sv)
        rec["m"].append(idx)
        rec["set_no"].append(set_no[idx].astype(np.int16))
        rec["game_no"].append((games[idx, 0] + games[idx, 1] + 1).astype(np.int16))
        rec["game_idx"].append(gi[idx].astype(np.int32))
        rec["pt_no"].append((k + 1).astype(np.int16))
        rec["is_tb"].append(in_tb[idx].astype(np.int8))
        rec["server"].append((sv + 1).astype(np.int8))
        rec["winner"].append((pw + 1).astype(np.int8))
        pts[idx, pw] += 1
        hi = pts[idx, pw]
        lo = pts[idx, 1 - pw]
        over = (hi >= target[idx]) & (hi - lo >= 2)
        g, gw = idx[over], pw[over]
        if g.size:
            was_tb = in_tb[g].copy()
            games[g, gw] += 1
            pts[g] = 0
            gi[g] += 1
            in_tb[g] = False
            target[g] = 4
            gwin, glose = games[g, gw], games[g, 1 - gw]
            set_over = was_tb | ((gwin >= 6) & (gwin - glose >= 2))
            so, sw = g[set_over], gw[set_over]
            sets[so, sw] += 1
            games[so] = 0
            set_no[so] += 1
            fin = sets[so, sw] >= need[so]
            done[so[fin]] = True
            # a tie-break starts the next game where the set is level at its tie-break score
            cont = g[~set_over]
            if cont.size:
                deciding = (sets[cont, 0] == need[cont] - 1) & (sets[cont, 1] == need[cont] - 1)
                f = fc[cont]
                tb_at = np.where(deciding & (f == 3), 12, np.where(deciding & (f == 2), -1, 6))
                start_tb = (games[cont, 0] == tb_at) & (games[cont, 1] == tb_at)
                st = cont[start_tb]
                in_tb[st] = True
                target[st] = np.where(deciding[start_tb] & (f[start_tb] == 1), 10, 7)
            active = active[~done[active]]
    if not done.all():
        raise RuntimeError(f"{int((~done).sum())} replayed matches unfinished after {max_points} points")
    m = np.concatenate(rec["m"])
    order = np.argsort(m, kind="stable")
    return {k: np.concatenate(v)[order] for k, v in rec.items()}


# ------------------------------------------------------------------------------------------------
# De-noised day rates with priors frozen on seasons <= 2018

def fit_priors(rows: pd.DataFrame) -> dict:
    """rows: one per player-match with tour, surface, year, P (measured serve rate), N (serve points), player, and
    the season. Fitted on rows with year <= 2018 only. Per tour x surface: mean, measured variance, true variance
    (measured less mean noise); groups under 400 rows use the tour's. Per tour, for VPS: the within-player-season
    true day variance v_w and the between-player-season variance v_b = v - v_w (residuals from the surface mean)."""
    r = rows[rows["year"] <= PRIOR_LAST_YEAR]
    pri = {"groups": {}, "tour": {}, "vps": {}, "rows_used": int(len(r))}
    for tour, g in r.groupby("tour"):
        P, N = g["P"].to_numpy(), g["N"].to_numpy()
        noise = P * (1 - P) / N
        mu, var = float(P.mean()), float(P.var())
        pri["tour"][tour] = {"mu": mu, "var": var, "v": max(var - float(noise.mean()), 1e-6), "rows": int(len(g))}
        for sf, h in g.groupby("surface"):
            Ph, Nh = h["P"].to_numpy(), h["N"].to_numpy()
            nh = Ph * (1 - Ph) / Nh
            if len(h) >= 400:
                v = max(float(Ph.var()) - float(nh.mean()), 1e-6)
                pri["groups"][f"{tour}|{sf}"] = {"mu": float(Ph.mean()), "var": float(Ph.var()), "v": v,
                                                 "rows": int(len(h)), "own": True}
            else:
                pri["groups"][f"{tour}|{sf}"] = {**pri["tour"][tour], "rows": int(len(h)), "own": False}
    for tour, g in r.groupby("tour"):
        mu = np.array([prior_of(pri, tour, s)["mu"] for s in g["surface"]])
        e = g["P"].to_numpy() - mu
        noise = g["P"].to_numpy() * (1 - g["P"].to_numpy()) / g["N"].to_numpy()
        d = pd.DataFrame({"ps": g["player"].astype(str) + "|" + g["year"].astype(str), "e": e, "noise": noise})
        grp = d.groupby("ps")
        cnt = grp["e"].transform("size")
        dd = d[cnt >= 2]
        within = dd.groupby("ps")["e"].var(ddof=1)
        wn = dd.groupby("ps")["noise"].mean()
        size = dd.groupby("ps").size()
        vw = max(float(np.average(within - wn, weights=size - 1)), 1e-6)
        v = float(np.average([pri["groups"][f"{tour}|{s}"]["v"] for s in g["surface"]]))
        pri["vps"][tour] = {"v_w": vw, "v_b": max(v - vw, 1e-6), "v": v, "player_seasons": int(within.size)}
    return pri


def prior_of(pri: dict, tour: str, surface: str) -> dict:
    return pri["groups"].get(f"{tour}|{surface}", pri["tour"][tour])


def draw_rates(rows: pd.DataFrame, pri: dict, variant: str, rng: np.random.Generator) -> np.ndarray:
    """A true day rate per player-match row (rows as for fit_priors, every year), under a variant: V1/V05/V15 scale the
    tour x surface true variance; VPS centres the prior on the player's leave-one-out season residual."""
    P, N = rows["P"].to_numpy("float64"), rows["N"].to_numpy("float64")
    noise = P * (1 - P) / N
    keys = rows["tour"].astype(str) + "|" + rows["surface"].astype(str)
    mu = keys.map(lambda k: pri["groups"].get(k, pri["tour"][k.split("|")[0]])["mu"]).to_numpy("float64")
    v = keys.map(lambda k: pri["groups"].get(k, pri["tour"][k.split("|")[0]])["v"]).to_numpy("float64")
    if variant != "VPS":
        vt = v * VARIANTS[variant]
        centre, vprior = mu, vt
    else:
        e = P - mu
        ps = rows["player"].astype(str) + "|" + rows["year"].astype(str)
        s_e = pd.Series(e).groupby(ps.to_numpy()).transform("sum").to_numpy()
        s_n = pd.Series(np.ones(len(e))).groupby(ps.to_numpy()).transform("sum").to_numpy()
        s_noise = pd.Series(noise).groupby(ps.to_numpy()).transform("sum").to_numpy()
        k = s_n - 1
        loo = np.divide(s_e - e, k, out=np.zeros(len(e)), where=k > 0)
        noise_loo = np.divide(s_noise - noise, k, out=np.zeros(len(e)), where=k > 0)
        vw = rows["tour"].map(lambda t: pri["vps"][t]["v_w"]).to_numpy("float64")
        vb = rows["tour"].map(lambda t: pri["vps"][t]["v_b"]).to_numpy("float64")
        lam = np.where(k > 0, vb / (vb + (vw + noise_loo) / np.maximum(k, 1)), 0.0)
        centre = mu + lam * loo
        vprior = np.where(k > 0, vw + vb * (1 - lam), v)
    s = vprior / (vprior + noise)
    draw = rng.normal(centre + s * (P - centre), np.sqrt(s * noise))
    return np.clip(draw, 0.02, 0.98)


def player_match_rates(pop: pd.DataFrame, pm: pd.DataFrame) -> pd.DataFrame:
    """Rows for fit_priors / draw_rates from the real statistics frame (2 rows per match, side 1 then 2)."""
    n = len(pop)
    side = pm["side"].to_numpy()
    mc = pm["mcode"].to_numpy()
    player = np.where(side == 1, pop["player_a_id"].to_numpy()[mc], pop["player_b_id"].to_numpy()[mc])
    out = pd.DataFrame({"mcode": mc, "side": side, "tour": pop["tour"].to_numpy()[mc],
                        "surface": pop["surface"].to_numpy()[mc], "year": pop["year"].to_numpy()[mc],
                        "player": player, "N": pm["svpt"].to_numpy(), "P": pm["svpt_won"].to_numpy() / pm["svpt"].to_numpy()})
    assert len(out) == 2 * n
    return out
