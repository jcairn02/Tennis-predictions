"""Once-per-job guard for the non-thinking TabPFN-3.5 ("3.5-Plus") calls of this study.

The owner asked on 6 Oct 2026 to test this study's representation with TabPFN-3.5-Plus (the API's plain v3.5, thinking
off) rather than the costly thinking fits. Each registered job (build_frames.jobs: stage, arm, season, seed) gets one
fit and ONE billed prediction. Adapted from src/eda/tabpfn_leakproof/guard.py (tabpfn-client 0.6.0):

  * the fit is the SDK's synchronous upload-and-fit. In quota v3 a non-thinking fit is not a billed operation (the
    cost API knows only predict, thinking_fit, thinking_predict and cache_predict); a fit whose outcome is unknown may
    therefore be repeated, a prediction never;
  * the prediction is `ServiceClient._predict` (one POST) with the SDK's retry removed, a durable slot receipt written
    immediately before it, and the probabilities saved the moment they return;
  * a job whose prediction slot was consumed without saved probabilities is never repeated automatically;
  * saved probabilities are re-used on every later call, bound to the job's input fingerprint and configuration.

No network or SDK import happens at module import; `backend_factory` injects a fake backend for the offline tests.
"""
from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

SDK_VERSION = "0.6.0"
SCHEMA = "tennis-surface-elo-pieces-plus-v1"
MODEL_PATH = "v3.5_default"                  # TabPFN-3.5; with thinking off this is the hosted 3.5-Plus
CONFIG = {"model_path": MODEL_PATH, "n_estimators": 8, "softmax_temperature": 0.9, "ignore_pretraining_limits": True,
          "thinking_mode": False, "http_timeout_s": 1800.0}


