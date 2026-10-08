"""IBM SlamTracker feeds (Wimbledon, the US Open): draws, point histories, match statistics and IBM's extras.

Host-agnostic. A ``Site`` holds everything that differs between tournaments: the source name, the host of each
year, the language segment, the event codes, the per-match feeds, and the files known to be blocked. Wimbledon's
Site is in wimbledon.py; another tournament defines its own Site and calls ``main(site)``.

Feeds, relative to a year's host (<lang> is en_GB at Wimbledon, en_US at the US Open):
    /<lang>/scores/feeds/<year>/draws/<EV>.json                   one event's draw: matches, teams, statsLevel
    /<lang>/scores/feeds/<year>/slamtracker/history/<id>C.json    point history, one row per point (a numeric
                                                                  PointNumber) among marker rows: 0X and 0Y before
                                                                  play, <n>D at a suspension, <n>X and <n>Y after it
    /<lang>/scores/feeds/<year>/matches/complete/<id>.json         match statistics
    /<lang>/scores/feeds/<year>/completed_matches/eventDays.json   days of play, then .../days/day_<n>.json:
                                                                   completed matches by day (the match list where
                                                                   a draw file is blocked)
    extras, as Feed settings of each Site (IBM likelihood-to-win, TennisViz, ...)

Rules (docs/decisions/2026-09-24-official-point-feeds.md, via feeds.FeedClient): about 2 s between requests plus
jitter, a request budget, every answer cached with a receipt and never asked twice; redirects are not followed;
a redirect to the site's /notfound page, or HTTP 404, is a terminal "absent" answer; any other redirect (robots.txt
included), HTTP 403 or 429, a challenge or a connection reset stops the run. Files a Site lists as blocked are
never requested. Five core fetches in a row without a document stop the run (feeds.FailureStreak); an extra feed
that is absent five times in a row within one year and event is abandoned for that group only.

Order: every match not in Sackmann's Slam archive first (newest year first), then the held ones; within a
year and event, the history and statistics of each match, then each extra feed.

Raw layout under data/raw/point_sources/<source>/ (every body gzipped, verbatim):
    <year>/draws/<EV>.json.gz, <year>/days/eventDays.json.gz, <year>/days/day_<n>.json.gz
    <year>/<feed>/<file>.gz for each per-match feed (history/1101C.json.gz, stats/1101.json.gz, ...)
    _receipts.jsonl (receipt names: draws/<year>/<EV>, days/<year>/<file>, <feed>/<year>/<id>)

Staged under data/dump/points/<source>/ (strings, rebuilt from the raw files):
    matches.parquet     one row per listed match: the draw entry flattened, where it was listed, each feed's
                        outcome, history rows and points (rows with a numeric PointNumber)
    points.parquet      every history row verbatim (union of keys over years), with year, event, match_id, row
    statistics.parquet  the statistics file in long form: section, period, team, key, value
    <extra>.parquet     each extra feed: row-shaped documents (a list of objects) keep one row per object;
                        other documents are flattened to path and value
Summary: data/studies/official_point_feeds/<source>_summary.json (and runs.jsonl).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P
from src.ingest.point_sources import feeds as F

SCORES = "/{lang}/scores/feeds/{year}"
SACKMANN_DIR = P.DUMP_ROOT / "sackmann_archive" / "slam_pointbypoint"
PERIOD = re.compile(r"match|set_\d+")


@dataclass(frozen=True)
class Feed:
    """A file fetched once per match. ``path`` is a template with {lang}, {year} and {id}."""
    name: str                                  # receipt prefix and raw folder: "history", "stats", "livel2w", ...
    path: str
    years: frozenset[int] | None = None        # None: every year of the site
    events: frozenset[str] | None = None       # None: every event
    levels: frozenset[str] | None = None       # draw statsLevel values to fetch for; None: every match
    hosts: dict[int, str] | None = None        # per-year host, where it differs from the site's
    core: bool = False                         # history and statistics; the others are extras

    def applies(self, year: int, event: str, level: str | None = None) -> bool:
        return ((self.years is None or year in self.years) and (self.events is None or event in self.events)
                and (self.levels is None or level in self.levels))


@dataclass(frozen=True)
class Site:
    key: str                                   # "wimbledon"
    source: str                                # folder under data/raw/point_sources and data/dump/points
    slam: str                                  # the slam's name in Sackmann's files ("wimbledon", "usopen")
    lang: str                                  # "en_GB"
    hosts: dict[int, str]                      # year -> "https://2025.wimbledon.com"
    events: tuple[str, ...]                    # draw codes, in fetch order
    feeds: tuple[Feed, ...]
    impersonate: str = "chrome"
    blocked: dict[str, str] = field(default_factory=dict)   # receipt name -> reason; never requested
    day_lists: frozenset[int] = frozenset()    # years whose matches are also listed from completed_matches days

    @property
    def years(self) -> list[int]:
        return sorted(self.hosts)

    def host(self, year: int, feed: Feed | None = None) -> str:
        if feed is not None and feed.hosts and year in feed.hosts:
            return feed.hosts[year]
        return self.hosts[year]

    def url(self, year: int, path: str, feed: Feed | None = None, **ids) -> str:
        return self.host(year, feed) + path.format(lang=self.lang, year=year, **ids)

    def feed(self, name: str) -> Feed:
        return next(f for f in self.feeds if f.name == name)


def history_feed(**kw) -> Feed:
    return Feed("history", SCORES + "/slamtracker/history/{id}C.json", core=True, **kw)


def stats_feed(**kw) -> Feed:
    return Feed("stats", SCORES + "/matches/complete/{id}.json", core=True, **kw)


@dataclass
class MatchRef:
    year: int
    event: str
    match_id: str
    level: str | None = None                   # the draw's statsLevel ("H" = full data)
    listed_in: list[str] = field(default_factory=list)   # "draw", "days"
    entry: dict = field(default_factory=dict)  # the listing's match object, flattened


# --------------------------------------------------------------------------------------
# parsing (pure functions; tested offline)
# --------------------------------------------------------------------------------------
def flatten(obj, prefix: str = "") -> dict:
    """Nested objects as dotted keys; lists and scalars are leaves (lists become JSON text when staged)."""
    if not isinstance(obj, dict):
        return {prefix or "value": obj}
    out = {}
    for key, value in obj.items():
        name = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict) and value:
            out.update(flatten(value, name))
        else:
            out[name] = value
    return out


def set_scores(sets) -> str | None:
    """Set scores from a draw's scores.sets, e.g. "7-6(8) 3-1". Both sides carry their tiebreak points; a set
    decided by a tiebreak shows the loser's, as scores are usually written."""
    out = []
    for pair in sets or []:
        if not isinstance(pair, list) or len(pair) != 2:
            continue
        a, b = (x or {} for x in pair)
        text = f"{a.get('scoreDisplay', a.get('score'))}-{b.get('scoreDisplay', b.get('score'))}"
        ga, gb = _games(a), _games(b)
        if ga is not None and gb is not None and abs(ga - gb) == 1 and max(ga, gb) >= 7:
            loser = b if ga > gb else a
            points = loser.get("tiebreakDisplay", loser.get("tiebreak"))
            if points not in (None, ""):
                text += f"({points})"
        out.append(text)
    return " ".join(out) or None


