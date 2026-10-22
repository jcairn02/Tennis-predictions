"""The ATP Stats Centre's Challenger point files, decrypted and staged in tables of their own (owner, 14 Oct 2026).

The files are those infosys_challengers.py and the P6 data-issues probe downloaded into the infosys_atp adapter's raw
folder (data/raw/point_sources/infosys_atp/<year>/<event>/<route>/<MID>.json.gz), told apart by their receipts'
purpose (CHALLENGER_PURPOSES). The owner's decision (docs/decisions/2026-10-14-p6-data-issues.md, point 2): put them on
the data map in their own tables, kept out of the serve-speed history. So nothing here touches the infosys_atp tables,
which the serve-speed backfill reads (src/eda/serve_speed_tabpfn/panel.py); infosys_atp_decrypt and infosys_atp_stage
leave these purposes out in turn.

Decryption is the site's own (src/ingest/point_sources/infosys_slams.decrypt), approved for the ATP's files
(docs/decisions/2026-10-08-scraping-approved.md). Every decoded field is kept:
    data/dump/points/infosys_challengers/decrypted/<year>/<event>/<route>/<MID>.json
An existing plain file that differs is preserved and reported, never overwritten. The raw envelopes are not touched.

Tables (data/dump/points/infosys_challengers/, strings as the rest of the dump, with infosys_atp_stage's parsers):
    matches.parquet   one row per (year, event, match code) with a file: infosys_atp_stage's match columns, plus the
                      copy's match date for the code (the Hugging Face copy, infosys_full, which lists most 2021-24
                      Challenger matches with their day) and Stage 0's tournament date for the event
    points.parquet    every MatchBeats point, its fields verbatim, with set and game numbers
    rally.parquet     every rally-analysis entry
Summary: data/studies/p6_data_issues/infosys_challengers/stage_summary.json

Run: ./python.sh -m src.ingest.point_sources.infosys_challengers_stage
"""
from __future__ import annotations

import gzip
import json
import sys
import time
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P
from src.ingest.point_sources import infosys_atp as A
from src.ingest.point_sources import infosys_atp_stage as S
from src.ingest.point_sources import infosys_slams as I

SOURCE = "infosys_challengers"
DECISION = "docs/decisions/2026-10-14-p6-data-issues.md"
CHALLENGER_PURPOSES = frozenset({"p6 challengers", "p6_data_issues probe"})
ROUTES = ("match-beats", "rally-analysis")
DECRYPTED = P.dump_path(SOURCE, "decrypted")
COPY = P.PROJECT_ROOT / "data" / "raw" / "public_dump" / "atp_pipeline_handoff" / "infosys_full"
STAGE0 = P.PROJECT_ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
SUMMARY = P.PROJECT_ROOT / "data" / "studies" / "p6_data_issues" / "infosys_challengers" / "stage_summary.json"
MATCH_COLUMNS = S.MATCH_COLUMNS + ["copy_match_date", "stage0_tournament_date"]


def challenger_receipts(receipts=None) -> dict[str, dict]:
    """The adapter's receipts of served Challenger files (CHALLENGER_PURPOSES), by receipt name."""
    receipts = receipts if receipts is not None else P.receipts_for(A.SOURCE)
    return {name: r for name, r in receipts.all().items()
            if r.get("purpose") in CHALLENGER_PURPOSES and A.served(r) and r.get("route") in ROUTES}


