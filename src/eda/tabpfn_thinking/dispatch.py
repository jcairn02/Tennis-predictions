"""The study's calls to the hosted TabPFN API (Prior Labs). Runs in the isolated `tennis-tabpfn` env.

    ./python_tabpfn.sh src/eda/tabpfn_thinking/dispatch.py --preflight   account quota and the server's model limits
                                                                          (free: no upload, no inference)
    ./python_tabpfn.sh src/eda/tabpfn_thinking/dispatch.py --quote       the server's token quotes for the exact upload
                                                                          (free: only row and column counts are sent)
    ./python_tabpfn.sh src/eda/tabpfn_thinking/dispatch.py --dry-run     both of the above, plus the client-side
                                                                          validation of the request (no paid call)
    ./python_tabpfn.sh src/eda/tabpfn_thinking/dispatch.py --run --spend-tokens
                                                                          the ONE paid thinking fit and the ONE paid
                                                                          prediction batch, through guard.execute_once

Every mode first checks that the upload files are the ones build_frame.py wrote (sha256 and the value fingerprint in
manifest.json). The token is read from TABPFN_TOKEN and never written anywhere. Outputs, in
data/studies/tabpfn_thinking/: preflight.json, quotes.json, and for --run the receipts in thinking/ plus
thinking_run.json (account usage before and after, timings, the served model).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_thinking import common as T  # noqa: E402
from src.eda.tabpfn_thinking import guard as G  # noqa: E402


def load_upload() -> tuple[pd.DataFrame, np.ndarray, pd.DataFrame, dict]:
    manifest = json.loads((T.OUT / "manifest.json").read_text(encoding="utf-8"))
    for name, sha in manifest["upload_sha256"].items():
        actual = T.sha256_file(T.UPLOAD / name)
        if actual != sha:
            raise RuntimeError(f"upload/{name} differs from the manifest; rebuild with build_frame.py")
    X_train = pd.read_parquet(T.UPLOAD / "X_train.parquet")
    y_train = np.load(T.UPLOAD / "y_train.npy")
    X_query = pd.read_parquet(T.UPLOAD / "X_query.parquet")
    if list(X_train.columns) != manifest["names"] or list(X_query.columns) != manifest["names"]:
        raise RuntimeError("upload columns differ from the manifest's inputs")
    fp = T.fingerprint(X_train, y_train, X_query)
    if fp != manifest["input_fingerprint"]:
        raise RuntimeError("the value fingerprint differs from the manifest")
    return X_train, y_train, X_query, manifest


def preflight(X_train, X_query) -> dict:
    backend = G.LiveBackend(G.CONFIG)
    account = backend.preflight()
    capacity = G.validate_account(account, X_train, X_query)
    out = {"checked_at": account["checked_at"], "sdk_version": account["sdk_version"], "usage": account["usage"],
           "model_limits_v3.5": account["settings"]["model_limits"]["v3.5"],
           "default_model_version": account["settings"].get("default_model_version"),
           "async_settings": account["settings"].get("async_settings"), "capacity": capacity}
    T.write_json(T.OUT / "preflight.json", out)
    return out


def quote(X_train, X_query) -> dict:
    backend = G.LiveBackend(G.CONFIG)
    q = backend.quote(X_train, X_query)
    half = backend.quote(X_train, X_query.iloc[: len(X_query) // 2])
    out = {"quoted_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "config": G.CONFIG,
           "shapes": {"X_train": list(X_train.shape), "X_query": list(X_query.shape)},
           "thinking_fit": q["thinking_fit"], "thinking_predict_both_orientations": q["thinking_predict"],
           "thinking_predict_one_orientation": half["thinking_predict"],
           "total_quoted": q["thinking_fit"]["estimated_cost"] + q["thinking_predict"]["estimated_cost"],
           "note": "server quotes from row/column counts only; the UFC study (2026-09-19) was billed below its quotes"}
    T.write_json(T.OUT / "quotes.json", out)
    return out


def dry_run(X_train, y_train, X_query) -> dict:
    """Build the request exactly as fit() would, client-side only (no request is sent)."""
    from tabpfn_client import estimator as E
    from tabpfn_client.models import ApiMode, ClientOptions
    kwargs = {k: v for k, v in G.CONFIG.items() if k != "http_timeout_s"}
    model = E.TabPFNClassifier(**kwargs, api_mode=ApiMode.ASYNC,
                               client_options=ClientOptions(timeout=G.CONFIG["http_timeout_s"]))
    cfg = model._get_tabpfn_config()
    E.validate_train_set(X_train, y_train)
    systems = E._build_tabpfn_systems(model.paper_version, True)
    thinking = E._build_thinking_config(X_train, enabled=True, effort=model.thinking_effort,
                                        timeout_secs=model.thinking_timeout_s, metric=model.thinking_metric)
    return {"tabpfn_config": cfg.model_dump(mode="json"), "systems": list(systems),
            "thinking_config": thinking.model_dump(mode="json") if thinking is not None else None}


def run(X_train, y_train, X_query, manifest) -> dict:
    usage_before = G.LiveBackend(G.CONFIG).usage()
    t0 = time.time()
    res = G.execute_once(X_train, y_train, X_query, G.canonical_root(),
                         expected_input_sha256=manifest["input_fingerprint"], fingerprint=T.fingerprint,
                         description=manifest["fit_description"], backend_factory=None, log=T.log)
    seconds = time.time() - t0
    usage_after = G.LiveBackend(G.CONFIG).usage()
    out = {"finished_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "wall_seconds": round(seconds, 1),
           "reused_saved_predictions": res["reused_saved_predictions"], "receipt": res["receipt"],
           "usage_before": usage_before, "usage_after": usage_after,
           "tokens_monthly_delta": (usage_after.get("monthly_usage", np.nan) - usage_before.get("monthly_usage", np.nan))}
    if not res["reused_saved_predictions"]:
        T.write_json(T.OUT / "thinking_run.json", out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--quote", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--run", action="store_true")
    ap.add_argument("--spend-tokens", action="store_true", help="required with --run")
    a = ap.parse_args()
    X_train, y_train, X_query, manifest = load_upload()
    T.log(f"upload verified: X_train {X_train.shape}, X_query {X_query.shape}, fingerprint "
          f"{manifest['input_fingerprint'][:16]}...")
    if a.preflight:
        out = preflight(X_train, X_query)
        T.log(f"usage {out['usage']}; capacity {out['capacity']}")
    elif a.quote:
        out = quote(X_train, X_query)
        T.log(f"quoted: fit {out['thinking_fit']['estimated_cost']:,}, predict (both orientations) "
              f"{out['thinking_predict_both_orientations']['estimated_cost']:,}, one orientation "
              f"{out['thinking_predict_one_orientation']['estimated_cost']:,}; total {out['total_quoted']:,}")
    elif a.dry_run:
        pre = preflight(X_train, X_query)
        q = quote(X_train, X_query)
        req = dry_run(X_train, y_train, X_query)
        T.write_json(T.OUT / "dry_run.json", {"request_preview": req, "quote_total": q["total_quoted"],
                                              "capacity": pre["capacity"]})
        T.log(f"dry run ok: thinking config {req['thinking_config']}; quoted total {q['total_quoted']:,}; "
              f"capacity {pre['capacity']}")
    else:
        if not a.spend_tokens:
            print("--run spends TabPFN tokens (one thinking fit + one prediction); add --spend-tokens to proceed")
            return 2
        out = run(X_train, y_train, X_query, manifest)
        T.log(f"done in {out['wall_seconds']} s; monthly tokens delta {out['tokens_monthly_delta']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
