"""Serve/return leads, the speed builder (docs/studies/serve_return_leads/team/speed_builder.md): second-serve speed
form, the first-second gap, first-serve fault speed and the fade within a match. Reads no match result: every input is a
speed, a count, a clock or a key, read with explicit column lists.

Builder columns: serve_speed_tabpfn/adaptive/columns.py's `build`, run on a replaced history exactly as
infosys_atp_backfill/columns.py's `build_on` does (module attributes patched inside this process only; no file of theirs
is edited). Scenario B = the weekly feed's release days (latency/availability.parquet), as `spd_L_B`.
    spd_L_B    the first-serve 28-day form on the augmented history (live_panel.BACKFILLED); reproduced first: it must
               equal infosys_atp_backfill/speed_columns_augmented.parquet on all 63,737 matches
    spd2_L_B   the same builder on the second-serve history: y = spd2, y_raw = spd2_raw, n = n2 (the AO match centre's
    spd2_T_B   rows, which lack n2, get first_total - first_in from the same statistics file); use2 = use & spd2 >= 100
               km/h & n2 >= 10. Edition, family, basis, clock and release days are the first serve's (same record).
               Constants: each frozen first-serve constant times the ratio of the second-serve to the first-serve
               estimate under one estimator (constants()); the column's own standardiser
    gap_L_B    the same builder on the per-match gap y1 - spd2 (use & use2), n replaced by an effective count n_eff
    gap_T_B    so that sigma_g^2 / n_eff = sigma1^2 / n + sigma2^2 / n2 (sigma_g^2 = sigma1^2 + sigma2^2); constants as above
Window columns (data/studies/match_timing/timing.parquet: a match counts from lf + 1, a target reads at es; own-order
earlier matches only):
    fade_dev_14   his previous point-timed match within 14 days (obs >= es - 14): last-third minus first-third mean
                  first-serve-in speed (his own timed first serves in, in point order, n >= 30), minus his normal fade
                  (his other released fades within 364 days, shrunk to the field's mean as of es with weight K0 = 3)
    fault_dev_28  his first-serve fault speed minus first-serve-in speed (same match), mean over his released matches of
                  the last 28 days, minus his normal (his released matches 28-364 days back, shrunk likewise)
Targets: frame_keys.parquet's 63,737 matches plus the 10 Oct instance frame's men's matches missing from it (2018; read
with match_id, tour, season, tournament_date only). Women: every column 0.

Run: ./python.sh src/eda/serve_return_leads/speed_ext.py reproduce | constants | build | probe <col> | fade | fault
Writes data/studies/serve_return_leads/speed/
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
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

from src.eda.serve_speed_tabpfn import features as F  # noqa: E402
from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402
from src.eda.serve_speed_tabpfn.adaptive import columns as CO  # noqa: E402
from src.eda.serve_speed_tabpfn.latency import features_latency as FL  # noqa: E402
from src.eda.serve_speed_tabpfn.live import live_panel as LP  # noqa: E402

OUT = ROOT / "data" / "studies" / "serve_return_leads" / "speed"
STORED = ROOT / "data" / "studies" / "infosys_atp_backfill" / "speed_columns_augmented.parquet"
FRAME_10OCT = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-10" / "model_frame.parquet"
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
REBUILDS = ROOT / "data" / "studies" / "data_continuity" / "rebuilds"
ID_MAPS = ["2026-10-07T0005Z", "2026-10-08T1853Z", "2026-10-14T0412Z", "2026-10-14T2119Z"]
FRAME_COLS = ["match_id", "tour", "season", "tournament_date"]          # never a_won
S0_KEY_COLS = ["match_id", "tour", "year", "level", "qualifying", "tournament_id", "tournament_name", "tournament_date",
               "round_order", "player_a_id", "player_b_id"]
MEN_MIN2, MIN_N2 = 100.0, 10          # second serve: the analogue of the first serve's 120 km/h floor; n2 >= 10
FROZEN = dict(F.MEN)                  # hl 14, s2f 12, q 4/365, c 2, nu_pts 7, nu_ks 8, sigma 13.49
TAU2_1, S_SERVE_1 = P.TAU2, P.S_SERVE  # 22, 12.4 (the edition offsets' weights)
TUNE_LAST = 2022                      # the frozen constants were tuned on seasons <= 2022 (2_audit.md Q3)
SD_SEASONS = (2022, 2023)
K0 = 3.0
SEALED_FROM = pd.Timestamp("2026-07-29")
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, default=float) + "\n", encoding="utf-8")


# ------------------------------------------------------------------------------------------------ ids and keys
def remap_ids(ids: pd.Series) -> pd.Series:
    """Apply the Stage 0 rebuilds' id maps in order (each a no-op for ids it does not list)."""
    out = ids.astype(object).copy()
    for r in ID_MAPS:
        f = REBUILDS / r / "id_map.csv"
        if not f.exists():
            continue
        m = pd.read_csv(f, usecols=["old_match_id", "new_match_id"])
        if len(m):
            d = dict(zip(m["old_match_id"], m["new_match_id"]))
            out = out.map(lambda x, d=d: d.get(x, x) if isinstance(x, str) else x)
    return out


def augmented() -> pd.DataFrame:
    """The live speed history with the ATP backfill, checked against its own record (as live_panel.frozen_panel)."""
    meta = json.loads(LP.BACKFILLED_META.read_text(encoding="utf-8"))
    if sha256(LP.BACKFILLED) != meta["backfilled_sha256"]:
        raise SystemExit(f"{LP.BACKFILLED} does not match its record")
    return pd.read_parquet(LP.BACKFILLED)


def ext_keys() -> pd.DataFrame:
    """frame_keys plus the 10 Oct frame's men's matches it lacks (all 2018), keyed outcome-free from Stage 0 and the
    current timing table."""
    fk = P.load_frame_keys()
    fr = pd.read_parquet(FRAME_10OCT, columns=FRAME_COLS)
    # seen dates only: the 10 Oct frame's matches from 29 Jul 2026 on get no value here
    fr = fr[fr["tour"].eq("atp") & ~fr["match_id"].isin(fk["match_id"]) & (fr["tournament_date"] < SEALED_FROM)]
    if not len(fr):
        return fk
    s0 = pd.read_parquet(P.S0, columns=S0_KEY_COLS)
    cur = remap_ids(fr["match_id"])
    x = pd.DataFrame({"match_id": fr["match_id"].to_numpy(), "rebuilt_id": cur.to_numpy(),
                      "season": fr["season"].to_numpy()})
    x = x.merge(s0.rename(columns={"match_id": "rebuilt_id"}), on="rebuilt_id", how="left", validate="one_to_one")
    tm = pd.read_parquet(TIMING, columns=["match_id", "es", "lf", "obs"]).rename(columns={"match_id": "rebuilt_id"})
    x = x.merge(tm, on="rebuilt_id", how="left", validate="one_to_one")
    ok = x[["es", "lf", "obs", "player_a_id", "player_b_id"]].notna().all(axis=1)
    x = x[ok].copy()
    x["obs_raw"] = x["obs"]
    x["es"], x["lf"] = x["es"].astype("int64"), x["lf"].astype("int64")
    x["obs"] = np.floor(x["obs"]).astype("int64")
    x["tdate"] = P.days(x["tournament_date"])
    x["id_conflict"], x["flipped"] = False, False
    x["a_rebuilt"], x["b_rebuilt"] = x["player_a_id"], x["player_b_id"]
    x = x[list(fk.columns)]
    out = pd.concat([fk, x], ignore_index=True)
    assert out["match_id"].is_unique
    return out


