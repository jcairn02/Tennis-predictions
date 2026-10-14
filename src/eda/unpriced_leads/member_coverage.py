"""Outcome-free: each registered member's presence and non-zero share on the frame's matches, seasons 2013-2024 and
Look A (seasons 2025-2026 before 29 Jul 2026), by tour; debut seasons out; no result column read.
Writes data/studies/unpriced_leads/registration/member_coverage.csv.
Run: ./python.sh src/eda/unpriced_leads/member_coverage.py
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

from src.eda.unpriced_leads import screen as H  # noqa: E402


def main() -> int:
    reg = json.loads((ROOT / "docs" / "studies" / "unpriced_leads" / "registry.json").read_text(encoding="utf-8"))
    f = pd.read_parquet(H.FRAME, columns=["match_id", "tour", "season", "tournament_date", "debut_season"])
    f = f[~f["debut_season"].astype(bool)].copy()
    f["match_id"] = f["match_id"].astype(str)
    win = {"2013_24": f["season"].between(2013, 2024).to_numpy(),
           "lookA": (f["season"].between(2025, 2026) & (f["tournament_date"] < "2026-07-29")).to_numpy()}
    rows = []
    for g in reg["groups"]:
        for m in g["members"]:
            v = pd.read_parquet(ROOT / m["values"], columns=["match_id", m["column"]]).astype({"match_id": str})
            x = v.drop_duplicates("match_id").set_index("match_id")[m["column"]].reindex(f["match_id"]).to_numpy(float)
            r = {"group": g["id"], "member": m["label"], "column": m["column"]}
            for lab, w in win.items():
                for tour in ("atp", "wta"):
                    k = w & (f["tour"] == tour).to_numpy()
                    r[f"present_{tour}_{lab}"] = float(np.mean(np.isfinite(x[k])))
                    r[f"nonzero_{tour}_{lab}"] = float(np.mean(np.isfinite(x[k]) & (x[k] != 0)))
            rows.append(r)
    out = pd.DataFrame(rows)
    (H.OUT / "registration").mkdir(parents=True, exist_ok=True)
    out.to_csv(H.OUT / "registration" / "member_coverage.csv", index=False)
    pd.set_option("display.width", 250)
    print(out.round(3).to_string(index=False))
    print("Look A matches:", int(win["lookA"].sum()), "by tour", f.loc[win["lookA"], "tour"].value_counts().to_dict())
    return 0


if __name__ == "__main__":
    sys.exit(main())
