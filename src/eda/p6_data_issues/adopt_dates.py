"""Put the Tenerife date correction (D1) into the decided correction tables (owner, 14 Oct 2026;
docs/decisions/2026-10-14-p6-data-issues.md, point 1; its harm check found no harm the same day).

The proposed table (data/studies/p6_data_issues/stage0_review/date_corrections.csv, the three reviewers' 31 matches) is
copied to data/studies/input_data_audit/fixes/date_corrections.csv, which every Stage 0 build applies from then on, and
which history.py counts as decided repairs. As with the Roland Garros repair, the swap and the coordinated live rebuild
(src/eda/data_continuity/rebuild_stage0.py, with --expect the dry run's build) go together: prediction runs build their
own Stage 0 from the decided tables, template builds copy the live one.

    --apply     copy the table in (refused if a decided date table already exists); record its SHA-256 and the harm
                check's reading in data/studies/p6_data_issues/adoption/<stamp>/adoption.json
    --restore <stamp>   move the decided table into that folder's restored/ (nothing is deleted); then rebuild_stage0.py
                --restore with the rebuild's own stamp puts the live tables back
Run: ./python.sh src/eda/p6_data_issues/adopt_dates.py --apply
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROPOSED = ROOT / "data" / "studies" / "p6_data_issues" / "stage0_review" / "date_corrections.csv"
DECIDED = ROOT / "data" / "studies" / "input_data_audit" / "fixes" / "date_corrections.csv"
OUT = ROOT / "data" / "studies" / "p6_data_issues" / "adoption"
HARM = ROOT / "data" / "studies" / "current_best_model" / "2026-10-14_tenerife_dates" / "vs_reference_2026-10-08"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--apply", action="store_true")
    g.add_argument("--restore")
    a = ap.parse_args()
    if a.restore:
        dest = OUT / a.restore / "restored"
        dest.mkdir(parents=True, exist_ok=True)
        if DECIDED.exists():
            shutil.move(str(DECIDED), str(dest / DECIDED.name))
        print(f"the decided date table moved to {dest.relative_to(ROOT)}; now run rebuild_stage0.py --restore <its stamp>")
        return 0
    if DECIDED.exists():
        raise SystemExit(f"{DECIDED.relative_to(ROOT)} exists already: nothing done")
    reading = json.loads((HARM / "adoption_read.json").read_text(encoding="utf-8"))
    if reading.get("decision") != "adopt":
        raise SystemExit(f"the harm check's reading says {reading.get('decision')}: nothing done")
    stamp = time.strftime("%Y%m%dT%H%M%S")
    shutil.copy2(PROPOSED, DECIDED)
    rec = {"stamp": stamp, "decision": "docs/decisions/2026-10-14-p6-data-issues.md", "table": str(DECIDED.relative_to(ROOT)),
           "sha256": sha(DECIDED), "from": str(PROPOSED.relative_to(ROOT)), "replaced": None,
           "harm_check": {k: reading.get(k) for k in ("population", "comparison", "estimate", "lo", "hi", "p_better",
                                                       "reading", "harm", "decision", "input_flags")}}
    (OUT / stamp).mkdir(parents=True, exist_ok=True)
    (OUT / stamp / "adoption.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
