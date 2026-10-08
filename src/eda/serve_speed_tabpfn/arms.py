"""The arms (input sets) of this study's TabPFN fits, the frame they read and how a match is flipped (audit C5).

Every arm starts from the model's 58 inputs (surface_rating_race/model/model_frame.parquet, columns in_<name>, in the
order of model_inputs.json) and appends speed inputs registered in data/studies/serve_speed_tabpfn/features/
registry.json (REGISTRY_SPEC, written by `write_registry`), with values in features/<family>.parquet:

    spd_f       A1   clip((f_A - f_B) / s_f, -4, 4): the posterior fast speed state, men; 0 for women; never NaN
    spd_raw     A2   the registered x_raw on the new panel / 5.998, clipped; NaN unless both men timed in 14 days
    spd_f_all   A3   spd_f with women's Slam values (women's constants); never NaN

Kinds, as the model frame's: diff (A - B, negated when A and B swap), pair (exchanged), context (unchanged).

ARMS maps an arm to its extra inputs; "<arm>_noodds" drops odds_logit. "model" is the 58 inputs alone.

The frame is read with an explicit column list. `a_won` is selected only when labels=True, which only the fit runner
(training labels) and the fingerprint check ask for; the scorer's --check and --synthetic modes never do.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from src.eda.serve_speed_tabpfn import common as C

REGISTRY_SPEC = {
    "spd_f": {"family": "speed", "kind": "diff", "arm": "spd (A1)",
              "desc": "clip((f_A - f_B) / s_f, -4, 4): posterior fast first-serve-speed state (audit C3), men; "
                      "women 0; never NaN"},
    "spd_raw": {"family": "speed", "kind": "diff", "arm": "spd_raw (A2)",
                "desc": "clip(x_raw / 5.998, -4, 4): the registered 14-day minus 364-day statistic on the new panel, "
                        "men with both sides timed in 14 days; NaN otherwise"},
    "spd_f_all": {"family": "speed", "kind": "diff", "arm": "spd_all (A3)",
                  "desc": "spd_f with women's Slam values from the women's constants and the men's s_f; never NaN"},
}
NEVER_NAN = ("spd_f", "spd_f_all")

ARMS: dict[str, list[str]] = {"model": [], "spd": ["spd_f"], "spd_raw": ["spd_raw"], "spd_all": ["spd_f_all"]}

# speed_meta.json must carry two passing probe records (audit C7): Probe A (own history, order cuts) and Probe B
# (clock, day cuts). Accepted spellings of each record's key; a record is True or a dict with passed/pass/ok True.
PROBE_KEYS = {"A": ("probe_a", "probe_a_own_history", "own_history", "a", "T-F2", "t_f2"),
              "B": ("probe_b", "probe_b_clock", "clock", "b", "T-F3", "t_f3")}


def write_registry(P: C.Paths = C.DEFAULT) -> dict:
    P.features.mkdir(parents=True, exist_ok=True)
    C.write_json(P.registry, REGISTRY_SPEC)
    return REGISTRY_SPEC


def registry(P: C.Paths = C.DEFAULT) -> dict:
    return json.loads(P.registry.read_text(encoding="utf-8")) if P.registry.exists() else {}


def base_inputs(P: C.Paths = C.DEFAULT) -> tuple[list[str], dict[str, str], dict[str, str]]:
    """(the 58 input names in order, kind per input, pair partner per pair input)."""
    meta = json.loads(P.model_inputs.read_text(encoding="utf-8"))
    names = [d["name"] for d in meta["inputs"]]
    kinds = {d["name"]: d["kind"] for d in meta["inputs"]}
    partners = {}
    for n, k in kinds.items():
        if k == "pair":
            stem, side = n.rsplit("_", 1)
            partners[n] = f"{stem}_{'b' if side == 'a' else 'a'}"
    return names, kinds, partners


def stem(arm: str) -> str:
    return arm[:-len("_noodds")] if arm.endswith("_noodds") else arm


def arm_inputs(arm: str, P: C.Paths = C.DEFAULT) -> list[str]:
    names, _, _ = base_inputs(P)
    cols = names + [c for c in ARMS[stem(arm)] if c not in names]
    return [c for c in cols if c != "odds_logit"] if arm.endswith("_noodds") else cols


def has_odds(arm: str) -> bool:
    return not arm.endswith("_noodds")


def kinds_and_partners(cols: list[str], P: C.Paths = C.DEFAULT) -> tuple[dict[str, str], dict[str, str]]:
    _, kinds, partners = base_inputs(P)
    reg = registry(P)
    for c in cols:
        if c in kinds:
            continue
        if c not in reg:
            raise KeyError(f"input {c} is neither a model input nor registered in {P.registry}")
        kinds[c] = reg[c]["kind"]
        if reg[c]["kind"] == "pair":
            partners[c] = reg[c]["partner"]
    return kinds, partners


def _probe_passed(rec) -> bool:
    if isinstance(rec, bool):
        return rec
    if isinstance(rec, dict):
        return any(rec.get(k) is True for k in ("passed", "pass", "ok"))
    return False


def feature_status(P: C.Paths = C.DEFAULT) -> dict:
    """The feature file's SHA-256 and its probe records (speed_meta.json). ok = both probes passed; the meta records the
    file's own hash and it equals the file's; the recorded panel_sha256 and features_py_sha256 equal the current
    speed_panel.parquet and features.py (red team F1); not a stand-in panel; no result read."""
    out = {"file": str(P.feature_file), "exists": P.feature_file.exists(), "ok": False, "problems": []}
    if not P.feature_file.exists():
        out["problems"].append("feature file missing")
        return out
    out["sha256"] = C.sha256_file(P.feature_file)
    if not P.feature_meta.exists():
        out["problems"].append("speed_meta.json missing")
        return out
    meta = C.read_json(P.feature_meta)
    probes = meta.get("probes", {})
    if not isinstance(probes, dict):
        probes = {}
    lower = {str(k).lower(): v for k, v in probes.items()}
    found = {}
    for label, keys in PROBE_KEYS.items():
        hit = [lower[k.lower()] for k in keys if k.lower() in lower]
        found[label] = bool(hit) and all(_probe_passed(h) for h in hit)
        if not hit:
            out["problems"].append(f"no probe record for probe {label} (keys {keys})")
        elif not found[label]:
            out["problems"].append(f"probe {label} did not pass")
    recorded = meta.get("features_parquet_sha256") or meta.get("sha256") or meta.get("feature_sha256")
    if not recorded:
        out["problems"].append("speed_meta.json records no feature file hash: its probe records could be another file's")
    elif recorded != out["sha256"]:
        out["problems"].append("speed_meta.json records another feature file hash")
    for key, path in (("panel_sha256", P.panel), ("features_py_sha256", P.features_py)):   # red team F1
        if not meta.get(key):
            out["problems"].append(f"speed_meta.json records no {key}")
        elif not path.exists():
            out["problems"].append(f"{key}: {path} is missing")
        elif meta[key] != C.sha256_file(path):
            out["problems"].append(f"{key} differs from the current {path.name}")
    if meta.get("probes_pass") is False:
        out["problems"].append("speed_meta.json: probes_pass is false")
    if meta.get("standin_panel") is True:
        out["problems"].append("built on a stand-in panel (standin_panel true): not the R3 panel")
    if meta.get("reads_results") is True:
        out["problems"].append("speed_meta.json: the build read results")
    out["probes"] = found
    out["standin_panel"] = meta.get("standin_panel")
    out["ok"] = not out["problems"]
    return out


def require_features(P: C.Paths = C.DEFAULT) -> dict:
    st = feature_status(P)
    if not st["ok"]:
        raise RuntimeError(f"feature file refused: {st['problems']}")
    return st


def frame_columns(P: C.Paths = C.DEFAULT, labels: bool = False) -> list[str]:
    names, _, _ = base_inputs(P)
    cols = ["match_id", "tour", "season", "tournament_date", "debut_season"] + [f"in_{n}" for n in names]
    return cols + (["a_won"] if labels else [])


def load_frame(extra: list[str], P: C.Paths = C.DEFAULT, labels: bool = False) -> pd.DataFrame:
    """The model frame (every season, its stored order) with the requested registered inputs joined one-to-one by match
    id (in_<name>). Every frame match must have a feature row; the never-NaN columns must be finite everywhere."""
    f = pd.read_parquet(P.model_frame, columns=frame_columns(P, labels))
    f["match_id"] = f["match_id"].astype(str)
    if f["match_id"].duplicated().any():
        raise RuntimeError("model frame match ids are not unique")
    reg = registry(P)
    fams = sorted({reg[c]["family"] for c in extra}) if extra else []
    for fam in fams:
        cols = [c for c in extra if reg[c]["family"] == fam]
        t = pd.read_parquet(P.features / f"{fam}.parquet", columns=["match_id"] + cols)
        t["match_id"] = t["match_id"].astype(str)
        if t["match_id"].duplicated().any():
            raise RuntimeError(f"{fam}.parquet: duplicate match ids")
        j = f[["match_id"]].merge(t, on="match_id", how="left", validate="one_to_one", indicator=True)
        missing = int((j["_merge"] != "both").sum())
        if missing:
            raise RuntimeError(f"{fam}.parquet: {missing} frame matches have no feature row")
        for c in cols:
            v = j[c].to_numpy(dtype="float64")
            if c in NEVER_NAN and not np.isfinite(v).all():
                raise RuntimeError(f"{c}: {int((~np.isfinite(v)).sum())} values are not finite (must never be NaN)")
            f[f"in_{c}"] = v
    return f


def matrix(frame: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    return pd.DataFrame({c: frame[f"in_{c}"].to_numpy(dtype="float64") for c in cols})


def flip(X: pd.DataFrame, P: C.Paths = C.DEFAULT) -> pd.DataFrame:
    """The same matches with A and B swapped: diffs negated (NaN stays NaN), pairs exchanged, context unchanged."""
    kinds, partners = kinds_and_partners(list(X.columns), P)
    out = X.copy()
    anti = [c for c in X.columns if kinds[c] == "diff"]
    out[anti] = -X[anti]
    for c in X.columns:
        if kinds[c] == "pair":
            out[c] = X[partners[c]].to_numpy()
    return out


def check_flip(frame: pd.DataFrame, cols: list[str], P: C.Paths = C.DEFAULT) -> bool:
    X = matrix(frame, cols)
    return bool(np.allclose(flip(flip(X, P), P).to_numpy(), X.to_numpy(), equal_nan=True))


def job_data(frame: pd.DataFrame, cols: list[str], season: int):
    """(X_train, y_train, X_test, test match ids): training 2013 .. season - 1 (expanding window), test = the season."""
    if "a_won" not in frame.columns:
        raise RuntimeError("job_data needs the training labels: load_frame(..., labels=True)")
    tr = frame["season"].between(C.TRAIN_FROM, season - 1).to_numpy()
    te = (frame["season"] == season).to_numpy()
    X = matrix(frame, cols)
    return (X[tr].reset_index(drop=True), frame.loc[tr, "a_won"].astype("int64").to_numpy(),
            X[te].reset_index(drop=True), frame.loc[te, "match_id"].to_numpy())


def columns_hash(frame: pd.DataFrame, cols: list[str]) -> str:
    """SHA-256 of the given in_<name> columns as little-endian float64 (one NaN pattern), in order."""
    h = hashlib.sha256(b"serve_speed_tabpfn/columns/v1")
    for c in cols:
        v = np.ascontiguousarray(frame[f"in_{c}"].to_numpy(dtype="float64"))
        v = np.where(np.isnan(v), np.nan, v).astype("<f8")
        h.update(c.encode())
        h.update(v.tobytes())
    return h.hexdigest()


def base_columns_unchanged(frame: pd.DataFrame, P: C.Paths = C.DEFAULT) -> bool:
    """T-H1: the 58 base columns of a joined frame hash-equal the model frame's own columns."""
    names, _, _ = base_inputs(P)
    raw = pd.read_parquet(P.model_frame, columns=[f"in_{n}" for n in names])
    return columns_hash(frame, names) == columns_hash(raw, names)
