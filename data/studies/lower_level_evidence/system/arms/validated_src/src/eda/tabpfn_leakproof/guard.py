"""Once-only dispatch guard for the leak-proof refit's ONE paid TabPFN-3.5-Thinking fit and ONE paid prediction batch.

The owner authorised this single fit on 5 Oct 2026: the original fit's design (src/eda/tabpfn_thinking/) with the
solved-together (IOS) inputs rebuilt on the leak-proof match timeline (src/eda/match_timing/). It reuses the inspected
0.6.0 dispatch logic of the earlier studies with a distinct schema and a permanently fixed receipt directory; the earlier
studies' budgets and receipts are never read or changed. Token lookup as in the predictive-frontier guard (the process,
the environment or the normal login cache; never a browser login).

Adapted from the UFC project's src/eda/tabpfn35_vs_30_thinking/client_guard060.py (tabpfn-client 0.6.0), with three
changes for a long thinking fit on ~43k rows:

  * the fit is ASYNC: `ServiceClient._submit_fit_job` (one POST, which enqueues the job and returns its id) is the paid
    dispatch, wrapped with its SDK retry removed and a durable receipt written immediately before it; the returned
    fitted-train-set id is written to disk the moment the POST returns, before the (free) status polling, so a crash or
    a poll timeout never loses a paid fit. The SYNC path is not used: its `_fit` retries on a read timeout, and a
    thinking fit can outlast any HTTP timeout, which would pay for a second fit.
  * the fitted model is saved with the SDK's own `save_model()` as soon as the fit completes, so the one prediction
    (and any later, separately authorised one) never needs a new fit;
  * the budget is one fit and one prediction for the study. `ServiceClient._predict` (one POST) is wrapped the same way.

An attempt whose outcome is unknown (timeout, crash, any exception after the receipt) is never repeated automatically:
the slot stays consumed and the caller must inspect the receipts. Saved probabilities are re-used on every later call.
No network or SDK import happens at module import; `backend_factory` injects a fake backend for the offline tests.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

SDK_VERSION = "0.6.0"
SCHEMA = "tennis-tabpfn-leakproof-thinking-v1"
MODEL_PATH = "v3.5_default"          # explicit pin: TabPFN-3.5(-Thinking), never the server default
CONFIG = {
    "model_path": MODEL_PATH,
    "n_estimators": 8, "softmax_temperature": 0.9, "random_state": 0, "ignore_pretraining_limits": True,
    "thinking_mode": True, "thinking_effort": "high", "thinking_metric": "log_loss", "thinking_timeout_s": None,
    "http_timeout_s": 2700.0,
}
MAX_FIT_REQUESTS = 1
MAX_PREDICTION_REQUESTS = 1


class OnceOnlyError(RuntimeError):
    """The attempted request cannot safely be repeated automatically."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str)


