"""TennisExplorer's match odds: every listed book's match-winner prices with their history, Pinnacle's among them.

Why (21 Oct 2026): Pinnacle's own closes are missing from August 2025 (docs/decisions/2026-10-09-pinnacle-first-odds-input.md
§ 3). TennisExplorer's match pages list the "Home/Away" prices of about 15 books, Pinnacle included, each with every
change and its time and the opening price with its time (docs/research/pinnacle-gap/README.md). Collected under the
scraping approval (docs/decisions/2026-10-08-scraping-approved.md): paced, a receipt per request, raw copies kept; a
non-200 answer or a challenge page stops the run (back off and report, never retry in a loop). No login, no key.

The site's pages (server-rendered HTML):
    /calendar/{atp-men|wta-women}/<year>/      the year's events: start date, surface, draw, and a type ("main", "lower",
                                               "exhibitions") on each row
    /<slug>/<year>/{atp-men|wta-women}/        an event: every main-draw match (date, time, round, the players' pages,
                                               sets, two listed prices) with its match-detail id
    /match-detail/?id=<id>                     a match: date, time, event, round, surface, full names, score; the odds
                                               tabs, "Home/Away" among them: per book, each side's last price, each
                                               change with its time ("18.10. 10:21") and the opening with its time
Times on the site are Europe/Berlin's (the header says "GMT+1, Berlin, Prague, Vienna"; summer time is observed: its
clock read 03:07 at 01:07 UTC on 22 Oct 2026). They are stored in UTC. Each page's header clock is kept to check it.

    ./python.sh -m src.ingest.tennisexplorer --calendar 2025 2026        the calendar pages (re-fetched when not final)
    ./python.sh -m src.ingest.tennisexplorer --events --since 2025-07-01 each "main" event's page from that date on
    ./python.sh -m src.ingest.tennisexplorer --matches --since 2025-08-01 [--until D] [--max N]
                                                                         each finished main-draw match's page not on disk
    ./python.sh -m src.ingest.tennisexplorer --stage                     the staged tables from every raw match page
    ./python.sh -m src.ingest.tennisexplorer --link <model_frame.parquet> the frame's matches linked to TennisExplorer's

Raw copies: data/raw/tennisexplorer/{calendar,events,matches}/...html.gz; receipts data/raw/tennisexplorer/_receipts.jsonl.
Staged (gitignored, data/dump/odds/tennisexplorer/): events.parquet (the index), matches.parquet (one row per match
page), odds.parquet (one row per match and book: each side's last, opening and change count), moves.parquet (every
change), link.parquet (frame match_id -> TennisExplorer id, with Pinnacle's last prices for A and B).
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import os
import random
import re
import sys
import time
import unicodedata
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingest.public_dump import common as C  # noqa: E402

SOURCE = "tennisexplorer"
RAW = C.PROJECT_ROOT / "data" / "raw" / SOURCE
DUMP = C.DUMP_ROOT / "odds" / SOURCE
BASE = "https://www.tennisexplorer.com"
TOURS = {"atp": "atp-men", "wta": "wta-women"}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) tennis-predictions/1.0 (research use; python-requests)"
PAUSE = 3.0          # seconds between requests, plus up to one second of jitter
BERLIN = ZoneInfo("Europe/Berlin")
NUM = re.compile(r"^\s*(\d+(?:\.\d+)?)")
STAMP = re.compile(r"^(\d{1,2})\.(\d{1,2})\.\s+(\d{1,2}):(\d{2})$")
FINAL_AFTER_DAYS = 3  # an event page or calendar fetched this many days after the event's last match is final
# "main" events the model's frame never holds (team events, leagues, the Next Gen Finals, the Challenger 175s the site
# files as main): their pages are not fetched. The frame's 2025-26 matches are tour main draws and the two Finals.
SKIP = re.compile(r"(?:davis-cup|billie-jean-king-cup|united-cup|laver-cup|hopman-cup|league|next-gen|challenger|-chall$|"
                  r"exhibition|invitational)")


class Stop(RuntimeError):
    """An answer that must end the run: a block, a challenge page, a changed site."""


# --------------------------------------------------------------------------------------
# the client
# --------------------------------------------------------------------------------------
class Client:
    def __init__(self, receipts: C.Receipts, pause: float = PAUSE):
        self.sess = requests.Session()
        self.sess.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9",
                                  "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
        self.receipts = receipts
        self.pause = pause
        self._last = 0.0
        self.sent = 0

    def get(self, name: str, url: str, dest: Path) -> bytes:
        wait = self._last + self.pause + random.random() - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        receipt = {"name": name, "url": url, "retrieved_at": C.utc_now_iso(), "dest": C.rel(dest)}
        try:
            r = self.sess.get(url, timeout=60, allow_redirects=False)
        except requests.RequestException as err:
            self.receipts.record({**receipt, "error": f"{type(err).__name__}: {err}"})
            raise Stop(f"{name}: {type(err).__name__}: {err}") from err
        finally:
            self._last = time.monotonic()
            self.sent += 1
        body = r.content
        receipt.update(status=r.status_code, content_type=r.headers.get("Content-Type"), bytes=len(body),
                       sha256=C.sha256_bytes(body))
        if r.status_code != 200:
            self.receipts.record({**receipt, "error": f"HTTP {r.status_code}"})
            raise Stop(f"{name}: HTTP {r.status_code} (a block or a changed site: stopped, not retried)")
        head = body[:30000].lower()
        if b"captcha" in head or b"cf-chl" in head or b"<title>tennis explorer" not in head:
            self.receipts.record({**receipt, "error": "not a TennisExplorer page (a challenge page?)"})
            raise Stop(f"{name}: the answer is not a TennisExplorer page (a challenge?): stopped")
        dest.parent.mkdir(parents=True, exist_ok=True)
        C.write_atomic(dest, gzip.compress(body))
        self.receipts.record(receipt)
        return body


def read_raw(path: Path) -> str:
    return gzip.decompress(path.read_bytes()).decode("utf-8", "replace")


def calendar_path(tour: str, year: int) -> Path:
    return RAW / "calendar" / f"{tour}_{year}.html.gz"


def event_path(tour: str, year: int, slug: str) -> Path:
    return RAW / "events" / str(year) / tour / f"{slug}.html.gz"


def match_path(te_id: int) -> Path:
    return RAW / "matches" / f"{te_id // 10000:04d}" / f"{te_id}.html.gz"


# --------------------------------------------------------------------------------------
# parsers
# --------------------------------------------------------------------------------------
def _num(s) -> float | None:
    m = NUM.match(s or "")
    return float(m.group(1)) if m else None


def norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", s)


def name_tokens(name) -> frozenset:
    if not isinstance(name, str):
        return frozenset()                               # a missing name (NaN) matches nothing
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(\d{4}\)", " ", s)                    # "Damm Martin (2003)": the site's homonym tag
    return frozenset(t for t in re.split(r"[^a-z]+", s) if t)


def berlin_to_utc(day: dt.date, hhmm: str | None) -> str | None:
    if not hhmm:
        return None
    h, m = map(int, hhmm.split(":"))
    return dt.datetime.combine(day, dt.time(h, m), BERLIN).astimezone(dt.timezone.utc).isoformat()


def parse_calendar(html: str, tour: str, year: int) -> list[dict]:
    """A calendar page -> one row per event: slug, name, start date, type, surface, draw size."""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for th in soup.select("th.t-name"):
        a = th.find("a", href=True)
        tr = th.find_parent("tr")
        if a is None or tr is None:
            continue
        m = re.match(rf"^/([^/]+)/(\d{{4}})/{TOURS[tour]}/$", a["href"])
        if not m:
            continue
        d = tr.select_one("td.shortdate")
        dm = re.search(r"(\d{2})\.(\d{2})\.\s*(\d{4})", d.get_text(" ", strip=True)) if d is not None else None
        surf = tr.select_one("td.s-color span")
        draw = tr.select_one("td.draw")
        out.append({"tour": tour, "year": int(m.group(2)), "slug": m.group(1), "name": a.get_text(" ", strip=True),
                    "type": tr.get("data-type"),
                    "start": dt.date(int(dm.group(3)), int(dm.group(2)), int(dm.group(1))).isoformat() if dm else None,
                    "surface": surf.get("title") if surf is not None else None,
                    "draw": int(draw.get_text(strip=True)) if draw is not None and draw.get_text(strip=True).isdigit()
                    else None, "href": a["href"]})
    return out


def _year_for(day: int, month: int, start: dt.date) -> int:
    """The year that puts dd.mm. nearest the event's start (an event can straddle the new year)."""
    best = None
    for y in (start.year - 1, start.year, start.year + 1):
        try:
            gap = abs((dt.date(y, month, day) - start).days)
        except ValueError:
            continue
        if best is None or gap < best[0]:
            best = (gap, y)
    return best[1]


