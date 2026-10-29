"""The daily ATP serve-speed collector (path a: the current season's ATP Stats Centre files, decrypted).

Decision: docs/decisions/2026-10-08-scraping-approved.md, "Clarified by the owner later on 8 October 2026": "The daily
collector we NEED to decrypt them. The do not decrypt only applie to the 2015-2021 session". So:
    * this collector decrypts its OWN current-season files (2026 onward), stored under
      data/raw/point_sources/infosys_atp_daily/<year>/<event>/<route>/<MID>.json.gz;
    * it REFUSES to decrypt anything from 2015-2021, and anything under data/raw/point_sources/infosys_atp/ (the
      encrypted backfill of session tennis-predictions-74), whatever the year (guard(); tested).
Decryption reuses src/ingest/point_sources/infosys_slams.py's key_iv / decrypt by import (the same Infosys scheme as the
AO and RG files: an AES-128-CBC envelope keyed by its lastModified).

THE FETCH IS OFF. fetch_daily() sends no request unless (1) live/collector.json has "atp_daily_enabled": true, which
the lead sets once the other session's backfill has finished, and (2) the backfill adapter
src/ingest/point_sources/infosys_atp.py is on disk (its headers and client factory are imported if it exposes them,
never edited; it is not on disk in this workspace on 8 Oct 2026), or collector.json says
"require_backfill_adapter": false, in which case the official feeds' shared client is used. Daily mode: the current season, the /prod/api/ routes (static files answer 403 for
current-season keystats: 2026/747/MS001, per the other session), only the codes of rounds played since the last run.
The first live run is to be small: yesterday's matches only (max_requests small).

Run (offline parts): see src/ingest/speed_daily.py. Reads no match result.
"""
from __future__ import annotations

import gzip
import importlib
import json
from pathlib import Path

import pandas as pd

from src.eda.serve_speed_tabpfn.live import common as LC
from src.eda.serve_speed_tabpfn.live import staging as ST

HOST = "https://itp-atp-sls.infosys-platforms.com"
ROUTES = {"keystats-api": "/prod/api/stats-plus/v1/keystats/year/{year}/eventId/{event}/matchId/{mid}"}
RAW_DIR = LC.ROOT / "data" / "raw" / "point_sources" / "infosys_atp_daily"
BACKFILL_DIR = LC.ROOT / "data" / "raw" / "point_sources" / "infosys_atp"
FIRST_YEAR = 2026                      # the daily collector's own files: the current season onward
REFUSED_YEARS = range(2015, 2022)      # the encrypted backfill: never decrypted
SOURCE = "infosys_atp_daily"
MAX_REQUESTS_FIRST_RUN = 60
ROUND_CODES = {"F": (1, 1), "SF": (2, 3), "QF": (4, 7), "R16": (8, 15), "R32": (16, 31), "R64": (32, 63),
               "R128": (64, 127)}
QUAL = "Q"                             # the plan's group of an event's qualifying codes (daily_plan)


class RefusedDecryption(RuntimeError):
    """Raised before any decryption of a backfill file or of a year outside the current-season collector's scope."""


class NotEnabled(RuntimeError):
    """The daily fetch is off (collector.json) or its adapter is missing; no request was sent."""


def guard(year, path: Path | str | None = None) -> None:
    """Refuse a file of 2015-2021, of any year before the current-season collector's first (2026), or any file under
    the backfill folder data/raw/point_sources/infosys_atp/ (even of an allowed year)."""
    if path is not None:
        p = Path(path).resolve()
        b = BACKFILL_DIR.resolve()
        if p == b or b in p.parents:
            raise RefusedDecryption(f"{p} is in the encrypted 2015-2021 backfill folder: not decrypted (owner, 8 Oct)")
    try:
        y = int(year)
    except (TypeError, ValueError):
        raise RefusedDecryption(f"year {year!r} unknown: not decrypted")
    if y in REFUSED_YEARS:
        raise RefusedDecryption(f"{y} is a backfill year (2015-2021): not decrypted (owner, 8 Oct)")
    if y < FIRST_YEAR:
        raise RefusedDecryption(f"{y} is before the daily collector's first season ({FIRST_YEAR}): not decrypted")


