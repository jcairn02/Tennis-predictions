"""Round 0, body-and-schedule brainstormer: value sets of the categorical columns the ideas use.

No outcome column (a_won, won) is read. Seasons up to 2024 only.
Run: ./python.sh src/eda/feature_interactions/round0/body/categories.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
S0 = ROOT / "data/studies/predictability_diagnostic"

MCOLS = ["match_id", "tour", "year", "level", "qualifying", "evaluation", "round", "round_order",
         "surface", "indoor", "best_of", "draw_size", "tournament_id", "tournament_name",
         "tournament_date", "status", "status_detail", "minutes", "format"]
PCOLS = ["match_id", "player_id", "entry", "country", "hand", "height", "age", "seed"]


def main() -> None:
    m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=MCOLS)
    m = m[m["year"] <= 2024]
    print("rows <=2024:", len(m))
    for col in ["tour", "level", "round", "status", "surface", "best_of", "format"]:
        print(f"\n== {col}")
        print(m[col].value_counts(dropna=False).head(40).to_string())
    print("\n== status_detail (top 30)")
    print(m["status_detail"].value_counts(dropna=False).head(30).to_string())
    main_tour = m[m["level"].isin(["G", "F", "M", "A", "P", "PM", "I", "W", "WTA1000", "WTA500", "WTA250"])]
    print("\nlevel values again, evaluation only:")
    print(m.loc[m["evaluation"], ["tour", "level"]].value_counts().to_string())
    p = pd.read_parquet(S0 / "stage0_match_players.parquet", columns=PCOLS)
    p = p[p["match_id"].isin(m["match_id"])]
    print("\n== entry")
    print(p["entry"].value_counts(dropna=False).head(30).to_string())
    print("\n== hand")
    print(p["hand"].value_counts(dropna=False).to_string())
    print("\nnon-missing shares: country", p["country"].notna().mean().round(4),
          "height", p["height"].notna().mean().round(4), "age", p["age"].notna().mean().round(4),
          "seed", p["seed"].notna().mean().round(4))


if __name__ == "__main__":
    main()
