"""Serve-speed acquisition (decision of 7 Oct 2026): per-player match speeds from the two new sources, linked to
Stage 0, and the checks that they are right. Reads no match result.

Sources
    infosys_slams  data/dump/points/infosys_slams/: the AO's and RG's Infosys match-centre files, decrypted (AO 2025,
                   RG 2025, RG 2026). From MatchBeats points, per player: the mean speed of first serves in (points
                   played on the first serve with a timed speed) and their number, the same for second serves, the
                   speed of first-serve faults and the fastest serve. From RG's key statistics ("set0" = the match):
                   "1st Serve Average Speed", "2nd Serve Average Speed", "Max Speed", "First Serve" (in / total).
    mantennisdata  data/raw/public_dump/mantennisdata/atp/matches_2021-2026.csv: the ATP Stats Centre's key statistics
                   as atptour.com shows them: first- and second-serve averages, the maximum, first serves in.
    infosys_atp    data/dump/points/infosys_atp/: the ATP Stats Centre's own Infosys files of 2018 to 17 Oct 2021,
                   decrypted on 8 Oct 2026 (src/ingest/point_sources/infosys_atp_stage.py). From MatchBeats points and
                   the key statistics as for the Slam files, with the ATP files' double-fault codes ("P" and "DF") left
                   out of the second-serve mean. Every planned match is a row, timed or not (only the 2018 ATP Finals
                   and Washington, San Diego and Indian Wells 2021 carry speeds).
A speed outside 40-270 km/h counts as missing (the shot-level adapters' rule).

Linking: shot_level.common.Stage0Linker (surname pair, tournament date, round, draw). The Slams take Stage 0's own
tournament date for the edition and draw; ManTennisData takes its tournaments.csv start_dtm. The ATP files take the
live speed pipeline's linker (serve_speed_tabpfn/live/link.py: ATP codes through its crosswalk; the id Stage 0 would
give, else the event's match of the same pair, else the names), with each code's round from ManTennisData's stats link.

Checks (observed; checks.json):
    1 sirgenkii_points   SirGenkii's rally analysis (decrypted ATP Stats Centre files, held) for its 14 AO 2025 men's
                         first-round matches, joined to MatchBeats point by point on the point id
    2 ao_match_centre    the AO match centre's plain match "1st Serve Average" (held Wayback captures of AO 2025)
                         against the MatchBeats mean of first serves in, oriented by surname
    3 rg_keystats        RG's own key statistic against the mean of first serves in from the same file's points
    4 flashscore         Flashscore's "Average 1st serve speed" (held handoff crawl) on linked matches, unoriented, as
                         serve_speed_sources/flashscore_crawl.py
    5 mantd_vs_infosys   ManTennisData against the held decrypted ATP key statistics, matched by year, tournament and
                         match code: SirGenkii (Jan-Apr 2025, by player) and the Hugging Face handoff (2021-24,
                         unoriented); and the matches that carry speed in one and not the other
    6 continuity         each player's mean speed of first serves in at the same Slam in consecutive years, paired by
                         player: the held point-based copies to 2024 (shot_level/stage1_match_stats.parquet), the
                         decrypted files from 2025. A change of measuring system would show as a jump in the median
                         change between two years that ordinary year-to-year changes do not show

Run: ./python.sh src/eda/serve_speed_acquisition/speeds.py   (a few minutes)
Writes data/studies/serve_speed_acquisition/: speeds.parquet (one row per player and source match), checks.json,
links.json
"""
from __future__ import annotations

import gzip
import json
import multiprocessing as mp
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as PD  # noqa: E402
from src.eda.serve_speed_sources import coverage as CV  # noqa: E402
from src.eda.serve_speed_sources import flashscore_crawl as FC  # noqa: E402

OUT = ROOT / "data" / "studies" / "serve_speed_acquisition"
INFO = ROOT / "data" / "dump" / "points" / "infosys_slams"
ATP = ROOT / "data" / "dump" / "points" / "infosys_atp"
MANTD = ROOT / "data" / "raw" / "public_dump" / "mantennisdata" / "atp"
MANTD_STAGED = ROOT / "data" / "dump" / "matches" / "mantennisdata"
SIRG = ROOT / "data" / "dump" / "points" / "sirgenkii_infotennis"
AO_DUMP = ROOT / "data" / "dump" / "points" / "ausopen"
SHOT_STATS = ROOT / "data" / "studies" / "shot_level" / "stage1_match_stats.parquet"
HANDOFF = CV.HANDOFF
FS_LINK = CV.FS_LINK
MANTD_YEARS = range(2021, 2027)
LO, HI = 40.0, 270.0
KS = {"1st Serve Average Speed": "ks_spd1", "2nd Serve Average Speed": "ks_spd2", "Max Speed": "ks_max",
      "First Serve": "ks_first"}
