"""Latency red team (auditor): an independent rebuild of spd_B_M0 and spd_B_M1 from latency/availability.parquet's
release_B, my own panel (auditor_r4_rebuild.panel, which equals the R3 panel's use rows), the frozen constants and the
variants' own SDs. features_latency.py is NOT imported. Feature values only: no outcome, result, target or price.

Scenario B (plan.md; 1_engineer.md; 2_modeller.md):
    history   the side's own earlier rows (earlier tdate, or the same tournament at an earlier round), obs >= es - 364,
              AND release_B <= es
    offsets   the as-of edition snapshot at es, fitted on rows with release_B <= es (obs >= es - 364); the panel.py
              reference and fallback conventions
    filter    the frozen men's constants; half-life 14 d (M0) or 28 d (M1); projected to es
    column    clip(dfhat / SD_variant, +-4), SD_variant from variants_meta.json (also recomputed here); women 0
Also:
    the release rule itself against 1_engineer.md (weekday mapping, Mondays, Slams = last main-draw day + 3)
    the share of men's 2024-26 frame sides whose history holds a row of their own current event, under B and A

Run: ./python.sh src/eda/serve_speed_tabpfn/design/auditor_lat_rebuild.py
Writes data/studies/serve_speed_tabpfn/latency/auditor_lat_rebuild.json and auditor_lat_variants.parquet
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
from src.eda.serve_speed_tabpfn.design import auditor_r4_rebuild as R4  # noqa: E402

LAT = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "latency"
AV = LAT / "availability.parquet"
VAR = LAT / "variants.parquet"
META = LAT / "variants_meta.json"
OUT = LAT / "auditor_lat_rebuild.json"
FEAT_OUT = LAT / "auditor_lat_variants.parquet"
MEN = {"hl": 14.0, "s2f": 12.0, "q": 4.0 / 365, "c": 2.0, "nu_pm": 7.0, "nu_ks": 8.0}
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


FROZEN_PANEL = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "speed_panel.parquet"


def panel_with_release(frozen: bool = True) -> pd.DataFrame:
    """The panel the variants were built on. frozen=True reads speed_panel.parquet (13:49, SHA-256 f774eb50..., the
    study's pinned panel; read as data, panel.py not imported). frozen=False rebuilds it with my R4 code, which since
    16:21 mixes the R1 records (old speeds.parquet) with the acquisition's corrected round labels and so admits 4 rows
    of two mislinked QF records (see 4_audit.md)."""
    if frozen:
        p = pd.read_parquet(FROZEN_PANEL)
        p = p[p["use"]].rename(columns={"family": "fam"}).copy()
        p = p.sort_values(["tour", "player_id", "tdate", "tournament_id", "round_order", "obs", "match_id"],
                          kind="mergesort").reset_index(drop=True)
    else:
        p = R4.panel(True, True, True, True)
    a = pd.read_parquet(AV, columns=["match_id", "side", "release_A", "release_B", "rule_B"])
    p = p.merge(a, on=["match_id", "side"], how="left", validate="one_to_one")
    assert p["release_B"].notna().all() and p["release_A"].notna().all()
    assert (p["release_A"] == p["lf"] + 1).all()
    return p


class SnapRel(R4.Snap):
    """My C2 snapshots, admitting a row from its `release` day instead of lf + 1."""

    def __init__(self, p: pd.DataFrame, release: np.ndarray):
        super().__init__(p, reref=True)
        self.rel = np.asarray(release, float)
        self.cache = {}


def side_fhat(p: pd.DataFrame, t: pd.DataFrame, release_col: str, hl: float, history_release: bool = True,
              y: np.ndarray | None = None) -> np.ndarray:
    """f_hat (km/h) of each target side under a release rule. history_release: own rows also need release <= es."""
    y = p["y"].to_numpy(float) if y is None else y
    q = p.assign(y=y)
    out = np.zeros(len(t))
    ok = (t["player_id"].notna() & t["es"].notna()).to_numpy()
    tv = t[ok].reset_index()
    h = AL.histories(q, tv)
    idx = h["idx"]
    rel = q[release_col].to_numpy(float)
    es = tv["es"].to_numpy(float)
    if history_release:
        okrel = (idx >= 0) & (rel[np.maximum(idx, 0)] <= es[:, None])
        idx = np.where(okrel, idx, -1)
    snaps = {}
    ed_idx = np.full(len(q), -1)
    for tour in ("atp", "wta"):
        mm = (q["tour"] == tour).to_numpy()
        qt = q[mm].reset_index(drop=True)
        snaps[tour] = SnapRel(qt, qt[release_col].to_numpy(float))
        ed_idx[mm] = pd.Index(snaps[tour].ed_u).get_indexer(q.loc[mm, "edition"])
    Z = np.full(idx.shape, np.nan)
    yy = q["y"].to_numpy(float)
    for (tour, day), g in tv.groupby(["tour", "es"], sort=False):
        rows = g.index.to_numpy()
        gam = snaps[tour].at(float(day))
        ii = idx[rows]
        e = ed_idx[np.maximum(ii, 0)]
        Z[rows] = np.where(ii >= 0, yy[np.maximum(ii, 0)] - gam[np.maximum(e, 0)], np.nan)
    D = np.where(idx >= 0, q["obs"].to_numpy(float)[np.maximum(idx, 0)], np.nan)
    nb = q["basis"].eq("ks").to_numpy()
    sig = {"atp": 13.49, "wta": 10.72}
    prm_w = {"hl": 14.0, "s2f": 12.0, "q": 4.0 / 365, "c": 4.0, "nu_pm": 14.0, "nu_ks": 10.0}
    fh = np.zeros(len(tv))
    for tour, prm in (("atp", dict(MEN, hl=hl)), ("wta", dict(prm_w, hl=hl))):
        sel = np.flatnonzero(tv["tour"].to_numpy() == tour)
        nu = np.where(nb, prm["nu_ks"], prm["nu_pm"])
        r_row = nu + sig[tour] ** 2 / q["n"].to_numpy(float)
        R = np.where(idx[sel] >= 0, r_row[np.maximum(idx[sel], 0)], np.nan)
        fh[sel] = AL.kalman_batch(Z[sel], R, D[sel], es[sel], prm)["f_hat"]
    out[tv["index"].to_numpy()] = fh
    return out, idx, tv


def to_match(t: pd.DataFrame, f: np.ndarray) -> pd.DataFrame:
    x = t.assign(f=f)
    a, b = x[x["side"] == "A"].set_index("match_id"), x[x["side"] == "B"].set_index("match_id")
    m = a[["tour", "season"]].copy()
    m["d"] = a["f"] - b["f"]
    return m.reset_index()


def release_rule_check(p: pd.DataFrame) -> dict:
    a = pd.read_parquet(AV, columns=["match_id", "side", "tour", "year", "level", "qualifying", "tournament_id", "slam",
                                     "use", "lf", "release_A", "release_B", "rule_B", "slam_last_main_day"])
    u = a[a["use"]].copy()
    res = {"use_rows": int(len(u)), "release_B_ge_A_all_rows": bool((a["release_B"] >= a["release_A"]).all())}
    wd = ((u["lf"] + 3) % 7).astype(int)                 # 1970-01-01 was a Thursday: (days + 3) % 7, Monday = 0
    rel_wd = ((u["release_B"] + 3) % 7).astype(int)
    ns = u["rule_B"].eq("mantd_weekly_sunday")
    expected = {0: 7, 1: 6, 2: 5, 3: 4, 4: 3, 5: 9, 6: 8}
    lag = (u["release_B"] - u["lf"])
    res["non_slam"] = {"rows": int(ns.sum()), "level_not_GS": bool(u.loc[ns, "level"].ne("GS").all()),
                       "release_on_monday": float((rel_wd[ns] == 0).mean()),
                       "lag_matches_weekday_rule": float((lag[ns] == wd[ns].map(expected)).mean()),
                       "lag_by_lf_weekday": {int(k): sorted(map(int, v.unique()))
                                             for k, v in lag[ns].groupby(wd[ns])}}
    sl = u["rule_B"].eq("slam_after_event")
    res["slam"] = {"rows": int(sl.sum()), "level_GS": bool(u.loc[sl, "level"].eq("GS").all()),
                   "release_eq_last_main_day_plus_3": float((u.loc[sl, "release_B"]
                                                             == u.loc[sl, "slam_last_main_day"] + 3).mean()),
                   "one_release_per_slam_year": bool(u[sl].groupby(["year", "slam"])["release_B"].nunique().max() == 1),
                   "qualifying_rows": int((sl & u["qualifying"].astype(bool)).sum())}
    # recompute the last main-draw day independently: the latest lf of the Slam-year's main-draw singles, both tours
    s0 = pd.read_parquet(ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet",
                         columns=["match_id", "year", "level", "qualifying", "tournament_name"])
    s0 = s0[s0["level"].eq("GS") & ~s0["qualifying"].astype(bool)]
    tm = pd.read_parquet(ROOT / "data" / "studies" / "match_timing" / "timing.parquet", columns=["match_id", "lf"])
    s0 = s0.merge(tm, on="match_id")
    n = s0["tournament_name"].fillna("").str.lower()
    s0["slam"] = np.select([n.str.contains("austral"), n.str.contains("roland|french"), n.str.contains("wimbledon"),
                            n.str.contains("us open|u.s. open")], ["AO", "RG", "W", "USO"], "")
    last = s0.groupby(["year", "slam"])["lf"].max()
    mine = u[sl].apply(lambda r: last.get((r["year"], r["slam"]), np.nan), axis=1)
    res["slam"]["last_main_day_reproduced"] = float((mine == u.loc[sl, "slam_last_main_day"]).mean())
    return res


def main() -> None:
    res = {"reads_results": False}
    meta = json.loads(META.read_text(encoding="utf-8"))
    sd_meta = {k: meta["standardisation_sd_km_h"][k] for k in ("B_M0", "B_M1", "A_M0")}
    p = panel_with_release()
    t = R4.frame_sides(True)
    log(f"panel {len(p)} rows; frame sides {len(t)}")
    res["release_rule"] = release_rule_check(p)
    log(json.dumps(res["release_rule"])[:900])
    var = pd.read_parquet(VAR, columns=["match_id", "spd_A_M0", "spd_B_M0", "spd_B_M1"])
    mine_cols = {}
    hist_B = None
    for name, rel, hl, hr in (("B_M0", "release_B", 14.0, True), ("B_M1", "release_B", 28.0, True),
                              ("A_M0", "release_A", 14.0, False)):
        f, idx, tv = side_fhat(p, t, rel, hl, history_release=hr)
        if name == "B_M0":
            hist_B = (idx, tv)
        m = to_match(t, f)
        men = m["tour"].eq("atp")
        sd_mine = float(m.loc[men & m["season"].between(2022, 2023), "d"].std(ddof=1))
        col = np.where(men, np.clip(m["d"] / sd_meta[name], -4, 4), 0.0)
        mine_cols[f"spd_{name}"] = pd.Series(col, index=m["match_id"])
        j = var[["match_id", f"spd_{name}"]].merge(pd.DataFrame({"match_id": m["match_id"], "mine": col,
                                                                  "tour": m["tour"]}), on="match_id",
                                                     validate="one_to_one")
        out = {"sd_meta": sd_meta[name], "sd_mine": sd_mine}
        for lab, mm in (("all", np.ones(len(j), bool)), ("men", j["tour"].eq("atp").to_numpy())):
            x, y = j[f"spd_{name}"].to_numpy(float)[mm], j["mine"].to_numpy(float)[mm]
            dd = np.abs(x - y)
            out[lab] = {"n": int(mm.sum()), "corr": float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 else None,
                        "share_within_0.05": float(np.mean(dd <= 0.05)), "max_abs_diff": float(dd.max())}
        res[f"agreement_{name}"] = out
        log(f"{name}: SD meta {sd_meta[name]:.6f} mine {sd_mine:.6f}; all {out['all']}; men {out['men']}")
    # the same-event share under B (and A) for men's frame sides 2024-26
    idx, tv = hist_B
    tid = p["tournament_id"].to_numpy()
    tt = tv["tournament_id"].to_numpy()
    same_B = ((idx >= 0) & (tid[np.maximum(idx, 0)] == tt[:, None])).any(1)
    hA = AL.histories(p, tv)
    same_A = ((hA["idx"] >= 0) & (tid[np.maximum(hA["idx"], 0)] == tt[:, None])).any(1)
    sel = (tv["tour"].eq("atp") & tv["season"].between(2024, 2026)).to_numpy()
    res["same_event_share_men_2024_26"] = {"sides": int(sel.sum()), "B": float(same_B[sel].mean()),
                                           "A": float(same_A[sel].mean()), "B_count": int(same_B[sel].sum())}
    if same_B[sel].any():
        g = tv[sel & same_B][["tournament_id"]].value_counts().head(12)
        res["same_event_share_men_2024_26"]["B_top_events"] = {str(k[0]): int(v) for k, v in g.items()}
    log(json.dumps(res["same_event_share_men_2024_26"]))
    pd.DataFrame(mine_cols).rename_axis("match_id").reset_index().to_parquet(FEAT_OUT, index=False)
    OUT.write_text(json.dumps(res, indent=1, default=float) + "\n", encoding="utf-8")
    log(f"wrote {OUT.name}")


if __name__ == "__main__":
    main()
