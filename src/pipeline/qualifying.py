"""Tour-level qualifying on bet days (the owner, 22 Oct 2026: docs/decisions/2026-10-22-qualifying-bets.md): a listed
qualifying match's event and round, which the linker needs (live.todays_matches) and Pinnacle's listing does not give
(its league says only "ATP Almaty - Qualifiers").

The event:
    Tennis My Life's rows of the edition when it holds any (the men's qualifying file fills as rounds are played; either
    tour's main draw once begun), found as the linker finds a main-draw event. Else its previous edition in Tennis My
    Life (previous_edition): the same tour, 300-430 days earlier, a name whose tokens equal the listing's (else contain
    them or are contained in them, one edition only). The new edition (built_event) takes that edition's event code
    with this year as its id, and its name, surface, indoor flag, level and draw size, in Tennis My Life's own codes,
    dated the match's day. A round 1 has no row of its edition yet, and women's qualifying never has one: Tennis My
    Life carries none.
The round:
    TennisLive's results section of the event (src/ingest/point_sources/tennislive_events.py: one request lists every
    finished match of the event by round, qualifying included, within minutes of the result; the daily task reads the
    site for every level's results). Paced, a receipt and a raw copy per request, a stop on any refusal. The players'
    finished qualifying matches there decide (round_from_results):
        neither has played: round 1, unless round 1 already looks complete there (as many finished matches as the
            previous edition's round 1 held) or a later round has begun;
        both won round k: round k + 1;
        anything else (a player already out, the match already played, the two disagreeing): left out, with the reason.
    Tennis My Life's rows of the edition must agree. Without TennisLive (a refusal, the event not found there) only both
    players' Tennis My Life wins in one round give the next; a round 1 is never read from Tennis My Life's silence:
    its qualifying file lags the day by hours, so a round 2 whose round 1 it has not published yet would look like one.
Best of: 3; a men's Slam qualifying round takes its previous edition's (Wimbledon's last round was 5 in 2021, 2023, 2025
and 2026).
The main draw's start (main_draw_start), which every qualifying row carries (event_main_date): Stage 0 dates an event by
its main draw's first date (rule C05), and training's qualifying rows have it, while a live qualifying match's main
draw is not played yet. The estimate: the main draw's week (a Slam's: the week after the match's; a tour event's: the
next week for a weekend match, else the match's own), on the weekday the previous edition's Stage 0 date fell on (its
Wednesday or Sunday start), never before the match's day. Checked against training's own dates in
src/eda/master_pipeline/qualifying_dates.py.
"""
from __future__ import annotations

import datetime as dt
import re
import sys

import pandas as pd

from . import config as CFG

if str(CFG.ROOT) not in sys.path:
    sys.path.insert(0, str(CFG.ROOT))
from src.eda.merge_feasibility.scan import name_key, norm  # noqa: E402

EDITION_DAYS = (300, 430)             # a previous edition: about a year before, the calendar's moves allowed
ROUNDS = ("Q1", "Q2", "Q3")
TL_KINDS = ("tour", "slam")           # TennisLive's kinds of the 250s to the Slams
MAX_REQUESTS = 20                     # TennisLive requests per linking: a session, date pages, one section per event
QUALIFYING_ROUND = re.compile(r"^Q\d$")


def _tokens(name) -> frozenset:
    from .live import event_tokens                         # live imports this module: read at call time
    return event_tokens(name)


def is_qualifying_round(rnd) -> bool:
    return bool(QUALIFYING_ROUND.match(str(rnd or "").strip().upper()))


def _mode(values: pd.Series) -> str:
    v = values.dropna().astype(str).str.strip()
    v = v[v.ne("") & v.str.lower().ne("nan")]
    return str(v.value_counts().index[0]) if len(v) else ""


