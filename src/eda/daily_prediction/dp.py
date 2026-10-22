"""The daily prediction script, phase 1 (docs/studies/daily_prediction/README.md; the plan:
docs/studies/prediction_pipeline/PLAN.md sections 2, 3 and 7). One command per step; run_day chains them.

Steps (each writes into the run's folder; a step that reads a tree's tables runs inside that tree):
    worktree    a fresh work tree (sandbox copy of the repository, the prediction run's licence for live rows), with
                the checkpoint's constants installed; --replay: Tennis My Life's dump held at the freeze
    refresh     box scores first: prediction_run's refresh (Tennis My Life, Stage 0 on it, the gaps, the WTA fills)
    matchups    the day's matches as live rows: a CSV (prediction_run's columns), or --replay WEEK ROUND (a past day's
                first-day matches, their outcome removed)
    prices      each match's margin-free chance of side A: the CSV's p_a (live), the instance's own price (replay)
    tables      in the work tree: Stage 0 with the live rows and the decided overrides, the accepted packages, the level
                layer resolved, Stage 1's odds, the timeline (replay: the instance's timeline held); not the steps that
                reach no input (Stage 0's and the timeline's checks, the leak-proof features)
    history     the history check against the frozen reference (a report; run_day runs it beside the states step)
    states      in the work tree: each family resumed from the checkpoint (or recomputed where its history changed),
                the 57 inputs of the live matches, the gate (the surface IOS and Stage B's forms in processes of their
                own, beside the rest)
    fit         the GPU: 16 seeds, every live match at 91 prices and its own, both orientations; each seed's TabPFN
                training cache read from disk (built the first time: dp_tabcache), or --fit-cache off
    thinking    only a run made with --thinking (20 Oct 2026; dp_thinking): TabPFN-3.5-Thinking's ONE paid prediction of
                the same rows on the instance's season fit (the hosted API, --spend-tokens), uncalibrated
    predict     the seed mean, stage 2, the prediction file and its provenance; with Thinking, the prediction used is
                the local model's chance and Thinking's averaged 50/50 in log-odds (the patterns, while on, added after)
    grade       after results: each prediction against its result and the market
    run_day     all of the above in order (refresh optional), each step's time recorded
Checkpoints: checkpoint --tree T --day D (every family's state before D on a tree's tables).

Run: ./python.sh src/eda/daily_prediction/dp.py <step> --run <folder> [options]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import dp_common as DC  # noqa: E402


def cmd_checkpoint(a) -> int:
    tree = Path(a.tree)
    read_only = not (tree / ".prediction_run_sandbox").exists()
    DC.enter_tree(tree, read_only=read_only)
    import dp_state as SP
    import dp_store as STR
    d0 = DC.day_of(a.day)
    ck = STR.folder(DC.date_of(d0))
    man = SP.make_checkpoint(tree, d0, ck, workers=a.workers, made_from=a.note or "")
    print(json.dumps({"checkpoint": str(ck), "seconds": man["seconds"]}, indent=1))
    return 0


def cmd_tree_check(a) -> int:
    """The state path on a tree's own tables against an instance frame: every frame match after the checkpoint (whose
    earliest start is on or after its day), its 57 inputs from the checkpoint (or in full) against the frame's."""
    import numpy as np
    import pandas as pd
    tree = Path(a.tree)
    DC.enter_tree(tree, read_only=True)
    import dp_state as SP
    import dp_store as STR
    ck = STR.folder(a.day) if not a.full else None
    d0 = DC.day_of(a.day)
    frame = pd.read_parquet(Path(a.frame))
    frame["match_id"] = frame["match_id"].astype(str)
    timing = pd.read_parquet(tree / DC.MT / "timing.parquet", columns=["match_id", "es"]).astype({"match_id": str})
    es = timing.set_index("match_id")["es"].reindex(frame["match_id"]).to_numpy()
    pick = (pd.to_datetime(frame["tournament_date"]) >= pd.Timestamp(a.day)).to_numpy() & (es >= d0)
    if a.limit:
        pick &= np.cumsum(pick) <= a.limit
    tg = frame[pick].reset_index(drop=True)
    got, rec = SP.inputs(tree, True, d0, ck, tg["match_id"].to_numpy(), tg["p_mkt"].to_numpy(), workers=a.workers)
    names = SP.model_names()
    res = {}
    for n in names:
        res[n] = DC.compare(got[f"in_{n}"].to_numpy(), tg[f"in_{n}"].to_numpy())
    out = {"tree": str(tree), "frame": a.frame, "checkpoint": None if ck is None else str(ck), "matches": int(len(tg)),
           "inputs_bitwise": int(sum(DC.bitwise(v) for v in res.values())), "inputs": len(names),
           "max_abs_diff": max(v["max_abs_diff"] for v in res.values()),
           "not_bitwise": {k: v for k, v in res.items() if not DC.bitwise(v)}, "record": rec}
    path = DC.OUT / "checks" / f"tree_check_{a.day}{'_full' if a.full else ''}{a.tag}.json"
    DC.write_json(path, out)
    print(json.dumps({k: out[k] for k in ("matches", "inputs_bitwise", "inputs", "max_abs_diff")}, indent=1))
    print(json.dumps({k: (v["bitwise_equal"], v["rows"], v["max_abs_diff"]) for k, v in out["not_bitwise"].items()}))
    print(json.dumps(rec["seconds"]))
    return 0 if out["inputs_bitwise"] == out["inputs"] else 1


