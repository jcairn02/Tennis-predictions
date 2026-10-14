"""Summaries for link_sources_b.py: coverage of Stage 0, agreement with tennis-data.co.uk's match days,
date plausibility, time-zone checks and agreement between the sources themselves."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.eda.match_timing import srcb_common as X
from src.eda.match_timing import srcb_sources as SRC
from src.eda.predictability_diagnostic import common as C

ODDS = C.OUT / "stage1_odds.parquet"
CELL = ["tour", "level", "qualifying", "year"]


def records(frame: pd.DataFrame) -> list:
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def load_td() -> pd.DataFrame:
    """tennis-data.co.uk's match day per linked Stage 0 match (Stage 1), rows it re-dated left out."""
    o = pd.read_parquet(ODDS, columns=["match_id", "td_date", "td_redated", "td_tournament", "td_round"])
    o = o[o["td_date"].notna() & ~o["td_redated"]]
    return o.assign(td_date=o["td_date"].astype("datetime64[ns]").dt.normalize())


def day_diff(a: pd.Series, b: pd.Series) -> pd.Series:
    return ((pd.to_datetime(a) - pd.to_datetime(b)) / np.timedelta64(1, "D")).round()


def share_table(d: pd.Series) -> dict:
    d = d.dropna()
    n = int(len(d))
    if not n:
        return {"matches": 0}
    return {"matches": n, "same_day": int((d == 0).sum()), "same_day_pct": round(100 * float((d == 0).mean()), 2),
            "one_day_off": int((d.abs() == 1).sum()), "one_day_off_pct": round(100 * float((d.abs() == 1).mean()), 2),
            "larger": int((d.abs() > 1).sum()), "larger_pct": round(100 * float((d.abs() > 1).mean()), 2),
            "source_minus_td_days": {str(int(k)): int(v) for k, v in d.value_counts().sort_index().items()
                                     if abs(k) <= 3}}


def td_agreement(o: pd.DataFrame, td: pd.DataFrame, worst: int = 20) -> dict:
    j = o[o["date_local"].notna()].merge(td, on="match_id")
    j["diff"] = day_diff(j["date_local"], j["td_date"])
    out = share_table(j["diff"])
    out["by_basis"] = {b: share_table(g["diff"]) for b, g in j.groupby("date_basis")}
    out["by_tour"] = {t: share_table(g["diff"]) for t, g in j.groupby("tour")}
    region = np.where(j["tz"].isna(), "zone unknown",
                      np.where(j["tz"].fillna("").str.startswith("America"), "Americas", "elsewhere"))
    out["by_region"] = {r: share_table(g["diff"]) for r, g in j.groupby(region)}
    st = pd.to_datetime(j["start_utc"], utc=True)
    if st.notna().any():
        # tennis-data dates a match by the calendar day in the UK, not at the venue
        uk = st.dt.tz_convert("Europe/London").dt.tz_localize(None).dt.normalize()
        out["start_as_uk_calendar_day_vs_td"] = share_table(day_diff(uk, j["td_date"]))
    ev = j.groupby(["tour", "year", "tournament_name"]).agg(
        matches=("diff", "size"), not_same_day=("diff", lambda s: int((s != 0).sum())),
        median_diff=("diff", "median"), tz=("tz", "first")).reset_index()
    ev = ev[ev["not_same_day"] > 0].sort_values(["not_same_day", "matches"], ascending=[False, False])
    out["events_not_same_day"] = int(len(ev))
    out["events_with_most_disagreement"] = records(ev.head(15))
    w = j.assign(absd=j["diff"].abs()).sort_values(["absd", "match_id"], ascending=[False, True]).head(worst)
    w = w[w["absd"] > 0]
    out["worst"] = records(w[["match_id", "source_key", "tournament_name", "round", "tournament_date", "date_local",
                              "td_date", "diff", "date_basis", "link_method"]].assign(
        tournament_date=lambda f: f["tournament_date"].dt.strftime("%Y-%m-%d"),
        date_local=lambda f: pd.to_datetime(f["date_local"]).dt.strftime("%Y-%m-%d"),
        td_date=lambda f: f["td_date"].dt.strftime("%Y-%m-%d")))
    return out


