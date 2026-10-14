"""Lead's re-check (13 Oct 2026, after the market builder's curvature reading): the shortlisted luck and totals members
screened beside the close with per-tour curvature terms in the base (harness `curv=True`), raw and orthogonal, seasons
<= 2024 only (through the harness). Writes data/studies/unpriced_leads/lead_checks/curv_check.csv.
Run: ./python.sh src/eda/unpriced_leads/curv_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.unpriced_leads import screen as H  # noqa: E402

C = H.OUT / "candidates"
MEMBERS = {
    "luck": [("PS01_tb", "diff"), ("PS06_close", "diff"), ("PS03_hold", "diff"), ("PS03_net", "diff"),
             ("PS03_conv", "diff"), ("PS03_save", "diff"), ("PS04_flat", "diff"), ("PS03_chance", "diff"),
             ("I025_pool", "diff")],
    "market": [("mp01_lop_move", "context"), ("mp01_lop_close", "context")],
}


def main() -> int:
    f = H.load_frame()
    rows = []
    for fam, mem in MEMBERS.items():
        v = pd.read_parquet(C / fam / "values.parquet", columns=["match_id"] + [m for m, _ in mem])
        v = v.astype({"match_id": str}).drop_duplicates("match_id").set_index("match_id")
        for name, kind in mem:
            x = v[name].reindex(f["match_id"]).to_numpy(float)
            forms = [(name, x)]
            if kind == "diff":
                xo, _ = H.orthogonal_part(f, x)
                forms.append((name + "__orth", xo))
            for nm, xx in forms:
                for curv in (False, True):
                    cl = H.close_lens(f, xx, nm, kind, curv=curv)
                    for _, r in cl[cl["era"] == "2013-24 pooled"].iterrows():
                        eras = cl[(cl["tour"] == r["tour"]) & (cl["era"] != "2013-24 pooled")]
                        rows.append({"family": fam, "name": nm, "kind": kind, "curv": curv, "tour": r["tour"],
                                     "beta": r["beta"], "z": r["z"], "eras_same_sign": r["eras_same_sign"],
                                     **{f"z_{e}": float(eras[eras["era"] == e]["z"].iloc[0])
                                        for e in H.ERAS if (eras["era"] == e).any()}})
    out = pd.DataFrame(rows)
    d = H.OUT / "lead_checks"
    d.mkdir(parents=True, exist_ok=True)
    out.to_csv(d / "curv_check.csv", index=False)
    piv = out[out["tour"] == "both"].pivot_table(index="name", columns="curv", values="z").round(2)
    print(piv.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