def _run(a) -> Path:
    p = Path(a.run)
    return p if p.is_absolute() else DC.REPO / p


def _print(res) -> int:
    print(json.dumps(res, indent=1, default=str)[:6000])
    return 0


def cmd_init(a) -> int:
    import dp_steps as S
    replay = None
    if a.replay_week:
        replay = {"week": a.replay_week, "round": a.replay_round, "winner": a.replay_winner,
                  "dating": a.replay_dating}
        if a.replay_frame:                           # a frame holding rows the instance's lacks (a qualifying replay)
            replay["frame"] = str(Path(a.replay_frame).resolve())
        if a.replay_main_date:                       # a qualifying replay's main-draw start, in place of the instance's
            replay["main_date"] = a.replay_main_date
    elif not a.matchups:
        raise SystemExit("init: --matchups CSV (live) or --replay-week (replay)")
    if a.thinking and not a.spend_tokens:
        raise SystemExit("--thinking: TabPFN-3.5-Thinking's prediction is a paid call: pass --spend-tokens too")
    return _print(S.init(_run(a), "replay" if replay else "live", replay, a.matchups, a.checkpoint, a.seeds,
                         thinking=a.thinking))


def cmd_step(a) -> int:
    import dp_steps as S
    run_dir = _run(a)
    t0 = time.time()
    if a.cmd == "worktree":
        res = S.step_worktree(run_dir)
    elif a.cmd == "refresh":
        res = S.step_refresh(run_dir, not a.no_download, a.max_requests)
    elif a.cmd == "matchups":
        res = S.step_matchups(run_dir, a.inside)
    elif a.cmd == "prices":
        res = S.step_prices(run_dir)
    elif a.cmd == "tables":
        res = S.step_tables(run_dir)
    elif a.cmd == "history":
        res = S.step_history(run_dir)
    elif a.cmd == "states":
        res = S.step_states(run_dir, a.inside, a.workers, a.full)
    elif a.cmd == "fit":
        res = S.step_fit(run_dir, a.seeds or S.run_config(run_dir)["seeds"], a.direct_seeds, a.fit_cache)
    elif a.cmd == "thinking":
        res = S.step_thinking(run_dir, a.spend_tokens)
    elif a.cmd == "thinking-send":                   # the paid call's part, in the hosted API's environment
        import dp_thinking as TK
        res = TK.send(run_dir, a.spend_tokens)
    elif a.cmd == "predict":
        res = S.step_predict(run_dir, a.seeds or S.run_config(run_dir)["seeds"])
    elif a.cmd == "grade":
        res = S.step_grade(run_dir)
    elif a.cmd == "replay-compare":
        res = S.replay_compare(run_dir)
        res = {k: v for k, v in res.items() if k != "per_input"}
    elif a.cmd == "reprice":
        if not a.prices:
            raise SystemExit("reprice: --prices CSV (match_id, p_a)")
        res = S.reprice(run_dir, Path(a.prices))
    else:
        raise SystemExit(a.cmd)
    if not getattr(a, "inside", False) and a.cmd not in ("replay-compare", "thinking-send"):
        S.record(run_dir, a.cmd, {"seconds": round(time.time() - t0, 1), "result": res})
    return _print(res)


def cmd_run_day(a) -> int:
    import dp_steps as S
    run_dir = _run(a)
    if not (run_dir / "run.json").exists():
        cmd_init(a)
    elif a.thinking and not S.run_config(run_dir).get("thinking"):
        raise SystemExit(f"{run_dir} was made without --thinking: Thinking needs a new run folder")
    res = S.run_day(run_dir, a.refresh, not a.no_fit, a.keep_worktree, a.workers, a.direct_seeds, a.leave_checkpoint,
                    a.fit_cache, spend_tokens=a.spend_tokens)
    return _print(res)


