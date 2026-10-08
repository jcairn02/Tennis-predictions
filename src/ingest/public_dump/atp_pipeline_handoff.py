"""Hugging Face dataset ``atlas-polybot/atp-pipeline-handoff``: a third party's raw scraper outputs for
men's tennis, 1990-2024 with some 2025-26, about 152 GB in 5,764 files, no licence and no dataset card.

Folders under ``data/tennis/`` in the repository: ATP Infosys Stats Centre match and point files
(``infosys_deep``, ``infosys_full``), Hawk-Eye Court Vision tracking (``court_vision``), Flashscore match
pages, statistics and head-to-head crawls (``flashscore_*``), ATP-site results with per-set and
season-to-date statistics (``atp_scraped*``), Tennis Abstract player and chart pages (``tennis_abstract``,
``mcp/charts``), api-tennis.com fixtures, ITF Davis Cup rows, ATP player profiles and Jeff Sackmann's ATP
files (``tennis_atp``). Collected under the owner's decision of 25 Sep 2026
(docs/decisions/2026-09-25-atp-pipeline-handoff.md).

``plan`` lists the pinned commit and assigns every file a chunk (``CHUNKS``, most predictive first) and an
action: fetch, or skip because the project already holds an identical copy or the dump holds the same
bytes twice. ``fetch`` streams each planned file in byte ranges (256 MB by default), gzips it as it
arrives with one gzip member per range, and checks it against the Hub's own hash (LFS SHA-256, or the
git blob SHA-1 of small files) before it counts as done. An interrupted file resumes from its last
complete range, recorded in ``_progress.jsonl``. Files under 1 MB and files that are already gzip are
stored as served. ``status`` rewrites the tracked status files from the receipts.

    data/raw/public_dump/atp_pipeline_handoff/   files mirroring the repository's paths under data/tennis/
                                                 (root files under _repo_root/), .gz added where compressed;
                                                 _receipts.jsonl, _progress.jsonl, _tree/, _logs/ (gitignored)
    data/studies/atp_pipeline_handoff/           README.md, plan.csv, status.md, status.json, runs.jsonl

Usage:
    ./python.sh -m src.ingest.public_dump.atp_pipeline_handoff plan
    ./python.sh -m src.ingest.public_dump.atp_pipeline_handoff fetch              # every chunk, in order
    ./python.sh -m src.ingest.public_dump.atp_pipeline_handoff fetch --chunks 1 --max-gb 5
    ./python.sh -m src.ingest.public_dump.atp_pipeline_handoff status
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import re
import sys
import threading
import time
import traceback
import urllib.parse
import zlib
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path

import requests

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import common as C

SOURCE = "atp_pipeline_handoff"
REPO = "atlas-polybot/atp-pipeline-handoff"
REVISION = "ea3d94d79f5d9e9b4bead031e2c6262f91a86c35"  # the dataset's last change, 19 Jun 2026; pinned 25 Sep 2026
HUB = "https://huggingface.co"
RAW_DIR = C.RAW_ROOT / SOURCE
STUDY_DIR = C.PROJECT_ROOT / "data" / "studies" / SOURCE
HELD_SACKMANN = C.RAW_ROOT / "sackmann_archive" / "atp"
DATA_PREFIX = "data/tennis/"
ROOT_DIR = "_repo_root"

PIECE_BYTES = 256 * 1024 * 1024
COMPRESS_MIN_BYTES = 1_000_000
GZIP_LEVEL = 6
DEFAULT_WORKERS = 4
DEFAULT_RPS = 5.0          # huggingface.co requests per second; the anonymous allowance is 3,000 per 5 minutes
LOW_REMAINING = 100        # pause for the window reset when fewer requests than this remain
MAX_CONSECUTIVE_429 = 3
PIECE_RETRIES = 5
EXPIRY_MARGIN_S = 300      # renew a signed download link this long before it expires
STATUS_EVERY_S = 60

CHUNKS = {
    1: "Everything outside the large Flashscore and infosys_full files: Infosys point data 2021-24, Court "
       "Vision tracking, ATP per-set and season-to-date statistics, Tennis Abstract chart and player pages, "
       "api-tennis fixtures, ATP profiles, Davis Cup, pre-2010 Sackmann files, the dump's progress files",
    2: "infosys_full: Infosys match files with Court Vision embedded, 2021-24",
    3: "flashscore_gql_stats: Flashscore statistics with winners, unforced errors and net points",
    4: "flashscore_full match files 2010-2024 (with Challenger 2010-11 and early 2025)",
    5: "flashscore_full match files 1990-2009 (with Challenger 2008-09)",
    6: "flashscore_full head-to-head crawl passes",
}
# Inside chunk 1, the most predictive sources first; inside every source, the most recent years first.
CHUNK1_ORDER = ("infosys_deep", "atp_scraped_enriched", "mcp", "api_tennis", "court_vision", "tennis_abstract",
                "atp_player_scrape", "atp_scraped", "tennis_atp", "itf_full", "itf_scraped", "flashscore_full",
                "flashscore_daily", "flashscore_data", "flashscore_bruteforce", ROOT_DIR)
PLAN_FIELDS = ("chunk", "rank", "source", "path", "size", "storage", "hash_algo", "hash", "action", "reason",
               "dest", "compress")
EMPTY_HASHES = {"sha256": hashlib.sha256(b"").hexdigest(), "git-sha1": hashlib.sha1(b"blob 0\0").hexdigest()}


class FatalStop(Exception):
    """Stops the whole run: the repository changed or vanished, or the Hub keeps refusing."""


class FileError(Exception):
    """One file could not be completed in this run; it stays resumable."""


class PieceError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


# --------------------------------------------------------------------------------------
# the plan
# --------------------------------------------------------------------------------------
@dataclass
class Entry:
    path: str                 # path in the repository, e.g. data/tennis/infosys_deep/2024_data.jsonl
    size: int
    storage: str              # "lfs" (content-addressed by SHA-256) or "git" (small file, git blob SHA-1)
    hash_algo: str            # "sha256" or "git-sha1"
    hash: str
    source: str = ""
    chunk: int = 0
    rank: int = 0
    action: str = "fetch"     # fetch | skip-held | skip-duplicate
    reason: str = ""
    dest: str = ""            # path under RAW_DIR
    compress: bool = False

    @classmethod
    def from_tree(cls, item: dict) -> "Entry":
        lfs = item.get("lfs")
        if lfs:
            return cls(item["path"], int(item["size"]), "lfs", "sha256", lfs["oid"])
        return cls(item["path"], int(item["size"]), "git", "git-sha1", item["oid"])

    def row(self) -> dict:
        return {"chunk": self.chunk, "rank": self.rank, "source": self.source, "path": self.path, "size": self.size,
                "storage": self.storage, "hash_algo": self.hash_algo, "hash": self.hash, "action": self.action,
                "reason": self.reason, "dest": self.dest, "compress": "gzip" if self.compress else ""}

    @classmethod
    def from_row(cls, row: dict) -> "Entry":
        return cls(row["path"], int(row["size"]), row["storage"], row["hash_algo"], row["hash"], row["source"],
                   int(row["chunk"]), int(row["rank"]), row["action"], row["reason"], row["dest"],
                   row["compress"] == "gzip")


def source_of(path: str) -> str:
    if not path.startswith(DATA_PREFIX):
        return ROOT_DIR
    return path[len(DATA_PREFIX):].split("/", 1)[0]


def chunk_of(path: str) -> int:
    source, name = source_of(path), path.rsplit("/", 1)[-1]
    if source == "infosys_full":
        return 2
    if source == "flashscore_gql_stats":
        return 3
    if source == "flashscore_full" and name.endswith(".jsonl"):
        if "_h2h_pass" in name:
            return 6
        match = re.match(r"flashscore_full_(\d{4})_(\d{4})_", name)
        return 5 if match and int(match.group(1)) < 2010 else 4
    return 1


def rank_of(path: str, chunk: int) -> int:
    """Order inside a chunk: source priority (chunk 1), then the most recent year first."""
    source = source_of(path)
    base = CHUNK1_ORDER.index(source) if chunk == 1 and source in CHUNK1_ORDER else len(CHUNK1_ORDER)
    inside = path[len(DATA_PREFIX):] if path.startswith(DATA_PREFIX) else path  # court_vision keeps its year in a folder
    years = [int(y) for y in re.findall(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", inside)]
    return base * 10_000 + (9_999 - max(years) if years else 9_999)


def dest_of(path: str, compress: bool) -> str:
    rel_path = path[len(DATA_PREFIX):] if path.startswith(DATA_PREFIX) else f"{ROOT_DIR}/{path}"
    return rel_path + (".gz" if compress else "")


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def held_identical(entry: Entry, held_dir: Path) -> str | None:
    """Reason text when the project already holds this file byte for byte (allowing CRLF line endings)."""
    if entry.source != "tennis_atp":
        return None
    local = held_dir / entry.path.rsplit("/", 1)[-1]
    if not local.is_file():
        return None
    data = local.read_bytes()
    candidates = [(data, "")]
    if b"\r\n" not in data:
        candidates.append((data.replace(b"\n", b"\r\n"), " apart from CRLF line endings"))
    for body, note in candidates:
        if len(body) != entry.size:
            continue
        digest = git_blob_sha1(body) if entry.hash_algo == "git-sha1" else hashlib.sha256(body).hexdigest()
        if digest == entry.hash:
            return f"identical to {C.rel(local)}{note}"
    return None


def build_plan(tree_items: list[dict], held_dir: Path = HELD_SACKMANN) -> list[Entry]:
    entries = [Entry.from_tree(item) for item in tree_items if item.get("type") == "file"]
    for e in entries:
        e.source = source_of(e.path)
        e.chunk = chunk_of(e.path)
        e.rank = rank_of(e.path, e.chunk)
        e.compress = e.size >= COMPRESS_MIN_BYTES and not e.path.endswith(".gz")
        e.dest = dest_of(e.path, e.compress)
        reason = held_identical(e, held_dir)
        if reason:
            e.action, e.reason = "skip-held", reason
    groups: dict[str, list[Entry]] = {}
    for e in entries:
        if e.storage == "lfs" and e.action == "fetch":
            groups.setdefault(e.hash, []).append(e)
    for group in groups.values():
        if len(group) > 1:
            keep = min(group, key=lambda e: (bool(re.search(r"shard|backup", e.path)), e.chunk, e.path))
            for e in group:
                if e is not keep:
                    e.action, e.reason = "skip-duplicate", f"same SHA-256 as {keep.path}"
    entries.sort(key=lambda e: (e.chunk, e.rank, e.path))
    return entries


def write_plan(entries: list[Entry], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PLAN_FIELDS)
        writer.writeheader()
        for e in entries:
            writer.writerow(e.row())


def read_plan(path: Path) -> list[Entry]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [Entry.from_row(row) for row in csv.DictReader(handle)]


def list_tree(sess=None) -> tuple[list[dict], list[str]]:
    """Every entry of the pinned commit, following the API's pagination."""
    sess = sess or C.session()
    url = f"{HUB}/api/datasets/{REPO}/tree/{REVISION}?recursive=true&expand=false"
    items, pages = [], []
    while url:
        response = sess.get(url, timeout=120)
        response.raise_for_status()
        items.extend(response.json())
        pages.append(url)
        match = re.search(r'<([^>]+)>;\s*rel="next"', response.headers.get("Link", ""))
        url = match.group(1) if match else None
        if url:
            time.sleep(1.0)
    return items, pages


