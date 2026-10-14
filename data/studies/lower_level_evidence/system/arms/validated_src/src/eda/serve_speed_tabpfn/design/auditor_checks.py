"""Design R2 (auditor): result-free spot checks of the R1 proposals' data claims. Values and counts only; no match
result, no statistic target, no price is read.

    1  the modeller's panel against the engineer's draft panel: rows per (tour, year, Slam), AO 2026 in particular
    2  ManTennisData quarterfinals: speeds.parquet's draw label (stadie_id startswith "Q") against Stage 0's qualifying
       flag and round of the linked match
    3  the model frame against Stage 0: men's 2018; women's 2026 ids absent from the rebuild; matches whose player ids
       differ between the pre-rebuild and the rebuilt Stage 0
    4  Slam qualifying rows in the panels by year (the train/test coverage shift)
    5  the modeller's frozen system offsets: fitted on <= 2022 against <= 2023 (stability)

Run: ./python.sh src/eda/serve_speed_tabpfn/design/auditor_checks.py
Writes data/studies/serve_speed_tabpfn/design/auditor_checks.json
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
from src.eda.serve_speed_tabpfn.design import modeller_common as M  # noqa: E402
from src.eda.serve_speed_tabpfn.design import modeller_state as MS  # noqa: E402

OUT = EC.OUT / "auditor_checks.json"


def main() -> None:
    res: dict = {"reads_results": False}
    # 1 panels
    mp = M.panel("ks_first")
    ep = pd.read_parquet(EC.OUT / "engineer_panel0.parquet")
    for name, p in (("modeller_ks_first", mp), ("engineer_panel0", ep)):
        slam = np.where(p["level"].eq("GS"), EC.slam_of(p["level"], p["tournament_name"]).to_numpy(), "tour")
        g = p.assign(slam=slam).groupby(["tour", "year", "slam"]).size()
        res[f"{name}_rows_2024_26"] = {f"{t}|{y}|{s}": int(v) for (t, y, s), v in g.items() if y >= 2024}
    # 2 ManTennisData quarterfinals
    sp = pd.read_parquet(EC.SPEEDS, columns=["source", "draw", "round", "match_id", "side", "ks_spd1"])
    sp = sp[sp["source"].eq("mantennisdata")]
    s0 = EC.stage0(cols=["match_id", "qualifying", "round", "level"])
    q = sp[sp["round"].astype(str).str.upper().eq("QF")].merge(s0.rename(columns={"round": "round_s0"}),
                                                                on="match_id", how="left")
    res["mantd_QF"] = {"rows": int(len(q)), "labelled_qual": int(q["draw"].eq("qual").sum()),
                       "linked": int(q["match_id"].notna().sum()),
                       "linked_to_qualifying_match": int(q["qualifying"].eq(True).sum()),
                       "linked_round_s0": q["round_s0"].value_counts(dropna=False).astype(int).to_dict()}
    rounds = sp["round"].astype(str).str.upper()
    res["mantd_round_labels"] = rounds.value_counts().head(20).astype(int).to_dict()
    res["mantd_qual_label_by_round"] = sp.assign(r=rounds).groupby("r")["draw"].apply(
        lambda x: int(x.eq("qual").sum())).loc[lambda x: x > 0].astype(int).to_dict()
    # 3 frame against Stage 0
    fr = pd.read_parquet(EC.MODEL_FRAME, columns=["match_id", "tour", "season"])
    res["frame_men_by_season"] = fr[fr["tour"].eq("atp")]["season"].value_counts().sort_index().astype(int).to_dict()
    pre = EC.stage0(EC.S0_PRE, cols=["match_id", "player_a_id", "player_b_id"])
    new = EC.stage0(cols=["match_id", "player_a_id", "player_b_id"])
    remap = EC.id_map()
    f2 = fr.assign(nid=fr["match_id"].map(lambda x: remap.get(x, x)))
    f2 = f2.merge(pre.rename(columns={"player_a_id": "a_pre", "player_b_id": "b_pre"}), on="match_id", how="left")
    f2 = f2.merge(new.rename(columns={"match_id": "nid", "player_a_id": "a_new", "player_b_id": "b_new"}), on="nid",
                  how="left")
    res["frame_ids_rekeyed"] = int((f2["nid"] != f2["match_id"]).sum())
    res["frame_ids_absent_from_rebuild_after_map"] = int(f2["a_new"].isna().sum())
    diff = f2["a_new"].notna() & ((f2["a_pre"] != f2["a_new"]) | (f2["b_pre"] != f2["b_new"]))
    res["frame_player_ids_differ_pre_vs_rebuilt"] = f2[diff].groupby(["tour", "season"]).size().astype(int).to_dict()
    res["frame_player_ids_differ_pre_vs_rebuilt"] = {f"{k[0]}|{k[1]}": v for k, v in
                                                    res["frame_player_ids_differ_pre_vs_rebuilt"].items()}
    # 4 Slam qualifying rows
    for name, p in (("modeller_ks_first", mp), ("engineer_panel0", ep)):
        g = p[p["level"].eq("GS")].groupby(["tour", "year", "qualifying"]).size().unstack(fill_value=0)
        res[f"{name}_slam_rows_by_draw"] = {f"{t}|{y}": {"main": int(r.get(False, 0)), "qual": int(r.get(True, 0))}
                                            for (t, y), r in g.iterrows() if y >= 2019}
    # 5 frozen offsets <= 2022 vs <= 2023 (modeller's method, ks_first panel)
    o22, o23 = MS.offsets(mp, 2022), MS.offsets(mp, 2023)
    res["modeller_offsets"] = {t: {k: [round(o22[t][k], 2), round(o23[t][k], 2)] for k in o22[t] if not k.startswith("_")}
                               for t in o22}
    OUT.write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
