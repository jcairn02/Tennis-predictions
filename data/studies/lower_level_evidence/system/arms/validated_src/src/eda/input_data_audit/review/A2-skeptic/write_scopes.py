"""Reviewer A2-skeptic: write the confirmed scope files for F1-F4 from the per-candidate outputs.

Each row names the live Stage 0 match_id (and player_id for player-row fixes), Sackmann's _source_file and _row, and
for player rows which raw side (w_ or l_) the player sits on, checked by name against the raw row.
Writes data/studies/input_data_audit/fixes/A2-skeptic/{f1,f2,f3a,f3b,f4}_scope.csv
Run (after f1_wta2015.py, f2_swapped.py, f2_verdicts.py, f3_adelaide.py, f4_copies.py, f4_decide.py):
    ./python.sh src/eda/input_data_audit/review/A2-skeptic/write_scopes.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import _common as K


def raw_rows() -> pd.DataFrame:
    out = []
    for tour in ("atp", "wta"):
        r = K.sackmann(tour)
        r["tour"] = tour
        out.append(r)
    r = pd.concat(out, ignore_index=True)
    return r.set_index(["_source_file", "_row"])


def raw_side(raw: pd.DataFrame, src, row, name) -> str | None:
    try:
        x = raw.loc[(src, int(row))]
    except KeyError:
        return None
    if isinstance(x, pd.DataFrame):
        x = x.iloc[0]
    if K.name_key(x["winner_name"]) == K.name_key(name):
        return "w"
    if K.name_key(x["loser_name"]) == K.name_key(name):
        return "l"
    return None


def main() -> None:
    raw = raw_rows()
    p0 = pd.read_parquet(K.S0 / "stage0_match_players.parquet", columns=["match_id", "player_id", "player_name", "won"] + K.BOX)
    m0 = pd.read_parquet(K.S0 / "stage0_matches.parquet", columns=["match_id", "source_file", "source_row", "has_box"])

    # ---- F1: every player row of the 30 events (all of the candidate scope)
    f1 = pd.read_csv(K.OUT / "f1_scope_candidate.csv")
    f1["raw_side"] = [raw_side(raw, s, r, n) for s, r, n in zip(f1["source_file"], f1["source_row"], f1["player_name"])]
    f1["new_svpt"] = f1["svpt"] + f1["df"]
    f1["raw_column"] = f1["raw_side"] + "_svpt"
    f1 = f1[["match_id", "player_id", "player_name", "tournament_name", "tournament_date", "round", "source_file",
             "source_row", "raw_side", "raw_column", "svpt", "df", "new_svpt", "def_fail"]]
    f1.to_csv(K.OUT / "f1_scope.csv", index=False)
    print("F1 rows", len(f1), "matches", f1["match_id"].nunique(), "raw side unresolved", int(f1["raw_side"].isna().sum()),
          "rows changed (df>0)", int((f1["df"] > 0).sum()))

    # ---- F2: the confirmed matches; exchange all nine counts between the two players
    v = pd.read_csv(K.OUT / "f2_verdicts.csv")
    conf = v[v["verdict"].eq("confirm")].copy()
    rows = []
    for r in conf.itertuples():
        pr = p0[p0["match_id"].eq(r.match_id)]
        a, b = pr.iloc[0], pr.iloc[1]
        rows.append({"match_id": r.match_id, "player_id_1": a["player_id"], "player_name_1": a["player_name"],
                     "player_id_2": b["player_id"], "player_name_2": b["player_name"], "source_file": r.source_file,
                     "source_row": r.source_row, "operation": "exchange all nine counts between the two players",
                     **{f"p1_{c}": a[c] for c in K.BOX}, **{f"p2_{c}": b[c] for c in K.BOX}, "basis": r.reason})
    f2 = pd.DataFrame(rows)
    f2.to_csv(K.OUT / "f2_scope.csv", index=False)
    print("F2 confirmed matches", len(f2))

    # ---- F3: Adelaide 2 2022 copies that Stage 0 holds with a box
    t = pd.read_csv(K.OUT / "f3_adelaide2_2022_matches.csv")
    c = t[t["copy_of_2021"].notna() & t["stage0_has_box"].eq(True)].copy()
    out_a, out_b = [], []
    for r in c.itertuples():
        pr = p0[p0["match_id"].eq(r.match_id)]
        for _, p in pr.iterrows():
            side = raw_side(raw, r.source_file, r.source_row, p["player_name"])
            base = {"match_id": r.match_id, "player_id": p["player_id"], "player_name": p["player_name"],
                    "source_file": r.source_file, "source_row": r.source_row, "raw_side": side, "match": r.match,
                    "copy_of_2021": r.copy_of_2021}
            out_a.append({**base, "operation": "blank the box (all nine counts missing, has_box False)"})
            if bool(r.api_has_stats) and r.api_checks_on_2022_score == "pass":
                won = bool(p["won"])
                vals = {f"new_{k}": getattr(r, f"api_{'w' if won else 'l'}_{k}") for k in K.BOX}
                out_b.append({**base, "operation": f"replace all nine counts with the WTA API's ({r.api_key})", **vals})
            else:
                out_b.append({**base, "operation": "blank the box (no WTA API statistics: walkover)"})
    pd.DataFrame(out_a).to_csv(K.OUT / "f3a_scope.csv", index=False)
    pd.DataFrame(out_b).to_csv(K.OUT / "f3b_scope.csv", index=False)
    print("F3 matches", c["match_id"].nunique(), "rows", len(out_a), "replaced rows (F3b)",
          sum(1 for x in out_b if x["operation"].startswith("replace")))

    # ---- F4: copies (refuted for their own score) that Stage 0 holds with a box
    f4 = pd.read_csv(K.OUT / "f4_decisions.csv")
    cp = f4[f4["role"].str.startswith("copy") & f4["stage0_has_box"].eq(True)].copy()
    rows = []
    for r in cp.itertuples():
        pr = p0[p0["match_id"].eq(r.match_id)]
        rows.append({"match_id": r.match_id, "player_id_1": pr.iloc[0]["player_id"], "player_id_2": pr.iloc[1]["player_id"],
                     "tour": r.tour, "event": r.event, "date": r.date, "round": r.round, "match": r.match,
                     "source_file": r.source_file, "source_row": r.source_row, "group_id": r.group_id, "role": r.role,
                     "evidence": r.state_reason, "operation": "blank the box (all nine counts missing, has_box False)"})
    f4s = pd.DataFrame(rows)
    f4s.to_csv(K.OUT / "f4_scope.csv", index=False)
    print("F4 copies blanked", len(f4s))
    print(f4s[["event", "date", "round", "match", "evidence"]].to_string())


if __name__ == "__main__":
    main()
