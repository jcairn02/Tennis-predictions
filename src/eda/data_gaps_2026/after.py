"""The gaps before and after a feed snapshot (outcome-free): the coverage check on a Stage 0 built from today's files,
with the accepted packages merged (before) and with the snapshot merged instead of the package it supersedes (after),
through a scratch registry, so nothing is accepted by running this. Also the snapshot's additions by tour, level and
month, and how many carry a box score.
Writes data/studies/data_gaps_2026/coverage/after_<snapshot>/ (the coverage outputs, additions.csv, summary.json).
Run: ./python.sh src/eda/data_gaps_2026/after.py --stage0 <a Stage 0 folder> --snapshot <feed>/<snapshot>
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import additions as AD  # noqa: E402
from src.eda.data_gaps_2026 import coverage as CV  # noqa: E402


def additions_table(snap: Path) -> pd.DataFrame:
    m = pd.read_parquet(snap / "matches.parquet", columns=["match_id", "tour", "map_level", "tournament_date",
                                                           "has_box"])
    m["month"] = pd.to_datetime(m["tournament_date"]).dt.to_period("M").astype(str)
    return (m.groupby(["tour", "map_level", "month"]).agg(added=("match_id", "size"), with_box=("has_box", "sum"))
            .reset_index())


def run(stage0: Path, target: str, as_of: pd.Timestamp, supersedes: str | None = "men_2026_ch_chq") -> dict:
    snap = AD.ACCEPTED / target
    out = CV.OUT / f"after_{target.replace('/', '_')}"
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        feed, name = target.split("/")
        shutil.copytree(snap, tmp / feed / name)
        cur = AD.index()
        keep = [p for p in cur["packages"] if p != supersedes]
        for p in keep:
            shutil.copytree(AD.ACCEPTED / p, tmp / p)
        (tmp / "accepted.json").write_text(json.dumps({"packages": keep, "feeds": {feed: name}}), encoding="utf-8")
        after = CV.run(stage0, True, as_of, None, out / "after", accepted=tmp)
    before = CV.run(stage0, True, as_of, None, out / "before")
    t = additions_table(snap)
    t.to_csv(out / "additions.csv", index=False)
    summary = {"stage0": str(stage0), "snapshot": target, "as_of": str(as_of.date()), "superseded": supersedes,
               "before": {"alarm": before["alarm"], "cells": before["alarm_cells"]},
               "after": {"alarm": after["alarm"], "cells": after["alarm_cells"], "merged": after["packages"]},
               "added_by_tour_level": t.groupby(["tour", "map_level"])[["added", "with_box"]].sum().reset_index()
               .to_dict("records")}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage0", required=True)
    ap.add_argument("--snapshot", required=True, help="<feed>/<snapshot> under the accepted additions' folder")
    ap.add_argument("--as-of", default=None)
    a = ap.parse_args()
    s = run(Path(a.stage0), a.snapshot, pd.Timestamp(a.as_of) if a.as_of else pd.Timestamp.now().normalize())
    print(json.dumps({k: s[k] for k in ("before", "after")}, indent=1, default=str)[:6000])
    print(pd.DataFrame(s["added_by_tour_level"]).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
