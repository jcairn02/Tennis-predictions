"""Serve-speed TabPFN study, R3 build C3 (agent 2, the modeller): the speed-state columns of the model frame.

Spec: data/studies/serve_speed_tabpfn/design/2_audit.md, section (c) C3 and C7 (binding). Reads no match result: the
panel and the frame keys come from the engineer's panel.py (fixed API); Stage 0's `order` is read with an explicit
column list for Probe A only.

For each frame side P (the frame's own player ids give the orientation) before match m:

    history   P's panel rows (use) with tdate < tdate_m, or the same tournament_id with round_order < round_order_m,
              and obs >= es_m - 364, in own order (tdate, tournament_id, round_order)
    centred   z_h = y_h - gamma_{edition(h)}(es_m): ONE as-of snapshot per target (panel.EditionOffsets at the target's
              own earliest start), the filter re-run per target; no state is shared between targets
    noise     R_h = nu_{basis(h)} + sigma^2 / n_h
    filter    level L (random walk, q per day; diffuse start L = 0, P11 = 1e6) and fast state f (Ornstein-Uhlenbeck,
              half-life h, stationary variance s2f; start f = 0, P22 = s2f); per row: predict over
              D = max(obs_h - obs_prev, 0) (not before the first row), update with the innovation clipped at c
              predictive SDs; projected to es_m: f_hat = 2^(-D/h) f, sd^2 = phi^2 P22 + s2f (1 - phi^2)
    none      f_hat = 0, sd = sqrt(s2f), L_hat = NaN

Columns (one row per frame match, all of them):
    spd_f      clip((f_hat_A - f_hat_B) / s_f, -4, 4); women 0                                   (arm A1, diff)
    spd_f_all  the same with the women's own values (women's constants), the same s_f            (arm A3, diff)
    spd_raw    clip(x_raw / 5.998, -4, 4): the registered statistic on this panel (raw y, n-weighted means over own
               earlier rows with obs_m - obs_h <= 14 and <= 364), A - B; men with both 14-day windows, else NaN (A2)
    s_f        the SD of the unclipped f_hat_A - f_hat_B over men's frame matches of 2022-23 (values <= 2023 only)
Per side (suffix _a / _b): f_hat, f_sd, L_hat, hist (rows), k14, k28 (rows within 14 / 28 days of es), last_age,
ks28 / pts28 (the basis mix of the 28-day history), x_raw (km/h); per match: id_conflict, flipped.

Probes (C7; the fit runner refuses a feature file whose metadata lacks them or whose pass flags are false):
    A  own history: >= 25 cuts in Stage 0 `order` (>= 10 in 2024-26) over 5,000 frame sides; y of rows with
       order >= cut replaced by U(100, 250) in the filter input only (snapshots held at the clean build); no side
       value of a target with order <= cut may move (1e-12). Leaky control: each target's own row added to its
       history -> targets at the cut must move in >= 80% of cuts.
    B  clock: >= 25 cut days D (match_timing/probe.py's four, each Slam's second Wednesday in 2024-26 within the
       frame, random days); y of rows with es > D noised in the filter AND the snapshot inputs; no value of any frame
       side with lf <= D may move, f_hat and the gamma it used alike. Leaky control: snapshots that release rows at
       their tournament date (lf := tdate - 1) must move some such side.

Run: ./python.sh src/eda/serve_speed_tabpfn/features.py [--no-probes] [--standin]
Writes data/studies/serve_speed_tabpfn/features/speed.parquet and speed_meta.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "features"
FEATURES = OUT / "speed.parquet"
META = OUT / "speed_meta.json"
PANEL_FILE = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "speed_panel.parquet"
STAGE0 = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"

# frozen constants (2_audit.md C3; tuned on speeds <= 2022, modeller_state.py; women's for A3 only)
MEN = {"hl": 14.0, "s2f": 12.0, "q": 4.0 / 365.0, "c": 2.0, "nu_pts": 7.0, "nu_ks": 8.0, "sigma": 13.49}
WOMEN = {"hl": 14.0, "s2f": 12.0, "q": 4.0 / 365.0, "c": 4.0, "nu_pts": 14.0, "nu_ks": 10.0, "sigma": 10.72}
CONST = {"atp": MEN, "wta": WOMEN}
C2_FROZEN = {"tau2": 22.0, "s": 12.4, "K": 25.0, "window_days": 364}
WINDOW = 364.0
RAW_SD = 5.998
CLIP = 4.0
SF_SEASONS = (2022, 2023)
BIG = 1e6
SIDE_COLS = ["f_hat", "f_sd", "L_hat", "hist", "k14", "k28", "last_age", "ks28", "pts28", "x_raw"]
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def panel_module(standin: bool = False):
    if standin:
        return importlib.import_module("src.eda.serve_speed_tabpfn.design.modeller_panel_standin")
    return importlib.import_module("src.eda.serve_speed_tabpfn.panel")


def sha256(path: Path) -> str | None:
    if path is None or not Path(path).exists():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------ inputs
def prepare_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """The use rows in own order, with integer codes for the comparisons."""
    p = panel[panel["use"].astype(bool)].copy() if "use" in panel.columns else panel.copy()
    # own order; rows sharing (tdate, tournament_id, round_order) (round robins) are ordered by obs, then match id
    p = p.sort_values(["player_id", "tdate", "tournament_id", "round_order", "obs", "match_id"],
                      kind="mergesort").reset_index(drop=True)
    return p


def side_targets(keys: pd.DataFrame) -> pd.DataFrame:
    """Two rows per frame match (A then B), keyed by the frame's own player ids."""
    base = ["match_id", "rebuilt_id", "tour", "season", "es", "lf", "obs", "tdate", "tournament_id", "round_order",
            "id_conflict", "flipped"]
    a = keys[base].assign(side="A", player_id=keys["player_a_id"].to_numpy())
    b = keys[base].assign(side="B", player_id=keys["player_b_id"].to_numpy())
    t = pd.concat([a, b], ignore_index=True)
    return t


