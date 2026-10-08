"""Render the write-up's tables from results.json (so that docs/studies/tabpfn_thinking/README.md holds only numbers
a script produced). Prints markdown; writes nothing.

Run: ./python.sh src/eda/tabpfn_thinking/tables.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_thinking import common as T  # noqa: E402

LABEL = {
    "market": "Odds recalibrated (one slope)", "market_raw": "Raw odds",
    "tabpfn": "**TabPFN-3.5-Thinking** (odds + 53 inputs)",
    "lr_mkt_profile": "Linear: odds + 16-input profile", "lr_mkt_everything": "Linear: odds + everything (9)",
    "lr_mkt_everything_profile": "Linear: odds + everything + profile (25)", "lr_mkt_all": "Linear: odds + all 47 differences",
    "gbm_mkt_additive": "Boosting, no interactions: odds + 47", "gbm_mkt": "Boosting with interactions: odds + 53",
    "elo": "Elo recalibrated", "elo_raw": "Raw Elo", "lr_everything": "Linear: Elo + everything (9)",
    "lr_all": "Linear: Elo + all 47 differences", "gbm_additive": "Boosting, no interactions (47)",
    "gbm": "Boosting with interactions (53)", "stack_base": "Odds (cross-fitted)",
}


def lab(k: str) -> str:
    return LABEL.get(k, k)


def fmt(r: dict) -> str:
    return f"{r['gain']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}]"


def table(res: dict, section: str, title: str, tours=("atp", "wta", "both")) -> str:
    rows = {}
    for t in tours:
        for r in res[section][t]:
            rows.setdefault((r["base"], r["model"]), {})[t] = r
    out = [f"**{title}**", "", "| Base → model | Men | Women | Both |", "|---|---:|---:|---:|"]
    for (b, m), d in rows.items():
        out.append(f"| {lab(b)} → {lab(m)} | " + " | ".join(fmt(d[t]) if t in d else "" for t in tours) + " |")
    n = {t: next(iter(res[section][t]))["n"] for t in tours}
    out += ["", f"Matches: men {n['atp']:,}, women {n['wta']:,}, both {n['both']:,}."]
    return "\n".join(out)


def main() -> int:
    res = json.loads((T.OUT / "results.json").read_text(encoding="utf-8"))
    print(table(res, "beyond_odds", "Against the odds recalibrated (models with the odds as an input)"))
    print()
    print(table(res, "beyond_odds_raw", "Against the raw odds"))
    print()
    print(table(res, "nonlinear_odds", "Non-linear against linear, with the odds as an input"))
    print()
    print(table(res, "stack", "Each forecast stacked with the odds (cross-fitted by season) against the odds stacked alone"))
    print()
    print(table(res, "stack_forward", "The same, forward-only (2023-2026, each season fitted on the earlier ones)"))
    print()
    print(table(res, "beyond_elo", "Without the odds: against Elo recalibrated (every test match)"))
    print()
    print(table(res, "nonlinear_no_odds", "Without the odds: non-linear against linear"))
    print()
    lad = res["ladder"]
    keys = ["elo_raw", "elo", "lr_all", "gbm", "market", "lr_mkt_profile", "lr_mkt_everything_profile", "lr_mkt_all",
            "gbm_mkt", "tabpfn", "stack_tabpfn"]
    print("**Ladder** (coin 0%, raw odds 100%; test matches with odds)\n")
    print("| Forecast | Men | Women | Both |\n|---|---:|---:|---:|")
    for k in keys:
        if k in lad["atp"]:
            print(f"| {lab(k)} | " + " | ".join(f"{100 * lad[t][k]:.1f}%" for t in ("atp", "wta", "both")) + " |")
    print()
    print("**Adjustment to the price** (model log-odds minus recalibrated odds; share explained on held-out tournaments)\n")
    print("| Model | Tour | sd of adjustment | mean abs prob change | linear | additive | + interactions | interaction share |")
    print("|---|---|---:|---:|---:|---:|---:|---:|")
    for m, d in res["adjustment"].items():
        for t, v in d.items():
            print(f"| {lab(m)} | {t} | {v['adjustment_sd']:.3f} | {v['adjustment_mean_abs_prob']:.4f} | {v['linear']:.2f} | "
                  f"{v['additive']:.2f} | {v['with_interactions']:.2f} | {v['interaction_share']:.2f} |")
    print()
    print("**Group importance in the adjustment surrogate** (share explained lost when the group is permuted)\n")
    groups = list(next(iter(next(iter(res["adjustment"].values())).values()))["group_importance_r2_drop"])
    print("| Model | Tour | " + " | ".join(groups) + " |\n|---|---|" + "---:|" * len(groups))
    for m, d in res["adjustment"].items():
        for t, v in d.items():
            print(f"| {lab(m)} | {t} | " + " | ".join(f"{v['group_importance_r2_drop'].get(g, float('nan')):.2f}" for g in groups) + " |")
    print()
    if res["tabpfn"].get("tabpfn"):
        i = res["tabpfn"]
        print(f"TabPFN asymmetry: mean |P(A|x) - (1 - P(A|swapped x))| {i['asymmetry_mean_abs']:.4f}, "
              f"95th percentile {i['asymmetry_p95']:.4f}, max {i['asymmetry_max']:.4f}")
    for k, v in res["agreement"].items():
        print(f"agreement {k}: {v}")
    print()
    for t in ("atp", "wta"):
        print(t, "stack coefficients:", {m: (round(c['odds'][0], 3), round(c['model'][0], 3), round(c['model'][1], 3))
                                         for m, c in res["stack_coefs"][t].items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
