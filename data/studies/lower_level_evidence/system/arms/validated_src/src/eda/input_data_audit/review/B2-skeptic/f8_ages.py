"""B2-skeptic review of F8 / F8b (garbage ages on TML's 2026 WTA rows). Read-only.

1. The 12 rows with age > 100 in live Stage 0: the established birth date (Sackmann's player file, via the F7 identity),
   the age it gives at the tournament date ((date - dob) / 365.25, TML's own convention), and whether the garbage value
   decodes to it (integer part = first two digits).
2. TML's convention check: every TML WTA 2026 row whose player id has a Sackmann birth date: TML's age against
   (tournament_date - dob) / 365.25. Mismatches > 0.01 years are listed (other garbage or a different convention).

Writes data/studies/input_data_audit/fixes/B2-skeptic/f8_rows.csv (the scope with the recomputed ages) and
f8_tml_convention.csv.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B2-skeptic"
S0 = ROOT / "data/studies/predictability_diagnostic"


def main() -> None:
    pairs = pd.read_csv(ROOT / "data/studies/input_data_audit/frame_split_ids_oct07.csv")
    alias = dict(zip(pairs["new_id"], pairs["established_id"]))
    p = pd.read_parquet(S0 / "stage0_match_players.parquet", columns=["match_id", "player_id", "player_name", "side", "age"])
    m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "tournament_date", "tournament_name", "source",
                                                                "tour", "round"])
    d = p.merge(m, on="match_id")
    d["tournament_date"] = pd.to_datetime(d["tournament_date"])
    wp = pd.read_parquet(ROOT / "data/dump/players/sackmann_archive/wta/wta_players.parquet")
    ap = pd.read_parquet(ROOT / "data/dump/players/sackmann_archive/atp/atp_players.parquet")
    dob = pd.concat([wp.assign(t="wta"), ap.assign(t="atp")])
    dob["pid"] = dob["t"] + ":" + dob["player_id"].astype(str)
    dob = dob.set_index("pid")["dob"].astype(str)
    dob = pd.to_datetime(dob.where(dob.str.fullmatch(r"\d{8}")), format="%Y%m%d", errors="coerce")

    bad = d[d["age"].gt(100) | d["age"].lt(5)].copy()
    bad["established_id"] = bad["player_id"].map(alias)
    bad["dob"] = bad["established_id"].map(dob)
    bad["age_recomputed"] = ((bad["tournament_date"] - bad["dob"]).dt.days / 365.25).round(3)
    bad["garbage_int_part"] = (bad["age"] // 100).astype("Int64")
    bad["decodes"] = bad["garbage_int_part"].eq(np.floor(bad["age_recomputed"]).astype("Int64"))
    # TML's own age for the same player at the nearest other row (established id, TML source), for comparison
    cols = ["match_id", "player_id", "established_id", "player_name", "tournament_name", "tournament_date", "round",
            "source", "age", "dob", "age_recomputed", "garbage_int_part", "decodes"]
    bad = bad[cols].sort_values(["player_name", "round"])
    bad.to_csv(OUT / "f8_rows.csv", index=False)
    print(bad.to_string())

    t = d[d["source"].eq("tml") & d["tour"].eq("wta") & d["tournament_date"].ge("2026-01-01")].copy()
    t["canon"] = t["player_id"].map(lambda x: alias.get(x, x))
    t["dob"] = t["canon"].map(dob)
    t = t[t["dob"].notna() & t["age"].notna()]
    t["age_dob"] = (t["tournament_date"] - t["dob"]).dt.days / 365.25
    t["diff"] = t["age"] - t["age_dob"]
    print("TML WTA 2026 rows with a Sackmann dob and an age:", len(t))
    print("abs diff quantiles:", t["diff"].abs().quantile([.5, .9, .99, 1]).round(4).to_dict())
    off = t[t["diff"].abs().gt(0.01)].sort_values("diff")
    print("rows off by > 0.01 y:", len(off))
    print(off[["match_id", "player_id", "player_name", "tournament_name", "tournament_date", "age", "age_dob", "diff"]]
          .to_string(max_rows=60))
    off.to_csv(OUT / "f8_tml_convention.csv", index=False)


if __name__ == "__main__":
    main()
