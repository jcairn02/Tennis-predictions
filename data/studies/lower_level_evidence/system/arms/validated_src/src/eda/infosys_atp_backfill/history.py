"""The serve-speed history with the ATP's own decrypted files added (2018 to Oct 2021). Reads no match result.

The current best model's speed adjustment reads the live feed's history: the serve-speed study's frozen panel without the
130 records the input-data audit confirmed impossible (serve_speed_tabpfn/live/speed_panel_frozen_corrected.parquet,
built by src/eda/input_data_audit/speed_live_panel.py). This builds the same history with one source more, by the same
method:
    records   the study's frozen records (serve_speed_tabpfn/speed_records.parquet) plus the new source's, built by the
              panel's own code: panel.build_records(sources={"infosys_atp", "infosys_atp_ks"}) (MatchBeats point means
              and the key statistics, linked through serve_speed_acquisition/speeds.parquet)
    tables    the Stage 0 and timing tables the frozen panel was built on, kept by the rebuild of 8 Oct (no match id
              changed in that rebuild, so the new records' links hold)
    audit     the 130 exclusions applied as for the corrected history; the audit's rule (a first-serve average at or
              above the record's own fastest serve, or 240 km/h and more) applied to the new records too
    choice    panel.build_panel: per player-match, the tier rule (outside the Slams: key statistic, then point mean)
Checks before writing: the frozen records alone reproduce the corrected history exactly; every row that differs from it
is a player-match with a new record, or an own-outlier flag of one of their players.

Writes the live feed's history with the backfill, beside the corrected copy it extends:
data/studies/serve_speed_tabpfn/live/speed_panel_backfilled.parquet and speed_panel_backfilled.json (the SHA-256 of
the corrected copy it was built from and of itself: live/live_panel.py reads it only while both hold). The study's
summary goes to data/studies/infosys_atp_backfill/history.json.
Run: ./python.sh src/eda/infosys_atp_backfill/history.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.input_data_audit import corrections as K  # noqa: E402
from src.eda.input_data_audit import speed_live_panel as SLP  # noqa: E402
from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402
from src.eda.serve_speed_tabpfn.live import live_panel as LP  # noqa: E402

OUT = ROOT / "data" / "studies" / "infosys_atp_backfill"
AUGMENTED = LP.BACKFILLED
RECORD = LP.BACKFILLED_META
META = OUT / "history.json"
NEW_SOURCES = {"infosys_atp", "infosys_atp_ks"}
KEY = ["match_id", "side"]
IMPOSSIBLE_KMH = 240.0


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def use_kept_tables() -> None:
    """The Stage 0 and timing tables the frozen panel (and the corrected history) were built on."""
    P.S0 = SLP.KEPT / "predictability_diagnostic" / "stage0_matches.parquet"
    P.TIMING = SLP.KEPT / "match_timing" / "timing.parquet"


def new_records() -> tuple[pd.DataFrame, dict]:
    rec = P.build_records(NEW_SOURCES)
    impossible = (rec["y_raw"] >= IMPOSSIBLE_KMH) | (np.isfinite(rec["spd_max"].astype(float))
                                                     & (rec["y_raw"] >= rec["spd_max"].astype(float)))
    rec.loc[impossible & rec["valid"], "invalid_reason"] = "audit_impossible"
    rec.loc[impossible, "valid"] = False
    info = {"records": int(len(rec)), "by_source": rec["source"].value_counts().to_dict(),
            "valid": int(rec["valid"].sum()),
            "invalid_reasons": rec.loc[~rec["valid"], "invalid_reason"].value_counts().to_dict(),
            "audit_rule_hits": int(impossible.sum())}
    return rec, info


def build() -> tuple[pd.DataFrame, dict]:
    use_kept_tables()
    rec0 = pd.read_parquet(P.RECORDS)
    table = pd.read_csv(K.SPEED_EXCLUSIONS, dtype=str, keep_default_na=False)
    corrected = pd.read_parquet(LP.CORRECTED)
    order = lambda d: d.sort_values(KEY).reset_index(drop=True)       # noqa: E731
    base_rec, _ = SLP.corrected(rec0, table)
    base = P.build_panel(base_rec)
    pd.testing.assert_frame_equal(order(base), order(corrected), check_dtype=False)   # reproduces the history
    new, info = new_records()
    s0_ids = set(pd.read_parquet(P.S0, columns=["match_id"])["match_id"])
    linked = new["match_id"].notna()
    assert new.loc[linked, "match_id"].isin(s0_ids).all(), "a new record links to a match the kept Stage 0 lacks"
    rec = pd.concat([rec0, new.drop(columns=[c for c in new.columns if c not in rec0.columns])], ignore_index=True)
    rec, hit = SLP.corrected(rec, table)
    aug = P.build_panel(rec)
    # compare with the corrected history
    a, b = order(corrected), order(aug)
    keys_a = set(map(tuple, a[KEY].to_numpy()))
    keys_b = set(map(tuple, b[KEY].to_numpy()))
    assert keys_a <= keys_b, "a player-match of the corrected history is missing"
    added = b[[tuple(k) not in keys_a for k in b[KEY].to_numpy()]]
    bb = b[[tuple(k) in keys_a for k in b[KEY].to_numpy()]].reset_index(drop=True)
    cols = [c for c in a.columns if c not in KEY]
    diff = pd.DataFrame({c: ~((a[c] == bb[c]) | (a[c].isna() & bb[c].isna())) for c in cols})
    value_cols = [c for c in cols if c != "flag_own_outlier"]
    changed = diff[value_cols].any(axis=1)
    new_keys = set(map(tuple, new.loc[new["valid"], KEY].dropna().to_numpy()))
    touched = pd.Series([tuple(k) in new_keys for k in a[KEY].to_numpy()])
    players = set(b.loc[[tuple(k) in new_keys for k in b[KEY].to_numpy()], "player_id"])
    if (changed & ~touched).any():
        raise SystemExit(f"{int((changed & ~touched).sum())} rows without a new record changed value")
    flag_only = diff["flag_own_outlier"] & ~changed
    if (flag_only & ~a["player_id"].isin(players)).any():
        raise SystemExit("an own-outlier flag changed for a player without a new record")
    ch = a[changed.to_numpy()].merge(bb[changed.to_numpy()], left_index=True, right_index=True, suffixes=("_before",
                                                                                                         "_after"))
    info.update({
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "inputs": {"frozen_records_sha256": sha(P.RECORDS), "corrected_history_sha256": sha(LP.CORRECTED),
                   "exclusions_sha256": sha(K.SPEED_EXCLUSIONS), "speeds_sha256": sha(P.SPEEDS),
                   "atp_points_sha256": sha(P.INFO_ATP_POINTS),
                   "stage0": P.S0.relative_to(ROOT).as_posix(), "timing": P.TIMING.relative_to(ROOT).as_posix()},
        "corrected_history_reproduced": True,
        "rows_corrected": int(len(a)), "rows_augmented": int(len(b)),
        "use_corrected": int(a["use"].sum()), "use_augmented": int(b["use"].sum()),
        "added_player_matches": int(len(added)), "added_use": int(added["use"].sum()),
        "added_by_source": added["source"].value_counts().to_dict(),
        "added_drop_reasons": added.loc[~added["use"], "drop_reason"].value_counts().to_dict(),
        "added_by_year_event": {f"{y}|{t}": int(n) for (y, t), n in
                                added[added["use"]].groupby(["year", "tournament_id"]).size().items()},
        "changed_player_matches": int(changed.sum()),
        "changed_source_before_after": {f"{s0}->{s1}": int(n) for (s0, s1), n in
                                        ch.groupby(["source_before", "source_after"]).size().items()},
        "changed_y_abs_kmh": {"median": float((ch["y_after"] - ch["y_before"]).abs().median()) if len(ch) else None,
                              "max": float((ch["y_after"] - ch["y_before"]).abs().max()) if len(ch) else None},
        "changed_use_before_after": {"before": int(ch["use_before"].sum()) if len(ch) else 0,
                                     "after": int(ch["use_after"].sum()) if len(ch) else 0},
        "own_outlier_flag_changes_on_the_same_players": int(flag_only.sum()),
        "atp_use_rows_by_year": {"corrected": a[a["use"] & a["tour"].eq("atp")].groupby("year").size()
                                 .loc[2017:2022].to_dict(),
                                 "augmented": b[b["use"] & b["tour"].eq("atp")].groupby("year").size()
                                 .loc[2017:2022].to_dict()},
    })
    return aug, info


def main() -> int:
    aug, info = build()
    OUT.mkdir(parents=True, exist_ok=True)
    aug.to_parquet(AUGMENTED, index=False)
    info["augmented"] = AUGMENTED.relative_to(ROOT).as_posix()
    info["augmented_sha256"] = sha(AUGMENTED)
    record = {"what": "the live feed's corrected speed history plus the ATP Stats Centre's decrypted files of 2018 to "
                      "Oct 2021 (docs/studies/infosys_atp_backfill/)",
              "built_by": "src/eda/infosys_atp_backfill/history.py", "generated_at": info["generated_at"],
              "corrected_sha256": info["inputs"]["corrected_history_sha256"],
              "backfilled_sha256": info["augmented_sha256"], "rows": info["rows_augmented"],
              "added_player_matches": info["added_player_matches"],
              "changed_player_matches": info["changed_player_matches"]}
    RECORD.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    META.write_text(json.dumps(info, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(info, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
