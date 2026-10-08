"""Source 2, wta_api: the WTA API's match lists (every WTA 1000/500/250/125, Finals and Slam edition of 2019-2026 that
the API lists, qualifying included) and the umpire's event logs, staged under data/dump/points/wta/
(src/ingest/point_sources/wta.py; docs/studies/official_point_feeds/README.md, WTA sections).

Times (observed on the staged tables, 5 Oct 2026):
    * the event log stamps every record with a millisecond UTC time ("timestamp") and the venue's wall-clock time
      ("timestamp_local"); their difference is the venue's UTC offset on that day (+10 h at Brisbane in January,
      -8 h then -7 h at Indian Wells across the March clock change). The first Point, Ace or Fault record is the
      match's first point, so its local time gives the local match day with no time-zone table at all;
    * the match list's MatchTimeStamp is when the umpire opened the match: a median 15 minutes before the first
      point (2024), hours before it when the match was put back, sometimes to the next day (Indian Wells 2024 LS085:
      opened 6 March 20:09 local, first point 7 March 14:42). The first point is therefore preferred;
    * matches without a log (2019 before April, the Slams, a few others) keep the list's time: the umpire's start
      at regular events, the order of play's scheduled time at the Slams (28% of them on the hour, 08:00, 15:00 ...;
      their start_utc is left empty and only the day is used). Their offset is that of the same edition's logged
      match nearest in time, else the zone of the calendar's city (srcc_tz), else the UTC day is kept.
Walkovers have no first point; their list time gives the day, flagged in link_method, with no start time.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.eda.match_timing import srcc_common as K
from src.eda.match_timing import srcc_tz as TZ

SOURCE = "wta_api"
WTA = K.DUMP / "points" / "wta"
YEARS = range(2019, 2027)
SCORE_COLS = [f"ScoreSet{k}{s}" for k in range(1, 6) for s in "AB"]
MCOLS = ["tournament_id", "match_id", "tier", "draw", "walkover", "RoundID", "MatchState", "DateSeq", "MatchTimeStamp",
         "Winner", "events_status", "PlayerIDA", "PlayerNameFirstA", "PlayerNameLastA", "PlayerIDB",
         "PlayerNameFirstB", "PlayerNameLastB"] + SCORE_COLS
SINGLES = ("main_singles", "qual_singles")
MAIN_ROUNDS = {"Q": "QF", "S": "SF", "F": "F", "G": "RR"}


OPTIONAL = ["isEstimatedStartTime"]     # staged from 5 Oct 2026 (src/ingest/point_sources/wta.py); older files lack it


def read(table: str, year: int, cols: list[str]) -> pd.DataFrame:
    """A staged per-year table; these files hold a second 'year' column, so columns are always named. OPTIONAL
    columns are read where the file has them."""
    path = WTA / table / f"{year}.parquet"
    have = set(pq.read_schema(path).names)
    return pq.read_table(path, columns=cols + [c for c in OPTIONAL if c in have and c not in cols]).to_pandas()


def first_points(year: int) -> pd.DataFrame:
    """Per match of the year's logs: the first and last Point/Ace/Fault record (UTC), the venue offset in minutes
    (timestamp_local - timestamp) at the first, and the number of such records."""
    ev = read("events", year, ["tournament_id", "match_id", "name", "timestamp", "timestamp_local"])
    ev = ev[ev["name"].isin(["Point", "Ace", "Fault"])]
    ts = pd.to_datetime(ev["timestamp"], utc=True, format="ISO8601", errors="coerce")
    tl = pd.to_datetime(ev["timestamp_local"].str.replace(r"(Z|[+-]\d\d:?\d\d)$", "", regex=True),
                        format="ISO8601", errors="coerce")
    ev = ev.assign(ts=ts, tl=tl).dropna(subset=["ts"])
    g = ev.groupby(["tournament_id", "match_id"])
    i = g["ts"].idxmin()
    f = ev.loc[i, ["tournament_id", "match_id", "ts", "tl"]].reset_index(drop=True)
    f["offset_min"] = ((f["tl"] - f["ts"].dt.tz_convert(None)).dt.total_seconds() / 60).round()
    f.loc[(f["offset_min"] % 15 != 0) | (f["offset_min"].abs() > 14 * 60), "offset_min"] = np.nan
    last = g["ts"].max().rename("last_ts").reset_index()
    n = g.size().rename("n_point_records").reset_index()
    return f.merge(last, on=["tournament_id", "match_id"]).merge(n, on=["tournament_id", "match_id"]).assign(year=year)


def editions() -> pd.DataFrame:
    e = pq.read_table(WTA / "editions.parquet", columns=["tournament_id", "year", "tier", "city", "country",
                                                          "start_date", "end_date", "live_scoring_id"]).to_pandas()
    e["year"] = e["year"].astype(int)
    e["zone"] = [edition_zone(ci, co) for ci, co in zip(e["city"], e["country"])]
    return e.drop_duplicates(["tournament_id", "year"])


def edition_zone(city, country) -> str | None:
    """The calendar's city and country as an IANA zone; US states are read from 'CA, UNITED STATES' forms."""
    text = f"{country or ''}"
    cc = TZ.country_code(country)
    if cc is None and re.search(r"united states|usa", text, re.I):
        cc = "USA"
    if cc == "USA":
        m = re.search(r"\b([A-Z]{2})\b", f"{text.upper().replace('USA', '')} {str(city or '').upper()}")
        st = m.group(1) if m else None
        city_part = re.sub(r",\s*[A-Z]{2}$", "", str(city or ""))
        return TZ.STATE_TZ.get(st) if st in TZ.STATE_TZ else TZ.zone_for("USA", city_part)
    if city and "+" in str(city):
        return None
    return TZ.zone_for(cc, city)


