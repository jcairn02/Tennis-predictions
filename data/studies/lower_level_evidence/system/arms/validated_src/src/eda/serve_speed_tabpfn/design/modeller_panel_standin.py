"""R3 development stand-in (agent 2, modeller) for the engineer's `src/eda/serve_speed_tabpfn/panel.py`, with the same
FIXED API, built from the auditor's independent re-implementation (auditor_lib: ks-first panel from the R1 records,
as-of edition snapshots with the C2 constants). Used only to develop and unit-test features.py before the real panel
lands; the final build runs on the real panel. Reads no match result (Stage 0 with explicit column lists).

    load_panel(use_only=True)            match_id, side, player_id, tour, year, level, qualifying, tournament_id, tdate,
                                         round_order, es, lf, obs, y, n, basis ('pts'|'ks'), edition, family, source,
                                         use, drop_reason
    EditionOffsets(panel, tour).at(day)  pd.Series edition -> gamma
    EditionOffsets(panel, tour).gamma(editions, day) -> np.ndarray
    load_frame_keys()                    one row per frame match: match_id, rebuilt_id, tour, season, player_a_id,
                                         player_b_id (the frame's own ids), es, lf, obs, tdate, tournament_id,
                                         round_order, id_conflict, flipped
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.design import auditor_lib as AL  # noqa: E402
from src.eda.serve_speed_tabpfn.design import engineer_common as EC  # noqa: E402

TAU2, S_SERVE, K_PRIOR, WINDOW = AL.TAU2, AL.S_SERVE, AL.K_PRIOR, 364.0
PANEL_PATH = None          # the stand-in has no file of its own
_CACHE: dict = {}


def load_panel(use_only: bool = True) -> pd.DataFrame:
    if "panel" not in _CACHE:
        p = AL.panel("ks_first")
        p = p.rename(columns={"fam": "family"})
        p["use"] = True
        p["drop_reason"] = ""
        p["obs"] = p["obs"].astype("int64")
        p["n"] = p["n"].astype("int64")
        cols = ["match_id", "side", "player_id", "tour", "year", "level", "qualifying", "tournament_id", "tdate",
                "round_order", "es", "lf", "obs", "y", "n", "basis", "edition", "family", "source", "use",
                "drop_reason"]
        _CACHE["panel"] = p[cols].reset_index(drop=True)
    p = _CACHE["panel"]
    return p[p["use"]].reset_index(drop=True) if use_only else p.copy()


class EditionOffsets:
    """As-of edition offsets of one tour (auditor_lib.Snapshots on the given panel's rows of that tour)."""

    def __init__(self, panel: pd.DataFrame, tour: str):
        q = panel[(panel["tour"] == tour) & panel["use"].astype(bool)].reset_index(drop=True)
        self._s = AL.Snapshots(q.rename(columns={"family": "fam"}))
        self.editions = pd.Index(self._s.ed_u)

    def at(self, day: float) -> pd.Series:
        return pd.Series(self._s.at(float(day)), index=self.editions)

    def gamma(self, editions, day: float) -> np.ndarray:
        g = self._s.at(float(day))
        ix = self.editions.get_indexer(pd.Index(editions))
        return np.where(ix >= 0, g[np.maximum(ix, 0)], 0.0)


def load_frame_keys() -> pd.DataFrame:
    f = pd.read_parquet(EC.MODEL_FRAME, columns=["match_id", "tour", "season"])
    pre = pd.read_parquet(EC.S0_PRE, columns=["match_id", "player_a_id", "player_b_id"])
    f = f.merge(pre, on="match_id", how="left")
    idm = EC.id_map()
    f["rebuilt_id"] = f["match_id"].map(lambda m: idm.get(m, m))
    s0 = EC.stage0(cols=["match_id", "tournament_id", "tournament_date", "round_order", "player_a_id", "player_b_id"])
    s0 = s0.rename(columns={"match_id": "rebuilt_id", "player_a_id": "new_a", "player_b_id": "new_b"})
    f = f.merge(s0, on="rebuilt_id", how="left")
    tm = pd.read_parquet(EC.TIMING, columns=["match_id", "es", "lf", "obs"]).rename(columns={"match_id": "rebuilt_id"})
    f = f.merge(tm, on="rebuilt_id", how="left")
    f.loc[f["new_a"].isna(), "rebuilt_id"] = None
    f["tdate"] = f["tournament_date"].to_numpy().astype("datetime64[D]").astype("float")
    f["flipped"] = (f["new_a"] == f["player_b_id"]) & (f["new_b"] == f["player_a_id"])
    same = (f["new_a"] == f["player_a_id"]) & (f["new_b"] == f["player_b_id"])
    f["id_conflict"] = ~same
    return f[["match_id", "rebuilt_id", "tour", "season", "player_a_id", "player_b_id", "es", "lf", "obs", "tdate",
              "tournament_id", "round_order", "id_conflict", "flipped"]]