def _games(side: dict) -> int | None:
    value = str(side.get("score", "")).strip()
    return int(value) if value.isdigit() else None


def draw_refs(payload: dict, year: int, event: str) -> list[MatchRef]:
    """One MatchRef per match of a draw file that carries a match id."""
    refs = []
    for match in payload.get("matches") or []:
        match_id = str(match.get("match_id") or "").strip()
        if not match_id:
            continue
        entry = flatten(match)
        entry["score_text"] = set_scores((match.get("scores") or {}).get("sets"))
        refs.append(MatchRef(year, event, match_id, match.get("statsLevel"), ["draw"], entry))
    return refs


def is_point(row: dict) -> bool:
    """A played point: its PointNumber is numeric (the 0X and 0Y rows are pre-match markers)."""
    return str(row.get("PointNumber", "")).isdigit()


def history_rows(payload) -> list[dict]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):  # not seen; kept so an odd file stages instead of failing
        return next((v for v in payload.values() if isinstance(v, list)), [payload])
    return []


def statistics_rows(payload: dict) -> list[dict]:
    """A statistics file in long form: section, period (match, set_N), team, key, value. Other fields of the
    match object (teams, scores, status) and of the file (epoch) come as section "meta" with a dotted key."""
    rows = []
    for key, value in payload.items():
        if key != "matches":
            rows.append({"section": "meta", "period": None, "team": None, "key": f"file.{key}", "value": value})
    for match in payload.get("matches") or []:
        for section, value in match.items():
            if isinstance(value, dict) and value and all(PERIOD.fullmatch(str(p)) for p in value):
                for period, teams in value.items():
                    if not isinstance(teams, dict):
                        rows.append({"section": section, "period": period, "team": None, "key": None, "value": teams})
                        continue
                    for team, stats in teams.items():
                        if isinstance(stats, dict):
                            rows.extend({"section": section, "period": period, "team": team, "key": k, "value": v}
                                        for k, v in stats.items())
                        else:
                            rows.append({"section": section, "period": period, "team": team, "key": None, "value": stats})
            else:
                rows.extend({"section": "meta", "period": None, "team": None, "key": k, "value": v}
                            for k, v in flatten({section: value}).items())
    return rows


