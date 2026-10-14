"""The lean review's T2 (docs/studies/lean_review/README.md, "The test plan"): shared definitions.

T2 is a 2x2 of column drops on the Pinnacle-first instance of the current best model (decision of 9 Oct 2026,
docs/decisions/2026-10-09-pinnacle-first-odds-input.md):

    A0  the 58 inputs (the base, refitted only to add the opening-line queries; its close-fed predictions must equal the
        instance's stored fits)
    A1  without the 21-input long-memory IOS profile (iosO_*, iosD_*, prod_* on seven statistics)
    A2  without ios_points_short
    A3  without both

Two yardsticks, each with its own walk-forward calibration and stage-2 coefficients:
    (C) the Pinnacle-first close, as the model is trained (the frame's in_odds_logit)
    (O) Pinnacle's opening line, margin-free, fed in place of the close at query time (OddsTrader's timed recording,
        p_ot20o of data/studies/odds_sources/sources.parquet). Complete cases only: a coherent line stamped no later than
        the listed start; the 2021 US Open left out (OddsTrader's Pinnacle recording failed there, odds_sources § 2).
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

from src.eda.serve_speed_tabpfn import common as SC  # noqa: E402

OUT = ROOT / "data" / "studies" / "lean_review"
INSTANCE = ROOT / "data" / "studies" / "current_best_model" / "pinnacle_first_2026-10-09"
FRAME = INSTANCE / "model_frame.parquet"
INPUTS = INSTANCE / "model_inputs.json"
SOURCES = ROOT / "data" / "studies" / "odds_sources" / "sources.parquet"
NOWHERE = OUT / "no_fits_here"

SEASONS = tuple(range(2019, 2025))      # fitted: 2019 feeds only the walk-forward fits; scored 2020-2024
TEST = tuple(range(2020, 2025))
SEEDS = (0, 1, 2, 3)
STATS = ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved")
PROFILE = [f"{p}_{s}" for p in ("iosO", "iosD") for s in STATS] + [f"prod_{s}" for s in STATS]
SHORT = ["ios_points_short"]
ARMS = {"A0": [], "A1": PROFILE, "A2": SHORT, "A3": PROFILE + SHORT}
US_OPEN_2021_START = "2021-08-30"       # the frame's tournament_date of the 2021 US Open (a Slam, level code 0)


def arm_dir(arm: str) -> Path:
    return OUT / "arms" / arm


def inputs_path(arm: str) -> Path:
    """A0 reads the instance's own input list; the other arms a copy without their dropped inputs."""
    return INPUTS if arm == "A0" else arm_dir(arm) / "model_inputs.json"


def fits_dir(arm: str) -> Path:
    return arm_dir(arm) / "fits"


def paths(arm: str) -> SC.Paths:
    """The serve-speed harness's paths for one arm: the instance's frame, the arm's input list, the arm's fits."""
    return SC.DEFAULT.with_(model_frame=FRAME, model_inputs=inputs_path(arm), local=fits_dir(arm),
                            fi_local=NOWHERE, race_local=NOWHERE, checks=NOWHERE)


def write_inputs(arm: str) -> list[str]:
    """Write the arm's input list (the instance's, minus the dropped inputs, every other field unchanged)."""
    meta = json.loads(INPUTS.read_text(encoding="utf-8"))
    names = [d["name"] for d in meta["inputs"]]
    drop = ARMS[arm]
    missing = [d for d in drop if d not in names]
    if missing:
        raise RuntimeError(f"{arm}: not model inputs: {missing}")
    if arm == "A0":
        return names
    meta["inputs"] = [d for d in meta["inputs"] if d["name"] not in drop]
    meta["lean_review"] = {"arm": arm, "dropped": drop, "from": str(INPUTS.relative_to(ROOT))}
    path = inputs_path(arm)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return [d["name"] for d in meta["inputs"]]


def opening_prices(frame: pd.DataFrame) -> pd.DataFrame:
    """Per frame match: Pinnacle's margin-free opening P(A wins) and why a match is left out of (O).

    Kept: a coherent line (sources.parquet's p_ot20o is set only for both prices above 1 and an overround of 1.00-1.20)
    stamped no later than OddsTrader's listed start, outside the 2021 US Open. Oriented to the frame's side A by the
    odds-sources table. Reads no result."""
    s = pd.read_parquet(SOURCES, columns=["match_id", "p_ot20o", "after_ot20o_min"])
    s["match_id"] = s["match_id"].astype(str)
    if s["match_id"].duplicated().any():
        raise RuntimeError("sources.parquet: duplicate match ids")
    f = frame[["match_id", "season", "tournament_date", "in_level"]].merge(s, on="match_id", how="left",
                                                                            validate="one_to_one")
    p = f["p_ot20o"].to_numpy(float)
    why = reasons(p, f["after_ot20o_min"].to_numpy(float),
                  pd.to_datetime(f["tournament_date"]).dt.strftime("%Y-%m-%d").to_numpy(),
                  f["in_level"].to_numpy(float))
    return pd.DataFrame({"match_id": f["match_id"].to_numpy(), "season": f["season"].to_numpy(),
                         "p_open": np.where(why == "kept", p, np.nan), "why": why})


def reasons(p: np.ndarray, after_min: np.ndarray, tournament_date: np.ndarray, level: np.ndarray) -> np.ndarray:
    """'kept', or why a match is left out of (O): no coherent line, no stamp, stamped after the listed start, or the
    2021 US Open."""
    p, after = np.asarray(p, dtype=float), np.asarray(after_min, dtype=float)
    uso = (np.asarray(tournament_date).astype(str) == US_OPEN_2021_START) & (np.asarray(level, dtype=float) == 0.0)
    return np.where(~np.isfinite(p), "no coherent opening line",
                    np.where(~np.isfinite(after), "no stamp",
                             np.where(after > 0, "stamped after the listed start",
                                      np.where(uso, "2021 US Open (recording failed)", "kept"))))
