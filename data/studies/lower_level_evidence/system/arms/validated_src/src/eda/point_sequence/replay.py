"""Replay a point sequence under the scoring rules, and the servers the rules imply.

``replay(winners, rules)`` plays a list of point winners (1 or 2; anything else is an unknown winner) and returns
where each point falls (set, game within the set, game within the match, point within the game, tie-break or not),
the completed sets' scores, the state reached and the match winner. A game ends on its last point: a regular game at
four points with two clear (or, with no-ad scoring, at four points); a tie-break at seven (ten for a ten-point
tie-break) with two clear. A set ends at six games with two clear or on a tie-break at six-all; the deciding set
follows the rules' ``final``:

    tb      a 7-point tie-break at 6-6, like the other sets (every tour event, the US Open)
    tb10    a 10-point tie-break at 6-6 (Australian Open from 2019; every Slam from 2022)
    adv     no tie-break: the set goes on until two games clear (Slams before those changes except the US Open,
            older Davis Cup and Olympics)
    tb12    a 7-point tie-break at 12-12 (Wimbledon 2019-2021)
    mtb10   a 10-point match tie-break in place of the deciding set (Stage 0 format "match_tiebreak": many ITF events)

and ``set_games``/``tb_at`` give short sets (Stage 0 format "short_sets", the Next Gen Finals: sets to four, a
tie-break at 3-3, no-ad games). The match ends when a player has won best_of // 2 + 1 sets.

Status of a replay:
    complete   the match ends exactly on the last point
    partial    every point is consistent and the match has not ended (a retirement, or a truncated record)
    overlong   the match ended before the last point: points after the end
    unknown    a point's winner is unknown: the replay stops there

``rule_servers`` gives each point's server under the rules from the first server: the serve alternates by game over
the whole match (a tie-break counts as one game); in a tie-break the first server serves one point, then the serve
alternates every two points. (After a tie-break the player who received first serves the next set's first game,
which is what the game alternation gives.)

``replay_match`` tries the rules a match's context allows (``candidates``: with Stage 0's context only the rules that
can apply; without it everything), most likely first, and keeps the first under which the match completes; when none
completes it keeps the first candidate's replay if it is partial, else the first partial one, else the first
candidate's. Which rule was used is recorded, and so is whether it was the first candidate (a match completed under a
fallback rule is checked against the official score before it is trusted: build.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

FINALS = ("tb", "tb10", "adv", "tb12", "mtb10")


@dataclass(frozen=True)
class Rules:
    best_of: int = 3
    final: str = "tb"
    set_games: int = 6
    tb_at: int = 6
    no_ad: bool = False

    @property
    def name(self) -> str:
        s = f"bo{self.best_of}/{self.final}"
        if self.set_games != 6 or self.tb_at != 6:
            s += f"/sets{self.set_games}tb{self.tb_at}"
        if self.no_ad:
            s += "/noad"
        return s


STD3 = Rules(3, "tb")
STD5 = Rules(5, "tb")


@dataclass
class Replay:
    status: str
    stop: int                      # points replayed: all of them unless overlong or unknown
    sets: list                     # completed sets: (games1, games2, tb1, tb2), tb None without a tie-break
    games: tuple                   # games in the unfinished set (0, 0 when complete)
    points: tuple                  # points in the unfinished game
    winner: int                    # 1 or 2 when finished, else 0
    set_no: np.ndarray             # per point, -1 beyond stop
    game_no: np.ndarray            # game within the set, 1-based
    game_idx: np.ndarray           # game within the match, 0-based
    pt_no: np.ndarray              # point within the game, 1-based
    is_tb: np.ndarray              # 1 in a tie-break (a match tie-break included)
    rule: Rules = field(default=STD3)
    primary: bool = True
    tried: int = 1

    @property
    def sets_won(self) -> tuple:
        a = sum(1 for g1, g2, _, _ in self.sets if g1 > g2)
        return a, len(self.sets) - a


def replay(winners, rules: Rules = STD3) -> Replay:
    w = np.asarray(winners).astype(np.int64)
    n = len(w)
    set_no = np.full(n, -1, np.int16)
    game_no = np.full(n, -1, np.int16)
    game_idx = np.full(n, -1, np.int16)
    pt_no = np.full(n, -1, np.int16)
    is_tb = np.zeros(n, np.int8)
    need = rules.best_of // 2 + 1
    final, tb_at, set_games, no_ad = rules.final, rules.tb_at, rules.set_games, rules.no_ad
    s1 = s2 = 0          # sets won
    g1 = g2 = 0          # games in the set
    p1 = p2 = 0          # points in the game
    gi = 0               # game in the match
    sets: list = []
    kind, target = 0, 4  # 0 regular game, 1 tie-break, 2 match tie-break
    winner = 0
    status, stop = None, n
    wl = w.tolist()
    for i in range(n):
        x = wl[i]
        if winner:
            status, stop = "overlong", i
            break
        if x != 1 and x != 2:
            status, stop = "unknown", i
            break
        if p1 == 0 and p2 == 0:
            deciding = s1 == need - 1 and s2 == need - 1
            if deciding and final == "mtb10":
                kind, target = 2, 10
            elif g1 == tb_at and g2 == tb_at and not (deciding and final in ("adv", "tb12")):
                kind, target = 1, (10 if deciding and final == "tb10" else 7)
            elif deciding and final == "tb12" and g1 == 12 and g2 == 12:
                kind, target = 1, 7
            else:
                kind, target = 0, 4
        if x == 1:
            p1 += 1
        else:
            p2 += 1
        set_no[i] = len(sets) + 1
        game_no[i] = g1 + g2 + 1
        game_idx[i] = gi
        pt_no[i] = p1 + p2
        if kind:
            is_tb[i] = 1
            done = (p1 >= target or p2 >= target) and abs(p1 - p2) >= 2
        elif no_ad:
            done = p1 >= 4 or p2 >= 4
        else:
            done = (p1 >= 4 or p2 >= 4) and abs(p1 - p2) >= 2
        if not done:
            continue
        gw = 1 if p1 > p2 else 2
        a, b = p1, p2
        p1 = p2 = 0
        gi += 1
        if kind == 2:
            sets.append((1, 0, a, b) if gw == 1 else (0, 1, a, b))
            set_over = True
        else:
            if gw == 1:
                g1 += 1
            else:
                g2 += 1
            set_over = kind == 1 or ((g1 >= set_games or g2 >= set_games) and abs(g1 - g2) >= 2)
            if set_over:
                sets.append((g1, g2, a, b) if kind == 1 else (g1, g2, None, None))
                g1 = g2 = 0
        if set_over:
            if gw == 1:
                s1 += 1
            else:
                s2 += 1
            if s1 == need or s2 == need:
                winner = gw
    if status is None:
        status = "complete" if winner else "partial"
    return Replay(status, stop, sets, (g1, g2), (p1, p2), winner, set_no, game_no, game_idx, pt_no, is_tb, rules)


def rule_servers(game_idx: np.ndarray, pt_no: np.ndarray, is_tb: np.ndarray, s0: int) -> np.ndarray:
    """Each point's server under the rules (1 or 2; 0 where the replay did not reach the point)."""
    gi = np.asarray(game_idx).astype(np.int64)
    first = np.where(gi % 2 == 0, s0, 3 - s0)
    k = np.asarray(pt_no).astype(np.int64) - 1
    flip = ((k + 1) // 2) % 2 == 1
    srv = np.where((np.asarray(is_tb) > 0) & flip, 3 - first, first)
    return np.where(gi < 0, 0, srv).astype(np.int8)


def best_first_server(game_idx, pt_no, is_tb, source_server) -> tuple[int, float]:
    """The first server (1 or 2) under which the rules agree best with a source's servers, and the share of the
    source's known servers they agree with (NaN when it has none)."""
    src = np.asarray(source_server)
    known = (src == 1) | (src == 2)
    reach = np.asarray(game_idx) >= 0
    m = known & reach
    if not m.any():
        return 1, float("nan")
    r1 = rule_servers(game_idx, pt_no, is_tb, 1)
    a1 = float((r1[m] == src[m]).mean())
    a2 = 1.0 - a1          # the rule for s0 = 2 is the mirror of s0 = 1 at every point
    return (1, a1) if a1 >= a2 else (2, a2)


def slam_final(slam: str | None, year: int, qual: bool = False) -> str:
    """The deciding-set rule of a Grand Slam in a year. Main draws: the Australian Open's 10-point tie-break from 2019,
    Wimbledon's tie-break at 12-12 in 2019-2021, and every Slam's 10-point tie-break from 2022; the US Open's 7-point
    tie-break throughout. Qualifying, as Stage 0's deciding-set scores show (7-6 sets and no set past 7 games): a
    7-point tie-break at the Australian Open in 2018 and at Roland Garros in 2017-2021."""
    if slam == "AO":
        return "tb10" if year >= 2019 else ("tb" if qual and year == 2018 else "adv")
    if slam == "RG":
        return "tb10" if year >= 2022 else ("tb" if qual and year >= 2017 else "adv")
    if slam == "W":
        return "tb10" if year >= 2022 else ("tb12" if year >= 2019 else "adv")
    return "tb"


def candidates(ctx: dict) -> list[Rules]:
    """The rules to try, most likely first. ctx: best_of (int or None), best_of_certain (bool: from Stage 0), format
    (Stage 0's "standard", "match_tiebreak", "short_sets", or None), slam (AO/RG/W/USO or None), qual, year, level.

    With Stage 0's context (best_of_certain) the candidates are only the rules that can apply: a tour, Challenger or
    ITF match in standard format is replayed under 7-point tie-breaks in every set and nothing else, so a broken
    sequence cannot be rescued by an unusual rule; a Slam may fall back on the other Slam deciding-set rules and a
    team event on any (Davis Cup, Fed Cup, Olympics and others changed rules over the years). Without Stage 0's context
    (an unlinked match) everything is tried."""
    bo = int(ctx.get("best_of") or 3)
    fmt = ctx.get("format") or "standard"
    slam = ctx.get("slam")
    qual = bool(ctx.get("qual"))
    year = int(ctx.get("year") or 0)
    level = ctx.get("level") or ""
    certain = bool(ctx.get("best_of_certain"))
    out: list[Rules] = []
    if fmt == "short_sets":
        out += [Rules(bo, "tb", 4, 3, True), Rules(bo, "tb", 4, 3, False)]
    elif fmt == "match_tiebreak":
        out += [Rules(bo, "mtb10"), Rules(bo, "tb")]
    elif slam:
        out.append(Rules(bo, slam_final(slam, year, qual)))
        out += [Rules(bo, f) for f in ("tb10", "adv", "tb12", "tb")]
    elif level == "TEAM":
        out.append(Rules(bo, "adv" if year < 2016 else "tb"))
        out += [Rules(bo, f) for f in ("tb", "adv", "tb10", "mtb10")]
    else:
        out.append(Rules(bo, "tb"))
    if not certain:
        out += [Rules(bo, f) for f in ("tb", "tb10", "adv", "tb12", "mtb10")]
        other = 5 if bo == 3 else 3
        out += [Rules(other, f) for f in ("tb", "adv", "tb10", "tb12")]
        out += [Rules(5, "tb", 4, 3, True), Rules(3, "tb", 4, 3, True)]
    seen, uniq = set(), []
    for r in out:
        if r not in seen:
            seen.add(r)
            uniq.append(r)
    return uniq


def replay_match(winners, ctx: dict) -> Replay:
    cands = candidates(ctx)
    first = None
    partial = None
    for k, r in enumerate(cands):
        res = replay(winners, r)
        res.rule, res.primary, res.tried = r, k == 0, k + 1
        if first is None:
            first = res
        if res.status == "complete":
            return res
        if res.status == "partial" and partial is None:
            partial = res
    if first.status == "partial":
        return first
    return partial if partial is not None else first


def boundary_mismatches(derived: np.ndarray, labels: np.ndarray, stop: int) -> int:
    """How many points, among the first ``stop``, start a new game in one partition and not in the other (labels: the
    source's own game key per point; derived: the replay's game index)."""
    if stop <= 1:
        return 0
    d = np.asarray(derived[:stop])
    s = np.asarray(labels[:stop])
    return int(((d[1:] != d[:-1]) != (s[1:] != s[:-1])).sum())


def score_text(sets: list, games: tuple = (0, 0), first_is: int = 1, partial: bool = False) -> str:
    """Set scores from player ``first_is``'s side ('6-4 7-6(5)'; a match tie-break as '[10-8]'), with the games of an
    unfinished set appended when ``partial``."""
    out = []
    for g1, g2, t1, t2 in sets:
        a, b, ta, tb = (g1, g2, t1, t2) if first_is == 1 else (g2, g1, t2, t1)
        if (a + b) == 1 and ta is not None and max(ta, tb) >= 10:
            out.append(f"[{ta}-{tb}]")
            continue
        s = f"{a}-{b}"
        if ta is not None:
            s += f"({min(ta, tb)})"
        out.append(s)
    if partial and (games[0] or games[1]):
        a, b = games if first_is == 1 else (games[1], games[0])
        out.append(f"{a}-{b}")
    return " ".join(out)
