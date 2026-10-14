"""Dispatch guard for the surface-IOS study's TabPFN-3.5 (Plus, non-thinking) fits: one fit and one prediction per
registered slot, a slot being one arm in one expanding window (test season).

NOT USED FOR THE STUDY'S RESULTS. The owner first asked for TabPFN-3.5 Plus fits (6 Oct 2026); later that day another
session relayed the owner's concern about API costs, and that the local open-weight TabPFN-3.5 could be used instead.
No rule was recorded; the study left paid calls for the owner to approve, and its fits ran locally (run_local.py).
This guard is kept, tested offline, for a later API confirmation if the owner approves one. No paid request was made
through it (only free server quotes, before the relay).

The slots are the arms of the locked plan (plan.ARMS) times the seeds and seasons; nothing outside that list can be
dispatched, and each slot's budget is one fit and one prediction.

Built on the leak-proof refit's guard (src/eda/tabpfn_leakproof/guard.py, itself from the UFC project's inspected 0.6.0
dispatch logic) and reusing its generic pieces: the async fit is one wrapped submit POST with its SDK retry removed and a
durable receipt written immediately before it; the fitted-train-set id is saved the moment the POST returns; the fitted
model is saved before predicting; the prediction is one wrapped POST likewise. An attempt with an unknown outcome is
never repeated automatically: the slot stays consumed. Saved probabilities are re-used on every later call.

Non-thinking: model_path v3.5_default with thinking off is TabPFN-3.5 Plus (the API's plain 3.5; the UFC project's
tabpfn35_vs_30_thinking research). Its fit fits the preprocessing only; the prediction is the priced step.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from src.eda.tabpfn_leakproof import guard as LG
from src.eda.tabpfn_leakproof.guard import (OnceOnlyError, _consume, _now, _publish_json, _read, _write_exclusive,  # noqa: F401
                                             _digest, _save_predictions, _validate_probabilities, load_predictions,
                                             validate_account)

SDK_VERSION = LG.SDK_VERSION
SCHEMA = "tennis-tabpfn-surface-ios-plus-v1"
MODEL_PATH = "v3.5_default"          # TabPFN-3.5; with thinking off this is 3.5 Plus
BASE_CONFIG = {
    "model_path": MODEL_PATH,
    "n_estimators": 8, "softmax_temperature": 0.9, "random_state": 0, "ignore_pretraining_limits": True,
    "thinking_mode": False,
    "http_timeout_s": 2700.0,
}
MAX_FIT_REQUESTS = 1                 # per slot
MAX_PREDICTION_REQUESTS = 1          # per slot


def slot_config(random_state: int) -> dict:
    return {**BASE_CONFIG, "random_state": int(random_state)}


class LiveBackend(LG.LiveBackend):
    """The leak-proof guard's tabpfn-client 0.6.0 adapter (token in memory only, dedup on, ASYNC submit), with the
    non-thinking quote: the prediction is the priced operation."""

    def quote(self, X_train, X_query) -> dict:
        from tabpfn_client.cost import estimate_cost
        pred = estimate_cost(X_train, X_query, model_version="v3.5", operation="predict",
                             n_estimators=self.config["n_estimators"])
        return {"predict": pred.model_dump(mode="json")}


def canonical_root() -> Path:
    return Path(__file__).resolve().parents[3] / "data/studies/surface_ios/tabpfn"


def binding_for(slot: str, input_sha256: str, config: dict) -> dict:
    return {"schema": SCHEMA, "slot": slot, "input_sha256": input_sha256, "config_sha256": _digest(config),
            "model_path": config["model_path"]}


def execute_once(slot: str, registered: dict, X_train, y_train, X_query, *, expected_input_sha256: str,
                 fingerprint, description: str, backend_factory=None, root: Path | None = None, log=print) -> dict:
    """Fit once and predict once for ``slot`` (a key of ``registered``: slot -> its config), and re-use the saved
    probabilities on every later call. Live dispatch must use the canonical study directory, whose budget.json fixes the
    registered slots and their configurations the first time it is written."""
    import numpy as np
    if slot not in registered:
        raise ValueError(f"{slot} is not a registered slot")
    config = dict(registered[slot])
    y = np.asarray(y_train)
    actual = fingerprint(X_train, y, X_query)
    if actual != expected_input_sha256:
        raise ValueError("Inputs do not match the frozen manifest fingerprint")
    base = Path(root or canonical_root()).resolve()
    if backend_factory is None and base != canonical_root().resolve():
        raise ValueError("Live dispatch must use the canonical study directory")
    base.mkdir(parents=True, exist_ok=True)
    budget = {"schema": SCHEMA, "max_fit_requests_per_slot": MAX_FIT_REQUESTS,
              "max_prediction_requests_per_slot": MAX_PREDICTION_REQUESTS, "model_path": MODEL_PATH,
              "slots": {k: _digest(v) for k, v in sorted(registered.items())}}
    budget_path = base / "budget.json"
    if budget_path.exists():
        saved = _read(budget_path)
        if saved != budget:
            raise OnceOnlyError("The registered slots or their configurations changed")
    else:
        _write_exclusive(budget_path, budget)
    root_ = base / slot
    root_.mkdir(parents=True, exist_ok=True)
    binding = binding_for(slot, actual, config)
    request = {**binding, "config": config, "training_rows": int(len(X_train)), "query_rows": int(len(X_query)),
               "feature_names": list(map(str, X_train.columns)), "positive_class": 1,
               "positive_class_meaning": "player A won", "description": description}
    request_path = root_ / "request.json"
    if request_path.exists():
        if _read(request_path) != request:
            raise OnceOnlyError("The slot directory holds a different request")
    else:
        _write_exclusive(request_path, request)

    prediction_path, complete_path = root_ / "predictions.npz", root_ / "COMPLETE.json"
    if prediction_path.exists():
        for name in ("fit_slot.json", "predict_slot.json", "fit_complete.json"):
            if not (root_ / name).exists():
                raise OnceOnlyError(f"Saved predictions lack the receipt {name}")
        _, p_a, metadata, _ = load_predictions(prediction_path, binding, len(X_query))
        receipt = {**binding, "status": "COMPLETE", "fit_requests_dispatched": 1, "prediction_requests_dispatched": 1,
                   "prediction_sha256": hashlib.sha256(prediction_path.read_bytes()).hexdigest(),
                   "query_rows": int(len(X_query)), "metadata": metadata}
        if complete_path.exists():
            if _read(complete_path) != receipt:
                raise OnceOnlyError("The completion receipt or the prediction file changed")
        else:
            _publish_json(complete_path, receipt)
        return {"p_a": p_a.copy(), "receipt": receipt, "reused_saved_predictions": True}
    if (root_ / "predict_slot.json").exists():
        raise OnceOnlyError("The prediction was dispatched with an unknown outcome; it will not be repeated")

    backend = (backend_factory or LiveBackend)(config)
    account = backend.preflight()
    capacity = validate_account(account, X_train, X_query)
    _publish_json(root_ / f"account_preflight_{uuid4().hex}.json", {**account, "capacity": capacity})
    fit_complete, model_record = root_ / "fit_complete.json", root_ / "fitted_model.json"
    submitted = root_ / "fit_submitted.json"

    if fit_complete.exists():
        fit_state = _read(fit_complete)["fit_state"]
        if _read(fit_complete)["binding"] != binding or not model_record.exists():
            raise OnceOnlyError("The saved fit is not bound to this request")
        backend.resume(model_record)
        log(f"{slot}: resuming from the saved fitted model (no new fit)")
    elif submitted.exists():
        sub = _read(submitted)
        if sub["binding"] != binding:
            raise OnceOnlyError("The submitted fit is not bound to this request")
        log(f"{slot}: polling the submitted fit {sub['fitted_train_set_id']} (free)")
        status = backend.wait_for_fit(sub["fitted_train_set_id"])
        record = {"tabpfn_client_version": SDK_VERSION, "task": "classification",
                  "model_id": sub["fitted_train_set_id"], "params": sub["params"],
                  "n_train_rows": int(len(X_train)), "classes": [0, 1]}
        _publish_json(model_record, record)
        backend.resume(model_record)
        fit_state = {"fitted_train_set_id": sub["fitted_train_set_id"], "classes": [0, 1], "status": status}
        _publish_json(fit_complete, {"binding": binding, "fit_state": fit_state, "completed_at": _now(),
                                     "resumed": True})
    elif (root_ / "fit_slot.json").exists():
        raise OnceOnlyError("The fit slot was consumed but no fit id was saved; inspect the receipts")
    else:
        params_holder = {}

        def before():
            _consume(root_, "fit", binding)
            _write_exclusive(root_ / "fit_attempt.json", {**binding, "attempted_at": _now()})

        def on_submitted(fitted_id: str):
            _publish_json(submitted, {"binding": binding, "fitted_train_set_id": fitted_id, "submitted_at": _now(),
                                      "params": params_holder["params"]})

        params_holder["params"] = LG._model_params(backend)
        try:
            log(f"{slot}: dispatching the fit (async submit; then free status polling)")
            fit_state = backend.fit(X_train, y.astype("int64"), before, on_submitted, description=description)
            if not (root_ / "fit_slot.json").exists() or not submitted.exists():
                raise OnceOnlyError("The backend bypassed the fit guard")
            if set(fit_state.get("classes", [])) != {0, 1}:
                raise ValueError("The fitted model did not keep both classes")
            backend.save_model(model_record)
            _publish_json(fit_complete, {"binding": binding, "fit_state": fit_state, "completed_at": _now(),
                                         "resumed": False})
        except Exception as exc:
            raise OnceOnlyError(f"{slot}: the fit did not complete durably ({type(exc).__name__}: {exc}); inspect "
                                f"the receipts in {root_} before any further action") from None
    try:
        log(f"{slot}: dispatching the prediction")
        result = backend.predict(X_query, fit_state, lambda: _consume(root_, "predict", binding))
        if not (root_ / "predict_slot.json").exists():
            raise OnceOnlyError("The backend bypassed the prediction guard")
        proba, p_a = _validate_probabilities(result, len(X_query))
        _save_predictions(prediction_path, proba, result["classes"], result.get("metadata", {}), binding)
    except Exception as exc:
        raise OnceOnlyError(f"{slot}: the prediction did not complete durably ({type(exc).__name__}: {exc}); "
                            f"inspect the receipts in {root_} before any further action") from None
    receipt = {**binding, "status": "COMPLETE", "fit_requests_dispatched": 1, "prediction_requests_dispatched": 1,
               "prediction_sha256": hashlib.sha256(prediction_path.read_bytes()).hexdigest(),
               "query_rows": int(len(X_query)), "metadata": result.get("metadata", {})}
    _publish_json(complete_path, receipt)
    return {"p_a": np.asarray(p_a).copy(), "receipt": receipt, "reused_saved_predictions": False}
