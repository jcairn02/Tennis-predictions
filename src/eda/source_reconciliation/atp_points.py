"""Point-record plumbing shared by the atp_ recount readers: Infosys match codes, MatchBeats and rally-analysis rows
turned into the recount engine's points, the Stage 0 context a recount is checked against, and the long output."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from src.eda.source_reconciliation import atp_common as A
from src.eda.source_reconciliation import atp_recount as R

NEXT_GEN_FINALS = {7696}          # no-ad games, sets to 4 (the 2018-2019, 2021-2023 Next Gen ATP Finals, Milan/Jeddah)
END_MB = {"A": "ACE", "P": "DOUBLE FAULT", "DF": "DOUBLE FAULT", "W": "WINNER", "FE": "FORCED ERROR",
          "UE": "UNFORCED ERROR", "N": "UNCLASSIFIED"}
WIN_OF_LIST = {"t1win": 1, "t2err": 1, "t2win": 2, "t1err": 2}
PER_PLAYER = A.FIELDS + ["x_tb_first", "x_bp_faced_seq", "x_sets_won", "x_sv_gms_unfinished"]
PER_MATCH = ["x_points", "x_points_without_server", "x_point_gaps", "x_game_gaps", "x_games_not_ending_at_last_point",
             "x_sets_recount", "x_sets_stage0", "x_sets_equal", "x_tb_played", "x_games", "x_tiebreaks",
             "x_games_without_evidence", "x_games_evidence_against_alternation", "x_sets_without_assignment",
             "x_aces_against_assigned_server", "x_double_faults_against_assigned_server",
             "x_set_first_server_against_previous_set", "x_set_pairs", "x_tiebreak_evidence_against",
             "x_score_steps_inconsistent", "x_games_two_servers"]


def round_hint(code: str) -> tuple[bool | None, str]:
    """(qualifying, round) from an Infosys match code: QSnnn qualifying (round unknown); MS001 F, MS002-003 SF,
    MS004-007 QF, MS008-015 R16, MS016-031 R32, MS032-063 R64, MS064-127 R128 (a round robin's codes do not follow
    this: the round is only a tie-breaker)."""
    m = re.match(r"^([MQ])S(\d+)$", str(code or "").upper())
    if not m:
        return None, ""
    if m.group(1) == "Q":
        return True, ""
    n = int(m.group(2))
    for hi, r in ((1, "F"), (3, "SF"), (7, "QF"), (15, "R16"), (31, "R32"), (63, "R64"), (127, "R128")):
        if n <= hi:
            return False, r
    return False, ""


def truthy(v) -> bool:
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    return str(v).strip().upper() in ("TRUE", "1", "T", "YES")


def as_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def mb_points(g: pd.DataFrame) -> list[dict]:
    """MatchBeats rows of one match (server, serve, scorer, result, isBrkPt, set, game, point, game_fields)."""
    out = []
    for r in g.itertuples(index=False):
        srv = as_int(r.server)
        bp = truthy(r.isBrkPt)
        tb = '"isTieBreak": true' in str(r.game_fields or "")
        out.append({"set": as_int(r.set), "game": as_int(r.game), "point": as_int(r.point), "server": srv,
                    "serve": as_int(r.serve), "winner": as_int(r.scorer), "end": END_MB.get(str(r.result), ""),
                    "bp1": bp and srv == 2, "bp2": bp and srv == 1, "tb": tb})
    return out


def rally_point(point_id, lst, end, score, bp1, bp2, tb) -> dict | None:
    """One rally-analysis entry as an engine point; pointId is set_game_point_serve."""
    parts = str(point_id or "").split("_")
    if len(parts) != 4:
        return None
    s, g, p, sv = (as_int(x) for x in parts)
    return {"set": s, "game": g, "point": p, "serve": sv, "winner": WIN_OF_LIST.get(str(lst)), "end": str(end or ""),
            "score": score, "bp1": truthy(bp1), "bp2": truthy(bp2), "tb": truthy(tb)}


def rally_points(g: pd.DataFrame) -> list[dict]:
    """Staged rally-analysis rows of one match (list, pointId, pointEndType, score, t1/t2BreakPoint, tieBreak);
    a point filed twice is kept once."""
    out, seen = [], set()
    for r in g.itertuples(index=False):
        if r.pointId in seen:
            continue
        seen.add(r.pointId)
        p = rally_point(r.pointId, r.list, r.pointEndType, r.score, r.t1BreakPoint, r.t2BreakPoint, r.tieBreak)
        if p:
            out.append(p)
    return out


def stage0_context(match_ids: pd.Series, p1_side: pd.Series) -> pd.DataFrame:
    """Per linked source match: Stage 0's set games (winner first), whether player 1 is Stage 0's winner, the status."""
    s = A.s0_men().set_index("match_id")
    a_won = match_ids.map(s["a_won"])
    p1_win = pd.Series(np.where(match_ids.isna(), None,
                                np.where(p1_side.eq("A"), a_won, np.where(p1_side.eq("B"), ~a_won.astype(bool),
                                                                          None))), index=match_ids.index)
    return pd.DataFrame({"s0_sets": match_ids.map(s["sets_w"]), "p1_is_winner": p1_win,
                         "s0_status": match_ids.map(s["status"]), "s0_ev": match_ids.map(s["ev"])},
                        index=match_ids.index)


def recount_all(groups: dict, ctx: pd.DataFrame, derive: bool) -> pd.DataFrame:
    """groups: {source row index: engine points}; ctx: stage0_context on the same index. One row per match."""
    rows = {}
    for i, pts in groups.items():
        c = ctx.loc[i] if i in ctx.index else None
        linked = c is not None and isinstance(c["s0_sets"], tuple)
        no_ad = bool(c is not None and c["s0_ev"] in NEXT_GEN_FINALS)
        r = R.recount_match(pts, c["s0_sets"] if linked else None, c["p1_is_winner"] if linked else None,
                            bool(c is not None and c["s0_status"] == "retired"), derive=derive, no_ad=no_ad)
        rows[i] = r
    return pd.DataFrame.from_dict(rows, orient="index")


def to_long(wide: pd.DataFrame, extra: list[str]) -> pd.DataFrame:
    """The recount's wide rows (match_id, p1_side, source_key, <field>_1/_2, per-match x_) in the contract's long form,
    with x_won (the recount's winner, for complete recounts of completed matches) per player."""
    for c in PER_PLAYER:
        for no in (1, 2):
            if f"{c}_{no}" not in wide:
                wide[f"{c}_{no}"] = np.nan
    for c in PER_MATCH:
        if c not in wide:
            wide[c] = np.nan
    rows = A.long_rows(wide, PER_PLAYER, extra=PER_MATCH + extra)
    w1 = pd.concat([wide["x_sets_won_1"], wide["x_sets_won_2"]], ignore_index=True).to_numpy()
    w2 = pd.concat([wide["x_sets_won_2"], wide["x_sets_won_1"]], ignore_index=True).to_numpy()
    done = rows["complete"].astype(bool) & rows["x_s0_status"].eq("completed")
    rows["x_won"] = pd.Series(np.where(done, w1 > w2, None), index=rows.index, dtype=object)
    return rows
