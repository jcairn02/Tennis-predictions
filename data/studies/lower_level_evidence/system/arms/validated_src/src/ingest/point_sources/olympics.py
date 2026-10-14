"""The Paris 2024 Olympic tennis results files (singles): official per-match statistics and play-by-play.

olympics.com published one results document per match ("event unit") during the Games,
    https://olympics.com/OG2024/data/RES_ByRSC_H2H~comp=OG2024~disc=TEN~rscResult=<unit>~lang=<LANG>.json
with the status ("OFFICIAL"), the set scores, each player's statistics per set and in total (statsItems: 1ST_SERVE
in/served with points won and aces, 2ND_SERVE, ACES, DBL_FAULT, BREAK_PTS, RECEIVE, PTS_WON_SERVE, ...) and a
play-by-play block. The site no longer serves them (www.olympics.com answered 404 on 9 Oct 2026), so they are taken
from the Wayback Machine's captures: for each singles unit, the latest capture answered 200, English first, then any
other language (the numbers do not depend on the language), fetched verbatim with the "id_" flag.

Collected under the owner's decision of 8 Oct 2026 (docs/decisions/2026-10-08-scraping-approved.md) for the
Roland-Garros first-serve recount (docs/studies/rg_first_serve_recount/): the Olympics of 2024 were played at Roland
Garros and carry the same first-serve fault in Sackmann's rows. About 2 s between requests plus jitter, a budget,
every answer kept with a receipt and nothing fetched twice, a stop on any block (feeds.FeedClient).

Raw:    data/raw/point_sources/olympics/OG2024/cdx_<event>.txt (the capture lists) and
        data/raw/point_sources/olympics/OG2024/RES_ByRSC_H2H/<unit>.json.gz, plus _receipts.jsonl
Staged: data/dump/points/olympics/units.parquet  one row per unit: capture, status, phase, players, set scores
        data/dump/points/olympics/stats.parquet  one row per player, statistic and period (TOT = the match)
        data/dump/points/olympics/pbp.parquet    one row per play-by-play action, fields verbatim
Summary: data/studies/rg_first_serve_recount/collection/olympics_summary.json (and runs.jsonl).

Usage:
    ./python.sh -m src.ingest.point_sources.olympics                # list, fetch, stage
    ./python.sh -m src.ingest.point_sources.olympics --stage-only
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P
from src.ingest.point_sources import feeds as F

SOURCE = "olympics"
DECISION = "docs/decisions/2026-10-08-scraping-approved.md"
STUDY_ROOT = P.PROJECT_ROOT / "data" / "studies" / "rg_first_serve_recount" / "collection"
GAMES = "OG2024"
EVENTS = ("TENMSINGLES", "TENWSINGLES")
PREFIX = "olympics.com/OG2024/data/RES_ByRSC_H2H~comp=OG2024~disc=TEN~rscResult={event}"
CDX = "https://web.archive.org/cdx/search/cdx?url={prefix}&matchType=prefix&fl=timestamp,original,statuscode,length"
CAPTURE = "https://web.archive.org/web/{ts}id_/{url}"
LANG_ORDER = ("ENG", "FRA", "SPA", "DEU", "JPN", "CHI")
STAT_COLUMNS = ["unit", "athlete_code", "athlete_name", "side", "code", "pos", "value", "attempt", "percent",
                "extended"]
UNIT_COLUMNS = ["event", "unit", "phase", "description", "lang", "capture", "status", "date", "court", "home_code",
                "home_name", "home_wlt", "away_code", "away_name", "away_wlt", "periods", "source_file",
                "source_sha256", "retrieved_at"]
PBP_COLUMNS = ["unit", "period", "pbpa_id", "pbpa_order", "action", "action_desc", "result", "score_h", "score_a",
               "speed", "server", "extended", "competitors", "other"]


def unit_of(url: str) -> str:
    return url.split("rscResult=", 1)[1].split("~", 1)[0]


def lang_of(url: str) -> str:
    return url.split("~lang=", 1)[1].split(".", 1)[0] if "~lang=" in url else ""


def pick_captures(cdx_lines: list[str]) -> dict[str, tuple[str, str]]:
    """unit -> (timestamp, original url): the latest 200 capture in the first language of LANG_ORDER that has one."""
    by_unit: dict[str, dict[str, list[tuple[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for line in cdx_lines:
        parts = line.split()
        if len(parts) < 3 or parts[2] != "200":
            continue
        ts, url = parts[0], parts[1]
        by_unit[unit_of(url)][lang_of(url)].append((ts, url))
    out = {}
    for unit, langs in by_unit.items():
        for lang in LANG_ORDER + tuple(sorted(set(langs) - set(LANG_ORDER))):
            if langs.get(lang):
                out[unit] = max(langs[lang])
                break
    return out


def dest_of(unit: str) -> Path:
    return P.raw_path(SOURCE, GAMES, "RES_ByRSC_H2H", f"{unit}.json.gz")


# --------------------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------------------
def s(value) -> str | None:
    return P.s(value)


def stage(receipts) -> dict:
    units, stats, pbp = [], [], []
    for name, rec in sorted(receipts.all().items()):
        if not name.startswith("unit/") or rec.get("status") != 200 or rec.get("error"):
            continue
        unit = name.split("/", 1)[1]
        path = dest_of(unit)
        if not path.exists():
            continue
        res = (P.read_json(path) or {}).get("results") or {}
        items = sorted(res.get("items") or [], key=lambda it: it.get("sortOrder") or 0)
        sides = {}
        for side, it in zip(("home", "away"), items):
            part = it.get("participant") or {}
            sides[side] = (s(part.get("code") or it.get("athleteCode")), s(part.get("name")), s(it.get("resultWLT")))
            for st in it.get("statsItems") or []:
                stats.append([unit, s(part.get("code") or it.get("athleteCode")), s(part.get("name")), side,
                              s(st.get("code")), s(st.get("pos")), s(st.get("value")), s(st.get("attempt")),
                              s(st.get("percent")), json.dumps(st.get("extendedStatsItems") or [], ensure_ascii=False)])
        periods = [{"p": p.get("p_code"), "home": (p.get("home") or {}).get("score"),
                    "away": (p.get("away") or {}).get("score"),
                    "ext": p.get("extendedPeriods")} for p in res.get("periods") or []]
        sched = res.get("schedule") or {}
        units.append([unit.split("-", 1)[0], unit, ((res.get("eventUnit") or {}).get("phase") or {}).get("order"),
                      s((res.get("eventUnit") or {}).get("description")), rec.get("lang"), rec.get("capture"),
                      s((res.get("status") or {}).get("code")), s(res.get("date")),
                      s((sched.get("location") or {}).get("shortDescription"))]
                     + list(sides.get("home", (None,) * 3)) + list(sides.get("away", (None,) * 3))
                     + [json.dumps(periods, ensure_ascii=False), P.rel(path), rec.get("sha256"), rec.get("retrieved_at")])
        for blk in res.get("playByPlay") or []:
            for a in blk.get("actions") or []:
                ext = {e.get("pbpea_code"): e.get("pbpea_value") for e in a.get("extendedActions") or []}
                known = {"pbpa_period", "pbpa_id", "pbpa_order", "pbpa_Action", "pbpa_ActionDesc", "pbpa_Result",
                         "pbpa_ScoreH", "pbpa_ScoreA", "pbpa_Speed", "extendedActions", "competitors"}
                pbp.append([unit, s(a.get("pbpa_period")), s(a.get("pbpa_id")), s(a.get("pbpa_order")),
                            s(a.get("pbpa_Action")), s(a.get("pbpa_ActionDesc")), s(a.get("pbpa_Result")),
                            s(a.get("pbpa_ScoreH")), s(a.get("pbpa_ScoreA")), s(a.get("pbpa_Speed")),
                            s(ext.get("SERVER")), json.dumps(a.get("extendedActions") or [], ensure_ascii=False),
                            json.dumps(a.get("competitors") or [], ensure_ascii=False),
                            json.dumps({k: v for k, v in a.items() if k not in known}, ensure_ascii=False)])
    retrieved = max((u[-1] or "" for u in units), default=None)
    out = {}
    for file, header, rows in (("units.parquet", UNIT_COLUMNS, units), ("stats.parquet", STAT_COLUMNS, stats),
                               ("pbp.parquet", PBP_COLUMNS, pbp)):
        st_ = P.stage_table(SOURCE, P.dump_path(SOURCE, file), header, rows, source_file=P.rel(P.raw_path(SOURCE)),
                            retrieved_at=retrieved, extra={"decision": DECISION, "via": "Wayback Machine captures"})
        out[file] = {"rows": st_["rows"], "bytes": st_["bytes"]}
        P.log(f"[{SOURCE}] staged {file}: {st_['rows']:,} rows")
    return out


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def run(args) -> dict:
    P.configure_stdout()
    started = time.time()
    receipts = P.receipts_for(SOURCE)
    summary = {"source": SOURCE, "started_at": P.utc_now_iso(), "args": vars(args), "decision": DECISION}
    outcomes = Counter()
    if not args.stage_only:
        client = F.FeedClient("chrome", min_interval=args.min_interval, jitter=args.jitter,
                              max_requests=args.max_requests)
        try:
            chosen = {}
            for event in EVENTS:
                cdx_path = P.raw_path(SOURCE, GAMES, f"cdx_{event}.txt")
                rec = P.fetch(client, CDX.format(prefix=PREFIX.format(event=event)), cdx_path, receipts,
                              name=f"cdx/{event}", refresh=True, extra={"event": event})
                outcomes[f"cdx:{rec.get('status')}"] += 1
                if rec.get("status") != 200 or rec.get("error"):
                    raise P.Blocked(f"capture list for {event}: {rec.get('error') or rec.get('status')}")
                picks = pick_captures(P.read_bytes(cdx_path).decode("utf-8").splitlines())
                summary[f"units_{event}"] = len(picks)
                chosen.update(picks)
            for unit, (ts, url) in sorted(chosen.items()):
                rec = P.fetch(client, CAPTURE.format(ts=ts, url=url), dest_of(unit), receipts, name=f"unit/{unit}",
                              refresh=args.refresh, validator=P.json_validator, compress=True,
                              extra={"unit": unit, "capture": ts, "original": url, "lang": lang_of(url)})
                outcomes[f"unit:{rec.get('status')}{':cached' if rec.get('skipped') else ''}"] += 1
        except (P.Blocked, P.BudgetExhausted) as stop:
            summary["stopped"] = f"{type(stop).__name__}: {stop}"
            P.log(f"[{SOURCE}] STOPPED: {stop}")
        summary["client"] = client.stats()
    summary["fetch_outcomes"] = dict(sorted(outcomes.items()))
    if not args.no_stage:
        summary["staged"] = stage(receipts)
    errors = [r for r in receipts.all().values() if r.get("error")]
    summary["receipts_with_errors"] = len(errors)
    summary["error_examples"] = [{"name": r["name"], "error": r["error"]} for r in errors[:20]]
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - started, 1)
    path = P.write_summary("olympics_summary.json", summary, root=STUDY_ROOT)
    P.log(f"[{SOURCE}] summary written to {P.rel(path)}")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-requests", type=int, default=200)
    parser.add_argument("--min-interval", type=float, default=2.0)
    parser.add_argument("--jitter", type=float, default=1.0)
    parser.add_argument("--refresh", action="store_true", help="fetch the units' captures again")
    parser.add_argument("--stage-only", action="store_true")
    parser.add_argument("--no-stage", action="store_true")
    summary = run(parser.parse_args())
    P.log(f"[{SOURCE}] done in {summary['seconds']} s" + (f"; stopped: {summary['stopped']}" if summary.get("stopped") else ""))
    return 1 if summary.get("stopped") or summary["receipts_with_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
