"""Hand checks of the atp_ readers (brief rule 8): for 5 random linked matches per reader (seed 20261016), print the
raw document's values (the raw JSON line of the handoff, the collector's decrypted raw file, else the staged rows),
simple tallies from the raw points for the recounts (counted here by a different, direct route: rows per server field,
endings per side), the reader's rows, and Stage 0's names of the linked players, for checking by eye.

Writes nothing to the study folders: prints to stdout (the session saved it in its scratchpad); the keys checked and
the verdicts are recorded in each reader's JSON by atp_handcheck_record.py.

Run: ./python.sh src/eda/source_reconciliation/atp_handcheck.py [reader ...]
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import atp_common as A  # noqa: E402

SEED = 20261016
SHOW = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_faced", "bp_saved", "sv_won"]
KS_NAMES = ["Aces", "Double Faults", "1st Serve", "1st Serve Points Won", "2nd Serve Points Won", "Break Points Saved",
            "Service Games Played", "Service Points Won"]


def sample(reader: str, n: int = 5, where=None) -> pd.DataFrame:
    r = pd.read_parquet(A.READERS / f"{reader}.parquet")
    r = r[r["match_id"].notna()]
    if where is not None:
        r = r[where(r)]
    keys = pd.Series(sorted(r["source_key"].unique())).sample(n, random_state=SEED).tolist()
    return r[r["source_key"].isin(keys)].sort_values(["source_key", "x_player_no"])


def show_reader(rows: pd.DataFrame) -> None:
    s = A.s0_players().set_index(["match_id", "player_id"])
    for _, x in rows.iterrows():
        nm = s["player_name"].get((x["match_id"], x["player_id"]))
        st = {c: s[c].get((x["match_id"], x["player_id"])) for c in SHOW if c in s}
        print(f"   reader p{x['x_player_no']} {x.get('x_code', '')} -> {x['player_id']} ({nm}) complete={x['complete']} "
              f"| " + " ".join(f"{c}={x[c]:g}" if pd.notna(x[c]) else f"{c}=-" for c in SHOW))
        print("        stage0 " + " ".join(f"{c}={v:g}" if pd.notna(v) else f"{c}=-" for c, v in st.items()))


def handoff_line(folder: str, file: str, line: int) -> dict:
    path = A.C.HANDOFF / folder / file
    op = gzip.open if path.suffix == ".gz" else open
    with op(path, "rt", encoding="utf-8", errors="replace") as fh:
        for n, ln in enumerate(fh, start=1):
            if n == line:
                return json.loads(ln)
    return {}


def ks_handoff() -> None:
    recs = pd.read_parquet(A.BOX / "atp_handoff_records.parquet",
                           columns=["source_key", "folder", "file", "line", "has_ks", "has_rally"])
    rows = sample("atp_ks_handoff")
    for key, g in rows.groupby("source_key"):
        rec = recs[(recs["source_key"] == key) & recs["has_ks"].fillna(False)].sort_values("folder").iloc[0]
        r = handoff_line(rec["folder"], rec["file"], int(rec["line"]))
        ks = r["keystats"]
        print(f"== {key} ({rec['folder']}/{rec['file']} line {rec['line']}) record players: "
              f"{r['player1_id']} {r['player1_name']} | {r['player2_id']} {r['player2_name']}; keystats players: "
              f"{[p.get('player1Id') for p in ks.get('players', [])]} matchCompleted={ks.get('matchCompleted')}")
        for e in ks["setStats"]["set0"]:
            if e["name"] in KS_NAMES:
                print(f"     {e['name']:<24} p1={e['player1']:<14} p2={e['player2']}")
        show_reader(g)


def mb_handoff() -> None:
    recs = pd.read_parquet(A.BOX / "atp_handoff_records.parquet",
                           columns=["source_key", "folder", "file", "line", "has_rally"])
    rows = sample("atp_mb_handoff_recount", where=lambda r: r["complete"])
    for key, g in rows.groupby("source_key"):
        rec = recs[(recs["source_key"] == key) & recs["has_rally"].fillna(False)].sort_values("folder").iloc[0]
        r = handoff_line(rec["folder"], rec["file"], int(rec["line"]))
        ra = r["rally_analysis"]
        tally = {"t1_points_won": 0, "t2_points_won": 0, "ace_t1": 0, "ace_t2": 0, "df_t1": 0, "df_t2": 0, "n": 0}
        for cat in ra["rallyData"]:
            for lst in ("t1err", "t1win", "t2err", "t2win"):
                for e in cat.get(lst) or []:
                    tally["n"] += 1
                    w = 1 if lst in ("t1win", "t2err") else 2
                    tally[f"t{w}_points_won"] += 1
                    if e.get("pointEndType") == "ACE":
                        tally[f"ace_t{w}"] += 1
                    if e.get("pointEndType") == "DOUBLE FAULT":
                        tally[f"df_t{3 - w}"] += 1
        print(f"== {key} rally playerDetails {[d.get('player1Id') for d in ra['playerDetails']]} record "
              f"{r['player1_id']} | {r['player2_id']}; raw tallies (aces by the side that won them, double faults "
              f"by the side that lost them): {tally}")
        show_reader(g)
        a = g.set_index("x_player_no")
        print(f"     check: ace p1={a.at[1, 'ace']:g} p2={a.at[2, 'ace']:g}; df p1={a.at[1, 'df']:g} p2={a.at[2, 'df']:g}; "
              f"points won p1 = sv_won1 + (svpt2 - sv_won2) = {a.at[1, 'sv_won'] + a.at[2, 'svpt'] - a.at[2, 'sv_won']:g}")


def staged_keystats(dump: Path, key: str) -> None:
    y, e, c = key.split("_")
    k = pd.read_parquet(dump / "keystats.parquet", columns=["year", "event_id", "match_id", "set_key", "name",
                                                            "player1", "player2"])
    k = k[(k["year"] == y) & (k["event_id"] == e) & (k["match_id"].str.upper() == c) & k["set_key"].eq("set0")]
    for n in KS_NAMES:
        x = k[k["name"] == n]
        if len(x):
            print(f"     {n:<24} p1={x['player1'].iloc[0]:<14} p2={x['player2'].iloc[0]}")


def staged_match(dump: Path, key: str) -> str:
    y, e, c = key.split("_")
    m = pd.read_parquet(dump / "matches.parquet")
    m = m[(m["year"] == y) & (m["event_id"] == e) & (m["match_id"].str.upper() == c)]
    if not len(m):
        return "(no staged match row)"
    x = m.iloc[0]
    return f"p1 {x['p1_id']} {x['p1_first_name']} {x['p1_last_name']} | p2 {x['p2_id']} {x['p2_first_name']} " \
           f"{x['p2_last_name']} winner={x['match_winner']} complete={x['is_match_complete']}"


def ks_backfill() -> None:
    rows = sample("atp_ks_backfill")
    for key, g in rows.groupby("source_key"):
        print(f"== {key} staged: {staged_match(A.ATP_DUMP, key)}")
        staged_keystats(A.ATP_DUMP, key)
        show_reader(g)


def mb_tally(dump: Path, key: str) -> None:
    y, e, c = key.split("_")
    p = pd.read_parquet(dump / "points.parquet", columns=["year", "event_id", "match_id", "server", "serve", "scorer",
                                                           "result"])
    p = p[(p["year"] == y) & (p["event_id"] == e) & (p["match_id"].str.upper() == c)]
    for s in ("1", "2"):
        q = p[p["server"] == s]
        print(f"     raw MatchBeats rows served by {s}: {len(q)}; serve==1: {(q['serve'] == '1').sum()}; "
              f"won on serve 1: {((q['serve'] == '1') & (q['scorer'] == s)).sum()}; won on serve 2: "
              f"{((q['serve'] == '2') & (q['scorer'] == s)).sum()}; result A: {(q['result'] == 'A').sum()}; "
              f"result P/DF: {q['result'].isin(['P', 'DF']).sum()}")


def recount_backfill() -> None:
    rows = sample("atp_backfill_recount", where=lambda r: r["complete"])
    for key, g in rows.groupby("source_key"):
        print(f"== {key} staged: {staged_match(A.ATP_DUMP, key)}")
        mb_tally(A.ATP_DUMP, key)
        show_reader(g)


def recount_ch() -> None:
    rows = sample("atp_ch_recount", where=lambda r: r["complete"] & r["x_route"].eq("match-beats"), n=4)
    rows = pd.concat([rows, sample("atp_ch_recount", where=lambda r: r["x_route"].eq("rally-analysis"), n=1)])
    for key, g in rows.groupby("source_key"):
        print(f"== {key} ({g['x_route'].iloc[0]}) staged: {staged_match(A.CH_DUMP, key)}")
        mb_tally(A.CH_DUMP, key)
        show_reader(g)


def ks_sirgenkii() -> None:
    rows = sample("atp_ks_sirgenkii")
    k = pd.read_parquet(A.SIRG / "atp_key_stats.parquet")
    k = k[k["set_n"].eq("0")]
    for key, g in rows.groupby("source_key"):
        y, e, c = key.split("_")
        x = k[(k["year"] == y) & (k["tournament_id"] == e) & (k["match_id"].str.upper() == c)]
        for _, r in x.iterrows():
            print(f"== {key} staged {r['player_id']} v {r['opponent_id']}: aces={r['aces']} df={r['double_faults']} "
                  f"serve1={r['serve1']} serve1_pts_won={r['serve1_pts_won']} serve2_pts_won={r['serve2_pts_won']} "
                  f"service_points_won={r['service_points_won']} svgames={r['service_games_played']} "
                  f"bp_faced={r['break_points_faced']} bp_saved_share={r['break_points_saved']} | return: "
                  f"s1ret={r['serve1_return_pts_won']} s2ret={r['serve2_return_pts_won']} rpw={r['return_points_won']} "
                  f"rgp={r['return_games_played']}")
        show_reader(g)
        for _, q in g.iterrows():
            if pd.notna(q["svpt"]) and q["svpt"] > 0:
                print(f"     check p{q['x_player_no']}: first_in/svpt={q['first_in'] / q['svpt']:.5f} "
                      f"first_won/first_in={q['first_won'] / max(q['first_in'], 1):.5f} "
                      f"second_won/(svpt-first_in)={q['second_won'] / max(q['svpt'] - q['first_in'], 1):.5f} "
                      f"sv_won/svpt={q['sv_won'] / q['svpt']:.5f}")


def recount_sirgenkii() -> None:
    rows = sample("atp_sirgenkii_recount", where=lambda r: r["complete"])
    r = pd.read_parquet(A.SIRG / "atp_rally_analysis.parquet", columns=["year", "tournament_id", "match_id",
                                                                         "player_id", "outcome", "point_end_type"])
    for key, g in rows.groupby("source_key"):
        y, e, c = key.split("_")
        x = r[(r["year"] == y) & (r["tournament_id"] == e) & (r["match_id"].str.upper() == c)]
        t = x.groupby(["player_id", "point_end_type", "outcome"]).size()
        print(f"== {key} raw rally rows {len(x)}; by subject, ending, outcome: {t.to_dict()}")
        show_reader(g)


def ks_daily() -> None:
    from src.eda.serve_speed_tabpfn.live import atp_daily as AD
    rows = sample("atp_ks_daily")
    for key, g in rows.groupby("source_key"):
        path = A.C.ROOT / g["x_file"].iloc[0]
        meta = AD.parse_path(path)
        with gzip.open(path, "rt", encoding="utf-8") as f:
            doc = AD.decrypt_envelope(json.load(f), year=meta["year"], path=path)
        ks = doc.get("stats", doc)
        print(f"== {key} raw (decrypted) players {[p.get('player1Id') + ' ' + str(p.get('player1Name')) for p in ks['players']]} "
              f"matchCompleted={ks.get('matchCompleted')}")
        for e in ks["setStats"]["set0"]:
            if e["name"] in KS_NAMES:
                print(f"     {e['name']:<24} p1={e['player1']:<14} p2={e['player2']}")
        show_reader(g)


def tdi_stats() -> None:
    rows = sample("atp_tdi_stats")
    st = pd.read_parquet(A.TDI / "statistics.parquet", columns=["match_id", "period", "label", "team_a", "team_b"],
                         filters=[("period", "==", "match")])
    m = pd.read_parquet(A.TDI / "matches.parquet", columns=["match_id", "team_a_atp_ids", "team_a_names",
                                                            "team_b_atp_ids", "team_b_names", "team_a_scores",
                                                            "team_b_scores"])
    for key, g in rows.groupby("source_key"):
        mid = key.split(":", 1)[1]
        x = m[m["match_id"] == mid].iloc[0]
        print(f"== {key} team A {x['team_a_atp_ids']} {x['team_a_names']} ({x['team_a_scores']}) | team B "
              f"{x['team_b_atp_ids']} {x['team_b_names']} ({x['team_b_scores']})")
        s = st[(st["match_id"] == mid) & st["label"].isin(["Aces", "Double Faults", "Service Games Played",
                                                            "Break Points Faced", "Break Points Saved",
                                                            "Total Service Points Won", "Total Return Points Won"])]
        for _, q in s.iterrows():
            print(f"     {q['label']:<26} A={q['team_a']:<5} B={q['team_b']}")
        show_reader(g)


def tdi_recount() -> None:
    rows = sample("atp_tdi_recount", where=lambda r: r["complete"])
    p = pd.read_parquet(A.TDI / "points.parquet", columns=["match_id", "team_serving", "winner", "serve", "faults",
                                                          "ace"])
    for key, g in rows.groupby("source_key"):
        mid = key.split(":", 1)[1]
        x = p[p["match_id"] == mid]
        for t in ("teamA", "teamB"):
            q = x[x["team_serving"] == t]
            first = q["serve"].eq("FIRST") | (q["serve"].eq("ACE") & q["faults"].eq("0"))
            print(f"     raw points served by {t}: {len(q)}; label first serves in: {first.sum()}; won on them: "
                  f"{(first & q['winner'].eq(t)).sum()}; aces: {q['ace'].eq('TRUE').sum()}; double faults: "
                  f"{q['serve'].eq('DOUBLE FAULT').sum()}; won: {q['winner'].eq(t).sum()}")
        print(f"== {key}")
        show_reader(g)


def mantd() -> None:
    rows = sample("atp_mantennisdata", where=lambda r: r["x_season"] >= 2018)
    files = {}
    for key, g in rows.groupby("source_key"):
        y = int(g["x_season"].iloc[0])
        if y not in files:
            files[y] = pd.concat([pd.read_parquet(A.MANTD / f"atp_matches_{yy}.parquet") for yy in (y, y + 1)
                                  if (A.MANTD / f"atp_matches_{yy}.parquet").exists()])
        mid = key.split(":", 1)[1]
        x = files[y][files[y]["id"] == mid].iloc[0]
        print(f"== {key} winner {x['winner_code']} {x['winner_name']} | loser {x['loser_code']} {x['loser_name']} "
              f"score {x['match_score']} {x['match_ret']}")
        for pre in ("win_", "los_"):
            print(f"     {pre} aces={x[pre + 'aces']} df={x[pre + 'double_faults']} 1st in/total="
                  f"{x[pre + 'first_serves_in']}/{x[pre + 'first_serves_total']} 1st won={x[pre + 'first_serve_points_won']} "
                  f"2nd won={x[pre + 'second_serve_points_won']} bp saved/faced={x[pre + 'break_points_saved']}/"
                  f"{x[pre + 'break_points_serve_total']} sv games={x[pre + 'service_games_played']} sv won="
                  f"{x[pre + 'service_points_won']}")
        show_reader(g)


CHECKS = {"atp_ks_handoff": ks_handoff, "atp_mb_handoff_recount": mb_handoff, "atp_ks_backfill": ks_backfill,
          "atp_backfill_recount": recount_backfill, "atp_ch_recount": recount_ch, "atp_ks_sirgenkii": ks_sirgenkii,
          "atp_sirgenkii_recount": recount_sirgenkii, "atp_ks_daily": ks_daily, "atp_tdi_stats": tdi_stats,
          "atp_tdi_recount": tdi_recount, "atp_mantennisdata": mantd}


def main() -> int:
    names = sys.argv[1:] or list(CHECKS)
    for n in names:
        print(f"\n######## {n}")
        CHECKS[n]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