def _digest(value) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _write_exclusive(path: Path, value) -> None:
    with Path(path).open("x", encoding="utf-8") as f:
        f.write(_json(value) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _read(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _publish_json(path: Path, value) -> None:
    path = Path(path)
    if path.exists():
        raise OnceOnlyError(f"Refusing to replace an existing receipt: {path.name}")
    temp = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
    _write_exclusive(temp, value)
    os.replace(temp, path)


def _consume(root: Path, operation: str, binding: dict) -> None:
    """Durably consume the study's one slot for ``operation`` immediately before its paid POST. A crash between this
    write and the POST consumes the slot and fails closed."""
    if operation not in ("fit", "predict"):
        raise ValueError("only the registered fit / predict slots exist")
    try:
        _write_exclusive(root / f"{operation}_slot.json", {**binding, "operation": operation, "attempted_at": _now(),
                                                            "status": "DISPATCHED_OR_OUTCOME_UNKNOWN"})
    except FileExistsError:
        raise OnceOnlyError(f"The study's one {operation} slot was already consumed") from None


@contextmanager
def _one_dispatch(service_class, method: str, before_dispatch, after_return=None):
    """Replace ``service_class.<method>`` (a classmethod wrapped by the SDK's backoff retry) by its undecorated function
    for one call, running ``before_dispatch()`` just before the raw POST and ``after_return(result)`` just after it."""
    descriptor = service_class.__dict__.get(method)
    if not isinstance(descriptor, classmethod):
        raise RuntimeError(f"Unsupported SDK dispatch descriptor for {method}")
    raw = getattr(descriptor.__func__, "__wrapped__", None)
    if raw is None:
        raise RuntimeError(f"The inspected SDK retry decorator on {method} has changed; review the guard")

    def guarded(cls, *args, **kwargs):
        before_dispatch()
        result = raw(cls, *args, **kwargs)
        if after_return is not None:
            after_return(result)
        return result

    setattr(service_class, method, classmethod(guarded))
    try:
        yield
    finally:
        setattr(service_class, method, descriptor)


def _safe_usage(value) -> dict:
    """Quota counters and reset times only; never identifiers or credentials."""
    if not isinstance(value, dict):
        return {}
    out = {}
    for key, item in value.items():
        low = str(key).lower()
        if any(w in low for w in ("access", "auth", "api_key", "secret", "password", "email")):
            continue
        if not any(w in low for w in ("usage", "limit", "reset", "remaining", "used", "daily", "monthly",
                                      "thinking", "quota")):
            continue
        if isinstance(item, dict):
            out[key] = _safe_usage(item)
        elif item is None or isinstance(item, (bool, int, float)):
            out[key] = item
        elif isinstance(item, str) and ("reset" in low or item.replace(".", "", 1).isdigit()):
            out[key] = item
    return out


class LiveBackend:
    """tabpfn-client 0.6.0 adapter. The token is authorised in memory only; dataset deduplication on, forced
    re-uploads off; api_mode ASYNC so that the paid dispatch is the single submit POST this guard wraps."""

    def __init__(self, config: dict):
        from importlib.metadata import version
        installed = version("tabpfn-client")
        if installed != SDK_VERSION:
            raise RuntimeError(f"This guard was inspected against tabpfn-client {SDK_VERSION}; installed {installed}")
        from tabpfn_client import set_access_token
        from tabpfn_client.client import ServiceClient
        from tabpfn_client.estimator import TabPFNClassifier
        from tabpfn_client.models import ApiMode, ClientOptions
        from tabpfn_client.options import get_opts
        from tabpfn_client.service_wrapper import UserAuthenticationClient
        token, _source = UserAuthenticationClient.resolve_token_with_source()
        if not token:
            raise RuntimeError("No TabPFN token in the process, environment, or normal login cache; no browser login is started")
        opts = get_opts()
        if opts.TABPFN_CLIENT_FORCE_REUPLOAD or not opts.TABPFN_CLIENT_DEDUP_DATASETS:
            raise RuntimeError("Disable forced re-uploads and enable dataset deduplication before this run")
        set_access_token(token)
        self.service = ServiceClient
        self.token = token
        self.config = dict(config)
        self._cls = TabPFNClassifier
        self._opts = ClientOptions(timeout=float(config["http_timeout_s"]))
        kwargs = {k: v for k, v in config.items() if k != "http_timeout_s"}
        self.model = TabPFNClassifier(**kwargs, api_mode=ApiMode.ASYNC, client_options=self._opts)

    def preflight(self) -> dict:
        if self.service.is_auth_token_outdated(self.token) is not True:
            raise RuntimeError("TabPFN authentication is not accepted; no model call made")
        settings = self.service.get_settings()
        if settings is None:
            raise RuntimeError("TabPFN server settings could not be fetched; no model call made")
        return {"sdk_version": SDK_VERSION, "authenticated": True,
                "usage": _safe_usage(self.service.get_api_usage(self.token)),
                "settings": settings.model_dump(mode="json"), "checked_at": _now()}

    def usage(self) -> dict:
        return _safe_usage(self.service.get_api_usage(self.token))

    def quote(self, X_train, X_query) -> dict:
        """Server quotes for the thinking fit and the thinking prediction; nothing is uploaded or reserved."""
        from tabpfn_client.cost import estimate_cost
        fit = estimate_cost(X_train, None, model_version="v3.5", operation="thinking_fit",
                            n_estimators=self.config["n_estimators"], thinking_effort=self.config["thinking_effort"])
        pred = estimate_cost(X_train, X_query, model_version="v3.5", operation="thinking_predict",
                             n_estimators=self.config["n_estimators"])
        return {"thinking_fit": fit.model_dump(mode="json"), "thinking_predict": pred.model_dump(mode="json")}

    def fit(self, X, y, before_dispatch, on_submitted, *, description: str) -> dict:
        with _one_dispatch(self.service, "_submit_fit_job", before_dispatch,
                           lambda resp: on_submitted(str(resp.fitted_train_set_id))):
            self.model.fit(X, y, description=description)
        return {"fitted_train_set_id": str(self.model.model_id_), "classes": [int(c) for c in self.model.classes_],
                "fit_timings": getattr(self.model, "fit_timings_", None), "trace_id": self.model._last_trace_id}

    def save_model(self, path: Path) -> dict:
        return self.model.save_model(path)

    def resume(self, record_path: Path) -> None:
        """Re-create the fitted estimator from a saved record (no request is made here)."""
        model = self._cls.load_model(record_path)
        model.client_options = self._opts
        self.model = model

    def wait_for_fit(self, fitted_id: str) -> dict:
        """Poll a submitted fit until it completes (free; the SDK's own loop)."""
        from uuid import UUID
        resp = self.service._wait_for_fit(UUID(fitted_id))
        return resp.model_dump(mode="json")

    def predict(self, X, fit_state, before_dispatch) -> dict:
        from sklearn.utils.validation import check_is_fitted
        check_is_fitted(self.model)
        if str(self.model.model_id_) != fit_state["fitted_train_set_id"]:
            raise OnceOnlyError("The estimator's fitted-train-set id does not match the saved fit")
        with _one_dispatch(self.service, "_predict", before_dispatch):
            proba = self.model.predict_proba(X)
        meta = dict(getattr(self.model, "_last_meta", {}) or {})
        keep = ("task", "package_version", "tabpfn_config", "test_set_num_rows", "test_set_num_cols", "n_estimators",
                "billing_model_version", "execution_mode", "cache_outcome")
        metadata = {k: meta[k] for k in keep if k in meta}
        try:
            metadata["timings"] = self.model.get_timings()
        except Exception:  # noqa: BLE001 - timings are informational
            pass
        return {"probabilities": proba, "classes": [int(c) for c in self.model.classes_], "metadata": metadata}


def validate_account(account: dict, X_train, X_query, *, model_version: str = "v3.5") -> dict:
    """Refuse a non-authenticated preflight, exhausted quota, or a payload beyond the model's limits (the server's
    enforcement stays authoritative)."""
    if account.get("authenticated") is not True:
        raise ValueError("An authenticated preflight is required")
    usage = account.get("usage", {})

    def number(key):
        v = usage.get(key)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise ValueError(f"Missing or invalid usage counter: {key}")
        return v

    for used, cap in (("daily_usage", "daily_limit"), ("monthly_usage", "monthly_limit")):
        if number(cap) > 0 and number(used) >= number(cap):
            raise ValueError(f"Account {used} has reached its limit")
    try:
        limits = account["settings"]["model_limits"][model_version]
        checks = {"train_set_max_rows": len(X_train), "test_set_max_rows": len(X_query),
                  "train_set_max_cells": X_train.size, "test_set_max_cells": X_query.size,
                  "max_cols": max(len(X_train.columns), len(X_query.columns)), "max_classes": 2}
        for name, size in checks.items():
            cap = limits[name]
            if isinstance(cap, bool) or not isinstance(cap, (int, float)) or cap <= 0 or size > cap:
                raise ValueError(f"Prepared inputs exceed or cannot verify {model_version} {name}")
        pairs = limits.get("predict_row_pairs_budget")
        if isinstance(pairs, (int, float)) and pairs > 0 and len(X_train) * len(X_query) > pairs:
            raise ValueError("The prediction would need more than one request (row-pair budget)")
    except (KeyError, TypeError):
        raise ValueError(f"Verified {model_version} model limits are required") from None
    return {"training_rows": len(X_train), "prediction_rows": len(X_query), "features": len(X_train.columns),
            "monthly_tokens_remaining": number("monthly_limit") - number("monthly_usage"),
            "daily_tokens_remaining": number("daily_limit") - number("daily_usage")}


def _validate_probabilities(result: dict, n_rows: int):
    import numpy as np
    classes = result["classes"]
    if len(classes) != 2 or set(classes) != {0, 1}:
        raise ValueError("Class labels must be exactly 0 and 1")
    proba = np.asarray(result["probabilities"], dtype=float)
    if proba.shape != (n_rows, 2) or not np.isfinite(proba).all():
        raise ValueError("Invalid probability shape or a non-finite value")
    if ((proba < 0) | (proba > 1)).any() or not np.allclose(proba.sum(axis=1), 1.0, atol=1e-6, rtol=0.0):
        raise ValueError("Probabilities must be bounded and sum to one")
    return proba, proba[:, list(classes).index(1)]


def _save_predictions(path: Path, proba, classes, metadata, binding) -> None:
    import numpy as np
    temp = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
    with temp.open("xb") as f:
        np.savez(f, probabilities=proba, classes=np.asarray(classes, dtype="int64"),
                 metadata=np.asarray(_json(metadata)), binding=np.asarray(_json(binding)))
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def load_predictions(path: Path, binding: dict | None, n_rows: int):
    import numpy as np
    with np.load(path, allow_pickle=False) as payload:
        saved_binding = json.loads(str(payload["binding"]))
        if binding is not None and saved_binding != binding:
            raise OnceOnlyError("The saved probabilities belong to another request")
        result = {"probabilities": payload["probabilities"], "classes": payload["classes"].tolist(),
                  "metadata": json.loads(str(payload["metadata"]))}
    proba, p_a = _validate_probabilities(result, n_rows)
    return proba, p_a, result["metadata"], saved_binding


def canonical_root() -> Path:
    return Path(__file__).resolve().parents[3] / "data/studies/tabpfn_leakproof/thinking"


def binding_for(input_sha256: str, config: dict) -> dict:
    return {"schema": SCHEMA, "input_sha256": input_sha256, "config_sha256": _digest(config),
            "model_path": config["model_path"]}


def execute_once(X_train, y_train, X_query, output_dir, *, expected_input_sha256: str, fingerprint,
                 description: str, config: dict | None = None, backend_factory=None, log=print) -> dict:
    """Fit once, predict once, and re-use the saved probabilities on every later call.

    ``fingerprint(X_train, y_train, X_query)`` must equal ``expected_input_sha256`` (the manifest's). Live dispatch
    must use the canonical study directory, so that a new directory can never reset the budget. A completed fit whose
    prediction was never dispatched resumes from the saved model record; a fit submitted but not known to be complete
    resumes by polling its saved id (free). Any dispatch with an unknown outcome is never repeated."""
    import numpy as np
    config = dict(CONFIG if config is None else config)
    if {k: v for k, v in config.items() if k != "http_timeout_s"} != {k: v for k, v in CONFIG.items()
                                                                       if k != "http_timeout_s"}:
        raise ValueError("The registered configuration is fixed; only the HTTP timeout may move")
    y = np.asarray(y_train)
    actual = fingerprint(X_train, y, X_query)
    if actual != expected_input_sha256:
        raise ValueError("Inputs do not match the frozen manifest fingerprint")
    root = Path(output_dir).resolve()
    if backend_factory is None and root != canonical_root().resolve():
        raise ValueError("Live dispatch must use the canonical study thinking directory")
    root.mkdir(parents=True, exist_ok=True)
    budget = {"schema": SCHEMA, "max_fit_requests": MAX_FIT_REQUESTS, "max_prediction_requests": MAX_PREDICTION_REQUESTS,
              "model_path": MODEL_PATH}
    budget_path = root / "budget.json"
    if budget_path.exists():
        if _read(budget_path) != budget:
            raise OnceOnlyError("The registered budget changed")
    else:
        _write_exclusive(budget_path, budget)
    binding = binding_for(actual, config)
    request = {**binding, "config": config, "training_rows": int(len(X_train)), "query_rows": int(len(X_query)),
               "feature_names": list(map(str, X_train.columns)), "positive_class": 1,
               "positive_class_meaning": "player A won", "description": description}
    request_path = root / "request.json"
    if request_path.exists():
        if _read(request_path) != request:
            raise OnceOnlyError("The study directory holds a different request")
    else:
        _write_exclusive(request_path, request)

    prediction_path, complete_path = root / "predictions.npz", root / "COMPLETE.json"
    if prediction_path.exists():
        for name in ("fit_slot.json", "predict_slot.json", "fit_complete.json"):
            if not (root / name).exists():
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
    if (root / "predict_slot.json").exists():
        raise OnceOnlyError("The prediction was dispatched with an unknown outcome; it will not be repeated")

    backend = (backend_factory or LiveBackend)(config)
    account = backend.preflight()
    capacity = validate_account(account, X_train, X_query)
    _publish_json(root / f"account_preflight_{uuid4().hex}.json", {**account, "capacity": capacity})
    fit_complete, model_record = root / "fit_complete.json", root / "fitted_model.json"
    submitted = root / "fit_submitted.json"

    if fit_complete.exists():                                   # the fit is done: resume from its saved record
        fit_state = _read(fit_complete)["fit_state"]
        if _read(fit_complete)["binding"] != binding or not model_record.exists():
            raise OnceOnlyError("The saved fit is not bound to this request")
        backend.resume(model_record)
        log("resuming from the saved fitted model (no new fit)")
    elif submitted.exists():                                    # submitted, completion unknown: poll its id (free)
        sub = _read(submitted)
        if sub["binding"] != binding:
            raise OnceOnlyError("The submitted fit is not bound to this request")
        log(f"polling the submitted fit {sub['fitted_train_set_id']} (free)")
        status = backend.wait_for_fit(sub["fitted_train_set_id"])
        record = {"tabpfn_client_version": SDK_VERSION, "task": "classification",
                  "model_id": sub["fitted_train_set_id"], "params": sub["params"],
                  "n_train_rows": int(len(X_train)), "classes": [0, 1]}
        _publish_json(model_record, record)
        backend.resume(model_record)
        fit_state = {"fitted_train_set_id": sub["fitted_train_set_id"], "classes": [0, 1], "status": status}
        _publish_json(fit_complete, {"binding": binding, "fit_state": fit_state, "completed_at": _now(),
                                     "resumed": True})
    elif (root / "fit_slot.json").exists():
        raise OnceOnlyError("The fit slot was consumed but no fit id was saved; inspect the receipts")
    else:
        params_holder = {}

        def before():
            _consume(root, "fit", binding)
            _write_exclusive(root / "fit_attempt.json", {**binding, "attempted_at": _now()})

        def on_submitted(fitted_id: str):
            _publish_json(submitted, {"binding": binding, "fitted_train_set_id": fitted_id, "submitted_at": _now(),
                                      "params": params_holder["params"]})

        params_holder["params"] = _model_params(backend)
        try:
            log("dispatching the one thinking fit (async submit; then free status polling)")
            fit_state = backend.fit(X_train, y.astype("int64"), before, on_submitted, description=description)
            if not (root / "fit_slot.json").exists() or not submitted.exists():
                raise OnceOnlyError("The backend bypassed the fit guard")
            if set(fit_state.get("classes", [])) != {0, 1}:
                raise ValueError("The fitted model did not keep both classes")
            backend.save_model(model_record)
            _publish_json(fit_complete, {"binding": binding, "fit_state": fit_state, "completed_at": _now(),
                                         "resumed": False})
        except Exception as exc:
            raise OnceOnlyError(f"The fit did not complete durably ({type(exc).__name__}: {exc}); inspect the "
                                f"receipts in {root} before any further action") from None
    try:
        log("dispatching the one prediction batch")
        result = backend.predict(X_query, fit_state, lambda: _consume(root, "predict", binding))
        if not (root / "predict_slot.json").exists():
            raise OnceOnlyError("The backend bypassed the prediction guard")
        proba, p_a = _validate_probabilities(result, len(X_query))
        _save_predictions(prediction_path, proba, result["classes"], result.get("metadata", {}), binding)
    except Exception as exc:
        raise OnceOnlyError(f"The prediction did not complete durably ({type(exc).__name__}: {exc}); inspect the "
                            f"receipts in {root} before any further action") from None
    receipt = {**binding, "status": "COMPLETE", "fit_requests_dispatched": 1, "prediction_requests_dispatched": 1,
               "prediction_sha256": hashlib.sha256(prediction_path.read_bytes()).hexdigest(),
               "query_rows": int(len(X_query)), "metadata": result.get("metadata", {})}
    _publish_json(complete_path, receipt)
    return {"p_a": np.asarray(p_a).copy(), "receipt": receipt, "reused_saved_predictions": False}


def _model_params(backend) -> dict:
    """The estimator's own hyperparameters as save_model() would record them (for a resume from a submitted id)."""
    model = getattr(backend, "model", None)
    if model is None or not hasattr(model, "get_params"):
        return {}
    params = {}
    for k, v in model.get_params(deep=False).items():
        if k == "client_options":
            continue
        params[k] = v.value if hasattr(v, "value") else v
    return params
