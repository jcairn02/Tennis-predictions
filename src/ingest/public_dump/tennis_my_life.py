"""Tennis My Life current downloads (register PUB049): ATP main tour, Challenger, ATP qualifying,
WTA main tour season files, ongoing-tournament files, the ATP player database and a rankings file.

Source: https://stats.tennismylife.org/tennis-match-database with the public file manifest at
https://stats.tennismylife.org/api/data-files. Rights are unresolved: the website labels the
dataset MIT while the publisher's GitHub README says noncommercial unless permitted.

Season files are re-downloaded when the manifest's mtime/size changes (or the copy held is not the size the
manifest lists); ongoing files are always refreshed because they change daily. Since Sackmann's end, Stage 0
takes every new result from these files, and TML rewrites them in place (it corrected a 2024 score on 5 Oct
2026). So, agreed in docs/studies/data_continuity/ (6 Oct 2026):

* Nothing is lost. A re-download that brings different bytes keeps the replaced file first, under
  superseded/ with its receipts (common.keep_replaced). --no-keep-superseded turns that off.
* A damaged file never becomes current. A season file is held when its last record is ragged (a
  half-written file), when it is not the size the manifest lists (TML was rewriting it), when a column is
  lost, or when more than 5 rows, or more than half the rows, of the current copy are gone once corrections
  are paired with the rows they correct. An ongoing file is held only when ragged or a column is lost. A held file is kept under held/
  with the reason, the current copy stays, staging uses the current copy, and the run exits non-zero. After
  review, --accept-held NAME@SHA12 lets that exact version through on the next run.
* A correction is a vanished row and a new row of the same match: the same tournament id, date, round and
  player ids, or names where TML had left ids blank. Since 28 Oct 2026 (the owner's decision: "Decision 1 ... I
  approve"; docs/decisions/2026-10-28-tml-corrections-pass.md) also a row of the same event with the same two
  player ids in any order, any round, date or score (a winner reversed, a round relabelled), the event by its id
  or, when TML renumbered it, by its name and date. A row whose player id changed is not one: it still counts
  as gone. Until then such corrections held whole season files, and on 19-20 Oct 2026 a finished week with them.
* Every accepted revision of a season file appends its rows added, removed and corrected, and the changed
  columns, to _changes.jsonl, with the corrections of the same event and players and the rows removed listed
  for review (at most LIST_MAX of each).
* Nothing that left a file of events under way is lost (28 Oct 2026, the same plan): each finished event of
  the previous copy must be in the new copy or in an accepted season file. One that is in neither (its season
  file held, or not yet updated) is carried: its rows, from the held season copy that has them (TML's later
  version), else from the previous copy, are added to the staged copy of the file of events under way, each row
  with its own source, until an accepted season file holds the event. The kept events are in carried/<file>.json;
  the run says CARRIED for a new one and "back" when one returns. On 19 Oct 2026 Wuhan and six Challengers
  (241 rows) left the files of events under way into held season files, and four bet-day runs lacked them.
* One run at a time: a .lock file younger than an hour stops a second run.

Usage:
    ./python.sh -m src.ingest.public_dump.tennis_my_life --start-year 2010
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import common as C

SOURCE = "tennis_my_life"
CATALOG_URL = "https://stats.tennismylife.org/api/data-files"
PAGE_URL = "https://stats.tennismylife.org/tennis-match-database"
README_URL = "https://raw.githubusercontent.com/Tennismylife/TML-Database/master/README.md"

MATCH_HEADER = C.csv_header_contains("tourney_id")
RULES = [
    # regex on catalog name, branch, subdir, validator, has_year, always_refresh
    (r"^(\d{4})\.csv$", "matches", "atp_main", MATCH_HEADER, True, False),
    (r"^(\d{4})_challenger\.csv$", "matches", "atp_challenger", MATCH_HEADER, True, False),
    (r"^(\d{4})_wta\.csv$", "matches", "wta_main", MATCH_HEADER, True, False),
    (r"^atp_quali/(\d{4})_atp_quali\.csv$", "matches", "atp_qualifying", MATCH_HEADER, True, False),
    (r"^(?:ongoing_tourneys|wta_ongoing_tourneys|challenger_ongoing_tourneys|ch_ongoing_tourney)\.csv$",
     "matches", "ongoing", MATCH_HEADER, False, True),
    (r"^ATP_Database\.csv$", "players", "", C.csv_header_contains("player"), False, True),
    (r"^atp_rankings_.*\.csv$", "rankings", "", C.csv_header_contains("rank"), False, False),
]
SKIP_RULES = [
    (r"^backup_ll_audit_", "publisher backup copy of the same season files (duplicate)"),
    (r"^atp_matches_amateur\.csv$", "amateur-era results (from 1877); outside the recency priority"),
]
SEASON = re.compile(r"^(?:atp_quali/)?\d{4}(?:_challenger|_wta|_atp_quali)?\.csv$")
ONGOING = re.compile(r"ongoing_tourney")
GATE_MAX_REMOVED = 5          # rows of the current copy that may vanish (TML removes the odd duplicate)
LOCK_MAX_AGE = 3600           # seconds after which a lock is taken to be left by a dead run
ID_KEY = ["tourney_id", "tourney_date", "round", "winner_id", "loser_id"]
NAME_KEY = ["tourney_id", "round", "winner_name", "loser_name"]
# the owner's decision 1 (28 Oct 2026): a row of the same event with the same two player ids, in any order, round, date
# or score, corrects a vanished one; the event by its id, then by its name and date (TML renumbered San Diego 2 on 19 Oct
# 2026, and events of 2022-2023 on 28 Oct)
PAIR_KEYS = (("same event and players", ["tourney_id"]), ("event renumbered", ["tourney_name", "tourney_date"]))
LIST_MAX = 200                # corrections and removed rows listed per file in _changes.jsonl
ONGOING_SEASON = {"ongoing_tourneys.csv": "{}.csv", "challenger_ongoing_tourneys.csv": "{}_challenger.csv",
                  "wta_ongoing_tourneys.csv": "{}_wta.csv"}    # each file of events under way and its season files
CARRIED = "carried"           # <raw>/carried/<file of events under way>.json: the events kept (the continuity check)
UNTRUSTED_HOLDS = ("half-written", "columns lost")   # a held copy whose rows are not taken for a carried event


def default_end_year() -> int:
    """This year and the next: TML's next season file appears in late December (its 2025 file starts with matches
    of 29 Dec 2024)."""
    return dt.datetime.now(dt.timezone.utc).year + 1


def plan(catalog_files, start: int, end: int):
    selected, skipped = [], []
    for item in catalog_files:
        name = item["name"]
        reason = next((why for regex, why in SKIP_RULES if re.match(regex, name)), None)
        if reason:
            skipped.append({"path": name, "reason": reason})
            continue
        for regex, branch, subdir, validator, has_year, always in RULES:
            match = re.match(regex, name)
            if not match:
                continue
            if has_year:
                year = int(match.group(1))
                if not start <= year <= end:
                    skipped.append({"path": name, "reason": f"year {year} outside {start}-{end}"})
                    break
            selected.append((branch, subdir, item, validator, always))
            break
        else:
            skipped.append({"path": name, "reason": "no rule matches this catalog entry"})
    return selected, skipped


# ------------------------------------------------------------------------------------------------
# The gate: a damaged file never becomes current

def read_rows(data: bytes) -> tuple[list[str], list[tuple[str, ...]], bool]:
    """Header, data records, and whether the last record is ragged (fewer fields than the header)."""
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    reader = csv.reader(io.StringIO(text))
    header = next(reader, [])
    rows = [tuple(r) for r in reader if r]
    return header, rows, bool(rows) and len(rows[-1]) < len(header)


def correction_kind(cols: list[str], old: tuple, new: tuple) -> str:
    """What a correction of the same event and players changed, in words ("winner reversed + score")."""
    at = {c: i for i, c in enumerate(cols)}

    def get(row, c):
        return row[at[c]] if c in at else ""
    words = ["event renumbered"] if get(old, "tourney_id") != get(new, "tourney_id") else []
    if get(old, "winner_id") == get(new, "loser_id") and get(old, "loser_id") == get(new, "winner_id"):
        words.append("winner reversed")
    words += [w for c, w in (("round", "round"), ("tourney_date", "date"), ("score", "score")) if get(old, c) != get(new, c)]
    return " + ".join(words) or "other cells"


def _said(cols: list[str], row: tuple) -> dict:
    """A row in a reviewer's words: its event, round, players and score."""
    at = {c: i for i, c in enumerate(cols)}

    def get(c):
        return row[at[c]] if c in at else ""
    return {"event": get("tourney_id"), "name": get("tourney_name"), "date": get("tourney_date"), "round": get("round"),
            "winner": f"{get('winner_name')} ({get('winner_id')})", "loser": f"{get('loser_name')} ({get('loser_id')})",
            "score": get("score")}


