"""Hand checks of the third-party readers (rule 8 of the brief): for the match ids each reader's JSON lists under
hand_check.keys, print the raw staged document next to the reader's rows and Stage 0's names, so the counts and the
player orientation can be checked by eye. ``--record <reader> "<verdict>"`` writes the verdict into the reader's JSON
(hand_check.status = "checked", with the date and the verdict text).

Run: ./python.sh src/eda/source_reconciliation/tp_handcheck.py <reader> [--keys k1,k2]
     ./python.sh src/eda/source_reconciliation/tp_handcheck.py --record <reader> "<verdict>"
"""
from __future__ import annotations

import gzip
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import tp_common as T  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_colwidth", 60)
SHOW = ["player_id", "x_side"] + C.FIELDS + ["complete"]


def reader_rows(reader: str, keys: list[str]) -> pd.DataFrame:
    return pd.read_parquet(T.READERS / f"{reader}.parquet", filters=[("match_id", "in", keys)])


def stage0_rows(keys: list[str]) -> pd.DataFrame:
    _, p = C.stage0(["match_id"], ["match_id", "player_id", "side", "player_name", "won"] + C.COUNTS)
    m, _ = C.stage0(["match_id", "score", "tournament_name", "round", "tournament_date"], ["match_id"])
    return p[p["match_id"].isin(keys)].merge(m, on="match_id")


def sofascore(reader: str, keys: list[str]) -> None:
    rows = reader_rows(reader, keys)
    s0 = stage0_rows(keys)
    for mid in keys:
        r = rows[rows["match_id"].eq(mid)]
        if r.empty:
            continue
        eid = r["source_key"].iat[0].split(":")[1]
        print("=" * 100)
        print(mid, "->", r["source_key"].iat[0], r["x_collection"].iat[0])
        print(s0[s0["match_id"].eq(mid)][["side", "player_id", "player_name", "won", "score"] + C.COUNTS].to_string())
        coll = r["x_collection"].iat[0]
        ev = pq.read_table(C.DUMP / "points" / coll / "events.parquet", filters=[("event_id", "==", eid)],
                           columns=["event_id", "home_name", "away_name", "winner_code", "status_description",
                                    "home_set1", "away_set1", "home_set2", "away_set2", "home_set3",
                                    "away_set3"]).to_pandas()
        print(ev.to_string())
        if reader in ("tp_sofascore_box", "tp_sofascore_setbox"):
            st = pq.read_table(C.DUMP / "points" / coll / "statistics.parquet", filters=[("event_id", "==", eid)],
                               columns=["period", "key", "home", "away"]).to_pandas()
            st = st[st["key"].isin(["aces", "doubleFaults", "firstServeAccuracy", "firstServePointsAccuracy",
                                    "secondServePointsAccuracy", "serviceGamesTotal", "breakPointsSaved",
                                    "servicePointsScored"])]
            print(st.pivot_table(index="key", columns="period", values=["home", "away"], aggfunc="first").to_string())
        else:
            pt = pq.read_table(C.DUMP / "points" / coll / "points.parquet", filters=[("event_id", "==", eid)],
                               columns=["set", "game", "point", "home_point", "away_point", "point_description",
                                        "serving", "scoring", "tiebreak"]).to_pandas()
            for c in ("set", "game", "point"):
                pt[c] = pd.to_numeric(pt[c])
            pt = pt.sort_values(["set", "game", "point"])
            g = pt.groupby(["set", "game"]).agg(n=("point", "size"), serving=("serving", "first"),
                                                scoring=("scoring", "last"), tb=("tiebreak", "first"),
                                                last=("home_point", "last"), last_a=("away_point", "last"),
                                                aces=("point_description", lambda s: int((s == "1").sum())),
                                                dfs=("point_description", lambda s: int((s == "2").sum())))
            print(g.head(14).to_string())
            print(f"... {len(g)} games, {len(pt)} listed points")
        print(r[[c for c in SHOW + [x for x in r.columns if x.startswith("x_") and x not in SHOW][:12]]
                if True else SHOW].to_string())


def mcp(reader: str, keys: list[str]) -> None:
    rows = reader_rows(reader, keys)
    s0 = stage0_rows(keys)
    base = C.DUMP / "points" / "match_charting_project"
    for mid in keys:
        r = rows[rows["match_id"].eq(mid)]
        if r.empty:
            continue
        key = r["source_key"].iat[0]
        g = "m" if "-M-" in key else "w"
        print("=" * 100)
        print(mid, "->", key)
        print(s0[s0["match_id"].eq(mid)][["side", "player_id", "player_name", "won", "score"] + C.COUNTS].to_string())
        ov = pd.read_parquet(base / "stats" / f"charting-{g}-stats-Overview.parquet", filters=[("match_id", "==", key)])
        print(ov[ov["set"].astype(str).eq("Total")][["player", "serve_pts", "aces", "dfs", "first_in", "first_won",
                                                    "second_in", "second_won", "bk_pts", "bp_saved"]].to_string())
        print(r[SHOW + [c for c in r.columns if c.startswith("x_")][:14]].to_string())


