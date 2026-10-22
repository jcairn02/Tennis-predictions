"""Step 1: link the build tree's tour-level qualifying matches to OddsTrader's played singles events. No result is read.

tennis-data.co.uk holds no qualifying match, so the odds step's link (odds_sources/table.py: tennis-data rows to
OddsTrader events) never reaches one. This link starts from Stage 0 instead:
    * Stage 0's side A and side B names, each in every "surname span + first initial" form (the sharp benchmark's
      td_variants), as the pair "A > B";
    * OddsTrader's played singles events (status complete or retired), each pair in both orders
      (sharp_benchmark/build.candidate_pairs: a pair an event gives in both orders, two players with the same surname
      and initial, is dropped); away_is_a says whether OddsTrader's away player is side A;
    * the same tour, and OddsTrader's listed start day (UTC) from the match clock's earliest start minus 1 day to its
      latest finish plus 1 day (the clock: 97% of these matches have an exact day);
    * the nearest day wins (0 inside the clock's window), then an event with BetOnline's close, then the lower event id;
      one event per match and one match per event: an event nearest to two matches leaves both out.

Writes data/studies/qualifying_targets/oddstrader_link.parquet (match_id, eid, away_is_a, gap_days, ...),
oddstrader_eids.csv (the events for the every-book pull) and link_counts.json (link rates by tour, season and kind,
ambiguities, samples for reading by hand).

Run: ./python.sh src/eda/qualifying_targets/link.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.merge_feasibility import scan as S  # noqa: E402
from src.eda.qualifying_targets import common as C  # noqa: E402
from src.eda.sharp_benchmark import build as BLD  # noqa: E402

WINDOW_PAD = 1          # days added on both sides of the clock's window


def ot_markets() -> pd.DataFrame:
    """OddsTrader's played singles events as the market frame BLD.candidate_pairs expects (eid as condition_id;
    name_a = the away player, so a_won there means 'the away player is the pair's first')."""
    ev = pd.read_parquet(C.OT_EVENTS, columns=["eid", "tour", "singles", "es", "dt_ms", "home_first", "home_last",
                                               "away_first", "away_last"])
    ev = ev[ev["singles"].astype(bool) & ev["es"].isin(["complete", "retired"])].copy()
    full = lambda first, last: (first.fillna("") + " " + last.fillna("")).str.strip()  # noqa: E731
    bo = pd.read_parquet(C.OT / "betonline_matches.parquet", columns=["eid", "mw_close_home", "mw_close_away"])
    close = set(bo.loc[bo["mw_close_home"].notna() & bo["mw_close_away"].notna(), "eid"].astype("int64"))
    return pd.DataFrame({
        "condition_id": ev["eid"].astype("int64").to_numpy(), "tour": ev["tour"].str.lower().to_numpy(),
        "day": pd.to_datetime(ev["dt_ms"], unit="ms", utc=True).dt.tz_convert(None).dt.normalize().to_numpy(),
        "name_a": full(ev["away_first"], ev["away_last"]).to_numpy(),
        "name_b": full(ev["home_first"], ev["home_last"]).to_numpy(),
        "has_close": ev["eid"].astype("int64").isin(close).to_numpy(), "volume": 0.0})


def stage0_rows() -> pd.DataFrame:
    m = C.qualifying_matches()
    p = pd.read_parquet(C.TREE_PLAYERS, columns=["match_id", "side", "player_name"])
    p["match_id"] = p["match_id"].astype(str)
    nm = p[p["match_id"].isin(set(m["match_id"]))].pivot(index="match_id", columns="side", values="player_name")
    m["name_a"] = nm.reindex(m["match_id"])["A"].to_numpy()
    m["name_b"] = nm.reindex(m["match_id"])["B"].to_numpy()
    tm = pd.read_parquet(C.TREE_TIMING, columns=["match_id", "es", "lf", "exact"])
    tm["match_id"] = tm["match_id"].astype(str)
    m = m.merge(tm, on="match_id", how="left", validate="one_to_one")
    if m[["es", "lf"]].isna().any().any() or m[["name_a", "name_b"]].isna().any().any():
        raise SystemExit("qualifying matches without a clock window or a name")
    return m


