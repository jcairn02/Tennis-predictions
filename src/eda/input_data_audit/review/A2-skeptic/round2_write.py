"""Round 2 (A2-skeptic): write data/studies/input_data_audit/fixes/A2-skeptic/round2.json from round2.py / round2b.py
evidence (round2_detail_f2x.csv and the checks printed by round2b.py, restated here).
Run: ./python.sh src/eda/input_data_audit/review/A2-skeptic/round2_write.py
"""
from __future__ import annotations

import json

import pandas as pd

import _common as K

EXCH = "exchange all nine counts between the two players (w_* <-> l_* on the raw row)"
SVPT = "svpt := svpt + df for both players (raw w_svpt += w_df and l_svpt += l_df); every other count unchanged"

SAME_SURNAME = {
    "wta|2019-1052|R16|wta:201662|wta:201697": "Kristyna d. Karolina Pliskova",
    "wta|2020-M004|R32|wta:206374|wta:216016": "Xiyu d. Yafan Wang (WTA API 1002/2020/LS031)",
    "wta|2021-1052|Q1|wta:202916|wta:206391": "Georgina Garcia Perez d. Ellen Perez",
    "wta|2024-1049|R16|wta:216016|wta:216133": "Xiyu d. Xin Yu Wang",
    "wta|2024-1096|R32|wta:202492|wta:216016": "Xiyu d. Qiang Wang",
    "wta|2024-1075|R32|wta:222965|wta:259799": "Erika d. Mirra Andreeva",
    "wta|2025-1038|R128|wta:206368|wta:221236": "Veronika d. Polina Kudermetova",
    "wta|2025-822|R32|wta:206368|wta:221236": "Veronika d. Polina Kudermetova",
    "wta|2026-1156|R16|wta:216055|wta:221164": "Francisca d. Matilde Jorge",
}
SCORE_NOTE = {
    "wta|2021-2028|Q2|wta:213620|wta:214388": "The API scores it 4-6 7-5 7-5 (Sackmann 4-6 6-4 7-5) and its box fits that score exactly; Stage 0 keeps no service games (B5) either way. The score is a separate fault, not fixed here.",
    "wta|2021-2028|R64|wta:206107|wta:213550": "The API's own box is one game off its own score (7-6(4) 6-3; Sackmann 7-6(4) 6-2), so the identity cannot decide; the orientation is decided by points: as recorded the winner of 13-8 games wins 89 of 190 points, after the exchange 101.",
    "wta|2021-2027|Q1|wta:215337|wta:215872": "The API scores it 7-6(7) 6-2 (Sackmann 7-6(7) 6-4) and its box fits that score exactly; after the exchange Rakhimova's 13 games fit both scores. The score is a separate fault, not fixed here.",
    "wta|2021-2027|R16|wta:206255|wta:213525": "Retirement (the API has 6-3 4-3 Ret'd against Sackmann's 6-3 3-3 RET); as recorded the player leading 9-6 in games has 53 of 116 points, after the exchange 63.",
    "wta|2021-2028|R32|wta:201465|wta:213550": "Retirement at 5-7 5-4: the identity and points cannot decide the orientation inside the match; the WTA API (the source Sackmann transcribes) decides, as in every testable match of the same event.",
    "wta|2021-2027|R64|wta:201492|wta:215020": "Both orientations fit the games identity here, so the WTA API decides, as in every testable match of the same event.",
    "wta|2021-2027|R64|wta:201478|wta:211702": "Retirement at 6-3 3-0: as recorded the leader (9-3 in games) has 30 of 74 points, after the exchange 44.",
}


def f2x_items() -> list[dict]:
    x = pd.read_csv(K.OUT / "round2_detail_f2x.csv")
    out = []
    for r in x.itertuples():
        if r.match_id in SAME_SURNAME:
            out.append({"match_id": r.match_id, "vote": "reject", "fix": "none",
                        "reasons": (f"Same-surname pair ({SAME_SURNAME[r.match_id]}). Matched to the WTA API by full name, the API "
                                    f"record ({r.api_key if isinstance(r.api_key, str) else '1002/2020/LS031'}) equals Stage 0's box AS "
                                    f"RECORDED on 18 of 18 counts; the 'exchanged' match came from matching by surname only, which cannot "
                                    f"tell the two players apart (my round-1 list of 25 included it). Nothing is exchanged.")})
            continue
        n = int(r.fields)
        bits = [f"WTA API {r.api_key} ({r.api_result}) equals Stage 0's box exchanged on {int(r.equal_exchanged)} of {n} counts "
                f"(as recorded {int(r.equal_as_recorded)})" + (" and the raw service games are equal both ways" if n == 16 else ""),
                f"API winner = Stage 0 winner; progression: {r.progression}"]
        if r.api_identity_excl_tb is True or str(r.api_identity_excl_tb) == "True":
            bits.append("the API's own box fits its own score (games identity, tiebreaks credited)")
        if str(r.stage0_identity_exchanged) == "True" and str(r.stage0_identity_as_recorded) == "False":
            bits.append("Stage 0's box fits the score only exchanged")
        bits.append(f"points won as recorded {r.winner_pts_as_recorded:g}-{r.loser_pts_as_recorded:g}, after the exchange "
                    f"{r.loser_pts_as_recorded:g}-{r.winner_pts_as_recorded:g}")
        reason = "; ".join(bits) + "."
        if r.match_id in SCORE_NOTE:
            reason += " " + SCORE_NOTE[r.match_id]
        out.append({"match_id": r.match_id, "vote": "confirm", "fix": EXCH, "reasons": reason})
    return out


