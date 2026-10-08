"""The Live Tennis API's public match index (Zenodo sample) against the data map's point gaps.

The vendor's paid archive is claimed to carry point sequences for most of the matches its index lists
(99.6% of Challenger men's singles, by its own count; 60.5% of all 2023+ matches "point-complete"). The
index is public and already in the dump, so the share of a gap's matches that it lists is an upper bound
on what the paid archive could fill. Links are by tour, the pair of surname keys and the scheduled day
within -10 to +21 days of the data map's date (tournament start), as the data map links its sources.

Usage:
    ./python.sh src/eda/gap_sources/lta_index_links.py

Writes data/studies/gap_sources/lta_index_links.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.data_map.measure import pair_key, surname_key   # noqa: E402
from src.eda.gap_sources.sample import gap_population        # noqa: E402

DUMP = PROJECT_ROOT / "data" / "dump"
OUT = PROJECT_ROOT / "data" / "studies" / "gap_sources" / "lta_index_links.json"
GAPS = ["challenger_points_2025", "atp_points_2025", "slam_points_ao_rg", "itf_detail"]


def main() -> int:
    idx = pd.read_parquet(DUMP / "matches" / "live_tennis_api_zenodo" / "matches.parquet",
                          columns=["match_id", "player1_id", "player2_id", "tournament", "scheduled_time_utc", "is_qualifying"])
    pl = pd.read_parquet(DUMP / "players" / "live_tennis_api_zenodo" / "players.parquet",
                         columns=["player_id", "name", "tour"]).set_index("player_id")
    idx["tour"] = idx["player1_id"].map(pl["tour"]).fillna(idx["player2_id"].map(pl["tour"])).map({"atp": "M", "wta": "W"})
    idx["pair"] = pair_key(idx["player1_id"].map(pl["name"]).map(surname_key),
                           idx["player2_id"].map(pl["name"]).map(surname_key))
    idx["d_i"] = pd.to_datetime(idx["scheduled_time_utc"], errors="coerce")
    idx = idx.dropna(subset=["tour", "pair", "d_i"])
    m = pd.read_parquet(PROJECT_ROOT / "data" / "studies" / "data_map" / "matches.parquet")
    gaps = {g["id"]: g for g in yaml.safe_load((PROJECT_ROOT / "data" / "data_map.yaml").read_text(encoding="utf-8"))["gaps"]}
    out = {"index_rows": int(len(idx)), "index_first": str(idx["d_i"].min()), "index_last": str(idx["d_i"].max())}
    for gap_id in GAPS:
        pop = gap_population(m, gaps[gap_id]["select"])
        pop["pair"] = pair_key(pop["name1"].map(surname_key), pop["name2"].map(surname_key))
        cand = pop[["uid", "tour", "pair", "d", "level", "year"]].merge(idx[["tour", "pair", "d_i"]], on=["tour", "pair"])
        delta = (cand["d_i"] - cand["d"]).dt.days
        listed = set(cand.loc[(delta >= -10) & (delta <= 21), "uid"])
        pop["listed"] = pop["uid"].isin(listed)
        by = pop.groupby(["tour", "level", "year"])["listed"].agg(["size", "sum"])
        out[gap_id] = {"gap": int(len(pop)), "listed_by_index": int(pop["listed"].sum()),
                       "share": round(float(pop["listed"].mean()), 3),
                       "by_tour_level_year": {f"{t}|{lv}|{y}": {"gap": int(r["size"]), "listed": int(r["sum"])}
                                              for (t, lv, y), r in by.iterrows()}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk != "by_tour_level_year"})
                      for k, v in out.items()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
