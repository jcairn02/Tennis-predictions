"""Live Tennis API public sample on Zenodo (register PUB010): a 2023-2026 ATP/WTA/Challenger/ITF
match index (no winner or final score), a player table with a partial Sackmann crosswalk, and one
month (June 2026) of live-observed score states.

Source: https://zenodo.org/records/22048731 (CC BY-NC 4.0 sample; the full dataset is by academic
application only and is not requested here). MD5 checksums from the record are verified.

Usage:
    ./python.sh -m src.ingest.public_dump.live_tennis_api_zenodo
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import common as C

SOURCE = "live_tennis_api_zenodo"
RECORD_ID = 22048731
RECORD_URL = f"https://zenodo.org/api/records/{RECORD_ID}"
BRANCH_FOR = {"matches.csv.gz": ("matches", "matches"), "players.csv.gz": ("players", "players"),
              "points_sample_2026-06.csv.gz": ("points", "points_sample_2026-06")}


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(args) -> dict:
    receipts = C.Receipts(SOURCE)
    record_dest = C.raw_path(SOURCE, "_record.json")
    receipt = C.download(RECORD_URL, record_dest, receipts, name="_record.json", refresh=True, validator=C.not_html)
    if receipt.get("error"):
        raise RuntimeError(f"Zenodo record unavailable: {receipt['error']}")
    record = json.loads(record_dest.read_text(encoding="utf-8"))
    version = record.get("metadata", {}).get("version")
    C.log(f"[{SOURCE}] record {RECORD_ID} version {version}, {len(record['files'])} files")
    staged = []
    for item in record["files"]:
        key = item["key"]
        dest = C.raw_path(SOURCE, key)
        validator = C.gzip_magic if key.endswith(".gz") else C.not_html
        receipt = C.download(item["links"]["self"], dest, receipts, name=key, refresh=args.refresh,
                             validator=validator, extra={"zenodo_version": version, "zenodo_checksum": item.get("checksum")})
        if receipt.get("error"):
            C.log(f"[{SOURCE}] FAIL {key}: {receipt['error']}")
            continue
        expected = (item.get("checksum") or "").split(":", 1)
        checksum_ok = None
        if len(expected) == 2 and expected[0] == "md5":
            checksum_ok = md5_file(dest) == expected[1]
            if not checksum_ok:
                C.log(f"[{SOURCE}] WARNING md5 mismatch for {key}")
        if key not in BRANCH_FOR:
            continue
        branch, stem = BRANCH_FOR[key]
        out = C.dump_path(branch, SOURCE, stem + ".parquet")
        if out.exists() and receipt.get("skipped") and not args.refresh:
            continue
        meta = C.stage_csv_file(branch, SOURCE, receipt, dest, out, zenodo_record=RECORD_ID,
                                zenodo_version=version, checksum_ok=checksum_ok)
        staged.append(meta)
        C.log(f"[{SOURCE}] staged {meta['dest']} rows={meta['rows']} short={meta['short_rows']} long={meta['long_rows']}")
    summary = C.summarize(receipts, staged)
    summary["zenodo_version"] = version
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--refresh", action="store_true")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    C.log(f"[{SOURCE}] done: {summary['staged_files']} staged files, {summary['staged_rows']:,} rows, "
          f"{len(summary['errors'])} download errors")
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
