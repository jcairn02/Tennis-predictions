"""Design R1 (speed-data engineer), step 3b: where the ATP key statistic and the point mean of the same player-match
disagree by more than 3 km/h, which one agrees with the player's level in his other matches? Seasons 2021-2023 only
(a statistic target: the player's other-match speed; logged in the design file's Looks). No match result is read.

Reference for a player-match: the median, over the same player's OTHER tour-level matches of the same season (Infosys
points and key statistic agreeing within 1 km/h), of the point mean minus the frozen per-event offset is not used here:
both candidate values are compared against the same reference, so an event's level cancels in the comparison of the
two errors, not in each error.

Run: ./python.sh src/eda/serve_speed_tabpfn/design/engineer_basis_ref.py
Writes data/studies/serve_speed_tabpfn/design/engineer_basis_ref.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from src.eda.serve_speed_tabpfn.design import engineer_common as EC  # noqa: E402

LAST = 2023


def main() -> None:
    r = pd.read_parquet(EC.RECORDS)
    r = r[r["linked"]]
    ks = r[r["source"].eq("mantennisdata") & r["spd1"].notna()].drop_duplicates(["match_id", "side"], keep=False)
    p = r[r["source"].eq("infosys") & r["gate_half"].astype(bool)]
    j = ks[["match_id", "side", "spd1", "ks_first_in"]].rename(columns={"spd1": "ks"}).merge(
        p[["match_id", "side", "spd1", "n1", "f1"]], on=["match_id", "side"])
    m = EC.stage0(cols=["match_id", "year", "tournament_id", "player_a_id", "player_b_id"])
    j = j.merge(m, on="match_id")
    j = j[j["year"] <= LAST].copy()
    j["player_id"] = np.where(j["side"].eq("A"), j["player_a_id"], j["player_b_id"])
    j["d"] = j["ks"] - j["spd1"]
    j["agree"] = j["d"].abs() <= 1
    # each player-season's agreeing matches: leave-one-out median of the point mean
    out_rows = []
    for (pid, yr), g in j.groupby(["player_id", "year"]):
        ok = g[g["agree"]]
        if len(ok) < 3:
            continue
        for i, row in g.iterrows():
            others = ok.loc[ok.index != i, "spd1"]
            if len(others) < 3:
                continue
            out_rows.append((i, float(others.median()), len(others)))
    ref = pd.DataFrame(out_rows, columns=["i", "ref", "k"]).set_index("i")
    j = j.join(ref, how="inner")
    j["e_ks"] = (j["ks"] - 0.5) - j["ref"]
    j["e_pm"] = j["spd1"] - j["ref"]
    res = {"reads_results": False, "seasons": f"2021-{LAST}", "player_matches_with_reference": int(len(j))}
    for name, g in (("big_gap_gt3", j[j["d"].abs() > 3]), ("gap_1_3", j[j["d"].abs().between(1, 3)]),
                    ("agree_le1", j[j["d"].abs() < 1])):
        res[name] = {"n": int(len(g)), "median_abs_err_keystat_minus_half": round(float(g["e_ks"].abs().median()), 3),
                     "median_abs_err_point_mean": round(float(g["e_pm"].abs().median()), 3),
                     "share_keystat_closer": round(float((g["e_ks"].abs() < g["e_pm"].abs()).mean()), 3),
                     "mean_err_keystat": round(float(g["e_ks"].mean()), 3),
                     "mean_err_point_mean": round(float(g["e_pm"].mean()), 3)}
    big = j[j["d"].abs() > 3]
    for sgn, g in (("keystat_higher", big[big["d"] > 0]), ("keystat_lower", big[big["d"] < 0])):
        res[f"big_{sgn}"] = {"n": int(len(g)), "median_abs_err_keystat": round(float(g["e_ks"].abs().median()), 3),
                             "median_abs_err_point_mean": round(float(g["e_pm"].abs().median()), 3),
                             "share_keystat_closer": round(float((g["e_ks"].abs() < g["e_pm"].abs()).mean()), 3)}
    # the same split by completeness of the point table
    big = big.assign(complete=(big["f1"] == big["ks_first_in"]) & (big["n1"] == big["f1"]))
    res["big_by_complete"] = (big.groupby("complete").apply(
        lambda g: pd.Series({"n": len(g), "share_keystat_closer": (g["e_ks"].abs() < g["e_pm"].abs()).mean()}))
        .round(3).reset_index().to_dict(orient="records"))
    (EC.OUT / "engineer_basis_ref.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
