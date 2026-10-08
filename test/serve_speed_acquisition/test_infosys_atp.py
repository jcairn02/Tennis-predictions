"""The ATP Stats Centre download (offline): the plan from ManTennisData's links, calibration, discovery and expansion
against a fake host, the files kept exactly as served, and no decryption anywhere."""
import base64
import csv
import gzip
import json
import sys
from argparse import ArgumentParser
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import feeds as F  # noqa: E402
from src.ingest.point_sources import infosys_atp as A  # noqa: E402

DENIED = (b'<?xml version="1.0" encoding="UTF-8"?>\n'
          b"<Error><Code>AccessDenied</Code><Message>Access Denied</Message></Error>")


# ----------------------------------------------------------------------------------- the plan
@pytest.mark.parametrize("url, code", [
    ("https://www.atptour.com/en/scores/2018/339/QS012/match-stats?isLive=False", (2018, 339, "QS012")),
    ("https://www.atptour.com/en/scores/match-stats/archive/2019/6116/MS014", (2019, 6116, "MS014")),
    ("https://www.atptour.com/en/scores/stats-centre/archive/2021/9428/ms052", (2021, 9428, "MS052")),
    ("https://www.atptour.com/en/scores/archive/doha/451/1999/results", None),
    ("", None),
    (None, None),
])
def test_code_of(url, code):
    assert A.code_of(url) == code


def test_code_order_puts_the_final_first_and_qualifying_last():
    codes = ["QS002", "MS016", "QS001", "MS001", "MS002"]
    assert sorted(codes, key=A.code_order) == ["MS001", "MS002", "MS016", "QS001", "QS002"]


def test_parse_years():
    assert A.parse_years("2020,2019,2015-2017") == [2020, 2019, 2015, 2016, 2017]
    assert A.parse_years("2018, 2018") == [2018]


def link(year, event, code, form=0):
    return [f"https://www.atptour.com/en/scores/{year}/{event}/{code}/match-stats?isLive=False",
            f"https://www.atptour.com/en/scores/match-stats/archive/{year}/{event}/{code}",
            f"https://www.atptour.com/en/scores/stats-centre/archive/{year}/{event}/{code.lower()}"][form]


def write_mtd(root: Path) -> None:
    """A small ManTennisData: three tour-level events of 2018, a Slam, a Challenger and an event after the window."""
    root.mkdir(parents=True, exist_ok=True)
    tours = [("2018-605", "Nitto ATP Finals", "atp", "atpFinal", "20181111"),
             ("2018-339", "Brisbane", "atp", "atp250", "20171231"),
             ("2018-418", "Washington", "atp", "atp500", "20180730"),
             ("2018-580", "Australian Open", "gs", "gs", "20180115"),
             ("2018-1763", "Genoa", "ch", "ch50", "20180827"),
             ("2018-352", "Paris", "1000", "1000", "20181029")]
    pq.write_table(pa.table({k: [t[i] for t in tours] for i, k in
                             enumerate(["id", "name", "series_id", "series_category_id", "start_dtm"])}),
                   root / "atp_tournaments.parquet")
    rows = [("2018-605", link(2018, 605, c, i % 3)) for i, c in enumerate(["MS001", "MS002", "MS003", "MS008", "MS009"])]
    rows += [("2018-339", link(2018, 339, c)) for c in ["MS002", "QS001", "MS001"]] + [("2018-339", "")]
    rows += [("2018-418", link(2018, 418, c, 1)) for c in ["QS003", "MS001", "MS002", "MS003", "QS001", "QS002"]]
    rows += [("2018-580", link(2018, 580, "MS001")), ("2018-1763", link(2018, 1763, "MS001")),
             ("2018-352", link(2018, 352, "MS001"))]
    pq.write_table(pa.table({"tournament_id": [r[0] for r in rows], "stats_url": [r[1] for r in rows]}),
                   root / "atp_matches_2018.parquet")


def test_load_plan(tmp_path):
    write_mtd(tmp_path)
    plan = A.load_plan([2018], "20150101", "20181031", root=tmp_path)
    assert [(e.event, e.level) for e in plan] == [(339, "atp250"), (418, "atp500"), (352, "1000")]  # by start date
    brisbane, washington, paris = plan
    assert brisbane.codes == ["MS001", "MS002", "QS001"] and brisbane.uncoded == 1
    assert washington.codes == ["MS001", "MS002", "MS003", "QS001", "QS002", "QS003"]
    assert paris.codes == ["MS001"]
    assert [e.event for e in A.load_plan([2018], "20150101", "20211017", {605}, root=tmp_path)] == [605]
    finals = A.load_plan([2018], "20150101", "20211017", {605}, root=tmp_path)[0]
    assert finals.codes == ["MS001", "MS002", "MS003", "MS008", "MS009"]  # all three link forms read


