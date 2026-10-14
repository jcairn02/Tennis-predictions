"""The tour-pooling study's money context: each model's return at the closes, against the current model's, paired.

The Pinnacle-first backtest's rules (src/eda/pinnacle_first/backtest.py, from tabpfn_thinking58.score): completed
matches with both sides priced at the book; back the side whose expected return p d - 1 is the larger and above the
threshold (0, the primary; 2%); the owner's staking (tabpfn_thinking58.common.stake); ROI = profit / staked. The books:
Pinnacle's close as the current instance's input takes it (to 7 Sep 2025) and BetOnline's last line (OddsTrader, to Jul
2026), from the instance's book_prices.parquet.

The forecasts are the scorer's both-stage forecasts (data/studies/tour_pooling/scores/forecasts.parquet, q_<model>:
seeds 0-3, walk-forward calibration and speed stage), so the current model here is its 4-seed version. Matches: debut
seasons out, 2022 to 28 Jul 2026 (no sealed result is in the table) and 2020-2024. Intervals: 2,000 draws of four-week
blocks, the same draws for every model in a cell, so "minus pooled" is paired.

Context, not a verdict: the inputs were chosen on these seasons, and these are archived closes, not fills.
Writes data/studies/tour_pooling/money/roi.csv. Run: ./python.sh src/eda/tour_pooling/money.py
"""
from __future__ import annotations

import sys
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.pinnacle_first import backtest as BT  # noqa: E402  (STAGE1_REF: each match's status)
from src.eda.tabpfn_thinking58.score import bets, settle  # noqa: E402
from src.eda.tour_pooling import common as C  # noqa: E402

FORECASTS = C.OUT / "scores" / "forecasts.parquet"
OUT = C.OUT / "money"
BOOKS = {"pinnacle": ("pin_a", "pin_b"), "betonline": ("bol_a", "bol_b")}
RULES = (("edge > 0", 0.0), ("edge > 2%", 0.02))
WINDOWS = {"2022-2026": (2022, 2026), "2020-2024": (2020, 2024)}
DRAWS, RNG_SEED = 2000, 20261009
BASE = "pooled"


def load() -> tuple[pd.DataFrame, list[str]]:
    f = pd.read_parquet(FORECASTS)
    f["match_id"] = f["match_id"].astype(str)
    if (pd.to_datetime(f["tournament_date"]) >= BT.SEALED_FROM).any():
        raise RuntimeError("the forecast table holds a sealed match")
    models = [c[2:] for c in f.columns if c.startswith("q_") and not c.startswith("q_close")
              and not any(c.endswith(f"_s{k}") for k in range(4))]
    if BASE not in models:
        raise RuntimeError("the forecast table lacks the current model (q_pooled)")
    books = pd.read_parquet(C.INSTANCE / "book_prices.parquet").astype({"match_id": str}).set_index("match_id")
    for c in ("pin_a", "pin_b", "bol_a", "bol_b"):
        f[c] = books[c].reindex(f["match_id"]).to_numpy(float)
    st = pd.read_parquet(BT.STAGE1_REF, columns=["match_id", "status"]).astype({"match_id": str}).set_index("match_id")
    f["status"] = st["status"].reindex(f["match_id"]).to_numpy()
    return f, [BASE] + [m for m in models if m != BASE]


def cell(g: pd.DataFrame, models: list[str], ca: str, cb: str, threshold: float, label: dict) -> list[dict]:
    labels, ix = np.unique(g["block"].to_numpy(), return_inverse=True)
    rng = np.random.default_rng([RNG_SEED, zlib.crc32(repr(sorted(label.items())).encode())])
    W = rng.multinomial(len(labels), np.full(len(labels), 1 / len(labels)), size=DRAWS).astype(float)
    rows, draws = [], {}
    for m in models:
        b = bets(g[f"q_{m}"].to_numpy(float), g[ca].to_numpy(float), g[cb].to_numpy(float), threshold)
        profit, _ = settle(b, g["y"].astype(bool).to_numpy())
        stake = b["stake"].to_numpy()
        nb = int(b["bet"].sum())
        draws[m] = (W @ np.bincount(ix, weights=profit, minlength=len(labels))) / \
            np.maximum(W @ np.bincount(ix, weights=stake, minlength=len(labels)), 1e-12)
        rows.append({**label, "model": m, "matches": int(len(g)), "bets": nb, "staked": float(stake.sum()),
                     "profit": float(profit.sum()), "roi": float(profit.sum() / stake.sum()) if nb else np.nan,
                     "roi_lo": float(np.quantile(draws[m], 0.025)) if nb else np.nan,
                     "roi_hi": float(np.quantile(draws[m], 0.975)) if nb else np.nan, "blocks": int(len(labels))})
    base = next(r for r in rows if r["model"] == BASE)
    for r in rows:
        if r["model"] != BASE and r["bets"] and base["bets"]:
            d = draws[r["model"]] - draws[BASE]
            r.update({"minus_pooled": r["roi"] - base["roi"], "minus_pooled_lo": float(np.quantile(d, 0.025)),
                      "minus_pooled_hi": float(np.quantile(d, 0.975)), "p_higher": float((d > 0).mean())})
    return rows


def main() -> int:
    f, models = load()
    rows = []
    for book, (ca, cb) in BOOKS.items():
        ok = (~f["debut"].astype(bool)) & (f["status"] == "completed") & f[ca].notna() & f[cb].notna()
        for wname, (a, b) in WINDOWS.items():
            for pop, tm in (("both tours", None), ("men", "atp"), ("women", "wta")):
                m = ok & f["season"].between(a, b)
                if tm:
                    m &= f["tour"] == tm
                g = f[m.to_numpy()].reset_index(drop=True)
                if len(g) < 200:
                    continue
                for rule, th in RULES:
                    rows += cell(g, models, ca, cb, th, {"book": book, "window": wname, "population": pop,
                                                         "rule": rule, "first_day": str(g["tournament_date"].min())[:10],
                                                         "last_day": str(g["tournament_date"].max())[:10]})
    OUT.mkdir(parents=True, exist_ok=True)
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "roi.csv", index=False)
    show = t[(t["rule"] == "edge > 0") & (t["population"] == "both tours")]
    pd.set_option("display.width", 220)
    print(show[["book", "window", "model", "bets", "roi", "roi_lo", "roi_hi", "minus_pooled", "minus_pooled_lo",
                "minus_pooled_hi", "p_higher"]].round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
