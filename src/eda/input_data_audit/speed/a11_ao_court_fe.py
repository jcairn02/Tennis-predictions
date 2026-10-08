"""Audit step 11: AO 2022-2025 court x year effects with player fixed effects (weighted), for first serves in and for
first-serve faults separately, men and women; RG 2022-2026 as the control. Read-only on the repo."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path.cwd()
SCR = Path.cwd() / "data" / "studies" / "input_data_audit" / "speed"   # run from the repo root
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 600)
pd.set_option("display.max_columns", 40)
pm = pd.read_parquet(SCR / "pm_slam_points.parquet")


def norm_court(c: str) -> str:
    c = str(c or "").strip()
    c = c.replace("Show Court", "Court").replace("Ct ", "Court ")
    return c


def fe(d: pd.DataFrame, ycol: str, ncol: str, cell: str, iters: int = 200) -> pd.DataFrame:
    d = d[np.isfinite(d[ycol]) & (d[ncol] >= 5)].copy()
    w = 1.0 / (22.0 + 12.4 ** 2 / d[ncol].to_numpy(float))
    y = d[ycol].to_numpy(float)
    pi, pu = pd.factorize(d["player_id"])
    ci, cu = pd.factorize(d[cell])
    g = np.zeros(len(cu))
    for _ in range(iters):
        a = np.bincount(pi, w * (y - g[ci])) / np.bincount(pi, w)
        g_new = np.bincount(ci, w * (y - a[pi])) / np.bincount(ci, w)
        if np.max(np.abs(g_new - g)) < 1e-8:
            g = g_new
            break
        g = g_new
    r = y - a[pi] - g[ci]
    out = pd.DataFrame({"cell": cu, "gamma": g, "pm": np.bincount(ci), "w": np.bincount(ci, w)})
    # rough SE: residual SD / sqrt(sum of w*s2) ~ use unweighted residual variance per cell
    s2 = np.average(r ** 2, weights=w)
    out["se"] = np.sqrt(s2 / np.bincount(ci, w) / (np.average(w)))
    return out


rows = []
for slam, years in (("AO", (2022, 2023, 2024, 2025)), ("RG", (2022, 2023, 2024, 2025, 2026))):
    for tour in ("atp", "wta"):
        d = pm[(pm["slam"] == slam) & (pm["tour"] == tour) & (pm["mq"] == "M") & pm["year"].isin(years)
               & pm["player_id"].notna()].copy()
        d["court"] = d["court"].map(norm_court)
        d["cell"] = d["year"].astype(str) + "|" + d["court"]
        d["yr"] = d["year"].astype(str)
        for kind in ("in1", "fault1", "in2"):
            # year effects first (player FE), then court x year cells
            fy = fe(d, f"mean_{kind}", f"size_{kind}", "yr")
            fy = fy.assign(slam=slam, tour=tour, kind=kind, level="year")
            fc = fe(d, f"mean_{kind}", f"size_{kind}", "cell")
            fc = fc.assign(slam=slam, tour=tour, kind=kind, level="court")
            # express each court-year cell relative to its own year (pm-weighted mean of the year's cells)
            fc["year"] = fc["cell"].str.split("|").str[0]
            fc["court"] = fc["cell"].str.split("|").str[1]
            rows += [fy, fc]
res = pd.concat(rows, ignore_index=True)
yr = res[res["level"] == "year"].copy()
for (slam, tour, kind), g in yr.groupby(["slam", "tour", "kind"]):
    ref = g["gamma"].mean()
    yr.loc[g.index, "rel_to_mean_of_years"] = g["gamma"] - ref
print("=== year effects (player FE), relative to the mean of the years; km/h")
print(yr.pivot_table(index=["slam", "tour", "kind"], columns="cell", values="rel_to_mean_of_years").round(2).to_string())

ct = res[(res["level"] == "court")].copy()
# reference: the court's value relative to the mean over years 2022/2023 (AO) of the same court
piv = ct.pivot_table(index=["slam", "tour", "kind", "court"], columns="year", values="gamma")
cnt = ct.pivot_table(index=["slam", "tour", "kind", "court"], columns="year", values="pm")
print("=== court x year effects (player FE), km/h (raw cell effects; compare across a row)")
for (slam, kind), g in piv.groupby(level=["slam", "kind"]):
    if kind == "in2":
        continue
    c = cnt.loc[g.index]
    show = g.copy()
    show.columns = [f"g{x}" for x in show.columns]
    c.columns = [f"n{x}" for x in c.columns]
    print(pd.concat([show.round(1), c], axis=1).to_string())
res.to_csv(SCR / "t_slam_court_year_fe.csv", index=False)
