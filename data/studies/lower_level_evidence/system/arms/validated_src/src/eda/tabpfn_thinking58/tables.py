"""Print the write-up's tables (docs/studies/tabpfn_thinking58/README.md) from results.json and roi.csv, so that every
number in it is read from the study's outputs.
Run: ./python.sh src/eda/tabpfn_thinking58/tables.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_thinking58 import common as C  # noqa: E402

NAMES = {"thinking": "Thinking (raw)", "thinking_final": "Thinking (raw) + speed offset", "twin": "Twin, calibrated",
         "twin4": "Twin, 4 seeds, calibrated", "twin_raw": "Twin, raw", "twin_final": "Twin, calibrated + speed offset",
         "best": "Current best model (both stages)", "best_stage1": "Current best, stage 1 (calibrated)",
         "market": "Close, recalibrated", "mkt": "Close (market average), de-vigged",
         "price_early": "Polymarket 24 h price", "price_early_recal": "Polymarket 24 h price, recalibrated",
         "thinking_wf": "Thinking, own walk-forward slope", "twin_wf": "Twin, own walk-forward slope"}


def cell(r) -> str:
    v = "tie" if r["lo"] <= 0 <= r["hi"] else ("better" if r["lo"] > 0 else "worse")
    return f"{r['gain']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}] {v}"


def pick(R: pd.DataFrame, setting: str, window: str, base: str, model: str, tour: str):
    k = R[(R["setting"] == setting) & (R["window"] == window) & (R["base"] == base) & (R["model"] == model) &
          (R["tour"] == tour)]
    return k.iloc[0] if len(k) else None


def table(R, rows, setting, window):
    print(f"\n{setting}, {window} (positive = the second-named better)\n")
    print("| Comparison | Both tours | Men | Women |\n|---|---|---|---|")
    for b, m in rows:
        cells = [pick(R, setting, window, b, m, t) for t in ("both", "atp", "wta")]
        if all(c is None for c in cells):
            continue
        print(f"| {NAMES.get(b, b)} → {NAMES.get(m, m)} | " +
              " | ".join(cell(c) if c is not None else "" for c in cells) + " |")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")            # the tables use arrows and the Windows console is cp1252
    res = json.loads((C.OUT / "results.json").read_text(encoding="utf-8"))
    R = pd.DataFrame(res["comparisons"])
    roi = pd.read_csv(C.OUT / "roi.csv")
    facts = res["facts"]
    table(R, [("twin", "thinking"), ("twin4", "thinking"), ("best_stage1", "thinking"), ("twin_raw", "thinking"),
              ("market", "thinking"), ("market", "twin"), ("market", "best_stage1")],
          "close, base forecasts", "2022-2026")
    table(R, [("twin_final", "thinking_final"), ("best", "thinking_final"), ("market", "thinking_final"),
              ("market", "twin_final"), ("market", "best"), ("thinking", "thinking_final"), ("twin", "twin_final"),
              ("best_stage1", "best")], "close, with the speed offset", "2024-2026")
    table(R, [("twin_final", "thinking_final"), ("best", "thinking_final"), ("market", "thinking_final"),
              ("market", "best")], "close, with the speed offset from 2024", "2022-2026")
    table(R, [("thinking", "thinking_wf"), ("twin_raw", "twin_wf"), ("twin_wf", "thinking"), ("twin_wf", "thinking_wf")],
          "close, own walk-forward calibration", "2023-2026")
    table(R, [("twin", "thinking"), ("twin_final", "thinking_final"), ("best", "thinking_final"),
              ("price_early_recal", "thinking_final"), ("price_early_recal", "twin_final"), ("price_early_recal", "best"),
              ("price_early", "thinking")], "Polymarket price 24 h out", "2025-2026")
    print("\nBy season, both tours: twin -> thinking | twin_final -> thinking_final | best -> thinking_final\n")
    for Y in C.TEST_YEARS:
        cells = [pick(R, "close, by season", str(Y), b, m, "both") for b, m in
                 (("twin", "thinking"), ("twin_final", "thinking_final"), ("best", "thinking_final"))]
        print(f"| {Y} | " + " | ".join(cell(c) if c is not None else "" for c in cells) + " |")
    print("\nIn-sample slopes 2022-2026 (diagnosis only; 1 = calibrated), and SD of log-odds minus the raw close\n")
    for k, v in facts["slopes_in_sample_2022_2026"].items():
        print(f"| {NAMES.get(k, k)} | " + " | ".join(f"{v[t]['slope']:.3f} ± {v[t]['se']:.3f} (SD {v[t]['sd_vs_close']:.3f})"
                                                     for t in C.TOURS) + " |")
    print("\nAgreement:", json.dumps(facts.get("agreement"), indent=0))
    print("\nThe return (owner's staking unless flat). ROI and intervals in percent.\n")
    for book in ("pinnacle", "betonline"):
        b = roi[roi["book"] == book]
        for (pop, subset, staking, rule), g in b.groupby(["population", "subset", "staking", "rule"], sort=False):
            g = g.set_index("forecast")
            first = g.iloc[0]
            print(f"\n{book}, {pop}, {subset}, {staking} stakes, {rule}: {int(first['matches'])} matches "
                  f"{first['first_day']} to {first['last_day']} ({int(first['blocks'])} four-week blocks), mean margin "
                  f"{100 * first['book_margin_mean']:.2f}%\n")
            print("| Forecast | Edge threshold | Bets | Staked | Profit | ROI [95%] | vs Thinking, points [95%] |\n"
                  "|---|---:|---:|---:|---:|---|---|")
            for fc in ("thinking_final", "best", "twin_final", "thinking", "twin", "twin_raw", "market", "mkt"):
                if fc not in g.index:
                    continue
                r = g.loc[fc]
                vs = ""
                if isinstance(r.get("versus"), str):
                    vs = (f"{100 * r['roi_minus_versus']:+.2f} [{100 * r['diff_lo']:+.2f}, {100 * r['diff_hi']:+.2f}]"
                          f" vs {NAMES.get(r['versus'], r['versus'])}")
                print(f"| {NAMES.get(fc, fc)} | {100 * r['threshold']:.2f}% | {int(r['bets']):,} | {r['staked']:,.0f} | "
                      f"{r['profit']:+,.0f} | {100 * r['roi']:+.2f}% [{100 * r['roi_lo']:+.2f}, {100 * r['roi_hi']:+.2f}] "
                      f"| {vs} |")
    print("\nSpeed coefficients:", json.dumps(facts.get("speed_coefficients"), indent=0)[:800])
    if facts.get("thinking_metadata"):
        print("\nThinking metadata:", json.dumps(facts["thinking_metadata"])[:1200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
