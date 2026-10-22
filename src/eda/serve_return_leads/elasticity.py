"""PS10, return elasticity to server strength (serve/return-leads study; the elasticity builder, 16 Oct 2026).

Does a returner gain more, or less, against big servers than the additive IOS rating predicts? The model's return
ratings are additive (IOS: y = logit((x + 1/2)/(d + 1)) - mu ~ O_server - D_returner); this builds the non-additive
part the long list calls PS10, per returner, from the points of his earlier matches, and the matchup term it implies.

    long_table()     each player's own matches at every level before 29 Jul 2026, one row per (match, player), in the
                     player's own order (screen.long_table's order), WITHOUT the won column; the Stage 0, timing and
                     rating reads filter tournament_date < 29 Jul 2026 inside the parquet read and then assert it. Adds
                     the surface IOS's pre-match spw ratings of 6 Oct (surface_features.parquet: srf_O_eff_spw,
                     srf_D_eff_spw; the rating pool is the main tour, Challengers and their qualifying), the
                     opponent's (server's) O and the tour's surface average mu (the solver's centring, logit scale)
    residuals        per return row k of returner j against server i, with a box score under the IOS's own rule
                     (completed, standard format, serve points > 0) and both ratings:
                         y_k = logit((x_k + 1/2)/(d_k + 1)) - mu_k     (x = the server's serve points won, d = served)
                         r_k = (O_i,k - D_j,k) - y_k                   (+ = the returner won more return points than
                                                                        the additive prediction)
                     u_k = d_k (return points played) is the unit weight (the IOS's tau = 1)
    centre           the server's O on a time-centred scale: O~ = O - M(t), M(t) = the tour's mean pre-match O_eff_spw
                     over its main-draw tour-level matches with earliest start in [t - 364, t) (leak-proof: pre-match
                     ratings of earlier matches). The ITF box scores of 2025-26 shift the rating scale (the men's frame
                     mean of O rose from 0.33 in 2024 to 0.44 in 2026); centring keeps the slope and the term on a
                     stable scale
    slope            at target match m, returner j's history = his residual rows k with lf_k + 1 <= es_m (timing.parquet;
                     the match itself and anything that could still be running are out); weighted least squares of
                     r_k on O~_srv,k with an intercept, weights u_k 2^(-(es_m - obs_k)/H), H = 365 days: b_hat, the
                     centre Obar_j (the weighted mean of O~ over the history) and v_unit (the slope's sampling variance
                     per unit of s^2, the residual variance per return point)
    empirical Bayes  at each 1 January snapshot S (2011-2026), per tour: every player's history released by S split into
                     alternate matches (odd and even in his own order), each half's slope with the decay to S; over
                     players with >= 10 matches in each half: s^2 = mean (b_odd - b_even)^2 / (v_odd + v_even) (the
                     chance spread), the population slope b_bar, and tau^2 = the precision-weighted covariance of the
                     halves (the true spread between returners). A target m reads the latest snapshot <= es_m:
                         b* = b_prior + lambda (b_hat - b_prior),  lambda = tau^2 / (tau^2 + s^2 v_unit)
    matchup term     per row: term_j = b*_j (O~_opp,m - Obar_j), the returner's predicted extra return logit beyond the
                     additive rating against today's server; at match m, A - B: x = term_A - term_B
                     (= b_A (O_B - Obar_A) - b_B (O_A - Obar_B), each returner's centre his own opponents' mean)

Every value comes from strictly earlier rows of the same player (and population constants from rows released by the
snapshot), so `screen.timing_probe` applies unchanged.

Run (each step writes into data/studies/serve_return_leads/elasticity/):
    ./python.sh src/eda/serve_return_leads/elasticity.py --check      outcome-free mapping and coverage checks
    ./python.sh src/eda/serve_return_leads/elasticity.py --build      values, reliability, empirical Bayes (outcome-free)
    ./python.sh src/eda/serve_return_leads/elasticity.py --probe      the timing probe
    ./python.sh src/eda/serve_return_leads/elasticity.py --points     the points check (box scores before 29 Jul 2026)
    ./python.sh src/eda/serve_return_leads/elasticity.py --read       the readings (readings.read; results via seen_frame)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_return_leads import common as C  # noqa: E402
from src.eda.unpriced_leads import screen as H  # noqa: E402

OUT = C.OUT / "elasticity"
SEALED_FROM = C.SEALED_FROM                      # 29 Jul 2026: nothing from this tournament date on is loaded here
STAGE0_M, STAGE0_P, TIMING = H.STAGE0_M, H.STAGE0_P, H.TIMING
RATINGS = ROOT / "data" / "studies" / "surface_ios" / "surface_features.parquet"
CONSTANTS = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage4_constants.csv"
POOL = ROOT / "data" / "studies" / "surface_ios" / "cache" / "pool.parquet"
CACHE = ROOT / "data" / "studies" / "surface_ios" / "cache"

H_DAYS = 365.0                                   # the decay half-life, fixed before any reading
WINDOW_M = 364                                   # days of the time-centring mean M(t)
MIN_M = 200                                      # values M(t) needs (else the mean of everything earlier)
NMIN_HALF = 10                                   # matches per half for a player to enter the snapshot's estimates
MAIN_LEVELS = ("GS", "FIN", "T1000", "T500", "T250")
SURF_NAME = {"Hard": "Hard", "Clay": "Clay", "Grass": "Grass", "Carpet": "Carpet"}
REF_DAY = int((pd.Timestamp("2010-01-01") - pd.Timestamp("1970-01-01")).days)
KEY = 1_000_000                                  # player code * KEY + day: a sortable (player, day) key
PRIOR = "population"                             # the empirical-Bayes prior mean: "population" (b_bar) or "zero"
MATCH_COLS = ["match_id", "tour", "level", "qualifying", "round_order", "match_num", "surface", "tournament_id",
              "tournament_date", "status", "format", "has_box"]
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def day_of(ts) -> int:
    return int((pd.Timestamp(ts) - pd.Timestamp("1970-01-01")).days)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------- the long table

def mu_table() -> dict:
    """The tour's surface average of serve points won (Stage 3's, 2010-2018; the IOS solver's centring), logit scale.
    Keys (tour, surface name or 'all')."""
    k = pd.read_csv(CONSTANTS)
    k = k[(k["kind"] == "surface average") & (k["stat"] == "spw")]
    return {(r.tour, r.surface): float(logit(r.value)) for r in k.itertuples(index=False)}


def long_table() -> pd.DataFrame:
    """Each player's own matches at every level before 29 Jul 2026 (screen.long_table's order; no won column), with
    the return-side box score (the player's return points won and played; the opponent's serve points), the IOS's
    box-score rule, both players' pre-match surface-IOS spw ratings where the match is in the rating pool, and mu."""
    m = pd.read_parquet(STAGE0_M, columns=MATCH_COLS, filters=[("tournament_date", "<", SEALED_FROM)])
    if len(m) == 0 or m["tournament_date"].max() >= SEALED_FROM:
        raise RuntimeError("a match from 29 Jul 2026 on was loaded")
    m["match_id"] = m["match_id"].astype(str)
    ids = m["match_id"].tolist()
    t = pd.read_parquet(TIMING, columns=["match_id", "tournament_date", "es", "lf", "obs"],
                        filters=[("tournament_date", "<", SEALED_FROM)])
    if t["tournament_date"].max() >= SEALED_FROM:
        raise RuntimeError("a timing row from 29 Jul 2026 on was loaded")
    t = t.drop(columns=["tournament_date"])
    t["match_id"] = t["match_id"].astype(str)
    p = pd.read_parquet(STAGE0_P, columns=["match_id", "player_id", "opponent_id", "side", "has_box", "spw_n",
                                           "spw_d", "rpw_n", "rpw_d"],
                        filters=[("match_id", "in", ids)])
    p["match_id"] = p["match_id"].astype(str)
    if not p["match_id"].isin(set(ids)).all():
        raise RuntimeError("a player row outside the sealed matches was loaded")
    p = p.rename(columns={"has_box": "has_box_p"})
    r = pd.read_parquet(RATINGS, columns=["match_id", "srf_O_eff_spw_a", "srf_D_eff_spw_a", "srf_O_eff_spw_b",
                                          "srf_D_eff_spw_b"], filters=[("match_id", "in", ids)])
    r["match_id"] = r["match_id"].astype(str)
    if not r["match_id"].isin(set(ids)).all():
        raise RuntimeError("a rating row outside the sealed matches was loaded")
    m = m.merge(t, on="match_id", how="left", validate="one_to_one")
    m = m.merge(r, on="match_id", how="left", validate="one_to_one")
    L = p.merge(m, on="match_id", how="left", validate="many_to_one")
    a = (L["side"] == "A").to_numpy()
    L["own_O"] = np.where(a, L["srf_O_eff_spw_a"], L["srf_O_eff_spw_b"])
    L["own_D"] = np.where(a, L["srf_D_eff_spw_a"], L["srf_D_eff_spw_b"])
    L["opp_O"] = np.where(a, L["srf_O_eff_spw_b"], L["srf_O_eff_spw_a"])
    L = L.drop(columns=["srf_O_eff_spw_a", "srf_D_eff_spw_a", "srf_O_eff_spw_b", "srf_D_eff_spw_b"])
    mus = mu_table()
    sname = L["surface"].map(SURF_NAME).fillna("all")
    L["mu"] = [mus[(tr, s)] for tr, s in zip(L["tour"].to_numpy(), sname.to_numpy())]
    L["box_ok"] = ((L["status"] == "completed") & (L["format"] == "standard") & L["rpw_n"].notna()
                   & L["rpw_d"].notna() & (L["rpw_d"] > 0) & (L["rpw_n"] >= 0) & (L["rpw_n"] <= L["rpw_d"]))
    L["main"] = L["level"].isin(MAIN_LEVELS) & ~L["qualifying"].astype(bool)
    # screen.long_table's order: each event by its earliest best-estimate day, then tournament date and id, round order
    # and match number
    L["tday"] = (pd.to_datetime(L["tournament_date"]) - pd.Timestamp("1970-01-01")).dt.days.astype(float)
    L["ev_obs"] = L.groupby(["player_id", "tournament_id", "tday"])["obs"].transform("min")
    L = L.sort_values(["player_id", "ev_obs", "tday", "tournament_id", "round_order", "match_num"], kind="stable")
    L["k"] = L.groupby("player_id").cumcount()
    return L.reset_index(drop=True)


