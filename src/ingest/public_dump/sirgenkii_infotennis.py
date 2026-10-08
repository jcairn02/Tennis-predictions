"""SirGenkii/infotennis: the ATP's Stats Centre data for the 2025 season to 7 April 2025, as MySQL dumps.

Source: GitHub SirGenkii/infotennis, a fork of glad94/infotennis (code MIT; the data has no licence),
pinned to its head commit ec1b188 (11 Apr 2025, still the head on 29 Sep 2026). Its backup_sql/ folder
(commit 1bb7527, 7 Apr 2025) holds six MySQL 8.0.41 dumps of the database ``infotennis4``, which the
fork's scrapers filled from the ATP's Stats Centre (Infosys) match files: 1,294 matches of 23 events, from
the United Cup and Brisbane (27 Dec 2024) to the first days of Monte-Carlo 2025. 922 have every point, each
with how it ended (winner, forced or unforced error, ace, double fault), the serve number and, at some
events, the serve speed; there are also per-set key statistics, stroke summaries and Court Vision ball
tracking for 6 matches. What it adds to the data map's ATP tour-level gap was measured on 29 Sep 2026:
docs/research/gap-sources/README.md and
data/studies/gap_sources/research_notes/B_tour_pbp_datasets_and_sackmann.md (lane B2).

Like the Hugging Face handoff (docs/decisions/2026-09-25-atp-pipeline-handoff.md), this is a third
party's decrypted copy of ATP data. The project decrypts nothing.

Raw (data/raw/public_dump/sirgenkii_infotennis/, gitignored): the dumps, the README, licence, config,
player table and API notes at the repository's own paths, each checked against the pinned tree's git
blob SHA-1, plus _tree_<sha12>.json and _receipts.jsonl.
Staged (data/dump/points/sirgenkii_infotennis/<table>.parquet): every row of each dump, in the table's
column order, as strings exactly as dumped (MySQL NULL becomes null; escapes are undone), with the
dump's provenance columns and a .meta.json sidecar.
Summary: data/studies/gap_downloads/sirgenkii_summary.json.

Usage:
    ./python.sh -m src.ingest.public_dump.sirgenkii_infotennis
    ./python.sh -m src.ingest.public_dump.sirgenkii_infotennis --stage-only   # no HTTP
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import common as C

SOURCE = "sirgenkii_infotennis"
REPO = "SirGenkii/infotennis"
PINNED_COMMIT = "ec1b188f30e9bccc6923ed084b0db99e0e472917"  # head since 11 Apr 2025; dumps from 1bb7527 (7 Apr 2025)
RAW_URL = "https://raw.githubusercontent.com/{repo}/{commit}/{path}"
TREE_URL = "https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1"
STUDY = C.PROJECT_ROOT / "data" / "studies" / "gap_downloads"
WANTED = re.compile(r"^(backup_sql/.+\.sql|references/api-info/.+\.json|README\.md|LICENSE|config\.yaml"
                    r"|data/players_ATP\.csv)$")
DUMP_NAME = re.compile(r"^backup_sql/infotennis4_(atp_\w+)\.sql$")
_ESCAPES = {"0": "\0", "b": "\b", "n": "\n", "r": "\r", "t": "\t", "Z": "\x1a"}
_VALUE = re.compile(r"'((?:[^'\\]|\\.)*)'|([^,()']+)|([(),])", re.S)


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


# --------------------------------------------------------------------------------------
# MySQL dump reading (pure functions; tested offline)
# --------------------------------------------------------------------------------------
def unescape(text: str) -> str:
    """A quoted MySQL string's content with its backslash escapes undone."""
    return re.sub(r"\\(.)", lambda m: _ESCAPES.get(m.group(1), m.group(1)), text, flags=re.S)


def table_columns(text: str, table: str) -> list[str]:
    """Column names of ``CREATE TABLE `table``` in dump order."""
    m = re.search(r"CREATE TABLE `%s` \((.*?)\n\) ENGINE" % re.escape(table), text, re.S)
    if m is None:
        raise ValueError(f"no CREATE TABLE for {table}")
    return [line.strip().split("`")[1] for line in m.group(1).splitlines() if line.strip().startswith("`")]


def value_rows(values: str):
    """Rows of a VALUES list ``(1,'a\\'b',NULL,2.5),(...)`` as lists of strings (NULL -> None). Unquoted
    values keep their dumped text: numbers are not converted."""
    row = None
    for quoted, bare, punct in (m.groups() for m in _VALUE.finditer(values)):
        if punct == "(":
            row = []
        elif punct == ")":
            if row is not None:
                yield row
            row = None
        elif punct == ",":
            continue
        elif row is not None:
            if quoted is not None:
                row.append(unescape(quoted))
            else:
                bare = bare.strip()
                row.append(None if bare == "NULL" else bare)


