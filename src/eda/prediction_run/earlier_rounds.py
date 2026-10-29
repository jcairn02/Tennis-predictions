"""Earlier qualifying rounds from TennisLive, as live rows with their results (an agent's choice of 24 Oct 2026, on the
owner's "we need to get this data"; the master pipeline's process log, Part 12).

Why. A qualifying match after its first round is blocked (gate.previous_round_missing) while a player's round before
at the event is missing from Stage 0, and it nearly always is on the day: Tennis My Life's men's qualifying file lags by
days (its 2026 file last changed on 23 Oct, with the qualifying of 17-18 Oct), and women's qualifying reaches the tables
only through the weekly lower-level feed (Wednesdays). On 24 Oct 2026 that blocked every round 2 of Vienna, Basel, Tokyo
and Guangzhou. TennisLive lists each finished match of an event within minutes (qualifying.py reads the round from it),
and its match pages give the box score.

    tl_score     the listing's games as Tennis My Life writes a score: winner first, a tiebreak's loser's points
    tl_box       a match page's statistics as Stage 0's TML box columns, winner first: the candidate builder's mapping
                 (lower_level_evidence/candidate_stage0.load_tennislive_pages: first serves in of serve points, first-
                 and second-serve points won, aces, double faults, break points from the opponent's "converted" line),
                 and service games (service_games), which the page does not list: the hold and break inputs read them.
                 A page whose winner took under 45% of the points is not used (TennisLive has swapped the players'
                 statistics). TennisLive's counts equal the history's on 99.6-100% of the qualifying levels measured
                 (docs/studies/tennislive_box_fill/README.md); the men's tour qualifying: master pipeline process log,
                 Part 14
    service_games  each side's service games from the score and the match's first server, games alternating
                 through the match and a tiebreak not counted as a service game but taking its turn: equal to Tennis
                 My Life's on 36 of 36 men's tour-qualifying matches of 17-19 Oct 2026 (counting the tiebreak: 15)
    played_rows  the sidecar's earlier matches as live rows with their result (live_role "played"), and the meta table
                 that dates them (played_meta: their day, venue and tour, which inject.py's links and pin read)

Live only: the rows go into a prediction run's sandbox, never the training history, and Stage 0 drops one as soon as its
source publishes the match (stage0_build.drop_replaced: the source's row stands). A row is left out, with its reason, when
a player is not exactly one Stage 0 player; the live match then stays blocked as before.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

TL_STATS = {"First serve": "fs", "First serve points won": "fw", "Second serve points won": "sw",
            "Break points converted": "bp", "Total points won": "tp", "Aces": "ace", "Double faults": "df"}
SWAP_SHARE = 0.45                    # a winner under this share of the points: the page's sides are taken as swapped
BOX_TML = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced"]
EARLIER_MATCH_NUM = 800              # before the live rows' 900s (live_rows.LIVE_MATCH_NUM)
SIDECAR_SUFFIX = "_earlier"          # <matchups>_earlier.csv beside the matchups CSV (src/pipeline/live.build_matchups)


def sidecar(csv) -> "Path":
    from pathlib import Path
    p = Path(csv)
    return p.with_name(p.stem + SIDECAR_SUFFIX + ".csv")


def same_player(a, b) -> bool:
    """Two spellings of one name (25 Oct 2026): the same key; or every word of one among the other's, each with two
    words at least (TennisLive adds given names: "Chak Lam Coleman Wong" for Stage 0's "Coleman Wong", "Jodie Anna
    Burrage" for "Jodie Burrage"); or the same letters in the same order once the spaces go ("Seongchan Hong", "Seong
    Chan Hong"). The linker takes it only when exactly one Stage 0 player fits (src/pipeline/live._tl_player)."""
    from src.eda.merge_feasibility.scan import name_key, norm
    if not (isinstance(a, str) and isinstance(b, str) and a.strip() and b.strip()):
        return False
    ka, kb = name_key(a), name_key(b)
    if ka == kb:
        return True
    ta, tb = set(ka.split()), set(kb.split())
    if min(len(ta), len(tb)) >= 2 and (ta <= tb or tb <= ta):
        return True
    return norm(a).replace(" ", "") == norm(b).replace(" ", "")


def _frac(text) -> tuple[int | None, int | None]:
    m = re.match(r"^\s*(\d+)\s*/\s*(\d+)\s*$", str(text or ""))
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def _int(text) -> int | None:
    m = re.match(r"^\s*(\d+)\s*$", str(text or ""))
    return int(m.group(1)) if m else None


def service_games(score: str, first_is_winner: bool) -> tuple[int, int]:
    """(the winner's, the loser's) service games of a winner-first score ('7-6(4) 3-6 6-2', ' RET' allowed): games
    alternate from the first server through every set; a 7-6 set's tiebreak takes its turn but is not a service game."""
    w = lo = 0
    winner_serves = bool(first_is_winner)
    for a, b in re.findall(r"(\d+)-(\d+)", re.sub(r"\(\d+\)", "", str(score))):
        a, b = int(a), int(b)
        tiebreak = {a, b} == {6, 7}
        for _ in range(12 if tiebreak else a + b):
            if winner_serves:
                w += 1
            else:
                lo += 1
            winner_serves = not winner_serves
        if tiebreak:
            winner_serves = not winner_serves
    return w, lo


def tl_box(statistics: list[dict], winner_side: int, first_server_index=None, score: str | None = None
           ) -> tuple[dict | None, str]:
    """(the TML box columns w_* and l_*, as text; None when not usable, with the reason) from a parsed match page's
    statistics (tennislive.parse_match_page), the page's winner (1 or 2), and its first server (meta's
    first_server_index: 0 or 1, the page's player order) with the winner-first score for the service games (blank
    without them, which Stage 0 keeps as "no_svgms")."""
    rows = {s["name"]: s for s in statistics
            if s.get("period") == "match" and (s.get("name") in TL_STATS or s.get("name") == "Service games won")}
    need = [n for n in TL_STATS if n != "Total points won"]
    if any(n not in rows for n in need):
        return None, f"statistics incomplete (missing: {[n for n in need if n not in rows]})"
    per = {}
    for side in (1, 2):
        opp = 2 if side == 1 else 1
        first_in, svpt = _frac(rows["First serve"][f"player{side}_detail"])
        first_won = _frac(rows["First serve points won"][f"player{side}_detail"])[0]
        second_won = _frac(rows["Second serve points won"][f"player{side}_detail"])[0]
        conv, chances = _frac(rows["Break points converted"][f"player{opp}_detail"])
        ace, df = _int(rows["Aces"][f"player{side}_value"]), _int(rows["Double faults"][f"player{side}_value"])
        vals = {"ace": ace, "df": df, "svpt": svpt, "1stIn": first_in, "1stWon": first_won, "2ndWon": second_won,
                "bpFaced": chances, "bpSaved": None if chances is None or conv is None else chances - conv}
        if any(v is None for v in vals.values()):
            return None, f"a count is unreadable (player {side}: {vals})"
        per[side] = vals
    if "Total points won" in rows:
        tp = [_frac(rows["Total points won"][f"player{s}_detail"])[0] for s in (1, 2)]
        if None not in tp and sum(tp) > 0 and tp[winner_side - 1] / sum(tp) < SWAP_SHARE:
            return None, f"the winner took {tp[winner_side - 1]} of {sum(tp)} points: the page's sides look swapped"
    loser_side = 2 if winner_side == 1 else 1
    sv = None
    if first_server_index in (0, 1) and score and "W/O" not in str(score):
        sv = service_games(score, first_server_index == winner_side - 1)
    elif score and "W/O" not in str(score) and "Service games won" in rows:
        # a page without its game-by-game record: the "Service games won" line's games played, only when they are the
        # score's games as one of the two first servers would give them (the line is built from the live points, and
        # some pages hold only part of them: Machac v Moutet, Vienna 2026, 7 + 6 for a 6-4 6-4)
        played = [_frac(rows["Service games won"][f"player{s}_detail"])[1] for s in (winner_side, loser_side)]
        if tuple(played) in {service_games(score, True), service_games(score, False)}:
            sv = tuple(played)
    out = {}
    for prefix, side, k in (("w", winner_side, 0), ("l", loser_side, 1)):
        for c in BOX_TML:
            out[f"{prefix}_{c}"] = ("" if sv is None else str(sv[k])) if c == "SvGms" else str(per[side][c])
    return out, "TennisLive match page" + ("" if sv else " (service games unknown: no first server)")


def _sets(text) -> list[tuple[int, int | None]]:
    """'7(7) 3 2' -> [(7, 7), (3, None), (2, None)] (candidate_stage0.tl_sets)."""
    return [(int(g), int(t) if t else None) for g, t in re.findall(r"(\d+)(?:\((\d+)\))?", str(text or ""))]


def tl_score(player1_sets, player2_sets, winner_side: int, end_reason=None) -> str:
    """The listing's games as Tennis My Life's score: winner first, a 7-6 set with the tiebreak loser's points, and
    " RET" for a retirement (candidate_stage0.load_tennislive's rule)."""
    a, b = _sets(player1_sets), _sets(player2_sets)
    if winner_side == 2:
        a, b = b, a
    out = []
    for (x, tx), (y, ty) in zip(a, b):
        s = f"{x}-{y}"
        if {x, y} == {6, 7}:
            lost = ty if x > y else tx
            if lost is not None:
                s += f"({lost})"
        out.append(s)
    mark = {"retired": " RET", "disqualified": " DEF"}.get(str(end_reason or ""), "")
    return " ".join(out) + mark


def finish_utc(row) -> pd.Timestamp | None:
    """A TennisLive results row's finish (finished_at, else observed_finished_at: epoch seconds, 0 when unknown), else
    its start (start_utc, 'YYYY-MM-DD HH:MM')."""
    for c in ("finished_at", "observed_finished_at"):
        v = pd.to_numeric(pd.Series([row.get(c)]), errors="coerce").iloc[0]
        if pd.notna(v) and v > 0:
            return pd.Timestamp(int(v), unit="s", tz="UTC")
    t = pd.to_datetime(row.get("start_utc"), utc=True, errors="coerce")
    return None if pd.isna(t) else t


def uk_day(ts) -> str | None:
    """The UK day (YYYY-MM-DD) of a UTC time: the day the run's meta tables use (prediction_run/run.uk_day)."""
    t = pd.to_datetime(ts, utc=True, errors="coerce")
    if pd.isna(t):
        return None
    return t.tz_convert("Europe/London").date().isoformat()


def played_rows(earlier: pd.DataFrame, raw: pd.DataFrame, players: pd.DataFrame, stage0_keyed: pd.DataFrame,
                event_tid, handles: dict | None = None, leave_out: bool = False
                ) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """(live rows with their results, their meta for the dating, the rows left out with the reason) from the sidecar.
    earlier: one row per earlier match (src/pipeline/live.build_matchups' sidecar). raw: the staged TML rows
    (live_rows.staged_tml). players: live_rows.stage0_players (a player without a TML row). stage0_keyed: Stage 0's
    player rows with their tour and name key (each name must give one player). event_tid(row): the event's Stage 0 id.
    handles (live_rows.id_handles, since 28 Oct 2026): the match id takes each player's id as Stage 0's match ids give
    the one the row carries; without it, the players' Stage 0 ids (as before). leave_out (the daily engine's live runs,
    since 28 Oct 2026): a row that fails in any other way is left out with its reason too, and the others are built."""
    out, meta, left = [], [], []
    for i, e in earlier.reset_index(drop=True).iterrows():
        try:
            _played_row(i, e, raw, players, stage0_keyed, event_tid, handles, out, meta, left)
        except (SystemExit, Exception) as exc:  # noqa: BLE001 - one earlier round's failure, kept with its reason
            if not leave_out:
                raise
            from src.eda.prediction_run import common as P
            left.append({"tl_url": e.get("tl_url"), "reason": P.reason_of(exc)})
    rows = pd.DataFrame(out)
    if len(rows):
        rows = rows.reindex(columns=list(dict.fromkeys(list(rows.columns))))
    return rows, pd.DataFrame(meta), left


def _played_row(i: int, e: pd.Series, raw: pd.DataFrame, players: pd.DataFrame, stage0_keyed: pd.DataFrame, event_tid,
                handles: dict | None, out: list, meta: list, left: list) -> None:
    """One sidecar row (position i): its live row and its meta row appended together, or its reason in left."""
    from src.eda.predictability_diagnostic import stage0_build as B
    from src.eda.prediction_run import live_rows as LR

    tour = str(e["tour"])
    name = e.get("tourney_name") if isinstance(e.get("tourney_name"), str) and e.get("tourney_name") else None
    event = LR.event_rows(raw, tour, e["tourney_id"], name)
    event_date = None
    if event.empty:
        row = LR.csv_event(e)
        if row is None:
            left.append({"tl_url": e.get("tl_url"), "reason": f"no columns of the event {e['tourney_id']}"})
            return
        event_date = row["tourney_date"]
    else:
        first = LR.latest(event).iloc[0]
        row = {c: first[c] for c in LR.EVENT}
        if pd.notna(e.get("best_of")) and str(e.get("best_of")).strip():
            row["best_of"] = str(int(float(e["best_of"])))
    try:
        for side, who in (("winner", "winner_name"), ("loser", "loser_name")):
            cols = LR.player_columns(raw, tour, B.S.name_key(str(e[who])), event, event_date, players)
            row.update({f"{side}_{b}": v for b, v in cols.items()})
    except SystemExit as exc:
        left.append({"tl_url": e.get("tl_url"), "reason": str(exc)})
        return
    ids = []
    for who in ("winner_name", "loser_name"):
        hit = stage0_keyed[stage0_keyed["tour"].eq(tour) & stage0_keyed["key"].eq(B.S.name_key(str(e[who])))]
        ids.append(hit["player_id"].unique())
    if any(len(x) != 1 for x in ids):
        left.append({"tl_url": e.get("tl_url"), "reason": f"{e['winner_name']} / {e['loser_name']}: not exactly one "
                     f"Stage 0 player each ({[len(x) for x in ids]})"})
        return
    main = e.get("event_main_date")
    if main is not None and not (not isinstance(main, str) and pd.isna(main)) and str(main).strip():
        row["event_main_date"] = str(int(float(main)))
    row.update({"round": str(e["round"]).upper(), "score": str(e["score"]), "minutes": "",
                "match_num": str(EARLIER_MATCH_NUM + i), "tour": tour, "live_role": "played",
                "_source_file": "earlier_rounds", "_row": i})
    for c in LR.BOX:
        v = e.get(c)
        row[c] = "" if v is None or (not isinstance(v, str) and pd.isna(v)) else str(int(float(v))) if str(v).strip() else ""
    tid = event_tid(e)
    lo, hi = sorted(LR.handle_of(handles or {}, tour, row.get(f"{side}_id"), x[0])
                    for side, x in (("winner", ids[0]), ("loser", ids[1])))
    out.append(row)
    meta.append({"match_id": f"{tour}|{tid}|{str(e['round']).upper()}|{lo}|{hi}", "day": e["day"],
                 "venue": e.get("venue"), "tour": tour, "tournament_name": row["tourney_name"],
                 "round": str(e["round"]).upper(), "winner": e["winner_name"], "loser": e["loser_name"],
                 "score": e["score"], "has_box": bool(str(row.get("w_svpt", "")).strip()),
                 "tl_url": e.get("tl_url"), "box_note": e.get("box_note")})
