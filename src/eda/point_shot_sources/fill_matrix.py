"""Point/shot sources study, step 4: what each candidate source would add to the ten careers.

Starts from the career-coverage grading (reference_record.csv: 4,055 official matches of ten Challenger players,
85 of them with a point or shot record in the dump) and asks, source by source, which of the others it would
give a point- or shot-level record.

Measured, match by match:
* sofascore: listed with the point-level marker (sofascore_links.csv; marker checked in pbp_check_summary.json);
  in ITF draws of 2025-26, where the marker failed the check, only matches whose record was read directly
* live_tennis_api: listed in the vendor's public match index (reference_record.in_live_tennis_api); the vendor
  claims point sequences for part of its index, and its June 2026 observed sample is measured separately
* sackmann_pbp_copies, tennis_abstract_web: rows in public_source_rows.csv linked to an official match
  (charts count only when the dump's export lacks them)
Claimed, by rule: every other source in source_claims.csv (one row per source and level: years the provider
says it covers at point or shot level). A claimed match is a provider statement mapped onto the calendar,
not a checked record.

A point-level source counts the matches it would lift from no point record to one; a shot-level source counts
the matches it would lift to a shot record, including matches that already have a point sequence.

Writes fill_matrix.csv (one row per official match, one column per source) and fill_summary.json to
data/studies/point_shot_sources/.
Run: ./python.sh src/eda/point_shot_sources/fill_matrix.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "studies" / "point_shot_sources"
REFERENCE = ROOT / "data" / "studies" / "career_coverage" / "reference_record.csv"
HAS_POINTS = {"Point-by-point sequence", "Shot-by-shot chart"}
LEVELS = ["ITF qualifying", "ITF main draw", "Challenger qualifying", "Challenger main draw", "Tour qualifying",
          "Tour main draw", "Davis Cup"]
PERIODS = [(2012, 2018, "2012-18"), (2019, 2021, "2019-21"), (2022, 2023, "2022-23"), (2024, 2024, "2024"),
           (2025, 2026, "2025-26")]


def period(year: int) -> str:
    return next(label for lo, hi, label in PERIODS if lo <= year <= hi)


def itf_recent(ref: pd.DataFrame) -> pd.Series:
    """ITF draws of 2025-26: SofaScore's point marker does not track its point records there (pbp_checks.py)."""
    return ref["level"].str.startswith("ITF") & (ref["year"] >= 2025)


def direct_checks() -> pd.DataFrame:
    """Every SofaScore event whose point-by-point endpoint was read: sofa_id, has_record."""
    frames = [pd.read_csv(OUT / f, dtype=str, keep_default_na=False)
              for f in ("pbp_checks.csv", "pbp_checks_itf_recent.csv") if (OUT / f).exists()]
    c = pd.concat(frames)[["sofa_id", "http"]]
    c = c[c["http"].isin(["200", "404"])]
    return c.assign(has_record=c["http"] == "200").drop_duplicates("sofa_id")


def measured(ref: pd.DataFrame) -> pd.DataFrame:
    """One boolean column per measured source: would it give this match a point or shot record.
    SofaScore counts a linked match with the point marker, except in ITF draws of 2025-26, where only a match
    whose point record was read directly counts."""
    sofa = pd.read_csv(OUT / "sofascore_links.csv", dtype=str, keep_default_na=False)
    rows = pd.read_csv(OUT / "public_source_rows.csv", dtype=str, keep_default_na=False)
    m = pd.DataFrame(index=ref.index)
    marker = set(sofa.loc[(sofa["sofa_status"] == "linked") & (sofa["pbp_marker"] == "True"), "ref_id"])
    checks = direct_checks()
    read_ok = set(sofa.loc[sofa["sofa_id"].isin(set(checks.loc[checks["has_record"], "sofa_id"])), "ref_id"])
    m["sofascore"] = (ref["ref_id"].isin(marker) & ~itf_recent(ref)) | (ref["ref_id"].isin(read_ok) & itf_recent(ref))
    m["sofascore_read_directly"] = ref["ref_id"].isin(set(sofa.loc[sofa["sofa_id"].isin(set(checks["sofa_id"])),
                                                                   "ref_id"]))
    m["sofascore_unobserved"] = ref["ref_id"].isin(set(sofa.loc[sofa["sofa_status"] == "unobserved", "ref_id"]))
    m["sofascore_observed"] = ref["ref_id"].isin(set(sofa.loc[sofa["sofa_status"].isin(
        ["linked", "ambiguous", "absent"]), "ref_id"]))
    m["live_tennis_api"] = ref["in_live_tennis_api"] == "True"
    m["live_tennis_api_june_sample"] = ref["score_states"] == "True"
    pbp = rows[rows["source"].str.startswith("pbp_copy") & (rows["link"] == "linked")]
    m["sackmann_pbp_copies"] = ref["ref_id"].isin(set(pbp["ref_id"]))
    web = rows[(rows["source"] == "tennis_abstract_chart") & (rows["in_dump_export"] == "False") &
               (rows["link"] == "linked")]
    m["tennis_abstract_web"] = ref["ref_id"].isin(set(web["ref_id"]))
    return m


