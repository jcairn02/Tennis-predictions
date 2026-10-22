"""The Match Charting Project recounted on Stage 0's ids (reader tp_mcp_recount of the source-reconciliation study;
brief: docs/studies/source_reconciliation/subagent_briefs.md).

Inputs (read-only): data/dump/points/match_charting_project/ (metadata/charting-{m,w}-matches.parquet,
points/charting-{m,w}-points-{2010s,2020s}.parquet, stats/charting-{m,w}-stats-Overview.parquet) and the study's frozen
link file _snapshot/links/match_charting.parquet (source_key = the chart's match_id -> Stage 0 match_id).

Every count is recounted from each point's first- and second-serve strings ('1st', '2nd'), the server (Svr: 1 =
Player 1) and the point's winner (PtWinner). The conventions, read from the data (16 Oct 2026; the shot-level study's
mcp_point() and the RG referee scripts use the same codes):
    * a serve string may start with lets, 'c' (one per let); they are dropped;
    * a serve is a fault when, lets dropped, it is a direction (4 wide, 5 body, 6 T, 0 unknown; may be missing),
      optional modifiers (+ ^ ; !), one or more fault codes n (net) w (wide) d (deep) x (wide and deep) g (foot
      fault) e (unknown) ! (shank), and optional trailing marks (; @ # !): '6d@', '4^n', '4;w', '4wd'. 'V' (a time
      violation) costs the first serve like a fault. This reading reproduces MCP's own Overview first serves in
      99.62% of player rows (a narrower one, direction + one code: 99.4%; "a second string means a fault": 99.17%);
    * a first serve in followed by a second-serve string (128 points), or a fault with no second serve (6), is
      ambiguous: x_bad_points, and the chart is not complete;
    * a double fault: the second serve is a fault (the server loses 56,420 of 56,426);
    * an ace: the serve played is its direction followed by '*' (the server wins 94,005 of 94,005). '#' after the
      serve (an unreturned serve the returner touched) and 'C' are not aces;
    * 'S' / 'R' (the whole first string): the point went to the server / returner but the video missed it: a served
      point with no serve detail (counted in svpt and sv_won; first serves unknown: x_unknown_points);
    * 'P' / 'Q': a point penalty against the server / returner: no serve, not counted as a served point
      (x_penalty_points); it moves the score.
Counts per player (that player's serve): svpt, first_in, first_won, second_won (a double fault is a second-serve point
lost), ace, df, sv_won, sv_gms (completed non-tiebreak games served), bp_faced (points of a non-tiebreak service game
at which the returner wins the game by winning the point: Pts, written server first, 0/15/30-40 or 40-AD) and
bp_saved. A tiebreak game is one whose point scores are numbers (1-0, 2-3, ...).
complete: the chart's points are numbered 1..N without a gap, every point's recorded score (sets, games, points) is
the previous point's score plus that point's winner, the first point is 0-0 in the first game, the set scores so
reconstructed equal Stage 0's score, and no point lacks its serve detail (S/R). x_points_consistent is the same
without the last condition (svpt, sv_won, sv_gms and break points do not need serve detail).
Orientation: the chart's Player 1 / Player 2 names graded against Stage 0's A and B (tp_common.orient). x_src_won is
the recount's winner by finished sets (None where the sets do not decide it, as at a retirement).
x_mcp_*: MCP's own Overview totals (set Total) of the same player, computed by the project from the same strings:
a check of this parser, not an independent record.
Writes box/readers/tp_mcp_recount.{parquet,json}.
Run: ./python.sh src/eda/source_reconciliation/tp_mcp.py
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import tp_common as T  # noqa: E402

BASE = C.DUMP / "points" / "match_charting_project"
READER, FAMILY = "tp_mcp_recount", "mcp"
FAULT = re.compile(r"^[0456]?[+^;!]*[nwdxge!V]+[;@#!]*$")
ACE = re.compile(r"^[0456][+^;]*\*$")
GAME_PTS = {"0": 0, "15": 1, "30": 2, "40": 3, "AD": 4, "A": 4}


def serve_kind(first, second) -> tuple[str, bool, int]:
    """(kind, ace, lets): kind 'first' (first serve in), 'second' (second serve in), 'df', 'unknown' (S/R),
    'penalty' (P/Q), 'bad' (unparseable)."""
    s1 = first.strip() if isinstance(first, str) else ""
    s2 = second.strip() if isinstance(second, str) else ""
    lets = (len(s1) - len(s1.lstrip("c"))) + (len(s2) - len(s2.lstrip("c")))
    a, b = s1.lstrip("c"), s2.lstrip("c")
    if a in ("S", "R"):
        return "unknown", False, lets
    if a in ("P", "Q"):
        return "penalty", False, lets
    if not a:
        return "bad", False, lets
    if a == "V" or FAULT.match(a):
        if not b:
            return "bad", False, lets              # a first-serve fault without a second serve
        if FAULT.match(b) or b == "V":
            return "df", False, lets
        return "second", bool(ACE.match(b)), lets
    if b:
        return "bad", False, lets                  # a first serve in, yet a second-serve string: ambiguous
    return "first", bool(ACE.match(a)), lets


def is_tb_score(text) -> bool:
    """A point score that only a tiebreak can have: a number other than 0, 15, 30, 40 on either side."""
    m = re.match(r"^\s*(\w+)-(\w+)\s*$", str(text or ""))
    if not m:
        return False
    return any(v.isdigit() and v not in ("0", "15", "30", "40") for v in (m.group(1), m.group(2)))


def parse_pts(text, tb: bool) -> tuple[object, object]:
    """Pts -> (first, second): a regular game's scores as 0..4 (0 15 30 40 AD), a tiebreak's as ints."""
    m = re.match(r"^\s*(\w+)-(\w+)\s*$", str(text or ""))
    if not m:
        return None, None
    x, y = m.group(1).upper(), m.group(2).upper()
    if tb:
        return (int(x), int(y)) if x.isdigit() and y.isdigit() else (None, None)
    if x in GAME_PTS and y in GAME_PTS:
        return GAME_PTS[x], GAME_PTS[y]
    return None, None


def _after_game(s: int, r: int, server_won: bool) -> tuple[int, int, bool]:
    """A regular game's score (server, returner on 0..4) after a point; returns (s, r, game_over)."""
    if server_won:
        if s == 4:
            return s, r, True
        if s == 3 and r < 3:
            return s, r, True
        if s == 3 and r == 4:
            return 3, 3, False
        if s == 3 and r == 3:
            return 4, 3, False
        return s + 1, r, False
    if r == 4:
        return s, r, True
    if r == 3 and s < 3:
        return s, r, True
    if r == 3 and s == 4:
        return 3, 3, False
    if r == 3 and s == 3:
        return 3, 4, False
    return s, r + 1, False


