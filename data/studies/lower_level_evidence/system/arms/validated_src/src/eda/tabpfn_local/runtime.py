"""Local TabPFN-3.5 on this machine (RTX 5090, Windows): the settings every local fit needs, in one place.

    from src.eda.tabpfn_local.runtime import classifier
    clf = classifier(n_estimators=8, softmax_temperature=0.9, random_state=0, ignore_pretraining_limits=True)

Run in the `tennis-tabpfn-local` env (./python_tabpfn_local.sh). For another estimator, call `prepare()` before fitting
and pass `model_path=str(checkpoint_path())`, `device="cuda"`, `memory_saving_mode=True` yourself. The settings:

1. Grouped-query attention. tabpfn 9.1.0 calls torch's attention with enable_gqa=True on any GPU of compute capability
   8 or more. Windows builds of torch have no FlashAttention kernels and the memory-efficient kernel rejects
   enable_gqa, so torch falls back to its MATH kernel, which builds every attention matrix in float32: rows x rows x 16
   heads x 4 bytes, about 100 GB for the 39,918-match tennis training set. Windows then silently spills the card's
   memory into system RAM and the run crawls (seen 6 Oct 2026). `prepare()` sends tabpfn down its own path for older
   torch: the key/value heads are repeated, and torch's memory-efficient kernel runs. On 5,000 tennis matches the
   predictions agree with the MATH path to 4e-4 at most (bfloat16 rounding); 39,918 training x 47,638 query rows peak
   at 7.7 GB.
2. A cap on torch's allocator (85% of the card), so a run that still outgrows the GPU stops with an out-of-memory error
   instead of spilling into system RAM.
3. memory_saving_mode=True: "auto" sizes its batches to the free GPU memory (the UFC project's local-TabPFN lesson).
"""
from __future__ import annotations

from pathlib import Path

CHECKPOINT = "tabpfn-v3.5-20260909.safetensors"
MEMORY_FRACTION = 0.85


def prepare(memory_fraction: float = MEMORY_FRACTION) -> None:
    """Repeat the key/value heads instead of asking torch for grouped-query attention, and cap torch's allocator."""
    import torch

    import tabpfn.architectures.shared.scaled_dot_product_attention as sdpa

    sdpa.gqa_is_supported = lambda: False
    torch.cuda.set_per_process_memory_fraction(memory_fraction)


def checkpoint_path() -> Path:
    from tabpfn.model_loading import get_cache_dir

    return get_cache_dir() / CHECKPOINT


def classifier(**kwargs):
    """A TabPFNClassifier on the cached TabPFN-3.5 checkpoint, on the GPU, with `prepare()` applied."""
    from tabpfn import TabPFNClassifier

    path = checkpoint_path()
    if not path.exists():
        raise FileNotFoundError(f"no checkpoint at {path}; run src/eda/tabpfn_local/verify.py first")
    prepare()
    return TabPFNClassifier(**{"model_path": str(path), "device": "cuda", "memory_saving_mode": True, **kwargs})
