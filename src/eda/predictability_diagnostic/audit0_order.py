"""Audit of Stage 0, check 8: the chronological order within events.

For 20 events drawn at random (every event equally likely), the matches are listed in the table's
order and read: do the rounds come in the order the draw is played (qualifying Q1..Q4, then a round
robin, then R128 .. F), does the event keep one tournament date, and does the draw hold together
(each player of a round won their previous round unless they entered there; no main-draw loser plays
on)? The same readings are then made over every event of the table.

An event is (tour, tournament_id), as the as-of helper groups it.
Writes audit0/order_sample.csv, audit0/order_sample_events.json and audit0/order.json.
Run: ./python.sh src/eda/predictability_diagnostic/audit0_order.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.predictability_diagnostic import audit0_common as A  # noqa: E402

SEED = 20260930
# the order the rounds of a draw are played in (the audit's own statement of it)
PLAYED = ["Q1", "Q2", "Q3", "Q4", "RR", "R128", "R64", "R32", "R16", "QF", "SF", "BR", "F"]
RANK = {r: i for i, r in enumerate(PLAYED)}
RANK["F"] = RANK["BR"]          # the bronze-medal match and the final are played the same day
NEXT = {"Q1": "Q2", "Q2": "Q3", "Q3": "Q4", "R128": "R64", "R64": "R32", "R32": "R16", "R16": "QF", "QF": "SF",
        "SF": "F"}


def load() -> pd.DataFrame:
    m = A.load_matches(["match_id", "tour", "tournament_id", "tournament_name", "tournament_date", "level", "qualifying",
                        "round", "round_order", "match_num", "order", "source", "status", "year"])
    mp = A.load_players(["match_id", "player_id", "won"])
    w = mp[mp["won"]].set_index("match_id")["player_id"]
    l = mp[~mp["won"]].set_index("match_id")["player_id"]
    m["winner"], m["loser"] = m["match_id"].map(w), m["match_id"].map(l)
    m["rank"] = m["round"].map(RANK)
    return m.sort_values("order").reset_index(drop=True)


def read_event(e: pd.DataFrame) -> dict:
    """Readings of one event's matches, taken in the table's order."""
    e = e.sort_values("order")
    runs = []
    for r in e["round"]:
        if runs and runs[-1][0] == r:
            runs[-1][1] += 1
        else:
            runs.append([r, 1])
    sequence = " > ".join(f"{r} x{n}" for r, n in runs)
    in_order = bool((np.diff(e["rank"].to_numpy()) >= 0).all())
    rounds_contiguous = len(runs) == e["round"].nunique()
    dates = sorted(e["tournament_date"].dt.strftime("%Y-%m-%d").unique())
    # the draw: who plays each round, who won and lost the round before
    ko = e[~e["round"].isin(["RR", "BR"])]
    entered_late, lost_then_played, winners_missing = [], [], []
    team = e["level"].eq("TEAM").any()
    for r, nxt in NEXT.items():
        cur, after = ko[ko["round"].eq(r)], ko[ko["round"].eq(nxt)]
        if cur.empty or after.empty:
            continue
        players_next = set(after["winner"]) | set(after["loser"])
        losers = set(cur["loser"])
        winners = set(cur["winner"])
        lost_then_played += sorted(losers & players_next)
        winners_missing += sorted(winners - players_next)
        entered_late += sorted(players_next - winners - losers)
    # qualifiers: a Q-round loser may enter the main draw as a lucky loser; count separately
    q_losers = set(e.loc[e["qualifying"], "loser"])
    main_players = set(e.loc[~e["qualifying"], "winner"]) | set(e.loc[~e["qualifying"], "loser"])
    return {"tour": e["tour"].iat[0], "tournament_id": e["tournament_id"].iat[0], "name": e["tournament_name"].iat[0],
            "level": e["level"].iat[0], "source": "/".join(sorted(e["source"].unique())), "matches": int(len(e)),
            "dates": dates, "rounds_in_table_order": sequence, "rounds_in_played_order": in_order,
            "each_round_in_one_block": rounds_contiguous,
            "qualifying_before_main": bool(e.loc[e["qualifying"], "order"].max() < e.loc[~e["qualifying"], "order"].min())
            if e["qualifying"].any() and (~e["qualifying"]).any() else None,
            "team_event": bool(team),
            "players_entering_after_the_first_round": len(entered_late),
            "losers_who_play_the_next_round": len(lost_then_played),
            "winners_absent_from_the_next_round": len(winners_missing),
            "qualifying_losers_in_main_draw": len(q_losers & main_players)}


def sweep(m: pd.DataFrame) -> dict:
    """The same readings over every event, vectorised where it matters."""
    ev = ["tour", "tournament_id"]
    # rounds in played order along the table's order
    m = m.sort_values(ev + ["order"])
    back = m.groupby(ev)["rank"].diff().lt(0)
    events_out_of_order = m.loc[back, ev].drop_duplicates()
    # one date per event, and whether any later round carries an earlier date
    nd = m.groupby(ev)["tournament_date"].nunique()
    multi = nd[nd > 1].reset_index()[ev]
    mm = m.merge(multi, on=ev)
    by_round = mm.groupby(ev + ["rank"])["tournament_date"].agg(["min", "max"]).reset_index().sort_values(ev + ["rank"])
    prev_max = by_round.groupby(ev)["max"].cummax().groupby([by_round[c] for c in ev]).shift(1)
    date_back = by_round[by_round["min"] < prev_max]
    # losers who play on in a knockout draw (team events and round robins aside)
    ko = m[~m["round"].isin(["RR", "BR"]) & m["level"].ne("TEAM")]
    lost = ko[["tour", "tournament_id", "rank", "loser", "qualifying"]].rename(columns={"loser": "player", "rank": "lost_at"})
    played = pd.concat([ko[["tour", "tournament_id", "rank", "winner", "qualifying"]].rename(columns={"winner": "player"}),
                        ko[["tour", "tournament_id", "rank", "loser", "qualifying"]].rename(columns={"loser": "player"})])
    later = lost.merge(played.rename(columns={"qualifying": "q_later"}), on=["tour", "tournament_id", "player"])
    later = later[later["rank"] > later["lost_at"]]
    lucky = later[later["qualifying"] & ~later["q_later"]]
    main_again = later[~later["qualifying"]]
    qual_again = later[later["qualifying"] & later["q_later"]]
    return {
        "events": int(m.groupby(ev).ngroups),
        "events_with_a_round_out_of_played_order": int(len(events_out_of_order)),
        "events_out_of_order_examples": events_out_of_order.head(10).to_dict(orient="records"),
        "events_with_more_than_one_date": int(len(multi)),
        "events_with_more_than_one_date_by_level": mm.drop_duplicates(ev).groupby(["tour", "level"]).size()
        .rename("events").reset_index().to_dict(orient="records"),
        "rounds_dated_before_an_earlier_round_of_their_event": int(len(date_back)),
        "events_where_a_later_round_is_dated_earlier": int(len(date_back[ev].drop_duplicates())),
        "date_back_examples": date_back.head(10).assign(min=lambda f: f["min"].astype(str), max=lambda f: f["max"].astype(str))
        .to_dict(orient="records"),
        "main_draw_losers_playing_a_later_main_round": {"rows": int(len(main_again)),
                                                        "events": int(len(main_again[["tour", "tournament_id"]].drop_duplicates()))},
        "main_draw_losers_examples": main_again.head(10).to_dict(orient="records"),
        "qualifying_losers_playing_a_later_qualifying_round": int(len(qual_again)),
        "qualifying_losers_in_the_main_draw_lucky_losers": int(len(lucky)),
    }


def main() -> int:
    m = load()
    events = m[["tour", "tournament_id"]].drop_duplicates().reset_index(drop=True)
    pick = events.sample(20, random_state=SEED)
    readings, rows = [], []
    for t, tid in pick.itertuples(index=False):
        e = m[(m["tour"] == t) & (m["tournament_id"] == tid)]
        readings.append(read_event(e))
        rows.append(e[["tour", "tournament_id", "tournament_name", "tournament_date", "level", "round", "match_num", "order",
                       "winner", "loser", "source"]])
    pd.concat(rows).to_csv(A.out_dir() / "order_sample.csv", index=False)
    A.write_json("order_sample_events.json", readings)
    s = sweep(m)
    s["sample_seed"] = SEED
    s["sample_levels"] = pd.Series([r["level"] for r in readings]).value_counts().to_dict()
    A.write_json("order.json", s)
    for r in readings:
        print({k: r[k] for k in ("tour", "tournament_id", "name", "level", "matches", "dates", "rounds_in_played_order",
                                 "each_round_in_one_block", "qualifying_before_main", "losers_who_play_the_next_round",
                                 "winners_absent_from_the_next_round", "players_entering_after_the_first_round")})
        print("   ", r["rounds_in_table_order"])
    print({k: v for k, v in s.items() if "examples" not in k})
    return 0


if __name__ == "__main__":
    sys.exit(main())