# -------------------------------------------------------------------------------------------- the time centring

def centring(L: pd.DataFrame) -> np.ndarray:
    """M(es) for every row: the tour's mean pre-match O_eff_spw (each player's own, at main-draw tour-level matches)
    over earliest starts in [es - 364, es); with fewer than MIN_M values, the mean of all earlier ones."""
    out = np.full(len(L), np.nan)
    es = L["es"].to_numpy(float)
    tour = L["tour"].to_numpy()
    oo = L["own_O"].to_numpy(float)
    main = L["main"].to_numpy(bool) & np.isfinite(oo) & np.isfinite(es)
    for t in np.unique(tour):
        src = np.flatnonzero(main & (tour == t))
        o = np.argsort(es[src], kind="stable")
        e_s, v_s = es[src][o], oo[src][o]
        cs = np.r_[0.0, np.cumsum(v_s)]
        tgt = np.flatnonzero(tour == t)
        q = es[tgt]
        hi = np.searchsorted(e_s, q, side="left")
        lo = np.searchsorted(e_s, q - WINDOW_M, side="left")
        n = hi - lo
        with np.errstate(invalid="ignore", divide="ignore"):
            win = (cs[hi] - cs[lo]) / n
            allb = cs[hi] / hi
        out[tgt] = np.where(n >= MIN_M, win, np.where(hi > 0, allb, np.nan))
    return out


# --------------------------------------------------------------------------------------------- the residual rows

def residual_rows(L: pd.DataFrame, M: np.ndarray) -> dict:
    """The return rows that enter histories, with their residual r, unit weight u and time-centred server O."""
    ok = L["box_ok"].to_numpy(bool) & np.isfinite(L["opp_O"].to_numpy(float)) & \
        np.isfinite(L["own_D"].to_numpy(float)) & np.isfinite(M) & np.isfinite(L["lf"].to_numpy(float)) & \
        np.isfinite(L["obs"].to_numpy(float))
    d = L["rpw_d"].to_numpy(float)
    xs = d - L["rpw_n"].to_numpy(float)                       # the server's serve points won
    with np.errstate(invalid="ignore", divide="ignore"):
        y = logit((xs + 0.5) / (d + 1.0)) - L["mu"].to_numpy(float)
    pred = L["opp_O"].to_numpy(float) - L["own_D"].to_numpy(float)
    r = pred - y
    ok &= np.isfinite(r)
    return {"ok": ok, "r": np.where(ok, r, np.nan), "u": np.where(ok, d, 0.0), "y": y, "pred": pred,
            "Ot": L["opp_O"].to_numpy(float) - M}


def _sums(e: np.ndarray, e2: np.ndarray, Ot: np.ndarray, r: np.ndarray) -> np.ndarray:
    """Columns: n, sum e, e O, e O^2, e r, e O r, e2, e2 O, e2 O^2 (the moments a slope and its variance need)."""
    return np.column_stack([np.ones(len(e)), e, e * Ot, e * Ot ** 2, e * r, e * Ot * r, e2, e2 * Ot, e2 * Ot ** 2])


def _slope(S: np.ndarray) -> dict:
    """b_hat, Obar, v_unit, n, Sxx (per e unit) from the moment columns of _sums (rows: targets)."""
    n, A0, A1, A2, B1, B2, C0, C1, C2 = S.T
    with np.errstate(invalid="ignore", divide="ignore"):
        Ob = A1 / A0
        Sxx = A2 - A1 * Ob
        Sxy = B2 - Ob * B1
        good = (n >= 3) & (A0 > 0) & (Sxx > 1e-10 * A0)
        b = np.where(good, Sxy / Sxx, np.nan)
        num = C2 - 2 * Ob * C1 + Ob ** 2 * C0
        v = np.where(good, num / Sxx ** 2, np.nan)
    return {"b": b, "Obar": np.where(A0 > 0, Ob, np.nan), "v": v, "n": n, "good": good}


# ------------------------------------------------------------------------------------------------ the builder

def snapshot_days() -> list[int]:
    return [day_of(f"{y}-01-01") for y in range(2011, 2027)]