def dump_rows(text: str, table: str):
    """Every row of ``table``'s INSERT statements (mysqldump writes one statement per line)."""
    prefix = f"INSERT INTO `{table}` VALUES "
    for line in text.splitlines():
        if line.startswith(prefix):
            yield from value_rows(line[len(prefix):].rstrip().rstrip(";"))


# --------------------------------------------------------------------------------------
# download and stage
# --------------------------------------------------------------------------------------
def download(receipts: C.Receipts, refresh: bool) -> tuple[dict, list[dict]]:
    """The pinned tree, then every wanted file, each checked against its blob SHA-1. Returns
    (tree entries by path, receipts of the wanted files)."""
    tree_name = f"_tree_{PINNED_COMMIT[:12]}.json"
    tree_dest = C.raw_path(SOURCE, tree_name)
    receipt = C.download(TREE_URL.format(repo=REPO, commit=PINNED_COMMIT), tree_dest, receipts, name=tree_name,
                         refresh=refresh, validator=C.not_html)
    if receipt.get("error"):
        raise RuntimeError(f"could not list the repository tree: {receipt['error']}")
    tree = {e["path"]: e for e in json.loads(tree_dest.read_text(encoding="utf-8"))["tree"] if e["type"] == "blob"}
    files = []
    for path in sorted(p for p in tree if WANTED.match(p)):
        dest = C.raw_path(SOURCE, path)
        r = C.download(RAW_URL.format(repo=REPO, commit=PINNED_COMMIT, path=path), dest, receipts, name=path,
                       refresh=refresh, extra={"commit": PINNED_COMMIT, "git_blob_sha1": tree[path]["sha"]})
        if not r.get("error") and git_blob_sha1(dest.read_bytes()) != tree[path]["sha"]:
            r = receipts.record({**{k: v for k, v in r.items() if k != "skipped"},
                                 "error": "bytes differ from the pinned tree's blob SHA-1"})
        C.log(f"[{SOURCE}] {path}: " + (r["error"] if r.get("error") else f"{r.get('bytes', 0):,} bytes"
                                         + (" (cached)" if r.get("skipped") else "")))
        files.append(r)
    return tree, files


def stage(receipts: C.Receipts) -> list[dict]:
    staged = []
    for path in sorted(C.raw_path(SOURCE, "backup_sql").glob("*.sql")):
        rel_path = f"backup_sql/{path.name}"
        m = DUMP_NAME.match(rel_path)
        receipt = receipts.get(rel_path) or {}
        if m is None or receipt.get("error"):
            continue
        table = m.group(1)
        text = path.read_text(encoding="utf-8")
        columns = table_columns(text, table)
        dest = C.dump_path("points", SOURCE, f"{table}.parquet")
        prov = C.Provenance(SOURCE, C.rel(path), receipt.get("sha256"), receipt.get("retrieved_at"),
                            {"_commit": PINNED_COMMIT})
        stats = C.stage_rows(columns, ((i + 1, r) for i, r in enumerate(dump_rows(text, table))), dest, prov)
        meta = C.staged_meta("points", SOURCE, dest, receipt, stats, table=table, commit=PINNED_COMMIT,
                             repository_path=rel_path)
        staged.append(meta)
        C.log(f"[{SOURCE}] staged {meta['dest']}: {meta['rows']:,} rows, {len(columns)} columns"
              + (f", {meta['short_rows']} short, {meta['long_rows']} long" if meta["short_rows"] or meta["long_rows"] else ""))
    return staged


def run(args) -> dict:
    receipts = C.Receipts(SOURCE)
    files = []
    if not args.stage_only:
        _, files = download(receipts, args.refresh)
    staged = stage(receipts)
    summary = C.summarize(receipts, staged)
    summary.update(repo=REPO, commit=PINNED_COMMIT, retrieved_at=C.utc_now_iso(),
                   files=[{k: r.get(k) for k in ("name", "bytes", "sha256", "git_blob_sha1", "retrieved_at", "error")}
                          for r in files] or "stage only",
                   tables={s["table"]: {"rows": s["rows"], "columns": len(s["columns"]), "short_rows": s["short_rows"],
                                        "long_rows": s["long_rows"], "dest": s["dest"]} for s in staged})
    STUDY.mkdir(parents=True, exist_ok=True)
    (STUDY / "sirgenkii_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n",
                                                  encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh", action="store_true", help="download again even what is on disk")
    parser.add_argument("--stage-only", action="store_true", help="no HTTP; rebuild the Parquet from the raw dumps")
    summary = run(parser.parse_args())
    C.log(f"[{SOURCE}] done: {summary['staged_files']} tables, {summary['staged_rows']:,} rows, "
          f"{len(summary['errors'])} download errors")
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
