"""OddsTrader (register: oddstrader): BetOnline and SportsBetting.ag tennis opening and last lines.

oddstrader.com is an odds-comparison site. Its pages load their prices from the site's own GraphQL odds service,
which answers plain GET requests without a login. This adapter lists every ATP and WTA event month by month, then
reads, for the singles matches, the opening line and the current line of the chosen books in two markets. For a
finished match the current line is the last line the site recorded.

Decision and limits: docs/decisions/2026-10-06-oddstrader-betonline-lines.md. The owner chose to pull without the
written permission that OddsTrader's terms say automated access "may require": about 2 s between requests, a
request budget, a stop on any block, no login, nothing republished. Research: docs/research/betonline-lines/.

Service (undocumented; read from the site's own scripts on 6 Oct 2026):
    GET https://ms.virginia.us-east-1.oddstrader.com/odds-v2/odds-v2-service?query=<GraphQL>
    eventsByDateNew(lid, startDate ms, hoursRange, mtid, showEmptyEvents)  events listed in a window
    openingLines(paid, eid, mtid, marketTypeLayout: "PARTICIPANTS")       first line the site recorded per book
    currentLines(paid, eid, mtid)                                          latest line per book
    lineHistory(eid, mtid, paid, partid) has every line, but one side per request and no aliases; unused here.
Leagues 23 ATP, 24 WTA. Books (paid) 8 BetOnline, 131 SportsBetting.ag. Markets (mtid) 126 match winner,
396 total games. A line has ap (American price), pri (decimal price), adj (total-games line; 0 for the match
winner), tim (ms UTC), iof (the line is off the board; the site's isLiveLineOff) and partid: the player's side, or
15143 Over and 15144 Under (the site's own constants).

Layout:
    data/raw/oddstrader/events/<lid>/<YYYY-MM>.json        one eventsByDateNew response per tour and month
    data/raw/oddstrader/lines/<lid>/<YYYY-MM>/<nn>.json    one line response per batch of up to 100 singles
    data/raw/oddstrader/_receipts.jsonl                    one receipt per request, with the query sent
    data/dump/odds/oddstrader/events.parquet               one row per listed event (singles and doubles)
    data/dump/odds/oddstrader/lines.parquet                one row per line: kind (open/last), book, market, side
    data/dump/odds/oddstrader/betonline_matches.parquet    one row per singles event: BetOnline's opening and
                                                           closing prices in both markets, with flags (matches_table)

A month is listed whole, so the current month's listing and lines are a snapshot: matches still to be played
carry a provisional last line (status `es` other than "complete"). Nothing is fetched twice; --refresh-month
fetches one month again.

Usage:
    ./python.sh -m src.ingest.oddstrader --from 2024-01 --to 2026-10
    ./python.sh -m src.ingest.oddstrader --stage-only
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import sys
import time
from pathlib import Path

import pandas as pd
import requests

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingest.public_dump import common as C

SOURCE = "oddstrader"
SERVICE = "https://ms.virginia.us-east-1.oddstrader.com/odds-v2/odds-v2-service"
RAW = C.PROJECT_ROOT / "data" / "raw" / SOURCE
DUMP = C.DUMP_ROOT / "odds" / SOURCE
USER_AGENT = "tennis-predictions/1.0 (research use; python-requests)"
LEAGUES = {23: "ATP", 24: "WTA"}
BOOKS = {8: "BetOnline", 131: "SportsBetting.ag"}
MARKETS = {126: "match_winner", 396: "total_games"}
TOTAL_SIDES = {15143: "over", 15144: "under"}
BATCH = 100
PAUSE = 2.0  # seconds between requests, plus up to one second of jitter

EVENT_FIELDS = (
    "eid es dt lid spid tvs ic des seid sta cit ven st cou "
    "eventGroup { egid nam parentid parentname } "
    "participants { eid partid tr rot ih source { ... on Player { pid fn lnam } ... on Team { tmid nam } } }"
)
LINE_FIELDS = ("mtid", "eid", "boid", "paid", "partid", "adj", "ap", "pri", "dp", "bs", "iof", "fpd", "fpn",
               "lineid", "sequence", "entrid", "mtgrp", "tmid")


class Stop(RuntimeError):
    """A response the decision says must end the run: a block, a non-JSON body or a GraphQL error."""


# --------------------------------------------------------------------------------------
# queries
# --------------------------------------------------------------------------------------
def month_starts(first: str, last: str):
    """(year, month) for every month from 'YYYY-MM' to 'YYYY-MM', inclusive."""
    year, month = map(int, first.split("-"))
    end = tuple(map(int, last.split("-")))
    while (year, month) <= end:
        yield year, month
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def month_window(year: int, month: int) -> tuple[int, int]:
    """(start in ms UTC, length in hours) of a calendar month."""
    start = dt.datetime(year, month, 1, tzinfo=dt.timezone.utc)
    end = dt.datetime(year + (month == 12), month % 12 + 1, 1, tzinfo=dt.timezone.utc)
    return int(start.timestamp() * 1000), int((end - start).total_seconds() // 3600)


def events_query(lid: int, start_ms: int, hours: int) -> str:
    return (f"{{ eventsByDateNew(lid: [{lid}], startDate: {start_ms}, hoursRange: {hours}, mtid: [126], "
            f"showEmptyEvents: true) {{ events {{ {EVENT_FIELDS} }} }} }}")


def lines_query(eids, books=BOOKS, markets=MARKETS) -> str:
    """Current lines of every book, and opening lines book by book, in one request (aliases work here)."""
    e, p, m = (",".join(str(x) for x in values) for values in (eids, books, markets))
    parts = [f"cur: currentLines(paid: [{p}], eid: [{e}], mtid: [{m}])"]
    parts += [f'o{b}: openingLines(paid: [{b}], eid: [{e}], mtid: [{m}], marketTypeLayout: "PARTICIPANTS")'
              for b in books]
    return "{ " + " ".join(parts) + " }"


def is_singles(event: dict) -> bool:
    return "singles" in ((event.get("eventGroup") or {}).get("nam") or "").lower()


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------
class Client:
    """Paced GET of the service with receipts; reuses any earlier good response; raises Stop on a block."""

    def __init__(self, receipts: C.Receipts, max_requests: int):
        self.sess = requests.Session()
        self.sess.headers["User-Agent"] = USER_AGENT
        self.receipts = receipts
        self.left = max_requests
        self.sent = 0
        self._last = 0.0

    def fetch(self, name: str, query: str, dest: Path, extra: dict | None = None, refresh: bool = False):
        previous = self.receipts.get(name)
        if dest.exists() and previous and not previous.get("error") and not refresh:
            return json.loads(dest.read_text(encoding="utf-8"))
        if self.left <= 0:
            return None
        wait = self._last + PAUSE + random.random() - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self.left -= 1
        self.sent += 1
        receipt = {"name": name, "url": SERVICE, "query": query, "dest": C.rel(dest),
                   "retrieved_at": C.utc_now_iso(), **(extra or {})}
        try:
            response = self.sess.get(SERVICE, params={"query": query}, timeout=90, allow_redirects=False)
        except requests.RequestException as err:
            self.receipts.record({**receipt, "error": f"{type(err).__name__}: {err}"})
            raise Stop(f"{name}: {type(err).__name__}: {err}") from err
        finally:
            self._last = time.monotonic()
        body = response.content
        receipt.update(status=response.status_code, content_type=response.headers.get("Content-Type"),
                       bytes=len(body))
        problem = None
        if response.status_code != 200:
            problem = f"HTTP {response.status_code}"
        else:
            try:
                doc = json.loads(body)
            except ValueError:
                problem = "body is not JSON (a challenge page?)"
            else:
                data = doc.get("data")
                if doc.get("errors") or not isinstance(data, dict) or any(v is None for v in data.values()):
                    problem = "GraphQL error: " + json.dumps(doc.get("errors"))[:400]
        if problem:
            self.receipts.record({**receipt, "error": problem})
            raise Stop(f"{name}: {problem}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        C.write_atomic(dest, body)
        self.receipts.record({**receipt, "sha256": C.sha256_bytes(body)})
        return doc


def download(first: str, last: str, leagues, client: Client, refresh_month: str | None = None) -> dict:
    """List every month, then fetch the lines of its singles in batches. Returns counts; raises Stop."""
    batches = []
    for lid in leagues:
        for year, month in month_starts(first, last):
            tag = f"{year}-{month:02d}"
            start_ms, hours = month_window(year, month)
            doc = client.fetch(f"events/{lid}/{tag}", events_query(lid, start_ms, hours),
                               RAW / "events" / str(lid) / f"{tag}.json", {"lid": lid, "month": tag},
                               refresh=(tag == refresh_month))
            if doc is None:
                C.log(f"[{SOURCE}] request budget spent while listing {lid} {tag}")
                return {"requests": client.sent, "stopped": "budget"}
            events = doc["data"]["eventsByDateNew"]["events"]
            singles = sorted({e["eid"] for e in events if is_singles(e)})
            C.log(f"[{SOURCE}] {LEAGUES[lid]} {tag}: {len(events)} events, {len(singles)} singles")
            for k in range(0, len(singles), BATCH):
                batches.append((lid, tag, k // BATCH, singles[k:k + BATCH]))
    for lid, tag, k, eids in batches:
        doc = client.fetch(f"lines/{lid}/{tag}/{k:02d}", lines_query(eids),
                           RAW / "lines" / str(lid) / tag / f"{k:02d}.json", {"lid": lid, "month": tag, "eids": eids},
                           refresh=(tag == refresh_month))
        if doc is None:
            C.log(f"[{SOURCE}] request budget spent at lines {lid} {tag} batch {k}")
            return {"requests": client.sent, "batches": len(batches), "stopped": "budget"}
    return {"requests": client.sent, "batches": len(batches)}


# --------------------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------------------
def ms_to_iso(value) -> str | None:
    if value in (None, ""):
        return None
    return dt.datetime.fromtimestamp(float(value) / 1000, dt.timezone.utc).isoformat(timespec="seconds")


def event_rows(doc: dict, provenance: dict) -> list[dict]:
    rows = []
    for e in doc["data"]["eventsByDateNew"]["events"]:
        group = e.get("eventGroup") or {}
        row = {"eid": e.get("eid"), "lid": e.get("lid"), "tour": LEAGUES.get(e.get("lid")), "des": e.get("des"),
               "es": e.get("es"), "dt_ms": e.get("dt"), "dt_utc": ms_to_iso(e.get("dt")),
               "group_id": group.get("egid"), "group": group.get("nam"), "group_parent_id": group.get("parentid"),
               "group_parent": group.get("parentname"), "singles": is_singles(e)}
        for key in ("spid", "tvs", "ic", "seid", "sta", "cit", "ven", "st", "cou"):
            row[key] = e.get(key)
        for p in e.get("participants") or []:
            side = "home" if p.get("ih") else "away"
            src = p.get("source") or {}
            row.update({f"{side}_partid": p.get("partid"), f"{side}_pid": src.get("pid", src.get("tmid")),
                        f"{side}_first": src.get("fn"), f"{side}_last": src.get("lnam", src.get("nam")),
                        f"{side}_rot": p.get("rot")})
        rows.append({**row, **provenance})
    return rows


def line_rows(doc: dict, provenance: dict) -> list[dict]:
    rows = []
    for alias, lines in doc["data"].items():
        kind = "last" if alias == "cur" else "open"
        for line in lines or []:
            row = {"kind": kind, **{k: line.get(k) for k in LINE_FIELDS}}
            row["book"] = BOOKS.get(line.get("paid"))
            row["market"] = MARKETS.get(line.get("mtid"))
            row["total_side"] = TOTAL_SIDES.get(line.get("partid"))
            row["tim_ms"] = int(float(line["tim"])) if line.get("tim") not in (None, "") else None
            row["tim_utc"] = ms_to_iso(line.get("tim"))
            rows.append({**row, **provenance})
    return rows


def matches_table(events: pd.DataFrame, lines: pd.DataFrame, paid: int = 8) -> pd.DataFrame:
    """One row per singles event: one book's opening and closing prices in both markets, with flags.

    The close is the last line the site recorded. It is flagged uncertain when stamped more than 30 minutes after
    the listed start, or when its two sides do not form a market (one side missing, or an implied-probability sum
    outside 1.00-1.15). On the 2024-26 pull, late closes and broken pairs were mostly the same matches."""
    cols = ["tour", "group", "es", "dt_ms", "dt_utc", "home_partid", "home_first", "home_last",
            "away_partid", "away_first", "away_last"]
    out = events[events["singles"]].set_index("eid")[cols].copy()
    book = lines[lines["paid"] == paid].sort_values("tim_ms").drop_duplicates(["kind", "mtid", "eid", "partid"],
                                                                                 keep="last")

    def iso(ms: pd.Series) -> pd.Series:
        return pd.to_datetime(ms, unit="ms", utc=True).map(lambda t: None if pd.isna(t) else t.isoformat())

    def sides(kind: str, mtid: int, first, second):
        part = book[(book["kind"] == kind) & (book["mtid"] == mtid)]
        if mtid == 126:
            part = part.merge(out[["home_partid", "away_partid"]], left_on="eid", right_index=True)
            a = part[part["partid"] == part["home_partid"]].set_index("eid")
            b = part[part["partid"] == part["away_partid"]].set_index("eid")
        else:
            a = part[part["partid"] == first].set_index("eid")
            b = part[part["partid"] == second].set_index("eid")
        return a.reindex(out.index), b.reindex(out.index)

    for mtid, prefix, first, second, labels in ((126, "mw", None, None, ("home", "away")),
                                                (396, "tg", 15143, 15144, ("over", "under"))):
        for kind, tag in (("open", "open"), ("last", "close")):
            a, b = sides(kind, mtid, first, second)
            if mtid == 396:
                out[f"{prefix}_{tag}_line"] = a["adj"].combine_first(b["adj"])
            out[f"{prefix}_{tag}_{labels[0]}"] = a["ap"]
            out[f"{prefix}_{tag}_{labels[1]}"] = b["ap"]
            ms = pd.concat([a["tim_ms"], b["tim_ms"]], axis=1).max(axis=1)
            out[f"{prefix}_{tag}_utc"] = iso(ms)
            out[f"{prefix}_{tag}_overround"] = (1 / a["pri"] + 1 / b["pri"]).round(4)
            present = a["ap"].notna() | b["ap"].notna()
            broken = present & ~out[f"{prefix}_{tag}_overround"].between(1.0, 1.15)
            if tag == "close":
                after = (ms - out["dt_ms"]) / 60000
                out[f"{prefix}_close_after_listed_min"] = after.round(1)
                out[f"{prefix}_close_off_board"] = a["iof"].fillna(False).astype(bool) | b["iof"].fillna(False).astype(bool)
                out[f"{prefix}_close_uncertain"] = present & ((after > 30) | broken)
            else:
                out[f"{prefix}_open_uncertain"] = broken
    out.insert(0, "book", BOOKS[paid])
    return out.reset_index()


def stage(receipts: C.Receipts) -> dict:
    latest = receipts.all()
    tables = {"events": [], "lines": []}
    for kind, parse in (("events", event_rows), ("lines", line_rows)):
        for path in sorted((RAW / kind).rglob("*.json")):
            name = path.relative_to(RAW).with_suffix("").as_posix()
            receipt = latest.get(name) or {}
            provenance = {"_source": SOURCE, "_source_file": C.rel(path), "_sha256": receipt.get("sha256"),
                          "_retrieved_at": receipt.get("retrieved_at")}
            tables[kind].extend(parse(json.loads(path.read_text(encoding="utf-8")), provenance))
    events = pd.DataFrame(tables["events"])
    if not events.empty:
        # Month windows do not overlap, but an event moved to another month can be listed twice: keep the newest.
        events = events.sort_values("_retrieved_at").drop_duplicates("eid", keep="last")
    lines = pd.DataFrame(tables["lines"])
    DUMP.mkdir(parents=True, exist_ok=True)
    events.to_parquet(DUMP / "events.parquet", index=False)
    lines.to_parquet(DUMP / "lines.parquet", index=False)
    matches = matches_table(events, lines) if len(events) and len(lines) else pd.DataFrame()
    matches.to_parquet(DUMP / "betonline_matches.parquet", index=False)
    return {"events": len(events), "singles": int(events["singles"].sum()) if len(events) else 0,
            "lines": len(lines), "betonline_matches": len(matches)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="first", default="2024-01", help="first month, YYYY-MM")
    ap.add_argument("--to", dest="last", default=dt.date.today().strftime("%Y-%m"), help="last month, YYYY-MM")
    ap.add_argument("--leagues", default="23,24", help="23 ATP, 24 WTA")
    ap.add_argument("--max-requests", type=int, default=400)
    ap.add_argument("--refresh-month", help="fetch this YYYY-MM again (listing and lines)")
    ap.add_argument("--stage-only", action="store_true", help="rebuild the tables from the raw responses")
    args = ap.parse_args()
    receipts = C.Receipts(SOURCE, root=RAW.parent)
    if not args.stage_only:
        client = Client(receipts, args.max_requests)
        try:
            counts = download(args.first, args.last, [int(x) for x in args.leagues.split(",")], client,
                              args.refresh_month)
        except Stop as err:
            C.log(f"[{SOURCE}] STOPPED after {client.sent} requests: {err}")
            C.log(f"[{SOURCE}] staged what was fetched: {stage(receipts)}")
            return 2
        C.log(f"[{SOURCE}] download: {counts}")
    C.log(f"[{SOURCE}] staged: {stage(receipts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