def document_rows(payload) -> tuple[str, list[dict]]:
    """An extra feed's document as rows: ("rows", one flattened row per object) when it is a list of objects,
    else ("paths", one {path, value} row per leaf)."""
    if isinstance(payload, list) and payload and all(isinstance(x, dict) for x in payload):
        return "rows", [flatten(x) for x in payload]
    return "paths", [{"path": k, "value": v} for k, v in flatten(payload).items()]


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------
def notfound_redirect(response) -> str | None:
    """A redirect to the site's /notfound page, the IBM sites' answer for a missing file (seen on /clouddata/:
    HTTP 302 to https://2025.wimbledon.com/notfound)."""
    if 300 <= response.status_code < 400:
        location = response.headers.get("location") or ""
        if urlsplit(location).path.rstrip("/").lower().endswith("/notfound"):
            return f"HTTP {response.status_code} redirect to {location}"
    return None


def make_client(site: Site, *, min_interval: float, jitter: float, max_requests: int | None) -> F.FeedClient:
    return F.FeedClient(site.impersonate, not_found=lambda r: notfound_redirect(r) is not None,
                        min_interval=min_interval, jitter=jitter, max_requests=max_requests)


def raw_dest(site: Site, year: int, folder: str, url: str) -> Path:
    return P.raw_path(site.source, str(year), folder, url.rsplit("/", 1)[-1] + ".gz")


def json_body(body: bytes) -> str | None:
    """common.json_validator, with the answer's size and first bytes in the problem, since the body is not kept
    (Wimbledon 2019 LD 4301 and 4305, walkovers: HTTP 200, application/json, not JSON)."""
    problem = P.json_validator(body)
    return f"{problem}: {len(body)} bytes, starting {body[:40]!r}" if problem else None


def fetch_doc(client, receipts, site: Site, *, name: str, url: str, dest: Path, refresh: bool = False,
              extra: dict | None = None) -> dict:
    """One JSON document into the cache; a name the Site lists as blocked is never requested."""
    if name in site.blocked:
        return {"name": name, "url": url, "blocked": site.blocked[name], "skipped": True}
    return P.fetch(client, url, dest, receipts, name=name, refresh=refresh, validator=json_body,
                   compress=True, extra=extra, absent=notfound_redirect)


def fetch_draw(client, receipts, site: Site, year: int, event: str, *, refresh: bool = False) -> dict:
    url = site.url(year, SCORES + f"/draws/{event}.json")
    return fetch_doc(client, receipts, site, name=f"draws/{year}/{event}", url=url,
                     dest=raw_dest(site, year, "draws", url), refresh=refresh, extra={"year": year, "event": event})