def row_changes(old_header: list[str], old_rows: list[tuple], new_header: list[str], new_rows: list[tuple]) -> dict:
    """Rows added, removed and corrected between two versions of a file, and the changed cells per column.

    Rows are compared whole, so line endings and quoting do not count. A vanished row and a new row are a
    correction when they share a match identity: first tournament id and date, round and both player ids (where
    both ids are given), then tournament id, round and both names (TML fills in blank ids later). Then (decision 1,
    28 Oct 2026) the same event and the same two player ids in any order, any round, date or score (PAIR_KEYS):
    "paired" counts these by key, "paired_kinds" by what changed, and "paired_rows" lists them (before and after).
    "removed_rows" lists the rows of the old copy left without a twin."""
    cols = list(dict.fromkeys(list(old_header) + list(new_header)))

    def align(header, rows):
        idx = [header.index(c) if c in header else None for c in cols]
        return [tuple(r[i] if i is not None and i < len(r) else "" for i in idx) for r in rows]

    old, new = Counter(align(old_header, old_rows)), Counter(align(new_header, new_rows))
    gone, came = list((old - new).elements()), list((new - old).elements())
    corrected, cells = 0, Counter()
    for key, need in ((ID_KEY, ("winner_id", "loser_id")), (NAME_KEY, ("winner_name", "loser_name"))):
        ki = [cols.index(k) for k in key if k in cols]
        ni = [cols.index(k) for k in need if k in cols]
        if len(ki) < len(key):
            continue
        pool: dict[tuple, list] = {}
        for row in came:
            if all(row[i] for i in ni):
                pool.setdefault(tuple(row[i] for i in ki), []).append(row)
        left = []
        for row in gone:
            twins = pool.get(tuple(row[i] for i in ki)) if all(row[i] for i in ni) else None
            if twins:
                twin = twins.pop()
                came.remove(twin)
                corrected += 1
                cells.update(c for j, c in enumerate(cols) if row[j] != twin[j])
            else:
                left.append(row)
        gone = left
    paired, kinds, listed = Counter(), Counter(), []
    ids = [cols.index(c) for c in ("winner_id", "loser_id") if c in cols]
    for label, event in (PAIR_KEYS if len(ids) == 2 else ()):
        ei = [cols.index(k) for k in event if k in cols]
        if len(ei) < len(event):
            continue

        def pair_key(row):
            a, b = row[ids[0]], row[ids[1]]
            return (*(row[i] for i in ei), *sorted((a, b))) if a and b and all(row[i] for i in ei) else None
        pool = {}
        for row in came:
            k = pair_key(row)
            if k is not None:
                pool.setdefault(k, []).append(row)
        left = []
        for row in gone:
            k = pair_key(row)
            twins = pool.get(k) if k is not None else None
            if twins:
                twin = twins.pop()
                came.remove(twin)
                paired[label] += 1
                cells.update(c for j, c in enumerate(cols) if row[j] != twin[j])
                kind = correction_kind(cols, row, twin)
                kinds[kind] += 1
                if len(listed) < LIST_MAX:
                    listed.append({"changed": kind, "before": _said(cols, row), "after": _said(cols, twin)})
            else:
                left.append(row)
        gone = left
    out = {"rows_old": len(old_rows), "rows_new": len(new_rows), "added": len(came), "removed": len(gone),
           "corrected": corrected + sum(paired.values()), "cells": dict(cells.most_common())}
    if paired:
        out.update(paired=dict(paired), paired_kinds=dict(kinds.most_common()), paired_rows=listed)
    if gone:
        out["removed_rows"] = [_said(cols, r) for r in gone[:LIST_MAX]]
    return out


