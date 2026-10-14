"""Work package P12's question, asked for P7's hole: do itftennis.com's draws, read in a Chrome tab, give the match ids
that the ITF live-data API's per-match statistics and point-by-point accept, for 2025?

SofaScore holds no ITF point records for January 2025 to February 2026. The ITF live-data API (Stadion) serves
statistics and points by match id for 2025 matches, but lists matches only for the last 14 days, and exposes no draw,
round or event resource (itf_stadion_probe.py, 13 Oct 2026). itftennis.com lists every draw, behind Imperva, which
refused a plain client (data/studies/gap_sources/research_notes/C_itf_listings.md). So its own API is called here from
inside a Chrome tab on the site (browser.py's transport, its own profile and port 9223), as the page itself calls it:
    /tennis/api/TournamentApi/GetCalendar        the 2025 events of one week (keys)
    /tennis/api/TournamentApi/GetEventFilters    an event's numeric id
    /tennis/api/TournamentApi/GetDrawsheet       its singles main draw
For W75 Zagreb 2025 (W-ITF-CRO-2025-001) the archived ITF day list of 16 May 2025 gives two Stadion match ids, so the
draw is searched for them. If it carries them, the points and statistics of two of its matches are asked of the Stadion
API (plain client, as P1).

Paced, one request at a time, with receipts; answers gzipped under data/raw/point_sources/itf_site_probe/ (gitignored);
a --max-requests budget (the plan's P12 allows 150); a stop on a block. If Imperva shows a check, the run stops: it is
the owner's to click. Writes data/studies/gap_downloads/itf_site_probe.json.

Usage (Chrome open with --remote-debugging-port=9223 --user-data-dir=%LOCALAPPDATA%\\itf-cdp on www.itftennis.com):
    ./python.sh src/eda/gap_downloads/itf_site_probe.py [--max-requests 40]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P                   # noqa: E402
from src.ingest.point_sources import itf_live as L                 # noqa: E402

SOURCE = "itf_site_probe"
SITE = "https://www.itftennis.com"
STUDY = PROJECT_ROOT / "data" / "studies" / "gap_downloads"
KNOWN = {"W-ITF-CRO-2025-001": ["ca3cea83-c144-4576-936e-cbad91bd18a7", "f67b5975-e57f-4ebd-898d-28d51b1a7db3"]}
UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def calendar_path(circuit: str, date_from: str, date_to: str) -> str:
    return (f"/tennis/api/TournamentApi/GetCalendar?circuitCode={circuit}&searchString=&skip=0&take=100&nationCodes="
            f"&zoneCodes=&dateFrom={date_from}&dateTo={date_to}&indoorOutdoor=&categories=&isOrderAscending=true"
            f"&orderField=startDate&surfaceCodes=")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-requests", type=int, default=40)
    parser.add_argument("--cdp", default="http://localhost:9223")
    args = parser.parse_args()
    P.configure_stdout()
    from src.ingest.point_sources import browser as B

    receipts = P.receipts_for(SOURCE)
    site = B.BrowserClient(args.cdp, origin=SITE, min_interval=2.5, jitter=1.0, max_requests=args.max_requests,
                           headers={"Accept": "application/json, text/plain, */*"})
    stadion = P.Client(L.IMPERSONATE, min_interval=2.5, jitter=1.0, max_requests=10, headers=L.HEADERS)
    page = site._session.page
    title = page.title()
    body = page.evaluate("() => document.body ? document.body.innerText.slice(0, 400) : ''")
    out = {"generated_at": P.utc_now_iso(), "page_title": title, "asked": [], "stopped": None}
    if "incapsula" in (title + body).lower() or "request unsuccessful" in body.lower():
        out["stopped"] = "Imperva's block page is showing in the tab"
    asked = out["asked"]

    def ask(client, base: str, label: str, path: str):
        name = re.sub(r"[^A-Za-z0-9_.-]+", "_", path.strip("/"))[:150]
        dest = P.raw_path(SOURCE, f"{name}.json.gz")
        r = P.fetch(client, base + path, dest, receipts, name=name, validator=P.json_validator, compress=True)
        doc = P.read_json(dest) if r.get("status") == 200 and not r.get("error") and dest.exists() else None
        text = json.dumps(doc) if doc is not None else ""
        asked.append({"label": label, "path": path, "status": r.get("status"), "error": r.get("error"),
                      "bytes": r.get("bytes"), "uuids": len(set(UUID.findall(text)))})
        P.log(f"[itf_site_probe] {label}: {r.get('status')} {r.get('error') or ''} {r.get('bytes')} bytes")
        return doc, text

    try:
        if out["stopped"]:
            raise P.Blocked(out["stopped"])
        cal, cal_text = ask(site, SITE, "calendar, women, 12-18 May 2025", calendar_path("WT", "2025-05-12", "2025-05-18"))
        out["calendar_keys"] = sorted(set(re.findall(r"[WM]-ITF-[A-Z]{3}-2025-\d{3}", cal_text)))[:60]
        key = "W-ITF-CRO-2025-001"
        filters, _ = ask(site, SITE, f"event filters {key}", f"/tennis/api/TournamentApi/GetEventFilters?tournamentKey={key}")
        tid = (filters or {}).get("tournamentId")
        out["tournament_id"] = tid
        if tid:
            draw, draw_text = ask(site, SITE, f"main draw {key}",
                                  f"/tennis/api/TournamentApi/GetDrawsheet?circuitCode=WT&eventClassificationCode=M"
                                  f"&matchTypeCode=S&tournamentId={tid}&tourType=N&weekNumber=0")
            ids = sorted(set(u.lower() for u in UUID.findall(draw_text)))
            out["draw_uuids"] = len(ids)
            out["known_ids_in_draw"] = [m for m in KNOWN[key] if m in ids]
            out["draw_sample"] = draw_text[:1500]
            for mid in out["known_ids_in_draw"][:1] + [u for u in ids if u not in KNOWN[key]][:1]:
                ask(stadion, L.API, f"points {mid}", f"custom/pointByPoint/{mid}")
                ask(stadion, L.API, f"statistics {mid}", f"custom/widgetMatchStats/{mid}")
    except (P.Blocked, P.BudgetExhausted) as stop:
        out["stopped"] = f"{type(stop).__name__}: {stop}"
        P.log(f"[itf_site_probe] STOPPED: {stop}")
    finally:
        site.close()
    out["client"] = {"site": site.stats(), "stadion": stadion.stats()}
    path = STUDY / "itf_site_probe.json"
    path.write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")
    P.log(f"[itf_site_probe] written {P.rel(path)}")
    return 1 if out["stopped"] else 0


if __name__ == "__main__":
    sys.exit(main())
