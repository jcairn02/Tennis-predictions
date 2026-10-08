"""Adapters: each new point source turned into the common point table (src/eda/shot_level/points.py), plus this
study's extra columns, and a per-match table for linking.

Every adapter returns (points, matches[, extra]):

points      one row per point, in order, with the shot-level study's columns (source, key, seq, set_no, game_key,
            server, winner, serve_no, rally, end, ender, speed, place, net1, net2, ret_deep, wing) and
                t_utc       the point's time, seconds since 1970 UTC; NaN unknown
                is_tb       1 for a tie-break point (a match tie-break included), 0 otherwise, from the source's own
                            structure
                game_no     the game's number within its set (1-based), from the source's own structure
                server_src  the source's own server field where it is not per point (SofaScore and marcosjn2 give one
                            per game) or not kept as is: 1 / 2, 0 unknown. ``server`` is then derived (see below)
            set_no and game_key are the source's own labels (game_key: the game's order in the match, 0-based); the
            replay (replay.py) checks them against the rules. Players 1 and 2 are the source's (name1, name2).
matches     one row per match: source, key, tour (M/W), d (the date used for linking: the match's day where the
            source has it), year, name1, name2, round, draw (main/qual), level (data map codes where the source says),
            tname, slam, best_of_hint, src_winner (1/2 as the source says, 0 unknown), src_score (the source's own set
            scores, player 1 first, where it has them), src_status, n_points, has_time, plus source-specific fields.

Sources and how their fields map (observed in the files; see each function):

marcosjn2       Kaggle "tennis point-by-point match dataset 2015-2025" (marcosjn2, version 2 of 29 Aug 2025), a scrape
                of SofaScore: per game a string of point winners ('1' home, '0' away), a tie-break flag, the game
                winner and a server per game. 99.5% of tie-breaks carry one extra point appended after the tie-break's
                end, won by its winner (gap_sources/marcosjn2_links.py; the Slam logs show it is not played): it is
                dropped (only that exact pattern: one point, after the end, to the winner). The per-game server is
                right in regular games but not in tie-breaks (73% "away" in the first 20,000 ATP records), so the
                server is derived: the first server is the one under which the alternation of service games agrees
                best with the per-game field over regular games, then the rules (replay.rule_servers).
sofascore       The project's three SofaScore scrapes (data/dump/points/sofascore, sofascore_editions,
                sofascore_tournaments; singles; exhibitions and juniors left out). A game lists the score after each
                point except the last in a regular game, whose winner is the game's ``scoring``; a tie-break lists
                every state, the last included (src/ingest/point_sources/sofascore.py). Each listed point's winner
                comes from the score change (point_shot_sources/sofascore_codes.point_winner). ``serving`` is one per
                game and is not trusted as is (granular-data-leads "Side findings": ace-coded points won by the
                player marked receiving): the server is derived as for marcosjn2, the first server chosen by the
                alternation's agreement with ``serving`` over regular games. (The event's firstToServe is not used:
                it names the first game's server in about half of the records, no better than chance; and
                ``serving`` on a tie-break is the tie-break's first server in about half of them.)
                pointDescription 1 (ace) and 2 (double fault) are kept as end codes on the points they describe; the
                implied last point of a regular game has no code.
wta             The WTA API's umpire event logs (staged data/dump/points/wta/events/<year>.parquet; the documents'
                Attributes kept as JSON), read with official_point_feeds/verify_wta.event_points: points in log order
                with server, winner (from the score), ace / double fault, tie-break flag and millisecond time. Serve
                number: 2 when a first-serve fault was logged since the previous point (or for a double fault), else
                1; where the record's firstServe attribute is present (from 2021) it is used instead. Logs without
                attributes (April-May 2019, "bare") give no points. Records that are not points (medical and toilet
                breaks, violations, suspensions, challenges, lets, state changes) go to a separate table.
wta_pbp         The WTA API's point-by-point feed (staged data/dump/points/wta/points/<year>.parquet, 2022-2026):
                winners from the change of the game score (verify_wta.derived_winners; the feed's pointWinner is
                wrong after a lost advantage), server per point (blank on tie-break points: derived by the rules in
                the build), one-second times.
sackmann_pbp    Sackmann's tennis_pointbypoint strings (two GitHub snapshots, 2015 and 2018; men, ATP incl. Slams,
                Challenger and Futures): S / A the server won the point (A an ace), R / D the returner won it (D a
                double fault), ';' ends a game, '.' a set, '/' marks a change of server in a tie-break. server1 serves
                first; the server of each game follows the alternation, and in a tie-break each '/'-segment's. Both
                snapshots hold July 2011 - December 2015 and January - February 2017 (8 matches of 2010); 2016 is
                absent from both. Ace / double-fault letters are kept only where adf_flag is 1.
ausopen_mc      The Australian Open match centre (2026, and Wayback captures of earlier years), converted like the
                shot-level study's AO table but with every point: the feed writes a game's last point as a row of
                type 'game' / 'set' / 'match', which that table leaves out. Times per point (epoch seconds).
"""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.data_map import measure as M  # noqa: E402
from src.eda.point_sequence import common as C  # noqa: E402
from src.eda.point_sequence import replay as R  # noqa: E402

PCOLS = C.COLUMNS + C.EXTRA + ["server_src"]


def _frame(rows: dict, source: str) -> pd.DataFrame:
    """Point columns from arrays; missing schema columns get the shot-level schema's unknown values."""
    n = len(rows["key"])
    df = pd.DataFrame(rows)
    df["source"] = source
    fills = {"serve_no": 0, "rally": -1, "end": 0, "ender": 0, "place": 0, "net1": -1, "net2": -1, "ret_deep": -1,
             "wing": 0, "server_src": 0, "is_tb": 0, "game_no": 0}
    for c, v in fills.items():
        if c not in df:
            df[c] = v
    if "speed" not in df:
        df["speed"] = np.float32(np.nan)
    if "t_utc" not in df:
        df["t_utc"] = np.nan
    df["seq"] = df.groupby("key", sort=False).cumcount().astype("int32") if n else pd.Series(dtype="int32")
    for c in ("set_no", "server", "winner", "serve_no", "end", "ender", "place", "net1", "net2", "ret_deep", "wing",
              "server_src", "is_tb"):
        df[c] = df[c].astype("int8")
    df["game_key"] = df["game_key"].astype("int16")
    df["game_no"] = df["game_no"].astype("int16")
    df["rally"] = df["rally"].astype("int16")
    df["speed"] = df["speed"].astype("float32")
    df["t_utc"] = df["t_utc"].astype("float64")
    return df[PCOLS]


