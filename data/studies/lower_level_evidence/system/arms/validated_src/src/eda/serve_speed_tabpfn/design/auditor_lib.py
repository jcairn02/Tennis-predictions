"""Design R2 (auditor): an independent, vectorised re-implementation of the pieces the R1 proposals argue about, for the
auditor's result-free checks. Reads no match result (Stage 0 with an explicit column list; no a_won, score or winner).

    panel(policy)        one row per Stage 0 (match_id, side) with a usable first-serve speed, built from the engineer's
                         per-source records (engineer_records.parquet):
                           'ks_first'  tour level and below: the ATP key statistic - 0.5 km/h (ManTennisData, else the
                                       handoff's identical copy), else a gated point mean; Slams: a gated point mean,
                                       else the key statistic - 0.5, else the AO match centre + 0.5
                           'pm_first'  a gated point mean everywhere first (the engineer's order)
                         drops: conflicting duplicate key statistics, ManTennisData rows whose round label disagrees
                         with the linked Stage 0 round (this catches the QF-labelled-as-qualifying mislinks), men < 120
                         km/h, women < 100, fewer than 10 timed first serves in
    Snapshots            as-of edition offsets (the engineer's model, re-implemented): for day D, weighted alternating
                         least squares of y = alpha_player + gamma_edition on the rows released by D (lf + 1 <= D) with
                         obs >= D - 364, each gamma shrunk to its family mean with a prior worth K player-matches;
                         an edition with nothing released takes its family mean (else 0)
    frozen_offsets       the modeller's within-player system offsets (modeller_state.offsets), frozen on <= a year
    histories            per target (player, tdate, tournament_id, round_order, es): the own earlier rows (earlier
                         tournament date, or the same tournament at an earlier round) with obs >= es - 364
    kalman_batch         the modeller's two-state robust filter, vectorised across targets (same equations: diffuse
                         level, OU fast state, innovation clipped at c predictive SDs), projected to the target day
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.design import engineer_common as EC  # noqa: E402

OUT = EC.OUT
PRIORITY = ["infosys_slams", "sirgenkii", "infosys", "slam_tracking", "slamtracker", "slam_pbp"]
S2 = {"atp": 13.49 ** 2, "wta": 10.72 ** 2}          # per-serve variance (modeller_variance.json, <= 2023)
TAU2, S_SERVE, K_PRIOR = 22.0, 12.4, 25.0            # the engineer's snapshot constants (engineer_asof.py)
MEN = {"hl": 14.0, "s2f": 12.0, "q": 4.0 / 365, "c": 2.0, "nu_pm": 7.0, "nu_ks": 8.0}
WOMEN_MENDYN = {"hl": 14.0, "s2f": 12.0, "q": 4.0 / 365, "c": 4.0, "nu_pm": 14.0, "nu_ks": 10.0}


# ------------------------------------------------------------------------------------------------ panel
def panel(policy: str = "ks_first") -> pd.DataFrame:
    r = pd.read_parquet(EC.RECORDS)
    r = r[r["linked"] & r["spd1"].notna()].copy()
    # point means: gated, the source timing the most first serves in (ties by priority)
    pts = r[r["basis"].eq("point_mean") & r["gate_half"].astype(bool)].copy()
    pts["prio"] = pts["source"].map({s: i for i, s in enumerate(PRIORITY)})
    pts = pts.sort_values(["match_id", "side", "n1", "prio"], ascending=[True, True, False, True])
    pts = pts.drop_duplicates(["match_id", "side"])
    # key statistics: conflicting duplicates and round mismatches out
    ks = r[r["basis"].eq("keystat_atp")].copy()
    spread = ks.groupby(["source", "match_id", "side"])["spd1"].agg(["size", "min", "max"])
    bad = spread[(spread["size"] > 1) & (spread["max"] - spread["min"] > 0.5)].reset_index()[["source", "match_id",
                                                                                               "side"]]
    ks = ks.merge(bad.assign(_bad=True), on=["source", "match_id", "side"], how="left")
    ks = ks[ks["_bad"].isna()].drop(columns="_bad")
    sp = pd.read_parquet(EC.SPEEDS, columns=["source", "round", "match_id", "side"])
    sp = sp[sp["source"].eq("mantennisdata") & sp["match_id"].notna()]
    s0r = EC.stage0(cols=["match_id", "round"]).rename(columns={"round": "round_s0"})
    sp = sp.merge(s0r, on="match_id", how="left")
    mism = sp[sp["round"].astype(str).str.upper() != sp["round_s0"].astype(str).str.upper()][["match_id", "side"]]
    mism = mism.drop_duplicates().assign(_mis=True)
    ks = ks.merge(mism, on=["match_id", "side"], how="left")
    ks = ks[~(ks["source"].eq("mantennisdata") & ks["_mis"].eq(True))].drop(columns="_mis")
    ks["prio"] = ks["source"].map({"mantennisdata": 0, "handoff_ks": 1})
    ks = ks.sort_values(["match_id", "side", "prio"]).drop_duplicates(["match_id", "side"])
    mc = r[r["basis"].eq("mc_rounded")].copy()
    mcs = mc.groupby(["match_id", "side"])["spd1"].agg(["size", "min", "max"])
    mc_bad = mcs[(mcs["size"] > 1) & (mcs["max"] - mcs["min"] > 0.5)].index
    mc = mc[~mc.set_index(["match_id", "side"]).index.isin(mc_bad)].drop_duplicates(["match_id", "side"])
    keys = EC.stage0(cols=["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "surface",
                           "tournament_id", "tournament_name", "tournament_date", "player_a_id", "player_b_id"])
    lev = keys.set_index("match_id")["level"]
    cand = []
    for tier_name, t, shift, basis in (("pts", pts, 0.0, "pts"), ("ks", ks, -0.5, "ks"), ("mc", mc, 0.5, "pts")):
        x = t[["match_id", "side", "source", "spd1", "n1"]].copy()
        x["y"] = x["spd1"] + shift
        x["basis"] = basis
        x["tier"] = tier_name
        cand.append(x)
    c = pd.concat(cand, ignore_index=True)
    slam = c["match_id"].map(lev).eq("GS").to_numpy()
    if policy == "ks_first":
        order = np.where(slam, c["tier"].map({"pts": 0, "ks": 1, "mc": 2}), c["tier"].map({"ks": 0, "pts": 1, "mc": 2}))
    else:
        order = c["tier"].map({"pts": 0, "ks": 1, "mc": 2}).to_numpy()
    c["order"] = order
    c = c.sort_values(["match_id", "side", "order"]).drop_duplicates(["match_id", "side"])
    p = c.merge(keys, on="match_id", how="inner")
    p["player_id"] = np.where(p["side"].eq("A"), p["player_a_id"], p["player_b_id"])
    p = p.drop(columns=["player_a_id", "player_b_id", "spd1", "order"])
    p = p.rename(columns={"n1": "n"})
    tm = pd.read_parquet(EC.TIMING, columns=["match_id", "es", "lf", "obs"])
    p = p.merge(tm, on="match_id", how="left")
    p = p[p["es"].notna() & p["n"].ge(10)]
    p = p[~((p["tour"].eq("atp") & (p["y"] < 120)) | (p["tour"].eq("wta") & (p["y"] < 100)))]
    p["tdate"] = p["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    p["slam"] = EC.slam_of(p["level"], p["tournament_name"]).to_numpy()
    p["draw"] = np.where(p["qualifying"].astype(bool), "Q", "M")
    p["edition"] = p["tournament_id"].astype(str) + "|" + p["draw"] + "|" + p["basis"]
    p["fam"] = np.where(p["slam"].ne(""), p["slam"], "tour") + "_" + p["draw"]
    # the modeller's measuring systems: the Slam family (draws together), else basis x (Challenger | tour)
    bname = np.where(p["basis"].eq("ks"), "ks", "pm")
    p["system"] = np.where(p["slam"].ne(""), p["slam"],
                           np.where(p["level"].eq("CH"), np.char.add(bname.astype(str), "_ch"),
                                    np.char.add(bname.astype(str), "_tour")))
    p = p.sort_values(["tour", "player_id", "tdate", "tournament_id", "round_order"], kind="mergesort")
    return p.reset_index(drop=True)


# ------------------------------------------------------------------------------------------------ offsets
class Snapshots:
    """As-of edition offsets of one tour (see the module docstring)."""

    def __init__(self, p: pd.DataFrame, tau2: float = TAU2, s: float = S_SERVE, k_prior: float = K_PRIOR):
        self.rel = (p["lf"].to_numpy(float) + 1.0)
        self.obs = p["obs"].to_numpy(float)
        self.y = p["y"].to_numpy(float)
        self.w = 1.0 / (tau2 + s * s / p["n"].clip(lower=1).to_numpy(float))
        self.pid = pd.factorize(p["player_id"])[0]
        self.ed, self.ed_u = pd.factorize(p["edition"])
        fam_of = p.drop_duplicates("edition").set_index("edition")["fam"]
        self.fam_of_ed = fam_of.reindex(self.ed_u).to_numpy()
        self.fam_idx, self.fam_u = pd.factorize(self.fam_of_ed)
        self.k_prior = k_prior
        self.cache: dict[float, np.ndarray] = {}

    def at(self, day: float, iters: int = 60) -> np.ndarray:
        """gamma(day) for every edition of the tour, fallbacks applied (family mean at day, else 0)."""
        if day in self.cache:
            return self.cache[day]
        m = (self.rel <= day) & (self.obs >= day - 364.0)
        g_all = np.full(len(self.ed_u), np.nan)
        if m.sum() >= 50:
            y, w, pc, ec = self.y[m], self.w[m], self.pid[m], self.ed[m]
            _, pi = np.unique(pc, return_inverse=True)
            eu, ei = np.unique(ec, return_inverse=True)
            fi_ed = self.fam_idx[eu]
            fu, fi = np.unique(fi_ed, return_inverse=True)
            wp = np.bincount(pi, weights=w)
            we = np.bincount(ei, weights=w)
            g = np.zeros(len(eu))
            kw = self.k_prior * float(np.mean(w))
            for _ in range(iters):
                a = np.bincount(pi, weights=w * (y - g[ei])) / wp
                r = np.bincount(ei, weights=w * (y - a[pi]))
                fm = np.bincount(fi, weights=r) / np.maximum(np.bincount(fi, weights=we), 1e-12)
                g_new = (r + kw * fm[fi]) / (we + kw)
                done = np.max(np.abs(g_new - g)) < 1e-6
                g = g_new
                if done:
                    break
            g_all[eu] = g
            fmean = pd.Series(g).groupby(fi_ed).mean()
            miss = np.isnan(g_all)
            fill = pd.Series(self.fam_idx[miss]).map(fmean).to_numpy(float)
            g_all[miss] = np.nan_to_num(fill, nan=0.0)
        else:
            g_all[:] = 0.0
        self.cache[day] = g_all
        return g_all


def frozen_offsets(p: pd.DataFrame, last_year: int) -> dict:
    """The modeller's offsets (modeller_state.offsets) on this panel: {tour: {system: offset}}."""
    from src.eda.serve_speed_tabpfn.design import modeller_state as MS
    return MS.offsets(p, last_year)


