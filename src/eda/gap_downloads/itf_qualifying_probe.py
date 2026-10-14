"""ITF qualifying on SofaScore (work package P7, step 1): do the qualifying events of the trials' editions carry point
records? The plan adds a separate ITF qualifying gap only if most of them do.

For each edition the trials located (data/studies/gap_downloads/sofascore_<gap>_editions.csv of the two ITF gaps, the
editions with a season), the season listing already on disk (no HTTP) gives its singles events. The played qualifying
ones (the adapter's is_qualifying and is_played; walkovers left out) are sampled, at most --per-edition of them
(seeded), and their /point-by-point is asked for through the adapter's own client and cache: receipts, nothing asked
twice, the plan's pace, a --max-requests budget, a stop on a block. Each record is judged as the adapter judges a
target's (pbp_verdict). Beside them: the trials' main-draw targets of the same editions (their per-match tables), and
how many qualifying matches of the same tournament and week the map holds (level ITFQ).

Writes data/studies/gap_downloads/itf_qualifying_probe.json (counts by edition and overall) and
itf_qualifying_probe.csv (one row per sampled event).

Usage: ./python.sh src/eda/gap_downloads/itf_qualifying_probe.py --browser [--editions KEY ...] [--per-edition 30]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P                   # noqa: E402
from src.ingest.point_sources import sofascore as S                # noqa: E402
from src.ingest.point_sources import sofascore_editions as E       # noqa: E402

GAPS = ("itf_points_2025_2026", "itf_detail")
COMPLETE = ("complete", "complete to retirement")
PART = "point-by-point"


def qualifying_events(events: list[dict]) -> list[dict]:
    """The played singles qualifying events of a season listing; walkovers have no record to ask for."""
    return [e for e in E.singles(events) if E.is_qualifying(e) and E.is_played(e)
            and S._dig(e, ("status", "description")) != "Walkover"]


def sample(events: list[dict], n: int, seed: int) -> list[dict]:
    """At most ``n`` events: all of them, or a seeded random sample; ordered by event id either way."""
    events = sorted(events, key=lambda e: e["id"])
    return events if len(events) <= n else sorted(random.Random(seed).sample(events, n), key=lambda e: e["id"])


def located_editions(keys=None) -> pd.DataFrame:
    """The ITF gaps' editions with a located season (only ``keys``, when given)."""
    frames = [pd.read_csv(p) for gap in GAPS if (p := E.STUDY / f"sofascore_{gap}_editions.csv").exists()]
    eds = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=E.EDITION_COLUMNS)
    eds = eds[eds["utid"].notna()]
    if keys:
        eds = eds[eds["edition"].isin(keys)]
    return eds.assign(utid=eds["utid"].astype(int), sid=eds["sid"].astype(int)).reset_index(drop=True)


def main_draw(eds: pd.DataFrame) -> dict:
    """The trials' main-draw targets of these editions: linked, with a point record, complete."""
    out = {}
    for gap, g in eds.groupby("gap"):
        t = pd.read_csv(E.targets_path(gap), usecols=["edition", "listed", "pbp_status", "pbp_verdict"], dtype=str)
        t = t[t["edition"].isin(set(g["edition"]))]
        for edition, te in t.groupby("edition"):
            out[edition] = {"targets": int(len(te)), "linked": int(te["listed"].eq("True").sum()),
                            "points": int(pd.to_numeric(te["pbp_status"], errors="coerce").eq(200).sum()),
                            "complete": int(te["pbp_verdict"].isin(COMPLETE).sum())}
    return out


def map_qualifying(eds: pd.DataFrame) -> dict:
    """The map's qualifying matches (ITFQ) of each edition's tournament within a week of its dates, and how many are
    below point."""
    m = pd.read_parquet(E.MATCHES, columns=["tour", "level", "tname", "year", "d", "best"])
    m = m[m["level"].eq("ITFQ")]
    out = {}
    for r in eds.itertuples(index=False):
        d0, d1 = pd.Timestamp(r.d_min), pd.Timestamp(r.d_max)
        q = m[m["tour"].eq(r.tour) & m["tname"].eq(r.tname)
              & m["d"].between(d0 - pd.Timedelta(days=7), d1 + pd.Timedelta(days=7))]
        out[r.edition] = {"map_qualifying": int(len(q)),
                          "map_qualifying_below_point": int((q["best"].map(E.GRAIN_RANK) < E.GRAIN_RANK["point"]).sum())}
    return out


