"""Family 11, the body analyst's rows of the final family (round2/hypothesis_family.md): I-053 (age x recovery debt),
B-LOAD (I-052's fitness-fatigue kernel with I-051's off-site part) and B-PREV (BOD-L1's previous-match set excess with
I-056's rest contrast). Also the shared per-player history machinery that f21-f28 import (load kernel, rest, walk-
forward field tables, reading a history value at the model matches). Builders read NO results of the model matches
and no season after the panel's last (builders.md); a player's own earlier matches are pre-match facts.

Shared definitions (constants fixed in advance, none tuned on outcomes, the price or the current best):

    t           the match clock's best-estimate day along the player's own order, as its running maximum
                (history.long_table's obs_mono: non-decreasing within a player)
    history     history.long_table() cut before 20 Dec of the panel's last season (an event dated from 20 Dec belongs to
                the next season), so no later season is ever read; one row per (match, player), the player's own order
    load L_j    minutes of earlier played match j when 1 <= minutes <= 700 (Isner-Mahut was 665); else points played
                (tpw_d) x minutes per point; else games x minutes per game; walkovers 0 (BOD-02's definition). The two
                pace constants are FIELD statistics, so they are walk-forward on the clock: for tournament year Y, the
                ratio over the trailing three years' matches with lf + 1 <= T_Y (T_Y = 20 Dec of Y - 1, or the year's
                first es if earlier), per tour x surface, falling back to tour, then both tours x surface, then both tours
                (>= 300 matches each), then a prior of 0.625 min/point and 4.4 min/game (BOD-02's arithmetic: 165 points,
                22.5 games, 103 minutes in an even best of 3; only 2010 rows use it). Women have no minutes before 2016
                and ITF matches none at all, so those loads are imputed; `imp` marks them
    Fat_X(tau)  log(1 + sum_j L_j exp(-(t - t_j)/tau)) over X's STRICTLY earlier played matches at every level;
                tau2 = 3 days fixed in advance (math audit, cross-cutting finding 2; the grid 1.5/5 and Fit's 21 days are
                sensitivities in round2/builds/body.md, not hypotheses)
    imp share   the imputed loads' share of the kernel sum (0 without load); the minutes-imputed indicator of the
                math audit's I-052 card: miss_A - miss_B is a control, 1[either share > 0.5] x eta an eta-modulator control
    rest        t - t of X's previous played match (days, best estimate)

Hypotheses (block members are standardised on 2014-2021, multiplied by their declared sign and summed, so a block row
carries sign + for its oriented sum, the convention of every block module; the family table writes the members' sign)
    I-053   x = Fat_A a_A - Fat_B a_B, a = (age - 26)+ (single coefficient, sign -, weight 1, slow). Controls: dFat,
            age, age_sq, sets_14d, the imputed-share difference, the nearest inputs; eta-mod: sum Fat, sum a (centred on
            2014-2021), 1[imputed].
    B-LOAD  members dFat (-) and dOff (-), Off = log(1 + the decayed load of earlier matches not at this event): Fat
            minus its on-site part (the round-2 rebuttal BOD-R1, accepted). Weight 1. Controls: sets_14d,
            surf_layoff_a - surf_layoff_b, the imputed-share difference, the nearest inputs; eta-mod: 1[imputed].
    B-PREV  members dPrevX (-) and d[PrevX (1[rest <= 1] - 1[rest >= 2])] (-); PrevX = (sets of X's previous played
            match - the format's minimum) / (maximum - minimum) when that match was at this event and <= 3 days
            before, else 0, missing when it ended in a retirement (BOD-L1; equal to I-056's Scare in best of three).
            Weight 1. Controls: sets_14d, dFat, d min(rest, 7), the PrevX-missing difference, the nearest inputs;
            the batch adds 1[x missing] x eta (S11). I-056's other Scare definitions are sensitivities, not built.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.eda.feature_interactions import common as C

TAU_FAT = 3.0                     # days, I-052's tau2 (fixed in advance)
AGE_KNEE_53 = 26.0                # I-053: (age - 26)+ (originator's simpler form)
MIN_VALID = (1.0, 700.0)          # plausible minutes of a played match
PRIOR_MPP, PRIOR_MPG = 0.625, 4.4  # minutes per point / per game before any walk-forward data exists (2010 only)
PACE_YEARS, PACE_MIN_N = 3, 300   # trailing years and minimum matches of a pace cell
REST_SHORT = 1.5                  # I-056: rest < 1.5 days is "one day or less"
DAY0 = pd.Timestamp("1970-01-01")
_CACHE: dict = {}


# ------------------------------------------------------------------------------------------------
# history machinery (shared with f21-f27)

def season_cut(P: pd.DataFrame) -> pd.Timestamp:
    """Rows dated from 20 Dec of the panel's last season belong to the next season and are never read."""
    return pd.Timestamp(f"{int(P['season'].max())}-12-20")