# ------------------------------------------------------------------------------------------------ histories
def histories(p: pd.DataFrame, targets: pd.DataFrame, window: float = 364.0, hmax: int = 250) -> dict:
    """Padded own-history index arrays. targets: tour, player_id, tdate, tournament_id, round_order, es (and any
    other columns). Returns {'idx': (n_t, H) panel row indices or -1, 'k14': rows within 14 days of es, 'last_age':
    es - obs of the latest row, 'same_event': the latest row is at the target's tournament}."""
    groups = {k: g.index.to_numpy() for k, g in p.groupby(["tour", "player_id"], sort=False)}
    td_all, tid_all = p["tdate"].to_numpy(), p["tournament_id"].to_numpy()
    ro_all, ob_all = p["round_order"].to_numpy(), p["obs"].to_numpy(float)
    n = len(targets)
    lists = [None] * n
    k14 = np.zeros(n, int)
    last_age = np.full(n, np.nan)
    same_ev = np.zeros(n, bool)
    t = targets.reset_index(drop=True)
    for (tour, pid), tg in t.groupby(["tour", "player_id"], sort=False):
        ix = groups.get((tour, pid))
        if ix is None:
            for i in tg.index:
                lists[i] = np.empty(0, int)
            continue
        td, tid, ro, ob = td_all[ix], tid_all[ix], ro_all[ix], ob_all[ix]
        for i, ttd, ttid, tro, tes in zip(tg.index, tg["tdate"].to_numpy(), tg["tournament_id"].to_numpy(),
                                          tg["round_order"].to_numpy(), tg["es"].to_numpy(float)):
            earlier = (td < ttd) | ((tid == ttid) & (ro < tro))
            keep = earlier & (ob >= tes - window)
            sel = ix[keep]
            if len(sel) > hmax:
                sel = sel[-hmax:]
            lists[i] = sel
            if len(sel):
                k14[i] = int((ob[keep] >= tes - 14).sum())
                last_age[i] = tes - ob[keep].max()
                same_ev[i] = bool((tid[keep] == ttid).any())
    H = max(1, max(len(x) for x in lists))
    idx = np.full((n, H), -1, int)
    for i, x in enumerate(lists):
        if len(x):
            idx[i, :len(x)] = x
    return {"idx": idx, "k14": k14, "last_age": last_age, "same_event": same_ev}


