"""The steps of a run (dp.py's commands). A run is a folder holding run.json (what it is) and every step's output.

Where each step runs:
    repository process     worktree, refresh, matchups (live), prices, tables (it drives the work tree by
                           subprocesses), predict, grade, run_day
    inside the work tree   matchups (replay: the work tree's frozen dump), states (today's tables): dp.py re-runs
                           itself with the work tree's copy of this package, so the builders it imports are the work
                           tree's and so are their tables
    the GPU environment    fit (tennis-tabpfn-local)
    the API environment    thinking's paid call (tennis-tabpfn; dp_thinking: its query and read-back run here)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

import dp_common as DC

ACE_ROWS = "ios_ace_recent.parquet"     # the states step's ace ratings (dp_state.write_ace_rows), read by step_patterns
REPLAY_TABLES = "replay_tables.json"    # a replay's dump view and the instance's additions (dp_common.replay_tables)


def repo_imports() -> None:
    """The repository's `src` for a step that runs in the repository's process (never before a tree in a process
    that entered one: `src` is a namespace package, resolved in sys.path order)."""
    if str(DC.REPO) not in sys.path:
        sys.path.append(str(DC.REPO))


def span(text: str) -> list[int]:
    out = []
    for part in str(text).split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def run_config(run_dir: Path) -> dict:
    p = run_dir / "run.json"
    if not p.exists():
        raise SystemExit(f"{p} missing: start the run with run_day, or `dp.py init`")
    return DC.read_json(p)


def init(run_dir: Path, mode: str, replay: dict | None, csv: str | None, checkpoint: str, seeds: str,
         work_tree: Path = DC.WORK_TREE, thinking: bool = False) -> dict:
    """thinking: TabPFN-3.5-Thinking beside the local model (dp_thinking; a paid call), recorded in run.json."""
    if not (DC.INSTANCE / "model_frame.parquet").exists():
        raise SystemExit(f"no instance at {DC.INSTANCE} (DP_INSTANCE names the folder under "
                         "data/studies/current_best_model/)")
    run_dir.mkdir(parents=True, exist_ok=True)
    cfg = {"created_at": DC.stamp(), "mode": mode, "replay": replay, "matchups_csv": csv, "checkpoint": checkpoint,
           "seeds": seeds, "work_tree": str(work_tree), "instance": str(DC.INSTANCE), "base_tree": str(DC.BASE_TREE)}
    if thinking:
        cfg["thinking"] = True
    DC.write_json(run_dir / "run.json", cfg)
    return cfg


def replay_frame(cfg: dict) -> Path:
    """A replay's frame: the one run.json names (--replay-frame: rows the instance frame lacks, e.g. a qualifying
    round's), else the instance's own."""
    given = (cfg.get("replay") or {}).get("frame")
    return Path(given) if given else Path(cfg["instance"]) / "model_frame.parquet"


def record(run_dir: Path, step: str, value: dict) -> None:
    p = run_dir / "steps.json"
    d = DC.read_json(p) if p.exists() else {}
    d[step] = value
    DC.write_json(p, d)


def in_tree(box: Path, args: list[str], env: dict | None = None, log: Path | None = None) -> int:
    """dp.py <args> with the work tree's copy of this package (its builders, its tables)."""
    script = box / "src" / "eda" / "daily_prediction" / "dp.py"
    if not script.exists():
        raise SystemExit(f"{script} missing: the work tree predates this package")
    cmd = [str(DC.PY), str(script), *args]
    full_env = {**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})}
    if log is None:
        return subprocess.run(cmd, cwd=box, env=full_env).returncode
    with open(log, "w", encoding="utf-8") as fh:
        return subprocess.run(cmd, cwd=box, env=full_env, stdout=fh, stderr=subprocess.STDOUT).returncode


# ------------------------------------------------------------------------------------------------

def choose_checkpoint(cfg: dict, run_dir: Path) -> Path:
    """The run's checkpoint: the day named, or the latest whose day is on or before the earliest live match's
    tournament week (the checkpoint must cover only history)."""
    import dp_store as STR
    if cfg["checkpoint"] not in (None, "", "auto"):
        ck = STR.folder(cfg["checkpoint"])
        if not (ck / "manifest.json").exists():
            raise SystemExit(f"no checkpoint {ck}")
        return ck
    meta = pd.read_parquet(run_dir / "live_meta.parquet") if (run_dir / "live_meta.parquet").exists() else None
    first = DC.day_of(pd.to_datetime(meta["day"]).min()) - 7 if meta is not None else DC.day_of(pd.Timestamp.now())
    cands = STR.latest_on_or_before(first)
    if not cands:
        raise SystemExit("no checkpoint on or before the live matches: build one (dp.py checkpoint)")
    return cands[0]