def derive_servers(gidx: np.ndarray, is_tb: np.ndarray, pt_in_game: np.ndarray, field: np.ndarray,
                   regular_game_field: np.ndarray, tie_first: int) -> tuple[np.ndarray, int, float]:
    """Servers of one match from its own game structure: the first server s0 is the one under which the alternation
    of service games agrees best with a per-game server field over regular games (ties: ``tie_first``, then 1); then
    the rules. Returns (servers, s0, agreement of the field with the alternation over regular games)."""
    reg = (regular_game_field == 1) | (regular_game_field == 2)
    if reg.any():
        alt1 = np.where(gidx[reg] % 2 == 0, 1, 2)
        a1 = float((alt1 == regular_game_field[reg]).mean())
        if a1 > 0.5:
            s0 = 1
        elif a1 < 0.5:
            s0 = 2
        else:
            s0 = tie_first if tie_first in (1, 2) else 1
        agree = a1 if s0 == 1 else 1.0 - a1
    else:
        s0, agree = (tie_first if tie_first in (1, 2) else 1), float("nan")
    return R.rule_servers(gidx, pt_in_game, is_tb, s0), s0, agree


# ------------------------------------------------------------------------------------------------
# marcosjn2 (Kaggle SofaScore scrape, 2015-2025)

def _marcosjn2_file(path: str) -> tuple[dict, list]:
    from src.eda.gap_sources.marcosjn2_links import _game
    P = {k: [] for k in ("key", "set_no", "game_key", "game_no", "is_tb", "winner", "server", "server_src")}
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            key = r["key"]
            tour = "M" if r["meta"]["gender"] == "M" else "W"
            rnd = (r.get("round") or {}).get("name") or ""
            tname = r["tournament"].get("name") or ""
            qual = bool(re.search(r"qualif", rnd, re.I) or re.search(r"qualif", tname, re.I))
            pts = r["tournament"].get("points")
            tier = "none" if pts is None else str(int(pts))
            seqs = (r.get("sequence") or {}).get("sets") or []
            gi = 0
            g_rows = []           # per point: (set, gkey, gno, tb, winner, field, pt_in_game)
            dropped = 0
            bad_chars = 0
            for si, s in enumerate(seqs, 1):
                for gn, g in enumerate(s.get("games") or [], 1):
                    ps = g.get("point_sequence") or ""
                    tb = bool(g.get("is_tiebreak"))
                    if tb:
                        state, _w, _h, _a, _t = _game(ps, True)
                        if state == "trailing":
                            ps = ps[:-1]
                            dropped += 1
                    side = g.get("server_side")
                    field = 1 if side == "home" else 2 if side == "away" else 0
                    for j, ch in enumerate(ps, 1):
                        w = 1 if ch == "1" else 2 if ch == "0" else 0
                        bad_chars += w == 0
                        g_rows.append((si, gi, gn, int(tb), w, field, j))
                    gi += 1
            if g_rows:
                arr = np.array(g_rows, dtype=np.int64)
                reg_field = np.where(arr[:, 3] == 0, arr[:, 5], 0)
                # agreement over regular games, one vote per game (the field is per game)
                first_pt = np.r_[True, arr[1:, 1] != arr[:-1, 1]]
                srv, s0, agree = derive_servers(arr[:, 1], arr[:, 3], arr[:, 6], arr[:, 5], np.where(first_pt, reg_field, 0),
                                                0)
                n = len(arr)
                P["key"] += [key] * n
                P["set_no"].append(arr[:, 0])
                P["game_key"].append(arr[:, 1])
                P["game_no"].append(arr[:, 2])
                P["is_tb"].append(arr[:, 3])
                P["winner"].append(arr[:, 4])
                P["server"].append(srv)
                P["server_src"].append(arr[:, 5])
                tb_games = arr[first_pt & (arr[:, 3] == 1)]
                tb_field_first = float(np.mean(tb_games[:, 5] == srv[first_pt & (arr[:, 3] == 1)])) if len(tb_games) else np.nan
            else:
                s0, agree, n, tb_field_first = 0, np.nan, 0, np.nan
            set_scores = []
            for s in seqs:
                gs = s.get("game_sequence") or ""
                set_scores.append(f"{gs.count('1')}-{gs.count('0')}")
            mw = str((r.get("sequence") or {}).get("match_winner"))
            rows.append({"source": "marcosjn2", "key": key, "event_id": r["meta"].get("event_id"), "tour": tour,
                         "d": r["meta"].get("date"), "tname": r["tournament"].get("unique_name") or tname,
                         "tname_full": tname, "tier": tier, "round_name": rnd, "round": M.canon_round(rnd),
                         "draw": "qual" if qual else "main", "name1": r["players"]["home"]["name"],
                         "name2": r["players"]["away"]["name"], "src_winner": 1 if mw == "1" else 2 if mw == "0" else 0,
                         "src_score": " ".join(set_scores), "n_points": n, "tb_trailing_dropped": dropped,
                         "bad_chars": bad_chars, "s0": s0, "server_field_agree": agree,
                         "tb_field_is_first_server": tb_field_first,
                         "ground": r["tournament"].get("ground_type")})
    for k in ("set_no", "game_key", "game_no", "is_tb", "winner", "server", "server_src"):
        P[k] = np.concatenate(P[k]) if P[k] else np.zeros(0, np.int64)
    return P, rows


def marcosjn2(workers: int = 2) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = C.RAW / "gap_sources" / "marcosjn2"
    paths = [str(base / "atp-matches.jsonl"), str(base / "wta-matches.jsonl")]
    with ProcessPoolExecutor(max_workers=min(workers, 2)) as ex:
        parts = list(ex.map(_marcosjn2_file, paths))
    P = {k: (sum((p[0][k] for p in parts), []) if k == "key" else np.concatenate([p[0][k] for p in parts]))
         for k in parts[0][0]}
    pts = _frame(P, "marcosjn2")
    m = pd.DataFrame([row for p in parts for row in p[1]])
    m["d"] = pd.to_datetime(m["d"], errors="coerce")
    m["year"] = m["d"].dt.year
    m["slam"] = np.where(m["tier"].eq("2000"), m["tname"].map(C.slam_of), None)
    m["level"] = np.where(m["tier"].eq("2000"), np.where(m["draw"].eq("qual"), "GSQ", "GS"), None)
    m["best_of_hint"] = np.where(m["tour"].eq("M") & m["tier"].eq("2000") & m["draw"].eq("main"), 5, 3)
    m["src_status"] = None
    m["has_time"] = False
    return pts, m


# ------------------------------------------------------------------------------------------------
# SofaScore (the project's three scrapes)

SOFA_DIRS = ["sofascore_editions", "sofascore_tournaments", "sofascore"]
SOFA_EVENT_COLS = ["event_id", "start_utc", "start_timestamp", "unique_tournament_name", "tournament_name",
                   "category_name", "round_name", "status_description", "status_type", "winner_code", "first_to_serve",
                   "home_name", "away_name", "doubles", "pbp_status", "season_year", "ground_type"] + \
                  [f"{s}_set{i}" for s in ("home", "away") for i in range(1, 6)] + \
                  [f"{s}_tb{i}" for s in ("home", "away") for i in range(1, 6)]
SOFA_POINT_COLS = ["event_id", "set", "game", "point", "home_point", "away_point", "point_description", "serving",
                   "scoring", "tiebreak", "set_index", "game_index"]
