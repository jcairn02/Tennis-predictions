"""Tennis My Life current downloads (register PUB049): ATP main tour, Challenger, ATP qualifying,
WTA main tour season files, ongoing-tournament files, the ATP player database and a rankings file.

Source: https://stats.tennismylife.org/tennis-match-database with the public file manifest at
https://stats.tennismylife.org/api/data-files. Rights are unresolved: the website labels the
dataset MIT while the publisher's GitHub README says noncommercial unless permitted.

Season files are re-downloaded when the manifest's mtime/size changes (or the copy held is not the size the
manifest lists); ongoing files are always refreshed because they change daily. Since Sackmann's end, Stage 0
takes every new result from these files, and TML rewrites them in place (it corrected a 2024 score on 5 Oct
2026). So, agreed in docs/studies/data_continuity/ (6 Oct 2026):

* Nothing is lost. A re-download that brings different bytes keeps the replaced file first, under
  superseded/ with its receipts (common.keep_replaced). --no-keep-superseded turns that off.
* A damaged file never becomes current. A season file is held when its last record is ragged (a
  half-written file), when it is not the size the manifest lists (TML was rewriting it), when a column is
  lost, or when more than 5 rows, or more than half the rows, of the current copy are gone once corrections
  are paired with the rows they correct. An ongoing file is held only when ragged or a column is lost. A held file is kept under held/
  with the reason, the current copy stays, staging uses the current copy, and the run exits non-zero. After
  review, --accept-held NAME@SHA12 lets that exact version through on the next run.
* Every accepted revision of a season file appends its rows added, removed and corrected, and the changed
  columns, to _changes.jsonl.
* One run at a time: a .lock file younger than an hour stops a second run.

Usage:
    ./python.sh -m src.ingest.public_dump.tennis_my_life --start-year 2010
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import common as C

SOURCE = "tennis_my_life"
CATALOG_URL = "https://stats.tennismylife.org/api/data-files"
PAGE_URL = "https://stats.tennismylife.org/tennis-match-database"
README_URL = "https://raw.githubusercontent.com/Tennismylife/TML-Database/master/README.md"

MATCH_HEADER = C.csv_header_contains("tourney_id")
RULES = [
    # regex on catalog name, branch, subdir, validator, has_year, always_refresh
    (r"^(\d{4})\.csv$", "matches", "atp_main", MATCH_HEADER, True, False),
    (r"^(\d{4})_challenger\.csv$", "matches", "atp_challenger", MATCH_HEADER, True, False),
    (r"^(\d{4})_wta\.csv$", "matches", "wta_main", MATCH_HEADER, True, False),
    (r"^atp_quali/(\d{4})_atp_quali\.csv$", "matches", "atp_qualifying", MATCH_HEADER, True, False),
    (r"^(?:ongoing_tourneys|wta_ongoing_tourneys|challenger_ongoing_tourneys|ch_ongoing_tourney)\.csv$",
     "matches", "ongoing", MATCH_HEADER, False, True),
    (r"^ATP_Database\.csv$", "players", "", C.csv_header_contains("player"), False, True),
    (r"^atp_rankings_.*\.csv$", "rankings", "", C.csv_header_contains("rank"), False, False),
]
SKIP_RULES = [
    (r"^backup_ll_audit_", "publisher backup copy of the same season files (duplicate)"),
    (r"^atp_matches_amateur\.csv$", "amateur-era results (from 1877); outside the recency priority"),
]
SEASON = re.compile(r"^(?:atp_quali/)?\d{4}(?:_challenger|_wta|_atp_quali)?\.csv$")
ONGOING = re.compile(r"ongoing_tourney")
GATE_MAX_REMOVED = 5          # rows of the current copy that may vanish (TML removes the odd duplicate)
LOCK_MAX_AGE = 3600           # seconds after which a lock is taken to be left by a dead run
ID_KEY = ["tourney_id", "tourney_date", "round", "winner_id", "loser_id"]
NAME_KEY = ["tourney_id", "round", "winner_name", "loser_name"]


def default_end_year() -> int:
    """This year and the next: TML's next season file appears in late December (its 2025 file starts with matches
    of 29 Dec 2024)."""
    return dt.datetime.now(dt.timezone.utc).year + 1


def plan(catalog_files, start: int, end: int):
    selected, skipped = [], []
    for item in catalog_files:
        name = item["name"]
        reason = next((why for regex, why in SKIP_RULES if re.match(regex, name)), None)
        if reason:
            skipped.append({"path": name, "reason": reason})
            continue
        for regex, branch, subdir, validator, has_year, always in RULES:
            match = re.match(regex, name)
            if not match:
                continue
            if has_year:
                year = int(match.group(1))
                if not start <= year <= end:
                    skipped.append({"path": name, "reason": f"year {year} outside {start}-{end}"})
                    break
            selected.append((branch, subdir, item, validator, always))
            break
        else:
            skipped.append({"path": name, "reason": "no rule matches this catalog entry"})
    return selected, skipped


# ------------------------------------------------------------------------------------------------
# The gate: a damaged file never becomes current

def read_rows(data: bytes) -> tuple[list[str], list[tuple[str, ...]], bool]:
    """Header, data records, and whether the last record is ragged (fewer fields than the header)."""
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    reader = csv.reader(io.StringIO(text))
    header = next(reader, [])
    rows = [tuple(r) for r in reader if r]
    return header, rows, bool(rows) and len(rows[-1]) < len(header)


def row_changes(old_header: list[str], old_rows: list[tuple], new_header: list[str], new_rows: list[tuple]) -> dict:
    """Rows added, removed and corrected between two versions of a file, and the changed cells per column.

    Rows are compared whole, so line endings and quoting do not count. A vanished row and a new row are a
    correction when they share a match identity: first tournament id and date, round and both player ids (where
    both ids are given), then tournament id, round and both names (TML fills in blank ids later)."""
    cols = list(dict.fromkeys(list(old_header) + list(new_header)))

    def align(header, rows):
        idx = [header.index(c) if c in header else None for c in cols]
        return [tuple(r[i] if i is not None and i < len(r) else "" for i in idx) for r in rows]

    old, new = Counter(align(old_header, old_rows)), Counter(align(new_header, new_rows))
    gone, came = list((old - new).elements()), list((new - old).elements())
    corrected, cells = 0, Counter()
    for key, need in ((ID_KEY, ("winner_id", "loser_id")), (NAME_KEY, ("winner_name", "loser_name"))):
        ki = [cols.index(k) for k in key if k in cols]
        ni = [cols.index(k) for k in need if k in cols]
        if len(ki) < len(key):
            continue
        pool: dict[tuple, list] = {}
        for row in came:
            if all(row[i] for i in ni):
                pool.setdefault(tuple(row[i] for i in ki), []).append(row)
        left = []
        for row in gone:
            twins = pool.get(tuple(row[i] for i in ki)) if all(row[i] for i in ni) else None
            if twins:
                twin = twins.pop()
                came.remove(twin)
                corrected += 1
                cells.update(c for j, c in enumerate(cols) if row[j] != twin[j])
            else:
                left.append(row)
        gone = left
    return {"rows_old": len(old_rows), "rows_new": len(new_rows), "added": len(came), "removed": len(gone),
            "corrected": corrected, "cells": dict(cells.most_common())}


def make_gate(name: str, dest: Path, item: dict, accept: set[str], changes: dict):
    """The gate for one catalog file (common.download's ``gate``): a reason to hold the new bytes, or None."""
    season, ongoing = bool(SEASON.match(name)), bool(ONGOING.search(name))

    def gate(body: bytes):
        if f"{name}@{C.sha256_bytes(body)[:12]}" in accept:
            changes[name] = {"accepted_after_review": True}
            return None
        if not (season or ongoing):
            return None
        header, rows, ragged = read_rows(body)
        if ragged:
            return "its last record has fewer fields than the header (a half-written file)"
        if season and item.get("size") is not None and len(body) != item["size"]:
            return f"received {len(body):,} bytes where the manifest lists {item['size']:,} (a file being rewritten)"
        if not dest.exists():
            return None
        old_header, old_rows, _ = read_rows(dest.read_bytes())
        lost = [c for c in old_header if c not in header]
        if lost:
            return f"columns lost: {', '.join(lost)}"
        if season:
            diff = row_changes(old_header, old_rows, header, rows)
            if diff["removed"] > GATE_MAX_REMOVED:
                return f"{diff['removed']} rows of the current copy are gone (more than {GATE_MAX_REMOVED})"
            if diff["removed"] and diff["removed"] * 2 > len(old_rows):
                return f"{diff['removed']} of the current copy's {len(old_rows)} rows are gone (more than half)"
            changes[name] = diff
        return None

    return gate


def take_lock(path: Path) -> None:
    if path.exists():
        age = time.time() - path.stat().st_mtime
        if age < LOCK_MAX_AGE:
            raise RuntimeError(f"another Tennis My Life run holds {C.rel(path)} (started {age / 60:.0f} minutes ago); "
                               "wait for it, or delete the file if that run has died")
        path.unlink()                    # left by a run that died more than an hour ago
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps({"pid": os.getpid(), "started_at": C.utc_now_iso()}))


