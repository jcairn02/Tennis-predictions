"""Design scratch (agent 2): do this folder's window functions reproduce the registered side statistic x_raw
(point_sequence/speed_features.parquet, x_raw_side_a) on men's 2022-2023 matches when fed point means only?
Feature values only; no result, no target.

Run: ./python.sh src/eda/serve_speed_tabpfn/design/modeller_repro.py
Writes data/studies/serve_speed_tabpfn/design/modeller_repro.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.design import modeller_common as M  # noqa: E402
from src.eda.serve_speed_tabpfn.design import modeller_state as S  # noqa: E402
from src.eda.serve_speed_tabpfn.design.modeller_gate import speed_windows  # noqa: E402

REG = ROOT / "data" / "studies" / "point_sequence" / "speed_features.parquet"


def main() -> None:
    reg = pd.read_parquet(REG, columns=["match_id", "tour", "year", "x_raw_side_a"])
    reg = reg[reg["year"].between(2022, 2023) & reg["tour"].eq("atp")]
    p = M.panel("pm_first")
    p = p[(p["year"] <= 2023) & (p["tour"] == "atp") & (p["basis"] == "pm")].copy()
    p = S.centre(p, {}, {"pm": 7.0, "ks": 8.0})
    k = M.match_keys(reg["match_id"])
    t = k.assign(side="A", player_id=k["player_a_id"]).reset_index(drop=True)
    t["x"] = speed_windows(p, t)["x_raw"].to_numpy()
    j = reg.merge(t[["match_id", "x"]], on="match_id", how="left")
    both = j["x"].notna() & j["x_raw_side_a"].notna()
    d = (j.loc[both, "x"] - j.loc[both, "x_raw_side_a"]).abs()
    out = {"men_2022_23_side_a_rows": int(len(j)), "both_present": int(both.sum()),
           "equal_within_1e-6": int((d < 1e-6).sum()), "max_abs_diff": float(d.max()),
           "registered_only": int((j["x_raw_side_a"].notna() & j["x"].isna()).sum()),
           "mine_only": int((j["x"].notna() & j["x_raw_side_a"].isna()).sum())}
    (M.OUT / "modeller_repro.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
