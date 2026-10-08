"""Shared helpers of the STRUCTURE analyst's builders (modules f02-f09). No hypothesis lives here (HYPOTHESES is empty),
but the file is a features/f*.py module so that the batch hashes it with the builders that import it.

Result-free by construction: nothing here reads `a_won`; history is cut at the panel's last season before anything is
derived (`cut_history`), so a build for 2014-2024 never reads a 2025-2026 value, and the same code builds the final
test's columns when the panel runs to 2026.

    disc(P)                      the discovery rows (seasons 2014-2021): every centring and standardisation uses them
    mu(P, stat)                  logit of the tour x surface average of a statistic (stage4_constants.csv, 2010-2018,
                                 the same centre the surface IOS uses; Carpet has its own row)
    ios(P, kind, stat, side)     the panel's surface IOS (kind srfO, srfD, curO, curD, srfE, srfF)
    pt(P, stat, server, ret)     expit(mu + O_server - D_returner) on the match's surface (effective ratings)
    comp_serve(P, server, ret)   p = fi*fw + (1 - fi)*sw, the serve point composed from the three IOS components
    rule(P)                      each match's deciding-set rule (stage2_iid.deciding_set_rule; main draws)
    match_logit(pa, pb, bo, r)   logit P(A wins) under the iid point model (stage2_iid.match_win_by)
    leverage(m, bo, r)           beta_L(m) = d logit P / d Delta at Delta = 0, logit pA = m + Delta/2, pB = m - Delta/2
    centre_disc / std_disc       result-free centring (within cells) and scaling on the discovery rows
    signed_block(P, members)     a signed-sum block: sum of sign * member / SD_disc(member) (missing member -> 0)
    nearest(P, x, k)             the k inputs most correlated with x on discovery rows (names, correlations)
    inputs(P, names)             those inputs as an (n, k) control matrix
    clock_sum(...)               per-player (or per-key) sums over source rows released (lf + 1) by a target day,
                                 optionally decayed or windowed: the leak-proof clock for cross-player constructions
    probe_check(...)             the probe-equivalent: results of matches starting after a cut day reversed; no target
                                 starting on or before the cut may change
"""
from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage2_iid as IID  # noqa: E402  (read-only import)

HYPOTHESES: list = []                       # a library module: no hypothesis of its own

CONSTANTS = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage4_constants.csv"
SURFACE_FEATURES = ROOT / "data" / "studies" / "surface_ios" / "surface_features.parquet"
DIAG = C.OUT / "round2" / "structure"      # this analyst's result-free diagnostics
CONTEXT_IN = ("tour", "surface", "level", "indoor", "best_of", "round")
EPS = 1e-6


def lg(p) -> np.ndarray:
    return logit(np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS))


def num(P: pd.DataFrame, c: str) -> np.ndarray:
    return pd.to_numeric(P[c], errors="coerce").to_numpy(dtype=float)


def ab(P: pd.DataFrame, c: str) -> tuple[np.ndarray, np.ndarray]:
    return num(P, f"{c}_a"), num(P, f"{c}_b")


def disc(P: pd.DataFrame) -> np.ndarray:
    return P["season"].between(C.DISCOVERY[0], C.DISCOVERY[-1]).to_numpy()


def is_atp(P: pd.DataFrame) -> np.ndarray:
    return (P["tour"].astype(str) == "atp").to_numpy()


@lru_cache(maxsize=1)
def _means() -> dict:
    k = pd.read_csv(CONSTANTS)
    k = k[k["kind"].eq("surface average")]
    return {(r.stat, r.tour, r.surface): float(r.value) for r in k.itertuples(index=False)}


