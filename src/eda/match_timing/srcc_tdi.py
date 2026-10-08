"""Source 5, tdi: TDI Tennis Results (results.tennisdata.com), staged under data/dump/points/tdi/
(src/ingest/point_sources/tdi.py; docs/decisions/2026-09-25-tdi-tennis-results.md; README "TDI Tennis Results").

What it holds for timing (observed): every point's UTC time (on 99.8% of points), so each match's first and last point
(matches.first_point_time / last_point_time), the listing's start stamp and day, the completion time, and the place
("Milan, Italy"; "Cincinnati, OH, U.S.A."). Window: ATP Tour and Challenger matches completed 23 June - 29 September
2026, and 634 older matches (May 2025 - April 2026) whose ids the Wayback Machine kept. Singles only here.

Linking: identity (srcc_common.link) against Stage 0's ATP matches from April 2025; the page's ATP code
(year#tournament#match) gives Stage 0's tournament id ('<year>-<tournament>') to rank candidates; the pages' ATP player
ids feed the id pass. Day: the first point in the place's zone (srcc_tz; a US state code settles the US zone).
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.eda.match_timing import srcc_common as K
from src.eda.match_timing import srcc_tz as TZ

SOURCE = "tdi"
TDI = K.DUMP / "points" / "tdi"


def tdi_sets(a: str, b: str) -> tuple:
    """'1:6 2:2 3:6' and '1:4 2:6 3:4' (set:games[/tiebreak]) -> ((6, 4), (2, 6), (6, 4))."""
    def parse(s):
        out = {}
        for tok in str(s or "").split():
            m = re.match(r"^(\d+):(\d+)", tok)
            if m:
                out[int(m.group(1))] = int(m.group(2))
        return out
    x, y = parse(a), parse(b)
    return K.sets_from_pairs([(x.get(k), y.get(k)) for k in sorted(set(x) | set(y))])


def place_zone(place) -> tuple[str | None, str | None, str | None]:
    """(IOC country, city, zone) of 'City, Country' or 'City, ST, U.S.A.'."""
    parts = [p.strip() for p in str(place or "").split(",") if p.strip()]
    if not parts:
        return None, None, None
    country = TZ.country_code(parts[-1])
    city = re.sub(r"\b\d+\b", " ", TZ.norm_place(parts[0]))
    city = " ".join(city.split()) or None
    if country == "USA" and len(parts) >= 3 and re.fullmatch(r"[A-Z]{2}", parts[1]):
        return country, city, TZ.STATE_TZ.get(parts[1]) or TZ.zone_for(country, city)
    return country, city, TZ.zone_for(country, city)


def run() -> dict:
    s0 = K.stage0()
    t = pq.read_table(TDI / "matches.parquet").to_pandas().rename(columns={"match_id": "tdi_id"})
    s = t[t["draw_type"].eq("singles")].copy().reset_index(drop=True)
    s["t0"] = pd.to_datetime(s["first_point_time"], utc=True, format="ISO8601", errors="coerce")
    s["t1"] = pd.to_datetime(s["last_point_time"], utc=True, format="ISO8601", errors="coerce")
    pz = s["place"].map(place_zone)
    s["country"], s["city"], s["zone"] = pz.str[0], pz.str[1], pz.str[2]
    s["day_local"] = K.local_day(s["t0"], s["zone"])
    s["last_local"] = K.local_day(s["t1"], s["zone"])
    s["day"] = s["day_local"].fillna(K.utc_day(s["t0"]))
    s["date_basis"] = np.where(s["day_local"].notna(), "local", "utc_date")
    s["sid"] = "tdi:" + s["tdi_id"].astype(str)
    scope = s[s["t0"].notna()].copy()
    src = pd.DataFrame({
        "sid": scope["sid"], "tour": "atp", "day": scope["day"],
        "p1": scope["team_a_names"], "p2": scope["team_b_names"],
        "sets": [tdi_sets(a, b) for a, b in zip(scope["team_a_scores"], scope["team_b_scores"])],
        "rnd": scope["round"].map(K.round_code), "qual": scope["draw"].eq("qualifying"),
        "tid": scope["atp_year"].astype(str) + "-" + scope["atp_tournament_id"].astype(str),
        "id1": scope["team_a_atp_ids"].astype(str), "id2": scope["team_b_atp_ids"].astype(str)})
    sl = s0[(s0["tour"] == "atp") & (s0["tdate"] >= "2025-04-01")]
    K.log(f"[tdi] {len(src):,} singles matches to link against {len(sl):,} Stage 0 matches")
    res = K.link(src, sl)
    lk = res["links"].merge(scope, on="sid", how="left")
    # a place the tables cannot read ('Monastir, Monastir') takes the linked Stage 0 event's country and city
    sm = s0.set_index("match_id")
    miss = lk["zone"].isna()
    if miss.any():
        z = [TZ.zone_for(c, K.s0_city(n)) if isinstance(c, str) else None
             for c, n in zip(lk.loc[miss, "match_id"].map(sm["country"]), lk.loc[miss, "match_id"].map(sm["tournament_name"]))]
        lk.loc[miss, "zone"] = z
        lk.loc[miss, "day_local"] = K.local_day(lk.loc[miss, "t0"], lk.loc[miss, "zone"])
        lk.loc[miss, "last_local"] = K.local_day(lk.loc[miss, "t1"], lk.loc[miss, "zone"])
        lk.loc[miss & lk["day_local"].notna(), "day"] = lk.loc[miss & lk["day_local"].notna(), "day_local"]
        lk.loc[miss & lk["day_local"].notna(), "date_basis"] = "local"
    spans = (lk["last_local"] - lk["day_local"]).dt.days
    out = pd.DataFrame({
        "match_id": lk["match_id"], "source_key": lk["sid"], "date_local": lk["day"], "start_utc": lk["t0"],
        "date_basis": lk["date_basis"],
        "link_method": ("identity_" + lk["pass"] + ";first_point;" + np.where(lk["date_basis"].eq("local"),
                                                                             "place_zone", "utc")
                        + np.where(spans.fillna(0) > 0, ";last_point_day+" + spans.fillna(0).astype(int).astype(str), "")
                        + np.where(lk["tidok"].eq(1), ";tid", "")),
        "score_agrees": lk["sc"], "round_agrees": lk["rd"].map(K.rd_bool)})
    path = K.write_links(out, SOURCE)
    reason = res["reason"]
    diag = src.assign(reason=src["sid"].map(reason))
    diag = diag[diag["reason"] != "linked"].copy()
    diag["candidates"] = diag["sid"].map(lambda x: ";".join(res["ambiguous"].get(x, [])))
    diag["sets"] = diag["sets"].map(lambda x: " ".join(f"{a}-{b}" for a, b in x))
    diag = diag.merge(scope[["sid", "place", "level", "draw", "in_wayback_list"]], on="sid", how="left")
    K.write_diagnostics(diag.drop(columns=["id1", "id2"]), SOURCE)
    s0max = sl["tdate"].max()
    return {
        "source": SOURCE, "file": str(path.relative_to(K.ROOT)),
        "method": "identity (srcc_common.link; ATP tournament id from the page's ATP code ranks candidates; ATP player "
                  "ids for the id pass) against Stage 0's ATP matches from April 2025; day = first point in the place's "
                  "zone",
        "rows_read": int(len(t)), "singles": int(len(s)), "singles_with_first_point": int(len(scope)),
        "linked": int(len(out)),
        "ambiguous": int(reason.str.startswith("ambiguous").sum()),
        "unlinked": int(len(src) - len(out) - reason.str.startswith("ambiguous").sum()),
        "outcomes": K.outcome_counts(reason),
        "stage0_last_atp_tournament_date": str(s0max.date()),
        "unlinked_after_stage0_ends": int(diag["day"].gt(s0max + pd.Timedelta(days=21)).sum()),
        "unlinked_by_level_draw": diag.groupby(["level", "draw", "reason"]).size().rename("rows").reset_index()
                                      .to_dict("records"),
        "linked_by_pass": lk["pass"].value_counts().to_dict(),
        "linked_with_tournament_id_agreeing": int(lk["tidok"].eq(1).sum()),
        "linked_with_tournament_id_disagreeing": int(lk["tidok"].eq(-1).sum()),
        "date_basis": out["date_basis"].value_counts().to_dict(),
        "places_without_zone": scope.loc[scope["zone"].isna(), "place"].value_counts().head(20).to_dict(),
        "matches_whose_last_point_is_on_a_later_local_day": int((spans > 0).sum()),
        "with_start_utc": int(out["start_utc"].notna().sum()),
        "score_agrees": out["score_agrees"].value_counts(dropna=False).rename(str).to_dict(),
        "round_agrees": out["round_agrees"].value_counts(dropna=False).rename(str).to_dict(),
    }
