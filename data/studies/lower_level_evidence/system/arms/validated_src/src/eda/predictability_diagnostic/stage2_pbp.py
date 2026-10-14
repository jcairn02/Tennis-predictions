"""Stage 2 of the predictability diagnostic, optional part: big points in the Grand Slam point-by-point files.

Jeff Sackmann's slam_pointbypoint files (data/dump/points/sackmann_archive/slam_pointbypoint/) hold every point
of most Grand Slam main-draw singles matches of 2011-2024: who served it and who won it. Here each point is
weighted by its importance, how much winning it rather than losing it changes the chance of winning the match,
and each player's record on important points is set against their record on all points of the same match.

    importance   from the score alone: the iid model (stage2_iid.py) with both players at their tour's average
                 serve rate in these files, so a point's weight does not depend on how the match then went.
                 Importance = P(win the match | win this point) - P(win the match | lose it).
    clutch       for one player in one match, on serve: the importance-weighted share of serve points won minus
                 the plain share; the same on return. A player's return points are the opponent's serve points,
                 so in each match one player's return clutch is the other's serve clutch turned over. Under the
                 iid model a point's result does not depend on the score it is played at, but both shares are
                 ratios over a path that the results shape, so the measure is not exactly zero under pure luck:
                 the pure-luck replays below give its benchmark.
    (b)          the result regressed on the points share, then also on the two players' clutch difference
    (d)          split-half correlations of each player's clutch across their matches (players by name), with
                 serve points won as the yardstick
    pure luck    every kept match replayed point by point under the iid model (replay_luck): the same players,
                 format and deciding-set rule, at true serve rates drawn from what the measured ones allow
                 (stage2_anatomy.denoised_rates), scored with the same weights and measures

Each match is replayed point by point from its point winners under its format (men best of five, women best of
three; the Slam's deciding-set rule for the year). A match is kept when the replay agrees with the file at every
point (the set and games after each point, and who serves) and the match ends on its last point.

Writes, in data/studies/predictability_diagnostic/:
    stage2_pbp_points.parquet    one row per point kept: match, score before it, server, winner, importance
    stage2_pbp_players.parquet   one row per player and match: serve and return points, won, and weighted
    stage2_pbp_results.json      everything stage2.md and the report quote

Run after stage2_anatomy.py: ./python.sh src/eda/predictability_diagnostic/stage2_pbp.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage2_anatomy as A  # noqa: E402
from src.eda.predictability_diagnostic import stage2_iid as M  # noqa: E402

PBP = C.DUMP / "points" / "sackmann_archive" / "slam_pointbypoint"
POINTS_OUT = C.OUT / "stage2_pbp_points.parquet"
PLAYERS_OUT = C.OUT / "stage2_pbp_players.parquet"
RESULTS = C.OUT / "stage2_pbp_results.json"
SLAM_FILES = {"ausopen": "Australian Open", "frenchopen": "Roland Garros", "wimbledon": "Wimbledon", "usopen": "US Open"}
POINT_COLS = ["match_id", "_row", "PointWinner", "PointServer", "SetNo", "P1GamesWon", "P2GamesWon", "P1Score", "P2Score"]
TOKENS = {0: "0", 1: "15", 2: "30", 3: "40"}
BEST_OF = {"atp": 5, "wta": 3}
SPLITS = 50
SEED = A.SEED
REPLAYS = 3                              # pure-luck replays for the benchmark
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# One point at a time

def advance(state: tuple, srv1: bool, won1: bool, need: int, final_rule: str) -> tuple:
    """Apply one point to a position.

    state = (sa, sb, ga, gb, x, y, tb, first1): sets, games, points of the current game or tiebreak (player 1
    first), whether a tiebreak is on, and who served the tiebreak's first point. srv1, won1: player 1 served,
    player 1 won. Returns (new state, the games the point left in the set it was played in, whether the match is
    over, whether player 1 serves the next point)."""
    sa, sb, ga, gb, x, y, tb, first1 = state
    tb_at, tb_points = M.SET_RULES[final_rule if sa == sb == need - 1 else M.STANDARD]
    if tb and x + y == 0:
        first1 = srv1
    x, y = (x + 1, y) if won1 else (x, y + 1)
    target = tb_points if tb else 4
    if max(x, y) >= target and abs(x - y) >= 2:              # the game (or tiebreak) is over
        p1 = x > y
        x = y = 0
        ga, gb = (ga + 1, gb) if p1 else (ga, gb + 1)
        shown = (ga, gb)
        if tb or (max(ga, gb) >= 6 and abs(ga - gb) >= 2):    # and the set
            sa, sb = (sa + 1, sb) if ga > gb else (sa, sb + 1)
            next1 = (not first1) if tb else (not srv1)        # after a tiebreak, its first receiver serves
            ga = gb = 0
            tb = False
        elif tb_at is not None and ga == tb_at and gb == tb_at:
            tb, next1 = True, not srv1                         # the tiebreak starts with the next game's server
            first1 = next1
        else:
            next1 = not srv1
    else:
        shown = (ga, gb)
        next1 = (first1 == M._tb_first_serves(x + y)) if tb else srv1
    return (sa, sb, ga, gb, x, y, tb, first1), shown, sa == need or sb == need, next1


# ------------------------------------------------------------------------------------------------
# The chance of winning from any position, under the iid model

class Chances:
    """P(player 1 wins the match) from any position between points, for fixed serve rates p1 and p2.

    Deuce, long tiebreaks and advantage sets close in two-point (or two-game) races, as in stage2_iid; sets are
    independent draws, so the match follows from the set score with stage2_iid's set probabilities."""

    def __init__(self, p1: float, p2: float, best_of: int, final_rule: str):
        self.p1, self.p2, self.final_rule = float(p1), float(p2), final_rule
        self.need = (int(best_of) + 1) // 2
        self.hold1, self.hold2 = float(M.game(self.p1)), float(M.game(self.p2))
        self.set_std = float(M.set_win(self.p1, self.p2, M.STANDARD))
        self.set_final = float(M.set_win(self.p1, self.p2, final_rule))
        self.game_from = lru_cache(maxsize=None)(self._game_from)
        self.tb_from = lru_cache(maxsize=None)(self._tb_from)
        self.set_from = lru_cache(maxsize=None)(self._set_from)
        self.match_from = lru_cache(maxsize=None)(self._match_from)
        self.value = lru_cache(maxsize=None)(self._value)

    def _game_from(self, x: int, y: int, srv1: bool) -> float:
        """P(player 1 wins the current game) from points x (player 1) and y."""
        if x >= 4 and x - y >= 2:
            return 1.0
        if y >= 4 and y - x >= 2:
            return 0.0
        s = self.p1 if srv1 else 1 - self.p2                  # player 1 wins a point of this game
        if x >= 3 and y >= 3:
            deuce = s * s / (s * s + (1 - s) * (1 - s))
            return deuce if x == y else (s + (1 - s) * deuce if x > y else s * deuce)
        return s * self.game_from(x + 1, y, srv1) + (1 - s) * self.game_from(x, y + 1, srv1)

    def _tb_from(self, x: int, y: int, first1: bool, target: int) -> float:
        """P(player 1 wins the tiebreak) from points x and y; first1: player 1 served its first point."""
        if x >= target and x - y >= 2:
            return 1.0
        if y >= target and y - x >= 2:
            return 0.0
        a_srv, b_srv = self.p1, 1 - self.p2
        if x == y and x >= target - 1:                         # each pair of points has one served by each
            return a_srv * b_srv / (a_srv * b_srv + (1 - a_srv) * (1 - b_srv))
        s = a_srv if M._tb_first_serves(x + y) == first1 else b_srv
        return s * self.tb_from(x + 1, y, first1, target) + (1 - s) * self.tb_from(x, y + 1, first1, target)

    def _set_from(self, ga: int, gb: int, next1: bool, rule: str) -> float:
        """P(player 1 wins the set) from the start of a game at games ga, gb; next1: player 1 serves it."""
        tb_at, tb_points = M.SET_RULES[rule]
        if max(ga, gb) >= 6 and abs(ga - gb) >= 2:
            return 1.0 if ga > gb else 0.0
        if tb_at is not None and ga == tb_at and gb == tb_at:
            return self.tb_from(0, 0, next1, tb_points)
        g = self.hold1 if next1 else 1 - self.hold2            # player 1 wins the next game
        if tb_at is None and min(ga, gb) >= 5:
            level = self.hold1 * (1 - self.hold2) / (self.hold1 * (1 - self.hold2) + (1 - self.hold1) * self.hold2)
            if ga == gb:
                return level
            return g + (1 - g) * level if ga > gb else g * level
        return g * self.set_from(ga + 1, gb, not next1, rule) + (1 - g) * self.set_from(ga, gb + 1, not next1, rule)

    def _match_from(self, sa: int, sb: int) -> float:
        if sa == self.need or sb == self.need:
            return 1.0 if sa == self.need else 0.0
        s = self.set_final if sa == sb == self.need - 1 else self.set_std
        return s * self.match_from(sa + 1, sb) + (1 - s) * self.match_from(sa, sb + 1)

    def _value(self, state: tuple, next1: bool) -> float:
        """P(player 1 wins the match) from a position, with player 1 serving the next point or not."""
        sa, sb, ga, gb, x, y, tb, first1 = state
        if sa == self.need or sb == self.need:
            return 1.0 if sa == self.need else 0.0
        rule = self.final_rule if sa == sb == self.need - 1 else M.STANDARD
        if tb:
            p_set = self.tb_from(x, y, first1, M.SET_RULES[rule][1])
        else:
            g = self.game_from(x, y, next1)
            p_set = g * self.set_from(ga + 1, gb, not next1, rule) + (1 - g) * self.set_from(ga, gb + 1, not next1, rule)
        return p_set * self.match_from(sa + 1, sb) + (1 - p_set) * self.match_from(sa, sb + 1)

    def importance(self, state: tuple, srv1: bool) -> float:
        """How much winning the point rather than losing it raises player 1's chance of winning the match."""
        up = advance(state, srv1, True, self.need, self.final_rule)
        down = advance(state, srv1, False, self.need, self.final_rule)
        return self.value(up[0], up[3]) - self.value(down[0], down[3])


