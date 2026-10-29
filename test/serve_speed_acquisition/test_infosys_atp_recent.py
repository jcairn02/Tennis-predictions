"""Work package P9's ATP Stats Centre collector and staging (offline): the plan with the Challengers, what other
folders hold, sharing the host with the daily collector, a run against a fake host (calibration, discovery, expansion,
the API routes, nothing fetched twice, files kept as served), and staging by real decryption with its guard."""
import base64
import datetime as dt
import gzip
import json
import sys
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import infosys_atp as A  # noqa: E402
from src.ingest.point_sources import infosys_atp_recent as R  # noqa: E402
from src.ingest.point_sources import infosys_atp_recent_stage as S  # noqa: E402
from src.ingest.point_sources import infosys_slams as I  # noqa: E402

DENIED = (b'<?xml version="1.0" encoding="UTF-8"?>\n'
          b"<Error><Code>AccessDenied</Code><Message>Access Denied</Message></Error>")
LM = 1780000000999


def encrypt(obj, last_modified: int = LM) -> dict:
    """An envelope as the Infosys hosts serve it (test_acquisition_adapters.encrypt)."""
    from Crypto.Cipher import AES

    key, iv = I.key_iv(last_modified)
    plain = json.dumps(obj).encode("utf-8")
    pad = 16 - len(plain) % 16
    cipher = AES.new(key, AES.MODE_CBC, iv).encrypt(plain + bytes([pad]) * pad)
    return {"lastModified": last_modified, "response": base64.b64encode(cipher).decode("ascii"), "data": None}


def link(year, event, code):
    return f"https://www.atptour.com/en/scores/stats-centre/archive/{year}/{event}/{code.lower()}"


def write_mtd(root: Path) -> None:
    """2025: a 250, a Masters, a Challenger and a Slam (not on this host); 2026: a 250 and a Challenger."""
    root.mkdir(parents=True, exist_ok=True)
    tours = [("2025-418", "Washington", "atp", "atp500", "20250728"),
             ("2025-5014", "Shanghai", "1000", "1000", "20251001"),
             ("2025-2907", "Nottingham", "ch", "ch100", "20250106"),
             ("2025-580", "Australian Open", "gs", "gs", "20250112"),
             ("2026-421", "Canada", "1000", "1000", "20260801"),
             ("2026-1763", "Genoa", "ch", "ch125", "20260907")]
    pq.write_table(pa.table({k: [t[i] for t in tours] for i, k in
                             enumerate(["id", "name", "series_id", "series_category_id", "start_dtm"])}),
                   root / "atp_tournaments.parquet")
    r25 = [("2025-418", link(2025, 418, c)) for c in ["MS001", "MS002", "MS003", "QS001"]] + [("2025-418", "")]
    r25 += [("2025-5014", link(2025, 5014, c)) for c in ["MS001", "MS002"]]
    r25 += [("2025-2907", link(2025, 2907, c)) for c in ["MS001", "MS002", "MS003", "QS001", "QS002"]]
    r25 += [("2025-580", link(2025, 580, "MS001"))]
    pq.write_table(pa.table({"tournament_id": [r[0] for r in r25], "stats_url": [r[1] for r in r25]}),
                   root / "atp_matches_2025.parquet")
    r26 = [("2026-421", link(2026, 421, c)) for c in ["MS001", "MS002"]]
    r26 += [("2026-1763", link(2026, 1763, c)) for c in ["MS001", "MS002", "QS001"]]
    pq.write_table(pa.table({"tournament_id": [r[0] for r in r26], "stats_url": [r[1] for r in r26]}),
                   root / "atp_matches_2026.parquet")


# ----------------------------------------------------------------------------------- the plan
def test_plan_adds_challengers_tour_level_first_newest_first(tmp_path):
    write_mtd(tmp_path)
    plan = R.load_plan([2025, 2026], "20250101", "20261016", root=tmp_path)
    assert [(e.year, e.event, e.series) for e in plan] == [
        (2026, 421, "1000"), (2025, 5014, "1000"), (2025, 418, "atp"), (2026, 1763, "ch"), (2025, 2907, "ch")]
    assert plan[2].codes == ["MS001", "MS002", "MS003", "QS001"] and plan[2].uncoded == 1
    # the backfill adapter's own plan keeps its tour-level default
    assert [e.event for e in A.load_plan([2025], "20250101", "20261016", root=tmp_path)] == [418, 5014]
    assert R.load_plan([2025, 2026], "20250101", "20261016", series=("ch",), root=tmp_path,
                       events={(2025, 2907)})[0].codes == ["MS001", "MS002", "MS003", "QS001", "QS002"]


def test_urls_and_paths():
    assert R.url_of(2026, 421, "keystats-api", "MS001") == \
        "https://itp-atp-sls.infosys-platforms.com/prod/api/stats-plus/v1/keystats/year/2026/eventId/421/matchId/MS001"
    assert R.url_of(2025, 418, "match-beats-api", "QS001") == \
        "https://itp-atp-sls.infosys-platforms.com/prod/api/match-beats/data/year/2025/eventId/418/matchId/QS001"
    assert R.dest_of(2025, 418, "court-vision", "MS001").as_posix().endswith(
        "data/raw/point_sources/infosys_atp_recent/2025/418/court-vision/MS001.json.gz")
    assert R.parse_events("2025:418, 2026:1763") == {(2025, 418), (2026, 1763)}


