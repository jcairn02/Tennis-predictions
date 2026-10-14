"""Summaries of role B's relationship outputs for the report (reads system/relationship/ only; no fit).

Writes, in data/studies/lower_level_evidence/system/relationship/:
    level_summary.csv     per (season_used, tour, level): the median across statistics of w (and its bootstrap interval:
                          the median across statistics in each draw), the range across statistics, the level mean of the
                          shrinkage, the median w per match, and delta of the main statistics
    era_stability.csv     per (tour, stat, level): w and delta of season_used 2019 (fit window 2013-2018) against 2024
                          (2018-2023), the difference and its z from the bootstrap SDs (independent draws; the windows
                          share 2018); the window ending 2024 is the 2025 row's, which stays unread before the holdout
    headline_men.csv      men's w and delta for TQ, GSQ, CH, CHQ, season_used 2024, for the points and games
                          statistics, with intervals
    checks_params.json    coverage of the point estimates by their intervals, convergence, counts

Run: ./python.sh src/eda/lower_level_evidence/relationship_report.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import common as C  # noqa: E402

OUT = C.OUT / "system" / "relationship"
LOWER4 = ("TQ", "GSQ", "CH", "CHQ")
MAIN_STATS = ("spw", "rpw", "tpw", "hold", "brk", "first_won", "second_won", "ace", "bp_saved", "bp_conv")


def level_summary(par: pd.DataFrame, draws: pd.DataFrame) -> pd.DataFrame:
    p = par[(par["stat"] != "results") & par["level"].isin(LOWER4) & par["fitted"].astype(bool)]
    rows = []
    med_draw = draws.groupby(["tour", "season", "level", "b"])["w"].median().reset_index()
    for (Y, tour, L), g in p.groupby(["season_used", "tour", "level"]):
        md = med_draw[(med_draw["season"] == Y) & (med_draw["tour"] == tour) & (med_draw["level"] == L)]["w"]
        rec = {"season_used": Y, "tour": tour, "level": L, "stats": int(len(g)),
               "w_median": float(g["w"].median()), "w_min": float(g["w"].min()), "w_max": float(g["w"].max()),
               "w_median_lo": float(md.quantile(0.025)) if len(md) else np.nan,
               "w_median_hi": float(md.quantile(0.975)) if len(md) else np.nan,
               "w_level_mean": float(g["w_level_mean"].median()), "w_tau": float(np.sqrt(g["w_tau2"].median())),
               "w_per_match_median": float(g["w_per_match"].median()), "n_players": int(g["n_players"].max()),
               "h_weeks_median": float(g["h_weeks"].median())}
        for s in ("spw", "rpw", "tpw", "hold", "brk"):
            r = g[g["stat"] == s]
            if len(r):
                rec[f"w_{s}"] = float(r["w"].iloc[0])
                rec[f"delta_{s}"] = float(r["delta"].iloc[0])
        rows.append(rec)
    return pd.DataFrame(rows)


def era(par: pd.DataFrame, draws: pd.DataFrame, a: int = 2019, b: int = 2024) -> pd.DataFrame:
    p = par[(par["stat"] != "results") & par["level"].isin(LOWER4)]
    sd = draws.groupby(["stat", "tour", "season", "level"]).agg(w_sd=("w", "std"), delta_sd=("delta", "std"))
    rows = []
    for (tour, stat, L), g in p.groupby(["tour", "stat", "level"]):
        ra, rb = g[g["season_used"] == a], g[g["season_used"] == b]
        if not len(ra) or not len(rb) or not (bool(ra["fitted"].iloc[0]) and bool(rb["fitted"].iloc[0])):
            continue
        rec = {"tour": tour, "stat": stat, "level": L}
        for v in ("w", "delta"):
            x, y = float(ra[v].iloc[0]), float(rb[v].iloc[0])
            sa = sd.loc[(stat, tour, a, L), f"{v}_sd"] if (stat, tour, a, L) in sd.index else np.nan
            sb = sd.loc[(stat, tour, b, L), f"{v}_sd"] if (stat, tour, b, L) in sd.index else np.nan
            se = float(np.sqrt(sa ** 2 + sb ** 2)) if np.isfinite(sa) and np.isfinite(sb) else np.nan
            rec.update({f"{v}_{a}": x, f"{v}_{b}": y, f"{v}_diff": y - x, f"{v}_diff_se": se,
                        f"{v}_z": (y - x) / se if se and np.isfinite(se) and se > 0 else np.nan})
        rec["delta_allowed"] = bool(rb["delta_allowed"].iloc[0])
        rows.append(rec)
    return pd.DataFrame(rows)


def headline(par: pd.DataFrame, Y: int = 2024) -> pd.DataFrame:
    p = par[(par["season_used"] == Y) & (par["tour"] == "atp") & par["level"].isin(LOWER4) & par["stat"].isin(MAIN_STATS)]
    return p[["stat", "level", "w", "w_lo", "w_hi", "delta", "delta_lo", "delta_hi", "delta_allowed", "w_per_match",
              "w_free", "w_level_mean", "n_players", "h_weeks"]].sort_values(["level", "stat"])


def sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def noclass_view() -> dict | None:
    """params_noclass.parquet: the frozen table with the no-class fit (SYS_NOCLASS) in the standard columns, so a
    layer config can point `params` at it unchanged. A view of params.parquet, not a new fit: gamma, delta, w <-
    gamma_noclass, delta_noclass, w_noclass; every box-score statistic translated by the gap; no bootstrap (the
    interval columns are NaN). Results rows unchanged."""
    src = OUT / "params.parquet"
    if not src.exists():
        return None
    t = pd.read_parquet(src)
    box = t["stat"] != "results"
    v = t.copy()
    v.loc[box, "gamma"] = t.loc[box, "gamma_noclass"]
    v.loc[box, "delta"] = t.loc[box, "delta_noclass"]
    v.loc[box, "w"] = t.loc[box, "w_noclass"]
    v.loc[box, ["w_lo", "w_hi", "delta_lo", "delta_hi"]] = np.nan
    v.loc[box, "translate_mode"] = "gap"
    v.loc[box, "delta_allowed"] = True
    v["method_version"] = v["method_version"].astype(str) + "|noclass-view"
    v["view_of"] = f"params.parquet {sha256_file(src)}"
    dst = OUT / "params_noclass.parquet"
    v.to_parquet(dst, index=False)
    (OUT / "params_noclass.sha256").write_text(f"{sha256_file(dst)}  params_noclass.parquet\n", encoding="utf-8")
    return {"rows": int(len(v)), "sha256": sha256_file(dst), "view_of": sha256_file(src)}


def main() -> int:
    nc = noclass_view()
    if nc:
        print("params_noclass:", nc)
    par = pd.read_parquet(OUT / "params_dev.parquet")
    draws = pd.read_parquet(OUT / "bootstrap_draws.parquet")
    ls = level_summary(par, draws)
    ls.to_csv(OUT / "level_summary.csv", index=False)
    er = era(par, draws)
    er.to_csv(OUT / "era_stability.csv", index=False)
    headline(par).to_csv(OUT / "headline_men.csv", index=False)
    box = par[(par["stat"] != "results") & par["level"].isin(LOWER4) & par["fitted"].astype(bool)]
    inside = ((box["w"] >= box["w_lo"] - 1e-9) & (box["w"] <= box["w_hi"] + 1e-9))
    inside_d = ((box["delta"] >= box["delta_lo"] - 1e-9) & (box["delta"] <= box["delta_hi"] + 1e-9))
    chk = {"rows": int(len(par)), "fitted_lower_rows": int(len(box)),
           "w_point_inside_interval_share": float(inside.mean()),
           "delta_point_inside_interval_share": float(inside_d.mean()),
           "not_converged": int((~par["converged"].fillna(True).astype(bool)).sum()),
           "boot_draws_min": int(box["boot_draws"].min()), "code_sha256": sorted(set(par["code_sha256"].dropna()))}
    (OUT / "checks_params.json").write_text(json.dumps(chk, indent=1), encoding="utf-8")
    print(json.dumps(chk, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
