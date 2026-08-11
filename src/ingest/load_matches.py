"""Load downloaded Sackmann match CSVs into one chronologically ordered DataFrame.

Chronology in Sackmann files: ``tourney_date`` is the tournament START date for
every match in that event, so within a tournament the round sequence carries the
time order. This loader builds an explicit sort key
(tourney_date, tourney_id, round_rank, match_num) — that is its documented job,
not a defensive fallback. Downstream consumers (e.g. ratings) still verify
non-decreasing dates and raise if violated.

Round codes seen in the data, earliest to latest:
    ER (early round), BR (bronze/3rd-place), RR (round robin),
    R128, R64, R32, R16, QF, SF, F
BR is placed after SF since 3rd-place matches happen at the end of an event.
Unknown round codes raise — no silent ordering guesses.

Score-code taxonomy (verified against all 59 ATP files, 2026-06-10 — see
docs/02_data_and_tools.md): normalize score.strip() before matching. Walkovers are
'W/O' (plus 10 legacy rows with a leading space) and 6 Davis Cup rows spell out
'Walkover'; retirements are '... RET' (the score prefix tells whether a set was
completed); defaults appear as 'DEF', 'Def.', or 'Default'; also 'ABD', 'UNK',
'Played and unfinished/abandoned', and a few NaN. NOTE: minutes is 0.0 (not blank)
on most W/O rows — minutes-notnull is NOT a valid played-match filter. Label-policy
filtering belongs in the feature/training layer (Phase 2), not here: this loader
returns everything.
"""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ROUND_RANK = {
    "ER": 0, "RR": 1,
    "R128": 2, "R64": 3, "R32": 4, "R16": 5,
    "QF": 6, "SF": 7, "BR": 8, "F": 9,
}


def load_sackmann_matches(tour: str, start: int, end: int,
                          raw_root: Path | None = None) -> pd.DataFrame:
    """Concatenate {tour}_matches_{start..end}.csv in chronological order.

    Raises FileNotFoundError listing every missing year file (download first via
    download_sackmann.py) and ValueError on unknown round codes.
    """
    root = (raw_root or PROJECT_ROOT / "data" / "raw" / "sackmann") / tour
    paths = [root / f"{tour}_matches_{year}.csv" for year in range(start, end + 1)]
    missing = [p for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing Sackmann files (run download_sackmann.py first):\n  "
            + "\n  ".join(str(p) for p in missing))

    frames = [pd.read_csv(p) for p in paths]
    df = pd.concat(frames, ignore_index=True)

    unknown_rounds = set(df["round"].dropna().unique()) - set(ROUND_RANK)
    if unknown_rounds:
        raise ValueError(f"Unknown round codes {unknown_rounds} — extend ROUND_RANK "
                         "deliberately rather than letting ordering silently degrade.")

    df["round_rank"] = df["round"].map(ROUND_RANK)
    df = df.sort_values(
        ["tourney_date", "tourney_id", "round_rank", "match_num"],
        kind="mergesort",  # stable: preserves file order for ties
    ).reset_index(drop=True)
    return df