def round_of(draw: str, rid) -> str | None:
    r = "" if rid is None or (isinstance(rid, float) and np.isnan(rid)) else str(rid).strip()
    if draw == "qual_singles":
        return f"Q{r}" if r in ("1", "2", "3", "4") else "Q?"
    if r in MAIN_ROUNDS:
        return MAIN_ROUNDS[r]
    return f"N{r}" if r in ("1", "2", "3", "4", "5") else None


def load() -> tuple[pd.DataFrame, dict]:
    frames, fps, counts = [], [], {}
    for y in YEARS:
        m = read("matches", y, MCOLS).assign(year=y)
        counts[y] = {"listed": int(len(m)), "singles": int(m["draw"].isin(SINGLES).sum())}
        frames.append(m)
        fps.append(first_points(y))
    m = pd.concat(frames, ignore_index=True)
    fp = pd.concat(fps, ignore_index=True)
    m = m.merge(fp, on=["tournament_id", "match_id", "year"], how="left")
    return m.rename(columns={"match_id": "wta_mid"}), counts


def place_offsets(m: pd.DataFrame, ed: pd.DataFrame) -> pd.DataFrame:
    """Offset (minutes) and its basis for every match: its own log, else the nearest logged match of the edition,
    else the calendar city's zone, else none."""
    m = m.copy()
    m["list_ts"] = pd.to_datetime(m["MatchTimeStamp"], utc=True, format="ISO8601", errors="coerce")
    m["t_ref"] = m["ts"].fillna(m["list_ts"])
    m["zone_basis"] = np.where(m["offset_min"].notna(), "log_offset", "")
    need = m["offset_min"].isna() & m["t_ref"].notna()
    logged = m[m["offset_min"].notna()][["tournament_id", "year", "ts", "offset_min"]]
    by_ed = {k: g.sort_values("ts") for k, g in logged.groupby(["tournament_id", "year"])}
    for i in m.index[need]:
        g = by_ed.get((m.at[i, "tournament_id"], m.at[i, "year"]))
        if g is None or g.empty:
            continue
        j = (g["ts"] - m.at[i, "t_ref"]).abs().idxmin()
        m.at[i, "offset_min"] = g.at[j, "offset_min"]
        m.at[i, "zone_basis"] = "edition_offset"
    m = m.merge(ed[["tournament_id", "year", "zone", "city", "country", "start_date", "live_scoring_id"]].astype(
        {"tournament_id": str}), on=["tournament_id", "year"], how="left")
    return m