def histories(p: pd.DataFrame, t: pd.DataFrame, extra_own: np.ndarray | None = None) -> dict:
    """Per target: the panel rows of its history (padded matrix of positions into p, -1 = none, left-aligned, own
    order) and the side diagnostics; the registered windows' n-weighted sums. extra_own (positions into p or -1) appends
    a row to each target's history (the leaky control of Probe A only)."""
    n = len(t)
    tid_codes, tid_u = pd.factorize(pd.concat([p["tournament_id"].astype(str), t["tournament_id"].astype(str)]))
    p_tid, t_tid = tid_codes[:len(p)], tid_codes[len(p):]
    p_td, p_ro = p["tdate"].to_numpy(float), p["round_order"].to_numpy(float)
    p_ob, p_y, p_n = p["obs"].to_numpy(float), p["y"].to_numpy(float), p["n"].to_numpy(float)
    p_ks = p["basis"].astype(str).eq("ks").to_numpy()
    t_td, t_ro = t["tdate"].to_numpy(float), t["round_order"].to_numpy(float)
    t_es, t_ob = t["es"].to_numpy(float), t["obs"].to_numpy(float)
    groups = p.groupby("player_id", sort=False).indices
    lists: list = [np.empty(0, np.int64)] * n
    k14 = np.zeros(n, np.int64); k28 = np.zeros(n, np.int64); ks28 = np.zeros(n, np.int64); pts28 = np.zeros(n, np.int64)
    last_age = np.full(n, np.nan)
    s14 = np.zeros(n); w14 = np.zeros(n); s364 = np.zeros(n); w364 = np.zeros(n)
    valid_t = t["player_id"].notna().to_numpy() & np.isfinite(t_es) & np.isfinite(t_td)
    tg = pd.Series(np.arange(n))[valid_t].groupby(t["player_id"].to_numpy()[valid_t]).indices
    for pid, ti_local in tg.items():
        ti = np.arange(n)[valid_t][ti_local]
        r = groups.get(pid)
        if r is None:
            continue
        td, tid, ro, ob = p_td[r], p_tid[r], p_ro[r], p_ob[r]
        earlier = (td[None, :] < t_td[ti, None]) | ((tid[None, :] == t_tid[ti, None]) & (ro[None, :] < t_ro[ti, None]))
        inwin = ob[None, :] >= (t_es[ti, None] - WINDOW)
        m = earlier & inwin
        age = t_ob[ti, None] - ob[None, :]
        m14r, m364r = earlier & (age <= 14.0), earlier & (age <= WINDOW)
        nw = p_n[r][None, :]
        yw = (p_n[r] * p_y[r])[None, :]
        s14[ti], w14[ti] = (m14r * yw).sum(1), (m14r * nw).sum(1)
        s364[ti], w364[ti] = (m364r * yw).sum(1), (m364r * nw).sum(1)
        near14 = m & (ob[None, :] >= t_es[ti, None] - 14.0)
        near28 = m & (ob[None, :] >= t_es[ti, None] - 28.0)
        k14[ti], k28[ti] = near14.sum(1), near28.sum(1)
        ks28[ti] = (near28 & p_ks[r][None, :]).sum(1)
        pts28[ti] = (near28 & ~p_ks[r][None, :]).sum(1)
        anyh = m.any(1)
        lastob = np.where(m, ob[None, :], -np.inf).max(1)
        last_age[ti] = np.where(anyh, t_es[ti] - lastob, np.nan)
        for j, i in enumerate(ti):
            lists[i] = r[m[j]]
    if extra_own is not None:
        lists = [np.append(x, e) if e >= 0 else x for x, e in zip(lists, extra_own)]
    H = max(1, max((len(x) for x in lists), default=1))
    idx = np.full((n, H), -1, np.int64)
    for i, x in enumerate(lists):
        if len(x):
            idx[i, :len(x)] = x
    x_raw = np.where(w14 > 0, s14 / np.where(w14 > 0, w14, 1) - s364 / np.where(w364 > 0, w364, 1), np.nan)
    return {"idx": idx, "k14": k14, "k28": k28, "ks28": ks28, "pts28": pts28, "last_age": last_age,
            "hist": (idx >= 0).sum(1), "x_raw": x_raw}


