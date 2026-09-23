"""Career-coverage study, step 1: draw the player sample.

Question: for players who compete on the ATP Challenger Tour, how much of their whole career is in
the staged public dump, and how much in-match statistics does it carry?

Population: players ranked 1-700 in the latest ATP ranking in the dump (Tennis My Life snapshot of
2026-08-31) with at least 5 Challenger main-draw matches in the 52 weeks to that date (Tennis My
Life Challenger files), born 1994 or later so a career can fall inside the dump's 2010+ window.
Stratified by rank band, two players per band, drawn with a fixed seed; two reserves per band
replace a pick whose ATP activity starts before 2010.

Reads data/dump read-only; writes data/studies/career_coverage/sample.json.
Run: ./python.sh src/eda/career_coverage/select_players.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DUMP = ROOT / "data" / "dump"
OUT = ROOT / "data" / "studies" / "career_coverage"
SEED = 20260923
RANKING_FILE = "rankings/tennis_my_life/atp_rankings_2026-08-31.parquet"
WINDOW = ("20250901", "20260831")  # tournament weeks counted as the last 52 weeks
MIN_CHALLENGER_MATCHES = 5
MIN_BIRTH_YEAR = 1994
BANDS = [(1, 100), (101, 200), (201, 300), (301, 450), (451, 700)]
PER_BAND, RESERVES = 2, 2


def main():
    rk = pd.read_parquet(DUMP / RANKING_FILE, columns=["playerId", "rank", "points"])
    rk["rank"] = rk["rank"].astype(int)
    db = pd.read_parquet(DUMP / "players/tennis_my_life/ATP_Database.parquet",
                         columns=["id", "player", "birthdate", "ioc"]).drop_duplicates("id")
    files = [DUMP / "matches/tennis_my_life/atp_challenger/2025_challenger.parquet",
             DUMP / "matches/tennis_my_life/atp_challenger/2026_challenger.parquet",
             DUMP / "matches/tennis_my_life/ongoing/challenger_ongoing_tourneys.parquet"]
    ch = pd.concat([pd.read_parquet(f, columns=["tourney_date", "winner_id", "loser_id"]) for f in files])
    ch = ch[ch["tourney_date"].between(*WINDOW)]
    apps = pd.concat([ch["winner_id"], ch["loser_id"]]).value_counts().rename("challenger_matches_52w")

    p = rk.merge(db, left_on="playerId", right_on="id", how="left").merge(apps, left_on="playerId",
                                                                          right_index=True, how="left")
    p["challenger_matches_52w"] = p["challenger_matches_52w"].fillna(0).astype(int)
    p["birth_year"] = pd.to_numeric(p["birthdate"].str[:4], errors="coerce")
    eligible = p[(p["challenger_matches_52w"] >= MIN_CHALLENGER_MATCHES) & (p["birth_year"] >= MIN_BIRTH_YEAR)]

    rng = np.random.default_rng(SEED)
    bands, picks = [], []
    for lo, hi in BANDS:
        pool = eligible[eligible["rank"].between(lo, hi)].sort_values("playerId")
        order = rng.permutation(len(pool))[:PER_BAND + RESERVES]
        drawn = pool.iloc[order]
        bands.append({"band": f"{lo}-{hi}", "ranked_players": int(p["rank"].between(lo, hi).sum()),
                      "eligible": len(pool)})
        for i, (_, r) in enumerate(drawn.iterrows()):
            picks.append({"band": f"{lo}-{hi}", "draw_order": i + 1, "role": "pick" if i < PER_BAND else "reserve",
                          "atp_code": r["playerId"], "name": r["player"], "rank_2026_08_31": int(r["rank"]),
                          "points": int(r["points"]), "birthdate": r["birthdate"], "ioc": r["ioc"],
                          "challenger_matches_52w": int(r["challenger_matches_52w"])})

    OUT.mkdir(parents=True, exist_ok=True)
    result = {"seed": SEED, "ranking_file": RANKING_FILE, "challenger_window_tourney_weeks": WINDOW,
              "min_challenger_main_draw_matches": MIN_CHALLENGER_MATCHES, "min_birth_year": MIN_BIRTH_YEAR,
              "bands": bands, "draws": picks}
    (OUT / "sample.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(pd.DataFrame(bands).to_string(index=False))
    print(pd.DataFrame(picks).to_string(index=False))


if __name__ == "__main__":
    main()
