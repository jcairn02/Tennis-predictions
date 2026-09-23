"""Open Tennis Data v3 release assets (register PUB013): exact-date ATP/WTA main-tour singles results
with per-row source attribution, plus fixtures, players, tournaments, provenance, quarantine and
coverage tables.

This is a DERIVATIVE collection (every completed row cites tennis-data.co.uk, most also cite
Sackmann); it is staged for its exact match dates and source crosswalk, not as independent results.
Source: https://github.com/ryantjx/tennis-match-data releases (MIT software; data has source-specific
terms). The release tag defaults to the newest one; ``--otd-tag`` pins a specific release.
SHA256SUMS from the release are verified.

Usage:
    ./python.sh -m src.ingest.public_dump.open_tennis_data
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import common as C

SOURCE = "open_tennis_data"
REPO = "ryantjx/tennis-match-data"
RELEASES_URL = f"https://api.github.com/repos/{REPO}/releases?per_page=10"
DOC_URL = f"https://raw.githubusercontent.com/{REPO}/main/{{path}}"
DOCS = ["README.md", "DATA.md", "DATA_LICENSE.md", "docs/SCHEMA.md", "docs/SOURCES.md"]


def pick_release(releases, tag: str | None):
    candidates = [r for r in releases if not r.get("draft")]
    if tag:
        for release in candidates:
            if release["tag_name"] == tag:
                return release
        raise RuntimeError(f"release tag {tag} not among the {len(candidates)} newest releases")
    if not candidates:
        raise RuntimeError("no releases listed")
    return candidates[0]


def parse_sha256sums(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            out[parts[-1].lstrip("*")] = parts[0]
    return out


def run(args) -> dict:
    receipts = C.Receipts(SOURCE)
    releases_dest = C.raw_path(SOURCE, "_releases.json")
    receipt = C.download(RELEASES_URL, releases_dest, receipts, name="_releases.json", refresh=True, validator=C.not_html)
    if receipt.get("error"):
        raise RuntimeError(f"release listing unavailable: {receipt['error']}")
    releases = json.loads(releases_dest.read_text(encoding="utf-8"))
    release = pick_release(releases, getattr(args, "otd_tag", None))
    tag = release["tag_name"]
    C.log(f"[{SOURCE}] release {tag} published {release.get('published_at')} prerelease={release.get('prerelease')}")
    for doc in DOCS:
        C.download(DOC_URL.format(path=doc), C.raw_path(SOURCE, "docs", doc.replace("/", "_")), receipts,
                   name="docs/" + doc, refresh=args.refresh, validator=C.not_html)
    downloaded = {}
    for asset in release["assets"]:
        name = asset["name"]
        dest = C.raw_path(SOURCE, tag, name)
        receipt = C.download(asset["browser_download_url"], dest, receipts, name=f"{tag}/{name}",
                             refresh=args.refresh, validator=C.not_html, extra={"release_tag": tag})
        if receipt.get("error"):
            C.log(f"[{SOURCE}] FAIL {name}: {receipt['error']}")
            continue
        downloaded[name] = (dest, receipt)
    sums = {}
    if "SHA256SUMS" in downloaded:
        sums = parse_sha256sums(downloaded["SHA256SUMS"][0].read_text(encoding="utf-8"))
    staged = []
    for name, (dest, receipt) in downloaded.items():
        if not name.endswith(".parquet"):
            continue
        checksum_ok = (C.sha256_file(dest) == sums[name]) if name in sums else None
        if checksum_ok is False:
            C.log(f"[{SOURCE}] WARNING sha256 mismatch for {name}")
        branch = "players" if name == "players.parquet" else "matches"
        out = C.dump_path(branch, SOURCE, Path(name).stem + ".parquet")
        if out.exists() and receipt.get("skipped") and not args.refresh:
            continue
        prov = C.Provenance(SOURCE, C.rel(dest), receipt.get("sha256"), receipt.get("retrieved_at"),
                            {"_release_tag": tag})
        stats = C.stage_parquet_as_strings(dest, out, prov)
        meta = C.staged_meta(branch, SOURCE, out, receipt, stats, release_tag=tag, checksum_ok=checksum_ok,
                             derivative_of=["tennis-data.co.uk", "sackmann", "wikimedia"])
        staged.append(meta)
        C.log(f"[{SOURCE}] staged {meta['dest']} rows={meta['rows']}")
    summary = C.summarize(receipts, staged)
    summary["release_tag"] = tag
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--otd-tag", default=None, help="pin a release tag (default: newest release)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    C.log(f"[{SOURCE}] done: {summary['staged_files']} staged files, {summary['staged_rows']:,} rows, "
          f"{len(summary['errors'])} download errors")
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
