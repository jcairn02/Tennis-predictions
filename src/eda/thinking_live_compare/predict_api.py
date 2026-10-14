"""TabPFN-3.5-Thinking on live matches: step 2, ONE paid prediction on the season fit (tennis-tabpfn env).

The query of query.py, sent once to the 2026 season fit of src/pipeline/thinking_api.py (re-attached from its saved
record with the SDK's load_model: no new fit). Built on the project's guarded client (src/eda/tabpfn_thinking58/guard.py,
tabpfn-client 0.6.0): the one POST is the SDK's `_predict` with its retry removed, and predict_slot.json is written
immediately before it. Once that file exists, nothing is sent again from this folder: an attempt with an unknown
outcome is never repeated, and saved probabilities are only read back.

    ./python_tabpfn.sh src/eda/thinking_live_compare/predict_api.py --out <folder> --spend-tokens
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_thinking58 import guard as G  # noqa: E402

SCHEMA = "tennis-thinking-live-compare-v1"
SLOT = ROOT / "data" / "studies" / "master_pipeline" / "thinking" / "template_2026-10-10" / "season2026"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _query_sha256(X: pd.DataFrame) -> str:
    import hashlib
    h = hashlib.sha256(b"thinking_live_compare/query/v1")
    h.update("\x00".join(map(str, X.columns)).encode())
    v = np.asarray(X, dtype="float64")
    h.update(np.ascontiguousarray(np.where(np.isnan(v), np.nan, v), dtype="<f8").tobytes())
    return h.hexdigest()


def predict(out: Path, spend_tokens: bool) -> dict:
    q = json.loads((out / "query.json").read_text(encoding="utf-8"))
    with np.load(out / "query.npz", allow_pickle=False) as z:
        X = pd.DataFrame(z["X"], columns=[str(c) for c in z["columns"]])
    if _query_sha256(X) != q["query_sha256"]:
        raise SystemExit("query.npz does not match query.json's query_sha256")
    fit = G._read(SLOT / "fit.json")
    complete = G._read(SLOT / "fit_complete.json")
    if fit["train_sha256"] != q["train_sha256"]:
        raise SystemExit("the query was built against other training rows than the fit's")
    if list(map(str, X.columns)) != fit["columns"]:
        raise SystemExit("the query's columns differ from the fit's")
    binding = {"schema": SCHEMA, "query_sha256": q["query_sha256"], "train_sha256": fit["train_sha256"],
               "fitted_train_set_id": fit["fitted_train_set_id"], "config_sha256": G._digest(fit["config"]),
               "model_path": fit["config"]["model_path"]}
    pred_path = out / "predictions.npz"
    if pred_path.exists():
        proba, p1, metadata, _ = G.load_predictions(pred_path, binding, len(X))
        print("saved probabilities read back; nothing sent")
        return {"p1": p1, "metadata": metadata}
    if (out / "predict_slot.json").exists():
        raise G.OnceOnlyError("this folder's prediction was dispatched with an unknown outcome; it is never repeated")
    if not spend_tokens:
        print("Refused: the prediction spends tokens; pass --spend-tokens (the owner asked for it on 13 Oct 2026).")
        raise SystemExit(2)

    backend = G.LiveBackend(dict(fit["config"]))
    account = backend.preflight()
    with np.load(SLOT / "train.npz", allow_pickle=False) as z:
        X_train = pd.DataFrame(z["X"], columns=[str(c) for c in z["columns"]])
    capacity = G.validate_account(account, X_train, X)
    G._publish_json(out / f"account_preflight_{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}.json",
                    {**account, "capacity": capacity})
    backend.resume(SLOT / "fitted_model.json")
    usage_before = account.get("usage", {})

    def before():
        G._write_exclusive(out / "predict_slot.json", {**binding, "operation": "predict", "attempted_at": _now(),
                                                       "query_rows": int(len(X)),
                                                       "status": "DISPATCHED_OR_OUTCOME_UNKNOWN"})
    try:
        print(f"dispatching the one prediction: {len(X)} rows on fit {fit['fitted_train_set_id']}")
        result = backend.predict(X, complete["fit_state"], before)
        if not (out / "predict_slot.json").exists():
            raise G.OnceOnlyError("the backend bypassed the prediction guard")
        proba, p1 = G._validate_probabilities(result, len(X))
        G._save_predictions(pred_path, proba, result["classes"], result.get("metadata", {}), binding)
    except Exception as exc:  # noqa: BLE001 - every failure after the slot is fail-closed
        raise G.OnceOnlyError(f"the prediction did not complete durably ({type(exc).__name__}: {exc}); inspect the "
                              f"receipts in {out} before any further action") from None
    try:
        usage_after = backend.usage()
    except Exception:  # noqa: BLE001 - informational
        usage_after = {}
    used = None
    if isinstance(usage_before.get("daily_usage"), (int, float)) and isinstance(usage_after.get("daily_usage"), (int, float)):
        used = usage_after["daily_usage"] - usage_before["daily_usage"]
    receipt = {**binding, "status": "COMPLETE", "completed_at": _now(), "query_rows": int(len(X)),
               "metadata": result.get("metadata", {}), "tokens_used_daily_counter": used, "usage_after": usage_after}
    G._publish_json(out / "predict_complete.json", receipt)
    print(json.dumps({"query_rows": len(X), "tokens_used_daily_counter": used,
                      "served": {k: receipt["metadata"].get(k) for k in ("package_version", "billing_model_version",
                                                                         "execution_mode", "cache_outcome")}},
                     indent=1, default=str))
    return {"p1": p1, "metadata": result.get("metadata", {})}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--spend-tokens", action="store_true")
    a = ap.parse_args()
    predict(a.out, a.spend_tokens)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