def fetch_match_feed(client, receipts, site: Site, feed: Feed, year: int, match_id: str, *, event: str | None = None,
                     refresh: bool = False) -> dict:
    url = site.url(year, feed.path, feed, id=match_id)
    return fetch_doc(client, receipts, site, name=f"{feed.name}/{year}/{match_id}", url=url,
                     dest=raw_dest(site, year, feed.name, url), refresh=refresh,
                     extra={"year": year, "event": event, "match_id": match_id, "feed": feed.name})


def outcome(receipt: dict | None) -> str:
    """One word for a receipt: ok, absent, blocked, error, or 'not requested'."""
    if not receipt:
        return "not requested"
    if receipt.get("blocked"):
        return "blocked"
    if receipt.get("error"):
        return "error"
    if receipt.get("status") == 404 or receipt.get("absent"):
        return "absent"
    return "ok" if receipt.get("status") == 200 else "error"


UNREADABLE: dict[str, tuple[str, str]] = {}  # cached file (receipt dest) -> (receipt name, why it does not parse)


def cached_json(receipt: dict | None):
    """The cached document of a successful receipt, else None. A document that was saved but does not parse
    (the US Open's 2025 prematch_l2w 2701 has a doubled quote; the fetch checks only the first byte) is kept on
    disk, never asked for again, recorded in UNREADABLE and read as None, so staging goes on without it."""
    if outcome(receipt) != "ok":
        return None
    path = P.PROJECT_ROOT / receipt["dest"]
    if not path.exists():
        return None
    try:
        return P.read_json(path)
    except (ValueError, OSError, EOFError) as err:  # JSONDecodeError, UnicodeDecodeError, a damaged gzip
        if receipt["dest"] not in UNREADABLE:
            UNREADABLE[receipt["dest"]] = (receipt["name"], f"{type(err).__name__}: {err}")
            P.log(f"[unreadable] {receipt['name']} ({receipt['dest']}): {type(err).__name__}: {err}")
        return None


def is_unreadable(receipt: dict | None) -> bool:
    return bool(receipt) and receipt.get("dest") in UNREADABLE


# --------------------------------------------------------------------------------------
# match lists
# --------------------------------------------------------------------------------------
def listed_matches(site: Site, receipts, years: list[int], events: list[str]) -> list[MatchRef]:
    """Every match of the selected years and events in the cached draw files (and day lists, where kept)."""
    refs: dict[tuple[int, str], MatchRef] = {}
    for year in years:
        for event in events:
            payload = cached_json(receipts.get(f"draws/{year}/{event}"))
            for ref in draw_refs(payload or {}, year, event):
                refs[(year, ref.match_id)] = ref
        if year in site.day_lists:
            for ref in day_refs(site, receipts, year):
                if ref.event not in events:
                    continue
                known = refs.get((year, ref.match_id))
                if known:
                    known.listed_in.append("days")
                    known.entry["day_file"] = ref.entry["day_file"]
                else:
                    refs[(year, ref.match_id)] = ref
    order = {e: i for i, e in enumerate(site.events)}
    return sorted(refs.values(), key=lambda r: (r.year, order.get(r.event, 99), _id_key(r.match_id)))


def _id_key(match_id: str):
    return (0, int(match_id), "") if match_id.isdigit() else (1, 0, match_id)


def day_refs(site: Site, receipts, year: int) -> list[MatchRef]:
    """Matches listed in the cached completed-match day files of ``year`` (none until they are fetched). A day
    file holds every event played that day (juniors, wheelchair and invitation events too); the caller filters."""
    refs: dict[str, MatchRef] = {}
    names = [n for n in receipts.all() if n.startswith(f"days/{year}/day_")]
    for name in sorted(names, key=lambda n: int(n.rsplit("_", 1)[-1]) if n.rsplit("_", 1)[-1].isdigit() else 0):
        for match in (cached_json(receipts.get(name)) or {}).get("matches") or []:
            match_id, event = str(match.get("match_id") or "").strip(), match.get("eventCode")
            if not match_id or not event:
                continue
            if match_id in refs:  # listed on more than one day
                refs[match_id].entry["day_file"] += ";" + name
                continue
            entry = flatten(match)
            entry["score_text"] = set_scores((match.get("scores") or {}).get("sets"))
            entry["day_file"] = name
            refs[match_id] = MatchRef(year, event, match_id, match.get("statsLevel"), ["days"], entry)
    return list(refs.values())


