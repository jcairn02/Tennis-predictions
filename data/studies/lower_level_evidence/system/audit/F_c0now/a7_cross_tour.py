"""Role E audit of C0_now, part 7: the cross-tour identity defect. TennisLive keeps one id space per tour (id 100093 is
Daniel Fennis on the ATP pages and Kennedy Hutto on the WTA pages), but candidate_stage0.crosswalk / resolve_ids key on
the bare source id, so a row of one tour can take a Stage 0 id of the other tour. Counts the rows, the frame players
reached, and how many the chain's identity repair (alias by the match's tour and exact name) would put right.
Names, ids and counts only. Run: ./python.sh data/studies/lower_level_evidence/system/audit/F_c0now/a7_cross_tour.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from src.eda.lower_level_evidence import common as LC  # noqa: E402
from src.eda.feature_alpha_audit.repair_data import name_key  # noqa: E402

AUD = ROOT / "data/studies/lower_level_evidence/system/audit/F_c0now"
CAND = ROOT / "data/studies/lower_level_evidence/system/stage0/C0_now"
OUT: dict = {}
m = pd.read_parquet(CAND / "stage0_matches.parquet", columns=["match_id", "tour", "source", "tournament_date",
                                                               "map_level"])
ref_ids = set(pd.read_parquet(LC.STAGE0_DIR / "stage0_matches.parquet", columns=["match_id"])["match_id"])
mp = pd.read_parquet(CAND / "stage0_match_players.parquet", columns=["match_id", "player_id", "player_name", "country"])
mp = mp.merge(m, on="match_id")
mp["new"] = ~mp["match_id"].isin(ref_ids)
mp["id_tour"] = mp["player_id"].str.split(":").str[0]
bad = mp[mp["new"] & mp["id_tour"].ne(mp["tour"])].copy()
OUT["wrong_tour_player_rows"] = int(len(bad))
OUT["wrong_tour_matches"] = int(bad["match_id"].nunique())
OUT["wrong_tour_distinct_ids"] = int(bad["player_id"].nunique())
OUT["wrong_tour_rows_by_source_tour"] = bad.groupby(["source", "tour"]).size().rename("n").reset_index().to_dict(
    "records")
# the ids' own Stage 0 names (frozen rows) beside the names the new rows carry
ref_rows = mp[~mp["new"]]
own = ref_rows.drop_duplicates("player_id").set_index("player_id")[["player_name", "tour"]]
fr = set(pd.read_parquet(LC.FRAME, columns=["match_id"])["match_id"])
fp = set(ref_rows.loc[ref_rows["match_id"].isin(fr), "player_id"])
bad["frame_player"] = bad["player_id"].isin(fp)
OUT["wrong_tour_ids_that_are_frame_players"] = int(bad.loc[bad["frame_player"], "player_id"].nunique())
OUT["wrong_tour_rows_on_frame_players"] = int(bad["frame_player"].sum())
ex = bad[bad["frame_player"]].groupby(["player_id"]).agg(rows=("match_id", "size"),
                                                         names_in_new_rows=("player_name", lambda s: "; ".join(
                                                             sorted(set(s))[:3])),
                                                         match_tour=("tour", "first")).reset_index()
ex["stage0_name"] = ex["player_id"].map(own["player_name"])
OUT["frame_player_examples"] = ex.sort_values("rows", ascending=False).head(12).astype(str).to_dict("records")
# would the chain's repair (sackmann ids by (match tour, exact name), unique, no country clash) re-home them?
q = mp[mp["source"].eq("sackmann")].assign(key=lambda d: d["player_name"].map(name_key))
ids = q.groupby(["tour", "key"])["player_id"].agg(lambda s: tuple(sorted(set(s))))
bad["key"] = bad["player_name"].map(name_key)
cand = [ids.get((t, k), ()) for t, k in zip(bad["tour"], bad["key"])]
bad["repair_target"] = [c[0] if len(c) == 1 else None for c in cand]
OUT["wrong_tour_rows_repair_would_rehome_to_right_tour"] = int(
    bad["repair_target"].notna().sum())
OUT["wrong_tour_rows_left_wrong_after_repair"] = int(bad["repair_target"].isna().sum())
OUT["wrong_tour_rows_left_wrong_after_repair_on_frame_players"] = int((bad["repair_target"].isna()
                                                                        & bad["frame_player"]).sum())
bad.drop(columns=["key"]).to_csv(AUD / "cross_tour_rows.csv.gz", index=False, compression="gzip")
(AUD / "a7_results.json").write_text(json.dumps(OUT, indent=1, default=str), encoding="utf-8")
print(json.dumps(OUT, indent=1, default=str))