ATP_KS = {**{k: v for k, v in KS.items() if k != "First Serve"}, "1st Serve": "ks_first"}   # the ATP files' label
ATP_DOUBLE_FAULTS = ("P", "DF")       # MatchBeats ends an ATP double fault with "P" (2018-20, most of 2021) or "DF"
STATS_URL = re.compile(r"/archive/(\d{4})/(\d+)/([a-z]{2}\d{3})", re.I)
FIRST_SERVE = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")
COLUMNS = ["source", "basis", "event", "year", "tour", "draw", "round", "source_key", "player_no", "player_name",
           "player_source_id", "match_id", "side", "spd1_mean", "spd1_n", "spd2_mean", "spd2_n", "fault1_mean",
           "fault1_n", "spd_max", "service_points", "ks_spd1", "ks_spd2", "ks_max", "ks_first_in", "ks_first_total"]
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def speed(values) -> pd.Series:
    """km/h as floats; anything outside 40-270 km/h (including Infosys's 0 for "not timed") is missing."""
    x = pd.to_numeric(pd.Series(values), errors="coerce")
    return x.where((x > LO) & (x <= HI))


def full_name(first, last, fallback) -> str:
    first, last = (str(v).strip() if isinstance(v, str) else "" for v in (first, last))
    return f"{first} {last}".strip() if first and last else (fallback or "")


# ------------------------------------------------------------------------------------------------
# the Infosys Slam files
# ------------------------------------------------------------------------------------------------
def infosys_matches() -> pd.DataFrame:
    m = pd.read_parquet(INFO / "matches.parquet")
    m = m[m["files"].astype(int) > 0].copy()
    m["year"] = m["year"].astype(int)
    return m


def infosys_points() -> pd.DataFrame:
    p = pd.read_parquet(INFO / "points.parquet", columns=["slam", "year", "match_id", "pointId", "server", "serve",
                                                          "serveSpeed", "faultSrvSpd"])
    p["year"] = p["year"].astype(int)
    p["spd"] = speed(p["serveSpeed"]).to_numpy()
    p["fault"] = speed(p["faultSrvSpd"]).to_numpy()
    return p


def point_speeds(p: pd.DataFrame) -> pd.DataFrame:
    """Per match and server: first serves in (points played on the first serve, timed), second serves, first-serve
    faults, the fastest timed serve and the service points."""
    p = p.assign(s1=p["spd"].where(p["serve"].eq("1")), s2=p["spd"].where(p["serve"].eq("2")),
                 f1=p["fault"].where(p["serve"].eq("2")))
    g = p.groupby(["slam", "year", "match_id", "server"])
    out = g.agg(service_points=("serve", "size"), spd1_n=("s1", "count"), spd1_mean=("s1", "mean"),
                spd2_n=("s2", "count"), spd2_mean=("s2", "mean"), fault1_n=("f1", "count"),
                fault1_mean=("f1", "mean"), spd_max=("spd", "max")).reset_index()
    out = out[out["server"].isin(["1", "2"])]
    return out.rename(columns={"server": "player_no"})


def key_stats() -> pd.DataFrame:
    """RG's key statistics of the match ("set0"), one row per match and player."""
    k = pd.read_parquet(INFO / "keystats.parquet", columns=["slam", "year", "match_id", "set_key", "name", "player1",
                                                            "player2"])
    k = k[k["set_key"].eq("set0") & k["name"].isin(KS)].drop_duplicates(["slam", "year", "match_id", "name"])
    k["year"] = k["year"].astype(int)
    rows = []
    for no in ("1", "2"):
        w = k.pivot_table(index=["slam", "year", "match_id"], columns="name", values=f"player{no}",
                          aggfunc="first").reset_index()
        w["player_no"] = no
        rows.append(w)
    w = pd.concat(rows, ignore_index=True).rename(columns=KS)
    for c in ("ks_spd1", "ks_spd2", "ks_max"):
        w[c] = speed(w[c]).to_numpy() if c in w else np.nan
    first = w["ks_first"].astype(str).str.extract(FIRST_SERVE) if "ks_first" in w else pd.DataFrame({0: [], 1: []})
    w["ks_first_in"] = pd.to_numeric(first[0], errors="coerce")
    w["ks_first_total"] = pd.to_numeric(first[1], errors="coerce")
    return w.drop(columns=["ks_first"], errors="ignore")


def slam_dates() -> dict:
    """Stage 0's tournament date for each (slam, year, tour M/W, draw): the date its matches of that edition carry."""
    m = pd.read_parquet(PD.MATCHES, columns=["tour", "year", "level", "qualifying", "tournament_name",
                                             "tournament_date"])
    m = m[m["level"].eq("GS")].copy()
    m["slam"] = CV.slam_of(m["level"], m["tournament_name"]).to_numpy()
    m["draw"] = np.where(m["qualifying"].astype(bool), "qual", "main")
    m["tour"] = m["tour"].map({"atp": "M", "wta": "W"})
    g = m.groupby(["slam", "year", "tour", "draw"])["tournament_date"].agg(lambda x: x.mode().iloc[0])
    return g.to_dict()


