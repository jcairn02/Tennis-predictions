"""R2-skeptic (round 2): does the service-game convention hold? A strict check from the score.

In tennis the serve alternates game by game through the whole match, a tie-break counting as one game in the
alternation (the player who received first in a tie-break serves first in the next set). So once the first server is
known, each player's service games follow from the set scores exactly:
    excl   non-tie-break games served (the convention the proposal takes: "tiebreaks not counted")
    incl   the same with each tie-break counted for the player whose turn it is in the alternation
The first server comes from MatchBeats' first point; the set scores from RG's own match document (team sets, with
tie-break points).

For every Stage 0 player row of RG 2019-2026 with a MatchBeats file, this compares:
    MatchBeats' own count of non-tie-break games served (mb_sv_gms_regular)  with excl
    the raw row's SvGms (Sackmann's or TML's)                                 with excl and incl
    the lead's off_sv_gms (whole_box_rows.csv)                                with excl
Retirements: the score shows completed games only, so a game in progress at the retirement is not in excl/incl; such
rows are reported apart.

Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/:
    svgms_rows.csv      one row per player row: scores, first server, excl/incl, MatchBeats', the row's, the lead's
    svgms_summary.json  agreement by period, source and status; the lead's fallback rows; the 2019-2021 claim
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/service_games.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"


def expected(my_games: list, opp_games: list, my_tb: list, opp_tb: list, i_serve_first: bool) -> dict:
    """Service games of 'me' from the set scores, given whether I served the match's first point."""
    turn_me = i_serve_first
    excl = incl = opp_excl = opp_incl = 0
    tbs = 0
    for a, b, ta, tb in zip(my_games, opp_games, my_tb, opp_tb):
        if a is None or b is None:
            continue
        n = a + b
        is_tb_set = (max(a, b) == 7 and min(a, b) == 6) or (ta is not None or tb is not None)
        for gi in range(n):
            tb_game = is_tb_set and gi == n - 1 and max(a, b) == 7 and min(a, b) == 6
            if tb_game:
                tbs += 1
                if turn_me:
                    incl += 1
                else:
                    opp_incl += 1
            else:
                if turn_me:
                    excl += 1
                    incl += 1
                else:
                    opp_excl += 1
                    opp_incl += 1
            turn_me = not turn_me
    return {"exp_excl": excl, "exp_incl": incl, "exp_opp_excl": opp_excl, "exp_opp_incl": opp_incl, "exp_tb": tbs}