def build(L: pd.DataFrame, h: float = H_DAYS, prior: str = PRIOR, tables: bool = False):
    """Per row of L: the returner's slope, centre, variance, the empirical-Bayes slope and the matchup term's half
    (term = b* (O~_opp - Obar)); with tables=True also the snapshots' split-half and empirical-Bayes table."""
    M = centring(L)
    R = residual_rows(L, M)
    pc = pd.factorize(L["player_id"])[0].astype(np.int64)
    es, lf, obs = (L[c].to_numpy(float) for c in ("es", "lf", "obs"))
    tour = L["tour"].to_numpy()
    k = L["k"].to_numpy(np.int64)
    ok = R["ok"]
    ri = np.flatnonzero(ok)
    rel = lf[ri] + 1
    lam = 1.0 / h
    e = R["u"][ri] * np.exp2((obs[ri] - REF_DAY) * lam)
    e2 = R["u"][ri] * np.exp2(2 * (obs[ri] - REF_DAY) * lam)
    Ot, r = R["Ot"][ri], R["r"][ri]
    mom = _sums(e, e2, Ot, r)

    # targets: every row with a finite earliest start; history = the same player's residual rows released by es
    keyr = pc[ri] * KEY + rel.astype(np.int64)
    o = np.argsort(keyr, kind="stable")
    keyr_s = keyr[o]
    # cumulative moments within each player (a running total across players would make an early, small sum the
    # difference of two huge ones)
    cum = pd.DataFrame(mom[o]).groupby(pc[ri][o]).cumsum().to_numpy()
    tg = np.flatnonzero(np.isfinite(es))
    keyt = pc[tg] * KEY + es[tg].astype(np.int64)
    hi = np.searchsorted(keyr_s, keyt, side="right")
    lo = np.searchsorted(keyr_s, pc[tg] * KEY, side="left")
    Sm = np.where((hi > lo)[:, None], cum[np.maximum(hi - 1, 0)], 0.0)
    sl = _slope(Sm)

    # the snapshots: split-half per player, the chance spread s^2, the population slope, the true spread tau^2
    half = np.empty(len(ri), np.int64)
    rank = pd.Series(k[ri]).groupby(pc[ri]).rank(method="first").to_numpy().astype(np.int64)
    half[:] = rank % 2
    snaps = snapshot_days()
    rows = []
    eb = {}
    for t in np.unique(tour):
        it = tour[ri] == t
        for S in snaps:
            el = it & (rel <= S)
            if el.sum() < 1000:
                continue
            res = {}
            for hh in (0, 1):
                mk = el & (half == hh)
                P = np.zeros((pc.max() + 1, mom.shape[1]))
                for c in range(mom.shape[1]):
                    P[:, c] = np.bincount(pc[ri][mk], weights=mom[mk, c], minlength=pc.max() + 1)
                res[hh] = _slope(P)
            b0, b1 = res[0]["b"], res[1]["b"]
            v0, v1 = res[0]["v"], res[1]["v"]
            use = res[0]["good"] & res[1]["good"] & (res[0]["n"] >= NMIN_HALF) & (res[1]["n"] >= NMIN_HALF) & \
                np.isfinite(b0) & np.isfinite(b1) & np.isfinite(v0) & np.isfinite(v1)
            b0, b1, v0, v1 = b0[use], b1[use], v0[use], v1[use]
            npl = int(use.sum())
            if npl < 30:
                continue
            s2 = float(np.mean((b0 - b1) ** 2 / (v0 + v1)))
            s2_med = float(np.median((b0 - b1) ** 2 / (v0 + v1)) / 0.4549364)
            tau2 = max(float(np.cov(b0, b1)[0, 1]), 0.0)
            for _ in range(20):
                w = 1.0 / ((tau2 + s2 * v0) * (tau2 + s2 * v1))
                m0, m1 = np.sum(w * b0) / w.sum(), np.sum(w * b1) / w.sum()
                new = max(float(np.sum(w * (b0 - m0) * (b1 - m1)) / w.sum()), 0.0)
                if abs(new - tau2) < 1e-12:
                    tau2 = new
                    break
                tau2 = new
            w = 1.0 / ((tau2 + s2 * v0) * (tau2 + s2 * v1)) if tau2 > 0 else 1.0 / (s2 * v0 * s2 * v1)
            m0, m1 = np.sum(w * b0) / w.sum(), np.sum(w * b1) / w.sum()
            cw = np.sum(w * (b0 - m0) * (b1 - m1)) / w.sum()
            sw0 = np.sqrt(np.sum(w * (b0 - m0) ** 2) / w.sum())
            sw1 = np.sqrt(np.sum(w * (b1 - m1) ** 2) / w.sum())
            r_w = float(cw / (sw0 * sw1))
            r_u = float(np.corrcoef(b0, b1)[0, 1])
            bbar = float((m0 + m1) / 2)
            eb[(t, S)] = {"s2": s2, "tau2": tau2, "bbar": bbar}
            # reliability of a typical player's full-history slope (v halves ~ 2 v_full)
            vfull_med = float(np.median(1.0 / (1.0 / v0 + 1.0 / v1)))
            rows.append({"tour": t, "snapshot": str(pd.Timestamp("1970-01-01") + pd.Timedelta(days=S))[:10],
                         "players": npl, "matches_per_half_median": float(np.median(res[0]["n"][use])),
                         "s2": s2, "s2_median_based": s2_med, "tau2": tau2, "tau": float(np.sqrt(tau2)),
                         "b_bar": bbar, "split_half_r_weighted": r_w, "split_half_r_unweighted": r_u,
                         "spearman_brown_weighted": float(2 * r_w / (1 + r_w)) if r_w > -1 else np.nan,
                         "chance_sd_full_median": float(np.sqrt(s2 * vfull_med)),
                         "lambda_median_player": float(tau2 / (tau2 + s2 * vfull_med)) if tau2 > 0 else 0.0})

    # each target reads the latest snapshot <= es (per tour); before the first snapshot: no value
    s2_t, tau2_t, bbar_t = (np.full(len(tg), np.nan) for _ in range(3))
    snap_arr = np.array(snaps, float)
    for t in np.unique(tour):
        mt = tour[tg] == t
        have = [S for S in snaps if (t, S) in eb]
        if not have:
            continue
        hv = np.array(have, float)
        j = np.searchsorted(hv, es[tg][mt], side="right") - 1
        okj = j >= 0
        idx = np.flatnonzero(mt)[okj]
        sel = [eb[(t, int(hv[q]))] for q in j[okj]]
        s2_t[idx] = [d_["s2"] for d_ in sel]
        tau2_t[idx] = [d_["tau2"] for d_ in sel]
        bbar_t[idx] = [d_["bbar"] for d_ in sel]
    del snap_arr
    b, v = sl["b"], sl["v"]
    prior_mean = bbar_t if prior == "population" else np.zeros(len(tg))
    with np.errstate(invalid="ignore", divide="ignore"):
        lam_j = np.where(np.isfinite(v) & np.isfinite(tau2_t), tau2_t / (tau2_t + s2_t * v), np.nan)
    bstar = np.where(np.isfinite(b) & np.isfinite(lam_j), lam_j * (b - prior_mean), 0.0)  # the deviation from the prior
    Ot_tgt = R["Ot"][tg]
    term = np.where(np.isfinite(Ot_tgt) & np.isfinite(sl["Obar"]), bstar * (Ot_tgt - sl["Obar"]), 0.0)
    term = np.where(np.isfinite(Ot_tgt), term, np.nan)
    vals = pd.DataFrame({"match_id": L["match_id"].to_numpy()[tg], "player_id": L["player_id"].to_numpy()[tg],
                         "b_hat": b, "v_unit": v, "obar": sl["Obar"], "n_hist": sl["n"], "lambda": lam_j,
                         "b_star": bstar, "term": term, "Ot_opp": Ot_tgt})
    if tables:
        return vals, pd.DataFrame(rows), R, M
    return vals