def mu(P: pd.DataFrame, stat: str, tour=None, surface=None) -> np.ndarray:
    """logit of the tour x surface average of `stat` (Stage 3's 2010-2018 constants); 'all' where the surface is unknown."""
    m = _means()
    tour = P["tour"].astype(str).to_numpy() if tour is None else np.asarray(tour, dtype=object)
    surf = P["surface"].astype(str).to_numpy() if surface is None else np.asarray(surface, dtype=object)
    keys = pd.Series(list(zip(tour, surf)))
    table = {k: m.get((stat, k[0], k[1]), m.get((stat, k[0], "all"), np.nan)) for k in set(keys)}
    return lg(keys.map(table).to_numpy(dtype=float))


def ios(P: pd.DataFrame, kind: str, stat: str, side: str) -> np.ndarray:
    return num(P, f"ios_{kind}_{stat}_{side}")


def pt(P: pd.DataFrame, stat: str, server: str, ret: str) -> np.ndarray:
    return expit(mu(P, stat) + ios(P, "srfO", stat, server) - ios(P, "srfD", stat, ret))


def comp_serve(P: pd.DataFrame, server: str, ret: str) -> np.ndarray:
    fi, fw, sw = pt(P, "first_in", server, ret), pt(P, "first_won", server, ret), pt(P, "second_won", server, ret)
    return fi * fw + (1 - fi) * sw


def rule(P: pd.DataFrame) -> np.ndarray:
    """Deciding-set rule per match (main draws: the model population has no qualifying)."""
    r = IID.deciding_set_rule(P["level"].astype(str), P["tournament_name"].astype(str),
                              P["season"].astype(int), pd.Series(False, index=P.index))
    return r.to_numpy(dtype=object)


def match_logit(pa, pb, bo, rules) -> np.ndarray:
    """logit P(A wins) under the iid model; NaN where a rate is missing. Rates clipped to [0.02, 0.98]."""
    pa, pb = np.asarray(pa, float), np.asarray(pb, float)
    out = np.full(len(pa), np.nan)
    ok = np.isfinite(pa) & np.isfinite(pb)
    if ok.any():
        p = IID.match_win_by(np.clip(pa[ok], 0.02, 0.98), np.clip(pb[ok], 0.02, 0.98),
                             np.where(np.asarray(bo, float)[ok] == 5, 5, 3), np.asarray(rules, dtype=object)[ok])
        out[ok] = lg(p)
    return out


def leverage(m, bo, rules, h: float = 1e-3) -> np.ndarray:
    """beta_L(m): d logit P(match) / d Delta at Delta = 0 (logit pA = m + Delta/2, logit pB = m - Delta/2); central
    difference on the logit scale (P(Delta = 0) = 1/2 exactly, so one evaluation per side)."""
    m = np.asarray(m, float)
    up = match_logit(expit(m + h / 2), expit(m - h / 2), bo, rules)
    dn = match_logit(expit(m - h / 2), expit(m + h / 2), bo, rules)
    return (up - dn) / (2 * h)


# ------------------------------------------------------------------------------------------------
# Result-free centring, scaling, blocks and controls (discovery rows only; no result involved)

def cell_keys(P: pd.DataFrame, keys=("tour", "surface")) -> np.ndarray:
    return P[list(keys)].astype(str).agg("|".join, axis=1).to_numpy()


def centre_disc(P: pd.DataFrame, s, keys=("tour", "surface")) -> np.ndarray:
    """A symmetric modulator minus its discovery-row mean within cells (tour x surface by default); a cell without
    discovery rows falls back to the tour's discovery mean."""
    s = np.asarray(s, float)
    d = disc(P) & np.isfinite(s)
    k = cell_keys(P, keys) if keys else np.full(len(P), "all")
    means = pd.Series(s[d]).groupby(k[d]).mean()
    m = pd.Series(k).map(means).to_numpy(dtype=float)
    if np.isnan(m).any() and keys and "tour" in keys:
        tm = pd.Series(s[d]).groupby(P["tour"].astype(str).to_numpy()[d]).mean()
        m = np.where(np.isnan(m), P["tour"].astype(str).map(tm).to_numpy(dtype=float), m)
    return s - m


def std_disc(P: pd.DataFrame, x) -> np.ndarray:
    x = np.asarray(x, float)
    sd = float(np.nanstd(x[disc(P)]))
    return x / sd if sd > 0 else x


