"""R4 test verifier, part 1: score.py's --synthetic (and --check) never read a match result.

Three independent checks:

  trace          every Python function called during score.synthetic() is recorded (sys.setprofile); none of the
                 functions that select a_won may run (score.labels, arms.job_data, arms.frame_columns(labels=True),
                 local_fits.fingerprint_check).
  read spy       pandas.read_parquet, pyarrow.parquet.read_table and numpy.load are wrapped: every parquet read must
                 name its columns, and no named column may be a result column (RESULT_COLUMNS).
  substitution   copies of the three tables that hold results are written WITHOUT any result column (the model
                 frame without a_won; Stage 0 reduced to match_id and the two player ids; the early-price frame without
                 a_won, td_winner, td_loser), plus a model frame whose a_won is coin flips. score.synthetic() on each
                 must give output identical (bit for bit) to the run on the real files. score.check() must run on the
                 stripped copies too.

The copies are built by reading every column EXCEPT the result columns (explicit lists), so no real result is loaded
here either. They go to a fresh temporary folder (--scratch to choose one), which is left in place.

Writes data/studies/serve_speed_tabpfn/design/verifier_noread.json.
Run: ./python.sh src/eda/serve_speed_tabpfn/design/verifier_noread.py
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402

OUT = C.OUT / "design" / "verifier_noread.json"
RESULT_COLUMNS = {"a_won", "won", "winner", "loser", "td_winner", "td_loser", "score", "score_flag", "status",
                  "status_detail", "minutes", "sets", "games", "sv_gms_incl_tb"}
FORBIDDEN_CALLS = {("score", "labels"), ("arms", "job_data"), ("local_fits", "fingerprint_check"),
                   ("local_fits", "run")}


class Spy:
    def __init__(self):
        self.reads, self.problems = [], []
        self._rp, self._rt, self._nl = pd.read_parquet, pq.read_table, np.load

    def __enter__(self):
        spy = self

        def read_parquet(path, *a, columns=None, **kw):
            spy._note("pandas.read_parquet", path, columns)
            return spy._rp(path, *a, columns=columns, **kw)

        def read_table(source, *a, columns=None, **kw):
            spy._note("pyarrow.read_table", source, columns)
            return spy._rt(source, *a, columns=columns, **kw)

        def load(file, *a, **kw):
            spy.reads.append({"fn": "numpy.load", "path": str(file)})
            return spy._nl(file, *a, **kw)
        pd.read_parquet, pq.read_table, np.load = read_parquet, read_table, load
        return self

    def __exit__(self, *exc):
        pd.read_parquet, pq.read_table, np.load = self._rp, self._rt, self._nl

    def _note(self, fn, path, columns):
        self.reads.append({"fn": fn, "path": str(path), "columns": list(columns) if columns is not None else None})
        if columns is None:
            self.problems.append(f"{fn} {path}: no explicit column list")
        elif RESULT_COLUMNS & set(columns):
            self.problems.append(f"{fn} {path}: result columns {sorted(RESULT_COLUMNS & set(columns))}")


def traced(fn, *a, **kw):
    calls = set()

    def prof(frame, event, arg):
        if event == "call":
            mod = frame.f_globals.get("__name__", "")
            if mod.startswith("src.eda."):
                calls.add((mod.rsplit(".", 1)[-1], frame.f_code.co_name, mod))
    sys.setprofile(prof)
    try:
        out = fn(*a, **kw)
    finally:
        sys.setprofile(None)
    return out, calls


def stripped_copies(scratch: Path) -> dict:
    """Copies of the result-holding tables without any result column (read with explicit non-result column lists)."""
    P = C.DEFAULT
    scratch.mkdir(parents=True, exist_ok=True)
    out = {}
    names = [c for c in pq.read_schema(P.model_frame).names if c not in RESULT_COLUMNS]
    f = pd.read_parquet(P.model_frame, columns=names)
    assert "a_won" not in f.columns
    out["model_frame_no_result"] = scratch / "model_frame_no_result.parquet"
    f.to_parquet(out["model_frame_no_result"], index=False)
    g = f.copy()
    g["a_won"] = np.random.default_rng(123).random(len(g)) < 0.5          # coin flips, NOT the results
    out["model_frame_coinflip"] = scratch / "model_frame_coinflip.parquet"
    g.to_parquet(out["model_frame_coinflip"], index=False)
    s0 = pd.read_parquet(P.stage0_pre, columns=["match_id", "player_a_id", "player_b_id"])
    out["stage0_ids_only"] = scratch / "stage0_ids_only.parquet"
    s0.to_parquet(out["stage0_ids_only"], index=False)
    names = [c for c in pq.read_schema(P.early).names if c not in RESULT_COLUMNS]
    e = pd.read_parquet(P.early, columns=names)
    out["early_no_result"] = scratch / "early_no_result.parquet"
    e.to_parquet(out["early_no_result"], index=False)
    return out


def comparable(res: dict) -> str:
    """The replicates and the summary as canonical JSON text (NaN-safe, exact floats)."""
    return json.dumps({"replicates": res["replicates"], "summary": res["summary"]}, sort_keys=True, default=str)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", default=None)
    a = ap.parse_args()
    scratch = Path(a.scratch) if a.scratch else Path(tempfile.mkdtemp(prefix="ssp_verifier_noread_"))
    P0 = C.DEFAULT
    kw = dict(beta=0.09, capture_share=0.5, reps=4, seed=7)
    report = {"what": "score.py --synthetic and --check read no match result (trace, read spy, substitution)",
              "scratch": str(scratch)}

    # 1) trace + read spy on the real files
    with Spy() as spy:
        res_real, calls = traced(S.synthetic, P0.with_(out=scratch / "real"), **kw)
    called = sorted({(m, n) for m, n, _ in calls})
    report["trace"] = {"functions_called": [f"{m}.{n}" for m, n in called],
                       "forbidden_called": [f"{m}.{n}" for m, n in called if (m, n) in FORBIDDEN_CALLS],
                       "frame_columns_called": any(n == "frame_columns" for _, n in called),
                       "load_frame_called": any(n == "load_frame" for _, n in called)}
    report["read_spy_real_files"] = {"parquet_reads": [r for r in spy.reads if r["fn"] != "numpy.load"],
                                     "npz_reads": sum(r["fn"] == "numpy.load" for r in spy.reads),
                                     "problems": spy.problems}

    # 2) substitution: stripped copies and a coin-flip a_won
    cp = stripped_copies(scratch)
    P_strip = P0.with_(model_frame=cp["model_frame_no_result"], stage0_pre=cp["stage0_ids_only"],
                       early=cp["early_no_result"], out=scratch / "stripped")
    P_flip = P0.with_(model_frame=cp["model_frame_coinflip"], out=scratch / "coinflip")
    with Spy() as spy2:
        res_strip = S.synthetic(P_strip, **kw)
    res_flip = S.synthetic(P_flip, **kw)
    report["substitution"] = {
        "copies": {k: str(v) for k, v in cp.items()},
        "stripped_identical_to_real": comparable(res_strip) == comparable(res_real),
        "coinflip_identical_to_real": comparable(res_flip) == comparable(res_real),
        "read_spy_problems_stripped": spy2.problems,
        "replicate_P2_real": [r["P2"] for r in res_real["replicates"]],
        "replicate_P2_stripped": [r["P2"] for r in res_strip["replicates"]]}

    # 3) --check on the stripped copies (result-free by design)
    with Spy() as spy3:
        chk, calls3 = traced(S.check, P_strip)
    report["check_on_stripped_copies"] = {
        "ran": True, "men_2024_2026": chk["populations"]["men 2024-2026"]["matches"],
        "population_sha256": chk["hashes"]["POPULATION_SHA256"],
        "forbidden_called": sorted(f"{m}.{n}" for m, n, _ in calls3 if (m, n) in FORBIDDEN_CALLS),
        "read_spy_problems": spy3.problems}
    ok = (not report["trace"]["forbidden_called"] and not report["read_spy_real_files"]["problems"]
          and report["substitution"]["stripped_identical_to_real"] and report["substitution"]["coinflip_identical_to_real"]
          and not report["substitution"]["read_spy_problems_stripped"]
          and not report["check_on_stripped_copies"]["forbidden_called"]
          and not report["check_on_stripped_copies"]["read_spy_problems"])
    report["passed"] = bool(ok)
    C.write_json(OUT, report)
    print(json.dumps({k: v for k, v in report.items() if k not in ("trace", "read_spy_real_files")}, indent=1,
                     default=str)[:4000])
    print("forbidden calls:", report["trace"]["forbidden_called"], "| spy problems:",
          report["read_spy_real_files"]["problems"])
    print("parquet reads (real run):")
    for r in report["read_spy_real_files"]["parquet_reads"]:
        print("  ", Path(r["path"]).name, r["columns"])
    print("PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
