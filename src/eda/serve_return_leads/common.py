"""Shared pieces of the serve/return-leads study (docs/studies/serve_return_leads/): the men's serve, return and
serve-speed leads of the edge-anatomy study, locked in, and their cleaner versions.

    SEALED_FROM   no result of a match with tournament date on or after 29 Jul 2026 is read by `seen()`; the unseen
                  matches are read only by `unseen()`, which needs the owner's words
    seen()        the 10 Oct instance's frame (the one edge anatomy and unpriced leads read), seasons 2013-2026, tournament
                  date before 29 Jul 2026, debut seasons out, with the result, L (the close's log-odds), four-week blocks,
                  the model's both-stages forecast (L_model, 2020 - 28 Jul 2026, from edge anatomy's analysis table) and
                  the stage-2 speed column (spd)
    LOCKED        the four traits as locked in (lock_in.md): columns, orientation (+ = expected to beat the close)
    scales()      the frozen RMS scales, from the men's matches of 1 Jan 2025 - 28 Jul 2026
    scores()      the trait scores T1-T4 and the combined serve/return score R0, from the frozen scales
    fit           unpriced leads' registered `look.fit`, unchanged: logistic, no intercept, per-tour slope and
                  curvature on the base's log-odds, beta per RMS of the score, cluster-robust over four-week blocks,
                  p from t on G - 1
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.unpriced_leads import look as LK  # noqa: E402
from src.eda.unpriced_leads import screen as H  # noqa: E402

INSTANCE = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-10"
ANALYSIS = ROOT / "data" / "studies" / "edge_anatomy" / "analysis.parquet"
OUT = ROOT / "data" / "studies" / "serve_return_leads"
DOCS = ROOT / "docs" / "studies" / "serve_return_leads"
SEALED_FROM = pd.Timestamp("2026-07-29")
SCALE_WINDOW = (pd.Timestamp("2025-01-01"), SEALED_FROM)       # the frozen scales: men, 1 Jan 2025 - 28 Jul 2026
ERAS = {"2013-16": (2013, 2016), "2017-19": (2017, 2019), "2020-22": (2020, 2022), "2023-24": (2023, 2024)}

# The four traits (the owner's wording of 16 Oct 2026), men only. Orientation: + means the player higher on the
# oriented value is expected to beat the close; the serving traits are expected to lose to it.
LOCKED = {
    "T1": {"name": "Serving strength (long memory: holds and break points saved)",
           "columns": {"iosO_hold": -1, "iosO_bp_saved": -1}},
    "T2": {"name": "Break points saved, recently (two-week form)",
           "columns": {"form_bp_saved": -1}},
    "T3": {"name": "Returning strength (long memory: holding the server's first-serve points and holds down)",
           "columns": {"iosD_first_won": +1, "iosD_hold": +1}},
    "T4": {"name": "Serve-speed change (the serve-speed stage's 28-day speed memory)",
           "columns": {"spd": +1}},
}
R0_TRAITS = ("T1", "T2", "T3")          # the combined serve/return score; speed (T4) is tested on its own


def seen(tour: str | None = "atp") -> pd.DataFrame:
    """Seasons 2013-2026 of the 10 Oct instance's frame, before 29 Jul 2026 (the registered loader, its guards on)."""
    paths = {"frame": INSTANCE / "model_frame.parquet", "model_inputs": INSTANCE / "model_inputs.json"}
    f = LK.load_window(paths, 2013, 2026, str(SEALED_FROM.date()), allow_post_2024=True)
    if len(f) and f["tournament_date"].max() >= SEALED_FROM:
        raise RuntimeError("a result from 29 Jul 2026 or later was read")
    a = pd.read_parquet(ANALYSIS, columns=["match_id", "q_full", "q_full_s1", "spd"]).astype({"match_id": str})
    a = a.drop_duplicates("match_id").set_index("match_id").reindex(f["match_id"])
    f["L_model"] = np.where(np.isfinite(a["q_full"].to_numpy(float)), H.lg(a["q_full"].to_numpy(float)), np.nan)
    f["L_model_s1"] = np.where(np.isfinite(a["q_full_s1"].to_numpy(float)), H.lg(a["q_full_s1"].to_numpy(float)),
                               np.nan)
    f["in_spd"] = a["spd"].to_numpy(float)
    if tour:
        f = f[f["tour"] == tour].reset_index(drop=True)
    return f


def _x(frame: pd.DataFrame, col: str) -> np.ndarray:
    x = frame[f"in_{col}"].to_numpy(float)
    return np.where(np.isfinite(x), x, 0.0)


def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x ** 2)))


def scales(frame: pd.DataFrame) -> dict:
    """Frozen RMS scales of every column, trait and R0, on the men's matches of the scale window (outcome-free)."""
    w = frame[(frame["tour"] == "atp") & (frame["tournament_date"] >= SCALE_WINDOW[0]) &
              (frame["tournament_date"] < SCALE_WINDOW[1])]
    sc = {"columns": {}, "traits": {}, "window": [str(SCALE_WINDOW[0].date()), "2026-07-28"], "matches": int(len(w))}
    for t in LOCKED.values():
        for c in t["columns"]:
            x = _x(w, c)
            sc["columns"][c] = _rms(x[x != 0]) if c == "spd" else _rms(x)
    raw = _trait_values(w, sc)
    for k, v in raw.items():
        sc["traits"][k] = _rms(v[v != 0]) if k == "T4" else _rms(v)
    r0 = np.mean([raw[k] / sc["traits"][k] for k in R0_TRAITS], axis=0)
    sc["R0"] = _rms(r0)
    return sc


def _trait_values(frame: pd.DataFrame, sc: dict) -> dict:
    out = {}
    for k, t in LOCKED.items():
        out[k] = np.mean([sign * _x(frame, c) / sc["columns"][c] for c, sign in t["columns"].items()], axis=0)
    return out


def scores(frame: pd.DataFrame, sc: dict) -> dict:
    """T1-T4 (each in units of its frozen RMS, oriented) and R0 (the mean of T1-T3, in units of its frozen RMS)."""
    raw = _trait_values(frame, sc)
    out = {k: v / sc["traits"][k] for k, v in raw.items()}
    out["R0"] = np.mean([out[k] for k in R0_TRAITS], axis=0) / sc["R0"]
    return out


def fit(frame: pd.DataFrame, s: np.ndarray, base: str = "L", curv: bool = True) -> dict:
    """The registered fit. Note: it reports beta per RMS of s *in the rows fitted*; `beta_per_unit` converts it to
    the frozen units (beta / RMS(s) in those rows)."""
    r = LK.fit(frame, s, base=base, curv=curv)
    ok = np.isfinite(frame[base].to_numpy(float))
    rms = _rms(np.asarray(s, float)[ok])
    r["rms_in_rows"] = rms
    r["beta_per_unit"] = r["beta"] / rms if rms > 0 else np.nan
    r["se_per_unit"] = r["se"] / rms if rms > 0 else np.nan
    return r


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, default=float), encoding="utf-8")
