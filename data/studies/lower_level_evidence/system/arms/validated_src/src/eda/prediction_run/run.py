"""A prediction run: box scores refreshed first, then live inputs built by the training code, in a sandbox
(docs/decisions/2026-10-08-prediction-run-box-scores.md).

The steps, each with its own command (a run's records go to its folder, default data/studies/prediction_run/<stamp>/):
    --refresh   box scores first. Tennis My Life is downloaded; Stage 0 is built from it into the run's folder; the
                main-tour matches of the last weeks with a result but no box score are listed (fills.py); those the
                frozen reference does not hold are filled from the official feed that serves them (the WTA API), as an
                override table for the sandbox's Stage 0 only. --matchups <csv> then writes the upcoming matches' live
                rows and meta (live_rows.py; the price p_a and day of each come with the matchups)
    --setup     create the sandbox (sandbox.py)
    --build     in the sandbox: Stage 0 with the decided overrides, the fills and the live rows, its checks, Stage 1's
                odds with the live prices, the match timeline with the live days, the leak-proof features (as
                data_continuity/rebuild_stage0.py builds them, without TrueSkill, which no input reads), then the model's
                chain (model_rebuild/run_chain.py's lanes: 1 and 2 side by side, then 3). The live matches' rows of the
                model frame are collected into the run's folder (live_frame.parquet), with the model's input list (the
                chain's, less the inputs the owner dropped: current_best_model/template_inputs.py) and the history check
                of the sandbox's Stage 0 against the frozen reference (current_best_model/history.py)
    --gate      the training standard (gate.py): every finished match of either player at the event and in the last 14
                days has a box score; a live match that fails is marked not to bet, with what is missing
    --cleanup   delete the sandbox (its links first)
A replay (replay.py) prepares a folder of played matches as live rows and is built with --build like a run.

Run: ./python.sh src/eda/prediction_run/run.py --refresh [--matchups <csv>] [--out <folder>]
     ./python.sh src/eda/prediction_run/run.py --setup
     ./python.sh src/eda/prediction_run/run.py --build <folder> [--from <step>]
     ./python.sh src/eda/prediction_run/run.py --gate <folder>
     ./python.sh src/eda/prediction_run/run.py --cleanup
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import threading
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.prediction_run import common as P  # noqa: E402
from src.eda.prediction_run import sandbox as SB  # noqa: E402

INJECT = "src/eda/prediction_run/inject.py"
UPDATING = "tennis_data,wta_api,sofascore,slam_feeds,tdi"     # match_timing/refresh.py's updating sources
TML_ARGS = ["-m", "src.ingest.public_dump.tennis_my_life", "--start-year", "2000"]   # as the daily job downloads it
MATCHUP_COLUMNS = ["tour", "tourney_id", "round", "player_a", "player_b", "day", "p_a"]


def subprocess_step(name: str, args: list[str], record: list) -> int:
    import subprocess
    import time

    t0 = time.time()
    P.log(f"--> {name}: {' '.join(args)}")
    done = subprocess.run([str(P.PY), *args], cwd=P.ROOT, capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    record.append({"step": name, "args": args, "exit": done.returncode, "seconds": round(time.time() - t0, 1),
                   "tail": (done.stdout + done.stderr)[-1500:]})
    P.log(f"    exit {done.returncode} in {time.time() - t0:.0f} s")
    return done.returncode


def venue_for(tour: str, tid: str, name: str) -> str:
    """The event's city: its last edition's tennis-data Location (Stage 1's links), else TML's event name."""
    from src.eda.match_timing import srcc_tennis_data as TD

    code = str(tid).split("-")[1] if "-" in str(tid) else str(tid)
    o = pd.read_parquet(P.ROOT / P.PD / "stage1_odds.parquet", columns=["match_id", "tour", "td_file", "td_row",
                                                                       "tournament_date"])
    o = o[o["tour"].eq(tour) & o["td_file"].notna() & o["match_id"].astype(str).str.split("|").str[1]
          .str.split("-").str[1].eq(code)]
    if len(o):
        last = o.sort_values("tournament_date").tail(1).reset_index(drop=True)
        city = TD.locations(last).iloc[0]
        if isinstance(city, str) and city:
            return city
    return name


def uk_day(day, start_utc) -> pd.Timestamp:
    """tennis-data dates a match by the UK calendar day of its start: from the start time when known."""
    if isinstance(start_utc, str) and start_utc.strip():
        return pd.Timestamp(start_utc).tz_convert("Europe/London").tz_localize(None).normalize()
    return pd.Timestamp(day).normalize()


def live_from_matchups(matchups: pd.DataFrame, stage0: Path, folder: Path) -> dict:
    """Live rows and meta for upcoming matches (columns MATCHUP_COLUMNS, optional tourney_name, best_of, start_utc).
    p_a is the margin-free price that player_a wins at bet time; the match id is predicted from Stage 0's ids and
    checked in the sandbox."""
    from src.eda.prediction_run import live_rows as LR
    from src.eda.predictability_diagnostic import common as C
    from src.eda.predictability_diagnostic import stage0_build as B

    missing = set(MATCHUP_COLUMNS) - set(matchups.columns)
    if missing:
        raise SystemExit(f"matchups: columns missing: {sorted(missing)}")
    years = sorted({pd.Timestamp(d).year for d in matchups["day"]})
    raw = LR.staged_tml(sorted(set(years) | {y - 1 for y in years}))
    rows = LR.upcoming_rows(matchups, raw)
    m = pd.read_parquet(stage0 / "stage0_matches.parquet", columns=["match_id", "tour", "tournament_id", "source_file",
                                                                    "source_row"])
    p = pd.read_parquet(stage0 / "stage0_match_players.parquet", columns=["match_id", "player_id", "player_name"])
    keyed = p.assign(key=B.S.keys_for(p["player_name"])).merge(m[["match_id", "tour"]], on="match_id")
    meta = []
    for i, mu in matchups.reset_index(drop=True).iterrows():
        event = LR.event_rows(raw, mu["tour"], mu["tourney_id"], mu.get("tourney_name") or None)
        own = m[m["source_file"].astype(str).isin(set(event["_source_file"].astype(str)))
                & pd.to_numeric(m["source_row"]).isin(pd.to_numeric(event["_row"]))]
        tids = own.loc[own["tour"].eq(mu["tour"]), "tournament_id"].value_counts()
        if tids.empty:
            raise SystemExit(f"matchups: the event {mu['tourney_id']} has no Stage 0 match")
        ids = []
        for who in ("player_a", "player_b"):
            hit = keyed[keyed["tour"].eq(mu["tour"]) & keyed["key"].eq(B.S.name_key(str(mu[who])))]["player_id"]
            if hit.nunique() != 1:
                raise SystemExit(f"matchups: {mu[who]!r} names {hit.nunique()} Stage 0 players")
            ids.append(hit.iloc[0])
        lo, hi = sorted(ids)
        mid = f"{mu['tour']}|{tids.index[0]}|{str(mu['round']).upper()}|{lo}|{hi}"
        a_is_a = (lo if C.side_is_low(mid) else hi) == ids[0]
        p_a = float(mu["p_a"])
        meta.append({"match_id": mid, "day": uk_day(mu["day"], mu.get("start_utc")),
                     "p_a": p_a if a_is_a else 1 - p_a, "venue": venue_for(mu["tour"], tids.index[0],
                                                                         str(event["tourney_name"].iloc[0])),
                     "tour": mu["tour"], "tournament_name": str(event["tourney_name"].iloc[0]),
                     "round": str(mu["round"]).upper(), "player_a": mu["player_a"], "player_b": mu["player_b"]})
    meta = pd.DataFrame(meta)
    rows.to_parquet(folder / "live_rows.parquet", index=False)
    meta.to_parquet(folder / "live_meta.parquet", index=False)
    return {"live_matches": int(len(meta)), "match_ids": meta["match_id"].tolist()}


def refresh(folder: Path, matchups: Path | None, download: bool, max_requests: int) -> int:
    """Box scores first: the download, Stage 0 on it, the gaps, the WTA fills; then the upcoming matches' live rows."""
    from src.eda.prediction_run import fills as FL
    from src.eda.prediction_run import live_rows as LR

    folder.mkdir(parents=True, exist_ok=True)
    record: dict = {"started_at": P.stamp(), "steps": []}
    try:
        if download and subprocess_step("tml", TML_ARGS, record["steps"]) not in (0, 1):
            return 2                                   # 1: a file held or a download error, reported in the record
        if subprocess_step("stage0", ["src/eda/predictability_diagnostic/stage0_build.py", "--out-dir",
                                      str(folder / "stage0")], record["steps"]):
            return 2
        today = pd.Timestamp.now().normalize()
        g = FL.gaps(folder / "stage0", today, FL.reference_ids())
        record["gaps"] = g.groupby(["class", "tour", "level"]).size().rename("matches").reset_index().to_dict("records")
        fillable = g[g["class"].eq("fillable")]
        keys = FL.tml_keys(fillable, LR.staged_tml(sorted({int(y) for y in fillable["year"]}))) if len(fillable) else None
        fills, notes = FL.fill_wta(fillable, keys, max_requests) if len(fillable) else (pd.DataFrame(), [])
        g = g.merge(pd.DataFrame(notes, columns=["match_id", "outcome"]), on="match_id", how="left") if notes else g
        g[["match_id", "tour", "level", "tournament_name", "round", "tournament_date", "class"]
          + (["outcome"] if "outcome" in g else [])].to_csv(folder / "gaps.csv", index=False)
        record["fills"] = {"filled": int(len(fills)), "notes": notes[:50]}
        if len(fills):
            fills.to_csv(folder / "fills.csv", index=False)
            FL.override_table(fills).to_csv(folder / "overrides.csv", index=False)
        if matchups is not None:
            record["live"] = live_from_matchups(pd.read_csv(matchups), folder / "stage0", folder)
        return 0
    finally:
        record["finished_at"] = P.stamp()
        P.write_json(folder / "refresh.json", record)


def stage0_steps(has_overrides: bool) -> list[tuple[str, str, list[str]]]:
    """Stage 0 to the leak-proof features, with the live rows' injections between the builders."""
    over = ["--box-overrides", "run/overrides.csv", "--confirm-live-overrides"] if has_overrides else []
    return [
        ("stage0", "src/eda/predictability_diagnostic/stage0_build.py", ["--live-rows", "run/live_rows.parquet", *over]),
        ("check", INJECT, ["--meta", "run/live_meta.parquet", "--step", "check"]),
        ("stage0_checks", "src/eda/predictability_diagnostic/stage0_checks.py", []),
        ("odds", "src/eda/predictability_diagnostic/stage1_odds.py", []),
        ("live_odds", INJECT, ["--meta", "run/live_meta.parquet", "--step", "odds"]),
        ("remap", INJECT, ["--meta", "run/live_meta.parquet", "--step", "remap"]),
        ("links", "src/eda/match_timing/link_sources_c.py", ["--sources", UPDATING]),
        ("live_links", INJECT, ["--meta", "run/live_meta.parquet", "--step", "links"]),
        ("timing", "src/eda/match_timing/timing.py", []),
        ("timing_check", "src/eda/match_timing/timing_check.py", []),
        ("live_window", INJECT, ["--meta", "run/live_meta.parquet", "--step", "pin"]),
        ("timing_features", "src/eda/match_timing/rebuild.py", []),
    ]


def chain_lanes() -> dict[str, list[tuple[str, str, list[str]]]]:
    from src.eda.model_rebuild import run_chain as RC

    return {lane: [(name, script.split()[0], script.split()[1:]) for name, script in RC.LANES[lane]]
            for lane in ("1", "2", "3")}


def run_steps(steps, record: list, start: str | None = None) -> int:
    names = [s[0] for s in steps]
    for name, script, args in steps[names.index(start):] if start in names else steps:
        code = SB.run(name, script, *args, record=record)
        if code != 0:
            return code
    return 0


def build(folder: Path, start: str | None = None) -> int:
    box = P.SANDBOX
    if not (box / P.MARKER).exists():
        raise SystemExit(f"no sandbox at {box}: run.py --setup")
    run_dir = box / "run"
    SB.refresh_code()                                  # the sandbox runs the repository's current code
    first = start is None
    if first:
        if run_dir.exists():
            raise SystemExit(f"{run_dir} exists: this sandbox has built a run already (--cleanup, --setup)")
        (run_dir / "stage0_before").mkdir(parents=True)
        for f in ("live_rows.parquet", "live_meta.parquet", "overrides.csv"):
            if (folder / f).exists():
                shutil.copy2(folder / f, run_dir / f)
        for f in ("stage0_matches.parquet", "stage0_match_players.parquet"):
            shutil.copy2(box / P.PD / f, run_dir / "stage0_before" / f)
    record_path = folder / "build.json"
    record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.exists() and not first else {"steps": []}
    record.update({"sandbox": str(box), "folder": str(folder)})
    steps = record["steps"]
    lanes = chain_lanes()
    order = ["prep"] + ["lane1_2", "lane3", "collect"]
    begin = "prep"
    if start:
        for phase, names in (("prep", [s[0] for s in stage0_steps(True)]), ("lane1_2", [s[0] for s in lanes["1"]]
                             + [s[0] for s in lanes["2"]]), ("lane3", [s[0] for s in lanes["3"]]),
                             ("collect", ["collect"])):
            if start in names:
                begin = phase
                break
    try:
        if order.index(begin) <= order.index("prep"):
            code = run_steps(stage0_steps((run_dir / "overrides.csv").exists()), steps,
                             start if begin == "prep" else None)
            if code:
                return code
        if order.index(begin) <= order.index("lane1_2"):
            codes = {}

            def lane(n: str) -> None:
                codes[n] = run_steps(lanes[n], steps, start if begin == "lane1_2" else None)

            threads = [threading.Thread(target=lane, args=(n,)) for n in ("1", "2")]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            if any(codes.values()):
                return max(codes.values())
        if order.index(begin) <= order.index("lane3"):
            code = run_steps(lanes["3"], steps, start if begin == "lane3" else None)
            if code:
                return code
        collect(folder, record)
        return 0
    finally:
        P.write_json(record_path, record)


def collect(folder: Path, record: dict) -> None:
    """The live matches' rows of the sandbox's model frame, its input list, the history check and the logs."""
    box = P.SANDBOX
    meta = pd.read_parquet(folder / "live_meta.parquet").astype({"match_id": str})
    frame = pd.read_parquet(box / P.FRAME)
    frame["match_id"] = frame["match_id"].astype(str)
    live = frame[frame["match_id"].isin(set(meta["match_id"]))]
    live.to_parquet(folder / "live_frame.parquet", index=False)
    shutil.copy2(box / P.INPUTS, folder / "model_inputs.json")
    from src.eda.current_best_model import template_inputs as TI

    record["inputs"] = TI.apply(folder)          # the model's list: the chain's 58 less the dropped (9 Oct 2026)
    from src.eda.current_best_model import history as H

    res = H.check(box / P.PD, box / P.MT / "timing.parquet")
    record["history"] = {k: v for k, v in res.items() if k != "feeds"}
    from src.eda.prediction_run import gate as G

    record["gate"] = G.run(folder, box / P.PD, box / P.MT / "timing.parquet")
    record["collected"] = {"live_matches": int(len(meta)), "in_frame": int(len(live)),
                           "missing_from_frame": sorted(set(meta["match_id"]) - set(live["match_id"]))[:20]}
    logs = folder / "logs"
    logs.mkdir(exist_ok=True)
    for f in (box / "logs").glob("*.log"):
        shutil.copy2(f, logs / f.name)
    for f in (box / "run").glob("*.json"):
        shutil.copy2(f, folder / f"sandbox_{f.name}")
    P.log(f"collected {len(live)} of {len(meta)} live matches into {folder}; {H.summary_line(res)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    which = ap.add_mutually_exclusive_group(required=True)
    which.add_argument("--refresh", action="store_true")
    which.add_argument("--setup", action="store_true")
    which.add_argument("--build", metavar="FOLDER")
    which.add_argument("--gate", metavar="FOLDER")
    which.add_argument("--cleanup", action="store_true")
    ap.add_argument("--from", dest="start", default=None, help="--build: resume at this step")
    ap.add_argument("--out", default=None, help="--refresh: the run's folder (default data/studies/prediction_run/<stamp>)")
    ap.add_argument("--matchups", default=None, help="--refresh: CSV of upcoming matches (" + ", ".join(MATCHUP_COLUMNS)
                    + "; optional tourney_name, best_of, start_utc)")
    ap.add_argument("--no-download", action="store_true", help="--refresh: use the Tennis My Life files held")
    ap.add_argument("--max-requests", type=int, default=300, help="--refresh: the WTA API's request budget")
    a = ap.parse_args()
    if a.setup:
        SB.setup()
        return 0
    if a.cleanup:
        SB.cleanup()
        return 0
    if a.refresh:
        out = Path(a.out) if a.out else P.OUT / P.stamp()
        out = out if out.is_absolute() else ROOT / out
        return refresh(out, Path(a.matchups) if a.matchups else None, not a.no_download, a.max_requests)
    if a.gate:
        from src.eda.prediction_run import gate as G

        folder = Path(a.gate) if Path(a.gate).is_absolute() else ROOT / a.gate
        print(json.dumps(G.run(folder, P.SANDBOX / P.PD, P.SANDBOX / P.MT / "timing.parquet"), indent=1, default=str))
        return 0
    folder = Path(a.build) if Path(a.build).is_absolute() else ROOT / a.build
    return build(folder, a.start)


if __name__ == "__main__":
    sys.exit(main())
