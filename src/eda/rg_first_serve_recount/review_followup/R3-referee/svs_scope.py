"""R3-referee, group SVS: sets_scope.csv (my values), the withdrawal of Stosur d. Halep from swaps_scope.csv, and the
"SVS" entry of verdict.json (run once).

A set is confirmed when (svs.py; svx_simulate.py --table proposed_sets.csv --tag _svs):
    - the first server is proven by the file under my stricter test, or, where the file only splits one game's points
      into two records of the same server, by the alternation of the merged games, with the row's own break points
      rejecting the other first server through the identity;
    - my truth (the score's alternation from that server) gives both values, equal to the proposal's;
    - the guards hold on the current rows (serve points; the counts replaced: blank, 0/0 or the row's values);
    - the truth passes the identity with the row's own break points (games won outside tiebreaks = service games -
      breaks conceded + breaks made), for both players;
    - no independent record holding the match reads another count or another first server;
    - with the candidate as it stands, the set changes only the row's two service-game counts, to the truth, and no
      check fails afterwards (the box is full, or stays partial for a count missing apart from the service games).
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/svs_scope.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3f as F  # noqa: E402
from addendum import alternation  # noqa: E402

STOSUR = "data/raw/public_dump/sackmann_archive/wta/wta_matches_2016.csv"


def main() -> int:
    vpath = F.OUT / "verdict.json"
    v = json.loads(vpath.read_text(encoding="utf-8"))
    if "SVS" in v:
        raise SystemExit("verdict.json already has an SVS entry")
    d = pd.read_csv(F.OUT / "svs_rows.csv", low_memory=False)
    sim = pd.read_csv(F.OUT / "svx_sim_rows_svs.csv", index_col=0)
    # the other first server, and whether the row's break points reject it
    rej = []
    for r in d.itertuples():
        aw, al = alternation(r.score, r.first_side != "w")
        differs = (aw, al) != (r.true_w, r.true_l)
        passes = (r.games_w_outside_tb == aw - r.breaks_w + r.breaks_l) and (r.games_l_outside_tb == al - r.breaks_l + r.breaks_w)
        rej.append(differs and not passes)
    d["other_first_server_rejected"] = rej
    s = sim.reindex(d["key"])
    t = pd.DataFrame({"key": d["key"]})
    t["first_server"] = (d["proven"].astype(bool) | d["other_first_server_rejected"]).to_numpy()
    t["values_equal_truth"] = d["values_equal_my_truth"].astype(bool).to_numpy()
    t["guards"] = (d["value_guard_ok"].astype(bool) & d["svpt_guard_ok"].astype(bool)).to_numpy()
    t["identity"] = d["consistent_truth"].astype(str).eq("True").to_numpy()
    against = pd.Series(False, index=d.index)
    for ref in ("cv", "mcp"):
        h = d[f"{ref}_holds"].fillna(False).astype(bool)
        against |= h & (~d[f"{ref}_reading"].eq("truth") | d[f"{ref}_first_agrees"].astype(str).eq("False"))
    t["no_record_against"] = (~against).to_numpy()
    t["checks_after"] = (s["B_box_status"].isin(["full", "partial"]) & ~s["B_B5"].fillna(False).astype(bool)
                         & ~s["B_B8"].fillna(False).astype(bool)).to_numpy()
    tests = ["first_server", "values_equal_truth", "guards", "identity", "no_record_against", "checks_after"]
    t["confirmed"] = t[tests].all(axis=1)
    raw_file = d["key"].str.rsplit("#", n=1).str[0]
    raw_row = d["key"].str.rsplit("#", n=1).str[1]
    scope = pd.DataFrame({"source_file": raw_file, "source_row": raw_row,
                          "w_SvGms": d["true_w"].astype("Int64"), "l_SvGms": d["true_l"].astype("Int64")})[t["confirmed"].to_numpy()]
    scope.to_csv(F.OUT / "sets_scope.csv", index=False)
    ps = pd.read_csv(F.FOLLOW / "service_games" / "proposed_sets.csv", dtype=str, keep_default_na=False)
    m = scope.astype(str).merge(ps[["source_file", "source_row", "w_SvGms", "l_SvGms"]], on=["source_file", "source_row"],
                                suffixes=("", "_lead"))
    same_values = int((m["w_SvGms"].eq(m["w_SvGms_lead"]) & m["l_SvGms"].eq(m["l_SvGms_lead"])).sum())
    # the withdrawal of Stosur d. Halep from the swaps
    sw = pd.read_csv(F.OUT / "swaps_scope.csv", dtype=str, keep_default_na=False)
    if not (F.OUT / "swaps_scope_810.csv").exists():
        shutil.copy2(F.OUT / "swaps_scope.csv", F.OUT / "swaps_scope_810.csv")
    stosur = sw["match_id"].str.contains("wta|2016-520|", regex=False) & sw["source_file"].eq(STOSUR)
    st_ids = sw[stosur & sw["match_id"].str.contains("R128|", regex=False)]
    halep = d.empty
    x = pd.read_csv(F.OUT / "svx_add2_rows.csv", low_memory=False)
    k = x.loc[x["winner_name"].eq("Samantha Stosur") & x["loser_name"].eq("Simona Halep"), "key"].iloc[0]
    drop = (sw["source_file"] + "#" + sw["source_row"]).eq(k)
    if drop.sum() != 1:
        raise SystemExit("Stosur d. Halep not found once in swaps_scope.csv")
    sw[~drop].to_csv(F.OUT / "swaps_scope.csv", index=False)
    smry = {"proposed": int(len(d)), "confirmed": int(len(scope)), "same_values_as_the_proposal": same_values,
            "tests_failed": {c: int((~t[c]).sum()) for c in tests},
            "first_server_by_merged_record_and_identity": d.loc[~d["proven"].astype(bool), ["winner_name", "loser_name",
                                                                                            "season"]].to_dict("records"),
            "fills_left_partial": int((s["B_box_status"].eq("partial")).sum()),
            "boxes_brought_back": int((s["A_box_status"].ne("full") & s["B_box_status"].eq("full")).sum()),
            "swaps_scope_rows_after_withdrawal": int((~drop).sum())}
    (F.OUT / "svs_scope.json").write_text(json.dumps(smry, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(smry, indent=1, default=str))
    if len(scope) != len(d) or same_values != len(d):
        print("not every set confirmed with the same values: write the verdict entry by hand")
        return 1
    v["SVS"] = {
        "vote": "confirm",
        "corrupt_beyond_doubt": True,
        "fix_clear_and_correct": True,
        "scope": ("All 558 proposed sets (sets_scope.csv, with my values, equal to the proposal's in all 558): 460 fills "
                  "(RG 2013 and 2014, 167 each, service games blank beside serve points; RG 2017, 126 recorded as 0 and 0) "
                  "and 98 others (AO 2019-2026 55; RG 2015 8, 2016 3, 2017 6, 2018 6, 2019 7, 2020 4, 2021 7, 2023 1, 2024 "
                  "1); set_svgms on Sackmann's row. Bar: the 8 Oct bar. Tests per match: the first server proven by the "
                  "file under my stricter test (557), or, for Pironkova d. Beck (RG 2014), whose file splits one game "
                  "into two records of the same server, by the merged alternation with the row's own break points "
                  "rejecting the other first server; my truth equal to the proposal's values; the operation's guards "
                  "holding on the current rows; the truth passing the break-point identity for both players; no record "
                  "against; and Stage 0's checks passing afterwards."),
        "reasons": ("Every value is mine: the score's alternation from the first server MatchBeats proves, a tiebreak "
                    "taking its turn uncounted and a retirement's score holding only finished games. MatchBeats' own "
                    "completed games equal it on 557 of the 558; on Pironkova d. Beck its raw count is one higher only "
                    "because the split game counts twice. The row's own break points confirm the first server "
                    "independently of MatchBeats: in all 300 sets where the other first server would give other counts, "
                    "the identity (games won outside tiebreaks = service games - breaks conceded + breaks made) rejects "
                    "it, and the truth passes the identity in all 558. The independent records agree wherever they hold "
                    "a match: Court Vision 33 and the hand charts 39, all reading the truth and naming the same first "
                    "server. The fills are missing counts by the row's own showing: blanks or 0 and 0 beside serve "
                    "points, which Stage 0 already treats as missing. The others are real errors, not another "
                    "convention. None counts tiebreak games. 90 give both players the same count where the score forces "
                    "different ones (one of them also a game short). The other 8 of RG 2015 move one game between the "
                    "players, which the alternation rules out. Struff d. Tiafoe (RG 2020) has 26 and 25 where both "
                    "tiebreaks fall on Struff's turns (truth 24 and 27). Every other fails the identity with the row's "
                    "own break points. The fix: on the candidate as it stands (809 swaps included), only the 558 rows "
                    "change, only in their two service-game counts, to the truth; every changed row of the whole frame "
                    "is named by a table; the guards hold; B5 failures fall from 12 to 11 and B8 stays 0; no row loses a "
                    "box. The sets bring back 455 boxes from 'service games missing' to full (RG 2013 164, RG 2014 164, "
                    "RG 2017 126, RG 2023 1). Six RG 2013-2014 fills stay partial because those rows lack double faults "
                    "too; their service games are still right, and the set is harmless."),
        "checks": [
            "svs.py: the 558 rows against my tables and the raw rows: my class, proof, truth, MatchBeats' count, the "
            "guards, the identity for the truth and the row, the row's convention for each other, the records "
            "(svs_rows.csv, svs_summary.json)",
            "svx_simulate.py --table proposed_sets.csv --tag _svs: the candidate as it stands (2,272 overrides; 2,393 "
            "corrections with the 809 swaps) with and without the 558 sets: 4,664 rows change on the whole frame, all "
            "named; only the 558 rows differ, only in w_SvGms and l_SvGms, all equal to the truth after; B5 12 -> 11, "
            "B8 0 -> 0; 455 rows no_svgms -> full; set rows after: 552 full, 6 partial (svx_sim_summary_svs.json, "
            "svx_sim_rows_svs.csv)",
            "svs_scope.py: the tests per set, 558/558 pass, values equal to the proposal's in 558/558 (svs_scope.json, "
            "sets_scope.csv)",
        ],
    }
    v["SVX_addendum2"]["scope"] += (" [Withdrawn after the SVS check: Stosur d. Halep (RG 2016 R128). The truth from "
                                    "MatchBeats' first server fails the break-point identity with the row's own break "
                                    "points while the row's counts pass it, and its file misses points, so the record "
                                    "and the row disagree and the exchange is not beyond doubt. swaps_scope.csv now "
                                    "holds 809 rows, the consensus's 809; the 810-row file is kept as "
                                    "swaps_scope_810.csv.]")
    v["other_findings"] += (
        " 19. SVS: the break-point identity is an independent check of the first server, built from Sackmann's break "
        "points and not MatchBeats' labels. It rejected the other first server wherever that would change the counts "
        "(300 of 300 sets), and among my 810 swaps it failed only for Stosur d. Halep, which I withdraw. 20. SVS: the "
        "other sets change values inside Stage 0's B5 tolerance in usable boxes, so they move hold rates without "
        "changing box status; only the fills (and one B5 failure, RG 2023) bring boxes back.")
    vpath.write_text(json.dumps(v, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