# ----------------------------------------------------------------------------------- what other folders hold
def fake_folder(root: Path, name: str, recs: list[tuple[str, int]]) -> Path:
    folder = root / name
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "_receipts.jsonl").open("w", encoding="utf-8") as fh:
        for rname, status in recs:
            dest = folder / f"{rname}.json.gz"
            if status == 200:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(gzip.compress(b"{}"))
            fh.write(json.dumps({"name": rname, "status": status, "dest": dest.as_posix()}) + "\n")
    return folder


def test_held_elsewhere_reads_both_folders_and_only_completed_daily_matches(tmp_path):
    back = fake_folder(tmp_path, "infosys_atp", [("2025/352/keystats/MS001", 200), ("2023/1202/match-beats/MS027", 200),
                                                ("2023/1202/rally-analysis/MS027", 404)])
    daily = fake_folder(tmp_path, "infosys_atp_daily", [("2026/5014/keystats-api/MS004", 200),
                                                       ("2026/5014/keystats-api/MS005", 200),
                                                       ("2026/5014/keystats-api/MS009", 404)])
    held = R.held_elsewhere({"infosys_atp": back, "infosys_atp_daily": daily},
                            complete=lambda: {(2026, 5014, "MS004")})
    assert held[(2025, 352, "keystats", "MS001")] == "infosys_atp"
    assert held[(2025, 352, "keystats-api", "MS001")] == "infosys_atp"       # the same document by the API
    assert held[(2023, 1202, "match-beats", "MS027")] == "infosys_atp"
    assert (2023, 1202, "rally-analysis", "MS027") not in held                # absent there: not held
    assert held[(2026, 5014, "keystats", "MS004")] == "infosys_atp_daily"
    assert (2026, 5014, "keystats", "MS005") not in held                      # fetched while being played
    held = R.held_elsewhere({"infosys_atp_daily": daily}, complete=lambda: None)   # staging unreadable: all served
    assert (2026, 5014, "keystats-api", "MS005") in held


# ----------------------------------------------------------------------------------- sharing the host
@pytest.mark.parametrize("cmd, age, found", [
    (["python.exe", "src/ingest/speed_daily.py", "--max-requests", "200"], 5, "the daily speed job"),
    (["pythonw.exe", "-m", "src.ingest.scheduled"], 60, "the daily task's first 20 minutes"),
    (["pythonw.exe", "-m", "src.ingest.scheduled"], 30 * 60, None),             # past the speed job
    (["pythonw.exe", "-m", "src.ingest.scheduled", "--weekly"], 60, None),     # the lower-level feed: other hosts
    (["python.exe", "src/eda/daily_prediction/dp.py", "run_day", "--run", "x", "--refresh"], 5,
     "a bet-day run's box-score fills"),
    (["python.exe", "src/eda/daily_prediction/dp.py", "run_day", "--run", "x", "--replay-week", "2026-07-13"], 5,
     None),
    (["python.exe", "src/eda/prediction_run/run.py", "--refresh", "--matchups", "m.csv"], 5,
     "a prediction run's refresh"),
    (["python.exe", "-m", "src.ingest.point_sources.infosys_atp", "--years", "2021"], 5,
     "the 2015-2021 backfill adapter"),
    (["python.exe", "-m", "src.ingest.point_sources.infosys_atp"], 5, "the 2015-2021 backfill adapter"),
    (["python.exe", "-m", "src.ingest.point_sources.infosys_atp_stage"], 5, None),
    (["python.exe", "-m", "src.ingest.point_sources.infosys_challengers", "--stop-at", "11:40"], 5,
     "the P6 Challenger download"),
    (["python.exe", "-m", "src.ingest.point_sources.sofascore_editions", "--gap", "itf_detail"], 5, None),
])
def test_job_running(cmd, age, found):
    got = R.job_running([(1, cmd, age)])
    assert (got is None) if found is None else got.startswith(found)
    assert R.job_running([(7, cmd, age)], own_pid=7) is None


def test_other_collector_ignores_staging_and_plan_runs():
    fetch = (2, ["python.exe", "-m", "src.ingest.point_sources.infosys_atp_recent", "--max-requests", "9"], 1)
    stage = (3, ["python.exe", "-m", "src.ingest.point_sources.infosys_atp_recent", "--stage-only"], 1)
    stager = (4, ["python.exe", "-m", "src.ingest.point_sources.infosys_atp_recent_stage"], 1)
    assert R.other_collector([fetch, stage, stager], own_pid=99).startswith("pid 2")
    assert R.other_collector([stage, stager], own_pid=99) is None
    assert R.other_collector([fetch], own_pid=2) is None