# ------------------------------------------------------------------------------------------------ the builder
@contextlib.contextmanager
def patched(history: pd.DataFrame, keys: pd.DataFrame | None = None, const: dict | None = None,
            tau2: float | None = None, s_serve: float | None = None, sd: tuple | None = None):
    """build_on's patch (the history in place of the frozen panel), plus optional frame keys, men's filter constants,
    the edition offsets' weights and the two standardisers (CO.S_F, CO.SD_L), restored on exit."""
    saved = (P.load_panel, P.load_frame_keys, F.CONST, P.TAU2, P.S_SERVE, CO.S_F, CO.SD_L)
    P.load_panel = lambda use_only=True: (history[history["use"].astype(bool)].reset_index(drop=True)
                                          if use_only else history)
    if keys is not None:
        P.load_frame_keys = lambda: keys
    if const is not None:
        F.CONST = {"atp": dict(const), "wta": F.WOMEN}
    if tau2 is not None:
        P.TAU2 = float(tau2)
    if s_serve is not None:
        P.S_SERVE = float(s_serve)
    if sd is not None:
        CO.S_F, CO.SD_L = float(sd[0]), float(sd[1])
    try:
        yield
    finally:
        P.load_panel, P.load_frame_keys, F.CONST, P.TAU2, P.S_SERVE, CO.S_F, CO.SD_L = saved


def run_builder(history: pd.DataFrame, keys: pd.DataFrame | None = None, spec: dict | None = None) -> dict:
    spec = spec or {}
    with patched(history, keys, spec.get("const"), spec.get("tau2"), spec.get("s_serve"), spec.get("sd")):
        return CO.build(probes=False)


def side_diff(res: dict, scen: str, filt: str) -> pd.DataFrame:
    """Unclipped f_hat_A - f_hat_B (km/h) of every men's frame match, with the side diagnostics."""
    tm, s = res["tm"], res["parts"][scen]["sides"][filt]
    a = tm["side"].eq("A").to_numpy()
    assert (tm.loc[a, "match_id"].to_numpy() == tm.loc[~a, "match_id"].to_numpy()).all()
    return pd.DataFrame({"match_id": tm.loc[a, "match_id"].to_numpy(), "season": tm.loc[a, "season"].to_numpy(),
                         "d": s.loc[a, "f_hat"].to_numpy() - s.loc[~a, "f_hat"].to_numpy(),
                         "k28_a": s.loc[a, "k28"].to_numpy(), "k28_b": s.loc[~a, "k28"].to_numpy(),
                         "hist_a": s.loc[a, "hist"].to_numpy(), "hist_b": s.loc[~a, "hist"].to_numpy()})


def sd_of(d: pd.DataFrame) -> float:
    return float(d.loc[d["season"].between(*SD_SEASONS), "d"].std(ddof=1))


def column(keys: pd.DataFrame, d: pd.DataFrame, sd: float) -> np.ndarray:
    z = pd.Series(np.clip(d["d"].to_numpy() / sd, -F.CLIP, F.CLIP), index=d["match_id"].to_numpy())
    out = np.array(keys["match_id"].map(z).fillna(0.0).to_numpy(dtype=float), copy=True)
    out[keys["tour"].eq("wta").to_numpy()] = 0.0
    return out


# ------------------------------------------------------------------------------------------------ the histories
def ao_second_counts() -> pd.DataFrame:
    """The AO match centre's second-serve counts (first_total - first_in, match level), keyed as the panel's mc rows
    (source_key = record_key, side), by panel.py's own record and side rules."""
    a = pd.read_parquet(P.AO_STATS, columns=["record_key", "set", "stat", "team1_secondary", "team2_secondary"])
    a = a[a["set"].eq("All") & a["stat"].eq("1st serve in")].drop_duplicates(["record_key", "stat"])
    links = pd.read_parquet(P.SHOT / "stage0_source_matches.parquet", columns=P.LINK_COLS)
    lk = links[links["source"].eq("ausopen") & links["match_id"].notna() & links["a1"].notna()][["key", "match_id", "a1"]]
    lk = lk.drop_duplicates("key").rename(columns={"key": "record_key"})
    rows = []
    for no in (1, 2):
        fs = a[f"team{no}_secondary"].astype(str).str.extract(P.FIRST)
        w = pd.DataFrame({"record_key": a["record_key"].to_numpy(), "player_no": no,
                          "first_in": pd.to_numeric(fs[0], errors="coerce").to_numpy(),
                          "first_total": pd.to_numeric(fs[1], errors="coerce").to_numpy()})
        rows.append(w)
    w = pd.concat(rows, ignore_index=True).merge(lk, on="record_key", how="left")
    w["side"] = P._side_of(w["a1"], w["player_no"])
    w["n2_ao"] = w["first_total"] - w["first_in"]
    return w[["record_key", "side", "first_in", "n2_ao"]].rename(columns={"record_key": "source_key"})


