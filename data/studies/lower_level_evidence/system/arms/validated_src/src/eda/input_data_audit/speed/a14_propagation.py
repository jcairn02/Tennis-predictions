"""Audit step 14: how far each flagged block reaches f28 and spd_L (the decided column), recomputed with the project's own
functions (features_latency.Scenario / histories_rel / side_values_v; panel.EditionOffsets), nothing written to the repo.

For each counterfactual panel (the flagged block corrected), spd_L is recomputed for every men's frame match of
2024-2026 under scenario A (instant; the backtest as run) and B (today's sources: weekly ManTennisData, Slams after the
event), and compared with the actual panel's. Reproduction check first: the actual panel must give
adaptive/columns.parquet's spd_L_A and spd_L_B exactly.
Writes scratch/t_propagation_summary.csv and scratch/prop_<scenario>.parquet."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
SCR = Path.cwd() / "data" / "studies" / "input_data_audit" / "speed"   # run from the repo root
pd.set_option("display.width", 260)
pd.set_option("display.max_rows", 300)
pd.set_option("display.max_columns", 40)

from src.eda.serve_speed_tabpfn import features as F  # noqa: E402
from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402
from src.eda.serve_speed_tabpfn.latency import features_latency as FL  # noqa: E402

SD_L = float(json.loads(FL.META.read_text(encoding="utf-8"))["standardisation_sd_km_h"]["B_M1"])
COEF = json.loads((ROOT / "data/studies/serve_speed_tabpfn/adaptive/coefficients.json").read_text())
B_L = {int(k): v["b_shrunk"] for k, v in COEF["L_weekly"].items()}
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:6.1f}s] {m}", flush=True)


p0 = FL.load_panel()
rd = FL.release_days(p0)
keys = P.load_frame_keys()
t = F.side_targets(keys)
sel = t["tour"].eq("atp") & t["season"].between(2024, 2026)
A = t[sel & t["side"].eq("A")]
Bs = t[sel & t["side"].eq("B")]
assert (A["match_id"].to_numpy() == Bs["match_id"].to_numpy()).all()
tm = pd.concat([A, Bs], ignore_index=True)
nm = len(A)
log(f"panel rows {len(p0)}; men's 2024-26 frame matches {nm}")


def spd_cols(pp: pd.DataFrame, rel_b: np.ndarray, box: np.ndarray) -> pd.DataFrame:
    out = {}
    for scen in ("A", "B"):
        if scen == "A":
            S = FL.Scenario("A", pp, None, None)
            hist = FL.histories_rel(pp, tm, None)
        else:
            S = FL.Scenario("B", pp, rel_b, box)
            hist = FL.histories_rel(pp, tm, rel_b)
        sv = FL.side_values_v(S, tm, dict(FL.MEN, hl=28.0), hist=hist)
        f = sv["f_hat"].to_numpy(float)
        out[f"fA_{scen}"], out[f"fB_{scen}"] = f[:nm], f[nm:]
        out[f"spd_L_{scen}"] = np.clip((f[:nm] - f[nm:]) / SD_L, -4, 4)
    return pd.DataFrame(out, index=A["match_id"].to_numpy())


base = spd_cols(p0, rd["B"].to_numpy(np.int64), rd["box"].to_numpy(np.int64))
ref = pd.read_parquet(ROOT / "data/studies/serve_speed_tabpfn/adaptive/columns.parquet",
                      columns=["match_id", "spd_L_A", "spd_L_B"]).set_index("match_id").reindex(base.index)
repro = {s: float(np.max(np.abs(base[f"spd_L_{s}"] - ref[f"spd_L_{s}"]))) for s in ("A", "B")}
log(f"reproduction of adaptive/columns.parquet (max |diff|): {repro}")
base.to_parquet(SCR / "prop_base.parquet")

# ------------------------------------------------------------------ attributes of the panel rows used by the masks
pr = p0.copy()
pr["court"] = pd.Series([None] * len(pr), index=pr.index, dtype=object)
C = {}
he = pd.read_parquet(ROOT / "data/dump/points/slam_ball_tracking/matches.parquet", columns=["slam", "year", "match_id",
                                                                                           "court_name"])
C.update(dict(zip(he["slam"].astype(str) + "_" + he["year"].astype(str) + "_" + he["match_id"].astype(str),
                  he["court_name"].astype(str))))
im = pd.read_parquet(ROOT / "data/dump/points/infosys_slams/matches.parquet", columns=["slam", "year", "match_id",
                                                                                       "court_name"])
C.update(dict(zip(im["slam"].astype(str) + "_" + im["year"].astype(str) + "_" + im["match_id"].astype(str),
                  im["court_name"].astype(str))))
isslam = pr["source"].isin(["slam_tracking", "infosys_slams"])
pr["court"] = np.where(isslam, pr["source_key"].astype(str).map(C).astype(object), None)
men = pr["tour"].eq("atp")


def masks() -> dict:
    m = {}
    ao24 = men & pr["slam"].eq("AO") & pr["year"].eq(2024) & pr["mq"].eq("M")
    m["ao24"] = ao24
    m["rg2324"] = men & pr["slam"].eq("RG") & pr["year"].isin([2023, 2024]) & pr["source"].eq("slam_tracking")
    m["ao25_c1213"] = men & pr["slam"].eq("AO") & pr["year"].eq(2025) & pr["court"].isin(["Court 12", "Court 13"])
    m["w2526"] = men & pr["slam"].eq("W") & pr["year"].isin([2025, 2026])
    return m


M = masks()
log("rows: " + ", ".join(f"{k} {int(v.sum())}" for k, v in M.items()))

# per-court AO 2024 shifts (men, first serves in; player FE across AO 2022-2025, a11): 2024 minus the mean of 2023 and
# 2025 on the same court, shrunk toward the edition-level 3.0 km/h with weight n / (n + 20)
fe = pd.read_csv(SCR / "t_slam_court_year_fe.csv")
fe = fe[(fe["slam"] == "AO") & (fe["tour"] == "atp") & (fe["kind"] == "in1") & (fe["level"] == "court")]
pv = fe.pivot_table(index="court", columns="year", values="gamma")
pn = fe.pivot_table(index="court", columns="year", values="pm")
EDGE = 3.0
shift = {}
for c in pv.index:
    refy = [y for y in (2023, 2025) if y in pv.columns and np.isfinite(pv.loc[c, y])]
    if 2024 in pv.columns and np.isfinite(pv.loc[c, 2024]) and refy:
        raw = pv.loc[c, 2024] - np.mean([pv.loc[c, y] for y in refy])
        n = pn.loc[c, 2024]
        shift[c] = EDGE + (raw - EDGE) * n / (n + 20.0)
log("AO 2024 per-court shifts (men): " + json.dumps({k: round(v, 2) for k, v in shift.items()}))

# RG 2023/2024 first-serve means without stale repeats (raw Hawk-Eye rows, faults kept for the "previous serve")
pts = pd.read_parquet(SCR / "pts_slam_points.parquet")
rgp = pts[(pts["src"] == "slam_tracking") & (pts["slam"] == "RG") & pts["year"].isin([2023, 2024])].copy()
# pts keeps file order within key; flag a speed equal to the previous row's (any serve, same match)
rgp["prev"] = rgp.groupby("key")["spd"].shift()
rgp["stale"] = rgp["spd"].notna() & rgp["spd"].eq(rgp["prev"])
clean = rgp[(rgp["kind"] == "in1") & rgp["spd"].notna() & ~rgp["stale"]]
cm = clean.groupby(["s0_id", "side"])["spd"].agg(["mean", "size"])
allm = rgp[(rgp["kind"] == "in1") & rgp["spd"].notna()].groupby(["s0_id", "side"])["spd"].agg(["mean", "size"])
cmp_ = allm.join(cm, rsuffix="_clean")
cmp_["d"] = cmp_["mean"] - cmp_["mean_clean"]
log(f"RG 2023/24 stale-speed effect on first-serve means (all - clean), km/h: "
    f"{cmp_['d'].describe().round(2).to_dict()}")

# handoff key statistics: broken when avg >= max - 1 or more than 5 km/h from the same match's gated point mean
rec = pd.read_parquet(ROOT / "data/studies/serve_speed_tabpfn/speed_records.parquet")
ptm = rec[(rec["source"] == "infosys") & rec["valid"]][["match_id", "side", "y", "n"]].rename(
    columns={"y": "y_pts", "n": "n_pts_inf"}).drop_duplicates(["match_id", "side"])
hk = pr[pr["source"].eq("handoff_ks")][["match_id", "side", "y", "y_raw", "spd_max"]].merge(ptm, on=["match_id", "side"],
                                                                                            how="left")
hk["bad"] = (hk["y_raw"] >= hk["spd_max"] - 1) | ((hk["y"] + 0.5 - hk["y_pts"]).abs() > 5)
log(f"handoff rows {len(hk)}; broken {int(hk['bad'].sum())}; with a point mean to replace {int((hk['bad'] & hk['y_pts'].notna()).sum())}")

# ManTennisData: both-sides match failures, avg >= max - 1, stats copied from another match (the later copy)
fs = pd.read_csv(SCR / "t_match_failures_slow.csv")["match_id"]
ff = pd.read_csv(SCR / "t_match_failures_fast.csv")["match_id"]
md = pr["source"].eq("mantennisdata")
bad_md = md & (pr["match_id"].isin(set(fs) | set(ff)) | (pr["y_raw"] >= pr["spd_max"] - 1))
k = ["player_id", "y_raw", "n", "spd2_raw", "spd_max"]
dup = pr.duplicated(k, keep="first") & pr["n"].gt(0) & pr["spd_max"].notna()
bad_md |= dup & pr["source"].isin(["mantennisdata", "handoff_ks"])
log(f"ManTennisData rows dropped in S7: {int(bad_md.sum())} (2024-26: {int((bad_md & pr['year'].between(2024, 2026)).sum())})")


def scenario(name: str):
    pp = p0.copy()
    keep = np.ones(len(pp), bool)
    if name in ("S1_ao24_const",):
        pp.loc[M["ao24"], "y"] -= EDGE
    if name in ("S2_ao24_court", "S8_all"):
        sh = pr.loc[M["ao24"], "court"].map(shift).fillna(EDGE)
        pp.loc[M["ao24"], "y"] -= sh.to_numpy()
    if name in ("S3_rg_stale", "S8_all"):
        idx = pr.index[M["rg2324"]]
        new = pd.MultiIndex.from_frame(pr.loc[idx, ["match_id", "side"]]).map(
            lambda k: cmp_["mean_clean"].get(k, np.nan))
        new = np.asarray(new, float)
        ok = np.isfinite(new)
        pp.loc[idx[ok], "y"] = new[ok]
    if name in ("S4_ao25_courts", "S8_all"):
        pp.loc[M["ao25_c1213"], "y"] += 6.0
    if name in ("S5_w_break",):
        pp.loc[M["w2526"], "y"] -= 8.4
    if name in ("S6_handoff", "S8_all"):
        h = pr["source"].eq("handoff_ks")
        hh = pr[h][["match_id", "side"]].merge(hk[["match_id", "side", "bad", "y_pts"]], on=["match_id", "side"],
                                               how="left")
        hb = hh["bad"].fillna(False).to_numpy(bool)
        rep = hb & hh["y_pts"].notna().to_numpy()
        hidx = pr.index[h]
        pp.loc[hidx[rep], "y"] = hh.loc[rep, "y_pts"].to_numpy()
        keep[hidx[hb & ~rep]] = False
    if name in ("S7_mantd", "S8_all"):
        keep &= ~bad_md.to_numpy()
    pp = pp[keep].reset_index(drop=True)
    return pp, rd["B"].to_numpy(np.int64)[keep], rd["box"].to_numpy(np.int64)[keep]


info = keys.set_index("match_id").reindex(A["match_id"].to_numpy())
s0 = pd.read_parquet(ROOT / "data/studies/predictability_diagnostic/stage0_matches.parquet",
                     columns=["match_id", "tournament_name", "level", "round", "tournament_date"])
info = info.join(s0.set_index("match_id"), on="rebuilt_id", rsuffix="_s0")
season = info["season"].to_numpy()
bL = np.array([B_L[int(s)] for s in season])

rows = []
for name in ("S1_ao24_const", "S2_ao24_court", "S3_rg_stale", "S4_ao25_courts", "S5_w_break", "S6_handoff",
             "S7_mantd", "S8_all"):
    pp, relb, box = scenario(name)
    cf = spd_cols(pp, relb, box)
    cf.to_parquet(SCR / f"prop_{name}.parquet")
    for scen in ("A", "B"):
        d = (base[f"spd_L_{scen}"] - cf[f"spd_L_{scen}"]).to_numpy()
        dl = bL * d                                         # log-odds moved by the artefact
        ad = np.abs(d)
        rows.append({"scenario": name, "avail": scen, "matches": nm,
                     "moved_ge_0.05": int((ad >= 0.05).sum()), "moved_ge_0.25": int((ad >= 0.25).sum()),
                     "moved_ge_0.5": int((ad >= 0.5).sum()), "moved_ge_1": int((ad >= 1).sum()),
                     "mean_abs_units": float(ad.mean()), "max_abs_units": float(ad.max()),
                     "max_abs_km_h": float(np.max(np.abs((base[f"fA_{scen}"] - base[f"fB_{scen}"])
                                                          - (cf[f"fA_{scen}"] - cf[f"fB_{scen}"])))),
                     "max_abs_logodds": float(np.max(np.abs(dl))),
                     "max_abs_pp_at_50pc": float(25.0 * np.max(np.abs(dl))),
                     "sum_signed_units": float(d.sum())})
    log(f"{name}: " + "; ".join(f"{r['avail']}: >=0.25u {r['moved_ge_0.25']}, max {r['max_abs_units']:.2f}u"
                                 for r in rows[-2:]))
S = pd.DataFrame(rows)
S.to_csv(SCR / "t_propagation_summary.csv", index=False)
print(S.round(4).to_string(index=False))
info[["tournament_name", "level", "round", "tournament_date", "season", "es", "player_a_id", "player_b_id"]].to_parquet(
    SCR / "prop_info.parquet")
