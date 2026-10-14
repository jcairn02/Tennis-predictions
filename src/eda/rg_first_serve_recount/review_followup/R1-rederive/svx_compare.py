"""R1-rederive (group SVX): my classes, truths and swaps against the lead's tables, read only now.

Lead: data/studies/rg_first_serve_recount/followup/service_games/matches.csv (one row per player row) and
proposed_swaps.csv. Mine: svx_checked.csv (svx_truth.py, svx_checks.py).
Writes svx_compare.json and svx_compare_rows.csv (every match where the class, the truth or the first server differs).
Run: ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/svx_compare.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "service_games"


def main() -> None:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 60)
    pd.set_option("display.max_rows", 200)
    mine = pd.read_csv(HERE / "svx_checked.csv", low_memory=False)
    mine = mine[mine["proof"].ne("no_file")].copy()
    mine["key"] = mine["source_file"] + "#" + mine["source_row"].astype("Int64").astype(str)
    lm = pd.read_csv(LEAD / "matches.csv", low_memory=False)
    lm["key"] = lm["source_file"] + "#" + lm["source_row"].astype("Int64").astype(str)
    w = lm[lm["raw_side"].eq("w")].set_index("key")
    l = lm[lm["raw_side"].eq("l")].set_index("key")
    lead = pd.DataFrame({"lead_cls": w["cls"], "lead_t_w": w["true_sv_gms"], "lead_t_l": l["true_sv_gms"].reindex(w.index),
                         "lead_w_served_first": w["served_first"], "lead_alternation_ok": w["alternation_ok"],
                         "lead_match_id": w["match_id"], "lead_code": w["code"], "lead_override": w["rg_override"],
                         "lead_decided": w["decided_correction"]}).reset_index()
    j = mine.merge(lead, on="key", how="outer", indicator=True)
    res = {"mine_rows_with_file": int(len(mine)), "lead_matches": int(len(lead)),
           "joined": int((j["_merge"] == "both").sum()), "mine_only": int((j["_merge"] == "left_only").sum()),
           "lead_only": int((j["_merge"] == "right_only").sum())}
    b = j[j["_merge"] == "both"].copy()
    cmap = {"no_count": "incomplete"}
    b["cls_m"] = b["cls"].replace(cmap)
    res["class_equal"] = int((b["cls_m"] == b["lead_cls"]).sum())
    res["class_crosstab_where_different"] = {f"{a}|{c}": int(n) for (a, c), n in
                                             b[b["cls_m"] != b["lead_cls"]].groupby(["cls_m", "lead_cls"]).size().items()}
    pr = b[b["proof"].eq("proven") & b["lead_t_w"].notna()]
    res["truth_compared"] = int(len(pr))
    res["truth_equal"] = int((pr["t_w"].eq(pr["lead_t_w"]) & pr["t_l"].eq(pr["lead_t_l"])).sum())
    fs_mine = pr["first_server"].astype(str).eq(pr["mb_w_team"].astype(str))
    res["first_server_equal"] = int((fs_mine == pr["lead_w_served_first"].astype(bool)).sum())
    diff = b[(b["cls_m"] != b["lead_cls"]) | (b["proof"].eq("proven") & b["lead_t_w"].notna() &
                                              ~(b["t_w"].eq(b["lead_t_w"]) & b["t_l"].eq(b["lead_t_l"])))]
    cols = ["slam", "year", "code", "score", "w_SvGms", "l_SvGms", "t_w", "t_l", "lead_t_w", "lead_t_l", "cls",
            "lead_cls", "proof", "p1_order", "p2_opens", "p3_alternation", "p4_sets", "games_checked", "games_off",
            "first_set", "first_game", "first_gs1", "first_gs2", "bp_sv_w", "bp_sv_l", "lead_alternation_ok", "key"]
    diff[cols].to_csv(HERE / "svx_compare_rows.csv", index=False)
    print(json.dumps(res, indent=1))
    print(diff[cols].to_string())
    if res["lead_only"]:
        print(j[j["_merge"] == "right_only"][["key", "lead_code", "lead_cls", "lead_match_id"]].to_string())
    if res["mine_only"]:
        print(j[j["_merge"] == "left_only"][["key", "slam", "year", "code", "cls", "proof"]].to_string())
    # the swap lists
    ps = pd.read_csv(LEAD / "proposed_swaps.csv", dtype=str, keep_default_na=False)
    ps["key"] = ps["source_file"] + "#" + ps["source_row"]
    ms = mine[mine["cls"].eq("swapped") & ~mine["excluded"].astype(bool)]
    lk, mk = set(ps["key"]), set(ms["key"])
    res["swaps"] = {"lead": len(lk), "mine": len(mk), "both": len(lk & mk), "lead_only": sorted(lk - mk),
                    "mine_only": sorted(mk - lk)}
    sm = ms.set_index("key")["s0_match_id"]
    res["swaps"]["match_ids_equal"] = int(sum(sm.get(k) == m for k, m in zip(ps["key"], ps["match_id"]) if k in mk))
    print(json.dumps(res["swaps"], indent=1))
    (HERE / "svx_compare.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