def second_history(h: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """The history with the second serve in place of the first: y, y_raw, n replaced; use2 = use & spd2 >= 100 km/h
    (men) & n2 >= 10. The record, edition, family, basis, clock and release are the first serve's."""
    q = h.copy()
    n2 = pd.to_numeric(q["n2"], errors="coerce")
    mc = q["kind"].eq("mc_floor") & n2.isna()
    filled = 0
    if mc.any():
        ao = ao_second_counts()
        m = q.loc[mc, ["source_key", "side", "n", "f1"]].merge(ao, on=["source_key", "side"], how="left")
        ok = m["first_in"].to_numpy(float) == m["f1"].to_numpy(float)      # the same record's first serves in
        v = np.where(ok, m["n2_ao"].to_numpy(float), np.nan)
        n2.loc[mc] = v
        filled = int(np.isfinite(v).sum())
    floor = np.where(q["tour"].eq("atp"), MEN_MIN2, 0.0)
    spd2 = pd.to_numeric(q["spd2"], errors="coerce")
    use2 = q["use"].astype(bool) & spd2.notna() & n2.ge(MIN_N2) & (spd2 >= floor)
    info = {"rows": int(len(q)), "use_first": int(q["use"].sum()), "use_second": int(use2.sum()),
            "men_use_first": int((q["use"] & q["tour"].eq("atp")).sum()),
            "men_use_second": int((use2 & q["tour"].eq("atp")).sum()),
            "ao_match_centre_n2_filled": filled, "ao_match_centre_rows": int(mc.sum()),
            "dropped_men": {"no_spd2": int((q["use"] & q["tour"].eq("atp") & spd2.isna()).sum()),
                            "n2_lt_10_or_missing": int((q["use"] & q["tour"].eq("atp") & spd2.notna()
                                                        & ~n2.ge(MIN_N2)).sum()),
                            "spd2_lt_100": int((q["use"] & q["tour"].eq("atp") & spd2.notna() & n2.ge(MIN_N2)
                                                & (spd2 < floor)).sum())}}
    q["y_first"], q["n_first"] = q["y"], q["n"]
    q["y"], q["y_raw"] = spd2, pd.to_numeric(q["spd2_raw"], errors="coerce")
    q["n"] = n2.fillna(0).round().astype("int64")
    q["n2"] = n2
    q["use"] = use2
    return q, info


def gap_history(h: pd.DataFrame, sig1: float, sig2: float) -> tuple[pd.DataFrame, dict]:
    """The per-match gap y1 - spd2 (both from the same record, so the key-statistic and match-centre shifts cancel);
    n is the effective count with sigma_g^2 / n_eff = sigma1^2 / n1 + sigma2^2 / n2, sigma_g^2 = sigma1^2 + sigma2^2."""
    s2, info2 = second_history(h)
    q = h.copy()
    n1 = q["n"].to_numpy(float)
    n2 = s2["n2"].to_numpy(float)
    var = sig1 ** 2 / np.maximum(n1, 1.0) + sig2 ** 2 / np.maximum(n2, 1.0)
    neff = (sig1 ** 2 + sig2 ** 2) / var
    q["y"] = q["y"].to_numpy(float) - s2["y"].to_numpy(float)
    q["y_raw"] = q["y"]
    q["n"] = np.where(np.isfinite(neff), np.round(neff), 0).astype("int64")
    q["use"] = q["use"].astype(bool) & s2["use"].astype(bool)
    info = {"men_use_gap": int((q["use"] & q["tour"].eq("atp")).sum()), "sigma_g": float(math.sqrt(sig1 ** 2 + sig2 ** 2)),
            "n_eff_median_men": float(np.median(q.loc[q["use"] & q["tour"].eq("atp"), "n"]))}
    return q, info


# ------------------------------------------------------------------------------------------------ constants
def point_moments(last: int = 2023) -> pd.DataFrame:
    """Per men's player-match of the point tables the frozen sigma came from (infosys, slam_pbp, slam_tracking,
    slamtracker; seasons <= last): counts, sums and sums of squares of timed first serves in and second serves in."""
    links = pd.read_parquet(P.SHOT / "stage0_source_matches.parquet", columns=P.LINK_COLS)
    s0 = pd.read_parquet(P.S0, columns=["match_id", "tour", "year"])
    from src.eda.shot_level.points import END
    parts = []
    for name in ("infosys", "slam_pbp", "slam_tracking", "slamtracker"):
        p = pd.read_parquet(P.SHOT / f"stage1_points_{name}.parquet", columns=P.POINT_COLS)
        lk = links[links["source"].eq(name) & links["match_id"].notna() & links["a1"].notna()][["key", "match_id", "a1"]]
        sizes = p.groupby("key").size().rename("pts")
        lk = lk.join(sizes, on="key").sort_values("pts", ascending=False).drop_duplicates("match_id")
        p = p.merge(lk[["key", "match_id", "a1"]], on="key", how="inner")
        srv = p["server"].to_numpy()
        a1 = p["a1"].astype(bool).to_numpy()
        srv = np.where(srv == 0, 0, np.where(a1, srv, 3 - srv))
        keep = np.isin(srv, [1, 2])
        p, srv = p[keep], srv[keep]
        sp = P.plaus(p["speed"])
        df = p["end"].to_numpy() == END["df"]
        sn = p["serve_no"].to_numpy()
        f1, f2 = (sn == 1) & ~df, (sn == 2) & ~df
        t1, t2 = f1 & np.isfinite(sp), f2 & np.isfinite(sp)
        g = pd.DataFrame({"match_id": p["match_id"].to_numpy(), "side": np.where(srv == 1, "A", "B"),
                          "f1": f1, "n1": t1, "s1": np.where(t1, sp, 0.0), "q1": np.where(t1, sp * sp, 0.0),
                          "f2": f2, "n2": t2, "s2": np.where(t2, sp, 0.0), "q2": np.where(t2, sp * sp, 0.0)})
        a = g.groupby(["match_id", "side"]).sum().reset_index()
        a["source"] = name
        parts.append(a)
    m = pd.concat(parts, ignore_index=True)
    m["match_id"] = remap_ids(m["match_id"])
    m = m.merge(s0, on="match_id", how="inner")
    return m[m["tour"].eq("atp") & (m["year"] <= last)].reset_index(drop=True)


def serve_noise(m: pd.DataFrame) -> dict:
    """Pooled within-match SD (the frozen sigma's estimator, modeller_variance.serve_noise) and the median within-match
    SD (the engineer's s), first serves in and second serves in; player-matches with >= 10 timed serves and at least
    half of their serves timed."""
    out = {}
    for k in ("1", "2"):
        n, s, q, f = (m[f"n{k}"].to_numpy(float), m[f"s{k}"].to_numpy(float), m[f"q{k}"].to_numpy(float),
                      m[f"f{k}"].to_numpy(float))
        ok = (n >= 10) & (n >= 0.5 * f)
        var = (q[ok] - s[ok] ** 2 / n[ok]) / (n[ok] - 1)
        out[k] = {"player_matches": int(ok.sum()),
                  "pooled_sd": float(np.sqrt(np.sum((n[ok] - 1) * var) / np.sum(n[ok] - 1))),
                  "median_sd": float(np.median(np.sqrt(np.maximum(var, 0.0))))}
    return out


def tau2_of(history: pd.DataFrame, s_serve: float, last: int = 2023) -> dict:
    """The engineer's estimator (engineer_systems.fit + tau2_from) on one series: y = alpha[player-season] +
    gamma[edition] + e by alternating weighted means (weights n), single-match player-seasons dropped; tau^2 = mean
    resid^2 k/(k - 1) - s^2 mean(1/n). Men, seasons <= last, use rows."""
    d = history[history["use"].astype(bool) & history["tour"].eq("atp") & (history["year"] <= last)].copy()
    d["ps"] = d["player_id"].astype(str) + "|" + d["year"].astype(str)
    d = d[d.groupby("ps")["ps"].transform("size") > 1]
    n = d["n"].clip(lower=1).to_numpy(float)
    y = d["y"].to_numpy(float)
    ps_c, _ = pd.factorize(d["ps"])
    ed_c, _ = pd.factorize(d["edition"])
    wps, wed = np.bincount(ps_c, weights=n), np.bincount(ed_c, weights=n)
    g = np.zeros(ed_c.max() + 1)
    for _ in range(500):
        a = np.bincount(ps_c, weights=n * (y - g[ed_c])) / wps
        g_new = np.bincount(ed_c, weights=n * (y - a[ps_c])) / wed
        delta = np.max(np.abs(g_new - g))
        g = g_new
        if delta < 1e-6:
            break
    r = y - a[ps_c] - g[ed_c]
    k = d.groupby("ps")["ps"].transform("size").to_numpy(float)
    tau2 = float(max(np.mean(r ** 2 * k / (k - 1)) - s_serve ** 2 * np.mean(1.0 / n), 1.0))
    return {"tau2": tau2, "rows": int(len(d))}


class OneStep:
    """The frozen constants' criterion (design/modeller_state.py, Kalman tuning): the one-step-ahead MSE of a timed
    player-match's centred speed z_m by L_hat + f_hat of the filter on his earlier rows (own order, 364 days, the
    instant rule of features.py), centred by the as-of edition offsets at the target's es; men, seasons <= TUNE_LAST;
    targets with n >= 15, a history, and |z - m364| inside the series' cut (the first serve's 20 km/h; another series
    uses the same tail share)."""

    def __init__(self, history: pd.DataFrame, tau2: float, s_serve: float, cut_share: float | None = None):
        with patched(history, tau2=tau2, s_serve=s_serve):
            p = FL.load_panel()
            off = {"atp": P.EditionOffsets(p, "atp", cache=False)}
        t = p[p["tour"].eq("atp") & (p["year"] <= TUNE_LAST)][
            ["match_id", "side", "player_id", "tour", "tdate", "tournament_id", "round_order", "es", "lf", "obs", "y",
             "n", "edition", "year"]].reset_index(drop=True)
        hist = F.histories(p, t)
        idx = hist["idx"]
        ok = idx >= 0
        safe = np.maximum(idx, 0)
        G = F.snapshot_gammas(p, t, idx, off)
        g_t = np.full(len(t), np.nan)
        for day, grp in t.groupby("es"):
            g_t[grp.index.to_numpy()] = off["atp"].gamma(grp["edition"].to_numpy(), int(day))
        self.z = t["y"].to_numpy(float) - g_t
        self.Z = np.where(ok, p["y"].to_numpy(float)[safe] - G, np.nan)
        self.DAY = np.where(ok, p["obs"].to_numpy(float)[safe], np.nan)
        self.nh = np.where(ok, p["n"].to_numpy(float)[safe], np.nan)
        self.ks = np.where(ok, p["basis"].astype(str).eq("ks").to_numpy()[safe], False)
        self.es = t["es"].to_numpy(float)
        w = np.where(ok, self.nh, 0.0)
        m364 = np.where(w.sum(1) > 0, (np.nan_to_num(self.Z) * w).sum(1) / np.maximum(w.sum(1), 1e-12), np.nan)
        dev = np.abs(self.z - m364)
        base = (hist["hist"] > 0) & (t["n"].to_numpy(float) >= 15) & np.isfinite(dev)
        if cut_share is None:
            self.cut = 20.0
            self.cut_share = float(np.mean(dev[base] > 20.0))
        else:
            self.cut_share = float(cut_share)
            self.cut = float(np.quantile(dev[base], 1.0 - cut_share))
        self.sel = base & (dev <= self.cut)
        self.targets = int(self.sel.sum())

    def mse(self, prm: dict) -> float:
        R = np.where(self.ks, prm["nu_ks"], prm["nu_pts"]) + prm["sigma"] ** 2 / np.maximum(np.nan_to_num(self.nh), 1.0)
        R = np.where(np.isfinite(self.Z), R, np.nan)
        kf = F.kalman(self.Z[self.sel], R[self.sel], self.DAY[self.sel], self.es[self.sel], prm)
        pred = kf["L_hat"] + kf["f_hat"]
        return float(np.mean((self.z[self.sel] - pred) ** 2))


TUNED = ("s2f", "q", "nu_pts", "nu_ks")


def tune(os_: OneStep, sigma: float, hl: float = 14.0) -> dict:
    """Nelder-Mead on the log of (s2f, q, nu_pts, nu_ks), from the frozen values; hl and c fixed, sigma the series'."""
    from scipy.optimize import minimize
    x0 = np.log([FROZEN[k] for k in TUNED])

    def f(x):
        prm = dict(FROZEN, hl=hl, sigma=sigma, **{k: float(np.exp(v)) for k, v in zip(TUNED, x)})
        return os_.mse(prm)

    r = minimize(f, x0, method="Nelder-Mead", options={"xatol": 1e-3, "fatol": 1e-4, "maxiter": 400})
    est = {k: float(np.exp(v)) for k, v in zip(TUNED, r.x)}
    return {"estimate": est, "mse": float(r.fun), "mse_at_frozen": f(x0), "iterations": int(r.nit),
            "converged": bool(r.success), "targets": os_.targets, "cut_km_h": os_.cut, "cut_share": os_.cut_share}


def constants() -> dict:
    """Every constant of the second-serve and gap series, outcome-free: the frozen first-serve constant times the ratio
    of the series' estimate to the first serve's estimate under one estimator (point tables for sigma and s; the
    engineer's two-way fit for tau^2; the modeller's one-step criterion for s2f, q, nu_pts, nu_ks). hl, c, the window and
    the clip are the column's definition and stay."""
    h = augmented()
    log("point moments (<= 2023)")
    m = point_moments()
    sn = serve_noise(m)
    r_sig = sn["2"]["pooled_sd"] / sn["1"]["pooled_sd"]
    r_s = sn["2"]["median_sd"] / sn["1"]["median_sd"]
    sig1, s1 = FROZEN["sigma"], S_SERVE_1
    sig2, s2 = sig1 * r_sig, s1 * r_s
    h2, info2 = second_history(h)
    hg, infog = gap_history(h, sig1, sig2)
    sg = math.sqrt(s1 ** 2 + s2 ** 2)
    log("tau^2 by the engineer's estimator")
    t1 = tau2_of(h, s1)
    t2 = tau2_of(h2, s2)
    tg = tau2_of(hg, sg)
    tau2_2 = TAU2_1 * t2["tau2"] / t1["tau2"]
    tau2_g = TAU2_1 * tg["tau2"] / t1["tau2"]
    log("one-step tuning, first serve")
    os1 = OneStep(h, TAU2_1, s1)
    k1 = tune(os1, sig1)
    log(f"  first: {k1['estimate']} mse {k1['mse']:.3f} (at frozen {k1['mse_at_frozen']:.3f}); cut share "
        f"{os1.cut_share:.4f}")
    log("one-step tuning, second serve")
    os2 = OneStep(h2, tau2_2, s2, cut_share=os1.cut_share)
    k2 = tune(os2, sig2)
    log(f"  second: {k2['estimate']} mse {k2['mse']:.3f}")
    log("one-step tuning, gap")
    osg = OneStep(hg, tau2_g, sg, cut_share=os1.cut_share)
    sig_g = math.sqrt(sig1 ** 2 + sig2 ** 2)
    kg = tune(osg, sig_g)
    log(f"  gap: {kg['estimate']} mse {kg['mse']:.3f}")

    def calibrated(k, sigma):
        c = dict(FROZEN)
        for p_ in TUNED:
            c[p_] = FROZEN[p_] * k["estimate"][p_] / k1["estimate"][p_]
        c["sigma"] = sigma
        return c

    out = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "reads_results": False,
           "frozen_first_serve": {"filter": FROZEN, "tau2": TAU2_1, "s_serve": s1},
           "serve_noise_points_le_2023": sn, "ratios": {"pooled_sd": r_sig, "median_sd": r_s},
           "tau2_estimates": {"first": t1, "second": t2, "gap": tg},
           "one_step": {"first": k1, "second": k2, "gap": kg},
           "second": {"filter": calibrated(k2, sig2), "tau2": tau2_2, "s_serve": s2},
           "gap": {"filter": calibrated(kg, sig_g), "tau2": tau2_g, "s_serve": sg, "sigma_parts": [sig1, sig2]},
           "histories": {"second": info2, "gap": infog},
           "rule": "constant(series) = frozen first-serve constant x estimate(series) / estimate(first serve), the same "
                   "estimator for both; hl (14 / 28), c = 2, the 364-day window and the clip at 4 are the columns' "
                   "definition"}
    write_json(OUT / "constants.json", out)
    return out