def signed_block(P: pd.DataFrame, members: list[tuple[np.ndarray, str]]) -> np.ndarray:
    """The block's single column: sum over members of sign * x / SD_disc(x) (signs '+' or '-'). A member missing on a
    row contributes 0 there (no information; its missingness enters the controls); NaN only where every member is."""
    zs, any_ok = [], np.zeros(len(P), bool)
    for x, sign in members:
        z = std_disc(P, x)
        any_ok |= np.isfinite(z)
        zs.append((1.0 if sign == "+" else -1.0) * np.nan_to_num(z, nan=0.0))
    out = np.sum(zs, axis=0)
    return np.where(any_ok, out, np.nan)


def input_names(P: pd.DataFrame, numeric_only: bool = True) -> list[str]:
    names = [c[3:] for c in P.columns if c.startswith("in_")]
    return [n for n in names if not (numeric_only and n in CONTEXT_IN)]


def nearest(P: pd.DataFrame, x, k: int = 3, exclude=()) -> list[tuple[str, float]]:
    """The k numeric inputs most correlated (in absolute value) with x on discovery rows. Result-free."""
    x = np.asarray(x, float)
    out = []
    for n in input_names(P):
        if n in exclude or n.startswith("surf_season") or n.startswith("surf_layoff"):
            continue
        v = num(P, f"in_{n}")
        ok = disc(P) & np.isfinite(x) & np.isfinite(v)
        if ok.sum() < 1000 or np.std(v[ok]) == 0 or np.std(x[ok]) == 0:
            continue
        out.append((n, float(np.corrcoef(x[ok], v[ok])[0, 1])))
    out.sort(key=lambda t: -abs(t[1]))
    return [(n, round(r, 3)) for n, r in out[:k]]


def inputs(P: pd.DataFrame, names) -> np.ndarray:
    return np.column_stack([num(P, f"in_{n}") for n in names]) if len(names) else np.zeros((len(P), 0))


def miss_diff(xa, xb) -> np.ndarray:
    """miss_A - miss_B (antisymmetric missingness control)."""
    return (~np.isfinite(np.asarray(xa, float))).astype(float) - (~np.isfinite(np.asarray(xb, float))).astype(float)


def pack(cols: list[tuple[str, np.ndarray]]) -> tuple[np.ndarray | None, list[str]]:
    """(controls matrix, names) from (name, column) pairs, dropping columns that are constant on discovery rows."""
    keep = [(n, np.asarray(c, float)) for n, c in cols]
    if not keep:
        return None, []
    return np.column_stack([c for _, c in keep]), [n for n, _ in keep]


def r2_on_58(P: pd.DataFrame, x, extra: np.ndarray | None = None) -> float:
    """R-squared of x on the 58 inputs (as screen_batch: the in_ columns, NaN -> 0, no intercept), discovery rows."""
    x = np.asarray(x, float)
    Z = np.nan_to_num(P[[c for c in P.columns if c.startswith("in_")]].to_numpy(float))
    if extra is not None:
        Z = np.column_stack([Z, np.nan_to_num(np.asarray(extra, float).reshape(len(P), -1))])
    ok = disc(P) & np.isfinite(x)
    beta, *_ = np.linalg.lstsq(Z[ok], x[ok], rcond=None)
    return float(1 - np.var(x[ok] - Z[ok] @ beta) / np.var(x[ok]))