class OnceOnlyError(RuntimeError):
    """The attempted request cannot safely be repeated automatically."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str)


def _write_exclusive(path: Path, value) -> None:
    with Path(path).open("x", encoding="utf-8") as f:
        f.write(_json(value) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _read(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical_root() -> Path:
    return Path(__file__).resolve().parents[3] / "data/studies/surface_elo_pieces/tabpfn"


def job_config(seed: int) -> dict:
    return {**CONFIG, "random_state": int(seed)}


def binding_for(job: dict, config: dict) -> dict:
    return {"schema": SCHEMA, "job": job["job"], "input_sha256": job["fingerprint"],
            "config_sha256": hashlib.sha256(_json({k: v for k, v in config.items() if k != "http_timeout_s"})
                                            .encode()).hexdigest(), "model_path": config["model_path"]}


@contextmanager
def _one_dispatch(service_class, method: str, before_dispatch):
    """Replace ``service_class.<method>`` (a classmethod wrapped by the SDK's backoff retry) by its undecorated
    function for one call, running ``before_dispatch()`` just before the raw POST."""
    descriptor = service_class.__dict__.get(method)
    if not isinstance(descriptor, classmethod):
        raise RuntimeError(f"Unsupported SDK dispatch descriptor for {method}")
    raw = getattr(descriptor.__func__, "__wrapped__", None)
    if raw is None:
        raise RuntimeError(f"The inspected SDK retry decorator on {method} has changed; review the guard")

    def guarded(cls, *args, **kwargs):
        before_dispatch()
        return raw(cls, *args, **kwargs)

    setattr(service_class, method, classmethod(guarded))
    try:
        yield
    finally:
        setattr(service_class, method, descriptor)


class LiveBackend:
    """tabpfn-client 0.6.0, thinking off, synchronous fit; the token is read from the process environment only."""

    def __init__(self, config: dict):
        from importlib.metadata import version
        installed = version("tabpfn-client")
        if installed != SDK_VERSION:
            raise RuntimeError(f"This guard was inspected against tabpfn-client {SDK_VERSION}; installed {installed}")
        from tabpfn_client import set_access_token
        from tabpfn_client.client import ServiceClient
        from tabpfn_client.estimator import TabPFNClassifier
        from tabpfn_client.models import ApiMode, ClientOptions
        from tabpfn_client.service_wrapper import UserAuthenticationClient
        token, _source = UserAuthenticationClient.resolve_token_with_source()
        if not token:
            raise RuntimeError("No TabPFN token in the process environment; no browser login is started")
        set_access_token(token)
        self.service, self.token = ServiceClient, token
        kwargs = {k: v for k, v in config.items() if k != "http_timeout_s"}
        self.model = TabPFNClassifier(**kwargs, api_mode=ApiMode.SYNC,
                                      client_options=ClientOptions(timeout=float(config["http_timeout_s"])))

    def usage(self) -> dict:
        u = self.service.get_api_usage(self.token) or {}
        return {k: v for k, v in u.items() if isinstance(v, (int, float)) and ("usage" in k or "limit" in k)}

    def fit(self, X, y) -> dict:
        self.model.fit(X, y)
        return {"fitted_train_set_id": str(self.model.model_id_), "classes": [int(c) for c in self.model.classes_],
                "fit_timings": getattr(self.model, "fit_timings_", None)}

    def predict(self, X, before_dispatch) -> dict:
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


def _validate(result: dict, n_rows: int):
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


def load_predictions(path: Path, binding: dict | None, n_rows: int):
    import numpy as np
    with np.load(path, allow_pickle=False) as payload:
        saved = json.loads(str(payload["binding"]))
        if binding is not None and saved != binding:
            raise OnceOnlyError("The saved probabilities belong to another request")
        result = {"probabilities": payload["probabilities"], "classes": payload["classes"].tolist(),
                  "metadata": json.loads(str(payload["metadata"]))}
    proba, p_a = _validate(result, n_rows)
    return p_a, result["metadata"]


def execute_job(job: dict, X_train, y_train, X_query, *, fingerprint, root: Path | None = None,
                backend_factory=None, log=print) -> dict:
    """Fit and predict one registered job once; re-use its saved probabilities on every later call."""
    import numpy as np
    config = job_config(job["seed"])
    actual = fingerprint(X_train, np.asarray(y_train), X_query)
    if actual != job["fingerprint"]:
        raise ValueError(f"{job['job']}: inputs do not match the registered fingerprint")
    if list(map(str, X_train.columns)) != job["columns"]:
        raise ValueError(f"{job['job']}: columns differ from the registered job")
    base = canonical_root() if root is None else Path(root)
    if backend_factory is None and base.resolve() != canonical_root().resolve():
        raise ValueError("Live dispatch must use the canonical study directory")
    d = base / job["job"]
    d.mkdir(parents=True, exist_ok=True)
    binding = binding_for(job, config)
    # the HTTP timeout is not part of the request's identity (audit G5): changing it alone must not lock a job
    request = {**binding, "config": {k: v for k, v in config.items() if k != "http_timeout_s"},
               "training_rows": int(len(X_train)), "query_rows": int(len(X_query)),
               "feature_names": job["columns"], "positive_class": 1, "positive_class_meaning": "player A won"}
    if (d / "request.json").exists():
        if _read(d / "request.json") != request:
            raise OnceOnlyError(f"{job['job']}: the directory holds a different request")
    else:
        _write_exclusive(d / "request.json", request)
    pred_path = d / "predictions.npz"
    if pred_path.exists():
        p_a, metadata = load_predictions(pred_path, binding, len(X_query))
        return {"p_a": p_a, "metadata": metadata, "reused": True}
    if (d / "predict_slot.json").exists():
        raise OnceOnlyError(f"{job['job']}: the prediction was dispatched with an unknown outcome; not repeated")
    backend = (backend_factory or LiveBackend)(config)
    usage_before = backend.usage()
    fit_state = backend.fit(X_train, np.asarray(y_train).astype("int64"))
    if set(fit_state.get("classes", [])) != {0, 1}:
        raise ValueError("The fitted model did not keep both classes")
    usage_after_fit = backend.usage()             # the audit's S3: separates what the fit and the prediction bill

    def consume():
        _write_exclusive(d / "predict_slot.json", {**binding, "attempted_at": _now(),
                                                   "status": "DISPATCHED_OR_OUTCOME_UNKNOWN"})

    try:
        result = backend.predict(X_query, consume)
        if not (d / "predict_slot.json").exists():
            raise OnceOnlyError("The backend bypassed the prediction guard")
        proba, p_a = _validate(result, len(X_query))
        tmp = pred_path.with_name(f"predictions.{uuid4().hex}.tmp")
        with tmp.open("xb") as f:
            np.savez(f, probabilities=proba, classes=np.asarray(result["classes"], dtype="int64"),
                     metadata=np.asarray(_json(result.get("metadata", {}))), binding=np.asarray(_json(binding)))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, pred_path)
    except Exception as exc:
        raise OnceOnlyError(f"{job['job']}: the prediction did not complete durably ({type(exc).__name__}: {exc}); "
                            f"inspect {d}") from None
    usage_after = backend.usage()
    _write_exclusive(d / "COMPLETE.json", {**binding, "status": "COMPLETE", "completed_at": _now(),
                                           "fit": fit_state, "metadata": result.get("metadata", {}),
                                           "usage_before": usage_before, "usage_after_fit": usage_after_fit,
                                           "usage_after": usage_after,
                                           "prediction_sha256": hashlib.sha256(pred_path.read_bytes()).hexdigest()})
    return {"p_a": np.asarray(p_a).copy(), "metadata": result.get("metadata", {}), "reused": False}