# --- the event -------------------------------------------------------------------------------------------------------------
def previous_edition(tml: pd.DataFrame, tour: str, event: str, day: pd.Timestamp, levels) -> tuple[dict | None, str]:
    """(the event's previous edition, a note) from Tennis My Life's staged rows (live._tml's columns): the same tour,
    EDITION_DAYS before the day, its name's tokens equal to the listing's (else containing them or contained in them),
    exactly one edition. Its surface, indoor flag, level and draw size are its main draw's (its qualifying's when it
    holds no main draw); best_of maps each qualifying round to its value there."""
    want = _tokens(event)
    if not want:
        return None, f"{event!r} has no name to match"
    lo, hi = day - pd.Timedelta(days=EDITION_DAYS[1]), day - pd.Timedelta(days=EDITION_DAYS[0])
    rows = tml[tml["tour"].eq(tour) & tml["_date"].between(lo, hi) & tml["tourney_level"].astype(str).isin(levels)]
    if rows.empty:
        return None, "no Tennis My Life event a year earlier"
    eds = rows.groupby(["_tid", "tourney_name"], as_index=False).agg(first=("_date", "min"))
    eds["tokens"] = eds["tourney_name"].map(_tokens)
    for rule in (lambda t: t == want, lambda t: bool(t) and (t <= want or want <= t)):
        hit = eds[eds["tokens"].map(rule)]
        if hit["_tid"].nunique() > 1:
            return None, f"{event!r} matches several editions a year earlier: {sorted(hit['tourney_name'].unique())}"
        if len(hit):
            tid, name = str(hit["_tid"].iloc[0]), str(hit["tourney_name"].iloc[0])
            ed = rows[rows["_tid"].eq(tid) & rows["tourney_name"].eq(name)]
            qual = ed["round"].astype(str).str.upper().str.fullmatch(r"Q\d")
            base = ed[~qual] if (~qual).any() else ed
            if "-" not in tid:
                return None, f"the previous edition's id {tid!r} has no event code"
            return {"tid": tid, "code": tid.split("-", 1)[1], "name": name, "surface": _mode(base["surface"]),
                    "indoor": _mode(base["indoor"]), "level": _mode(base["tourney_level"]),
                    "draw_size": _mode(base["draw_size"]), "first": hit["first"].iloc[0],
                    "best_of": {r: _mode(ed.loc[qual & ed["round"].astype(str).str.upper().eq(r), "best_of"])
                                for r in ROUNDS}}, "previous edition"
    return None, f"no Tennis My Life event named like {event!r} a year earlier"


def built_event(prev: dict, day: pd.Timestamp) -> dict:
    """A new edition's columns for the matchups CSV (prediction_run/live_rows.CSV_EVENT), from its previous edition.
    Its indoor flag may be blank, as in every women's row of Tennis My Life: the women's indoor input is read from the
    WTA's calendar (src/eda/indoor_fill/status.py), and a men's event without one is blocked by the run's gate."""
    missing = [k for k in ("surface", "level", "draw_size") if not prev.get(k)]
    if missing:
        raise ValueError(f"the previous edition {prev['tid']} lacks {missing}")
    return {"tourney_id": f"{day.year}-{prev['code']}", "tourney_name": prev["name"],
            "event_surface": prev["surface"], "event_draw_size": int(float(prev["draw_size"])),
            "event_level": prev["level"], "event_indoor": prev["indoor"], "event_date": day.strftime("%Y%m%d"),
            "event_from": f"previous edition {prev['tid']} ({prev['first']:%Y-%m-%d})"}


def main_draw_start(day: pd.Timestamp, slam: bool, previous: pd.Timestamp | None = None) -> pd.Timestamp:
    """The estimated start of a qualifying match's main draw (the date Stage 0 gives its event, C05): the main draw's
    week (a Slam's qualifying runs the week before; a tour event's from Friday to Sunday before, or from Monday on in
    the week of a Wednesday or Thursday start), on the weekday of the previous edition's Stage 0 date (``previous``;
    Monday without one: the date of most events), never before the match's own day."""
    day = pd.Timestamp(day).normalize()
    monday = day - pd.Timedelta(days=day.weekday())
    # a Friday to Sunday match: the main draw starts in the days after (the Sunday starts of Doha, Dubai, Brisbane)
    week = monday + pd.Timedelta(days=7) if slam or day.weekday() >= 4 else monday
    if previous is None or pd.isna(previous):
        return max(week, day)
    wd = pd.Timestamp(previous).weekday()
    return max(week + pd.Timedelta(days=wd if wd < 5 else wd - 7), day)


def best_of(tour: str, level: str, rnd: str, prev: dict | None) -> int | None:
    """A men's Slam qualifying round's best-of from its previous edition when it was 5; None otherwise (the event's
    rows or the default 3 stand)."""
    if tour != "atp" or str(level) != "G" or prev is None:
        return None
    v = (prev.get("best_of") or {}).get(str(rnd).upper())
    return 5 if str(v).strip() in ("5", "5.0") else None


# --- the round ---------------------------------------------------------------------------------------------------------------
def player_keys(*names) -> set[str]:
    """The keys a player is matched by: each name's key (accents, case and punctuation removed, words sorted), and the
    surname with the first name's initial (TennisLive and Pinnacle may add or drop a middle name)."""
    keys = set()
    for n in names:
        if not isinstance(n, str) or not n.strip():
            continue
        keys.add(name_key(n))
        parts = norm(n).split()
        if len(parts) >= 2:
            keys.add(f"{parts[-1]} {parts[0][0]}")
    return keys