def load_constants() -> dict:
    return json.loads((OUT / "constants.json").read_text(encoding="utf-8"))


def spec_of(name: str, cst: dict, sd: tuple | None = None) -> dict:
    c = cst[name]
    return {"const": c["filter"], "tau2": c["tau2"], "s_serve": c["s_serve"], "sd": sd}


def series_history(name: str, cst: dict) -> pd.DataFrame:
    h = augmented()
    if name == "second":
        return second_history(h)[0]
    if name == "gap":
        return gap_history(h, *cst["gap"]["sigma_parts"])[0]
    raise ValueError(name)


# ------------------------------------------------------------------------------------------------ commands
def cmd_reproduce() -> dict:
    """build_on on the augmented history reproduces the stored columns exactly (every column, all 63,737 matches)."""
    stored = pd.read_parquet(STORED)
    res = run_builder(augmented())
    new = res["out"]
    pd.testing.assert_frame_equal(new.reset_index(drop=True), stored[new.columns].reset_index(drop=True),
                                  check_dtype=False)
    exact = {c: int((new[c].to_numpy() != stored[c].to_numpy()).sum()) for c in new.columns if c != "match_id"}
    # the extended targets: frame_keys' rows unchanged by adding the 2018 men's matches
    keys = ext_keys()
    res2 = run_builder(augmented(), keys)
    e = res2["out"].set_index("match_id").loc[stored["match_id"]]
    moved = {c: int((e[c].to_numpy() != stored[c].to_numpy()).sum()) for c in stored.columns if c != "match_id"}
    added = keys[~keys["match_id"].isin(stored["match_id"])]
    out = {"what": "build_on(live_panel.BACKFILLED) vs infosys_atp_backfill/speed_columns_augmented.parquet",
           "stored_sha256": sha256(STORED), "history_sha256": sha256(LP.BACKFILLED), "rows": int(len(new)),
           "exact_mismatches_by_column": exact, "assert_frame_equal": "passed",
           "extended_keys": {"rows": int(len(keys)), "added": int(len(added)),
                             "added_by_tour_season": added.groupby(["tour", "season"]).size().reset_index(name="n")
                             .to_dict(orient="records"),
                             "stored_rows_moved_by_the_extension": moved}}
    d = side_diff(res2, "B", "L")
    out["extended_keys"]["spd_L_B_nonzero_2018"] = int(((d["season"] == 2018) & (d["d"] != 0)).sum())
    write_json(OUT / "reproduce.json", out)
    log(json.dumps({k: v for k, v in out.items() if k != "extended_keys"}, default=float)[:600])
    return out


