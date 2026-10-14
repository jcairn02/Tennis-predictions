"""Serve-speed acquisition: how much of the serve-speed-change feature the two new sources make possible, measured
on what was actually acquired. Reads no match result.

The feature and its frame are serve_speed_sources/coverage.py's (a player's first-serve speed over the last 14 days
against the last 364; Stage 0's main-tour main draws; a match carries it when both players have a timed match in the
14-day window). That script's scenarios S0 (held) and S1 (files already on disk) are reused as they are. The new
scenarios are observed and per player, from speeds.parquet:
    N1 + ManTennisData   S1, plus every Stage 0 player-match that ManTennisData times (1st Serve Average Speed in
                         40-270 km/h, linked and oriented)
    N2 + Infosys Slams   N1, plus every player-match of AO 2025, RG 2025 and RG 2026 with a timed first serve in from
                         the decrypted MatchBeats points
For reference, coverage.py's hypothetical ceilings are stacked on N2:
    H1 + ATP files       every ATP tour-level non-Slam player-match of 2025-26 timed
    H2 + Slams in full   every player-match of AO 2025, RG 2025 and RG 2026 timed
    H3 + WTA             every WTA tour-level non-Slam player-match of 2025-26 timed

Run: ./python.sh src/eda/serve_speed_acquisition/coverage_after.py   (after speeds.py; about 5 minutes)
Writes data/studies/serve_speed_acquisition/: coverage_matches.csv (match level: both players timed, by tour x
group x year), coverage_feature.csv and coverage_feature_by_year.csv (the feature on the frame), coverage_summary.json
(the men's and women's 2025-26 counts and power, the Polymarket window)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_sources import coverage as CV  # noqa: E402

OUT = ROOT / "data" / "studies" / "serve_speed_acquisition"
SCENARIOS = ["S0_held", "S1_on_disk", "N1_mantd", "N2_slams", "H1_atp_files", "H2_slams_full", "H3_wta"]
log = CV.log


def timed_sides(players: pd.DataFrame, source: str, column: str) -> set:
    t = players[players["source"].eq(source) & players[column].notna() & players["side"].notna()]
    return set(t["match_id"] + "|" + t["side"])


def flags(rows: pd.DataFrame, players: pd.DataFrame) -> pd.DataFrame:
    base = CV.scenario_flags(rows, None)
    key = (rows["match_id"] + "|" + rows["side"]).to_numpy()
    f = pd.DataFrame(index=rows.index)
    f["S0_held"], f["S1_on_disk"] = base["S0_held"], base["S1_on_disk"]
    f["N1_mantd"] = f["S1_on_disk"] | np.isin(key, list(timed_sides(players, "mantennisdata", "ks_spd1")))
    f["N2_slams"] = f["N1_mantd"] | np.isin(key, list(timed_sides(players, "infosys_slams", "spd1_mean")))
    atp_tour = rows["tour"].eq("atp") & rows["level"].isin(CV.TOUR_LEVELS) & rows["year"].between(2025, 2026)
    f["H1_atp_files"] = f["N2_slams"] | atp_tour.to_numpy()
    slams = (rows["slam"].eq("AO") & rows["year"].eq(2025)) | (rows["slam"].eq("RG") & rows["year"].between(2025, 2026))
    f["H2_slams_full"] = f["H1_atp_files"] | slams.to_numpy()
    wta_tour = rows["tour"].eq("wta") & rows["level"].isin(CV.TOUR_LEVELS) & rows["year"].between(2025, 2026)
    f["H3_wta"] = f["H2_slams_full"] | wta_tour.to_numpy()
    return f


def main() -> None:
    players = pd.read_parquet(OUT / "speeds.parquet")
    log("Stage 0 rows and the clock")
    rows = CV.player_rows()
    f = flags(rows, players)

    log("match-level availability")
    mrows = rows.assign(grp=CV.group_of(rows), **{s: f[s].to_numpy() for s in SCENARIOS})
    both = mrows.groupby("match_id").agg(tour=("tour", "first"), year=("year", "first"), grp=("grp", "first"),
                                         slam=("slam", "first"), **{s: (s, "all") for s in SCENARIOS[:4]})
    cm = both.groupby(["tour", "grp", "year"]).agg(matches=("S0_held", "size"),
                                                   **{s: (s, "sum") for s in SCENARIOS[:4]}).reset_index()
    for s in SCENARIOS[:4]:
        cm[f"{s}_share"] = (cm[s] / cm["matches"]).round(4)
    cm.to_csv(OUT / "coverage_matches.csv", index=False)

    log("feature presence on the frame")
    fm = CV.frame_mask(rows)
    targets = rows.index[fm].to_numpy()
    pres = {s: CV.feature_presence(rows, f[s].to_numpy(), targets) for s in SCENARIOS}
    side = rows.loc[targets, ["match_id", "tour", "year", "level", "obs"]].copy()
    for s in SCENARIOS:
        side[s] = pres[s]
    feat = side.groupby("match_id").agg(tour=("tour", "first"), year=("year", "first"), level=("level", "first"),
                                        obs=("obs", "first"), **{s: (s, "all") for s in SCENARIOS})
    feat["window"] = CV.window_of(feat["year"])
    feat["slam"] = feat["level"].eq("GS")
    cf = feat.groupby(["tour", "window", "slam"]).agg(frame=("S0_held", "size"),
                                                      **{s: (s, "sum") for s in SCENARIOS}).reset_index()
    by_year = feat.groupby(["tour", "year", "slam"]).agg(frame=("S0_held", "size"),
                                                         **{s: (s, "sum") for s in SCENARIOS}).reset_index()
    cf.to_csv(OUT / "coverage_feature.csv", index=False)
    by_year.to_csv(OUT / "coverage_feature_by_year.csv", index=False)
    lo, hi = (pd.Timestamp(d).value // 86_400_000_000_000 for d in ("2025-09-10", "2026-09-10"))
    pw = feat[feat["obs"].between(lo, hi)]
    poly = pw.groupby("tour").agg(frame=("S0_held", "size"), **{s: (s, "sum") for s in SCENARIOS})

    hold = {}
    for tour in ("atp", "wta"):
        t = cf[(cf["tour"] == tour) & (cf["window"] == "2025-26")]
        n = {s: int(t[s].sum()) for s in SCENARIOS}
        hold[tour] = {"frame_matches": int(t["frame"].sum()), "with_feature": n,
                      "share": {s: round(v / max(int(t["frame"].sum()), 1), 4) for s, v in n.items()},
                      "power_beta_0.09": {s: round(CV.power_one_sided(v), 3) for s, v in n.items()}}
    summary = {
        "built_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "reads_results": False,
        "scenarios": SCENARIOS,
        "holdout_2025_26": hold,
        "power_note": "two-sided 5% Wald test, SE = 1/sqrt(n * 0.19 * 1.06) as speed_prereg.md section 8; beta 0.09 "
                      "is the 2022-24 replication estimate (probably inflated). The women's row uses the same formula",
        "polymarket_window_10sep2025_10sep2026": {tour: {"frame": int(r["frame"]), **{s: int(r[s]) for s in SCENARIOS}}
                                                  for tour, r in poly.iterrows()},
        "men_2022_24": {s: int(cf[(cf["tour"] == "atp") & (cf["window"] == "2022-24")][s].sum()) for s in SCENARIOS},
    }
    (OUT / "coverage_summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    log("feature coverage:\n" + cf.to_string(index=False))
    log(json.dumps(hold, indent=1))


if __name__ == "__main__":
    main()