def test_quiet_window():
    w = R.parse_window("07:20-08:00")
    assert R.in_window(dt.datetime(2026, 10, 17, 7, 30), w)
    assert not R.in_window(dt.datetime(2026, 10, 17, 8, 0), w)
    assert not R.in_window(dt.datetime(2026, 10, 17, 7, 19), w)
    wrap = R.parse_window("23:30-00:30")
    assert R.in_window(dt.datetime(2026, 10, 17, 0, 10), wrap) and not R.in_window(dt.datetime(2026, 10, 17, 1), wrap)
    assert R.parse_window("off") is None and not R.in_window(dt.datetime(2026, 10, 17, 7, 30), None)


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def test_host_share_waits_for_the_window_the_daily_receipts_and_a_job(tmp_path):
    clock = Clock()
    receipts = tmp_path / "_receipts.jsonl"
    receipts.write_text("{}\n")
    import os
    os.utime(receipts, (clock.t - 3600, clock.t - 3600))
    jobs = {"on": False}
    procs = lambda: [(5, ["python.exe", "src/ingest/speed_daily.py"], 1)] if jobs["on"] else []  # noqa: E731
    start = dt.datetime(2026, 10, 17, 7, 10)
    now = lambda: start + dt.timedelta(seconds=clock.t - 1_000_000.0)  # noqa: E731
    share = R.HostShare(window=R.parse_window("07:20-08:00"), daily_receipts=receipts, procs=procs, now=now,
                        clock=clock, sleep=clock.sleep, log=lambda m: None)
    share.wait()                                   # 07:10, nothing on the host: no wait
    assert clock.t == 1_000_000.0
    clock.t += 15 * 60                             # 07:25: the window
    share.wait()
    assert now().time() >= dt.time(8, 0) and share.waits["quiet window"] > 0
    os.utime(receipts, (clock.t - 60, clock.t - 60))   # the daily collector wrote a minute ago
    t0 = clock.t
    share.wait()
    assert clock.t - t0 >= 240 and share.waits["daily receipts"] > 0
    jobs["on"] = True
    t0 = clock.t
    share._last_scan = -1e18
    share.sleep = lambda s: (clock.sleep(s), jobs.update(on=clock.t - t0 < 300))   # the job ends after 5 minutes
    share.wait()
    assert 300 <= clock.t - t0 <= 400 and share.waits["another job"] > 0


# ----------------------------------------------------------------------------------- a run against a fake host
class FakeResponse:
    def __init__(self, url, status, content=b"", ctype="application/json"):
        self.url, self.status_code, self.content = url, status, content
        self.headers = {"content-type": ctype}


class FakeHost:
    """S3 (static routes): a file where held, else 403 AccessDenied; the API: a file where held, else 404."""

    def __init__(self, files, refuse=()):
        self.files, self.refuse, self.calls = files, set(refuse), []

    def get(self, url, timeout=None, allow_redirects=None, headers=None):
        self.calls.append((url, headers))
        if url in self.refuse:
            return FakeResponse(url, 403, b"<html>Request blocked</html>", "text/html")
        if url in self.files:
            return FakeResponse(url, 200, self.files[url])
        if "/prod/api/" in url:
            return FakeResponse(url, 404, b'{"message":"Not Found"}')
        return FakeResponse(url, 403, DENIED, "application/xml")


def doc_for(route, year, event, mid):
    """A small decryptable document of each kind."""
    kind = {"match-beats-api": "match-beats"}.get(S.KIND[route], S.KIND[route])
    if kind == "match-beats":
        pts = [{"pointId": "1_1_1_1", "point": 1, "server": "1", "serve": 1, "serveSpeed": 201.4, "faultSrvSpd": 0.0,
                "scorer": "1", "result": "A", "stroke": "N", "tm1GameScore": "15", "tm2GameScore": "0"},
               {"pointId": "1_1_2_2", "point": 2, "server": "1", "serve": 2, "serveSpeed": 160.2, "faultSrvSpd": 199.0,
                "scorer": "2", "result": "UE", "stroke": "F", "tm1GameScore": "15", "tm2GameScore": "15"}]
        return {"eventId": event, "matchId": mid, "year": year, "isMatchComplete": True, "matchStatus": "C",
                "matchWinner": 1, "setsComplete": 1, "eventType": "Men's Singles", "courtId": 1,
                "playerData": {"tm1Ply1Id": "S0AG", "tm1Ply1Name": "J. SINNER", "tm2Ply1Id": "Z355",
                               "tm2Ply1Name": "A. ZVEREV"},
                "setData": [{"set": 1, "gameData": [{"game": 1, "tm1SetScore": 6, "tm2SetScore": 4, "isTieBreak": False,
                                                     "pointData": pts}]}]}
    if kind == "keystats":
        return {"matchCompleted": True, "setsCompleted": 1, "courtId": 1,
                "players": [{"player1Id": "S0AG", "player1Name": "J. SINNER"}, {"player1Id": "Z355",
                                                                               "player1Name": "A. ZVEREV"}],
                "setStats": {"set0": [{"order": 20, "name": "1st Serve Average Speed", "player1": "201",
                                       "player2": "199"}], "set1": [{"order": 2, "name": "Aces", "player1": "1",
                                                                    "player2": "0"}]}}
    if kind == "rally-analysis":
        return {"matchCompleted": True, "setsCompleted": 1, "playerDetails": [{"player1Id": "S0AG"}, {"player1Id": "Z355"}],
                "rallyData": [{"name": "Serve", "t1win": [{"pointId": "1_1_1_1", "serve": 1, "serveSpeed": 201,
                                                           "pointEndType": "ACE"}], "t2win": []}]}
    return {"courtVisionData": [{"a75": True, "a76": "Men's Singles", "a79": {"a83": [{"a86": "S0AG"}]}, "a49": [],
                                 "a50": {"1_1_1_1": {"a81": "1_1_1_1", "a16": "201.40 KPH", "a95": "Ace",
                                                     "a35": {"a122": "1"},
                                                     "a27": {"a70": -11.0, "a71": 0.5, "a72": 2.9, "a74": False},
                                                     "a12": [{"a70": -11.0, "a71": 0.5, "a72": 2.9, "a73": "hit"},
                                                             {"a70": 0.0, "a71": 1.0, "a72": 1.1, "a73": "net"},
                                                             {"a70": 5.0, "a71": 3.0, "a72": 0.04, "a73": "bounce"},
                                                             {"a70": 12.0, "a71": 5.0, "a72": 1.3, "a73": "last"}]}}}]}


