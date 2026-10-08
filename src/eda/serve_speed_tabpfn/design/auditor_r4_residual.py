"""R4 red team (auditor): where do my independent rebuild and the R3 build disagree? Values only (no result, no target).

    1  panel diff: use rows in one panel and not the other, and rows whose value y, n, basis or edition differ
       (my 'spec' panel from auditor_r4_rebuild against speed_panel.parquet), by reason and year
    2  the frame matches with the largest |spd_f difference| (s_f units): for each, the history rows (of both sides)
       that differ between the panels
    3  the women's and the men's spd_raw presence disagreements, explained

Run: ./python.sh src/eda/serve_speed_tabpfn/design/auditor_r4_residual.py
Writes data/studies/serve_speed_tabpfn/design/auditor_r4_residual.json
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

from src.eda.serve_speed_tabpfn.design import auditor_r4_rebuild as RB  # noqa: E402

OUT = RB.AL.OUT / "auditor_r4_residual.json"


def main() -> None:
    mine = RB.panel(True, True, True)
    r3 = pd.read_parquet(RB.R3_PANEL)
    r3u = r3[r3["use"]]
    k = ["match_id", "side"]
    j = mine.merge(r3u, on=k, how="outer", suffixes=("_m", "_b"), indicator=True)
    res = {"reads_results": False, "mine_rows": int(len(mine)), "r3_use_rows": int(len(r3u))}
    only_m = j[j["_merge"] == "left_only"]
    only_b = j[j["_merge"] == "right_only"]
    both = j[j["_merge"] == "both"]
    # why are rows only in one panel? look the R3 row's drop reason / source up
    om = only_m[k].merge(r3[k + ["use", "drop_reason", "source", "y"]], on=k, how="left")
    res["only_in_mine"] = {"rows": int(len(only_m)),
                           "r3_drop_reason": om["drop_reason"].fillna("absent from R3 panel").value_counts().to_dict(),
                           "by_year": only_m["year_m"].value_counts().sort_index().astype(int).to_dict(),
                           "examples": om.head(8).to_dict(orient="records")}
    res["only_in_r3"] = {"rows": int(len(only_b)), "source": only_b["source_b"].value_counts().to_dict(),
                         "by_year": only_b["year_b"].value_counts().sort_index().astype(int).to_dict(),
                         "examples": only_b[k + ["source_b", "y_b", "n_b", "year_b"]].head(8).to_dict(orient="records")}
    dy = (both["y_m"] - both["y_b"]).abs() > 1e-9
    dn = both["n_m"].astype(float) != both["n_b"].astype(float)
    de = both["edition_m"] != both["edition_b"]
    dsrc = both["source_m"] != both["source_b"]
    res["both_rows"] = int(len(both))
    res["value_diff"] = {"y": int(dy.sum()), "n": int(dn.sum()), "edition": int(de.sum()), "source": int(dsrc.sum()),
                         "source_pairs": {f"{a}->{b}": int(v) for (a, b), v in
                                          both[dsrc].groupby(["source_m", "source_b"]).size().items()},
                         "y_diff_examples": both[dy][k + ["source_m", "source_b", "y_m", "y_b", "n_m", "n_b", "year_m"]]
                         .head(10).to_dict(orient="records")}
    # 2 the largest spd_f differences
    feat_m = pd.read_parquet(RB.FEAT_OUT)
    feat_b = pd.read_parquet(RB.BUILD, columns=["match_id", "tour", "season", "spd_f_unclipped_km_h"])
    f = feat_b.merge(feat_m[["match_id", "d"]], on="match_id")
    f["diff_sf"] = (f["spd_f_unclipped_km_h"] - f["d"]) / RB.S_F_BUILD
    big = f[f["tour"].eq("atp")].reindex(f["diff_sf"].abs().sort_values(ascending=False).index).head(40)
    big = big[big["tour"].eq("atp")].head(15)
    # which players' histories touch a differing row?
    diff_rows = pd.concat([only_m[k].assign(kind="only_mine"), only_b[k].assign(kind="only_r3"),
                           both[dy | dn | de][k].assign(kind="value")])
    pl = pd.concat([mine[k + ["player_id", "obs", "tournament_id"]], r3u[k + ["player_id", "obs", "tournament_id"]]]) \
        .drop_duplicates(k)
    diff_rows = diff_rows.merge(pl, on=k, how="left")
    fk = pd.read_parquet(ROOT / "data" / "studies" / "serve_speed_tabpfn" / "frame_keys.parquet",
                         columns=["match_id", "player_a_id", "player_b_id", "es"])
    expl = []
    for _, row in big.iterrows():
        kk = fk[fk["match_id"] == row["match_id"]].iloc[0]
        hits = diff_rows[diff_rows["player_id"].isin([kk["player_a_id"], kk["player_b_id"]])
                         & (diff_rows["obs"] >= kk["es"] - 364) & (diff_rows["obs"] <= kk["es"])]
        expl.append({"match_id": row["match_id"], "season": int(row["season"]), "diff_sf": float(row["diff_sf"]),
                     "differing_history_rows": hits[["match_id", "side", "kind"]].to_dict(orient="records")})
    res["largest_diffs"] = expl
    res["largest_explained_by_panel_rows"] = float(np.mean([len(e["differing_history_rows"]) > 0 for e in expl]))
    # all men's frame matches beyond 0.05: share whose sides' 364-day history touches a differing row
    out_m = f[f["tour"].eq("atp") & (f["diff_sf"].abs() > 0.05)]
    fk2 = fk.set_index("match_id")
    touched = []
    dr = diff_rows.groupby("player_id")["obs"].apply(np.asarray).to_dict()
    for mid in out_m["match_id"]:
        kk = fk2.loc[mid]
        t = False
        for pid in (kk["player_a_id"], kk["player_b_id"]):
            o = dr.get(pid)
            if o is not None and np.any((o >= kk["es"] - 364) & (o <= kk["es"])):
                t = True
        touched.append(t)
    res["men_beyond_0.05"] = {"matches": int(len(out_m)), "share_touching_a_differing_panel_row":
                              float(np.mean(touched)) if touched else None}
    OUT.write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({kk: v for kk, v in res.items() if kk not in ("largest_diffs",)}, indent=1, default=str)[:6000])
    print(json.dumps(res["largest_diffs"][:6], indent=1, default=str)[:3000])


if __name__ == "__main__":
    main()
