"""Shared helpers of the MARKET analyst's hypothesis modules (f10-f19; docs/studies/feature_interactions/builders.md).

Reads NO results: no function here touches `a_won`. Past matches' own facts (a player's earlier wins, retirements, scores,
box scores) are pre-match information when taken strictly from the player's earlier rows (own order, safe by
construction); anything pooled over other players is built walk-forward on the match clock (lf + 1 <= es) in the module
that needs it, and probed there.

Windows and constants (fixed without results):
    DISC   2014-2021 rows: symmetric modulators are centred (per tour) and block members standardised here
    TUNE   2013-2018 rows: scale constants (view rescalings, rank->Elo line, component standardisation)
    STD    "Std" controls: the k = 3 model inputs nearest (|corr|, DISC rows) to the candidate column, among the
           antisymmetric inputs other than odds_logit (the base log-odds carries the price), plus the two switch pairs'
           A - B differences

History: `hist(L, P)` cuts the long table at the panel's last earliest-start day (no later season is read; the cut moves
with the panel, so the builders work unchanged for later seasons).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda.feature_interactions import common as C
from src.eda.feature_interactions.arms import base_inputs

TUNE = (2013, 2018)
LN10_400 = np.log(10) / 400
MAIN_LEVELS = ("GS", "FIN", "T1000", "T500", "T250")
TOUR_LEVELS = ("GS", "T1000", "T500", "T250")
LEVEL_SCORE = {"T250": 0.0, "T500": 1.0, "T1000": 2.0, "GS": 3.0, "FIN": 3.0}     # I-080's attention scale
_MEMO: dict = {}


# ------------------------------------------------------------------------------------------------ basics

def memo(key: str, *objs):
    """Decorator-free memo for expensive prepares within one process: keyed on the ids and lengths of the frames."""
    sig = (key,) + tuple((id(o), len(o)) for o in objs)
    return sig, _MEMO


def cached(key, objs, fn):
    sig, store = memo(key, *objs)
    if sig not in store:
        store[sig] = fn()
    return store[sig]


def num(P: pd.DataFrame, c: str) -> np.ndarray:
    return pd.to_numeric(P[c], errors="coerce").to_numpy(dtype=float)


def pair(P: pd.DataFrame, name: str) -> tuple[np.ndarray, np.ndarray]:
    return num(P, f"{name}_a"), num(P, f"{name}_b")


def seasons(P: pd.DataFrame, lo: int, hi: int) -> np.ndarray:
    return P["season"].astype(int).between(lo, hi).to_numpy()


def disc(P: pd.DataFrame) -> np.ndarray:
    return seasons(P, C.DISCOVERY[0], C.DISCOVERY[-1])


def tune(P: pd.DataFrame) -> np.ndarray:
    return seasons(P, *TUNE)


def tours(P: pd.DataFrame) -> np.ndarray:
    return P["tour"].astype(str).to_numpy()


def centre(v: np.ndarray, P: pd.DataFrame) -> np.ndarray:
    """A symmetric modulator minus its tour mean on the DISC rows (builders.md, step 2)."""
    v = np.asarray(v, float).copy()
    t, d = tours(P), disc(P)
    for tour in C.TOURS:
        m = t == tour
        ok = m & d & np.isfinite(v)
        if ok.any():
            v[m] = v[m] - v[ok].mean()
    return v


def zsym(v: np.ndarray, P: pd.DataFrame) -> np.ndarray:
    """A symmetric modulator, centred per tour and divided by its SD, both on the DISC rows."""
    c = centre(v, P)
    ok = disc(P) & np.isfinite(c)
    return c / c[ok].std()


def unit(v: np.ndarray, P: pd.DataFrame) -> np.ndarray:
    """An antisymmetric column divided by its root mean square on the DISC rows (never centred: it is antisymmetric)."""
    v = np.asarray(v, float)
    ok = disc(P) & np.isfinite(v)
    return v / np.sqrt(np.mean(v[ok] ** 2))


def signed_sum(members: list[tuple[np.ndarray, str]], P: pd.DataFrame, symmetric: bool) -> np.ndarray:
    """A composite block's column: each member standardised on the DISC rows and multiplied by its declared sign, then
    summed; a member missing in a row counts 0 there (its standardised centre), the row is missing only if all are."""
    parts = []
    for v, sign in members:
        s = zsym(v, P) if symmetric else unit(v, P)
        parts.append((1.0 if sign == "+" else -1.0) * s)
    M = np.column_stack(parts)
    out = np.nansum(M, axis=1)
    out[~np.isfinite(M).any(axis=1)] = np.nan
    return out


def eta(P: pd.DataFrame) -> np.ndarray:
    """The current best's out-of-sample log-odds (the screen's model base), 2014 on; NaN before."""
    return num(P, "eta_model")


def zmkt(P: pd.DataFrame) -> np.ndarray:
    """The de-vigged average closing log-odds (the market base)."""
    return num(P, "in_odds_logit")


def adj(P: pd.DataFrame) -> np.ndarray:
    """The current best's own adjustment to the price, eta_model - odds_logit (replaces the result-fitted nudge N)."""
    return eta(P) - zmkt(P)


