"""SofaScore against the data map's gaps: does it list the sampled matches, with points and a box score?

For every edition in data/studies/gap_sources/sample_editions.csv (drawn by sample.py):

1. **Locate it.** Read SofaScore's day listing of the edition's category (ITF Men, ITF Women, Challenger,
   WTA 125, ATP or WTA) on a few days of its week, and take the tournament season whose singles events
   name the most of the edition's known matches (both players).
2. **List it.** Every singles event of that season (``/unique-tournament/<id>/season/<id>/events/last/<n>``).
3. **Link** each of the edition's gap matches to an event: both players' names share a word, and the
   event starts within 10 days before and 21 after the tournament start.
4. **Check** the sampled matches ("check" rows): ``/event/<id>/point-by-point`` and ``/event/<id>/statistics``.
   A point record is *complete* when every set has as many games as the event's set scores.

Endpoints (public JSON behind SofaScore's site, no key; observed 29 Sep 2026):
    /api/v1/sport/tennis/<date>/0/categories                    categories with events that day (small)
    /api/v1/category/<id>/scheduled-events/<date>               that day's events (about a day either side)
    /api/v1/unique-tournament/<id>/season/<id>/events/last/<n>  30 events a page, newest first
    /api/v1/event/<id>/point-by-point, /api/v1/event/<id>/statistics   HTTP 404 when absent

Pace and stops are those of src/ingest/point_sources/common.Client (a Chrome TLS fingerprint, one request
at a time, a minimum interval with jitter, a --max-requests budget, stop on 403/429/challenge). Every
answer is cached with a receipt, so a rerun asks only for what is missing. SofaScore's terms forbid
automated extraction; this is a bounded measurement under the owner's decision of 23 Sep 2026.

Usage:
    ./python.sh src/eda/gap_sources/sofascore_probe.py [--gaps itf_detail,...] [--max-requests 1400]
    ./python.sh src/eda/gap_sources/sofascore_probe.py --offline      # rebuild the tables from the cache
    ./python.sh src/eda/gap_sources/sofascore_probe.py --browser      # when SofaScore challenges the plain client:
        requests go through a Chrome tab the owner opened with a debugging port, as for the adapter
        (the Chrome command is in docs/studies/point_shot_sources/README.md, Rerunning)

Writes data/raw/gap_sources/sofascore/ (verbatim, gzipped, _receipts.jsonl; gitignored) and
data/studies/gap_sources/sofascore_editions.csv, sofascore_matches.csv, sofascore_summary.json.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P        # noqa: E402
from src.ingest.public_dump import common as C          # noqa: E402

SOURCE = "sofascore"
RAW = PROJECT_ROOT / "data" / "raw" / "gap_sources"
OUT = PROJECT_ROOT / "data" / "studies" / "gap_sources"
API = "https://api.sofascore.com/api/v1"
HEADERS = {"Accept": "*/*", "Referer": "https://www.sofascore.com/", "Origin": "https://www.sofascore.com"}
FIXED_CATEGORY = {("M", "ITF"): 785, ("W", "ITF"): 213, ("M", "CH"): 72, ("M", "tour"): 3, ("W", "tour"): 6}
OFFSETS = {"ITF": [2, 4, 1, 5], "CH": [2, 4, 1, 5, -1], "CHQ": [0, -1, 1, 2], "tour": [2, 4, 1, 6, 0, -1],
           "GS": [2, 5, 8, 11, 0]}
FULL_BOX = {"aces", "doubleFaults", "firstServeAccuracy", "firstServePointsAccuracy", "secondServePointsAccuracy",
            "breakPointsSaved"}
PARTICLES = {"jr", "sr", "ii", "iii", "iv", "de", "da", "van", "von", "del", "der", "la", "le", "di", "dos", "du"}
MAX_SEASON_PAGES = 25


# ------------------------------------------------------------------------------------------ names
def words(name) -> frozenset:
    text = "".join(ch for ch in unicodedata.normalize("NFKD", str(name or "")) if not unicodedata.combining(ch))
    return frozenset(w for w in re.split(r"[^a-z]+", text.lower()) if len(w) >= 3 and w not in PARTICLES)


def pair_score(a: frozenset, b: frozenset, h: frozenset, w: frozenset) -> int:
    """Words shared by the two pairs in the better orientation; 0 unless both players share a word."""
    best = 0
    for x, y in ((h, w), (w, h)):
        s1, s2 = len(a & x), len(b & y)
        if s1 and s2:
            best = max(best, s1 + s2)
    return best


def is_doubles(event: dict) -> bool:
    home, away = event.get("homeTeam") or {}, event.get("awayTeam") or {}
    return bool(home.get("subTeams") or away.get("subTeams") or home.get("type") == 2 or away.get("type") == 2)


def team_words(team: dict) -> frozenset:
    return words(team.get("name")) | words(team.get("shortName")) | words((team.get("slug") or "").replace("-", " "))


# ------------------------------------------------------------------------------------------ fetching
class Probe:
    def __init__(self, client, receipts, offline: bool):
        self.client, self.receipts, self.offline = client, receipts, offline
        self.never_asked = 0   # offline: answers the online runs never got (the run stopped first)

    def get(self, url: str, rel_path: str, name: str) -> dict | None:
        """The JSON at ``url`` (cached under RAW/sofascore/rel_path), or None when absent or failed."""
        dest = RAW / SOURCE / rel_path
        if self.offline:
            r = self.receipts.get(name) or {}
            self.never_asked += not r
        else:
            r = P.fetch(self.client, url, dest, self.receipts, name=name, validator=P.json_validator,
                        compress=dest.suffix == ".gz")
        if r.get("status") == 200 and not r.get("error") and dest.exists():
            return P.read_json(dest)
        return None

    def status(self, name: str):
        r = self.receipts.get(name) or {}
        return r.get("error") or r.get("status") or ("not fetched" if not r else None)

    def categories(self, day: str) -> list[dict]:
        doc = self.get(f"{API}/sport/tennis/{day}/0/categories", f"categories/{day}.json", f"categories/{day}")
        return (doc or {}).get("categories") or []

    def day_events(self, category: int, day: str) -> list[dict]:
        doc = self.get(f"{API}/category/{category}/scheduled-events/{day}", f"category/{category}/{day}.json.gz",
                       f"category/{category}/{day}")
        return (doc or {}).get("events") or []

    def season_events(self, utid: int, sid: int) -> tuple[list[dict], int]:
        events, pages = [], 0
        for page in range(MAX_SEASON_PAGES):
            doc = self.get(f"{API}/unique-tournament/{utid}/season/{sid}/events/last/{page}",
                           f"season/{utid}_{sid}/last_{page}.json.gz", f"season/{utid}_{sid}/last_{page}")
            if doc is None:
                break
            pages += 1
            events.extend(doc.get("events") or [])
            if not doc.get("hasNextPage"):
                break
        return events, pages

    def event_part(self, event_id: int, part: str) -> dict | None:
        return self.get(f"{API}/event/{event_id}/{part}", f"events/{event_id}/{part}.json.gz", f"events/{event_id}/{part}")


# ------------------------------------------------------------------------------------------ steps
def level_group(levels: str) -> str:
    lv = set(levels.split(";"))
    if lv & {"ITF", "ITFQ"}:
        return "ITF"
    if lv == {"CHQ"}:
        return "CHQ"
    if lv & {"CH", "CHQ"}:
        return "CH"
    if lv & {"GS", "GSQ"}:
        return "GS"
    return "tour"


def category_for(probe: Probe, tour: str, group: str, day: str) -> int | None:
    key = (tour, "CH" if group in ("CH", "CHQ") else "ITF" if group == "ITF" else "tour")
    if key in FIXED_CATEGORY:
        return FIXED_CATEGORY[key]
    # WTA 125: its category id is read from the day's categories (name contains 125), else WTA itself
    for c in probe.categories(day):
        if "125" in (c.get("category") or {}).get("name", ""):
            return c["category"]["id"]
    return FIXED_CATEGORY[(tour, "tour")]


def best_event(a: frozenset, b: frozenset, d0: pd.Timestamp, d1: pd.Timestamp, events: list[dict]):
    """The singles event whose players share the most name words with (a, b), inside the date window."""
    best, best_key = None, None
    lo, hi = (d0 - pd.Timedelta(days=10)).timestamp(), (d1 + pd.Timedelta(days=21)).timestamp()
    for e in events:
        ts = e.get("startTimestamp") or 0
        if not lo <= ts <= hi:
            continue
        s = pair_score(a, b, e["_hw"], e["_aw"])
        if s:
            key = (s, -abs(ts - d0.timestamp()))
            if best_key is None or key > best_key:
                best, best_key = e, key
    return best


def prep(events: list[dict]) -> list[dict]:
    out = []
    for e in events:
        if is_doubles(e):
            continue
        e["_hw"], e["_aw"] = team_words(e.get("homeTeam") or {}), team_words(e.get("awayTeam") or {})
        out.append(e)
    return out


def locate(probe: Probe, ed: pd.Series, known: pd.DataFrame) -> dict:
    """Find the SofaScore tournament season holding this edition."""
    group = level_group(ed["levels"])
    d0 = pd.Timestamp(ed["d_min"])
    tried = []
    need = 2 if len(known) >= 4 else 1
    for off in OFFSETS[group]:
        day = (d0 + pd.Timedelta(days=off)).strftime("%Y-%m-%d")
        cat = category_for(probe, ed["tour"], group, day)
        events = prep(probe.day_events(cat, day))
        tried.append(f"{cat}/{day}:{len(events)}")
        hits = Counter()
        names = {}
        for a, b in zip(known["w1"], known["w2"]):
            e = best_event(a, b, d0, pd.Timestamp(ed["d_max"]), events)
            if e is not None:
                key = ((e.get("tournament") or {}).get("uniqueTournament") or {}).get("id"), (e.get("season") or {}).get("id")
                hits[key] += 1
                names[key] = ((e.get("tournament") or {}).get("name"), (e.get("season") or {}).get("name"))
        if hits:
            key, n = hits.most_common(1)[0]
            if n >= need and key[0] and key[1]:
                return {"utid": key[0], "sid": key[1], "ss_tournament": names[key][0], "ss_season": names[key][1],
                        "located_by": f"{cat}/{day}", "locate_hits": n, "locate_tried": ";".join(tried)}
    return {"utid": None, "sid": None, "located_by": None, "locate_hits": 0, "locate_tried": ";".join(tried)}


def pbp_check(pbp: list, event: dict) -> dict:
    sets = sorted(pbp, key=lambda s: s.get("set") or 0)
    games = {s.get("set"): len(s.get("games") or []) for s in sets}
    points = sum(len(g.get("points") or []) for s in sets for g in s.get("games") or [])
    hs, as_ = event.get("homeScore") or {}, event.get("awayScore") or {}
    want = {}
    for n in range(1, 6):
        h, a = hs.get(f"period{n}"), as_.get(f"period{n}")
        if h is None or a is None:
            continue
        want[n] = int(h) + int(a)
    status = event.get("status") or {}
    retired = status.get("code") == 92 or "retired" in str(status.get("description") or "").lower()
    extra = sum(games.values()) - sum(want.values())
    if not want:
        verdict = "no score to compare"
    elif all(games.get(n) == g for n, g in want.items()) and len(games) == len(want):
        verdict = "complete"
    elif retired and 0 <= extra <= 1:
        verdict = "complete to retirement"   # the record also lists the game in progress when play stopped
    elif all(games.get(n, 0) <= g for n, g in want.items()):
        verdict = "short"
    else:
        verdict = "other"
    return {"pbp_sets": len(sets), "pbp_games": sum(games.values()), "pbp_points": points,
            "score_games": sum(want.values()), "pbp_verdict": verdict}


def stats_check(doc: list) -> dict:
    keys = set()
    for period in doc:
        if period.get("period") == "ALL":
            for g in period.get("groups") or []:
                keys |= {it.get("key") for it in g.get("statisticsItems") or []}
    return {"stats_keys": len(keys), "stats_full_box": FULL_BOX <= keys,
            "stats_aces_df_only": bool(keys) and not (FULL_BOX <= keys),
            "stats_winners_errors": "winnersTotal" in keys or "unforcedErrorsTotal" in keys}


# ------------------------------------------------------------------------------------------ run
def wilson(k: int, n: int) -> list:
    if n == 0:
        return [None, None]
    z, p = 1.96, k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(mid - half, 3), round(mid + half, 3)]


def make_client(args):
    """The plain Chrome-fingerprint client, or with --browser the adapter's transport inside a Chrome tab the
    owner opened (src/ingest/point_sources/browser.py; for when SofaScore challenges the plain client)."""
    if getattr(args, "browser", None):
        from src.ingest.point_sources import browser as B
        return B.BrowserClient(args.browser, origin="https://www.sofascore.com",
                               url_map={"https://api.sofascore.com/": "https://www.sofascore.com/"},
                               token_key="sofa.captcha.token", min_interval=args.min_interval, jitter=args.jitter,
                               max_requests=args.max_requests, headers={"Accept": "*/*"})
    return P.Client("chrome", min_interval=args.min_interval, jitter=args.jitter, max_requests=args.max_requests,
                    headers=HEADERS if "HEADERS" in globals() else S.HEADERS)


def run(args) -> int:
    P.configure_stdout()
    editions = pd.read_csv(OUT / "sample_editions.csv")
    matches = pd.read_csv(OUT / "sample_matches.csv", parse_dates=["d"])
    if args.gaps:
        keep = set(args.gaps.split(","))
        editions, matches = editions[editions["gap"].isin(keep)], matches[matches["gap"].isin(keep)]
    universe = pd.read_parquet(PROJECT_ROOT / "data" / "studies" / "data_map" / "matches.parquet",
                               columns=["uid", "tour", "tname", "year", "d", "name1", "name2"])
    receipts = C.Receipts(SOURCE, root=RAW)
    client = None if args.offline else make_client(args)
    probe = Probe(client, receipts, args.offline)
    for frame in (matches, universe):
        frame["w1"], frame["w2"] = frame["name1"].map(words), frame["name2"].map(words)
    ed_rows, match_rows, stopped = [], [], None
    started = time.time()
    try:
        for i, ed in enumerate(editions.itertuples(index=False), 1):
            ed = pd.Series(ed._asdict())
            em = matches[(matches["gap"] == ed["gap"]) & (matches["edition"] == ed["edition"])]
            tour, tname, year = ed["tour"], ed["tname"], int(ed["year"])
            d0, d1 = pd.Timestamp(ed["d_min"]), pd.Timestamp(ed["d_max"])
            known = universe[(universe["tour"] == tour) & (universe["tname"] == tname) & (universe["year"] == year)
                             & universe["d"].between(d0 - pd.Timedelta(days=3), d1 + pd.Timedelta(days=3))]
            asked_before = probe.never_asked
            loc = locate(probe, ed, known if len(known) else em)
            events, pages = ([], 0)
            if loc["utid"]:
                events, pages = probe.season_events(int(loc["utid"]), int(loc["sid"]))
            singles = prep(events)
            if probe.never_asked > asked_before and not singles:
                # offline, and the online runs stopped before reaching this edition: nothing to count
                ed_rows.append({**{k: ed[k] for k in ("gap", "stratum", "edition", "tour", "tname", "year", "levels",
                                                     "gap_matches", "checked", "inclusion_prob")},
                                **loc, "season_pages": 0, "season_singles": 0, "gap_linked": None,
                                "note": "not reached: the online run stopped first"})
                continue
            linked = 0
            for m in em.itertuples(index=False):
                e = best_event(m.w1, m.w2, d0, d1, singles) if singles else None
                row = {"gap": m.gap, "stratum": m.stratum, "edition": m.edition, "role": m.role, "uid": m.uid,
                       "tour": m.tour, "level": m.level, "draw": m.draw, "year": m.year, "d": m.d.date(),
                       "name1": m.name1, "name2": m.name2, "listed": e is not None}
                if e is not None:
                    linked += 1
                    ts = e.get("startTimestamp")
                    row.update(event_id=e.get("id"), ss_home=(e.get("homeTeam") or {}).get("name"),
                               ss_away=(e.get("awayTeam") or {}).get("name"),
                               ss_round=(e.get("roundInfo") or {}).get("name"),
                               ss_start=dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else None,
                               ss_status=(e.get("status") or {}).get("description"),
                               ss_winner_code=e.get("winnerCode"), ss_first_to_serve=e.get("firstToServe"),
                               ss_final_result_only=e.get("finalResultOnly"))
                    if m.role == "check":
                        pbp = probe.event_part(e["id"], "point-by-point")
                        row["pbp_status"] = probe.status(f"events/{e['id']}/point-by-point")
                        if pbp is not None:
                            row.update(pbp_check(pbp.get("pointByPoint") or [], e))
                        st = probe.event_part(e["id"], "statistics")
                        row["stats_status"] = probe.status(f"events/{e['id']}/statistics")
                        if st is not None:
                            row.update(stats_check(st.get("statistics") or []))
                        if "not fetched" in (row["pbp_status"], row["stats_status"]):
                            row["role"] = "check_not_reached"   # offline: the online run stopped before asking
                match_rows.append(row)
            ed_rows.append({**{k: ed[k] for k in ("gap", "stratum", "edition", "tour", "tname", "year", "levels",
                                                 "gap_matches", "checked", "inclusion_prob")},
                            **loc, "season_pages": pages, "season_singles": len(singles), "gap_linked": linked})
            P.log(f"[{i}/{len(editions)}] {ed['gap']} {ed['edition']}: located={bool(loc['utid'])} "
                  f"({loc.get('ss_tournament')}), singles={len(singles)}, linked {linked}/{len(em)}; "
                  f"requests={client.requests if client else 0}")
    except (P.Blocked, P.BudgetExhausted) as stop:
        stopped = f"{type(stop).__name__}: {stop}"
        P.log(f"STOPPED: {stopped}")
    eds, ms = pd.DataFrame(ed_rows), pd.DataFrame(match_rows)
    if args.gaps and (OUT / "sofascore_matches.csv").exists():      # keep the other gaps' earlier rows
        old_m, old_e = pd.read_csv(OUT / "sofascore_matches.csv"), pd.read_csv(OUT / "sofascore_editions.csv")
        ms = pd.concat([old_m[~old_m["gap"].isin(keep)], ms], ignore_index=True)
        eds = pd.concat([old_e[~old_e["gap"].isin(keep)], eds], ignore_index=True)
    eds.to_csv(OUT / "sofascore_editions.csv", index=False)
    ms.to_csv(OUT / "sofascore_matches.csv", index=False)
    summary = summarize(eds, ms)
    summary.update(generated_at=P.utc_now_iso(), stopped=stopped, seconds=round(time.time() - started, 1),
                   client=client.stats() if client else "offline", args=vars(args))
    previous = OUT / "sofascore_summary.json"
    if previous.exists():   # keep the record of the last online run (and how it ended) through offline rebuilds
        old = json.loads(previous.read_text(encoding="utf-8"))
        last = old.get("last_online_run") if old.get("client") == "offline" else {
            k: old.get(k) for k in ("generated_at", "stopped", "seconds", "client", "args")}
        summary["last_online_run"] = None if client else last
    (OUT / "sofascore_summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    P.log(json.dumps(summary["by_gap"], indent=1, default=str))
    return 1 if stopped else 0


def summarize(eds: pd.DataFrame, ms: pd.DataFrame) -> dict:
    out = {"by_gap": {}, "by_stratum": {}}
    if ms.empty:
        return out
    for col in ("pbp_verdict", "stats_full_box", "stats_aces_df_only", "pbp_status", "stats_status"):
        if col not in ms:
            ms[col] = None
    chk = ms[ms["role"] == "check"]

    def cell(g_all, g_chk):
        n = len(g_chk)
        listed = int(g_chk["listed"].sum())
        pbp_any = int(pd.to_numeric(g_chk["pbp_status"], errors="coerce").eq(200).sum())
        pbp_full = int(g_chk["pbp_verdict"].isin(["complete", "complete to retirement"]).sum())
        box = int(g_chk["stats_full_box"].astype(str).str.lower().eq("true").sum())
        return {"listing_all_gap_matches": {"n": int(len(g_all)), "listed": int(g_all["listed"].sum()),
                                            "share": round(float(g_all["listed"].mean()), 3) if len(g_all) else None},
                "checked": n, "listed": listed, "points_any": pbp_any, "points_complete": pbp_full,
                "full_box_score": box,
                "share_points_any": [round(pbp_any / n, 3) if n else None, wilson(pbp_any, n)],
                "share_points_complete": [round(pbp_full / n, 3) if n else None, wilson(pbp_full, n)],
                "share_full_box": [round(box / n, 3) if n else None, wilson(box, n)]}

    for gap, g in ms.groupby("gap"):
        out["by_gap"][gap] = cell(g, chk[chk["gap"] == gap])
        e = eds[eds["gap"] == gap]
        out["by_gap"][gap]["editions"] = int(len(e))
        out["by_gap"][gap]["editions_located"] = int(e["utid"].notna().sum())
    for (gap, stratum), g in ms.groupby(["gap", "stratum"]):
        out["by_stratum"][f"{gap}|{stratum}"] = cell(g, chk[(chk["gap"] == gap) & (chk["stratum"] == stratum)])
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gaps", help="comma list of gap ids (default: every gap in the sample)")
    parser.add_argument("--max-requests", type=int, default=1400)
    parser.add_argument("--min-interval", type=float, default=1.2)
    parser.add_argument("--jitter", type=float, default=0.8)
    parser.add_argument("--browser", nargs="?", const="http://localhost:9222", metavar="CDP_URL",
                        help="make the requests inside a Chrome tab the owner opened (see src/ingest/point_sources/browser.py)")
    parser.add_argument("--offline", action="store_true", help="no HTTP: rebuild the tables from cached answers")
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
