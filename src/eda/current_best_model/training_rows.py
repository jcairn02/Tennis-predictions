"""The live fit's training rows (the owner, 20 Oct 2026; docs/decisions/2026-10-09-adoption-by-change-class.md, its
amendment): season Y trains on 2013 .. Y - 1 plus, after a retrain the owner calls, every season-Y match of the
instance's frame whose result counts by the retrain's cut-off under the match clock (lf + 1 <= the cut-off;
docs/decisions/2026-10-05-match-timing.md). Never at a prediction run: the cut-off is the instance's, recorded once.

    <instance>/training_cutoff.json   written by the retrain (write_cutoff): the cut-off day, the season, the admitted
                                      season-Y match ids (sorted) and their SHA-256, the frame and timeline read
    absent                            the season rule: season Y on 2013 .. Y - 1, as before 20 Oct 2026

The walk-forward fits (model_rebuild/fits.py) never read it: backtests, harm checks and every check on unseen matches
keep the season rule. The daily pipeline's fit (dp_fit), Thinking's season fit (src/pipeline/thinking.py) and stage 2's
coefficients (dp_predict) all take their rows from here, so the three read the same matches.

    ./python.sh src/eda/current_best_model/training_rows.py --write <instance> --cutoff <YYYY-MM-DD> [--timing <parquet>]
    ./python.sh src/eda/current_best_model/training_rows.py --show <instance>
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
CUTOFF_FILE = "training_cutoff.json"
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
TRAIN_FROM = 2013                       # serve_speed_tabpfn.common.TRAIN_FROM: the first training season
EPOCH = dt.date(1970, 1, 1)
RULE = ("season Y on 2013 .. Y - 1 plus every season-Y frame match whose result counts by the cut-off "
        "(lf + 1 <= cutoff_day; the owner, 20 Oct 2026)")


def day_number(day) -> int:
    """Days since 1970-01-01, the match clock's unit."""
    return (pd.Timestamp(day).date() - EPOCH).days


def day_text(n: int) -> str:
    return (EPOCH + dt.timedelta(days=int(n))).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def ids_sha256(ids) -> str:
    return hashlib.sha256("\n".join(sorted(map(str, ids))).encode("utf-8")).hexdigest()


def admitted_by(frame: pd.DataFrame, timing: pd.DataFrame, season: int, cutoff_day: int) -> np.ndarray:
    """A mask over the frame's rows: the season-Y matches whose result counts by cutoff_day (lf + 1 <= cutoff_day).
    Refused when a season-Y match has no timing row: the clock must know every row it admits or leaves out."""
    lf = timing.assign(match_id=timing["match_id"].astype(str)).set_index("match_id")["lf"]
    sel = (frame["season"] == season).to_numpy()
    got = lf.reindex(frame.loc[sel, "match_id"].astype(str))
    if got.isna().any():
        raise RuntimeError(f"{int(got.isna().sum())} season-{season} frame matches have no timing row")
    out = np.zeros(len(frame), dtype=bool)
    out[np.flatnonzero(sel)] = got.to_numpy(dtype="int64") + 1 <= int(cutoff_day)
    return out


def train_mask(frame: pd.DataFrame, season: int, ids=None) -> np.ndarray:
    """The training rows of a season-Y fit: 2013 .. Y - 1, plus the given season-Y match ids (None: the season rule)."""
    m = frame["season"].between(TRAIN_FROM, season - 1).to_numpy()
    if ids:
        m = m | (frame["match_id"].astype(str).isin(set(map(str, ids))).to_numpy()
                 & (frame["season"] == season).to_numpy())
    return m


