"""Source 4, slam_feeds: the Grand Slams' own scoring feeds, staged under data/dump/points/ (docs/studies/
official_point_feeds/README.md):
    ausopen/matches.parquet         Australian Open 2026 match centre (all six events) and the Wayback captures of
                                    2020-2026: each point's Unix time, the listed local date and local start time
    ausopen/archived_draws.parquet  archived AO draws 2019-2025 (Wayback): every match of an archived event with its
                                    listed local date, no time (2019 men's and women's qualifying, 2020 singles,
                                    2021 men, 2022 singles and men's qualifying, 2023-24 men, 2025 all four singles events)
    wimbledon/                      IBM SlamTracker 2019, 2021-2026: matches (the draw entry) and every point with
                                    EpochTimeStart / EpochTimeEnd
    usopen/                         IBM SlamTracker 2022-2026, the same
Singles only (AO: MS, WS, MQ, WQ and 2019's QS, PS; Wimbledon MS, LS, QS, RS; US Open MS, WS, MQ, WQ).

Times, per the study's warnings:
    * the first point is the start. SlamTracker: the first numbered point's EpochTimeStart when it lies 0-15 minutes
      before its own EpochTimeEnd, else its EpochTimeEnd (the more reliable clock; EpochTimeStart is sometimes the
      keying time). The later faults (spurious day jumps, 2026 start times running ahead) arise mid-match, after it.
      AO: the earliest point entry's time (entries keyed late are stamped later, never earlier);
    * the listings' own times are not used for a start: the US Open's 2026 draw times run 5 hours early. A US Open
      2022-2025 match without points (qualifying the draw marks "S") takes the day of the draw's epoch, the match's
      end in those years, as its day, with no start time; the AO's archived draws give a listed local date only.
Days are local: Melbourne, London, New York.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.eda.match_timing import srcc_common as K

SOURCE = "slam_feeds"
PTS = K.DUMP / "points"
ZONE = {"ausopen": "Australia/Melbourne", "wimbledon": "Europe/London", "usopen": "America/New_York"}
EVENTS = {"ausopen": {"MS": ("atp", False), "WS": ("wta", False), "MQ": ("atp", True), "WQ": ("wta", True),
                      "QS": ("atp", True), "PS": ("wta", True)},
          "wimbledon": {"MS": ("atp", False), "LS": ("wta", False), "QS": ("atp", True), "RS": ("wta", True)},
          "usopen": {"MS": ("atp", False), "WS": ("wta", False), "MQ": ("atp", True), "WQ": ("wta", True)}}
AO_MAIN = {"1st Round": "R128", "2nd Round": "R64", "3rd Round": "R32", "4th Round": "R16", "Quarterfinals": "QF",
           "Semifinals": "SF", "Final": "F"}
AO_QUAL = {"1st Round": "Q1", "2nd Round": "Q2", "3rd Round": "Q3", "Final Round": "Q3"}
ST_MAIN = {"1": "R128", "2": "R64", "3": "R32", "4": "R16", "Q": "QF", "S": "SF", "F": "F"}
ST_QUAL = {"1": "Q1", "2": "Q2", "3": "Q3"}
EPOCH_OK = (pd.Timestamp("2018-01-01", tz="UTC").timestamp(), pd.Timestamp("2027-01-01", tz="UTC").timestamp())


def epoch_hi(year) -> np.ndarray:
    """Per row, the latest plausible Unix time: EPOCH_OK's end for seasons to 2026 (the bound for every row before
    10 Oct 2026), the 1 January after the row's season for a later one."""
    y = pd.to_numeric(pd.Series(np.asarray(year)), errors="coerce").to_numpy(dtype=float)
    hi = np.full(len(y), EPOCH_OK[1])
    later = np.isfinite(y) & (y >= 2027)
    for v in np.unique(y[later]):
        hi[later & (y == v)] = pd.Timestamp(f"{int(v) + 1}-01-01", tz="UTC").timestamp()
    return hi


