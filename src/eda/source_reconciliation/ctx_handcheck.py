"""Hand checks of the ctx_ readers (the brief's rule 8): for each reader, five random linked matches (seed 20261016),
the raw staged row read directly from the source's file (not through the reader), the reader's values oriented to
Stage 0's player A, and Stage 0's own row, printed side by side for a check by eye. The checker's verdicts are written
by hand into context/handcheck.json (the keys printed here and what was seen).

Run: ./python.sh src/eda/source_reconciliation/ctx_handcheck.py [--readers a,b] [--n 5]
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import ctx_common as X  # noqa: E402

SEED = 20261016
SHOW = ["source_key", "p1", "p2", "p1_side", "a_won_src", "src_sets_text", "src_status", "seed_a_src", "seed_b_src",
        "surface_raw", "indoor_raw", "level_raw", "round_raw"]


def raw_row(source: str, key: str) -> dict:
    """The source's own row for a key, read straight from its staged file."""
    if source == "tennis_data":
        f, i = key.rsplit("#", 1)
        t = pd.read_parquet(ROOT / f)
        r = t.iloc[int(i)]
        cols = [c for c in ["Tournament", "Date", "Round", "Winner", "Loser", "W1", "L1", "W2", "L2", "W3", "L3", "W4",
                            "L4", "W5", "L5", "Comment", "Surface", "Court", "Series", "Tier", "Best of"] if c in t]
        return r[cols].to_dict()
    if source == "api_tennis":
        for p in sorted((C.HANDOFF / "api_tennis").glob("fixtures_*.csv*")):
            t = pd.read_csv(p, dtype=str, keep_default_na=False)
            h = t[t["event_key"] == key]
            if len(h):
                return h.iloc[0][["event_date", "event_first_player", "event_second_player", "event_winner",
                                  "event_final_result", "event_status", "scores_json", "tournament_round"]].to_dict()
        return {}
    if source == "open_tennis_data":
        t = pd.read_parquet(C.DUMP / "matches" / "open_tennis_data" / "completed.parquet")
        return t[t["match_id"] == key].iloc[0][["date", "player1_name", "player2_name", "winner_id", "player1_id",
                                                 "score", "status", "round", "best_of"]].to_dict()
    if source == "flashscore":
        t = pd.read_parquet(C.SNAP / "links" / "flashscore_records.parquet",
                            filters=[("fs_match_id", "=", key)])
        return t.iloc[0][["home_name", "away_name", "winner", "set_scores", "status", "surface", "round",
                          "tournament_name", "start_utc"]].to_dict()
    if source == "slam_feeds":
        site, rest = key.split(":", 1)
        if site == "ausopen":
            body = rest.split("@")[0]
            y, mid = body.split("/")
            f = "archived_draws.parquet" if rest.endswith("@archived_draw") else "matches.parquet"
            t = pq.read_table(C.DUMP / "points" / "ausopen" / f).to_pandas()
            h = t[(t["year"].astype(int) == int(y)) & (t["match_id"] == mid)]
            if f == "matches.parquet":
                h = h[h["route"].eq("api") if "@" not in rest else ~h["route"].eq("api")]
            return h.iloc[-1][["team1_names", "team2_names", "winner_team", "team1_score", "team2_score",
                               "match_status", "team1_seed", "team2_seed", "round_name"]].to_dict() if len(h) else {}
        y, ev, mid = rest.split("/")
        t = pq.read_table(C.DUMP / "points" / site / "matches.parquet",
                          columns=["year", "event", "match_id", "entry.team1.lastNameA", "entry.team2.lastNameA",
                                   "entry.winner", "entry.score_text", "entry.statusCode", "entry.team1.seed",
                                   "entry.team2.seed", "entry.roundCode"]).to_pandas()
        h = t[(t["year"].astype(int) == int(y)) & (t["event"] == ev) & (t["match_id"].astype(str) == mid)]
        return h.iloc[-1].to_dict() if len(h) else {}
    if source == "wta_api":
        tid, y, mid = key.split(":", 1)[1].split("/")
        t = pq.read_table(C.DUMP / "points" / "wta" / "matches" / f"{y}.parquet",
                          columns=["tournament_id", "match_id", "PlayerNameLastA", "PlayerNameLastB", "Winner",
                                   "ScoreString", "SeedA", "SeedB", "RoundID", "draw"]).to_pandas()
        h = t[(t["tournament_id"].astype(str) == tid) & (t["match_id"].astype(str) == mid)]
        return h.iloc[-1].to_dict() if len(h) else {}
    if source == "tdi":
        t = pd.read_parquet(C.DUMP / "points" / "tdi" / "matches.parquet",
                            columns=["match_id", "team_a_names", "team_b_names", "team_a_scores", "team_b_scores",
                                     "description_score", "team_a_entry", "team_b_entry", "round"])
        return t[t["match_id"] == key.split(":", 1)[1]].iloc[0].to_dict()
    if source == "sofascore":
        eid = int(key.split(":", 1)[1])
        for c in ("sofascore", "sofascore_editions", "sofascore_tournaments"):
            t = pd.read_parquet(C.DUMP / "points" / c / "events.parquet",
                                columns=["event_id", "home_name", "away_name", "winner_code", "home_set1", "away_set1",
                                         "home_set2", "away_set2", "home_set3", "away_set3", "home_tb1", "away_tb1",
                                         "status_description", "home_seed", "away_seed", "ground_type", "round_name"])
            h = t[pd.to_numeric(t["event_id"], errors="coerce") == eid]
            if len(h):
                return h.iloc[0].to_dict()
        return {}
    if source == "live_tennis_api":
        t = pd.read_parquet(C.DUMP / "matches" / "live_tennis_api_zenodo" / "matches.parquet")
        h = t[t["match_id"].astype(str) == key]
        return h.iloc[0][["player1_id", "player2_id", "tournament", "surface", "indoor", "best_of", "round",
                          "event_status", "is_qualifying"]].to_dict() if len(h) else {}
    if source == "infosys":
        y, tid, code = key.split("_")
        for d in ("infosys_deep", "infosys_full"):
            for p in sorted((C.HANDOFF / d).glob(f"{y}_data.jsonl*")):
                op = gzip.open if p.suffix == ".gz" else open
                with op(p, "rt", encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        if f'"match_id": "{code}"' not in line and f'"match_id":"{code}"' not in line:
                            continue
                        r = json.loads(line)
                        if str(r.get("tournament_id")) == tid and r.get("match_id") == code:
                            ms = r.get("match_status") or {}
                            return {"file": p.name, "player1_name": r.get("player1_name"),
                                    "player2_name": r.get("player2_name"), "player1_seed": r.get("player1_seed"),
                                    "player2_seed": r.get("player2_seed"), "matchWinner": ms.get("matchWinner"),
                                    "matchStatus": ms.get("matchStatus"), "match_date": r.get("match_date")}
        return {}
    if source == "tennislive":
        parts = key.split(":")                 # tennislive:<tour>:<event number>:<match id>
        ek, mid = parts[1] + ":" + parts[2], ":".join(parts[3:])
        t = pd.read_parquet(C.DUMP / "points" / "tennislive" / "listed.parquet",
                            columns=["event_key", "match_id", "event_name", "round", "player1_name", "player2_name",
                                     "winner_side", "player1_sets", "player2_sets", "end_reason", "player1_seed",
                                     "player2_seed"], filters=[("event_key", "=", ek)])
        h = t[t["match_id"].astype(str) == mid]
        return h.iloc[0].to_dict() if len(h) else {}
    if source == "wta_site":
        k = key.split(":", 1)[1]
        if k.startswith("api:"):
            t = pd.read_parquet(C.DUMP / "points" / "wta" / "player_results" / "2026.parquet")
            h = t[t["match_key"].astype(str) == k[4:]]
            return h.iloc[0][["title", "round_name", "winner_name", "loser_name", "scores", "reason_code",
                              "winner_seed", "loser_seed"]].to_dict() if len(h) else {}
        it = pd.read_csv(C.RAW / "gap_sources" / "bwandowando" / "matches.csv", low_memory=False, chunksize=500_000,
                         usecols=["pseudo_match_id", "team_name_1", "team_name_2", "winner", "scores", "reason_code",
                                  "round_name", "player_1", "player_2"])
        for ch in it:
            h = ch[ch["pseudo_match_id"].astype(str) == k]
            if len(h):
                return h.iloc[0].to_dict()
        return {}
    if source == "tml":
        f, row = key.rsplit(":", 1)
        for p in sorted((C.DUMP / "matches" / "tennis_my_life").glob("*/*.parquet")):
            t = pq.read_table(p, columns=["_source_file", "_row", "winner_name", "loser_name", "score", "surface",
                                          "tourney_level", "indoor", "winner_seed", "loser_seed"]).to_pandas()
            h = t[(t["_source_file"] == f) & (t["_row"].astype(str) == row)]
            if len(h):
                return h.iloc[0].to_dict()
        return {}
    return {}


def dob_checks(n: int) -> None:
    """Birth-date readers: for each source, n random Stage 0 players with a date from it, the raw record found by the
    source's own key in its own file, the date ctx_dob read, and Stage 0's name and Sackmann's date."""
    d = pd.read_parquet(X.WORK / "dob_players.parquet")
    sack = {t: pd.read_parquet(C.DUMP / "players" / "sackmann_archive" / t / f"{t}_players.parquet")
            for t in ("atp", "wta")}
    tml = pd.read_parquet(C.DUMP / "players" / "tennis_my_life" / "ATP_Database.parquet")
    lta = pd.read_parquet(C.DUMP / "players" / "live_tennis_api_zenodo" / "players.parquet")
    otd = pd.read_parquet(C.DUMP / "players" / "open_tennis_data" / "players.parquet")
    wpm = pd.read_parquet(C.DUMP / "points" / "wta" / "player_matches" / "2026.parquet",
                          columns=["asked_id", "asked_fullName", "asked_dateOfBirth", "opponent_id",
                                   "opponent_fullName", "opponent_dateOfBirth"])
    for s in ("sackmann", "tennis_abstract", "open_tennis_data", "tml", "wta_api", "live_tennis_api"):
        smp = d[d[s].notna()].sample(min(n, int(d[s].notna().sum())), random_state=SEED)
        print(f"\n==================== dob: {s}")
        for _, r in smp.iterrows():
            pid = r["player_id"]
            tour, num = pid.split(":", 1)
            print(f"--- {pid}  stage0 name={r['name']}  read={pd.Timestamp(r[s]).date()}  "
                  f"sackmann={'' if pd.isna(r['sackmann']) else pd.Timestamp(r['sackmann']).date()}")
            if s == "sackmann":
                q = sack[tour][sack[tour]["player_id"].astype(str) == num]
                print("  raw: " + q[["player_id", "name_first", "name_last", "dob"]].to_string(index=False, header=False))
            elif s == "open_tennis_data":
                q = otd[otd["player_id"] == pid]
                print("  raw: " + q[["player_id", "name", "birth_date", "preferred_source"]].to_string(index=False, header=False))
            elif s == "live_tennis_api":
                q = lta[lta["sackmann_id"].astype(str).str.replace(".0", "", regex=False) == num]
                print("  raw: " + q[["player_id", "name", "tour", "birthday", "sackmann_id"]].to_string(index=False, header=False))
            elif s == "tml":
                q = tml[tml["player"].str.lower() == str(r["name"]).lower()]
                print("  raw (by name): " + q[["id", "player", "birthdate"]].to_string(index=False, header=False))
            elif s == "wta_api":
                q = wpm[wpm["asked_fullName"].str.lower() == str(r["name"]).lower()].drop_duplicates("asked_id")
                q2 = wpm[wpm["opponent_fullName"].str.lower() == str(r["name"]).lower()].drop_duplicates("opponent_id")
                print("  raw (by name): " + q[["asked_id", "asked_fullName", "asked_dateOfBirth"]].to_string(index=False, header=False)
                      + " | " + q2[["opponent_id", "opponent_fullName", "opponent_dateOfBirth"]].head(2).to_string(index=False, header=False))
            elif s == "tennis_abstract":
                hit = []
                import glob
                for f in glob.glob(str(C.HANDOFF / "tennis_abstract" / "player_bios_*.jsonl")):
                    with open(f, encoding="utf-8") as fh:
                        for line in fh:
                            if f'"sackmann_id": "{num}"' in line:
                                rr = json.loads(line)
                                hit.append(f"{rr.get('fullname')} {rr.get('dob_iso')} id={rr.get('sackmann_id')}")
                print("  raw: " + " | ".join(hit[:3]))


def stage0_raw(m_row) -> dict:
    """Stage 0's own source row: Sackmann's or TML's staged row by (_source_file, _row)."""
    f, row = m_row["source_file"], str(m_row["source_row"])
    base = C.DUMP / "matches" / ("sackmann_archive" if m_row["source"] == "sackmann" else "tennis_my_life")
    for p in sorted(base.glob("**/*.parquet")):
        names = set(pq.read_schema(p).names)
        if "_source_file" not in names:
            continue
        t = pq.read_table(p, columns=[c for c in ["_source_file", "_row", "tourney_name", "winner_name", "loser_name",
                                                  "score", "round"] if c in names],
                          filters=[("_source_file", "=", f)]).to_pandas()
        h = t[t["_row"].astype(str) == row]
        if len(h):
            return h.iloc[0].to_dict()
    return {}


def contradicted_checks(n: int) -> None:
    """n random rows of results_contradicted.csv: Stage 0's own source row and every contradicting source's raw row."""
    c = pd.read_csv(X.OUT / "results_contradicted.csv")
    m = X.stage0_matches().set_index("match_id")
    smp = pd.concat([c[c["field"].eq("winner")], c[c["field"].ne("winner")].sample(n, random_state=SEED)])
    links = {s: pd.read_parquet(X.WORK / f"results_{s}.parquet", columns=["match_id", "source_key"])
             for s in ("tennis_data", "api_tennis", "flashscore", "slam_feeds", "wta_api", "tdi", "sofascore",
                       "tennislive", "wta_site")}
    for _, r in smp.iterrows():
        mid = r["match_id"]
        print(f"\n--- {mid}  field={r['field']}  stage0={r['stage0_value']}  competing={r['competing_values']}")
        print("  stage0 row: " + "; ".join(f"{k}={v}" for k, v in stage0_raw(m.loc[mid]).items()))
        for s, lk in links.items():
            k = lk.loc[lk["match_id"].eq(mid), "source_key"]
            if len(k):
                print(f"  {s}: " + "; ".join(f"{a}={b}" for a, b in raw_row(s, k.iloc[0]).items()))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dob", action="store_true")
    ap.add_argument("--contradicted", action="store_true")
    ap.add_argument("--readers", default="tennis_data,api_tennis,open_tennis_data,flashscore,slam_feeds,wta_api,tdi,"
                                         "sofascore,live_tennis_api,infosys,tennislive,wta_site,tml")
    ap.add_argument("--n", type=int, default=5)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.dob:
        dob_checks(args.n)
        return 0
    if args.contradicted:
        contradicted_checks(args.n)
        return 0
    m = X.stage0_matches().set_index("match_id")
    for s in args.readers.split(","):
        r = pd.read_parquet(X.WORK / f"results_{s}.parquet")
        r = r[r["p1_side"].notna()]
        smp = r.sample(args.n, random_state=SEED)
        print(f"\n==================== {s}")
        for _, row in smp.iterrows():
            s0 = m.loc[row["match_id"]]
            print(f"--- {row['match_id']}")
            print(f"  stage0: A={s0['name_a']} B={s0['name_b']} a_won={s0['a_won']} score={s0['score']} "
                  f"status={s0['status_detail']} seeds=({s0['seed_a']}, {s0['seed_b']}) surface={s0['surface']} "
                  f"indoor={s0['indoor']} level={s0['level']} round={s0['round']}")
            print("  reader: " + "; ".join(f"{c}={row[c]}" for c in SHOW if c in row))
            print("  raw:    " + "; ".join(f"{k}={v}" for k, v in raw_row(s, row["source_key"]).items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
