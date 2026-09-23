"""Match Charting Project raw files (register PUB005): shot-by-shot point logs, chart metadata and
per-match aggregate statistics for volunteer-charted ATP/WTA matches.

Source: https://github.com/JeffSackmann/tennis_MatchChartingProject (CC BY-NC-SA 4.0). Pinned to
the commit "thru 18 sep 2026"; pass ``--mcp-commit master`` to follow the branch. Points before
2010 are skipped unless ``--mcp-all-eras`` is set (recency priority); the aggregate stats files
cover every era and are always fetched.

Usage:
    ./python.sh -m src.ingest.public_dump.match_charting
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

SOURCE = "match_charting_project"
REPO = "JeffSackmann/tennis_MatchChartingProject"
PINNED_COMMIT = "1813a1309b7ed7ebf1c7e884b32bf675d00e4edf"  # "thru 18 sep 2026"
RAW_URL = "https://raw.githubusercontent.com/{repo}/{commit}/{path}"
TREE_URL = "https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1"
COMMIT_URL = "https://api.github.com/repos/{repo}/commits/{ref}"

CHART_HEADER = C.csv_header_contains("match_id")
RULES = [
    (r"^charting-(m|w)-matches\.csv$", "metadata", False),
    (r"^charting-(m|w)-points-(?:2020s|2010s)\.csv$", "points", False),
    (r"^charting-(m|w)-points-to-2009\.csv$", "points", True),
    (r"^charting-(m|w)-stats-\w+\.csv$", "stats", False),
]
DOCS = {"README.md", "data_dictionary.txt"}


def plan(tree_paths, all_eras: bool):
    selected, skipped = [], []
    for path in tree_paths:
        if path in DOCS:
            selected.append(("docs", path))
            continue
        for regex, subdir, old_era in RULES:
            if re.match(regex, path):
                if old_era and not all_eras:
                    skipped.append({"path": path, "reason": "points before 2010; pass --mcp-all-eras to include"})
                else:
                    selected.append((subdir, path))
                break
        else:
            skipped.append({"path": path, "reason": "charting tool or repository housekeeping"})
    return selected, skipped


def resolve_commit(ref: str) -> str:
    if re.fullmatch(r"[0-9a-f]{40}", ref):
        return ref
    return C.fetch_json(COMMIT_URL.format(repo=REPO, ref=ref))["sha"]


def run(args) -> dict:
    receipts = C.Receipts(SOURCE)
    commit = resolve_commit(getattr(args, "mcp_commit", PINNED_COMMIT) or PINNED_COMMIT)
    C.log(f"[{SOURCE}] commit {commit}")
    tree_dest = C.raw_path(SOURCE, f"_tree_{commit[:12]}.json")
    receipt = C.download(TREE_URL.format(repo=REPO, commit=commit), tree_dest, receipts,
                         name=f"_tree_{commit[:12]}.json", refresh=args.refresh, validator=C.not_html)
    if receipt.get("error"):
        raise RuntimeError(f"could not list repository tree: {receipt['error']}")
    tree = json.loads(tree_dest.read_text(encoding="utf-8"))
    paths = [item["path"] for item in tree["tree"] if item["type"] == "blob"]
    selected, skipped = plan(paths, getattr(args, "mcp_all_eras", False))
    C.log(f"[{SOURCE}] {len(selected)} files planned, {len(skipped)} skipped")
    staged = []
    for subdir, path in selected:
        url = RAW_URL.format(repo=REPO, commit=commit, path=path)
        dest = C.raw_path(SOURCE, path)
        validator = C.not_html if subdir == "docs" else CHART_HEADER
        receipt = C.download(url, dest, receipts, name=path, refresh=args.refresh, validator=validator,
                             extra={"commit": commit})
        if receipt.get("error"):
            C.log(f"[{SOURCE}] FAIL {path}: {receipt['error']}")
            continue
        if subdir == "docs":
            continue
        out = C.dump_path("points", SOURCE, subdir, Path(path).stem + ".parquet")
        if out.exists() and receipt.get("skipped") and not args.refresh:
            continue
        meta = C.stage_csv_file("points", SOURCE, receipt, dest, out, commit=commit, repository_path=path)
        staged.append(meta)
        C.log(f"[{SOURCE}] staged {meta['dest']} rows={meta['rows']} short={meta['short_rows']} long={meta['long_rows']}")
    summary = C.summarize(receipts, staged, skipped)
    summary["commit"] = commit
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--mcp-commit", default=PINNED_COMMIT, help="commit sha or branch name")
    parser.add_argument("--mcp-all-eras", action="store_true", help="also fetch points charted before 2010")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    C.log(f"[{SOURCE}] done: {summary['staged_files']} staged files, {summary['staged_rows']:,} rows, "
          f"{len(summary['errors'])} download errors")
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
