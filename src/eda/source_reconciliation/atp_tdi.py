"""Readers of TDI, the ATP's data company (data/dump/points/tdi/): ATP tour and Challenger matches, mostly June-
September 2026, plus some older ones.

    atp_tdi_stats     the match statistics (statistics.parquet, period 'match'), as data_continuity/sources.py tdi()
                      maps them: ace Aces · df Double Faults · sv_gms Service Games Played · bp_faced Break Points
                      Faced · bp_saved Break Points Saved · sv_won Total Service Points Won · svpt = sv_won + the
                      opponent's Total Return Points Won. No first-serve split (first_in, first_won, second_won NaN).
    atp_tdi_recount   the nine counts recounted from its points (points.parquet): the server is given per point
                      (team_serving, tiebreaks included), the winner (winner), the serve number by the 'serve' label
                      (FIRST: first serve in; SECOND and DOUBLE FAULT: a second-serve point; ACE: by its faults, 0
                      first, 1 second). The fault counter (faults 0/1/2) disagrees with the label on about 0.1% of
                      points (mostly SECOND with faults 0), and the label's first serves agree better with the ATP's
                      own key statistics (ManTennisData: 97.1% of complete rows against 92.9% by faults, observed
                      while building this reader): x_first_in_faults keeps the faults reading. Aces (ace); the scores
                      after each point (team_a/b_game_score: 0, 15, 30, 40, Av; numbers in a tiebreak), so the score
                      before a point is the previous point's, and a break point is read from it (the receiver at 40
                      against less, or at Av): TDI's is_break_point flag marks the state AFTER the point (set on
                      exactly the points after which the receiver holds a break point) and is not used. Game 13 of a
                      set is its tiebreak.

Orientation: team A / team B are TDI's own (team_a_atp_ids, team_a_names), placed on Stage 0's sides by ATP code or
name inside the linked match, never by who won. Linked by the tdi link file of match_timing (source_key 'tdi:<uuid>';
built on identity pairs, first point time and place), and, where it has no link, by the event linker on TDI's own
ATP key (atp_year, atp_tournament_id, atp_match_code).

Run: ./python.sh src/eda/source_reconciliation/atp_tdi.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import atp_common as A  # noqa: E402
from src.eda.source_reconciliation import atp_points as P  # noqa: E402
from src.eda.source_reconciliation import atp_recount as R  # noqa: E402
from src.eda.source_reconciliation import common as C  # noqa: E402

LABELS = {"Aces": "ace", "Double Faults": "df", "Service Games Played": "sv_gms", "Break Points Faced": "bp_faced",
          "Break Points Saved": "bp_saved", "Total Service Points Won": "sv_won", "Total Return Points Won": "rt_won"}
SET_SCORE = re.compile(r"(\d+):(\d+)")
SCORE_PT = {"0": 0, "15": 1, "30": 2, "40": 3, "AV": 4, "A": 4, "AD": 4}


def sets_won(a: str, b: str) -> tuple[int, int]:
    ga = {k: int(g) for k, g in SET_SCORE.findall(str(a or ""))}
    gb = {k: int(g) for k, g in SET_SCORE.findall(str(b or ""))}
    wa = sum(1 for k in ga if k in gb and ga[k] > gb[k] and ga[k] >= 6)
    wb = sum(1 for k in gb if k in ga and gb[k] > ga[k] and gb[k] >= 6)
    return wa, wb


def matches() -> pd.DataFrame:
    m = pd.read_parquet(A.TDI / "matches.parquet")
    m = m[m["draw_type"].eq("singles")].copy()
    m["source_key"] = "tdi:" + m["match_id"].astype(str)
    m = m.rename(columns={"match_id": "tdi_id"}).drop_duplicates("source_key").set_index("source_key", drop=False)
    m["season"] = pd.to_numeric(m["atp_year"], errors="coerce").fillna(-1).astype(int)
    m["ev"] = pd.to_numeric(m["atp_tournament_id"], errors="coerce").fillna(-1).astype(int)
    hint = [P.round_hint(c) for c in m["atp_match_code"].fillna("")]
    m["qual"] = [h[0] for h in hint]
    m["round"] = [h[1] for h in hint]
    m["c1"], m["c2"] = m["team_a_atp_ids"].map(A.atp_code), m["team_b_atp_ids"].map(A.atp_code)
    m["f1"], m["f2"] = m["team_a_names"].fillna(""), m["team_b_names"].fillna("")
    sw = [sets_won(a, b) for a, b in zip(m["team_a_scores"], m["team_b_scores"])]
    m["sets_a"], m["sets_b"] = [s[0] for s in sw], [s[1] for s in sw]
    m["winner_no"] = np.where(m["sets_a"] > m["sets_b"], 1, np.where(m["sets_b"] > m["sets_a"], 2, np.nan))
    m["finished"] = np.maximum(m["sets_a"], m["sets_b"]) >= 2
    return m


orient_in_match = A.orient_in_match


def link(m: pd.DataFrame, xw: pd.Series, linker: A.EventLinker) -> tuple[pd.DataFrame, dict]:
    lf = C.links("tdi", columns=["match_id", "source_key", "score_agrees"]).drop_duplicates("source_key") \
        .set_index("source_key")
    m = m.copy()
    m["lf_match_id"] = m.index.map(lf["match_id"])
    m["match_id"], m["p1_side"], m["link_method"] = None, None, ""
    for key in m.index[m["lf_match_id"].notna()]:
        k1 = A.player_keys(m.at[key, "c1"], m.at[key, "f1"], "", xw)
        k2 = A.player_keys(m.at[key, "c2"], m.at[key, "f2"], "", xw)
        side = orient_in_match(linker, m.at[key, "lf_match_id"], k1, k2)
        if side:
            m.loc[key, ["match_id", "p1_side", "link_method"]] = [m.at[key, "lf_match_id"], side, "tdi_link_file"]
    s0_ids = set(linker.s0["match_id"])
    rest = m[m["match_id"].isna()]
    lk = linker.link(rest, xw)
    lk = lk[lk["match_id"].notna() & ~lk["match_id"].isin(set(m["match_id"].dropna()))]
    m.loc[lk.index, ["match_id", "p1_side", "link_method"]] = lk[["match_id", "p1_side", "link_method"]].to_numpy()
    info = {"singles_records": int(len(m)), "in_link_file": int(m["lf_match_id"].notna().sum()),
            "link_file_match_not_in_snapshot": int((m["lf_match_id"].notna() & ~m["lf_match_id"].isin(s0_ids)).sum()),
            "linked": int(m["match_id"].notna().sum()), "link_methods": m["link_method"].value_counts().to_dict(),
            "unlinked": int(m["match_id"].isna().sum())}
    return m, info


def stats_reader(m: pd.DataFrame, info: dict) -> tuple[pd.DataFrame, dict]:
    st = pd.read_parquet(A.TDI / "statistics.parquet", columns=["match_id", "period", "label", "team_a", "team_b"],
                         filters=[("period", "==", "match")])
    st = st[st["label"].isin(LABELS)].assign(field=lambda d: d["label"].map(LABELS))
    st["source_key"] = "tdi:" + st["match_id"].astype(str)
    w = st.pivot_table(index="source_key", columns="field", values=["team_a", "team_b"], aggfunc="first")
    w.columns = [f"{f}_{'1' if side == 'team_a' else '2'}" for side, f in w.columns]
    for c in w.columns:
        w[c] = pd.to_numeric(w[c], errors="coerce").astype("float64")
    info = dict(info, reader="atp_tdi_stats", records_with_match_statistics=int(len(w)))
    lm = m[m["match_id"].notna()].join(w, how="inner")
    info["dropped"] = {"no_match_statistics": int(m["match_id"].notna().sum() - len(lm))}
    lm["svpt_1"] = lm["sv_won_1"] + lm["rt_won_2"]
    lm["svpt_2"] = lm["sv_won_2"] + lm["rt_won_1"]
    lm["complete"] = lm["finished"].astype(bool)
    lm["x_status"] = np.where(lm["finished"], "two sets won", "unfinished")
    lm["x_season"] = lm["season"]
    lm["x_level"] = lm["level"]
    rows = A.long_rows(lm, A.FIELDS, extra=["complete", "link_method", "x_status", "x_season", "x_level"])
    # TDI states no winner: the one who won two sets, read only where the match was finished (a player who retires
    # may lead in sets)
    wn = pd.concat([lm["winner_no"].where(lm["finished"])] * 2, ignore_index=True)
    rows["x_won"] = pd.Series(np.where(wn.isna(), None, wn == rows["x_player_no"].astype(float)), dtype=object)
    rows["x_code"] = pd.concat([lm["c1"], lm["c2"]], ignore_index=True).to_numpy()
    info["winner_vs_stage0"] = A.winner_check(rows)
    return A.to_contract(rows, "atp_tdi_stats", "box"), info


def tdi_points(g: pd.DataFrame) -> tuple[list[dict], dict]:
    """TDI's points of one match as engine points (player 1 = team A). The serve number is the label's (FIRST: the
    first serve in; SECOND, DOUBLE FAULT: a second-serve point; ACE: by its faults, 0 first, 1 second), and the
    faults-only reading (faults 0 = first serve in) is counted beside it (d['faults_first'])."""
    pts, d = [], {"faults_first": {1: 0, 2: 0}, "flag_bp_post": 0, "score_bp_pre": 0, "flag_on_pre_bp": 0,
                  "score_bp_post": 0, "flag_on_post_bp": 0, "label_faults_disagree": 0}
    g = g.assign(n_set=pd.to_numeric(g["set"], errors="coerce"), n_game=pd.to_numeric(g["game"], errors="coerce"),
                 n_point=pd.to_numeric(g["point"], errors="coerce")).sort_values(["n_set", "n_game", "n_point"])
    prev_key, prev = None, ("0", "0")
    for r in g.itertuples(index=False):
        s, gm, p = P.as_int(r.n_set), P.as_int(r.n_game), P.as_int(r.n_point)
        server = 1 if r.team_serving == "teamA" else 2 if r.team_serving == "teamB" else None
        winner = 1 if r.winner == "teamA" else 2 if r.winner == "teamB" else None
        if (s, gm) != prev_key:
            prev = ("0", "0")
            prev_key = (s, gm)
        tb = gm == 13
        a, b = str(prev[0]).upper(), str(prev[1]).upper()
        bp_pre = False
        if not tb and server in (1, 2) and a in SCORE_PT and b in SCORE_PT:
            sv, rc = (SCORE_PT[a], SCORE_PT[b]) if server == 1 else (SCORE_PT[b], SCORE_PT[a])
            bp_pre = (rc == 3 and sv < 3) or rc == 4
        faults = P.as_int(r.faults)
        label = str(r.serve).upper()
        dfault = label == "DOUBLE FAULT" or faults == 2
        by_faults = 2 if (dfault or (faults is not None and faults >= 1)) else 1
        if label == "FIRST":
            serve = 1
        elif label in ("SECOND", "DOUBLE FAULT"):
            serve = 2
        elif label == "ACE":
            serve = 2 if (faults is not None and faults >= 1) else 1
        else:
            serve = by_faults
        d["label_faults_disagree"] += serve != by_faults
        if server in (1, 2) and by_faults == 1:
            d["faults_first"][server] += 1
        d["score_bp_pre"] += bp_pre
        d["flag_on_pre_bp"] += bp_pre and P.truthy(r.is_break_point)
        d["flag_bp_post"] += P.truthy(r.is_break_point)
        a2, b2 = str(r.team_a_game_score).upper(), str(r.team_b_game_score).upper()
        bp_post = False
        if not tb and server in (1, 2) and a2 in SCORE_PT and b2 in SCORE_PT:
            sv2, rc2 = (SCORE_PT[a2], SCORE_PT[b2]) if server == 1 else (SCORE_PT[b2], SCORE_PT[a2])
            bp_post = (rc2 == 3 and sv2 < 3) or rc2 == 4
        d["score_bp_post"] += bp_post
        d["flag_on_post_bp"] += bp_post and P.truthy(r.is_break_point)
        pts.append({"set": s, "game": gm, "point": p, "server": server, "serve": serve, "winner": winner,
                    "end": "ACE" if P.truthy(r.ace) else "DOUBLE FAULT" if dfault else "",
                    "bp1": bp_pre and server == 2, "bp2": bp_pre and server == 1, "tb": tb})
        prev = (r.team_a_game_score, r.team_b_game_score)
    return pts, d


def recount_reader(m: pd.DataFrame, info: dict) -> tuple[pd.DataFrame, dict]:
    cols = ["match_id", "set", "game", "point", "winner", "team_serving", "team_a_game_score", "team_b_game_score",
            "ace", "is_break_point", "serve", "faults"]
    p = pd.read_parquet(A.TDI / "points.parquet", columns=cols)
    p["source_key"] = "tdi:" + p["match_id"].astype(str)
    lm = m[m["match_id"].notna()]
    p = p[p["source_key"].isin(set(lm.index))]
    groups, diag = {}, {}
    for key, g in p.groupby("source_key"):
        groups[key], diag[key] = tdi_points(g)
    info = dict(info, reader="atp_tdi_recount", records_with_points=int(len(groups)))
    lm = lm[lm.index.isin(list(groups))]
    ctx = P.stage0_context(lm["match_id"], lm["p1_side"])
    wide = P.recount_all({k: groups[k] for k in lm.index}, ctx, derive=False)
    wide = lm[["source_key", "match_id", "p1_side", "link_method", "season", "c1", "c2", "level"]].join(wide).join(ctx)
    wide["x_first_in_faults_1"] = [diag[k]["faults_first"][1] for k in wide.index]
    wide["x_first_in_faults_2"] = [diag[k]["faults_first"][2] for k in wide.index]
    wide["x_label_faults_disagree"] = [diag[k]["label_faults_disagree"] for k in wide.index]
    wide = wide.rename(columns={"s0_status": "x_s0_status", "season": "x_season", "level": "x_level"})
    wide["x_route"] = "tdi-points"
    for c in P.PER_MATCH:
        if c not in wide:
            wide[c] = np.nan
    rows = A.long_rows(wide, P.PER_PLAYER + ["x_first_in_faults"],
                       extra=P.PER_MATCH + ["complete", "link_method", "x_route", "x_s0_status", "x_season",
                                            "x_label_faults_disagree",
                                            "x_level"])
    w1 = pd.concat([wide["x_sets_won_1"], wide["x_sets_won_2"]], ignore_index=True).to_numpy()
    w2 = pd.concat([wide["x_sets_won_2"], wide["x_sets_won_1"]], ignore_index=True).to_numpy()
    done = rows["complete"].astype(bool) & rows["x_s0_status"].eq("completed")
    rows["x_won"] = pd.Series(np.where(done, w1 > w2, None), dtype=object)
    rows["x_code"] = pd.concat([wide["c1"], wide["c2"]], ignore_index=True).to_numpy()
    tot = {k: sum(d[k] for d in diag.values()) for k in ("flag_bp_post", "score_bp_pre", "flag_on_pre_bp",
                                                          "score_bp_post", "flag_on_post_bp")}
    info["break_point_flag_vs_score"] = {
        "points_played_at_break_point_by_the_scores": tot["score_bp_pre"],
        "of_them_flagged_is_break_point": tot["flag_on_pre_bp"],
        "points_after_which_the_receiver_holds_a_break_point": tot["score_bp_post"],
        "of_them_flagged_is_break_point_": tot["flag_on_post_bp"],
        "points_flagged_is_break_point": tot["flag_bp_post"],
        "used": "break points are read from TDI's scores before each point (the previous point's scores), not from "
                "the flag"}
    info["recounted_matches"] = int(len(wide))
    info["recounts_complete"] = int(wide["complete"].sum())
    info["incomplete_reasons"] = {
        "point_gaps": int((wide["x_point_gaps"] > 0).sum()), "game_gaps": int((wide["x_game_gaps"] > 0).sum()),
        "games_not_ending_at_last_point": int((wide["x_games_not_ending_at_last_point"] > 0).sum()),
        "set_games_differ_from_stage0": int(wide["x_sets_equal"].eq(False).sum()),
        "points_without_server": int((wide["x_points_without_server"] > 0).sum())}
    info["winner_vs_stage0"] = A.winner_check(rows)
    return A.to_contract(rows, "atp_tdi_recount", "recount"), info


def main() -> int:
    xw, linker = A.crosswalk(), A.EventLinker()
    m, info = link(matches(), xw, linker)
    info["source"] = "data/dump/points/tdi/{matches,statistics,points}.parquet"
    for fn in (stats_reader, recount_reader):
        rows, inf = fn(m, info)
        A.write_reader(inf["reader"], rows, inf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