def decrypt_all(recs: dict[str, dict], out: Path = DECRYPTED) -> tuple[dict, Counter]:
    """Each served envelope decrypted to its plain file; returns {(year, event, MID): {route: path}} and counts."""
    files: dict[tuple, dict] = {}
    counts: Counter = Counter()
    for name, r in sorted(recs.items()):
        year, event, route, mid = str(r["year"]), str(r["event_id"]), r["route"], str(r["match_id"]).upper()
        src = P.PROJECT_ROOT / r["dest"]
        target = out / year / event / route / f"{mid}.json"
        try:
            doc = I.decrypt(json.loads(gzip.decompress(src.read_bytes())))
            plain = (json.dumps(doc, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and target.read_bytes() != plain:
                counts["existing_output_differs_kept"] += 1
                continue
            if not target.exists():
                target.write_bytes(plain)
                counts["decrypted"] += 1
            else:
                counts["already_decrypted"] += 1
            files.setdefault((year, event, mid), {})[route] = target
        except (OSError, ValueError, KeyError, TypeError) as exc:
            counts[f"error: {type(exc).__name__}"] += 1
    return files, counts


def copy_dates(keys: set) -> dict:
    """The copy's match date for each (year, event, MID), where the copy lists the code."""
    out = {}
    for year in sorted({k[0] for k in keys}):
        path = COPY / f"{year}_data.jsonl.gz"
        if not path.exists():
            continue
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                d = json.loads(line)
                k = (str(d.get("year")), str(d.get("tournament_id")), str(d.get("match_id") or "").upper())
                if k in keys and d.get("match_date"):
                    out[k] = str(d["match_date"])
    return out


def event_key(year, event) -> str:
    """'<year>-<event>' without the event's leading zeros: Stage 0 writes some of Sackmann's ids '2018-0444'."""
    return f"{year}-{str(event).lstrip('0')}"


def stage0_dates() -> dict:
    """Stage 0's tournament date for each ATP event ('<year>-<event>'), Challengers and qualifying included."""
    import pandas as pd
    s0 = pd.read_parquet(STAGE0, columns=["tour", "tournament_id", "tournament_date"])
    s0 = s0[s0["tour"].eq("atp")].drop_duplicates("tournament_id")
    out = {}
    for t, d in zip(s0["tournament_id"].astype(str), s0["tournament_date"]):
        y, _, e = t.partition("-")
        if e.isdigit():
            out.setdefault(event_key(y, e), str(pd.Timestamp(d).date()))
    return out


def stage(files: dict) -> dict:
    """The three tables from the decrypted files (infosys_atp_stage's row builders)."""
    dates = copy_dates(set(files))
    t_dates = stage0_dates()
    points, rallies, match_rows = [], [], []
    counts = Counter()
    for (year, event, mid), paths in sorted(files.items(), key=lambda kv: (kv[0][0], int(kv[0][1]), kv[0][2])):
        docs = {route: json.loads(path.read_text(encoding="utf-8")) for route, path in paths.items()}
        keys = [year, event, mid]
        mb = docs.get("match-beats") if isinstance(docs.get("match-beats"), dict) else {}
        ra = docs.get("rally-analysis") if isinstance(docs.get("rally-analysis"), dict) else {}
        if mb:
            points.extend(I.point_rows(keys + ["match-beats"], mb))
        if ra:
            rallies.extend(I.rally_rows(keys + ["rally-analysis"], ra))
        pts = [p for set_ in mb.get("setData") or [] for g in set_.get("gameData") or [] for p in g.get("pointData") or []]
        timed = [p for p in pts if (I.num(p.get("serveSpeed")) or 0) > 0]
        rally_entries = [e for c in ra.get("rallyData") or [] for v in c.values() if isinstance(v, list) for e in v
                         if isinstance(e, dict)]
        p1, p2 = S.players(docs)
        family = mid[:2]
        first = lambda *vals: next((v for v in vals if v not in (None, "")), None)  # noqa: E731
        match_rows.append(keys + [
            family, "qual" if family == "QS" else "main", S.round_from_code(event, mid),
            "p6 challengers", json.dumps(sorted(paths)), str(len(paths)),
            P.s(mb.get("eventType")), P.s(mb.get("courtId")), P.s(mb.get("courtName")),
            P.s(first(mb.get("isMatchComplete"), ra.get("matchCompleted"))), P.s(mb.get("matchStatus")),
            P.s(mb.get("matchWinner")), P.s(first(mb.get("setsComplete"), ra.get("setsCompleted"))),
            P.s(p1.get("id")), P.s(p1.get("name")), P.s(p1.get("first")), P.s(p1.get("last")), P.s(p1.get("country")),
            P.s(p2.get("id")), P.s(p2.get("name")), P.s(p2.get("first")), P.s(p2.get("last")), P.s(p2.get("country")),
            str(len(pts)), str(len(timed)), str(sum(1 for p in timed if str(p.get("serve")) == "1")),
            str(sum(1 for p in pts if str(p.get("result")) in S.ENDINGS)), "0", P.s(False), str(len(rally_entries)),
            str(sum(1 for e in rally_entries if (I.num(e.get("serveSpeed")) or 0) > 0)), "0", "0", None,
            json.dumps([P.rel(paths[r]) for r in sorted(paths)]),
            dates.get((year, event, mid)), t_dates.get(event_key(year, event))])
        counts[f"{year}|matches"] += 1
        counts[f"{year}|with_points"] += bool(pts)
        counts[f"{year}|with_rally"] += bool(rally_entries)
        counts[f"{year}|with_a_date"] += bool(dates.get((year, event, mid)) or t_dates.get(event_key(year, event)))
    out = {}
    tables = [
        ("matches.parquet", MATCH_COLUMNS, match_rows),
        ("points.parquet", S.KEYS + ["route", "set", "game", "seq"] + I.POINT_FIELDS
         + ["other_fields", "game_fields", "set_fields"], points),
        ("rally.parquet", S.KEYS + ["route", "category", "list"] + I.RALLY_FIELDS + ["other_fields"], rallies),
    ]
    for file, header, rows in tables:
        st = P.stage_table(SOURCE, P.dump_path(SOURCE, file), header, rows, source_file=P.rel(DECRYPTED),
                           retrieved_at=None, extra={"decision": DECISION})
        out[file] = {"rows": st["rows"], "bytes": st["bytes"]}
        P.log(f"[{SOURCE}] staged {file}: {st['rows']:,} rows")
    out["by_year"] = {}
    for key, n in sorted(counts.items()):
        y, what = key.split("|")
        out["by_year"].setdefault(y, {})[what] = n
    return out


def main() -> int:
    P.configure_stdout()
    t0 = time.time()
    recs = challenger_receipts()
    files, counts = decrypt_all(recs)
    summary = {"source": SOURCE, "started_at": P.utc_now_iso(), "decision": DECISION,
               "receipts": len(recs), "decryption": dict(counts), "matches": len(files),
               "decrypted_folder": P.rel(DECRYPTED), "staged": stage(files)}
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - t0, 1)
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    P.log(f"[{SOURCE}] {len(files):,} matches staged; summary {P.rel(SUMMARY)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
