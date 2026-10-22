"""The ATP Stats Centre's point files for the Challenger matches SofaScore lacks (P6 data issues, 14 Oct 2026).

Why. P6 found SofaScore almost without Challenger point records from spring 2022 to the end of 2023
(docs/studies/p6_data_issues/README.md, section 2). The Hugging Face copy of the ATP's Infosys files holds most
2021-24 Challenger matches, about 30% of them without rally analysis, and a probe of 14 Oct 2026
(src/eda/p6_data_issues/infosys_probe.py) found the ATP's host serving the point files of every such match it asked
for (20 of 20 rally analysis, 6 of 6 MatchBeats): the host has them now, the copy does not.

What. The plan is P6's targets without a SofaScore point record that the copy holds without rally analysis (linked by
the two surnames within 7 days: src/eda/p6_data_issues/checks/infosys_targets.py's rule), each asked on MatchBeats
(every point, with the serve's speed) and then on rally analysis. --all-copy widens it to every 2021-24 Challenger
record of the copy without rally analysis. Collection is approved (docs/decisions/2026-10-08-scraping-approved.md);
decryption of these files too (its "Backfill decryption authorized subsequently"), done afterwards by
infosys_atp_decrypt, not here.

How. The infosys_atp adapter's own client, calibration and receipts (src/ingest/point_sources/infosys_atp.py): about
2 s between requests plus up to 1 s, a --max-requests budget, nothing fetched twice, S3's 403 read as "no such object"
only on a calibrated route, a stop on any block. Envelopes are saved as served (encrypted, gzipped) under
data/raw/point_sources/infosys_atp/<year>/<event>/<route>/<MID>.json.gz, the receipts' purpose "p6 challengers"
(the map's reader of the staged files keeps purpose "plan" only, so nothing here reaches it by itself).
--stop-at HH:MM (local time) ends the run before the host is needed by the daily speeds job at 12:00 (one collector
per host).

Writes data/studies/p6_data_issues/infosys_challengers/: plan.csv (the codes, why each is planned) and
summary.json (requests, answers by route).

Run: ./python.sh -m src.ingest.point_sources.infosys_challengers --stop-at 11:40 --max-requests 5000
     ./python.sh -m src.ingest.point_sources.infosys_challengers --plan-only
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P
from src.ingest.point_sources import feeds as F
from src.ingest.point_sources import infosys_atp as I

COPY = P.PROJECT_ROOT / "data" / "raw" / "public_dump" / "atp_pipeline_handoff" / "infosys_full"
TARGETS = P.PROJECT_ROOT / "data" / "studies" / "p6_data_issues" / "flashscore" / "targets.csv.gz"
STAGE0 = P.PROJECT_ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
OUT = P.PROJECT_ROOT / "data" / "studies" / "p6_data_issues" / "infosys_challengers"
YEARS = (2021, 2022, 2023, 2024)
ROUTES = ("match-beats", "rally-analysis")
PURPOSE = "p6 challengers"
LINK_DAYS = 7


def surname(name) -> str:
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode().lower()
    w = [x for x in s.replace("-", " ").replace(".", " ").split() if len(x) > 1]
    return w[-1] if w else ""


def copy_records() -> pd.DataFrame:
    """The copy's records of Stage 0's Challenger events of YEARS: event, code, date, players, files held."""
    s0 = pd.read_parquet(STAGE0, columns=["tournament_id", "level", "year"])
    ch = s0[s0["level"].eq("CH") & s0["year"].isin(YEARS)].drop_duplicates("tournament_id")
    ids = {(int(y), t.split("-", 1)[1].lstrip("0")) for y, t in zip(ch["year"], ch["tournament_id"].astype(str))}
    rows = []
    for year in YEARS:
        with gzip.open(COPY / f"{year}_data.jsonl.gz", "rt", encoding="utf-8") as fh:
            for line in fh:
                d = json.loads(line)
                if (year, str(d.get("tournament_id"))) in ids:
                    rows.append({"year": year, "event": int(d["tournament_id"]), "mid": d["match_id"],
                                 "date": d.get("match_date"), "p1": d.get("player1_name"), "p2": d.get("player2_name"),
                                 "rally": d.get("rally_analysis") is not None})
    r = pd.DataFrame(rows)
    r["date"] = pd.to_datetime(r["date"], errors="coerce")
    r["pair"] = ["|".join(sorted([surname(a), surname(b)])) for a, b in zip(r["p1"], r["p2"])]
    return r


def build_plan(all_copy: bool) -> pd.DataFrame:
    r = copy_records()
    r = r[~r["rally"]].copy()
    t = pd.read_csv(TARGETS, low_memory=False, usecols=["gap", "uid", "tour", "d", "name1", "name2"])
    t = t[t["tour"].eq("M")].copy()
    t["d"] = pd.to_datetime(t["d"])
    t["pair"] = ["|".join(sorted([surname(a), surname(b)])) for a, b in zip(t["name1"], t["name2"])]
    m = r.reset_index().merge(t, on="pair")
    m["days"] = (m["date"] - m["d"]).abs().dt.days
    m = m[m["days"].le(LINK_DAYS)].sort_values(["days", "uid"]).drop_duplicates("index")   # the nearest target
    r["p6_gap"] = r.index.map(m.set_index("index")["gap"])
    r["p6_uid"] = r.index.map(m.set_index("index")["uid"])
    if not all_copy:
        r = r[r["p6_gap"].notna()]
    r["why"] = r["p6_gap"].map(lambda g: f"P6 target without SofaScore points ({g})" if isinstance(g, str)
                               else "a copy record without rally analysis")
    return r.sort_values(["p6_gap", "year", "event", "mid"], na_position="last").reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--all-copy", action="store_true", help="every 2021-24 copy record without rally analysis")
    ap.add_argument("--plan-only", action="store_true", help="write the plan and stop (no HTTP)")
    ap.add_argument("--routes", default=",".join(ROUTES))
    ap.add_argument("--stop-at", default=None, help="local HH:MM after which no request starts")
    ap.add_argument("--max-requests", type=int, default=5000)
    ap.add_argument("--min-interval", type=float, default=2.0)
    ap.add_argument("--jitter", type=float, default=1.0)
    ap.add_argument("--timeout", type=float, default=30.0)
    a = ap.parse_args()
    a.refresh = False
    routes = [x.strip() for x in a.routes.split(",")]

    plan = build_plan(a.all_copy)
    OUT.mkdir(parents=True, exist_ok=True)
    plan.drop(columns=["rally"]).to_csv(OUT / "plan.csv", index=False)
    print(f"plan: {len(plan)} codes ({plan['why'].value_counts().to_dict()})", flush=True)
    if a.plan_only:
        return 0
    stop = None
    if a.stop_at:
        hh, mm = (int(x) for x in a.stop_at.split(":"))
        stop = dt.datetime.now().replace(hour=hh, minute=mm, second=0, microsecond=0)

    receipts = P.receipts_for(I.SOURCE)
    cal = I.Calibration(receipts)
    if [r for r in routes if r not in cal.ok]:
        raise SystemExit(f"routes not calibrated in the receipts: {[r for r in routes if r not in cal.ok]}")
    client = I.make_client(a, cal)
    streak = F.FailureStreak(limit=25)      # 25 answers in a row without a file: the host changed; stop and report
    outcomes: Counter = Counter()
    why_stopped = "plan done"
    try:
        for p in plan.itertuples():
            if stop and dt.datetime.now() >= stop:
                why_stopped = f"--stop-at {a.stop_at}"
                break
            for route in routes:
                rec = I.fetch_one(client, receipts, cal, int(p.year), int(p.event), route, p.mid, a, outcomes,
                                  purpose=PURPOSE)
                streak.note(rec)
            if p.Index % 100 == 0:
                print(f"[{dt.datetime.now():%H:%M:%S}] {p.Index + 1}/{len(plan)} codes; requests={client.requests}; "
                      f"{dict(outcomes.most_common(6))}", flush=True)
    except (P.Blocked, F.Stopped) as exc:
        why_stopped = f"stopped: {exc}"
        print(why_stopped, flush=True)
    except P.BudgetExhausted as exc:
        why_stopped = f"budget: {exc}"
    summary = {"finished_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "why_stopped": why_stopped,
               "plan_codes": int(len(plan)), "requests": client.requests,
               "answers": {k: int(v) for k, v in sorted(outcomes.items())}}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