# ------------------------------------------------------------------------------------------------- the checks

def check(L: pd.DataFrame) -> dict:
    """Outcome-free: how the ratings map to the IOS prediction and to Stage 0's serve and return points; coverage."""
    out = {}
    # (1) Stage 0's return points are the opponent's serve points
    opp = L[["match_id", "player_id", "spw_n", "spw_d"]].rename(columns={"player_id": "opponent_id",
                                                                         "spw_n": "o_spw_n", "spw_d": "o_spw_d"})
    J = L[["match_id", "opponent_id", "rpw_n", "rpw_d", "box_ok"]].merge(opp, on=["match_id", "opponent_id"],
                                                                          how="left")
    b = J["box_ok"].to_numpy(bool)
    out["return_equals_opponent_serve"] = {
        "box_rows": int(b.sum()),
        "rpw_d_eq_opp_spw_d": int((J.loc[b, "rpw_d"] == J.loc[b, "o_spw_d"]).sum()),
        "rpw_n_eq_opp_spw_d_minus_spw_n": int((J.loc[b, "rpw_n"] == J.loc[b, "o_spw_d"] - J.loc[b, "o_spw_n"]).sum())}
    # (2) sides: the match id carries player A's and B's ids in its last two fields
    parts = L["match_id"].str.split("|")
    pa, pb = parts.str[-2], parts.str[-1]
    own = np.where(L["side"] == "A", pa, pb)
    out["side_matches_match_id"] = {"rows": int(len(L)), "agree": int((own == L["player_id"].to_numpy()).sum())}
    # (3) the solver's mu: the cache's per-row centring (outcome-free) at pool rows equals mu here
    pool = pd.read_parquet(POOL, columns=["match_id", "tour", "pos_a", "pos_b"])
    pool["match_id"] = pool["match_id"].astype(str)
    agree, n = 0, 0
    for t in ("atp", "wta"):
        with np.load(CACHE / f"{t}.npz", allow_pickle=False) as z:
            mu_c = z["spw__mu"]                          # a constant per tour and surface: no result in it
        pt = pool[pool["tour"] == t]
        Lt = L[(L["tour"] == t) & (L["side"] == "A")][["match_id", "mu"]]
        g = Lt.merge(pt, on="match_id", how="inner")
        n += len(g)
        agree += int(np.isclose(mu_c[g["pos_a"].to_numpy()], g["mu"].to_numpy(), atol=1e-9).sum())
    out["mu_equals_solver_cache"] = {"pool_matches_compared": n, "agree": agree}
    # (4) calibration of the IOS prediction: y on O_srv - D_ret, weighted by points, by tour and era
    M = centring(L)
    R = residual_rows(L, M)
    ok = R["ok"]
    yr = pd.to_datetime(L["tournament_date"]).dt.year.to_numpy()
    cal = []
    for t in ("atp", "wta"):
        for lab, (a, z_) in {"2010-12": (2010, 2012), "2013-16": (2013, 2016), "2017-19": (2017, 2019),
                             "2020-22": (2020, 2022), "2023-24": (2023, 2024), "2025-26": (2025, 2026)}.items():
            for scope in ("all", "main"):
                m = ok & (L["tour"].to_numpy() == t) & (yr >= a) & (yr <= z_)
                if scope == "main":
                    m &= L["main"].to_numpy(bool)
                if m.sum() < 100:
                    continue
                w, x_, y_ = R["u"][m], R["pred"][m], R["y"][m]
                X = np.column_stack([np.ones(m.sum()), x_])
                beta = np.linalg.solve((X.T * w) @ X, (X.T * w) @ y_)
                cal.append({"tour": t, "years": lab, "scope": scope, "rows": int(m.sum()), "intercept": float(beta[0]),
                            "slope_y_on_pred": float(beta[1]),
                            "mean_residual_weighted": float(np.sum(w * R["r"][m]) / w.sum()),
                            "sd_pred": float(np.sqrt(np.cov(x_, aweights=w))),
                            "corr": float(np.corrcoef(x_, y_)[0, 1])})
    out["calibration"] = cal
    # (5) coverage of the box-score return rows by the ratings (the pool), by tour and level
    cov = []
    for (t, lv), g in L[L["box_ok"]].groupby(["tour", "level"]):
        has = np.isfinite(g["opp_O"]) & np.isfinite(g["own_D"])
        cov.append({"tour": t, "level": lv, "box_return_rows": int(len(g)), "with_ratings": int(has.sum())})
    out["coverage_by_level"] = cov
    # (6) the time centring M(t), by tour and year (mean over the year's rows)
    mc = pd.DataFrame({"tour": L["tour"], "year": yr, "M": M}).groupby(["tour", "year"])["M"].mean()
    out["centring_M_by_year"] = {f"{t}|{y}": float(v) for (t, y), v in mc.items()}
    return out


# ------------------------------------------------------------------------------------------------- the frame

def frame_x(vals: pd.DataFrame, frame: pd.DataFrame) -> tuple[np.ndarray, dict]:
    """x = term_A - term_B on the frame's rows (NaN where the match has no rating), and coverage counts."""
    a, b = H.at_frame(vals, "term", frame)
    x = a - b
    na, nb = H.at_frame(vals, "n_hist", frame)
    info = {"rows": int(len(frame)), "with_term": int(np.isfinite(x).sum()),
            "nonzero": int(np.sum(np.isfinite(x) & (x != 0))),
            "both_sides_history_ge_20": int(np.sum((np.nan_to_num(na) >= 20) & (np.nan_to_num(nb) >= 20)))}
    return x, info


def frame_free(tour: str, inputs: bool = False) -> pd.DataFrame:
    """The 10 Oct instance's frame rows before 29 Jul 2026, seasons 2013-2026, debut seasons out, with the players'
    ids and (inputs=True) the model's inputs; no result column: for outcome-free coverage, scale and redundancy checks
    before any reading."""
    cols = ["match_id", "tour", "season", "tournament_date", "debut_season"]
    if inputs:
        names = H.diff_input_names()
        allc = [d["name"] for d in json.loads((C.INSTANCE / "model_inputs.json").read_text(encoding="utf-8"))["inputs"]]
        cols += [f"in_{n}" for n in allc if n not in H.CONTEXT and n != "odds_logit"]
    f = pd.read_parquet(C.INSTANCE / "model_frame.parquet", columns=cols,
                        filters=[("tournament_date", "<", SEALED_FROM)])
    if f["tournament_date"].max() >= SEALED_FROM:
        raise RuntimeError("a frame row from 29 Jul 2026 on was loaded")
    f["match_id"] = f["match_id"].astype(str)
    f = f[(f["tour"] == tour) & (f["season"].between(2013, 2026)) & ~f["debut_season"].astype(bool)].copy()
    if inputs:
        for k_, (a, b) in H.PAIRS.items():
            f[f"in_{k_}"] = f[f"in_{a}"] - f[f"in_{b}"]
        del names
    st = pd.read_parquet(STAGE0_M, columns=["match_id", "player_a_id", "player_b_id"],
                         filters=[("tournament_date", "<", SEALED_FROM)]).astype({"match_id": str})
    return f.merge(st, on="match_id", how="left", validate="one_to_one").reset_index(drop=True)