def recount_match(g: pd.DataFrame) -> dict:
    """One chart's points (sorted by Pt) -> per player (index 0 = Player 1) counts and the checks."""
    n = len(g)
    pt = pd.to_numeric(g["Pt"], errors="coerce").to_numpy()
    svr = pd.to_numeric(g["Svr"], errors="coerce").to_numpy()
    win = pd.to_numeric(g["PtWinner"], errors="coerce").to_numpy()
    s1, s2 = pd.to_numeric(g["Set1"], errors="coerce").to_numpy(), pd.to_numeric(g["Set2"], errors="coerce").to_numpy()
    g1, g2 = pd.to_numeric(g["Gm1"], errors="coerce").to_numpy(), pd.to_numeric(g["Gm2"], errors="coerce").to_numpy()
    pts = g["Pts"].astype(str).to_numpy()
    first, second = g["1st"].to_numpy(), g["2nd"].to_numpy()
    cnt = {k: [0, 0] for k in ("svpt", "first_in", "first_won", "second_won", "ace", "df", "sv_won", "sv_gms",
                              "bp_faced", "bp_saved", "unknown", "penalty", "lets", "bad")}
    ok = bool(n) and np.isfinite(pt).all() and (np.diff(pt) == 1).all() and pt[0] == 1
    ok &= np.isin(svr, (1, 2)).all() and np.isin(win, (1, 2)).all()
    ok = bool(ok)
    # games: (set index, game index) from the recorded scores
    key = list(zip(np.nan_to_num(s1 + s2, nan=-1).astype(int), np.nan_to_num(g1 + g2, nan=-1).astype(int)))
    tb_game: dict = {}
    for k, p in zip(key, pts):
        tb_game[k] = tb_game.get(k, False) or is_tb_score(p)
    sets_last: dict = {}
    for i in range(n):
        sv = int(svr[i]) - 1 if np.isfinite(svr[i]) else 0
        w = int(win[i]) - 1 if np.isfinite(win[i]) else -1
        kind, ace, lets = serve_kind(first[i], second[i])
        cnt["lets"][sv] += lets
        if kind == "penalty":
            cnt["penalty"][sv] += 1
        else:
            cnt["svpt"][sv] += 1
            if w == sv:
                cnt["sv_won"][sv] += 1
            if kind == "unknown":
                cnt["unknown"][sv] += 1
            elif kind == "bad":
                cnt["bad"][sv] += 1
            elif kind == "first":
                cnt["first_in"][sv] += 1
                cnt["first_won"][sv] += int(w == sv)
                cnt["ace"][sv] += int(ace)
            elif kind == "second":
                cnt["second_won"][sv] += int(w == sv)
                cnt["ace"][sv] += int(ace)
            elif kind == "df":
                cnt["df"][sv] += 1
        tb = tb_game.get(key[i], False)
        x, y = parse_pts(pts[i], tb)
        if not tb and x is not None and kind != "penalty" and ((y == 3 and x < 3) or y == 4):
            cnt["bp_faced"][sv] += 1
            cnt["bp_saved"][sv] += int(w == sv)
        # the next point's recorded score must be this one's plus this point's winner
        if x is None or w < 0:
            ok = False
            continue
        server_won = (w == sv)
        if tb:
            nx, ny = (x + 1, y) if server_won else (x, y + 1)
            hi, lo = max(nx, ny), min(nx, ny)
            game_over = hi >= 7 and hi - lo >= 2
            # a 10-point tiebreak is not over at 7: the next point says whether the game went on
            if game_over and i + 1 < n and key[i + 1] == key[i]:
                game_over = False
        else:
            nx, ny, game_over = _after_game(x, y, server_won)
        if i + 1 < n:
            same = key[i + 1] == key[i]
            if same:
                ex, ey = parse_pts(pts[i + 1], tb)
                if int(svr[i + 1]) - 1 != sv and not tb:
                    ok = False
                if tb:
                    # tiebreak scores are written from the current server's side: compare as Player 1 / Player 2
                    p1n = nx if sv == 0 else ny
                    p2n = ny if sv == 0 else nx
                    sv2 = int(svr[i + 1]) - 1
                    e1 = ex if sv2 == 0 else ey
                    e2 = ey if sv2 == 0 else ex
                    ok &= (e1, e2) == (p1n, p2n) and not game_over
                else:
                    ok &= (ex, ey) == (nx, ny) and not game_over
            else:
                ok &= bool(game_over)
                gw = w                                   # the game's winner
                if s1[i + 1] + s2[i + 1] == s1[i] + s2[i]:
                    exp = (g1[i] + (gw == 0), g2[i] + (gw == 1))
                    ok &= (g1[i + 1], g2[i + 1]) == exp
                else:
                    sets_last[int(s1[i] + s2[i])] = (int(g1[i] + (gw == 0)), int(g2[i] + (gw == 1)))
                    ok &= (s1[i + 1], s2[i + 1]) == (s1[i] + (gw == 0), s2[i] + (gw == 1)) and \
                        (g1[i + 1], g2[i + 1]) == (0, 0)
        if not tb and game_over:
            cnt["sv_gms"][sv] += 1
        if i == n - 1:
            if game_over:
                sets_last[int(s1[i] + s2[i])] = (int(g1[i] + (w == 0)), int(g2[i] + (w == 1)))
            else:
                sets_last[int(s1[i] + s2[i])] = (int(g1[i]), int(g2[i]))
    if n:
        ok &= (s1[0], s2[0], g1[0], g2[0]) == (0, 0, 0, 0) and str(pts[0]).strip() == "0-0"
    sets = tuple(sets_last[k] for k in sorted(sets_last))
    return {"cnt": cnt, "ok": bool(ok), "sets": sets}


