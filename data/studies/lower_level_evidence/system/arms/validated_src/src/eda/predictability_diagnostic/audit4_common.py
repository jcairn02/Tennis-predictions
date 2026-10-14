"""Audit B of Stage 4: shared helpers, written for the audit and independent of Stage 4's code.

Nothing here imports stage4_features.py or stage4_rundown.py. The audit reads the Stage 0 tables, the earlier
stages' frozen constants (which the plan names) and Stage 4's outputs, and recomputes what it checks with its own code:

    tables          the Stage 0 matches and player rows, with each match's side A and B
    time rule       a feature for a match may use the player's matches of earlier tournament dates and the same
                    event's earlier rounds; never the match itself, its round, later rounds or the week's other events.
                    Here it is applied through the table's global order: every match of an earlier date has a smaller
                    order, and so does every match of the same date with a smaller round order (common.chrono_sort)
    iid model       the chance of winning a match from the two serve-point rates, by exact recursion over the score
    rating passes   Stage 1's Elo with each update weighted (the games-weighted Elo), and Stage 3's serve and return
                    ratings, both under the time rule, organised week by week, event by event, round by round
    scorer          the plan's walk-forward logistic regression without an intercept, with the plan's shuffled copies

Outputs of the audit go to data/studies/predictability_diagnostic/audit4/.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "studies" / "predictability_diagnostic"
DOCS = ROOT / "docs" / "studies" / "predictability_diagnostic"
AUDIT = OUT / "audit4"
SEED = 20261002                       # the audit's own draws
PLAN_SEED = 20261001                  # Stage 4's seed: the shuffled copies' keys are drawn with it (the plan's keys)
COPIES = 20
MIN_TRAIN = 300
RIDGE = 1e-6                          # Stage 4's numerical guard, kept so that its numbers can be reproduced
SHARE_CLIP = 1e-4
HALF_LIFE = 52
WEEK52 = 364
SURFACES = ("Hard", "Clay", "Grass", "Carpet")
EVAL_LEVELS = ("GS", "FIN", "T1000", "T500", "T250", "CH")
MAIN_TOUR = ("GS", "FIN", "T1000", "T500", "T250")
RATES = ("spw", "rpw", "tpw", "hold", "brk", "ace", "df", "first_in", "first_won", "second_won", "bp_saved",
         "bp_conv", "bp_faced_pg", "tb_won", "sets_won", "games_won")
ERAS = {"2013-16": (2013, 2016), "2017-19": (2017, 2019), "2020-21": (2020, 2021), "2022-26": (2022, 2026)}


def log(msg: str, t0=[None]) -> None:
    import time
    if t0[0] is None:
        t0[0] = time.time()
    print(f"[{time.time() - t0[0]:7.1f}s] {msg}", flush=True)


def save_json(obj, name: str) -> Path:
    AUDIT.mkdir(parents=True, exist_ok=True)
    p = AUDIT / name
    p.write_text(json.dumps(obj, indent=1, default=_json_default), encoding="utf-8")
    return p


def _json_default(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return None if not np.isfinite(x) else float(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (pd.Timestamp,)):
        return x.isoformat()
    raise TypeError(type(x))


def logit(p):
    p = np.asarray(p, dtype="float64")
    return np.log(p / (1 - p))


def expit(x):
    return 1.0 / (1.0 + np.exp(-np.asarray(x, dtype="float64")))


def safe_logit(p):
    return logit(np.clip(np.asarray(p, dtype="float64"), SHARE_CLIP, 1 - SHARE_CLIP))


# ------------------------------------------------------------------------------------------------
# Tables

MATCH_COLS = ["match_id", "tour", "year", "level", "qualifying", "evaluation", "round", "round_order", "surface",
              "best_of", "tournament_id", "tournament_name", "tournament_date", "status", "score", "minutes", "format",
              "has_box", "player_a_id", "player_b_id", "a_won", "order"]
PLAYER_COLS = ["match_id", "player_id", "side", "won", "rank", "rank_points", "entry", "age", "height", "hand",
               "country"] + [f"{r}_{x}" for r in RATES for x in ("n", "d")]


def load_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    """The Stage 0 matches in their chronological order and the player rows aligned to them: match i's side A is
    player row 2i, its side B row 2i + 1. Derived: the tournament date in days, the event (tournament id and date),
    and the surface code (0 unknown, 1-4 as SURFACES)."""
    m = pd.read_parquet(OUT / "stage0_matches.parquet", columns=MATCH_COLS)
    m = m.sort_values("order", kind="mergesort").reset_index(drop=True)
    assert (m["order"].to_numpy() == np.arange(len(m))).all(), "order is not 0..n-1"
    m["day"] = m["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    m["ev"] = pd.factorize(m["tournament_id"].astype(str) + "|" + m["tournament_date"].astype(str))[0]
    m["surf"] = m["surface"].map({s: i + 1 for i, s in enumerate(SURFACES)}).fillna(0).astype("int64")
    p = pd.read_parquet(OUT / "stage0_match_players.parquet", columns=PLAYER_COLS)
    pos = pd.Series(np.arange(len(m)), index=m["match_id"].to_numpy())
    p["_m"] = pos.reindex(p["match_id"].to_numpy()).to_numpy()
    p["_s"] = (p["side"] == "B").astype("int64")
    p = p.sort_values(["_m", "_s"], kind="mergesort").reset_index(drop=True)
    assert (p["_m"].to_numpy() == np.repeat(np.arange(len(m)), 2)).all()
    assert (p["player_id"].to_numpy()[0::2] == m["player_a_id"].to_numpy()).all()
    assert (p["player_id"].to_numpy()[1::2] == m["player_b_id"].to_numpy()).all()
    assert (p["won"].to_numpy()[0::2] == m["a_won"].to_numpy()).all()
    return m, p.drop(columns=["_s"])


def player_codes(p: pd.DataFrame) -> np.ndarray:
    return pd.factorize(p["player_id"])[0].astype("int64")


# ------------------------------------------------------------------------------------------------
# The time rule through the global order

def order_thresholds(m: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Per match: T_day, the smallest order of any match on its tournament date (every match of an earlier date has
    a smaller order), and T_round, the smallest order of any match on its date with its round order (every match of
    the same date and a smaller round order has a smaller order, and so does nothing else of that date)."""
    day, rnd, order = m["day"].to_numpy(), m["round_order"].to_numpy(), m["order"].to_numpy()
    t_day = pd.Series(order).groupby(day).transform("min").to_numpy()
    t_round = pd.Series(order).groupby([day, rnd]).transform("min").to_numpy()
    # the order really is date, then round order (common.chrono_sort): check it
    assert (np.diff(day) >= 0).all()
    same = np.diff(day) == 0
    assert (np.diff(rnd)[same] >= 0).all()
    return t_day, t_round