def ao_sets(t1: str, t2: str) -> tuple:
    """'7 4 6 7(7)' / '5 6 4 6(3)' -> ((7, 5), (4, 6), (6, 4), (7, 6))."""
    a = [re.sub(r"\(.*?\)", "", x) for x in str(t1 or "").split()]
    b = [re.sub(r"\(.*?\)", "", x) for x in str(t2 or "").split()]
    return K.sets_from_pairs(list(zip(a, b)))


def text_sets(score: str) -> tuple:
    """SlamTracker's 'score_text', team 1 first: '6-7(6) 3-6 6-4' -> ((6, 7), (3, 6), (6, 4))."""
    out = []
    for tok in str(score or "").split():
        m = re.match(r"^(\d+)-(\d+)", tok)
        if not m:
            break
        out.append((int(m.group(1)), int(m.group(2))))
    return tuple(out)


# ------------------------------------------------------------------------------------------------

def ausopen() -> pd.DataFrame:
    """AO singles rows: match centre (2026 and Wayback captures) first, archived draws for what they lack."""
    m = pq.read_table(PTS / "ausopen" / "matches.parquet").to_pandas()
    p = pq.read_table(PTS / "ausopen" / "points.parquet", columns=["record_key", "type", "timestamp"]).to_pandas()
    p["timestamp"] = pd.to_numeric(p["timestamp"], errors="coerce")
    season = p["record_key"].map(m.drop_duplicates("record_key").set_index("record_key")["year"])
    p = p[(p["timestamp"] > EPOCH_OK[0]) & (p["timestamp"] < epoch_hi(season))]
    first = p.groupby("record_key")["timestamp"].min()
    last = p[p["type"].eq("match")].groupby("record_key")["timestamp"].min()   # the match-ending entry
    m["year"] = m["year"].astype(int)
    m = m[m["event"].isin(EVENTS["ausopen"])].copy()
    m["t0"] = pd.to_datetime(m["record_key"].map(first), unit="s", utc=True)
    m["t1"] = pd.to_datetime(m["record_key"].map(last), unit="s", utc=True)
    m["listed_day"] = pd.to_datetime(m["date"], errors="coerce")
    # one row per match: a capture with points beats one without, the API beats a capture, the latest capture last
    m["rank"] = m["t0"].notna().astype(int) * 2 + m["route"].eq("api").astype(int)
    m = m.sort_values(["year", "event", "match_id", "rank", "capture_timestamp"], na_position="first")
    m = m.drop_duplicates(["year", "event", "match_id"], keep="last")
    rows = pd.DataFrame({
        "site": "ausopen", "year": m["year"], "event": m["event"], "mid": m["match_id"],
        "sid": "ausopen:" + m["year"].astype(str) + "/" + m["match_id"] + np.where(m["route"].eq("api"), "", "@wayback"),
        "p1": m["team1_names"], "p2": m["team2_names"], "id1": m["team1_tour_ids"], "id2": m["team2_tour_ids"],
        "sets": [ao_sets(a, b) for a, b in zip(m["team1_score"], m["team2_score"])],
        "round_name": m["round_name"], "status": m["match_status"], "t0": m["t0"], "t1": m["t1"],
        "listed_day": m["listed_day"], "end_ts": pd.NaT})
    a = pq.read_table(PTS / "ausopen" / "archived_draws.parquet").to_pandas()
    a["year"] = a["year"].astype(int)
    a = a[a["event"].isin(EVENTS["ausopen"]) & a["date"].notna()]
    a = a[~a.set_index(["year", "event", "match_id"]).index.isin(
        rows.set_index(["year", "event", "mid"]).index[rows["t0"].notna()])]
    rows = rows[~rows.set_index(["year", "event", "mid"]).index.isin(a.set_index(["year", "event", "match_id"]).index)
                | rows["t0"].notna()]
    arch = pd.DataFrame({
        "site": "ausopen", "year": a["year"], "event": a["event"], "mid": a["match_id"],
        "sid": "ausopen:" + a["year"].astype(str) + "/" + a["match_id"] + "@archived_draw",
        "p1": a["team1_names"], "p2": a["team2_names"], "id1": a["team1_tour_ids"], "id2": a["team2_tour_ids"],
        "sets": [ao_sets(x, y) for x, y in zip(a["team1_score"], a["team2_score"])],
        "round_name": a["round_name"], "status": a["match_status"], "t0": pd.NaT, "t1": pd.NaT,
        "listed_day": pd.to_datetime(a["date"], errors="coerce"), "end_ts": pd.NaT})
    out = pd.concat([rows, arch], ignore_index=True)
    q = out["event"].map(lambda e: EVENTS["ausopen"][e][1])
    out["rnd"] = [(AO_QUAL if qq else AO_MAIN).get(r) for r, qq in zip(out["round_name"], q)]
    out["walkover"] = out["status"].eq("W/O")
    out["played"] = out["status"].isin(["CMP", "RET"]) | out["t0"].notna()
    return out


