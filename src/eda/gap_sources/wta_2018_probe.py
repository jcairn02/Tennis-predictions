"""Is the WTA API's point log really empty for 2018? A spread of 2018 editions, two matches each.

The official feeds study found the umpire's event log (``.../matches/<MatchID>/events``) empty for the one
2018 match it asked (the Charleston final), and point-by-point absent before March 2022, so the data map
says WTA point data starts in 2019. This asks the event log and point-by-point of the final and one
first-round match of ten 2018 editions spread over the season and the tiers, plus the WTA 125 events.

The API is read as src/ingest/point_sources/wta.py reads it: plain GETs with an honest User-Agent, no key,
2 s apart plus jitter, stop on a block, a hard budget (under the owner's decision of 24 Sep 2026).

Usage:
    ./python.sh src/eda/gap_sources/wta_2018_probe.py

Writes data/raw/gap_sources/wta/ (verbatim, _receipts.jsonl; gitignored) and
data/studies/gap_sources/wta_2018_probe.csv.
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P        # noqa: E402
from src.ingest.public_dump import common as C          # noqa: E402

API = "https://api.wtatennis.com/tennis"
USER_AGENT = "tennis-predictions research (non-commercial; python-requests)"
RAW = PROJECT_ROOT / "data" / "raw" / "gap_sources"
OUT = PROJECT_ROOT / "data" / "studies" / "gap_sources" / "wta_2018_probe.csv"
# (tournament group id, tier label) from the 2018 calendar already on disk (data/raw/point_sources/wta/calendar/2018_0.json)
EDITIONS = [(800, "Premier Brisbane, Jan"), (1003, "Premier 5 Doha, Feb"), (609, "Premier Mandatory Indian Wells, Mar"),
            (1038, "Premier Mandatory Madrid, May"), (1091, "International Mallorca, Jun"),
            (1017, "Premier 5 Cincinnati, Aug"), (1075, "Premier 5 Wuhan, Sep"), (730, "Premier Moscow, Oct"),
            (808, "WTA Finals Singapore, Oct"), (1072, "125K Limoges, Nov")]


class Session:
    """A requests session with the same pace and stop rules as the project's clients."""

    def __init__(self, budget: int):
        import requests
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        self.client = P.Client("chrome", min_interval=2.0, jitter=1.0, max_requests=budget, session=session)


def main() -> int:
    P.configure_stdout()
    receipts = C.Receipts("wta", root=RAW)
    client = Session(budget=60).client
    rows = []

    def get(url, rel):
        dest = RAW / "wta" / rel
        r = P.fetch(client, url, dest, receipts, name=rel, validator=P.json_validator)
        body = json.loads(dest.read_bytes()) if r.get("status") == 200 and dest.exists() else None
        return r.get("error") or r.get("status"), body

    try:
        for tid, label in EDITIONS:
            status, doc = get(f"{API}/tournaments/{tid}/2018/matches", f"tournaments/{tid}_2018/matches.json")
            singles = [m for m in (doc or {}).get("matches") or [] if m.get("DrawMatchType") == "S"
                       and m.get("DrawLevelType") == "M" and m.get("MatchState") == "F"]
            if not singles:
                rows.append({"tournament_id": tid, "edition": label, "list_status": status, "singles_played": 0})
                continue
            singles.sort(key=lambda m: str(m.get("RoundID")))
            final = [m for m in singles if str(m.get("RoundID")) == "F"] or singles[-1:]
            first = [m for m in singles if m is not final[0]][:1]
            for m in final + first:
                mid = m["MatchID"]
                row = {"tournament_id": tid, "edition": label, "list_status": status, "singles_played": len(singles),
                       "match_id": mid, "round": m.get("RoundID"),
                       "players": f"{m.get('PlayerNameLastA')} v {m.get('PlayerNameLastB')}"}
                for endpoint in ("events", "point-by-point"):
                    st, body = get(f"{API}/tournaments/{tid}/2018/matches/{mid}/{endpoint}",
                                   f"matches/{tid}_2018/{mid}/{endpoint}.json")
                    row[f"{endpoint}_status"] = st
                    if endpoint == "events":
                        events = (body or {}).get("Events") or []
                        row["events_records"] = len(events)
                        row["events_points"] = sum(1 for e in events if (e.get("Attributes") or {}).get("type") in ("Point", "Ace", "Fault")
                                                   or e.get("Name") in ("Point", "Ace"))
                    else:
                        row["pbp_points"] = len((body or {}).get("pointByPoint") or body or []) if isinstance(body, (dict, list)) else None
                rows.append(row)
    except (P.Blocked, P.BudgetExhausted) as stop:
        rows.append({"edition": f"STOPPED: {stop}"})
    frame = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUT, index=False)
    print(frame.to_string())
    print("requests", client.requests)
    return 0


if __name__ == "__main__":
    sys.exit(main())