def first_order_from_day(m: pd.DataFrame, days: np.ndarray) -> np.ndarray:
    """The smallest order among matches with a tournament date on or after each given day."""
    d = m["day"].to_numpy()
    return np.searchsorted(d, np.asarray(days), side="left")


# ------------------------------------------------------------------------------------------------
# Constants the plan names (frozen by earlier stages, or set by Stage 4 before scoring)

def constants() -> dict:
    s3 = json.loads((OUT / "stage3_results.json").read_text(encoding="utf-8"))
    c4 = pd.read_csv(OUT / "stage4_constants.csv")
    shr = pd.read_csv(OUT / "stage3_shrinkage.csv")
    means: dict = {}
    for r in s3["surface_means"]:
        means[(r["stat"], r["tour"], r["surface"])] = float(r["mean"])
    for r in c4[c4["kind"].eq("surface average")].itertuples(index=False):
        if r.stat not in RATES:
            means[(r.stat, r.tour, r.surface)] = float(r.value)
    K: dict = {}
    for r in shr[shr["years"].eq("2010-2018") & shr["surface"].eq("all")].itertuples(index=False):
        K[(r.stat, r.tour)] = float(r.K_units)
    for r in c4[c4["kind"].eq("shrinkage K") & c4["surface"].eq("all")].itertuples(index=False):
        if r.stat not in RATES:
            K[(r.stat, r.tour)] = float(r.value)
    b = json.loads((OUT / "stage1_baselines_summary.json").read_text(encoding="utf-8"))
    elo = {c["tour"]: c for c in b["chosen"] if c["rule"] == "ret"}
    r3 = json.loads((OUT / "stage3_ratings_summary.json").read_text(encoding="utf-8"))
    return {"means": means, "K": K, "elo": elo, "s3": r3["chosen"], "s3_mu": r3["surface_means"],
            "elo_scale": {(r.stat, r.tour): float(r.value) for r in c4[c4["kind"].eq("weighted Elo scale")].itertuples()}}