def parse_event(html: str, tour: str, start: dt.date) -> list[dict]:
    """An event page -> one row per listed match: id, day, time, round, players, sets, prices. The results sit in the
    first tab of a finished event, in a box of their own below "Next matches" while the event is under way, and in the
    page's only table at the Finals (no draw tab); every results table of the page is read, the rows of a played or
    listed match (id "r<n>") only."""
    soup = BeautifulSoup(html, "html.parser")
    center = soup.select_one("#center") or soup
    out, seen = [], set()
    for tab in center.select("table.result"):
        if {"moneydetails", "interesting"} & set(tab.get("class") or []):
            continue
        for m in _event_rows(tab.select("tbody > tr"), start):
            if m["te_id"] not in seen:
                seen.add(m["te_id"])
                out.append(m)
    return out


def _event_rows(rows: list, start: dt.date) -> list[dict]:
    out = []
    for i, r in enumerate(rows):
        if not re.fullmatch(r"r\d+", r.get("id") or "") or i + 1 >= len(rows):
            continue
        r2 = rows[i + 1]
        link = r.find("a", href=re.compile(r"match-detail/\?id=\d+"))
        if link is None:
            continue
        t = r.select_one("td.time")
        tt = t.get_text(" ", strip=True) if t is not None else ""
        m = re.search(r"(\d{1,2})\.(\d{1,2})\.\s*(\d{1,2}:\d{2})?", tt)
        day = None
        if m:
            d, mo = int(m.group(1)), int(m.group(2))
            day = dt.date(_year_for(d, mo, start), mo, d)
        rnd = r.find("td", attrs={"title": True})
        p1, p2 = r.select_one("td.t-name a"), r2.select_one("td.t-name a")
        s1, s2 = r.select_one("td.result"), r2.select_one("td.result")
        prices = r.select("td.course")
        out.append({"te_id": int(re.search(r"id=(\d+)", link["href"]).group(1)), "day": day.isoformat() if day else None,
                    "time_berlin": m.group(3) if m and m.group(3) else None,
                    "round": rnd.get("title") if rnd is not None else None,
                    "p1": p1.get_text(strip=True) if p1 else None, "p1_slug": p1.get("href") if p1 else None,
                    "p2": p2.get_text(strip=True) if p2 else None, "p2_slug": p2.get("href") if p2 else None,
                    "sets1": s1.get_text(strip=True) if s1 else None, "sets2": s2.get_text(strip=True) if s2 else None,
                    "h": _num(prices[0].get_text(strip=True)) if len(prices) > 0 else None,
                    "a": _num(prices[1].get_text(strip=True)) if len(prices) > 1 else None})
    return out


