"""Match timing, sources B: exact match days (and start times where given) from six sources, linked to
the Stage 0 match table, so that a leak-proof timeline can order matches by day rather than by
tournament week.

Targets: data/studies/predictability_diagnostic/stage0_matches.parquet (872,704 singles matches, the
week of 28 Dec 2009 to Sep 2026, every level) and its player table.

Sources (each written to data/studies/match_timing/links/<source>.parquet):
    api_tennis        api-tennis.com fixtures from the Hugging Face ATP pipeline handoff: men's ATP,
                      Challenger and ITF singles 2021-2024 with date, start time and status. Times are
                      read as Europe/Berlin wall-clock (the API's documented default zone; the handoff
                      does not say what its fetcher asked for) and checked in the summary.
    live_tennis_api   the Live Tennis API's public match index (Zenodo, staged), 1 Jan 2023 - 13 Aug 2026,
                      every level, no scores. 'scheduled_time_utc' is Israel wall-clock time in v1.0.0
                      (staged until 8 Oct 2026; converted to UTC here) and UTC in v1.0.2 (staged since).
    open_tennis_data  Open Tennis Data's completed main-tour results 2020 - 29 Aug 2026 (a derivative of
                      tennis-data.co.uk and Sackmann; its days are not independent of tennis-data).
    match_charting    the Match Charting Project's charted matches, with the charter's date and,
                      for about half, a local start time written by hand.
    infosys           ATP Stats Centre (Infosys) records 2021-2024 from the handoff (infosys_deep and
                      infosys_full): a date per match and no time. Linked by ATP player codes (learned
                      from Tennis My Life rows linked to Stage 0) and the ATP tournament number and season,
                      names as the fallback; the date is kept only when it fits the event.
    tml_days          Tennis My Life rows dated by the day played (most 2026 ATP events, the WTA Finals,
                      the United Cup in the WTA files, Davis Cup ties of 2026, the US Open 2026
                      qualifying): only events whose rows carry several dates that follow the rounds.

Linking (src/eda/match_timing/srcb_common.py): identity first (Stage 0 ids where the source has a
crosswalk, else scan.py's name keys), the source date 10 days before to 21 after the tournament date,
then stage1_odds.pick()'s ranking (identical set scores either way round, an agreeing round, the
nearest date inside the event's span), at most one row per match and one match per row, ties
recorded as ambiguous.

Outputs, in data/studies/match_timing/links/:
    <source>.parquet             match_id, source, source_key, date_local, start_utc, date_basis,
                                 link_method, score_agrees, round_agrees
    <source>.csv                 the ambiguous rows' tied candidates
    <source>.json                the source's counts, passes, checks and notes
    sources_b_summary.json       all sources: rows, links, coverage, agreement with tennis-data,
                                 implausible dates, time-zone checks, agreement between sources
    sources_b_link_counts.csv    Stage 0 matches and dated links by source x tour x level x qualifying x year

Run: ./python.sh src/eda/match_timing/link_sources_b.py     (about 10 minutes; at most 3 processes)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.match_timing import srcb_common as X  # noqa: E402
from src.eda.match_timing import srcb_report as R  # noqa: E402
from src.eda.match_timing import srcb_sources as SRC  # noqa: E402

SOURCES = ("api_tennis", "live_tennis_api", "open_tennis_data", "match_charting", "infosys", "tml_days")
WORKERS = 3


def scope_by_dates(s0: pd.DataFrame, src: pd.DataFrame, tours=None, pad: int = 31) -> pd.Index:
    d = src.loc[src["date"] > pd.Timestamp("2000-01-01"), "date"]
    lo, hi = d.min() - pd.Timedelta(days=pad), d.max() + pd.Timedelta(days=pad)
    mask = s0["tdate"].between(lo, hi)
    if tours:
        mask &= s0["tour"].isin(tours)
    return s0.index[mask]


def assemble(name: str, L: X.Linker, src: pd.DataFrame, s0: pd.DataFrame, mode: str,
             local_regions: tuple | None = None) -> pd.DataFrame:
    """The output rows (plus helper columns) for a linker's links. mode: 'utc_time' (the source gives a
    UTC instant: the event's zone gives the local day, else the UTC day) or 'local_date' (the source
    gives a day). ``local_regions``: for a day source whose days are the venue's only in some regions
    (measured against the timed sources), the regions labelled 'local'; elsewhere 'utc_date'."""
    lk = L.result().reset_index(drop=True)
    ri, li = lk["ri"].to_numpy(dtype="int64"), lk["li"].to_numpy(dtype="int64")
    o = pd.DataFrame({"ri": ri, "li": li, "gap": lk["gap"].to_numpy(),
                      "match_id": s0["match_id"].to_numpy()[li], "source": name,
                      "source_key": src["source_key"].astype(str).to_numpy()[ri],
                      "link_method": lk["method"].to_numpy(),
                      "score_agrees": X.tri(lk["sc"]).to_numpy(), "round_agrees": X.tri(lk["rd"]).to_numpy()})
    for c in ("tour", "level", "qualifying", "year", "round", "tournament_name", "end_days", "tz"):
        o[c] = s0[c].to_numpy()[li]
    o["tournament_date"] = s0["tdate"].to_numpy()[li]
    if mode == "utc_time":
        start = pd.Series(src["start_utc"].to_numpy()[ri]) if len(ri) else pd.Series(dtype="datetime64[ns, UTC]")
        start = pd.to_datetime(start, utc=True)
        tz = pd.Series(o["tz"].to_numpy(), dtype=object)
        local = X.local_dates(start, tz)
        utc_day = start.dt.tz_localize(None).dt.normalize()
        zoned = start.notna() & tz.notna()
        o["start_utc"] = start.to_numpy()
        o["start_utc"] = pd.to_datetime(o["start_utc"], utc=True)
        o["date_local"] = np.where(zoned, local, utc_day)
        o["date_local"] = pd.to_datetime(o["date_local"])
        o["date_basis"] = np.where(zoned, "local", "utc_date")
    else:
        o["date_local"] = pd.to_datetime(src["date"].to_numpy()[ri])
        o["start_utc"] = pd.Series(pd.NaT, index=o.index, dtype="datetime64[ns, UTC]")
        o["date_basis"] = "local"
        if local_regions is not None:
            reg = X.region_of(o["tz"])
            o["date_basis"] = np.where(np.isin(reg, list(local_regions)), "local", "utc_date")
    return o


def ambiguous_rows(name: str, L: X.Linker, src: pd.DataFrame, s0: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ri, (method, lis) in sorted(L.ambiguous.items()):
        for li in lis:
            rows.append({"source": name, "source_key": str(src.at[ri, "source_key"]),
                         "source_date": pd.Timestamp(src.at[ri, "date"]).strftime("%Y-%m-%d"),
                         "source_players": f"{src.at[ri, 'name1']} v {src.at[ri, 'name2']}", "method": method,
                         "tied_candidates": len(lis), "candidate_match_id": s0.at[li, "match_id"],
                         "candidate_tournament": s0.at[li, "tournament_name"], "candidate_round": s0.at[li, "round"],
                         "candidate_tournament_date": s0.at[li, "tdate"].strftime("%Y-%m-%d")})
    return pd.DataFrame(rows, columns=["source", "source_key", "source_date", "source_players", "method", "tied_candidates",
                                       "candidate_match_id", "candidate_tournament", "candidate_round",
                                       "candidate_tournament_date"])


def package(name, L, src, s0, info, mode, notes, local_regions=None) -> dict:
    o = assemble(name, L, src, s0, mode, local_regions)
    st = L.status()
    return {"name": name, "out": o, "src": src, "status": st, "info": info, "passes": L.counts,
            "ambiguous": ambiguous_rows(name, L, src, s0), "notes": notes, "linker": L}


# ------------------------------------------------------------------------------------------------
# The sources

def run_tml(s0: pd.DataFrame) -> tuple[dict, pd.Series]:
    t, info = SRC.load_tml_rows()
    ev = SRC.day_level_events(t)
    src = SRC.tml_frame(t)
    src["day_level"] = src["event"].map(ev["day_level"]).fillna(False).astype(bool)
    scope = s0.index[s0["tdate"] >= pd.Timestamp(f"{SRC.TML_FIRST_SEASON - 1}-12-01")]
    L = X.Linker("tml", src, s0, scope)
    tm = s0[s0["source"].eq("tml")]
    pos = pd.Series(src.index, index=src["src_file"] + ":" + src["src_row"].astype(str))
    pos = pos[~pos.index.duplicated()]
    pairs = pd.DataFrame({"ri": (tm["source_file"] + ":" + tm["source_row"].astype(str)).map(pos), "li": tm.index})
    L.direct("stage0_tml_row", pairs.dropna().astype("int64"))
    sl = X.src_long_from(src, f1="f1", f2="f2", i1="i1", i2="i2")
    tl = X.s0_long(s0, scope, forms=("F", "I"))
    # most TML rows are dated by event, so no round-aware date span here (identity, scores and round decide)
    L.pair_pass("name_pair", sl, ["F"], s0_long_=tl, need_span=False)
    L.pair_pass("player_ids", sl, ["I"], s0_long_=tl, need_span=False)
    L.anchor_pass("one_player_anchor", sl, forms=("F", "I"), need_score=True, s0_long_=tl, need_in_exp=False)
    learned = L.learn_ids(sl)
    src["i1"] = src["pid1"].map(learned).fillna(src["i1"])
    src["i2"] = src["pid2"].map(learned).fillna(src["i2"])
    L.pair_pass("learned_ids", X.src_long_from(src, i1="i1", i2="i2"), ["I"], s0_long_=tl, need_span=False)
    learned = L.learn_ids(sl)
    code_to_id = learned[~learned.index.astype(str).str.startswith("wta:")]
    info["atp_codes_learned"] = int(len(code_to_id))
    info["atp_codes_learned_to_sackmann_ids"] = int(code_to_id.astype(str).str.startswith("atp:").sum())
    info["events"] = int(len(ev))
    info["day_level_events"] = int(ev["day_level"].sum())
    info["multi_date_events_judged_event_dated"] = records_events(ev[(ev["dates"] >= 2) & ~ev["day_level"]])
    info["day_level_events_by_file"] = ev[ev["day_level"]].assign(file=ev[ev["day_level"]].index.str.split("|").str[0]) \
        .groupby("file").size().to_dict()
    info["rows_in_day_level_events"] = int(src["day_level"].sum())
    res = package("tml_days", L, src, s0, info, "local_date",
                  ["Only rows of events judged day-level (srcb_sources.day_level_events) are output; the rest of "
                   "Tennis My Life is dated by event, as Stage 0's rule C05 notes.",
                   "TML gives calendar days without times and does not say which calendar. Measured against the venue's "
                   "day from api_tennis / the Live Tennis API (agreement_with_timed_sources_venue_day) they are the "
                   "venue's day at events in Oceania (all) and Europe, Africa and Asia (about 93%), but not in the "
                   "Americas, where most late matches carry the next day and no single calendar fits. date_basis is "
                   "'local' only in the first regions; in the Americas and where the zone is unknown it is 'utc_date', "
                   "meaning 'not the venue's day' (TML gives no time to convert). Some WTA events are off by more.",
                   "The TML rows linked here also give the ATP player code -> Stage 0 id crosswalk used for Infosys."],
                  local_regions=("EurAfrAsia", "Oceania"))
    keep = src["day_level"].to_numpy()[res["out"]["ri"].to_numpy()]
    res["out_all"] = res["out"]
    res["out"] = res["out"][keep].reset_index(drop=True)
    res["status"] = res["status"][src["day_level"]]
    res["ambiguous"] = res["ambiguous"][res["ambiguous"]["source_key"].isin(src.loc[src["day_level"], "source_key"])]
    return res, code_to_id


def records_events(ev: pd.DataFrame) -> list:
    e = ev.reset_index()[["event", "rows", "dates", "span", "monotone", "crowded_day", "round_dated", "final_on_last_day"]]
    return R.records(e)


def run_api_tennis(s0: pd.DataFrame) -> dict:
    src, info = SRC.load_api_tennis()
    scope = scope_by_dates(s0, src, ["atp"])
    L = X.Linker("api_tennis", src, s0, scope)
    sl = X.src_long_from(src, f1="f1", f2="f2", a1="a1", a2="a2")
    tl = X.s0_long(s0, scope, forms=("F", "A", "I"))
    L.pair_pass("names", sl, ["F", "A"], s0_long_=tl)
    L.anchor_pass("one_player_anchor", sl, forms=("F", "A"), need_score=True, s0_long_=tl)
    learned = L.learn_ids(sl, min_votes=2)
    src["i1"], src["i2"] = src["pid1"].map(learned).fillna(""), src["pid2"].map(learned).fillna("")
    info["player_keys_learned"] = int(len(learned))
    L.pair_pass("learned_player_keys", X.src_long_from(src, i1="i1", i2="i2"), ["I"], s0_long_=tl)
    return package("api_tennis", L, src, s0, info, "utc_time",
                   [f"event_date/event_time read as {SRC.API_TZ} wall-clock (api-tennis.com's documented default; "
                    "the handoff's fetcher settings are not published) - see tz_checks.",
                    "Cancelled fixtures, doubles, team ties and identical duplicate rows are left out.",
                    "Qualifying rounds are labelled from the end (Final = last qualifying round)."])


def run_lta(s0: pd.DataFrame, names: pd.Series) -> dict:
    src, info = SRC.load_lta(names)
    scope = scope_by_dates(s0, src)
    L = X.Linker("live_tennis_api", src, s0, scope)
    sl = X.src_long_from(src, f1="f1", f2="f2", a1="a1", a2="a2", i1="i1", i2="i2")
    tl = X.s0_long(s0, scope, forms=("F", "A", "I"))
    L.pair_pass("sackmann_ids", sl, ["I"], s0_long_=tl)
    L.pair_pass("names", sl, ["F"], s0_long_=tl)
    L.pair_pass("abbreviated_names", sl, ["A"], s0_long_=tl)
    L.anchor_pass("one_player_anchor", sl, forms=("I", "F"), need_score=False, s0_long_=tl)
    learned = L.learn_ids(sl, min_votes=2)
    info["player_ids_learned"] = int(len(learned))
    src["i1"] = src["i1"].where(src["i1"] != "", src["pid1"].map(learned).fillna(""))
    src["i2"] = src["i2"].where(src["i2"] != "", src["pid2"].map(learned).fillna(""))
    L.pair_pass("learned_player_ids", X.src_long_from(src, i1="i1", i2="i2"), ["I"], s0_long_=tl)
    israel = info["scheduled_time_utc_read_as"] == SRC.LTA_TZ
    return package("live_tennis_api", L, src, s0, info, "utc_time",
                   ["scheduled_time_utc of v1.0.0 is Israel wall-clock time (Zenodo v1.0.2, 28 Sep 2026): converted "
                    "from Asia/Jerusalem to UTC here. Scheduled, not actual, start." if israel else
                    "scheduled_time_utc is read as UTC: the staged index is Zenodo v1.0.2 (28 Sep 2026), which corrects "
                    "v1.0.0's Israel wall-clock times. Scheduled, not actual, start.",
                    "No scores in the index: links are confirmed by round only (score_agrees is null).",
                    "The Sackmann crosswalk is used only where Stage 0 knows the id under a compatible name."])


def run_otd(s0: pd.DataFrame) -> dict:
    src, info = SRC.load_otd()
    scope = scope_by_dates(s0, src)
    L = X.Linker("open_tennis_data", src, s0, scope)
    sl = X.src_long_from(src, f1="f1", f2="f2", a1="a1", a2="a2", i1="i1", i2="i2")
    tl = X.s0_long(s0, scope, forms=("F", "A", "I"))
    L.pair_pass("sackmann_ids", sl, ["I"], s0_long_=tl)
    L.pair_pass("names", sl, ["F"], s0_long_=tl)
    L.pair_pass("abbreviated_names", sl, ["A"], s0_long_=tl)
    L.anchor_pass("one_player_anchor", sl, forms=("I", "F"), need_score=True, s0_long_=tl)
    return package("open_tennis_data", L, src, s0, info, "local_date",
                   ["Open Tennis Data's dates come from tennis-data.co.uk (its 'source' column cites it on every row): "
                    "agreement with tennis-data is not an independent check.",
                    "Like tennis-data, its day is the UK calendar day of the match (measured: 99.8% in the Americas "
                    "against 75% for the venue's day). That is the venue's day only in Europe, Africa and Asia, where "
                    "date_basis is 'local'; in the Americas, Oceania and where the zone is unknown it is 'utc_date' "
                    "(the UK day, within an hour of UTC; no time is given to convert)."],
                   local_regions=("EurAfrAsia",))


def run_mcp(s0: pd.DataFrame) -> dict:
    src, info = SRC.load_mcp()
    scope = scope_by_dates(s0, src)
    L = X.Linker("match_charting", src, s0, scope)
    sl = X.src_long_from(src, f1="f1", f2="f2", a1="a1", a2="a2")
    tl = X.s0_long(s0, scope, forms=("F", "A"))
    L.pair_pass("names", sl, ["F"], s0_long_=tl)
    L.pair_pass("abbreviated_names", sl, ["A"], s0_long_=tl)
    L.anchor_pass("one_player_anchor", sl, forms=("F",), need_score=False, s0_long_=tl)
    res = package("match_charting", L, src, s0, info, "local_date",
                  ["Date is the charter's match date (read as the local day). 'Time' is free text; where it reads as a "
                   "clock time (24-hour times before 09:00 left out as am/pm-ambiguous) and the event's zone is "
                   "known, it is taken as local wall-clock time and given as start_utc. Unverified.",
                   "No scores in the metadata: links are confirmed by round only."])
    o = res["out"]
    clock = src["clock"].to_numpy()[o["ri"].to_numpy()]
    naive = pd.Series([pd.Timestamp(d) + pd.Timedelta(hours=c[0], minutes=c[1]) if c is not None else pd.NaT
                       for d, c in zip(o["date_local"], clock)], dtype="datetime64[ns]")
    start = pd.Series(pd.NaT, index=o.index, dtype="datetime64[ns, UTC]")
    ok = naive.notna() & o["tz"].notna()
    for zone, idx in naive[ok].groupby(o.loc[ok, "tz"]).groups.items():
        start.loc[idx] = naive.loc[idx].dt.tz_localize(zone, ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("UTC")
    o["start_utc"] = start
    info["linked_with_start_utc_from_time_field"] = int(start.notna().sum())
    return res


def run_infosys(s0: pd.DataFrame, code_to_id: pd.Series) -> dict:
    src, info = SRC.load_infosys(code_to_id, workers=WORKERS)
    ev = s0["tournament_id"].str.extract(r"^(\d{4})-(\d+)$")
    s0x = s0.assign(season=s0["year"], tnum=pd.to_numeric(ev[1], errors="coerce").fillna(-2).astype(int))
    scope = s0x.index[s0x["tour"].eq("atp") & s0x["year"].between(src["season"].min(), src["season"].max())]
    L = X.Linker("infosys", src, s0x, scope)
    sl = X.src_long_from(src, f1="f1", f2="f2", a1="a1", a2="a2", i1="i1", i2="i2")
    tl = X.s0_long(s0x, scope, forms=("F", "A", "I"))
    on = ["season", "tnum"]
    # the event itself is matched (ATP tournament number and season), so the date is not used to link
    L.pair_pass("atp_ids_event", sl, ["I"], extra_on=on, window=False, s0_long_=tl, need_span=False)
    L.pair_pass("names_event", sl, ["F", "A"], extra_on=on, window=False, s0_long_=tl, need_span=False)
    L.pair_pass("atp_ids_date_window", sl, ["I"], s0_long_=tl)
    L.anchor_pass("one_player_anchor_event", sl, forms=("I", "F"), need_score=False, extra_on=on, window=False,
                  s0_long_=tl, need_in_exp=False)
    learned = L.learn_ids(sl, min_votes=2)
    info["atp_codes_learned_from_own_links"] = int(len(learned))
    src["i1"] = src["pid1"].map(learned).fillna(src["i1"])
    src["i2"] = src["pid2"].map(learned).fillna(src["i2"])
    L.pair_pass("learned_ids_event", X.src_long_from(src, i1="i1", i2="i2"), ["I"], extra_on=on, window=False,
                s0_long_=tl, need_span=False)
    res = package("infosys", L, src, s0x, info, "local_date",
                  ["No time of day in the records (match_date and match_status.matchDate only).",
                   "Joined on ATP tournament number and season with ATP player codes first, then names; the date "
                   "is kept only if it lies from 1 day (main draw) or 10 days (qualifying) before the tournament "
                   "date to the level's plausible end, else date_local is null.",
                   "Round from the ATP match number (MS001 final, MS002-003 semi-finals ...); qualifying numbers are "
                   "not read."])
    o = res["out"]
    days = R.day_diff(o["date_local"], o["tournament_date"])
    lo = np.where(o["qualifying"], -10, -1)
    plaus = days.notna() & (days >= lo) & (days <= o["end_days"])
    dated = pd.Series(src["date"].to_numpy()[o["ri"]] > np.datetime64("2000-01-01"), index=o.index)
    info["linked_dates_kept"] = int(plaus.sum())
    info["linked_dates_dropped_implausible"] = int((~plaus & dated).sum())
    info["linked_without_date"] = int((~dated).sum())
    drop = o[~plaus & dated].assign(days=days[~plaus & dated], infosys_date=lambda f: f["date_local"].dt.strftime("%Y-%m-%d"),
                                    tournament_date=lambda f: f["tournament_date"].dt.strftime("%Y-%m-%d"))
    info["implausible_dates_dropped"] = R.records(drop.sort_values("days", key=lambda s: s.abs(), ascending=False)
                                                  [["match_id", "source_key", "tournament_name", "round", "tournament_date",
                                                    "infosys_date", "days"]])
    o.loc[~plaus, "date_local"] = pd.NaT
    # winner check: Infosys matchWinner against Stage 0's winner, where the ids say who is who
    w = src["winner"].to_numpy()[o["ri"]]
    i1 = src["i1"].to_numpy()[o["ri"]]
    s0w = np.where(s0x["a_won"].to_numpy()[o["li"]], s0x["player_a_id"].to_numpy()[o["li"]], s0x["player_b_id"].to_numpy()[o["li"]])
    i2 = src["i2"].to_numpy()[o["ri"]]
    known = (w == 1) | (w == 2)
    infos_w = np.where(w == 1, i1, i2)
    readable = known & ((i1 == s0w) | (i2 == s0w))
    info["winner_check"] = {"links_with_winner_and_ids": int(readable.sum()),
                            "agree": int((readable & (infos_w == s0w)).sum()),
                            "disagree": int((readable & (infos_w != s0w)).sum())}
    return res


# ------------------------------------------------------------------------------------------------
# Writing

def source_json(res: dict, td: pd.DataFrame, s0: pd.DataFrame) -> dict:
    o, st = res["out"], res["status"]
    by_method = o.groupby("link_method").agg(links=("match_id", "size"), dated=("date_local", lambda s: int(s.notna().sum())),
                                             score_agrees=("score_agrees", lambda s: int(s.eq(True).sum())),
                                             score_differs=("score_agrees", lambda s: int(s.eq(False).sum())),
                                             round_agrees=("round_agrees", lambda s: int(s.eq(True).sum())),
                                             round_differs=("round_agrees", lambda s: int(s.eq(False).sum())))
    d = {"source": res["name"], "notes": res["notes"], "input": res["info"],
         "rows_in_scope": int(len(st)), "row_status": st.value_counts().to_dict(),
         "linked": int((st == "linked").sum()), "ambiguous": int((st == "ambiguous").sum()),
         "unlinked": int((st != "linked").sum() - (st == "ambiguous").sum()),
         "passes": res["passes"], "links_by_method": R.records(by_method.reset_index()),
         "date_basis": o["date_basis"].value_counts().to_dict(),
         "links_with_date": int(o["date_local"].notna().sum()), "links_with_start_utc": int(o["start_utc"].notna().sum()),
         "score_agrees": {str(k): int(v) for k, v in o["score_agrees"].astype("object").fillna("unknown").value_counts().items()},
         "round_agrees": {str(k): int(v) for k, v in o["round_agrees"].astype("object").fillna("unknown").value_counts().items()},
         "agreement_with_tennis_data": R.td_agreement(o, td), "date_flags": R.date_flags(o)}
    return d


def findings(per: dict, extra: dict) -> list:
    """The measured points the summary leads with (numbers from this run)."""
    out = []

    def g(d, *keys):
        for k in keys:
            d = (d or {}).get(k) if isinstance(d, dict) else None
        return d

    for n in ("api_tennis", "live_tennis_api"):
        uk = g(per.get(n), "agreement_with_tennis_data", "start_as_uk_calendar_day_vs_td")
        loc = g(per.get(n), "agreement_with_tennis_data", "by_region")
        if uk:
            out.append(f"{n}: the UK calendar day of the start equals tennis-data's date for {uk['same_day_pct']}% of "
                       f"{uk['matches']:,} matches; the venue's day does for "
                       f"{g(loc, 'elsewhere', 'same_day_pct')}% outside the Americas and {g(loc, 'Americas', 'same_day_pct')}% in "
                       "the Americas. tennis-data.co.uk dates a match by the UK calendar day (inference): late matches in "
                       "the Americas carry the next day there.")
    pair = g(extra, "tz_checks", "same_match_api_tennis_vs_live_tennis_api", "after_conversion_api_utc_minus_lta_utc")
    if pair:
        out.append(f"api_tennis read as Europe/Berlin and the Live Tennis API read as {SRC.lta_zone()} give the same UTC "
                   f"start to within 15 minutes for {pair['within_15_min_pct']}% of {pair['matches']:,} shared matches.")
    for n in ("tml_days", "match_charting", "infosys", "open_tennis_data"):
        a = g(per.get(n), "agreement_with_timed_sources_venue_day")
        if a and a.get("matches"):
            out.append(f"{n}: same venue day as api_tennis / Live Tennis API for {a['same_day_pct']}% of {a['matches']:,} "
                       f"shared matches (one day off {a['one_day_off_pct']}%, more {a['larger_pct']}%).")
    return out


def write(results: dict, s0: pd.DataFrame, extra: dict) -> None:
    X.OUT.mkdir(parents=True, exist_ok=True)
    td = R.load_td()
    outs = {n: r["out"] for n, r in results.items()}
    per = {}
    for name, res in results.items():
        o = res["out"]
        X.write_links(o, X.OUT / f"{name}.parquet")
        res["ambiguous"].to_csv(X.OUT / f"{name}.csv", index=False)
        per[name] = source_json(res, td, s0)
        per[name]["agreement_with_timed_sources_venue_day"] = R.ref_agreement(o, R.reference_days(outs, name))
        (X.OUT / f"{name}.json").write_text(json.dumps(per[name], indent=1, default=str), encoding="utf-8")
        X.log(f"wrote {name}: {len(o):,} links")
    cov = R.coverage(outs, s0)
    cov.to_csv(X.OUT / "sources_b_link_counts.csv", index=False)
    spans = {n: (int(o["year"].min()), int(o["year"].max())) for n, o in outs.items() if len(o)}
    cov_json = []
    for n, g in cov.groupby("source"):
        lo, hi = spans.get(n, (2010, 2026)) if n != "any_source_b" else (2010, 2026)
        g = g[g["year"].between(lo, hi) & ((g["dated"] > 0) | (n == "any_source_b"))]
        cov_json += R.records(g)
    summary = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "stage0_matches": int(len(s0)), "window_days": list(X.WINDOW),
        "plausible_end_days_by_level": {**X.END_DAYS, "other": X.END_DEFAULT},
        "sources": {n: {k: per[n][k] for k in ("rows_in_scope", "linked", "ambiguous", "unlinked", "row_status",
                                               "links_with_date", "links_with_start_utc", "date_basis", "score_agrees",
                                               "round_agrees")}
                    | {"rows_read": per[n]["input"].get("rows_read", per[n]["input"].get("records_read")),
                       "links_by_method": {r["link_method"]: r["links"] for r in per[n]["links_by_method"]},
                       "agreement_with_tennis_data": {k: v for k, v in per[n]["agreement_with_tennis_data"].items()},
                       "agreement_with_timed_sources_venue_day": per[n]["agreement_with_timed_sources_venue_day"],
                       "date_flags": per[n]["date_flags"], "notes": per[n]["notes"]}
                    for n in results},
        "findings": findings(per, extra),
        "coverage_by_tour_level_qualifying_year": cov_json,
        "agreement_between_sources": R.cross_source(outs),
        **extra}
    (X.OUT / "sources_b_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    X.log("wrote sources_b_summary.json and sources_b_link_counts.csv")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", nargs="*", choices=SOURCES, help="run only these sources (tml_days always runs: "
                    "Infosys needs its crosswalk)")
    args = ap.parse_args(argv)
    want = set(args.only or SOURCES)
    s0 = X.load_stage0()
    X.log(f"Stage 0: {len(s0):,} matches")
    names = X.player_names(s0)
    results, extra = {}, {}
    tml, code_to_id = run_tml(s0)
    if "tml_days" in want:
        results["tml_days"] = tml
    if "api_tennis" in want:
        results["api_tennis"] = run_api_tennis(s0)
    if "live_tennis_api" in want:
        results["live_tennis_api"] = run_lta(s0, names)
    if "open_tennis_data" in want:
        results["open_tennis_data"] = run_otd(s0)
    if "match_charting" in want:
        results["match_charting"] = run_mcp(s0)
    if "infosys" in want:
        results["infosys"] = run_infosys(s0, code_to_id)
    td = R.load_td()
    tz = {}
    if "api_tennis" in results:
        tz["api_tennis_if_times_were_written_in"] = R.tz_check(results["api_tennis"]["out"], results["api_tennis"]["src"], td,
                                                               ["Europe/Berlin", "UTC", "Europe/London"])
    if "live_tennis_api" in results:
        tz["live_tennis_api_if_times_were_written_in"] = R.tz_check(results["live_tennis_api"]["out"],
                                                                    results["live_tennis_api"]["src"], td,
                                                                    ["Asia/Jerusalem", "UTC"])
        tz["live_tennis_api_whole_index_shift"] = R.lta_whole_file_shifts()
    if "api_tennis" in results and "live_tennis_api" in results:
        tz["same_match_api_tennis_vs_live_tennis_api"] = R.pair_offsets(
            results["api_tennis"]["out"], results["api_tennis"]["src"],
            results["live_tennis_api"]["out"], results["live_tennis_api"]["src"])
    extra["tz_checks"] = tz
    extra["tml_crosswalk"] = {"atp_codes_learned": int(len(code_to_id)),
                              "to_sackmann_ids": int(code_to_id.astype(str).str.startswith("atp:").sum())}
    write(results, s0, extra)
    return 0


if __name__ == "__main__":
    sys.exit(main())