def resid_on_58(P: pd.DataFrame, x, fit_rows: np.ndarray | None = None, by_tour: bool = False) -> np.ndarray:
    """x minus its least-squares projection on the 58 inputs (plus an intercept and missing indicators), the projection
    fitted on `fit_rows` (default: seasons 2013-2018, result-free) and applied to every row; per tour when by_tour.
    Swap-consistent: refitted on the swapped panel, the remainder changes sign exactly (the regressor set is closed
    under the swap: differences negate, context stays, pairs exchange)."""
    x = np.asarray(x, float)
    X = P[[c for c in P.columns if c.startswith("in_")]].to_numpy(float)
    miss = ~np.isfinite(X)
    Z = np.column_stack([np.ones(len(P)), np.where(miss, 0.0, X), miss[:, miss.any(axis=0)].astype(float)])
    rows = P["season"].between(2013, 2018).to_numpy() if fit_rows is None else fit_rows
    groups = [P["tour"].astype(str).to_numpy() == t for t in ("atp", "wta")] if by_tour else [np.ones(len(P), bool)]
    out = np.full(len(P), np.nan)
    for g in groups:
        ok = rows & g & np.isfinite(x)
        beta, *_ = np.linalg.lstsq(Z[ok], x[ok], rcond=None)
        out[g] = x[g] - Z[g] @ beta
    return out


# ------------------------------------------------------------------------------------------------
# History, the leak-proof clock and the probe-equivalent

def cut_history(L: pd.DataFrame, P: pd.DataFrame) -> pd.DataFrame:
    """History rows up to the panel's last season (a 2024 build never reads a 2025-2026 row; a 2026 build reads to 2026)."""
    last = int(P["season"].max())
    keep = pd.to_datetime(L["tournament_date"]) < pd.Timestamp(f"{last + 1}-01-01")
    return L[keep.to_numpy()].reset_index(drop=True)