def centred_values(p: pd.DataFrame, targets: pd.DataFrame, hist: dict, scheme: str, frozen: dict | None = None,
                   snaps: dict | None = None) -> np.ndarray:
    """Z (n_t, H): the history rows' centred speeds for each target under a scheme:
        'raw'     y
        'frozen'  y - o_system (the modeller's frozen offsets)
        'asof'    y - gamma_edition(es_target) (the snapshot of the target's own earliest start)"""
    idx = hist["idx"]
    ok = idx >= 0
    y = p["y"].to_numpy(float)
    Z = np.where(ok, y[np.maximum(idx, 0)], np.nan)
    if scheme == "raw":
        return Z
    if scheme == "frozen":
        o = np.array([frozen.get(t, {}).get(s, 0.0) for t, s in zip(p["tour"], p["system"])], float)
        return np.where(ok, Z - o[np.maximum(idx, 0)], np.nan)
    if scheme == "asof":
        out = np.full(Z.shape, np.nan)
        ed_code = {}
        for tour, s in snaps.items():
            ed_code[tour] = pd.Index(s.ed_u)
        ed_idx = np.full(len(p), -1, int)
        for tour in snaps:
            mm = (p["tour"] == tour).to_numpy()
            ed_idx[mm] = ed_code[tour].get_indexer(p.loc[mm, "edition"])
        t = targets.reset_index(drop=True)
        for (tour, day), g in t.groupby(["tour", "es"], sort=False):
            gam = snaps[tour].at(float(day))
            rows = g.index.to_numpy()
            ii = idx[rows]
            okk = ii >= 0
            e = ed_idx[np.maximum(ii, 0)]
            out[rows] = np.where(okk, Z[rows] - gam[np.maximum(e, 0)], np.nan)
        return out
    raise ValueError(scheme)