# ------------------------------------------------------------------------------------------------- the points check

def points_check(L: pd.DataFrame, vals: pd.DataFrame) -> pd.DataFrame:
    """Does the term predict the target match's own return points beyond the additive IOS prediction? The target's
    return residual r_m (its pre-match ratings; matches before 29 Jul 2026 only) on the term, weighted by return points,
    with an intercept, cluster-robust over four-week blocks: slope 1 = calibrated, 0 = no information. Rows: each
    returner in the frame-level (main-draw tour-level) matches, by tour and window; and the match-level difference
    (r_A - r_B on term_A - term_B). Reads no won/lost result."""
    M = centring(L)
    R = residual_rows(L, M)
    v = vals.set_index(["match_id", "player_id"])
    key = pd.MultiIndex.from_arrays([L["match_id"], L["player_id"]])
    term = v["term"].reindex(key).to_numpy(float)
    nh = v["n_hist"].reindex(key).to_numpy(float)
    ok = R["ok"] & np.isfinite(term) & L["main"].to_numpy(bool)
    yr = pd.to_datetime(L["tournament_date"]).dt.year.to_numpy()
    blk = H.blocks(pd.to_datetime(L["tournament_date"]).to_numpy(), 28)
    tour = L["tour"].to_numpy()
    rows = []
    wins = {"2013-16": (2013, 2016), "2017-19": (2017, 2019), "2020-22": (2020, 2022), "2023-24": (2023, 2024),
            "2013-24": (2013, 2024), "2025-26": (2025, 2026)}

    def wls(xv, yv, wv, bl):
        X = np.column_stack([np.ones(len(xv)), xv])
        XtW = X.T * wv
        A = np.linalg.inv(XtW @ X)
        beta = A @ (XtW @ yv)
        e = yv - X @ beta
        labels, ix = np.unique(bl, return_inverse=True)
        Sg = np.zeros((len(labels), 2))
        np.add.at(Sg, ix, X * (wv * e)[:, None])
        G = len(labels)
        V = G / (G - 1) * A @ (Sg.T @ Sg) @ A
        return float(beta[1]), float(np.sqrt(V[1, 1])), G

    for t in ("atp", "wta"):
        for w, (a, z_) in wins.items():
            m = ok & (tour == t) & (yr >= a) & (yr <= z_)
            if m.sum() < 200:
                continue
            for lab, mm in (("all returners", m), ("history >= 50", m & (nh >= 50))):
                xs = term[mm]
                if np.sum(xs != 0) < 100:
                    continue
                b_, se, G = wls(xs, R["r"][mm], R["u"][mm], blk[mm])
                rows.append({"tour": t, "window": w, "rows": lab, "level": "row", "n": int(mm.sum()),
                             "sd_term": float(np.std(xs)), "slope": b_, "se": se, "z": b_ / se, "blocks": G})
            # the match level: both sides' residuals present
            df = pd.DataFrame({"match_id": L["match_id"].to_numpy()[m], "side": L["side"].to_numpy()[m],
                               "r": R["r"][m], "u": R["u"][m], "term": term[m], "blk": blk[m]})
            A_ = df[df["side"] == "A"].set_index("match_id")
            B_ = df[df["side"] == "B"].set_index("match_id")
            J = A_.join(B_, lsuffix="_a", rsuffix="_b", how="inner")
            if len(J) >= 200:
                xd = (J["term_a"] - J["term_b"]).to_numpy()
                yd = (J["r_a"] - J["r_b"]).to_numpy()
                wd = 1.0 / (1.0 / J["u_a"].to_numpy() + 1.0 / J["u_b"].to_numpy())
                b_, se, G = wls(xd, yd, wd, J["blk_a"].to_numpy())
                rows.append({"tour": t, "window": w, "rows": "match A - B", "level": "match", "n": int(len(J)),
                             "sd_term": float(np.std(xd)), "slope": b_, "se": se, "z": b_ / se, "blocks": G})
    return pd.DataFrame(rows)


def points_control(L: pd.DataFrame, vals: pd.DataFrame) -> pd.DataFrame:
    """The points check's row slope with the population interaction held fixed: the target's return residual on
    [1, term, O~_opp, D~_own, O~_opp x D~_own] (D~ time-centred like O~), weighted by points, cluster-robust over
    four-week blocks, frame-level rows. If the term keeps its slope, the returner's own elasticity carries information
    beyond the population's 'strong returners gain more against big servers' (which the model's prod_* resemble)."""
    M = centring(L)
    R = residual_rows(L, M)
    Ld = L.copy()
    Ld["own_O"] = L["own_D"]
    Dt = L["own_D"].to_numpy(float) - centring(Ld)
    v = vals.set_index(["match_id", "player_id"])
    key = pd.MultiIndex.from_arrays([L["match_id"], L["player_id"]])
    term = v["term"].reindex(key).to_numpy(float)
    Oo = v["Ot_opp"].reindex(key).to_numpy(float)
    ok = R["ok"] & np.isfinite(term) & np.isfinite(Oo) & np.isfinite(Dt) & L["main"].to_numpy(bool)
    yr = pd.to_datetime(L["tournament_date"]).dt.year.to_numpy()
    blk = H.blocks(pd.to_datetime(L["tournament_date"]).to_numpy(), 28)
    tour = L["tour"].to_numpy()
    rows = []
    for t in ("atp", "wta"):
        for w, (a, z_) in {"2013-16": (2013, 2016), "2017-19": (2017, 2019), "2020-22": (2020, 2022),
                           "2023-24": (2023, 2024), "2013-24": (2013, 2024), "2025-26": (2025, 2026)}.items():
            m = ok & (tour == t) & (yr >= a) & (yr <= z_)
            if m.sum() < 200 or np.sum(term[m] != 0) < 100:
                continue
            wv = R["u"][m]
            Oc = Oo[m] - np.average(Oo[m], weights=wv)
            Dc = Dt[m] - np.average(Dt[m], weights=wv)
            X = np.column_stack([np.ones(m.sum()), term[m], Oc, Dc, Oc * Dc])
            XtW = X.T * wv
            A = np.linalg.inv(XtW @ X)
            beta = A @ (XtW @ R["r"][m])
            e = R["r"][m] - X @ beta
            labels, ix = np.unique(blk[m], return_inverse=True)
            Sg = np.zeros((len(labels), X.shape[1]))
            np.add.at(Sg, ix, X * (wv * e)[:, None])
            G = len(labels)
            V = G / (G - 1) * A @ (Sg.T @ Sg) @ A
            se = np.sqrt(np.diag(V))
            rows.append({"tour": t, "window": w, "n": int(m.sum()), "slope_term": float(beta[1]),
                         "se_term": float(se[1]), "z_term": float(beta[1] / se[1]), "b_OxD": float(beta[4]),
                         "z_OxD": float(beta[4] / se[4]),
                         "corr_term_OxD": float(np.corrcoef(term[m], Oc * Dc)[0, 1])})
    return pd.DataFrame(rows)