def test_urls_and_paths():
    assert A.url_of(2018, 605, "keystats", "MS001") == \
        "https://itp-atp-sls.infosys-platforms.com/static/prod/stats-plus/2018/605/MS001/keystats.json"
    assert A.url_of(2020, 8888, "court-vision", "MS101") == \
        "https://itp-atp-sls.infosys-platforms.com/static/prod/court-vision/2020/8888/MS101/data.json"
    assert A.dest_of(2018, 605, "match-beats", "MS001").as_posix().endswith(
        "data/raw/point_sources/infosys_atp/2018/605/match-beats/MS001.json.gz")


# ----------------------------------------------------------------------------------- envelopes
@pytest.mark.parametrize("body, ok", [
    (b'{"lastModified": 1, "response": "x", "data": null}', True),
    (b'{"message": "Match Not Found"}', False),
    (b"<html>blocked</html>", False),
    (b"[1, 2]", False),
])
def test_envelope_validator(body, ok):
    assert (A.envelope_validator(body) is None) == ok


def test_envelope_facts_read_plain_fields_only():
    whole = base64.b64encode(bytes(range(32))).decode()
    facts = A.envelope_facts({"lastModified": 1542585600000, "response": whole, "data": None})
    assert facts == {"last_modified": 1542585600000, "last_modified_utc": "2018-11-19T00:00:00+00:00",
                     "response_chars": len(whole), "aes_blocks_whole": True, "data_null": True}
    assert not A.envelope_facts({"lastModified": 1, "response": base64.b64encode(bytes(30)).decode()})["aes_blocks_whole"]
    assert not A.envelope_facts({"lastModified": 1, "response": "not base64!"})["aes_blocks_whole"]
    assert A.envelope_facts("not a dict")["response_chars"] == 0


def test_the_module_cannot_decrypt():
    source = Path(A.__file__).read_text(encoding="utf-8")
    for marker in ("Crypto", "AES.new", "infosys_slams", "key_iv", "decrypt("):
        assert marker not in source
    assert not hasattr(A, "decrypt")


class FakeResponse:
    def __init__(self, url, status, content=b"", ctype="application/json"):
        self.url, self.status_code, self.content = url, status, content
        self.headers = {"content-type": ctype}


class FakeReceipts:
    def __init__(self, recs):
        self._recs = recs

    def all(self):
        return self._recs


def test_calibration_reads_s3_403_as_absent_only_on_a_route_that_served_a_file():
    cal = A.Calibration(FakeReceipts({"2025/352/keystats/MS001": {"status": 200},
                                      "2022/605/match-beats/MS001": {"status": 403, "error": "HTTP 403"}}))
    denied = FakeResponse("u", 403, DENIED, "application/xml")
    cal.current = "keystats"
    assert cal.not_found(denied)
    assert cal.not_found(FakeResponse("u", 403, b"<html>Request blocked</html>", "text/html")) is None
    cal.current = "match-beats"  # never served a file yet
    assert cal.not_found(denied) is None
    assert cal.not_found(FakeResponse("u", 200, b"{}")) is None


# ----------------------------------------------------------------------------------- a run against a fake host
class FakeHost:
    """S3 behind CloudFront: a file where one is held, else 403 AccessDenied; ``refuse`` answers a 403 HTML page."""

    def __init__(self, files, refuse=()):
        self.files, self.refuse, self.calls = files, set(refuse), []

    def get(self, url, timeout=None, allow_redirects=None, headers=None):
        self.calls.append((url, headers))
        if url in self.refuse:
            return FakeResponse(url, 403, b"<html>Request blocked</html>", "text/html")
        if url in self.files:
            return FakeResponse(url, 200, self.files[url])
        return FakeResponse(url, 403, DENIED, "application/xml")


def envelope(tag: str) -> bytes:
    cipher = base64.b64encode(tag.encode().ljust(48, b"#")).decode()
    return json.dumps({"lastModified": 1542585600000, "response": cipher, "data": None}).encode()


HELD = [*[(y, e, r, m) for r, (y, e, m) in A.CALIBRATION.items()],
        (2018, 605, "keystats", "MS001"), (2018, 605, "keystats", "MS002"), (2018, 605, "keystats", "MS008"),
        (2018, 605, "court-vision", "MS001"), (2018, 605, "court-vision", "MS003"),
        (2018, 418, "keystats", "MS002")]


