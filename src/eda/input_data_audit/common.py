"""Shared paths, loaders and detectors for the input-data audit of the current best model (src/eda/input_data_audit/).

The question (owner, 8 Oct 2026): is there a bug like "one year of serve speeds reads about 4 km/h high on every serve"
anywhere in the data that feeds the current best model, column by column, including the box scores its averages are
built from?

Two Stage 0 snapshots are audited:
    "sep30"  the tables of 30 Sep 2026, which every input of the model frame was built on, kept by the 7 Oct rebuild
             (data/studies/data_continuity/rebuilds/2026-10-07T0005Z/replaced/)
    "oct07"  the live tables after the 7 Oct rebuild, which the next rebuild of the model's inputs will read

The detectors are pure functions of a frame, so the tests can feed them synthetic rows.
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "studies" / "input_data_audit"
SNAPSHOTS = {   # the 7 Oct tables were replaced by the corrections' rebuild of 8 Oct (decision 2026-10-08) and kept
    "sep30": ROOT / "data/studies/data_continuity/rebuilds/2026-10-07T0005Z/replaced/data/studies/predictability_diagnostic",
    "oct07": ROOT / "data/studies/data_continuity/rebuilds/2026-10-08T1853Z/replaced/data/studies/predictability_diagnostic",
    "oct08": ROOT / "data/studies/predictability_diagnostic",
}
MODEL_FRAME = ROOT / "data/studies/surface_rating_race/model/model_frame.parquet"
SACKMANN = ROOT / "data/dump/matches/sackmann_archive"
MCP = ROOT / "data/raw/public_dump/match_charting_project"
INFOSYS = ROOT / "data/dump/points/infosys_slams"

BOX = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"]
SLAMS = ("Australian Open", "Roland Garros", "Wimbledon", "US Open")

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, default=_default), encoding="utf-8")


def _default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, (pd.Timestamp, np.datetime64)):
        return str(o)
    raise TypeError(type(o))


def name_key(name) -> str:
    """Accents dropped, lower case, words sorted: 'Sorribes Tormo, Sara' and 'Sara Sorribes Tormo' agree."""
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    return " ".join(sorted(re.findall(r"[a-z]+", s)))


def event_key(name) -> str:
    """A tournament name without its year, for following one event across seasons."""
    s = re.sub(r"\b(19|20)\d\d\b", "", str(name).lower())
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


# ------------------------------------------------------------------------------------------------
# Loaders

MATCH_COLS = ["match_id", "tour", "year", "level", "qualifying", "round", "surface", "tournament_id", "tournament_name",
              "tournament_date", "status", "score", "source"]
PLAYER_COLS = ["match_id", "player_id", "opponent_id", "side", "won", "player_name", "age", "has_box",
               "games_won_n", "tb_won_d"] + BOX


def load_player_rows(snapshot: str) -> pd.DataFrame:
    """Two rows per match from one Stage 0 snapshot: the player's box score, the opponent's (o_<count>) and the match."""
    folder = SNAPSHOTS[snapshot]
    p = pd.read_parquet(folder / "stage0_match_players.parquet", columns=PLAYER_COLS)
    m = pd.read_parquet(folder / "stage0_matches.parquet", columns=MATCH_COLS)
    d = p.merge(m, on="match_id", how="left", validate="many_to_one")
    opp = d[["match_id", "side", "player_name"] + BOX].copy()
    opp["side"] = opp["side"].map({"A": "B", "B": "A"})
    opp = opp.rename(columns={c: f"o_{c}" for c in BOX + ["player_name"]})
    return d.merge(opp, on=["match_id", "side"], how="left", validate="one_to_one")


def load_model_frame(columns: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(MODEL_FRAME, columns=columns)


# ------------------------------------------------------------------------------------------------
# Detectors on one row per match (side A, with the opponent's counts as o_<count>)

def identity_flags(b: pd.DataFrame) -> pd.DataFrame:
    """Accounting identities that Stage 0's row checks (B0-B9) do not test.

    svg_not_alternating   completed match whose two service-game counts differ by more than one
    games_identity_fails  completed match without a tiebreak where A's games won (from the score) differ from
                          A's holds plus B's breaks conceded, using the box score
    swapped_box_fits      the identity fails as recorded but holds exactly with the two box scores exchanged
    winner_fewer_points   the recorded winner won fewer points than the loser (about 4% of real matches)
    """
    comp = b["status"].eq("completed")
    svg = b["sv_gms"].notna() & b["o_sv_gms"].notna()
    brk_a, brk_b = b["bp_faced"] - b["bp_saved"], b["o_bp_faced"] - b["o_bp_saved"]
    no_tb = b["tb_won_d"].fillna(-1).eq(0) & b["games_won_n"].notna()
    testable = comp & svg & no_tb
    as_recorded = b["sv_gms"] - brk_a + brk_b
    exchanged = b["o_sv_gms"] - brk_b + brk_a
    pts_a = b["first_won"] + b["second_won"] + (b["o_svpt"] - b["o_first_won"] - b["o_second_won"])
    pts_b = b["o_first_won"] + b["o_second_won"] + (b["svpt"] - b["first_won"] - b["second_won"])
    won = b["won"].astype(bool)
    winner_pts, loser_pts = pts_a.where(won, pts_b), pts_b.where(won, pts_a)
    out = pd.DataFrame(index=b.index)
    out["identity_testable"] = testable
    out["svg_not_alternating"] = comp & svg & ((b["sv_gms"] - b["o_sv_gms"]).abs() > 1)
    out["games_identity_fails"] = testable & (as_recorded != b["games_won_n"])
    out["swapped_box_fits"] = out["games_identity_fails"] & (exchanged == b["games_won_n"])
    out["winner_fewer_points"] = comp & (winner_pts < loser_pts)
    return out


def serve_points_exclude_dfs(rows: pd.DataFrame) -> pd.Series:
    """A row that is impossible when serve points include double faults: points won behind the second serve plus
    double faults exceed the second-serve points (svpt - first_in). Each double fault is a second-serve point lost."""
    return (rows["second_won"] + rows["df"]) > (rows["svpt"] - rows["first_in"])


def pooled_rates(rows: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Pooled serve rates (sums over rows, then ratios), in percent."""
    g = rows.groupby(keys).agg(rows=("svpt", "size"), svpt=("svpt", "sum"), fi=("first_in", "sum"),
                               fw=("first_won", "sum"), sw=("second_won", "sum"), ace=("ace", "sum"),
                               df=("df", "sum"), bps=("bp_saved", "sum"), bpf=("bp_faced", "sum"))
    out = pd.DataFrame({"rows": g["rows"]})
    out["first_in_pct"] = 100 * g["fi"] / g["svpt"]
    out["first_won_pct"] = 100 * g["fw"] / g["fi"]
    out["second_won_pct"] = 100 * g["sw"] / (g["svpt"] - g["fi"])
    out["second_won_pct_if_svpt_plus_df"] = 100 * g["sw"] / (g["svpt"] + g["df"] - g["fi"])
    out["serve_pts_won_pct"] = 100 * (g["fw"] + g["sw"]) / g["svpt"]
    out["ace_pct"] = 100 * g["ace"] / g["svpt"]
    out["df_pct"] = 100 * g["df"] / g["svpt"]
    out["bp_saved_pct"] = 100 * g["bps"] / g["bpf"]
    return out