# ------------------------------------------------------------------------------------------------ the filter
def noise(p: pd.DataFrame, hist: dict, prm: dict) -> np.ndarray:
    idx = hist["idx"]
    ok = idx >= 0
    n = p["n"].to_numpy(float)
    nu = np.where(p["basis"].eq("ks").to_numpy(), prm["nu_ks"], prm["nu_pm"])
    s2 = p["tour"].map(S2).to_numpy(float)
    r = nu + s2 / n
    return np.where(ok, r[np.maximum(idx, 0)], np.nan)


def kalman_batch(Z: np.ndarray, R: np.ndarray, DAY: np.ndarray, target_day: np.ndarray, prm: dict) -> dict:
    """The modeller's filter (modeller_state.kalman) on padded histories, all targets at once. Rows of Z are in own
    order; NaN = no row. Returns f_hat, f_sd, L_hat (NaN without history), L_sd, n (history rows)."""
    nt, H = Z.shape
    lam = math.log(2) / prm["hl"]
    s2f, q, c = prm["s2f"], prm["q"], prm["c"]
    big = 1e6
    L = np.zeros(nt); f = np.zeros(nt)
    P11 = np.full(nt, big); P12 = np.zeros(nt); P22 = np.full(nt, s2f)
    d0 = np.full(nt, np.nan)
    for k in range(H):
        a = np.isfinite(Z[:, k])
        if not a.any():
            continue
        first = a & np.isnan(d0)
        dt = np.where(first, 0.0, np.maximum(DAY[:, k] - np.nan_to_num(d0), 0.0))
        ph = np.exp(-lam * dt)
        # predict (active rows only)
        f_p = np.where(a, f * ph, f)
        P11_p = np.where(a, P11 + q * dt, P11)
        P12_p = np.where(a, P12 * ph, P12)
        P22_p = np.where(a, P22 * ph * ph + s2f * (1 - ph * ph), P22)
        z = np.where(a, Z[:, k], 0.0)
        Rk = np.where(a, R[:, k], 1.0)
        v = z - L - f_p
        S = P11_p + 2 * P12_p + P22_p + Rk
        sd = np.sqrt(S)
        v = np.clip(v, -c * sd, c * sd)
        K1, K2 = (P11_p + P12_p) / S, (P12_p + P22_p) / S
        L = np.where(a, L + K1 * v, L)
        f = np.where(a, f_p + K2 * v, f)
        P11 = np.where(a, P11_p - K1 * K1 * S, P11)
        P12 = np.where(a, P12_p - K1 * K2 * S, P12)
        P22 = np.where(a, P22_p - K2 * K2 * S, P22)
        d0 = np.where(a, DAY[:, k], d0)
    has = np.isfinite(d0)
    dt = np.where(has, np.maximum(target_day - np.nan_to_num(d0), 0.0), 0.0)
    ph = np.exp(-lam * dt)
    f_t = np.where(has, f * ph, 0.0)
    P22_t = np.where(has, P22 * ph * ph + s2f * (1 - ph * ph), s2f)
    P11_t = np.where(has, P11 + q * dt, np.nan)
    nh = np.isfinite(Z).sum(axis=1)
    return {"f_hat": f_t, "f_sd": np.sqrt(np.maximum(P22_t, 0)), "L_hat": np.where(has, L, np.nan),
            "L_sd": np.sqrt(np.maximum(P11_t, 0)), "n": nh}


def window_means(Z: np.ndarray, hist: dict, p: pd.DataFrame, target_day: np.ndarray) -> dict:
    """n-weighted 364-day mean (c52) and 14-day mean (c14) of the centred history (the registered x's windows)."""
    idx = hist["idx"]
    ok = idx >= 0
    n = np.where(ok, p["n"].to_numpy(float)[np.maximum(idx, 0)], 0.0)
    day = np.where(ok, p["obs"].to_numpy(float)[np.maximum(idx, 0)], np.nan)
    zz = np.nan_to_num(Z)
    w52 = n * ok
    c52 = (w52 * zz).sum(1) / np.where(w52.sum(1) > 0, w52.sum(1), np.nan)
    in14 = ok & (day >= (target_day[:, None] - 14))
    w14 = n * in14
    c14 = (w14 * zz).sum(1) / np.where(w14.sum(1) > 0, w14.sum(1), np.nan)
    return {"c52": c52, "c14": c14, "x": c14 - c52}


def days_matrix(p: pd.DataFrame, hist: dict) -> np.ndarray:
    idx = hist["idx"]
    return np.where(idx >= 0, p["obs"].to_numpy(float)[np.maximum(idx, 0)], np.nan)