def at_model(L: pd.DataFrame, values, P: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """A per-row history value read at the model matches for side A and side B."""
    s = pd.Series(np.asarray(values, float), index=L.index)
    out = []
    for side in ("A", "B"):
        idx = L.index[L["side"].to_numpy() == side]
        m = pd.Series(s.loc[idx].to_numpy(), index=L.loc[idx, "match_id"].astype(str).to_numpy())
        m = m[~m.index.duplicated()]
        out.append(m.reindex(P["match_id"].astype(str).to_numpy()).to_numpy(dtype=float))
    return out[0], out[1]


def history_ios(L: pd.DataFrame, cols: list[str]) -> dict:
    """For every history row, the row player's ('own') and the opponent's ('opp') pre-match surface-IOS value of each
    column (e.g. 'srf_O_eff_spw'), from surface_features (pool matches: main tour, qualifying, Challengers; NaN else)."""
    need = ["match_id"] + [f"{c}_{s}" for c in cols for s in "ab"]
    sf = pd.read_parquet(SURFACE_FEATURES, columns=need)
    sf["match_id"] = sf["match_id"].astype(str)
    sf = sf.set_index("match_id")
    mid = L["match_id"].astype(str)
    is_a = (L["side"].to_numpy() == "A")
    out = {}
    for c in cols:
        va = mid.map(sf[f"{c}_a"]).to_numpy(dtype=float)
        vb = mid.map(sf[f"{c}_b"]).to_numpy(dtype=float)
        out[("own", c)] = np.where(is_a, va, vb)
        out[("opp", c)] = np.where(is_a, vb, va)
    return out


def clock_sum(src_key, src_release, vals, tgt_key, tgt_day, tau: float | None = None,
              window: float | None = None) -> np.ndarray:
    """Sum of vals over source rows with the same key and release <= target day (release = lf + 1: a result counts from
    the day after its latest possible finish; a target reads the state as of its earliest start es). Optional
    exponential decay exp(-(day - release)/tau) and window (day - release < window). Returns (n_targets, q).
    Sums accumulate within each key only, so no other key's values (not even their rounding) reach a target."""
    V = np.asarray(vals, float)
    V = V[:, None] if V.ndim == 1 else V
    V = np.nan_to_num(V)
    sk, sr = np.asarray(src_key, np.int64), np.asarray(src_release, float)
    tk, td = np.asarray(tgt_key, np.int64), np.asarray(tgt_day, float)
    BIG = 1_000_000.0
    s_comb = sk.astype(float) * BIG + sr
    o = np.argsort(s_comb, kind="stable")
    s_sorted, Vs, sk_s, sr_s = s_comb[o], V[o], sk[o], sr[o]
    if tau is not None:
        first = pd.Series(sr_s).groupby(sk_s).transform("min").to_numpy()
        expo = (sr_s - first) / tau
        if expo.max(initial=0.0) > 690:
            raise ValueError("decay exponent too large: rebase the clock")
        Vs = Vs * np.exp(expo)[:, None]
        base = pd.Series(first, index=sk_s).groupby(level=0).first()
    G = pd.DataFrame(Vs).groupby(sk_s).cumsum().to_numpy()          # inclusive cumulative sums within each key
    G = np.vstack([np.zeros((1, Vs.shape[1])), G])
    keyp = np.r_[np.int64(-1), sk_s]                                # the key of each cumulative position

    def upto(pos):                                                  # the key's sum over its first `pos` sorted rows
        return np.where((keyp[pos] == tk)[:, None], G[pos], 0.0)
    hi = np.searchsorted(s_sorted, tk.astype(float) * BIG + td, side="right")
    out = upto(hi)
    if window is not None:
        lo = np.searchsorted(s_sorted, tk.astype(float) * BIG + (td - window), side="right")
        out = out - upto(np.minimum(lo, hi))
    if tau is not None:
        bb = pd.Series(tk).map(base).to_numpy(dtype=float)
        scale = np.where(np.isfinite(bb), np.exp(-(td - np.nan_to_num(bb)) / tau), 0.0)
        out = out * scale[:, None]
    return out


def reverse_after(L: pd.DataFrame, day: float, stat_cols: list[str]) -> pd.DataFrame:
    """The probe's perturbation: every match that surely started after `day` (es > day) has its result reversed: the
    winner flag and every per-player statistic exchanged between the two players' rows; the score string stays winner-
    first, so its orientation follows. Returns a copy."""
    M = L.copy()
    later = (M["es"].to_numpy(float) > day)
    idx = np.flatnonzero(later)
    sub = M.iloc[idx][["match_id", "side"]].copy()
    sub["pos"] = idx
    a = sub[sub["side"] == "A"].set_index("match_id")["pos"]
    b = sub[sub["side"] == "B"].set_index("match_id")["pos"]
    both = a.index.intersection(b.index)
    ia, ib = a.loc[both].to_numpy(), b.loc[both].to_numpy()
    for c in stat_cols + ["won"]:
        if c not in M.columns:
            continue
        v = M[c].to_numpy().copy()
        v[ia], v[ib] = M[c].to_numpy()[ib], M[c].to_numpy()[ia]
        M[c] = v
    return M


def probe_check(build, L: pd.DataFrame, P: pd.DataFrame, stat_cols: list[str], cuts=None) -> dict:
    """Probe-equivalent for a cross-player construction. `build(L) -> (n, k) array aligned with P`. For each cut day D,
    later results are reversed; every model match with es <= D must keep its value exactly; the count of later model
    matches that moved shows the probe has power."""
    cuts = cuts or ("2016-09-07", "2019-07-10", "2021-01-27", "2023-09-06", "2024-07-10")
    base = np.asarray(build(L), float).reshape(len(P), -1)
    es = num(P, "es")
    res = {}
    for c in cuts:
        D = float((pd.Timestamp(c) - pd.Timestamp("1970-01-01")).days)
        if D > es.max():
            continue
        new = np.asarray(build(reverse_after(L, D, stat_cols)), float).reshape(len(P), -1)
        early, late = es <= D, es > D
        diff_e = np.abs(np.nan_to_num(new[early], nan=1e9) - np.nan_to_num(base[early], nan=1e9))
        moved_l = (np.abs(np.nan_to_num(new[late], nan=1e9) - np.nan_to_num(base[late], nan=1e9)) > 1e-12).any(axis=1)
        res[c] = {"earlier_rows": int(early.sum()), "earlier_max_abs_change": float(diff_e.max(initial=0.0)),
                  "later_rows": int(late.sum()), "later_rows_moved": int(moved_l.sum())}
    res["passed"] = all(v["earlier_max_abs_change"] == 0.0 for k, v in res.items() if isinstance(v, dict))
    return res


def write_diag(name: str, obj: dict) -> Path:
    DIAG.mkdir(parents=True, exist_ok=True)
    path = DIAG / f"{name}.json"
    path.write_text(json.dumps(obj, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)),
                    encoding="utf-8")
    return path