def mean_for(ctx: dict, stat: str, tour, surface) -> np.ndarray:
    """The tour's average of a statistic on each surface (the tour's over all surfaces where unknown)."""
    tour = np.asarray(tour, dtype=object)
    surface = np.asarray(surface, dtype=object)
    out = np.empty(len(tour))
    for i, (t, s) in enumerate(zip(tour, surface)):
        key = s if s in SURFACES else "all"
        out[i] = ctx["means"][(stat, t, key)]
    return out


def shrunk(mu_here, sum_centred, sum_units, K):
    """The plan's shrunk form (candidates.md, section 2): this surface's tour average plus the history's centred
    count over its units plus K."""
    return mu_here + sum_centred / (sum_units + K)


def combine(srv, ret, mu):
    """A server's expected rate against a returner on the log-odds scale (candidates.md, section 2): log-odds mu, plus
    the server's log-odds above mu, minus the returner's log-odds above 1 - mu; mu the serve statistic's average."""
    mu = np.clip(np.asarray(mu, dtype="float64"), SHARE_CLIP, 1 - SHARE_CLIP)
    return expit(logit(mu) + (safe_logit(srv) - logit(mu)) - (safe_logit(ret) - logit(1 - mu)))


# ------------------------------------------------------------------------------------------------
# Formats

@lru_cache(maxsize=1)
def slam_table() -> pd.DataFrame:
    return pd.read_csv(OUT / "stage2_slam_final_set_rules.csv", dtype={"tiebreak_at": "Int64", "tiebreak_points": "Int64"})


def slam_code(name: str) -> str | None:
    n = str(name).lower()
    if "aus open" in n or "australian open" in n:
        return "AO"
    if "roland garros" in n or "french open" in n:
        return "RG"
    if "wimbledon" in n:
        return "WIM"
    if "us open" in n:
        return "USO"
    return None


def final_rule(level: str, name: str, year: int, qualifying: bool) -> tuple:
    """The deciding set's rule as (games all at which a tiebreak is played or None for an advantage set, tiebreak
    points): the Grand Slams' hand-made table (Stage 2), a 7-point tiebreak at 6-6 everywhere else."""
    if level != "GS":
        return (6, 7)
    code = slam_code(name)
    t = slam_table()
    hit = t[t["slam"].eq(code) & t["draw"].eq("qualifying" if qualifying else "main")
            & (t["first_year"] <= year) & (t["last_year"] >= year)]
    assert len(hit) == 1, (name, year, qualifying)
    r = hit.iloc[0]
    if r["final_set"] == "advantage":
        return (None, 0)
    return (int(r["tiebreak_at"]), int(r["tiebreak_points"]))


# ------------------------------------------------------------------------------------------------
# The iid model, exact recursion over the score (scalar)

