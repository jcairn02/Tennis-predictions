# Counting script of the feature-provenance study (8 Oct 2026), written by the session's data-availability
# audit and copied here with its output folder moved to data/studies/feature_provenance/counts/.
# Counts only: no result column is read for any match after 28 Jul 2026.
"""Slam qualifying: Stage 0's tournament_date is the main draw's week, so link with a wider window (-14..+7 days).
No label column is read. Run from the repo root: ./python.sh <this file>"""
import re
import unicodedata
import pandas as pd


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", "", s.replace("-", " ")).strip()


def full(s):
    return norm(s).replace(" ", "")


m = pd.read_parquet("data/studies/predictability_diagnostic/stage0_matches.parquet",
                    columns=["match_id", "tour", "year", "level", "qualifying", "status", "tournament_date", "has_box"])
m = m[(m["level"] == "GS") & m["qualifying"] & (m["year"] >= 2024) & m["status"].isin(["completed", "retired"])].copy()
p = pd.read_parquet("data/studies/predictability_diagnostic/stage0_match_players.parquet", columns=["match_id", "side", "player_name"])
p = p[p["match_id"].isin(m["match_id"])]
nm = p.pivot(index="match_id", columns="side", values="player_name")
m["k"] = [tuple(sorted((full(nm.at[i, "A"]), full(nm.at[i, "B"])))) for i in m["match_id"]]

bo = pd.read_parquet("data/dump/odds/oddstrader/betonline_matches.parquet",
                     columns=["eid", "dt_utc", "home_first", "home_last", "away_first", "away_last", "mw_close_home", "mw_close_uncertain"])
bo["day"] = pd.to_datetime(bo["dt_utc"]).dt.tz_localize(None).dt.normalize()
bo["k"] = [tuple(sorted((full(f"{a} {b}"), full(f"{c} {d}")))) for a, b, c, d in
           zip(bo["home_first"], bo["home_last"], bo["away_first"], bo["away_last"])]
bo = bo[bo["mw_close_home"].notna() & ~bo["mw_close_uncertain"]]
pm = pd.read_parquet("data/studies/sharp_benchmark/pm_markets.parquet", columns=["name_a", "name_b", "start_ts", "status", "has_close"])
pm["day"] = pd.to_datetime(pm["start_ts"], unit="s").dt.normalize()
pm["k"] = [tuple(sorted((full(a), full(b)))) for a, b in zip(pm["name_a"], pm["name_b"])]
pm = pm[pm["status"].eq("decisive") & pm["has_close"]]


def has(ext):
    j = m[["match_id", "k", "tournament_date"]].merge(ext[["k", "day"]], on="k")
    g = (j["day"] - j["tournament_date"]).dt.days
    return set(j.loc[(g >= -14) & (g <= 7), "match_id"])


m["bo"], m["pm"] = m["match_id"].isin(has(bo)), m["match_id"].isin(has(pm))
print(m.groupby(["tour", "year"]).agg(n=("match_id", "size"), box=("has_box", "sum"), betonline=("bo", "sum"),
                                      polymarket=("pm", "sum")).to_string())