# --------------------------------------------------------------------------------------
# journals, pacing, hashing
# --------------------------------------------------------------------------------------
class Journal:
    """Append-only JSONL of partial-file progress; the latest line per name wins."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._latest: dict[str, dict] = {}
        self._lock = threading.Lock()
        if path.exists():
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue  # a line cut short by a crash; that piece is simply fetched again
                self._latest[record["name"]] = record

    def get(self, name: str) -> dict | None:
        return self._latest.get(name)

    def record(self, name: str, **fields) -> None:
        record = {"name": name, "at": C.utc_now_iso(), **fields}
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write("\n" + json.dumps(record))  # leading newline: never glued to a cut-short line
            self._latest[name] = record


def parse_ratelimit(value: str | None) -> tuple[int, int] | None:
    """``"resolvers";r=2999;t=119`` -> (remaining requests, seconds until the window resets)."""
    if not value:
        return None
    remaining, reset = re.search(r"\br=(\d+)", value), re.search(r"\bt=(\d+)", value)
    if not remaining or not reset:
        return None
    return int(remaining.group(1)), int(reset.group(1))


class RateLimiter:
    """Paces requests to huggingface.co for every thread, and pauses when the Hub says the window is nearly used."""

    def __init__(self, rps: float):
        self.interval = 1.0 / rps if rps > 0 else 0.0
        self._lock = threading.Lock()
        self._next_at = 0.0
        self._pause_until = 0.0

    def wait(self) -> None:
        with self._lock:
            start = max(time.monotonic(), self._next_at, self._pause_until)
            self._next_at = start + self.interval
        delay = start - time.monotonic()
        if delay > 0:
            time.sleep(delay)

    def pause(self, seconds: float) -> None:
        with self._lock:
            self._pause_until = max(self._pause_until, time.monotonic() + seconds)

    def observe(self, headers) -> None:
        parsed = parse_ratelimit(headers.get("RateLimit"))
        if parsed and parsed[0] < LOW_REMAINING:
            self.pause(parsed[1] + 1)


class Digests:
    """SHA-256 of every file, plus the git blob SHA-1 that identifies a small git-stored file."""

    def __init__(self, entry: Entry | None = None):
        self.sha256 = hashlib.sha256()
        self.git = None
        if entry is not None and entry.hash_algo == "git-sha1":
            self.git = hashlib.sha1(b"blob %d\0" % entry.size)

    def update(self, block: bytes) -> None:
        self.sha256.update(block)
        if self.git is not None:
            self.git.update(block)

    def copy(self) -> "Digests":
        other = Digests()
        other.sha256 = self.sha256.copy()
        other.git = self.git.copy() if self.git is not None else None
        return other

    def check(self) -> str:
        return (self.git or self.sha256).hexdigest()


# --------------------------------------------------------------------------------------
# fetching one file
# --------------------------------------------------------------------------------------
@dataclass
class Context:
    raw_dir: Path
    receipts: C.Receipts
    progress: Journal
    limiter: RateLimiter
    run_id: str
    piece_bytes: int = PIECE_BYTES
    piece_retries: int = PIECE_RETRIES
    log_path: Path | None = None
    stop: threading.Event = field(default_factory=threading.Event)
    stop_reasons: list = field(default_factory=list)
    bytes_received: int = 0
    hub_requests: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def add_bytes(self, n: int) -> None:
        with self._lock:
            self.bytes_received += n

    def count_request(self) -> None:
        with self._lock:
            self.hub_requests += 1

    def log(self, message: str) -> None:
        line = f"{C.utc_now_iso()} {message}"
        print(line, flush=True)
        if self.log_path:
            with self._lock:
                with self.log_path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")


def resolve_url(path: str) -> str:
    return f"{HUB}/datasets/{REPO}/resolve/{REVISION}/{urllib.parse.quote(path)}"


def is_hub(url: str) -> bool:
    return urllib.parse.urlsplit(url).netloc == urllib.parse.urlsplit(HUB).netloc


def link_expiry(url: str) -> int | None:
    values = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("Expires")
    return int(values[0]) if values and values[0].isdigit() else None


def hub_request(ctx: Context, method: str, url: str, **kwargs) -> requests.Response:
    """One paced request to huggingface.co; a 429 waits for the advertised reset, three in a row stop the run."""
    for attempt in range(1, MAX_CONSECUTIVE_429 + 1):
        ctx.limiter.wait()
        response = C.session().request(method, url, **kwargs)
        ctx.count_request()
        ctx.limiter.observe(response.headers)
        if response.status_code != 429:
            return response
        response.close()
        wait_s = (parse_ratelimit(response.headers.get("RateLimit")) or (0, 60))[1] + 1
        ctx.log(f"HTTP 429 from the Hub ({attempt} in a row); waiting {wait_s}s for the window to reset")
        ctx.limiter.pause(wait_s)
    raise FatalStop(f"HTTP 429 {MAX_CONSECUTIVE_429} times in a row on {url}")


def resolve(entry: Entry, ctx: Context) -> tuple[str, dict]:
    """The download location of one file at the pinned commit, checked against the plan."""
    url, last = resolve_url(entry.path), None
    for attempt in range(4):
        try:
            response = hub_request(ctx, "HEAD", url, allow_redirects=False, timeout=60)
        except requests.RequestException as err:
            last = f"{type(err).__name__}: {err}"
            time.sleep(2 * (attempt + 1))
            continue
        status, headers = response.status_code, response.headers
        if status in (301, 302, 303, 307, 308):
            location = urllib.parse.urljoin(url, headers["Location"])
            meta = {"x_repo_commit": headers.get("X-Repo-Commit"),
                    "x_linked_etag": (headers.get("X-Linked-ETag") or "").strip('"') or None,
                    "x_linked_size": headers.get("X-Linked-Size"),
                    "final_host": urllib.parse.urlsplit(location).netloc, "expires": link_expiry(location)}
            if meta["x_repo_commit"] and meta["x_repo_commit"] != REVISION:
                raise FatalStop(f"{entry.path}: served from commit {meta['x_repo_commit']}, not {REVISION}")
            if meta["x_linked_size"] and int(meta["x_linked_size"]) != entry.size:
                raise FatalStop(f"{entry.path}: size {meta['x_linked_size']} differs from the plan's {entry.size}")
            if meta["x_linked_etag"] and meta["x_linked_etag"] != entry.hash:
                raise FatalStop(f"{entry.path}: hash {meta['x_linked_etag']} differs from the plan's {entry.hash}")
            return location, meta
        if status == 200:
            return url, {"final_host": urllib.parse.urlsplit(url).netloc, "expires": None}
        if status in (401, 403, 404, 410):
            raise FatalStop(f"HTTP {status} resolving {entry.path}: the repository changed, vanished or refused")
        last = f"HTTP {status}"
        time.sleep(2 * (attempt + 1))
    raise FileError(f"could not resolve {entry.path}: {last}")


def fetch_piece(url: str, entry: Entry, start: int, end: int, handle, digests: Digests, ctx: Context) -> int:
    """Append bytes ``start..end`` of the file to ``handle`` (one complete gzip member if compressing)."""
    kwargs = {"headers": {"Range": f"bytes={start}-{end}"}, "stream": True, "timeout": (30, 120)}
    response = hub_request(ctx, "GET", url, **kwargs) if is_hub(url) else C.session().get(url, **kwargs)
    with response:
        whole = start == 0 and end == entry.size - 1
        if response.status_code == 206:
            served = re.match(r"bytes (\d+)-(\d+)/", response.headers.get("Content-Range", ""))
            if not served or int(served.group(1)) != start:
                raise PieceError(f"asked for bytes {start}-{end}, got {response.headers.get('Content-Range')!r}")
        elif not (response.status_code == 200 and whole):
            raise PieceError(f"HTTP {response.status_code} for bytes {start}-{end}", response.status_code)
        compressor = zlib.compressobj(GZIP_LEVEL, zlib.DEFLATED, 31) if entry.compress else None
        wanted, got = end - start + 1, 0
        for block in response.iter_content(1 << 20):
            if not block:
                continue
            got += len(block)
            if got > wanted:
                raise PieceError(f"more than the {wanted} bytes asked for")
            digests.update(block)
            handle.write(compressor.compress(block) if compressor else block)
            ctx.add_bytes(len(block))
        if compressor:
            handle.write(compressor.flush())
    if got != wanted:
        raise PieceError(f"short read: {got} of {wanted} bytes")
    return got


def fetch_range(url: str, meta: dict, entry: Entry, start: int, end: int, handle, digests: Digests,
                ctx: Context) -> tuple[Digests, str, dict]:
    """``fetch_piece`` with retries; a failed attempt is rolled back to the piece's start."""
    position, last, renewed = handle.tell(), None, False
    for attempt in range(ctx.piece_retries + 1):
        if meta.get("expires") and time.time() > meta["expires"] - EXPIRY_MARGIN_S:
            url, meta = resolve(entry, ctx)
        attempt_digests = digests.copy()
        try:
            fetch_piece(url, entry, start, end, handle, attempt_digests, ctx)
            return attempt_digests, url, meta
        except FatalStop:
            raise
        except (requests.RequestException, PieceError, zlib.error) as err:
            last = err
            handle.seek(position)
            handle.truncate()
            if isinstance(err, PieceError) and err.status in (403, 410):
                if renewed:
                    raise FatalStop(f"HTTP {err.status} on {entry.path} even with a renewed download link")
                url, meta = resolve(entry, ctx)  # an expired signed link: renew it once
                renewed = True
                continue
            if attempt < ctx.piece_retries:
                ctx.log(f"retry {entry.path} bytes {start:,}-{end:,} ({type(err).__name__}: {err})")
                time.sleep(min(60, 2 ** (attempt + 1)))
    raise FileError(f"{entry.path} bytes {start:,}-{end:,} failed {ctx.piece_retries + 1} times: {last}")