def make_gate(name: str, dest: Path, item: dict, accept: set[str], changes: dict):
    """The gate for one catalog file (common.download's ``gate``): a reason to hold the new bytes, or None."""
    season, ongoing = bool(SEASON.match(name)), bool(ONGOING.search(name))

    def gate(body: bytes):
        if f"{name}@{C.sha256_bytes(body)[:12]}" in accept:
            changes[name] = {"accepted_after_review": True}
            return None
        if not (season or ongoing):
            return None
        header, rows, ragged = read_rows(body)
        if ragged:
            return "its last record has fewer fields than the header (a half-written file)"
        if season and item.get("size") is not None and len(body) != item["size"]:
            return f"received {len(body):,} bytes where the manifest lists {item['size']:,} (a file being rewritten)"
        if not dest.exists():
            return None
        old_header, old_rows, _ = read_rows(dest.read_bytes())
        lost = [c for c in old_header if c not in header]
        if lost:
            return f"columns lost: {', '.join(lost)}"
        if season:
            diff = row_changes(old_header, old_rows, header, rows)
            if diff["removed"] > GATE_MAX_REMOVED:
                more = sum((diff.get("paired") or {}).values())
                return (f"{diff['removed']} rows of the current copy are gone (more than {GATE_MAX_REMOVED})" +
                        (f"; {more} more are corrections of the same event and players" if more else ""))
            if diff["removed"] and diff["removed"] * 2 > len(old_rows):
                return f"{diff['removed']} of the current copy's {len(old_rows)} rows are gone (more than half)"
            changes[name] = diff
        return None

    return gate


