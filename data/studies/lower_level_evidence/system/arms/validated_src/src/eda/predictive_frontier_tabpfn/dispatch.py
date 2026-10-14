"""One explicitly authorized hosted Thinking fit, in the tennis-tabpfn environment."""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.eda.predictive_frontier_tabpfn import common as C, guard as G


def dry_run():
    from tabpfn_client import estimator as E
    X, y, Q, _, manifest = C.load_upload()
    backend = G.LiveBackend(G.CONFIG)
    account = backend.preflight()
    capacity = G.validate_account(account, X, Q)
    quotes = backend.quote(X, Q)
    total = sum(q["estimated_cost"] for q in quotes.values())
    if total > min(capacity["monthly_tokens_remaining"], capacity["daily_tokens_remaining"]):
        raise ValueError("Quoted cost exceeds remaining quota; no fit dispatched")
    E.validate_train_set(X, y)
    model = backend.model
    preview = {"tabpfn_config": model._get_tabpfn_config().model_dump(mode="json"),
        "thinking_config": E._build_thinking_config(X, enabled=True, effort=model.thinking_effort,
              timeout_secs=model.thinking_timeout_s, metric=model.thinking_metric).model_dump(mode="json")}
    result = {"checked_at": account["checked_at"], "sdk_version": account["sdk_version"],
        "usage": account["usage"], "model_limits": account["settings"]["model_limits"]["v3.5"],
        "capacity": capacity, "quote": quotes, "total_quoted": total, "preview": preview,
        "input_sha256": manifest["input_sha256"], "config": G.CONFIG}
    C.write_json(C.OUT / "preflight.json", result)
    print(f"Preflight and request validation passed: train {X.shape}, query {Q.shape}; quoted {total:,} tokens; monthly remaining {capacity['monthly_tokens_remaining']:,}", flush=True)
    return result


def run():
    X, y, Q, _, manifest = C.load_upload()
    preflight = __import__("json").loads((C.OUT / "preflight.json").read_text())
    if preflight["input_sha256"] != manifest["input_sha256"] or preflight["config"] != G.CONFIG:
        raise ValueError("Preflight does not describe current frozen request")
    backend = G.LiveBackend(G.CONFIG)
    before = backend.usage()
    start = time.monotonic()
    result = G.execute_once(X, y, Q, C.THINKING, expected_input_sha256=manifest["input_sha256"],
        fingerprint=C.fingerprint, description=manifest["fit_description"], log=lambda msg: print(msg, flush=True))
    after = backend.usage()
    record = {"finished_at": pd.Timestamp.now(tz="UTC").isoformat(), "wall_seconds": time.monotonic()-start,
        "reused_saved_predictions": result["reused_saved_predictions"], "receipt": result["receipt"],
        "usage_before": before, "usage_after": after,
        "tokens_monthly_delta": after["monthly_usage"]-before["monthly_usage"]}
    if not result["reused_saved_predictions"]:
        C.write_json(C.OUT / "thinking_run.json", record)
    print(f"Complete: {record['wall_seconds']:.1f}s, token counter change {record['tokens_monthly_delta']:,}; saved probability rows {len(result['p_a']):,}", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--run", action="store_true")
    p.add_argument("--spend-tokens", action="store_true")
    args = p.parse_args()
    if args.run:
        if not args.spend_tokens:
            p.error("--run requires --spend-tokens")
        run()
    else:
        dry_run()
