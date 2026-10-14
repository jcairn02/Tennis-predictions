"""Odds sources, step 3: drift, season by season.

The owner's concern of 9 Oct 2026: "as the years go by, certain books go bankrupt or change their policy, so the ratio
of whats sharp will change too ... Betonline for example got way sharper as the years went by while pinnacle was sharp
for a long time."

    margin        each source's median overround minus 1
    accuracy      log loss on the matches every compared source prices, against Pinnacle's close (tennis-data):
                  2013-2025 the average, Bet365, Pinnacle; 2018-2025 also BetOnline, Pinnacle at OddsTrader and the
                  median of OddsTrader's books
    calibration   the slope of the result on each source's log-odds, by season (1 = calibrated)
    drift cost    log loss with the slope fitted on the earlier seasons (walk-forward, as a model trained on them would
                  read the source) minus with the slope fitted on the season itself: the part of a season's error that
                  comes from the source's relation to the result having moved
    distance      median log-odds gap to Pinnacle's close: how far the average's (or another source's) view moves
    composition   OddsTrader: how many books price a match, and each book's coverage and margin, by season

OddsTrader's lines stamped over 30 minutes after the listed start are dropped throughout (quality.drop_late: some of
them are in-play prices).

Reads sources.parquet; writes drift.json and drift_tables.md.
Run: ./python.sh src/eda/odds_sources/drift.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.odds_sources import common as C  # noqa: E402
from src.eda.odds_sources import quality as Q  # noqa: E402

MIN_SEASON_ROWS = 300
CLONES = {"ot131"}                 # SportsBetting.ag repeats BetOnline's lines; left out of OddsTrader's median
OT_MEDIAN_MIN = 3


def with_ot_median(df: pd.DataFrame) -> pd.DataFrame:
    books = [s for s in Q.closing_ot(df) if s not in CLONES]
    df = df.copy()
    df["p_otmed"] = C.median_logit(df[[f"p_{s}" for s in books]].to_numpy(float), OT_MEDIAN_MIN)
    df["n_ot"] = np.isfinite(df[[f"p_{s}" for s in books]].to_numpy(float)).sum(axis=1)
    return df


def margins(df: pd.DataFrame, sources: list[str]) -> dict:
    out = {}
    for s in sources:
        if f"over_{s}" not in df:
            continue
        g = df.groupby("season")[f"over_{s}"].median().dropna()
        out[s] = {str(k): round(100 * (v - 1), 2) for k, v in g.items()}
    return out


def accuracy(df: pd.DataFrame, sources: list[str], seasons, base: str = "ps") -> dict:
    """Log loss of each source minus Pinnacle's (tennis-data), mLL, on the matches all of them price."""
    m = df["season"].isin(seasons).to_numpy().copy()
    for s in sources:
        m &= np.isfinite(df[f"p_{s}"].to_numpy(float))
    x = df[m]
    y, blk = x["a_won"].to_numpy(float), x["block"].to_numpy()
    ll = {s: C.log_loss(x[f"p_{s}"], y) for s in sources}
    out = {"n": int(m.sum()), "log_loss": {s: round(float(v.mean()), 5) for s, v in ll.items()},
           "minus_base": {s: C.mean_ci(ll[s] - ll[base], blk) for s in sources if s != base}, "by_season": {}}
    for season in sorted(x["season"].unique()):
        k = (x["season"] == season).to_numpy()
        if k.sum() < MIN_SEASON_ROWS:
            continue
        out["by_season"][str(season)] = {"n": int(k.sum()),
                                         **{s: C.mean_ci(ll[s][k] - ll[base][k], blk[k]) for s in sources if s != base}}
    return out


def calibration(df: pd.DataFrame, sources: list[str]) -> dict:
    """Per season: the in-season slope, and the drift cost (walk-forward slope's log loss minus the in-season's)."""
    out = {}
    for s in sources:
        p = df[f"p_{s}"].to_numpy(float)
        ok = np.isfinite(p)
        z, y, blk, season = C.lg(p), df["a_won"].to_numpy(float), df["block"].to_numpy(), df["season"].to_numpy()
        rows = {}
        for yr in sorted(np.unique(season[ok])):
            cur = ok & (season == yr)
            if cur.sum() < MIN_SEASON_ROWS:
                continue
            fit = C.slope_ci(z[cur], y[cur], blk[cur])
            row = {"n": int(cur.sum()), "slope": fit}
            past = ok & (season < yr)
            if past.sum() >= MIN_SEASON_ROWS:
                b_past = float(C.fit_logistic(z[past][:, None], y[past])[0][0])
                cost = C.log_loss(C.ex(b_past * z[cur]), y[cur]) - C.log_loss(C.ex(fit["est"] * z[cur]), y[cur])
                row["slope_before"] = round(b_past, 4)
                row["drift_cost"] = C.mean_ci(cost, blk[cur])
            rows[str(yr)] = row
        out[s] = rows
    return out


