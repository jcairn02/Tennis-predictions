"""The ATP Stats Centre's key statistics ("keystats", Infosys) mapped onto the box-score contract (atp_ readers).

The match is "set0". Values are counts ("5") or fractions with a share ("34/57 (60%)"). Mapping (as
prediction_run/fills.py KS_COUNTS and infosys_atp_backfill/checks.py read them):
    ace          Aces
    df           Double Faults
    svpt         1st Serve, denominator (first-serve attempts = every point served)
    first_in     1st Serve, numerator
    first_won    1st Serve Points Won, numerator
    second_won   2nd Serve Points Won, numerator
    sv_gms       Service Games Played
    bp_saved     Break Points Saved, numerator
    bp_faced     Break Points Saved, denominator
    sv_won       Service Points Won, numerator
Kept for the internal-consistency check: x_first_won_den (1st Serve Points Won's denominator, should equal first_in),
x_second_den (2nd Serve Points Won's, should equal svpt - first_in), x_sv_won_den (Service Points Won's, should equal
svpt), and x_spd1 (1st Serve Average Speed, where given).
"""
from __future__ import annotations

import math
import re

FRACTION = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")
NUMBER = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*$")
KS_MAP = {"ace": ("Aces", 0), "df": ("Double Faults", 0), "svpt": ("1st Serve", 1), "first_in": ("1st Serve", 0),
          "first_won": ("1st Serve Points Won", 0), "second_won": ("2nd Serve Points Won", 0),
          "sv_gms": ("Service Games Played", 0), "bp_saved": ("Break Points Saved", 0),
          "bp_faced": ("Break Points Saved", 1), "sv_won": ("Service Points Won", 0),
          "x_first_won_den": ("1st Serve Points Won", 1), "x_second_den": ("2nd Serve Points Won", 1),
          "x_sv_won_den": ("Service Points Won", 1), "x_spd1": ("1st Serve Average Speed", 0)}
KS_FIELDS = list(KS_MAP)


def value(text, part: int) -> float:
    """Part 0 (the count, or a fraction's numerator) or 1 (a fraction's denominator) of a key-statistic value."""
    if text is None or (isinstance(text, float) and math.isnan(text)):
        return float("nan")
    t = str(text)
    m = FRACTION.match(t)
    if m:
        return float(m.group(1 if part == 0 else 2))
    if part == 1:
        return float("nan")
    m = NUMBER.match(t)
    return float(m.group(1)) if m else float("nan")


def counts(stats: dict) -> dict:
    """stats: {name: (player1 value, player2 value)} of set0 -> {'<field>_1': .., '<field>_2': ..}."""
    out = {}
    for f, (name, part) in KS_MAP.items():
        v = stats.get(name)
        for no in (1, 2):
            out[f"{f}_{no}"] = value(v[no - 1], part) if v is not None else float("nan")
    return out


def consistency(row: dict, no: int) -> dict:
    """The key statistics' own fractions agree: 1st-serve points won over the first serves in, 2nd-serve points won
    over the rest of the serve points, serve points won over the serve points, and serve points won = first + second
    won."""
    g = lambda f: row.get(f"{f}_{no}", float("nan"))  # noqa: E731
    return {"first_won_den_eq_first_in": g("x_first_won_den") == g("first_in"),
            "second_den_eq_svpt_minus_first_in": g("x_second_den") == g("svpt") - g("first_in"),
            "sv_won_den_eq_svpt": g("x_sv_won_den") == g("svpt"),
            "sv_won_eq_first_plus_second": g("sv_won") == g("first_won") + g("second_won")}
