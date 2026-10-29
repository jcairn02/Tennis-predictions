"""The matches a live run leaves out because of an error in their own row, so that every other match is still predicted
(the owner, 28 Oct 2026: "while you fix a single row it shouldnt hold up the whole pipeline", and, asking for this: "Be
sure to mention the match that was left out and that there was an error in one row clearly and loudly, however still
give all the other predictions"; docs/decisions/2026-10-28-one-bad-match-left-out.md; master pipeline process log, Part
25). The design is an agent's choice.

    <run>/left_out.json   {"matches": [...], "earlier_rounds": [...], "updated_at"}
        matches           one record per match left out: the matchups CSV's row (csv_row), its tour, event
                          (tourney_id, tourney_name), round, players (the CSV's names) and day, the step that left it
                          out, the reason, and the match id where one was made
        earlier_rounds    the earlier qualifying rounds from TennisLive (prediction_run/earlier_rounds.py) the run could
                          not add or Stage 0 does not hold: their match is still predicted without them, and the gate
                          decides on it as before
    A4 (src/pipeline/predict.py: its check before the run writes the step "check" here first) prints every record, and
    the bet sheet shows them; the run's log says each one with "!!!" when it is made.

Where a live run leaves a match out (a replay, and the 8 Oct path prediction_run/run.py, still stop on any of these):
    matchups   its row cannot be placed: its event, a player, its live row or its day (prediction_run/run.
               live_from_matchups with leave_out)
    prices     its price is not strictly between 0 and 1 (dp_matchups.prices)
    tables     the live rows' check (prediction_run/inject.py check --leave-out): not in the work tree's Stage 0 under
               the id expected, not built as a live match, no Stage 1 row to come, or sides that disagree. Its live row
               goes and Stage 0 is built again without it (dp_tables.prep), so the other matches' inputs are those of a
               run whose CSV did not list it
A refusal that names no match still stops the run, and so does a run whose every match is left out.
"""
from __future__ import annotations

import math
import numbers
from pathlib import Path

import numpy as np
import pandas as pd

import dp_common as DC

FILE = "left_out.json"
MATCH_FIELDS = ("csv_row", "tour", "tourney_id", "tourney_name", "round", "player_a", "player_b", "day")
EARLIER_FIELDS = ("tour", "tourney_id", "tourney_name", "round", "winner", "loser", "tl_url", "match_id")
ENGINE_STEPS = ("matchups", "prices", "tables")       # A4's own check ("check") runs before them, outside the engine


def _plain(v):
    """A JSON value: None for a missing one, an int for a whole number (numpy's too), a day as YYYY-MM-DD, else text."""
    if v is None:
        return None
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, numbers.Integral):
        return int(v)
    if isinstance(v, numbers.Real):
        return None if math.isnan(v) else (int(v) if float(v).is_integer() else float(v))
    if isinstance(v, pd.Timestamp):
        return None if pd.isna(v) else (v.strftime("%Y-%m-%d") if v == v.normalize() else v.isoformat())
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return str(v)


def read(run_dir: Path) -> dict:
    """The run's records ({"matches": [], "earlier_rounds": []} when it left nothing out)."""
    p = Path(run_dir) / FILE
    held = DC.read_json(p) if p.exists() else {}
    return {"matches": list(held.get("matches") or []), "earlier_rounds": list(held.get("earlier_rounds") or [])}


def _write(run_dir: Path, held: dict) -> None:
    DC.write_json(Path(run_dir) / FILE, {**held, "updated_at": DC.stamp()})


def describe(r: dict) -> str:
    """'WTA Guangzhou R16: Anna Bondar v Kaitlin Quevedo'."""
    event = r.get("tourney_name") or r.get("tourney_id") or "event unknown"
    return f"{str(r.get('tour') or '').upper()} {event} {r.get('round') or ''}".strip() + \
        f": {r.get('player_a')} v {r.get('player_b')}"


def describe_earlier(e: dict) -> str:
    """'WTA Guangzhou Q2: Kaitlin Quevedo beat Ena Chen'."""
    event = e.get("tourney_name") or e.get("tourney_id") or "event unknown"
    return f"{str(e.get('tour') or '').upper()} {event} {e.get('round') or ''}".strip() + \
        f": {e.get('winner')} beat {e.get('loser')}"


