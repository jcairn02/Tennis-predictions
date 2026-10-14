"""Offline tests for the Match Charting adapter across commits (no network): a later commit's changed files replace the
held ones, whose bytes are kept under superseded/; unchanged files are not fetched again; a body that is not the
tree's blob is refused; a held file the new tree lacks is reported."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.public_dump import common as C  # noqa: E402
from src.ingest.public_dump import match_charting as M  # noqa: E402

A, B = "a" * 40, "b" * 40
MATCHES_A = b"match_id,Player 1,Player 2\n20260101-M-X,A,B\n"
MATCHES_B = MATCHES_A + b"20260918-M-Y,C,D\n"
POINTS = b"match_id,Pt,Set1\n20260101-M-X,1,0\n"
README = b"# Match Charting Project\n"


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class FakeResponse:
    def __init__(self, status, content=b"", url="http://x"):
        self.status_code = status
        self.content = content
        self.url = url
        self.headers = {"Content-Type": "text/plain"}


class FakeSite:
    def __init__(self):
        self.pages, self.requested = {}, []

    def serve(self, commit: str, files: dict, tree_blobs: dict | None = None) -> None:
        """One commit: its tree (blob SHA-1s of ``files``, or ``tree_blobs`` where given) and its raw files."""
        tree = {"sha": commit, "truncated": False, "tree": [
            {"path": p, "type": "blob", "sha": (tree_blobs or {}).get(p, blob(body)), "size": len(body)}
            for p, body in files.items()]}
        self.pages[M.TREE_URL.format(repo=M.REPO, commit=commit)] = json.dumps(tree).encode()
        for path, body in files.items():
            self.pages[M.RAW_URL.format(repo=M.REPO, commit=commit, path=path)] = body

    def get(self, url, timeout=None):
        self.requested.append(url)
        return FakeResponse(200, self.pages[url], url) if url in self.pages else FakeResponse(404, b"", url)


def setup(tmp_path, monkeypatch) -> FakeSite:
    monkeypatch.setattr(C, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(C, "DUMP_ROOT", tmp_path / "dump")
    monkeypatch.setattr(C, "PROJECT_ROOT", tmp_path)
    site = FakeSite()
    monkeypatch.setattr(C, "session", lambda: site)
    return site


def run(commit: str) -> dict:
    return M.run(argparse.Namespace(refresh=False, mcp_commit=commit, mcp_all_eras=False))


def raw_requests(site: FakeSite) -> list[str]:
    return [u for u in site.requested if u.startswith("https://raw.githubusercontent.com/")]


def test_a_later_commit_replaces_changed_files_and_keeps_the_earlier_bytes(tmp_path, monkeypatch):
    site = setup(tmp_path, monkeypatch)
    site.serve(A, {"charting-m-matches.csv": MATCHES_A, "charting-m-points-2020s.csv": POINTS, "README.md": README})
    assert run(A)["files"] == {"downloaded": 3}
    site.serve(B, {"charting-m-matches.csv": MATCHES_B, "charting-m-points-2020s.csv": POINTS, "README.md": README})
    site.requested.clear()
    second = run(B)
    folder = tmp_path / "raw" / M.SOURCE
    assert second["files"] == {"changed, previous kept": 1, "held, unchanged": 2}
    assert raw_requests(site) == [M.RAW_URL.format(repo=M.REPO, commit=B, path="charting-m-matches.csv")]
    assert (folder / "charting-m-matches.csv").read_bytes() == MATCHES_B
    kept = [p for p in (folder / "superseded").glob("charting-m-matches.*.csv")]
    assert len(kept) == 1 and kept[0].read_bytes() == MATCHES_A                       # commit A's file stays
    meta = json.loads((kept[0].parent / (kept[0].name + ".meta.json")).read_text(encoding="utf-8"))
    assert meta["receipt"]["commit"] == A and meta["replaced_by_sha256"] == C.sha256_bytes(MATCHES_B)
    receipts = C.Receipts(M.SOURCE)
    assert receipts.get("charting-m-matches.csv")["commit"] == B
    assert receipts.get("charting-m-matches.csv")["git_blob_sha1"] == blob(MATCHES_B)
    assert receipts.get("charting-m-points-2020s.csv")["commit"] == A               # unchanged: not fetched again
    assert (folder / f"_tree_{A[:12]}.json").exists() and (folder / f"_tree_{B[:12]}.json").exists()
    staged = pq.read_table(tmp_path / "dump" / "points" / M.SOURCE / "metadata" / "charting-m-matches.parquet")
    assert staged.num_rows == 2 and second["staged_files"] == 1                    # only the changed file re-staged
    assert second["not_in_this_commit"] == []


def test_receipts_without_a_blob_hash_are_checked_against_the_file(tmp_path, monkeypatch):
    site = setup(tmp_path, monkeypatch)
    site.serve(A, {"charting-w-matches.csv": MATCHES_A})
    folder = tmp_path / "raw" / M.SOURCE
    folder.mkdir(parents=True)
    (folder / "charting-w-matches.csv").write_bytes(MATCHES_A)                     # held before receipts had blobs
    C.Receipts(M.SOURCE).record({"name": "charting-w-matches.csv", "url": "u", "commit": A, "sha256": C.sha256_bytes(MATCHES_A),
                                 "retrieved_at": "2026-09-22T21:25:32+00:00"})
    assert run(A)["files"] == {"held, unchanged": 1} and raw_requests(site) == []


def test_a_body_that_is_not_the_trees_blob_is_refused(tmp_path, monkeypatch):
    site = setup(tmp_path, monkeypatch)
    site.serve(A, {"charting-m-matches.csv": MATCHES_A}, tree_blobs={"charting-m-matches.csv": blob(MATCHES_B)})
    summary = run(A)
    assert summary["files"] == {"error": 1}
    assert not (tmp_path / "raw" / M.SOURCE / "charting-m-matches.csv").exists()
    assert C.Receipts(M.SOURCE).get("charting-m-matches.csv")["error"] == "git blob SHA-1 differs from the tree"


def test_a_held_file_the_new_tree_lacks_is_kept_and_reported(tmp_path, monkeypatch):
    site = setup(tmp_path, monkeypatch)
    site.serve(A, {"charting-m-matches.csv": MATCHES_A, "charting-m-points-2020s.csv": POINTS})
    run(A)
    site.serve(B, {"charting-m-matches.csv": MATCHES_A})
    second = run(B)
    assert second["not_in_this_commit"] == ["charting-m-points-2020s.csv"]
    assert (tmp_path / "raw" / M.SOURCE / "charting-m-points-2020s.csv").read_bytes() == POINTS
