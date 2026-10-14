"""Audit step 15: how fast the as-of edition offsets learn each flagged Slam break (panel.EditionOffsets, the project's
own class, refitted in memory; nothing written). For each edition: gamma as of each day from the first match day to 30 days
after the last, the rows released, and the gap to the settled value (the as-of value 30 days after the edition).
Gap = the part of the edition's shift NOT yet removed from its rows when they enter a target's history that day."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
SCR = Path.cwd() / "data" / "studies" / "input_data_audit" / "speed"   # run from the repo root
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 400)
from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402

panel = P.load_panel(use_only=True)
EDS = [("atp", "2024-580|M|pts"), ("wta", "2024-580|M|pts"), ("atp", "2023-520|M|pts"), ("atp", "2025-540|M|pts"),
       ("atp", "2025-540|Q|pts"), ("wta", "2025-540|M|pts"), ("atp", "2026-560|M|pts"), ("atp", "2026-560|Q|pts"),
       ("wta", "2026-905|M|pts"), ("atp", "2025-580|M|pts"), ("atp", "2026-520|M|pts")]
out = []
eo = {t: P.EditionOffsets(panel, t, cache=False) for t in ("atp", "wta")}
for tour, ed in EDS:
    q = panel[(panel["tour"] == tour) & (panel["edition"] == ed)]
    if q.empty:
        print("missing", tour, ed)
        continue
    d0, d1 = int(q["es"].min()), int(q["lf"].max())
    fam = q["family"].iloc[0]
    days = list(range(d0, d1 + 32))
    g = []
    for d in days:
        s = eo[tour].at(d)
        rel = int(((q["lf"] + 1) <= d).sum())
        g.append({"tour": tour, "edition": ed, "family": fam, "day": d, "date": str(pd.Timestamp(d, unit="D").date()),
                  "gamma": float(s.get(ed, np.nan)), "rows_released": rel, "rows_total": len(q)})
    g = pd.DataFrame(g)
    settled = g["gamma"].iloc[-1]
    g["gap_to_settled"] = g["gamma"] - settled
    out.append(g)
    first = g[g["rows_released"] > 0]
    print(f"\n=== {tour} {ed} ({fam}); rows {len(q)}; settled gamma {settled:.2f}; before release (family fallback) "
          f"{g['gamma'].iloc[0]:.2f}")
    show = g[(g["day"] <= d1 + 2)]
    print(show[["date", "rows_released", "gamma", "gap_to_settled"]].round(2).to_string(index=False))
O = pd.concat(out, ignore_index=True)
O.to_csv(SCR / "t_offset_learning.csv", index=False)