def claimed(ref: pd.DataFrame, claims: pd.DataFrame) -> pd.DataFrame:
    """One column per claimed source: the share of matches of this match's level and year that the provider
    says carry point (or shot) data, 0 outside every claim. Summing it over matches gives the expected number of
    matches the source would fill if its claim holds. A claim with an unstated share counts as 1 and is marked
    in source_claims.csv; claims without years are listed in the report but not mapped."""
    c = pd.DataFrame(index=ref.index)
    for src, g in claims.groupby("source_id", sort=False):
        share = pd.Series(0.0, index=ref.index)
        for _, r in g.iterrows():
            lv = ref["level"] == r["level"]
            if r.get("event_types", ""):
                lv &= ref["event_type"].isin(r["event_types"].split(";"))
            if r.get("event_names", ""):
                lv &= ref["event_name"].isin(r["event_names"].split(";"))
            hit = lv & ref["year"].between(int(r["year_from"]), int(r["year_to"]))
            share = share.where(~hit, share.clip(lower=float(r["share"] or 1)))
        c[src] = share
    return c


def sofascore_estimate(need: pd.DataFrame) -> tuple[dict, pd.Series]:
    """Matches in stretches of SofaScore's lists the reading tool cut off, credited at the rate observed for the
    same level and period (share of read matches with the point marker). In ITF draws of 2025-26 every match not
    read directly is credited at the share of directly read matches of the same year with a point record.
    An estimate, kept apart from the count. Also returns the expected value per match: 1 when measured, the
    cell's rate when unread or unchecked, 0 otherwise."""
    extra, cells = 0.0, []
    expected = need["sofascore"].astype(float).copy()
    checks = direct_checks()
    sofa = pd.read_csv(OUT / "sofascore_links.csv", dtype=str, keep_default_na=False)
    read = sofa[sofa["sofa_id"].isin(set(checks["sofa_id"]))].merge(checks, on="sofa_id")
    read = read[read["level"].str.startswith("ITF") & (read["year"].astype(int) >= 2025)]
    year_rate = read.groupby(read["year"].astype(int))["has_record"].mean().to_dict()
    for (lv, p), g in need.groupby(["level", "period"]):
        if lv.startswith("ITF") and p == "2025-26":
            for y, gy in g.groupby("year"):
                open_ = gy[~gy["sofascore_read_directly"]]
                rate = year_rate.get(int(y))
                if rate is not None:
                    extra += rate * len(open_)
                    expected[open_.index] = rate
                cells.append({"level": lv, "period": str(y), "read_directly": int(gy["sofascore_read_directly"].sum()),
                              "not_read": int(len(open_)), "record_rate_when_read": None if rate is None
                              else round(float(rate), 3)})
            continue
        seen, hidden = g[g["sofascore_observed"]], g[g["sofascore_unobserved"]]
        rate = float(seen["sofascore"].mean()) if len(seen) else None
        if len(hidden) and rate is not None:
            extra += rate * len(hidden)
            expected[hidden.index] = rate
        cells.append({"level": lv, "period": p, "read": int(len(seen)), "unread": int(len(hidden)),
                      "marker_rate_when_read": None if rate is None else round(rate, 3)})
    measured_n = int(need["sofascore"].sum())
    return ({"measured": measured_n, "estimated_in_unread_or_unchecked": round(extra),
             "estimated_total": round(measured_n + extra), "itf_2025_26_record_rate_by_year": year_rate,
             "cells": cells}, expected)


