"""Canonical hashes of the arrays a family's saved state read (its history slice before the checkpoint day).

A checkpoint is valid on today's tables only if every array its state consumed is unchanged: the manifest stores one
SHA-256 per family over those arrays, recomputed on today's tables before every resume. Each array is hashed with its
name, dtype class and shape; floats as little-endian float64 with one NaN bit pattern (a float32 table read back as
float64 hashes as its float64 values); integers and booleans as int64; text and objects as UTF-8, NUL-separated (None
and NaN as one marker). Order matters: the arrays are hashed in the order the state read them.
"""
from __future__ import annotations

import hashlib

import numpy as np

NA = "\x00<NA>\x00"


def _canon(v) -> tuple[str, bytes]:
    a = np.asarray(v)
    if a.dtype.kind == "f":
        x = np.ascontiguousarray(a, dtype="<f8")
        x = np.where(np.isnan(x), np.nan, x).astype("<f8")
        return "f", x.tobytes()
    if a.dtype.kind in "iub":
        return "i", np.ascontiguousarray(a, dtype="<i8").tobytes()
    if a.dtype.kind == "M":
        return "M", np.ascontiguousarray(a.astype("datetime64[ns]").astype("<i8")).tobytes()
    out = []
    for x in a.ravel().tolist():
        if x is None or (isinstance(x, float) and x != x):
            out.append(NA)
        else:
            out.append(str(x))
    return "s", "\x00".join(out).encode("utf-8")


def hash_arrays(named: dict, tag: str = "dp/slice/v1") -> str:
    """One SHA-256 over named arrays, in the dict's order."""
    h = hashlib.sha256(tag.encode())
    for name, v in named.items():
        kind, data = _canon(v)
        a = np.asarray(v)
        h.update(f"|{name}|{kind}|{a.shape}|{len(data)}|".encode())
        h.update(data)
    return h.hexdigest()


def hash_value(value, tag: str = "dp/value/v1") -> str:
    """A JSON-able value (constants), canonically."""
    import json
    return hashlib.sha256((tag + json.dumps(value, sort_keys=True, default=str)).encode()).hexdigest()