def distance(df: pd.DataFrame, sources: list[str], base: str = "ps") -> dict:
    zb = C.lg(df[f"p_{base}"].to_numpy(float))
    out = {}
    for s in sources:
        if s == base:
            continue
        gap = np.abs(C.lg(df[f"p_{s}"].to_numpy(float)) - zb)
        g = pd.Series(gap).groupby(df["season"].to_numpy()).median().dropna()
        out[s] = {str(k): round(float(v), 4) for k, v in g.items()}
    return out


def composition(df: pd.DataFrame) -> dict:
    books = Q.closing_ot(df)
    priced = df[df["n_ot"] > 0]
    out = {"books_per_match": {str(k): {"median": float(v.median()), "p10": float(v.quantile(0.1)),
                                        "p90": float(v.quantile(0.9))}
                               for k, v in priced.groupby("season")["n_ot"]},
           "coverage": {}, "margin_pct": {}}
    for s in books:
        cov = df.groupby("season")[f"p_{s}"].apply(lambda v: v.notna().mean())
        out["coverage"][s] = {str(k): round(float(v), 3) for k, v in cov.items() if k >= 2018}
        mg = df.groupby("season")[f"over_{s}"].median()
        out["margin_pct"][s] = {str(k): round(100 * (float(v) - 1), 2) for k, v in mg.items() if pd.notna(v)}
    return out


def openings(df: pd.DataFrame) -> dict:
    """Pinnacle's opening line at OddsTrader against its last line there and tennis-data's close, on the same matches:
    how much softer the opening is (mLL, + = the opening worse), and how early it came."""
    po, pc, ps = (df[f"p_{s}"].to_numpy(float) for s in ("ot20o", "ot20", "ps"))
    hours = -df["after_ot20o_min"].to_numpy(float) / 60.0
    m = np.isfinite(po) & np.isfinite(pc) & np.isfinite(ps) & (hours > 0)
    y, blk, season = df["a_won"].to_numpy(float), df["block"].to_numpy(), df["season"].to_numpy()
    lo, lc, lp = C.log_loss(po, y), C.log_loss(pc, y), C.log_loss(ps, y)
    out = {"n": int(m.sum()), "hours_before_listed_start": {q: round(float(np.quantile(hours[m], v)), 1) for q, v in
                                                            (("p10", 0.1), ("median", 0.5), ("p90", 0.9))},
           "open_minus_last": C.mean_ci(lo[m] - lc[m], blk[m]), "open_minus_tennis_data": C.mean_ci(lo[m] - lp[m], blk[m]),
           "by_season": {}}
    for yr in sorted(np.unique(season[m])):
        k = m & (season == yr)
        if k.sum() >= MIN_SEASON_ROWS:
            out["by_season"][str(yr)] = {"n": int(k.sum()), "open_minus_last": C.mean_ci(lo[k] - lc[k], blk[k]),
                                         "median_hours": round(float(np.median(hours[k])), 1)}
    return out


def fmt(ci, digits=2) -> str:
    return Q.fmt(ci, digits)


