"""R3-referee (follow-up), step 8: my scope, from my own values.

overrides_scope.csv: one row per match I confirm (W22: RG 2022-2025; W26: RG 2026), with feed_key, stage0_match_id and
the eighteen values I derived from RG's raw documents and MatchBeats (official.py), for the raw row's winner (w) and
loser (l). The matches are those whose override key my own link places on the same RG document as the lead's
(values_check.py: 1,509 of 1,509, every value equal), minus any match a test below removes:
    - a value of mine that differs from the lead's (none),
    - the official box failing Stage 0's checks in the simulation (none),
    - a valid referee (Court Vision 2022 on every count, Court Vision 2023-2024 on serve points, aces, break points and
      service games, a hand chart) reading the row's value instead of RG's on a count that changes (none among the
      proposed matches).
exchanges_scope.csv: the RGX exchanges I confirm (rgx.py: all four).
Also writes scope_notes.csv: per confirmed match, the group, the pattern (bar_analysis.py), the service games' source
and whether MatchBeats' service games differ from the row's by the retirement convention.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/make_scope.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3f as F  # noqa: E402


def main() -> int:
    vc = pd.read_csv(F.OUT / "values_check.csv", low_memory=False)
    o = pd.read_csv(F.OUT / "official_rows.csv", low_memory=False)
    sim = pd.read_csv(F.OUT / "sim_rows.csv", index_col=0)
    det = pd.read_csv(F.OUT / "ref_votes_detail.csv", low_memory=False)
    bar = pd.read_csv(F.OUT / "bar_rows.csv", low_memory=False)
    ov = pd.read_csv(F.FOLLOW / "proposed_overrides.csv", dtype=str, keep_default_na=False)
    o["ovkey"] = o["source"] + "|" + o["tour"] + "|" + o["tid"] + "|" + o["round"] + "|" + o["wkey"] + "|" + o["lkey"]
    ov["ovkey"] = ov["source"] + "|" + ov["tour"] + "|" + ov["tid"] + "|" + ov["round"] + "|" + ov["winner_key"] + "|" \
        + ov["loser_key"]
    j = ov[["feed_key", "stage0_match_id", "ovkey"]].merge(o, on="ovkey", how="left")
    # the tests
    same = vc.set_index("feed_key")["differences"].fillna("").eq("")
    j["values_equal_lead"] = j["feed_key"].map(same).fillna(False)
    st = sim.set_index("stage0_match_id")["cand_box_status"]
    j["box_status_after"] = j["stage0_match_id"].map(st)
    j["passes_checks"] = j["box_status_after"].isin(["full", "no_svgms"])
    dv = det[det["valid_referee"] & det["lead_cls"].eq("proposed") & det["vote"].eq("row")]
    against = set(dv["source_file"] + "#" + dv["source_row"].astype(str))
    j["referee_against"] = (j["source_file"] + "#" + j["source_row"].astype(str)).isin(against)
    keep = j["values_equal_lead"] & j["passes_checks"] & ~j["referee_against"]
    s = j[keep].copy()
    rows = []
    for r in s.to_dict("records"):
        rec = {"feed_key": r["feed_key"], "stage0_match_id": r["stage0_match_id"]}
        for side in ("w", "l"):
            for c, col in F.NINE.items():
                v = r[f"my_{side}_{c}"]
                rec[f"{side}_{col}"] = "" if pd.isna(v) else str(int(v))
        rows.append(rec)
    scope = pd.DataFrame(rows, columns=F.SCOPE_COLS)
    scope.to_csv(F.OUT / "overrides_scope.csv", index=False)
    ex = pd.read_csv(F.FOLLOW / "proposed_exchanges.csv", dtype=str, keep_default_na=False)
    rg = pd.read_csv(F.OUT / "rgx_check.csv")
    ok = rg[rg["score_sets_equal"] & rg["rg_winner_flag_is_row_winner"] & rg["mb_winner_is_row_winner"]
            & rg["row_winner_plays_next_round"] & ~rg["row_loser_plays_next_round"]
            & rg["counts_differing_once_exchanged"].isna()]
    exs = ex.merge(ok[["source_file", "source_row"]].astype(str), on=["source_file", "source_row"])
    exs[["source_file", "source_row", "match_id"]].to_csv(F.OUT / "exchanges_scope.csv", index=False)
    # notes per confirmed match
    b = bar.drop_duplicates(["source_file", "source_row"]).set_index(
        bar.drop_duplicates(["source_file", "source_row"])["source_file"] + "#"
        + bar.drop_duplicates(["source_file", "source_row"])["source_row"].astype(str))["pattern"]
    s["key"] = s["source_file"] + "#" + s["source_row"].astype(str)
    s["group"] = np.where(s["season"].eq(2026), "W26", "W22")
    s["pattern"] = s["key"].map(b)
    s["retirement_convention"] = (s["my_sv_from"].eq("matchbeats") & s["status_parsed"].eq("retired")
                                  & ((s["my_w_sv_gms"] + s["my_l_sv_gms"]) - (s["games"] - s["std_tb"])).eq(1))
    s["sv_gms_differs_from_row"] = s["raw_w_sv_gms"].notna() & (s["my_w_sv_gms"].ne(s["raw_w_sv_gms"])
                                                                 | s["my_l_sv_gms"].ne(s["raw_l_sv_gms"]))
    s[["feed_key", "stage0_match_id", "group", "season", "tour", "draw", "round", "winner_name", "loser_name", "score",
       "source", "pattern", "my_sv_from", "retirement_convention", "sv_gms_differs_from_row", "box_status_after"]] \
        .to_csv(F.OUT / "scope_notes.csv", index=False)
    smry = {"lead_overrides": int(len(ov)), "found": int(j["code"].notna().sum()),
            "values_equal_lead": int(j["values_equal_lead"].sum()), "passes_checks": int(j["passes_checks"].sum()),
            "box_status_after": j["box_status_after"].value_counts().to_dict(),
            "referee_against": int(j["referee_against"].sum()), "confirmed": int(len(scope)),
            "confirmed_by_group": s["group"].value_counts().to_dict(),
            "confirmed_by_group_source_draw": s.groupby(["group", "source", "tour", "draw"]).size().rename("matches")
            .reset_index().to_dict("records"),
            "by_pattern": s.groupby(["group", "pattern"]).size().rename("matches").reset_index().to_dict("records"),
            "sv_gms_from": s.groupby(["group", "my_sv_from"]).size().rename("matches").reset_index().to_dict("records"),
            "retirement_convention_matches": s.groupby("group")["retirement_convention"].sum().astype(int).to_dict(),
            "retirement_convention_list": s.loc[s["retirement_convention"], ["feed_key", "winner_name", "loser_name",
                                                                              "score"]].to_dict("records"),
            "exchanges_confirmed": int(len(exs))}
    (F.OUT / "scope_summary.json").write_text(json.dumps(smry, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(smry, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