# ------------------------------------------------------------------------------------------------
# The continuity check: nothing that leaves a file of events under way is lost (28 Oct 2026)

def held_now(path: Path | None = None) -> dict[str, dict]:
    """The files whose newest version is held for review, from the receipts: {name: {"since": the first hold after the
    last accepted version, "runs": how many downloads held it since, "reason", "dest", "sha256", "retrieved_at": the
    newest held version's}}. A version accepted later (or with --accept-held) ends the hold."""
    path = path or C.raw_path(SOURCE, "_receipts.jsonl")
    accepted: dict[str, int] = {}                  # the line of each file's last accepted version: the receipts file
    holds: dict[str, list[tuple[int, dict]]] = {}  # is append-only, so its order is the order of the downloads
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
    for i, line in enumerate(lines):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        name = str(r.get("name") or "")
        if r.get("error") or not r.get("sha256"):
            continue
        if name.startswith("held/"):
            holds.setdefault(name[len("held/"):], []).append((i, r))
        else:
            accepted[name] = i
    out = {}
    for name, rs in holds.items():
        after = [r for i, r in rs if i > accepted.get(name, -1)]
        if after:
            last = after[-1]
            out[name] = {"since": after[0]["retrieved_at"], "runs": len(after), "reason": last.get("held"),
                         "dest": last.get("dest"), "sha256": last.get("sha256"), "retrieved_at": last.get("retrieved_at")}
    return out


