"""Final-test verifier: result-free frames and synthetic outcomes for final_test.py.

No real 2025-2026 result is ever loaded here: `frame_free` is tabpfn_tests.frame without the a_won column (a_won is NaN
until a synthetic draw fills it), and it replaces tabpfn_tests.frame, so final_test.population() and history_frame() are
result-free. The walk-forward fits on 2014-2025 also see synthetic outcomes only. Forecasts (eta) and the B-INJ column x
are real: they are forecasts and features, not results.

DGP: y ~ Bernoulli(expit(a_tour * eta_B + beta * x_scaled)), a = 0.89 (men) / 0.91 (women), every season 2014-2026,
eta_B the seed mean of every seed held for the season (final_test.eta with seeds 0-15), x_scaled = final_test.x_scaled.
"""
from __future__ import annotations

import functools
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions import screen as S  # noqa: E402
from src.eda.feature_interactions import tabpfn_tests as TT  # noqa: E402
from src.eda.feature_interactions import final_test as FT  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

OUT = C.OUT / "verify_final"
A_TRUE = {"atp": 0.89, "wta": 0.91}
ORIG_FRAME, ORIG_ETA, ORIG_HISTORY = TT.frame, FT.eta, FT.history_frame
CURRENT_Y: pd.Series | None = None          # the current synthetic draw by match id (set by Synth.draw)


def frame_free(seasons, with_players: bool = True) -> pd.DataFrame:
    """tabpfn_tests.frame with a_won never read: NaN, or the current synthetic draw once one exists."""
    f = pd.read_parquet(C.MODEL_FRAME, columns=["match_id", "tour", "season", "tournament_date", "debut_season",
                                                "in_odds_logit"])
    f = f[f["season"].isin(list(seasons)) & ~f["debut_season"].astype(bool)].reset_index(drop=True)
    f["match_id"] = f["match_id"].astype(str)
    f.insert(4, "a_won", np.nan if CURRENT_Y is None else f["match_id"].map(CURRENT_Y).to_numpy(float))
    if with_players:
        s0 = pd.read_parquet(S.PRE_REBUILD_STAGE0, columns=["match_id", "player_a_id", "player_b_id"])
        s0["match_id"] = s0["match_id"].astype(str)
        f = f.merge(s0, on="match_id", how="left", validate="one_to_one")
    f["block"] = T.blocks(f["tournament_date"].to_numpy(), 28)
    return f


@functools.lru_cache(maxsize=None)
def _eta(seeds: tuple, seasons: tuple, block: str) -> pd.Series:
    return ORIG_ETA(seeds, seasons, block)


def eta_cached(seeds, seasons, block: str = "td") -> pd.Series:
    return _eta(tuple(seeds), tuple(seasons), block).copy()


class Synth:
    """The population, the 2014-2025 history and the DGP; draw(beta, rng) fills a_won everywhere consistently."""

    def __init__(self):
        TT.frame = frame_free                       # every final_test frame is now result-free
        FT.eta = eta_cached
        self.f = FT.population()                    # 2025-2026, a_won NaN
        assert self.f["a_won"].isna().all()
        self.H = ORIG_HISTORY(range(FT.NUDGE_FROM, 2026))   # 2014-2025 with eta (seed means), a_won NaN
        assert self.H["a_won"].isna().all()
        FT.history_frame = self.history
        self.x = pd.read_parquet(FT.X_FILE).set_index("match_id")["x"]
        self.xs = FT.x_scaled(self.x)
        e_all = eta_cached(FT.SEEDS_ALL, range(FT.NUDGE_FROM, 2027))
        ids = pd.Index(sorted(set(self.H["match_id"]) | set(self.f["match_id"])))
        self.ids = ids
        self.eta_true = e_all.reindex(ids).to_numpy(float)
        tour = pd.concat([self.H[["match_id", "tour"]], self.f[["match_id", "tour"]]]).drop_duplicates("match_id")
        self.a_vec = tour.set_index("match_id")["tour"].reindex(ids).map(A_TRUE).to_numpy(float)
        self.x_vec = self.xs.reindex(ids).to_numpy(float)
        self.iH = ids.get_indexer(self.H["match_id"])
        self.iF = ids.get_indexer(self.f["match_id"])
        for name, v in (("eta", self.eta_true), ("a", self.a_vec), ("x", self.x_vec)):
            if not np.isfinite(v).all():
                raise RuntimeError(f"{int((~np.isfinite(v)).sum())} rows without {name}")
        assert (self.iH >= 0).all() and (self.iF >= 0).all()
        self.z0 = self.f["match_id"].map(eta_cached(FT.OFFSET, FT.TEST)).to_numpy(float)
        self.z8 = self.f["match_id"].map(eta_cached(FT.DEVIATION, FT.TEST)).to_numpy(float)
        self.z16 = self.f["match_id"].map(eta_cached(FT.SEEDS_ALL, FT.TEST)).to_numpy(float)
        self.p = None

    def history(self, seasons) -> pd.DataFrame:
        h = self.H[self.H["season"].isin(list(seasons))].reset_index(drop=True)
        if not h["a_won"].isin([0.0, 1.0]).all():
            raise RuntimeError("history without synthetic outcomes")
        return h

    def p_true(self, beta: float) -> np.ndarray:
        return expit(self.a_vec * self.eta_true + beta * self.x_vec)

    def draw(self, beta: float, rng: np.random.Generator) -> None:
        global CURRENT_Y
        self.p = self.p_true(beta)
        y = (rng.random(len(self.p)) < self.p).astype(float)
        self.H["a_won"] = y[self.iH]
        self.f["a_won"] = y[self.iF]
        CURRENT_Y = pd.Series(y, index=self.ids)   # any later frame_free call (e.g. column_arm's) gets this draw


def ce(p_true: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Expected log loss of forecast q under the true probability p_true (T.ll's clipping)."""
    q = np.clip(np.asarray(q, float), T.EPS, 1 - T.EPS)
    return -(p_true * np.log(q) + (1 - p_true) * np.log(1 - q))
