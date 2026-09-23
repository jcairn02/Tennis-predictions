"""Sackmann archival mirror (register PUB003): ATP/WTA results with serve statistics, rankings,
player tables, tour-level doubles (2000-2020) and Grand Slam point-by-point files (2011-2024).

Source: https://github.com/Aneeshers/tennis-sackmann-archive (CC BY-NC-SA 4.0, an archival copy of
Jeff Sackmann's repositories, whose original addresses returned 404 on 10 and 22 Sep 2026).
Pinned to the 2026-06-25 snapshot commit; pass ``--sackmann-commit main`` to follow the branch.

Usage:
    ./python.sh -m src.ingest.public_dump.sackmann_archive --start-year 2010
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import common as C

SOURCE = "sackmann_archive"
REPO = "Aneeshers/tennis-sackmann-archive"
PINNED_COMMIT = "83733587353df8a41f2fd4f516147d5aa83f5a8d"  # "Archive of Jeff Sackmann tennis datasets", 2026-06-25
RAW_URL = "https://raw.githubusercontent.com/{repo}/{commit}/{path}"
TREE_URL = "https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1"
COMMIT_URL = "https://api.github.com/repos/{repo}/commits/{ref}"

MATCH_HEADER = C.csv_header_contains("tourney_id")
RULES = [
    # regex, branch, subdir, validator, year mode ("year" | "decade" | None)
    (r"^atp/atp_matches_(\d{4})\.csv$", "matches", "atp", MATCH_HEADER, "year"),
    (r"^atp/atp_matches_qual_chall_(\d{4})\.csv$", "matches", "atp", MATCH_HEADER, "year"),
    (r"^atp/atp_matches_futures_(\d{4})\.csv$", "matches", "atp", MATCH_HEADER, "year"),
    (r"^atp/atp_matches_doubles_(\d{4})\.csv$", "matches", "atp", MATCH_HEADER, "year"),
    (r"^atp/atp_players\.csv$", "players", "atp", C.csv_header_contains("player_id"), None),
    (r"^atp/atp_rankings_(\d{2})s\.csv$", "rankings", "atp", C.csv_header_contains("ranking_date"), "decade"),
    (r"^atp/atp_rankings_current\.csv$", "rankings", "atp", C.csv_header_contains("ranking_date"), None),
    (r"^wta/wta_matches_(\d{4})\.csv$", "matches", "wta", MATCH_HEADER, "year"),
    (r"^wta/wta_matches_qual_itf_(\d{4})\.csv$", "matches", "wta", MATCH_HEADER, "year"),
    (r"^wta/wta_players\.csv$", "players", "wta", C.csv_header_contains("player_id"), None),
    (r"^wta/wta_rankings_(\d{2})s\.csv$", "rankings", "wta", C.csv_header_contains("ranking_date"), "decade"),
    (r"^wta/wta_rankings_current\.csv$", "rankings", "wta", C.csv_header_contains("ranking_date"), None),
    (r"^slam_pointbypoint/(\d{4})-[a-z]+-(?:matches|points)(?:-doubles|-mixed)?\.csv$", "points",
     "slam_pointbypoint", C.csv_header_contains("match_id"), "year"),
]
DOCS = {"README.md", "LICENSE", "atp/UPSTREAM_README.md", "atp/matches_data_dictionary.txt",
        "wta/UPSTREAM_README.md", "slam_pointbypoint/UPSTREAM_README.md", "slam_pointbypoint/data_dictionary.txt"}
SKIP = {"atp/atp_matches_amateur.csv": "pre-Open-era amateur results; outside the recency priority",
        ".gitignore": "repository housekeeping"}


def decade_start(two_digits: str) -> int:
    value = int(two_digits)
    return 1900 + value if value >= 60 else 2000 + value


def plan(tree_paths, start: int, end: int, include_slam: bool = True, include_doubles: bool = True):
    """Split archive paths into (selected, skipped). ``selected`` items are
    (branch, subdir, path, validator); docs use branch "docs"."""
    selected, skipped = [], []
    for path in tree_paths:
        if path in DOCS:
            selected.append(("docs", "", path, C.not_html))
            continue
        if path in SKIP:
            skipped.append({"path": path, "reason": SKIP[path]})
            continue
        decision = None
        for regex, branch, subdir, validator, year_mode in RULES:
            match = re.match(regex, path)
            if not match:
                continue
            if year_mode == "year":
                year = int(match.group(1))
                if not start <= year <= end:
                    decision = {"path": path, "reason": f"year {year} outside {start}-{end}"}
                elif "doubles" in path and not include_doubles:
                    decision = {"path": path, "reason": "doubles excluded by flag"}
                elif branch == "points" and not include_slam:
                    decision = {"path": path, "reason": "slam point-by-point excluded by flag"}
            elif year_mode == "decade":
                first = decade_start(match.group(1))
                if first + 9 < start or first > end:
                    decision = {"path": path, "reason": f"ranking decade {first}s outside {start}-{end}"}
            if decision is None:
                decision = (branch, subdir, path, validator)
            break
        if decision is None:
            skipped.append({"path": path, "reason": "no rule matches this path"})
        elif isinstance(decision, dict):
            skipped.append(decision)
        else:
            selected.append(decision)
    return selected, skipped


def resolve_commit(ref: str) -> str:
    if re.fullmatch(r"[0-9a-f]{40}", ref):
        return ref
    return C.fetch_json(COMMIT_URL.format(repo=REPO, ref=ref))["sha"]


def load_tree(commit: str, receipts: C.Receipts, refresh: bool) -> list[str]:
    dest = C.raw_path(SOURCE, f"_tree_{commit[:12]}.json")
    receipt = C.download(TREE_URL.format(repo=REPO, commit=commit), dest, receipts,
                         name=f"_tree_{commit[:12]}.json", refresh=refresh, validator=C.not_html)
    if receipt.get("error"):
        raise RuntimeError(f"could not list archive tree: {receipt['error']}")
    import json

    tree = json.loads(dest.read_text(encoding="utf-8"))
    if tree.get("truncated"):
        raise RuntimeError("GitHub returned a truncated tree; the plan would be incomplete")
    return [item["path"] for item in tree["tree"] if item["type"] == "blob"]


def run(args) -> dict:
    receipts = C.Receipts(SOURCE)
    commit = resolve_commit(getattr(args, "sackmann_commit", PINNED_COMMIT) or PINNED_COMMIT)
    C.log(f"[{SOURCE}] commit {commit}")
    paths = load_tree(commit, receipts, args.refresh)
    selected, skipped = plan(paths, args.start_year, args.end_year,
                             include_slam=not getattr(args, "no_slam", False),
                             include_doubles=not getattr(args, "no_doubles", False))
    C.log(f"[{SOURCE}] {len(selected)} files planned, {len(skipped)} skipped")
    staged = []
    for branch, subdir, path, validator in selected:
        url = RAW_URL.format(repo=REPO, commit=commit, path=path)
        dest = C.raw_path(SOURCE, path)
        receipt = C.download(url, dest, receipts, name=path, refresh=args.refresh, validator=validator,
                             extra={"commit": commit})
        if receipt.get("error"):
            C.log(f"[{SOURCE}] FAIL {path}: {receipt['error']}")
            continue
        if branch == "docs":
            continue
        out = C.dump_path(branch, SOURCE, subdir, Path(path).stem + ".parquet")
        if out.exists() and receipt.get("skipped") and not args.refresh:
            continue
        meta = C.stage_csv_file(branch, SOURCE, receipt, dest, out, commit=commit, archive_path=path)
        staged.append(meta)
        C.log(f"[{SOURCE}] staged {meta['dest']} rows={meta['rows']} short={meta['short_rows']} long={meta['long_rows']}")
    summary = C.summarize(receipts, staged, skipped)
    summary["commit"] = commit
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--start-year", type=int, default=C.DEFAULT_START_YEAR)
    parser.add_argument("--end-year", type=int, default=C.DEFAULT_END_YEAR)
    parser.add_argument("--refresh", action="store_true", help="re-download and re-stage existing files")
    parser.add_argument("--sackmann-commit", default=PINNED_COMMIT, help="commit sha or branch name")
    parser.add_argument("--no-slam", action="store_true", help="skip Grand Slam point-by-point files")
    parser.add_argument("--no-doubles", action="store_true", help="skip ATP doubles files")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    C.log(f"[{SOURCE}] done: {summary['staged_files']} staged files, {summary['staged_rows']:,} rows, "
          f"{len(summary['errors'])} download errors")
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