def miss_diff(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """miss_A - miss_B, the antisymmetric missingness control."""
    return (~np.isfinite(a)).astype(float) - (~np.isfinite(b)).astype(float)


def clear_memo() -> None:
    _MEMO.clear()


# ------------------------------------------------------------------------------------------------ Std controls

def std_candidates(P: pd.DataFrame) -> dict[str, np.ndarray]:
    """The antisymmetric model inputs a Std control may be (odds_logit excluded), with the switch pairs as A - B."""
    names, kinds, partners = base_inputs()
    out = {}
    for n in names:
        if kinds[n] == "diff" and n != "odds_logit" and f"in_{n}" in P.columns:
            out[n] = num(P, f"in_{n}")
    for stem in ("surf_season", "surf_layoff"):
        if f"in_{stem}_a" in P.columns:
            out[f"{stem}_diff"] = num(P, f"in_{stem}_a") - num(P, f"in_{stem}_b")
    return out


def nearest(P: pd.DataFrame, v: np.ndarray, k: int = 3, exclude: tuple = ()) -> list[tuple[str, float]]:
    """The k candidate inputs most correlated (|corr|, DISC rows, pairwise complete) with the column v."""
    d = disc(P)
    out = []
    for n, c in std_candidates(P).items():
        if n in exclude:
            continue
        ok = d & np.isfinite(v) & np.isfinite(c)
        if ok.sum() < 1000 or np.std(c[ok]) == 0 or np.std(v[ok]) == 0:
            continue
        out.append((n, float(np.corrcoef(v[ok], c[ok])[0, 1])))
    out.sort(key=lambda t: -abs(t[1]))
    return out[:k]


def std_controls(P: pd.DataFrame, v: np.ndarray, k: int = 3, force: tuple = (), exclude: tuple = ()):
    """(matrix, names) of the forced inputs plus the k nearest others: the hypothesis's Std controls."""
    cand = std_candidates(P)
    chosen = [n for n in force if n in cand]
    chosen += [n for n, _ in nearest(P, v, k, exclude=tuple(exclude) + tuple(chosen))]
    if not chosen:
        return np.zeros((len(P), 0)), []
    return np.column_stack([cand[n] for n in chosen]), [f"in_{n}" for n in chosen]


def stack(parts: list[tuple[np.ndarray, str]]):
    """(matrix, names) from (column, name) pairs; columns may be 2-D blocks with a list of names."""
    cols, names = [], []
    for v, n in parts:
        v = np.asarray(v, float)
        if v.ndim == 2:
            cols.append(v)
            names += list(n)
        else:
            cols.append(v[:, None])
            names.append(n)
    return (np.column_stack(cols) if cols else None), names


# ------------------------------------------------------------------------------------------------ history

def hist(L: pd.DataFrame, P: pd.DataFrame) -> pd.DataFrame:
    """The long table cut at the panel's last earliest-start day, in its own order (player, then own sequence), with
    integer player codes `pc`, the monotone best-estimate day `t` (running maximum of obs) and string ids."""
    def make():
        H = L[L["es"].to_numpy(float) <= float(np.nanmax(num(P, "es")))].copy()
        H["match_id"] = H["match_id"].astype(str)
        H["player_id"] = H["player_id"].astype(str)
        H["pc"] = pd.factorize(H["player_id"])[0]
        # the player's running maximum of the best-estimate day (history.py's obs_mono): monotone in own order even
        # where an undated event's rounds carry earlier obs than the round before (rounds never reverse)
        H["t"] = H["obs"].astype(float).groupby(H["pc"].to_numpy()).cummax()
        H["first_row"] = H["pc"].to_numpy() != np.r_[-1, H["pc"].to_numpy()[:-1]]
        if not (np.diff(H["pc"].to_numpy()) >= 0).all() and not _blocks_contiguous(H["pc"].to_numpy()):
            raise RuntimeError("the long table is not ordered by player")
        return H.reset_index(drop=True)
    return cached("hist", (L, P), make)


def _blocks_contiguous(pc: np.ndarray) -> bool:
    change = np.r_[True, pc[1:] != pc[:-1]]
    return len(np.unique(pc[change])) == change.sum()


def model_pos(H: pd.DataFrame, P: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Row positions in H of each panel match's side A and side B (-1 where absent)."""
    def make():
        ids = pd.Index(P["match_id"].astype(str))
        out = []
        for s in ("A", "B"):
            m = (H["side"] == s).to_numpy()
            ser = pd.Series(np.flatnonzero(m), index=H.loc[m, "match_id"].to_numpy())
            ser = ser[~ser.index.duplicated()]
            out.append(ser.reindex(ids).fillna(-1).to_numpy(int))
        return tuple(out)
    return cached("model_pos", (H, P), make)


def at_model(H: pd.DataFrame, P: pd.DataFrame, values) -> tuple[np.ndarray, np.ndarray]:
    """A per-row value of H read at the panel's matches for side A and side B (NaN where absent)."""
    v = np.asarray(values, float)
    pa, pb = model_pos(H, P)
    return np.where(pa >= 0, v[np.maximum(pa, 0)], np.nan), np.where(pb >= 0, v[np.maximum(pb, 0)], np.nan)


def shift_own(H: pd.DataFrame, v, n: int = 1) -> np.ndarray:
    """The value in the player's n-th previous row (strictly earlier; NaN at the start of a player's history)."""
    v = np.asarray(v, float)
    out = np.full(len(v), np.nan)
    pc = H["pc"].to_numpy()
    if n < len(v):
        same = pc[n:] == pc[:-n]
        out[n:] = np.where(same, v[:-n], np.nan)
    return out


def decayed(H: pd.DataFrame, v, half_life: float) -> np.ndarray:
    """sum over the player's STRICTLY EARLIER rows j of v_j * 2^(-(t_i - t_j) / half_life), t = best-estimate days.
    Exact, through a per-player cumulative sum on the player's own time origin (half-lives of 14 days and more)."""
    lam = np.log(2.0) / half_life
    pc, t = H["pc"].to_numpy(), H["t"].to_numpy(float)
    t0 = pd.Series(t).groupby(pc).transform("min").to_numpy()
    rel = t - t0
    if np.nanmax(lam * rel) > 650:
        raise ValueError("half-life too short for the cumulative form; use decayed_lag")
    x = np.nan_to_num(np.asarray(v, float)) * np.exp(lam * rel)
    cs = pd.Series(x).groupby(pc).cumsum().to_numpy() - x
    return cs * np.exp(-lam * rel)


def decayed_lag(H: pd.DataFrame, v, tau: float, horizon: float, max_lag: int = 60) -> np.ndarray:
    """sum over strictly earlier own rows within `horizon` days of v_j * exp(-(t_i - t_j) / tau) (short time scales)."""
    v = np.nan_to_num(np.asarray(v, float))
    pc, t = H["pc"].to_numpy(), H["t"].to_numpy(float)
    out = np.zeros(len(v))
    for lag in range(1, max_lag + 1):
        same = pc[lag:] == pc[:-lag]
        dt = t[lag:] - t[:-lag]
        ok = same & (dt <= horizon)
        if not ok.any():
            break
        out[lag:] += np.where(ok, v[:-lag] * np.exp(-np.maximum(dt, 0.0) / tau), 0.0)
    return out


def window_sum(H: pd.DataFrame, v, days: float) -> tuple[np.ndarray, np.ndarray]:
    """(sum of v, number of rows) over the player's strictly earlier rows with t_j >= t_i - days."""
    pc, t = H["pc"].to_numpy(), H["t"].to_numpy(float)
    key = pc.astype(np.float64) * 1e6 + t
    if not (np.diff(key) >= 0).all():
        raise RuntimeError("rows are not in (player, day) order")
    lo = np.searchsorted(key, key - days, side="left")
    i = np.arange(len(key))
    cs = np.r_[0.0, np.cumsum(np.nan_to_num(np.asarray(v, float)))]
    return cs[i] - cs[lo], (i - lo).astype(float)


# ------------------------------------------------------------------------------------------------ per-player quantities

FAT_TAU, FAT_HORIZON, FAT_IMPUTED_WEIGHT = 3.0, 45.0, 0.05
WARMUP_LAST = 2012            # history-only seasons before the panel's first (2013)


def minutes_filled(H: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Each played match's minutes; where missing, total points x the tour's median minutes per point, else games x the
    tour's median minutes per game (medians over the 2010-2012 warm-up rows, before any panel season, so no
    later match moves them: statistics, no result). Walkovers 0.
    Returns (minutes, imputed flag: 1 where the value is a fallback or unknown)."""
    played = H["played"].to_numpy(bool)
    mins = H["minutes"].to_numpy(float)
    mins = np.where((mins > 0) & (mins < 1000), mins, np.nan)
    pts, games = H["tpw_d"].to_numpy(float), H["games"].to_numpy(float)
    yr = pd.to_datetime(H["tournament_date"]).dt.year.to_numpy()
    tour = H["tour"].astype(str).to_numpy()
    out, imp = mins.copy(), np.zeros(len(H))
    for tr in C.TOURS:
        m = tour == tr
        ref = m & (yr <= WARMUP_LAST) & np.isfinite(mins)
        mpp = np.nanmedian(mins[ref & (pts > 0)] / pts[ref & (pts > 0)])
        mpg = np.nanmedian(mins[ref & (games > 0)] / games[ref & (games > 0)])
        need = m & ~np.isfinite(out)
        by_pts = need & (pts > 0)
        out[by_pts] = pts[by_pts] * mpp
        by_games = need & ~by_pts & (games > 0)
        out[by_games] = games[by_games] * mpg
        imp[need] = 1.0
    out = np.where(played, out, 0.0)
    imp = np.where(played, imp, 0.0)
    return out, imp


def fat(H: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """I-052's Fat (math audit: tau2 = 3 days fixed in advance): log(1 + sum_j minutes_j exp(-(t_i - t_j)/3)) over the
    player's strictly earlier matches (best-estimate days), and the imputed flag: 1 if any match weighing >= 0.05 had
    imputed or unknown minutes."""
    def make():
        mins, imp = minutes_filled(H)
        unknown = H["played"].to_numpy(bool) & ~np.isfinite(mins)
        S = decayed_lag(H, np.nan_to_num(mins), FAT_TAU, FAT_HORIZON)
        cut = -FAT_TAU * np.log(FAT_IMPUTED_WEIGHT)
        flag = decayed_lag(H, np.maximum(imp, unknown.astype(float)), 1e9, cut) > 0
        return np.log1p(S), flag.astype(float)
    return cached("fat", (H,), make)


def fame(H: pd.DataFrame) -> np.ndarray:
    """I-083's F = log(1 + main-tour titles + Grand Slam events reached at quarter-final or better), counted over the
    player's strictly earlier matches (history from 2010: left-censored for careers that began earlier)."""
    def make():
        main = H["level"].isin(MAIN_LEVELS).to_numpy() & ~H["qualifying"].astype(bool).to_numpy()
        title = (main & (H["round"].astype(str) == "F").to_numpy() & H["won"].astype(bool).to_numpy()).astype(float)
        qf = ((H["level"] == "GS").to_numpy() & ~H["qualifying"].astype(bool).to_numpy()
              & (H["round_order"].to_numpy(float) >= 15))
        key = pd.Series(H["pc"].astype(str).to_numpy() + "|" + H["tournament_id"].astype(str).to_numpy())
        first_qf = np.zeros(len(H), bool)
        idx = np.flatnonzero(qf)
        first_qf[idx] = ~key.iloc[idx].duplicated().to_numpy()       # the event's first QF-or-later match (own order)
        cnt = title + first_qf.astype(float)
        before = pd.Series(cnt).groupby(H["pc"].to_numpy()).cumsum().to_numpy() - cnt
        return np.log1p(before)
    return cached("fame", (H,), make)


def elo_rows(H: pd.DataFrame) -> np.ndarray:
    """Each row's pre-match overall Elo (surface_elo_pieces, every level) for the row's player."""
    def make():
        pc = pd.read_parquet(C.ROOT / "data" / "studies" / "surface_elo_pieces" / "pieces.parquet",
                             columns=["match_id", "R_a", "R_b"])
        pc["match_id"] = pc["match_id"].astype(str)
        pc = pc.drop_duplicates("match_id").set_index("match_id")
        mid = H["match_id"].to_numpy()
        ra, rb = pc["R_a"].reindex(mid).to_numpy(float), pc["R_b"].reindex(mid).to_numpy(float)
        return np.where(H["side"].to_numpy() == "A", ra, rb)
    return cached("elo_rows", (H,), make)


def unranked_value(H: pd.DataFrame, P: pd.DataFrame) -> np.ndarray:
    """Stage 1's rule per panel row: one below the worst rank seen on the tour in earlier seasons (all levels)."""
    yr = pd.to_datetime(H["tournament_date"]).dt.year
    worst = pd.to_numeric(H["rank"], errors="coerce").groupby([H["tour"].astype(str).to_numpy(), yr.to_numpy()]).max()
    out = np.full(len(P), np.nan)
    for tr in C.TOURS:
        s = worst.loc[tr].sort_index().cummax()
        prior = s.shift(1).fillna(s.iloc[0])
        m = tours(P) == tr
        out[m] = prior.reindex(P.loc[m, "season"].astype(int)).ffill().to_numpy() + 1
    return out


# ------------------------------------------------------------------------------------------------ panel-level quantities

def views_scale(P: pd.DataFrame, v: np.ndarray, lo: float = 0.005, hi: float = 0.995) -> np.ndarray:
    """A log-odds view rescaled, per tour, to the price's SD on the TUNE rows (I-034's result-free fix); the SDs are
    taken after winsorising each column at its 0.5% and 99.5% quantiles (ratings_iid saturates at +-9.21)."""
    out = np.full(len(P), np.nan)
    t, m0 = tours(P), tune(P)
    z = zmkt(P)
    for tr in C.TOURS:
        m = t == tr
        ref = m & m0 & np.isfinite(v) & np.isfinite(z)
        qv, qz = np.quantile(v[ref], [lo, hi]), np.quantile(z[ref], [lo, hi])
        sv, sz = np.clip(v[ref], *qv).std(), np.clip(z[ref], *qz).std()
        out[m] = v[m] * sz / sv
    return out


def delta1(P: pd.DataFrame) -> np.ndarray:
    """Delta1 = the points view (ratings_iid) minus the results view (offset Elo: elo_overall + elo_surf_offset), each
    rescaled to the price's SD within tour on 2013-2018 (antisymmetric)."""
    return views_scale(P, num(P, "in_ratings_iid")) - views_scale(P, num(P, "in_elo_overall")
                                                                  + num(P, "in_elo_surf_offset"))


def round_depth(P: pd.DataFrame) -> np.ndarray:
    """Round depth in the draw: its first round 0, the final 1 (first round from the draw size); round robin 0.5."""
    r = num(P, "in_round")
    ds = num(P, "draw_size")
    first = np.select([ds >= 96, ds >= 48, ds >= 28, ds >= 12], [11.0, 12.0, 13.0, 14.0], 15.0)
    d = np.clip((r - first) / (17.0 - first), 0.0, 1.0)
    return np.where(r == 10, 0.5, d)


def level_dummies(P: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    """Indicators of the levels other than the 250s (symmetric), centred per tour on the DISC rows."""
    lv = P["level"].astype(str).to_numpy()
    cols, names = [], []
    for name in ("GS", "FIN", "T1000", "T500"):
        cols.append(centre((lv == name).astype(float), P))
        names.append(f"lvl_{name}")
    return np.column_stack(cols), names


def ranks(P: pd.DataFrame, H: pd.DataFrame | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(rank_A, rank_B, unranked_A, unranked_B): Stage 0's pre-match ranks, an unranked player at Stage 1's value when
    the history is given (else at the panel's worst rank + 1)."""
    ra, rb = pair(P, "rank")
    ua, ub = (~np.isfinite(ra)).astype(float), (~np.isfinite(rb)).astype(float)
    fill = unranked_value(H, P) if H is not None else np.full(len(P), np.nanmax(np.r_[ra, rb]) + 1)
    return np.where(ua > 0, fill, ra), np.where(ub > 0, fill, rb), ua, ub


def evidence_rbar(P: pd.DataFrame, K: float = 20.0) -> np.ndarray:
    """I-032's evidence weight: the harmonic mean over the two players of n/(n + K), n = surface matches rated, K = 20."""
    na, nb = pair(P, "elo_NS")
    ra, rb = na / (na + K), nb / (nb + K)
    return 2 * ra * rb / np.maximum(ra + rb, 1e-12)


def describe(v: np.ndarray, P: pd.DataFrame) -> dict:
    """Result-free distribution of a column on the DISC rows."""
    v = np.asarray(v, float)
    ok = disc(P) & np.isfinite(v)
    q = np.quantile(v[ok], [0.01, 0.1, 0.5, 0.9, 0.99]) if ok.any() else [np.nan] * 5
    return {"n": int(ok.sum()), "mean": float(np.mean(v[ok])), "sd": float(np.std(v[ok])),
            "share_nonzero": float(np.mean(v[ok] != 0)), "q01_q10_q50_q90_q99": [float(x) for x in q]}


# ------------------------------------------------------------------------------------------------ final-family helpers

def signed_sum_masked(members: list[tuple[np.ndarray, str]], d: np.ndarray, symmetric: bool) -> np.ndarray:
    """signed_sum on any row subset (for x_of_eta): each member standardised on the rows where d (the DISC mask of the
    given rows) holds; a missing member counts 0, the row is missing only if all members are."""
    parts = []
    for v, sign in members:
        v = np.asarray(v, float)
        ok = d & np.isfinite(v)
        s = (v - v[ok].mean()) / v[ok].std() if symmetric else v / np.sqrt(np.mean(v[ok] ** 2))
        parts.append((1.0 if sign == "+" else -1.0) * s)
    Mx = np.column_stack(parts)
    out = np.nansum(Mx, axis=1)
    out[~np.isfinite(Mx).any(axis=1)] = np.nan
    return out


def rest_played(H: pd.DataFrame) -> np.ndarray:
    """Days since the player's previous PLAYED match at any level (best-estimate days; NaN for a first match)."""
    t = H["t"].to_numpy(float)
    tp = pd.Series(np.where(H["played"].to_numpy(bool), t, np.nan)).groupby(H["pc"].to_numpy()).ffill().to_numpy()
    return t - shift_own(H, tp)


def elo_forecast(P: pd.DataFrame, lo: int = 2014, hi: int = 2018) -> np.ndarray:
    """The fit-free Elo forecast F = c x (elo_overall + elo_surf_offset), c = SD(price) / SD(offset-Elo log-odds) per
    tour on the lo-hi rows (SD-matching; the rulings' MKT-R4: no outcome, no regression on the price)."""
    z = zmkt(P)
    elo = num(P, "in_elo_overall") + num(P, "in_elo_surf_offset")
    F = np.full(len(P), np.nan)
    rows = seasons(P, lo, hi)
    for tr in C.TOURS:
        m = tours(P) == tr
        ok = m & rows & np.isfinite(z) & np.isfinite(elo)
        F[m] = elo[m] * z[ok].std() / elo[ok].std()
    return F


def ranks_fixed(P: pd.DataFrame, unranked: float = 1500.0):
    """(rank_A, rank_B, unranked_A, unranked_B) with an unranked player at a fixed rank (the family's I-036 rule)."""
    ra, rb = pair(P, "rank")
    ua, ub = (~np.isfinite(ra)).astype(float), (~np.isfinite(rb)).astype(float)
    return np.where(ua > 0, unranked, ra), np.where(ub > 0, unranked, rb), ua, ub


def body_fat(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    """I-052's Fat and imputed-load share from the body analyst's builder (f20_fatigue), so the family has one Fat:
    bd_fat_a/b, bd_fatimp_a/b."""
    from src.eda.feature_interactions.features import f20_fatigue as F20
    return F20.prepare_fat(P, L)