def p_hold(p: float) -> float:
    """P(the server wins a game), each serve point won with probability p: a race to 4 points, won by two."""
    @lru_cache(maxsize=None)
    def g(i, j):
        if i >= 4 and i - j >= 2:
            return 1.0
        if j >= 4 and j - i >= 2:
            return 0.0
        if i >= 3 and j >= 3 and i == j:            # deuce: two points in a row first
            return p * p / (p * p + (1 - p) * (1 - p)) if (p * p + (1 - p) * (1 - p)) > 0 else 0.5
        return p * g(i + 1, j) + (1 - p) * g(i, j + 1)
    return g(0, 0)


def p_tiebreak(pa: float, pb: float, target: int) -> float:
    """P(A wins a tiebreak to ``target``, won by two), A serving its first point, then B two, A two, ..."""
    def a_serves(k):        # point k (0-indexed)
        return k == 0 or ((k + 1) // 2) % 2 == 0

    @lru_cache(maxsize=None)
    def t(i, j):
        if i >= target and i - j >= 2:
            return 1.0
        if j >= target and j - i >= 2:
            return 0.0
        if i == j and i >= target - 1:
            # from level at target - 1 or more, every two points hold one serve each: win both, or lose both
            w = pa * (1 - pb)
            lo = (1 - pa) * pb
            return w / (w + lo) if w + lo > 0 else 0.5
        q = pa if a_serves(i + j) else 1 - pb
        return q * t(i + 1, j) + (1 - q) * t(i, j + 1)
    return t(0, 0)


def p_set(pa: float, pb: float, rule: tuple) -> float:
    """P(A wins a set), A serving first: first to six games by two, a tiebreak at rule[0]-all (rule[1] points), or
    an advantage set (rule[0] None)."""
    ha, hb = p_hold(pa), p_hold(pb)
    tb_at, tb_pts = rule

    @lru_cache(maxsize=None)
    def s(i, j):
        if (i >= 6 and i - j >= 2) or (tb_at is not None and i == tb_at + 1 and j == tb_at):
            return 1.0
        if (j >= 6 and j - i >= 2) or (tb_at is not None and j == tb_at + 1 and i == tb_at):
            return 0.0
        if tb_at is not None and i == tb_at and j == tb_at:
            return p_tiebreak(pa, pb, tb_pts) if (i + j) % 2 == 0 else 1 - p_tiebreak(pb, pa, tb_pts)
        if tb_at is None and i == j and i >= 5:
            w = ha * (1 - hb)
            lo = (1 - ha) * hb
            return w / (w + lo) if w + lo > 0 else 0.5
        q = ha if (i + j) % 2 == 0 else 1 - hb
        return q * s(i + 1, j) + (1 - q) * s(i, j + 1)
    return s(0, 0)


def p_match(pa: float, pb: float, best_of: int, rule: tuple, match_tiebreak: bool = False) -> float:
    """P(A wins the match): every set a standard set (tiebreak at 6-6) but the deciding one, which follows ``rule``,
    or is a 10-point match tiebreak."""
    s = p_set(pa, pb, (6, 7))
    f = p_tiebreak(pa, pb, 10) if match_tiebreak else p_set(pa, pb, rule)
    need = (best_of + 1) // 2

    @lru_cache(maxsize=None)
    def m(i, j):
        if i == need:
            return 1.0
        if j == need:
            return 0.0
        q = f if (i == need - 1 and j == need - 1) else s
        return q * m(i + 1, j) + (1 - q) * m(i, j + 1)
    return m(0, 0)


def serve_for_hold(h: float) -> float:
    """The serve-point rate whose hold rate is h (p_hold inverted; p_hold rises with p)."""
    from scipy.optimize import brentq
    h = min(max(h, 1e-9), 1 - 1e-9)
    return brentq(lambda p: p_hold(p) - h, 1e-6, 1 - 1e-6, xtol=1e-14, rtol=1e-14, maxiter=200)


# ------------------------------------------------------------------------------------------------
# Rating passes under the time rule, organised by week, event and round

def week_structure(week, event, rnd, idx) -> list:
    """The matches ``idx`` (in table order) grouped: [(week, [(event, [(round, [match, ...]), ...]), ...]), ...], and
    per week the order in which each (player, event) pair first appears is kept by the caller."""
    out = []
    i, n = 0, len(idx)
    while i < n:
        wk = week[idx[i]]
        j = i
        while j < n and week[idx[j]] == wk:
            j += 1
        evs: dict = {}
        for k in idx[i:j]:
            evs.setdefault(event[k], {}).setdefault(rnd[k], []).append(k)
        out.append((wk, [(e, sorted(r.items())) for e, r in evs.items()]))
        i = j
    return out


def elo_pass(idx, week, event, rnd, a, b, a_won, surf, upd, wgt, k0, offset, shape, n_players) -> dict:
    """Stage 1's Elo (overall and per surface) with each update multiplied by the match's weight. A rating used for
    a match is the player's rating at the start of the week plus what their earlier rounds of the same event added;
    what an event adds reaches the player's other events after the week. Returns {match: (A overall, B overall,
    A surface, B surface)} before the match (surface values None where the surface is unknown)."""
    R = [1500.0] * n_players
    N = [0] * n_players
    RS = [[1500.0] * n_players for _ in range(4)]
    NS = [[0] * n_players for _ in range(4)]
    out = {}
    for wk, events in week_structure(week, event, rnd, idx):
        week_acc = []
        for e, rounds in events:
            acc: dict = {}                  # player -> [dR, dN, {s: [dRS, dNS]}]
            for r, ms in rounds:
                pend: dict = {}
                for k in ms:
                    pa, pb, s = a[k], b[k], surf[k]
                    xa, xb = acc.get(pa), acc.get(pb)
                    ra = R[pa] + (xa[0] if xa else 0.0)
                    rb = R[pb] + (xb[0] if xb else 0.0)
                    na = N[pa] + (xa[1] if xa else 0)
                    nb = N[pb] + (xb[1] if xb else 0)
                    if s > 0:
                        sa = RS[s - 1][pa] + (xa[2].get(s, (0.0, 0))[0] if xa else 0.0)
                        sb = RS[s - 1][pb] + (xb[2].get(s, (0.0, 0))[0] if xb else 0.0)
                        nsa = NS[s - 1][pa] + (xa[2].get(s, (0.0, 0))[1] if xa else 0)
                        nsb = NS[s - 1][pb] + (xb[2].get(s, (0.0, 0))[1] if xb else 0)
                    else:
                        sa = sb = None
                    out[k] = (ra, rb, sa, sb)
                    if not upd[k]:
                        continue
                    res = 1.0 if a_won[k] else 0.0
                    sur = res - 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))
                    da = wgt[k] * k0 / (na + offset) ** shape * sur
                    db = -wgt[k] * k0 / (nb + offset) ** shape * sur
                    pend.setdefault(pa, [0.0, 0, {}])
                    pend.setdefault(pb, [0.0, 0, {}])
                    pend[pa][0] += da
                    pend[pa][1] += 1
                    pend[pb][0] += db
                    pend[pb][1] += 1
                    if s > 0:
                        sur = res - 1.0 / (1.0 + 10.0 ** ((sb - sa) / 400.0))
                        dsa = wgt[k] * k0 / (nsa + offset) ** shape * sur
                        dsb = -wgt[k] * k0 / (nsb + offset) ** shape * sur
                        for p_, d_ in ((pa, dsa), (pb, dsb)):
                            v = pend[p_][2].get(s, [0.0, 0])
                            pend[p_][2][s] = [v[0] + d_, v[1] + 1]
                for p_, d_ in pend.items():            # the round's updates reach the event's later rounds
                    x = acc.setdefault(p_, [0.0, 0, {}])
                    x[0] += d_[0]
                    x[1] += d_[1]
                    for s, v in d_[2].items():
                        w = x[2].get(s, (0.0, 0))
                        x[2][s] = (w[0] + v[0], w[1] + v[1])
            week_acc.append(acc)
        for acc in week_acc:                            # the week's events reach everything after the week
            for p_, d_ in acc.items():
                R[p_] += d_[0]
                N[p_] += d_[1]
                for s, v in d_[2].items():
                    RS[s - 1][p_] += v[0]
                    NS[s - 1][p_] += v[1]
    return out