def date_flags(o: pd.DataFrame, examples: int = 10) -> dict:
    """Dates more than one day before the tournament's start, or after its plausible end."""
    d = o[o["date_local"].notna()].copy()
    d["days"] = day_diff(d["date_local"], d["tournament_date"])
    early_main = ~d["qualifying"] & (d["days"] < -1)
    early_qual = d["qualifying"] & (d["days"] < -1)
    late = d["days"] > d["end_days"]
    cols = ["match_id", "source_key", "tournament_name", "level", "round", "tournament_date", "date_local", "days",
            "link_method"]

    def ex(mask, n=examples):
        e = d[mask].sort_values("days", key=lambda s: s.abs(), ascending=False).head(n)[cols]
        return records(e.assign(tournament_date=e["tournament_date"].dt.strftime("%Y-%m-%d"),
                                date_local=pd.to_datetime(e["date_local"]).dt.strftime("%Y-%m-%d")))

    late_round_early = ~d["qualifying"] & d["round"].isin(X.LATE_ROUNDS) & (d["days"] < 1)
    return {"dated_links": int(len(d)),
            "main_draw_more_than_1_day_before_start": int(early_main.sum()),
            "qualifying_more_than_1_day_before_start_expected": int(early_qual.sum()),
            "after_plausible_end": int(late.sum()),
            "round_of_16_or_later_dated_on_or_before_start": int(late_round_early.sum()),
            "plausible_end_days_by_level": {**X.END_DAYS, "other": X.END_DEFAULT},
            "flagged_main_draw_early": ex(early_main, 500), "flagged_after_end": ex(late, 500),
            "examples_round_of_16_or_later_on_or_before_start": ex(late_round_early),
            "days_from_start_quantiles": {str(q): float(v) for q, v in d["days"].quantile([0, .01, .5, .99, 1]).items()}}


def coverage(outs: dict, s0: pd.DataFrame) -> pd.DataFrame:
    """Stage 0 matches per tour x level x qualifying x year and how many each source dates."""
    base = s0.groupby(CELL).size().rename("stage0_matches")
    rows = []
    union = set()
    for name, o in outs.items():
        lk = s0.loc[o["li"]].assign(dated=o["date_local"].notna().to_numpy())
        union |= set(lk.loc[lk["dated"], "match_id"])
        g = lk.groupby(CELL).agg(linked=("match_id", "size"), dated=("dated", "sum"))
        t = base.to_frame().join(g, how="left").fillna(0).reset_index()
        rows.append(t.assign(source=name))
    u = s0[s0["match_id"].isin(union)].groupby(CELL).size().rename("dated")
    t = base.to_frame().join(u, how="left").fillna(0).reset_index()
    rows.append(t.assign(source="any_source_b", linked=t["dated"]))
    out = pd.concat(rows, ignore_index=True)
    out[["linked", "dated"]] = out[["linked", "dated"]].astype("int64")
    out["dated_pct"] = (100 * out["dated"] / out["stage0_matches"]).round(2)
    return out[["source"] + CELL + ["stage0_matches", "linked", "dated", "dated_pct"]]


def reference_days(outs: dict, leave_out: str) -> pd.DataFrame:
    """The venue's day from the two timed sources (api_tennis, live_tennis_api) where the event's zone is
    known, the source under test left out; where both date a match, the Live Tennis API's day is used."""
    parts = [outs[n].loc[outs[n]["date_basis"].eq("local"), ["match_id", "date_local"]]
             for n in ("live_tennis_api", "api_tennis") if n in outs and n != leave_out]
    if not parts:
        return pd.DataFrame(columns=["match_id", "ref_day"])
    ref = pd.concat(parts, ignore_index=True).drop_duplicates("match_id")
    return ref.rename(columns={"date_local": "ref_day"})


def ref_agreement(o: pd.DataFrame, ref: pd.DataFrame, worst: int = 15) -> dict:
    j = o[o["date_local"].notna()].merge(ref, on="match_id")
    if j.empty:
        return {"matches": 0}
    j["diff"] = day_diff(j["date_local"], j["ref_day"])
    out = share_table(j["diff"])
    region = np.where(j["tz"].isna(), "zone unknown",
                      np.where(j["tz"].fillna("").str.startswith("America"), "Americas", "elsewhere"))
    out["by_tour"] = {t: share_table(g["diff"]) for t, g in j.groupby("tour")}
    out["by_region"] = {r: share_table(g["diff"]) for r, g in j.groupby(region)}
    ev = j.groupby(["tour", "year", "tournament_name"]).agg(
        matches=("diff", "size"), same_day_pct=("diff", lambda s: round(100 * float((s == 0).mean()), 1)),
        later=("diff", lambda s: int((s > 0).sum())), earlier=("diff", lambda s: int((s < 0).sum()))).reset_index()
    out["events_least_agreeing"] = records(ev[ev["same_day_pct"] < 100].sort_values(["same_day_pct", "matches"],
                                                                                   ascending=[True, False]).head(worst))
    return out


def cross_source(outs: dict) -> list:
    names = list(outs)
    res = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            j = outs[a][["match_id", "date_local"]].dropna().merge(outs[b][["match_id", "date_local"]].dropna(),
                                                                   on="match_id", suffixes=("_a", "_b"))
            if j.empty:
                continue
            res.append({"a": a, "b": b, **{k: v for k, v in share_table(day_diff(j["date_local_a"], j["date_local_b"])).items()}})
    return res


# ------------------------------------------------------------------------------------------------
# Time-zone checks

