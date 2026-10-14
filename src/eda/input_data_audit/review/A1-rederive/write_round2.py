"""Write data/studies/input_data_audit/fixes/A1-rederive/round2.json from round2_checks.csv (round2.py) and the extra
checks of round2_more.py (re-derived here)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

X = pd.read_csv(R.OUT / "round2_checks.csv")
C = pd.read_csv(R.AUDIT / "fixes" / "round2_A_candidates.csv")
out = {"F1x": [], "F2x": [], "F2y": [], "F4x": [], "F1y": []}

# ---------------- F1x
mcp_txt = {
    "wta|2015-W-PR-QAT-1A-2015|SF|wta:201425|wta:201521":
        "MCP 20150227 Doha SF: Safarova svpt 53 + df 2 = 55 = MCP serve points 55; Suarez Navarro 53 + 1 = 54 = MCP 54. "
        "first_in 42/42 and 38/38, first_won 28/28 and 18/18, second_won 9/9 and 7/7, aces 2/2 and 0/0 all equal MCP.",
    "wta|2015-W-PR-QAT-1A-2015|F|wta:201425|wta:201458":
        "MCP 20150228 Doha F: Safarova svpt 63 + df 2 = 65 = MCP 65; Azarenka 52 + 2 = 54 = MCP 54. first_won 33/33 and "
        "19/19, second_won 9/9 and 11/11, aces 7/7 and 6/6 equal MCP; first_in 47 vs 46 and 32/32."}
for r in C[C["cand"].eq("F1x")].to_dict("records"):
    out["F1x"].append({"match_id": r["match_id"], "vote": "confirm",
                       "fix": "svpt := svpt + df for both players; every other count unchanged",
                       "reasons": mcp_txt[r["match_id"]] + " All four player rows equal the charted serve points only once "
                                  "df is added (a coincidence of exactly df on four rows is not credible), and the other "
                                  "counts agree, so only svpt is wrong. Doha's SF/F (27-28 Feb) fall after the switch of "
                                  "the source to serve points without double faults; Doha's R32/R16 rows are inclusive "
                                  "per MCP and are not touched. Stage 0 holds the raw values; after the fix the definition "
                                  "test passes on all four rows."})

# ---------------- F2x
for r in C[C["cand"].eq("F2x")].to_dict("records"):
    x = X[X["match_id"].eq(r["match_id"])].iloc[0]
    fix = "exchange all nine counts between the two players (w_* <-> l_* on the raw row)"
    if bool(x["same_surname_pair"]):
        reason = (f"Not exchanged. The two players share a surname ({x['winner']} / {x['loser']}), so a surname-only link "
                  f"to the WTA API cannot tell them apart and orients the API's players arbitrarily. Linked by first and "
                  f"last name, the API's {x['api_match']} ({x['api_result']}) equals Stage 0's box AS RECORDED on "
                  f"{int(x['api_match_recorded_of18'])}/18 counts (exchanged: {int(x['api_match_exchanged_of18'])}/18), with "
                  f"the API's winner = the recorded winner. Orientation-free check: the box as recorded gives games "
                  f"{x['box_games_recorded']} for the score {x['score']} (non-tiebreak games {x['games_score']}), and the "
                  f"recorded winner wins {x['pts_W_recorded']:.0f} points to {x['pts_L_recorded']:.0f}. The apparent "
                  f"exchange is a linking artifact; exchanging would corrupt a correct box.")
        out["F2x"].append({"match_id": r["match_id"], "vote": "reject", "fix": fix, "reasons": reason})
        continue
    n_exc = int(x["api_match_exchanged_of18"])
    extra = ""
    if not bool(x["s0_equals_raw"]):
        extra = (" Stage 0 differs from the raw row only in service games, which Stage 0 blanked (B5) because Sackmann's "
                 "second-set score differs from the API's; on the raw row, with service games (equal for both players), "
                 "the exchanged box equals the API on all 18 counts.")
        n_exc = 18
    reason = (f"WTA API {x['api_event']} {x['api_match']} ({x['api_result']}): Stage 0's box equals the API's counts on "
              f"{n_exc}/18 only once the two boxes are exchanged (as recorded: {int(x['api_match_recorded_of18'])}/18); the "
              f"API's winner = the recorded winner; the two players' surnames differ, so the link is unambiguous "
              f"(first and last name). Games from the box as recorded: {x['box_games_recorded']} for the score {x['score']} "
              f"(non-tiebreak {x['games_score']}).{extra} The API equals Sackmann on all 18 counts in 99.4% of linked "
              f"matches outside the faulty events, so it measures what Sackmann measures.")
    out["F2x"].append({"match_id": r["match_id"], "vote": "confirm", "fix": fix, "reasons": reason})

# ---------------- F2y
out["F2y"].append({
    "match_id": "atp|2022-580|R128|atp:105332|atp:106329", "vote": "confirm",
    "fix": "exchange the two players' service games (sv_gms) only: Paire 26 -> 25, Monteiro 25 -> 26; every other count unchanged",
    "reasons": ("AO 2022 ball tracking (2022_MS146, 51 games, none with two servers): Monteiro served the first game and "
                "served 26 games (held 22, broken 4); Paire served 25 (held 21, broken 4). Stage 0 has Paire 26 and "
                "Monteiro 25, with breaks conceded 4 and 4 (bp 8/12 and 10/14), so its break counts are right and only the "
                "service games are exchanged. With sv_gms exchanged the box gives games 25-26, equal to the score "
                "6-4 3-6 7-5 2-6 7-5; as recorded it gives 26-25. The point counts (svpt 156/158, first_in 82/109, "
                "first_won 70/77, second_won 35/26, aces 30/13, DFs 13/3) equal the ball tracking AS RECORDED, so a "
                "whole-box exchange would be wrong (round 1 rejected it).")})

# ---------------- F4x
out["F4x"].append({
    "match_id": "wta|2012-W-SL-AUS-1A-2012|R128|wta:201419|wta:201584", "vote": "confirm",
    "fix": "blank the box (all nine counts of both players)",
    "reasons": ("Two independent records of AO 2012 R128 Li d. Pervak agree with each other and not with the box: MCP "
                "(Li 41 serve points, 0 aces, 0 DFs, 29 first serves in; Pervak 56, 0, 5, 31) and AO's own point-by-point "
                "(2012-ausopen-2116: Li 41 serve points, 25 won, 0 aces, 0 DFs; Pervak 56, 24, 0, 5). Stage 0's box (Li 50 "
                "serve points, 34 won, 3 aces, 1 DF; Pervak 46, 21, 0, 8) equals, count for count, Wimbledon 2012's "
                "point-by-point of the same pair (2012-wimbledon-2125) and Sackmann's Wimbledon 2012 row. The AO row "
                "therefore carries Wimbledon's box. Stage 0 holds the raw values (has_box True). Blanking is the stated "
                "fix and is correct.")})

# ---------------- F1y
s15 = R.sack("wta", "wta_matches_2015.parquet").set_index("_row")
txt = {185: "Stosur d. Koukalova 6-1 6-0: Koukalova has 9 double faults against 6 second serves in play (svpt 21 - first_in 15)",
       234: "Yang d. Beygelzimer 6-3 0-0 RET: Yang has 6 double faults against 2 second serves in play (svpt 26 - first_in 24)",
       306: "Ce d. Kania 6-2 7-6(7): Ce has 8 double faults against 6 second serves in play (svpt 72 - first_in 66)"}
games = {185: "Stosur 7 service games, 0 broken; Koukalova 6, 5 broken: 12-1 games = the score",
         234: "Yang 5 service games, 2 broken; Beygelzimer 4, 3 broken: 6-3 games = the score",
         306: "Ce 10 service games, 6 broken; Kania 10, 8 broken: 12-8 non-tiebreak games = the score"}
for r in C[C["cand"].eq("F1y")].to_dict("records"):
    row = int(r["source_row"])
    raw = s15.loc[row]
    out["F1y"].append({
        "match_id": r["match_id"], "vote": "confirm",
        "fix": "svpt := svpt + df for both players (on the raw row, before Stage 0's checks); every other count unchanged",
        "reasons": (f"{raw['tourney_name']} 2015 is one of the 30 events in the window (F1). {txt[row]}, so B6 fails. That "
                    "is impossible if serve points include double faults (a double fault is a lost second-serve point), "
                    "and it is the window's convention at its most visible. On the raw counts only B6 fails. After "
                    "svpt := svpt + df for both players every check B0-B9 passes, the definition test holds on both rows, "
                    f"points per game are normal, and the games identity fits exactly ({games[row]}). The fix is the F1 "
                    "fix that round 1 confirmed for the event's other rows. The 4th B6 failure, Nottingham QF "
                    "Konjuh-Vickery, is not proposed and would still fail B9 after the fix.")})

R.OUT.joinpath("round2.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
chk = json.loads(R.OUT.joinpath("round2.json").read_text(encoding="utf-8"))
for k, v in chk.items():
    print(k, {x: sum(1 for i in v if i["vote"] == x) for x in ("confirm", "reject")})
