"""Step 4, tables: today's tables in the run's work tree, with the live rows.

prediction_run/run.py's preparation (its own step list, run.stage0_steps, run unchanged: Stage 0 with the live rows and
the decided box-score overrides and fills, the accepted lower-level packages, the live rows' check, the level layer
resolved on this Stage 0, Stage 1's odds with the live prices, the links and the timeline with the live days and
windows), without the steps that reach no input (the daily_update_speed scoping, re-checked there for the IOS source):
    stage0_checks     reports only
    timing_check      reports only
    timing_features   match_timing/rebuild.py: its columns are replaced by the surface IOS; only checks read them
A replay holds the timeline at the instance's (its build tree's timing.parquet), as the 10 Oct layer replay did
(sources were restaged after the freeze; the played matches keep their days: "training" dating), so the steps that only
build the timeline (links, remap, timing, the live and the packages' windows) are skipped there.
A replay's tables are the instance's own (16 Oct 2026): its Stage 0 is built on the instance's dump view (the work
tree's), the additions step merges the additions the instance's build merged (the run's replay_tables.json, not today's
accepted.json), and before that merge the copied timeline is made the instance's (training dating: hold_timeline,
then again after the steps) or trimmed to the tree's Stage 0 (live dating). The copied timeline is the repository's
current one, which since 13 Oct holds matches a frozen dump lacks; 43 of them are in the lower-level feed, and the merge
would add their rows a second time.
A live run's live rows' check runs with --leave-out (since 28 Oct 2026: the owner's "a single row shouldnt hold up the
whole pipeline"; docs/decisions/2026-10-28-one-bad-match-left-out.md), right after Stage 0 (the precheck) and again
after the additions step: a match it cannot place is taken out of the live rows, the meta and the prices (dp_leftout),
the timeline is put back as the work tree had it (the additions step appends to it), and the steps run again from Stage
0, so the other matches' tables are those of a run whose CSV did not list it. A replay's check still stops the run.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

import dp_common as DC
import dp_worktree as WT

SKIP = ("stage0_checks", "timing_check", "timing_features")
SKIP_REPLAY = ("remap", "links", "live_links", "timing", "live_window", "additions_window")
LEFT_OUT_EXIT = 3          # prediction_run/inject.py check --leave-out: some live matches cannot be placed
REBUILDS = 3               # Stage 0 built again at most this many times, each without the matches its check left out
TIMELINE_COPY = "timing_before_tables.parquet"     # in <box>/run: the work tree's timeline before the additions step


def steps(has_overrides: bool, hold: bool, leave_out: bool = False) -> list[tuple[str, str, list[str]]]:
    """leave_out (a live run): the live rows' check lists the matches it cannot place instead of stopping, and it runs
    once more right after Stage 0 ("precheck"), before the additions step, whose merge takes 200-550 s: every cause the
    check names is Stage 0's, so a match left out there costs one Stage 0 build. The check after the additions stays,
    for a live row the additions step changed."""
    from src.eda.prediction_run import run as RUN            # the repository's (this process runs from it)
    skip = set(SKIP) | (set(SKIP_REPLAY) if hold else set())
    todo = [s for s in RUN.stage0_steps(has_overrides, layer=True) if s[0] not in skip]
    if not leave_out:
        return todo
    check = next(s for s in todo if s[0] == "check")
    out = []
    for n, s, a in todo:
        out.append((n, s, [*a, "--leave-out"] if n == "check" else a))
        if n == "stage0":
            out.append(("precheck", check[1], [*check[2], "--leave-out"]))
    return out


def leave_out_unplaced(run_dir: Path, rdir: Path) -> list[dict]:
    """The matches the live rows' check could not place (<box>/run/inject.json), taken out of the work tree's live rows
    and meta and of the run folder's (its prices too), and recorded (dp_leftout, the step "tables")."""
    import dp_leftout as LO
    left = (DC.read_json(rdir / "inject.json").get("check") or {}).get("left_out") or []
    why = {str(r["match_id"]): str(r["reason"]) for r in left}
    meta = pd.read_parquet(rdir / "live_meta.parquet")
    meta["match_id"] = meta["match_id"].astype(str)
    gone = meta[meta["match_id"].isin(set(why))]
    if len(gone) != len(why) or "csv_row" not in gone.columns or gone["csv_row"].isna().any():
        raise SystemExit(f"tables: the check left out matches the run cannot find by their CSV row: {sorted(why)}")
    for folder in (rdir, run_dir):
        LO.drop(folder, gone["csv_row"])
    LO.add(run_dir, "tables", matches=LO.from_meta(gone, why))
    return [{"match_id": k, "reason": v} for k, v in why.items()]