def step_worktree(run_dir: Path) -> dict:
    """The work tree. A replay's is built on the instance's own dump view, and the view and the additions the
    instance's build merged are recorded in <run>/replay_tables.json, which the tables step merges (16 Oct 2026). Since
    22 Oct 2026 a replay also reads the decided correction tables of the instance's build tree (DC.BASE_TREE's copy,
    recorded there as "fixes"), so corrections decided after the instance was built do not reach its replay."""
    import dp_store as STR
    import dp_worktree as WT
    cfg = run_config(run_dir)
    box = Path(cfg["work_tree"])
    freeze, fixes = None, None
    if cfg["mode"] == "replay":
        rt = DC.replay_tables(Path(cfg["instance"]))
        own = DC.BASE_TREE / WT.FIXES
        if own.is_dir():
            fixes = own
            rt["fixes"] = str(own)
            rt["fixes_sha256"] = {f.name: DC.sha256(f) for f in sorted(own.glob("*.csv"))}
        DC.write_json(run_dir / REPLAY_TABLES, rt)
        freeze = Path(rt["dump_view"])
    rec = WT.setup(box, replay=cfg["mode"] == "replay", freeze=freeze, owner=str(run_dir), fixes=fixes)
    ck = choose_checkpoint(cfg, run_dir) if (run_dir / "live_meta.parquet").exists() else (
        STR.folder(cfg["checkpoint"]) if cfg["checkpoint"] not in (None, "", "auto") else STR.checkpoints()[0])
    rec["constants_from"] = str(ck)
    rec["constants_replaced"] = STR.install_constants(ck, box, STR.read_manifest(ck))
    return rec


def step_refresh(run_dir: Path, download: bool, max_requests: int) -> dict:
    repo_imports()
    from src.eda.prediction_run import run as RUN
    code = RUN.refresh(run_dir, None, download, max_requests)
    if code:
        raise SystemExit(f"refresh failed ({code}): {run_dir / 'refresh.json'}")
    return DC.read_json(run_dir / "refresh.json")


def step_matchups(run_dir: Path, inside: bool = False) -> dict:
    import dp_matchups as MU
    cfg = run_config(run_dir)
    if cfg["mode"] == "live":
        repo_imports()
        import shutil
        shutil.copy2(cfg["matchups_csv"], run_dir / "matchups.csv")   # the CSV as read (the prices step reads it too)
        rec = MU.live(run_dir, run_dir / "matchups.csv")
        from src.eda.prediction_run import run as RUN
        rec["wta_calendar"] = RUN.wta_calendar(pd.read_csv(run_dir / "matchups.csv"), 300)
        return rec
    if not inside:                                      # a replay reads the work tree's frozen dump
        box = Path(cfg["work_tree"])
        code = in_tree(box, ["matchups", "--run", str(run_dir), "--inside"], log=run_dir / "matchups_inside.log")
        if code:
            raise SystemExit(f"matchups failed inside the work tree: {run_dir / 'matchups_inside.log'}")
        return DC.read_json(run_dir / "replay.json")
    DC.use_tree(Path(cfg["work_tree"]))
    r = cfg["replay"]
    rec = MU.replay(run_dir, r["week"], r["round"], r.get("winner", "A"), Path(cfg["base_tree"]),
                    replay_frame(cfg), r.get("dating", "training"), **({"main_date": r["main_date"]}
                                                                       if r.get("main_date") else {}))
    DC.write_json(run_dir / "replay.json", rec)
    return rec


def step_prices(run_dir: Path) -> dict:
    import dp_matchups as MU
    cfg = run_config(run_dir)
    if cfg["mode"] == "replay":
        return MU.prices(run_dir, replay_frame(cfg))
    return MU.prices(run_dir, None, run_dir / "matchups.csv")