def infosys_players(linker) -> tuple[pd.DataFrame, pd.DataFrame]:
    m = infosys_matches()
    dates = slam_dates()
    rows = pd.DataFrame({
        "tour": m["tour"], "draw": m["draw"], "round": m["round_from_code"],
        "d": [dates.get((s, y, t, d)) for s, y, t, d in zip(m["slam"], m["year"], m["tour"], m["draw"])],
        "name1": [full_name(f, l, n) for f, l, n in zip(m["p1_first_name"], m["p1_last_name"], m["p1_name"])],
        "name2": [full_name(f, l, n) for f, l, n in zip(m["p2_first_name"], m["p2_last_name"], m["p2_name"])]},
        index=m.index)
    linked = linker.link(rows)
    m = m.assign(name1=rows["name1"], name2=rows["name2"], match_id_s0=linked["match_id"], a1=linked["a1"])
    ps = point_speeds(infosys_points())
    ks = key_stats()
    long = []
    for no in ("1", "2"):
        long.append(m.assign(player_no=no, player_name=m[f"name{no}"], player_source_id=m[f"p{no}_id"]))
    long = pd.concat(long, ignore_index=True)
    long = long.merge(ps, on=["slam", "year", "match_id", "player_no"], how="left")
    long = long.merge(ks, on=["slam", "year", "match_id", "player_no"], how="left")
    out = pd.DataFrame({
        "source": "infosys_slams", "basis": np.where(long["ks_spd1"].notna(), "points+keystats", "points"),
        "event": long["slam"], "year": long["year"], "tour": long["tour"], "draw": long["draw"],
        "round": long["round_from_code"], "source_key": long["slam"] + "_" + long["year"].astype(str) + "_"
        + long["match_id"], "player_no": long["player_no"].astype(int), "player_name": long["player_name"],
        "player_source_id": long["player_source_id"], "match_id": long["match_id_s0"],
        "side": side_of(long["a1"], long["player_no"])})
    for c in COLUMNS:
        if c not in out:
            out[c] = long[c] if c in long else np.nan
    return out[COLUMNS], m


def side_of(a1: pd.Series, player_no: pd.Series) -> pd.Series:
    """Stage 0's side (A/B) of a source player: player 1 is A when a1 is True; unknown when a1 is missing."""
    no = player_no.astype(str)
    t, f = a1.eq(True), a1.eq(False)
    a = (t & no.eq("1")) | (f & no.eq("2"))
    b = (t & no.eq("2")) | (f & no.eq("1"))
    return pd.Series(np.select([a, b], ["A", "B"], default=None), index=a1.index, dtype=object)


# ------------------------------------------------------------------------------------------------
# ManTennisData
# ------------------------------------------------------------------------------------------------
def mantd_table() -> pd.DataFrame:
    t = pd.read_csv(MANTD / "tournaments.csv", dtype=str, usecols=["id", "name", "series_id", "start_dtm"])
    parts = [pd.read_csv(MANTD / f"matches_{y}.csv", dtype=str, keep_default_na=False) for y in MANTD_YEARS
             if (MANTD / f"matches_{y}.csv").exists()]
    m = pd.concat(parts, ignore_index=True).merge(t.rename(columns={"id": "tournament_id"}), on="tournament_id",
                                                  how="left")
    key = m["stats_url"].str.extract(STATS_URL)
    m["k_year"], m["k_tid"], m["k_code"] = key[0], key[1], key[2].str.upper()
    return m


def mantd_draw(rounds: pd.Series) -> np.ndarray:
    """ManTennisData's draw from its round code (stadie_id): Q1-Q3 are qualifying; QF is the main draw's
    quarter-final."""
    from src.eda.data_map import measure as M
    return np.where(M.is_qual_round(rounds), "qual", "main")


def mantd_players(linker) -> tuple[pd.DataFrame, pd.DataFrame]:
    m = mantd_table()
    long = []
    for no, pre, who in (("1", "win_", "winner"), ("2", "los_", "loser")):
        long.append(pd.DataFrame({
            "rid": m.index, "player_no": int(no), "player_name": m[f"{who}_name"], "player_source_id": m[f"{who}_code"],
            "ks_spd1": speed(m[f"{pre}average_first_serves_kmh"]).to_numpy(),
            "ks_spd2": speed(m[f"{pre}average_second_serve_kmh"]).to_numpy(),
            "ks_max": speed(m[f"{pre}fastest_first_serves_kmh"]).to_numpy(),
            "ks_first_in": pd.to_numeric(m[f"{pre}first_serves_in"], errors="coerce").to_numpy(),
            "ks_first_total": pd.to_numeric(m[f"{pre}first_serves_total"], errors="coerce").to_numpy()}))
    long = pd.concat(long, ignore_index=True)
    timed = set(long.loc[long[["ks_spd1", "ks_spd2", "ks_max"]].notna().any(axis=1), "rid"])
    mt = m.loc[sorted(timed)]
    draw = mantd_draw(mt["stadie_id"])
    rows = pd.DataFrame({"tour": "M", "d": pd.to_datetime(mt["start_dtm"], format="%Y%m%d", errors="coerce"),
                         "name1": mt["winner_name"], "name2": mt["loser_name"], "round": mt["stadie_id"], "draw": draw},
                        index=mt.index)
    linked = linker.link(rows)
    mt = mt.assign(match_id_s0=linked["match_id"], a1=linked["a1"], draw=draw)
    long = long[long["rid"].isin(timed)].merge(
        mt[["match_id_s0", "a1", "draw", "series_id", "stadie_id", "id", "start_dtm", "k_year"]]
        .rename_axis("rid").reset_index(), on="rid", how="left")
    out = pd.DataFrame({
        "source": "mantennisdata", "basis": "keystats", "event": long["series_id"],
        "year": pd.to_numeric(long["start_dtm"].str[:4], errors="coerce"), "tour": "M", "draw": long["draw"],
        "round": long["stadie_id"], "source_key": long["id"], "player_no": long["player_no"],
        "player_name": long["player_name"], "player_source_id": long["player_source_id"], "match_id": long["match_id_s0"],
        "side": side_of(long["a1"], long["player_no"])})
    for c in COLUMNS:
        if c not in out:
            out[c] = long[c] if c in long else np.nan
    return out[COLUMNS], m


