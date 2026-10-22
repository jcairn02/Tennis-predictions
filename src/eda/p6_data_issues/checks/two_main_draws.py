"""The feed builder's "player in two main draws of one week" flags (candidate_stage0's duplicate check), listed by week
and event for one or more candidate folders (read-only). Usage: two_main_draws.py <candidate folder> [...]"""
import sys
from pathlib import Path
import pandas as pd

for f in map(Path, sys.argv[1:]):
    m = pd.read_parquet(f / "stage0_matches.parquet",
                        columns=["match_id", "tour", "tournament_id", "tournament_name", "tournament_date", "round",
                                 "qualifying", "player_a_id", "player_b_id", "level"])
    add = pd.read_parquet(f / "additions.parquet", columns=["match_id"]) if (f / "additions.parquet").exists() else None
    new = set(add["match_id"]) if add is not None else set()
    m["new"] = m["match_id"].isin(new)
    pl = pd.concat([m.assign(pid=m["player_a_id"]), m.assign(pid=m["player_b_id"])])
    pl = pl[pl["round"].ne("RR") & ~pl["qualifying"].astype(bool)]
    pw = pl.groupby(["pid", "tournament_date"]).agg(events=("tournament_id", "nunique"), new=("new", "any"),
                                                   names=("tournament_name", lambda s: " | ".join(sorted(set(map(str, s))))),
                                                   tour=("tour", "first"), level=("level", lambda s: ",".join(sorted(set(map(str, s))))))
    flag = pw[(pw["events"] > 1) & pw["new"]].reset_index()
    print(f"{f.name}: {len(flag)} player-weeks with a new match in two main draws")
    print(flag.groupby(["tournament_date", "tour"]).size().to_string())
    print(flag.groupby("names").size().sort_values(ascending=False).head(25).to_string())
