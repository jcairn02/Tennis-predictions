"""Loading the saved TabPFN forecasts of an arm (audit C6, "Forecasts").

A fit file (arm, season, seed) holds P(A wins) for every season match as stored and flipped (`td`), and for arms with
the odds in 2025-2026 the same at Polymarket's 24-hour (`early`) and 30-minute (`late`) prices. A forecast is
symmetrised: the mean of P(A | x) and 1 - P(A | x swapped).

Where a fit is found:
    this study's arms             data/studies/serve_speed_tabpfn/local/ only
    the base arms "model",        this study's folder, then feature interactions' (seeds 3-15, fingerprinted), then the
    "model_noodds"                rating race's (seeds 0-2, no fingerprint)

Checks on every file: its stored column list equals the arm's inputs, its training shape equals the expanding window's
(the frame's matches of 2013 .. season - 1 by the arm's column count), and its `td` ids equal the season's frame ids in
order. A speed-arm fit (spd, spd_raw, spd_all, spd_noodds) must also store the SHA-256 of the CURRENT feature file
(meta feature_sha256): a fit made before a feature rebuild is never scored. The rating race's files are used only after the reproduction check and the fingerprint check have passed
(checks/repro_check.json, checks/fingerprint_check.json), unless require_checks=False (the synthetic mode, which reads no
result and is not a test of the fits).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.eda.serve_speed_tabpfn import arms as A
from src.eda.serve_speed_tabpfn import common as C

BASE_ARMS = ("model", "model_noodds")
_SHA_CACHE: dict = {}


def feature_sha(P: C.Paths = C.DEFAULT) -> str:
    """SHA-256 of the current feature file (cached by path, size and modification time)."""
    st = P.feature_file.stat()
    key = (str(P.feature_file), st.st_size, st.st_mtime_ns)
    if key not in _SHA_CACHE:
        _SHA_CACHE[key] = C.sha256_file(P.feature_file)
    return _SHA_CACHE[key]


def stale_speed_fits(P: C.Paths = C.DEFAULT, wanted: dict | None = None) -> dict:
    """Every existing speed-arm fit (not the base arms) whose stored feature_sha256 differs from the current feature
    file's: a fit made before a feature rebuild must never be scored. wanted: {arm: {(season, seed)}} to scan; default
    every speed-arm file in this study's folder."""
    current = feature_sha(P)
    paths = []
    if wanted is None:
        paths = sorted(p for p in P.local.glob("*.npz") if p.name.split("__")[0] not in BASE_ARMS)
    else:
        for arm, need in sorted(wanted.items()):
            if arm in BASE_ARMS:
                continue
            paths += [P.local / f"{arm}__{s}__seed{k}.npz" for s, k in sorted(need)
                      if (P.local / f"{arm}__{s}__seed{k}.npz").exists()]
    bad = []
    for path in paths:
        with np.load(path, allow_pickle=False) as z:
            stored = json.loads(str(z["meta"])).get("feature_sha256")
        if stored != current:
            bad.append({"file": path.name, "stored": stored})
    return {"feature_sha256": current, "speed_fits_checked": len(paths), "mismatches": bad}


def folders(arm: str, P: C.Paths = C.DEFAULT) -> list[tuple[str, Path]]:
    if arm in BASE_ARMS:
        return [("study", P.local), ("feature_interactions", P.fi_local), ("race", P.race_local)]
    return [("study", P.local)]


def find_fit(arm: str, season: int, seed: int, P: C.Paths = C.DEFAULT) -> tuple[str, Path]:
    for label, d in folders(arm, P):
        path = d / f"{arm}__{season}__seed{seed}.npz"
        if path.exists():
            return label, path
    raise FileNotFoundError(f"no fit for {arm} {season} seed {seed}")


def checks_passed(P: C.Paths = C.DEFAULT) -> dict:
    out = {}
    for name, key in (("repro_check.json", "passed"), ("fingerprint_check.json", "all_ok")):
        path = P.checks / name
        out[name] = bool(path.exists() and C.read_json(path).get(key) is True)
    return out


