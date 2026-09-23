"""Inspect research snapshots with explicitly selected ufc-ag pandas/pyarrow.

No downloads, installations, or production-file changes. Writes public/table_audit.json.
"""
import collections
import csv
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/studies/tennis_data_audit/public"
RAW = OUT / "raw"
START, END = pd.Timestamp("2025-09-10", tz="UTC"), pd.Timestamp("2026-09-11", tz="UTC")


def missing(frame):
    return {c: int(frame[c].isna().sum()) for c in frame.columns}


def date_summary(series):
    dates = pd.to_datetime(series, errors="coerce", utc=True, format="mixed")
    return {"min": str(dates.min()), "max": str(dates.max()), "invalid": int(dates.isna().sum()),
            "requested_window_rows": int(((dates >= START) & (dates < END)).sum())}


def public_index():
    m = pd.read_csv(RAW / "zenodo_matches.csv.gz", dtype={"tier_key":"string", "tournament_key":"string", "is_qualifying":"string"}, low_memory=False)
    players = pd.read_csv(RAW / "zenodo_players.csv.gz")
    points = pd.read_csv(RAW / "zenodo_points_sample_2026-06.csv.gz", low_memory=False)
    result = {"matches": {"rows": len(m), "columns": list(m.columns), "missing": missing(m),
                           "scheduled_time": date_summary(m.scheduled_time_utc),
                           "duplicate_ids": int(m.match_id.duplicated().sum()),
                           "self_matches": int((m.player1_id == m.player2_id).sum()),
                           "qualifying": m.is_qualifying.fillna("missing").value_counts(dropna=False).to_dict(),
                           "tiers": m.tier_key.fillna("missing").value_counts(dropna=False).to_dict(),
                           "event_status": m.event_status.value_counts(dropna=False).to_dict(),
                           "tier_round_examples": m.groupby("tier_key")["round"].agg(lambda a: sorted(set(a.dropna()))[:6]).to_dict()},
              "players": {"rows": len(players), "missing": missing(players), "duplicate_ids": int(players.player_id.duplicated().sum()),
                          "duplicate_nonempty_sackmann_ids": int(players.sackmann_id.dropna().duplicated().sum())}}
    used = set(m.player1_id) | set(m.player2_id)
    lookup = players.set_index("player_id")
    result["matches"]["distinct_players"] = len(used)
    result["matches"]["missing_player_foreign_keys"] = len(used - set(players.player_id))
    result["matches"]["used_players_with_sackmann_id"] = int(lookup.loc[sorted(used)].sackmann_id.notna().sum())
    result["matches"]["both_players_have_sackmann_id"] = int((m.player1_id.map(lookup.sackmann_id).notna() & m.player2_id.map(lookup.sackmann_id).notna()).sum())
    result["matches"]["tier_surface_missing"] = m.groupby("tier_key")["surface"].agg(lambda a: int(a.isna().sum())).to_dict()
    t = pd.to_datetime(points.timestamp_utc, utc=True, format="mixed")
    group = points.groupby("match_id", sort=False)
    starts, ends = group.head(1), group.tail(1)
    counts = group.size()
    state_cols = [c for c in points.columns if c not in ("match_id", "timestamp_utc")]
    same_match = points.match_id.eq(points.match_id.shift())
    same_state = points[state_cols].fillna("missing").eq(points[state_cols].shift().fillna("missing")).all(axis=1) & same_match
    delta = t.groupby(points.match_id).diff().dt.total_seconds()
    indexed = set(m.match_id)
    pp = {"rows": len(points), "distinct_matches": int(points.match_id.nunique()), "missing": missing(points),
          "capture_time": date_summary(points.timestamp_utc), "unjoined_match_ids": len(set(points.match_id) - indexed),
          "negative_capture_time_steps": int((delta < 0).sum()), "zero_capture_time_steps": int((delta == 0).sum()),
          "consecutive_identical_states": int(same_state.sum()),
          "capture_gap_over_5_minutes": int((delta > 300).sum()), "capture_gap_over_30_minutes": int((delta > 1800).sum()),
          "row_count_per_match": {str(k): float(v) for k,v in counts.quantile([0,.25,.5,.75,1]).items()},
          "start_sets_zero": int(((starts.sets_p1 == 0) & (starts.sets_p2 == 0)).sum()),
          "start_empty_game_arrays": int(((starts.games_p1 == "[]") & (starts.games_p2 == "[]")).sum()),
          "end_someone_has_2_sets": int(((ends.sets_p1 >= 2) | (ends.sets_p2 >= 2)).sum())}
    joined = ends.merge(m[["match_id", "best_of", "tier_key"]], on="match_id", how="left")
    required = joined.best_of.map({"BO3":2,"BO5":3})
    pp["end_reaches_declared_best_of_win_sets"] = int(((joined.sets_p1 >= required) | (joined.sets_p2 >= required)).sum())
    pp["matches_per_tier"] = joined.tier_key.fillna("missing").value_counts(dropna=False).to_dict()
    result["points_sample"] = pp
    return result


