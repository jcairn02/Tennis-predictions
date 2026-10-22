"""Recounts of the nine counts from the ATP Stats Centre's point records (atp_ readers).

Two kinds of point record:
    MatchBeats (the backfill's and the Challengers' points.parquet): every point names its server (1/2), its serve
        number (1 = played on the first serve, 2 = after a first-serve fault, double faults included), its scorer and
        its ending (A ace; P or DF double fault, see infosys_atp_backfill/README.md quirk 1; W, FE, UE; N unclassified),
        and whether it was a break point (isBrkPt, the state before the point). Nothing to derive.
    Rally analysis (the Hugging Face handoff, the staged rally tables, SirGenkii): every point is filed under the side
        and kind that ended it (t1err, t1win, t2err, t2win), so the point's WINNER is known (t1win or t2err: player 1;
        t2win or t1err: player 2), with its serve number (pointId = set_game_point_serve), ending (ACE, DOUBLE FAULT,
        WINNER, FORCED ERROR, UNFORCED ERROR, UNCLASSIFIED), the score before the point SERVER FIRST ("30-40" with the
        receiver's break-point flag set), the break-point flags of each side (tXBreakPoint: X can break on this point)
        and the tiebreak flag. The SERVER is not given and is derived (derive_servers):
        1. per non-tiebreak game, evidence for its server: an ace is won by the server; a double fault is lost by
           the server (filed either as the server's error or as the receiver's win); a side holding a break point is
           the receiver; and two consecutive points' scores (server first) show whether the server or the receiver
           won the first of them, so with that point's winner they name the server;
        2. per tiebreak, the same evidence point by point, under the serving pattern A, B, B, A, A, ... (the first
           server is the player whose turn it was);
        3. games alternate within a set (game g is served by the set's first server when g is odd), so each set's first
           server is the side most of its games' evidence points to; every point's server then follows from it. The
           failure measures: games whose own evidence contradicts the alternation, sets with no evidence or a tied
           vote (the match is then not recounted), aces or double faults contradicting the assigned server, and sets
           whose first server does not follow from the previous set's (games alternate across sets, a tiebreak counted
           as one game).
        Validated against MatchBeats' own server where both routes hold the same points (atp_validate_server.py).

The counts (Sackmann's definitions), per player as server: svpt every point served; first_in serve 1; first_won
serve 1 and won; second_won serve 2 and won (a double fault is a lost second-serve point); ace; df; sv_gms the
non-tiebreak games served (each game once, for the server of most of its points: x_games_two_servers counts games
whose record names both players as server), the game in progress at a retirement left out as the ATP and Sackmann
leave it out
(x_sv_gms_unfinished says whose it was), x_tb_first the tiebreaks the player served first, x_tb_played the tiebreaks
played (a source that counts tiebreaks as service games shows sv_gms + one of these); bp_faced the points served at
break point
(the record's flag: MatchBeats isBrkPt, rally analysis the receiver's tXBreakPoint); bp_saved those won; sv_won
first_won + second_won. x_bp_faced_seq is the same count derived from the score sequence instead of the flag.

Completeness (complete): every point of every game present (point numbers 1..n with no gap), every game of every set
present (1..n), every game ending at its last point (the final game of a retired match may be unfinished), and the
recount's set games equal to Stage 0's score (oriented by the link). x_sets_recount / x_sets_stage0 show both.
"""
from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np

PT = {"0": 0, "15": 1, "30": 2, "40": 3, "AD": 4, "A": 4}


def parse_score(s) -> tuple | None:
    """'30-40' -> (2, 3) (server first); tiebreak '5-6' -> ('tb', 5, 6); None when unreadable."""
    if s is None:
        return None
    t = str(s).strip().upper()
    if "-" not in t:
        return None
    a, b = t.split("-", 1)
    a, b = a.strip(), b.strip()
    if a in PT and b in PT and not (a.isdigit() and b.isdigit() and (int(a) not in (0, 15, 30, 40)
                                                                     or int(b) not in (0, 15, 30, 40))):
        return (PT[a], PT[b])
    if a.isdigit() and b.isdigit():
        return ("tb", int(a), int(b))
    return None


def advance(state: tuple, server_won: bool) -> tuple | None:
    """The next state of a regular game (server first) after a point; None when the point ends the game."""
    x, y = state
    if not server_won:
        y2, x2 = advance((y, x), True) or (None, None)
        return None if y2 is None else (x2, y2)
    if x == 4:
        return None
    if y == 4:
        return (3, 3)
    if x == 3 and y < 3:
        return None
    if x == 3 and y == 3:
        return (4, 3)
    return (x + 1, y)