def served_files(keys):
    return {R.url_of(*k): json.dumps(encrypt(doc_for(k[2], k[0], k[1], k[3]))).encode() for k in keys}


CAL = [(y, e, r, m) for r, (y, e, m) in R.CALIBRATION.items()]
HOST_FILES = CAL + [
    # Washington 2025: all four static routes for the main draw; qualifying has MatchBeats only
    *[(2025, 418, r, m) for r in R.STATIC for m in ("MS001", "MS002", "MS003")], (2025, 418, "match-beats", "QS001"),
    # Shanghai 2025: MatchBeats static, key statistics only by the API
    (2025, 5014, "match-beats", "MS002"), (2025, 5014, "keystats-api", "MS001"), (2025, 5014, "keystats-api", "MS002"),
    # Genoa 2026: no static copy yet, the API has both
    (2026, 1763, "match-beats-api", "MS001"), (2026, 1763, "keystats-api", "MS001"),
    (2026, 1763, "match-beats-api", "MS002"),
]


def setup_run(tmp_path, monkeypatch, refuse=(), host_files=HOST_FILES):
    write_mtd(tmp_path / "mtd")
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(R, "STUDY_ROOT", tmp_path / "study")
    monkeypatch.setattr(A, "MTD_ROOT", tmp_path / "mtd")
    monkeypatch.setattr(R, "OTHER_FOLDERS", {"infosys_atp": tmp_path / "raw" / "infosys_atp",
                                             "infosys_atp_daily": tmp_path / "raw" / "infosys_atp_daily"})
    monkeypatch.setattr(R, "daily_complete", lambda: set())
    monkeypatch.setattr(R, "FULL_RUNS", tmp_path / "study" / "full_runs.jsonl")           # never the real records
    monkeypatch.setattr(R, "NEWER_TARGETS", tmp_path / "study" / "newer_targets.csv.gz")
    monkeypatch.setattr(S, "DIFFERENCES", tmp_path / "study" / "matchbeats_copies.csv.gz")
    files = served_files(host_files)
    host = FakeHost(files, refuse)
    from src.ingest.point_sources import feeds as F
    monkeypatch.setattr(R, "make_client", lambda args, cal, share: R.SharedClient(
        "chrome", not_found=cal.not_found, min_interval=0, jitter=0, max_requests=args.max_requests, session=host,
        share=share))
    return host, files


def args_for(*argv):
    parser = ArgumentParser()
    R.add_arguments(parser)
    return parser.parse_args(["--until", "20261016", "--skip-after", "2", "--cold-skip-after", "1",
                              "--cv-cold-skip-after", "1", "--no-share",
                              "--no-stage", *argv])


def asked(host):
    return [u.replace(R.HOST, "") for u, _ in host.calls]


