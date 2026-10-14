"""The Live Tennis API sample's v1.0.2 against v1.0.0, file by file and column by column (work package P3 of
docs/studies/gap_downloads/collection-plan.md).

The provider's note on v1.0.2 (Zenodo record 23018680, 28 Sep 2026): "Every other data byte is unchanged" and only two
columns moved, from Israel local time to UTC: matches.csv.gz's scheduled_time_utc (120,758 rows back 3 hours, 52,813
back 2) and points_sample_2026-06.csv.gz's timestamp_utc (all 951,064 rows back 3 hours). This checks that against the
two copies kept side by side in data/raw/public_dump/live_tennis_api_zenodo/ (v1.0.0 at the root, v1.0.2 in
record_23018680/):
    * the same rows in the same order, the same columns, every other column identical;
    * each corrected time equal to the v1.0.0 time read as Israel wall-clock time and converted to UTC, with the
      hour repeated when clocks go back read either way (summer or winter time), counted separately.

Writes data/studies/public_data_dump/live_tennis_api_versions.json.
Run: ./python.sh src/eda/public_data_dump/lta_versions.py
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

from src.ingest.public_dump import live_tennis_api_zenodo as Z  # noqa: E402

RAW = ROOT / "data" / "raw" / "public_dump" / Z.SOURCE
OUT = ROOT / "data" / "studies" / "public_data_dump" / "live_tennis_api_versions.json"
FILES = {"matches.csv.gz": ("match_id", "scheduled_time_utc"), "points_sample_2026-06.csv.gz": (None, "timestamp_utc"),
         "players.csv.gz": ("player_id", None)}


def israel_to_utc(naive: pd.Series, summer: bool) -> pd.Series:
    flags = np.full(len(naive), summer)
    return (naive.dt.tz_localize("Asia/Jerusalem", ambiguous=flags, nonexistent="shift_forward")
            .dt.tz_convert("UTC").dt.tz_localize(None))


def compare(old: pd.DataFrame, new: pd.DataFrame, key: str | None, time: str | None) -> dict:
    out = {"rows": [len(old), len(new)], "columns_identical": list(old.columns) == list(new.columns)}
    if key:
        out["keys_in_the_same_order"] = bool(old[key].equals(new[key]))
    rest = [c for c in old.columns if c != time]
    out["other_columns_identical"] = bool(old[rest].equals(new[rest]))
    if time:
        a = pd.to_datetime(old[time], format="mixed", errors="coerce")
        b = pd.to_datetime(new[time], format="mixed", errors="coerce")
        hours = ((a - b) / pd.Timedelta(hours=1)).round(4)
        out["hours_moved_back"] = {str(k): int(v) for k, v in hours.value_counts(dropna=False).items()}
        summer, winter = israel_to_utc(a, True).eq(b), israel_to_utc(a, False).eq(b)
        out["equal_to_israel_time_converted"] = int(summer.sum())
        out["equal_only_reading_the_repeated_hour_as_winter_time"] = int((~summer & winter).sum())
        out["equal_to_neither"] = int((~summer & ~winter).sum())
        out["v1_0_2_first_last"] = [str(b.min()), str(b.max())]
    return out


def main() -> int:
    new_dir = RAW / f"record_{Z.RECORD_ID}"
    summary = {"v1_0_0": {"record": Z.FIRST_RECORD, "folder": str(RAW.relative_to(ROOT).as_posix())},
               "v1_0_2": {"record": Z.RECORD_ID, "folder": str(new_dir.relative_to(ROOT).as_posix())},
               "provider_note": {"matches.csv.gz": {"3.0": 120758, "2.0": 52813}, "points_sample_2026-06.csv.gz": {"3.0": 951064}},
               "files": {}}
    for name, (key, time) in FILES.items():
        old = pd.read_csv(RAW / name, dtype=str, keep_default_na=False)
        new = pd.read_csv(new_dir / name, dtype=str, keep_default_na=False)
        summary["files"][name] = compare(old, new, key, time)
        print(name, json.dumps(summary["files"][name]))
    OUT.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
