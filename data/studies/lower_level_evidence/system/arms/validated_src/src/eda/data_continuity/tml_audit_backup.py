"""Tennis My Life's own backup of its season files from before its audit of 6 Sep 2026, kept and replayed through the
adapter's gate.

The publisher lists backup_ll_audit_20260906_044746/ in its manifest (the adapter skips it as a duplicate). Those 31
files are the only versions older than the project's copy of 22 Sep. They are downloaded once into
data/raw/data_continuity/tennis_my_life/ with receipts; the 8 seasons the project holds (2016-19, 2022, 2024-26) are
then compared with its 22 Sep copies by the gate's own row comparison (tennis_my_life.row_changes), to show what
the audit changed and what the gate would have done with it.

Writes data/studies/data_continuity/tml_audit_backup.csv and tml_audit_backup.json.
Run: ./python.sh src/eda/data_continuity/tml_audit_backup.py [--no-fetch]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.data_continuity import common as K  # noqa: E402
from src.ingest.public_dump import common as C  # noqa: E402
from src.ingest.public_dump import tennis_my_life as T  # noqa: E402

PREFIX = "backup_ll_audit_20260906_044746/"
ROOT = K.RAW / "tennis_my_life"
HELD = C.RAW_ROOT / "tennis_my_life"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-fetch", action="store_true")
    a = ap.parse_args()
    manifests = sorted(ROOT.glob("*/_catalog.json"))
    if not manifests:
        raise SystemExit("no saved manifest; run tml_revisions.py first")
    catalog = json.loads(manifests[-1].read_text(encoding="utf-8"))
    items = [x for x in catalog["files"] if x["name"].startswith(PREFIX)]
    receipts = C.Receipts(PREFIX.rstrip("/"), root=ROOT)
    rows = []
    for item in items:
        name = item["name"]
        dest = ROOT / name
        if not a.no_fetch:
            r = C.download(item["url"], dest, receipts, name=name, validator=T.MATCH_HEADER,
                           extra={"catalog_mtime": item.get("mtime"), "catalog_size": item.get("size")})
            if r.get("error"):
                print(f"FAIL {name}: {r['error']}", flush=True)
                continue
        season_name = name[len(PREFIX):]
        held = HELD / season_name
        row = {"file": season_name, "backup_bytes": dest.stat().st_size if dest.exists() else None,
               "backup_sha256": (receipts.get(name) or {}).get("sha256"), "held_copy": held.exists()}
        if dest.exists() and held.exists():
            old_h, old_r, _ = T.read_rows(dest.read_bytes())
            new_body = held.read_bytes()
            new_h, new_r, _ = T.read_rows(new_body)
            d = T.row_changes(old_h, old_r, new_h, new_r)
            reason = T.make_gate(season_name, dest, {"size": len(new_body)}, set(), {})(new_body)
            row.update({k: d[k] for k in ("rows_old", "rows_new", "added", "removed", "corrected")},
                       cells=json.dumps(d["cells"]), gate=reason or "accepted")
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(K.OUT / "tml_audit_backup.csv", index=False)
    compared = out[out["held_copy"]] if "held_copy" in out else out
    K.write_json(K.OUT / "tml_audit_backup.json", {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "backup": PREFIX, "files": int(len(out)), "kept_in": C.rel(ROOT / PREFIX),
        "compared_with_22_sep_copies": int(len(compared)),
        "totals": {k: int(compared[k].sum()) for k in ("added", "removed", "corrected") if k in compared},
        "gate_outcomes": compared["gate"].value_counts().to_dict() if "gate" in compared else {},
    })
    print(compared.drop(columns=["backup_sha256"], errors="ignore").to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
