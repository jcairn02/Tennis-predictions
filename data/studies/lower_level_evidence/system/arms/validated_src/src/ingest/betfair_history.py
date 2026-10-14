"""Betfair Exchange historical data (register: betfair_history): tennis Match Odds tick files.

Betfair publishes its Exchange stream history at https://historicdata.betfair.com in three plans: BASIC (free;
last traded price at one-minute intervals), ADVANCED (one-second intervals, top three prices each side, traded
volume) and PRO (50 ms, full ladder). Every plan needs a Betfair account, and the data has to be added to the
account in the portal first (BASIC at no charge) for a sport and date range. This adapter then lists and
downloads the account's files through the portal's API and stages them as tick tables. It cannot create an
account, log in, or buy data.

Access: log in at https://historicdata.betfair.com, add Tennis with the plan and dates (e.g. 1 Jan 2025 to
today) and check out; then put the session token (the `ssoid` cookie of the logged-in portal, or a token from
Betfair's login API) in the environment variable BETFAIR_SSOID. The token is sent as a request header and is
never written to disk or to the receipts.

API, as Betfair's own betfairlightweight client calls it: POST https://historicdata.betfair.com/api/<Method> with
a JSON body and the `ssoid` header. GetMyData lists the purchases; DownloadListOfFiles lists the file paths for a
sport, plan, day range, market types, countries and file type ("M", market files); GET
DownloadFile?filePath=<path> returns one bz2 file of newline-delimited Exchange Stream messages (op "mcm"),
each with a publish time `pt` (ms) and, per market, changes to its definition and to its runners' prices.
Status on 5 Oct 2026: written without an account, so the API calls have not been run against the live service;
the stream parser is tested on a synthetic stream in the documented format.

Layout:
    data/raw/betfair_history/<plan>/<file path as listed>      files exactly as downloaded (bz2)
    data/raw/betfair_history/_receipts.jsonl                    one receipt per listing and per file
    data/dump/odds/betfair_history/<plan>/ticks/<YYYY-MM>.parquet     one row per runner price change
    data/dump/odds/betfair_history/<plan>/markets/<YYYY-MM>.parquet   one row per market runner: names,
                                                                scheduled start, settlement status

Usage:
    ./python.sh -m src.ingest.betfair_history --my-data
    ./python.sh -m src.ingest.betfair_history --plan basic --from 2025-01-01 --to 2026-10-05
    ./python.sh -m src.ingest.betfair_history --plan basic --stage-only
"""
from __future__ import annotations

import argparse
import bz2
import datetime as dt
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import requests

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingest.public_dump import common as C

SOURCE = "betfair_history"
API = "https://historicdata.betfair.com/api/"
RAW = C.PROJECT_ROOT / "data" / "raw" / SOURCE
DUMP = C.DUMP_ROOT / "odds" / SOURCE
PLANS = {"basic": "Basic Plan", "advanced": "Advanced Plan", "pro": "Pro Plan"}
TOKEN_ENV = "BETFAIR_SSOID"


# --------------------------------------------------------------------------------------
# portal API
# --------------------------------------------------------------------------------------
def api_session(token: str) -> requests.Session:
    sess = requests.Session()
    sess.headers.update({"ssoid": token, "Content-Type": "application/json", "User-Agent": C.USER_AGENT})
    return sess


def file_list_body(plan: str, start: dt.date, end: dt.date, market_types=("MATCH_ODDS",), sport: str = "Tennis") -> dict:
    return {"sport": sport, "plan": PLANS[plan], "fromDay": start.day, "fromMonth": start.month,
            "fromYear": start.year, "toDay": end.day, "toMonth": end.month, "toYear": end.year,
            "marketTypesCollection": list(market_types), "countriesCollection": [], "fileTypeCollection": ["M"]}


