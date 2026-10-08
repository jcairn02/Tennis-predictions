"""Source 1, tennis_data: the match days Stage 1 already linked (stage1_odds.parquet), in the common schema.

tennis-data.co.uk's Date is a match day with no time. Every Stage 1 row with a td_date is kept, as Stage 1 linked it.
Rows Stage 1 moved to their file's season by its misdating rule (td_redated: the ATP 2013 file's China and Japan Opens
written as October 2012, one WTA row written as 2029) keep Stage 1's corrected day and say 'redated' in link_method.

date_basis is 'local', as the task specifies. Measured against the exact first points of the other sources
(link_sources_c.py, summary "tennis_data_clock"), the day behaves like the UK calendar day of the start rather than the
venue's: the two differ only at venues four or more hours from the UK, so those rows carry a link_method token naming
the side ('uk_day_venue_west': an evening start in the Americas can be the venue's previous day; 'uk_day_venue_east':
a morning start in Asia or Oceania can be the venue's next day). The venue is tennis-data's Location (Stage 4's city
table), placed in its zone by srcc_tz.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.eda.match_timing import srcc_common as K
from src.eda.match_timing import srcc_tz as TZ
from src.eda.predictability_diagnostic import common as C
from src.eda.predictability_diagnostic import stage4_country as SC

SOURCE = "tennis_data"
ODDS = C.OUT / "stage1_odds.parquet"
ODDS_SUMMARY = C.OUT / "stage1_odds_summary.json"
FAR = 4          # hours between the venue's and the UK's clocks from which the two calendar days can differ


def locations(o: pd.DataFrame) -> pd.Series:
    """tennis-data's Location (a city) for each linked row, read from the row Stage 1 linked."""
    out = pd.Series(None, index=o.index, dtype=object)
    for f, g in o.groupby("td_file"):
        loc = pd.read_parquet(K.ROOT / f, columns=["Location"])["Location"].to_numpy()
        out.loc[g.index] = loc[g["td_row"].astype(int).to_numpy()]
    return out


def venue_zone(city) -> str | None:
    if not isinstance(city, str) or not city.strip():
        return None
    folded = SC.ascii_fold(city)
    country = SC.CITY.get(folded)
    if country is None:
        return None
    return TZ.zone_for(country, folded)


def run() -> dict:
    o = pd.read_parquet(ODDS, columns=["match_id", "link", "td_file", "td_row", "td_date", "td_redated",
                                       "same_set_scores", "round_agrees"])
    linked = o[o["td_date"].notna()].copy()
    linked["location"] = locations(linked)
    zones = {c: venue_zone(c) for c in linked["location"].dropna().unique()}
    linked["zone"] = linked["location"].map(zones)
    noon = pd.to_datetime(linked["td_date"]).dt.normalize() + pd.Timedelta(hours=12)
    noon = noon.dt.tz_localize("UTC")
    lon = TZ.zoneinfo("Europe/London")
    rel = []
    for t, z in zip(noon, linked["zone"]):
        if not isinstance(z, str):
            rel.append(np.nan)
            continue
        rel.append((t.tz_convert(TZ.zoneinfo(z)).utcoffset() - t.tz_convert(lon).utcoffset()).total_seconds() / 3600)
    linked["rel_h"] = rel
    side = np.where(linked["rel_h"] <= -FAR, ";uk_day_venue_west", np.where(linked["rel_h"] >= FAR, ";uk_day_venue_east", ""))
    out = pd.DataFrame({
        "match_id": linked["match_id"].astype(str),
        "source_key": linked["td_file"].astype(str) + "#" + linked["td_row"].astype("Int64").astype(str),
        "date_local": pd.to_datetime(linked["td_date"]).dt.normalize(),
        "start_utc": pd.NaT,
        "date_basis": "local",
        "link_method": ("stage1_" + linked["link"].astype(str) + linked["td_redated"].map({True: ";redated", False: ""})
                        + side),
        "score_agrees": linked["same_set_scores"],
        "round_agrees": linked["round_agrees"].map({"yes": True, "no": False}),
    })
    path = K.write_links(out, SOURCE)
    s1 = json.loads(ODDS_SUMMARY.read_text(encoding="utf-8"))
    outcomes = s1.get("td_rows_by_outcome", {})
    amb = int(sum(v for k, v in outcomes.items() if k.startswith("ambiguous")))
    return {
        "source": SOURCE, "file": str(path.relative_to(K.ROOT)),
        "method": "Stage 1's links (src/eda/predictability_diagnostic/stage1_odds.py), taken as they are: name pair, "
                  "one-player anchor and winner-swapped passes, confirmed by set scores or round",
        "rows_read": int(s1.get("td_rows_2010_on", 0)),
        "stage0_candidate_matches": int(len(o)),
        "linked": int(len(out)), "ambiguous": amb, "unlinked": int(s1.get("td_rows_2010_on", 0)) - int(len(out)) - amb,
        "outcomes_stage1": outcomes,
        "linked_by_method": out["link_method"].value_counts().to_dict(),
        "redated_kept": int(linked["td_redated"].sum()),
        "venue_zone_found": int(linked["zone"].notna().sum()),
        "venues_without_zone": linked.loc[linked["zone"].isna(), "location"].value_counts(dropna=False).head(20)
                                     .rename(str).to_dict(),
        "rows_far_from_uk_clock": {"west": int((linked["rel_h"] <= -FAR).sum()), "east": int((linked["rel_h"] >= FAR).sum())},
        "date_basis": {"local": int(len(out))}, "with_start_utc": 0,
        "score_agrees": out["score_agrees"].value_counts(dropna=False).rename(str).to_dict(),
        "round_agrees": out["round_agrees"].value_counts(dropna=False).rename(str).to_dict(),
    }