def history(P: pd.DataFrame, L: pd.DataFrame) -> pd.DataFrame:
    """L cut at the panel's season end, with per-row derived columns (cached per L object and last season)."""
    key = (id(L), int(P["season"].max()))
    if key in _CACHE:
        return _CACHE[key][1]
    H = L[pd.to_datetime(L["tournament_date"]) < season_cut(P)].reset_index(drop=True).copy()
    H["pid"] = pd.factorize(H["player_id"])[0]
    # the player's clock: the running maximum of the best-estimate day along his own order (history.py's obs_mono since
    # its 22:00 correction: an event is placed by its earliest day and its rounds keep their order), so every decay
    # and window below sees non-decreasing days
    obs = H["obs_mono"] if "obs_mono" in H.columns else H.groupby("player_id")["obs"].cummax()
    H["t"] = obs.astype(float).to_numpy()
    H["tyear"] = pd.to_datetime(H["tournament_date"]).dt.year.astype(int)
    late = pd.to_datetime(H["tournament_date"]) >= pd.to_datetime(H["tyear"].astype(str) + "-12-20")
    H.loc[late, "tyear"] += 1                                        # late-December events open the next season
    H["played"] = H["played"].astype(bool)
    _loads(H)
    _rest(H)
    _CACHE.clear()                                                   # one history at a time (memory)
    _CACHE[key] = (L, H)
    return H


def clear_cache() -> None:
    _CACHE.clear()


def season_T(H: pd.DataFrame) -> dict:
    """T_Y: the day before which a result must have finished (lf + 1 <= T_Y) to enter year Y's field tables."""
    first = H.groupby("tyear")["es"].min()
    return {int(y): min(float(first.get(y, np.inf)), float((pd.Timestamp(f"{y - 1}-12-20") - DAY0).days))
            for y in range(int(H["tyear"].min()), int(H["tyear"].max()) + 1)}


def walk_forward_ratio(H: pd.DataFrame, num: np.ndarray, den: np.ndarray, ok: np.ndarray, levels: list,
                       years: int, min_n: int, prior: float) -> np.ndarray:
    """Per row, sum(num)/sum(den) over rows with ok and lf + 1 <= T_Y of the row's tournament year Y and tyear in
    [Y - years, Y - 1]; `levels` are cell keys from finest to coarsest (each a list of column names, [] = all), the
    first cell with >= min_n contributing rows wins, else `prior`. Each match counts once per player row (ratios)."""
    T = season_T(H)
    out = np.full(len(H), np.nan)
    lf, ty = H["lf"].to_numpy(float), H["tyear"].to_numpy()
    for y in sorted(T):
        rows = ty == y
        if not rows.any():
            continue
        src = ok & (lf + 1 <= T[y]) & (ty >= y - years) & (ty <= y - 1)
        val = np.full(int(rows.sum()), np.nan)
        for keys in levels:
            if src.sum() == 0:
                break
            if keys:
                g = pd.DataFrame({k: H.loc[src, k].astype(str).to_numpy() for k in keys})
                g["num"], g["den"] = num[src], den[src]
                agg = g.groupby(keys).agg(num=("num", "sum"), den=("den", "sum"), n=("num", "size"))
                agg = agg[(agg["n"] >= 2 * min_n) & (agg["den"] > 0)]          # two rows per match
                ratio = (agg["num"] / agg["den"])
                q = pd.MultiIndex.from_frame(pd.DataFrame({k: H.loc[rows, k].astype(str).to_numpy() for k in keys})) \
                    if len(keys) > 1 else pd.Index(H.loc[rows, keys[0]].astype(str).to_numpy())
                r = ratio.reindex(q).to_numpy(float)
            else:
                n = int(src.sum())
                r = np.full(int(rows.sum()), num[src].sum() / den[src].sum() if n >= 2 * min_n else np.nan)
            val = np.where(np.isfinite(val), val, r)
        out[rows] = np.where(np.isfinite(val), val, prior)
    return out