def link() -> tuple[pd.DataFrame, dict]:
    m = stage0_rows()
    pm = ot_markets()
    rows = pd.DataFrame({"match_id": m["match_id"], "tour": m["tour"], "es": m["es"].astype(float),
                         "lf": m["lf"].astype(float), "av": m["name_a"].map(S.td_variants),
                         "bv": m["name_b"].map(S.td_variants)}).explode("av").explode("bv")
    rows["pair"] = rows["av"] + ">" + rows["bv"]
    rows = rows.drop(columns=["av", "bv"]).drop_duplicates(["match_id", "pair"])
    cand = BLD.candidate_pairs(pm)
    x = rows.merge(cand, on="pair", suffixes=("", "_ot"))
    x = x[x["tour_ot"].isna() | (x["tour_ot"] == x["tour"])]
    d = C.day_number(x["day"])
    lo, hi = x["es"].to_numpy() - WINDOW_PAD, x["lf"].to_numpy() + WINDOW_PAD
    x = x[(d >= lo) & (d <= hi)].copy()
    d = C.day_number(x["day"])
    x["gap_days"] = np.where(d < x["es"], x["es"] - d, np.where(d > x["lf"], d - x["lf"], 0.0))
    x = x.rename(columns={"condition_id": "eid", "a_won": "away_is_a"})
    x = x.merge(pm[["condition_id", "has_close"]].rename(columns={"condition_id": "eid"}), on="eid", how="left")
    x = x.drop_duplicates(["match_id", "eid", "away_is_a"])
    # a match whose pair forms meet one event in both orientations cannot say who is who: out
    both = x.groupby(["match_id", "eid"])["away_is_a"].transform("nunique") > 1
    oriented_both = int(x.loc[both, "match_id"].nunique())
    x = x[~both]
    x = x.sort_values(["gap_days", "has_close", "eid"], ascending=[True, False, True])
    near = x.groupby("match_id")["gap_days"].transform("min")
    multi = x[x["gap_days"] == near].groupby("match_id")["eid"].nunique()
    best = x.groupby("match_id", sort=False).head(1)
    best = best[best["gap_days"] == best.groupby("eid")["gap_days"].transform("min")]
    tie = best.groupby("eid")["match_id"].transform("size") > 1
    out = best[~tie][["match_id", "eid", "away_is_a", "gap_days", "has_close"]].reset_index(drop=True)
    out = out.merge(m[["match_id", "tour", "year", "kind", "level", "round", "tournament_name", "name_a", "name_b",
                       "exact"]], on="match_id", how="left", validate="one_to_one")
    info = {"qualifying_matches": int(len(m)), "linked": int(len(out)),
            "matches_with_an_event_in_both_orientations_dropped": oriented_both,
            "matches_with_several_events_at_the_nearest_day": int((multi > 1).sum()),
            "events_nearest_to_two_matches_dropped": int(best[tie]["eid"].nunique()),
            "gap_days": out["gap_days"].value_counts().sort_index().to_dict()}
    return out, m, info


def main() -> int:
    out, m, info = link()
    C.OUT.mkdir(parents=True, exist_ok=True)
    out.to_parquet(C.LINK, index=False)
    pd.DataFrame({"eid": sorted(out["eid"].astype("int64").unique())}).to_csv(C.EIDS, index=False)
    m["linked"] = m["match_id"].isin(set(out["match_id"]))
    rate = m.groupby(["tour", "year", "kind"])["linked"].agg(["size", "sum", "mean"]).reset_index()
    rate.columns = ["tour", "year", "kind", "matches", "linked", "rate"]
    core = m[m["year"].between(2019, 2025)]
    pm_names = pd.read_parquet(C.OT_EVENTS, columns=["eid", "home_first", "home_last", "away_first", "away_last",
                                                    "dt_ms", "group"])
    sample = out.sample(40, random_state=20261022).merge(pm_names, on="eid", how="left")
    sample["ot_day"] = pd.to_datetime(sample["dt_ms"], unit="ms", utc=True).dt.strftime("%Y-%m-%d %H:%M")
    unl = m[~m["linked"]].sample(min(40, int((~m["linked"]).sum())), random_state=20261022)
    info.update({"rate_2019_2025": float(core["linked"].mean()), "rate_all": float(m["linked"].mean()),
                 "rates": rate.to_dict("records"),
                 "sample_linked": sample[["match_id", "tournament_name", "round", "name_a", "name_b", "away_is_a",
                                          "away_first", "away_last", "home_first", "home_last", "ot_day", "group",
                                          "gap_days"]].to_dict("records"),
                 "sample_unlinked": unl[["match_id", "tournament_name", "round", "name_a", "name_b"]].to_dict("records"),
                 "sources": {"stage0": C.sha256_file(C.TREE_STAGE0), "timing": C.sha256_file(C.TREE_TIMING),
                             "events": C.sha256_file(C.OT_EVENTS)}})
    C.write_json(C.OUT / "link_counts.json", info)
    C.log(f"linked {info['linked']:,} of {info['qualifying_matches']:,}; 2019-2025 rate {info['rate_2019_2025']:.3f}; "
          f"{out['eid'].nunique():,} events -> {C.EIDS.name}")
    print(rate.pivot_table(index=["tour", "kind"], columns="year", values="rate").round(3).to_string())
    if info["rate_2019_2025"] < 0.80:
        C.log("STOP RULE: fewer than 80% of the 2019-2025 qualifying matches link")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