class FrameIndex:
    """What the checks compare a fit against: each season's frame ids in order and the training-window sizes."""

    def __init__(self, frame: pd.DataFrame):
        self.ids = {int(s): g["match_id"].astype(str).to_numpy() for s, g in frame.groupby("season", sort=True)}
        seasons = frame["season"].to_numpy()
        self.n_train = {int(s): int(((seasons >= C.TRAIN_FROM) & (seasons < s)).sum()) for s in self.ids}


def load_fit(arm: str, season: int, seed: int, fx: FrameIndex, P: C.Paths = C.DEFAULT,
             require_checks: bool = True) -> tuple[dict, dict]:
    """({block: pd.Series of symmetrised P(A wins) by match id}, provenance) for one fit, after the file checks."""
    label, path = find_fit(arm, season, seed, P)
    if label == "race" and require_checks:
        st = checks_passed(P)
        if not all(st.values()):
            raise RuntimeError(f"{path.name}: the rating race's fits are reused only after the reproduction and "
                               f"fingerprint checks pass ({st})")
    with np.load(path, allow_pickle=False) as z:
        meta = json.loads(str(z["meta"]))
        cols = A.arm_inputs(arm, P)
        stored = meta.get("columns") or []
        if (C.race_names(stored) if label == "race" else stored) != cols:
            raise RuntimeError(f"{path}: stored columns differ from the arm's inputs")
        if list(meta.get("train_shape", [])) != [fx.n_train[season], len(cols)]:
            raise RuntimeError(f"{path}: training shape {meta.get('train_shape')} is not the expanding window's "
                               f"{[fx.n_train[season], len(cols)]}")
        if not np.array_equal(z["ids_td"].astype(str), fx.ids[season]):
            raise RuntimeError(f"{path}: td ids are not the season's frame matches in order")
        if arm not in BASE_ARMS and meta.get("feature_sha256") != feature_sha(P):
            raise RuntimeError(f"{path}: fitted on another feature file (stored feature_sha256 "
                               f"{meta.get('feature_sha256')}); a stale fit is never scored")
        out = {}
        for b in ("td", "early", "late"):
            if f"p_{b}" not in z.files:
                continue
            p, ids = z[f"p_{b}"], z[f"ids_{b}"].astype(str)
            k = len(ids)
            if len(p) != 2 * k:
                raise RuntimeError(f"{path}: block {b} is not stored + flipped")
            out[b] = pd.Series(C.symmetrize(p[:k], p[k:]), index=ids)
    prov = {"arm": arm, "season": season, "seed": seed, "folder": label, "file": path.name,
            "fingerprint": meta.get("fingerprint"), "feature_sha256": meta.get("feature_sha256")}
    return out, prov


def seed_table(arm: str, seasons, seeds, fx: FrameIndex, P: C.Paths = C.DEFAULT, block: str = "td",
               require_checks: bool = True) -> tuple[pd.DataFrame, list[dict]]:
    """Rows: the seasons' matches (block's ids); columns: seed k -> symmetrised P(A wins). Every listed seed must exist
    in every season."""
    parts, provs = [], []
    for s in seasons:
        per = {}
        for k in seeds:
            blocks, prov = load_fit(arm, s, k, fx, P, require_checks)
            if block not in blocks:
                raise RuntimeError(f"{arm} {s} seed {k}: no block {block}")
            per[k] = blocks[block]
            provs.append(prov)
        parts.append(pd.DataFrame(per))
    return pd.concat(parts), provs


def available(arm: str, seasons, seeds, P: C.Paths = C.DEFAULT) -> dict:
    """Which (season, seed) fits exist, without loading them (for --check)."""
    have, missing = 0, []
    for s in seasons:
        for k in seeds:
            try:
                find_fit(arm, s, k, P)
                have += 1
            except FileNotFoundError:
                missing.append([s, k])
    return {"present": have, "missing": missing}
