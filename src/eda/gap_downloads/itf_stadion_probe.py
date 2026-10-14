"""Can the ITF live-data API list a 2025 event's matches (work package P7: ITF points of January 2025 to February 2026)?

SofaScore holds no ITF point records for January 2025 to February 2026. The ITF's own live-data API (Stadion; P1)
serves statistics and point-by-point by match id for 2025 matches too, but its day list, the only listing it is known to
serve, refuses dates more than 14 days old (data/studies/gap_sources/research_notes/C_itf_listings.md). Its widget
library also reads matches as generic resources (``match/<id>?include=round.draw.event...``), so the draws and events
may be readable the same way. This probe asks, for one 2025 event taken from an archived day list (W75 Zagreb,
W-ITF-CRO-2025-001; the list of 16 May 2025 in the research's Internet Archive copies):
    match/<id>?include=round.draw.event                 the generic match resource, with its draw and event
    round/<id>?include=matches, draw/<id>?include=rounds.matches, event/<id>?include=draws.rounds.matches
    match?filter[roundId]=<id>, event?filter[tennisId]=<key>
and, for any early-round match a listing returns, its custom/pointByPoint and custom/widgetMatchStats.

Paced (2.5 s plus up to 1 s), one request at a time, with receipts; answers gzipped under
data/raw/point_sources/itf_stadion_probe/ (gitignored); a --max-requests budget; a stop on a block. Not to be run while
P1's collector (src/ingest/point_sources/itf_live.py) is running: same host.

Writes data/studies/gap_downloads/itf_stadion_probe.json.

Usage: ./python.sh src/eda/gap_downloads/itf_stadion_probe.py [--max-requests 40]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P                   # noqa: E402
from src.ingest.point_sources import itf_live as L                 # noqa: E402

SOURCE = "itf_stadion_probe"
STUDY = PROJECT_ROOT / "data" / "studies" / "gap_downloads"
ARCHIVED = (PROJECT_ROOT / "data" / "raw" / "gap_sources" / "itf" / "other" / "web.archive.org" / "stadion" /
            "custom_wttCompleteMatchList_2025-05-16__20250516235401.json")


def find_ids(obj, key: str, out=None) -> list[str]:
    """Every ``id`` under a dict key named ``key`` (or ``<key>Id`` values), anywhere in a JSON answer."""
    out = [] if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, dict) and v.get("id"):
                out.append(v["id"])
            elif k == f"{key}Id" and isinstance(v, str) and v:
                out.append(v)
            find_ids(v, key, out)
    elif isinstance(obj, list):
        for v in obj:
            find_ids(v, key, out)
    return list(dict.fromkeys(out))


def matches_in(obj, out=None) -> list[dict]:
    """Every dict that looks like a match (an id and a match-style tennisId, '-S-M-' for singles main draw)."""
    out = [] if out is None else out
    if isinstance(obj, dict):
        if obj.get("id") and "-S-" in str(obj.get("tennisId") or ""):
            out.append({"id": obj["id"], "tennisId": obj["tennisId"]})
        for v in obj.values():
            matches_in(v, out)
    elif isinstance(obj, list):
        for v in obj:
            matches_in(v, out)
    return list({m["id"]: m for m in out}.values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-requests", type=int, default=40)
    args = parser.parse_args()
    P.configure_stdout()
    day = json.loads(ARCHIVED.read_text(encoding="utf-8"))["data"]
    event = next(e for e in day.values() if e.get("tennisId") == "W-ITF-CRO-2025-001")
    match = next(m for ms in event["courts"].values() for m in ms if "-S-M-" in str(m.get("tennisId")))
    ids = {"event": event["id"], "event_key": event["tennisId"], "match": match["id"], "round": match["roundId"]}
    client = P.Client(L.IMPERSONATE, min_interval=2.5, jitter=1.0, max_requests=args.max_requests, headers=L.HEADERS)
    receipts = P.receipts_for(SOURCE)
    results, stopped = [], None

    def ask(label: str, path: str):
        name = path.replace("?", "__").replace("/", "_").replace("[", "(").replace("]", ")").replace("=", "-")[:150]
        dest = P.raw_path(SOURCE, f"{name}.json.gz")
        r = P.fetch(client, L.API + path, dest, receipts, name=name, validator=P.json_validator, compress=True)
        doc = P.read_json(dest) if r.get("status") == 200 and not r.get("error") and dest.exists() else None
        found = matches_in(doc) if doc is not None else []
        results.append({"label": label, "path": path, "status": r.get("status"), "error": r.get("error"),
                        "bytes": r.get("bytes"), "matches_found": len(found),
                        "top_keys": list(doc)[:6] if isinstance(doc, dict) else None})
        P.log(f"[itf_stadion_probe] {label}: {r.get('status')} {r.get('error') or ''} {r.get('bytes')} bytes; "
              f"{len(found)} singles main-draw matches in it")
        return doc, found

    try:
        doc, _ = ask("match with round, draw and event", f"match/{ids['match']}?include=round.draw.event")
        draw = (find_ids(doc, "draw") or [None])[0] if doc else None
        ids["draw"] = draw
        listing = []
        for label, path in [("round with matches", f"round/{ids['round']}?include=matches"),
                            ("draw with rounds and matches", f"draw/{draw}?include=rounds.matches" if draw else None),
                            ("event with draws, rounds, matches", f"event/{ids['event']}?include=draws.rounds.matches"),
                            ("matches filtered by round", f"match?filter[roundId]={ids['round']}"),
                            ("event filtered by key", f"event?filter[tennisId]={ids['event_key']}")]:
            if path is None:
                continue
            _, found = ask(label, path)
            if len(found) > len(listing):
                listing = found
        early = [m for m in listing if any(f"-{r}-" in m["tennisId"] for r in ("1", "R32", "R16", "QF"))] or listing
        for m in early[:2]:
            ask(f"points of {m['tennisId'][:40]}", f"custom/pointByPoint/{m['id']}")
            ask(f"statistics of {m['tennisId'][:40]}", f"custom/widgetMatchStats/{m['id']}")
    except (P.Blocked, P.BudgetExhausted) as stop:
        stopped = f"{type(stop).__name__}: {stop}"
        P.log(f"[itf_stadion_probe] STOPPED: {stop}")
    out = {"generated_at": P.utc_now_iso(), "ids": ids, "stopped": stopped, "client": client.stats(), "asked": results}
    path = STUDY / "itf_stadion_probe.json"
    path.write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")
    P.log(f"[itf_stadion_probe] written {P.rel(path)}")
    return 1 if stopped else 0


if __name__ == "__main__":
    sys.exit(main())
