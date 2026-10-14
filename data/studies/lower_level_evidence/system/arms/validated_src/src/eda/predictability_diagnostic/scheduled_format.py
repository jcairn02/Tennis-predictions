"""Outcome-independent singles formats for the study's 2010--2026 scope.

Stage 0's ``format`` is an anatomy label inferred from scores. Its ``best_of``
also misses some Wimbledon final qualifying rounds. Neither is an input here.
Only event metadata determines a forecast's format. Sources and deliberate
exclusions: docs/studies/feature_alpha_audit/format_rules.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda.predictability_diagnostic import stage2_iid as M

STANDARD_LEVELS = ("FIN", "T1000", "T500", "T250", "CH")
MELBOURNE_2021 = ("yarra valley classic", "gippsland trophy", "grampians trophy")


def scheduled_format(rows: pd.DataFrame) -> pd.DataFrame:
    """Return best_of, format, supported and reason, with the input index.

    Unknown metadata, team/ITF rules, Next Gen's unimplemented short/no-ad sets,
    and the three mid-event format changes in Melbourne 2021 yield no iid
    forecast. A missing Wimbledon men's qualifying round is unknown, never
    guessed from the score or from the latest observed round in the dataset.
    ``supported`` refers to this iid model, not the existence of official rules.
    """
    def col(name, default=None):
        return rows[name] if name in rows else pd.Series(default, index=rows.index)

    tour = col("tour").astype("string").str.lower()
    level = col("level").astype("string")
    year = pd.to_numeric(col("year"), errors="coerce")
    name = col("tournament_name").astype("string").str.lower().str.strip()
    qualifying = col("qualifying").astype("boolean")
    round_name = col("round").astype("string").str.upper()
    if "round_order" in rows:
        fallback = pd.to_numeric(rows["round_order"], errors="coerce").map({1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"})
        round_name = round_name.fillna(fallback)

    bo = pd.Series(np.nan, index=rows.index, dtype="float64")
    fmt = pd.Series("unknown", index=rows.index, dtype=object)
    reason = pd.Series("unmapped_event_rules", index=rows.index, dtype=object)
    valid = (tour.isin(["atp", "wta"]) & year.between(2010, 2026) & qualifying.notna()
             & name.notna() & name.ne(""))

    def assign(mask, best_of, form, why):
        mask = mask.fillna(False)
        bo.loc[mask], fmt.loc[mask], reason.loc[mask] = best_of, form, why

    assign(valid & level.isin(STANDARD_LEVELS), 3, "standard", "tour_singles_rule")
    slam_map = {n: M.slam_of(n) for n in name.dropna().unique()}
    slam = name.map(slam_map)
    gs = valid & level.eq("GS") & slam.notna()
    assign(gs, 3, "standard", "grand_slam_singles_rule")
    assign(gs & tour.eq("atp") & ~qualifying, 5, "standard", "mens_grand_slam_main")
    wimq = gs & tour.eq("atp") & qualifying & slam.eq("WIM")
    assign(wimq & ~round_name.isin(["Q1", "Q2", "Q3"]), np.nan, "unknown", "wimbledon_qualifying_round_unknown")
    assign(wimq & round_name.eq("Q3"), 5, "standard", "mens_wimbledon_final_qualifying")

    nextgen = valid & tour.eq("atp") & name.str.contains(r"next\s*gen", regex=True, na=False)
    assign(nextgen, 5, "short_sets", "nextgen_short_no_ad_not_implemented")
    melbourne = valid & tour.eq("wta") & year.eq(2021) & name.isin(MELBOURNE_2021)
    assign(melbourne, 3, "unknown", "melbourne_2021_mid_event_rule_change")
    supported = fmt.eq("standard") & bo.isin([3, 5])
    return pd.DataFrame({"best_of": bo, "format": fmt, "supported": supported, "reason": reason}, index=rows.index)