def setup_run(tmp_path, monkeypatch, refuse=(), held=HELD):
    write_mtd(tmp_path / "mtd")
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(A, "STUDY_ROOT", tmp_path / "study")
    monkeypatch.setattr(A, "MTD_ROOT", tmp_path / "mtd")
    files = {A.url_of(*h): envelope("/".join(map(str, h))) for h in held}
    host = FakeHost(files, refuse)
    monkeypatch.setattr(A, "make_client", lambda args, cal: F.FeedClient(
        "chrome", not_found=cal.not_found, min_interval=0, jitter=0, max_requests=args.max_requests, session=host))
    return host, files


def args_for(*argv):
    parser = ArgumentParser()
    A.add_arguments(parser)
    return parser.parse_args(["--years", "2018", "--until", "20181231", "--skip-after", "2", *argv])


def test_run_discovers_expands_and_keeps_files_as_served(tmp_path, monkeypatch):
    host, files = setup_run(tmp_path, monkeypatch)
    summary = A.run(args_for())
    assert "stopped" not in summary and summary["receipts_with_errors"] == 0
    assert all(h["Origin"] == "https://www.atptour.com" for _, h in host.calls)
    asked = [url.split("/prod/")[1] for url, _ in host.calls]
    # calibration, then discovery: Brisbane (empty) costs the final on 4 routes plus the semi-final on 2
    assert asked[:4] == ["stats-plus/2025/352/MS001/keystats.json", "match-beats/2022/605/MS001/data.json",
                         "rally-analysis/2022/605/MS001/data.json", "court-vision/2022/605/MS001/data.json"]
    assert sum("/2018/339/" in a for a in asked) == 6
    # Washington's final has nothing, but its semi-final has key statistics, so it is expanded
    assert "stats-plus/2018/418/MS003/keystats.json" in asked
    # the ATP Finals: every code on the two routes that served the final; the others given up after 2 absences
    for code in ("MS002", "MS003", "MS008", "MS009"):
        assert f"stats-plus/2018/605/{code}/keystats.json" in asked
        assert f"court-vision/2018/605/{code}/data.json" in asked
    assert "match-beats/2018/605/MS003/data.json" not in asked
    # Paris has one code: its final on 4 routes, no semi-final to ask
    assert sum("/2018/352/" in a for a in asked) == 4
    assert len(asked) == 45 == len(set(asked))  # nothing asked twice
    assert summary["files_held"] == 10 and summary["files_held_in_plan"] == 6
    given_up = {(n["event"], n["route"], n["family"]) for n in summary["families_given_up"]}
    assert ("2018/418", "keystats", "QS") in given_up and ("2018/605", "match-beats", "MS") in given_up
    assert ("2018/605", "keystats", "MS") not in given_up
    # every file is the served envelope, byte for byte (gzipped), never decrypted
    for h in HELD:
        assert gzip.decompress(A.dest_of(*h).read_bytes()) == files[A.url_of(*h)]
    with (tmp_path / "study" / "infosys_atp_events.csv").open(encoding="utf-8") as fh:
        states = {int(r["event_id"]): r for r in csv.DictReader(fh)}
    assert {e: r["state"] for e, r in states.items()} == {339: "empty", 418: "files", 352: "empty", 605: "files"}
    assert states[605]["files_keystats"] == "3" and states[605]["files_court-vision"] == "2"
    assert states[339]["uncoded_rows"] == "1"
    with (tmp_path / "study" / "infosys_atp_files.csv").open(encoding="utf-8") as fh:
        held = list(csv.DictReader(fh))
    assert len(held) == 10 and sum(r["purpose"] == "calibration" for r in held) == 4
    assert all(r["aes_blocks_whole"] == "True" and r["last_modified"] == "1542585600000" for r in held)

    rerun = A.run(args_for())  # everything is cached: no request
    assert rerun["client"]["requests"] == 0 and len(host.calls) == 45
    assert rerun["files_held"] == 10


def test_discover_phase_stops_before_expanding(tmp_path, monkeypatch):
    host, _ = setup_run(tmp_path, monkeypatch)
    summary = A.run(args_for("--phase", "discover"))
    assert summary["events_with_files_found"] == 2
    assert len(host.calls) == 4 + 6 + 6 + 4 + 4  # calibration, Brisbane, Washington, Paris, the ATP Finals


def test_a_refusal_stops_the_run_and_is_reported(tmp_path, monkeypatch):
    refuse = [A.url_of(2018, 339, "match-beats", "MS001")]
    host, _ = setup_run(tmp_path, monkeypatch, refuse=refuse)
    summary = A.run(args_for())
    assert summary["stopped"].startswith("Blocked: HTTP 403")
    assert host.calls[-1][0] == refuse[0]


def test_a_missing_calibration_file_stops_the_run(tmp_path, monkeypatch):
    host, _ = setup_run(tmp_path, monkeypatch, held=[h for h in HELD if h[2] != "court-vision"])
    summary = A.run(args_for())
    assert summary["stopped"].startswith("Blocked") and len(host.calls) == 4
