"""The gate: what a live match's missing inputs mean for betting it (docs/decisions/2026-10-14-box-score-gate.md, which
replaced point 3 of docs/decisions/2026-10-08-prediction-run-box-scores.md; the review behind it:
docs/studies/box_score_gate_review/).

40 of the model's 57 inputs are built from box scores (41 of 58 until ios_points_short was dropped on 9 Oct 2026). A
match without one gets zero weight in them, in the training rows and the live rows alike, so the player's values lean
a little more toward the prior. For each live match and each of its players, every completed match before it, at the
same event or within WINDOW_DAYS of its day, is checked for a box score in the Stage 0 the inputs were built on.
Retired matches and walkovers are not required: no box-score input reads them.

A missing box score never blocks a bet: in the review's replay one missing earlier round moved the forecast by a median
of 0.35 points (at most 1.4), and a block gave up about twelve times the expected profit the gap cost. What a gap does
depends on its kind (kind()), by the training rows' own coverage (2013-2025, box_score_gate_review/coverage.py):
    BAR_KINDS    main tour, Challenger / WTA 125, qualifying above ITF level: 85-100% of training matches have a box
                 score, so a gap is a live difference. The match may be bet only if its edge clears EDGE_BAR: the
                 forecast moved 1 point against the side must still be worth betting at the odds
                 (pipeline/diagnostics applies it)
    NOTE_KINDS   team events (about half have one) and ITF, its qualifying included (about 7%): the training rows lack
                 them as often, so a gap is noted and changes nothing
A kind not listed (none in Stage 0 on 14 Oct 2026) is treated as a BAR_KINDS one.

Still blocking ("do not bet: inputs incomplete"):
    * a player who entered through the qualifying (Q, or LL) with no qualifying match in that span of Stage 0: results
      are missing, not only box scores (Tennis My Life has lacked the WTA's qualifying since June 2026);
    * a qualifying match after its first round (tour-level qualifying is bet since 22 Oct 2026: docs/decisions/
      2026-10-22-qualifying-bets.md) whose player has no match of the round before in Stage 0, at the event or in the
      PREVIOUS_ROUND_DAYS before (the feed files some women's qualifying under an id of its own): the result is
      missing. Women's qualifying reaches the tables only through the weekly lower-level feed, so a women's round 2
      is blocked until its round 1 is in a snapshot; a men's waits for Tennis My Life's qualifying file;
    * a live match not in Stage 0;
    * since 9 Oct 2026, an unknown indoor input: every training match has one (src/eda/indoor_fill/status.py), so a
      live match whose collected frame row (live_frame.parquet) has none fails.
The days are the timeline's: a match counts as within the window when its latest possible finish falls within it.

gate.csv, one row per live match: complete (True: may be bet, with or without the bar), bet (BET, BET_BAR or NO_BET),
edge_bar (EDGE_BAR or 0), bar_gaps and noted_gaps (their sum is without_box), reason. gate_missing.csv, one row per
missing box score: its kind and effect ("edge bar" or "note").

Run: ./python.sh src/eda/prediction_run/gate.py --run <folder> [--stage0 <folder>] [--timing <timing.parquet>]
     (default: the sandbox's tables, which hold the live rows)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.prediction_run import common as P  # noqa: E402

REQUIRED = ("completed",)
QUALIFIED = ("Q", "LL")                            # entries that played the qualifying (a lucky loser lost its last round)
MAIN_LEVELS = ("GS", "FIN", "T1000", "T500", "T250")
BAR_KINDS = ("main tour", "Challenger / WTA 125", "qualifying")
NOTE_KINDS = ("team event", "ITF")
EDGE_BAR = 0.01                                    # 1 point: about the 90th-percentile move of one missing round (1.17)
PREVIOUS_ROUND_DAYS = 4                            # qualifying rounds follow day by day (a Slam's over about four days)
BET, BET_BAR, NO_BET = "may be bet", "may be bet if its edge clears 1 point", "do not bet: inputs incomplete"
MISSING_COLUMNS = ["live_match_id", "player_id", "player_name", "match_id", "tournament_name", "round", "same_event",
                   "kind", "effect"]


def kind(level, qualifying) -> str:
    """The kind of an earlier match, as the review sorts them (box_score_gate_review/simulate_gate.level_group): ITF
    and team events first, so the ITF qualifying, which training lacks, is never taken for the tour's qualifying."""
    lv = str(level)
    if lv == "ITF":
        return "ITF"
    if lv == "TEAM":
        return "team event"
    if not pd.isna(qualifying) and bool(qualifying):
        return "qualifying"
    if lv in MAIN_LEVELS:
        return "main tour"
    if lv == "CH":
        return "Challenger / WTA 125"
    return "other"


