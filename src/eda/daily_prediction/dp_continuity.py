"""The bet-time check that nothing finished has gone missing (the production-integrity plan as revised after the audit
of 27 Oct 2026 and approved by the owner on 28 Oct: "I approve the plan"; docs/studies/master_pipeline/process_log.md,
Part 10). An agent's design; it decides nothing.

On 19-20 Oct 2026 four bet-day runs lacked a whole finished week (Wuhan and six Challengers, 241 matches) and nothing
said so: the history check compares with the frozen reference of 8 Oct, so every later match is "future" to it, and
nothing compared a run with the runs before. This check keeps a ledger of the finished matches that live runs' tables
held over the last WINDOW_DAYS, and looks for each of them again in each new live run's tables (the work tree's Stage 0
after the lower-level additions):

    found      by identity, never by match id (an id changes when Tennis My Life renumbers an event: 60 and 136 such
               between the runs of 20-23 Oct 2026): the same tour and two players at the same event, the event by its
               name or by a date at most DATE_SLACK days away, so a round relabelled, a winner reversed or an event
               renumbered or re-dated is still found (two players who meet again a week later are not one match);
               else the same tour, event, round and score with one of the two players (a player's id changed)
    missing    a ledger match not found. It stays in the ledger with the run that first missed it, so it is said on
               every run until it is back: a run-to-run comparison would say it once and then take the hole as normal
    removed    a missing match Tennis My Life itself removed in a revision the download accepted (its removed rows,
               listed in _changes.jsonl since 28 Oct 2026): said as such, apart from the missing ones

It never restores or blocks (the owner, 27 Oct 2026: "I could imagine that it could block bets incorrectly"). A4 prints
its line (src/pipeline/predict.py), and the bet sheet gives each match whose player has a missing match an amber note
(src/pipeline/diagnostics.py). Only live runs read and write the ledger: a replay's tables are of another day.

    <run>/continuity.json                         this run's check (read by A4 and the bet sheet)
    data/studies/daily_prediction/ledger/         finished_matches.parquet (the ledger), checks.jsonl (one line a run)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd

import dp_common as DC

WINDOW_DAYS = 56          # about 8 weeks: a qualifier's or a returning player's recent form reaches this far back
DATE_SLACK = 3            # days: an event of the same name, or one dated this close (Stage 0's rule C05 re-dates an
                          # event by its main draw), is the same event; a week apart is another (agent's choice)
RESULTS = ("completed", "retired", "walkover")
LEDGER = DC.OUT / "ledger"
COLUMNS = ["match_id", "tour", "tournament_id", "tournament_name", "tdate", "level", "qualifying", "round", "score", "lo",
           "hi", "name_lo", "name_hi", "first_seen_run", "last_seen_run", "last_seen_at", "missing_since_run",
           "missing_since_at"]


def finished(matches: pd.DataFrame, players: pd.DataFrame, day: pd.Timestamp) -> pd.DataFrame:
    """The finished matches of a Stage 0 whose event is dated from day - WINDOW_DAYS on, in the ledger's columns,
    without the run's own live rows (an upcoming match, or an earlier round filled from TennisLive for one run only).
    No upper date: Stage 0 dates an event by its main draw (rule C05), so qualifying played today is dated days ahead
    (found by the replay of 18-25 Oct 2026: Brussels' and Almaty's first qualifying round, played on 18 Oct and dated
    20 Oct the next morning, looked missing)."""
    m = matches[matches["status"].isin(RESULTS)].copy()
    if "source_file" in m.columns:
        m = m[m["source_file"].astype(str).ne("live_rows")]
    m["tdate"] = pd.to_datetime(m["tournament_date"]).dt.strftime("%Y-%m-%d")
    m = m[m["tdate"] >= (pd.Timestamp(day) - pd.Timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%d")]
    a, b = m["player_a_id"].astype(str), m["player_b_id"].astype(str)
    m["lo"], m["hi"] = a.where(a < b, b), b.where(a < b, a)
    names = (players.drop_duplicates("player_id").set_index("player_id")["player_name"].astype(str)
             if len(players) else pd.Series(dtype=str))
    m["name_lo"], m["name_hi"] = m["lo"].map(names).fillna(""), m["hi"].map(names).fillna("")
    m["score"] = m["score"].fillna("").astype(str)
    for c in ("tournament_id", "tournament_name", "round", "level"):
        m[c] = m[c].astype(str)
    return m[["match_id", "tour", "tournament_id", "tournament_name", "tdate", "level", "qualifying", "round", "score",
              "lo", "hi", "name_lo", "name_hi"]].reset_index(drop=True)


def found_in(ledger: pd.DataFrame, cur: pd.DataFrame) -> pd.Series:
    """For each ledger row, whether the current matches hold it by identity (the module's "found")."""
    if not len(ledger):
        return pd.Series(dtype=bool)
    led = ledger.reset_index(drop=True).assign(_i=lambda d: range(len(d)))

    def near(x: pd.DataFrame) -> pd.Series:           # the same event: its name, or a date at most DATE_SLACK days away
        days = (pd.to_datetime(x["tdate"]) - pd.to_datetime(x["tdate_c"])).abs()
        return x["tournament_name"].eq(x["tournament_name_c"]) | (days <= pd.Timedelta(days=DATE_SLACK))
    ev = ["tournament_name", "tdate"]
    pair = led[["_i", "tour", "lo", "hi", *ev]].merge(cur[["tour", "lo", "hi", *ev]], on=["tour", "lo", "hi"],
                                                     suffixes=("", "_c"))
    hit = set(pair.loc[near(pair), "_i"]) if len(pair) else set()

    def sides(x: pd.DataFrame, idx: bool) -> pd.DataFrame:
        cols = ["tour", "round", "score", *ev] + (["_i"] if idx else [])
        x = x[x["score"].str.strip().ne("")]
        return pd.concat([x[cols].assign(pid=x["lo"]), x[cols].assign(pid=x["hi"])], ignore_index=True)
    one = sides(led[~led["_i"].isin(hit)], True).merge(sides(cur, False), on=["tour", "round", "score", "pid"],
                                                       suffixes=("", "_c"))
    hit |= set(one.loc[near(one), "_i"]) if len(one) else set()
    return pd.Series(led["_i"].isin(hit).to_numpy(), index=ledger.index)


def tml_removed(raw: Path) -> pd.DataFrame:
    """The rows Tennis My Life removed in the revisions the download accepted (_changes.jsonl's removed_rows, since 28
    Oct 2026): event id, round and score, with the file and the time."""
    path = Path(raw) / "_changes.jsonl"
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []:
        try:
            c = json.loads(line)
        except ValueError:
            continue
        for r in c.get("removed_rows") or []:
            rows.append({"tournament_id": str(r.get("event")), "round": str(r.get("round")),
                         "score": str(r.get("score") or "").strip(), "file": c.get("name"), "at": c.get("retrieved_at")})
    return pd.DataFrame(rows, columns=["tournament_id", "round", "score", "file", "at"])


def check(cur: pd.DataFrame, ledger: pd.DataFrame, day: pd.Timestamp, run: str, now: str,
          removed: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """One live run's check: the ledger after it, and the report (missing and removed matches, with their players)."""
    lo_day = (pd.Timestamp(day) - pd.Timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%d")
    first = not len(ledger)
    led = ledger[ledger["tdate"] >= lo_day].copy() if len(ledger) else pd.DataFrame(columns=COLUMNS)
    seen = found_in(led, cur) if len(led) else pd.Series(dtype=bool)
    gone = led[~seen] if len(led) else led
    if removed is not None and len(removed) and len(gone):
        by = removed.assign(score=removed["score"].str.strip())
        key = gone["tournament_id"] + "|" + gone["round"] + "|" + gone["score"].str.strip()
        rkey = by["tournament_id"] + "|" + by["round"] + "|" + by["score"]
        was = key.isin(set(rkey))
        where = dict(zip(rkey, by["file"] + " at " + by["at"].astype(str)))
    else:
        was, where = pd.Series(False, index=gone.index), {}
    # the ledger after this run: what is still found is updated, what is not keeps its first missing run, and every
    # finished match of today's tables not in it yet is added
    if len(led):
        led.loc[seen, ["last_seen_run", "last_seen_at"]] = [run, now]
        led.loc[seen, ["missing_since_run", "missing_since_at"]] = [None, None]
        new_gone = ~seen & led["missing_since_run"].isna()
        led.loc[new_gone, ["missing_since_run", "missing_since_at"]] = [run, now]
    known = found_in(cur, led[seen]) if len(led) and seen.any() else pd.Series(False, index=cur.index)
    add = cur[~known].assign(first_seen_run=run, last_seen_run=run, last_seen_at=now, missing_since_run=None,
                             missing_since_at=None)
    after = pd.concat([led, add[COLUMNS]], ignore_index=True)[COLUMNS] if len(led) else add[COLUMNS].reset_index(drop=True)

    def said(r) -> dict:
        return {"tour": r["tour"], "event": r["tournament_name"], "event_id": r["tournament_id"], "date": r["tdate"],
                "round": r["round"], "players": f"{r['name_lo'] or r['lo']} v {r['name_hi'] or r['hi']}",
                "player_ids": [r["lo"], r["hi"]], "score": r["score"], "last_seen": r["last_seen_run"],
                "missing_since": r["missing_since_run"] or run}
    missing = [said(r) for _, r in gone[~was].iterrows()]
    by_tml = [{**said(r), "removed_by": where.get(f"{r['tournament_id']}|{r['round']}|{r['score'].strip()}")}
              for _, r in gone[was].iterrows()]
    players: dict[str, list[dict]] = {}
    for m in missing:
        for pid in m["player_ids"]:
            players.setdefault(pid, []).append({"event": m["event"], "round": m["round"], "date": m["date"]})
    events = sorted({(m["tour"], m["event"], m["date"]) for m in missing})
    report = {"run": run, "checked_at": now, "first_check": first, "window_days": WINDOW_DAYS,
              "finished_now": int(len(cur)), "in_ledger": int(len(led)), "found": int(seen.sum()) if len(led) else 0,
              "missing": missing, "removed_by_tml": by_tml, "missing_by_player": players,
              "missing_events": [{"tour": t, "event": e, "date": d,
                                  "matches": sum(1 for m in missing if (m["tour"], m["event"], m["date"]) == (t, e, d))}
                                 for t, e, d in events]}
    report["line"] = line(report)
    return after, report


def line(rep: dict) -> str:
    """A4's line: loud when finished matches are missing."""
    if rep.get("failed"):
        return f"CONTINUITY CHECK FAILED ({rep['failed']}): nothing compared this run's results with earlier runs'."
    if rep.get("first_check"):
        return (f"Continuity check: started its ledger with the {rep['finished_now']} finished matches of the last "
                f"{rep['window_days']} days; the next live run is compared with it.")
    miss = rep.get("missing") or []
    tail = (f" {len(rep['removed_by_tml'])} more were removed by Tennis My Life in a revision it published."
            if rep.get("removed_by_tml") else "")
    if not miss:
        return (f"Continuity check: all {rep['found']} finished matches of the last {rep['window_days']} days seen by "
                f"earlier runs are in today's data." + tail)
    ev = "; ".join(f"{e['tour'].upper()} {e['event']} {e['date']} ({e['matches']})" for e in rep["missing_events"][:8])
    more = f" and {len(rep['missing_events']) - 8} more events" if len(rep["missing_events"]) > 8 else ""
    return (f"MISSING RESULTS: {len(miss)} finished matches that earlier runs had are not in today's data ({ev}{more}). "
            f"The model does not know them: a bet on a player who played one carries an amber note on the sheet. "
            f"Not a block. Ask Claude to find why (usually a held Tennis My Life file)." + tail)


def newest_results(matches: pd.DataFrame, timing: pd.DataFrame | None) -> dict:
    """Each live player's newest finished match in the tables (the bet sheet's "newest result"): its day (the timeline's
    latest possible finish, else the event's date), event and round. The live players are those of the run's own live
    rows."""
    live = matches[matches["source_file"].astype(str).eq("live_rows")] if "source_file" in matches.columns else \
        matches.iloc[0:0]
    ids = set(live["player_a_id"].astype(str)) | set(live["player_b_id"].astype(str))
    done = matches[matches["status"].isin(RESULTS) & ~matches.index.isin(live.index)]
    done = done[done["player_a_id"].astype(str).isin(ids) | done["player_b_id"].astype(str).isin(ids)].copy()
    lf = (timing.astype({"match_id": str}).set_index("match_id")["lf"] if timing is not None and len(timing)
          else pd.Series(dtype=float))
    days = done["match_id"].astype(str).map(lf)
    done["day"] = [DC.date_of(int(d)) if pd.notna(d) else str(t)[:10]
                   for d, t in zip(days, pd.to_datetime(done["tournament_date"]))]
    out = {}
    for side in ("player_a_id", "player_b_id"):
        for pid, g in done.groupby(done[side].astype(str)):
            if pid in ids:
                top = g.sort_values(["day", "round_order"]).iloc[-1]
                if pid not in out or top["day"] > out[pid]["day"]:
                    out[pid] = {"day": top["day"], "event": str(top["tournament_name"]), "round": str(top["round"])}
    return out


def run_check(run_dir: Path, tree: Path) -> dict:
    """The check of a live run on its work tree's tables: the ledger read and written (atomically), the report in
    <run>/continuity.json and a line in ledger/checks.jsonl. A failure is reported, never raised (it must not stop a
    bet-day run)."""
    now, run = DC.stamp(), Path(run_dir).name
    try:
        meta = pd.read_parquet(Path(run_dir) / "live_meta.parquet")
        day = pd.to_datetime(meta["day"]).min().normalize()
        m = pd.read_parquet(Path(tree) / DC.PD / "stage0_matches.parquet")
        p = pd.read_parquet(Path(tree) / DC.PD / "stage0_match_players.parquet", columns=["player_id", "player_name"])
        cur = finished(m, p, day)
        path = LEDGER / "finished_matches.parquet"
        ledger = pd.read_parquet(path) if path.exists() else pd.DataFrame(columns=COLUMNS)
        after, rep = check(cur, ledger, day, run, now, tml_removed(DC.REPO / "data/raw/public_dump/tennis_my_life"))
        try:
            tl = Path(tree) / DC.MT / "timing.parquet"
            rep["newest_result"] = newest_results(m, pd.read_parquet(tl, columns=["match_id", "lf"]) if tl.exists()
                                                  else None)
        except Exception as exc:  # noqa: BLE001 - context for the sheet only
            rep["newest_result_failed"] = f"{type(exc).__name__}: {exc}"
        LEDGER.mkdir(parents=True, exist_ok=True)
        part = path.with_name(path.name + ".part")
        after.astype({c: "string" for c in COLUMNS if c != "qualifying"}).to_parquet(part, index=False)
        os.replace(part, path)
    except Exception as exc:  # noqa: BLE001 - a check never stops the run; its failure is said loudly instead
        rep = {"run": run, "checked_at": now, "failed": f"{type(exc).__name__}: {exc}"}
        rep["line"] = line(rep)
    try:
        if str(DC.REPO) not in sys.path:
            sys.path.append(str(DC.REPO))
        from src.ingest import health as H
        rep["tml"] = H.tml_status()
        rep["speed"] = H.speed_status()            # the serve-speed feed's newest reading, as of the run
    except Exception as exc:  # noqa: BLE001
        rep["tml"] = {"lines": [f"Tennis My Life status unknown ({type(exc).__name__}: {exc})"]}
    DC.write_json(Path(run_dir) / "continuity.json", rep)
    LEDGER.mkdir(parents=True, exist_ok=True)
    with (LEDGER / "checks.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({k: rep.get(k) for k in ("run", "checked_at", "first_check", "finished_now", "in_ledger",
                                                      "found", "failed")} |
                            {"missing": len(rep.get("missing") or []),
                             "removed_by_tml": len(rep.get("removed_by_tml") or [])}) + "\n")
    return rep
