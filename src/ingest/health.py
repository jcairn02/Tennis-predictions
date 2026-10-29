"""Feed health: how fresh each feed's newest content must be, and which source flags are known (production-integrity
plan, step 1; docs/decisions/2026-10-22-production-integrity-plan.md; docs/studies/master_pipeline/process_log.md,
Part 10).

One place for these rules: the scheduled task's alerts (src/ingest/scheduled.py), STATUS (src/pipeline/overview.py) and
the bet sheet read them here, never from copies of their own.

Freshness is judged from the newest CONTENT a feed brought (the newest reading, the newest match), never from a job's
exit code or a file's date: until 22 Oct 2026 the serve-speed job wrote a "today" form file on every run, even with
nothing collected, and STATUS showed that file's date.

    serve speeds   the speed job's own record (data/studies/serve_speed_tabpfn/live/runs.jsonl): the newest reading,
                   and how many matches it planned and staged. "stale": the newest reading is older than
                   SPEED_STALE_DAYS while there were rounds to collect; "empty": rounds planned, nothing staged; "off":
                   the collector is switched off
    source flags   the canary's flags (data/studies/data_continuity/canary_latest.json), less the ones acknowledged
                   until a date (data/studies/data_continuity/canary_acknowledged.json)
    Tennis My Life (28 Oct 2026; master pipeline process log, Part 10) the files whose newest version is held for
                   review ("lagging" once held longer than TML_LAG_HOURS: its new results are not in the data), the
                   finished events carried from earlier copies because no accepted season file holds them yet
                   (public_dump/tennis_my_life.py's continuity check), and the corrections the download accepted by
                   itself in the last TML_CORRECTIONS_DAYS days (the owner's decision 1, 28 Oct 2026)
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEED_RUNS = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "live" / "runs.jsonl"
SPEED_STALE_DAYS = 4          # a men's tour week has play on most days; four days without a reading while rounds were
                              # there to collect means the collector is not bringing them (agent's choice, 22 Oct 2026)
CANARY_LATEST = ROOT / "data" / "studies" / "data_continuity" / "canary_latest.json"
CANARY_KNOWN = ROOT / "data" / "studies" / "data_continuity" / "canary_acknowledged.json"
TML_RAW = ROOT / "data" / "raw" / "public_dump" / "tennis_my_life"
TML_LAG_HOURS = 24            # a file held longer than a day is lagging: the scheduled download runs daily, and TML's
                              # manifest catches up within a day when it only lagged (agent's choice, 28 Oct 2026)
TML_CORRECTIONS_DAYS = 7      # corrections accepted by the download itself, listed for review this long


def last_jsonl(path: Path) -> dict:
    """The last record of a JSON-lines file ({} when there is none)."""
    path = Path(path)
    if not path.exists():
        return {}
    lines = [x for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    return json.loads(lines[-1]) if lines else {}


def speed_status(today: dt.date | None = None, record: dict | None = None) -> dict:
    """The serve-speed feed's state from its own latest record: status ok / stale / empty / off / unknown, the newest
    reading and its age in days, the matches planned and staged by the latest collection, and a plain line."""
    today = today or dt.date.today()
    rec = last_jsonl(SPEED_RUNS) if record is None else record
    if not rec:
        return {"status": "unknown", "line": "no record of the speed job yet"}
    col = rec.get("collector") or {}
    newest = (rec.get("form") or {}).get("latest_reading")
    age = (today - dt.date.fromisoformat(str(newest)[:10])).days if newest else None
    planned, staged = int(col.get("plan_requests") or 0), int(col.get("staged") or 0)
    out = {"newest_reading": newest, "age_days": age, "planned": planned, "staged": staged,
           "collected_at": rec.get("run_at"), "collector": col.get("status")}
    if str(col.get("status") or "").startswith("disabled"):
        out["status"] = "off"
    elif planned and (age is None or age > SPEED_STALE_DAYS):
        out["status"] = "stale"
    elif planned and not staged and col.get("status") == "ran":
        out["status"] = "empty"
    else:
        out["status"] = "ok"
    when = str(rec.get("run_at") or "?")[:16].replace("T", " ")
    out["line"] = (f"newest reading {newest or 'none'}" + (f" ({age} days old)" if age is not None else "") +
                   f"; last collection {when} UTC: {staged} of {planned} planned matches staged" +
                   {"ok": "", "stale": f"  STALE: older than {SPEED_STALE_DAYS} days while rounds were there to collect",
                    "empty": "  NOTHING STAGED although rounds were planned",
                    "off": "  COLLECTOR SWITCHED OFF (live/collector.json)"}[out["status"]])
    return out


def canary_known(today: dt.date | None = None) -> dict:
    """{flag: entry} of the acknowledged canary flags, each with "active" (its date not passed)."""
    today = today or dt.date.today()
    if not CANARY_KNOWN.exists():
        return {}
    rows = json.loads(CANARY_KNOWN.read_text(encoding="utf-8")).get("acknowledged", [])
    return {r["flag"]: {**r, "active": today <= dt.date.fromisoformat(r["until"])} for r in rows}


def canary_flags() -> set[str]:
    """item:FLAG pairs of the latest canary run (only a flag's first word counts, so a flag whose text carries a date
    or a day count does not look new every week)."""
    try:
        flags = json.loads(CANARY_LATEST.read_text(encoding="utf-8")).get("flags", {})
    except (FileNotFoundError, ValueError):
        return set()
    if isinstance(flags, dict):
        return {f"{item}:{str(f).split()[0]}" for item, fl in flags.items()
                for f in (fl if isinstance(fl, list) else [fl]) if str(f).strip()}
    return {str(f).split()[0] for f in flags if str(f).strip()}


def canary_split(flags: set[str], known: dict) -> dict:
    """The flags in three groups: acknowledged (and still in date), lapsed (acknowledged, its date passed: alert again),
    and open (never acknowledged)."""
    return {"acknowledged": sorted(f for f in flags if f in known and known[f]["active"]),
            "lapsed": sorted(f for f in flags if f in known and not known[f]["active"]),
            "open": sorted(f for f in flags if f not in known)}


def _utc(text) -> dt.datetime | None:
    try:
        t = dt.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def _day(t: dt.datetime | None) -> str:
    return t.astimezone().strftime("%d %b %H:%M") if t else "?"


def tml_status(now: dt.datetime | None = None, raw: Path | None = None) -> dict:
    """Tennis My Life's download as the data stands: held files (lagging past TML_LAG_HOURS), the events carried from
    earlier copies, and the corrections accepted by the download itself in the last TML_CORRECTIONS_DAYS days. "lines":
    plain lines for STATUS, A1 and the bet sheet, a loud one first ("LAGGING", "CARRIED"); empty when all is well."""
    from src.ingest.public_dump import tennis_my_life as T
    now = now or dt.datetime.now(dt.timezone.utc)
    raw = Path(raw or TML_RAW)
    held = []
    for name, h in sorted(T.held_now(raw / "_receipts.jsonl").items()):
        since = _utc(h.get("since"))
        hours = (now - since).total_seconds() / 3600 if since else None
        held.append({"file": name, "since": h.get("since"), "hours": round(hours, 1) if hours is not None else None,
                     "lagging": hours is None or hours > TML_LAG_HOURS, "runs": h.get("runs"),
                     "reason": h.get("reason"),
                     "accept_with": f"--accept-held {name}@{str(h.get('sha256'))[:12]}"})
    carried = []
    for p in sorted((raw / T.CARRIED).glob("*.json")) if (raw / T.CARRIED).exists() else []:
        try:
            state = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        for e in state.get("events") or []:
            since = _utc(e.get("since"))
            carried.append({"file": state.get("file"), "event": e.get("tourney_id"), "name": e.get("tourney_name"),
                            "date": e.get("tourney_date"), "rows": len(e.get("rows") or []), "from": e.get("from"),
                            "since": e.get("since"), "days": round((now - since).total_seconds() / 86400, 1)
                            if since else None})
    corrections = []
    changes = raw / "_changes.jsonl"
    for line in changes.read_text(encoding="utf-8", errors="replace").splitlines() if changes.exists() else []:
        try:
            c = json.loads(line)
        except ValueError:
            continue
        at = _utc(c.get("retrieved_at"))
        if c.get("paired") and at and (now - at) <= dt.timedelta(days=TML_CORRECTIONS_DAYS):
            corrections.append({"file": c.get("name"), "at": c.get("retrieved_at"), "rows": sum(c["paired"].values()),
                                "kinds": c.get("paired_kinds") or {}})
    lines = []
    lag = [h for h in held if h["lagging"]]
    if lag:
        lines.append("LAGGING: Tennis My Life " + "; ".join(
            f"{h['file']} held since {_day(_utc(h['since']))} ({h['hours'] / 24:.1f} days, {h['runs']} downloads: "
            f"{h['reason']})" for h in lag) +
            ". The data keeps the copy before each; a finished event that moved into a held file is carried (CARRIED). "
            "Ask Claude to review the held copies.")
    if carried:
        lines.append("CARRIED: " + "; ".join(
            f"{c['name']} {c['date']} ({c['rows']} rows, since {_day(_utc(c['since']))})" for c in carried) +
            ": finished events kept from earlier copies, because no accepted season file holds them yet.")
    fresh = [h for h in held if not h["lagging"]]
    if fresh:
        lines.append("Held for review today (not yet lagging): " +
                     "; ".join(f"{h['file']}: {h['reason']}" for h in fresh) + ".")
    if corrections:
        lines.append("Corrections Tennis My Life made and the download accepted by itself (last "
                     f"{TML_CORRECTIONS_DAYS} days): " + "; ".join(
                         f"{c['file']} {c['rows']} ({', '.join(f'{v} {k}' for k, v in c['kinds'].items())})"
                         for c in corrections) + ". Listed in data/raw/public_dump/tennis_my_life/_changes.jsonl.")
    return {"held": held, "lagging": [h["file"] for h in lag], "carried": carried, "corrections": corrections,
            "lines": lines}