def month_ranges(start: dt.date, end: dt.date):
    """(first day, last day) of each calendar month between start and end, clipped to them."""
    cursor = start
    while cursor <= end:
        nxt = (cursor.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
        yield cursor, min(end, nxt - dt.timedelta(days=1))
        cursor = nxt


def post(sess: requests.Session, method: str, body: dict | None = None):
    response = sess.post(API + method, data=json.dumps(body or {}), timeout=120)
    response.raise_for_status()
    return response.json()


def dest_for(plan: str, file_path: str) -> Path:
    return RAW / plan / file_path.strip("/").replace(":", "_")


def bz2_magic(body: bytes):
    return None if body[:3] == b"BZh" else "not a bz2 file (portal error page or empty body?)"


def download_files(sess: requests.Session, plan: str, start: dt.date, end: dt.date, receipts: C.Receipts) -> dict:
    counts = defaultdict(int)
    for first, last in month_ranges(start, end):
        paths = post(sess, "DownloadListOfFiles", file_list_body(plan, first, last))
        receipts.record({"name": f"list/{plan}/{first}", "url": API + "DownloadListOfFiles",
                         "retrieved_at": C.utc_now_iso(), "body": file_list_body(plan, first, last),
                         "files": len(paths)})
        C.log(f"[{SOURCE}] {plan} {first:%Y-%m}: {len(paths)} files listed")
        for path in paths:
            url = requests.Request("GET", API + "DownloadFile", params={"filePath": path}).prepare().url
            receipt = C.download(url, dest_for(plan, path), receipts, name=f"{plan}:{path}", validator=bz2_magic,
                                 extra={"plan": plan, "file_path": path}, sess=sess)
            counts["skipped" if receipt.get("skipped") else ("error" if receipt.get("error") else "downloaded")] += 1
    return dict(counts)


# --------------------------------------------------------------------------------------
# stream files -> tick tables
# --------------------------------------------------------------------------------------
def _apply_levels(book: dict, updates) -> None:
    """Level-indexed price updates [level, price, size]; size 0 empties the level."""
    for level, price, size in updates or []:
        if size == 0:
            book.pop(level, None)
        else:
            book[level] = (price, size)


def parse_stream(lines) -> tuple[list[dict], list[dict]]:
    """Exchange Stream messages -> (ticks, market runners). A tick is one runner's state after a change: last
    traded price, best back and lay (ADVANCED and PRO), traded volume, with the market's definition at that
    moment (in play or not, status). Runner rows carry the last definition seen: names, scheduled start
    (marketTime) and settlement status (WINNER, LOSER, REMOVED)."""
    definition: dict[str, dict] = {}
    books: dict[tuple, dict] = defaultdict(lambda: {"ltp": None, "tv": None, "batb": {}, "batl": {}})
    ticks = []
    for line in lines:
        if not line.strip():
            continue
        msg = json.loads(line)
        if msg.get("op") != "mcm":
            continue
        pt = msg.get("pt")
        for mc in msg.get("mc") or []:
            market = mc["id"]
            if mc.get("marketDefinition"):
                definition[market] = mc["marketDefinition"]
            d = definition.get(market, {})
            for rc in mc.get("rc") or []:
                book = books[(market, rc["id"])]
                if "ltp" in rc:
                    book["ltp"] = rc["ltp"]
                if "tv" in rc:
                    book["tv"] = rc["tv"]
                _apply_levels(book["batb"], rc.get("batb"))
                _apply_levels(book["batl"], rc.get("batl"))
                back, lay = book["batb"].get(0, (None, None)), book["batl"].get(0, (None, None))
                ticks.append({"market_id": market, "selection_id": rc["id"], "pt": pt, "ltp": book["ltp"],
                              "back1": back[0], "back1_size": back[1], "lay1": lay[0], "lay1_size": lay[1],
                              "tv": book["tv"], "in_play": d.get("inPlay"), "market_status": d.get("status")})
    runners = []
    for market, d in definition.items():
        for r in d.get("runners") or []:
            runners.append({"market_id": market, "selection_id": r.get("id"), "runner_name": r.get("name"),
                            "runner_status": r.get("status"), "sort_priority": r.get("sortPriority"),
                            "event_id": d.get("eventId"), "event_name": d.get("eventName"),
                            "market_type": d.get("marketType"), "market_time": d.get("marketTime"),
                            "open_date": d.get("openDate"), "settled_time": d.get("settledTime"),
                            "country_code": d.get("countryCode"), "market_status": d.get("status")})
    return ticks, runners


def file_month(parts: tuple[str, ...]) -> str:
    """'YYYY-MM' from a listed file path (.../<YYYY>/<Mon>/<day>/<eventId>/<marketId>.bz2), else 'unknown'."""
    for year, month in zip(parts, parts[1:]):
        if year.isdigit() and len(year) == 4:
            try:
                return f"{year}-{dt.datetime.strptime(month, '%b').month:02d}"
            except ValueError:
                continue
    return "unknown"


def stage(plan: str) -> dict:
    """Parse every downloaded file of a plan into monthly tick and runner tables (month of the file's path)."""
    by_month: dict[str, tuple[list, list]] = defaultdict(lambda: ([], []))
    files = sorted((RAW / plan).rglob("*.bz2"))
    for path in files:
        with bz2.open(path, "rt", encoding="utf-8") as handle:
            ticks, runners = parse_stream(handle)
        month = file_month(path.relative_to(RAW / plan).parts)
        source = C.rel(path)
        by_month[month][0].extend(dict(t, _source_file=source) for t in ticks)
        by_month[month][1].extend(dict(r, _source_file=source) for r in runners)
    rows = 0
    for month, (ticks, runners) in by_month.items():
        for kind, table in (("ticks", ticks), ("markets", runners)):
            out = DUMP / plan / kind / f"{month}.parquet"
            out.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(table).to_parquet(out, index=False)
        rows += len(ticks)
    return {"files": len(files), "months": len(by_month), "tick_rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", choices=sorted(PLANS), default="basic")
    ap.add_argument("--from", dest="start", default="2025-01-01")
    ap.add_argument("--to", dest="end", default=dt.date.today().isoformat())
    ap.add_argument("--my-data", action="store_true", help="print what the account holds and stop")
    ap.add_argument("--stage-only", action="store_true", help="rebuild the tick tables from downloaded files")
    args = ap.parse_args()
    if not args.stage_only:
        token = os.environ.get(TOKEN_ENV)
        if not token:
            sys.exit(f"set {TOKEN_ENV} to the session token of a Betfair account holding the data (see the docstring)")
        sess = api_session(token)
        if args.my_data:
            print(json.dumps(post(sess, "GetMyData"), indent=1))
            return 0
        receipts = C.Receipts(SOURCE, root=RAW.parent)
        counts = download_files(sess, args.plan, dt.date.fromisoformat(args.start), dt.date.fromisoformat(args.end),
                                receipts)
        C.log(f"[{SOURCE}] files: {counts}")
    C.log(f"[{SOURCE}] staged: {stage(args.plan)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
