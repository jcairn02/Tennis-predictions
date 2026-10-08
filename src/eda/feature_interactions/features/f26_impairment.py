"""B-INJ, hidden physical impairment (math audit block; composite, weight 0.5): I-043 rust after an unplanned layoff
(-), I-044 returning from injury: reputation against rust (-), I-045 within-event serve decay (-). Own matches only;
the expected gap is a walk-forward field table on the clock.

    gap      days since X's previous played match (f20's rest); E = the field's mean of min(gap, 90) for the same
             tour, week of the year and ranking band in the three previous seasons, lf + 1 <= T_Y (f20's
             walk_forward_ratio); a RETURN is a match with gap >= 42 days (BOD-13's six weeks) and gap > E
    n        played matches since the latest return (0 at the return itself)
    inj      1[X's row just before the return was X's retirement or a walkover X gave]
    I-043    Rust = U exp(-n / 2) (1 + 0.05 (age - 28)+ + 0.5 inj + 0.5 1[entry PR or SR]), U = log(1 + gap - E) of the
             latest return; nu = 2 (the originator's middle value), rho = 0.05 (as I-060's alpha), eta = psi = 0.5:
             fixed in advance, not tuned (math audit)
    I-044    inj44 1[gap >= 56] 1[n <= 2] e_pre (MKT-21's primary), inj44 = inj or entry PR; e_pre = overall Elo at
             the return (Elo does not move during a break) minus the tour's mean on 2014-2021 rows
    I-045    Dec = minus the shrunk within-event slope of X's serve residuals over X's matches at this event and the
             previous one, before this match: z = (z_first_in + z_first_won) / sqrt 2, binomial z-scores against X's
             own decayed means (half-life 182 days; 30 pseudo-trials at the field's walk-forward tour mean); slope by
             least squares on the match sequence, shrunk by tau2 / (tau2 + 12 / (n^3 - n)); TAU2_DEC and the
             reliability gate (first-in slope against first-won slope, real above replays, as declared: r 0.0096 on
             39,555 windows against 0.0003) from prechecks.py i045;
             0 with fewer than 2 such matches. Sign -: a decaying serve predicts losing beyond the price (the slope
             itself would carry +)
Block: x = -(z43 + z44 + z45). Controls: dU, d age, surf_layoff pair difference, d(inj44 window) (I-044 without e_pre),
the Elo difference (d e_pre), form_first_won, form_first_in, the nearest inputs.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.eda.feature_interactions import common as C
from src.eda.feature_interactions.features import f20_fatigue as F

NU, RHO, ETA_INJ, PSI_PR, AGE_C = 2.0, 0.05, 0.5, 0.5, 28.0
LAYOFF_MIN, INJ_MIN, WINDOW_N, GAP_CAP = 42.0, 56.0, 2, 90.0
DEC_HALF_LIFE, DEC_PRIOR_N = 182.0, 30.0
TAU2_DEC = 0.00390                   # prechecks.py i045 (the slopes' covariance)
USE_I045 = True    # the gate as declared PASSES: r 0.0096 (39,555 windows) > replays 0.0003 (fails a 2-SE margin)
BANDS = (20, 50, 100, 250)


def _week_band(H: pd.DataFrame) -> None:
    if "_week" not in H.columns:
        day = pd.to_datetime(H["t"].to_numpy(), unit="D")
        H["_week"] = np.minimum((day.dayofyear.to_numpy() - 1) // 7, 51).astype(str)
        rank = H["rank"].to_numpy(float)
        band = np.select([rank <= b for b in BANDS], [str(b) for b in BANDS], "other")
        H["_band"] = np.where(np.isfinite(rank), band, "other")


def layoffs(H: pd.DataFrame) -> None:
    """H columns: gap_E, ret_U (U of the latest return, 0 if none), ret_n, ret_inj, ret_gap, ret_row (-1 if none)."""
    if "ret_U" in H.columns:
        return
    _week_band(H)
    gap = H["rest"].to_numpy(float)
    ok = np.isfinite(gap)
    E = F.walk_forward_ratio(H, np.where(ok, np.minimum(gap, GAP_CAP), 0.0), np.ones(len(H)), ok,
                             [["tour", "_week", "_band"], ["tour", "_week"], ["tour"]], 3, 30, np.nan)
    H["gap_E"] = E
    ret = ok & np.isfinite(E) & (gap >= LAYOFF_MIN) & (gap > E)
    pid = H["pid"].to_numpy()
    idx = pd.Series(np.where(ret, np.arange(len(H)), np.nan))
    last = idx.groupby(pid).ffill().to_numpy()                 # the latest return at or before this row
    has = np.isfinite(last)
    r = np.where(has, last, 0).astype(int)
    played = H["played"].to_numpy(bool).astype(float)
    cum = pd.Series(played).groupby(pid).cumsum().to_numpy() - played     # played rows strictly before
    H["ret_row"] = np.where(has, r, -1)
    H["ret_n"] = np.where(has, cum - cum[r], np.nan)
    H["ret_U"] = np.where(has, np.log1p(np.maximum(gap[r] - E[r], 0)), 0.0)
    H["ret_gap"] = np.where(has, gap[r], np.nan)
    gave = (H["retired_self"].to_numpy(bool) | (H["walkover"].to_numpy(bool) & ~H["won"].to_numpy(bool)))
    before = np.maximum(r - 1, 0)
    same = has & (r >= 1) & (pid[before] == pid)
    H["ret_inj"] = np.where(same, gave[before].astype(float), 0.0)


def elo_rows(H: pd.DataFrame) -> np.ndarray:
    """Overall pre-match Elo per history row (surface-Elo pieces' R, every match)."""
    if "_elo" not in H.columns:
        pc = pd.read_parquet(C.ROOT / "data" / "studies" / "surface_elo_pieces" / "pieces.parquet",
                             columns=["match_id", "R_a", "R_b"], filters=[("year", "<=", int(H["tyear"].max()))])
        pc["match_id"] = pc["match_id"].astype(str)
        pc = pc.set_index("match_id")
        mid = H["match_id"].astype(str)
        H["_elo"] = np.where((H["side"] == "A").to_numpy(), mid.map(pc["R_a"]).to_numpy(float),
                             mid.map(pc["R_b"]).to_numpy(float))
    return H["_elo"].to_numpy(float)


def serve_z(H: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Binomial z-scores of first serves in and first-serve points won per history row (NaN without a box score)."""
    if "_z_fi" not in H.columns:
        sv, fi, fw = (H[k].to_numpy(float) for k in ("svpt", "first_in", "first_won"))
        ok = H["played"].to_numpy(bool) & (sv > 0) & (fi > 0) & (fi <= sv) & (fw >= 0) & (fw <= fi)
        lv = [["tour"], []]
        mu_fi = F.walk_forward_ratio(H, np.where(ok, fi, 0.0), np.where(ok, sv, 0.0), ok, lv, 3, 300, 0.6)
        mu_fw = F.walk_forward_ratio(H, np.where(ok, fw, 0.0), np.where(ok, fi, 0.0), ok, lv, 3, 300, 0.7)
        pid, t = H["pid"].to_numpy(), H["t"].to_numpy(float)
        tau = DEC_HALF_LIFE / math.log(2.0)
        z = []
        for k_num, k_den, mu in ((fi, sv, mu_fi), (fw, fi, mu_fw)):
            a = F.decayed_sum(pid, t, np.where(ok, k_num, 0.0), tau)
            b = F.decayed_sum(pid, t, np.where(ok, k_den, 0.0), tau)
            m = np.clip((a + DEC_PRIOR_N * mu) / (b + DEC_PRIOR_N), 0.02, 0.98)
            z.append(np.where(ok, (k_num - k_den * m) / np.sqrt(np.where(ok, k_den, 1.0) * m * (1 - m)), np.nan))
            H[f"_m{len(z)}"] = m
        H["_z_fi"], H["_z_fw"] = z
    return H["_z_fi"].to_numpy(float), H["_z_fw"].to_numpy(float)


def window_slope(H: pd.DataFrame, z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(least-squares slope of z on the match sequence, n) over the player's rows at this event and the previous one,
    strictly before each row (rows without z skipped); slope NaN with n < 2."""
    pid = H["pid"].to_numpy()
    tid = H["tournament_id"].astype(str).to_numpy()
    n_rows = len(H)
    new_seg = np.r_[True, (pid[1:] != pid[:-1]) | (tid[1:] != tid[:-1])]
    seg_first = np.maximum.accumulate(np.where(new_seg, np.arange(n_rows), 0))
    prev_first = np.where(seg_first > 0, seg_first[np.maximum(seg_first - 1, 0)], seg_first)
    start = np.where((seg_first > 0) & (pid[np.maximum(seg_first - 1, 0)] == pid), prev_first, seg_first)
    k = pd.Series(np.ones(n_rows)).groupby(pid).cumsum().to_numpy() - 1      # position within the player
    f = np.isfinite(z)
    zz = np.where(f, z, 0.0)
    parts = [f.astype(float), f * k, f * k * k, zz, zz * k]
    # prefix sums WITHIN the player (sums over his rows strictly before each row): no other player's row enters the
    # rounding of the window difference
    S = [pd.Series(v).groupby(pid).cumsum().to_numpy() - v for v in parts]
    n, c1, c2, s0, s1 = (s - s[start] for s in S)
    den = n * c2 - c1 * c1
    with np.errstate(invalid="ignore", divide="ignore"):
        slope = np.where((n >= 2) & (den > 1e-9), (n * s1 - c1 * s0) / den, np.nan)
    return slope, n


def decay(H: pd.DataFrame, tau2: float | None = None) -> np.ndarray:
    tau2 = TAU2_DEC if tau2 is None else tau2
    zfi, zfw = serve_z(H)
    s, n = window_slope(H, (zfi + zfw) / math.sqrt(2.0))
    v = np.where(n >= 2, 12.0 / np.maximum(n ** 3 - n, 1e-9), np.inf)
    return np.where(np.isfinite(s), -s * tau2 / (tau2 + v), 0.0)


def prepare_inj(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    H = F.history(P, L)
    layoffs(H)
    elo = elo_rows(H)
    r = H["ret_row"].to_numpy()
    n = H["ret_n"].to_numpy(float)
    fade = np.where(np.isfinite(n), np.exp(-np.nan_to_num(n) / NU), 0.0)
    vals = {"U": H["ret_U"].to_numpy(float), "rust0": H["ret_U"].to_numpy(float) * fade,
            "rinj": H["ret_U"].to_numpy(float) * fade * H["ret_inj"].to_numpy(float),
            "inj": H["ret_inj"].to_numpy(float), "win": ((H["ret_gap"].to_numpy(float) >= INJ_MIN)
                                                        & (np.nan_to_num(n, nan=99) <= WINDOW_N)).astype(float),
            "elo_ret": np.where(r >= 0, elo[np.maximum(r, 0)], np.nan),
            "dec": decay(H) if USE_I045 else np.zeros(len(H))}
    out = {}
    for k, v in vals.items():
        out[f"bdinj_{k}_a"], out[f"bdinj_{k}_b"] = F.at_model(P, H, v)
    return out


def inj_members(P: pd.DataFrame) -> dict:
    g = lambda k: F.ab(P, f"bdinj_{k}")                                  # noqa: E731
    (r0a, r0b), (ria, rib), (ia, ib), (wa, wb), (ea, eb) = g("rust0"), g("rinj"), g("inj"), g("win"), g("elo_ret")
    pra, prb = (P[f"entry_{s}"].astype(str).isin(["PR", "SR"]).to_numpy(float) for s in "ab")
    aa, ag = F.ab(P, "age")
    rust = [r0 * (1 + RHO * np.maximum(a - AGE_C, 0) + PSI_PR * pr) + ETA_INJ * ri
            for r0, ri, a, pr in ((r0a, ria, aa, pra), (r0b, rib, ag, prb))]
    tour = P["tour"].astype(str).to_numpy()
    d = F.disc(P)
    ra, rb = F.ab(P, "elo_R")
    mean = {t: np.nanmean(np.r_[ra[d & (tour == t)], rb[d & (tour == t)]]) for t in C.TOURS}
    mu = np.array([mean.get(t, np.nan) for t in tour])
    i44a, i44b = np.maximum(ia, pra) * wa, np.maximum(ib, prb) * wb
    out = {"I-043": rust[0] - rust[1], "I-044": i44a * np.nan_to_num(ea - mu) - i44b * np.nan_to_num(eb - mu),
           "_w44": i44a - i44b}
    if USE_I045:
        da, db = g("dec")
        out["I-045"] = da - db
    return out


def combine_inj(P: pd.DataFrame) -> dict:
    M = inj_members(P)
    x = F.block(P, [(M[k], -1) for k in ("I-043", "I-044", "I-045") if k in M])
    (ua, ub) = F.ab(P, "bdinj_U")
    named = {"U_a-b": ua - ub, "in_age": F.col(P, "in_age"),
             "surf_layoff_a-b": F.col(P, "in_surf_layoff_a") - F.col(P, "in_surf_layoff_b"),
             "inj44_window_a-b": M["_w44"], "in_elo_overall": F.col(P, "in_elo_overall"),
             "in_form_first_won": F.col(P, "in_form_first_won"), "in_form_first_in": F.col(P, "in_form_first_in")}
    ctrl, names = F.controls(P, named, x, F.NEAREST.get("B-INJ"))
    tab = {f"bdinj_{k.replace('-', '')}": (M[k], "diff", None) for k in ("I-043", "I-044", "I-045") if k in M}
    return {"x": x, "controls": ctrl, "control_names": names, "tabpfn": tab}


HYPOTHESES = [
    {"hid": "B-INJ", "master": "I-043+I-044+I-045" if USE_I045 else "I-043+I-044 (I-045 dropped: precheck)", "kind": "W", "sign": "+", "weight": 0.5, "trait": "none",
     "deployment": "diff", "prepare": prepare_inj, "combine": combine_inj, "family": "09",
     "members": {"I-043": "-", "I-044": "-", "I-045": "-"}},
]
