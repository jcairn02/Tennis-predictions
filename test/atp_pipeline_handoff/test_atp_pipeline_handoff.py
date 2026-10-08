"""Offline tests for the Hugging Face ATP pipeline dump downloader: planning, hashing, resume and status."""
import gzip
import hashlib
import http.server
import json
import math
import re
import sys
import threading
import time
import urllib.parse
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.public_dump import atp_pipeline_handoff as H  # noqa: E402
from src.ingest.public_dump import common as C  # noqa: E402


# --------------------------------------------------------------------------------------
# planning
# --------------------------------------------------------------------------------------
def lfs(path, size, oid):
    return {"type": "file", "path": path, "size": size, "oid": "0" * 40, "lfs": {"oid": oid, "size": size}}


def git(path, size, oid):
    return {"type": "file", "path": path, "size": size, "oid": oid}


def test_git_blob_sha1_matches_git():
    assert H.git_blob_sha1(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
    assert H.git_blob_sha1(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"
    assert H.EMPTY_HASHES["git-sha1"] == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


def test_parse_ratelimit():
    assert H.parse_ratelimit('"resolvers";r=2999;t=119') == (2999, 119)
    assert H.parse_ratelimit(None) is None
    assert H.parse_ratelimit("garbage") is None


def test_plan_assigns_chunks_actions_and_destinations(tmp_path):
    held = tmp_path / "held"
    held.mkdir()
    ours = b"tourney_id,winner_name\n2020-001,A\n2020-002,B\n"
    (held / "atp_matches_2020.csv").write_bytes(ours)
    (held / "atp_players.csv").write_bytes(b"player_id\n1\n")
    theirs = ours.replace(b"\n", b"\r\n")
    twice = "a" * 64
    items = [
        {"type": "directory", "path": "data"},
        git("RAW_DATA_SOURCES.md", 3826, "1" * 40),
        git("data/tennis/tennis_atp/atp_matches_2020.csv", len(theirs), H.git_blob_sha1(theirs)),
        git("data/tennis/tennis_atp/atp_players.csv", 99, "2" * 40),
        git("data/tennis/tennis_atp/atp_matches_1999.csv", 500_000, "3" * 40),
        git("data/tennis/flashscore_full/checkpoint_full_2023_2023_atp.json", 5000, "4" * 40),
        lfs("data/tennis/infosys_deep/2024_data.jsonl", 1_045_700_000, "b" * 64),
        lfs("data/tennis/infosys_deep/2022_data.jsonl", 940_700_000, "8" * 64),
        lfs("data/tennis/infosys_full/2024_data.jsonl", 2_983_000_000, "c" * 64),
        lfs("data/tennis/court_vision/2024/1536_MS001.json.gz", 40_000, "d" * 64),
        lfs("data/tennis/flashscore_gql_stats/gql_stats_2023_2023_atp.jsonl", 323_000_000, "e" * 64),
        lfs("data/tennis/flashscore_full/flashscore_full_2023_2023_atp.jsonl", 1_418_000_000, "f" * 64),
        lfs("data/tennis/flashscore_full/flashscore_full_2009_2009_challenger.jsonl", 961_000_000, twice),
        lfs("data/tennis/flashscore_full/flashscore_full_shard0.jsonl", 961_000_000, twice),
        lfs("data/tennis/flashscore_full/flashscore_full_h2h_pass11_shard0.jsonl", 8_013_000_000, "9" * 64),
    ]
    entries = H.build_plan(items, held)
    plan = {e.path: e for e in entries}
    assert len(entries) == 14  # directories are not files

    held_file = plan["data/tennis/tennis_atp/atp_matches_2020.csv"]
    assert held_file.action == "skip-held" and "CRLF" in held_file.reason
    assert plan["data/tennis/tennis_atp/atp_players.csv"].action == "fetch"  # differs from ours
    assert plan["data/tennis/tennis_atp/atp_matches_1999.csv"].action == "fetch"  # we hold no copy
    shard = plan["data/tennis/flashscore_full/flashscore_full_shard0.jsonl"]
    assert shard.action == "skip-duplicate" and "2009_2009_challenger" in shard.reason
    assert plan["data/tennis/flashscore_full/flashscore_full_2009_2009_challenger.jsonl"].action == "fetch"

    chunk = {p: e.chunk for p, e in plan.items()}
    assert chunk["data/tennis/infosys_deep/2024_data.jsonl"] == 1
    assert chunk["data/tennis/court_vision/2024/1536_MS001.json.gz"] == 1
    assert chunk["data/tennis/flashscore_full/checkpoint_full_2023_2023_atp.json"] == 1
    assert chunk["RAW_DATA_SOURCES.md"] == 1
    assert chunk["data/tennis/infosys_full/2024_data.jsonl"] == 2
    assert chunk["data/tennis/flashscore_gql_stats/gql_stats_2023_2023_atp.jsonl"] == 3
    assert chunk["data/tennis/flashscore_full/flashscore_full_2023_2023_atp.jsonl"] == 4
    assert chunk["data/tennis/flashscore_full/flashscore_full_2009_2009_challenger.jsonl"] == 5
    assert chunk["data/tennis/flashscore_full/flashscore_full_h2h_pass11_shard0.jsonl"] == 6

    root = plan["RAW_DATA_SOURCES.md"]
    assert root.dest == "_repo_root/RAW_DATA_SOURCES.md" and not root.compress
    deep = plan["data/tennis/infosys_deep/2024_data.jsonl"]
    assert deep.dest == "infosys_deep/2024_data.jsonl.gz" and deep.compress
    vision = plan["data/tennis/court_vision/2024/1536_MS001.json.gz"]
    assert vision.dest == "court_vision/2024/1536_MS001.json.gz" and not vision.compress  # already gzip

    order = [e.path for e in entries]
    assert order.index("data/tennis/infosys_deep/2024_data.jsonl") < order.index(
        "data/tennis/infosys_deep/2022_data.jsonl") < order.index("data/tennis/court_vision/2024/1536_MS001.json.gz")
    assert [e.chunk for e in entries] == sorted(e.chunk for e in entries)

    path = tmp_path / "plan.csv"
    H.write_plan(entries, path)
    assert [e.row() for e in H.read_plan(path)] == [e.row() for e in entries]


# --------------------------------------------------------------------------------------
# a fake Hub: /resolve/ redirects like huggingface.co, /files/ serves byte ranges
# --------------------------------------------------------------------------------------
class FakeHub(http.server.BaseHTTPRequestHandler):
    files: dict = {}        # repository path -> (bytes, "lfs" | "git")
    etags: dict = {}        # repository path -> ETag to advertise instead of the true hash
    cut_once: set = set()   # (path, range start) answered with half its bytes, once
    seen: list = []         # (path, range start) of every byte request

    def log_message(self, *args):
        pass

    def do_HEAD(self):
        self._resolve()

    def do_GET(self):
        if self.path.startswith("/files/"):
            self._serve()
        else:
            self._resolve()

    def _resolve(self):
        prefix = f"/datasets/{H.REPO}/resolve/{H.REVISION}/"
        path = urllib.parse.unquote(self.path[len(prefix):]) if self.path.startswith(prefix) else None
        if path not in self.files:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        data, storage = self.files[path]
        true_hash = hashlib.sha256(data).hexdigest() if storage == "lfs" else H.git_blob_sha1(data)
        self.send_response(302 if storage == "lfs" else 307)
        self.send_header("Location", f"/files/{urllib.parse.quote(path)}?Expires={int(time.time()) + 3600}")
        self.send_header("X-Repo-Commit", H.REVISION)
        if storage == "lfs":
            self.send_header("X-Linked-Size", str(len(data)))
        self.send_header("X-Linked-ETag", f'"{self.etags.get(path, true_hash)}"')
        self.send_header("RateLimit", '"resolvers";r=2999;t=100')
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _serve(self):
        path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path[len("/files/"):])
        data, _ = self.files[path]
        match = re.match(r"bytes=(\d+)-(\d+)", self.headers.get("Range", ""))
        start, end = int(match.group(1)), int(match.group(2))
        type(self).seen.append((path, start))
        body = data[start:end + 1]
        self.send_response(206)
        self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if (path, start) in self.cut_once:
            self.cut_once.discard((path, start))
            self.wfile.write(body[: len(body) // 2])  # the connection closes with the body short
            return
        self.wfile.write(body)


@pytest.fixture
def hub(monkeypatch):
    FakeHub.files, FakeHub.etags, FakeHub.cut_once, FakeHub.seen = {}, {}, set(), []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeHub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(H, "HUB", f"http://127.0.0.1:{server.server_address[1]}")
    yield FakeHub
    server.shutdown()
    server.server_close()


def make_context(tmp_path, run_id, retries, receipts=None):
    raw = tmp_path / "raw"
    return H.Context(raw, receipts or C.Receipts(H.SOURCE, root=tmp_path / "receipts"),
                     H.Journal(raw / "_progress.jsonl"), H.RateLimiter(1000), run_id,
                     piece_bytes=10_000, piece_retries=retries)


def entry_for(path, data, storage, compress, hash_value=None):
    hash_algo = "sha256" if storage == "lfs" else "git-sha1"
    real = hashlib.sha256(data).hexdigest() if storage == "lfs" else H.git_blob_sha1(data)
    return H.Entry(path, len(data), storage, hash_algo, hash_value or real, H.source_of(path), 1, 0, "fetch", "",
                   H.dest_of(path, compress), compress)


def test_interrupted_file_resumes_from_its_last_complete_range(tmp_path, hub):
    data = b"".join(json.dumps({"point": i, "pad": "x" * (i % 97)}).encode() + b"\n" for i in range(3000))
    path = "data/tennis/infosys_deep/2024_data.jsonl"
    hub.files = {path: (data, "lfs")}
    hub.cut_once = {(path, 20_000)}
    entry = entry_for(path, data, "lfs", compress=True)
    receipts = C.Receipts(H.SOURCE, root=tmp_path / "receipts")

    first = H.run_fetch([entry], make_context(tmp_path, "run1", retries=0, receipts=receipts), workers=1)
    assert first["files_failed"] == 1 and first["files_done"] == 0
    raw = tmp_path / "raw"
    assert not (raw / entry.dest).exists()
    assert H.Journal(raw / "_progress.jsonl").get(path)["offset"] == 20_000

    hub.seen.clear()
    second = H.run_fetch([entry], make_context(tmp_path, "run2", retries=2, receipts=receipts), workers=1)
    assert second["files_done"] == 1 and second["complete"]
    assert min(start for _, start in hub.seen) == 20_000  # resumed; the first two ranges were not fetched again
    stored = (raw / entry.dest).read_bytes()
    assert gzip.decompress(stored) == data  # one gzip member per range reads back as the original bytes
    receipt = receipts.get(path)
    assert receipt["hash_ok"] and receipt["sha256"] == entry.hash
    assert receipt["resumed_from"] == 20_000
    assert receipt["pieces"] == math.ceil((len(data) - 20_000) / 10_000)
    assert not (raw / (entry.dest + ".part")).exists()


def test_retry_inside_a_run_rolls_back_the_broken_range(tmp_path, hub):
    data = bytes(range(256)) * 200  # 51,200 bytes, stored uncompressed
    path = "data/tennis/api_tennis/fixtures_2024.csv"
    hub.files = {path: (data, "lfs")}
    hub.cut_once = {(path, 30_000)}
    entry = entry_for(path, data, "lfs", compress=False)
    result = H.run_fetch([entry], make_context(tmp_path, "run1", retries=2), workers=1)
    assert result["files_done"] == 1
    assert (tmp_path / "raw" / entry.dest).read_bytes() == data


def test_small_git_file_empty_file_hash_mismatch_and_missing_file(tmp_path, hub):
    small = b'{"completed": [], "total_matches": 12502}'
    other = b"a different body"
    good = "data/tennis/infosys_deep/checkpoint_2024.json"
    empty = "data/tennis/tennis_abstract/player_matches_0.jsonl"
    wrong = "data/tennis/itf_full/checkpoint_dc_api_2023.json"
    hub.files = {good: (small, "git"), wrong: (other, "git")}
    claimed = H.git_blob_sha1(small)
    hub.etags = {wrong: claimed}  # headers agree with the plan, but the bytes served do not
    entries = [entry_for(good, small, "git", compress=False),
               H.Entry(empty, 0, "git", "git-sha1", H.EMPTY_HASHES["git-sha1"], "tennis_abstract", 1, 0, "fetch", "",
                       H.dest_of(empty, False), False),
               entry_for(wrong, other, "git", compress=False, hash_value=claimed)]
    ctx = make_context(tmp_path, "run1", retries=0)
    result = H.run_fetch(entries, ctx, workers=1)
    raw = tmp_path / "raw"
    assert (raw / "infosys_deep/checkpoint_2024.json").read_bytes() == small
    assert (raw / "tennis_abstract/player_matches_0.jsonl").read_bytes() == b""
    bad = ctx.receipts.get(wrong)
    assert "hash mismatch" in bad["error"]
    assert Path(C.PROJECT_ROOT, bad["kept_as"]).exists() or Path(bad["kept_as"]).exists()  # kept, not deleted
    assert result["files_done"] == 2 and result["files_failed"] == 1

    missing = entry_for("data/tennis/infosys_deep/2031_data.jsonl", b"x", "lfs", compress=False)
    ctx2 = make_context(tmp_path, "run2", retries=0, receipts=ctx.receipts)
    stopped = H.run_fetch([missing], ctx2, workers=1)
    assert ctx2.stop.is_set() and "HTTP 404" in stopped["stop_reasons"][0]


# --------------------------------------------------------------------------------------
# status
# --------------------------------------------------------------------------------------
def test_status_counts_done_partial_and_failed(tmp_path):
    raw = tmp_path / "raw"
    receipts = C.Receipts(H.SOURCE, root=tmp_path / "receipts")
    progress = H.Journal(raw / "_progress.jsonl")
    entries = [H.Entry(f"data/tennis/infosys_deep/{y}_data.jsonl", 1_000, "lfs", "sha256", str(y), "infosys_deep", 1,
                       0, "fetch", "", f"infosys_deep/{y}_data.jsonl", False) for y in (2022, 2023, 2024)]
    entries.append(H.Entry("data/tennis/tennis_atp/atp_matches_2020.csv", 10, "git", "git-sha1", "x", "tennis_atp",
                           1, 0, "skip-held", "identical", "tennis_atp/atp_matches_2020.csv", False))
    (raw / "infosys_deep").mkdir(parents=True)
    (raw / "infosys_deep/2024_data.jsonl").write_bytes(b"x")
    receipts.record({"name": entries[2].path, "hash_ok": True, "stored_bytes": 100})
    progress.record(entries[1].path, offset=400, part_bytes=50)
    receipts.record({"name": entries[0].path, "error": "HTTP 503"})
    status = H.compute_status(entries, receipts, progress, raw)
    total = status["total"]
    assert (total["files"], total["done_files"], total["partial_files"], total["failed_files"]) == (3, 1, 1, 1)
    assert total["done_bytes"] == 1_000 and total["stored_bytes"] == 100
    assert status["skipped"] == {"skip-held": 1}
    text = H.render_status(status)
    assert "**1 of 3 files done" in text and "2 files and" in text and "`data/tennis/infosys_deep/2023_data.jsonl`" in text
    running = H.render_status(status, {"run_id": "r1", "started_at": "2026-09-25T14:00:00+00:00", "bytes_received": 5e9})
    assert "no end recorded" in running and "5.00 GB received" in running
    ended = H.render_status(status, {"run_id": "r2", "ended_at": "2026-09-25T15:00:00+00:00", "files_done": 7,
                                     "files_failed": 0, "bytes_received": 1e9, "stop_reasons": []})
    assert "ended 2026-09-25T15:00:00+00:00: 7 files done" in ended and "it finished its list" in ended
