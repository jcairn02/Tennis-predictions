"""Round 2, extra checks: (a) full raw / API counts for Bondar-Pieri and Rakhimova-Danilovic (Stage 0 blanked their
service games); (b) F1y: the three 2015 matches whose box Stage 0 drops: which of B0-B9 fail on the raw counts, and
whether all pass after svpt := svpt + df for both players. Prints only."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

X = pd.read_csv(R.OUT / "round2_checks.csv")
q21 = R.sack("wta", "wta_matches_qual_itf_2021.parquet").set_index("_row")
for mid, row in (("wta|2021-2028|Q2|wta:213620|wta:214388", 22855), ("wta|2021-2027|Q1|wta:215337|wta:215872", 22990)):
    raw = q21.loc[row]
    x = X[X["match_id"].eq(mid)].iloc[0]
    print(mid, raw["winner_name"], "d.", raw["loser_name"], raw["score"], "| API:", x["api_result"])
    print("   raw winner :", {b: raw[f"w_{b}"] for b in R.BOX})
    print("   raw loser  :", {b: raw[f"l_{b}"] for b in R.BOX})
    print("   API winner :", {b: x[f"apiW_{b}"] for b in R.BOX})
    print("   API loser  :", {b: x[f"apiL_{b}"] for b in R.BOX})
    exc = all(raw[f"l_{b}"] == x[f"apiW_{b}"] and raw[f"w_{b}"] == x[f"apiL_{b}"] for b in R.BOX)
    print("   raw exchanged == API on all 18:", exc)


def checks(c, o, score):
    gw, gl, tw, tl, ntb, ret = R.games_of(score)
    games = gw + gl
    bad = []
    for x in (c, o):
        if any(v < 0 for v in x.values()):
            bad.append("B0")
        if x["first_in"] > x["svpt"]:
            bad.append("B1")
        if x["first_won"] > x["first_in"]:
            bad.append("B2")
        if x["second_won"] > x["svpt"] - x["first_in"]:
            bad.append("B3")
        if x["bp_saved"] > x["bp_faced"]:
            bad.append("B4")
        if x["df"] > x["svpt"] - x["first_in"]:
            bad.append("B6")
        if x["ace"] > x["first_won"] + x["second_won"]:
            bad.append("B7")
        if pd.notna(x["sv_gms"]) and x["bp_faced"] - x["bp_saved"] > x["sv_gms"]:
            bad.append("B8")
    sv = c["sv_gms"] + o["sv_gms"]
    if pd.notna(sv) and not (abs(sv - (games - ntb)) <= 1 or abs(sv - games) <= 1):
        bad.append("B5")
    played = games - ntb - (1 if ret else 0)
    if c["svpt"] + o["svpt"] < 4.5 * played:
        bad.append("B9")
    return sorted(set(bad)), (c["svpt"] + o["svpt"]) / max(played, 1)


C = pd.read_csv(R.AUDIT / "fixes" / "round2_A_candidates.csv")
m, p = R.stage0()
mi = m.set_index("match_id")
s15 = R.sack("wta", "wta_matches_2015.parquet").set_index("_row")
f1 = pd.read_csv(R.OUT / "f1_scope_rows.csv")
print("\nF1y rows in the candidate file:", int(C["cand"].eq("F1y").sum()))
for r in C[C["cand"].eq("F1y")].to_dict("records"):
    raw = s15.loc[int(r["source_row"])]
    mr = mi.loc[r["match_id"]]
    w = {b: raw[f"w_{b}"] for b in R.BOX}
    l_ = {b: raw[f"l_{b}"] for b in R.BOX}
    before, ppg0 = checks(w, l_, raw["score"])
    w2, l2 = dict(w), dict(l_)
    w2["svpt"] += w2["df"]
    l2["svpt"] += l2["df"]
    after, ppg1 = checks(w2, l2, raw["score"])
    in_window_events = raw["tourney_name"] in set(f1["tourney_name"]) and str(raw["tourney_date"]) >= "20150223"
    print(f"{r['match_id']} | {raw['tourney_name']} {raw['tourney_date']} {raw['round']} {raw['winner_name']} d. "
          f"{raw['loser_name']} {raw['score']} | in the 30 events: {in_window_events} | Stage 0 has_box {mr['has_box']} "
          f"box_status {mr['box_status']}")
    print(f"    raw winner {w}\n    raw loser  {l_}")
    print(f"    checks failing on the raw counts: {before} (points per game {ppg0:.2f}); after svpt += df: {after} "
          f"(points per game {ppg1:.2f})")
    for side, x in (("winner", w), ("loser", l_)):
        print(f"    {side}: second serves in (svpt - first_in) {x['svpt'] - x['first_in']:.0f}, df {x['df']:.0f}, "
              f"second_won {x['second_won']:.0f} -> second-serve points after fix {x['svpt'] + x['df'] - x['first_in']:.0f}, "
              f"definition test after fix {x['second_won'] + x['df'] <= x['svpt'] + x['df'] - x['first_in']}")
