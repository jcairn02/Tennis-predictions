"""TabPFN-3.5-Thinking season fits for an instance (the owner's model switch, 11 Oct 2026).

Division of work agreed with the daily_prediction session (process log, 10:20): this module holds the PAID season fits;
the daily pipeline's own `--model thinking` (dp_fit / dp_predict, not built yet) will re-attach to a fit by its id
and predict the day's price grid. So:

    fit_season(instance, season)                     a FREE quote (the hosted API's cost estimate sends only the
                                                     data's shape) and the account's remaining quota; nothing paid
    fit_season(instance, season, spend_tokens=True)  the ONE paid fit for that instance and season: season Y trained on
                                                     the instance frame's 2013 .. Y-1 rows, the 57 inputs in the model's
                                                     order (exactly the local model's training rows)

Owner decisions pending before any token is spent (put to the owner by both sessions): paid spend, seed 0 only, and
stage 2 for Thinking. Until the owner approves, call it without spend_tokens (a quote).

Two steps, each in its own environment:
    prepare   (tennis env)          the training rows from the instance frame -> <folder>/train.npz, prepared.json
                                    with train_sha256 (the daily pipeline's recipe, dp_tabcache.train_sha256)
    quote|fit (tennis-tabpfn env)   thinking_api.py, built on the project's guarded client
                                    (src/eda/tabpfn_thinking58/guard.py: async submit, the SDK retry removed,
                                    receipts, save_model; the SDK's synchronous path can bill twice)
The folder is data/studies/master_pipeline/thinking/<instance>/season<Y>/: one slot per instance and season; a slot
once used is never reset by this code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import config as CFG  # noqa: E402

SALT = b"daily_prediction/tabpfn_train/v1"     # dp_tabcache.train_sha256's recipe (the daily_prediction session's)


def folder(instance: Path, season: int) -> Path:
    return CFG.THINKING / Path(instance).name / f"season{int(season)}"


def train_sha256(columns, X, y) -> str:
    """sha256 over the salt, the column names joined by NUL, X as little-endian float64 (C order, one NaN pattern),
    y as little-endian int64: the daily pipeline's dp_tabcache.train_sha256, so dp_fit can verify the rows."""
    import numpy as np
    h = hashlib.sha256(SALT)
    h.update("\x00".join(map(str, columns)).encode())
    v = np.asarray(X, dtype="float64")
    h.update(np.ascontiguousarray(np.where(np.isnan(v), np.nan, v), dtype="<f8").tobytes())
    h.update(np.ascontiguousarray(np.asarray(y), dtype="<i8").tobytes())
    return h.hexdigest()


def prepare(instance: Path, season: int) -> dict:
    """The season's training rows, exactly as the local fit trains (serve_speed_tabpfn.arms.job_data on the instance
    frame, the model's 57 inputs from in_<name> columns), saved for the API worker (which cannot import the frame
    code's environment)."""
    import numpy as np

    from src.eda.model_rebuild import fits as FITS
    from src.eda.serve_speed_tabpfn import arms as A
    from src.eda.serve_speed_tabpfn import common as C
    P = FITS.paths(Path(instance))
    cols = A.arm_inputs("model", P)
    frame = A.load_frame([], P, labels=True)
    X_train, y_train, X_test, test_ids = A.job_data(frame, cols, int(season))
    out = folder(instance, season)
    out.mkdir(parents=True, exist_ok=True)
    digest = train_sha256(X_train.columns, X_train.to_numpy(dtype="float64"), y_train)
    held = out / "prepared.json"
    if held.exists():
        old = json.loads(held.read_text(encoding="utf-8"))
        if old.get("train_sha256") != digest and (out / "fit_slot.json").exists():
            raise RuntimeError(f"{out}: a fit was made on other training rows ({old.get('train_sha256')}); "
                               "a rebuilt instance needs its own folder")
    tmp = out / "train.npz.tmp.npz"
    np.savez(tmp, X=X_train.to_numpy(dtype="float64"), y=np.asarray(y_train, dtype="int64"),
             columns=np.asarray(list(map(str, X_train.columns))), test_rows=np.int64(len(X_test)))
    tmp.replace(out / "train.npz")
    rec = {"instance": CFG.rel(instance), "season": int(season), "train_from": int(C.TRAIN_FROM),
           "train_through": int(season) - 1, "training_rows": int(len(X_train)), "features": len(cols),
           "columns": list(map(str, X_train.columns)), "train_sha256": digest,
           "frame_sha256": C.sha256_file(P.model_frame), "season_matches": int(len(X_test))}
    held.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in rec.items() if k != "columns"}, indent=1))
    return rec


# --- the notebook's call -----------------------------------------------------------------------------------------------
def fit_season(instance, season: int, *, spend_tokens: bool = False, daily_matches: int = 30, dry_run: bool = False):
    """Quote (default) or make (spend_tokens=True) the one Thinking fit of an instance and season."""
    from .runner import Step, run_steps
    inst = Path(instance)
    out = folder(inst, season)
    mode = "fit" if spend_tokens else "quote"
    steps = [Step(f"thinking_prepare_{season}", ["-m", "src.pipeline.thinking", "prepare", "--instance", str(inst),
                                                 "--season", str(season)]),
             Step(f"thinking_{mode}_{season}", ["-m", "src.pipeline.thinking_api", mode, "--folder", str(out),
                                                "--daily-matches", str(daily_matches)]
                  + (["--spend-tokens"] if spend_tokens else []), env="api",
                  note="PAID" if spend_tokens else "free quote")]
    if spend_tokens:
        print("PAID: this dispatches the one Thinking fit of this instance and season (owner approval required).")
    res = run_steps(steps, dry_run=dry_run)
    fit = out / "fit.json"
    if fit.exists() and not dry_run:
        print("fit.json:", json.loads(fit.read_text(encoding="utf-8")).get("fitted_train_set_id"))
    return res


def status(instance) -> dict:
    """Per season: prepared rows, the latest quote, and the fit (if made)."""
    base = CFG.THINKING / Path(instance).name
    out = {}
    for d in sorted(base.glob("season*")) if base.exists() else []:
        quotes = sorted(d.glob("quote_*.json"))
        out[d.name] = {"prepared": (d / "prepared.json").exists(),
                       "latest_quote": json.loads(quotes[-1].read_text(encoding="utf-8")).get("summary") if quotes else None,
                       "fit": json.loads((d / "fit.json").read_text(encoding="utf-8")) if (d / "fit.json").exists() else None,
                       "slot_used": (d / "fit_slot.json").exists()}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Thinking season fits: prepare the training rows (tennis env)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--instance", required=True, type=Path)
    p.add_argument("--season", required=True, type=int)
    a = ap.parse_args()
    if a.cmd == "prepare":
        prepare(a.instance, a.season)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