def implied_effect(L: pd.DataFrame, vals: pd.DataFrame) -> list[dict]:
    """Outcome-free benchmark: the match log-odds shift the term implies if it is calibrated in points (the points
    check) and nothing of it is priced. Per frame match: the IOS serve-point chances p_A = expit(mu + O_A - D_B),
    p_B = expit(mu + O_B - D_A) from the pre-match ratings; each serve-point logit lowered by the other side's term;
    the shift = logit P_match(after) - logit P_match(before) under the iid match model (stage2_iid.match_win, the
    match's best-of, standard sets). k = sum(shift x) / sum(x^2); the implied beta per RMS = k RMS(x) in the window,
    the scale `read` reports."""
    from scipy.special import expit
    from src.eda.predictability_diagnostic import stage2_iid as IID
    bo = pd.read_parquet(STAGE0_M, columns=["match_id", "best_of", "tournament_date"],
                         filters=[("tournament_date", "<", SEALED_FROM)])
    bo["match_id"] = bo["match_id"].astype(str)
    bo = bo.set_index("match_id")["best_of"]
    v = vals.set_index(["match_id", "player_id"])["term"]
    Li = L.set_index(["match_id", "player_id"])
    out = []
    for t in ("atp", "wta"):
        f = frame_free(t)
        ka = pd.MultiIndex.from_arrays([f["match_id"], f["player_a_id"]])
        kb = pd.MultiIndex.from_arrays([f["match_id"], f["player_b_id"]])
        OA, DA, mu = (Li[c].reindex(ka).to_numpy(float) for c in ("own_O", "own_D", "mu"))
        OB, DB = (Li[c].reindex(kb).to_numpy(float) for c in ("own_O", "own_D"))
        tA, tB = v.reindex(ka).to_numpy(float), v.reindex(kb).to_numpy(float)
        b_o = bo.reindex(f["match_id"]).to_numpy(float)
        ok = np.isfinite(OA + DA + OB + DB + mu + tA + tB + b_o)
        la, lb = mu + OA - DB, mu + OB - DA
        shift = np.full(len(f), np.nan)
        for B_ in (3, 5):
            m = ok & (b_o == B_)
            if not m.any():
                continue
            p0 = IID.match_win(expit(la[m]), expit(lb[m]), B_)
            p1 = IID.match_win(expit(la[m] - tB[m]), expit(lb[m] - tA[m]), B_)
            shift[m] = logit(np.clip(p1, 1e-9, 1 - 1e-9)) - logit(np.clip(p0, 1e-9, 1 - 1e-9))
        x = tA - tB
        for w, (a, z_) in {"2013-24": (2013, 2024), "2020-24": (2020, 2024), "2025-26": (2025, 2026)}.items():
            m = ok & f["season"].between(a, z_).to_numpy() & np.isfinite(shift)
            if m.sum() < 100 or np.sum(x[m] ** 2) == 0:
                continue
            k = float(np.sum(shift[m] * x[m]) / np.sum(x[m] ** 2))
            rms = float(np.sqrt(np.mean(x[m] ** 2)))
            out.append({"tour": t, "window": w, "matches": int(m.sum()), "k_logodds_per_unit_x": k, "rms_x": rms,
                        "implied_beta_per_rms": k * rms, "rms_shift_logodds": float(np.sqrt(np.mean(shift[m] ** 2)))})
    return out


# ------------------------------------------------------------------------------------------------- reliability

def halves_at(L: pd.DataFrame, R: dict, S: int, tour: str, h: float = H_DAYS) -> pd.DataFrame:
    """Per player of one tour: the two alternate-match halves' slopes of his history released by day S (decay to S),
    as build()'s snapshots compute them (outcome-free; for the reliability tables)."""
    pc = pd.factorize(L["player_id"])[0].astype(np.int64)
    lf, obs = L["lf"].to_numpy(float), L["obs"].to_numpy(float)
    k = L["k"].to_numpy(np.int64)
    ri = np.flatnonzero(R["ok"])
    rel = lf[ri] + 1
    e = R["u"][ri] * np.exp2((obs[ri] - REF_DAY) / h)
    e2 = R["u"][ri] * np.exp2(2 * (obs[ri] - REF_DAY) / h)
    mom = _sums(e, e2, R["Ot"][ri], R["r"][ri])
    rank = pd.Series(k[ri]).groupby(pc[ri]).rank(method="first").to_numpy().astype(np.int64)
    half = rank % 2
    el = (L["tour"].to_numpy()[ri] == tour) & (rel <= S)
    out = {}
    for hh in (0, 1):
        mk = el & (half == hh)
        P = np.zeros((pc.max() + 1, mom.shape[1]))
        for c in range(mom.shape[1]):
            P[:, c] = np.bincount(pc[ri][mk], weights=mom[mk, c], minlength=pc.max() + 1)
        out[hh] = _slope(P)
    df = pd.DataFrame({"b0": out[0]["b"], "b1": out[1]["b"], "v0": out[0]["v"], "v1": out[1]["v"],
                       "n0": out[0]["n"], "n1": out[1]["n"]})
    return df[np.isfinite(df["b0"]) & np.isfinite(df["b1"]) & np.isfinite(df["v0"]) & np.isfinite(df["v1"])]


def reliability(L: pd.DataFrame) -> dict:
    """Outcome-free: (1) the split-half correlation of the slopes by data volume (players with at least n matches in
    each half) at four snapshots; (2) the population question, do strong returners in general gain more against big
    servers: weighted least squares of r on O~, D~ and O~ x D~ (D~ = the returner's D minus the tour's 52-week mean),
    by tour and era, cluster-robust over four-week blocks."""
    M = centring(L)
    R = residual_rows(L, M)
    out = {"by_volume": [], "population_interaction": []}
    for t in ("atp", "wta"):
        for snap in ("2017-01-01", "2020-01-01", "2023-01-01", "2026-01-01"):
            df = halves_at(L, R, day_of(snap), t)
            for nmin in (10, 25, 50, 100):
                g = df[(df["n0"] >= nmin) & (df["n1"] >= nmin)]
                if len(g) < 20:
                    continue
                r_ = float(np.corrcoef(g["b0"], g["b1"])[0, 1])
                s2 = float(np.mean((g["b0"] - g["b1"]) ** 2 / (g["v0"] + g["v1"])))
                out["by_volume"].append({"tour": t, "snapshot": snap, "min_matches_per_half": nmin,
                                         "players": int(len(g)), "median_matches_per_half": float(np.median(g["n0"])),
                                         "split_half_r": r_,
                                         "spearman_brown": float(2 * r_ / (1 + r_)) if r_ > -1 else np.nan,
                                         "cov_halves": float(np.cov(g["b0"], g["b1"])[0, 1]),
                                         "sd_half_slope": float(np.std(np.r_[g["b0"], g["b1"]])),
                                         "chance_sd_half_slope_median":
                                             float(np.sqrt(s2 * np.median(np.r_[g["v0"], g["v1"]])))})
    # D~: the returner's D minus the tour's 52-week main-draw mean of D (the same centring as O)
    Ld = L.copy()
    Ld["own_O"] = L["own_D"]
    MD = centring(Ld)
    Dt = L["own_D"].to_numpy(float) - MD
    yr = pd.to_datetime(L["tournament_date"]).dt.year.to_numpy()
    blk = H.blocks(pd.to_datetime(L["tournament_date"]).to_numpy(), 28)
    for t in ("atp", "wta"):
        for lab, (a, z_) in {"2010-12": (2010, 2012), "2013-16": (2013, 2016), "2017-19": (2017, 2019),
                             "2020-22": (2020, 2022), "2023-24": (2023, 2024), "2025-26": (2025, 2026)}.items():
            m = R["ok"] & np.isfinite(Dt) & (L["tour"].to_numpy() == t) & (yr >= a) & (yr <= z_)
            if m.sum() < 1000:
                continue
            Ot, D_, r, w = R["Ot"][m], Dt[m], R["r"][m], R["u"][m]
            Ot_c, D_c = Ot - np.average(Ot, weights=w), D_ - np.average(D_, weights=w)
            X = np.column_stack([np.ones(m.sum()), Ot_c, D_c, Ot_c * D_c])
            XtW = X.T * w
            A = np.linalg.inv(XtW @ X)
            beta = A @ (XtW @ r)
            e = r - X @ beta
            labels, ix = np.unique(blk[m], return_inverse=True)
            Sg = np.zeros((len(labels), 4))
            np.add.at(Sg, ix, X * (w * e)[:, None])
            G = len(labels)
            V = G / (G - 1) * A @ (Sg.T @ Sg) @ A
            se = np.sqrt(np.diag(V))
            out["population_interaction"].append(
                {"tour": t, "years": lab, "rows": int(m.sum()), "b_O": float(beta[1]), "z_O": float(beta[1] / se[1]),
                 "b_D": float(beta[2]), "z_D": float(beta[2] / se[2]), "b_OxD": float(beta[3]),
                 "z_OxD": float(beta[3] / se[3]), "sd_O": float(np.sqrt(np.average(Ot_c ** 2, weights=w))),
                 "sd_D": float(np.sqrt(np.average(D_c ** 2, weights=w)))})
    return out


