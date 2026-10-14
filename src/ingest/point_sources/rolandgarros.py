"""Roland-Garros's own match statistics, from rolandgarros.com's plain match API: singles, main draw and qualifying.

The site's match page (https://www.rolandgarros.com/en-us/matches/<year>/<MID>) is rendered from
https://www.rolandgarros.com/api/en-us/matches/<MID>?event=<year>, a plain (unencrypted) JSON document per match:
    match.matchData            draw, round, court, duration, schedule day, end time, status
    match.teamA / teamB        players (RG ids, names, country), set scores with tie-breaks, winner, end cause
    matchStatisticsSection     RG's statistics for the match (matchStatistics) and each set (setStatistics1-5):
                               aces, double faults, first serve "in/served (%)", win on 1st and 2nd serve
                               "won/played (%)", net points, break points won, receiving points won, winners,
                               unforced errors, total points won; serviceStatistics (speeds, mph)
The route was found by the serve-speed research (data/studies/serve_speed_sources/research_notes/A2_slams_and_espn.md,
section 2.2), which read only the speeds. A code the site does not hold is answered HTTP 200 with "match": null and
recorded as absent.

Collected under the owner's decision of 8 Oct 2026 (docs/decisions/2026-10-08-scraping-approved.md) for the Roland-
Garros first-serve recount (docs/studies/rg_first_serve_recount/). Practice as for the official feeds: about 2 s
between requests plus jitter, a --max-requests budget, every answer kept with a receipt and nothing fetched twice, and
a stop and report on any block (feeds.FeedClient: HTTP 403 or 429, a challenge page, a redirect, a reset).

Matches (as infosys_slams): SM/SD 001-127 (001 the final ... 064-127 the first round); QM/QD 016-127 (016-031 the
last qualifying round). A family whose first --skip-family-after codes are all absent is given up for that year.

Raw:    data/raw/point_sources/rolandgarros/matches/<year>/<MID>.json.gz, each document as served (gzipped), and
        _receipts.jsonl.
Staged: data/dump/points/rolandgarros/matches.parquet     one row per code asked: answer, draw, round, court,
                                                            players, set scores, winner, end cause
        data/dump/points/rolandgarros/statistics.parquet  one row per statistic per set ("match" = the whole match)
        Every held year is staged, whichever years a run fetched.
Summary: data/studies/rg_first_serve_recount/collection/rolandgarros_summary.json (and runs.jsonl), or --summary-dir.

Usage:
    ./python.sh -m src.ingest.point_sources.rolandgarros                        # 2019-2026, every family
    ./python.sh -m src.ingest.point_sources.rolandgarros --years 2024 --families QM --max-requests 20
    ./python.sh -m src.ingest.point_sources.rolandgarros --stage-only           # rebuild the tables from raw
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P
from src.ingest.point_sources import feeds as F

SOURCE = "rolandgarros"
DECISION = "docs/decisions/2026-10-08-scraping-approved.md"
STUDY_ROOT = P.PROJECT_ROOT / "data" / "studies" / "rg_first_serve_recount" / "collection"
API = "https://www.rolandgarros.com/api/en-us/matches/{mid}?event={year}"
PAGE = "https://www.rolandgarros.com/en-us/matches/{year}/{mid}"
YEARS = tuple(range(2019, 2027))
FAMILIES = ("SM", "SD", "QM", "QD")
RG_MAIN = ((1, 1, "F"), (2, 2, "SF"), (4, 4, "QF"), (8, 8, "R16"), (16, 16, "R32"), (32, 32, "R64"), (64, 64, "R128"))
RG_QUAL = ((16, 16, "Q3"), (32, 32, "Q2"), (64, 64, "Q1"))
NULL_MATCH = re.compile(rb'"match"\s*:\s*null')
STAT_SETS = ("matchStatistics",) + tuple(f"setStatistics{i}" for i in range(1, 6))
MATCH_COLUMNS = [
    "year", "match_id", "family", "tour", "draw", "round_from_code", "answer", "type", "type_label", "round_label",
    "court_name", "duration_minutes", "date_schedule", "end_timestamp", "status", "status_label",
    "a_ids", "a_names", "a_countries", "b_ids", "b_names", "b_countries", "a_sets", "b_sets", "a_winner", "b_winner",
    "a_end_cause", "b_end_cause", "has_statistics", "source_file", "source_sha256", "retrieved_at"]
STAT_COLUMNS = ["year", "match_id", "set_key", "stat", "label", "team_a", "team_b"]


def match_codes(family: str) -> list[tuple[str, str]]:
    """(match id, round) for every match of a family, the final round first."""
    rounds = RG_QUAL if family[0] == "Q" else RG_MAIN
    return [(f"{family}{n:03d}", rnd) for first, k, rnd in rounds for n in range(first, first + k)]


def round_lookup() -> dict[str, str]:
    return {mid: rnd for fam in FAMILIES for mid, rnd in match_codes(fam)}


def url_of(year: int, mid: str) -> str:
    return API.format(mid=mid, year=year)


def dest_of(year: int, mid: str) -> Path:
    return P.raw_path(SOURCE, "matches", str(year), f"{mid}.json.gz")


def receipt_name(year: int, mid: str) -> str:
    return f"matches/{year}/{mid}"


def headers_for(year: int, mid: str) -> dict:
    """What the site's own match page sends with its request."""
    return {"Referer": PAGE.format(year=year, mid=mid), "Accept": "application/json, text/plain, */*"}