def test_run_calibrates_discovers_expands_and_keeps_files_as_served(tmp_path, monkeypatch):
    host, files = setup_run(tmp_path, monkeypatch)
    summary = R.run(args_for())
    assert "stopped" not in summary and summary["receipts_with_errors"] == 0
    calls = asked(host)
    # calibration first, one known file per static route
    assert calls[:4] == [R.ROUTES[r].format(year=y, event=e, mid=m) for r, (y, e, m) in R.CALIBRATION.items()]
    assert all(h == R.HEADERS for _, h in host.calls)
    for key in HOST_FILES:                          # every served file held, byte for byte
        dest = R.dest_of(*key)
        assert dest.exists(), key
        assert gzip.decompress(dest.read_bytes()) == files[R.url_of(*key)]
    # Washington's qualifying: the static routes without its file given up after one absence (cold), MatchBeats kept
    assert "/static/prod/match-beats/2025/418/QS001/data.json" in calls
    # Shanghai 2025: key statistics by the API where the static copy is absent; never asked twice
    assert "/prod/api/stats-plus/v1/keystats/year/2025/eventId/5014/matchId/MS002" in calls
    assert len(calls) == len(set(calls))
    # Genoa 2026: discovery found no static file, so the API was asked, then expanded on the API only
    assert "/prod/api/match-beats/data/year/2026/eventId/1763/matchId/MS002" in calls
    assert "/static/prod/match-beats/2026/1763/MS002/data.json" not in calls
    # the Slam is not in the plan
    assert not any("/580/" in c for c in calls)
    ev = pd.read_csv(tmp_path / "study" / "infosys_atp_recent_events.csv")
    assert dict(zip(ev["event_id"], ev["state"])) == {421: "files", 5014: "files", 418: "files", 1763: "files",
                                                       2907: "empty"}
    # a rerun asks nothing: every answer is on record
    n = len(host.calls)
    R.run(args_for())
    assert len(host.calls) == n


def test_api_never_and_held_files_are_not_asked(tmp_path, monkeypatch):
    host, _ = setup_run(tmp_path, monkeypatch)
    back = fake_folder(tmp_path / "raw", "infosys_atp", [("2025/418/keystats/MS001", 200)])
    monkeypatch.setattr(R, "OTHER_FOLDERS", {"infosys_atp": back})
    R.run(args_for("--api", "never"))
    calls = asked(host)
    assert not any("/prod/api/" in c for c in calls)
    assert "/static/prod/stats-plus/2025/418/MS001/keystats.json" not in calls     # held by the backfill folder
    assert "/static/prod/stats-plus/2025/418/MS002/keystats.json" in calls


def test_empty_documents_are_kept_but_count_as_no_data(tmp_path, monkeypatch):
    host, _ = setup_run(tmp_path, monkeypatch)
    empty = json.dumps(encrypt({"courtVisionData": []})).encode()      # 88 bytes, as the host serves it
    assert len(empty) < R.EMPTY_BYTES
    for m in ("MS001", "MS002", "MS003", "QS001"):
        host.files[R.url_of(2025, 418, "court-vision", m)] = empty
    R.run(args_for("--events", "2025:418", "--cv-cold-skip-after", "2"))
    cv = [c for c in asked(host) if "/court-vision/2025/418/" in c]
    assert cv == [f"/static/prod/court-vision/2025/418/{m}/data.json" for m in ("MS001", "MS002", "QS001")]
    assert gzip.decompress(R.dest_of(2025, 418, "court-vision", "MS001").read_bytes()) == empty   # kept as served
    ev = pd.read_csv(tmp_path / "study" / "infosys_atp_recent_events.csv").iloc[0]
    assert (ev["files_court-vision"], ev["empty_court-vision"], ev["files_match-beats"]) == (0, 3, 4)


def test_an_unexpected_403_stops_the_run(tmp_path, monkeypatch):
    blocked = R.url_of(2025, 418, "rally-analysis", "MS001")
    host, _ = setup_run(tmp_path, monkeypatch, refuse=[blocked])
    summary = R.run(args_for())
    assert summary["stopped"].startswith("Blocked")
    assert host.calls[-1][0] == blocked
    assert R.exit_code(summary) == 2


class ResettingHost(FakeHost):
    """A FakeHost whose connection is reset on given URLs, a given number of times each."""

    def __init__(self, files, resets: dict[str, int]):
        super().__init__(files)
        self.resets = dict(resets)

    def get(self, url, timeout=None, allow_redirects=None, headers=None):
        if self.resets.get(url, 0) > 0:
            self.resets[url] -= 1
            self.calls.append((url, headers))
            raise ConnectionError("curl: (56) Recv failure: Connection was reset")
        return super().get(url, timeout=timeout, allow_redirects=allow_redirects, headers=headers)


def reset_client(host, max_requests=50):
    return R.SharedClient("chrome", min_interval=0, jitter=0, max_requests=max_requests, session=host,
                          reset_wait=0.001)


def test_a_connection_reset_is_asked_once_more():
    url = R.url_of(2025, 418, "match-beats", "MS001")
    host = ResettingHost({url: b'{"lastModified": 1, "response": ""}'}, {url: 1})
    c = reset_client(host)
    assert c.get(url).status_code == 200 and c.resets == 1 and len(host.calls) == 2
    assert c.stats()["connection_resets_retried"] == 1


def test_a_second_reset_in_a_row_stops_the_run():
    from src.ingest.point_sources import common as PC
    url = R.url_of(2025, 418, "match-beats", "MS001")
    host = ResettingHost({}, {url: 2})
    with pytest.raises(PC.Blocked, match="connection reset"):
        reset_client(host).get(url)
    no_wait = R.SharedClient("chrome", min_interval=0, jitter=0, session=ResettingHost({}, {url: 1}), reset_wait=0)
    with pytest.raises(PC.Blocked, match="connection reset"):     # --reset-wait 0: the feeds' client's own rule
        no_wait.get(url)


