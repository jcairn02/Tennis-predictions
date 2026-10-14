"""Can Tennis My Life's ATP player database (backhand, weight, turned pro) be joined to the men's model matches?
(feature-interactions data map, round 0)

TML's ATP_Database.parquet has an `id` column. This script checks whether it is Sackmann's player id (Stage 0's men's ids
are "atp:<Sackmann id>") by comparing names, and measures, on the men's model matches of 2013-2024, the share where
both players' backhand (1H/2H), weight and turned-pro year are known. Counts only. Read-only.
Writes data/studies/feature_interactions/inventory/backhand_join.json.
Run: ./python.sh src/eda/feature_interactions/inventory/backhand.py
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
S = ROOT / "data" / "studies"
OUT = S / "feature_interactions" / "inventory"
OLD = S / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" / "data" / "studies"
MODEL = S / "surface_rating_race" / "model" / "model_frame.parquet"


def norm(s: pd.Series) -> pd.Series:
    return s.fillna("").map(lambda x: unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode()
                            .lower().replace("-", " ").strip())


def main() -> int:
    t = pd.read_parquet(ROOT / "data" / "dump" / "players" / "tennis_my_life" / "ATP_Database.parquet")
    s = pd.read_parquet(ROOT / "data" / "dump" / "players" / "sackmann_archive" / "atp" / "atp_players.parquet")
    s["name"] = norm(s["name_first"] + " " + s["name_last"])
    j = t.assign(pid=t["id"].astype(str)).merge(s.assign(pid=s["player_id"].astype(str))[["pid", "name", "dob"]],
                                                 on="pid", how="left")
    res = {"tml_rows": int(len(t)), "tml_ids_found_in_sackmann": float(j["name"].notna().mean()),
           "name_agrees_where_found": float((norm(j["player"]) == j["name"])[j["name"].notna()].mean()),
           "birthdate_agrees_where_found": float((j["birthdate"].astype(str) == j["dob"].astype(str))[j["name"].notna()].mean())}
    # TML's id is mostly an ATP code, not Sackmann's: join on (normalised name, birth date) to Sackmann's players,
    # trying TML's `player` and `atpname`; a key matching several Sackmann players is dropped (ambiguous)
    s_key = s.assign(key=s["name"] + "|" + s["dob"].astype(str))
    s_key = s_key[~s_key["key"].duplicated(keep=False)].set_index("key")["player_id"].astype(str)
    sid = (norm(t["player"]) + "|" + t["birthdate"].astype(str)).map(s_key)
    sid = sid.fillna((norm(t["atpname"]) + "|" + t["birthdate"].astype(str)).map(s_key))
    res["tml_rows_joined_by_name_and_birthdate"] = float(sid.notna().mean())
    t = t.assign(stage0_id="atp:" + sid.astype(str))
    t = t[sid.notna()]
    t["bh"] = t["backhand"].where(t["backhand"].isin(["1H", "2H"]))
    t["wt"] = pd.to_numeric(t["weight"], errors="coerce")
    t["tp"] = pd.to_numeric(t["turnedpro"], errors="coerce")
    mf = pd.read_parquet(MODEL, columns=["match_id", "season", "tour"])
    mf = mf[(mf["season"] <= 2024) & (mf["tour"] == "atp")].reset_index(drop=True)
    m = mf.merge(pd.read_parquet(OLD / "predictability_diagnostic" / "stage0_matches.parquet",
                                 columns=["match_id", "player_a_id", "player_b_id"]), on="match_id", how="left")
    look = t.drop_duplicates("stage0_id").set_index("stage0_id")
    out = {}
    for f in ("bh", "wt", "tp"):
        a = m["player_a_id"].map(look[f]).notna().to_numpy()
        b = m["player_b_id"].map(look[f]).notna().to_numpy()
        both = a & b
        out[f] = {p: round(float(both[(m["season"] <= 2021) == (p == "2013-2021")].mean()), 4)
                  for p in ("2013-2021", "2022-2024")}
    bh = pd.concat([m["player_a_id"].map(look["bh"]), m["player_b_id"].map(look["bh"])])
    res["men_model_matches_both_known"] = {"backhand": out["bh"], "weight": out["wt"], "turned_pro": out["tp"]}
    res["men_model_player_rows_backhand"] = bh.value_counts(dropna=False).to_dict()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "backhand_join.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