VAR_FLOOR = 1e-5


def s3_pass(idx, week, event, rnd, a, b, mu, upd, n_a, w_a, n_b, w_b, n_players, var_serve, var_return, drift,
            start_serve, start_return=0.0) -> dict:
    """Stage 3's serve and return ratings (stage3_ratings.py's model: one Newton step of a Gaussian rating on the
    serve points of each match, both ways; variances widen with time away, up to a newcomer's) under the time rule.
    Returns {match: (S_A, S_B, R_A, R_B)} before the match."""
    S = [float(start_serve)] * n_players
    R = [float(start_return)] * n_players
    VS = [float(var_serve)] * n_players
    VR = [float(var_return)] * n_players
    LW = [None] * n_players
    out = {}
    ex = math.exp
    for wk, events in week_structure(week, event, rnd, idx):
        # drift: every player who plays this week, against the last week they played
        seen = set()
        first_seen = []                                   # (player, event) in table order, for the week-end updates
        for e, rounds in events:
            for r, ms in rounds:
                for k in ms:
                    for p_ in (a[k], b[k]):
                        seen.add(p_)
        for p_ in seen:
            last = LW[p_]
            if last is not None and drift > 0.0 and last != wk:
                grow = drift * (wk - last) / 7.0
                VS[p_] = min(VS[p_] + grow, var_serve)
                VR[p_] = min(VR[p_] + grow, var_return)
            LW[p_] = wk
        week_acc = {}
        for e, rounds in events:
            acc: dict = {}                                # player -> [dS, dR, dVS, dVR]
            for r, ms in rounds:
                pend: dict = {}
                for k in ms:
                    pa, pb = a[k], b[k]
                    xa = acc.get(pa, (0.0, 0.0, 0.0, 0.0))
                    xb = acc.get(pb, (0.0, 0.0, 0.0, 0.0))
                    sa, ra = S[pa] + xa[0], R[pa] + xa[1]
                    sb, rb = S[pb] + xb[0], R[pb] + xb[1]
                    vsa, vra = max(VS[pa] + xa[2], VAR_FLOOR), max(VR[pa] + xa[3], VAR_FLOOR)
                    vsb, vrb = max(VS[pb] + xb[2], VAR_FLOOR), max(VR[pb] + xb[3], VAR_FLOOR)
                    out[k] = (sa, sb, ra, rb)
                    if not upd[k]:
                        continue
                    m_ = mu[k]
                    for n, w, s_srv, v_srv, r_ret, v_ret, srv, ret in ((n_a[k], w_a[k], sa, vsa, rb, vrb, pa, pb),
                                                                      (n_b[k], w_b[k], sb, vsb, ra, vra, pb, pa)):
                        if n <= 0:
                            continue
                        p = 1.0 / (1.0 + ex(-(m_ + s_srv - r_ret)))
                        g = w - n * p
                        h = n * p * (1.0 - p)
                        den = 1.0 + (v_srv + v_ret) * h
                        ps = pend.setdefault(srv, [0.0, 0.0, 0.0, 0.0])
                        pr = pend.setdefault(ret, [0.0, 0.0, 0.0, 0.0])
                        ps[0] += v_srv * g / den
                        ps[2] -= v_srv * v_srv * h / den
                        pr[1] -= v_ret * g / den
                        pr[3] -= v_ret * v_ret * h / den
                for p_, d_ in pend.items():
                    x = acc.get(p_, (0.0, 0.0, 0.0, 0.0))
                    acc[p_] = (x[0] + d_[0], x[1] + d_[1], x[2] + d_[2], x[3] + d_[3])
            week_acc[e] = acc
        # week end, in the order each (player, event) first appeared in the table (the variance floor is applied
        # per event, as Stage 3 applies it)
        order_pe = []
        seen_pe = set()
        firsts = []
        for e, rounds in events:
            for r, ms in rounds:
                for k in ms:
                    for p_ in (a[k], b[k]):
                        firsts.append((k, p_, e))
        firsts.sort(key=lambda x: x[0])
        for k, p_, e in firsts:
            if (p_, e) in seen_pe:
                continue
            seen_pe.add((p_, e))
            order_pe.append((p_, e))
        for p_, e in order_pe:
            d_ = week_acc[e].get(p_)
            if d_ is None:
                continue
            S[p_] += d_[0]
            R[p_] += d_[1]
            VS[p_] = max(VS[p_] + d_[2], VAR_FLOOR)
            VR[p_] = max(VR[p_] + d_[3], VAR_FLOOR)
    return out