# ------------------------------------------------------------------------------------------------

def run(args) -> dict:
    lock = C.raw_path(SOURCE, ".lock")
    take_lock(lock)
    try:
        return _run(args)
    finally:
        lock.unlink(missing_ok=True)


def _run(args) -> dict:
    receipts = C.Receipts(SOURCE)
    keep = not getattr(args, "no_keep_superseded", False)
    accept = set(getattr(args, "accept_held", None) or [])
    catalog_dest = C.raw_path(SOURCE, "_catalog.json")
    receipt = C.download(CATALOG_URL, catalog_dest, receipts, name="_catalog.json", refresh=True,
                         validator=C.not_html, keep_superseded=keep)
    if receipt.get("error"):
        raise RuntimeError(f"Tennis My Life manifest unavailable: {receipt['error']}")
    catalog = json.loads(catalog_dest.read_text(encoding="utf-8"))
    C.download(README_URL, C.raw_path(SOURCE, "docs", "TML-Database_README.md"), receipts,
               name="docs/TML-Database_README.md", refresh=args.refresh, validator=C.not_html, keep_superseded=keep)
    selected, skipped = plan(catalog["files"], args.start_year, args.end_year)
    C.log(f"[{SOURCE}] catalog lists {catalog['count']} files; {len(selected)} planned, {len(skipped)} skipped")
    staged, held, changes = [], [], {}
    for branch, subdir, item, validator, always in selected:
        name = item["name"]
        dest = C.raw_path(SOURCE, name)
        previous = receipts.get(name)
        unchanged = (previous and not previous.get("error") and dest.exists()
                     and previous.get("catalog_mtime") == item.get("mtime")
                     and previous.get("catalog_size") == item.get("size")
                     and previous.get("bytes") == item.get("size"))
        refresh = args.refresh or always or not unchanged
        receipt = C.download(item["url"], dest, receipts, name=name, refresh=refresh, validator=validator,
                             extra={"catalog_mtime": item.get("mtime"), "catalog_size": item.get("size")},
                             keep_superseded=keep, gate=make_gate(name, dest, item, accept, changes))
        if receipt.get("held"):
            held.append({"name": name, "reason": receipt["held"], "kept_as": receipt["dest"],
                         "accept_with": f"--accept-held {name}@{receipt['sha256'][:12]}"})
            C.log(f"[{SOURCE}] HELD {name}: {receipt['held']}; kept as {receipt['dest']}, the current copy stays")
            continue
        if receipt.get("superseded") and not receipt.get("skipped"):   # a skipped file returns its last receipt
            C.log(f"[{SOURCE}] {name} changed; kept the replaced file as {receipt['superseded']}")
        if receipt.get("error"):
            C.log(f"[{SOURCE}] FAIL {name}: {receipt['error']}")
            continue
        diff = changes.get(name)
        if diff and not receipt.get("skipped") and (diff.get("added") or diff.get("removed") or diff.get("corrected")
                                                    or diff.get("accepted_after_review")):
            line = {"name": name, "retrieved_at": receipt.get("retrieved_at"), "sha256": receipt.get("sha256"),
                    "previous_sha256": (previous or {}).get("sha256"), "superseded": receipt.get("superseded"), **diff}
            with C.raw_path(SOURCE, "_changes.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(line, ensure_ascii=False) + "\n")
        out = C.dump_path(branch, SOURCE, subdir, Path(name).stem + ".parquet")
        if out.exists() and receipt.get("skipped") and not args.refresh:
            continue
        meta = C.stage_csv_file(branch, SOURCE, receipt, dest, out, catalog_name=name,
                                catalog_mtime=item.get("mtime"), catalog_size=item.get("size"))
        staged.append(meta)
        C.log(f"[{SOURCE}] staged {meta['dest']} rows={meta['rows']} short={meta['short_rows']} long={meta['long_rows']}")
    summary = C.summarize(receipts, staged, skipped)
    summary["held"] = held
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--start-year", type=int, default=C.DEFAULT_START_YEAR)
    parser.add_argument("--end-year", type=int, default=default_end_year(),
                        help="last season file to fetch (default: next year, so a season file published in "
                             "December is not missed)")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--no-keep-superseded", action="store_true",
                        help="overwrite changed files without keeping the replaced bytes")
    parser.add_argument("--accept-held", action="append", default=[], metavar="NAME@SHA12",
                        help="after review, let this held version through (repeatable)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    C.log(f"[{SOURCE}] done: {summary['staged_files']} staged files, {summary['staged_rows']:,} rows, "
          f"{len(summary['errors'])} download errors, {len(summary['held'])} held")
    for h in summary["held"]:
        C.log(f"[{SOURCE}] held {h['name']}: {h['reason']}. To accept it after review: {h['accept_with']}")
    return 1 if summary["errors"] or summary["held"] else 0


if __name__ == "__main__":
    sys.exit(main())
