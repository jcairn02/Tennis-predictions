"""What Tennis My Life changes after publication: today's copies of the files it has revised since the project's own
copy, saved beside it (never over it), and diffed row by row.

The adapter (src/ingest/public_dump/tennis_my_life.py) re-downloads a season file whenever the publisher's manifest
shows a new mtime or size, and writes it over the old one, so a revision is lost on the next run. This script leaves
data/raw/public_dump/tennis_my_life/ untouched: it reads the live manifest, downloads every file whose mtime or size
differs from the adapter's receipt into data/raw/data_continuity/tennis_my_life/<UTC date>/ with receipts, and
compares each with the adapter's copy.

A row is the whole CSV record. Rows present in only one copy are paired by match identity (tournament id and date,
round, both player ids) to separate corrections from additions and removals.

Writes to data/studies/data_continuity/:
    tml_revisions_files.csv    per file: manifest dates and sizes, rows in each copy, added, removed, corrected
    tml_revisions_cells.csv    corrected cells per file and column
    tml_revisions.json         summary, with both copies' SHA-256
Run: ./python.sh src/eda/data_continuity/tml_revisions.py [--no-fetch]
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.data_continuity import common as K  # noqa: E402
from src.ingest.public_dump import common as C  # noqa: E402
from src.ingest.public_dump import tennis_my_life as TML  # noqa: E402

HELD = C.RAW_ROOT / "tennis_my_life"
KEY = ["tourney_id", "tourney_date", "round", "winner_id", "loser_id"]


def read_rows(path: Path) -> pd.DataFrame:
    text, _ = C.open_text(path)
    return pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)


def diff(old: pd.DataFrame, new: pd.DataFrame) -> tuple[dict, Counter]:
    cols = list(dict.fromkeys(list(old.columns) + list(new.columns)))
    old, new = old.reindex(columns=cols, fill_value=""), new.reindex(columns=cols, fill_value="")
    o, n = Counter(map(tuple, old.to_numpy())), Counter(map(tuple, new.to_numpy()))
    gone, came = o - n, n - o
    key_idx = [cols.index(k) for k in KEY if k in cols]
    by_key: dict[tuple, list] = {}
    for row, c in came.items():
        by_key.setdefault(tuple(row[i] for i in key_idx), []).extend([row] * c)
    corrected, cells = 0, Counter()
    removed = 0
    for row, c in gone.items():
        for _ in range(c):
            twins = by_key.get(tuple(row[i] for i in key_idx))
            if twins:
                twin = twins.pop()
                corrected += 1
                for j, col in enumerate(cols):
                    if row[j] != twin[j]:
                        cells[col] += 1
            else:
                removed += 1
    added = sum(len(v) for v in by_key.values())
    return {"rows_old": int(len(old)), "rows_new": int(len(new)), "added": added, "removed": removed,
            "corrected": corrected, "columns_changed": len(set(old.columns) ^ set(new.columns))}, cells


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-fetch", action="store_true", help="compare the copies already saved, download nothing")
    a = ap.parse_args()
    held = C.Receipts(TML.SOURCE)
    root = K.RAW / "tennis_my_life"
    if not a.no_fetch:
        day = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
        r = C.download(TML.CATALOG_URL, root / day / "_catalog.json", C.Receipts(day, root=root), name="_catalog.json",
                       refresh=True, validator=C.not_html)
        if r.get("error"):
            raise SystemExit(f"manifest unavailable: {r['error']}")
    days = sorted(p.name for p in root.iterdir() if (p / "_catalog.json").exists()) if root.exists() else []
    if not days:
        raise SystemExit("no saved copies; run without --no-fetch")
    dest_root = root / days[-1]
    receipts = C.Receipts(days[-1], root=root)
    catalog = json.loads((dest_root / "_catalog.json").read_text(encoding="utf-8"))
    files, cell_rows = [], []
    for item in catalog["files"]:
        name = item["name"]
        mine = held.get(name)
        if not mine or mine.get("error"):
            continue
        if mine.get("catalog_mtime") == item.get("mtime") and mine.get("catalog_size") == item.get("size"):
            continue
        dest = dest_root / name
        if not a.no_fetch:
            is_matches = any(re.match(rx, name) for rx, branch, *_ in TML.RULES if branch == "matches")
            got = C.download(item["url"], dest, receipts, name=name,
                             validator=TML.MATCH_HEADER if is_matches else C.not_html,
                             extra={"catalog_mtime": item.get("mtime"), "catalog_size": item.get("size")})
            if got.get("error"):
                print(f"FAIL {name}: {got['error']}", flush=True)
                continue
        theirs = receipts.get(name) or {}
        row = {"file": name, "held_retrieved_at": mine.get("retrieved_at"), "held_mtime": mine.get("catalog_mtime"),
               "held_size": mine.get("catalog_size"), "held_sha256": mine.get("sha256"),
               "new_retrieved_at": theirs.get("retrieved_at"), "new_mtime": item.get("mtime"),
               "new_size": item.get("size"), "new_sha256": theirs.get("sha256")}
        old_path = HELD / name
        if dest.exists() and old_path.exists():
            stats, cells = diff(read_rows(old_path), read_rows(dest))
            row.update(stats)
            cell_rows += [{"file": name, "column": c, "cells": n} for c, n in cells.most_common()]
        files.append(row)
        print(f"{name}: {row.get('rows_old')} -> {row.get('rows_new')} rows; +{row.get('added')} "
              f"-{row.get('removed')} ~{row.get('corrected')}", flush=True)
    K.OUT.mkdir(parents=True, exist_ok=True)
    f = pd.DataFrame(files)
    f.to_csv(K.OUT / "tml_revisions_files.csv", index=False)
    pd.DataFrame(cell_rows, columns=["file", "column", "cells"]).to_csv(K.OUT / "tml_revisions_cells.csv", index=False)
    K.write_json(K.OUT / "tml_revisions.json", {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "held_copy": C.rel(HELD),
        "new_copies": C.rel(dest_root),
        "manifest_files": int(catalog.get("count", len(catalog["files"]))),
        "files_changed_since_held_copy": int(len(f)),
        "season_files_changed": [r["file"] for r in files if not r["file"].endswith("ongoing_tourneys.csv")
                                 and r["file"] != "ch_ongoing_tourney.csv"],
        "totals": {k: int(f[k].sum()) for k in ("added", "removed", "corrected") if k in f},
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