def snapshot_gammas(p: pd.DataFrame, t: pd.DataFrame, idx: np.ndarray, offsets: dict) -> np.ndarray:
    """G (n_t, H): gamma of each history row's edition in the snapshot at the TARGET's es (one snapshot per target)."""
    G = np.full(idx.shape, np.nan)
    ed = p["edition"].astype(str).to_numpy()
    ok = idx >= 0
    tt = t["tour"].to_numpy()
    es = t["es"].to_numpy(float)
    has = ok.any(1)
    for tour in np.unique(tt[has]):
        eo = offsets[tour]
        sel = np.flatnonzero(has & (tt == tour))
        for day in np.unique(es[sel]):
            rows = sel[es[sel] == day]
            sub = idx[rows]
            m = sub >= 0
            g = np.asarray(eo.gamma(ed[sub[m]], float(day)), dtype=float)
            blk = np.full(sub.shape, np.nan)
            blk[m] = g
            G[rows] = blk
    return G


def kalman(Z: np.ndarray, R: np.ndarray, DAY: np.ndarray, tday: np.ndarray, prm: dict) -> dict:
    """The two-state robust filter over left-aligned histories (row k of every target processed together)."""
    nt, H = Z.shape
    lam = math.log(2.0) / prm["hl"]
    s2f, q, c = prm["s2f"], prm["q"], prm["c"]
    L = np.zeros(nt); f = np.zeros(nt)
    P11 = np.full(nt, BIG); P12 = np.zeros(nt); P22 = np.full(nt, s2f)
    last = np.full(nt, np.nan)
    for k in range(H):
        act = np.isfinite(Z[:, k])
        if not act.any():
            break
        if k == 0:
            dt_ = np.zeros(nt)
        else:
            dt_ = np.where(act, np.maximum(DAY[:, k] - last, 0.0), 0.0)
        phi = np.exp(-lam * dt_)
        fp = f * phi
        P11p = P11 + q * dt_
        P12p = P12 * phi
        P22p = P22 * phi * phi + s2f * (1.0 - phi * phi)
        z = np.where(act, Z[:, k], 0.0)
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
    has = np.isfinite(last)
    d = np.where(has, np.maximum(tday - np.nan_to_num(last), 0.0), 0.0)
    phi = np.exp(-lam * d)
    f_hat = np.where(has, f * phi, 0.0)
    var = np.where(has, P22 * phi * phi + s2f * (1.0 - phi * phi), s2f)
    return {"f_hat": f_hat, "f_sd": np.sqrt(np.maximum(var, 0.0)), "L_hat": np.where(has, L, np.nan)}