def slamtracker(site: str) -> pd.DataFrame:
    cols = ["year", "event", "match_id", "entry.roundCode", "entry.statusCode", "entry.score_text", "entry.winner",
            "entry.epoch", "entry.eventDay", "entry.team1.firstNameA", "entry.team1.lastNameA", "entry.team1.idA",
            "entry.team2.firstNameA", "entry.team2.lastNameA", "entry.team2.idA", "history_points"]
    m = pq.read_table(PTS / site / "matches.parquet", columns=cols).to_pandas()
    m["year"] = m["year"].astype(int)
    m = m[m["event"].isin(EVENTS[site])].copy()
    p = pq.read_table(PTS / site / "points.parquet",
                      columns=["year", "event", "match_id", "row", "PointNumber", "EpochTimeStart", "EpochTimeEnd"]).to_pandas()
    p = p[p["event"].isin(EVENTS[site]) & p["PointNumber"].astype(str).str.fullmatch(r"\d+")].copy()
    p["pn"] = p["PointNumber"].astype(int)
    p["ts"] = pd.to_numeric(p["EpochTimeStart"], errors="coerce")
    p["te"] = pd.to_numeric(p["EpochTimeEnd"], errors="coerce")
    p = p[(p["te"] >= EPOCH_OK[0]) & (p["te"] <= epoch_hi(p["year"]))]
    p["year"] = p["year"].astype(int)
    f = p.sort_values(["year", "event", "match_id", "pn", "row"]).drop_duplicates(["year", "event", "match_id"])
    ok = (f["ts"] >= EPOCH_OK[0]) & (f["ts"] <= epoch_hi(f["year"])) & (f["te"] - f["ts"]).between(0, 900)
    f["t0"] = pd.to_datetime(np.where(ok, f["ts"], f["te"]), unit="s", utc=True)
    f["t0_basis"] = np.where(ok, "first_point_start", "first_point_end")
    last = p.groupby(["year", "event", "match_id"])["te"].max().rename("te_last").reset_index()
    jumps = pd.read_csv(K.ROOT / "data" / "studies" / "official_point_feeds" / f"{site}_epoch_problems.csv", dtype=str)
    jumps = jumps[pd.to_numeric(jumps["day_jumps"], errors="coerce").fillna(0) > 0]
    jk = set(zip(jumps["year"].astype(int), jumps["event"], jumps["match_id"].astype(str)))
    last["day_jump"] = [(y, e, str(i)) in jk for y, e, i in zip(last["year"], last["event"], last["match_id"])]
    last["t1"] = pd.to_datetime(last["te_last"].where(~last["day_jump"]), unit="s", utc=True)
    m = m.merge(f[["year", "event", "match_id", "t0", "t0_basis"]], on=["year", "event", "match_id"], how="left")
    m = m.merge(last[["year", "event", "match_id", "t1", "day_jump"]], on=["year", "event", "match_id"], how="left")
    q = m["event"].map(lambda e: EVENTS[site][e][1])
    epoch = pd.to_numeric(m["entry.epoch"], errors="coerce") / 1000
    out = pd.DataFrame({
        "site": site, "year": m["year"], "event": m["event"], "mid": m["match_id"],
        "sid": site + ":" + m["year"].astype(str) + "/" + m["event"] + "/" + m["match_id"],
        "p1": (m["entry.team1.firstNameA"].fillna("") + " " + m["entry.team1.lastNameA"].fillna("")).str.strip(),
        "p2": (m["entry.team2.firstNameA"].fillna("") + " " + m["entry.team2.lastNameA"].fillna("")).str.strip(),
        "id1": m["entry.team1.idA"], "id2": m["entry.team2.idA"],
        "sets": m["entry.score_text"].map(text_sets),
        "round_name": m["entry.roundCode"], "status": m["entry.statusCode"], "t0": m["t0"], "t0_basis": m["t0_basis"],
        "t1": m["t1"], "day_jump": m["day_jump"].fillna(False).astype(bool),
        "listed_day": pd.NaT, "end_ts": pd.to_datetime(epoch.where((epoch >= EPOCH_OK[0])
                                                                    & (epoch <= epoch_hi(m["year"]))), unit="s", utc=True),
        "event_day": pd.to_numeric(m["entry.eventDay"], errors="coerce")})
    out["rnd"] = [(ST_QUAL if qq else ST_MAIN).get(str(r)) for r, qq in zip(out["round_name"], q)]
    out["walkover"] = out["status"].eq("F")
    out["played"] = out["status"].isin(["D", "E"])
    return out


