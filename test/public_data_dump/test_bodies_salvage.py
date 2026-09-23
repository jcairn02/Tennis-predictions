"""The raw Polymarket bodies store must survive a run killed mid-write (damaged gzip member)."""
import gzip
import json
import sys
import zlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.public_dump import polymarket_prices as P  # noqa: E402


def member(lines):
    return gzip.compress(("".join(json.dumps(l) + "\n" for l in lines)).encode("utf-8"))


def test_iter_body_lines_skips_damaged_member_and_keeps_intact_ones(tmp_path):
    import os

    noise = lambda n: os.urandom(n).hex()  # incompressible, so truncation removes real content
    good1 = member([{"name": "1/0", "body": noise(1500)}, {"name": "2/0", "body": noise(1500)}])
    full = member([{"name": "3/0", "body": noise(30000)}, {"name": "4/0", "body": noise(30000)}])
    assert len(full) > 20000
    damaged = full[: int(len(full) * 0.7)]  # cut inside the second record
    good2 = member([{"name": "5/0", "body": noise(1500)}])
    path = tmp_path / "bucket.jsonl.gz"
    path.write_bytes(good1 + damaged + good2)
    with gzip.open(path, "rt", encoding="utf-8") as handle:  # the standard reader cannot get past the damage
        try:
            handle.read()
            standard_ok = True
        except (EOFError, zlib.error):
            standard_ok = False
    assert standard_ok is False
    report = {}
    names = []
    for line in P.iter_body_lines(path, report):
        try:
            names.append(json.loads(line)["name"])
        except json.JSONDecodeError:
            names.append("<garbage>")  # a damaged member may emit one unparseable line; consumers skip it
    assert names[:2] == ["1/0", "2/0"] and names[-1] == "5/0"
    assert "4/0" not in names  # the partial tail of the damaged member is dropped
    assert report["damaged_members"] == 1
    stored = P.names_with_bodies(tmp_path)
    assert {"1/0", "2/0", "5/0"} <= stored and "4/0" not in stored


def test_iter_body_lines_reads_clean_multi_member_file(tmp_path):
    path = tmp_path / "ok.jsonl.gz"
    path.write_bytes(member([{"name": "a"}]) + member([{"name": "b"}, {"name": "c"}]))
    report = {}
    assert [json.loads(l)["name"] for l in P.iter_body_lines(path, report)] == ["a", "b", "c"]
    assert report["damaged_members"] == 0
