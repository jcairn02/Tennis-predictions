"""Loaders for the six match-timing sources of link_sources_b.py, each as one frame in a common layout.

Common columns (one row per source match, RangeIndex ri):
    source_key   the source's own id for the row (str)
    tour         'atp' or 'wta'
    date         naive calendar day used for the -10..+21 day window (the source's date, or the UTC day)
    start_utc    tz-aware UTC start where the source gives a time (NaT otherwise)
    name1/name2  the two players as written; f1/f2 full-name keys; a1/a2 tuples of abbreviated keys
    i1/i2        Stage 0 player ids where the source has a crosswalk ('' otherwise)
    pid1/pid2    the source's own player ids (for ids learned from links)
    sets         set scores in the source's player order, () if none
    rspec        the round as srcb_common.round_spec alternatives
Each loader also returns a dict of counts (rows read, rows left out and why).

Read-only: raw files under data/raw/public_dump/ and staged files under data/dump/.
"""
from __future__ import annotations

import gzip
import json
import re
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from src.eda.match_timing import srcb_common as X
from src.eda.merge_feasibility import scan as S
from src.eda.predictability_diagnostic import common as C
from src.ingest.public_dump import live_tennis_api_zenodo as LTA

HANDOFF = X.RAW / "atp_pipeline_handoff"
API_TYPES = ("Atp Singles", "Challenger Men Singles", "Itf Men Singles")
# api-tennis.com's documented default zone for event_date / event_time; the handoff does not say which
# zone its fetcher asked for, so this is checked against tennis-data and the Live Tennis API in the summary
API_TZ = "Europe/Berlin"
# Live Tennis API v1.0.0 'scheduled_time_utc' was written in Israel local time (Zenodo v1.0.2 note,
# 28 Sep 2026, docs/research/gap-sources/README.md); checked in the summary. v1.0.2, staged since 8 Oct 2026,
# holds the same rows in UTC: lta_zone() reads which version the staged index is.
LTA_TZ = "Asia/Jerusalem"
LTA_MATCHES = X.DUMP / "matches" / "live_tennis_api_zenodo" / "matches.parquet"


def lta_zone() -> str:
    """The zone the staged index's 'scheduled_time_utc' is written in: Asia/Jerusalem (v1.0.0) or UTC (v1.0.2)."""
    return LTA.staged_time_zone(LTA_MATCHES)
LTA_TIERS = {"265": "atp", "265_inferred": "atp", "270": "atp", "281": "atp",
             "266": "wta", "266_inferred": "wta", "271": "wta", "272": "wta"}


def _finish(f: pd.DataFrame) -> pd.DataFrame:
    """Common columns, keys, a RangeIndex."""
    f = f.reset_index(drop=True)
    for c in ("i1", "i2", "pid1", "pid2"):
        if c not in f:
            f[c] = ""
    f["f1"], f["f2"] = f["name1"].map(X.full_key), f["name2"].map(X.full_key)
    if "a1" not in f:
        f["a1"], f["a2"] = f["name1"].map(X.abbr_from_full), f["name2"].map(X.abbr_from_full)
    if "start_utc" not in f:
        f["start_utc"] = pd.Series(pd.NaT, index=f.index, dtype="datetime64[ns, UTC]")
    f["date"] = pd.to_datetime(f["date"]).astype("datetime64[ns]")
    return f


def to_utc(local: pd.Series, zone: str) -> tuple[pd.Series, int]:
    """Naive local wall-clock times in ``zone`` as UTC. A time in the hour repeated when clocks go back
    is read as summer time (one hour's doubt, counted and returned)."""
    strict = local.dt.tz_localize(zone, ambiguous="NaT", nonexistent="shift_forward")
    doubtful = int((strict.isna() & local.notna()).sum())
    utc = local.dt.tz_localize(zone, ambiguous=np.ones(len(local), dtype=bool), nonexistent="shift_forward")
    return utc.dt.tz_convert("UTC"), doubtful


# ------------------------------------------------------------------------------------------------
# 1. api_tennis (Hugging Face handoff): men's ATP, Challenger and ITF fixtures 2021-2024