START = (0, 0, 0, 0, 0, 0, False, True)


# ------------------------------------------------------------------------------------------------
# Loading and replaying the files

def edition_notes(f: Path) -> dict:
    """What an edition's file writes: blank games columns, the 'GAME' token, and aces by serve number (where the
    file has ServeNumber)."""
    names = pq.read_schema(f).names
    cols = [c for c in ("P1GamesWon", "P2GamesWon", "P1Score", "P2Score", "PointServer", "ServeNumber", "P1Ace", "P2Ace") if c in names]
    q = pd.read_parquet(f, columns=cols)
    srv = pd.to_numeric(q["PointServer"], errors="coerce")
    out = {"games_blank_pct": round(100 * float(pd.to_numeric(q["P1GamesWon"], errors="coerce").isna().mean()), 2),
           "game_token": bool((q["P1Score"].astype(str).str.strip().eq("GAME") | q["P2Score"].astype(str).str.strip().eq("GAME")).any())}
    if {"ServeNumber", "P1Ace", "P2Ace"} <= set(cols):
        ace = np.where(srv == 1, pd.to_numeric(q["P1Ace"], errors="coerce"), np.where(srv == 2, pd.to_numeric(q["P2Ace"], errors="coerce"), np.nan))
        sn = pd.to_numeric(q["ServeNumber"], errors="coerce").to_numpy()
        out["aces_first_serve"], out["aces_second_serve"] = int(np.nansum(ace[sn == 1])), int(np.nansum(ace[sn == 2]))
    return out


