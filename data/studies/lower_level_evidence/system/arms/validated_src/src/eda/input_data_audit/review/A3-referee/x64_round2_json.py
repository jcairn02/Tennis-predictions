"""Round 2 (A3-referee): write round2.json from round2_evidence.csv and the checks of x61-x63."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc  # noqa: E402

E = pd.read_csv(rc.OUT / "round2_evidence.csv")
cand = pd.read_csv(rc.ROOT / "data/studies/input_data_audit/fixes/round2_A_candidates.csv")
E = E.merge(cand[["match_id", "proposed_fix", "source_file", "source_row"]], on="match_id", how="left")
SISTERS = {"Pliskova", "Wang", "Andreeva", "Kudermetova", "Perez", "Jorge"}
SCORE_NOTE = {
    "wta|2021-2028|Q2|wta:213620|wta:214388": "Sackmann's score 4-6 6-4 7-5 differs from the API's 4-6 7-5 7-5; with the API's score the exchanged box fits the games identity for both players (the score, a separate fault, is not changed by this fix)",
    "wta|2021-2027|Q1|wta:215337|wta:215872": "Sackmann's score 7-6(7) 6-4 differs from the API's 7-6(7) 6-2; with the API's score the exchanged box fits the identity for both players (separate score fault, not changed here)",
    "wta|2021-2027|R16|wta:206255|wta:213525": "Sackmann's score 6-3 3-3 RET differs from the API's 6-3 4-3 RET; with the API's score the exchanged box fits the identity for both players (separate score fault, not changed here)",
    "wta|2021-2028|R64|wta:206107|wta:213550": "Sackmann's score 7-6(4) 6-2 differs from the API's 7-6(4) 6-3; the exchanged box equals the API's own box, which itself misses the identity under the API's score (as at Palermo 2022)",
    "wta|2021-2028|R32|wta:201465|wta:213550": "retirement (API: 5-7 5-4 Ret'd), so the games identity is not testable",
}
out = {"F1x": [], "F1y": [], "F2x": [], "F2y": [], "F4x": []}
for _, r in E.iterrows():
    mid, c = r["match_id"], r["cand"]
    raw = f"raw row {r['source_file'].split('/')[-1]} _row {int(r['source_row'])}"
    if c == "F1x":
        item = {"match_id": mid, "vote": "confirm",
                "fix": f"svpt := svpt + df for both players ({raw}: w_svpt {r['w_svpt']:g} -> {r['w_svpt'] + r['w_df']:g}, "
                       f"l_svpt {r['l_svpt']:g} -> {r['l_svpt'] + r['l_df']:g}); nothing else",
                "reasons": (f"MCP charts this match: {r['raw_winner']}: {r['mcp_w']}; {r['raw_loser']}: {r['mcp_l']}. Both rows "
                            "equal MCP's serve points only as svpt + df while every other count agrees, so this match is "
                            "recorded without double faults although Doha's R32 and R16 are not (MCP). After the fix: B0-B9 "
                            "pass (replica and stage0_build.box_scores), games identity exact for both players, definition "
                            "test passes.")}
    elif c == "F1y":
        item = {"match_id": mid, "vote": "confirm",
                "fix": f"svpt := svpt + df for both players ({raw}: w_svpt {r['w_svpt']:g} -> {r['w_svpt'] + r['w_df']:g}, "
                       f"l_svpt {r['l_svpt']:g} -> {r['l_svpt'] + r['l_df']:g}); nothing else",
                "reasons": (f"{r['event']} 2015 is one of the 30 events confirmed in F1 (MCP and the same-player test). Stage 0 "
                            "drops this box only for B6, double faults exceeding svpt - first_in, which cannot happen when "
                            "serve points include double faults: the row itself shows the fault. After the fix every check "
                            "passes (B0-B9 in the replica and stage0_build.box_scores, games identity on both players, "
                            f"definition test); points won {r['after_pts_rawwinner']:g}-{r['after_pts_rawloser']:g} for the "
                            "recorded winner. No MCP chart of this match.")}
    elif c == "F2x":
        sister = any(s in str(r["raw_winner"]) for s in SISTERS) and any(s in str(r["raw_loser"]) for s in SISTERS) \
            and str(r["raw_winner"]).split()[-1] == str(r["raw_loser"]).split()[-1]
        if sister:
            item = {"match_id": mid, "vote": "reject", "fix": "none (the box is as recorded)",
                    "reasons": (f"{r['raw_winner']} v {r['raw_loser']}: the two players share a surname. Joined by full first "
                                "and last name (and checked against the API's player ids and seeds), the WTA API's statistics "
                                "for each named player equal Sackmann's box AS RECORDED on all 18 counts "
                                f"({r['api_result'] if isinstance(r['api_result'], str) else 'API LS012 Auckland 2024, Xinyu Wang = Sackmann Xin Yu Wang'}), "
                                "so an exchange would put each sister's statistics on the other. The 'exchange' match comes "
                                "from joining by surname or initial.")}
        else:
            note = SCORE_NOTE.get(mid, "")
            item = {"match_id": mid, "vote": "confirm",
                    "fix": f"exchange all nine counts between the two players (w_* <-> l_* on {raw})",
                    "reasons": (f"WTA API {r['api_match']}: its statistics for each player equal Sackmann's box only once "
                                f"exchanged ({int(r['api_eq_exchanged'])}/18 exchanged, {int(r['api_eq_as_recorded'])}/18 as "
                                f"recorded); its result '{r['api_result']}' names the recorded winner. The precondition from "
                                "F3b holds (API = Sackmann on 99.69% of clean 2021-22 rows, all nine counts). After the "
                                f"exchange B0-B9 pass (replica and stage0_build.box_scores)"
                                + (", games identity exact for both players" if r["after_identity_both"] else "")
                                + (f"; {note}" if note else "") + ".")}
    elif c == "F2y":
        item = {"match_id": mid, "vote": "confirm",
                "fix": f"exchange the two players' sv_gms only ({raw}: w_SvGms {r['w_svgms']:g} -> {r['l_svgms']:g}, "
                       f"l_SvGms {r['l_svgms']:g} -> {r['w_svgms']:g}); every other count unchanged",
                "reasons": ("AO 2022 ball tracking (2022_MS146, the AO's own point records): Monteiro serves first and serves "
                            "26 games, Paire 25 (no tiebreak, 51 games); every other count equals Sackmann's as recorded "
                            "(Paire 156 serve points, 30 aces, 13 double faults, 82 first in, 70 / 35 won; Monteiro 158, 13, "
                            "3, 109, 77 / 26). Sofascore (a different source at the AO) gives the same: Paire 25, Monteiro "
                            "26, the rest as recorded. Sackmann has 26 and 25. After the exchange the games identity is "
                            "exact for both players (25 = 25 - 4 + 4, 26 = 26 - 4 + 4) and B0-B9 pass.")}
    elif c == "F4x":
        item = {"match_id": mid, "vote": "confirm",
                "fix": f"blank the box (all nine counts of both players) on {raw}",
                "reasons": ("Sackmann's AO 2012 R128 and Wimbledon 2012 R128 rows of Li d. Pervak have the same score (6-3 6-1, "
                            "which is why the audit's copy scan took them for one match listed twice) and the same box: Li "
                            "50 serve points, 3 aces, 1 double fault, break points 0/1; Pervak 46, 0, 8, 0/5. Sackmann's Slam "
                            "point-by-point gives exactly that box for Wimbledon 2012 (Li 50, 3, 1, 0/1; Pervak 46, 0, 8, 0/5) "
                            "and a different one for the AO 2012 match (Li 41, 0, 0, 0/2; Pervak 56, 0, 5, 8/14), which MCP's "
                            "independent chart of the AO match confirms (Li 41, 0, 0, 0/2; Pervak 56, 0, 5, 8/14). So the AO "
                            "2012 row carries Wimbledon's box; Stage 0 keeps it today (service games blank).")}
    out[c].append(item)
(rc.OUT / "round2.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
for k, v in out.items():
    print(k, {x: sum(i["vote"] == x for i in v) for x in ("confirm", "reject")})
print([i["match_id"] for i in out["F2x"] if i["vote"] == "reject"])