def tables(res: dict) -> str:
    L = ["# Odds sources: drift by season (generated by drift.py)", ""]
    srcs = res["sources"]
    L += ["## Margin (median overround − 1, %)", "", "| Season | " + " | ".join(Q.name(s) for s in srcs if s in
                                                                                  res["margin"]) + " |",
          "|---|" + "---:|" * sum(s in res["margin"] for s in srcs)]
    seasons = sorted({k for v in res["margin"].values() for k in v})
    for yr in seasons:
        L.append(f"| {yr} | " + " | ".join(str(res["margin"][s].get(yr, "—")) for s in srcs if s in res["margin"]) + " |")
    for key, title in (("acc_long", "Accuracy against Pinnacle's close (tennis-data), 2013–2025"),
                       ("acc_ot", "Accuracy against Pinnacle's close (tennis-data), 2018–2025, with OddsTrader")):
        a = res[key]
        others = list(a["minus_base"])
        L += ["", f"## {title}", "", f"mLL, + = the source is worse than Pinnacle; {a['n']:,} matches all priced.", "",
              "| Season | " + " | ".join(Q.name(s) for s in others) + " |", "|---|" + "---|" * len(others)]
        for yr, row in a["by_season"].items():
            L.append(f"| {yr} ({row['n']:,}) | " + " | ".join(fmt(row[s]) for s in others) + " |")
        L.append("| **all** | " + " | ".join(f"**{fmt(a['minus_base'][s])}**" for s in others) + " |")
    L += ["", "## Calibration slope by season (1 = calibrated; above 1 = too timid)", "",
          "| Season | " + " | ".join(Q.name(s) for s in srcs) + " |", "|---|" + "---|" * len(srcs)]
    seasons = sorted({k for v in res["calibration"].values() for k in v})
    for yr in seasons:
        cells = []
        for s in srcs:
            r = res["calibration"].get(s, {}).get(yr)
            cells.append("—" if not r else f"{r['slope']['est']:.3f}")
        L.append(f"| {yr} | " + " | ".join(cells) + " |")
    L += ["", "## Drift cost (mLL: walk-forward slope minus the season's own; + = lost to drift)", "",
          "| Season | " + " | ".join(Q.name(s) for s in srcs) + " |", "|---|" + "---|" * len(srcs)]
    for yr in seasons:
        cells = []
        for s in srcs:
            r = res["calibration"].get(s, {}).get(yr)
            cells.append("—" if not r or "drift_cost" not in r else fmt(r["drift_cost"]))
        L.append(f"| {yr} | " + " | ".join(cells) + " |")
    L += ["", "## Median log-odds gap to Pinnacle's close (tennis-data)", "",
          "| Season | " + " | ".join(Q.name(s) for s in res["distance"]) + " |", "|---|" + "---:|" * len(res["distance"])]
    seasons = sorted({k for v in res["distance"].values() for k in v})
    for yr in seasons:
        L.append(f"| {yr} | " + " | ".join(str(res["distance"][s].get(yr, "—")) for s in res["distance"]) + " |")
    po = res.get("pinnacle_opening")
    if po:
        h = po["hours_before_listed_start"]
        L += ["", "## Pinnacle's opening line (OddsTrader) against its close", "",
              f"{po['n']:,} matches; the opening came a median {h['median']} h before the listed start (10th–90th "
              f"percentile {h['p10']}–{h['p90']} h). mLL, + = the opening worse: against Pinnacle's last line at "
              f"OddsTrader {fmt(po['open_minus_last'])}; against tennis-data's close {fmt(po['open_minus_tennis_data'])}.",
              "", "| Season | Matches | Median hours before | Opening − last line |", "|---|---:|---:|---|"]
        for yr, v in po["by_season"].items():
            L.append(f"| {yr} | {v['n']:,} | {v['median_hours']} | {fmt(v['open_minus_last'])} |")
    comp = res["composition"]
    L += ["", "## OddsTrader: books per match, and each book's coverage of the frame's matches", "",
          "| Season | Books per match, median (10th–90th percentile) |", "|---|---|"]
    for yr, v in comp["books_per_match"].items():
        L.append(f"| {yr} | {v['median']:.0f} ({v['p10']:.0f}–{v['p90']:.0f}) |")
    yrs = sorted({k for v in comp["coverage"].values() for k in v})
    L += ["", "| Book | " + " | ".join(yrs) + " | Median margin, latest season |", "|---|" + "---:|" * (len(yrs) + 1)]
    for s, cov in comp["coverage"].items():
        mg = comp["margin_pct"].get(s, {})
        last = mg[max(mg)] if mg else "—"
        L.append(f"| {Q.name(s)} | " + " | ".join(f"{cov.get(y, 0):.0%}" for y in yrs) + f" | {last} |")
    return "\n".join(L) + "\n"


def main() -> int:
    df = with_ot_median(Q.drop_late(pd.read_parquet(C.SOURCES)))
    df = df[df["a_won"].notna()].reset_index(drop=True)
    sources = [s for s in ["avg", "ps", "b365", "ex", "lb", "bfe", "ot8", "ot20", "otmed", "pm_m30"] if f"p_{s}" in df]
    res = {"sources": sources,
           "margin": margins(df, [s for s in sources if s not in ("otmed", "pm_m30")] + ["max"]),
           "acc_long": accuracy(df, ["avg", "ps", "b365"], range(2013, 2026)),
           "acc_ot": accuracy(df, ["avg", "ps", "b365", "ot8", "ot20", "otmed"], range(2018, 2026)),
           "calibration": calibration(df, sources),
           "distance": distance(df, [s for s in sources if s != "pm_m30"]),
           "composition": composition(df),
           "pinnacle_opening": openings(df) if "p_ot20o" in df else None}
    C.write_json(C.OUT / "drift.json", res)
    (C.OUT / "drift_tables.md").write_text(tables(res), encoding="utf-8")
    C.log("drift.json, drift_tables.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