def api_sets(js) -> tuple:
    try:
        v = json.loads(js) if isinstance(js, str) and js.startswith("[") else []
        v = sorted(v, key=lambda d: int(d.get("score_set", 0)))
        out = tuple((int(str(d["score_first"]).split(".")[0]), int(str(d["score_second"]).split(".")[0])) for d in v)
        return out
    except (ValueError, KeyError, TypeError, AttributeError):
        return ()


def load_api_tennis() -> tuple[pd.DataFrame, dict]:
    frames = []
    for p in sorted((HANDOFF / "api_tennis").glob("fixtures_*.csv*")):
        df = pd.read_csv(p, dtype=str, keep_default_na=False, low_memory=False)
        frames.append(df.assign(_file=p.name, _row=np.arange(1, len(df) + 1)))
    f = pd.concat(frames, ignore_index=True)
    info = {"files": sorted({p for p in f["_file"]}), "rows_read": int(len(f)), "left_out": {}}
    lo = info["left_out"]
    single = f["event_type_type"].isin(API_TYPES)
    lo["doubles_team_ties_or_malformed_type"] = int((~single).sum())
    f = f[single]
    day = pd.to_datetime(f["event_date"], format="%Y-%m-%d", errors="coerce")
    lo["unreadable_date"] = int(day.isna().sum())
    f, day = f[day.notna()], day[day.notna()]
    dup = f["event_key"].duplicated()
    lo["duplicate_event_key_identical_copy"] = int(dup.sum())
    f, day = f[~dup], day[~dup]
    slash = f["event_first_player"].str.contains("/") | f["event_second_player"].str.contains("/")
    lo["doubles_names_in_singles"] = int(slash.sum())
    f, day = f[~slash], day[~slash]
    cancelled = f["event_status"].eq("Cancelled")
    lo["cancelled"] = int(cancelled.sum())
    f, day = f[~cancelled], day[~cancelled]
    info["status_kept"] = f["event_status"].replace("", "(blank)").value_counts().to_dict()
    local = pd.to_datetime(f["event_date"] + " " + f["event_time"], format="%Y-%m-%d %H:%M", errors="coerce")
    utc, amb = to_utc(local, API_TZ)
    info["rows_without_time"] = int(local.isna().sum())
    info["times_in_repeated_dst_hour_read_as_summer_time"] = amb
    qual = f["event_qualification"].map({"True": True, "False": False})
    out = pd.DataFrame({
        "source_key": f["event_key"].to_numpy(), "tour": "atp", "date": day.to_numpy(),
        "start_utc": utc.reset_index(drop=True), "local_naive": local.reset_index(drop=True),
        "name1": f["event_first_player"].to_numpy(), "name2": f["event_second_player"].to_numpy(),
        "pid1": f["first_player_key"].to_numpy(), "pid2": f["second_player_key"].to_numpy(),
        "sets": f["scores_json"].map(api_sets).to_numpy(),
        "rspec": [X.round_spec(r, (None if pd.isna(q) else bool(q))) for r, q in zip(f["tournament_round"], qual)],
        "status": f["event_status"].to_numpy(), "kind": f["event_type_type"].to_numpy(),
        "tournament": f["tournament_name"].to_numpy()})
    out["a1"] = out["name1"].map(lambda n: tuple(k for k in [X.abbr_short(n)] if k) or X.abbr_from_full(n))
    out["a2"] = out["name2"].map(lambda n: tuple(k for k in [X.abbr_short(n)] if k) or X.abbr_from_full(n))
    out = _finish(out)
    # an abbreviated name is not a full name: its 'F:' key would read 'o otte'
    abbreviated1 = out["name1"].map(lambda n: X.abbr_short(n) != "")
    abbreviated2 = out["name2"].map(lambda n: X.abbr_short(n) != "")
    out.loc[abbreviated1, "f1"] = ""
    out.loc[abbreviated2, "f2"] = ""
    info["rows_in_scope"] = int(len(out))
    return out, info


