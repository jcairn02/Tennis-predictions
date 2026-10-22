"""R1 recompute, step 11: Stage 0 matches that would read the two G2 walkovers early, now and under the proposed date
(window from s09: as is 2021-01-08..15; after the fix 2020-12-11..18). Play day 2021-01-12 (TennisLive, SofaScore).
Same definition as for G1: shares a player; es_R >= lf + 1; es_R <= play day. Read-only."""
import pandas as pd

EPOCH = pd.Timestamp("1970-01-01")
day = lambda s: (pd.Timestamp(s) - EPOCH).days
s0 = pd.read_parquet("data/studies/predictability_diagnostic/stage0_matches.parquet",
                     columns=["match_id", "player_a_id", "player_b_id", "tournament_name", "round"])
tm = pd.read_parquet("data/studies/match_timing/timing.parquet", columns=["match_id", "es", "lf"])
s0 = s0.merge(tm, on="match_id")
g2 = {"atp|2021-580|Q2|atp:106045|atp:208013": ("atp:106045", "atp:208013"),
      "atp|2021-580|Q2|atp:106408|atp:202103": ("atp:106408", "atp:202103")}
play = day("2021-01-12")
for label, lf in [("as is", day("2021-01-15")), ("proposed fix", day("2020-12-18"))]:
    out = []
    for mid, pids in g2.items():
        r = s0[(s0["match_id"] != mid) & (s0["player_a_id"].isin(pids) | s0["player_b_id"].isin(pids))]
        r = r[(r["es"] >= lf + 1) & (r["es"] <= play)]
        out += [(mid, x.match_id, x.round, (EPOCH + pd.Timedelta(days=int(x.es))).date()) for x in r.itertuples()]
    print(f"{label}: {len(set(o[1] for o in out))} distinct early readers")
    for o in out:
        print("   ", o)
