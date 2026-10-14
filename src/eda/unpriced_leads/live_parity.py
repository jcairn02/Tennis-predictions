"""Step 3's proof: the registered members computed for live rows equal the same members computed with the matches
played, on the same tables (rules: docs/studies/unpriced_leads/check_now_rules.md).

From a replay work tree (the daily engine's `run_day --replay-week W --replay-round R --no-fit --keep-worktree`,
training dating: the instance's timeline held):
    live      live_members.py run in the tree for the replayed matches: live rows, results removed, later rounds held back
    restored  the same module on the same tree, with Stage 0 restored for those matches only (their rows as played, their
              later rounds back; every other row identical, the accepted package included)
Both must agree to 1e-9 on every built member (NaN = NaN counts as equal). Also reported, for information: both
against the registered values files, which were built on the repository's 8 Oct Stage 0 and the 12 Oct clock, so
table versions may differ there.
Writes data/studies/unpriced_leads/check_now/live_parity/<name>.json and <name>.csv.
Run: ./python.sh src/eda/unpriced_leads/live_parity.py --live <parquet> --restored <parquet> --name <replay>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.unpriced_leads import live_members as LM  # noqa: E402
from src.eda.unpriced_leads import look as LK  # noqa: E402

OUT = ROOT / "data" / "studies" / "unpriced_leads" / "check_now" / "live_parity"
TOL = 1e-9


def compare(a: np.ndarray, b: np.ndarray) -> dict:
    a, b = np.asarray(a, float), np.asarray(b, float)
    both_nan = np.isnan(a) & np.isnan(b)
    d = np.abs(a - b)
    eq = both_nan | (d <= TOL)
    fin = np.isfinite(a) & np.isfinite(b)
    return {"matches": int(len(a)), "equal": int(eq.sum()), "both_present": int(fin.sum()),
            "only_one_present": int((np.isfinite(a) ^ np.isfinite(b)).sum()),
            "max_abs_diff": float(np.max(d[fin])) if fin.any() else 0.0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", required=True)
    ap.add_argument("--restored", required=True)
    ap.add_argument("--name", required=True)
    a = ap.parse_args()
    lv = pd.read_parquet(a.live).astype({"match_id": str}).set_index("match_id")
    rs = pd.read_parquet(a.restored).astype({"match_id": str}).set_index("match_id").reindex(lv.index)
    reg = json.loads((ROOT / "docs" / "studies" / "unpriced_leads" / "registry.json").read_text(encoding="utf-8"))
    members = {m["column"]: m for g in reg["groups"] for m in g["members"]}
    built = list(LM.POOL) + LM.RHYTHM
    rows = []
    for col in built:
        m = members[col]
        regv = pd.read_parquet(ROOT / m["values"], columns=["match_id", col]).astype({"match_id": str})
        LK.check_hash(ROOT / m["values"], m.get("values_sha256"), col)
        regv = regv.drop_duplicates("match_id").set_index("match_id")[col].reindex(lv.index).to_numpy(float)
        rows.append({"member": col, "comparison": "live vs restored (the proof)",
                     **compare(lv[col].to_numpy(float), rs[col].to_numpy(float))})
        rows.append({"member": col, "comparison": "restored vs registered file (information)",
                     **compare(rs[col].to_numpy(float), regv)})
    t = pd.DataFrame(rows)
    proof = t[t["comparison"].str.startswith("live")]
    passed = bool((proof["equal"] == proof["matches"]).all())
    OUT.mkdir(parents=True, exist_ok=True)
    t.to_csv(OUT / f"{a.name}.csv", index=False)
    rec = {"name": a.name, "matches": int(len(lv)), "members_built": built, "not_built": LM.NOT_BUILT,
           "tolerance": TOL, "proof_passed": passed, "rows": rows}
    (OUT / f"{a.name}.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    pd.set_option("display.width", 220)
    print(t.to_string(index=False))
    print(f"PROOF {'PASSED' if passed else 'FAILED'}: live = restored on every built member ({len(lv)} matches)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