# ------------------------------------------------------------------------------------------------
# 2. live_tennis_api (Zenodo, staged: v1.0.0 until 8 Oct 2026, then v1.0.2): match index Jan 2023 - 13 Aug 2026,
#    every level

def compatible(a, b) -> bool:
    """Two spellings of one player: equal full keys, or one's last word is a word of the other."""
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    if X.full_key(a) and X.full_key(a) == X.full_key(b):
        return True
    wa, wb = S.norm(a).split(), S.norm(b).split()
    return bool(wa and wb and (wa[-1] in wb or wb[-1] in wa))


def load_lta(s0_names: pd.Series) -> tuple[pd.DataFrame, dict]:
    lm = pd.read_parquet(LTA_MATCHES)
    lp = pd.read_parquet(X.DUMP / "players" / "live_tennis_api_zenodo" / "players.parquet",
                         columns=["player_id", "name", "tour", "sackmann_id", "birthday"])
    info = {"rows_read": int(len(lm)), "left_out": {}}
    lo = info["left_out"]
    ptour = dict(zip(lp["player_id"], lp["tour"]))
    tour = lm["tier_key"].map(LTA_TIERS)
    t1, t2 = lm["player1_id"].map(ptour), lm["player2_id"].map(ptour)
    untiered = lm["tier_key"].eq("") & t1.isin(["atp", "wta"]) & t1.eq(t2)
    tour = tour.where(tour.notna(), t1.where(untiered))
    lo["doubles_juniors_utr_or_unknown_tier"] = int(tour.isna().sum())
    keep = tour.notna()
    names = dict(zip(lp["player_id"], lp["name"]))
    n1, n2 = lm["player1_id"].map(names), lm["player2_id"].map(names)
    slash = n1.fillna("").str.contains("/") | n2.fillna("").str.contains("/")
    lo["doubles_names"] = int((keep & slash).sum())
    keep &= ~slash
    cancelled = lm["event_status"].eq("Cancelled")
    lo["cancelled"] = int((keep & cancelled).sum())
    keep &= ~cancelled
    local = pd.to_datetime(lm["scheduled_time_utc"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    lo["unreadable_time"] = int((keep & local.isna()).sum())
    keep &= local.notna()
    lm, tour, n1, n2, local = lm[keep], tour[keep], n1[keep], n2[keep], local[keep]
    zone = lta_zone()
    utc, amb = to_utc(local, zone)
    info["scheduled_time_utc_read_as"] = zone
    info["times_in_repeated_dst_hour_read_as_summer_time"] = amb
    if zone == LTA_TZ:
        shift = ((local - utc.dt.tz_localize(None)) / pd.Timedelta(hours=1)).round()
        info["hours_moved_back_israel_to_utc"] = {str(int(k)): int(v) for k, v in shift.value_counts().items()}
    # Sackmann crosswalk, kept only where Stage 0 knows the id under a compatible name
    sid = lp.set_index("player_id")["sackmann_id"].fillna("")
    stour = lp.set_index("player_id")["tour"]

    def mapped(pid, tr, name):
        s = sid.get(pid, "")
        if not s:
            return "", "none"
        cand = f"{tr}:{s}"
        known = s0_names.get(cand)
        if known is None:
            return "", "id_not_in_stage0"
        return (cand, "ok") if compatible(name, known) else ("", "name_disagrees")

    m1 = [mapped(p, t, n) for p, t, n in zip(lm["player1_id"], tour, n1)]
    m2 = [mapped(p, t, n) for p, t, n in zip(lm["player2_id"], tour, n2)]
    qual = lm["is_qualifying"].map({"True": True, "False": False})
    out = pd.DataFrame({
        "source_key": lm["match_id"].to_numpy(), "tour": tour.to_numpy(),
        "date": utc.dt.tz_localize(None).dt.normalize().reset_index(drop=True),
        "start_utc": utc.reset_index(drop=True),
        "local_naive": local.reset_index(drop=True), "name1": n1.to_numpy(), "name2": n2.to_numpy(),
        "pid1": lm["player1_id"].to_numpy(), "pid2": lm["player2_id"].to_numpy(),
        "i1": [a for a, _ in m1], "i2": [a for a, _ in m2], "sets": [()] * len(lm),
        "rspec": [X.round_spec(r, (None if pd.isna(q) else bool(q))) for r, q in zip(lm["round"], qual)],
        "tier": lm["tier_key"].to_numpy(), "status": lm["event_status"].to_numpy(),
        "tournament": lm["tournament"].to_numpy()})
    out["date"] = out["date"].fillna(local.dt.normalize().reset_index(drop=True))
    xw = pd.Series([s for _, s in m1] + [s for _, s in m2]).value_counts().to_dict()
    info["sackmann_crosswalk_player_slots"] = {k: int(v) for k, v in xw.items()}
    out = _finish(out)
    info["rows_in_scope"] = int(len(out))
    return out, info


# ------------------------------------------------------------------------------------------------
# 3. open_tennis_data (staged release data-v3-20260905T083014Z): main-tour results 2020 - 29 Aug 2026

def first_of(js) -> str:
    v = S.parse_list(js)
    return str(v[0]) if v else ""


def load_otd() -> tuple[pd.DataFrame, dict]:
    o = pd.read_parquet(X.DUMP / "matches" / "open_tennis_data" / "completed.parquet")
    info = {"rows_read": int(len(o)), "left_out": {}, "release": str(o["_release_tag"].iloc[0])}
    day = pd.to_datetime(o["date"], format="%Y-%m-%d", errors="coerce")
    info["left_out"]["unreadable_date"] = int(day.isna().sum())
    o, day = o[day.notna()], day[day.notna()]
    id1, id2 = o["player1_id"].map(first_of), o["player2_id"].map(first_of)
    sack = r"^(?:atp|wta):\d+$"
    info["player_slots_without_sackmann_id"] = int((~id1.str.match(sack)).sum() + (~id2.str.match(sack)).sum())
    out = pd.DataFrame({
        "source_key": o["match_id"].to_numpy(), "tour": o["tour"].to_numpy(), "date": day.to_numpy(),
        "name1": o["player1_name"].map(first_of).to_numpy(), "name2": o["player2_name"].map(first_of).to_numpy(),
        "i1": id1.where(id1.str.match(sack), "").to_numpy(), "i2": id2.where(id2.str.match(sack), "").to_numpy(),
        "pid1": id1.to_numpy(), "pid2": id2.to_numpy(),
        "sets": o["score"].map(X.sets_of_score).to_numpy(),
        "rspec": [X.round_spec(r, False if r != "Qualifying competition" else True) for r in o["round"]],
        "status": o["status"].to_numpy(), "tournament": o["tournament_name"].to_numpy(),
        "provenance": o["source"].to_numpy()})
    out = _finish(out)
    info["rows_in_scope"] = int(len(out))
    return out, info


# ------------------------------------------------------------------------------------------------
# 4. match_charting (Match Charting Project metadata, staged)

MCP_TIME = re.compile(r"^(\d{1,2})(?:[:.h](\d{2}))?\s*([ap])\.?\s*m\.?$|^(\d{1,2})[:.h](\d{2})$", re.I)


def mcp_clock(text) -> tuple | None:
    """'3pm', '11:10 AM', '15:00' -> (hour, minute); 24-hour times before 09:00 are left out (am or pm?)."""
    s = str(text or "").strip().lower().replace(" ", "")
    m = MCP_TIME.match(s)
    if not m:
        return None
    if m.group(3):
        h, mi = int(m.group(1)), int(m.group(2) or 0)
        if not 1 <= h <= 12 or mi > 59:
            return None
        h = (h % 12) + (12 if m.group(3) == "p" else 0)
        return h, mi
    h, mi = int(m.group(4)), int(m.group(5))
    if h > 23 or mi > 59 or h < 9:
        return None
    return h, mi


def load_mcp() -> tuple[pd.DataFrame, dict]:
    frames = []
    for g, tour in (("m", "atp"), ("w", "wta")):
        m = pd.read_parquet(X.DUMP / "points" / "match_charting_project" / "metadata" / f"charting-{g}-matches.parquet")
        frames.append(m.assign(tour=tour))
    m = pd.concat(frames, ignore_index=True)
    info = {"rows_read": int(len(m)), "left_out": {}}
    # rows whose fields shifted (short rows): date, round and players from the match id
    short = m["_width_ok"].ne("ok")
    parts = m.loc[short, "match_id"].str.split("-")
    ok6 = parts.str.len() == 6
    for col, k in (("Date", 0), ("Tournament", 2), ("Round", 3), ("Player 1", 4), ("Player 2", 5)):
        vals = parts[ok6].str[k]
        if col in ("Tournament", "Player 1", "Player 2"):
            vals = vals.str.replace("_", " ")
        m.loc[vals.index, col] = vals
    m.loc[short & ~short.index.isin(parts[ok6].index), "Date"] = ""
    info["short_rows_read_from_match_id"] = int(ok6.sum())
    day = pd.to_datetime(m["Date"], format="%Y%m%d", errors="coerce")
    info["left_out"]["unreadable_date"] = int(day.isna().sum())
    early = day < pd.Timestamp(f"{C.FIRST_YEAR - 1}-12-01")
    info["left_out"]["before_december_2009"] = int(early.sum())
    keep = day.notna() & ~early
    m, day = m[keep], day[keep]
    rnd = m["Round"].fillna("").str.strip()
    qual = rnd.str.match(r"^Q\d$")
    out = pd.DataFrame({
        "source_key": m["match_id"].to_numpy(), "tour": m["tour"].to_numpy(), "date": day.to_numpy(),
        "name1": m["Player 1"].to_numpy(), "name2": m["Player 2"].to_numpy(), "sets": [()] * len(m),
        "rspec": [X.round_spec(r, bool(q)) for r, q in zip(rnd, qual)],
        "clock": m["Time"].map(mcp_clock).to_numpy(), "time_text": m["Time"].fillna("").to_numpy(),
        "tournament": m["Tournament"].to_numpy()})
    info["time_field_filled"] = int((out["time_text"].str.strip() != "").sum())
    info["time_field_read_as_clock"] = int(out["clock"].notna().sum())
    out = _finish(out)
    info["rows_in_scope"] = int(len(out))
    return out, info


# ------------------------------------------------------------------------------------------------
# 5. infosys (Hugging Face handoff): ATP Stats Centre records 2021-2024, infosys_deep and infosys_full

def _infosys_file(path: str) -> list[dict]:
    """One dict per record of one file (run in a worker process)."""
    p = Path(path)
    opener = gzip.open if p.suffix == ".gz" else open
    rows = []
    with opener(p, "rt", encoding="utf-8", errors="replace") as fh:
        for n, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                rows.append({"folder": p.parent.name, "file": p.name, "line": n, "bad_json": True})
                continue
            ms = r.get("match_status") or {}
            pdx = ms.get("playerData") or {}
            rows.append({
                "folder": p.parent.name, "file": p.name, "line": n, "bad_json": False,
                "year": r.get("year"), "tournament_id": r.get("tournament_id"), "code": r.get("match_id"),
                "match_date": r.get("match_date"), "status_date": ms.get("matchDate"),
                "name1": r.get("player1_name"), "name2": r.get("player2_name"),
                "id1": r.get("player1_id"), "id2": r.get("player2_id"),
                "first1": pdx.get("tm1Ply1FirstName"), "last1": pdx.get("tm1Ply1LastName"),
                "first2": pdx.get("tm2Ply1FirstName"), "last2": pdx.get("tm2Ply1LastName"),
                "partner1": pdx.get("tm1Ply2Id"), "partner2": pdx.get("tm2Ply2Id"),
                "winner": ms.get("matchWinner"), "status": ms.get("matchStatus"),
                "sets_completed": r.get("sets_completed")})
    return rows


def read_infosys(workers: int = 3) -> pd.DataFrame:
    paths = sorted(str(p) for d in ("infosys_deep", "infosys_full") for p in (HANDOFF / d).glob("*_data.jsonl*"))
    paths.sort(key=lambda s: -Path(s).stat().st_size)      # biggest first
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for part in ex.map(_infosys_file, paths):
            rows.extend(part)
    return pd.DataFrame(rows)


def infosys_round(code: str) -> str:
    """ATP match numbers count back from the final: MS001 final, MS002-003 semi-finals, MS004-007
    quarter-finals ...; a round robin's matches are numbered after the semi-finals, hence 'RR?'."""
    m = re.match(r"^([MQ])S(\d+)$", str(code or ""))
    if not m:
        return ""
    if m.group(1) == "Q":
        return "Q"
    n = int(m.group(2))
    for hi, r in ((1, "F"), (3, "SF"), (7, "QF"), (15, "R16"), (31, "R32"), (63, "R64"), (127, "R128")):
        if n <= hi:
            return r if n <= 3 else r + "|RR?"
    return "RR?"


def atp_code(v) -> str:
    s = str(v or "").strip().upper()
    if len(s) > 4 and s.startswith("ATP"):
        s = s[3:]
    return s


def load_infosys(code_to_id: pd.Series, workers: int = 3) -> tuple[pd.DataFrame, dict]:
    raw = read_infosys(workers)
    info = {"records_read": int(len(raw)), "records_by_folder": raw["folder"].value_counts().to_dict(),
            "left_out": {}}
    lo = info["left_out"]
    lo["unreadable_json"] = int(raw["bad_json"].sum())
    r = raw[~raw["bad_json"]].copy()
    r["code"] = r["code"].astype(str)
    singles = r["code"].str.match(r"^[MQ]S\d+$")
    lo["doubles_or_other_codes"] = int((~singles).sum())
    r = r[singles]
    r["year"] = pd.to_numeric(r["year"], errors="coerce")
    old = ~r["year"].between(2010, 2026)
    lo["no_season_1970_file"] = int(old.sum())
    r = r[~old]
    r["key"] = r["year"].astype(int).astype(str) + "_" + r["tournament_id"].astype(str) + "_" + r["code"]
    # infosys_deep and infosys_full hold most matches twice: one row per match, both dates kept
    both = r.groupby("key").agg(n=("folder", "size"), dates=("match_date", lambda s: tuple(sorted(set(s.dropna())))),
                                folders=("folder", lambda s: ",".join(sorted(set(s)))))
    info["matches"] = int(len(both))
    info["matches_by_folders"] = both["folders"].value_counts().to_dict()
    info["matches_whose_two_records_disagree_on_date"] = int((both["dates"].map(len) > 1).sum())
    info["records_whose_status_date_differs"] = int((r["match_date"] != r["status_date"]).sum())
    r = r.sort_values(["key", "folder"]).drop_duplicates("key", keep="first")   # infosys_deep first
    r["dates"] = r["key"].map(both["dates"])
    day = pd.to_datetime(r["match_date"], format="%Y-%m-%d", errors="coerce")
    c1, c2 = r["id1"].map(atp_code), r["id2"].map(atp_code)
    i1 = c1.map(code_to_id).fillna("atpcode:" + c1).where(c1 != "", "")
    i2 = c2.map(code_to_id).fillna("atpcode:" + c2).where(c2 != "", "")
    full1 = (r["first1"].fillna("") + " " + r["last1"].fillna("")).str.strip()
    full2 = (r["first2"].fillna("") + " " + r["last2"].fillna("")).str.strip()
    out = pd.DataFrame({
        "source_key": r["key"].to_numpy(), "tour": "atp", "date": day.to_numpy(),
        "season": r["year"].astype(int).to_numpy(),
        "tnum": pd.to_numeric(r["tournament_id"], errors="coerce").fillna(-1).astype(int).to_numpy(),
        "name1": np.where(full1 != "", full1, r["name1"].fillna("")), "name2": np.where(full2 != "", full2, r["name2"].fillna("")),
        "short1": r["name1"].fillna("").to_numpy(), "short2": r["name2"].fillna("").to_numpy(),
        "pid1": c1.to_numpy(), "pid2": c2.to_numpy(), "i1": i1.to_numpy(), "i2": i2.to_numpy(),
        "sets": [()] * len(r), "rspec": r["code"].map(infosys_round).to_numpy(),
        "winner": pd.to_numeric(r["winner"], errors="coerce").to_numpy(), "status": r["status"].to_numpy(),
        "folders": r["key"].map(both["folders"]).to_numpy(), "dates": r["dates"].to_numpy()})
    out["date"] = out["date"].fillna(pd.Timestamp("1900-01-01"))   # undated: linked by event only
    out["a1"] = [tuple(k for k in [X.abbr_short(s)] if k) + X.abbr_from_full(f) for s, f in zip(out["short1"], out["name1"])]
    out["a2"] = [tuple(k for k in [X.abbr_short(s)] if k) + X.abbr_from_full(f) for s, f in zip(out["short2"], out["name2"])]
    out = _finish(out)
    info["player_slots_mapped_to_stage0_ids_by_tml_codes"] = int(c1.isin(code_to_id.index).sum() + c2.isin(code_to_id.index).sum())
    info["player_slots"] = int(2 * len(out))
    info["rows_in_scope"] = int(len(out))
    info["statuses"] = out["status"].fillna("(none)").value_counts().to_dict()
    return out, info


# ------------------------------------------------------------------------------------------------
# 6. tml_days (Tennis My Life, staged): rows whose date is the day the match was played

TML_GROUPS = [("atp_main", "atp_main/[0-9]*.parquet", "atp"), ("atp_challenger", "atp_challenger/*_challenger.parquet", "atp"),
              ("atp_qualifying", "atp_qualifying/*_atp_quali.parquet", "atp"), ("wta_main", "wta_main/*_wta.parquet", "wta"),
              ("atp_ongoing", "ongoing/ongoing_tourneys.parquet", "atp"),
              ("atp_challenger_ongoing", "ongoing/challenger_ongoing_tourneys.parquet", "atp"),
              ("wta_ongoing", "ongoing/wta_ongoing_tourneys.parquet", "wta")]
TML_COLS = ["tourney_id", "tourney_name", "tourney_level", "tourney_date", "round", "winner_id", "winner_name",
            "loser_id", "loser_name", "score", "_source_file", "_row"]
TML_FIRST_SEASON = 2019
MAX_ROUNDS_PER_DAY = 2          # a day-level event plays at most two rounds of singles on one day
MAX_MATCHES_PER_DAY = 34        # a Slam's first day plays 32 men's (or women's) first-round matches
MIN_SPREAD_ROUND = 12           # a round this big is played over two days or more (a round of 16 often is not)


def load_tml_rows() -> tuple[pd.DataFrame, dict]:
    frames = []
    for group, pattern, tour in TML_GROUPS:
        for f in sorted((X.DUMP / "matches" / "tennis_my_life").glob(pattern)):
            m = re.search(r"(\d{4})", f.name)
            season = int(m.group(1)) if m else None
            if season is not None and season < TML_FIRST_SEASON:
                continue
            df = pd.read_parquet(f).reindex(columns=TML_COLS)
            frames.append(df.assign(group=group, tour=tour, file=f.parent.name + "/" + f.name))
    t = pd.concat(frames, ignore_index=True)
    info = {"rows_read": int(len(t)), "first_season_file": TML_FIRST_SEASON, "left_out": {}}
    t["d"] = pd.to_datetime(t["tourney_date"], format="%Y%m%d", errors="coerce")
    t["round"] = t["round"].fillna("").str.upper().replace({"3RD/4TH": "BR"})
    bad = t["d"].isna() | ~t["round"].isin(list(C.ROUND_ORDER)) | t["winner_name"].fillna("").eq("") \
        | t["loser_name"].fillna("").eq("")
    info["left_out"]["no_date_round_or_name"] = int(bad.sum())
    t = t[~bad].reset_index(drop=True)
    t["event"] = t["file"] + "|" + t["tourney_id"].astype(str) + "|" + t["tourney_name"].astype(str)
    return t, info


def day_level_events(t: pd.DataFrame) -> pd.DataFrame:
    """Per TML event (file, id, name): is each row dated by the day it was played? Yes when the event
    has several dates within 16 days, its rounds follow one another in time (an earlier round's last
    date at most one day after a later round's first), no day holds more than two rounds or more than
    34 matches, the final (if any) is on the last date, and every round of 12 or more matches is spread
    over at least two dates (otherwise the dates are per round, not per match: Charleston 2026 in the WTA
    file puts all 16 first-round and all 16 second-round matches on one day each). One-date events and
    events dated in two blocks (all early rounds on one day) are event-dated."""
    g = t.groupby("event")
    ev = pd.DataFrame({"rows": g.size(), "dates": g["d"].nunique(), "first": g["d"].min(), "last": g["d"].max()})
    ev["span"] = (ev["last"] - ev["first"]).dt.days
    rr = t.assign(ro=t["round"].map(C.ROUND_ORDER)).groupby(["event", "ro"])["d"].agg(["min", "max", "size", "nunique"]).reset_index()
    rr = rr.sort_values(["event", "ro"])
    rr["next_min"] = rr.groupby("event")["min"].shift(-1)
    over = ((rr["max"] - rr["next_min"]).dt.days > 1).groupby(rr["event"]).any()
    one_date_big_round = ((rr["size"] >= MIN_SPREAD_ROUND) & (rr["nunique"] < 2)).groupby(rr["event"]).any()
    per_day = t.groupby(["event", "d"]).agg(rounds=("round", "nunique"), matches=("round", "size"))
    crowded = ((per_day["rounds"] > MAX_ROUNDS_PER_DAY) | (per_day["matches"] > MAX_MATCHES_PER_DAY)).groupby(level=0).any()
    fin = t[t["round"].eq("F")].groupby("event")["d"].max()
    ev["monotone"] = ~over.reindex(ev.index).fillna(False).astype(bool)
    ev["crowded_day"] = crowded.reindex(ev.index).fillna(False).astype(bool)
    ev["round_dated"] = one_date_big_round.reindex(ev.index).fillna(False).astype(bool)
    ev["final_on_last_day"] = (fin.reindex(ev.index).isna()) | (fin.reindex(ev.index) == ev["last"])
    ev["day_level"] = ((ev["dates"] >= 2) & (ev["span"] <= 16) & ev["monotone"] & ~ev["crowded_day"]
                       & ~ev["round_dated"] & ev["final_on_last_day"])
    return ev


def tml_frame(t: pd.DataFrame) -> pd.DataFrame:
    """TML rows in the common layout (winner first)."""
    atp = t["tour"].eq("atp")
    wid, lid = t["winner_id"].fillna("").astype(str), t["loser_id"].fillna("").astype(str)
    out = pd.DataFrame({
        "source_key": (t["_source_file"].astype(str).str.replace("data/raw/public_dump/tennis_my_life/", "", regex=False)
                       + ":" + t["_row"].astype(str)).to_numpy(),
        "tour": t["tour"].to_numpy(), "date": t["d"].to_numpy(), "name1": t["winner_name"].to_numpy(),
        "name2": t["loser_name"].to_numpy(), "pid1": np.where(atp, wid, "wta:" + wid), "pid2": np.where(atp, lid, "wta:" + lid),
        "i1": np.where(wid == "", "", np.where(atp, "atpcode:" + wid, "wta:" + wid)),
        "i2": np.where(lid == "", "", np.where(atp, "atpcode:" + lid, "wta:" + lid)),
        "sets": t["score"].fillna("").map(X.sets_of_score).to_numpy(), "rspec": t["round"].to_numpy(),
        "event": t["event"].to_numpy(), "group": t["group"].to_numpy(), "src_file": t["_source_file"].to_numpy(),
        "src_row": t["_row"].astype("int64").to_numpy()})
    return _finish(out)