def _stamp_utc(s: str, year: int, month: int) -> dt.datetime | None:
    m = STAMP.match(s.strip())
    if not m:
        return None
    d, mo, hh, mi = map(int, m.groups())
    y = year - 1 if mo > month + 6 else (year + 1 if mo + 6 < month else year)
    return dt.datetime(y, mo, d, hh, mi, tzinfo=BERLIN).astimezone(dt.timezone.utc)


def _side(td, year: int, month: int) -> dict:
    """One odds cell -> {'last': x, 'moves': [(utc, odds)] newest first, 'open': (utc, odds) or None}."""
    div = td.select_one("div.odds-in")
    if div is None:
        return {"last": _num(td.get_text(strip=True)), "moves": [], "open": None}
    last = _num(div.find(string=True, recursive=False) or "")
    moves, opening, in_open = [], None, False
    tab = div.select_one("div.odds-change-div table")
    if tab is not None:
        for tr in tab.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) == 1 and "title" in (tds[0].get("class") or []):
                in_open = "opening" in tds[0].get_text(strip=True).lower()
                continue
            if len(tds) >= 2:
                when = _stamp_utc(tds[0].get_text(strip=True), year, month)
                val = _num(tds[1].get_text(strip=True))
                if in_open:
                    opening = (when, val)
                else:
                    moves.append((when, val))
    return {"last": last, "moves": moves, "open": opening}


CLOCK = re.compile(r'(\d{1,2})\.(\d{1,2})\.\s+(\d{1,2}):(\d{2}),\s*<span class="timezone" title="([^"]*)"')


