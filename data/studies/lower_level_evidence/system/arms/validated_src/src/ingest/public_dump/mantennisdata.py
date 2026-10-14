"""ATP match statistics with serve speeds: the GitHub dataset msolonskyi/ManTennisData.

What the repository holds, at commit 4e2d39f (4 Oct 2026, "atp update 2026-10-04"; a commit every Sunday):
    atp/matches_<year>.csv   one row per ATP match, 1999-2026 (tour level, Challengers, Slams): ATP player codes,
                             score, the box score and, from October 2021, the ATP Stats Centre's "Max Speed",
                             "1st Serve Average Speed" and "2nd Serve Average Speed" in km/h
                             (win_/los_fastest_first_serves_kmh, _average_first_serves_kmh, _average_second_serve_kmh),
                             with first serves in beside them. The Slams' rows carry no speed. No match date: the
                             tournament's start_dtm and the round (stadie_id) place a match.
    atp/tournaments.csv      tournament id, name, series, start and finish dates
    atp/players.csv          ATP player codes and names
    dc/                      the Davis Cup equivalents (not fetched)

The repository's collector (msolonskyi/tennisAnalyzer) opens atptour.com Stats Centre pages in Chrome and keeps the
numbers the page shows; the ATP's own page script decrypts the files in the browser. MIT label on the repository, no
data licence; the numbers are the ATP's. Downloaded under the owner's decision of 7 Oct 2026
(docs/decisions/2026-10-07-serve-speed-acquisition.md).

By default the files the serve-speed feature needs are fetched: matches_2021.csv ... matches_2026.csv (speeds start in
October 2021), tournaments.csv and players.csv, about 32 MB. ``--years all`` fetches every season from 1999.

Raw: data/raw/public_dump/mantennisdata/, the repository's paths kept (so serve_speed_sources/coverage.py --mantd
data/raw/public_dump/mantennisdata/atp reads them as they are), and _receipts.jsonl: URL, commit, time, status, bytes,
SHA-256 and the git blob SHA-1, checked against the tree. A file that a later commit changes is replaced, and the
earlier bytes are kept under superseded/ (common.keep_replaced).

Staged (data/dump/matches/mantennisdata/; strings throughout, as the rest of the dump):
    atp_matches_<year>.parquet, atp_tournaments.parquet, atp_players.parquet   each CSV verbatim, with provenance

Usage:
    ./python.sh -m src.ingest.public_dump.mantennisdata                   # 2021-2026 at the pinned commit
    ./python.sh -m src.ingest.public_dump.mantennisdata --commit latest   # the repository's current head (weekly)
    ./python.sh -m src.ingest.public_dump.mantennisdata --years all       # every season from 1999
    ./python.sh -m src.ingest.public_dump.mantennisdata --stage-only      # rebuild the tables from raw
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import common as C

SOURCE = "mantennisdata"
REPO = "msolonskyi/ManTennisData"
PINNED_COMMIT = "4e2d39f99e40b39bb98c3d2b7eb315ab0a510ea4"  # 4 Oct 2026, the head on 7 Oct 2026
RAW_URL = "https://raw.githubusercontent.com/{repo}/{commit}/{path}"
TREE_URL = "https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1"
HEAD_URL = "https://api.github.com/repos/{repo}/commits/HEAD"
STUDY_DIR = C.PROJECT_ROOT / "data" / "studies" / "serve_speed_acquisition"
META = {"README.md", "LICENSE", "atp/tournaments.csv", "atp/players.csv"}
MATCHES = re.compile(r"^atp/matches_(\d{4})\.csv$")
DEFAULT_YEARS = "2021-2026"
SPEED = ("win_average_first_serves_kmh", "los_average_first_serves_kmh")


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def parse_years(value: str) -> set[int] | None:
    """'2021-2026' -> {2021, ..., 2026}; '2019,2024' -> {2019, 2024}; 'all' -> None (every season)."""
    value = (value or "").strip().lower()
    if value == "all":
        return None
    years = set()
    for part in value.split(","):
        lo, _, hi = part.partition("-")
        years |= set(range(int(lo), int(hi or lo) + 1))
    return years


def wanted(path: str, years: set[int] | None) -> bool:
    if path in META:
        return True
    m = MATCHES.match(path)
    return bool(m) and (years is None or int(m.group(1)) in years)


def resolve_commit(value: str) -> str:
    """The pinned commit, an explicit SHA, or 'latest' (the repository's head, from the GitHub API)."""
    if value != "latest":
        return value
    response = C.session().get(HEAD_URL.format(repo=REPO), timeout=60)
    response.raise_for_status()
    return response.json()["sha"]


def load_tree(commit: str, receipts: C.Receipts) -> list[dict]:
    name = f"_tree_{commit[:12]}.json"
    dest = C.raw_path(SOURCE, name)
    rec = C.download(TREE_URL.format(repo=REPO, commit=commit), dest, receipts, name=name, validator=C.not_html)
    if rec.get("error"):
        raise RuntimeError(f"could not list the repository tree: {rec['error']}")
    tree = json.loads(dest.read_text(encoding="utf-8"))
    if tree.get("truncated"):
        raise RuntimeError("the tree listing is truncated")
    return [e for e in tree["tree"] if e["type"] == "blob"]


def fetch_file(entry: dict, commit: str, receipts: C.Receipts, refresh: bool) -> dict:
    path, blob = entry["path"], entry["sha"]
    dest = C.raw_path(SOURCE, path)
    previous = receipts.get(path)
    if (previous and not previous.get("error") and previous.get("git_blob_sha1") == blob and dest.exists()
            and not refresh):
        return {**previous, "skipped": True}
    url = RAW_URL.format(repo=REPO, commit=commit, path=path)
    receipt = {"name": path, "url": url, "dest": C.rel(dest), "commit": commit, "git_blob_sha1": blob,
               "retrieved_at": C.utc_now_iso()}
    body, last_error = None, None
    for attempt in range(3):
        try:
            response = C.session().get(url, timeout=180)
            receipt["status"] = response.status_code
            if response.status_code == 200:
                body = response.content
                break
            last_error = f"HTTP {response.status_code}"
        except Exception as err:  # requests' exception family
            last_error = f"{type(err).__name__}: {err}"
        time.sleep(3 * (attempt + 1))
    if body is None:
        receipt["error"] = last_error
        return receipts.record(receipt)
    if git_blob_sha1(body) != blob:
        receipt["error"] = "git blob SHA-1 differs from the tree"
        return receipts.record(receipt)
    dest.parent.mkdir(parents=True, exist_ok=True)
    kept = C.keep_replaced(dest, path, receipts, body)
    C.write_atomic(dest, body)
    receipt.update(bytes=len(body), sha256=C.sha256_bytes(body), blob_ok=True)
    if kept:
        receipt["superseded"] = kept
    return receipts.record(receipt)


def speed_census(path: Path) -> dict:
    """Rows, and rows with both players' 1st Serve Average Speed above zero (a raw count; no plausibility filter)."""
    header, _, rows = C.iter_delimited(path)
    idx = [header.index(c) for c in SPEED if c in header]
    n = both = 0
    for _, fields in rows:
        n += 1
        if len(idx) == 2 and all(i < len(fields) and _positive(fields[i]) for i in idx):
            both += 1
    return {"rows": n, "rows_both_first_serve_speeds": both}


def _positive(value: str) -> bool:
    try:
        return float(value) > 0
    except ValueError:
        return False


def stage(receipts: C.Receipts, commit: str) -> list[dict]:
    out = []
    for name, rec in sorted(receipts.all().items()):
        if rec.get("error") or not name.endswith(".csv") or name.startswith("held/"):
            continue
        src = C.raw_path(SOURCE, name)
        if not src.exists():
            continue
        dest = C.dump_path("matches", SOURCE, name.replace("/", "_").replace(".csv", ".parquet"))
        meta = C.stage_csv_file("matches", SOURCE, rec, src, dest, extra_provenance={"commit": rec.get("commit")},
                                commit=rec.get("commit"), repo=REPO)
        entry = {"file": name, "dest": meta["dest"], "rows": meta["rows"], "commit": rec.get("commit")}
        if MATCHES.match(name):
            entry.update(speed_census(src))
        out.append(entry)
        C.log(f"[{SOURCE}] staged {name}: {meta['rows']:,} rows")
    return out


def run(args) -> dict:
    started = time.time()
    receipts = C.Receipts(SOURCE)
    commit = resolve_commit(args.commit)
    years = parse_years(args.years)
    summary = {"source": SOURCE, "repo": REPO, "commit": commit, "years": args.years, "started_at": C.utc_now_iso(),
               "decision": "docs/decisions/2026-10-07-serve-speed-acquisition.md"}
    if not args.stage_only:
        blobs = load_tree(commit, receipts)
        plan = [e for e in blobs if wanted(e["path"], years)]
        summary.update(planned=len(plan), planned_bytes=sum(e["size"] for e in plan))
        C.log(f"[{SOURCE}] commit {commit[:12]}: {len(plan)} files planned ({summary['planned_bytes'] / 1e6:,.1f} MB)")
        outcomes = Counter()
        for entry in plan:
            rec = fetch_file(entry, commit, receipts, args.refresh)
            outcomes["error" if rec.get("error") else "held" if rec.get("skipped") else "downloaded"] += 1
        summary["outcomes"] = dict(outcomes)
    errors = [r for r in receipts.all().values() if r.get("error")]
    summary["receipts_with_errors"] = len(errors)
    summary["error_examples"] = [{"name": r["name"], "error": r["error"]} for r in errors[:20]]
    if not args.no_stage:
        summary["staged"] = stage(receipts, commit)
    summary["finished_at"] = C.utc_now_iso()
    summary["seconds"] = round(time.time() - started, 1)
    STUDY_DIR.mkdir(parents=True, exist_ok=True)
    (STUDY_DIR / "mantennisdata_summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--commit", default=PINNED_COMMIT,
                        help=f"commit to fetch: the pinned {PINNED_COMMIT[:12]} (default), a SHA, or 'latest'")
    parser.add_argument("--years", default=DEFAULT_YEARS,
                        help="seasons of atp/matches_<year>.csv: '2021-2026' (default), '2019,2024' or 'all'")
    parser.add_argument("--refresh", action="store_true", help="fetch files already held again")
    parser.add_argument("--stage-only", action="store_true", help="no downloads; rebuild the tables from raw")
    parser.add_argument("--no-stage", action="store_true", help="download only")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    C.log(f"[{SOURCE}] done in {summary['seconds']} s; {summary['receipts_with_errors']} receipts with errors")
    return 1 if summary["receipts_with_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
