"""TabPFN's training cache kept on disk: the daily fit without re-processing the training rows (part 2 of the build).

The decided fit (dp_fit's decided path, fit_mode "fit_preprocessors") pushes the instance's ~63k training rows through
the model at every call: about 41 of the 43-46 s a seed. fit_mode "fit_with_cache" pushes them through once and keeps
what test rows read (per estimator: the scaler and ECDF context, the inducing states, the 24 ICL layers' keys and values
of the training rows, the decoder keys). That depends only on the training rows, the seed, the configuration, the
library and the model weights, so it is built once per instance, season and seed, kept on disk, and each day's fit
reads it and predicts its query rows in seconds.

Why one cache per estimator. tabpfn 9.1.0's cached path batches the 8 estimators into one cache; with the decided
memory_saving_mode=True its peak-memory chunking then splits the batch by estimator but hands every chunk the whole
cache, and the attention wrapper slices the cache from estimator 0: every estimator attended to estimator 0's training
rows (the 0.18 gap of prediction_pipeline/cache_precision.json; diagnosis: dp_cachediag.py, process log part 2). With
max_batched_estimator_rows 0 each estimator has its own cache and runs alone, which is also what the decided path does
at this training size (its row budget, 32,768 a forward, is below the ~63k rows), and the cached predictions equal the
decided path's bit for bit (checked at full size; the tests check every seed on the replay's query rows).

What a cache is keyed by (key.json, compared before every use; any difference and the cache is rebuilt, never used):
the SHA-256 of the training matrix and labels, the season, the seed, the configuration (CONFIG, the engine settings),
the tabpfn and torch versions, the model weights' SHA-256, the GPU's name and this module's FORMAT.
Saved as tabpfn's own save_fitted_tabpfn_model saves (the init parameters, the fitted attributes, the inference
engine's state without the weights), but into a folder, uncompressed (the library zips it with deflate: tens of
seconds a seed for ~3.5 GB). About 3.5 GB a seed.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import shutil
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path

import numpy as np
import pandas as pd

import dp_common as DC

FORMAT = 1
ENGINE = {"fit_mode": "fit_with_cache", "kv_cache_precision": "auto"}
SETTINGS = {"max_batched_estimator_rows": 0}           # one cache per estimator (see above)
BLACKLIST = {"models_", "executor_", "configs_", "devices_"}   # as tabpfn's save_fitted_tabpfn_model
_WEIGHTS_SHA: dict[str, str] = {}


def root(instance: Path = DC.INSTANCE) -> Path:
    return DC.STATE / Path(instance).name / "tabpfn"


def folder(season: int, seed: int, instance: Path = DC.INSTANCE) -> Path:
    return root(instance) / f"season{int(season)}" / f"seed{int(seed)}"


def train_sha256(X_train: pd.DataFrame, y_train: np.ndarray) -> str:
    """The training matrix (column names, float64 values with one NaN pattern) and labels."""
    h = hashlib.sha256(b"daily_prediction/tabpfn_train/v1")
    h.update("\x00".join(map(str, X_train.columns)).encode())
    v = X_train.to_numpy(dtype="float64")
    h.update(np.ascontiguousarray(np.where(np.isnan(v), np.nan, v), dtype="<f8").tobytes())
    h.update(np.ascontiguousarray(np.asarray(y_train), dtype="<i8").tobytes())
    return h.hexdigest()


def weights_sha256() -> str:
    from src.eda.tabpfn_local import runtime
    p = str(runtime.checkpoint_path())
    if p not in _WEIGHTS_SHA:
        _WEIGHTS_SHA[p] = DC.sha256(p)
    return _WEIGHTS_SHA[p]


def key(X_train: pd.DataFrame, y_train: np.ndarray, season: int, seed: int, config: dict) -> dict:
    from importlib.metadata import version

    import torch

    from src.eda.tabpfn_local import runtime
    return {"format": FORMAT, "season": int(season), "seed": int(seed), "train_rows": int(len(X_train)),
            "train_sha256": train_sha256(X_train, y_train), "config": dict(config), "engine": dict(ENGINE),
            "settings": dict(SETTINGS), "memory_saving_mode": True, "gqa_patch": True,
            "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
            "weights": runtime.CHECKPOINT, "weights_sha256": weights_sha256(), "gpu": torch.cuda.get_device_name(0)}


@contextlib.contextmanager
def one_cache_per_estimator():
    from tabpfn.settings import settings
    before = {k: getattr(settings.tabpfn, k) for k in SETTINGS}
    try:
        for k, v in SETTINGS.items():
            setattr(settings.tabpfn, k, v)
        yield
    finally:
        for k, v in before.items():
            setattr(settings.tabpfn, k, v)


def build(X_train: pd.DataFrame, y_train: np.ndarray, seed: int, config: dict):
    """The cached classifier: the decided configuration and runtime, fit_with_cache, one cache per estimator."""
    from src.eda.tabpfn_local import runtime
    with one_cache_per_estimator():
        clf = runtime.classifier(**config, random_state=seed, **ENGINE)
        clf.fit(X_train, y_train)
    n, m = len(clf.executor_.kv_caches), len(clf.executor_.ensemble_members)
    if n != m or any(len(g) != 1 for g in clf.executor_.cache_groups):
        raise RuntimeError(f"expected one cache per estimator, got {n} caches for {m} estimators")
    return clf


def predict(clf, X: pd.DataFrame) -> np.ndarray:
    with one_cache_per_estimator():
        p = clf.predict_proba(X)
    if [int(c) for c in clf.classes_] != [0, 1] or not np.isfinite(p).all():
        raise RuntimeError("invalid probabilities from the cached classifier")
    return p[:, 1]


def size_bytes(path: Path) -> int:
    return sum(f.stat().st_size for f in Path(path).rglob("*") if f.is_file())


def _retry(fn, *args, tries: int = 60, wait_s: float = 2.0):
    """Windows refuses a delete or a rename (WinError 5) while another process (an antivirus scan of a file just
    written) holds the file open: wait and retry, up to two minutes."""
    for i in range(tries):
        try:
            return fn(*args)
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(wait_s)


def save(clf, path: Path, k: dict) -> dict:
    """tabpfn's save_fitted_tabpfn_model's three parts, into the seed's folder, uncompressed. key.json marks a
    complete cache (status() requires it and the three parts): an old one is deleted before anything is written and
    the new one written last, so a half-written cache is never used. (No folder rename: on 11 Oct a rename into place
    was refused once, a scan holding the new 3.6 GB file.)"""
    import joblib
    import torch
    t0 = time.monotonic()
    path = Path(path)
    tmp = path
    tmp.mkdir(parents=True, exist_ok=True)
    if (tmp / "key.json").exists():
        _retry((tmp / "key.json").unlink)
    params = clf.get_params(deep=False)
    params = {n: (asdict(v) if is_dataclass(v) and not isinstance(v, type)
                  else (str(v) if isinstance(v, torch.dtype) else v)) for n, v in params.items()}
    params["device"] = "cuda"
    params["__class_name__"] = type(clf).__name__
    (tmp / "init_params.json").write_text(json.dumps(params), encoding="utf-8")
    fitted = {n: (copy.deepcopy(v).to("cpu") if isinstance(v, torch.nn.Module)
                  else (v.to("cpu") if isinstance(v, torch.Tensor) else v))
              for n, v in vars(clf).items() if n.endswith("_") and n not in BLACKLIST}
    joblib.dump(fitted, tmp / "fitted_attrs.joblib")
    clf.executor_.save_state_except_model_weights(tmp / "executor_state.joblib")
    _retry(DC.write_json, tmp / "key.json", k)
    return {"save_seconds": round(time.monotonic() - t0, 2), "bytes": size_bytes(path)}


def stored_key(path: Path) -> dict | None:
    f = Path(path) / "key.json"
    return DC.read_json(f) if f.exists() else None


def load(path: Path):
    """tabpfn's load_fitted_tabpfn_model from the folder save() wrote, on the GPU, with the runtime's settings."""
    import joblib
    import torch
    from tabpfn import TabPFNClassifier
    from tabpfn.inference import InferenceEngine

    from src.eda.tabpfn_local import runtime
    path = Path(path)
    runtime.prepare()
    params = json.loads((path / "init_params.json").read_text(encoding="utf-8"))
    if params.pop("__class_name__") != "TabPFNClassifier":
        raise TypeError(f"{path}: not a TabPFNClassifier")
    prec = params.get("inference_precision")
    if isinstance(prec, str) and prec.startswith("torch."):
        params["inference_precision"] = getattr(torch, prec.split(".")[1])
    params["device"] = "cuda"
    est = TabPFNClassifier(**params)
    est._initialize_model_variables()
    for n, v in joblib.load(path / "fitted_attrs.joblib").items():
        setattr(est, n, v)
    est.executor_ = InferenceEngine.load_state(path / "executor_state.joblib", est.models_)
    est.to("cuda")
    return est


def status(path: Path, k: dict) -> str:
    """"usable" when the folder holds a complete cache whose key equals k; else "missing" or "stale: <fields>"."""
    old = stored_key(path)
    if old is None:
        return "missing"
    if any(not (Path(path) / f).exists() for f in ("init_params.json", "fitted_attrs.joblib", "executor_state.joblib")):
        return "stale: incomplete"
    diff = sorted(n for n in set(k) | set(old) if k.get(n) != old.get(n))
    return "usable" if not diff else "stale: " + ", ".join(diff)


def get(X_train: pd.DataFrame, y_train: np.ndarray, season: int, seed: int, config: dict,
        instance: Path = DC.INSTANCE, rebuild: bool = False) -> tuple[object, dict]:
    """The seed's cached classifier: loaded when its folder's key equals today's, else built and saved (replacing a
    stale one). Returns (classifier, record)."""
    k = key(X_train, y_train, season, seed, config)
    path = folder(season, seed, instance)
    st = status(path, k)
    rec: dict = {"cache": str(path)}
    if st == "usable" and not rebuild:
        t0 = time.monotonic()
        clf = load(path)
        rec.update({"how": "loaded", "load_seconds": round(time.monotonic() - t0, 2)})
        return clf, rec
    rec["how"] = "rebuilt (forced)" if st == "usable" else ("built" if st == "missing" else f"rebuilt ({st})")
    t0 = time.monotonic()
    clf = build(X_train, y_train, seed, config)
    rec["build_seconds"] = round(time.monotonic() - t0, 2)
    rec.update(save(clf, path, k))
    return clf, rec