def run() -> dict:
    s0 = K.stage0()
    frames = [ausopen(), slamtracker("wimbledon"), slamtracker("usopen")]
    rows = pd.concat(frames, ignore_index=True)
    rows["tour"] = [EVENTS[s][e][0] for s, e in zip(rows["site"], rows["event"])]
    rows["qual"] = [EVENTS[s][e][1] for s, e in zip(rows["site"], rows["event"])]
    zone = rows["site"].map(ZONE)
    # the day: first point in the venue's zone; else the AO's listed local date; else the US Open 2022-25 draw epoch
    rows["day_fp"] = K.local_day(rows["t0"], zone)
    usend = rows["site"].eq("usopen") & rows["year"].between(2022, 2025) & rows["t0"].isna() & rows["end_ts"].notna()
    rows["day_end"] = K.local_day(rows["end_ts"].where(usend), zone)
    rows["day"] = rows["day_fp"].fillna(rows["listed_day"]).fillna(rows["day_end"])
    rows["time_basis"] = np.select([rows["day_fp"].notna(), rows["listed_day"].notna(), rows["day_end"].notna()],
                                   ["first_point", "listed_local_date", "draw_end_time"], "none")
    rows.loc[rows["time_basis"].eq("first_point") & rows.get("t0_basis", pd.Series(index=rows.index)).eq(
        "first_point_end"), "time_basis"] = "first_point_end"
    scope = rows[rows["day"].notna() & ~rows["walkover"]].copy().reset_index(drop=True)
    src = scope[["sid", "tour", "day", "p1", "p2", "sets", "rnd", "qual", "id1", "id2"]].assign(tid=None)
    sl = s0[(s0["level"] == "GS") & (s0["tdate"] >= "2018-12-01")]
    K.log(f"[slam_feeds] {len(src):,} singles matches with a day to link")
    res = K.link(src, sl)
    lk = res["links"].merge(scope, on="sid", how="left")
    spans = (K.local_day(lk["t1"], lk["site"].map(ZONE)) - lk["day_fp"]).dt.days
    jump = lk["day_jump"].fillna(False).astype(bool) if "day_jump" in lk else pd.Series(False, index=lk.index)
    out = pd.DataFrame({
        "match_id": lk["match_id"], "source_key": lk["sid"], "date_local": lk["day"],
        "start_utc": lk["t0"], "date_basis": "local",
        "link_method": ("identity_" + lk["pass"] + ";" + lk["site"] + ";" + lk["time_basis"]
                        + np.where(spans.fillna(0) > 0, ";last_point_day+" + spans.fillna(0).astype(int).astype(str), "")
                        + np.where(jump, ";feed_day_jump", "")),
        "score_agrees": lk["sc"], "round_agrees": lk["rd"].map(K.rd_bool)})
    path = K.write_links(out, SOURCE)
    reason = res["reason"]
    diag = src.assign(reason=src["sid"].map(reason))
    diag = diag[diag["reason"] != "linked"].copy()
    diag["candidates"] = diag["sid"].map(lambda s: ";".join(res["ambiguous"].get(s, [])))
    diag["sets"] = diag["sets"].map(lambda t: " ".join(f"{a}-{b}" for a, b in t))
    K.write_diagnostics(diag.drop(columns=["id1", "id2"]), SOURCE)
    return summary(rows, scope, src, res, out, lk, path)