# ------------------------------------------------------------------------------------------------
# Statistic-level prechecks (box scores of earlier matches; never a match result, never a price)

def wls_clustered(X: np.ndarray, y: np.ndarray, w: np.ndarray, groups) -> tuple[np.ndarray, np.ndarray]:
    """Weighted least squares with group-clustered standard errors."""
    XtW = X.T * w
    A = np.linalg.inv(XtW @ X)
    beta = A @ (XtW @ y)
    u = X * (w * (y - X @ beta))[:, None]
    g = pd.DataFrame(u).groupby(np.asarray(groups)).sum().to_numpy()
    return beta, np.sqrt(np.diag(A @ (g.T @ g) @ A))


@lru_cache(maxsize=1)
def player_heights() -> pd.Series:
    """Each player's height (cm), the median over their Stage 0 rows (pre-rebuild copy; a fixed trait)."""
    from src.eda.feature_interactions.panel import SOURCES
    p = pd.read_parquet(SOURCES["stage0_players"], columns=["player_id", "height"])
    p["height"] = pd.to_numeric(p["height"], errors="coerce")
    return p.dropna().groupby(p["player_id"].astype(str))["height"].median()


@lru_cache(maxsize=1)
def player_hands() -> pd.Series:
    """Each player's hand ('R', 'L'; 'U' unknown -> missing), the most frequent over their Stage 0 rows (fixed trait)."""
    from src.eda.feature_interactions.panel import SOURCES
    p = pd.read_parquet(SOURCES["stage0_players"], columns=["player_id", "hand"])
    p = p[p["hand"].isin(["R", "L"])]
    return p.groupby(p["player_id"].astype(str))["hand"].agg(lambda s: s.value_counts().index[0])


def history_stat(L: pd.DataFrame, stat: str) -> tuple[np.ndarray, np.ndarray]:
    """(count, units) of a serve statistic in each history row's own box score (the row player's serve)."""
    sv, fi = num(L, "svpt"), num(L, "first_in")
    table = {"spw": (num(L, "spw_n"), num(L, "spw_d")), "ace": (num(L, "ace"), sv), "df": (num(L, "df"), sv),
             "first_in": (fi, sv), "first_won": (num(L, "first_won"), fi), "second_won": (num(L, "second_won"), sv - fi)}
    n, d = table[stat]
    ok = np.isfinite(n) & np.isfinite(d) & (d > 0) & (n >= 0) & (n <= d)
    return np.where(ok, n, np.nan), np.where(ok, d, np.nan)


def history_pair(L: pd.DataFrame, path, cols: list[str]) -> dict:
    """Like history_ios, for any match-level table with <col>_a / <col>_b columns keyed by match_id."""
    sf = pd.read_parquet(path, columns=["match_id"] + [f"{c}_{s}" for c in cols for s in "ab"])
    sf["match_id"] = sf["match_id"].astype(str)
    sf = sf.drop_duplicates("match_id").set_index("match_id")
    mid = L["match_id"].astype(str)
    is_a = (L["side"].to_numpy() == "A")
    out = {}
    for c in cols:
        va, vb = mid.map(sf[f"{c}_a"]).to_numpy(dtype=float), mid.map(sf[f"{c}_b"]).to_numpy(dtype=float)
        out[("own", c)], out[("opp", c)] = np.where(is_a, va, vb), np.where(is_a, vb, va)
    return out


def binom_ll(n, d, p) -> float:
    """Binomial log loss per unit (lower is better)."""
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    return float(-np.sum(n * np.log(p) + (d - n) * np.log(1 - p)) / np.sum(d))