def cmd_build() -> dict:
    cst = load_constants()
    keys = ext_keys()
    out = keys[["match_id", "tour", "season"]].copy()
    meta = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "reads_results": False,
            "constants": "constants.json", "columns": {}}
    log("first serve on the extended keys")
    r1 = run_builder(augmented(), keys)
    d1 = side_diff(r1, "B", "L")
    out["spd_L_B"] = column(keys, d1, CO.SD_L)
    meta["columns"]["spd_L_B"] = {"sd_km_h": CO.SD_L, "source": "frozen standardiser (latency B_M1)"}
    diags = {"spd_L_B": d1}
    for name, prefix in (("second", "spd2"), ("gap", "gap")):
        log(f"{name} serve series")
        hist = series_history(name, cst)
        r = run_builder(hist, keys, spec_of(name, cst))
        for filt, lab in (("L", "L"), ("T", "T")):
            d = side_diff(r, "B", filt)
            sd = sd_of(d)
            col = f"{prefix}_{lab}_B"
            out[col] = column(keys, d, sd)
            diags[col] = d
            men = keys["tour"].eq("atp").to_numpy()
            meta["columns"][col] = {"sd_km_h": sd, "sd_definition": "SD (ddof 1) of unclipped f_hat_A - f_hat_B, men's "
                                    "frame matches of 2022-23 (as latency B_M1's standardiser)",
                                    "clipped": int((np.abs(out.loc[men, col]) >= F.CLIP).sum()),
                                    "corr_with_spd_L_B_men_nonzero": float(np.corrcoef(
                                        out.loc[men & (out[col] != 0), col],
                                        out.loc[men & (out[col] != 0), "spd_L_B"])[0, 1])}
    # the reproduction on the extended keys: frame_keys' rows equal the stored spd_L_B exactly
    stored = pd.read_parquet(STORED, columns=["match_id", "spd_L_B"]).set_index("match_id")["spd_L_B"]
    sel = out["match_id"].isin(stored.index).to_numpy()
    meta["columns"]["spd_L_B"]["stored_rows_differing"] = int(
        (out.loc[sel, "spd_L_B"].to_numpy() != stored.reindex(out.loc[sel, "match_id"]).to_numpy()).sum())
    # sensitivity (outcome-free, never read): the frozen first-serve filter constants, only sigma and n the second
    # serve's; reported as its correlation with the primary
    log("sensitivity: second serve with the frozen constants (sigma and n its own)")
    hist2 = series_history("second", cst)
    fc = dict(FROZEN, sigma=cst["second"]["filter"]["sigma"])
    r = run_builder(hist2, keys, {"const": fc, "tau2": TAU2_1, "s_serve": cst["second"]["s_serve"]})
    d = side_diff(r, "B", "L")
    x = column(keys, d, sd_of(d))
    men = keys["tour"].eq("atp").to_numpy()
    nz = men & ((x != 0) | (out["spd2_L_B"].to_numpy() != 0))
    meta["sensitivity_frozen_constants"] = {
        "corr_with_spd2_L_B_men_nonzero": float(np.corrcoef(x[nz], out.loc[nz, "spd2_L_B"])[0, 1]),
        "sd_km_h": sd_of(d), "note": "not read against results"}
    OUT.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT / "builder_columns.parquet", index=False)
    cov = []
    for col, d in diags.items():
        g = d.assign(nz=d["d"] != 0, both=(d["k28_a"] > 0) & (d["k28_b"] > 0),
                     either=(d["k28_a"] > 0) | (d["k28_b"] > 0))
        for s, x in g.groupby("season"):
            cov.append({"column": col, "season": int(s), "men_matches": int(len(x)), "nonzero": int(x["nz"].sum()),
                        "both_sides_28d_row": int(x["both"].sum()), "either_side_28d_row": int(x["either"].sum())})
    pd.DataFrame(cov).to_csv(OUT / "builder_coverage.csv", index=False)
    meta["coverage"] = "builder_coverage.csv"
    meta["sha256"] = {"builder_columns.parquet": sha256(OUT / "builder_columns.parquet"),
                      "history": sha256(LP.BACKFILLED), "speed_ext.py": sha256(Path(__file__))}
    write_json(OUT / "builder_columns.json", meta)
    log(json.dumps(meta["columns"], default=float))
    return meta


def cmd_probe(name: str) -> dict:
    """adaptive/columns.py's Probe B (probe_b_adaptive) under scenario B on the series' history and constants: rows
    released after day D get random speeds and a new release day in (D, D + 60]; no column or flag of a men's frame
    match with es <= D may move; its leaky controls must move."""
    cst = load_constants()
    keys = ext_keys()
    meta = json.loads((OUT / "builder_columns.json").read_text(encoding="utf-8"))
    prefix = {"second": "spd2", "gap": "gap", "first": "spd"}[name]
    if name == "first":                 # spd_L_B itself on the extended keys: the frozen constants and standardisers
        hist, spec = augmented(), (None, None, None, None)
    else:
        sd = (meta["columns"][f"{prefix}_T_B"]["sd_km_h"], meta["columns"][f"{prefix}_L_B"]["sd_km_h"])
        hist = series_history(name, cst)
        spec = (cst[name]["filter"], cst[name]["tau2"], cst[name]["s_serve"], sd)
    with patched(hist, keys, *spec):
        p = FL.load_panel()
        k = P.load_frame_keys()
        t = F.side_targets(k)
        tm = t[t["tour"].eq("atp")].reset_index(drop=True)
        rt = CO.release_table(p)
        days = FL.probe_days(k)
        log(f"probe {name}: {len(days)} days")
        r = CO.probe_b_adaptive(p, k, tm, rt, "B", days)
    r["series"] = name
    write_json(OUT / f"probe_{prefix}.json", r)
    log(f"probe {name}: moved {r['moved']}, leaky columns {r['leaky_columns_moved']}, leaky flag "
        f"{r['leaky_flag_moved']} -> pass {r['pass']}")
    return r