def _side_keys(rows: pd.DataFrame, side: int) -> pd.Series:
    return rows[f"player{side}_name"].map(lambda n: player_keys(n))


def round_from_results(rows: pd.DataFrame, a: set[str], b: set[str], names: tuple[str, str],
                       round1_size: int | None = None) -> tuple[str | None, str]:
    """(the round, how it was read) of a listed qualifying match from TennisLive's results rows of its event
    (tennislive_events.section_rows); (None, the reason) when the match is to be left out. a, b: each player's keys
    (player_keys)."""
    q = rows[rows["draw"].astype(str).eq("qualifying") & rows["discipline"].astype(str).eq("singles")].copy()
    if q.empty:
        return "Q1", "no qualifying result at the event yet on TennisLive: round 1"
    k1, k2 = _side_keys(q, 1), _side_keys(q, 2)
    done = q["played"].astype(str).str.upper().isin(["TRUE", "1"]) | q["state"].astype(str).isin(["walkover", "awarded"])
    win1 = pd.to_numeric(q["winner_side"], errors="coerce").eq(1)
    win2 = pd.to_numeric(q["winner_side"], errors="coerce").eq(2)
    in_a1, in_a2 = k1.map(lambda k: bool(k & a)), k2.map(lambda k: bool(k & a))
    in_b1, in_b2 = k1.map(lambda k: bool(k & b)), k2.map(lambda k: bool(k & b))
    if (done & ((in_a1 & in_b2) | (in_b1 & in_a2))).any():
        return None, "already played (TennisLive holds the result)"
    order = {r: i for i, r in enumerate(ROUNDS, 1)}
    won = {}
    for keys1, keys2, name in ((in_a1, in_a2, names[0]), (in_b1, in_b2, names[1])):
        lost = done & ((keys1 & win2) | (keys2 & win1))
        if lost.any():
            return None, f"{name} already lost in this qualifying (TennisLive)"
        w = q.loc[done & ((keys1 & win1) | (keys2 & win2)), "round"].astype(str)
        w = [r for r in w if r in order]
        won[name] = max(w, key=order.get) if w else None
    wa, wb = won[names[0]], won[names[1]]
    if wa is None and wb is None:
        later = q.loc[done, "round"].astype(str).isin([r for r in ROUNDS if r != "Q1"]).any()
        played1 = int((done & q["round"].astype(str).eq("Q1")).sum())
        if later:
            return None, "neither player has a qualifying result on TennisLive, but its later rounds have begun"
        if round1_size and played1 >= round1_size:
            return None, (f"neither player has a qualifying result on TennisLive, but its round 1 looks complete "
                          f"({played1} of {round1_size} matches): a name spelled differently?")
        return "Q1", "neither player has a qualifying result on TennisLive: round 1"
    if wa is not None and wa == wb:
        nxt = order[wa] + 1
        if nxt > len(ROUNDS):
            return None, f"both players have won {wa}: no qualifying round after it"
        return ROUNDS[nxt - 1], f"both players won {wa} on TennisLive"
    return None, (f"the players' qualifying results disagree on TennisLive ({names[0]}: {wa or 'none'}, {names[1]}: "
                  f"{wb or 'none'})")


def round_from_tml(event_rows: pd.DataFrame, a: str, b: str) -> tuple[str | None, str]:
    """The round from Tennis My Life's rows of the edition alone: both players won round k there, so round k + 1. Never
    round 1 (Tennis My Life's qualifying file lags the day), and None when the rows say nothing for sure."""
    q = event_rows[event_rows["round"].astype(str).str.upper().str.fullmatch(r"Q\d")]
    ka, kb = name_key(a), name_key(b)
    order = {r: i for i, r in enumerate(ROUNDS, 1)}
    won = {}
    for k, n in ((ka, a), (kb, b)):
        if (q["_lk"] == k).any():
            return None, f"{n} already lost in this qualifying (Tennis My Life)"
        w = [r for r in q.loc[q["_wk"] == k, "round"].astype(str).str.upper() if r in order]
        won[n] = max(w, key=order.get) if w else None
    if won[a] is not None and won[a] == won[b] and order[won[a]] < len(ROUNDS):
        return ROUNDS[order[won[a]]], f"both players won {won[a]} (Tennis My Life)"
    return None, ("round unknown: TennisLive did not answer, and Tennis My Life's rows do not give it "
                  f"({a}: {won[a] or 'no win'}, {b}: {won[b] or 'no win'})")


