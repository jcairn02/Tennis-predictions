"""R2-skeptic (round 2): is RG's capture complete? A point-by-point integrity test of MatchBeats.

RG's statistics and its MatchBeats come from one capture, so their agreement (the proposal's "complete" test: the same
serve points) cannot show that the capture holds every point. Tennis scoring can: replaying each game from the
scorers must reproduce the game score MatchBeats prints after every point, end the game exactly at its last point,
with the printed game winner, keep one server per game and alternate servers game by game, and give RG's set scores.
A point missing from the capture breaks one of these, except a whole deuce pair (40-40 -> AD -> 40-40) or a whole
game, which the set scores catch. From 2022 the deciding set's tie-break at 6-6 is played to 10 points.

Per RG match of 2019-2026 with a MatchBeats file, writes in
data/studies/rg_first_serve_recount/followup/review/R2-skeptic/:
    mb_integrity.csv   points, games; score steps that do not follow from the point (bad_steps); games not ending at
                       their last point or with another winner (bad_ends); games with two servers outside tie-breaks
                       (mixed_server); breaks in the alternation of servers (alternation_breaks); sets whose replayed
                       games differ from RG's set score (set_mismatch); whether the last game is unfinished
                       (last_game_open, allowed in a retirement); special codes; integrity = all zero
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/mb_integrity.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
STEP = {"0": 0, "15": 1, "30": 2, "40": 3}


def game_state(a: int, b: int, tb: bool) -> tuple[str, str]:
    """The printed score of a game in progress with a and b points (player 1, player 2)."""
    if tb:
        return str(a), str(b)
    if a >= 3 and b >= 3:
        if a == b:
            return "40", "40"
        return ("AD", "40") if a > b else ("40", "AD")
    names = ["0", "15", "30", "40"]
    return names[min(a, 3)], names[min(b, 3)]


def ended(a: int, b: int, tb: bool, need_tb: int = 7) -> int:
    need = need_tb if tb else 4
    if a >= need and a - b >= 2:
        return 1
    if b >= need and b - a >= 2:
        return 2
    return 0


def check_match(g: pd.DataFrame, set_games: dict, deciding_set: int, year: int) -> dict:
    """deciding_set: 5 (men's main draw) or 3; from 2022 the deciding set's tie-break at 6-6 is first to 10."""
    g = g.sort_values("idx")
    out = {"points": len(g), "games": 0, "bad_steps": 0, "bad_ends": 0, "mixed_server": 0, "alternation_breaks": 0,
           "set_mismatch": 0, "last_game_open": False}
    prev_server = None
    won = {}
    games = list(g.groupby(["set_i", "game_i"], sort=True))
    for gi, ((si, gno), pts) in enumerate(games):
        out["games"] += 1
        tb = bool(pts["tb"].iloc[0])
        need_tb = 10 if (tb and year >= 2022 and int(pts["set"].iloc[0]) == deciding_set) else 7
        servers = set(pts["server"])
        first_server = pts["server"].iloc[0]
        if not tb and len(servers) > 1:
            out["mixed_server"] += 1
        if prev_server is not None and first_server == prev_server:
            out["alternation_breaks"] += 1
        prev_server = first_server
        a = b = 0
        winner = 0
        for k, p in enumerate(pts.itertuples(index=False)):
            if winner:                       # points after the game ended
                out["bad_ends"] += 1
                break
            if p.scorer == "1":
                a += 1
            elif p.scorer == "2":
                b += 1
            winner = ended(a, b, tb, need_tb)
            s1, s2 = str(p.tm1_score), str(p.tm2_score)
            if winner:
                ok = (s1 == "GAME" and winner == 1) or (s2 == "GAME" and winner == 2) or \
                     (tb and ((winner == 1 and s1 in ("GAME", str(a))) or (winner == 2 and s2 in ("GAME", str(b)))))
            else:
                e1, e2 = game_state(a, b, tb)
                ok = (s1, s2) == (e1, e2)
            if not ok:
                out["bad_steps"] += 1
        last = gi == len(games) - 1
        if not winner:
            if last:
                out["last_game_open"] = True
            else:
                out["bad_ends"] += 1
        else:
            gw = pts["game_winner"].iloc[-1]
            if pd.notna(gw) and str(int(gw)) in ("1", "2") and int(gw) != winner:
                out["bad_ends"] += 1
            won.setdefault(si, [0, 0])[winner - 1] += 1
    for si, (x, y) in won.items():
        exp = set_games.get(si)
        if exp is not None and (x, y) != exp:
            out["set_mismatch"] += 1
    out["integrity"] = (out["bad_steps"] == 0 and out["bad_ends"] == 0 and out["mixed_server"] == 0
                        and out["alternation_breaks"] == 0 and out["set_mismatch"] == 0)
    out["special_codes"] = ";".join(sorted(set(g["result"].dropna()) - {"UE", "FE", "W", "A", "DF"}))
    return out


def main() -> int:
    pts = pd.read_parquet(OUT / "mb_points.parquet")
    meta = pd.read_parquet(OUT / "mb_meta.parquet")
    api = pd.read_parquet(OUT / "api.parquet")
    names = {}
    for r in meta[meta["problem"].isna()].itertuples(index=False):
        names[(r.year, r.code)] = (f"{r.p1_first} {r.p1_last}".casefold(), f"{r.p2_first} {r.p2_last}".casefold())
    a_idx = {(r.year, r.code, r.team): r for r in api.itertuples(index=False)}
    rows = []
    for (y, c), g in pts.groupby(["year", "code"], sort=False):
        # RG's set scores in MatchBeats' slot order: slot 1 is the API team whose last name is in slot 1's name
        ta, tb_ = a_idx.get((y, c, "A")), a_idx.get((y, c, "B"))
        set_games = {}
        if ta is not None and tb_ is not None and (y, c) in names:
            n1 = names[(y, c)][0]
            a_is_1 = str(ta.last).casefold() in n1
            ga, gb = json.loads(ta.set_games), json.loads(tb_.set_games)
            for i, (x1, x2) in enumerate(zip(ga, gb), 1):
                if x1 is None or x2 is None:
                    continue
                set_games[i] = (x1, x2) if a_is_1 else (x2, x1)
        rec = {"year": y, "code": c, **check_match(g, set_games, 5 if c.startswith("SM") else 3, int(y))}
        rows.append(rec)
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "mb_integrity.csv", index=False)
    print(out.groupby("year")["integrity"].agg(["size", "sum"]).to_string())
    print(out[~out["integrity"]][["bad_steps", "bad_ends", "mixed_server", "alternation_breaks", "set_mismatch"]]
          .gt(0).sum().to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