def step_tables(run_dir: Path, history: bool = True) -> dict:
    """history False: without the history check (run_day starts it with start_history beside the states step)."""
    repo_imports()
    import dp_tables as TB
    cfg = run_config(run_dir)
    exact = cfg["mode"] == "replay" and (cfg.get("replay") or {}).get("dating", "training") == "training"
    replay_add = None
    if cfg["mode"] == "replay":
        if not (run_dir / REPLAY_TABLES).exists():
            raise SystemExit(f"{run_dir / REPLAY_TABLES} missing: run the worktree step again (it records the "
                             "instance's dump view and additions)")
        replay_add = DC.read_json(run_dir / REPLAY_TABLES)["additions"]
    rec = TB.prep(run_dir, Path(cfg["work_tree"]), cfg["mode"] == "replay", Path(cfg["base_tree"]), hold=exact,
                  history=history, replay_additions=replay_add)
    DC.write_json(run_dir / "tables.json", rec)
    if rec.get("failed"):
        raise SystemExit(f"tables: step {rec['failed']} failed (its log: {Path(cfg['work_tree']) / 'logs'})")
    return {"steps": {s["step"]: s["seconds"] for s in rec["steps"]}, "history": rec.get("history_line"),
            "timeline_held": rec.get("timeline_held")}


def step_history(run_dir: Path) -> dict:
    """The history check on the work tree's tables (after the tables step): history.json, and its fields into
    tables.json where the tables step records them when it runs the check itself."""
    repo_imports()
    import dp_tables as TB
    cfg = run_config(run_dir)
    res = TB.history_check(Path(cfg["work_tree"]))
    DC.write_json(run_dir / "history.json", res)
    tab = DC.read_json(run_dir / "tables.json")
    tab.update(res)
    DC.write_json(run_dir / "tables.json", tab)
    return {"history": res["history_line"], "seconds": res["history_seconds"]}


