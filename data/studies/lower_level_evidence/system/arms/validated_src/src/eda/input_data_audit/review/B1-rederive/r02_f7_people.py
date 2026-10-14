"""B1-rederive reviewer: F7, who is behind each id (read-only).

For each of the 13 pairs:
  * exact name key (repair_data.name_key) and sorted-token key of the names on the new id;
  * every Sackmann player-file id of that tour with the same exact key / sorted key (dob, ioc);
  * every Stage 0 id (any source) with the same key;
  * the raw TML rows behind the new id (ids, names, ages, ioc), and TML's ATP database for atpcodes;
  * the established id's Sackmann player-file row (dob, ioc).
Writes f7_people.csv.
"""
from pathlib import Path
import re
import unicodedata

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B1-rederive"
S0 = ROOT / "data/studies/predictability_diagnostic"
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_colwidth", 80)


def name_key(value):
    if pd.isna(value):
        return ""
    s = unicodedata.normalize("NFKD", str(value)).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


def sorted_key(value):
    return " ".join(sorted(name_key(value).split()))


m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "tour", "tournament_date", "source",
                                                             "tournament_name", "source_file", "source_row"])
p = pd.read_parquet(S0 / "stage0_match_players.parquet", columns=["match_id", "player_id", "side", "player_name",
                                                                   "age", "country", "rank"])
q = p.merge(m, on="match_id")
q["key"] = q.player_name.map(name_key)
q["skey"] = q.player_name.map(sorted_key)

players = {}
for tour in ("atp", "wta"):
    d = pd.read_parquet(ROOT / f"data/dump/players/sackmann_archive/{tour}/{tour}_players.parquet")
    d["full"] = d.name_first.fillna("") + " " + d.name_last.fillna("")
    d["key"] = d.full.map(name_key)
    d["skey"] = d.full.map(sorted_key)
    d["pid"] = tour + ":" + d.player_id.astype(str)
    players[tour] = d
tml_atp = pd.read_parquet(ROOT / "data/dump/players/tennis_my_life/ATP_Database.parquet")
tml_atp["skey"] = tml_atp.player.map(sorted_key)

pairs = pd.read_csv(ROOT / "data/studies/input_data_audit/frame_split_ids_oct07.csv")
out = []
for r in pairs.itertuples():
    tour = r.tour
    newrows = q[q.player_id.eq(r.new_id)]
    estrows = q[q.player_id.eq(r.established_id)]
    keys = sorted(set(newrows.key))
    skeys = sorted(set(newrows.skey))
    pl = players[tour]
    same_exact = pl[pl.key.isin(keys)]
    same_sorted = pl[pl.skey.isin(skeys)]
    est_pl = pl[pl.pid.eq(r.established_id)]
    s0_ids_exact = sorted(set(q.loc[q.tour.eq(tour) & q.key.isin(keys), "player_id"]))
    s0_ids_sorted = sorted(set(q.loc[q.tour.eq(tour) & q.skey.isin(skeys), "player_id"]))
    s0_sack_ids_exact = sorted(set(q.loc[q.tour.eq(tour) & q.key.isin(keys) & q.source.eq("sackmann"), "player_id"]))
    s0_sack_ids_sorted = sorted(set(q.loc[q.tour.eq(tour) & q.skey.isin(skeys) & q.source.eq("sackmann"), "player_id"]))
    print("\n########", tour, keys, r.established_id, "->", r.new_id)
    print("  Sackmann player file, exact key:")
    print(same_exact[["pid", "full", "dob", "ioc", "hand", "height"]].to_string(index=False))
    if set(same_sorted.pid) != set(same_exact.pid):
        print("  Sackmann player file, sorted-token key:")
        print(same_sorted[["pid", "full", "dob", "ioc", "hand", "height"]].to_string(index=False))
    print("  established id player-file row:", est_pl[["pid", "full", "dob", "ioc"]].to_dict("records"))
    print("  Stage 0 ids with exact key:", s0_ids_exact, " Sackmann-sourced:", s0_sack_ids_exact)
    print("  Stage 0 ids with sorted key:", s0_ids_sorted, " Sackmann-sourced:", s0_sack_ids_sorted)
    # other Stage 0 Sackmann ids with the key: their spans
    for oid in sorted(set(s0_ids_sorted) - {r.established_id, r.new_id}):
        o = q[q.player_id.eq(oid)]
        print(f"   other id {oid}: {len(o)} rows {o.tournament_date.min()}..{o.tournament_date.max()} "
              f"names {sorted(set(o.player_name))} countries {sorted(set(o.country.dropna()))} "
              f"ages {o.age.min()}..{o.age.max()}")
    print("  raw source of new-id rows:")
    print(newrows[["match_id", "source", "source_file", "source_row", "player_name", "age", "country", "rank"]].to_string(index=False))
    if tour == "atp" and r.new_id.startswith("atpcode:"):
        code = r.new_id.split(":", 1)[1]
        t = tml_atp[tml_atp.id.eq(code) | tml_atp.skey.isin(skeys)]
        print("  TML ATP database rows (code or same sorted name):")
        print(t[["id", "player", "atpname", "birthdate", "ioc", "hand"]].to_string(index=False))
    out.append({"tour": tour, "established_id": r.established_id, "new_id": r.new_id,
                "exact_keys_new": "|".join(keys), "sorted_keys_new": "|".join(skeys),
                "sackmann_file_ids_exact": "|".join(same_exact.pid),
                "sackmann_file_ids_sorted": "|".join(same_sorted.pid),
                "sackmann_file_dobs_sorted": "|".join(same_sorted.dob.fillna("").astype(str)),
                "sackmann_file_ioc_sorted": "|".join(same_sorted.ioc.fillna("").astype(str)),
                "est_dob": "|".join(est_pl.dob.fillna("").astype(str)), "est_ioc": "|".join(est_pl.ioc.fillna("").astype(str)),
                "stage0_ids_exact": "|".join(s0_ids_exact), "stage0_ids_sorted": "|".join(s0_ids_sorted),
                "stage0_sackmann_ids_exact": "|".join(s0_sack_ids_exact),
                "stage0_sackmann_ids_sorted": "|".join(s0_sack_ids_sorted)})
pd.DataFrame(out).to_csv(OUT / "f7_people.csv", index=False)
