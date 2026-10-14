"""B3-referee: the scope files of the confirmed rows, one CSV per candidate, from the live (7 Oct) tables.

Read-only on the repo; writes data/studies/input_data_audit/fixes/B3-referee/scope_*.csv.

scope_F7.csv     Stage 0 rows of the 11 confirmed new ids: field (player_id on stage0_match_players, opponent_id on the
                 opponent's row, player_a_id / player_b_id on stage0_matches), match_id, side, old id, new id
scope_F8.csv     the 12 age rows: match_id, player_id (as stored), age stored, F8 value (blank), F8b value
scope_F9.csv     the 182 age rows: match_id, player_id, age stored, Sackmann dob, recomputed age (floor to 0.1, Sackmann's
                 convention) and the unrounded age
scope_F11.csv    Stage 1 rows: match_id, td_file, td_row, which pairs to exchange, stored and corrected values
scope_F12.csv    the Nottingham 2017 final: every price pair exchanged
scope_F14.csv    key-statistic records with y_raw >= spd_max - 1 (tier strict / equal / within1), identity as in
                 speed_records.parquet; scope_F15.csv the 14 men's >= 240 records (a subset)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B3-referee"
S0 = ROOT / "data/studies/predictability_diagnostic"
SP = ROOT / "data/studies/serve_speed_tabpfn"

F7 = {"wta:315232": "wta:201548", "wta:320319": "wta:211713", "wta:324261": "wta:215035", "wta:330332": "wta:223253",
      "wta:322082": "wta:214082", "wta:328897": "wta:221236", "wta:328884": "wta:222391", "wta:332718": "wta:260765",
      "wta:321837": "wta:215386", "atpcode:M0VL": "atp:149128", "atpcode:C0UQ": "atp:214346"}


def dobs() -> pd.Series:
    out = []
    for tour in ("atp", "wta"):
        t = pq.ParquetFile(ROOT / f"data/dump/players/sackmann_archive/{tour}/{tour}_players.parquet").read().to_pandas()
        t["cid"] = tour + ":" + t.player_id.astype(str)
        out.append(t.set_index("cid")["dob"].pipe(lambda s: pd.to_datetime(s.astype(str), format="%Y%m%d", errors="coerce")))
    return pd.concat(out)


def main() -> None:
    p = pd.read_parquet(S0 / "stage0_match_players.parquet", columns=["match_id", "side", "player_id", "opponent_id", "age"])
    m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "player_a_id", "player_b_id", "tournament_date"])
    # F7
    rows = []
    for col in ("player_id", "opponent_id"):
        x = p[p[col].isin(F7)]
        rows += [{"table": "stage0_match_players", "field": col, "match_id": r.match_id, "side": r.side,
                  "old_id": getattr(r, col), "new_id": F7[getattr(r, col)]} for r in x.itertuples()]
    for col in ("player_a_id", "player_b_id"):
        x = m[m[col].isin(F7)]
        rows += [{"table": "stage0_matches", "field": col, "match_id": r.match_id, "side": col[7].upper(),
                  "old_id": getattr(r, col), "new_id": F7[getattr(r, col)]} for r in x.itertuples()]
    pd.DataFrame(rows).sort_values(["old_id", "match_id", "table", "field"]).to_csv(OUT / "scope_F7.csv", index=False)

    dob = dobs()
    # F8 / F8b
    f8 = pd.read_csv(OUT / "f8_rows.csv")
    f8["F8_value"] = np.nan
    f8["F8b_value"] = f8["age_from_dob"]
    f8[["match_id", "player_id", "established_id", "player_name", "tournament_date", "source_file", "source_row", "age",
        "sackmann_dob", "F8_value", "F8b_value"]].rename(columns={"age": "age_stored"}).to_csv(OUT / "scope_F8.csv", index=False)
    # F9
    f9 = pd.read_csv(OUT / "f9_rows.csv")
    f9["sackmann_dob"] = pd.to_datetime(f9["sackmann_dob"])
    exact = (pd.to_datetime(f9["tournament_date"]) - f9["sackmann_dob"]).dt.days / 365.25
    f9["age_exact"] = exact.round(4)
    f9["age_new_floor_1dp"] = np.floor(exact * 10 + 1e-9) / 10
    mid = f9["sackmann_dob"] + pd.to_timedelta((f9["age"] + 0.05) * 365.25, unit="D")
    print("F9 implied reference date of the stored ages (floor convention, midpoint): median", mid.median())
    f9[["match_id", "player_id", "player_name", "tournament_name", "tournament_date", "source_file", "source_row", "age",
        "sackmann_dob", "age_exact", "age_new_floor_1dp"]].rename(columns={"age": "age_stored"}).to_csv(
        OUT / "scope_F9.csv", index=False)
    # F11 / F12
    s1 = pd.read_parquet(S0 / "stage1_odds.parquet")
    spec = [("atp|2013-891|SF|atp:104386|atp:105379", True, False, "Chennai 2013 SF: Avg and Max reversed vs 5 books"),
            ("atp|2016-540|F|atp:104918|atp:105683", True, False, "Wimbledon 2016 F: Avg and Max reversed vs 4 books"),
            ("wta|2022-2030|R32|wta:201603|wta:216146", False, False, "Adelaide 2 2022 R32: Avg reversed; stored Avg above Max"),
            ("wta|2025-822|F|wta:210722|wta:211817", False, False, "'s-Hertogenbosch 2025 F: Avg reversed; stored Avg above Max")]
    out = []
    for mid_, with_max, _, why in spec:
        a = s1[s1.match_id.eq(mid_)].iloc[0]
        out.append({"match_id": mid_, "td_file": a.td_file, "td_row": int(a.td_row), "link": a.link,
                    "exchange_avg": True, "exchange_max": with_max, "exchange_ps": False, "exchange_b365": False,
                    "avg_a_stored": a.avg_a, "avg_b_stored": a.avg_b, "max_a_stored": a.max_a, "max_b_stored": a.max_b,
                    "p_avg_a_stored": a.p_avg_a, "avg_a_new": a.avg_b, "avg_b_new": a.avg_a,
                    "max_a_new": a.max_b if with_max else a.max_a, "max_b_new": a.max_a if with_max else a.max_b,
                    "p_avg_a_new": 1 - a.p_avg_a, "note": why})
    pd.DataFrame(out).to_csv(OUT / "scope_F11.csv", index=False)
    a = s1[s1.match_id.eq("wta|2017-1080|F|wta:202427|wta:202499")].iloc[0]
    pd.DataFrame([{"match_id": a.match_id, "td_file": a.td_file, "td_row": int(a.td_row), "link": a.link,
                   "exchange_avg": True, "exchange_max": True, "exchange_ps": True, "exchange_b365": True,
                   "avg_a_stored": a.avg_a, "avg_b_stored": a.avg_b, "p_avg_a_stored": a.p_avg_a,
                   "avg_a_new": a.avg_b, "avg_b_new": a.avg_a, "max_a_new": a.max_b, "max_b_new": a.max_a,
                   "ps_a_new": a.ps_b, "ps_b_new": a.ps_a, "b365_a_new": a.b365_b, "b365_b_new": a.b365_a,
                   "p_avg_a_new": 1 - a.p_avg_a,
                   "note": "tennis-data names swapped: W columns (rank 75, sets 2-6 7-6 7-5, prices) are Vekic's"}]).to_csv(
        OUT / "scope_F12.csv", index=False)
    # F14 / F15
    rec = pd.read_parquet(SP / "speed_records.parquet")
    pan = pd.read_parquet(SP / "speed_panel.parquet", columns=["match_id", "side", "source", "source_key", "use"])
    k = rec[rec["kind"].eq("keystat") & rec["spd_max"].notna() & (rec["y_raw"] >= rec["spd_max"] - 1)].copy()
    k["tier"] = np.select([k.y_raw > k.spd_max, k.y_raw == k.spd_max], ["strict", "equal"], "within1")
    k = k.merge(pan.rename(columns={"use": "panel_use_row"}), on=["match_id", "side", "source", "source_key"], how="left")
    k["panel_use_row"] = k["panel_use_row"].fillna(False).astype(bool)
    cols = ["match_id", "side", "source", "source_key", "tier", "y_raw", "spd_max", "n", "spd2_raw", "valid",
            "invalid_reason", "panel_use_row", "tour_s0", "year_s0", "level_s0", "round_s0"]
    k[cols].sort_values(["tier", "match_id", "side", "source"]).to_csv(OUT / "scope_F14.csv", index=False)
    f15 = k[k["tour_s0"].eq("atp") & (k["y_raw"] - 0.5 >= 240)]
    f15[cols].to_csv(OUT / "scope_F15.csv", index=False)
    print("F7 rows", len(rows), "| F8", len(f8), "| F9", len(f9), "| F14", len(k), k["tier"].value_counts().to_dict(),
          "use rows", int(k["panel_use_row"].sum()), "| F15", len(f15), "use rows", int(f15["panel_use_row"].sum()))


if __name__ == "__main__":
    main()
