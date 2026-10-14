"""Red team (S3): an independent re-implementation of B-INJ from the WRITTEN specification (the docstring of
features/f26_impairment.py and the shared definitions in f20_fatigue.py's docstring), written without f26's code.

Data layer reused (documented, shared): history.long_table() (Stage 0 pre-rebuild + the match clock, each player's own
order). Everything B-INJ-specific is re-derived here: the clock t, the gap, the walk-forward field table E, returns, n,
inj, the three members, A/B assignment BY PLAYER ID (not the history's side label), the 2014-2021 standardisation.

Spec readings where the docstring is silent are parameters (OPT) so the comparison can say which reading the frozen
builder took. Reads no match result of a model match: only earlier rows' facts (status, box score) are used, and the
current row's own score/minutes/box/won never enter (asserted by the probe in binj_attack.py).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

DAY0 = pd.Timestamp("1970-01-01")
OPT = {"cut": "2024-12-20", "e_levels": (("tour", "week", "band"), ("tour", "week"), ("tour",)), "e_min_rows": 60,
       "e_rows": "all", "i44_sr": True,
       "entry_at": "current", "elo_mean": "panel_pooled", "event": ("tournament_id", "tday"), "i045_prior_year": "j"}


def tyear_of(td: pd.Series) -> np.ndarray:
    d = pd.to_datetime(td)
    y = d.dt.year.to_numpy().astype(int)
    late = (d.dt.month.to_numpy() == 12) & (d.dt.day.to_numpy() >= 20)
    return y + late.astype(int)


def player_bounds(pid: np.ndarray) -> np.ndarray:
    """Start index of each row's player block (rows of a player are contiguous)."""
    new = np.r_[True, pid[1:] != pid[:-1]]
    return np.maximum.accumulate(np.where(new, np.arange(len(pid)), 0))