# tournament weeks; ITF starts in March 2025: the sampled pages run March-August, and the January 2025 ITF pages
# the public-web research opened had no point-by-point
TENNISLIVE_CELLS = [("Challenger main draw", "2022-01-01", "2023-12-31"),
                    ("Challenger qualifying", "2022-01-01", "2023-12-31"),
                    ("ITF main draw", "2025-03-01", "2025-12-31")]


def tennislive_estimate(need: pd.DataFrame) -> dict:
    """TennisLive.net in SofaScore's holes: the matches there that SofaScore is not expected to fill, credited at
    the share of sampled TennisLive pages that showed point-by-point (tennislive_checks.csv), and at the lower end
    of its 95% interval. Bulk use of the site needs its operator's permission."""
    path = OUT / "tennislive_checks.csv"
    if not path.exists():
        return {}
    c = pd.read_csv(path, dtype=str, keep_default_na=False)
    found = c[c["page"] == "found"]
    k, n = int((found["point_by_point"] == "yes").sum()), len(found)
    share = k / n if n else 0.0
    z = 1.96
    low = ((share + z * z / (2 * n) - z * ((share * (1 - share) / n + z * z / (4 * n * n)) ** 0.5)) / (1 + z * z / n)
           if n else 0.0)
    cells, open_total = [], 0.0
    for lv, a, b in TENNISLIVE_CELLS:
        g = need[(need["level"] == lv) & need["event_date"].between(a, b)]
        open_ = float((1 - g["sofascore_expected"]).sum())
        open_total += open_
        cells.append({"level": lv, "weeks": f"{a} to {b}", "need": int(len(g)),
                      "not_expected_from_sofascore": round(open_),
                      "tennislive_expected": round(open_ * share), "tennislive_low": round(open_ * low)})
    return {"pages_found": n, "with_point_by_point": k, "share": round(share, 3), "wilson_low": round(low, 3),
            "cells": cells, "expected": round(open_total * share), "low": round(open_total * low)}


