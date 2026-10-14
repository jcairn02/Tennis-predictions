"""Outcome-free: what the registered completeness gate does on Look A (seasons 2025-2026 before 29 Jul 2026), computed
before the look and registered with it. Reads the frame without its result column, the members' values and the gate's
input counts. Writes data/studies/unpriced_leads/registration/gate_lookA.json.
Run: ./python.sh src/eda/unpriced_leads/gate_lookA.py
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

from src.eda.unpriced_leads import look as LK  # noqa: E402


def main() -> int:
    reg = json.loads((ROOT / "docs" / "studies" / "unpriced_leads" / "registry.json").read_text(encoding="utf-8"))
    paths = LK.instance_paths(reg)
    f = pd.read_parquet(paths["frame"], columns=["match_id", "tour", "season", "tournament_date", "debut_season"])
    if "a_won" in f.columns:
        raise RuntimeError("no result column may be read here")
    f = f[~f["debut_season"].astype(bool) & f["season"].between(2025, 2026) &
          (f["tournament_date"] < pd.Timestamp("2026-07-29"))].copy()
    f["match_id"] = f["match_id"].astype(str)
    f["month"] = f["tournament_date"].dt.to_period("M").astype(str)
    f = f.reset_index(drop=True)
    LK._load_frame_months(paths)
    out = {"matches": int(len(f)), "members": {}}
    for g in reg["groups"] + reg.get("look_b_only", []):
        for m in g["members"]:
            v = pd.read_parquet(ROOT / m["values"], columns=["match_id", m["column"]]).astype({"match_id": str})
            x_all = v.drop_duplicates("match_id").set_index("match_id")[m["column"]]
            ok, failed = LK.gate_mask(m, f, x_all)
            share = {t: float(np.mean(~ok[(f["tour"] == t).to_numpy()])) for t in ("atp", "wta")}
            out["members"][m["column"]] = {"group": g["id"], "gate": m.get("gate"), "failed_months": failed,
                                           "share_of_lookA_matches_gated": share}
    d = ROOT / "data" / "studies" / "unpriced_leads" / "registration"
    (d / "gate_lookA.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out["members"].items():
        print(f"{v['group']:>3} {k:<42} gate {v['gate']:<12} gated men {v['share_of_lookA_matches_gated']['atp']:.2f} "
              f"women {v['share_of_lookA_matches_gated']['wta']:.2f}  {sorted(v['failed_months'])[:3]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