def start_history(run_dir: Path) -> subprocess.Popen:
    """step_history in its own process, beside the states step: it reads the work tree's Stage 0 and timeline, which
    nothing after the tables step writes, and nothing reads its result to build an input."""
    fh = open(run_dir / "history.log", "w", encoding="utf-8")
    return subprocess.Popen([str(DC.PY), str(DC.HERE / "dp.py"), "history", "--run", str(run_dir)], cwd=DC.REPO,
                            stdout=fh, stderr=subprocess.STDOUT, env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def join_history(proc: subprocess.Popen, run_dir: Path) -> dict:
    if proc.wait() != 0:
        raise SystemExit(f"history check failed: {run_dir / 'history.log'}")
    res = DC.read_json(run_dir / "history.json")
    return {"history": res["history_line"], "ran_seconds": res["history_seconds"]}


def side_names(matches: pd.DataFrame, players: pd.DataFrame) -> pd.DataFrame:
    """The matches' rows with each side's name added (player_a_name, player_b_name) from Stage 0's own player rows by
    side: the name each live row was built with, on the side Stage 0 gave that player. predictions.csv reads these and
    never the matchups CSV's names: a CSV's player_a is Stage 0's side B whenever its id sorts higher, and
    prediction_run's live_from_matchups turns the price to side A's but keeps the CSV's names (reported by the
    tennis-predictions-fc session, 11 Oct 2026). Refuses a match whose player rows do not give one A and one B with the
    match row's ids."""
    m = matches.astype({"match_id": str}).set_index("match_id")
    p = players.astype({"match_id": str})
    p = p[p["match_id"].isin(set(m.index))]
    a, b = (p[p["side"].eq(s)].set_index("match_id") for s in ("A", "B"))
    if a.index.duplicated().any() or b.index.duplicated().any():
        raise RuntimeError("live matches: a side given twice in Stage 0's player rows")
    ids_a = a["player_id"].reindex(m.index).astype(str).to_numpy()
    ids_b = b["player_id"].reindex(m.index).astype(str).to_numpy()
    bad = (ids_a != m["player_a_id"].astype(str).to_numpy()) | (ids_b != m["player_b_id"].astype(str).to_numpy())
    if bad.any():
        raise RuntimeError(f"{int(bad.sum())} live matches: Stage 0's player rows disagree with the match rows on the "
                           f"sides (first: {m.index[bad][:3].tolist()})")
    m["player_a_name"] = a["player_name"].reindex(m.index).to_numpy()
    m["player_b_name"] = b["player_name"].reindex(m.index).to_numpy()
    return m.reset_index()


def step_states(run_dir: Path, inside: bool = False, workers: int = 7, full: bool = False) -> dict:
    cfg = run_config(run_dir)
    box = Path(cfg["work_tree"])
    if not inside:
        repo_imports()
        import dp_tables as TB
        code = in_tree(box, ["states", "--run", str(run_dir), "--inside", "--workers", str(workers)]
                       + (["--full"] if full else []), env=TB.layer_env(box), log=run_dir / "states_inside.log")
        if code:
            raise SystemExit(f"states failed inside the work tree: {run_dir / 'states_inside.log'}")
        return {k: v for k, v in DC.read_json(run_dir / "states.json").items() if k in ("checkpoint", "seconds",
                                                                                        "parts_summary", "gate")}
    DC.enter_tree(box, read_only=False)
    import dp_state as SP
    import dp_store as STR
    ck = None if full else choose_checkpoint(cfg, run_dir)        # full: every part from scratch (tier 2)
    d0 = None if full else int(STR.read_manifest(ck)["d0"])
    meta = pd.read_parquet(run_dir / "live_meta.parquet").astype({"match_id": str})
    pr = pd.read_parquet(run_dir / "prices.parquet").astype({"match_id": str}).set_index("match_id")
    targets = meta["match_id"].to_numpy()
    # ace_rows: the ace ratings of the live rows and of the history since the checkpoint, for the pattern step's venue
    # pace (16 Oct 2026); the 57 inputs are the same with or without it
    frame, rec = SP.inputs(box, False, d0, ck, targets, pr.loc[targets, "p_a"].to_numpy(dtype="float64"),
                           workers=workers, cache_dir=run_dir, ace_rows=run_dir / ACE_ROWS)
    frame.to_parquet(run_dir / "live_frame.parquet", index=False)
    from src.eda.predictability_diagnostic import common as C
    s0 = pd.read_parquet(C.MATCHES, columns=["match_id", "player_a_id", "player_b_id", "tournament_id",
                                              "tournament_date", "level", "round"]).astype({"match_id": str})
    s0 = s0[s0["match_id"].isin(set(targets))]
    players = pd.read_parquet(C.MATCH_PLAYERS, columns=["match_id", "player_id", "side", "player_name"])
    side_names(s0, players).to_parquet(run_dir / "live_stage0.parquet", index=False)
    from src.eda.prediction_run import gate as G
    gate = G.run(run_dir, box / DC.PD, box / DC.MT / "timing.parquet")
    parts = pd.Series(rec["parts"]).value_counts().to_dict()
    out = {"checkpoint": None if ck is None else str(ck), "record": rec, "parts_summary": parts, "seconds": rec["seconds"],
           "layer_config": os.environ.get("LLE_LAYER"), "layer_config_sha256": DC.sha256(os.environ["LLE_LAYER"]),
           "gate": {k: gate[k] for k in ("live_matches", "complete")}}
    DC.write_json(run_dir / "states.json", out)
    return out


def step_fit(run_dir: Path, seeds: str, direct: str = "", cache: str = "use") -> dict:
    """cache: "use" (each seed's training cache on disk, dp_tabcache), "rebuild", "off" (the decided path)."""
    if Path(sys.executable).resolve() != DC.PY_TABPFN.resolve():
        cmd = [str(DC.PY_TABPFN), str(DC.HERE / "dp.py"), "fit", "--run", str(run_dir), "--seeds", seeds,
               "--fit-cache", cache]
        if direct:
            cmd += ["--direct-seeds", direct]
        with open(run_dir / "fit.log", "w", encoding="utf-8") as fh:
            code = subprocess.run(cmd, cwd=DC.REPO, stdout=fh, stderr=subprocess.STDOUT,
                                  env={**os.environ, "PYTHONIOENCODING": "utf-8"}).returncode
        if code:
            raise SystemExit(f"fit failed: {run_dir / 'fit.log'}")
        return DC.read_json(run_dir / "fit.json")["summary"]
    import dp_fit as FT
    return FT.run(run_dir, span(seeds), Path(run_config(run_dir)["instance"]), direct_seeds=span(direct) if direct else [],
                  cache=cache)["summary"]


def step_thinking(run_dir: Path, spend_tokens: bool) -> dict:
    """TabPFN-3.5-Thinking's one paid prediction of the run's matches (dp_thinking): the query in this process, the call
    in the hosted API's environment, the answers read back and symmetrised here."""
    import dp_thinking as TK
    cfg = run_config(run_dir)
    if not cfg.get("thinking"):
        raise SystemExit("thinking: this run was made without --thinking")
    failed = TK.folder(run_dir) / "failed.json"             # an earlier attempt's failure: kept, renamed
    if failed.exists():
        failed.replace(failed.with_name(f"failed_{DC.stamp()}.json"))
    repo_imports()
    query = TK.build_query(run_dir, Path(cfg["instance"]))
    cmd = [str(DC.PY_API), str(DC.HERE / "dp.py"), "thinking-send", "--run", str(run_dir)]
    if spend_tokens:
        cmd.append("--spend-tokens")
    with open(run_dir / "thinking.log", "w", encoding="utf-8") as fh:
        code = subprocess.run(cmd, cwd=DC.REPO, stdout=fh, stderr=subprocess.STDOUT, env=TK.api_env()).returncode
    if code:
        tail = (run_dir / "thinking.log").read_text(encoding="utf-8", errors="replace").strip().splitlines()[-3:]
        raise SystemExit(f"thinking failed ({run_dir / 'thinking.log'}): " + " | ".join(tail))
    return {"query": query, **TK.read(run_dir)}


def patterns_on() -> bool:
    """Whether the combined-pattern adjustment is on (unpriced_leads/patterns_live.py; off: no step, no change)."""
    repo_imports()
    from src.eda.unpriced_leads import patterns_live as PL
    return PL.is_on()


def step_patterns(run_dir: Path) -> dict:
    """The combined-pattern adjustment's live values and z, while it is on: unpriced_leads/live_members.py inside the
    work tree for the run's matches (the registered members on the tree's own tables), then the live gate and z with
    the check's frozen parameters. Writes <run>/live_members.parquet, live_members.json, live_patterns.parquet and
    live_patterns.json.
    The venue pace's surface IOS (16 Oct 2026): the instance's own table (its build tree's), with the ace ratings the
    states step solved on today's tables laid over it (the live rows and the history since the checkpoint)."""
    repo_imports()
    from src.eda.unpriced_leads import patterns_live as PL
    cfg = run_config(run_dir)
    box = Path(cfg["work_tree"])
    script = box / "src" / "eda" / "unpriced_leads" / "live_members.py"
    if not script.exists():
        raise SystemExit(f"{script} missing: the work tree predates the pattern adjustment")
    ace = run_dir / ACE_ROWS
    if not ace.exists():
        raise SystemExit(f"{ace} missing: the states step predates the live ace ratings (16 Oct 2026); run it again")
    ios_table = Path(cfg["base_tree"]) / "data" / "studies" / "surface_ios" / "surface_features.parquet"
    meta = pd.read_parquet(run_dir / "live_meta.parquet").astype({"match_id": str})
    ids = run_dir / "patterns_ids.txt"
    ids.write_text("\n".join(meta["match_id"].tolist()) + "\n", encoding="utf-8")
    cmd = [str(DC.PY), str(script), "--ids", str(ids), "--out", str(run_dir / PL.MEMBERS_FILE),
           "--ios-table", str(ios_table), "--ace-rows", str(ace), "--frame", str(run_dir / "live_frame.parquet"),
           "--ios-out", str(box / "run" / "live_ios_table.parquet")]
    with open(run_dir / "patterns_inside.log", "w", encoding="utf-8") as fh:
        code = subprocess.run(cmd, cwd=box, env={**os.environ, "PYTHONIOENCODING": "utf-8"}, stdout=fh,
                              stderr=subprocess.STDOUT).returncode
    if code:
        raise SystemExit(f"patterns failed inside the work tree: {run_dir / 'patterns_inside.log'}")
    return PL.build_for_run(run_dir, box)


def step_predict(run_dir: Path, seeds: str) -> dict:
    repo_imports()
    import dp_predict as PR
    states = DC.read_json(run_dir / "states.json")
    cfg = run_config(run_dir)
    out = PR.run(run_dir, span(seeds), Path(cfg["instance"]),
                 checkpoint=Path(states["checkpoint"]).name if states["checkpoint"]
                 else "none: every part from scratch (tier 2)", thinking=bool(cfg.get("thinking")))
    if cfg["mode"] == "live":                            # the archive (PLAN.md section 2), beside the bet sheets' records
        day = str(pd.read_csv(run_dir / "predictions.csv")["day"].min())[:10]   # (master pipeline, 13 Oct 2026): the
        dst = DC.REPO / "predictions" / day / "records"                         # day's folder keeps the sheets on top
        dst.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(run_dir / "predictions.csv", dst / f"{run_dir.name}.csv")
        shutil.copy2(run_dir / "provenance.json", dst / f"{run_dir.name}.provenance.json")
        out["archived_to"] = str(dst)
    return out


def step_grade(run_dir: Path) -> dict:
    """Each prediction against its result where the repository's Stage 0 holds one (a played match keeps the id the
    live row was given): log loss of q and of the market's price."""
    repo_imports()
    from src.eda.predictability_diagnostic import common as C
    pred = pd.read_csv(run_dir / "predictions.csv").astype({"match_id": str})
    m = pd.read_parquet(C.MATCHES, columns=["match_id", "status", "a_won"]).astype({"match_id": str})
    g = pred.merge(m, on="match_id", how="left")
    done = g["status"].isin(["completed", "retired"])
    y = g.loc[done, "a_won"].astype(bool).to_numpy()

    def ll(p):
        p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
        return np.where(y, -np.log(p), -np.log(1 - p))
    g.loc[done, "ll_model"] = ll(g.loc[done, "q_a"])
    g.loc[done, "ll_market"] = ll(g.loc[done, "p_market_a"])
    if "q_a_patterns_off" in g.columns:               # the model without the combined-pattern adjustment, beside it
        g.loc[done, "ll_model_patterns_off"] = ll(g.loc[done, "q_a_patterns_off"])
    # a run with Thinking beside the local model (q_a is their ensemble): each model alone, without the patterns
    both = {"ll_local_patterns_off": "q_a_local_patterns_off", "ll_thinking": "q_a_thinking"}
    both = {k: c for k, c in both.items() if c in g.columns and g.loc[done, c].notna().all()}
    for k, c in both.items():
        g.loc[done, k] = ll(g.loc[done, c])
    g.to_csv(run_dir / "graded.csv", index=False)
    out = {"predictions": int(len(g)), "graded": int(done.sum())}
    if done.any():
        out.update({"mean_ll_model": float(g.loc[done, "ll_model"].mean()),
                    "mean_ll_market": float(g.loc[done, "ll_market"].mean()),
                    "note": "a handful of matches decides nothing (the adoption framework's resolution)"})
        if "ll_model_patterns_off" in g.columns:
            out["mean_ll_model_patterns_off"] = float(g.loc[done, "ll_model_patterns_off"].mean())
            out["patterns"] = str(g["patterns"].iloc[0]) if "patterns" in g.columns else None
        for k in both:
            out[f"mean_{k}"] = float(g.loc[done, k].mean())
    DC.write_json(run_dir / "grade.json", out)
    return out


def reprice(run_dir: Path, prices_csv: Path) -> dict:
    """Tier 0 (PLAN.md section 3.2): new margin-free prices (CSV: match_id, p_a, side A's chance) read off the run's
    stored curves, linear in log-odds (stage 2 is affine in eta, so this is eta's interpolation); no refit. Refused when
    the run's inputs changed since its predictions (provenance), and NaN outside the grid (its own-price forecast
    stands; a price there needs a new fit)."""
    from scipy.special import expit, logit
    prov = DC.read_json(run_dir / "provenance.json")
    if DC.sha256(run_dir / "live_frame.parquet") != prov["live_frame_sha256"]:
        raise SystemExit("reprice: the run's inputs changed since its predictions (provenance): predict again")
    curves = pd.read_parquet(run_dir / "curves.parquet").astype({"match_id": str})
    new = pd.read_csv(prices_csv).astype({"match_id": str})
    two = "q_a_patterns_off" in curves.columns          # the combined-pattern adjustment's two versions (13 Oct 2026)
    # a run with Thinking beside the local model (20 Oct 2026): q_a is their ensemble; each model's own curve beside it
    # (q_a_thinking with stage 2's speed term, q_a_thinking_api the API's own: runs from the evening of 20 Oct)
    each = [c for c in ("q_a_local", "q_a_local_patterns_off", "q_a_thinking", "q_a_thinking_api")
            if c in curves.columns]
    status = "off"
    if (run_dir / "predictions.csv").exists():
        pc = pd.read_csv(run_dir / "predictions.csv")
        status = str(pc["patterns"].iloc[0]) if "patterns" in pc.columns and len(pc) else "off"
    rows = []
    for mid, p in zip(new["match_id"], new["p_a"].astype(float)):
        c = curves[curves["match_id"].eq(mid)].sort_values("odds_logit")
        if c.empty:
            rows.append({"match_id": mid, "p_market_a": p, "q_a": np.nan, "note": "not in this run"})
            continue
        x = float(logit(p))
        g = c["odds_logit"].to_numpy()
        inside = g[0] <= x <= g[-1]
        q = float(expit(np.interp(x, g, logit(c["q_a"].to_numpy())))) if inside else np.nan
        row = {"match_id": mid, "p_market_a": p, "q_a": q}
        if two:
            q_off = float(expit(np.interp(x, g, logit(c["q_a_patterns_off"].to_numpy())))) if inside else np.nan
            row.update({"q_a_patterns_off": q_off, "q_a_patterns_on": q if status == "on" else np.nan,
                        "patterns": status})
        for col in each:
            row[col] = float(expit(np.interp(x, g, logit(c[col].to_numpy())))) if inside else np.nan
        row["note"] = "" if inside else "outside the price grid"
        rows.append(row)
    out = pd.DataFrame(rows)
    path = run_dir / f"reprice_{DC.stamp()}.csv"
    out.to_csv(path, index=False)
    return {"repriced": int(out["q_a"].notna().sum()), "outside_grid_or_unknown": int(out["q_a"].isna().sum()),
            "file": str(path)}


def replay_compare(run_dir: Path, frame: Path | None = None) -> dict:
    """The replayed matches' 57 inputs against the instance frame's (prediction_run/replay.compare's question, every
    input bit for bit; the IOS inputs also within the owner's 1e-6)."""
    import dp_state as SP
    cfg = run_config(run_dir)
    frame = frame or replay_frame(cfg)
    names = SP.model_names(Path(cfg["instance"]))
    live = pd.read_parquet(run_dir / "live_frame.parquet").astype({"match_id": str}).set_index("match_id")
    tmpl = pd.read_parquet(frame, columns=["match_id"] + [f"in_{n}" for n in names]).astype({"match_id": str})
    tmpl = tmpl.set_index("match_id")
    ids = live.index
    missing = sorted(set(ids) - set(tmpl.index))
    ids = ids[ids.isin(tmpl.index)]
    per = {n: DC.compare(live.loc[ids, f"in_{n}"].to_numpy(), tmpl.loc[ids, f"in_{n}"].to_numpy()) for n in names}
    ios = [n for n in names if n.startswith(("iosO_", "iosD_", "prod_"))]
    out = {"frame": str(frame), "matches": int(len(ids)), "missing_from_frame": missing, "inputs": len(names),
           "inputs_bitwise": int(sum(DC.bitwise(v) for v in per.values())),
           "non_ios_bitwise": int(sum(DC.bitwise(per[n]) for n in names if n not in ios)),
           "non_ios_inputs": len(names) - len(ios),
           "ios_max_abs_diff": max(per[n]["max_abs_diff"] for n in ios),
           "ios_nan_pattern_equal": all(per[n]["nan_pattern_equal"] for n in ios),
           "max_abs_diff": max(v["max_abs_diff"] for v in per.values()),
           "per_input": per}
    out["matches_equal_on_every_input"] = int(sum(
        all((np.isnan(live.loc[i, f"in_{n}"]) and np.isnan(tmpl.loc[i, f"in_{n}"]))
            or live.loc[i, f"in_{n}"] == tmpl.loc[i, f"in_{n}"] for n in names) for i in ids))
    DC.write_json(run_dir / "replay_compare.json", out)
    return out


def checkpoint_day(run_dir: Path) -> str:
    """The checkpoint a live day should leave: the Monday at least three weeks before its earliest match (PLAN.md
    section 3.3: a tournament-week boundary, three weeks back, so every row it covers is final)."""
    meta = pd.read_parquet(run_dir / "live_meta.parquet")
    first = pd.to_datetime(meta["day"]).min().normalize() - pd.Timedelta(days=21)
    return str((first - pd.Timedelta(days=first.weekday())).date())


def step_save_checkpoint(run_dir: Path, workers: int) -> dict:
    """A checkpoint on the work tree's tables (today's), for the next days to resume from. Its rows all lie before
    its day, so the live rows (after it) are in none of its states."""
    import dp_store as STR
    import dp_tables as TB
    cfg = run_config(run_dir)
    box = Path(cfg["work_tree"])
    day = checkpoint_day(run_dir)
    if (STR.folder(day) / "manifest.json").exists():
        return {"day": day, "skipped": "a checkpoint of that day exists"}
    code = in_tree(box, ["checkpoint", "--tree", str(box), "--day", day, "--workers", str(workers),
                         "--note", f"left by the live run {run_dir.name}"], env=TB.layer_env(box),
                   log=run_dir / "checkpoint_inside.log")
    if code:
        raise SystemExit(f"checkpoint failed inside the work tree: {run_dir / 'checkpoint_inside.log'}")
    return {"day": day, "folder": str(STR.folder(day))}


def run_day(run_dir: Path, do_refresh: bool, do_fit: bool, keep_tree: bool, workers: int, direct: str = "",
            leave_checkpoint: str = "auto", fit_cache: str = "use", spend_tokens: bool = False) -> dict:
    """Every step in order, each one's time recorded (run_day.json). A live day leaves a checkpoint on its own tables
    (leave_checkpoint "auto": when a part had to be recomputed in full, or the checkpoint it resumed from is more than
    two weeks older than the one it would leave; "yes", "no"). fit_cache: step_fit's.
    A run made with --thinking (run.json) also gets TabPFN-3.5-Thinking's paid prediction after the local fit
    (spend_tokens must be given, or nothing starts). If that call fails, the local model's predictions still come, and
    run_day.json, predictions.csv's `ensemble` and provenance.json say why there is no ensemble."""
    import dp_worktree as WT
    cfg = run_config(run_dir)
    if Path(cfg["instance"]).resolve() != DC.INSTANCE.resolve():
        raise SystemExit(f"this run was made for {cfg['instance']}, but DP_INSTANCE now names {DC.INSTANCE}")
    if cfg.get("thinking") and do_fit and not spend_tokens:
        raise SystemExit("this run asks for TabPFN-3.5-Thinking, a paid call: pass --spend-tokens")
    times: dict = {}
    out: dict = {"run": str(run_dir), "mode": cfg["mode"], "started_at": DC.stamp(), "steps": times}

    def timed(name, fn, *args):
        t0 = time.time()
        DC.log(f"== {name}")
        res = fn(*args)
        times[name] = round(time.time() - t0, 1)
        record(run_dir, name, {"seconds": times[name], "result": res})
        DC.write_json(run_dir / "run_day.json", out)
        DC.log(f"   {name}: {times[name]} s")
        return res
    hist = None
    try:
        if do_refresh and cfg["mode"] == "live":
            timed("refresh", step_refresh, run_dir, True, 300)
        if cfg["mode"] == "live":
            timed("matchups", step_matchups, run_dir)
            timed("prices", step_prices, run_dir)
            timed("worktree", step_worktree, run_dir)
        else:
            timed("worktree", step_worktree, run_dir)
            timed("matchups", step_matchups, run_dir)
            timed("prices", step_prices, run_dir)
        timed("tables", step_tables, run_dir, False)
        hist = start_history(run_dir)                    # beside the states step (part 2)
        st = timed("states", step_states, run_dir, False, workers)
        timed("history", join_history, hist, run_dir)    # the wait only, if it is still running
        if patterns_on():                                # the combined-pattern adjustment: off, no step at all
            timed("patterns", step_patterns, run_dir)
        if cfg["mode"] == "live" and leave_checkpoint != "no":
            stale = st.get("checkpoint") is None or any(v != "resumed" for v in DC.read_json(
                run_dir / "states.json")["record"]["parts"].values())
            old_day = Path(st["checkpoint"]).name if st.get("checkpoint") else "1970-01-01"
            if leave_checkpoint == "yes" or stale or DC.day_of(checkpoint_day(run_dir)) - DC.day_of(old_day) > 14:
                timed("checkpoint", step_save_checkpoint, run_dir, workers)
        if do_fit:
            timed("fit", step_fit, run_dir, cfg["seeds"], direct, fit_cache)
            if cfg.get("thinking"):                      # after the local fit: no token is spent on a run that failed
                try:
                    timed("thinking", step_thinking, run_dir, spend_tokens)
                except (Exception, SystemExit) as exc:  # noqa: BLE001 - the local model's predictions still come
                    reason = str(exc) if isinstance(exc, SystemExit) else f"{type(exc).__name__}: {exc}"
                    out["thinking_failed"] = reason
                    record(run_dir, "thinking", {"failed": reason})
                    DC.write_json(run_dir / "thinking" / "failed.json", {"failed_at": DC.stamp(), "reason": reason})
                    DC.log(f"   THINKING FAILED ({reason}): the local model's predictions follow, without the ensemble")
            timed("predict", step_predict, run_dir, cfg["seeds"])
        out["finished_at"] = DC.stamp()
        return out
    finally:
        if hist is not None and hist.poll() is None:     # never delete the work tree under it
            hist.wait()
        # Only a work tree whose marker names this run: a run refused because another run's tree exists must leave
        # that tree to it (found by the tennis-predictions-fc session's review, 11 Oct 2026).
        if not keep_tree and WT.owner_of(Path(cfg["work_tree"])) == str(run_dir):
            t0 = time.time()
            out["cleanup"] = WT.cleanup(Path(cfg["work_tree"]))
            times["cleanup"] = round(time.time() - t0, 1)
        DC.write_json(run_dir / "run_day.json", out)
