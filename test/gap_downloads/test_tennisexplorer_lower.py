"""TennisExplorer's lower-level collector (src/ingest/tennisexplorer_lower.py): its day parser, its scope rule, its
fetcher's waits and stops, a whole run against a fake site, and the monthly staging; on synthetic pages built like the
site's (structure observed 19-22 Oct 2026; every price here is made up, no raw page is committed)."""
import datetime as dt
import gzip
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "test" / "pinnacle_gap"))

from src.ingest import tennisexplorer_lower as L  # noqa: E402
from src.ingest.point_sources import common as P  # noqa: E402
from test_tennisexplorer import page as match_page  # noqa: E402


def head(name, href=None):
    inner = f'<a href="{href}">{name}</a>' if href else name
    return f'<tr class="head flags"><td class="t-name" colspan="2">{inner}</td><td class="course">H</td></tr>'


def match(n, mid, p1, p2, prices=("1.25", "3.50"), hhmm="13:30"):
    a, b = prices
    return (f'<tr id="r{n}" class="one bott"><td class="first time" rowspan="2">{hhmm}</td><td class="t-name">'
            f'<a href="/player/{p1.split()[0].lower()}/">{p1}</a></td><td class="coursew" rowspan="2">{a}</td>'
            f'<td class="course" rowspan="2">{b}</td><td rowspan="2"><a href="/match-detail/?id={mid}">info</a></td></tr>'
            f'<tr id="r{n}b" class="one"><td class="t-name"><a href="/player/{p2.split()[0].lower()}/">{p2}</a></td></tr>')


def day_page(*parts):
    return ('<html><head><title>Tennis Explorer: results</title></head><body><table class="result">'
            + "".join(parts) + "</table></body></html>")


MEN = day_page(head("Almaty", "/almaty/2026/atp-men/"), match(1, 101, "Bee A.", "Dee C."),
               head("Lisbon challenger", "/lisbon-challenger/2026/atp-men/"), match(2, 102, "Fox E.", "Hil G."),
               head("Valencie challenger", "/valencie-challenger/2026/atp-men/"), match(3, 103, "Jo I.", "Lu K."),
               head("Futures 2026"), match(4, 104, "Mo N.", "Po Q."), match(5, 105, "Ra S.", "Tu V.", ("&nbsp;", "&nbsp;")),
               head("UTR Pro Tennis Series 3", "/utr-pro-tennis-series-3/2026/atp-men/"), match(6, 106, "Wy X.", "Za B."))
WOMEN = day_page(head("Saguenay ITF", "/saguenay-itf/2026/wta-women/"), match(1, 201, "Ann B.", "Cid D."),
                 head("Lisbon", "/lisbon/2026/wta-women/"), match(2, 202, "Eve F.", "Gus H."),
                 head("Ningbo WTA", "/ningbo-wta/2026/wta-women/"), match(3, 203, "Ivy J.", "Kay L."))
TYPES = {("atp", "almaty", 2026): "main", ("atp", "lisbon-challenger", 2026): "lower",
         ("atp", "valencie-challenger", 2026): "main", ("wta", "saguenay-itf", 2026): "lower",
         ("wta", "lisbon", 2026): "lower", ("wta", "ningbo-wta", 2026): "main"}


def test_day_rows_and_scope():
    rows = L.day_rows(MEN, dt.date(2026, 10, 19), "atp")
    assert [r["te_id"] for r in rows] == [101, 102, 103, 104, 105, 106]
    assert rows[1]["event"] == "Lisbon challenger" and rows[1]["event_href"] == "/lisbon-challenger/2026/atp-men/"
    assert (rows[0]["avg1"], rows[0]["avg2"], rows[0]["priced"]) == ("1.25", "3.50", True)
    assert rows[4]["priced"] is False and rows[4]["avg1"] is None
    scope = [L.in_scope(r, TYPES) for r in rows]
    assert scope == [(False, "tour level (the tour adapter's)"), (True, "Challenger"), (True, "Challenger"),
                     (True, "men's ITF (Futures)"), (True, "men's ITF (Futures)"),
                     (False, "exhibition, league, team or UTR event")]
    w = [L.in_scope(r, TYPES) for r in L.day_rows(WOMEN, dt.date(2026, 10, 19), "wta")]
    assert w == [(True, "lower"), (True, "lower"), (False, "tour level (the tour adapter's)")]
    unknown = {"tour": "wta", "event": "Monastir 51 ITF", "event_href": "/monastir-51-itf/2019/wta-women/"}
    assert L.in_scope(unknown, {}) == (True, "ITF (not on the calendar)")
    assert L.in_scope({**unknown, "event": "Somewhere", "event_href": "/somewhere/2019/wta-women/"}, {}) == \
        (False, "not on the calendar")


class FakeResponse:
    def __init__(self, status, body, url):
        self.status_code, self.content, self.url = status, body, url
        self.headers = {"content-type": "text/html"}


class FakeSession:
    """Answers like the site: day pages, calendars and match pages from dicts; counts the requests."""

    def __init__(self, pages: dict, status: dict | None = None):
        self.pages, self.status, self.asked = pages, status or {}, []

    def get(self, url, timeout=None, headers=None):
        self.asked.append(url)
        for key, code in self.status.items():
            if key in url:
                return FakeResponse(code, b"refused", url)
        for key, body in self.pages.items():
            if key in url:
                return FakeResponse(200, body.encode(), url)
        return FakeResponse(404, b"", url)


