"""A probe of the ATP Stats Centre's host for Challenger point files (P6 data issues, 14 Oct 2026).

Question. The Hugging Face copy of the ATP's Infosys files holds 2022-23 Challenger matches with key statistics but
without rally analysis (2022: 2,506 of 8,483 Challenger records). Its crawler fetched those matches' other files, so
the host probably had no point file for them (an inference in docs/studies/p6_data_issues/README.md, section 2). Does
the host serve one now, on the rally-analysis route or on MatchBeats (every point, with the serve's speed)?

How. A few matches of each kind, chosen by a fixed seed from the copy: targets (key statistics, no rally analysis) and
controls (rally analysis held). Each asked on the two point routes with the infosys_atp adapter's own client,
calibration and receipts (src/ingest/point_sources/infosys_atp.py): its pacing (2 s plus up to 1 s), its stop on any
block, S3's 403 read as "no such object" only on a route that has served a file to the same headers, the envelope saved
as served (encrypted, gzipped) under data/raw/point_sources/infosys_atp/, nothing fetched twice. Nothing is decrypted.

Writes data/studies/p6_data_issues/infosys_probe/probe.csv (one row per request: the match, its kind, the route, the
answer) and summary.json.

Run: ./python.sh src/eda/p6_data_issues/infosys_probe.py [--per-year 3] [--controls 1] [--max-requests 20]
     ./python.sh src/eda/p6_data_issues/infosys_probe.py --years 2021,2022,2023,2024 --per-year 5 --controls 0 \
         --uncopied 3 --routes rally-analysis --max-requests 40       (the second probe: more matches, and events the
                                                                       copy lacks; probe.csv accumulates)
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import infosys_atp as I  # noqa: E402

COPY = ROOT / "data" / "raw" / "public_dump" / "atp_pipeline_handoff" / "infosys_full"
STAGE0 = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
OUT = ROOT / "data" / "studies" / "p6_data_issues" / "infosys_probe"
ROUTES = ["rally-analysis", "match-beats"]
SEED = 20261014


def challenger_records(year: int) -> pd.DataFrame:
    """The copy's records of Stage 0's Challenger events of ``year``: event, match code, and which files it holds."""
    s0 = pd.read_parquet(STAGE0, columns=["tournament_id", "level", "year"])
    ids = s0.loc[(s0["year"] == year) & (s0["level"] == "CH"), "tournament_id"].astype(str).str.split("-", n=1).str[1]
    ids = set(ids.str.lstrip("0"))
    rows = []
    with gzip.open(COPY / f"{year}_data.jsonl.gz", "rt", encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            if str(d.get("tournament_id")) in ids:
                rows.append({"year": year, "event": int(d["tournament_id"]), "mid": d["match_id"],
                             "date": d.get("match_date"), "keystats": d.get("keystats") is not None,
                             "rally": d.get("rally_analysis") is not None})
    return pd.DataFrame(rows)


def uncopied_events(year: int, n: int) -> pd.DataFrame:
    """``n`` Challenger events of ``year`` that Stage 0 holds and the copy does not (seeded): their final, MS001."""
    s0 = pd.read_parquet(STAGE0, columns=["tournament_id", "level", "year", "tournament_date"])
    ev = s0[(s0["year"] == year) & (s0["level"] == "CH")].drop_duplicates("tournament_id")
    ev = ev.assign(event=ev["tournament_id"].astype(str).str.split("-", n=1).str[1].str.lstrip("0"))
    ev = ev[ev["event"].str.fullmatch(r"\d+")]
    path = COPY / f"{year}_data.jsonl.gz"
    held = set()
    if path.exists():
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            held = {str(json.loads(line).get("tournament_id")) for line in fh}
    ev = ev[~ev["event"].isin(held)]
    ev = ev.sample(min(n, len(ev)), random_state=SEED) if len(ev) else ev
    return pd.DataFrame({"year": year, "event": ev["event"].astype(int).to_numpy(), "mid": "MS001",
                         "date": ev["tournament_date"].astype(str).to_numpy(), "keystats": False, "rally": False,
                         "kind": "event not in the copy"})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--years", default="2022,2023")
    ap.add_argument("--per-year", type=int, default=3, help="targets per year (key statistics, no rally analysis)")
    ap.add_argument("--controls", type=int, default=1, help="controls per year (rally analysis held)")
    ap.add_argument("--uncopied", type=int, default=0, help="per year: Challenger events the copy lacks, their final")
    ap.add_argument("--routes", default=",".join(ROUTES), help="the point routes asked for targets")
    ap.add_argument("--max-requests", type=int, default=20)
    ap.add_argument("--min-interval", type=float, default=2.0)
    ap.add_argument("--jitter", type=float, default=1.0)
    ap.add_argument("--timeout", type=float, default=30.0)
    a = ap.parse_args()
    a.refresh = False
    routes_asked = [r.strip() for r in a.routes.split(",")]

    picks = []
    for year in [int(y) for y in a.years.split(",")]:
        r = challenger_records(year) if (COPY / f"{year}_data.jsonl.gz").exists() else pd.DataFrame()
        if len(r):
            no_rally = r[r["keystats"] & ~r["rally"]]
            t = no_rally.sample(min(a.per_year, len(no_rally)), random_state=SEED).assign(kind="target")
            c = r[r["rally"]].sample(min(a.controls, int(r["rally"].sum())), random_state=SEED).assign(kind="control")
            picks.append(pd.concat([t, c]))
            print(f"{year}: {len(r)} Challenger records, {len(no_rally)} without rally analysis", flush=True)
        else:
            print(f"{year}: the copy has no file", flush=True)
        if a.uncopied:
            u = uncopied_events(year, a.uncopied)
            print(f"{year}: {len(u)} Challenger events not in the copy asked", flush=True)
            picks.append(u)
    picks = pd.concat(picks, ignore_index=True)

    receipts = P.receipts_for(I.SOURCE)
    cal = I.Calibration(receipts)
    missing = [r for r in ROUTES if r not in cal.ok]
    if missing:
        raise SystemExit(f"routes not calibrated in the receipts: {missing}; run the adapter's calibration first")
    client = I.make_client(a, cal)
    outcomes: Counter = Counter()
    rows = []
    try:
        for p in picks.itertuples():
            routes = routes_asked if p.kind == "target" else ["rally-analysis"]
            for route in routes:
                rec = I.fetch_one(client, receipts, cal, p.year, p.event, route, p.mid, a, outcomes,
                                  purpose="p6_data_issues probe")
                rows.append({"year": p.year, "event": p.event, "mid": p.mid, "date": p.date, "kind": p.kind,
                             "route": route, "answer": I.outcome_of(rec), "served": I.served(rec),
                             "absent": I.is_absent(rec)})
                print(f"{p.year}/{p.event}/{p.mid} {p.kind} {route}: {I.outcome_of(rec)}", flush=True)
    except P.Blocked as exc:
        print(f"stopped: {exc}", flush=True)
        rows.append({"kind": "stopped", "answer": str(exc)})
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    if (OUT / "probe.csv").exists():                 # earlier probes kept: the file accumulates, one row per request
        df = pd.concat([pd.read_csv(OUT / "probe.csv"), df], ignore_index=True)
    df.to_csv(OUT / "probe.csv", index=False)
    summary = {"requests": client.requests, "by_kind_route_answer":
               {f"{k}|{r}|{ans}": int(n) for (k, r, ans), n in df.groupby(["kind", "route", "answer"]).size().items()}
               if "route" in df else {}}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
