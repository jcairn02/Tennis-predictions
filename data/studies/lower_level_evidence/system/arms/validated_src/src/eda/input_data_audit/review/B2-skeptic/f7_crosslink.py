"""B2-skeptic review of F7, second pass: independent identity links for the 13 split pairs. Read-only.

WTA pairs: TML's 2026 WTA rows carry the WTA's own player id. The WTA API match list (data/dump/points/wta/matches.parquet)
gives, per WTA id, the matches it played. A WTA-API match is "shared" with the established Sackmann id when Stage 0 holds a
match of the established id within 10 days of the WTA-API match time against an opponent with the same surname key.
ATP pairs: TML's age (three decimals, (tourney_date - dob) / 365.25) gives the birth date to the day; it is compared with
Sackmann's player file. Ranking continuity: Sackmann's last ranking of the established id against TML's 31 Aug 2026 ranking.

Writes data/studies/input_data_audit/fixes/B2-skeptic/f7_crosslink.csv and f7_dob_check.csv.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B2-skeptic"
S0 = ROOT / "data/studies/predictability_diagnostic"


def ascii_lower(s) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()


def surname_key(name) -> str:
    words = re.findall(r"[a-z]+", ascii_lower(name))
    return words[-1] if words else ""


def main() -> None:
    pairs = pd.read_csv(ROOT / "data/studies/input_data_audit/frame_split_ids_oct07.csv")
    p = pd.read_parquet(S0 / "stage0_match_players.parquet",
                        columns=["match_id", "player_id", "opponent_id", "player_name", "age"])
    m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "tournament_date", "tournament_name"])
    d = p.merge(m, on="match_id")
    d["tournament_date"] = pd.to_datetime(d["tournament_date"])
    names = d.drop_duplicates("player_id").set_index("player_id")["player_name"]
    d["opp_name"] = d["opponent_id"].map(names)
    w = pq.ParquetFile(ROOT / "data/dump/points/wta/matches.parquet").read().to_pandas()
    w = w.loc[:, ~w.columns.duplicated()]
    w["t"] = pd.to_datetime(w["MatchTimeStamp"], errors="coerce", utc=True, format="ISO8601").dt.tz_localize(None)
    rows = []
    for r in pairs[pairs["tour"].eq("wta")].itertuples():
        wid = r.new_id.split(":")[1]
        est = d[d["player_id"].eq(r.established_id)]
        for side, other in (("A", "B"), ("B", "A")):
            x = w[w["PlayerID" + side].astype(str).eq(wid)]
            for y in x.itertuples():
                opp_last = surname_key(getattr(y, "PlayerNameLast" + other))
                cand = est[(est["tournament_date"] - y.t).abs().le(pd.Timedelta(days=10))
                           & est["opp_name"].map(surname_key).eq(opp_last)]
                rows.append({"name_key": r.name_key, "new_id": r.new_id, "established_id": r.established_id,
                             "wta_tournament": y.tournament_id, "wta_year": y.year, "wta_match": y.match_id,
                             "wta_time": y.t, "wta_name": f"{getattr(y, 'PlayerNameFirst' + side)} {getattr(y, 'PlayerNameLast' + side)}",
                             "wta_country": getattr(y, "PlayerCountry" + side),
                             "opponent": f"{getattr(y, 'PlayerNameFirst' + other)} {getattr(y, 'PlayerNameLast' + other)}",
                             "shared_with_established": len(cand) > 0,
                             "established_match": cand["match_id"].iloc[0] if len(cand) else None})
    x = pd.DataFrame(rows)
    x.to_csv(OUT / "f7_crosslink.csv", index=False)
    summ = x.groupby(["name_key", "new_id", "established_id"]).agg(
        wta_api_matches=("wta_match", "size"), shared=("shared_with_established", "sum"),
        countries=("wta_country", lambda s: ",".join(sorted(set(map(str, s)))))).reset_index()
    print(summ.to_string())
    # birth dates
    a = pd.read_parquet(ROOT / "data/dump/players/sackmann_archive/atp/atp_players.parquet")
    wp = pd.read_parquet(ROOT / "data/dump/players/sackmann_archive/wta/wta_players.parquet")
    dob = pd.concat([a.assign(tour="atp"), wp.assign(tour="wta")])
    dob["pid"] = dob["tour"] + ":" + dob["player_id"].astype(str)
    dob = dob.set_index("pid")["dob"]
    out = []
    for r in pairs.itertuples():
        for pid in [r.established_id, r.new_id]:
            for z in d[d["player_id"].eq(pid)].itertuples():
                if pd.isna(z.age) or z.age > 100 or z.age < 5:
                    implied = None
                else:
                    implied = (z.tournament_date - pd.Timedelta(days=float(z.age) * 365.25)).date()
                out.append({"name_key": r.name_key, "id": pid, "role": "new" if pid == r.new_id else "established",
                            "match_id": z.match_id, "tournament_date": z.tournament_date.date(), "age": z.age,
                            "implied_dob": implied, "sackmann_dob_established": dob.get(r.established_id)})
    o = pd.DataFrame(out)
    o = o[o["role"].eq("new")]
    o.to_csv(OUT / "f7_dob_check.csv", index=False)
    print(o.to_string())
    # other Sackmann ids with the same dob and name (O'Connell, Munk Mesa)
    for pid in ["atp:206736", "atp:213206", "atp:210458", "atp:212827"]:
        print(pid, "dob", dob.get(pid))


if __name__ == "__main__":
    main()