def tb_server(first: int, p: int) -> int:
    """The server of tiebreak point p (1-based) when `first` served the tiebreak's first point: A, B, B, A, A, ..."""
    if p == 1:
        return first
    return first if ((p - 2) // 2) % 2 == 1 else 3 - first


def game_ok(winners: list, tb: bool, no_ad: bool = False) -> bool:
    """The game ends exactly at its last point: a regular game at 4+ points with 2 ahead (no-ad scoring, the Next Gen
    Finals': the first to 4), a tiebreak at 7+ with 2 ahead."""
    a = b = 0
    n = len(winners)
    for k, w in enumerate(winners):
        if w == 1:
            a += 1
        else:
            b += 1
        hi, lo = max(a, b), min(a, b)
        if tb:
            done = hi >= 7 and hi - lo >= 2
        else:
            done = hi >= 4 and (hi - lo >= 2 or no_ad)
        if done:
            return k == n - 1
    return False


def sets_won(games_sets: list, short_sets: bool = False) -> tuple[int, int]:
    """Sets won by players 1 and 2 among decided sets (6+ games and 2 ahead, 7-5, 7-6; short sets: 4 and 2 ahead,
    4-3)."""
    won = [0, 0]
    for a, b in games_sets:
        hi, lo = max(a, b), min(a, b)
        decided = (hi >= 6 and hi - lo >= 2) or (hi == 7 and lo in (5, 6))
        if short_sets:
            decided = decided or (hi == 4 and (hi - lo >= 2 or lo == 3))
        if decided and a != b:
            won[0 if a > b else 1] += 1
    return won[0], won[1]


def derive_servers(points: list[dict]) -> tuple[dict, dict]:
    """points: dicts with set, game, point, winner, end, score, bp1, bp2, tb. Returns ({(set, game, point): server},
    diagnostics)."""
    by_game = defaultdict(list)
    for p in points:
        by_game[(p["set"], p["game"])].append(p)
    for g in by_game.values():
        g.sort(key=lambda q: q["point"])
    diag = Counter()
    game_vote = {}          # (set, game) -> {1: votes, 2: votes} (for tiebreaks: votes for the first server)
    for (s, g), pts in by_game.items():
        tb = any(q["tb"] for q in pts)
        v = Counter()
        if not tb:
            for q in pts:
                if q["end"] == "ACE":
                    v[q["winner"]] += 1
                elif q["end"] == "DOUBLE FAULT":
                    v[3 - q["winner"]] += 1
                if q["bp1"]:
                    v[2] += 1
                if q["bp2"]:
                    v[1] += 1
            for q, r in zip(pts, pts[1:]):
                if r["point"] != q["point"] + 1:
                    continue
                a, b = parse_score(q["score"]), parse_score(r["score"])
                if not a or not b or a[0] == "tb" or b[0] == "tb":
                    continue
                if advance(a, True) == b:
                    v[q["winner"]] += 1
                elif advance(a, False) == b:
                    v[3 - q["winner"]] += 1
                else:
                    diag["score_steps_inconsistent"] += 1
        else:
            for first in (1, 2):
                for q in pts:
                    srv = tb_server(first, q["point"])
                    if q["end"] == "ACE":
                        v[first] += srv == q["winner"]
                    elif q["end"] == "DOUBLE FAULT":
                        v[first] += srv != q["winner"]
                # scores: the server-first score must equal the points each side has won so far
                won = {1: 0, 2: 0}
                expect = 1
                for q in pts:
                    if q["point"] != expect:
                        break
                    sc = parse_score(q["score"])
                    srv = tb_server(first, q["point"])
                    if sc and sc[0] == "tb":
                        v[first] += (sc[1], sc[2]) == (won[srv], won[3 - srv])
                    won[q["winner"]] += 1
                    expect += 1
        game_vote[(s, g)] = (tb, v)
    servers, set_first = {}, {}
    for s in sorted({k[0] for k in by_game}):
        votes = Counter()
        for (s2, g), (tb, v) in game_vote.items():
            if s2 != s:
                continue
            if tb:
                # the tiebreak (game 13) is served first by the set's first server (13 is odd); one vote, as a game
                if v[1] != v[2]:
                    own_first = 1 if v[1] > v[2] else 2
                    votes[own_first if g % 2 == 1 else 3 - own_first] += 1
                continue
            if v[1] == v[2]:
                diag["games_without_evidence"] += 1
                continue
            own = 1 if v[1] > v[2] else 2
            votes[own if g % 2 == 1 else 3 - own] += 1
        if votes[1] == votes[2]:
            diag["sets_without_assignment"] += 1
            continue
        f = 1 if votes[1] > votes[2] else 2
        set_first[s] = f
        for (s2, g), (tb, v) in game_vote.items():
            if s2 != s:
                continue
            srv_g = f if g % 2 == 1 else 3 - f
            if tb:
                diag["tiebreaks"] += 1
                if (v[srv_g] < v[3 - srv_g]):
                    diag["tiebreak_evidence_against"] += 1
            else:
                diag["games"] += 1
                if v[1] != v[2] and (1 if v[1] > v[2] else 2) != srv_g:
                    diag["games_evidence_against_alternation"] += 1
            for q in by_game[(s, g)]:
                srv = tb_server(srv_g, q["point"]) if tb else srv_g
                servers[(s, g, q["point"])] = srv
                if q["end"] == "ACE" and q["winner"] != srv:
                    diag["aces_against_assigned_server"] += 1
                if q["end"] == "DOUBLE FAULT" and q["winner"] == srv:
                    diag["double_faults_against_assigned_server"] += 1
    # the first server of each set follows from the previous set's (a tiebreak counts as one game)
    sets = sorted(set_first)
    for s, t in zip(sets, sets[1:]):
        if t != s + 1:
            continue
        n_games = max(g for (s2, g) in by_game if s2 == s)
        expect = set_first[s] if n_games % 2 == 0 else 3 - set_first[s]
        diag["set_pairs"] += 1
        diag["set_first_server_against_previous_set"] += set_first[t] != expect
    return servers, dict(diag)


def recount_match(points: list[dict], stage0_sets: tuple | None, p1_is_winner, retired: bool,
                  derive: bool, no_ad: bool = False) -> dict:
    """The nine counts of both players (keys '<count>_1', '<count>_2') and the completeness of one match.
    points: dicts with set, game, point, serve (1/2), winner (1/2), end, bp1, bp2 (side X can break: the point is a
    break point against the other side's serve), tb, and either server (MatchBeats) or score (rally analysis).
    stage0_sets: Stage 0's set games, winner first; p1_is_winner: whether player 1 is Stage 0's winner (None if the
    match is not linked)."""
    out = {}
    pts = [p for p in points if p["winner"] in (1, 2) and p["set"] is not None and p["game"] is not None
           and p["point"] is not None]
    out["x_points"] = len(pts)
    diag = {}
    if derive:
        servers, diag = derive_servers(pts)
        for p in pts:
            p["server"] = servers.get((p["set"], p["game"], p["point"]))
    out["x_points_without_server"] = sum(1 for p in pts if p.get("server") not in (1, 2))
    for k, v in diag.items():
        out["x_" + k] = v
    by_game = defaultdict(list)
    for p in pts:
        by_game[(p["set"], p["game"])].append(p)
    for g in by_game.values():
        g.sort(key=lambda q: q["point"])
    # counts
    c = {n: {1: 0, 2: 0} for n in ("svpt", "first_in", "first_won", "second_won", "ace", "df", "bp_faced",
                                   "bp_saved", "bp_faced_seq")}
    sv_games = {1: set(), 2: set()}
    tb_first = {1: 0, 2: 0}
    tb_played = 0
    for (s, g), gp in by_game.items():
        tb = any(q["tb"] for q in gp)
        if tb:
            tb_played += 1
            f = [q for q in gp if q["point"] == 1]
            if f and f[0].get("server") in (1, 2):
                tb_first[f[0]["server"]] += 1
        state = (0, 0)
        expect = 1
        for q in gp:
            srv = q.get("server")
            if srv not in (1, 2):
                continue
            won = q["winner"] == srv
            c["svpt"][srv] += 1
            if q["serve"] == 1:
                c["first_in"][srv] += 1
                c["first_won"][srv] += won
            elif q["serve"] == 2:
                c["second_won"][srv] += won
            c["ace"][srv] += q["end"] == "ACE"
            c["df"][srv] += q["end"] == "DOUBLE FAULT"
            # the receiver can break; a record whose flags do not say which side (bp_any) marks the point only
            bp = q["bp_any"] if "bp_any" in q else (q["bp2"] if srv == 1 else q["bp1"])
            if bp and not tb:
                c["bp_faced"][srv] += 1
                c["bp_saved"][srv] += won
            if not tb:
                # break point from the score sequence (only while every earlier point of the game is present)
                if state is not None and q["point"] == expect:
                    x, y = state
                    if (y == 3 and x < 3) or y == 4:
                        c["bp_faced_seq"][srv] += 1
                    state = advance(state, won)
                    expect += 1
                else:
                    state = None
    # a non-tiebreak game has one server: it counts once, for the server of most of its points (the first point's on a
    # tie); a game whose record names both players as server on some point is counted in x_games_two_servers (TDI:
    # 8 such games gave a recount one service game above the score)
    two = 0
    for (s, g), gp in by_game.items():
        if any(q["tb"] for q in gp):
            continue
        srvs = [q.get("server") for q in gp if q.get("server") in (1, 2)]
        if not srvs:
            continue
        n1, n2 = srvs.count(1), srvs.count(2)
        two += n1 > 0 and n2 > 0
        sv_games[1 if n1 > n2 else 2 if n2 > n1 else srvs[0]].add((s, g))
    out["x_games_two_servers"] = two
    for n, d in c.items():
        for no in (1, 2):
            out[f"{n}_{no}"] = float(d[no])
    for no in (1, 2):
        out[f"sv_gms_{no}"] = float(len(sv_games[no]))
        out[f"sv_won_{no}"] = out[f"first_won_{no}"] + out[f"second_won_{no}"]
        out[f"x_tb_first_{no}"] = tb_first[no]
        out[f"x_bp_faced_seq_{no}"] = out.pop(f"bp_faced_seq_{no}")
    out["x_tb_played"] = tb_played
    # completeness: point and game gaps, games ending at their last point, set games against Stage 0
    point_gaps = game_gaps = bad_games = 0
    sets = defaultdict(dict)
    for (s, g), gp in by_game.items():
        nums = [q["point"] for q in gp]
        point_gaps += max(nums) - len(set(nums))
        if min(nums) != 1:
            point_gaps += min(nums) - 1
        tb = any(q["tb"] for q in gp)
        if not game_ok([q["winner"] for q in gp], tb, no_ad):
            bad_games += 1
            sets[s][g] = None
        else:
            sets[s][g] = gp[-1]["winner"]
    games_sets = []
    last_set = max(sets) if sets else None
    final_unfinished = False
    for s in sorted(sets):
        gs = sets[s]
        game_gaps += max(gs) - len(gs)
        unfinished = [g for g, w in gs.items() if w is None]
        if s == last_set and unfinished and max(gs) in unfinished:
            final_unfinished = True
        games_sets.append((sum(1 for w in gs.values() if w == 1), sum(1 for w in gs.values() if w == 2)))
    # the game in progress when a match stops (a retirement) is not a service game played: the ATP's key statistics and
    # Sackmann count finished games only (observed: 286 of the 290 handoff rows whose recount had one service game more
    # were such games, and Stage 0 equalled the key statistics on them)
    for no in (1, 2):
        out[f"x_sv_gms_unfinished_{no}"] = 0
    if final_unfinished:
        g_last = max(sets[last_set])
        for srv in (1, 2):
            if (last_set, g_last) in sv_games[srv]:
                out[f"sv_gms_{srv}"] -= 1
                out[f"x_sv_gms_unfinished_{srv}"] = 1
    out["x_point_gaps"] = point_gaps
    out["x_game_gaps"] = game_gaps
    out["x_games_not_ending_at_last_point"] = bad_games
    out["x_final_game_unfinished"] = final_unfinished
    out["x_sets_recount"] = " ".join(f"{a}-{b}" for a, b in games_sets)
    out["x_sets_won_1"], out["x_sets_won_2"] = sets_won(games_sets, short_sets=no_ad)
    return finalize(out, stage0_sets, p1_is_winner, retired)


def finalize(out: dict, stage0_sets, p1_is_winner, retired: bool) -> dict:
    """Completeness against Stage 0: x_sets_stage0 (Stage 0's set games, player 1 first), x_sets_equal, complete
    (no point or game gap, every game ending at its last point, the game in progress at a retirement excepted, every
    point with a server, and the same set games as Stage 0)."""
    sets_ok = None
    if stage0_sets is not None and isinstance(stage0_sets, tuple) and p1_is_winner is not None \
            and not (isinstance(p1_is_winner, float) and np.isnan(p1_is_winner)):
        s0 = [(w, l) if p1_is_winner else (l, w) for w, l in stage0_sets]
        out["x_sets_stage0"] = " ".join(f"{a}-{b}" for a, b in s0)
        rec = [tuple(int(v) for v in t.split("-")) for t in str(out.get("x_sets_recount") or "").split()]
        sets_ok = rec == s0
    else:
        out["x_sets_stage0"] = None
    out["x_sets_equal"] = sets_ok
    bad = out["x_games_not_ending_at_last_point"] - (1 if retired and out.get("x_final_game_unfinished") else 0)
    out["complete"] = bool(out["x_points"]) and out["x_point_gaps"] == 0 and out["x_game_gaps"] == 0 and bad == 0 \
        and bool(sets_ok) and out["x_points_without_server"] == 0
    return out