def _loads(H: pd.DataFrame) -> None:
    """H["load"] (minutes-equivalent of each played match; 0 for a walkover), H["imp"] (1 where imputed),
    H["mpp"], H["mpg"] (the walk-forward pace constants of the row's tour x surface and year)."""
    played = H["played"].to_numpy(bool)
    mins = H["minutes"].to_numpy(float)
    pts = H["tpw_d"].to_numpy(float)
    games = H["games"].to_numpy(float)
    valid = played & np.isfinite(mins) & (mins >= MIN_VALID[0]) & (mins <= MIN_VALID[1])
    levels = [["tour", "surface"], ["tour"], ["surface"], []]
    okp = valid & np.isfinite(pts) & (pts > 0)
    okg = valid & np.isfinite(games) & (games > 0)
    H["mpp"] = walk_forward_ratio(H, np.where(okp, mins, 0.0), np.where(okp, pts, 0.0), okp, levels, PACE_YEARS,
                                  PACE_MIN_N, PRIOR_MPP)
    H["mpg"] = walk_forward_ratio(H, np.where(okg, mins, 0.0), np.where(okg, games, 0.0), okg, levels, PACE_YEARS,
                                  PACE_MIN_N, PRIOR_MPG)
    bo = pd.to_numeric(H["best_of"], errors="coerce").to_numpy(float)
    default_games = np.where(bo == 5, 35.0, 22.5)                    # score unparseable: a typical match
    by_pts = np.isfinite(pts) & (pts > 0)
    by_games = np.isfinite(games) & (games > 0)
    imputed = np.where(by_pts, pts * H["mpp"].to_numpy(), np.where(by_games, games, default_games) * H["mpg"].to_numpy())
    load = np.where(valid, mins, imputed)
    H["load"] = np.where(played, load, 0.0)
    H["imp"] = (played & ~valid).astype(float)


def decayed_sum(pid: np.ndarray, t: np.ndarray, v: np.ndarray, tau: float) -> np.ndarray:
    """sum over the same player's STRICTLY earlier rows j of v_j exp(-(t_i - t_j)/tau) (rows in own order)."""
    pid_l, t_l = pid.tolist(), t.tolist()
    v_l = np.nan_to_num(np.asarray(v, float)).tolist()
    out = [0.0] * len(pid_l)
    acc, prev_p, prev_t, prev_v = 0.0, -1, 0.0, 0.0
    exp = math.exp
    for i in range(len(pid_l)):
        p, ti = pid_l[i], t_l[i]
        if p != prev_p:
            acc = 0.0
        else:
            acc = (acc + prev_v) * exp(-(ti - prev_t) / tau)
        out[i] = acc
        prev_p, prev_t, prev_v = p, ti, v_l[i]
    return np.asarray(out)


def fat(H: pd.DataFrame, tau: float = TAU_FAT, unit: str = "load") -> tuple[np.ndarray, np.ndarray]:
    """(Fat = log1p of the decayed load, the imputed share of that load) per history row; cached on H."""
    key = f"_fat_{unit}_{tau:g}"
    if key not in H.columns:
        pid, t = H["pid"].to_numpy(), H["t"].to_numpy(float)
        v = H[unit].to_numpy(float) if unit != "games" else np.where(H["played"], H["games"].fillna(0.0), 0.0)
        s = decayed_sum(pid, t, v, tau)
        si = decayed_sum(pid, t, v * H["imp"].to_numpy(float), tau)
        H[key] = np.log1p(s)
        H[key + "_imp"] = np.where(s > 1e-9, si / np.maximum(s, 1e-12), 0.0)
    return H[key].to_numpy(float), H[key + "_imp"].to_numpy(float)