def cmd_cleanup(a) -> int:
    import dp_worktree as WT
    return _print(WT.cleanup(Path(a.work_tree)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def run_args(p, init: bool = False):
        p.add_argument("--run", required=True, help="the run's folder (default root data/studies/daily_prediction/runs)")
        if init:
            p.add_argument("--matchups", default=None, help="live: CSV of the day's matches (prediction_run's columns)")
            p.add_argument("--replay-week", default=None, help="replay: the Monday of the week replayed")
            p.add_argument("--replay-round", default="R16")
            p.add_argument("--replay-winner", default="A", choices=["A", "B"])
            p.add_argument("--replay-dating", default="training", choices=["training", "live"],
                           help="training: the exact replay (the instance's timeline held); live: dated as upcoming "
                                "matches are, the live timeline steps run (a smoke test, not exact)")
            p.add_argument("--replay-frame", default=None,
                           help="replay: a frame (match_id, p_mkt, odds_input, in_<inputs>) that holds the replayed "
                                "matches, for their selection, prices and comparison (default the instance's "
                                "model_frame.parquet, main draws only; a qualifying round needs one)")
            p.add_argument("--replay-main-date", default=None,
                           help="a qualifying replay: the main-draw start (YYYY-MM-DD) every live row names, in place "
                                "of the instance's own date of its event (to measure a live estimate's error)")
            p.add_argument("--checkpoint", default="auto", help="a checkpoint day, or auto (the latest before the matches)")
            p.add_argument("--seeds", default="0-15")
            p.add_argument("--thinking", action="store_true",
                           help="also TabPFN-3.5-Thinking (hosted, paid, uncalibrated) on the same rows; the prediction "
                                "used is the two models' chances averaged 50/50 in log-odds (needs --spend-tokens)")
            p.add_argument("--spend-tokens", action="store_true",
                           help="allow the paid TabPFN-3.5-Thinking call of --thinking (owner approval)")
    i = sub.add_parser("init", help="a run's folder and run.json")
    run_args(i, init=True)
    i.set_defaults(func=cmd_init)
    for name, help_ in (("worktree", "a fresh work tree with the checkpoint's constants"),
                        ("refresh", "box scores first (prediction_run's refresh)"),
                        ("matchups", "the day's matches as live rows"), ("prices", "each match's margin-free price"),
                        ("tables", "today's tables in the work tree"),
                        ("history", "the history check on the work tree's tables (run_day: beside the states step)"),
                        ("states", "the 57 inputs and the gate"),
                        ("fit", "the GPU's price grid"),
                        ("thinking", "a --thinking run: TabPFN-3.5-Thinking's one paid prediction (--spend-tokens)"),
                        ("thinking-send", "internal: the thinking step's paid call, in the hosted API's environment"),
                        ("predict", "stage 2 and the prediction file"),
                        ("grade", "predictions against results"),
                        ("replay-compare", "a replay's inputs against the instance frame"),
                        ("reprice", "new prices read off the run's curves (no refit)")):
        p = sub.add_parser(name, help=help_)
        run_args(p)
        p.add_argument("--inside", action="store_true", help=argparse.SUPPRESS)
        p.add_argument("--workers", type=int, default=7)
        p.add_argument("--seeds", default=None)
        p.add_argument("--direct-seeds", default="")
        p.add_argument("--no-download", action="store_true")
        p.add_argument("--max-requests", type=int, default=300)
        p.add_argument("--prices", default=None, help="reprice: CSV of match_id, p_a")
        p.add_argument("--full", action="store_true", help="states: every part from scratch (tier 2), no checkpoint")
        p.add_argument("--fit-cache", default="use", choices=["use", "rebuild", "off"],
                       help="fit: each seed's TabPFN training cache on disk (use: built when missing or stale), or "
                            "off: the decided path (the training rows processed at this call)")
        p.add_argument("--spend-tokens", action="store_true", help="thinking: allow its paid call")
        p.set_defaults(func=cmd_step)
    r = sub.add_parser("run_day", help="every step in order, each one's time recorded")
    run_args(r, init=True)
    r.add_argument("--refresh", action="store_true", help="live: download and fill box scores first")
    r.add_argument("--no-fit", action="store_true", help="stop after the inputs and the gate")
    r.add_argument("--keep-worktree", action="store_true")
    r.add_argument("--workers", type=int, default=7)
    r.add_argument("--direct-seeds", default="", help="seeds that also predict each match's own price alone")
    r.add_argument("--leave-checkpoint", default="auto", choices=["auto", "yes", "no"],
                   help="live: a checkpoint on the day's tables for the next days (auto: when this one fell back or "
                        "aged)")
    r.add_argument("--fit-cache", default="use", choices=["use", "rebuild", "off"],
                   help="the fit's TabPFN training caches (see fit --fit-cache)")
    r.set_defaults(func=cmd_run_day)
    cl = sub.add_parser("cleanup", help="delete the work tree")
    cl.add_argument("--work-tree", default=str(DC.WORK_TREE))
    cl.set_defaults(func=cmd_cleanup)
    c = sub.add_parser("checkpoint", help="every family's state before a day, on a tree's tables")
    c.add_argument("--tree", default=str(DC.BASE_TREE))
    c.add_argument("--day", required=True)
    c.add_argument("--workers", type=int, default=7)
    c.add_argument("--note", default="")
    c.set_defaults(func=cmd_checkpoint)
    t = sub.add_parser("tree-check", help="the state path on a tree's own tables against its instance frame")
    t.add_argument("--tree", default=str(DC.BASE_TREE))
    t.add_argument("--day", required=True)
    t.add_argument("--frame", default=str(DC.INSTANCE / "model_frame.parquet"))
    t.add_argument("--full", action="store_true", help="every family in full (no checkpoint)")
    t.add_argument("--limit", type=int, default=0)
    t.add_argument("--workers", type=int, default=7)
    t.add_argument("--tag", default="")
    t.set_defaults(func=cmd_tree_check)
    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
