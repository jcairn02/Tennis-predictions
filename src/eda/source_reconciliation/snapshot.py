"""Freeze the shared tables the study reads, with a manifest of their SHA-256, size and modification time.

Copies Stage 0 (matches, player rows, summary), every match-timing link file and the data map's per-match source list
into data/studies/source_reconciliation/_snapshot/. Every part of the study reads these copies, so a rebuild of the live
tables by another session cannot change its inputs mid-way. Refuses to overwrite an existing snapshot unless --force.

Run: ./python.sh src/eda/source_reconciliation/snapshot.py
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402

FILES = [
    (C.STAGE0_LIVE / "stage0_matches.parquet", "stage0_matches.parquet"),
    (C.STAGE0_LIVE / "stage0_match_players.parquet", "stage0_match_players.parquet"),
    (C.STAGE0_LIVE / "stage0_summary.json", "stage0_summary.json"),
    (C.STUDIES / "data_map" / "matches.parquet", "data_map_matches.parquet"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if (C.SNAP / "manifest.json").exists() and not args.force:
        print(f"snapshot exists: {C.SNAP} (use --force to replace it)")
        return 1
    (C.SNAP / "links").mkdir(parents=True, exist_ok=True)
    pairs = list(FILES) + [(p, f"links/{p.name}") for p in sorted(C.LINKS_LIVE.glob("*.parquet"))]
    rows = []
    for src, rel in pairs:
        before = src.stat()
        dst = C.SNAP / rel
        shutil.copy2(src, dst)
        after = src.stat()
        if (before.st_size, before.st_mtime) != (after.st_size, after.st_mtime):
            print(f"changed while copying: {src}")
            return 2
        digest = C.sha256(dst)
        if digest != C.sha256(src):
            print(f"copy differs from source: {src}")
            return 2
        rows.append({"source": str(src.relative_to(C.ROOT)).replace("\\", "/"), "copy": rel, "bytes": after.st_size,
                     "modified": datetime.fromtimestamp(after.st_mtime, tz=timezone.utc).isoformat(timespec="seconds"),
                     "sha256": digest})
        print(f"{rel}: {after.st_size:,} bytes {digest[:12]}")
    C.write_json(C.SNAP / "manifest.json", {"made_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                            "files": rows})
    return 0


if __name__ == "__main__":
    sys.exit(main())