def earlier_unplaced(run_dir: Path, rdir: Path) -> int:
    """The earlier rounds from TennisLive that the live rows' check found no match of in Stage 0 under the id predicted
    for them (its earlier_rounds' not_in_stage0), recorded (dp_leftout): their player's match is predicted without
    them, and the gate decides on it as before."""
    import dp_leftout as LO
    er = (DC.read_json(rdir / "inject.json").get("check") or {}).get("earlier_rounds") or {}
    gone = [str(x) for x in er.get("not_in_stage0") or []]
    if not gone or not (rdir / "played_meta.parquet").exists():
        return 0
    pm = pd.read_parquet(rdir / "played_meta.parquet")
    pm = pm.assign(match_id=pm["match_id"].astype(str)).drop_duplicates("match_id").set_index("match_id")
    recs = []
    for mid in gone:
        e = pm.loc[mid] if mid in pm.index else pd.Series(dtype=object)
        recs.append({"tour": e.get("tour"), "tourney_id": mid.split("|")[1] if "|" in mid else None,
                     "tourney_name": e.get("tournament_name"), "round": e.get("round"), "winner": e.get("winner"),
                     "loser": e.get("loser"), "tl_url": e.get("tl_url"), "match_id": mid,
                     "reason": "the run's Stage 0 holds no match under the id predicted for it, so its result may be "
                               "missing from its player's inputs"})
    LO.add(run_dir, "tables", earlier=recs)
    return len(recs)


def layer_env(box: Path) -> dict:
    from src.eda.current_best_model import layer_config as LCF
    p = LCF.build_config(box)
    LCF.require_resolved(p, box)
    return {"LLE_LAYER": str(p)}


def hold_timeline(box: Path, base_tree: Path) -> dict:
    """The work tree's timeline set to the instance's on every match of the work tree's Stage 0."""
    t = pd.read_parquet(Path(base_tree) / DC.MT / "timing.parquet")
    t["match_id"] = t["match_id"].astype(str)
    m = pd.read_parquet(box / DC.PD / "stage0_matches.parquet", columns=["match_id"])
    ids = set(m["match_id"].astype(str))
    missing = sorted(ids - set(t["match_id"]))
    if missing:
        raise SystemExit(f"hold: {len(missing)} of the work tree's matches are not in the instance's timeline "
                         f"(first: {missing[:3]})")
    held = t[t["match_id"].isin(ids)].reset_index(drop=True)
    path = box / DC.MT / "timing.parquet"
    part = path.with_name(path.name + ".part")
    held.to_parquet(part, index=False)
    os.replace(part, path)
    return {"rows": int(len(held)), "of_instance_rows": int(len(t)), "sha256": DC.sha256(path),
            "source": str(Path(base_tree) / DC.MT / "timing.parquet")}


def trim_timeline(box: Path) -> dict:
    """The work tree's timeline cut to the matches of its own Stage 0 (a live-dated replay, before the merge)."""
    m = pd.read_parquet(box / DC.PD / "stage0_matches.parquet", columns=["match_id"])
    ids = set(m["match_id"].astype(str))
    path = box / DC.MT / "timing.parquet"
    t = pd.read_parquet(path)
    keep = t["match_id"].astype(str).isin(ids).to_numpy()
    part = path.with_name(path.name + ".part")
    t[keep].reset_index(drop=True).to_parquet(part, index=False, compression="zstd")
    os.replace(part, path)
    return {"rows": int(keep.sum()), "dropped": int((~keep).sum()), "sha256": DC.sha256(path)}


def replay_steps(steps: list[tuple[str, str, list[str]]], additions_list: Path) -> list[tuple[str, str, list[str]]]:
    """A replay's steps: the additions step and the packages' window merge the instance's list, not accepted.json."""
    return [(n, s, [*a, "--accepted-json", str(additions_list)] if n in ("additions", "additions_window") else a)
            for n, s, a in steps]