def effect(k: str) -> str:
    """"note" for a kind the training rows mostly lack, else "edge bar"."""
    return "note" if k in NOTE_KINDS else "edge bar"


def previous_round_missing(h: pd.DataFrame, tournament_id, round_order, day: int) -> bool:
    """A qualifying match after its first round, and no match of the player's round before in ``h`` (the player's
    Stage 0 rows with their latest finish, lf): at the same event, or a qualifying match of that round finished in the
    PREVIOUS_ROUND_DAYS before the day."""
    k = int(round_order) - 1
    if k < 1:
        return False
    prev = h["qualifying"].astype(bool) & h["round_order"].eq(k)
    near = h["lf"].notna() & (h["lf"] >= day - PREVIOUS_ROUND_DAYS) & (h["lf"] < day)
    return not (prev & (h["tournament_id"].eq(tournament_id) | near)).any()


def previous_round_reason(name: str, rnd: str, round_order, tour: str) -> str:
    """The block's text: the result of the round before is missing, and what brings it."""
    before = f"Q{int(round_order) - 1}"
    where = ("women's qualifying reaches the data only through the weekly lower-level feed" if tour == "wta" else
             "Tennis My Life has not published it yet")
    return f"{name}: no {before} match before this {rnd} in Stage 0, so its result is missing ({where})"