def side_values(p: pd.DataFrame, t: pd.DataFrame, offsets: dict, hist: dict | None = None,
                y_override: np.ndarray | None = None, G: np.ndarray | None = None) -> pd.DataFrame:
    """Every side value of the targets t. y_override replaces the panel's y in the FILTER input (and the registered
    windows) only; G (precomputed snapshot gammas) holds the snapshots fixed."""
    hist = hist if hist is not None else histories(p, t)
    idx = hist["idx"]
    ok = idx >= 0
    safe = np.maximum(idx, 0)
    y = p["y"].to_numpy(float) if y_override is None else y_override
    G = G if G is not None else snapshot_gammas(p, t, idx, offsets)
    Z = np.where(ok, y[safe] - G, np.nan)
    DAY = np.where(ok, p["obs"].to_numpy(float)[safe], np.nan)
    nb = np.where(p["basis"].astype(str).eq("ks").to_numpy(), 1, 0)
    out = {}
    res = pd.DataFrame(index=t.index)
    for c in ("f_hat", "f_sd", "L_hat"):
        res[c] = np.nan
    tours = t["tour"].to_numpy()
    for tour, prm in CONST.items():
        sel = np.flatnonzero(tours == tour)
        if not len(sel):
            continue
        nu = np.where(nb == 1, prm["nu_ks"], prm["nu_pts"])
        r_row = nu + prm["sigma"] ** 2 / p["n"].to_numpy(float)
        R = np.where(ok[sel], r_row[safe[sel]], np.nan)
        kf = kalman(Z[sel], R, DAY[sel], t["es"].to_numpy(float)[sel], prm)
        for c in ("f_hat", "f_sd", "L_hat"):
            res.iloc[sel, res.columns.get_loc(c)] = kf[c]
    if y_override is not None:
        hh = dict(hist)
        # the registered windows read y too: recompute their sums with the override
        hh = _raw_with(p, t, hist, y)
        res["x_raw"] = hh
    else:
        res["x_raw"] = hist["x_raw"]
    for c in ("hist", "k14", "k28", "last_age", "ks28", "pts28"):
        res[c] = hist[c]
    res["g_sum"] = np.where(ok, G, 0.0).sum(1)
    res["g_abs"] = np.abs(np.where(ok, G, 0.0)).sum(1)
    return res


def _raw_with(p: pd.DataFrame, t: pd.DataFrame, hist: dict, y: np.ndarray) -> np.ndarray:
    """The registered x_raw with another y vector (probes): recomputed through histories() on a copy of p."""
    q = p.copy()
    q["y"] = y
    return histories(q, t)["x_raw"]