def run() -> dict:
    s0 = K.stage0()
    m, counts = load()
    ed = editions()
    m = place_offsets(m, ed)
    single = m["draw"].isin(SINGLES)
    played = m["MatchState"].eq("F") | m["ts"].notna()
    sc = m[single & played].copy().reset_index(drop=True)
    walk = sc["walkover"].astype(str).str.upper().eq("TRUE")
    # the time of the day: first point, else the list's time
    sc["t_use"] = sc["ts"].where(~walk).fillna(sc["list_ts"])
    # a list time is the order of play's schedule where the API flags it as estimated (staged from 5 Oct 2026), else,
    # for older files, at the Slams
    flag = sc["isEstimatedStartTime"] if "isEstimatedStartTime" in sc else pd.Series(None, index=sc.index, dtype=object)
    scheduled = np.where(flag.notna(), flag.astype(str).str.upper().eq("TRUE"), sc["tier"].eq("slam"))
    sc["time_basis"] = np.where(sc["ts"].notna() & ~walk, "first_point",
                                np.where(scheduled, "listing_schedule", "listing_start"))
    # local day: the calendar city's zone (the venue's clock). The log's local stamp is the umpire device's clock,
    # set wrongly at some editions (Budapest on UTC, Canberra 2025 without daylight saving: summary check), so it is
    # used only where the city gives no zone; else the UTC day is kept
    zone_day = K.local_day(sc["t_use"], sc["zone"])
    off = pd.to_timedelta(sc["offset_min"], unit="min")
    sc["dev_day"] = (sc["t_use"].dt.tz_convert(None) + off).dt.normalize()
    sc["zone_day"] = zone_day
    last_zone = K.local_day(sc["last_ts"].where(sc["time_basis"].eq("first_point")), sc["zone"])
    last_dev = (sc["last_ts"].dt.tz_convert(None) + off).dt.normalize().where(sc["time_basis"].eq("first_point"))
    sc["last_local"] = last_zone.where(sc["zone"].notna(), last_dev)
    sc["day_local"] = zone_day.where(zone_day.notna(), sc["dev_day"])
    sc["zone_basis"] = np.where(zone_day.notna(), "city_zone",
                                np.where(sc["dev_day"].notna(), "device_" + sc["zone_basis"].astype(str), "utc"))
    # the list's day number (DateSeq) against the first point: within an edition and draw, day minus DateSeq is
    # constant when both are right. A first point two or more days from the day its day number implies is rejected
    # and the implied day taken instead, with no start time (Tianjin 2019 QF: first point stamped six days after the
    # day the list and tennis-data give). One day apart is kept: play put back or resumed past midnight.
    seq = pd.to_numeric(sc["DateSeq"], errors="coerce")
    fp = sc["time_basis"].eq("first_point") & sc["day_local"].notna() & seq.notna()
    base = (sc["day_local"] - pd.to_timedelta(seq, unit="D")).where(fp)
    grp = [sc["tournament_id"], sc["year"], sc["draw"]]
    mode = base.groupby(grp).transform(lambda x: x.mode().iloc[0] if x.notna().any() else pd.NaT)
    seq_day = mode + pd.to_timedelta(seq, unit="D")
    far = fp & ((sc["day_local"] - seq_day).dt.days.abs() >= 2)
    sc["seq_gap"] = (sc["day_local"] - seq_day).dt.days.where(far)
    sc.loc[far, "day_local"] = seq_day[far]
    sc.loc[far, "time_basis"] = "day_number"
    sc.loc[far, "last_local"] = pd.NaT
    # 2019's list times are not UTC: against the first points of the year's logged matches they run a whole number of
    # hours off, mostly by the venue's offset (local times stamped as UTC; Beijing +8 h, Seoul +9 h, New York -4 h)
    # and +6 h at five spring editions. A 2019 match without a log keeps only its label's calendar day, as a
    # UTC-basis day (uncertain by a day either way), with no start time
    lab = sc["time_basis"].isin(["listing_start", "listing_schedule"]) & sc["year"].eq(2019)
    sc.loc[lab, "day_local"] = pd.NaT
    sc.loc[lab, "time_basis"] = "listing_2019_label_day"
    sc.loc[lab, "zone_basis"] = "label"
    sc["date_basis"] = np.where(sc["day_local"].notna(), "local", "utc_date")
    sc["day"] = sc["day_local"].fillna(sc["t_use"].dt.tz_convert(None).dt.normalize())
    # the Stage 0 tournament id the edition corresponds to (WTA number, or the live-scoring id Sackmann used in 2019-20)
    w0 = s0[(s0["tour"] == "wta") & s0["level"].isin(["GS", "FIN", "T1000", "T500", "T250", "CH"])
            & (s0["tdate"] >= "2018-12-01")]
    ids = set(w0["tournament_id"])

    def hint(tid, year, lsid):
        for cand in (f"{year}-{int(tid)}" if str(tid).isdigit() else None, f"{year}-{str(tid).zfill(4)}",
                     f"{year}-{lsid}" if isinstance(lsid, str) and lsid else None):
            if cand and cand in ids:
                return cand
        return None
    sc["tid_hint"] = [hint(t, y, l) for t, y, l in zip(sc["tournament_id"], sc["year"], sc["live_scoring_id"])]
    sc["sid"] = "wta:" + sc["tournament_id"].astype(str) + "/" + sc["year"].astype(str) + "/" + sc["wta_mid"].astype(str)
    src = pd.DataFrame({
        "sid": sc["sid"], "tour": "wta", "day": sc["day"],
        "p1": (sc["PlayerNameFirstA"].fillna("") + " " + sc["PlayerNameLastA"].fillna("")).str.strip(),
        "p2": (sc["PlayerNameFirstB"].fillna("") + " " + sc["PlayerNameLastB"].fillna("")).str.strip(),
        "sets": [K.sets_from_pairs([(r[f"ScoreSet{k}A"], r[f"ScoreSet{k}B"]) for k in range(1, 6)])
                 for _, r in sc[SCORE_COLS].iterrows()],
        "rnd": [round_of(d, r) for d, r in zip(sc["draw"], sc["RoundID"])],
        "qual": sc["draw"].eq("qual_singles"), "tid": sc["tid_hint"],
        "id1": sc["PlayerIDA"].astype(str), "id2": sc["PlayerIDB"].astype(str)})
    K.log(f"[wta_api] {len(src):,} singles rows to link")
    res = K.link(src, w0)
    lk = res["links"].merge(sc, on="sid", how="left")
    walk_l = lk["walkover"].astype(str).str.upper().eq("TRUE")
    start = lk["t_use"].where(lk["time_basis"].isin(["first_point", "listing_start"]) & ~walk_l)
    spans = (lk["last_local"] - lk["day_local"]).dt.days
    method = ("identity_" + lk["pass"] + ";" + lk["time_basis"] + ";" + lk["zone_basis"] + np.where(walk_l, ";walkover", "")
              + np.where(spans.fillna(0) > 0, ";last_point_day+" + spans.fillna(0).astype(int).astype(str), "")
              + np.where(lk["tidok"].eq(1), ";tid", ""))
    out = pd.DataFrame({"match_id": lk["match_id"], "source_key": lk["sid"], "date_local": lk["day"],
                        "start_utc": start, "date_basis": lk["date_basis"], "link_method": method,
                        "score_agrees": lk["sc"], "round_agrees": lk["rd"].map(K.rd_bool)})
    path = K.write_links(out, SOURCE)
    # diagnostics: every singles row not linked, with why
    diag = src.assign(reason=src["sid"].map(res["reason"]))
    diag = diag[diag["reason"] != "linked"].copy()
    diag["candidates"] = diag["sid"].map(lambda s: ";".join(res["ambiguous"].get(s, [])))
    diag["sets"] = diag["sets"].map(lambda t: " ".join(f"{a}-{b}" for a, b in t))
    diag = diag.merge(sc[["sid", "tier", "draw", "walkover", "time_basis", "zone_basis"]], on="sid", how="left")
    K.write_diagnostics(diag, SOURCE)
    return summary(m, sc, src, res, out, counts, path, lk)


