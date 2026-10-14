"""Runs the registered dry run (look.py's run(), window "dry-run" = seasons 2023-2024, already read in discovery) and
writes its result here instead of data/studies/unpriced_leads/looks/dry-run/ (the red team writes only its own folder).
Then compares it with the lead's stored dry run, field by field (run_at excepted).
Run: PYTHONDONTWRITEBYTECODE=1 ./python.sh data/studies/unpriced_leads/team/red_team/dry_run_here.py
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import json  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.unpriced_leads import look  # noqa: E402


def flat(o, pre=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from flat(v, f"{pre}.{k}" if pre else str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from flat(v, f"{pre}[{i}]")
    else:
        yield pre, o


def main() -> int:
    res = look.run(ROOT / "docs" / "studies" / "unpriced_leads" / "registry.json", "dry-run", None)
    (HERE / "dry_run_result.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    mine = dict(flat(json.loads(json.dumps(res, default=float))))
    theirs = dict(flat(json.loads((ROOT / "data" / "studies" / "unpriced_leads" / "looks" / "dry-run" /
                                   "result.json").read_text(encoding="utf-8"))))
    diffs = []
    for k in sorted(set(mine) | set(theirs)):
        if k.endswith("run_at"):
            continue
        a, b = mine.get(k, "<absent>"), theirs.get(k, "<absent>")
        if isinstance(a, float) and isinstance(b, float):
            if not (abs(a - b) <= 1e-9 or (a != a and b != b)):
                diffs.append((k, a, b))
        elif a != b:
            diffs.append((k, a, b))
    print(f"fields compared: {len(set(mine) | set(theirs))}; differing (run_at excepted): {len(diffs)}")
    for d in diffs[:40]:
        print("  ", d)
    o = res["omnibus"]
    print(f"OMNIBUS beta {o['beta']:+.4f} z {o['z']:+.2f} G {o['blocks']} p1 {o['p_one_sided']:.4f} "
          f"real {o['realisation']:+.3f} rms {o['score_rms']:.4f}")
    for k, v in o["secondary"].items():
        print(f"   {k:<18} beta {v.get('beta', float('nan')):+.4f} z {v.get('z', float('nan')):+.2f} "
              f"n {v.get('n')} G {v.get('blocks')}")
    for g in res["groups"]:
        print(f"{g['id']} beta {g['beta']:+.4f} z {g['z']:+.2f} p1 {g['p_one_sided']:.3f} holm {g['p_holm']:.3f} "
              f"rms {g['score_rms']:.4f} real {g['realisation']:+.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
