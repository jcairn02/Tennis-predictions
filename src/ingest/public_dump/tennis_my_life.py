"""Tennis My Life current downloads (register PUB049): ATP main tour, Challenger, ATP qualifying,
WTA main tour season files, ongoing-tournament files, the ATP player database and a rankings file.

Source: https://stats.tennismylife.org/tennis-match-database with the public file manifest at
https://stats.tennismylife.org/api/data-files. Rights are unresolved: the website labels the
dataset MIT while the publisher's GitHub README says noncommercial unless permitted.

Season files are re-downloaded only when the manifest's mtime/size changes; ongoing files are
always refreshed because they change daily.

Usage:
    ./python.sh -m src.ingest.public_dump.tennis_my_life --start-year 2010
"""
from __future__ import annotations

import argparse
import json
import re
import sys
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


def run(args) -> dict:
    receipts = C.Receipts(SOURCE)
    catalog_dest = C.raw_path(SOURCE, "_catalog.json")
    receipt = C.download(CATALOG_URL, catalog_dest, receipts, name="_catalog.json", refresh=True,
                         validator=C.not_html)
    if receipt.get("error"):
        raise RuntimeError(f"Tennis My Life manifest unavailable: {receipt['error']}")
    catalog = json.loads(catalog_dest.read_text(encoding="utf-8"))
    C.download(README_URL, C.raw_path(SOURCE, "docs", "TML-Database_README.md"), receipts,
               name="docs/TML-Database_README.md", refresh=args.refresh, validator=C.not_html)
    selected, skipped = plan(catalog["files"], args.start_year, args.end_year)
    C.log(f"[{SOURCE}] catalog lists {catalog['count']} files; {len(selected)} planned, {len(skipped)} skipped")
    staged = []
    for branch, subdir, item, validator, always in selected:
        name = item["name"]
        dest = C.raw_path(SOURCE, name)
        previous = receipts.get(name)
        unchanged = (previous and not previous.get("error") and dest.exists()
                     and previous.get("catalog_mtime") == item.get("mtime")
                     and previous.get("catalog_size") == item.get("size"))
        refresh = args.refresh or always or not unchanged
        receipt = C.download(item["url"], dest, receipts, name=name, refresh=refresh, validator=validator,
                             extra={"catalog_mtime": item.get("mtime"), "catalog_size": item.get("size")})
        if receipt.get("error"):
            C.log(f"[{SOURCE}] FAIL {name}: {receipt['error']}")
            continue
        out = C.dump_path(branch, SOURCE, subdir, Path(name).stem + ".parquet")
        if out.exists() and receipt.get("skipped") and not args.refresh:
            continue
        meta = C.stage_csv_file(branch, SOURCE, receipt, dest, out, catalog_name=name,
                                catalog_mtime=item.get("mtime"), catalog_size=item.get("size"))
        staged.append(meta)
        C.log(f"[{SOURCE}] staged {meta['dest']} rows={meta['rows']} short={meta['short_rows']} long={meta['long_rows']}")
    return C.summarize(receipts, staged, skipped)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--start-year", type=int, default=C.DEFAULT_START_YEAR)
    parser.add_argument("--end-year", type=int, default=C.DEFAULT_END_YEAR)
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
