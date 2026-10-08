"""Serve-speed TabPFN study, latency follow-up (agent 2, the modeller): the speed-state feature when speeds arrive late.

Plan (fixed by the lead): data/studies/serve_speed_tabpfn/latency/plan.md. Reuses features.py and panel.py by import
(never edits them). Reads no match result: box scores come from stage0_match_players.parquet with an explicit column
list that never names `won`, sets or games.

Scenarios: each panel row gets a release day; a row enters a target's history and the as-of edition offsets only when
release <= es (the target's earliest start).
    A    lf + 1 (the backtest as run; the history follows features.py exactly, so spd_A_M0 == spd_f)
    B    today's sources going forward (release days from the engineer's availability.parquet)
    Lk   lf + 1 + k for k in 1, 3, 7, 14
Methods:
    M0   spd_f recomputed on the released rows; constants unchanged (features.MEN)
    M1   M0 with the half-life only re-tuned per scenario on T1 (seasons <= 2022), checked on 2023
    M2   the nowcast: a history match whose speed is not released by es but whose box score is (box_release <= es)
         enters the filter as a pseudo-observation of its centred speed,
             z_nc = L + a f + c0 + beta' d_box,   noise variance R_nc,
         where (L, f) is the filter's state just before that match and d_box the match's box-score rates minus the
         player's own 364-day rates (aces, double faults and first serves in per service point, first- and second-
         serve points won, log service points). (a, c0, beta) come from OLS on men's timed matches <= 2022 (target:
         the match's centred speed minus the instant filter's level); R_nc is tuned on T1 <= 2022; 2023 is the check.

Columns (variants.parquet): spd_<scenario>_<method> = clip((f_A - f_B) / sd, -4, 4), sd = the SD of f_A - f_B over
men's 2022-23 frame matches (own SD per variant), women 0, never NaN.

Run: ./python.sh src/eda/serve_speed_tabpfn/latency/features_latency.py [--no-probes]
Writes data/studies/serve_speed_tabpfn/latency/variants.parquet, variants_meta.json, readings.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import features as F  # noqa: E402
from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402

OUT = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "latency"
AVAIL = OUT / "availability.parquet"
VARIANTS = OUT / "variants.parquet"
META = OUT / "variants_meta.json"
READINGS = OUT / "readings.json"
MATCH_PLAYERS = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_match_players.parquet"
STAGE0 = F.STAGE0
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"

LAGS = {"L1": 1, "L3": 3, "L7": 7, "L14": 14}
MEN = dict(F.MEN)
HL_GRID = (3.0, 5.0, 7.0, 10.0, 14.0, 21.0, 28.0, 42.0, 60.0)
RNC_MULT = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0)
BOX_COLS = ["match_id", "player_id", "has_box", "ace", "df", "svpt", "first_in", "first_won", "second_won"]
DEV = ["d_ace", "d_df", "d_fin", "d_fwon", "d_swon", "d_lsvpt"]
NORM_MIN_SVPT, NORM_MIN_MATCHES = 150.0, 3
T1_TUNE, T1_EVAL = (2019, 2022), (2023, 2023)
GATE_YEARS = (2022, 2023)
SD_SEASONS = (2022, 2023)
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------ inputs
def load_panel() -> pd.DataFrame:
    return F.prepare_panel(P.load_panel(use_only=True))


def load_availability() -> pd.DataFrame:
    return pd.read_parquet(AVAIL, columns=["match_id", "side", "player_id", "lf", "release_A", "release_B", "release_L1",
                                           "release_L3", "release_L7", "release_L14", "rule_B", "box_release"])


def release_days(p: pd.DataFrame, avail: pd.DataFrame | None = None) -> pd.DataFrame:
    """Release day per panel row (aligned with p) for every scenario, and the box-score release day, from the engineer's
    availability.parquet (one row per Stage 0 player-match). A and the lags are checked against lf; Astrict (lf + 1 applied
    strictly to own history too) is a diagnostic."""
    avail = load_availability() if avail is None else avail
    key = p[["match_id", "side"]].astype(str)
    m = key.merge(avail.astype({"match_id": str, "side": str}), on=["match_id", "side"], how="left", validate="one_to_one")
    assert m["release_B"].notna().all(), "a panel row has no release day"
    assert (m["lf"].to_numpy(np.int64) == p["lf"].to_numpy(np.int64)).all(), "availability lf differs from the panel"
    lf = p["lf"].to_numpy(np.int64)
    r = pd.DataFrame(index=p.index)
    r["Astrict"] = lf + 1
    assert (m["release_A"].to_numpy(np.int64) == lf + 1).all()
    for k, lag in LAGS.items():
        r[k] = m[f"release_{k}"].to_numpy(np.int64)
        assert (r[k].to_numpy() == lf + 1 + lag).all()
    r["B"] = m["release_B"].to_numpy(np.int64)
    r["box"] = m["box_release"].to_numpy(np.int64)
    r["rule_B"] = m["rule_B"].to_numpy()
    return r


def box_release_of(box: pd.DataFrame, avail: pd.DataFrame) -> np.ndarray:
    """box_release per box-table row (by match and player), lf + 1 where the availability table has none."""
    a = avail[["match_id", "player_id", "box_release"]].drop_duplicates(["match_id", "player_id"])
    m = box[["match_id", "player_id"]].astype(str).merge(a.astype({"match_id": str, "player_id": str}),
                                                          on=["match_id", "player_id"], how="left")
    br = m["box_release"].to_numpy(float)
    return np.where(np.isfinite(br), br, box["lf"].to_numpy(float) + 1)


def box_table(tour: str = "atp") -> pd.DataFrame:
    """Box-score player-matches with the own-order keys and the clock. Explicit columns, no result."""
    mp = pd.read_parquet(MATCH_PLAYERS, columns=BOX_COLS)
    mp = mp[mp["has_box"].astype(bool) & (mp["svpt"] > 0)]
    k = pd.read_parquet(STAGE0, columns=["match_id", "tour", "year", "level", "qualifying", "tournament_id",
                                         "tournament_date", "round_order", "surface"])
    mp = mp.merge(k[k["tour"].eq(tour)], on="match_id", how="inner")
    tm = pd.read_parquet(TIMING, columns=["match_id", "es", "lf", "obs"])
    mp = mp.merge(tm, on="match_id", how="left")
    mp = mp[mp["obs"].notna()].copy()
    mp["tdate"] = mp["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    mp["obs"] = np.floor(mp["obs"]).astype("int64")
    for c in ("ace", "df", "svpt", "first_in", "first_won", "second_won"):
        mp[c] = pd.to_numeric(mp[c], errors="coerce").astype(float)
    mp = mp.sort_values(["player_id", "tdate", "tournament_id", "round_order", "obs", "match_id"], kind="mergesort")
    return mp.reset_index(drop=True)


def _rates(b: pd.DataFrame | dict) -> dict:
    sv, fi = np.asarray(b["svpt"], float), np.asarray(b["first_in"], float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return {"ace": np.asarray(b["ace"], float) / sv, "df": np.asarray(b["df"], float) / sv, "fin": fi / sv,
                "fwon": np.asarray(b["first_won"], float) / fi,
                "swon": np.asarray(b["second_won"], float) / (sv - fi)}


def box_deviations(p: pd.DataFrame, box: pd.DataFrame) -> pd.DataFrame:
    """Per panel row (aligned with p): the match's box-score rates minus the player's own rates over his earlier box
    matches (own order: earlier events, earlier rounds of the same event) with obs within 364 days before the match's
    obs; NaN when the match has no box score or the norm is thin (< 150 service points or < 3 matches)."""
    out = pd.DataFrame(np.nan, index=p.index, columns=DEV)
    bkey = pd.Series(np.arange(len(box)), index=pd.MultiIndex.from_arrays([box["match_id"].astype(str),
                                                                          box["player_id"].astype(str)]))
    bkey = bkey[~bkey.index.duplicated()]
    own = bkey.reindex(pd.MultiIndex.from_arrays([p["match_id"].astype(str), p["player_id"].astype(str)]))
    own = own.fillna(-1).astype(np.int64).to_numpy()
    cnt = box[["ace", "df", "svpt", "first_in", "first_won", "second_won"]].to_numpy(float)
    lsv = np.log(box["svpt"].to_numpy(float))
    b_td, b_ro, b_ob = box["tdate"].to_numpy(float), box["round_order"].to_numpy(float), box["obs"].to_numpy(float)
    tid_codes, _ = pd.factorize(pd.concat([box["tournament_id"].astype(str), p["tournament_id"].astype(str)]))
    b_tid, p_tid = tid_codes[:len(box)], tid_codes[len(box):]
    groups = box.groupby("player_id", sort=False).indices
    have = np.flatnonzero(own >= 0)
    rows_by_player = pd.Series(have).groupby(p["player_id"].to_numpy()[have]).indices
    p_td, p_ro, p_ob = p["tdate"].to_numpy(float), p["round_order"].to_numpy(float), p["obs"].to_numpy(float)
    res = np.full((len(p), len(DEV)), np.nan)
    for pid, loc in rows_by_player.items():
        ti = have[loc]
        r = groups.get(pid)
        if r is None:
            continue
        earlier = (b_td[r][None, :] < p_td[ti, None]) | ((b_tid[r][None, :] == p_tid[ti, None])
                                                          & (b_ro[r][None, :] < p_ro[ti, None]))
        m = earlier & (b_ob[r][None, :] >= p_ob[ti, None] - 364.0)
        S = m.astype(float) @ cnt[r]                                # sums of the six counts
        nm = m.sum(1)
        msv = (m * lsv[r][None, :]).sum(1) / np.maximum(nm, 1)
        norm = _rates({"ace": S[:, 0], "df": S[:, 1], "svpt": S[:, 2], "first_in": S[:, 3], "first_won": S[:, 4],
                       "second_won": S[:, 5]})
        cur = _rates({k: cnt[own[ti], j] for j, k in enumerate(["ace", "df", "svpt", "first_in", "first_won",
                                                                 "second_won"])})
        ok = (S[:, 2] >= NORM_MIN_SVPT) & (nm >= NORM_MIN_MATCHES)
        dev = np.column_stack([cur["ace"] - norm["ace"], cur["df"] - norm["df"], cur["fin"] - norm["fin"],
                               cur["fwon"] - norm["fwon"], cur["swon"] - norm["swon"], lsv[own[ti]] - msv])
        dev[~ok] = np.nan
        res[ti] = dev
    out[:] = res
    out[~np.isfinite(out).all(axis=1)] = np.nan
    return out


# ------------------------------------------------------------------------------------------------ histories
def histories_rel(p: pd.DataFrame, t: pd.DataFrame, rel: np.ndarray | None, box_rel: np.ndarray | None = None,
                  nc_ok: np.ndarray | None = None) -> dict:
    """features.histories' own-history rule (earlier events, earlier rounds of the same event; obs >= es - 364; own
    order), restricted to rows released by the target's es (rel <= es). With box_rel and nc_ok, a row that is not
    released but whose box score is (box_rel <= es) and that has nowcast inputs (nc_ok) enters as a nowcast row."""
    if rel is None:                                  # scenario A as built: features.py's history exactly
        h = F.histories(p, t)
        h["nc"] = np.zeros(h["idx"].shape, bool)
        return h
    n = len(t)
    tid_codes, _ = pd.factorize(pd.concat([p["tournament_id"].astype(str), t["tournament_id"].astype(str)]))
    p_tid, t_tid = tid_codes[:len(p)], tid_codes[len(p):]
    p_td, p_ro, p_ob = p["tdate"].to_numpy(float), p["round_order"].to_numpy(float), p["obs"].to_numpy(float)
    p_ks = p["basis"].astype(str).eq("ks").to_numpy()
    rel = np.asarray(rel, float)
    t_td, t_ro, t_es = t["tdate"].to_numpy(float), t["round_order"].to_numpy(float), t["es"].to_numpy(float)
    groups = p.groupby("player_id", sort=False).indices
    lists, nlists = [np.empty(0, np.int64)] * n, [np.empty(0, bool)] * n
    k14 = np.zeros(n, np.int64); k28 = np.zeros(n, np.int64); ks28 = np.zeros(n, np.int64)
    pts28 = np.zeros(n, np.int64); nnc = np.zeros(n, np.int64)
    last_age = np.full(n, np.nan)
    valid = t["player_id"].notna().to_numpy() & np.isfinite(t_es) & np.isfinite(t_td)
    tg = pd.Series(np.arange(n))[valid].groupby(t["player_id"].to_numpy()[valid]).indices
    for pid, loc in tg.items():
        ti = np.arange(n)[valid][loc]
        r = groups.get(pid)
        if r is None:
            continue
        earlier = (p_td[r][None, :] < t_td[ti, None]) | ((p_tid[r][None, :] == t_tid[ti, None])
                                                          & (p_ro[r][None, :] < t_ro[ti, None]))
        inwin = p_ob[r][None, :] >= (t_es[ti, None] - F.WINDOW)
        base = earlier & inwin
        spd = base & (rel[r][None, :] <= t_es[ti, None])
        if box_rel is not None:
            nc = base & ~spd & (np.asarray(box_rel, float)[r][None, :] <= t_es[ti, None]) & nc_ok[r][None, :]
        else:
            nc = np.zeros_like(spd)
        use = spd | nc
        ob = p_ob[r]
        near14 = spd & (ob[None, :] >= t_es[ti, None] - 14.0)
        near28 = spd & (ob[None, :] >= t_es[ti, None] - 28.0)
        k14[ti], k28[ti] = near14.sum(1), near28.sum(1)
        ks28[ti] = (near28 & p_ks[r][None, :]).sum(1)
        pts28[ti] = (near28 & ~p_ks[r][None, :]).sum(1)
        nnc[ti] = nc.sum(1)
        anyh = spd.any(1)
        last = np.where(spd, ob[None, :], -np.inf).max(1)
        last_age[ti] = np.where(anyh, t_es[ti] - last, np.nan)
        for j, i in enumerate(ti):
            lists[i] = r[use[j]]
            nlists[i] = nc[j][use[j]]
    H = max(1, max((len(x) for x in lists), default=1))
    idx = np.full((n, H), -1, np.int64)
    ncm = np.zeros((n, H), bool)
    for i, (x, y) in enumerate(zip(lists, nlists)):
        if len(x):
            idx[i, :len(x)] = x
            ncm[i, :len(x)] = y
    return {"idx": idx, "nc": ncm, "k14": k14, "k28": k28, "ks28": ks28, "pts28": pts28, "last_age": last_age,
            "hist": (idx >= 0).sum(1), "n_nowcast": nnc}


# ------------------------------------------------------------------------------------------------ the filter
def kalman_nc(Z: np.ndarray, R: np.ndarray, DAY: np.ndarray, tday: np.ndarray, prm: dict,
              NC: np.ndarray | None = None, W: np.ndarray | None = None, a: float = 1.0) -> dict:
    """features.kalman with nowcast rows: where NC is true the observation is the pseudo-value L + a f_pred + W (its
    noise in R). Without nowcast rows it is features.kalman, operation for operation."""
    if NC is None or not NC.any():
        return F.kalman(Z, R, DAY, tday, prm)
    nt, H = Z.shape
    lam = math.log(2.0) / prm["hl"]
    s2f, q, c = prm["s2f"], prm["q"], prm["c"]
    L = np.zeros(nt); f = np.zeros(nt)
    P11 = np.full(nt, F.BIG); P12 = np.zeros(nt); P22 = np.full(nt, s2f)
    last = np.full(nt, np.nan)
    seen = np.zeros(nt, bool)                        # a released speed has set the (diffuse) level
    for k in range(H):
        real = np.isfinite(Z[:, k])
        nck = NC[:, k] & seen                        # a nowcast row is used only once the level is known
        act = real | nck
        if not (real | NC[:, k]).any():
            break
        dt_ = np.where(act & np.isfinite(last), np.maximum(DAY[:, k] - np.nan_to_num(last), 0.0), 0.0)
        phi = np.exp(-lam * dt_)
        fp = f * phi
        P11p = P11 + q * dt_
        P12p = P12 * phi
        P22p = P22 * phi * phi + s2f * (1.0 - phi * phi)
        zk = np.where(nck, L + a * fp + np.nan_to_num(W[:, k]), np.where(real, np.nan_to_num(Z[:, k]), 0.0))
        z = np.where(act, zk, 0.0)
        Rk = np.where(act, R[:, k], 1.0)
        v = z - L - fp
        S = P11p + 2.0 * P12p + P22p + Rk
        cs = c * np.sqrt(S)
        v = np.minimum(np.maximum(v, -cs), cs)
        K1 = (P11p + P12p) / S
        K2 = (P12p + P22p) / S
        L = np.where(act, L + K1 * v, L)
        f = np.where(act, fp + K2 * v, f)
        P11 = np.where(act, P11p - K1 * K1 * S, P11)
        P12 = np.where(act, P12p - K1 * K2 * S, P12)
        P22 = np.where(act, P22p - K2 * K2 * S, P22)
        last = np.where(act, DAY[:, k], last)
        seen |= real
    has = np.isfinite(last)
    d = np.where(has, np.maximum(tday - np.nan_to_num(last), 0.0), 0.0)
    phi = np.exp(-lam * d)
    return {"f_hat": np.where(has, f * phi, 0.0),
            "f_sd": np.sqrt(np.maximum(np.where(has, P22 * phi * phi + s2f * (1.0 - phi * phi), s2f), 0.0)),
            "L_hat": np.where(has, L, np.nan)}


class Scenario:
    """One availability scenario: release days, the as-of offsets that honour them (cached by day)."""

    def __init__(self, name: str, p: pd.DataFrame, rel: np.ndarray | None, box_rel: np.ndarray | None):
        self.name, self.p = name, p
        self.rel = rel
        self.box_rel = box_rel
        if rel is None:                              # A: the build's snapshots (lf + 1), disk cache allowed
            self.offsets = {tour: P.EditionOffsets(p, tour) for tour in ("atp", "wta")}
        else:
            q = p.assign(rel_s=np.asarray(rel, np.int64))
            self.offsets = {tour: P.EditionOffsets(q, tour, cache=False, release="rel_s") for tour in ("atp", "wta")}


def side_values_v(S: Scenario, t: pd.DataFrame, prm: dict, nowcast: dict | None = None,
                  hist: dict | None = None, y: np.ndarray | None = None) -> pd.DataFrame:
    """f_hat, f_sd, L_hat (and diagnostics) of target sides t under scenario S and the filter constants prm; with
    nowcast = {"W": per-panel-row pseudo deviation (NaN = no nowcast), "R": noise, "a": coefficient on f}, method M2."""
    p = S.p
    if hist is None:
        if nowcast is not None:
            ok = np.isfinite(nowcast["W"])
            hist = histories_rel(p, t, S.rel, S.box_rel, ok)
        else:
            hist = histories_rel(p, t, S.rel)
    idx, ncm = hist["idx"], hist["nc"]
    ok = idx >= 0
    safe = np.maximum(idx, 0)
    spd_idx = np.where(ok & ~ncm, idx, -1)
    G = F.snapshot_gammas(p, t, spd_idx, S.offsets)
    yv = p["y"].to_numpy(float) if y is None else y
    Z = np.where(ok & ~ncm, yv[safe] - G, np.nan)
    DAY = np.where(ok, p["obs"].to_numpy(float)[safe], np.nan)
    nb = p["basis"].astype(str).eq("ks").to_numpy()
    res = pd.DataFrame(index=t.index, columns=["f_hat", "f_sd", "L_hat"], dtype=float)
    tours = t["tour"].to_numpy()
    for tour, base in F.CONST.items():
        sel = np.flatnonzero(tours == tour)
        if not len(sel):
            continue
        pr = dict(base, **{k: v for k, v in prm.items() if k in ("hl",)}) if tour == "atp" else dict(base)
        r_row = np.where(nb, pr["nu_ks"], pr["nu_pts"]) + pr["sigma"] ** 2 / p["n"].to_numpy(float)
        R = np.where(ok[sel], r_row[safe[sel]], np.nan)
        if nowcast is not None:
            Wfull = nowcast["W"][safe[sel]]
            NC = ncm[sel]
            R = np.where(NC, nowcast["R"], R)
            kf = kalman_nc(Z[sel], R, DAY[sel], t["es"].to_numpy(float)[sel], pr, NC, np.where(NC, Wfull, np.nan),
                           nowcast["a"])
        else:
            kf = F.kalman(Z[sel], R, DAY[sel], t["es"].to_numpy(float)[sel], pr)
        for c in ("f_hat", "f_sd", "L_hat"):
            res.iloc[sel, res.columns.get_loc(c)] = kf[c]
    for c in ("hist", "k14", "k28", "last_age"):
        res[c] = hist[c]
    res["n_nowcast"] = hist.get("n_nowcast", np.zeros(len(t), np.int64))
    res["g_sum"] = np.where(ok & ~ncm, G, 0.0).sum(1)
    res["g_abs"] = np.abs(np.where(ok & ~ncm, G, 0.0)).sum(1)
    return res


# ------------------------------------------------------------------------------------------------ targets
def t1_targets(p: pd.DataFrame, years=(T1_TUNE[0], T1_EVAL[1])) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """The auditor's T1: men's timed player-matches as targets; matches with both sides timed (row positions iA, iB)."""
    t = p[p["tour"].eq("atp") & p["year"].between(*years)][
        ["match_id", "side", "player_id", "tour", "tdate", "tournament_id", "round_order", "es", "lf", "obs", "y",
         "year", "edition"]].reset_index(drop=True)
    pos = pd.Series(np.arange(len(t)), index=pd.MultiIndex.from_arrays([t["match_id"], t["side"]]))
    mids = t.loc[t["side"].eq("A"), "match_id"]
    has_b = pd.MultiIndex.from_arrays([mids, np.full(len(mids), "B")]).isin(pos.index)
    mids = mids[has_b].to_numpy()
    iA = pos.reindex(pd.MultiIndex.from_arrays([mids, np.full(len(mids), "A")])).to_numpy().astype(int)
    iB = pos.reindex(pd.MultiIndex.from_arrays([mids, np.full(len(mids), "B")])).to_numpy().astype(int)
    return t, iA, iB


def gate_targets() -> pd.DataFrame:
    """The mechanism gate's targets (men 2022-23, Slams, tour, Finals, Challengers), with the R1 controls (own 364-day
    and two-week box-score rates, the opponent's conceded rates); statistic targets <= 2023 only."""
    from src.eda.serve_speed_tabpfn.design import modeller_gate as MG
    b = MG.box_history((2013, GATE_YEARS[1]), "atp")
    tg = b[b["year"].between(*GATE_YEARS) & b["level"].isin(("GS", "T1000", "T500", "T250", "FIN", "CH"))]
    for _, (n, d) in MG.STATS.items():
        tg = tg[tg[d] > 0]
    tg = tg.reset_index(drop=True)
    tg["tour"] = "atp"
    tm = pd.read_parquet(TIMING, columns=["match_id", "es"])
    tg = tg.drop(columns=[c for c in ("es",) if c in tg.columns]).merge(tm, on="match_id", how="left")
    tg = tg[tg["es"].notna()].reset_index(drop=True)
    tg["es"] = tg["es"].astype(np.int64)
    tg["obs"] = np.floor(tg["obs"]).astype(np.int64)
    orates = MG.own_rates(b, tg)
    tg = tg.join(orates)
    opp_cols = [c for c in tg.columns if c.startswith("c52_")]
    oppv = tg[["match_id", "player_id"] + opp_cols].rename(columns={"player_id": "opponent_id"})
    tg = tg.merge(oppv, on=["match_id", "opponent_id"], how="left", suffixes=("", "_opp"))
    tg["block"] = (tg["es"] // 28).astype(int)
    tg["edition_fe"] = tg["tournament_id"].astype(str) + "|" + tg["qualifying"].astype(str)
    return tg


# ------------------------------------------------------------------------------------------------ readings
def _boot(vals: dict, blocks: np.ndarray, reps: int = 1000, seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    ub = np.unique(blocks)
    ix = [np.flatnonzero(blocks == u) for u in ub]
    out = {}
    draws = {k: [] for k in vals}
    for _ in range(reps):
        s = np.concatenate([ix[j] for j in rng.integers(0, len(ub), len(ub))])
        for k, v in vals.items():
            draws[k].append(v(s))
    for k, v in vals.items():
        est = v(np.arange(len(blocks)))
        out[k] = {"est": float(est), "lo": float(np.percentile(draws[k], 2.5)), "hi": float(np.percentile(draws[k], 97.5))}
    return out


def t1_reading(T: np.ndarray, dLA: np.ndarray, dfs: dict, year: np.ndarray, block: np.ndarray, ok: np.ndarray) -> dict:
    """For each variant's df = f_A - f_B: the information it adds beyond the instant level (A's L_hat difference) about
    the within-match speed difference T. Slope b fitted on the tuning seasons (through 0), then
        gain = MSE(T - dLA) - MSE(T - dLA - b df)   on 2023 (positive = the variant's f_hat adds information)
    and its share of A's gain; intervals: 28-day-block bootstrap (1,000)."""
    tune = ok & (year >= T1_TUNE[0]) & (year <= T1_TUNE[1])
    ev = ok & (year >= T1_EVAL[0]) & (year <= T1_EVAL[1])
    resid = T - dLA
    out = {"matches_tune": int(tune.sum()), "matches_eval": int(ev.sum()), "variants": {}}
    bA = float(np.dot(dfs["A_M0"][tune], resid[tune]) / np.dot(dfs["A_M0"][tune], dfs["A_M0"][tune]))
    e = np.flatnonzero(ev)
    for name, df in dfs.items():
        b = float(np.dot(df[tune], resid[tune]) / max(np.dot(df[tune], df[tune]), 1e-12))
        gtune = float(np.mean(resid[tune] ** 2) - np.mean((resid[tune] - b * df[tune]) ** 2))
        r_e, d_e, dA_e = resid[e], df[e], dfs["A_M0"][e]

        def gain(s, r_e=r_e, d_e=d_e, b=b):
            return np.mean(r_e[s] ** 2) - np.mean((r_e[s] - b * d_e[s]) ** 2)

        def gainA(s, r_e=r_e, dA_e=dA_e):
            return np.mean(r_e[s] ** 2) - np.mean((r_e[s] - bA * dA_e[s]) ** 2)

        def share(s):
            return gain(s) / gainA(s)

        bt = _boot({"gain": gain, "share": share}, block[e])
        out["variants"][name] = {"slope_tune": b, "gain_tune": gtune, "gain_eval": bt["gain"], "share_of_A_eval": bt["share"],
                                 "corr_eval": float(np.corrcoef(d_e, r_e)[0, 1]) if d_e.std() > 0 else 0.0,
                                 "sd_df_eval": float(d_e.std())}
    return out


def gate_reading(tg: pd.DataFrame, fh: dict, LA: np.ndarray) -> dict:
    """Mechanism gate with target-edition fixed effects, men 2022-23 (all rows with controls): pp of the target rate per
    SD of each variant's f_hat, beyond the player's 364-day and two-week box rates, A's level L_hat and the opponent's
    conceded rate. 95% intervals clustered by 28-day blocks. Positive = speed above his norm serves better."""
    from src.eda.serve_speed_tabpfn.design import auditor_centring as AC
    from src.eda.serve_speed_tabpfn.design import modeller_gate as MG
    out = {"rows": {}, "variants": {k: {} for k in fh}}
    for s, (n, d) in MG.STATS.items():
        yv = (tg[n] / tg[d]).to_numpy(float)
        r52 = (tg[f"s52_{n}"] / tg[f"s52_{d}"]).to_numpy(float)
        rew = (tg[f"ew_{n}"] / tg[f"ew_{d}"]).to_numpy(float)
        oc = (tg[f"c52_{n}_opp"] / tg[f"c52_{d}_opp"]).to_numpy(float)
        w = tg[d].to_numpy(float)
        ok = np.isfinite(r52) & np.isfinite(rew) & np.isfinite(oc) & np.isfinite(LA) & np.isfinite(yv)
        g = np.flatnonzero(ok)
        out["rows"][s] = int(len(g))
        ctrl = np.column_stack([r52[g], rew[g], oc[g], LA[g]])
        for name, f in fh.items():
            fz = f[g]
            if fz.std() == 0:
                continue
            beta, se = AC.wls_fe(yv[g], np.column_stack([fz / fz.std(), ctrl]), w[g], tg.loc[g, "edition_fe"].to_numpy(),
                                 tg.loc[g, "block"].to_numpy(), True)
            out["variants"][name][s] = {"pp_per_sd": 100 * beta[0], "lo": 100 * (beta[0] - 1.96 * se[0]),
                                        "hi": 100 * (beta[0] + 1.96 * se[0])}
    for name in fh:
        for s in MG.STATS:
            a = out["variants"]["A_M0"].get(s, {}).get("pp_per_sd")
            v = out["variants"][name].get(s, {}).get("pp_per_sd")
            if a and v is not None:
                out["variants"][name][s]["ratio_to_A"] = v / a
    return out


# ------------------------------------------------------------------------------------------------ the nowcast (M2)
def nowcast_fit(p: pd.DataFrame, S_A: "Scenario", dev: pd.DataFrame) -> dict:
    """OLS on men's timed matches (as targets of the instant filter, scenario A as built), seasons <= 2022, checked on
    2023: u = z - L_hat on [1, f_hat, d_box]; z = y - gamma_edition(es) (the match's own edition at its own es),
    (L_hat, f_hat) the filter's state from the player's earlier rows projected to es. Rows: >= 3 history rows and a
    box deviation. Returns the coefficients, the residual variance and the fit statistics."""
    men = p["tour"].eq("atp").to_numpy() & (p["year"] <= T1_EVAL[1]).to_numpy()
    tg = p[men][["match_id", "side", "player_id", "tour", "tdate", "tournament_id", "round_order", "es", "lf", "obs",
                 "y", "year", "edition"]].reset_index()
    sv = side_values_v(S_A, tg, MEN)
    g = np.full(len(tg), np.nan)
    for day, grp in tg.groupby("es"):
        g[grp.index.to_numpy()] = S_A.offsets["atp"].gamma(grp["edition"].to_numpy(), int(day))
    tg["u"] = tg["y"].to_numpy() - g - sv["L_hat"].to_numpy()
    tg["f"] = sv["f_hat"].to_numpy()
    tg["hist"] = sv["hist"].to_numpy()
    tg = tg.join(dev, on="index")
    ok = np.isfinite(tg[["u", "f"] + DEV].to_numpy()).all(axis=1) & (tg["hist"] >= 3).to_numpy()
    d = tg[ok]
    tr, ck = d[d["year"] <= T1_TUNE[1]], d[d["year"] == T1_EVAL[0]]

    def X(x):
        return np.column_stack([np.ones(len(x)), x["f"].to_numpy()] + [x[c].to_numpy() for c in DEV])

    beta, *_ = np.linalg.lstsq(X(tr), tr["u"].to_numpy(), rcond=None)
    r_tr = tr["u"].to_numpy() - X(tr) @ beta
    r_ck = ck["u"].to_numpy() - X(ck) @ beta
    names = ["c0", "a_f"] + DEV
    box_part_tr = X(tr)[:, 2:] @ beta[2:]
    # the same fit without the box: what the box adds
    b0, *_ = np.linalg.lstsq(X(tr)[:, :2], tr["u"].to_numpy(), rcond=None)
    r_ck0 = ck["u"].to_numpy() - X(ck)[:, :2] @ b0
    den = np.mean((ck["u"] - ck["u"].mean()) ** 2)
    return {"coef": dict(zip(names, map(float, beta))), "rows_tune": int(len(tr)), "rows_check": int(len(ck)),
            "resid_var_tune": float(r_tr.var()), "u_var_tune": float(tr["u"].var()),
            "r2_tune": float(1 - r_tr.var() / tr["u"].var()),
            "r2_check_2023": float(1 - np.mean(r_ck ** 2) / den),
            "r2_check_2023_without_box": float(1 - np.mean(r_ck0 ** 2) / den),
            "resid_var_check_2023": float(np.mean(r_ck ** 2)), "sd_box_part_tune": float(box_part_tr.std())}


def nowcast_inputs(dev: pd.DataFrame, fit: dict) -> np.ndarray:
    """W per panel row: c0 + beta' d_box (NaN where the row has no box deviation)."""
    c = fit["coef"]
    W = c["c0"] + sum(c[k] * dev[k].to_numpy() for k in DEV)
    return np.where(np.isfinite(dev.to_numpy()).all(axis=1), W, np.nan)


# ------------------------------------------------------------------------------------------------ tuning (M1, M2)
def t1_forecast_mse(sv: pd.DataFrame, T: np.ndarray, iA: np.ndarray, iB: np.ndarray, sel: np.ndarray) -> float:
    L, f = sv["L_hat"].to_numpy(float), sv["f_hat"].to_numpy(float)
    F_ = (L[iA] + f[iA]) - (L[iB] + f[iB])
    return float(np.mean((T[sel] - F_[sel]) ** 2))


def info_gain(df: np.ndarray, T: np.ndarray, dLA: np.ndarray, tune: np.ndarray, ev: np.ndarray) -> tuple[float, float]:
    """The column's information on T1: gain = MSE(T - dLA) - MSE(T - dLA - b df), slope b fitted on the tuning
    matches (through 0); returned on the tuning matches and on the check matches (2023, with the tuning slope)."""
    r = T - dLA
    b = float(np.dot(df[tune], r[tune]) / max(np.dot(df[tune], df[tune]), 1e-12))
    g = lambda m: float(np.mean(r[m] ** 2) - np.mean((r[m] - b * df[m]) ** 2))  # noqa: E731
    return g(tune), g(ev)


def _tune(S: "Scenario", t1, iA, iB, T, year, dLA, grid_vals, make) -> dict:
    """Shared grid: for each value, the side values (make(value) -> side_values_v kwargs), then (a) the column's T1
    information gain beyond the instant level (the criterion) and (b) T1's full-forecast MSE under the scenario
    (sensitivity), each on 2019-2022 and on the 2023 check."""
    ok = np.isfinite(dLA)
    tune_i = ok & (year >= T1_TUNE[0]) & (year <= T1_TUNE[1])
    ev_i = ok & (year == T1_EVAL[0])
    rows, sel = {}, None
    for v in grid_vals:
        sv = side_values_v(S, t1, **make(v))
        f = sv["f_hat"].to_numpy(float)
        L = sv["L_hat"].to_numpy(float)
        if sel is None:
            both = np.isfinite(L[iA]) & np.isfinite(L[iB])
            sel = (both & (year >= T1_TUNE[0]) & (year <= T1_TUNE[1]), both & (year == T1_EVAL[0]))
        gt, ge = info_gain(f[iA] - f[iB], T, dLA, tune_i, ev_i)
        rows[v] = {"info_gain_tune": gt, "info_gain_check_2023": ge,
                   "forecast_mse_tune": t1_forecast_mse(sv, T, iA, iB, sel[0]),
                   "forecast_mse_check_2023": t1_forecast_mse(sv, T, iA, iB, sel[1])}
    best = max(rows, key=lambda k: rows[k]["info_gain_tune"])
    best_fc = min(rows, key=lambda k: rows[k]["forecast_mse_tune"])
    return {"best": best, "best_by_forecast_mse": best_fc, "matches_tune": int(tune_i.sum()),
            "matches_check": int(ev_i.sum()), "at_best": rows[best], "grid": {f"{k:g}": r for k, r in rows.items()},
            "on_grid_edge": bool(best in (grid_vals[0], grid_vals[-1]))}


def tune_half_life(S: "Scenario", t1: pd.DataFrame, iA, iB, T, year, dLA) -> dict:
    """M1: the half-life only. Criterion: the column's T1 information beyond the instant level, 2019-2022; 2023 check."""
    hist = histories_rel(S.p, t1, S.rel)
    r = _tune(S, t1, iA, iB, T, year, dLA, HL_GRID, lambda hl: {"prm": dict(MEN, hl=hl), "hist": hist})
    r.update({"scenario": S.name, "hl": float(r["best"]), "at_14": r["grid"]["14"]})
    return r


def tune_nowcast_noise(S: "Scenario", t1: pd.DataFrame, iA, iB, T, year, dLA, W: np.ndarray, a: float,
                       resid_var: float) -> dict:
    """M2: the nowcast rows' noise variance R_nc = mult x the regression's residual variance (<= 2022). Criterion: the
    column's T1 information beyond the instant level, 2019-2022; 2023 check."""
    hist = histories_rel(S.p, t1, S.rel, S.box_rel, np.isfinite(W))
    r = _tune(S, t1, iA, iB, T, year, dLA, RNC_MULT,
              lambda m: {"prm": MEN, "nowcast": {"W": W, "R": m * resid_var, "a": a}, "hist": hist})
    r.update({"scenario": S.name, "mult": float(r["best"]), "R_nc": float(r["best"]) * resid_var})
    return r


# ------------------------------------------------------------------------------------------------ variants
def variant_specs(m1: dict, m2: dict, W: np.ndarray, a: float) -> dict:
    """name -> (scenario, filter constants, nowcast or None). Astrict (lf + 1 applied to own history too) is descriptive."""
    v = {"A_M0": ("A", MEN, None), "Astrict_M0": ("Astrict", MEN, None)}
    for k in LAGS:
        v[f"{k}_M0"] = (k, MEN, None)
    v["B_M0"] = ("B", MEN, None)
    for s in ("B", "L7"):
        v[f"{s}_M1"] = (s, dict(MEN, hl=m1[s]["hl"]), None)
        v[f"{s}_M2"] = (s, MEN, {"W": W, "R": m2[s]["R_nc"], "a": a})
    return v


def frame_differences(sv: pd.DataFrame, t: pd.DataFrame) -> pd.DataFrame:
    a = t["side"].eq("A").to_numpy()
    assert (t.loc[a, "match_id"].to_numpy() == t.loc[~a, "match_id"].to_numpy()).all()
    return pd.DataFrame({"match_id": t.loc[a, "match_id"].to_numpy(), "season": t.loc[a, "season"].to_numpy(),
                         "d": sv.loc[a, "f_hat"].to_numpy() - sv.loc[~a, "f_hat"].to_numpy()})


def standardise(d: pd.Series, season: pd.Series) -> tuple[np.ndarray, float]:
    sd = float(d[season.between(*SD_SEASONS)].std(ddof=1))
    return np.clip(d.to_numpy() / sd, -F.CLIP, F.CLIP), sd


# ------------------------------------------------------------------------------------------------ Probe B
def probe_days(keys: pd.DataFrame, n_random: int = 6, seed: int = 20261010) -> list[float]:
    """The timing probe's four days, each Slam's second Wednesday in 2024-26 within the frame, and random days."""
    rng = np.random.default_rng(seed)
    fixed = [float((pd.Timestamp(d) - pd.Timestamp("1970-01-01")).days)
             for d in ("2023-09-06", "2024-01-24", "2024-07-10", "2024-08-14")]
    slams = F.slam_second_wednesdays(keys)
    es = keys["es"].to_numpy(float)
    rand = sorted(rng.uniform(float(es.min()) + 400.0, float(es.max()) - 1.0, n_random).round().tolist())
    return sorted(set(fixed) | set(slams) | set(rand))


def probe_b_latency(name: str, scen: str, p: pd.DataFrame, rd: pd.DataFrame, tm: pd.DataFrame, prm: dict,
                    nowcast_parts: dict | None, days: list[float], seed: int = 20261009) -> dict:
    """Probe B under a scenario's release days: on day D every speed row released after D (release > D) is noised in
    the filter and the snapshot inputs; for the nowcast, every box score released after D is redrawn too (aces, double
    faults, first- and second-serve points won). No value of any men's frame side with es <= D may move (f_hat, f_sd,
    L_hat, the gamma used). Leaky control: the same noise with rows admitted by lf + 1 (scenario A's release) in the
    history and the snapshots: some side with es <= D must move."""
    rng = np.random.default_rng(seed)
    rel = rd[scen].to_numpy(np.int64)
    boxr = rd["box"].to_numpy(np.int64)
    lk_rel = p["lf"].to_numpy(np.int64) + 1

    def nowcast_for(panel, box):
        if nowcast_parts is None:
            return None
        Wq = nowcast_inputs(box_deviations(panel, box), nowcast_parts["fit"])
        return {"W": Wq, "R": nowcast_parts["R"], "a": nowcast_parts["fit"]["coef"]["a_f"]}

    box0 = nowcast_parts["box"] if nowcast_parts else None
    nc0 = nowcast_for(p, box0)
    base = side_values_v(Scenario(scen, p, rel, boxr), tm, prm, nowcast=nc0)
    base_lk = side_values_v(Scenario("leaky", p, lk_rel, boxr), tm, prm, nowcast=nc0)
    es = tm["es"].to_numpy(float)
    cols = ["f_hat", "f_sd", "L_hat", "g_sum", "g_abs"]
    recs, moved, leaky_total = [], 0, 0
    for D in days:
        q = p.copy()
        late = rel > D
        q.loc[late, "y"] = rng.uniform(100.0, 250.0, int(late.sum()))
        nc = None
        if nowcast_parts is not None:
            bq = box0.copy()
            bl = nowcast_parts["box_rel"] > D
            for c in ("ace", "df", "first_won", "second_won"):
                bq.loc[bl, c] = np.floor(rng.uniform(0.0, 0.5, int(bl.sum())) * bq.loc[bl, "svpt"].to_numpy())
            nc = nowcast_for(q, bq)
        chk = np.flatnonzero(es <= D)
        got = side_values_v(Scenario(scen, q, rel, boxr), tm.iloc[chk].reset_index(drop=True), prm, nowcast=nc)
        b0 = base.iloc[chk].reset_index(drop=True)
        diff = np.zeros(len(chk), bool)
        for c in cols:
            x0, x1 = b0[c].to_numpy(float), got[c].to_numpy(float)
            diff |= ~(np.isclose(x0, x1, rtol=0.0, atol=1e-12) | (np.isnan(x0) & np.isnan(x1)))
        moved += int(diff.sum())
        near = np.flatnonzero((es <= D) & (es >= D - 28.0))
        l1 = side_values_v(Scenario("leaky", q, lk_rel, boxr), tm.iloc[near].reset_index(drop=True), prm, nowcast=nc)
        l0 = base_lk.iloc[near].reset_index(drop=True)
        lm = ~(np.isclose(l0["f_hat"].to_numpy(), l1["f_hat"].to_numpy(), rtol=0.0, atol=1e-12)
               & np.isclose(l0["g_sum"].to_numpy(), l1["g_sum"].to_numpy(), rtol=0.0, atol=1e-12))
        leaky_total += int(lm.sum())
        recs.append({"day": D, "date": str(pd.Timestamp("1970-01-01") + pd.Timedelta(days=D))[:10],
                     "sides_checked": int(len(chk)), "moved": int(diff.sum()), "leaky_sides": int(len(near)),
                     "leaky_moved": int(lm.sum())})
        log(f"  probe B {name} {recs[-1]['date']}: checked {len(chk)}, moved {int(diff.sum())}; leaky "
            f"{int(lm.sum())}/{len(near)}")
    passed = moved == 0 and leaky_total > 0
    return {"variant": name, "scenario": scen, "days": len(days), "values_checked": cols, "tolerance": 1e-12,
            "check_set": "men's frame sides with es <= D", "moved": moved, "leaky_control_moved": leaky_total,
            "leaky_control": "rows admitted by lf + 1 in history and snapshots, noise by the scenario's release",
            "pass": bool(passed), "per_day": recs}


# ------------------------------------------------------------------------------------------------ main
def build_all(probes: bool = True) -> dict:
    log("inputs")
    p = load_panel()
    keys = P.load_frame_keys()
    t = F.side_targets(keys)
    tm = t[t["tour"].eq("atp")].reset_index(drop=True)
    avail = load_availability()
    rd = release_days(p, avail)
    box = box_table("atp")
    dev = box_deviations(p, box)
    boxrel = box_release_of(box, avail)
    scen = {"A": Scenario("A", p, None, None)}
    for k in ["Astrict", *LAGS, "B"]:
        scen[k] = Scenario(k, p, rd[k].to_numpy(np.int64), rd["box"].to_numpy(np.int64))
    log(f"panel {len(p)}; men's frame sides {len(tm)}; men's panel rows with a box deviation "
        f"{int(np.isfinite(dev.to_numpy()).all(axis=1)[p['tour'].eq('atp').to_numpy()].sum())}")
    fit = nowcast_fit(p, scen["A"], dev)
    W = nowcast_inputs(dev, fit)
    a = fit["coef"]["a_f"]
    log(f"nowcast fit: {json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in fit['coef'].items()})}; "
        f"R2 tune {fit['r2_tune']:.3f}, 2023 {fit['r2_check_2023']:.3f} (without box {fit['r2_check_2023_without_box']:.3f})")
    t1, iA, iB = t1_targets(p)
    T = t1["y"].to_numpy(float)[iA] - t1["y"].to_numpy(float)[iB]
    year = t1["year"].to_numpy()[iA]
    block = (t1["es"].to_numpy()[iA] // 28).astype(int)
    # the instant level (scenario A as built): the reference level of every T1 reading and of the tuning criterion
    LA = side_values_v(scen["A"], t1, MEN)["L_hat"].to_numpy(float)
    dLA = LA[iA] - LA[iB]
    ok = np.isfinite(dLA)
    m1 = {s: tune_half_life(scen[s], t1, iA, iB, T, year, dLA) for s in ("B", "L7")}
    log(f"M1 half-lives: { {s: m1[s]['hl'] for s in m1} } (by forecast MSE: "
        f"{ {s: m1[s]['best_by_forecast_mse'] for s in m1} })")
    m2 = {s: tune_nowcast_noise(scen[s], t1, iA, iB, T, year, dLA, W, a, fit["resid_var_tune"]) for s in ("B", "L7")}
    log(f"M2 noise: { {s: (m2[s]['mult'], round(m2[s]['R_nc'], 2)) for s in m2} } (by forecast MSE: "
        f"{ {s: m2[s]['best_by_forecast_mse'] for s in m2} })")
    specs = variant_specs(m1, m2, W, a)
    gt = gate_targets()
    log(f"gate targets {len(gt)}")
    frame, t1v, gatev = {}, {}, {}
    for name, (s, prm, nc) in specs.items():
        S = scen[s]
        frame[name] = side_values_v(S, tm, prm, nowcast=nc)
        t1v[name] = side_values_v(S, t1, prm, nowcast=nc)
        gatev[name] = side_values_v(S, gt, prm, nowcast=nc)
        log(f"  {name}: built")
    # readings (result-free, <= 2023)
    assert np.allclose(t1v["A_M0"]["L_hat"].to_numpy(float), LA, equal_nan=True)
    dfs = {n: (v["f_hat"].to_numpy(float)[iA] - v["f_hat"].to_numpy(float)[iB]) for n, v in t1v.items()}
    t1r = t1_reading(T, dLA, dfs, year, block, ok)
    gr = gate_reading(gt, {n: v["f_hat"].to_numpy(float) for n, v in gatev.items()},
                      gatev["A_M0"]["L_hat"].to_numpy(float))
    # the columns
    base = keys[["match_id", "tour", "season"]].copy()
    cols, sds, values = {}, {}, {}
    A_ref = None
    for name in specs:
        d = frame_differences(frame[name], tm)
        z, sd = standardise(d["d"], d["season"])
        sds[name] = sd
        col = pd.Series(z, index=d["match_id"].to_numpy())
        cols[name] = base["match_id"].map(col).fillna(0.0).to_numpy()
        late = d["season"].between(2024, 2026).to_numpy()
        if name == "A_M0":
            A_ref = pd.Series(z, index=d["match_id"].to_numpy())
        zz = pd.Series(z, index=d["match_id"].to_numpy())
        values[name] = {"corr_with_A_2024_26": float(np.corrcoef(zz[late], A_ref.reindex(zz.index)[late])[0, 1]),
                        "sd_km_h_2024_26": float(d.loc[late, "d"].std(ddof=1)), "sd_km_h_2022_23": sd,
                        "nonzero_share_2024_26": float((z[late] != 0).mean()),
                        "abs_ge_0.05_share_2024_26": float((np.abs(z[late]) >= 0.05).mean()),
                        "clipped_2024_26": int((np.abs(z[late]) >= F.CLIP).sum())}
        nn = frame[name]["n_nowcast"].to_numpy()          # frame sides: the A block, then the B block
        values[name]["sides_with_a_nowcast_row_2024_26"] = float((nn[np.r_[late, late]] > 0).mean())
    out = base.copy()
    for name in specs:
        out[f"spd_{name}"] = cols[name]
    out.loc[out["tour"].eq("wta"), [f"spd_{n}" for n in specs]] = 0.0
    res = {"p": p, "keys": keys, "tm": tm, "rd": rd, "box": box, "boxrel": boxrel, "fit": fit, "m1": m1, "m2": m2,
           "specs": specs, "sds": sds, "values": values, "t1": t1r, "gate": gr, "out": out, "scen": scen, "W": W,
           "frame": frame}
    res["probes"] = {}
    if probes:
        days = probe_days(keys)
        log(f"Probe B on {len(days)} days")
        res["probes"]["B_M0"] = probe_b_latency("B_M0", "B", p, rd, tm, MEN, None, days)
        res["probes"]["B_M2"] = probe_b_latency(
            "B_M2", "B", p, rd, tm, MEN, {"fit": fit, "box": box, "box_rel": boxrel, "R": m2["B"]["R_nc"]}, days)
    return res


def write(res: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    out = res["out"]
    assert len(out) == 63737 and out["match_id"].is_unique
    for c in [c for c in out.columns if c.startswith("spd_")]:
        assert out[c].notna().all() and (out[c].abs() <= F.CLIP).all()
    out[["match_id"] + [c for c in out.columns if c.startswith("spd_")]].to_parquet(VARIANTS, index=False)
    meta = {
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "plan": "data/studies/serve_speed_tabpfn/latency/plan.md", "reads_results": False,
        "inputs": {"panel_sha256": F.sha256(F.PANEL_FILE), "availability_sha256": F.sha256(AVAIL),
                   "features_parquet_sha256": F.sha256(F.FEATURES)},
        "code_sha256": {"features_latency.py": F.sha256(Path(__file__)), "features.py": F.sha256(Path(F.__file__))},
        "variants_parquet_sha256": F.sha256(VARIANTS),
        "constants": {"men": MEN, "hl_grid": list(HL_GRID), "r_nc_multipliers": list(RNC_MULT), "box_deviations": DEV,
                      "norm": {"window_days": 364, "min_service_points": NORM_MIN_SVPT, "min_matches": NORM_MIN_MATCHES},
                      "t1_tune": list(T1_TUNE), "t1_eval": list(T1_EVAL), "sd_seasons": list(SD_SEASONS),
                      "clip": F.CLIP},
        "scenarios": {"A": "as built (features.py): own history by own order, snapshots release lf + 1",
                      "Astrict": "descriptive: lf + 1 applied to own history too (not the instant reference)", **{k: f"lf + 1 + {v}" for k, v in LAGS.items()},
                      "B": "availability.parquet release_B (engineer)", "box": "availability.parquet box_release"},
        "columns": {f"spd_{n}": {"scenario": s, "half_life": prm["hl"], "nowcast": nc is not None}
                    for n, (s, prm, nc) in res["specs"].items()},
        "standardisation_sd_km_h": res["sds"],
        "nowcast": {"fit": res["fit"], "noise": {s: {k: v for k, v in res["m2"][s].items() if k != "grid"}
                                                 for s in res["m2"]},
                    "pseudo_observation": "z_nc = L + a_f * f_pred + c0 + sum(beta_k * d_k); variance R_nc"},
        "m1": res["m1"], "m2": res["m2"],
        "probes": res["probes"], "probes_pass": bool(res["probes"]) and all(v["pass"] for v in res["probes"].values()),
    }
    META.write_text(json.dumps(meta, indent=1, default=float) + "\n", encoding="utf-8")
    READINGS.write_text(json.dumps({"t1": res["t1"], "gate": res["gate"], "values_2024_26": res["values"],
                                    "key": {"t1": "within-match A - B first-serve speed (km/h^2), men; gain = MSE(T - dL_A) - "
                                                  "MSE(T - dL_A - b df), slope b from 2019-22, read on 2023; positive = the "
                                                  "variant's f_hat adds information; share = gain / A's gain",
                                            "gate": "pp of the rate per SD of the variant's f_hat, men 2022-23, target-edition "
                                                    "fixed effects, controls as R1 + A's level; positive = speed above his "
                                                    "norm serves better; 95% intervals clustered by 28-day blocks"}},
                                   indent=1, default=float) + "\n", encoding="utf-8")
    log(f"wrote {VARIANTS.name}, {META.name}, {READINGS.name}; probes pass: {meta['probes_pass']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-probes", action="store_true")
    a = ap.parse_args()
    res = build_all(probes=not a.no_probes)
    write(res)


if __name__ == "__main__":
    main()