def check(stage0: Path, timing: Path, meta: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per live match: blocked or not, the bar, and the earlier matches that lack a box score (one row per
    player-match, with its kind and effect)."""
    m = pd.read_parquet(stage0 / "stage0_matches.parquet",
                        columns=["match_id", "tour", "tournament_id", "tournament_name", "round", "round_order",
                                 "status", "has_box", "qualifying", "level", "tournament_date"])
    p = pd.read_parquet(stage0 / "stage0_match_players.parquet",
                        columns=["match_id", "player_id", "player_name", "entry"])
    for t in (m, p):
        t["match_id"] = t["match_id"].astype(str)
    t = pd.read_parquet(timing, columns=["match_id", "lf"]).astype({"match_id": str}).set_index("match_id")["lf"]
    m["lf"] = m["match_id"].map(t)
    hist = p.merge(m, on="match_id")
    live_ids = set(meta["match_id"])
    rows, missing = [], []
    for _, lm in meta.iterrows():
        me = m[m["match_id"].eq(lm["match_id"])]
        if me.empty:
            rows.append({"match_id": lm["match_id"], "complete": False, "reason": "not in Stage 0", "bar_gaps": 0,
                         "noted_gaps": 0, "without_box": 0, "edge_bar": 0.0})
            continue
        me = me.iloc[0]
        day = P.day_of(lm["day"])
        players = p[p["match_id"].eq(lm["match_id"])]
        checked = bar = noted = 0
        blocks = []
        for _, pl in players.iterrows():
            h = hist[hist["player_id"].eq(pl["player_id"]) & ~hist["match_id"].isin(live_ids)]
            same_event = h["tournament_id"].eq(me["tournament_id"]) & (h["round_order"] < me["round_order"])
            recent = h["lf"].notna() & (h["lf"] >= day - P.WINDOW_DAYS) & (h["lf"] < day)
            before = h[(same_event | recent) & h["status"].isin(REQUIRED)]
            checked += len(before)
            for _, g in before[~before["has_box"].astype(bool)].iterrows():
                k = kind(g["level"], g["qualifying"])
                e = effect(k)
                bar += e == "edge bar"
                noted += e == "note"
                missing.append({"live_match_id": lm["match_id"], "player_id": pl["player_id"],
                                "player_name": pl["player_name"], "match_id": g["match_id"],
                                "tournament_name": g["tournament_name"], "round": g["round"],
                                "same_event": bool(g["tournament_id"] == me["tournament_id"]), "kind": k, "effect": e})
            # TML files some events' qualifying under an id of its own (Shanghai 2026: -20261005, the main draw
            # -20261007), so the qualifying matches are looked for in the window, not by the event's id
            if str(pl.get("entry") or "").upper() in QUALIFIED and not h.loc[same_event | recent, "qualifying"].any():
                blocks.append(f"{pl['player_name']}: entered through qualifying, but no qualifying match in Stage 0")
            if bool(me["qualifying"]) and previous_round_missing(h, me["tournament_id"], me["round_order"], day):
                blocks.append(previous_round_reason(pl["player_name"], me["round"], me["round_order"], me["tour"]))
        notes = []
        if bar:
            notes.append(f"{bar} earlier match(es) without a box score of a kind the training rows nearly always hold: "
                         "the edge must clear 1 point")
        if noted:
            notes.append(f"{noted} earlier match(es) without a box score of a kind the training rows mostly lack: noted")
        rows.append({"match_id": lm["match_id"], "tournament_name": me["tournament_name"], "round": me["round"],
                     "players": " v ".join(players["player_name"].astype(str)), "earlier_matches_checked": checked,
                     "without_box": bar + noted, "bar_gaps": bar, "noted_gaps": noted, "complete": not blocks,
                     "edge_bar": EDGE_BAR if bar else 0.0, "reason": "; ".join(blocks + notes)})
    return pd.DataFrame(rows), pd.DataFrame(missing, columns=MISSING_COLUMNS)


def indoor_unknown(folder: Path) -> set[str]:
    """Live matches whose collected frame row has no indoor input (none when the rows are not collected yet)."""
    path = folder / "live_frame.parquet"
    if not path.exists():
        return set()
    f = pd.read_parquet(path, columns=["match_id", "in_indoor"])
    return set(f.loc[f["in_indoor"].isna(), "match_id"].astype(str))


def with_indoor(table: pd.DataFrame, unknown: set[str]) -> pd.DataFrame:
    """The gate's table with the indoor check: a match whose indoor input is unknown fails."""
    table = table.copy()
    hit = table["match_id"].astype(str).isin(unknown).to_numpy()
    if hit.any():
        note = "indoor or outdoor unknown (src/eda/indoor_fill/status.py found no source)"
        table.loc[hit, "reason"] = [f"{note}; {r}" if isinstance(r, str) and r else note for r in table.loc[hit, "reason"]]
        table.loc[hit, "complete"] = False
    return table


def verdict(table: pd.DataFrame) -> pd.Series:
    """The bet column: NO_BET when blocked, BET_BAR when a gap sets the bar, else BET."""
    ok = table["complete"].astype(bool).to_numpy()
    bar = table["edge_bar"].fillna(0).astype(float).to_numpy() > 0
    return pd.Series(np.where(~ok, NO_BET, np.where(bar, BET_BAR, BET)), index=table.index)


def run(folder: Path, stage0: Path, timing: Path) -> dict:
    meta = pd.read_parquet(folder / "live_meta.parquet").astype({"match_id": str})
    table, missing = check(stage0, timing, meta)
    table = with_indoor(table, indoor_unknown(folder))
    table["bet"] = verdict(table)
    table.to_csv(folder / "gate.csv", index=False)
    missing.to_csv(folder / "gate_missing.csv", index=False)
    out = {"checked_at": P.stamp(), "stage0": str(stage0), "live_matches": int(len(table)),
           "complete": int(table["complete"].sum()), "edge_bar": int((table["bet"] == BET_BAR).sum()),
           "noted_gaps": int(table["noted_gaps"].fillna(0).sum()),
           "incomplete": table.loc[~table["complete"], ["match_id", "reason"]].to_dict("records")}
    P.write_json(folder / "gate.json", out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="the run's folder (live_meta.parquet)")
    ap.add_argument("--stage0", default=str(P.SANDBOX / P.PD))
    ap.add_argument("--timing", default=str(P.SANDBOX / P.MT / "timing.parquet"))
    a = ap.parse_args()
    folder = Path(a.run) if Path(a.run).is_absolute() else ROOT / a.run
    res = run(folder, Path(a.stage0), Path(a.timing))
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
