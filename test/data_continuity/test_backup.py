"""Offline tests of the cold-storage backup: reading a zip's entries from its last bytes, the pack and check round
trip through Windows tar, and which zip each file goes to."""
from __future__ import annotations

import base64
import gzip
import hashlib
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.eda.data_continuity import backup as B  # noqa: E402


def test_central_directory_from_the_tail_grows_until_it_fits(tmp_path):
    path = tmp_path / "x.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for i in range(300):
            z.writestr(f"public_dump/f{i:03d}.json", f'{{"i": {i}}}' * (i + 1))
    whole = path.read_bytes()
    asked = []

    def fetch(n):
        asked.append(n)
        return whole[-n:]

    got = B.central_directory(fetch, len(whole), first=64)
    with zipfile.ZipFile(path) as z:
        assert [(i.filename, i.file_size, i.CRC) for i in got] == [(i.filename, i.file_size, i.CRC)
                                                                   for i in z.infolist()]
    assert len(asked) > 1 and asked == sorted(asked)        # the first tail was too short
    with pytest.raises(EOFError):                            # byte 0 is before a 10-byte tail
        B.Tail(whole[-10:], len(whole)).read(4)


@pytest.mark.skipif(not B.TAR.exists(), reason="Windows tar is the restore tool")
def test_pack_then_check_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(B.K, "ROOT", tmp_path)
    files = {"data/raw/src/a.json": b'{"a": 1}\n' * 1000, "data/raw/src/b.json.gz": gzip.compress(b"b" * 5000),
             "data/raw/src/sub/empty.txt": b""}
    for rel, body in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_bytes(body)
    rows = [{"path": rel, "bytes": str(len(body)), "mtime": "", "status": "copy", "where": "w", "sha256": "",
             "crc32": "", "note": ""} for rel, body in files.items()] + [
            {"path": "data/raw/src/gone.json", "bytes": "5", "mtime": "", "status": "copy", "where": "w",
             "sha256": "", "crc32": "", "note": ""}]
    zpath = tmp_path / "t.zip"
    done, stream = B.pack_one((str(zpath), rows))
    by_path = {r["path"]: r for r in done}
    assert by_path["data/raw/src/gone.json"]["status"] == "removed"
    for rel, body in files.items():
        assert by_path[rel]["status"] == "zipped" and by_path[rel]["note"] == ""
        assert by_path[rel]["sha256"] == hashlib.sha256(body).hexdigest()
    with zipfile.ZipFile(zpath) as z:
        kinds = {i.filename: i.compress_type for i in z.infolist()}
    assert kinds["data/raw/src/a.json"] == zipfile.ZIP_DEFLATED
    assert kinds["data/raw/src/b.json.gz"] == zipfile.ZIP_STORED
    with pytest.raises(FileExistsError):                     # never over an existing zip
        B.pack_one((str(zpath), rows[:1]))

    expected = {r["path"]: (int(r["bytes"]), r["crc32"]) for r in done if r["status"] == "zipped"}
    got = B.check_one((str(zpath), expected, stream))
    assert got["files"] == 3 and got["data_bytes"] == sum(map(len, files.values()))
    assert got["md5"] == base64.b64encode(hashlib.md5(zpath.read_bytes()).digest()).decode()
    with pytest.raises(SystemExit):                          # an entry the manifest does not describe
        B.check_one((str(zpath), {**expected, "data/raw/src/a.json": (8000, "00000000")}, stream))
    with pytest.raises(SystemExit):                          # tar's bytes must hash to the packed stream
        B.check_one((str(zpath), expected, {**stream, "stream_sha256": "0" * 64}))


def test_zip_names_and_exclusions():
    day = "2026-10-08"
    assert B.zip_name("data/raw/point_sources/wta/x.json.gz", day) == "tennis_data_raw_2026-10-08.zip"
    assert B.zip_name("data/dump/odds/x.parquet", day) == "tennis_data_dump_2026-10-08.zip"
    for p in ("data/studies/a/b.csv", "data/data_map.yaml", "data/betting_history/x.csv"):
        assert B.zip_name(p, day) == "tennis_data_studies_2026-10-08.zip"
    profile = "data/studies/predictive_frontier_tabpfn/report_qa/edge_desktop_profile/Default/History"
    assert B.excluded_by(profile)[0] == "data/studies/predictive_frontier_tabpfn/report_qa/edge_desktop_profile/"
    assert B.excluded_by("data/backups/2026-10-08/tennis_data_raw_2026-10-08.zip")[0] == "data/backups/"
    assert B.excluded_by("data/studies/predictive_frontier_tabpfn/report_qa/report.html") is None


def test_scan_keeps_to_the_groups(tmp_path, monkeypatch):
    monkeypatch.setattr(B.K, "ROOT", tmp_path)
    monkeypatch.setattr(B, "DATA", tmp_path / "data")
    for rel in ("data/raw/s/a.json", "data/dump/odds/b.parquet", "data/studies/x/c.csv", "data/README.md",
                "data/betting_history/d.csv"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_bytes(b"x")

    def paths(groups):
        return sorted(f["path"] for f in B.scan(groups)[0])

    assert paths(("raw", "dump")) == ["data/dump/odds/b.parquet", "data/raw/s/a.json"]
    assert paths(("studies",)) == ["data/README.md", "data/betting_history/d.csv", "data/studies/x/c.csv"]
    assert len(paths(B.GROUPS)) == 5


def test_readme_names_the_scope_and_the_earlier_zips_oldest_first():
    s = {"made": "2026-10-29", "snapshot": "2026-10-29T16:00:00+00:00", "origin": "https://github.com/o/r.git",
         "head": "9228b26fce26594429d048884456053481062717", "groups": ["raw", "dump"],
         "bucket": f"{B.BUCKET}/data/2026-10-29/", "by_status": {"zipped": {"files": 2, "bytes": 3}},
         "zips": [{"zip": "tennis_data_raw_2026-10-29.zip", "files": 2, "data_bytes": 3, "bytes": 4, "sha256": "ab"}],
         "earlier_zips": {f"{B.BUCKET}/data/2026-10-08/tennis_data_raw_2026-10-08.zip": {"files": 1, "bytes": 1},
                          f"{B.BUCKET}/public_dump/tennis_public_dump_raw_2026-09-22.zip": {"files": 1, "bytes": 1}},
         "unreadable": [], "removed": [], "excluded": {}, "changed_while_read": []}
    text = B.readme(s)
    assert "copy of the files in data\\raw\\ and data\\dump\\ that GitHub" in text
    assert "Restore data\\raw\\ and data\\dump\\:" in text and "Scope:    data\\raw\\ and data\\dump\\ only" in text
    order = [text.index(t) for t in ("tar -x -f tennis_public_dump_raw_2026-09-22.zip -C <repo>\\data\\raw\n",
                                     "tar -x -f tennis_data_raw_2026-10-08.zip -C <repo>\n",
                                     "tar -x -f tennis_data_raw_2026-10-29.zip -C <repo>\n")]
    assert order == sorted(order)
    old = B.readme({k: v for k, v in s.items() if k != "groups"})    # a summary from before --groups: all of data/
    assert "Restore data\\ completely:" in old and "Scope:" not in old
