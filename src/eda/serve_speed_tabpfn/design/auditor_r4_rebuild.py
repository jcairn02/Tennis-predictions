"""R4 red team (auditor): an independent rebuild of spd_f, spd_f_all and spd_raw from the audit's spec (2_audit.md C1-C4),
compared with the R3 build (features/speed.parquet). Feature values only; no match result, no statistic target, no price.

Independence. Nothing here imports panel.py or features.py. The records come from the R1 extraction
(engineer_records.parquet: per-source point means, key statistics, AO match centre); the choice rule, the drops, the
families, the as-of offsets, the frame join, the histories, the filter and the columns are this file's or auditor_lib's.
A separate check compares the R3 panel's point means with the shot-level study's own stage1_match_stats.

Spec choices left open (switched, to attribute any residual):
    dup_after_round  the key-statistic duplicate check runs after the round-mismatch rule (panel.py) or before (R2 lib)
    mislink_level    panel.py's added rule (a Slam feed on a non-Slam match, an ATP-tour feed on a Slam): on / off
    floor_obs        obs floored to whole days (panel.py deviation 4) or kept as timing's value
    reref            gamma re-referenced (men's tour main draws average 0 with 200+ rows, else the Slam main draws) before
                     the families' fallback means; the "else 0" fallback then means the reference level (panel.py) - or
                     not re-referenced (the R2 lib)
Variants: 'spec' = C1-C4 read literally with the engineer's documented choices (all four on) is compared first; then each
switch is turned off alone to measure its share of the residual.

Agreement (C7): the A - B difference in units of the build's s_f (2.2240 km/h): correlation, and the share of matches
with |difference| <= 0.05 s_f, on all 63,737 frame matches and on men only (also by season, and spd_f_all for women).

Run: ./python.sh src/eda/serve_speed_tabpfn/design/auditor_r4_rebuild.py
Writes data/studies/serve_speed_tabpfn/design/auditor_r4_rebuild.json and auditor_r4_features.parquet (my columns)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.design import auditor_lib as AL  # noqa: E402
from src.eda.serve_speed_tabpfn.design import engineer_common as EC  # noqa: E402

OUT = AL.OUT / "auditor_r4_rebuild.json"
FEAT_OUT = AL.OUT / "auditor_r4_features.parquet"
BUILD = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "features" / "speed.parquet"
R3_PANEL = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "speed_panel.parquet"
PRIORITY = ["infosys_slams", "sirgenkii", "infosys", "slam_tracking", "slamtracker", "slam_pbp"]
SLAM_ONLY = {"slam_pbp", "slam_tracking", "slamtracker", "infosys_slams", "ausopen_mc"}
TOUR_ONLY = {"infosys", "mantennisdata", "handoff_ks"}
TOUR_LEVELS = ("T250", "T500", "T1000", "FIN")
MEN = {"hl": 14.0, "s2f": 12.0, "q": 4.0 / 365, "c": 2.0, "nu_pm": 7.0, "nu_ks": 8.0}
WOMEN = {"hl": 14.0, "s2f": 12.0, "q": 4.0 / 365, "c": 4.0, "nu_pm": 14.0, "nu_ks": 10.0}
SIGMA = {"atp": 13.49, "wta": 10.72}
S_F_BUILD = 2.223995373606193
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------ C1 panel
def panel(dup_after_round: bool, mislink_level: bool, floor_obs: bool, round_rowlevel: bool = True) -> pd.DataFrame:
    r = pd.read_parquet(EC.RECORDS)
    r = r[r["linked"] & r["spd1"].notna()].copy()
    s0 = EC.stage0(cols=["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "tournament_id",
                         "tournament_name", "tournament_date", "player_a_id", "player_b_id"])
    lev = s0.set_index("match_id")["level"]
    r["level"] = r["match_id"].map(lev)
    r = r[r["level"].notna()]
    # round mismatch (ManTennisData only)
    sp = pd.read_parquet(EC.SPEEDS, columns=["source", "source_key", "round", "match_id", "side", "ks_spd1"])
    sp = sp[sp["source"].eq("mantennisdata") & sp["match_id"].notna() & sp["ks_spd1"].notna()]
    sp = sp.merge(s0[["match_id", "round"]].rename(columns={"round": "round_s0"}), on="match_id", how="left")
    keyc = list(zip(r["match_id"], r["side"]))
    if round_rowlevel:
        # per record: the R1 records keep ManTennisData's source_key, so each record's own round label is known
        bad = sp[sp["round"].astype(str) != sp["round_s0"].astype(str)]
        mis_rec = set(zip(bad["source_key"].astype(str), bad["match_id"], bad["side"]))
        is_mis = r["source"].eq("mantennisdata").to_numpy() & np.array(
            [(str(s), m_, s_) in mis_rec for s, m_, s_ in zip(r["source_key"], r["match_id"], r["side"])])
    else:
        # per key (the first R4 run): a key with ANY mismatched ManTennisData row loses all its ManTennisData records
        mis = sp[sp["round"].astype(str) != sp["round_s0"].astype(str)][["match_id", "side"]].drop_duplicates()
        mis_key = set(zip(mis["match_id"], mis["side"]))
        is_mis = r["source"].eq("mantennisdata").to_numpy() & np.array([k in mis_key for k in keyc])
    lvl_bad = (r["source"].isin(SLAM_ONLY) & r["level"].ne("GS")) | (r["source"].isin(TOUR_ONLY) & r["level"].eq("GS"))
    valid = np.ones(len(r), bool)
    valid &= ~(r["basis"].eq("point_mean") & ~r["gate_half"].astype(bool)).to_numpy()
    if dup_after_round:
        valid &= ~is_mis
    if mislink_level:
        valid &= ~lvl_bad.to_numpy()
    for src in ("mantennisdata", "handoff_ks", "ausopen_mc"):
        sel = r["source"].eq(src).to_numpy() & valid
        g = r[sel].groupby(["match_id", "side"])["spd1"].agg(["size", "min", "max"])
        bad = g[(g["size"] > 1) & (g["max"] - g["min"] > 0.5)].index
        badk = set(bad)
        valid &= ~(r["source"].eq(src).to_numpy() & np.array([k in badk for k in keyc]))
    if not dup_after_round:
        valid &= ~is_mis
    r = r[valid].copy()
    shift = r["basis"].map({"point_mean": 0.0, "keystat_atp": -0.5, "mc_rounded": 0.5})
    r["y"] = r["spd1"] + shift
    r["b"] = np.where(r["basis"].eq("keystat_atp"), "ks", "pts")
    r["kind"] = r["basis"].map({"point_mean": "pts", "keystat_atp": "ks", "mc_rounded": "mc"})
    slam = r["level"].eq("GS").to_numpy()
    r["krank"] = np.where(r["kind"].eq("mc"), 2, np.where(r["kind"].eq("pts"), np.where(slam, 0, 1),
                                                          np.where(slam, 1, 0)))
    r["nrank"] = np.where(r["kind"].eq("pts"), -r["n1"].fillna(0), 0)
    r["srank"] = r["source"].map({**{s: i for i, s in enumerate(PRIORITY)}, "mantennisdata": 0, "handoff_ks": 1,
                                  "ausopen_mc": 0}).fillna(9)
    r = r.sort_values(["match_id", "side", "krank", "nrank", "srank"]).drop_duplicates(["match_id", "side"])
    p = r[["match_id", "side", "source", "b", "y", "n1"]].rename(columns={"n1": "n", "b": "basis"}).merge(
        s0, on="match_id", how="inner")
    p["player_id"] = np.where(p["side"].eq("A"), p["player_a_id"], p["player_b_id"])
    p = p.drop(columns=["player_a_id", "player_b_id"])
    tm = pd.read_parquet(EC.TIMING, columns=["match_id", "es", "lf", "obs"])
    p = p.merge(tm, on="match_id", how="left")
    p = p[p["es"].notna() & p["lf"].notna() & p["obs"].notna()]
    if floor_obs:
        p["obs"] = np.floor(p["obs"])
    p["n"] = p["n"].fillna(0).round()
    p = p[p["n"].ge(10)]
    p = p[~((p["tour"].eq("atp") & (p["y"] < 120)) | (p["tour"].eq("wta") & (p["y"] < 100)))]
    p["tdate"] = p["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    sl = EC.slam_of(p["level"], p["tournament_name"]).to_numpy()
    draw = np.where(p["qualifying"].astype(bool), "Q", "M")
    base = np.where(sl != "", sl, np.where(p["level"].isin(TOUR_LEVELS), "tour",
                                           np.where(p["level"].eq("CH"), "ch", "other")))
    p["fam"] = np.char.add(np.char.add(base.astype(str), "|"), draw.astype(str))
    p["edition"] = p["tournament_id"].astype(str) + "|" + draw + "|" + p["basis"]
    p["slam"] = sl
    p = p.sort_values(["tour", "player_id", "tdate", "tournament_id", "round_order", "obs", "match_id"],
                      kind="mergesort").reset_index(drop=True)
    return p


# ------------------------------------------------------------------------------------------------ C2 offsets
class Snap:
    """As-of offsets (my implementation of C2); reref: re-reference to the men's tour main draws (200+ rows) else the
    Slam main draws before the family means and the 0 fallback."""

    def __init__(self, p: pd.DataFrame, reref: bool):
        self.rel = p["lf"].to_numpy(float) + 1.0
        self.obs = p["obs"].to_numpy(float)
        self.y = p["y"].to_numpy(float)
        self.w = 1.0 / (22.0 + 12.4 ** 2 / np.maximum(p["n"].to_numpy(float), 1.0))
        self.pid = pd.factorize(p["player_id"])[0]
        self.ed, self.ed_u = pd.factorize(p["edition"])
        fam = p.drop_duplicates("edition").set_index("edition")["fam"].reindex(self.ed_u).to_numpy()
        self.fam_idx, fam_u = pd.factorize(fam)
        self.fam_u = pd.Index(fam_u)
        self.tour_main = self.fam_u.get_indexer(["tour|M"])[0]
        self.slam_main = [self.fam_u.get_loc(f) for f in ("AO|M", "RG|M", "W|M", "USO|M") if f in self.fam_u]
        self.reref = reref
        self.cache: dict = {}

    def at(self, day: float) -> np.ndarray:
        if day in self.cache:
            return self.cache[day]
        m = (self.rel <= day) & (self.obs >= day - 364.0)
        g_all = np.zeros(len(self.ed_u))
        if m.sum() >= 50:
            y, w = self.y[m], self.w[m]
            _, pi = np.unique(self.pid[m], return_inverse=True)
            eu, ei = np.unique(self.ed[m], return_inverse=True)
            fe = self.fam_idx[eu]
            _, fi = np.unique(fe, return_inverse=True)
            wp, we = np.bincount(pi, weights=w), np.bincount(ei, weights=w)
            wf = np.bincount(fi, weights=we)
            kw = 25.0 * float(np.mean(w))
            g = np.zeros(len(eu))
            for _ in range(60):
                a = np.bincount(pi, weights=w * (y - g[ei])) / wp
                r = np.bincount(ei, weights=w * (y - a[pi]))
                g_new = (r + kw * (np.bincount(fi, weights=r) / wf)[fi]) / (we + kw)
                done = np.max(np.abs(g_new - g)) < 1e-6
                g = g_new
                if done:
                    break
            if self.reref:
                n_e = np.bincount(ei)
                ref = fe == self.tour_main
                if n_e[ref].sum() < 200:
                    ref = np.isin(fe, self.slam_main)
                if ref.any():
                    g = g - np.average(g[ref], weights=n_e[ref])
            fmean = pd.Series(g).groupby(fe).mean()
            g_all = np.array(pd.Series(self.fam_idx).map(fmean).fillna(0.0).to_numpy(float), copy=True)
            g_all[eu] = g
        self.cache[day] = g_all
        return g_all


# ------------------------------------------------------------------------------------------------ C4 frame sides
def frame_sides(floor_obs: bool) -> pd.DataFrame:
    fr = pd.read_parquet(EC.MODEL_FRAME, columns=["match_id", "tour", "season"])
    pre = EC.stage0(EC.S0_PRE, cols=["match_id", "player_a_id", "player_b_id"])
    f = fr.merge(pre, on="match_id", how="left", validate="one_to_one")
    remap = EC.id_map()
    f["nid"] = f["match_id"].map(lambda x: remap.get(x, x))
    tm = pd.read_parquet(EC.TIMING, columns=["match_id", "es", "lf", "obs", "tournament_id", "tournament_date",
                                            "round_order"]).rename(columns={"match_id": "nid"})
    f = f.merge(tm, on="nid", how="left", validate="one_to_one")
    if floor_obs:
        f["obs"] = np.floor(f["obs"])
    f["tdate"] = f["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    s = pd.concat([f.assign(side="A", player_id=f["player_a_id"]), f.assign(side="B", player_id=f["player_b_id"])],
                  ignore_index=True)
    return s


def registered_x(p: pd.DataFrame, t: pd.DataFrame) -> np.ndarray:
    """x_raw as registered: n-weighted means of raw y over own earlier rows with obs_t - obs_h <= 14 minus <= 364."""
    groups = {k: g.index.to_numpy() for k, g in p.groupby("player_id", sort=False)}
    td_, tid_, ro_, ob_ = (p["tdate"].to_numpy(), p["tournament_id"].to_numpy(), p["round_order"].to_numpy(),
                           p["obs"].to_numpy(float))
    y_, n_ = p["y"].to_numpy(float), p["n"].to_numpy(float)
    out = np.full(len(t), np.nan)
    tt = t.reset_index(drop=True)
    for pid, g in tt.groupby("player_id", sort=False):
        ix = groups.get(pid)
        if ix is None:
            continue
        for i, a, b_, c_, o in zip(g.index, g["tdate"].to_numpy(), g["tournament_id"].to_numpy(),
                                   g["round_order"].to_numpy(), g["obs"].to_numpy(float)):
            e = (td_[ix] < a) | ((tid_[ix] == b_) & (ro_[ix] < c_))
            age = o - ob_[ix]
            w14, w364 = e & (age <= 14), e & (age <= 364)
            if not w14.any():
                continue
            nn = n_[ix]
            yy = y_[ix]
            out[i] = (nn[w14] * yy[w14]).sum() / nn[w14].sum() - (nn[w364] * yy[w364]).sum() / nn[w364].sum()
    return out


def build(dup_after_round=True, mislink_level=True, floor_obs=True, reref=True,
          round_rowlevel=True) -> tuple[pd.DataFrame, float, dict]:
    p = panel(dup_after_round, mislink_level, floor_obs, round_rowlevel)
    t = frame_sides(floor_obs)
    ok = t["player_id"].notna() & t["es"].notna()
    snaps = {tour: Snap(p[p["tour"] == tour].reset_index(drop=True), reref) for tour in ("atp", "wta")}
    # map panel rows to their tour-local edition index for the snapshot lookup
    ed_idx = np.full(len(p), -1)
    for tour, s in snaps.items():
        mm = (p["tour"] == tour).to_numpy()
        ed_idx[mm] = pd.Index(s.ed_u).get_indexer(p.loc[mm, "edition"])
    f_hat = np.zeros(len(t))
    tv = t[ok].reset_index()
    h = AL.histories(p, tv.rename(columns={"index": "_i"}))
    idx = h["idx"]
    okh = idx >= 0
    y = p["y"].to_numpy(float)
    Z = np.full(idx.shape, np.nan)
    for (tour, day), g in tv.groupby(["tour", "es"], sort=False):
        rows = g.index.to_numpy()
        gam = snaps[tour].at(float(day))
        ii = idx[rows]
        e = ed_idx[np.maximum(ii, 0)]
        Z[rows] = np.where(ii >= 0, y[np.maximum(ii, 0)] - gam[np.maximum(e, 0)], np.nan)
    D = np.where(okh, p["obs"].to_numpy(float)[np.maximum(idx, 0)], np.nan)
    nb = np.where(p["basis"].eq("ks").to_numpy(), "ks", "pm")
    fh = np.zeros(len(tv))
    for tour, prm in (("atp", MEN), ("wta", WOMEN)):
        sel = np.flatnonzero(tv["tour"].to_numpy() == tour)
        nu = np.where(nb == "ks", prm["nu_ks"], prm["nu_pm"])
        r_row = nu + SIGMA[tour] ** 2 / p["n"].to_numpy(float)
        R = np.where(okh[sel], r_row[np.maximum(idx[sel], 0)], np.nan)
        kf = AL.kalman_batch(Z[sel], R, D[sel], tv["es"].to_numpy(float)[sel], prm)
        fh[sel] = kf["f_hat"]
    f_hat[tv["index"].to_numpy()] = fh
    xr = np.full(len(t), np.nan)
    xr[tv["index"].to_numpy()] = registered_x(p, tv)
    t = t.assign(f_hat=f_hat, x_raw=xr)
    a, b = t[t["side"] == "A"].set_index("match_id"), t[t["side"] == "B"].set_index("match_id")
    m = a[["tour", "season"]].copy()
    m["d"] = a["f_hat"] - b["f_hat"]
    m["xr"] = a["x_raw"] - b["x_raw"]
    men = m["tour"].eq("atp")
    s_f = float(m.loc[men & m["season"].between(2022, 2023), "d"].std(ddof=1))
    m["spd_f"] = np.where(men, np.clip(m["d"] / s_f, -4, 4), 0.0)
    m["spd_f_all"] = np.clip(m["d"] / s_f, -4, 4)
    m["spd_raw"] = np.where(men & m["xr"].notna(), np.clip(m["xr"] / 5.998, -4, 4), np.nan)
    info = {"panel_rows": int(len(p)), "panel_by_tour": p.groupby("tour").size().to_dict()}
    return m.reset_index(), s_f, info


def agree(mine: pd.DataFrame, s_f_mine: float) -> dict:
    b = pd.read_parquet(BUILD, columns=["match_id", "tour", "season", "spd_f", "spd_f_all", "spd_raw",
                                        "spd_f_unclipped_km_h"])
    j = b.merge(mine, on="match_id", suffixes=("_b", "_m"), validate="one_to_one")
    out = {"matches": int(len(j)), "s_f_mine": s_f_mine, "s_f_build": S_F_BUILD}
    # spd_f in common units: the build's s_f applied to both unclipped differences, then clipped
    db = np.clip(j["spd_f_unclipped_km_h"] / S_F_BUILD, -4, 4)
    dm = np.clip(j["d"] / S_F_BUILD, -4, 4)
    men = j["tour_b"].eq("atp").to_numpy()
    spd_b = np.where(men, db, 0.0)
    spd_m = np.where(men, dm, 0.0)

    def stats(x, y, m):
        if not np.any(m):
            return {"n": 0}
        dd = np.abs(x[m] - y[m])
        return {"n": int(m.sum()), "corr": float(np.corrcoef(x[m], y[m])[0, 1]) if np.std(x[m]) > 0 else None,
                "share_within_0.05": float(np.mean(dd <= 0.05)), "share_within_0.01": float(np.mean(dd <= 0.01)),
                "p99_abs_diff": float(np.quantile(dd, 0.99)), "max_abs_diff": float(dd.max())}
    allm = np.ones(len(j), bool)
    out["spd_f_all_matches"] = stats(spd_b, spd_m, allm)
    out["spd_f_men"] = stats(spd_b, spd_m, men)
    out["spd_f_men_by_season"] = {int(s): stats(spd_b, spd_m, men & (j["season_b"] == s).to_numpy())
                                  for s in sorted(j["season_b"].unique()) if s >= 2014}
    wom = ~men
    out["spd_f_all_col_women"] = stats(db.to_numpy(), dm.to_numpy(), wom)
    out["spd_f_all_col_all"] = stats(db.to_numpy(), dm.to_numpy(), allm)
    # the column as stored (each side's own s_f)
    out["spd_f_as_stored_all"] = stats(j["spd_f_b"].to_numpy(), j["spd_f_m"].to_numpy(), allm)
    # spd_raw: presence pattern and values
    pb, pm = j["spd_raw_b"].notna().to_numpy(), j["spd_raw_m"].notna().to_numpy()
    both = pb & pm
    out["spd_raw"] = {"present_build": int(pb.sum()), "present_mine": int(pm.sum()), "present_both": int(both.sum()),
                      "presence_disagree": int((pb ^ pm).sum()),
                      **{k: v for k, v in stats(j["spd_raw_b"].to_numpy(), j["spd_raw_m"].to_numpy(), both).items()
                         if k != "n"}}
    return out


def point_mean_check() -> dict:
    """The R3 panel's chosen point means against the shot-level study's stage1_match_stats (an independent extraction):
    same source, same player-match."""
    p = pd.read_parquet(R3_PANEL, columns=["match_id", "side", "source", "kind", "y", "n", "use"])
    p = p[p["use"] & p["kind"].eq("point_mean") & p["source"].isin(["slam_pbp", "slam_tracking", "slamtracker",
                                                                       "infosys", "sirgenkii"])]
    st = pd.read_parquet(EC.SHOT / "stage1_match_stats.parquet", columns=["match_id", "side", "spd1_n", "spd1_d",
                                                                          "spd1_src"])
    remap = EC.id_map()
    st["match_id"] = st["match_id"].map(lambda x: remap.get(x, x))
    st = st[st["spd1_d"] > 0]
    st["pm"] = st["spd1_n"] / st["spd1_d"]
    j = p.merge(st, on=["match_id", "side"], how="inner")
    j = j[j["source"] == j["spd1_src"]]
    d = (j["y"] - j["pm"]).abs()
    return {"compared": int(len(j)), "share_equal_1e-6": float(np.mean(d < 1e-6)),
            "share_within_0.1": float(np.mean(d <= 0.1)), "max_abs_diff": float(d.max()),
            "n_equal": float(np.mean(j["n"] == j["spd1_d"]))}


def main() -> None:
    res = {"reads_results": False}
    log("point means of the R3 panel against stage1_match_stats")
    res["point_mean_check"] = point_mean_check()
    log(json.dumps(res["point_mean_check"]))
    variants = {"spec": {}, "round_check_per_key": {"round_rowlevel": False}, "no_reref": {"reref": False},
                "dup_before_round": {"dup_after_round": False}, "no_mislink_level": {"mislink_level": False},
                "obs_unfloored": {"floor_obs": False}}
    res["variants"] = {}
    keep = None
    for name, kw in variants.items():
        log(f"variant {name}")
        m, s_f, info = build(**kw)
        a = agree(m, s_f)
        a["panel"] = info
        res["variants"][name] = a
        log(f"  {name}: s_f {s_f:.4f}; spd_f all within 0.05: {a['spd_f_all_matches']['share_within_0.05']:.4f}; "
            f"men {a['spd_f_men']['share_within_0.05']:.4f} (corr {a['spd_f_men']['corr']:.5f}); "
            f"women spd_f_all {a['spd_f_all_col_women']['share_within_0.05']:.4f}; spd_raw presence disagree "
            f"{a['spd_raw']['presence_disagree']}, values within 0.05 {a['spd_raw']['share_within_0.05']:.4f}")
        if name == "spec":
            keep = m
    keep.to_parquet(FEAT_OUT, index=False)
    OUT.write_text(json.dumps(res, indent=1, default=float) + "\n", encoding="utf-8")
    log(f"wrote {OUT.name}")


if __name__ == "__main__":
    main()