REGULAR = {"0": 0, "15": 1, "30": 2, "40": 3, "A": 4}


def _sofa_game(states: list, tiebreak: bool, scoring: int) -> tuple[list, list, str]:
    """Point winners (1 home, 2 away, 0 unknown) and description codes of one SofaScore game, and a note:
    'ok', 'implied' (a tie-break whose last state was missing and is implied by scoring), 'unended' (the states plus
    the implied point do not end the game)."""
    from src.eda.point_shot_sources.sofascore_codes import point_winner
    winners, codes = [], []
    prev = ("0", "0")
    for (h, a, desc) in states:
        cur = (str(h), str(a))
        w = point_winner(prev, cur, tiebreak)
        winners.append(w if w in (1, 2) else 0)
        codes.append(desc)
        prev = cur
    note = "ok"
    if not tiebreak:
        if scoring in (1, 2):
            winners.append(scoring)
            codes.append(0)
            ph, pa = REGULAR.get(prev[0]), REGULAR.get(prev[1])
            if ph is None or pa is None:
                note = "unended"
            else:
                if scoring == 1:
                    ok = (ph == 3 and pa <= 2) or (ph == 4 and pa == 3)
                else:
                    ok = (pa == 3 and ph <= 2) or (pa == 4 and ph == 3)
                note = "ok" if ok else "unended"
        else:
            note = "unended"
    else:
        try:
            h, a = int(prev[0]), int(prev[1])
        except ValueError:
            h = a = -1
        ended = max(h, a) >= 7 and abs(h - a) >= 2
        if not ended and scoring in (1, 2):
            h2, a2 = (h + 1, a) if scoring == 1 else (h, a + 1)
            if max(h2, a2) >= 7 and abs(h2 - a2) >= 2:
                winners.append(scoring)
                codes.append(0)
                note = "implied"
            else:
                note = "unended"
    return winners, codes, note


