"""The live speed feed's history without the serve-speed records all three reviewers confirmed impossible.

Decision: docs/decisions/2026-10-08-corrupt-data-fixes.md (the owner, 8 Oct 2026: "Yes apply them" to the live speed
feed). The study's frozen panel (data/studies/serve_speed_tabpfn/speed_panel.parquet) stays as it is: it is a frozen input
of the pre-registered serve-speed study. The live feed (src/eda/serve_speed_tabpfn/live/live_panel.py) reads this
corrected copy instead.

How: the study's own record table (speed_records.parquet) marks every record's validity as a candidate. The records in
data/studies/input_data_audit/fixes/speed_exclusions.csv (a first-serve average at or above the record's own fastest
serve, or 240 km/h and more) are marked not valid ("audit_impossible"), and the study's own choice
(panel.build_panel) runs again, on the Stage 0 and timing tables the frozen panel was built on (kept by the rebuild of 8
Oct, 2026-10-08T1853Z). So each affected player-match takes its next valid record, by the panel's own precedence, or
none. Checks before writing: the same choice without the exclusions reproduces the frozen panel exactly; the corrected
panel differs from it only on rows of the affected player-matches' players.

Writes data/studies/serve_speed_tabpfn/live/speed_panel_frozen_corrected.parquet and speed_panel_frozen_corrected.json.
Run: ./python.sh src/eda/input_data_audit/speed_live_panel.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.eda.input_data_audit import corrections as K  # noqa: E402
from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402
from src.eda.serve_speed_tabpfn.live import common as LC  # noqa: E402

KEPT = ROOT / "data" / "studies" / "data_continuity" / "rebuilds" / "2026-10-08T1853Z" / "replaced" / "data" / "studies"
OUT = LC.OUT / "speed_panel_frozen_corrected.parquet"
META = LC.OUT / "speed_panel_frozen_corrected.json"
KEY = ["match_id", "side"]


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def corrected(rec: pd.DataFrame, table: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """The records with the table's records no longer valid candidates."""
    hit = K.speed_exclusions(rec, table)
    rec = rec.copy()
    rec.loc[hit & rec["valid"], "invalid_reason"] = "audit_impossible"
    rec.loc[hit, "valid"] = False
    return rec, hit


def main() -> int:
    P.S0 = KEPT / "predictability_diagnostic" / "stage0_matches.parquet"      # what the frozen panel was built on
    P.TIMING = KEPT / "match_timing" / "timing.parquet"
    rec = pd.read_parquet(P.RECORDS)
    frozen = pd.read_parquet(P.PANEL)
    table = pd.read_csv(K.SPEED_EXCLUSIONS, dtype=str, keep_default_na=False)
    base = P.build_panel(rec)
    order = lambda d: d.sort_values(KEY).reset_index(drop=True)               # noqa: E731
    pd.testing.assert_frame_equal(order(base), order(frozen), check_dtype=False)   # the choice reproduces the panel
    rec2, hit = corrected(rec, table)
    new = P.build_panel(rec2)
    if len(new) != len(frozen) or set(map(tuple, new[KEY].to_numpy())) != set(map(tuple, frozen[KEY].to_numpy())):
        raise SystemExit("the corrected panel does not hold the frozen panel's player-matches")
    a, b = order(frozen), order(new)
    cols = [c for c in a.columns if c not in KEY]
    diff = pd.DataFrame({c: ~((a[c] == b[c]) | (a[c].isna() & b[c].isna())) for c in cols})
    changed = diff.any(axis=1)
    hit_rows = set(map(tuple, rec.loc[hit, KEY].to_numpy()))
    affected = pd.Series([tuple(k) in hit_rows for k in a[KEY].to_numpy()])
    value_cols = [c for c in cols if c != "flag_own_outlier"]
    value_changed = diff[value_cols].any(axis=1)
    players = set(a.loc[affected, "player_id"])
    outside = value_changed & ~affected
    flag_only = changed & ~value_changed
    if outside.any() or (flag_only & ~a["player_id"].isin(players)).any():
        raise SystemExit(f"{int(outside.sum())} rows outside the affected player-matches changed value")
    chosen_before = a["source_key"].astype(str) + "|" + a["source"].astype(str)
    excluded_keys = set(rec.loc[hit, "source_key"].astype(str) + "|" + rec.loc[hit, "source"].astype(str))
    was_chosen = affected & chosen_before.isin(excluded_keys)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    new.to_parquet(OUT, index=False)
    meta = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "decision": "docs/decisions/2026-10-08-corrupt-data-fixes.md",
        "frozen_panel_sha256": sha(P.PANEL), "records_sha256": sha(P.RECORDS),
        "exclusions_sha256": sha(K.SPEED_EXCLUSIONS), "corrected_sha256": sha(OUT),
        "built_on": {"stage0": P.S0.relative_to(ROOT).as_posix(), "timing": P.TIMING.relative_to(ROOT).as_posix()},
        "excluded_records": int(hit.sum()), "excluded_already_invalid": int((hit & ~rec["valid"]).sum()),
        "player_matches_with_an_excluded_record": int(affected.sum()),
        "excluded_record_was_the_chosen_value": int(was_chosen.sum()),
        "rows_whose_value_changed": int(value_changed.sum()),
        "now_from": b.loc[was_chosen.to_numpy(), "source"].value_counts().to_dict(),
        "use_before": int(a.loc[was_chosen, "use"].sum()), "use_after": int(b.loc[was_chosen.to_numpy(), "use"].sum()),
        "outlier_flag_changes_on_the_same_players": int(flag_only.sum()),
        "changes": [{"match_id": m, "side": s, "source_before": sb, "y_before": float(yb), "use_before": bool(ub),
                     "source_after": sa, "y_after": (None if pd.isna(ya) else float(ya)), "use_after": bool(ua)}
                    for m, s, sb, yb, ub, sa, ya, ua in zip(
                        a.loc[was_chosen, "match_id"], a.loc[was_chosen, "side"], a.loc[was_chosen, "source"],
                        a.loc[was_chosen, "y"], a.loc[was_chosen, "use"], b.loc[was_chosen.to_numpy(), "source"],
                        b.loc[was_chosen.to_numpy(), "y"], b.loc[was_chosen.to_numpy(), "use"])],
    }
    META.write_text(json.dumps(meta, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in meta.items() if k != "changes"}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