def resume_state(entry: Entry, part: Path, ctx: Context) -> tuple[int, Digests, int]:
    """(source offset, digests so far, bytes to keep in the .part file); (0, fresh, 0) restarts the file."""
    fresh = (0, Digests(entry), 0)
    progress = ctx.progress.get(entry.path)
    if not progress or not part.exists() or int(progress.get("offset", 0)) <= 0:
        return fresh
    offset, keep = int(progress["offset"]), int(progress["part_bytes"])
    if part.stat().st_size < keep or offset > entry.size:
        return fresh
    with part.open("r+b") as handle:
        handle.truncate(keep)  # drops a piece that was being written when the run stopped
    digests, seen = Digests(entry), 0
    try:
        with (gzip.open(part, "rb") if entry.compress else part.open("rb")) as source:
            for block in iter(lambda: source.read(1 << 20), b""):
                digests.update(block)
                seen += len(block)
    except (OSError, EOFError, zlib.error):
        return fresh
    if seen != offset:
        return fresh
    ctx.log(f"resume {entry.path} from byte {offset:,} of {entry.size:,}")
    return offset, digests, keep


def fetch_file(entry: Entry, ctx: Context) -> dict:
    """Download, verify and store one planned file; returns its receipt."""
    dest = ctx.raw_dir / entry.dest
    part = dest.with_name(dest.name + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    receipt = {"name": entry.path, "chunk": entry.chunk, "source": entry.source, "url": resolve_url(entry.path),
               "revision": REVISION, "bytes": entry.size, "hash_algo": entry.hash_algo,
               "hash_expected": entry.hash, "dest": C.rel(dest),
               "compression": "gzip, one member per range" if entry.compress else "none",
               "retrieved_at": C.utc_now_iso(), "run_id": ctx.run_id}
    if entry.size == 0:
        if entry.hash != EMPTY_HASHES[entry.hash_algo]:
            raise FileError(f"{entry.path}: size 0 but hash {entry.hash}")
        dest.write_bytes(b"")
        receipt.update(route="empty file; its content is fixed by its hash", sha256=EMPTY_HASHES["sha256"],
                       hash_ok=True, stored_bytes=0, pieces=0, finished_at=C.utc_now_iso())
        return ctx.receipts.record(receipt)
    offset, digests, keep = resume_state(entry, part, ctx)
    resumed_from = offset
    url, meta = resolve(entry, ctx)
    receipt.update({k: v for k, v in meta.items() if k != "expires"})
    pieces = 0
    with part.open("r+b" if part.exists() else "wb") as handle:
        handle.seek(keep)
        handle.truncate()
        while offset < entry.size:
            end = min(offset + ctx.piece_bytes, entry.size) - 1
            digests, url, meta = fetch_range(url, meta, entry, offset, end, handle, digests, ctx)
            handle.flush()
            os.fsync(handle.fileno())
            offset, pieces = end + 1, pieces + 1
            if entry.size > ctx.piece_bytes:
                ctx.progress.record(entry.path, offset=offset, part_bytes=handle.tell(), run_id=ctx.run_id)
        stored_bytes = handle.tell()
    if digests.check() != entry.hash:
        kept = part.with_name(f"{part.name}.bad-{ctx.run_id}")
        os.replace(part, kept)  # kept as evidence, never deleted; the next run starts the file again
        ctx.progress.record(entry.path, offset=0, part_bytes=0, run_id=ctx.run_id, note="hash mismatch")
        receipt.update(error=f"hash mismatch: got {digests.check()}", kept_as=C.rel(kept))
        return ctx.receipts.record(receipt)
    os.replace(part, dest)
    receipt.update(sha256=digests.sha256.hexdigest(), hash_ok=True, stored_bytes=stored_bytes, pieces=pieces,
                   resumed_from=resumed_from, finished_at=C.utc_now_iso(),
                   seconds=round(time.monotonic() - started, 1))
    return ctx.receipts.record(receipt)


def is_done(entry: Entry, receipts: C.Receipts, raw_dir: Path) -> bool:
    receipt = receipts.get(entry.path)
    return bool(receipt and receipt.get("hash_ok") and (raw_dir / entry.dest).exists())


# --------------------------------------------------------------------------------------
# a run
# --------------------------------------------------------------------------------------
def run_fetch(entries: list[Entry], ctx: Context, workers: int = DEFAULT_WORKERS, max_bytes: int | None = None,
              max_requests: int | None = None, max_files: int | None = None, on_progress=None) -> dict:
    """Fetch ``entries`` in order with ``workers`` threads until done, a budget is spent or a fatal stop."""
    todo = [e for e in entries if e.action == "fetch" and not is_done(e, ctx.receipts, ctx.raw_dir)]
    queue = iter(todo)
    done, failed, started_files = [], [], 0
    lock = threading.Lock()

    def work(entry: Entry) -> dict:
        try:
            return fetch_file(entry, ctx)
        except FatalStop as err:
            ctx.stop.set()
            ctx.stop_reasons.append(str(err))
            message = str(err)
        except FileError as err:
            message = str(err)
        except Exception as err:  # noqa: BLE001 - one file's bug must not lose the other threads' work
            message = f"{type(err).__name__}: {err} | {traceback.format_exc(limit=3)}"
        return ctx.receipts.record({"name": entry.path, "chunk": entry.chunk, "source": entry.source,
                                    "url": resolve_url(entry.path), "revision": REVISION,
                                    "retrieved_at": C.utc_now_iso(), "run_id": ctx.run_id, "error": message})

    def budget_left() -> bool:
        if max_bytes is not None and ctx.bytes_received >= max_bytes:
            reason = f"byte budget reached ({ctx.bytes_received / 1e9:.2f} GB)"
        elif max_requests is not None and ctx.hub_requests >= max_requests:
            reason = f"request budget reached ({ctx.hub_requests})"
        elif max_files is not None and started_files >= max_files:
            reason = f"file budget reached ({started_files})"
        else:
            return True
        if reason not in ctx.stop_reasons:
            ctx.stop_reasons.append(reason)
        return False

    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {}

        def submit_next() -> None:
            nonlocal started_files
            if ctx.stop.is_set() or not budget_left():
                return
            entry = next(queue, None)
            if entry is not None:
                started_files += 1
                pending[pool.submit(work, entry)] = entry

        for _ in range(workers):
            submit_next()
        while pending:
            finished, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in finished:
                entry = pending.pop(future)
                receipt = future.result()
                with lock:
                    (failed if receipt.get("error") else done).append(receipt)
                if receipt.get("error"):
                    ctx.log(f"FAILED [chunk {entry.chunk}] {entry.path}: {receipt['error'][:300]}")
                else:
                    ctx.log(f"done [chunk {entry.chunk}] {entry.path} {entry.size / 1e6:,.1f} MB in "
                            f"{receipt.get('seconds', 0)}s | run: {len(done)} files, "
                            f"{ctx.bytes_received / 1e9:.2f} GB received, {ctx.hub_requests} Hub requests")
                if on_progress:
                    on_progress()
                submit_next()
    return {"planned_this_run": len(todo), "files_done": len(done), "files_failed": len(failed),
            "failed": [r["name"] for r in failed], "bytes_received": ctx.bytes_received,
            "hub_requests": ctx.hub_requests, "stop_reasons": list(ctx.stop_reasons),
            "complete": not ctx.stop.is_set() and len(done) == len(todo)}


# --------------------------------------------------------------------------------------
# status
# --------------------------------------------------------------------------------------
def compute_status(entries: list[Entry], receipts: C.Receipts, progress: Journal, raw_dir: Path) -> dict:
    def blank():
        return {"files": 0, "bytes": 0, "done_files": 0, "done_bytes": 0, "stored_bytes": 0, "partial_files": 0,
                "partial_bytes": 0, "failed_files": 0}

    chunks = {c: blank() for c in CHUNKS}
    sources: dict[str, dict] = {}
    skipped, failed, partial = Counter(), [], []
    for e in entries:
        if e.action != "fetch":
            skipped[e.action] += 1
            continue
        for bucket in (chunks[e.chunk], sources.setdefault(e.source, blank())):
            bucket["files"] += 1
            bucket["bytes"] += e.size
        receipt = receipts.get(e.path)
        if receipt and receipt.get("hash_ok") and (raw_dir / e.dest).exists():
            for bucket in (chunks[e.chunk], sources[e.source]):
                bucket["done_files"] += 1
                bucket["done_bytes"] += e.size
                bucket["stored_bytes"] += int(receipt.get("stored_bytes") or 0)
            continue
        state = progress.get(e.path)
        if state and int(state.get("offset", 0)) > 0:
            for bucket in (chunks[e.chunk], sources[e.source]):
                bucket["partial_files"] += 1
                bucket["partial_bytes"] += int(state["offset"])
            partial.append({"path": e.path, "offset": int(state["offset"]), "size": e.size})
        if receipt and receipt.get("error"):
            for bucket in (chunks[e.chunk], sources[e.source]):
                bucket["failed_files"] += 1
            failed.append({"path": e.path, "chunk": e.chunk, "error": receipt["error"][:300],
                           "at": receipt.get("retrieved_at")})
    total = blank()
    for bucket in chunks.values():
        for key in total:
            total[key] += bucket[key]
    return {"generated_at": C.utc_now_iso(), "repository": REPO, "revision": REVISION, "total": total,
            "chunks": {str(c): {"content": CHUNKS[c], **v} for c, v in chunks.items()},
            "sources": dict(sorted(sources.items())), "skipped": dict(skipped),
            "partial": partial, "failed": failed}


def _gb(n: int) -> str:
    return f"{n / 1e9:,.2f}"


def render_status(status: dict, last_run: dict | None = None) -> str:
    total = status["total"]
    left_files = total["files"] - total["done_files"]
    lines = [
        "# Download status: `atlas-polybot/atp-pipeline-handoff`",
        "",
        f"Generated {status['generated_at']} by `./python.sh -m src.ingest.public_dump.atp_pipeline_handoff status` "
        f"(also rewritten every minute while a fetch runs). Pinned commit `{status['revision']}`. "
        "What the chunks are and how to resume: [README.md](README.md).",
        "",
        f"**{total['done_files']:,} of {total['files']:,} files done ({_gb(total['done_bytes'])} of "
        f"{_gb(total['bytes'])} GB); {left_files:,} files and {_gb(total['bytes'] - total['done_bytes'])} GB left.** "
        f"Done files take {_gb(total['stored_bytes'])} GB on disk. "
        f"{total['partial_files']} file(s) part-way, {total['failed_files']} with an error in their latest attempt.",
        "",
        "| Chunk | Content | Files done / planned | GB done / planned | GB left | State |",
        "|---:|---|---:|---:|---:|---|",
    ]
    for chunk, c in status["chunks"].items():
        state = ("done" if c["done_files"] == c["files"] else
                 "in progress" if c["done_files"] or c["partial_files"] else "not started")
        if c["failed_files"]:
            state += f", {c['failed_files']} failed"
        lines.append(f"| {chunk} | {c['content']} | {c['done_files']:,} / {c['files']:,} | {_gb(c['done_bytes'])} / "
                     f"{_gb(c['bytes'])} | {_gb(c['bytes'] - c['done_bytes'])} | {state} |")
    lines += ["", "| Source folder | Files done / planned | GB done / planned | GB on disk |", "|---|---:|---:|---:|"]
    for source, s in status["sources"].items():
        lines.append(f"| `{source}` | {s['done_files']:,} / {s['files']:,} | {_gb(s['done_bytes'])} / "
                     f"{_gb(s['bytes'])} | {_gb(s['stored_bytes'])} |")
    skipped = ", ".join(f"{n} {k}" for k, n in sorted(status["skipped"].items())) or "none"
    lines += ["", f"Not planned for download: {skipped} (reasons per file in [plan.csv](plan.csv))."]
    if status["partial"]:
        lines += ["", "Part-way (resume from the byte shown):", ""]
        lines += [f"* `{p['path']}`: {p['offset']:,} of {p['size']:,} bytes" for p in status["partial"][:50]]
    if status["failed"]:
        lines += ["", "Latest attempt failed (the next fetch retries them):", ""]
        lines += [f"* `{f['path']}` ({f['at']}): {f['error']}" for f in status["failed"][:50]]
    if last_run and last_run.get("ended_at"):
        lines += ["", f"Last run `{last_run.get('run_id')}` ended {last_run['ended_at']}: "
                      f"{last_run.get('files_done', 0)} files done, {last_run.get('files_failed', 0)} failed, "
                      f"{_gb(last_run.get('bytes_received', 0))} GB received; stopped because: "
                      f"{'; '.join(last_run.get('stop_reasons') or []) or 'it finished its list'}."]
    elif last_run:
        lines += ["", f"Run `{last_run.get('run_id')}` started {last_run.get('started_at')} and has no end recorded: "
                      f"it is still running, or it was interrupted (compare this page's time with now). "
                      f"{_gb(last_run.get('bytes_received') or 0)} GB received by this update."]
    lines += ["", "Resume (skips finished files, continues part-way ones from their last complete range):", "",
              "```", "./python.sh -m src.ingest.public_dump.atp_pipeline_handoff fetch", "```", ""]
    return "\n".join(lines)


def write_status(entries: list[Entry], receipts: C.Receipts, progress: Journal, raw_dir: Path = RAW_DIR,
                 study_dir: Path = STUDY_DIR, last_run: dict | None = None) -> dict:
    status = compute_status(entries, receipts, progress, raw_dir)
    if last_run:
        status["last_run"] = last_run
    study_dir.mkdir(parents=True, exist_ok=True)
    (study_dir / "status.json").write_text(json.dumps(status, indent=1), encoding="utf-8")
    (study_dir / "status.md").write_text(render_status(status, last_run), encoding="utf-8")
    return status


RAW_README = """# atlas-polybot/atp-pipeline-handoff: downloaded files

Files from the public Hugging Face dataset https://huggingface.co/datasets/{repo}
at commit {revision}, fetched by `src/ingest/public_dump/atp_pipeline_handoff.py` under
docs/decisions/2026-09-25-atp-pipeline-handoff.md.

* Paths mirror the repository's `data/tennis/<source>/...`; the repository's root files are in `{root}/`.
* A `.gz` suffix means the file was gzipped on arrival (one gzip member per 256 MB range);
  `gzip.open()` returns the original bytes. Files under 1 MB and files that were already gzip are as served.
* Every finished file matched the Hub's own hash; see `_receipts.jsonl` (latest line per name wins).
* `*.part` files are downloads in progress; `_progress.jsonl` records their last complete range.
* `_tree/` holds the repository listing the plan was built from; `_logs/` holds one log per run.

The plan (which chunk each file belongs to, what was skipped and why), the live status of what is done
and left, and the run log are tracked in data/studies/{source}/.

Resume or continue: ./python.sh -m src.ingest.public_dump.atp_pipeline_handoff fetch
"""


# --------------------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------------------
def cmd_plan(args) -> int:
    items, pages = list_tree()
    tree_path = RAW_DIR / "_tree" / f"tree_{REVISION[:12]}.json"
    tree_path.parent.mkdir(parents=True, exist_ok=True)
    tree_path.write_text(json.dumps(items), encoding="utf-8")
    receipts = C.Receipts(SOURCE)
    receipts.record({"name": C.rel(tree_path), "url": pages[0], "pages": len(pages), "revision": REVISION,
                     "entries": len(items), "sha256": C.sha256_file(tree_path), "retrieved_at": C.utc_now_iso()})
    entries = build_plan(items)
    write_plan(entries, STUDY_DIR / "plan.csv")
    (RAW_DIR / "README.md").write_text(RAW_README.format(repo=REPO, revision=REVISION, root=ROOT_DIR,
                                                         source=SOURCE), encoding="utf-8")
    actions = Counter(e.action for e in entries)
    C.log(f"[{SOURCE}] {len(entries):,} files at {REVISION[:12]}: {dict(actions)}")
    for chunk in CHUNKS:
        todo = [e for e in entries if e.chunk == chunk and e.action == "fetch"]
        C.log(f"  chunk {chunk}: {len(todo):,} files, {sum(e.size for e in todo) / 1e9:,.2f} GB")
    write_status(entries, receipts, Journal(RAW_DIR / "_progress.jsonl"))
    return 0


def cmd_fetch(args) -> int:
    plan_path = STUDY_DIR / "plan.csv"
    if not plan_path.exists():
        C.log(f"[{SOURCE}] no plan yet: run the plan command first")
        return 2
    entries = read_plan(plan_path)
    selected = [e for e in entries if e.chunk in set(args.chunks) and e.action == "fetch"]
    if args.paths:
        wanted = set(args.paths)
        selected = [e for e in entries if e.path in wanted]
    selected.sort(key=lambda e: (args.chunks.index(e.chunk) if e.chunk in args.chunks else 99, e.rank, e.path))
    receipts = C.Receipts(SOURCE)
    progress = Journal(RAW_DIR / "_progress.jsonl")
    todo = [e for e in selected if not is_done(e, receipts, RAW_DIR)]
    C.log(f"[{SOURCE}] {len(todo):,} of {len(selected):,} selected files still to fetch, "
          f"{sum(e.size for e in todo) / 1e9:,.2f} GB")
    if args.dry_run:
        for chunk in args.chunks:
            part = [e for e in todo if e.chunk == chunk]
            C.log(f"  chunk {chunk}: {len(part):,} files, {sum(e.size for e in part) / 1e9:,.2f} GB")
        return 0
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    log_path = RAW_DIR / "_logs" / f"{run_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    ctx = Context(RAW_DIR, receipts, progress, RateLimiter(args.rps), run_id,
                  piece_bytes=args.piece_mb * 1024 * 1024, log_path=log_path)
    run = {"run_id": run_id, "started_at": C.utc_now_iso(), "argv": sys.argv[1:], "chunks": args.chunks,
           "workers": args.workers, "rps": args.rps, "revision": REVISION, "log": C.rel(log_path)}
    runs_path = STUDY_DIR / "runs.jsonl"
    with runs_path.open("a", encoding="utf-8") as handle:  # a run that crashes leaves this line and no "ended" one
        handle.write(json.dumps({"event": "started", **run, "files_to_fetch": len(todo)}) + "\n")
    if args.abort_after_seconds:  # test aid: an abrupt stop, as if the machine or session died
        timer = threading.Timer(args.abort_after_seconds, lambda: os._exit(3))
        timer.daemon = True
        timer.start()
    last_status = [time.monotonic()]

    def on_progress() -> None:
        if time.monotonic() - last_status[0] >= STATUS_EVERY_S:
            last_status[0] = time.monotonic()
            write_status(entries, receipts, progress, last_run={**run, "bytes_received": ctx.bytes_received})

    ctx.log(f"run {run_id}: chunks {args.chunks}, {len(todo):,} files, workers {args.workers}, {args.rps} req/s")
    result = {}
    try:
        result = run_fetch(selected, ctx, workers=args.workers,
                           max_bytes=int(args.max_gb * 1e9) if args.max_gb else None,
                           max_requests=args.max_requests, max_files=args.max_files, on_progress=on_progress)
    finally:
        run.update(result or {"stop_reasons": ctx.stop_reasons, "bytes_received": ctx.bytes_received,
                              "hub_requests": ctx.hub_requests})
        run["ended_at"] = C.utc_now_iso()
        with runs_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"event": "ended", **{k: v for k, v in run.items() if k != "failed"}}) + "\n")
        status = write_status(entries, receipts, progress, last_run=run)
        ctx.log(f"run {run_id} ended: {run.get('files_done', 0)} done, {run.get('files_failed', 0)} failed, "
                f"{ctx.bytes_received / 1e9:.2f} GB received; overall {status['total']['done_files']:,} of "
                f"{status['total']['files']:,} files; stop: {'; '.join(run.get('stop_reasons') or []) or 'none'}")
    return 0 if result.get("complete") else 1