def main() -> None:
    res = {
        "reviewer": "A2-skeptic",
        "F1x": [
            {"match_id": "wta|2015-W-PR-QAT-1A-2015|SF|wta:201425|wta:201521", "vote": "confirm", "fix": SVPT,
             "reasons": "Match Charting Project 20150227-W-Doha-SF: svpt + df equals the charted serve points for both players "
                        "(Safarova 53+2 = 55, Suarez Navarro 53+1 = 54) with first serves in, first- and second-serve points "
                        "won and double faults all equal; svpt alone is off by exactly df. Read inclusively, Safarova would have "
                        "won 9 of 9 second serves in play. The box fits the score exactly (games identity 12-5) and is not a copy "
                        "of any other raw row. Doha's charted R32/R16 rows equal MCP with svpt alone (inclusive), so the SF and F "
                        "came in the other convention, as the window events did that week."},
            {"match_id": "wta|2015-W-PR-QAT-1A-2015|F|wta:201425|wta:201458", "vote": "confirm", "fix": SVPT,
             "reasons": "Match Charting Project 20150228-W-Doha-F: svpt + df equals the charted serve points for both players "
                        "(Safarova 63+2 = 65, Azarenka 52+2 = 54); first-serve and second-serve points won and double faults "
                        "equal (Safarova's first serves in 47 against 46). Games identity exact (12-7), checks pass before and "
                        "after, no copy elsewhere."},
        ],
        "F2x": f2x_items(),
        "F2y": [
            {"match_id": "atp|2022-580|R128|atp:105332|atp:106329", "vote": "confirm",
             "fix": "exchange the two players' sv_gms only (Paire 26 -> 25, Monteiro 25 -> 26); every other count unchanged",
             "reasons": "AO ball tracking 2022_MS146: Monteiro served the first game; of 51 games (no tiebreak) Monteiro served "
                        "26 and Paire 25. Its serve points (156/158), double faults (13/3), aces (30/13) and break points faced "
                        "(12/14) per server equal Stage 0's unexchanged, so only the service games are swapped. SofaScore "
                        "10065714 equals Stage 0 on 16 of 18 counts, all but sv_gms, which it has 25/26. With 4 breaks each, "
                        "the score forces Paire's service games to equal his 25 games won; after the fix the games identity "
                        "holds for both players. B5 is unaffected (sum 51). The whole-box exchange of F2 would be wrong here."},
        ],
        "F4x": [
            {"match_id": "wta|2012-W-SL-AUS-1A-2012|R128|wta:201419|wta:201584", "vote": "confirm",
             "fix": "blank the box (all nine counts of both players missing, has_box False, box-derived columns missing)",
             "reasons": "Sackmann's AO 2012 R128 and Wimbledon 2012 R128 rows (both Li d. Pervak 6-3 6-1) carry the identical "
                        "16-count box, so at least one is a copy. The Match Charting Project charted the AO match "
                        "(20120116-W-Australian_Open-R128-Na_Li-Ksenia_Pervak): serve points Li 41 / Pervak 56 against the box's "
                        "50 / 46, double faults 0/5 against 1/8, break points faced 2/14 against 1/5. Far beyond charting noise; "
                        "the chart itself fits 6-3 6-1. The box is not the AO match's. Blanking AO is right whoever owns the "
                        "box. I did not verify A1's record for Wimbledon, and the Wimbledon row is not voted here."},
        ],
        "F1y": [
            {"match_id": "wta|2015-W-INT-AUT-1A-2015|R16|wta:201325|wta:201344", "vote": "confirm", "fix": SVPT,
             "reasons": "Bad Gastein R16 Stosur d. Koukalova 6-1 6-0. As recorded Koukalova's 9 double faults exceed her 6 "
                        "second-serve points (B6), impossible if serve points include double faults; with +df every check "
                        "B0-B9 passes. The games identity holds exactly (12-1), which does not involve svpt; points per game "
                        "6.2 after the fix; the box appears in no other raw row. The extreme double-fault rate is what selects "
                        "a row into B6: with the 2015 convention, rows with more double faults than second serves in play are "
                        "0.14% of the 30 events' raw rows against 0.11-0.17% in clean WTA data, so nothing beyond the known "
                        "fault is indicated."},
            {"match_id": "wta|2015-W-INT-AZE-1A-2015|R32|wta:201377|wta:206107", "vote": "confirm", "fix": SVPT,
             "reasons": "Baku R32 Yang d. Beygelzimer 6-3 0-0 RET. As recorded Yang's 6 double faults exceed her 2 "
                        "second-serve points (B6); with +df every check passes. Service games 5+4 = 9 match the 9 games played, "
                        "and the first set's identity holds (6-3); 6.1 points per game after the fix; no copy elsewhere. Same "
                        "base-rate argument as Bad Gastein."},
            {"match_id": "wta|2015-W-INT-BRA-2A-2015|R16|wta:203518|wta:206194", "vote": "confirm", "fix": SVPT,
             "reasons": "Florianopolis R16 Ce d. Kania 6-2 7-6(7). As recorded Ce's 8 double faults exceed her 6 second-serve "
                        "points (B6); with +df every check passes, and the identity holds exactly for both players (13-8, a "
                        "match with 14 breaks in 20 service games). Ce's 82.5% first serves in and 1 of 6 second serves won are "
                        "unusual for her, but clean rows that also have more double faults than second serves in play include "
                        "first-in rates of 80-87% (e.g. Errani, Eikeri, Bolkvadze), so this profile is what the selection "
                        "produces, not a sign of a second fault. No copy elsewhere; no independent record exists for 2015."},
        ],
    }
    (K.OUT / "round2.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for k in ("F1x", "F2x", "F2y", "F4x", "F1y"):
        v = pd.Series([i["vote"] for i in res[k]]).value_counts().to_dict()
        print(k, v)


if __name__ == "__main__":
    main()
