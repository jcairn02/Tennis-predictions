"""Design R2 (auditor): the basis question (key statistic first at tour level against point mean first) and the
robustness of the centring result to the key statistic's error tail. Result-free: no match result is read.

Looks: statistic targets on seasons <= 2023 only (the target match's own first-serve speeds, T1 = y_A - y_B within a
match); 2022-2026 frame matches: feature values only.

    1  T1 residual tails by season and basis (why men's 2023 MSE is ~3x 2022's)
    2  robust T1: the frozen-vs-as-of comparison with Huber loss (k = 10 km/h) and with matches whose |T - forecast| >
       25 km/h under BOTH schemes removed
    3  common-target basis comparison (men, as-of, the modeller's constants): matches whose two target values are the
       same point means in both panels (2021-2023); forecasts from ks-first and pm-first histories
    4  values: A - B f_hat (as-of) from the two panels on men's frame matches 2022-2026: correlation, SD by season and
       Slam / non-Slam, and the share of sides whose 28-day history is key statistics only / points only / mixed

Run: ./python.sh src/eda/serve_speed_tabpfn/design/auditor_basis.py
Writes data/studies/serve_speed_tabpfn/design/auditor_basis.json
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

from src.eda.serve_speed_tabpfn.design import auditor_centring as AC  # noqa: E402
from src.eda.serve_speed_tabpfn.design import auditor_lib as AL  # noqa: E402

OUT = AL.OUT / "auditor_basis.json"
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def t1_setup(p: pd.DataFrame, snaps: dict, years=(2019, 2023)):
    pt = p[p["tour"] == "atp"]
    tg = pt[pt["year"].between(*years)].reset_index(drop=True)
    h = AL.histories(p, tg)
    tday = tg["es"].to_numpy(float)
    frozen = AL.frozen_offsets(pt, 2022)
    D = AL.days_matrix(p, h)
    R = AL.noise(p, h, AL.MEN)
    iA, iB = AC.t1_pairs(tg)
    y = tg["y"].to_numpy(float)
    out = {"tg": tg, "iA": iA, "iB": iB, "T": y[iA] - y[iB], "year": tg["year"].to_numpy()[iA],
           "blk": (tday[iA] // 28).astype(int), "basisA": tg["basis"].to_numpy()[iA],
           "basisB": tg["basis"].to_numpy()[iB], "slam": tg["level"].eq("GS").to_numpy()[iA], "fc": {}}
    for name in ("frozen", "asof"):
        Z = AL.centred_values(p, tg, h, name, frozen=frozen, snaps=snaps)
        kf = AL.kalman_batch(Z, R, D, tday, dict(AL.MEN))
        out["fc"][name] = (kf["L_hat"][iA] + kf["f_hat"][iA]) - (kf["L_hat"][iB] + kf["f_hat"][iB])
        out["fc"][name + "_f"] = (kf["f_hat"][iA], kf["f_hat"][iB])
    return out


def huber(r: np.ndarray, k: float = 10.0) -> np.ndarray:
    a = np.abs(r)
    return np.where(a <= k, 0.5 * r * r, k * (a - 0.5 * k))


def main() -> None:
    res = {"reads_results": False}
    pk = AL.panel("ks_first")
    pp = AL.panel("pm_first")
    log(f"panels: ks_first {len(pk)}, pm_first {len(pp)}")
    sk = {"atp": AL.Snapshots(pk[pk["tour"] == "atp"].reset_index(drop=True))}
    spm = {"atp": AL.Snapshots(pp[pp["tour"] == "atp"].reset_index(drop=True))}
    a = t1_setup(pk, sk)
    T, has = a["T"], np.isfinite(a["fc"]["frozen"]) & np.isfinite(a["fc"]["asof"])
    # 1 tails
    tails = []
    for yr in range(2019, 2024):
        for lab, m in (("both_ks", (a["basisA"] == "ks") & (a["basisB"] == "ks")),
                       ("both_pts", (a["basisA"] == "pts") & (a["basisB"] == "pts")),
                       ("mixed", a["basisA"] != a["basisB"])):
            mm = has & (a["year"] == yr) & m
            if mm.sum() < 20:
                continue
            r = T[mm] - a["fc"]["asof"][mm]
            tails.append({"year": yr, "bases": lab, "matches": int(mm.sum()), "mse": float(np.mean(r ** 2)),
                          "share_abs_resid_gt_25": float(np.mean(np.abs(r) > 25)),
                          "mse_without_gt_25": float(np.mean(r[np.abs(r) <= 25] ** 2))})
    res["t1_tails_ks_first_asof"] = tails
    log(pd.DataFrame(tails).to_string(index=False))
    # 2 robust comparison on 2023
    ev = has & (a["year"] == 2023)
    rf, ra = T - a["fc"]["frozen"], T - a["fc"]["asof"]
    keep = ev & ~((np.abs(rf) > 25) & (np.abs(ra) > 25))
    res["t1_robust_2023"] = {
        "huber10_frozen_minus_asof": AC.block_boot({"d": (huber(rf) - huber(ra))[ev]}, a["blk"][ev])["d"],
        "mse_trimmed_frozen_minus_asof": AC.block_boot({"d": (rf ** 2 - ra ** 2)[keep]}, a["blk"][keep])["d"],
        "matches": int(ev.sum()), "matches_trimmed": int(keep.sum()),
        "key": "positive = as-of better (lower loss); km/h^2; 95% four-week-block bootstrap"}
    log(json.dumps(AC.jsonable(res["t1_robust_2023"])))
    # 3 common target: matches whose two values are the same point means in both panels, 2021-2023
    b = t1_setup(pp, spm)
    ka = pd.DataFrame({"match_id": a["tg"]["match_id"].to_numpy()[a["iA"]], "T_ks": T, "fc_ks": a["fc"]["asof"],
                       "bA": a["basisA"], "bB": a["basisB"], "year": a["year"], "blk": a["blk"],
                       "fA_ks": a["fc"]["asof_f"][0], "fB_ks": a["fc"]["asof_f"][1]})
    kb = pd.DataFrame({"match_id": b["tg"]["match_id"].to_numpy()[b["iA"]], "T_pm": b["T"], "fc_pm": b["fc"]["asof"],
                       "bA_pm": b["basisA"], "bB_pm": b["basisB"],
                       "fA_pm": b["fc"]["asof_f"][0], "fB_pm": b["fc"]["asof_f"][1]})
    j = ka.merge(kb, on="match_id")
    same = (j["bA"].eq("pts") & j["bB"].eq("pts") & j["bA_pm"].eq("pts") & j["bB_pm"].eq("pts")
            & np.isclose(j["T_ks"], j["T_pm"]) & j["year"].between(2021, 2023) & j["fc_ks"].notna()
            & j["fc_pm"].notna())
    g = j[same]
    d = (g["T_ks"] - g["fc_ks"]) ** 2 - (g["T_pm"] - g["fc_pm"]) ** 2
    dff = (g["fA_ks"] - g["fB_ks"]).to_numpy()
    dfp = (g["fA_pm"] - g["fB_pm"]).to_numpy()
    res["common_target_point_means_2021_23"] = {
        "matches": int(len(g)),
        "mse_ks_history": float(np.mean((g["T_ks"] - g["fc_ks"]) ** 2)),
        "mse_pm_history": float(np.mean((g["T_pm"] - g["fc_pm"]) ** 2)),
        "ks_minus_pm": AC.block_boot({"d": d.to_numpy()}, g["blk"].to_numpy())["d"],
        "corr_df_ks_vs_pm": float(np.corrcoef(dff, dfp)[0, 1]),
        "key": "positive ks_minus_pm = the point-mean history forecasts the point-mean target better"}
    log(json.dumps(AC.jsonable(res["common_target_point_means_2021_23"])))
    # 4 values on the frame, men 2022-2026
    tg = AC.frame_targets()
    tg = tg[(tg["season"] >= 2022) & (tg["tour"] == "atp")].reset_index(drop=True)
    vals = {}
    mix = {}
    for name, p, s in (("ks", pk, sk), ("pm", pp, spm)):
        h = AL.histories(p, tg)
        Z = AL.centred_values(p, tg, h, "asof", snaps=s)
        kf = AL.kalman_batch(Z, AL.noise(p, h, AL.MEN), AL.days_matrix(p, h), tg["es"].to_numpy(float), dict(AL.MEN))
        vals[name] = kf["f_hat"]
        idx = h["idx"]
        okk = idx >= 0
        day = np.where(okk, p["obs"].to_numpy(float)[np.maximum(idx, 0)], np.nan)
        rec = okk & (day >= tg["es"].to_numpy(float)[:, None] - 28)
        isks = np.where(okk, p["basis"].to_numpy()[np.maximum(idx, 0)] == "ks", False)
        nks, npt = (rec & isks).sum(1), (rec & ~isks).sum(1)
        mix[name] = np.select([(nks > 0) & (npt == 0), (npt > 0) & (nks == 0), (nks > 0) & (npt > 0)],
                              ["ks_only", "pts_only", "mixed"], "none")
    t = tg.assign(f_ks=vals["ks"], f_pm=vals["pm"], mix_ks=mix["ks"], mix_pm=mix["pm"])
    A, B = t[t["side"] == "A"].set_index("match_id"), t[t["side"] == "B"].set_index("match_id")
    m = A[["season", "level"]].assign(ks=A["f_ks"] - B["f_ks"], pm=A["f_pm"] - B["f_pm"])
    rows = []
    for (season, slam), g2 in m.groupby([m["season"], m["level"].eq("GS")]):
        rows.append({"season": int(season), "slam": bool(slam), "matches": int(len(g2)),
                     "sd_ks_first": float(g2["ks"].std()), "sd_pm_first": float(g2["pm"].std()),
                     "corr": float(g2[["ks", "pm"]].corr().iloc[0, 1]),
                     "share_diff_gt_1sd": float(((g2["ks"] - g2["pm"]).abs() > 2.22).mean())})
    res["values_ks_vs_pm_first"] = rows
    mixtab = []
    for name in ("ks", "pm"):
        c = t[t["level"].ne("GS")].groupby(["season", f"mix_{name}"]).size().unstack(fill_value=0)
        c = (c.T / c.sum(1)).T.round(3)
        mixtab.append({"panel": name, "non_slam_sides_28d_history_mix": {int(k): v for k, v in
                                                                          c.to_dict(orient="index").items()}})
    res["history_basis_mix"] = mixtab
    log(pd.DataFrame(rows).to_string(index=False))
    log(json.dumps(mixtab))
    OUT.write_text(json.dumps(AC.jsonable(res), indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