def load_points() -> tuple[pd.DataFrame, list]:
    frames, editions = [], []
    for f in sorted(PBP.glob("*-points.parquet")):
        m = re.match(r"(\d{4})-(ausopen|frenchopen|wimbledon|usopen)-points", f.name)
        if not m:
            continue
        p = pd.read_parquet(f, columns=POINT_COLS)
        mt = pd.read_parquet(f.with_name(f.name.replace("-points", "-matches")), columns=["match_id", "player1", "player2"])
        p = p.merge(mt, on="match_id", how="left").assign(year=int(m.group(1)), tournament_name=SLAM_FILES[m.group(2)])
        frames.append(p)
        editions.append({"edition": f"{m.group(1)} {SLAM_FILES[m.group(2)]}", "rows": int(len(p)), "matches": int(p["match_id"].nunique()),
                         **edition_notes(f)})
    p = pd.concat(frames, ignore_index=True)
    for c in ("PointWinner", "PointServer", "SetNo", "P1GamesWon", "P2GamesWon"):
        p[c] = pd.to_numeric(p[c], errors="coerce")
    first = p["match_id"].str.rsplit("-", n=1).str[1].str[0]
    p["tour"] = np.select([first.isin(["1", "M"]), first.isin(["2", "W"])], ["atp", "wta"], "")
    return p, editions