def _slices(html: str) -> tuple[str, str, dict]:
    """The two parts of a match page that are parsed (the page is ~0.3-0.5 MB, mostly head-to-head tables): the match
    header (date, event, names, score) and the Home/Away odds table; plus the header clock, read by pattern."""
    i0 = html.find('<div id="center">')
    if i0 < 0:
        raise ValueError("no #center block: not a match page")
    g = html.find('class="result gDetail', i0)
    gend = html.find("</table>", g) if g > 0 else -1
    top = html[i0: gend + 8] if gend > 0 else html[i0: i0 + 30000]
    odds = ""
    b = html.find(">Betting odds<", i0)
    if b > 0:
        ha = re.search(r'<li id="(oddsMenu-\d+)"[^>]*>\s*<a[^>]*>\s*Home/Away[^<]*</a>', html[b: b + 6000])
        if ha:
            idpos = html.find(f'id="{ha.group(1)}-data"', b)
            if idpos > 0:
                start = html.rfind("<div", 0, idpos)
                nxt = html.find('<div id="oddsMenu-', idpos + 10)
                odds = (f'<ul class="tabs"><li id="{ha.group(1)}">{re.sub("<[^>]+>", "", ha.group(0))}</li></ul>'
                        + html[start: nxt if nxt > 0 else idpos + 400000])
    m = CLOCK.search(html[:i0])
    clock = {"tz_label": m.group(5) if m else None,
             "clock": f"{m.group(1)}.{m.group(2)}. {m.group(3)}:{m.group(4)}" if m else None}
    return top, odds, clock


def parse_match(html: str) -> dict:
    """A match page -> the match and its Home/Away odds by book."""
    top, odds, clock = _slices(html)
    c = BeautifulSoup(top + odds, "html.parser")
    info = c.select_one("div.box.boxBasic.lGray")
    info_txt = info.get_text(" ", strip=True) if info is not None else ""
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})\s*,?\s*(\d{1,2}:\d{2})?", info_txt)
    day = dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None
    hhmm = m.group(4) if m else None
    ev = info.find("a", href=True) if info is not None else None
    parts = [p.strip() for p in info_txt.split(",")]
    names = c.select("table.gDetail th.plName a")
    score = c.select_one("table.gDetail td.gScore")
    res = {"date": day.isoformat() if day else None, "time_berlin": hhmm,
           "start_utc": berlin_to_utc(day, hhmm) if day else None,
           "event": ev.get_text(strip=True) if ev is not None else None, "event_href": ev.get("href") if ev else None,
           "round": parts[-2] if len(parts) >= 4 else None, "surface": parts[-1] if len(parts) >= 4 else None,
           "info": info_txt,
           "p1": names[0].get_text(" ", strip=True) if len(names) > 0 else None,
           "p1_slug": names[0].get("href") if len(names) > 0 else None,
           "p2": names[1].get_text(" ", strip=True) if len(names) > 1 else None,
           "p2_slug": names[1].get("href") if len(names) > 1 else None,
           "score": score.get_text(" ", strip=True) if score is not None else None,
           "ha_tab": None, "books": {}, **clock}
    tab = None
    for li in c.select("ul.tabs li[id^=oddsMenu-]"):
        label = li.get_text(" ", strip=True)
        if label.lower().startswith("home/away"):
            res["ha_tab"] = label
            tab = c.select_one(f"#{li['id']}-data table")
            break
    if tab is None or day is None:
        return res
    for tr in tab.select("tr"):
        if "head" in (tr.get("class") or []) or tr.find_parent("div", class_="odds-change-div") is not None:
            continue
        name_td, k1, k2 = tr.select_one("td.first"), tr.find("td", class_="k1"), tr.find("td", class_="k2")
        if name_td is None or k1 is None or k2 is None:
            continue
        t = name_td.select_one("span.t")
        res["books"][(t or name_td).get_text(strip=True)] = {"k1": _side(k1, day.year, day.month),
                                                            "k2": _side(k2, day.year, day.month)}
    return res


# --------------------------------------------------------------------------------------
# the pulls
# --------------------------------------------------------------------------------------
def _final(path: Path, last_day: dt.date | None) -> bool:
    """A page on disk is final when it was fetched FINAL_AFTER_DAYS after the last day it covers."""
    if not path.exists() or last_day is None:
        return False
    fetched = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).date()
    return fetched >= last_day + dt.timedelta(days=FINAL_AFTER_DAYS)


