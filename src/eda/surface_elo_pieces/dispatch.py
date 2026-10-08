"""Calls to the hosted TabPFN-3.5-Plus for this study. Runs in the isolated `tennis-tabpfn` env.

    ./python_tabpfn.sh src/eda/surface_elo_pieces/dispatch.py --quote [--stage pilot|confirm]
        the server's token quote for every registered job of the stage (free: only row and column counts are sent)
    ./python_tabpfn.sh src/eda/surface_elo_pieces/dispatch.py --run --stage pilot --spend-tokens [--jobs ID ...]
        fit and predict every pending job of the stage once (guard.execute_job); finished jobs are re-used, never re-sent

The frame is rebuilt into each job's exact upload from data/studies/surface_elo_pieces/frame.parquet and checked against
the job's registered fingerprint before anything is sent. --run refuses if the stage's quote exceeds the remaining daily
or monthly quota. Writes quotes_<stage>.json and run_<stage>.jsonl (one line per job: timings, usage before and after).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_elo_pieces import build_frames as BF  # noqa: E402
from src.eda.surface_elo_pieces import common as C  # noqa: E402
from src.eda.surface_elo_pieces import guard as G  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402


def load_jobs(stage: str, only: list[str] | None) -> list[dict]:
    js = [j for j in json.loads((C.OUT / "jobs.json").read_text(encoding="utf-8")) if j["stage"] == stage]
    if only:
        js = [j for j in js if j["job"] in set(only)]
        if len(js) != len(set(only)):
            raise SystemExit("unknown job id")
    return js


def quote(stage: str, js: list[dict], registered: bool) -> dict:
    """The server's quote for the jobs. The registered quote (--quote) is written to quotes_<stage>.json; a quote taken
    at run time is appended to quotes_<stage>_runs.jsonl, so the registered one is never overwritten (audit G5)."""
    from tabpfn_client import set_access_token
    from tabpfn_client.client import ServiceClient
    from tabpfn_client.cost import estimate_cost
    from tabpfn_client.service_wrapper import UserAuthenticationClient
    import numpy as np
    token, _ = UserAuthenticationClient.resolve_token_with_source()
    set_access_token(token)
    usage = ServiceClient.get_api_usage(token)
    rows, total = [], 0
    for j in js:
        q = estimate_cost(np.zeros((j["train_rows"], len(j["columns"]))), np.zeros((j["query_rows"], len(j["columns"]))),
                          model_version="v3.5", operation="predict", n_estimators=G.CONFIG["n_estimators"])
        cost = q.model_dump(mode="json")["estimated_cost"]
        total += cost
        rows.append({"job": j["job"], "estimated_cost": cost})
    out = {"quoted_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "stage": stage, "jobs": rows,
           "total_quoted": total,
           "usage": {k: v for k, v in usage.items() if isinstance(v, (int, float)) and ("usage" in k or "limit" in k)}}
    if registered:
        C.write_json(C.OUT / f"quotes_{stage}.json", out)
    else:
        with (C.OUT / f"quotes_{stage}_runs.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(out) + "\n")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--quote", action="store_true")
    mode.add_argument("--run", action="store_true")
    ap.add_argument("--stage", choices=list(BF.STAGES), required=True)
    ap.add_argument("--jobs", nargs="*")
    ap.add_argument("--spend-tokens", action="store_true", help="required with --run")
    a = ap.parse_args()
    js = load_jobs(a.stage, a.jobs)
    q = quote(a.stage, js, registered=a.quote and not a.jobs)
    u = q["usage"]
    room = min(u["monthly_limit"] - u["monthly_usage"], u["daily_limit"] - u["daily_usage"])
    C.log(f"{a.stage}: {len(js)} jobs quoted at {q['total_quoted']:,} tokens; room today {room:,}")
    if a.quote:
        return 0
    if not a.spend_tokens:
        print("--run spends TabPFN tokens; add --spend-tokens to proceed")
        return 2
    if q["total_quoted"] > room:
        raise SystemExit(f"quoted {q['total_quoted']:,} tokens exceed the remaining quota {room:,}; nothing sent")
    frame = pd.read_parquet(C.OUT / "frame.parquet")
    log_path = C.OUT / f"run_{a.stage}.jsonl"
    for j in js:
        X_train, y_train, X_query, _ = BF.job_data(frame, j["arm"], j["season"])
        t0 = time.monotonic()
        res = G.execute_job(j, X_train, y_train, X_query, fingerprint=T.fingerprint, log=C.log)
        line = {"job": j["job"], "reused": res["reused"], "seconds": round(time.monotonic() - t0, 1),
                "finished_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}
        if not res["reused"]:
            done = json.loads((G.canonical_root() / j["job"] / "COMPLETE.json").read_text(encoding="utf-8"))
            u0, u1, u2 = done["usage_before"], done["usage_after_fit"], done["usage_after"]
            line["tokens_fit"] = u1.get("monthly_usage", 0) - u0.get("monthly_usage", 0)
            line["tokens_predict"] = u2.get("monthly_usage", 0) - u1.get("monthly_usage", 0)
            line["served"] = {k: done["metadata"].get(k) for k in ("billing_model_version", "execution_mode")}
            line["served_model"] = (done["metadata"].get("tabpfn_config") or {}).get("model_path")
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(line) + "\n")
        C.log(f"{j['job']}: {'re-used' if res['reused'] else 'done'} in {line['seconds']} s"
              + (f", tokens fit {line['tokens_fit']}, predict {line['tokens_predict']}, served {line['served']}"
                 if not res["reused"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
