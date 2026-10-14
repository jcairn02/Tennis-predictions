"""Does SofaScore hold anything for the ITF events it lists with ``coverage: -1`` (work package P7)?

P7 found no ITF point records from January 2025 to February 2026: SofaScore's listings flag almost every ITF singles
event of that window with ``coverage: -1``, and its /point-by-point answers 404. This asks a small seeded sample of
flagged events, one per sampled month, for four of SofaScore's per-event endpoints, beside two unflagged events with a
point record as controls:
    /event/<id>                  the event's own record (does it say more than the listing?)
    /event/<id>/tennis-power     SofaScore's momentum series (built from points, where it has them)
    /event/<id>/point-by-point   and /event/<id>/statistics (the controls already have these)
through the adapter's client and cache (receipts; nothing asked twice; the plan's pace; a budget; a stop on a block).
The events come from the season listings on disk (no listing request).

Writes data/studies/gap_downloads/sofascore_uncovered_probe.json.

Usage: ./python.sh src/eda/gap_downloads/sofascore_uncovered_probe.py --browser [--max-requests 40]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P                   # noqa: E402
from src.ingest.point_sources import sofascore as S                # noqa: E402
from src.ingest.point_sources import sofascore_editions as E       # noqa: E402

MONTHS = ["2025-01", "2025-03", "2025-07", "2025-10", "2026-01", "2026-02"]   # flagged events, one per month
CONTROL_MONTHS = ["2026-03", "2026-04"]                                       # unflagged, with a point record
EXTRA = ("event", "tennis-power")


def itf_singles(entry: dict) -> bool:
    e = entry["event"]
    name = str(S._dig(e, ("tournament", "name")) or "")
    return (("ITF" in name or "-ITF-" in name) and not E.is_qualifying(e) and not S.is_doubles(e)
            and S._dig(e, ("status", "type")) == "finished")


def month(e: dict) -> str:
    return dt.datetime.fromtimestamp(e.get("startTimestamp") or 0, dt.timezone.utc).strftime("%Y-%m")


def pick(listed: dict, receipts, seed: int) -> list[tuple[str, dict]]:
    """One flagged event per month of MONTHS and one unflagged event with a point record per month of CONTROL_MONTHS."""
    rng = random.Random(seed)
    out = []
    for m in MONTHS:
        pool = sorted((x["event"] for x in listed.values() if itf_singles(x) and month(x["event"]) == m
                       and E.uncovered(x["event"])), key=lambda e: e["id"])
        if pool:
            out.append(("flagged", rng.choice(pool)))
    for m in CONTROL_MONTHS:
        pool = sorted((x["event"] for x in listed.values() if itf_singles(x) and month(x["event"]) == m
                       and not E.uncovered(x["event"])
                       and (receipts.get(f"events/{x['event']['id']}/point-by-point") or {}).get("status") == 200),
                      key=lambda e: e["id"])
        if pool:
            out.append(("control", rng.choice(pool)))
    return out


def describe(doc) -> str:
    """A short account of a 200 answer: its top-level keys, and the length of any list in it."""
    if not isinstance(doc, dict):
        return type(doc).__name__
    parts = []
    for k, v in doc.items():
        parts.append(f"{k}[{len(v)}]" if isinstance(v, list) else k)
    return ", ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--max-requests", type=int, default=40)
    parser.add_argument("--min-interval", type=float, default=2.0)
    parser.add_argument("--jitter", type=float, default=1.0)
    parser.add_argument("--browser", nargs="?", const="http://localhost:9222", metavar="CDP_URL")
    args = parser.parse_args()
    P.configure_stdout()
    receipts = P.receipts_for(E.SOURCE)
    sample = pick(E.season_listings(), receipts, args.seed)
    client = E.make_client(args)
    lister = E.Lister(client, receipts, offline=False)
    rows, stopped = [], None
    try:
        for kind, e in sample:
            eid = e["id"]
            row = {"kind": kind, "event_id": eid, "month": month(e), "tournament": S._dig(e, ("tournament", "name")),
                   "home": S._dig(e, ("homeTeam", "name")), "away": S._dig(e, ("awayTeam", "name")),
                   "coverage": e.get("coverage")}
            for part in EXTRA:
                url = f"{E.API}/event/{eid}" + ("" if part == "event" else f"/{part}")
                doc = lister.get(url, f"events/{eid}/{part}.json.gz", f"events/{eid}/{part}")
                row[part] = lister.status(f"events/{eid}/{part}")
                row[f"{part}_content"] = describe(doc) if doc is not None else None
                if part == "event" and doc is not None:
                    ev = doc.get("event") or {}
                    row["event_coverage"] = ev.get("coverage")
                    row["event_flags"] = {k: v for k, v in ev.items() if k.startswith("has") or "overage" in k}
            for part in E.PARTS:
                doc = lister.event_part(eid, part)
                row[part] = lister.status(f"events/{eid}/{part}")
                row[f"{part}_content"] = describe(doc) if doc is not None else None
            rows.append(row)
            P.log(f"[uncovered_probe] {kind} {eid} {row['month']} {row['tournament']}: " +
                  ", ".join(f"{p}={row[p]}" for p in (*EXTRA, *E.PARTS)))
    except (P.Blocked, P.BudgetExhausted) as stop:
        stopped = f"{type(stop).__name__}: {stop}"
        P.log(f"[uncovered_probe] STOPPED: {stop}")
    finally:
        if hasattr(client, "close"):
            client.close()
    out = {"generated_at": P.utc_now_iso(), "args": vars(args), "stopped": stopped, "client": client.stats(),
           "events": rows}
    path = E.STUDY / "sofascore_uncovered_probe.json"
    path.write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")
    P.log(f"[uncovered_probe] written {P.rel(path)}")
    return 1 if stopped else 0


if __name__ == "__main__":
    sys.exit(main())