def main() -> int:
    t0 = time.time()
    files = sorted(BASE.glob("points/charting-*-points-*.parquet")) + \
        sorted(BASE.glob("metadata/charting-*-matches.parquet")) + sorted(BASE.glob("stats/charting-*-stats-Overview.parquet"))
    rec = T.receipts(files)
    meta = pd.concat([pd.read_parquet(BASE / "metadata" / f"charting-{g}-matches.parquet",
                                      columns=["match_id", "Player 1", "Player 2", "Date", "Tournament", "Round"])
                      for g in ("m", "w")], ignore_index=True).drop_duplicates("match_id")
    pts = pd.concat([pd.read_parquet(f, columns=["match_id", "Pt", "Set1", "Set2", "Gm1", "Gm2", "Pts", "TbSet", "Svr",
                                                 "1st", "2nd", "PtWinner"])
                     for f in sorted(BASE.glob("points/charting-*-points-*.parquet"))], ignore_index=True)
    ov = pd.concat([pd.read_parquet(BASE / "stats" / f"charting-{g}-stats-Overview.parquet")
                    for g in ("m", "w")], ignore_index=True)
    ov = ov[ov["set"].astype(str).eq("Total")].drop_duplicates(["match_id", "player"])
    links = C.links("match_charting")
    S = T.s0_frame().set_index("match_id")
    links = links[links["match_id"].isin(S.index)]
    lk = links.set_index("source_key")
    stats = {"charts_listed": int(len(meta)), "charts_with_points": int(pts["match_id"].nunique()),
             "point_rows": int(len(pts)), "links": int(len(links))}
    L = meta[meta["match_id"].isin(lk.index)].copy()
    L["s0"] = L["match_id"].map(lk["match_id"])
    L["link_method"] = L["match_id"].map(lk["link_method"])
    na, nb = S.loc[L["s0"], "name_a"].to_numpy(), S.loc[L["s0"], "name_b"].to_numpy()
    o = [T.orient(x, y, a, b) for x, y, a, b in zip(L["Player 1"], L["Player 2"], na, nb)]
    L["a1"] = [x[0] for x in o]
    L["g_same"], L["g_swap"] = [x[1] for x in o], [x[2] for x in o]
    stats["linked_charts"] = int(len(L))
    stats["linked_with_points"] = int(L["match_id"].isin(set(pts["match_id"])).sum())
    stats["orientation_unresolved"] = int(L["a1"].isna().sum())
    pts = pts[pts["match_id"].isin(set(L["match_id"]))].copy()
    pts["_pt"] = pd.to_numeric(pts["Pt"], errors="coerce")
    pts = pts.sort_values(["match_id", "_pt"], kind="mergesort")
    rows = []
    for mid, g in pts.groupby("match_id", sort=False):
        res = recount_match(g)
        r = {"chart": mid, "ok": res["ok"], "sets": res["sets"], "n_points": len(g)}
        for k, v in res["cnt"].items():
            r[f"p1_{k}"], r[f"p2_{k}"] = v[0], v[1]
        rows.append(r)
    R = pd.DataFrame(rows).merge(L, left_on="chart", right_on="match_id", how="inner", suffixes=("", "_meta"))
    T.log(f"recounted {len(R):,} linked charts in {time.time() - t0:.0f}s")
    # set scores against Stage 0's score, oriented
    s0_ok, rec_win = [], []
    for sets, a1, mid in zip(R["sets"], R["a1"], R["s0"]):
        if a1 is None or not sets:
            s0_ok.append(False)
            rec_win.append(None)
            continue
        a_won, s0s = bool(S.at[mid, "a_won"]), S.at[mid, "sets_w"]
        ab = [(x, y) if a1 else (y, x) for x, y in sets]
        wf = ab if a_won else [(y, x) for x, y in ab]
        s0_ok.append(bool(T.K.sets_equal(tuple(wf), s0s)))
        sa = sum(1 for x, y in ab if x > y and _set_done(x, y))
        sb = sum(1 for x, y in ab if y > x and _set_done(y, x))
        p1_sets, p2_sets = (sa, sb) if a1 else (sb, sa)
        last = sets[-1]
        finished = _set_done(max(last), min(last))       # a chart ending inside a set (a retirement) names no winner
        rec_win.append(None if (p1_sets == p2_sets or not finished) else p1_sets > p2_sets)
    R["x_sets_equal_stage0"] = s0_ok
    R["x_points_consistent"] = R["ok"]
    unknown = (R["p1_unknown"] + R["p2_unknown"] + R["p1_bad"] + R["p2_bad"]) > 0
    R["complete"] = R["ok"] & R["x_sets_equal_stage0"] & ~unknown
    w = pd.DataFrame({"source_key": R["chart"], "match_id": R["s0"], "a1": R["a1"], "complete": R["complete"],
                      "link_method": R["link_method"]})
    ovk = ov.set_index(["match_id", "player"])
    mcp_cols = {"serve_pts": "svpt", "aces": "ace", "dfs": "df", "first_in": "first_in", "first_won": "first_won",
                "second_won": "second_won", "bk_pts": "bp_faced", "bp_saved": "bp_saved"}
    for k, name in (("p1", "Player 1"), ("p2", "Player 2")):
        for f in ("svpt", "first_in", "first_won", "second_won", "ace", "df", "sv_won", "sv_gms", "bp_faced",
                  "bp_saved"):
            w[f"{k}_{f}"] = R[f"{k}_{f}"].astype("float64")
        for f in ("unknown", "penalty", "lets", "bad"):
            w[f"{k}_x_{f}_points" if f != "lets" else f"{k}_x_lets"] = R[f"{k}_{f}"]
        idx = pd.MultiIndex.from_arrays([R["chart"], R[name]])
        for src, f in mcp_cols.items():
            w[f"{k}_x_mcp_{f}"] = pd.to_numeric(ovk[src].reindex(idx), errors="coerce").to_numpy()
        w[f"{k}_x_src_name"] = R[name].to_numpy()
    w["p1_x_src_won"] = [np.nan if v is None else v for v in rec_win]
    w["p2_x_src_won"] = [np.nan if v is None else (not v) for v in rec_win]
    for c in ("x_points_consistent", "x_sets_equal_stage0"):
        w[c] = R[c].to_numpy()
    w["x_n_points"] = R["n_points"].to_numpy()
    w["x_date"] = R["Date"].astype(str).to_numpy()
    w["x_tournament"] = R["Tournament"].to_numpy()
    w["x_name_grade_same"], w["x_name_grade_swap"] = R["g_same"].to_numpy(), R["g_swap"].to_numpy()
    pe = ["x_unknown_points", "x_penalty_points", "x_lets", "x_bad_points"] + \
        [f"x_mcp_{f}" for f in mcp_cols.values()] + ["x_src_name", "x_src_won"]
    rc = T.to_contract(w, READER, FAMILY, "recount", player_extra=pe,
                       match_extra=["x_points_consistent", "x_sets_equal_stage0", "x_n_points", "x_date",
                                    "x_tournament", "x_name_grade_same", "x_name_grade_swap"])
    rc["x_src_won"] = rc["x_src_won"].astype("boolean")
    # this parser against MCP's own Overview totals (same strings): per count, all linked charts / complete ones
    parser = {}
    for sub, d in (("all", rc), ("complete", rc[rc["complete"]])):
        parser[sub] = {f: {"n": int((d[f].notna() & d[f"x_mcp_{f}"].notna()).sum()),
                           "equal_share": round(float((d[f] == d[f"x_mcp_{f}"])[d[f].notna() & d[f"x_mcp_{f}"].notna()]
                                                      .mean()), 5)}
                       for f in mcp_cols.values()}
    summary = {
        "inputs": rec, "records": stats,
        "dropped": {"charts_not_in_link_file": int(len(meta) - len(L)),
                    "linked_charts_without_points": int(len(L) - len(R)),
                    "orientation_unresolved": int(R["a1"].isna().sum())},
        "checks": {"recounted": int(len(R)), "points_consistent": int(R["ok"].sum()),
                   "sets_equal_stage0": int(sum(s0_ok)), "with_unknown_or_bad_points": int(unknown.sum()),
                   "complete": int(R["complete"].sum())},
        "parser_vs_mcp_overview": parser,
        "contract_checks": T.check_contract(rc),
        "winner_vs_stage0_complete": T.winner_check(rc[rc["complete"]]),
        "winner_vs_stage0_all": T.winner_check(rc),
        "definitions": __doc__.split("Every count is recounted")[1].split("Writes box")[0].strip(),
        "sanity_vs_stage0_complete_by_tour": T.records(T.sanity(rc[rc["complete"]], by=["tour"])),
        "hand_check": {"keys": T.sample_keys(rc, where=rc["complete"]), "status": "pending"},
    }
    T.write_reader(rc, READER, summary)
    T.log(f"done in {time.time() - t0:.0f}s")
    return 0


def _set_done(w: int, l: int) -> bool:
    return (w >= 6 and w - l >= 2) or (w == 7 and l == 6) or (w >= 7 and w - l >= 2) or (w == 1 and l == 0)


if __name__ == "__main__":
    sys.exit(main())