def null_match(response) -> str | None:
    """The site's "no such match": HTTP 200 with "match": null."""
    if response.status_code == 200 and NULL_MATCH.search(response.content[:400]):
        return 'HTTP 200 with "match": null'
    return None


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------
def outcome_of(receipt: dict) -> str:
    what = receipt.get("error") and "error" or receipt.get("absent") and "absent" or str(receipt.get("status"))
    return what + (":cached" if receipt.get("skipped") else "")


def fetch_family(client, receipts, year: int, family: str, codes: list[tuple[str, str]], args,
                 outcomes: Counter) -> dict | None:
    """Fetch one family's documents for one year. Returns a note when the family was given up."""
    misses, seen = 0, False
    for mid, _ in codes:
        receipt = P.fetch(client, url_of(year, mid), dest_of(year, mid), receipts, name=receipt_name(year, mid),
                          refresh=args.refresh, validator=P.json_validator, compress=True,
                          headers=headers_for(year, mid), absent=null_match,
                          extra={"year": year, "match_id": mid, "decision": DECISION})
        outcomes[f"{year}:{family}:{outcome_of(receipt)}"] += 1
        if receipt.get("status") == 200 and not receipt.get("error") and not receipt.get("absent"):
            seen = True
        elif not seen and (receipt.get("absent") or receipt.get("status") == 404):
            misses += 1
            if args.skip_family_after and misses >= args.skip_family_after:
                return {"year": year, "family": family, "reason": f"the first {misses} codes are absent",
                        "last_code": mid}
    return None


# --------------------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------------------
def s(value) -> str | None:
    return P.s(value)


def team_fields(team: dict) -> list:
    players = team.get("players") or []
    sets = [{"score": st.get("score"), "tieBreak": st.get("tieBreak"), "winner": st.get("winner"),
             "isMatchTieBreak": st.get("isMatchTieBreak")} for st in team.get("sets") or []]
    return [json.dumps([p.get("id") for p in players]),
            json.dumps([f"{p.get('firstName') or ''} {p.get('lastName') or ''}".strip() for p in players],
                       ensure_ascii=False),
            json.dumps([p.get("country") for p in players]), json.dumps(sets)]


