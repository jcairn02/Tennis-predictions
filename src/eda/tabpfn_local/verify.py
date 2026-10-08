"""Check that the `tennis-tabpfn-local` env runs TabPFN-3.5 locally on the GPU, without the hosted API.

    ./python_tabpfn_local.sh src/eda/tabpfn_local/verify.py             every check; the first run downloads the
                                                                          checkpoint (876 MB, after a one-time licence
                                                                          check against the account behind TABPFN_TOKEN)
    ./python_tabpfn_local.sh src/eda/tabpfn_local/verify.py --offline   the same fits with TABPFN_TOKEN removed,
                                                                          Hugging Face offline and every socket blocked:
                                                                          once the weights are cached, a fit needs no
                                                                          account, token or network

Checks, each fatal: torch is a CUDA build with kernels for the RTX 5090 (compute capability 12.0) and multiplies
matrices on it in float32 and bfloat16; tabpfn is 9.1.0 and its default model is TabPFN-3.5; the cached checkpoint is
tabpfn-v3.5-20260909.safetensors with Hugging Face's size and sha256; a fit on sklearn's breast-cancer data (half for
training) runs on the GPU with accuracy above 0.9; a tall fit (30,000 training and 10,000 query rows) stays under
12 GB of GPU memory, which it can only do with runtime.prepare()'s attention fix (without it the training rows'
attention alone needs ~58 GB and stops at the allocator cap). Writes data/studies/tabpfn_local/verify.json
(verify_offline.json).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_local import runtime  # noqa: E402

OUT = ROOT / "data" / "studies" / "tabpfn_local"
TABPFN_VERSION = "9.1.0"
# as listed by Hugging Face for Prior-Labs/tabpfn_3_5 at revision 06bf2ba35c80 (read 6 Oct 2026)
CHECKPOINT_BYTES = 876_027_932
CHECKPOINT_SHA256 = "ece4d67eadfea42eb0e610df5189bea60cb7f31073d81e9c7a019b76eacf0be3"
TALL_PEAK_GB = 12.0


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def check(ok: bool, what: str) -> None:
    if not ok:
        raise SystemExit(f"FAILED: {what}")
    log(f"ok: {what}")


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def go_offline() -> None:
    """No token, Hugging Face offline, and any network connection raises: a fit that completes used none."""
    os.environ.pop("TABPFN_TOKEN", None)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TABPFN_NO_BROWSER"] = "1"

    def blocked(*_args, **_kwargs):
        raise RuntimeError("network access attempted in --offline mode")

    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    socket.create_connection = blocked
    socket.getaddrinfo = blocked


def gpu_checks(torch) -> dict:
    check(torch.cuda.is_available(), "torch sees a CUDA device")
    cap = torch.cuda.get_device_capability(0)
    arch = torch.cuda.get_arch_list()
    info = {"device": torch.cuda.get_device_name(0), "capability": list(cap), "arch_list": arch,
            "total_memory_gb": round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1)}
    check(f"sm_{cap[0]}{cap[1]}" in arch, f"torch has kernels for this GPU (sm_{cap[0]}{cap[1]} in {arch})")
    a = torch.randn(4096, 4096, device="cuda")
    b = (a @ a.T).float()
    with torch.autocast("cuda", dtype=torch.bfloat16):
        c = (a @ a.T).float()
    torch.cuda.synchronize()
    rel = float(((b - c).abs().max() / b.abs().max()).item())
    check(bool(torch.isfinite(b).all()) and rel < 0.05, f"float32 and bfloat16 matmuls run on the GPU (rel. gap {rel:.4f})")
    info["bf16_matmul_rel_gap"] = rel
    return info


def checkpoint(offline: bool) -> dict:
    from tabpfn.constants import ModelVersion
    from tabpfn.model_loading import download_model
    from tabpfn.settings import settings

    check(settings.tabpfn.model_version == ModelVersion.V3_5, "the package's default model is TabPFN-3.5")
    path = runtime.checkpoint_path()
    downloaded = False
    if not path.exists():
        if offline:
            raise SystemExit(f"FAILED: no checkpoint cached at {path}; run without --offline first")
        import tabpfn.browser_auth as auth
        # the licence check would otherwise save the API key in plain text under ~/.cache/tabpfn; like the API env,
        # keep it in TABPFN_TOKEN only (it is needed once, for this download)
        auth.save_token = lambda _token: None
        log(f"downloading {path.name} to {path.parent} (one-time licence check first)")
        t0 = time.monotonic()
        res = download_model(path, version=ModelVersion.V3_5, which="classifier")
        if res != "ok":
            for e in res:
                print(f"\n{type(e).__name__}: {e}", file=sys.stderr)
            raise SystemExit("FAILED: checkpoint download (see the errors above; a licence error means the TabPFN-3.5 "
                             "licence must be accepted at https://ux.priorlabs.ai/account/licenses with the account "
                             "behind TABPFN_TOKEN)")
        log(f"downloaded in {time.monotonic() - t0:.0f} s")
        downloaded = True
    size, digest = path.stat().st_size, sha256_file(path)
    check(size == CHECKPOINT_BYTES and digest == CHECKPOINT_SHA256,
          f"checkpoint matches Hugging Face's listing ({size:,} bytes, sha256 {digest[:12]}...)")
    return {"path": str(path), "bytes": size, "sha256": digest, "downloaded_this_run": downloaded}


def timed_fit(torch, clf, X_tr, y_tr, X_te) -> tuple:
    torch.cuda.reset_peak_memory_stats()
    t0 = time.monotonic()
    clf.fit(X_tr, y_tr)
    proba = clf.predict_proba(X_te)
    torch.cuda.synchronize()
    return proba, round(time.monotonic() - t0, 2), round(torch.cuda.max_memory_allocated() / 2**30, 2)


def toy_fit(torch) -> dict:
    import numpy as np
    from sklearn.datasets import load_breast_cancer
    from sklearn.metrics import accuracy_score, log_loss
    from sklearn.model_selection import train_test_split

    X, y = load_breast_cancer(return_X_y=True)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.5, random_state=42, stratify=y)
    clf = runtime.classifier(random_state=0)
    proba, seconds, peak = timed_fit(torch, clf, X_tr, y_tr, X_te)
    devices = sorted({str(p.device) for m in clf.models_ for p in m.parameters()})
    acc, ll = accuracy_score(y_te, proba.argmax(1)), log_loss(y_te, proba)
    check(devices == ["cuda:0"], f"the model's weights sit on the GPU ({devices})")
    check(np.allclose(proba.sum(1), 1) and acc > 0.9, f"breast cancer: accuracy {acc:.3f}, log loss {ll:.4f}")
    return {"train_rows": len(X_tr), "test_rows": len(X_te), "features": X.shape[1], "accuracy": acc, "log_loss": ll,
            "fit_predict_seconds": seconds, "peak_vram_gb": peak, "weights_device": devices}


def tall_fit(torch) -> dict:
    import numpy as np
    from sklearn.datasets import make_classification

    X, y = make_classification(n_samples=40_000, n_features=50, n_informative=20, random_state=0)
    clf = runtime.classifier(n_estimators=1, random_state=0)
    try:
        proba, seconds, peak = timed_fit(torch, clf, X[:30_000], y[:30_000], X[30_000:])
    except Exception as e:  # noqa: BLE001 - an out-of-memory error at the cap is the failure this check exists for
        raise SystemExit(f"FAILED: tall fit ({type(e).__name__}: {str(e)[:300]})") from None
    acc = float((proba.argmax(1) == y[30_000:]).mean())
    check(peak < TALL_PEAK_GB and np.isfinite(proba).all(),
          f"tall fit (30,000 x 50 train, 10,000 query): peak {peak} GB < {TALL_PEAK_GB} GB, {seconds} s, accuracy {acc:.3f}")
    return {"train_rows": 30_000, "test_rows": 10_000, "features": 50, "accuracy": acc, "fit_predict_seconds": seconds,
            "peak_vram_gb": peak}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    if a.offline:
        go_offline()
        log("offline: TABPFN_TOKEN removed, Hugging Face offline, sockets blocked")
    from importlib.metadata import version

    import torch

    res = {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "offline": a.offline,
           "versions": {"python": sys.version.split()[0], "torch": torch.__version__, "torch_cuda": torch.version.cuda,
                        "tabpfn": version("tabpfn"), "numpy": version("numpy"), "pandas": version("pandas"),
                        "scikit-learn": version("scikit-learn")}}
    log(f"versions: {res['versions']}")
    check(res["versions"]["tabpfn"] == TABPFN_VERSION, f"tabpfn is {TABPFN_VERSION}")
    res["gpu"] = gpu_checks(torch)
    res["checkpoint"] = checkpoint(a.offline)
    res["toy_fit"] = toy_fit(torch)
    res["tall_fit"] = tall_fit(torch)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / ("verify_offline.json" if a.offline else "verify.json")
    out.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    log(f"all checks passed; wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
