"""Register new inputs for the TabPFN arms: features/<family>.parquet (match_id + columns) and features/registry.json
(kind, partner, family, description per input). Reads no results."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.eda.feature_interactions import common as C


def register(family: str, frame: pd.DataFrame, specs: dict[str, dict]) -> None:
    """frame: match_id + one column per input; specs: {name: {"kind": ..., "desc": ..., "partner": ... (pairs)}}."""
    missing = [c for c in specs if c not in frame.columns]
    if missing:
        raise KeyError(missing)
    for name, s in specs.items():
        if s["kind"] not in ("diff", "context", "pair"):
            raise ValueError(f"{name}: kind {s['kind']}")
        if s["kind"] == "pair" and s.get("partner") not in specs:
            raise ValueError(f"{name}: pair without a registered partner")
    C.FEATURES.mkdir(parents=True, exist_ok=True)
    out = frame[["match_id"] + list(specs)].copy()
    out["match_id"] = out["match_id"].astype(str)
    if out["match_id"].duplicated().any():
        raise ValueError("duplicate match ids")
    out.to_parquet(C.FEATURES / f"{family}.parquet", index=False)
    path = C.FEATURES / "registry.json"
    reg = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for name, s in specs.items():
        reg[name] = {"family": family, **s,
                     "coverage": float(np.isfinite(out[name].to_numpy(dtype=float)).mean())}
    C.write_json(path, reg)
