"""Final-test verifier, step 0: inventory of the base's forecast files (forecasts only, no result read).

For every season 2014-2026 and seed 0-15: which of this study's local fits (C.LOCAL) and the rating race's (C.RACE_LOCAL)
hold model__<season>__seed<k>.npz, their keys, and whether the two copies agree where both exist.

    ./python.sh src/eda/feature_interactions/verify_final/inventory.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402

OUT = C.OUT / "verify_final"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, keys, disagree = {}, {}, []
    for s in range(2014, 2027):
        loc, race = [], []
        for k in range(16):
            name = f"model__{s}__seed{k}.npz"
            a, b = C.LOCAL / name, C.RACE_LOCAL / name
            if a.exists():
                loc.append(k)
            if b.exists():
                race.append(k)
            for p in (a, b):
                if p.exists() and s not in keys:
                    with np.load(p, allow_pickle=False) as z:
                        keys[s] = {q: list(z[q].shape) for q in z.files}
            if a.exists() and b.exists():
                with np.load(a, allow_pickle=False) as za, np.load(b, allow_pickle=False) as zb:
                    for q in ("p_td", "ids_td", "p_early", "ids_early"):
                        if q in za.files and q in zb.files:
                            same = (za[q].shape == zb[q].shape) and bool(np.all(za[q] == zb[q]))
                            if not same:
                                disagree.append([s, k, q])
        rows[s] = {"local": loc, "race": race}
    out = {"files": rows, "keys_by_season": keys, "local_vs_race_disagree": disagree}
    (OUT / "inventory.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for s, r in rows.items():
        print(s, "local", r["local"], "race", r["race"])
    print("keys 2014:", keys.get(2014))
    print("keys 2025:", keys.get(2025))
    print("disagreements:", disagree[:10], len(disagree))
    return 0


if __name__ == "__main__":
    sys.exit(main())
