"""Read-only schema dump of the study tables under data/studies/ (the feature-interactions data map, round 0).

For every parquet file outside upload/ and pytest folders: rows, columns and dtypes, from the parquet footer only
(no data is read). Files under data/studies/feature_interactions/ are skipped.

Writes data/studies/feature_interactions/inventory/schemas.json and prints one line per file.
Run: ./python.sh src/eda/feature_interactions/inventory/schemas.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[4]
STUDIES = ROOT / "data" / "studies"
OUT = STUDIES / "feature_interactions" / "inventory"
SKIP_PARTS = {"upload", "uploads", "feature_interactions", "local", "replaced", "cache"}


def wanted(p: Path) -> bool:
    parts = set(p.relative_to(STUDIES).parts[:-1])
    if parts & SKIP_PARTS:
        return False
    return not any(s.startswith("pytest") for s in parts)


def main() -> int:
    rows = []
    for p in sorted(STUDIES.rglob("*.parquet")):
        try:
            if not wanted(p):
                continue
            meta = pq.read_metadata(p)
            schema = pq.read_schema(p)
        except (PermissionError, OSError) as e:          # pytest folders without access, files being written
            rows.append({"path": p.relative_to(ROOT).as_posix(), "error": str(e)[:200]})
            continue
        cols = [{"name": f.name, "type": str(f.type)} for f in schema if f.name != "__index_level_0__"]
        rows.append({"path": p.relative_to(ROOT).as_posix(), "rows": meta.num_rows, "n_columns": len(cols),
                     "bytes": p.stat().st_size, "mtime": p.stat().st_mtime, "columns": cols})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "schemas.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    for r in rows:
        if "error" in r:
            print(f"{r['path']}: ERROR {r['error']}")
        else:
            names = [c["name"] for c in r["columns"]]
            head = ", ".join(names[:12]) + (" ..." if len(names) > 12 else "")
            print(f"{r['path']}: {r['rows']:,} x {r['n_columns']} | {head}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