def sofascore() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    evs, pts = [], []
    for d in SOFA_DIRS:
        base = C.DUMP / "points" / d
        ecols = [c for c in SOFA_EVENT_COLS if c in pq.ParquetFile(base / "events.parquet").schema_arrow.names]
        e = pq.ParquetFile(base / "events.parquet").read(columns=ecols).to_pandas()
        e["scrape"] = d
        evs.append(e)
        p = pq.ParquetFile(base / "points.parquet").read(columns=SOFA_POINT_COLS).to_pandas()
        p["scrape"] = d
        pts.append(p)
    e = pd.concat(evs, ignore_index=True)
    p = pd.concat(pts, ignore_index=True)
    e = e[e["doubles"].astype(str).str.upper().ne("TRUE") & e["pbp_status"].astype(str).eq("200")]
    e = e[~e["category_name"].astype(str).isin(["Exhibition", "Juniors"])]
    # one record per event: the scrape with the most points
    npts = p.groupby(["scrape", "event_id"]).size().rename("n").reset_index()
    e = e.merge(npts, on=["scrape", "event_id"], how="inner")
    e = e.sort_values(["event_id", "n"], ascending=[True, False]).drop_duplicates("event_id")
    p = p.merge(e[["scrape", "event_id"]], on=["scrape", "event_id"], how="inner")
    for c in ("set_index", "game_index", "point", "point_description", "serving", "scoring"):
        p[c] = C.num(p[c]).fillna(0).astype("int64")
    p = p.sort_values(["event_id", "set_index", "game_index", "point"], kind="mergesort")
    # the event's firstToServe is recorded but not used: it names the first game's server in only about half of the
    # records (build_summary.json, sofascore audit), no better than a coin
    first = dict(zip(e["event_id"], C.num(e["first_to_serve"]).fillna(0).astype(int)))
    P = {k: [] for k in ("key", "set_no", "game_key", "game_no", "is_tb", "winner", "server", "server_src", "end",
                         "ender", "serve_no")}
    audit = {"games": 0, "games_unended": 0, "tiebreaks_last_point_implied": 0, "points_unknown_winner": 0,
             "regular_games_serving_vs_alternation_disagree": 0, "regular_games_with_serving": 0,
             "tb_games": 0, "tb_serving_is_tb_first_server": 0,
             "ace_coded": 0, "ace_won_by_server_field": 0, "ace_won_by_derived_server": 0,
             "df_coded": 0, "df_won_by_receiver_field": 0, "df_won_by_receiver_derived": 0,
             "matches": 0, "first_to_serve_present": 0, "first_to_serve_agrees_with_chosen": 0}
    mrows = []
    cols = ["event_id", "set_index", "game_index", "home_point", "away_point", "point_description", "serving",
            "scoring", "tiebreak"]
    arr = p[cols].to_numpy(dtype=object)
    ev_ids = arr[:, 0]
    bounds = np.flatnonzero(np.r_[True, ev_ids[1:] != ev_ids[:-1], True])
    for b0, b1 in zip(bounds[:-1], bounds[1:]):
        rows = arr[b0:b1]
        eid = rows[0, 0]
        audit["matches"] += 1
        gkeys = [(int(r[1]), int(r[2])) for r in rows]
        recs = []      # per point: set, gidx, gno, tb, winner, field, code, pt_in_game
        gi = -1
        last = None
        set_seen, gno = None, 0
        notes = []
        i = 0
        while i < len(rows):
            j = i
            while j < len(rows) and gkeys[j] == gkeys[i]:
                j += 1
            g = rows[i:j]
            gi += 1
            s_idx = gkeys[i][0]
            if s_idx != set_seen:
                set_seen, gno = s_idx, 0
            gno += 1
            tb = str(g[0, 8]).upper() == "TRUE"
            scoring = int(g[0, 7])
            serving = int(g[0, 6])
            states = [(x[3], x[4], int(x[5])) for x in g]
            wins, codes, note = _sofa_game(states, tb, scoring)
            notes.append(note)
            audit["games"] += 1
            audit["games_unended"] += note == "unended"
            audit["tiebreaks_last_point_implied"] += note == "implied"
            for k, (w, cd) in enumerate(zip(wins, codes), 1):
                recs.append((s_idx, gi, gno, int(tb), w, serving if serving in (1, 2) else 0, cd, k))
            i = j
        a = np.array(recs, dtype=np.int64)
        first_pt = np.r_[True, a[1:, 1] != a[:-1, 1]]
        reg_vote = np.where(first_pt & (a[:, 3] == 0), a[:, 5], 0)
        ft = first.get(eid, 0)
        srv, s0, agree = derive_servers(a[:, 1], a[:, 3], a[:, 7], a[:, 5], reg_vote, 0)
        audit["first_to_serve_present"] += ft in (1, 2)
        audit["first_to_serve_agrees_with_chosen"] += ft == s0
        # audit of the server fix: the field against the alternation, and the codes against both
        alt = np.where(a[:, 1] % 2 == 0, s0, 3 - s0)
        regg = first_pt & (a[:, 3] == 0) & np.isin(a[:, 5], [1, 2])
        audit["regular_games_with_serving"] += int(regg.sum())
        audit["regular_games_serving_vs_alternation_disagree"] += int((a[regg, 5] != alt[regg]).sum())
        tbg = first_pt & (a[:, 3] == 1) & np.isin(a[:, 5], [1, 2])
        audit["tb_games"] += int(tbg.sum())
        audit["tb_serving_is_tb_first_server"] += int((a[tbg, 5] == alt[tbg]).sum())
        win = a[:, 4]
        ace, dfc = a[:, 6] == 1, a[:, 6] == 2
        known = win > 0
        # in the regular games whose field breaks the alternation, whose serve do the ace and double-fault codes fit?
        bad_games = a[regg & (a[:, 5] != alt), 1]
        inb = np.isin(a[:, 1], bad_games) & (a[:, 3] == 0) & known
        audit["field_breaks_alternation_codes"] = audit.get("field_breaks_alternation_codes", 0) + int((inb & (ace | dfc)).sum())
        audit["field_breaks_alternation_codes_fit_field"] = audit.get("field_breaks_alternation_codes_fit_field", 0) + \
            int((inb & ((ace & (win == a[:, 5])) | (dfc & (win != a[:, 5])))).sum())
        audit["field_breaks_alternation_codes_fit_derived"] = audit.get("field_breaks_alternation_codes_fit_derived", 0) + \
            int((inb & ((ace & (win == srv)) | (dfc & (win != srv)))).sum())
        audit["ace_coded"] += int((ace & known).sum())
        audit["ace_won_by_server_field"] += int((ace & known & (win == a[:, 5])).sum())
        audit["ace_won_by_derived_server"] += int((ace & known & (win == srv)).sum())
        audit["df_coded"] += int((dfc & known).sum())
        audit["df_won_by_receiver_field"] += int((dfc & known & (a[:, 5] > 0) & (win != a[:, 5])).sum())
        audit["df_won_by_receiver_derived"] += int((dfc & known & (win != srv)).sum())
        audit["points_unknown_winner"] += int((~known).sum())
        n = len(a)
        P["key"] += [str(eid)] * n
        P["set_no"].append(a[:, 0])
        P["game_key"].append(a[:, 1])
        P["game_no"].append(a[:, 2])
        P["is_tb"].append(a[:, 3])
        P["winner"].append(a[:, 4])
        P["server"].append(srv)
        P["server_src"].append(a[:, 5])
        end = np.where(ace, C.END["ace"], np.where(dfc, C.END["df"], 0))
        P["end"].append(end)
        P["ender"].append(np.where(end > 0, srv, 0))
        P["serve_no"].append(np.where(dfc, 2, 0))
        mrows.append({"key": str(eid), "n_points": n, "s0": s0, "server_field_agree": agree,
                      "games_unended": notes.count("unended"), "tb_implied": notes.count("implied")})
    for k in P:
        if k != "key":
            P[k] = np.concatenate(P[k]) if P[k] else np.zeros(0, np.int64)
    pts = _frame(P, "sofascore")
    m = e.copy()
    m["key"] = m["event_id"].astype(str)
    m = m.merge(pd.DataFrame(mrows), on="key", how="inner")
    cat = m["category_name"].astype(str)
    utn = m["unique_tournament_name"].astype(str)
    women = cat.str.contains("WTA|Women", regex=True) | utn.str.contains("Women", regex=False)
    m["tour"] = np.where(women, "W", "M")
    m["d"] = pd.to_datetime(m["start_utc"], errors="coerce")
    m["year"] = m["d"].dt.year
    qual = m["round_name"].astype(str).str.contains("qualif", case=False) | \
        m["tournament_name"].astype(str).str.contains("qualif", case=False)
    m["draw"] = np.where(qual, "qual", "main")
    m["slam"] = [C.slam_of(u) if re.search(r"open|wimbledon|roland|garros", str(u), re.I) and
                 str(c) in ("ATP", "WTA") else None for u, c in zip(utn, cat)]
    m["level"] = np.where(pd.notna(m["slam"]) & m["slam"].astype(object).ne(None),
                          np.where(qual, "GSQ", "GS"), None)
    m.loc[m["slam"].isna(), "level"] = None
    m["round"] = m["round_name"].map(M.canon_round)
    m["name1"], m["name2"] = m["home_name"], m["away_name"]
    m["tname"] = m["unique_tournament_name"]
    m["src_winner"] = C.num(m["winner_code"]).fillna(0).astype(int).where(lambda s: s.isin([1, 2]), 0)
    sets = []
    for _, r in m.iterrows():
        out = []
        for i in range(1, 6):
            h, a = r.get(f"home_set{i}"), r.get(f"away_set{i}")
            if pd.isna(h) or pd.isna(a) or str(h) == "" or str(a) == "":
                continue
            s = f"{h}-{a}"
            th, ta = r.get(f"home_tb{i}"), r.get(f"away_tb{i}")
            if pd.notna(th) and pd.notna(ta) and str(th) != "" and str(ta) != "":
                s += f"({min(int(th), int(ta))})"
            out.append(s)
        sets.append(" ".join(out))
    m["src_score"] = sets
    m["src_status"] = m["status_description"]
    m["best_of_hint"] = np.where(m["tour"].eq("M") & m["level"].eq("GS"), 5, 3)
    m["has_time"] = False
    m["source"] = "sofascore"
    keep = ["source", "key", "event_id", "scrape", "tour", "d", "year", "tname", "category_name", "round_name", "round",
            "draw", "level", "slam", "name1", "name2", "src_winner", "src_score", "src_status", "first_to_serve", "s0",
            "server_field_agree", "games_unended", "tb_implied", "n_points", "best_of_hint", "has_time", "start_utc",
            "ground_type"]
    return pts, m[keep].reset_index(drop=True), audit


# ------------------------------------------------------------------------------------------------
# WTA API: the umpire's event log and the point-by-point feed

WTA = C.DUMP / "points" / "wta"
WTA_EVENT_COLS = ["tournament_id", "match_id", "index", "name", "type", "reason", "player", "first_serve", "server",
                  "receiver", "score", "set", "game", "timestamp", "attributes"]
WTA_MATCH_COLS = ["tournament_id", "match_id", "tier", "draw", "walkover", "RoundID", "MatchState", "ResultString",
                  "ScoreString", "Winner", "MatchTimeStamp", "MatchTimeTotal", "PlayerIDA", "PlayerNameFirstA",
                  "PlayerNameLastA", "PlayerIDB", "PlayerNameFirstB", "PlayerNameLastB", "events_status",
                  "point_by_point_status"] + [f"ScoreSet{i}{s}" for i in range(1, 6) for s in "AB"] + \
                 [f"ScoreTbSet{i}" for i in range(1, 5)]
WTA_TIER_LEVEL = {"1000": "T1000", "500": "T500", "250": "T250", "125": "CH", "finals": "FIN", "slam": "GS"}
WINNER_CODES = {"2": (1, "played"), "3": (2, "played"), "4": (1, "retired"), "5": (2, "retired"),
                "6": (1, "walkover"), "7": (2, "walkover")}