def atp_scraped(reader: str, keys: list[str]) -> None:
    rows = reader_rows(reader, keys)
    s0 = stage0_rows(keys)
    for mid in keys:
        r = rows[rows["match_id"].eq(mid)]
        print("=" * 100)
        sk = r["source_key"].iat[0]
        print(mid, "->", sk, r["x_file"].iat[0])
        stem, tid, rnd, wid, lid = sk.split(":", 1)[1].split("|")
        path = C.HANDOFF / r["x_file"].iat[0]
        d = pd.read_csv(path, dtype=str, low_memory=False)
        raw = d[(d["tourney_id"].astype(str) == tid) & (d["round"].astype(str) == rnd) &
                (d["winner_id"].astype(str) == wid) & (d["loser_id"].astype(str) == lid)]
        cols = ["tourney_name", "tourney_date", "round", "score", "winner_name", "loser_name"] + \
            [f"{s}_{c}" for s in ("w", "l") for c in ("ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms",
                                                      "bpSaved", "bpFaced")]
        print(raw[cols].T.to_string())
        print(s0[s0["match_id"].eq(mid)][["side", "player_id", "player_name", "won", "score"] + C.COUNTS].to_string())
        print(r[SHOW + ["x_src_name", "x_atp_code"]].to_string())


def flashscore(reader: str, keys: list[str]) -> None:
    rows = reader_rows(reader, keys)
    s0 = stage0_rows(keys)
    for mid in keys:
        r = rows[rows["match_id"].eq(mid)]
        print("=" * 100)
        f, line = r["x_file"].iat[0], int(r["x_line"].iat[0])
        print(mid, "->", r["source_key"].iat[0], f, "line", line)
        folder = C.HANDOFF / ("flashscore_gql_stats" if f.startswith("gql_stats") else "flashscore_full")
        op = gzip.open if f.endswith(".gz") else open
        with op(folder / f, "rt", encoding="utf-8", errors="replace") as h:
            for i, text in enumerate(h, 1):
                if i == line:
                    d = json.loads(text)
                    break
        print({k: d.get(k) for k in ("match_id", "home_player", "away_player", "match_date", "set_scores", "status")})
        for side in ("home", "away"):
            print(side, {k: d.get(f"{side}_{k}") for k in ("aces", "double_faults", "1st_serve_points_won",
                                                          "2nd_serve_points_won", "break_points_saved",
                                                          "service_points_won", "service_games_won")})
        print(s0[s0["match_id"].eq(mid)][["side", "player_id", "player_name", "won", "score"] + C.COUNTS].to_string())
        print(r[SHOW + ["x_src_name", "x_src_side"]].to_string())


def tennislive(reader: str, keys: list[str]) -> None:
    rows = reader_rows(reader, keys)
    s0 = stage0_rows(keys)
    TL = C.DUMP / "points" / "tennislive"
    for mid in keys:
        r = rows[rows["match_id"].eq(mid)]
        url = r["x_url"].iat[0]
        print("=" * 100)
        print(mid, "->", url, r["x_collection"].iat[0])
        m = pd.read_parquet(TL / "matches.parquet", filters=[("url", "==", url)],
                            columns=["player1_name", "player2_name", "score", "winner_id", "player1_id", "player2_id"])
        print(m.to_string())
        st = pd.read_parquet(TL / "statistics.parquet", filters=[("url", "==", url)],
                             columns=["period", "name", "player1_value", "player1_detail", "player2_value", "player2_detail"])
        print(st[st["period"].eq("match")].to_string())
        print(s0[s0["match_id"].eq(mid)][["side", "player_id", "player_name", "won", "score"] + C.COUNTS].to_string())
        print(r[SHOW + ["x_src_name"]].to_string())


def generic(reader: str, keys: list[str]) -> None:
    rows = reader_rows(reader, keys)
    s0 = stage0_rows(keys)
    for mid in keys:
        r = rows[rows["match_id"].eq(mid)]
        print("=" * 100)
        print(mid, "->", r["source_key"].iat[0] if len(r) else None)
        print(s0[s0["match_id"].eq(mid)][["side", "player_id", "player_name", "won", "score"] + C.COUNTS].to_string())
        print(r[SHOW + [c for c in r.columns if c.startswith("x_")][:14]].to_string())


def record(reader: str, verdict: str) -> None:
    path = T.READERS / f"{reader}.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    d.setdefault("hand_check", {})
    d["hand_check"].update({"status": "checked", "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "verdict": verdict,
                            "how": "tp_handcheck.py printed each key's raw staged rows (the source's own document as "
                                   "staged under data/dump/ or data/raw/) beside the reader's rows and Stage 0's "
                                   "names and counts; checked by eye: the player orientation (names) and every count "
                                   "of the mapping"})
    C.write_json(path, d)
    print(f"recorded for {reader}")


def main() -> int:
    if sys.argv[1] == "--record":
        record(sys.argv[2], sys.argv[3])
        return 0
    reader = sys.argv[1]
    d = json.loads((T.READERS / f"{reader}.json").read_text(encoding="utf-8"))
    keys = d["hand_check"]["keys"]
    if "--keys" in sys.argv:
        keys = sys.argv[sys.argv.index("--keys") + 1].split(",")
    fn = {"tp_sofascore_box": sofascore, "tp_sofascore_setbox": sofascore, "tp_sofascore_recount": sofascore,
          "tp_mcp_recount": mcp, "tp_atp_scraped": atp_scraped, "tp_flashscore_stats": flashscore,
          "tp_tennislive_stats": tennislive}.get(reader, generic)
    fn(reader, keys)
    return 0


if __name__ == "__main__":
    sys.exit(main())