def score_tokens(x: int, y: int, tb: bool) -> tuple[str, str]:
    """How the files write a score in the middle of a game: 0/15/30/40/AD, or tiebreak points."""
    if tb:
        return str(x), str(y)
    if x >= 3 and y >= 3:
        return ("40", "40") if x == y else (("AD", "40") if x > y else ("40", "AD"))
    return TOKENS[x], TOKENS[y]


def replay_all(p: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Replay every match from its point winners and servers; check it against the file.

    The checks, after each point: the set it was played in; the score of the game (or tiebreak) when the point
    did not end it; the games of the set where the file writes them (some editions leave them blank); and the
    server of the next point against the rules. Returns the points of the matches kept (with the position before
    each point) and one status row per match: points, disagreements, whether the match ended on its last point,
    and who won."""
    p = p[p["PointServer"].isin([1, 2]) & p["PointWinner"].isin([1, 2]) & p["tour"].ne("")]
    p = p.sort_values(["match_id", "_row"], kind="mergesort")
    rules = {}
    keep, status = [], []
    for mid, g in p.groupby("match_id", sort=False):
        tour, year, name = g["tour"].iat[0], int(g["year"].iat[0]), g["tournament_name"].iat[0]
        if (name, year) not in rules:
            rules[(name, year)] = M.deciding_set_rule(pd.Series(["GS"]), pd.Series([name]), pd.Series([year]),
                                                      pd.Series([False])).iat[0]
        rule, need = rules[(name, year)], (BEST_OF[tour] + 1) // 2
        srv = g["PointServer"].to_numpy() == 1
        won = g["PointWinner"].to_numpy() == 1
        g1, g2, setno = g["P1GamesWon"].to_numpy(), g["P2GamesWon"].to_numpy(), g["SetNo"].to_numpy()
        s1 = g["P1Score"].astype(str).str.strip().to_numpy()
        s2 = g["P2Score"].astype(str).str.strip().to_numpy()
        state, expect1, over = START, None, False
        rows, games_bad, score_bad, server_bad, early = [], 0, 0, 0, False
        for i in range(len(g)):
            if over:
                early = True
                break
            if expect1 is not None and expect1 != bool(srv[i]):
                server_bad += 1
            set_no = state[0] + state[1] + 1
            rows.append((i, state, bool(srv[i]), bool(won[i]), set_no))
            in_tb = state[6]
            state, shown, over, expect1 = advance(state, bool(srv[i]), bool(won[i]), need, rule)
            if setno[i] != set_no or (not np.isnan(g1[i]) and not np.isnan(g2[i]) and shown != (g1[i], g2[i])):
                games_bad += 1
            if state[4] + state[5] > 0 and (s1[i], s2[i]) != score_tokens(state[4], state[5], in_tb):
                score_bad += 1
        ok = over and not early and games_bad == 0 and score_bad == 0 and server_bad == 0
        status.append({"match_id": mid, "tour": tour, "year": year, "tournament_name": name, "rule": rule, "points": int(len(g)),
                       "games_disagree": int(games_bad), "score_disagree": int(score_bad), "server_disagree": int(server_bad),
                       "ended_on_last_point": bool(over and not early),
                       "kept": bool(ok), "p1_won": bool(state[0] > state[1]) if over else None,
                       "player1": g["player1"].iat[0], "player2": g["player2"].iat[0]})
        if ok:
            for i, st, s1, w1, set_no in rows:
                keep.append((mid, tour, set_no, *st, s1, w1))
    cols = ["match_id", "tour", "set_no", "sa", "sb", "ga", "gb", "x", "y", "tb", "first1", "srv1", "won1"]
    return pd.DataFrame(keep, columns=cols), pd.DataFrame(status)


def add_importance(pts: pd.DataFrame, status: pd.DataFrame, rate: dict) -> pd.DataFrame:
    """Each point's importance, with both players at the tour's average serve rate."""
    rule = status.set_index("match_id")["rule"]
    imp = np.empty(len(pts))
    chances: dict = {}
    states = list(zip(pts["sa"], pts["sb"], pts["ga"], pts["gb"], pts["x"], pts["y"], pts["tb"], pts["first1"]))
    for i, (mid, tour, st, s1) in enumerate(zip(pts["match_id"], pts["tour"], states, pts["srv1"])):
        key = (tour, rule[mid])
        if key not in chances:
            chances[key] = Chances(rate[tour], rate[tour], BEST_OF[tour], rule[mid])
        imp[i] = chances[key].importance(tuple(int(v) if not isinstance(v, (bool, np.bool_)) else bool(v) for v in st), bool(s1))
    pts = pts.assign(importance=imp)
    srv_pts = np.where(pts["srv1"], pts["x"], pts["y"])
    rcv_pts = np.where(pts["srv1"], pts["y"], pts["x"])
    pts["break_point"] = ~pts["tb"] & (rcv_pts >= 3) & (rcv_pts > srv_pts)
    return pts


# ------------------------------------------------------------------------------------------------
# The pure-luck replay, point by point

SURFACE = {"Australian Open": "Hard", "Roland Garros": "Clay", "Wimbledon": "Grass", "US Open": "Hard"}


def measured(pts: pd.DataFrame, status: pd.DataFrame) -> pd.DataFrame:
    """Per kept match: each player's serve points and the share won, with the tour and the surface."""
    srv_won = pts["srv1"] == pts["won1"]
    g = pd.DataFrame({"match_id": pts["match_id"], "s1": pts["srv1"].astype(int), "w1": (pts["srv1"] & srv_won).astype(int),
                      "s2": (~pts["srv1"]).astype(int), "w2": (~pts["srv1"] & srv_won).astype(int)}).groupby("match_id").sum()
    st = status.set_index("match_id").loc[g.index]
    return pd.DataFrame({"match_id": g.index, "tour": st["tour"].to_numpy(), "rule": st["rule"].to_numpy(),
                         "surface": st["tournament_name"].map(SURFACE).to_numpy(), "player1": st["player1"].to_numpy(),
                         "player2": st["player2"].to_numpy(), "pa": (g["w1"] / g["s1"]).to_numpy(),
                         "pb": (g["w2"] / g["s2"]).to_numpy(), "svpt_a": g["s1"].to_numpy(), "svpt_b": g["s2"].to_numpy()})


def replay_luck(ms: pd.DataFrame, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Play every kept match again point by point under the iid model: the same players, format and deciding-set
    rule, at true serve rates drawn from what each measured rate allows (stage2_anatomy.denoised_rates). The first
    server is drawn at random. Returns points and statuses shaped as replay_all's."""
    rng = np.random.default_rng(seed)
    p1, p2, _ = A.denoised_rates(ms, rng)
    keep, status = [], []
    for k, row in enumerate(ms.itertuples(index=False)):
        need = (BEST_OF[row.tour] + 1) // 2
        u = rng.random(800)
        state, over, next1, i = START, False, bool(rng.random() < 0.5), 0
        while not over:
            if i == len(u):
                u, i = rng.random(800), 0
            srv_wins = u[i] < (p1[k] if next1 else p2[k])
            i += 1
            won1 = srv_wins if next1 else not srv_wins
            keep.append((row.match_id, row.tour, state[0] + state[1] + 1, *state, next1, won1))
            state, _, over, next1 = advance(state, next1, won1, need, row.rule)
        status.append({"match_id": row.match_id, "tour": row.tour, "rule": row.rule, "player1": row.player1,
                       "player2": row.player2, "p1_won": bool(state[0] > state[1])})
    cols = ["match_id", "tour", "set_no", "sa", "sb", "ga", "gb", "x", "y", "tb", "first1", "srv1", "won1"]
    return pd.DataFrame(keep, columns=cols), pd.DataFrame(status)


# ------------------------------------------------------------------------------------------------
# Per player and match, and the analyses

def player_rows(pts: pd.DataFrame, status: pd.DataFrame) -> pd.DataFrame:
    """Two rows per kept match: each player's serve and return points, won, importance-weighted."""
    out = []
    for k in (1, 2):
        on_serve = pts["srv1"] if k == 1 else ~pts["srv1"]
        won = pts["won1"] if k == 1 else ~pts["won1"]
        w = pts["importance"]
        d = pd.DataFrame({"match_id": pts["match_id"], "tour": pts["tour"],
                          "s_n": on_serve.astype(int), "s_won": (on_serve & won).astype(int),
                          "s_w": w * on_serve, "s_wwon": w * (on_serve & won),
                          "r_n": (~on_serve).astype(int), "r_won": (~on_serve & won).astype(int),
                          "r_w": w * ~on_serve, "r_wwon": w * (~on_serve & won)})
        g = d.groupby(["match_id", "tour"], sort=False).sum().reset_index()
        st = status.set_index("match_id")
        g["player"] = g["match_id"].map(st[f"player{k}"])
        g["won_match"] = g["match_id"].map(st["p1_won"]) == (k == 1)
        g["side"] = k
        out.append(g)
    r = pd.concat(out, ignore_index=True)
    r["serve_rate"] = r["s_won"] / r["s_n"]
    r["return_rate"] = r["r_won"] / r["r_n"]
    r["clutch_serve"] = r["s_wwon"] / r["s_w"] - r["serve_rate"]
    r["clutch_return"] = r["r_wwon"] / r["r_w"] - r["return_rate"]
    r["clutch"] = (r["clutch_serve"] + r["clutch_return"]) / 2
    r["points_share"] = (r["s_won"] + r["r_won"]) / (r["s_n"] + r["r_n"])
    return r


def clutch_means(r: pd.DataFrame) -> list:
    return [{"tour": t, "serve": mean_ci(r.loc[r["tour"] == t, "clutch_serve"].to_numpy()),
             "return": mean_ci(r.loc[r["tour"] == t, "clutch_return"].to_numpy()),
             "winners": mean_ci(r.loc[(r["tour"] == t) & r["won_match"], "clutch"].to_numpy()),
             "losers": mean_ci(r.loc[(r["tour"] == t) & ~r["won_match"], "clutch"].to_numpy())} for t in C.TOURS]


def mean_ci(v: np.ndarray) -> dict:
    v = v[np.isfinite(v)]
    m, se = float(v.mean()), float(v.std(ddof=1) / np.sqrt(len(v)))
    return {"n": int(len(v)), "mean_points": round(100 * m, 3), "lo": round(100 * (m - 1.96 * se), 3), "hi": round(100 * (m + 1.96 * se), 3)}


def regressions(r: pd.DataFrame) -> list:
    """Per tour: the result on player 1's points edge, then also on the clutch difference (player 1 minus 2)."""
    out = []
    one, two = r[r["side"] == 1].set_index("match_id"), r[r["side"] == 2].set_index("match_id")
    for tour in C.TOURS:
        a = one[one["tour"] == tour]
        b = two.loc[a.index]
        y = a["won_match"].to_numpy()
        edge = 100 * (a["points_share"].to_numpy() - 0.5)
        specs = {"points": [edge], "points + clutch": [edge, 100 * (a["clutch"] - b["clutch"]).to_numpy()],
                 "points + clutch on serve and return": [edge, 100 * (a["clutch_serve"] - b["clutch_serve"]).to_numpy(),
                                                         100 * (a["clutch_return"] - b["clutch_return"]).to_numpy()]}
        ll = {}
        for name, cols in specs.items():
            pr, coef = A.oof_logit(np.column_stack(cols), y)
            ll[name] = A.logloss(pr, y)
            out.append({"tour": tour, "model": name, "matches": int(len(y)), "cv_logloss": float(ll[name].mean()),
                        "gain_over_points_milli": A.gap(ll["points"], ll[name]), "coefficients": [round(float(c), 4) for c in coef]})
    return out


def persistence(r: pd.DataFrame) -> list:
    measures = {"clutch_serve": "s_w", "clutch_return": "r_w", "clutch": "s_w", "serve_rate": "s_n", "return_rate": "r_n"}
    rng = np.random.default_rng(SEED)
    out = []
    for tour in C.TOURS:
        rr = r[r["tour"].eq(tour) & r["player"].notna()].reset_index(drop=True)
        n_matches = rr.groupby("player").size()
        for min_half in (5, 10, 20):
            sub = rr[rr["player"].isin(n_matches.index[n_matches >= 2 * min_half])].reset_index(drop=True)
            res = {k: [] for k in measures}
            players = int(sub["player"].nunique())
            for _ in range(SPLITS):
                half = sub.assign(k=rng.random(len(sub))).groupby("player")["k"].rank(method="first").astype(int) % 2
                sums = sub[["s_n", "s_won", "s_w", "s_wwon", "r_n", "r_won", "r_w", "r_wwon"]].groupby([sub["player"], half]).sum()
                cs = sums["s_wwon"] / sums["s_w"] - sums["s_won"] / sums["s_n"]
                cr = sums["r_wwon"] / sums["r_w"] - sums["r_won"] / sums["r_n"]
                vals = {"clutch_serve": cs, "clutch_return": cr, "clutch": (cs + cr) / 2,
                        "serve_rate": sums["s_won"] / sums["s_n"], "return_rate": sums["r_won"] / sums["r_n"]}
                for k, v in vals.items():
                    u = v.unstack()
                    u = u[u.notna().all(axis=1)]
                    res[k].append(float(np.corrcoef(u[0], u[1])[0, 1]))
            for k in measures:
                rs = np.array(res[k])
                lo, hi = A.fisher_ci(float(rs.mean()), players)
                out.append({"tour": tour, "min_matches_per_half": min_half, "measure": k, "players": players,
                            "r_mean": round(float(rs.mean()), 4), "r_ci_lo": round(lo, 4), "r_ci_hi": round(hi, 4),
                            "r_split_p2_5": round(float(np.percentile(rs, 2.5)), 4), "r_split_p97_5": round(float(np.percentile(rs, 97.5)), 4)})
    return out


def main() -> int:
    raw, editions = load_points()
    log(f"loaded {len(raw):,} rows of {raw['match_id'].nunique():,} matches from {len(editions)} editions")
    pts, status = replay_all(raw)
    log(f"replayed: {int(status['kept'].sum()):,} of {len(status):,} matches kept, {len(pts):,} points")
    rate = {t: float(pts.loc[pts["tour"].eq(t), "won1"].eq(pts.loc[pts["tour"].eq(t), "srv1"]).mean()) for t in C.TOURS}
    pts = add_importance(pts, status, rate)
    log("importance computed")
    r = player_rows(pts, status)
    res = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "editions": editions,
           "serve_rate_used": rate, "splits": SPLITS}
    st = status
    res["matches"] = {t: {"in_files": int((st["tour"] == t).sum()), "kept": int((st["kept"] & (st["tour"] == t)).sum()),
                          "games_disagree": int(((st["games_disagree"] > 0) & (st["tour"] == t)).sum()),
                          "score_disagree": int(((st["score_disagree"] > 0) & (st["tour"] == t)).sum()),
                          "server_disagree": int(((st["server_disagree"] > 0) & (st["tour"] == t)).sum()),
                          "not_ended_on_last_point": int((~st["ended_on_last_point"] & (st["tour"] == t)).sum()),
                          "dropped_ended_early": int((~st["kept"] & ~st["ended_on_last_point"] & (st["tour"] == t)).sum()),
                          "dropped_disagreeing": int((~st["kept"] & st["ended_on_last_point"] & (st["tour"] == t)).sum()),
                          "points_kept": int((pts["tour"] == t).sum()),
                          "players": int(pd.concat([st.loc[st["kept"] & (st["tour"] == t), "player1"],
                                                    st.loc[st["kept"] & (st["tour"] == t), "player2"]]).nunique())} for t in C.TOURS}
    imp = []
    for t in C.TOURS:
        g = pts[pts["tour"] == t]
        w = np.sort(g["importance"].to_numpy())[::-1]
        imp.append({"tour": t, "mean": float(g["importance"].mean()), "median": float(g["importance"].median()),
                    "top10pct_share_pct": round(100 * float(w[: len(w) // 10].sum() / w.sum()), 2),
                    "break_point_mean": float(g.loc[g["break_point"], "importance"].mean()),
                    "tiebreak_mean": float(g.loc[g["tb"], "importance"].mean()),
                    "break_point_share_of_points_pct": round(100 * float(g["break_point"].mean()), 2),
                    "break_point_share_of_importance_pct": round(100 * float(g.loc[g["break_point"], "importance"].sum() / g["importance"].sum()), 2)})
    res["importance"] = imp
    ed = pd.DataFrame(editions)
    a1, a2 = ed["aces_first_serve"].sum(), ed["aces_second_serve"].sum()
    res["file_notes"] = {"editions_with_games_blank": ed.loc[ed["games_blank_pct"] > 99, "edition"].tolist(),
                         "editions_writing_GAME": ed.loc[ed["game_token"], "edition"].tolist(),
                         "editions_with_serve_number": int(ed["aces_first_serve"].notna().sum()),
                         "aces_on_second_serve_pct": round(100 * float(a2 / (a1 + a2)), 2),
                         "aces_counted": int(a1 + a2)}
    res["clutch_mean"] = clutch_means(r)
    res["regressions"] = regressions(r)
    log("regressions done")
    # the same measures on pure-luck replays of the kept matches (same players, formats and weights)
    ms = measured(pts, status[status["kept"]])
    pers = [pd.DataFrame(persistence(r)).assign(world="real", replay=0)]
    for k in range(REPLAYS):
        lp, ls = replay_luck(ms, SEED + 1000 * (k + 1))
        lp = add_importance(lp, ls, rate)
        lr = player_rows(lp, ls)
        if k == 0:
            res["pure_luck"] = {"points": int(len(lp)), "clutch_mean": clutch_means(lr), "regressions": regressions(lr)}
        pers.append(pd.DataFrame(persistence(lr)).assign(world="pure luck", replay=k + 1))
        log(f"pure-luck replay {k + 1} of {REPLAYS}")
    d = pd.concat(pers, ignore_index=True)
    luck = d[d["world"].eq("pure luck")].groupby(["tour", "min_matches_per_half", "measure"])["r_mean"]
    real = d[d["world"].eq("real")].set_index(["tour", "min_matches_per_half", "measure"])
    res["persistence"] = json.loads(real.assign(luck_r_mean=luck.mean(), luck_r_min=luck.min(), luck_r_max=luck.max())
                                    .reset_index().to_json(orient="records"))
    res["replays"] = REPLAYS
    log("persistence done")
    pts.to_parquet(POINTS_OUT, index=False)
    r.to_parquet(PLAYERS_OUT, index=False)
    res["status_examples_dropped"] = json.loads(st[~st["kept"]].head(20).to_json(orient="records"))
    RESULTS.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    log(f"wrote {RESULTS.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