# ------------------------------------------------------------------------------------------------
# the ATP Stats Centre's own Infosys files, 2018 to October 2021 (decrypted on 8 Oct 2026)
# ------------------------------------------------------------------------------------------------
ATP_KEYS = ["year", "event_id", "match_id"]


def atp_rounds(years) -> pd.DataFrame:
    """The round of each ATP match code (year, event, code), from ManTennisData's stats links: the plan's own source.
    Identity only (no winner, loser or score is read)."""
    from src.ingest.point_sources import infosys_atp as A
    parts = [pd.read_parquet(p, columns=["stadie_id", "stats_url"]) for y in years
             if (p := MANTD_STAGED / f"atp_matches_{y}.parquet").exists()]
    if not parts:
        return pd.DataFrame(columns=ATP_KEYS + ["round_mantd"])
    m = pd.concat(parts, ignore_index=True)
    code = m["stats_url"].map(A.code_of)
    ok = code.notna().to_numpy()
    out = pd.DataFrame({"year": [str(c[0]) for c in code[ok]], "event_id": [str(c[1]) for c in code[ok]],
                        "match_id": [c[2] for c in code[ok]], "round_mantd": m.loc[ok, "stadie_id"].to_numpy()})
    return out.drop_duplicates(ATP_KEYS)


def atp_point_speeds() -> pd.DataFrame:
    """As point_speeds, per (year, event, code, server); double faults ("P" or "DF") are not second serves in."""
    p = pd.read_parquet(ATP / "points.parquet", columns=ATP_KEYS + ["server", "serve", "serveSpeed", "faultSrvSpd",
                                                                    "result"])
    p["spd"] = speed(p["serveSpeed"]).to_numpy()
    p["fault"] = speed(p["faultSrvSpd"]).to_numpy()
    dfl = p["result"].isin(ATP_DOUBLE_FAULTS)
    p = p.assign(s1=p["spd"].where(p["serve"].eq("1")), s2=p["spd"].where(p["serve"].eq("2") & ~dfl),
                 f1=p["fault"].where(p["serve"].eq("2")))
    g = p.groupby(ATP_KEYS + ["server"])
    out = g.agg(service_points=("serve", "size"), spd1_n=("s1", "count"), spd1_mean=("s1", "mean"),
                spd2_n=("s2", "count"), spd2_mean=("s2", "mean"), fault1_n=("f1", "count"),
                fault1_mean=("f1", "mean"), spd_max=("spd", "max")).reset_index()
    out = out[out["server"].isin(["1", "2"])]
    return out.rename(columns={"server": "player_no"})


def atp_key_stats() -> pd.DataFrame:
    """The ATP files' key statistics of the match ("set0"), one row per match and player."""
    k = pd.read_parquet(ATP / "keystats.parquet", columns=ATP_KEYS + ["set_key", "name", "player1", "player2"])
    k = k[k["set_key"].eq("set0") & k["name"].isin(ATP_KS)].drop_duplicates(ATP_KEYS + ["name"])
    rows = []
    for no in ("1", "2"):
        w = k.pivot_table(index=ATP_KEYS, columns="name", values=f"player{no}", aggfunc="first").reset_index()
        w["player_no"] = no
        rows.append(w)
    w = pd.concat(rows, ignore_index=True).rename(columns=ATP_KS)
    for c in ("ks_spd1", "ks_spd2", "ks_max"):
        w[c] = speed(w[c]).to_numpy() if c in w else np.nan
    first = w["ks_first"].astype(str).str.extract(FIRST_SERVE) if "ks_first" in w else pd.DataFrame({0: [], 1: []})
    w["ks_first_in"] = pd.to_numeric(first[0], errors="coerce")
    w["ks_first_total"] = pd.to_numeric(first[1], errors="coerce")
    return w.drop(columns=["ks_first"], errors="ignore")


