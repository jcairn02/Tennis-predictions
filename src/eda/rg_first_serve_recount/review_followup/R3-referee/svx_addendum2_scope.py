"""R3-referee, group SVX addendum 2 (RG 2016-2018): append the confirmed swaps to swaps_scope.csv (the 705 rows kept, a
copy kept as swaps_scope_round2.csv) and add "SVX_addendum2" to verdict.json (once).

A swap is confirmed on the same tests as the SVX addendum (svx_addendum.py --editions RG2016-2018 --tag 2;
svx_simulate.py --table addendum2_swaps.csv --base-extra addendum_swaps.csv --tag _add2): the first server proven by
the file under my stricter test; the row's two counts the truth's two exchanged, the truth's two differing;
MatchBeats' completed games equal to the truth; no hand chart holding the match reading the row or naming another first
server; with the candidate as it stands plus the swaps already confirmed, only the row's two counts change, exchanged,
to the truth, and Stage 0's checks pass.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/svx_addendum2_scope.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3f as F  # noqa: E402


def main() -> int:
    vpath = F.OUT / "verdict.json"
    v = json.loads(vpath.read_text(encoding="utf-8"))
    if "SVX_addendum2" in v:
        raise SystemExit("verdict.json already has an SVX_addendum2 entry")
    if not (F.OUT / "swaps_scope_round2.csv").exists():
        shutil.copy2(F.OUT / "swaps_scope.csv", F.OUT / "swaps_scope_round2.csv")
    base = pd.read_csv(F.OUT / "swaps_scope_round2.csv", dtype=str, keep_default_na=False)
    if len(base) != 705:
        raise SystemExit(f"expected my 705 rows, found {len(base)}")
    d = pd.read_csv(F.OUT / "svx_add2_rows.csv", low_memory=False)
    sim = pd.read_csv(F.OUT / "svx_sim_rows_add2.csv", index_col=0)
    ad = pd.read_csv(F.FOLLOW / "review" / "addendum2_swaps.csv", dtype=str, keep_default_na=False)
    ad["key"] = F.rowkey(ad["source_file"], ad["source_row"])
    p = d.set_index("key").reindex(ad["key"])
    mch = p["mcp_holds"].fillna(False).astype(bool)
    t = pd.DataFrame({"key": ad["key"].to_numpy()})
    t["swapped_and_proven"] = p["my_cls"].eq("swapped").to_numpy()
    t["mb_equals_truth"] = (p["mb_w"].eq(p["true_w"]) & p["mb_l"].eq(p["true_l"])).to_numpy()
    against = mch & (p["mcp_reading"].isin(["row", "neither"]) | p["mcp_first_agrees"].astype(str).eq("False"))
    t["no_record_against"] = (~against).to_numpy()
    s = sim.reindex(ad["key"])
    t["full_after_no_b5_b8"] = (s["B_box_status"].eq("full") & ~s["B_B5"].fillna(False).astype(bool)
                                & ~s["B_B8"].fillna(False).astype(bool)).to_numpy()
    tests = ["swapped_and_proven", "mb_equals_truth", "no_record_against", "full_after_no_b5_b8"]
    t["confirmed"] = t[tests].all(axis=1)
    conf = ad[t["confirmed"].to_numpy()][["source_file", "source_row", "match_id"]]
    out = pd.concat([base, conf], ignore_index=True)
    if out.duplicated(["source_file", "source_row"]).any():
        raise SystemExit("a swap named twice")
    out.to_csv(F.OUT / "swaps_scope.csv", index=False)
    ps = pd.read_csv(F.FOLLOW / "service_games" / "proposed_swaps.csv", dtype=str, keep_default_na=False)
    same = set(F.rowkey(out["source_file"], out["source_row"])) == set(F.rowkey(ps["source_file"], ps["source_row"]))
    smry = {"addendum2_swaps": int(len(ad)), "confirmed": int(len(conf)),
            "tests_failed": {c: int((~t[c]).sum()) for c in tests}, "held_by_a_chart": int(mch.sum()),
            "scope_rows_after": int(len(out)), "scope_equals_the_proposal": bool(same), "proposal_rows": int(len(ps))}
    (F.OUT / "svx_add2_scope.json").write_text(json.dumps(smry, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(smry, indent=1))
    if len(conf) != len(ad):
        print("not every swap confirmed: write the verdict entry by hand")
        return 1
    v["SVX_addendum2"] = {
        "vote": "confirm",
        "corrupt_beyond_doubt": True,
        "fix_clear_and_correct": True,
        "scope": ("All 105 swaps of addendum2_swaps.csv, appended to swaps_scope.csv after my 705 (810 rows, equal to the "
                  "proposal's 810): RG 2016 43, 2017 10, 2018 52; exchange_svgms on Sackmann's row. Bar: the 8 Oct bar. "
                  "Tests per match, from my own code: the first server proven by the RG 2016-2018 MatchBeats file under my "
                  "stricter test (105 of 105); the row's two counts the truth's two exchanged, the truth's two differing; "
                  "MatchBeats' own completed games equal to the truth; no hand chart holding the match reading the row or "
                  "naming another first server; with the candidate as it stands plus the 382 swaps of the first addendum, "
                  "only the row's two counts change, exchanged, to the truth, and Stage 0's checks pass. Nothing added: "
                  "my derivation finds no other swap in these editions."),
        "reasons": ("My decryption of the 1,333 RG 2016-2018 files on the API route (none failing) and my link to "
                    "Sackmann's rows by tour, draw, round and both names (every file placed, no tie; the 105 swaps 100 exact "
                    "and 5 name variants: Ramos-Vinolas, Ekaterina Makarova, Kateryna Kozlova) find exactly the lead's 105, "
                    "and my stricter proof passes all of them. MatchBeats' own completed non-tiebreak games equal the truth "
                    "on all 105 (104 files holding every point; Stosur d. Halep 2016 misses some points but holds every "
                    "game). The only independent record for these years is the hand charts (Court Vision's copy starts in "
                    "2019): they hold 47 matches with a file, name MatchBeats' first server on all 46 that have one (the "
                    "47th, Watson d. Gibbs 2016, is one of the matches without a file), read the row's own count wherever it equals the truth (29), "
                    "and on the 3 swaps they hold (Thiem d. Zverev 2018 QF, Muguruza d. Sharapova 2018 QF, Williams d. "
                    "Pereira 2016 R64) read the truth, never the row. The other 102 rest on the file and the score, the "
                    "same evidence that the records confirmed on the 705 swaps before (no record has read a row in 351 "
                    "readings). 85 rows are the score as if the winner had served first when the loser did, 20 the other "
                    "way; 3 are retirements. The fix: on the candidate as it stands plus the first addendum's 382, only "
                    "the 105 rows change, only in their two service-game counts, exchanged; all 105 then equal the truth; "
                    "every changed row of the whole frame is named by a table (exchange_svgms on 811 rows); B5 failures "
                    "stay 12 and B8 failures 0 across 12,762 AO, RG and Olympic rows; no row loses a box."),
        "checks": [
            "svx_addendum.py --editions RG2016-2018 --tag 2 --list addendum2_swaps.csv: files, links, my proof, truth and "
            "classes; the lead's 105 found, all swapped and proven; no swap outside the list; the chart readings "
            "(svx_add2_rows.csv, svx_add2_summary.json)",
            "svx_simulate.py --table addendum2_swaps.csv --base-extra addendum_swaps.csv --tag _add2: the candidate as "
            "confirmed (2,272 overrides; 1,907 corrections with the 323 round-1 swaps) plus the first addendum's 382, "
            "with and without the 105: 4,107 rows change on the whole frame, all named; only the 105 rows differ, only "
            "in w_SvGms and l_SvGms, exchanged; all 105 equal the truth after; B5 12 -> 12, B8 0 -> 0, no status change, "
            "no row loses a box (svx_sim_summary_add2.json)",
            "svx_addendum2_scope.py: the tests per swap, 105/105 pass; swaps_scope.csv 810 rows, equal to the proposal's "
            "810 (svx_add2_scope.json; my 705-row scope kept as swaps_scope_round2.csv)",
        ],
    }
    v["other_findings"] += (
        " 17. SVX addendum 2: RG 2017's 132 'other' matches all give the two players equal service games; 123 of them "
        "carry 0 and 0, which Stage 0 treats as missing (its rule for service games recorded as 0 with serve points "
        "played), not a B5 failure; 6 have the right total split equally where the score forces unequal counts; 3 are "
        "8-13 games short. Where the first server is proven, the score's alternation would fill or correct them as the "
        "RG 2026 zeros were filled; not proposed, so not voted. 18. SVX addendum 2: my proof test agrees with the "
        "lead's new strict flag on RG 2016-2018. AO 2019 MS140, which that flag fails, passes mine: the split set "
        "records keep set 3 and run games 9 and 10 on from 8, so my game-sequence check sees no repeat or gap. The "
        "chart and Court Vision readings confirm it either way.")
    vpath.write_text(json.dumps(v, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
