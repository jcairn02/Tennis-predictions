"""The check on unseen matches registered by the lock-in (docs/studies/serve_return_leads/lock_in.md).

    window     men's main-tour matches of the given instance's frame, debut seasons out, tournament date from
               --start (29 Jul 2026) to --end (exclusive). Reading results in it needs --owner-go "<the owner's words>".
               --dry-run reads the seen window instead (1 Jan 2025 - 28 Jul 2026 by season, the 10 Oct instance, edge
               anatomy's speed column) and must reproduce the lock-in's seen readings; it validates the code only.
    scores     common.scores with the frozen scales (lock_in_scales.json, hash-checked): T1-T4 and R0
    speed      the serve-speed stage's 28-day column for the window's matches, from --speed (a parquet with match_id
               and spd_L: spd_L_B before 8 Oct 2026, spd_L_D from then, as the production rule defines it); a match
               without a value counts 0
    test       unpriced leads' registered look.fit (common.fit): beta per RMS beyond the close (slope and curvature),
               four-week blocks, one-sided p from t on G - 1
    verdicts   H0 (R0) and HS (T4) at --level (the schedule's level for this look, e.g. 0.0221); H1-H3 (T1-T3) only
               if H0 is confirmed, Holm at the same level; words: confirmed / contrary / unresolved (with P(beta > 0))
    beside     each trait; beyond the model's forecast (--forecasts: match_id, q_full); completed matches only; the
               Slams left out; the 416 matches already read by the five-pattern check, apart and left out; the
               large-gap table

Run (dry run): ./python.sh src/eda/serve_return_leads/check.py --dry-run
Run (a look):  ./python.sh src/eda/serve_return_leads/check.py --instance <folder> --speed <parquet> --end <date>
               --level <alpha> --owner-go "<the owner's words>" [--forecasts <parquet>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_return_leads import common as C  # noqa: E402
from src.eda.unpriced_leads import look as LK  # noqa: E402
from src.eda.unpriced_leads import screen as H  # noqa: E402

SCALES_SHA = "2547980b0367e38bc8a8eecb89cdd07204b08990b050c0528d90aeba6773635c"
READ_BY_FIVE_PATTERN_CHECK = (pd.Timestamp("2026-07-29"), pd.Timestamp("2026-09-24"))   # read once on 13 Oct 2026
TRAITS = ("R0", "T1", "T2", "T3", "T4")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_scales() -> dict:
    p = C.OUT / "lock_in_scales.json"
    if sha256(p) != SCALES_SHA:
        raise RuntimeError("the frozen scales differ from the lock-in's")
    return json.loads(p.read_text(encoding="utf-8"))


def load_unseen(instance: Path, start: str, end: str, speed: Path) -> pd.DataFrame:
    paths = {"frame": instance / "model_frame.parquet", "model_inputs": instance / "model_inputs.json"}
    seasons = (pd.Timestamp(start).year - 1, pd.Timestamp(end).year)
    f = LK.load_window(paths, seasons[0], seasons[1], end, allow_post_2024=True, start_date=start)
    f = f[f["tour"] == "atp"].reset_index(drop=True)
    s = pd.read_parquet(speed, columns=["match_id", "spd_L"]).astype({"match_id": str})
    f["in_spd"] = s.drop_duplicates("match_id").set_index("match_id")["spd_L"].reindex(f["match_id"]).to_numpy(float)
    return f


def load_dry_run() -> pd.DataFrame:
    f = C.seen("atp")
    return f[f["season"] >= 2025].reset_index(drop=True)


def add_beside(f: pd.DataFrame, forecasts: Path | None) -> pd.DataFrame:
    st = pd.read_parquet(H.STAGE0_M, columns=["match_id", "status"]).astype({"match_id": str})
    st = st.drop_duplicates("match_id").set_index("match_id")["status"].reindex(f["match_id"])
    f["retired"] = (st.astype(str).str.lower() == "retired").to_numpy()
    f["slam"] = (f["in_best_of"].to_numpy(float) == 5)
    if forecasts is not None:
        q = pd.read_parquet(forecasts, columns=["match_id", "q_full"]).astype({"match_id": str})
        q = q.drop_duplicates("match_id").set_index("match_id")["q_full"].reindex(f["match_id"]).to_numpy(float)
        f["L_model"] = np.where(np.isfinite(q), H.lg(q), np.nan)
    return f


def verdict(r: dict, level: float) -> str:
    if not np.isfinite(r.get("p_one_sided", np.nan)):
        return "not readable"
    if r["p_one_sided"] <= level:
        return "confirmed"
    if 1 - r["p_one_sided"] <= level:
        return "contrary"
    return f"unresolved, P(beta > 0) = {r['p_beta_positive']:.2f}"


def large_gap(f: pd.DataFrame, x: np.ndarray) -> dict:
    ok = np.isfinite(x) & (x != 0)
    xs, g = x[ok], f[ok]
    rms = float(np.sqrt(np.mean(xs ** 2))) if ok.any() else np.nan
    flip = xs < 0
    p_a = expit(g["L"].to_numpy(float))
    p = np.where(flip, 1 - p_a, p_a)
    won = np.where(flip, 1 - g["y"].to_numpy(float), g["y"].to_numpy(float))
    k = np.abs(xs) / rms > 1.0
    return {"matches": int(k.sum()), "close_pct": float(100 * np.mean(p[k])) if k.any() else np.nan,
            "won_pct": float(100 * np.mean(won[k])) if k.any() else np.nan}


def run(f: pd.DataFrame, level: float) -> dict:
    sc = load_scales()
    s = C.scores(f, sc)
    out = {"matches": int(len(f)), "blocks": int(len(np.unique(f["block"]))),
           "first_date": str(f["tournament_date"].min().date()), "last_date": str(f["tournament_date"].max().date()),
           "level": level, "readings": {}, "beside": {}}
    for k in TRAITS:
        out["readings"][k] = C.fit(f, s[k], base="L")
    out["verdicts"] = {"H0 (R0)": verdict(out["readings"]["R0"], level),
                       "HS (T4)": verdict(out["readings"]["T4"], level)}
    if out["verdicts"]["H0 (R0)"] == "confirmed":
        ps = [out["readings"][k]["p_one_sided"] for k in ("T1", "T2", "T3")]
        adj = LK.holm(ps)
        for k, p in zip(("T1", "T2", "T3"), adj):
            r = dict(out["readings"][k], p_one_sided=p)
            out["verdicts"][f"H{k[1]} ({k})"] = verdict(r, level)
    else:
        for k in ("T1", "T2", "T3"):
            out["verdicts"][f"H{k[1]} ({k})"] = "not tested (H0 not confirmed)"
    subsets = {"completed only": ~f["retired"].to_numpy(), "Slams out": ~f["slam"].to_numpy()}
    d = f["tournament_date"]
    read5 = ((d >= READ_BY_FIVE_PATTERN_CHECK[0]) & (d < READ_BY_FIVE_PATTERN_CHECK[1])).to_numpy()
    if read5.any():
        subsets["the 416 read by the five-pattern check"] = read5
        subsets["without them"] = ~read5
    for name, m in subsets.items():
        g = f[m].reset_index(drop=True)
        out["beside"][name] = {k: C.fit(g, s[k][m], base="L") for k in ("R0", "T4")}
    if "L_model" in f and np.isfinite(f["L_model"]).any():
        out["beside"]["beyond the model"] = {k: C.fit(f, s[k], base="L_model") for k in TRAITS}
    out["beside"]["large gap"] = {k: large_gap(f, s[k]) for k in TRAITS}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--instance")
    ap.add_argument("--speed")
    ap.add_argument("--forecasts")
    ap.add_argument("--start", default="2026-07-29")
    ap.add_argument("--end")
    ap.add_argument("--level", type=float, default=0.05)
    ap.add_argument("--owner-go")
    a = ap.parse_args()
    if a.dry_run:
        f = add_beside(load_dry_run(), None)
        name = "dry-run"
    else:
        if not a.owner_go:
            raise SystemExit("a look reads unseen results: it needs --owner-go \"<the owner's words>\"")
        if pd.Timestamp(a.start) < C.SEALED_FROM:
            raise SystemExit("the window starts before 29 Jul 2026")
        f = add_beside(load_unseen(Path(a.instance), a.start, a.end, Path(a.speed)),
                       Path(a.forecasts) if a.forecasts else None)
        name = f"look_{time.strftime('%Y%m%d_%H%M')}"
    res = run(f, a.level)
    res.update({"run": name, "owner_go": a.owner_go, "run_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "code_sha256": sha256(Path(__file__)), "common_sha256": sha256(Path(C.__file__)),
                "look_sha256": sha256(Path(LK.__file__))})
    C.write_json(C.OUT / "checks" / name / "result.json", res)
    print(json.dumps({k: res[k] for k in ("matches", "blocks", "first_date", "last_date", "verdicts")}, indent=1))
    print({k: round(v["z"], 3) for k, v in res["readings"].items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