def held_by_sackmann(slam: str) -> dict[int, set[str]]:
    """Match numbers per year in the dump's copy of Sackmann's Slam archive (singles, doubles, mixed)."""
    import pyarrow.parquet as pq

    held: dict[int, set[str]] = defaultdict(set)
    for path in sorted(SACKMANN_DIR.glob(f"*-{slam}-matches*.parquet")):
        year = int(path.name[:4])
        for value in pq.read_table(path, columns=["match_num"]).column("match_num").to_pylist():
            if value is not None:
                held[year].add(str(value).strip())
    return held


def plan_groups(site: Site, refs: list[MatchRef], held: dict[int, set[str]], order: str) -> list[tuple[bool, int, str, list[MatchRef]]]:
    """(held, year, event, matches) groups in fetch order."""
    groups: dict[tuple[int, str], list[MatchRef]] = defaultdict(list)
    for ref in refs:
        groups[(ref.year, ref.event)].append(ref)
    event_order = {e: i for i, e in enumerate(site.events)}
    out = []
    for (year, event), group in groups.items():
        share = sum(1 for r in group if r.match_id in held.get(year, ())) / len(group)
        out.append((share >= 0.5, year, event, group))
    if order == "new-first":
        out.sort(key=lambda g: (g[0], -g[1], event_order.get(g[2], 99)))
    else:
        out.sort(key=lambda g: (g[1], event_order.get(g[2], 99)))
    return out


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def fetch_listings(client, receipts, site: Site, years: list[int], events: list[str], outcomes: Counter,
                   refresh: bool) -> None:
    for year in years:
        for event in events:
            receipt = fetch_draw(client, receipts, site, year, event, refresh=refresh)
            outcomes[f"draws:{outcome(receipt)}" + (":cached" if receipt.get("skipped") and not receipt.get("blocked") else "")] += 1
        if year in site.day_lists:
            fetch_day_lists(client, receipts, site, year, events, outcomes, refresh)


def fetch_day_lists(client, receipts, site: Site, year: int, events: list[str], outcomes: Counter, refresh: bool) -> None:
    """completed_matches/eventDays.json, then the file of every day on which one of ``events`` was played."""
    url = site.url(year, SCORES + "/completed_matches/eventDays.json")
    receipt = fetch_doc(client, receipts, site, name=f"days/{year}/eventDays", url=url,
                        dest=raw_dest(site, year, "days", url), refresh=refresh, extra={"year": year})
    outcomes[f"days:{outcome(receipt)}" + (":cached" if receipt.get("skipped") else "")] += 1
    for day in event_days(cached_json(receipts.get(f"days/{year}/eventDays")), events):
        url = site.url(year, SCORES + f"/completed_matches/days/day_{day}.json")
        receipt = fetch_doc(client, receipts, site, name=f"days/{year}/day_{day}", url=url,
                            dest=raw_dest(site, year, "days", url), refresh=refresh, extra={"year": year, "day": day})
        outcomes[f"days:{outcome(receipt)}" + (":cached" if receipt.get("skipped") else "")] += 1


def event_days(payload, events=None) -> list[int]:
    """Day numbers of an eventDays document on which one of ``events`` was played. Each entry's tournDay names
    its file (Wimbledon 2026: qualifying Q1-Q4 are days 1-4, the Championships' days 1-14 are 8-21)."""
    days = set()
    for day in (payload or {}).get("eventDays") or []:
        number = str(day.get("tournDay", "")).strip()
        if number.isdigit() and (events is None or set(day.get("events") or []) & set(events)):
            days.add(int(number))
    return sorted(days)