def pull_calendar(client: Client, years: list[int]) -> list[dict]:
    rows = []
    for year in years:
        for tour in TOURS:
            p = calendar_path(tour, year)
            if not _final(p, dt.date(year, 12, 31)):
                client.get(f"calendar_{tour}_{year}", f"{BASE}/calendar/{TOURS[tour]}/{year}/", p)
            rows += parse_calendar(read_raw(p), tour, year)
    return rows


def calendar_rows() -> pd.DataFrame:
    rows = []
    for p in sorted((RAW / "calendar").glob("*_*.html.gz")):
        tour, year = p.name.split(".")[0].split("_")
        rows += parse_calendar(read_raw(p), tour, int(year))
    return pd.DataFrame(rows).drop_duplicates(["tour", "year", "slug"])


def pull_events(client: Client, since: dt.date, until: dt.date) -> int:
    cal = calendar_rows()
    cal = cal[(cal.type == "main") & cal.start.notna() & ~cal.slug.str.contains(SKIP)].copy()
    cal["start_d"] = pd.to_datetime(cal.start).dt.date
    todo = cal[(cal.start_d >= since - dt.timedelta(days=21)) & (cal.start_d <= until)]
    n = 0
    for r in todo.itertuples():
        p = event_path(r.tour, r.year, r.slug)
        if _final(p, r.start_d + dt.timedelta(days=16)):
            continue
        client.get(f"event_{r.tour}_{r.year}_{r.slug}", f"{BASE}{r.href}", p)
        n += 1
    return n


def event_index() -> pd.DataFrame:
    """Every listed match of every event page on disk, with the event's calendar row."""
    cal = calendar_rows()
    cal["start_d"] = pd.to_datetime(cal.start).dt.date
    rows = []
    for r in cal.itertuples():
        p = event_path(r.tour, r.year, r.slug)
        if not p.exists() or r.start_d is None or pd.isna(r.start_d):
            continue
        for m in parse_event(read_raw(p), r.tour, r.start_d):
            rows.append({"tour": r.tour, "year": r.year, "slug": r.slug, "event_name": r.name, "event_type": r.type,
                         "event_start": r.start, "surface_cal": r.surface, "draw": r.draw, **m})
    df = pd.DataFrame(rows)
    return df.drop_duplicates("te_id") if len(df) else df


def pull_matches(client: Client, since: dt.date, until: dt.date, max_n: int | None, newest_first: bool) -> int:
    idx = event_index()
    if idx.empty:
        raise Stop("no event pages on disk: run --events first")
    idx = idx[idx.day.notna()].copy()
    idx["d"] = pd.to_datetime(idx.day).dt.date
    played = idx.sets1.fillna("").str.strip().ne("") | idx.sets2.fillna("").str.strip().ne("")
    today = dt.datetime.now(dt.timezone.utc).date()
    todo = idx[(idx.d >= since) & (idx.d <= until) & (idx.d < today) & played]
    todo = todo.sort_values(["d", "te_id"], ascending=not newest_first)
    n = 0
    for r in todo.itertuples():
        p = match_path(int(r.te_id))
        if p.exists():
            continue
        client.get(f"match_{r.te_id}", f"{BASE}/match-detail/?id={int(r.te_id)}", p)
        n += 1
        if n % 100 == 0:
            C.log(f"[{SOURCE}] {n} match pages fetched (last: {r.day} {r.slug})")
        if max_n is not None and n >= max_n:
            break
    return n