def infosys_atp_players() -> tuple[pd.DataFrame, pd.DataFrame]:
    """One row per player of every planned ATP match code with a file (the four calibration files of 2022 and 2025 are
    outside the window), linked by the live pipeline's linker on the current Stage 0."""
    from src.eda.serve_speed_tabpfn.live import link as LK
    m = pd.read_parquet(ATP / "matches.parquet")
    m = m[m["purpose"].eq("plan")].reset_index(drop=True)
    m = m.merge(atp_rounds(sorted(set(m["year"].astype(int)))), on=ATP_KEYS, how="left")
    m["round"] = m["round_mantd"].fillna(m["round_from_code"])
    m["name1"] = [full_name(f, l, n) for f, l, n in zip(m["p1_first_name"], m["p1_last_name"], m["p1_name"])]
    m["name2"] = [full_name(f, l, n) for f, l, n in zip(m["p2_first_name"], m["p2_last_name"], m["p2_name"])]
    staged = pd.DataFrame({"year": m["year"].astype(int), "event_id": m["event_id"], "match_code": m["match_id"],
                           "round": m["round"], "p1_atp_id": m["p1_id"], "p1_name": m["name1"], "p2_atp_id": m["p2_id"],
                           "p2_name": m["name2"]})
    lk = LK.link(staged)
    ins = lk["in_stage0"].astype(bool).to_numpy()
    m["match_id_s0"] = np.where(ins, lk["match_id"], None)
    m["side_p1"] = np.where(ins, lk["side_p1"], None)
    m["link_method"] = np.where(ins, lk["link_method"], "unlinked")
    m["round_s0"] = lk["round_s0"].to_numpy()
    long = pd.concat([m.assign(player_no=no, player_name=m[f"name{no}"], player_source_id=m[f"p{no}_id"])
                      for no in ("1", "2")], ignore_index=True)
    long = long.merge(atp_point_speeds(), on=ATP_KEYS + ["player_no"], how="left")
    long = long.merge(atp_key_stats(), on=ATP_KEYS + ["player_no"], how="left")
    p1 = long["player_no"].eq("1")
    side = np.where(p1, long["side_p1"], long["side_p1"].map({"A": "B", "B": "A"}))
    basis = np.where(long["ks_spd1"].notna() & long["spd1_mean"].notna(), "points+keystats",
                     np.where(long["ks_spd1"].notna(), "keystats", "points"))
    out = pd.DataFrame({
        "source": "infosys_atp", "basis": basis, "event": long["event_id"], "year": long["year"].astype(int),
        "tour": "M", "draw": long["draw"], "round": long["round"],
        "source_key": long["year"] + "_" + long["event_id"] + "_" + long["match_id"],
        "player_no": long["player_no"].astype(int), "player_name": long["player_name"],
        "player_source_id": long["player_source_id"], "match_id": long["match_id_s0"],
        "side": pd.Series(side, dtype=object).where(pd.notna(long["match_id_s0"]).to_numpy(), None)})
    for c in COLUMNS:
        if c not in out:
            out[c] = long[c] if c in long else np.nan
    return out[COLUMNS], m


# ------------------------------------------------------------------------------------------------
# checks
# ------------------------------------------------------------------------------------------------
def check_sirgenkii_points(points: pd.DataFrame) -> dict:
    r = pd.read_parquet(SIRG / "atp_rally_analysis.parquet", columns=["year", "tournament_id", "match_id", "point_id",
                                                                      "serve", "serve_speed"])
    r = r[r["year"].astype(str).eq("2025") & r["tournament_id"].astype(str).eq("580")].copy()
    r["mid"] = r["match_id"].str.upper()
    p = points[points["slam"].eq("AO") & points["year"].eq(2025) & points["match_id"].isin(set(r["mid"]))]
    j = p.merge(r, left_on=["match_id", "pointId"], right_on=["mid", "point_id"], how="outer", indicator=True)
    b = j[j["_merge"].eq("both")]
    a, g = pd.to_numeric(b["serveSpeed"], errors="coerce"), pd.to_numeric(b["serve_speed"], errors="coerce")
    same_speed = (a.round(1) == g.round(1)) | (a.isna() & g.isna())
    return {"matches": int(r["mid"].nunique()), "matches_in_matchbeats": int(p["match_id"].nunique()),
            "points_joined": int(len(b)), "only_matchbeats": int(j["_merge"].eq("left_only").sum()),
            "only_sirgenkii": int(j["_merge"].eq("right_only").sum()), "speed_equal": int(same_speed.sum()),
            "serve_number_equal": int((b["serve_x"].astype(str) == b["serve_y"].astype(str)).sum()),
            "max_abs_speed_diff_kmh": float((a - g).abs().max()) if len(b) else None}