# ------------------------------------------------------------------------------------------------- the steps

def step_reliability() -> None:
    L = long_table()
    res = reliability(L)
    C.write_json(OUT / "reliability.json", res)
    with pd.option_context("display.width", 250):
        print(pd.DataFrame(res["by_volume"]).round(4).to_string(index=False))
        print(pd.DataFrame(res["population_interaction"]).round(4).to_string(index=False))


def step_check() -> None:
    L = long_table()
    log(f"long table: {len(L):,} rows")
    res = check(L)
    C.write_json(OUT / "check.json", res)
    print(json.dumps({k: v for k, v in res.items() if k not in ("coverage_by_level", "centring_M_by_year",
                                                                "calibration")}, indent=1, default=float))
    print(pd.DataFrame(res["calibration"]).round(4).to_string(index=False))
    print(pd.DataFrame(res["coverage_by_level"]).to_string(index=False))
    print({k: round(v, 3) for k, v in res["centring_M_by_year"].items()})


def step_build() -> None:
    L = long_table()
    log(f"long table: {len(L):,} rows")
    vals, snaps, R, M = build(L, tables=True)
    log("built")
    OUT.mkdir(parents=True, exist_ok=True)
    vals.to_parquet(OUT / "values.parquet", index=False)
    snaps.to_csv(OUT / "snapshots.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(snaps.round(4).to_string(index=False))
    rep = {"h_days": H_DAYS, "prior": PRIOR, "nmin_half": NMIN_HALF, "values_sha256": sha256(OUT / "values.parquet"),
           "rows": int(len(vals)), "residual_rows": int(R["ok"].sum()),
           "residual_rows_by_tour": {t: int((R["ok"] & (L["tour"].to_numpy() == t)).sum()) for t in ("atp", "wta")}}
    for t in ("atp", "wta"):
        f = frame_free(t, inputs=True)
        x, info = frame_x(vals, f)
        s = pd.Series(x).groupby(f["season"].to_numpy())
        rep[f"frame_{t}"] = info
        rep[f"frame_{t}_rms_by_season"] = {int(k_): float(np.sqrt(np.nanmean(v_.to_numpy() ** 2))) for k_, v_ in s}
        rep[f"frame_{t}_nonzero_by_season"] = {int(k_): float(np.mean(np.nan_to_num(v_.to_numpy()) != 0))
                                               for k_, v_ in s}
        f["tour"] = t
        r2 = H.redundancy(f, np.where(np.isfinite(x), x, np.nan), kind="diff")
        rep[f"frame_{t}_r2_on_48_inputs"] = r2.get(t)
        xx = np.nan_to_num(x)
        rep[f"frame_{t}_corr_with_inputs"] = {
            c[3:]: float(np.corrcoef(xx, np.nan_to_num(f[c].to_numpy(float)))[0, 1])
            for c in [f"in_{n}" for n in H.diff_input_names()] if np.nanstd(f[c].to_numpy(float)) > 0}
        top = sorted(rep[f"frame_{t}_corr_with_inputs"].items(), key=lambda kv: -abs(kv[1]))[:8]
        rep[f"frame_{t}_top_input_corr"] = dict(top)
    C.write_json(OUT / "build.json", rep)
    print(json.dumps({k: v for k, v in rep.items() if "corr_with_inputs" not in k}, indent=1, default=float))


def probe_detail(L: pd.DataFrame, cols=("b_hat", "v_unit", "obar", "n_hist", "b_star"),
                 cuts=("2016-06-01", "2019-03-01", "2022-09-01"), seed: int = 20261013) -> list[dict]:
    """screen.timing_probe's scrambling (the same rule and random stream), reported per value column, with each
    compared row's empirical-Bayes snapshot placed before or after the cut: the per-player values (b_hat, v_unit,
    obar, n_hist) use the player's own earlier rows only; b_star also reads the population constants of the latest
    1 January snapshot on or before the target's earliest start, which pool every player's rows released by that day,
    so a snapshot after the cut legitimately holds scrambled rows (each finished before the target could start)."""
    rng = np.random.default_rng(seed)
    base = build(L).set_index(["match_id", "player_id"])[list(cols)]
    box = [c for c in L.columns if c not in ("match_id", "player_id", "opponent_id", "side", "k", "tday", "es", "lf",
                                              "obs", "obs_mono", "ev_obs", "exact", "start", "rest_days", "rest_min",
                                              "rank", "rank_points", "seed", "entry", "age", "height", "hand",
                                              "country", "tour", "level", "qualifying", "round", "round_order",
                                              "match_num", "surface", "indoor", "best_of", "draw_size",
                                              "tournament_id", "tournament_name", "tournament_date", "has_box")
           and (c in H.RESULT_COLS or pd.api.types.is_numeric_dtype(L[c]))]
    snaps = np.array(snapshot_days(), float)
    out = []
    for cut in cuts:
        c_day = day_of(cut)
        after = (L["es"].to_numpy(float) >= c_day) | ~np.isfinite(L["es"].to_numpy(float))
        S = L.copy()
        idx = np.flatnonzero(after)
        for c in box:
            if c == "won":
                S.loc[S.index[idx], c] = rng.random(len(idx)) < 0.5
            else:
                S.loc[S.index[idx], c] = S[c].to_numpy()[rng.permutation(idx)]
        new = build(S).set_index(["match_id", "player_id"])[list(cols)]
        A = pd.DataFrame({"player_id": L["player_id"].to_numpy(), "k": L["k"].to_numpy(), "after": after})
        first_after = A[A["after"]].groupby("player_id")["k"].min()
        last_before_max = A[~A["after"]].groupby("player_id")["k"].max()
        okp = first_after.index[(first_after > last_before_max.reindex(first_after.index).fillna(-1)).to_numpy()]
        fa = first_after.loc[okp]
        own = L.set_index(["player_id", "k"]).index.isin(pd.MultiIndex.from_arrays([fa.index, fa.to_numpy()]))
        for lab, sel in (("future (lf + 1 <= cut)", L["lf"].to_numpy(float) + 1 <= c_day), ("own first match", own)):
            rows = L.loc[sel]
            keys = pd.MultiIndex.from_frame(rows[["match_id", "player_id"]])
            snap_of = snaps[np.clip(np.searchsorted(snaps, rows["es"].to_numpy(float), side="right") - 1, 0, None)]
            snap_after = snap_of > c_day
            for c in cols:
                a = base[c].reindex(keys).to_numpy(float)
                b = new[c].reindex(keys).to_numpy(float)
                ch = ~((a == b) | (np.isnan(a) & np.isnan(b)))
                out.append({"cut": cut, "rows": lab, "column": c, "compared": int(len(keys)), "changed": int(ch.sum()),
                            "compared_snapshot_after_cut": int(snap_after.sum()),
                            "changed_snapshot_after_cut": int((ch & snap_after).sum()),
                            "changed_snapshot_before_cut": int((ch & ~snap_after).sum())})
    return out


def step_probe() -> None:
    L = long_table()
    log(f"long table: {len(L):,} rows; probe")
    # the probe scrambles every numeric column it does not know as a fixed attribute: here the box score, the
    # ratings (own and opponent's, pre-match) and mu, at every match that may start on or after the cut
    res = H.timing_probe(lambda X: build(X), L, ["b_hat", "v_unit", "obar", "n_hist", "b_star"])
    C.write_json(OUT / "probe.json", res)
    print(json.dumps(res, indent=1))
    log("detailed probe")
    det = probe_detail(L)
    pd.DataFrame(det).to_csv(OUT / "probe_detail.csv", index=False)
    with pd.option_context("display.width", 250):
        print(pd.DataFrame(det).to_string(index=False))


def _frozen_values() -> pd.DataFrame:
    rep = json.loads((OUT / "build.json").read_text(encoding="utf-8"))
    if sha256(OUT / "values.parquet") != rep["values_sha256"]:
        raise RuntimeError("values.parquet differs from the frozen build")
    return pd.read_parquet(OUT / "values.parquet")


def step_points() -> None:
    L = long_table()
    vals = _frozen_values()
    res = points_check(L, vals)
    res.to_csv(OUT / "points_check.csv", index=False)
    with pd.option_context("display.width", 250):
        print(res.round(4).to_string(index=False))


def step_points_control() -> None:
    L = long_table()
    vals = _frozen_values()
    res = points_control(L, vals)
    res.to_csv(OUT / "points_control.csv", index=False)
    with pd.option_context("display.width", 250):
        print(res.round(4).to_string(index=False))


def step_read() -> None:
    from src.eda.serve_return_leads import readings as RD
    vals = _frozen_values()
    out = []
    cover = {}
    for t in ("atp", "wta"):
        fr = RD.seen_frame(t)
        x, info = frame_x(vals, fr)
        cover[t] = info
        r = RD.read(fr, x, "PS10", sign=+1)
        r.insert(0, "tour", t)
        out.append(r)
        log(f"read {t}")
    res = pd.concat(out, ignore_index=True)
    res.to_csv(OUT / "readings.csv", index=False)
    C.write_json(OUT / "readings_coverage.json", cover)
    with pd.option_context("display.width", 250, "display.max_rows", 200):
        print(res.round(4).to_string(index=False))


def step_read_strict() -> None:
    """The compliance re-read of the 2025-26 window: matches dated before 29 Jul 2026 whose earliest start falls on or
    after it (events of 27-28 Jul 2026) read pre-match ratings whose solve may hold box scores dated 29 Jul 2026 or
    later; their x is set to no information. No other window holds such a match."""
    from src.eda.serve_return_leads import readings as RD
    vals = _frozen_values()
    t = pd.read_parquet(TIMING, columns=["match_id", "tournament_date", "es"],
                        filters=[("tournament_date", "<", SEALED_FROM)])
    t["match_id"] = t["match_id"].astype(str)
    es = t.set_index("match_id")["es"]
    out, cnt = [], {}
    for tr in ("atp", "wta"):
        fr = RD.seen_frame(tr)
        x, _ = frame_x(vals, fr)
        late = es.reindex(fr["match_id"].astype(str)).to_numpy(float) >= day_of(SEALED_FROM)
        cnt[tr] = int(late.sum())
        x = np.where(late, np.nan, x)
        r = RD.read(fr, x, "PS10", sign=+1, windows={"2025-26": (2025, 2026)})
        r.insert(0, "tour", tr)
        out.append(r)
    res = pd.concat(out, ignore_index=True)
    res.to_csv(OUT / "readings_strict_2025_26.csv", index=False)
    C.write_json(OUT / "readings_strict_2025_26.json", {"matches_set_to_no_information": cnt})
    print(cnt)
    with pd.option_context("display.width", 250):
        print(res.round(4).to_string(index=False))


def step_implied() -> None:
    L = long_table()
    res = implied_effect(L, _frozen_values())
    C.write_json(OUT / "implied_effect.json", res)
    print(pd.DataFrame(res).round(4).to_string(index=False))


def step_summary() -> None:
    """The readings with t-based 95% intervals (t on G - 1, as `read`'s p), beside the implied benchmark: how far
    below 'calibrated in points and wholly unpriced' each reading lies (z of the shortfall)."""
    from scipy.stats import t as student_t
    r = pd.read_csv(OUT / "readings.csv")
    imp = pd.DataFrame(json.loads((OUT / "implied_effect.json").read_text(encoding="utf-8")))
    q = student_t.ppf(0.975, r["blocks"] - 1)
    r["lo95"], r["hi95"] = r["beta"] - q * r["se"], r["beta"] + q * r["se"]
    # the model's forecast exists from 2020 only: a 2013-24 reading beyond the model holds the 2020-24 rows
    r["bench_window"] = np.where((r["base"] == "L_model") & (r["window"] == "2013-24"), "2020-24", r["window"])
    r = r.merge(imp[["tour", "window", "implied_beta_per_rms"]].rename(columns={"window": "bench_window"}),
                on=["tour", "bench_window"], how="left")
    r["z_below_implied"] = (r["implied_beta_per_rms"] - r["beta"]) / r["se"]
    r["share_of_implied"] = r["beta"] / r["implied_beta_per_rms"]
    r.to_csv(OUT / "readings_summary.csv", index=False)
    cols = ["tour", "window", "form", "base", "beta", "se", "lo95", "hi95", "p_beta_positive", "n", "blocks",
            "implied_beta_per_rms", "z_below_implied"]
    with pd.option_context("display.width", 250, "display.max_rows", 200):
        print(r[cols].round(4).to_string(index=False))


def main() -> int:
    ap = argparse.ArgumentParser()
    for s in ("check", "build", "reliability", "probe", "points", "points-control", "read", "read-strict", "implied",
              "summary"):
        ap.add_argument(f"--{s}", action="store_true")
    a = ap.parse_args()
    if a.read_strict:
        step_read_strict()
    if a.points_control:
        OUT.mkdir(parents=True, exist_ok=True)
        step_points_control()
    if a.implied:
        step_implied()
    if a.summary:
        step_summary()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.check:
        step_check()
    if a.build:
        step_build()
    if a.reliability:
        step_reliability()
    if a.probe:
        step_probe()
    if a.points:
        step_points()
    if a.read:
        step_read()
    return 0


if __name__ == "__main__":
    sys.exit(main())