def stat_rows(year: int, mid: str, section: dict) -> list[list]:
    rows = []
    for key in STAT_SETS:
        block = section.get(key)
        if not isinstance(block, dict):
            continue
        set_key = "match" if key == "matchStatistics" else f"set{key[-1]}"
        for stat, v in block.items():
            if isinstance(v, dict) and ("teamAValue" in v or "teamBValue" in v):
                rows.append([str(year), mid, set_key, stat, s(v.get("label")), s(v.get("teamAValue")),
                             s(v.get("teamBValue"))])
    speed = section.get("serviceStatistics")
    if isinstance(speed, dict):
        for stat in ("fastest", "averageFirstServe", "averageSecondServe"):
            v = speed.get(stat)
            if isinstance(v, dict):
                rows.append([str(year), mid, "match", f"speed_{stat}", s(speed.get("title")), s(v.get("teamAValue")),
                             s(v.get("teamBValue"))])
    return rows


def stage(receipts, years: list[int]) -> dict:
    rounds = round_lookup()
    match_rows, stats = [], []
    answers = Counter()
    for name, rec in sorted(receipts.all().items()):
        parts = name.split("/")
        if len(parts) != 3 or parts[0] != "matches" or int(parts[1]) not in years:
            continue
        year, mid = int(parts[1]), parts[2]
        family = mid[:2]
        row = {"year": str(year), "match_id": mid, "family": family, "tour": "W" if family[1] == "D" else "M",
               "draw": "qual" if family[0] == "Q" else "main", "round_from_code": rounds.get(mid),
               "retrieved_at": rec.get("retrieved_at")}
        path = dest_of(year, mid)
        if rec.get("error") or rec.get("absent") or rec.get("status") != 200 or not path.exists():
            row["answer"] = "error" if rec.get("error") else "absent" if (rec.get("absent") or rec.get("status") == 404) \
                else f"status {rec.get('status')}"
            answers[row["answer"]] += 1
            match_rows.append([row.get(c) for c in MATCH_COLUMNS])
            continue
        doc = P.read_json(path)
        m = doc.get("match") or {}
        md = m.get("matchData") or {}
        a, b = m.get("teamA") or {}, m.get("teamB") or {}
        st = stat_rows(year, mid, doc.get("matchStatisticsSection") or {})
        stats.extend(st)
        answers["ok"] += 1
        ta, tb = team_fields(a), team_fields(b)
        row.update({
            "answer": "ok", "type": s(md.get("type")), "type_label": s(md.get("typeLabel")),
            "round_label": s(md.get("roundLabel")), "court_name": s(md.get("courtName")),
            "duration_minutes": s(md.get("durationInMinutes")), "date_schedule": s(md.get("dateSchedule")),
            "end_timestamp": s(md.get("endTimestamp")), "status": s(md.get("status")),
            "status_label": s(md.get("statusLabel")),
            "a_ids": ta[0], "a_names": ta[1], "a_countries": ta[2], "b_ids": tb[0], "b_names": tb[1],
            "b_countries": tb[2], "a_sets": ta[3], "b_sets": tb[3], "a_winner": s(a.get("winner")),
            "b_winner": s(b.get("winner")), "a_end_cause": s(a.get("endCause")), "b_end_cause": s(b.get("endCause")),
            "has_statistics": "TRUE" if any(r[2] == "match" for r in st) else "FALSE",
            "source_file": P.rel(path), "source_sha256": rec.get("sha256")})
        match_rows.append([row.get(c) for c in MATCH_COLUMNS])
    retrieved = max((r[-1] or "" for r in match_rows), default=None)
    out = {"answers": dict(answers)}
    for file, header, rows in (("matches.parquet", MATCH_COLUMNS, match_rows),
                               ("statistics.parquet", STAT_COLUMNS, stats)):
        st_ = P.stage_table(SOURCE, P.dump_path(SOURCE, file), header, rows, source_file=P.rel(P.raw_path(SOURCE)),
                            retrieved_at=retrieved, extra={"decision": DECISION})
        out[file] = {"rows": st_["rows"], "bytes": st_["bytes"]}
        P.log(f"[{SOURCE}] staged {file}: {st_['rows']:,} rows")
    return out


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def parse_years(text: str | None) -> list[int]:
    if not text:
        return list(YEARS)
    out = []
    for part in text.split(","):
        if "-" in part:
            lo, hi = part.split("-")
            out.extend(range(int(lo), int(hi) + 1))
        else:
            out.append(int(part))
    return out


