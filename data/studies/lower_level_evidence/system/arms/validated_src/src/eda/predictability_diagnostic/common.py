"""Shared helpers for the predictability diagnostic study (every stage uses them).

What is here:
    * the study's fixed scope from the Brief (levels, evaluation window, eras);
    * loaders for the Stage 0 analysis tables;
    * the one chronological order of matches, and the as-of helper every pre-match feature goes
      through, with a black-box leakage probe that later stages can point at any feature.

The time rule, from the Brief: a feature for a match may use only earlier events and earlier rounds
of the same event. Dates are tournament Mondays, so matches of two events in the same week are
treated as simultaneous, and so are the matches of one round-robin stage.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DUMP = ROOT / "data" / "dump"
OUT = ROOT / "data" / "studies" / "predictability_diagnostic"
DOCS = ROOT / "docs" / "studies" / "predictability_diagnostic"
MATCHES = OUT / "stage0_matches.parquet"
MATCH_PLAYERS = OUT / "stage0_match_players.parquet"

# ------------------------------------------------------------------------------------------------
# Scope (the Brief)

TOURS = ("atp", "wta")
TOUR_NAMES = {"atp": "ATP (men)", "wta": "WTA (women)"}

# One level taxonomy across sources and years. Qualifying is a separate flag, not a level.
LEVELS = [
    ("GS", "Grand Slams", "The four majors: Australian Open, Roland Garros, Wimbledon, US Open."),
    ("FIN", "Tour Finals", "Season finales: ATP and WTA Finals, the Next Gen ATP Finals, the WTA Elite Trophy "
                           "and the WTA Tournament of Champions."),
    ("T1000", "1000s", "Masters 1000 and WTA 1000 (Premier Mandatory and Premier 5 before 2021)."),
    ("T500", "500s", "ATP 500 and WTA 500 (WTA Premier before 2021)."),
    ("T250", "250s", "ATP 250 and WTA 250 (WTA International before 2021)."),
    ("TEAM", "Team events", "Davis Cup, Fed Cup / Billie Jean King Cup, ATP Cup, United Cup, Laver Cup, "
                            "the World Team Championship and the Olympics."),
    ("CH", "Challenger / WTA 125", "The second tier, below the main tours."),
    ("ITF", "ITF", "The entry level: men's Futures (M15/M25) and women's W10-W100 events."),
]
LEVEL_CODES = [c for c, _, _ in LEVELS]
LEVEL_NAMES = {c: n for c, n, _ in LEVELS}
EVAL_LEVELS = ("GS", "FIN", "T1000", "T500", "T250", "CH")   # with their qualifying (the Finals have none)
EVAL_STATUSES = ("completed", "retired")

FIRST_YEAR = 2010                      # history (ratings and features) starts here
WARMUP_YEARS = range(2010, 2013)       # history only
EVAL_YEARS = range(2013, 2027)
HEADLINE_YEARS = range(2022, 2027)
ERAS = {"2013-16": range(2013, 2017), "2017-19": range(2017, 2020), "2020-21": range(2020, 2022),
        "2022-26": range(2022, 2027)}
WTA_BOX_FROM = 2019                    # WTA box-score features are evaluated from this season on
DIRECTIONAL_ONLY_BELOW = 300           # groups smaller than this are directional only

# The data map's level codes (data/studies/data_map/coverage_cells.csv): qualifying has its own code.
MAP_QUAL = {"GS": "GSQ", "T1000": "TQ", "T500": "TQ", "T250": "TQ", "FIN": "TQ", "CH": "CHQ", "ITF": "ITFQ"}
MAP_TOUR = {"atp": "M", "wta": "W"}

ROUND_ORDER = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4, "RR": 10, "R128": 11, "R64": 12, "R32": 13, "R16": 14,
               "QF": 15, "SF": 16, "BR": 17, "F": 17}   # the bronze-medal match and the final are simultaneous

# The nine box-score counts, per player (Sackmann's w_/l_ columns, renamed).
BOX = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"]
BOX_SOURCE_NAMES = {"ace": "ace", "df": "df", "svpt": "svpt", "first_in": "1stIn", "first_won": "1stWon",
                    "second_won": "2ndWon", "sv_gms": "SvGms", "bp_saved": "bpSaved", "bp_faced": "bpFaced"}

# Per-player rates, each stored as <name>_n / <name>_d in stage0_match_players.
RATES = {
    "spw": "serve points won, of points served",
    "rpw": "return points won, of the opponent's serve points",
    "tpw": "total points won, of all points played",
    "hold": "service games held, of service games played",
    "brk": "opponent service games broken, of the opponent's service games",
    "ace": "aces, per serve point",
    "df": "double faults, per serve point",
    "first_in": "first serves in, of serve points",
    "first_won": "points won on the first serve, of first serves in",
    "second_won": "points won on the second serve, of second-serve points",
    "bp_saved": "break points saved, of break points faced",
    "bp_conv": "break points converted, of break-point chances on the opponent's serve",
    "bp_faced_pg": "break points faced per service game (a rate per game, not a share)",
    "tb_won": "tiebreaks won, of tiebreaks played (from the score)",
    "sets_won": "sets won, of completed sets (from the score)",
    "games_won": "games won, of games played (from the score; a tiebreak counts as one game)",
}


def map_level(level: pd.Series, qualifying: pd.Series) -> pd.Series:
    """The data map's code for (level, qualifying): GS + qualifying -> GSQ, T250 + qualifying -> TQ ..."""
    q = level.map(MAP_QUAL)
    return level.where(~qualifying.astype(bool) | q.isna(), q)


