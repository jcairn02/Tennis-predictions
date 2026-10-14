"""B1 rhythm-and-body scout: outcome-free prevalence and coverage for the memo's lead ideas.

Reads NO result: no a_won / won / winner / score / sets / box-score numerators, of any season.
Reads ids, dates, levels, rounds, entries, statuses (completed/retired/walkover), minutes, clock days and clock times.
2025-26 rows are counted (coverage only), never related to a result.

Parts
  A  men's main-tour doubles participation at the same event, 2013-2020 (Sackmann ATP doubles, ids)
  B  doubles matches in the 7 / 2 days before a frame match, both tours, 2018-2026 (TennisLive listings, names ->
     Stage 0 ids through lower_level_evidence's TennisLive crosswalk)
  C  rest in hours before each frame match (previous played match at any level; clock times from the match-timing
     link files; end = Flashscore end_utc, else start + Stage 0 minutes), and the two players' rest gap
  D  entry types in the frame (qualifiers, lucky losers) and the qualifiers' hours since their previous match
  E  exhibitions in the Flashscore records (counts only)
Writes prevalence.json and prints tables. Run:
  ./python.sh data/studies/unpriced_leads/team/rhythm_body/prevalence.py > data/studies/unpriced_leads/team/rhythm_body/prevalence.txt
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
S = ROOT / "data" / "studies"
DUMP = ROOT / "data" / "dump"
L = S / "match_timing" / "links"
OUT = Path(__file__).resolve().parent
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 300)
res: dict = {}

# ------------------------------------------------------------------ shared tables (no outcomes)
frame = pd.read_parquet(S / "current_best_model/template_2026-10-10/model_frame.parquet",
                        columns=["match_id", "tour", "season"])
s0 = pd.read_parquet(S / "predictability_diagnostic/stage0_matches.parquet",
                     columns=["match_id", "tour", "year", "level", "qualifying", "round", "round_order",
                              "tournament_id", "tournament_name", "tournament_date", "status", "minutes", "draw_size",
                              "player_a_id", "player_b_id"])
tm = pd.read_parquet(S / "match_timing/timing.parquet", columns=["match_id", "obs", "es", "lf"])
mp = pd.read_parquet(S / "predictability_diagnostic/stage0_match_players.parquet",
                     columns=["match_id", "player_id", "side", "entry", "seed", "player_name"])
fr = frame.merge(s0[["match_id", "level", "round", "tournament_id", "tournament_date", "draw_size",
                     "player_a_id", "player_b_id"]], on="match_id", how="left").merge(tm, on="match_id", how="left")
print("frame rows", len(fr))

# ------------------------------------------------------------------ A: Sackmann ATP doubles, event participation
dbl = []
for y in range(2013, 2021):
    d = pd.read_parquet(DUMP / f"matches/sackmann_archive/atp/atp_matches_doubles_{y}.parquet",
                        columns=["tourney_id", "tourney_level", "round", "winner1_id", "winner2_id", "loser1_id", "loser2_id"])
    d["tid"] = d["tourney_id"].astype(str).str.replace(r"-0+(\d)", r"-\1", regex=True)
    for c in ["winner1_id", "winner2_id", "loser1_id", "loser2_id"]:
        dbl.append(pd.DataFrame({"tid": d["tid"], "pid": "atp:" + d[c].astype(str).str.replace(r"\.0$", "", regex=True)}))
dbl = pd.concat(dbl).drop_duplicates()
dset = set(zip(dbl["tid"], dbl["pid"]))
men = fr[(fr["tour"] == "atp") & fr["season"].between(2013, 2020)].copy()
men["a_dbl"] = [(t, p) in dset for t, p in zip(men["tournament_id"], men["player_a_id"])]
men["b_dbl"] = [(t, p) in dset for t, p in zip(men["tournament_id"], men["player_b_id"])]
men["any_dbl"] = men["a_dbl"] | men["b_dbl"]
men["one_dbl"] = men["a_dbl"] ^ men["b_dbl"]
tA = men.groupby("level")[["a_dbl", "any_dbl", "one_dbl"]].mean().round(3)
tA["n"] = men.groupby("level").size()
print("\nA. men 2013-2020: share of frame matches where player A / either / exactly one is in the same event's doubles draw")
print(tA)
print("by season:", men.groupby("season")["any_dbl"].mean().round(3).to_dict())
res["A_men_doubles_event_2013_2020"] = {"by_level": tA.reset_index().to_dict("records"),
                                        "by_season_any": men.groupby("season")["any_dbl"].mean().round(4).to_dict()}

# ------------------------------------------------------------------ B: TennisLive doubles 2018-2026, by name
def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z ]", " ", s).split())


xw = pd.read_csv(S / "lower_level_evidence/system/stage0/C0_now/evidence/crosswalk_tennislive.csv")
xw["tour"] = xw["src"].str.split("|").str[0]
xw["key"] = xw["tour"] + "|" + xw["src_name"].map(norm)
amb = xw["key"].duplicated(keep=False)
name2id = dict(zip(xw.loc[~amb, "key"], xw.loc[~amb, "s0"]))
tl = pd.read_parquet(DUMP / "points/tennislive/listed.parquet",
                     columns=["tour", "discipline", "event_kind", "played", "state", "start_utc", "player1_members", "player2_members"])
tl = tl[tl["discipline"] == "doubles"].copy()
tl["day"] = (pd.to_datetime(tl["start_utc"], errors="coerce").dt.normalize() - pd.Timestamp("1970-01-01")).dt.days
print("\nB. TennisLive doubles rows", len(tl), "played values", tl["played"].value_counts().head(4).to_dict(),
      "state", tl["state"].value_counts().head(5).to_dict())
rows = []
for side in ["player1_members", "player2_members"]:
    parts = tl[side].fillna("").str.split(" / ", expand=True)
    for k in range(min(2, parts.shape[1])):
        rows.append(pd.DataFrame({"tour": tl["tour"].values, "day": tl["day"].values, "nm": parts[k].values}))
dp = pd.concat(rows)
dp = dp[dp["nm"].notna() & (dp["nm"] != "")]
dp["pid"] = (dp["tour"] + "|" + dp["nm"].map(norm)).map(name2id)
print("doubles member-rows", len(dp), "mapped to a Stage 0 id:", round(dp["pid"].notna().mean(), 3))
dp = dp.dropna(subset=["pid", "day"])
dp["day"] = dp["day"].astype(int)
byp = {p: np.sort(g["day"].to_numpy()) for p, g in dp.groupby("pid")}


def count_window(pid, day, lo, hi):
    """Doubles matches of player pid on days day-lo .. day-hi (inclusive)."""
    a = byp.get(pid)
    if a is None or not np.isfinite(day):
        return 0
    return int(np.searchsorted(a, day - hi, side="right") - np.searchsorted(a, day - lo, side="left"))


b = fr[fr["season"] >= 2018].copy()
for s, col in [("a", "player_a_id"), ("b", "player_b_id")]:
    b[f"d7_{s}"] = [count_window(p, d, 7, 1) for p, d in zip(b[col], b["obs"])]
    b[f"d2_{s}"] = [count_window(p, d, 2, 1) for p, d in zip(b[col], b["obs"])]
    b[f"d0_{s}"] = [count_window(p, d, 0, 0) for p, d in zip(b[col], b["obs"])]
b["any7"] = (b["d7_a"] > 0) | (b["d7_b"] > 0)
b["diff7"] = (b["d7_a"] > 0) ^ (b["d7_b"] > 0)
b["any2"] = (b["d2_a"] > 0) | (b["d2_b"] > 0)
b["same_day"] = (b["d0_a"] > 0) | (b["d0_b"] > 0)
tB = b.groupby(["tour", "level"])[["any7", "diff7", "any2", "same_day"]].mean().round(3)
tB["n"] = b.groupby(["tour", "level"]).size()
print("\nB. 2018-2026 frame matches: share where either player played doubles in the 7 days before (days -7..-1),"
      " exactly one did, either in days -2..-1, or a doubles match the same day")
print(tB)
tBs = b.groupby(["tour", "season"])[["any7", "diff7", "any2"]].mean().round(3)
tBs["n"] = b.groupby(["tour", "season"]).size()
print(tBs)
res["B_doubles_2018_2026"] = {"by_tour_level": tB.reset_index().to_dict("records"),
                              "by_tour_season": tBs.reset_index().to_dict("records")}

# ------------------------------------------------------------------ C: rest in hours
times = []
fsr = pd.read_parquet(L / "flashscore_records.parquet", columns=["fs_match_id", "end_utc"])
fl = pd.read_parquet(L / "flashscore.parquet", columns=["match_id", "source_key", "start_utc"])
fl = fl.merge(fsr, left_on="source_key", right_on="fs_match_id", how="left")
fl["src"] = "flashscore"
times.append(fl[["match_id", "start_utc", "end_utc", "src"]])
for f in ["sofascore", "live_tennis_api", "api_tennis", "wta_api", "slam_feeds", "tdi", "match_charting"]:
    d = pd.read_parquet(L / f"{f}.parquet", columns=["match_id", "start_utc"])
    d["end_utc"] = pd.NaT
    d["src"] = f
    times.append(d)
tt = pd.concat(times, ignore_index=True)
tt["t0"] = pd.to_datetime(tt["start_utc"], errors="coerce", utc=True)
tt["t1"] = pd.to_datetime(tt["end_utc"], errors="coerce", utc=True)
tt = tt[tt["t0"].notna() & ((tt["t0"].dt.hour != 0) | (tt["t0"].dt.minute != 0))]
tt = tt.drop_duplicates("match_id", keep="first")   # flashscore first, then the order above
seq = mp[["match_id", "player_id", "entry"]].merge(
    s0[["match_id", "level", "qualifying", "round_order", "tournament_id", "tournament_date", "status", "minutes"]],
    on="match_id").merge(tm[["match_id", "obs"]], on="match_id").merge(tt[["match_id", "t0", "t1"]], on="match_id", how="left")
seq = seq[seq["status"].isin(["completed", "retired"])].copy()
seq = seq.sort_values(["player_id", "obs", "tournament_date", "round_order", "t0"])
seq["dur_fs"] = (seq["t1"] - seq["t0"]).dt.total_seconds() / 60
EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
t0m = (seq["t0"] - EPOCH).dt.total_seconds() / 60      # minutes since the epoch (the link files are datetime64[ms])
t1m = (seq["t1"] - EPOCH).dt.total_seconds() / 60
seq["end"] = np.where(seq["dur_fs"].between(15, 420), t1m, np.nan)
alt = t0m + seq["minutes"]
seq["end"] = seq["end"].where(seq["end"].notna(), alt.where(seq["t0"].notna() & seq["minutes"].between(15, 420)))
seq["start_min"] = t0m
seq["prev_end"] = seq.groupby("player_id")["end"].shift(1)
seq["prev_obs"] = seq.groupby("player_id")["obs"].shift(1)
seq["prev_level"] = seq.groupby("player_id")["level"].shift(1)
seq["prev_q"] = seq.groupby("player_id")["qualifying"].shift(1)
seq["rest_h"] = (seq["start_min"] - seq["prev_end"]) / 60
seq.loc[~seq["rest_h"].between(0.25, 24 * 60), "rest_h"] = np.nan
seq["rest_d"] = seq["obs"] - seq["prev_obs"]
c = fr[["match_id", "tour", "season", "level", "player_a_id", "player_b_id"]].copy()
for s, col in [("a", "player_a_id"), ("b", "player_b_id")]:
    m = seq[["match_id", "player_id", "rest_h", "rest_d", "prev_level", "prev_q", "entry"]].rename(
        columns={"player_id": col, "rest_h": f"rh_{s}", "rest_d": f"rd_{s}", "prev_level": f"pl_{s}", "prev_q": f"pq_{s}",
                 "entry": f"en_{s}"})
    c = c.merge(m, on=["match_id", col], how="left")
c["both_h"] = c["rh_a"].notna() & c["rh_b"].notna()
c["short_any"] = (c["rh_a"] < 20) | (c["rh_b"] < 20)
c["short_one"] = (c["rh_a"] < 20) ^ (c["rh_b"] < 20)
both72 = c["both_h"] & (c["rh_a"] < 72) & (c["rh_b"] < 72)
c["gap12"] = both72 & ((c["rh_a"] - c["rh_b"]).abs() >= 12)
c["sameday_gap12"] = both72 & ((c["rh_a"] - c["rh_b"]).abs() >= 12) & (c["rd_a"] == c["rd_b"])
c["both72"] = both72
tC = c.groupby(["tour", "season"]).agg(n=("match_id", "size"), both_hours=("both_h", "mean"), both_lt72h=("both72", "mean"),
                                       short_any=("short_any", "mean"), short_one=("short_one", "mean"),
                                       gap12=("gap12", "mean"), gap12_same_days=("sameday_gap12", "mean")).round(3)
print("\nC. rest in hours: share of frame matches with both players' rest in hours; both under 72 h; any / exactly one"
      " under 20 h; rest gap of 12 h or more (both under 72 h); the same, with equal rest in days")
print(tC)
rh = pd.concat([c["rh_a"], c["rh_b"]]).dropna()
print("rest-hours quantiles (all player-matches with hours):", rh.quantile([.01, .05, .1, .25, .5]).round(1).to_dict())
lt72 = rh[rh < 72]
print("within 72 h: n", len(lt72), "share < 16 h", round((lt72 < 16).mean(), 3), "< 20 h", round((lt72 < 20).mean(), 3),
      "< 24 h", round((lt72 < 24).mean(), 3))
gap = (c.loc[both72, "rh_a"] - c.loc[both72, "rh_b"]).abs()
print("rest gap (both < 72 h) quantiles:", gap.quantile([.5, .75, .9, .95]).round(1).to_dict())
res["C_rest_hours"] = {"by_tour_season": tC.reset_index().to_dict("records"),
                       "rest_h_quantiles": rh.quantile([.01, .05, .1, .25, .5]).round(2).to_dict(),
                       "within72_share_lt20": float((lt72 < 20).mean()), "gap_quantiles": gap.quantile([.5, .75, .9, .95]).round(2).to_dict()}

# ------------------------------------------------------------------ D: qualifiers and lucky losers
for s in ["a", "b"]:
    c[f"q_{s}"] = c[f"en_{s}"].isin(["Q", "LL"])
c["q_any"] = c["q_a"] | c["q_b"]
tD = c.groupby(["tour", "level"]).agg(n=("match_id", "size"), q_any=("q_any", "mean")).round(3)
print("\nD. share of frame matches with a qualifier or lucky loser")
print(tD)
qh = pd.concat([c.loc[c["q_a"], "rh_a"], c.loc[c["q_b"], "rh_b"]]).dropna()
print("qualifier/LL rest-hours quantiles:", qh.quantile([.1, .25, .5, .75]).round(1).to_dict(), "n", len(qh))
res["D_qualifiers"] = {"by_tour_level": tD.reset_index().to_dict("records"),
                       "q_rest_h_quantiles": qh.quantile([.1, .25, .5, .75]).round(2).to_dict()}

# ------------------------------------------------------------------ E: exhibitions in Flashscore
ex = pd.read_parquet(L / "flashscore_records.parquet", columns=["start_utc", "is_exhibition", "tournament_name", "gender"])
ex = ex[ex["is_exhibition"] == True]  # noqa: E712
ex["y"] = pd.to_datetime(ex["start_utc"], errors="coerce", utc=True).dt.year
print("\nE. Flashscore exhibition records by year:", ex["y"].value_counts().sort_index().to_dict())
print(ex["tournament_name"].value_counts().head(30).to_string())
res["E_exhibitions"] = {"by_year": {int(k): int(v) for k, v in ex["y"].value_counts().sort_index().items() if pd.notna(k)},
                        "top_names": ex["tournament_name"].value_counts().head(30).to_dict()}

(OUT / "prevalence.json").write_text(json.dumps(res, indent=1, default=str))
print("\nwrote", OUT / "prevalence.json")

# scratch per-match values for the outcome-free novelty check (novelty.py); no result column
feat = c[["match_id", "rh_a", "rh_b", "rd_a", "rd_b", "q_a", "q_b"]].merge(
    b[["match_id", "d7_a", "d7_b", "d2_a", "d2_b"]], on="match_id", how="left")
feat.to_parquet(OUT / "scratch_features.parquet", index=False)
print("wrote", OUT / "scratch_features.parquet", len(feat))
