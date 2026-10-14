"""Surface-blended Elo ratings for tennis — the project's first baseline.

Design (FiveThirtyEight-style, the strongest simple pre-match model in
Kovalchik's model-comparison literature):

- Match-count-dependent K factor: ``K(n) = k0 / (n + offset) ** shape`` with
  defaults 250 / (n + 5) ** 0.4 — new players move fast, veterans stabilize.
- Two rating tables per player: overall and per-surface (Hard/Clay/Grass/Carpet).
  Every match updates overall AND that match's surface table, each with its own
  match count.
- Prediction blends the two on the rating scale:
      r_eff = (1 - surface_weight) * r_overall + surface_weight * r_surface
      P(A beats B) = 1 / (1 + 10 ** ((r_B_eff - r_A_eff) / 400))
  surface_weight is tunable (0 = ignore surface, 1 = surface-only).

Temporal validity: ``fit`` consumes matches in the order given and RAISES if the
date column ever decreases — chronological input is the caller's job (see
src/ingest/load_matches.py); there is deliberately no silent sort here. fit()
predicts BEFORE updating on each row, so its returned probabilities are
walk-forward and leak-free.
"""

import numpy as np
import pandas as pd

DEFAULT_RATING = 1500.0
SURFACES = ("Hard", "Clay", "Grass", "Carpet")


def k_factor(match_count: float, k0: float = 250.0, offset: float = 5.0,
             shape: float = 0.4) -> float:
    """FiveThirtyEight tennis K: large for new players, shrinking with history."""
    return k0 / (match_count + offset) ** shape


def expected_score(r_a: float, r_b: float) -> float:
    """Classic Elo expectation for A vs B."""
    return 1.0 / (1.0 + 10.0 ** ((r_b - r_a) / 400.0))


class SurfaceBlendElo:
    """Overall + per-surface Elo with blended prediction.

    missing_surface policy (applies when a row's surface is not one of
    Hard/Clay/Grass/Carpet, e.g. blank Davis Cup rows):
      - "raise" (default): ValueError — the caller must decide.
      - "overall": predict from overall ratings only and update overall only.
    """

    def __init__(self, k0: float = 250.0, offset: float = 5.0, shape: float = 0.4,
                 surface_weight: float = 0.5, default_rating: float = DEFAULT_RATING,
                 missing_surface: str = "raise"):
        if not 0.0 <= surface_weight <= 1.0:
            raise ValueError(f"surface_weight must be in [0, 1], got {surface_weight}")
        if missing_surface not in ("raise", "overall"):
            raise ValueError(f"missing_surface must be 'raise' or 'overall', got {missing_surface!r}")
        self.k0, self.offset, self.shape = k0, offset, shape
        self.surface_weight = surface_weight
        self.default_rating = default_rating
        self.missing_surface = missing_surface

        self.overall: dict = {}
        self.overall_counts: dict = {}
        self.by_surface: dict = {s: {} for s in SURFACES}
        self.surface_counts: dict = {s: {} for s in SURFACES}

    # ----- internals ---------------------------------------------------------

    def _normalize_surface(self, surface) -> str | None:
        if isinstance(surface, str):
            s = surface.strip().title()
            if s in SURFACES:
                return s
        if self.missing_surface == "raise":
            raise ValueError(
                f"Unknown surface {surface!r}. Pass one of {SURFACES}, or construct "
                "SurfaceBlendElo(missing_surface='overall') to deliberately use "
                "overall-only ratings for such rows.")
        return None  # 'overall' policy

    def _effective(self, player: str, surface: str | None) -> float:
        r_overall = self.overall.get(player, self.default_rating)
        if surface is None or self.surface_weight == 0.0:
            return r_overall
        r_surface = self.by_surface[surface].get(player, self.default_rating)
        return (1.0 - self.surface_weight) * r_overall + self.surface_weight * r_surface

    @staticmethod
    def _update_table(table: dict, counts: dict, winner: str, loser: str,
                      default_rating: float, k0: float, offset: float, shape: float,
                      k_scale: float) -> None:
        r_w = table.get(winner, default_rating)
        r_l = table.get(loser, default_rating)
        e_w = expected_score(r_w, r_l)
        k_w = k_scale * k_factor(counts.get(winner, 0), k0, offset, shape)
        k_l = k_scale * k_factor(counts.get(loser, 0), k0, offset, shape)
        table[winner] = r_w + k_w * (1.0 - e_w)
        table[loser] = r_l - k_l * (1.0 - e_w)
        counts[winner] = counts.get(winner, 0) + 1
        counts[loser] = counts.get(loser, 0) + 1

    # ----- public API --------------------------------------------------------

    def predict_proba(self, player_a: str, player_b: str, surface) -> float:
        """P(player_a beats player_b) BEFORE seeing the result."""
        s = self._normalize_surface(surface)
        return expected_score(self._effective(player_a, s), self._effective(player_b, s))

    def update(self, winner: str, loser: str, surface, k_scale: float = 1.0) -> None:
        """k_scale: per-match K multiplier — the verified FiveThirtyEight spec uses
        1.1 for Grand Slam matches (Kovalchik 2016, p.130). Caller's policy."""
        s = self._normalize_surface(surface)
        self._update_table(self.overall, self.overall_counts, winner, loser,
                           self.default_rating, self.k0, self.offset, self.shape, k_scale)
        if s is not None:
            self._update_table(self.by_surface[s], self.surface_counts[s], winner, loser,
                               self.default_rating, self.k0, self.offset, self.shape, k_scale)

    def fit(self, df: pd.DataFrame, date_col: str = "tourney_date",
            winner_col: str = "winner_name", loser_col: str = "loser_name",
            surface_col: str = "surface", k_scale_col: str | None = None) -> pd.DataFrame:
        """Walk forward through df (predict, then update). Returns predictions.

        Output columns: index-aligned ``p_winner`` = pre-match probability the
        model gave the actual winner. Log loss = -mean(log(p_winner)).
        Raises ValueError if date_col ever decreases (input must be chronological).
        """
        required = [date_col, winner_col, loser_col, surface_col]
        if k_scale_col is not None:
            required.append(k_scale_col)
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise KeyError(f"fit() missing required columns: {missing}")

        dates = df[date_col].to_numpy()
        if len(dates) > 1:
            decreases = np.where(dates[1:] < dates[:-1])[0]
            if len(decreases) > 0:
                i = int(decreases[0])
                raise ValueError(
                    f"{date_col} decreases at row {i + 1} "
                    f"({dates[i]} -> {dates[i + 1]}): input must be chronological. "
                    "Order it explicitly (see src/ingest/load_matches.py); "
                    "fit() will not sort for you.")

        p_winner = np.empty(len(df))
        winners = df[winner_col].to_numpy()
        losers = df[loser_col].to_numpy()
        surfaces = df[surface_col].to_numpy()
        k_scales = (df[k_scale_col].to_numpy() if k_scale_col is not None
                    else np.ones(len(df)))
        for i in range(len(df)):
            p_winner[i] = self.predict_proba(winners[i], losers[i], surfaces[i])
            self.update(winners[i], losers[i], surfaces[i], k_scale=float(k_scales[i]))
        return pd.DataFrame({"p_winner": p_winner}, index=df.index)