def history_check(box: Path) -> dict:
    """current_best_model/history.py's check of the work tree's Stage 0 and timeline against the frozen reference (a
    report: nothing reads it to build an input)."""
    import time

    from src.eda.current_best_model import history as H
    t0 = time.time()
    res = H.check(box / DC.PD, box / DC.MT / "timing.parquet")
    return {"history": {k: v for k, v in res.items() if k != "feeds"}, "history_line": H.summary_line(res),
            "history_seconds": round(time.time() - t0, 1)}


def prep(run_dir: Path, box: Path, replay: bool, base_tree: Path = DC.BASE_TREE, hold: bool | None = None,
         history: bool = True, replay_additions: dict | None = None) -> dict:
    """The preparation in the work tree; the live rows, meta and overrides come from the run's folder. hold (default:
    a replay): the instance's timeline instead of the timeline steps (the exact replay, "training" dating); a replay
    dated as live builds the timeline as a live run does (a smoke test of those steps, not an exactness test).
    replay_additions (a replay's, required there): the additions the instance's build merged, in accepted.json's form.
    history False: the history check is left to the caller (run_day runs it beside the states step)."""
    hold = replay if hold is None else hold
    if replay and replay_additions is None:
        raise SystemExit("a replay merges the instance's own additions: pass them (dp_common.replay_tables)")
    if not (box / WT.MARKER).exists():
        raise SystemExit(f"no work tree at {box}: dp.py worktree")
    rdir = box / "run"
    if rdir.exists():
        raise SystemExit(f"{rdir} exists: this work tree has built a run already (dp.py cleanup, worktree)")
    (rdir / "stage0_before").mkdir(parents=True)
    for f in ("live_rows.parquet", "live_meta.parquet", "played_meta.parquet", "overrides.csv"):
        if (run_dir / f).exists():
            shutil.copy2(run_dir / f, rdir / f)
    for f in ("stage0_matches.parquet", "stage0_match_players.parquet"):
        shutil.copy2(box / DC.PD / f, rdir / "stage0_before" / f)
    record: dict = {"work_tree": str(box), "replay": replay, "timeline_held": hold, "steps": []}
    todo = steps((rdir / "overrides.csv").exists(), hold, leave_out=not replay)
    if replay:
        additions_list = rdir / "accepted_for_replay.json"
        DC.write_json(additions_list, replay_additions)
        record["replay_additions"] = replay_additions
        todo = replay_steps(todo, additions_list)
    else:                                  # the additions step appends to the timeline: a second Stage 0 starts from this
        shutil.copy2(box / DC.MT / "timing.parquet", rdir / TIMELINE_COPY)
    env: dict = {}
    names = [n for n, _, _ in todo]
    k = 0
    while k < len(todo):
        name, script, args = todo[k]
        code = WT.run(box, name, script, args, env=env, record=record["steps"])
        if (name in ("precheck", "check") and code == LEFT_OUT_EXIT and not replay
                and record.get("stage0_rebuilt", 0) < REBUILDS):    # matches it cannot place: Stage 0 without them
            record.setdefault("left_out", []).extend(leave_out_unplaced(run_dir, rdir))
            shutil.copy2(rdir / TIMELINE_COPY, box / DC.MT / "timing.parquet")
            record["stage0_rebuilt"] = record.get("stage0_rebuilt", 0) + 1
            DC.log(f"!!! Stage 0 built again without the {len(record['left_out'])} match(es) left out")
            k = names.index("stage0")
            continue
        if code != 0:
            record["failed"] = name
            return record
        if name == "lle_layer":
            env = layer_env(box)
            record["lle_layer"] = env["LLE_LAYER"]
        if replay and name == "stage0":                   # the timeline the merge meets: the instance's, or trimmed
            record["timeline_before_additions"] = hold_timeline(box, base_tree) if hold else trim_timeline(box)
        k += 1
    if not replay:
        record["earlier_rounds_not_in_stage0"] = earlier_unplaced(run_dir, rdir)
    if hold:
        record["timeline_held"] = hold_timeline(box, base_tree)
    if history:
        record.update(history_check(box))
    else:
        record["history_line"] = "run beside the states step (history.json)"
    return record
