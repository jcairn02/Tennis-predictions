"""R1-rederive (group SVX): two checks of the truth that do not lean on MatchBeats' first server, and the exclusions.

1. The break identity. Every finished non-tiebreak game is a hold or a break, and a break is the converted break point
   that ends it, so for each player
       service games = regular games won + breaks conceded - breaks made,
   with regular games won read off the row's score (a 7-6 set's tiebreak is not a game) and breaks conceded = break
   points faced - saved, from the row's own box. This fixes the split from the score and the row's break points alone.
   (Exact for completed matches; a retirement's unfinished game is in neither count.)
2. The labels: in each file, the share of finished service games won by the player MatchBeats has serving (servers
   hold most games; a file whose labels named the receiver would hold under half).
3. Exclusions: rows another table of the candidate already changes (the decided row corrections of 8 Oct, round 1's
   split rows, the four RGX exchanges, and my confirmed overrides of RG 2022-2026, which take MatchBeats' service
   games: exchanging after them would undo them).

Writes svx_checked.csv and prints the tallies. Run after svx_truth.py:
  ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/svx_checks.py
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive"
WORK = HERE / "work"


def reg_won(score: str) -> tuple[int, int]:
    w = l = 0
    for tok in str(score or "").split():
        m = re.match(r"^(\d+)-(\d+)", tok)
        if not m:
            continue
        a, b = int(m.group(1)), int(m.group(2))
        if max(a, b) == 7 and min(a, b) == 6:     # the set winner's seventh game is the tiebreak
            a, b = (a - 1, b) if a > b else (a, b - 1)
        w, l = w + a, l + b
    return w, l


def main() -> None:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 60)
    pd.set_option("display.max_rows", 200)
    x = pd.read_csv(HERE / "svx_rows.csv", low_memory=False)
    games = pd.read_parquet(WORK / "svx_games.parquet")
    # 1. break identity
    rw = np.array([reg_won(s) for s in x["score"].fillna("")])
    x["reg_w"], x["reg_l"] = rw[:, 0], rw[:, 1]
    brk_w = x["w_bpFaced"] - x["w_bpSaved"]
    brk_l = x["l_bpFaced"] - x["l_bpSaved"]
    x["bp_sv_w"] = x["reg_w"] + brk_w - brk_l
    x["bp_sv_l"] = x["reg_l"] + brk_l - brk_w
    x["bp_eq_truth"] = x["bp_sv_w"].eq(x["t_w"]) & x["bp_sv_l"].eq(x["t_l"])
    x["bp_eq_row"] = x["bp_sv_w"].eq(x["w_SvGms"]) & x["bp_sv_l"].eq(x["l_SvGms"])
    # 2. the labels: hold rate by file
    g = games[~games["tb"] & games["complete"] & games["server"].notna()]
    hold = g.assign(held=g["winner"].eq(g["server"])).groupby(["slam", "year", "code"])["held"].agg(["mean", "size"])
    hold.columns = ["mb_hold_rate", "mb_games"]
    x = x.merge(hold.reset_index(), on=["slam", "year", "code"], how="left")
    # 3. exclusions
    rc = pd.read_csv(ROOT / "data" / "studies" / "input_data_audit" / "fixes" / "row_corrections.csv", dtype=str,
                     keep_default_na=False)
    r1 = pd.read_csv(ROOT / "data" / "studies" / "rg_first_serve_recount" / "confirmed" / "confirmed_corrections.csv",
                     dtype=str, keep_default_na=False)
    rgx = pd.read_csv(HERE / "exchanges_scope.csv", dtype=str, keep_default_na=False)
    ovs = pd.read_csv(HERE / "overrides_scope.csv", dtype=str, keep_default_na=False)
    key = x["source_file"].astype(str) + "#" + x["source_row"].astype("Int64").astype(str)
    x["in_decided_corrections"] = key.isin(set(rc["source_file"] + "#" + rc["source_row"]))
    x["in_round1_split"] = key.isin(set(r1["source_file"] + "#" + r1["source_row"]))
    x["in_rgx"] = key.isin(set(rgx["source_file"] + "#" + rgx["source_row"]))
    x["in_my_overrides"] = x["s0_match_id"].isin(set(ovs["stage0_match_id"])) & x["slam"].eq("RG")
    x["excluded"] = x[["in_decided_corrections", "in_round1_split", "in_rgx", "in_my_overrides"]].any(axis=1)
    x.to_csv(HERE / "svx_checked.csv", index=False)

    sw = x[x["cls"].eq("swapped")]
    pr = x[x["proof"].eq("proven") & x["w_bpFaced"].notna() & x["status_ok"]] if "status_ok" in x else \
        x[x["proof"].eq("proven") & x["w_bpFaced"].notna()]
    comp = ~pr["score"].fillna("").str.contains("RET|DEF|W/O", regex=True)
    print("break identity on proven completed rows: equals the truth on",
          int(pr.loc[comp, "bp_eq_truth"].sum()), "of", int(comp.sum()))
    sc = ~sw["score"].fillna("").str.contains("RET|DEF|W/O", regex=True)
    print("swapped rows (completed): break identity equals the truth on", int(sw.loc[sc, "bp_eq_truth"].sum()),
          "of", int(sc.sum()), "| equals the row as recorded on", int(sw.loc[sc, "bp_eq_row"].sum()))
    print("swapped retirements: break identity equals the truth on", int(sw.loc[~sc, "bp_eq_truth"].sum()), "of",
          int((~sc).sum()))
    print(sw.loc[sc & ~sw["bp_eq_truth"], ["slam", "year", "code", "score", "w_SvGms", "l_SvGms", "t_w", "t_l",
                                           "bp_sv_w", "bp_sv_l", "w_bpFaced", "w_bpSaved", "l_bpFaced",
                                           "l_bpSaved"]].to_string())
    print("\nMatchBeats hold rate by file: proven files min", round(x.loc[x["proof"].eq("proven"), "mb_hold_rate"].min(), 3),
          "| swapped files min", round(sw["mb_hold_rate"].min(), 3), "median", round(sw["mb_hold_rate"].median(), 3),
          "| files below 0.5:", int((x["mb_hold_rate"] < 0.5).sum()))
    print(x[x["mb_hold_rate"] < 0.5][["slam", "year", "code", "mb_hold_rate", "mb_games", "cls", "proof"]].to_string())
    print("\nswapped rows excluded:", sw[sw["excluded"]][["slam", "year", "code", "in_decided_corrections",
                                                           "in_round1_split", "in_rgx", "in_my_overrides"]].to_string())


if __name__ == "__main__":
    main()