def test_exit_codes_tell_the_bulk_wrapper_when_to_go_on(tmp_path, monkeypatch):
    host, _ = setup_run(tmp_path, monkeypatch)
    summary = R.run(args_for("--max-requests", "10"))
    assert summary["stopped"].startswith("BudgetExhausted") and R.exit_code(summary) == 3
    summary = R.run(args_for())
    assert "stopped" not in summary and R.exit_code(summary) == 0
    assert R.exit_code({"refused": "pid 1"}) == 4
    assert R.exit_code({"finished_at": "x", "receipts_with_errors": 2}) == 5
    assert R.exit_code({"finished_at": "x", "stopped": "KeyboardInterrupt: "}) == 1
    assert R.exit_code({"finished_at": "x", "staging_failed": "ValueError"}) == 1


def test_a_second_collector_is_refused(tmp_path, monkeypatch):
    setup_run(tmp_path, monkeypatch)
    other = [(424242, ["python.exe", "-m", "src.ingest.point_sources.infosys_atp_recent", "--max-requests", "5"], 9)]
    monkeypatch.setattr(R, "python_procs", lambda: other)
    a = args_for()
    a.no_share = False
    summary = R.run(a)
    assert summary == {"refused": "pid 424242: python.exe -m src.ingest.point_sources.infosys_atp_recent "
                                  "--max-requests 5"} and R.exit_code(summary) == 4


def test_a_calibration_file_not_served_stops_the_run(tmp_path, monkeypatch):
    host, _ = setup_run(tmp_path, monkeypatch, host_files=[k for k in HOST_FILES if k[2] != "court-vision"])
    summary = R.run(args_for())
    assert summary["stopped"].startswith("Blocked")
    assert len(host.calls) == 4


# ----------------------------------------------------------------------------------- staging
def test_guard_refuses_the_backfill_folder_and_early_years(tmp_path):
    with pytest.raises(S.Refused):
        S.guard(S.BACKFILL_RAW / "2025" / "352" / "keystats" / "MS001.json.gz", 2025)
    with pytest.raises(S.Refused):
        S.guard(S.RAW / "2021" / "1" / "match-beats" / "MS001.json.gz", 2021)
    with pytest.raises(S.Refused):
        S.guard(S.RAW / "x", "year")
    S.guard(S.RAW / "2025" / "418" / "match-beats" / "MS001.json.gz", 2025)
    S.guard(S.DAILY_RAW / "2026" / "5014" / "keystats-api" / "MS004.json.gz", 2026)


def test_shots_split_a_trajectory_at_each_hit():
    t = [{"a70": 1, "a71": 2, "a72": 3, "a73": "hit"}, {"a70": 1, "a71": 2, "a72": 3.1, "a73": "peak"},
         {"a70": 0, "a71": 1, "a72": 1, "a73": "net"}, {"a70": 5, "a71": 1, "a72": 0, "a73": "bounce"},
         {"a70": 9, "a71": 1, "a72": 1, "a73": "peak"}, {"a70": 10, "a71": 1, "a72": 1, "a73": "hit"},
         {"a70": 0, "a71": 0, "a72": 1, "a73": "net"}, {"a70": -5, "a71": 0, "a72": 0, "a73": "bounce"},
         {"a70": -9, "a71": 0, "a72": 1, "a73": "last"}]
    s1, s2 = S.shots(t)
    assert s1["labels"] == ["hit", "peak", "net", "bounce", "peak"] and s1["peak_pre"] == (1, 2, 3.1)
    assert s1["peak_post"] == (9, 1, 1) and s2["last"] == (-9, 0, 1) and "peak_pre" not in s2
    assert S.shots([{"a70": 0, "a71": 0, "a72": 1, "a73": "net"}, {"a73": "odd"}])[0]["extra"] == [{"a73": "odd"}]


def test_score_from_points():
    def game(a, b, tb=False, pts=()):
        return {"tm1SetScore": a, "tm2SetScore": b, "isTieBreak": tb, "pointData": list(pts)}
    mb = {"setData": [{"gameData": [game(1, 0), game(6, 4)]},
                      {"gameData": [game(6, 6), game(7, 6, True, [{"tm1GameScore": "7", "tm2GameScore": "5"}])]}]}
    assert S.score_from_points(mb) == "6-4 7-6(5)"
    assert S.score_from_points({"setData": []}) is None
    assert S.winner_from_points(mb) == 1
    lost = {"setData": [{"gameData": [game(1, 6)]}, {"gameData": [game(6, 7, True)]}]}
    assert S.winner_from_points(lost) == 2
    retired = {"setData": [{"gameData": [game(6, 4)]}, {"gameData": [game(2, 1)]}]}
    assert S.winner_from_points(retired) == 0
    three = {"setData": [{"gameData": [game(4, 6)]}, {"gameData": [game(6, 1)]}, {"gameData": [game(7, 5)]}]}
    assert S.winner_from_points(three) == 1