def _rest(H: pd.DataFrame) -> None:
    """H["rest"]: days since the player's previous PLAYED match; H["prev_k"]: that row's position (-1 if none)."""
    played = H["played"].to_numpy(bool)
    pid = H["pid"].to_numpy()
    idx = pd.Series(np.where(played, np.arange(len(H)), np.nan))
    upto = idx.groupby(pid).ffill()                                  # the last played row at or before this row
    prev = upto.groupby(pid).shift(1).to_numpy()                     # ... strictly before it
    H["prev_k"] = np.where(np.isfinite(prev), prev, -1).astype(int)
    t = H["t"].to_numpy(float)
    H["rest"] = np.where(H["prev_k"] >= 0, t - t[np.maximum(H["prev_k"].to_numpy(), 0)], np.nan)


def positions(P: pd.DataFrame, H: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Row positions in H of side A's and side B's row of every panel match (-1 where absent); cached on H."""
    if "_posA" not in H.attrs:
        ids = P["match_id"].astype(str).to_numpy()
        out = []
        for side in ("A", "B"):
            m = (H["side"] == side).to_numpy()
            s = pd.Series(np.flatnonzero(m), index=H["match_id"].astype(str).to_numpy()[m])
            s = s[~s.index.duplicated()]
            out.append(s.reindex(ids).fillna(-1).to_numpy(int))
        H.attrs["_posA"], H.attrs["_posB"], H.attrs["_ids"] = out[0], out[1], ids
    if not np.array_equal(H.attrs["_ids"], P["match_id"].astype(str).to_numpy()):
        H.attrs.pop("_posA")
        return positions(P, H)
    return H.attrs["_posA"], H.attrs["_posB"]


def at_model(P: pd.DataFrame, H: pd.DataFrame, values) -> tuple[np.ndarray, np.ndarray]:
    """A per-history-row value (pre-match by construction) read at the panel's matches for side A and side B."""
    v = np.asarray(values, float)
    pa, pb = positions(P, H)
    return (np.where(pa >= 0, v[np.maximum(pa, 0)], np.nan), np.where(pb >= 0, v[np.maximum(pb, 0)], np.nan))


# ------------------------------------------------------------------------------------------------
# result-free combination helpers (shared with f21-f27): only panel columns, so the swap test can run on them

def disc(P: pd.DataFrame) -> np.ndarray:
    return P["season"].between(C.DISCOVERY[0], C.DISCOVERY[-1]).to_numpy()


def col(P: pd.DataFrame, name: str) -> np.ndarray:
    return pd.to_numeric(P[name], errors="coerce").to_numpy(float)


def ab(P: pd.DataFrame, name: str) -> tuple[np.ndarray, np.ndarray]:
    return col(P, f"{name}_a"), col(P, f"{name}_b")


def centre(P: pd.DataFrame, s: np.ndarray) -> np.ndarray:
    """A symmetric modulator centred on its 2014-2021 mean (no results involved)."""
    s = np.asarray(s, float)
    return s - np.nanmean(s[disc(P)])


def standardise(P: pd.DataFrame, x: np.ndarray, q: float = 0.99) -> np.ndarray:
    """An antisymmetric member clipped at the 99th percentile of |x| and divided by its SD, both on 2014-2021 rows (the
    screen's own preprocessing of a single column; never centred)."""
    x = np.asarray(x, float)
    d = disc(P) & np.isfinite(x)
    if not d.any():
        return x
    clip = float(np.quantile(np.abs(x[d]), q)) or 1.0
    xc = np.clip(x, -clip, clip)
    sd = float(np.std(xc[d])) or 1.0
    return xc / sd


def diff_inputs() -> list[str]:
    from src.eda.feature_interactions.arms import base_inputs
    names, kinds, _ = base_inputs()
    return [n for n in names if kinds[n] == "diff" and n != "odds_logit"]


def nearest(P: pd.DataFrame, x: np.ndarray, exclude=(), k: int = 3, thr: float = 0.10) -> list[str]:
    """The one to three existing difference inputs most correlated with x (|r| on 2014-2021 rows; result-free): every
    input with |r| >= thr up to k, at least the first. The price is never one (it is the base)."""
    X = np.asarray(x, float).reshape(len(P), -1)          # a Wald block: the largest |r| over its columns
    r = {}
    for n in diff_inputs():
        if n in exclude:
            continue
        v = col(P, f"in_{n}")
        for j in range(X.shape[1]):
            m = disc(P) & np.isfinite(X[:, j]) & np.isfinite(v)
            if m.sum() > 100 and np.std(v[m]) > 0 and np.std(X[m, j]) > 0:
                r[n] = max(r.get(n, 0.0), abs(float(np.corrcoef(X[m, j], v[m])[0, 1])))
    top = sorted(r, key=lambda n: -r[n])
    return [n for i, n in enumerate(top[:k]) if i == 0 or r[n] >= thr]


def controls(P: pd.DataFrame, named: dict, x, near_fixed: list | None = None, exclude=()) -> tuple[np.ndarray, list]:
    """Antisymmetric controls: the hypothesis's marginality set (named), then the nearest inputs (fixed list if given)."""
    cols, names = list(named.values()), list(named)
    near = near_fixed if near_fixed is not None else nearest(P, x, exclude=set(exclude) | {n[3:] for n in named
                                                                                        if n.startswith("in_")})
    for n in near:
        if f"in_{n}" not in names:
            cols.append(col(P, f"in_{n}"))
            names.append(f"in_{n}")
    return np.column_stack([np.asarray(c, float) for c in cols]), names


def block(P: pd.DataFrame, members: list) -> np.ndarray:
    """A signed-sum block: each (member, sign) standardised on 2014-2021 rows and multiplied by its sign, summed with a
    missing member counting 0 (its missingness enters the controls); NaN only where every member is missing."""
    Z = np.column_stack([sgn * standardise(P, np.asarray(m, float)) for m, sgn in members])
    x = np.nansum(Z, axis=1)
    x[~np.isfinite(Z).any(axis=1)] = np.nan
    return x


def sym_miss(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """The symmetric missing indicator (either side missing), centred on 2014-2021: an eta-modulator control."""
    return (~np.isfinite(a) | ~np.isfinite(b)).astype(float)


def miss_diff(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return (~np.isfinite(a)).astype(float) - (~np.isfinite(b)).astype(float)

# ------------------------------------------------------------------------------------------------
# B-LOAD, I-053, B-PREV (the final family, round2/hypothesis_family.md)

def segments(H: pd.DataFrame) -> np.ndarray:
    """Event segment per row: consecutive rows of a player with the same tournament id (qualifying included)."""
    if "_segid" not in H.columns:
        pid = H["pid"].to_numpy()
        tid = H["tournament_id"].astype(str).to_numpy()
        new = np.r_[True, (pid[1:] != pid[:-1]) | (tid[1:] != tid[:-1])]
        H["_segid"] = np.cumsum(new) - 1
    return H["_segid"].to_numpy()


def off_site(H: pd.DataFrame, tau: float = TAU_FAT) -> np.ndarray:
    """Off = log(1 + the decayed load of strictly earlier matches NOT at this event): Fat minus its on-site part
    (BOD-01's Off with the kernel of I-052, as the round-2 rebuttal computed it); cached on H."""
    key = f"_off_{tau:g}"
    if key not in H.columns:
        t, v = H["t"].to_numpy(float), H["load"].to_numpy(float)
        s_all = decayed_sum(H["pid"].to_numpy(), t, v, tau)
        s_on = decayed_sum(segments(H), t, v, tau)                 # resets at every new event segment
        H[key] = np.log1p(np.maximum(s_all - s_on, 0.0))
    return H[key].to_numpy(float)


def prev_x(H: pd.DataFrame) -> np.ndarray:
    """BOD-L1's PrevX: the previous played match's set excess (sets - the format's minimum) / (maximum - minimum) if
    it was at this event and at most 3 days before; 0 otherwise; missing if it ended in a retirement or has no score."""
    if "_prevx" not in H.columns:
        k = H["prev_k"].to_numpy()
        kk = np.maximum(k, 0)
        sets = H["sets"].to_numpy(float)[kk]
        bo = pd.to_numeric(H["best_of"], errors="coerce").to_numpy(float)[kk]
        lo = (bo + 1) / 2
        grade = np.clip((sets - lo) / (bo - lo), 0.0, 1.0)
        tid = H["tournament_id"].astype(str).to_numpy()
        near = (k >= 0) & (tid[kk] == tid) & (H["rest"].to_numpy(float) <= 3)
        retired = H["status"].astype(str).to_numpy()[kk] == "retired"
        H["_prevx"] = np.where(near, np.where(retired | ~np.isfinite(grade), np.nan, grade), 0.0)
    return H["_prevx"].to_numpy(float)


def prepare_fat(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    H = history(P, L)
    f, imp = fat(H)
    out = {}
    for k, v in {"bd_fat": f, "bd_fatimp": imp, "bd_off": off_site(H)}.items():
        out[f"{k}_a"], out[f"{k}_b"] = at_model(P, H, v)
    return out


def _imp_mod(P: pd.DataFrame) -> np.ndarray:
    ia, ib = ab(P, "bd_fatimp")
    return centre(P, ((np.fmax(ia, ib) > 0.5)).astype(float))


def combine_bload(P: pd.DataFrame) -> dict:
    (fa, fb), (oa, ob), (ia, ib) = ab(P, "bd_fat"), ab(P, "bd_off"), ab(P, "bd_fatimp")
    m_fat, m_off = fa - fb, oa - ob
    x = block(P, [(m_fat, -1), (m_off, -1)])
    ctrl, names = controls(P, {"in_sets_14d": col(P, "in_sets_14d"),
                               "surf_layoff_a-b": col(P, "in_surf_layoff_a") - col(P, "in_surf_layoff_b"),
                               "fat_imputed_share_a-b": ia - ib}, x, NEAREST.get("B-LOAD"))
    return {"x": x, "controls": ctrl, "control_names": names, "eta_mod_controls": _imp_mod(P)[:, None],
            "tabpfn": {"bd_fat3": (m_fat, "diff", None), "bd_off3": (m_off, "diff", None)}}


def combine_h053(P: pd.DataFrame) -> dict:
    fa, fb = ab(P, "bd_fat")
    ia, ib = ab(P, "bd_fatimp")
    aa, ag = ab(P, "age")
    ka, kb = np.maximum(aa - AGE_KNEE_53, 0), np.maximum(ag - AGE_KNEE_53, 0)
    x = fa * ka - fb * kb
    ctrl, names = controls(P, {"fat_a-b": fa - fb, "in_age": col(P, "in_age"), "in_age_sq": col(P, "in_age_sq"),
                               "in_sets_14d": col(P, "in_sets_14d"), "fat_imputed_share_a-b": ia - ib}, x,
                           NEAREST.get("I-053"))
    mods = np.column_stack([centre(P, fa + fb), centre(P, ka + kb), _imp_mod(P)])
    return {"x": x, "controls": ctrl, "control_names": names, "eta_mod_controls": mods,
            "tabpfn": {"bd_fat3_x_age26": (x, "diff", None)}}


def prepare_prev(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    H = history(P, L)
    f, imp = fat(H)
    out = {}
    for k, v in {"bd_prevx": prev_x(H), "bd_rest": H["rest"].to_numpy(float), "bd_fat": f}.items():
        out[f"{k}_a"], out[f"{k}_b"] = at_model(P, H, v)
    return out


def combine_bprev(P: pd.DataFrame) -> dict:
    (pa, pb), (ra, rb), (fa, fb) = ab(P, "bd_prevx"), ab(P, "bd_rest"), ab(P, "bd_fat")
    ca = (ra <= 1).astype(float) - (ra >= 2).astype(float)          # 1[rest <= 1] - 1[rest >= 2]
    cb = (rb <= 1).astype(float) - (rb >= 2).astype(float)
    m_l1, m_56 = pa - pb, pa * ca - pb * cb
    x = block(P, [(m_l1, -1), (m_56, -1)])
    rest7 = np.fmin(np.nan_to_num(ra, nan=7.0), 7) - np.fmin(np.nan_to_num(rb, nan=7.0), 7)
    ctrl, names = controls(P, {"in_sets_14d": col(P, "in_sets_14d"), "fat_a-b": fa - fb, "rest7_a-b": rest7,
                               "prevx_missing_a-b": miss_diff(pa, pb)}, x, NEAREST.get("B-PREV"))
    # x is missing exactly where either PrevX is: the batch then forms 1[missing] x eta itself (S11), so no copy here
    return {"x": x, "controls": ctrl, "control_names": names,
            "tabpfn": {"bd_prevx": (m_l1, "diff", None), "bd_prevx_x_rest": (m_56, "diff", None)}}


def load_members(P: pd.DataFrame) -> dict:
    """B-LOAD's members (for the diagnostics)."""
    (fa, fb), (oa, ob) = ab(P, "bd_fat"), ab(P, "bd_off")
    return {"I-052 dFat": fa - fb, "I-051 dOff": oa - ob}


def prev_members(P: pd.DataFrame) -> dict:
    """B-PREV's members (for the diagnostics)."""
    (pa, pb), (ra, rb) = ab(P, "bd_prevx"), ab(P, "bd_rest")
    ca = (ra <= 1).astype(float) - (ra >= 2).astype(float)
    cb = (rb <= 1).astype(float) - (rb >= 2).astype(float)
    return {"BOD-L1 dPrevX": pa - pb, "I-056 dPrevX x rest": pa * ca - pb * cb}


# the nearest inputs (|r| on 2014-2021 rows, result-free; nearest() with each row's own controls excluded), computed
# on 7 Oct 2026 (the corrected history order, the final family) and FIXED here so every rebuild and the fixed-trait permutations use the same control set
NEAREST: dict[str, list[str]] = {
    "I-053": ["iosO_bp_saved", "iosO_second_won", "iosO_hold"],
    "B-LOAD": ["adjperf_tpw_2w", "form_brk", "form_hold"],
    "B-PREV": ["elo_games", "elo_overall", "ratings_iid"],
    "B9a": ["iosO_ace", "prod_first_won", "prod_hold"],
    "B9b": ["sets_14d", "iosD_hold", "iosD_second_won"],
    "B10": ["adjperf_tpw_2w", "form_hold", "form_brk"],
    "B11": ["elo_overall", "elo_games", "ratings_iid"],
    "B-SWITCH": ["prod_hold", "prod_first_won", "iosO_first_won"],
    "B-INJ": ["sets_14d", "elo_games", "ratings_iid"],
    "B-HOME": ["elo_overall", "elo_games", "ratings_iid"],
    "B-STATE": ["form_brk", "form_hold", "form_rpw_first"]}   # recomputed for BOD-C1 alone (checkpoint 1, F-1)

HYPOTHESES = [
    {"hid": "I-053", "master": "I-053", "kind": "W", "sign": "-", "weight": 1.0, "trait": "slow",
     "deployment": "diff", "prepare": prepare_fat, "combine": combine_h053, "family": "11"},
    {"hid": "B-LOAD", "master": "I-052+I-051(Off)", "kind": "W", "sign": "+", "weight": 1.0, "trait": "none",
     "deployment": "diff", "prepare": prepare_fat, "combine": combine_bload, "family": "11",
     "members": {"I-052": "-", "I-051 Off": "-"}},
    {"hid": "B-PREV", "master": "BOD-L1+I-056", "kind": "W", "sign": "+", "weight": 1.0, "trait": "none",
     "deployment": "diff", "prepare": prepare_prev, "combine": combine_bprev, "family": "11",
     "members": {"BOD-L1": "-", "I-056": "-"}},
]