# ------------------------------------------------------------------------------------------------ the columns
def columns(t: pd.DataFrame, sv: pd.DataFrame, s_f: float | None) -> tuple[pd.DataFrame, float]:
    """One row per match (A row first): the three columns and the side diagnostics. s_f None = computed here from
    men's 2022-23 frame matches (values <= 2023 only)."""
    a = t["side"].eq("A").to_numpy()
    A = pd.concat([t.loc[a, ["match_id", "tour", "season", "id_conflict", "flipped"]].reset_index(drop=True),
                   sv.loc[a, SIDE_COLS].reset_index(drop=True).add_suffix("_a")], axis=1)
    B = pd.concat([t.loc[~a, ["match_id"]].reset_index(drop=True),
                   sv.loc[~a, SIDE_COLS].reset_index(drop=True).add_suffix("_b")], axis=1)
    assert (A["match_id"].to_numpy() == B["match_id"].to_numpy()).all()
    m = pd.concat([A, B.drop(columns="match_id")], axis=1)
    d = m["f_hat_a"] - m["f_hat_b"]
    men = m["tour"].eq("atp")
    if s_f is None:
        s_f = float(d[men & m["season"].between(*SF_SEASONS)].std(ddof=1))
    m["spd_f"] = np.where(men, np.clip(d / s_f, -CLIP, CLIP), 0.0)
    m["spd_f_all"] = np.clip(d / s_f, -CLIP, CLIP)
    xr = m["x_raw_a"] - m["x_raw_b"]
    m["spd_raw"] = np.where(men & xr.notna(), np.clip(xr / RAW_SD, -CLIP, CLIP), np.nan)
    m["spd_f_unclipped_km_h"] = d
    lead = ["match_id", "tour", "season", "spd_f", "spd_f_all", "spd_raw"]
    return m[lead + [c for c in m.columns if c not in lead]], s_f


def build(P, standin: bool = False, keys: pd.DataFrame | None = None, s_f: float | None = None) -> dict:
    log("panel and frame keys")
    panel = P.load_panel(use_only=True)
    p = prepare_panel(panel)
    keys = P.load_frame_keys() if keys is None else keys
    t = side_targets(keys)
    log(f"panel rows {len(p)}; frame matches {len(keys)}; sides {len(t)}")
    offsets = {tour: P.EditionOffsets(p, tour) for tour in ("atp", "wta")}
    hist = histories(p, t)
    log(f"histories built (max rows {hist['idx'].shape[1]})")
    G = snapshot_gammas(p, t, hist["idx"], offsets)
    log("snapshots read")
    sv = side_values(p, t, offsets, hist=hist, G=G)
    m, s_f = columns(t, sv, s_f)
    log(f"columns built; s_f = {s_f:.4f} km/h")
    return {"p": p, "t": t, "keys": keys, "offsets": offsets, "hist": hist, "G": G, "sv": sv, "m": m, "s_f": s_f}


# ------------------------------------------------------------------------------------------------ probes
def stage0_order(ids: pd.Series) -> pd.Series:
    o = pd.read_parquet(STAGE0, columns=["match_id", "order"])
    return ids.map(o.set_index("match_id")["order"])


