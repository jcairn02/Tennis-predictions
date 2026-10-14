"""TabPFN-3.5-Thinking on live matches already predicted by the local model: step 1, the query (tennis env).

A one-off comparison the owner asked for on 13 Oct 2026 ("Train tabpfn3.5 thinking on the same model as the tabpfn3.5
non thinking model. Dont calibrate the thinking one and see the predictions on these 5 fights"). It is not a prediction
path: the daily engine's own `--model thinking` is that, and it is not built.

The query is exactly what the local model predicted in the given live runs: dp_fit.season_jobs, so each match at the
91 grid prices and at its own price, stored then with A and B swapped. Before saving, the season's training rows are
checked to be the ones the Thinking season fit was made on (the slot's prepared.json train_sha256), and the columns to
be the fit's, in its order. predict_api.py (tennis-tabpfn env) sends the query; compare.py reads the answers back.

    ./python.sh src/eda/thinking_live_compare/query.py --out <folder> <run folder> [<run folder> ...]
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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "eda" / "daily_prediction"))

import dp_fit  # noqa: E402  (the daily engine's own query rows)

from src.pipeline import thinking as TH  # noqa: E402

INSTANCE = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-10"
SLOT = TH.CFG.THINKING / INSTANCE.name / "season2026"


def query_sha256(X: pd.DataFrame) -> str:
    """sha256 over a salt, the column names joined by NUL and X as little-endian float64 (one NaN pattern)."""
    h = hashlib.sha256(b"thinking_live_compare/query/v1")
    h.update("\x00".join(map(str, X.columns)).encode())
    v = np.asarray(X, dtype="float64")
    h.update(np.ascontiguousarray(np.where(np.isnan(v), np.nan, v), dtype="<f8").tobytes())
    return h.hexdigest()


def build(runs: list[Path], out: Path) -> dict:
    prep = json.loads((SLOT / "prepared.json").read_text(encoding="utf-8"))
    parts, segments, start = [], [], 0
    for run in runs:
        for season, part, X_train, y_train, X_all, k, n in dp_fit.season_jobs(run, INSTANCE):
            if int(season) != int(prep["season"]):
                raise SystemExit(f"{run.name}: season {season}, but the fit is season {prep['season']}")
            if TH.train_sha256(X_train.columns, X_train.to_numpy(dtype="float64"), y_train) != prep["train_sha256"]:
                raise SystemExit(f"{run.name}: the training rows differ from the Thinking fit's")
            if list(map(str, X_all.columns)) != prep["columns"]:
                raise SystemExit(f"{run.name}: the query's columns differ from the fit's")
            parts.append(X_all)
            segments.append({"run": run.name, "season": int(season), "start": start, "rows": int(len(X_all)),
                             "stored_rows": int(k), "matches": int(n),
                             "match_id": part["match_id"].astype(str).tolist(),
                             "own_logit": part["in_odds_logit"].astype("float64").tolist()})
            start += len(X_all)
    X = pd.concat(parts, ignore_index=True)
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "query.tmp.npz"
    np.savez(tmp, X=X.to_numpy(dtype="float64"), columns=np.asarray(list(map(str, X.columns))))
    tmp.replace(out / "query.npz")
    manifest = {"made_at": dt.datetime.now(dt.timezone.utc).isoformat(), "instance": TH.CFG.rel(INSTANCE),
                "slot": TH.CFG.rel(SLOT), "train_sha256": prep["train_sha256"], "query_sha256": query_sha256(X),
                "rows": int(len(X)), "columns": list(map(str, X.columns)),
                "grid": {"prices": int(len(dp_fit.GRID)), "from_logit": float(dp_fit.GRID[0]),
                         "to_logit": float(dp_fit.GRID[-1])},
                "segments": segments}
    (out / "query.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k not in ("columns", "segments")}, indent=1))
    for s in segments:
        print(f"{s['run']}: {s['matches']} matches, {s['rows']} rows from row {s['start']}")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("runs", nargs="+", type=Path)
    a = ap.parse_args()
    build(a.runs, a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