def summary(rows, scope, src, res, out, lk, path) -> dict:
    reason = res["reason"]
    # checks: AO listed local date against the first point's Melbourne day; SlamTracker day numbers against days
    ao = rows[rows["site"].eq("ausopen") & rows["day_fp"].notna() & rows["listed_day"].notna()]
    st = rows[rows["site"].isin(["wimbledon", "usopen"]) & rows["day_fp"].notna()].copy()
    mode = st.groupby(["site", "year", "event_day"])["day_fp"].agg(lambda x: x.mode().iloc[0])
    st["mode_day"] = pd.MultiIndex.from_frame(st[["site", "year", "event_day"]]).map(mode)
    dev = (st["day_fp"] - st["mode_day"]).dt.days
    return {
        "source": SOURCE, "file": str(path.relative_to(K.ROOT)),
        "method": "identity (srcc_common.link; tour ids for the id pass) against Stage 0's Grand Slam matches from Dec "
                  "2018; day = the first point's local day (Melbourne, London, New York); AO archived draws: listed local "
                  "date; US Open 2022-25 without points: the draw epoch's day (match end)",
        "rows_read": int(len(rows)), "rows_by_site_year": rows.groupby(["site", "year"]).size().rename("rows")
                                                         .reset_index().to_dict("records"),
        "singles_with_a_day": int(len(src)),
        "without_a_day_or_walkover": int(len(rows) - len(scope)),
        "linked": int(len(out)),
        "ambiguous": int(reason.str.startswith("ambiguous").sum()),
        "unlinked": int(len(src) - len(out) - reason.str.startswith("ambiguous").sum()),
        "outcomes": K.outcome_counts(reason),
        "linked_by_pass": lk["pass"].value_counts().to_dict(),
        "linked_by_site_time_basis": lk.groupby(["site", "time_basis"]).size().rename("links").reset_index()
                                       .to_dict("records"),
        "unlinked_by_site_year": diag_counts(src, reason),
        "with_start_utc": int(out["start_utc"].notna().sum()),
        "score_agrees": out["score_agrees"].value_counts(dropna=False).rename(str).to_dict(),
        "round_agrees": out["round_agrees"].value_counts(dropna=False).rename(str).to_dict(),
        "check_ao_listed_date_vs_first_point_day": {"matches": int(len(ao)),
                                                    "same": int((ao["listed_day"] == ao["day_fp"]).sum()),
                                                    "differences": (ao["day_fp"] - ao["listed_day"]).dt.days
                                                    .value_counts().sort_index().to_dict()},
        "check_slamtracker_day_vs_event_day": {"matches": int(len(st)), "on_their_event_day's_usual_date":
                                               int((dev == 0).sum()),
                                               "differences": dev[dev != 0].value_counts().sort_index().to_dict(),
                                               "note": "eventDay is the draw's day number; a match started on another "
                                                       "date than most matches of its day number was put back or "
                                                       "resumed"},
    }


def diag_counts(src, reason) -> list:
    d = src.assign(r=src["sid"].map(reason), site=src["sid"].str.split(":").str[0],
                   year=src["sid"].str.split(":").str[1].str[:4])
    d = d[d["r"] != "linked"]
    return d.groupby(["site", "year", "r"]).size().rename("rows").reset_index().to_dict("records")