def run(site: Site, args) -> dict:
    P.configure_stdout()
    started = time.time()
    years = _int_list(args.years) or site.years
    unknown = [y for y in years if y not in site.hosts]
    if unknown:
        raise SystemExit(f"{site.key}: no host for years {unknown}")
    events = _str_list(args.events) or list(site.events)
    wanted_feeds = _str_list(args.feeds)
    feeds = [f for f in site.feeds if not wanted_feeds or f.name in wanted_feeds]
    receipts = P.receipts_for(site.source)
    summary = {"source": site.source, "site": site.key, "started_at": P.utc_now_iso(), "args": vars(args),
               "decision": F.DECISION, "hosts": {str(y): site.hosts[y] for y in years}, "events": events,
               "feeds": [f.name for f in feeds]}
    client = None
    if not args.stage_only:
        client = make_client(site, min_interval=args.min_interval, jitter=args.jitter, max_requests=args.max_requests)
    outcomes: Counter = Counter()
    abandoned: list[str] = []
    try:
        if client is not None and not args.skip_listings:
            fetch_listings(client, receipts, site, years, events, outcomes, args.refresh)
        refs = listed_matches(site, receipts, years, events)
        wanted = {tuple(x.split(":", 1)) for x in _str_list(args.matches)}
        if wanted:
            refs = [r for r in refs if (str(r.year), r.match_id) in wanted]
        held = held_by_sackmann(site.slam)
        groups = plan_groups(site, refs, held, args.order)
        if args.limit:
            kept, left = [], args.limit
            for g in groups:
                if left <= 0:
                    break
                kept.append((*g[:3], g[3][:left]))
                left -= len(kept[-1][3])
            groups = kept
        summary["matches_selected"] = sum(len(g[3]) for g in groups)
        summary["plan"] = [f"{y} {e}: {len(g)} matches{' (held)' if h else ''}" for h, y, e, g in groups]
        P.log(f"[{site.source}] {summary['matches_selected']} matches in {len(groups)} groups: " + "; ".join(summary["plan"]))
        if client is not None and not args.listings_only:
            streak = F.FailureStreak(args.streak)
            done = 0
            for is_held, year, event, group in groups:
                core = [f for f in feeds if f.core]
                extras = [f for f in feeds if not f.core]
                for ref in group:
                    for feed in core:
                        if not feed.applies(year, event, ref.level):
                            continue
                        receipt = fetch_match_feed(client, receipts, site, feed, year, ref.match_id, event=event,
                                                   refresh=args.refresh)
                        outcomes[f"{feed.name}:{outcome(receipt)}" + (":cached" if receipt.get("skipped") else "")] += 1
                        streak.note(receipt)
                    done += 1
                    if done % 50 == 0:
                        P.log(f"[{site.source}] {done}/{summary['matches_selected']} matches; requests={client.requests}; "
                              + ", ".join(f"{k}={v}" for k, v in sorted(outcomes.items())))
                for feed in extras:
                    misses = 0
                    for ref in group:
                        if not feed.applies(year, event, ref.level):
                            continue
                        receipt = fetch_match_feed(client, receipts, site, feed, year, ref.match_id, event=event,
                                                   refresh=args.refresh)
                        outcomes[f"{feed.name}:{outcome(receipt)}" + (":cached" if receipt.get("skipped") else "")] += 1
                        if receipt.get("skipped"):
                            continue
                        if outcome(receipt) == "absent":
                            misses += 1
                            if args.streak and misses >= args.streak:
                                abandoned.append(f"{feed.name} {year} {event}: {misses} absent in a row from "
                                                 f"{ref.match_id}; the rest of the group not requested")
                                P.log(f"[{site.source}] abandoned {abandoned[-1]}")
                                break
                        else:
                            misses = 0
                            streak.note(receipt)  # a document resets the run's streak, an error counts toward it
                P.log(f"[{site.source}] done {year} {event}; requests={client.requests}")
    except (P.Blocked, P.BudgetExhausted, F.Stopped) as stop:
        summary["stopped"] = f"{type(stop).__name__}: {stop}"
        P.log(f"[{site.source}] STOPPED: {stop}")
    summary["fetch_outcomes"] = dict(sorted(outcomes.items()))
    summary["abandoned"] = abandoned
    if client is not None:
        summary["client"] = client.stats()
    if not args.no_stage:  # every table holds every year, so a run for one year restages them all
        summary["staged"] = stage(site, receipts, years=_int_list(args.stage_years) or site.years)
    errors = [r for r in receipts.all().values() if r.get("error")]
    summary["receipts_with_errors"] = len(errors)
    summary["error_examples"] = [{"name": r["name"], "error": r["error"]} for r in errors[:20]]
    summary["receipts_by_feed_outcome"] = receipt_counts(receipts)
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - started, 1)
    path = F.write_summary(f"{site.source}_summary.json", summary)
    P.log(f"[{site.source}] summary written to {P.rel(path)}")
    return summary