def events_of(header: list[str], rows: list[tuple]) -> dict[str, dict]:
    """A file's events by tournament id, in file order: name, first date and every date (TML's men's files date each
    row by its day), the header, the rows and their numbers (1-based, as staging numbers them)."""
    at = {c: i for i, c in enumerate(header)}

    def get(row, c):
        i = at.get(c)
        return row[i] if i is not None and i < len(row) else ""
    out: dict[str, dict] = {}
    for n, row in enumerate(rows, 1):
        tid = get(row, "tourney_id")
        e = out.setdefault(tid, {"tourney_id": tid, "tourney_name": get(row, "tourney_name"),
                                 "tourney_date": get(row, "tourney_date"), "dates": [], "header": list(header),
                                 "rows": [], "row_numbers": []})
        e["rows"].append(list(row))
        e["row_numbers"].append(n)
        if get(row, "tourney_date") not in e["dates"]:
            e["dates"].append(get(row, "tourney_date"))
    return out


def _named(e: dict) -> set:
    return {("event", e["tourney_name"], d) for d in (e.get("dates") or [e["tourney_date"]])}


def event_keys(events) -> set:
    """An event is found by its id, or by its name and any of its dates (an event TML renumbered)."""
    events = events.values() if isinstance(events, dict) else events
    return {k for e in events for k in ({("id", e["tourney_id"])} | _named(e))}


def find_event(events: dict, e: dict) -> dict | None:
    """The event of ``events`` that is ``e``: by id, else by name and a date in common."""
    if e["tourney_id"] in events:
        return events[e["tourney_id"]]
    return next((x for x in events.values() if _named(x) & _named(e)), None)


def carry_forward(previous: dict, current: dict, accepted: set, held: list[dict], kept: list[dict], source: dict,
                  now: str) -> tuple[list[dict], dict]:
    """The continuity check of one file of events under way.

    previous, current: its events before and after this run's download (events_of); accepted: the event keys of the
    accepted season copies (event_keys); held: the season copies held for review, newest first, each {"path",
    "sha256", "retrieved_at", "events"}; kept: the events the last run carried; source: the previous copy's "path",
    "sha256" and "retrieved_at". An event of the previous copy in neither the new copy nor an accepted season copy is
    carried, and one carried before stays carried until it is back in one of them. Its rows come from whichever has
    the most of them: a held copy (TML's own later version; the newer on a tie) or what it had (the previous copy's
    rows, or the last run's). Returns the events carried and a report: "new", "kept" and "back" (no longer carried)."""
    here = event_keys(current) | accepted

    def found(e):
        return bool(({("id", e["tourney_id"])} | _named(e)) & here)

    def best(e, base):
        cands = [{**x, "from": h["path"], "from_sha256": h["sha256"], "from_retrieved_at": h["retrieved_at"]}
                 for h in held for x in [find_event(h["events"], e)] if x] + [base]
        top = max(cands, key=lambda c: len(c["rows"]))              # the first of the largest: held, newest first
        keep = ("tourney_id", "tourney_name", "tourney_date", "dates", "header", "rows", "row_numbers", "from",
                "from_sha256", "from_retrieved_at")
        return {**{k: top.get(k) for k in keep}, "since": base.get("since") or now}

    def said(e):
        return {"event": e["tourney_id"], "name": e["tourney_name"], "date": e["tourney_date"], "rows": len(e["rows"]),
                "from": e.get("from"), "since": e.get("since")}

    out, report = [], {"new": [], "kept": [], "back": []}
    for e in kept:
        if found(e):
            report["back"].append(said(e))
        else:
            out.append(best(e, e))
            report["kept"].append(said(out[-1]))
    carried = event_keys(out)
    for e in previous.values():
        if found(e) or ({("id", e["tourney_id"])} | _named(e)) & carried:
            continue
        out.append(best(e, {**e, "from": source.get("path"), "from_sha256": source.get("sha256"),
                            "from_retrieved_at": source.get("retrieved_at")}))
        report["new"].append(said(out[-1]))
    return out, report


