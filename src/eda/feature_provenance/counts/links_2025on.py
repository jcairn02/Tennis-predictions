# Counting script of the feature-provenance study (8 Oct 2026), written by the session's data-availability
# audit and copied here with its output folder moved to data/studies/feature_provenance/counts/.
# Counts only: no result column is read for any match after 28 Jul 2026.
"""Q1/Q3: link Stage 0 matches (Sep 2025 on) to Polymarket markets and BetOnline lines by player-name pair
and date window. Approximate, for counting coverage only. No label column (a_won, won, y0, winner) is read.
Run from the repo root: ./python.sh <this file>
"""
import re
import unicodedata
import numpy as np
import pandas as pd

SCR = "data/studies/feature_provenance/counts/"
S0 = "data/studies/predictability_diagnostic/stage0_matches.parquet"
S0P = "data/studies/predictability_diagnostic/stage0_match_players.parquet"


def norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", "", s.replace("-", " ")).strip()


def full(s):
    return norm(s).replace(" ", "")


def last(s):
    t = norm(s).split()
    return t[-1] if t else ""


m = pd.read_parquet(S0, columns=["match_id", "tour", "year", "level", "qualifying", "status", "tournament_date",
                                 "tournament_name", "has_box"])
m = m[m["tournament_date"] >= "2025-08-15"].copy()
p = pd.read_parquet(S0P, columns=["match_id", "side", "player_name"])          # 'won' deliberately not read
p = p[p["match_id"].isin(m["match_id"])]
a = p[p["side"] == "A"].set_index("match_id")["player_name"]
b = p[p["side"] == "B"].set_index("match_id")["player_name"]
m["na"], m["nb"] = m["match_id"].map(a), m["match_id"].map(b)
m["kfull"] = [tuple(sorted((full(x), full(y)))) for x, y in zip(m["na"], m["nb"])]
m["klast"] = [tuple(sorted((last(x), last(y)))) for x, y in zip(m["na"], m["nb"])]
m["tier"] = np.where(m["qualifying"], "Q:" + m["level"], m["level"])


def link(m, ext, day_col, lo=-3, hi=21):
    """ext must have columns ext_id, kfull, klast, day (date). Returns match_id -> ext_id (unique, nearest)."""
    out = {}
    used = set()
    for key in ("kfull", "klast"):
        j = m[~m["match_id"].isin(list(out))][["match_id", key, "tournament_date"]].merge(
            ext[["ext_id", key, day_col]], on=key)
        j = j[~j["ext_id"].isin(used)]
        gap = (j[day_col] - j["tournament_date"]).dt.days
        j = j[(gap >= lo) & (gap <= hi)].assign(gap=gap.abs())
        j = j.sort_values("gap").drop_duplicates("match_id").drop_duplicates("ext_id")
        out.update(dict(zip(j["match_id"], j["ext_id"])))
        used |= set(j["ext_id"])
    return out


# ---- Polymarket (sharp-benchmark market table: Sep 2025 - Oct 2026). y0/outcomes not read.
pm = pd.read_parquet("data/studies/sharp_benchmark/pm_markets.parquet",
                     columns=["condition_id", "event_type", "name_a", "name_b", "start_ts", "status", "has_close",
                              "p0_m1440", "p0_m30", "volume"])
pm["day"] = pd.to_datetime(pm["start_ts"], unit="s").dt.normalize()
pm["kfull"] = [tuple(sorted((full(x), full(y)))) for x, y in zip(pm["name_a"], pm["name_b"])]
pm["klast"] = [tuple(sorted((last(x), last(y)))) for x, y in zip(pm["name_a"], pm["name_b"])]
pm = pm[pm["status"].eq("decisive") & ~pm["event_type"].isin(["juniors", "team_exhib"])].rename(columns={"condition_id": "ext_id"})
lk = link(m, pm, "day")
m["pm"] = m["match_id"].map(lk)
pmx = pm.set_index("ext_id")
m["pm_close"] = m["pm"].map(pmx["has_close"]).fillna(False).astype(bool)
m["pm_24h"] = m["pm"].map(pmx["p0_m1440"]).notna()
print("Polymarket decisive markets used:", len(pm), "| linked to Stage 0:", len(lk))
print("Polymarket decisive markets by type and month (all, linked or not):")
pm["month"] = pm["day"].dt.strftime("%Y-%m")
print(pd.crosstab(pm["event_type"], pm["month"]).to_string())
um = pm[~pm["ext_id"].isin(set(lk.values()))]
print("\nUNLINKED Polymarket markets by type and month:")
print(pd.crosstab(um["event_type"], um["month"]).to_string())

# ---- BetOnline (OddsTrader), main tour and qualifying
bo = pd.read_parquet("data/dump/odds/oddstrader/betonline_matches.parquet",
                     columns=["eid", "tour", "group", "es", "dt_utc", "home_first", "home_last", "away_first",
                              "away_last", "mw_open_home", "mw_close_home", "mw_close_uncertain"])
bo["day"] = pd.to_datetime(bo["dt_utc"]).dt.tz_localize(None).dt.normalize()
bo["kfull"] = [tuple(sorted((full(f"{a} {b}"), full(f"{c} {d}")))) for a, b, c, d in
               zip(bo["home_first"], bo["home_last"], bo["away_first"], bo["away_last"])]
bo["klast"] = [tuple(sorted((last(b), last(d)))) for b, d in zip(bo["home_last"], bo["away_last"])]
bo = bo.rename(columns={"eid": "ext_id"})
lk2 = link(m, bo, "day")
m["bo"] = m["match_id"].map(lk2)
box = bo.set_index("ext_id")
m["bo_close"] = m["bo"].map(box["mw_close_home"]).notna() & ~m["bo"].map(box["mw_close_uncertain"]).fillna(True).astype(bool)
m["bo_open"] = m["bo"].map(box["mw_open_home"]).notna()
print("\nBetOnline singles rows:", len(bo), "| linked to Stage 0 (Aug 2025 on):", len(lk2))

m["month"] = m["tournament_date"].dt.strftime("%Y-%m")
ev = m[m["status"].isin(["completed", "retired"])]
m.drop(columns=["kfull", "klast"]).to_parquet(SCR + "links_stage0_2025on.parquet", index=False)

MAIN = ["GS", "FIN", "T1000", "T500", "T250"]
post = ev[ev["level"].isin(MAIN) & ~ev["qualifying"] & (ev["tournament_date"] > "2026-07-28")]
print("\n== POST-FRAME main-tour main draws (completed+retired):", len(post))
print(post.groupby(["tour", "month"]).agg(n=("match_id", "size"), pm_close=("pm_close", "sum"), pm_24h=("pm_24h", "sum"),
                                          bo_close=("bo_close", "sum"), bo_open=("bo_open", "sum")).to_string())
print(post.groupby("tour")[["pm_close", "pm_24h", "bo_close", "bo_open"]].sum().to_string())

print("\n== Stage 0 matches (completed+retired) Sep 2025 on, by tier: with a Polymarket close / BetOnline close, and box")
ev2 = ev[ev["tournament_date"] >= "2025-09-01"].copy()
ev2["yr"] = ev2["tournament_date"].dt.year
print(ev2.groupby(["tour", "tier", "yr"]).agg(n=("match_id", "size"), box=("has_box", "sum"), pm_close=("pm_close", "sum"),
      pm_close_and_box=("pm_close", lambda x: int((x & ev2.loc[x.index, "has_box"]).sum())),
      bo_close=("bo_close", "sum")).to_string())
