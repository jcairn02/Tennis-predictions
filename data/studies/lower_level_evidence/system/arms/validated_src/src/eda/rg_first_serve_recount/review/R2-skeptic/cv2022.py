"""R2-skeptic: my own recount of the Hawk-Eye Court Vision copy of RG 2022 (data/dump/points/slam_ball_tracking/, the
staged verbatim copy of the public CSVs; one row per serve, a faulted first serve is its own "Faulty Serve" row), as a
per-row referee. 2022 is the one disputed edition where this copy is reliable: against RG's statistics it reads first
serves in exactly on 94-95% of rows and one MORE than RG on only 0-0.5% (the lead's agree_cv_vs_api.csv; re-derived
here on the agreeing rows), so on a "-" or "0" row (Sackmann's first serves in at or below RG's) a Court Vision read
equal to RG's split is strong evidence that RG's record, not Sackmann's, is right.

Players are paired to RG's teams within RG's own match code by surname (Court Vision names are "X.SURNAME"), never by
position. Writes cv2022_sides.csv and cv2022_summary.json.
Usage: ./python.sh src/eda/rg_first_serve_recount/review/R2-skeptic/cv2022.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R2-skeptic"
CV = ROOT / "data" / "dump" / "points" / "slam_ball_tracking"


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    lc = load("link_compare")
    cat = pd.read_parquet(CV / "matches.parquet")
    cat = cat[cat["slam"].eq("RG") & cat["year"].astype(str).eq("2022")]
    pt = pd.read_parquet(CV / "points" / "RG_2022.parquet")
    dup = int(pt.duplicated(["match_id", "point_ID"]).sum())
    pt = pt.drop_duplicates(["match_id", "point_ID"])
    pts = pt[~pt["point_end_type"].eq("Faulty Serve")]
    rows = []
    for r in cat.itertuples(index=False):
        code = str(r.match_id).split("_")[-1]
        q = pts[pts["match_id"].astype(str).str.split("_").str[-1].eq(code)]
        if q.empty:
            continue
        for pid, nm in ((r.player1_id, r.player1), (r.player2_id, r.player2)):
            s = q[q["server_id"].astype(str).eq(str(pid))]
            n = s["serve_num"].astype(str)
            w = s["point_winner_id"].astype(str).eq(str(pid))
            rows.append({"year": 2022, "code": code, "cv_name": nm, "surname": lc.fold(str(nm).split(".", 1)[-1]),
                         "cv_svpt": len(s), "cv_first_in": int(n.eq("1").sum()),
                         "cv_first_won": int((n.eq("1") & w).sum()), "cv_second_won": int((n.eq("2") & w).sum()),
                         "cv_ace": int(s["point_end_type"].eq("Ace").sum()),
                         "cv_df": int(s["point_end_type"].eq("DoubleFault").sum())})
    cv = pd.DataFrame(rows)
    s = pd.read_parquet(OUT / "my_sides.parquet")
    s = s[s["event"].eq("RG") & s["year"].eq(2022)].copy()
    # pair by surname within the code: the API side's last-name words must contain the CV surname words
    def match(r):
        c = cv[cv["code"].eq(r.code)]
        last = lc.fold(r.api_last)
        hits = c[[set(x) <= set(last) or "".join(x) == "".join(last) for x in c["surname"]]]
        return hits.iloc[0] if len(hits) == 1 else None
    recs = []
    for r in s.itertuples(index=False):
        h = match(r)
        recs.append({} if h is None else h[["cv_name", "cv_svpt", "cv_first_in", "cv_first_won", "cv_second_won",
                                            "cv_ace", "cv_df"]].to_dict())
    s = pd.concat([s.reset_index(drop=True), pd.DataFrame(recs)], axis=1)
    s["cv_complete"] = s["cv_svpt"].eq(s["off_svpt"])
    s["cv_eq_off_split"] = s["cv_complete"] & s["cv_first_in"].eq(s["off_first_in"]) & s["cv_first_won"].eq(
        s["off_first_won"]) & s["cv_second_won"].eq(s["off_second_won"])
    s["cv_eq_raw_split"] = s["cv_complete"] & s["cv_first_in"].eq(s["raw_first_in"]) & s["cv_first_won"].eq(
        s["raw_first_won"]) & s["cv_second_won"].eq(s["raw_second_won"])
    s["sign"] = np.sign(s["d_first_in"]).map({1.0: "+", -1.0: "-", 0.0: "0"})
    s.to_csv(OUT / "cv2022_sides.csv", index=False)
    agree = s[s["my_cls"].isin(["equal"]) & s["cv_complete"]]
    res = {"duplicate_point_rows_dropped": dup, "cv_player_rows": int(len(cv)),
           "sides_2022_with_cv": int(s["cv_svpt"].notna().sum()),
           "calibration_on_equal_rows": {"sides": int(len(agree)),
                                         "cv_first_in_equal": int(agree["cv_first_in"].eq(agree["off_first_in"]).sum()),
                                         "cv_first_in_one_more": int((agree["cv_first_in"] - agree["off_first_in"]).eq(1).sum()),
                                         "cv_first_in_more_any": int((agree["cv_first_in"] > agree["off_first_in"]).sum()),
                                         "cv_split_equal": int(agree["cv_eq_off_split"].sum())}}
    disp = s[s["my_cls"].isin(["split", "split_other"]) & s["cv_complete"]]
    res["disputed_complete"] = disp.groupby("sign").apply(
        lambda g: {"sides": len(g), "cv_equals_official_split": int(g["cv_eq_off_split"].sum()),
                   "cv_equals_sackmann_split": int(g["cv_eq_raw_split"].sum()),
                   "cv_first_in_equals_official": int(g["cv_first_in"].eq(g["off_first_in"]).sum()),
                   "cv_first_in_equals_sackmann": int(g["cv_first_in"].eq(g["raw_first_in"]).sum())}).to_dict()
    (OUT / "cv2022_summary.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