# --------------------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------------------
def stage() -> dict:
    idx = event_index()
    by_id = {int(r.te_id): r for r in idx.itertuples()} if len(idx) else {}
    receipts = C.Receipts(SOURCE, root=RAW.parent)
    mrows, orows, vrows = [], [], []
    for p in sorted((RAW / "matches").glob("*/*.html.gz")):
        te_id = int(p.name.split(".")[0])
        try:
            d = parse_match(read_raw(p))
        except ValueError as err:
            C.log(f"[{SOURCE}] {p.name}: {err}")
            continue
        rec = receipts.get(f"match_{te_id}") or {}
        e = by_id.get(te_id)
        mrows.append({"te_id": te_id, "tour": getattr(e, "tour", None), "slug": getattr(e, "slug", None),
                      "event_year": getattr(e, "year", None), "event_type": getattr(e, "event_type", None),
                      **{k: v for k, v in d.items() if k != "books"}, "n_books": len(d["books"]),
                      "has_pinnacle": "Pinnacle" in d["books"], "retrieved_at": rec.get("retrieved_at"),
                      "sha256": rec.get("sha256"), "raw": C.rel(p)})
        for book, sides in d["books"].items():
            o = {"te_id": te_id, "book": book}
            for k in ("k1", "k2"):
                s = sides[k]
                last_t = max((w for w, _ in s["moves"] if w is not None), default=None)
                o.update({f"{k}_last": s["last"], f"{k}_open": s["open"][1] if s["open"] else None,
                          f"{k}_open_t": s["open"][0].isoformat() if s["open"] and s["open"][0] else None,
                          f"{k}_n_moves": len(s["moves"]),
                          f"{k}_last_t": last_t.isoformat() if last_t else None})
                for w, v in s["moves"]:
                    vrows.append({"te_id": te_id, "book": book, "side": k, "t_utc": w.isoformat() if w else None,
                                  "odds": v, "opening": False})
                if s["open"]:
                    vrows.append({"te_id": te_id, "book": book, "side": k,
                                  "t_utc": s["open"][0].isoformat() if s["open"][0] else None,
                                  "odds": s["open"][1], "opening": True})
            orows.append(o)
    DUMP.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, rows in (("events", idx), ("matches", pd.DataFrame(mrows)), ("odds", pd.DataFrame(orows)),
                       ("moves", pd.DataFrame(vrows))):
        df = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
        path = DUMP / f"{name}.parquet"
        tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")     # one per process: two runs may stage at once
        df.to_parquet(tmp, index=False)
        tmp.replace(path)
        out[name] = len(df)
    C.log(f"[{SOURCE}] staged: {out}")
    return out


# --------------------------------------------------------------------------------------
# the link to the model's frame
# --------------------------------------------------------------------------------------
STAGE0_PLAYERS = C.PROJECT_ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_match_players.parquet"


def _same_tokens(a: frozenset, b: frozenset) -> bool:
    if not a or not b:
        return False
    if a == b or (len(a) >= 2 and a <= b) or (len(b) >= 2 and b <= a):
        return True
    return len(a & b) >= 2


def _same_player(te_name, s0_name) -> bool:
    return _same_tokens(name_tokens(te_name), name_tokens(s0_name))


def _close_tokens(a: frozenset, b: frozenset) -> bool:
    """The second pass's looser test, used only inside one event: a shared word of 4 letters or more (the surname)
    and, of the words left, at least one first letter in common, so spellings of a first name meet ("Yulia" /
    "Yuliia", "Darya" / "Daria", "Abedallah" / "Abdullah", "Jeffrey John" / "J.J.", "Yeon Woo" / "Yeonwoo")."""
    if _same_tokens(a, b):
        return True
    if a and b and sorted("".join(sorted(a))) == sorted("".join(sorted(b))):
        return True                                   # the same letters: a name split or joined ("Ma Yexin" / "Ye Xin Ma")
    common = a & b
    if not any(len(t) >= 4 for t in common):
        return False
    rest_a, rest_b = a - common, b - common
    if not rest_a or not rest_b:
        return True
    return bool({t[0] for t in rest_a} & {t[0] for t in rest_b})


def _same_round(frame_round: str, te_round) -> bool:
    """Only used to split a pair that met twice: the frame's F / SF / QF against the site's round title; RR against
    any other title."""
    te_round = str(te_round or "").lower()
    named = {"F": "final", "SF": "semifinal", "QF": "quarterfinal"}
    if frame_round in named:
        return te_round == named[frame_round]
    if frame_round == "RR":
        return te_round not in named.values()
    return True


REFEREE_SKIP = ("Pinnacle", "Betfair Exchange")       # not referees of Pinnacle's row: itself, and an exchange


def books_referee(od: pd.DataFrame) -> pd.DataFrame:
    """Per site match: the median log-odds (the site's first player against the second) of its books other than
    REFEREE_SKIP, how many price it, and their interquartile range. A Pinnacle row far from it is a recording error of
    the site (three in 2026: research note, 22 Oct 2026)."""
    o = od[~od["book"].isin(REFEREE_SKIP)]
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.log((1.0 / o["k1_last"].astype(float)) / (1.0 / o["k2_last"].astype(float)))
    o = o.assign(z=z)[np.isfinite(z)]
    g = o.groupby("te_id")["z"]
    return pd.DataFrame({"z": g.median(), "n": g.size(), "iqr": g.quantile(0.75) - g.quantile(0.25)})


