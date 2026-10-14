"""Result-free descriptives for the tennis-signal scout's memo (edge_anatomy, round 1).

Reads only the feature-universe store (no result column exists in it) and counts how often each candidate
signal's situation arises, season by season. No match outcome of any season is read.

Run:  ./python.sh data/studies/edge_anatomy/team/tennis_scout/descriptives.py
Writes: data/studies/edge_anatomy/team/tennis_scout/descriptives.json and descriptives.md (beside this file).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
STORE = ROOT / "data/studies/feature_universe/store.parquet"
OUT = Path(__file__).resolve().parent
LEVELS = {0.0: "Slams", 1.0: "Finals", 2.0: "1000s", 3.0: "500s", 4.0: "250s"}

COLS = [
    "match_id", "tour", "season", "tournament_date", "ctx__level", "ctx__draw_size", "ctx__round",
    "fi__B11__bd11_on", "pp__seeded_a", "pp__seeded_b",
    "fp__f26_impairment__ret_n_a", "fp__f26_impairment__ret_n_b",
    "fp__f26_impairment__ret_gap_a", "fp__f26_impairment__ret_gap_b",
    "el__low_share_diff", "el__low_share_a", "el__low_share_b",
    "fp__f09_venue__f09_ve", "pp__age_a", "pp__age_b",
    "sl__spd1_change_dec2_w52_a", "sl__spd1_change_dec2_w52_b",
]


def era(season: int) -> str:
    if season <= 2016:
        return "2013-16"
    if season <= 2019:
        return "2017-19"
    if season <= 2022:
        return "2020-22"
    if season <= 2024:
        return "2023-24"
    return "2025-26*"


def main() -> None:
    d = pd.read_parquet(STORE, columns=COLS)
    assert not any(c in d.columns for c in ("a_won", "winner", "result")), "a result column must never be read"
    d["level"] = d["ctx__level"].map(LEVELS)
    d["era"] = d["season"].map(era)
    d["event"] = d["match_id"].str.split("|").str[1]          # e.g. 2013-339
    d["event_code"] = d["event"].str.split("-", n=1).str[1]
    out: dict = {"source": str(STORE.relative_to(ROOT)), "rows": int(len(d)),
                 "note": "2026 = matches of events starting by 28 Jul 2026 (the store's frame); no outcome read"}

    # 1. Draw sizes at the 1000s (the 96-player, 12-day expansion) and on-site asymmetry.
    k = d[d["level"] == "1000s"]
    out["draw96_share_1000s"] = (k.assign(d96=k["ctx__draw_size"] >= 96)
                                  .groupby(["tour", "season"])["d96"].mean().round(3)
                                  .unstack(0).to_dict())
    d["on_asym"] = d["fi__B11__bd11_on"].abs() > 1e-9
    # a seed meeting an unseeded player who has already played more matches on site (the bye's "cold start")
    cold = (((d["pp__seeded_a"] == 1) & (d["pp__seeded_b"] == 0) & (d["fi__B11__bd11_on"] < -1e-9)) |
            ((d["pp__seeded_b"] == 1) & (d["pp__seeded_a"] == 0) & (d["fi__B11__bd11_on"] > 1e-9)))
    d["cold_seed"] = cold
    out["on_asym_share_by_era_level"] = (d.groupby(["era", "level"])["on_asym"].mean().round(3)
                                         .unstack(1).to_dict())
    out["cold_seed_share_by_era_level"] = (d.groupby(["era", "level"])["cold_seed"].mean().round(3)
                                           .unstack(1).to_dict())
    out["cold_seed_count_by_season"] = d.groupby("season")["cold_seed"].sum().astype(int).to_dict()

    # 2. Players back from a break of six weeks or more (within their first three matches back).
    ret = ((d["fp__f26_impairment__ret_n_a"] <= 2) | (d["fp__f26_impairment__ret_n_b"] <= 2))
    d["returning"] = ret
    out["returning_share_by_era_tour"] = d.groupby(["era", "tour"])["returning"].mean().round(3).unstack(1).to_dict()

    # 3. History composition: a large difference in the share of last year's matches below the main tour.
    d["low_gap"] = d["el__low_share_diff"].abs() >= 0.5
    out["low_share_gap_ge_0.5_by_era_tour"] = d.groupby(["era", "tour"])["low_gap"].mean().round(3).unstack(1).to_dict()
    d["low_mean"] = (d["el__low_share_a"] + d["el__low_share_b"]) / 2
    out["low_share_mean_by_era_tour"] = d.groupby(["era", "tour"])["low_mean"].mean().round(3).unstack(1).to_dict()

    # 4. Venue pace: edition-to-edition change of the leak-proof as-of pace for the same event code.
    v = (d.groupby(["tour", "event_code", "season"])["fp__f09_venue__f09_ve"].median().reset_index()
           .sort_values(["tour", "event_code", "season"]))
    v["prev"] = v.groupby(["tour", "event_code"])["fp__f09_venue__f09_ve"].shift(1)
    v["jump"] = (v["fp__f09_venue__f09_ve"] - v["prev"]).abs()
    v = v.dropna(subset=["prev"])
    out["venue_pace_sd_across_matches"] = round(float(d["fp__f09_venue__f09_ve"].std()), 4)
    out["venue_editions_jump_gt_0.10_by_season"] = (v.assign(big=v["jump"] > 0.10)
                                                     .groupby("season")["big"].mean().round(3).to_dict())
    out["venue_editions_median_jump_by_season"] = v.groupby("season")["jump"].median().round(4).to_dict()

    # 5. Age: matches with a player aged 21 or under, and with a player aged 32 or over.
    for c in ("pp__age_a", "pp__age_b"):
        d.loc[d[c] > 60, c] = np.nan
    d["young"] = (d["pp__age_a"] <= 21) | (d["pp__age_b"] <= 21)
    d["old"] = (d["pp__age_a"] >= 32) | (d["pp__age_b"] >= 32)
    out["young_le21_share_by_era_tour"] = d.groupby(["era", "tour"])["young"].mean().round(3).unstack(1).to_dict()
    out["old_ge32_share_by_era_tour"] = d.groupby(["era", "tour"])["old"].mean().round(3).unstack(1).to_dict()

    # 6. Serve-speed change coverage (the store's own shot-level column; men).
    m = d[d["tour"] == "atp"]
    both = m["sl__spd1_change_dec2_w52_a"].notna() & m["sl__spd1_change_dec2_w52_b"].notna()
    out["men_speed_change_both_share_by_season"] = both.groupby(m["season"]).mean().round(3).to_dict()

    (OUT / "descriptives.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    lines = ["# Result-free descriptives (tennis scout)", "", f"Source: `{out['source']}`, {out['rows']} matches. {out['note']}.", ""]
    for key, val in out.items():
        if isinstance(val, dict):
            lines.append(f"## {key}")
            lines.append("")
            lines.append("```")
            lines.append(json.dumps(val, indent=1, default=str))
            lines.append("```")
            lines.append("")
    (OUT / "descriptives.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