def check_ao_match_centre(players: pd.DataFrame) -> dict:
    a = pd.read_parquet(AO_DUMP / "set_statistics.parquet", columns=["record_key", "year", "event", "match_id", "set",
                                                                     "stat", "team1_primary", "team2_primary"])
    a = a[a["stat"].eq("1st Serve Average") & a["set"].eq("All") & a["year"].astype(str).eq("2025")
          & a["event"].isin(["MS", "WS", "MQ", "WQ"])]
    mm = pd.read_parquet(AO_DUMP / "matches.parquet", columns=["record_key", "team1_names", "team2_names",
                                                               "match_status_name"])
    a = a.merge(mm, on="record_key", how="left")
    me = players[players["source"].eq("infosys_slams") & players["event"].eq("AO") & players["year"].eq(2025)]
    me = me.assign(mid=me["source_key"].str.split("_").str[-1])
    rows = []
    for r in a.itertuples(index=False):
        ours = me[me["mid"].eq(r.match_id)]
        if len(ours) != 2:
            continue
        for team, val in ((r.team1_names, r.team1_primary), (r.team2_names, r.team2_primary)):
            v = speed([val]).iloc[0]
            hit = ours[[surname(team) == surname(n) for n in ours["player_name"]]]
            if np.isnan(v) or len(hit) != 1:
                continue
            h = hit.iloc[0]
            rows.append({"match_id": r.match_id, "player": h["player_name"], "status": r.match_status_name,
                         "ao_value": v, "matchbeats_mean": round(float(h["spd1_mean"]), 2), "n": int(h["spd1_n"]),
                         "diff": round(v - float(h["spd1_mean"]), 2)})
    d = pd.DataFrame(rows)
    return {"player_matches": len(d), "matches": int(d["match_id"].nunique()) if len(d) else 0,
            "equal_to_rounded_mean": int((d["ao_value"] == d["matchbeats_mean"].round()).sum()) if len(d) else 0,
            "within_1_kmh": int((d["diff"].abs() <= 1).sum()) if len(d) else 0,
            "rows": d.to_dict(orient="records")}


def surname(name) -> str:
    from src.eda.data_map import measure as M
    return M.surname_key(str(name or ""))


def check_rg_keystats(players: pd.DataFrame) -> dict:
    r = players[players["source"].eq("infosys_slams") & players["ks_spd1"].notna() & players["spd1_mean"].notna()]
    d = r["ks_spd1"] - r["spd1_mean"]
    n = r["ks_first_in"] - r["spd1_n"]
    out = {"player_matches": int(len(r)), "by_year": {str(k): int(v) for k, v in r.groupby("year").size().items()}}
    if len(r):
        out.update(diff_median=round(float(d.median()), 3), diff_mean=round(float(d.mean()), 3),
                   abs_diff_p90=round(float(d.abs().quantile(0.9)), 3),
                   equal_to_rounded_mean=int((r["ks_spd1"] == r["spd1_mean"].round()).sum()),
                   within_1_kmh=int((d.abs() <= 1).sum()),
                   first_in_minus_timed_median=float(n.median()),
                   note="positive diff = the key statistic is faster than the mean of first serves in from points")
    return out


def check_flashscore(players: pd.DataFrame) -> dict:
    """Flashscore's two averages against ours, unoriented (flashscore_crawl.py's method)."""
    sl = players[players["source"].eq("infosys_slams") & players["match_id"].notna()]
    w = sl.pivot_table(index="match_id", columns="player_no", values="spd1_mean").dropna()
    if w.empty:
        return {"matches": 0}
    link = pd.read_parquet(FS_LINK, columns=["match_id", "source_key"])
    link = link[link["match_id"].isin(set(w.index))]
    files = sorted(str(p) for d in ("flashscore_full", "flashscore_gql_stats") for p in (HANDOFF / d).glob("*.jsonl.gz"))
    with mp.Pool(6) as pool:
        parts = pool.map(FC.scan, files, chunksize=1)
    fs = pd.DataFrame([r for p in parts for r in p], columns=["fs_id", "date", "event", "has_stats", "h1", "a1"])
    fs = fs[fs["h1"].notna() & fs["a1"].notna()].drop_duplicates("fs_id")
    k = fs.merge(link.rename(columns={"source_key": "fs_id"}), on="fs_id").merge(w, left_on="match_id",
                                                                                  right_index=True)
    k["diff_match_mean"] = (k["h1"] + k["a1"]) / 2 - (k[1] + k[2]) / 2
    k["pair_err"] = np.minimum(abs(k["h1"] - k[1]) + abs(k["a1"] - k[2]), abs(k["h1"] - k[2]) + abs(k["a1"] - k[1])) / 2
    k["edition"] = k["match_id"].map(sl.drop_duplicates("match_id").set_index("match_id")["source_key"]
                                     .str.rsplit("_", n=1).str[0])
    g = k.groupby("edition").agg(matches=("fs_id", "size"), mean_diff_kmh=("diff_match_mean", "mean"),
                                 median_player_err_kmh=("pair_err", "median"),
                                 p90_player_err_kmh=("pair_err", lambda x: x.quantile(0.9))).round(3)
    return {"matches": int(len(k)), "by_edition": g.reset_index().to_dict(orient="records"),
            "note": "positive diff = Flashscore faster; Flashscore prints whole km/h"}


def handoff_keystats() -> pd.DataFrame:
    """The Hugging Face handoff's decrypted ATP key statistics: year, tournament, match code and both players'
    1st Serve Average Speed (records whose key statistics name the statistic at all)."""
    rows = []
    for folder in ("infosys_deep", "infosys_full"):
        for p in sorted((HANDOFF / folder).glob("*_data.jsonl*")):
            op = gzip.open if p.suffix == ".gz" else open
            with op(p, "rt", encoding="utf-8") as f:
                for line in f:
                    if "1st Serve Average Speed" not in line:
                        continue
                    r = json.loads(line)
                    s0 = ((r.get("keystats") or {}).get("setStats") or {}).get("set0") or []
                    x = next((e for e in s0 if e.get("name") == "1st Serve Average Speed"), None)
                    if x is None:
                        continue
                    rows.append((str(r.get("year")), str(r.get("tournament_id")), str(r.get("match_id")).upper(),
                                 x.get("player1"), x.get("player2")))
    h = pd.DataFrame(rows, columns=["k_year", "k_tid", "k_code", "v1", "v2"]).drop_duplicates(["k_year", "k_tid",
                                                                                                "k_code"])
    h["v1"], h["v2"] = speed(h["v1"]).to_numpy(), speed(h["v2"]).to_numpy()
    return h