def base(L: pd.DataFrame, opt: dict = OPT) -> pd.DataFrame:
    H = L[pd.to_datetime(L["tournament_date"]) < pd.Timestamp(opt["cut"])].reset_index(drop=True).copy()
    pid = pd.factorize(H["player_id"])[0]
    assert (np.diff(pid) >= 0).all() or (pd.Series(pid).diff().fillna(0) != 0).sum() == pid.max(), "players contiguous"
    H["pid"] = pid
    start = player_bounds(pid)
    H["start"] = start
    # clock: running max of obs along the player's own order
    H["t"] = H.groupby("pid")["obs"].cummax().astype(float)
    H["tyear"] = tyear_of(H["tournament_date"])
    played = ~H["walkover"].to_numpy(bool)
    H["played"] = played
    # previous PLAYED row strictly before each row (same player)
    idx = np.where(played, np.arange(len(H)), -1)
    lastp = pd.Series(idx).groupby(pid).cummax().to_numpy()            # last played at or before
    prevp = np.r_[-1, lastp[:-1]]
    prevp[np.arange(len(H)) == start] = -1
    t = H["t"].to_numpy(float)
    H["prevp"] = prevp
    H["gap"] = np.where(prevp >= 0, t - t[np.maximum(prevp, 0)], np.nan)
    day = pd.to_datetime(t, unit="D")
    H["week"] = np.minimum((day.dayofyear.to_numpy() - 1) // 7, 51)
    rank = pd.to_numeric(H["rank"], errors="coerce").to_numpy(float)
    H["band"] = np.select([rank <= 20, rank <= 50, rank <= 100, rank <= 250], ["20", "50", "100", "250"], "other")
    H["lost"] = ~H["won"].to_numpy(bool)
    return H


def T_of_year(H: pd.DataFrame) -> dict:
    first = H.groupby("tyear")["es"].min()
    return {int(y): min(float(first.get(y, np.inf)), float((pd.Timestamp(f"{y - 1}-12-20") - DAY0).days))
            for y in range(int(H["tyear"].min()), int(H["tyear"].max()) + 1)}


def field_E(H: pd.DataFrame, opt: dict = OPT) -> np.ndarray:
    """Walk-forward mean of min(gap, 90) per (tour, week, band) over the 3 previous tyears, lf + 1 <= T_Y."""
    T = T_of_year(H)
    gap = H["gap"].to_numpy(float)
    ok = np.isfinite(gap)
    if opt["e_rows"] == "played":
        ok &= H["played"].to_numpy(bool)
    v = np.minimum(gap, 90.0)
    lf, ty = H["lf"].to_numpy(float), H["tyear"].to_numpy()
    out = np.full(len(H), np.nan)
    keys_all = H[["tour", "week", "band"]].astype(str)
    for y in sorted(T):
        rows = np.flatnonzero(ty == y)
        if not len(rows):
            continue
        src = ok & (lf + 1 <= T[y]) & (ty >= y - 3) & (ty <= y - 1)
        val = np.full(len(rows), np.nan)
        for keys in opt["e_levels"]:
            keys = list(keys)
            if keys:
                g = keys_all.loc[src, keys].copy()
                g["v"] = v[src]
                agg = g.groupby(keys)["v"].agg(["sum", "size"])
                agg = agg[agg["size"] >= opt["e_min_rows"]]
                m = (agg["sum"] / agg["size"])
                q = keys_all.iloc[rows][keys]
                r = q.merge(m.rename("E").reset_index(), on=keys, how="left")["E"].to_numpy(float)
            else:
                r = np.full(len(rows), v[src].mean() if src.sum() >= opt["e_min_rows"] else np.nan)
            val = np.where(np.isfinite(val), val, r)
        out[rows] = val
    return out


def layoff_state(H: pd.DataFrame, opt: dict = OPT) -> None:
    E = field_E(H, opt)
    H["E"] = E
    gap = H["gap"].to_numpy(float)
    ret = np.isfinite(gap) & np.isfinite(E) & (gap >= 42.0) & (gap > E)
    H["is_ret"] = ret
    pid, start = H["pid"].to_numpy(), H["start"].to_numpy()
    n = len(H)
    lastr = pd.Series(np.where(ret, np.arange(n), -1)).groupby(pid).cummax().to_numpy()
    H["r"] = lastr
    played = H["played"].to_numpy(bool)
    cp = np.concatenate([[0], np.cumsum(played)])                    # cp[i] = played rows before i (global)
    r0 = np.maximum(lastr, 0)
    H["n_since"] = np.where(lastr >= 0, cp[np.arange(n)] - cp[r0], np.nan)
    st = H["status"].astype(str).to_numpy()
    lost = H["lost"].to_numpy(bool)
    gave = lost & ((st == "retired") | (st == "walkover"))
    prev_row = r0 - 1
    inj = np.where((lastr >= 0) & (prev_row >= start[r0]), gave[np.maximum(prev_row, 0)], False)
    H["inj"] = inj.astype(float)
    U = np.where(lastr >= 0, np.log1p(gap[r0] - E[r0]), 0.0)
    H["U"] = U
    H["ret_gap"] = np.where(lastr >= 0, gap[r0], np.nan)


def rust_and_i044(H: pd.DataFrame, elo_ret: np.ndarray, opt: dict = OPT) -> None:
    ent = H["entry"].astype(str).str.upper().to_numpy()
    r0 = np.maximum(H["r"].to_numpy(), 0)
    if opt["entry_at"] == "return":
        ent = ent[r0]
    prsr = np.isin(ent, ["PR", "SR"]).astype(float)
    pr = (np.isin(ent, ["PR", "SR"]) if opt.get("i44_sr", False) else (ent == "PR")).astype(float)
    age = pd.to_numeric(H["age"], errors="coerce").to_numpy(float)
    n = H["n_since"].to_numpy(float)
    U = H["U"].to_numpy(float)
    mult = 1 + 0.05 * np.maximum(age - 28.0, 0.0) + 0.5 * H["inj"].to_numpy(float) + 0.5 * prsr
    H["rust"] = np.where(H["r"].to_numpy() >= 0, U * np.exp(-n / 2.0) * mult, 0.0)
    inj44 = np.maximum(H["inj"].to_numpy(float), pr)
    win = (H["r"].to_numpy() >= 0) & (H["ret_gap"].to_numpy(float) >= 56.0) & (n <= 2)
    H["i44win"] = np.where(win, inj44, 0.0)
    w = H["i44win"].to_numpy(float)
    H["i044"] = np.where(w > 0, w * elo_ret, 0.0)


def field_rates(H: pd.DataFrame, box: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per row: the tour's walk-forward first-in rate and first-won rate (3 previous tyears, lf + 1 <= T_Y)."""
    T = T_of_year(H)
    lf, ty, tour = H["lf"].to_numpy(float), H["tyear"].to_numpy(), H["tour"].astype(str).to_numpy()
    fi, sv, fw = (H[c].to_numpy(float) for c in ("first_in", "svpt", "first_won"))
    mu_fi, mu_fw = np.full(len(H), np.nan), np.full(len(H), np.nan)
    for y in sorted(T):
        src = box & (lf + 1 <= T[y]) & (ty >= y - 3) & (ty <= y - 1)
        for tr in np.unique(tour):
            rows = (ty == y) & (tour == tr)
            s = src & (tour == tr)
            if rows.any() and s.any():
                mu_fi[rows] = fi[s].sum() / sv[s].sum()
                mu_fw[rows] = fw[s].sum() / fi[s].sum()
    return mu_fi, mu_fw


def serve_z(H: pd.DataFrame, half_life: float = 182.0, prior_n: float = 30.0) -> np.ndarray:
    """z_j = (z_first_in + z_first_won)/sqrt 2 of each box-score row against the player's own decayed means over
    STRICTLY earlier box-score rows, with prior_n pseudo-trials at the field's tour rate; NaN for rows without box."""
    fi, sv, fw = (pd.to_numeric(H[c], errors="coerce").to_numpy(float) for c in ("first_in", "svpt", "first_won"))
    box = H["played"].to_numpy(bool) & np.isfinite(fi) & np.isfinite(sv) & np.isfinite(fw) & (sv > 0) & (fi > 0)
    mu_fi, mu_fw = field_rates(H, box)
    t, start = H["t"].to_numpy(float), H["start"].to_numpy()
    z = np.full(len(H), np.nan)
    a1 = b1 = a2 = b2 = 0.0
    tl = 0.0
    lam = math.log(2.0) / half_life
    for j in range(len(H)):
        if start[j] == j:
            a1 = b1 = a2 = b2 = 0.0
        else:
            d = math.exp(-lam * (t[j] - tl))
            a1, b1, a2, b2 = a1 * d, b1 * d, a2 * d, b2 * d
        tl = t[j]
        if box[j]:
            p = (a1 + prior_n * mu_fi[j]) / (b1 + prior_n)
            q = (a2 + prior_n * mu_fw[j]) / (b2 + prior_n)
            z1 = (fi[j] - sv[j] * p) / math.sqrt(sv[j] * p * (1 - p))
            z2 = (fw[j] - fi[j] * q) / math.sqrt(fi[j] * q * (1 - q))
            z[j] = (z1 + z2) / math.sqrt(2.0)
            a1 += fi[j]; b1 += sv[j]; a2 += fw[j]; b2 += fi[j]
    return z


def decay_at(H: pd.DataFrame, z: np.ndarray, rows: np.ndarray, tau2: float = 0.00390,
             event=("tournament_id", "tday"), seq: str = "row") -> np.ndarray:
    """Dec at the given rows: minus the shrunk LS slope of z over the player's box rows at this event (before the row)
    and at the previous event; 0 with fewer than 2."""
    key = H[list(event)].astype(str).agg("|".join, axis=1).to_numpy()
    start = H["start"].to_numpy()
    n = len(H)
    newev = np.r_[True, (key[1:] != key[:-1]) | (start[1:] == np.arange(1, n))]
    ev_start = np.maximum.accumulate(np.where(newev, np.arange(n), 0))
    out = np.full(len(rows), np.nan)
    for k, i in enumerate(rows):
        if i < 0:
            continue
        es = ev_start[i]
        ps = ev_start[es - 1] if es - 1 >= start[i] else es
        w = z[ps:i]
        fin = np.isfinite(w)
        w = w[fin]
        m = len(w)
        if m < 2:
            out[k] = 0.0
            continue
        # "the match sequence": the row's position in the player's own order (walkovers and box-less matches keep
        # their slots; reading matched to the frozen builder), shrinkage still 12/(m^3 - m) on the m residuals
        s = np.arange(ps, i, dtype=float)[fin] if seq == "row" else np.arange(m, dtype=float)
        sl = float(((s - s.mean()) * (w - w.mean())).sum() / ((s - s.mean()) ** 2).sum())
        out[k] = -sl * tau2 / (tau2 + 12.0 / (m ** 3 - m))
    return out


def standardise(x: np.ndarray, disc: np.ndarray, q: float = 0.99, clip: bool = True) -> np.ndarray:
    d = disc & np.isfinite(x)
    c = float(np.quantile(np.abs(x[d]), q)) if clip else np.inf
    c = c or 1.0
    xc = np.clip(x, -c, c)
    return xc / (float(np.std(xc[d])) or 1.0)


def model_rows(H: pd.DataFrame, ids: np.ndarray, pa: np.ndarray, pb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """H row of player_a_id's and player_b_id's row of each model match, by PLAYER ID (-1 if absent)."""
    key = pd.Series(np.arange(len(H)), index=H["match_id"].astype(str) + "#" + H["player_id"].astype(str))
    key = key[~key.index.duplicated()]
    ra = key.reindex(pd.Index(ids.astype(str)) + "#" + pd.Index(pa.astype(str))).fillna(-1).to_numpy(int)
    rb = key.reindex(pd.Index(ids.astype(str)) + "#" + pd.Index(pb.astype(str))).fillna(-1).to_numpy(int)
    return ra, rb


def elo_at(H: pd.DataFrame, pieces: pd.DataFrame, rows: np.ndarray) -> np.ndarray:
    """Pre-match overall Elo (pieces R) of the history row's player at that row's match (NaN if absent)."""
    pc = pieces.set_index(pieces["match_id"].astype(str))
    ok = rows >= 0
    mid = H["match_id"].astype(str).to_numpy()[np.maximum(rows, 0)]
    pid = H["player_id"].astype(str).to_numpy()[np.maximum(rows, 0)]
    out = np.full(len(rows), np.nan)
    RA = pc["R_a"].reindex(mid).to_numpy(float)
    RB = pc["R_b"].reindex(mid).to_numpy(float)
    PA = pc["pa"].reindex(mid).astype(str).to_numpy()            # Stage 0's player_a_id of that match
    out = np.where(pid == PA, RA, RB)
    out[~ok] = np.nan
    return out


def build(L: pd.DataFrame, M: pd.DataFrame, pieces: pd.DataFrame, opt: dict = OPT) -> dict:
    """M: model rows (match_id, season, tour, player_a_id, player_b_id, elo_R_a, elo_R_b). Returns per-player and
    difference columns and x."""
    H = base(L, opt)
    layoff_state(H, opt)
    ids = M["match_id"].astype(str).to_numpy()
    ra, rb = model_rows(H, ids, M["player_a_id"].to_numpy(), M["player_b_id"].to_numpy())
    disc = M["season"].between(2014, 2021).to_numpy()
    # e_pre: Elo at the return (pieces R at the return row) minus the tour's mean on 2014-2021 rows
    r_all = H["r"].to_numpy()
    out = {"ra": ra, "rb": rb}
    tour = M["tour"].astype(str).to_numpy()
    mean = {}
    for tr in np.unique(tour):
        m = disc & (tour == tr)
        mean[tr] = float(np.nanmean(np.r_[M["elo_R_a"].to_numpy(float)[m], M["elo_R_b"].to_numpy(float)[m]]))
    for side, r in (("a", ra), ("b", rb)):
        rr = np.where(r >= 0, r_all[np.maximum(r, 0)], -1)
        out[f"elo_ret_{side}"] = elo_at(H, pieces, rr)
        out[f"e_pre_{side}"] = out[f"elo_ret_{side}"] - np.array([mean[x] for x in tour])
    for c in ("gap", "E", "U", "n_since", "inj", "ret_gap"):
        for side, r in (("a", ra), ("b", rb)):
            out[f"{c}_{side}"] = np.where(r >= 0, H[c].to_numpy(float)[np.maximum(r, 0)], np.nan)
    Hm = H  # rust needs per-row e_pre only at model rows: compute rust on all rows, I-044 at model rows
    rust_and_i044(Hm, np.zeros(len(H)), opt)
    for side, r in (("a", ra), ("b", rb)):
        out[f"rust_{side}"] = np.where(r >= 0, Hm["rust"].to_numpy(float)[np.maximum(r, 0)], np.nan)
        w = np.where(r >= 0, Hm["i44win"].to_numpy(float)[np.maximum(r, 0)], np.nan)
        out[f"i44win_{side}"] = w
        out[f"i044_{side}"] = np.where(w > 0, w * out[f"e_pre_{side}"], np.where(np.isfinite(w), 0.0, np.nan))
    z = serve_z(H)
    out["dec_a"] = decay_at(H, z, ra, event=opt["event"])
    out["dec_b"] = decay_at(H, z, rb, event=opt["event"])
    d43 = out["rust_a"] - out["rust_b"]
    d44 = out["i044_a"] - out["i044_b"]
    d45 = out["dec_a"] - out["dec_b"]
    Z = np.column_stack([standardise(v, disc) for v in (d43, d44, d45)])
    x = -np.nansum(Z, axis=1)
    x[~np.isfinite(Z).any(axis=1)] = np.nan
    out.update({"d43": d43, "d44": d44, "d45": d45, "z43": Z[:, 0], "z44": Z[:, 1], "z45": Z[:, 2], "x": x})
    out["_H"] = H
    out["_z"] = z
    return out