def main():
    ref = pd.read_csv(REFERENCE, dtype=str, keep_default_na=False)
    ref = ref[ref["is_bye"] != "True"].reset_index(drop=True)
    ref["year"] = ref["event_date"].str[:4].astype(int)
    ref["period"] = ref["year"].map(period)
    played = ref["walkover"] != "True"
    ref["needs_points"] = played & ~ref["depth_label"].isin(HAS_POINTS)
    ref["needs_shots"] = played & (ref["depth_label"] != "Shot-by-shot chart")
    claims = pd.read_csv(OUT / "source_claims.csv", dtype=str, keep_default_na=False)
    claims = claims[(claims["year_from"] != "") & (claims["level"] != "")]
    meas = measured(ref)
    measured_cols = set(meas.columns)
    fill = pd.concat([meas, claimed(ref, claims)], axis=1)
    sources = [c for c in fill.columns if c not in ("sofascore_unobserved", "sofascore_observed",
                                                     "sofascore_read_directly", "live_tennis_api_june_sample")]
    unit = {"tennis_abstract_web": "shot", **claims.drop_duplicates("source_id").set_index("source_id")["unit"]}
    unit = {s: unit.get(s, "point") for s in sources}

    table = pd.concat([ref[["ref_id", "player", "event_name", "event_date", "round", "level", "year", "period",
                            "depth_label", "needs_points", "needs_shots"]], fill], axis=1)
    table.to_csv(OUT / "fill_matrix.csv", index=False)

    def added(s):  # the matches source s would lift to its own depth, weighted by the claimed share
        eligible = table[table["needs_shots" if unit[s] == "shot" else "needs_points"]]
        return eligible.assign(w=eligible[s].astype(float))

    def tally(s, by, order):
        a = added(s)
        return {k: round(float(a.loc[a[by] == k, "w"].sum()), 1) for k in order}

    need = table[table["needs_points"]].copy()
    public = ["sofascore", "sackmann_pbp_copies", "tennis_abstract_web"]
    estimate, need["sofascore_expected"] = sofascore_estimate(need)
    # the ten careers after adding sources: measured free sources, then the Live Tennis API index on top
    need["free_measured"] = need[public].astype(bool).any(axis=1)
    need["free_expected"] = need[["sofascore_expected"]].join(need[["sackmann_pbp_copies", "tennis_abstract_web"]]
                                                              .astype(float)).max(axis=1)
    need["free_plus_lta_index"] = need["free_measured"] | need["live_tennis_api"].astype(bool)
    # upper bound: every match in the Live Tennis API index counted as having a point sequence
    need["free_plus_lta_expected"] = need[["free_expected"]].join(need["live_tennis_api"].astype(float)).max(axis=1)
    now = table.assign(has=table["depth_label"].isin(HAS_POINTS)).groupby("player")["has"].sum()
    by_player = []
    for pl, g in need.groupby("player"):
        total = int((table["player"] == pl).sum())
        by_player.append({"player": pl, "matches": total, "with_points_now": int(now[pl]),
                          "needing": int(len(g)), "sofascore_measured": int(g["sofascore"].sum()),
                          "sofascore_expected": round(float(g["sofascore_expected"].sum())),
                          "free_measured": int(g["free_measured"].sum()),
                          "free_expected": round(float(g["free_expected"].sum())),
                          "live_tennis_api_index": int(g["live_tennis_api"].sum()),
                          "free_plus_lta_index": int(g["free_plus_lta_index"].sum()),
                          "free_plus_lta_expected": round(float(g["free_plus_lta_expected"].sum()))})
    grid_union = [{"level": lv, "period": p, "need": int(len(g)),
                   "sofascore_measured": int(g["sofascore"].sum()),
                   "sofascore_expected": round(float(g["sofascore_expected"].sum()), 1),
                   "free_measured": int(g["free_measured"].sum()),
                   "free_expected": round(float(g["free_expected"].sum()), 1),
                   "live_tennis_api_index": int(g["live_tennis_api"].sum()),
                   "free_plus_lta_index": int(g["free_plus_lta_index"].sum()),
                   "free_plus_lta_expected": round(float(g["free_plus_lta_expected"].sum()), 1)}
                  for (lv, p), g in need.groupby(["level", "period"])]
    summary = {
        "official_matches": int(len(table)),
        "with_point_or_shot_record_now": int(table["depth_label"].isin(HAS_POINTS).sum()),
        "walkovers": int((~played).sum()),
        "needing_point_data": int(len(need)),
        "per_source": {s: {"unit": unit[s], "basis": "measured" if s in measured_cols else "claimed",
                           "matches": round(float(added(s)["w"].sum()), 1),
                           "by_level": tally(s, "level", LEVELS),
                           "by_period": tally(s, "period", [p for *_, p in PERIODS])}
                       for s in sources},
        "public_measured_union": int(need[public].astype(bool).any(axis=1).sum()),
        "public_measured_plus_live_tennis_api": int(need[public + ["live_tennis_api"]].astype(bool).any(axis=1).sum()),
        "sofascore_unobserved": int(need["sofascore_unobserved"].sum()),
        "sofascore_estimate": estimate,
        "free_expected_total": round(float(need["free_expected"].sum())),
        "free_plus_lta_expected_total": round(float(need["free_plus_lta_expected"].sum())),
        "tennislive_in_sofascore_holes": tennislive_estimate(need),
        "by_player": by_player,
        "level_period_union": grid_union,
        "needs_by_level": need["level"].value_counts().to_dict(),
        "needs_by_period": need["period"].value_counts().to_dict(),
        "level_period_grid": [
            {"level": lv, "period": p, "need": int(len(g)),
             **{s: round(float(g[s].astype(float).sum()), 1) for s in sources}}
            for (lv, p), g in need.groupby(["level", "period"])],
    }
    (OUT / "fill_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("level_period_grid", "per_source")}, indent=1))
    print(pd.DataFrame({s: v["by_level"] for s, v in summary["per_source"].items()}).T.assign(
        total=[v["matches"] for v in summary["per_source"].values()]).to_string())


if __name__ == "__main__":
    main()