def cmd_status(args) -> int:
    entries = read_plan(STUDY_DIR / "plan.csv")
    runs = (STUDY_DIR / "runs.jsonl").read_text(encoding="utf-8").splitlines() if (STUDY_DIR / "runs.jsonl").exists() else []
    last_run = json.loads(runs[-1]) if runs else None
    status = write_status(entries, C.Receipts(SOURCE), Journal(RAW_DIR / "_progress.jsonl"), last_run=last_run)
    total = status["total"]
    C.log(f"[{SOURCE}] {total['done_files']:,} of {total['files']:,} files, {_gb(total['done_bytes'])} of "
          f"{_gb(total['bytes'])} GB done; {total['partial_files']} part-way, {total['failed_files']} failed")
    for chunk, c in status["chunks"].items():
        C.log(f"  chunk {chunk}: {c['done_files']:,}/{c['files']:,} files, {_gb(c['done_bytes'])}/{_gb(c['bytes'])} GB")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan", help="list the pinned commit and write plan.csv, the raw README and the status")
    fetch = sub.add_parser("fetch", help="download planned files, most predictive chunk first")
    fetch.add_argument("--chunks", type=int, nargs="+", default=list(CHUNKS), choices=list(CHUNKS))
    fetch.add_argument("--paths", nargs="+", help="only these repository paths (smoke tests)")
    fetch.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    fetch.add_argument("--rps", type=float, default=DEFAULT_RPS, help="requests per second to huggingface.co")
    fetch.add_argument("--max-gb", type=float, help="stop starting new files after this many GB this run")
    fetch.add_argument("--max-requests", type=int, help="stop starting new files after this many Hub requests")
    fetch.add_argument("--max-files", type=int, help="start at most this many files this run")
    fetch.add_argument("--piece-mb", type=int, default=PIECE_BYTES // (1024 * 1024))
    fetch.add_argument("--dry-run", action="store_true")
    fetch.add_argument("--abort-after-seconds", type=float, help=argparse.SUPPRESS)
    sub.add_parser("status", help="rewrite status.md and status.json from the receipts")
    args = parser.parse_args(argv)
    return {"plan": cmd_plan, "fetch": cmd_fetch, "status": cmd_status}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
