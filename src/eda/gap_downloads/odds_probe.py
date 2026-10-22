"""Work package P11's probe: which public site holds bookmakers' opening and closing odds for Challenger, WTA 125 and
ITF matches (docs/studies/gap_downloads/collection-plan.md, P11; process log in docs/studies/gap_downloads/).

The sample (offline, seeded): one week per year (2019, 2022, 2025, 2026) among the weeks that hold a WTA 125 edition and
several men's Challengers and ITF editions of both tours; every map match of that week's editions at the levels CH,
CHQ, ITF and ITFQ, both tours. Most lower-level rows carry only their tournament's Monday, so each site is read by day
over the week's whole span of play: the Saturday before (qualifying) to the Sunday after, 9 days. Each match gets a
seeded rank inside its stratum (year, tour, level); per site, the first DETAIL_MAIN main-draw and DETAIL_QUAL qualifying
matches in rank order that the site lists with a price get the match-level reading.

Per site, through the project's client (src/ingest/point_sources/common.py: paced, one request at a time, receipts,
answers gzipped under data/raw/odds_probe/<site>/, a --max-requests budget, a stop on a block):
    betexplorer     the day's tennis results (one page a day), then each detail match's odds call
                    (/match-odds-old/<id>/1/ha/1/en/: per book each side's last price and the time it was set); the
                    opening of a few cells from the page's own history call (/archive-odds/...)
    tennisexplorer  the day's results, men and women (/results/?type=<atp|wta>-single&...): every singles match of the
                    day with the books' average last price; then each detail match's page (per book the last price,
                    every change with its time and the opening with its time; src/ingest/tennisexplorer.py's parser)
    oddsportal      whether its results pages and odds feed answer this client, and what they hold (a few requests)
Evidence (data/studies/gap_downloads/odds_probe_*): counts and flags only, never a price (the repository is public).

    ./python.sh src/eda/gap_downloads/odds_probe.py --sample
    ./python.sh src/eda/gap_downloads/odds_probe.py --site betexplorer --max-requests 200
    ./python.sh src/eda/gap_downloads/odds_probe.py --report          (offline: every measure from what is on disk)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P        # noqa: E402
from src.ingest.public_dump import common as C          # noqa: E402

SEED = 20261022
YEARS = (2019, 2022, 2025, 2026)
LEVELS = ("CH", "CHQ", "ITF", "ITFQ")
MAIN, QUAL = ("CH", "ITF"), ("CHQ", "ITFQ")
DETAIL_MAIN, DETAIL_QUAL = 5, 2
LAST_WEEK_2026 = dt.date(2026, 9, 21)      # the map of 16 Oct: the last weeks' lower levels are still filling in
MAP = PROJECT_ROOT / "data" / "studies" / "data_map" / "matches.parquet"
STUDY = PROJECT_ROOT / "data" / "studies" / "gap_downloads"
RAW = PROJECT_ROOT / "data" / "raw" / "odds_probe"
SAMPLE = STUDY / "odds_probe_sample.csv"


# --------------------------------------------------------------------------------------------------------------------
# the sample
# --------------------------------------------------------------------------------------------------------------------
def week_of(d: pd.Series, draw: pd.Series) -> pd.Series:
    """The Monday of each match's edition week: the date's Monday, except qualifying dated on a Saturday or Sunday
    (played before its edition's Monday), which belongs to the next Monday."""
    d = pd.to_datetime(d)
    monday = d - pd.to_timedelta(d.dt.dayofweek, unit="D")
    weekend_qual = draw.eq("qual") & d.dt.dayofweek.ge(5)
    return (monday + pd.to_timedelta(np.where(weekend_qual, 7, 0), unit="D")).dt.normalize()


def eligible_weeks(m: pd.DataFrame) -> pd.DataFrame:
    """Per year and week: the editions (tournament names) per tour and level, and whether the week qualifies."""
    main = m[m.level.isin(MAIN)]
    g = main.groupby(["year", "wk", "tour", "level"]).tname.nunique().unstack(["tour", "level"], fill_value=0)
    g.columns = [f"{t}_{lv}" for t, lv in g.columns]
    for col in ("M_CH", "W_CH", "M_ITF", "W_ITF"):
        if col not in g:
            g[col] = 0
    g["ok"] = (g.W_CH >= 1) & (g.M_CH >= 3) & (g.M_ITF >= 4) & (g.W_ITF >= 4)
    wk = g.index.get_level_values("wk")
    g.loc[(g.index.get_level_values("year") == 2026) & (wk > pd.Timestamp(LAST_WEEK_2026)), "ok"] = False
    return g.reset_index()


def draw_sample(m: pd.DataFrame, seed: int = SEED, years=YEARS) -> tuple[pd.DataFrame, dict]:
    """The sampled weeks' matches, each with its stratum rank. ``m`` is the map's matches table."""
    m = m[m.level.isin(LEVELS) & m.year.isin(years)].copy()
    m["wk"] = week_of(m.d, m.draw)
    weeks = eligible_weeks(m)
    rng = np.random.default_rng(seed)
    chosen = {}
    for year in years:
        ok = weeks[(weeks.year == year) & weeks.ok].sort_values("wk")
        if ok.empty:
            continue
        chosen[year] = ok.wk.iloc[int(rng.integers(len(ok)))]
    s = m[m.wk.eq(m.year.map(chosen))].copy()
    s = s.sort_values(["year", "tour", "level", "uid"]).reset_index(drop=True)
    s["rank"] = 0
    for _, idx in s.groupby(["year", "tour", "level"]).groups.items():
        s.loc[idx, "rank"] = rng.permutation(len(idx)) + 1
    s["first_day"] = (s.wk - pd.Timedelta(days=2)).dt.date
    s["last_day"] = (s.wk + pd.Timedelta(days=6)).dt.date
    info = {"seed": seed, "weeks": {str(y): str(w.date()) for y, w in chosen.items()},
            "eligible_weeks": {str(y): int(((weeks.year == y) & weeks.ok).sum()) for y in years},
            "matches": int(len(s)),
            "by_stratum": {f"{y} {t} {lv}": int(n) for (y, t, lv), n in s.groupby(["year", "tour", "level"]).size().items()}}
    return s, info


def write_sample(seed: int = SEED) -> dict:
    m = pd.read_parquet(MAP, columns=["uid", "tour", "level", "draw", "year", "d", "name1", "name2", "tname", "creator"])
    s, info = draw_sample(m, seed)
    cols = ["uid", "year", "tour", "level", "draw", "d", "wk", "first_day", "last_day", "tname", "name1", "name2",
            "creator", "rank"]
    STUDY.mkdir(parents=True, exist_ok=True)
    s[cols].to_csv(SAMPLE, index=False)
    info["map_built"] = dt.datetime.fromtimestamp(MAP.stat().st_mtime, dt.timezone.utc).isoformat(timespec="seconds")
    (STUDY / "odds_probe_sample.json").write_text(json.dumps(info, indent=1) + "\n", encoding="utf-8")
    return info


def read_sample() -> pd.DataFrame:
    s = pd.read_csv(SAMPLE, parse_dates=["d", "wk"])
    s["first_day"] = pd.to_datetime(s.first_day).dt.date
    s["last_day"] = pd.to_datetime(s.last_day).dt.date
    return s


def sample_days(s: pd.DataFrame) -> list[dt.date]:
    days = set()
    for (a, b) in s[["first_day", "last_day"]].drop_duplicates().itertuples(index=False):
        days |= {a + dt.timedelta(days=i) for i in range((b - a).days + 1)}
    return sorted(days)


# --------------------------------------------------------------------------------------------------------------------
# names: the map's full names against a site's "Surname I." / "Surname F. G."
# --------------------------------------------------------------------------------------------------------------------
def words(name) -> list[str]:
    if not isinstance(name, str):
        return []
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(\d{4}\)", " ", s)
    return [w for w in re.split(r"[^a-z]+", s) if w]


def site_name(name) -> tuple[frozenset, str]:
    """'Alcala Gurri M.' -> ({'alcala', 'gurri'}, 'm'); 'Kukushkin M.' -> ({'kukushkin'}, 'm'); no initial -> ''."""
    if not isinstance(name, str):
        return frozenset(), ""
    raw = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower().strip()
    toks = raw.split()
    ini = []
    while len(toks) > 1 and re.fullmatch(r"[a-z](?:[.-]+[a-z])*\.", toks[-1]):    # "m.", "j-l.", "j.-l."
        ini.insert(0, toks.pop())
    sur = " ".join(toks)
    return frozenset(w for w in re.split(r"[^a-z]+", sur) if w), (ini[0][0] if ini else "")


def same_player(map_name, site) -> bool:
    """A site name matches a map name when every surname word is among the map name's words and, if the site gives an
    initial, another word of the map name starts with it (or the surname word itself, for a one-word map name)."""
    sur, ini = site
    w = words(map_name)
    if not sur or not w or not sur <= set(w):
        return False
    if not ini:
        return True
    rest = [x for x in w if x not in sur] or w
    return any(x.startswith(ini) for x in rest)


def link_rows(sample: pd.DataFrame, rows: pd.DataFrame) -> pd.DataFrame:
    """Each sample match against a site's listed rows (columns: site_id, tour, day, p1, p2, priced): the one row of the
    same tour, dated first_day..last_day, whose two players match the map's two in either order. Returns the sample
    with site_id, site_day, priced and link ('one', 'none', 'several')."""
    rows = rows.reset_index(drop=True).copy()
    rows["s1"] = rows.p1.map(site_name)
    rows["s2"] = rows.p2.map(site_name)
    index: dict[tuple[str, str], set[int]] = {}             # (tour, surname word) -> rows naming it
    for i, (t, s1, s2) in enumerate(zip(rows.tour, rows.s1, rows.s2)):
        for w in s1[0] | s2[0]:
            index.setdefault((t, w), set()).add(i)
    out = []
    for r in sample.itertuples():
        cand = set()
        for w in set(words(r.name1)):
            cand |= index.get((r.tour, w), set())
        hit = []
        for i in sorted(cand):
            x = rows.iloc[i]
            if not (r.first_day <= x.day <= r.last_day):
                continue
            if (same_player(r.name1, x.s1) and same_player(r.name2, x.s2)) or \
                    (same_player(r.name1, x.s2) and same_player(r.name2, x.s1)):
                hit.append(x)
        if len(hit) > 1:                                        # the same pair twice (qualifying, then main draw)
            ids = {h.site_id for h in hit}
            hit = hit if len(ids) > 1 else hit[:1]
        if len(hit) == 1:
            h = hit[0]
            out.append({"uid": r.uid, "site_id": h.site_id, "site_day": h.day, "site_event": h.event,
                        "priced": bool(h.priced), "link": "one"})
        else:
            out.append({"uid": r.uid, "site_id": None, "site_day": None, "site_event": None, "priced": False,
                        "link": "none" if not hit else "several"})
    return sample.merge(pd.DataFrame(out), on="uid", how="left")


def detail_pick(linked: pd.DataFrame) -> pd.DataFrame:
    """Per stratum, the first DETAIL_MAIN (main draw) or DETAIL_QUAL (qualifying) matches in rank order that the site
    lists with a price."""
    ok = linked[linked.link.eq("one") & linked.priced].sort_values(["year", "tour", "level", "rank"])
    k = ok.level.map(lambda lv: DETAIL_MAIN if lv in MAIN else DETAIL_QUAL)
    ok = ok.assign(_k=k.values, _n=ok.groupby(["year", "tour", "level"]).cumcount() + 1)
    return ok[ok._n <= ok._k].drop(columns=["_k", "_n"])


# --------------------------------------------------------------------------------------------------------------------
# fetching (shared)
# --------------------------------------------------------------------------------------------------------------------
class Site:
    """One site's client, receipts and raw folder: every answer gzipped under data/raw/odds_probe/<site>/."""

    def __init__(self, name: str, base: str, max_requests: int, impersonate: str = "chrome",
                 headers: dict | None = None):
        self.name, self.base = name, base
        self.receipts = C.Receipts(name, root=RAW)
        self.client = P.Client(impersonate, min_interval=2.0, jitter=1.0, max_requests=max_requests,
                               headers=headers)
        self.log: list[dict] = []

    def path(self, *parts: str) -> Path:
        return RAW.joinpath(self.name, *parts)

    def get(self, name: str, url: str, dest: Path, validator=None, headers: dict | None = None) -> dict:
        r = P.fetch(self.client, url, dest, self.receipts, name=name, validator=validator, compress=True,
                    headers=headers)
        self.log.append({"name": name, "status": r.get("status"), "error": r.get("error"),
                         "skipped": bool(r.get("skipped"))})
        if r.get("error") and not r.get("skipped"):
            P.log(f"[odds_probe:{self.name}] {name}: {r.get('error')}")
        return r

    def ok(self, r: dict, dest: Path) -> bool:
        return r.get("status") == 200 and not r.get("error") and dest.exists()


def json_or_html(body: bytes):
    head = body[:64].lstrip()
    return None if head.startswith((b"{", b"[", b"<")) else "response is neither JSON nor HTML"


# --------------------------------------------------------------------------------------------------------------------
# BetExplorer
# --------------------------------------------------------------------------------------------------------------------
BE = "https://www.betexplorer.com"
BE_TZ = dt.timezone(dt.timedelta(hours=1))      # its data-dt-now read 05:46 at 04:46 UTC on 22 Oct 2026: UTC+1
BE_GROUP = re.compile(r"^(?P<cat>ATP|WTA|Challenger Men|Challenger Women|ITF Men|ITF Women)\s*-\s*Singles:\s*"
                      r"(?P<event>.+?)(?:,\s*(?P<surface>[a-z ]+))?$", re.I)


def be_stamp(s: str | None) -> dt.datetime | None:
    """'6,1,2026,2,10' (day, month, year, hour, minute; the site's UTC+1) -> UTC."""
    try:
        d, mo, y, h, mi = (int(x) for x in str(s).split(","))
        return dt.datetime(y, mo, d, h, mi, tzinfo=BE_TZ).astimezone(dt.timezone.utc)
    except (ValueError, TypeError):
        return None


def be_day_rows(html: str) -> list[dict]:
    """BetExplorer's tennis results of a day -> one row per singles match: its code, start (UTC), category, event,
    the two players as listed ('Surname I.'), the match path."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    out, group = [], None
    for tr in soup.select("table.table-main tr"):
        if "js-tournament" in (tr.get("class") or []):
            group = BE_GROUP.match(tr.get_text(" ", strip=True))
            continue
        if group is None or not tr.get("data-dt"):
            continue
        a = tr.select_one("a.table-main__teamsLink")
        home = tr.select_one(".table-main__teamLine--home")
        away = tr.select_one(".table-main__teamLine--away")
        if a is None or home is None or away is None:
            continue
        m = re.search(r"/([A-Za-z0-9]{8})/?$", a.get("href", ""))
        start = be_stamp(tr.get("data-dt"))
        cat = group.group("cat").lower()
        out.append({"site_id": m.group(1) if m else None, "start_utc": start.isoformat() if start else None,
                    "day": start.date() if start else None,
                    "tour": "W" if ("wta" in cat or "women" in cat) else "M",
                    "category": group.group("cat"), "event": group.group("event"),
                    "p1": home.get_text(" ", strip=True), "p2": away.get_text(" ", strip=True),
                    "href": a.get("href"), "priced": True})
    return [r for r in out if r["site_id"]]


def be_odds(doc: dict) -> dict:
    """The odds call's table (Home/Away) -> per book: name, id, each side's last price and the time it was set (UTC),
    whether the page shows an opening (data-opening-odd) or offers the history call, and the history call's path."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(doc.get("odds") or "", "html.parser")
    books = {}
    for tr in soup.select("table tbody tr"):
        logo = tr.select_one("span.in-bookmaker-logo[title]") or tr.select_one("a.in-bookmaker-logo-link")
        name = logo.get("title") if logo is not None and logo.get("title") else (logo.get_text(strip=True) if logo else None)
        cells = tr.select("td[data-odd]")
        if not name or len(cells) < 2:
            continue
        sides = []
        for td in cells[:2]:
            t = be_stamp(td.get("data-created"))
            sides.append({"odd": float(td["data-odd"]) if re.match(r"^\d+(\.\d+)?$", td.get("data-odd", "")) else None,
                          "set_utc": t.isoformat() if t else None,
                          "opening": td.get("data-opening-odd"), "opening_date": td.get("data-opening-date"),
                          "history": "js-has-aodds" in (td.get("class") or []),
                          "inactive": "inactive" in (td.get("class") or []),
                          "archive": (f"/archive-odds/{td.get('data-oid')}/{td.get('data-bid')}/{td.get('data-bt')}/"
                                      f"{td.get('data-sc')}/{td.get('data-hcp')}/") if td.get("data-oid") else None})
        books[name] = {"bid": tr.get("data-bid"), "sides": sides}
    return books


def be_history(doc, ref: dt.datetime | None = None) -> list[tuple[dt.datetime | None, float | None]]:
    """The history call's answer ([{"date": "26.02. 20:08", "odd": "2.01", "change": "0"}, ...]; the site's UTC+1, no
    year) -> [(UTC time, price)], oldest first (the opening first). The year is the one that puts the date nearest
    ``ref`` (the match's start)."""
    items = doc if isinstance(doc, list) else (doc.get("odds") or doc.get("data") or []) if isinstance(doc, dict) else []
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        t, m = None, re.match(r"^\s*(\d{1,2})\.(\d{1,2})\.(\d{4})?\s+(\d{1,2}):(\d{2})", str(it.get("date") or ""))
        if m:
            d, mo, y, hh, mi = int(m.group(1)), int(m.group(2)), m.group(3), int(m.group(4)), int(m.group(5))
            years = [int(y)] if y else ([ref.year - 1, ref.year, ref.year + 1] if ref is not None else [])
            best = None
            for yy in years:
                try:
                    cand = dt.datetime(yy, mo, d, hh, mi, tzinfo=BE_TZ).astimezone(dt.timezone.utc)
                except ValueError:
                    continue
                gap = abs((cand - ref).total_seconds()) if ref is not None else 0
                if best is None or gap < best[0]:
                    best = (gap, cand)
            t = best[1] if best else None
        odd = it.get("odd") or it.get("odds")
        out.append((t, float(odd) if odd not in (None, "") and re.match(r"^\d+(\.\d+)?$", str(odd)) else None))
    return sorted(out, key=lambda x: (x[0] is None, x[0] or dt.datetime.min.replace(tzinfo=dt.timezone.utc)))


def book_measures(books: dict, start: dt.datetime | None) -> dict:
    """Per match, from {book: {'sides': [{'odd', 'set_utc', 'opening_utc'?}, ...]}}: counts and times, no price."""
    priced = {b: v for b, v in books.items() if len(v["sides"]) >= 2 and all(s.get("odd") for s in v["sides"][:2])}
    last = {}
    for b, v in priced.items():
        ts = [pd.Timestamp(s["set_utc"]) for s in v["sides"][:2] if s.get("set_utc")]
        if ts:
            last[b] = max(ts)
    mins = [(pd.Timestamp(start) - t).total_seconds() / 60 for t in last.values()] if start is not None else []
    pin = [b for b in priced if "pinnacle" in b.lower()]
    pin_last = last.get(pin[0]) if pin else None
    opened = [b for b, v in priced.items() if any(s.get("opening_utc") or s.get("opening") for s in v["sides"][:2])]
    return {"n_books": len(priced), "books": ";".join(sorted(priced)), "pinnacle": bool(pin),
            "n_books_timed": len(last), "n_books_opening": len(opened),
            "last_change_min_before_start_median": float(np.median(mins)) if mins else None,
            "books_last_change_after_start": int(sum(m < 0 for m in mins)) if mins else None,
            "pinnacle_timed": pin_last is not None,
            "pinnacle_last_min_before_start": (pd.Timestamp(start) - pin_last).total_seconds() / 60
            if pin_last is not None and start is not None else None}


def be_listed(site: "Site", s: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for day in sample_days(s):
        dest = site.path("day", f"{day.isoformat()}.html.gz")
        if dest.exists():
            rows += be_day_rows(P.read_bytes(dest).decode("utf-8", "replace"))
    return pd.DataFrame(rows).drop_duplicates("site_id") if rows else pd.DataFrame(
        columns=["site_id", "tour", "day", "event", "p1", "p2", "priced", "start_utc", "href"])


def be_history_path(site: "Site", site_id: str, archive: str) -> Path:
    return site.path("history", f"{site_id}_{re.sub(r'[^A-Za-z0-9]+', '_', archive)[:90]}.json.gz")


def run_betexplorer(max_requests: int, archives: int = 20) -> dict:
    site = Site("betexplorer", BE, max_requests,
                headers={"Accept-Language": "en-US,en;q=0.9", "Referer": f"{BE}/tennis/"})
    s = read_sample()
    stopped = None
    try:
        for day in sample_days(s):
            site.get(f"day_{day.isoformat()}", f"{BE}/results/tennis/?year={day.year}&month={day.month}&day={day.day}",
                     site.path("day", f"{day.isoformat()}.html.gz"), validator=P.html_validator)
        listed = be_listed(site, s)
        picks = detail_pick(link_rows(s, listed))
        hrefs = dict(zip(listed.site_id, listed.href))
        n_arch = 0
        for r in picks.itertuples():
            dest = site.path("odds", f"{r.site_id}.json.gz")
            xhr = {"Referer": f"{BE}{hrefs.get(r.site_id, '/')}", "X-Requested-With": "XMLHttpRequest"}
            got = site.get(f"odds_{r.site_id}", f"{BE}/match-odds-old/{r.site_id}/1/ha/1/en/", dest,
                           validator=P.json_validator, headers=xhr)
            if not site.ok(got, dest) or n_arch >= archives:
                continue
            cell = next((sd for v in be_odds(P.read_json(dest)).values() for sd in v["sides"] if sd.get("archive")),
                        None)
            if cell is not None:
                n_arch += 1
                site.get(f"history_{r.site_id}_{cell['archive']}", f"{BE}{cell['archive']}",
                         be_history_path(site, r.site_id, cell["archive"]), validator=P.json_validator, headers=xhr)
    except (P.Blocked, P.BudgetExhausted) as stop:
        stopped = f"{type(stop).__name__}: {stop}"
    return measure_betexplorer(site, stopped)


def measure_betexplorer(site: "Site", stopped: str | None = None) -> dict:
    """Every BetExplorer measure from the raw files (no request)."""
    s = read_sample()
    listed = be_listed(site, s)
    linked = link_rows(s, listed)
    picks = detail_pick(linked)
    starts = dict(zip(listed.site_id, listed.start_utc))
    details = {}
    for r in picks.itertuples():
        dest = site.path("odds", f"{r.site_id}.json.gz")
        rec = site.receipts.get(f"odds_{r.site_id}") or {}
        if not dest.exists():
            details[r.uid] = {"odds_status": rec.get("status"), "odds_error": rec.get("error") or "not asked"}
            continue
        books = be_odds(P.read_json(dest))
        start = pd.Timestamp(starts[r.site_id]) if starts.get(r.site_id) else None
        hist = None
        for v in books.values():
            for sd in v["sides"]:
                hp = be_history_path(site, r.site_id, sd["archive"]) if sd.get("archive") else None
                if hp is not None and hp.exists():
                    hist = be_history(P.read_json(hp), start.to_pydatetime() if start is not None else None)
        d = book_measures(books, start)
        d.update({"odds_status": 200, "history_read": hist is not None,
                  "history_entries": len(hist) if hist is not None else None,
                  "history_opening_min_before_start": ((start - pd.Timestamp(hist[0][0])).total_seconds() / 60)
                  if hist and hist[0][0] is not None and start is not None else None})
        details[r.uid] = d
    return finish("betexplorer", site, s, listed, linked, picks, details, stopped)


# --------------------------------------------------------------------------------------------------------------------
# TennisExplorer
# --------------------------------------------------------------------------------------------------------------------
TE = "https://www.tennisexplorer.com"
TE_TYPES = {"M": "atp-single", "W": "wta-single"}


def te_validator(body: bytes):
    problem = P.html_validator(body)
    if problem:
        return problem
    head = body[:30000].lower()
    if b"captcha" in head or b"cf-chl" in head or b"<title>" in head and b"tennis explorer" not in head:
        return "not a TennisExplorer page (a challenge page?)"
    return None


def te_day_rows(html: str, day: dt.date, tour: str) -> list[dict]:
    """TennisExplorer's results of a day for one tour (M or W) -> the collector's rows (src/ingest/
    tennisexplorer_lower.day_rows) in the probe's columns: site_id, day, tour, time, event, players, priced."""
    from src.ingest import tennisexplorer_lower as L
    return [{"site_id": r["te_id"], "day": day, "tour": tour, "time_berlin": r["time_berlin"], "event": r["event"],
             "event_href": r["event_href"], "p1": r["p1"], "p2": r["p2"], "priced": r["priced"]}
            for r in L.day_rows(html, day, {"M": "atp", "W": "wta"}[tour])]


def te_books(parsed: dict) -> dict:
    """src/ingest/tennisexplorer.parse_match's books -> book_measures' form: per side the last price, the time it was
    set (its latest change, else its opening) and the opening's time."""
    out = {}
    for book, sides in parsed["books"].items():
        ss = []
        for k in ("k1", "k2"):
            sd = sides[k]
            times = [w for w, _ in sd["moves"] if w is not None]
            op = sd["open"][0] if sd["open"] and sd["open"][0] is not None else None
            set_t = max(times) if times else op
            ss.append({"odd": sd["last"], "set_utc": set_t.isoformat() if set_t else None,
                       "opening_utc": op.isoformat() if op else None, "n_moves": len(sd["moves"])})
        out[book] = {"sides": ss}
    return out


def te_listed(site: "Site", s: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for day in sample_days(s):
        for tour, typ in TE_TYPES.items():
            dest = site.path("day", f"{typ}_{day.isoformat()}.html.gz")
            if dest.exists():
                rows += te_day_rows(P.read_bytes(dest).decode("utf-8", "replace"), day, tour)
    return pd.DataFrame(rows).drop_duplicates("site_id") if rows else pd.DataFrame(
        columns=["site_id", "tour", "day", "event", "p1", "p2", "priced", "time_berlin", "event_href"])


def tennisexplorer_busy() -> int | None:
    """The pid of a running tour-level TennisExplorer collector (python -m src.ingest.tennisexplorer), or None."""
    try:
        import psutil
    except ImportError:
        return None
    me = psutil.Process().pid
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmd = p.info["cmdline"] or []
            if p.info["pid"] != me and "python" in (p.info["name"] or "").lower() and "src.ingest.tennisexplorer" in cmd:
                return p.info["pid"]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def run_tennisexplorer(max_requests: int) -> dict:
    busy = tennisexplorer_busy()
    if busy:
        raise SystemExit(f"[odds_probe:tennisexplorer] the host is in use by pid {busy} (shared rule 3): not started")
    site = Site("tennisexplorer", TE, max_requests, headers={"Accept-Language": "en-US,en;q=0.9"})
    s = read_sample()
    stopped = None
    try:
        for day in sample_days(s):
            for typ in TE_TYPES.values():
                site.get(f"day_{typ}_{day.isoformat()}", f"{TE}/results/?type={typ}&year={day.year}"
                         f"&month={day.month:02d}&day={day.day:02d}", site.path("day", f"{typ}_{day.isoformat()}.html.gz"),
                         validator=te_validator)
        picks = detail_pick(link_rows(s, te_listed(site, s)))
        for r in picks.itertuples():
            mid = int(r.site_id)
            site.get(f"match_{mid}", f"{TE}/match-detail/?id={mid}", site.path("match", f"{mid}.html.gz"),
                     validator=te_validator)
    except (P.Blocked, P.BudgetExhausted) as stop:
        stopped = f"{type(stop).__name__}: {stop}"
    return measure_tennisexplorer(site, stopped)


def measure_tennisexplorer(site: "Site", stopped: str | None = None) -> dict:
    from src.ingest import tennisexplorer as T
    s = read_sample()
    listed = te_listed(site, s)
    linked = link_rows(s, listed)
    picks = detail_pick(linked)
    details = {}
    for r in picks.itertuples():
        dest = site.path("match", f"{int(r.site_id)}.html.gz")
        if not dest.exists():
            rec = site.receipts.get(f"match_{int(r.site_id)}") or {}
            details[r.uid] = {"page_status": rec.get("status"), "page_error": rec.get("error") or "not asked"}
            continue
        parsed = T.parse_match(P.read_bytes(dest).decode("utf-8", "replace"))
        start = pd.Timestamp(parsed["start_utc"]) if parsed.get("start_utc") else None
        d = book_measures(te_books(parsed), start)
        d.update({"page_status": 200, "listed_start_utc": parsed.get("start_utc"), "round": parsed.get("round")})
        details[r.uid] = d
    return finish("tennisexplorer", site, s, listed, linked, picks, details, stopped)


# --------------------------------------------------------------------------------------------------------------------
# evidence (counts and flags only)
# --------------------------------------------------------------------------------------------------------------------
def finish(name: str, site: Site, s: pd.DataFrame, listed: pd.DataFrame, linked: pd.DataFrame, picks: pd.DataFrame,
           details: dict, stopped: str | None) -> dict:
    det = pd.DataFrame.from_dict(details, orient="index") if details else pd.DataFrame()
    det.index.name = "uid"
    t = linked.drop(columns=["name1", "name2"], errors="ignore").copy()
    t["detail"] = t.uid.isin(picks.uid)
    if len(det):
        t = t.merge(det.reset_index(), on="uid", how="left")
    t.to_csv(STUDY / f"odds_probe_{name}.csv.gz", index=False)
    summary = {"site": name, "generated_at": C.utc_now_iso(), "stopped": stopped, "client": site.client.stats(),
               "asked": {k: int(v) for k, v in pd.Series([x["status"] for x in site.log if not x["skipped"]])
                         .value_counts(dropna=False).items()} if site.log else {},
               "listed_rows": int(len(listed)), "by_stratum": strata(t)}
    (STUDY / f"odds_probe_{name}.json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    P.log(f"[odds_probe:{name}] {site.client.requests} requests; stopped: {stopped}; "
          f"written {P.rel(STUDY / f'odds_probe_{name}.json')}")
    return summary


def strata(t: pd.DataFrame) -> dict:
    out = {}
    for (y, tour, lv), g in t.groupby(["year", "tour", "level"]):
        d = g[g.detail]
        row = {"map_matches": int(len(g)), "linked": int(g.link.eq("one").sum()),
               "several": int(g.link.eq("several").sum()), "linked_priced": int((g.link.eq("one") & g.priced).sum()),
               "detail": int(len(d))}
        if len(d) and "n_books" in d:
            def col(name):
                return d[name] if name in d else pd.Series([None] * len(d), index=d.index, dtype=object)

            def med(name):
                x = pd.to_numeric(col(name), errors="coerce")
                return float(x.median()) if x.notna().any() else None

            def count(name):
                return int(col(name).fillna(False).astype(bool).sum())

            row.update({"detail_with_odds": int((pd.to_numeric(col("n_books"), errors="coerce").fillna(0) > 0).sum()),
                        "books_median": med("n_books"), "pinnacle": count("pinnacle"),
                        "pinnacle_timed": count("pinnacle_timed"),
                        "with_opening": int((pd.to_numeric(col("n_books_opening"), errors="coerce").fillna(0) > 0).sum()),
                        "last_change_min_before_start_median": med("last_change_min_before_start_median"),
                        "pinnacle_last_min_before_start_median": med("pinnacle_last_min_before_start")})
        out[f"{y} {tour} {lv}"] = row
    return out


# --------------------------------------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sample", action="store_true", help="draw the seeded sample (offline)")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--site", choices=["betexplorer", "tennisexplorer", "oddsportal"])
    ap.add_argument("--max-requests", type=int, default=200)
    ap.add_argument("--report", action="store_true", help="offline: every measure from the raw files on disk")
    a = ap.parse_args(argv)
    P.configure_stdout()
    if a.sample:
        info = write_sample(a.seed)
        print(json.dumps(info, indent=1))
    runs = {"betexplorer": (run_betexplorer, measure_betexplorer, BE),
            "tennisexplorer": (run_tennisexplorer, measure_tennisexplorer, TE)}
    if a.site in runs and not a.report:
        out = runs[a.site][0](a.max_requests)
        print(json.dumps(out["by_stratum"], indent=1))
        return 1 if out["stopped"] and not out["stopped"].startswith("BudgetExhausted") else 0
    if a.report:
        for name, (_, measure, base) in runs.items():
            if (a.site in (None, name)) and (RAW / name).exists():
                out = measure(Site(name, base, 0))
                print(name, json.dumps(out["by_stratum"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
