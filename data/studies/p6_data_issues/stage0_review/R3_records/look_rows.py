"""R3 scratch (read-only): print the G1 and G2 Stage 0 rows with names, and the 2024 Tenerife events Stage 0 holds."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
S0 = ROOT / "data/studies/predictability_diagnostic/stage0_matches.parquet"
MP = ROOT / "data/studies/predictability_diagnostic/stage0_match_players.parquet"
TM = ROOT / "data/studies/match_timing/timing.parquet"

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 400)
pd.set_option("display.max_colwidth", 60)

cols = ["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "tournament_id", "tournament_name",
        "tournament_date", "status", "score", "player_a_id", "player_b_id", "a_won", "source", "source_file",
        "source_row", "tml_link"]
m = pd.read_parquet(S0, columns=cols)
names = pd.read_parquet(MP, columns=["match_id", "player_id", "player_name"]).drop_duplicates(["player_id"])
nm = names.set_index("player_id")["player_name"]
m["a_name"] = m["player_a_id"].map(nm)
m["b_name"] = m["player_b_id"].map(nm)

which = sys.argv[1] if len(sys.argv) > 1 else "g1"
if which == "g1":
    ten = m[(m["year"] == 2024) & m["tournament_name"].astype(str).str.contains("tenerife", case=False)]
    print(ten.groupby(["tour", "tournament_id", "tournament_name", "tournament_date", "qualifying", "source"]).size())
    g1 = m[(m["tournament_id"].astype(str) == "2024-2847")].sort_values(["round_order", "source_row"])
    print(len(g1))
    print(g1[["match_id", "round", "tournament_name", "tournament_date", "status", "score", "a_name", "b_name",
              "a_won", "source", "source_row"]].to_string())
    t = pd.read_parquet(TM)
    t = t[t["match_id"].isin(g1["match_id"])]
    t["es_d"] = pd.to_datetime(t["es"], unit="D").dt.date
    t["lf_d"] = pd.to_datetime(t["lf"], unit="D").dt.date
    print(t[["match_id", "round", "tournament_date", "anchor", "es_d", "lf_d", "exact", "window_basis",
             "sources", "rejected_links", "demoted"]].to_string())
elif which == "g2":
    ids = ["atp|2021-580|Q2|atp:106045|atp:208013", "atp|2021-580|Q2|atp:106408|atp:202103"]
    g2 = m[m["match_id"].isin(ids)]
    print(g2.T.to_string())
    ao = m[(m["year"] == 2021) & m["qualifying"].astype(bool) & (m["tour"] == "atp") & (m["level"] == "GS")
           & (m["tournament_date"].astype(str) < "2021-03-01")]
    print(ao.groupby(["tournament_id", "tournament_name", "tournament_date", "round", "source"]).size())
    pl = set(g2["player_a_id"]) | set(g2["player_b_id"])
    q2 = ao[(ao["round"] == "Q2") & (ao["player_a_id"].isin(pl) | ao["player_b_id"].isin(pl))]
    print(q2[["match_id", "round", "tournament_name", "tournament_date", "status", "score", "a_name", "b_name",
              "source", "source_row"]].to_string())
    t = pd.read_parquet(TM)
    t = t[t["match_id"].isin(ids)]
    t["es_d"] = pd.to_datetime(t["es"], unit="D").dt.date
    t["lf_d"] = pd.to_datetime(t["lf"], unit="D").dt.date
    print(t[["match_id", "round", "tournament_name", "tournament_date", "anchor", "es_d", "lf_d", "exact",
             "window_basis", "sources", "rejected_links", "demoted"]].to_string())