def cal_row(kind, href, name):
    return (f'<tr data-type="{kind}"><td class="shortdate">19.10. 2026</td><th class="t-name"><a href="{href}">{name}'
            f'</a></th></tr>')


CAL = ('<html><head><title>Tennis Explorer: calendar</title></head><body><table>'
       + cal_row("main", "/almaty/2026/atp-men/", "Almaty") + cal_row("lower", "/lisbon-challenger/2026/atp-men/", "Lisbon")
       + cal_row("main", "/ningbo-wta/2026/wta-women/", "Ningbo") + cal_row("lower", "/lisbon/2026/wta-women/", "Lisbon")
       + cal_row("lower", "/saguenay-itf/2026/wta-women/", "Saguenay") + "</table></body></html>")


@pytest.fixture
def site(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "RAW", tmp_path / "raw" / L.SOURCE)
    monkeypatch.setattr(L, "DUMP", tmp_path / "dump")
    pages = {"type=atp-single&year=2026&month=10&day=19": MEN, "type=wta-single&year=2026&month=10&day=19": WOMEN,
             "type=atp-single&year=2026&month=10&day=18": day_page(head("Futures 2026"), match(1, 301, "Ab C.", "De F.")),
             "type=wta-single&year=2026&month=10&day=18": day_page(),
             "/calendar/": CAL}
    for mid in (102, 103, 104, 201, 202, 301):
        pages[f"match-detail/?id={mid}"] = match_page()
    return pages


def fetcher(session, busy=lambda: None, max_requests=100):
    client = P.Client("chrome", min_interval=0, jitter=0, max_requests=max_requests, session=session)
    return L.Fetcher(max_requests, 0, 0, busy=busy, client=client, sleep=lambda s: None)


def test_a_run_newest_first_priced_in_scope_pages_once(site):
    s = FakeSession(site)
    f = fetcher(s)
    out = L.run(dt.date(2026, 10, 18), dt.date(2026, 10, 19), f, today=dt.date(2026, 10, 22))
    asked = [u.split("tennisexplorer.com")[1] for u in s.asked]
    assert sum("/calendar/" in u for u in asked) == 2                              # this year's two calendars
    days = [u for u in asked if u.startswith("/results/")]
    assert days[0].endswith("day=19") and days[-1].endswith("day=18")              # newest first
    pages = [int(u.split("=")[1]) for u in asked if "match-detail" in u]
    assert pages == [102, 103, 104, 201, 202, 301]       # tour level, unpriced and UTR left out
    assert out["stopped"] is None and out["match_pages_new"] == 6 and out["days"] == 2 and out["finished"]
    assert L.done_days() == {"2026-10-18", "2026-10-19"}         # fetched after day + 3 (today's clock), all answered
    (L.RAW / "_state" / "done_days.txt").unlink()
    fetched_20 = dt.datetime(2026, 10, 20, 12, tzinfo=dt.timezone.utc).timestamp()
    for p in (L.RAW / "day").glob("*/*/*.html.gz"):                          # as if fetched on 20 Oct
        os.utime(p, (fetched_20, fetched_20))
    s2 = FakeSession(site)
    L.run(dt.date(2026, 10, 18), dt.date(2026, 10, 19), fetcher(s2), today=dt.date(2026, 10, 22))
    assert not any("match-detail" in u for u in s2.asked)                         # nothing asked twice
    assert [u.split("day=")[1] for u in s2.asked if "/results/" in u] == ["19", "19", "18", "18"]   # under 3 days old
    s3 = FakeSession(site)
    out3 = L.run(dt.date(2026, 10, 18), dt.date(2026, 10, 19), fetcher(s3), today=dt.date(2026, 10, 22))
    assert s3.asked == [] and out3["days_done_before"] == 2                       # done days are not read again


def test_waits_for_the_tour_adapter_then_goes_on(site):
    calls = iter([4242, 4242, None] + [None] * 1000)
    f = fetcher(FakeSession(site), busy=lambda: next(calls))
    out = L.run(dt.date(2026, 10, 19), dt.date(2026, 10, 19), f, today=dt.date(2026, 10, 22))
    assert out["stopped"] is None and f.waited == 2 * L.HOST_WAIT


def test_a_refusal_stops_the_run(site):
    s = FakeSession(site, status={"match-detail/?id=103": 403})
    f = fetcher(s)
    f.client.block_retries = 0
    out = L.run(dt.date(2026, 10, 18), dt.date(2026, 10, 19), f, today=dt.date(2026, 10, 22))
    assert out["stopped"].startswith("Blocked") and not any("id=104" in u for u in s.asked)


def test_staging_by_month_strings_and_rebuilt_only_when_changed(site):
    L.run(dt.date(2026, 10, 18), dt.date(2026, 10, 19), fetcher(FakeSession(site)), today=dt.date(2026, 10, 22))
    first = L.stage()
    assert first["months_rebuilt"] == 1 and first["listed_rows"] == 10 and first["matches_rows"] == 6
    listed = pd.read_parquet(L.DUMP / "listed" / "2026-10.parquet")
    assert set(listed.dtypes.astype(str)) == {"string"}
    assert listed.set_index("te_id").loc["101", "scope"] == "tour level (the tour adapter's)"
    odds = pd.read_parquet(L.DUMP / "odds" / "2026-10.parquet")
    assert set(odds.book) == {"Pinnacle", "bet365"} and len(odds) == 12
    assert L.stage() == {"months_unchanged": 1}
    s = L.summary()["2026-10"]
    assert (s["listed"], s["priced"], s["match_pages"], s["with_pinnacle"], s["pinnacle_timed"]) == (10, 9, 6, 6, 6)
