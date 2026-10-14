"""F4 review (A2-skeptic), step 2: decide each group of f4_groups.csv.

Evidence, in order of strength:
  1. the Match Charting Project: the box equals the chart of one match (serve points within 2 for both players) and
     differs from the chart of the other by more than 5;
  2. Stage 0's B5/B9 and the games identity where service games exist (WTA from February 2015, ATP);
  3. points per game: where WTA service games are missing (before February 2015), the box's total serve points over
     the score's games, against the same tour's clean matches of 2010-2015 with a similar number of games (empirical
     percentile). A match is "implausible" outside the 0.1-99.9 percentile band and "plausible" inside 1-99.
A group is decided only when exactly one match is consistent and every other match is refuted; a match is "copy"
only when refuted. Groups where the box fits no match mark every match as refuted (foreign box).
Writes data/studies/input_data_audit/fixes/A2-skeptic/f4_decisions.csv
Run: ./python.sh src/eda/input_data_audit/review/A2-skeptic/f4_decide.py
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

import _common as K


def main() -> None:
    pd.set_option("display.width", 320)
    pd.set_option("display.max_colwidth", 60)
    t = pd.read_csv(K.OUT / "f4_groups.csv")
    # reference: clean Stage 0 matches 2010-2015, completed, with a box, by tour; total serve points / games
    d = pd.read_parquet(K.S0 / "stage0_match_players.parquet", columns=["match_id", "side", "svpt", "has_box", "games_won_d"])
    m = pd.read_parquet(K.S0 / "stage0_matches.parquet", columns=["match_id", "tour", "year", "status", "level"])
    d = d[d["has_box"]].groupby("match_id").agg(pts=("svpt", "sum"), games=("games_won_d", "first")).reset_index()
    d = d.merge(m, on="match_id")
    d = d[d["status"].eq("completed") & d["year"].between(2010, 2015) & d["games"].gt(0)]
    d["ppg"] = d["pts"] / d["games"]

    def pct(tour, games, ppg):
        ref = d[(d["tour"] == tour) & (d["games"].between(games - 3, games + 3))]["ppg"]
        return float((ref < ppg).mean() * 100), len(ref)

    pcs, ns = [], []
    for _, r in t.iterrows():
        if r["completed"]:
            p, n = pct(r["tour"], r["games"], r["pts_per_game"])
        else:
            p, n = np.nan, 0
        pcs.append(p)
        ns.append(n)
    t["ppg_percentile"] = pcs
    t["ppg_ref_n"] = ns

    def mcp_state(note):
        if not isinstance(note, str):
            return None
        mm = re.findall(r"serve_pts (\d+) \(box (\d+)", note)
        diffs = [abs(int(a) - int(b)) for a, b in mm]
        if all(x <= 2 for x in diffs):
            return "fits"
        if any(x > 5 for x in diffs):
            return "refutes"
        return None

    t["mcp_state"] = t["mcp"].map(mcp_state)

    def state(r):
        if r["mcp_state"] == "refutes":
            return "refuted", "MCP chart differs"
        if not (r["B5_pass"] and r["B9_pass"]):
            return "refuted", "fails Stage 0 B5/B9 on this score"
        if r["identity"] is not None and not pd.isna(r["identity"]) and str(r["identity"]) == "False":
            return "refuted", "games identity fails on this score"
        if r["mcp_state"] == "fits":
            return "consistent", "MCP chart equals the box"
        if r["identity"] is not None and str(r["identity"]) == "True":
            return "consistent", "identity holds"
        p = r["ppg_percentile"]
        if pd.isna(p):
            return "unknown", "retirement: points per game not testable"
        if p < 0.1 or p > 99.9:
            return "refuted", f"points per game {r['pts_per_game']} at percentile {p:.2f}"
        if 1 <= p <= 99:
            return "consistent", f"points per game {r['pts_per_game']} at percentile {p:.1f}"
        return "unknown", f"points per game {r['pts_per_game']} at percentile {p:.2f} (tail)"

    st = t.apply(state, axis=1, result_type="expand")
    t["state"], t["state_reason"] = st[0], st[1]
    roles = {}
    for gid, g in t.groupby("group_id"):
        cons = g[g["state"].eq("consistent")]
        refd = g[g["state"].eq("refuted")]
        if len(refd) == len(g):
            for i in g.index:
                roles[i] = "copy (box fits no match of the group)"
        elif len(cons) == 1 and len(refd) == len(g) - 1:
            for i in g.index:
                roles[i] = "genuine" if i == cons.index[0] else "copy"
        else:
            for i in g.index:
                roles[i] = "copy (refuted; owner undecided)" if i in refd.index else "undecided"
    t["role"] = [roles[i] for i in t.index]
    t.to_csv(K.OUT / "f4_decisions.csv", index=False)
    show = ["group_id", "event", "date", "round", "match", "stage0_has_box", "games", "pts_per_game", "ppg_percentile",
            "state", "state_reason", "role"]
    print(t[show].to_string())
    print(t.groupby(["role", "stage0_has_box"]).size())


if __name__ == "__main__":
    main()