def _hits(r, w: pd.DataFrame, test) -> list:
    """The site's matches in `w` whose two players pass `test` against the frame row's, each with whether A is the
    site's second player; a pair that met twice (the Finals: round robin, then the final) split by the round."""
    hits = []
    for t in w.itertuples():
        if test(t.t1, r.tA) and test(t.t2, r.tB):
            hits.append((t, False))
        elif test(t.t1, r.tB) and test(t.t2, r.tA):
            hits.append((t, True))
    if len(hits) > 1:
        hits = [h for h in hits if _same_round(r.match_id.split("|")[2], h[0].round)] or hits
    return hits


def link(frame_path: Path, since: dt.date, out_path: Path | None = None,
         players_path: Path = STAGE0_PLAYERS) -> dict:
    """link_frame, written to out_path (default the staged link.parquet); returns the counts."""
    df, how = link_frame(frame_path, since, players_path)
    path = out_path or DUMP / "link.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")     # one per process: two runs may stage at once
    df.to_parquet(tmp, index=False)
    tmp.replace(path)
    C.log(f"[{SOURCE}] link: {how}")
    return how


def link_frame(frame_path: Path, since: dt.date, players_path: Path = STAGE0_PLAYERS) -> tuple[pd.DataFrame, dict]:
    """The frame's matches from `since` on, each linked to one TennisExplorer match of the same tour.
    Pass 1: the site's day within [the frame's tournament date - 3, + 21] days and both players' names the same
    (word sets); one candidate only. Pass 1's links name the site's event for each frame tournament (the most common).
    Pass 2, for the rest: only that event's matches, the same names first, else the looser test (_close_tokens: one
    surname word shared, a first initial in common). Two candidates or none leave the row unlinked, counted.
    Returns one row per linked match, with Pinnacle's last prices for A and B and how it was linked, and the counts.
    The players' names come from Stage 0's match players (players_path: the build's own tree when it has one)."""
    fr = pd.read_parquet(frame_path, columns=["match_id", "tour", "season", "tournament_date"])
    fr = fr[fr.tournament_date >= pd.Timestamp(since)].copy()
    pl = pd.read_parquet(players_path, columns=["match_id", "side", "player_name"])
    pl = pl[pl.match_id.isin(fr.match_id)].pivot(index="match_id", columns="side", values="player_name")
    fr = fr.join(pl, on="match_id")
    fr["event_key"] = fr.match_id.str.split("|").str[1]
    tm = pd.read_parquet(DUMP / "matches.parquet")
    tm = tm[tm.date.notna()].copy()
    tm["d"] = pd.to_datetime(tm.date)
    tm["t1"], tm["t2"] = tm.p1.map(name_tokens), tm.p2.map(name_tokens)
    tm["ev"] = tm.tour.astype(str) + "/" + tm.slug.astype(str) + "/" + tm.event_year.astype(str)
    fr["tA"], fr["tB"] = fr.A.map(name_tokens), fr.B.map(name_tokens)
    od = pd.read_parquet(DUMP / "odds.parquet")
    pin = od[od.book == "Pinnacle"].set_index("te_id")
    refs = books_referee(od)
    by_tour = {t: g for t, g in tm.groupby("tour")}
    found, left = {}, []
    for r in fr.itertuples():
        g = by_tour.get(r.tour)
        if g is None:
            left.append(r)
            continue
        w = g[(g.d >= r.tournament_date - pd.Timedelta(days=3)) & (g.d <= r.tournament_date + pd.Timedelta(days=21))]
        hits = _hits(r, w, _same_tokens)
        if len(hits) == 1:
            found[r.match_id] = (hits[0], "names")
        else:
            left.append(r)
    ev_of = {}
    if found:
        ev = pd.DataFrame([(mid.split("|")[1], h[0].ev) for mid, (h, _) in found.items()], columns=["key", "ev"])
        ev_of = ev.groupby("key").ev.agg(lambda s: s.value_counts().index[0]).to_dict()
    by_ev = {e: g for e, g in tm.groupby("ev")}
    how = {"linked": 0, "linked_pass2_names": 0, "linked_pass2_close": 0, "none": 0, "several": 0}
    for r in left:
        w = by_ev.get(ev_of.get(r.event_key))
        if w is None:
            how["none"] += 1
            continue
        hits, kind = _hits(r, w, _same_tokens), "event, names"
        if not hits:
            hits, kind = _hits(r, w, _close_tokens), "event, close names"
        if len(hits) == 1:
            found[r.match_id] = (hits[0], kind)
            how["linked_pass2_names" if kind == "event, names" else "linked_pass2_close"] += 1
        else:
            how["none" if not hits else "several"] += 1
    rows = []
    for r in fr.itertuples():
        if r.match_id not in found:
            continue
        (t, flip), kind = found[r.match_id]
        how["linked"] += 1
        row = {"match_id": r.match_id, "te_id": int(t.te_id), "a_is_p2": flip, "link_how": kind,
               "te_p1": t.p1, "te_p2": t.p2, "te_date": t.date,
               "start_utc": t.start_utc, "n_books": t.n_books, "has_pinnacle": bool(t.has_pinnacle)}
        if t.te_id in refs.index:                       # the site's other books, for A (log-odds)
            rf = refs.loc[t.te_id]
            row.update({"books_z_a": -rf["z"] if flip else rf["z"], "books_n": int(rf["n"]), "books_iqr": rf["iqr"]})
        if t.te_id in pin.index:
            p = pin.loc[t.te_id]
            a, b = ("k2", "k1") if flip else ("k1", "k2")
            row.update({"pin_a": p[f"{a}_last"], "pin_b": p[f"{b}_last"], "pin_open_a": p[f"{a}_open"],
                        "pin_open_b": p[f"{b}_open"], "pin_open_t": p[f"{a}_open_t"],
                        "pin_last_t": max([x for x in (p["k1_last_t"], p["k2_last_t"]) if isinstance(x, str)],
                                          default=None),
                        "pin_n_moves": int(p["k1_n_moves"]) + int(p["k2_n_moves"])})
        rows.append(row)
    df = pd.DataFrame(rows)
    how["frame_rows"] = int(len(fr))
    how["with_pinnacle"] = int(df.pin_a.notna().sum()) if len(df) and "pin_a" in df else 0
    return df, how