def check_mantd_vs_infosys(m: pd.DataFrame) -> dict:
    m = m.assign(w=speed(m["win_average_first_serves_kmh"]).to_numpy(),
                 l=speed(m["los_average_first_serves_kmh"]).to_numpy())
    m["timed"] = m["w"].notna() & m["l"].notna()
    out = {}
    # SirGenkii, January to April 2025, by player
    k = pd.read_parquet(SIRG / "atp_key_stats.parquet", columns=["year", "tournament_id", "match_id", "set_n",
                                                                 "player_id", "serve1_avg_speed"])
    k = k[k["set_n"].astype(str).eq("0")].assign(k_code=lambda x: x["match_id"].str.upper(),
                                                 v=lambda x: speed(x["serve1_avg_speed"]).to_numpy())
    k = k[k["v"].notna()]
    long = pd.concat([m.assign(code=m["winner_code"].str.upper(), mv=m["w"]),
                      m.assign(code=m["loser_code"].str.upper(), mv=m["l"])])
    j = long.merge(k, left_on=["k_year", "k_tid", "k_code", "code"],
                   right_on=["year", "tournament_id", "k_code", "player_id"], how="inner", suffixes=("", "_k"))
    both = j[j["mv"].notna()]
    out["sirgenkii_2025"] = {"player_matches_with_speed_in_sirgenkii": int(len(j)),
                             "with_speed_in_both": int(len(both)),
                             "equal": int((both["mv"].round() == both["v"].round()).sum()),
                             "sirgenkii_only": int(j["mv"].isna().sum())}
    # the Hugging Face handoff, 2021-24, unoriented
    h = handoff_keystats()
    h["timed"] = h["v1"].notna() & h["v2"].notna()
    names = pd.read_csv(MANTD / "tournaments.csv", dtype=str, usecols=["id", "name"]).set_index("id")["name"]
    early = h[h["timed"] & (h["k_year"] <= "2021")]
    out["handoff_timed_records_by_year"] = h[h["timed"]].groupby("k_year").size().to_dict()
    out["handoff_timed_before_2022_by_event"] = [
        {"year": y, "tournament_id": t, "name": names.get(f"{y}-{t}"), "matches": int(n)}
        for (y, t), n in early.groupby(["k_year", "k_tid"]).size().sort_values(ascending=False).items()]
    x = m[m["k_year"].isin(["2021", "2022", "2023", "2024"])].merge(h, on=["k_year", "k_tid", "k_code"], how="left",
                                                                     suffixes=("", "_h"), indicator=True)
    x["timed_h"] = x["timed_h"].fillna(False).astype(bool)
    b = x[x["timed"] & x["timed_h"]]
    same = ((b["w"].round() == b["v1"].round()) & (b["l"].round() == b["v2"].round())) | \
           ((b["w"].round() == b["v2"].round()) & (b["l"].round() == b["v1"].round()))
    only_h = x[~x["timed"] & x["timed_h"]]
    out["handoff_2021_24"] = {
        "mantd_rows": int(len(x)), "rows_with_a_handoff_keystats_record": int(x["_merge"].eq("both").sum()),
        "timed_in_both": int(len(b)), "equal_both_players": int(same.sum()),
        "timed_only_in_mantd": int((x["timed"] & ~x["timed_h"]).sum()),
        "timed_only_in_handoff": int(len(only_h)),
        "timed_only_in_handoff_by_series": only_h.groupby("series_id").size().to_dict(),
        "timed_only_in_handoff_top_events": only_h.groupby(["k_year", "name"]).size().sort_values(ascending=False)
        .head(15).reset_index().rename(columns={0: "matches"}).to_dict(orient="records")}
    return out