def local_hours(start: pd.Series, tz: pd.Series) -> pd.Series:
    out = pd.Series(np.nan, index=start.index)
    ok = start.notna() & tz.notna()
    for zone, idx in start[ok].groupby(tz[ok]).groups.items():
        out.loc[idx] = start.loc[idx].dt.tz_convert(zone).dt.hour.astype(float)
    return out


def hypothesis(local_naive: pd.Series, zone: str, tz: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Local day and hour at the event, and the UK calendar day, if the source's naive times were
    written in ``zone``."""
    utc = local_naive.dt.tz_localize(zone, ambiguous=np.ones(len(local_naive), dtype=bool),
                                     nonexistent="shift_forward").dt.tz_convert("UTC")
    uk = utc.dt.tz_convert("Europe/London").dt.tz_localize(None).dt.normalize()
    return X.local_dates(utc, tz), local_hours(utc, tz), uk


def tz_check(o: pd.DataFrame, src: pd.DataFrame, td: pd.DataFrame, zones: list[str]) -> dict:
    """For a source with naive times, if they were written in each candidate zone: the share of starts
    between 09:00 and 23:59 at the event, and agreement with tennis-data's day both as the event's day
    and as the UK calendar day (tennis-data dates matches by the UK day: see the summary's notes)."""
    lk = o[o["tz"].notna()].copy()
    naive = pd.Series(src["local_naive"].to_numpy()[lk["ri"].to_numpy()], index=lk.index)
    res = {}
    for zone in zones:
        day, hour, uk = hypothesis(naive, zone, lk["tz"])
        j = lk.assign(day=day, uk=uk).merge(td, on="match_id")
        res[zone] = {"links_with_event_zone": int(len(lk)),
                     "starts_09_to_24_local_pct": round(100 * float(hour.between(9, 23).mean()), 2),
                     "starts_00_to_06_local_pct": round(100 * float(hour.between(0, 6).mean()), 2),
                     "event_day_vs_tennis_data": share_table(day_diff(j["day"], j["td_date"])),
                     "uk_day_vs_tennis_data": share_table(day_diff(j["uk"], j["td_date"]))}
    return res


def pair_offsets(api: pd.DataFrame, api_src: pd.DataFrame, lta: pd.DataFrame, lta_src: pd.DataFrame) -> dict:
    """The same Stage 0 match in api_tennis and the Live Tennis API: hours between the naive times as
    written, and between the UTC instants as converted here."""
    a = api[["match_id", "ri"]].assign(a_naive=api_src["local_naive"].to_numpy()[api["ri"].to_numpy()],
                                       a_utc=api_src["start_utc"].to_numpy()[api["ri"].to_numpy()])
    b = lta[["match_id", "ri"]].assign(b_naive=lta_src["local_naive"].to_numpy()[lta["ri"].to_numpy()],
                                       b_utc=lta_src["start_utc"].to_numpy()[lta["ri"].to_numpy()])
    j = a.merge(b, on="match_id")
    if j.empty:
        return {"matches": 0}
    naive = ((pd.to_datetime(j["a_naive"]) - pd.to_datetime(j["b_naive"])) / pd.Timedelta(hours=1))
    conv = ((pd.to_datetime(j["a_utc"], utc=True) - pd.to_datetime(j["b_utc"], utc=True)) / pd.Timedelta(hours=1))

    def dist(x):
        x = x.dropna()
        r = x.round(2)
        return {"matches": int(len(x)), "median_hours": float(x.median()),
                "most_common_hours": {str(k): int(v) for k, v in r.value_counts().head(6).items()},
                "within_15_min_pct": round(100 * float((x.abs() <= 0.25).mean()), 2),
                "within_60_min_pct": round(100 * float((x.abs() <= 1.0).mean()), 2)}

    return {"api_naive_minus_lta_naive": dist(naive), "after_conversion_api_utc_minus_lta_utc": dist(conv)}


def lta_whole_file_shifts() -> dict:
    """Every row of the staged Live Tennis API index: hours between its written time and the same time read in
    the zone the staged version writes (Israel wall-clock for v1.0.0, so Zenodo v1.0.2's note applies: 120,758
    rows move back 3 h, 52,813 2 h; UTC for v1.0.2, so none moves)."""
    zone = SRC.lta_zone()
    lm = pd.read_parquet(SRC.LTA_MATCHES, columns=["scheduled_time_utc"])
    local = pd.to_datetime(lm["scheduled_time_utc"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    utc = local.dt.tz_localize(zone, ambiguous=np.ones(len(local), dtype=bool),
                               nonexistent="shift_forward").dt.tz_convert("UTC").dt.tz_localize(None)
    shift = ((local - utc) / pd.Timedelta(hours=1)).round()
    return {"rows": int(len(lm)), "read_as": zone, "unreadable": int(local.isna().sum()),
            "hours_back": {str(int(k)): int(v) for k, v in shift.value_counts().items()},
            "zenodo_v1_0_2_note": {"3": 120758, "2": 52813}}