def era_of(year: pd.Series) -> pd.Series:
    out = pd.Series(pd.NA, index=year.index, dtype="object")
    for name, years in ERAS.items():
        out[year.isin(list(years))] = name
    return out


def side_is_low(match_id: str) -> bool:
    """Whether the lower-sorted player id of a match is side A: one bit of a hash of match_id.

    Side depends on nothing but the match id, so it carries no information about the winner,
    rank or name.
    """
    return int(hashlib.sha256(match_id.encode("utf-8")).hexdigest()[:8], 16) % 2 == 0


# ------------------------------------------------------------------------------------------------
# Loaders

ORDER_COLS = ["order", "tournament_date", "tournament_id", "round_order"]


def load_matches(columns: list[str] | None = None) -> pd.DataFrame:
    """stage0_matches: one row per match, in chronological order."""
    cols = None if columns is None else list(dict.fromkeys(list(columns) + ["order"]))
    return pd.read_parquet(MATCHES, columns=cols).sort_values("order", kind="mergesort").reset_index(drop=True)


def load_match_players(columns: list[str] | None = None, with_order: bool = True,
                       match_columns: list[str] | None = None) -> pd.DataFrame:
    """stage0_match_players (two rows per match), with the order keys and any match columns joined."""
    mp = pd.read_parquet(MATCH_PLAYERS, columns=columns)
    extra = (ORDER_COLS if with_order else []) + [c for c in (match_columns or []) if c not in ORDER_COLS]
    if extra:
        m = pd.read_parquet(MATCHES, columns=["match_id"] + extra)
        mp = mp.merge(m, on="match_id", how="left", validate="many_to_one")
    if with_order:
        keys = ["order", "side"] if "side" in mp.columns else ["order"]
        mp = mp.sort_values(keys, kind="mergesort").reset_index(drop=True)
    return mp


def rate(frame: pd.DataFrame, name: str) -> pd.Series:
    """numerator / denominator of a stored rate; missing where the denominator is missing or zero."""
    n, d = frame[f"{name}_n"], frame[f"{name}_d"]
    return (n / d.where(d > 0)).astype("float64")


# ------------------------------------------------------------------------------------------------
# Chronological order and as-of features

def chrono_sort(matches: pd.DataFrame) -> pd.DataFrame:
    """The study's one chronological order: tournament date (the Monday), then round order
    (qualifying before the main draw), then match number; tournament and match id break ties so
    the order is deterministic."""
    key = matches.assign(_mn=pd.to_numeric(matches["match_num"], errors="coerce"))
    key = key.sort_values(["tournament_date", "round_order", "_mn", "tournament_id", "match_id"],
                          kind="mergesort", na_position="last")
    return key.drop(columns="_mn")


def asof_sums(rows: pd.DataFrame, values: list[str], player: str = "player_id", date: str = "tournament_date",
              event: str = "tournament_id", rnd: str = "round_order") -> pd.DataFrame:
    """For each player-match row, the sum of ``values`` over the same player's earlier matches.

    Earlier means what the Brief allows: matches of events with an earlier tournament date, plus
    earlier rounds of the same event (same tournament and date). Never included: the match itself,
    other matches of the same round (a round-robin stage), and other events of the same week.
    Missing values count as zero; pass an indicator column to count how many were present.

    One vectorised pass (group sums and exclusive cumulative sums), not a per-row look-back.
    """
    v = rows[[player, date, event, rnd]].copy()
    for c in values:
        v[c] = pd.to_numeric(rows[c], errors="coerce").fillna(0.0).astype("float64")
    by_day = v.groupby([player, date], sort=True)[values].sum()
    before_day = by_day.groupby(level=0, sort=False).cumsum() - by_day
    by_round = v.groupby([player, date, event, rnd], sort=True)[values].sum()
    before_round = by_round.groupby(level=[0, 1, 2], sort=False).cumsum() - by_round
    a = before_day.reindex(pd.MultiIndex.from_frame(v[[player, date]])).to_numpy()
    b = before_round.reindex(pd.MultiIndex.from_frame(v[[player, date, event, rnd]])).to_numpy()
    return pd.DataFrame(a + b, index=rows.index, columns=values)


def leak_probe(rows: pd.DataFrame, feature_fn, values: list[str], n_cuts: int = 25, seed: int = 0,
               order: str = "order") -> dict:
    """Black-box test that a feature uses neither the match itself nor anything after it.

    For each of ``n_cuts`` random cut points c in the chronological order, every value of the
    match at c and of all later matches is replaced with noise and the feature recomputed. A
    feature that respects time gives unchanged values for every match up to and including c.
    Returns the number of cut points and how many matches changed: before the cut (the feature
    looked ahead) and at the cut (it used the match itself or a simultaneous later one).
    """
    rng = np.random.default_rng(seed)
    base = feature_fn(rows).to_numpy(dtype="float64")
    orders = np.sort(rows[order].unique())
    cuts = rng.choice(orders[len(orders) // 10:], size=min(n_cuts, len(orders)), replace=False)
    ords = rows[order].to_numpy()
    changed_before = changed_at = 0
    for c in cuts:
        pert = rows.copy()
        late = ords >= c
        for col in values:
            pert.loc[late, col] = rng.integers(0, 1000, int(late.sum())).astype("float64")
        got = feature_fn(pert).to_numpy(dtype="float64")
        diff = ~np.all(np.isclose(got, base, equal_nan=True), axis=1)
        changed_before += int((diff & (ords < c)).sum())
        changed_at += int((diff & (ords == c)).sum())
    return {"cuts": int(len(cuts)), "changed_before_cut": changed_before, "changed_at_cut": changed_at}