def summary(m, sc, src, res, out, counts, path, lk) -> dict:
    reason = res["reason"]
    # checks: the umpire device's offset against the calendar city's zone, and the days they give
    chk = sc[sc["offset_min"].notna() & sc["zone"].notna()].copy()
    chk["zone_off"] = [t.tz_convert(TZ.zoneinfo(z)).utcoffset().total_seconds() / 60
                       for t, z in zip(chk["t_use"], chk["zone"])]
    dis = chk[chk["zone_off"] != chk["offset_min"]]
    day_dis = chk[chk["dev_day"] != chk["zone_day"]]
    # the list's day number (DateSeq) against the day: constant within an edition and draw when both are right
    seq = pd.to_numeric(sc["DateSeq"], errors="coerce")
    d = (sc["day_local"] - pd.to_timedelta(seq, unit="D"))
    q = sc.assign(base=d).dropna(subset=["base"])
    mode = q.groupby(["tournament_id", "year", "draw"])["base"].agg(lambda x: x.mode().iloc[0])
    dev = (q["base"] - pd.MultiIndex.from_frame(q[["tournament_id", "year", "draw"]]).map(mode)).dt.days
    gap = (sc["ts"] - sc["list_ts"]).dt.total_seconds() / 60
    return {
        "source": SOURCE, "file": str(path.relative_to(K.ROOT)),
        "method": "identity (srcc_common.link): WTA, levels GS/FIN/T1000/T500/T250/CH from Dec 2018, both names, day "
                  "-10..+21 of the tournament date, set scores (the list's ScoreSet fields) and/or round (RoundID; "
                  "numbered rounds counted from the draw's first); the WTA edition number (or 2019-20 live-scoring id) "
                  "as Stage 0's tournament id ranks candidates. Day: first point of the umpire's log in the log's own "
                  "local time; else the list's time with the edition's offset or the city's zone",
        "rows_read": int(len(m)), "rows_by_year": counts,
        "singles_played_in_scope": int(len(src)),
        "singles_with_first_point": int(sc["time_basis"].eq("first_point").sum()),
        "linked": int((reason == "linked").sum()),
        "ambiguous": int(reason.str.startswith("ambiguous").sum()),
        "unlinked": int((~reason.isin(["linked"]) & ~reason.str.startswith("ambiguous")).sum()),
        "outcomes": K.outcome_counts(reason),
        "unlinked_by_tier_draw": sc.assign(r=sc["sid"].map(reason)).query("r != 'linked'")
                                   .groupby(["tier", "draw"]).size().rename("rows").reset_index().to_dict("records"),
        "linked_by_method": out["link_method"].str.replace(";tid", "", regex=False).value_counts().to_dict(),
        "linked_by_pass": lk["pass"].value_counts().to_dict(),
        "first_points_rejected_by_day_number": {
            "rows": int(sc["seq_gap"].notna().sum()),
            "first_point_minus_implied_day": sc["seq_gap"].dropna().astype(int).value_counts().sort_index().to_dict(),
            "rows_list": sc.loc[sc["seq_gap"].notna(), ["sid", "seq_gap"]].astype(str).to_dict("records")},
        "player_id_crosswalk_size": len(res["crosswalk"]),
        "linked_with_tournament_id_agreeing": int(lk["tidok"].eq(1).sum()),
        "linked_with_tournament_id_disagreeing": int(lk["tidok"].eq(-1).sum()),
        "date_basis": out["date_basis"].value_counts().to_dict(),
        "with_start_utc": int(out["start_utc"].notna().sum()),
        "score_agrees": out["score_agrees"].value_counts(dropna=False).rename(str).to_dict(),
        "round_agrees": out["round_agrees"].value_counts(dropna=False).rename(str).to_dict(),
        "name_grades": lk.groupby(["q1", "q2"]).size().rename("links").reset_index().to_dict("records"),
        "check_device_offset_vs_city_zone": {"matches_checked": int(len(chk)), "disagree": int(len(dis)),
                                          "disagreeing_editions": dis.groupby(["tournament_id", "year", "city", "country"])
                                          .agg(matches=("offset_min", "size"), log_offset_min=("offset_min", "first"),
                                               zone_offset_min=("zone_off", "first")).reset_index().head(30)
                                          .to_dict("records")},
        "check_device_days_vs_city_zone_days": {"matches": int(len(chk)), "different_day": int(len(day_dis)),
                                                "by_edition": day_dis.groupby(["tournament_id", "year", "city"]).size()
                                                .rename("matches").reset_index().head(40).to_dict("records")},
        "check_day_vs_list_day_number": {"matches": int(len(dev)), "consistent_with_edition_and_draw": int((dev == 0).sum()),
                                         "differences_days": dev[dev != 0].value_counts().sort_index().to_dict(),
                                         "note": "DateSeq is the list's day number; within an edition and draw, day minus "
                                                 "DateSeq should be constant. A difference is a match put back to another "
                                                 "day, or a wrong day on one side"},
        "first_point_minus_list_time_minutes": {str(k): round(float(v), 1) for k, v in
                                                gap.dropna().quantile([0.01, 0.05, 0.5, 0.95, 0.99]).items()},
        "first_point_more_than_6h_after_list_time": int((gap > 360).sum()),
    }
