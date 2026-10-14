"""TabPFN-3.5-Thinking on the hosted API: the free quote, and the ONE paid season fit (runs in tennis-tabpfn).

    ./python_tabpfn.sh -m src.pipeline.thinking_api quote --folder <thinking/<instance>/season<Y>>
    ./python_tabpfn.sh -m src.pipeline.thinking_api fit   --folder <...> --spend-tokens

Built on the project's guarded client, src/eda/tabpfn_thinking58/guard.py (tabpfn-client 0.6.0): its LiveBackend
(async submit; the SDK's retry removed from the one paid POST; dataset deduplication on; the token resolved from the
process, the environment or the login cache, never a browser login), its account check and its write-once receipts.
The flow is the guard's execute_once, fit part only:
    budget.json, request.json      the slot's registration (one fit per instance and season); a changed request is refused
    fit_slot.json                  written immediately before the paid POST; once it exists, no new fit is ever sent
    fit_submitted.json             the fitted-train-set id, written the moment the POST returns (before free polling)
    fitted_model.json              the SDK's save_model() record (load_model re-attaches without a new fit)
    fit_complete.json, fit.json    the outcome; fit.json is what the daily pipeline's dp_fit reads (agreed 10:20):
                                   fitted_train_set_id, train_sha256, columns, rows, config, the tokens used
A fit submitted but not known complete resumes by polling its saved id (free). An attempt with an unknown outcome is
never repeated. The served checkpoint is known at the first prediction (the predict metadata); it is recorded then.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_thinking58 import guard as G  # noqa: E402  (no SDK import at module import)

SCHEMA = "tennis-master-pipeline-thinking-season-v1"
GRID_PRICES = 92            # the daily query: 91 grid prices and the match's own, both orientations


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _load(folder: Path):
    import numpy as np
    import pandas as pd
    sys.path.insert(0, str(ROOT))
    from src.pipeline.thinking import train_sha256
    prep = json.loads((folder / "prepared.json").read_text(encoding="utf-8"))
    with np.load(folder / "train.npz", allow_pickle=False) as z:
        X = pd.DataFrame(z["X"], columns=[str(c) for c in z["columns"]])
        y = z["y"].astype("int64")
        test_rows = int(z["test_rows"])
    if train_sha256(X.columns, X.to_numpy(), y) != prep["train_sha256"]:
        raise RuntimeError("train.npz does not match prepared.json's train_sha256; prepare again")
    return prep, X, y, test_rows


def _daily_query(X, matches: int):
    """A query of the daily size (only its shape reaches the cost estimate)."""
    import numpy as np
    import pandas as pd
    return pd.DataFrame(np.zeros((matches * GRID_PRICES * 2, X.shape[1])), columns=X.columns)


def quote(folder: Path, daily_matches: int, backend_factory=None) -> dict:
    """Free: the account's preflight (authentication, quota) and the server's cost estimates for this season's fit
    and for a daily prediction of `daily_matches` matches. Nothing is uploaded, reserved or paid."""
    prep, X, y, _ = _load(folder)
    backend = (backend_factory or G.LiveBackend)(dict(G.CONFIG))
    account = backend.preflight()
    Xq = _daily_query(X, daily_matches)
    capacity = G.validate_account(account, X, Xq)
    q = backend.quote(X, Xq)
    fit_q = q["thinking_fit"]
    pred_q = q["thinking_predict"]
    summary = {"season": prep["season"], "training_rows": len(X), "features": X.shape[1],
               "fit_quote": fit_q, "daily_predict_quote": pred_q, "daily_matches": daily_matches,
               "daily_tokens_remaining": capacity.get("daily_tokens_remaining"),
               "monthly_tokens_remaining": capacity.get("monthly_tokens_remaining"),
               "note": "past bills were 25% of the quote (4 of 4 runs, the Thinking studies); a quote is not a bill"}
    rec = {"schema": SCHEMA, "made_at": _now(), "summary": summary, "usage": account.get("usage"),
           "model_limits": account.get("settings", {}).get("model_limits", {}).get("v3.5")}
    path = folder / f"quote_{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}.json"
    path.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=1, default=str))
    return rec


def fit(folder: Path, backend_factory=None, log=print) -> dict:
    """The one paid fit of this instance and season (the caller passed --spend-tokens)."""
    prep, X, y, _ = _load(folder)
    config = dict(G.CONFIG)
    binding = {"schema": SCHEMA, "train_sha256": prep["train_sha256"], "config_sha256": G._digest(config),
               "model_path": config["model_path"], "instance": prep["instance"], "season": prep["season"]}
    budget = {"schema": SCHEMA, "max_fit_requests": 1, "model_path": config["model_path"],
              "instance": prep["instance"], "season": prep["season"]}
    if (folder / "budget.json").exists():
        if G._read(folder / "budget.json") != budget:
            raise G.OnceOnlyError("The registered budget changed")
    else:
        G._write_exclusive(folder / "budget.json", budget)
    request = {**binding, "config": config, "training_rows": int(len(X)), "feature_names": list(map(str, X.columns)),
               "positive_class": 1, "positive_class_meaning": "player A won",
               "description": f"Tennis match winner, season {prep['season']} trained on {prep['train_from']}-"
                              f"{prep['train_through']}: the current best model's 57 pre-match inputs"}
    if (folder / "request.json").exists():
        if G._read(folder / "request.json") != request:
            raise G.OnceOnlyError("This season's folder holds a different request (rebuilt instance? use a new instance)")
    else:
        G._write_exclusive(folder / "request.json", request)
    if (folder / "fit.json").exists():
        log("this instance and season already has its fit; nothing sent")
        return G._read(folder / "fit.json")

    backend = (backend_factory or G.LiveBackend)(config)
    account = backend.preflight()
    G.validate_account(account, X, _daily_query(X, 1))
    G._publish_json(folder / f"account_preflight_{uuid4().hex}.json", account)
    complete, record, submitted = folder / "fit_complete.json", folder / "fitted_model.json", folder / "fit_submitted.json"
    usage_before = account.get("usage", {})
    if complete.exists():
        fit_state = G._read(complete)["fit_state"]
    elif submitted.exists():
        sub = G._read(submitted)
        if sub["binding"] != binding:
            raise G.OnceOnlyError("The submitted fit is not bound to this request")
        log(f"polling the submitted fit {sub['fitted_train_set_id']} (free)")
        status = backend.wait_for_fit(sub["fitted_train_set_id"])
        G._publish_json(record, {"tabpfn_client_version": G.SDK_VERSION, "task": "classification",
                                 "model_id": sub["fitted_train_set_id"], "params": sub["params"],
                                 "n_train_rows": int(len(X)), "classes": [0, 1]})
        fit_state = {"fitted_train_set_id": sub["fitted_train_set_id"], "classes": [0, 1], "status": status}
        G._publish_json(complete, {"binding": binding, "fit_state": fit_state, "completed_at": _now(), "resumed": True})
    elif (folder / "fit_slot.json").exists():
        raise G.OnceOnlyError("The fit slot was consumed but no fit id was saved; inspect the receipts")
    else:
        params = G._model_params(backend)

        def before():
            G._write_exclusive(folder / "fit_slot.json", {**binding, "operation": "fit", "attempted_at": _now(),
                                                          "status": "DISPATCHED_OR_OUTCOME_UNKNOWN"})

        def on_submitted(fitted_id: str):
            G._publish_json(submitted, {"binding": binding, "fitted_train_set_id": fitted_id, "submitted_at": _now(),
                                        "params": params})
        try:
            log("dispatching the one Thinking fit (async submit, then free status polling)")
            fit_state = backend.fit(X, y, before, on_submitted, description=request["description"])
            if not (folder / "fit_slot.json").exists() or not submitted.exists():
                raise G.OnceOnlyError("The backend bypassed the fit guard")
            if set(fit_state.get("classes", [])) != {0, 1}:
                raise ValueError("The fitted model did not keep both classes")
            backend.save_model(record)
            G._publish_json(complete, {"binding": binding, "fit_state": fit_state, "completed_at": _now(),
                                       "resumed": False})
        except Exception as exc:  # noqa: BLE001 - every failure after the slot is fail-closed
            raise G.OnceOnlyError(f"The fit did not complete durably ({type(exc).__name__}: {exc}); inspect the "
                                  f"receipts in {folder} before any further action") from None
    try:
        usage_after = backend.usage()
    except Exception:  # noqa: BLE001 - informational
        usage_after = {}
    used = None
    if isinstance(usage_before.get("daily_usage"), (int, float)) and isinstance(usage_after.get("daily_usage"), (int, float)):
        used = usage_after["daily_usage"] - usage_before["daily_usage"]
    out = {"schema": SCHEMA, "instance": prep["instance"], "season": prep["season"],
           "fitted_train_set_id": fit_state["fitted_train_set_id"], "model_record": "fitted_model.json",
           "train_sha256": prep["train_sha256"], "columns": prep["columns"], "training_rows": prep["training_rows"],
           "train_from": prep["train_from"], "train_through": prep["train_through"], "config": config,
           "sdk_version": G.SDK_VERSION, "tokens_used_daily_counter": used, "usage_after": usage_after,
           "served_checkpoint": None, "server_package_version": None,
           "served_note": "known at the first prediction (predict metadata); dp_fit records and checks it",
           "made_at": _now()}
    G._publish_json(folder / "fit.json", out)
    log(f"fit saved: {out['fitted_train_set_id']}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["quote", "fit"])
    ap.add_argument("--folder", required=True, type=Path)
    ap.add_argument("--daily-matches", type=int, default=30)
    ap.add_argument("--spend-tokens", action="store_true", help="required for fit: the one paid fit")
    a = ap.parse_args()
    if a.mode == "quote":
        quote(a.folder, a.daily_matches)
    else:
        if not a.spend_tokens:
            print("Refused: a fit spends tokens; pass --spend-tokens (owner approval required).")
            return 2
        fit(a.folder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