def receipt_counts(receipts) -> dict:
    """Latest receipts by kind, year and outcome, e.g. "history|2025|ok": 604."""
    counts = Counter()
    for name, receipt in receipts.all().items():
        parts = name.split("/")
        kind, year = parts[0], parts[1] if len(parts) > 1 else ""
        counts[f"{kind}|{year}|{outcome(receipt)}"] += 1
    return dict(sorted(counts.items()))


def _int_list(text) -> list[int]:
    return [int(x) for x in _str_list(text)]


def _str_list(text) -> list[str]:
    return [x.strip() for x in (text or "").split(",") if x.strip()]


# --------------------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------------------
def stage(site: Site, receipts, *, years: list[int]) -> dict:
    """Rebuild the Parquet tables of ``site`` from the cached files of ``years``."""
    refs = listed_matches(site, receipts, years, list(site.events))
    held = held_by_sackmann(site.slam)
    now = P.utc_now_iso()
    source_file = P.rel(P.raw_path(site.source))
    out = {}

    def write(name: str, header: list[str], rows) -> None:
        dest = P.dump_path(site.source, f"{name}.parquet")
        table = ([P.s(r.get(c)) for c in header] for r in rows)
        stats = P.stage_table(site.source, dest, header, table, source_file=source_file, retrieved_at=now,
                              extra={"site": site.key})
        out[name] = {"rows": stats["rows"], "dest": stats["dest"], "bytes": stats["bytes"]}
        P.log(f"[{site.source}] staged {stats['dest']}: {stats['rows']:,} rows")

    def docs(feed_name: str):
        for ref in refs:
            payload = cached_json(receipts.get(f"{feed_name}/{ref.year}/{ref.match_id}"))
            if payload is not None:
                yield ref, payload

    ids = lambda ref: {"year": ref.year, "event": ref.event, "match_id": ref.match_id}

    # points: two passes, so the header is the union of keys over every year, in first-seen order
    keys: dict[str, None] = {}
    counts: dict[tuple[int, str], tuple[int, int]] = {}
    for ref, payload in docs("history"):
        rows = history_rows(payload)
        for row in rows:
            keys.update(dict.fromkeys(row))
        counts[(ref.year, ref.match_id)] = (len(rows), sum(1 for r in rows if is_point(r)))
    point_header = ["year", "event", "match_id", "row"] + list(keys)
    write("points", point_header, ({**row, **ids(ref), "row": n}
                                   for ref, payload in docs("history")
                                   for n, row in enumerate(history_rows(payload), 1)))

    write("statistics", ["year", "event", "match_id", "section", "period", "team", "key", "value"],
          ({**row, **ids(ref)} for ref, payload in docs("stats") for row in statistics_rows(payload)))

    for feed in site.feeds:
        if feed.core:
            continue
        shape, extra_keys = None, {}
        for ref, payload in docs(feed.name):
            kind, rows = document_rows(payload)
            shape = shape or kind
            for row in rows:
                extra_keys.update(dict.fromkeys(row))
        if shape == "rows":
            header = ["year", "event", "match_id", "row"] + list(extra_keys)
            rows = ({**row, **ids(ref), "row": n} for ref, payload in docs(feed.name)
                    for n, row in enumerate(document_rows(payload)[1], 1))
        else:
            header = ["year", "event", "match_id", "path", "value"]
            rows = ({**row, **ids(ref)} for ref, payload in docs(feed.name) for row in document_rows(payload)[1])
        write(feed.name, header, rows)

    entry_keys: dict[str, None] = {}
    for ref in refs:
        entry_keys.update(dict.fromkeys(ref.entry))
    feed_columns = [c for f in site.feeds for c in (f"{f.name}_outcome", f"{f.name}_bytes")]
    header = (["year", "event", "match_id", "listed_in", "stats_level", "held_by_sackmann"] + feed_columns
              + ["history_rows", "history_points"] + [f"entry.{k}" for k in entry_keys])

    def match_rows():
        for ref in refs:
            row = {"year": ref.year, "event": ref.event, "match_id": ref.match_id, "listed_in": "+".join(ref.listed_in),
                   "stats_level": ref.level, "held_by_sackmann": ref.match_id in held.get(ref.year, ())}
            for f in site.feeds:
                receipt = receipts.get(f"{f.name}/{ref.year}/{ref.match_id}")
                applies = f.applies(ref.year, ref.event, ref.level)
                row[f"{f.name}_outcome"] = ("unreadable" if is_unreadable(receipt) else outcome(receipt)
                                            if (receipt or applies) else "not applicable")
                row[f"{f.name}_bytes"] = (receipt or {}).get("bytes")
            row["history_rows"], row["history_points"] = counts.get((ref.year, ref.match_id), (None, None))
            row.update({f"entry.{k}": v for k, v in ref.entry.items()})
            yield row

    write("matches", header, match_rows())
    mine = P.rel(P.raw_path(site.source)) + "/"
    out["unreadable"] = {name: why for dest, (name, why) in sorted(UNREADABLE.items()) if dest.startswith(mine)}
    return out


