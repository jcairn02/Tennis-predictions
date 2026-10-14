"""Checks of the edge-anatomy study added after the first results (process log, 12 Oct 2026).

1. The input's source. In 2025-26 the model's odds input comes from four sources (Pinnacle's close from tennis-data;
   Pinnacle's last line as OddsTrader recorded it, Aug - 7 Sep 2025; BetOnline's last line; the books' average). The
   672 matches fed OddsTrader's Pinnacle line showed a gain of +4.8 mLL. If a source is softer than a true close, the
   model's "edge" there is partly beating a soft price. On each source's matches: the log loss of the input price,
   BetOnline's last line, Pinnacle's price where it exists and the books' average (each margin-free, raw), and the
   model; each price against the input (mLL, + = the named price sharper than the input).
Writes data/studies/edge_anatomy/check_sources.csv.
Run: ./python.sh src/eda/edge_anatomy/checks.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.edge_anatomy import common as E  # noqa: E402
from src.eda.edge_anatomy import stats as S  # noqa: E402


def demargin(da: np.ndarray, db: np.ndarray) -> np.ndarray:
    ia, ib = 1 / da, 1 / db
    return ia / (ia + ib)


def sources() -> pd.DataFrame:
    df = pd.read_parquet(E.OUT / "analysis.parquet")
    df = df[df["season"].isin((2025, 2026)) & ~df["debut"]].copy()
    df["p_bol"] = demargin(df["bol_a"].to_numpy(float), df["bol_b"].to_numpy(float))
    df["p_pin"] = demargin(df["pin_a"].to_numpy(float), df["pin_b"].to_numpy(float))
    rows = []
    for (src, tour), g in df.groupby(["odds_input", "tour"]):
        for other in ("p_bol", "p_pin", "p_mkt_avg", "q_full"):
            h = g[np.isfinite(g[other]) & np.isfinite(g["p_mkt"])]
            if len(h) < 100:
                continue
            v = S.gain(h["p_mkt"], h[other], h["y"].to_numpy(), h["block"].to_numpy())
            rows.append({"source": src, "tour": tour, "compared": other, "n": int(len(h)),
                         "ll_input": float(S.ll(h["p_mkt"], h["y"]).mean()),
                         "ll_compared": float(S.ll(h[other], h["y"]).mean()),
                         **{a: v[a] for a in ("est", "lo", "hi", "p_better")}, "verdict": S.verdict(v),
                         "first_day": str(h["tournament_date"].min().date()),
                         "last_day": str(h["tournament_date"].max().date())})
    return pd.DataFrame(rows)


def same_matches() -> pd.DataFrame:
    """2. The benchmark (the tennis scout's suggestion #4, 12 Oct 2026). On the matches of 2024 - 7 Sep 2025 that have
    both Pinnacle's close (the model's input there) and BetOnline's last line: the model's gain over each price
    (margin-free, raw) and their difference. A larger gain over BetOnline on the same matches is BetOnline's extra
    softness, which 2026's edge (fed and scored against BetOnline's line) contains and an edge against Pinnacle would
    not. mLL, + = the model better; the difference + = the model gains more against BetOnline."""
    df = pd.read_parquet(E.OUT / "analysis.parquet")
    df = df[df["season"].isin((2024, 2025)) & ~df["debut"] & (df["tournament_date"] <= pd.Timestamp("2025-09-07"))]
    df = df[df["odds_input"].str.startswith("pinnacle")].copy()
    df["p_bol"] = demargin(df["bol_a"].to_numpy(float), df["bol_b"].to_numpy(float))
    df["p_pin"] = demargin(df["pin_a"].to_numpy(float), df["pin_b"].to_numpy(float))
    df = df[np.isfinite(df["p_bol"]) & np.isfinite(df["p_pin"])]
    rows = []
    for tour in ("both", "atp", "wta"):
        g = df if tour == "both" else df[df["tour"] == tour]
        y, blk = g["y"].to_numpy(), g["block"].to_numpy()
        vp = S.gain(g["p_pin"], g["q_full"], y, blk)
        vb = S.gain(g["p_bol"], g["q_full"], y, blk)
        vd = S.gain(g["p_bol"], g["p_pin"], y, blk)
        for name, v in (("model over Pinnacle's close", vp), ("model over BetOnline's last line", vb),
                        ("Pinnacle over BetOnline (= the extra the model gains against BetOnline)", vd)):
            rows.append({"tour": tour, "reading": name, "n": int(len(g)), **v, "verdict": S.verdict(v),
                         "first_day": str(g["tournament_date"].min().date()),
                         "last_day": str(g["tournament_date"].max().date())})
    return pd.DataFrame(rows)


def sharpest() -> pd.DataFrame:
    """3. The sharpest close (the practitioner's suggestion 1, 12 Oct 2026). The model's final forecast against each
    other close the instance's odds_sources.parquet holds, on the matches that close exists for, 2025 - 28 Jul 2026:
    Betfair's exchange close (p_bfe, untimed), Polymarket's price 30 minutes before the listed start (p_pm_m30), their
    log-odds average (the "sharp consensus"), the books' average (p_avg), and the model's own input (p_mkt). Every price
    margin-free and raw (no recalibration: Polymarket has no earlier seasons to fit one on). mLL, + = the model better;
    and each price against the input on the same matches (+ = that price sharper than the input). By period: 2025 to
    7 Sep (Pinnacle the input), 8 Sep - Dec 2025 and 2026 (BetOnline the input, mostly)."""
    df = pd.read_parquet(E.OUT / "analysis.parquet")
    df = df[df["season"].isin((2025, 2026)) & ~df["debut"]].copy()
    o = pd.read_parquet(E.INSTANCE / "odds_sources.parquet", columns=["match_id", "p_bfe", "p_pm_m30", "p_avg"])
    df = df.merge(o.astype({"match_id": str}), on="match_id", how="left")
    lb, lp = S.lg(df["p_bfe"].to_numpy(float)), S.lg(df["p_pm_m30"].to_numpy(float))
    both = np.isfinite(lb) & np.isfinite(lp)
    df["p_sharp"] = np.where(both, 1 / (1 + np.exp(-(lb + lp) / 2)), np.nan)
    period = np.where(df["tournament_date"] <= pd.Timestamp("2025-09-07"), "2025 to 7 Sep (Pinnacle input)",
                      np.where(df["season"] == 2025, "8 Sep - Dec 2025", "2026 to 28 Jul"))
    df["period"] = period
    rows = []
    for (per, tour), g0 in df.groupby(["period", "tour"]):
        for bench in ("p_sharp", "p_bfe", "p_pm_m30", "p_avg", "p_mkt"):
            g = g0[np.isfinite(g0[bench].to_numpy(float))]
            if len(g) < 150:
                continue
            y, blk = g["y"].to_numpy(), g["block"].to_numpy()
            v = S.gain(g[bench], g["q_full"], y, blk)
            w = S.gain(g["p_mkt"], g[bench], y, blk) if bench != "p_mkt" else {k: np.nan for k in ("est", "lo", "hi")}
            rows.append({"period": per, "tour": tour, "benchmark": bench, "n": int(len(g)),
                         **{f"model_over_{k}": v[k] for k in ("est", "lo", "hi", "p_better")},
                         "verdict": S.verdict(v), **{f"bench_over_input_{k}": w[k] for k in ("est", "lo", "hi")}})
    return pd.DataFrame(rows)


def main() -> int:
    s = sources()
    s.to_csv(E.OUT / "check_sources.csv", index=False)
    b = same_matches()
    b.to_csv(E.OUT / "check_benchmark.csv", index=False)
    h = sharpest()
    h.to_csv(E.OUT / "check_sharpest.csv", index=False)
    pd.set_option("display.width", 250)
    print(s.round(4).to_string(index=False))
    print(b.round(3).to_string(index=False))
    print(h.round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