def write_cutoff(instance: Path, cutoff, timing_path: Path = TIMING, season: int | None = None) -> dict:
    """Record a retrain's cut-off in the instance (after its odds input and input list are applied: the record names the
    frame's SHA-256). season defaults to the cut-off's year."""
    instance = Path(instance)
    frame_path = instance / "model_frame.parquet"
    frame = pd.read_parquet(frame_path, columns=["match_id", "season"])
    timing = pd.read_parquet(timing_path, columns=["match_id", "lf"])
    c = day_number(cutoff)
    season = int(season or pd.Timestamp(cutoff).year)
    mask = admitted_by(frame, timing, season, c)
    ids = sorted(frame.loc[mask, "match_id"].astype(str))
    rec = {"rule": RULE, "cutoff": day_text(c), "cutoff_day": c, "season": season, "admitted": len(ids),
           "season_matches_in_frame": int((frame["season"] == season).sum()),
           "train_rows": int(train_mask(frame, season, ids).sum()),
           "train_rows_season_rule": int(train_mask(frame, season).sum()),
           "ids_sha256": ids_sha256(ids), "frame_sha256": sha256_file(frame_path),
           "timing": str(timing_path), "timing_sha256": sha256_file(timing_path),
           "written_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "ids": ids}
    (instance / CUTOFF_FILE).write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return rec


def read_cutoff(instance: Path) -> dict | None:
    path = Path(instance) / CUTOFF_FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def admitted_ids(instance: Path, season: int) -> list[str] | None:
    """The season-Y matches the instance's retrain admits; None for the season rule (no record, or another season).
    Refused when the record does not belong to the instance's present frame, or its list was altered."""
    rec = read_cutoff(instance)
    if rec is None or int(rec["season"]) != int(season):
        return None
    if ids_sha256(rec["ids"]) != rec["ids_sha256"]:
        raise RuntimeError(f"{Path(instance).name}/{CUTOFF_FILE}: its id list does not match its SHA-256")
    if sha256_file(Path(instance) / "model_frame.parquet") != rec["frame_sha256"]:
        raise RuntimeError(f"{Path(instance).name}/{CUTOFF_FILE} was written on another frame: write it again "
                           "(training_rows.py --write) after the frame's last change")
    return list(rec["ids"])


def job_data(frame: pd.DataFrame, cols: list[str], season: int, instance: Path | None = None, ids=None):
    """(X_train, y_train, X_test, test match ids) as serve_speed_tabpfn.arms.job_data, with the instance's admitted
    season-Y matches (or the given ids) among the training rows, in the frame's order; the test rows are the season's
    other matches. Without a record it is arms.job_data exactly."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src.eda.serve_speed_tabpfn import arms as A
    if "a_won" not in frame.columns:
        raise RuntimeError("job_data needs the training labels: load_frame(..., labels=True)")
    if ids is None and instance is not None:
        ids = admitted_ids(Path(instance), season)
    tr = train_mask(frame, season, ids)
    te = (frame["season"] == season).to_numpy() & ~tr
    X = A.matrix(frame, cols)
    return (X[tr].reset_index(drop=True), frame.loc[tr, "a_won"].astype("int64").to_numpy(),
            X[te].reset_index(drop=True), frame.loc[te, "match_id"].to_numpy())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", help="an instance folder: record its retrain's cut-off")
    ap.add_argument("--show", help="an instance folder: print its record (without the id list)")
    ap.add_argument("--cutoff", help="the cut-off day, YYYY-MM-DD: results counting by it are training rows")
    ap.add_argument("--timing", default=str(TIMING), help="the match clock the build read (its tree's timing.parquet)")
    a = ap.parse_args()
    if a.write:
        if not a.cutoff:
            raise SystemExit("--write needs --cutoff")
        rec = write_cutoff(Path(a.write), a.cutoff, Path(a.timing))
    elif a.show:
        rec = read_cutoff(Path(a.show))
        if rec is None:
            print(f"{a.show}: no {CUTOFF_FILE} (the season rule)")
            return 0
    else:
        raise SystemExit("--write or --show")
    print(json.dumps({k: v for k, v in rec.items() if k != "ids"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