def refresh(since: dt.date, until: dt.date | None = None, pause: float = PAUSE, max_matches: int | None = None) -> dict:
    """Bring the raw pages up to date for the matches played from `since` to `until` (default today): the calendars of
    those years, the pages of the events not yet final, every finished match's page not on disk; then restage.
    Raises Stop on a block (nothing is staged then). Used by the daily download and by the model's odds step."""
    until = until or dt.datetime.now(dt.timezone.utc).date()
    client = Client(C.Receipts(SOURCE, root=RAW.parent), pause=pause)
    years = list(range(since.year, until.year + 1))
    pull_calendar(client, years)
    n_events = pull_events(client, since, until)
    n_matches = pull_matches(client, since, until, max_matches, newest_first=True)
    staged = stage()
    return {"since": since.isoformat(), "until": until.isoformat(), "requests": client.sent,
            "event_pages": n_events, "match_pages": n_matches, "staged": staged}


# --------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--calendar", nargs="+", type=int, metavar="YEAR")
    ap.add_argument("--events", action="store_true")
    ap.add_argument("--matches", action="store_true")
    ap.add_argument("--stage", action="store_true")
    ap.add_argument("--link", type=Path, metavar="MODEL_FRAME")
    ap.add_argument("--since", type=dt.date.fromisoformat, default=dt.date(2025, 8, 1))
    ap.add_argument("--until", type=dt.date.fromisoformat, default=dt.datetime.now(dt.timezone.utc).date())
    ap.add_argument("--max", type=int)
    ap.add_argument("--oldest-first", action="store_true", help="matches oldest first (default: newest first)")
    ap.add_argument("--pause", type=float, default=PAUSE)
    a = ap.parse_args(argv)
    client = Client(C.Receipts(SOURCE, root=RAW.parent), pause=a.pause)
    try:
        if a.calendar:
            rows = pull_calendar(client, a.calendar)
            C.log(f"[{SOURCE}] calendar: {len(rows)} events listed")
        if a.events:
            C.log(f"[{SOURCE}] events: {pull_events(client, a.since, a.until)} pages fetched")
        if a.matches:
            n = pull_matches(client, a.since, a.until, a.max, newest_first=not a.oldest_first)
            C.log(f"[{SOURCE}] matches: {n} pages fetched")
    except Stop as err:
        C.log(f"[{SOURCE}] STOPPED: {err} ({client.sent} requests sent)")
        return 2
    if a.stage:
        stage()
    if a.link:
        print(json.dumps(link(a.link, a.since)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