def _wta_round(rid, draw: str, size) -> str | None:
    r = str(rid or "").strip().upper()
    if draw == "qual":
        return {"1": "Q1", "2": "Q2", "3": "Q3", "4": "Q4"}.get(r)
    if r in ("Q", "S", "F"):
        return {"Q": "QF", "S": "SF", "F": "F"}[r]
    if r.isdigit() and int(r) >= 1:
        try:
            n = int(float(size))
        except (TypeError, ValueError):
            return None
        top = 1 << int(np.ceil(np.log2(max(n, 2))))       # 28 -> 32, 56 -> 64, 96 -> 128
        field = top >> (int(r) - 1)
        return {128: "R128", 64: "R64", 32: "R32", 16: "R16", 8: "QF", 4: "SF", 2: "F"}.get(field)
    return None


def _wta_matches(year: int) -> pd.DataFrame:
    f = pq.ParquetFile(WTA / "matches" / f"{year}.parquet")
    cols = [c for c in WTA_MATCH_COLS if c in f.schema_arrow.names]
    m = f.read(columns=cols).to_pandas()
    m = m[m["draw"].isin(["main_singles", "qual_singles"])].copy()
    m["year"] = year
    return m


def _int(v, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _iso_seconds(ts: pd.Series) -> np.ndarray:
    t = pd.to_datetime(ts, errors="coerce", utc=True, format="mixed")
    return ((t - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds()).to_numpy(dtype="float64")


def _wta_year(year: int) -> tuple[dict, list, list]:
    """Points, match rows and non-point records of one year's singles event logs."""
    from src.eda.official_point_feeds import verify_wta as V
    m = _wta_matches(year)
    teams = {(r.tournament_id, r.match_id): {str(r.PlayerIDA): "A", str(r.PlayerIDB): "B"}
             for r in m.itertuples(index=False)}
    f = pq.ParquetFile(WTA / "events" / f"{year}.parquet")
    ev = f.read(columns=WTA_EVENT_COLS).to_pandas()
    ev = ev[ev["match_id"].astype(str).str.match(r"^(LS|RS)")]
    ev["idx"] = C.num(ev["index"]).fillna(-1).astype("int64")
    ev = ev.sort_values(["tournament_id", "match_id", "idx"], kind="mergesort").reset_index(drop=True)
    P = {k: [] for k in ("key", "set_no", "game_key", "game_no", "is_tb", "winner", "server", "end", "ender",
                         "serve_no", "t_str")}
    mrows, others = [], []
    keys = (ev["tournament_id"].astype(str) + "|" + ev["match_id"].astype(str)).to_numpy()
    bounds = np.flatnonzero(np.r_[True, keys[1:] != keys[:-1], True])
    names = ev["name"].to_numpy(dtype=object)
    attrs_s = ev["attributes"].to_numpy(dtype=object)
    # the attributes event_points reads, from the staged columns (the same values as the Attributes JSON, which is
    # kept verbatim in the non-point table); an empty Attributes object stays empty (the bare logs of 2019)
    a_type, a_reason = ev["type"].to_numpy(dtype=object), ev["reason"].to_numpy(dtype=object)
    a_first = ev["first_serve"].map({"TRUE": True, "FALSE": False}).to_numpy(dtype=object)
    a_score, a_server = ev["score"].to_numpy(dtype=object), ev["server"].to_numpy(dtype=object)
    idxs = ev["idx"].to_numpy()
    sets_ = ev["set"].to_numpy(dtype=object)
    games_ = ev["game"].to_numpy(dtype=object)
    stamps = ev["timestamp"].to_numpy(dtype=object)
    tids, mids = ev["tournament_id"].to_numpy(dtype=object), ev["match_id"].to_numpy(dtype=object)

    def present(v):
        return v is not None and not (isinstance(v, float) and np.isnan(v))

    for b0, b1 in zip(bounds[:-1], bounds[1:]):
        tid, mid = tids[b0], mids[b0]
        key = f"{tid}/{year}/{mid}"
        tm = teams.get((tid, mid))
        recs = []
        for i in range(b0, b1):
            a = attrs_s[i]
            if not isinstance(a, str) or a in ("", "{}", "null"):
                at = {}
            else:
                at = {k: v for k, v in (("type", a_type[i]), ("reason", a_reason[i]), ("firstServe", a_first[i]),
                                        ("score", a_score[i]), ("server", a_server[i])) if present(v)}
            recs.append({"Index": int(idxs[i]), "Name": names[i], "Attributes": at, "Set": sets_[i],
                         "Game": games_[i], "Timestamp": stamps[i]})
        row = {"key": key, "tournament_id": tid, "match_id": mid, "year": year, "records": len(recs)}
        if tm is None:
            row["log"] = "not_listed"
            mrows.append(row)
            continue
        if V.is_bare_log(recs):
            row["log"] = "bare"
            mrows.append(row)
            continue
        pts, games = V.event_points({"Events": recs}, tm)
        row["log"] = "full" if pts else "empty"
        # a finished tie-break whose final score is written (its scores before it may be the unwritten "0-0") was won
        # on its last point by its winner: that point's winner is filled; the others stay unknown
        last_of = {}
        for k, q in enumerate(pts):
            last_of[q["game_seq"]] = k
        tb_filled = 0
        for gseq, gm in enumerate(games, 1):
            k = last_of.get(gseq)
            if gm["tiebreak"] and gm["finished"] and gm["winner"] in ("A", "B") and k is not None \
                    and pts[k]["winner"] is None:
                pts[k]["winner"] = gm["winner"]
                tb_filled += 1
        row["tb_last_point_filled"] = tb_filled
        # serve number: a first-serve fault since the previous point-ending record, or the record's own attribute
        fault_since, sn_by_index = False, {}
        attr_by_index = {}
        for rec in recs:
            nm = V.kind(rec)
            at = rec["Attributes"] or {}
            if nm == "Fault" and at.get("firstServe") is True:
                fault_since = True
            elif nm in ("Point", "Ace") or (nm == "Fault" and at.get("firstServe") is not True):
                sn_by_index[rec["Index"]] = 2 if (fault_since or nm == "Fault") else 1
                attr_by_index[rec["Index"]] = at.get("firstServe")
                fault_since = False
        n = len(pts)
        sn_attr_agree = sn_attr_n = 0
        point_index = []
        for k, q in enumerate(pts):
            g = q["game_seq"] - 1
            P["key"].append(key)
            P["game_key"].append(g)
            P["is_tb"].append(1 if q["tiebreak"] else 0)
            P["winner"].append(1 if q["winner"] == "A" else 2 if q["winner"] == "B" else 0)
            s = 1 if q["server"] == "A" else 2 if q["server"] == "B" else 0
            P["server"].append(s)
            e = C.END["ace"] if q["kind"] == "ace" else C.END["df"] if q["kind"] == "double_fault" else 0
            P["end"].append(e)
            P["ender"].append(s if e else 0)
            sn = sn_by_index.get(q["index"], 0)
            fa = attr_by_index.get(q["index"])
            if q["kind"] == "double_fault":
                sn = 2
            elif fa is True or fa is False:
                sn_attr_n += 1
                sn_attr_agree += (2 if fa is False else 1) == sn
                sn = 1 if fa is True else 2
            P["serve_no"].append(sn)
            P["t_str"].append(q["timestamp"])
            point_index.append(q["index"])
        # the set and game labels of each game: those of its first record (a game-ending record can carry the next
        # game's numbers, verify_wta's notes)
        if n:
            gk = P["game_key"][-n:]
            first_rec = {}
            for k, q in enumerate(pts):
                first_rec.setdefault(q["game_seq"] - 1, (_int(q["set"]), _int(q["game"])))
            P["set_no"] += [first_rec[g][0] for g in gk]
            P["game_no"] += [first_rec[g][1] for g in gk]
        row.update({"n_points": n, "games": len(games), "unknown_winners": sum(1 for q in pts if q["winner"] is None),
                    "serve_no_attr_points": sn_attr_n, "serve_no_attr_agree": sn_attr_agree,
                    "tiebreak_orientations": ";".join(sorted({q["tiebreak_orientation"] for q in pts
                                                             if q["tiebreak_orientation"]})) or None})
        mrows.append(row)
        # records that are not points
        pidx = np.array(point_index, dtype=np.int64)
        for i in range(b0, b1):
            nm = names[i]
            if nm in ("Point", "Ace", "Fault"):
                continue
            others.append((key, int(idxs[i]), int(np.searchsorted(pidx, idxs[i])) if n else 0, i))
    # non-point records as rows of the events frame
    oth = ev.loc[[o[3] for o in others], ["index", "name", "type", "reason", "player", "server", "receiver", "score",
                                          "set", "game", "timestamp", "attributes"]].copy() if others else \
        pd.DataFrame(columns=["index", "name", "type", "reason", "player", "server", "receiver", "score", "set", "game",
                              "timestamp", "attributes"])
    oth.insert(0, "key", [o[0] for o in others])
    oth["next_point_seq"] = [o[2] for o in others]
    return P, mrows, oth


def wta(workers: int = 6) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    years = sorted(int(p.stem) for p in (WTA / "events").glob("*.parquet"))
    with ProcessPoolExecutor(max_workers=min(workers, len(years))) as ex:
        parts = list(ex.map(_wta_year, years))
    P = {k: sum((p[0][k] for p in parts), []) for k in parts[0][0]}
    t_str = P.pop("t_str")
    P = {k: (v if k == "key" else np.asarray(v, dtype=np.int64)) for k, v in P.items()}
    P["t_utc"] = _iso_seconds(pd.Series(t_str, dtype=object))
    pts = _frame(P, "wta")
    logs = pd.DataFrame([r for p in parts for r in p[1]])
    events = pd.concat([p[2] for p in parts], ignore_index=True)
    events["t_utc"] = _iso_seconds(events["timestamp"])
    m = _wta_match_table(sorted({int(y) for y in years}))
    m = m.merge(logs.drop(columns=["tournament_id", "match_id", "year"]), on="key", how="inner")
    m["source"] = "wta"
    m["has_time"] = True
    return pts, m, events


def _wta_match_table(years: list[int]) -> pd.DataFrame:
    ed = pq.ParquetFile(WTA / "editions.parquet").read(columns=["tournament_id", "year", "title", "start_date",
                                                                 "singles_draw_size", "surface"]).to_pandas()
    ed["year"] = C.num(ed["year"]).astype("Int64")
    ed = ed.drop_duplicates(["tournament_id", "year"])
    frames = []
    for y in years:
        m = _wta_matches(y)
        frames.append(m)
    m = pd.concat(frames, ignore_index=True)
    m["year"] = m["year"].astype("Int64")
    m = m.merge(ed, on=["tournament_id", "year"], how="left")
    m["key"] = m["tournament_id"].astype(str) + "/" + m["year"].astype(str) + "/" + m["match_id"].astype(str)
    m["draw"] = np.where(m["draw"].eq("qual_singles"), "qual", "main")
    m["tour"] = "W"
    ts = pd.to_datetime(m["MatchTimeStamp"], errors="coerce", utc=True, format="mixed").dt.tz_localize(None)
    m["d"] = ts.fillna(pd.to_datetime(m["start_date"], errors="coerce"))
    m["name1"] = m["PlayerNameFirstA"].fillna("") + " " + m["PlayerNameLastA"].fillna("")
    m["name2"] = m["PlayerNameFirstB"].fillna("") + " " + m["PlayerNameLastB"].fillna("")
    m["round"] = [_wta_round(r, d, s) for r, d, s in zip(m["RoundID"], m["draw"], m["singles_draw_size"])]
    lv = m["tier"].map(WTA_TIER_LEVEL)
    qual_of = {"GS": "GSQ", "T1000": "TQ", "T500": "TQ", "T250": "TQ", "FIN": "TQ", "CH": "CHQ"}
    m["level"] = np.where(m["draw"].eq("qual"), lv.map(qual_of), lv)
    m["tname"] = m["title"]
    m["slam"] = np.where(m["tier"].eq("slam"), m["title"].map(C.slam_of), None)
    wc = m["Winner"].astype(str).map(lambda x: WINNER_CODES.get(x, (0, None)))
    m["src_winner"] = [w for w, _ in wc]
    m["src_status"] = [h for _, h in wc]
    sc = []
    for r in m.itertuples(index=False):
        out = []
        for i in range(1, 6):
            a, b = getattr(r, f"ScoreSet{i}A", None), getattr(r, f"ScoreSet{i}B", None)
            if a in (None, "") and b in (None, ""):
                continue
            s = f"{a}-{b}"
            tb = getattr(r, f"ScoreTbSet{i}", None) if i <= 4 else None
            if tb not in (None, "") and str(tb).isdigit():
                s += f"({tb})"
            out.append(s)
        sc.append(" ".join(out))
    m["src_score"] = sc
    m["best_of_hint"] = 3
    keep = ["key", "tournament_id", "year", "match_id", "tour", "d", "tname", "tier", "level", "slam", "draw", "round",
            "RoundID", "name1", "name2", "PlayerIDA", "PlayerIDB", "src_winner", "src_status", "src_score",
            "ResultString", "MatchTimeStamp", "MatchTimeTotal", "best_of_hint", "events_status",
            "point_by_point_status", "walkover"]
    return m[keep]


def _wta_pbp_year(year: int) -> tuple[dict, list]:
    from src.eda.official_point_feeds import verify_wta as V
    path = WTA / "points" / f"{year}.parquet"
    f = pq.ParquetFile(path)
    if f.metadata.num_rows == 0:
        return {k: [] for k in ("key", "set_no", "game_key", "game_no", "is_tb", "winner", "server", "t_str")}, []
    p = f.read(columns=["tournament_id", "match_id", "point_number", "set", "game", "server", "point_winner",
                        "game_score_a", "game_score_b", "timestamp", "match_status"]).to_pandas()
    p = p[p["match_id"].astype(str).str.match(r"^(LS|RS)")].copy()
    p["pn"] = C.num(p["point_number"]).fillna(0).astype("int64")
    p = p.sort_values(["tournament_id", "match_id", "pn"], kind="mergesort").reset_index(drop=True)
    P = {k: [] for k in ("key", "set_no", "game_key", "game_no", "is_tb", "winner", "server", "t_str")}
    rows = []
    keys = (p["tournament_id"].astype(str) + "|" + p["match_id"].astype(str)).to_numpy()
    bounds = np.flatnonzero(np.r_[True, keys[1:] != keys[:-1], True])
    recs_all = p[["set", "game", "game_score_a", "game_score_b", "server", "timestamp", "point_winner"]].to_dict("records")
    tids, mids = p["tournament_id"].to_numpy(dtype=object), p["match_id"].to_numpy(dtype=object)
    for b0, b1 in zip(bounds[:-1], bounds[1:]):
        recs = recs_all[b0:b1]
        key = f"{tids[b0]}/{year}/{mids[b0]}"
        wins = V.derived_winners(recs)
        labels = [(r["set"], r["game"]) for r in recs]
        gk, prev = -1, None
        # a tie-break game: a score outside the regular ladder (numbers other than 0/15/30/40, or none of 'A'/'G')
        tb_games = set()
        for r in recs:
            for v in (r["game_score_a"], r["game_score_b"]):
                s = str(v or "").strip().upper()
                if s.isdigit() and s not in ("0", "15", "30", "40"):
                    tb_games.add((r["set"], r["game"]))
        for r, w, lab in zip(recs, wins, labels):
            if lab != prev:
                gk += 1
                prev = lab
            P["key"].append(key)
            P["set_no"].append(_int(r["set"]))
            P["game_no"].append(_int(r["game"]))
            P["game_key"].append(gk)
            P["is_tb"].append(1 if lab in tb_games else 0)
            P["winner"].append(1 if w == "A" else 2 if w == "B" else 0)
            sv = str(r["server"] or "").strip().upper()
            P["server"].append(1 if sv == "A" else 2 if sv == "B" else 0)
            P["t_str"].append(r["timestamp"])
        rows.append({"key": key, "n_points": b1 - b0, "unknown_winners": sum(1 for w in wins if w is None),
                     "point_winner_field_disagrees": sum(1 for r, w in zip(recs, wins)
                                                         if w and str(r["point_winner"] or "") != w)})
    return P, rows


def wta_pbp(workers: int = 6) -> tuple[pd.DataFrame, pd.DataFrame]:
    years = sorted(int(p.stem) for p in (WTA / "points").glob("*.parquet"))
    with ProcessPoolExecutor(max_workers=min(workers, len(years))) as ex:
        parts = list(ex.map(_wta_pbp_year, years))
    P = {k: sum((p[0][k] for p in parts), []) for k in parts[0][0]}
    t_str = P.pop("t_str")
    P = {k: (v if k == "key" else np.asarray(v, dtype=np.int64)) for k, v in P.items()}
    P["t_utc"] = _iso_seconds(pd.Series(t_str, dtype=object))
    pts = _frame(P, "wta_pbp")
    info = pd.DataFrame([r for p in parts for r in p[1]])
    m = _wta_match_table(years).merge(info, on="key", how="inner")
    m["source"] = "wta_pbp"
    m["has_time"] = True
    return pts, m


# ------------------------------------------------------------------------------------------------
# Australian Open match centre (2026 and Wayback captures), with every point

def ausopen_mc() -> tuple[pd.DataFrame, pd.DataFrame]:
    """The AO match centre's points, the shot-level study's conventions (src/eda/shot_level/points.ausopen) but with
    every point: the feed writes a game's last point as a row of type 'game' ('set', 'match' when it also ends the set
    or the match), which the shot-level table leaves out (it keeps type 'point' only, so each game there lacks its
    last point). winner and point_server_team 1/2; outcome ace / double_fault / winner / forced_error /
    unforced_error / service_winner with subject_team; stroke_side; timestamp (epoch seconds) per point."""
    base = C.DUMP / "points" / "ausopen"
    m = pd.read_parquet(base / "matches.parquet")
    m = m[m["event"].isin(["MS", "WS", "MQ", "WQ"])].copy()
    p = pd.read_parquet(base / "points.parquet",
                        columns=["record_key", "seq", "set", "game", "point", "tiebreak", "type", "winner", "outcome",
                                 "subject_team", "stroke_side", "point_server_team", "timestamp"])
    p = p[p["type"].isin(["point", "game", "set", "match"]) & p["record_key"].isin(set(m["record_key"]))].copy()
    p["_o"] = C.num(p["seq"])
    p = p.sort_values(["record_key", "_o"], kind="mergesort").reset_index(drop=True)
    oc = p["outcome"].astype(str)
    svc = oc.eq("service_winner").to_numpy()
    end = np.select([oc.eq("ace"), oc.eq("double_fault"), oc.eq("winner"), oc.eq("forced_error"),
                     oc.eq("unforced_error"), oc.eq("service_winner")],
                    [C.END["ace"], C.END["df"], C.END["winner"], C.END["forced"], C.END["unforced"], C.END["forced"]], 0)
    srv = C.num(p["point_server_team"]).fillna(0).astype(int).to_numpy()
    subj = C.num(p["subject_team"]).fillna(0).astype(int).to_numpy()
    lab = p["record_key"].astype(str) + "|" + p["set"].astype(str) + "|" + p["game"].astype(str)
    new = (lab != lab.shift()) | (p["record_key"] != p["record_key"].shift())
    gk = new.astype(int).groupby(p["record_key"]).cumsum() - 1
    ss = p["stroke_side"].astype(str)
    P = {"key": p["record_key"].astype(str).tolist(), "set_no": C.num(p["set"]).fillna(0).astype(int).to_numpy(),
         "game_key": gk.to_numpy(), "game_no": C.num(p["game"]).fillna(0).astype(int).to_numpy(),
         "is_tb": p["tiebreak"].astype(str).str.upper().eq("TRUE").astype(int).to_numpy(),
         "server": srv, "winner": C.num(p["winner"]).fillna(0).astype(int).to_numpy(), "end": end,
         "ender": np.where(svc, 3 - srv, np.where(end > 0, subj, 0)),
         "rally": np.select([end == C.END["df"], end == C.END["ace"], svc], [0, 1, 2], -1),
         "serve_no": np.where(end == C.END["df"], 2, 0),
         "wing": np.where(np.isin(end, [C.END["winner"], C.END["forced"], C.END["unforced"]]),
                          np.select([ss.eq("forehand"), ss.eq("backhand")], [1, 2], 0), 0),
         "t_utc": C.num(p["timestamp"]).to_numpy(dtype="float64")}
    pts = _frame(P, "ausopen_mc")
    n = pts.groupby("key").size()
    qual = m["event"].isin(["MQ", "WQ"])
    out = pd.DataFrame({"source": "ausopen_mc", "key": m["record_key"].astype(str),
                        "tour": np.where(m["event"].isin(["MS", "MQ"]), "M", "W"),
                        "d": pd.to_datetime(m["date"], errors="coerce", utc=True, format="mixed").dt.tz_localize(None),
                        "tname": "Australian Open", "round_name": m["round_name"],
                        "round": [M.slam_round(c, q) for c, q in zip(m["round_name"], qual)],
                        "draw": np.where(qual, "qual", "main"), "level": np.where(qual, "GSQ", "GS"), "slam": "AO",
                        "name1": m["team1_names"], "name2": m["team2_names"],
                        "src_winner": C.num(m["winner_team"]).fillna(0).astype(int).where(lambda s: s.isin([1, 2]), 0),
                        "src_score": m["team1_score"].astype(str) + " / " + m["team2_score"].astype(str),
                        "src_status": m["match_status_name"], "route": m["route"],
                        "best_of_hint": np.where(m["event"].eq("MS"), 5, 3), "has_time": True})
    out["year"] = out["d"].dt.year
    out["n_points"] = out["key"].map(n).fillna(0).astype(int)
    return pts, out.reset_index(drop=True)


# ------------------------------------------------------------------------------------------------
# Sackmann's point strings (tennis_pointbypoint, two snapshots)

def parse_pbp_string(pbp: str) -> tuple[list, str]:
    """Points of one Sackmann string: (set_no, game_idx, game_no, is_tb, pt_in_game, server, winner, end), with the
    players as server1 = 1 and server2 = 2, and a note ('ok' or what was odd)."""
    out = []
    note = "ok"
    gi = 0
    sets = pbp.strip().strip(".").split(".")
    for si, sset in enumerate(sets, 1):
        games = [g for g in sset.split(";")]
        for gn, game in enumerate(games, 1):
            if game == "":
                note = "empty_game"
                continue
            first = 1 if gi % 2 == 0 else 2
            tb = "/" in game
            segs = game.split("/") if tb else [game]
            k = 0
            for sg, seg in enumerate(segs):
                srv = first if sg % 2 == 0 else 3 - first
                if tb and ((sg == 0 and len(seg) != 1) or (0 < sg < len(segs) - 1 and len(seg) != 2)):
                    note = "tb_segment_length"
                for ch in seg:
                    k += 1
                    if ch in "SA":
                        w = srv
                    elif ch in "RD":
                        w = 3 - srv
                    else:
                        w = 0
                        note = "bad_char"
                    end = C.END["ace"] if ch == "A" else C.END["df"] if ch == "D" else 0
                    out.append((si, gi, gn, int(tb), k, srv, w, end))
            gi += 1
    return out, note


def sackmann_pbp() -> tuple[pd.DataFrame, pd.DataFrame]:
    base = C.RAW / "point_shot_sources"
    frames = []
    for copy in ("pbp_copy_2018", "pbp_copy_2015"):
        for f in sorted((base / copy).glob("pbp_matches_*.csv")):
            d = pd.read_csv(f, dtype=str, keep_default_na=False)
            if d.empty:
                continue
            d["copy"] = copy
            d["file"] = f.name
            d["row"] = np.arange(len(d))
            frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    d["key"] = np.where(d["copy"].eq("pbp_copy_2018"), "c18_" + d["pbp_id"].fillna("").astype(str),
                        "c15_" + d["file"].str.replace(".csv", "", regex=False) + "_" + d["row"].astype(str))
    d["d"] = pd.to_datetime(d["date"], format="%d %b %y", errors="coerce")
    # the 2018 snapshot first; a 2015-snapshot row is kept only when no 2018 row has the same day, players and points
    d["sig"] = d["date"] + "|" + d["server1"] + "|" + d["server2"] + "|" + d["pbp"]
    d = d.sort_values(["copy"], ascending=False, kind="mergesort")      # 2018 before 2015
    n0 = len(d)
    d = d.drop_duplicates("key").drop_duplicates("sig")
    P = {k: [] for k in ("key", "set_no", "game_key", "game_no", "is_tb", "winner", "server", "end", "ender")}
    notes, npts = [], []
    for key, s in zip(d["key"], d["pbp"]):
        pts, note = parse_pbp_string(str(s))
        notes.append(note)
        npts.append(len(pts))
        if not pts:
            continue
        a = np.array(pts, dtype=np.int64)
        P["key"] += [key] * len(a)
        P["set_no"].append(a[:, 0])
        P["game_key"].append(a[:, 1])
        P["game_no"].append(a[:, 2])
        P["is_tb"].append(a[:, 3])
        P["server"].append(a[:, 5])
        P["winner"].append(a[:, 6])
        P["end"].append(a[:, 7])
        P["ender"].append(np.where(a[:, 7] > 0, a[:, 5], 0))
    for k in P:
        if k != "key":
            P[k] = np.concatenate(P[k])
    pts = _frame(P, "sackmann_pbp")
    # aces and double faults are marked only where adf_flag is 1; elsewhere the codes stay unknown
    adf = dict(zip(d["key"], d["adf_flag"].astype(str)))
    pts.loc[pts["key"].map(adf).ne("1") & pts["end"].gt(0), ["end", "ender"]] = 0
    pts.loc[pts["end"].eq(C.END["df"]), "serve_no"] = 2
    m = pd.DataFrame({"source": "sackmann_pbp", "key": d["key"].to_numpy(), "copy": d["copy"].to_numpy(),
                      "file": d["file"].to_numpy(), "pbp_id": d["pbp_id"].fillna("").to_numpy(), "tour": "M",
                      "d": d["d"].to_numpy(), "tname": d["tny_name"].to_numpy(), "src_tour": d["tour"].to_numpy(),
                      "draw": np.where(d["draw"].str.lower().eq("qual"), "qual", "main"),
                      "name1": d["server1"].to_numpy(), "name2": d["server2"].to_numpy(),
                      "src_winner": C.num(d["winner"]).fillna(0).astype(int).to_numpy(),
                      "src_score": d["score"].to_numpy(), "adf_flag": d["adf_flag"].to_numpy(),
                      "minutes": C.num(d.get("wh_minutes", pd.Series(np.nan, index=d.index))).to_numpy(),
                      "parse_note": notes, "n_points": npts})
    m["year"] = pd.to_datetime(m["d"]).dt.year
    lv = m["src_tour"].map({"ATP": None, "CH": "CH", "FU": "ITF"})
    qual_of = {"CH": "CHQ", "ITF": "ITFQ"}
    m["level"] = [qual_of.get(x, x) if dr == "qual" and x else x for x, dr in zip(lv, m["draw"])]
    m.loc[m["src_tour"].eq("ATP") & m["draw"].eq("qual"), "level"] = "TQ"
    m["round"] = None
    m["slam"] = None
    m["best_of_hint"] = 3
    m["src_status"] = np.where(m["src_score"].astype(str).str.contains("RET|DEF|W/O", case=False), "retired", None)
    m["has_time"] = False
    m.attrs["rows_read"] = n0
    return pts, m