# ------------------------------------------------------------------------------------------------
# The scorer: walk-forward logistic regression without an intercept, with the plan's shuffled copies

def newton(Z: np.ndarray, y: np.ndarray, iters: int = 100, tol: float = 1e-11) -> np.ndarray:
    """Maximum-likelihood coefficients (no intercept) for C design matrices at once: Z (C, n, k), y (n,).
    Iteratively reweighted least squares, steps capped at 4, with Stage 4's tiny ridge."""
    C, n, k = Z.shape
    beta = np.zeros((C, k))
    yf = y.astype("float64")
    eye = np.eye(k) * RIDGE
    for _ in range(iters):
        eta = np.einsum("cnk,ck->cn", Z, beta)
        p = 1.0 / (1.0 + np.exp(-eta))
        g = np.einsum("cnk,cn->ck", Z, yf[None, :] - p) - RIDGE * beta
        W = p * (1 - p)
        H = np.einsum("cnk,cnl->ckl", Z * W[:, :, None], Z) + eye
        step = np.linalg.solve(H, g[:, :, None])[:, :, 0]
        big = np.abs(step).max(axis=1, keepdims=True)
        step = np.where(big > 4, step * 4 / np.maximum(big, 1e-300), step)
        beta = beta + step
        if np.abs(step).max() < tol:
            break
    return beta