def stage_carried(out: Path, events: list[dict]) -> int:
    """Append the carried events' rows to a staged file of events under way, each row with its own source (the
    held or archived copy it came from, and its row there), so Stage 0 and every other reader of that file see them.
    Returns the rows added."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    rows = [(e, num, row) for e in events for num, row in zip(e["row_numbers"], e["rows"])]
    if not rows:
        return 0
    table = pq.read_table(out)
    prov = {"_source": lambda e, n: SOURCE, "_source_file": lambda e, n: e.get("from"), "_row": lambda e, n: n,
            "_width_ok": lambda e, n: "ok", "_extra": lambda e, n: None,
            "_sha256": lambda e, n: e.get("from_sha256"), "_retrieved_at": lambda e, n: e.get("from_retrieved_at")}
    index = {id(e): {c: i for i, c in enumerate(C.dedupe_header(e["header"]))} for e in events}
    arrays = []
    for f in table.schema:
        if f.name in prov:
            arrays.append(pa.array([prov[f.name](e, n) for e, n, _ in rows], f.type))
        else:
            arrays.append(pa.array([r[index[id(e)][f.name]] if f.name in index[id(e)] and
                                    index[id(e)][f.name] < len(r) else None for e, _, r in rows], f.type))
    part = out.with_name(out.name + ".part")
    pq.write_table(pa.concat_tables([table, pa.Table.from_arrays(arrays, schema=table.schema)]), part,
                   compression="zstd")
    os.replace(part, out)
    return len(rows)


def continuity(receipts: C.Receipts, before: dict[str, bytes], replaced: dict[str, str | None], items: dict,
               now: str) -> dict:
    """The continuity check of every file of events under way after this run's downloads (carry_forward), its state
    written to carried/<file>.json, and the file staged again with the carried rows. ``before``: each file's bytes
    before the run; ``replaced``: where the run archived them (superseded/); ``items``: the catalog's entries."""
    pending = held_now()
    out = {"new": [], "kept": [], "back": []}
    for name, season in ONGOING_SEASON.items():
        dest = C.raw_path(SOURCE, name)
        state = C.raw_path(SOURCE, CARRIED, Path(name).stem + ".json")
        kept = json.loads(state.read_text(encoding="utf-8")).get("events", []) if state.exists() else []
        if not dest.exists() or (name not in before and not kept):
            continue
        current = events_of(*read_rows(dest.read_bytes())[:2])
        previous = events_of(*read_rows(before[name])[:2]) if name in before else {}
        years = {int(str(e["tourney_date"])[:4]) + k for e in [*previous.values(), *kept]
                 if str(e["tourney_date"])[:4].isdigit() for k in (0, 1)}
        accepted, held = set(), []
        for year in sorted(years):
            file = season.format(year)
            if C.raw_path(SOURCE, file).exists():
                accepted |= event_keys(events_of(*read_rows(C.raw_path(SOURCE, file).read_bytes())[:2]))
            h = pending.get(file)
            path = C.PROJECT_ROOT / h["dest"] if h and h.get("dest") else None
            if h and path and path.exists() and not any(w in str(h.get("reason")) for w in UNTRUSTED_HOLDS):
                header, rows, ragged = read_rows(path.read_bytes())
                if not ragged:
                    held.append({"path": h["dest"], "sha256": h["sha256"], "retrieved_at": h["retrieved_at"],
                                 "events": events_of(header, rows)})
        held.sort(key=lambda h: str(h["retrieved_at"]), reverse=True)
        first, _ = receipts.sightings(name, C.sha256_bytes(before[name])) if name in before else (None, None)
        source = {"path": replaced.get(name) or C.rel(dest), "retrieved_at": (first or {}).get("retrieved_at"),
                  "sha256": C.sha256_bytes(before[name]) if name in before else None}
        carried, report = carry_forward(previous, current, accepted, held, kept, source, now)
        for k in out:
            out[k] += [{"file": name, **r} for r in report[k]]
        if carried or kept:
            state.parent.mkdir(parents=True, exist_ok=True)
            C.write_atomic(state, json.dumps({"file": name, "checked_at": now, "events": carried}, ensure_ascii=False,
                                             indent=1).encode("utf-8"))
        staged = C.dump_path("matches", SOURCE, "ongoing", Path(name).stem + ".parquet")
        if (carried or kept) and receipts.get(name):
            item = items.get(name) or {}
            meta = C.stage_csv_file("matches", SOURCE, receipts.get(name), dest, staged, catalog_name=name,
                                    catalog_mtime=item.get("mtime"), catalog_size=item.get("size"))
            n = stage_carried(staged, carried)
            if n:
                meta.update(rows=(meta.get("rows") or 0) + n, carried_rows=n,
                            carried=[{k: e.get(k) for k in ("tourney_id", "tourney_name", "tourney_date", "from",
                                                              "since")} | {"rows": len(e["rows"])} for e in carried])
                meta["bytes"] = staged.stat().st_size
                C.write_meta(staged, meta)
    return out


