"""Each player's own match history at every level, 2010-2026: one row per (match, player) from the PRE-REBUILD Stage 0
(consistent with the frozen model frame), in the player's own order, with what each past match was (level, surface,
indoor, format, sets, games, tiebreaks, minutes, retirement, walkover, box score) and the match clock's days.

Features that follow a player's own matches in order are safe by construction under the match clock (CLAUDE.md): a
player's earlier match has finished before the player's next one starts. A builder takes a value from STRICTLY EARLIER
rows of the same player (`prior(...)`, or a groupby on `player_id` with shift(1) along `k`), then reads it at the model
match's row for side A and side B (`at_model(...)`). Never use the current row's own match facts (score, minutes, box
score, won): they are the result.

    from src.eda.feature_interactions.history import long_table, at_model
    L = long_table()                                   # about 1.75 million rows
    L["sets_prev"] = L.groupby("player_id")["sets"].shift(1)      # the player's previous match's sets
    a, b = at_model(L, "sets_prev", match_ids)         # aligned to the given model-frame match ids

Days are the clock's floats (days since 1970-01-01). Order within a player: each event by its earliest best-estimate day
`obs` (the exact day, else the class's median offset inside the window), then the tournament date and id, and within an
event the round order and match number (so rounds never reverse). `rest_days` = the running maximum of obs at this
match minus that at the previous match (best estimate, days, never negative); `rest_min` = this es minus the previous lf
(a conservative lower bound; often negative where a day is unknown).
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from src.eda.feature_interactions.panel import SOURCES

MATCH_COLS = ["match_id", "tour", "level", "qualifying", "round", "round_order", "match_num", "surface", "indoor",
              "best_of", "tournament_id", "tournament_name", "tournament_date", "status", "status_detail", "score",
              "minutes"]
PLAYER_COLS = ["match_id", "player_id", "opponent_id", "side", "won", "rank", "rank_points", "entry", "age", "country",
               "ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced",
               "tpw_n", "tpw_d", "spw_n", "spw_d", "rpw_n", "rpw_d"]
SET_RE = re.compile(r"(\d+)-(\d+)(\(\d+\))?")


def parse_score(score: str) -> tuple[float, float, float, float]:
    """(sets, games, tiebreaks, sets won by the winner) from a winner-first score string; NaN when unparseable."""
    if not isinstance(score, str) or not score.strip():
        return (np.nan, np.nan, np.nan, np.nan)
    sets = games = tbs = won = 0
    for a, b, tb in SET_RE.findall(score):
        a, b = int(a), int(b)
        sets += 1
        games += a + b
        tbs += int(bool(tb) or {a, b} == {7, 6})
        won += int(a > b)
    if sets == 0:
        return (np.nan, np.nan, np.nan, np.nan)
    return (float(sets), float(games), float(tbs), float(won))


def long_table() -> pd.DataFrame:
    m = pd.read_parquet(SOURCES["stage0_matches"], columns=MATCH_COLS)
    t = pd.read_parquet(SOURCES["timing"], columns=["match_id", "es", "lf", "obs", "exact"])
    p = pd.read_parquet(SOURCES["stage0_players"], columns=PLAYER_COLS)
    for d in (m, t, p):
        d["match_id"] = d["match_id"].astype(str)
    parsed = np.array([parse_score(s) for s in m["score"].to_numpy()], dtype=float)
    m["sets"], m["games"], m["tiebreaks"], m["sets_won_by_winner"] = parsed.T
    m = m.merge(t, on="match_id", how="left", validate="one_to_one")
    L = p.merge(m, on="match_id", how="left", validate="many_to_one")
    L["won"] = L["won"].astype(bool)
    L["retired_self"] = (L["status"] == "retired") & ~L["won"]          # the loser retires
    L["walkover"] = L["status"] == "walkover"
    L["played"] = ~L["walkover"]
    L["tday"] = (pd.to_datetime(L["tournament_date"]) - pd.Timestamp("1970-01-01")).dt.days.astype(float)
    # an event is placed by its earliest best-estimate day; within an event, rounds keep their order (verifier B3:
    # sorting by each match's own estimated day reversed rounds of undated events in 3,476 places)
    L["ev_obs"] = L.groupby(["player_id", "tournament_id", "tday"])["obs"].transform("min")
    L = L.sort_values(["player_id", "ev_obs", "tday", "tournament_id", "round_order", "match_num"], kind="stable")
    L["k"] = L.groupby("player_id").cumcount()
    L["obs_mono"] = L.groupby("player_id")["obs"].cummax()
    g = L.groupby("player_id")
    L["rest_days"] = L["obs_mono"] - g["obs_mono"].shift(1)
    L["rest_min"] = L["es"] - g["lf"].shift(1)
    return L.reset_index(drop=True)


def prior(L: pd.DataFrame, col: str, n: int = 1) -> pd.Series:
    """The value of `col` in the player's n-th previous match (strictly earlier rows)."""
    return L.groupby("player_id")[col].shift(n)


def at_model(L: pd.DataFrame, col: str, match_ids, sides=("A", "B")) -> tuple[np.ndarray, np.ndarray]:
    """`col` at the given model matches for side A and side B (aligned to match_ids; NaN where absent)."""
    ids = pd.Index(pd.Series(match_ids).astype(str))
    out = []
    for side in sides:
        s = L.loc[L["side"] == side, ["match_id", col]].drop_duplicates("match_id").set_index("match_id")[col]
        out.append(s.reindex(ids).to_numpy())
    return out[0], out[1]
