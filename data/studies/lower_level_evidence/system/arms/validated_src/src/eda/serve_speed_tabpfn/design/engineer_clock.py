"""Design R1 (speed-data engineer), step 7: linking and the clock. Reads no match result.

    * ManTennisData (no match dates): its rows linked to the rebuilt Stage 0 take es / lf / obs from timing.parquet by
      match_id; how many are unlinked, how many linked rows lack a clock, and how wide their windows are
    * every draft-panel row: clock present, window width by source
    * the model frame (pre-rebuild Stage 0 ids) against the rebuilt Stage 0: missing ids by tour and season, the id map,
      and player ids that differ between the two Stage 0 versions for the same match (a speed history keyed on the rebuilt
      ids would miss them)
    * name-based player ids ('<tour>:name:...') in the rebuilt Stage 0 and in the draft panel

Run: ./python.sh src/eda/serve_speed_tabpfn/design/engineer_clock.py
Writes data/studies/serve_speed_tabpfn/design/engineer_clock.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from src.eda.serve_speed_tabpfn.design import engineer_common as EC  # noqa: E402

PANEL0 = EC.OUT / "engineer_panel0.parquet"


def main() -> None:
    res = {"reads_results": False}
    tm = pd.read_parquet(EC.TIMING, columns=["match_id", "es", "lf", "obs", "exact", "width_days", "window_basis"])
    # ManTennisData rows
    r = pd.read_parquet(EC.RECORDS)
    md = r[r["source"].eq("mantennisdata")]
    mdl = md[md["linked"]].merge(tm, on="match_id", how="left")
    sp = pd.read_parquet(EC.SPEEDS, columns=["source", "year", "event", "draw", "match_id", "side", "ks_spd1"])
    spm = sp[sp["source"].eq("mantennisdata")]
    res["mantennisdata"] = {
        "rows": int(len(md)), "rows_timed": int(md["timed"].sum()), "linked_rows": int(md["linked"].sum()),
        "unlinked_timed_rows_by_year_event_draw": (spm[spm["match_id"].isna() & spm["ks_spd1"].notna()]
                                                   .groupby(["year", "event", "draw"]).size().reset_index(name="rows")
                                                   .to_dict(orient="records")),
        "linked_rows_without_clock": int(mdl["es"].isna().sum()),
        "exact_day_share": round(float(mdl["exact"].mean()), 4),
        "width_days": EC.q(mdl["lf"] - mdl["es"], (0.5, 0.75, 0.9, 0.99)),
        "window_basis": mdl["window_basis"].value_counts().head(8).to_dict()}
    # every draft-panel row
    p = pd.read_parquet(PANEL0)
    pw = p.merge(tm[["match_id", "width_days", "window_basis"]], on="match_id", how="left")
    res["panel_clock"] = {"rows": int(len(p)), "without_es": int(p["es"].isna().sum()),
                          "exact_share_by_source": pw.groupby("source")["exact"].mean().round(4).to_dict(),
                          "median_width_by_source": (pw["lf"] - pw["es"]).groupby(pw["source"]).median().to_dict(),
                          "obs_minus_es_median": float((p["obs"] - p["es"]).median())}
    # model frame vs the rebuilt Stage 0
    f = EC.model_frame()
    new = EC.stage0(cols=["match_id", "tour", "year", "player_a_id", "player_b_id"])
    pre = EC.stage0(EC.S0_PRE, cols=["match_id", "tour", "year", "player_a_id", "player_b_id"])
    remap = EC.id_map()
    fr = f.merge(pre, on="match_id", how="left", suffixes=("", "_pre"))
    res["frame_ids_in_pre_rebuild"] = int(fr["player_a_id"].notna().sum())
    fr["new_id"] = fr["match_id"].map(lambda x: remap.get(x, x))
    fr = fr.merge(new.rename(columns={"match_id": "new_id", "player_a_id": "a_new", "player_b_id": "b_new",
                                      "tour": "tour_new", "year": "year_new"}), on="new_id", how="left")
    miss_direct = ~f["match_id"].isin(set(new["match_id"]))
    res["frame_missing_in_rebuilt_direct"] = (f[miss_direct].groupby(["tour", "season"]).size()
                                              .reset_index(name="n").to_dict(orient="records"))
    res["frame_missing_after_id_map"] = int(fr["a_new"].isna().sum())
    res["frame_in_id_map"] = int(f["match_id"].isin(set(remap)).sum())
    same_pair = ((fr["player_a_id"] == fr["a_new"]) & (fr["player_b_id"] == fr["b_new"])) | \
                ((fr["player_a_id"] == fr["b_new"]) & (fr["player_b_id"] == fr["a_new"]))
    flipped = (fr["player_a_id"] == fr["b_new"]) & (fr["player_b_id"] == fr["a_new"])
    res["frame_player_ids_differ"] = (fr[fr["a_new"].notna() & ~same_pair].groupby(["tour", "season"]).size()
                                      .reset_index(name="n").to_dict(orient="records"))
    res["frame_sides_flipped_in_rebuilt"] = int((fr["a_new"].notna() & flipped & ~(fr["player_a_id"] == fr["a_new"]))
                                                .sum())
    # name-based player ids
    for lab, s0 in (("rebuilt", new), ("pre_rebuild", pre)):
        ids = pd.concat([s0[["tour", "year", "player_a_id"]].rename(columns={"player_a_id": "pid"}),
                         s0[["tour", "year", "player_b_id"]].rename(columns={"player_b_id": "pid"})])
        nm = ids[ids["pid"].astype(str).str.contains(":name:")]
        res[f"name_ids_{lab}"] = nm.groupby(["tour", "year"]).size().reset_index(name="player_rows") \
            .query("year >= 2021").to_dict(orient="records")
    res["panel_name_ids"] = int(p["player_id"].astype(str).str.contains(":name:").sum())
    res["panel_name_ids_by_tour_year"] = (p[p["player_id"].astype(str).str.contains(":name:")]
                                          .groupby(["tour", "year"]).size().reset_index(name="n")
                                          .to_dict(orient="records"))
    # the player ids of the frame's players that appear in the panel under the same id
    fpl = pd.concat([fr[["tour", "season", "player_a_id"]].rename(columns={"player_a_id": "pid"}),
                     fr[["tour", "season", "player_b_id"]].rename(columns={"player_b_id": "pid"})])
    have = set(p["player_id"].astype(str))
    fpl["in_panel"] = fpl["pid"].astype(str).isin(have)
    res["frame_players_with_any_panel_row_by_tour"] = fpl.groupby("tour")["in_panel"].mean().round(4).to_dict()
    (EC.OUT / "engineer_clock.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, default=str)[:7000])


if __name__ == "__main__":
    main()