# ------------------------------------------------------------------------------------------------ window columns (C, D)
FADE_MIN_N = 30
FADE_WINDOW, FAULT_WINDOW, NORMAL_WINDOW = 14.0, 28.0, 364.0
FAULT_MIN_N = 5
STAGE1_FADE = ("slam_pbp", "slam_tracking", "slamtracker", "infosys", "sirgenkii")
PRIORITY = {s: i for i, s in enumerate(P.PTS_PRIORITY)}
OWN_ORDER = ["player_id", "tdate", "tournament_id", "round_order", "obs", "match_id"]


def _stage1_serves(name: str, links: pd.DataFrame) -> pd.DataFrame:
    """One row per timed first serve in (not a double fault), in point order (seq), oriented to Stage 0's sides as
    panel._point_records does (the link copy with the most points per match)."""
    from src.eda.shot_level.points import END
    p = pd.read_parquet(P.SHOT / f"stage1_points_{name}.parquet",
                        columns=["key", "seq", "server", "serve_no", "end", "speed"])
    lk = links[links["source"].eq(name) & links["match_id"].notna() & links["a1"].notna()][["key", "match_id", "a1"]]
    sizes = p.groupby("key").size().rename("pts")
    lk = lk.join(sizes, on="key").sort_values("pts", ascending=False).drop_duplicates("match_id")
    p = p.merge(lk[["key", "match_id", "a1"]], on="key", how="inner")
    srv = p["server"].to_numpy()
    a1 = p["a1"].astype(bool).to_numpy()
    srv = np.where(srv == 0, 0, np.where(a1, srv, 3 - srv))
    sp = P.plaus(p["speed"])
    keep = np.isin(srv, [1, 2]) & (p["serve_no"].to_numpy() == 1) & (p["end"].to_numpy() != END["df"]) & np.isfinite(sp)
    return pd.DataFrame({"source": name, "match_id": p["match_id"].to_numpy()[keep],
                         "side": np.where(srv[keep] == 1, "A", "B"), "ord": p["seq"].to_numpy(float)[keep],
                         "sp": sp[keep]})


def _infosys_slams_serves(sp_tab: pd.DataFrame) -> pd.DataFrame:
    """The Infosys Slam files (AO 2025, RG 2025-26): order = (set, game, point number in the game); linked through
    speeds.parquet as panel._infosys_slams_records."""
    p = pd.read_parquet(P.INFO_SLAMS_POINTS, columns=["slam", "year", "match_id", "set", "game", "seq", "server", "serve",
                                                      "serveSpeed", "result"])
    p = p[p["server"].astype(str).isin(["1", "2"])]
    sp = P.plaus(p["serveSpeed"])
    df = p["result"].astype(str).eq("DF").to_numpy()            # the point's ending code, not a match result
    keep = (p["serve"].astype(str).to_numpy() == "1") & ~df & np.isfinite(sp)
    q = p[keep]
    o = (pd.to_numeric(q["set"], errors="coerce").to_numpy(float) * 1e4
         + pd.to_numeric(q["game"], errors="coerce").to_numpy(float) * 1e2
         + pd.to_numeric(q["seq"], errors="coerce").to_numpy(float))
    g = pd.DataFrame({"source_key": q["slam"].astype(str) + "_" + q["year"].astype(str) + "_" + q["match_id"].astype(str),
                      "player_no": q["server"].astype(int).to_numpy(), "ord": o, "sp": sp[keep]})
    lk = sp_tab[sp_tab["source"].eq("infosys_slams")][["source_key", "player_no", "match_id", "side"]]
    g = g.merge(lk.drop_duplicates(["source_key", "player_no"]), on=["source_key", "player_no"], how="inner")
    g["source"] = "infosys_slams"
    return g[["source", "match_id", "side", "ord", "sp"]][np.isfinite(g["ord"])]


def _thirds(g: pd.DataFrame) -> pd.DataFrame:
    """Per (source, match, side): n1 timed first serves in, the means of the first and last equal-count thirds in point
    order, fade = last - first."""
    g = g.sort_values(["source", "match_id", "side", "ord"], kind="mergesort").reset_index(drop=True)
    grp = g.groupby(["source", "match_id", "side"], sort=False)
    r = grp.cumcount().to_numpy()
    n = grp["sp"].transform("size").to_numpy()
    k = n // 3
    g["first"] = np.where(r < k, g["sp"], np.nan)
    g["last"] = np.where(r >= n - k, g["sp"], np.nan)
    a = g.groupby(["source", "match_id", "side"], sort=False).agg(
        n1=("sp", "size"), mean1=("sp", "mean"), first=("first", "mean"), last=("last", "mean")).reset_index()
    a["fade"] = a["last"] - a["first"]
    return a


def fade_rows() -> tuple[pd.DataFrame, dict]:
    """Every men's player-match with point-ordered first-serve speeds (n >= 30), one source per player-match (the
    largest n, ties by the panel's precedence), on the current Stage 0 ids, players and clock."""
    links = pd.read_parquet(P.SHOT / "stage0_source_matches.parquet", columns=P.LINK_COLS)
    parts = [_thirds(_stage1_serves(s, links)) for s in STAGE1_FADE]
    parts.append(_thirds(_infosys_slams_serves(P._read_speeds())))
    a = pd.concat(parts, ignore_index=True)
    a = a[a["n1"] >= FADE_MIN_N].copy()
    a["match_id"] = remap_ids(a["match_id"])
    s0 = pd.read_parquet(P.S0, columns=S0_KEY_COLS)
    a = a.merge(s0, on="match_id", how="inner")
    slam_only = a["source"].isin(P.SLAM_ONLY) & a["level"].ne("GS")
    tour_only = a["source"].isin(P.TOUR_ONLY) & a["level"].eq("GS")
    info = {"player_matches_n30": int(len(a)), "dropped_level_mislink": int((slam_only | tour_only).sum())}
    a = a[~(slam_only | tour_only) & a["tour"].eq("atp")].copy()
    a["player_id"] = np.where(a["side"].eq("A"), a["player_a_id"], a["player_b_id"])
    tm = pd.read_parquet(TIMING, columns=["match_id", "es", "lf", "obs"])
    a = a.merge(tm, on="match_id", how="inner")
    a["prio"] = a["source"].map(PRIORITY).fillna(9)
    a = a.sort_values(["match_id", "side", "n1", "prio"], ascending=[True, True, False, True])
    a = a.drop_duplicates(["match_id", "side"]).reset_index(drop=True)
    a["tdate"] = P.days(a["tournament_date"])
    a["obs"] = np.floor(a["obs"].astype(float))
    a["rel"] = a["lf"].astype(float) + 1.0
    a["v"] = a["fade"]
    info.update({"men_player_matches": int(len(a)),
                 "by_source_year": a.groupby(["source", "year"]).size().reset_index(name="n").to_dict(orient="records")})
    return a, info


def fault_rows() -> tuple[pd.DataFrame, dict]:
    """The augmented history's player-matches with a first-serve fault speed (the Infosys Slam files: AO 2025, RG
    2025-26), men, use, >= 5 timed faults: v = fault1 - y_raw (the same record's first-serve-in point mean), released by
    scenario B's day (as spd_L_B)."""
    h = augmented()
    q = h[h["use"].astype(bool) & h["tour"].eq("atp") & h["fault1"].notna()
          & (pd.to_numeric(h["nfault1"], errors="coerce") >= FAULT_MIN_N)].copy()
    rel = CO.release_table(F.prepare_panel(q))
    q = F.prepare_panel(q)
    q["rel"] = rel["B"].to_numpy(float)
    q["rel_instant"] = q["lf"].to_numpy(float) + 1.0
    q["v"] = q["fault1"].to_numpy(float) - q["y_raw"].to_numpy(float)
    info = {"men_player_matches": int(len(q)), "by_year_slam": q.groupby(["year", "slam"]).size().reset_index(name="n")
            .to_dict(orient="records"), "v_mean_km_h": float(q["v"].mean()), "v_sd_km_h": float(q["v"].std())}
    return q.reset_index(drop=True), info