def edition_effects(num: pd.Series, den: pd.Series, baseline: pd.Series, edition: pd.Series, min_den: float,
                    iterations: int = 40) -> pd.DataFrame:
    """Same-player edition effects: rate = theta[baseline] + delta[edition] + noise, weighted by the denominator and
    fitted by alternating weighted means. The baseline key is a player-season (or player-season-surface), so delta is
    how an edition reads for the same players against their own matches elsewhere: the box-score analogue of the
    serve-speed acquisition's check 6. Returns delta (in rate units) and the rows per edition."""
    ok = num.notna() & den.notna() & (den >= min_den)
    y = pd.DataFrame({"r": (num / den)[ok], "w": den[ok], "b": baseline[ok], "e": edition[ok]})
    y["de"] = 0.0
    de = pd.Series(dtype=float)
    for _ in range(iterations):
        th = ((y["r"] - y["de"]) * y["w"]).groupby(y["b"]).sum() / y["w"].groupby(y["b"]).sum()
        y["th"] = y["b"].map(th)
        de = ((y["r"] - y["th"]) * y["w"]).groupby(y["e"]).sum() / y["w"].groupby(y["e"]).sum()
        y["de"] = y["e"].map(de)
    out = y.groupby("e").agg(rows=("r", "size"))
    out["delta"] = de
    return out