def decrypt_envelope(envelope: dict, *, year, path: Path | str | None = None):
    """The plain JSON of one current-season envelope, after the guard (infosys_slams.decrypt does the AES step)."""
    guard(year, path)
    from src.ingest.point_sources import infosys_slams as I
    return I.decrypt(envelope)


def raw_path(year: int, event, mid: str, route: str = "keystats-api") -> Path:
    return RAW_DIR / str(int(year)) / str(event) / route / f"{mid}.json.gz"


def parse_path(path: Path) -> dict:
    """year, event, route and match code from a raw file's path (RAW_DIR/<year>/<event>/<route>/<MID>.json.gz)."""
    p = Path(path)
    return {"year": int(p.parents[2].name), "event": p.parents[1].name, "route": p.parent.name,
            "mid": p.name.split(".")[0].upper()}


def decrypt_and_stage(paths, collected_on: str, rounds: dict | None = None) -> pd.DataFrame:
    """Staging rows from the collector's raw keystats files: guard, decrypt, parse. rounds: {(event, mid): round} from
    the plan, else the code's bracket round."""
    rows = []
    for path in paths:
        meta = parse_path(path)
        guard(meta["year"], path)                                  # before the file is even read
        with gzip.open(path, "rt", encoding="utf-8") as f:
            env = json.load(f)
        doc = decrypt_envelope(env, year=meta["year"], path=path)
        ks = doc.get("stats", doc) if isinstance(doc, dict) else {}
        rnd = (rounds or {}).get((meta["event"], meta["mid"]))
        r = ST.parse_keystats(ks, year=meta["year"], event_id=meta["event"], match_code=meta["mid"], rnd=rnd,
                              retrieved_at=pd.Timestamp(Path(path).stat().st_mtime, unit="s", tz="UTC").isoformat(),
                              collected_on=collected_on, source=SOURCE, source_file=str(path))
        if r is not None:
            rows.append(r)
    return ST.to_frame(rows)


def enabled(cfg: Path = LC.COLLECTOR_CFG) -> bool:
    return bool(LC.read_json(cfg, {}).get("atp_daily_enabled", False))


def group_of(rnd) -> str | None:
    """The plan's group of a Tennis My Life round: the main-draw round itself, QUAL for every qualifying round (their
    QS numbers overlap, so an event's qualifying is one group), None for a round without codes."""
    if rnd in ROUND_CODES:
        return rnd
    return QUAL if str(rnd).startswith("Q") and rnd != "QF" else None


def plan_order(entry: tuple) -> tuple:
    """Every main-draw code before any qualifying code, then year, event and code: the run's budget reaches each event's
    main draw (24 Oct 2026: no run had asked for Almaty's last 16 and quarter-finals since 22 Oct, the 200 requests
    going first to Lyon's and Brussels's qualifying numbers, which sort before Almaty's event id)."""
    year, event, code, _ = entry
    return (str(code).startswith("QS"), year, event, code)


