"""Live Tennis API public sample on Zenodo (register PUB010): a 2023-2026 ATP/WTA/Challenger/ITF
match index (no winner or final score), a player table with a partial Sackmann crosswalk, and one
month (June 2026) of live-observed score states.

Source: https://zenodo.org/records/23018680, v1.0.2 of 28 Sep 2026 (CC BY-NC 4.0 sample; the full dataset is by
academic application only and is not requested here). MD5 checksums from the record are verified.

Versions. v1.0.0 (record 22048731, 21 Aug 2026) wrote ``scheduled_time_utc`` and the point sample's ``timestamp_utc``
in Israel local time, though the columns say UTC. v1.0.2 holds the same rows with those times in UTC (its notes: "The
timestamps in versions 1.0.0 and 1.0.1 were labelled UTC but were written in Israel local time"). ``--record`` picks
the version:
    * each record's files are kept side by side: v1.0.0's at the source's root, where they were first saved, and
      every other record's under record_<id>/;
    * the staged tables are rebuilt from the record asked for whenever they hold another one (a file whose MD5 is
      not the record's is never staged);
    * they carry _zenodo_record and _zenodo_version, and staged_time_zone() tells their readers which zone the
      times are written in.

Usage:
    ./python.sh -m src.ingest.public_dump.live_tennis_api_zenodo                    # v1.0.2
    ./python.sh -m src.ingest.public_dump.live_tennis_api_zenodo --record 22048731  # v1.0.0
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import common as C

SOURCE = "live_tennis_api_zenodo"
RECORD_ID = 23018680      # v1.0.2, 28 Sep 2026: times in UTC
FIRST_RECORD = 22048731   # v1.0.0, 21 Aug 2026: times in Israel local time; staged until 8 Oct 2026
RECORD_URL = "https://zenodo.org/api/records/{record}"
ISRAEL_TIME_VERSIONS = {"1.0.0", "1.0.1"}
BRANCH_FOR = {"matches.csv.gz": ("matches", "matches"), "players.csv.gz": ("players", "players"),
              "points_sample_2026-06.csv.gz": ("points", "points_sample_2026-06")}


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record_name(record: int, key: str) -> str:
    """A record's file as its receipt names it, and its path under the raw folder: v1.0.0's at the root, every other
    record's under record_<id>/."""
    return key if record == FIRST_RECORD else f"record_{record}/{key}"


def staged_version(path: Path) -> str:
    """The Zenodo version a staged table was built from: its _zenodo_version column, or 1.0.0 for a table staged before
    8 Oct 2026 (v1.0.0 was then the only version staged, and no table carried the column)."""
    if "_zenodo_version" not in pq.read_schema(path).names:
        return "1.0.0"
    versions = set(pq.read_table(path, columns=["_zenodo_version"]).column(0).unique().to_pylist())
    if len(versions) != 1:
        raise ValueError(f"{path} mixes Zenodo versions {sorted(map(str, versions))}")
    return versions.pop()


def staged_time_zone(path: Path) -> str:
    """The zone the times of a staged table (matches or points) are written in: Asia/Jerusalem for v1.0.0 and v1.0.1,
    UTC from v1.0.2."""
    return "Asia/Jerusalem" if staged_version(path) in ISRAEL_TIME_VERSIONS else "UTC"


def run(args) -> dict:
    record_id = int(getattr(args, "record", None) or RECORD_ID)
    receipts = C.Receipts(SOURCE)
    name = record_name(record_id, "_record.json")
    record_dest = C.raw_path(SOURCE, *name.split("/"))
    receipt = C.download(RECORD_URL.format(record=record_id), record_dest, receipts, name=name, refresh=True,
                         validator=C.not_html)
    if receipt.get("error"):
        raise RuntimeError(f"Zenodo record unavailable: {receipt['error']}")
    record = json.loads(record_dest.read_text(encoding="utf-8"))
    version = record.get("metadata", {}).get("version")
    C.log(f"[{SOURCE}] record {record_id} version {version}, {len(record['files'])} files")
    staged, mismatches = [], []
    for item in record["files"]:
        key = item["key"]
        name = record_name(record_id, key)
        dest = C.raw_path(SOURCE, *name.split("/"))
        validator = C.gzip_magic if key.endswith(".gz") else C.not_html
        receipt = C.download(item["links"]["self"], dest, receipts, name=name, refresh=args.refresh,
                             validator=validator, extra={"zenodo_record": record_id, "zenodo_version": version,
                                                         "zenodo_checksum": item.get("checksum")})
        if receipt.get("error"):
            C.log(f"[{SOURCE}] FAIL {key}: {receipt['error']}")
            continue
        expected = (item.get("checksum") or "").split(":", 1)
        checksum_ok = None
        if len(expected) == 2 and expected[0] == "md5":
            checksum_ok = md5_file(dest) == expected[1]
            if not checksum_ok:
                mismatches.append(name)
                C.log(f"[{SOURCE}] WARNING md5 mismatch for {name}; not staged")
                continue
        if key not in BRANCH_FOR:
            continue
        branch, stem = BRANCH_FOR[key]
        out = C.dump_path(branch, SOURCE, stem + ".parquet")
        same_record = (C.read_meta(out) or {}).get("zenodo_record") == record_id
        if out.exists() and receipt.get("skipped") and same_record and not args.refresh:
            continue
        meta = C.stage_csv_file(branch, SOURCE, receipt, dest, out,
                                extra_provenance={"_zenodo_record": record_id, "_zenodo_version": version},
                                zenodo_record=record_id, zenodo_version=version, checksum_ok=checksum_ok)
        staged.append(meta)
        C.log(f"[{SOURCE}] staged {meta['dest']} rows={meta['rows']} short={meta['short_rows']} long={meta['long_rows']}")
    summary = C.summarize(receipts, staged)
    summary.update(zenodo_record=record_id, zenodo_version=version, md5_mismatches=mismatches)
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--record", type=int, default=RECORD_ID,
                        help=f"Zenodo record id: {RECORD_ID} (v1.0.2, the default) or {FIRST_RECORD} (v1.0.0)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    C.log(f"[{SOURCE}] done: {summary['staged_files']} staged files, {summary['staged_rows']:,} rows, "
          f"{len(summary['errors'])} download errors, {len(summary['md5_mismatches'])} md5 mismatches")
    return 1 if summary["errors"] or summary["md5_mismatches"] else 0


if __name__ == "__main__":
    sys.exit(main())
