"""SofaScore against the two ITF gaps no file lists: women's ITF qualifying 2025-26, and ITF after June 2026.

Neither gap has known matches to sample, so each is measured from SofaScore's own listings and calibrated
on a year the project's files do cover:

* **Women's ITF qualifying.**
  * *2024, the benchmark:* eight women's ITF editions with Sackmann qualifying rows, drawn with probability
    proportional to their qualifying matches. Each is located on SofaScore through its qualifying matches,
    its events listed, and Sackmann's qualifying matches linked to them (listing coverage).
  * *2025-26:* ten women's ITF editions of the data map (main draws are held to early June 2026), located
    through their main-draw matches; SofaScore's qualifying events in the same tournament season are
    counted and compared with 2024's qualifying matches per edition of the same grade (W15, W35 ...).
  * A few qualifying events of each period have their point-by-point and statistics read.
* **ITF after June 2026.**
  * *Weekly counts:* the ITF singles tournaments SofaScore lists on the Wednesday of ISO weeks 27-38, in
    2026 and in 2025 (when Sackmann's files list them too, so the two can be compared).
  * *Editions:* twelve 2026 tournaments from those lists (six men's, six women's), their events listed:
    main-draw matches finished with a winner, qualifying events, and the points and box score of three
    main-draw matches each.

Endpoints, pace, stops and caching as in sofascore_probe.py (the same cache, data/raw/gap_sources/sofascore/).

Usage:
    ./python.sh src/eda/gap_sources/sofascore_itf_listings.py [--max-requests 700] [--offline] [--browser]

Writes data/studies/gap_sources/sofascore_itf_listings.json and sofascore_itf_editions.csv.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.gap_sources import sofascore_probe as S   # noqa: E402
from src.ingest.point_sources import common as P        # noqa: E402
from src.ingest.public_dump import common as C          # noqa: E402

OUT = S.OUT
MATCHES = PROJECT_ROOT / "data" / "studies" / "data_map" / "matches.parquet"
SEED = 20260929


def grade(tname: str) -> str | None:
    import re
    m = re.match(r"^[MW](\d{2,3})\b", str(tname or ""))
    if m:
        return m.group(1)
    m = re.search(r"\$(\d{2,3})K", str(tname or ""))
    return m.group(1) if m else None


def is_qual_round(name) -> bool:
    return "qualif" in str(name or "").lower()


def locate_with(probe: S.Probe, tour: str, d0: pd.Timestamp, offsets: list[int], known: pd.DataFrame) -> dict:
    category = S.FIXED_CATEGORY[(tour, "ITF")]
    tried = []
    for off in offsets:
        day = (d0 + pd.Timedelta(days=off)).strftime("%Y-%m-%d")
        events = S.prep(probe.day_events(category, day))
        tried.append(f"{category}/{day}:{len(events)}")
        hits, names = Counter(), {}
        for a, b in zip(known["w1"], known["w2"]):
            e = S.best_event(a, b, d0, d0 + pd.Timedelta(days=7), events)
            if e is not None:
                key = (((e.get("tournament") or {}).get("uniqueTournament") or {}).get("id"), (e.get("season") or {}).get("id"))
                hits[key] += 1
                names[key] = (e.get("tournament") or {}).get("name")
        if hits:
            key, n = hits.most_common(1)[0]
            if n >= (2 if len(known) >= 4 else 1) and key[0] and key[1]:
                return {"utid": key[0], "sid": key[1], "ss_tournament": names[key], "locate_hits": n,
                        "located_by": f"{category}/{day}", "locate_tried": ";".join(tried)}
    return {"utid": None, "sid": None, "locate_hits": 0, "locate_tried": ";".join(tried)}


def season_counts(events: list[dict]) -> dict:
    singles = S.prep(events)
    qual = [e for e in singles if is_qual_round((e.get("roundInfo") or {}).get("name"))]
    main = [e for e in singles if e not in qual]
    fin = lambda es: [e for e in es if (e.get("status") or {}).get("type") == "finished" and e.get("winnerCode") in (1, 2)]
    return {"ss_singles": len(singles), "ss_main": len(main), "ss_main_finished": len(fin(main)),
            "ss_qual": len(qual), "ss_qual_finished": len(fin(qual)),
            "ss_qual_rounds": ";".join(f"{k}:{v}" for k, v in sorted(Counter((e.get("roundInfo") or {}).get("name") for e in qual).items()))}


def check_events(probe: S.Probe, events: list[dict], n: int, rng) -> list[dict]:
    rows = []
    picks = rng.choice(len(events), size=min(n, len(events)), replace=False) if events else []
    for i in picks:
        e = events[int(i)]
        row = {"event_id": e["id"], "round": (e.get("roundInfo") or {}).get("name")}
        pbp = probe.event_part(e["id"], "point-by-point")
        row["pbp_status"] = probe.status(f"events/{e['id']}/point-by-point")
        if pbp is not None:
            row.update(S.pbp_check(pbp.get("pointByPoint") or [], e))
        st = probe.event_part(e["id"], "statistics")
        row["stats_status"] = probe.status(f"events/{e['id']}/statistics")
        if st is not None:
            row.update(S.stats_check(st.get("statistics") or []))
        rows.append(row)
    return rows


def pps(sizes: pd.Series, n: int, rng) -> list:
    p = (sizes / sizes.sum()).to_numpy()
    return list(rng.choice(sizes.index.to_numpy(), size=min(n, len(sizes)), replace=False, p=p))


def weekly_tournaments(probe: S.Probe, day: str) -> list[dict]:
    """ITF singles tournaments (men's and women's) SofaScore lists on ``day``."""
    out, page = [], 1
    while page <= 6:
        doc = probe.get(f"{S.API}/sport/tennis/scheduled-tournaments/{day}/page/{page}",
                        f"scheduled_tournaments/{day}_{page}.json", f"scheduled_tournaments/{day}_{page}")
        if doc is None:
            break
        for t in doc.get("scheduled") or []:
            tt = t.get("tournament") or {}
            cat = (tt.get("category") or {}).get("name")
            if cat in ("ITF Men", "ITF Women") and "doubles" not in tt.get("name", "").lower():
                out.append({"category": cat, "name": tt.get("name"), "utid": (tt.get("uniqueTournament") or {}).get("id")})
        if not doc.get("hasNextPage"):
            break
        page += 1
    return out


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
    rng = np.random.default_rng(SEED)
    receipts = C.Receipts(S.SOURCE, root=S.RAW)
    client = None if args.offline else make_client(args)
    probe = S.Probe(client, receipts, args.offline)
    m = pd.read_parquet(MATCHES)
    m["w1"], m["w2"] = m["name1"].map(S.words), m["name2"].map(S.words)
    m["week"] = m["d"].dt.isocalendar().week
    m["edition"] = m["tname"].fillna("") + "|" + m["year"].astype(str) + "|w" + m["week"].astype(str)
    m["grade"] = m["tname"].map(grade)
    rows, checks, weekly, stopped = [], [], [], None
    try:
        # ---- women's qualifying, 2024 benchmark
        q24 = m[m["tour"].eq("W") & m["level"].eq("ITFQ") & m["year"].eq(2024)]
        for ed in pps(q24.groupby("edition").size(), 8, rng):
            em = q24[q24["edition"] == ed]
            d0 = em["d"].min()
            loc = locate_with(probe, "W", d0, [-1, 0, -2, 1], em)
            row = {"part": "wq_2024", "edition": ed, "grade": em["grade"].iloc[0], "sackmann_qual": len(em), **loc}
            if loc["utid"]:
                events, _ = probe.season_events(int(loc["utid"]), int(loc["sid"]))
                row.update(season_counts(events))
                singles = S.prep(events)
                linked = [S.best_event(a, b, d0, d0 + pd.Timedelta(days=7), singles) for a, b in zip(em["w1"], em["w2"])]
                row["sackmann_qual_linked"] = sum(e is not None for e in linked)
                qual = [e for e in singles if is_qual_round((e.get("roundInfo") or {}).get("name"))]
                checks += [{"part": "wq_2024", "edition": ed, **c} for c in check_events(probe, qual, 3, rng)]
            rows.append(row)
            P.log(f"wq_2024 {ed}: {row.get('ss_tournament')} qual {row.get('ss_qual')} linked {row.get('sackmann_qual_linked')}/{len(em)}")
        # ---- women's qualifying, 2025-26: editions located through their main draws
        for year, n in ((2025, 6), (2026, 4)):
            wm = m[m["tour"].eq("W") & m["level"].eq("ITF") & m["year"].eq(year)]
            for ed in pps(wm.groupby("edition").size(), n, rng):
                em = wm[wm["edition"] == ed]
                d0 = em["d"].min()
                loc = locate_with(probe, "W", d0, [2, 4, 1], em)
                row = {"part": f"wq_{year}", "edition": ed, "grade": em["grade"].iloc[0], "main_known": len(em), **loc}
                if loc["utid"]:
                    events, _ = probe.season_events(int(loc["utid"]), int(loc["sid"]))
                    row.update(season_counts(events))
                    qual = [e for e in S.prep(events) if is_qual_round((e.get("roundInfo") or {}).get("name"))]
                    checks += [{"part": f"wq_{year}", "edition": ed, **c} for c in check_events(probe, qual, 3, rng)]
                rows.append(row)
                P.log(f"wq_{year} {ed}: {row.get('ss_tournament')} main {row.get('ss_main')} qual {row.get('ss_qual')}")
        # ---- ITF after June 2026: weekly tournament counts, then editions
        pool = []
        for year in (2025, 2026):
            for week in range(27, 39):
                day = dt.date.fromisocalendar(year, week, 3).isoformat()
                if pd.Timestamp(day) > pd.Timestamp("2026-09-23"):
                    continue
                ts = weekly_tournaments(probe, day)
                c = Counter(t["category"] for t in ts)
                weekly.append({"year": year, "week": week, "wednesday": day, "itf_men": c.get("ITF Men", 0),
                               "itf_women": c.get("ITF Women", 0)})
                if year == 2026:
                    pool += [{**t, "week": week, "day": day} for t in ts]
        for cat, n in (("ITF Men", 6), ("ITF Women", 6)):
            cands = [t for t in pool if t["category"] == cat and t["utid"]]
            for i in rng.choice(len(cands), size=min(n, len(cands)), replace=False):
                t = cands[int(i)]
                se = probe.get(f"{S.API}/unique-tournament/{t['utid']}/seasons", f"seasons/{t['utid']}.json", f"seasons/{t['utid']}")
                seasons = (se or {}).get("seasons") or []
                row = {"part": "itf_after_june_2026", "edition": t["name"], "category": cat, "week": t["week"], "utid": t["utid"]}
                if seasons:
                    sid = seasons[0]["id"]
                    row["sid"] = sid
                    events, _ = probe.season_events(int(t["utid"]), int(sid))
                    row.update(season_counts(events))
                    main = [e for e in S.prep(events) if not is_qual_round((e.get("roundInfo") or {}).get("name"))
                            and (e.get("status") or {}).get("type") == "finished"]
                    checks += [{"part": "itf_after_june_2026", "edition": t["name"], **c} for c in check_events(probe, main, 3, rng)]
                rows.append(row)
                P.log(f"after June {t['name']}: main {row.get('ss_main_finished')}/{row.get('ss_main')} qual {row.get('ss_qual')}")
    except (P.Blocked, P.BudgetExhausted) as stop:
        stopped = f"{type(stop).__name__}: {stop}"
        P.log(f"STOPPED: {stopped}")
    eds, chk, wk = pd.DataFrame(rows), pd.DataFrame(checks), pd.DataFrame(weekly)
    eds.to_csv(OUT / "sofascore_itf_editions.csv", index=False)
    chk.to_csv(OUT / "sofascore_itf_checks.csv", index=False)
    wk.to_csv(OUT / "sofascore_itf_weekly.csv", index=False)
    summary = {"generated_at": P.utc_now_iso(), "stopped": stopped,
               "client": client.stats() if client else "offline", "benchmarks": benchmarks(m, wk)}
    if not eds.empty:
        for part, g in eds.groupby("part"):
            summary[part] = {c: (int(g[c].sum()) if c in g and g[c].notna().any() else None)
                             for c in ("sackmann_qual", "sackmann_qual_linked", "ss_main", "ss_main_finished", "ss_qual",
                                       "ss_qual_finished", "main_known")}
            summary[part]["editions"], summary[part]["located"] = int(len(g)), int(g["utid"].notna().sum())
    if not chk.empty:
        for part, g in chk.groupby("part"):
            summary[f"{part}_checks"] = {"n": int(len(g)),
                                         "pbp_200": int(pd.to_numeric(g["pbp_status"], errors="coerce").eq(200).sum()),
                                         "pbp_complete": int(g.get("pbp_verdict", pd.Series(dtype=str)).eq("complete").sum()),
                                         "full_box": int(g.get("stats_full_box", pd.Series(dtype=str)).astype(str).str.lower().eq("true").sum())}
    (OUT / "sofascore_itf_listings.json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1, default=str))
    return 1 if stopped else 0


def benchmarks(m: pd.DataFrame, wk: pd.DataFrame) -> dict:
    """2024 qualifying matches per edition by grade (Sackmann), and 2025 ITF editions per ISO week 27-38."""
    q = m[m["tour"].eq("W") & m["level"].eq("ITFQ") & m["year"].eq(2024)]
    per = q.groupby(["grade", "edition"]).size().groupby("grade").agg(["count", "mean"])
    out = {"w_itfq_2024_per_edition_by_grade": {str(k): {"editions": int(v["count"]), "mean_matches": round(float(v["mean"]), 1)}
                                              for k, v in per.iterrows()}}
    itf25 = m[m["level"].eq("ITF") & m["year"].eq(2025) & m["week"].between(27, 38)]
    ed = itf25.groupby(["tour", "week"])["edition"].nunique().unstack(0).fillna(0).astype(int)
    out["sackmann_itf_editions_2025_by_week"] = {int(w): {"M": int(r.get("M", 0)), "W": int(r.get("W", 0))} for w, r in ed.iterrows()}
    out["sackmann_itf_matches_2025_weeks_27_38"] = {t: int(n) for t, n in itf25.groupby("tour").size().items()}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-requests", type=int, default=700)
    parser.add_argument("--min-interval", type=float, default=1.2)
    parser.add_argument("--jitter", type=float, default=0.8)
    parser.add_argument("--browser", nargs="?", const="http://localhost:9222", metavar="CDP_URL",
                        help="make the requests inside a Chrome tab the owner opened (see src/ingest/point_sources/browser.py)")
    parser.add_argument("--offline", action="store_true")
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
