"""Swap test of every audit proxy column (result-free): diff columns must change sign when A and B swap, context
columns must not change. The panel's swap exchanges every _a/_b pair; the model's A - B inputs are negated here.

    ./python.sh src/eda/feature_interactions/round1/math_audit/swap_check.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from src.eda.feature_interactions.panel import swap_sides  # noqa: E402
from src.eda.feature_interactions.round1.math_audit import candidates as CB  # noqa: E402
from src.eda.feature_interactions.round1.math_audit.common_audit import OUT, INPUTS, load_panel, surface_means  # noqa: E402


def swapped(P):
    Q = swap_sides(P.assign(a_won=False)).drop(columns=["a_won"])
    for d in json.loads(INPUTS.read_text())["inputs"]:
        if d["kind"] == "diff":
            Q[f"in_{d['name']}"] = -P[f"in_{d['name']}"]
    return Q


def main() -> int:
    P = load_panel()
    means = surface_means()
    C, K, A = CB.build(P, means)
    C2, K2 = CB.build2(P, means, A)
    C.update(C2)
    K.update(K2)
    Q = swapped(P)
    D, _, A2 = CB.build(Q, means)
    D2, _ = CB.build2(Q, means, A2)
    D.update(D2)
    res = {}
    for name, x in C.items():
        y = D[name]
        ok = np.isfinite(x) & np.isfinite(y)
        want = y if K.get(name, "diff") == "context" else -y
        res[name] = {"kind": K.get(name, "diff"), "max_gap": float(np.max(np.abs(x[ok] - want[ok]))),
                     "same_missing": bool((np.isfinite(x) == np.isfinite(y)).all())}
    (OUT / "swap_check.json").write_text(json.dumps(res, indent=1))
    bad = {k: v for k, v in res.items() if v["max_gap"] > 1e-8 or not v["same_missing"]}
    print(f"{len(res)} columns, {len(bad)} failing")
    for k, v in bad.items():
        print(k, v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
