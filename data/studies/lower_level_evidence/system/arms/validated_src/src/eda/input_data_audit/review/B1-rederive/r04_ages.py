"""B1-rederive reviewer: F8, F8b, F9, F10 ages, recomputed from Stage 0 and Sackmann's player files (read-only).

age_dob = (tournament_date - dob).days / 365.25 with dob from Sackmann's player file for the row's id
(for the F7 new ids, the established id's dob). Writes f8_*, f9_*, f10_* CSVs.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B1-rederive"
S0 = ROOT / "data/studies/predictability_diagnostic"
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 400)
pd.set_option("display.max_columns", 30)

m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "tour", "level", "qualifying", "round",
                                                             "tournament_id", "tournament_name", "tournament_date",
                                                             "source", "source_file", "source_row"])
p = pd.read_parquet(S0 / "stage0_match_players.parquet", columns=["match_id", "player_id", "side", "player_name",
                                                                   "age", "country", "rank"])
q = p.merge(m, on="match_id")
q["tdate"] = pd.to_datetime(q.tournament_date)

dob = []
for tour in ("atp", "wta"):
    d = pd.read_parquet(ROOT / f"data/dump/players/sackmann_archive/{tour}/{tour}_players.parquet",
                        columns=["player_id", "dob", "name_first", "name_last"])
    d["pid"] = tour + ":" + d.player_id.astype(str)
    dob.append(d)
dob = pd.concat(dob)
dob["dob_dt"] = pd.to_datetime(dob.dob.astype(str), format="%Y%m%d", errors="coerce")
dob = dob.drop_duplicates("pid").set_index("pid")

# F7 aliases (new id -> established id) to reach a dob for the new ids
pairs = pd.read_csv(ROOT / "data/studies/input_data_audit/frame_split_ids_oct07.csv")
alias = dict(zip(pairs.new_id, pairs.established_id))
q["dob_id"] = q.player_id.map(lambda x: alias.get(x, x))
q["dob_dt"] = q.dob_id.map(dob.dob_dt)
q["age_dob"] = (q.tdate - q.dob_dt).dt.days / 365.25
q["diff"] = q.age - q.age_dob

# Sackmann's rounding convention: compare age with floor/round of age_dob to 1 decimal
s = q[q.source.eq("sackmann") & q.age.notna() & q.age_dob.notna()].copy()
s["dec"] = (s.age * 10).round(6) % 1 != 0
print("Sackmann rows with age and dob:", len(s), " ages with more than 1 decimal:", int(s.dec.sum()))
one = s[~s.dec]
for name, f in (("floor", np.floor), ("round", np.round)):
    eq = np.isclose(one.age, f(one.age_dob * 10) / 10)
    print(f"  1-decimal ages equal to {name}(age_dob,1): {eq.mean():.4f}")
print("  |age - age_dob| <= 0.1:", float((s["diff"].abs() <= 0.1).mean()))
t = q[q.source.eq("tml") & q.age.notna() & q.age_dob.notna() & q.age.lt(100)].copy()
print("TML rows with age and dob:", len(t), " |age - age_dob| <= 0.01:", float((t["diff"].abs() <= 0.01).mean()),
      " equal to round(age_dob,3):", float(np.isclose(t.age, t.age_dob.round(3)).mean()))

# ---------------- F8: ages in the thousands
f8 = q[q.age.gt(100)].sort_values(["player_name", "match_id"])
f8 = f8.assign(dob=f8.dob_dt.dt.date, age_from_dob_3dp=f8.age_dob.round(3))
cols = ["match_id", "player_id", "side", "player_name", "tournament_name", "tournament_date", "level", "round",
        "source", "source_file", "source_row", "age", "dob_id", "dob", "age_from_dob_3dp"]
print("\nF8: rows with age > 100:", len(f8))
print(f8[cols].to_string(index=False))
f8[cols].to_csv(OUT / "f8_age_over_100.csv", index=False)
# the same players' other TML rows at the same event (their own correct ages, if any)
same_ev = q[q.dob_id.isin(f8.dob_id) & q.tournament_id.isin(f8.tournament_id) & q.age.lt(100)]
print("Same players, same events, age < 100:")
print(same_ev[["match_id", "player_name", "tournament_date", "age", "age_dob"]].to_string(index=False))

# ---------------- F10: ages < 13 or > 60 (not thousands)
f10 = q[(q.age.lt(13) | q.age.between(60, 100))].copy()
f10["dob"] = f10.dob_dt.dt.date
print("\nF10: rows with age < 13 or 60..100:", len(f10))
print(f10.groupby(["player_id", "player_name", "source", "dob"], dropna=False)
      .agg(n=("age", "size"), amin=("age", "min"), amax=("age", "max"), dmin=("diff", "min"), dmax=("diff", "max"),
           d0=("tournament_date", "min"), d1=("tournament_date", "max"), levels=("level", lambda z: "|".join(sorted(set(z)))))
      .to_string())
f10[["match_id", "player_id", "player_name", "tournament_name", "tournament_date", "level", "source", "source_row", "age",
     "dob", "age_dob"]].to_csv(OUT / "f10_extreme_ages.csv", index=False)
# their whole careers: age span and dob-consistency
for pid in sorted(set(f10.player_id)):
    y = q[q.player_id.eq(pid)]
    print(f"  {pid} {y.player_name.iloc[0]}: {len(y)} rows {y.tournament_date.min()}..{y.tournament_date.max()} "
          f"ages {y.age.min()}..{y.age.max()} dob {dob.dob.get(pid)} |diff|>0.2: {int(y['diff'].abs().gt(0.2).sum())} "
          f"levels {y.level.value_counts().to_dict()}")

# ---------------- F9: Sackmann rows inconsistent with the dob
bad = q[q["diff"].abs().gt(0.15) & q.age.lt(100) & q.age_dob.notna()].copy()
print("\nRows with |age - age_dob| > 0.15:", len(bad))
print(bad.groupby(["tour", "source", "level", "tournament_date"]).agg(n=("age", "size"), dmin=("diff", "min"),
      dmax=("diff", "max"), dmed=("diff", "median")).to_string())
aug = q[q.tdate.eq(pd.Timestamp("2020-08-17")) & q.tour.eq("atp")].copy()
print("\nATP rows dated 2020-08-17 by event:")
print(aug.groupby(["tournament_name", "level", "source"]).agg(n=("age", "size"), with_dob=("age_dob", "count"),
      off=("diff", lambda z: (z.abs() > 0.15).sum()), dmed=("diff", "median"), dmin=("diff", "min"), dmax=("diff", "max"))
      .to_string())
# implied date of the ages: tdate_implied = dob + age*365.25
aug["implied"] = aug.dob_dt + pd.to_timedelta(aug.age * 365.25, unit="D")
print("implied age date (dob + age), quantiles:", aug.implied.quantile([0, .05, .5, .95, 1]).dt.date.tolist())
f9 = aug[aug["diff"].abs().gt(0.15)].copy()
f9["age_fixed_1dp_floor"] = np.floor(f9.age_dob * 10) / 10
f9 = f9.assign(dob=f9.dob_dt.dt.date)
f9[["match_id", "player_id", "side", "player_name", "tournament_name", "tournament_date", "level", "round", "source",
    "source_file", "source_row", "age", "dob", "age_dob", "diff", "age_fixed_1dp_floor"]].to_csv(OUT / "f9_aug2020.csv", index=False)
print("F9 rows (|diff| > 0.15) on 2020-08-17:", len(f9), " players without dob on that date:",
      int(aug.age_dob.isna().sum()), " rows with age but no dob:", int((aug.age.notna() & aug.age_dob.isna()).sum()))
# neighbouring weeks
for d in ["2020-03-02", "2020-03-09", "2020-08-10", "2020-08-17", "2020-08-24", "2020-08-31", "2020-09-07"]:
    y = q[q.tdate.eq(pd.Timestamp(d)) & q.tour.eq("atp") & q.age_dob.notna() & q.age.notna()]
    print(d, "rows", len(y), "median diff", round(y["diff"].median(), 3) if len(y) else None,
          "share |diff|>0.15:", round(y["diff"].abs().gt(0.15).mean(), 3) if len(y) else None,
          "levels", y.level.value_counts().to_dict())