def main() -> int:
    s = pd.read_parquet(OUT / "players.parquet")
    s = s[s["code"].notna() & s["mb_slot"].notna()].copy()
    recs = []
    for x in s.itertuples(index=False):
        g, og = json.loads(x.rg_set_games), json.loads(x.rg_opp_set_games)
        t, ot = json.loads(x.rg_set_tb), json.loads(x.rg_opp_set_tb)
        first = str(x.mb_first_server) == str(int(x.mb_slot))
        e = expected(g, og, t, ot, first)
        recs.append({"match_id": x.match_id, "side": x.side, **e})
    e = pd.DataFrame(recs)
    s = s.merge(e, on=["match_id", "side"], how="left")
    lead = pd.read_csv(LEAD / "whole_box_rows.csv", low_memory=False)
    lead["side"] = lead["raw_side"]
    s = s.merge(lead[["match_id", "side", "off_sv_gms", "sv_gms_from", "cls"]], on=["match_id", "side"], how="left")
    s["period"] = np.select([s["year"].le(2021), s["year"].le(2025)], ["2019-2021", "2022-2025"], "2026")
    s["retired"] = s["status"].eq("retired")
    s["mb_eq_excl"] = s["mb_sv_gms_regular"].eq(s["exp_excl"])
    s["raw_eq_excl"] = s["raw_SvGms"].eq(s["exp_excl"])
    s["raw_eq_incl"] = s["raw_SvGms"].eq(s["exp_incl"])
    s["raw_eq_mb"] = s["raw_SvGms"].eq(s["mb_sv_gms_regular"])
    s["lead_eq_excl"] = s["off_sv_gms"].eq(s["exp_excl"])
    keep = ["match_id", "year", "tour", "draw", "round", "side", "player", "source", "status", "code", "rg_set_games",
            "rg_opp_set_games", "rg_set_tb", "mb_first_server", "mb_slot", "mb_complete_match", "mb_svpt", "my_svpt",
            "exp_excl", "exp_incl", "exp_tb", "mb_sv_gms_regular", "mb_sv_gms_any", "mb_tb_games", "mb_mixed_nontb_games",
            "raw_SvGms", "off_sv_gms", "sv_gms_from", "cls", "mb_eq_excl", "raw_eq_excl", "raw_eq_incl", "raw_eq_mb",
            "lead_eq_excl", "mb_awarded_pts", "mb_penalty_pts", "mb_nopoint_pts"]
    s[keep].to_csv(OUT / "svgms_rows.csv", index=False)

    def rate(d, col):
        d = d[d[col].notna()] if col in d else d
        return {"rows": int(len(d)), "share": round(float(d[col].mean()), 4) if len(d) else None}

    summ = {}
    full = s["mb_complete_match"]
    for per, g in s.groupby("period"):
        gc = g[g["mb_complete_match"]]
        comp = gc[~gc["retired"]]
        tb = comp[comp["exp_tb"] > 0]
        has_raw = comp[comp["raw_SvGms"].notna() & comp["raw_SvGms"].gt(0)]
        has_raw_tb = has_raw[has_raw["exp_tb"] > 0]
        summ[per] = {
            "player_rows_mb_complete": int(len(gc)),
            "completed_rows": int(len(comp)),
            "mb_regular_equals_score_excl (completed)": int(comp["mb_eq_excl"].sum()),
            "rows_with_raw_svgms (completed)": int(len(has_raw)),
            "raw_equals_mb_regular": int(has_raw["raw_eq_mb"].sum()),
            "raw_equals_score_excl": int(has_raw["raw_eq_excl"].sum()),
            "raw_equals_score_incl": int(has_raw["raw_eq_incl"].sum()),
            "raw_equals_neither": int((~has_raw["raw_eq_excl"] & ~has_raw["raw_eq_incl"]).sum()),
            "rows_in_tiebreak_matches_with_raw": int(len(has_raw_tb)),
            "tb_matches: raw_equals_excl_only": int((has_raw_tb["raw_eq_excl"] & ~has_raw_tb["raw_eq_incl"]).sum()),
            "tb_matches: raw_equals_incl_only": int((has_raw_tb["raw_eq_incl"] & ~has_raw_tb["raw_eq_excl"]).sum()),
            "tb_matches: raw_equals_neither": int((~has_raw_tb["raw_eq_incl"] & ~has_raw_tb["raw_eq_excl"]).sum()),
            "no_tb_matches: raw_equals_excl": int(has_raw[has_raw["exp_tb"].eq(0)]["raw_eq_excl"].sum()),
            "no_tb_matches: rows": int(has_raw["exp_tb"].eq(0).sum()),
            "retired_rows_mb_complete": int(gc["retired"].sum()),
            "retired: mb_regular - excl": gc[gc["retired"]].eval("mb_sv_gms_regular - exp_excl").value_counts().to_dict(),
            "retired: raw - excl": gc[gc["retired"] & gc["raw_SvGms"].notna()].eval("raw_SvGms - exp_excl")
            .value_counts().to_dict(),
        }
    # the lead's sources of off_sv_gms in the proposed rows, against the score
    p = s[s["cls"].eq("proposed")]
    summ["proposed_rows"] = {
        "by_source": p["sv_gms_from"].value_counts().to_dict(),
        "matchbeats_rows_equal_score_excl (completed)": int(p[p["sv_gms_from"].eq("matchbeats") & ~p["retired"]]
                                                              ["lead_eq_excl"].sum()),
        "matchbeats_rows_completed": int((p["sv_gms_from"].eq("matchbeats") & ~p["retired"]).sum()),
        "matchbeats_rows_not_equal_excl": p[p["sv_gms_from"].eq("matchbeats") & ~p["lead_eq_excl"]][
            ["match_id", "side", "status", "exp_excl", "mb_sv_gms_regular", "off_sv_gms", "raw_SvGms"]]
        .to_dict("records"),
        "row_fallback_rows": p[p["sv_gms_from"].eq("row")][
            ["match_id", "side", "status", "source", "exp_excl", "exp_incl", "mb_sv_gms_regular", "raw_SvGms",
             "off_sv_gms", "mb_svpt", "my_svpt"]].to_dict("records"),
        "none_rows": p[p["sv_gms_from"].eq("none")][
            ["match_id", "side", "status", "exp_excl", "mb_sv_gms_regular", "raw_SvGms", "mb_svpt", "my_svpt"]]
        .to_dict("records"),
    }
    # where MatchBeats changes the raw row's count (2022-2025, rows with a raw count)
    ch = p[p["sv_gms_from"].eq("matchbeats") & p["raw_SvGms"].notna() & p["raw_SvGms"].gt(0)
           & ~p["raw_SvGms"].eq(p["off_sv_gms"])]
    summ["mb_changes_raw_count"] = {
        "rows": int(len(ch)), "by_period": ch["period"].value_counts().to_dict(),
        "new_equals_score_excl": int(ch["lead_eq_excl"].sum()),
        "raw_equals_score_excl": int(ch["raw_eq_excl"].sum()), "raw_equals_score_incl": int(ch["raw_eq_incl"].sum()),
        "retired": int(ch["retired"].sum()),
        "rows": ch[["match_id", "side", "status", "rg_set_games", "rg_opp_set_games", "exp_excl", "exp_incl",
                    "raw_SvGms", "off_sv_gms"]].to_dict("records")}
    (OUT / "svgms_summary.json").write_text(json.dumps(summ, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summ.items() if k not in ("proposed_rows", "mb_changes_raw_count")}, indent=1,
                     default=str))
    pr = summ["proposed_rows"]
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in pr.items()}, indent=1))
    mc = summ["mb_changes_raw_count"]
    print(json.dumps({k: v for k, v in mc.items() if k != "rows"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
