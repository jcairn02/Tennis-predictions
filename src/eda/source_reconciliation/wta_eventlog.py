"""The chair umpire's event log of a WTA singles match replayed point by point, with the umpire's corrections undone,
and the nine box-score counts recounted from it (pure functions; the reader is wta_events_recount.py).

The log (batches B1/B2, staged as data/dump/points/wta/events/<year>.parquet) is the umpire device's stream of actions.
Vocabulary, as observed on the staged tables (16 Oct 2026; docs/studies/official_point_feeds/README.md describes the
same documents):
    * type (Attributes.type; Name where type is blank: in two Brisbane 2020 logs Name is shifted by one record):
      Point, Ace, Fault, Foot, Let, StateIndicator (reason: Correction, InProgress, OnCourt, Warmup, ...), challenges,
      violations, medical, suspensions, swaps of server or receiver.
    * a point ends with a Point, an Ace, a Fault whose first_serve is not TRUE (a double fault), or, in 2019-2021, a
      Foot whose first_serve is not TRUE (a foot fault on the second serve, i.e. a double fault: the score moves to
      the receiver). A Fault or Foot with first_serve TRUE is a first-serve fault and ends nothing; a Let ends nothing.
    * first_serve on a Point or an Ace: TRUE = played on the first serve; FALSE (from 2022) or blank (2019-2021) = on
      the second serve. Points re-entered during a correction carry it too, often without the faults before them.
    * score: the score after the point, the server's count first in a regular game (0/15/30/40, "deuce",
      "advantage in" = the server's, "advantage out", "game"). In a tiebreak: two numbers, with the tiebreak's first
      server first (2019-2020) or each point's server first (2021 on); from 2022 nearly every tiebreak point is written
      "0-0" (unwritten), only its last record carrying a score, if any.
    * match_score (from mid-2021): the device's games after the point in A/B order ("6-2,6-7(3),0-0", the loser's
      tiebreak points in brackets); game_score its game score. A StateIndicator InProgress after a Correction carries
      the state the correction left.
    * a StateIndicator Correction opens an edit: the umpire may undo one or more points, back into an earlier game or
      set, and re-enter points (records stamped seconds apart, match_state "E"). Most corrections only precede a let.

How the log is read (this module):
    * the match is replayed under WTA singles rules (advantage games, sets to six by two, a 7-point tiebreak at 6-6 in
      every set; best of three). Each point record must follow from the replayed state: its server is the game's
      server (in a tiebreak, the first server and then every two points the other player), and its score text (and
      match_score where present) is what the replay gives after the point;
    * a Correction opens an edit that the next InProgress closes. The edit is read as a whole: the latest rewind
      (points removed, latest first, at most REWIND_LIMIT back) from which every point re-entered in the edit follows
      and after which the state equals the InProgress's (match_score and game score, where the log has them). Only if
      no rewind allows that may the edit also undo its own entries (1107/2024/LS026 re-enters 15-30, then 30-15).
      A Correction without a closing InProgress falls back to rewinding record by record: a record that does not
      follow rewinds until it does. An InProgress with no Correction before it whose state is one to three points
      back is a silent undo (1051/2024/LS008) and rewinds too. Nothing else is ever removed;
    * a record that follows from no state (no correction pending) is skipped and counted; three in a row resynchronise
      the replay on the record's own match_score and game score (2021 on), counted too. Either makes the recount
      incomplete;
    * tiebreak points are collected, then resolved when the tiebreak ends: written scores give each point's winner
      under the orientation that makes every step a one-point step (the server's count first, the next point's
      server's, the first server's: as official_point_feeds/verify_wta.tiebreak_orientation); unwritten points have no
      known winner (aces and double faults excepted). The tiebreak's winner comes from match_score, else the written
      last score, else the last point's known winner; its score from match_score, else from the written score, else
      from its number of points (n <= 12: 7 and n-7; n > 12: n/2+1 and n/2-1);
    * break point: a point of a regular game at which the receiver would win the game by winning it (receiver at 40 or
      advantage); never a tiebreak point.

Counts per player (that player's serve): svpt points served (double faults included); ace; df; first_in points
played on the first serve (aces included; first_serve_in gives the rule); first_won / second_won points won on the
first / second serve (a double fault is a second-serve point lost); sv_won serve points won; sv_gms regular service
games started (completed, plus the one in progress at a retirement, as Sackmann and the API's box count them;
tiebreaks not counted); bp_faced / bp_saved. first_won, second_won and sv_won are NaN for both players when any point
of the match has no known winner (unwritten tiebreak points); first_in, first_won and second_won are NaN when the log
records no serve numbers (serve_number_recorded).

Self-test: ./python.sh src/eda/source_reconciliation/wta_eventlog.py --selftest
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field

LADDER = ("0", "15", "30", "40")
WORDS = {"deuce", "advantage in", "advantage out", "game"}
REWIND_LIMIT = 80
RESYNC_AFTER = 3
NUM_PAIR = re.compile(r"^(\d+)-(\d+)$")
MS_SET = re.compile(r"^(\d+)-(\d+)(?:\((\d+)\))?$")


def other(side: str) -> str:
    return "B" if side == "A" else "A"


# ------------------------------------------------------------------------------------------------ records
@dataclass
class Rec:
    pos: int            # position in the sorted log
    index: int
    kind: str           # ace, point, df, foot_df, ff (first-serve fault), corr, inprog
    side: str | None    # the server's side for scoring records
    first_serve: bool
    score: str          # lower-cased, stripped
    game_score: str
    match_score: str
    state: str          # match_state (P, E, ...)


def record_kind(typ, reason, first_serve) -> str | None:
    t = "" if typ is None else str(typ)
    fs = str(first_serve).upper() == "TRUE"
    if t == "Ace":
        return "ace"
    if t == "Point":
        return "point"
    if t == "Fault":
        return "ff" if fs else "df"
    if t == "Foot":
        return "ff" if fs else "foot_df"
    if t == "StateIndicator":
        r = "" if reason is None else str(reason)
        return "corr" if r == "Correction" else "inprog" if r == "InProgress" else None
    if t == "Overrule":
        return "overrule"
    if t == "Let":
        return "let"
    if t == "Challenge" and str(reason) == "CallerWonChallenge":
        return "chal_won"
    return None


def _txt(v) -> str:
    if v is None:
        return ""
    s = str(v).strip().lower()
    return "" if s in ("nan", "none") else s


# ------------------------------------------------------------------------------------------------ state
@dataclass(frozen=True)
class St:
    sets: tuple = ()          # ((games A, games B, loser's tiebreak points or None), ...)
    ga: int = 0
    gb: int = 0
    pa: int = 0               # points in a regular game, A/B
    pb: int = 0
    srv: str | None = None    # server of the current regular game; in a tiebreak, its first server
    tb: bool = False
    tbn: int = 0              # tiebreak points so far
    over: bool = False


def sets_won(sets) -> tuple[int, int]:
    a = sum(1 for s in sets if s[0] > s[1])
    return a, len(sets) - a


def regular_text(srv_pts: int, rcv_pts: int) -> str:
    if srv_pts >= 3 and rcv_pts >= 3:
        return "deuce" if srv_pts == rcv_pts else "advantage in" if srv_pts > rcv_pts else "advantage out"
    return f"{LADDER[srv_pts]}-{LADDER[rcv_pts]}"


def render_ms(st: St) -> str:
    parts = [f"{a}-{b}" + (f"({t})" if t is not None else "") for a, b, t in st.sets]
    if not st.over:
        parts.append(f"{st.ga}-{st.gb}")
    return ",".join(parts)


def ms_equal(text: str, st: St) -> bool:
    """A match_score text against a state. At the start of a set the device writes the new set as ",0-0" from 2022
    and leaves it out in 2021 ("7-6(5),2-6" on a set's last point); both are accepted."""
    full = render_ms(st)
    if text == full:
        return True
    return (not st.over and st.sets and st.ga == 0 and st.gb == 0 and st.pa == 0 and st.pb == 0
            and full.endswith(",0-0") and text == full[:-4])


def render_game(st: St) -> str:
    """The game score text a state shows (as an InProgress record writes it): "0-0" at a game's start and in an
    unwritten tiebreak; the server's count first in a regular game."""
    if st.tb or st.srv is None:
        return "0-0"
    sp, rp = (st.pa, st.pb) if st.srv == "A" else (st.pb, st.pa)
    return regular_text(sp, rp)


def end_game(st: St, winner: str) -> St:
    ga, gb = st.ga + (winner == "A"), st.gb + (winner == "B")
    sets, over = st.sets, False
    if (ga >= 6 or gb >= 6) and abs(ga - gb) >= 2:
        sets = sets + ((ga, gb, None),)
        ga = gb = 0
        over = max(sets_won(sets)) >= 2
    tb = ga == 6 and gb == 6
    return St(sets, ga, gb, 0, 0, other(st.srv), tb, 0, over)


def close_tiebreak(st: St, winner: str, loser_points: int | None) -> St:
    ga, gb = (7, 6) if winner == "A" else (6, 7)
    sets = st.sets + ((ga, gb, loser_points),)
    over = max(sets_won(sets)) >= 2
    return St(sets, 0, 0, 0, 0, other(st.srv), False, 0, over)


def tb_server(first: str, k: int) -> str:
    return first if ((k + 1) // 2) % 2 == 0 else other(first)


def tb_score_from_count(n: int) -> tuple[int, int] | None:
    """(winner's, loser's) points of a 7-point tiebreak of n points."""
    if n < 7:
        return None
    if n <= 12:
        return 7, n - 7
    if n % 2:
        return None
    return n // 2 + 1, n // 2 - 1


def num_pair(text: str) -> tuple[int, int] | None:
    m = NUM_PAIR.match(text)
    return (int(m.group(1)), int(m.group(2))) if m else None


def parse_ms(text: str):
    """match_score text -> (completed sets, current games) or None."""
    if not text:
        return None
    parts = text.split(",")
    sets = []
    for p in parts:
        m = MS_SET.match(p.strip())
        if not m:
            return None
        sets.append((int(m.group(1)), int(m.group(2)), int(m.group(3)) if m.group(3) else None))
    return sets


# ------------------------------------------------------------------------------------------------ one point
@dataclass
class Pt:
    srv: str
    kind: str                 # ace, point, df
    first_serve: bool         # first serve in (aces and points); False for double faults
    win: str | None
    tb: bool
    bp: bool                  # a break point (regular game; receiver one point from the game)
    set_no: int
    rec_pos: int
    text: str = ""
    tb_k: int = -1
    tb_id: int = -1
    flag_fs: bool = False     # the record's own first_serve flag (TRUE)
    fault_before: bool = False    # a first-serve fault record since the last point, with no correction since
    fault_any: bool = False       # a first-serve fault record since the last point, corrections or not
    overrule_after: bool = False  # an Overrule or a won challenge between that fault and the point


def regular_candidates(st: St, r: Rec) -> list[tuple[str, St, bool]]:
    """(winner, state after, break point) for each winner under which the regular-game record r follows from st."""
    if st.over or st.tb:
        return []
    if st.srv is not None and r.side != st.srv:
        return []
    srv = st.srv or r.side
    base = St(st.sets, st.ga, st.gb, st.pa, st.pb, srv, False, 0, False)
    sp, rp = (base.pa, base.pb) if srv == "A" else (base.pb, base.pa)
    bp = rp >= 3 and rp > sp
    kind = "df" if r.kind == "foot_df" else r.kind
    winners = [srv] if kind == "ace" else [other(srv)] if kind == "df" else [srv, other(srv)]
    out = []
    for w in winners:
        pa, pb = base.pa + (w == "A"), base.pb + (w == "B")
        if (pa >= 4 or pb >= 4) and abs(pa - pb) >= 2:
            after = end_game(base, "A" if pa > pb else "B")
            text = "game"
        else:
            after = St(base.sets, base.ga, base.gb, pa, pb, srv, False, 0, False)
            s2, r2 = (pa, pb) if srv == "A" else (pb, pa)
            text = regular_text(s2, r2)
        if r.score and r.score != text:
            continue
        if r.match_score and not ms_equal(r.match_score, after):
            continue
        out.append((w, after, bp))
    return out


def tb_reachable(x: int, y: int) -> bool:
    hi, lo = max(x, y), min(x, y)
    return hi <= 7 or hi - lo <= 2


def tiebreak_check(st: St, r: Rec):
    """Whether tiebreak record r follows from st. Returns None, or a dict: final (the tiebreak ends with r), winner and
    loser_points when match_score or the record says so, written (the pair, if written)."""
    if st.over or not st.tb:
        return None
    if r.side != tb_server(st.srv, st.tbn):
        return None
    info = {"final": False, "winner": None, "loser_points": None, "written": None}
    if r.score in ("", "0-0"):
        pass
    elif r.score == "game":
        info["final"] = True
    else:
        pair = num_pair(r.score)
        if pair is None or sum(pair) != st.tbn + 1 or not tb_reachable(*pair):
            return None
        info["written"] = pair
        if max(pair) >= 7 and abs(pair[0] - pair[1]) >= 2:
            info["final"] = True
    if r.match_score:
        pre = render_ms(st)
        if r.match_score != pre:
            # the device closed the set on this record: it is the tiebreak's last point
            ms = parse_ms(r.match_score)
            n_done = len(st.sets)
            if ms is None or len(ms) < n_done + 1 or [tuple(s) for s in ms[:n_done]] != [tuple(s) for s in st.sets]:
                return None
            a, b, t = ms[n_done]
            if (a, b) not in ((7, 6), (6, 7)):
                return None
            rest = ms[n_done + 1:]
            if rest and not (len(rest) == 1 and rest[0][:2] == (0, 0)):
                return None
            info.update(final=True, winner="A" if a > b else "B", loser_points=t)
    return info


# ------------------------------------------------------------------------------------------------ the replay
@dataclass
class Replay:
    st: St = field(default_factory=St)
    pts: list = field(default_factory=list)
    snaps: list = field(default_factory=list)     # state before each point
    tb_open: list = field(default_factory=list)   # positions in pts of the open tiebreak's points
    tb_count: int = 0
    tb_results: list = field(default_factory=list)
    flags: dict = field(default_factory=lambda: {"skipped": 0, "resynced": 0, "rewinds": 0, "rewound_points": 0,
                                                  "inprogress_rewinds": 0, "inprogress_unmatched": 0,
                                                  "foot_ignored": 0, "after_end": 0, "server_unknown": 0,
                                                  "tb_unresolved": 0, "tb_count_mismatch": 0, "max_rewind": 0})

    # -- applying a record
    def accept_regular(self, r: Rec, w: str, after: St, bp: bool) -> None:
        kind = "df" if r.kind == "foot_df" else r.kind
        self.snaps.append(self.st)
        self.pts.append(Pt(srv=self.st.srv or r.side, kind=kind, first_serve=r.first_serve and kind != "df", win=w,
                           tb=False, bp=bp, set_no=len(self.st.sets) + 1, rec_pos=r.pos, text=r.score))
        self.st = after

    def accept_tb(self, r: Rec, info: dict) -> None:
        kind = "df" if r.kind == "foot_df" else r.kind
        srv = r.side
        win = srv if kind == "ace" else other(srv) if kind == "df" else None
        self.snaps.append(self.st)
        self.pts.append(Pt(srv=srv, kind=kind, first_serve=r.first_serve and kind != "df", win=win, tb=True, bp=False,
                           set_no=len(self.st.sets) + 1, rec_pos=r.pos, text=r.score, tb_k=self.st.tbn,
                           tb_id=self.tb_count))
        self.tb_open.append(len(self.pts) - 1)
        st = self.st
        self.st = St(st.sets, st.ga, st.gb, 0, 0, st.srv, True, st.tbn + 1, False)
        if info["final"]:
            self.resolve_tb(info["winner"], info["loser_points"])

    def resolve_tb(self, winner: str | None, loser_points: int | None) -> bool:
        """Close the open tiebreak: per-point winners from its written scores, its winner and score. Returns False when
        its winner cannot be known (the replay then stops being able to follow)."""
        idx = self.tb_open
        recs = [self.pts[i] for i in idx]
        written = [num_pair(p.text) if p.text not in ("", "0-0", "game") else None for p in recs]
        first = self.st.srv
        conv_winners = None
        if all(w is not None for w in written) and written:
            best = None
            for how in ("server", "next", "first"):
                prev, ok, wins = (0, 0), 0, []
                for i, (p, pair) in enumerate(zip(recs, written)):
                    if how == "server":
                        lead = p.srv
                    elif how == "first":
                        lead = first
                    else:
                        lead = recs[i + 1].srv if i + 1 < len(recs) else None
                    if lead is None:   # "next" at the last point: the orientation that makes a one-point step
                        cands = [x for x in ("A", "B") if _step(prev, pair if x == "A" else pair[::-1]) is not None]
                        lead = cands[0] if len(cands) == 1 else None
                    if lead is None:
                        wins.append(None)
                        continue
                    ab = pair if lead == "A" else (pair[1], pair[0])
                    s = _step(prev, ab)
                    ok += s is not None
                    wins.append(s)
                    prev = ab
                if best is None or ok > best[0]:
                    best = (ok, how, wins, prev)
            ok, how, wins, final_pair = best
            if ok == len(recs):
                conv_winners = wins
                if winner is None and max(final_pair) >= 7 and abs(final_pair[0] - final_pair[1]) >= 2:
                    winner = "A" if final_pair[0] > final_pair[1] else "B"
                if loser_points is None and winner is not None:
                    loser_points = min(final_pair)
        if conv_winners is not None:
            for i, w in zip(idx, conv_winners):
                if self.pts[i].win is not None and self.pts[i].win != w:
                    conv_winners = None
                    break
            if conv_winners is not None:
                for i, w in zip(idx, conv_winners):
                    self.pts[i].win = w
        if winner is None:
            last = self.pts[idx[-1]] if idx else None
            winner = last.win if last is not None else None
        if winner is None:
            return False
        by_count = tb_score_from_count(len(idx))
        if loser_points is None and by_count is not None:
            loser_points = by_count[1]
        if by_count is None or loser_points != by_count[1]:
            self.flags["tb_count_mismatch"] += 1
        self.tb_results.append({"tb_id": self.tb_count, "first_idx": idx[0] if idx else -1,
                                "last_idx": idx[-1] if idx else -1, "points": len(idx), "winner": winner,
                                "loser_points": loser_points, "first": first,
                                "winners_known": all(self.pts[i].win is not None for i in idx)})
        self.st = close_tiebreak(self.st, winner, loser_points)
        self.tb_open = []
        self.tb_count += 1
        return True

    # -- consistency of a record with a state
    def follows(self, st: St, r: Rec):
        """('regular', candidates) or ('tb', info) or ('tb_close_first', ...) when r follows from st; else None."""
        if st.over:
            return None
        if st.tb:
            info = tiebreak_check(st, r)
            if info is not None:
                return ("tb", info)
            return None
        c = regular_candidates(st, r)
        if c:
            return ("regular", c)
        return None

    def try_accept(self, r: Rec) -> bool:
        res = self.follows(self.st, r)
        if res is None and self.st.tb and self.tb_open:
            # the tiebreak may have ended at the record before (unwritten, no match_score): close it with a winner that
            # lets r follow as the next set's first point
            fits = []
            for w in ("A", "B"):
                trial = Replay(st=self.st, pts=[], snaps=[], tb_open=list(self.tb_open))
                trial.pts = self.pts
                saved = [p.win for p in self.pts[-len(self.tb_open):]]
                ok = trial.resolve_tb(w, None)
                after = trial.st
                for p, s in zip(self.pts[-len(self.tb_open):], saved):
                    p.win = s
                if ok and regular_candidates(after, r):
                    fits.append(w)
            if len(fits) == 1:
                self.resolve_tb(fits[0], None)
                res = self.follows(self.st, r)
            elif len(fits) == 2:
                # both winners fit (no match_score): the written scores, else the last point, decide
                if self.resolve_tb(None, None):
                    res = self.follows(self.st, r)
        if res is None:
            return False
        if res[0] == "regular":
            cands = res[1]
            if len(cands) != 1:
                return False
            w, after, bp = cands[0]
            self.accept_regular(r, w, after, bp)
        else:
            self.accept_tb(r, res[1])
        return True

    def rewind_to(self, k: int) -> None:
        """Remove the points from position k on; the state is the one before point k. A tiebreak closed by a removed
        point is open again: its points are the last st.tbn points kept, their winners back to what their kind says."""
        dropped = len(self.pts) - k
        self.st = self.snaps[k]
        del self.pts[k:]
        del self.snaps[k:]
        self.flags["rewound_points"] += dropped
        self.flags["max_rewind"] = max(self.flags["max_rewind"], dropped)
        self.tb_results = [t for t in self.tb_results if t["last_idx"] < k]
        self.tb_count = len(self.tb_results)
        self.tb_open = list(range(k - self.st.tbn, k)) if self.st.tb else []
        for i in self.tb_open:
            p = self.pts[i]
            p.win = p.srv if p.kind == "ace" else other(p.srv) if p.kind == "df" else None
            p.tb_id = self.tb_count

    def rewind_search(self, r: Rec) -> bool:
        n = len(self.pts)
        for k in range(n - 1, max(-1, n - REWIND_LIMIT - 1), -1):
            st = self.snaps[k]
            if self.follows(st, r) is not None:
                self.rewind_to(k)
                self.flags["rewinds"] += 1
                return self.try_accept(r)
        return False

    def inprogress(self, r: Rec) -> None:
        target_g, target_m = r.game_score, r.match_score
        if not target_m:
            return
        if ms_equal(target_m, self.st) and (not target_g or render_game(self.st) == target_g or self.st.tb):
            return
        n = len(self.pts)
        for k in range(n - 1, max(-1, n - REWIND_LIMIT - 1), -1):
            st = self.snaps[k]
            if ms_equal(target_m, st) and (not target_g or render_game(st) == target_g or st.tb):
                self.rewind_to(k)
                self.flags["inprogress_rewinds"] += 1
                return
        self.flags["inprogress_unmatched"] += 1

    def resync(self, r: Rec) -> bool:
        """Put the replay on the record's own match_score and game score (the state after it), counting the record as
        a point with no known winner."""
        ms = parse_ms(r.match_score)
        if ms is None or r.side is None:
            return False
        done, cur = ms[:-1], ms[-1]
        if cur[2] is not None:
            return False
        ga, gb = cur[0], cur[1]
        if r.score == "game":
            st = St(tuple(tuple(s) for s in done), ga, gb, 0, 0, other(r.side), ga == 6 and gb == 6, 0, False)
        elif ga == 6 and gb == 6:
            return False
        else:
            m = re.match(r"^(0|15|30|40)-(0|15|30|40)$", r.score)
            if r.score == "deuce":
                sp, rp = 3, 3
            elif r.score == "advantage in":
                sp, rp = 4, 3
            elif r.score == "advantage out":
                sp, rp = 3, 4
            elif m:
                sp, rp = LADDER.index(m.group(1)), LADDER.index(m.group(2))
            else:
                return False
            pa, pb = (sp, rp) if r.side == "A" else (rp, sp)
            st = St(tuple(tuple(s) for s in done), ga, gb, pa, pb, r.side, False, 0, False)
        kind = "df" if r.kind == "foot_df" else r.kind
        win = r.side if kind == "ace" else other(r.side) if kind == "df" else None
        self.snaps.append(self.st)
        self.pts.append(Pt(srv=r.side, kind=kind, first_serve=r.first_serve and kind != "df", win=win, tb=False,
                           bp=False, set_no=len(st.sets) + 1, rec_pos=r.pos, text=r.score))
        self.st = st
        self.tb_open = []
        self.flags["resynced"] += 1
        return True


def _step(prev: tuple[int, int], now: tuple[int, int]) -> str | None:
    if now == (prev[0] + 1, prev[1]):
        return "A"
    if now == (prev[0], prev[1] + 1):
        return "B"
    return None


SCORING = ("ace", "point", "df", "foot_df")
EPISODE_MAX = 60          # records after a Correction searched for the InProgress that ends its edit
INPROG_NOCORR_LIMIT = 3   # points an InProgress with no Correction before it may undo


def episode_end(records: list[Rec], i: int) -> int | None:
    """The position of the InProgress that ends the edit opened by the Correction at records[i]: the records between
    are the edit (re-entered points, lets, faults, further corrections). A point record in normal play (match_state
    other than "E") before any InProgress means the edit has no closing record: None."""
    for j in range(i + 1, min(len(records), i + 1 + EPISODE_MAX)):
        r = records[j]
        if r.kind == "inprog":
            return j
        if r.kind in SCORING and r.state != "E":
            return None
    return None


def state_matches(st: St, target: Rec) -> bool:
    if not target.match_score:
        return True
    if not ms_equal(target.match_score, st):
        return False
    return not target.game_score or st.tb or render_game(st) == target.game_score


def sim_from(rp: Replay, k: int) -> Replay:
    """A scratch replay that starts from the state before point k (k = len(pts): the current state), holding copies of
    the open tiebreak's points so that it can close it."""
    st = rp.snaps[k] if k < len(rp.pts) else rp.st
    sim = Replay(st=st)
    if st.tb and st.tbn:
        sim.pts = []
        for p in rp.pts[k - st.tbn:k]:
            q = Pt(**{f: getattr(p, f) for f in p.__dataclass_fields__})
            q.win = q.srv if q.kind == "ace" else other(q.srv) if q.kind == "df" else None
            sim.pts.append(q)
        sim.snaps = [st] * len(sim.pts)
        sim.tb_open = list(range(len(sim.pts)))
    return sim


def replay(records: list[Rec], start: Replay | None = None) -> Replay:
    """Replay a match's records (sorted by index), from the start of the match or from ``start`` (tests). See the
    module docstring for the rules."""
    rp = start or Replay()
    for k in ("episodes", "episode_rewinds", "episode_fallback", "inprogress_rewinds_nocorr"):
        rp.flags[k] = 0
    pending = False
    misses = 0
    fault, fault_any, overrule = False, False, False

    def mark(r: Rec) -> None:
        nonlocal fault, fault_any, overrule
        p = rp.pts[-1]
        p.flag_fs = r.first_serve
        p.fault_before, p.fault_any, p.overrule_after = fault, fault_any, overrule and fault_any
        fault, fault_any, overrule = False, False, False

    def side_record(r: Rec) -> bool:
        """Faults, lets, overrules: True when r is one of them (handled)."""
        nonlocal fault, fault_any, overrule
        if r.kind == "ff":
            fault, fault_any, overrule = True, True, False
            return True
        if r.kind == "let":
            return True
        if r.kind in ("overrule", "chal_won"):
            overrule = True
            return True
        return False

    def take(rr: Replay, r: Rec, floor: int) -> bool:
        """Accept r on rr, or after undoing points re-entered in this edit (positions >= floor): an edit can undo its
        own entries with no Correction record of its own (1107/2024/LS026: re-entered 15-30, then 30-15)."""
        if rr.try_accept(r):
            return True
        for q in range(len(rr.pts) - 1, floor - 1, -1):
            if rr.follows(rr.snaps[q], r) is not None:
                rr.rewind_to(q)
                rr.flags["edit_self_undo"] = rr.flags.get("edit_self_undo", 0) + 1
                return rr.try_accept(r)
        return False

    def episode(i: int, j: int) -> bool:
        """The edit records[i+1:j] closed by the InProgress records[j]: the latest rewind from which every re-entered
        point follows (allowing the edit to undo its own entries) and the state reaches the InProgress's. Committed
        when found."""
        nonlocal fault
        epi = records[i + 1:j]
        target = records[j]
        scoring = [r for r in epi if r.kind in SCORING and r.side is not None]
        n = len(rp.pts)
        # first every re-entered point must follow as it comes; only if no rewind allows that may the edit undo its
        # own entries
        for self_undo in (False, True):
            for k in range(n, max(-1, n - REWIND_LIMIT - 1), -1):
                sim = sim_from(rp, k)
                floor = len(sim.pts) if self_undo else 10 ** 9
                if not all(take(sim, r, floor) for r in scoring):
                    continue
                if not state_matches(sim.st, target):
                    continue
                if k < n:
                    rp.rewind_to(k)
                    rp.flags["episode_rewinds"] += 1
                fault = False
                floor = len(rp.pts) if self_undo else 10 ** 9
                for r in epi:
                    if side_record(r) or r.kind in ("corr", "inprog") or r.kind not in SCORING or r.side is None:
                        if r.kind == "corr":
                            fault = False
                        continue
                    if not take(rp, r, floor):      # not expected: the scratch replay accepted it
                        rp.flags["skipped"] += 1
                        rp.flags["episode_commit_failed"] = rp.flags.get("episode_commit_failed", 0) + 1
                        continue
                    mark(r)
                return True
        return False

    i = 0
    while i < len(records):
        r = records[i]
        i += 1
        if side_record(r):
            continue
        if r.kind == "corr":
            fault = False
            j = episode_end(records, i - 1)
            if j is not None:
                rp.flags["episodes"] += 1
                if episode(i - 1, j):
                    pending = False
                    misses = 0
                    i = j + 1
                    continue
                rp.flags["episode_fallback"] += 1
            pending = True
            continue
        if r.kind == "inprog":
            if pending:
                rp.inprogress(r)
            elif r.match_score and not state_matches(rp.st, r):
                n = len(rp.pts)
                for k in range(n - 1, max(-1, n - INPROG_NOCORR_LIMIT - 1), -1):
                    if state_matches(rp.snaps[k], r):
                        rp.rewind_to(k)
                        rp.flags["inprogress_rewinds_nocorr"] += 1
                        break
            continue
        if r.kind not in SCORING:
            continue
        if r.side is None:
            rp.flags["server_unknown"] += 1
            continue
        if rp.try_accept(r):
            pending = False
            misses = 0
            mark(r)
            continue
        if pending and rp.rewind_search(r):
            pending = False
            misses = 0
            mark(r)
            continue
        if r.kind == "foot_df" and (r.score == render_game(rp.st) or not r.score):
            rp.flags["foot_ignored"] += 1
            continue
        if rp.st.over:
            rp.flags["after_end"] += 1
            continue
        misses += 1
        if misses >= RESYNC_AFTER and rp.resync(r):
            misses = 0
            mark(r)
            continue
        rp.flags["skipped"] += 1
    if rp.st.tb and rp.tb_open:
        # the log ends inside a tiebreak: closed only when its own last record says it ended
        rp.flags["tb_unresolved"] += 1
    return rp


# ------------------------------------------------------------------------------------------------ counts
COUNT_NAMES = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced", "sv_won"]


def first_serve_in(p: Pt, rule: str = "faults") -> bool:
    """Whether point p was played on the first serve.

    rule "faults" (the reading used for the counts): a point is a second-serve point when a first-serve fault record
    (Fault or Foot with first_serve TRUE) stands before it, i.e. one was logged since the previous point with no
    Correction after it; a double fault always is. Chosen on 2024 after comparing with the API's box (observed: in
    matches with a correction the device's own flag on the next point is stale, "Fault, Correction, Let, Point
    first_serve FALSE" being the commonest case, and the box counts that point as a first serve).
    rule "flag": the record's own first_serve flag (TRUE = first serve)."""
    if p.kind == "df":
        return False
    return p.flag_fs if rule == "flag" else not p.fault_before


def serve_number_recorded(rp: Replay, first_serve_faults: int) -> bool:
    """False for a log that does not record serve numbers: no first-serve fault record at all, or most double faults
    with no first-serve fault before them (observed at Brisbane, Canberra and Auckland in the first week of 2024,
    where nearly every point is flagged as played on the first serve)."""
    dfs = [p for p in rp.pts if p.kind == "df"]
    if first_serve_faults == 0:
        return False
    if len(dfs) >= 2 and sum(not p.fault_any for p in dfs) / len(dfs) > 0.5:
        return False
    return True


def counts(rp: Replay, rule: str = "faults", serve_recorded: bool = True) -> dict:
    """Per side (A, B): the nine counts and sv_won, with the diagnostics. first_in, first_won and second_won are None
    when the log does not record serve numbers; first_won, second_won and sv_won are None when any point's winner is
    unknown."""
    out = {s: {c: 0 for c in COUNT_NAMES} for s in ("A", "B")}
    flag = {s: {"first_in": 0, "first_won": 0} for s in ("A", "B")}
    unknown = {"A": 0, "B": 0}
    for p in rp.pts:
        c = out[p.srv]
        c["svpt"] += 1
        if p.kind == "ace":
            c["ace"] += 1
        if p.kind == "df":
            c["df"] += 1
        if p.win == p.srv:
            c["sv_won"] += 1
        if first_serve_in(p, rule):
            c["first_in"] += 1
            if p.win == p.srv:
                c["first_won"] += 1
        else:
            if p.win == p.srv:
                c["second_won"] += 1
        if first_serve_in(p, "flag"):
            flag[p.srv]["first_in"] += 1
            flag[p.srv]["first_won"] += p.win == p.srv
        if p.win is None:
            unknown[p.srv] += 1
        if p.bp:
            c["bp_faced"] += 1
            if p.win == p.srv:
                c["bp_saved"] += 1
    # service games: completed regular games, by their server; a regular game is completed when the state after its
    # last point starts a new game
    games = {"A": 0, "B": 0}
    unfinished = {"A": 0, "B": 0}
    for i, p in enumerate(rp.pts):
        if p.tb:
            continue
        nxt = rp.snaps[i + 1] if i + 1 < len(rp.snaps) else rp.st
        here = rp.snaps[i]
        if (len(nxt.sets), nxt.ga + nxt.gb) != (len(here.sets), here.ga + here.gb):
            games[p.srv] += 1
    st = rp.st
    if not st.over and not st.tb and (st.pa or st.pb) and st.srv is not None:
        unfinished[st.srv] += 1
    for s in ("A", "B"):
        # Sackmann's definition, as observed against Stage 0 and the API's box (both equal completed games + the game
        # in progress at a retirement in 99.9% of rows): a regular service game started counts, a tiebreak does not
        out[s]["sv_gms"] = games[s] + unfinished[s]
        out[s]["x_sv_gms_completed"] = games[s]
    any_unknown = unknown["A"] + unknown["B"] > 0
    tb_first = {"A": sum(1 for t in rp.tb_results if t["first"] == "A"),
                "B": sum(1 for t in rp.tb_results if t["first"] == "B")}
    for s in ("A", "B"):
        out[s]["x_first_won_known"] = out[s]["first_won"] if serve_recorded else None
        out[s]["x_second_won_known"] = out[s]["second_won"] if serve_recorded else None
        out[s]["x_sv_won_known"] = out[s]["sv_won"]
        out[s]["x_first_in_flag"] = flag[s]["first_in"] if serve_recorded else None
        out[s]["x_first_won_flag"] = flag[s]["first_won"] if serve_recorded and not any_unknown else None
        if any_unknown:
            for c in ("first_won", "second_won", "sv_won"):
                out[s][c] = None
        if not serve_recorded:
            for c in ("first_in", "first_won", "second_won"):
                out[s][c] = None
        out[s]["x_unknown_winner_points"] = unknown[s]
        out[s]["x_sv_gms_unfinished"] = unfinished[s]
        out[s]["x_tb_served_first"] = tb_first[s]
    return out


def tb_detail(rp: Replay, rule: str = "faults") -> str:
    """Each tiebreak's points, for checking and for filling unwritten winners from another record: per tiebreak
    "set|servers|serve numbers (1/2)|kinds (a ace, d double fault, p point)|winners (A/B/?)", joined by ";"."""
    out = []
    by_tb: dict[int, list] = {}
    for p in rp.pts:
        if p.tb:
            by_tb.setdefault(p.tb_id, []).append(p)
    for tid in sorted(by_tb):
        pts = by_tb[tid]
        out.append("|".join([str(pts[0].set_no), "".join(p.srv for p in pts),
                             "".join("1" if first_serve_in(p, rule) else "2" for p in pts),
                             "".join(p.kind[0] for p in pts), "".join(p.win or "?" for p in pts)]))
    return ";".join(out)


def final_sets(rp: Replay) -> list[tuple]:
    """Completed sets (A, B, loser's tiebreak points) plus the set in progress (A, B, None) when the match did not end."""
    sets = [tuple(s) for s in rp.st.sets]
    if not rp.st.over and (rp.st.ga or rp.st.gb or rp.st.pa or rp.st.pb or rp.st.tb):
        sets.append((rp.st.ga, rp.st.gb, None))
    return sets


# ------------------------------------------------------------------------------------------------ self-test
def _recs(spec: list[tuple]) -> list[Rec]:
    out = []
    for i, t in enumerate(spec):
        kind, side, fs, score = t[:4]
        ms = t[4] if len(t) > 4 else ""
        gs = t[5] if len(t) > 5 else ""
        out.append(Rec(pos=i, index=i, kind=kind, side=side, first_serve=fs, score=score, game_score=gs,
                       match_score=ms, state="P"))
    return out


def _hold(side: str, ms_before: str, ms_after: str, aces: int = 0) -> list[tuple]:
    seq = []
    for i, s in enumerate(("15-0", "30-0", "40-0")):
        seq.append(("ace" if i < aces else "point", side, True, s, ms_before))
    seq.append(("point", side, True, "game", ms_after))
    return seq


def selftest() -> int:
    # 1. a love hold, then a game won by the receiver with a double fault and a second-serve point
    spec = _hold("A", "0-0", "1-0", aces=1)
    spec += [("ff", "B", True, "0-0"), ("point", "B", False, "0-15", "1-0"), ("df", "B", False, "0-30", "1-0"),
             ("point", "B", True, "0-40", "1-0"), ("point", "B", True, "game", "2-0")]
    rp = replay(_recs(spec))
    c = counts(rp)
    assert rp.st.ga == 2 and rp.st.gb == 0 and not any(rp.flags[k] for k in ("skipped", "resynced")), rp.flags
    assert c["A"]["svpt"] == 4 and c["A"]["ace"] == 1 and c["A"]["first_in"] == 4 and c["A"]["first_won"] == 4
    assert c["B"]["svpt"] == 4 and c["B"]["df"] == 1 and c["B"]["first_in"] == 2 and c["B"]["second_won"] == 0
    assert c["B"]["bp_faced"] == 1 and c["B"]["bp_saved"] == 0 and c["A"]["sv_gms"] == 1 and c["B"]["sv_gms"] == 1
    # 2. a correction that undoes two points and re-enters one (2090/2023/LS015's pattern)
    spec = [("point", "A", True, "15-0", "0-0"), ("point", "A", True, "30-0", "0-0"), ("point", "A", True, "40-0", "0-0"),
            ("point", "A", True, "40-15", "0-0"), ("corr", None, False, ""), ("point", "A", True, "30-15", "0-0"),
            ("point", "A", True, "40-15", "0-0"), ("point", "A", True, "game", "1-0")]
    rp = replay(_recs(spec))
    assert len(rp.pts) == 5 and rp.flags["rewinds"] == 1 and rp.st.ga == 1, (len(rp.pts), rp.flags)
    # 3. a correction with an InProgress state one point back and no re-entry (804/2023/RS014's pattern)
    spec = [("point", "A", True, "0-15", "0-0"), ("point", "A", True, "0-30", "0-0"), ("corr", None, False, ""),
            ("inprog", None, False, "", "0-0", "0-15"), ("point", "A", False, "15-15", "0-0")]
    rp = replay(_recs(spec))
    assert len(rp.pts) == 2 and rp.flags["episode_rewinds"] == 1 and (rp.st.pa, rp.st.pb) == (1, 1), rp.flags
    # 3b. a re-entry that fits without a rewind but whose second re-entered point does not (2088/2024/RS011's
    # unwritten tiebreak): the edit as a whole decides, so the point before the correction is removed
    seq = [("point", tb_server("A", k), True, "0-0", "6-6") for k in range(8)]       # points 0-7: A B B A A B B A
    seq += [("corr", None, False, ""), ("point", "A", False, "0-0", "6-6", ""), ("point", "A", True, "0-0", "6-6", ""),
            ("inprog", None, False, "", "6-6", "0-0"), ("point", "B", True, "game", "7-6(3),0-0")]
    recs = _recs(seq)
    for r in recs:
        if r.kind == "point" and r.match_score == "6-6" and r.pos in (9, 10):
            r.state = "E"
    full = replay(recs, Replay(st=St((), 6, 6, 0, 0, "A", True, 0, False)))
    assert len(full.pts) == 10 and full.st.sets == ((7, 6, 3),) and full.flags["skipped"] == 0, full.flags
    assert [p.rec_pos for p in full.pts][-3:] == [9, 10, 12], [p.rec_pos for p in full.pts]
    # 4. an unwritten tiebreak closed by match_score on its last record
    st = St((), 6, 6, 0, 0, "A", True, 0, False)
    rp = Replay(st=st)
    seq = []
    for k in range(10):
        s = tb_server("A", k)
        seq.append(("point", s, True, "0-0", "6-6" if k < 9 else "6-7(3),0-0"))
    for r in _recs(seq):
        assert rp.try_accept(r), r
    assert rp.st.sets == ((6, 7, 3),) and rp.st.srv == "B" and rp.tb_results[0]["winners_known"] is False
    # 5. a written tiebreak, each point's server first, resolved to its winners
    rp = Replay(st=St((), 6, 6, 0, 0, "A", True, 0, False))
    tb_winners = ["A", "A", "B", "A", "A", "B", "A", "A", "A"]   # 7-2 to A
    a = b = 0
    seq = []
    for k, w in enumerate(tb_winners):
        s = tb_server("A", k)
        a, b = a + (w == "A"), b + (w == "B")
        pair = (a, b) if s == "A" else (b, a)
        seq.append(("point", s, True, f"{pair[0]}-{pair[1]}", ""))
    for r in _recs(seq):
        assert rp.try_accept(r), r
    assert rp.st.sets == ((7, 6, 2),), rp.st
    assert [p.win for p in rp.pts] == tb_winners, [p.win for p in rp.pts]
    # 6. a correction that rewinds into the previous set (2014/2026/RS024's pattern): set 1 at 5-2, A serving game 8;
    # the game is played, set 2 starts, then the umpire undoes back to the start of game 8 and re-enters it
    pre = "5-2"
    rp = Replay(st=St((), 5, 2, 0, 0, "A", False, 0, False))
    spec = [("point", "A", True, "15-0", pre), ("point", "A", True, "15-15", pre), ("point", "A", True, "30-15", pre),
            ("point", "A", True, "40-15", pre), ("point", "A", True, "game", "6-2,0-0"),
            ("point", "B", True, "15-0", "6-2,0-0"), ("point", "B", True, "15-15", "6-2,0-0"),
            ("corr", None, False, ""), ("point", "A", True, "15-0", pre), ("point", "A", True, "30-0", pre),
            ("point", "A", True, "40-0", pre), ("point", "A", True, "40-15", pre), ("point", "A", True, "game", "6-2,0-0")]
    pending = False
    for r in _recs(spec):
        if r.kind == "corr":
            pending = True
            continue
        if not rp.try_accept(r):
            assert pending and rp.rewind_search(r), r
            pending = False
    assert len(rp.pts) == 5 and rp.st.sets == ((6, 2, None),) and rp.flags["rewound_points"] == 7, rp.flags
    print("selftest: all passed")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print(__doc__)
