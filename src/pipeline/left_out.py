"""The matches a prediction run left out because of an error in their own row, said loudly (the owner, 28 Oct 2026:
"while you fix a single row it shouldnt hold up the whole pipeline", and, asking for this: "Be sure to mention the
match that was left out and that there was an error in one row clearly and loudly, however still give all the other
predictions"; docs/decisions/2026-10-28-one-bad-match-left-out.md; master pipeline process log, Part 25).

The run's <run>/left_out.json is the daily engine's file (src/eda/daily_prediction/dp_leftout.py; this layer reads and
writes the file, never the engine's modules): {"matches": [...], "earlier_rounds": [...], "updated_at"}. A match record
names the step that left it out: "check" (A4's check before the run, predict.predict_day: written here), "matchups",
"prices" or "tables" (the engine's), with the reason; its tour, event, round and the matchups CSV's players and day.
A record of a tour switched off for the bet day (config.BET_TOURS) carries switched_off: no error, the switch's.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

FILE = "left_out.json"
STEPS = {"check": "A4's check before the run", "matchups": "the run placing each match",
         "prices": "the run's prices", "tables": "the run's check of its own data"}


def read(run: Path) -> dict:
    """The run's records ({"matches": [], "earlier_rounds": []} for a run that left nothing out, or made before 28 Oct
    2026)."""
    p = Path(run) / FILE
    try:
        held = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except (OSError, ValueError) as exc:          # an unreadable record is itself said, never a silent "none"
        return {"matches": [{"step": "?", "reason": f"the run's {FILE} cannot be read ({type(exc).__name__}: {exc})",
                             "unreadable": True}], "earlier_rounds": []}
    return {"matches": list(held.get("matches") or []), "earlier_rounds": list(held.get("earlier_rounds") or [])}


def errors(run: Path) -> list[dict]:
    """The run's matches left out by an error (not by the bet day's tour switch)."""
    return [r for r in read(run)["matches"] if not r.get("switched_off")]


def write_check(run: Path, records: list[dict]) -> None:
    """A4's own records (the step "check"), written before the engine starts: it adds its records after these."""
    held = read(run)
    held["matches"] += [{**r, "step": "check"} for r in records]
    p = Path(run) / FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({**held, "updated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")},
                            indent=1, default=str), encoding="utf-8")


def describe(r: dict) -> str:
    """'WTA Guangzhou R16: Anna Bondar v Kaitlin Quevedo'."""
    event = r.get("tourney_name") or r.get("tourney_id") or "event unknown"
    return f"{str(r.get('tour') or '').upper()} {event} {r.get('round') or ''}".strip() + \
        f": {r.get('player_a')} v {r.get('player_b')}"


def describe_earlier(e: dict) -> str:
    """'ATP Basel Q2: Jan Kowalski beat Ivan Petrov'."""
    event = e.get("tourney_name") or e.get("tourney_id") or "event unknown"
    return f"{str(e.get('tour') or '').upper()} {event} {e.get('round') or ''}".strip() + \
        f": {e.get('winner')} beat {e.get('loser')}"


def lines(run: Path, predicted: int | None = None) -> list[str]:
    """The run's left-out matches and missing earlier rounds as "!!!" lines (none when there are none). predicted: the
    matches the run did predict, said beside them."""
    held = read(run)
    bad = [r for r in held["matches"] if not r.get("switched_off")]
    out = []
    if bad:
        rest = f"; the other {predicted} match{'es' * (predicted != 1)} were predicted" if predicted is not None else ""
        out.append(f"!!! ERROR IN {len(bad)} ROW{'S' * (len(bad) != 1)}: {len(bad)} MATCH{'ES' * (len(bad) != 1)} LEFT "
                   f"OUT, NO PREDICTION{rest} (the bet sheet lists {'them' if len(bad) != 1 else 'it'} under "
                   "'Not predicted'):")
        for r in bad:
            out.append(f"!!!   {describe(r)} -- at {STEPS.get(r.get('step'), r.get('step'))}: {r.get('reason')}")
    off = [r for r in held["matches"] if r.get("switched_off")]
    if off:
        out.append(f"{len(off)} match{'es' * (len(off) != 1)} of a switched-off tour left out before the run "
                   "(config.BET_TOURS): " + "; ".join(describe(r) for r in off))
    if held["earlier_rounds"]:
        n = len(held["earlier_rounds"])
        out.append(f"!!! {n} EARLIER ROUND{'S' * (n != 1)} FROM TENNISLIVE NOT IN THE RUN'S DATA (its player's match is "
                   "predicted without it; the gate decides on it as before):")
        for e in held["earlier_rounds"]:
            out.append(f"!!!   {describe_earlier(e)} -- {e.get('reason')}")
    return out