def daily_plan(year: int, events: pd.DataFrame, held: set | None = None, staged: set | None = None,
               listed: dict | None = None) -> list[tuple[int, str, str, str]]:
    """(year, event, match code, round) to ask, each code once: for each event with matches played since the last run
    (events: columns event_id, round), the codes of those rounds (main draw by the bracket numbering); an event's
    qualifying rounds share every QS code up to the qualifying draw (their numbers overlap), asked once under the
    latest of them. Codes already held complete are skipped (held: (year, event, code)). A group, a main-draw round or
    an event's whole qualifying, whose staged codes (staged, complete or not) already number the matches Tennis My Life
    lists for it (listed: {(year, event, group): matches}) asks only its staged codes not yet complete: the others are
    byes or numbers no match carries (24 Oct 2026: 181 of a run's 200 requests answered "no such match", each
    qualifying number asked once per qualifying round). Main draws first (plan_order)."""
    held, staged, listed = held or set(), staged or set(), listed or {}
    groups: dict = {}
    for (event, rnd), _ in events.groupby(["event_id", "round"]):
        grp = group_of(rnd)
        if grp is None:
            continue
        if grp == QUAL:
            codes = [f"QS{n:03d}" for n in range(1, 64)]
        else:
            lo, hi = ROUND_CODES[rnd]
            codes = [f"MS{n:03d}" for n in range(lo, hi + 1)]
        g = groups.setdefault((str(event), grp), {"codes": codes, "round": rnd})
        g["round"] = max(g["round"], rnd)            # Q1 < Q2 < Q3: the latest qualifying round names the codes
    plan = []
    for (event, grp), g in groups.items():
        ask = [c for c in g["codes"] if (int(year), event, c) not in held]
        mine = {c for c in g["codes"] if (int(year), event, c) in staged}
        n = listed.get((int(year), event, grp))
        if n is not None and len(mine) >= n:
            ask = [c for c in ask if c in mine]
        plan += [(int(year), event, c, g["round"]) for c in ask]
    return sorted(plan, key=plan_order)


def tml_played(day_from: int, day_to: int) -> pd.DataFrame:
    """Tennis My Life's ATP tour-level and Challenger matches of the seasons of day_from..day_to played by day_to, with
    their day (d_day), year and event_id (identity columns only; its Slams and team events are not the ATP Stats
    Centre's)."""
    from src.eda.serve_speed_tabpfn.live import link as LK
    years = sorted({int(LC.date_of(day_from)[:4]), int(LC.date_of(day_to)[:4])})
    t = LK.tml_table(years)
    if t.empty:
        return pd.DataFrame(columns=["year", "event_id", "round", "d_day"])
    d = t["d"].map(lambda x: LC.day_of(x) if pd.notna(x) else -1)
    t = t.assign(d_day=d)[(d >= 0) & (d <= day_to) & t["per_match_dates"] & ~t["level"].isin(["GS", "TEAM"])
                          & t["tid"].str.fullmatch(r"\d{4}-\d+")]
    return t.assign(year=t["tid"].str[:4].astype(int), event_id=t["tid"].str.split("-").str[1])


def played_rounds(day_from: int, day_to: int, played: pd.DataFrame | None = None) -> pd.DataFrame:
    """(year, event_id, round, matches) of ATP tour-level and Challenger matches that Tennis My Life lists as played on
    days day_from..day_to (identity columns only; its Slams and team events are not the ATP Stats Centre's)."""
    t = tml_played(day_from, day_to) if played is None else played
    t = t[t["d_day"] >= day_from]
    return t.groupby(["year", "event_id", "round"]).size().rename("matches").reset_index()


def listed_matches(played: pd.DataFrame) -> dict:
    """{(year, event, group): matches} Tennis My Life lists as played by the window's last day, from any earlier day
    (tml_played's rows): what a group's staged codes are counted against (daily_plan)."""
    grp = played["round"].map(group_of)
    t = played.assign(grp=grp)[grp.notna()]
    return {(int(y), str(e), g): int(n) for (y, e, g), n in t.groupby(["year", "event_id", "grp"]).size().items()}


def held_codes() -> tuple[set, set]:
    """(year, event, match code) of this collector's own staged matches: those staged complete, and all of them. The
    year since 24 Oct 2026: an event's codes recur every season."""
    st = ST.read_all()
    if st.empty:
        return set(), set()
    st = st[st["source"].eq(SOURCE)]

    def keys(d: pd.DataFrame) -> set:
        return set(zip(d["year"].astype(int), d["event_id"].astype(str), d["match_code"].astype(str)))
    return keys(st[st["match_completed"].astype("boolean").fillna(False)]), keys(st)


def held_complete() -> set:
    """(year, event, match code) already staged as complete matches from this collector's own files."""
    return held_codes()[0]