def loss(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return np.where(y, -np.log(p), -np.log(1 - p))


def plan_keys(n_rows: int) -> np.ndarray:
    """The plan's 20 random keys per match of stage4_features.parquet (every row of the table, in its order)."""
    return np.random.default_rng(PLAN_SEED).random((n_rows, COPIES))


def shuffle_copies(X: np.ndarray, year: np.ndarray, keys: np.ndarray) -> np.ndarray:
    """COPIES copies of X (n, q) permuted within each season: inside a season, the match with the j-th smallest key
    of copy c receives the value of the season's j-th match in the table's order (the plan's shared keys)."""
    out = np.empty((COPIES,) + X.shape)
    for s in np.unique(year):
        pos = np.flatnonzero(year == s)                   # the season's matches, in table order
        for c in range(COPIES):
            ranked = pos[np.argsort(keys[pos, c], kind="stable")]
            out[c, ranked] = X[pos]
    return out


def walk_forward(Xs: np.ndarray, y: np.ndarray, year: np.ndarray, base: np.ndarray | None, first: int,
                 copies: np.ndarray | None = None) -> dict:
    """Per match (rows sorted by season): the baseline's log loss and the model's (real feature first, then each
    copy), walk-forward by season from ``first`` to 2026: each season fitted on every earlier match of the subset.
    A season is skipped when its training set holds fewer than MIN_TRAIN matches, or fewer than MIN_TRAIN on which
    the feature is not zero. base: the baseline's one input (log-odds), or None for a coin."""
    assert (np.diff(year) >= 0).all()
    Xall = Xs[None] if copies is None else np.concatenate([Xs[None], copies], axis=0)
    C = Xall.shape[0]
    if base is None:
        Z = Xall
    else:
        Z = np.concatenate([np.broadcast_to(base[None, :, None], (C, len(base), 1)), Xall], axis=2)
    Z = np.ascontiguousarray(Z)
    n = len(y)
    llm = np.full((C, n), np.nan)
    llb = np.full(n, np.nan)
    nonzero = np.r_[0, np.cumsum((Xs != 0).any(axis=1))]
    seasons, skipped, coefs = [], [], {}
    for Y in range(first, 2027):
        lo, hi = np.searchsorted(year, Y, "left"), np.searchsorted(year, Y, "right")
        if hi == lo:
            continue
        if lo < MIN_TRAIN or nonzero[lo] < MIN_TRAIN:
            skipped.append(Y)
            continue
        beta = newton(Z[:, :lo], y[:lo])
        p = 1.0 / (1.0 + np.exp(-np.einsum("cnk,ck->cn", Z[:, lo:hi], beta)))
        llm[:, lo:hi] = loss(p, y[lo:hi][None, :])
        if base is None:
            llb[lo:hi] = math.log(2)
        else:
            bb = newton(base[None, :lo, None], y[:lo])[0, 0]
            llb[lo:hi] = loss(1.0 / (1.0 + np.exp(-base[lo:hi] * bb)), y[lo:hi])
        coefs[Y] = beta[0].tolist()
        seasons.append(Y)
    return {"llm": llm, "llb": llb, "seasons": seasons, "skipped": skipped, "coefs": coefs}


def summarize(d: np.ndarray, mask: np.ndarray) -> dict:
    """The real improvement (row 0 of d, milli-log-loss) on the matches in mask, its 95% range, and the copies'."""
    n = int(mask.sum())
    if n == 0:
        return {"n": 0}
    real = d[0, mask]
    imp = 1000 * real.mean()
    se = 1000 * real.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
    out = {"n": n, "imp": float(imp), "lo": float(imp - 1.96 * se), "hi": float(imp + 1.96 * se)}
    if d.shape[0] > 1:
        cp = 1000 * d[1:, mask].mean(axis=1)
        sd = float(cp.std(ddof=1))
        out.update({"band_min": float(cp.min()), "band_max": float(cp.max()), "band_mean": float(cp.mean()),
                    "band_sd": sd, "z": float((imp - cp.mean()) / sd) if sd > 0 else float("nan"),
                    "above_band": bool(imp > cp.max()), "below_band": bool(imp < cp.min()),
                    "copies": [float(v) for v in cp]})
    return out


def score_feature(X: np.ndarray, y: np.ndarray, year: np.ndarray, ev: np.ndarray, base: np.ndarray | None,
                  first: int, sub: np.ndarray | None = None, keys: np.ndarray | None = None,
                  groups: dict | None = None, interaction: bool = False) -> dict:
    """One score of one feature. X, y, year, ev, base and keys cover the matches of one tour where the feature exists,
    in table order. The feature is standardised over all of them and its copies are shuffled among all of them, as
    Stage 4 does; the score then uses the matches in ``sub`` (for the market score: those with odds). Walked forward
    and summarised over the evaluation matches it scores, and over each group in ``groups`` (masks over the same
    matches). keys: the plan's keys of these matches, to add the 20 shuffled copies. interaction: the feature enters
    multiplied by the baseline's log-odds (the plan's match length)."""
    sd = X.std(axis=0)
    Xs = X / np.where(sd > 0, sd, 1.0)
    cp = shuffle_copies(Xs, year, keys) if keys is not None else None
    if interaction:
        Xs = Xs * base[:, None]
        cp = None if cp is None else cp * base[None, :, None]
    sub = np.ones(len(y), dtype=bool) if sub is None else sub
    w = walk_forward(Xs[sub], y[sub], year[sub], None if base is None else base[sub], first,
                     None if cp is None else cp[:, sub])
    d = w["llb"][None, :] - w["llm"]
    scored = np.isfinite(d[0]) & ev[sub]
    out = {"all": summarize(d, scored), "seasons": w["seasons"], "skipped": w["skipped"], "coefs": w["coefs"]}
    for g, m in (groups or {}).items():
        out[g] = summarize(d, scored & m[sub])
    return out
