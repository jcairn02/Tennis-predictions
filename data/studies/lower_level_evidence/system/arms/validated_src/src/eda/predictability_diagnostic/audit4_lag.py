"""Audit B of Stage 4, check 2: the ten strongest rows per tour (given Elo) rebuilt with one more match of lag, and
scored again. Which gains collapse?

The features are rebuilt for every match of Stage 4's table by the audit's own engine, not Stage 4's code:
    visibility      a player's row j is visible to match t when j's order is below the first order of t's date (an
                    earlier date), or j is in t's event with an order below the first order of t's date and round (an
                    earlier round); sums are differences of cumulative sums found by binary search on (player, order)
                    and (player, event, order). Stage 4 uses common.asof_sums (group sums); the two must agree
    one more lag    the player's history without their most recent visible match of that history: for a statistic,
                    the latest visible match carrying it; for load, rest and activity, the latest visible match played
                    (completed or retired); for a rating, its value before the latest visible match that moved it.
                    Windows keep this match's dates (the last 14 days, the last 52 weeks), so the lagged load is "the
                    load of the window less the latest match", where Stage 4's lag took "the load before the latest
                    match" (a window anchored on that match). For single facts (age, ranking), the value at the
                    latest visible match played, as Stage 4 did
    unlagged        the same engine without the lag reproduces Stage 4's features on every match (reported)

Scored given Elo and given the market (closing average) with the plan's walk-forward and its 20 shuffled copies
(audit4_common), the feature as built and the lagged feature on the same matches (those where both exist).
Fixed before the scores were seen: a gain "collapses" when the lagged improvement given Elo no longer clears its own
null band; it is "largely lost" when it keeps less than half of the gain as built.

Also rebuilt, as Stage 4 rebuilt them: the rows above the family-wide line given the market that this engine covers
(men's sets and minutes over 7 days; women's days since the last match, matches played, ranking, ranking points,
level of the last 52 weeks). The women's gap between ranking and Elo is not rebuilt.

Writes, in data/studies/predictability_diagnostic/audit4/:
    lag_features.parquet   the audit's features as built and one match later (rebuilt by this script)
    lag.csv                one row per tour x row: the scores as built and one match later, bands, correlation
    lag.json               the summary, with the engine's agreement with Stage 4's features

Run: ./python.sh src/eda/predictability_diagnostic/audit4_lag.py   (about 10 minutes)
"""
from __future__ import annotations

import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import audit4_common as A  # noqa: E402
from src.eda.predictability_diagnostic import audit4_recompute as RC  # noqa: E402
from src.eda.predictability_diagnostic import stage2_iid as M  # noqa: E402  (the iid model, checked equal to the audit's)

BIG = 1 << 20
DECAY = 7.0 * A.HALF_LIFE
REF = int(np.datetime64("2018-01-01", "D").astype("int64"))
STATS = ("spw", "rpw", "tpw", "hold", "brk", "first_in", "first_won", "second_won", "rpw_first", "rpw_second")
MARKET_EXTRA = {"atp": [("sets_7d", "single"), ("minutes_7d", "single")],
                "wta": [("days_since", "single"), ("played_career", "single"), ("rank", "single"),
                        ("rank_points", "single"), ("recent_level", "single")]}
WORKERS = max(1, min(12, (os.cpu_count() or 2) - 2))
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# The engine

