"""The early-price sample: the confirmation's 2025-2026 test matches linked to their Polymarket market, with the price
at 24 hours and 30 minutes before the listed start, and the timing facts that decide which matches give a clean test.

Added on the owner's request of 6 Oct 2026 ("run it"): does the new representation carry information the early price
lacks? Nothing here reads a result or a forecast; it only builds the sample (the plan is early_price_plan.md).

    link        a frame match (tour, tennis-data day, winner "Surname I.", loser) to the row of the sharp-benchmark
                study's match table (data/studies/sharp_benchmark/matches.parquet), which carries the linked
                Polymarket market and its price of the row's winner at nine horizons before the listed start
                (pw_pm_m1440 = 24 hours, pw_pm_m30 = 30 minutes, the study's closing benchmark)
    p_early_a, p_close_a     those prices as P(A wins), in the frame's orientation
    opener      both players' first match at this event (no earlier round of the same tournament and start date)
    buffer_ok   both players' previous played match (any level) surely finished at least 3 days before the listed
                start's UTC day: latest possible finish day (match-timing study) <= start day - 3. A local day ends at
                most 1.33 days after its own UTC midnight (UTC-8), so 3 days guarantees the previous result was known
                24 hours before the listed start in every time zone
    clean       opener & buffer_ok & both prices present: every input of the forecast existed 24 hours before the start

Writes data/studies/surface_elo_pieces/early_price_frame.parquet and early_price_counts.json.
Run: ./python.sh src/eda/surface_elo_pieces/early_price_frame.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic.stage4_features import prev_visible  # noqa: E402
from src.eda.surface_elo_pieces import common as C  # noqa: E402

SHARP = ROOT / "data" / "studies" / "sharp_benchmark" / "matches.parquet"
ODDS = C.PD_OUT / "stage1_odds.parquet"
BUFFER_DAYS = 3


def previous_match_lf(m: pd.DataFrame, lf: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per match, for player A and player B: the latest-finish day of the player's previous played match (any level,
    Stage 1's time rule: an earlier event or an earlier round of the same event), and whether that previous match was an
    earlier round of the same event."""
    n = len(m)
    rows = pd.DataFrame({
        "player_id": np.column_stack([m["player_a_id"], m["player_b_id"]]).reshape(-1),
        "tour": np.repeat(m["tour"].to_numpy(), 2),
        "tournament_date": np.repeat(m["tournament_date"].to_numpy(), 2),
        "tournament_id": np.repeat(m["tournament_id"].to_numpy(), 2),
        "round_order": np.repeat(m["round_order"].to_numpy(), 2),
        "order": np.repeat(m["order"].to_numpy(), 2),
        "played": np.repeat(m["status"].isin(["completed", "retired"]).to_numpy(), 2)})
    rows["day"] = rows["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    rows["ev"] = pd.factorize(rows["tournament_id"].astype(str) + "|" + rows["tournament_date"].astype(str))[0]
    rows["pcode"] = pd.factorize(rows["tour"] + "|" + rows["player_id"])[0]
    prev = prev_visible(rows, rows["played"].to_numpy())
    ev = rows["ev"].to_numpy()
    lf2 = np.repeat(lf, 2)
    prev_lf = np.where(prev >= 0, lf2[np.maximum(prev, 0)], -np.inf)          # no previous match: no constraint
    same_event = (prev >= 0) & (ev[np.maximum(prev, 0)] == ev)
    return prev_lf.reshape(n, 2), same_event.reshape(n, 2), (prev >= 0).reshape(n, 2)


def main() -> int:
    fr = pd.read_parquet(C.OUT / "frame.parquet", columns=["match_id", "tour", "season", "a_won", "debut_season",
                                                           "tournament_date", "x_odds_logit", "x_surface"])
    fr = fr[fr["season"].isin([2025, 2026])].reset_index(drop=True)
    # frame match -> its tennis-data row (Stage 1's link: tour, day, winner and loser in tennis-data's spelling)
    od = pd.read_parquet(ODDS, columns=["match_id", "td_date", "td_winner", "td_loser"])
    fr = fr.merge(od, on="match_id", how="left", validate="one_to_one")
    sb = pd.read_parquet(SHARP, columns=["tour", "date", "winner", "loser", "condition_id", "pm_start_ts",
                                         "pw_pm_m1440", "pw_pm_m360", "pw_pm_m30", "pm_volume"])
    sb["td_date"] = pd.to_datetime(sb["date"]).dt.normalize()
    key = ["tour", "td_date", "winner", "loser"]
    dup = sb.duplicated(key, keep=False)
    sb = sb[~dup].rename(columns={"winner": "td_winner", "loser": "td_loser"})
    fr["td_date"] = pd.to_datetime(fr["td_date"]).dt.normalize()
    fr = fr.merge(sb, on=["tour", "td_date", "td_winner", "td_loser"], how="left", validate="many_to_one")
    a = fr["a_won"].to_numpy(bool)
    for h, col in (("early", "pw_pm_m1440"), ("6h", "pw_pm_m360"), ("close", "pw_pm_m30")):
        pw = fr[col].to_numpy(dtype=float)
        fr[f"p_{h}_a"] = np.where(a, pw, 1 - pw)                    # the winner's price -> P(A wins)
    # timing: previous matches of both players, from Stage 0 and the leak-proof timeline
    m = pd.read_parquet(C.STAGE0, columns=["match_id", "tour", "tournament_id", "tournament_date", "round_order",
                                           "order", "status", "player_a_id", "player_b_id"])
    tm = pd.read_parquet(C.TIMING, columns=["match_id", "lf"]).set_index("match_id").reindex(m["match_id"])
    prev_lf, same_event, has_prev = previous_match_lf(m, tm["lf"].to_numpy(dtype=float))
    idx = pd.Series(np.arange(len(m)), index=m["match_id"]).reindex(fr["match_id"]).to_numpy()
    start_day = np.floor(pd.to_numeric(fr["pm_start_ts"], errors="coerce").to_numpy(dtype=float) / 86400.0)
    if np.nanmedian(start_day) > 1e6:                               # milliseconds, not seconds
        start_day = np.floor(pd.to_numeric(fr["pm_start_ts"], errors="coerce").to_numpy(dtype=float) / 86400000.0)
    fr["opener"] = ~same_event[idx].any(axis=1)
    fr["prev_lf_max"] = prev_lf[idx].max(axis=1)
    fr["start_day_utc"] = start_day
    fr["buffer_ok"] = fr["prev_lf_max"] <= fr["start_day_utc"] - BUFFER_DAYS
    fr["has_early"] = np.isfinite(fr["p_early_a"]) & np.isfinite(fr["p_close_a"])
    fr["clean"] = fr["opener"] & fr["buffer_ok"] & fr["has_early"] & ~fr["debut_season"]
    fr["all_early"] = fr["has_early"] & ~fr["debut_season"]
    fr.to_parquet(C.OUT / "early_price_frame.parquet", index=False)
    counts = {"frame_2025_2026": int(len(fr)), "linked_to_polymarket": int(fr["condition_id"].notna().sum()),
              "with_24h_and_30m_prices": int(fr["has_early"].sum()), "openers": int(fr["opener"].sum()),
              "openers_with_buffer": int((fr["opener"] & fr["buffer_ok"]).sum()),
              "clean_sample": int(fr["clean"].sum()), "all_with_prices_excl_debut": int(fr["all_early"].sum()),
              "clean_by_tour": fr[fr["clean"]].groupby("tour").size().to_dict(),
              "clean_by_season": fr[fr["clean"]].groupby("season").size().to_dict(),
              "duplicate_sharp_keys_dropped": int(dup.sum())}
    C.write_json(C.OUT / "early_price_counts.json", counts)
    print(counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