def run(args) -> dict:
    P.configure_stdout()
    eds = located_editions(args.editions)
    if eds.empty:
        raise SystemExit("no located ITF edition to probe: run the trials first")
    receipts = P.receipts_for(E.SOURCE)
    offline = E.Lister(None, receipts, offline=True)
    chosen = []
    for i, r in enumerate(eds.itertuples(index=False)):
        events, _ = offline.season_events(r.utid, r.sid)
        qual = qualifying_events(events)
        picked = sample(qual, args.per_edition, args.seed + i)
        chosen += [(r, len(qual), e) for e in picked]
        P.log(f"[itf_qualifying] {r.edition}: season {r.utid}/{r.sid}, {len(qual)} played qualifying singles, "
              f"{len(picked)} sampled")
    summary = {"generated_at": P.utc_now_iso(), "args": {k: v for k, v in vars(args).items()},
               "editions": eds["edition"].tolist()}
    client = E.make_client(args)
    lister = E.Lister(client, receipts, offline=False)
    rows = []
    try:
        for r, n_qual, e in chosen:
            lister.event_part(e["id"], PART)
            status = lister.status(f"events/{e['id']}/{PART}")
            row = {"gap": r.gap, "edition": r.edition, "event_id": e["id"], "ss_tournament": S._dig(e, ("tournament", "name")),
                   "ss_round": S._dig(e, ("roundInfo", "name")), "ss_home": S._dig(e, ("homeTeam", "name")),
                   "ss_away": S._dig(e, ("awayTeam", "name")),
                   "ss_start_utc": dt.datetime.fromtimestamp(e["startTimestamp"], dt.timezone.utc).strftime("%Y-%m-%d %H:%M"),
                   "pbp_status": status, "pbp_verdict": None, "pbp_points": None}
            path = P.raw_path(E.SOURCE, "events", str(e["id"]), f"{PART}.json.gz")
            if status == 200 and path.exists():
                v = E.pbp_verdict(P.read_json(path).get("pointByPoint") or [], e)
                row.update(pbp_verdict=v["pbp_verdict"], pbp_points=v["pbp_points"])
            rows.append(row)
    except (P.Blocked, P.BudgetExhausted) as stop:
        summary["stopped"] = f"{type(stop).__name__}: {stop}"
        P.log(f"[itf_qualifying] STOPPED: {stop}")
    finally:
        if hasattr(client, "close"):
            client.close()
    summary["client"] = client.stats()
    frame = pd.DataFrame(rows, columns=["gap", "edition", "event_id", "ss_tournament", "ss_round", "ss_home", "ss_away",
                                        "ss_start_utc", "pbp_status", "pbp_verdict", "pbp_points"])

    def cell(f: pd.DataFrame) -> dict:
        status = pd.to_numeric(f["pbp_status"], errors="coerce")
        return {"sampled": int(len(f)), "points": int(status.eq(200).sum()),
                "complete": int(f["pbp_verdict"].isin(COMPLETE).sum()), "absent": int(status.eq(404).sum())}

    played = {r.edition: n for r, n, _ in chosen}
    mains, maps = main_draw(eds), map_qualifying(eds)
    summary["by_edition"] = {ed: {"qualifying_played": played.get(ed, 0), **cell(frame[frame["edition"].eq(ed)]),
                                  "main_draw": mains.get(ed), **maps.get(ed, {})} for ed in eds["edition"]}
    summary["qualifying"] = cell(frame)
    summary["by_round"] = {str(k): cell(g) for k, g in frame.groupby(frame["ss_round"].fillna("none"))}
    main_all = [v for v in mains.values()]
    summary["main_draw"] = {k: sum(v[k] for v in main_all) for k in ("targets", "linked", "points", "complete")}
    q = summary["qualifying"]
    summary["most_carry_points"] = bool(q["sampled"] and q["points"] * 2 > q["sampled"])
    frame.to_csv(E.STUDY / "itf_qualifying_probe.csv", index=False)
    (E.STUDY / "itf_qualifying_probe.json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    P.log(f"[itf_qualifying] qualifying {json.dumps(q)}; main draw {json.dumps(summary['main_draw'])}")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--editions", nargs="+", metavar="KEY", help="only these editions (keys as in the editions tables)")
    parser.add_argument("--per-edition", type=int, default=30, help="qualifying events sampled per edition (default 30)")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-requests", type=int, default=250)
    parser.add_argument("--min-interval", type=float, default=2.0)
    parser.add_argument("--jitter", type=float, default=1.0)
    parser.add_argument("--browser", nargs="?", const="http://localhost:9222", metavar="CDP_URL",
                        help="make the requests inside the Chrome tab (bare flag: http://localhost:9222)")
    summary = run(parser.parse_args())
    return 1 if summary.get("stopped") else 0


if __name__ == "__main__":
    sys.exit(main())