def tml_agrees(event_rows: pd.DataFrame, a: str, b: str, rnd: str) -> str | None:
    """A reason the round read from TennisLive disagrees with Tennis My Life's rows of the edition: a player there won a
    later or the same round, or lost; None when they agree (a lagging file only lacks rounds)."""
    q = event_rows[event_rows["round"].astype(str).str.upper().str.fullmatch(r"Q\d")]
    order = {r: i for i, r in enumerate(ROUNDS, 1)}
    for k, n in ((name_key(a), a), (name_key(b), b)):
        if (q["_lk"] == k).any():
            return f"Tennis My Life has {n} out of this qualifying already"
        w = [order[r] for r in q.loc[q["_wk"] == k, "round"].astype(str).str.upper() if r in order]
        if w and max(w) >= order[rnd]:
            return f"Tennis My Life has {n} past {rnd} already"
    return None


class TennisLive:
    """One linking's TennisLive reads (tennislive_events' own client, session, pages and parser): the date pages of
    the match days (and the Monday after: the event's own week), then each event's results section once."""

    def __init__(self, max_requests: int = MAX_REQUESTS):
        from src.ingest.point_sources import common as PS
        from src.ingest.point_sources import tennislive as TL
        from src.ingest.point_sources import tennislive_events as TLE
        self.PS, self.TLE = PS, TLE
        self.client = PS.Client(TL.IMPERSONATE, min_interval=1.5, jitter=1.0, max_requests=max_requests)
        self.receipts = PS.receipts_for(TLE.SOURCE)
        self.session = TLE.Session(self.client, self.receipts)
        self.events: dict[str, dict] = {}
        self.days: set = set()
        self.sections: dict[str, pd.DataFrame] = {}
        self.stopped: str | None = None
        self.requests = 0

    def _guard(self, fn, *args):
        if self.stopped:
            return None
        try:
            return fn(*args)
        except (self.PS.Blocked, self.PS.BudgetExhausted) as stop:     # a refusal stops TennisLive for this linking
            self.stopped = f"{type(stop).__name__}: {stop}"
        except Exception as exc:  # noqa: BLE001 - the linker falls back to Tennis My Life, and says why
            self.stopped = f"{type(exc).__name__}: {exc}"
        return None

    def _day(self, day: dt.date) -> None:
        """A date page: asked again when it is today's or later (a held copy may predate the day's order of play)."""
        if day in self.days or self.stopped:
            return
        self.days.add(day)
        fresh = day >= dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1)
        self._guard(self.TLE.fetch_day, self.client, self.receipts, self.session, day, fresh)
        dest = self.PS.raw_path(self.TLE.SOURCE, "calendar", f"{day.isoformat()}.html.gz")
        if dest.exists():
            cal = self.TLE.parse_calendar(self.PS.read_bytes(dest).decode("utf-8", errors="replace"))
            monday = day - dt.timedelta(days=day.weekday())
            for key, ev in self.TLE.collect_events([(monday, cal)]).items():
                self.events.setdefault(key, ev)

    def event(self, tour: str, name: str, day: dt.date) -> tuple[dict | None, str]:
        """TennisLive's event of a listed qualifying match: one of the tour's 250s to Slams of the match's day page,
        else of the next Monday's (the event's own week), named like the listing."""
        want = _tokens(name)
        for d in (day, day + dt.timedelta(days=(7 - day.weekday()) % 7 or 7)):
            self._day(d)
            cands = [e for e in self.events.values() if e.get("tour") == tour and e.get("kind") in TL_KINDS
                     and e.get("url")]
            for rule in (lambda t: t == want, lambda t: bool(t) and (t <= want or want <= t)):
                hit = {e["key"]: e for e in cands if rule(_tokens(e.get("name")))}
                if len(hit) == 1:
                    return next(iter(hit.values())), ""
                if len(hit) > 1:
                    return None, f"TennisLive names several events like {name!r}: {sorted(e['name'] for e in hit.values())}"
        return None, (f"TennisLive lists no {tour.upper()} event like {name!r}" +
                      (f" ({self.stopped})" if self.stopped else ""))

    def results(self, ev: dict) -> pd.DataFrame | None:
        """The event's results rows (tennislive_events.section_rows), its section asked afresh once per linking (an
        event under way lists only its finished matches, so a held answer would read as final)."""
        if ev["key"] in self.sections:
            return self.sections[ev["key"]]
        r = self._guard(self.TLE.fetch_section, self.client, self.receipts, self.session, ev, True)
        target = self.TLE.section_target(ev["url"])
        if r is None or target is None or r.get("status") not in (200, None) or not target[1].exists():
            return None
        if r.get("error"):
            self.stopped = self.stopped or f"results section: {r['error']}"
            return None
        rows = pd.DataFrame(self.TLE.section_rows(self.PS.read_json(target[1]), ev,
                                                  {"retrieved_at": r.get("retrieved_at")}))
        self.sections[ev["key"]] = rows
        return rows