# --------------------------------------------------------------------------------------
# command line
# --------------------------------------------------------------------------------------
def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--years", help="comma list of years (default: every year of the site)")
    parser.add_argument("--events", help="comma list of draw codes (default: every event of the site)")
    parser.add_argument("--feeds", help="comma list of per-match feeds (default: all: history, stats and the extras)")
    parser.add_argument("--matches", help="comma list of year:match_id to fetch (they must be in a cached listing)")
    parser.add_argument("--limit", type=int, help="fetch only the first N matches of the plan (pilots)")
    parser.add_argument("--order", choices=("new-first", "calendar"), default="new-first",
                        help="new-first: matches missing from Sackmann's archive first, newest year first")
    parser.add_argument("--max-requests", type=int, help="stop after this many HTTP requests")
    parser.add_argument("--min-interval", type=float, default=2.0, help="seconds between requests (plus jitter)")
    parser.add_argument("--jitter", type=float, default=1.0)
    parser.add_argument("--streak", type=int, default=5, help="stop after this many core fetches in a row without a "
                        "document; abandon an extra feed for a year and event after this many absences in a row")
    parser.add_argument("--refresh", action="store_true", help="refetch documents already cached (404s included)")
    parser.add_argument("--listings-only", action="store_true", help="fetch draws and day lists only")
    parser.add_argument("--skip-listings", action="store_true", help="use the draws and day lists already cached")
    parser.add_argument("--stage-only", action="store_true", help="no HTTP; rebuild the Parquet tables and summary")
    parser.add_argument("--stage-years", help="comma list of years to stage (default: every year of the site; each "
                        "table holds all the years staged, so a narrower list shrinks the tables)")
    parser.add_argument("--stage-all", action="store_true", help="(the default now; kept for old command lines)")
    parser.add_argument("--no-stage", action="store_true", help="fetch only; skip the Parquet rebuild")


def main(site: Site, argv=None) -> int:
    parser = argparse.ArgumentParser(description=f"IBM SlamTracker feeds: {site.key}",
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(site, parser.parse_args(argv))
    return 1 if summary.get("stopped") else 0