def targets_of(keys: pd.DataFrame, clock: str) -> pd.DataFrame:
    """Men's target sides (A block, then B): clock 'keys' = the builder's es; 'timing' = the current timing table."""
    t = F.side_targets(keys)
    t = t[t["tour"].eq("atp")].reset_index(drop=True)
    if clock == "timing":
        tm = pd.read_parquet(TIMING, columns=["match_id", "es"]).set_index("match_id")["es"]
        es = remap_ids(t["rebuilt_id"]).map(tm)
        t["es_keys"] = t["es"]
        t["es"] = es.to_numpy(float)
    return t


def window_dev(rows: pd.DataFrame, t: pd.DataFrame, mode: str, window: float, peek: float = 0.0,
               k0: float = K0) -> pd.DataFrame:
    """Per target side: from the player's own-order earlier rows released by es (rel <= es + peek; peek > 0 only for
    a leaky control), within 364 days (obs >= es - 364):
        mode 'prev'  recent = the latest such row with obs >= es - window; normal = his other such rows
        mode 'mean'  recent = the mean of such rows with obs >= es - window; normal = the rest
    dev = recent - (sum normal + K0 mu) / (k normal + K0), mu = the field's mean of every released row within 364 days
    of es (the leak-proof clock). NaN where no recent row."""
    r = rows.sort_values(OWN_ORDER, kind="mergesort").reset_index(drop=True)
    n = len(t)
    v, rel, ob = r["v"].to_numpy(float), r["rel"].to_numpy(float), r["obs"].to_numpy(float)
    td, ro = r["tdate"].to_numpy(float), r["round_order"].to_numpy(float)
    codes, _ = pd.factorize(pd.concat([r["tournament_id"].astype(str), t["tournament_id"].astype(str)]))
    r_tid, t_tid = codes[:len(r)], codes[len(r):]
    t_es, t_td, t_ro = t["es"].to_numpy(float), t["tdate"].to_numpy(float), t["round_order"].to_numpy(float)
    # the field's mean as of each target day
    mu = np.full(n, np.nan)
    days_u = np.unique(t_es[np.isfinite(t_es)])
    for chunk in np.array_split(days_u, max(1, len(days_u) // 200)):
        m = (rel[None, :] <= chunk[:, None] + peek) & (ob[None, :] >= chunk[:, None] - NORMAL_WINDOW)
        cnt = m.sum(1)
        s = (m * v[None, :]).sum(1)
        val = np.where(cnt > 0, s / np.maximum(cnt, 1), 0.0)
        pos = np.searchsorted(days_u, t_es)
        sel = np.isin(t_es, chunk)
        mu[sel] = val[np.searchsorted(chunk, t_es[sel])]
    out = {k: np.full(n, np.nan) for k in ("recent", "normal", "dev")}
    k_rec, k_norm = np.zeros(n, np.int64), np.zeros(n, np.int64)
    groups = r.groupby("player_id", sort=False).indices
    valid = t["player_id"].notna().to_numpy() & np.isfinite(t_es)
    tg = pd.Series(np.arange(n))[valid].groupby(t["player_id"].to_numpy()[valid]).indices
    for pid, loc in tg.items():
        ti = np.arange(n)[valid][loc]
        ri = groups.get(pid)
        if ri is None:
            continue
        es = t_es[ti, None]
        earlier = (td[ri][None, :] < t_td[ti, None]) | ((r_tid[ri][None, :] == t_tid[ti, None])
                                                         & (ro[ri][None, :] < t_ro[ti, None]))
        ok = earlier & (rel[ri][None, :] <= es + peek) & (ob[ri][None, :] >= es - NORMAL_WINDOW)
        rec = ok & (ob[ri][None, :] >= es - window)
        vv = v[ri][None, :]
        if mode == "prev":
            pos = np.where(rec, np.arange(len(ri))[None, :], -1).max(1)
            has = pos >= 0
            recent = np.where(has, v[ri][np.maximum(pos, 0)], np.nan)
            kr = has.astype(np.int64)
            norm = ok & (np.arange(len(ri))[None, :] != pos[:, None])
        else:
            kr = rec.sum(1)
            recent = np.where(kr > 0, (rec * vv).sum(1) / np.maximum(kr, 1), np.nan)
            norm = ok & ~rec
        kn = norm.sum(1)
        sn = (norm * vv).sum(1)
        normal = (sn + k0 * mu[ti]) / (kn + k0)
        out["recent"][ti], out["normal"][ti] = recent, normal
        out["dev"][ti] = np.where(kr > 0, recent - normal, np.nan)
        k_rec[ti], k_norm[ti] = kr, kn
    res = pd.DataFrame(out)
    res["k_recent"], res["k_normal"], res["mu"] = k_rec, k_norm, mu
    return res


def match_values(t: pd.DataFrame, dev: np.ndarray) -> pd.DataFrame:
    """A - B per men's frame match (a missing side counts 0; NaN when both are missing)."""
    a = t["side"].eq("A").to_numpy()
    assert (t.loc[a, "match_id"].to_numpy() == t.loc[~a, "match_id"].to_numpy()).all()
    da, db = dev[a], dev[~a]
    x = np.where(np.isfinite(da) | np.isfinite(db), np.nan_to_num(da) - np.nan_to_num(db), np.nan)
    return pd.DataFrame({"match_id": t.loc[a, "match_id"].to_numpy(), "season": t.loc[a, "season"].to_numpy(),
                         "x": x, "a_has": np.isfinite(da), "b_has": np.isfinite(db)})


def probe_window(rows: pd.DataFrame, t: pd.DataFrame, mode: str, window: float, days: list[float],
                 seed: int = 20261016, peek: float = 7.0) -> dict:
    """Cut-scramble probe: on day D the rows released after D (rel > D) get random values; no target side with es <= D
    may move (dev, recent, normal, mu; exact). Leaky control: the same with rows admitted up to `peek` days after es
    (longer than the rows' release lag, so that a leak could reach them): some side with es <= D must move."""
    rng = np.random.default_rng(seed)
    base = window_dev(rows, t, mode, window)
    base_lk = window_dev(rows, t, mode, window, peek=peek)
    es = t["es"].to_numpy(float)
    recs, moved, leaky = [], 0, 0
    sd = float(np.nanstd(rows["v"]))
    for D in days:
        q = rows.copy()
        late = q["rel"].to_numpy(float) > D
        q.loc[late, "v"] = rng.uniform(-4 * sd, 4 * sd, int(late.sum()))
        chk = np.flatnonzero(es <= D)
        got = window_dev(q, t.iloc[chk].reset_index(drop=True), mode, window)
        b0 = base.iloc[chk].reset_index(drop=True)
        diff = np.zeros(len(chk), bool)
        for c in ("dev", "recent", "normal", "mu"):
            x0, x1 = b0[c].to_numpy(float), got[c].to_numpy(float)
            diff |= ~((x0 == x1) | (np.isnan(x0) & np.isnan(x1)))
        moved += int(diff.sum())
        near = np.flatnonzero((es <= D) & (es >= D - 28.0))
        lk = window_dev(q, t.iloc[near].reset_index(drop=True), mode, window, peek=peek)
        l0 = base_lk.iloc[near].reset_index(drop=True)
        lm = ~((l0["dev"].to_numpy() == lk["dev"].to_numpy()) | (l0["dev"].isna().to_numpy() & lk["dev"].isna().to_numpy()))
        leaky += int(lm.sum())
        recs.append({"day": D, "date": str(pd.Timestamp("1970-01-01") + pd.Timedelta(days=D))[:10],
                     "rows_scrambled": int(late.sum()), "sides_checked": int(len(chk)), "moved": int(diff.sum()),
                     "leaky_sides": int(len(near)), "leaky_moved": int(lm.sum())})
        log(f"  probe {recs[-1]['date']}: checked {len(chk)}, moved {int(diff.sum())}; leaky {int(lm.sum())}/{len(near)}")
    return {"days": len(days), "moved": moved, "leaky_control_moved": leaky, "pass": bool(moved == 0 and leaky > 0),
            "leaky_peek_days": peek, "values_checked": ["dev", "recent", "normal", "mu"], "tolerance": "exact",
            "per_day": recs}


LEVEL_GROUPS = [("slam_main", lambda l, q: l.eq("GS") & ~q), ("slam_qual", lambda l, q: l.eq("GS") & q),
                ("tour_main", lambda l, q: l.isin(P.TOUR_LEVELS) & ~q), ("tour_qual", lambda l, q: l.isin(P.TOUR_LEVELS) & q),
                ("challenger", lambda l, q: l.eq("CH")), ("other", lambda l, q: ~l.isin(("GS", "CH") + P.TOUR_LEVELS))]


def coverage_by(mv: pd.DataFrame, keys: pd.DataFrame) -> pd.DataFrame:
    s0 = pd.read_parquet(P.S0, columns=["match_id", "level", "qualifying"]).rename(columns={"match_id": "cur"})
    k = keys[["match_id", "rebuilt_id"]].assign(cur=remap_ids(keys["rebuilt_id"]).to_numpy())
    k = k.merge(s0, on="cur", how="left")
    m = mv.merge(k[["match_id", "level", "qualifying"]], on="match_id", how="left")
    lv, q = m["level"].fillna(""), m["qualifying"].fillna(False).astype(bool)
    m["group"] = "other"
    for name, rule in LEVEL_GROUPS:
        m.loc[rule(lv, q).to_numpy(), "group"] = name
    m["either"] = m["a_has"] | m["b_has"]
    m["both"] = m["a_has"] & m["b_has"]
    return (m.groupby(["season", "group"]).agg(matches=("x", "size"), either_side=("either", "sum"),
                                                both_sides=("both", "sum")).reset_index())


def cmd_window(kind: str, probe: bool = True) -> dict:
    keys = ext_keys()
    if kind == "fade":
        rows, info = fade_rows()
        t = targets_of(keys, "timing")
        mode, window, col = "prev", FADE_WINDOW, "fade_dev_14"
    else:
        rows, info = fault_rows()
        t = targets_of(keys, "keys")
        mode, window, col = "mean", FAULT_WINDOW, "fault_dev_28"
    log(f"{kind}: {len(rows)} men's player-matches; {len(t)} target sides")
    dev = window_dev(rows, t, mode, window)
    mv = match_values(t, dev["dev"].to_numpy())
    # the builder columns' scale rule: A - B over its SD (men's 2022-23 matches with a value; all seasons when fewer
    # than 100), clipped at +-4 SD (outcome-free; it caps a speed gun's glitch)
    xs = mv.loc[mv["season"].between(*SD_SEASONS), "x"].dropna()
    sd = float(xs.std(ddof=1)) if len(xs) >= 100 else float(mv["x"].dropna().std(ddof=1))
    mv[col] = np.clip(mv["x"] / sd, -F.CLIP, F.CLIP)
    mv[f"{col}_kmh"] = mv["x"]
    out = keys[["match_id", "tour", "season"]].merge(mv[["match_id", col, f"{col}_kmh"]], on="match_id", how="left")
    out.loc[out["tour"].eq("wta"), [col, f"{col}_kmh"]] = 0.0
    cov = coverage_by(mv, keys)
    OUT.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT / f"{col}.parquet", index=False)
    cov.to_csv(OUT / f"{col}_coverage.csv", index=False)
    rows.drop(columns=[c for c in ("player_a_id", "player_b_id") if c in rows.columns]).to_parquet(
        OUT / f"{kind}_rows.parquet", index=False)
    side = dev.assign(match_id=t["match_id"].to_numpy(), side=t["side"].to_numpy(), season=t["season"].to_numpy())
    meta = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "reads_results": False,
            "column": col, "mode": mode, "window_days": window, "normal_window_days": NORMAL_WINDOW, "k0": K0,
            "rows": info, "clock": "timing.parquet (lf + 1 / es)" if kind == "fade" else
            "scenario B release days (availability.parquet), the builder's es",
            "value_units": f"{col}: (A - B) / sd, clipped at +-4; {col}_kmh: A - B in km/h",
            "sd_km_h": sd, "clipped": int((np.abs(mv[col]) >= F.CLIP).sum()),
            "sides_with_recent": int(np.isfinite(dev["dev"]).sum()),
            "side_dev_sd_km_h": float(np.nanstd(dev["dev"])), "side_recent_sd_km_h": float(np.nanstd(dev["recent"])),
            "men_matches_nonmissing_by_season": out[out["tour"].eq("atp")].groupby("season")[col]
            .apply(lambda s: int(s.notna().sum())).to_dict(),
            "sha256": {f"{col}.parquet": sha256(OUT / f"{col}.parquet"), "speed_ext.py": sha256(Path(__file__))}}
    if kind == "fault":
        # coverage the instant rule (lf + 1, as live Slam feeds would allow) would give: counts only
        ri = rows.assign(rel=rows["rel_instant"])
        di = window_dev(ri, t, mode, window)
        mi = match_values(t, di["dev"].to_numpy())
        meta["instant_rule_men_matches_nonmissing_by_season"] = mi.groupby("season")["x"].apply(
            lambda s: int(s.notna().sum())).to_dict()
    if probe:
        days = FL.probe_days(keys)
        rr = rows.copy()
        # the leaky control must reach past the rows' release lag: lf + 1 for the fade; scenario B's Slam release
        # (up to 22 days after lf + 1) for fault speed
        lag = float(np.nanmax(rr["rel"].to_numpy(float) - rr["lf"].to_numpy(float) - 1.0))
        meta["probe"] = probe_window(rr, t, mode, window, days, peek=max(7.0, lag + 8.0))
        meta["probe"]["release_lag_max_days"] = lag
        log(f"{kind} probe: moved {meta['probe']['moved']}, leaky {meta['probe']['leaky_control_moved']} -> "
            f"pass {meta['probe']['pass']}")
    write_json(OUT / f"{col}.json", meta)
    side.to_parquet(OUT / f"{col}_sides.parquet", index=False)
    return meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["reproduce", "constants", "build", "probe", "fade", "fault"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--no-probe", action="store_true")
    a = ap.parse_args()
    if a.cmd == "reproduce":
        cmd_reproduce()
    elif a.cmd == "constants":
        constants()
    elif a.cmd == "build":
        cmd_build()
    elif a.cmd == "probe":
        cmd_probe(a.arg)
    else:
        cmd_window(a.cmd, probe=not a.no_probe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