def probe_a(B: dict, n_sides: int = 5000, n_cuts: int = 26, n_late: int = 12, seed: int = 20261007) -> dict:
    """Own-history probe in Stage 0 order (see the module docstring)."""
    rng = np.random.default_rng(seed)
    p, t, offsets = B["p"], B["t"], B["offsets"]
    p_order = stage0_order(p["match_id"]).to_numpy(float)
    t_order = stage0_order(t["rebuilt_id"]).to_numpy(float)
    # each target's own panel row (for the leaky control), keyed by (rebuilt match id, player id)
    key = pd.Series(np.arange(len(p)), index=pd.MultiIndex.from_arrays([p["match_id"].astype(str),
                                                                         p["player_id"].astype(str)]))
    key = key[~key.index.duplicated()]
    look = pd.MultiIndex.from_arrays([t["rebuilt_id"].astype(str), t["player_id"].astype(str)])
    own = pd.Series(key.reindex(look).fillna(-1).astype(np.int64).to_numpy(), index=t.index)
    ok = np.isfinite(t_order) & t["es"].notna().to_numpy()
    pool = np.flatnonzero(ok)
    late = np.flatnonzero(ok & t["season"].between(2024, 2026).to_numpy())
    n_late_sides = min(1500, n_sides // 3)
    other = np.setdiff1d(pool, late)
    pick = np.sort(np.concatenate([rng.choice(other, n_sides - n_late_sides, replace=False),
                                   rng.choice(late, n_late_sides, replace=False)]))
    S = t.iloc[pick].reset_index(drop=True)
    S_order = t_order[pick]
    S_own = own.to_numpy()[pick]
    hist = histories(p, S)
    G = snapshot_gammas(p, S, hist["idx"], offsets)
    base = side_values(p, S, offsets, hist=hist, G=G)
    # leaky control: the target's own row appended to its history
    hist_l = histories(p, S, extra_own=S_own)
    G_l = snapshot_gammas(p, S, hist_l["idx"], offsets)
    base_l = side_values(p, S, offsets, hist=hist_l, G=G_l)
    timed = S_own >= 0
    cand_late = np.unique(S_order[timed & S["season"].between(2024, 2026).to_numpy()])
    cand_all = np.unique(S_order[timed])
    cuts = np.concatenate([rng.choice(cand_late, n_late, replace=False),
                           rng.choice(np.setdiff1d(cand_all, cand_late), n_cuts - n_late, replace=False)])
    y0 = p["y"].to_numpy(float)
    recs, moved_before, moved_at, leaky_hits = [], 0, 0, 0
    cols = ["f_hat", "f_sd", "L_hat", "x_raw"]
    for c in np.sort(cuts):
        y = y0.copy()
        late_rows = p_order >= c
        y[late_rows] = rng.uniform(100.0, 250.0, int(late_rows.sum()))
        got = side_values(p, S, offsets, hist=hist, y_override=y, G=G)
        diff = np.zeros(len(S), bool)
        for col in cols:
            a_, b_ = base[col].to_numpy(float), got[col].to_numpy(float)
            diff |= ~(np.isclose(a_, b_, rtol=0.0, atol=1e-12) | (np.isnan(a_) & np.isnan(b_)))
        before = diff & (S_order < c)
        at = diff & (S_order == c)
        moved_before += int(before.sum())
        moved_at += int(at.sum())
        got_l = side_values(p, S, offsets, hist=hist_l, y_override=y, G=G_l)
        at_t = (S_order == c) & timed
        lk = ~np.isclose(base_l["f_hat"].to_numpy(), got_l["f_hat"].to_numpy(), rtol=0.0, atol=1e-12)
        hit = bool((lk & at_t).any())
        leaky_hits += int(hit)
        recs.append({"cut_order": float(c), "season": int(S.loc[S_order == c, "season"].iloc[0]),
                     "targets_before": int((S_order < c).sum()), "targets_at": int((S_order == c).sum()),
                     "moved_before": int(before.sum()), "moved_at": int(at.sum()), "leaky_moved_at": hit})
    passed = (moved_before == 0) and (moved_at == 0) and (leaky_hits >= math.ceil(0.8 * len(cuts)))
    log(f"probe A: cuts {len(cuts)}; moved before {moved_before}, at {moved_at}; leaky control fired in "
        f"{leaky_hits}/{len(cuts)} -> {'PASS' if passed else 'FAIL'}")
    return {"probe": "A (own history, Stage 0 order)", "sides": int(len(S)), "cuts": int(len(cuts)),
            "cuts_2024_26": int(sum(r["season"] >= 2024 for r in recs)), "tolerance": 1e-12,
            "values_checked": cols, "moved_before_cut": moved_before, "moved_at_cut": moved_at,
            "leaky_control_cuts_moved": leaky_hits, "leaky_control_required": math.ceil(0.8 * len(cuts)),
            "pass": bool(passed), "per_cut": recs}


def slam_second_wednesdays(keys: pd.DataFrame) -> list[float]:
    """The second Wednesday of each Slam edition of 2024-26 that has frame matches (the first Wednesday on or after the
    tournament date + 7 days)."""
    s0 = pd.read_parquet(STAGE0, columns=["match_id", "level", "tournament_id", "tournament_date"])
    k = keys.merge(s0.rename(columns={"match_id": "rebuilt_id"}), on="rebuilt_id", how="inner",
                   suffixes=("", "_s0"))
    k = k[k["level"].eq("GS") & k["season"].between(2024, 2026)]
    days = []
    for d0 in sorted(set(pd.to_datetime(k["tournament_date"]))):
        d = d0 + pd.Timedelta(days=7)
        d = d + pd.Timedelta(days=(2 - d.weekday()) % 7)
        days.append(float((d - pd.Timestamp("1970-01-01")).days))
    return sorted(set(days))


def probe_b(B: dict, P, n_random: int = 13, seed: int = 20261008) -> dict:
    """Clock probe (see the module docstring)."""
    rng = np.random.default_rng(seed)
    p, t, keys = B["p"], B["t"], B["keys"]
    fixed = [float((pd.Timestamp(d) - pd.Timestamp("1970-01-01")).days)
             for d in ("2023-09-06", "2024-01-24", "2024-07-10", "2024-08-14")]
    slams = slam_second_wednesdays(keys)
    lo, hi = float(t["es"].min()) + 400.0, float(t["lf"].max()) - 1.0
    rand = sorted(rng.uniform(lo, hi, n_random).round().tolist())
    days = sorted(set(fixed) | set(slams) | set(rand))
    base = B["sv"]
    es_p = p["es"].to_numpy(float)
    t_lf = t["lf"].to_numpy(float)
    t_es = t["es"].to_numpy(float)
    # the leaky control: snapshots that release a row at its tournament date (the panel module's release="tdate";
    # for a module without that option, lf := tdate - 1, which makes lf + 1 = tdate)
    def leaky_offsets(panel_df: pd.DataFrame) -> dict:
        try:
            return {tour: P.EditionOffsets(panel_df, tour, cache=False, release="tdate") for tour in ("atp", "wta")}
        except TypeError:
            q_ = panel_df.copy()
            q_["lf"] = q_["tdate"].astype(float) - 1.0
            return {tour: P.EditionOffsets(q_, tour) for tour in ("atp", "wta")}

    p_leak = p
    recs, moved, leaky_moved_total = [], 0, 0
    cols = ["f_hat", "f_sd", "L_hat", "x_raw", "g_sum", "g_abs"]
    for D in days:
        chk = np.flatnonzero(t_lf <= D)
        noise = rng.uniform(100.0, 250.0, len(p))
        late = es_p > D
        q = p.copy()
        q.loc[late, "y"] = noise[late]
        T = t.iloc[chk]
        off_q = {tour: P.EditionOffsets(q, tour) for tour in ("atp", "wta")}
        got = side_values(q, T, off_q)
        b0 = base.iloc[chk]
        diff = np.zeros(len(chk), bool)
        for col in cols:
            a_, b_ = b0[col].to_numpy(float), got[col].to_numpy(float)
            diff |= ~(np.isclose(a_, b_, rtol=0.0, atol=1e-12) | (np.isnan(a_) & np.isnan(b_)))
        moved += int(diff.sum())
        # leaky control on the sides closest to D (lf <= D, es >= D - 28): clean leaky build vs perturbed leaky build
        near = np.flatnonzero((t_lf <= D) & (t_es >= D - 28.0))
        TN = t.iloc[near]
        l0 = side_values(p_leak, TN, leaky_offsets(p_leak))
        l1 = side_values(q, TN, leaky_offsets(q))
        lmv = ~(np.isclose(l0["f_hat"].to_numpy(), l1["f_hat"].to_numpy(), rtol=0.0, atol=1e-12)
                & np.isclose(l0["g_sum"].to_numpy(), l1["g_sum"].to_numpy(), rtol=0.0, atol=1e-12))
        leaky_moved_total += int(lmv.sum())
        recs.append({"day": D, "date": str(pd.Timestamp("1970-01-01") + pd.Timedelta(days=D))[:10],
                     "kind": "timing_probe" if D in fixed else ("slam_2nd_wed" if D in slams else "random"),
                     "sides_checked": int(len(chk)), "moved": int(diff.sum()),
                     "leaky_sides": int(len(near)), "leaky_moved": int(lmv.sum())})
        log(f"probe B {recs[-1]['date']}: checked {len(chk)}, moved {int(diff.sum())}; leaky moved "
            f"{int(lmv.sum())}/{len(near)}")
    passed = moved == 0 and leaky_moved_total > 0 and len(days) >= 25
    log(f"probe B: days {len(days)}; moved {moved}; leaky control moved {leaky_moved_total} -> "
        f"{'PASS' if passed else 'FAIL'}")
    return {"probe": "B (clock: rows with es > D noised in filter and snapshot inputs)", "days": len(days),
            "values_checked": cols, "tolerance": 1e-12, "moved": moved, "leaky_control_moved": leaky_moved_total,
            "pass": bool(passed), "per_day": recs}


# ------------------------------------------------------------------------------------------------ outputs
def coverage(m: pd.DataFrame) -> list[dict]:
    rows = []
    for (tour, season), g in m.groupby(["tour", "season"]):
        both = (g["k28_a"] > 0) & (g["k28_b"] > 0)
        rows.append({"tour": tour, "season": int(season), "matches": int(len(g)),
                     "spd_f_nonzero": int((g["spd_f"] != 0).sum()),
                     "spd_f_all_nonzero": int((g["spd_f_all"] != 0).sum()),
                     "spd_raw_present": int(g["spd_raw"].notna().sum()),
                     "both_timed_28d": int(both.sum()),
                     "either_timed_28d": int(((g["k28_a"] > 0) | (g["k28_b"] > 0)).sum()),
                     "both_timed_14d": int(((g["k14_a"] > 0) & (g["k14_b"] > 0)).sum()),
                     "id_conflict": int(g["id_conflict"].sum()),
                     "spd_f_clipped": int((g["spd_f"].abs() >= CLIP).sum())})
    return rows


def write(B: dict, P, probes: dict, standin: bool) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    m = B["m"]
    keep = [c for c in m.columns if c != "spd_f_unclipped_km_h"] + ["spd_f_unclipped_km_h"]
    m[keep].to_parquet(FEATURES, index=False)
    panel_path = None if standin else Path(getattr(P, "PANEL", PANEL_FILE))
    c2 = {k: getattr(P, k) for k in ("TAU2", "S_SERVE", "K_PRIOR", "WINDOW") if hasattr(P, k)}
    meta = {
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "spec": "data/studies/serve_speed_tabpfn/design/2_audit.md, section (c) C3 and C7",
        "panel_module": P.__name__, "standin_panel": bool(standin),
        "panel_file": str(panel_path) if panel_path else None, "panel_sha256": sha256(panel_path) if panel_path else None,
        "features_py_sha256": sha256(Path(__file__)), "features_parquet_sha256": sha256(FEATURES),
        "constants": {"men": MEN, "women_A3_only": WOMEN, "window_days": WINDOW, "raw_sd": RAW_SD, "clip": CLIP,
                      "s_f_seasons": list(SF_SEASONS), "c2_frozen": C2_FROZEN, "c2_from_panel_module": c2},
        "s_f": B["s_f"], "s_f_definition": "SD (ddof 1) of unclipped f_hat_A - f_hat_B, men's frame matches 2022-23",
        "rows": int(len(m)), "nan_spd_f": int(m["spd_f"].isna().sum()), "nan_spd_f_all": int(m["spd_f_all"].isna().sum()),
        "coverage": coverage(m), "probes": probes,
        "probes_pass": bool(probes and all(v.get("pass") for v in probes.values())),
        "reads_results": False,
    }
    META.write_text(json.dumps(meta, indent=1, default=float) + "\n", encoding="utf-8")
    log(f"wrote {FEATURES.name} ({len(m)} rows) and {META.name}; probes pass: {meta['probes_pass']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-probes", action="store_true")
    ap.add_argument("--standin", action="store_true", help="development only: the stand-in panel")
    a = ap.parse_args()
    P = panel_module(a.standin)
    B = build(P, standin=a.standin)
    probes = {}
    if not a.no_probes:
        probes["A"] = probe_a(B)
        probes["B"] = probe_b(B, P)
    write(B, P, probes, a.standin)


if __name__ == "__main__":
    main()