def check_continuity(players: pd.DataFrame, min_first_in: int = 20) -> dict:
    st = pd.read_parquet(SHOT_STATS, columns=["match_id", "side", "spd1_n", "spd1_d"])
    st = st[st["spd1_d"] > 0]
    m = pd.read_parquet(PD.MATCHES, columns=["match_id", "tour", "year", "level", "tournament_name", "player_a_id",
                                             "player_b_id"])
    m = m[m["level"].eq("GS")].copy()
    m["slam"] = CV.slam_of(m["level"], m["tournament_name"]).to_numpy()
    m = m[m["slam"].isin(["AO", "RG"])]
    held = st.merge(m, on="match_id")
    held = held[held["year"] < 2025]
    held_rows = pd.DataFrame({"slam": held["slam"], "year": held["year"], "tour": held["tour"],
                              "player_id": np.where(held["side"].eq("A"), held["player_a_id"], held["player_b_id"]),
                              "s": held["spd1_n"], "n": held["spd1_d"]})
    new = players[players["source"].eq("infosys_slams") & players["spd1_mean"].notna() & players["side"].notna()]
    new = new.merge(m[["match_id", "tour", "player_a_id", "player_b_id"]], on="match_id", suffixes=("", "_s0"))
    new_rows = pd.DataFrame({"slam": new["event"], "year": new["year"].astype(int), "tour": new["tour_s0"],
                             "player_id": np.where(new["side"].eq("A"), new["player_a_id"], new["player_b_id"]),
                             "s": new["spd1_mean"] * new["spd1_n"], "n": new["spd1_n"]})
    per = pd.concat([held_rows, new_rows]).groupby(["slam", "tour", "year", "player_id"])[["s", "n"]].sum()
    per = per[per["n"] >= min_first_in].assign(v=lambda x: x["s"] / x["n"])["v"].reset_index()
    out = []
    for (slam, tour), g in per.groupby(["slam", "tour"]):
        years = sorted(int(y) for y in g["year"].unique())
        for y0, y1 in [(y, y + 1) for y in years] + [(y, y + 2) for y in years]:
            if y1 not in years:
                continue
            a = g[g["year"].eq(y0)].set_index("player_id")["v"]
            b = g[g["year"].eq(y1)].set_index("player_id")["v"]
            common = a.index.intersection(b.index)
            if len(common) < 10:
                continue
            d = b[common] - a[common]
            out.append({"slam": slam, "tour": tour, "from": int(y0), "to": int(y1), "players": int(len(common)),
                        "median_change_kmh": round(float(d.median()), 2), "mean_change_kmh": round(float(d.mean()), 2),
                        "new_files": bool(y1 >= 2025)})
    return {"min_first_serves_in": min_first_in, "pairs": out,
            "note": "positive = faster in the later year; pairs one and two years apart; years to 2024 from the held "
                    "copies (Sackmann's Slam files, the Hawk-Eye Court Vision copy), 2025 on from the decrypted "
                    "Infosys files"}


# ------------------------------------------------------------------------------------------------
def link_summary(players: pd.DataFrame) -> dict:
    out = {}
    for (src, ev, yr), g in players.groupby(["source", "event", "year"], dropna=False):
        timed = g[g[["spd1_mean", "ks_spd1"]].notna().any(axis=1)]
        out[f"{src}|{ev}|{int(yr) if pd.notna(yr) else 'na'}"] = {
            "source_matches": int(g["source_key"].nunique()),
            "linked": int(g.loc[g["match_id"].notna(), "source_key"].nunique()),
            "oriented": int(g.loc[g["side"].notna(), "source_key"].nunique()),
            "player_matches_timed": int(len(timed)),
            "player_matches_timed_linked": int(timed["side"].notna().sum())}
    return out


def main() -> None:
    from src.eda.shot_level import common as S

    OUT.mkdir(parents=True, exist_ok=True)
    log("Stage 0 linker")
    linker = S.Stage0Linker()
    log("Infosys Slam files")
    sl, sl_matches = infosys_players(linker)
    log(f"  {len(sl):,} player rows; ManTennisData")
    md, md_table = mantd_players(linker)
    log(f"  {len(md):,} player rows; the ATP's own Infosys files")
    ia, _ = infosys_atp_players()
    log(f"  {len(ia):,} player rows")
    players = pd.concat([sl, md, ia], ignore_index=True)
    players["year"] = players["year"].astype("Int64")
    players.to_parquet(OUT / "speeds.parquet", index=False)
    links = link_summary(players)
    (OUT / "links.json").write_text(json.dumps(links, indent=1) + "\n", encoding="utf-8")
    log("checks")
    checks = {"built_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "reads_results": False}
    checks["1_sirgenkii_points"] = check_sirgenkii_points(infosys_points())
    log(f"  1 {checks['1_sirgenkii_points']}")
    checks["2_ao_match_centre"] = check_ao_match_centre(players)
    log(f"  2 {({k: v for k, v in checks['2_ao_match_centre'].items() if k != 'rows'})}")
    checks["3_rg_keystats"] = check_rg_keystats(players)
    log(f"  3 {checks['3_rg_keystats']}")
    checks["4_flashscore"] = check_flashscore(players)
    log(f"  4 {checks['4_flashscore']}")
    checks["5_mantd_vs_infosys"] = check_mantd_vs_infosys(md_table)
    log(f"  5 {checks['5_mantd_vs_infosys']}")
    checks["6_continuity"] = check_continuity(players)
    log("  6 " + "; ".join(f"{p['slam']} {p['tour']} {p['from']}->{p['to']}: {p['median_change_kmh']:+.2f} "
                           f"(n={p['players']})" for p in checks["6_continuity"]["pairs"] if p["to"] >= 2022))
    (OUT / "checks.json").write_text(json.dumps(checks, indent=1, default=str) + "\n", encoding="utf-8")
    log("links:\n" + json.dumps(links, indent=1))


if __name__ == "__main__":
    main()