def test_staging_decrypts_every_kind_with_provenance(tmp_path, monkeypatch):
    host, _ = setup_run(tmp_path, monkeypatch)
    R.run(args_for())
    receipts = P.receipts_for(R.SOURCE)
    out = S.stage(receipts=receipts, daily_receipts=None, complete=lambda: set(), dump=tmp_path / "dump",
                  summary_path=None)
    assert out["failures_total"] == 0
    m = pd.read_parquet(tmp_path / "dump" / "matches.parquet")
    w1 = m[(m["event_id"] == "418") & (m["match_id"] == "MS001")].iloc[0]
    assert json.loads(w1["routes"]) == ["court-vision", "keystats", "match-beats", "rally-analysis"]
    assert (w1["p1_id"], w1["p2_id"], w1["match_winner"], w1["score_from_points"]) == ("S0AG", "Z355", "1", "6-4")
    assert w1["winner_from_points"] == "0"          # one set only: no one has won two
    assert m.loc[m["match_id"].eq("MS001") & m["event_id"].eq("421"), "winner_from_points"].isna().all()   # no MB
    assert (w1["points"], w1["points_timed"], w1["first_serve_points_timed"]) == ("2", "2", "1")
    assert (w1["keystats_speed"], w1["rally_entries"], w1["cv_points"], w1["cv_timed"]) == ("TRUE", "1", "1", "1")
    assert (w1["series"], w1["tournament_start"], w1["round_from_code"]) == ("atp", "20250728", "F")
    sh = m[(m["event_id"] == "5014") & (m["match_id"] == "MS002")].iloc[0]
    assert json.loads(sh["routes"]) == ["keystats-api", "match-beats"]
    pts = pd.read_parquet(tmp_path / "dump" / "points.parquet")
    p = pts[(pts["event_id"] == "418") & (pts["match_id"] == "MS001")]
    assert list(p["serveSpeed"]) == ["201.4", "160.2"] and list(p["faultSrvSpd"]) == ["0.0", "199.0"]
    assert p["source_file"].iloc[0].endswith("infosys_atp_recent/2025/418/match-beats/MS001.json.gz")
    assert p["source_sha256"].notna().all() and p["retrieved_at"].notna().all()
    shots = pd.read_parquet(tmp_path / "dump" / "court_vision_shots.parquet")
    s = shots[(shots["event_id"] == "418") & (shots["match_id"] == "MS001")].iloc[0]
    assert (s["labels"], s["x_hit"], s["z_bounce"], s["x_last"]) == ("hit|net|bounce|last", "-11.0", "0.04", "12.0")
    cv = pd.read_parquet(tmp_path / "dump" / "court_vision.parquet")
    assert cv["a16"].iloc[0] == "201.40 KPH" and json.loads(cv["positions"].iloc[0])["a27"]["a70"] == -11.0
    ks = pd.read_parquet(tmp_path / "dump" / "keystats.parquet")
    assert set(ks["set_key"]) == {"set0", "set1"}
    # nothing under the backfill folder is ever read
    assert all("point_sources/infosys_atp/" not in f for f in pts["source_file"])


# ----------------------------------------------------------------------------------- the newer MatchBeats format
def newer(doc: dict, **change) -> dict:
    """A MatchBeats document in the newer format: every point gains the API copy's fields (and ``change``)."""
    out = json.loads(json.dumps(doc))
    for st in out["setData"]:
        for g in st["gameData"]:
            for p in g["pointData"]:
                p.update({"firstServer": "1A", "lastHitter": "", "serveClassId": 2, "tm1Shot": 0, "tm2Shot": 0,
                          "pointDuration": 0.027, "tm1AtNet": False, "tm2AtNet": False}, **change)
    return out


def test_compare_matchbeats_and_the_newer_details():
    old = doc_for("match-beats", 2025, 418, "MS001")
    assert S.is_newer_format(newer(old)) and not S.is_newer_format(old)
    same = S.compare_matchbeats(old, newer(old))
    assert same["core_identical"] and same["points_matched"] == 2 and same["newer_format"]
    lost = S.compare_matchbeats(old, newer(old, serveSpeed=0.0))                 # a rewrite that lost the speeds
    assert not lost["core_identical"] and (lost["timed_static"], lost["timed_api"]) == (2, 0)
    assert json.loads(lost["fields_differing"]) == {"serveSpeed": 2}
    relabelled = S.compare_matchbeats(old, newer(old, result="N"))
    assert json.loads(relabelled["endings_differing"]) == {"A->N": 1, "UE->N": 1}
    d = S.newer_details(newer(old, result="N"))
    assert d["1_1_1_1"] == ["1A", "", "2", "0", "0", "0.027", "FALSE", "FALSE", "N", None, None]
    assert len(d["1_1_1_1"]) == len(S.NEWER_COLUMNS)