def take_lock(path: Path) -> None:
    if path.exists():
        age = time.time() - path.stat().st_mtime
        if age < LOCK_MAX_AGE:
            raise RuntimeError(f"another Tennis My Life run holds {C.rel(path)} (started {age / 60:.0f} minutes ago); "
                               "wait for it, or delete the file if that run has died")
        path.unlink()                    # left by a run that died more than an hour ago
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps({"pid": os.getpid(), "started_at": C.utc_now_iso()}))


# ------------------------------------------------------------------------------------------------

def run(args) -> dict:
    lock = C.raw_path(SOURCE, ".lock")
    take_lock(lock)
    try:
        return _run(args)
    finally:
        lock.unlink(missing_ok=True)


def _run(args) -> dict:
    receipts = C.Receipts(SOURCE)
    keep = not getattr(args, "no_keep_superseded", False)
    accept = set(getattr(args, "accept_held", None) or [])
    catalog_dest = C.raw_path(SOURCE, "_catalog.json")
    receipt = C.download(CATALOG_URL, catalog_dest, receipts, name="_catalog.json", refresh=True,
                         validator=C.not_html, keep_superseded=keep)
    if receipt.get("error"):
        raise RuntimeError(f"Tennis My Life manifest unavailable: {receipt['error']}")
    catalog = json.loads(catalog_dest.read_text(encoding="utf-8"))
    C.download(README_URL, C.raw_path(SOURCE, "docs", "TML-Database_README.md"), receipts,
               name="docs/TML-Database_README.md", refresh=args.refresh, validator=C.not_html, keep_superseded=keep)
    selected, skipped = plan(catalog["files"], args.start_year, args.end_year)
    C.log(f"[{SOURCE}] catalog lists {catalog['count']} files; {len(selected)} planned, {len(skipped)} skipped")
    staged, held, changes = [], [], {}
    # the files of events under way as they were before this run, for the continuity check after it
    before = {n: C.raw_path(SOURCE, n).read_bytes() for n in ONGOING_SEASON if C.raw_path(SOURCE, n).exists()}
    replaced: dict[str, str | None] = {}
    for branch, subdir, item, validator, always in selected:
        name = item["name"]
        dest = C.raw_path(SOURCE, name)
        previous = receipts.get(name)
        unchanged = (previous and not previous.get("error") and dest.exists()
                     and previous.get("catalog_mtime") == item.get("mtime")
                     and previous.get("catalog_size") == item.get("size")
                     and previous.get("bytes") == item.get("size"))
        refresh = args.refresh or always or not unchanged
        receipt = C.download(item["url"], dest, receipts, name=name, refresh=refresh, validator=validator,
                             extra={"catalog_mtime": item.get("mtime"), "catalog_size": item.get("size")},
                             keep_superseded=keep, gate=make_gate(name, dest, item, accept, changes))
        if name in ONGOING_SEASON and not receipt.get("skipped"):
            replaced[name] = receipt.get("superseded")
        if receipt.get("held"):
            held.append({"name": name, "reason": receipt["held"], "kept_as": receipt["dest"],
                         "accept_with": f"--accept-held {name}@{receipt['sha256'][:12]}"})
            C.log(f"[{SOURCE}] HELD {name}: {receipt['held']}; kept as {receipt['dest']}, the current copy stays")
            continue
        if receipt.get("superseded") and not receipt.get("skipped"):   # a skipped file returns its last receipt
            C.log(f"[{SOURCE}] {name} changed; kept the replaced file as {receipt['superseded']}")
        if receipt.get("error"):
            C.log(f"[{SOURCE}] FAIL {name}: {receipt['error']}")
            continue
        diff = changes.get(name)
        if diff and not receipt.get("skipped") and (diff.get("added") or diff.get("removed") or diff.get("corrected")
                                                    or diff.get("accepted_after_review")):
            line = {"name": name, "retrieved_at": receipt.get("retrieved_at"), "sha256": receipt.get("sha256"),
                    "previous_sha256": (previous or {}).get("sha256"), "superseded": receipt.get("superseded"), **diff}
            with C.raw_path(SOURCE, "_changes.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(line, ensure_ascii=False) + "\n")
        out = C.dump_path(branch, SOURCE, subdir, Path(name).stem + ".parquet")
        if out.exists() and receipt.get("skipped") and not args.refresh:
            continue
        meta = C.stage_csv_file(branch, SOURCE, receipt, dest, out, catalog_name=name,
                                catalog_mtime=item.get("mtime"), catalog_size=item.get("size"))
        staged.append(meta)
        C.log(f"[{SOURCE}] staged {meta['dest']} rows={meta['rows']} short={meta['short_rows']} long={meta['long_rows']}")
    for name, d in changes.items():
        if d.get("paired"):
            C.log(f"[{SOURCE}] {name}: {sum(d['paired'].values())} corrections of the same event and players accepted "
                  f"({', '.join(f'{v} {k}' for k, v in d['paired_kinds'].items())}); listed in _changes.jsonl")
    carry = continuity(receipts, before, replaced, {i["name"]: i for i in catalog["files"]}, C.utc_now_iso())
    for e in carry["new"]:
        C.log(f"[{SOURCE}] CARRIED {e['name']} {e['date']} ({e['event']}, {e['rows']} rows): it left {e['file']} and "
              f"no accepted season file holds it; kept from {e['from']}")
    for e in carry["kept"]:
        C.log(f"[{SOURCE}] still carried {e['name']} {e['date']} ({e['event']}, {e['rows']} rows) since {e['since']}, "
              f"from {e['from']}")
    for e in carry["back"]:
        C.log(f"[{SOURCE}] back: {e['name']} {e['date']} ({e['event']}) is in an accepted file again; no longer carried")
    summary = C.summarize(receipts, staged, skipped)
    summary["held"] = held
    summary["carried"] = carry
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--start-year", type=int, default=C.DEFAULT_START_YEAR)
    parser.add_argument("--end-year", type=int, default=default_end_year(),
                        help="last season file to fetch (default: next year, so a season file published in "
                             "December is not missed)")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--no-keep-superseded", action="store_true",
                        help="overwrite changed files without keeping the replaced bytes")
    parser.add_argument("--accept-held", action="append", default=[], metavar="NAME@SHA12",
                        help="after review, let this held version through (repeatable)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    carried = summary["carried"]["new"] + summary["carried"]["kept"]
    C.log(f"[{SOURCE}] done: {summary['staged_files']} staged files, {summary['staged_rows']:,} rows, "
          f"{len(summary['errors'])} download errors, {len(summary['held'])} held, {len(carried)} events carried")
    for h in summary["held"]:
        C.log(f"[{SOURCE}] held {h['name']}: {h['reason']}. To accept it after review: {h['accept_with']}")
    return 1 if summary["errors"] or summary["held"] else 0


if __name__ == "__main__":
    sys.exit(main())