def from_meta(meta: pd.DataFrame, reasons) -> list[dict]:
    """Records for matches of a run's meta table (live_meta.parquet's columns): reasons a text for all of them, or
    {match id: text}."""
    out = []
    for _, r in meta.iterrows():
        mid = str(r["match_id"])
        out.append({"csv_row": r.get("csv_row"), "tour": r.get("tour"), "tourney_id": mid.split("|")[1] if "|" in mid
                    else None, "tourney_name": r.get("tournament_name"), "round": r.get("round"),
                    "player_a": r.get("player_a"), "player_b": r.get("player_b"), "day": r.get("day"),
                    "match_id": mid, "reason": reasons if isinstance(reasons, str) else reasons.get(mid)})
    return out


def add(run_dir: Path, step: str, matches=(), earlier=()) -> dict:
    """The records of `step` added to the run's (matches: dicts with the reason and what they know of MATCH_FIELDS and
    match_id; earlier: the same with EARLIER_FIELDS), each said in the run's log with "!!!". Returns every record."""
    held = read(run_dir)
    new_m = [{**{k: _plain(r.get(k)) for k in MATCH_FIELDS}, "step": step,
              "reason": str(r.get("reason") or "no reason recorded"),
              **({"match_id": str(r["match_id"])} if r.get("match_id") else {})} for r in matches]
    new_e = [{**{k: _plain(e.get(k)) for k in EARLIER_FIELDS}, "step": step,
              "reason": str(e.get("reason") or "no reason recorded")} for e in earlier]
    if not new_m and not new_e:
        return held
    held["matches"] += new_m
    held["earlier_rounds"] += new_e
    _write(run_dir, held)
    for r in new_m:
        DC.log(f"!!! LEFT OUT at the {step} step, an error in its row: {describe(r)} -- {r['reason']}")
    if new_m:
        DC.log(f"!!! {len(new_m)} match{'es' * (len(new_m) != 1)} left out at the {step} step; the others go on")
    for e in new_e:
        DC.log(f"!!! EARLIER ROUND NOT ADDED ({step} step): {describe_earlier(e)} -- {e['reason']}; its player's match "
               "is still predicted, without it")
    return held


def reset(run_dir: Path, steps=ENGINE_STEPS) -> None:
    """Forget the records of `steps` (a matchups step run again builds every live row anew); A4's own stay."""
    p = Path(run_dir) / FILE
    if not p.exists():
        return
    held = read(run_dir)
    kept = {k: [r for r in v if r.get("step") not in steps] for k, v in held.items()}
    if kept != held:
        _write(run_dir, kept)


def drop(folder: Path, csv_rows) -> dict:
    """The matches of these CSV rows taken out of a run's tables (the run folder's, or the work tree's run/ copy):
    live_meta.parquet by csv_row, live_rows.parquet each one's live row (live_role "live", _row: its earlier rounds,
    "played", stay, as history), prices.parquet by the match ids the meta gave them. The other rows are written back
    as they were (pyarrow, the schema kept). Returns the counts dropped."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    rows = {int(x) for x in csv_rows}
    out, ids = {}, set()
    folder = Path(folder)
    p = folder / "live_meta.parquet"
    if p.exists():
        t = pq.read_table(p)
        m = t.select(["match_id", "csv_row"]).to_pandas()
        hit = pd.to_numeric(m["csv_row"], errors="coerce").isin(rows).to_numpy()
        ids = set(m.loc[hit, "match_id"].astype(str))
        pq.write_table(t.filter(pa.array(~hit)), p)
        out["live_meta"] = int(hit.sum())
    p = folder / "live_rows.parquet"
    if p.exists():
        t = pq.read_table(p)
        r = t.select(["live_role", "_source_file", "_row"]).to_pandas()
        hit = (r["live_role"].astype(str).eq("live") & r["_source_file"].astype(str).eq("live_rows")
               & pd.to_numeric(r["_row"], errors="coerce").isin(rows)).to_numpy()
        pq.write_table(t.filter(pa.array(~hit)), p)
        out["live_rows"] = int(hit.sum())
    p = folder / "prices.parquet"
    if p.exists() and ids:
        t = pq.read_table(p)
        hit = t.column("match_id").to_pandas().astype(str).isin(ids).to_numpy()
        pq.write_table(t.filter(pa.array(~hit)), p)
        out["prices"] = int(hit.sum())
    return out