def open_tennis():
    df = pd.read_parquet(RAW / "open_tennis_completed.parquet")
    coverage = pd.read_parquet(RAW / "open_tennis_coverage.parquet")
    quarantine = pd.read_parquet(RAW / "open_tennis_quarantine.parquet")
    health = pd.read_parquet(RAW / "open_tennis_health.parquet")
    provenance = pd.read_parquet(RAW / "open_tennis_provenance.parquet")
    for name, table in (("coverage",coverage),("quarantine",quarantine),("health",health)):
        table.to_json(OUT / f"open_tennis_{name}_records.json",orient="records",indent=2,date_format="iso")
    return {"rows": len(df), "columns": list(df.columns), "dates": date_summary(df.date), "missing": missing(df),
            "tour_year": [{"tour": k[0], "year": int(k[1]), "rows": int(v)} for k,v in df.groupby(["tour","year"]).size().items()],
            "duplicate_ids": int(df.match_id.duplicated().sum()), "status": df.status.value_counts(dropna=False).to_dict(),
            "round": df["round"].value_counts(dropna=False).to_dict(), "quarantine_columns": list(quarantine.columns),
            "quarantine_rows": len(quarantine), "provenance_columns": list(provenance.columns),
            "provenance_missing": missing(provenance), "sources": collections.Counter(s for sources in df.source for s in sources)}


def tennis_data():
    audits = []
    files = sorted(RAW.glob("tennis_data_*.xlsx")) + sorted((ROOT / "data/raw/tennis_data_couk").glob("*/*.xlsx"))
    for path in files:
        df = pd.read_excel(path)
        date = pd.to_datetime(df.Date, errors="coerce")
        cols = [c for c in df if c.startswith(("B365", "PS", "BFE", "Max", "Avg"))]
        audit = {"file": str(path.relative_to(ROOT)), "freshness": "downloaded this audit" if path.parent == RAW else "pre-existing local snapshot; not refreshed", "rows": len(df), "columns": list(df.columns), "dates": date_summary(df.Date),
                 "missing": missing(df), "comments": df.Comment.value_counts(dropna=False).to_dict(),
                 "duplicate_date_pair": int(df.duplicated(["Date","Winner","Loser"]).sum()),
                 "duplicate_full_rows": int(df.duplicated().sum()), "odds_nonempty": {c:int(df[c].notna().sum()) for c in cols},
                 "odds_last_observed_date": {c:str(date[df[c].notna()].max()) for c in cols}}
        audit["odds_pair_availability"] = {}
        for prefix in ("B365", "PS", "BFE", "Max", "Avg"):
            pair = [prefix + "W", prefix + "L"]
            if all(c in df for c in pair):
                present = df[pair].notna()
                numeric = df[pair].apply(pd.to_numeric, errors="coerce")
                audit["odds_pair_availability"][prefix] = {
                    "both_present": int(present.all(axis=1).sum()),
                    "one_sided": int((present.sum(axis=1) == 1).sum()),
                    "both_missing": int((~present.any(axis=1)).sum()),
                    "explicit_zero_cells": int((numeric == 0).sum().sum()),
                    "decimal_odds_at_or_below_one_cells": int((numeric <= 1).sum().sum())}
        audits.append(audit)
    return audits


def sackmann_anomalies():
    results = []
    for path in sorted(RAW.glob("*matches*202[456].csv")):
        df = pd.read_csv(path, low_memory=False)
        if "winner_id" not in df:
            continue
        checks = {}
        for side in ("w", "l"):
            for left, right in (("1stWon","1stIn"),("1stIn","svpt"),("bpSaved","bpFaced")):
                a,b = f"{side}_{left}",f"{side}_{right}"
                checks[f"{a}_greater_than_{b}"] = int((df[a] > df[b]).sum())
            checks[f"{side}_2ndWon_exceeds_second_serves"] = int((df[f"{side}_2ndWon"] > df[f"{side}_svpt"]-df[f"{side}_1stIn"]).sum())
        results.append({"file":path.name, "stat_arithmetic":checks})
    for path in sorted(RAW.glob("mcp_*_matches.csv")):
        with path.open(encoding="utf-8-sig",newline="") as f:
            rows = list(csv.reader(f))
        bad = [{"line": i+2,"column_count":len(row),"raw":row} for i,row in enumerate(rows[1:]) if len(row) != len(rows[0])]
        results.append({"file":path.name,"invalid_width":len(bad),"examples":bad[:6]})
    return results


def main():
    result = {"interpreter": "C:/Users/zerom/miniforge3/envs/ufc-ag/python.exe",
              "zenodo": public_index(), "open_tennis": open_tennis(), "tennis_data": tennis_data(),
              "sackmann_anomalies": sackmann_anomalies()}
    (OUT / "table_audit.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"zenodo":result["zenodo"], "tennis_data":result["tennis_data"],
                      "open_tennis":{k:v for k,v in result["open_tennis"].items() if k not in ("columns","missing","provenance_columns","provenance_missing")}}, indent=2,default=str))


if __name__ == "__main__":
    main()
