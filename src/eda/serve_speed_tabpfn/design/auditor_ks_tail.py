"""Design R2 (auditor): what is the heavy tail of the men's 2023 key-statistic matches? Values and source counts only
(no match result, no box score, no statistic target, no price).

For matches where ManTennisData's key statistic AND a held Infosys point table exist for both sides (2021-2024):
    same  = |KS_A - PM_A| + |KS_B - PM_B|        swap = |KS_A - PM_B| + |KS_B - PM_A|
    a side swap is flagged when swap < same - 6 km/h; the first-serves-in counts are compared the same way
    (ManTennisData's ks_first_in against the point table's count of first serves in, f1).
Also, without points: matches whose two key statistics are identical, or whose first-serve counts equal the other
side's, and the flagged share by year 2021-2026 (a count-only check usable in every season).

Run: ./python.sh src/eda/serve_speed_tabpfn/design/auditor_ks_tail.py
Writes data/studies/serve_speed_tabpfn/design/auditor_ks_tail.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.design import engineer_common as EC  # noqa: E402

OUT = EC.OUT / "auditor_ks_tail.json"


def wide(r: pd.DataFrame, src: str, cols: list[str]) -> pd.DataFrame:
    x = r[r["source"].eq(src) & r["linked"]].drop_duplicates(["match_id", "side"], keep=False)
    a = x[x["side"].eq("A")].set_index("match_id")[cols].add_suffix("_A")
    b = x[x["side"].eq("B")].set_index("match_id")[cols].add_suffix("_B")
    return a.join(b, how="inner")


def main() -> None:
    r = pd.read_parquet(EC.RECORDS)
    yrs = EC.stage0(cols=["match_id", "year", "level", "tournament_id", "tournament_name"]).set_index("match_id")
    ks = wide(r, "mantennisdata", ["spd1", "ks_first_in", "ks_first_total"])
    pm = wide(r, "infosys", ["spd1", "f1", "n1"])
    j = ks.join(pm, lsuffix="", rsuffix="_pm", how="inner").join(yrs, how="left")
    j = j[(j["n1_A"] >= 10) & (j["n1_B"] >= 10)]
    same = (j["spd1_A"] - j["spd1_A_pm"]).abs() + (j["spd1_B"] - j["spd1_B_pm"]).abs()
    swap = (j["spd1_A"] - j["spd1_B_pm"]).abs() + (j["spd1_B"] - j["spd1_A_pm"]).abs()
    j["swap_speed"] = swap < same - 6
    cs = (j["ks_first_in_A"] == j["f1_A"]) & (j["ks_first_in_B"] == j["f1_B"])
    cw = (j["ks_first_in_A"] == j["f1_B"]) & (j["ks_first_in_B"] == j["f1_A"])
    j["counts_same"], j["counts_swapped"] = cs, cw & ~cs
    j["far"] = np.minimum(same, swap) > 10           # neither orientation agrees: a mislink or a broken value
    res = {"reads_results": False, "matches_with_both": int(len(j))}
    res["by_year"] = []
    for y, g in j.groupby("year"):
        res["by_year"].append({"year": int(y), "matches": int(len(g)),
                               "speed_swap_flag": int(g["swap_speed"].sum()),
                               "counts_match_own_side": int(g["counts_same"].sum()),
                               "counts_match_other_side": int(g["counts_swapped"].sum()),
                               "speed_swap_and_counts_swapped": int((g["swap_speed"] & g["counts_swapped"]).sum()),
                               "neither_orientation_within_10": int(g["far"].sum())})
    # the flagged matches' events
    fl = j[j["swap_speed"]]
    res["swap_flag_top_events"] = fl.groupby(["year", "tournament_name"]).size().sort_values(ascending=False) \
        .head(15).reset_index().rename(columns={0: "matches"}).to_dict(orient="records")
    # a count-only rule usable in every season: two sides with identical first-serves-in AND identical totals is a
    # duplicated side; with no point table the swap itself is undetectable from speeds alone
    allks = wide(r, "mantennisdata", ["spd1", "ks_first_in", "ks_first_total"]).join(yrs, how="left")
    dup = (allks["ks_first_in_A"] == allks["ks_first_in_B"]) & (allks["ks_first_total_A"] == allks["ks_first_total_B"]) \
        & (allks["spd1_A"] == allks["spd1_B"])
    res["ks_identical_sides_by_year"] = allks.assign(dup=dup).groupby("year")["dup"].agg(["size", "sum"]) \
        .astype(int).reset_index().to_dict(orient="records")
    OUT.write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, default=str)[:5000])


if __name__ == "__main__":
    main()
