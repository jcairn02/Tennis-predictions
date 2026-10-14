"""B3-referee, F8/F8b/F9/F10: recompute ages from birth dates and compare.

Read-only. Writes data/studies/input_data_audit/fixes/B3-referee/f8_*.csv, f9_*.csv, f10_*.csv, f8_f10_summary.json.

F8   the 12 Stage 0 rows with age > 90 (TML 2026 WTA, 8 June 2026): raw TML value, Sackmann dob of the player
     (through the F7 established id), the age TML's own convention gives ((date - dob).days / 365.25, 3 decimals), and
     whether the garbage is that age with its decimal point and the fraction's leading zero dropped.
F9   the 182 "inconsistent" rows of ATP Challengers dated 17 Aug 2020: Sackmann dob, age at the tournament date, the
     reference date the stored age implies, Sackmann's rounding convention (checked on other 2020 rows), and TML's age
     for the same match when TML holds it.
F10  the "impossible" rows (ages 11-12 and 61-76): dob, every Stage 0 row of the player, and whether the ages fit.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data/studies/input_data_audit/fixes/B3-referee"
S0 = ROOT / "data/studies/predictability_diagnostic"
AUDIT = ROOT / "data/studies/input_data_audit"

ALIAS = {"wta:315232": "wta:201548", "wta:320319": "wta:211713", "wta:324261": "wta:215035", "wta:330332": "wta:223253",
         "wta:322082": "wta:214082", "wta:328897": "wta:221236", "wta:328884": "wta:222391"}


def read(path) -> pd.DataFrame:
    t = pq.ParquetFile(path).read().to_pandas()
    return t.loc[:, ~t.columns.duplicated()]


def dob_table() -> pd.Series:
    out = []
    for tour in ("atp", "wta"):
        t = read(ROOT / f"data/dump/players/sackmann_archive/{tour}/{tour}_players.parquet")
        t["cid"] = tour + ":" + t.player_id.astype(str)
        t["dob_ts"] = pd.to_datetime(t.dob.astype(str), format="%Y%m%d", errors="coerce")
        out.append(t.set_index("cid").dob_ts)
    return pd.concat(out)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p = pd.read_parquet(S0 / "stage0_match_players.parquet",
                        columns=["match_id", "player_id", "opponent_id", "player_name", "age", "rank"])
    m = pd.read_parquet(S0 / "stage0_matches.parquet",
                        columns=["match_id", "tour", "level", "qualifying", "round", "tournament_id", "tournament_name",
                                 "tournament_date", "source", "source_file", "source_row"])
    d = p.merge(m, on="match_id")
    dob = dob_table()
    summary = {}

    # ---------------- F8 / F8b ----------------
    f8 = d[d.age > 90].copy()
    f8["established_id"] = f8.player_id.map(ALIAS)
    f8["sackmann_dob"] = f8.established_id.map(dob)
    days = (f8.tournament_date - f8.sackmann_dob).dt.days
    f8["age_from_dob"] = (days / 365.25).round(3)
    f8["garbage_decodes_to"] = f8.age.map(lambda a: float(f"{str(int(a))[:2]}.0{str(int(a))[2:]}"))
    f8["decode_matches_dob_age"] = (f8.garbage_decodes_to - f8.age_from_dob).abs() < 0.0015
    # the established id's own TML rows of the following weeks: do they use the same convention?
    est_rows = d[d.player_id.isin(f8.established_id) & d.source.eq("tml")].copy()
    est_rows["sackmann_dob"] = est_rows.player_id.map(dob)
    est_rows["age_from_dob"] = ((est_rows.tournament_date - est_rows.sackmann_dob).dt.days / 365.25).round(3)
    est_rows["agrees"] = (est_rows.age - est_rows.age_from_dob).abs() <= 0.0015
    summary["F8"] = {"rows_age_gt_90": int(len(f8)),
                     "decode_matches_dob_age": int(f8.decode_matches_dob_age.sum()),
                     "established_ids_tml_rows_checked": int(est_rows.age.notna().sum()),
                     "established_ids_tml_rows_agree_with_dob_convention": int(est_rows.agrees.sum()),
                     "disagreeing": est_rows[~est_rows.agrees & est_rows.age.notna()][
                         ["match_id", "player_name", "tournament_date", "age", "age_from_dob"]].astype(str).to_dict("records")}
    f8[["match_id", "player_id", "established_id", "player_name", "tournament_name", "tournament_date", "source_file",
        "source_row", "age", "sackmann_dob", "age_from_dob", "garbage_decodes_to", "decode_matches_dob_age"]].to_csv(
        OUT / "f8_rows.csv", index=False)

    # ---------------- F9 ----------------
    ages = pd.read_csv(AUDIT / "box_ages_oct07.csv")
    f9 = ages[ages.kind.str.startswith("inconsistent") & ages.tournament_date.eq("2020-08-17")].copy()
    f9 = f9.merge(d[["match_id", "player_id", "tournament_id", "tournament_name", "source_file", "source_row"]],
                  on=["match_id", "player_id"], how="left")
    f9["sackmann_dob"] = f9.player_id.map(dob)
    f9["age_at_date_exact"] = (pd.to_datetime(f9.tournament_date) - f9.sackmann_dob).dt.days / 365.25
    f9["implied_reference_date"] = f9.sackmann_dob + pd.to_timedelta(f9.age * 365.25, unit="D")
    # Sackmann's rounding convention, from the same players' other 2020 Sackmann rows
    other = d[d.player_id.isin(f9.player_id) & d.source.eq("sackmann") & d.tournament_date.dt.year.eq(2020)
              & ~d.match_id.isin(f9.match_id)].copy()
    other["dob"] = other.player_id.map(dob)
    other["exact"] = (other.tournament_date - other.dob).dt.days / 365.25
    conv = {"rows": int(other.age.notna().sum()),
            "equals_round_1dp": int((other.age - other.exact.round(1)).abs().lt(1e-9).sum()),
            "equals_floor_1dp": int((other.age - np.floor(other.exact * 10) / 10).abs().lt(1e-9).sum()),
            "within_0.05": int((other.age - other.exact).abs().le(0.0500001).sum())}
    f9["proposed_age_round_1dp"] = f9.age_at_date_exact.round(1)
    f9["proposed_age_floor_1dp"] = np.floor(f9.age_at_date_exact * 10) / 10
    # TML's age for the same match (TML 2020 challenger and qualifying files)
    tml = []
    for f in glob.glob(str(ROOT / "data/dump/matches/tennis_my_life/*/2020*.parquet")):
        t = read(f)
        tml.append(t[t.tourney_date.astype(str).eq("20200817")])
    tml = pd.concat(tml, ignore_index=True) if tml else pd.DataFrame()
    tml_names = {}
    if len(tml):
        for side in ("winner", "loser"):
            for r in tml[[f"{side}_name", f"{side}_age", "tourney_name", "round"]].itertuples(index=False):
                tml_names[(str(r[0]).lower(), str(r[3]))] = (r[1], r[2])
    f9["tml_age"] = [tml_names.get((str(n).lower(), str(mid).split("|")[2]), (np.nan, None))[0]
                     for n, mid in zip(f9.player_name, f9.match_id)]
    f9["tml_event"] = [tml_names.get((str(n).lower(), str(mid).split("|")[2]), (np.nan, None))[1]
                       for n, mid in zip(f9.player_name, f9.match_id)]
    f9["tml_age"] = pd.to_numeric(f9.tml_age, errors="coerce")
    summary["F9"] = {
        "rows": int(len(f9)), "events": f9.tournament_name.value_counts().to_dict(),
        "players": int(f9.player_id.nunique()), "rows_without_dob": int(f9.sackmann_dob.isna().sum()),
        "implied_reference_date_median": str(f9.implied_reference_date.median()),
        "implied_reference_date_iqr": [str(f9.implied_reference_date.quantile(.25)), str(f9.implied_reference_date.quantile(.75))],
        "stored_minus_exact_years": f9.age.sub(f9.age_at_date_exact).describe().round(3).to_dict(),
        "sackmann_rounding_on_other_2020_rows": conv,
        "tml_rows_found": int(f9.tml_age.notna().sum()),
        "tml_age_minus_exact_abs_max": float((f9.tml_age - f9.age_at_date_exact).abs().max()) if f9.tml_age.notna().any() else None,
    }
    f9.to_csv(OUT / "f9_rows.csv", index=False)

    # ---------------- F10 ----------------
    f10 = ages[ages.kind.eq("impossible") & ages.source.eq("sackmann")].copy()
    rows = []
    for pid, g in f10.groupby("player_id"):
        allr = d[d.player_id.eq(pid)].sort_values("tournament_date")
        b = dob.get(pid, pd.NaT)
        exact = (allr.tournament_date - b).dt.days / 365.25 if pd.notna(b) else pd.Series(np.nan, index=allr.index)
        rows.append({"player_id": pid, "player_name": g.player_name.iloc[0], "flagged_rows": len(g),
                     "flagged_ages": sorted(set(g.age)), "sackmann_dob": str(b.date()) if pd.notna(b) else None,
                     "all_stage0_rows": len(allr), "first": str(allr.tournament_date.min().date()),
                     "last": str(allr.tournament_date.max().date()),
                     "age_range_all_rows": [float(allr.age.min()), float(allr.age.max())] if allr.age.notna().any() else None,
                     "ages_fit_dob_within_0.1": int(((allr.age - exact).abs() <= 0.1).sum()),
                     "levels": allr.level.value_counts().to_dict(),
                     "ranks": [float(x) for x in allr["rank"].dropna().unique()[:6]]})
    summary["F10"] = rows
    pd.DataFrame(rows).to_csv(OUT / "f10_players.csv", index=False)

    (OUT / "f8_f10_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=1, default=str))
    print(f8[["player_name", "age", "sackmann_dob", "age_from_dob", "garbage_decodes_to", "decode_matches_dob_age"]].to_string())


if __name__ == "__main__":
    main()