def plan_days(day_from: int, day_to: int) -> list[tuple[int, str, str, str]]:
    """The requests a run would make for matches played day_from..day_to (daily_plan): each played round's codes once,
    minus the matches already held complete; a group already staged in full asks only its codes not yet complete; main
    draws first. The first live test: day_from = day_to = yesterday."""
    played = tml_played(day_from, day_to)
    pr, listed = played_rounds(day_from, day_to, played), listed_matches(played)
    held, staged = held_codes()
    plan = []
    for year, g in pr.groupby("year"):
        plan += daily_plan(int(year), g, held, staged, listed)
    return sorted(plan, key=plan_order)


def _adapter():
    """The backfill session's adapter (client and plan), imported, never edited."""
    try:
        return importlib.import_module("src.ingest.point_sources.infosys_atp")
    except ImportError as e:
        raise NotEnabled("src/ingest/point_sources/infosys_atp.py is not on disk: its client is needed") from e


def site_headers() -> dict:
    """What atptour.com's own page sends to the Infosys host (a cross-origin fetch), as for the AO and RG files."""
    site = "https://www.atptour.com"
    return {"Origin": site, "Referer": site + "/", "Accept": "application/json, text/plain, */*"}


def fetch_daily(day: str, plan: list, max_requests: int = MAX_REQUESTS_FIRST_RUN, cfg: Path = LC.COLLECTOR_CFG) -> dict:
    """Fetch the plan's current-season keystats envelopes into RAW_DIR, with the project's standard path: the official
    feeds' client (stops on any block; about 2 s plus jitter between requests), point_sources.common.fetch (a receipt
    per request, nothing fetched twice, absent answers kept) and the Infosys envelope validator. The backfill adapter's
    own headers and client factory are preferred when it exposes them. Refuses (NotEnabled) unless the lead has
    enabled the collector and the adapter is on disk; never asks for a season before FIRST_YEAR."""
    if not enabled(cfg):
        raise NotEnabled("the ATP daily collector is off (live/collector.json); no request sent")
    try:
        A = _adapter()
    except NotEnabled:
        if LC.read_json(cfg, {}).get("require_backfill_adapter", True):
            raise
        import types
        A = types.SimpleNamespace()        # the lead allowed the shared feed client without the backfill adapter
    from src.ingest.point_sources import common as P
    from src.ingest.point_sources import feeds as FD
    from src.ingest.point_sources import infosys_slams as I
    # The backfill adapter's make_client(args, cal) needs its own argparse namespace and S3 calibration, so the client
    # is built here with the same impersonation, headers and pacing (2 s plus up to 1 s of jitter) instead.
    headers = dict(getattr(A, "HEADERS", None) or site_headers())
    client = FD.FeedClient(getattr(A, "IMPERSONATE", "chrome"), min_interval=2.0, jitter=1.0,
                           max_requests=max_requests, timeout=60)
    receipts = P.receipts_for(SOURCE)
    got, budget_hit = [], False
    for year, event, mid, rnd in plan:
        guard(year)
        dest = raw_path(year, event, mid)
        url = HOST + ROUTES["keystats-api"].format(year=year, event=event, mid=mid)
        # refresh: a code answered "absent" earlier (its match not yet played) is asked again when its round is played
        try:
            rec = P.fetch(client, url, dest, receipts, name=f"{year}/{event}/keystats-api/{mid}", refresh=True,
                          validator=I.envelope_validator, compress=True, headers=headers,
                          extra={"year": year, "event": event, "match_id": mid, "round": rnd})
        except P.BudgetExhausted:
            # the run's request budget is spent: stop asking and keep what was fetched (a block still raises)
            budget_hit = True
            break
        if rec.get("status") == 200 and not rec.get("error"):
            got.append(dest)
    return {"day": day, "planned": len(plan), "files": [str(p) for p in got], "budget_exhausted": budget_hit,
            "client": client.stats() if hasattr(client, "stats") else None}
