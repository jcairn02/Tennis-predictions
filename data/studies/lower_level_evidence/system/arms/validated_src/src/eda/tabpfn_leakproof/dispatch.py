"""The leak-proof refit's call to the hosted TabPFN API (Prior Labs). Runs in the isolated `tennis-tabpfn` env.

    ./python_tabpfn.sh src/eda/tabpfn_leakproof/dispatch.py --quote     the server's token quotes for the exact upload
                                                                         and the account's remaining quota (free: only
                                                                         row and column counts are sent)
    ./python_tabpfn.sh src/eda/tabpfn_leakproof/dispatch.py --run --spend-tokens
                                                                         the ONE paid thinking fit and the ONE paid
                                                                         prediction batch, through guard.execute_once

Both modes first check the upload against build_frame.py's manifest. --run refuses if the quote exceeds the remaining
daily or monthly quota. Outputs in data/studies/tabpfn_leakproof/: quotes.json, and for --run the receipts in thinking/
plus thinking_run.json (account usage before and after, timings).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_leakproof import common as C  # noqa: E402
from src.eda.tabpfn_leakproof import guard as G  # noqa: E402


def quote(X_train, X_query) -> dict:
    backend = G.LiveBackend(G.CONFIG)
    account = backend.preflight()
    capacity = G.validate_account(account, X_train, X_query)
    q = backend.quote(X_train, X_query)
    total = q["thinking_fit"]["estimated_cost"] + q["thinking_predict"]["estimated_cost"]
    out = {"quoted_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "config": G.CONFIG,
           "shapes": {"X_train": list(X_train.shape), "X_query": list(X_query.shape)},
           "thinking_fit": q["thinking_fit"], "thinking_predict": q["thinking_predict"], "total_quoted": total,
           "capacity": capacity, "usage": account["usage"],
           "note": "server quotes from row and column counts only; the original fit (2 Oct 2026, same shapes) was "
                   "quoted higher than it was billed"}
    C.write_json(C.OUT / "quotes.json", out)
    return out


def run(X_train, y_train, X_query, manifest) -> dict:
    q = quote(X_train, X_query)
    room = min(q["capacity"]["monthly_tokens_remaining"], q["capacity"]["daily_tokens_remaining"])
    if q["total_quoted"] > room:
        raise RuntimeError(f"quoted {q['total_quoted']:,} tokens exceed the remaining quota {room:,}; no fit dispatched")
    backend = G.LiveBackend(G.CONFIG)
    usage_before = backend.usage()
    t0 = time.monotonic()
    res = G.execute_once(X_train, y_train, X_query, G.canonical_root(),
                         expected_input_sha256=manifest["input_fingerprint"], fingerprint=C.fingerprint,
                         description=manifest["fit_description"], log=C.log)
    usage_after = backend.usage()
    out = {"finished_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
           "wall_seconds": round(time.monotonic() - t0, 1), "reused_saved_predictions": res["reused_saved_predictions"],
           "receipt": res["receipt"], "usage_before": usage_before, "usage_after": usage_after,
           "tokens_monthly_delta": usage_after.get("monthly_usage", float("nan"))
                                   - usage_before.get("monthly_usage", float("nan"))}
    if not res["reused_saved_predictions"]:
        C.write_json(C.OUT / "thinking_run.json", out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--quote", action="store_true")
    mode.add_argument("--run", action="store_true")
    ap.add_argument("--spend-tokens", action="store_true", help="required with --run")
    a = ap.parse_args()
    X_train, y_train, X_query, _, manifest = C.load_upload()
    C.log(f"upload verified: X_train {X_train.shape}, X_query {X_query.shape}, fingerprint "
          f"{manifest['input_fingerprint'][:16]}...")
    if a.quote:
        out = quote(X_train, X_query)
        C.log(f"quoted: fit {out['thinking_fit']['estimated_cost']:,}, predict {out['thinking_predict']['estimated_cost']:,},"
              f" total {out['total_quoted']:,}; capacity {out['capacity']}")
        return 0
    if not a.spend_tokens:
        print("--run spends TabPFN tokens (one thinking fit + one prediction); add --spend-tokens to proceed")
        return 2
    out = run(X_train, y_train, X_query, manifest)
    C.log(f"done in {out['wall_seconds']} s; monthly tokens delta {out['tokens_monthly_delta']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
