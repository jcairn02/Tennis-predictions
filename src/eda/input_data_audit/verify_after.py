"""After the corrections' live rebuild: the audit's detectors on the tables before and after it.

Reads the Stage 0 and Stage 1 tables a rebuild replaced (data/studies/data_continuity/rebuilds/<stamp>/replaced/) and the
live ones, and counts, before and after:
    exchanged-box fits     matches that fit their score only with the two box scores exchanged (by edition)
    definition test        rows whose second-serve points won + double faults exceed the second serves (WTA 2015)
    WTA 2015 window        the 30 events' pooled second-serve points won
    Adelaide 2 2022        player rows whose nine counts equal an Adelaide 2021 player row's
    split ids              second ids from 25 May 2026 whose name has an established id (the audit's rule;
                           also writes frame_split_ids_before.csv and _after.csv)
    ages                   player rows aged 100 or more
    odds                   the corrected rows' market probability
Writes data/studies/input_data_audit/fixes/after_rebuild.json.
Run: ./python.sh src/eda/input_data_audit/verify_after.py --stamp <rebuild stamp>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.eda.input_data_audit import common as C  # noqa: E402
from src.eda.input_data_audit import corrections as K  # noqa: E402
from src.eda.input_data_audit import model_frame_checks as F  # noqa: E402

LIVE = ROOT / "data" / "studies" / "predictability_diagnostic"


def split_pairs(key: str) -> int:
    """The audit's split-id rule (model_frame_checks.split_ids, which also writes frame_split_ids_<key>.csv)."""
    summary: dict = {}
    F.split_ids(key, C.load_model_frame(["match_id"]), summary)
    return int(summary[f"split_ids_{key}"]["pairs"])


def measures(key: str) -> dict:
    rows = C.load_player_rows(key)
    a = rows[rows["side"].eq("A")]
    flags = C.identity_flags(a)
    fits = a.loc[flags["swapped_box_fits"].to_numpy()]
    w15 = rows[rows["tour"].eq("wta") & rows["year"].eq(2015) & rows["svpt"].notna()]
    events = pd.read_csv(C.OUT / "box_wta2015_events.csv")
    window = events.loc[events["in_fault"], "tournament_name"]
    win = w15[w15["tournament_name"].isin(window) & ~w15["qualifying"]]
    second = (win["second_won"].sum() / (win["svpt"] - win["first_in"]).sum()) if len(win) else float("nan")
    box = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"]
    ade = rows[rows["tour"].eq("wta") & rows["tournament_name"].isin(["Adelaide", "Adelaide 2"])
               & rows["year"].isin([2021, 2022]) & rows["svpt"].notna()]
    sig = ade[box].astype(float).fillna(-1).apply(tuple, axis=1)
    copies = int(sig[ade["year"].eq(2022)].isin(set(sig[ade["year"].eq(2021)])).sum())
    p = pd.read_parquet(C.SNAPSHOTS[key] / "stage0_match_players.parquet", columns=["age"])
    return {"exchanged_box_fits": int(len(fits)),
            "exchanged_box_fits_by_event": {f"{n} {y}": int(v) for (n, y), v in fits.groupby(["tournament_name", "year"])
                                            .size().sort_values(ascending=False).head(8).items()},
            "wta2015_definition_test_failures": int(C.serve_points_exclude_dfs(w15).sum()),
            "wta2015_window_second_won_pct": round(100 * float(second), 2),
            "adelaide2_2022_rows_equal_to_an_adelaide_2021_row": copies,
            "split_ids": split_pairs(key),
            "ages_100_or_more": int(p["age"].ge(100).sum())}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stamp", required=True)
    a = ap.parse_args()
    before = ROOT / "data/studies/data_continuity/rebuilds" / a.stamp / "replaced/data/studies/predictability_diagnostic"
    C.SNAPSHOTS["before"], C.SNAPSHOTS["after"] = before, LIVE
    out = {"stamp": a.stamp, "before": measures("before"), "after": measures("after")}
    want = pd.read_csv(K.ODDS_CORRECTIONS, dtype=str, keep_default_na=False)
    ob = pd.read_parquet(before / "stage1_odds.parquet").set_index("match_id")
    oa = pd.read_parquet(LIVE / "stage1_odds.parquet").set_index("match_id")
    out["odds"] = [{"match_id": m, "p_avg_a_before": round(float(ob.loc[m, "p_avg_a"]), 4),
                    "p_avg_a_after": round(float(oa.loc[m, "p_avg_a"]), 4)} for m in want["match_id"]]
    (K.FIXES / "after_rebuild.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