class Hist:
    """Visible-history sums and the latest visible row, over the player rows in ``mask``, grouped by ``group``."""

    def __init__(self, group: np.ndarray, order: np.ndarray, ev: np.ndarray, mask: np.ndarray | None = None):
        rows = np.arange(len(group)) if mask is None else np.flatnonzero(mask)
        self.gcodes, g = np.unique(group, return_inverse=True)
        g = g.astype("int64")
        self.ginv = g
        self.nev = int(ev.max()) + 1
        gr, o, e = g[rows], order[rows], ev[rows]
        ka = gr * BIG + o
        oa = np.argsort(ka, kind="stable")
        self.ka, self.ra = ka[oa], rows[oa]
        kb = (gr * self.nev + e) * BIG + o
        ob = np.argsort(kb, kind="stable")
        self.kb, self.rb = kb[ob], rows[ob]

    def _keys(self, tg_rows, tg_ev, t_day, t_round):
        g = self.ginv[tg_rows]
        return g, g * BIG + t_day, (g * self.nev + tg_ev) * BIG + t_round, (g * self.nev + tg_ev) * BIG

    def sums(self, V: np.ndarray, tg_rows, tg_ev, t_day, t_round, win_start=None) -> np.ndarray:
        """Sums of V (one row per player row) over each target's visible rows (within the window from order
        ``win_start`` when given)."""
        V = V.reshape(len(V), -1)
        g, qa, qb, qb0 = self._keys(tg_rows, tg_ev, t_day, t_round)
        csa = np.vstack([np.zeros((1, V.shape[1])), np.cumsum(V[self.ra], axis=0)])
        csb = np.vstack([np.zeros((1, V.shape[1])), np.cumsum(V[self.rb], axis=0)])
        hi = np.searchsorted(self.ka, qa, "left")
        lo = np.searchsorted(self.ka, g * BIG + (0 if win_start is None else win_start), "left")
        same = csb[np.searchsorted(self.kb, qb, "left")] - csb[np.searchsorted(self.kb, qb0, "left")]
        return csa[hi] - csa[lo] + same

    def latest(self, tg_rows, tg_ev, t_day, t_round) -> np.ndarray:
        """The latest visible row (largest order) for each target, or -1: an earlier round of the same event if
        there is one, else the last row of an earlier date."""
        g, qa, qb, qb0 = self._keys(tg_rows, tg_ev, t_day, t_round)
        pa = np.searchsorted(self.ka, qa, "left") - 1
        ok_a = (pa >= 0) & (self.ka[np.maximum(pa, 0)] // BIG == g)
        pb = np.searchsorted(self.kb, qb, "left") - 1
        ok_b = (pb >= 0) & (self.kb[np.maximum(pb, 0)] // BIG == qb0 // BIG)
        return np.where(ok_b, self.rb[np.maximum(pb, 0)], np.where(ok_a, self.ra[np.maximum(pa, 0)], -1))


def hold_vec(p):
    q = 1 - p
    return p ** 4 * (1 + 4 * q + 10 * q * q) + 20 * p ** 3 * q ** 3 * (p * p / (p * p + q * q))


def serve_for_hold_vec(h):
    h = np.clip(h, 1e-9, 1 - 1e-9)
    lo, hi = np.full(h.shape, 1e-6), np.full(h.shape, 1 - 1e-6)
    for _ in range(80):
        mid = (lo + hi) / 2
        below = hold_vec(mid) < h
        lo, hi = np.where(below, mid, lo), np.where(below, hi, mid)
    return (lo + hi) / 2


RULE_CODE = {(6, 7): "TB7@6", (6, 10): "TB10@6", (12, 7): "TB7@12", (None, 0): "ADV"}


def iid_vec(pa, pb, bo5, rule, mtb):
    out = M.match_win_by(pa, pb, np.where(bo5, 5, 3), rule)
    if mtb.any():
        s, f = M.set_win(pa[mtb], pb[mtb]), M.tiebreak(pa[mtb], pb[mtb], 10)
        out[mtb] = np.where(bo5[mtb], s ** 3 + 3 * s ** 3 * (1 - s) + 6 * s ** 2 * (1 - s) ** 2 * f,
                            s ** 2 + 2 * s * (1 - s) * f)
    return out


# ------------------------------------------------------------------------------------------------

def build(m: pd.DataFrame, p: pd.DataFrame, ctx: dict) -> tuple[pd.DataFrame, dict]:
    n_rows = len(p)
    j = np.arange(n_rows) // 2
    order = j.astype("int64")
    ev = m["ev"].to_numpy()[j]
    day = m["day"].to_numpy()[j]
    pcode = A.player_codes(p)
    status = m["status"].to_numpy()[j]
    played = np.isin(status, ["completed", "retired"])
    box = (status == "completed") & (m["format"].to_numpy()[j] == "standard")
    t_day_m, t_round_m = A.order_thresholds(m)
    pool = (m["level"].isin(A.EVAL_LEVELS) & m["status"].isin(["completed", "retired"])
            & m["year"].between(2010, 2026)).to_numpy()
    P = np.flatnonzero(pool)
    TA, TB = 2 * P, 2 * P + 1
    T = np.concatenate([TA, TB])                       # target rows: A's of every pool match, then B's
    tj = T // 2
    t_day, t_round, t_ev, t_dd = t_day_m[tj], t_round_m[tj], m["ev"].to_numpy()[tj], m["day"].to_numpy()[tj]
    win = lambda w: A.first_order_from_day(m, t_dd - w)          # noqa: E731
    nA = len(P)
    out: dict = {}

    def diff(v, e=None):
        e = np.isfinite(v) if e is None else (e & np.isfinite(v))
        return np.where(e[:nA] & e[nA:], v[:nA] - v[nA:], np.nan)

    H = Hist(pcode, order, ev)
    Hp = Hist(pcode, order, ev, played)
    last_played = Hp.latest(T, t_ev, t_day, t_round)
    lp = np.maximum(last_played, 0)
    has_lp = last_played >= 0
    lp_day = day[lp]

    # load windows and activity -------------------------------------------------------------
    minutes = m["minutes"].to_numpy("float64")[j]
    sets = p["sets_won_d"].to_numpy("float64")
    mainrow = np.isin(m["level"].to_numpy()[j], A.MAIN_TOUR) & ~m["qualifying"].to_numpy(bool)[j]
    V = np.column_stack([played, played & np.isnan(minutes), np.where(played & ~np.isnan(minutes), minutes, 0.0),
                         played & np.isnan(sets), np.where(played & ~np.isnan(sets), sets, 0.0), played & mainrow]).astype("float64")
    for w in (7, 14):
        S = H.sums(V, T, t_ev, t_day, t_round, win(w))
        inwin = has_lp & (lp_day >= t_dd - w)
        L = S - np.where(inwin[:, None], V[lp], 0.0)
        for name, miss, val in (("minutes", 1, 2), ("sets", 3, 4)):
            for tag, X in (("built", S), ("lag", L)):
                v = np.where(X[:, miss] < 0.5, np.log1p(np.maximum(X[:, val], 0)), np.nan)
                out[(f"{name}_{w}d|single", tag)] = diff(v)
    car = H.sums(V[:, :1], T, t_ev, t_day, t_round)[:, 0]
    out[("played_career|single", "built")] = diff(np.log1p(car))
    out[("played_career|single", "lag")] = diff(np.log1p(np.maximum(car - has_lp, 0)))
    S52 = H.sums(V, T, t_ev, t_day, t_round, win(A.WEEK52))
    in52 = has_lp & (lp_day >= t_dd - A.WEEK52)
    L52 = S52 - np.where(in52[:, None], V[lp], 0.0)
    for tag, X in (("built", S52), ("lag", L52)):
        share = (X[:, 5] + 0.5) / (X[:, 0] + 1.0)
        out[("recent_level|single", tag)] = diff(np.where(X[:, 0] > 0.5, A.logit(share), np.nan))
    # days since the last match played, and one match later: between that match and the one before it
    gap = np.where(has_lp, (t_dd - lp_day).astype("float64"), np.nan)
    out[("days_since|single", "built")] = diff(np.log1p(gap))
    lpj = lp // 2
    prev2 = Hp.latest(lp, m["ev"].to_numpy()[lpj], t_day_m[lpj], t_round_m[lpj])
    gap2 = np.where(has_lp & (prev2 >= 0), (lp_day - day[np.maximum(prev2, 0)]).astype("float64"), np.nan)
    out[("days_since|single", "lag")] = diff(np.log1p(gap2))
    # one of the first matches on this surface this season
    yr = m["year"].to_numpy()[j]
    surf = m["surf"].to_numpy()[j]
    gss = (pcode * 20 + (yr - 2009)) * 8 + surf
    Hs = Hist(gss, order, ev)
    cnt = Hs.sums(played.astype("float64"), T, t_ev, t_day, t_round)[:, 0]
    sk = surf[T] > 0
    out[("surface_first|single", "built")] = diff(np.where(sk, (cnt < 3).astype("float64"), np.nan))
    out[("surface_first|single", "lag")] = diff(np.where(sk, (np.maximum(cnt - 1, 0) < 3).astype("float64"), np.nan))
    # age and rankings: the value here, and at the latest match played
    age = p["age"].to_numpy("float64")

    def age_feats(a):
        a1 = np.where((a >= 14) & (a <= 50), a - 25.0, np.nan)
        return diff(a1), diff(a1 ** 2)
    out[("age|single", "built")], out[("age|single|2", "built")] = age_feats(age[T])
    out[("age|single", "lag")], out[("age|single|2", "lag")] = age_feats(np.where(has_lp, age[lp], np.nan))
    rk = filled_rank(m, p)
    pts = np.clip(np.nan_to_num(p["rank_points"].to_numpy("float64"), nan=0.0), 0, None)
    for tag, rr, pp_ in (("built", rk[T], pts[T]), ("lag", np.where(has_lp, rk[lp], np.nan), np.where(has_lp, pts[lp], np.nan))):
        out[("rank|single", tag)] = np.log(rr[nA:]) - np.log(rr[:nA])
        out[("rank_points|single", tag)] = np.log1p(pp_[:nA]) - np.log1p(pp_[nA:])
    log("load, activity, age, rankings done")

    # statistics: 52 weeks and decayed, as built and without the latest match carrying the statistic -----------
    fac = np.exp2((day - REF) / DECAY)
    t_fac = np.exp2(-(t_dd - REF) / DECAY)
    vals = {}
    for st in STATS:
        x, d, ok = stat_xd(m, p, st)
        mu_row = mu_rows(ctx, st, m["tour"].to_numpy()[j], m["surface"].to_numpy()[j])
        xc = np.where(ok, x - d * mu_row, 0.0)
        dd = np.where(ok, d, 0.0)
        Vs = np.column_stack([xc, dd])
        s52 = H.sums(Vs, T, t_ev, t_day, t_round, win(A.WEEK52))
        sdec = H.sums(Vs * fac[:, None], T, t_ev, t_day, t_round) * t_fac[:, None]
        scar = H.sums(dd, T, t_ev, t_day, t_round)[:, 0]
        last = Hist(pcode, order, ev, ok & (d > 0)).latest(T, t_ev, t_day, t_round)
        has = last >= 0
        ls = np.maximum(last, 0)
        in52 = has & (day[ls] >= t_dd - A.WEEK52)
        l52 = s52 - np.where(in52[:, None], Vs[ls], 0.0)
        ldec = sdec - np.where(has[:, None], Vs[ls] * np.exp2(-(t_dd - day[ls]) / DECAY)[:, None], 0.0)
        lcar = scar - np.where(has, dd[ls], 0.0)
        mu_t = mu_rows(ctx, st, m["tour"].to_numpy()[tj], m["surface"].to_numpy()[tj])
        K = np.where(m["tour"].to_numpy()[tj] == "atp", ctx["K"][(st, "atp")], ctx["K"][(st, "wta")])
        for tag, w52, dec, cr in (("built", s52, sdec, scar), ("lag", l52, ldec, lcar)):
            vals[(st, "52 weeks", tag)] = np.where(w52[:, 1] > 0.5, A.shrunk(mu_t, w52[:, 0], w52[:, 1], K), np.nan)
            vals[(st, "decayed", tag)] = np.where(cr > 0, A.shrunk(mu_t, dec[:, 0], dec[:, 1], K), np.nan)
        log(f"  {st}")
    # the formats of each pool match (the plan's reading)
    bo5, rule, mtb = formats(m, p, P)
    tour_t = m["tour"].to_numpy()[P]
    surf_t = m["surface"].to_numpy()[P]
    mu = {st: mu_rows(ctx, st, tour_t, surf_t) for st in ("spw", "hold", "first_won", "second_won")}
    for form in ("52 weeks", "decayed"):
        for tag in ("built", "lag"):
            v = {st: vals[(st, form, tag)] for st in STATS}
            a_, b_ = (lambda st: v[st][:nA]), (lambda st: v[st][nA:])
            out[(f"tpw|{form}", tag)] = A.safe_logit(a_("tpw")) - A.safe_logit(b_("tpw"))
            for cid, need in (("mu_points", ("spw", "rpw")), ("mu_games", ("hold", "brk")),
                              ("mu_components", ("first_in", "first_won", "second_won", "rpw_first", "rpw_second"))):
                ex = np.all([np.isfinite(a_(s)) & np.isfinite(b_(s)) for s in need], axis=0)
                with np.errstate(invalid="ignore"):
                    if cid == "mu_points":
                        pa = A.combine(a_("spw"), b_("rpw"), mu["spw"])
                        pb = A.combine(b_("spw"), a_("rpw"), mu["spw"])
                    elif cid == "mu_games":
                        pa = serve_for_hold_vec(A.combine(a_("hold"), b_("brk"), mu["hold"]))
                        pb = serve_for_hold_vec(A.combine(b_("hold"), a_("brk"), mu["hold"]))
                    else:
                        fa, fb = np.clip(a_("first_in"), 0, 1), np.clip(b_("first_in"), 0, 1)
                        pa = fa * A.combine(a_("first_won"), b_("rpw_first"), mu["first_won"]) + (1 - fa) * A.combine(
                            a_("second_won"), b_("rpw_second"), mu["second_won"])
                        pb = fb * A.combine(b_("first_won"), a_("rpw_first"), mu["first_won"]) + (1 - fb) * A.combine(
                            b_("second_won"), a_("rpw_second"), mu["second_won"])
                res = np.full(nA, np.nan)
                ok = ex & np.isfinite(pa) & np.isfinite(pb)
                res[ok] = A.safe_logit(iid_vec(pa[ok], pb[ok], bo5[ok], rule[ok], mtb[ok]))
                out[(f"{cid}|{form}", tag)] = res
    log("statistics and matchups done")

    # ratings: the audit's own passes over every match; one match later, the value before the latest match that
    # moved the rating ------------------------------------------------------------------------------------------
    ov = np.full(n_rows, np.nan)
    sv = np.full(n_rows, np.nan)
    so = np.full(n_rows, np.nan)
    ro = np.full(n_rows, np.nan)
    mu_l = np.full(len(m), np.nan)
    upd3 = np.zeros(len(m), dtype=bool)
    for tour in ("atp", "wta"):
        arr, _ = RC.tour_arrays(m, p, tour, ctx)
        RC.init_worker({tour: arr})
        D = RC._W[tour]
        idx = list(range(len(D["week"])))
        e, s = RC.run_passes(D, idx, ctx, tour)
        sel = arr["sel"]
        E = np.array([[v if v is not None else np.nan for v in e[k]] for k in idx], dtype="float64")
        S3 = np.array([s[k] for k in idx])
        ov[2 * sel], ov[2 * sel + 1], sv[2 * sel], sv[2 * sel + 1] = E[:, 0], E[:, 1], E[:, 2], E[:, 3]
        so[2 * sel], so[2 * sel + 1], ro[2 * sel], ro[2 * sel + 1] = S3[:, 0], S3[:, 1], S3[:, 2], S3[:, 3]
        mu_l[sel] = arr["mu"]
        upd3[sel] = arr["upd3"]
        log(f"  rating passes {tour}")
    w_t = np.where(m["tour"].to_numpy()[tj] == "atp", ctx["elo"]["atp"]["w"], ctx["elo"]["wta"]["w"])
    last_s = Hist(pcode * 8 + surf, order, ev, played).latest(T, t_ev, t_day, t_round)
    upd3_rows = upd3[j]
    last_r = Hist(pcode, order, ev, upd3_rows).latest(T, t_ev, t_day, t_round)
    for tag in ("built", "lag"):
        if tag == "built":
            o_, s_ = ov[T], sv[T]
            so_, ro_ = so[T], ro[T]
        else:
            o_ = np.where(has_lp, ov[lp], ov[T])
            s_ = np.where(last_s >= 0, sv[np.maximum(last_s, 0)], sv[T])
            so_ = np.where(last_r >= 0, so[np.maximum(last_r, 0)], so[T])
            ro_ = np.where(last_r >= 0, ro[np.maximum(last_r, 0)], ro[T])
        s_ = np.where(np.isnan(s_), o_, s_)
        r_ = (1 - w_t) * o_ + w_t * s_
        out[("elo_games|single", tag)] = A.safe_logit(1.0 / (1.0 + 10.0 ** ((r_[nA:] - r_[:nA]) / 400.0)))
        out[("rating_serve|single", tag)] = so_[:nA] - so_[nA:]
        mu_p = mu_l[P]
        pa = A.expit(mu_p + so_[:nA] - ro_[nA:])
        pb = A.expit(mu_p + so_[nA:] - ro_[:nA])
        out[("rating_matchup|single", tag)] = A.safe_logit(iid_vec(pa, pb, bo5, rule, mtb))
    log("ratings done")
    frame = pd.DataFrame({"match_id": m["match_id"].to_numpy()[P]})
    for (col, tag), v in out.items():
        frame[f"{col}#{tag}"] = np.asarray(v, dtype="float32")          # Stage 4 stores its features as float32 too
    meta = {"pool_matches": int(len(P))}
    return frame, meta


def stat_xd(m: pd.DataFrame, p: pd.DataFrame, st: str):
    j = np.arange(len(p)) // 2
    box = (m["status"].to_numpy()[j] == "completed") & (m["format"].to_numpy()[j] == "standard")
    if st in ("rpw_first", "rpw_second"):
        src = "first_won" if st == "rpw_first" else "second_won"
        n = p[f"{src}_n"].to_numpy("float64").reshape(-1, 2)[:, ::-1].reshape(-1)
        d = p[f"{src}_d"].to_numpy("float64").reshape(-1, 2)[:, ::-1].reshape(-1)
        ok = box & ~np.isnan(n) & ~np.isnan(d)
        return np.where(ok, d - n, 0.0), np.where(ok, d, 0.0), ok
    n, d = p[f"{st}_n"].to_numpy("float64"), p[f"{st}_d"].to_numpy("float64")
    ok = box & ~np.isnan(n) & ~np.isnan(d)
    return np.where(ok, n, 0.0), np.where(ok, d, 0.0), ok


def mu_rows(ctx: dict, st: str, tour: np.ndarray, surface: np.ndarray) -> np.ndarray:
    key = np.where(np.isin(surface, A.SURFACES), surface, "all")
    out = np.empty(len(tour))
    for t in ("atp", "wta"):
        for s in list(A.SURFACES) + ["all"]:
            mm = (tour == t) & (key == s)
            out[mm] = ctx["means"][(st, t, s)]
    return out


def formats(m: pd.DataFrame, p: pd.DataFrame, P: np.ndarray):
    """The plan's reading of each pool match's format: best of five (from the score, the record or short sets), the
    deciding-set rule, a match tiebreak (Stage 0's format)."""
    sets = p["sets_won_n"].to_numpy("float64").reshape(-1, 2)[P]
    with np.errstate(invalid="ignore"):
        w = np.where(np.isnan(sets).all(axis=1), np.nan, np.fmax(sets[:, 0], sets[:, 1]))
        bo5 = (w >= 3) | (m["best_of"].to_numpy("float64")[P] == 5) | (m["format"].to_numpy()[P] == "short_sets")
    combos = m.iloc[P][["level", "tournament_name", "year", "qualifying"]].astype(str).agg("|".join, axis=1).to_numpy()
    uniq, inv = np.unique(combos, return_inverse=True)
    codes = []
    for u in uniq:
        lv, nm, yr, q = u.split("|")
        codes.append(RULE_CODE[A.final_rule(lv, nm, int(yr), q == "True")])
    rule = np.array(codes, dtype=object)[inv]
    mtb = m["format"].to_numpy()[P] == "match_tiebreak"
    return bo5, rule, mtb


def filled_rank(m: pd.DataFrame, p: pd.DataFrame) -> np.ndarray:
    """Each player row's rank; an unranked player takes one below the lowest rank seen on the tour in earlier
    seasons (the season's own in 2010), as Stage 1 sets it."""
    rk = p["rank"].to_numpy("float64")
    worst = pd.DataFrame({"tour": m["tour"], "year": m["year"], "w": np.fmax(rk[0::2], rk[1::2])}).groupby(["tour", "year"])["w"].max()
    fill = {}
    for t in ("atp", "wta"):
        s = worst.loc[t].sort_index()
        prior = s.cummax().shift(1)
        prior.iloc[0] = s.iloc[0]
        for y, v in prior.items():
            fill[(t, int(y))] = float(v) + 1
    j = np.arange(len(p)) // 2
    f = np.array([fill[(t, int(y))] for t, y in zip(m["tour"].to_numpy()[j], m["year"].to_numpy()[j])])
    return np.where(np.isnan(rk), f, rk)


# ------------------------------------------------------------------------------------------------
# Scoring, in worker processes

_S: dict = {}


def init_scorer() -> None:
    f = pd.read_parquet(A.OUT / "stage4_features.parquet")
    lag = pd.read_parquet(A.AUDIT / "lag_features.parquet").set_index("match_id").reindex(f["match_id"]).reset_index()
    _S["f"], _S["lag"] = f, lag
    _S["keys"] = A.plan_keys(len(f))


def score_task(task: dict) -> dict:
    f, lag, keys = _S["f"], _S["lag"], _S["keys"]
    t = f["tour"].to_numpy() == task["tour"]
    cols = task["cols"]
    Xo = np.column_stack([f[c].to_numpy("float64") for c in cols])
    Xl = np.column_stack([lag[f"{c}#lag"].to_numpy("float64") for c in cols])
    Xb = np.column_stack([lag[f"{c}#built"].to_numpy("float64") for c in cols])
    both = t & np.isfinite(Xo).all(axis=1) & np.isfinite(Xl).all(axis=1)
    idx = np.flatnonzero(both)
    y, yr, ev = f["a_won"].to_numpy()[idx], f["year"].to_numpy()[idx], f["evaluation"].to_numpy()[idx]
    le = A.logit(np.clip(f["p_elo"].to_numpy("float64")[idx], 1e-9, 1 - 1e-9))
    pm = f["p_mkt"].to_numpy("float64")[idx]
    has = np.isfinite(pm)
    lm = A.logit(np.clip(np.nan_to_num(pm, nan=0.5), 1e-9, 1 - 1e-9))
    rec = {k: task[k] for k in ("tour", "id", "form", "why")}
    rec["matches_both"] = int(ev.sum())
    rec["feature_corr"] = float(np.corrcoef(Xo[idx, 0], Xl[idx, 0])[0, 1])
    rec["values_differ"] = int((np.abs(Xo[idx] - Xl[idx]) > 1e-6).any(axis=1).sum())
    for kind, X in (("built", Xo), ("lag", Xl)):
        for score, base, sub in (("elo", le, None), ("market", lm, has)):
            r = A.score_feature(X[idx], y, yr, ev, base, task["first"], sub=sub, keys=keys[idx])["all"]
            for k in ("n", "imp", "lo", "hi", "band_min", "band_max", "band_sd", "z", "above_band"):
                rec[f"{kind}_{score}_{k}"] = r.get(k)
    return rec


# ------------------------------------------------------------------------------------------------

def iid_check() -> dict:
    """The vectorised iid model used here (Stage 2's) against the audit's exact recursion (audit4_common.p_match), and
    the hold inversion, on 300 random pairs of serve rates for every deciding-set rule, best of three and five, and
    the match tiebreak."""
    rng = np.random.default_rng(A.SEED)
    pa, pb = rng.uniform(0.35, 0.85, 300), rng.uniform(0.35, 0.85, 300)
    worst = 0.0
    for rule_t, code in RULE_CODE.items():
        for bo5 in (False, True):
            for mtb in (False, True):
                v = iid_vec(pa, pb, np.full(300, bo5), np.full(300, code, dtype=object), np.full(300, mtb))
                e = np.array([A.p_match(a, b, 5 if bo5 else 3, rule_t, mtb) for a, b in zip(pa, pb)])
                worst = max(worst, float(np.abs(v - e).max()))
    h = rng.uniform(0.3, 0.97, 300)
    inv = float(np.abs(serve_for_hold_vec(h) - np.array([A.serve_for_hold(x) for x in h])).max())
    return {"pairs": 300, "formats": 16, "match_probability_max_abs_diff": worst, "hold_inversion_max_abs_diff": inv}


def main() -> int:
    iid = iid_check()
    log(f"iid model against the audit's recursion: {iid}")
    m, p = A.load_tables()
    ctx = A.constants()
    log("tables loaded")
    frame, meta = build(m, p, ctx)
    A.AUDIT.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(A.AUDIT / "lag_features.parquet", index=False, compression="zstd")
    log(f"wrote lag_features.parquet ({frame.shape[1] - 1} columns)")

    # the engine as built against Stage 4's features, every pool match
    f = pd.read_parquet(A.OUT / "stage4_features.parquet")
    g = frame.set_index("match_id").reindex(f["match_id"])
    agree = []
    for c in sorted({c.split("#")[0] for c in frame.columns if c.endswith("#built")}):
        a = g[f"{c}#built"].to_numpy("float64")
        b = f[c].to_numpy("float64")
        ex_a, ex_b = np.isfinite(a), np.isfinite(b)
        both = ex_a & ex_b
        dif = np.abs(a[both] - b[both])
        agree.append({"feature": c, "pool_matches": int(len(b)), "exists_stage4": int(ex_b.sum()),
                      "exists_audit": int(ex_a.sum()), "existence_differs": int((ex_a != ex_b).sum()),
                      "max_abs_diff": float(dif.max()) if len(dif) else None,
                      "beyond_tolerance": int((dif > 2e-5 + 2e-5 * np.abs(b[both])).sum())})
        log(f"  agreement {c}: {agree[-1]}")

    rank = pd.read_csv(A.OUT / "stage4_ranking.csv")
    cand = pd.read_csv(A.OUT / "stage4_candidates.csv")
    tasks = []
    for t in ("atp", "wta"):
        top = rank[rank["tour"].eq(t)].nsmallest(10, "rank_given_elo")
        rows = [(r.id, r.form, "ten strongest given Elo") for r in top.itertuples()]
        rows += [(cid, form, "above the family-wide line given the market") for cid, form in MARKET_EXTRA[t]
                 if (cid, form) not in {(a, b) for a, b, _ in rows}]
        for cid, form, why in rows:
            col = f"{cid}|{form}"
            cols = [col] + ([f"{col}|2"] if f"{col}|2" in f.columns else [])
            c = cand[cand["id"].eq(cid)].iloc[0]
            first = 2019 if (t == "wta" and c["wta_box_from_2019"] == "yes") else 2013
            tasks.append({"tour": t, "id": cid, "form": form, "why": why, "cols": cols, "first": first})
    log(f"scoring {len(tasks)} rows with {WORKERS} workers")
    res = []
    with ProcessPoolExecutor(max_workers=WORKERS, initializer=init_scorer) as ex:
        for r in ex.map(score_task, tasks, chunksize=1):
            res.append(r)
            log(f"  {r['tour']} {r['id']} {r['form']}: given Elo {r['built_elo_imp']:.3f} -> {r['lag_elo_imp']:.3f} "
                f"(band max {r['lag_elo_band_max']:.3f}); market {r['built_market_imp']:.3f} -> {r['lag_market_imp']:.3f}")
    R = pd.DataFrame(res)
    R["kept_share_elo"] = R["lag_elo_imp"] / R["built_elo_imp"]
    R["collapses"] = ~R["lag_elo_above_band"].astype(bool)
    R["largely_lost"] = R["kept_share_elo"] < 0.5
    # Stage 4's own lag check beside the audit's
    s4 = pd.read_csv(A.OUT / "stage4_leak_checks.csv")
    s4 = s4[s4["check"].eq("one match later")][["tour", "id", "form", "original_elo", "rebuilt_elo", "original_market",
                                                "rebuilt_market", "feature_corr"]]
    R = R.merge(s4.rename(columns={c: f"stage4_{c}" for c in ("original_elo", "rebuilt_elo", "original_market",
                                                               "rebuilt_market", "feature_corr")}),
                on=["tour", "id", "form"], how="left")
    R.to_csv(A.AUDIT / "lag.csv", index=False)
    lines = A.json.loads((A.OUT / "stage4_results.json").read_text(encoding="utf-8"))["lines"]
    summ = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "meta": meta, "iid_check": iid,
            "engine_vs_stage4": agree, "rows": res,
            "family_lines_given_elo": {t: lines[f"{t}|elo"]["line"] for t in ("atp", "wta")},
            "collapse_rule": "the lagged improvement given Elo does not clear its own null band",
            "largely_lost_rule": "the lagged improvement given Elo is under half of the improvement as built",
            "seconds": round(time.time() - T0, 1)}
    A.save_json(summ, "lag.json")
    log("wrote lag.csv and lag.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