def run(args) -> dict:
    P.configure_stdout()
    started = time.time()
    years = parse_years(args.years)
    families = [f.strip().upper() for f in args.families.split(",")] if args.families else list(FAMILIES)
    receipts = P.receipts_for(SOURCE)
    summary = {"source": SOURCE, "started_at": P.utc_now_iso(), "args": vars(args), "decision": DECISION}
    outcomes, skipped = Counter(), []
    if not args.stage_only:
        client = F.FeedClient("chrome", min_interval=args.min_interval, jitter=args.jitter,
                              max_requests=args.max_requests)
        try:
            for year in years:
                for family in families:
                    note = fetch_family(client, receipts, year, family, match_codes(family), args, outcomes)
                    if note:
                        skipped.append(note)
                        P.log(f"[{SOURCE}] {year} {family}: given up ({note['reason']})")
                    P.log(f"[{SOURCE}] {year} {family} done; requests={client.requests}; "
                          + ", ".join(f"{k}={v}" for k, v in sorted(outcomes.items()) if k.startswith(f"{year}:{family}")))
        except (P.Blocked, P.BudgetExhausted) as stop:
            summary["stopped"] = f"{type(stop).__name__}: {stop}"
            P.log(f"[{SOURCE}] STOPPED: {stop}")
        summary["client"] = client.stats()
    summary["fetch_outcomes"] = dict(sorted(outcomes.items()))
    summary["families_given_up"] = skipped
    if not args.no_stage:       # every held year, so a run for one year never drops the others from the tables
        summary["staged"] = stage(receipts, sorted(set(YEARS) | set(years)))
    errors = [r for r in receipts.all().values() if r.get("error")]
    summary["receipts"] = dict(sorted(Counter(
        f"{r['name'].split('/')[1]}:{outcome_of(r)}" for r in receipts.all().values()).items()))
    summary["receipts_with_errors"] = len(errors)
    summary["error_examples"] = [{"name": r["name"], "error": r["error"]} for r in errors[:20]]
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - started, 1)
    path = P.write_summary("rolandgarros_summary.json", summary,
                           root=Path(args.summary_dir) if args.summary_dir else STUDY_ROOT)
    P.log(f"[{SOURCE}] summary written to {P.rel(path)}")
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--years", help="e.g. 2019-2025 or 2022,2024 (default: 2019-2026)")
    parser.add_argument("--families", help="comma list of SM, SD, QM, QD (default: all)")
    parser.add_argument("--max-requests", type=int, default=3600, help="stop after this many HTTP requests")
    parser.add_argument("--min-interval", type=float, default=2.0, help="seconds between requests (plus jitter)")
    parser.add_argument("--jitter", type=float, default=1.0, help="up to this many extra seconds, drawn at random")
    parser.add_argument("--skip-family-after", type=int, default=8,
                        help="give a family up for a year when its first N codes are all absent (0: never)")
    parser.add_argument("--refresh", action="store_true", help="fetch documents already held (and absences) again")
    parser.add_argument("--stage-only", action="store_true", help="no HTTP; rebuild the tables from the raw files")
    parser.add_argument("--no-stage", action="store_true", help="fetch only")
    parser.add_argument("--summary-dir", help="write the run's summary here (default: the study's collection folder)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    P.log(f"[{SOURCE}] done in {summary['seconds']} s; {summary['receipts_with_errors']} receipts with errors"
          + (f"; stopped: {summary['stopped']}" if summary.get("stopped") else ""))
    return 1 if summary.get("stopped") or summary["receipts_with_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