def test_the_newer_format_pass_asks_once_per_older_match_and_staging_takes_the_newer_copy(tmp_path, monkeypatch):
    host, _ = setup_run(tmp_path, monkeypatch)
    monkeypatch.setattr(R, "STUDY_ROOT", tmp_path / "study")
    monkeypatch.setattr(R, "NEWER_TARGETS", tmp_path / "study" / "newer_targets.csv.gz")
    monkeypatch.setattr(R, "FULL_RUNS", tmp_path / "study" / "full_runs.jsonl")
    R.run(args_for())
    dump = tmp_path / "dump"
    S.stage(receipts=P.receipts_for(R.SOURCE), daily_receipts=None, complete=lambda: set(), dump=dump,
            summary_path=None)
    monkeypatch.setattr(S.P, "dump_path", lambda source, *parts: dump.joinpath(*parts))
    targets = R.frozen_targets(R.NEWER_TARGETS, dump)
    static_mb = [k for k in HOST_FILES if k[2] == "match-beats"]
    assert sorted((y, e, m) for y, e, m, _, _ in targets) == sorted((y, e, m) for y, e, _, m in static_mb)
    assert targets[0][0] == 2025 and targets[0][4] >= targets[-1][4]                   # newest tournament first
    for y, e, _, m in static_mb:            # the API serves each in the newer format; one relabels an ending
        doc = newer(doc_for("match-beats", y, e, m), **({"result": "N"} if (e, m) == (418, "MS002") else {}))
        host.files[R.url_of(y, e, "match-beats-api", m)] = json.dumps(encrypt(doc)).encode()
    n = len(host.calls)
    full_runs = R.FULL_RUNS.read_text().count("\n")                     # the first, ordinary run recorded one
    summary = R.run(args_for("--newer-format"))
    asked = [u for u, _ in host.calls[n:]]
    assert len(asked) == len(static_mb) and all("/prod/api/match-beats/" in u for u in asked)
    assert summary["answers"] == {"data": len(static_mb)} and R.exit_code(summary) == 0
    assert R.FULL_RUNS.read_text().count("\n") == full_runs                      # not a full run of the plan
    out = S.stage(receipts=P.receipts_for(R.SOURCE), daily_receipts=None, complete=lambda: set(), dump=dump,
                  summary_path=None)
    both = out["matchbeats_both_copies"]
    assert both["matches"] == len(static_mb) and both["core_identical"] == len(static_mb) - 1
    assert both["ending_pairs_static_to_newer"] == {"A->N": 1, "UE->N": 1}
    m = pd.read_parquet(dump / "matches.parquet")
    w1 = m[(m["event_id"] == "418") & (m["match_id"] == "MS001")].iloc[0]
    assert w1["matchbeats_copy"] == "match-beats: static core, newer details from match-beats-api"
    pts = pd.read_parquet(dump / "points.parquet")
    p = pts[(pts["event_id"] == "418") & (pts["match_id"] == "MS002")]
    assert set(p["route"]) == {"match-beats"} and list(p["pointDuration"]) == ["0.027", "0.027"]
    assert list(p["result"]) == ["A", "UE"] and list(p["result_newer"]) == ["N", "N"]   # both endings kept
    assert list(p["serveSpeed"]) == ["201.4", "160.2"]                               # the core is the static one
    api_only = pts[(pts["event_id"] == "1763") & (pts["match_id"] == "MS001")]       # Genoa: the API copy only
    assert set(api_only["route"]) == {"match-beats-api"} and api_only["result_newer"].isna().all()
    assert R.frozen_targets(R.NEWER_TARGETS, dump) == targets                      # frozen at the first run


def test_a_full_run_is_recorded_for_the_topup_reminder(tmp_path, monkeypatch):
    setup_run(tmp_path, monkeypatch)
    monkeypatch.setattr(R, "FULL_RUNS", tmp_path / "study" / "full_runs.jsonl")
    R.run(args_for("--events", "2025:418"))
    assert not R.FULL_RUNS.exists()                                              # a partial run is not one
    R.run(args_for("--max-requests", "5"))
    assert not R.FULL_RUNS.exists()                                              # nor one stopped by its budget
    R.run(args_for())
    line = json.loads(R.FULL_RUNS.read_text().splitlines()[-1])
    assert line["events_selected"] == 5 and line["until"] == "20261016" and line["finished_at"]


def test_staging_takes_completed_daily_key_statistics(tmp_path, monkeypatch):
    setup_run(tmp_path, monkeypatch, host_files=[])
    daily = tmp_path / "raw" / "infosys_atp_daily"
    recs = []
    for mid, done in (("MS004", True), ("MS005", False)):
        dest = daily / "2026" / "5014" / "keystats-api" / f"{mid}.json.gz"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(gzip.compress(json.dumps(encrypt(doc_for("keystats", 2026, 5014, mid))).encode()))
        recs.append({"name": f"2026/5014/keystats-api/{mid}", "status": 200, "dest": dest.as_posix()})
    (daily / "_receipts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs), encoding="utf-8")
    out = S.stage(receipts=P.receipts_for(R.SOURCE), daily_receipts=R.receipts_at(daily),
                  complete=lambda: {(2026, 5014, "MS004")}, dump=tmp_path / "dump", summary_path=None)
    m = pd.read_parquet(tmp_path / "dump" / "matches.parquet")
    assert list(m["match_id"]) == ["MS004"] and out["files_by_folder"] == {"infosys_atp_daily": 1}
